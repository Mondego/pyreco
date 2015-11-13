__FILENAME__ = schemasync
#!/usr/bin/python

__author__ = "Mitch Matuson"
__copyright__ = "Copyright 2009 Mitch Matuson"
__version__ = "0.9.1"
__license__ = "Apache 2.0"

import re
import sys
import os
import logging
import datetime
import optparse
import syncdb
import utils
import warnings

# supress MySQLdb DeprecationWarning in Python 2.6
warnings.simplefilter("ignore", DeprecationWarning)

try:
    import MySQLdb
except ImportError:
    print "Error: Missing Required Dependency MySQLdb."
    sys.exit(1)

try:
    import schemaobject
except ImportError:
    print "Error: Missing Required Dependency SchemaObject"
    sys.exit(1)


APPLICATION_VERSION = __version__
APPLICATION_NAME = "Schema Sync"
LOG_FILENAME = "schemasync.log"
DATE_FORMAT = "%Y%m%d"
TPL_DATE_FORMAT = "%a, %b %d, %Y"
PATCH_TPL = """--
-- Schema Sync %(app_version)s %(type)s
-- Created: %(created)s
-- Server Version: %(server_version)s
-- Apply To: %(target_host)s/%(target_database)s
--

%(data)s"""


def parse_cmd_line(fn):
    """Parse the command line options and pass them to the application"""

    def processor(*args, **kwargs):
        usage = """
                %prog [options] <source> <target>
                source/target format: mysql://user:pass@host:port/database"""
        description = """
                       A MySQL Schema Synchronization Utility
                      """
        parser = optparse.OptionParser(usage=usage,
                                        description=description)

        parser.add_option("-V", "--version",
                          action="store_true",
                          dest="show_version",
                          default=False,
                          help=("show version and exit."))

        parser.add_option("-r", "--revision",
                        action="store_true",
                        dest="version_filename",
                        default=False,
                        help=("increment the migration script version number "
                              "if a file with the same name already exists."))

        parser.add_option("-a", "--sync-auto-inc",
                          dest="sync_auto_inc",
                          action="store_true",
                          default=False,
                          help="sync the AUTO_INCREMENT value for each table.")

        parser.add_option("-c", "--sync-comments",
                          dest="sync_comments",
                          action="store_true",
                          default=False,
                          help=("sync the COMMENT field for all "
                                "tables AND columns"))

        parser.add_option("--tag",
                         dest="tag",
                         help=("tag the migration scripts as <database>_<tag>."
                               " Valid characters include [A-Za-z0-9-_]"))

        parser.add_option("--output-directory",
                          dest="output_directory",
                          default=os.getcwd(),
                          help=("directory to write the migration scrips. "
                                 "The default is current working directory. "
                                 "Must use absolute path if provided."))

        parser.add_option("--log-directory",
                          dest="log_directory",
                          help=("set the directory to write the log to. "
                                "Must use absolute path if provided. "
                                "Default is output directory. "
                                "Log filename is schemasync.log"))

        options, args = parser.parse_args(sys.argv[1:])


        if options.show_version:
            print APPLICATION_NAME, __version__
            return 0

        if (not args) or (len(args) != 2):
            parser.print_help()
            return 0

        return fn(*args, **dict(version_filename=options.version_filename,
                                 output_directory=options.output_directory,
                                 log_directory=options.log_directory,
                                 tag=options.tag,
                                 sync_auto_inc=options.sync_auto_inc,
                                 sync_comments=options.sync_comments))
    return processor


def app(sourcedb='', targetdb='', version_filename=False,
        output_directory=None, log_directory=None,
        tag=None, sync_auto_inc=False, sync_comments=False):
    """Main Application"""

    options = locals()

    if not os.path.isabs(output_directory):
        print "Error: Output directory must be an absolute path. Quiting."
        return 1

    if not os.path.isdir(output_directory):
        print "Error: Output directory does not exist. Quiting."
        return 1

    if not log_directory or not os.path.isdir(log_directory):
        if log_directory:
            print "Log directory does not exist, writing log to %s" % output_directory
        log_directory = output_directory

    logging.basicConfig(filename=os.path.join(log_directory, LOG_FILENAME),
                        level=logging.INFO,
                        format= '[%(levelname)s  %(asctime)s] %(message)s')

    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    logging.getLogger('').addHandler(console)

    if not sourcedb:
        logging.error("Source database URL not provided. Exiting.")
        return 1

    source_info = schemaobject.connection.parse_database_url(sourcedb)
    if not source_info:
        logging.error("Invalid source database URL format. Exiting.")
        return 1

    if not source_info['protocol'] == 'mysql':
        logging.error("Source database must be MySQL. Exiting.")
        return 1

    if 'db' not in source_info:
        logging.error("Source database name not provided. Exiting.")
        return 1

    if not targetdb:
        logging.error("Target database URL not provided. Exiting.")
        return 1

    target_info = schemaobject.connection.parse_database_url(targetdb)
    if not target_info:
        logging.error("Invalid target database URL format. Exiting.")
        return 1

    if not target_info['protocol'] == 'mysql':
        logging.error("Target database must be MySQL. Exiting.")
        return 1

    if 'db' not in target_info:
        logging.error("Target database name not provided. Exiting.")
        return 1

    source_obj = schemaobject.SchemaObject(sourcedb)
    target_obj = schemaobject.SchemaObject(targetdb)

    if source_obj.version < '5.0.0':
        logging.error("%s requires MySQL version 5.0+ (source is v%s)"
                        % (APPLICATION_NAME, source_obj.version))
        return 1

    if target_obj.version < '5.0.0':
        logging.error("%s requires MySQL version 5.0+ (target is v%s)"
                % (APPLICATION_NAME, target_obj.version))
        return 1

    # data transformation filters
    filters = (lambda d: utils.REGEX_MULTI_SPACE.sub(' ', d),
                lambda d: utils.REGEX_DISTANT_SEMICOLIN.sub(';', d))

    # Information about this run, used in the patch/revert templates
    ctx = dict(app_version=APPLICATION_VERSION,
               server_version=target_obj.version,
               target_host=target_obj.host,
               target_database=target_obj.selected.name,
               created=datetime.datetime.now().strftime(TPL_DATE_FORMAT))

    p_fname, r_fname = utils.create_pnames(target_obj.selected.name, 
                                           tag=tag,
                                           date_format=DATE_FORMAT)

    ctx['type'] = "Patch Script"
    pBuffer = utils.PatchBuffer(name=os.path.join(output_directory, p_fname),
                                filters=filters, tpl=PATCH_TPL, ctx=ctx.copy(),
                                version_filename=version_filename)

    ctx['type'] = "Revert Script"
    rBuffer = utils.PatchBuffer(name=os.path.join(output_directory, r_fname),
                                filters=filters, tpl=PATCH_TPL, ctx=ctx.copy(),
                                version_filename=version_filename)

    db_selected = False
    for patch, revert in syncdb.sync_schema(source_obj.selected,
                                            target_obj.selected, options):
        if patch and revert:

            if not db_selected:
                pBuffer.write(target_obj.selected.select() + '\n')
                rBuffer.write(target_obj.selected.select() + '\n')
                db_selected = True

            pBuffer.write(patch + '\n')
            rBuffer.write(revert + '\n')

    if not pBuffer.modified:
        logging.info(("No migration scripts written."
                     " mysql://%s/%s and mysql://%s/%s were in sync.") %
                    (source_obj.host, source_obj.selected.name,
                     target_obj.host, target_obj.selected.name))
    else:
        try:
            pBuffer.save()
            rBuffer.save()
            logging.info("Migration scripts created for mysql://%s/%s\n"
                         "Patch Script: %s\nRevert Script: %s"
                         % (target_obj.host, target_obj.selected.name,
                            pBuffer.name, rBuffer.name))
        except OSError, e:
            pBuffer.delete()
            rBuffer.delete()
            logging.error("Failed writing migration scripts. %s" % e)
            return 1

    return 0


def main():
    try:
        sys.exit(parse_cmd_line(app)())
    except schemaobject.connection.DatabaseError, e:
        logging.error("MySQL Error %d: %s" % (e.args[0], e.args[1]))
        sys.exit(1)
    except KeyboardInterrupt:
        print "Sync Interrupted, Exiting."
        sys.exit(1)


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = syncdb
from utils import REGEX_TABLE_AUTO_INC, REGEX_TABLE_COMMENT


def sync_schema(fromdb, todb, options):
    """Generate the SQL statements needed to sync two Databases and all of
       their children (Tables, Columns, Indexes, Foreign Keys)

    Args:
        fromdb: A SchemaObject Schema Instance.
        todb: A SchemaObject Schema Instance.
        options: dictionary of options to use when syncing schemas
            sync_auto_inc: Bool, sync auto inc value throughout the schema?
            sync_comments: Bool, sync comment fields trhoughout the schema?

    Yields:
        A tuple (patch, revert) containing the next SQL statement needed
        to migrate fromdb to todb. The tuple will always contain 2 strings,
        even if they are empty.
    """

    p, r = sync_database_options(fromdb, todb)
    if p and r:
        yield ("%s %s;" % (todb.alter(), p),
               "%s %s;" % (todb.alter(), r))

    for p, r in sync_created_tables(fromdb.tables, todb.tables,
                                   sync_auto_inc=options['sync_auto_inc'],
                                   sync_comments=options['sync_comments']):
        yield p, r

    for p, r in sync_dropped_tables(fromdb.tables, todb.tables,
                                    sync_auto_inc=options['sync_auto_inc'],
                                    sync_comments=options['sync_comments']):
        yield  p, r

    for t in fromdb.tables:
        if not t in todb.tables:
            continue

        from_table = fromdb.tables[t]
        to_table = todb.tables[t]

        plist = []
        rlist = []
        for p, r in sync_table(from_table, to_table, options):
            plist.append(p)
            rlist.append(r)

        if plist and rlist:
            p = "%s %s;" % (to_table.alter(), ', '.join(plist))
            r = "%s %s;" % (to_table.alter(), ', '.join(rlist))
            yield p, r


def sync_table(from_table, to_table, options):
    """Generate the SQL statements needed to sync two Tables and all of their
       children (Columns, Indexes, Foreign Keys)

    Args:
        from_table: A SchemaObject TableSchema Instance.
        to_table: A SchemaObject TableSchema Instance.
        options: dictionary of options to use when syncing schemas
            sync_auto_inc: Bool, sync auto inc value throughout the table?
            sync_comments: Bool, sync comment fields trhoughout the table?

    Yields:
        A tuple (patch, revert) containing the next SQL statements
    """
    for p, r in sync_created_columns(from_table.columns,
                                     to_table.columns,
                                     sync_comments=options['sync_comments']):
        yield (p, r)

    for p, r in sync_dropped_columns(from_table.columns,
                                    to_table.columns,
                                    sync_comments=options['sync_comments']):
        yield (p, r)

    if from_table and to_table:
        for p, r in sync_modified_columns(from_table.columns,
                                          to_table.columns,
                                          sync_comments=options['sync_comments']):
            yield (p, r)

        # add new indexes, then compare existing indexes for changes
        for p, r in sync_created_constraints(from_table.indexes, to_table.indexes):
            yield (p, r)

        for p, r in sync_modified_constraints(from_table.indexes, to_table.indexes):
            yield (p, r)

        # we'll drop indexes after we process foreign keys...

        # add new foreign keys and compare existing fks for changes
        for p, r in sync_created_constraints(from_table.foreign_keys,
                                             to_table.foreign_keys):
            yield (p, r)

        for p, r in sync_modified_constraints(from_table.foreign_keys,
                                              to_table.foreign_keys):
            yield (p, r)

        for p, r in sync_dropped_constraints(from_table.foreign_keys,
                                             to_table.foreign_keys):
            yield (p, r)

        #drop remaining indexes
        for p, r in sync_dropped_constraints(from_table.indexes, to_table.indexes):
            yield (p, r)

        # end the alter table syntax with the changed table options
        p, r = sync_table_options(from_table, to_table,
                                 sync_auto_inc=options['sync_auto_inc'],
                                 sync_comments=options['sync_comments'])
        if p:
            yield (p, r)


def sync_database_options(from_db, to_db):
    """Generate the SQL statements needed to modify the Database options
       of the target schema (patch), and restore them to their previous
       definition (revert)

    Args:
        from_db: A SchemaObject DatabaseSchema Instance.
        to_db: A SchemaObject DatabaseSchema Instance.
        options: dictionary of options to use when syncing schemas
            sync_auto_inc: Bool, sync auto increment value throughout the table?
            sync_comments: Bool, sync comment fields trhoughout the table?

    Returns:
        A tuple (patch, revert) containing the SQL statements
        A tuple of empty strings will be returned if no changes were found
    """
    p = []
    r = []

    for opt in from_db.options:
        if from_db.options[opt] != to_db.options[opt]:
            p.append(from_db.options[opt].create())
            r.append(to_db.options[opt].create())

    if p:
        return (' '.join(p), ' '.join(r))
    else:
        return ('', '')


def sync_created_tables(from_tables, to_tables,
                        sync_auto_inc=False, sync_comments=False):
    """Generate the SQL statements needed to CREATE Tables in the target
       schema (patch), and remove them (revert)

    Args:
        from_tables: A OrderedDict of SchemaObject.TableSchema Instances.
        to_tables: A OrderedDict of SchemaObject.TableSchema Instances.
        sync_auto_inc: Bool (default=False), sync auto increment for each table?
        sync_comments: Bool (default=False), sync the comment field for the table?

    Yields:
        A tuple (patch, revert) containing the next SQL statements
    """
    for t in from_tables:
        if t not in to_tables:
            p, r = from_tables[t].create(), from_tables[t].drop()
            if not sync_auto_inc:
                p = REGEX_TABLE_AUTO_INC.sub('', p)
                r = REGEX_TABLE_AUTO_INC.sub('', r)
            if not sync_comments:
                p = REGEX_TABLE_COMMENT.sub('', p)
                r = REGEX_TABLE_COMMENT.sub('', r)

            yield p, r


def sync_dropped_tables(from_tables, to_tables,
                        sync_auto_inc=False, sync_comments=False):
    """Generate the SQL statements needed to DROP Tables in the target
       schema (patch), and restore them to their previous definition (revert)

    Args:
        from_tables: A OrderedDict of SchemaObject.TableSchema Instances.
        to_tables: A OrderedDict of SchemaObject.TableSchema Instances.
        sync_auto_inc: Bool (default=False), sync auto increment for each table?
        sync_comments: Bool (default=False), sync the comment field for the table?

    Yields:
        A tuple (patch, revert) containing the next SQL statements
    """
    for t in to_tables:
        if t not in from_tables:
            p, r = to_tables[t].drop(), to_tables[t].create()
            if not sync_auto_inc:
                p = REGEX_TABLE_AUTO_INC.sub('', p)
                r = REGEX_TABLE_AUTO_INC.sub('', r)
            if not sync_comments:
                p = REGEX_TABLE_COMMENT.sub('', p)
                r = REGEX_TABLE_COMMENT.sub('', r)

            yield p, r


def sync_table_options(from_table, to_table,
                       sync_auto_inc=False, sync_comments=False):
    """Generate the SQL statements needed to modify the Table options
       of the target table (patch), and restore them to their previous
       definition (revert)

    Args:
       from_table: A SchemaObject TableSchema Instance.
       to_table: A SchemaObject TableSchema Instance.
       sync_auto_inc: Bool, sync the tables auto increment value?
       sync_comments: Bool, sync the tbales comment field?

    Returns:
       A tuple (patch, revert) containing the SQL statements.
       A tuple of empty strings will be returned if no changes were found
    """
    p = []
    r = []

    for opt in from_table.options:
        if ((opt == 'auto_increment' and not sync_auto_inc) or
            (opt == 'comment' and not sync_comments)):
            continue

        if from_table.options[opt] != to_table.options[opt]:
            p.append(from_table.options[opt].create())
            r.append(to_table.options[opt].create())

    if p:
        return (' '.join(p), ' '.join(r))
    else:
        return ('', '')


def get_previous_item(lst, item):
    """ Given an item, find its previous item in the list
        If the item appears more than once in the list, return the first index

        Args:
            lst: the list to search
            item: the item we want to find the previous item for

        Returns: The previous item or None if not found.
    """
    try:
        i = lst.index(item)
        if i > 0:
            return lst[i - 1]
    except (IndexError, ValueError):
        pass

    return None


def sync_created_columns(from_cols, to_cols, sync_comments=False):
    """Generate the SQL statements needed to ADD Columns to the target
       table (patch) and remove them (revert)

    Args:
        from_cols: A OrderedDict of SchemaObject.ColumnSchema Instances.
        to_cols: A OrderedDict of SchemaObject.ColumnSchema Instances.
        sync_comments: Bool (default=False), sync the comment field for each column?

    Yields:
        A tuple (patch, revert) containing the next SQL statements
    """
    for c in from_cols:
        if c not in to_cols:
            fprev = get_previous_item(from_cols.keys(), c)
            yield (from_cols[c].create(after=fprev, with_comment=sync_comments),
                   from_cols[c].drop())


def sync_dropped_columns(from_cols, to_cols, sync_comments=False):
    """Generate the SQL statements needed to DROP Columns in the target
       table (patch) and restore them to their previous definition (revert)

    Args:
        from_cols: A OrderedDictionary of SchemaObject.ColumnSchema Instances.
        to_cols: A OrderedDictionary of SchemaObject.ColumnSchema Instances.
        sync_comments: Bool (default=False), sync the comment field for each column?

    Yields:
        A tuple (patch, revert) containing the next SQL statements
    """
    for c in to_cols:
        if c not in from_cols:
            tprev = get_previous_item(to_cols.keys(), c)
            yield (to_cols[c].drop(),
                   to_cols[c].create(after=tprev, with_comment=sync_comments))


def sync_modified_columns(from_cols, to_cols, sync_comments=False):
    """Generate the SQL statements needed to MODIFY Columns in the target
       table (patch) and restore them to their previous definition (revert)

    Args:
        from_cols: A OrderedDict of SchemaObject.ColumnSchema Instances.
        to_cols: A OrderedDict of SchemaObject.ColumnSchema Instances.
        sync_comments: Bool (default=False), sync the comment field for each column?

    Yields:
        A tuple (patch, revert) containing the next SQL statements
    """
    # find the column names comomon to each table
    # and retain the order in which they appear
    from_names = [c for c in from_cols.keys() if c in to_cols]
    to_names = [c for c in to_cols.keys() if c in from_cols]

    for from_idx, name in enumerate(from_names):

        to_idx = to_names.index(name)

        if ((from_idx != to_idx) or
            (to_cols[name] != from_cols[name]) or
            (sync_comments and (from_cols[name].comment != to_cols[name].comment))):

            # move the element to its correct spot as we do comparisons
            # this will prevent a domino effect of off-by-one false positives.
            if from_names.index(to_names[from_idx]) > to_idx:
                name = to_names[from_idx]
                from_names.remove(name)
                from_names.insert(from_idx, name)
            else:
                to_names.remove(name)
                to_names.insert(from_idx, name)

            fprev = get_previous_item(from_cols.keys(), name)
            tprev = get_previous_item(to_cols.keys(), name)
            yield (from_cols[name].modify(after=fprev, with_comment=sync_comments),
                   to_cols[name].modify(after=tprev, with_comment=sync_comments))


def sync_created_constraints(src, dest):
    """Generate the SQL statements needed to ADD constraints
       (indexes, foreign keys) to the target table (patch)
       and remove them (revert)

    Args:
        src: A OrderedDictionary of SchemaObject IndexSchema
             or ForeignKeySchema Instances
        dest: A OrderedDictionary of SchemaObject IndexSchema
              or ForeignKeySchema Instances

    Yields:
        A tuple (patch, revert) containing the next SQL statements
    """
    for c in src:
        if c not in dest:
            yield src[c].create(), src[c].drop()


def sync_dropped_constraints(src, dest):
    """Generate the SQL statements needed to DROP constraints
       (indexes, foreign keys) from the target table (patch)
       and re-add them (revert)

    Args:
        src: A OrderedDict of SchemaObject IndexSchema
             or ForeignKeySchema Instances
        dest: A OrderedDict of SchemaObject IndexSchema
              or ForeignKeySchema Instances

    Yields:
        A tuple (patch, revert) containing the next SQL statements
    """
    for c in dest:
        if c not in src:
            yield dest[c].drop(), dest[c].create()


def sync_modified_constraints(src, dest):
    """Generate the SQL statements needed to modify
       constraints (indexes, foreign keys) in the target table (patch)
       and restore them to their previous definition (revert)

       2 tuples will be generated for every change needed.
       Constraints must be dropped and re-added, since you can not modify them.

    Args:
        src: A OrderedDict of SchemaObject IndexSchema
             or ForeignKeySchema Instances
        dest: A OrderedDict of SchemaObject IndexSchema
              or ForeignKeySchema Instances

    Yields:
        A tuple (patch, revert) containing the next SQL statements
    """
    for c in src:
        if c in dest and src[c] != dest[c]:
            yield dest[c].drop(), dest[c].drop()
            yield src[c].create(), dest[c].create()

########NEW FILE########
__FILENAME__ = utils
"""Utility functions for Schema Sync"""

import re
import os
import datetime
import glob
import cStringIO

#REGEX_NO_TICKS = re.compile('`')
#REGEX_INT_SIZE = re.compile('int\(\d+\)')
REGEX_MULTI_SPACE = re.compile(r'\s\s+')
REGEX_DISTANT_SEMICOLIN = re.compile(r'(\s+;)$')
REGEX_FILE_COUNTER = re.compile(r"\_(?P<i>[0-9]+)\.(?:[^\.]+)$")
REGEX_TABLE_COMMENT = re.compile(r"COMMENT(?:(?:\s*=\s*)|\s*)'(.*?)'", re.I)
REGEX_TABLE_AUTO_INC = re.compile(r"AUTO_INCREMENT(?:(?:\s*=\s*)|\s*)(\d+)", re.I)


def versioned(filename):
    """Return the versioned name for a file.
       If filename exists, the next available sequence # will be added to it.
       file.txt => file_1.txt => file_2.txt => ...
       If filename does not exist the original filename is returned.

       Args:
            filename: the filename to version (including path to file)

       Returns:
            String, New filename.
    """
    name, ext = os.path.splitext(filename)
    files = glob.glob(name + '*' + ext)
    if not files:
        return filename

    files= map(lambda x: REGEX_FILE_COUNTER.search(x, re.I), files)
    file_counters = [i.group('i') for i in files if i]

    if file_counters:
        i = int(max(file_counters)) + 1
    else:
        i = 1

    return name + ('_%d' % i) + ext


def create_pnames(db, tag=None, date_format="%Y%m%d"):
    """Returns a tuple of the filenames to use to create the migration scripts.
       Filename format: <db>[_<tag>].<date=DATE_FORMAT>.(patch|revert).sql

        Args:
            db: srting, databse name
            tag: string, optional, tag for the filenames
            date_format: string, the current date format
                         Default Format: 21092009

        Returns:
            tuple of strings (patch_filename, revert_filename)
    """
    d = datetime.datetime.now().strftime(date_format)
    if tag:
        tag = re.sub('[^A-Za-z0-9_-]', '', tag)
        basename = "%s_%s.%s" % (db, tag, d)
    else:
        basename = "%s.%s" % (db, d)

    return ("%s.%s" % (basename, "patch.sql"),
            "%s.%s" % (basename, "revert.sql"))


class PatchBuffer(object):
    """Class for creating patch files

        Attributes:
            name: String, filename to use when saving the patch
            filters: List of functions to map to the patch data
            tpl: The patch template where the data will be written
                 All data written to the PatchBuffer is palced in the
                template variable %(data)s.
            ctx: Dictionary of values to be put replaced in the template.
            version_filename: Bool, version the filename if it already exists?
            modified: Bool (default=False), flag to check if the
                      PatchBuffer has been written to.
    """

    def __init__(self, name, filters, tpl, ctx, version_filename=False):
        """Inits the PatchBuffer class"""
        self._buffer = cStringIO.StringIO()
        self.name = name
        self.filters = filters
        self.tpl = tpl
        self.ctx = ctx
        self.version_filename = version_filename
        self.modified = False

    def write(self, data):
        """Write data to the buffer."""
        self.modified = True
        self._buffer.write(data)

    def save(self):
        """Apply filters, template transformations and write buffer to disk"""
        data = self._buffer.getvalue()
        if not data:
            return False

        if self.version_filename:
            self.name = versioned(self.name)
        fh = open(self.name, 'w')

        for f in self.filters:
            data = f(data)

        self.ctx['data'] = data

        fh.write(self.tpl % self.ctx)
        fh.close()

        return True

    def delete(self):
        """Delete the patch once it has been writen to disk"""
        if os.path.isfile(self.name):
            os.unlink(self.name)

    def __del__(self):
        self._buffer.close()

########NEW FILE########
__FILENAME__ = test_all
#!/usr/bin/python
import unittest
from test_sync_database import TestSyncDatabase
from test_sync_tables import TestSyncTables
from test_sync_columns import TestSyncColumns
from test_sync_constraints import TestSyncConstraints
from test_utils import TestVersioned, TestPNames, TestPatchBuffer
from test_regex import TestTableCommentRegex, TestTableAutoIncrementRegex, TestMultiSpaceRegex,TestFileCounterRegex,TestDistantSemiColonRegex

def get_database_url():
    database_url = raw_input("\nTests need to be run against the Sakila Database v0.8\n"
                            "Enter the MySQL Database Connection URL without the database name\n"
                            "Example: mysql://user:pass@host:port/\n"
                            "URL: ")
    if not database_url.endswith('/'):
        database_url += '/'
    return database_url

def regressionTest():
    test_cases = [
                  TestTableCommentRegex,
                  TestTableAutoIncrementRegex,
                  TestMultiSpaceRegex,
                  TestDistantSemiColonRegex,
                  TestFileCounterRegex,
                  TestSyncDatabase,
                  TestSyncTables,
                  TestSyncColumns,
                  TestSyncConstraints,
                  TestVersioned,
                  TestPNames,
                  TestPatchBuffer,
                  ]
    database_url = get_database_url()

    suite = unittest.TestSuite()
    for tc in test_cases:
        tc.database_url = database_url
        suite.addTest(unittest.makeSuite(tc))
    return suite

if __name__ == "__main__":
    unittest.main(defaultTest="regressionTest")
########NEW FILE########
__FILENAME__ = test_regex
#!/usr/bin/python
import unittest
import re
from schemasync.utils import REGEX_TABLE_AUTO_INC, REGEX_TABLE_COMMENT
from schemasync.utils import REGEX_MULTI_SPACE, REGEX_DISTANT_SEMICOLIN, REGEX_FILE_COUNTER

class TestTableCommentRegex(unittest.TestCase):

    def test_single_column_comment_case_insensitive(self):
        """Test REGEX_TABLE_COMMENT lowercase (comment '*')"""
        table = """CREATE TABLE `person` (`id` int(10) unsigned NOT NULL AUTO_INCREMENT, `first_name` varchar(100) NOT NULL comment 'this is your first name',`last_name` varchar(100) NOT NULL,`created` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',PRIMARY KEY (`id`)) ENGINE=InnoDB DEFAULT CHARSET=utf8"""
        (sql, count) = REGEX_TABLE_COMMENT.subn('', table)
        self.assertEqual(count, 1)
        self.assertEqual(sql, """CREATE TABLE `person` (`id` int(10) unsigned NOT NULL AUTO_INCREMENT, `first_name` varchar(100) NOT NULL ,`last_name` varchar(100) NOT NULL,`created` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',PRIMARY KEY (`id`)) ENGINE=InnoDB DEFAULT CHARSET=utf8""")

    def test_single_column_comment_space_seperator(self):
        """Test REGEX_TABLE_COMMENT space seperator (COMMENT '*')"""
        table = """CREATE TABLE `person` (`id` int(10) unsigned NOT NULL AUTO_INCREMENT, `first_name` varchar(100) NOT NULL COMMENT 'this is your first name',`last_name` varchar(100) NOT NULL,`created` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',PRIMARY KEY (`id`)) ENGINE=InnoDB DEFAULT CHARSET=utf8"""
        (sql, count) = REGEX_TABLE_COMMENT.subn('', table)
        self.assertEqual(count, 1)
        self.assertEqual(sql, """CREATE TABLE `person` (`id` int(10) unsigned NOT NULL AUTO_INCREMENT, `first_name` varchar(100) NOT NULL ,`last_name` varchar(100) NOT NULL,`created` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',PRIMARY KEY (`id`)) ENGINE=InnoDB DEFAULT CHARSET=utf8""")

    def test_single_column_comment_space_seperator_multiple_spaces(self):
        """Test REGEX_TABLE_COMMENT multiple spaces as the seperator (COMMENT   '*')"""
        table = """CREATE TABLE `person` (`id` int(10) unsigned NOT NULL AUTO_INCREMENT, `first_name` varchar(100) NOT NULL COMMENT   'this is your first name',`last_name` varchar(100) NOT NULL,`created` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',PRIMARY KEY (`id`)) ENGINE=InnoDB DEFAULT CHARSET=utf8"""
        (sql, count) = REGEX_TABLE_COMMENT.subn('', table)
        self.assertEqual(count, 1)
        self.assertEqual(sql, """CREATE TABLE `person` (`id` int(10) unsigned NOT NULL AUTO_INCREMENT, `first_name` varchar(100) NOT NULL ,`last_name` varchar(100) NOT NULL,`created` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',PRIMARY KEY (`id`)) ENGINE=InnoDB DEFAULT CHARSET=utf8""")

    def test_single_column_comment_equals_seperator(self):
        """Test REGEX_TABLE_COMMENT = seperator (COMMENT='*')"""
        table = """CREATE TABLE `person` (`id` int(10) unsigned NOT NULL AUTO_INCREMENT, `first_name` varchar(100) NOT NULL COMMENT='this is your first name',`last_name` varchar(100) NOT NULL,`created` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',PRIMARY KEY (`id`)) ENGINE=InnoDB DEFAULT CHARSET=utf8"""
        (sql, count) = REGEX_TABLE_COMMENT.subn('', table)
        self.assertEqual(count, 1)
        self.assertEqual(sql, """CREATE TABLE `person` (`id` int(10) unsigned NOT NULL AUTO_INCREMENT, `first_name` varchar(100) NOT NULL ,`last_name` varchar(100) NOT NULL,`created` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',PRIMARY KEY (`id`)) ENGINE=InnoDB DEFAULT CHARSET=utf8""")

    def test_single_column_comment_equals_seperator_with_spaces(self):
        """Test REGEX_TABLE_COMMENT = seperator surrounded by spaces (COMMENT = '*')"""
        table = """CREATE TABLE `person` (`id` int(10) unsigned NOT NULL AUTO_INCREMENT, `first_name` varchar(100) NOT NULL COMMENT = 'this is your first name',`last_name` varchar(100) NOT NULL,`created` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',PRIMARY KEY (`id`)) ENGINE=InnoDB DEFAULT CHARSET=utf8"""
        (sql, count) = REGEX_TABLE_COMMENT.subn('', table)
        self.assertEqual(count, 1)
        self.assertEqual(sql, """CREATE TABLE `person` (`id` int(10) unsigned NOT NULL AUTO_INCREMENT, `first_name` varchar(100) NOT NULL ,`last_name` varchar(100) NOT NULL,`created` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',PRIMARY KEY (`id`)) ENGINE=InnoDB DEFAULT CHARSET=utf8""")

    def test_multiple_mixed_seperated_column_comment(self):
        """Test REGEX_TABLE_COMMENT multiple column comments (COMMENT '*', COMMENT='*')"""
        table = """CREATE TABLE `person` (`id` int(10) unsigned NOT NULL AUTO_INCREMENT, `first_name` varchar(100) NOT NULL COMMENT 'this is your first name',`last_name` varchar(100) NOT NULL COMMENT='this is your last name',`created` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',PRIMARY KEY (`id`)) ENGINE=InnoDB DEFAULT CHARSET=utf8"""
        (sql, count) = REGEX_TABLE_COMMENT.subn('', table)
        self.assertEqual(count, 2)
        self.assertEqual(sql, """CREATE TABLE `person` (`id` int(10) unsigned NOT NULL AUTO_INCREMENT, `first_name` varchar(100) NOT NULL ,`last_name` varchar(100) NOT NULL ,`created` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',PRIMARY KEY (`id`)) ENGINE=InnoDB DEFAULT CHARSET=utf8""")

    def test_table_comment(self):
        """Test REGEX_TABLE_COMMENT Table comment"""
        table = """CREATE TABLE `person` (`id` int(10) unsigned NOT NULL AUTO_INCREMENT, `first_name` varchar(100) NOT NULL,`last_name` varchar(100) NOT NULL,`created` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',PRIMARY KEY (`id`)) ENGINE=InnoDB COMMENT 'table comment' DEFAULT CHARSET=utf8"""
        (sql, count) = re.subn(REGEX_TABLE_COMMENT, '', table)
        self.assertEqual(count, 1)
        self.assertEqual(sql, """CREATE TABLE `person` (`id` int(10) unsigned NOT NULL AUTO_INCREMENT, `first_name` varchar(100) NOT NULL,`last_name` varchar(100) NOT NULL,`created` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',PRIMARY KEY (`id`)) ENGINE=InnoDB  DEFAULT CHARSET=utf8""")

    def test_multiple_column_comment_with_table_comment(self):
        """Test REGEX_TABLE_COMMENT multiple column comments and the Table comment"""
        table = """CREATE TABLE `person` (`id` int(10) unsigned NOT NULL AUTO_INCREMENT, `first_name` varchar(100) NOT NULL COMMENT 'this is your first name',`last_name` varchar(100) NOT NULL COMMENT='this is your last name',`created` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',PRIMARY KEY (`id`)) ENGINE=InnoDB COMMENT 'table comment' DEFAULT CHARSET=utf8"""
        (sql, count) = REGEX_TABLE_COMMENT.subn('', table)
        self.assertEqual(count, 3)
        self.assertEqual(sql, """CREATE TABLE `person` (`id` int(10) unsigned NOT NULL AUTO_INCREMENT, `first_name` varchar(100) NOT NULL ,`last_name` varchar(100) NOT NULL ,`created` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',PRIMARY KEY (`id`)) ENGINE=InnoDB  DEFAULT CHARSET=utf8""")

    def test_no_comments(self):
        """Test REGEX_TABLE_COMMENT no comments"""
        table = """CREATE TABLE `person` (`id` int(10) unsigned NOT NULL AUTO_INCREMENT, `first_name` varchar(100) NOT NULL,`last_name` varchar(100) NOT NULL,`created` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',PRIMARY KEY (`id`)) ENGINE=InnoDB DEFAULT CHARSET=utf8"""
        (sql, count) = REGEX_TABLE_COMMENT.subn('', table)
        self.assertEqual(count, 0)
        self.assertEqual(sql, table)


class TestTableAutoIncrementRegex(unittest.TestCase):

    def test_auto_inc_regex_space_seperator(self):
        """Test REGEX_TABLE_AUTO_INC table option AUTO_INCREMENT 1"""
        table = """CREATE TABLE `person` (`id` int(10) unsigned NOT NULL AUTO_INCREMENT, `first_name` varchar(100) NOT NULL COMMENT 'this is your first name',`last_name` varchar(100) NOT NULL,`created` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',PRIMARY KEY (`id`)) AUTO_INCREMENT 1 ENGINE=InnoDB DEFAULT CHARSET=utf8"""
        (sql, count) = REGEX_TABLE_AUTO_INC.subn('', table)
        self.assertEqual(count, 1)
        self.assertEqual(sql, """CREATE TABLE `person` (`id` int(10) unsigned NOT NULL AUTO_INCREMENT, `first_name` varchar(100) NOT NULL COMMENT 'this is your first name',`last_name` varchar(100) NOT NULL,`created` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',PRIMARY KEY (`id`))  ENGINE=InnoDB DEFAULT CHARSET=utf8""")

    def test_auto_inc_regex_space_seperator_with_multiple_spaces(self):
        """Test REGEX_TABLE_AUTO_INC table option AUTO_INCREMENT   1"""
        table = """CREATE TABLE `person` (`id` int(10) unsigned NOT NULL AUTO_INCREMENT, `first_name` varchar(100) NOT NULL COMMENT 'this is your first name',`last_name` varchar(100) NOT NULL,`created` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',PRIMARY KEY (`id`)) AUTO_INCREMENT   1 ENGINE=InnoDB DEFAULT CHARSET=utf8"""
        (sql, count) = REGEX_TABLE_AUTO_INC.subn('', table)
        self.assertEqual(count, 1)
        self.assertEqual(sql, """CREATE TABLE `person` (`id` int(10) unsigned NOT NULL AUTO_INCREMENT, `first_name` varchar(100) NOT NULL COMMENT 'this is your first name',`last_name` varchar(100) NOT NULL,`created` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',PRIMARY KEY (`id`))  ENGINE=InnoDB DEFAULT CHARSET=utf8""")

    def test_auto_inc_regex_equals_seperator(self):
        """Test REGEX_TABLE_AUTO_INC table option AUTO_INCREMENT=1"""
        table = """CREATE TABLE `person` (`id` int(10) unsigned NOT NULL AUTO_INCREMENT, `first_name` varchar(100) NOT NULL COMMENT 'this is your first name',`last_name` varchar(100) NOT NULL,`created` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',PRIMARY KEY (`id`)) AUTO_INCREMENT=1 ENGINE=InnoDB DEFAULT CHARSET=utf8"""
        (sql, count) = REGEX_TABLE_AUTO_INC.subn('', table)
        self.assertEqual(count, 1)
        self.assertEqual(sql, """CREATE TABLE `person` (`id` int(10) unsigned NOT NULL AUTO_INCREMENT, `first_name` varchar(100) NOT NULL COMMENT 'this is your first name',`last_name` varchar(100) NOT NULL,`created` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',PRIMARY KEY (`id`))  ENGINE=InnoDB DEFAULT CHARSET=utf8""")

    def test_auto_inc_regex_equals_seperator_with_spaces(self):
        """Test REGEX_TABLE_AUTO_INC table option AUTO_INCREMENT = 1"""
        table = """CREATE TABLE `person` (`id` int(10) unsigned NOT NULL AUTO_INCREMENT, `first_name` varchar(100) NOT NULL COMMENT 'this is your first name',`last_name` varchar(100) NOT NULL,`created` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',PRIMARY KEY (`id`)) AUTO_INCREMENT  =  1 ENGINE=InnoDB DEFAULT CHARSET=utf8"""
        (sql, count) = REGEX_TABLE_AUTO_INC.subn('', table)
        self.assertEqual(count, 1)
        self.assertEqual(sql, """CREATE TABLE `person` (`id` int(10) unsigned NOT NULL AUTO_INCREMENT, `first_name` varchar(100) NOT NULL COMMENT 'this is your first name',`last_name` varchar(100) NOT NULL,`created` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',PRIMARY KEY (`id`))  ENGINE=InnoDB DEFAULT CHARSET=utf8""")

    def test_auto_inc_regex_case_insensitive(self):
        """Test REGEX_TABLE_AUTO_INC table option auto_increment=1"""
        table = """CREATE TABLE `person` (`id` int(10) unsigned NOT NULL AUTO_INCREMENT, `first_name` varchar(100) NOT NULL COMMENT 'this is your first name',`last_name` varchar(100) NOT NULL,`created` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',PRIMARY KEY (`id`)) auto_increment=1 ENGINE=InnoDB DEFAULT CHARSET=utf8"""
        (sql, count) = REGEX_TABLE_AUTO_INC.subn('', table)
        self.assertEqual(count, 1)
        self.assertEqual(sql, """CREATE TABLE `person` (`id` int(10) unsigned NOT NULL AUTO_INCREMENT, `first_name` varchar(100) NOT NULL COMMENT 'this is your first name',`last_name` varchar(100) NOT NULL,`created` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',PRIMARY KEY (`id`))  ENGINE=InnoDB DEFAULT CHARSET=utf8""")


class TestMultiSpaceRegex(unittest.TestCase):

    def test_multiple_spaces_in_string(self):
        """Test REGEX_MULTI_SPACE in string"""
        s = "hello,  world."
        matches = REGEX_MULTI_SPACE.findall(s)
        self.assertTrue(matches)
        self.assertEqual(matches, [' ' * 2])

    def test_multiple_spaces_leading_string(self):
        """Test REGEX_MULTI_SPACE leading string"""
        s = "     hello, world."
        matches = REGEX_MULTI_SPACE.findall(s)
        self.assertTrue(matches)
        self.assertEqual(matches, [' ' * 5])

    def test_multiple_spaces_trailing_string(self):
        """Test REGEX_MULTI_SPACE trailing string"""
        s = "hello, world.   "
        matches = REGEX_MULTI_SPACE.findall(s)
        self.assertTrue(matches)
        self.assertEqual(matches, [' ' * 3])

    def test_no_match(self):
        """Test REGEX_MULTI_SPACE no match"""
        s = "hello, world."
        matches = REGEX_MULTI_SPACE.findall(s)
        self.assertFalse(matches)


class TestDistantSemiColonRegex(unittest.TestCase):

    def test_single_space(self):
        """Test REGEX_DISTANT_SEMICOLIN with single space"""
        s = "CREATE DATABSE foobar ;"
        matches = REGEX_DISTANT_SEMICOLIN.search(s)
        self.assertTrue(matches)

    def test_multiple_spaces(self):
        """Test REGEX_DISTANT_SEMICOLIN with multiple spaces"""
        s = "CREATE DATABSE foobar    ;"
        matches = REGEX_DISTANT_SEMICOLIN.search(s)
        self.assertTrue(matches)

    def test_tabs(self):
        """Test REGEX_DISTANT_SEMICOLIN with tabs"""
        s = "CREATE DATABSE foobar      ;"
        matches = REGEX_DISTANT_SEMICOLIN.search(s)
        self.assertTrue(matches)

    def test_newline(self):
        """Test REGEX_DISTANT_SEMICOLIN with newline"""
        s = """CREATE DATABSE foobar
        ;"""
        matches = REGEX_DISTANT_SEMICOLIN.search(s)
        self.assertTrue(matches)

    def test_ignore_in_string(self):
        """Test REGEX_DISTANT_SEMICOLIN ignore when in string"""
        s = """ALTER TABLE `foo` COMMENT 'hello  ;'  ;"""
        matches = REGEX_DISTANT_SEMICOLIN.findall(s)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches, ['  ;'])
        
        s = """ALTER TABLE `foo` COMMENT 'hello  ;';"""
        matches = REGEX_DISTANT_SEMICOLIN.findall(s)
        self.assertFalse(matches)
            
    def test_no_match(self):
        """Test REGEX_DISTANT_SEMICOLIN with no spaces"""
        s = "CREATE DATABSE foobar;"
        matches = REGEX_DISTANT_SEMICOLIN.search(s)
        self.assertFalse(matches)

class TestFileCounterRegex(unittest.TestCase):

    def test_valid_numeric_matches_zero(self):
        """ Test REGEX_FILE_COUNTER valid numeric match 0"""
        test_str = "file_0.txt"
        matches = REGEX_FILE_COUNTER.search(test_str)
        self.assertTrue(matches)
        self.assertEqual(matches.group('i'), '0')

    def test_valid_numeric_matches_single_digit(self):
        """ Test REGEX_FILE_COUNTER valid numeric match 1 digit"""
        test_str = "file_8.txt"
        matches = REGEX_FILE_COUNTER.search(test_str)
        self.assertTrue(matches)
        self.assertEqual(matches.group('i'), '8')

    def test_valid_numeric_matches_two_digits(self):
        """ Test REGEX_FILE_COUNTER valid numeric match 2 digits"""
        test_str = "file_16.txt"
        matches = REGEX_FILE_COUNTER.search(test_str)
        self.assertTrue(matches)
        self.assertEqual(matches.group('i'), '16')

    def test_valid_numeric_matches_three_digit(self):
        """ Test REGEX_FILE_COUNTER valid numeric match 3 digits"""
        test_str = "file_256.txt"
        matches = REGEX_FILE_COUNTER.search(test_str)
        self.assertTrue(matches)
        self.assertEqual(matches.group('i'), '256')

    def test_valid_numeric_matches_four_digit(self):
        """ Test REGEX_FILE_COUNTER valid numeric match 4 digits"""
        test_str = "file_1024.txt"
        matches = REGEX_FILE_COUNTER.search(test_str)
        self.assertTrue(matches)
        self.assertEqual(matches.group('i'), '1024')

    def test_sequence_simple(self):
        """ Test REGEX_FILE_COUNTER simplest valid sequence"""
        test_str = "_1.txt"
        matches = REGEX_FILE_COUNTER.search(test_str)
        self.assertTrue(matches)
        self.assertEqual(matches.group('i'), '1')

    def test_sequence_repeated(self):
        """ Test REGEX_FILE_COUNTER repeated in sequence"""
        test_str = "hello_1._3.txt"
        matches = REGEX_FILE_COUNTER.findall(test_str)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches, ['3',])

    def test_sequence_underscore_ext(self):
        """ Test REGEX_FILE_COUNTER extention with underscore"""
        test_str = "hello_3._txt"
        matches = REGEX_FILE_COUNTER.findall(test_str)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches, ['3',])

    def test_sequence_numeric_ext_with_underscore(self):
        """ Test REGEX_FILE_COUNTER numeric extention with underscore"""
        test_str = "hello_3._123"
        matches = REGEX_FILE_COUNTER.findall(test_str)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches, ['3',])

    def test_no_match_invlaid_extention(self):
        """Test REGEX_FILE_COUNTER no match: invalid extention"""
        test_str = "_1."
        matches = REGEX_FILE_COUNTER.search(test_str)
        self.assertFalse(matches)

    def test_no_match_missing_sequence(self):
        """Test REGEX_FILE_COUNTER no match: missing sequence"""
        test_str = "file.txt"
        matches = REGEX_FILE_COUNTER.search(test_str)
        self.assertFalse(matches)

    def test_no_match_invalid_sequence(self):
        """Test REGEX_FILE_COUNTER no match: invalid sequence"""
        test_str = "file1.txt"
        matches = REGEX_FILE_COUNTER.search(test_str)
        self.assertFalse(matches)

    def test_no_match_sequence_not_at_end(self):
        """Test REGEX_FILE_COUNTER no match: sequence must be before extention"""
        test_str = "hello_3.x_x.txt"
        matches = REGEX_FILE_COUNTER.findall(test_str)
        self.assertFalse(matches)

if __name__ == '__main__':
    unittest.main()
########NEW FILE########
__FILENAME__ = test_sync_columns
#!/usr/bin/python
import unittest
import schemaobject
from schemasync import syncdb

class TestSyncColumns(unittest.TestCase):

    def setUp(self):
        self.schema = schemaobject.SchemaObject(self.database_url + 'sakila')
        self.src = self.schema.selected.tables['rental']

        self.schema2 = schemaobject.SchemaObject(self.database_url + 'sakila')
        self.dest = self.schema2.selected.tables['rental']

    def test_get_previous_item(self):
        """Test get previous item from Column list"""
        lst = ['bobby tables', 'jack', 'jill']
        self.assertEqual('jack', syncdb.get_previous_item(lst, 'jill'))
        self.assertEqual('bobby tables', syncdb.get_previous_item(lst, 'jack'))
        self.assertEqual(None, syncdb.get_previous_item(lst, 'bobby tables'))
        self.assertEqual(None, syncdb.get_previous_item(lst, 'jeff'))

    def test_sync_created_column(self):
        """Test: src table has columns not in dest table (ignore Column COMMENT)"""
        saved = self.dest.columns['staff_id']
        pos = self.dest.columns.index('staff_id')
        del self.dest.columns['staff_id']

        for i, (p,r) in enumerate(syncdb.sync_created_columns(self.src.columns, self.dest.columns, sync_comments=False)):
            self.assertEqual(p, "ADD COLUMN `staff_id` TINYINT(3) UNSIGNED NOT NULL AFTER `return_date`")
            self.assertEqual(r, "DROP COLUMN `staff_id`")

        self.assertEqual(i, 0)

    def test_sync_created_column_with_comments(self):
        """Test: src table has columns not in dest table (include Column COMMENT)"""
        saved = self.dest.columns['staff_id']
        pos = self.dest.columns.index('staff_id')
        del self.dest.columns['staff_id']

        self.src.columns['staff_id'].comment = "hello world"

        for i, (p,r) in enumerate(syncdb.sync_created_columns(self.src.columns, self.dest.columns, sync_comments=True)):
            self.assertEqual(p, "ADD COLUMN `staff_id` TINYINT(3) UNSIGNED NOT NULL COMMENT 'hello world' AFTER `return_date`")
            self.assertEqual(r, "DROP COLUMN `staff_id`")

        self.assertEqual(i, 0)

    def test_sync_dropped_column(self):
        """Test: dest table has columns not in src table (ignore Column COMMENT)"""
        saved = self.src.columns['staff_id']
        pos = self.src.columns.index('staff_id')
        del self.src.columns['staff_id']

        for i, (p,r) in enumerate(syncdb.sync_dropped_columns(self.src.columns, self.dest.columns, sync_comments=False)):
            self.assertEqual(p, "DROP COLUMN `staff_id`")
            self.assertEqual(r, "ADD COLUMN `staff_id` TINYINT(3) UNSIGNED NOT NULL AFTER `return_date`")

        self.assertEqual(i, 0)

    def test_sync_dropped_column_with_comment(self):
        """Test: dest table has columns not in src table (include Column COMMENT)"""
        saved = self.src.columns['staff_id']
        pos = self.src.columns.index('staff_id')
        del self.src.columns['staff_id']

        self.dest.columns['staff_id'].comment = "hello world"

        for i, (p,r) in enumerate(syncdb.sync_dropped_columns(self.src.columns, self.dest.columns, sync_comments=True)):
            self.assertEqual(p, "DROP COLUMN `staff_id`")
            self.assertEqual(r, "ADD COLUMN `staff_id` TINYINT(3) UNSIGNED NOT NULL COMMENT 'hello world' AFTER `return_date`")

        self.assertEqual(i, 0)

    def test_sync_modified_column(self):
        """Test: column in src table have been modified in dest table (ignore Column COMMENT)"""
        self.dest.columns['rental_date'].type = "TEXT"
        self.dest.columns['rental_date'].null = True
        self.dest.columns['rental_date'].comment = "hello world"

        for i, (p,r) in enumerate(syncdb.sync_modified_columns(self.src.columns, self.dest.columns, sync_comments=False)):
            self.assertEqual(p, "MODIFY COLUMN `rental_date` DATETIME NOT NULL AFTER `rental_id`")
            self.assertEqual(r, "MODIFY COLUMN `rental_date` TEXT NULL AFTER `rental_id`")

        self.assertEqual(i, 0)

    def test_sync_multiple_modified_columns(self):
        """Test: multiple columns in src table have been modified in dest table (ignore Column COMMENT)"""
        self.dest.columns['rental_date'].type = "TEXT"
        self.dest.columns['rental_date'].null = True
        self.dest.columns['rental_date'].comment = "hello world"
        self.dest.columns['return_date'].type = "TIMESTAMP"
        
        for i, (p,r) in enumerate(syncdb.sync_modified_columns(self.src.columns, self.dest.columns, sync_comments=False)):
            if i == 0:
                self.assertEqual(p, "MODIFY COLUMN `rental_date` DATETIME NOT NULL AFTER `rental_id`")
                self.assertEqual(r, "MODIFY COLUMN `rental_date` TEXT NULL AFTER `rental_id`")
            if i == 1:
                self.assertEqual(p, "MODIFY COLUMN `return_date` DATETIME NULL AFTER `customer_id`")
                self.assertEqual(r, "MODIFY COLUMN `return_date` TIMESTAMP NULL AFTER `customer_id`")

        self.assertEqual(i, 1)
            
    def test_sync_modified_column_with_comments(self):
        """Test: columns in src table have been modified in dest table (include Column COMMENT)"""
        self.dest.columns['rental_date'].type = "TEXT"
        self.dest.columns['rental_date'].null = True
        self.dest.columns['rental_date'].comment = "hello world"

        for i, (p,r) in enumerate(syncdb.sync_modified_columns(self.src.columns, self.dest.columns, sync_comments=True)):
            self.assertEqual(r, "MODIFY COLUMN `rental_date` TEXT NULL COMMENT 'hello world' AFTER `rental_id`")
            self.assertEqual(p, "MODIFY COLUMN `rental_date` DATETIME NOT NULL AFTER `rental_id`")

        self.assertEqual(i, 0)

    def test_move_col_to_end_in_dest(self):
        """Move a column in the dest table towards the end of the column list"""

        tmp = self.dest.columns._sequence[1]
        self.dest.columns._sequence.remove(tmp)
        self.dest.columns._sequence.insert(5, tmp)

        for i, (p,r) in enumerate(syncdb.sync_modified_columns(self.src.columns, self.dest.columns, sync_comments=True)):
            if i == 0:
                self.assertEqual(p, "MODIFY COLUMN `rental_date` DATETIME NOT NULL AFTER `rental_id`")
                self.assertEqual(r, "MODIFY COLUMN `rental_date` DATETIME NOT NULL AFTER `staff_id`")

        self.assertEqual(i, 0)

    def test_move_col_to_beg_in_dest(self):
        """Move a column in the dest table towards the begining of the column list"""

        tmp = self.dest.columns._sequence[4]
        self.dest.columns._sequence.remove(tmp)
        self.dest.columns._sequence.insert(1, tmp)

        for i, (p,r) in enumerate(syncdb.sync_modified_columns(self.src.columns, self.dest.columns, sync_comments=True)):
            if i == 0:
                self.assertEqual(p, "MODIFY COLUMN `return_date` DATETIME NULL AFTER `customer_id`")
                self.assertEqual(r, "MODIFY COLUMN `return_date` DATETIME NULL AFTER `rental_id`")

        self.assertEqual(i, 0)

    def test_swap_two_cols_in_dest(self):
        """Swap the position of 2 columns in the dest table"""

        self.dest.columns._sequence[1], self.dest.columns._sequence[5] = self.dest.columns._sequence[5], self.dest.columns._sequence[1]

        for i, (p,r) in enumerate(syncdb.sync_modified_columns(self.src.columns, self.dest.columns, sync_comments=True)):
            if i == 0:
                self.assertEqual(p, "MODIFY COLUMN `rental_date` DATETIME NOT NULL AFTER `rental_id`")
                self.assertEqual(r, "MODIFY COLUMN `rental_date` DATETIME NOT NULL AFTER `return_date`")
            if i == 1:
                self.assertEqual(p, "MODIFY COLUMN `staff_id` TINYINT(3) UNSIGNED NOT NULL AFTER `return_date`")
                self.assertEqual(r, "MODIFY COLUMN `staff_id` TINYINT(3) UNSIGNED NOT NULL AFTER `rental_id`")

        self.assertEqual(i, 1)

    def test_swap_pairs_of_cols_in_dest(self):
        """Swap the position of 2 pairs of columns in the dest table"""

        a,b = self.dest.columns._sequence[1], self.dest.columns._sequence[2]
        self.dest.columns._sequence[1], self.dest.columns._sequence[2] = self.dest.columns._sequence[4], self.dest.columns._sequence[5]
        self.dest.columns._sequence[4], self.dest.columns._sequence[5] = a,b

        for i, (p,r) in enumerate(syncdb.sync_modified_columns(self.src.columns, self.dest.columns, sync_comments=True)):
            if i == 0:
                self.assertEqual(p, "MODIFY COLUMN `rental_date` DATETIME NOT NULL AFTER `rental_id`")
                self.assertEqual(r, "MODIFY COLUMN `rental_date` DATETIME NOT NULL AFTER `customer_id`")
            if i == 1:
                self.assertEqual(p, "MODIFY COLUMN `inventory_id` MEDIUMINT(8) UNSIGNED NOT NULL AFTER `rental_date`")
                self.assertEqual(r, "MODIFY COLUMN `inventory_id` MEDIUMINT(8) UNSIGNED NOT NULL AFTER `rental_date`")
            if i == 2:
                self.assertEqual(p, "MODIFY COLUMN `customer_id` SMALLINT(5) UNSIGNED NOT NULL AFTER `inventory_id`")
                self.assertEqual(r, "MODIFY COLUMN `customer_id` SMALLINT(5) UNSIGNED NOT NULL AFTER `staff_id`")

        self.assertEqual(i, 2)

    def test_move_3_cols_in_dest(self):
        """Move around 3 columns in the dest table"""

        self.dest.columns._sequence[0], self.dest.columns._sequence[3] = self.dest.columns._sequence[3], self.dest.columns._sequence[0]
        tmp = self.dest.columns._sequence[1]
        self.dest.columns._sequence.remove(tmp)
        self.dest.columns._sequence.insert(2, tmp)

        for i, (p,r) in enumerate(syncdb.sync_modified_columns(self.src.columns, self.dest.columns, sync_comments=True)):
            if i == 0:
                self.assertEqual(p, "MODIFY COLUMN `rental_id` INT(11) NOT NULL auto_increment FIRST")
                self.assertEqual(r, "MODIFY COLUMN `rental_id` INT(11) NOT NULL auto_increment AFTER `rental_date`")
            if i == 1:
                self.assertEqual(p, "MODIFY COLUMN `rental_date` DATETIME NOT NULL AFTER `rental_id`")
                self.assertEqual(r, "MODIFY COLUMN `rental_date` DATETIME NOT NULL AFTER `inventory_id`")
            if i == 2:
                self.assertEqual(p, "MODIFY COLUMN `inventory_id` MEDIUMINT(8) UNSIGNED NOT NULL AFTER `rental_date`")
                self.assertEqual(r, "MODIFY COLUMN `inventory_id` MEDIUMINT(8) UNSIGNED NOT NULL AFTER `customer_id`")

        self.assertEqual(i, 2)


    def test_move_col_to_end_in_src(self):
        """Move a column in the dest table towards the end of the column list"""

        tmp = self.src.columns._sequence[1]
        self.src.columns._sequence.remove(tmp)
        self.src.columns._sequence.insert(5, tmp)

        for i, (p,r) in enumerate(syncdb.sync_modified_columns(self.src.columns, self.dest.columns, sync_comments=True)):
            if i == 0:
                self.assertEqual(p, "MODIFY COLUMN `rental_date` DATETIME NOT NULL AFTER `staff_id`")
                self.assertEqual(r, "MODIFY COLUMN `rental_date` DATETIME NOT NULL AFTER `rental_id`")

        self.assertEqual(i, 0)

    def test_move_col_to_beg_in_src(self):
        """Move a column in the dest table towards the begining of the column list"""

        tmp = self.src.columns._sequence[4]
        self.src.columns._sequence.remove(tmp)
        self.src.columns._sequence.insert(1, tmp)

        for i, (p,r) in enumerate(syncdb.sync_modified_columns(self.src.columns, self.dest.columns, sync_comments=True)):
            if i == 0:
                self.assertEqual(p, "MODIFY COLUMN `return_date` DATETIME NULL AFTER `rental_id`")
                self.assertEqual(r, "MODIFY COLUMN `return_date` DATETIME NULL AFTER `customer_id`")

        self.assertEqual(i, 0)

    def test_swap_two_cols_in_src(self):
        """Swap the position of 2 columns in the dest table"""

        self.src.columns._sequence[1], self.src.columns._sequence[5] = self.src.columns._sequence[5], self.src.columns._sequence[1]

        for i, (p,r) in enumerate(syncdb.sync_modified_columns(self.src.columns, self.dest.columns, sync_comments=True)):
            if i == 0:
                self.assertEqual(p, "MODIFY COLUMN `staff_id` TINYINT(3) UNSIGNED NOT NULL AFTER `rental_id`")
                self.assertEqual(r, "MODIFY COLUMN `staff_id` TINYINT(3) UNSIGNED NOT NULL AFTER `return_date`")

            if i == 1:
                self.assertEqual(p, "MODIFY COLUMN `rental_date` DATETIME NOT NULL AFTER `return_date`")
                self.assertEqual(r, "MODIFY COLUMN `rental_date` DATETIME NOT NULL AFTER `rental_id`")


        self.assertEqual(i, 1)

    def test_move_3_cols_in_src(self):
        """Move around 3 columns in the dest table"""

        self.src.columns._sequence[0], self.src.columns._sequence[3] = self.src.columns._sequence[3], self.src.columns._sequence[0]
        tmp = self.src.columns._sequence[1]
        self.src.columns._sequence.remove(tmp)
        self.src.columns._sequence.insert(2, tmp)

        for i, (p,r) in enumerate(syncdb.sync_modified_columns(self.src.columns, self.dest.columns, sync_comments=True)):
            if i == 0:
                self.assertEqual(p, "MODIFY COLUMN `customer_id` SMALLINT(5) UNSIGNED NOT NULL FIRST")
                self.assertEqual(r, "MODIFY COLUMN `customer_id` SMALLINT(5) UNSIGNED NOT NULL AFTER `inventory_id`")

            if i == 1:
                self.assertEqual(p, "MODIFY COLUMN `inventory_id` MEDIUMINT(8) UNSIGNED NOT NULL AFTER `customer_id`")
                self.assertEqual(r, "MODIFY COLUMN `inventory_id` MEDIUMINT(8) UNSIGNED NOT NULL AFTER `rental_date`")

            if i == 2:
                self.assertEqual(p, "MODIFY COLUMN `rental_date` DATETIME NOT NULL AFTER `inventory_id`")
                self.assertEqual(r, "MODIFY COLUMN `rental_date` DATETIME NOT NULL AFTER `rental_id`")

        self.assertEqual(i, 2)
if __name__ == "__main__":
    from test_all import get_database_url
    TestSyncColumns.database_url = get_database_url()
    unittest.main()
########NEW FILE########
__FILENAME__ = test_sync_constraints
#!/usr/bin/python
import unittest
import schemaobject
from schemasync import syncdb

class TestSyncConstraints(unittest.TestCase):

    def setUp(self):

        self.schema = schemaobject.SchemaObject(self.database_url + 'sakila')
        self.src = self.schema.selected.tables['rental']

        self.schema2 = schemaobject.SchemaObject(self.database_url + 'sakila')
        self.dest = self.schema2.selected.tables['rental']

    def test_sync_created_index(self):
        """Test: src table has indexes not in dest table"""
        saved = self.dest.indexes['idx_fk_customer_id']
        pos = self.dest.indexes.index('idx_fk_customer_id')
        del self.dest.indexes['idx_fk_customer_id']

        for i, (p,r) in enumerate(syncdb.sync_created_constraints(self.src.indexes, self.dest.indexes)):
            self.assertEqual(p, "ADD INDEX `idx_fk_customer_id` (`customer_id`) USING BTREE")
            self.assertEqual(r, "DROP INDEX `idx_fk_customer_id`")

        self.assertEqual(i, 0)

    def test_sync_dropped_index(self):
        """Test: dest table has indexes not in src table"""
        saved = self.src.indexes['idx_fk_customer_id']
        pos = self.dest.indexes.index('idx_fk_customer_id')
        del self.src.indexes['idx_fk_customer_id']

        for i, (p,r) in enumerate(syncdb.sync_dropped_constraints(self.src.indexes, self.dest.indexes)):
            self.assertEqual(p, "DROP INDEX `idx_fk_customer_id`")
            self.assertEqual(r, "ADD INDEX `idx_fk_customer_id` (`customer_id`) USING BTREE")

        self.assertEqual(i, 0)

    def test_sync_modified_index(self):
        """Test: src table has indexes modified in dest table"""
        self.dest.indexes['idx_fk_customer_id'].kind = "UNIQUE"
        self.dest.indexes['idx_fk_customer_id'].fields = [('inventory_id', 0)]

        for i, (p,r) in enumerate(syncdb.sync_modified_constraints(self.src.indexes, self.dest.indexes)):
            if i==0:
                self.assertEqual(p, "DROP INDEX `idx_fk_customer_id`")
                self.assertEqual(r, "DROP INDEX `idx_fk_customer_id`")
            if i==1:
                self.assertEqual(p, "ADD INDEX `idx_fk_customer_id` (`customer_id`) USING BTREE")
                self.assertEqual(r, "ADD UNIQUE INDEX `idx_fk_customer_id` (`inventory_id`) USING BTREE")

        self.assertEqual(i, 1)

    def test_sync_created_fk(self):
        """Test: src table has foreign keys not in dest table"""
        saved = self.dest.foreign_keys['fk_rental_customer']
        pos = self.dest.foreign_keys.index('fk_rental_customer')
        del self.dest.foreign_keys['fk_rental_customer']

        for i, (p,r) in enumerate(syncdb.sync_created_constraints(self.src.foreign_keys, self.dest.foreign_keys)):
            self.assertEqual(p, "ADD CONSTRAINT `fk_rental_customer` FOREIGN KEY `fk_rental_customer` (`customer_id`) REFERENCES `customer` (`customer_id`) ON DELETE RESTRICT ON UPDATE CASCADE")
            self.assertEqual(r, "DROP FOREIGN KEY `fk_rental_customer`")

        self.assertEqual(i, 0)

    def test_sync_dropped_fk(self):
        """Test: dest table has foreign keys not in src table"""
        saved = self.src.foreign_keys['fk_rental_customer']
        pos = self.dest.foreign_keys.index('fk_rental_customer')
        del self.src.foreign_keys['fk_rental_customer']

        for i, (p,r) in enumerate(syncdb.sync_dropped_constraints(self.src.foreign_keys, self.dest.foreign_keys)):
            self.assertEqual(p, "DROP FOREIGN KEY `fk_rental_customer`")
            self.assertEqual(r, "ADD CONSTRAINT `fk_rental_customer` FOREIGN KEY `fk_rental_customer` (`customer_id`) REFERENCES `customer` (`customer_id`) ON DELETE RESTRICT ON UPDATE CASCADE")

        self.assertEqual(i, 0)

    def test_sync_modified_fk(self):
        """Test: src table has foreign keys modified in dest table"""
        self.dest.foreign_keys['fk_rental_customer'].delete_rule = "SET NULL"

        for i, (p,r) in enumerate(syncdb.sync_modified_constraints(self.src.foreign_keys, self.dest.foreign_keys)):
            if i==0:
                self.assertEqual(p, "DROP FOREIGN KEY `fk_rental_customer`")
                self.assertEqual(r, "DROP FOREIGN KEY `fk_rental_customer`")
            if i==1:
                self.assertEqual(p, "ADD CONSTRAINT `fk_rental_customer` FOREIGN KEY `fk_rental_customer` (`customer_id`) REFERENCES `customer` (`customer_id`) ON DELETE RESTRICT ON UPDATE CASCADE")
                self.assertEqual(r, "ADD CONSTRAINT `fk_rental_customer` FOREIGN KEY `fk_rental_customer` (`customer_id`) REFERENCES `customer` (`customer_id`) ON DELETE SET NULL ON UPDATE CASCADE")

        self.assertEqual(i, 1)

if __name__ == "__main__":
    from test_all import get_database_url
    TestSyncConstraints.database_url = get_database_url()
    unittest.main()
########NEW FILE########
__FILENAME__ = test_sync_database
#!/usr/bin/python
import unittest
import schemaobject
from schemasync import syncdb

class TestSyncDatabase(unittest.TestCase):

    def setUp(self):
        self.schema = schemaobject.SchemaObject(self.database_url + 'sakila')
        self.src = self.schema.selected

        self.schema2 = schemaobject.SchemaObject(self.database_url + 'sakila')
        self.dest = self.schema2.selected

    def test_database_options(self):
        """Test: src and dest database options are different"""
        self.src.options['charset'].value = "utf8"
        self.src.options['collation'].value = "utf8_general_ci"

        p,r = syncdb.sync_database_options(self.src, self.dest)
        self.assertEqual(p, "CHARACTER SET=utf8 COLLATE=utf8_general_ci")
        self.assertEqual(r, "CHARACTER SET=latin1 COLLATE=latin1_swedish_ci")


if __name__ == "__main__":
    from test_all import get_database_url
    TestSyncDatabase.database_url = get_database_url()
    unittest.main()
########NEW FILE########
__FILENAME__ = test_sync_tables
#!/usr/bin/python
import unittest
import schemaobject
from schemasync import syncdb

class TestSyncTables(unittest.TestCase):

    def setUp(self):
        self.schema = schemaobject.SchemaObject(self.database_url + 'sakila')
        self.src = self.schema.selected

        self.schema2 = schemaobject.SchemaObject(self.database_url + 'sakila')
        self.dest = self.schema2.selected


    def test_created_tables(self):
        """Test: src db has tables not in dest db"""
        saved = self.dest.tables['rental']
        pos = self.dest.tables.index('rental')
        del self.dest.tables['rental']

        for i, (p, r) in enumerate(syncdb.sync_created_tables(self.src.tables, self.dest.tables)):
            self.assertEqual(p, "CREATE TABLE `rental` ( `rental_id` int(11) NOT NULL AUTO_INCREMENT, `rental_date` datetime NOT NULL, `inventory_id` mediumint(8) unsigned NOT NULL, `customer_id` smallint(5) unsigned NOT NULL, `return_date` datetime DEFAULT NULL, `staff_id` tinyint(3) unsigned NOT NULL, `last_update` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, PRIMARY KEY (`rental_id`), UNIQUE KEY `rental_date` (`rental_date`,`inventory_id`,`customer_id`), KEY `idx_fk_inventory_id` (`inventory_id`), KEY `idx_fk_staff_id` (`staff_id`), KEY `idx_fk_customer_id` (`customer_id`) USING BTREE, CONSTRAINT `fk_rental_customer` FOREIGN KEY (`customer_id`) REFERENCES `customer` (`customer_id`) ON UPDATE CASCADE, CONSTRAINT `fk_rental_inventory` FOREIGN KEY (`inventory_id`) REFERENCES `inventory` (`inventory_id`) ON UPDATE CASCADE, CONSTRAINT `fk_rental_staff` FOREIGN KEY (`staff_id`) REFERENCES `staff` (`staff_id`) ON UPDATE CASCADE) ENGINE=InnoDB DEFAULT CHARSET=utf8;")
            self.assertEqual(r, "DROP TABLE `rental`;")

        self.assertEqual(i, 0)
    
    def test_created_tables_strip_auto_increment(self):
        """Test: src db has tables not in dest db (strip table option auto_increment)"""
        saved = self.dest.tables['rental']
        pos = self.dest.tables.index('rental')
        del self.dest.tables['rental']

        for i, (p, r) in enumerate(syncdb.sync_created_tables(self.src.tables, self.dest.tables, sync_auto_inc=True)):
            self.assertEqual(p, "CREATE TABLE `rental` ( `rental_id` int(11) NOT NULL AUTO_INCREMENT, `rental_date` datetime NOT NULL, `inventory_id` mediumint(8) unsigned NOT NULL, `customer_id` smallint(5) unsigned NOT NULL, `return_date` datetime DEFAULT NULL, `staff_id` tinyint(3) unsigned NOT NULL, `last_update` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, PRIMARY KEY (`rental_id`), UNIQUE KEY `rental_date` (`rental_date`,`inventory_id`,`customer_id`), KEY `idx_fk_inventory_id` (`inventory_id`), KEY `idx_fk_staff_id` (`staff_id`), KEY `idx_fk_customer_id` (`customer_id`) USING BTREE, CONSTRAINT `fk_rental_customer` FOREIGN KEY (`customer_id`) REFERENCES `customer` (`customer_id`) ON UPDATE CASCADE, CONSTRAINT `fk_rental_inventory` FOREIGN KEY (`inventory_id`) REFERENCES `inventory` (`inventory_id`) ON UPDATE CASCADE, CONSTRAINT `fk_rental_staff` FOREIGN KEY (`staff_id`) REFERENCES `staff` (`staff_id`) ON UPDATE CASCADE) ENGINE=InnoDB DEFAULT CHARSET=utf8;")
            self.assertEqual(r, "DROP TABLE `rental`;")

        self.assertEqual(i, 0)
            
    def test_created_tables_strip_comments(self):
        """Test: src db has tables not in dest db (strip comments)"""
        saved = self.dest.tables['rental']
        pos = self.dest.tables.index('rental')
        del self.dest.tables['rental']

        for i, (p, r) in enumerate(syncdb.sync_created_tables(self.src.tables, self.dest.tables, sync_comments=True)):
            self.assertEqual(p, "CREATE TABLE `rental` ( `rental_id` int(11) NOT NULL AUTO_INCREMENT, `rental_date` datetime NOT NULL, `inventory_id` mediumint(8) unsigned NOT NULL, `customer_id` smallint(5) unsigned NOT NULL, `return_date` datetime DEFAULT NULL, `staff_id` tinyint(3) unsigned NOT NULL, `last_update` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, PRIMARY KEY (`rental_id`), UNIQUE KEY `rental_date` (`rental_date`,`inventory_id`,`customer_id`), KEY `idx_fk_inventory_id` (`inventory_id`), KEY `idx_fk_staff_id` (`staff_id`), KEY `idx_fk_customer_id` (`customer_id`) USING BTREE, CONSTRAINT `fk_rental_customer` FOREIGN KEY (`customer_id`) REFERENCES `customer` (`customer_id`) ON UPDATE CASCADE, CONSTRAINT `fk_rental_inventory` FOREIGN KEY (`inventory_id`) REFERENCES `inventory` (`inventory_id`) ON UPDATE CASCADE, CONSTRAINT `fk_rental_staff` FOREIGN KEY (`staff_id`) REFERENCES `staff` (`staff_id`) ON UPDATE CASCADE) ENGINE=InnoDB DEFAULT CHARSET=utf8;")
            self.assertEqual(r, "DROP TABLE `rental`;")

        self.assertEqual(i, 0)
        
    def test_dropped_tables(self):
        """Test: dest db has tables not in src db"""
        saved = self.src.tables['rental']
        pos = self.src.tables.index('rental')
        del self.src.tables['rental']

        for i, (p, r) in enumerate(syncdb.sync_dropped_tables(self.src.tables, self.dest.tables)):
            self.assertEqual(p, "DROP TABLE `rental`;")
            self.assertEqual(r, "CREATE TABLE `rental` ( `rental_id` int(11) NOT NULL AUTO_INCREMENT, `rental_date` datetime NOT NULL, `inventory_id` mediumint(8) unsigned NOT NULL, `customer_id` smallint(5) unsigned NOT NULL, `return_date` datetime DEFAULT NULL, `staff_id` tinyint(3) unsigned NOT NULL, `last_update` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, PRIMARY KEY (`rental_id`), UNIQUE KEY `rental_date` (`rental_date`,`inventory_id`,`customer_id`), KEY `idx_fk_inventory_id` (`inventory_id`), KEY `idx_fk_staff_id` (`staff_id`), KEY `idx_fk_customer_id` (`customer_id`) USING BTREE, CONSTRAINT `fk_rental_customer` FOREIGN KEY (`customer_id`) REFERENCES `customer` (`customer_id`) ON UPDATE CASCADE, CONSTRAINT `fk_rental_inventory` FOREIGN KEY (`inventory_id`) REFERENCES `inventory` (`inventory_id`) ON UPDATE CASCADE, CONSTRAINT `fk_rental_staff` FOREIGN KEY (`staff_id`) REFERENCES `staff` (`staff_id`) ON UPDATE CASCADE) ENGINE=InnoDB DEFAULT CHARSET=utf8;")

        self.assertEqual(i, 0)

    def test_table_options(self):
        """Test: src and dest table have different options"""
        self.src.tables['address'].options['engine'].value = "MyISAM"

        p,r = syncdb.sync_table_options(self.src.tables['address'], self.dest.tables['address'], sync_auto_inc=False, sync_comments=False)
        self.assertEqual(p, "ENGINE=MyISAM")
        self.assertEqual(r, "ENGINE=InnoDB")


    def test_table_options_with_auto_inc(self):
        """Test: src and dest table have different options (include AUTO_INCREMENT value)"""
        self.src.tables['address'].options['engine'].value = "MyISAM"
        self.src.tables['address'].options['auto_increment'].value = 11

        p,r = syncdb.sync_table_options(self.src.tables['address'], self.dest.tables['address'], sync_auto_inc=True, sync_comments=False)
        self.assertEqual(p, "ENGINE=MyISAM AUTO_INCREMENT=11")
        self.assertEqual(r, "ENGINE=InnoDB AUTO_INCREMENT=1")


    def test_table_options_with_comment(self):
        """Test: src and dest table have different options (include table COMMENT)"""
        self.src.tables['address'].options['engine'].value = "MyISAM"
        self.src.tables['address'].options['comment'].value =  "hello world"

        p,r = syncdb.sync_table_options(self.src.tables['address'], self.dest.tables['address'], sync_auto_inc=False, sync_comments=True)
        self.assertEqual(p, "ENGINE=MyISAM COMMENT='hello world'")
        self.assertEqual(r, "ENGINE=InnoDB COMMENT=''" )


if __name__ == "__main__":
    from test_all import get_database_url
    TestSyncTables.database_url = get_database_url()
    unittest.main()
########NEW FILE########
__FILENAME__ = test_utils
#!/usr/bin/python
import unittest
import os
import glob
import datetime
from schemasync.utils import versioned, create_pnames, PatchBuffer


class TestVersioned(unittest.TestCase):
    def setUp(self):
        filename = "/tmp/schemasync_util_testfile.txt"
        self.base_name, self.ext = os.path.splitext(filename)
        files = glob.glob(self.base_name + '*' + self.ext)

        for f in files:
            os.unlink(f)

    def tearDown(self):
        files = glob.glob(self.base_name + '*' + self.ext)

        for f in files:
            os.unlink(f)

    def test_inital_file(self):
        self.assertEqual(self.base_name + self.ext,
                         versioned(self.base_name + self.ext))

    def test_inc_sequence(self):
        open(self.base_name + self.ext, 'w').close()

        self.assertEqual(self.base_name + '_1' + self.ext,
                         versioned(self.base_name + self.ext))

    def test_inc_sequence_incomplete(self):
        open(self.base_name + self.ext, 'w').close()
        open(self.base_name + '_2' + self.ext, 'w').close()

        self.assertEqual(self.base_name + '_3' + self.ext,
                         versioned(self.base_name + self.ext))

    def test_inc_sequence_missing(self):
        open(self.base_name + '_4' + self.ext, 'w').close()

        self.assertEqual(self.base_name + '_5' + self.ext,
                         versioned(self.base_name + self.ext))


class TestPNames(unittest.TestCase):
    def test_no_tag(self):
        d = datetime.datetime.now().strftime("%Y%m%d")
        p = "mydb.%s.patch.sql" % d
        r = "mydb.%s.revert.sql" % d
        self.assertEqual((p,r), create_pnames("mydb", date_format="%Y%m%d"))

    def test_simple_tag(self):
        d = datetime.datetime.now().strftime("%Y%m%d")
        p = "mydb_tag.%s.patch.sql" % d
        r = "mydb_tag.%s.revert.sql" % d
        self.assertEqual((p,r), create_pnames("mydb",tag="tag", date_format="%Y%m%d"))

    def test_alphanumeric_tag(self):
        d = datetime.datetime.now().strftime("%Y%m%d")
        p = "mydb_tag123.%s.patch.sql" % d
        r = "mydb_tag123.%s.revert.sql" % d
        self.assertEqual((p,r), create_pnames("mydb",tag="tag123", date_format="%Y%m%d"))

    def test_tag_with_spaces(self):
        d = datetime.datetime.now().strftime("%Y%m%d")
        p = "mydb_mytag.%s.patch.sql" % d
        r = "mydb_mytag.%s.revert.sql" % d
        self.assertEqual((p,r), create_pnames("mydb",tag="my tag", date_format="%Y%m%d"))

    def test_tag_with_invalid_chars(self):
        d = datetime.datetime.now().strftime("%Y%m%d")
        p = "mydb_tag.%s.patch.sql" % d
        r = "mydb_tag.%s.revert.sql" % d
        self.assertEqual((p,r), create_pnames("mydb",tag="tag!@#$%^&*()+?<>:{},./|\[];", date_format="%Y%m%d"))

    def test_tag_with_valid_chars(self):
        d = datetime.datetime.now().strftime("%Y%m%d")
        p = "mydb_my-tag_123.%s.patch.sql" % d
        r = "mydb_my-tag_123.%s.revert.sql" % d
        self.assertEqual((p,r), create_pnames("mydb",tag="my-tag_123", date_format="%Y%m%d"))


class TestPatchBuffer(unittest.TestCase):

    def setUp(self):
        self.p = PatchBuffer(name="patch.txt",
                             filters=[],
                             tpl="data in this file: %(data)s",
                             ctx={'x':'y'},
                             version_filename=True)

    def tearDown(self):
        if (os.path.isfile(self.p.name)):
            os.unlink(self.p.name)

    def test_loaded(self):
        self.assertEqual("patch.txt", self.p.name)
        self.assertEqual([], self.p.filters)
        self.assertEqual("data in this file: %(data)s", self.p.tpl)
        self.assertEqual({'x':'y'}, self.p.ctx)
        self.assertEqual(True, self.p.version_filename)
        self.assertEqual(False, self.p.modified)

    def test_write(self):
        self.assertEqual(False, self.p.modified)
        self.p.write("hello world")
        self.assertEqual(True, self.p.modified)

    def test_save(self):
        self.assertEqual(False, os.path.isfile(self.p.name))
        self.p.write("hello, world")
        self.p.save()
        self.assertEqual(True, os.path.isfile(self.p.name))
        f= open(self.p.name, 'r')
        self.assertEqual("data in this file: hello, world", f.readline())

    def test_save_versioned(self):
        self.p.version_filename = True
        self.assertEqual(False, os.path.isfile(self.p.name))
        self.p.write("hello, world")

        self.p.save()
        self.assertEqual(self.p.name, "patch.txt")
        self.assertEqual(True, os.path.isfile(self.p.name))
        f= open(self.p.name, 'r')
        self.assertEqual("data in this file: hello, world", f.readline())

        self.p.save()
        self.assertEqual(self.p.name, "patch_1.txt")
        self.assertEqual(True, os.path.isfile(self.p.name))
        f= open(self.p.name, 'r')
        self.assertEqual("data in this file: hello, world", f.readline())

        os.unlink("patch.txt")
        self.assertEqual(False, os.path.isfile("patch.txt"))

        os.unlink("patch_1.txt")
        self.assertEqual(False, os.path.isfile("patch_1.txt"))

    def test_delete(self):
        self.assertEqual(False, os.path.isfile(self.p.name))
        self.p.write("hello, world")
        self.p.save()
        self.assertEqual(self.p.name, "patch.txt")
        self.assertEqual(True, os.path.isfile(self.p.name))
        self.p.delete()
        self.assertEqual(False, os.path.isfile(self.p.name))

if __name__ == "__main__":
    unittest.main()
########NEW FILE########
