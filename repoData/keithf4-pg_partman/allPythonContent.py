__FILENAME__ = check_unique_constraint
#!/usr/bin/env python

import argparse, collections, psycopg2, os, subprocess, sys, tempfile

parser = argparse.ArgumentParser(description="This script is used to check that all rows in a partition set are unique for the given columns. Since unique constraints are not applied across partition sets, this cannot be enforced within the database. This script can be used as a monitor to ensure uniquness. If any unique violations are found, the values, along with a count of each, are output.")
parser.add_argument('-p', '--parent', required=True, help="Parent table of the partition set to be checked")
parser.add_argument('-l', '--column_list', required=True, help="Comma separated list of columns that make up the unique constraint to be checked")
parser.add_argument('-c','--connection', default="host=localhost", help="""Connection string for use by psycopg. Defaults to "host=localhost".""")
parser.add_argument('-t', '--temp', help="Path to a writable folder that can be used for temp working files. Defaults system temp folder.")
parser.add_argument('--psql', help="Full path to psql binary if not in current PATH")
parser.add_argument('--simple', action="store_true", help="Output a single integer value with the total duplicate count. Use this for monitoring software that requires a simple value to be checked for.")
parser.add_argument('--index_scan', action="store_true", help="By default index scans are disabled to force the script to check the actual table data with sequential scans. Set this option if you want the script to allow index scans to be used (does not guarentee that they will be used).")
parser.add_argument('-q', '--quiet', action="store_true", help="Suppress all output unless there is a constraint violation found.")
args = parser.parse_args()

if args.temp == None:
    tmp_copy_file = tempfile.NamedTemporaryFile(prefix="partman_constraint")
else:
    tmp_copy_file = tempfile.NamedTemporaryFile(prefix="partman_constraint", dir=args.temp)

fh = open(tmp_copy_file.name, 'w')
conn = psycopg2.connect(args.connection)
conn.set_session(isolation_level="REPEATABLE READ", readonly=True)
cur = conn.cursor()
if args.index_scan == False:
    sql = """set enable_bitmapscan = false;
    set enable_indexonlyscan = false;
    set enable_indexscan = false;
    set enable_seqscan = true;"""
else:
    sql = """set enable_bitmapscan = true;
    set enable_indexonlyscan = true;
    set enable_indexscan = true;
    set enable_seqscan = false;"""
cur.execute(sql)
cur.close()
cur = conn.cursor()
if not args.quiet:
    print("Dumping out column data to temp file...")
cur.copy_to(fh, args.parent, sep=",", columns=args.column_list.split(","))
conn.rollback()
conn.close()
fh.close()

total_count = 0
if not args.quiet:
    print("Checking for dupes...")
with open(tmp_copy_file.name) as infile:
    counts = collections.Counter(l.strip() for l in infile)
for line, count in counts.most_common():
    if count > 1:
        if not args.simple:
            print(str(line) + ": " + str(count))
        total_count += count

if args.simple:
    if total_count > 0:
        print(total_count)
    elif not args.quiet:
        print(total_count)
else:
    if total_count == 0 and not args.quiet:
        print("No constraint violations found")


########NEW FILE########
__FILENAME__ = dump_partition
#!/usr/bin/env python

import argparse, hashlib, os, os.path, psycopg2, subprocess, sys

parser = argparse.ArgumentParser(description="This script will dump out and then drop all tables contained in the designated schema using pg_dump.  Each table will be in its own separate file along with a SHA-512 hash of the dump file.  Tables are not dropped from the database if pg_dump does not return successfully. All dump_* option defaults are the same as they would be for pg_dump if they are not given.", epilog="NOTE: The connection options for psyocpg and pg_dump were separated out due to distinct differences in their requirements depending on your database connection configuration.")
parser.add_argument('-n','--schema', required=True, help="The schema that contains the tables that will be dumped. (Required)")
parser.add_argument('-c','--connection', default="host=localhost", help="""Connection string for use by psycopg. Must be able to select pg_catalog.pg_tables in the relevant database and drop all tables in the given schema.  Defaults to "host=localhost". Note this is distinct from the parameters sent to pg_dump.""")
parser.add_argument('-o','--output', default=os.getcwd(), help="Path to dump file output location. Default is where the script is run from.")
parser.add_argument('-d','--dump_database', help="Used for pg_dump, same as its --dbname (-d) option or final database name parameter.")
parser.add_argument('--dump_host', help="Used for pg_dump, same as its --host (-h) option.")
parser.add_argument('--dump_username', help="Used for pg_dump, same as its --username (-U) option.")
parser.add_argument('--dump_port', help="Used for pg_dump, same as its --port (-p) option.")
parser.add_argument('--pg_dump_path', help="Path to pg_dump binary location. Must set if not in current PATH.")
parser.add_argument('--Fp', action="store_true", help="Dump using pg_dump plain text format. Default is binary custom (-Fc).")
parser.add_argument('--nohashfile', action="store_true", help="Do NOT create a separate file with the SHA-512 hash of the dump. If dump files are very large, hash generation can possibly take a long time.")
parser.add_argument('--nodrop', action="store_true", help="Do NOT drop the tables from the given schema after dumping/hashing.")
parser.add_argument('-v','--verbose', action="store_true", help="Provide more verbose output.")
args = parser.parse_args()

if not os.path.exists(args.output):
    print("Path given by --output (-o) does not exist: " + str(args.output))
    sys.exit(2)


def get_tables():
    conn = psycopg2.connect(args.connection)
    cur = conn.cursor()
    sql = "SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = %s";
    cur.execute(sql, [args.schema])
    result = cur.fetchall()
    cur.close()
    conn.close()
    return result


def perform_dump(result):
    table_name = result.pop()[0]
    processcmd = []
    if args.pg_dump_path != None:
        processcmd.append(args.pg_dump_path)
    else:
        processcmd.append("pg_dump")
    if args.dump_host != None:
        processcmd.append("--host=" + args.dump_host)
    if args.dump_port != None:
        processcmd.append("--port=" + args.dump_port)
    if args.dump_username != None:
        processcmd.append("--username=" + args.dump_username)
    if args.Fp:
        processcmd.append("--format=plain")
    else:
        processcmd.append("--format=custom")
    processcmd.append("--table=" + args.schema + "." + table_name)
    output_file = os.path.join(args.output, args.schema + "." + table_name + ".pgdump")
    processcmd.append("--file=" + output_file)
    if args.dump_database != None:
        processcmd.append(args.dump_database)
    
    if args.verbose:
        print(processcmd)
    try:
        subprocess.check_call(processcmd)
    except subprocess.CalledProcessError as e:
        print("Error in pg_dump command: " + str(e.cmd))
        sys.exit(2)

    return table_name 


def create_hash(table_name):
    output_file = os.path.join(args.output, args.schema + "." + table_name + ".pgdump")
    try:
        with open(output_file, "rb") as fh:
            shash = hashlib.sha512()
            while True:
                data = fh.read(8192)
                if not data:
                    break
                shash.update(data)
    except IOError as e:
        print("Cannot access dump file for hash creation: " + e.strerror)
        sys.exit(2)

    hash_file = os.path.join(args.output, args.schema + "." + table_name + ".hash")
    if args.verbose:
        print("hash_file: " + hash_file)
    try:
        with open(hash_file, "w") as fh:
            fh.write(shash.hexdigest() + "  " + os.path.basename(output_file))
    except IOError as e:
        print("Unable to write to hash file: " + e.strerror)
        sys.exit(2)


def drop_table(table_name):
    conn = psycopg2.connect(args.connection)
    cur = conn.cursor()
    sql = "DROP TABLE IF EXISTS " + args.schema + "." + table_name;
    print(sql)
    cur.execute(sql)
    conn.commit()
    cur.close()
    conn.close()

if __name__ == "__main__":
    result = get_tables()
    while len(result) > 0:
        table_name = perform_dump(result)
        if not args.nohashfile:
            create_hash(table_name)
        if not args.nodrop:
            drop_table(table_name)

########NEW FILE########
__FILENAME__ = partition_data
#!/usr/bin/env python

import argparse, psycopg2, time, sys

parser = argparse.ArgumentParser(description="This script calls either partition_data_time() or partition_data_id() depending on the value given for --type. A commit is done at the end of each --interval and/or fully created partition. Returns the total number of rows moved to partitions. Automatically stops when parent is empty. See docs for examples.", epilog="NOTE: To help avoid heavy load and contention during partitioning, autovacuum is turned off for the parent table and all child tables when this script is run. When partitioning is complete, autovacuum is set back to its default value and the parent table is vacuumed when it is emptied.")
parser.add_argument('-p','--parent', required=True, help="Parent table of an already created partition set. (Required)")
parser.add_argument('-t','--type', choices=["time","id",], required=True, help="""Type of partitioning. Valid values are "time" and "id". (Required)""")
parser.add_argument('-c','--connection', default="host=localhost", help="""Connection string for use by psycopg to connect to your database. Defaults to "host=localhost".""")
parser.add_argument('-i','--interval', help="Value that is passed on to the partitioning function as p_batch_interval argument. Use this to set an interval smaller than the partition interval to commit data in smaller batches. Defaults to the partition interval if not given.")
parser.add_argument('-b','--batch', default=0, type=int, help="""How many times to loop through the value given for --interval. If --interval not set, will use default partition interval and make at most -b partition(s). Script commits at the end of each individual batch. (NOT passed as p_batch_count to partitioning function). If not set, all data in the parent table will be partitioned in a single run of the script.""")
parser.add_argument('-w','--wait', default=0, type=float, help="Cause the script to pause for a given number of seconds between commits (batches) to reduce write load")
parser.add_argument('-o', '--order', choices=["ASC", "DESC"], default="ASC", help="Allows you to specify the order that data is migrated from the parent to the children, either ascending (ASC) or descending (DESC). Default is ASC.")
parser.add_argument('-l','--lockwait', default=0, type=float, help="Have a lock timeout of this many seconds on the data move. If a lock is not obtained, that batch will be tried again.")
parser.add_argument('--lockwait_tries', default=10, type=int, help="Number of times to allow a lockwait to time out before giving up on the partitioning.  Defaults to 10")
parser.add_argument('--autovacuum_on', action="store_true", help="Turning autovacuum off requires a brief lock to ALTER the table property. Set this option to leave autovacuum on and avoid the lock attempt.")
parser.add_argument('-q','--quiet', action="store_true", help="Switch setting to stop all output during and after partitioning for use in cron jobs")
parser.add_argument('--debug', action="store_true", help="Show additional debugging output")
args = parser.parse_args()

def create_conn():
    conn = psycopg2.connect(args.connection)
    conn.autocommit = True
    return conn


def close_conn(conn):
    conn.close()


def get_partman_schema(conn):
    cur = conn.cursor()
    sql = "SELECT nspname FROM pg_catalog.pg_namespace n, pg_catalog.pg_extension e WHERE e.extname = 'pg_partman' AND e.extnamespace = n.oid"
    cur.execute(sql)
    partman_schema = cur.fetchone()[0]
    cur.close()
    return partman_schema


def turn_off_autovacuum(conn, partman_schema):
    cur = conn.cursor()
    sql = "ALTER TABLE " + args.parent + " SET (autovacuum_enabled = false, toast.autovacuum_enabled = false)"
    if not args.quiet:
        print("Attempting to turn off autovacuum for partition set...")
    if args.debug:
        print(cur.mogrify(sql))
    cur.execute(sql)
    sql = "SELECT * FROM " + partman_schema + ".show_partitions(%s)"
    if args.debug:
        print(cur.mogrify(sql, [args.parent]))
    cur.execute(sql, [args.parent])
    result = cur.fetchall()
    for r in result:
        sql = "ALTER TABLE " + r[0] + " SET (autovacuum_enabled = false, toast.autovacuum_enabled = false)"
        if args.debug:
            print(cur.mogrify(sql))
        cur.execute(sql)
    print("\t... Success!")
    cur.close()


def reset_autovacuum(conn, table):
    cur = conn.cursor()
    sql = "ALTER TABLE " + args.parent + " RESET (autovacuum_enabled, toast.autovacuum_enabled)"
    if not args.quiet:
        print("Attempting to reset autovacuum for old parent table...")
    if args.debug:
        print(cur.mogrify(sql))
    cur.execute(sql)
    sql = "SELECT * FROM " + partman_schema + ".show_partitions(%s)"
    if args.debug:
        print(cur.mogrify(sql, [args.parent]))
    cur.execute(sql, [args.parent])
    result = cur.fetchall()
    for r in result:
        sql = "ALTER TABLE " + r[0] + " RESET (autovacuum_enabled, toast.autovacuum_enabled)"
        if args.debug:
            print(cur.mogrify(sql))
        cur.execute(sql)
    print("\t... Success!")
    cur.close()


def vacuum_parent(conn):
    cur = conn.cursor()
    sql = "VACUUM ANALYZE " + args.parent
    if args.debug:
        print(cur.mogrify(sql))
    if not args.quiet:
        print("Running vacuum analyze on parent table...")
    cur.execute(sql)
    cur.close()


def partition_data(conn, partman_schema):
    batch_count = 0
    total = 0
    lockwait_count = 0

    cur = conn.cursor()

    sql = "SELECT " + partman_schema + ".partition_data_" + args.type + "(%s"
    if args.interval != "":
        sql += ", p_batch_interval := %s"
    sql += ", p_lock_wait := %s"
    sql += ", p_order := %s)"

    while True:
        if args.interval != "":
            li = [args.parent, args.interval, args.lockwait, args.order]
        else:
            li = [args.parent, args.lockwait, args.order]
        if args.debug:
            print(cur.mogrify(sql, li))
        cur.execute(sql, li)
        result = cur.fetchone()
        if not args.quiet:
            if result[0] > 0:
                print("Rows moved: " + str(result[0]))
            elif result[0] == -1:
                print("Unable to obtain lock, trying again")
                print(conn.notices[-1])
        # if lock wait timeout, do not increment the counter
        if result[0] != -1:
            batch_count += 1
            total += result[0]
            lockwait_count = 0
        else:
            lockwait_count += 1
            if lockwait_count > args.lockwait_tries:
                print("Quitting due to inability to get lock on next rows to be moved")
                break
        # If no rows left or given batch argument limit is reached
        if (result[0] == 0) or (args.batch > 0 and batch_count >= int(args.batch)):
            break
        time.sleep(args.wait)

    return total

if __name__ == "__main__":
    conn = create_conn()
    partman_schema = get_partman_schema(conn)

    if not args.autovacuum_on:
        turn_off_autovacuum(conn, partman_schema)

    total = partition_data(conn, partman_schema)

    if not args.quiet:
        print("Total rows moved: %d" % total)

    vacuum_parent(conn)

    if not args.autovacuum_on:
        reset_autovacuum(conn, partman_schema)

    close_conn(conn)

########NEW FILE########
__FILENAME__ = reapply_constraints
#!/usr/bin/env python

import argparse, psycopg2, sys, time
from multiprocessing import Process

parser = argparse.ArgumentParser(description="Script for reapplying additional constraints managed by pg_partman on child tables. See docs for additional info on this special constraint management. Script runs in two distinct modes: 1) Drop all constraints  2) Apply all constraints. Typical usage would be to run the drop mode, edit the data, then run apply mode to re-create all constraints on a partition set.")
parser.add_argument('-p', '--parent', required=True, help="Parent table of an already created partition set. (Required)")
parser.add_argument('-c', '--connection', default="host=localhost", help="""Connection string for use by psycopg to connect to your database. Defaults to "host=localhost".""")
parser.add_argument('-d', '--drop_constraints', action="store_true", help="Drop all constraints managed by pg_partman. Drops constraints on all child tables including current & future.")
parser.add_argument('-a', '--add_constraints', action="store_true", help="Apply configured constraints to all child tables older than the premake value.")
parser.add_argument('-j', '--jobs', type=int, default=0, help="Use the python multiprocessing library to recreate indexes in parallel. Value for -j is number of simultaneous jobs to run. Note that this is per table, not per index. Be very careful setting this option if load is a concern on your systems.")
parser.add_argument('-w', '--wait', type=float, default=0, help="Wait the given number of seconds after a table has had its constraints dropped or applied before moving on to the next. When used with -j, this will set the pause between the batches of parallel jobs instead.")
parser.add_argument('--dryrun', action="store_true", help="Show what the script will do without actually running it against the database. Highly recommend reviewing this before running.")
parser.add_argument('-q', '--quiet', action="store_true", help="Turn off all output.")
args = parser.parse_args()

if args.parent.find(".") < 0:
    print("Parent table must be schema qualified")
    sys.exit(2)
    
if args.drop_constraints and args.add_constraints: 
    print("Can only set one or the other of --drop_constraints (-d) and --add_constraints (-a)")
    sys.exit(2)

if (args.drop_constraints == False) and (args.add_constraints == False):
    print("Must set one of --drop_constraints (-d) or --add_constraints (-a)")
    sys.exit(2)

def create_conn():
    conn = psycopg2.connect(args.connection)
    return conn

def close_conn(conn):
    conn.close()

def get_partman_schema(conn):
    cur = conn.cursor()
    sql = "SELECT nspname FROM pg_catalog.pg_namespace n, pg_catalog.pg_extension e WHERE e.extname = 'pg_partman' AND e.extnamespace = n.oid"
    cur.execute(sql)
    partman_schema = cur.fetchone()[0]
    cur.close()
    return partman_schema

def get_children(conn, partman_schema):
    cur = conn.cursor()
    sql = "SELECT " + partman_schema + ".show_partitions(%s, %s)"
    cur.execute(sql, [args.parent, 'ASC'])
    child_list = cur.fetchall()
    cur.close()
    return child_list

def get_premake(conn, partman_schema):
    cur = conn.cursor()
    sql = "SELECT premake FROM " + partman_schema + ".part_config WHERE parent_table = %s"
    cur.execute(sql, [args.parent])
    premake = int(cur.fetchone()[0])
    cur.close()
    return premake

def apply_proc(child_table, partman_schema):
    conn = create_conn()
    conn.autocommit = True
    cur = conn.cursor()
    sql = "SELECT " + partman_schema + ".apply_constraints(%s, %s, %s, %s)"
    debug = False;
    if not args.quiet:
        debug = True
        print(cur.mogrify(sql, [args.parent, child_table, False, debug]))
    if not args.dryrun:
        cur.execute(sql, [args.parent, child_table, False, debug])
    cur.close()
    close_conn(conn)


def drop_proc(child_table, partman_schema):
    conn = create_conn()
    conn.autocommit = True
    cur = conn.cursor()
    sql = "SELECT " + partman_schema + ".drop_constraints(%s, %s, %s)"
    debug = False;
    if not args.quiet:
        debug = True
        print(cur.mogrify(sql, [args.parent, child_table, debug]))
    if not args.dryrun:
        cur.execute(sql, [args.parent, child_table, debug])
    cur.close()
    close_conn(conn)

if __name__ == "__main__":
    main_conn = create_conn()
    partman_schema = get_partman_schema(main_conn)
    child_list = get_children(main_conn, partman_schema)
    premake = get_premake(main_conn, partman_schema)

    if args.add_constraints:
        # Remove tables from the list of child tables that shouldn't have constraints yet 
        for x in range((premake * 2) + 1):
            child_list.pop()
    
    if args.jobs == 0:
        for c in child_list:
            if args.drop_constraints:
               drop_proc(c[0], partman_schema)
            if args.add_constraints:
               apply_proc(c[0], partman_schema)
            if args.wait > 0:
                time.sleep(args.wait)
    else:
        child_list.reverse()
        while len(child_list) > 0:
            if not args.quiet:
                print("Jobs left in queue: " + str(len(child_list)))
            if len(child_list) < args.jobs:
                args.jobs = len(child_list)
            processlist = []
            for num in range(0, args.jobs):
                c = child_list.pop()
                if args.drop_constraints:
                    p = Process(target=drop_proc, args=(c[0], partman_schema))
                if args.add_constraints:
                    p = Process(target=apply_proc, args=(c[0], partman_schema))
                p.start()
                processlist.append(p)
            for j in processlist:
                j.join()
            if args.wait > 0:
                time.sleep(args.wait)

    sql = 'ANALYZE ' + args.parent
    main_cur = main_conn.cursor()
    if not args.quiet:
        print(main_cur.mogrify(sql))
    if not args.dryrun:
        main_cur.execute(sql)

    close_conn(main_conn)


########NEW FILE########
__FILENAME__ = reapply_foreign_keys
#!/usr/bin/env python

import argparse, psycopg2, sys, time

parser = argparse.ArgumentParser(description="This script will reapply the foreign keys on a parent table to all child tables in an inheritance set. Any existing foreign keys on child tables will be dropped in order to match the parent. A commit is done after each foreign key application to avoid excessive contention. Note that this script can work on any inheritance set, not just partition sets managed by pg_partman.")
parser.add_argument('-p','--parent', required=True, help="Parent table of an already created partition set. (Required)")
parser.add_argument('-c','--connection', default="host=localhost", help="""Connection string for use by psycopg to connect to your database. Defaults to "host=localhost".""")
parser.add_argument('-q', '--quiet', action="store_true", help="Switch setting to stop all output during and after partitioning undo.")
parser.add_argument('--dryrun', action="store_true", help="Show what the script will do without actually running it against the database. Highly recommend reviewing this before running.")
parser.add_argument('--debug', action="store_true", help="Show additional debugging output")
args = parser.parse_args() 


def apply_foreign_keys(conn, child_tables):
    if not args.quiet:
        print("Applying foreign keys to child tables...")
    cur = conn.cursor()
    for c in child_tables:
        sql = """SELECT keys.conname
                    , keys.confrelid::regclass::text AS ref_table
                    , '"'||string_agg(att.attname, '","')||'"' AS ref_column
                    , '"'||string_agg(att2.attname, '","')||'"' AS child_column
                FROM
                    ( SELECT con.conname
                            , unnest(con.conkey) as ref
                            , unnest(con.confkey) as child
                            , con.confrelid
                            , con.conrelid
                      FROM pg_catalog.pg_class c
                      JOIN pg_catalog.pg_namespace n ON c.relnamespace = n.oid
                      JOIN pg_catalog.pg_constraint con ON c.oid = con.conrelid
                      WHERE n.nspname ||'.'|| c.relname = %s
                      AND con.contype = 'f'
                      ORDER BY con.conkey
                ) keys
                JOIN pg_catalog.pg_class cl ON cl.oid = keys.confrelid
                JOIN pg_catalog.pg_attribute att ON att.attrelid = keys.confrelid AND att.attnum = keys.child
                JOIN pg_catalog.pg_attribute att2 ON att2.attrelid = keys.conrelid AND att2.attnum = keys.ref
                GROUP BY keys.conname, keys.confrelid""";
        if args.debug:
            print(cur.mogrify(sql, [args.parent]))
        cur.execute(sql, [args.parent])
        parent_fkeys = cur.fetchall()
        for pfk in parent_fkeys:
            alter_sql = "ALTER TABLE " + c[0] + " ADD FOREIGN KEY (" + pfk[3] + ") REFERENCES " + pfk[1] + "(" + pfk[2] + ")"
            if not args.quiet:
                print(alter_sql)
            if not args.dryrun:
                cur.execute(alter_sql)


def create_conn():
    conn = psycopg2.connect(args.connection)
    conn.autocommit = True
    return conn


def close_conn(conn):
    conn.close()


def drop_foreign_keys(conn, child_tables):
    if not args.quiet:
        print("Dropping current foreign keys on child tables...")
    cur = conn.cursor()
    for c in child_tables:
        sql = """SELECT constraint_name
            FROM information_schema.table_constraints 
            WHERE table_schema||'.'||table_name = %s AND constraint_type = 'FOREIGN KEY'"""
        if args.debug:
            print(cur.mogrify(sql, [ c[0] ]))
        cur.execute(sql, [ c[0] ])
        child_fkeys = cur.fetchall()
        for cfk in child_fkeys:
            alter_sql = "ALTER TABLE " + c[0] + " DROP CONSTRAINT " + cfk[0]
            if not args.quiet:
                print(alter_sql)
            if not args.dryrun:
                cur.execute(alter_sql)


def get_child_tables(conn, part_schema):
    if not args.quiet:
        print("Getting list of child tables...")
    cur = conn.cursor()
    sql = "SELECT * FROM " + partman_schema + ".show_partitions(%s)"
    if args.debug:
        print(cur.mogrify(sql, [args.parent]))
    cur.execute(sql, [args.parent])
    result = cur.fetchall()
    return result


def get_partman_schema(conn):
    cur = conn.cursor()
    sql = "SELECT nspname FROM pg_catalog.pg_namespace n, pg_catalog.pg_extension e WHERE e.extname = 'pg_partman' AND e.extnamespace = n.oid"
    cur.execute(sql)
    partman_schema = cur.fetchone()[0]
    cur.close()
    return partman_schema


if __name__ == "__main__":
    conn = create_conn()

    partman_schema = get_partman_schema(conn)
    child_tables = get_child_tables(conn, partman_schema)

    drop_foreign_keys(conn, child_tables)
    apply_foreign_keys(conn, child_tables)

    if not args.quiet:
        print("Done!")
    close_conn(conn)

########NEW FILE########
__FILENAME__ = reapply_indexes
#!/usr/bin/env python

import argparse, psycopg2, re, sys, time
from multiprocessing import Process

parser = argparse.ArgumentParser(description="Script for reapplying indexes on child tables in a partition set after they are changed on the parent table. All indexes on all child tables (not including primary key unless specified) will be dropped and recreated for the given set. Commits are done after each index is dropped/created to help prevent long running transactions & locks.", epilog="NOTE: New index names are made based off the child table name & columns used, so their naming may differ from the name given on the parent. This is done to allow the tool to account for long or duplicate index names. If an index name would be duplicated, an incremental counter is added on to the end of the index name to allow it to be created. Use the --dryrun option first to see what it will do and which names may cause dupes to be handled like this.")
parser.add_argument('-p', '--parent', required=True, help="Parent table of an already created partition set. (Required)")
parser.add_argument('-c', '--connection', default="host=localhost", help="""Connection string for use by psycopg to connect to your database. Defaults to "host=localhost".""")
parser.add_argument('--concurrent', action="store_true", help="Create indexes with the CONCURRENTLY option. Note this does not work on primary keys when --primary is given.")
parser.add_argument('--primary', action="store_true", help="By default the primary key is not recreated. Set this option if that is needed. Note this will cause an exclusive lock on the child table.")
parser.add_argument('--drop_concurrent', action="store_true", help="Drop indexes concurrently when recreating them (PostgreSQL >= v9.2). Note this does not work on primary keys when --primary is given.")
parser.add_argument('-j', '--jobs', type=int, default=0, help="Use the python multiprocessing library to recreate indexes in parallel. Value for -j is number of simultaneous jobs to run. Note that this is per table, not per index. Be very careful setting this option if load is a concern on your systems.")
parser.add_argument('-w', '--wait', type=float, default=0, help="Wait the given number of seconds after indexes have finished being created on a table before moving on to the next. When used with -j, this will set the pause between the batches of parallel jobs instead.")
parser.add_argument('--dryrun', action="store_true", help="Show what the script will do without actually running it against the database. Highly recommend reviewing this before running. Note that if multiple indexes would get the same default name, the duplicated name will show in the dryrun (because the index doesn't exist in the catalog to check for it). When the real thing is run, the duplicated names will be handled as stated in NOTE at the end of --help.")
parser.add_argument('-q', '--quiet', action="store_true", help="Turn off all output.")
args = parser.parse_args()

if args.parent.find(".") < 0:
    print("ERROR: Parent table must be schema qualified")
    sys.exit(2)


# Add any checks for version specific features to this function
def check_version(conn, partman_schema):
    cur = conn.cursor()
    if args.drop_concurrent:
        sql = "SELECT " + partman_schema + ".check_version('9.2.0')"
        cur.execute(sql)
        if cur.fetchone()[0] == False:
            print("ERROR: --drop_concurrent option requires PostgreSQL minimum version 9.2.0")
            sys.exit(2)
    cur.close()


def create_conn():
    conn = psycopg2.connect(args.connection)
    return conn


def create_index(conn, partman_schema, child_table, index_list):
    cur = conn.cursor()
    sql = """SELECT schemaname, tablename FROM pg_catalog.pg_tables WHERE schemaname||'.'||tablename = %s"""
    cur.execute(sql, [args.parent])
    result = cur.fetchone()
    parent_schemaname = result[0]
    parent_tablename = result[1]
    cur.execute(sql, [child_table])
    result = cur.fetchone()
    child_tablename = result[1]
    cur.close()
    regex = re.compile(r" ON %s| ON %s" % (args.parent, parent_tablename))
    for i in index_list:
        if i[1] == True and args.primary:
            index_name = child_tablename + "_" + "_".join(i[2].split(","))
            sql = "SELECT " + partman_schema + ".check_name_length('" + index_name + "', p_suffix := '_pk')"
            cur = conn.cursor()
            cur.execute(sql)
            index_name = cur.fetchone()[0]
            cur.close()
            statement = "ALTER TABLE " + child_table + " ADD CONSTRAINT " + index_name + " PRIMARY KEY (" + i[2] + ")"
        elif i[1] == False:
            index_name = child_tablename
            if i[2] != None:
                index_name += "_"
                index_name += "_".join(i[2].split(","))
            sql = "SELECT " + partman_schema + ".check_name_length('" + index_name + "', p_suffix := '_idx')"
            cur = conn.cursor()
            cur.execute(sql)
            index_name = cur.fetchone()[0]
            name_counter = 1
            while True:
                sql = "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON c.relnamespace = n.oid WHERE n.nspname = %s AND c.relname = %s"
                cur = conn.cursor()
                cur.execute(sql, [parent_schemaname, index_name])
                index_exists = cur.fetchone()[0]
                if index_exists != None and index_exists > 0:
                    index_name = child_tablename
                    if i[2] != None:
                        index_name += "_"
                        index_name += "_".join(i[2].split(","))
                    suffix = "_idx" + str(name_counter)
                    sql = "SELECT " + partman_schema + ".check_name_length('" + index_name + "', p_suffix := '" + suffix + "')"
                    cur = conn.cursor()
                    cur.execute(sql)
                    index_name = cur.fetchone()[0]
                else:
                    break
            cur.close()
            statement = i[0]
            statement = statement.replace(i[3], index_name)  # replace parent index name with child index name
            if args.concurrent:
                statement = statement.replace("CREATE INDEX ", "CREATE INDEX CONCURRENTLY ")
            statement = regex.sub(" ON " + child_table, statement)  
        cur = conn.cursor()
        if not args.quiet:
            print(cur.mogrify(statement))
        if not args.dryrun:
            cur.execute(statement)
        cur.close()


def close_conn(conn):
    conn.close()


def get_children(conn, partman_schema):
    cur = conn.cursor()
    sql = "SELECT " + partman_schema + ".show_partitions(%s, %s)"
    cur.execute(sql, [args.parent, 'ASC'])
    child_list = cur.fetchall()
    cur.close()
    return child_list


def get_drop_list(conn, child_table):
    cur = conn.cursor() 
    sql = """SELECT i.indisprimary, n.nspname||'.'||c.relname, t.conname
            FROM pg_catalog.pg_index i 
            JOIN pg_catalog.pg_class c ON i.indexrelid = c.oid
            JOIN pg_catalog.pg_namespace n ON c.relnamespace = n.oid
            LEFT JOIN pg_catalog.pg_constraint t ON c.oid = t.conindid
            WHERE i.indrelid = %s::regclass"""
    cur.execute(sql, [child_table])
    drop_tuple = cur.fetchall()
    cur.close()
    drop_list = []
    for d in drop_tuple:
        if d[0] == True and args.primary:
            statement = "ALTER TABLE " + child_table + " DROP CONSTRAINT " + d[2]
            drop_list.append(statement)
        elif d[0] == False:
            if args.drop_concurrent:
                statement = "DROP INDEX CONCURRENTLY " + d[1]
            else:
                statement = "DROP INDEX " + d[1]
            drop_list.append(statement)
    return drop_list


def get_parent_indexes(conn):
    cur = conn.cursor()
    sql = """SELECT 
            pg_get_indexdef(indexrelid) AS statement
            , i.indisprimary
            , ( SELECT array_to_string(array_agg( a.attname ORDER by x.r ), ',') 
                FROM pg_catalog.pg_attribute a 
                JOIN ( SELECT k, row_number() over () as r 
                        FROM unnest(i.indkey) k ) as x 
                ON a.attnum = x.k AND a.attrelid = i.indrelid
            ) AS indkey_names
            , c.relname
            FROM pg_catalog.pg_index i
            JOIN pg_catalog.pg_class c ON i.indexrelid = c.oid
            WHERE i.indrelid = %s::regclass
                AND i.indisvalid"""
    cur.execute(sql, [args.parent])
    parent_index_list = cur.fetchall()
    return parent_index_list


def get_partman_schema(conn):
    cur = conn.cursor()
    sql = "SELECT nspname FROM pg_catalog.pg_namespace n, pg_catalog.pg_extension e WHERE e.extname = 'pg_partman' AND e.extnamespace = n.oid"
    cur.execute(sql)
    partman_schema = cur.fetchone()[0]
    cur.close()
    return partman_schema


def reindex_proc(child_table, partman_schema):
    conn = create_conn()
    conn.autocommit = True # must be turned on to support CONCURRENTLY
    cur = conn.cursor()
    drop_list = get_drop_list(conn, child_table)
    parent_index_list = get_parent_indexes(conn)
    for d in drop_list:
        if not args.quiet:
            print(cur.mogrify(d))
        if not args.dryrun: 
            cur.execute(d)

    create_index(conn, partman_schema, child_table, parent_index_list)

    sql = "ANALYZE " + child_table
    if not args.quiet:
        print(cur.mogrify(sql))
    if not args.dryrun:
        cur.execute(sql)
    cur.close()
    close_conn(conn)


if __name__ == "__main__":
    conn = create_conn()
    cur = conn.cursor()
    partman_schema = get_partman_schema(conn)
    check_version(conn, partman_schema)
    child_list = get_children(conn, partman_schema)
    close_conn(conn)

    if args.jobs == 0:
         for c in child_list:
            reindex_proc(c[0], partman_schema)
            if args.wait > 0:
                time.sleep(args.wait)
    else:
        child_list.reverse()
        while len(child_list) > 0:
            if not args.quiet:
                print("Jobs left in queue: " + str(len(child_list)))
            if len(child_list) < args.jobs:
                args.jobs = len(child_list)
            processlist = []
            for num in range(0, args.jobs):
                c = child_list.pop()
                p = Process(target=reindex_proc, args=(c[0],partman_schema))
                p.start()
                processlist.append(p)
            for j in processlist:
                j.join()
            if args.wait > 0:
                time.sleep(args.wait)


########NEW FILE########
__FILENAME__ = undo_partition
#!/usr/bin/env python

import argparse, psycopg2, sys, time

parser = argparse.ArgumentParser(description="This script calls either undo_partition(), undo_partition_time() or undo_partition_id depending on the value given for --type. A commit is done at the end of each --interval and/or emptied partition. Returns the total number of rows put into the parent. Automatically stops when last child table is empty.")
parser.add_argument('-p','--parent', required=True, help="Parent table of the partition set. (Required)")
parser.add_argument('-t','--type', choices=["time","id",], help="""Type of partitioning. Valid values are "time" and "id". Not setting this argument will use undo_partition() and work on any parent/child table set.""")
parser.add_argument('-c','--connection', default="host=localhost", help="""Connection string for use by psycopg to connect to your database. Defaults to "host=localhost".""")
parser.add_argument('-i','--interval', help="Value that is passed on to the undo partitioning function as p_batch_interval. Use this to set an interval smaller than the partition interval to commit data in smaller batches. Defaults to the partition interval if not given. If -t value is not set, interval cannot be smaller than the partition interval and an entire partition is copied each batch.")
parser.add_argument('-b','--batch', type=int, default=0, help="How many times to loop through the value given for --interval. If --interval not set, will use default partition interval and undo at most -b partition(s).  Script commits at the end of each individual batch. (NOT passed as p_batch_count to undo function). If not set, all data will be moved to the parent table in a single run of the script.")
parser.add_argument('-d', '--droptable', action="store_true", help="Switch setting for whether to drop child tables when they are empty. Do not set to just uninherit.")
parser.add_argument('-w','--wait', type=float, default=0, help="Cause the script to pause for a given number of seconds between commits (batches).")
parser.add_argument('-l','--lockwait', default=0, type=float, help="Have a lock timeout of this many seconds on the data move. If a lock is not obtained, that batch will be tried again.")
parser.add_argument('--lockwait_tries', default=10, type=int, help="Number of times to allow a lockwait to time out before giving up on the partitioning.  Defaults to 10")
parser.add_argument('--autovacuum_on', action="store_true", help="Turning autovacuum off requires a brief lock to ALTER the table property. Set this option to leave autovacuum on and avoid the lock attempt.")
parser.add_argument('-q', '--quiet', action="store_true", help="Switch setting to stop all output during and after partitioning undo.")
parser.add_argument('--debug', action="store_true", help="Show additional debugging output")
args = parser.parse_args() 


def create_conn():
    conn = psycopg2.connect(args.connection)
    conn.autocommit = True
    return conn


def close_conn(conn):
    conn.close()


def get_partman_schema(conn):
    cur = conn.cursor()
    sql = "SELECT nspname FROM pg_catalog.pg_namespace n, pg_catalog.pg_extension e WHERE e.extname = 'pg_partman' AND e.extnamespace = n.oid"
    cur.execute(sql)
    partman_schema = cur.fetchone()[0]
    cur.close()
    return partman_schema


def turn_off_autovacuum(conn, partman_schema):
    cur = conn.cursor()
    sql = "ALTER TABLE " + args.parent + " SET (autovacuum_enabled = false, toast.autovacuum_enabled = false)"
    if not args.quiet:
        print("Attempting to turn off autovacuum for partition set...")
    if args.debug:
        print(cur.mogrify(sql))
    cur.execute(sql)
    sql = "SELECT * FROM " + partman_schema + ".show_partitions(%s)"
    if args.debug:
        print(cur.mogrify(sql, [args.parent]))
    cur.execute(sql, [args.parent])
    result = cur.fetchall()
    for r in result:
        sql = "ALTER TABLE " + r[0] + " SET (autovacuum_enabled = false, toast.autovacuum_enabled = false)"
        if args.debug:
            print(cur.mogrify(sql))
        cur.execute(sql)
    print("\t... Success!")
    cur.close()


def reset_autovacuum(conn, table):
    cur = conn.cursor()
    sql = "ALTER TABLE " + args.parent + " RESET (autovacuum_enabled, toast.autovacuum_enabled)"
    if not args.quiet:
        print("Attempting to reset autovacuum for old parent table...")
    if args.debug:
        print(cur.mogrify(sql))
    cur.execute(sql)
    sql = "SELECT * FROM " + partman_schema + ".show_partitions(%s)"
    if args.debug:
        print(cur.mogrify(sql, [args.parent]))
    cur.execute(sql, [args.parent])
    result = cur.fetchall()
    for r in result:
        sql = "ALTER TABLE " + r[0] + " RESET (autovacuum_enabled, toast.autovacuum_enabled)"
        if args.debug:
            print(cur.mogrify(sql))
        cur.execute(sql)
    print("\t... Success!")
    cur.close()


def vacuum_parent(conn):
    cur = conn.cursor()
    sql = "VACUUM ANALYZE " + args.parent
    if args.debug:
        print(cur.mogrify(sql))
    if not args.quiet:
        print("Running vacuum analyze on parent table...")
    cur.execute(sql)
    cur.close()


def undo_partition_data(conn, partman_schema):
    batch_count = 0
    total = 0
    lockwait_count = 0

    cur = conn.cursor()

    sql = "SELECT " + partman_schema + ".undo_partition"
    if args.type != None:
        sql += "_" + args.type
    sql += "(%s, p_keep_table := %s"
    if args.interval != None:
        sql += ", p_batch_interval := %s"
    sql += ", p_lock_wait := %s"
    sql += ")"

    # Actual undo sql functions do not drop by default, so fix argument value to match that default
    if args.droptable:
        keep_table = False
    else:
        keep_table = True

    while True:
        if args.interval != None:
            li = [args.parent, keep_table, args.interval, args.lockwait]
        else:
            li = [args.parent, keep_table, args.lockwait]
        if args.debug:
            print(cur.mogrify(sql, li))
        cur.execute(sql, li)
        result = cur.fetchone()
        conn.commit()
        if not args.quiet:
            if result[0] > 0:
                print("Rows moved into parent: " + str(result[0]))
            elif result[0] == -1:
                print("Unable to obtain lock, trying again (" + str(lockwait_count+1) + ")")
                print(conn.notices[-1])
        # if lock wait timeout, do not increment the counter
        if result[0] != -1:
            batch_count += 1
            total += result[0]
            lockwait_count = 0
        else:
            lockwait_count += 1
            if lockwait_count > args.lockwait_tries:
                print("Quitting due to inability to get lock on table/rows for migration to parent")
                break
        # If no rows left or given batch argument limit is reached
        if (result[0] == 0) or (args.batch > 0 and batch_count >= int(args.batch)):
            break
        if args.wait > 0:
            time.sleep(args.wait)

    return total


if __name__ == "__main__":
    conn = create_conn()
    partman_schema = get_partman_schema(conn)

    if not args.autovacuum_on:
        turn_off_autovacuum(conn, partman_schema)

    total = undo_partition_data(conn, partman_schema)

    if not args.quiet:
        print("Total rows moved: %d" % total)

    vacuum_parent(conn)

    if not args.autovacuum_on:
        reset_autovacuum(conn, partman_schema)

    close_conn(conn)

########NEW FILE########
