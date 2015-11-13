__FILENAME__ = fixman
#! /usr/bin/env python

import sys,re

# hacks to force empty lines into manpage
ln1 = r"\1<simpara></simpara>\2"
xml = sys.stdin.read()
xml = re.sub(r"(</literallayout>\s*)(<simpara)", ln1, xml)
xml = re.sub(r"(</variablelist>\s*)(<simpara)", ln1, xml)
sys.stdout.write(xml)


########NEW FILE########
__FILENAME__ = getattrs
#! /usr/bin/env python

import sys

buf = open(sys.argv[1], "r").read().lower()

if buf.find("pgq consumer") >= 0:
    print "-a pgq"


########NEW FILE########
__FILENAME__ = kwcheck
#! /usr/bin/env python

import sys
import re

import pkgloader
pkgloader.require('skytools', '3.0')
import skytools.quoting

kwmap = skytools.quoting._ident_kwmap

fn = "/opt/src/pgsql/postgresql/src/include/parser/kwlist.h"
if len(sys.argv) == 2:
    fn = sys.argv[1]

rc = re.compile(r'PG_KEYWORD[(]"(.*)" , \s* \w+ , \s* (\w+) [)]', re.X)

data = open(fn, 'r').read()
full_map = {}
cur_map = {}
print "== new =="
for kw, cat in rc.findall(data):
    full_map[kw] = 1
    if cat == 'UNRESERVED_KEYWORD':
        continue
    if cat == 'COL_NAME_KEYWORD':
        continue
    cur_map[kw] = 1
    if kw not in kwmap:
        print kw, cat
    kwmap[kw] = 1

print "== obsolete =="
kws = kwmap.keys()
kws.sort()
for k in kws:
    if k not in full_map:
        print k, '(not in full_map)'
    elif k not in cur_map:
        print k, '(not in cur_map)'

print "== full list =="
ln = ""
for k in kws:
    ln += '"%s":1, ' % k
    if len(ln) > 70:
        print ln.strip()
        ln = ""
print ln.strip()


########NEW FILE########
__FILENAME__ = bulk_loader
#! /usr/bin/env python

"""Bulkloader for slow databases (Bizgres).

Idea is following:
    - Script reads from queue a batch of urlencoded row changes.
      Inserts/updates/deletes, maybe many per one row.
    - It creates 3 lists: ins_list, upd_list, del_list.
      If one row is changed several times, it keeps the latest.
    - Lists are processed in followin way:
      ins_list - COPY into main table
      upd_list - COPY into temp table, UPDATE from there
      del_list - COPY into temp table, DELETE from there
    - One side-effect is that total order of how rows appear
      changes, but per-row changes will be kept in order.

The speedup from the COPY will happen only if the batches are
large enough.  So the ticks should happen only after couple
of minutes.

bl_sourcedb_queue_to_destdb.ini

Config template::
    [bulk_loader]
    # job name is optional when not given ini file name is used
    job_name = bl_sourcedb_queue_to_destdb

    src_db = dbname=sourcedb
    dst_db = dbname=destdb

    pgq_queue_name = source_queue

    use_skylog = 0

    logfile = ~/log/%(job_name)s.log
    pidfile = ~/pid/%(job_name)s.pid

    # 0 - apply UPDATE as UPDATE
    # 1 - apply UPDATE as DELETE+INSERT
    # 2 - merge INSERT/UPDATE, do DELETE+INSERT
    load_method = 0

    # no hurry
    loop_delay = 10

    # table renaming
    # remap_tables = skypein_cdr_closed:skypein_cdr, tbl1:tbl2
"""

import sys, os, pgq, skytools
from skytools import quote_ident, quote_fqident


## several methods for applying data

# update as update
METH_CORRECT = 0
# update as delete/copy
METH_DELETE = 1
# merge ins_list and upd_list, do delete/copy
METH_MERGED = 2

# no good method for temp table check before 8.2
USE_LONGLIVED_TEMP_TABLES = False

AVOID_BIZGRES_BUG = 1

def find_dist_fields(curs, fqtbl):
    if not skytools.exists_table(curs, "pg_catalog.mpp_distribution_policy"):
        return []
    schema, name = fqtbl.split('.')
    q = "select a.attname"\
        "  from pg_class t, pg_namespace n, pg_attribute a,"\
        "       mpp_distribution_policy p"\
        " where n.oid = t.relnamespace"\
        "   and p.localoid = t.oid"\
        "   and a.attrelid = t.oid"\
        "   and a.attnum = any(p.attrnums)"\
        "   and n.nspname = %s and t.relname = %s"
    curs.execute(q, [schema, name])
    res = []
    for row in curs.fetchall():
        res.append(row[0])
    return res

def exists_temp_table(curs, tbl):
    # correct way, works only on 8.2
    q = "select 1 from pg_class where relname = %s and relnamespace = pg_my_temp_schema()"

    # does not work with parallel case
    #q = """
    #select 1 from pg_class t, pg_namespace n
    #where n.oid = t.relnamespace
    #  and pg_table_is_visible(t.oid)
    #  and has_schema_privilege(n.nspname, 'USAGE')
    #  and has_table_privilege(n.nspname || '.' || t.relname, 'SELECT')
    #  and substr(n.nspname, 1, 8) = 'pg_temp_'
    #  and t.relname = %s;
    #"""
    curs.execute(q, [tbl])
    tmp = curs.fetchall()
    return len(tmp) > 0

class TableCache:
    """Per-table data hander."""

    def __init__(self, tbl):
        """Init per-batch table data cache."""
        self.name = tbl
        self.ev_list = []
        self.pkey_map = {}
        self.pkey_list = []
        self.pkey_str = None
        self.col_list = None

        self.final_ins_list = []
        self.final_upd_list = []
        self.final_del_list = []

    def add_event(self, ev):
        """Store new event."""

        # op & data
        ev.op = ev.ev_type[0]
        ev.data = skytools.db_urldecode(ev.ev_data)

        # get pkey column names
        if self.pkey_str is None:
            if len(ev.ev_type) > 2:
                self.pkey_str = ev.ev_type.split(':')[1]
            else:
                self.pkey_str = ev.ev_extra2

            if self.pkey_str:
                self.pkey_list = self.pkey_str.split(',')

        # get pkey value
        if self.pkey_str:
            pk_data = []
            for k in self.pkey_list:
                pk_data.append(ev.data[k])
            ev.pk_data = tuple(pk_data)
        elif ev.op == 'I':
            # fake pkey, just to get them spread out
            ev.pk_data = ev.id
        else:
            raise Exception('non-pk tables not supported: %s' % self.name)

        # get full column list, detect added columns
        if not self.col_list:
            self.col_list = ev.data.keys()
        elif self.col_list != ev.data.keys():
            # ^ supposedly python guarantees same order in keys()

            # find new columns
            for c in ev.data.keys():
                if c not in self.col_list:
                    for oldev in self.ev_list:
                        oldev.data[c] = None
            self.col_list = ev.data.keys()

        # add to list
        self.ev_list.append(ev)

        # keep all versions of row data
        if ev.pk_data in self.pkey_map:
            self.pkey_map[ev.pk_data].append(ev)
        else:
            self.pkey_map[ev.pk_data] = [ev]

    def finish(self):
        """Got all data, prepare for insertion."""

        del_list = []
        ins_list = []
        upd_list = []
        for ev_list in self.pkey_map.values():
            # rewrite list of I/U/D events to
            # optional DELETE and optional INSERT/COPY command
            exists_before = -1
            exists_after = 1
            for ev in ev_list:
                if ev.op == "I":
                    if exists_before < 0:
                        exists_before = 0
                    exists_after = 1
                elif ev.op == "U":
                    if exists_before < 0:
                        exists_before = 1
                    #exists_after = 1 # this shouldnt be needed
                elif ev.op == "D":
                    if exists_before < 0:
                        exists_before = 1
                    exists_after = 0
                else:
                    raise Exception('unknown event type: %s' % ev.op)

            # skip short-lived rows
            if exists_before == 0 and exists_after == 0:
                continue

            # take last event
            ev = ev_list[-1]
            
            # generate needed commands
            if exists_before and exists_after:
                upd_list.append(ev.data)
            elif exists_before:
                del_list.append(ev.data)
            elif exists_after:
                ins_list.append(ev.data)

        # reorder cols
        new_list = self.pkey_list[:]
        for k in self.col_list:
            if k not in self.pkey_list:
                new_list.append(k)

        self.col_list = new_list
        self.final_ins_list = ins_list
        self.final_upd_list = upd_list
        self.final_del_list = del_list

class BulkLoader(pgq.SerialConsumer):
    __doc__ = __doc__
    load_method = METH_CORRECT
    remap_tables = {}
    def __init__(self, args):
        pgq.SerialConsumer.__init__(self, "bulk_loader", "src_db", "dst_db", args)

    def reload(self):
        pgq.SerialConsumer.reload(self)

        self.load_method = self.cf.getint("load_method", METH_CORRECT)
        if self.load_method not in (METH_CORRECT,METH_DELETE,METH_MERGED):
            raise Exception("bad load_method")

        self.remap_tables = {}
        for mapelem in self.cf.getlist("remap_tables", ''):
            tmp = mapelem.split(':')
            tbl = tmp[0].strip()
            new = tmp[1].strip()
            self.remap_tables[tbl] = new

    def process_remote_batch(self, src_db, batch_id, ev_list, dst_db):
        """Content dispatcher."""

        # add events to per-table caches
        tables = {}
        for ev in ev_list:
            tbl = ev.extra1
            if not tbl in tables:
                tables[tbl] = TableCache(tbl)
            cache = tables[tbl]
            cache.add_event(ev)

        # then process them
        for tbl, cache in tables.items():
            cache.finish()
            self.process_one_table(dst_db, tbl, cache)

    def process_one_table(self, dst_db, tbl, cache):

        del_list = cache.final_del_list
        ins_list = cache.final_ins_list
        upd_list = cache.final_upd_list
        col_list = cache.col_list
        real_update_count = len(upd_list)

        self.log.debug("process_one_table: %s  (I/U/D = %d/%d/%d)" % (
                       tbl, len(ins_list), len(upd_list), len(del_list)))

        if tbl in self.remap_tables:
            old = tbl
            tbl = self.remap_tables[tbl]
            self.log.debug("Redirect %s to %s" % (old, tbl))

        # hack to unbroke stuff
        if self.load_method == METH_MERGED:
            upd_list += ins_list
            ins_list = []

        # check if interesting table
        curs = dst_db.cursor()
        if not skytools.exists_table(curs, tbl):
            self.log.warning("Ignoring events for table: %s" % tbl)
            return

        # fetch distribution fields
        dist_fields = find_dist_fields(curs, tbl)
        extra_fields = []
        for fld in dist_fields:
            if fld not in cache.pkey_list:
                extra_fields.append(fld)
        self.log.debug("PKey fields: %s  Extra fields: %s" % (
                       ",".join(cache.pkey_list), ",".join(extra_fields)))

        # create temp table
        temp = self.create_temp_table(curs, tbl)
        
        # where expr must have pkey and dist fields
        klist = []
        for pk in cache.pkey_list + extra_fields:
            exp = "%s.%s = %s.%s" % (quote_fqident(tbl), quote_ident(pk),
                                     quote_fqident(temp), quote_ident(pk))
            klist.append(exp)
        whe_expr = " and ".join(klist)

        # create del sql
        del_sql = "delete from only %s using %s where %s" % (
                  quote_fqident(tbl), quote_fqident(temp), whe_expr)

        # create update sql
        slist = []
        key_fields = cache.pkey_list + extra_fields
        for col in cache.col_list:
            if col not in key_fields:
                exp = "%s = %s.%s" % (quote_ident(col), quote_fqident(temp), quote_ident(col))
                slist.append(exp)
        upd_sql = "update only %s set %s from %s where %s" % (
                    quote_fqident(tbl), ", ".join(slist), quote_fqident(temp), whe_expr)

        # insert sql
        colstr = ",".join([quote_ident(c) for c in cache.col_list])
        ins_sql = "insert into %s (%s) select %s from %s" % (
                  quote_fqident(tbl), colstr, colstr, quote_fqident(temp))

        # process deleted rows
        if len(del_list) > 0:
            self.log.info("Deleting %d rows from %s" % (len(del_list), tbl))
            # delete old rows
            q = "truncate %s" % quote_fqident(temp)
            self.log.debug(q)
            curs.execute(q)
            # copy rows
            self.log.debug("COPY %d rows into %s" % (len(del_list), temp))
            skytools.magic_insert(curs, temp, del_list, col_list)
            # delete rows
            self.log.debug(del_sql)
            curs.execute(del_sql)
            self.log.debug("%s - %d" % (curs.statusmessage, curs.rowcount))
            self.log.debug(curs.statusmessage)
            if len(del_list) != curs.rowcount:
                self.log.warning("Delete mismatch: expected=%s updated=%d"
                        % (len(del_list), curs.rowcount))

        # process updated rows
        if len(upd_list) > 0:
            self.log.info("Updating %d rows in %s" % (len(upd_list), tbl))
            # delete old rows
            q = "truncate %s" % quote_fqident(temp)
            self.log.debug(q)
            curs.execute(q)
            # copy rows
            self.log.debug("COPY %d rows into %s" % (len(upd_list), temp))
            skytools.magic_insert(curs, temp, upd_list, col_list)
            if self.load_method == METH_CORRECT:
                # update main table
                self.log.debug(upd_sql)
                curs.execute(upd_sql)
                self.log.debug(curs.statusmessage)
                # check count
                if len(upd_list) != curs.rowcount:
                    self.log.warning("Update mismatch: expected=%s updated=%d"
                            % (len(upd_list), curs.rowcount))
            else:
                # delete from main table
                self.log.debug(del_sql)
                curs.execute(del_sql)
                self.log.debug(curs.statusmessage)
                # check count
                if real_update_count != curs.rowcount:
                    self.log.warning("Update mismatch: expected=%s deleted=%d"
                            % (real_update_count, curs.rowcount))
                # insert into main table
                if AVOID_BIZGRES_BUG:
                    # copy again, into main table
                    self.log.debug("COPY %d rows into %s" % (len(upd_list), tbl))
                    skytools.magic_insert(curs, tbl, upd_list, col_list)
                else:
                    # better way, but does not work due bizgres bug
                    self.log.debug(ins_sql)
                    curs.execute(ins_sql)
                    self.log.debug(curs.statusmessage)

        # process new rows
        if len(ins_list) > 0:
            self.log.info("Inserting %d rows into %s" % (len(ins_list), tbl))
            skytools.magic_insert(curs, tbl, ins_list, col_list)

        # delete remaining rows
        if USE_LONGLIVED_TEMP_TABLES:
            q = "truncate %s" % quote_fqident(temp)
        else:
            # fscking problems with long-lived temp tables
            q = "drop table %s" % quote_fqident(temp)
        self.log.debug(q)
        curs.execute(q)

    def create_temp_table(self, curs, tbl):
        # create temp table for loading
        tempname = tbl.replace('.', '_') + "_loadertmp"

        # check if exists
        if USE_LONGLIVED_TEMP_TABLES:
            if exists_temp_table(curs, tempname):
                self.log.debug("Using existing temp table %s" % tempname)
                return tempname
    
        # bizgres crashes on delete rows
        arg = "on commit delete rows"
        arg = "on commit preserve rows"
        # create temp table for loading
        q = "create temp table %s (like %s) %s" % (
                quote_fqident(tempname), quote_fqident(tbl), arg)
        self.log.debug("Creating temp table: %s" % q)
        curs.execute(q)
        return tempname
        
if __name__ == '__main__':
    script = BulkLoader(sys.argv[1:])
    script.start()


########NEW FILE########
__FILENAME__ = cube_dispatcher
#! /usr/bin/env python

"""It accepts urlencoded rows for multiple tables from queue
and insert them into actual tables, with partitioning on tick time.

Config template::

    [cube_dispatcher]
    job_name          = cd_srcdb_queue_to_dstdb_dstcolo.ini

    src_db            = dbname=sourcedb_test
    dst_db            = dbname=dataminedb_test

    pgq_queue_name    = udata.some_queue

    logfile           = ~/log/%(job_name)s.log
    pidfile           = ~/pid/%(job_name)s.pid

    # how many rows are kept: keep_latest, keep_all
    mode = keep_latest

    # to_char() fmt for table suffix
    #dateformat = YYYY_MM_DD
    # following disables table suffixes:
    #dateformat =

    part_template = 
        create table _DEST_TABLE (like _PARENT);
        alter table only _DEST_TABLE add primary key (_PKEY);
        grant select on _DEST_TABLE to postgres;
"""

import sys, os, pgq, skytools

DEF_CREATE = """
create table _DEST_TABLE (like _PARENT);
alter table only _DEST_TABLE add primary key (_PKEY);
"""

class CubeDispatcher(pgq.SerialConsumer):
    __doc__ = __doc__

    def __init__(self, args):
        pgq.SerialConsumer.__init__(self, "cube_dispatcher", "src_db", "dst_db", args)

        self.dateformat = self.cf.get('dateformat', 'YYYY_MM_DD')

        self.part_template = self.cf.get('part_template', DEF_CREATE)

        mode = self.cf.get('mode', 'keep_latest')
        if mode == 'keep_latest':
            self.keep_latest = 1
        elif mode == 'keep_all':
            self.keep_latest = 0
        else:
            self.log.fatal('wrong mode setting')
            sys.exit(1)

    def get_part_date(self, batch_id):
        if not self.dateformat:
            return None

        # fetch and format batch date
        src_db = self.get_database('src_db')
        curs = src_db.cursor()
        q = 'select to_char(batch_end, %s) from pgq.get_batch_info(%s)'
        curs.execute(q, [self.dateformat, batch_id])
        src_db.commit()
        return curs.fetchone()[0]

    def process_remote_batch(self, src_db, batch_id, ev_list, dst_db):
        # actual processing
        self.dispatch(dst_db, ev_list, self.get_part_date(batch_id))

    def dispatch(self, dst_db, ev_list, date_str):
        """Actual event processing."""

        # get tables and sql
        tables = {}
        sql_list = []
        for ev in ev_list:
            if date_str:
                tbl = "%s_%s" % (ev.extra1, date_str)
            else:
                tbl = ev.extra1

            sql = self.make_sql(tbl, ev)
            sql_list.append(sql)

            if not tbl in tables:
                tables[tbl] = self.get_table_info(ev, tbl)

        # create tables if needed
        self.check_tables(dst_db, tables)

        # insert into data tables
        curs = dst_db.cursor()
        block = []
        for sql in sql_list:
            self.log.debug(sql)
            block.append(sql)
            if len(block) > 100:
                curs.execute("\n".join(block))
                block = []
        if len(block) > 0:
            curs.execute("\n".join(block))
    
    def get_table_info(self, ev, tbl):
        klist = [skytools.quote_ident(k) for k in ev.key_list.split(',')]
        inf = {
            'parent': ev.extra1,
            'table': tbl,
            'key_list': ",".join(klist),
        }
        return inf

    def make_sql(self, tbl, ev):
        """Return SQL statement(s) for that event."""
        
        # parse data
        data = skytools.db_urldecode(ev.data)
            
        # parse tbl info
        if ev.type.find(':') > 0:
            op, keys = ev.type.split(':')
        else:
            op = ev.type
            keys = ev.extra2
        ev.key_list = keys
        key_list = keys.split(',')
        if self.keep_latest and len(key_list) == 0:
            raise Exception('No pkey on table %s' % tbl)

        # generate sql
        if op in ('I', 'U'):
            if self.keep_latest:
                sql = "%s %s" % (self.mk_delete_sql(tbl, key_list, data),
                                 self.mk_insert_sql(tbl, key_list, data))
            else:
                sql = self.mk_insert_sql(tbl, key_list, data)
        elif op == "D":
            if not self.keep_latest:
                raise Exception('Delete op not supported if mode=keep_all')

            sql = self.mk_delete_sql(tbl, key_list, data)
        else:
            raise Exception('Unknown row op: %s' % op)
        return sql
        
    def mk_delete_sql(self, tbl, key_list, data):
        # generate delete command
        whe_list = []
        for k in key_list:
            whe_list.append("%s = %s" % (skytools.quote_ident(k), skytools.quote_literal(data[k])))
        whe_str = " and ".join(whe_list)
        return "delete from %s where %s;" % (skytools.quote_fqident(tbl), whe_str)
            
    def mk_insert_sql(self, tbl, key_list, data):
        # generate insert command
        col_list = []
        val_list = []
        for c, v in data.items():
            col_list.append(skytools.quote_ident(c))
            val_list.append(skytools.quote_literal(v))
        col_str = ",".join(col_list)
        val_str = ",".join(val_list)
        return "insert into %s (%s) values (%s);" % (
                        skytools.quote_fqident(tbl), col_str, val_str)

    def check_tables(self, dcon, tables):
        """Checks that tables needed for copy are there. If not
        then creates them.

        Used by other procedures to ensure that table is there
        before they start inserting.

        The commits should not be dangerous, as we haven't done anything
        with cdr's yet, so they should still be in one TX.

        Although it would be nicer to have a lock for table creation.
        """

        dcur = dcon.cursor()
        for tbl, inf in tables.items():
            if skytools.exists_table(dcur, tbl):
                continue

            sql = self.part_template
            sql = sql.replace('_DEST_TABLE', skytools.quote_fqident(inf['table']))
            sql = sql.replace('_PARENT', skytools.quote_fqident(inf['parent']))
            sql = sql.replace('_PKEY', inf['key_list'])
            # be similar to table_dispatcher
            schema_table = inf['table'].replace(".", "__")
            sql = sql.replace('_SCHEMA_TABLE', skytools.quote_ident(schema_table))

            dcur.execute(sql)
            dcon.commit()
            self.log.info('%s: Created table %s' % (self.job_name, tbl))

if __name__ == '__main__':
    script = CubeDispatcher(sys.argv[1:])
    script.start()


########NEW FILE########
__FILENAME__ = simple_serial_consumer
#! /usr/bin/env python

"""simple serial consumer for skytools3

it consumes events from a predefined queue and feeds them to a sql statement

Config template::

[simple_serial_consumer]
job_name       = descriptive_name_for_job

src_db = dbname=sourcedb_test
dst_db = dbname=destdb port=1234 host=dbhost.com username=guest password=secret

pgq_queue_name = source_queue

logfile        = ~/log/%(job_name)s.log
pidfile        = ~/pid/%(job_name)s.pid

dst_query      = select 1

use_skylog     = 0
"""

"""Config example::

Create a queue named "echo_queue" in a database (like "testdb")

Register consumer "echo" to this queue

Start the echo consumer with config file shown below
(You may want to use -v to see, what will happen)

From some other window, insert something into the queue:
    select pgq.insert_event('echo_queue','type','hello=world');

Enjoy the ride :)

If dst_query is set to "select 1" then echo consumer becomes a sink consumer

[simple_serial_consumer]

job_name       = echo

src_db = dbname=testdb
dst_db = dbname=testdb

pgq_queue_name = echo_queue

logfile        = ~/log/%(job_name)s.log
pidfile        = ~/pid/%(job_name)s.pid

dst_query      =
        select *
        from pgq.insert_event('echo_queue', %%(pgq.ev_type)s, %%(pgq.ev_data)s)
"""

import sys, pgq, skytools
skytools.sane_config = 1

class SimpleSerialConsumer(pgq.SerialConsumer):
    doc_string = __doc__

    def __init__(self, args):
        pgq.SerialConsumer.__init__(self,"simple_serial_consumer","src_db","dst_db", args)
        self.dst_query = self.cf.get("dst_query")

    def process_remote_batch(self, db, batch_id, event_list, dst_db):
        curs = dst_db.cursor()
        for ev in event_list:
            payload = skytools.db_urldecode(ev.data)
            if payload is None:
                payload = {}
            payload['pgq.ev_type'] = ev.type
            payload['pgq.ev_data'] = ev.data
            payload['pgq.ev_id'] = ev.id
            payload['pgq.ev_time'] = ev.time
            payload['pgq.ev_extra1'] = ev.extra1
            payload['pgq.ev_extra2'] = ev.extra2
            payload['pgq.ev_extra3'] = ev.extra3
            payload['pgq.ev_extra4'] = ev.extra4

            self.log.debug(self.dst_query % payload)
            curs.execute(self.dst_query, payload)
            try:
                res = curs.fetchone()
                self.log.debug(res)
            except:
                pass

if __name__ == '__main__':
    script = SimpleSerialConsumer(sys.argv[1:])
    script.start()

########NEW FILE########
__FILENAME__ = table_dispatcher
#! /usr/bin/env python

"""It loads urlencoded rows for one trable from queue and inserts
them into actual tables, with optional partitioning.

--ini
[table_dispatcher]
job_name          = test_move

src_db            = dbname=sourcedb_test
dst_db            = dbname=dataminedb_test

pgq_queue_name    = OrderLog

logfile           = ~/log/%(job_name)s.log
pidfile           = ~/pid/%(job_name)s.pid

# where to put data.  when partitioning, will be used as base name
dest_table = orders

# date field with will be used for partitioning
# special value: _EVTIME - event creation time
part_column = start_date

#fields = *
#fields = id, name
#fields = id:newid, name, bar:baz


# template used for creating partition tables
# _DEST_TABLE
part_template     = 
    create table _DEST_TABLE () inherits (orders);
    alter table only _DEST_TABLE add constraint _DEST_TABLE_pkey primary key (id);
    grant select on _DEST_TABLE to group reporting;
"""

import sys, os, pgq, skytools

DEST_TABLE = "_DEST_TABLE"
SCHEMA_TABLE = "_SCHEMA_TABLE"

class TableDispatcher(pgq.SerialConsumer):
    """Single-table partitioner."""
    def __init__(self, args):
        pgq.SerialConsumer.__init__(self, "table_dispatcher", "src_db", "dst_db", args)

        self.part_template = self.cf.get("part_template", '')
        self.dest_table = self.cf.get("dest_table")
        self.part_field = self.cf.get("part_field", '')
        self.part_method = self.cf.get("part_method", 'daily')
        if self.part_method not in ('daily', 'monthly'):
            raise Exception('bad part_method')

        if self.cf.get("fields", "*") == "*":
            self.field_map = None
        else:
            self.field_map = {}
            for fval in self.cf.getlist('fields'):
                tmp = fval.split(':')
                if len(tmp) == 1:
                    self.field_map[tmp[0]] = tmp[0]
                else:
                    self.field_map[tmp[0]] = tmp[1]

    def process_remote_batch(self, src_db, batch_id, ev_list, dst_db):
        # actual processing
        self.dispatch(dst_db, ev_list)

    def dispatch(self, dst_db, ev_list):
        """Generic dispatcher."""

        # load data
        tables = {}
        for ev in ev_list:
            row = skytools.db_urldecode(ev.data)

            # guess dest table
            if self.part_field:
                if self.part_field == "_EVTIME":
                    partval = str(ev.creation_date)
                else:
                    partval = str(row[self.part_field])
                partval = partval.split(' ')[0]
                date = partval.split('-')
                if self.part_method == 'monthly':
                    date = date[:2]
                suffix = '_'.join(date)
                tbl = "%s_%s" % (self.dest_table, suffix)
            else:
                tbl = self.dest_table

            # map fields
            if self.field_map is None:
                dstrow = row
            else:
                dstrow = {}
                for k, v in self.field_map.items():
                    dstrow[v] = row[k]

            # add row into table
            if not tbl in tables:
                tables[tbl] = [dstrow]
            else:
                tables[tbl].append(dstrow)

        # create tables if needed
        self.check_tables(dst_db, tables)

        # insert into data tables
        curs = dst_db.cursor()
        for tbl, tbl_rows in tables.items():
            skytools.magic_insert(curs, tbl, tbl_rows)

    def check_tables(self, dcon, tables):
        """Checks that tables needed for copy are there. If not
        then creates them.

        Used by other procedures to ensure that table is there
        before they start inserting.

        The commits should not be dangerous, as we haven't done anything
        with cdr's yet, so they should still be in one TX.

        Although it would be nicer to have a lock for table creation.
        """

        dcur = dcon.cursor()
        for tbl in tables.keys():
            if not skytools.exists_table(dcur, tbl):
                if not self.part_template:
                    raise Exception('Dest table does not exists and no way to create it.')

                sql = self.part_template
                sql = sql.replace(DEST_TABLE, skytools.quote_fqident(tbl))

                # we do this to make sure that constraints for 
                # tables who contain a schema will still work
                schema_table = tbl.replace(".", "__")
                sql = sql.replace(SCHEMA_TABLE, skytools.quote_ident(schema_table))

                dcur.execute(sql)
                dcon.commit()
                self.log.info('%s: Created table %s' % (self.job_name, tbl))

if __name__ == '__main__':
    script = TableDispatcher(sys.argv[1:])
    script.start()


########NEW FILE########
__FILENAME__ = compare
#! /usr/bin/env python

"""Compares tables in replication set.

Currently just does count(1) on both sides.
"""

import sys, skytools

__all__ = ['Comparator']

from londiste.syncer import Syncer

class Comparator(Syncer):
    """Simple checker based on Syncer.
    When tables are in sync runs simple SQL query on them.
    """
    def process_sync(self, t1, t2, src_db, dst_db):
        """Actual comparison."""

        src_tbl = t1.dest_table
        dst_tbl = t2.dest_table

        src_curs = src_db.cursor()
        dst_curs = dst_db.cursor()

        dst_where = t2.plugin.get_copy_condition(src_curs, dst_curs)
        src_where = dst_where

        self.log.info('Counting %s', dst_tbl)

        # get common cols
        cols = self.calc_cols(src_curs, src_tbl, dst_curs, dst_tbl)

        # get sane query
        v1 = src_db.server_version
        v2 = dst_db.server_version
        if self.options.count_only:
            q = "select count(1) as cnt from only _TABLE_"
        elif v1 < 80300 or v2 < 80300:
            # 8.2- does not have record to text and text to bit casts, so we need to use a bit of evil hackery
            q = "select count(1) as cnt, sum(bit_in(textout('x'||substr(md5(textin(record_out(_COLS_))),1,16)), 0, 64)::bigint) as chksum from only _TABLE_"
        elif (v1 < 80400 or v2 < 80400) and v1 != v2:
            # hashtext changed in 8.4 so we need to use md5 in case there is 8.3 vs 8.4+ comparison
            q = "select count(1) as cnt, sum(('x'||substr(md5(_COLS_::text),1,16))::bit(64)::bigint) as chksum from only _TABLE_"
        else:
            # this way is much faster than the above
            q = "select count(1) as cnt, sum(hashtext(_COLS_::text)::bigint) as chksum from only _TABLE_"

        q = self.cf.get('compare_sql', q)
        q = q.replace("_COLS_", cols)
        src_q = q.replace('_TABLE_', skytools.quote_fqident(src_tbl))
        if src_where:
            src_q = src_q + " WHERE " + src_where
        dst_q = q.replace('_TABLE_', skytools.quote_fqident(dst_tbl))
        if dst_where:
            dst_q = dst_q + " WHERE " + dst_where

        f = "%(cnt)d rows"
        if not self.options.count_only:
            f += ", checksum=%(chksum)s"
        f = self.cf.get('compare_fmt', f)

        self.log.debug("srcdb: %s", src_q)
        src_curs.execute(src_q)
        src_row = src_curs.fetchone()
        src_str = f % src_row
        self.log.info("srcdb: %s", src_str)
        src_db.commit()

        self.log.debug("dstdb: %s", dst_q)
        dst_curs.execute(dst_q)
        dst_row = dst_curs.fetchone()
        dst_str = f % dst_row
        self.log.info("dstdb: %s", dst_str)
        dst_db.commit()

        if src_str != dst_str:
            self.log.warning("%s: Results do not match!", dst_tbl)
            return 1
        return 0

    def calc_cols(self, src_curs, src_tbl, dst_curs, dst_tbl):
        cols1 = self.load_cols(src_curs, src_tbl)
        cols2 = self.load_cols(dst_curs, dst_tbl)

        qcols = []
        for c in self.calc_common(cols1, cols2):
            qcols.append(skytools.quote_ident(c))
        return "(%s)" % ",".join(qcols)

    def load_cols(self, curs, tbl):
        schema, table = skytools.fq_name_parts(tbl)
        q = "select column_name from information_schema.columns"\
            " where table_schema = %s and table_name = %s"
        curs.execute(q, [schema, table])
        cols = []
        for row in curs.fetchall():
            cols.append(row[0])
        return cols

    def calc_common(self, cols1, cols2):
        common = []
        map2 = {}
        for c in cols2:
            map2[c] = 1
        for c in cols1:
            if c in map2:
                common.append(c)
        if len(common) == 0:
            raise Exception("no common columns found")

        if len(common) != len(cols1) or len(cols2) != len(cols1):
            self.log.warning("Ignoring some columns")

        return common

    def init_optparse(self, p=None):
        """Initialize cmdline switches."""
        p = super(Comparator, self).init_optparse(p)
        p.add_option("--count-only", action="store_true", help="just count rows, do not compare data")
        return p

if __name__ == '__main__':
    script = Comparator(sys.argv[1:])
    script.start()

########NEW FILE########
__FILENAME__ = exec_attrs
"""Custom parser for EXECUTE attributes.

The values are parsed from SQL file given to EXECUTE.

Format rules:
    * Only lines starting with meta-comment prefix will be parsed: --*--
    * Empty or regular SQL comment lines are ignored.
    * Parsing stops on first SQL statement.
    * Meta-line format: "--*-- Key: value1, value2"
    * If line ends with ',' then next line is taken as continuation.

Supported keys:
    * Local-Table:
    * Local-Sequence:
    * Local-Destination:

    * Need-Table
    * Need-Sequence
    * Need-Function
    * Need-Schema
    * Need-View

Sample file::
  --*-- Local-Sequence: myseq
  --*--
  --*-- Local-Table: table1,
  --*--     table2, table3
  --*--

Tests:

>>> a = ExecAttrs()
>>> a.add_value("Local-Table", "mytable")
>>> a.add_value("Local-Sequence", "seq1")
>>> a.add_value("Local-Sequence", "seq2")
>>> a.to_urlenc()
'local-table=mytable&local-sequence=seq1%2Cseq2'
>>> a.add_value("Local-Destination", "mytable-longname-more1")
>>> a.add_value("Local-Destination", "mytable-longname-more2")
>>> a.add_value("Local-Destination", "mytable-longname-more3")
>>> a.add_value("Local-Destination", "mytable-longname-more4")
>>> a.add_value("Local-Destination", "mytable-longname-more5")
>>> a.add_value("Local-Destination", "mytable-longname-more6")
>>> a.add_value("Local-Destination", "mytable-longname-more7")
>>> print a.to_sql()
--*-- Local-Table: mytable
--*-- Local-Sequence: seq1, seq2
--*-- Local-Destination: mytable-longname-more1, mytable-longname-more2,
--*--     mytable-longname-more3, mytable-longname-more4, mytable-longname-more5,
--*--     mytable-longname-more6, mytable-longname-more7
>>> a = ExecAttrs(sql = '''
... 
...  -- 
... 
... --*-- Local-Table: foo , 
... --
... --*-- bar , 
... --*--
... --*-- zoo 
... --*-- 
... --*-- Local-Sequence: goo  
... --*-- 
... --
... 
... create fooza;
... ''')
>>> print a.to_sql()
--*-- Local-Table: foo, bar, zoo
--*-- Local-Sequence: goo
>>> seqs = {'public.goo': 'public.goo'}
>>> tables = {}
>>> tables['public.foo'] = 'public.foo'
>>> tables['public.bar'] = 'other.Bar'
>>> tables['public.zoo'] = 'Other.Foo'
>>> a.need_execute(None, tables, seqs)
True
>>> a.need_execute(None, [], [])
False
>>> sql = '''alter table @foo@;
... alter table @bar@;
... alter table @zoo@;'''
>>> print a.process_sql(sql, tables, seqs)
alter table public.foo;
alter table other."Bar";
alter table "Other"."Foo";
"""

import skytools

META_PREFIX = "--*--"

class Matcher:
    nice_name = None
    def match(self, objname, curs, tables, seqs):
        pass
    def get_key(self):
        return self.nice_name.lower()
    def local_rename(self):
        return False

class LocalTable(Matcher):
    nice_name = "Local-Table"
    def match(self, objname, curs, tables, seqs):
        return objname in tables
    def local_rename(self):
        return True

class LocalSequence(Matcher):
    nice_name = "Local-Sequence"
    def match(self, objname, curs, tables, seqs):
        return objname in seqs
    def local_rename(self):
        return True

class LocalDestination(Matcher):
    nice_name = "Local-Destination"
    def match(self, objname, curs, tables, seqs):
        if objname not in tables:
            return False
        dest_name = tables[objname]
        return skytools.exists_table(curs, dest_name)
    def local_rename(self):
        return True

class NeedTable(Matcher):
    nice_name = "Need-Table"
    def match(self, objname, curs, tables, seqs):
        return skytools.exists_table(curs, objname)

class NeedSequence(Matcher):
    nice_name = "Need-Sequence"
    def match(self, objname, curs, tables, seqs):
        return skytools.exists_sequence(curs, objname)

class NeedSchema(Matcher):
    nice_name = "Need-Schema"
    def match(self, objname, curs, tables, seqs):
        return skytools.exists_schema(curs, objname)

class NeedFunction(Matcher):
    nice_name = "Need-Function"
    def match(self, objname, curs, tables, seqs):
        nargs = 0
        pos1 = objname.find('(')
        if pos1 > 0:
            pos2 = objname.find(')')
            if pos2 > 0:
                s = objname[pos1+1 : pos2]
                objname = objname[:pos1]
                nargs = int(s)
        return skytools.exists_function(curs, objname, nargs)

class NeedView(Matcher):
    nice_name = "Need-View"
    def match(self, objname, curs, tables, seqs):
        return skytools.exists_view(curs, objname)

META_SPLITLINE = 70

# list of matches, in order they need to be probed
META_MATCHERS = [
    LocalTable(), LocalSequence(), LocalDestination(),
    NeedTable(), NeedSequence(), NeedFunction(),
    NeedSchema(), NeedView()
]

# key to nice key
META_KEYS = {}
for m in META_MATCHERS:
    k = m.nice_name.lower()
    META_KEYS[k] = m

class ExecAttrsException(skytools.UsageError):
    """Some parsing problem."""

class ExecAttrs:
    """Container and parser for EXECUTE attributes."""
    def __init__(self, sql=None, urlenc=None):
        """Create container and parse either sql or urlenc string."""

        self.attrs = {}
        if sql and urlenc:
            raise Exception("Both sql and urlenc set.")
        if urlenc:
            self.parse_urlenc(urlenc)
        elif sql:
            self.parse_sql(sql)

    def add_value(self, k, v):
        """Add single value to key."""

        xk = k.lower().strip()
        if xk not in META_KEYS:
            raise ExecAttrsException("Invalid key: %s" % k)
        if xk not in self.attrs:
            self.attrs[xk] = []

        xv = v.strip()
        self.attrs[xk].append(xv)

    def to_urlenc(self):
        """Convert container to urlencoded string."""
        sdict = {}
        for k, v in self.attrs.items():
            sdict[k] = ','.join(v)
        return skytools.db_urlencode(sdict)

    def parse_urlenc(self, ustr):
        """Parse urlencoded string adding values to current container."""
        sdict = skytools.db_urldecode(ustr)
        for k, v in sdict.items():
            for v1 in v.split(','):
                self.add_value(k, v1)

    def to_sql(self):
        """Convert container to SQL meta-comments."""
        lines = []
        for m in META_MATCHERS:
            k = m.get_key()
            if k not in self.attrs:
                continue
            vlist = self.attrs[k]
            ln = "%s %s: " % (META_PREFIX, m.nice_name)
            start = 0
            for nr, v in enumerate(vlist):
                if nr > start:
                    ln = ln + ", " + v
                else:
                    ln = ln + v

                if len(ln) >= META_SPLITLINE and nr < len(vlist) - 1:
                    ln += ','
                    lines.append(ln)
                    ln = META_PREFIX + "     "
                    start = nr + 1
            lines.append(ln)
        return '\n'.join(lines)

    def parse_sql(self, sql):
        """Parse SQL meta-comments."""

        cur_key = None
        cur_continued = False
        lineno = 1
        for nr, ln in enumerate(sql.splitlines()):
            lineno = nr+1

            # skip empty lines
            ln = ln.strip()
            if not ln:
                continue

            # stop at non-comment
            if ln[:2] != '--':
                break

            # parse only meta-comments
            if ln[:len(META_PREFIX)] != META_PREFIX:
                continue

            # cut prefix, skip empty comments
            ln = ln[len(META_PREFIX):].strip()
            if not ln:
                continue

            # continuation of previous key
            if cur_continued:
                # collect values
                for v in ln.split(','):
                    v = v.strip()
                    if not v:
                        continue
                    self.add_value(cur_key, v)

                # does this key continue?
                if ln[-1] != ',':
                    cur_key = None
                    cur_continued = False

                # go to next line
                continue
            
            # parse key
            pos = ln.find(':')
            if pos < 0:
                continue
            k = ln[:pos].strip()

            # collect values
            for v in ln[pos+1:].split(','):
                v = v.strip()
                if not v:
                    continue
                self.add_value(k, v)

            # check if current key values will continue
            if ln[-1] == ',':
                cur_key = k
                cur_continued = True
            else:
                cur_key = None
                cur_continued = False

    def need_execute(self, curs, local_tables, local_seqs):
        # if no attrs, always execute
        if not self.attrs:
            return True
        
        matched = 0
        missed = 0
        good_list = []
        miss_list = []
        for m in META_MATCHERS:
            k = m.get_key()
            if k not in self.attrs:
                continue
            for v in self.attrs[k]:
                fqname = skytools.fq_name(v)
                if m.match(fqname, curs, local_tables, local_seqs):
                    matched += 1
                    good_list.append(v)
                else:
                    missed += 1
                    miss_list.append(v)
                    # should be drop out early?
        if matched > 0 and missed == 0:
            return True
        elif missed > 0 and matched == 0:
            return False
        elif missed == 0 and matched == 0:
            # should not happen, but lets restore old behaviour?
            return True
        else:
            raise Exception("SQL only partially matches local setup: matches=%r misses=%r" % (good_list, miss_list))

    def get_attr(self, k):
        k = k.lower().strip()
        if k not in META_KEYS:
            raise Exception("Bug: invalid key requested: " + k)
        if k not in self.attrs:
            return []
        return self.attrs[k]

    def process_sql(self, sql, local_tables, local_seqs):
        """Replace replacement tags in sql with actual local names."""
        for k, vlist in self.attrs.items():
            m = META_KEYS[k]
            if not m.local_rename():
                continue
            for v in vlist:
                repname = '@%s@' % v
                fqname = skytools.fq_name(v)
                if fqname in local_tables:
                    localname = local_tables[fqname]
                elif fqname in local_seqs:
                    localname = local_seqs[fqname]
                else:
                    # should not happen
                    raise Exception("bug: lost table: "+v)
                qdest = skytools.quote_fqident(localname)
                sql = sql.replace(repname, qdest)
        return sql

if __name__ == "__main__":
    import doctest
    doctest.testmod()


########NEW FILE########
__FILENAME__ = handler

"""Table handler.

Per-table decision how to create trigger, copy data and apply events.
"""

"""
-- redirect & create table
partition by batch_time
partition by date field

-- sql handling:
cube1 - I/U/D -> partition, insert
cube2 - I/U/D -> partition, del/insert
field remap
name remap

bublin filter
- replay: filter events
- copy: additional where
- add: add trigger args

multimaster
- replay: conflict handling, add fncall to sql queue?
- add: add 'backup' arg to trigger

plain londiste:
- replay: add to sql queue

"""

import sys
import logging
import skytools
import londiste.handlers

__all__ = ['RowCache', 'BaseHandler', 'build_handler', 'EncodingValidator',
           'load_handler_modules', 'create_handler_string']

class RowCache:
    def __init__(self, table_name):
        self.table_name = table_name
        self.keys = {}
        self.rows = []

    def add_row(self, d):
        row = [None] * len(self.keys)
        for k, v in d.items():
            try:
                row[self.keys[k]] = v
            except KeyError:
                i = len(row)
                self.keys[k] = i
                row.append(v)
        row = tuple(row)
        self.rows.append(row)

    def get_fields(self):
        row = [None] * len(self.keys)
        for k, i in self.keys.keys():
            row[i] = k
        return tuple(row)

    def apply_rows(self, curs):
        fields = self.get_fields()
        skytools.magic_insert(curs, self.table_name, self.rows, fields)

class BaseHandler:
    """Defines base API, does nothing.
    """
    handler_name = 'nop'
    log = logging.getLogger('basehandler')

    def __init__(self, table_name, args, dest_table):
        self.table_name = table_name
        self.dest_table = dest_table or table_name
        self.fq_table_name = skytools.quote_fqident(self.table_name)
        self.fq_dest_table = skytools.quote_fqident(self.dest_table)
        self.args = args
        self._check_args (args)
        self.conf = self.get_config()

    def _parse_args_from_doc (self):
        doc = self.__doc__ or ""
        params_descr = []
        params_found = False
        for line in doc.splitlines():
            ln = line.strip()
            if params_found:
                if ln == "":
                    break
                descr = ln.split (None, 1)
                name, sep, rest = descr[0].partition('=')
                if sep:
                    expr = descr[0].rstrip(":")
                    text = descr[1].lstrip(":- \t")
                else:
                    name, expr, text = params_descr.pop()
                    text += "\n" + ln
                params_descr.append ((name, expr, text))
            elif ln == "Parameters:":
                params_found = True
        return params_descr

    def _check_args (self, args):
        self.valid_arg_names = []
        passed_arg_names = args.keys() if args else []
        args_from_doc = self._parse_args_from_doc()
        if args_from_doc:
            self.valid_arg_names = list(zip(*args_from_doc)[0])
        invalid = set(passed_arg_names) - set(self.valid_arg_names)
        if invalid:
            raise ValueError ("Invalid handler argument: %s" % list(invalid))

    def get_arg (self, name, value_list, default = None):
        """ Return arg value or default; also check if value allowed. """
        default = default or value_list[0]
        val = type(default)(self.args.get(name, default))
        if val not in value_list:
            raise Exception('Bad argument %s value %r' % (name, val))
        return val

    def get_config (self):
        """ Process args dict (into handler config). """
        conf = skytools.dbdict()
        return conf

    def add(self, trigger_arg_list):
        """Called when table is added.

        Can modify trigger args.
        """
        pass

    def reset(self):
        """Called before starting to process a batch.
        Should clean any pending data.
        """
        pass

    def prepare_batch(self, batch_info, dst_curs):
        """Called on first event for this table in current batch."""
        pass

    def process_event(self, ev, sql_queue_func, arg):
        """Process a event.

        Event should be added to sql_queue or executed directly.
        """
        pass

    def finish_batch(self, batch_info, dst_curs):
        """Called when batch finishes."""
        pass

    def get_copy_condition(self, src_curs, dst_curs):
        """ Use if you want to filter data """
        return ''

    def real_copy(self, src_tablename, src_curs, dst_curs, column_list):
        """do actual table copy and return tuple with number of bytes and rows
        copied
        """
        condition = self.get_copy_condition(src_curs, dst_curs)
        return skytools.full_copy(src_tablename, src_curs, dst_curs,
                                  column_list, condition,
                                  dst_tablename = self.dest_table)

    def needs_table(self):
        """Does the handler need the table to exist on destination."""
        return True

class TableHandler(BaseHandler):
    """Default Londiste handler, inserts events into tables with plain SQL.

    Parameters:
      encoding=ENC - Validate and fix incoming data from encoding.
                     Only 'utf8' is supported at the moment.
      ignore_truncate=BOOL - Ignore truncate event. Default: 0; Values: 0,1.
    """
    handler_name = 'londiste'

    sql_command = {
        'I': "insert into %s %s;",
        'U': "update only %s set %s;",
        'D': "delete from only %s where %s;",
    }

    allow_sql_event = 1

    def __init__(self, table_name, args, dest_table):
        BaseHandler.__init__(self, table_name, args, dest_table)

        enc = args.get('encoding')
        if enc:
            self.encoding_validator = EncodingValidator(self.log, enc)
        else:
            self.encoding_validator = None

    def get_config (self):
        conf = BaseHandler.get_config(self)
        conf.ignore_truncate = self.get_arg('ignore_truncate', [0, 1], 0)
        return conf

    def process_event(self, ev, sql_queue_func, arg):
        row = self.parse_row_data(ev)
        if len(ev.type) == 1:
            # sql event
            fqname = self.fq_dest_table
            fmt = self.sql_command[ev.type]
            sql = fmt % (fqname, row)
        else:
            # urlenc event
            pklist = ev.type[2:].split(',')
            op = ev.type[0]
            tbl = self.dest_table
            if op == 'I':
                sql = skytools.mk_insert_sql(row, tbl, pklist)
            elif op == 'U':
                sql = skytools.mk_update_sql(row, tbl, pklist)
            elif op == 'D':
                sql = skytools.mk_delete_sql(row, tbl, pklist)

        sql_queue_func(sql, arg)

    def parse_row_data(self, ev):
        """Extract row data from event, with optional encoding fixes.

        Returns either string (sql event) or dict (urlenc event).
        """

        if len(ev.type) == 1:
            if not self.allow_sql_event:
                raise Exception('SQL events not supported by this handler')
            if self.encoding_validator:
                return self.encoding_validator.validate_string(ev.data, self.table_name)
            return ev.data
        else:
            row = skytools.db_urldecode(ev.data)
            if self.encoding_validator:
                return self.encoding_validator.validate_dict(row, self.table_name)
            return row

    def real_copy(self, src_tablename, src_curs, dst_curs, column_list):
        """do actual table copy and return tuple with number of bytes and rows
        copied
        """

        if self.encoding_validator:
            def _write_hook(obj, data):
                return self.encoding_validator.validate_copy(data, column_list, src_tablename)
        else:
            _write_hook = None
        condition = self.get_copy_condition(src_curs, dst_curs)
        return skytools.full_copy(src_tablename, src_curs, dst_curs,
                                  column_list, condition,
                                  dst_tablename = self.dest_table,
                                  write_hook = _write_hook)


#------------------------------------------------------------------------------
# ENCODING VALIDATOR
#------------------------------------------------------------------------------

class EncodingValidator:
    def __init__(self, log, encoding = 'utf-8', replacement = u'\ufffd'):
        """validates the correctness of given encoding. when data contains
        illegal symbols, replaces them with <replacement> and logs the
        incident
        """

        if encoding.lower() not in ('utf8', 'utf-8'):
            raise Exception('only utf8 supported')

        self.encoding = encoding
        self.log = log
        self.columns = None
        self.error_count = 0

    def show_error(self, col, val, pfx, unew):
        if pfx:
            col = pfx + '.' + col
        self.log.info('Fixed invalid UTF8 in column <%s>', col)
        self.log.debug('<%s>: old=%r new=%r', col, val, unew)

    def validate_copy(self, data, columns, pfx=""):
        """Validate tab-separated fields"""

        ok, _unicode = skytools.safe_utf8_decode(data)
        if ok:
            return data

        # log error
        vals = data.split('\t')
        for i, v in enumerate(vals):
            ok, tmp = skytools.safe_utf8_decode(v)
            if not ok:
                self.show_error(columns[i], v, pfx, tmp)

        # return safe data
        return _unicode.encode('utf8')

    def validate_dict(self, data, pfx=""):
        """validates data in dict"""
        for k, v in data.items():
            if v:
                ok, u = skytools.safe_utf8_decode(v)
                if not ok:
                    self.show_error(k, v, pfx, u)
                    data[k] = u.encode('utf8')
        return data

    def validate_string(self, value, pfx=""):
        """validate string"""
        ok, u = skytools.safe_utf8_decode(value)
        if ok:
            return value
        _pfx = pfx and (pfx+': ') or ""
        self.log.info('%sFixed invalid UTF8 in string <%s>', _pfx, value)
        return u.encode('utf8')

#
# handler management
#

_handler_map = {
    'londiste': TableHandler,
}

_handler_list = _handler_map.keys()

def register_handler_module(modname):
    """Import and module and register handlers."""
    try:
        __import__(modname)
    except ImportError:
        print "Failed to load handler module: %s" % (modname,)
        return
    m = sys.modules[modname]
    for h in m.__londiste_handlers__:
        _handler_map[h.handler_name] = h
        _handler_list.append(h.handler_name)

def _parse_arglist(arglist):
    args = {}
    for arg in arglist or []:
        key, _, val = arg.partition('=')
        key = key.strip()
        if key in args:
            raise Exception('multiple handler arguments: %s' % key)
        args[key] = val.strip()
    return args

def create_handler_string(name, arglist):
    handler = name
    if name.find('(') >= 0:
        raise Exception('invalid handler name: %s' % name)
    if arglist:
        args = _parse_arglist(arglist)
        astr = skytools.db_urlencode(args)
        handler = '%s(%s)' % (handler, astr)
    return handler

def _parse_handler(hstr):
    """Parse result of create_handler_string()."""
    args = {}
    name = hstr
    pos = hstr.find('(')
    if pos > 0:
        name = hstr[ : pos]
        if hstr[-1] != ')':
            raise Exception('invalid handler format: %s' % hstr)
        astr = hstr[pos + 1 : -1]
        if astr:
            astr = astr.replace(',', '&')
            args = skytools.db_urldecode(astr)
    return (name, args)

def build_handler(tblname, hstr, dest_table=None):
    """Parse and initialize handler.

    hstr is result of create_handler_string()."""
    hname, args = _parse_handler(hstr)
    # when no handler specified, use londiste
    hname = hname or 'londiste'
    klass = _handler_map[hname]
    if not dest_table:
        dest_table = tblname
    return klass(tblname, args, dest_table)

def load_handler_modules(cf):
    """Load and register modules from config."""
    lst = londiste.handlers.DEFAULT_HANDLERS
    lst += cf.getlist('handler_modules', [])

    for m in lst:
        register_handler_module(m)

def show(mods):
    if not mods:
        if 0:
            names = _handler_map.keys()
            names.sort()
        else:
            names = _handler_list
        for n in names:
            kls = _handler_map[n]
            desc = kls.__doc__ or ''
            if desc:
                desc = desc.strip().split('\n', 1)[0]
            print("%s - %s" % (n, desc))
    else:
        for n in mods:
            kls = _handler_map[n]
            desc = kls.__doc__ or ''
            if desc:
                desc = desc.strip()
            print("%s - %s" % (n, desc))

########NEW FILE########
__FILENAME__ = applyfn
"""
Send all events to a DB function.
"""

import skytools
from londiste.handler import BaseHandler

__all__ = ['ApplyFuncHandler']

class ApplyFuncHandler(BaseHandler):
    """Call DB function to apply event.

    Parameters:
      func_name=NAME - database function name
      func_conf=CONF - database function conf
    """
    handler_name = 'applyfn'

    def prepare_batch(self, batch_info, dst_curs):
        self.cur_tick = batch_info['tick_id']

    def process_event(self, ev, sql_queue_func, qfunc_arg):
        """Ignore events for this table"""
        fn = self.args.get('func_name')
        fnconf = self.args.get('func_conf', '')

        args = [fnconf, self.cur_tick,
                ev.ev_id, ev.ev_time,
                ev.ev_txid, ev.ev_retry,
                ev.ev_type, ev.ev_data,
                ev.ev_extra1, ev.ev_extra2,
                ev.ev_extra3, ev.ev_extra4]

        qfn = skytools.quote_fqident(fn)
        qargs = [skytools.quote_literal(a) for a in args]
        sql = "select %s(%s);" % (qfn, ', '.join(qargs))
        self.log.debug('applyfn.sql: %s', sql)
        sql_queue_func(sql, qfunc_arg)

#------------------------------------------------------------------------------
# register handler class
#------------------------------------------------------------------------------

__londiste_handlers__ = [ApplyFuncHandler]

########NEW FILE########
__FILENAME__ = bulk
"""
Bulk loading into OLAP database.

To use set in londiste.ini:

    handler_modules = londiste.handlers.bulk

then add table with:
  londiste3 add-table xx --handler="bulk"

or:
  londiste3 add-table xx --handler="bulk(method=X)"

Methods:

  0 (correct) - inserts as COPY into table,
                update as COPY into temp table and single UPDATE from there
                delete as COPY into temp table and single DELETE from there
  1 (delete)  - as 'correct', but do update as DELETE + COPY
  2 (merged)  - as 'delete', but merge insert rows with update rows

Default is 0.

"""

import skytools

from londiste.handler import BaseHandler, RowCache
from skytools import quote_ident, quote_fqident

__all__ = ['BulkLoader']

# BulkLoader load method
METH_CORRECT = 0
METH_DELETE = 1
METH_MERGED = 2
DEFAULT_METHOD = METH_CORRECT

# BulkLoader hacks
AVOID_BIZGRES_BUG = 0
USE_LONGLIVED_TEMP_TABLES = True

USE_REAL_TABLE = False

class BulkEvent(object):
    """Helper class for BulkLoader to store relevant data."""
    __slots__ = ('op', 'data', 'pk_data')
    def __init__(self, op, data, pk_data):
        self.op = op
        self.data = data
        self.pk_data = pk_data

class BulkLoader(BaseHandler):
    """Bulk loading into OLAP database.
    Instead of statement-per-event, load all data with one big COPY, UPDATE
    or DELETE statement.

    Parameters:
      method=TYPE - method to use for copying [0..2] (default: 0)

    Methods:
      0 (correct) - inserts as COPY into table,
                    update as COPY into temp table and single UPDATE from there
                    delete as COPY into temp table and single DELETE from there
      1 (delete)  - as 'correct', but do update as DELETE + COPY
      2 (merged)  - as 'delete', but merge insert rows with update rows
    """
    handler_name = 'bulk'
    fake_seq = 0

    def __init__(self, table_name, args, dest_table):
        """Init per-batch table data cache."""

        BaseHandler.__init__(self, table_name, args, dest_table)

        self.pkey_list = None
        self.dist_fields = None
        self.col_list = None

        self.pkey_ev_map = {}
        self.method = int(args.get('method', DEFAULT_METHOD))
        if not self.method in (0,1,2):
            raise Exception('unknown method: %s' % self.method)

        self.log.debug('bulk_init(%r), method=%d', args, self.method)

    def reset(self):
        self.pkey_ev_map = {}
        BaseHandler.reset(self)

    def finish_batch(self, batch_info, dst_curs):
        self.bulk_flush(dst_curs)

    def process_event(self, ev, sql_queue_func, arg):
        if len(ev.ev_type) < 2 or ev.ev_type[1] != ':':
            raise Exception('Unsupported event type: %s/extra1=%s/data=%s' % (
                            ev.ev_type, ev.ev_extra1, ev.ev_data))
        op = ev.ev_type[0]
        if op not in 'IUD':
            raise Exception('Unknown event type: '+ev.ev_type)
        # pkey_list = ev.ev_type[2:].split(',')
        data = skytools.db_urldecode(ev.ev_data)

        # get pkey value
        if self.pkey_list is None:
            #self.pkey_list = pkey_list
            self.pkey_list = ev.ev_type[2:].split(',')
        if len(self.pkey_list) > 0:
            pk_data = tuple(data[k] for k in self.pkey_list)
        elif op == 'I':
            # fake pkey, just to get them spread out
            pk_data = self.fake_seq
            self.fake_seq += 1
        else:
            raise Exception('non-pk tables not supported: %s' % self.table_name)

        # get full column list, detect added columns
        if not self.col_list:
            self.col_list = data.keys()
        elif self.col_list != data.keys():
            # ^ supposedly python guarantees same order in keys()
            self.col_list = data.keys()

        # keep all versions of row data
        ev = BulkEvent(op, data, pk_data)
        if ev.pk_data in self.pkey_ev_map:
            self.pkey_ev_map[ev.pk_data].append(ev)
        else:
            self.pkey_ev_map[ev.pk_data] = [ev]

    def prepare_data(self):
        """Got all data, prepare for insertion."""

        del_list = []
        ins_list = []
        upd_list = []
        for ev_list in self.pkey_ev_map.itervalues():
            # rewrite list of I/U/D events to
            # optional DELETE and optional INSERT/COPY command
            exists_before = -1
            exists_after = 1
            for ev in ev_list:
                if ev.op == "I":
                    if exists_before < 0:
                        exists_before = 0
                    exists_after = 1
                elif ev.op == "U":
                    if exists_before < 0:
                        exists_before = 1
                    #exists_after = 1 # this shouldnt be needed
                elif ev.op == "D":
                    if exists_before < 0:
                        exists_before = 1
                    exists_after = 0
                else:
                    raise Exception('unknown event type: %s' % ev.op)

            # skip short-lived rows
            if exists_before == 0 and exists_after == 0:
                continue

            # take last event
            ev = ev_list[-1]

            # generate needed commands
            if exists_before and exists_after:
                upd_list.append(ev.data)
            elif exists_before:
                del_list.append(ev.data)
            elif exists_after:
                ins_list.append(ev.data)

        return ins_list, upd_list, del_list

    def bulk_flush(self, curs):
        ins_list, upd_list, del_list = self.prepare_data()

        # reorder cols, put pks first
        col_list = self.pkey_list[:]
        for k in self.col_list:
            if k not in self.pkey_list:
                col_list.append(k)

        real_update_count = len(upd_list)

        self.log.debug("bulk_flush: %s  (I/U/D = %d/%d/%d)",
                self.table_name, len(ins_list), len(upd_list), len(del_list))

        # hack to unbroke stuff
        if self.method == METH_MERGED:
            upd_list += ins_list
            ins_list = []

        # fetch distribution fields
        if self.dist_fields is None:
            self.dist_fields = self.find_dist_fields(curs)

        key_fields = self.pkey_list[:]
        for fld in self.dist_fields:
            if fld not in key_fields:
                key_fields.append(fld)
        self.log.debug("PKey fields: %s  Dist fields: %s",
                       ",".join(self.pkey_list), ",".join(self.dist_fields))

        # create temp table
        temp, qtemp = self.create_temp_table(curs)
        tbl = self.dest_table
        qtbl = self.fq_dest_table

        # where expr must have pkey and dist fields
        klist = []
        for pk in key_fields:
            exp = "%s.%s = %s.%s" % (qtbl, quote_ident(pk),
                                     qtemp, quote_ident(pk))
            klist.append(exp)
        whe_expr = " and ".join(klist)

        # create del sql
        del_sql = "delete from only %s using %s where %s" % (qtbl, qtemp, whe_expr)

        # create update sql
        slist = []
        for col in col_list:
            if col not in key_fields:
                exp = "%s = %s.%s" % (quote_ident(col), qtemp, quote_ident(col))
                slist.append(exp)
        upd_sql = "update only %s set %s from %s where %s" % (
                   qtbl, ", ".join(slist), qtemp, whe_expr)

        # avoid updates on pk-only table
        if not slist:
            upd_list = []

        # insert sql
        colstr = ",".join([quote_ident(c) for c in col_list])
        ins_sql = "insert into %s (%s) select %s from %s" % (
                  qtbl, colstr, colstr, qtemp)

        temp_used = False

        # process deleted rows
        if len(del_list) > 0:
            self.log.debug("bulk: Deleting %d rows from %s", len(del_list), tbl)
            # delete old rows
            q = "truncate %s" % qtemp
            self.log.debug('bulk: %s', q)
            curs.execute(q)
            # copy rows
            self.log.debug("bulk: COPY %d rows into %s", len(del_list), temp)
            skytools.magic_insert(curs, qtemp, del_list, col_list, quoted_table=1)
            # delete rows
            self.log.debug('bulk: %s', del_sql)
            curs.execute(del_sql)
            self.log.debug("bulk: %s - %d", curs.statusmessage, curs.rowcount)
            if len(del_list) != curs.rowcount:
                self.log.warning("Delete mismatch: expected=%s deleted=%d",
                        len(del_list), curs.rowcount)
            temp_used = True

        # process updated rows
        if len(upd_list) > 0:
            self.log.debug("bulk: Updating %d rows in %s", len(upd_list), tbl)
            # delete old rows
            q = "truncate %s" % qtemp
            self.log.debug('bulk: %s', q)
            curs.execute(q)
            # copy rows
            self.log.debug("bulk: COPY %d rows into %s", len(upd_list), temp)
            skytools.magic_insert(curs, qtemp, upd_list, col_list, quoted_table=1)
            temp_used = True
            if self.method == METH_CORRECT:
                # update main table
                self.log.debug('bulk: %s', upd_sql)
                curs.execute(upd_sql)
                self.log.debug("bulk: %s - %d", curs.statusmessage, curs.rowcount)
                # check count
                if len(upd_list) != curs.rowcount:
                    self.log.warning("Update mismatch: expected=%s updated=%d",
                            len(upd_list), curs.rowcount)
            else:
                # delete from main table
                self.log.debug('bulk: %s', del_sql)
                curs.execute(del_sql)
                self.log.debug('bulk: %s', curs.statusmessage)
                # check count
                if real_update_count != curs.rowcount:
                    self.log.warning("bulk: Update mismatch: expected=%s deleted=%d",
                            real_update_count, curs.rowcount)
                # insert into main table
                if AVOID_BIZGRES_BUG:
                    # copy again, into main table
                    self.log.debug("bulk: COPY %d rows into %s", len(upd_list), tbl)
                    skytools.magic_insert(curs, qtbl, upd_list, col_list, quoted_table=1)
                else:
                    # better way, but does not work due bizgres bug
                    self.log.debug('bulk: %s', ins_sql)
                    curs.execute(ins_sql)
                    self.log.debug('bulk: %s', curs.statusmessage)

        # process new rows
        if len(ins_list) > 0:
            self.log.debug("bulk: Inserting %d rows into %s", len(ins_list), tbl)
            self.log.debug("bulk: COPY %d rows into %s", len(ins_list), tbl)
            skytools.magic_insert(curs, qtbl, ins_list, col_list, quoted_table=1)

        # delete remaining rows
        if temp_used:
            if USE_LONGLIVED_TEMP_TABLES or USE_REAL_TABLE:
                q = "truncate %s" % qtemp
            else:
                # fscking problems with long-lived temp tables
                q = "drop table %s" % qtemp
            self.log.debug('bulk: %s', q)
            curs.execute(q)

        self.reset()

    def create_temp_table(self, curs):
        if USE_REAL_TABLE:
            tempname = self.dest_table + "_loadertmpx"
        else:
            # create temp table for loading
            tempname = self.dest_table.replace('.', '_') + "_loadertmp"

        # check if exists
        if USE_REAL_TABLE:
            if skytools.exists_table(curs, tempname):
                self.log.debug("bulk: Using existing real table %s", tempname)
                return tempname, quote_fqident(tempname)

            # create non-temp table
            q = "create table %s (like %s)" % (
                        quote_fqident(tempname),
                        quote_fqident(self.dest_table))
            self.log.debug("bulk: Creating real table: %s", q)
            curs.execute(q)
            return tempname, quote_fqident(tempname)
        elif USE_LONGLIVED_TEMP_TABLES:
            if skytools.exists_temp_table(curs, tempname):
                self.log.debug("bulk: Using existing temp table %s", tempname)
                return tempname, quote_ident(tempname)

        # bizgres crashes on delete rows
        # removed arg = "on commit delete rows"
        arg = "on commit preserve rows"
        # create temp table for loading
        q = "create temp table %s (like %s) %s" % (
                quote_ident(tempname), quote_fqident(self.dest_table), arg)
        self.log.debug("bulk: Creating temp table: %s", q)
        curs.execute(q)
        return tempname, quote_ident(tempname)

    def find_dist_fields(self, curs):
        if not skytools.exists_table(curs, "pg_catalog.gp_distribution_policy"):
            return []
        schema, name = skytools.fq_name_parts(self.dest_table)
        q = "select a.attname"\
            "  from pg_class t, pg_namespace n, pg_attribute a,"\
            "       gp_distribution_policy p"\
            " where n.oid = t.relnamespace"\
            "   and p.localoid = t.oid"\
            "   and a.attrelid = t.oid"\
            "   and a.attnum = any(p.attrnums)"\
            "   and n.nspname = %s and t.relname = %s"
        curs.execute(q, [schema, name])
        res = []
        for row in curs.fetchall():
            res.append(row[0])
        return res


# register handler class
__londiste_handlers__ = [BulkLoader]

########NEW FILE########
__FILENAME__ = dispatch
"""
== HANDLERS ==

* dispatch - "vanilla" dispatch handler with default args (see below)
* hourly_event
* hourly_batch
* hourly_field
* hourly_time
* daily_event
* daily_batch
* daily_field
* daily_time
* monthly_event
* monthly_batch
* monthly_field
* monthly_time
* yearly_event
* yearly_batch
* yearly_field
* yearly_time
* bulk_hourly_event
* bulk_hourly_batch
* bulk_hourly_field
* bulk_hourly_time
* bulk_daily_event
* bulk_daily_batch
* bulk_daily_field
* bulk_daily_time
* bulk_monthly_event
* bulk_monthly_batch
* bulk_monthly_field
* bulk_monthly_time
* bulk_yearly_event
* bulk_yearly_batch
* bulk_yearly_field
* bulk_yearly_time
* bulk_direct - functionally identical to bulk

== HANDLER ARGUMENTS ==

table_mode:
    * part - partitioned table (default)
    * direct - non-partitioned table
    * ignore - all events are ignored

part_func:
    database function to use for creating partition table.
    default is {londiste|public}.create_partition

part_mode:
    * batch_time - partitioned by batch creation time (default)
    * event_time - partitioned by event creation time
    * date_field - partitioned by date_field value. part_field required
    * current_time - partitioned by current time

part_field:
    date_field to use for partition. Required when part_mode=date_field

period:
    partition period, used for automatic part_name and part_template building
    * hour
    * day - default
    * month
    * year

part_name:
    custom name template for partition table. default is None as it is built
    automatically.
    example for daily partition: %(parent)s_%(year)s_%(month)s_%(day)s
    template variables:
    * parent - parent table name
    * year
    * month
    * day
    * hour

part_template:
    custom sql template for creating partition table. if omitted then partition
    function is used.
    template variables:
    * dest - destination table name. result on part_name evaluation
    * part - same as dest
    * parent - parent table name
    * pkey - parent table primary keys
    * schema_table - table name with replace: '.' -> '__'. for using in
        pk names etc.
    * part_field - date field name if table is partitioned by field
    * part_time - time of partition

row_mode:
    how rows are applied to target table
    * plain - each event creates SQL statement to run (default)
    * keep_latest - change updates to DELETE + INSERT
    * keep_all - change updates to inserts, ignore deletes

event_types:
    event types to process, separated by comma. Other events are ignored.
    default is all event types
    * I - inserts
    * U - updates
    * D - deletes

load_mode:
    how data is loaded to dst database. default direct
    * direct - using direct sql statements (default)
    * bulk - using copy to temp table and then sql.

method:
    loading method for load_mode bulk. defaults to 0
    * 0 (correct) - inserts as COPY into table,
                    update as COPY into temp table and single UPDATE from there
                    delete as COPY into temp table and single DELETE from there
    * 1 (delete)  - as 'correct', but do update as DELETE + COPY
    * 2 (merged)  - as 'delete', but merge insert rows with update rows
    * 3 (insert)  - COPY inserts into table, error when other events

fields:
    field name map for using just part of the fields and rename them
    * '*' - all fields. default
    * <field>[,<field>..] - list of source fields to include in target
    * <field>:<new_name> - renaming fields
    list and rename syntax can be mixed: field1,field2:new_field2,field3

skip_fields:
    list of field names to skip

table:
    new name of destination table. default is same as source

pre_part:
    sql statement(s) to execute before creating partition table. Usable
    variables are the same as in part_template

post_part:
    sql statement(s) to execute after creating partition table. Usable
    variables are the same as in part_template

retention_period:
    how long to keep partitions around. examples: '3 months', '1 year'

ignore_old_events:
    * 0 - handle all events in the same way (default)
    * 1 - ignore events coming for obsolete partitions

ignore_truncate:
    * 0 - process truncate event (default)
    * 1 - ignore truncate event

encoding:
    name of destination encoding. handler replaces all invalid encoding symbols
    and logs them as warnings

analyze:
    * 0 - do not run analyze on temp tables (default)
    * 1 - run analyze on temp tables

== NOTES ==

NB! londiste3 does not currently support table renaming and field mapping when
creating or coping initial data to destination table.  --expect-sync and
--skip-truncate should be used and --create switch is to be avoided.
"""

import codecs
import datetime
import re
import sys
from functools import partial

import skytools
from skytools import quote_ident, quote_fqident, UsageError
from skytools.dbstruct import *
from skytools.utf8 import safe_utf8_decode

from londiste.handler import EncodingValidator
from londiste.handlers import handler_args, update
from londiste.handlers.shard import ShardHandler


__all__ = ['Dispatcher']

# BulkLoader load method
METH_CORRECT = 0
METH_DELETE = 1
METH_MERGED = 2
METH_INSERT = 3

# BulkLoader hacks
AVOID_BIZGRES_BUG = 0
USE_LONGLIVED_TEMP_TABLES = True
USE_REAL_TABLE = False

# mode variables (first in list is default value)
TABLE_MODES = ['part', 'direct', 'ignore']
PART_MODES = ['batch_time', 'event_time', 'date_field', 'current_time']
ROW_MODES = ['plain', 'keep_all', 'keep_latest']
LOAD_MODES = ['direct', 'bulk']
PERIODS = ['day', 'month', 'year', 'hour']
METHODS = [METH_CORRECT, METH_DELETE, METH_MERGED, METH_INSERT]

EVENT_TYPES = ['I', 'U', 'D']

PART_FUNC_OLD = 'public.create_partition'
PART_FUNC_NEW = 'londiste.create_partition'
PART_FUNC_ARGS = ['parent', 'part', 'pkeys', 'part_field', 'part_time', 'period']

RETENTION_FUNC = "londiste.drop_obsolete_partitions"



#------------------------------------------------------------------------------
# LOADERS
#------------------------------------------------------------------------------


class BaseLoader:
    def __init__(self, table, pkeys, log, conf):
        self.table = table
        self.pkeys = pkeys
        self.log = log
        self.conf = conf or {}

    def process(self, op, row):
        raise NotImplementedError()

    def flush(self, curs):
        raise NotImplementedError()


class DirectLoader(BaseLoader):
    def __init__(self, table, pkeys, log, conf):
        BaseLoader.__init__(self, table, pkeys, log, conf)
        self.data = []

    def process(self, op, row):
        self.data.append((op, row))

    def flush(self, curs):
        mk_sql = {'I': skytools.mk_insert_sql,
                  'U': skytools.mk_update_sql,
                  'D': skytools.mk_delete_sql}
        if self.data:
            curs.execute("\n".join(mk_sql[op](row, self.table, self.pkeys)
                                   for op, row in self.data))


class BaseBulkCollectingLoader(BaseLoader):
    """ Collect events into I,U,D lists by pk and keep only last event
    with most suitable operation. For example when event has operations I,U,U
    keep only last U, when I,U,D, keep nothing etc

    If after processing the op is not in I,U or D, then ignore that event for
    rest
    """
    OP_GRAPH = {None:{'U':'U', 'I':'I', 'D':'D'},
                'I':{'D':'.'},
                'U':{'D':'D'},
                'D':{'I':'U'},
                '.':{'I':'I'},
                }
    def __init__(self, table, pkeys, log, conf):
        BaseLoader.__init__(self, table, pkeys, log, conf)
        if not self.pkeys:
            raise Exception('non-pk tables not supported: %s' % self.table)
        self.pkey_ev_map = {}

    def process(self, op, row):
        """Collect rows into pk dict, keeping only last row with most
        suitable op"""
        pk_data = tuple(row[k] for k in self.pkeys)
        # get current op state, None if first event
        _op = self.pkey_ev_map.get(pk_data, (None,))[0]
        # find new state and store together with row data
        try:
            # get new op state using op graph
            # when no edge defined for old -> new op, keep old
            _op = self.OP_GRAPH[_op].get(op, _op)
            self.pkey_ev_map[pk_data] = (_op, row)

            # skip update to pk-only table
            if len(pk_data) == len(row) and _op == 'U':
                del self.pkey_ev_map[pk_data]
        except KeyError:
            raise Exception('unknown event type: %s' % op)

    def collect_data(self):
        """Collects list of rows into operation hashed dict
        """
        op_map = {'I': [], 'U': [], 'D': []}
        for op, row in self.pkey_ev_map.itervalues():
            # ignore None op events
            if op in op_map:
                op_map[op].append(row)
        return op_map

    def flush(self, curs):
        op_map = self.collect_data()
        self.bulk_flush(curs, op_map)

    def bulk_flush(self, curs, op_map):
        pass


class BaseBulkTempLoader(BaseBulkCollectingLoader):
    """ Provide methods for operating bulk collected events with temp table
    """
    def __init__(self, table, pkeys, log, conf):
        BaseBulkCollectingLoader.__init__(self, table, pkeys, log, conf)
        # temp table name
        if USE_REAL_TABLE:
            self.temp =  self.table + "_loadertmpx"
            self.qtemp = quote_fqident(self.temp)
        else:
            self.temp =  self.table.replace('.', '_') + "_loadertmp"
            self.qtemp = quote_ident(self.temp)
        # quoted table name
        self.qtable = quote_fqident(self.table)
        # all fields
        self.fields = None
        # key fields used in where part, possible to add non pk fields
        # (like dist keys in gp)
        self.keys = self.pkeys[:]

    def nonkeys(self):
        """returns fields not in keys"""
        return [f for f in self.fields if f not in self.keys]

    def logexec(self, curs, sql):
        """Logs and executes sql statement"""
        self.log.debug('exec: %s', sql)
        curs.execute(sql)
        self.log.debug('msg: %s, rows: %s', curs.statusmessage, curs.rowcount)

    # create sql parts

    def _where(self):
        tmpl = "%(tbl)s.%(col)s = t.%(col)s"
        stmt = (tmpl % {'col': quote_ident(f),
                         'tbl': self.qtable,
                        }
                for f in self.keys)
        return ' and '.join(stmt)

    def _cols(self):
        return ','.join(quote_ident(f) for f in self.fields)

    def insert(self, curs):
        sql = "insert into %s (%s) select %s from %s" % (
                self.qtable, self._cols(), self._cols(), self.qtemp)
        return self.logexec(curs, sql)

    def update(self, curs):
        qcols = [quote_ident(c) for c in self.nonkeys()]

        # no point to update pk-only table
        if not qcols:
            return

        tmpl = "%s = t.%s"
        eqlist = [tmpl % (c,c) for c in qcols]
        _set =  ", ".join(eqlist)

        sql = "update only %s set %s from %s as t where %s" % (
                self.qtable, _set, self.qtemp, self._where())
        return self.logexec(curs, sql)

    def delete(self, curs):
        sql = "delete from only %s using %s as t where %s" % (
                self.qtable, self.qtemp, self._where())
        return self.logexec(curs, sql)

    def truncate(self, curs):
        return self.logexec(curs, "truncate %s" % self.qtemp)

    def drop(self, curs):
        return self.logexec(curs, "drop table %s" % self.qtemp)

    def create(self, curs):
        if USE_REAL_TABLE:
            tmpl = "create table %s (like %s)"
        else:
            tmpl = "create temp table %s (like %s) on commit preserve rows"
        return self.logexec(curs, tmpl % (self.qtemp, self.qtable))

    def analyze(self, curs):
        return self.logexec(curs, "analyze %s" % self.qtemp)

    def process(self, op, row):
        BaseBulkCollectingLoader.process(self, op, row)
        # TODO: maybe one assignment is enough?
        self.fields = row.keys()


class BulkLoader(BaseBulkTempLoader):
    """ Collects events to and loads bulk data using copy and temp tables
    """
    def __init__(self, table, pkeys, log, conf):
        BaseBulkTempLoader.__init__(self, table, pkeys, log, conf)
        self.method = self.conf['method']
        self.run_analyze = self.conf['analyze']
        self.dist_fields = None
        # is temp table created
        self.temp_present = False

    def process(self, op, row):
        if self.method == METH_INSERT and op != 'I':
            raise Exception('%s not supported by method insert' % op)
        BaseBulkTempLoader.process(self, op, row)

    def process_delete(self, curs, op_map):
        """Process delete list"""
        data = op_map['D']
        cnt = len(data)
        if (cnt == 0):
            return
        self.log.debug("bulk: Deleting %d rows from %s", cnt, self.table)
        # copy rows to temp
        self.bulk_insert(curs, data)
        # delete rows using temp
        self.delete(curs)
        # check if right amount of rows deleted (only in direct mode)
        if self.conf.table_mode == 'direct' and cnt != curs.rowcount:
            self.log.warning("%s: Delete mismatch: expected=%s deleted=%d",
                    self.table, cnt, curs.rowcount)

    def process_update(self, curs, op_map):
        """Process update list"""
        data = op_map['U']
        # original update list count
        real_cnt = len(data)
        # merged method loads inserts together with updates
        if self.method == METH_MERGED:
            data += op_map['I']
        cnt = len(data)
        if (cnt == 0):
            return
        self.log.debug("bulk: Updating %d rows in %s", cnt, self.table)
        # copy rows to temp
        self.bulk_insert(curs, data)
        if self.method == METH_CORRECT:
            # update main table from temp
            self.update(curs)
            # check count (only in direct mode)
            if self.conf.table_mode == 'direct' and cnt != curs.rowcount:
                self.log.warning("%s: Update mismatch: expected=%s updated=%d",
                        self.table, cnt, curs.rowcount)
        else:
            # delete from main table using temp
            self.delete(curs)
            # check count (only in direct mode)
            if self.conf.table_mode == 'direct' and real_cnt != curs.rowcount:
                self.log.warning("%s: Update mismatch: expected=%s deleted=%d",
                        self.table, real_cnt, curs.rowcount)
            # insert into main table
            if AVOID_BIZGRES_BUG:
                # copy again, into main table
                self.bulk_insert(curs, data, table = self.qtable)
            else:
                # insert from temp - better way, but does not work
                # due bizgres bug
                self.insert(curs)

    def process_insert(self, curs, op_map):
        """Process insert list"""
        data = op_map['I']
        cnt = len(data)
        # merged method loads inserts together with updates
        if (cnt == 0) or (self.method == METH_MERGED):
            return
        self.log.debug("bulk: Inserting %d rows into %s", cnt, self.table)
        # copy into target table (no temp used)
        self.bulk_insert(curs, data, table = self.qtable)

    def bulk_flush(self, curs, op_map):
        self.log.debug("bulk_flush: %s  (I/U/D = %d/%d/%d)", self.table,
                len(op_map['I']), len(op_map['U']), len(op_map['D']))

        # fetch distribution fields
        if self.dist_fields is None:
            self.dist_fields = self.find_dist_fields(curs)
            self.log.debug("Key fields: %s  Dist fields: %s",
                           ",".join(self.pkeys), ",".join(self.dist_fields))
            # add them to key
            for key in self.dist_fields:
                if key not in self.keys:
                    self.keys.append(key)

        # check if temp table present
        self.check_temp(curs)
        # process I,U,D
        self.process_delete(curs, op_map)
        self.process_update(curs, op_map)
        self.process_insert(curs, op_map)
        # truncate or drop temp table
        self.clean_temp(curs)

    def check_temp(self, curs):
        if USE_REAL_TABLE:
            self.temp_present = skytools.exists_table(curs, self.temp)
        else:
            self.temp_present = skytools.exists_temp_table(curs, self.temp)

    def clean_temp(self, curs):
        # delete remaining rows
        if self.temp_present:
            if USE_LONGLIVED_TEMP_TABLES or USE_REAL_TABLE:
                self.truncate(curs)
            else:
                # fscking problems with long-lived temp tables
                self.drop(curs)

    def create_temp(self, curs):
        """ check if temp table exists. Returns False if using existing temp
        table and True if creating new
        """
        if USE_LONGLIVED_TEMP_TABLES or USE_REAL_TABLE:
            if self.temp_present:
                self.log.debug("bulk: Using existing temp table %s", self.temp)
                return False
        self.create(curs)
        self.temp_present = True
        return True

    def bulk_insert(self, curs, data, table = None):
        """Copy data to table. If table not provided, use temp table.
        When re-using existing temp table, it is always truncated first and
        analyzed after copy.
        """
        if not data:
            return
        _use_temp = table is None
        # if table not specified use temp
        if _use_temp:
            table = self.temp
            # truncate when re-using existing table
            if not self.create_temp(curs):
                self.truncate(curs)
        self.log.debug("bulk: COPY %d rows into %s", len(data), table)
        skytools.magic_insert(curs, table, data, self.fields,
                              quoted_table = True)
        if _use_temp and self.run_analyze:
            self.analyze(curs)

    def find_dist_fields(self, curs):
        """Find GP distribution keys"""
        if not skytools.exists_table(curs, "pg_catalog.gp_distribution_policy"):
            return []
        schema, name = skytools.fq_name_parts(self.table)
        qry = "select a.attname"\
            "  from pg_class t, pg_namespace n, pg_attribute a,"\
            "       gp_distribution_policy p"\
            " where n.oid = t.relnamespace"\
            "   and p.localoid = t.oid"\
            "   and a.attrelid = t.oid"\
            "   and a.attnum = any(p.attrnums)"\
            "   and n.nspname = %s and t.relname = %s"
        curs.execute(qry, [schema, name])
        res = []
        for row in curs.fetchall():
            res.append(row[0])
        return res


LOADERS = {'direct': DirectLoader, 'bulk': BulkLoader}



#------------------------------------------------------------------------------
# ROW HANDLERS
#------------------------------------------------------------------------------


class RowHandler:
    def __init__(self, log):
        self.log = log
        self.table_map = {}

    def add_table(self, table, ldr_cls, pkeys, args):
        self.table_map[table] = ldr_cls(table, pkeys, self.log, args)

    def process(self, table, op, row):
        try:
            self.table_map[table].process(op, row)
        except KeyError:
            raise Exception("No loader for table %s" % table)

    def flush(self, curs):
        for ldr in self.table_map.values():
            ldr.flush(curs)


class KeepAllRowHandler(RowHandler):
    def process(self, table, op, row):
        """Keep all row versions.

        Updates are changed to inserts, deletes are ignored.
        Makes sense only for partitioned tables.
        """
        if op == 'U':
            op = 'I'
        elif op == 'D':
            return
        RowHandler.process(self, table, op, row)


class KeepLatestRowHandler(RowHandler):
    def process(self, table, op, row):
        """Keep latest row version.

        Updates are changed to delete + insert
        Makes sense only for partitioned tables.
        """
        if op == 'U':
            RowHandler.process(self, table, 'D', row)
            RowHandler.process(self, table, 'I', row)
        elif op == 'I':
            RowHandler.process(self, table, 'I', row)
        elif op == 'D':
            RowHandler.process(self, table, 'D', row)


ROW_HANDLERS = {'plain': RowHandler,
                'keep_all': KeepAllRowHandler,
                'keep_latest': KeepLatestRowHandler}


#------------------------------------------------------------------------------
# DISPATCHER
#------------------------------------------------------------------------------


class Dispatcher (ShardHandler):
    """Partitioned loader.
    Splits events into partitions, if requested.
    Then applies them without further processing.
    """
    handler_name = 'dispatch'

    def __init__(self, table_name, args, dest_table):

        # compat for dest-table
        dest_table = args.get('table', dest_table)

        ShardHandler.__init__(self, table_name, args, dest_table)

        # show args
        self.log.debug("dispatch.init: table_name=%r, args=%r", table_name, args)
        self.ignored_tables = set()
        self.batch_info = None
        self.dst_curs = None
        self.pkeys = None
        # config
        hdlr_cls = ROW_HANDLERS[self.conf.row_mode]
        self.row_handler = hdlr_cls(self.log)

    def _parse_args_from_doc (self):
        doc = __doc__
        params_descr = []
        params_found = False
        for line in doc.splitlines():
            ln = line.strip()
            if params_found:
                if ln.startswith("=="):
                    break
                m = re.match ("^(\w+):$", ln)
                if m:
                    name = m.group(1)
                    expr = text = ""
                elif not params_descr:
                    continue
                else:
                    name, expr, text = params_descr.pop()
                    text += ln + "\n"
                params_descr.append ((name, expr, text))
            elif ln == "== HANDLER ARGUMENTS ==":
                params_found = True
        return params_descr

    def get_config(self):
        """Processes args dict"""
        conf = ShardHandler.get_config(self)
        # set table mode
        conf.table_mode = self.get_arg('table_mode', TABLE_MODES)
        conf.analyze = self.get_arg('analyze', [0, 1])
        if conf.table_mode == 'part':
            conf.part_mode = self.get_arg('part_mode', PART_MODES)
            conf.part_field = self.args.get('part_field')
            if conf.part_mode == 'date_field' and not conf.part_field :
                raise Exception('part_mode date_field requires part_field!')
            conf.period = self.get_arg('period', PERIODS)
            conf.part_name = self.args.get('part_name')
            conf.part_template = self.args.get('part_template')
            conf.pre_part = self.args.get('pre_part')
            conf.post_part = self.args.get('post_part')
            conf.part_func = self.args.get('part_func', PART_FUNC_NEW)
            conf.retention_period = self.args.get('retention_period')
            conf.ignore_old_events = self.get_arg('ignore_old_events', [0, 1], 0)
        # set row mode and event types to process
        conf.row_mode = self.get_arg('row_mode', ROW_MODES)
        event_types = self.args.get('event_types', '*')
        if event_types == '*':
            event_types = EVENT_TYPES
        else:
            event_types = [evt.upper() for evt in event_types.split(',')]
            for evt in event_types:
                if evt not in EVENT_TYPES:
                    raise Exception('Unsupported operation: %s' % evt)
        conf.event_types = event_types
        # set load handler
        conf.load_mode = self.get_arg('load_mode', LOAD_MODES)
        conf.method = self.get_arg('method', METHODS)
        # fields to skip
        conf.skip_fields = [f.strip().lower()
                for f in self.args.get('skip_fields','').split(',')]
        # get fields map (obsolete, for compatibility reasons)
        fields = self.args.get('fields', '*')
        if  fields == "*":
            conf.field_map = None
        else:
            conf.field_map = {}
            for fval in fields.split(','):
                tmp = fval.split(':')
                if len(tmp) == 1:
                    conf.field_map[tmp[0]] = tmp[0]
                else:
                    conf.field_map[tmp[0]] = tmp[1]
        return conf

    def _validate_hash_key(self):
        pass # no need for hash key when not sharding

    def reset(self):
        """Called before starting to process a batch.
        Should clean any pending data."""
        ShardHandler.reset(self)

    def prepare_batch(self, batch_info, dst_curs):
        """Called on first event for this table in current batch."""
        if self.conf.table_mode != 'ignore':
            self.batch_info = batch_info
            self.dst_curs = dst_curs
        ShardHandler.prepare_batch(self, batch_info, dst_curs)

    def filter_data(self, data):
        """Process with fields skip and map"""
        fskip = self.conf.skip_fields
        fmap = self.conf.field_map
        if fskip:
            data = dict((k, v) for k, v in data.items()
                    if k not in fskip)
        if fmap:
            # when field name not present in source is used then  None (NULL)
            # value is inserted. is it ok?
            data = dict( (v, data.get(k)) for k, v in fmap.items())
        return data

    def filter_pkeys(self, pkeys):
        """Process with fields skip and map"""
        fskip = self.conf.skip_fields
        fmap = self.conf.field_map
        if fskip:
            pkeys = [f for f in pkeys if f not in fskip]
        if fmap:
            pkeys = [fmap[p] for p in pkeys if p in fmap]
        return pkeys

    def _process_event(self, ev, sql_queue_func, arg):
        """Process a event.
        Event should be added to sql_queue or executed directly.
        """
        if self.conf.table_mode == 'ignore':
            return
        # get data
        data = skytools.db_urldecode(ev.data)
        if self.encoding_validator:
            data = self.encoding_validator.validate_dict(data, self.table_name)
        if len(ev.ev_type) < 2 or ev.ev_type[1] != ':':
            raise Exception('Unsupported event type: %s/extra1=%s/data=%s' % (
                            ev.ev_type, ev.ev_extra1, ev.ev_data))
        op, pkeys = ev.type.split(':', 1)
        if op not in 'IUD':
            raise Exception('Unknown event type: %s' % ev.ev_type)
        # process only operations specified
        if not op in self.conf.event_types:
            #self.log.debug('dispatch.process_event: ignored event type')
            return
        if self.pkeys is None:
            self.pkeys = self.filter_pkeys(pkeys.split(','))
        data = self.filter_data(data)
        # prepare split table when needed
        if self.conf.table_mode == 'part':
            dst, part_time = self.split_format(ev, data)
            if dst in self.ignored_tables:
                return
            if dst not in self.row_handler.table_map:
                self.check_part(dst, part_time)
                if dst in self.ignored_tables:
                    return
        else:
            dst = self.dest_table

        if dst not in self.row_handler.table_map:
            self.row_handler.add_table(dst, LOADERS[self.conf.load_mode],
                                       self.pkeys, self.conf)
        self.row_handler.process(dst, op, data)

    def finish_batch(self, batch_info, dst_curs):
        """Called when batch finishes."""
        if self.conf.table_mode != 'ignore':
            self.row_handler.flush(dst_curs)
        #ShardHandler.finish_batch(self, batch_info, dst_curs)

    def get_part_name(self):
        # if custom part name template given, use it
        if self.conf.part_name:
            return self.conf.part_name
        parts = ['year', 'month', 'day', 'hour']
        name_parts = ['parent'] + parts[:parts.index(self.conf.period)+1]
        return '_'.join('%%(%s)s' % part for part in name_parts)

    def split_format(self, ev, data):
        """Generates part table name from template"""
        if self.conf.part_mode == 'batch_time':
            dtm = self.batch_info['batch_end']
        elif self.conf.part_mode == 'event_time':
            dtm = ev.ev_time
        elif self.conf.part_mode == 'current_time':
            dtm = datetime.datetime.now()
        elif self.conf.part_mode == 'date_field':
            dt_str = data[self.conf.part_field]
            if dt_str is None:
                raise Exception('part_field(%s) is NULL: %s' % (self.conf.part_field, ev))
            dtm = datetime.datetime.strptime(dt_str[:19], "%Y-%m-%d %H:%M:%S")
        else:
            raise UsageError('Bad value for part_mode: %s' %\
                    self.conf.part_mode)
        vals = {'parent': self.dest_table,
                'year': "%04d" % dtm.year,
                'month': "%02d" % dtm.month,
                'day': "%02d" % dtm.day,
                'hour': "%02d" % dtm.hour,
               }
        return (self.get_part_name() % vals, dtm)

    def check_part(self, dst, part_time):
        """Create part table if not exists.

        It part_template present, execute it
        else if part function present in db, call it
        else clone master table"""
        curs = self.dst_curs
        if skytools.exists_table(curs, dst):
            return
        dst = quote_fqident(dst)
        vals = {'dest': dst,
                'part': dst,
                'parent': self.fq_dest_table,
                'pkeys': ",".join(self.pkeys), # quoting?
                # we do this to make sure that constraints for
                # tables who contain a schema will still work
                'schema_table': dst.replace(".", "__"),
                'part_field': self.conf.part_field,
                'part_time': part_time,
                'period': self.conf.period,
                }
        def exec_with_vals(tmpl):
            if tmpl:
                sql = tmpl % vals
                curs.execute(sql)
                return True
            return False

        exec_with_vals(self.conf.pre_part)

        if not exec_with_vals(self.conf.part_template):
            self.log.debug('part_template not provided, using part func')
            # if part func exists call it with val arguments
            pfargs = ', '.join('%%(%s)s' % arg for arg in PART_FUNC_ARGS)

            # set up configured function
            pfcall = 'select %s(%s)' % (self.conf.part_func, pfargs)
            have_func = skytools.exists_function(curs, self.conf.part_func, len(PART_FUNC_ARGS))

            # backwards compat
            if not have_func and self.conf.part_func == PART_FUNC_NEW:
                pfcall = 'select %s(%s)' % (PART_FUNC_OLD, pfargs)
                have_func = skytools.exists_function(curs, PART_FUNC_OLD, len(PART_FUNC_ARGS))

            if have_func:
                self.log.debug('check_part.exec: func: %s, args: %s', pfcall, vals)
                curs.execute(pfcall, vals)
            else:
                #
                # Otherwise create simple clone.
                #
                # FixMe: differences from create_partitions():
                # - check constraints
                # - inheritance
                #
                self.log.debug('part func %s not found, cloning table', self.conf.part_func)
                struct = TableStruct(curs, self.dest_table)
                struct.create(curs, T_ALL, dst)

        exec_with_vals(self.conf.post_part)
        self.log.info("Created table: %s", dst)

        if self.conf.retention_period:
            dropped = self.drop_obsolete_partitions (self.dest_table, self.conf.retention_period, self.conf.period)
            if self.conf.ignore_old_events and dropped:
                for tbl in dropped:
                    self.ignored_tables.add(tbl)
                    if tbl in self.row_handler.table_map:
                        del self.row_handler.table_map[tbl]

    def drop_obsolete_partitions (self, parent_table, retention_period, partition_period):
        """ Drop obsolete partitions of partition-by-date parent table.
        """
        curs = self.dst_curs
        func = RETENTION_FUNC
        args = [parent_table, retention_period, partition_period]
        sql = "select " + func + " (%s, %s, %s)"
        self.log.debug("func: %s, args: %s", func, args)
        curs.execute(sql, args)
        res = [row[0] for row in curs.fetchall()]
        if res:
            self.log.info("Dropped tables: %s", ", ".join(res))
        return res

    def get_copy_condition(self, src_curs, dst_curs):
        """ Prepare where condition for copy and replay filtering.
        """
        return ShardHandler.get_copy_condition(self, src_curs, dst_curs)

    def real_copy(self, tablename, src_curs, dst_curs, column_list):
        """do actual table copy and return tuple with number of bytes and rows
        copied
        """
        _src_cols = _dst_cols = column_list
        condition = self.get_copy_condition (src_curs, dst_curs)

        if self.conf.skip_fields:
            _src_cols = [col for col in column_list
                         if col not in self.conf.skip_fields]
            _dst_cols = _src_cols

        if self.conf.field_map:
            _src_cols = [col for col in _src_cols if col in self.conf.field_map]
            _dst_cols = [self.conf.field_map[col] for col in _src_cols]

        if self.encoding_validator:
            def _write_hook(obj, data):
                return self.encoding_validator.validate_copy(data, _src_cols, tablename)
        else:
            _write_hook = None

        return skytools.full_copy(tablename, src_curs, dst_curs,
                                  _src_cols, condition,
                                  dst_tablename = self.dest_table,
                                  dst_column_list = _dst_cols,
                                  write_hook = _write_hook)


# add arguments' description to handler's docstring
found = False
for line in __doc__.splitlines():
    if line.startswith ("== HANDLER ARGUMENTS =="):
        found = True
    if found:
        Dispatcher.__doc__ += "\n" + line
del found


#------------------------------------------------------------------------------
# register handler class
#------------------------------------------------------------------------------


__londiste_handlers__ = [Dispatcher]


#------------------------------------------------------------------------------
# helper function for creating dispatchers with different default values
#------------------------------------------------------------------------------

handler_args = partial(handler_args, cls=Dispatcher)

#------------------------------------------------------------------------------
# build set of handlers with different default values for easier use
#------------------------------------------------------------------------------


LOAD = { '': { 'load_mode': 'direct' },
         'bulk': { 'load_mode': 'bulk' }
}
PERIOD = { 'hourly': { 'period': 'hour' },
           'daily' : { 'period': 'day' },
           'monthly': { 'period': 'month' },
           'yearly': { 'period': 'year' },
}
MODE = { 'event': { 'part_mode': 'event_time' },
         'batch': { 'part_mode': 'batch_time' },
         'field': { 'part_mode': 'date_field' },
         'time': { 'part_mode': 'current_time' },
}
BASE = { 'table_mode': 'part',
         'row_mode': 'keep_latest',
}

def set_handler_doc (cls, defs):
    """ generate handler docstring """
    cls.__doc__ = "Custom dispatch handler with default args.\n\n" \
                  "Parameters:\n"
    for k,v in defs.items():
        cls.__doc__ += "  %s = %s\n" % (k,v)

for load, load_dict in LOAD.items():
    for period, period_dict in PERIOD.items():
        for mode, mode_dict in MODE.items():
            # define creator func to keep default dicts in separate context
            def create_handler():
                handler_name = '_'.join(p for p in (load, period, mode) if p)
                default = update(mode_dict, period_dict, load_dict, BASE)
                @handler_args(handler_name)
                def handler_func(args):
                    return update(args, default)
            create_handler()
            hcls = __londiste_handlers__[-1] # it was just added
            defs = update(mode_dict, period_dict, load_dict, BASE)
            set_handler_doc (hcls, defs)
del (hcls, defs)


@handler_args('bulk_direct')
def bulk_direct_handler(args):
    return update(args, {'load_mode': 'bulk', 'table_mode': 'direct'})
set_handler_doc (__londiste_handlers__[-1], {'load_mode': 'bulk', 'table_mode': 'direct'})

@handler_args('direct')
def direct_handler(args):
    return update(args, {'load_mode': 'direct', 'table_mode': 'direct'})
set_handler_doc (__londiste_handlers__[-1], {'load_mode': 'direct', 'table_mode': 'direct'})

########NEW FILE########
__FILENAME__ = multimaster
#!/usr/bin/env python
# encoding: utf-8
"""
Handler for replica with multiple master nodes.

Can only handle initial copy from one master. Add other masters with
expect-sync option.

NB! needs merge_on_time function to be compiled on database first.
"""

import skytools
from londiste.handlers.applyfn import ApplyFuncHandler
from londiste.handlers import update

__all__ = ['MultimasterHandler']

class MultimasterHandler(ApplyFuncHandler):
    __doc__ = __doc__
    handler_name = 'multimaster'

    def __init__(self, table_name, args, dest_table):
        """Init per-batch table data cache."""
        conf = args.copy()
        # remove Multimaster args from conf
        for name in ['func_name','func_conf']:
            if name in conf:
                conf.pop(name)
        conf = skytools.db_urlencode(conf)
        args = update(args, {'func_name': 'merge_on_time', 'func_conf': conf})
        ApplyFuncHandler.__init__(self, table_name, args, dest_table)

    def _check_args (self, args):
        pass # any arg can be passed

    def add(self, trigger_arg_list):
        """Create SKIP and BEFORE INSERT trigger"""
        trigger_arg_list.append('no_merge')


#------------------------------------------------------------------------------
# register handler class
#------------------------------------------------------------------------------

__londiste_handlers__ = [MultimasterHandler]

########NEW FILE########
__FILENAME__ = qtable
"""

Handlers:

qtable     - dummy handler to setup queue tables. All events are ignored. Use in
             root node.
fake_local - dummy handler to setup queue tables. All events are ignored. Table
             structure is not required. Use in branch/leaf.
qsplitter  - dummy handler to setup queue tables. All events are ignored. Table
             structure is not required. All table events are inserted to
             destination queue, specified with handler arg 'queue'.

"""

from londiste.handler import BaseHandler

import pgq

__all__ = ['QueueTableHandler', 'QueueSplitterHandler']


class QueueTableHandler(BaseHandler):
    """Queue table handler. Do nothing.

    Trigger: before-insert, skip trigger.
    Event-processing: do nothing.
    """
    handler_name = 'qtable'

    def add(self, trigger_arg_list):
        """Create SKIP and BEFORE INSERT trigger"""
        trigger_arg_list.append('tgflags=BI')
        trigger_arg_list.append('SKIP')
        trigger_arg_list.append('expect_sync')

    def real_copy(self, tablename, src_curs, dst_curs, column_list):
        """Force copy not to start"""
        return (0,0)

    def needs_table(self):
        return False

class QueueSplitterHandler(BaseHandler):
    """Send events for one table to another queue.

    Parameters:
      queue=QUEUE - Queue name.
    """
    handler_name = 'qsplitter'

    def __init__(self, table_name, args, dest_table):
        """Init per-batch table data cache."""
        BaseHandler.__init__(self, table_name, args, dest_table)
        try:
            self.dst_queue_name = args['queue']
        except KeyError:
            raise Exception('specify queue with handler-arg')
        self.rows = []

    def add(self, trigger_arg_list):
        trigger_arg_list.append('virtual_table')

    def prepare_batch(self, batch_info, dst_curs):
        """Called on first event for this table in current batch."""
        self.rows = []

    def process_event(self, ev, sql_queue_func, arg):
        """Process a event.

        Event should be added to sql_queue or executed directly.
        """
        if self.dst_queue_name is None: return

        data = [ev.type, ev.data,
                ev.extra1, ev.extra2, ev.extra3, ev.extra4, ev.time]
        self.rows.append(data)

    def finish_batch(self, batch_info, dst_curs):
        """Called when batch finishes."""
        if self.dst_queue_name is None: return

        fields = ['type', 'data',
                  'extra1', 'extra2', 'extra3', 'extra4', 'time']
        pgq.bulk_insert_events(dst_curs, self.rows, fields, self.dst_queue_name)

    def needs_table(self):
        return False


__londiste_handlers__ = [QueueTableHandler, QueueSplitterHandler]

########NEW FILE########
__FILENAME__ = shard
"""Event filtering by hash, for partitioned databases.

Parameters:
  key=COLUMN: column name to use for hashing
  hash_key=COLUMN: column name to use for hashing (overrides 'key' parameter)
  hashfunc=NAME: function to use for hashing (default: partconf.get_hash_raw)
  hashexpr=EXPR: full expression to use for hashing (deprecated)
  encoding=ENC: validate and fix incoming data (only utf8 supported atm)
  ignore_truncate=BOOL: ignore truncate event, default: 0, values: 0,1

On root node:
* Hash of key field will be added to ev_extra3.
  This is implemented by adding additional trigger argument:
        ev_extra3='hash='||partconf.get_hash_raw(key_column)

On branch/leaf node:
* On COPY time, the SELECT on provider side gets filtered by hash.
* On replay time, the events gets filtered by looking at hash in ev_extra3.

Local config:
* Local hash value and mask are loaded from partconf.conf table.

"""

import skytools
from londiste.handler import TableHandler

__all__ = ['ShardHandler', 'PartHandler']

class ShardHandler (TableHandler):
    __doc__ = __doc__
    handler_name = 'shard'

    DEFAULT_HASHFUNC = "partconf.get_hash_raw"
    DEFAULT_HASHEXPR = "%s(%s)"

    def __init__(self, table_name, args, dest_table):
        TableHandler.__init__(self, table_name, args, dest_table)
        self.hash_mask = None   # aka max part number (atm)
        self.shard_nr = None    # part number of local node

        # primary key columns
        self.hash_key = args.get('hash_key', args.get('key'))
        self._validate_hash_key()

        # hash function & full expression
        hashfunc = args.get('hashfunc', self.DEFAULT_HASHFUNC)
        self.hashexpr = self.DEFAULT_HASHEXPR % (
                skytools.quote_fqident(hashfunc),
                skytools.quote_ident(self.hash_key or ''))
        self.hashexpr = args.get('hashexpr', self.hashexpr)

    def _validate_hash_key(self):
        if self.hash_key is None:
            raise Exception('Specify hash key field as hash_key argument')

    def reset(self):
        """Forget config info."""
        self.hash_mask = None
        self.shard_nr = None
        TableHandler.reset(self)

    def add(self, trigger_arg_list):
        """Let trigger put hash into extra3"""
        arg = "ev_extra3='hash='||%s" % self.hashexpr
        trigger_arg_list.append(arg)
        TableHandler.add(self, trigger_arg_list)

    def prepare_batch(self, batch_info, dst_curs):
        """Called on first event for this table in current batch."""
        if self.hash_key is not None:
            if not self.hash_mask:
                self.load_shard_info(dst_curs)
        TableHandler.prepare_batch(self, batch_info, dst_curs)

    def process_event(self, ev, sql_queue_func, arg):
        """Filter event by hash in extra3, apply only if for local shard."""
        if ev.extra3 and self.hash_key is not None:
            meta = skytools.db_urldecode(ev.extra3)
            self.log.debug('shard.process_event: hash=%i, hash_mask=%i, shard_nr=%i',
                           int(meta['hash']), self.hash_mask, self.shard_nr)
            if (int(meta['hash']) & self.hash_mask) != self.shard_nr:
                self.log.debug('shard.process_event: not my event')
                return
        self._process_event(ev, sql_queue_func, arg)

    def _process_event(self, ev, sql_queue_func, arg):
        self.log.debug('shard.process_event: my event, processing')
        TableHandler.process_event(self, ev, sql_queue_func, arg)

    def get_copy_condition(self, src_curs, dst_curs):
        """Prepare the where condition for copy and replay filtering"""
        if self.hash_key is None:
            return TableHandler.get_copy_condition(self, src_curs, dst_curs)
        self.load_shard_info(dst_curs)
        w = "(%s & %d) = %d" % (self.hashexpr, self.hash_mask, self.shard_nr)
        self.log.debug('shard: copy_condition=%r', w)
        return w

    def load_shard_info(self, curs):
        """Load part/slot info from database."""
        q = "select part_nr, max_part from partconf.conf"
        curs.execute(q)
        self.shard_nr, self.hash_mask = curs.fetchone()
        if self.shard_nr is None or self.hash_mask is None:
            raise Exception('Error loading shard info')

class PartHandler (ShardHandler):
    __doc__ = "Deprecated compat name for shard handler.\n" + __doc__.split('\n',1)[1]
    handler_name = 'part'

# register handler class
__londiste_handlers__ = [ShardHandler, PartHandler]

########NEW FILE########
__FILENAME__ = vtable
"""Virtual Table handler.

Hack to get local=t for a table, but without processing any events.
"""

from londiste.handler import BaseHandler

__all__ = ['VirtualTableHandler', 'FakeLocalHandler']

class VirtualTableHandler(BaseHandler):
    __doc__ = __doc__
    handler_name = 'vtable'

    def add(self, trigger_arg_list):
        trigger_arg_list.append('virtual_table')

    def needs_table(self):
        return False

class FakeLocalHandler(VirtualTableHandler):
    """Deprecated compat name for vtable."""
    handler_name = 'fake_local'

__londiste_handlers__ = [VirtualTableHandler, FakeLocalHandler]

########NEW FILE########
__FILENAME__ = playback
#! /usr/bin/env python

"""Basic replication core."""

import sys, os, time
import skytools

from pgq.cascade.worker import CascadedWorker

from londiste.handler import *
from londiste.exec_attrs import ExecAttrs

__all__ = ['Replicator', 'TableState',
    'TABLE_MISSING', 'TABLE_IN_COPY', 'TABLE_CATCHING_UP',
    'TABLE_WANNA_SYNC', 'TABLE_DO_SYNC', 'TABLE_OK']

# state                 # owner - who is allowed to change
TABLE_MISSING      = 0  # main
TABLE_IN_COPY      = 1  # copy
TABLE_CATCHING_UP  = 2  # copy
TABLE_WANNA_SYNC   = 3  # main
TABLE_DO_SYNC      = 4  # copy
TABLE_OK           = 5  # setup

SYNC_OK   = 0  # continue with batch
SYNC_LOOP = 1  # sleep, try again
SYNC_EXIT = 2  # nothing to do, exit script

MAX_PARALLEL_COPY = 8 # default number of allowed max parallel copy processes

class Counter(object):
    """Counts table statuses."""

    missing = 0
    copy = 0
    catching_up = 0
    wanna_sync = 0
    do_sync = 0
    ok = 0

    def __init__(self, tables):
        """Counts and sanity checks."""
        for t in tables:
            if t.state == TABLE_MISSING:
                self.missing += 1
            elif t.state == TABLE_IN_COPY:
                self.copy += 1
            elif t.state == TABLE_CATCHING_UP:
                self.catching_up += 1
            elif t.state == TABLE_WANNA_SYNC:
                self.wanna_sync += 1
            elif t.state == TABLE_DO_SYNC:
                self.do_sync += 1
            elif t.state == TABLE_OK:
                self.ok += 1

    def get_copy_count(self):
        return self.copy + self.catching_up + self.wanna_sync + self.do_sync

class TableState(object):
    """Keeps state about one table."""
    def __init__(self, name, log):
        """Init TableState for one table."""
        self.name = name
        self.dest_table = name
        self.log = log
        # same as forget:
        self.state = TABLE_MISSING
        self.last_snapshot_tick = None
        self.str_snapshot = None
        self.from_snapshot = None
        self.sync_tick_id = None
        self.ok_batch_count = 0
        self.last_tick = 0
        self.table_attrs = {}
        self.copy_role = None
        self.dropped_ddl = None
        self.plugin = None
        # except this
        self.changed = 0
        # position in parallel copy work order
        self.copy_pos = 0
        # max number of parallel copy processes allowed
        self.max_parallel_copy = MAX_PARALLEL_COPY

    def forget(self):
        """Reset all info."""
        self.state = TABLE_MISSING
        self.last_snapshot_tick = None
        self.str_snapshot = None
        self.from_snapshot = None
        self.sync_tick_id = None
        self.ok_batch_count = 0
        self.last_tick = 0
        self.table_attrs = {}
        self.changed = 1
        self.plugin = None
        self.copy_pos = 0
        self.max_parallel_copy = MAX_PARALLEL_COPY

    def change_snapshot(self, str_snapshot, tag_changed = 1):
        """Set snapshot."""
        if self.str_snapshot == str_snapshot:
            return
        self.log.debug("%s: change_snapshot to %s", self.name, str_snapshot)
        self.str_snapshot = str_snapshot
        if str_snapshot:
            self.from_snapshot = skytools.Snapshot(str_snapshot)
        else:
            self.from_snapshot = None

        if tag_changed:
            self.ok_batch_count = 0
            self.last_tick = None
            self.changed = 1

    def change_state(self, state, tick_id = None):
        """Set state."""
        if self.state == state and self.sync_tick_id == tick_id:
            return
        self.state = state
        self.sync_tick_id = tick_id
        self.changed = 1
        self.log.debug("%s: change_state to %s", self.name, self.render_state())

    def render_state(self):
        """Make a string to be stored in db."""

        if self.state == TABLE_MISSING:
            return None
        elif self.state == TABLE_IN_COPY:
            return 'in-copy'
        elif self.state == TABLE_CATCHING_UP:
            return 'catching-up'
        elif self.state == TABLE_WANNA_SYNC:
            return 'wanna-sync:%d' % self.sync_tick_id
        elif self.state == TABLE_DO_SYNC:
            return 'do-sync:%d' % self.sync_tick_id
        elif self.state == TABLE_OK:
            return 'ok'

    def parse_state(self, merge_state):
        """Read state from string."""

        state = -1
        if merge_state == None:
            state = TABLE_MISSING
        elif merge_state == "in-copy":
            state = TABLE_IN_COPY
        elif merge_state == "catching-up":
            state = TABLE_CATCHING_UP
        elif merge_state == "ok":
            state = TABLE_OK
        elif merge_state == "?":
            state = TABLE_OK
        else:
            tmp = merge_state.split(':')
            if len(tmp) == 2:
                self.sync_tick_id = int(tmp[1])
                if tmp[0] == 'wanna-sync':
                    state = TABLE_WANNA_SYNC
                elif tmp[0] == 'do-sync':
                    state = TABLE_DO_SYNC

        if state < 0:
            raise Exception("Bad table state: %s" % merge_state)

        return state

    def loaded_state(self, row):
        """Update object with info from db."""

        self.log.debug("loaded_state: %s: %s / %s",
                       self.name, row['merge_state'], row['custom_snapshot'])
        self.change_snapshot(row['custom_snapshot'], 0)
        self.state = self.parse_state(row['merge_state'])
        self.changed = 0
        if row['table_attrs']:
            self.table_attrs = skytools.db_urldecode(row['table_attrs'])
        else:
            self.table_attrs = {}
        self.copy_role = row['copy_role']
        self.dropped_ddl = row['dropped_ddl']
        if row['merge_state'] == "?":
            self.changed = 1

        self.copy_pos = int(row.get('copy_pos','0'))
        self.max_parallel_copy = int(self.table_attrs.get('max_parallel_copy',
                                                        self.max_parallel_copy))

        if 'dest_table' in row and row['dest_table']:
            self.dest_table = row['dest_table']
        else:
            self.dest_table = self.name

        hstr = self.table_attrs.get('handlers', '') # compat
        hstr = self.table_attrs.get('handler', hstr)
        self.plugin = build_handler(self.name, hstr, self.dest_table)

    def max_parallel_copies_reached(self):
        return self.max_parallel_copy and\
                    self.copy_pos >= self.max_parallel_copy

    def interesting(self, ev, tick_id, copy_thread, copy_table_name):
        """Check if table wants this event."""

        if copy_thread:
            if self.name != copy_table_name:
                return False
            if self.state not in (TABLE_CATCHING_UP, TABLE_DO_SYNC):
                return False
        else:
            if self.state != TABLE_OK:
                return False

        # if no snapshot tracking, then accept always
        if not self.from_snapshot:
            return True

        # uninteresting?
        if self.from_snapshot.contains(ev.txid):
            return False

        # after couple interesting batches there no need to check snapshot
        # as there can be only one partially interesting batch
        if tick_id != self.last_tick:
            self.last_tick = tick_id
            self.ok_batch_count += 1

            # disable batch tracking
            if self.ok_batch_count > 3:
                self.change_snapshot(None)
        return True

    def gc_snapshot(self, copy_thread, prev_tick, cur_tick, no_lag):
        """Remove attached snapshot if possible.

        If the event processing is in current moment, the snapshot
        is not needed beyond next batch.

        The logic is needed for mostly unchanging tables,
        where the .ok_batch_count check in .interesting()
        method can take a lot of time.
        """

        # check if gc is needed
        if self.str_snapshot is None:
            return

        # check if allowed to modify
        if copy_thread:
            if self.state != TABLE_CATCHING_UP:
                return
        else:
            if self.state != TABLE_OK:
                return False

        # aquire last tick
        if not self.last_snapshot_tick:
            if no_lag:
                self.last_snapshot_tick = cur_tick
            return

        # reset snapshot if not needed anymore
        if self.last_snapshot_tick < prev_tick:
            self.change_snapshot(None)

    def get_plugin(self):
        return self.plugin

class Replicator(CascadedWorker):
    """Replication core.

    Config options::

        ## Parameters for Londiste ##

        # target database
        db = dbname=somedb host=127.0.0.1

        # extra connect string parameters to add to node public connect strings.
        # useful values: user= sslmode=
        #remote_extra_connstr =

        # how many tables can be copied in parallel
        #parallel_copies = 1

        # accept only events for locally present tables
        #local_only = true

        ## compare/repair
        # max amount of time table can be locked
        #lock_timeout = 10
        # compare: sql to use
        #compare_sql = select count(1) as cnt, sum(hashtext(t.*::text)) as chksum from only _TABLE_ t
        # workaround for hashtext change between 8.3 and 8.4
        #compare_sql = select count(1) as cnt, sum(('x'||substr(md5(t.*::text),1,16))::bit(64)::bigint) as chksum from only _TABLE_ t
        #compare_fmt = %(cnt)d rows, checksum=%(chksum)s

        ## Parameters for initial node creation: create-root/branch/leaf ##

        # These parameters can be given on either command-line or in config
        # command-line values override config values.  Those values are
        # used only during create time, otherwise they are loaded from database.

        # Name for local node.
        #node_name =

        # public connect string for local node, which other nodes will use
        # to connect to this one.
        #public_node_location =

        # connect string for existing node to use as provider
        #initial_provider_location =
    """

    # batch info
    cur_tick = 0
    prev_tick = 0
    copy_table_name = None # filled by Copytable()
    sql_list = []

    current_event = None

    def __init__(self, args):
        """Replication init."""
        CascadedWorker.__init__(self, 'londiste3', 'db', args)

        self.table_list = []
        self.table_map = {}

        self.copy_thread = 0
        self.set_name = self.queue_name
        self.used_plugins = {}

        self.parallel_copies = self.cf.getint('parallel_copies', 1)
        if self.parallel_copies < 1:
            raise Exception('Bad value for parallel_copies: %d' % self.parallel_copies)

        self.consumer_filter = None

        load_handler_modules(self.cf)

    def connection_hook(self, dbname, db):
        if dbname == 'db' and db.server_version >= 80300:
            curs = db.cursor()
            curs.execute("set session_replication_role = 'replica'")
            db.commit()

    code_check_done = 0
    def check_code(self, db):
        objs = [
            skytools.DBFunction("pgq.maint_operations", 0,
                sql_file = "londiste.maint-upgrade.sql"),
        ]
        skytools.db_install(db.cursor(), objs, self.log)
        db.commit()

    def process_remote_batch(self, src_db, tick_id, ev_list, dst_db):
        "All work for a batch.  Entry point from SetConsumer."

        self.current_event = None

        # this part can play freely with transactions

        if not self.code_check_done:
            self.check_code(dst_db)
            self.code_check_done = 1

        self.sync_database_encodings(src_db, dst_db)

        self.cur_tick = self.batch_info['tick_id']
        self.prev_tick = self.batch_info['prev_tick_id']

        dst_curs = dst_db.cursor()
        self.load_table_state(dst_curs)
        self.sync_tables(src_db, dst_db)

        self.copy_snapshot_cleanup(dst_db)

        # only main thread is allowed to restore fkeys
        if not self.copy_thread:
            self.restore_fkeys(dst_db)

        for p in self.used_plugins.values():
            p.reset()
        self.used_plugins = {}

        # now the actual event processing happens.
        # they must be done all in one tx in dst side
        # and the transaction must be kept open so that
        # the cascade-consumer can save last tick and commit.

        self.sql_list = []
        CascadedWorker.process_remote_batch(self, src_db, tick_id, ev_list, dst_db)
        self.flush_sql(dst_curs)

        for p in self.used_plugins.values():
            p.finish_batch(self.batch_info, dst_curs)
        self.used_plugins = {}

        # finalize table changes
        self.save_table_state(dst_curs)

        # store event filter
        if self.cf.getboolean('local_only', False):
            # create list of tables
            if self.copy_thread:
                _filterlist = skytools.quote_literal(self.copy_table_name)
            else:
                _filterlist = ','.join(map(skytools.quote_literal, self.table_map.keys()))

            # build filter
            meta = "(ev_type like 'pgq.%' or ev_type like 'londiste.%')"
            if _filterlist:
                self.consumer_filter = "(%s or (ev_extra1 in (%s)))" % (meta, _filterlist)
            else:
                self.consumer_filter = meta
        else:
            # no filter
            self.consumer_filter = None

    def sync_tables(self, src_db, dst_db):
        """Table sync loop.

        Calls appropriate handles, which is expected to
        return one of SYNC_* constants."""

        self.log.debug('Sync tables')
        while 1:
            cnt = Counter(self.table_list)
            if self.copy_thread:
                res = self.sync_from_copy_thread(cnt, src_db, dst_db)
            else:
                res = self.sync_from_main_thread(cnt, src_db, dst_db)

            if res == SYNC_EXIT:
                self.log.debug('Sync tables: exit')
                if self.copy_thread:
                    self.unregister_consumer()
                src_db.commit()
                sys.exit(0)
            elif res == SYNC_OK:
                return
            elif res != SYNC_LOOP:
                raise Exception('Program error')

            self.log.debug('Sync tables: sleeping')
            time.sleep(3)
            dst_db.commit()
            self.load_table_state(dst_db.cursor())
            dst_db.commit()

    dsync_backup = None
    def sync_from_main_thread(self, cnt, src_db, dst_db):
        "Main thread sync logic."

        # This operates on all table, any amount can be in any state

        ret = SYNC_OK

        if cnt.do_sync:
            # wait for copy thread to catch up
            ret = SYNC_LOOP

        # we need to do wanna-sync->do_sync with small batches
        need_dsync = False
        dsync_ok = True
        if self.pgq_min_interval or self.pgq_min_count:
            dsync_ok = False
        elif self.dsync_backup and self.dsync_backup[0] >= self.cur_tick:
            dsync_ok = False

        # now check if do-sync is needed
        for t in self.get_tables_in_state(TABLE_WANNA_SYNC):
            # copy thread wants sync, if not behind, do it
            if self.cur_tick >= t.sync_tick_id:
                if dsync_ok:
                    self.change_table_state(dst_db, t, TABLE_DO_SYNC, self.cur_tick)
                    ret = SYNC_LOOP
                else:
                    need_dsync = True

        # tune batch size if needed
        if need_dsync:
            if self.pgq_min_count or self.pgq_min_interval:
                bak = (self.cur_tick, self.pgq_min_count, self.pgq_min_interval)
                self.dsync_backup = bak
                self.pgq_min_count = None
                self.pgq_min_interval = None
        elif self.dsync_backup:
            self.pgq_min_count = self.dsync_backup[1]
            self.pgq_min_interval = self.dsync_backup[2]
            self.dsync_backup = None

        # now handle new copies
        npossible = self.parallel_copies - cnt.get_copy_count()
        if cnt.missing and npossible > 0:
            pmap = self.get_state_map(src_db.cursor())
            src_db.commit()
            for t in self.get_tables_in_state(TABLE_MISSING):
                if 'copy_node' in t.table_attrs:
                    # should we go and check this node?
                    pass
                else:
                    # regular provider is used
                    if t.name not in pmap:
                        self.log.warning("Table %s not available on provider", t.name)
                        continue
                    pt = pmap[t.name]
                    if pt.state != TABLE_OK: # or pt.custom_snapshot: # FIXME: does snapsnot matter?
                        self.log.info("Table %s not OK on provider, waiting", t.name)
                        continue

                # don't allow more copies than configured
                if npossible == 0:
                    break
                npossible -= 1

                # drop all foreign keys to and from this table
                self.drop_fkeys(dst_db, t.dest_table)

                # change state after fkeys are dropped thus allowing
                # failure inbetween
                self.change_table_state(dst_db, t, TABLE_IN_COPY)

                # the copy _may_ happen immediately
                self.launch_copy(t)

                # there cannot be interesting events in current batch
                # but maybe there's several tables, lets do them in one go
                ret = SYNC_LOOP

        return ret

    def sync_from_copy_thread(self, cnt, src_db, dst_db):
        "Copy thread sync logic."

        # somebody may have done remove-table in the meantime
        if self.copy_table_name not in self.table_map:
            self.log.error("copy_sync: lost table: %s", self.copy_table_name)
            return SYNC_EXIT

        # This operates on single table
        t = self.table_map[self.copy_table_name]

        if t.state == TABLE_DO_SYNC:
            # these settings may cause copy to miss right tick
            self.pgq_min_count = None
            self.pgq_min_interval = None

            # main thread is waiting, catch up, then handle over
            if self.cur_tick == t.sync_tick_id:
                self.change_table_state(dst_db, t, TABLE_OK)
                return SYNC_EXIT
            elif self.cur_tick < t.sync_tick_id:
                return SYNC_OK
            else:
                self.log.error("copy_sync: cur_tick=%d sync_tick=%d",
                                self.cur_tick, t.sync_tick_id)
                raise Exception('Invalid table state')
        elif t.state == TABLE_WANNA_SYNC:
            # wait for main thread to react
            return SYNC_LOOP
        elif t.state == TABLE_CATCHING_UP:

            # partition merging
            if t.copy_role in ('wait-replay', 'lead'):
                return SYNC_LOOP

            # copy just finished
            if t.dropped_ddl:
                self.restore_copy_ddl(t, dst_db)
                return SYNC_OK

            # is there more work?
            if self.work_state:
                return SYNC_OK

            # seems we have catched up
            self.change_table_state(dst_db, t, TABLE_WANNA_SYNC, self.cur_tick)
            return SYNC_LOOP
        elif t.state == TABLE_IN_COPY:
            # table is not copied yet, do it
            self.do_copy(t, src_db, dst_db)

            # forget previous value
            self.work_state = 1

            return SYNC_LOOP
        else:
            # nothing to do
            return SYNC_EXIT

    def restore_copy_ddl(self, ts, dst_db):
        self.log.info("%s: restoring DDL", ts.name)
        dst_curs = dst_db.cursor()
        for ddl in skytools.parse_statements(ts.dropped_ddl):
            self.log.info(ddl)
            dst_curs.execute(ddl)
        q = "select * from londiste.local_set_table_struct(%s, %s, NULL)"
        self.exec_cmd(dst_curs, q, [self.queue_name, ts.name])
        ts.dropped_ddl = None
        dst_db.commit()

        # analyze
        self.log.info("%s: analyze", ts.name)
        dst_curs.execute("analyze " + skytools.quote_fqident(ts.name))
        dst_db.commit()


    def do_copy(self, tbl, src_db, dst_db):
        """Callback for actual copy implementation."""
        raise Exception('do_copy not implemented')

    def process_remote_event(self, src_curs, dst_curs, ev):
        """handle one event"""

        self.log.debug("New event: id=%s / type=%s / data=%s / extra1=%s", ev.id, ev.type, ev.data, ev.extra1)

        # set current_event only if processing them one-by-one
        if self.work_state < 0:
            self.current_event = ev

        if ev.type in ('I', 'U', 'D'):
            self.handle_data_event(ev, dst_curs)
        elif ev.type[:2] in ('I:', 'U:', 'D:'):
            self.handle_data_event(ev, dst_curs)
        elif ev.type == "R":
            self.flush_sql(dst_curs)
            self.handle_truncate_event(ev, dst_curs)
        elif ev.type == 'EXECUTE':
            self.flush_sql(dst_curs)
            self.handle_execute_event(ev, dst_curs)
        elif ev.type == 'londiste.add-table':
            self.flush_sql(dst_curs)
            self.add_set_table(dst_curs, ev.data)
        elif ev.type == 'londiste.remove-table':
            self.flush_sql(dst_curs)
            self.remove_set_table(dst_curs, ev.data)
        elif ev.type == 'londiste.remove-seq':
            self.flush_sql(dst_curs)
            self.remove_set_seq(dst_curs, ev.data)
        elif ev.type == 'londiste.update-seq':
            self.flush_sql(dst_curs)
            self.update_seq(dst_curs, ev)
        else:
            CascadedWorker.process_remote_event(self, src_curs, dst_curs, ev)

        # no point keeping it around longer
        self.current_event = None

    def handle_data_event(self, ev, dst_curs):
        """handle one data event"""
        t = self.get_table_by_name(ev.extra1)
        if not t or not t.interesting(ev, self.cur_tick, self.copy_thread, self.copy_table_name):
            self.stat_increase('ignored_events')
            return

        try:
            p = self.used_plugins[ev.extra1]
        except KeyError:
            p = t.get_plugin()
            self.used_plugins[ev.extra1] = p
            p.prepare_batch(self.batch_info, dst_curs)

        p.process_event(ev, self.apply_sql, dst_curs)

    def handle_truncate_event(self, ev, dst_curs):
        """handle one truncate event"""
        t = self.get_table_by_name(ev.extra1)
        if not t or not t.interesting(ev, self.cur_tick, self.copy_thread, self.copy_table_name):
            self.stat_increase('ignored_events')
            return

        fqname = skytools.quote_fqident(t.dest_table)

        try:
            p = self.used_plugins[ev.extra1]
        except KeyError:
            p = t.get_plugin()
            self.used_plugins[ev.extra1] = p

        if p.conf.get('ignore_truncate'):
            self.log.info("ignoring truncate for %s", fqname)
            return

        #
        # Always use CASCADE, because without it the
        # operation cannot work with FKeys, on both
        # slave and master.
        #
        sql = "TRUNCATE %s CASCADE;" % fqname

        self.flush_sql(dst_curs)
        dst_curs.execute(sql)

    def handle_execute_event(self, ev, dst_curs):
        """handle one EXECUTE event"""

        if self.copy_thread:
            return

        # parse event
        fname = ev.extra1
        s_attrs = ev.extra2
        exec_attrs = ExecAttrs(urlenc = s_attrs)
        sql = ev.data

        # fixme: curs?
        pgver = dst_curs.connection.server_version
        if pgver >= 80300:
            dst_curs.execute("set local session_replication_role = 'local'")

        seq_map = {}
        q = "select seq_name, local from londiste.get_seq_list(%s) where local"
        dst_curs.execute(q, [self.queue_name])
        for row in dst_curs.fetchall():
            seq_map[row['seq_name']] = row['seq_name']

        tbl_map = {}
        for tbl, t in self.table_map.items():
            tbl_map[t.name] = t.dest_table

        q = "select * from londiste.execute_start(%s, %s, %s, false, %s)"
        res = self.exec_cmd(dst_curs, q, [self.queue_name, fname, sql, s_attrs], commit = False)
        ret = res[0]['ret_code']
        if ret > 200:
            self.log.info("Skipping execution of '%s'", fname)
            if pgver >= 80300:
                dst_curs.execute("set local session_replication_role = 'replica'")
            return

        if exec_attrs.need_execute(dst_curs, tbl_map, seq_map):
            self.log.info("%s: executing sql")
            xsql = exec_attrs.process_sql(sql, tbl_map, seq_map)
            for stmt in skytools.parse_statements(xsql):
                dst_curs.execute(stmt)
        else:
            self.log.info("%s: execution not needed on this node")

        q = "select * from londiste.execute_finish(%s, %s)"
        self.exec_cmd(dst_curs, q, [self.queue_name, fname], commit = False)
        if pgver >= 80300:
            dst_curs.execute("set local session_replication_role = 'replica'")

    def apply_sql(self, sql, dst_curs):

        # how many queries to batch together, drop batching on error
        limit = 200
        if self.work_state == -1:
            limit = 0

        self.sql_list.append(sql)
        if len(self.sql_list) >= limit:
            self.flush_sql(dst_curs)

    def flush_sql(self, dst_curs):
        """Send all buffered statements to DB."""

        if len(self.sql_list) == 0:
            return

        buf = "\n".join(self.sql_list)
        self.sql_list = []

        dst_curs.execute(buf)

    def add_set_table(self, dst_curs, tbl):
        """There was new table added to root, remember it."""

        q = "select londiste.global_add_table(%s, %s)"
        dst_curs.execute(q, [self.set_name, tbl])

    def remove_set_table(self, dst_curs, tbl):
        """There was table dropped from root, remember it."""
        if tbl in self.table_map:
            t = self.table_map[tbl]
            del self.table_map[tbl]
            self.table_list.remove(t)
        q = "select londiste.global_remove_table(%s, %s)"
        dst_curs.execute(q, [self.set_name, tbl])

    def remove_set_seq(self, dst_curs, seq):
        """There was seq dropped from root, remember it."""

        q = "select londiste.global_remove_seq(%s, %s)"
        dst_curs.execute(q, [self.set_name, seq])

    def load_table_state(self, curs):
        """Load table state from database.

        Todo: if all tables are OK, there is no need
        to load state on every batch.
        """

        q = "select * from londiste.get_table_list(%s)"
        curs.execute(q, [self.set_name])

        new_list = []
        new_map = {}
        for row in curs.fetchall():
            if not row['local']:
                continue
            t = self.get_table_by_name(row['table_name'])
            if not t:
                t = TableState(row['table_name'], self.log)
            t.loaded_state(row)
            new_list.append(t)
            new_map[t.name] = t

        self.table_list = new_list
        self.table_map = new_map

    def get_state_map(self, curs):
        """Get dict of table states."""

        q = "select * from londiste.get_table_list(%s)"
        curs.execute(q, [self.set_name])

        new_map = {}
        for row in curs.fetchall():
            if not row['local']:
                continue
            t = TableState(row['table_name'], self.log)
            t.loaded_state(row)
            new_map[t.name] = t
        return new_map

    def save_table_state(self, curs):
        """Store changed table state in database."""

        for t in self.table_list:
            # backwards compat: move plugin-only dest_table to table_info
            if t.dest_table != t.plugin.dest_table:
                self.log.info("Overwriting .dest_table from plugin: tbl=%s  dst=%s",
                              t.name, t.plugin.dest_table)
                q = "update londiste.table_info set dest_table = %s"\
                    " where queue_name = %s and table_name = %s"
                curs.execute(q, [t.plugin.dest_table, self.set_name, t.name])

            if not t.changed:
                continue
            merge_state = t.render_state()
            self.log.info("storing state of %s: copy:%d new_state:%s",
                            t.name, self.copy_thread, merge_state)
            q = "select londiste.local_set_table_state(%s, %s, %s, %s)"
            curs.execute(q, [self.set_name,
                             t.name, t.str_snapshot, merge_state])
            t.changed = 0

    def change_table_state(self, dst_db, tbl, state, tick_id = None):
        """Chage state for table."""

        tbl.change_state(state, tick_id)
        self.save_table_state(dst_db.cursor())
        dst_db.commit()

        self.log.info("Table %s status changed to '%s'",
                      tbl.name, tbl.render_state())

    def get_tables_in_state(self, state):
        "get all tables with specific state"

        for t in self.table_list:
            if t.state == state:
                yield t

    def get_table_by_name(self, name):
        """Returns cached state object."""
        if name.find('.') < 0:
            name = "public.%s" % name
        if name in self.table_map:
            return self.table_map[name]
        return None

    def launch_copy(self, tbl_stat):
        """Run parallel worker for copy."""
        self.log.info("Launching copy process")
        script = sys.argv[0]
        conf = self.cf.filename
        cmd = [script, conf, 'copy', tbl_stat.name, '-d']

        # pass same verbosity options as main script got
        if self.options.quiet:
            cmd.append('-q')
        if self.options.verbose:
            cmd += ['-v'] * self.options.verbose

        # let existing copy finish and clean its pidfile,
        # otherwise new copy will exit immediately.
        # FIXME: should not happen on per-table pidfile ???
        copy_pidfile = "%s.copy.%s" % (self.pidfile, tbl_stat.name)
        while skytools.signal_pidfile(copy_pidfile, 0):
            self.log.warning("Waiting for existing copy to exit")
            time.sleep(2)

        # launch and wait for daemonization result
        self.log.debug("Launch args: %r", cmd)
        res = os.spawnvp(os.P_WAIT, script, cmd)
        self.log.debug("Launch result: %r", res)
        if res != 0:
            self.log.error("Failed to launch copy process, result=%d", res)

    def sync_database_encodings(self, src_db, dst_db):
        """Make sure client_encoding is same on both side."""

        try:
            # psycopg2
            if src_db.encoding != dst_db.encoding:
                dst_db.set_client_encoding(src_db.encoding)
        except AttributeError:
            # psycopg1
            src_curs = src_db.cursor()
            dst_curs = dst_db.cursor()
            src_curs.execute("show client_encoding")
            src_enc = src_curs.fetchone()[0]
            dst_curs.execute("show client_encoding")
            dst_enc = dst_curs.fetchone()[0]
            if src_enc != dst_enc:
                dst_curs.execute("set client_encoding = %s", [src_enc])

    def copy_snapshot_cleanup(self, dst_db):
        """Remove unnecessary snapshot info from tables."""
        no_lag = not self.work_state
        changes = False
        for t in self.table_list:
            t.gc_snapshot(self.copy_thread, self.prev_tick, self.cur_tick, no_lag)
            if t.changed:
                changes = True

        if changes:
            self.save_table_state(dst_db.cursor())
            dst_db.commit()

    def restore_fkeys(self, dst_db):
        """Restore fkeys that have both tables on sync."""
        dst_curs = dst_db.cursor()
        # restore fkeys -- one at a time
        q = "select * from londiste.get_valid_pending_fkeys(%s)"
        dst_curs.execute(q, [self.set_name])
        fkey_list = dst_curs.fetchall()
        for row in fkey_list:
            self.log.info('Creating fkey: %(fkey_name)s (%(from_table)s --> %(to_table)s)' % row)
            q2 = "select londiste.restore_table_fkey(%(from_table)s, %(fkey_name)s)"
            dst_curs.execute(q2, row)
            dst_db.commit()

    def drop_fkeys(self, dst_db, table_name):
        """Drop all foreign keys to and from this table.

        They need to be dropped one at a time to avoid deadlocks with user code.
        """

        dst_curs = dst_db.cursor()
        q = "select * from londiste.find_table_fkeys(%s)"
        dst_curs.execute(q, [table_name])
        fkey_list = dst_curs.fetchall()
        for row in fkey_list:
            self.log.info('Dropping fkey: %s' % row['fkey_name'])
            q2 = "select londiste.drop_table_fkey(%(from_table)s, %(fkey_name)s)"
            dst_curs.execute(q2, row)
            dst_db.commit()

    def process_root_node(self, dst_db):
        """On root node send seq changes to queue."""

        CascadedWorker.process_root_node(self, dst_db)

        q = "select * from londiste.root_check_seqs(%s)"
        self.exec_cmd(dst_db, q, [self.queue_name])

    def update_seq(self, dst_curs, ev):
        if self.copy_thread:
            return

        val = int(ev.data)
        seq = ev.extra1
        q = "select * from londiste.global_update_seq(%s, %s, %s)"
        self.exec_cmd(dst_curs, q, [self.queue_name, seq, val])

    def copy_event(self, dst_curs, ev, filtered_copy):
        # send only data events down (skipping seqs also)
        if filtered_copy:
            if ev.type[:9] in ('londiste.',):
                return
        CascadedWorker.copy_event(self, dst_curs, ev, filtered_copy)

    def exception_hook(self, det, emsg):
        # add event info to error message
        if self.current_event:
            ev = self.current_event
            info = "[ev_id=%d,ev_txid=%d] " % (ev.ev_id,ev.ev_txid)
            emsg = info + emsg
        super(Replicator, self).exception_hook(det, emsg)

if __name__ == '__main__':
    script = Replicator(sys.argv[1:])
    script.start()

########NEW FILE########
__FILENAME__ = repair

"""Repair data on subscriber.

Walks tables by primary key and searches for missing inserts/updates/deletes.
"""

import sys, os, skytools, subprocess

from londiste.syncer import Syncer

__all__ = ['Repairer']

def unescape(s):
    """Remove copy escapes."""
    return skytools.unescape_copy(s)

class Repairer(Syncer):
    """Walks tables in primary key order and checks if data matches."""

    cnt_insert = 0
    cnt_update = 0
    cnt_delete = 0
    total_src = 0
    total_dst = 0
    pkey_list = []
    common_fields = []
    apply_curs = None

    def init_optparse(self, p=None):
        """Initialize cmdline switches."""
        p = super(Repairer, self).init_optparse(p)
        p.add_option("--apply", action="store_true", help="apply fixes")
        return p

    def process_sync(self, t1, t2, src_db, dst_db):
        """Actual comparison."""

        apply_db = None

        if self.options.apply:
            apply_db = self.get_database('db', cache='applydb', autocommit=1)
            self.apply_curs = apply_db.cursor()
            self.apply_curs.execute("set session_replication_role = 'replica'")

        src_tbl = t1.dest_table
        dst_tbl = t2.dest_table

        src_curs = src_db.cursor()
        dst_curs = dst_db.cursor()

        self.log.info('Checking %s', dst_tbl)

        self.common_fields = []
        self.fq_common_fields = []
        self.pkey_list = []
        self.load_common_columns(src_tbl, dst_tbl, src_curs, dst_curs)

        dump_src = dst_tbl + ".src"
        dump_dst = dst_tbl + ".dst"
        dump_src_sorted = dump_src + ".sorted"
        dump_dst_sorted = dump_dst + ".sorted"

        dst_where = t2.plugin.get_copy_condition(src_curs, dst_curs)
        src_where = dst_where

        self.log.info("Dumping src table: %s", src_tbl)
        self.dump_table(src_tbl, src_curs, dump_src, src_where)
        src_db.commit()
        self.log.info("Dumping dst table: %s", dst_tbl)
        self.dump_table(dst_tbl, dst_curs, dump_dst, dst_where)
        dst_db.commit()

        self.log.info("Sorting src table: %s", dump_src)
        self.do_sort(dump_src, dump_src_sorted)
        self.log.info("Sorting dst table: %s", dump_dst)
        self.do_sort(dump_dst, dump_dst_sorted)

        self.dump_compare(dst_tbl, dump_src_sorted, dump_dst_sorted)

        os.unlink(dump_src)
        os.unlink(dump_dst)
        os.unlink(dump_src_sorted)
        os.unlink(dump_dst_sorted)

    def do_sort(self, src, dst):
        """ Sort contents of src file, write them to dst file. """

        p = subprocess.Popen(["sort", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        s_ver = p.communicate()[0]
        del p

        xenv = os.environ.copy()
        xenv['LANG'] = 'C'
        xenv['LC_ALL'] = 'C'

        cmdline = ['sort', '-T', '.']
        if s_ver.find("coreutils") > 0:
            cmdline.append('-S')
            cmdline.append('30%')
        cmdline.append('-o')
        cmdline.append(dst)
        cmdline.append(src)
        p = subprocess.Popen(cmdline, env = xenv)
        if p.wait() != 0:
            raise Exception('sort failed')

    def load_common_columns(self, src_tbl, dst_tbl, src_curs, dst_curs):
        """Get common fields, put pkeys in start."""

        self.pkey_list = skytools.get_table_pkeys(src_curs, src_tbl)
        dst_pkey = skytools.get_table_pkeys(dst_curs, dst_tbl)
        if dst_pkey != self.pkey_list:
            self.log.error('pkeys do not match')
            sys.exit(1)

        src_cols = skytools.get_table_columns(src_curs, src_tbl)
        dst_cols = skytools.get_table_columns(dst_curs, dst_tbl)
        field_list = []
        for f in self.pkey_list:
            field_list.append(f)
        for f in src_cols:
            if f in self.pkey_list:
                continue
            if f in dst_cols:
                field_list.append(f)

        self.common_fields = field_list

        fqlist = [skytools.quote_ident(col) for col in field_list]
        self.fq_common_fields = fqlist

        cols = ",".join(fqlist)
        self.log.debug("using columns: %s", cols)

    def dump_table(self, tbl, curs, fn, whr):
        """Dump table to disk."""
        cols = ','.join(self.fq_common_fields)
        if len(whr) == 0:
            whr = 'true'
        q = "copy (SELECT %s FROM %s WHERE %s) to stdout" % (cols, skytools.quote_fqident(tbl), whr)
        self.log.debug("Query: %s", q)
        f = open(fn, "w", 64*1024)
        curs.copy_expert(q, f)
        size = f.tell()
        f.close()
        self.log.info('%s: Got %d bytes', tbl, size)

    def get_row(self, ln):
        """Parse a row into dict."""
        if not ln:
            return None
        t = ln[:-1].split('\t')
        row = {}
        for i in range(len(self.common_fields)):
            row[self.common_fields[i]] = t[i]
        return row

    def dump_compare(self, tbl, src_fn, dst_fn):
        """ Compare two table dumps, create sql file to fix target table
            or apply changes to target table directly.
        """
        self.log.info("Comparing dumps: %s", tbl)
        self.cnt_insert = 0
        self.cnt_update = 0
        self.cnt_delete = 0
        self.total_src = 0
        self.total_dst = 0
        f1 = open(src_fn, "r", 64*1024)
        f2 = open(dst_fn, "r", 64*1024)
        src_ln = f1.readline()
        dst_ln = f2.readline()
        if src_ln: self.total_src += 1
        if dst_ln: self.total_dst += 1

        fix = "fix.%s.sql" % tbl
        if os.path.isfile(fix):
            os.unlink(fix)

        while src_ln or dst_ln:
            keep_src = keep_dst = 0
            if src_ln != dst_ln:
                src_row = self.get_row(src_ln)
                dst_row = self.get_row(dst_ln)

                diff = self.cmp_keys(src_row, dst_row)
                if diff > 0:
                    # src > dst
                    self.got_missed_delete(tbl, dst_row)
                    keep_src = 1
                elif diff < 0:
                    # src < dst
                    self.got_missed_insert(tbl, src_row)
                    keep_dst = 1
                else:
                    if self.cmp_data(src_row, dst_row) != 0:
                        self.got_missed_update(tbl, src_row, dst_row)

            if not keep_src:
                src_ln = f1.readline()
                if src_ln: self.total_src += 1
            if not keep_dst:
                dst_ln = f2.readline()
                if dst_ln: self.total_dst += 1

        self.log.info("finished %s: src: %d rows, dst: %d rows,"
                " missed: %d inserts, %d updates, %d deletes",
                tbl, self.total_src, self.total_dst,
                self.cnt_insert, self.cnt_update, self.cnt_delete)

    def got_missed_insert(self, tbl, src_row):
        """Create sql for missed insert."""
        self.cnt_insert += 1
        fld_list = self.common_fields
        fq_list = []
        val_list = []
        for f in fld_list:
            fq_list.append(skytools.quote_ident(f))
            v = unescape(src_row[f])
            val_list.append(skytools.quote_literal(v))
        q = "insert into %s (%s) values (%s);" % (
                tbl, ", ".join(fq_list), ", ".join(val_list))
        self.show_fix(tbl, q, 'insert')

    def got_missed_update(self, tbl, src_row, dst_row):
        """Create sql for missed update."""
        self.cnt_update += 1
        fld_list = self.common_fields
        set_list = []
        whe_list = []
        for f in self.pkey_list:
            self.addcmp(whe_list, skytools.quote_ident(f), unescape(src_row[f]))
        for f in fld_list:
            v1 = src_row[f]
            v2 = dst_row[f]
            if self.cmp_value(v1, v2) == 0:
                continue

            self.addeq(set_list, skytools.quote_ident(f), unescape(v1))
            self.addcmp(whe_list, skytools.quote_ident(f), unescape(v2))

        q = "update only %s set %s where %s;" % (
                tbl, ", ".join(set_list), " and ".join(whe_list))
        self.show_fix(tbl, q, 'update')

    def got_missed_delete(self, tbl, dst_row):
        """Create sql for missed delete."""
        self.cnt_delete += 1
        whe_list = []
        for f in self.pkey_list:
            self.addcmp(whe_list, skytools.quote_ident(f), unescape(dst_row[f]))
        q = "delete from only %s where %s;" % (skytools.quote_fqident(tbl), " and ".join(whe_list))
        self.show_fix(tbl, q, 'delete')

    def show_fix(self, tbl, q, desc):
        """Print/write/apply repair sql."""
        self.log.debug("missed %s: %s", desc, q)
        if self.apply_curs:
            self.apply_curs.execute(q)
        else:
            fn = "fix.%s.sql" % tbl
            open(fn, "a").write("%s\n" % q)

    def addeq(self, list, f, v):
        """Add quoted SET."""
        vq = skytools.quote_literal(v)
        s = "%s = %s" % (f, vq)
        list.append(s)

    def addcmp(self, list, f, v):
        """Add quoted comparison."""
        if v is None:
            s = "%s is null" % f
        else:
            vq = skytools.quote_literal(v)
            s = "%s = %s" % (f, vq)
        list.append(s)

    def cmp_data(self, src_row, dst_row):
        """Compare data field-by-field."""
        for k in self.common_fields:
            v1 = src_row[k]
            v2 = dst_row[k]
            if self.cmp_value(v1, v2) != 0:
                return -1
        return 0

    def cmp_value(self, v1, v2):
        """Compare single field, tolerates tz vs notz dates."""
        if v1 == v2:
            return 0

        # try to work around tz vs. notz
        z1 = len(v1)
        z2 = len(v2)
        if z1 == z2 + 3 and z2 >= 19 and v1[z2] == '+':
            v1 = v1[:-3]
            if v1 == v2:
                return 0
        elif z1 + 3 == z2 and z1 >= 19 and v2[z1] == '+':
            v2 = v2[:-3]
            if v1 == v2:
                return 0

        return -1

    def cmp_keys(self, src_row, dst_row):
        """Compare primary keys of the rows.

        Returns 1 if src > dst, -1 if src < dst and 0 if src == dst"""

        # None means table is done.  tag it larger than any existing row.
        if src_row is None:
            if dst_row is None:
                return 0
            return 1
        elif dst_row is None:
            return -1

        for k in self.pkey_list:
            v1 = src_row[k]
            v2 = dst_row[k]
            if v1 < v2:
                return -1
            elif v1 > v2:
                return 1
        return 0

########NEW FILE########
__FILENAME__ = syncer

"""Catch moment when tables are in sync on master and slave.
"""

import sys, time, skytools
from londiste.handler import build_handler, load_handler_modules

from londiste.util import find_copy_source

class ATable:
    def __init__(self, row):
        self.table_name = row['table_name']
        self.dest_table = row['dest_table'] or row['table_name']
        self.merge_state = row['merge_state']
        attrs = row['table_attrs'] or ''
        self.table_attrs = skytools.db_urldecode(attrs)
        hstr = self.table_attrs.get('handler', '')
        self.plugin = build_handler(self.table_name, hstr, row['dest_table'])

class Syncer(skytools.DBScript):
    """Walks tables in primary key order and checks if data matches."""

    bad_tables = 0

    provider_info = None

    def __init__(self, args):
        """Syncer init."""
        skytools.DBScript.__init__(self, 'londiste3', args)
        self.set_single_loop(1)

        # compat names
        self.queue_name = self.cf.get("pgq_queue_name", '')
        self.consumer_name = self.cf.get('pgq_consumer_id', '')

        # good names
        if not self.queue_name:
            self.queue_name = self.cf.get("queue_name")
        if not self.consumer_name:
            self.consumer_name = self.cf.get('consumer_name', self.job_name)

        self.lock_timeout = self.cf.getfloat('lock_timeout', 10)

        if self.pidfile:
            self.pidfile += ".repair"

        load_handler_modules(self.cf)

    def set_lock_timeout(self, curs):
        ms = int(1000 * self.lock_timeout)
        if ms > 0:
            q = "SET LOCAL statement_timeout = %d" % ms
            self.log.debug(q)
            curs.execute(q)

    def init_optparse(self, p=None):
        """Initialize cmdline switches."""
        p = skytools.DBScript.init_optparse(self, p)
        p.add_option("--force", action="store_true", help="ignore lag")
        return p

    def get_provider_info(self, setup_curs):
        q = "select ret_code, ret_note, node_name, node_type, worker_name"\
            " from pgq_node.get_node_info(%s)"
        res = self.exec_cmd(setup_curs, q, [self.queue_name])
        pnode = res[0]
        self.log.info('Provider: %s (%s)', pnode['node_name'], pnode['node_type'])
        return pnode

    def check_consumer(self, setup_db, dst_db):
        """Before locking anything check if consumer is working ok."""

        setup_curs = setup_db.cursor()
        dst_curs = dst_db.cursor()
        c = 0
        while 1:
            q = "select * from pgq_node.get_consumer_state(%s, %s)"
            res = self.exec_cmd(dst_db, q, [self.queue_name, self.consumer_name])
            completed_tick = res[0]['completed_tick']

            q = "select extract(epoch from ticker_lag) from pgq.get_queue_info(%s)"
            setup_curs.execute(q, [self.queue_name])
            ticker_lag = setup_curs.fetchone()[0]

            q = "select extract(epoch from (now() - t.tick_time)) as lag"\
                " from pgq.tick t, pgq.queue q"\
                " where q.queue_name = %s"\
                "   and t.tick_queue = q.queue_id"\
                "   and t.tick_id = %s"
            setup_curs.execute(q, [self.queue_name, completed_tick])
            res = setup_curs.fetchall()

            if len(res) == 0:
                self.log.warning('Consumer completed_tick (%d) to not exists on provider (%s), too big lag?',
                                 completed_tick, self.provider_info['node_name'])
                self.sleep(10)
                continue

            consumer_lag = res[0][0]
            if consumer_lag < ticker_lag + 5:
                break

            lag_msg = 'Consumer lag: %s, ticker_lag %s, too big difference, waiting'
            if c % 30 == 0:
                self.log.warning(lag_msg, consumer_lag, ticker_lag)
            else:
                self.log.debug(lag_msg, consumer_lag, ticker_lag)
            c += 1
            time.sleep(1)

    def get_tables(self, db):
        """Load table info.

        Returns tuple of (dict(name->ATable), namelist)"""

        curs = db.cursor()
        q = "select table_name, merge_state, dest_table, table_attrs"\
            " from londiste.get_table_list(%s) where local"
        curs.execute(q, [self.queue_name])
        rows = curs.fetchall()
        db.commit()

        res = {}
        names = []
        for row in rows:
            t = ATable(row)
            res[t.table_name] = t
            names.append(t.table_name)
        return res, names

    def work(self):
        """Syncer main function."""

        # 'SELECT 1' and COPY must use same snapshot, so change isolation level.
        dst_db = self.get_database('db', isolation_level = skytools.I_REPEATABLE_READ)
        pnode, ploc = self.get_provider_location(dst_db)

        dst_tables, names = self.get_tables(dst_db)

        if len(self.args) > 2:
            tlist = self.args[2:]
        else:
            tlist = names

        for tbl in tlist:
            tbl = skytools.fq_name(tbl)
            if not tbl in dst_tables:
                self.log.warning('Table not subscribed: %s', tbl)
                continue
            t2 = dst_tables[tbl]
            if t2.merge_state != 'ok':
                self.log.warning('Table %s not synced yet, no point', tbl)
                continue

            pnode, ploc, wname = find_copy_source(self, self.queue_name, tbl, pnode, ploc)
            self.log.info('%s: Using node %s as provider', tbl, pnode)

            if wname is None:
                wname = self.consumer_name
            self.downstream_worker_name = wname

            self.process_one_table(tbl, t2, dst_db, pnode, ploc)

        # signal caller about bad tables
        sys.exit(self.bad_tables)

    def process_one_table(self, tbl, t2, dst_db, provider_node, provider_loc):

        lock_db = self.get_database('lock_db', connstr = provider_loc, profile = 'remote')
        setup_db = self.get_database('setup_db', autocommit = 1, connstr = provider_loc, profile = 'remote')

        src_db = self.get_database('provider_db', connstr = provider_loc, profile = 'remote',
                                   isolation_level = skytools.I_REPEATABLE_READ)

        setup_curs = setup_db.cursor()

        # provider node info
        self.provider_info = self.get_provider_info(setup_curs)

        src_tables, ignore = self.get_tables(src_db)
        if not tbl in src_tables:
            self.log.warning('Table not available on provider: %s', tbl)
            return
        t1 = src_tables[tbl]

        if t1.merge_state != 'ok':
            self.log.warning('Table %s not ready yet on provider', tbl)
            return

        #self.check_consumer(setup_db, dst_db)

        self.check_table(t1, t2, lock_db, src_db, dst_db, setup_db)
        lock_db.commit()
        src_db.commit()
        dst_db.commit()

        self.close_database('setup_db')
        self.close_database('lock_db')
        self.close_database('provider_db')

    def force_tick(self, setup_curs, wait=True):
        q = "select pgq.force_tick(%s)"
        setup_curs.execute(q, [self.queue_name])
        res = setup_curs.fetchone()
        cur_pos = res[0]
        if not wait:
            return cur_pos

        start = time.time()
        while 1:
            time.sleep(0.5)
            setup_curs.execute(q, [self.queue_name])
            res = setup_curs.fetchone()
            if res[0] != cur_pos:
                # new pos
                return res[0]

            # dont loop more than 10 secs
            dur = time.time() - start
            #if dur > 10 and not self.options.force:
            #    raise Exception("Ticker seems dead")

    def check_table(self, t1, t2, lock_db, src_db, dst_db, setup_db):
        """Get transaction to same state, then process."""

        src_tbl = t1.dest_table
        dst_tbl = t2.dest_table

        lock_curs = lock_db.cursor()
        src_curs = src_db.cursor()
        dst_curs = dst_db.cursor()

        if not skytools.exists_table(src_curs, src_tbl):
            self.log.warning("Table %s does not exist on provider side", src_tbl)
            return
        if not skytools.exists_table(dst_curs, dst_tbl):
            self.log.warning("Table %s does not exist on subscriber side", dst_tbl)
            return

        # lock table against changes
        try:
            if self.provider_info['node_type'] == 'root':
                self.lock_table_root(lock_db, setup_db, dst_db, src_tbl, dst_tbl)
            else:
                self.lock_table_branch(lock_db, setup_db, dst_db, src_tbl, dst_tbl)

            # take snapshot on provider side
            src_db.commit()
            src_curs.execute("SELECT 1")

            # take snapshot on subscriber side
            dst_db.commit()
            dst_curs.execute("SELECT 1")
        finally:
            # release lock
            if self.provider_info['node_type'] == 'root':
                self.unlock_table_root(lock_db, setup_db)
            else:
                self.unlock_table_branch(lock_db, setup_db)

        # do work
        bad = self.process_sync(t1, t2, src_db, dst_db)
        if bad:
            self.bad_tables += 1

        # done
        src_db.commit()
        dst_db.commit()

    def lock_table_root(self, lock_db, setup_db, dst_db, src_tbl, dst_tbl):

        setup_curs = setup_db.cursor()
        lock_curs = lock_db.cursor()

        # lock table in separate connection
        self.log.info('Locking %s', src_tbl)
        lock_db.commit()
        self.set_lock_timeout(lock_curs)
        lock_time = time.time()
        lock_curs.execute("LOCK TABLE %s IN SHARE MODE" % skytools.quote_fqident(src_tbl))

        # now wait until consumer has updated target table until locking
        self.log.info('Syncing %s', dst_tbl)

        # consumer must get futher than this tick
        tick_id = self.force_tick(setup_curs)
        # try to force second tick also
        self.force_tick(setup_curs)

        # now wait
        while 1:
            time.sleep(0.5)

            q = "select * from pgq_node.get_node_info(%s)"
            res = self.exec_cmd(dst_db, q, [self.queue_name])
            last_tick = res[0]['worker_last_tick']
            if last_tick > tick_id:
                break

            # limit lock time
            if time.time() > lock_time + self.lock_timeout and not self.options.force:
                self.log.error('Consumer lagging too much, exiting')
                lock_db.rollback()
                sys.exit(1)

    def unlock_table_root(self, lock_db, setup_db):
        lock_db.commit()

    def lock_table_branch(self, lock_db, setup_db, dst_db, src_tbl, dst_tbl):
        setup_curs = setup_db.cursor()

        lock_time = time.time()
        self.old_worker_paused = self.pause_consumer(setup_curs, self.provider_info['worker_name'])

        lock_curs = lock_db.cursor()
        self.log.info('Syncing %s', dst_tbl)

        # consumer must get futher than this tick
        tick_id = self.force_tick(setup_curs, False)

        # now wait
        while 1:
            time.sleep(0.5)

            q = "select * from pgq_node.get_node_info(%s)"
            res = self.exec_cmd(dst_db, q, [self.queue_name])
            last_tick = res[0]['worker_last_tick']
            if last_tick > tick_id:
                break

            # limit lock time
            if time.time() > lock_time + self.lock_timeout and not self.options.force:
                self.log.error('Consumer lagging too much, exiting')
                lock_db.rollback()
                sys.exit(1)

    def unlock_table_branch(self, lock_db, setup_db):
        # keep worker paused if it was so before
        if self.old_worker_paused:
            return
        setup_curs = setup_db.cursor()
        self.resume_consumer(setup_curs, self.provider_info['worker_name'])

    def process_sync(self, t1, t2, src_db, dst_db):
        """It gets 2 connections in state where tbl should be in same state.
        """
        raise Exception('process_sync not implemented')

    def get_provider_location(self, dst_db):
        curs = dst_db.cursor()
        q = "select * from pgq_node.get_node_info(%s)"
        rows = self.exec_cmd(dst_db, q, [self.queue_name])
        return (rows[0]['provider_node'], rows[0]['provider_location'])

    def pause_consumer(self, curs, cons_name):
        self.log.info("Pausing upstream worker: %s", cons_name)
        return self.set_pause_flag(curs, cons_name, True)

    def resume_consumer(self, curs, cons_name):
        self.log.info("Resuming upstream worker: %s", cons_name)
        return self.set_pause_flag(curs, cons_name, False)

    def set_pause_flag(self, curs, cons_name, flag):
        q = "select * from pgq_node.get_consumer_state(%s, %s)"
        res = self.exec_cmd(curs, q, [self.queue_name, cons_name])
        oldflag = res[0]['paused']

        q = "select * from pgq_node.set_consumer_paused(%s, %s, %s)"
        self.exec_cmd(curs, q, [self.queue_name, cons_name, flag])

        while 1:
            q = "select * from pgq_node.get_consumer_state(%s, %s)"
            res = self.exec_cmd(curs, q, [self.queue_name, cons_name])
            if res[0]['uptodate']:
                break
            time.sleep(0.5)
        return oldflag

########NEW FILE########
__FILENAME__ = table_copy
#! /usr/bin/env python

"""Do a full table copy.

For internal usage.
"""

import sys, time, skytools

from londiste.util import find_copy_source
from skytools.dbstruct import *
from londiste.playback import *

__all__ = ['CopyTable']

class CopyTable(Replicator):
    """Table copy thread implementation."""

    reg_ok = False

    def __init__(self, args, copy_thread = 1):
        """Initializer.  copy_thread arg shows if the copy process is separate
        from main Playback thread or not.  copy_thread=0 means copying happens
        in same process.
        """

        Replicator.__init__(self, args)

        if not copy_thread:
            raise Exception("Combined copy not supported")

        if len(self.args) != 3:
            self.log.error("londiste copy requires table name")
            sys.exit(1)
        self.copy_table_name = self.args[2]

        sfx = self.get_copy_suffix(self.copy_table_name)
        self.old_consumer_name = self.consumer_name
        self.pidfile += sfx
        self.consumer_name += sfx
        self.copy_thread = 1
        self.main_worker = False

    def get_copy_suffix(self, tblname):
        return ".copy.%s" % tblname

    def reload_table_stat(self, dst_curs, tblname):
        self.load_table_state(dst_curs)
        if tblname not in self.table_map:
            self.log.warning('Table %s removed from replication', tblname)
            sys.exit(1)
        t = self.table_map[tblname]
        return t

    def do_copy(self, tbl_stat, src_db, dst_db):
        """Entry point into copying logic."""

        dst_db.commit()

        src_curs = src_db.cursor()
        dst_curs = dst_db.cursor()

        while 1:
            if tbl_stat.copy_role == 'wait-copy':
                self.log.info('waiting for first partition to initialize copy')
            elif tbl_stat.max_parallel_copies_reached():
                self.log.info('number of max parallel copies (%s) reached',
                                tbl_stat.max_parallel_copy)
            else:
                break
            time.sleep(10)
            tbl_stat = self.reload_table_stat(dst_curs, tbl_stat.name)
            dst_db.commit()

        while 1:
            pmap = self.get_state_map(src_db.cursor())
            src_db.commit()
            if tbl_stat.name not in pmap:
                raise Exception("table %s not available on provider" % tbl_stat.name)
            pt = pmap[tbl_stat.name]
            if pt.state == TABLE_OK:
                break

            self.log.warning("table %s not in sync yet on provider, waiting", tbl_stat.name)
            time.sleep(10)

        src_real_table = pt.dest_table

        # 0 - dont touch
        # 1 - single tx
        # 2 - multi tx
        cmode = 1
        if tbl_stat.copy_role == 'lead':
            cmode = 2
        elif tbl_stat.copy_role:
            cmode = 0

        # We need to see COPY snapshot from txid_current_snapshot() later.
        oldiso = src_db.isolation_level
        src_db.set_isolation_level(skytools.I_REPEATABLE_READ)
        src_db.commit()

        self.sync_database_encodings(src_db, dst_db)

        self.log.info("Starting full copy of %s", tbl_stat.name)

        # just in case, drop all fkeys (in case "replay" was skipped)
        # !! this may commit, so must be done before anything else !!
        if cmode > 0:
            self.drop_fkeys(dst_db, tbl_stat.dest_table)

        # now start ddl-dropping tx
        if cmode > 0:
            q = "lock table " + skytools.quote_fqident(tbl_stat.dest_table)
            dst_curs.execute(q)

        # find dst struct
        src_struct = TableStruct(src_curs, src_real_table)
        dst_struct = TableStruct(dst_curs, tbl_stat.dest_table)

        # take common columns, warn on missing ones
        dlist = dst_struct.get_column_list()
        slist = src_struct.get_column_list()
        common_cols = []
        for c in slist:
            if c not in dlist:
                self.log.warning("Table %s column %s does not exist on subscriber",
                                 tbl_stat.name, c)
            else:
                common_cols.append(c)
        for c in dlist:
            if c not in slist:
                self.log.warning("Table %s column %s does not exist on provider",
                                 tbl_stat.name, c)

        # drop unnecessary stuff
        if cmode > 0:
            objs = T_CONSTRAINT | T_INDEX | T_RULE | T_PARENT # | T_TRIGGER
            dst_struct.drop(dst_curs, objs, log = self.log)

            # drop data
            if tbl_stat.table_attrs.get('skip_truncate'):
                self.log.info("%s: skipping truncate", tbl_stat.name)
            else:
                self.log.info("%s: truncating", tbl_stat.name)
                q = "truncate "
                if dst_db.server_version >= 80400:
                    q += "only "
                q += skytools.quote_fqident(tbl_stat.dest_table)
                dst_curs.execute(q)

            if cmode == 2 and tbl_stat.dropped_ddl is None:
                ddl = dst_struct.get_create_sql(objs)
                if ddl:
                    q = "select * from londiste.local_set_table_struct(%s, %s, %s)"
                    self.exec_cmd(dst_curs, q, [self.queue_name, tbl_stat.name, ddl])
                else:
                    ddl = None
                dst_db.commit()
                tbl_stat.dropped_ddl = ddl

        # do truncate & copy
        self.log.info("%s: start copy", tbl_stat.name)
        p = tbl_stat.get_plugin()
        stats = p.real_copy(src_real_table, src_curs, dst_curs, common_cols)
        if stats:
            self.log.info("%s: copy finished: %d bytes, %d rows",
                          tbl_stat.name, stats[0], stats[1])

        # get snapshot
        src_curs.execute("select txid_current_snapshot()")
        snapshot = src_curs.fetchone()[0]
        src_db.commit()

        # restore old behaviour
        src_db.set_isolation_level(oldiso)
        src_db.commit()

        tbl_stat.change_state(TABLE_CATCHING_UP)
        tbl_stat.change_snapshot(snapshot)
        self.save_table_state(dst_curs)

        # create previously dropped objects
        if cmode == 1:
            dst_struct.create(dst_curs, objs, log = self.log)
        elif cmode == 2:
            dst_db.commit()

            # start waiting for other copy processes to finish
            while tbl_stat.copy_role:
                self.log.info('waiting for other partitions to finish copy')
                time.sleep(10)
                tbl_stat = self.reload_table_stat(dst_curs, tbl_stat.name)
                dst_db.commit()

            if tbl_stat.dropped_ddl is not None:
                self.looping = 0
                for ddl in skytools.parse_statements(tbl_stat.dropped_ddl):
                    self.log.info(ddl)
                    dst_curs.execute(ddl)
                q = "select * from londiste.local_set_table_struct(%s, %s, NULL)"
                self.exec_cmd(dst_curs, q, [self.queue_name, tbl_stat.name])
                tbl_stat.dropped_ddl = None
                self.looping = 1
            dst_db.commit()

        # hack for copy-in-playback
        if not self.copy_thread:
            tbl_stat.change_state(TABLE_OK)
            self.save_table_state(dst_curs)
        dst_db.commit()

        # copy finished
        if tbl_stat.copy_role == 'wait-replay':
            return

        # if copy done, request immediate tick from pgqd,
        # to make state juggling faster.  on mostly idle db-s
        # each step may take tickers idle_timeout secs, which is pain.
        q = "select pgq.force_tick(%s)"
        src_curs.execute(q, [self.queue_name])
        src_db.commit()

    def work(self):
        if not self.reg_ok:
            # check if needed? (table, not existing reg)
            self.register_copy_consumer()
            self.reg_ok = True
        return Replicator.work(self)

    def register_copy_consumer(self):
        dst_db = self.get_database('db')
        dst_curs = dst_db.cursor()

        # fetch table attrs
        q = "select * from londiste.get_table_list(%s) where table_name = %s"
        dst_curs.execute(q, [ self.queue_name, self.copy_table_name ])
        rows = dst_curs.fetchall()
        attrs = {}
        if len(rows) > 0:
            v_attrs = rows[0]['table_attrs']
            if v_attrs:
                attrs = skytools.db_urldecode(v_attrs)

        # fetch parent consumer state
        q = "select * from pgq_node.get_consumer_state(%s, %s)"
        rows = self.exec_cmd(dst_db, q, [ self.queue_name, self.old_consumer_name ])
        state = rows[0]
        source_node = state['provider_node']
        source_location = state['provider_location']

        # do we have node here?
        if 'copy_node' in attrs:
            if attrs['copy_node'] == '?':
                source_node, source_location, wname = find_copy_source(self,
                        self.queue_name, self.copy_table_name, source_node, source_location)
            else:
                # take node from attrs
                source_node = attrs['copy_node']
                q = "select * from pgq_node.get_queue_locations(%s) where node_name = %s"
                dst_curs.execute(q, [ self.queue_name, source_node ])
                rows = dst_curs.fetchall()
                if len(rows):
                    source_location = rows[0]['node_location']

        self.log.info("Using '%s' as source node", source_node)
        self.register_consumer(source_location)

if __name__ == '__main__':
    script = CopyTable(sys.argv[1:])
    script.start()

########NEW FILE########
__FILENAME__ = util

import skytools
import londiste.handler

__all__ = ['handler_allows_copy', 'find_copy_source']

def handler_allows_copy(table_attrs):
    """Decide if table is copyable based on attrs."""
    if not table_attrs:
        return True
    attrs = skytools.db_urldecode(table_attrs)
    hstr = attrs.get('handler', '')
    p = londiste.handler.build_handler('unused.string', hstr, None)
    return p.needs_table()

def find_copy_source(script, queue_name, copy_table_name, node_name, node_location):
    """Find source node for table.

    @param script: DbScript
    @param queue_name: name of the cascaded queue
    @param copy_table_name: name of the table (or list of names)
    @param node_name: target node name
    @param node_location: target node location
    @returns (node_name, node_location, downstream_worker_name) of source node
    """

    # None means no steps upwards were taken, so local consumer is worker
    worker_name = None

    if isinstance(copy_table_name, str):
        need = set([copy_table_name])
    else:
        need = set(copy_table_name)

    while 1:
        src_db = script.get_database('_source_db', connstr = node_location, autocommit = 1, profile = 'remote')
        src_curs = src_db.cursor()

        q = "select * from pgq_node.get_node_info(%s)"
        src_curs.execute(q, [queue_name])
        info = src_curs.fetchone()
        if info['ret_code'] >= 400:
            raise skytools.UsageError("Node does not exist")

        script.log.info("Checking if %s can be used for copy", info['node_name'])

        q = "select table_name, local, table_attrs from londiste.get_table_list(%s)"
        src_curs.execute(q, [queue_name])
        got = set()
        for row in src_curs.fetchall():
            tbl = row['table_name']
            if tbl not in need:
                continue
            if not row['local']:
                script.log.debug("Problem: %s is not local", tbl)
                continue
            if not handler_allows_copy(row['table_attrs']):
                script.log.debug("Problem: %s handler does not store data [%s]", tbl, row['table_attrs'])
                continue
            script.log.debug("Good: %s is usable", tbl)
            got.add(tbl)

        script.close_database('_source_db')

        if got == need:
            script.log.info("Node %s seems good source, using it", info['node_name'])
            return node_name, node_location, worker_name
        else:
            script.log.info("Node %s does not have all tables", info['node_name'])

        if info['node_type'] == 'root':
            raise skytools.UsageError("Found root and no source found")

        # walk upwards
        node_name = info['provider_node']
        node_location = info['provider_location']
        worker_name = info['worker_name']

########NEW FILE########
__FILENAME__ = londiste
#! /usr/bin/env python

"""Londiste launcher.
"""

import sys, os, os.path, optparse

import pkgloader
pkgloader.require('skytools', '3.0')

import skytools

# python 2.3 will try londiste.py first...
if os.path.exists(os.path.join(sys.path[0], 'londiste.py')) \
    and not os.path.isdir(os.path.join(sys.path[0], 'londiste')):
    del sys.path[0]

import londiste, pgq.cascade.admin

command_usage = pgq.cascade.admin.command_usage + """
Replication Daemon:
  worker                replay events to subscriber

Replication Administration:
  add-table TBL ...     add table to queue
  remove-table TBL ...  remove table from queue
  change-handler TBL    change handler for the table
  add-seq SEQ ...       add sequence to provider
  remove-seq SEQ ...    remove sequence from provider
  tables                show all tables on provider
  seqs                  show all sequences on provider
  missing               list tables subscriber has not yet attached to
  resync TBL ...        do full copy again
  wait-sync             wait until all tables are in sync

Replication Extra:
  check                 compare table structure on both sides
  fkeys                 print out fkey drop/create commands
  compare [TBL ...]     compare table contents on both sides
  repair [TBL ...]      repair data on subscriber
  execute [FILE ...]    execute SQL files on set
  show-handlers [..]    show info about all or specific handler

Internal Commands:
  copy                  copy table logic
"""

cmd_handlers = (
    (('create-root', 'create-branch', 'create-leaf', 'members', 'tag-dead', 'tag-alive',
      'change-provider', 'rename-node', 'status', 'node-status', 'pause', 'resume', 'node-info',
      'drop-node', 'takeover', 'resurrect'), londiste.LondisteSetup),
    (('add-table', 'remove-table', 'change-handler', 'add-seq', 'remove-seq', 'tables', 'seqs',
      'missing', 'resync', 'wait-sync', 'wait-root', 'wait-provider',
      'check', 'fkeys', 'execute'), londiste.LondisteSetup),
    (('show-handlers',), londiste.LondisteSetup),
    (('worker',), londiste.Replicator),
    (('compare',), londiste.Comparator),
    (('repair',), londiste.Repairer),
    (('copy',), londiste.CopyTable),
)

class Londiste(skytools.DBScript):
    def __init__(self, args):
        self.full_args = args

        skytools.DBScript.__init__(self, 'londiste3', args)

        if len(self.args) < 2:
            print("need command")
            sys.exit(1)
        cmd = self.args[1]
        self.script = None
        for names, cls in cmd_handlers:
            if cmd in names:
                self.script = cls(args)
                break
        if not self.script:
            print("Unknown command '%s', use --help for help" % cmd)
            sys.exit(1)

    def start(self):
        self.script.start()

    def print_ini(self):
        """Let the Replicator print the default config."""
        londiste.Replicator(self.full_args)

    def init_optparse(self, parser=None):
        p = super(Londiste, self).init_optparse(parser)
        p.set_usage(command_usage.strip())

        g = optparse.OptionGroup(p, "options for cascading")
        g.add_option("--provider",
                help = "init: upstream node temp connect string")
        g.add_option("--target", metavar = "NODE",
                help = "switchover: target node")
        g.add_option("--merge", metavar = "QUEUE",
                help = "create-leaf: combined queue name")
        g.add_option("--dead", metavar = "NODE", action = 'append',
                help = "cascade: assume node is dead")
        g.add_option("--dead-root", action = 'store_true',
                help = "takeover: old node was root")
        g.add_option("--dead-branch", action = 'store_true',
                help = "takeover: old node was branch")
        g.add_option("--sync-watermark", metavar = "NODES",
                help = "create-branch: list of node names to sync wm with")
        p.add_option_group(g)

        g = optparse.OptionGroup(p, "repair queue position")
        g.add_option("--rewind", action = "store_true",
                help = "change queue position according to destination")
        g.add_option("--reset", action = "store_true",
                help = "reset queue position on destination side")
        p.add_option_group(g)

        g = optparse.OptionGroup(p, "options for add")
        g.add_option("--all", action="store_true",
                help = "add: include all possible tables")
        g.add_option("--wait-sync", action="store_true",
                help = "add: wait until all tables are in sync"),
        g.add_option("--dest-table", metavar = "NAME",
                help = "add: redirect changes to different table")
        g.add_option("--expect-sync", action="store_true", dest="expect_sync",
                help = "add: no copy needed", default=False)
        g.add_option("--skip-truncate", action="store_true", dest="skip_truncate",
                help = "add: keep old data", default=False)
        g.add_option("--create", action="store_true",
                help = "add: create table/seq if not exist, with minimal schema")
        g.add_option("--create-full", action="store_true",
                help = "add: create table/seq if not exist, with full schema")
        g.add_option("--trigger-flags",
                help="add: set trigger flags (BAIUDLQ)")
        g.add_option("--trigger-arg", action="append",
                help="add: custom trigger arg (can be specified multiple times)")
        g.add_option("--no-triggers", action="store_true",
                help="add: do not put triggers on table (makes sense on leaf)")
        g.add_option("--handler", action="store",
                help="add: custom handler for table")
        g.add_option("--handler-arg", action="append",
                help="add: argument to custom handler")
        g.add_option("--find-copy-node", dest="find_copy_node", action="store_true",
                help = "add: walk upstream to find node to copy from")
        g.add_option("--copy-node", metavar = "NODE", dest="copy_node",
                help = "add: use NODE as source for initial COPY")
        g.add_option("--merge-all", action="store_true",
                help="merge tables from all source queues", default=False)
        g.add_option("--no-merge", action="store_true",
                help="don't merge tables from source queues", default=False)
        g.add_option("--max-parallel-copy", metavar = "NUM", type = "int",
                help="max number of parallel copy processes")
        g.add_option("--skip-non-existing", action="store_true",
                help="add: skip object that does not exist")
        p.add_option_group(g)

        g = optparse.OptionGroup(p, "other options")
        g.add_option("--force", action="store_true",
                help = "add: ignore table differences, repair: ignore lag")
        g.add_option("--apply", action = "store_true",
                help="repair: apply fixes automatically")
        g.add_option("--count-only", action="store_true",
                help="compare: just count rows, do not compare data")
        p.add_option_group(g)

        return p

if __name__ == '__main__':
    script = Londiste(sys.argv[1:])
    script.start()

########NEW FILE########
__FILENAME__ = baseconsumer

"""PgQ consumer framework for Python.

todo:
    - pgq.next_batch_details()
    - tag_done() by default

"""

import sys, time, skytools

from pgq.event import *

__all__ = ['BaseConsumer', 'BaseBatchWalker']


class BaseBatchWalker(object):
    """Lazy iterator over batch events.

    Events are loaded using cursor.  It will be given
    as ev_list to process_batch(). It allows:

     - one for loop over events
     - len() after that
    """

    def __init__(self, curs, batch_id, queue_name, fetch_size = 300, consumer_filter = None):
        self.queue_name = queue_name
        self.fetch_size = fetch_size
        self.sql_cursor = "batch_walker"
        self.curs = curs
        self.length = 0
        self.batch_id = batch_id
        self.fetch_status = 0 # 0-not started, 1-in-progress, 2-done
        self.consumer_filter = consumer_filter

    def _make_event(self, queue_name, row):
        return Event(queue_name, row)

    def __iter__(self):
        if self.fetch_status:
            raise Exception("BatchWalker: double fetch? (%d)" % self.fetch_status)
        self.fetch_status = 1

        q = "select * from pgq.get_batch_cursor(%s, %s, %s, %s)"
        self.curs.execute(q, [self.batch_id, self.sql_cursor, self.fetch_size, self.consumer_filter])
        # this will return first batch of rows

        q = "fetch %d from %s" % (self.fetch_size, self.sql_cursor)
        while 1:
            rows = self.curs.fetchall()
            if not len(rows):
                break

            self.length += len(rows)
            for row in rows:
                ev = self._make_event(self.queue_name, row)
                yield ev

            # if less rows than requested, it was final block
            if len(rows) < self.fetch_size:
                break

            # request next block of rows
            self.curs.execute(q)

        self.curs.execute("close %s" % self.sql_cursor)

        self.fetch_status = 2

    def __len__(self):
        return self.length


class BaseConsumer(skytools.DBScript):
    """Consumer base class.
        Do not subclass directly (use pgq.Consumer or pgq.LocalConsumer instead)

    Config template::

        ## Parameters for pgq.Consumer ##

        # queue name to read from
        queue_name =

        # override consumer name
        #consumer_name = %(job_name)s

        # filter out only events for specific tables
        #table_filter = table1, table2

        # whether to use cursor to fetch events (0 disables)
        #pgq_lazy_fetch = 300

        # whether to read from source size in autocommmit mode
        # not compatible with pgq_lazy_fetch
        # the actual user script on top of pgq.Consumer must also support it
        #pgq_autocommit = 0

        # whether to wait for specified number of events,
        # before assigning a batch (0 disables)
        #pgq_batch_collect_events = 0

        # whether to wait specified amount of time,
        # before assigning a batch (postgres interval)
        #pgq_batch_collect_interval =

        # whether to stay behind queue top (postgres interval)
        #pgq_keep_lag =

        # in how many seconds to write keepalive stats for idle consumers
        # this stats is used for detecting that consumer is still running
        #keepalive_stats = 300
    """

    # by default, use cursor-based fetch
    default_lazy_fetch = 300

    # should reader connection be used in autocommit mode
    pgq_autocommit = 0

    # proper variables
    consumer_name = None
    queue_name = None

    # compat variables
    pgq_queue_name = None
    pgq_consumer_id = None

    pgq_lazy_fetch = None
    pgq_min_count = None
    pgq_min_interval = None
    pgq_min_lag = None

    batch_info = None

    consumer_filter = None

    keepalive_stats = None
    # statistics: time spent waiting for events
    idle_start = None

    _batch_walker_class = BaseBatchWalker

    def __init__(self, service_name, db_name, args):
        """Initialize new consumer.

        @param service_name: service_name for DBScript
        @param db_name: name of database for get_database()
        @param args: cmdline args for DBScript
        """

        skytools.DBScript.__init__(self, service_name, args)

        self.db_name = db_name

        # compat params
        self.consumer_name = self.cf.get("pgq_consumer_id", '')
        self.queue_name = self.cf.get("pgq_queue_name", '')

        # proper params
        if not self.consumer_name:
            self.consumer_name = self.cf.get("consumer_name", self.job_name)
        if not self.queue_name:
            self.queue_name = self.cf.get("queue_name")

        self.stat_batch_start = 0

        # compat vars
        self.pgq_queue_name = self.queue_name
        self.consumer_id = self.consumer_name

        # set default just once
        self.pgq_autocommit = self.cf.getint("pgq_autocommit", self.pgq_autocommit)
        if self.pgq_autocommit and self.pgq_lazy_fetch:
            raise skytools.UsageError("pgq_autocommit is not compatible with pgq_lazy_fetch")
        self.set_database_defaults(self.db_name, autocommit = self.pgq_autocommit)

        self.idle_start = time.time()

    def reload(self):
        skytools.DBScript.reload(self)

        self.pgq_lazy_fetch = self.cf.getint("pgq_lazy_fetch", self.default_lazy_fetch)

        # set following ones to None if not set
        self.pgq_min_count = self.cf.getint("pgq_batch_collect_events", 0) or None
        self.pgq_min_interval = self.cf.get("pgq_batch_collect_interval", '') or None
        self.pgq_min_lag = self.cf.get("pgq_keep_lag", '') or None

        # filter out specific tables only
        tfilt = []
        for t in self.cf.getlist('table_filter', ''):
            tfilt.append(skytools.quote_literal(skytools.fq_name(t)))
        if len(tfilt) > 0:
            expr = "ev_extra1 in (%s)" % ','.join(tfilt)
            self.consumer_filter = expr

        self.keepalive_stats = self.cf.getint("keepalive_stats", 300)

    def startup(self):
        """Handle commands here.  __init__ does not have error logging."""
        if self.options.register:
            self.register_consumer()
            sys.exit(0)
        if self.options.unregister:
            self.unregister_consumer()
            sys.exit(0)
        return skytools.DBScript.startup(self)

    def init_optparse(self, parser = None):
        p = skytools.DBScript.init_optparse(self, parser)
        p.add_option('--register', action='store_true',
                     help = 'register consumer on queue')
        p.add_option('--unregister', action='store_true',
                     help = 'unregister consumer from queue')
        return p

    def process_event(self, db, event):
        """Process one event.

        Should be overridden by user code.
        """
        raise Exception("needs to be implemented")

    def process_batch(self, db, batch_id, event_list):
        """Process all events in batch.

        By default calls process_event for each.
        Can be overridden by user code.
        """
        for ev in event_list:
            self.process_event(db, ev)

    def work(self):
        """Do the work loop, once (internal).
        Returns: true if wants to be called again,
        false if script can sleep.
        """

        db = self.get_database(self.db_name)
        curs = db.cursor()

        self.stat_start()

        # acquire batch
        batch_id = self._load_next_batch(curs)
        db.commit()
        if batch_id == None:
            return 0

        # load events
        ev_list = self._load_batch_events(curs, batch_id)
        db.commit()

        # process events
        self._launch_process_batch(db, batch_id, ev_list)

        # done
        self._finish_batch(curs, batch_id, ev_list)
        db.commit()
        self.stat_end(len(ev_list))

        return 1

    def register_consumer(self):
        self.log.info("Registering consumer on source queue")
        db = self.get_database(self.db_name)
        cx = db.cursor()
        cx.execute("select pgq.register_consumer(%s, %s)",
                [self.queue_name, self.consumer_name])
        res = cx.fetchone()[0]
        db.commit()

        return res

    def unregister_consumer(self):
        self.log.info("Unregistering consumer from source queue")
        db = self.get_database(self.db_name)
        cx = db.cursor()
        cx.execute("select pgq.unregister_consumer(%s, %s)",
                [self.queue_name, self.consumer_name])
        db.commit()

    def _launch_process_batch(self, db, batch_id, list):
        self.process_batch(db, batch_id, list)

    def _make_event(self, queue_name, row):
        return Event(queue_name, row)

    def _load_batch_events_old(self, curs, batch_id):
        """Fetch all events for this batch."""

        # load events
        sql = "select * from pgq.get_batch_events(%d)" % batch_id
        if self.consumer_filter is not None:
            sql += " where %s" % self.consumer_filter
        curs.execute(sql)
        rows = curs.fetchall()

        # map them to python objects
        ev_list = []
        for r in rows:
            ev = self._make_event(self.queue_name, r)
            ev_list.append(ev)

        return ev_list

    def _load_batch_events(self, curs, batch_id):
        """Fetch all events for this batch."""

        if self.pgq_lazy_fetch:
            return self._batch_walker_class(curs, batch_id, self.queue_name, self.pgq_lazy_fetch, self.consumer_filter)
        else:
            return self._load_batch_events_old(curs, batch_id)

    def _load_next_batch(self, curs):
        """Allocate next batch. (internal)"""

        q = """select * from pgq.next_batch_custom(%s, %s, %s, %s, %s)"""
        curs.execute(q, [self.queue_name, self.consumer_name,
                         self.pgq_min_lag, self.pgq_min_count, self.pgq_min_interval])
        inf = curs.fetchone().copy()
        inf['tick_id'] = inf['cur_tick_id']
        inf['batch_end'] = inf['cur_tick_time']
        inf['batch_start'] = inf['prev_tick_time']
        inf['seq_start'] = inf['prev_tick_event_seq']
        inf['seq_end'] = inf['cur_tick_event_seq']
        self.batch_info = inf
        return self.batch_info['batch_id']

    def _finish_batch(self, curs, batch_id, list):
        """Tag events and notify that the batch is done."""

        curs.execute("select pgq.finish_batch(%s)", [batch_id])

    def stat_start(self):
        t = time.time()
        self.stat_batch_start = t
        if self.stat_batch_start - self.idle_start > self.keepalive_stats:
            self.stat_put('idle', round(self.stat_batch_start - self.idle_start,4))
            self.idle_start = t

    def stat_end(self, count):
        t = time.time()
        self.stat_put('count', count)
        self.stat_put('duration', round(t - self.stat_batch_start,4))
        if count > 0: # reset timer if we got some events
            self.stat_put('idle', round(self.stat_batch_start - self.idle_start,4))
            self.idle_start = t

########NEW FILE########
__FILENAME__ = admin
#! /usr/bin/env python

## NB: not all commands work ##

"""Cascaded queue administration.

londiste.py INI pause [NODE [CONS]]

setadm.py INI pause NODE [CONS]

"""

import optparse
import os.path
import Queue
import sys
import threading
import time

import skytools
from skytools import UsageError, DBError
from pgq.cascade.nodeinfo import *

__all__ = ['CascadeAdmin']

RESURRECT_DUMP_FILE = "resurrect-lost-events.json"

command_usage = """\
%prog [options] INI CMD [subcmd args]

Node Initialization:
  create-root   NAME [PUBLIC_CONNSTR]
  create-branch NAME [PUBLIC_CONNSTR] --provider=<public_connstr>
  create-leaf   NAME [PUBLIC_CONNSTR] --provider=<public_connstr>
    All of the above initialize a node

Node Administration:
  pause                 Pause node worker
  resume                Resume node worker
  wait-root             Wait until node has caught up with root
  wait-provider         Wait until node has caught up with provider
  status                Show cascade state
  node-status           Show status of local node
  members               Show members in set

Cascade layout change:
  change-provider --provider NEW_NODE
    Change where worker reads from

  takeover FROM_NODE [--all] [--dead]
    Take other node position

  drop-node NAME
    Remove node from cascade

  tag-dead NODE ..
    Tag node as dead

  tag-alive NODE ..
    Tag node as alive
"""

standalone_usage = """
setadm extra switches:

  pause/resume/change-provider:
    --node=NODE_NAME | --consumer=CONSUMER_NAME

  create-root/create-branch/create-leaf:
    --worker=WORKER_NAME
"""


class CascadeAdmin(skytools.AdminScript):
    """Cascaded PgQ administration."""
    queue_name = None
    queue_info = None
    extra_objs = []
    local_node = None
    root_node_name = None

    commands_without_pidfile = ['status', 'node-status', 'node-info']

    def __init__(self, svc_name, dbname, args, worker_setup = False):
        skytools.AdminScript.__init__(self, svc_name, args)
        self.initial_db_name = dbname
        if worker_setup:
            self.options.worker = self.job_name
            self.options.consumer = self.job_name

    def init_optparse(self, parser = None):
        """Add SetAdmin switches to parser."""
        p = skytools.AdminScript.init_optparse(self, parser)

        usage = command_usage + standalone_usage
        p.set_usage(usage.strip())

        g = optparse.OptionGroup(p, "actual queue admin options")
        g.add_option("--connstr", action="store_true",
                     help = "initial connect string")
        g.add_option("--provider",
                     help = "init: connect string for provider")
        g.add_option("--queue",
                     help = "specify queue name")
        g.add_option("--worker",
                     help = "create: specify worker name")
        g.add_option("--node",
                     help = "specify node name")
        g.add_option("--consumer",
                     help = "specify consumer name")
        g.add_option("--target",
                    help = "takeover: specify node to take over")
        g.add_option("--merge",
                    help = "create-node: combined queue name")
        g.add_option("--dead", action="append",
                    help = "tag some node as dead")
        g.add_option("--dead-root", action="store_true",
                    help = "tag some node as dead")
        g.add_option("--dead-branch", action="store_true",
                    help = "tag some node as dead")
        g.add_option("--sync-watermark",
                    help = "list of node names to sync with")
        p.add_option_group(g)
        return p

    def reload(self):
        """Reload config."""
        skytools.AdminScript.reload(self)
        if self.options.queue:
            self.queue_name = self.options.queue
        else:
            self.queue_name = self.cf.get('queue_name', '')
            if not self.queue_name:
                self.queue_name = self.cf.get('pgq_queue_name', '')
                if not self.queue_name:
                    raise Exception('"queue_name" not specified in config')

    #
    # Node initialization.
    #

    def cmd_install(self):
        db = self.get_database(self.initial_db_name)
        self.install_code(db)

    def cmd_create_root(self, *args):
        return self.create_node('root', args)

    def cmd_create_branch(self, *args):
        return self.create_node('branch', args)

    def cmd_create_leaf(self, *args):
        return self.create_node('leaf', args)

    def create_node(self, node_type, args):
        """Generic node init."""

        if node_type not in ('root', 'branch', 'leaf'):
            raise Exception('unknown node type')

        # load node name
        if len(args) > 0:
            node_name = args[0]
        else:
            node_name = self.cf.get('node_name', '')
        if not node_name:
            raise UsageError('Node name must be given either in command line or config')

        # load node public location
        if len(args) > 1:
            node_location = args[1]
        else:
            node_location = self.cf.get('public_node_location', '')
        if not node_location:
            raise UsageError('Node public location must be given either in command line or config')

        if len(args) > 2:
            raise UsageError('Too many args, only node name and public connect string allowed')

        # load provider
        provider_loc = self.options.provider
        if not provider_loc:
            provider_loc = self.cf.get('initial_provider_location', '')

        # check if sane
        ok = 0
        for k, v in skytools.parse_connect_string(node_location):
            if k in ('host', 'service'):
                ok = 1
                break
        if not ok:
            self.log.warning('No host= in public connect string, bad idea')

        # connect to database
        db = self.get_database(self.initial_db_name)

        # check if code is installed
        self.install_code(db)

        # query current status
        res = self.exec_query(db, "select * from pgq_node.get_node_info(%s)", [self.queue_name])
        info = res[0]
        if info['node_type'] is not None:
            self.log.info("Node is already initialized as %s", info['node_type'])
            return

        # check if public connstr is sane
        self.check_public_connstr(db, node_location)

        self.log.info("Initializing node")
        node_attrs = {}

        worker_name = self.options.worker
        if not worker_name:
            raise Exception('--worker required')
        combined_queue = self.options.merge
        if combined_queue and node_type != 'leaf':
            raise Exception('--merge can be used only for leafs')

        if self.options.sync_watermark:
            if node_type != 'branch':
                raise UsageError('--sync-watermark can be used only for branch nodes')
            node_attrs['sync_watermark'] = self.options.sync_watermark

        # register member
        if node_type == 'root':
            global_watermark = None
            combined_queue = None
            provider_name = None
            self.exec_cmd(db, "select * from pgq_node.register_location(%s, %s, %s, false)",
                          [self.queue_name, node_name, node_location])
            self.exec_cmd(db, "select * from pgq_node.create_node(%s, %s, %s, %s, %s, %s, %s)",
                          [self.queue_name, node_type, node_name, worker_name, provider_name, global_watermark, combined_queue])
            provider_db = None
        else:
            if not provider_loc:
                raise Exception('Please specify --provider')

            root_db = self.find_root_db(provider_loc)
            queue_info = self.load_queue_info(root_db)

            # check if member already exists
            if queue_info.get_member(node_name) is not None:
                self.log.error("Node '%s' already exists", node_name)
                sys.exit(1)

            combined_set = None

            provider_db = self.get_database('provider_db', connstr = provider_loc, profile = 'remote')
            q = "select node_type, node_name from pgq_node.get_node_info(%s)"
            res = self.exec_query(provider_db, q, [self.queue_name])
            row = res[0]
            if not row['node_name']:
                raise Exception("provider node not found")
            provider_name = row['node_name']

            # register member on root
            self.exec_cmd(root_db, "select * from pgq_node.register_location(%s, %s, %s, false)",
                          [self.queue_name, node_name, node_location])

            # lookup provider
            provider = queue_info.get_member(provider_name)
            if not provider:
                self.log.error("Node %s does not exist", provider_name)
                sys.exit(1)

            # register on provider
            self.exec_cmd(provider_db, "select * from pgq_node.register_location(%s, %s, %s, false)",
                          [self.queue_name, node_name, node_location])
            rows = self.exec_cmd(provider_db, "select * from pgq_node.register_subscriber(%s, %s, %s, null)",
                                 [self.queue_name, node_name, worker_name])
            global_watermark = rows[0]['global_watermark']

            # initialize node itself

            # insert members
            self.exec_cmd(db, "select * from pgq_node.register_location(%s, %s, %s, false)",
                          [self.queue_name, node_name, node_location])
            for m in queue_info.member_map.values():
                self.exec_cmd(db, "select * from pgq_node.register_location(%s, %s, %s, %s)",
                              [self.queue_name, m.name, m.location, m.dead])

            # real init
            self.exec_cmd(db, "select * from pgq_node.create_node(%s, %s, %s, %s, %s, %s, %s)",
                          [ self.queue_name, node_type, node_name, worker_name,
                            provider_name, global_watermark, combined_queue ])

        self.extra_init(node_type, db, provider_db)

        if node_attrs:
            s_attrs = skytools.db_urlencode(node_attrs)
            self.exec_cmd(db, "select * from pgq_node.set_node_attrs(%s, %s)",
                          [self.queue_name, s_attrs])

        self.log.info("Done")

    def check_public_connstr(self, db, pub_connstr):
        """Look if public and local connect strings point to same db's.
        """
        pub_db = self.get_database("pub_db", connstr = pub_connstr, profile = 'remote')
        curs1 = db.cursor()
        curs2 = pub_db.cursor()
        q = "select oid, datname, txid_current() as txid, txid_current_snapshot() as snap"\
            " from pg_catalog.pg_database where datname = current_database()"
        curs1.execute(q)
        res1 = curs1.fetchone()
        db.commit()

        curs2.execute(q)
        res2 = curs2.fetchone()
        pub_db.commit()

        curs1.execute(q)
        res3 = curs1.fetchone()
        db.commit()

        self.close_database("pub_db")

        failure = 0
        if (res1['oid'], res1['datname']) != (res2['oid'], res2['datname']):
            failure += 1

        sn1 = skytools.Snapshot(res1['snap'])
        tx = res2['txid']
        sn2 = skytools.Snapshot(res3['snap'])
        if sn1.contains(tx):
            failure += 2
        elif not sn2.contains(tx):
            failure += 4

        if failure:
            raise UsageError("Public connect string points to different database than local connect string (fail=%d)" % failure)

    def extra_init(self, node_type, node_db, provider_db):
        """Callback to do specific init."""
        pass

    def find_root_db(self, initial_loc = None):
        """Find root node, having start point."""
        if initial_loc:
            loc = initial_loc
            db = self.get_database('root_db', connstr = loc, profile = 'remote')
        else:
            loc = self.cf.get(self.initial_db_name)
            db = self.get_database('root_db', connstr = loc)

        while 1:
            # query current status
            res = self.exec_query(db, "select * from pgq_node.get_node_info(%s)", [self.queue_name])
            info = res[0]
            node_type = info['node_type']
            if node_type is None:
                self.log.info("Root node not initialized?")
                sys.exit(1)

            self.log.debug("db='%s' -- type='%s' provider='%s'", loc, node_type, info['provider_location'])
            # configured db may not be root anymore, walk upwards then
            if node_type in ('root', 'combined-root'):
                db.commit()
                self.root_node_name = info['node_name']
                return db

            self.close_database('root_db')
            if loc == info['provider_location']:
                raise Exception("find_root_db: got loop: %s" % loc)
            loc = info['provider_location']
            if loc is None:
                self.log.error("Sub node provider not initialized?")
                sys.exit(1)

            db = self.get_database('root_db', connstr = loc, profile = 'remote')

        raise Exception('process canceled')

    def find_root_node(self):
        self.find_root_db()
        return self.root_node_name

    def find_consumer_check(self, node, consumer):
        cmap = self.get_node_consumer_map(node)
        return (consumer in cmap)

    def find_consumer(self, node = None, consumer = None):
        if not node and not consumer:
            node = self.options.node
            consumer = self.options.consumer
        if not node and not consumer:
            raise Exception('Need either --node or --consumer')

        # specific node given
        if node:
            if consumer:
                if not self.find_consumer_check(node, consumer):
                    raise Exception('Consumer not found')
            else:
                state = self.get_node_info(node)
                consumer = state.worker_name
            return (node, consumer)

        # global consumer search
        if self.find_consumer_check(self.local_node, consumer):
            return (self.local_node, consumer)

        # fixme: dead node handling?
        nodelist = self.queue_info.member_map.keys()
        for node in nodelist:
            if node == self.local_node:
                continue
            if self.find_consumer_check(node, consumer):
                return (node, consumer)

        raise Exception('Consumer not found')

    def install_code(self, db):
        """Install cascading code to db."""
        objs = [
            skytools.DBLanguage("plpgsql"),
            #skytools.DBFunction("txid_current_snapshot", 0, sql_file="txid.sql"),
            skytools.DBSchema("pgq", sql_file="pgq.sql"),
            skytools.DBFunction("pgq.get_batch_cursor", 3, sql_file = "pgq.upgrade.2to3.sql"),
            skytools.DBSchema("pgq_ext", sql_file="pgq_ext.sql"), # not needed actually
            skytools.DBSchema("pgq_node", sql_file="pgq_node.sql"),
        ]
        objs += self.extra_objs
        skytools.db_install(db.cursor(), objs, self.log)
        db.commit()

    #
    # Print status of whole set.
    #

    def cmd_status(self):
        """Show set status."""
        self.load_local_info()

        # prepare data for workers
        members = Queue.Queue()
        for m in self.queue_info.member_map.itervalues():
            cstr = self.add_connect_string_profile(m.location, 'remote')
            members.put( (m.name, cstr) )
        nodes = Queue.Queue()

        # launch workers and wait
        num_nodes = len(self.queue_info.member_map)
        num_threads = max (min (num_nodes / 4, 100), 1)
        tlist = []
        for i in range(num_threads):
            t = threading.Thread (target = self._cmd_status_worker, args = (members, nodes))
            t.daemon = True
            t.start()
            tlist.append(t)
        #members.join()
        for t in tlist:
            t.join()

        while True:
            try:
                node = nodes.get_nowait()
            except Queue.Empty:
                break
            self.queue_info.add_node(node)

        self.queue_info.print_tree()

    def _cmd_status_worker (self, members, nodes):
        # members in, nodes out, both thread-safe
        while True:
            try:
                node_name, node_connstr = members.get_nowait()
            except Queue.Empty:
                break
            node = self.load_node_status (node_name, node_connstr)
            nodes.put(node)
            members.task_done()

    def load_node_status (self, name, location):
        """ Load node info & status """
        # must be thread-safe (!)
        if not self.node_alive(name):
            node = NodeInfo(self.queue_name, None, node_name = name)
            return node
        try:
            db = None
            db = skytools.connect_database (location)
            db.set_isolation_level (skytools.I_AUTOCOMMIT)
            curs = db.cursor()
            curs.execute("select * from pgq_node.get_node_info(%s)", [self.queue_name])
            node = NodeInfo(self.queue_name, curs.fetchone())
            node.load_status(curs)
            self.load_extra_status(curs, node)
        except DBError, d:
            msg = str(d).strip().split('\n', 1)[0].strip()
            print('Node %r failure: %s' % (name, msg))
            node = NodeInfo(self.queue_name, None, node_name = name)
        finally:
            if db: db.close()
        return node

    def cmd_node_status(self):
        """
        Show status of a local node.
        """

        self.load_local_info()
        db = self.get_node_database(self.local_node)
        curs = db.cursor()
        node = self.queue_info.local_node
        node.load_status(curs)
        self.load_extra_status(curs, node)

        subscriber_nodes = self.get_node_subscriber_list(self.local_node)

        offset=4*' '
        print node.get_title()
        print offset+'Provider: %s' % node.provider_node
        print offset+'Subscribers: %s' % ', '.join(subscriber_nodes)
        for l in node.get_infolines():
            print offset+l

    def load_extra_status(self, curs, node):
        """Fetch extra info."""
        # must be thread-safe (!)
        pass

    #
    # Normal commands.
    #

    def cmd_change_provider(self):
        """Change node provider."""

        self.load_local_info()
        self.change_provider(
                node = self.options.node,
                consumer = self.options.consumer,
                new_provider = self.options.provider)

    def node_change_provider(self, node, new_provider):
        self.change_provider(node, new_provider = new_provider)

    def change_provider(self, node = None, consumer = None, new_provider = None):
        old_provider = None
        if not new_provider:
            raise Exception('Please give --provider')

        if not node or not consumer:
            node, consumer = self.find_consumer(node = node, consumer = consumer)

        if node == new_provider:
            raise UsageError ("cannot subscribe to itself")

        cmap = self.get_node_consumer_map(node)
        cinfo = cmap[consumer]
        old_provider = cinfo['provider_node']

        if old_provider == new_provider:
            self.log.info("Consumer '%s' at node '%s' has already '%s' as provider",
                          consumer, node, new_provider)
            return

        # pause target node
        self.pause_consumer(node, consumer)

        # reload node info
        node_db = self.get_node_database(node)
        qinfo = self.load_queue_info(node_db)
        ninfo = qinfo.local_node
        node_location = qinfo.get_member(node).location

        # reload consumer info
        cmap = self.get_node_consumer_map(node)
        cinfo = cmap[consumer]

        # is it node worker or plain consumer?
        is_worker = (ninfo.worker_name == consumer)

        # fixme: expect the node to be described already
        q = "select * from pgq_node.register_location(%s, %s, %s, false)"
        self.node_cmd(new_provider, q, [self.queue_name, node, node_location])

        # subscribe on new provider
        if is_worker:
            q = 'select * from pgq_node.register_subscriber(%s, %s, %s, %s)'
            self.node_cmd(new_provider, q, [self.queue_name, node, consumer, cinfo['last_tick_id']])
        else:
            q = 'select * from pgq.register_consumer_at(%s, %s, %s)'
            self.node_cmd(new_provider, q, [self.queue_name, consumer, cinfo['last_tick_id']])

        # change provider on target node
        q = 'select * from pgq_node.change_consumer_provider(%s, %s, %s)'
        self.node_cmd(node, q, [self.queue_name, consumer, new_provider])

        # done
        self.resume_consumer(node, consumer)

        # unsubscribe from old provider
        try:
            if is_worker:
                q = "select * from pgq_node.unregister_subscriber(%s, %s)"
                self.node_cmd(old_provider, q, [self.queue_name, node])
            else:
                q = "select * from pgq.unregister_consumer(%s, %s)"
                self.node_cmd(old_provider, q, [self.queue_name, consumer])
        except skytools.DBError, d:
            self.log.warning("failed to unregister from old provider (%s): %s", old_provider, str(d))

    def cmd_rename_node(self, old_name, new_name):
        """Rename node."""

        self.load_local_info()

        root_db = self.find_root_db()

        # pause target node
        self.pause_node(old_name)
        node = self.load_node_info(old_name)
        provider_node = node.provider_node
        subscriber_list = self.get_node_subscriber_list(old_name)

        # create copy of member info / subscriber+queue info
        step1 = 'select * from pgq_node.rename_node_step1(%s, %s, %s)'
        # rename node itself, drop copies
        step2 = 'select * from pgq_node.rename_node_step2(%s, %s, %s)'

        # step1
        self.exec_cmd(root_db, step1, [self.queue_name, old_name, new_name])
        self.node_cmd(provider_node, step1, [self.queue_name, old_name, new_name])
        self.node_cmd(old_name, step1, [self.queue_name, old_name, new_name])
        for child in subscriber_list:
            self.node_cmd(child, step1, [self.queue_name, old_name, new_name])

        # step1
        self.node_cmd(old_name, step2, [self.queue_name, old_name, new_name])
        self.node_cmd(provider_node, step1, [self.queue_name, old_name, new_name])
        for child in subscriber_list:
            self.node_cmd(child, step2, [self.queue_name, old_name, new_name])
        self.exec_cmd(root_db, step2, [self.queue_name, old_name, new_name])

        # resume node
        self.resume_node(old_name)

    def cmd_drop_node(self, node_name):
        """Drop a node."""

        self.load_local_info()

        try:
            node = self.load_node_info(node_name)
            if node:
                # see if we can safely drop
                subscriber_list = self.get_node_subscriber_list(node_name)
                if subscriber_list:
                    raise UsageError('node still has subscribers')
        except skytools.DBError:
            pass

        try:
            # unregister node location from root node (event will be added to queue)
            root_db = self.find_root_db()
            q = "select * from pgq_node.unregister_location(%s, %s)"
            self.exec_cmd(root_db, q, [self.queue_name, node_name])
        except skytools.DBError, d:
            self.log.warning("Unregister from root failed: %s", str(d))

        try:
            # drop node info
            db = self.get_node_database(node_name)
            q = "select * from pgq_node.drop_node(%s, %s)"
            self.exec_cmd(db, q, [self.queue_name, node_name])
        except skytools.DBError, d:
            self.log.warning("Local drop failure: %s", str(d))

        # brute force removal
        for n in self.queue_info.member_map.values():
            try:
                q = "select * from pgq_node.drop_node(%s, %s)"
                self.node_cmd(n.name, q, [self.queue_name, node_name])
            except skytools.DBError, d:
                self.log.warning("Failed to remove from '%s': %s", n.name, str(d))

    def node_depends(self, sub_node, top_node):
        cur_node = sub_node
        # walk upstream
        while 1:
            info = self.get_node_info(cur_node)
            if cur_node == top_node:
                # yes, top_node is sub_node's provider
                return True
            if info.type == 'root':
                # found root, no dependancy
                return False
            # step upwards
            cur_node = info.provider_node

    def demote_node(self, oldnode, step, newnode):
        """Downgrade old root?"""
        q = "select * from pgq_node.demote_root(%s, %s, %s)"
        res = self.node_cmd(oldnode, q, [self.queue_name, step, newnode])
        if res:
            return res[0]['last_tick']

    def promote_branch(self, node):
        """Promote old branch as root."""
        q = "select * from pgq_node.promote_branch(%s)"
        self.node_cmd(node, q, [self.queue_name])

    def wait_for_catchup(self, new, last_tick):
        """Wait until new_node catches up to old_node."""
        # wait for it on subscriber
        info = self.load_node_info(new)
        if info.completed_tick >= last_tick:
            self.log.info('tick already exists')
            return info
        if info.paused:
            self.log.info('new node seems paused, resuming')
            self.resume_node(new)
        while 1:
            self.log.debug('waiting for catchup: need=%d, cur=%d', last_tick, info.completed_tick)
            time.sleep(1)
            info = self.load_node_info(new)
            if info.completed_tick >= last_tick:
                return info

    def takeover_root(self, old_node_name, new_node_name, failover = False):
        """Root switchover."""

        new_info = self.get_node_info(new_node_name)
        old_info = None

        if self.node_alive(old_node_name):
            # old root works, switch properly
            old_info = self.get_node_info(old_node_name)
            self.pause_node(old_node_name)
            self.demote_node(old_node_name, 1, new_node_name)
            last_tick = self.demote_node(old_node_name, 2, new_node_name)
            self.wait_for_catchup(new_node_name, last_tick)
        else:
            # find latest tick on local node
            q = "select * from pgq.get_queue_info(%s)"
            db = self.get_node_database(new_node_name)
            curs = db.cursor()
            curs.execute(q, [self.queue_name])
            row = curs.fetchone()
            last_tick = row['last_tick_id']
            db.commit()

            # find if any other node has more ticks
            other_node = None
            other_tick = last_tick
            sublist = self.find_subscribers_for(old_node_name)
            for n in sublist:
                q = "select * from pgq_node.get_node_info(%s)"
                rows = self.node_cmd(n, q, [self.queue_name])
                info = rows[0]
                if info['worker_last_tick'] > other_tick:
                    other_tick = info['worker_last_tick']
                    other_node = n

            # if yes, load batches from there
            if other_node:
                self.change_provider(new_node_name, new_provider = other_node)
                self.wait_for_catchup(new_node_name, other_tick)
                last_tick = other_tick

        # promote new root
        self.pause_node(new_node_name)
        self.promote_branch(new_node_name)

        # register old root on new root as subscriber
        if self.node_alive(old_node_name):
            old_worker_name = old_info.worker_name
        else:
            old_worker_name = self.failover_consumer_name(old_node_name)
        q = 'select * from pgq_node.register_subscriber(%s, %s, %s, %s)'
        self.node_cmd(new_node_name, q, [self.queue_name, old_node_name, old_worker_name, last_tick])

        # unregister new root from old root
        q = "select * from pgq_node.unregister_subscriber(%s, %s)"
        self.node_cmd(new_info.provider_node, q, [self.queue_name, new_node_name])

        # launch new node
        self.resume_node(new_node_name)

        # demote & launch old node
        if self.node_alive(old_node_name):
            self.demote_node(old_node_name, 3, new_node_name)
            self.resume_node(old_node_name)

    def takeover_nonroot(self, old_node_name, new_node_name, failover):
        """Non-root switchover."""
        if self.node_depends(new_node_name, old_node_name):
            # yes, old_node is new_nodes provider,
            # switch it around
            pnode = self.find_provider(old_node_name)
            self.node_change_provider(new_node_name, pnode)

        self.node_change_provider(old_node_name, new_node_name)

    def cmd_takeover(self, old_node_name):
        """Generic node switchover."""
        self.log.info("old: %s", old_node_name)
        self.load_local_info()
        new_node_name = self.options.node
        if not new_node_name:
            worker = self.options.consumer
            if not worker:
                raise UsageError('old node not given')
            if self.queue_info.local_node.worker_name != worker:
                raise UsageError('old node not given')
            new_node_name = self.local_node
        if not old_node_name:
            raise UsageError('old node not given')

        if old_node_name not in self.queue_info.member_map:
            raise UsageError('Unknown node: %s' % old_node_name)

        if self.options.dead_root:
            otype = 'root'
            failover = True
        elif self.options.dead_branch:
            otype = 'branch'
            failover = True
        else:
            onode = self.get_node_info(old_node_name)
            otype = onode.type
            failover = False

        if failover:
            self.cmd_tag_dead(old_node_name)

        new_node = self.get_node_info(new_node_name)
        if old_node_name == new_node.name:
            self.log.info("same node?")
            return

        if otype == 'root':
            self.takeover_root(old_node_name, new_node_name, failover)
        else:
            self.takeover_nonroot(old_node_name, new_node_name, failover)

        # switch subscribers around
        if self.options.all or failover:
            for n in self.find_subscribers_for(old_node_name):
                self.node_change_provider(n, new_node_name)

    def find_provider(self, node_name):
        if self.node_alive(node_name):
            info = self.get_node_info(node_name)
            return info.provider_node
        nodelist = self.queue_info.member_map.keys()
        for n in nodelist:
            if n == node_name:
                continue
            if not self.node_alive(n):
                continue
            if node_name in self.get_node_subscriber_list(n):
                return n
        return self.find_root_node()

    def find_subscribers_for(self, parent_node_name):
        """Find subscribers for particular node node."""

        # use dict to eliminate duplicates
        res = {}

        nodelist = self.queue_info.member_map.keys()
        for node_name in nodelist:
            if node_name == parent_node_name:
                continue
            if not self.node_alive(node_name):
                continue
            n = self.get_node_info(node_name)
            if not n:
                continue
            if n.provider_node == parent_node_name:
                res[n.name] = 1
        return res.keys()

    def cmd_tag_dead(self, dead_node_name):
        self.load_local_info()

        # tag node dead in memory
        self.log.info("Tagging node '%s' as dead", dead_node_name)
        self.queue_info.tag_dead(dead_node_name)

        # tag node dead in local node
        q = "select * from pgq_node.register_location(%s, %s, null, true)"
        self.node_cmd(self.local_node, q, [self.queue_name, dead_node_name])

        # tag node dead in other nodes
        nodelist = self.queue_info.member_map.keys()
        for node_name in nodelist:
            if not self.node_alive(node_name):
                continue
            if node_name == dead_node_name:
                continue
            if node_name == self.local_node:
                continue
            try:
                q = "select * from pgq_node.register_location(%s, %s, null, true)"
                self.node_cmd(node_name, q, [self.queue_name, dead_node_name])
            except DBError, d:
                msg = str(d).strip().split('\n', 1)[0]
                print('Node %s failure: %s' % (node_name, msg))
                self.close_node_database(node_name)

    def cmd_pause(self):
        """Pause a node"""
        self.load_local_info()
        node, consumer = self.find_consumer()
        self.pause_consumer(node, consumer)

    def cmd_resume(self):
        """Resume a node from pause."""
        self.load_local_info()
        node, consumer = self.find_consumer()
        self.resume_consumer(node, consumer)

    def cmd_members(self):
        """Show member list."""
        self.load_local_info()
        db = self.get_database(self.initial_db_name)
        desc = 'Member info on %s@%s:' % (self.local_node, self.queue_name)
        q = "select node_name, dead, node_location"\
            " from pgq_node.get_queue_locations(%s) order by 1"
        self.display_table(db, desc, q, [self.queue_name])

    def cmd_node_info(self):
        self.load_local_info()

        q = self.queue_info
        n = q.local_node
        m = q.get_member(n.name)

        stlist = []
        if m.dead:
            stlist.append('DEAD')
        if n.paused:
            stlist.append("PAUSED")
        if not n.uptodate:
            stlist.append("NON-UP-TO-DATE")
        st = ', '.join(stlist)
        if not st:
            st = 'OK'
        print('Node: %s  Type: %s  Queue: %s' % (n.name, n.type, q.queue_name))
        print('Status: %s' % st)
        if n.type != 'root':
            print('Provider: %s' % n.provider_node)
        else:
            print('Provider: --')
        print('Connect strings:')
        print('  Local   : %s' % self.cf.get('db'))
        print('  Public  : %s' % m.location)
        if n.type != 'root':
            print('  Provider: %s' % n.provider_location)
        if n.combined_queue:
            print('Combined Queue: %s  (node type: %s)' % (n.combined_queue, n.combined_type))

    def cmd_wait_root(self):
        """Wait for next tick from root."""

        self.load_local_info()

        if self.queue_info.local_node.type == 'root':
            self.log.info("Current node is root, no need to wait")
            return

        self.log.info("Finding root node")
        root_node = self.find_root_node()
        self.log.info("Root is %s", root_node)

        dst_db = self.get_database(self.initial_db_name)
        self.wait_for_node(dst_db, root_node)

    def cmd_wait_provider(self):
        """Wait for next tick from provider."""

        self.load_local_info()

        if self.queue_info.local_node.type == 'root':
            self.log.info("Current node is root, no need to wait")
            return

        dst_db = self.get_database(self.initial_db_name)
        node = self.queue_info.local_node.provider_node
        self.log.info("Provider is %s", node)
        self.wait_for_node(dst_db, node)

    def wait_for_node(self, dst_db, node_name):
        """Core logic for waiting."""

        self.log.info("Fetching last tick for %s", node_name)
        node_info = self.load_node_info(node_name)
        tick_id = node_info.last_tick

        self.log.info("Waiting for tick > %d", tick_id)

        q = "select * from pgq_node.get_node_info(%s)"
        dst_curs = dst_db.cursor()

        while 1:
            dst_curs.execute(q, [self.queue_name])
            row = dst_curs.fetchone()
            dst_db.commit()

            if row['ret_code'] >= 300:
                self.log.warning("Problem: %s", row['ret_code'], row['ret_note'])
                return

            if row['worker_last_tick'] > tick_id:
                self.log.info("Got tick %d, exiting", row['worker_last_tick'])
                break

            self.sleep(2)

    def cmd_resurrect(self):
        """Convert out-of-sync old root to branch and sync queue contents.
        """
        self.load_local_info()

        db = self.get_database(self.initial_db_name)
        curs = db.cursor()

        # stop if leaf
        if self.queue_info.local_node.type == 'leaf':
            self.log.info("Current node is leaf, nothing to do")
            return

        # stop if dump file exists
        if os.path.lexists(RESURRECT_DUMP_FILE):
            self.log.error("Dump file exists, cannot perform resurrection: %s", RESURRECT_DUMP_FILE)
            sys.exit(1)

        #
        # Find failover position
        #

        self.log.info("** Searching for gravestone **")

        # load subscribers
        sub_list = []
        q = "select * from pgq_node.get_subscriber_info(%s)"
        curs.execute(q, [self.queue_name])
        for row in curs.fetchall():
            sub_list.append(row['node_name'])
        db.commit()

        # find backup subscription
        this_node = self.queue_info.local_node.name
        failover_cons = self.failover_consumer_name(this_node)
        full_list = self.queue_info.member_map.keys()
        done_nodes = { this_node: 1 }
        prov_node = None
        root_node = None
        for node_name in sub_list + full_list:
            if node_name in done_nodes:
                continue
            done_nodes[node_name] = 1
            if not self.node_alive(node_name):
                self.log.info('Node %s is dead, skipping', node_name)
                continue
            self.log.info('Looking on node %s', node_name)
            node_db = None
            try:
                node_db = self.get_node_database(node_name)
                node_curs = node_db.cursor()
                node_curs.execute("select * from pgq.get_consumer_info(%s, %s)", [self.queue_name, failover_cons])
                cons_rows = node_curs.fetchall()
                node_curs.execute("select * from pgq_node.get_node_info(%s)", [self.queue_name])
                node_info = node_curs.fetchone()
                node_db.commit()
                if len(cons_rows) == 1:
                    if prov_node:
                        raise Exception('Unexpected situation: there are two gravestones - on nodes %s and %s' % (prov_node, node_name))
                    prov_node = node_name
                    failover_tick = cons_rows[0]['last_tick']
                    self.log.info("Found gravestone on node: %s", node_name)
                if node_info['node_type'] == 'root':
                    self.log.info("Found new root node: %s", node_name)
                    root_node = node_name
                self.close_node_database(node_name)
                node_db = None
                if root_node and prov_node:
                    break
            except skytools.DBError:
                self.log.warning("failed to check node %s", node_name)
                if node_db:
                    self.close_node_database(node_name)
                    node_db = None

        if not root_node:
            self.log.error("Cannot find new root node", failover_cons)
            sys.exit(1)
        if not prov_node:
            self.log.error("Cannot find failover position (%s)", failover_cons)
            sys.exit(1)

        # load worker state
        q = "select * from pgq_node.get_worker_state(%s)"
        rows = self.exec_cmd(db, q, [self.queue_name])
        state = rows[0]

        # demote & pause
        self.log.info("** Demote & pause local node **")
        if self.queue_info.local_node.type == 'root':
            self.log.info('Node %s is root, demoting', this_node)
            q = "select * from pgq_node.demote_root(%s, %s, %s)"
            self.exec_cmd(db, q, [self.queue_name, 1, prov_node])
            self.exec_cmd(db, q, [self.queue_name, 2, prov_node])

            # change node type and set worker paused in same TX
            curs = db.cursor()
            self.exec_cmd(curs, q, [self.queue_name, 3, prov_node])
            q = "select * from pgq_node.set_consumer_paused(%s, %s, true)"
            self.exec_cmd(curs, q, [self.queue_name, state['worker_name']])
            db.commit()
        elif not state['paused']:
            # pause worker, don't wait for reaction, as it may be dead
            self.log.info('Node %s is branch, pausing worker: %s', this_node, state['worker_name'])
            q = "select * from pgq_node.set_consumer_paused(%s, %s, true)"
            self.exec_cmd(db, q, [self.queue_name, state['worker_name']])
        else:
            self.log.info('Node %s is branch and worker is paused', this_node)

        #
        # Drop old consumers and subscribers
        #
        self.log.info("** Dropping old subscribers and consumers **")

        # unregister subscriber nodes
        q = "select pgq_node.unregister_subscriber(%s, %s)"
        for node_name in sub_list:
            self.log.info("Dropping old subscriber node: %s", node_name)
            curs.execute(q, [self.queue_name, node_name])

        # unregister consumers
        q = "select consumer_name from pgq.get_consumer_info(%s)"
        curs.execute(q, [self.queue_name])
        for row in curs.fetchall():
            cname = row['consumer_name']
            if cname[0] == '.':
                self.log.info("Keeping consumer: %s", cname)
                continue
            self.log.info("Dropping old consumer: %s", cname)
            q = "pgq.unregister_consumer(%s, %s)"
            curs.execute(q, [self.queue_name, cname])
        db.commit()

        # dump events
        self.log.info("** Dump & delete lost events **")
        stats = self.resurrect_process_lost_events(db, failover_tick)

        self.log.info("** Subscribing %s to %s **", this_node, prov_node)

        # set local position
        self.log.info("Reset local completed pos")
        q = "select * from pgq_node.set_consumer_completed(%s, %s, %s)"
        self.exec_cmd(db, q, [self.queue_name, state['worker_name'], failover_tick])

        # rename gravestone
        self.log.info("Rename gravestone to worker: %s", state['worker_name'])
        prov_db = self.get_node_database(prov_node)
        prov_curs = prov_db.cursor()
        q = "select * from pgq_node.unregister_subscriber(%s, %s)"
        self.exec_cmd(prov_curs, q, [self.queue_name, this_node], quiet = True)
        q = "select ret_code, ret_note, global_watermark"\
            " from pgq_node.register_subscriber(%s, %s, %s, %s)"
        res = self.exec_cmd(prov_curs, q, [self.queue_name, this_node, state['worker_name'], failover_tick], quiet = True)
        global_wm = res[0]['global_watermark']
        prov_db.commit()

        # import new global watermark
        self.log.info("Reset global watermark")
        q = "select * from pgq_node.set_global_watermark(%s, %s)"
        self.exec_cmd(db, q, [self.queue_name, global_wm], quiet = True)

        # show stats
        if stats:
            self.log.info("** Statistics **")
            klist = stats.keys()
            klist.sort()
            for k in klist:
                v = stats[k]
                self.log.info("  %s: %s", k, v)
        self.log.info("** Resurrection done, worker paused **")

    def resurrect_process_lost_events(self, db, failover_tick):
        curs = db.cursor()
        this_node = self.queue_info.local_node.name
        cons_name = this_node + '.dumper'

        self.log.info("Dumping lost events")

        # register temp consumer on queue
        q = "select pgq.register_consumer_at(%s, %s, %s)"
        curs.execute(q, [self.queue_name, cons_name, failover_tick])
        db.commit()

        # process events as usual
        total_count = 0
        final_tick_id = -1
        stats = {}
        while 1:
            q = "select * from pgq.next_batch_info(%s, %s)"
            curs.execute(q, [self.queue_name, cons_name])
            b = curs.fetchone()
            batch_id = b['batch_id']
            if batch_id is None:
                break
            final_tick_id = b['cur_tick_id']
            q = "select * from pgq.get_batch_events(%s)"
            curs.execute(q, [batch_id])
            cnt = 0
            for ev in curs.fetchall():
                cnt += 1
                total_count += 1
                self.resurrect_dump_event(ev, stats, b)

            q = "select pgq.finish_batch(%s)"
            curs.execute(q, [batch_id])
            if cnt > 0:
                db.commit()

        stats['dumped_count'] = total_count

        self.resurrect_dump_finish()

        self.log.info("%s events dumped", total_count)

        # unregiser consumer
        q = "select pgq.unregister_consumer(%s, %s)"
        curs.execute(q, [self.queue_name, cons_name])
        db.commit()

        if failover_tick == final_tick_id:
            self.log.info("No batches found")
            return None

        #
        # Delete the events from queue
        #
        # This is done snapshots, to make sure we delete only events
        # that were dumped out previously.  This uses the long-tx
        # resistant logic described in pgq.batch_event_sql().
        #

        # find snapshots
        q = "select t1.tick_snapshot as s1, t2.tick_snapshot as s2"\
            " from pgq.tick t1, pgq.tick t2"\
            " where t1.tick_id = %s"\
            "   and t2.tick_id = %s"
        curs.execute(q, [failover_tick, final_tick_id])
        ticks = curs.fetchone()
        s1 = skytools.Snapshot(ticks['s1'])
        s2 = skytools.Snapshot(ticks['s2'])

        xlist = []
        for tx in s1.txid_list:
            if s2.contains(tx):
                xlist.append(str(tx))

        # create where clauses
        W1 = None
        if len(xlist) > 0:
            W1 = "ev_txid in (%s)" % (",".join(xlist),)
        W2 = "ev_txid >= %d AND ev_txid <= %d"\
             " and not txid_visible_in_snapshot(ev_txid, '%s')"\
             " and     txid_visible_in_snapshot(ev_txid, '%s')" % (
             s1.xmax, s2.xmax, ticks['s1'], ticks['s2'])

        # loop over all queue data tables
        q = "select * from pgq.queue where queue_name = %s"
        curs.execute(q, [self.queue_name])
        row = curs.fetchone()
        ntables = row['queue_ntables']
        tbl_pfx = row['queue_data_pfx']
        schema, table = tbl_pfx.split('.')
        total_del_count = 0
        self.log.info("Deleting lost events")
        for i in range(ntables):
            del_count = 0
            self.log.debug("Deleting events from table %d", i)
            qtbl = "%s.%s" % (skytools.quote_ident(schema),
                              skytools.quote_ident(table + '_' + str(i)))
            q = "delete from " + qtbl + " where "
            if W1:
                self.log.debug(q + W1)
                curs.execute(q + W1)
                if curs.rowcount and curs.rowcount > 0:
                    del_count += curs.rowcount
            self.log.debug(q + W2)
            curs.execute(q + W2)
            if curs.rowcount and curs.rowcount > 0:
                del_count += curs.rowcount
            total_del_count += del_count
            self.log.debug('%d events deleted', del_count)
        self.log.info('%d events deleted', total_del_count)
        stats['deleted_count'] = total_del_count

        # delete new ticks
        q = "delete from pgq.tick t using pgq.queue q"\
            " where q.queue_name = %s"\
            "   and t.tick_queue = q.queue_id"\
            "   and t.tick_id > %s"\
            "   and t.tick_id <= %s"
        curs.execute(q, [self.queue_name, failover_tick, final_tick_id])
        self.log.info("%s ticks deleted", curs.rowcount)

        db.commit()

        return stats

    _json_dump_file = None
    def resurrect_dump_event(self, ev, stats, batch_info):
        if self._json_dump_file is None:
            self._json_dump_file = open(RESURRECT_DUMP_FILE, 'w')
            sep = '['
        else:
            sep = ','

        # create ordinary dict to avoid problems with row class and datetime
        d = {
            'ev_id': ev.ev_id,
            'ev_type': ev.ev_type,
            'ev_data': ev.ev_data,
            'ev_extra1': ev.ev_extra1,
            'ev_extra2': ev.ev_extra2,
            'ev_extra3': ev.ev_extra3,
            'ev_extra4': ev.ev_extra4,
            'ev_time': ev.ev_time.isoformat(),
            'ev_txid': ev.ev_txid,
            'ev_retry': ev.ev_retry,
            'tick_id': batch_info['cur_tick_id'],
            'prev_tick_id': batch_info['prev_tick_id'],
        }
        jsev = skytools.json_encode(d)
        s = sep + '\n' + jsev
        self._json_dump_file.write(s)

    def resurrect_dump_finish(self):
        if self._json_dump_file:
            self._json_dump_file.write('\n]\n')
            self._json_dump_file.close()
            self._json_dump_file = None

    def failover_consumer_name(self, node_name):
        return node_name + ".gravestone"

    #
    # Shortcuts for operating on nodes.
    #

    def load_local_info(self):
        """fetch set info from local node."""
        db = self.get_database(self.initial_db_name)
        self.queue_info = self.load_queue_info(db)
        self.local_node = self.queue_info.local_node.name

    def get_node_database(self, node_name):
        """Connect to node."""
        if node_name == self.queue_info.local_node.name:
            db = self.get_database(self.initial_db_name)
        else:
            m = self.queue_info.get_member(node_name)
            if not m:
                self.log.error("get_node_database: cannot resolve %s", node_name)
                sys.exit(1)
            #self.log.info("%s: dead=%s", m.name, m.dead)
            if m.dead:
                return None
            loc = m.location
            db = self.get_database('node.' + node_name, connstr = loc, profile = 'remote')
        return db

    def node_alive(self, node_name):
        m = self.queue_info.get_member(node_name)
        if not m:
            res = False
        elif m.dead:
            res = False
        else:
            res = True
        #self.log.warning('node_alive(%s) = %s', node_name, res)
        return res

    def close_node_database(self, node_name):
        """Disconnect node's connection."""
        if node_name == self.queue_info.local_node.name:
            self.close_database(self.initial_db_name)
        else:
            self.close_database("node." + node_name)

    def node_cmd(self, node_name, sql, args, quiet = False):
        """Execute SQL command on particular node."""
        db = self.get_node_database(node_name)
        if not db:
            self.log.warning("ignoring cmd for dead node '%s': %s",
                    node_name, skytools.quote_statement(sql, args))
            return None
        return self.exec_cmd(db, sql, args, quiet = quiet, prefix=node_name)

    #
    # Various operation on nodes.
    #

    def set_paused(self, node, consumer, pause_flag):
        """Set node pause flag and wait for confirmation."""

        q = "select * from pgq_node.set_consumer_paused(%s, %s, %s)"
        self.node_cmd(node, q, [self.queue_name, consumer, pause_flag])

        self.log.info('Waiting for worker to accept')
        while 1:
            q = "select * from pgq_node.get_consumer_state(%s, %s)"
            stat = self.node_cmd(node, q, [self.queue_name, consumer], quiet = 1)[0]
            if stat['paused'] != pause_flag:
                raise Exception('operation canceled? %s <> %s' % (repr(stat['paused']), repr(pause_flag)))

            if stat['uptodate']:
                op = pause_flag and "paused" or "resumed"
                self.log.info("Consumer '%s' on node '%s' %s", consumer, node, op)
                return
            time.sleep(1)
        raise Exception('process canceled')

    def pause_consumer(self, node, consumer):
        """Shortcut for pausing by name."""
        self.set_paused(node, consumer, True)

    def resume_consumer(self, node, consumer):
        """Shortcut for resuming by name."""
        self.set_paused(node, consumer, False)

    def pause_node(self, node):
        """Shortcut for pausing by name."""
        state = self.get_node_info(node)
        self.pause_consumer(node, state.worker_name)

    def resume_node(self, node):
        """Shortcut for resuming by name."""
        state = self.get_node_info(node)
        if state:
            self.resume_consumer(node, state.worker_name)

    def subscribe_node(self, target_node, subscriber_node, tick_pos):
        """Subscribing one node to another."""
        q = "select * from pgq_node.subscribe_node(%s, %s, %s)"
        self.node_cmd(target_node, q, [self.queue_name, subscriber_node, tick_pos])

    def unsubscribe_node(self, target_node, subscriber_node):
        """Unsubscribing one node from another."""
        q = "select * from pgq_node.unsubscribe_node(%s, %s)"
        self.node_cmd(target_node, q, [self.queue_name, subscriber_node])

    _node_cache = {}
    def get_node_info(self, node_name):
        """Cached node info lookup."""
        if node_name in self._node_cache:
            return self._node_cache[node_name]
        inf = self.load_node_info(node_name)
        self._node_cache[node_name] = inf
        return inf

    def load_node_info(self, node_name):
        """Non-cached node info lookup."""
        db = self.get_node_database(node_name)
        if not db:
            self.log.warning('load_node_info(%s): ignoring dead node', node_name)
            return None
        q = "select * from pgq_node.get_node_info(%s)"
        rows = self.exec_query(db, q, [self.queue_name])
        return NodeInfo(self.queue_name, rows[0])

    def load_queue_info(self, db):
        """Non-cached set info lookup."""
        res = self.exec_query(db, "select * from pgq_node.get_node_info(%s)", [self.queue_name])
        info = res[0]

        q = "select * from pgq_node.get_queue_locations(%s)"
        member_list = self.exec_query(db, q, [self.queue_name])

        qinf = QueueInfo(self.queue_name, info, member_list)
        if self.options.dead:
            for node in self.options.dead:
                self.log.info("Assuming node '%s' as dead", node)
                qinf.tag_dead(node)
        return qinf

    def get_node_subscriber_list(self, node_name):
        """Fetch subscriber list from a node."""
        q = "select node_name, node_watermark from pgq_node.get_subscriber_info(%s)"
        db = self.get_node_database(node_name)
        rows = self.exec_query(db, q, [self.queue_name])
        return [r['node_name'] for r in rows]

    def get_node_consumer_map(self, node_name):
        """Fetch consumer list from a node."""
        q = "select consumer_name, provider_node, last_tick_id from pgq_node.get_consumer_info(%s)"
        db = self.get_node_database(node_name)
        rows = self.exec_query(db, q, [self.queue_name])
        res = {}
        for r in rows:
            res[r['consumer_name']] = r
        return res

if __name__ == '__main__':
    script = CascadeAdmin('setadm', 'node_db', sys.argv[1:], worker_setup = False)
    script.start()

########NEW FILE########
__FILENAME__ = consumer
"""Cascaded consumer.


Does not maintain node, but is able to pause, resume and switch provider.
"""

import sys, time

from pgq.baseconsumer import BaseConsumer

PDB = '_provider_db'

__all__ = ['CascadedConsumer']

class CascadedConsumer(BaseConsumer):
    """CascadedConsumer base class.

    Loads provider from target node, accepts pause/resume commands.
    """

    _consumer_state = None

    def __init__(self, service_name, db_name, args):
        """Initialize new consumer.

        @param service_name: service_name for DBScript
        @param db_name: target database name for get_database()
        @param args: cmdline args for DBScript
        """

        BaseConsumer.__init__(self, service_name, PDB, args)

        self.log.debug("__init__")

        self.target_db = db_name
        self.provider_connstr = None

    def init_optparse(self, parser = None):
        p = BaseConsumer.init_optparse(self, parser)
        p.add_option("--provider", help = "provider location for --register")
        p.add_option("--rewind", action = "store_true",
                help = "change queue position according to destination")
        p.add_option("--reset", action = "store_true",
                help = "reset queue position on destination side")
        return p

    def startup(self):
        if self.options.rewind:
            self.rewind()
            sys.exit(0)
        if self.options.reset:
            self.dst_reset()
            sys.exit(0)
        return BaseConsumer.startup(self)

    def register_consumer(self, provider_loc = None):
        """Register consumer on source node first, then target node."""

        if not provider_loc:
            provider_loc = self.options.provider
        if not provider_loc:
            self.log.error('Please give provider location with --provider=')
            sys.exit(1)

        dst_db = self.get_database(self.target_db)
        dst_curs = dst_db.cursor()
        src_db = self.get_database(PDB, connstr = provider_loc, profile = 'remote')
        src_curs = src_db.cursor()

        # check target info
        q = "select * from pgq_node.get_node_info(%s)"
        res = self.exec_cmd(src_db, q, [ self.queue_name ])
        pnode = res[0]['node_name']
        if not pnode:
            raise Exception('parent node not initialized?')

        # source queue
        BaseConsumer.register_consumer(self)

        # fetch pos
        q = "select last_tick from pgq.get_consumer_info(%s, %s)"
        src_curs.execute(q, [self.queue_name, self.consumer_name])
        last_tick = src_curs.fetchone()['last_tick']
        if not last_tick:
            raise Exception('registration failed?')
        src_db.commit()

        # target node
        q = "select * from pgq_node.register_consumer(%s, %s, %s, %s)"
        self.exec_cmd(dst_db, q, [self.queue_name, self.consumer_name, pnode, last_tick])

    def get_consumer_state(self):
        dst_db = self.get_database(self.target_db)
        dst_curs = dst_db.cursor()
        q = "select * from pgq_node.get_consumer_state(%s, %s)"
        rows = self.exec_cmd(dst_db, q, [ self.queue_name, self.consumer_name ])
        state = rows[0]
        return state

    def get_provider_db(self, state):
        provider_loc = state['provider_location']
        return self.get_database(PDB, connstr = provider_loc, profile = 'remote')

    def unregister_consumer(self):
        dst_db = self.get_database(self.target_db)
        state = self.get_consumer_state()
        src_db = self.get_provider_db(state)

        # unregister on provider
        BaseConsumer.unregister_consumer(self)

        # unregister on subscriber
        q = "select * from pgq_node.unregister_consumer(%s, %s)"
        self.exec_cmd(dst_db, q, [ self.queue_name, self.consumer_name ])

    def rewind(self):
        self.log.info("Rewinding queue")
        dst_db = self.get_database(self.target_db)
        dst_curs = dst_db.cursor()

        state = self.get_consumer_state()
        src_db = self.get_provider_db(state)
        src_curs = src_db.cursor()

        dst_tick = state['completed_tick']
        if dst_tick:
            q = "select pgq.register_consumer_at(%s, %s, %s)"
            src_curs.execute(q, [self.queue_name, self.consumer_name, dst_tick])
        else:
            self.log.warning('No tick found on dst side')

        dst_db.commit()
        src_db.commit()

    def dst_reset(self):
        self.log.info("Resetting queue tracking on dst side")

        dst_db = self.get_database(self.target_db)
        dst_curs = dst_db.cursor()

        state = self.get_consumer_state()

        src_db = self.get_provider_db(state)
        src_curs = src_db.cursor()

        # fetch last tick from source
        q = "select last_tick from pgq.get_consumer_info(%s, %s)"
        src_curs.execute(q, [self.queue_name, self.consumer_name])
        row = src_curs.fetchone()
        src_db.commit()

        # on root node we dont have consumer info
        if not row:
            self.log.info("No info about consumer, cannot reset")
            return

        # set on destination
        last_tick = row['last_tick']
        q = "select * from pgq_node.set_consumer_completed(%s, %s, %s)"
        dst_curs.execute(q, [self.queue_name, self.consumer_name, last_tick])
        dst_db.commit()

    def process_batch(self, src_db, batch_id, event_list):
        state = self._consumer_state

        dst_db = self.get_database(self.target_db)

        if self.is_batch_done(state, self.batch_info, dst_db):
            return

        tick_id = self.batch_info['tick_id']
        self.process_remote_batch(src_db, tick_id, event_list, dst_db)

        # this also commits
        self.finish_remote_batch(src_db, dst_db, tick_id)

    def process_root_node(self, dst_db):
        """This is called on root node, where no processing should happen.
        """
        # extra sleep
        time.sleep(10*self.loop_delay)

        self.log.info('{standby: 1}')

    def work(self):
        """Refresh state before calling Consumer.work()."""

        dst_db = self.get_database(self.target_db)
        self._consumer_state = self.refresh_state(dst_db)

        if self._consumer_state['node_type'] == 'root':
            self.process_root_node(dst_db)
            return

        if not self.provider_connstr:
            raise Exception('provider_connstr not set')
        src_db = self.get_provider_db(self._consumer_state)

        return BaseConsumer.work(self)

    def refresh_state(self, dst_db, full_logic = True):
        """Fetch consumer state from target node.

        This also sleeps if pause is set and updates
        "uptodate" flag to notify that data is refreshed.
        """

        while 1:
            q = "select * from pgq_node.get_consumer_state(%s, %s)"
            rows = self.exec_cmd(dst_db, q, [ self.queue_name, self.consumer_name ])
            state = rows[0]

            # tag refreshed
            if not state['uptodate'] and full_logic:
                q = "select * from pgq_node.set_consumer_uptodate(%s, %s, true)"
                self.exec_cmd(dst_db, q, [ self.queue_name, self.consumer_name ])

            if state['cur_error'] and self.work_state != -1:
                q = "select * from pgq_node.set_consumer_error(%s, %s, NULL)"
                self.exec_cmd(dst_db, q, [ self.queue_name, self.consumer_name ])

            if not state['paused'] or not full_logic:
                break
            time.sleep(self.loop_delay)

        # update connection
        loc = state['provider_location']
        if self.provider_connstr != loc:
            self.close_database(PDB)
            self.provider_connstr = loc
            # re-initialize provider connection
            db = self.get_provider_db(state);

        return state

    def is_batch_done(self, state, batch_info, dst_db):
        cur_tick = batch_info['tick_id']
        prev_tick = batch_info['prev_tick_id']
        dst_tick = state['completed_tick']

        if not dst_tick:
            raise Exception('dst_tick NULL?')

        if prev_tick == dst_tick:
            # on track
            return False

        if cur_tick == dst_tick:
            # current batch is already applied, skip it
            return True

        # anything else means problems
        raise Exception('Lost position: batch %s..%s, dst has %s' % (
                        prev_tick, cur_tick, dst_tick))

    def process_remote_batch(self, src_db, tick_id, event_list, dst_db):
        """Per-batch callback.

        By default just calls process_remote_event() in loop."""
        src_curs = src_db.cursor()
        dst_curs = dst_db.cursor()
        for ev in event_list:
            self.process_remote_event(src_curs, dst_curs, ev)

    def process_remote_event(self, src_curs, dst_curs, ev):
        """Per-event callback.

        By default ignores cascading events and gives error on others.
        Can be called from user handler to finish unprocessed events.
        """
        if ev.ev_type[:4] == "pgq.":
            # ignore cascading events
            pass
        else:
            raise Exception('Unhandled event type in queue: %s' % ev.ev_type)

    def finish_remote_batch(self, src_db, dst_db, tick_id):
        """Called after event processing.  This should finish
        work on remote db and commit there.
        """
        # this also commits
        q = "select * from pgq_node.set_consumer_completed(%s, %s, %s)"
        self.exec_cmd(dst_db, q, [ self.queue_name, self.consumer_name, tick_id ])

    def exception_hook(self, det, emsg):
        try:
            dst_db = self.get_database(self.target_db)
            q = "select * from pgq_node.set_consumer_error(%s, %s, %s)"
            self.exec_cmd(dst_db, q, [ self.queue_name, self.consumer_name, emsg ])
        except:
            self.log.warning("Failure to call pgq_node.set_consumer_error()")
        self.reset()
        BaseConsumer.exception_hook(self, det, emsg)

########NEW FILE########
__FILENAME__ = nodeinfo
#! /usr/bin/env python

"""Info about node/set/members.  For admin tool.
"""

__all__ = ['MemberInfo', 'NodeInfo', 'QueueInfo']

import datetime
import skytools

# node types
ROOT = 'root'
BRANCH = 'branch'
LEAF = 'leaf'

class MemberInfo:
    """Info about set member."""
    def __init__(self, row):
        self.name = row['node_name']
        self.location = row['node_location']
        self.dead = row['dead']

def ival2str(iv):
    res = ""
    tmp, secs = divmod(iv.seconds, 60)
    hrs, mins = divmod(tmp, 60)
    if iv.days:
        res += "%dd" % iv.days
    if hrs:
        res += "%dh" % hrs
    if mins:
        res += "%dm" % mins
    res += "%ds" % secs
    return res

class NodeInfo:
    """Detailed info about set node."""

    name = None
    type = None
    global_watermark = None
    local_watermark = None
    completed_tick = None
    provider_node = None
    provider_location = None
    consumer_name = None #?
    worker_name = None #?
    paused = False
    uptodate = True
    combined_queue = None
    combined_type = None
    last_tick = None
    node_attrs = {}

    def __init__(self, queue_name, row, main_worker = True, node_name = None):
        self.queue_name = queue_name
        self.member_map = {}
        self.main_worker = main_worker

        self.parent = None
        self.consumer_map = {}
        self.queue_info = {}
        self._info_lines = []
        self.cascaded_consumer_map = {}

        self._row = row

        if not row:
            self.name = node_name
            self.type = 'dead'
            return

        self.name = row['node_name']
        self.type = row['node_type']
        self.global_watermark = row['global_watermark']
        self.local_watermark = row['local_watermark']
        self.completed_tick = row['worker_last_tick']
        self.provider_node = row['provider_node']
        self.provider_location = row['provider_location']
        self.consumer_name = row['worker_name']
        self.worker_name = row['worker_name']
        self.paused = row['worker_paused']
        self.uptodate = row['worker_uptodate']
        self.combined_queue = row['combined_queue']
        self.combined_type = row['combined_type']
        self.last_tick = row['worker_last_tick']

        self.node_attrs = {}
        if 'node_attrs' in row:
            a = row['node_attrs']
            if a:
                self.node_attrs = skytools.db_urldecode(a)

    def __get_target_queue(self):
        qname = None
        if self.type == LEAF:
            if self.combined_queue:
                qname = self.combined_queue
            else:
                return None
        else:
            qname = self.queue_name
        if qname is None:
            raise Exception("no target queue")
        return qname

    def get_title(self):
        return "%s (%s)" % (self.name, self.type)

    def get_infolines(self):
        lst = self._info_lines

        lag = None
        if self.parent:
            root = self.parent
            while root.parent:
                root = root.parent
            cinfo = self.parent.consumer_map.get(self.consumer_name)
            if cinfo and root.queue_info:
                tick_time = cinfo['tick_time']
                root_time = root.queue_info['now']
                if root_time < tick_time:
                    # ignore negative lag - probably due to info gathering
                    # taking long time
                    lag = datetime.timedelta(0)
                else:
                    lag = root_time - tick_time
        elif self.queue_info:
            lag = self.queue_info['ticker_lag']

        txt = "Lag: %s" % (lag and ival2str(lag) or "(n/a)")
        if self.last_tick:
            txt += ", Tick: %s" % self.last_tick
        if self.paused:
            txt += ", PAUSED"
        if not self.uptodate:
            txt += ", NOT UPTODATE"
        lst.append(txt)

        for k, v in self.node_attrs.items():
            txt = "Attr: %s=%s" % (k, v)
            lst.append(txt)

        for cname, row in self.cascaded_consumer_map.items():
            err = row['cur_error']
            if err:
                # show only first line
                pos = err.find('\n')
                if pos > 0:
                    err = err[:pos]
                lst.append("ERR: %s: %s" % (cname, err))
        return lst

    def add_info_line(self, ln):
        self._info_lines.append(ln)

    def load_status(self, curs):
        self.consumer_map = {}
        self.queue_info = {}
        self.cascaded_consumer_map = {}
        if self.queue_name:
            q = "select consumer_name, current_timestamp - lag as tick_time,"\
                "  lag, last_seen, last_tick "\
                "from pgq.get_consumer_info(%s)"
            curs.execute(q, [self.queue_name])
            for row in curs.fetchall():
                cname = row['consumer_name']
                self.consumer_map[cname] = row

            q = "select current_timestamp - ticker_lag as tick_time,"\
                "  ticker_lag, current_timestamp as now "\
                "from pgq.get_queue_info(%s)"
            curs.execute(q, [self.queue_name])
            self.queue_info = curs.fetchone()

            q = "select * from pgq_node.get_consumer_info(%s)"
            curs.execute(q, [self.queue_name])
            for row in curs.fetchall():
                cname = row['consumer_name']
                self.cascaded_consumer_map[cname] = row

class QueueInfo:
    """Info about cascaded queue.

    Slightly broken, as all info is per-node.
    """

    def __init__(self, queue_name, info_row, member_rows):
        self.local_node = NodeInfo(queue_name, info_row)
        self.queue_name = queue_name
        self.member_map = {}
        self.node_map = {}
        self.add_node(self.local_node)

        for r in member_rows:
            m = MemberInfo(r)
            self._add_member(m)

    def _add_member(self, member):
        self.member_map[member.name] = member

    def get_member(self, name):
        return self.member_map.get(name)

    def get_node(self, name):
        return self.node_map.get(name)

    def add_node(self, node):
        self.node_map[node.name] = node

    def tag_dead(self, node_name):
        if node_name in self.node_map:
            self.member_map[node_name].dead = True
        else:
            row = {'node_name': node_name, 'node_location': None, 'dead': True}
            m = MemberInfo(row)
            self.member_map[node_name] = m
    #
    # Rest is about printing the tree
    #

    _DATAFMT = "%-30s%s"
    def print_tree(self):
        """Print ascii-tree for set.
        Expects that data for all nodes is filled in."""

        print('Queue: %s   Local node: %s' % (self.queue_name, self.local_node.name))
        print('')

        root_list = self._prepare_tree()
        for root in root_list:
            self._tree_calc(root)
            datalines = self._print_node(root, '', [])
            for ln in datalines:
                print(self._DATAFMT % (' ', ln))

    def _print_node(self, node, pfx, datalines):
        # print a tree fragment for node and info
        # returns list of unprinted data rows
        for ln in datalines:
            print(self._DATAFMT % (_setpfx(pfx, '|'), ln))
        datalines = node.get_infolines()
        print("%s%s" % (_setpfx(pfx, '+--: '), node.get_title()))

        for i, n in enumerate(node.child_list):
            sfx = ((i < len(node.child_list) - 1) and '  |' or '   ')
            datalines = self._print_node(n, pfx + sfx, datalines)

        return datalines

    def _prepare_tree(self):
        # reset vars, fill parent and child_list for each node
        # returns list of root nodes (mostly 1)

        for node in self.node_map.values():
            node.total_childs = 0
            node.levels = 0
            node.child_list = []
            node.parent = None

        root_list = []
        for node in self.node_map.values():
            if node.provider_node \
                    and node.provider_node != node.name \
                    and node.provider_node in self.node_map:
                p = self.node_map[node.provider_node]
                p.child_list.append(node)
                node.parent = p
            else:
                node.parent = None
                root_list.append(node)
        return root_list

    def _tree_calc(self, node):
        # calculate levels and count total childs
        # sort the tree based on them
        total = len(node.child_list)
        levels = 1
        for subnode in node.child_list:
            self._tree_calc(subnode)
            total += subnode.total_childs
            if levels < subnode.levels + 1:
                levels = subnode.levels + 1
        node.total_childs = total
        node.levels = levels
        node.child_list.sort(key = _node_key)

def _setpfx(pfx, sfx):
    if pfx:
        pfx = pfx[:-1] + sfx
    return pfx

def _node_key(n):
    return (n.levels, n.total_childs, n.name)

########NEW FILE########
__FILENAME__ = worker
"""Cascaded worker.

CascadedConsumer that also maintains node.

"""

import sys, time, skytools

from pgq.cascade.consumer import CascadedConsumer
from pgq.producer import bulk_insert_events
from pgq.event import Event

__all__ = ['CascadedWorker']

class WorkerState:
    """Depending on node state decides on actions worker needs to do."""
    # node_type,
    # node_name, provider_node,
    # global_watermark, local_watermark
    # combined_queue, combined_type
    process_batch = 0       # handled in CascadedConsumer
    copy_events = 0         # ok
    global_wm_event = 0     # ok
    local_wm_publish = 1    # ok

    process_events = 0      # ok
    send_tick_event = 0     # ok
    wait_behind = 0         # ok
    process_tick_event = 0  # ok
    target_queue = ''       # ok
    keep_event_ids = 0      # ok
    create_tick = 0         # ok
    filtered_copy = 0       # ok
    process_global_wm = 0   # ok

    sync_watermark = 0      # ?
    wm_sync_nodes = []

    def __init__(self, queue_name, nst):
        self.node_type = nst['node_type']
        self.node_name = nst['node_name']
        self.local_watermark = nst['local_watermark']
        self.global_watermark = nst['global_watermark']

        self.node_attrs = {}
        attrs = nst.get('node_attrs', '')
        if attrs:
            self.node_attrs = skytools.db_urldecode(attrs)

        ntype = nst['node_type']
        ctype = nst['combined_type']
        if ntype == 'root':
            self.global_wm_event = 1
            self.local_wm_publish = 0
        elif ntype == 'branch':
            self.target_queue = queue_name
            self.process_batch = 1
            self.process_events = 1
            self.copy_events = 1
            self.process_tick_event = 1
            self.keep_event_ids = 1
            self.create_tick = 1
            if 'sync_watermark' in self.node_attrs:
                slist = self.node_attrs['sync_watermark']
                self.sync_watermark = 1
                self.wm_sync_nodes = slist.split(',')
            else:
                self.process_global_wm = 1
        elif ntype == 'leaf' and not ctype:
            self.process_batch = 1
            self.process_events = 1
        elif ntype == 'leaf' and ctype:
            self.target_queue = nst['combined_queue']
            if ctype == 'root':
                self.process_batch = 1
                self.process_events = 1
                self.copy_events = 1
                self.filtered_copy = 1
                self.send_tick_event = 1
            elif ctype == 'branch':
                self.process_batch = 1
                self.wait_behind = 1
            else:
                raise Exception('invalid state 1')
        else:
            raise Exception('invalid state 2')
        if ctype and ntype != 'leaf':
            raise Exception('invalid state 3')

class CascadedWorker(CascadedConsumer):
    """CascadedWorker base class.

    Config fragment::

        ## Parameters for pgq.CascadedWorker ##

        # how often the root node should push wm downstream (seconds)
        #global_wm_publish_period = 300

        # how often the nodes should report their wm upstream (seconds)
        #local_wm_publish_period = 300
    """

    global_wm_publish_time = 0
    global_wm_publish_period = 5 * 60

    local_wm_publish_time = 0
    local_wm_publish_period = 5 * 60

    max_evbuf = 500
    cur_event_seq = 0
    cur_max_id = 0
    seq_buffer = 10000

    main_worker = True

    _worker_state = None
    ev_buf = []

    real_global_wm = None

    def __init__(self, service_name, db_name, args):
        """Initialize new consumer.

        @param service_name: service_name for DBScript
        @param db_name: target database name for get_database()
        @param args: cmdline args for DBScript
        """

        CascadedConsumer.__init__(self, service_name, db_name, args)

    def reload(self):
        CascadedConsumer.reload(self)

        self.global_wm_publish_period = self.cf.getfloat('global_wm_publish_period', CascadedWorker.global_wm_publish_period)
        self.local_wm_publish_period = self.cf.getfloat('local_wm_publish_period', CascadedWorker.local_wm_publish_period)

    def process_remote_batch(self, src_db, tick_id, event_list, dst_db):
        """Worker-specific event processing."""
        self.ev_buf = []
        max_id = 0
        st = self._worker_state

        if st.wait_behind:
            self.wait_for_tick(dst_db, tick_id)

        src_curs = src_db.cursor()
        dst_curs = dst_db.cursor()
        for ev in event_list:
            if st.copy_events:
                self.copy_event(dst_curs, ev, st.filtered_copy)
            if ev.ev_type.split('.', 1)[0] in ("pgq", "londiste"):
                # process cascade events even on waiting leaf node
                self.process_remote_event(src_curs, dst_curs, ev)
            else:
                if st.process_events:
                    self.process_remote_event(src_curs, dst_curs, ev)
            if ev.ev_id > max_id:
                max_id = ev.ev_id
        if max_id > self.cur_max_id:
            self.cur_max_id = max_id

    def wait_for_tick(self, dst_db, tick_id):
        """On combined-branch leaf needs to wait from tick
        to appear from combined-root.
        """
        while 1:
            cst = self._consumer_state
            if cst['completed_tick'] >= tick_id:
                return
            self.sleep(10 * self.loop_delay)
            self._consumer_state = self.refresh_state(dst_db)
            if not self.looping:
                sys.exit(0)

    def is_batch_done(self, state, batch_info, dst_db):
        wst = self._worker_state

        # on combined-branch the target can get several batches ahead
        if wst.wait_behind:
            # let the wait-behind logic track ticks
            return False

        # check if events have processed
        done = CascadedConsumer.is_batch_done(self, state, batch_info, dst_db)
        if not wst.create_tick:
            return done
        if not done:
            return False

        # check if tick is done - it happens in separate tx

        # fetch last tick from target queue
        q = "select t.tick_id from pgq.tick t, pgq.queue q"\
            " where t.tick_queue = q.queue_id and q.queue_name = %s"\
            " order by t.tick_queue desc, t.tick_id desc"\
            " limit 1"
        curs = dst_db.cursor()
        curs.execute(q, [self.queue_name])
        last_tick = curs.fetchone()['tick_id']
        dst_db.commit()

        # insert tick if missing
        cur_tick = batch_info['tick_id']
        if last_tick != cur_tick:
            prev_tick = batch_info['prev_tick_id']
            tick_time = batch_info['batch_end']
            if last_tick != prev_tick:
                raise Exception('is_batch_done: last branch tick = %d, expected %d or %d' % (
                                last_tick, prev_tick, cur_tick))
            self.create_branch_tick(dst_db, cur_tick, tick_time)
        return True

    def publish_local_wm(self, src_db, dst_db):
        """Send local watermark to provider.
        """

        t = time.time()
        if t - self.local_wm_publish_time < self.local_wm_publish_period:
            return

        st = self._worker_state
        wm = st.local_watermark
        if st.sync_watermark:
            # dont send local watermark upstream
            wm = self.batch_info['prev_tick_id']
        elif wm > self.batch_info['cur_tick_id']:
            # in wait-behind-leaf case, the wm from target can be
            # ahead from source queue, use current batch then
            wm = self.batch_info['cur_tick_id']

        self.log.debug("Publishing local watermark: %d", wm)
        src_curs = src_db.cursor()
        q = "select * from pgq_node.set_subscriber_watermark(%s, %s, %s)"
        src_curs.execute(q, [self.pgq_queue_name, st.node_name, wm])
        src_db.commit()

        # if next part fails, dont repeat it immediately
        self.local_wm_publish_time = t

        if st.sync_watermark and self.real_global_wm is not None:
            # instead sync 'global-watermark' with specific nodes
            dst_curs = dst_db.cursor()
            nmap = self._get_node_map(dst_curs)
            dst_db.commit()

            # local lowest
            wm = st.local_watermark

            # the global-watermark in subtree can stay behind
            # upstream global-watermark, but must not go ahead
            if self.real_global_wm < wm:
                wm = self.real_global_wm

            for node in st.wm_sync_nodes:
                if node == st.node_name:
                    continue
                if node not in nmap:
                    # dont ignore missing nodes - cluster may be partially set up
                    self.log.warning('Unknown node in sync_watermark list: %s', node)
                    return
                n = nmap[node]
                if n['dead']:
                    # ignore dead nodes
                    continue
                wmdb = self.get_database('wmdb', connstr = n['node_location'], autocommit = 1, profile = 'remote')
                wmcurs = wmdb.cursor()
                q = 'select local_watermark from pgq_node.get_node_info(%s)'
                wmcurs.execute(q, [self.queue_name])
                row = wmcurs.fetchone()
                if not row:
                    # partially set up node?
                    self.log.warning('Node not working: %s', node)
                elif row['local_watermark'] < wm:
                    # keep lowest wm
                    wm = row['local_watermark']
                self.close_database('wmdb')

            # now we have lowest wm, store it
            q = "select pgq_node.set_global_watermark(%s, %s)"
            dst_curs.execute(q, [self.queue_name, wm])
            dst_db.commit()

    def _get_node_map(self, curs):
        q = "select node_name, node_location, dead from pgq_node.get_queue_locations(%s)"
        curs.execute(q, [self.queue_name])
        res = {}
        for row in curs.fetchall():
            res[row['node_name']] = row
        return res

    def process_remote_event(self, src_curs, dst_curs, ev):
        """Handle cascading events.
        """

        if ev.retry:
            raise Exception('CascadedWorker must not get retry events')

        # non cascade events send to CascadedConsumer to error out
        if ev.ev_type[:4] != 'pgq.':
            CascadedConsumer.process_remote_event(self, src_curs, dst_curs, ev)
            return

        # ignore cascade events if not main worker
        if not self.main_worker:
            return

        # check if for right queue
        t = ev.ev_type
        if ev.ev_extra1 != self.pgq_queue_name and t != "pgq.tick-id":
            raise Exception("bad event in queue: "+str(ev))

        self.log.debug("got cascade event: %s(%s)", t, ev.ev_data)
        st = self._worker_state
        if t == "pgq.location-info":
            node = ev.ev_data
            loc = ev.ev_extra2
            dead = ev.ev_extra3
            q = "select * from pgq_node.register_location(%s, %s, %s, %s)"
            dst_curs.execute(q, [self.pgq_queue_name, node, loc, dead])
        elif t == "pgq.unregister-location":
            node = ev.ev_data
            q = "select * from pgq_node.unregister_location(%s, %s)"
            dst_curs.execute(q, [self.pgq_queue_name, node])
        elif t == "pgq.global-watermark":
            if st.sync_watermark:
                tick_id = int(ev.ev_data)
                self.log.debug('Half-ignoring global watermark %d', tick_id)
                self.real_global_wm = tick_id
            elif st.process_global_wm:
                tick_id = int(ev.ev_data)
                q = "select * from pgq_node.set_global_watermark(%s, %s)"
                dst_curs.execute(q, [self.pgq_queue_name, tick_id])
        elif t == "pgq.tick-id":
            tick_id = int(ev.ev_data)
            if ev.ev_extra1 == self.pgq_queue_name:
                raise Exception('tick-id event for own queue?')
            if st.process_tick_event:
                q = "select * from pgq_node.set_partition_watermark(%s, %s, %s)"
                dst_curs.execute(q, [self.pgq_queue_name, ev.ev_extra1, tick_id])
        else:
            raise Exception("unknown cascade event: %s" % t)

    def finish_remote_batch(self, src_db, dst_db, tick_id):
        """Worker-specific cleanup on target node.
        """

        # merge-leaf on branch should not update tick pos
        st = self._worker_state
        if st.wait_behind:
            dst_db.commit()

            # still need to publish wm info
            if st.local_wm_publish and self.main_worker:
                self.publish_local_wm(src_db, dst_db)

            return

        if self.main_worker:
            dst_curs = dst_db.cursor()

            self.flush_events(dst_curs)

            # send tick event into queue
            if st.send_tick_event:
                q = "select pgq.insert_event(%s, 'pgq.tick-id', %s, %s, null, null, null)"
                dst_curs.execute(q, [st.target_queue, str(tick_id), self.pgq_queue_name])

        CascadedConsumer.finish_remote_batch(self, src_db, dst_db, tick_id)

        if self.main_worker:
            if st.create_tick:
                # create actual tick
                tick_id = self.batch_info['tick_id']
                tick_time = self.batch_info['batch_end']
                self.create_branch_tick(dst_db, tick_id, tick_time)
            if st.local_wm_publish:
                self.publish_local_wm(src_db, dst_db)

    def create_branch_tick(self, dst_db, tick_id, tick_time):
        q = "select pgq.ticker(%s, %s, %s, %s)"
        # execute it in autocommit mode
        ilev = dst_db.isolation_level
        dst_db.set_isolation_level(0)
        dst_curs = dst_db.cursor()
        dst_curs.execute(q, [self.pgq_queue_name, tick_id, tick_time, self.cur_max_id])
        dst_db.set_isolation_level(ilev)

    def copy_event(self, dst_curs, ev, filtered_copy):
        """Add event to copy buffer.
        """
        if not self.main_worker:
            return
        if filtered_copy:
            if ev.type[:4] == "pgq.":
                return
        if len(self.ev_buf) >= self.max_evbuf:
            self.flush_events(dst_curs)

        if ev.type == 'pgq.global-watermark':
            st = self._worker_state
            if st.sync_watermark:
                # replace payload with synced global watermark
                row = ev._event_row.copy()
                row['ev_data'] = str(st.global_watermark)
                ev = Event(self.queue_name, row)
        self.ev_buf.append(ev)

    def flush_events(self, dst_curs):
        """Send copy buffer to target queue.
        """
        if len(self.ev_buf) == 0:
            return
        flds = ['ev_time', 'ev_type', 'ev_data', 'ev_extra1',
                'ev_extra2', 'ev_extra3', 'ev_extra4']
        st = self._worker_state
        if st.keep_event_ids:
            flds.append('ev_id')
        bulk_insert_events(dst_curs, self.ev_buf, flds, st.target_queue)
        self.ev_buf = []

    def refresh_state(self, dst_db, full_logic = True):
        """Load also node state from target node.
        """
        res = CascadedConsumer.refresh_state(self, dst_db, full_logic)
        q = "select * from pgq_node.get_node_info(%s)"
        st = self.exec_cmd(dst_db, q, [ self.pgq_queue_name ])
        self._worker_state = WorkerState(self.pgq_queue_name, st[0])
        return res

    def process_root_node(self, dst_db):
        """On root node send global watermark downstream.
        """

        CascadedConsumer.process_root_node(self, dst_db)

        t = time.time()
        if t - self.global_wm_publish_time < self.global_wm_publish_period:
            return

        self.log.debug("Publishing global watermark")
        dst_curs = dst_db.cursor()
        q = "select * from pgq_node.set_global_watermark(%s, NULL)"
        dst_curs.execute(q, [self.pgq_queue_name])
        dst_db.commit()
        self.global_wm_publish_time = t

########NEW FILE########
__FILENAME__ = consumer

"""PgQ consumer framework for Python.

"""

from pgq.baseconsumer import BaseConsumer, BaseBatchWalker
from pgq.event import Event

__all__ = ['Consumer']


# Event status codes
EV_UNTAGGED = -1
EV_RETRY = 0
EV_DONE = 1


class RetriableEvent(Event):
    """Event which can be retried

    Consumer is supposed to tag them after processing.
    """
    __slots__ = ('_status', )

    def __init__(self, queue_name, row):
        super(RetriableEvent, self).__init__(queue_name, row)
        self._status = EV_DONE

    def tag_done(self):
        self._status = EV_DONE

    def get_status(self):
        return self._status

    def tag_retry(self, retry_time = 60):
        self._status = EV_RETRY
        self.retry_time = retry_time


class RetriableWalkerEvent(RetriableEvent):
    """Redirects status flags to RetriableBatchWalker.

    That way event data can be gc'd immediately and
    tag_done() events don't need to be remembered.
    """
    __slots__ = ('_walker', )

    def __init__(self, walker, queue_name, row):
        super(RetriableWalkerEvent, self).__init__(queue_name, row)
        self._walker = walker

    def tag_done(self):
        self._walker.tag_event_done(self)

    def get_status(self):
        self._walker.get_status(self)

    def tag_retry(self, retry_time = 60):
        self._walker.tag_event_retry(self, retry_time)


class RetriableBatchWalker(BaseBatchWalker):
    """BatchWalker that returns RetriableEvents
    """

    def __init__(self, curs, batch_id, queue_name, fetch_size = 300, consumer_filter = None):
        super(RetriableBatchWalker, self).__init__(curs, batch_id, queue_name, fetch_size, consumer_filter)
        self.status_map = {}

    def _make_event(self, queue_name, row):
        return RetriableWalkerEvent(self, queue_name, row)

    def tag_event_done(self, event):
        if event.id in self.status_map:
            del self.status_map[event.id]

    def tag_event_retry(self, event, retry_time):
        self.status_map[event.id] = (EV_RETRY, retry_time)

    def get_status(self, event):
        return self.status_map.get(event.id, (EV_DONE, 0))[0]

    def iter_status(self):
        for res in self.status_map.iteritems():
            yield res


class Consumer(BaseConsumer):
    """Normal consumer base class.
    Can retry events
    """

    _batch_walker_class = RetriableBatchWalker

    def _make_event(self, queue_name, row):
        return RetriableEvent(queue_name, row)

    def _flush_retry(self, curs, batch_id, list):
        """Tag retry events."""

        retry = 0
        if self.pgq_lazy_fetch:
            for ev_id, stat in list.iter_status():
                if stat[0] == EV_RETRY:
                    self._tag_retry(curs, batch_id, ev_id, stat[1])
                    retry += 1
                elif stat[0] != EV_DONE:
                    raise Exception("Untagged event: id=%d" % ev_id)
        else:
            for ev in list:
                if ev._status == EV_RETRY:
                    self._tag_retry(curs, batch_id, ev.id, ev.retry_time)
                    retry += 1
                elif ev._status != EV_DONE:
                    raise Exception("Untagged event: (id=%d, type=%s, data=%s, ex1=%s" % (
                                    ev.id, ev.type, ev.data, ev.extra1))

        # report weird events
        if retry:
            self.stat_increase('retry-events', retry)

    def _finish_batch(self, curs, batch_id, list):
        """Tag events and notify that the batch is done."""

        self._flush_retry(curs, batch_id, list)

        super(Consumer, self)._finish_batch(curs, batch_id, list)

    def _tag_retry(self, cx, batch_id, ev_id, retry_time):
        """Tag event for retry. (internal)"""
        cx.execute("select pgq.event_retry(%s, %s, %s)",
                    [batch_id, ev_id, retry_time])

########NEW FILE########
__FILENAME__ = coopconsumer

"""PgQ cooperative consumer for Python.
"""

from pgq.consumer import Consumer

__all__ = ['CoopConsumer']

class CoopConsumer(Consumer):
    """Cooperative Consumer base class.

    There will be one dbscript process per subconsumer.

    Config params::
        ## pgq.CoopConsumer

        # name for subconsumer
        subconsumer_name =

        # pgsql interval when to consider parallel subconsumers dead,
        # and take over their unfinished batch
        #subconsumer_timeout = 1 hour
    """

    def __init__(self, service_name, db_name, args):
        """Initialize new subconsumer.

        @param service_name: service_name for DBScript
        @param db_name: name of database for get_database()
        @param args: cmdline args for DBScript
        """

        Consumer.__init__(self, service_name, db_name, args)

        self.subconsumer_name = self.cf.get("subconsumer_name")
        self.subconsumer_timeout = self.cf.get("subconsumer_timeout", "")

    def register_consumer(self):
        """Registration for subconsumer."""

        self.log.info("Registering consumer on source queue")
        db = self.get_database(self.db_name)
        cx = db.cursor()
        cx.execute("select pgq_coop.register_subconsumer(%s, %s, %s)",
                [self.queue_name, self.consumer_name, self.subconsumer_name])
        res = cx.fetchone()[0]
        db.commit()

        return res

    def unregister_consumer(self):
        """Unregistration for subconsumer."""

        self.log.info("Unregistering consumer from source queue")
        db = self.get_database(self.db_name)
        cx = db.cursor()
        cx.execute("select pgq_coop.unregister_subconsumer(%s, %s, %s, 0)",
                    [self.queue_name, self.consumer_name, self.subconsumer_name])
        db.commit()


    def _load_next_batch(self, curs):
        """Allocate next batch. (internal)"""

        if self.subconsumer_timeout:
            q = "select pgq_coop.next_batch(%s, %s, %s, %s)"
            curs.execute(q, [self.queue_name, self.consumer_name, self.subconsumer_name, self.subconsumer_timeout])
        else:
            q = "select pgq_coop.next_batch(%s, %s, %s)"
            curs.execute(q, [self.queue_name, self.consumer_name, self.subconsumer_name])
        return curs.fetchone()[0]

    def _finish_batch(self, curs, batch_id, list):
        """Finish batch. (internal)"""

        self._flush_retry(curs, batch_id, list)
        curs.execute("select pgq_coop.finish_batch(%s)", [batch_id])


########NEW FILE########
__FILENAME__ = event

"""PgQ event container.
"""

__all__ = ['Event']

_fldmap = {
        'ev_id': 'ev_id',
        'ev_txid': 'ev_txid',
        'ev_time': 'ev_time',
        'ev_type': 'ev_type',
        'ev_data': 'ev_data',
        'ev_extra1': 'ev_extra1',
        'ev_extra2': 'ev_extra2',
        'ev_extra3': 'ev_extra3',
        'ev_extra4': 'ev_extra4',
        'ev_retry': 'ev_retry',

        'id': 'ev_id',
        'txid': 'ev_txid',
        'time': 'ev_time',
        'type': 'ev_type',
        'data': 'ev_data',
        'extra1': 'ev_extra1',
        'extra2': 'ev_extra2',
        'extra3': 'ev_extra3',
        'extra4': 'ev_extra4',
        'retry': 'ev_retry',
}

class Event(object):
    """Event data for consumers.

    Will be removed from the queue by default.
    """
    __slots__ = ('_event_row', 'retry_time', 'queue_name')

    def __init__(self, queue_name, row):
        self._event_row = row
        self.retry_time = 60
        self.queue_name = queue_name

    def __getattr__(self, key):
        return self._event_row[_fldmap[key]]

    # would be better in RetriableEvent only since we don't care but
    # unfortunately it needs to be defined here due to compatibility concerns
    def tag_done(self):
        pass

    # be also dict-like
    def __getitem__(self, k): return self._event_row.__getitem__(k)
    def __contains__(self, k): return self._event_row.__contains__(k)
    def get(self, k, d=None): return self._event_row.get(k, d)
    def has_key(self, k): return self._event_row.has_key(k)
    def keys(self): return self._event_row.keys()
    def values(self): return self._event_row.keys()
    def items(self): return self._event_row.items()
    def iterkeys(self): return self._event_row.iterkeys()
    def itervalues(self): return self._event_row.itervalues()

    def __str__(self):
        return "<id=%d type=%s data=%s e1=%s e2=%s e3=%s e4=%s>" % (
                self.id, self.type, self.data, self.extra1, self.extra2, self.extra3, self.extra4)

########NEW FILE########
__FILENAME__ = localconsumer

"""
Consumer that stores last applied position in local file.

For cases where the consumer cannot use single database for remote tracking.

To be subclassed, then override .process_local_batch() or .process_local_event()
methods.

"""

import sys
import os
import errno
import skytools
from pgq.baseconsumer import BaseConsumer

__all__ = ['LocalConsumer']

class LocalConsumer(BaseConsumer):
    """Consumer that applies batches sequentially in second database.

    Requirements:
     - Whole batch in one TX.
     - Must not use retry queue.

    Features:
     - Can detect if several batches are already applied to dest db.
     - If some ticks are lost, allows to seek back on queue.
       Whether it succeeds, depends on pgq configuration.

    Config options::

        ## Parameters for LocalConsumer ##

        # file location where last applied tick is tracked
        local_tracking_file = ~/state/%(job_name)s.tick
    """

    def reload(self):
        super(LocalConsumer, self).reload()

        self.local_tracking_file = self.cf.getfile('local_tracking_file')
        if not os.path.exists(os.path.dirname(self.local_tracking_file)):
            raise skytools.UsageError ("path does not exist: %s" % self.local_tracking_file)

    def init_optparse(self, parser = None):
        p = super(LocalConsumer, self).init_optparse(parser)
        p.add_option("--rewind", action = "store_true",
                help = "change queue position according to local tick")
        p.add_option("--reset", action = "store_true",
                help = "reset local tick based on queue position")
        return p

    def startup(self):
        if self.options.rewind:
            self.rewind()
            sys.exit(0)
        if self.options.reset:
            self.dst_reset()
            sys.exit(0)
        super(LocalConsumer, self).startup()

        self.check_queue()

    def check_queue(self):
        queue_tick = -1
        local_tick = self.load_local_tick()

        db = self.get_database(self.db_name)
        curs = db.cursor()
        q = "select last_tick from pgq.get_consumer_info(%s, %s)"
        curs.execute(q, [self.queue_name, self.consumer_name])
        rows = curs.fetchall()
        if len(rows) == 1:
            queue_tick = rows[0]['last_tick']
        db.commit()

        if queue_tick < 0:
            if local_tick >= 0:
                self.log.info("Registering consumer at tick %d", local_tick)
                q = "select * from pgq.register_consumer_at(%s, %s, %s)"
                curs.execute(q, [self.queue_name, self.consumer_name, local_tick])
            else:
                self.log.info("Registering consumer at queue top")
                q = "select * from pgq.register_consumer(%s, %s)"
                curs.execute(q, [self.queue_name, self.consumer_name])
        elif local_tick < 0:
            self.log.info("Local tick missing, storing queue tick %d", queue_tick)
            self.save_local_tick(queue_tick)
        elif local_tick > queue_tick:
            self.log.warning("Tracking out of sync: queue=%d local=%d.  Repositioning on queue.  [Database failure?]",
                             queue_tick, local_tick)
            q = "select * from pgq.register_consumer_at(%s, %s, %s)"
            curs.execute(q, [self.queue_name, self.consumer_name, local_tick])
        elif local_tick < queue_tick:
            self.log.warning("Tracking out of sync: queue=%d local=%d.  Rewinding queue.  [Lost file data?]",
                             queue_tick, local_tick)
            q = "select * from pgq.register_consumer_at(%s, %s, %s)"
            curs.execute(q, [self.queue_name, self.consumer_name, local_tick])
        else:
            self.log.info("Ticks match: Queue=%d Local=%d", queue_tick, local_tick)

    def work(self):
        if self.work_state < 0:
            self.check_queue()
        return super(LocalConsumer, self).work()

    def process_batch(self, db, batch_id, event_list):
        """Process all events in batch.
        """

        # check if done
        if self.is_batch_done():
            return

        # actual work
        self.process_local_batch(db, batch_id, event_list)

        # finish work
        self.set_batch_done()

    def process_local_batch(self, db, batch_id, event_list):
        """Overridable method to process whole batch."""
        for ev in event_list:
            self.process_local_event(db, batch_id, ev)

    def process_local_event(self, db, batch_id, ev):
        """Overridable method to process one event at a time."""
        raise Exception('process_local_event not implemented')

    def is_batch_done(self):
        """Helper function to keep track of last successful batch in external database.
        """

        local_tick = self.load_local_tick()

        cur_tick = self.batch_info['tick_id']
        prev_tick = self.batch_info['prev_tick_id']

        if local_tick < 0:
            # seems this consumer has not run yet?
            return False

        if prev_tick == local_tick:
            # on track
            return False

        if cur_tick == local_tick:
            # current batch is already applied, skip it
            return True

        # anything else means problems
        raise Exception('Lost position: batch %d..%d, dst has %d' % (
                        prev_tick, cur_tick, local_tick))

    def set_batch_done(self):
        """Helper function to set last successful batch in external database.
        """
        tick_id = self.batch_info['tick_id']
        self.save_local_tick(tick_id)

    def register_consumer(self):
        new = super(LocalConsumer, self).register_consumer()
        if new: # fixme
            self.dst_reset()

    def unregister_consumer(self):
        """If unregistering, also clean completed tick table on dest."""

        super(LocalConsumer, self).unregister_consumer()
        self.dst_reset()

    def rewind(self):
        dst_tick = self.load_local_tick()
        if dst_tick >= 0:
            src_db = self.get_database(self.db_name)
            src_curs = src_db.cursor()

            self.log.info("Rewinding queue to local tick %d", dst_tick)
            q = "select pgq.register_consumer_at(%s, %s, %s)"
            src_curs.execute(q, [self.queue_name, self.consumer_name, dst_tick])

            src_db.commit()
        else:
            self.log.error('Cannot rewind, no tick found in local file')

    def dst_reset(self):
        self.log.info("Removing local tracking file")
        try:
            os.remove(self.local_tracking_file)
        except:
            pass

    def load_local_tick(self):
        """Reads stored tick or -1."""
        try:
            f = open(self.local_tracking_file, 'r')
            buf = f.read()
            f.close()
            data = buf.strip()
            if data:
                tick_id = int(data)
            else:
                tick_id = -1
            return tick_id
        except IOError, ex:
            if ex.errno == errno.ENOENT:
                return -1
            raise

    def save_local_tick(self, tick_id):
        """Store tick in local file."""
        data = str(tick_id)
        skytools.write_atomic(self.local_tracking_file, data)

########NEW FILE########
__FILENAME__ = producer

"""PgQ producer helpers for Python.
"""

import skytools

__all__ = ['bulk_insert_events', 'insert_event']

_fldmap = {
    'id': 'ev_id',
    'time': 'ev_time',
    'type': 'ev_type',
    'data': 'ev_data',
    'extra1': 'ev_extra1',
    'extra2': 'ev_extra2',
    'extra3': 'ev_extra3',
    'extra4': 'ev_extra4',

    'ev_id': 'ev_id',
    'ev_time': 'ev_time',
    'ev_type': 'ev_type',
    'ev_data': 'ev_data',
    'ev_extra1': 'ev_extra1',
    'ev_extra2': 'ev_extra2',
    'ev_extra3': 'ev_extra3',
    'ev_extra4': 'ev_extra4',
}

def bulk_insert_events(curs, rows, fields, queue_name):
    q = "select pgq.current_event_table(%s)"
    curs.execute(q, [queue_name])
    tbl = curs.fetchone()[0]
    db_fields = map(_fldmap.get, fields)
    skytools.magic_insert(curs, tbl, rows, db_fields)

def insert_event(curs, queue, ev_type, ev_data,
                 extra1=None, extra2=None,
                 extra3=None, extra4=None):
    q = "select pgq.insert_event(%s, %s, %s, %s, %s, %s, %s)"
    curs.execute(q, [queue, ev_type, ev_data,
                     extra1, extra2, extra3, extra4])
    return curs.fetchone()[0]


########NEW FILE########
__FILENAME__ = remoteconsumer

"""
old RemoteConsumer / SerialConsumer classes.

"""

import sys

from pgq.consumer import Consumer

__all__ = ['RemoteConsumer', 'SerialConsumer']

class RemoteConsumer(Consumer):
    """Helper for doing event processing in another database.

    Requires that whole batch is processed in one TX.
    """

    def __init__(self, service_name, db_name, remote_db, args):
        Consumer.__init__(self, service_name, db_name, args)
        self.remote_db = remote_db

    def process_batch(self, db, batch_id, event_list):
        """Process all events in batch.
        
        By default calls process_event for each.
        """
        dst_db = self.get_database(self.remote_db)
        curs = dst_db.cursor()

        if self.is_last_batch(curs, batch_id):
            return

        self.process_remote_batch(db, batch_id, event_list, dst_db)

        self.set_last_batch(curs, batch_id)
        dst_db.commit()

    def is_last_batch(self, dst_curs, batch_id):
        """Helper function to keep track of last successful batch
        in external database.
        """
        q = "select pgq_ext.is_batch_done(%s, %s)"
        dst_curs.execute(q, [ self.consumer_name, batch_id ])
        return dst_curs.fetchone()[0]

    def set_last_batch(self, dst_curs, batch_id):
        """Helper function to set last successful batch
        in external database.
        """
        q = "select pgq_ext.set_batch_done(%s, %s)"
        dst_curs.execute(q, [ self.consumer_name, batch_id ])

    def process_remote_batch(self, db, batch_id, event_list, dst_db):
        raise Exception('process_remote_batch not implemented')

class SerialConsumer(Consumer):
    """Consumer that applies batches sequentially in second database.

    Requirements:
     - Whole batch in one TX.
     - Must not use retry queue.

    Features:
     - Can detect if several batches are already applied to dest db.
     - If some ticks are lost. allows to seek back on queue.
       Whether it succeeds, depends on pgq configuration.
    """

    def __init__(self, service_name, db_name, remote_db, args):
        Consumer.__init__(self, service_name, db_name, args)
        self.remote_db = remote_db
        self.dst_schema = "pgq_ext"

    def startup(self):
        if self.options.rewind:
            self.rewind()
            sys.exit(0)
        if self.options.reset:
            self.dst_reset()
            sys.exit(0)
        return Consumer.startup(self)

    def init_optparse(self, parser = None):
        p = Consumer.init_optparse(self, parser)
        p.add_option("--rewind", action = "store_true",
                help = "change queue position according to destination")
        p.add_option("--reset", action = "store_true",
                help = "reset queue pos on destination side")
        return p

    def process_batch(self, db, batch_id, event_list):
        """Process all events in batch.
        """

        dst_db = self.get_database(self.remote_db)
        curs = dst_db.cursor()

        # check if done
        if self.is_batch_done(curs):
            return

        # actual work
        self.process_remote_batch(db, batch_id, event_list, dst_db)

        # finish work
        self.set_batch_done(curs)
        dst_db.commit()

    def is_batch_done(self, dst_curs):
        """Helper function to keep track of last successful batch
        in external database.
        """

        cur_tick = self.batch_info['tick_id']
        prev_tick = self.batch_info['prev_tick_id']

        dst_tick = self.get_last_tick(dst_curs)
        if not dst_tick:
            # seems this consumer has not run yet against dst_db
            return False

        if prev_tick == dst_tick:
            # on track
            return False

        if cur_tick == dst_tick:
            # current batch is already applied, skip it
            return True

        # anything else means problems
        raise Exception('Lost position: batch %d..%d, dst has %d' % (
                        prev_tick, cur_tick, dst_tick))

    def set_batch_done(self, dst_curs):
        """Helper function to set last successful batch
        in external database.
        """
        tick_id = self.batch_info['tick_id']
        self.set_last_tick(dst_curs, tick_id)

    def register_consumer(self):
        new = Consumer.register_consumer(self)
        if new: # fixme
            self.dst_reset()

    def unregister_consumer(self):
        """If unregistering, also clean completed tick table on dest."""

        Consumer.unregister_consumer(self)
        self.dst_reset()

    def process_remote_batch(self, db, batch_id, event_list, dst_db):
        raise Exception('process_remote_batch not implemented')

    def rewind(self):
        self.log.info("Rewinding queue")
        src_db = self.get_database(self.db_name)
        dst_db = self.get_database(self.remote_db)
        src_curs = src_db.cursor()
        dst_curs = dst_db.cursor()

        dst_tick = self.get_last_tick(dst_curs)
        if dst_tick:
            q = "select pgq.register_consumer_at(%s, %s, %s)"
            src_curs.execute(q, [self.queue_name, self.consumer_name, dst_tick])
        else:
            self.log.warning('No tick found on dst side')

        dst_db.commit()
        src_db.commit()
        
    def dst_reset(self):
        self.log.info("Resetting queue tracking on dst side")
        dst_db = self.get_database(self.remote_db)
        dst_curs = dst_db.cursor()
        self.set_last_tick(dst_curs, None)
        dst_db.commit()
        
    def get_last_tick(self, dst_curs):
        q = "select %s.get_last_tick(%%s)" % self.dst_schema
        dst_curs.execute(q, [self.consumer_name])
        res = dst_curs.fetchone()
        return res[0]

    def set_last_tick(self, dst_curs, tick_id):
        q = "select %s.set_last_tick(%%s, %%s)" % self.dst_schema
        dst_curs.execute(q, [ self.consumer_name, tick_id ])



########NEW FILE########
__FILENAME__ = status

"""Status display.
"""

import sys, skytools

__all__ = ['PGQStatus']

def ival(data, _as = None):
    "Format interval for output"
    if not _as:
        _as = data.split('.')[-1]
    numfmt = 'FM9999999'
    expr = "coalesce(to_char(extract(epoch from %s), '%s') || 's', 'NULL') as %s"
    return expr % (data, numfmt, _as)

class PGQStatus(skytools.DBScript):
    """Info gathering and display."""
    def __init__(self, args, check = 0):
        skytools.DBScript.__init__(self, 'pgqadm', args)

        self.show_status()

        sys.exit(0)

    def show_status(self):
        db = self.get_database("db", autocommit=1)
        cx = db.cursor()

        cx.execute("show server_version")
        pgver = cx.fetchone()[0]
        cx.execute("select pgq.version()")
        qver = cx.fetchone()[0]
        print("Postgres version: %s   PgQ version: %s" % (pgver, qver))

        q = """select f.queue_name, f.queue_ntables, %s, %s,
                      %s, %s, q.queue_ticker_max_count,
                      f.ev_per_sec, f.ev_new
                from pgq.get_queue_info() f, pgq.queue q
               where q.queue_name = f.queue_name""" % (
                    ival('f.queue_rotation_period'),
                    ival('f.ticker_lag'),
                    ival('q.queue_ticker_max_lag'),
                    ival('q.queue_ticker_idle_period'),
               )
        cx.execute(q)
        event_rows = cx.fetchall()

        q = """select queue_name, consumer_name, %s, %s, pending_events
               from pgq.get_consumer_info()""" % (
                ival('lag'),
                ival('last_seen'),
              )
        cx.execute(q)
        consumer_rows = cx.fetchall()

        print("\n%-33s %9s %13s %6s %6s %5s" % ('Event queue',
                            'Rotation', 'Ticker', 'TLag', 'EPS', 'New'))
        print('-' * 78)
        for ev_row in event_rows:
            tck = "%s/%s/%s" % (ev_row['queue_ticker_max_count'],
                    ev_row['queue_ticker_max_lag'],
                    ev_row['queue_ticker_idle_period'])
            rot = "%s/%s" % (ev_row['queue_ntables'], ev_row['queue_rotation_period'])
            print("%-33s %9s %13s %6s %6.1f %5d" % (
                ev_row['queue_name'],
                rot,
                tck,
                ev_row['ticker_lag'],
                ev_row['ev_per_sec'],
                ev_row['ev_new'],
            ))
        print('-' * 78)
        print("\n%-48s %9s %9s %8s" % (
                'Consumer', 'Lag', 'LastSeen', 'Pending'))
        print('-' * 78)
        for ev_row in event_rows:
            cons = self.pick_consumers(ev_row, consumer_rows)
            self.show_queue(ev_row, cons)
        print('-' * 78)
        db.commit()

    def show_consumer(self, cons):
        print("  %-46s %9s %9s %8d" % (
                    cons['consumer_name'],
                    cons['lag'], cons['last_seen'],
                    cons['pending_events']))

    def show_queue(self, ev_row, consumer_rows):
        print("%(queue_name)s:" % ev_row)
        for cons in consumer_rows:
            self.show_consumer(cons)


    def pick_consumers(self, ev_row, consumer_rows):
        res = []
        for con in consumer_rows:
            if con['queue_name'] != ev_row['queue_name']:
                continue
            res.append(con)
        return res


########NEW FILE########
__FILENAME__ = pkgloader
"""Loader for Skytools modules.

Primary idea is to allow several major versions to co-exists.
Secondary idea - allow checking minimal minor version.

"""

import sys, os, os.path, re

__all__ = ['require']

_top = os.path.dirname(os.path.abspath(os.path.normpath(__file__)))

_pkg_cache = None
_import_cache = {}
_pat = re.compile('^([a-z]+)-([0-9]+).([0-9]+)$')

def _load_pkg_cache():
    global _pkg_cache
    if _pkg_cache is not None:
        return _pkg_cache
    _pkg_cache = {}
    for dir in os.listdir(_top):
        m = _pat.match(dir)
        if not m:
            continue
        modname = m.group(1)
        modver = (int(m.group(2)), int(m.group(3)))
        _pkg_cache.setdefault(modname, []).append((modver, dir))
    for vlist in _pkg_cache.itervalues():
        vlist.sort(reverse = True)
    return _pkg_cache

def _install_path(pkg, newpath):
    for p in sys.path:
        pname = os.path.basename(p)
        m = _pat.match(pname)
        if m and m.group(1) == pkg:
            sys.path.remove(p)
    sys.path.insert(0, newpath)

def require(pkg, reqver):
    # parse arg
    reqval = tuple([int(n) for n in reqver.split('.')])
    need = reqval[:2] # cut minor ver

    # check if we already have one installed
    if pkg in _import_cache:
        got = _import_cache[pkg]
        if need[0] != got[0] or reqval > got:
            raise ImportError("Request for package '%s' ver '%s', have '%s'" % (
                              pkg, reqver, '.'.join(got)))
        return

    # pick best ver from available ones
    cache = _load_pkg_cache()
    if pkg not in cache:
        return

    for pkgver, pkgdir in cache[pkg]:
        if pkgver[0] == need[0] and pkgver >= need:
            # install the best on
            _install_path(pkg, os.path.join(_top, pkgdir))
            break

    inst_ver = reqval

    # now import whatever is available
    mod = __import__(pkg)

    # check if it is actually useful
    ver_str = mod.__version__
    for i, c in enumerate(ver_str):
        if c != '.' and not c.isdigit():
            ver_str = ver_str[:i]
            break
    full_ver = tuple([int(x) for x in ver_str.split('.')])
    if full_ver[0] != reqval[0] or reqval > full_ver:
        raise ImportError("Request for package '%s' ver '%s', have '%s'" % (
                          pkg, reqver, '.'.join(full_ver)))
    inst_ver = full_ver

    # remember full version
    _import_cache[pkg] = inst_ver

    return mod


########NEW FILE########
__FILENAME__ = qadmin
#! /usr/bin/env python

"""Commands that require only database connection:

    connect dbname=.. host=.. service=.. queue=..;
    connect [ queue=.. ] [ node=.. ];
    install pgq | londiste;

    show queue [ <qname | *> ];
    create queue <qname>;
    alter queue <qname | *> set param = , ...;
    drop queue <qname>;

    show consumer [ <cname | *> [on <qname>] ];
    register consumer <consumer> [on <qname> | at <tick_id> | copy <consumer> ]* ;
    unregister consumer <consumer | *> [from <qname>];
    register subconsumer <subconsumer> for <consumer> [on <qname>];
    unregister subconsumer <subconsumer | *> for <consumer> [from <qname>] [close [batch]];

    show node [ <node | *> [on <qname>] ];
    show table <tbl>;
    show sequence <seq>;

Following commands expect default queue:

    show batch <batch_id>;
    show batch <consumer>;

Londiste commands:

    londiste add table <tbl> [ , ... ]
        with skip_truncate, tgflags='UIDBAQL',
             expect_sync, no_triggers,
             -- pass trigger args:
             backup, skip, when='EXPR', ev_XX='EXPR';
    londiste add sequence <seq>;
    londiste remove table <tbl> [ , ... ];
    londiste remove sequence <seq> [ , ... ];
    londiste tables;
    londiste seqs;
    londiste missing;

Other commands:

    exit;  - quit program
    ^D     - quit program
    ^C     - clear current buffer
"""

# unimplemented:
"""
create <root | branch | leaf> node <node> location <loc> [on <qname>];
drop node <node> [on <qname>];
alter node <node> [location=<loc>]
show_queue_stats <q>;

change provider
drop node
status
rename node

node create

create root_node <name>;
create branch_node <name>;
create leaf_node <name>;

alter node <name> provider <new>;

alter node <name> takeover <oldnow> with all;
alter node <name> rename <new>;

takeover <oldnode>;

drop node <name>;

show node [ <node | *> [on <qname>] ];
show cascade;

"""

cmdline_usage = '''\
Usage: qadmin [switches]

Initial connection options:
    -h host
    -p port
    -U user
    -d dbname
    -Q queuename

Command options:
    -c cmd_string
    -f execfile

General options:
    --help
    --version
'''

import sys, os, readline, getopt, re, psycopg2, traceback

import pkgloader
pkgloader.require('skytools', '3.0')
import skytools

__version__ = skytools.__version__

script = None

IGNORE_HOSTS = {
    'ip6-allhosts': 1,
    'ip6-allnodes': 1,
    'ip6-allrouters': 1,
    #'ip6-localhost': 1,
    'ip6-localnet': 1,
    'ip6-loopback': 1,
    'ip6-mcastprefix': 1,
}

_ident_rx =''' ( " ( "" | [^"]+ )* " ) | ( [a-z_][a-z0-9_]* ) | [.] | (?P<err> .)  '''
_ident_rc = re.compile(_ident_rx, re.X | re.I)

def unquote_any(typ, s):
    global _ident_rc
    if typ == 'ident':
        res = []
        pos = 0
        while 1:
            m = _ident_rc.match(s, pos)
            if not m:
                break
            if m.group('err'):
                raise Exception('invalid syntax for ident')
            s1 = m.group()
            if s1[0] == '"':
                s1 = s1[1:-1].replace('""', '"')
            res.append(s1)
            pos = m.end()
        s = ''.join(res)
    elif typ == 'str' or typ == 'dolq':
        s = skytools.unquote_literal(s, True)
    return s

def normalize_any(typ, s):
    if typ == 'ident' and s.find('"') < 0:
        s = s.lower()
    return s

def display_result(curs, desc, fields = []):
    """Display multirow query as a table."""

    rows = curs.fetchall()

    if not fields:
        fields = [f[0] for f in curs.description]

    widths = [10] * len(fields)
    for i, f in enumerate(fields):
        rlen = len(f)
        if rlen > widths[i]:
            widths[i] = rlen
    for row in rows:
        for i, k in enumerate(fields):
            rlen = row[k] and len(str(row[k])) or 0
            if rlen > widths[i]:
                widths[i] = rlen
    widths = [w + 2 for w in widths]

    fmt = '%%-%ds' * (len(widths) - 1) + '%%s'
    fmt = fmt % tuple(widths[:-1])
    if desc:
        print(desc)
    print(fmt % tuple(fields))
    print(fmt % tuple([ '-' * (w - 2) for w in widths ]))

    for row in rows:
        print(fmt % tuple([row[k] for k in fields]))
    print('')

##
## Base token classes
##

class Token:
    """Base class for tokens.

    The optional 'param' kwarg will set corresponding key in
    'params' dict to final token value.
    """
    # string to append to completions
    c_append = ' '

    # token type to accept
    tk_type = ("ident", "dolq", "str", "num", "sym")
    # skipped: numarg, pyold, pynew

    def __init__(self, next = None, name = None, append = 0):
        self.next = next
        self.name = name
        self._append = append

    # top-level api

    def get_next(self, typ, word, params):
        """Return next token if 'word' matches this token."""
        if not self.is_acceptable(typ, word):
            return None
        self.set_param(typ, word, params)
        return self.next

    def get_completions(self, params):
        """Return list of all completions possible at this point."""
        wlist = self.get_wlist()
        comp_list = [w + self.c_append for w in wlist]
        return comp_list

    # internal api

    def get_wlist(self):
        """Return list of potential words at this point."""
        return []

    def set_param(self, typ, word, params):
        # now set special param
        if not self.name:
            return
        uw = unquote_any(typ, word)
        if self._append:
            lst = params.setdefault(self.name, [])
            lst.append(uw)
        else:
            params[self.name] = uw

    def is_acceptable(self, tok, word):
        if tok not in self.tk_type:
            return False
        return True

class Exact(Token):
    """Single fixed token."""
    def __init__(self, value, next, **kwargs):
        Token.__init__(self, next, **kwargs)
        self.value = value
    def get_wlist(self):
        return [self.value]
    def is_acceptable(self, typ, word):
        if not Token.is_acceptable(self, typ, word):
            return False
        return word == self.value

class List(Token):
    """List of Tokens, will be tried sequentially until one matches."""
    def __init__(self, *args, **kwargs):
        Token.__init__(self, **kwargs)
        self.tok_list = list(args)

    def add(self, *args):
        for a in args:
            self.tok_list.append(a)

    def get_next(self, typ, word, params):
        for w in self.tok_list:
            n = w.get_next(typ, word, params)
            if n:
                self.set_param(typ, word, params)
                return n
        return None

    def get_completions(self, params):
        comp_list = []
        for w in self.tok_list:
            comp_list += w.get_completions(params)
        return comp_list

##
## Dynamic token classes
##

class ConnstrPassword(Token):
    tk_type = ("str", "num", "ident")

class StrValue(Token):
    tk_type = ("str",)

class NumValue(Token):
    tk_type = ("num",)

class Word(Exact):
    """Single fixed keyword."""
    tk_type = ("ident",)

class Name(Token):
    """Dynamically generated list of idents."""
    tk_type = ("ident")

class Symbol(Exact):
    """Single fixed symbol."""
    tk_type = ("sym",)
    c_append = ''

class XSymbol(Symbol):
    """Symbol that is not shown in completion."""
    def get_wlist(self):
        return []

class SubConsumerName(Token):
    tk_type = ("str", "num", "ident")

# data-dependant completions

class Queue(Name):
    def get_wlist(self):
        return script.get_queue_list()

class Consumer(Name):
    def get_wlist(self):
        return script.get_consumer_list()

class DBNode(Name):
    def get_wlist(self):
        return script.get_node_list()

class Database(Name):
    def get_wlist(self):
        return script.get_database_list()

class Host(Name):
    def get_wlist(self):
        return script.get_host_list()

class User(Name):
    def get_wlist(self):
        return script.get_user_list()

class NewTable(Name):
    def get_wlist(self):
        return script.get_new_table_list()

class KnownTable(Name):
    def get_wlist(self):
        return script.get_known_table_list()

class PlainTable(Name):
    def get_wlist(self):
        return script.get_plain_table_list()

class PlainSequence(Name):
    def get_wlist(self):
        return script.get_plain_seq_list()

class NewSeq(Name):
    def get_wlist(self):
        return script.get_new_seq_list()

class KnownSeq(Name):
    def get_wlist(self):
        return script.get_known_seq_list()

class BatchId(NumValue):
    def get_wlist(self):
        return script.get_batch_list()

class TickId(NumValue):
    def get_wlist(self):
        return []

class Port(NumValue):
    def get_wlist(self):
        return ['5432', '6432']

# easier completion - add follow-up symbols

class WordEQ(Word):
    """Word that is followed by '='."""
    c_append = '='
    def __init__(self, word, next, **kwargs):
        next = Symbol('=', next)
        Word.__init__(self, word, next, **kwargs)

class WordEQQ(Word):
    """Word that is followed by '=' and string."""
    c_append = "='"
    def __init__(self, word, next, **kwargs):
        next = Symbol('=', next)
        Word.__init__(self, word, next, **kwargs)

##
##  Now describe the syntax.
##

top_level = List(name = 'cmd')

w_done = Symbol(';', top_level)
w_xdone = XSymbol(';', top_level)

w_sql = List(w_done)
w_sql.add(Token(w_sql))

w_connect = List()
w_connect.add(
        WordEQ('dbname', Database(w_connect, name = 'dbname')),
        WordEQ('host', Host(w_connect, name = 'host')),
        WordEQ('port', Port(w_connect, name = 'port')),
        WordEQ('user', User(w_connect, name = 'user')),
        WordEQ('password', ConnstrPassword(w_connect, name = 'password')),
        WordEQ('queue', Queue(w_connect, name = 'queue')),
        WordEQ('node', DBNode(w_connect, name = 'node')),
        w_done)

w_show_batch = List(
    BatchId(w_done, name = 'batch_id'),
    Consumer(w_done, name = 'consumer'))

w_show_queue = List(
    Symbol('*', w_done, name = 'queue'),
    Queue(w_done, name = 'queue'),
    w_done)

w_show_on_queue = List(
    Symbol('*', w_done, name = 'queue'),
    Queue(w_done, name = 'queue'),
    )

w_on_queue = List(Word('on', w_show_on_queue), w_done)

w_show_consumer = List(
    Symbol('*', w_on_queue, name = 'consumer'),
    Consumer(w_on_queue, name = 'consumer'),
    w_done)

w_show_node = List(
    Symbol('*', w_on_queue, name = 'node'),
    DBNode(w_on_queue, name = 'node'),
    w_done)

w_show_table = PlainTable(w_done, name = 'table')

w_show_seq = PlainSequence(w_done, name = 'seq')

w_show = List(
    Word('batch', w_show_batch),
    Word('help', w_done),
    Word('queue', w_show_queue),
    Word('consumer', w_show_consumer),
    Word('node', w_show_node),
    Word('table', w_show_table),
    Word('sequence', w_show_seq),
    Word('version', w_done),
    name = "cmd2")

w_install = List(
    Word('pgq', w_done),
    Word('londiste', w_done),
    name = 'module')

# alter queue
w_qargs2 = List()

w_qargs = List(
    WordEQQ('idle_period', StrValue(w_qargs2, name = 'ticker_idle_period')),
    WordEQ('max_count', NumValue(w_qargs2, name = 'ticker_max_count')),
    WordEQQ('max_lag', StrValue(w_qargs2, name = 'ticker_max_lag')),
    WordEQ('paused', NumValue(w_qargs2, name = 'ticker_paused')))

w_qargs2.add(w_done)
w_qargs2.add(Symbol(',', w_qargs))

w_set_q = Word('set', w_qargs)

w_alter_q = List(
        Symbol('*', w_set_q, name = 'queue'),
        Queue(w_set_q, name = 'queue'))

# alter
w_alter = List(
        Word('queue', w_alter_q),
        w_sql,
        name = 'cmd2')

# create
w_create = List(
        Word('queue', Queue(w_done, name = 'queue')),
        w_sql,
        name = 'cmd2')

# drop
w_drop = List(
        Word('queue', Queue(w_done, name = 'queue')),
        w_sql,
        name = 'cmd2')

# register
w_reg_target = List()
w_reg_target.add(
        Word('on', Queue(w_reg_target, name = 'queue')),
        Word('copy', Consumer(w_reg_target, name = 'copy_reg')),
        Word('at', TickId(w_reg_target, name = 'at_tick')),
        w_done)

w_cons_on_queue = Word('consumer',
        Consumer(w_reg_target, name = 'consumer'),
        name = 'cmd2')

w_sub_reg_target = List()
w_sub_reg_target.add(
        Word('on', Queue(w_sub_reg_target, name = 'queue')),
        Word('for', Consumer(w_sub_reg_target, name = 'consumer')),
        w_done)

w_subcons_on_queue = Word('subconsumer',
        SubConsumerName(w_sub_reg_target, name = 'subconsumer'),
        name = 'cmd2')

w_register = List(w_cons_on_queue,
                  w_subcons_on_queue)

# unregister

w_from_queue = List(w_done, Word('from', Queue(w_done, name = 'queue')))
w_cons_from_queue = Word('consumer',
        List( Symbol('*', w_from_queue, name = 'consumer'),
              Consumer(w_from_queue, name = 'consumer')
            ),
        name = 'cmd2')

w_done_close = List(w_done,
            Word('close', List(w_done, Word('batch', w_done)), name = 'close'))
w_from_queue_close = List(w_done_close,
                          Word('from', Queue(w_done_close, name = 'queue')))
w_con_from_queue = Consumer(w_from_queue_close, name = 'consumer')
w_subcons_from_queue = Word('subconsumer',
    List( Symbol('*', Word('for', w_con_from_queue), name = 'subconsumer'),
          SubConsumerName(Word('for', w_con_from_queue), name = 'subconsumer')
        ),
    name = 'cmd2')

w_unregister = List(w_cons_from_queue,
                    w_subcons_from_queue)

# londiste add table
w_table_with2 = List()
w_table_with = List(
    Word('skip_truncate', w_table_with2, name = 'skip_truncate'),
    Word('expect_sync', w_table_with2, name = 'expect_sync'),
    Word('backup', w_table_with2, name = 'backup'),
    Word('skip', w_table_with2, name = 'skip'),
    Word('no_triggers', w_table_with2, name = 'no_triggers'),
    WordEQQ('ev_ignore', StrValue(w_table_with2, name = 'ignore')),
    WordEQQ('ev_type', StrValue(w_table_with2, name = 'ev_type')),
    WordEQQ('ev_data', StrValue(w_table_with2, name = 'ev_data')),
    WordEQQ('ev_extra1', StrValue(w_table_with2, name = 'ev_extra1')),
    WordEQQ('ev_extra2', StrValue(w_table_with2, name = 'ev_extra2')),
    WordEQQ('ev_extra3', StrValue(w_table_with2, name = 'ev_extra3')),
    WordEQQ('ev_extra4', StrValue(w_table_with2, name = 'ev_extra4')),
    WordEQQ('pkey', StrValue(w_table_with2, name = 'pkey')),
    WordEQQ('when', StrValue(w_table_with2, name = 'when')),
    WordEQQ('tgflags', StrValue(w_table_with2, name = 'tgflags'))
    )

w_table_with2.add(w_done)
w_table_with2.add(Symbol(',', w_table_with))

w_londiste_add_table = List()
w_londiste_add_table2 = List(
    Symbol(',', w_londiste_add_table),
    Word('with', w_table_with),
    w_done)
w_londiste_add_table.add(
    NewTable(w_londiste_add_table2,
             name = 'tables', append = 1))

# londiste add seq
w_londiste_add_seq = List()
w_londiste_add_seq2 = List(
    Symbol(',', w_londiste_add_seq),
    w_done)
w_londiste_add_seq.add(
    NewSeq(w_londiste_add_seq2, name = 'seqs', append = 1))

# londiste remove table
w_londiste_remove_table = List()
w_londiste_remove_table2 = List(
    Symbol(',', w_londiste_remove_table),
    w_done)
w_londiste_remove_table.add(
    KnownTable(w_londiste_remove_table2, name = 'tables', append = 1))

# londiste remove sequence
w_londiste_remove_seq = List()
w_londiste_remove_seq2 = List(
    Symbol(',', w_londiste_remove_seq),
    w_done)
w_londiste_remove_seq.add(
    KnownSeq(w_londiste_remove_seq2, name = 'seqs', append = 1))

w_londiste_add = List(
        Word('table', w_londiste_add_table),
        Word('sequence', w_londiste_add_seq),
        name = 'cmd3')

w_londiste_remove = List(
        Word('table', w_londiste_remove_table),
        Word('sequence', w_londiste_remove_seq),
        name = 'cmd3')

# londiste
w_londiste = List(
    Word('add', w_londiste_add),
    Word('remove', w_londiste_remove),
    Word('missing', w_done),
    Word('tables', w_done),
    Word('seqs', w_done),
    name = "cmd2")

top_level.add(
    Word('alter', w_alter),
    Word('connect', w_connect),
    Word('create', w_create),
    Word('drop', w_drop),
    Word('install', w_install),
    Word('register', w_register),
    Word('unregister', w_unregister),
    Word('show', w_show),
    Word('exit', w_done),
    Word('londiste', w_londiste),

    Word('select', w_sql),
    w_sql)

##
## Main class for keeping the state.
##

class AdminConsole:
    cur_queue = None
    cur_database = None

    server_version = None
    pgq_version = None

    cmd_file = None
    cmd_str = None

    comp_cache = {
        'comp_pfx': None,
        'comp_list': None,
        'queue_list': None,
        'database_list': None,
        'consumer_list': None,
        'host_list': None,
        'user_list': None,
    }
    db = None
    initial_connstr = None

    rc_hosts = re.compile('\s+')

    def get_queue_list(self):
        q = "select queue_name from pgq.queue order by 1"
        return self._ccache('queue_list', q, 'pgq')

    def get_database_list(self):
        q = "select datname from pg_catalog.pg_database order by 1"
        return self._ccache('database_list', q)

    def get_user_list(self):
        q = "select usename from pg_catalog.pg_user order by 1"
        return self._ccache('user_list', q)

    def get_consumer_list(self):
        q = "select co_name from pgq.consumer order by 1"
        return self._ccache('consumer_list', q, 'pgq')

    def get_node_list(self):
        q = "select distinct node_name from pgq_node.node_location order by 1"
        return self._ccache('node_list', q, 'pgq_node')

    def _new_obj_sql(self, queue, objname, objkind):
        args = {'queue': skytools.quote_literal(queue),
                'obj': objname,
                'ifield': objname + '_name',
                'itable': 'londiste.' + objname + '_info',
                'kind': skytools.quote_literal(objkind),
            }
        q = """select quote_ident(n.nspname) || '.' || quote_ident(r.relname)
            from pg_catalog.pg_class r
            join pg_catalog.pg_namespace n on (n.oid = r.relnamespace)
            left join %(itable)s i
                 on (i.queue_name = %(queue)s and
                     i.%(ifield)s = (n.nspname || '.' || r.relname))
            where r.relkind = %(kind)s
              and n.nspname not in ('pg_catalog', 'information_schema', 'pgq', 'londiste', 'pgq_node', 'pgq_ext')
              and n.nspname !~ 'pg_.*'
              and i.%(ifield)s is null
            union all
            select londiste.quote_fqname(%(ifield)s) from %(itable)s
             where queue_name = %(queue)s and not local
            order by 1 """ % args
        return q

    def get_new_table_list(self):
        if not self.cur_queue:
            return []
        q = self._new_obj_sql(self.cur_queue, 'table', 'r')
        return self._ccache('new_table_list', q, 'londiste')

    def get_new_seq_list(self):
        if not self.cur_queue:
            return []
        q = self._new_obj_sql(self.cur_queue, 'seq', 'S')
        return self._ccache('new_seq_list', q, 'londiste')

    def get_known_table_list(self):
        if not self.cur_queue:
            return []
        qname = skytools.quote_literal(self.cur_queue)
        q = "select londiste.quote_fqname(table_name)"\
            " from londiste.table_info"\
            " where queue_name = %s order by 1" % qname
        return self._ccache('known_table_list', q, 'londiste')

    def get_known_seq_list(self):
        if not self.cur_queue:
            return []
        qname = skytools.quote_literal(self.cur_queue)
        q = "select londiste.quote_fqname(seq_name)"\
            " from londiste.seq_info"\
            " where queue_name = %s order by 1" % qname
        return self._ccache('known_seq_list', q, 'londiste')

    def get_plain_table_list(self):
        q = "select quote_ident(n.nspname) || '.' || quote_ident(r.relname)"\
            " from pg_class r join pg_namespace n on (n.oid = r.relnamespace)"\
            " where r.relkind = 'r' "\
            "   and n.nspname not in ('pg_catalog', 'information_schema', 'pgq', 'londiste', 'pgq_node', 'pgq_ext') "\
            "   and n.nspname !~ 'pg_.*' "\
            " order by 1"
        return self._ccache('plain_table_list', q)

    def get_plain_seq_list(self):
        q = "select quote_ident(n.nspname) || '.' || quote_ident(r.relname)"\
            " from pg_class r join pg_namespace n on (n.oid = r.relnamespace)"\
            " where r.relkind = 'S' "\
            "   and n.nspname not in ('pg_catalog', 'information_schema', 'pgq', 'londiste', 'pgq_node', 'pgq_ext') "\
            " order by 1"
        return self._ccache('plain_seq_list', q)

    def get_batch_list(self):
        if not self.cur_queue:
            return []
        qname = skytools.quote_literal(self.cur_queue)
        q = "select current_batch::text from pgq.get_consumer_info(%s)"\
            " where current_batch is not null order by 1" % qname
        return self._ccache('batch_list', q, 'pgq')

    def _ccache(self, cname, q, req_schema = None):
        if not self.db:
            return []

        # check if schema exists
        if req_schema:
            k = "schema_exists_%s" % req_schema
            ok = self.comp_cache.get(k)
            if ok is None:
                curs = self.db.cursor()
                ok = skytools.exists_schema(curs, req_schema)
                self.comp_cache[k] = ok
            if not ok:
                return []

        # actual completion
        clist = self.comp_cache.get(cname)
        if clist is None:
            curs = self.db.cursor()
            curs.execute(q)
            clist = [r[0] for r in curs.fetchall()]
            self.comp_cache[cname] = clist
        return clist

    def get_host_list(self):
        clist = self.comp_cache.get('host_list')
        if clist is None:
            try:
                f = open('/etc/hosts', 'r')
                clist = []
                while 1:
                    ln = f.readline()
                    if not ln:
                        break
                    ln = ln.strip()
                    if ln == '' or ln[0] == '#':
                        continue
                    lst = self.rc_hosts.split(ln)
                    for h in lst[1:]:
                        if h not in IGNORE_HOSTS:
                            clist.append(h)
                clist.sort()
                self.comp_cache['host_list'] = clist
            except IOError:
                clist = []
        return clist

    def parse_cmdline(self, argv):
        switches = "c:h:p:d:U:f:Q:"
        lswitches = ['help', 'version']
        try:
            opts, args = getopt.getopt(argv, switches, lswitches)
        except getopt.GetoptError, ex:
            print str(ex)
            print "Use --help to see command line options"
            sys.exit(1)

        cstr_map = {
            'dbname': None,
            'host': None,
            'port': None,
            'user': None,
            'password': None,
        }
        cmd_file = cmd_str = None
        for o, a in opts:
            if o == "--help":
                print cmdline_usage
                sys.exit(0)
            elif o == "--version":
                print "qadmin version %s" % __version__
                sys.exit(0)
            elif o == "-h":
                cstr_map['host'] = a
            elif o == "-p":
                cstr_map['port'] = a
            elif o == "-d":
                cstr_map['dbname'] = a
            elif o == "-U":
                cstr_map['user'] = a
            elif o == "-Q":
                self.cur_queue = a
            elif o == "-c":
                self.cmd_str = a
            elif o == "-f":
                self.cmd_file = a

        cstr_list = []
        for k, v in cstr_map.items():
            if v is not None:
                cstr_list.append("%s=%s" % (k, v))
        if len(args) == 1:
            a = args[0]
            if a.find('=') >= 0:
                cstr_list.append(a)
            else:
                cstr_list.append("dbname=%s" % a)
        elif len(args) > 1:
            print "too many arguments, use --help to see syntax"
            sys.exit(1)

        self.initial_connstr = " ".join(cstr_list)

    def db_connect(self, connstr, quiet=False):
        db = skytools.connect_database(connstr)
        db.set_isolation_level(0) # autocommit

        q = "select current_database(), current_setting('server_version')"
        curs = db.cursor()
        curs.execute(q)
        res = curs.fetchone()
        self.cur_database = res[0]
        self.server_version = res[1]
        q = "select pgq.version()"
        try:
            curs.execute(q)
            res = curs.fetchone()
            self.pgq_version = res[0]
        except psycopg2.ProgrammingError:
            self.pgq_version = "<none>"
        if not quiet:
            print "qadmin (%s, server %s, pgq %s)" % (__version__, self.server_version, self.pgq_version)
            #print "Connected to %r" % connstr
        return db

    def run(self, argv):
        self.parse_cmdline(argv)

        if self.cmd_file is not None and self.cmd_str is not None:
            print "cannot handle -c and -f together"
            sys.exit(1)

        # append ; to cmd_str if needed
        if self.cmd_str and not self.cmd_str.rstrip().endswith(';'):
            self.cmd_str += ';'

        cmd_str = self.cmd_str
        if self.cmd_file:
            cmd_str = open(self.cmd_file, "r").read()

        try:
            self.db = self.db_connect(self.initial_connstr, quiet=True)
        except psycopg2.Error, d:
            print str(d).strip()
            sys.exit(1)

        if cmd_str:
            self.exec_string(cmd_str)
        else:
            self.main_loop()

    def main_loop(self):
        readline.parse_and_bind('tab: complete')
        readline.set_completer(self.rl_completer_safe)
        #print 'delims: ', repr(readline.get_completer_delims())
        # remove " from delims
        #readline.set_completer_delims(" \t\n`~!@#$%^&*()-=+[{]}\\|;:',<>/?")

        hist_file = os.path.expanduser("~/.qadmin_history")
        try:
            readline.read_history_file(hist_file)
        except IOError:
            pass

        print "Welcome to qadmin %s (server %s), the PgQ interactive terminal." % (__version__, self.server_version)
        print "Use 'show help;' to see available commands."
        while 1:
            try:
                ln = self.line_input()
                self.exec_string(ln)
            except KeyboardInterrupt:
                print
            except EOFError:
                print
                break
            except psycopg2.Error, d:
                print 'ERROR:', str(d).strip()
            except Exception:
                traceback.print_exc()
            self.reset_comp_cache()

        try:
            readline.write_history_file(hist_file)
        except IOError:
            pass

    def rl_completer(self, curword, state):
        curline = readline.get_line_buffer()
        start = readline.get_begidx()
        end = readline.get_endidx()

        pfx = curline[:start]
        sglist = self.find_suggestions(pfx, curword)
        if state < len(sglist):
            return sglist[state]
        return None

    def rl_completer_safe(self, curword, state):
        try:
            return self.rl_completer(curword, state)
        except BaseException, det:
            print 'got some error', str(det)

    def line_input(self):
        qname = "(noqueue)"
        if self.cur_queue:
            qname = self.cur_queue
        p = "%s@%s> " % (qname, self.cur_database)
        return raw_input(p)

    def sql_words(self, sql):
        return skytools.sql_tokenizer(sql,
                standard_quoting = True,
                fqident = True,
                show_location = True,
                ignore_whitespace = True)

    def reset_comp_cache(self):
        self.comp_cache = {}

    def find_suggestions(self, pfx, curword, params = {}):

        # refresh word cache
        c_pfx = self.comp_cache.get('comp_pfx')
        c_list = self.comp_cache.get('comp_list', [])
        c_pos = self.comp_cache.get('comp_pos')
        if c_pfx != pfx:
            c_list, c_pos = self.find_suggestions_real(pfx, params)
            orig_pos = c_pos
            while c_pos < len(pfx) and pfx[c_pos].isspace():
                c_pos += 1
            #print repr(pfx), orig_pos, c_pos
            self.comp_cache['comp_pfx'] = pfx
            self.comp_cache['comp_list'] = c_list
            self.comp_cache['comp_pos'] = c_pos

        skip = len(pfx) - c_pos
        if skip:
            curword = pfx[c_pos : ] + curword

        # generate suggestions
        wlen = len(curword)
        res = []
        for cword in c_list:
            if curword == cword[:wlen]:
                res.append(cword)

        # resync with readline offset
        if skip:
            res = [s[skip:] for s in res]
        #print '\nfind_suggestions', repr(pfx), repr(curword), repr(res), repr(c_list)
        return res

    def find_suggestions_real(self, pfx, params):
        # find level
        node = top_level
        pos = 0
        xpos = 0
        xnode = node
        for typ, w, pos in self.sql_words(pfx):
            w = normalize_any(typ, w)
            node = node.get_next(typ, w, params)
            if not node:
                break
            xnode = node
            xpos = pos

        # find possible matches
        if xnode:
            return (xnode.get_completions(params), xpos)
        else:
            return ([], xpos)

    def exec_string(self, ln, eof = False):
        node = top_level
        params = {}
        self.tokens = []
        for typ, w, pos in self.sql_words(ln):
            self.tokens.append((typ, w))
            w = normalize_any(typ, w)
            if typ == 'error':
                print 'syntax error 1:', repr(ln)
                return
            onode = node
            node = node.get_next(typ, w, params)
            if not node:
                print "syntax error 2:", repr(ln), repr(typ), repr(w), repr(params)
                return
            if node == top_level:
                self.exec_params(params)
                params = {}
                self.tokens = []
        if eof:
            if params:
                self.exec_params(params)
        elif node != top_level:
            print "multi-line commands not supported:", repr(ln)

    def exec_params(self, params):
        #print 'RUN', params
        cmd = params.get('cmd')
        cmd2 = params.get('cmd2')
        cmd3 = params.get('cmd3')
        if not cmd:
            print 'parse error: no command found'
            return
        if cmd2:
            cmd = "%s_%s" % (cmd, cmd2)
        if cmd3:
            cmd = "%s_%s" % (cmd, cmd3)
        #print 'RUN', repr(params)
        fn = getattr(self, 'cmd_' + cmd, self.execute_sql)
        fn(params)

    def cmd_connect(self, params):
        qname = params.get('queue', self.cur_queue)

        if 'node' in params and not qname:
            print 'node= needs a queue also'
            return

        # load raw connection params
        cdata = []
        for k in ('dbname', 'host', 'port', 'user', 'password'):
            if k in params:
                arg = "%s=%s" % (k, params[k])
                cdata.append(arg)

        # raw connect
        if cdata:
            if 'node' in params:
                print 'node= cannot be used together with raw params'
                return
            cstr = " ".join(cdata)
            self.db = self.db_connect(cstr)

        # connect to queue
        if qname:
            curs = self.db.cursor()
            q = "select queue_name from pgq.get_queue_info(%s)"
            curs.execute(q, [qname])
            res = curs.fetchall()
            if len(res) == 0:
                print 'queue not found'
                return

            if 'node' in params:
                q = "select node_location from pgq_node.get_queue_locations(%s)"\
                    " where node_name = %s"
                curs.execute(q, [qname, params['node']])
                res = curs.fetchall()
                if len(res) == 0:
                    print "node not found"
                    return
                cstr = res[0]['node_location']
                self.db = self.db_connect(cstr)

        # set default queue
        if 'queue' in params:
            self.cur_queue = qname

        print "CONNECT"

    def cmd_show_version (self, params):
        print "qadmin version %s" % __version__
        print "server version %s" % self.server_version
        print "pgq version %s" % self.pgq_version

    def cmd_install(self, params):
        pgq_objs = [
            skytools.DBLanguage("plpgsql"),
            #skytools.DBFunction("txid_current_snapshot", 0, sql_file="txid.sql"),
            skytools.DBSchema("pgq", sql_file="pgq.sql"),
            skytools.DBSchema("pgq_ext", sql_file="pgq_ext.sql"),
            skytools.DBSchema("pgq_node", sql_file="pgq_node.sql"),
            skytools.DBSchema("pgq_coop", sql_file="pgq_coop.sql"),
        ]
        londiste_objs = pgq_objs + [
            skytools.DBSchema("londiste", sql_file="londiste.sql"),
        ]
        mod_map = {
            'londiste': londiste_objs,
            'pgq': pgq_objs,
        }
        mod_name = params['module']
        objs = mod_map[mod_name]
        if not self.db:
            print "no db?"
            return
        curs = self.db.cursor()
        skytools.db_install(curs, objs, None)
        print "INSTALL"

    def cmd_show_queue(self, params):
        queue = params.get('queue')
        if queue is None:
            # "show queue" without args, show all if not connected to
            # specific queue
            queue = self.cur_queue
            if not queue:
                queue = '*'
        curs = self.db.cursor()
        fields = [
            "queue_name",
            "queue_cur_table || '/' || queue_ntables as tables",
            "queue_ticker_max_count as max_count",
            "queue_ticker_max_lag as max_lag",
            "queue_ticker_idle_period as idle_period",
            "queue_ticker_paused as paused",
            "ticker_lag",
            "ev_per_sec",
            "ev_new",
        ]
        pfx = "select " + ",".join(fields)

        if queue == '*':
            q = pfx + " from pgq.get_queue_info()"
            curs.execute(q)
        else:
            q = pfx + " from pgq.get_queue_info(%s)"
            curs.execute(q, [queue])

        display_result(curs, 'Queue "%s":' % queue)

    def cmd_show_consumer(self, params):
        """Show consumer status"""
        consumer = params.get('consumer', '*')
        queue = params.get('queue', '*')

        q_queue = (queue != '*' and queue or None)
        q_consumer = (consumer != '*' and consumer or None)

        curs = self.db.cursor()
        q = "select * from pgq.get_consumer_info(%s, %s)"
        curs.execute(q, [q_queue, q_consumer])

        display_result(curs, 'Consumer "%s" on queue "%s":' % (consumer, queue))

    def cmd_show_node(self, params):
        """Show node information."""

        # TODO: This should additionally show node roles, lags and hierarchy.
        # Similar to londiste "status".

        node = params.get('node', '*')
        queue = params.get('queue', '*')

        q_queue = (queue != '*' and queue or None)
        q_node = (node != '*' and node or None)

        curs = self.db.cursor()
        q = """select queue_name, node_name, node_location, dead
               from pgq_node.node_location
               where node_name = coalesce(%s, node_name)
                     and queue_name = coalesce(%s, queue_name)
               order by 1,2"""
        curs.execute(q, [q_node, q_queue])

        display_result(curs, 'Node "%s" on queue "%s":' % (node, queue))

    def cmd_show_batch(self, params):
        batch_id = params.get('batch_id')
        consumer = params.get('consumer')
        queue = self.cur_queue
        if not queue:
            print 'No default queue'
            return
        curs = self.db.cursor()
        if consumer:
            q = "select current_batch from pgq.get_consumer_info(%s, %s)"
            curs.execute(q, [queue, consumer])
            res = curs.fetchall()
            if len(res) != 1:
                print 'no such consumer'
                return
            batch_id = res[0]['current_batch']
            if batch_id is None:
                print 'consumer has no open batch'
                return

        q = "select * from pgq.get_batch_events(%s)"
        curs.execute(q, [batch_id])

        display_result(curs, 'Batch events:')

    def cmd_register_consumer(self, params):
        queue = params.get("queue", self.cur_queue)
        if not queue:
            print 'No queue specified'
            return
        at_tick = params.get('at_tick')
        copy_reg = params.get('copy_reg')
        consumer = params['consumer']
        curs = self.db.cursor()

        # copy other registration
        if copy_reg:
            q = "select coalesce(next_tick, last_tick) as pos from pgq.get_consumer_info(%s, %s)"
            curs.execute(q, [queue, copy_reg])
            reg = curs.fetchone()
            if not reg:
                print "Consumer %s not registered on queue %d" % (copy_reg, queue)
                return
            at_tick = reg['pos']

        # avoid double reg if specific pos is not requested
        if not at_tick:
            q = "select * from pgq.get_consumer_info(%s, %s)"
            curs.execute(q, [queue, consumer])
            if curs.fetchone():
                print 'Consumer already registered'
                return

        if at_tick:
            q = "select * from pgq.register_consumer_at(%s, %s, %s)"
            curs.execute(q, [queue, consumer, int(at_tick)])
        else:
            q = "select * from pgq.register_consumer(%s, %s)"
            curs.execute(q, [queue, consumer])
        print "REGISTER"

    def cmd_register_subconsumer(self, params):
        queue = params.get("queue", self.cur_queue)
        if not queue:
            print 'No queue specified'
            return
        subconsumer = params['subconsumer']
        consumer = params.get("consumer")
        if not consumer:
            print 'No consumer specified'
            return
        curs = self.db.cursor()

        _subcon_name = '%s.%s' % (consumer, subconsumer)

        q = "select * from pgq.get_consumer_info(%s, %s)"
        curs.execute(q, [queue, _subcon_name])
        if curs.fetchone():
            print 'Subconsumer already registered'
            return

        q = "select * from pgq_coop.register_subconsumer(%s, %s, %s)"
        curs.execute(q, [queue, consumer, subconsumer])
        print "REGISTER"

    def cmd_unregister_consumer(self, params):
        queue = params.get("queue", self.cur_queue)
        if not queue:
            print 'No queue specified'
            return
        consumer = params['consumer']
        curs = self.db.cursor()
        if consumer == '*':
            q = 'select consumer_name from pgq.get_consumer_info(%s)'
            curs.execute(q, [queue])
            consumers = [row['consumer_name'] for row in curs.fetchall()]
        else:
            consumers = [consumer]
        q = "select * from pgq.unregister_consumer(%s, %s)"
        for consumer in consumers:
            curs.execute(q, [queue, consumer])
        print "UNREGISTER"

    def cmd_unregister_subconsumer(self, params):
        queue = params.get("queue", self.cur_queue)
        if not queue:
            print 'No queue specified'
            return
        subconsumer = params["subconsumer"]
        consumer = params['consumer']
        batch_handling = int(params.get('close') is not None)
        curs = self.db.cursor()
        if subconsumer == '*':
            q = 'select consumer_name from pgq.get_consumer_info(%s)'
            curs.execute(q, [queue])
            subconsumers = [row['consumer_name'].split('.')[1]
                           for row in curs.fetchall()
                           if row['consumer_name'].startswith('%s.' % consumer)]
        else:
            subconsumers = [subconsumer]
        q = "select * from pgq_coop.unregister_subconsumer(%s, %s, %s, %s)"
        for subconsumer in subconsumers:
            curs.execute(q, [queue, consumer, subconsumer, batch_handling])
        print "UNREGISTER"

    def cmd_create_queue(self, params):
        curs = self.db.cursor()
        q = "select * from pgq.get_queue_info(%(queue)s)"
        curs.execute(q, params)
        if curs.fetchone():
            print "Queue already exists"
            return
        q = "select * from pgq.create_queue(%(queue)s)"
        curs.execute(q, params)
        print "CREATE"

    def cmd_drop_queue(self, params):
        curs = self.db.cursor()
        q = "select * from pgq.drop_queue(%(queue)s)"
        curs.execute(q, params)
        print "DROP"

    def cmd_alter_queue(self, params):
        """Alter queue parameters, accepts * for all queues"""
        queue = params.get('queue')
        curs = self.db.cursor()
        if queue == '*':
            # operate on list of queues
            q = "select queue_name from pgq.get_queue_info()"
            curs.execute(q)
            qlist = [ r[0] for r in curs.fetchall() ]
        else:
            # just single queue specified
            qlist = [ queue ]

        for qname in qlist:
            params['queue'] = qname

            # loop through the parameters, passing any unrecognized
            # key down pgq.set_queue_config
            for k in params:
                if k in ('queue', 'cmd', 'cmd2'):
                    continue

                q = "select * from pgq.set_queue_config" \
                    "(%%(queue)s, '%s', %%(%s)s)" % (k, k)

                curs.execute(q, params)
        print "ALTER"

    def cmd_show_help(self, params):
        print __doc__

    def cmd_exit(self, params):
        sys.exit(0)

    ##
    ## Londiste
    ##

    def cmd_londiste_missing(self, params):
        """Show missing objects."""

        queue = self.cur_queue

        curs = self.db.cursor()
        q = """select * from londiste.local_show_missing(%s)"""
        curs.execute(q, [queue])

        display_result(curs, 'Missing objects on queue "%s":' % (queue))

    def cmd_londiste_tables(self, params):
        """Show local tables."""

        queue = self.cur_queue

        curs = self.db.cursor()
        q = """select * from londiste.get_table_list(%s) where local"""
        curs.execute(q, [queue])

        display_result(curs, 'Local tables on queue "%s":' % (queue))

    def cmd_londiste_seqs(self, params):
        """Show local seqs."""

        queue = self.cur_queue

        curs = self.db.cursor()
        q = """select * from londiste.get_seq_list(%s) where local"""
        curs.execute(q, [queue])

        display_result(curs, 'Sequences on queue "%s":' % (queue))

    def cmd_londiste_add_table(self, params):
        """Add table."""

        args = []
        for a in ('skip_truncate', 'expect_sync', 'backup', 'no_triggers', 'skip'):
            if a in params:
                args.append(a)
        for a in ('tgflags', 'ignore', 'pkey', 'when',
                  'ev_type', 'ev_data',
                  'ev_extra1', 'ev_extra2', 'ev_extra3', 'ev_extra4'):
            if a in params:
                args.append("%s=%s" % (a, params[a]))

        curs = self.db.cursor()
        q = """select * from londiste.local_add_table(%s, %s, %s)"""
        for tbl in params['tables']:
            curs.execute(q, [self.cur_queue, tbl, args])
            res = curs.fetchone()
            print res[0], res[1]
        print 'ADD_TABLE'

    def cmd_londiste_remove_table(self, params):
        """Remove table."""

        curs = self.db.cursor()
        q = """select * from londiste.local_remove_table(%s, %s)"""
        for tbl in params['tables']:
            curs.execute(q, [self.cur_queue, tbl])
            res = curs.fetchone()
            print res[0], res[1]
        print 'REMOVE_TABLE'

    def cmd_londiste_add_seq(self, params):
        """Add seq."""

        curs = self.db.cursor()
        q = """select * from londiste.local_add_seq(%s, %s)"""
        for seq in params['seqs']:
            curs.execute(q, [self.cur_queue, seq])
            res = curs.fetchone()
            print res[0], res[1]
        print 'ADD_SEQ'

    def cmd_londiste_remove_seq(self, params):
        """Remove seq."""

        curs = self.db.cursor()
        q = """select * from londiste.local_remove_seq(%s, %s)"""
        for seq in params['seqs']:
            curs.execute(q, [self.cur_queue, seq])
            res = curs.fetchone()
            print res[0], res[1]
        print 'REMOVE_SEQ:', res[0], res[1]

    ## generic info

    def cmd_show_table(self, params):
        print '-' * 64
        tbl = params['table']
        curs = self.db.cursor()
        s = skytools.TableStruct(curs, tbl)
        s.create(fakecurs(), skytools.T_ALL)
        print '-' * 64

    def cmd_show_sequence(self, params):
        print '-' * 64
        seq = params['seq']
        curs = self.db.cursor()
        s = skytools.SeqStruct(curs, seq)
        s.create(fakecurs(), skytools.T_ALL)
        print '-' * 64

    ## sql pass-through

    def execute_sql(self, params):
        tks = [tk[1] for tk in self.tokens]
        sql = ' '.join(tks)

        curs = self.db.cursor()
        curs.execute(sql)

        if curs.description:
            display_result(curs, None)
        print curs.statusmessage

class fakecurs:
    def execute(self, sql):
        print sql

def main():
    global script
    script = AdminConsole()
    script.run(sys.argv[1:])

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = setadm
#! /usr/bin/env python

"""SetAdmin launcher.
"""

import sys

import pkgloader
pkgloader.require('skytools', '3.0')

import pgq.cascade.admin

if __name__ == '__main__':
    script = pgq.cascade.admin.CascadeAdmin('cascade_admin', 'node_db', sys.argv[1:], worker_setup = False)
    script.start()


########NEW FILE########
__FILENAME__ = adminscript
#! /usr/bin/env python

"""Admin scripting.
"""

import sys, inspect

import skytools

__all__ = ['AdminScript']

class AdminScript(skytools.DBScript):
    """Contains common admin script tools.

    Second argument (first is .ini file) is taken as command
    name.  If class method 'cmd_' + arg exists, it is called,
    otherwise error is given.
    """
    commands_without_pidfile = {}
    def __init__(self, service_name, args):
        """AdminScript init."""
        skytools.DBScript.__init__(self, service_name, args)

        if len(self.args) < 2:
            self.log.error("need command")
            sys.exit(1)

        cmd = self.args[1]
        if cmd in self.commands_without_pidfile:
            self.pidfile = None

        if self.pidfile:
            self.pidfile = self.pidfile + ".admin"

    def work(self):
        """Non-looping work function, calls command function."""

        self.set_single_loop(1)

        cmd = self.args[1]
        cmdargs = self.args[2:]

        # find function
        fname = "cmd_" + cmd.replace('-', '_')
        if not hasattr(self, fname):
            self.log.error('bad subcommand, see --help for usage')
            sys.exit(1)
        fn = getattr(self, fname)

        # check if correct number of arguments
        (args, varargs, varkw, defaults) = inspect.getargspec(fn)
        n_args = len(args) - 1 # drop 'self'
        if varargs is None and n_args != len(cmdargs):
            helpstr = ""
            if n_args:
                helpstr = ": " + " ".join(args[1:])
            self.log.error("command '%s' got %d args, but expects %d%s"
                    % (cmd, len(cmdargs), n_args, helpstr))
            sys.exit(1)

        # run command
        fn(*cmdargs)

    def fetch_list(self, db, sql, args, keycol = None):
        """Fetch a resultset from db, optionally turning it into value list."""
        curs = db.cursor()
        curs.execute(sql, args)
        rows = curs.fetchall()
        db.commit()
        if not keycol:
            res = rows
        else:
            res = [r[keycol] for r in rows]
        return res

    def display_table(self, db, desc, sql, args = [], fields = [],
                      fieldfmt = {}):
        """Display multirow query as a table."""

        self.log.debug("display_table: %s" % skytools.quote_statement(sql, args))
        curs = db.cursor()
        curs.execute(sql, args)
        rows = curs.fetchall()
        db.commit()
        if len(rows) == 0:
            return 0

        if not fields:
            fields = [f[0] for f in curs.description]

        widths = [15] * len(fields)
        for row in rows:
            for i, k in enumerate(fields):
                rlen = row[k] and len(str(row[k])) or 0
                widths[i] = widths[i] > rlen and widths[i] or rlen
        widths = [w + 2 for w in widths]

        fmt = '%%-%ds' * (len(widths) - 1) + '%%s'
        fmt = fmt % tuple(widths[:-1])
        if desc:
            print(desc)
        print(fmt % tuple(fields))
        print(fmt % tuple([ '-' * (w - 2) for w in widths ]))
        #print(fmt % tuple(['-'*15] * len(fields)))
        for row in rows:
            vals = []
            for field in fields:
                val = row[field]
                if field in fieldfmt:
                    val = fieldfmt[field](val)
                vals.append(val)
            print(fmt % tuple(vals))
        print('\n')
        return 1

    def exec_stmt(self, db, sql, args):
        """Run regular non-query SQL on db."""
        self.log.debug("exec_stmt: %s" % skytools.quote_statement(sql, args))
        curs = db.cursor()
        curs.execute(sql, args)
        db.commit()

    def exec_query(self, db, sql, args):
        """Run regular query SQL on db."""
        self.log.debug("exec_query: %s" % skytools.quote_statement(sql, args))
        curs = db.cursor()
        curs.execute(sql, args)
        res = curs.fetchall()
        db.commit()
        return res

########NEW FILE########
__FILENAME__ = apipkg
"""
apipkg: control the exported namespace of a python package.

see http://pypi.python.org/pypi/apipkg

(c) holger krekel, 2009 - MIT license
"""
import os
import sys
from types import ModuleType

__version__ = '1.2.dev6'

def initpkg(pkgname, exportdefs, attr=dict()):
    """ initialize given package from the export definitions. """
    oldmod = sys.modules.get(pkgname)
    d = {}
    f = getattr(oldmod, '__file__', None)
    if f:
        f = os.path.abspath(f)
    d['__file__'] = f
    if hasattr(oldmod, '__version__'):
        d['__version__'] = oldmod.__version__
    if hasattr(oldmod, '__loader__'):
        d['__loader__'] = oldmod.__loader__
    if hasattr(oldmod, '__path__'):
        d['__path__'] = [os.path.abspath(p) for p in oldmod.__path__]
    if '__doc__' not in exportdefs and getattr(oldmod, '__doc__', None):
        d['__doc__'] = oldmod.__doc__
    d.update(attr)
    if hasattr(oldmod, "__dict__"):
        oldmod.__dict__.update(d)
    mod = ApiModule(pkgname, exportdefs, implprefix=pkgname, attr=d)
    sys.modules[pkgname]  = mod

def importobj(modpath, attrname):
    module = __import__(modpath, None, None, ['__doc__'])
    if not attrname:
        return module

    retval = module
    names = attrname.split(".")
    for x in names:
        retval = getattr(retval, x)
    return retval

class ApiModule(ModuleType):
    def __docget(self):
        try:
            return self.__doc
        except AttributeError:
            if '__doc__' in self.__map__:
                return self.__makeattr('__doc__')
    def __docset(self, value):
        self.__doc = value
    __doc__ = property(__docget, __docset)

    def __init__(self, name, importspec, implprefix=None, attr=None):
        self.__name__ = name
        self.__all__ = [x for x in importspec if x != '__onfirstaccess__']
        self.__map__ = {}
        self.__implprefix__ = implprefix or name
        if attr:
            for name, val in attr.items():
                #print "setting", self.__name__, name, val
                setattr(self, name, val)
        for name, importspec in importspec.items():
            if isinstance(importspec, dict):
                subname = '%s.%s'%(self.__name__, name)
                apimod = ApiModule(subname, importspec, implprefix)
                sys.modules[subname] = apimod
                setattr(self, name, apimod)
            else:
                parts = importspec.split(':')
                modpath = parts.pop(0)
                attrname = parts and parts[0] or ""
                if modpath[0] == '.':
                    modpath = implprefix + modpath

                if not attrname:
                    subname = '%s.%s'%(self.__name__, name)
                    apimod = AliasModule(subname, modpath)
                    sys.modules[subname] = apimod
                    if '.' not in name:
                        setattr(self, name, apimod)
                else:
                    self.__map__[name] = (modpath, attrname)

    def __repr__(self):
        l = []
        if hasattr(self, '__version__'):
            l.append("version=" + repr(self.__version__))
        if hasattr(self, '__file__'):
            l.append('from ' + repr(self.__file__))
        if l:
            return '<ApiModule %r %s>' % (self.__name__, " ".join(l))
        return '<ApiModule %r>' % (self.__name__,)

    def __makeattr(self, name):
        """lazily compute value for name or raise AttributeError if unknown."""
        #print "makeattr", self.__name__, name
        target = None
        if '__onfirstaccess__' in self.__map__:
            target = self.__map__.pop('__onfirstaccess__')
            importobj(*target)()
        try:
            modpath, attrname = self.__map__[name]
        except KeyError:
            if target is not None and name != '__onfirstaccess__':
                # retry, onfirstaccess might have set attrs
                return getattr(self, name)
            raise AttributeError(name)
        else:
            result = importobj(modpath, attrname)
            setattr(self, name, result)
            try:
                del self.__map__[name]
            except KeyError:
                pass # in a recursive-import situation a double-del can happen
            return result

    __getattr__ = __makeattr

    def __dict__(self):
        # force all the content of the module to be loaded when __dict__ is read
        dictdescr = ModuleType.__dict__['__dict__']
        dict = dictdescr.__get__(self)
        if dict is not None:
            hasattr(self, 'some')
            for name in self.__all__:
                try:
                    self.__makeattr(name)
                except AttributeError:
                    pass
        return dict
    __dict__ = property(__dict__)


def AliasModule(modname, modpath, attrname=None):
    mod = []

    def getmod():
        if not mod:
            x = importobj(modpath, None)
            if attrname is not None:
                x = getattr(x, attrname)
            mod.append(x)
        return mod[0]

    class AliasModule(ModuleType):

        def __repr__(self):
            x = modpath
            if attrname:
                x += "." + attrname
            return '<AliasModule %r for %r>' % (modname, x)

        def __getattribute__(self, name):
            return getattr(getmod(), name)

        def __setattr__(self, name, value):
            setattr(getmod(), name, value)

        def __delattr__(self, name):
            delattr(getmod(), name)

    return AliasModule(modname)

########NEW FILE########
__FILENAME__ = checker
#! /usr/bin/env python

"""Catch moment when tables are in sync on master and slave.
"""

import sys, time, os, subprocess

import pkgloader
pkgloader.require('skytools', '3.0')
import skytools

class TableRepair:
    """Checks that tables in two databases are in sync."""

    def __init__(self, table_name, log):
        self.table_name = table_name
        self.fq_table_name = skytools.quote_fqident(table_name)
        self.log = log
        self.reset()

    def reset(self):
        self.cnt_insert = 0
        self.cnt_update = 0
        self.cnt_delete = 0
        self.total_src = 0
        self.total_dst = 0
        self.pkey_list = []
        self.common_fields = []
        self.apply_fixes = False
        self.apply_cursor = None

    def do_repair(self, src_db, dst_db, where, pfx = 'repair', apply_fixes = False):
        """Actual comparision."""

        self.reset()

        src_curs = src_db.cursor()
        dst_curs = dst_db.cursor()

        self.apply_fixes = apply_fixes
        if apply_fixes:
            self.apply_cursor = dst_curs

        self.log.info('Checking %s' % self.table_name)

        copy_tbl = self.gen_copy_tbl(src_curs, dst_curs, where)

        dump_src = "%s.%s.src" % (pfx, self.table_name)
        dump_dst = "%s.%s.dst" % (pfx, self.table_name)
        fix = "%s.%s.fix" % (pfx, self.table_name)

        self.log.info("Dumping src table: %s" % self.table_name)
        self.dump_table(copy_tbl, src_curs, dump_src)
        src_db.commit()
        self.log.info("Dumping dst table: %s" % self.table_name)
        self.dump_table(copy_tbl, dst_curs, dump_dst)
        dst_db.commit()

        self.log.info("Sorting src table: %s" % self.table_name)
        self.do_sort(dump_src, dump_src + '.sorted')

        self.log.info("Sorting dst table: %s" % self.table_name)
        self.do_sort(dump_dst, dump_dst + '.sorted')

        self.dump_compare(dump_src + ".sorted", dump_dst + ".sorted", fix)

        os.unlink(dump_src)
        os.unlink(dump_dst)
        os.unlink(dump_src + ".sorted")
        os.unlink(dump_dst + ".sorted")

        if apply_fixes:
            dst_db.commit()

    def do_sort(self, src, dst):
        p = subprocess.Popen(["sort", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        s_ver = p.communicate()[0]
        del p

        xenv = os.environ.copy()
        xenv['LANG'] = 'C'
        xenv['LC_ALL'] = 'C'

        cmdline = ['sort', '-T', '.']
        if s_ver.find("coreutils") > 0:
            cmdline.append('-S')
            cmdline.append('30%')
        cmdline.append('-o')
        cmdline.append(dst)
        cmdline.append(src)
        p = subprocess.Popen(cmdline, env = xenv)
        if p.wait() != 0:
            raise Exception('sort failed')

    def gen_copy_tbl(self, src_curs, dst_curs, where):
        """Create COPY expession from common fields."""
        self.pkey_list = skytools.get_table_pkeys(src_curs, self.table_name)
        dst_pkey = skytools.get_table_pkeys(dst_curs, self.table_name)
        if dst_pkey != self.pkey_list:
            self.log.error('pkeys do not match')
            sys.exit(1)

        src_cols = skytools.get_table_columns(src_curs, self.table_name)
        dst_cols = skytools.get_table_columns(dst_curs, self.table_name)
        field_list = []
        for f in self.pkey_list:
            field_list.append(f)
        for f in src_cols:
            if f in self.pkey_list:
                continue
            if f in dst_cols:
                field_list.append(f)

        self.common_fields = field_list

        fqlist = [skytools.quote_ident(col) for col in field_list]

        tbl_expr = "select %s from %s" % (",".join(fqlist), self.fq_table_name)
        if where:
            tbl_expr += ' where ' + where
        tbl_expr = "COPY (%s) TO STDOUT" % tbl_expr

        self.log.debug("using copy expr: %s" % tbl_expr)

        return tbl_expr

    def dump_table(self, copy_cmd, curs, fn):
        """Dump table to disk."""
        f = open(fn, "w", 64*1024)
        curs.copy_expert(copy_cmd, f)
        self.log.info('%s: Got %d bytes' % (self.table_name, f.tell()))
        f.close()

    def get_row(self, ln):
        """Parse a row into dict."""
        if not ln:
            return None
        t = ln[:-1].split('\t')
        row = {}
        for i in range(len(self.common_fields)):
            row[self.common_fields[i]] = t[i]
        return row

    def dump_compare(self, src_fn, dst_fn, fix):
        """Dump + compare single table."""
        self.log.info("Comparing dumps: %s" % self.table_name)
        f1 = open(src_fn, "r", 64*1024)
        f2 = open(dst_fn, "r", 64*1024)
        src_ln = f1.readline()
        dst_ln = f2.readline()
        if src_ln: self.total_src += 1
        if dst_ln: self.total_dst += 1

        if os.path.isfile(fix):
            os.unlink(fix)

        while src_ln or dst_ln:
            keep_src = keep_dst = 0
            if src_ln != dst_ln:
                src_row = self.get_row(src_ln)
                dst_row = self.get_row(dst_ln)

                diff = self.cmp_keys(src_row, dst_row)
                if diff > 0:
                    # src > dst
                    self.got_missed_delete(dst_row, fix)
                    keep_src = 1
                elif diff < 0:
                    # src < dst
                    self.got_missed_insert(src_row, fix)
                    keep_dst = 1
                else:
                    if self.cmp_data(src_row, dst_row) != 0:
                        self.got_missed_update(src_row, dst_row, fix)

            if not keep_src:
                src_ln = f1.readline()
                if src_ln: self.total_src += 1
            if not keep_dst:
                dst_ln = f2.readline()
                if dst_ln: self.total_dst += 1

        self.log.info("finished %s: src: %d rows, dst: %d rows,"\
                    " missed: %d inserts, %d updates, %d deletes" % (
                self.table_name, self.total_src, self.total_dst,
                self.cnt_insert, self.cnt_update, self.cnt_delete))

    def got_missed_insert(self, src_row, fn):
        """Create sql for missed insert."""
        self.cnt_insert += 1
        fld_list = self.common_fields
        fq_list = []
        val_list = []
        for f in fld_list:
            fq_list.append(skytools.quote_ident(f))
            v = skytools.unescape_copy(src_row[f])
            val_list.append(skytools.quote_literal(v))
        q = "insert into %s (%s) values (%s);" % (
                self.fq_table_name, ", ".join(fq_list), ", ".join(val_list))
        self.show_fix(q, 'insert', fn)

    def got_missed_update(self, src_row, dst_row, fn):
        """Create sql for missed update."""
        self.cnt_update += 1
        fld_list = self.common_fields
        set_list = []
        whe_list = []
        for f in self.pkey_list:
            self.addcmp(whe_list, skytools.quote_ident(f), skytools.unescape_copy(src_row[f]))
        for f in fld_list:
            v1 = src_row[f]
            v2 = dst_row[f]
            if self.cmp_value(v1, v2) == 0:
                continue

            self.addeq(set_list, skytools.quote_ident(f), skytools.unescape_copy(v1))
            self.addcmp(whe_list, skytools.quote_ident(f), skytools.unescape_copy(v2))

        q = "update only %s set %s where %s;" % (
                self.fq_table_name, ", ".join(set_list), " and ".join(whe_list))
        self.show_fix(q, 'update', fn)

    def got_missed_delete(self, dst_row, fn):
        """Create sql for missed delete."""
        self.cnt_delete += 1
        whe_list = []
        for f in self.pkey_list:
            self.addcmp(whe_list, skytools.quote_ident(f), skytools.unescape_copy(dst_row[f]))
        q = "delete from only %s where %s;" % (self.fq_table_name, " and ".join(whe_list))
        self.show_fix(q, 'delete', fn)

    def show_fix(self, q, desc, fn):
        """Print/write/apply repair sql."""
        self.log.debug("missed %s: %s" % (desc, q))
        open(fn, "a").write("%s\n" % q)

        if self.apply_fixes:
            self.apply_cursor.execute(q)

    def addeq(self, list, f, v):
        """Add quoted SET."""
        vq = skytools.quote_literal(v)
        s = "%s = %s" % (f, vq)
        list.append(s)

    def addcmp(self, list, f, v):
        """Add quoted comparision."""
        if v is None:
            s = "%s is null" % f
        else:
            vq = skytools.quote_literal(v)
            s = "%s = %s" % (f, vq)
        list.append(s)

    def cmp_data(self, src_row, dst_row):
        """Compare data field-by-field."""
        for k in self.common_fields:
            v1 = src_row[k]
            v2 = dst_row[k]
            if self.cmp_value(v1, v2) != 0:
                return -1
        return 0

    def cmp_value(self, v1, v2):
        """Compare single field, tolerates tz vs notz dates."""
        if v1 == v2:
            return 0

        # try to work around tz vs. notz
        z1 = len(v1)
        z2 = len(v2)
        if z1 == z2 + 3 and z2 >= 19 and v1[z2] == '+':
            v1 = v1[:-3]
            if v1 == v2:
                return 0
        elif z1 + 3 == z2 and z1 >= 19 and v2[z1] == '+':
            v2 = v2[:-3]
            if v1 == v2:
                return 0

        return -1

    def cmp_keys(self, src_row, dst_row):
        """Compare primary keys of the rows.
        
        Returns 1 if src > dst, -1 if src < dst and 0 if src == dst"""

        # None means table is done.  tag it larger than any existing row.
        if src_row is None:
            if dst_row is None:
                return 0
            return 1
        elif dst_row is None:
            return -1

        for k in self.pkey_list:
            v1 = src_row[k]
            v2 = dst_row[k]
            if v1 < v2:
                return -1
            elif v1 > v2:
                return 1
        return 0


class Syncer(skytools.DBScript):
    """Checks that tables in two databases are in sync."""
    lock_timeout = 10
    ticker_lag_limit = 20
    consumer_lag_limit = 20

    def sync_table(self, cstr1, cstr2, queue_name, consumer_name, table_name):
        """Syncer main function.

        Returns (src_db, dst_db) that are in transaction
        where table should be in sync.
        """

        setup_db = self.get_database('setup_db', connstr = cstr1, autocommit = 1)
        lock_db = self.get_database('lock_db', connstr = cstr1)

        src_db = self.get_database('src_db', connstr = cstr1,
                isolation_level = skytools.I_REPEATABLE_READ)
        dst_db = self.get_database('dst_db', connstr = cstr2,
                isolation_level = skytools.I_REPEATABLE_READ)

        lock_curs = lock_db.cursor()
        setup_curs = setup_db.cursor()
        src_curs = src_db.cursor()
        dst_curs = dst_db.cursor()

        self.check_consumer(setup_curs, queue_name, consumer_name)

        # lock table in separate connection
        self.log.info('Locking %s' % table_name)
        self.set_lock_timeout(lock_curs)
        lock_time = time.time()
        lock_curs.execute("LOCK TABLE %s IN SHARE MODE" % skytools.quote_fqident(table_name))

        # now wait until consumer has updated target table until locking
        self.log.info('Syncing %s' % table_name)

        # consumer must get further than this tick
        tick_id = self.force_tick(setup_curs, queue_name)
        # try to force second tick also
        self.force_tick(setup_curs, queue_name)

        # take server time
        setup_curs.execute("select to_char(now(), 'YYYY-MM-DD HH24:MI:SS.MS')")
        tpos = setup_curs.fetchone()[0]
        # now wait
        while 1:
            time.sleep(0.5)

            q = "select now() - lag > timestamp %s, now(), lag from pgq.get_consumer_info(%s, %s)"
            setup_curs.execute(q, [tpos, queue_name, consumer_name])
            res = setup_curs.fetchall()
            if len(res) == 0:
                raise Exception('No such consumer: %s/%s' % (queue_name, consumer_name))
            row = res[0]
            self.log.debug("tpos=%s now=%s lag=%s ok=%s" % (tpos, row[1], row[2], row[0]))
            if row[0]:
                break

            # limit lock time
            if time.time() > lock_time + self.lock_timeout:
                self.log.error('Consumer lagging too much, exiting')
                lock_db.rollback()
                sys.exit(1)

        # take snapshot on provider side
        src_db.commit()
        src_curs.execute("SELECT 1")

        # take snapshot on subscriber side
        dst_db.commit()
        dst_curs.execute("SELECT 1")

        # release lock
        lock_db.commit()

        self.close_database('setup_db')
        self.close_database('lock_db')

        return (src_db, dst_db)

    def set_lock_timeout(self, curs):
        ms = int(1000 * self.lock_timeout)
        if ms > 0:
            q = "SET LOCAL statement_timeout = %d" % ms
            self.log.debug(q)
            curs.execute(q)

    def check_consumer(self, curs, queue_name, consumer_name):
        """ Before locking anything check if consumer is working ok.
        """
        self.log.info("Queue: %s Consumer: %s" % (queue_name, consumer_name))

        curs.execute('select current_database()')
        self.log.info('Actual db: %s' % curs.fetchone()[0])

        # get ticker lag
        q = "select extract(epoch from ticker_lag) from pgq.get_queue_info(%s);"
        curs.execute(q, [queue_name])
        ticker_lag = curs.fetchone()[0]
        self.log.info("Ticker lag: %s" % ticker_lag)
        # get consumer lag
        q = "select extract(epoch from lag) from pgq.get_consumer_info(%s, %s);"
        curs.execute(q, [queue_name, consumer_name])
        res = curs.fetchall()
        if len(res) == 0:
            self.log.error('check_consumer: No such consumer: %s/%s' % (queue_name, consumer_name))
            sys.exit(1)
        consumer_lag = res[0][0]

        # check that lag is acceptable
        self.log.info("Consumer lag: %s" % consumer_lag)
        if consumer_lag > ticker_lag + 10:
            self.log.error('Consumer lagging too much, cannot proceed')
            sys.exit(1)

    def force_tick(self, curs, queue_name):
        """ Force tick into source queue so that consumer can move on faster
        """
        q = "select pgq.force_tick(%s)"
        curs.execute(q, [queue_name])
        res = curs.fetchone()
        cur_pos = res[0]

        start = time.time()
        while 1:
            time.sleep(0.5)
            curs.execute(q, [queue_name])
            res = curs.fetchone()
            if res[0] != cur_pos:
                # new pos
                return res[0]

            # dont loop more than 10 secs
            dur = time.time() - start
            if dur > 10 and not self.options.force:
                raise Exception("Ticker seems dead")


class Checker(Syncer):
    """Checks that tables in two databases are in sync.
    
    Config options::

        ## data_checker ##
        confdb = dbname=confdb host=confdb.service

        extra_connstr = user=marko

        # one of: compare, repair, repair-apply, compare-repair-apply
        check_type = compare

        # random params used in queries
        cluster_name =
        instance_name =
        proxy_host =
        proxy_db =

        # list of tables to be compared
        table_list = foo, bar, baz

        where_expr = (hashtext(key_user_name) & %%(max_slot)s) in (%%(slots)s)

        # gets no args
        source_query =
         select h.hostname, d.db_name
           from dba.cluster c
                join dba.cluster_host ch on (ch.key_cluster = c.id_cluster)
                join conf.host h on (h.id_host = ch.key_host)
                join dba.database d on (d.key_host = ch.key_host)
          where c.db_name = '%(cluster_name)s'
            and c.instance_name = '%(instance_name)s'
            and d.mk_db_type = 'partition'
            and d.mk_db_status = 'active'
          order by d.db_name, h.hostname


        target_query =
            select db_name, hostname, slots, max_slot
              from dba.get_cross_targets(%%(hostname)s, %%(db_name)s, '%(proxy_host)s', '%(proxy_db)s')

        consumer_query =
            select q.queue_name, c.consumer_name
              from conf.host h
              join dba.database d on (d.key_host = h.id_host)
              join dba.pgq_queue q on (q.key_database = d.id_database)
              join dba.pgq_consumer c on (c.key_queue = q.id_queue)
             where h.hostname = %%(hostname)s
               and d.db_name = %%(db_name)s
               and q.queue_name like 'xm%%%%'
    """

    def __init__(self, args):
        """Checker init."""
        Syncer.__init__(self, 'data_checker', args)
        self.set_single_loop(1)
        self.log.info('Checker starting %s' % str(args))

        self.lock_timeout = self.cf.getfloat('lock_timeout', 10)

        self.table_list = self.cf.getlist('table_list')

    def work(self):
        """Syncer main function."""

        source_query = self.cf.get('source_query')
        target_query = self.cf.get('target_query')
        consumer_query = self.cf.get('consumer_query')
        where_expr = self.cf.get('where_expr')
        extra_connstr = self.cf.get('extra_connstr')

        check = self.cf.get('check_type', 'compare')

        confdb = self.get_database('confdb', autocommit=1)
        curs = confdb.cursor()

        curs.execute(source_query)
        for src_row in curs.fetchall():
            s_host = src_row['hostname']
            s_db = src_row['db_name']

            curs.execute(consumer_query, src_row)
            r = curs.fetchone()
            consumer_name = r['consumer_name']
            queue_name = r['queue_name']

            curs.execute(target_query, src_row)
            for dst_row in curs.fetchall():
                d_db = dst_row['db_name']
                d_host = dst_row['hostname']

                cstr1 = "dbname=%s host=%s %s" % (s_db, s_host, extra_connstr)
                cstr2 = "dbname=%s host=%s %s" % (d_db, d_host, extra_connstr)
                where = where_expr % dst_row

                self.log.info('Source: db=%s host=%s queue=%s consumer=%s' % (
                                  s_db, s_host, queue_name, consumer_name))
                self.log.info('Target: db=%s host=%s where=%s' % (d_db, d_host, where))

                for tbl in self.table_list:
                    src_db, dst_db = self.sync_table(cstr1, cstr2, queue_name, consumer_name, tbl)
                    if check == 'compare':
                        self.do_compare(tbl, src_db, dst_db, where)
                    elif check == 'repair':
                        r = TableRepair(tbl, self.log)
                        r.do_repair(src_db, dst_db, where, 'fix.' + tbl, False)
                    elif check == 'repair-apply':
                        r = TableRepair(tbl, self.log)
                        r.do_repair(src_db, dst_db, where, 'fix.' + tbl, True)
                    elif check == 'compare-repair-apply':
                        ok = self.do_compare(tbl, src_db, dst_db, where)
                        if not ok:
                            r = TableRepair(tbl, self.log)
                            r.do_repair(src_db, dst_db, where, 'fix.' + tbl, True)
                    else:
                        raise Exception('unknown check type')
                    self.reset()

    def do_compare(self, tbl, src_db, dst_db, where):
        """Actual comparision."""

        src_curs = src_db.cursor()
        dst_curs = dst_db.cursor()

        self.log.info('Counting %s' % tbl)

        q = "select count(1) as cnt, sum(hashtext(t.*::text)) as chksum from only _TABLE_ t where %s;" %  where
        q = self.cf.get('compare_sql', q)
        q = q.replace('_TABLE_', skytools.quote_fqident(tbl))

        f = "%(cnt)d rows, checksum=%(chksum)s"
        f = self.cf.get('compare_fmt', f)

        self.log.debug("srcdb: " + q)
        src_curs.execute(q)
        src_row = src_curs.fetchone()
        src_str = f % src_row
        self.log.info("srcdb: %s" % src_str)

        self.log.debug("dstdb: " + q)
        dst_curs.execute(q)
        dst_row = dst_curs.fetchone()
        dst_str = f % dst_row
        self.log.info("dstdb: %s" % dst_str)

        src_db.commit()
        dst_db.commit()

        if src_str != dst_str:
            self.log.warning("%s: Results do not match!" % tbl)
            return False
        else:
            self.log.info("%s: OK!" % tbl)
            return True


if __name__ == '__main__':
    script = Checker(sys.argv[1:])
    script.start()


########NEW FILE########
__FILENAME__ = config

"""Nicer config class."""

import os, os.path, ConfigParser, socket

import skytools

__all__ = ['Config']

class Config(object):
    """Bit improved ConfigParser.

    Additional features:
     - Remembers section.
     - Accepts defaults in get() functions.
     - List value support.
    """
    def __init__(self, main_section, filename, sane_config = 1, user_defs = {}, override = {}, ignore_defs = False):
        """Initialize Config and read from file.

        @param sane_config:  chooses between ConfigParser/SafeConfigParser.
        """
        # use config file name as default job_name
        if filename:
            job_name = os.path.splitext(os.path.basename(filename))[0]
        else:
            job_name = main_section

        # initialize defaults, make them usable in config file
        if ignore_defs:
            self.defs = {}
        else:
            self.defs = {
                'job_name': job_name,
                'service_name': main_section,
                'host_name': socket.gethostname(),
            }
            if filename:
                self.defs['config_dir'] = os.path.dirname(filename)
                self.defs['config_file'] = filename
            self.defs.update(user_defs)

        self.main_section = main_section
        self.filename = filename
        self.sane_config = sane_config
        self.override = override
        if sane_config:
            self.cf = ConfigParser.SafeConfigParser()
        else:
            self.cf = ConfigParser.ConfigParser()

        if filename is None:
            self.cf.add_section(main_section)
        elif not os.path.isfile(filename):
            raise Exception('Config file not found: '+filename)

        self.reload()

    def reload(self):
        """Re-reads config file."""
        if self.filename:
            self.cf.read(self.filename)
        if not self.cf.has_section(self.main_section):
            raise Exception("Wrong config file, no section '%s'" % self.main_section)

        # apply default if key not set
        for k, v in self.defs.items():
            if not self.cf.has_option(self.main_section, k):
                self.cf.set(self.main_section, k, v)

        # apply overrides
        if self.override:
            for k, v in self.override.items():
                self.cf.set(self.main_section, k, v)

    def get(self, key, default=None):
        """Reads string value, if not set then default."""
        try:
            return self.cf.get(self.main_section, key)
        except ConfigParser.NoOptionError:
            if default == None:
                raise Exception("Config value not set: " + key)
            return default

    def getint(self, key, default=None):
        """Reads int value, if not set then default."""
        try:
            return self.cf.getint(self.main_section, key)
        except ConfigParser.NoOptionError:
            if default == None:
                raise Exception("Config value not set: " + key)
            return default

    def getboolean(self, key, default=None):
        """Reads boolean value, if not set then default."""
        try:
            return self.cf.getboolean(self.main_section, key)
        except ConfigParser.NoOptionError:
            if default == None:
                raise Exception("Config value not set: " + key)
            return default

    def getfloat(self, key, default=None):
        """Reads float value, if not set then default."""
        try:
            return self.cf.getfloat(self.main_section, key)
        except ConfigParser.NoOptionError:
            if default == None:
                raise Exception("Config value not set: " + key)
            return default

    def getlist(self, key, default=None):
        """Reads comma-separated list from key."""
        try:
            s = self.cf.get(self.main_section, key).strip()
            res = []
            if not s:
                return res
            for v in s.split(","):
                res.append(v.strip())
            return res
        except ConfigParser.NoOptionError:
            if default == None:
                raise Exception("Config value not set: " + key)
            return default

    def getdict(self, key, default=None):
        """Reads key-value dict from parameter.

        Key and value are separated with ':'.  If missing,
        key itself is taken as value.
        """
        try:
            s = self.cf.get(self.main_section, key).strip()
            res = {}
            if not s:
                return res
            for kv in s.split(","):
                tmp = kv.split(':', 1)
                if len(tmp) > 1:
                    k = tmp[0].strip()
                    v = tmp[1].strip()
                else:
                    k = kv.strip()
                    v = k
                res[k] = v
            return res
        except ConfigParser.NoOptionError:
            if default == None:
                raise Exception("Config value not set: " + key)
            return default

    def getfile(self, key, default=None):
        """Reads filename from config.

        In addition to reading string value, expands ~ to user directory.
        """
        fn = self.get(key, default)
        if fn == "" or fn == "-":
            return fn
        # simulate that the cwd is script location
        #path = os.path.dirname(sys.argv[0])
        #  seems bad idea, cwd should be cwd

        fn = os.path.expanduser(fn)

        return fn

    def getbytes(self, key, default=None):
        """Reads a size value in human format, if not set then default.

        Examples: 1, 2 B, 3K, 4 MB
        """
        try:
            s = self.cf.get(self.main_section, key)
        except ConfigParser.NoOptionError:
            if default is None:
                raise Exception("Config value not set: " + key)
            s = default
        return skytools.hsize_to_bytes(s)

    def get_wildcard(self, key, values=[], default=None):
        """Reads a wildcard property from conf and returns its string value, if not set then default."""

        orig_key = key
        keys = [key]

        for wild in values:
            key = key.replace('*', wild, 1)
            keys.append(key)
        keys.reverse()

        for key in keys:
            try:
                return self.cf.get(self.main_section, key)
            except ConfigParser.NoOptionError:
                pass

        if default == None:
            raise Exception("Config value not set: " + orig_key)
        return default

    def sections(self):
        """Returns list of sections in config file, excluding DEFAULT."""
        return self.cf.sections()

    def has_section(self, section):
        """Checks if section is present in config file, excluding DEFAULT."""
        return self.cf.has_section(section)

    def clone(self, main_section):
        """Return new Config() instance with new main section on same config file."""
        return Config(main_section, self.filename, self.sane_config)

    def options(self):
        """Return list of options in main section."""
        return self.cf.options(self.main_section)

    def has_option(self, opt):
        """Checks if option exists in main section."""
        return self.cf.has_option(self.main_section, opt)

    def items(self):
        """Returns list of (name, value) for each option in main section."""
        return self.cf.items(self.main_section)

    # define some aliases (short-cuts / backward compatibility cruft)
    getbool = getboolean

########NEW FILE########
__FILENAME__ = dbservice
#! /usr/bin/env python

""" Class used to handle multiset receiving and returning PL/Python procedures
"""

import re, skytools

from skytools import dbdict

__all__ = ['DBService', 'ServiceContext',
    'get_record', 'get_record_list',
    'make_record', 'make_record_array',
    'TableAPI',
    #'log_result', 'transform_fields'
]

try:
    import plpy
except ImportError:
    pass

def transform_fields(rows, key_fields, name_field, data_field):
    """Convert multiple-rows per key input array
    to one-row, multiple-column output array.  The input arrays
    must be sorted by the key fields.

    >>> rows = []
    >>> rows.append({'time': '22:00', 'metric': 'count', 'value': 100})
    >>> rows.append({'time': '22:00', 'metric': 'dur', 'value': 7})
    >>> rows.append({'time': '23:00', 'metric': 'count', 'value': 200})
    >>> rows.append({'time': '23:00', 'metric': 'dur', 'value': 5})
    >>> transform_fields(rows, ['time'], 'metric', 'value')
    [{'count': 100, 'dur': 7, 'time': '22:00'}, {'count': 200, 'dur': 5, 'time': '23:00'}]
    """
    cur_key = None
    cur_row = None
    res = []
    for r in rows:
        k = [r[f] for f in key_fields]
        if k != cur_key:
            cur_key = k
            cur_row = {}
            for f in key_fields:
                cur_row[f] = r[f]
            res.append(cur_row)
        cur_row[r[name_field]] = r[data_field]
    return res

# render_table
def render_table(rows, fields):
    """ Render result rows as a table.
        Returns array of lines.
    """
    widths = [15] * len(fields)
    for row in rows:
        for i, k in enumerate(fields):
            rlen = len(str(row.get(k)))
            widths[i] = widths[i] > rlen and widths[i] or rlen
    widths = [w + 2 for w in widths]

    fmt = '%%-%ds' * (len(widths) - 1) + '%%s'
    fmt = fmt % tuple(widths[:-1])

    lines = []
    lines.append(fmt % tuple(fields))
    lines.append(fmt % tuple(['-'*15] * len(fields)))
    for row in rows:
        lines.append(fmt % tuple([str(row.get(k)) for k in fields]))
    return lines

# data conversion to and from url

def get_record(arg):
    """ Parse data for one urlencoded record.
        Useful for turning incoming serialized data into structure usable for manipulation.
    """
    if not arg:
        return dbdict()

    # allow array of single record
    if arg[0] in ('{', '['):
        lst = skytools.parse_pgarray(arg)
        if len(lst) != 1:
            raise ValueError('get_record() expects exactly 1 row, got %d' % len(lst))
        arg = lst[0]

    # parse record
    return dbdict(skytools.db_urldecode(arg))

def get_record_list(array):
    """ Parse array of urlencoded records.
        Useful for turning incoming serialized data into structure usable for manipulation.
    """
    if array is None:
        return []

    if isinstance(array, list):
        return map(get_record, array)
    else:
        return map(get_record, skytools.parse_pgarray(array))

def get_record_lists(tbl, field):
    """ Create dictionary of lists from given list using field as grouping criteria
        Used for master detail operatons to group detail records according to master id
    """
    dict = dbdict()
    for rec in tbl:
        id = str( rec[field] )
        dict.setdefault( id, [] ).append(rec)
    return dict

def _make_record_convert(row):
    """Converts complex values."""
    d = row.copy()
    for k, v in d.items():
        if isinstance(v, list):
            d[k] = skytools.make_pgarray(v)
    return skytools.db_urlencode(d)

def make_record(row):
    """ Takes record as dict and returns it as urlencoded string.
        Used to send data out of db service layer.or to fake incoming calls
    """
    for v in row.values():
        if isinstance(v, list):
            return _make_record_convert(row)
    return skytools.db_urlencode(row)

def make_record_array(rowlist):
    """ Takes list of records got from plpy execute and turns it into postgers aray string.
        Used to send data out of db service layer.
    """
    return '{' + ','.join( map(make_record, rowlist) ) +  '}'

def get_result_items(list, name):
    """ Get return values from result
    """
    for r in list:
        if r['res_code'] == name:
            return get_record_list(r['res_rows'])
    return None

def log_result(log, list):
    """ Sends dbservice execution logs to logfile
    """
    msglist = get_result_items(list, "_status")
    if msglist is None:
        if list:
            log.warning('Unhandled output result: _status res_code not present.')
    else:
        for msg in msglist:
            log.debug( msg['_message'] )


class DBService:
    """  Wrap parameterized query handling and multiset stored procedure writing
    """
    ROW = "_row"            # name of the fake field where internal record id is stored
    FIELD = "_field"        # parameter name for the field in record that is related to current message
    PARAM = "_param"        # name of the parameter to which message relates
    SKIP = "skip"           # used when record is needed for it's data but is not been updated
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    INFO = "info"           # just informative message for the user
    NOTICE = "notice"       # more than info less than warning
    WARNING = "warning"     # warning message, something is out of ordinary
    ERROR = "error"         # error found but execution continues until check then error is raised
    FATAL = "fatal"         # execution is terminated at once and all found errors returned

    def __init__(self, context, global_dict = None):
        """ This object must be initiated in the beginning of each db service
        """
        rec = skytools.db_urldecode(context)
        self._context = context             # used to run dbservice in retval
        self.global_dict = global_dict      # used for cacheing query plans
        self._retval = []                   # used to collect return resultsets
        self._is_test = 'is_test' in rec    # used to convert output into human readable form

        self.sqls = None                    # if sqls stays None then no recording of sqls is done
        if "show_sql" in rec:               # api must add exected sql to resultset
            self.sqls = []                  # sql's executed by dbservice, used for dubugging

        self.can_save = True                # used to keep value most severe error found so far
        self.messages = []                  # used to hold list of messages to be returned to the user

    # error and message handling

    def tell_user(self, severity, code, message, params = None, **kvargs):
        """ Adds another message to the set of messages to be sent back to user
            If error message then can_save is set false
            If fatal message then error or found errors are raised at once
        """
        params = params or kvargs
        #plpy.notice("%s %s: %s %s" % (severity, code, message, str(params)))
        params["_severity"] = severity
        params["_code"] = code
        params["_message"] = message
        self.messages.append( params )
        if severity == self.ERROR:
            self.can_save = False
        if severity == self.FATAL:
            self.can_save = False
            self.raise_if_errors()

    def raise_if_errors(self):
        """ To be used in places where before continuing must be chcked if errors have been found
            Raises found errors packing them into error message as urlencoded string
        """
        if not self.can_save:
            msgs = "Dbservice error(s): " + make_record_array( self.messages )
            plpy.error( msgs )

    # run sql meant mostly for select but not limited to

    def create_query(self, sql, params = None, **kvargs):
        """ Returns initialized querybuilder object for building complex dynamic queries
        """
        params = params or kvargs
        return skytools.PLPyQueryBuilder(sql, params, self.global_dict, self.sqls )

    def run_query(self, sql, params = None, **kvargs):
        """ Helper function if everything you need is just paramertisized execute
            Sets rows_found that is coneninet to use when you don't need result just
            want to know how many rows were affected
        """
        params = params or kvargs
        rows = skytools.plpy_exec(self.global_dict, sql, params)
        # convert result rows to dbdict
        if rows:
            rows = [dbdict(r) for r in rows]
            self.rows_found = len(rows)
        else:
            self.rows_found = 0
        return rows

    def run_query_row(self, sql, params = None, **kvargs):
        """ Helper function if everything you need is just paramertisized execute to
            fetch one row only. If not found none is returned
        """
        params = params or kvargs
        rows = self.run_query( sql, params )
        if len(rows) == 0:
            return None
        return rows[0]

    def run_exists(self, sql, params = None, **kvargs):
        """ Helper function to find out that record in given table exists using
            values in dict as criteria. Takes away all the hassle of preparing statements
            and processing returned result giving out just one boolean
        """
        params = params or kvargs
        self.run_query( sql, params )
        return self.rows_found

    def run_lookup(self, sql, params = None, **kvargs):
        """ Helper function to fetch one value Takes away all the hassle of preparing statements
            and processing returned result giving out just one value. Uses plan cache if used inside
            db service
        """
        params = params or kvargs
        rows = self.run_query( sql, params )
        if len(rows) == 0:
            return None
        row = rows[0]
        return row.values()[0]

     # resultset handling

    def return_next(self, rows, res_name, severity = None):
        """ Adds given set of rows to resultset
        """
        self._retval.append([res_name, rows])
        if severity is not None and len(rows) == 0:
            self.tell_user(severity, "dbsXXXX", "No matching records found")
        return rows

    def return_next_sql(self, sql, params, res_name, severity = None):
        """ Exectes query and adds recors resultset
        """
        rows = self.run_query( sql, params )
        return self.return_next( rows, res_name, severity )

    def retval(self, service_name = None, params = None, **kvargs):
        """ Return collected resultsets and append to the end messages to the users
            Method is called usually as last statment in dbservice to return the results
            Also converts results into desired format
        """
        params = params or kvargs
        self.raise_if_errors()
        if len( self.messages ):
            self.return_next( self.messages, "_status" )
        if self.sqls is not None and len( self.sqls ):
            self.return_next( self.sqls, "_sql" )
        results = []
        for r in self._retval:
            res_name = r[0]
            rows = r[1]
            res_count = str(len(rows))
            if self._is_test and len(rows) > 0:
                results.append([res_name, res_count, res_name])
                n = 1
                for trow in render_table(rows, rows[0].keys()):
                    results.append([res_name, n, trow])
                    n += 1
            else:
                res_rows = make_record_array(rows)
                results.append([res_name, res_count, res_rows])
        if service_name:
            sql = "select * from %s( {i_context}, {i_params} );" % skytools.quote_fqident(service_name)
            par = dbdict( i_context = self._context, i_params = make_record(params) )
            res = self.run_query( sql, par )
            for r in res:
                results.append((r.res_code, r.res_text, r.res_rows))
        return results

    # miscellaneous

    def check_required(self, record_name, record, severity, *fields):
        """ Checks if all required fields are present in record
            Used to validate incoming data
            Returns list of field names that are missing or empty
        """
        missing = []
        params = {self.PARAM: record_name}
        if self.ROW in record:
            params[self.ROW] = record[self.ROW]
        for field in fields:
            params[self.FIELD] = field
            if field in record:
                if record[field] is None or (isinstance(record[field], basestring) and len(record[field]) == 0):
                    self.tell_user(severity, "dbsXXXX", "Required value missing: {%s}.{%s}" % (self.PARAM, self.FIELD), **params)
                    missing.append(field)
            else:
                self.tell_user(severity, "dbsXXXX", "Required field missing: {%s}.{%s}" % (self.PARAM, self.FIELD), **params)
                missing.append(field)
        return missing




# TableAPI
class TableAPI:
    """ Class for managing one record updates using primary key
    """
    _table = None   # schema name and table name
    _where = None   # where condition used for update and delete
    _id = None      # name of the primary key filed
    _id_type = None # column type of primary key
    _op = None      # operation currently carried out
    _ctx = None     # context object for username and version
    _logging = True # should tapi log data changed
    _row = None     # row identifer from calling program

    def __init__(self, ctx, table, create_log = True, id_type='int8' ):
        """ Table name is used to construct insert update and delete statements
            Table must have primary key field whose name is in format id_<table>
            Tablename should be in format schema.tablename
        """
        self._ctx = ctx
        self._table = skytools.quote_fqident(table)
        self._id = "id_" + skytools.fq_name_parts(table)[1]
        self._id_type = id_type
        self._where = '%s = {%s:%s}' % (skytools.quote_ident(self._id), self._id, self._id_type)
        self._logging = create_log

    def _log(self, result, original = None):
        """ Log changei into table log.changelog
        """
        if not self._logging:
            return
        changes = []
        for key in result.keys():
            if self._op == 'update':
                if key in original:
                    if str(original[key]) <> str(result[key]):
                        changes.append( key + ": " + str(original[key]) + " -> " + str(result[key]) )
            else:
                changes.append( key + ": " + str(result[key]) )
        self._ctx.log( self._table,  result[ self._id ], self._op, "\n".join(changes) )

    def _version_check(self, original, version):
        if original is None:
            self._ctx.tell_user( self._ctx.INFO, "dbsXXXX",
                "Record ({table}.{field}={id}) has been deleted by other user while you were editing. Check version ({ver}) in changelog for details.",
                table = self._table, field = self._id, id = original[self._id], ver = original.version, _row = self._row )
        if version is not None and original.version is not None:
            if int(version) != int(original.version):
                    self._ctx.tell_user( self._ctx.INFO, "dbsXXXX",
                            "Record ({table}.{field}={id}) has been changed by other user while you were editing. Version in db: ({db_ver}) and version sent by caller ({caller_ver}). See changelog for details.",
                        table = self._table, field = self._id, id = original[self._id], db_ver = original.version, caller_ver = version, _row = self._row )

    def _insert(self, data):
        fields = []
        values = []
        for key in data.keys():
            if data[key] is not None:       # ignore empty
                fields.append(skytools.quote_ident(key))
                values.append("{" + key + "}")
        sql = "insert into %s (%s) values (%s) returning *;" % ( self._table, ",".join(fields), ",".join(values))
        result = self._ctx.run_query_row( sql, data )
        self._log( result )
        return result

    def _update(self, data, version):
        sql = "select * from %s where %s" % ( self._table, self._where )
        original = self._ctx.run_query_row( sql, data )
        self._version_check( original, version )
        pairs = []
        for key in data.keys():
            if data[key] is None:
                pairs.append( key + " = NULL" )
            else:
                pairs.append( key + " = {" + key + "}" )
        sql = "update %s set %s where %s returning *;" % ( self._table, ", ".join(pairs), self._where )
        result = self._ctx.run_query_row( sql, data )
        self._log( result, original )
        return result

    def _delete(self, data, version):
        sql = "delete from %s where %s returning *;" % ( self._table, self._where )
        result = self._ctx.run_query_row( sql, data )
        self._version_check( result, version )
        self._log( result )
        return result

    def do(self, data):
        """ Do dml according to special field _op that must be given together wit data
        """
        result = data                               # so it is initialized for skip
        self._op = data.pop(self._ctx.OP)           # determines operation done
        self._row = data.pop(self._ctx.ROW, None)   # internal record id used for error reporting
        if self._row is None:                       # if no _row variable was provided
            self._row = data.get(self._id, None)    # use id instead
        if self._id in data and data[self._id]:     # if _id field is given
            if int( data[self._id] ) < 0:           # and it is fake key generated by ui
                data.pop(self._id)                  # remove fake key so real one can be assigned
        version = data.get('version', None)         # version sent from caller
        data['version'] = self._ctx.version         # current transaction id is stored in each record
        if   self._op == self._ctx.INSERT: result = self._insert( data )
        elif self._op == self._ctx.UPDATE: result = self._update( data, version )
        elif self._op == self._ctx.DELETE: result = self._delete( data, version )
        elif self._op == self._ctx.SKIP:   None
        else:
            self._ctx.tell_user( self._ctx.ERROR, "dbsXXXX",
                "Unahndled _op='{op}' value in TableAPI (table={table}, id={id})",
                op = self._op, table = self._table, id = data[self._id] )
        result[self._ctx.OP] = self._op
        result[self._ctx.ROW] = self._row
        return result

# ServiceContext
class ServiceContext(DBService):
    OP = "_op"              # name of the fake field where record modificaton operation is stored

    def __init__(self, context, global_dict = None):
        """ This object must be initiated in the beginning of each db service
        """
        DBService.__init__(self, context, global_dict)

        rec = skytools.db_urldecode(context)
        if "username" not in rec:
            plpy.error("Username must be provided in db service context parameter")
        self.username = rec['username']     # used for logging purposes

        res = plpy.execute("select txid_current() as txid;")
        row = res[0]
        self.version = row["txid"]
        self.rows_found = 0                 # Flag set by run query to inicate number of rows got

    # logging

    def log(self, _object_type, _key_object, _change_op, _payload):
        """ Log stuff into the changelog whatever seems relevant to be logged
        """
        self.run_query(
            "select log.log_change( {version}, {username}, {object_type}, {key_object}, {change_op}, {payload} );",
                version= self.version , username= self.username ,
                object_type= _object_type , key_object= _key_object ,
                change_op= _change_op , payload= _payload )

    # data conversion to and from url

    def get_record(self, arg):
        """ Parse data for one urlencoded record.
            Useful for turning incoming serialized data into structure usable for manipulation.
        """
        return get_record(arg)

    def get_record_list(self, array):
        """ Parse array of urlencoded records.
            Useful for turning incoming serialized data into structure usable for manipulation.
        """
        return get_record_list(array)

    def get_list_groups(self, tbl, field):
        """ Create dictionary of lists from given list using field as grouping criteria
            Used for master detail operatons to group detail records according to master id
        """
        return get_record_lists(tbl, field)

    def make_record(self, row):
        """ Takes record as dict and returns it as urlencoded string.
            Used to send data out of db service layer.or to fake incoming calls
        """
        return make_record(row)

    def make_record_array(self, rowlist):
        """ Takes list of records got from plpy execute and turns it into postgers aray string.
            Used to send data out of db service layer.
        """
        return make_record_array(rowlist)

    # tapi based dml functions

    def _changelog(self, fields):
        log = True
        if fields:
            if '_log' in fields:
                if not fields.pop('_log'):
                    log = False
            if '_log_id' in fields:
                fields.pop('_log_id')
            if '_log_field' in fields:
                fields.pop('_log_field')
        return log

    def tapi_do(self, tablename, row, **fields):
        """ Convenience function for just doing the change without creating tapi object first
            Fields object may contain aditional overriding values that are aplied before do
        """
        tapi =  TableAPI(self, tablename, self._changelog(fields))
        row = row or dbdict()
        fields and row.update(fields)
        return tapi.do( row )

    def tapi_do_set(self, tablename, rows, **fields):
        """ Does changes to list of detail rows
            Used for normal foreign keys in master detail relationships
            Dows first deletes then updates and then inserts to avoid uniqueness problems
        """
        tapi = TableAPI(self, tablename, self._changelog(fields))
        results, updates, inserts = [], [], []
        for row in rows:
            fields and row.update(fields)
            if row[self.OP] == self.DELETE:
                results.append( tapi.do( row ) )
            elif row[self.OP] == self.UPDATE:
                updates.append( row )
            else:
                inserts.append( row )
        for row in updates:
            results.append( tapi.do( row ) )
        for row in inserts:
            results.append( tapi.do( row ) )
        return results

    # resultset handling

    def retval_dbservice(self, service_name, ctx, **params):
        """ Runs service with standard interface.
            Convenient to use for calling select services from other services
            For example to return data after doing save
        """
        self.raise_if_errors()
        service_sql = "select * from %s( {i_context}, {i_params} );" % skytools.quote_fqident(service_name)
        service_params = { "i_context": ctx, "i_params": self.make_record(params) }
        results = self.run_query( service_sql, service_params )
        retval = self.retval()
        for r in results:
            retval.append((r.res_code, r.res_text, r.res_rows))
        return retval

    # miscellaneous

    def field_copy(self, dict, *keys):
        """ Used to copy subset of fields from one record into another
            example: dbs.copy(record, hosting) "start_date", "key_colo", "key_rack")
        """
        retval = dbdict()
        for key in keys:
            if key in dict:
                retval[key] = dict[key]
        return retval

    def field_set(self, **fields):
        """ Fills dict with given values and returns resulting dict
            If dict was not provied with call it is created
        """
        return fields

########NEW FILE########
__FILENAME__ = dbstruct
"""Find table structure and allow CREATE/DROP elements from it.
"""

import re

import skytools

from skytools import quote_ident, quote_fqident

__all__ = ['TableStruct', 'SeqStruct',
    'T_TABLE', 'T_CONSTRAINT', 'T_INDEX', 'T_TRIGGER',
    'T_RULE', 'T_GRANT', 'T_OWNER', 'T_PKEY', 'T_ALL',
    'T_SEQUENCE', 'T_PARENT', 'T_DEFAULT']

T_TABLE       = 1 << 0
T_CONSTRAINT  = 1 << 1
T_INDEX       = 1 << 2
T_TRIGGER     = 1 << 3
T_RULE        = 1 << 4
T_GRANT       = 1 << 5
T_OWNER       = 1 << 6
T_SEQUENCE    = 1 << 7
T_PARENT      = 1 << 8
T_DEFAULT     = 1 << 9
T_PKEY        = 1 << 20 # special, one of constraints
T_ALL = (  T_TABLE | T_CONSTRAINT | T_INDEX | T_SEQUENCE
         | T_TRIGGER | T_RULE | T_GRANT | T_OWNER | T_DEFAULT )

#
# Utility functions
#

def find_new_name(curs, name):
    """Create new object name for case the old exists.

    Needed when creating a new table besides old one.
    """
    # cut off previous numbers
    m = re.search('_[0-9]+$', name)
    if m:
        name = name[:m.start()]

    # now loop
    for i in range(1, 1000):
        tname = "%s_%d" % (name, i)
        q = "select count(1) from pg_class where relname = %s"
        curs.execute(q, [tname])
        if curs.fetchone()[0] == 0:
            return tname

    # failed
    raise Exception('find_new_name failed')

def rx_replace(rx, sql, new_part):
    """Find a regex match and replace that part with new_part."""
    m = re.search(rx, sql, re.I)
    if not m:
        raise Exception('rx_replace failed: rx=%r sql=%r new=%r' % (rx, sql, new_part))
    p1 = sql[:m.start()]
    p2 = sql[m.end():]
    return p1 + new_part + p2

#
# Schema objects
#

class TElem(object):
    """Keeps info about one metadata object."""
    SQL = ""
    type = 0
    def get_create_sql(self, curs, new_name = None):
        """Return SQL statement for creating or None if not supported."""
        return None
    def get_drop_sql(self, curs):
        """Return SQL statement for dropping or None of not supported."""
        return None

    @classmethod
    def get_load_sql(cls, pgver):
        """Return SQL statement for finding objects."""
        return cls.SQL

class TConstraint(TElem):
    """Info about constraint."""
    type = T_CONSTRAINT
    SQL = """
        SELECT c.conname as name, pg_get_constraintdef(c.oid) as def, c.contype,
               i.indisclustered as is_clustered
          FROM pg_constraint c LEFT JOIN pg_index i ON
            c.conrelid = i.indrelid AND
            c.conname = (SELECT r.relname FROM pg_class r WHERE r.oid = i.indexrelid)
          WHERE c.conrelid = %(oid)s AND c.contype != 'f'
    """
    def __init__(self, table_name, row):
        """Init constraint."""
        self.table_name = table_name
        self.name = row['name']
        self.defn = row['def']
        self.contype = row['contype']
        self.is_clustered = row['is_clustered']

        # tag pkeys
        if self.contype == 'p':
            self.type += T_PKEY

    def get_create_sql(self, curs, new_table_name=None):
        """Generate creation SQL."""
        # no ONLY here as table with childs (only case that matters)
        # cannot have contraints that childs do not have
        fmt = "ALTER TABLE %s ADD CONSTRAINT %s\n  %s;"
        if new_table_name:
            name = self.name
            if self.contype in ('p', 'u'):
                name = find_new_name(curs, self.name)
            qtbl = quote_fqident(new_table_name)
            qname = quote_ident(name)
        else:
            qtbl = quote_fqident(self.table_name)
            qname = quote_ident(self.name)
        sql = fmt % (qtbl, qname, self.defn)
        if self.is_clustered:
            sql +=' ALTER TABLE ONLY %s\n  CLUSTER ON %s;' % (qtbl, qname)
        return sql

    def get_drop_sql(self, curs):
        """Generate removal sql."""
        fmt = "ALTER TABLE ONLY %s\n  DROP CONSTRAINT %s;"
        sql = fmt % (quote_fqident(self.table_name), quote_ident(self.name))
        return sql

class TIndex(TElem):
    """Info about index."""
    type = T_INDEX
    SQL = """
        SELECT n.nspname || '.' || c.relname as name,
               pg_get_indexdef(i.indexrelid) as defn,
               c.relname                     as local_name,
               i.indisclustered              as is_clustered
         FROM pg_index i, pg_class c, pg_namespace n
        WHERE c.oid = i.indexrelid AND i.indrelid = %(oid)s
          AND n.oid = c.relnamespace
          AND NOT EXISTS
            (select objid from pg_depend
              where classid = %(pg_class_oid)s
                and objid = c.oid
                and deptype = 'i')
    """
    def __init__(self, table_name, row):
        self.name = row['name']
        self.defn = row['defn'].replace(' USING ', '\n  USING ', 1) + ';'
        self.is_clustered = row['is_clustered']
        self.table_name = table_name
        self.local_name = row['local_name']

    def get_create_sql(self, curs, new_table_name = None):
        """Generate creation SQL."""
        if new_table_name:
            # fixme: seems broken
            iname = find_new_name(curs, self.name)
            tname = new_table_name
            pnew = "INDEX %s ON %s " % (quote_ident(iname), quote_fqident(tname))
            rx = r"\bINDEX[ ][a-z0-9._]+[ ]ON[ ][a-z0-9._]+[ ]"
            sql = rx_replace(rx, self.defn, pnew)
        else:
            sql = self.defn
            iname = self.local_name
            tname = self.table_name
        if self.is_clustered:
            sql += ' ALTER TABLE ONLY %s\n  CLUSTER ON %s;' % (
                quote_fqident(tname), quote_ident(iname))
        return sql

    def get_drop_sql(self, curs):
        return 'DROP INDEX %s;' % quote_fqident(self.name)

class TRule(TElem):
    """Info about rule."""
    type = T_RULE
    SQL = """SELECT rw.*, pg_get_ruledef(rw.oid) as def
              FROM pg_rewrite rw
             WHERE rw.ev_class = %(oid)s AND rw.rulename <> '_RETURN'::name
    """
    def __init__(self, table_name, row, new_name = None):
        self.table_name = table_name
        self.name = row['rulename']
        self.defn = row['def']
        self.enabled = row.get('ev_enabled', 'O')

    def get_create_sql(self, curs, new_table_name = None):
        """Generate creation SQL."""
        if not new_table_name:
            sql = self.defn
            table = self.table_name
        else:
            idrx = r'''([a-z0-9._]+|"([^"]+|"")+")+'''
            # fixme: broken / quoting
            rx = r"\bTO[ ]" + idrx
            rc = re.compile(rx, re.X)
            m = rc.search(self.defn)
            if not m:
                raise Exception('Cannot find table name in rule')
            old_tbl = m.group(1)
            new_tbl = quote_fqident(new_table_name)
            sql = self.defn.replace(old_tbl, new_tbl)
            table = new_table_name
        if self.enabled != 'O':
            # O - rule fires in origin and local modes
            # D - rule is disabled
            # R - rule fires in replica mode
            # A - rule fires always
            action = {'R': 'ENABLE REPLICA',
                      'A': 'ENABLE ALWAYS',
                      'D': 'DISABLE'} [self.enabled]
            sql += ('\nALTER TABLE %s %s RULE %s;' % (table, action, self.name))
        return sql

    def get_drop_sql(self, curs):
        return 'DROP RULE %s ON %s' % (quote_ident(self.name), quote_fqident(self.table_name))


class TTrigger(TElem):
    """Info about trigger."""
    type = T_TRIGGER

    def __init__(self, table_name, row):
        self.table_name = table_name
        self.name = row['name']
        self.defn = row['def'] + ';'
        self.defn = self.defn.replace('FOR EACH', '\n  FOR EACH', 1)

    def get_create_sql(self, curs, new_table_name = None):
        """Generate creation SQL."""
        if not new_table_name:
            return self.defn

        # fixme: broken / quoting
        rx = r"\bON[ ][a-z0-9._]+[ ]"
        pnew = "ON %s " % new_table_name
        return rx_replace(rx, self.defn, pnew)

    def get_drop_sql(self, curs):
        return 'DROP TRIGGER %s ON %s' % (quote_ident(self.name), quote_fqident(self.table_name))

    @classmethod
    def get_load_sql(cls, pg_vers):
        """Return SQL statement for finding objects."""

        sql = "SELECT tgname as name, pg_get_triggerdef(oid) as def "\
              "  FROM  pg_trigger "\
              "  WHERE tgrelid = %(oid)s AND "
        if pg_vers >= 90000:
            sql += "NOT tgisinternal"
        else:
            sql += "NOT tgisconstraint"
        return sql

class TParent(TElem):
    """Info about trigger."""
    type = T_PARENT
    SQL = """
        SELECT n.nspname||'.'||c.relname AS name
          FROM pg_inherits i
          JOIN pg_class c ON i.inhparent = c.oid
          JOIN pg_namespace n ON c.relnamespace = n.oid
         WHERE i.inhrelid = %(oid)s
    """
    def __init__(self, table_name, row):
        self.name = table_name
        self.parent_name = row['name']

    def get_create_sql(self, curs, new_table_name = None):
        return 'ALTER TABLE ONLY %s\n  INHERIT %s' % (quote_fqident(self.name), quote_fqident(self.parent_name))

    def get_drop_sql(self, curs):
        return 'ALTER TABLE ONLY %s\n  NO INHERIT %s' % (quote_fqident(self.name), quote_fqident(self.parent_name))


class TOwner(TElem):
    """Info about table owner."""
    type = T_OWNER
    SQL = """
        SELECT pg_get_userbyid(relowner) as owner FROM pg_class
         WHERE oid = %(oid)s
    """
    def __init__(self, table_name, row, new_name = None):
        self.table_name = table_name
        self.name = 'Owner'
        self.owner = row['owner']

    def get_create_sql(self, curs, new_name = None):
        """Generate creation SQL."""
        if not new_name:
            new_name = self.table_name
        return 'ALTER TABLE %s\n  OWNER TO %s;' % (quote_fqident(new_name), quote_ident(self.owner))

class TGrant(TElem):
    """Info about permissions."""
    type = T_GRANT
    SQL = "SELECT relacl FROM pg_class where oid = %(oid)s"

    # Sync with: src/include/utils/acl.h
    acl_map = {
        'a': 'INSERT',
        'r': 'SELECT',
        'w': 'UPDATE',
        'd': 'DELETE',
        'D': 'TRUNCATE',
        'x': 'REFERENCES',
        't': 'TRIGGER',
        'X': 'EXECUTE',
        'U': 'USAGE',
        'C': 'CREATE',
        'T': 'TEMPORARY',
        'c': 'CONNECT',
        # old
        'R': 'RULE',
    }

    def acl_to_grants(self, acl):
        if acl == "arwdRxt":   # ALL for tables
            return "ALL"
        i = 0
        lst1 = []
        lst2 = []
        while i < len(acl):
            a = self.acl_map[acl[i]]
            if i+1 < len(acl) and acl[i+1] == '*':
                lst2.append(a)
                i += 2
            else:
                lst1.append(a)
                i += 1
        return ", ".join(lst1), ", ".join(lst2)

    def parse_relacl(self, relacl):
        """Parse ACL to tuple of (user, acl, who)"""
        if relacl is None:
            return []
        tup_list = []
        for sacl in skytools.parse_pgarray(relacl):
            acl = skytools.parse_acl(sacl)
            if not acl:
                continue
            tup_list.append(acl)
        return tup_list

    def __init__(self, table_name, row, new_name = None):
        self.name = table_name
        self.acl_list = self.parse_relacl(row['relacl'])

    def get_create_sql(self, curs, new_name = None):
        """Generate creation SQL."""
        if not new_name:
            new_name = self.name

        qtarget = quote_fqident(new_name)

        sql_list = []
        for role, acl, who in self.acl_list:
            qrole = quote_ident(role)
            astr1, astr2 = self.acl_to_grants(acl)
            if astr1:
                sql = "GRANT %s ON %s\n  TO %s;" % (astr1, qtarget, qrole)
                sql_list.append(sql)
            if astr2:
                sql = "GRANT %s ON %s\n  TO %s WITH GRANT OPTION;" % (astr2, qtarget, qrole)
                sql_list.append(sql)
        return "\n".join(sql_list)

    def get_drop_sql(self, curs):
        sql_list = []
        for user, acl, who in self.acl_list:
            sql = "REVOKE ALL FROM %s ON %s;" % (quote_ident(user), quote_fqident(self.name))
            sql_list.append(sql)
        return "\n".join(sql_list)

class TColumnDefault(TElem):
    """Info about table column default value."""
    type = T_DEFAULT
    SQL = """
        select a.attname as name, pg_get_expr(d.adbin, d.adrelid) as expr
          from pg_attribute a left join pg_attrdef d
            on (d.adrelid = a.attrelid and d.adnum = a.attnum)
         where a.attrelid = %(oid)s
           and not a.attisdropped
           and a.atthasdef
           and a.attnum > 0
         order by a.attnum;
    """
    def __init__(self, table_name, row):
        self.table_name = table_name
        self.name = row['name']
        self.expr = row['expr']

    def get_create_sql(self, curs, new_name = None):
        """Generate creation SQL."""
        tbl = new_name or self.table_name
        sql = "ALTER TABLE ONLY %s ALTER COLUMN %s\n  SET DEFAULT %s;" % (
                quote_fqident(tbl), quote_ident(self.name), self.expr)
        return sql

    def get_drop_sql(self, curs):
        return "ALTER TABLE %s ALTER COLUMN %s\n  DROP DEFAULT;" % (
                quote_fqident(self.table_name), quote_ident(self.name))

class TColumn(TElem):
    """Info about table column."""
    SQL = """
        select a.attname as name,
               quote_ident(a.attname) as qname,
               format_type(a.atttypid, a.atttypmod) as dtype,
               a.attnotnull,
               (select max(char_length(aa.attname))
                  from pg_attribute aa where aa.attrelid = %(oid)s) as maxcol,
               pg_get_serial_sequence(%(fq2name)s, a.attname) as seqname
          from pg_attribute a left join pg_attrdef d
            on (d.adrelid = a.attrelid and d.adnum = a.attnum)
         where a.attrelid = %(oid)s
           and not a.attisdropped
           and a.attnum > 0
         order by a.attnum;
    """
    seqname = None
    def __init__(self, table_name, row):
        self.name = row['name']

        fname = row['qname'].ljust(row['maxcol'] + 3)
        self.column_def = fname + ' ' + row['dtype']
        if row['attnotnull']:
            self.column_def += ' not null'

        self.sequence = None
        if row['seqname']:
            self.seqname = skytools.unquote_fqident(row['seqname'])


class TGPDistKey(TElem):
    """Info about GreenPlum table distribution keys"""
    SQL = """
        select a.attname as name
          from pg_attribute a, gp_distribution_policy p
        where p.localoid = %(oid)s
          and a.attrelid = %(oid)s
          and a.attnum = any(p.attrnums)
        order by a.attnum;
        """
    def __init__(self, table_name, row):
        self.name = row['name']


class TTable(TElem):
    """Info about table only (columns)."""
    type = T_TABLE
    def __init__(self, table_name, col_list, dist_key_list = None):
        self.name = table_name
        self.col_list = col_list
        self.dist_key_list = dist_key_list

    def get_create_sql(self, curs, new_name = None):
        """Generate creation SQL."""
        if not new_name:
            new_name = self.name
        sql = "CREATE TABLE %s (" % quote_fqident(new_name)
        sep = "\n    "
        for c in self.col_list:
            sql += sep + c.column_def
            sep = ",\n    "
        sql += "\n)"
        if self.dist_key_list is not None:
            if self.dist_key_list != []:
                sql += "\ndistributed by(%s)" % ','.join(c.name for c
                                                         in self.dist_key_list)
            else:
                sql += '\ndistributed randomly'

        sql += ";"
        return sql

    def get_drop_sql(self, curs):
        return "DROP TABLE %s;" % quote_fqident(self.name)


class TSeq(TElem):
    """Info about sequence."""
    type = T_SEQUENCE
    SQL = """SELECT *, %(owner)s as "owner" from %(fqname)s """
    def __init__(self, seq_name, row):
        self.name = seq_name
        defn = ''
        self.owner = row['owner']
        if row['increment_by'] != 1:
            defn += ' INCREMENT BY %d' % row['increment_by']
        if row['min_value'] != 1:
            defn += ' MINVALUE %d' % row['min_value']
        if row['max_value'] != 9223372036854775807:
            defn += ' MAXVALUE %d' % row['max_value']
        last_value = row['last_value']
        if row['is_called']:
            last_value += row['increment_by']
            if last_value >= row['max_value']:
                raise Exception('duh, seq passed max_value')
        if last_value != 1:
            defn += ' START %d' % last_value
        if row['cache_value'] != 1:
            defn += ' CACHE %d' % row['cache_value']
        if row['is_cycled']:
            defn += ' CYCLE '
        if self.owner:
            defn += ' OWNED BY %s' % self.owner
        self.defn = defn

    def get_create_sql(self, curs, new_seq_name = None):
        """Generate creation SQL."""

        # we are in table def, forget full def
        if self.owner:
            sql = "ALTER SEQUENCE %s\n  OWNED BY %s;" % (
                    quote_fqident(self.name), self.owner )
            return sql

        name = self.name
        if new_seq_name:
            name = new_seq_name
        sql = 'CREATE SEQUENCE %s %s;' % (quote_fqident(name), self.defn)
        return sql

    def get_drop_sql(self, curs):
        if self.owner:
            return ''
        return 'DROP SEQUENCE %s;' % quote_fqident(self.name)

#
# Main table object, loads all the others
#

class BaseStruct(object):
    """Collects and manages all info about a higher-level db object.

    Allow to issue CREATE/DROP statements about any
    group of elements.
    """
    object_list = []
    def __init__(self, curs, name):
        """Initializes class by loading info about table_name from database."""

        self.name = name
        self.fqname = quote_fqident(name)

    def _load_elem(self, curs, name, args, eclass):
        """Fetch element(s) from db."""
        elem_list = []
        #print "Loading %s, name=%s, args=%s" % (repr(eclass), repr(name), repr(args))
        sql = eclass.get_load_sql(curs.connection.server_version)
        curs.execute(sql % args)
        for row in curs.fetchall():
            elem_list.append(eclass(name, row))
        return elem_list

    def create(self, curs, objs, new_table_name = None, log = None):
        """Issues CREATE statements for requested set of objects.

        If new_table_name is giver, creates table under that name
        and also tries to rename all indexes/constraints that conflict
        with existing table.
        """

        for o in self.object_list:
            if o.type & objs:
                sql = o.get_create_sql(curs, new_table_name)
                if not sql:
                    continue
                if log:
                    log.info('Creating %s' % o.name)
                    log.debug(sql)
                curs.execute(sql)

    def drop(self, curs, objs, log = None):
        """Issues DROP statements for requested set of objects."""
        # make sure the creating & dropping happen in reverse order
        olist = self.object_list[:]
        olist.reverse()
        for o in olist:
            if o.type & objs:
                sql = o.get_drop_sql(curs)
                if not sql:
                    continue
                if log:
                    log.info('Dropping %s' % o.name)
                    log.debug(sql)
                curs.execute(sql)

    def get_create_sql(self, objs):
        res = []
        for o in self.object_list:
            if o.type & objs:
                sql = o.get_create_sql(None, None)
                if sql:
                    res.append(sql)
        return "".join(res)

class TableStruct(BaseStruct):
    """Collects and manages all info about table.

    Allow to issue CREATE/DROP statements about any
    group of elements.
    """
    def __init__(self, curs, table_name):
        """Initializes class by loading info about table_name from database."""

        BaseStruct.__init__(self, curs, table_name)

        self.table_name = table_name

        # fill args
        schema, name = skytools.fq_name_parts(table_name)
        args = {
            'schema': schema,
            'table': name,
            'fqname': self.fqname,
            'fq2name': skytools.quote_literal(self.fqname),
            'oid': skytools.get_table_oid(curs, table_name),
            'pg_class_oid': skytools.get_table_oid(curs, 'pg_catalog.pg_class'),
        }

        # load table struct
        self.col_list = self._load_elem(curs, self.name, args, TColumn)
        # if db is GP then read also table distribution keys
        if skytools.exists_table(curs, "pg_catalog.gp_distribution_policy"):
            self.dist_key_list = self._load_elem(curs, self.name, args,
                                                 TGPDistKey)
        else:
            self.dist_key_list = None
        self.object_list = [ TTable(table_name, self.col_list,
                                    self.dist_key_list) ]
        self.seq_list = []

        # load seqs
        for col in self.col_list:
            if col.seqname:
                fqname = quote_fqident(col.seqname)
                owner = self.fqname + '.' + quote_ident(col.name)
                seq_args = { 'fqname': fqname, 'owner': skytools.quote_literal(owner) }
                self.seq_list += self._load_elem(curs, col.seqname, seq_args, TSeq)
        self.object_list += self.seq_list

        # load additional objects
        to_load = [TColumnDefault, TConstraint, TIndex, TTrigger,
                   TRule, TGrant, TOwner, TParent]
        for eclass in to_load:
            self.object_list += self._load_elem(curs, self.name, args, eclass)

    def get_column_list(self):
        """Returns list of column names the table has."""

        res = []
        for c in self.col_list:
            res.append(c.name)
        return res

class SeqStruct(BaseStruct):
    """Collects and manages all info about sequence.

    Allow to issue CREATE/DROP statements about any
    group of elements.
    """
    def __init__(self, curs, seq_name):
        """Initializes class by loading info about table_name from database."""

        BaseStruct.__init__(self, curs, seq_name)

        # fill args
        args = { 'fqname': self.fqname, 'owner': 'null' }

        # load table struct
        self.object_list = self._load_elem(curs, seq_name, args, TSeq)

def test():
    from skytools import connect_database
    db = connect_database("dbname=fooz")
    curs = db.cursor()

    s = TableStruct(curs, "public.data1")

    s.drop(curs, T_ALL)
    s.create(curs, T_ALL)
    s.create(curs, T_ALL, "data1_new")
    s.create(curs, T_PKEY)

if __name__ == '__main__':
    test()


########NEW FILE########
__FILENAME__ = fileutil
"""File utilities

>>> import tempfile, os
>>> pidfn = tempfile.mktemp('.pid')
>>> write_atomic(pidfn, "1")
>>> write_atomic(pidfn, "2")
>>> os.remove(pidfn)
>>> write_atomic(pidfn, "1", '.bak')
>>> write_atomic(pidfn, "2", '.bak')
>>> os.remove(pidfn)
"""

import sys
import os
import errno

__all__ = ['write_atomic', 'signal_pidfile']

# non-win32
def write_atomic(fn, data, bakext=None, mode='b'):
    """Write file with rename."""

    if mode not in ['', 'b', 't']:
        raise ValueError("unsupported fopen mode")

    # write new data to tmp file
    fn2 = fn + '.new'
    f = open(fn2, 'w' + mode)
    f.write(data)
    f.close()

    # link old data to bak file
    if bakext:
        if bakext.find('/') >= 0:
            raise ValueError("invalid bakext")
        fnb = fn + bakext
        try:
            os.unlink(fnb)
        except OSError, e:
            if e.errno != errno.ENOENT:
                raise
        try:
            os.link(fn, fnb)
        except OSError, e:
            if e.errno != errno.ENOENT:
                raise

    # win32 does not like replace
    if sys.platform == 'win32':
        try:
            os.remove(fn)
        except:
            pass

    # atomically replace file
    os.rename(fn2, fn)

def signal_pidfile(pidfile, sig):
    """Send a signal to process whose ID is located in pidfile.

    Read only first line of pidfile to support multiline
    pidfiles like postmaster.pid.

    Returns True is successful, False if pidfile does not exist
    or process itself is dead.  Any other errors will passed
    as exceptions."""

    ln = ''
    try:
        f = open(pidfile, 'r')
        ln = f.readline().strip()
        f.close()
        pid = int(ln)
        if sig == 0 and sys.platform == 'win32':
            return win32_detect_pid(pid)
        os.kill(pid, sig)
        return True
    except IOError, ex:
        if ex.errno != errno.ENOENT:
            raise
    except OSError, ex:
        if ex.errno != errno.ESRCH:
            raise
    except ValueError, ex:
        # this leaves slight race when someone is just creating the file,
        # but more common case is old empty file.
        if not ln:
            return False
        raise ValueError('Corrupt pidfile: %s' % pidfile)
    return False

def win32_detect_pid(pid):
    """Process detection for win32."""

    # avoid pywin32 dependecy, use ctypes instead
    import ctypes

    # win32 constants
    PROCESS_QUERY_INFORMATION = 1024
    STILL_ACTIVE = 259
    ERROR_INVALID_PARAMETER = 87
    ERROR_ACCESS_DENIED = 5

    # Load kernel32.dll
    k = ctypes.windll.kernel32
    OpenProcess = k.OpenProcess
    OpenProcess.restype = ctypes.c_void_p

    # query pid exit code
    h = OpenProcess(PROCESS_QUERY_INFORMATION, 0, pid)
    if h == None:
        err = k.GetLastError()
        if err == ERROR_INVALID_PARAMETER:
            return False
        if err == ERROR_ACCESS_DENIED:
            return True
        raise OSError(errno.EFAULT, "Unknown win32error: " + str(err))
    code = ctypes.c_int()
    k.GetExitCodeProcess(h, ctypes.byref(code))
    k.CloseHandle(h)
    return code.value == STILL_ACTIVE

def win32_write_atomic(fn, data, bakext=None, mode='b'):
    """Write file with rename for win32."""

    if mode not in ['', 'b', 't']:
        raise ValueError("unsupported fopen mode")

    # write new data to tmp file
    fn2 = fn + '.new'
    f = open(fn2, 'w' + mode)
    f.write(data)
    f.close()

    # move old data to bak file
    if bakext:
        if bakext.find('/') >= 0:
            raise ValueError("invalid bakext")
        fnb = fn + bakext
        try:
            os.remove(fnb)
        except OSError, e:
            if e.errno != errno.ENOENT:
                raise
        try:
            os.rename(fn, fnb)
        except OSError, e:
            if e.errno != errno.ENOENT:
                raise
    else:
        try:
            os.remove(fn)
        except:
            pass

    # replace file
    os.rename(fn2, fn)

if sys.platform == 'win32':
    write_atomic = win32_write_atomic

if __name__ == '__main__':
    import doctest
    doctest.testmod()


########NEW FILE########
__FILENAME__ = gzlog

"""Atomic append of gzipped data.

The point is - if several gzip streams are concatenated,
they are read back as one whole stream.
"""

import gzip
from cStringIO import StringIO

__all__ = ['gzip_append']

#
# gzip storage
#
def gzip_append(filename, data, level = 6):
    """Append a block of data to file with safety checks."""

    # compress data
    buf = StringIO()
    g = gzip.GzipFile(fileobj = buf, compresslevel = level, mode = "w")
    g.write(data)
    g.close()
    zdata = buf.getvalue()

    # append, safely
    f = open(filename, "a+", 0)
    f.seek(0, 2)
    pos = f.tell()
    try:
        f.write(zdata)
        f.close()
    except Exception, ex:
        # rollback on error
        f.seek(pos, 0)
        f.truncate()
        f.close()
        raise ex

########NEW FILE########
__FILENAME__ = hashtext
"""
Implementation of Postgres hashing function.

hashtext_old() - used up to PostgreSQL 8.3
hashtext_new() - used since PostgreSQL 8.4

>>> import skytools._chashtext
>>> for i in range(3):
...     print [hashtext_new_py('x' * (i*5 + j)) for j in range(5)]
[-1477818771, 1074944137, -1086392228, -1992236649, -1379736791]
[-370454118, 1489915569, -66683019, -2126973000, 1651296771]
[755764456, -1494243903, 631527812, 28686851, -9498641]
>>> for i in range(3):
...     print [hashtext_old_py('x' * (i*5 + j)) for j in range(5)]
[-863449762, 37835117, 294739542, -320432768, 1007638138]
[1422906842, -261065348, 59863994, -162804943, 1736144510]
[-682756517, 317827663, -495599455, -1411793989, 1739997714]
>>> data = 'HypficUjFitraxlumCitcemkiOkIkthi'
>>> p = [hashtext_old_py(data[:l]) for l in range(len(data)+1)]
>>> c = [hashtext_old(data[:l]) for l in range(len(data)+1)]
>>> assert p == c, '%s <> %s' % (p, c)
>>> p == c
True
>>> p = [hashtext_new_py(data[:l]) for l in range(len(data)+1)]
>>> c = [hashtext_new(data[:l]) for l in range(len(data)+1)]
>>> assert p == c, '%s <> %s' % (p, c)
>>> p == c
True
"""

import sys, struct

__all__ = ["hashtext_old", "hashtext_new"]

# pad for last partial block
PADDING = '\0' * 12

def uint32(x):
    """python does not have 32 bit integer so we need this hack to produce uint32 after bit operations"""
    return x & 0xffffffff

#
# Old Postgres hashtext() - lookup2 with custom initval
#

FMT_OLD = struct.Struct("<LLL")

def mix_old(a,b,c):
    c = uint32(c)

    a -= b; a -= c; a = uint32(a ^ (c>>13))
    b -= c; b -= a; b = uint32(b ^ (a<<8))
    c -= a; c -= b; c = uint32(c ^ (b>>13))
    a -= b; a -= c; a = uint32(a ^ (c>>12))
    b -= c; b -= a; b = uint32(b ^ (a<<16))
    c -= a; c -= b; c = uint32(c ^ (b>>5))
    a -= b; a -= c; a = uint32(a ^ (c>>3))
    b -= c; b -= a; b = uint32(b ^ (a<<10))
    c -= a; c -= b; c = uint32(c ^ (b>>15))

    return a, b, c

def hashtext_old_py(k):
    """Old Postgres hashtext()"""

    remain = len(k)
    pos = 0
    a = b = 0x9e3779b9
    c = 3923095

    # handle most of the key
    while remain >= 12:
        a2, b2, c2 = FMT_OLD.unpack_from(k, pos)
        a, b, c = mix_old(a + a2, b + b2, c + c2)
        pos += 12;
        remain -= 12;

    # handle the last 11 bytes
    a2, b2, c2 = FMT_OLD.unpack_from(k[pos:] + PADDING, 0)

    # the lowest byte of c is reserved for the length
    c2 = (c2 << 8) + len(k)

    a, b, c = mix_old(a + a2, b + b2, c + c2)

    # convert to signed int
    if (c & 0x80000000):
        c = -0x100000000 + c

    return int(c)

#
# New Postgres hashtext() - hacked lookup3:
# - custom initval
# - calls mix() when len=12
# - shifted c in last block on little-endian
#

FMT_NEW = struct.Struct("=LLL")

def rol32(x,k):
    return (((x)<<(k)) | (uint32(x)>>(32-(k))))

def mix_new(a,b,c):
    a -= c;  a ^= rol32(c, 4);  c += b
    b -= a;  b ^= rol32(a, 6);  a += c
    c -= b;  c ^= rol32(b, 8);  b += a
    a -= c;  a ^= rol32(c,16);  c += b
    b -= a;  b ^= rol32(a,19);  a += c
    c -= b;  c ^= rol32(b, 4);  b += a

    return uint32(a), uint32(b), uint32(c)

def final_new(a,b,c):
    c ^= b; c -= rol32(b,14)
    a ^= c; a -= rol32(c,11)
    b ^= a; b -= rol32(a,25)
    c ^= b; c -= rol32(b,16)
    a ^= c; a -= rol32(c, 4)
    b ^= a; b -= rol32(a,14)
    c ^= b; c -= rol32(b,24)

    return uint32(a), uint32(b), uint32(c)

def hashtext_new_py(k):
    """New Postgres hashtext()"""
    remain = len(k)
    pos = 0
    a = b = c = 0x9e3779b9 + len(k) + 3923095

    # handle most of the key
    while remain >= 12:
        a2, b2, c2 = FMT_NEW.unpack_from(k, pos)
        a, b, c = mix_new(a + a2, b + b2, c + c2)
        pos += 12;
        remain -= 12;

    # handle the last 11 bytes
    a2, b2, c2 = FMT_NEW.unpack_from(k[pos:] + PADDING, 0)
    if sys.byteorder == 'little':
        c2 = c2 << 8
    a, b, c = final_new(a + a2, b + b2, c + c2)

    # convert to signed int
    if (c & 0x80000000):
        c = -0x100000000 + c

    return int(c)


try:
    from skytools._chashtext import hashtext_old, hashtext_new
except ImportError:
    hashtext_old = hashtext_old_py
    hashtext_new = hashtext_new_py


# run doctest
if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = natsort
"""Natural sort.

Compares numeric parts numerically.
"""

# Based on idea at http://code.activestate.com/recipes/285264/
# Works with both Python 2.x and 3.x
# Ignores leading zeroes: 001 and 01 are considered equal

import re as _re
_rc = _re.compile(r'\d+|\D+')

__all__ = ['natsort_key', 'natsort', 'natsorted',
        'natsort_key_icase', 'natsort_icase', 'natsorted_icase']

def natsort_key(s):
    """Split string to numeric and non-numeric fragments."""
    return [ not f[0].isdigit() and f or int(f, 10) for f in _rc.findall(s) ]

def natsort(lst):
    """Natural in-place sort, case-sensitive."""
    lst.sort(key = natsort_key)

def natsorted(lst):
    """Return copy of list, sorted in natural order, case-sensitive.

    >>> natsorted(['ver-1.1', 'ver-1.11', '', 'ver-1.0'])
    ['', 'ver-1.0', 'ver-1.1', 'ver-1.11']
    """
    lst = lst[:]
    natsort(lst)
    return lst

# case-insensitive api

def natsort_key_icase(s):
    """Split string to numeric and non-numeric fragments."""
    return natsort_key(s.lower())

def natsort_icase(lst):
    """Natural in-place sort, case-sensitive."""
    lst.sort(key = natsort_key_icase)

def natsorted_icase(lst):
    """Return copy of list, sorted in natural order, case-sensitive.
    
    >>> natsorted_icase(['Ver-1.1', 'vEr-1.11', '', 'veR-1.0'])
    ['', 'veR-1.0', 'Ver-1.1', 'vEr-1.11']
    """
    lst = lst[:]
    natsort_icase(lst)
    return lst


# run doctest
if __name__ == '__main__':
    import doctest
    doctest.testmod()


########NEW FILE########
__FILENAME__ = parsing

"""Various parsers for Postgres-specific data formats."""

import re
import skytools

__all__ = [
    "parse_pgarray", "parse_logtriga_sql", "parse_tabbed_table",
    "parse_statements", 'sql_tokenizer', 'parse_sqltriga_sql',
    "parse_acl", "dedent", "hsize_to_bytes",
    "parse_connect_string", "merge_connect_string"]

_rc_listelem = re.compile(r'( [^,"}]+ | ["] ( [^"\\]+ | [\\]. )* ["] )', re.X)

def parse_pgarray(array):
    r"""Parse Postgres array and return list of items inside it.

    Examples:
    >>> parse_pgarray('{}')
    []
    >>> parse_pgarray('{a,b,null,"null"}')
    ['a', 'b', None, 'null']
    >>> parse_pgarray(r'{"a,a","b\"b","c\\c"}')
    ['a,a', 'b"b', 'c\\c']
    >>> parse_pgarray("[0,3]={1,2,3}")
    ['1', '2', '3']
    """
    if array is None:
        return None
    if not array or array[0] not in ("{", "[") or array[-1] != '}':
        raise Exception("bad array format: must be surrounded with {}")
    res = []
    pos = 1
    # skip optional dimensions descriptor "[a,b]={...}"
    if array[0] == "[":
        pos = array.find('{') + 1
        if pos < 1:
            raise Exception("bad array format: must be surrounded with {}")
    while 1:
        m = _rc_listelem.search(array, pos)
        if not m:
            break
        pos2 = m.end()
        item = array[pos:pos2]
        if len(item) == 4 and item.upper() == "NULL":
            val = None
        else:
            if len(item) > 0 and item[0] == '"':
                if len(item) == 1 or item[-1] != '"':
                    raise Exception("bad array format: broken '\"'")
                item = item[1:-1]
            val = skytools.unescape(item)
        res.append(val)

        pos = pos2 + 1
        if array[pos2] == "}":
            break
        elif array[pos2] != ",":
            raise Exception("bad array format: expected ,} got " + repr(array[pos2]))
    if pos < len(array) - 1:
        raise Exception("bad array format: failed to parse completely (pos=%d len=%d)" % (pos, len(array)))
    return res

#
# parse logtriga partial sql
#

class _logtriga_parser:
    """Parses logtriga/sqltriga partial SQL to values."""
    def tokenizer(self, sql):
        """Token generator."""
        for typ, tok in sql_tokenizer(sql, ignore_whitespace = True):
            yield tok

    def parse_insert(self, tk, fields, values, key_fields, key_values):
        """Handler for inserts."""
        # (col1, col2) values ('data', null)
        if tk.next() != "(":
            raise Exception("syntax error")
        while 1:
            fields.append(tk.next())
            t = tk.next()
            if t == ")":
                break
            elif t != ",":
                raise Exception("syntax error")
        if tk.next().lower() != "values":
            raise Exception("syntax error, expected VALUES")
        if tk.next() != "(":
            raise Exception("syntax error, expected (")
        while 1:
            values.append(tk.next())
            t = tk.next()
            if t == ")":
                break
            if t == ",":
                continue
            raise Exception("expected , or ) got "+t)
        t = tk.next()
        raise Exception("expected EOF, got " + repr(t))

    def parse_update(self, tk, fields, values, key_fields, key_values):
        """Handler for updates."""
        # col1 = 'data1', col2 = null where pk1 = 'pk1' and pk2 = 'pk2'
        while 1:
            fields.append(tk.next())
            if tk.next() != "=":
                raise Exception("syntax error")
            values.append(tk.next())
            t = tk.next()
            if t == ",":
                continue
            elif t.lower() == "where":
                break
            else:
                raise Exception("syntax error, expected WHERE or , got "+repr(t))
        while 1:
            fld = tk.next()
            key_fields.append(fld)
            self.pklist.append(fld)
            if tk.next() != "=":
                raise Exception("syntax error")
            key_values.append(tk.next())
            t = tk.next()
            if t.lower() != "and":
                raise Exception("syntax error, expected AND got "+repr(t))

    def parse_delete(self, tk, fields, values, key_fields, key_values):
        """Handler for deletes."""
        # pk1 = 'pk1' and pk2 = 'pk2'
        while 1:
            fld = tk.next()
            key_fields.append(fld)
            self.pklist.append(fld)
            if tk.next() != "=":
                raise Exception("syntax error")
            key_values.append(tk.next())
            t = tk.next()
            if t.lower() != "and":
                raise Exception("syntax error, expected AND, got "+repr(t))

    def _create_dbdict(self, fields, values):
        fields = [skytools.unquote_ident(f) for f in fields]
        values = [skytools.unquote_literal(f) for f in values]
        return skytools.dbdict(zip(fields, values))

    def parse_sql(self, op, sql, pklist=None, splitkeys=False):
        """Main entry point."""
        if pklist is None:
            self.pklist = []
        else:
            self.pklist = pklist
        tk = self.tokenizer(sql)
        fields = []
        values = []
        key_fields = []
        key_values = []
        try:
            if op == "I":
                self.parse_insert(tk, fields, values, key_fields, key_values)
            elif op == "U":
                self.parse_update(tk, fields, values, key_fields, key_values)
            elif op == "D":
                self.parse_delete(tk, fields, values, key_fields, key_values)
            raise Exception("syntax error")
        except StopIteration:
            # last sanity check
            if (len(fields) + len(key_fields) == 0 or
                len(fields) != len(values) or
                len(key_fields) != len(key_values)):
                raise Exception("syntax error, fields do not match values")
        if splitkeys:
            return (self._create_dbdict(key_fields, key_values),
                    self._create_dbdict(fields, values))
        return self._create_dbdict(fields + key_fields, values + key_values)

def parse_logtriga_sql(op, sql, splitkeys=False):
    return parse_sqltriga_sql(op, sql, splitkeys=splitkeys)

def parse_sqltriga_sql(op, sql, pklist=None, splitkeys=False):
    """Parse partial SQL used by pgq.sqltriga() back to data values.

    Parser has following limitations:
     - Expects standard_quoted_strings = off
     - Does not support dollar quoting.
     - Does not support complex expressions anywhere. (hashtext(col1) = hashtext(val1))
     - WHERE expression must not contain IS (NOT) NULL
     - Does not support updating pk value, unless you use the splitkeys parameter.

    Returns dict of col->data pairs.

    Insert event:
    >>> parse_logtriga_sql('I', '(id, data) values (1, null)')
    {'data': None, 'id': '1'}

    Update event:
    >>> parse_logtriga_sql('U', "data='foo' where id = 1")
    {'data': 'foo', 'id': '1'}

    Delete event:
    >>> parse_logtriga_sql('D', "id = 1 and id2 = 'str''val'")
    {'id2': "str'val", 'id': '1'}

    If you set the splitkeys parameter, it will return two dicts, one for key
    fields and one for data fields.

    Insert event:
    >>> parse_logtriga_sql('I', '(id, data) values (1, null)', splitkeys=True)
    ({}, {'data': None, 'id': '1'})

    Update event:
    >>> parse_logtriga_sql('U', "data='foo' where id = 1", splitkeys=True)
    ({'id': '1'}, {'data': 'foo'})

    Delete event:
    >>> parse_logtriga_sql('D', "id = 1 and id2 = 'str''val'", splitkeys=True)
    ({'id2': "str'val", 'id': '1'}, {})

    """
    return _logtriga_parser().parse_sql(op, sql, pklist, splitkeys=splitkeys)


def parse_tabbed_table(txt):
    r"""Parse a tab-separated table into list of dicts.

    Expect first row to be column names.

    Very primitive.

    Example:
    >>> parse_tabbed_table('col1\tcol2\nval1\tval2\n')
    [{'col2': 'val2', 'col1': 'val1'}]
    """

    txt = txt.replace("\r\n", "\n")
    fields = None
    data = []
    for ln in txt.split("\n"):
        if not ln:
            continue
        if not fields:
            fields = ln.split("\t")
            continue
        cols = ln.split("\t")
        if len(cols) != len(fields):
            continue
        row = dict(zip(fields, cols))
        data.append(row)
    return data


_extstr = r""" ['] (?: [^'\\]+ | \\. | [']['] )* ['] """
_stdstr = r""" ['] (?: [^']+ | [']['] )* ['] """
_name = r""" (?: [a-z_][a-z0-9_$]* | " (?: [^"]+ | "" )* " ) """

_ident   = r""" (?P<ident> %s ) """ % _name
_fqident = r""" (?P<ident> %s (?: \. %s )* ) """ % (_name, _name)

_base_sql = r"""
      (?P<dolq>   (?P<dname> [$] (?: [_a-z][_a-z0-9]*)? [$] )
                  .*?
                  (?P=dname) )
    | (?P<num>    [0-9][0-9.e]* )
    | (?P<numarg> [$] [0-9]+ )
    | (?P<pyold>  [%][(] [a-z_][a-z0-9_]* [)] [s] )
    | (?P<pynew>  [{] [^{}]+ [}] )
    | (?P<ws>     (?: \s+ | [/][*] .*? [*][/] | [-][-][^\n]* )+ )
    | (?P<sym>    (?: [-+*~!@#^&|?/%<>=]+ | [,()\[\].:;] ) )
    | (?P<error>  . )"""

_base_sql_fq = r"%s | %s" % (_fqident, _base_sql)
_base_sql    = r"%s | %s" % (_ident, _base_sql)

_std_sql    = r"""(?: (?P<str> [E] %s | %s ) | %s )""" % (_extstr, _stdstr, _base_sql)
_std_sql_fq = r"""(?: (?P<str> [E] %s | %s ) | %s )""" % (_extstr, _stdstr, _base_sql_fq)
_ext_sql    = r"""(?: (?P<str> [E]? %s ) | %s )""" % (_extstr, _base_sql)
_ext_sql_fq = r"""(?: (?P<str> [E]? %s ) | %s )""" % (_extstr, _base_sql_fq)
_std_sql_rc = _ext_sql_rc = None
_std_sql_fq_rc = _ext_sql_fq_rc = None

def sql_tokenizer(sql, standard_quoting = False, ignore_whitespace = False,
                  fqident = False, show_location = False):
    r"""Parser SQL to tokens.

    Iterator, returns (toktype, tokstr) tuples.

    Example
    >>> [x for x in sql_tokenizer("select * from a.b", ignore_whitespace=True)]
    [('ident', 'select'), ('sym', '*'), ('ident', 'from'), ('ident', 'a'), ('sym', '.'), ('ident', 'b')]
    >>> [x for x in sql_tokenizer("\"c olumn\",'str''val'")]
    [('ident', '"c olumn"'), ('sym', ','), ('str', "'str''val'")]
    >>> list(sql_tokenizer('a.b a."b "" c" a.1', fqident=True, ignore_whitespace=True))
    [('ident', 'a.b'), ('ident', 'a."b "" c"'), ('ident', 'a'), ('sym', '.'), ('num', '1')]
    """
    global _std_sql_rc, _ext_sql_rc, _std_sql_fq_rc, _ext_sql_fq_rc
    if not _std_sql_rc:
        _std_sql_rc = re.compile(_std_sql, re.X | re.I | re.S)
        _ext_sql_rc = re.compile(_ext_sql, re.X | re.I | re.S)
        _std_sql_fq_rc = re.compile(_std_sql_fq, re.X | re.I | re.S)
        _ext_sql_fq_rc = re.compile(_ext_sql_fq, re.X | re.I | re.S)

    if standard_quoting:
        if fqident:
            rc = _std_sql_fq_rc
        else:
            rc = _std_sql_rc
    else:
        if fqident:
            rc = _ext_sql_fq_rc
        else:
            rc = _ext_sql_rc

    pos = 0
    while 1:
        m = rc.match(sql, pos)
        if not m:
            break
        pos = m.end()
        typ = m.lastgroup
        if ignore_whitespace and typ == "ws":
            continue
        tk = m.group()
        if show_location:
            yield (typ, tk, pos)
        else:
            yield (typ, tk)

_copy_from_stdin_re = "copy.*from\s+stdin"
_copy_from_stdin_rc = None
def parse_statements(sql, standard_quoting = False):
    """Parse multi-statement string into separate statements.

    Returns list of statements.

    >>> [sql for sql in parse_statements("begin; select 1; select 'foo'; end;")]
    ['begin;', 'select 1;', "select 'foo';", 'end;']
    """

    global _copy_from_stdin_rc
    if not _copy_from_stdin_rc:
        _copy_from_stdin_rc = re.compile(_copy_from_stdin_re, re.X | re.I)
    tokens = []
    pcount = 0 # '(' level
    for typ, t in sql_tokenizer(sql, standard_quoting = standard_quoting):
        # skip whitespace and comments before statement
        if len(tokens) == 0 and typ == "ws":
            continue
        # keep the rest
        tokens.append(t)
        if t == "(":
            pcount += 1
        elif t == ")":
            pcount -= 1
        elif t == ";" and pcount == 0:
            sql = "".join(tokens)
            if _copy_from_stdin_rc.match(sql):
                raise Exception("copy from stdin not supported")
            yield ("".join(tokens))
            tokens = []
    if len(tokens) > 0:
        yield ("".join(tokens))
    if pcount != 0:
        raise Exception("syntax error - unbalanced parenthesis")

_acl_name = r'(?: [0-9a-z_]+ | " (?: [^"]+ | "" )* " )'
_acl_re = r'''
    \s* (?: group \s+ | user \s+ )?
    (?P<tgt> %s )?
    (?P<perm> = [a-z*]*  )?
    (?P<owner> / %s )?
    \s* $
    ''' % (_acl_name, _acl_name)
_acl_rc = None

def parse_acl(acl):
    """Parse ACL entry.

    >>> parse_acl('user=rwx/owner')
    ('user', 'rwx', 'owner')
    >>> parse_acl('" ""user"=rwx/" ""owner"')
    (' "user', 'rwx', ' "owner')
    >>> parse_acl('user=rwx')
    ('user', 'rwx', None)
    >>> parse_acl('=/f')
    (None, '', 'f')
    """
    global _acl_rc
    if not _acl_rc:
        _acl_rc = re.compile(_acl_re, re.I | re.X)

    m = _acl_rc.match(acl)
    if not m:
        return None

    target = m.group('tgt')
    perm = m.group('perm')
    owner = m.group('owner')

    if target:
        target = skytools.unquote_ident(target)
    if perm:
        perm = perm[1:]
    if owner:
        owner = skytools.unquote_ident(owner[1:])

    return (target, perm, owner)


def dedent(doc):
    r"""Relaxed dedent.

    - takes whitespace to be removed from first indented line.
    - allows empty or non-indented lines at the start
    - allows first line to be unindented
    - skips empty lines at the start
    - ignores indent of empty lines
    - if line does not match common indent, is stays unchanged

    >>> dedent('  Line1:\n    Line 2\n')
    'Line1:\n  Line 2\n'
    >>> dedent('  \nLine1:\n  Line 2\n Line 3\n    Line 4')
    'Line1:\nLine 2\n Line 3\n  Line 4\n'
    """
    pfx = None
    res = []
    for ln in doc.splitlines():
        ln = ln.rstrip()
        if not pfx and len(res) < 2:
            if not ln:
                continue
            wslen = len(ln) - len(ln.lstrip())
            pfx = ln[ : wslen]
        if pfx:
            if ln.startswith(pfx):
                ln = ln[ len(pfx) : ]
        res.append(ln)
    res.append('')
    return '\n'.join(res)


def hsize_to_bytes (input):
    """ Convert sizes from human format to bytes (string to integer) """

    assert isinstance (input, str)
    m = re.match (r"^([0-9]+) *([KMGTPEZY]?)B?$", input.strip(), re.IGNORECASE)
    if not m: raise ValueError ("cannot parse: %s" % input)
    units = ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y']
    bytes = int(m.group(1)) * 1024 ** units.index(m.group(2).upper())
    return bytes

#
# Connect string parsing
#

_cstr_rx = r""" \s* (\w+) \s* = \s* ( ' ( \\.| [^'\\] )* ' | \S+ ) \s* """
_cstr_unesc_rx = r"\\(.)"
_cstr_badval_rx = r"[\s'\\]"
_cstr_rc = None
_cstr_unesc_rc = None
_cstr_badval_rc = None

def parse_connect_string(cstr):
    r"""Parse Postgres connect string.

    >>> parse_connect_string("host=foo")
    [('host', 'foo')]
    >>> parse_connect_string(r" host = foo password = ' f\\\o\'o ' ")
    [('host', 'foo'), ('password', "' f\\o'o '")]
    """
    global _cstr_rc, _cstr_unesc_rc
    if not _cstr_rc:
        _cstr_rc = re.compile(_cstr_rx, re.X)
        _cstr_unesc_rc = re.compile(_cstr_unesc_rx)
    pos = 0
    res = []
    while pos < len(cstr):
        m = _cstr_rc.match(cstr, pos)
        if not m:
            raise ValueError('Invalid connect string')
        pos = m.end()
        k = m.group(1)
        v = m.group(2)
        if v[0] == "'":
            v = _cstr_unesc_rc.sub(r"\1", v)
        res.append( (k,v) )
    return res

def merge_connect_string(cstr_arg_list):
    """Put fragments back together.

    >>> merge_connect_string([('host', 'ip'), ('pass', ''), ('x', ' ')])
    "host=ip pass='' x=' '"
    """
    global _cstr_badval_rc
    if not _cstr_badval_rc:
        _cstr_badval_rc = re.compile(_cstr_badval_rx)

    buf = []
    for k, v in cstr_arg_list:
        if not v or _cstr_badval_rc.search(v):
            v = v.replace('\\', r'\\')
            v = v.replace("'", r"\'")
            v = "'" + v + "'"
        buf.append("%s=%s" % (k, v))
    return ' '.join(buf)

if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = plpy_applyrow

"""
PLPY helper module for applying row events from pgq.logutriga().
"""


import plpy

import pkgloader
pkgloader.require('skytools', '3.0')
import skytools

## TODO: automatic fkey detection
# find FK columns
FK_SQL = """
SELECT (SELECT array_agg( (SELECT attname::text FROM pg_attribute
                            WHERE attrelid = conrelid AND attnum = conkey[i]))
          FROM generate_series(1, array_upper(conkey, 1)) i) AS kcols,
       (SELECT array_agg( (SELECT attname::text FROM pg_attribute
                            WHERE attrelid = confrelid AND attnum = confkey[i]))
          FROM generate_series(1, array_upper(confkey, 1)) i) AS fcols,
       confrelid::regclass::text AS ftable
  FROM pg_constraint
 WHERE conrelid = {tbl}::regclass AND contype='f'
"""

class DataError(Exception):
    "Invalid data"

def colfilter_full(rnew, rold):
    return rnew

def colfilter_changed(rnew, rold):
    res = {}
    for k, v in rnew:
        if rnew[k] != rold[k]:
            res[k] = rnew[k]
    return res

def canapply_dummy(rnew, rold):
    return True

def canapply_tstamp_helper(rnew, rold, tscol):
    tnew = rnew[tscol]
    told = rold[tscol]
    if not tnew[0].isdigit():
        raise DataError('invalid timestamp')
    if not told[0].isdigit():
        raise DataError('invalid timestamp')
    return tnew > told

def applyrow(tblname, ev_type, new_row,
             backup_row = None,
             alt_pkey_cols = None,
             fkey_cols = None,
             fkey_ref_table = None,
             fkey_ref_cols = None,
             fn_canapply = canapply_dummy,
             fn_colfilter = colfilter_full):
    """Core logic.  Actual decisions will be done in callback functions.

    - [IUD]: If row referenced by fkey does not exist, event is not applied
    - If pkey does not exist but alt_pkey does, row is not applied.
    
    @param tblname: table name, schema-qualified
    @param ev_type: [IUD]:pkey1,pkey2
    @param alt_pkey_cols: list of alternatice columns to consuder
    @param fkey_cols: columns in this table that refer to other table
    @param fkey_ref_table: other table referenced here
    @param fkey_ref_cols: column in other table that must match
    @param fn_canapply: callback function, gets new and old row, returns whether the row should be applied
    @param fn_colfilter: callback function, gets new and old row, returns dict of final columns to be applied
    """

    gd = None

    # parse ev_type
    tmp = ev_type.split(':', 1)
    if len(tmp) != 2 or tmp[0] not in ('I', 'U', 'D'):
        raise DataError('Unsupported ev_type: '+repr(ev_type))
    if not tmp[1]:
        raise DataError('No pkey in event')

    cmd = tmp[0]
    pkey_cols = tmp[1].split(',')
    qtblname = skytools.quote_fqident(tblname)

    # parse ev_data
    fields = skytools.db_urldecode(new_row)

    if ev_type.find('}') >= 0:
        raise DataError('Really suspicious activity')
    if ",".join(fields.keys()).find('}') >= 0:
        raise DataError('Really suspicious activity 2')

    # generate pkey expressions
    tmp = ["%s = {%s}" % (skytools.quote_ident(k), k) for k in pkey_cols]
    pkey_expr = " and ".join(tmp)
    alt_pkey_expr = None
    if alt_pkey_cols:
        tmp = ["%s = {%s}" % (skytools.quote_ident(k), k) for k in alt_pkey_cols]
        alt_pkey_expr = " and ".join(tmp)

    log = "data ok"

    #
    # Row data seems fine, now apply it
    #

    if fkey_ref_table:
        tmp = []
        for k, rk in zip(fkey_cols, fkey_ref_cols):
            tmp.append("%s = {%s}" % (skytools.quote_ident(rk), k))
        fkey_expr = " and ".join(tmp)
        q = "select 1 from only %s where %s" % (
                skytools.quote_fqident(fkey_ref_table),
                fkey_expr)
        res = skytools.plpy_exec(gd, q, fields)
        if not res:
            return "IGN: parent row does not exist"
        log += ", fkey ok"

    # fetch old row
    if alt_pkey_expr:
        q = "select * from only %s where %s for update" % (qtblname, alt_pkey_expr)
        res = skytools.plpy_exec(gd, q, fields)
        if res:
            oldrow = res[0]
            # if altpk matches, but pk not, then delete
            need_del = 0
            for k in pkey_cols:
                # fixme: proper type cmp?
                if fields[k] != str(oldrow[k]):
                    need_del = 1
                    break
            if need_del:
                log += ", altpk del"
                q = "delete from only %s where %s" % (qtblname, alt_pkey_expr)
                skytools.plpy_exec(gd, q, fields)
                res = None
            else:
                log += ", altpk ok"
    else:
        # no altpk
        q = "select * from only %s where %s for update" % (qtblname, pkey_expr)
        res = skytools.plpy_exec(None, q, fields)

    # got old row, with same pk and altpk
    if res:
        oldrow = res[0]
        log += ", old row"
        ok = fn_canapply(fields, oldrow)
        if ok:
            log += ", new row better"
        if not ok:
            # ignore the update
            return "IGN:" + log + ", current row more up-to-date"
    else:
        log += ", no old row"
        oldrow = None

    if res:
        if cmd == 'I':
            cmd = 'U'
    else:
        if cmd == 'U':
            cmd = 'I'

    # allow column changes
    if oldrow:
        fields2 = fn_colfilter(fields, oldrow)
        for k in pkey_cols:
            if k not in fields2:
                fields2[k] = fields[k]
        fields = fields2

    # apply change
    if cmd == 'I':
        q = skytools.mk_insert_sql(fields, tblname, pkey_cols)
    elif cmd == 'U':
        q = skytools.mk_update_sql(fields, tblname, pkey_cols)
    elif cmd == 'D':
        q = skytools.mk_delete_sql(fields, tblname, pkey_cols)
    else:
        plpy.error('Huh')

    plpy.execute(q)

    return log


def ts_conflict_handler(gd, args):
    """Conflict handling based on timestamp column."""

    conf = skytools.db_urldecode(args[0])
    timefield = conf['timefield']
    ev_type = args[1]
    ev_data = args[2]
    ev_extra1 = args[3]
    ev_extra2 = args[4]
    ev_extra3 = args[5]
    ev_extra4 = args[6]
    altpk = None
    if 'altpk' in conf:
        altpk = conf['altpk'].split(',')

    def ts_canapply(rnew, rold):
        return canapply_tstamp_helper(rnew, rold, timefield)

    return applyrow(ev_extra1, ev_type, ev_data,
                    backup_row = ev_extra2,
                    alt_pkey_cols = altpk,
                    fkey_ref_table = conf.get('fkey_ref_table'),
                    fkey_ref_cols = conf.get('fkey_ref_cols'),
                    fkey_cols = conf.get('fkey_cols'),
                    fn_canapply = ts_canapply)


########NEW FILE########
__FILENAME__ = psycopgwrapper

"""Wrapper around psycopg2.

Database connection provides regular DB-API 2.0 interface.

Connection object methods::

    .cursor()

    .commit()

    .rollback()

    .close()

Cursor methods::

    .execute(query[, args])

    .fetchone()

    .fetchall()


Sample usage::

    db = self.get_database('somedb')
    curs = db.cursor()

    # query arguments as array
    q = "select * from table where id = %s and name = %s"
    curs.execute(q, [1, 'somename'])

    # query arguments as dict
    q = "select id, name from table where id = %(id)s and name = %(name)s"
    curs.execute(q, {'id': 1, 'name': 'somename'})

    # loop over resultset
    for row in curs.fetchall():

        # columns can be asked by index:
        id = row[0]
        name = row[1]

        # and by name:
        id = row['id']
        name = row['name']

    # now commit the transaction
    db.commit()

Deprecated interface:  .dictfetchall/.dictfetchone functions on cursor.
Plain .fetchall() / .fetchone() give exact same result.

"""

__all__ = ['connect_database', 'DBError', 'I_AUTOCOMMIT', 'I_READ_COMMITTED',
           'I_REPEATABLE_READ', 'I_SERIALIZABLE']

import sys
import socket
import psycopg2.extensions
import psycopg2.extras
import skytools

from psycopg2 import Error as DBError
from skytools.sockutil import set_tcp_keepalive


I_AUTOCOMMIT = psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT
I_READ_COMMITTED = psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED
I_REPEATABLE_READ = psycopg2.extensions.ISOLATION_LEVEL_REPEATABLE_READ
I_SERIALIZABLE = psycopg2.extensions.ISOLATION_LEVEL_SERIALIZABLE


class _CompatRow(psycopg2.extras.DictRow):
    """Make DictRow more dict-like."""
    __slots__ = ('_index',)

    def __contains__(self, k):
        """Returns if such row has such column."""
        return k in self._index

    def copy(self):
        """Return regular dict."""
        return skytools.dbdict(self.iteritems())
    
    def iterkeys(self):
        return self._index.iterkeys()

    def itervalues(self):
        return list.__iter__(self)

    # obj.foo access
    def __getattr__(self, k):
        return self[k]

class _CompatCursor(psycopg2.extras.DictCursor):
    """Regular psycopg2 DictCursor with dict* methods."""
    def __init__(self, *args, **kwargs):
        psycopg2.extras.DictCursor.__init__(self, *args, **kwargs)
        self.row_factory = _CompatRow
    dictfetchone = psycopg2.extras.DictCursor.fetchone
    dictfetchall = psycopg2.extras.DictCursor.fetchall
    dictfetchmany = psycopg2.extras.DictCursor.fetchmany

class _CompatConnection(psycopg2.extensions.connection):
    """Connection object that uses _CompatCursor."""
    my_name = '?'
    def cursor(self, name = None):
        if name:
            return psycopg2.extensions.connection.cursor(self,
                    cursor_factory = _CompatCursor,
                    name = name)
        else:
            return psycopg2.extensions.connection.cursor(self,
                    cursor_factory = _CompatCursor)

def connect_database(connstr, keepalive = True,
                     tcp_keepidle = 4 * 60,     # 7200
                     tcp_keepcnt = 4,           # 9
                     tcp_keepintvl = 15):       # 75
    """Create a db connection with connect_timeout and TCP keepalive.
    
    Default connect_timeout is 15, to change put it directly into dsn.

    The extra tcp_* options are Linux-specific, see `man 7 tcp` for details.
    """

    # allow override
    if connstr.find("connect_timeout") < 0:
        connstr += " connect_timeout=15"

    # create connection
    db = _CompatConnection(connstr)
    curs = db.cursor()

    # tune keepalive
    fd = hasattr(db, 'fileno') and db.fileno() or curs.fileno()
    set_tcp_keepalive(fd, keepalive, tcp_keepidle, tcp_keepcnt, tcp_keepintvl)

    # fill .server_version on older psycopg
    if not hasattr(db, 'server_version'):
        iso = db.isolation_level
        db.set_isolation_level(0)
        curs.execute('show server_version_num')
        db.server_version = int(curs.fetchone()[0])
        db.set_isolation_level(iso)

    return db


########NEW FILE########
__FILENAME__ = querybuilder
#! /usr/bin/env python

"""Helper classes for complex query generation.

Main target is code execution under PL/Python.

Query parameters are referenced as C{{key}} or C{{key:type}}.
Type will be given to C{plpy.prepare}.
If C{type} is missing, C{text} is assumed.

See L{plpy_exec} for examples.

"""

import skytools

__all__ = [ 
    'QueryBuilder', 'PLPyQueryBuilder', 'PLPyQuery', 'plpy_exec',
    "run_query", "run_query_row", "run_lookup", "run_exists",
]

# make plpy available
try:
    import plpy
except ImportError:
    pass


PARAM_INLINE = 0 # quote_literal()
PARAM_DBAPI = 1  # %()s
PARAM_PLPY = 2   # $n


class QArgConf:
    """Per-query arg-type config object."""
    param_type = None

class QArg:
    """Place-holder for a query parameter."""
    def __init__(self, name, value, pos, conf):
        self.name = name
        self.value = value
        self.pos = pos
        self.conf = conf
    def __str__(self):
        if self.conf.param_type == PARAM_INLINE:
            return skytools.quote_literal(self.value)
        elif self.conf.param_type == PARAM_DBAPI:
            return "%s"
        elif self.conf.param_type == PARAM_PLPY:
            return "$%d" % self.pos
        else:
            raise Exception("bad QArgConf.param_type")


# need an structure with fast remove-from-middle
# and append operations.
class DList:
    """Simple double-linked list."""
    def __init__(self):
        self.next = self
        self.prev = self

    def append(self, obj):
        obj.next = self
        obj.prev = self.prev
        self.prev.next = obj
        self.prev = obj

    def remove(self, obj):
        obj.next.prev = obj.prev
        obj.prev.next = obj.next
        obj.next = obj.prev = None

    def empty(self):
        return self.next == self

    def pop(self):
        """Remove and return first element."""
        obj = None
        if not self.empty():
            obj = self.next
            self.remove(obj)
        return obj


class CachedPlan:
    """Wrapper around prepared plan."""
    def __init__(self, key, plan):
        self.key = key # (sql, (types))
        self.plan = plan


class PlanCache:
    """Cache for limited amount of plans."""

    def __init__(self, maxplans = 100):
        self.maxplans = maxplans
        self.plan_map = {}
        self.plan_list = DList()

    def get_plan(self, sql, types):
        """Prepare the plan and cache it."""

        t = (sql, tuple(types))
        if t in self.plan_map:
            pc = self.plan_map[t]
            # put to the end
            self.plan_list.remove(pc)
            self.plan_list.append(pc)
            return pc.plan

        # prepare new plan
        plan = plpy.prepare(sql, types)

        # add to cache
        pc = CachedPlan(t, plan)
        self.plan_list.append(pc)
        self.plan_map[t] = pc

        # remove plans if too much
        while len(self.plan_map) > self.maxplans:
            pc = self.plan_list.pop()
            del self.plan_map[pc.key]

        return plan


class QueryBuilder:
    """Helper for query building.

    >>> args = {'success': 't', 'total': 45, 'ccy': 'EEK', 'id': 556}
    >>> q = QueryBuilder("update orders set total = {total} where id = {id}", args)
    >>> q.add(" and optional = {non_exist}")
    >>> q.add(" and final = {success}")
    >>> print q.get_sql(PARAM_INLINE)
    update orders set total = '45' where id = '556' and final = 't'
    >>> print q.get_sql(PARAM_DBAPI)
    update orders set total = %s where id = %s and final = %s
    >>> print q.get_sql(PARAM_PLPY)
    update orders set total = $1 where id = $2 and final = $3
    """

    def __init__(self, sqlexpr, params):
        """Init the object.

        @param sqlexpr:     Partial sql fragment.
        @param params:      Dict of parameter values.
        """
        self._params = params
        self._arg_type_list = []
        self._arg_value_list = []
        self._sql_parts = []
        self._arg_conf = QArgConf()
        self._nargs = 0

        if sqlexpr:
            self.add(sqlexpr, required = True)

    def add(self, expr, type = "text", required = False):
        """Add SQL fragment to query.
        """
        self._add_expr('', expr, self._params, type, required)

    def get_sql(self, param_type = PARAM_INLINE):
        """Return generated SQL (thus far) as string.

        Possible values for param_type:
            - 0: Insert values quoted with quote_literal()
            - 1: Insert %()s in place of parameters.
            - 2: Insert $n in place of parameters.
        """
        self._arg_conf.param_type = param_type
        tmp = map(str, self._sql_parts)
        return "".join(tmp)

    def _add_expr(self, pfx, expr, params, type, required):
        parts = []
        types = []
        values = []
        nargs = self._nargs
        if pfx:
            parts.append(pfx)
        pos = 0
        while 1:
            # find start of next argument
            a1 = expr.find('{', pos)
            if a1 < 0:
                parts.append(expr[pos:])
                break

            # find end end of argument name
            a2 = expr.find('}', a1)
            if a2 < 0:
                raise Exception("missing argument terminator: "+expr)

            # add plain sql
            if a1 > pos:
                parts.append(expr[pos:a1])
            pos = a2 + 1

            # get arg name, check if exists
            k = expr[a1 + 1 : a2]
            # split name from type
            tpos = k.rfind(':')
            if tpos > 0:
                kparam = k[:tpos]
                ktype = k[tpos+1 : ]
            else:
                kparam = k
                ktype = type

            # params==None means params are checked later
            if params is not None and kparam not in params:
                if required:
                    raise Exception("required parameter missing: "+kparam)
                # optional fragment, param missing, skip it
                return

            # got arg
            nargs += 1
            if params is not None:
                val = params[kparam]
            else:
                val = kparam
            values.append(val)
            types.append(ktype)
            arg = QArg(kparam, val, nargs, self._arg_conf)
            parts.append(arg)

        # add interesting parts to the main sql
        self._sql_parts.extend(parts)
        if types:
            self._arg_type_list.extend(types)
        if values:
            self._arg_value_list.extend(values)
        self._nargs = nargs

    def execute(self, curs):
        """Client-side query execution on DB-API 2.0 cursor.

        Calls C{curs.execute()} with proper arguments.

        Returns result of curs.execute(), although that does not
        return anything interesting.  Later curs.fetch* methods
        must be called to get result.
        """
        q = self.get_sql(PARAM_DBAPI)
        args = self._params
        return curs.execute(q, args)

class PLPyQueryBuilder(QueryBuilder):

    def __init__(self, sqlexpr, params, plan_cache = None, sqls = None):
        """Init the object.

        @param sqlexpr:     Partial sql fragment.
        @param params:      Dict of parameter values.
        @param plan_cache:  (PL/Python) A dict object where to store the plan cache, under the key C{"plan_cache"}.
                            If not given, plan will not be cached and values will be inserted directly
                            to query.  Usually either C{GD} or C{SD} should be given here.
        @param sqls:        list object where to append executed sqls (used for debugging)
        """
        QueryBuilder.__init__(self, sqlexpr, params)
        self._sqls = sqls

        if plan_cache is not None:
            if 'plan_cache' not in plan_cache:
                plan_cache['plan_cache'] = PlanCache()
            self._plan_cache = plan_cache['plan_cache']
        else:
            self._plan_cache = None

    def execute(self):
        """Server-side query execution via plpy.

        Query can be run either cached or uncached, depending
        on C{plan_cache} setting given to L{__init__}.

        Returns result of plpy.execute().
        """

        args = self._arg_value_list
        types = self._arg_type_list

        if self._sqls is not None:
            self._sqls.append( { "sql": self.get_sql(PARAM_INLINE) } )

        if self._plan_cache is not None:
            sql = self.get_sql(PARAM_PLPY)
            plan = self._plan_cache.get_plan(sql, types)
            res = plpy.execute(plan, args)
        else:
            sql = self.get_sql(PARAM_INLINE)
            res = plpy.execute(sql)
        if res:
            res = [skytools.dbdict(r) for r in res]
        return res


class PLPyQuery:
    """Static, cached PL/Python query that uses QueryBuilder formatting.
    
    See L{plpy_exec} for simple usage.
    """
    def __init__(self, sql):
        qb = QueryBuilder(sql, None)
        p_sql = qb.get_sql(PARAM_PLPY)
        p_types =  qb._arg_type_list
        self.plan = plpy.prepare(p_sql, p_types)
        self.arg_map = qb._arg_value_list
        self.sql = sql

    def execute(self, arg_dict, all_keys_required = True):
        try:
            if all_keys_required:
                arg_list = [arg_dict[k] for k in self.arg_map]
            else:
                arg_list = [arg_dict.get(k) for k in self.arg_map]
            return plpy.execute(self.plan, arg_list)
        except KeyError:
            need = set(self.arg_map)
            got = set(arg_dict.keys())
            missing = list(need.difference(got))
            plpy.error("Missing arguments: [%s]  QUERY: %s" % (
                ','.join(missing), repr(self.sql)))

    def __repr__(self):
        return 'PLPyQuery<%s>' % self.sql

def plpy_exec(gd, sql, args, all_keys_required = True):
    """Cached plan execution for PL/Python.

    @param gd:  dict to store cached plans under.  If None, caching is disabled.
    @param sql: SQL statement to execute.
    @param args: dict of arguments to query.
    @param all_keys_required: if False, missing key is taken as NULL, instead of throwing error.

    >>> res = plpy_exec(GD, "select {arg1}, {arg2:int4}, {arg1}", {'arg1': '1', 'arg2': '2'})
    DBG: plpy.prepare('select $1, $2, $3', ['text', 'int4', 'text'])
    DBG: plpy.execute(('PLAN', 'select $1, $2, $3', ['text', 'int4', 'text']), ['1', '2', '1'])
    >>> res = plpy_exec(None, "select {arg1}, {arg2:int4}, {arg1}", {'arg1': '1', 'arg2': '2'})
    DBG: plpy.execute("select '1', '2', '1'", [])
    >>> res = plpy_exec(GD, "select {arg1}, {arg2:int4}, {arg1}", {'arg1': '3', 'arg2': '4'})
    DBG: plpy.execute(('PLAN', 'select $1, $2, $3', ['text', 'int4', 'text']), ['3', '4', '3'])
    >>> res = plpy_exec(GD, "select {arg1}, {arg2:int4}, {arg1}", {'arg1': '3'})
    DBG: plpy.error("Missing arguments: [arg2]  QUERY: 'select {arg1}, {arg2:int4}, {arg1}'")
    >>> res = plpy_exec(GD, "select {arg1}, {arg2:int4}, {arg1}", {'arg1': '3'}, False)
    DBG: plpy.execute(('PLAN', 'select $1, $2, $3', ['text', 'int4', 'text']), ['3', None, '3'])
    """

    if gd is None:
        return PLPyQueryBuilder(sql, args).execute()

    try:
        sq = gd['plq_cache'][sql]
    except KeyError:
        if 'plq_cache' not in gd:
            gd['plq_cache'] = {}
        sq = PLPyQuery(sql)
        gd['plq_cache'][sql] = sq
    return sq.execute(args, all_keys_required)

# some helper functions for convenient sql execution

def run_query(cur, sql, params = None, **kwargs):
    """ Helper function if everything you need is just paramertisized execute
        Sets rows_found that is coneninet to use when you don't need result just
        want to know how many rows were affected
    """
    params = params or kwargs
    sql = QueryBuilder(sql, params).get_sql(0)
    cur.execute(sql)
    rows = cur.fetchall()
    # convert result rows to dbdict
    if rows:
        rows = [skytools.dbdict(r) for r in rows]
    return rows

def run_query_row(cur, sql, params = None, **kwargs):
    """ Helper function if everything you need is just paramertisized execute to
        fetch one row only. If not found none is returned
    """
    params = params or kwargs
    rows = run_query(cur, sql, params)
    if len(rows) == 0:
        return None
    return rows[0]

def run_lookup(cur, sql, params = None, **kwargs):
    """ Helper function to fetch one value Takes away all the hassle of preparing statements
        and processing returned result giving out just one value.
    """
    params = params or kwargs
    sql = QueryBuilder(sql, params).get_sql(0)
    cur.execute(sql)
    row = cur.fetchone()
    if row is None:
        return None
    return row[0]

def run_exists(cur, sql, params = None, **kwargs):
    """ Helper function to fetch one value Takes away all the hassle of preparing statements
        and processing returned result giving out just one value.
    """
    params = params or kwargs
    val = run_lookup(cur, sql, params)
    return not (val is None)


# fake plpy for testing
class fake_plpy:
    def prepare(self, sql, types):
        print "DBG: plpy.prepare(%s, %s)" % (repr(sql), repr(types))
        return ('PLAN', sql, types)
    def execute(self, plan, args = []):
        print "DBG: plpy.execute(%s, %s)" % (repr(plan), repr(args))
    def error(self, msg):
        print "DBG: plpy.error(%s)" % repr(msg)

# launch doctest
if __name__ == '__main__':
    import doctest
    plpy = fake_plpy()
    GD = {}
    doctest.testmod()



########NEW FILE########
__FILENAME__ = quoting
# quoting.py

"""Various helpers for string quoting/unquoting."""

import re

__all__ = [
    # _pyqoting / _cquoting
    "quote_literal", "quote_copy", "quote_bytea_raw",
    "db_urlencode", "db_urldecode", "unescape",
    "unquote_literal",
    # local
    "quote_bytea_literal", "quote_bytea_copy", "quote_statement",
    "quote_ident", "quote_fqident", "quote_json", "unescape_copy",
    "unquote_ident", "unquote_fqident",
    "json_encode", "json_decode",
    "make_pgarray",
]

try:
    from skytools._cquoting import *
except ImportError:
    from skytools._pyquoting import *

# 
# SQL quoting
#

def quote_bytea_literal(s):
    """Quote bytea for regular SQL."""

    return quote_literal(quote_bytea_raw(s))

def quote_bytea_copy(s):
    """Quote bytea for COPY."""

    return quote_copy(quote_bytea_raw(s))

def quote_statement(sql, dict_or_list):
    """Quote whole statement.

    Data values are taken from dict or list or tuple.
    """
    if hasattr(dict_or_list, 'items'):
        qdict = {}
        for k, v in dict_or_list.items():
            qdict[k] = quote_literal(v)
        return sql % qdict
    else:
        qvals = [quote_literal(v) for v in dict_or_list]
        return sql % tuple(qvals)

# reserved keywords (RESERVED_KEYWORD + TYPE_FUNC_NAME_KEYWORD)
_ident_kwmap = {
"all":1, "analyse":1, "analyze":1, "and":1, "any":1, "array":1, "as":1,
"asc":1, "asymmetric":1, "authorization":1, "binary":1, "both":1, "case":1,
"cast":1, "check":1, "collate":1, "collation":1, "column":1, "concurrently":1,
"constraint":1, "create":1, "cross":1, "current_catalog":1, "current_date":1,
"current_role":1, "current_schema":1, "current_time":1, "current_timestamp":1,
"current_user":1, "default":1, "deferrable":1, "desc":1, "distinct":1,
"do":1, "else":1, "end":1, "errors":1, "except":1, "false":1, "fetch":1,
"for":1, "foreign":1, "freeze":1, "from":1, "full":1, "grant":1, "group":1,
"having":1, "ilike":1, "in":1, "initially":1, "inner":1, "intersect":1,
"into":1, "is":1, "isnull":1, "join":1, "lateral":1, "leading":1, "left":1,
"like":1, "limit":1, "localtime":1, "localtimestamp":1, "natural":1, "new":1,
"not":1, "notnull":1, "null":1, "off":1, "offset":1, "old":1, "on":1, "only":1,
"or":1, "order":1, "outer":1, "over":1, "overlaps":1, "placing":1, "primary":1,
"references":1, "returning":1, "right":1, "select":1, "session_user":1,
"similar":1, "some":1, "symmetric":1, "table":1, "then":1, "to":1, "trailing":1,
"true":1, "union":1, "unique":1, "user":1, "using":1, "variadic":1, "verbose":1,
"when":1, "where":1, "window":1, "with":1,
}

_ident_bad = re.compile(r"[^a-z0-9_]|^[0-9]")
def quote_ident(s):
    """Quote SQL identifier.

    If is checked against weird symbols and keywords.
    """

    if _ident_bad.search(s) or s in _ident_kwmap:
        s = '"%s"' % s.replace('"', '""')
    elif not s:
        return '""'
    return s

def quote_fqident(s):
    """Quote fully qualified SQL identifier.

    The '.' is taken as namespace separator and
    all parts are quoted separately

    Example:
    >>> quote_fqident('tbl')
    'public.tbl'
    >>> quote_fqident('Baz.Foo.Bar')
    '"Baz"."Foo.Bar"'
    """
    tmp = s.split('.', 1)
    if len(tmp) == 1:
        return 'public.' + quote_ident(s)
    return '.'.join(map(quote_ident, tmp))

#
# quoting for JSON strings
#

_jsre = re.compile(r'[\x00-\x1F\\/"]')
_jsmap = { "\b": "\\b", "\f": "\\f", "\n": "\\n", "\r": "\\r",
    "\t": "\\t", "\\": "\\\\", '"': '\\"',
    "/": "\\/",   # to avoid html attacks
}

def _json_quote_char(m):
    """Quote single char."""
    c = m.group(0)
    try:
        return _jsmap[c]
    except KeyError:
        return r"\u%04x" % ord(c)

def quote_json(s):
    """JSON style quoting."""
    if s is None:
        return "null"
    return '"%s"' % _jsre.sub(_json_quote_char, s)

def unescape_copy(val):
    r"""Removes C-style escapes, also converts "\N" to None.

    Example:
    >>> unescape_copy(r'baz\tfo\'o')
    "baz\tfo'o"
    >>> unescape_copy(r'\N') is None
    True
    """
    if val == r"\N":
        return None
    return unescape(val)

def unquote_ident(val):
    """Unquotes possibly quoted SQL identifier.
    
    >>> unquote_ident('Foo')
    'foo'
    >>> unquote_ident('"Wei "" rd"')
    'Wei " rd'
    """
    if len(val) > 1 and val[0] == '"' and val[-1] == '"':
        return val[1:-1].replace('""', '"')
    if val.find('"') > 0:
        raise Exception('unsupported syntax')
    return val.lower()

def unquote_fqident(val):
    """Unquotes fully-qualified possibly quoted SQL identifier.

    >>> unquote_fqident('foo')
    'foo'
    >>> unquote_fqident('"Foo"."Bar "" z"')
    'Foo.Bar " z'
    """
    tmp = val.split('.', 1)
    return '.'.join([unquote_ident(i) for i in tmp])

# accept simplejson or py2.6+ json module
# search for simplejson first as there exists
# incompat 'json' module
try:
    import simplejson as json
except ImportError:
    try:
        import json
    except:
        pass

def json_encode(val = None, **kwargs):
    """Creates JSON string from Python object.

    >>> json_encode({'a': 1})
    '{"a": 1}'
    >>> json_encode('a')
    '"a"'
    >>> json_encode(['a'])
    '["a"]'
    >>> json_encode(a=1)
    '{"a": 1}'
    """
    return json.dumps(val or kwargs)

def json_decode(s):
    """Parses JSON string into Python object.

    >>> json_decode('[1]')
    [1]
    """
    return json.loads(s)

#
# Create Postgres array
#

# any chars not in "good" set?  main bad ones: [ ,{}\"]
_pgarray_bad_rx = r"[^0-9a-z_.%&=()<>*/+-]"
_pgarray_bad_rc = None

def _quote_pgarray_elem(s):
    if s is None:
        return 'NULL'
    s = str(s)
    if _pgarray_bad_rc.search(s):
        s = s.replace('\\', '\\\\')
        return '"' + s.replace('"', r'\"') + '"'
    elif not s:
        return '""'
    return s

def make_pgarray(lst):
    r"""Formats Python list as Postgres array.
    Reverse of parse_pgarray().

    >>> make_pgarray([])
    '{}'
    >>> make_pgarray(['foo_3',1,'',None])
    '{foo_3,1,"",NULL}'
    >>> make_pgarray([None,',','\\',"'",'"',"{","}",'_'])
    '{NULL,",","\\\\","\'","\\"","{","}",_}'
    """

    global _pgarray_bad_rc
    if _pgarray_bad_rc is None:
        _pgarray_bad_rc = re.compile(_pgarray_bad_rx)

    items = [_quote_pgarray_elem(v) for v in lst]
    return '{' + ','.join(items) + '}'


if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = scripting

"""Useful functions and classes for database scripts.

"""

import errno
import logging
import logging.config
import logging.handlers
import optparse
import os
import select
import signal
import sys
import time

import psycopg2
import skytools
import skytools.skylog

try:
    import skytools.installer_config
    default_skylog = skytools.installer_config.skylog
except ImportError:
    default_skylog = 0

__pychecker__ = 'no-badexcept'

__all__ = ['BaseScript', 'UsageError', 'daemonize', 'DBScript']

class UsageError(Exception):
    """User induced error."""

#
# daemon mode
#

def daemonize():
    """Turn the process into daemon.

    Goes background and disables all i/o.
    """

    # launch new process, kill parent
    pid = os.fork()
    if pid != 0:
        os._exit(0)

    # start new session
    os.setsid()

    # stop i/o
    fd = os.open("/dev/null", os.O_RDWR)
    os.dup2(fd, 0)
    os.dup2(fd, 1)
    os.dup2(fd, 2)
    if fd > 2:
        os.close(fd)

#
# Pidfile locking+cleanup & daemonization combined
#

def run_single_process(runnable, daemon, pidfile):
    """Run runnable class, possibly daemonized, locked on pidfile."""

    # check if another process is running
    if pidfile and os.path.isfile(pidfile):
        if skytools.signal_pidfile(pidfile, 0):
            print("Pidfile exists, another process running?")
            sys.exit(1)
        else:
            print("Ignoring stale pidfile")

    # daemonize if needed
    if daemon:
        daemonize()

    # clean only own pidfile
    own_pidfile = False

    try:
        if pidfile:
            data = str(os.getpid())
            skytools.write_atomic(pidfile, data)
            own_pidfile = True

        runnable.run()
    finally:
        if own_pidfile:
            try:
                os.remove(pidfile)
            except: pass

#
# logging setup
#

_log_config_done = 0
_log_init_done = {}

def _load_log_config(fn, defs):
    """Fixed fileConfig."""

    # Work around fileConfig default behaviour to disable
    # not only old handlers on load (which slightly makes sense)
    # but also old logger objects (which does not make sense).

    if sys.hexversion >= 0x2060000:
        logging.config.fileConfig(fn, defs, False)
    else:
        logging.config.fileConfig(fn, defs)
        root = logging.getLogger()
        for lg in root.manager.loggerDict.values():
            lg.disabled = 0

def _init_log(job_name, service_name, cf, log_level, is_daemon):
    """Logging setup happens here."""
    global _log_init_done, _log_config_done

    got_skylog = 0
    use_skylog = cf.getint("use_skylog", default_skylog)

    # if non-daemon, avoid skylog if script is running on console.
    # set use_skylog=2 to disable.
    if not is_daemon and use_skylog == 1:
        if os.isatty(sys.stdout.fileno()):
            use_skylog = 0

    # load logging config if needed
    if use_skylog and not _log_config_done:
        # python logging.config braindamage:
        # cannot specify external classess without such hack
        logging.skylog = skytools.skylog
        skytools.skylog.set_service_name(service_name, job_name)

        # load general config
        flist = cf.getlist('skylog_locations',
                           ['skylog.ini', '~/.skylog.ini', '/etc/skylog.ini'])
        for fn in flist:
            fn = os.path.expanduser(fn)
            if os.path.isfile(fn):
                defs = {'job_name': job_name, 'service_name': service_name}
                _load_log_config(fn, defs)
                got_skylog = 1
                break
        _log_config_done = 1
        if not got_skylog:
            sys.stderr.write("skylog.ini not found!\n")
            sys.exit(1)

    # avoid duplicate logging init for job_name
    log = logging.getLogger(job_name)
    if job_name in _log_init_done:
        return log
    _log_init_done[job_name] = 1

    # tune level on root logger
    root = logging.getLogger()
    root.setLevel(log_level)

    # compatibility: specify ini file in script config
    def_fmt = '%(asctime)s %(process)s %(levelname)s %(message)s'
    def_datefmt = '' # None
    logfile = cf.getfile("logfile", "")
    if logfile:
        fstr = cf.get('logfmt_file', def_fmt)
        fstr_date = cf.get('logdatefmt_file', def_datefmt)
        if log_level < logging.INFO:
            fstr = cf.get('logfmt_file_verbose', fstr)
            fstr_date = cf.get('logdatefmt_file_verbose', fstr_date)
        fmt = logging.Formatter(fstr, fstr_date)
        size = cf.getint('log_size', 10*1024*1024)
        num = cf.getint('log_count', 3)
        hdlr = logging.handlers.RotatingFileHandler(
                    logfile, 'a', size, num)
        hdlr.setFormatter(fmt)
        root.addHandler(hdlr)

    # if skylog.ini is disabled or not available, log at least to stderr
    if not got_skylog:
        fstr = cf.get('logfmt_console', def_fmt)
        fstr_date = cf.get('logdatefmt_console', def_datefmt)
        if log_level < logging.INFO:
            fstr = cf.get('logfmt_console_verbose', fstr)
            fstr_date = cf.get('logdatefmt_console_verbose', fstr_date)
        hdlr = logging.StreamHandler()
        fmt = logging.Formatter(fstr, fstr_date)
        hdlr.setFormatter(fmt)
        root.addHandler(hdlr)

    return log


class BaseScript(object):
    """Base class for service scripts.

    Handles logging, daemonizing, config, errors.

    Config template::

        ## Parameters for skytools.BaseScript ##

        # how many seconds to sleep between work loops
        # if missing or 0, then instead sleeping, the script will exit
        loop_delay = 1.0

        # where to log
        logfile = ~/log/%(job_name)s.log

        # where to write pidfile
        pidfile = ~/pid/%(job_name)s.pid

        # per-process name to use in logging
        #job_name = %(config_name)s

        # whether centralized logging should be used
        # search-path [ ./skylog.ini, ~/.skylog.ini, /etc/skylog.ini ]
        #   0 - disabled
        #   1 - enabled, unless non-daemon on console (os.isatty())
        #   2 - always enabled
        #use_skylog = 0

        # where to find skylog.ini
        #skylog_locations = skylog.ini, ~/.skylog.ini, /etc/skylog.ini

        # how many seconds to sleep after catching a exception
        #exception_sleep = 20
    """
    service_name = None
    job_name = None
    cf = None
    cf_defaults = {}
    pidfile = None

    # >0 - sleep time if work() requests sleep
    # 0  - exit if work requests sleep
    # <0 - run work() once [same as looping=0]
    loop_delay = 1.0

    # 0 - run work() once
    # 1 - run work() repeatedly
    looping = 1

    # result from last work() call:
    #  1 - there is probably more work, don't sleep
    #  0 - no work, sleep before calling again
    # -1 - exception was thrown
    work_state = 1

    # setup logger here, this allows override by subclass
    log = logging.getLogger('skytools.BaseScript')

    def __init__(self, service_name, args):
        """Script setup.

        User class should override work() and optionally __init__(), startup(),
        reload(), reset(), shutdown() and init_optparse().

        NB: In case of daemon, __init__() and startup()/work()/shutdown() will be
        run in different processes.  So nothing fancy should be done in __init__().

        @param service_name: unique name for script.
            It will be also default job_name, if not specified in config.
        @param args: cmdline args (sys.argv[1:]), but can be overridden
        """
        self.service_name = service_name
        self.go_daemon = 0
        self.need_reload = 0
        self.stat_dict = {}
        self.log_level = logging.INFO

        # parse command line
        parser = self.init_optparse()
        self.options, self.args = parser.parse_args(args)

        # check args
        if self.options.version:
            self.print_version()
            sys.exit(0)
        if self.options.daemon:
            self.go_daemon = 1
        if self.options.quiet:
            self.log_level = logging.WARNING
        if self.options.verbose > 1:
            self.log_level = skytools.skylog.TRACE
        elif self.options.verbose:
            self.log_level = logging.DEBUG

        self.cf_override = {}
        if self.options.set:
            for a in self.options.set:
                k, v = a.split('=', 1)
                self.cf_override[k.strip()] = v.strip()

        if self.options.ini:
            self.print_ini()
            sys.exit(0)

        # read config file
        self.reload()

        # init logging
        _init_log(self.job_name, self.service_name, self.cf, self.log_level, self.go_daemon)

        # send signal, if needed
        if self.options.cmd == "kill":
            self.send_signal(signal.SIGTERM)
        elif self.options.cmd == "stop":
            self.send_signal(signal.SIGINT)
        elif self.options.cmd == "reload":
            self.send_signal(signal.SIGHUP)

    def print_version(self):
        service = self.service_name
        if getattr(self, '__version__', None):
            service += ' version %s' % self.__version__
        print '%s, Skytools version %s' % (service, skytools.__version__)

    def print_ini(self):
        """Prints out ini file from doc string of the script of default for dbscript

        Used by --ini option on command line.
        """

        # current service name
        print("[%s]\n" % self.service_name)

        # walk class hierarchy
        bases = [self.__class__]
        while len(bases) > 0:
            parents = []
            for c in bases:
                for p in c.__bases__:
                    if p not in parents:
                        parents.append(p)
                doc = c.__doc__
                if doc:
                    self._print_ini_frag(doc)
            bases = parents

    def _print_ini_frag(self, doc):
        # use last '::' block as config template
        pos = doc and doc.rfind('::\n') or -1
        if pos < 0:
            return
        doc = doc[pos+2 : ].rstrip()
        doc = skytools.dedent(doc)

        # merge overrided options into output
        for ln in doc.splitlines():
            vals = ln.split('=', 1)
            if len(vals) != 2:
                print(ln)
                continue

            k = vals[0].strip()
            v = vals[1].strip()
            if k and k[0] == '#':
                print(ln)
                k = k[1:]
                if k in self.cf_override:
                    print('%s = %s' % (k, self.cf_override[k]))
            elif k in self.cf_override:
                if v:
                    print('#' + ln)
                print('%s = %s' % (k, self.cf_override[k]))
            else:
                print(ln)

        print('')

    def load_config(self):
        """Loads and returns skytools.Config instance.

        By default it uses first command-line argument as config
        file name.  Can be overridden.
        """

        if len(self.args) < 1:
            print("need config file, use --help for help.")
            sys.exit(1)
        conf_file = self.args[0]
        return skytools.Config(self.service_name, conf_file,
                               user_defs = self.cf_defaults,
                               override = self.cf_override)

    def init_optparse(self, parser = None):
        """Initialize a OptionParser() instance that will be used to
        parse command line arguments.

        Note that it can be overridden both directions - either DBScript
        will initialize an instance and pass it to user code or user can
        initialize and then pass to DBScript.init_optparse().

        @param parser: optional OptionParser() instance,
               where DBScript should attach its own arguments.
        @return: initialized OptionParser() instance.
        """
        if parser:
            p = parser
        else:
            p = optparse.OptionParser()
            p.set_usage("%prog [options] INI")

        # generic options
        p.add_option("-q", "--quiet", action="store_true",
                     help = "log only errors and warnings")
        p.add_option("-v", "--verbose", action="count",
                     help = "log verbosely")
        p.add_option("-d", "--daemon", action="store_true",
                     help = "go background")
        p.add_option("-V", "--version", action="store_true",
                     help = "print version info and exit")
        p.add_option("", "--ini", action="store_true",
                    help = "display sample ini file")
        p.add_option("", "--set", action="append",
                    help = "override config setting (--set 'PARAM=VAL')")

        # control options
        g = optparse.OptionGroup(p, 'control running process')
        g.add_option("-r", "--reload",
                     action="store_const", const="reload", dest="cmd",
                     help = "reload config (send SIGHUP)")
        g.add_option("-s", "--stop",
                     action="store_const", const="stop", dest="cmd",
                     help = "stop program safely (send SIGINT)")
        g.add_option("-k", "--kill",
                     action="store_const", const="kill", dest="cmd",
                     help = "kill program immediately (send SIGTERM)")
        p.add_option_group(g)

        return p

    def send_signal(self, sig):
        if not self.pidfile:
            self.log.warning("No pidfile in config, nothing to do")
        elif os.path.isfile(self.pidfile):
            alive = skytools.signal_pidfile(self.pidfile, sig)
            if not alive:
                self.log.warning("pidfile exists, but process not running")
        else:
            self.log.warning("No pidfile, process not running")
        sys.exit(0)

    def set_single_loop(self, do_single_loop):
        """Changes whether the script will loop or not."""
        if do_single_loop:
            self.looping = 0
        else:
            self.looping = 1

    def _boot_daemon(self):
        run_single_process(self, self.go_daemon, self.pidfile)

    def start(self):
        """This will launch main processing thread."""
        if self.go_daemon:
            if not self.pidfile:
                self.log.error("Daemon needs pidfile")
                sys.exit(1)
        self.run_func_safely(self._boot_daemon)

    def stop(self):
        """Safely stops processing loop."""
        self.looping = 0

    def reload(self):
        "Reload config."
        # avoid double loading on startup
        if not self.cf:
            self.cf = self.load_config()
        else:
            self.cf.reload()
            self.log.info ("Config reloaded")
        self.job_name = self.cf.get("job_name")
        self.pidfile = self.cf.getfile("pidfile", '')
        self.loop_delay = self.cf.getfloat("loop_delay", self.loop_delay)
        self.exception_sleep = self.cf.getfloat("exception_sleep", 20)
        self.exception_quiet = self.cf.getlist("exception_quiet", [])
        self.exception_grace = self.cf.getfloat("exception_grace", 5*60)
        self.exception_reset = self.cf.getfloat("exception_reset", 15*60)

    def hook_sighup(self, sig, frame):
        "Internal SIGHUP handler.  Minimal code here."
        self.need_reload = 1

    last_sigint = 0
    def hook_sigint(self, sig, frame):
        "Internal SIGINT handler.  Minimal code here."
        self.stop()
        t = time.time()
        if t - self.last_sigint < 1:
            self.log.warning("Double ^C, fast exit")
            sys.exit(1)
        self.last_sigint = t

    def stat_get(self, key):
        """Reads a stat value."""
        try:
            value = self.stat_dict[key]
        except KeyError:
            value = None
        return value

    def stat_put(self, key, value):
        """Sets a stat value."""
        self.stat_dict[key] = value

    def stat_increase(self, key, increase = 1):
        """Increases a stat value."""
        try:
            self.stat_dict[key] += increase
        except KeyError:
            self.stat_dict[key] = increase

    def send_stats(self):
        "Send statistics to log."

        res = []
        for k, v in self.stat_dict.items():
            res.append("%s: %s" % (k, v))

        if len(res) == 0:
            return

        logmsg = "{%s}" % ", ".join(res)
        self.log.info(logmsg)
        self.stat_dict = {}

    def reset(self):
        "Something bad happened, reset all state."
        pass

    def run(self):
        "Thread main loop."

        # run startup, safely
        self.run_func_safely(self.startup)

        while 1:
            # reload config, if needed
            if self.need_reload:
                self.reload()
                self.need_reload = 0

            # do some work
            work = self.run_once()

            if not self.looping or self.loop_delay < 0:
                break

            # remember work state
            self.work_state = work
            # should sleep?
            if not work:
                if self.loop_delay > 0:
                    self.sleep(self.loop_delay)
                    if not self.looping:
                        break
                else:
                    break

        # run shutdown, safely?
        self.shutdown()

    def run_once(self):
        state = self.run_func_safely(self.work, True)

        # send stats that was added
        self.send_stats()

        return state

    last_func_fail = None
    def run_func_safely(self, func, prefer_looping = False):
        "Run users work function, safely."
        try:
            r = func()
            if self.last_func_fail and time.time() > self.last_func_fail + self.exception_reset:
                self.last_func_fail = None
            return r
        except UsageError, d:
            self.log.error(str(d))
            sys.exit(1)
        except MemoryError, d:
            try: # complex logging may not succeed
                self.log.exception("Job %s out of memory, exiting" % self.job_name)
            except MemoryError:
                self.log.fatal("Out of memory")
            sys.exit(1)
        except SystemExit, d:
            self.send_stats()
            if prefer_looping and self.looping and self.loop_delay > 0:
                self.log.info("got SystemExit(%s), exiting" % str(d))
            self.reset()
            raise d
        except KeyboardInterrupt, d:
            self.send_stats()
            if prefer_looping and self.looping and self.loop_delay > 0:
                self.log.info("got KeyboardInterrupt, exiting")
            self.reset()
            sys.exit(1)
        except Exception, d:
            try: # this may fail too
                self.send_stats()
            except:
                pass
            if self.last_func_fail is None:
                self.last_func_fail = time.time()
            emsg = str(d).rstrip()
            self.reset()
            self.exception_hook(d, emsg)
        # reset and sleep
        self.reset()
        if prefer_looping and self.looping and self.loop_delay > 0:
            self.sleep(self.exception_sleep)
            return -1
        sys.exit(1)

    def sleep(self, secs):
        """Make script sleep for some amount of time."""
        try:
            time.sleep(secs)
        except IOError, ex:
            if ex.errno != errno.EINTR:
                raise

    def _is_quiet_exception(self, ex):
        return ((self.exception_quiet == ["ALL"] or ex.__class__.__name__ in self.exception_quiet)
                and self.last_func_fail and time.time() < self.last_func_fail + self.exception_grace)

    def exception_hook(self, det, emsg):
        """Called on after exception processing.

        Can do additional logging.

        @param det: exception details
        @param emsg: exception msg
        """
        lm = "Job %s crashed: %s" % (self.job_name, emsg)
        if self._is_quiet_exception(det):
            self.log.warning(lm)
        else:
            self.log.exception(lm)

    def work(self):
        """Here should user's processing happen.

        Return value is taken as boolean - if true, the next loop
        starts immediately.  If false, DBScript sleeps for a loop_delay.
        """
        raise Exception("Nothing implemented?")

    def startup(self):
        """Will be called just before entering main loop.

        In case of daemon, if will be called in same process as work(),
        unlike __init__().
        """
        self.started = time.time()

        # set signals
        if hasattr(signal, 'SIGHUP'):
            signal.signal(signal.SIGHUP, self.hook_sighup)
        if hasattr(signal, 'SIGINT'):
            signal.signal(signal.SIGINT, self.hook_sigint)

    def shutdown(self):
        """Will be called just after exiting main loop.

        In case of daemon, if will be called in same process as work(),
        unlike __init__().
        """
        pass

    # define some aliases (short-cuts / backward compatibility cruft)
    stat_add = stat_put                 # Old, deprecated function.
    stat_inc = stat_increase

##
##  DBScript
##

#: how old connections need to be closed
DEF_CONN_AGE = 20*60  # 20 min

class DBScript(BaseScript):
    """Base class for database scripts.

    Handles database connection state.

    Config template::

        ## Parameters for skytools.DBScript ##

        # default lifetime for database connections (in seconds)
        #connection_lifetime = 1200
    """

    def __init__(self, service_name, args):
        """Script setup.

        User class should override work() and optionally __init__(), startup(),
        reload(), reset() and init_optparse().

        NB: in case of daemon, the __init__() and startup()/work() will be
        run in different processes.  So nothing fancy should be done in __init__().

        @param service_name: unique name for script.
            It will be also default job_name, if not specified in config.
        @param args: cmdline args (sys.argv[1:]), but can be overridden
        """
        self.db_cache = {}
        self._db_defaults = {}
        self._listen_map = {} # dbname: channel_list
        BaseScript.__init__(self, service_name, args)

    def connection_hook(self, dbname, conn):
        pass

    def set_database_defaults(self, dbname, **kwargs):
        self._db_defaults[dbname] = kwargs

    def add_connect_string_profile(self, connstr, profile):
        """Add extra profile info to connect string.
        """
        if profile:
            extra = self.cf.get("%s_extra_connstr" % profile, '')
            if extra:
                connstr += ' ' + extra
        return connstr

    def get_database(self, dbname, autocommit = 0, isolation_level = -1,
                     cache = None, connstr = None, profile = None):
        """Load cached database connection.

        User must not store it permanently somewhere,
        as all connections will be invalidated on reset.
        """

        max_age = self.cf.getint('connection_lifetime', DEF_CONN_AGE)

        if not cache:
            cache = dbname

        params = {}
        defs = self._db_defaults.get(cache, {})
        params.update(defs)
        if isolation_level >= 0:
            params['isolation_level'] = isolation_level
        elif autocommit:
            params['isolation_level'] = 0
        elif params.get('autocommit', 0):
            params['isolation_level'] = 0
        elif not 'isolation_level' in params:
            params['isolation_level'] = skytools.I_READ_COMMITTED

        if not 'max_age' in params:
            params['max_age'] = max_age

        if cache in self.db_cache:
            dbc = self.db_cache[cache]
            if connstr is None:
                connstr = self.cf.get(dbname, '')
            if connstr:
                connstr = self.add_connect_string_profile(connstr, profile)
                dbc.check_connstr(connstr)
        else:
            if not connstr:
                connstr = self.cf.get(dbname)
            connstr = self.add_connect_string_profile(connstr, profile)

            # connstr might contain password, it is not a good idea to log it
            filtered_connstr = connstr
            pos = connstr.lower().find('password')
            if pos >= 0:
                filtered_connstr = connstr[:pos] + ' [...]'

            self.log.debug("Connect '%s' to '%s'" % (cache, filtered_connstr))
            dbc = DBCachedConn(cache, connstr, params['max_age'], setup_func = self.connection_hook)
            self.db_cache[cache] = dbc

        clist = []
        if cache in self._listen_map:
            clist = self._listen_map[cache]

        return dbc.get_connection(params['isolation_level'], clist)

    def close_database(self, dbname):
        """Explicitly close a cached connection.

        Next call to get_database() will reconnect.
        """
        if dbname in self.db_cache:
            dbc = self.db_cache[dbname]
            dbc.reset()
            del self.db_cache[dbname]

    def reset(self):
        "Something bad happened, reset all connections."
        for dbc in self.db_cache.values():
            dbc.reset()
        self.db_cache = {}
        BaseScript.reset(self)

    def run_once(self):
        state = BaseScript.run_once(self)

        # reconnect if needed
        for dbc in self.db_cache.values():
            dbc.refresh()

        return state

    def exception_hook(self, d, emsg):
        """Log database and query details from exception."""
        curs = getattr(d, 'cursor', None)
        conn = getattr(curs, 'connection', None)
        cname = getattr(conn, 'my_name', None)
        if cname:
            # Properly named connection
            cname = d.cursor.connection.my_name
            sql = getattr(curs, 'query', None) or '?'
            if len(sql) > 200: # avoid logging londiste huge batched queries
                sql = sql[:60] + " ..."
            lm = "Job %s got error on connection '%s': %s.   Query: %s" % (
                self.job_name, cname, emsg, sql)
            if self._is_quiet_exception(d):
                self.log.warning(lm)
            else:
                self.log.exception(lm)
        else:
            BaseScript.exception_hook(self, d, emsg)

    def sleep(self, secs):
        """Make script sleep for some amount of time."""
        fdlist = []
        for dbname in self._listen_map.keys():
            if dbname not in self.db_cache:
                continue
            fd = self.db_cache[dbname].fileno()
            if fd is None:
                continue
            fdlist.append(fd)

        if not fdlist:
            return BaseScript.sleep(self, secs)

        try:
            if hasattr(select, 'poll'):
                p = select.poll()
                for fd in fdlist:
                    p.register(fd, select.POLLIN)
                p.poll(int(secs * 1000))
            else:
                select.select(fdlist, [], [], secs)
        except select.error, d:
            self.log.info('wait canceled')

    def _exec_cmd(self, curs, sql, args, quiet = False, prefix = None):
        """Internal tool: Run SQL on cursor."""
        if self.options.verbose:
            self.log.debug("exec_cmd: %s" % skytools.quote_statement(sql, args))

        _pfx = ""
        if prefix:
            _pfx = "[%s] " % prefix
        curs.execute(sql, args)
        ok = True
        rows = curs.fetchall()
        for row in rows:
            try:
                code = row['ret_code']
                msg = row['ret_note']
            except KeyError:
                self.log.error("Query does not conform to exec_cmd API:")
                self.log.error("SQL: %s" % skytools.quote_statement(sql, args))
                self.log.error("Row: %s" % repr(row.copy()))
                sys.exit(1)
            level = code / 100
            if level == 1:
                self.log.debug("%s%d %s" % (_pfx, code, msg))
            elif level == 2:
                if quiet:
                    self.log.debug("%s%d %s" % (_pfx, code, msg))
                else:
                    self.log.info("%s%s" % (_pfx, msg,))
            elif level == 3:
                self.log.warning("%s%s" % (_pfx, msg,))
            else:
                self.log.error("%s%s" % (_pfx, msg,))
                self.log.debug("Query was: %s" % skytools.quote_statement(sql, args))
                ok = False
        return (ok, rows)

    def _exec_cmd_many(self, curs, sql, baseargs, extra_list, quiet = False, prefix=None):
        """Internal tool: Run SQL on cursor multiple times."""
        ok = True
        rows = []
        for a in extra_list:
            (tmp_ok, tmp_rows) = self._exec_cmd(curs, sql, baseargs + [a], quiet, prefix)
            if not tmp_ok:
                ok = False
            rows += tmp_rows
        return (ok, rows)

    def exec_cmd(self, db_or_curs, q, args, commit = True, quiet = False, prefix = None):
        """Run SQL on db with code/value error handling."""
        if hasattr(db_or_curs, 'cursor'):
            db = db_or_curs
            curs = db.cursor()
        else:
            db = None
            curs = db_or_curs
        (ok, rows) = self._exec_cmd(curs, q, args, quiet, prefix)
        if ok:
            if commit and db:
                db.commit()
            return rows
        else:
            if db:
                db.rollback()
            if self.options.verbose:
                raise Exception("db error")
            # error is already logged
            sys.exit(1)

    def exec_cmd_many(self, db_or_curs, sql, baseargs, extra_list,
                      commit = True, quiet = False, prefix = None):
        """Run SQL on db multiple times."""
        if hasattr(db_or_curs, 'cursor'):
            db = db_or_curs
            curs = db.cursor()
        else:
            db = None
            curs = db_or_curs
        (ok, rows) = self._exec_cmd_many(curs, sql, baseargs, extra_list, quiet, prefix)
        if ok:
            if commit and db:
                db.commit()
            return rows
        else:
            if db:
                db.rollback()
            if self.options.verbose:
                raise Exception("db error")
            # error is already logged
            sys.exit(1)

    def execute_with_retry (self, dbname, stmt, args, exceptions = None):
        """ Execute SQL and retry if it fails.
        Return number of retries and current valid cursor, or raise an exception.
        """
        sql_retry = self.cf.getbool("sql_retry", False)
        sql_retry_max_count = self.cf.getint("sql_retry_max_count", 10)
        sql_retry_max_time = self.cf.getint("sql_retry_max_time", 300)
        sql_retry_formula_a = self.cf.getint("sql_retry_formula_a", 1)
        sql_retry_formula_b = self.cf.getint("sql_retry_formula_b", 5)
        sql_retry_formula_cap = self.cf.getint("sql_retry_formula_cap", 60)
        elist = exceptions or (psycopg2.OperationalError,)
        stime = time.time()
        tried = 0
        dbc = None
        while True:
            try:
                if dbc is None:
                    if dbname not in self.db_cache:
                        self.get_database(dbname, autocommit=1)
                    dbc = self.db_cache[dbname]
                    if dbc.isolation_level != skytools.I_AUTOCOMMIT:
                        raise skytools.UsageError ("execute_with_retry: autocommit required")
                else:
                    dbc.reset()
                curs = dbc.get_connection(dbc.isolation_level).cursor()
                curs.execute (stmt, args)
                break
            except elist, e:
                if not sql_retry or tried >= sql_retry_max_count or time.time() - stime >= sql_retry_max_time:
                    raise
                self.log.info("Job %s got error on connection %s: %s" % (self.job_name, dbname, e))
            except:
                raise
            # y = a + bx , apply cap
            y = sql_retry_formula_a + sql_retry_formula_b * tried
            if sql_retry_formula_cap is not None and y > sql_retry_formula_cap:
                y = sql_retry_formula_cap
            tried += 1
            self.log.info("Retry #%i in %i seconds ...", tried, y)
            self.sleep(y)
        return tried, curs

    def listen(self, dbname, channel):
        """Make connection listen for specific event channel.

        Listening will be activated on next .get_database() call.

        Basically this means that DBScript.sleep() will poll for events
        on that db connection, so when event appears, script will be
        woken up.
        """
        if dbname not in self._listen_map:
            self._listen_map[dbname] = []
        clist = self._listen_map[dbname]
        if channel not in clist:
            clist.append(channel)

    def unlisten(self, dbname, channel='*'):
        """Stop connection for listening on specific event channel.

        Listening will stop on next .get_database() call.
        """
        if dbname not in self._listen_map:
            return
        if channel == '*':
            del self._listen_map[dbname]
            return
        clist = self._listen_map[dbname]
        try:
            clist.remove(channel)
        except ValueError:
            pass

class DBCachedConn(object):
    """Cache a db connection."""
    def __init__(self, name, loc, max_age = DEF_CONN_AGE, verbose = False, setup_func=None, channels=[]):
        self.name = name
        self.loc = loc
        self.conn = None
        self.conn_time = 0
        self.max_age = max_age
        self.isolation_level = -1
        self.verbose = verbose
        self.setup_func = setup_func
        self.listen_channel_list = []

    def fileno(self):
        if not self.conn:
            return None
        return self.conn.cursor().fileno()

    def get_connection(self, isolation_level = -1, listen_channel_list = []):

        # default isolation_level is READ COMMITTED
        if isolation_level < 0:
            isolation_level = skytools.I_READ_COMMITTED

        # new conn?
        if not self.conn:
            self.isolation_level = isolation_level
            self.conn = skytools.connect_database(self.loc)
            self.conn.my_name = self.name

            self.conn.set_isolation_level(isolation_level)
            self.conn_time = time.time()
            if self.setup_func:
                self.setup_func(self.name, self.conn)
        else:
            if self.isolation_level != isolation_level:
                raise Exception("Conflict in isolation_level")

        self._sync_listen(listen_channel_list)

        # done
        return self.conn

    def _sync_listen(self, new_clist):
        if not new_clist and not self.listen_channel_list:
            return
        curs = self.conn.cursor()
        for ch in self.listen_channel_list:
            if ch not in new_clist:
                curs.execute("UNLISTEN %s" % skytools.quote_ident(ch))
        for ch in new_clist:
            if ch not in self.listen_channel_list:
                curs.execute("LISTEN %s" % skytools.quote_ident(ch))
        if self.isolation_level != skytools.I_AUTOCOMMIT:
            self.conn.commit()
        self.listen_channel_list = new_clist[:]

    def refresh(self):
        if not self.conn:
            return
        #for row in self.conn.notifies():
        #    if row[0].lower() == "reload":
        #        self.reset()
        #        return
        if not self.max_age:
            return
        if time.time() - self.conn_time >= self.max_age:
            self.reset()

    def reset(self):
        if not self.conn:
            return

        # drop reference
        conn = self.conn
        self.conn = None
        self.listen_channel_list = []

        # close
        try:
            conn.close()
        except: pass

    def check_connstr(self, connstr):
        """Drop connection if connect string has changed.
        """
        if self.loc != connstr:
            self.reset()

########NEW FILE########
__FILENAME__ = skylog
"""Our log handlers for Python's logging package.
"""

import logging
import logging.handlers
import os
import socket
import time

import skytools

# use fast implementation if available, otherwise fall back to reference one
try:
    import tnetstring as tnetstrings
    tnetstrings.parse = tnetstrings.pop
except ImportError:
    import skytools.tnetstrings as tnetstrings
    tnetstrings.dumps = tnetstrings.dump

__all__ = ['getLogger']

# add TRACE level
TRACE = 5
logging.TRACE = TRACE
logging.addLevelName(TRACE, 'TRACE')

# extra info to be added to each log record
_service_name = 'unknown_svc'
_job_name = 'unknown_job'
_hostname = socket.gethostname()
try:
    _hostaddr = socket.gethostbyname(_hostname)
except:
    _hostaddr = "0.0.0.0"
_log_extra = {
    'job_name': _job_name,
    'service_name': _service_name,
    'hostname': _hostname,
    'hostaddr': _hostaddr,
}
def set_service_name(service_name, job_name):
    """Set info about current script."""
    global _service_name, _job_name

    _service_name = service_name
    _job_name = job_name

    _log_extra['job_name'] = _job_name
    _log_extra['service_name'] = _service_name

#
# How to make extra fields available to all log records:
# 1. Use own getLogger()
#    - messages logged otherwise (eg. from some libs)
#      will crash the logging.
# 2. Fix record in own handlers
#    - works only with custom handlers, standard handlers will
#      crash is used with custom fmt string.
# 3. Change root logger
#    - can't do it after non-root loggers are initialized,
#      doing it before will depend on import order.
# 4. Update LogRecord.__dict__
#    - fails, as formatter uses obj.__dict__ directly.
# 5. Change LogRecord class
#    - ugly but seems to work.
#
_OldLogRecord = logging.LogRecord
class _NewLogRecord(_OldLogRecord):
    def __init__(self, *args):
        _OldLogRecord.__init__(self, *args)
        self.__dict__.update(_log_extra)
logging.LogRecord = _NewLogRecord


# configurable file logger
class EasyRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """Easier setup for RotatingFileHandler."""
    def __init__(self, filename, maxBytes = 10*1024*1024, backupCount = 3):
        """Args same as for RotatingFileHandler, but in filename '~' is expanded."""
        fn = os.path.expanduser(filename)
        logging.handlers.RotatingFileHandler.__init__(self, fn, maxBytes=maxBytes, backupCount=backupCount)


# send JSON message over UDP
class UdpLogServerHandler(logging.handlers.DatagramHandler):
    """Sends log records over UDP to logserver in JSON format."""

    # map logging levels to logserver levels
    _level_map = {
        logging.DEBUG   : 'DEBUG',
        logging.INFO    : 'INFO',
        logging.WARNING : 'WARN',
        logging.ERROR   : 'ERROR',
        logging.CRITICAL: 'FATAL',
    }

    # JSON message template
    _log_template = '{\n\t'\
        '"logger": "skytools.UdpLogServer",\n\t'\
        '"timestamp": %.0f,\n\t'\
        '"level": "%s",\n\t'\
        '"thread": null,\n\t'\
        '"message": %s,\n\t'\
        '"properties": {"application":"%s", "apptype": "%s", "type": "sys", "hostname":"%s", "hostaddr": "%s"}\n'\
        '}\n'

    # cut longer msgs
    MAXMSG = 1024

    def makePickle(self, record):
        """Create message in JSON format."""
        # get & cut msg
        msg = self.format(record)
        if len(msg) > self.MAXMSG:
            msg = msg[:self.MAXMSG]
        txt_level = self._level_map.get(record.levelno, "ERROR")
        hostname = _hostname
        hostaddr = _hostaddr
        jobname = _job_name
        svcname = _service_name
        pkt = self._log_template % (time.time()*1000, txt_level, skytools.quote_json(msg),
                jobname, svcname, hostname, hostaddr)
        return pkt

    def send(self, s):
        """Disable socket caching."""
        sock = self.makeSocket()
        sock.sendto(s, (self.host, self.port))
        sock.close()


# send TNetStrings message over UDP
class UdpTNetStringsHandler(logging.handlers.DatagramHandler):
    """ Sends log records in TNetStrings format over UDP. """

    # LogRecord fields to send
    send_fields = [
        'created', 'exc_text', 'levelname', 'levelno', 'message', 'msecs', 'name',
        'hostaddr', 'hostname', 'job_name', 'service_name']

    _udp_reset = 0

    def makePickle(self, record):
        """ Create message in TNetStrings format.
        """
        msg = {}
        self.format(record) # render 'message' attribute and others
        for k in self.send_fields:
            msg[k] = record.__dict__[k]
        tnetstr = tnetstrings.dumps(msg)
        return tnetstr

    def send(self, s):
        """ Cache socket for a moment, then recreate it.
        """
        now = time.time()
        if now - 1 > self._udp_reset:
            if self.sock:
                self.sock.close()
            self.sock = self.makeSocket()
            self._udp_reset = now
        self.sock.sendto(s, (self.host, self.port))


class LogDBHandler(logging.handlers.SocketHandler):
    """Sends log records into PostgreSQL server.

    Additionally, does some statistics aggregating,
    to avoid overloading log server.

    It subclasses SocketHandler to get throtthling for
    failed connections.
    """

    # map codes to string
    _level_map = {
        logging.DEBUG   : 'DEBUG',
        logging.INFO    : 'INFO',
        logging.WARNING : 'WARNING',
        logging.ERROR   : 'ERROR',
        logging.CRITICAL: 'FATAL',
    }

    def __init__(self, connect_string):
        """
        Initializes the handler with a specific connection string.
        """

        logging.handlers.SocketHandler.__init__(self, None, None)
        self.closeOnError = 1

        self.connect_string = connect_string

        self.stat_cache = {}
        self.stat_flush_period = 60
        # send first stat line immidiately
        self.last_stat_flush = 0

    def createSocket(self):
        try:
            logging.handlers.SocketHandler.createSocket(self)
        except:
            self.sock = self.makeSocket()

    def makeSocket(self):
        """Create server connection.
        In this case its not socket but database connection."""

        db = skytools.connect_database(self.connect_string)
        db.set_isolation_level(0) # autocommit
        return db

    def emit(self, record):
        """Process log record."""

        # we do not want log debug messages
        if record.levelno < logging.INFO:
            return

        try:
            self.process_rec(record)
        except (SystemExit, KeyboardInterrupt):
            raise
        except:
            self.handleError(record)

    def process_rec(self, record):
        """Aggregate stats if needed, and send to logdb."""
        # render msg
        msg = self.format(record)

        # dont want to send stats too ofter
        if record.levelno == logging.INFO and msg and msg[0] == "{":
            self.aggregate_stats(msg)
            if time.time() - self.last_stat_flush >= self.stat_flush_period:
                self.flush_stats(_job_name)
            return

        if record.levelno < logging.INFO:
            self.flush_stats(_job_name)

        # dont send more than one line
        ln = msg.find('\n')
        if ln > 0:
            msg = msg[:ln]

        txt_level = self._level_map.get(record.levelno, "ERROR")
        self.send_to_logdb(_job_name, txt_level, msg)

    def aggregate_stats(self, msg):
        """Sum stats together, to lessen load on logdb."""

        msg = msg[1:-1]
        for rec in msg.split(", "):
            k, v = rec.split(": ")
            agg = self.stat_cache.get(k, 0)
            if v.find('.') >= 0:
                agg += float(v)
            else:
                agg += int(v)
            self.stat_cache[k] = agg

    def flush_stats(self, service):
        """Send acquired stats to logdb."""
        res = []
        for k, v in self.stat_cache.items():
            res.append("%s: %s" % (k, str(v)))
        if len(res) > 0:
            logmsg = "{%s}" % ", ".join(res)
            self.send_to_logdb(service, "INFO", logmsg)
        self.stat_cache = {}
        self.last_stat_flush = time.time()

    def send_to_logdb(self, service, type, msg):
        """Actual sending is done here."""

        if self.sock is None:
            self.createSocket()

        if self.sock:
            logcur = self.sock.cursor()
            query = "select * from log.add(%s, %s, %s)"
            logcur.execute(query, [type, service, msg])


# fix unicode bug in SysLogHandler
class SysLogHandler(logging.handlers.SysLogHandler):
    """Fixes unicode bug in logging.handlers.SysLogHandler."""

    # be compatible with both 2.6 and 2.7
    socktype = socket.SOCK_DGRAM

    _udp_reset = 0

    def _custom_format(self, record):
        msg = self.format(record) + '\000'
        """
        We need to convert record level to lowercase, maybe this will
        change in the future.
        """
        prio = '<%d>' % self.encodePriority(self.facility,
                                            self.mapPriority(record.levelname))
        msg = prio + msg
        return msg

    def emit(self, record):
        """
        Emit a record.

        The record is formatted, and then sent to the syslog server. If
        exception information is present, it is NOT sent to the server.
        """
        msg = self._custom_format(record)
        # Message is a string. Convert to bytes as required by RFC 5424
        if type(msg) is unicode:
            msg = msg.encode('utf-8')
            ## this puts BOM in wrong place
            #if codecs:
            #    msg = codecs.BOM_UTF8 + msg
        try:
            if self.unixsocket:
                try:
                    self.socket.send(msg)
                except socket.error:
                    self._connect_unixsocket(self.address)
                    self.socket.send(msg)
            elif self.socktype == socket.SOCK_DGRAM:
                now = time.time()
                if now - 1 > self._udp_reset:
                    self.socket.close()
                    self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    self._udp_reset = now
                self.socket.sendto(msg, self.address)
            else:
                self.socket.sendall(msg)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)

class SysLogHostnameHandler(SysLogHandler):
    """Slightly modified standard SysLogHandler - sends also hostname and service type"""

    def _custom_format(self, record):
        msg = self.format(record)
        format_string = '<%d> %s %s %s\000'
        msg = format_string % (self.encodePriority(self.facility,self.mapPriority(record.levelname)),
                               _hostname,
                               _service_name,
                               msg)
        return msg


try:
    from logging import LoggerAdapter
except ImportError:
    # LoggerAdapter is missing from python 2.5
    class LoggerAdapter(object):
        def __init__(self, logger, extra):
            self.logger = logger
            self.extra = extra
        def process(self, msg, kwargs):
            kwargs["extra"] = self.extra
            return msg, kwargs
        def debug(self, msg, *args, **kwargs):
            msg, kwargs = self.process(msg, kwargs)
            self.logger.debug(msg, *args, **kwargs)
        def info(self, msg, *args, **kwargs):
            msg, kwargs = self.process(msg, kwargs)
            self.logger.info(msg, *args, **kwargs)
        def warning(self, msg, *args, **kwargs):
            msg, kwargs = self.process(msg, kwargs)
            self.logger.warning(msg, *args, **kwargs)
        def error(self, msg, *args, **kwargs):
            msg, kwargs = self.process(msg, kwargs)
            self.logger.error(msg, *args, **kwargs)
        def exception(self, msg, *args, **kwargs):
            msg, kwargs = self.process(msg, kwargs)
            kwargs["exc_info"] = 1
            self.logger.error(msg, *args, **kwargs)
        def critical(self, msg, *args, **kwargs):
            msg, kwargs = self.process(msg, kwargs)
            self.logger.critical(msg, *args, **kwargs)
        def log(self, level, msg, *args, **kwargs):
            msg, kwargs = self.process(msg, kwargs)
            self.logger.log(level, msg, *args, **kwargs)

# add missing aliases (that are in Logger class)
LoggerAdapter.fatal = LoggerAdapter.critical
LoggerAdapter.warn = LoggerAdapter.warning

class SkyLogger(LoggerAdapter):
    def __init__(self, logger, extra):
        LoggerAdapter.__init__(self, logger, extra)
        self.name = logger.name
    def trace(self, msg, *args, **kwargs):
        """Log 'msg % args' with severity 'TRACE'."""
        self.log(TRACE, msg, *args, **kwargs)
    def addHandler(self, hdlr):
        """Add the specified handler to this logger."""
        self.logger.addHandler(hdlr)
    def isEnabledFor(self, level):
        """See if the underlying logger is enabled for the specified level."""
        return self.logger.isEnabledFor(level)

def getLogger(name=None, **kwargs_extra):
    """Get logger with extra functionality.

    Adds additional log levels, and extra fields to log record.

    name - name for logging.getLogger()
    kwargs_extra - extra fields to add to log record
    """
    log = logging.getLogger(name)
    return SkyLogger(log, kwargs_extra)

########NEW FILE########
__FILENAME__ = sockutil
"""Various low-level utility functions for sockets."""

__all__ = ['set_tcp_keepalive', 'set_nonblocking', 'set_cloexec']

import sys
import os
import socket

try:
    import fcntl
except ImportError:
    pass

__all__ = ['set_tcp_keepalive', 'set_nonblocking', 'set_cloexec']

def set_tcp_keepalive(fd, keepalive = True,
                     tcp_keepidle = 4 * 60,
                     tcp_keepcnt = 4,
                     tcp_keepintvl = 15):
    """Turn on TCP keepalive.  The fd can be either numeric or socket
    object with 'fileno' method.

    OS defaults for SO_KEEPALIVE=1:
     - Linux: (7200, 9, 75) - can configure all.
     - MacOS: (7200, 8, 75) - can configure only tcp_keepidle.
     - Win32: (7200, 5|10, 1) - can configure tcp_keepidle and tcp_keepintvl.

    Our defaults: (240, 4, 15).

    >>> import socket
    >>> s = socket.socket()
    >>> set_tcp_keepalive(s)
    """

    # usable on this OS?
    if not hasattr(socket, 'SO_KEEPALIVE') or not hasattr(socket, 'fromfd'):
        return

    # need socket object
    if isinstance(fd, socket.SocketType):
        s = fd
    else:
        if hasattr(fd, 'fileno'):
            fd = fd.fileno()
        s = socket.fromfd(fd, socket.AF_INET, socket.SOCK_STREAM)

    # skip if unix socket
    if type(s.getsockname()) != type(()):
        return

    # no keepalive?
    if not keepalive:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 0)
        return

    # basic keepalive
    s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

    # detect available options
    TCP_KEEPCNT = getattr(socket, 'TCP_KEEPCNT', None)
    TCP_KEEPINTVL = getattr(socket, 'TCP_KEEPINTVL', None)
    TCP_KEEPIDLE = getattr(socket, 'TCP_KEEPIDLE', None)
    TCP_KEEPALIVE = getattr(socket, 'TCP_KEEPALIVE', None)
    SIO_KEEPALIVE_VALS = getattr(socket, 'SIO_KEEPALIVE_VALS', None)
    if TCP_KEEPIDLE is None and TCP_KEEPALIVE is None and sys.platform == 'darwin':
        TCP_KEEPALIVE = 0x10

    # configure
    if TCP_KEEPCNT is not None:
        s.setsockopt(socket.IPPROTO_TCP, TCP_KEEPCNT, tcp_keepcnt)
    if TCP_KEEPINTVL is not None:
        s.setsockopt(socket.IPPROTO_TCP, TCP_KEEPINTVL, tcp_keepintvl)
    if TCP_KEEPIDLE is not None:
        s.setsockopt(socket.IPPROTO_TCP, TCP_KEEPIDLE, tcp_keepidle)
    elif TCP_KEEPALIVE is not None:
        s.setsockopt(socket.IPPROTO_TCP, TCP_KEEPALIVE, tcp_keepidle)
    elif SIO_KEEPALIVE_VALS is not None:
        s.ioctl(SIO_KEEPALIVE_VALS, (1, tcp_keepidle*1000, tcp_keepintvl*1000))


def set_nonblocking(fd, onoff=True):
    """Toggle the O_NONBLOCK flag.

    If onoff==None then return current setting.

    Actual sockets from 'socket' module should use .setblocking() method,
    this is for situations where it is not available.  Eg. pipes
    from 'subprocess' module.

    >>> import socket
    >>> s = socket.socket()
    >>> set_nonblocking(s, None)
    False
    >>> set_nonblocking(s, 1)
    >>> set_nonblocking(s, None)
    True
    """

    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    if onoff is None:
        return (flags & os.O_NONBLOCK) > 0
    if onoff:
        flags |= os.O_NONBLOCK
    else:
        flags &= ~os.O_NONBLOCK
    fcntl.fcntl(fd, fcntl.F_SETFL, flags)

def set_cloexec(fd, onoff=True):
    """Toggle the FD_CLOEXEC flag.

    If onoff==None then return current setting.

    Some libraries do it automatically (eg. libpq).
    Others do not (Python stdlib).

    >>> import os
    >>> f = open(os.devnull, 'rb')
    >>> set_cloexec(f, None)
    False
    >>> set_cloexec(f, True)
    >>> set_cloexec(f, None)
    True
    >>> import socket
    >>> s = socket.socket()
    >>> set_cloexec(s, None)
    False
    >>> set_cloexec(s)
    >>> set_cloexec(s, None)
    True
    """

    flags = fcntl.fcntl(fd, fcntl.F_GETFD)
    if onoff is None:
        return (flags & fcntl.FD_CLOEXEC) > 0
    if onoff:
        flags |= fcntl.FD_CLOEXEC
    else:
        flags &= ~fcntl.FD_CLOEXEC
    fcntl.fcntl(fd, fcntl.F_SETFD, flags)

if __name__ == '__main__':
    import doctest
    doctest.testmod()


########NEW FILE########
__FILENAME__ = sqltools

"""Database tools."""

import os
from cStringIO import StringIO
import skytools

try:
    import plpy
except ImportError:
    pass

__all__ = [
    "fq_name_parts", "fq_name", "get_table_oid", "get_table_pkeys",
    "get_table_columns", "exists_schema", "exists_table", "exists_type",
    "exists_sequence", "exists_temp_table", "exists_view",
    "exists_function", "exists_language", "Snapshot", "magic_insert",
    "CopyPipe", "full_copy", "DBObject", "DBSchema", "DBTable", "DBFunction",
    "DBLanguage", "db_install", "installer_find_file", "installer_apply_file",
    "dbdict", "mk_insert_sql", "mk_update_sql", "mk_delete_sql",
]

class dbdict(dict):
    """Wrapper on actual dict that allows accessing dict keys as attributes."""
    # obj.foo access
    def __getattr__(self, k):
        "Return attribute."
        try:
            return self[k]
        except KeyError:
            raise AttributeError(k)
    def __setattr__(self, k, v):
        "Set attribute."
        self[k] = v
    def __delattr__(self, k):
        "Remove attribute."
        del self[k]
    def merge(self, other):
        for key in other:
            if key not in self:
                self[key] = other[key]

#
# Fully qualified table name
#

def fq_name_parts(tbl):
    """Return fully qualified name parts.

    >>> fq_name_parts('tbl')
    ['public', 'tbl']
    >>> fq_name_parts('foo.tbl')
    ['foo', 'tbl']
    >>> fq_name_parts('foo.tbl.baz')
    ['foo', 'tbl.baz']
    """

    tmp = tbl.split('.', 1)
    if len(tmp) == 1:
        return ['public', tbl]
    elif len(tmp) == 2:
        return tmp
    else:
        raise Exception('Syntax error in table name:'+tbl)

def fq_name(tbl):
    """Return fully qualified name.

    >>> fq_name('tbl')
    'public.tbl'
    >>> fq_name('foo.tbl')
    'foo.tbl'
    >>> fq_name('foo.tbl.baz')
    'foo.tbl.baz'
    """
    return '.'.join(fq_name_parts(tbl))

#
# info about table
#
def get_table_oid(curs, table_name):
    """Find Postgres OID for table."""
    schema, name = fq_name_parts(table_name)
    q = """select c.oid from pg_namespace n, pg_class c
           where c.relnamespace = n.oid
             and n.nspname = %s and c.relname = %s"""
    curs.execute(q, [schema, name])
    res = curs.fetchall()
    if len(res) == 0:
        raise Exception('Table not found: '+table_name)
    return res[0][0]

def get_table_pkeys(curs, tbl):
    """Return list of pkey column names."""
    oid = get_table_oid(curs, tbl)
    q = "SELECT k.attname FROM pg_index i, pg_attribute k"\
        " WHERE i.indrelid = %s AND k.attrelid = i.indexrelid"\
        "   AND i.indisprimary AND k.attnum > 0 AND NOT k.attisdropped"\
        " ORDER BY k.attnum"
    curs.execute(q, [oid])
    return map(lambda x: x[0], curs.fetchall())

def get_table_columns(curs, tbl):
    """Return list of column names for table."""
    oid = get_table_oid(curs, tbl)
    q = "SELECT k.attname FROM pg_attribute k"\
        " WHERE k.attrelid = %s"\
        "   AND k.attnum > 0 AND NOT k.attisdropped"\
        " ORDER BY k.attnum"
    curs.execute(q, [oid])
    return map(lambda x: x[0], curs.fetchall())

#
# exist checks
#
def exists_schema(curs, schema):
    """Does schema exists?"""
    q = "select count(1) from pg_namespace where nspname = %s"
    curs.execute(q, [schema])
    res = curs.fetchone()
    return res[0]

def exists_table(curs, table_name):
    """Does table exists?"""
    schema, name = fq_name_parts(table_name)
    q = """select count(1) from pg_namespace n, pg_class c
           where c.relnamespace = n.oid and c.relkind = 'r'
             and n.nspname = %s and c.relname = %s"""
    curs.execute(q, [schema, name])
    res = curs.fetchone()
    return res[0]

def exists_sequence(curs, seq_name):
    """Does sequence exists?"""
    schema, name = fq_name_parts(seq_name)
    q = """select count(1) from pg_namespace n, pg_class c
           where c.relnamespace = n.oid and c.relkind = 'S'
             and n.nspname = %s and c.relname = %s"""
    curs.execute(q, [schema, name])
    res = curs.fetchone()
    return res[0]

def exists_view(curs, view_name):
    """Does view exists?"""
    schema, name = fq_name_parts(view_name)
    q = """select count(1) from pg_namespace n, pg_class c
           where c.relnamespace = n.oid and c.relkind = 'v'
             and n.nspname = %s and c.relname = %s"""
    curs.execute(q, [schema, name])
    res = curs.fetchone()
    return res[0]

def exists_type(curs, type_name):
    """Does type exists?"""
    schema, name = fq_name_parts(type_name)
    q = """select count(1) from pg_namespace n, pg_type t
           where t.typnamespace = n.oid
             and n.nspname = %s and t.typname = %s"""
    curs.execute(q, [schema, name])
    res = curs.fetchone()
    return res[0]

def exists_function(curs, function_name, nargs):
    """Does function exists?"""
    # this does not check arg types, so may match several functions
    schema, name = fq_name_parts(function_name)
    q = """select count(1) from pg_namespace n, pg_proc p
           where p.pronamespace = n.oid and p.pronargs = %s
             and n.nspname = %s and p.proname = %s"""
    curs.execute(q, [nargs, schema, name])
    res = curs.fetchone()

    # if unqualified function, check builtin functions too
    if not res[0] and function_name.find('.') < 0:
        name = "pg_catalog." + function_name
        return exists_function(curs, name, nargs)

    return res[0]

def exists_language(curs, lang_name):
    """Does PL exists?"""
    q = """select count(1) from pg_language
           where lanname = %s"""
    curs.execute(q, [lang_name])
    res = curs.fetchone()
    return res[0]

def exists_temp_table(curs, tbl):
    """Does temp table exists?"""
    # correct way, works only on 8.2
    q = "select 1 from pg_class where relname = %s and relnamespace = pg_my_temp_schema()"
    curs.execute(q, [tbl])
    tmp = curs.fetchall()
    return len(tmp) > 0

#
# Support for PostgreSQL snapshot
#

class Snapshot(object):
    """Represents a PostgreSQL snapshot.

    Example:
    >>> sn = Snapshot('11:20:11,12,15')
    >>> sn.contains(9)
    True
    >>> sn.contains(11)
    False
    >>> sn.contains(17)
    True
    >>> sn.contains(20)
    False
    """

    def __init__(self, str):
        "Create snapshot from string."

        self.sn_str = str
        tmp = str.split(':')
        if len(tmp) != 3:
            raise Exception('Unknown format for snapshot')
        self.xmin = int(tmp[0])
        self.xmax = int(tmp[1])
        self.txid_list = []
        if tmp[2] != "":
            for s in tmp[2].split(','):
                self.txid_list.append(int(s))

    def contains(self, txid):
        "Is txid visible in snapshot."

        txid = int(txid)

        if txid < self.xmin:
            return True
        if txid >= self.xmax:
            return False
        if txid in self.txid_list:
            return False
        return True

#
# Copy helpers
#

def _gen_dict_copy(tbl, row, fields, qfields):
    tmp = []
    for f in fields:
        v = row.get(f)
        tmp.append(skytools.quote_copy(v))
    return "\t".join(tmp)

def _gen_dict_insert(tbl, row, fields, qfields):
    tmp = []
    for f in fields:
        v = row.get(f)
        tmp.append(skytools.quote_literal(v))
    fmt = "insert into %s (%s) values (%s);"
    return fmt % (tbl, ",".join(qfields), ",".join(tmp))

def _gen_list_copy(tbl, row, fields, qfields):
    tmp = []
    for i in range(len(fields)):
        try:
            v = row[i]
        except IndexError:
            v = None
        tmp.append(skytools.quote_copy(v))
    return "\t".join(tmp)

def _gen_list_insert(tbl, row, fields, qfields):
    tmp = []
    for i in range(len(fields)):
        try:
            v = row[i]
        except IndexError:
            v = None
        tmp.append(skytools.quote_literal(v))
    fmt = "insert into %s (%s) values (%s);"
    return fmt % (tbl, ",".join(qfields), ",".join(tmp))

def magic_insert(curs, tablename, data, fields = None, use_insert = 0, quoted_table = False):
    r"""Copy/insert a list of dict/list data to database.

    If curs == None, then the copy or insert statements are returned
    as string.  For list of dict the field list is optional, as its
    possible to guess them from dict keys.

    Example:
    >>> magic_insert(None, 'tbl', [[1, '1'], [2, '2']], ['col1', 'col2'])
    'COPY public.tbl (col1,col2) FROM STDIN;\n1\t1\n2\t2\n\\.\n'
    """
    if len(data) == 0:
        return

    # decide how to process
    if hasattr(data[0], 'keys'):
        if fields == None:
            fields = data[0].keys()
        if use_insert:
            row_func = _gen_dict_insert
        else:
            row_func = _gen_dict_copy
    else:
        if fields == None:
            raise Exception("Non-dict data needs field list")
        if use_insert:
            row_func = _gen_list_insert
        else:
            row_func = _gen_list_copy

    qfields = [skytools.quote_ident(f) for f in fields]
    if quoted_table:
        qtablename = tablename
    else:
        qtablename = skytools.quote_fqident(tablename)

    # init processing
    buf = StringIO()
    if curs == None and use_insert == 0:
        fmt = "COPY %s (%s) FROM STDIN;\n"
        buf.write(fmt % (qtablename, ",".join(qfields)))

    # process data
    for row in data:
        buf.write(row_func(qtablename, row, fields, qfields))
        buf.write("\n")

    # if user needs only string, return it
    if curs == None:
        if use_insert == 0:
            buf.write("\\.\n")
        return buf.getvalue()

    # do the actual copy/inserts
    if use_insert:
        curs.execute(buf.getvalue())
    else:
        buf.seek(0)
        hdr = "%s (%s)" % (qtablename, ",".join(qfields))
        curs.copy_from(buf, hdr)

#
# Full COPY of table from one db to another
#

class CopyPipe(object):
    "Splits one big COPY to chunks."

    def __init__(self, dstcurs, tablename = None, limit = 512*1024,
                 sql_from = None):
        self.tablename = tablename
        self.sql_from = sql_from
        self.dstcurs = dstcurs
        self.buf = StringIO()
        self.limit = limit
        #hook for new data, hook func should return new data
        #def write_hook(obj, data):
        #   return data
        self.write_hook = None
        #hook for flush, hook func result is discarded
        # def flush_hook(obj):
        #   return None
        self.flush_hook = None
        self.total_rows = 0
        self.total_bytes = 0

    def write(self, data):
        "New data from psycopg"
        if self.write_hook:
            data = self.write_hook(self, data)

        self.total_bytes += len(data)
        self.total_rows += data.count("\n")

        if self.buf.tell() >= self.limit:
            pos = data.find('\n')
            if pos >= 0:
                # split at newline
                p1 = data[:pos + 1]
                p2 = data[pos + 1:]
                self.buf.write(p1)
                self.flush()

                data = p2

        self.buf.write(data)

    def flush(self):
        "Send data out."

        if self.flush_hook:
            self.flush_hook(self)

        if self.buf.tell() <= 0:
            return

        self.buf.seek(0)
        if self.sql_from:
            self.dstcurs.copy_expert(self.sql_from, self.buf)
        else:
            self.dstcurs.copy_from(self.buf, self.tablename)
        self.buf.seek(0)
        self.buf.truncate()


def full_copy(tablename, src_curs, dst_curs, column_list = [], condition = None,
        dst_tablename = None, dst_column_list = None,
        write_hook = None, flush_hook = None):
    """COPY table from one db to another."""

    # default dst table and dst columns to source ones
    dst_tablename = dst_tablename or tablename
    dst_column_list = dst_column_list or column_list[:]
    if len(dst_column_list) != len(column_list):
        raise Exception('src and dst column lists must match in length')

    def build_qfields(cols):
        if cols:
            return ",".join([skytools.quote_ident(f) for f in cols])
        else:
            return "*"

    def build_statement(table, cols):
        qtable = skytools.quote_fqident(table)
        if cols:
            qfields = build_qfields(cols)
            return "%s (%s)" % (qtable, qfields)
        else:
            return qtable

    dst = build_statement(dst_tablename, dst_column_list)
    if condition:
        src = "(SELECT %s FROM %s WHERE %s)" % (build_qfields(column_list),
                                                skytools.quote_fqident(tablename),
                                                condition)
    else:
        src = build_statement(tablename, column_list)

    if hasattr(src_curs, 'copy_expert'):
        sql_to = "COPY %s TO stdout" % src
        sql_from = "COPY %s FROM stdin" % dst
        buf = CopyPipe(dst_curs, sql_from = sql_from)
        buf.write_hook = write_hook
        buf.flush_hook = flush_hook
        src_curs.copy_expert(sql_to, buf)
    else:
        if condition:
            # regular psycopg copy_to generates invalid sql for subselect copy
            raise Exception('copy_expert() is needed for conditional copy')
        buf = CopyPipe(dst_curs, dst)
        buf.write_hook = write_hook
        buf.flush_hook = flush_hook
        src_curs.copy_to(buf, src)
    buf.flush()

    return (buf.total_bytes, buf.total_rows)


#
# SQL installer
#

class DBObject(object):
    """Base class for installable DB objects."""
    name = None
    sql = None
    sql_file = None
    def __init__(self, name, sql = None, sql_file = None):
        """Generic dbobject init."""
        self.name = name
        self.sql = sql
        self.sql_file = sql_file

    def create(self, curs, log = None):
        """Create a dbobject."""
        if log:
            log.info('Installing %s' % self.name)
        if self.sql:
            sql = self.sql
        elif self.sql_file:
            fn = self.find_file()
            if log:
                log.info("  Reading from %s" % fn)
            sql = open(fn, "r").read()
        else:
            raise Exception('object not defined')
        for stmt in skytools.parse_statements(sql):
            #if log: log.debug(repr(stmt))
            curs.execute(stmt)

    def find_file(self):
        """Find install script file."""
        return installer_find_file(self.sql_file)

class DBSchema(DBObject):
    """Handles db schema."""
    def exists(self, curs):
        """Does schema exists."""
        return exists_schema(curs, self.name)

class DBTable(DBObject):
    """Handles db table."""
    def exists(self, curs):
        """Does table exists."""
        return exists_table(curs, self.name)

class DBFunction(DBObject):
    """Handles db function."""
    def __init__(self, name, nargs, sql = None, sql_file = None):
        """Function object - number of args is significant."""
        DBObject.__init__(self, name, sql, sql_file)
        self.nargs = nargs
    def exists(self, curs):
        """Does function exists."""
        return exists_function(curs, self.name, self.nargs)

class DBLanguage(DBObject):
    """Handles db language."""
    def __init__(self, name):
        """PL object - creation happens with CREATE LANGUAGE."""
        DBObject.__init__(self, name, sql = "create language %s" % name)
    def exists(self, curs):
        """Does PL exists."""
        return exists_language(curs, self.name)

def db_install(curs, list, log = None):
    """Installs list of objects into db."""
    for obj in list:
        if not obj.exists(curs):
            obj.create(curs, log)
        else:
            if log:
                log.info('%s is installed' % obj.name)

def installer_find_file(filename):
    """Find SQL script from pre-defined paths."""
    full_fn = None
    if filename[0] == "/":
        if os.path.isfile(filename):
            full_fn = filename
    else:
        import skytools.installer_config
        dir_list = skytools.installer_config.sql_locations
        for fdir in dir_list:
            fn = os.path.join(fdir, filename)
            if os.path.isfile(fn):
                full_fn = fn
                break

    if not full_fn:
        raise Exception('File not found: '+filename)
    return full_fn

def installer_apply_file(db, filename, log):
    """Find SQL file and apply it to db, statement-by-statement."""
    fn = installer_find_file(filename)
    sql = open(fn, "r").read()
    if log:
        log.info("applying %s" % fn)
    curs = db.cursor()
    for stmt in skytools.parse_statements(sql):
        #log.debug(repr(stmt))
        curs.execute(stmt)

#
# Generate INSERT/UPDATE/DELETE statement
#

def mk_insert_sql(row, tbl, pkey_list = None, field_map = None):
    """Generate INSERT statement from dict data.

    >>> mk_insert_sql({'id': '1', 'data': None}, 'tbl')
    "insert into public.tbl (data, id) values (null, '1');"
    """

    col_list = []
    val_list = []
    if field_map:
        for src, dst in field_map.iteritems():
            col_list.append(skytools.quote_ident(dst))
            val_list.append(skytools.quote_literal(row[src]))
    else:
        for c, v in row.iteritems():
            col_list.append(skytools.quote_ident(c))
            val_list.append(skytools.quote_literal(v))
    col_str = ", ".join(col_list)
    val_str = ", ".join(val_list)
    return "insert into %s (%s) values (%s);" % (
                    skytools.quote_fqident(tbl), col_str, val_str)

def mk_update_sql(row, tbl, pkey_list, field_map = None):
    r"""Generate UPDATE statement from dict data.

    >>> mk_update_sql({'id': 0, 'id2': '2', 'data': 'str\\'}, 'Table', ['id', 'id2'])
    'update only public."Table" set data = E\'str\\\\\' where id = \'0\' and id2 = \'2\';'
    """

    if len(pkey_list) < 1:
        raise Exception("update needs pkeys")
    set_list = []
    whe_list = []
    pkmap = {}
    for k in pkey_list:
        pkmap[k] = 1
        new_k = field_map and field_map[k] or k
        col = skytools.quote_ident(new_k)
        val = skytools.quote_literal(row[k])
        whe_list.append("%s = %s" % (col, val))

    if field_map:
        for src, dst in field_map.iteritems():
            if src not in pkmap:
                col = skytools.quote_ident(dst)
                val = skytools.quote_literal(row[src])
                set_list.append("%s = %s" % (col, val))
    else:
        for col, val in row.iteritems():
            if col not in pkmap:
                col = skytools.quote_ident(col)
                val = skytools.quote_literal(val)
                set_list.append("%s = %s" % (col, val))
    return "update only %s set %s where %s;" % (skytools.quote_fqident(tbl),
            ", ".join(set_list), " and ".join(whe_list))

def mk_delete_sql(row, tbl, pkey_list, field_map = None):
    """Generate DELETE statement from dict data."""

    if len(pkey_list) < 1:
        raise Exception("delete needs pkeys")
    whe_list = []
    for k in pkey_list:
        new_k = field_map and field_map[k] or k
        col = skytools.quote_ident(new_k)
        val = skytools.quote_literal(row[k])
        whe_list.append("%s = %s" % (col, val))
    whe_str = " and ".join(whe_list)
    return "delete from only %s where %s;" % (skytools.quote_fqident(tbl), whe_str)

if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = timeutil

"""Fill gaps in Python time API-s.

parse_iso_timestamp:
    Parse reasonable subset of ISO_8601 timestamp formats.
    [ http://en.wikipedia.org/wiki/ISO_8601 ]

datetime_to_timestamp:
    Get POSIX timestamp from datetime() object.

"""

import re
import time
from datetime import datetime, timedelta, tzinfo

__all__ = ['parse_iso_timestamp', 'FixedOffsetTimezone', 'datetime_to_timestamp']

class FixedOffsetTimezone(tzinfo):
    """Fixed offset in minutes east from UTC."""
    __slots__ = ('__offset', '__name')

    def __init__(self, offset):
        self.__offset = timedelta(minutes = offset)

        # numeric tz name
        h, m = divmod(abs(offset), 60)
        if offset < 0:
            h = -h
        if m:
            self.__name = "%+03d:%02d" % (h,m)
        else:
            self.__name = "%+03d" % h

    def utcoffset(self, dt):
        return self.__offset

    def tzname(self, dt):
        return self.__name

    def dst(self, dt):
        return ZERO

ZERO = timedelta(0)

#
# Parse ISO_8601 timestamps.
#

"""
TODO:
- support more combinations from ISO 8601 (only reasonable ones)
- cache TZ objects
- make it faster?
"""

_iso_regex = r"""
    \s*
    (?P<year> \d\d\d\d) [-] (?P<month> \d\d) [-] (?P<day> \d\d) [ T]
    (?P<hour> \d\d) [:] (?P<min> \d\d)
    (?: [:] (?P<sec> \d\d ) (?: [.,] (?P<ss> \d+))? )?
    (?: \s*  (?P<tzsign> [-+]) (?P<tzhr> \d\d) (?: [:]? (?P<tzmin> \d\d))? )?
    \s* $
    """
_iso_rc = None

def parse_iso_timestamp(s, default_tz = None):
    """Parse ISO timestamp to datetime object.
    
    YYYY-MM-DD[ T]HH:MM[:SS[.ss]][-+HH[:MM]]

    Assumes that second fractions are zero-trimmed from the end,
    so '.15' means 150000 microseconds.

    If the timezone offset is not present, use default_tz as tzinfo.
    By default its None, meaning the datetime object will be without tz.

    Only fixed offset timezones are supported.

    >>> str(parse_iso_timestamp('2005-06-01 15:00'))
    '2005-06-01 15:00:00'
    >>> str(parse_iso_timestamp(' 2005-06-01T15:00 +02 '))
    '2005-06-01 15:00:00+02:00'
    >>> str(parse_iso_timestamp('2005-06-01 15:00:33+02:00'))
    '2005-06-01 15:00:33+02:00'
    >>> d = parse_iso_timestamp('2005-06-01 15:00:59.33 +02')
    >>> d.strftime("%z %Z")
    '+0200 +02'
    >>> str(parse_iso_timestamp(str(d)))
    '2005-06-01 15:00:59.330000+02:00'
    >>> parse_iso_timestamp('2005-06-01 15:00-0530').strftime('%Y-%m-%d %H:%M %z %Z')
    '2005-06-01 15:00 -0530 -05:30'
    """

    global _iso_rc
    if _iso_rc is None:
        _iso_rc = re.compile(_iso_regex, re.X)

    m = _iso_rc.match(s)
    if not m:
        raise ValueError('Date not in ISO format: %s' % repr(s))

    tz = default_tz
    if m.group('tzsign'):
        tzofs = int(m.group('tzhr')) * 60
        if m.group('tzmin'):
            tzofs += int(m.group('tzmin'))
        if m.group('tzsign') == '-':
            tzofs = -tzofs
        tz = FixedOffsetTimezone(tzofs)

    return datetime(int(m.group('year')),
                int(m.group('month')),
                int(m.group('day')),
                int(m.group('hour')),
                int(m.group('min')),
                m.group('sec') and int(m.group('sec')) or 0,
                m.group('ss') and int(m.group('ss').ljust(6, '0')) or 0,
                tz)

#
# POSIX timestamp from datetime()
#

UTC = FixedOffsetTimezone(0)
TZ_EPOCH = datetime.fromtimestamp(0, UTC)
UTC_NOTZ_EPOCH = datetime.utcfromtimestamp(0)

def datetime_to_timestamp(dt, local_time=True):
    """Get posix timestamp from datetime() object.

    if dt is without timezone, then local_time specifies
    whether it's UTC or local time.

    Returns seconds since epoch as float.

    >>> datetime_to_timestamp(parse_iso_timestamp("2005-06-01 15:00:59.5 +02"))
    1117630859.5
    >>> datetime_to_timestamp(datetime.fromtimestamp(1117630859.5, UTC))
    1117630859.5
    >>> datetime_to_timestamp(datetime.fromtimestamp(1117630859.5))
    1117630859.5
    >>> now = datetime.utcnow()
    >>> now2 = datetime.utcfromtimestamp(datetime_to_timestamp(now, False))
    >>> abs(now2.microsecond - now.microsecond) < 100
    True
    >>> now2 = now2.replace(microsecond = now.microsecond)
    >>> now == now2
    True
    >>> now = datetime.now()
    >>> now2 = datetime.fromtimestamp(datetime_to_timestamp(now))
    >>> abs(now2.microsecond - now.microsecond) < 100
    True
    >>> now2 = now2.replace(microsecond = now.microsecond)
    >>> now == now2
    True
    """
    if dt.tzinfo:
        delta = dt - TZ_EPOCH
        return delta.total_seconds()
    elif local_time:
        s = time.mktime(dt.timetuple())
        return s + (dt.microsecond / 1000000.0)
    else:
        delta = dt - UTC_NOTZ_EPOCH
        return delta.total_seconds()

if __name__ == '__main__':
    import doctest
    doctest.testmod()


########NEW FILE########
__FILENAME__ = tnetstrings
# Note this implementation is more strict than necessary to demonstrate
# minimum restrictions on types allowed in dictionaries.

def dump(data):
    if type(data) is long or type(data) is int:
        out = str(data)
        return '%d:%s#' % (len(out), out)
    elif type(data) is float:
        out = '%f' % data
        return '%d:%s^' % (len(out), out)
    elif type(data) is str:
        return '%d:' % len(data) + data + ',' 
    elif type(data) is dict:
        return dump_dict(data)
    elif type(data) is list:
        return dump_list(data)
    elif data == None:
        return '0:~'
    elif type(data) is bool:
        out = repr(data).lower()
        return '%d:%s!' % (len(out), out)
    else:
        assert False, "Can't serialize stuff that's %s." % type(data)


def parse(data):
    payload, payload_type, remain = parse_payload(data)

    if payload_type == '#':
        value = int(payload)
    elif payload_type == '}':
        value = parse_dict(payload)
    elif payload_type == ']':
        value = parse_list(payload)
    elif payload_type == '!':
        value = payload == 'true'
    elif payload_type == '^':
        value = float(payload)
    elif payload_type == '~':
        assert len(payload) == 0, "Payload must be 0 length for null."
        value = None
    elif payload_type == ',':
        value = payload
    else:
        assert False, "Invalid payload type: %r" % payload_type

    return value, remain

def parse_payload(data):
    assert data, "Invalid data to parse, it's empty."
    length, extra = data.split(':', 1)
    length = int(length)

    payload, extra = extra[:length], extra[length:]
    assert extra, "No payload type: %r, %r" % (payload, extra)
    payload_type, remain = extra[0], extra[1:]

    assert len(payload) == length, "Data is wrong length %d vs %d" % (length, len(payload))
    return payload, payload_type, remain

def parse_list(data):
    if len(data) == 0: return []

    result = []
    value, extra = parse(data)
    result.append(value)

    while extra:
        value, extra = parse(extra)
        result.append(value)

    return result

def parse_pair(data):
    key, extra = parse(data)
    assert extra, "Unbalanced dictionary store."
    value, extra = parse(extra)

    return key, value, extra

def parse_dict(data):
    if len(data) == 0: return {}

    key, value, extra = parse_pair(data)
    assert type(key) is str, "Keys can only be strings."

    result = {key: value}

    while extra:
        key, value, extra = parse_pair(extra)
        result[key] = value
  
    return result
    


def dump_dict(data):
    result = []
    for k,v in data.items():
        result.append(dump(str(k)))
        result.append(dump(v))

    payload = ''.join(result)
    return '%d:' % len(payload) + payload + '}'


def dump_list(data):
    result = []
    for i in data:
        result.append(dump(i))

    payload = ''.join(result)
    return '%d:' % len(payload) + payload + ']'



########NEW FILE########
__FILENAME__ = utf8
r"""UTF-8 sanitizer.

Python's UTF-8 parser is quite relaxed, this creates problems when
talking with other software that uses stricter parsers.

>>> safe_utf8_decode("foobar")
(True, u'foobar')
>>> safe_utf8_decode('X\xed\xa0\x80Y\xed\xb0\x89Z')
(False, u'X\ufffdY\ufffdZ')
>>> safe_utf8_decode('X\xed\xa0\x80\xed\xb0\x89Z')
(False, u'X\U00010009Z')
>>> safe_utf8_decode('X\0Z')
(False, u'X\ufffdZ')
>>> safe_utf8_decode('OK')
(True, u'OK')
>>> safe_utf8_decode('X\xF1Y')
(False, u'X\ufffdY')
"""

import re, codecs

__all__ = ['safe_utf8_decode']

# by default, use same symbol as 'replace'
REPLACEMENT_SYMBOL = unichr(0xFFFD)

def _fix_utf8(m):
    """Merge UTF16 surrogates, replace others"""
    u = m.group()
    if len(u) == 2:
        # merge into single symbol
        c1 = ord(u[0])
        c2 = ord(u[1])
        c = 0x10000 + ((c1 & 0x3FF) << 10) + (c2 & 0x3FF)
        return unichr(c)
    else:
        # use replacement symbol
        return REPLACEMENT_SYMBOL

_urc = None

def sanitize_unicode(u):
    """Fix invalid symbols in unicode string."""
    global _urc

    assert isinstance(u, unicode)

    # regex for finding invalid chars, works on unicode string
    if not _urc:
        rx = u"[\uD800-\uDBFF] [\uDC00-\uDFFF]? | [\0\uDC00-\uDFFF]"
        _urc = re.compile(rx, re.X)

    # now find and fix UTF16 surrogates
    m = _urc.search(u)
    if m:
        u = _urc.sub(_fix_utf8, u)
    return u

def safe_replace(exc):
    """Replace only one symbol at a time.

    Builtin .decode('xxx', 'replace') replaces several symbols
    together, which is unsafe.
    """
    if not isinstance(exc, UnicodeDecodeError):
        raise exc
    c2 = REPLACEMENT_SYMBOL

    # we could assume latin1
    if 0:
        c1 = exc.object[exc.start]
        c2 = unichr(ord(c1))

    return c2, exc.start + 1

# register, it will be globally available
codecs.register_error("safe_replace", safe_replace)

def safe_utf8_decode(s):
    """Decode UTF-8 safely.

    Acts like str.decode('utf8', 'replace') but also fixes
    UTF16 surrogates and NUL bytes, which Python's default
    decoder does not do.
    
    @param s: utf8-encoded byte string
    @return: tuple of (was_valid_utf8, unicode_string) 
    """

    # decode with error detection
    ok = True
    try:
        # expect no errors by default
        u = s.decode('utf8')
    except UnicodeDecodeError:
        u = s.decode('utf8', 'safe_replace')
        ok = False
    
    u2 = sanitize_unicode(u)
    if u is not u2:
        ok = False
    return (ok, u2)

if __name__ == '__main__':
    import doctest
    doctest.testmod()


########NEW FILE########
__FILENAME__ = _pyquoting
# _pyquoting.py

"""Various helpers for string quoting/unquoting.

Here is pure Python that should match C code in _cquoting.
"""

import urllib, re

__all__ = [
    "quote_literal", "quote_copy", "quote_bytea_raw",
    "db_urlencode", "db_urldecode", "unescape",
    "unquote_literal",
]

# 
# SQL quoting
#

def quote_literal(s):
    """Quote a literal value for SQL.

    If string contains '\\', extended E'' quoting is used,
    otherwise standard quoting.  Input value of None results
    in string "null" without quotes.

    Python implementation.
    """

    if s == None:
        return "null"
    s = str(s).replace("'", "''")
    s2 = s.replace("\\", "\\\\")
    if len(s) != len(s2):
        return "E'" + s2 + "'"
    return "'" + s2 + "'"

def quote_copy(s):
    """Quoting for copy command.  None is converted to \\N.
    
    Python implementation.
    """

    if s == None:
        return "\\N"
    s = str(s)
    s = s.replace("\\", "\\\\")
    s = s.replace("\t", "\\t")
    s = s.replace("\n", "\\n")
    s = s.replace("\r", "\\r")
    return s

_bytea_map = None
def quote_bytea_raw(s):
    """Quoting for bytea parser.  Returns None as None.
    
    Python implementation.
    """
    global _bytea_map
    if s == None:
        return None
    if 1 and _bytea_map is None:
        _bytea_map = {}
        for i in xrange(256):
            c = chr(i)
            if i < 0x20 or i >= 0x7F:
                _bytea_map[c] = "\\%03o" % i
            elif c == "\\":
                _bytea_map[c] = r"\\"
            else:
                _bytea_map[c] = c
    return "".join([_bytea_map[c] for c in s])

#
# Database specific urlencode and urldecode.
#

def db_urlencode(dict):
    """Database specific urlencode.

    Encode None as key without '='.  That means that in "foo&bar=",
    foo is NULL and bar is empty string.

    Python implementation.
    """

    elem_list = []
    for k, v in dict.items():
        if v is None:
            elem = urllib.quote_plus(str(k))
        else:
            elem = urllib.quote_plus(str(k)) + '=' + urllib.quote_plus(str(v))
        elem_list.append(elem)
    return '&'.join(elem_list)

def db_urldecode(qs):
    """Database specific urldecode.

    Decode key without '=' as None.
    This also does not support one key several times.

    Python implementation.
    """

    res = {}
    for elem in qs.split('&'):
        if not elem:
            continue
        pair = elem.split('=', 1)
        name = urllib.unquote_plus(pair[0])

        # keep only one instance around
        name = intern(str(name))

        if len(pair) == 1:
            res[name] = None
        else:
            res[name] = urllib.unquote_plus(pair[1])
    return res

#
# Remove C-like backslash escapes
#

_esc_re = r"\\([0-7]{1,3}|.)"
_esc_rc = re.compile(_esc_re)
_esc_map = {
    't': '\t',
    'n': '\n',
    'r': '\r',
    'a': '\a',
    'b': '\b',
    "'": "'",
    '"': '"',
    '\\': '\\',
}

def _sub_unescape_c(m):
    """unescape single escape seq."""
    v = m.group(1)
    if (len(v) == 1) and (v < '0' or v > '7'):
        try:
            return _esc_map[v]
        except KeyError:
            return v
    else:
        return chr(int(v, 8))

def unescape(val):
    """Removes C-style escapes from string.
    Python implementation.
    """
    return _esc_rc.sub(_sub_unescape_c, val)

_esql_re = r"''|\\([0-7]{1,3}|.)"
_esql_rc = re.compile(_esql_re)
def _sub_unescape_sqlext(m):
    """Unescape extended-quoted string."""
    if m.group() == "''":
        return "'"
    v = m.group(1)
    if (len(v) == 1) and (v < '0' or v > '7'):
        try:
            return _esc_map[v]
        except KeyError:
            return v
    return chr(int(v, 8))

def unquote_literal(val, stdstr = False):
    """Unquotes SQL string.

    E'..' -> extended quoting.
    '..' -> standard or extended quoting
    null -> None
    other -> returned as-is
    """
    if val[0] == "'" and val[-1] == "'":
        if stdstr:
            return val[1:-1].replace("''", "'")
        else:
            return _esql_rc.sub(_sub_unescape_sqlext, val[1:-1])
    elif len(val) > 2 and val[0] in ('E', 'e') and val[1] == "'" and val[-1] == "'":
        return _esql_rc.sub(_sub_unescape_sqlext, val[2:-1])
    elif len(val) >= 2 and val[0] == '$' and val[-1] == '$':
        p1 = val.find('$', 1)
        p2 = val.rfind('$', 1, -1)
        if p1 > 0 and p2 > p1:
            t1 = val[:p1+1]
            t2 = val[p2:]
            if t1 == t2:
                return val[len(t1):-len(t1)]
        raise Exception("Bad dollar-quoted string")
    elif val.lower() == "null":
        return None
    return val


########NEW FILE########
__FILENAME__ = walmgr
#! /usr/bin/env python

"""WALShipping manager.

walmgr INI COMMAND [-n]

Master commands:
  setup              Configure PostgreSQL for WAL archiving
  sync               Copies in-progress WALs to slave
  syncdaemon         Daemon mode for regular syncing
  stop               Stop archiving - de-configure PostgreSQL
  periodic           Run periodic command if configured.
  synch-standby      Manage synchronous streaming replication.

Slave commands:
  boot               Stop playback, accept queries
  pause              Just wait, don't play WAL-s
  continue           Start playing WAL-s again
  createslave        Create streaming replication slave

Common commands:
  init               Create configuration files, set up ssh keys.
  listbackups        List backups.
  backup             Copies all master data to slave. Will keep backup history
                     if slave keep_backups is set. EXPERIMENTAL: If run on slave,
                     creates backup from in-recovery slave data.
  restore [set][dst] Stop postmaster, move new data dir to right location and start
                     postmaster in playback mode. Optionally use [set] as the backupset
                     name to restore. In this case the directory is copied, not moved.
  cleanup            Cleanup any walmgr files after stop.

Internal commands:
  xarchive           archive one WAL file (master)
  xrestore           restore one WAL file (slave)
  xlock              Obtain backup lock (master)
  xrelease           Release backup lock (master)
  xrotate            Rotate backup sets, expire and archive oldest if necessary.
  xpurgewals         Remove WAL files not needed for backup (slave)
  xpartialsync       Append data to WAL file (slave)
"""

import os, sys, re, signal, time, traceback
import errno, glob, ConfigParser, shutil, subprocess

import pkgloader
pkgloader.require('skytools', '3.0')

import skytools

DEFAULT_PG_VERSION = "8.3"

XLOG_SEGMENT_SIZE = 16 * 1024**2

def usage(err):
    if err > 0:
        print >>sys.stderr, __doc__
    else:
        print __doc__
    sys.exit(err)

def die(err,msg):
    print >> sys.stderr, msg
    sys.exit(err)

def yesno(prompt):
    """Ask a Yes/No question"""
    while True:
        sys.stderr.write(prompt + " ")
        sys.stderr.flush()
        answer = sys.stdin.readline()
        if not answer:
            return False
        answer = answer.strip().lower()
        if answer in ('yes','y'):
            return True
        if answer in ('no','n'):
            return False
        sys.stderr.write("Please answer yes or no.\n")

def copy_conf(src, dst):
    """Copy config file or symlink.
    Does _not_ overwrite target.
    """
    if os.path.isdir(dst):
        dst = os.path.join(dst, os.path.basename(src))
    if os.path.exists(dst):
        return False
    if os.path.islink(src):
        linkdst = os.readlink(src)
        os.symlink(linkdst, dst)
    elif os.path.isfile(src):
        shutil.copy2(src, dst)
    else:
        raise Exception("Unsupported file type: %s" % src)
    return True

class WalChunk:
    """Represents a chunk of WAL used in record based shipping"""
    def __init__(self,filename,pos=0,bytes=0):
        self.filename = filename
        self.pos = pos
        self.bytes = bytes
        self.start_time = time.time()
        self.sync_count = 0
        self.sync_time = 0.0

    def __str__(self):
        return "%s @ %d +%d" % (self.filename, self.pos, self.bytes)

class PgControlData:
    """Contents of pg_controldata"""

    def __init__(self, bin_dir, data_dir, findRestartPoint):
        """Collect last checkpoint information from pg_controldata output"""
        self.xlogid = None
        self.xrecoff = None
        self.timeline = None
        self.wal_size = None
        self.wal_name = None
        self.cluster_state = None
        self.is_shutdown = False
        self.pg_version = 0
        self.is_valid = False

        try:
            pg_controldata = os.path.join(bin_dir, "pg_controldata")
            pipe = subprocess.Popen([ pg_controldata, data_dir ], stdout=subprocess.PIPE)
        except OSError:
            # don't complain if we cannot execute it
            return

        matches = 0
        for line in pipe.stdout.readlines():
            if findRestartPoint:
                m = re.match("^Latest checkpoint's REDO location:\s+([0-9A-F]+)/([0-9A-F]+)", line)
            else:
                m = re.match("^Latest checkpoint location:\s+([0-9A-F]+)/([0-9A-F]+)", line)
            if m:
                matches += 1
                self.xlogid = int(m.group(1), 16)
                self.xrecoff = int(m.group(2), 16)
            m = re.match("^Latest checkpoint's TimeLineID:\s+(\d+)", line)
            if m:
                matches += 1
                self.timeline = int(m.group(1))
            m = re.match("^Bytes per WAL segment:\s+(\d+)", line)
            if m:
                matches += 1
                self.wal_size = int(m.group(1))
            m = re.match("^pg_control version number:\s+(\d+)", line)
            if m:
                matches += 1
                self.pg_version = int(m.group(1))
            m = re.match("^Database cluster state:\s+(.*$)", line)
            if m:
                matches += 1
                self.cluster_state = m.group(1)
                self.is_shutdown = (self.cluster_state == "shut down")

        # ran successfully and we got our needed matches
        if pipe.wait() == 0 and matches == 5:
            self.wal_name = "%08X%08X%08X" % \
                (self.timeline, self.xlogid, self.xrecoff / self.wal_size)
            self.is_valid = True

class BackupLabel:
    """Backup label contents"""

    def __init__(self, backupdir):
        """Initialize a new BackupLabel from existing file"""
        filename = os.path.join(backupdir, "backup_label")
        self.first_wal = None
        self.start_time = None
        self.label_string = None
        if not os.path.exists(filename):
            return
        for line in open(filename):
            m = re.match('^START WAL LOCATION: [^\s]+ \(file ([0-9A-Z]+)\)$', line)
            if m:
                self.first_wal = m.group(1)
            m = re.match('^START TIME:\s(.*)$', line)
            if m:
                self.start_time = m.group(1)
            m = re.match('^LABEL: (.*)$', line)
            if m:
                self.label_string = m.group(1)

class Pgpass:
    """Manipulate pgpass contents"""

    def __init__(self, passfile):
        """Load .pgpass contents"""
        self.passfile = os.path.expanduser(passfile)
        self.contents = []

        if os.path.isfile(self.passfile):
            self.contents = open(self.passfile).readlines()

    def split_pgpass_line(selg, pgline):
        """Parses pgpass line, returns dict"""
        try:
            (host, port, db, user, pwd) = pgline.rstrip('\n\r').split(":")
            return {'host': host, 'port': port, 'db': db, 'user': user, 'pwd': pwd}
        except ValueError:
            return None

    def ensure_user(self, host, port, user, pwd):
        """Ensure that line for streaming replication exists in .pgpass"""
        self.remove_user(host, port, user)
        self.contents.insert(0, '%s:%s:%s:%s:%s\n' % (host, port, 'replication', user, pwd))

    def remove_user(self, host, port, user):
        """Remove all matching lines from .pgpass"""

        new_contents = []
        found = False
        for l in self.contents:
            p = self.split_pgpass_line(l)
            if p and p['host'] == host and p['port'] == port and p['user'] == user and p['db'] == 'replication':
                    found = True
                    continue

            new_contents.append(l)

        self.contents = new_contents
        return found

    def write(self):
        """Write contents back to file"""
        f = open(self.passfile,'w')
        os.chmod(self.passfile, 0600)
        f.writelines(self.contents)
        f.close()


class PostgresConfiguration:
    """Postgres configuration manipulation"""

    def __init__(self, walmgr, cf_file):
        """load the configuration from master_config"""
        self.walmgr = walmgr
        self.log = walmgr.log
        self.cf_file = cf_file
        self.cf_buf = open(self.cf_file, "r").read()

    def archive_mode(self):
        """Return value for specified parameter"""
        # see if explicitly set
        m = re.search("^\s*archive_mode\s*=\s*'?([a-zA-Z01]+)'?\s*#?.*$", self.cf_buf, re.M | re.I)
        if m:
            return m.group(1)
        # also, it could be commented out as initdb leaves it
        # it'd probably be best to check from the database ...
        m = re.search("^#archive_mode\s*=.*$", self.cf_buf, re.M | re.I)
        if m:
            return "off"
        return None

    def synchronous_standby_names(self):
        """Return value for specified parameter"""
        # see if explicitly set
        m = re.search("^\s*synchronous_standby_names\s*=\s*'([^']*)'\s*#?.*$", self.cf_buf, re.M | re.I)
        if m:
            return m.group(1)
        # also, it could be commented out as initdb leaves it
        # it'd probably be best to check from the database ...
        m = re.search("^#synchronous_standby_names\s*=.*$", self.cf_buf, re.M | re.I)
        if m:
            return ''
        return None

    def wal_level(self):
        """Return value for specified parameter"""
        # see if explicitly set
        m = re.search("^\s*wal_level\s*=\s*'?([a-z_]+)'?\s*#?.*$", self.cf_buf, re.M | re.I)
        if m:
            return m.group(1)
        # also, it could be commented out as initdb leaves it
        # it'd probably be best to check from the database ...
        m = re.search("^#wal_level\s*=.*$", self.cf_buf, re.M | re.I)
        if m:
            return "minimal"
        return None

    def modify(self, cf_params):
        """Change the configuration parameters supplied in cf_params"""

        for (param, value) in cf_params.iteritems():
            r_active = re.compile("^\s*%s\s*=\s*([^\s#]*).*$" % param, re.M)
            r_disabled = re.compile("^\s*#\s*%s\s*=.*$" % param, re.M)

            cf_full = "%s = '%s'" % (param, value)

            m = r_active.search(self.cf_buf)
            if m:
                old_val = m.group(1)
                self.log.debug("found parameter %s with value %r", param, old_val)
                self.cf_buf = "%s%s%s" % (self.cf_buf[:m.start()], cf_full, self.cf_buf[m.end():])
            else:
                m = r_disabled.search(self.cf_buf)
                if m:
                    self.log.debug("found disabled parameter %s", param)
                    self.cf_buf = "%s\n%s%s" % (self.cf_buf[:m.end()], cf_full, self.cf_buf[m.end():])
                else:
                    # not found, append to the end
                    self.log.debug("found no value")
                    self.cf_buf = "%s\n%s\n\n" % (self.cf_buf, cf_full)

    def write(self):
        """Write the configuration back to file"""
        cf_old = self.cf_file + ".old"
        cf_new = self.cf_file + ".new"

        if self.walmgr.not_really:
            cf_new = "/tmp/postgresql.conf.new"
            open(cf_new, "w").write(self.cf_buf)
            self.log.info("Showing diff")
            os.system("diff -u %s %s" % (self.cf_file, cf_new))
            self.log.info("Done diff")
            os.remove(cf_new)
            return

        # polite method does not work, as usually not enough perms for it
        open(self.cf_file, "w").write(self.cf_buf)

    def set_synchronous_standby_names(self,param_value):
        """Helper function to change synchronous_standby_names and signal postmaster"""

        self.log.info("Changing synchronous_standby_names from %r to %r", self.synchronous_standby_names(), param_value)
        cf_params = dict()
        cf_params['synchronous_standby_names'] = param_value
        self.modify(cf_params)
        self.write()

        data_dir=self.walmgr.cf.getfile("master_data")
        self.log.info("Sending SIGHUP to postmaster")
        self.walmgr.signal_postmaster(data_dir, signal.SIGHUP)


class WalMgr(skytools.DBScript):

    def init_optparse(self, parser=None):
        p = skytools.DBScript.init_optparse(self, parser)
        p.set_usage(__doc__.strip())
        p.add_option("-n", "--not-really", action="store_true", dest="not_really",
                     help = "Don't actually do anything.", default=False)
        p.add_option("", "--init-master", action="store_true", dest="init_master",
                     help = "Initialize master walmgr.", default=False)
        p.add_option("", "--slave", action="store", type="string", dest="slave",
                     help = "Slave host name.", default="")
        p.add_option("", "--pgdata", action="store", type="string", dest="pgdata",
                     help = "Postgres data directory.", default="")
        p.add_option("", "--config-dir", action="store", type="string", dest="config_dir",
                     help = "Configuration file location for --init-X commands.", default="~/conf")
        p.add_option("", "--ssh-keygen", action="store_true", dest="ssh_keygen",
                     help = "master: generate SSH key pair if needed", default=False)
        p.add_option("", "--ssh-add-key", action="store", dest="ssh_add_key",
                     help = "slave: add public key to authorized_hosts", default=False)
        p.add_option("", "--ssh-remove-key", action="store", dest="ssh_remove_key",
                     help = "slave: remove master key from authorized_hosts", default=False)
        p.add_option("", "--add-password", action="store", dest="add_password",
                     help = "slave: add password from file to .pgpass. Additional fields will be extracted from primary-conninfo", default=False)
        p.add_option("", "--remove-password", action="store_true", dest="remove_password",
                     help = "slave: remove previously added line from .pgpass", default=False)
        p.add_option("", "--primary-conninfo", action="store", dest="primary_conninfo", default=None,
                     help = "slave: connect string for streaming replication master")
        p.add_option("", "--init-slave", action="store_true", dest="init_slave",
                     help = "Initialize slave walmgr.", default=False)
        p.add_option("", "--synch-standby", action="store", dest="synchronous_standby_names", default=None,
                help = "master: do the same thing as command synch-standby, but do not use INI file")
        return p

    def load_config(self):
        """override config load to allow operation without a config file"""

        if len(self.args) < 1:
            # no config file, generate default

            # guess the job name from cmdline options
            if self.options.init_master:
                job_name = 'wal-master'
            elif self.options.init_slave:
                job_name = 'wal-slave'
            else:
                job_name = 'walmgr'

            # common config settings
            opt_dict = {
                'use_skylog':       '0',
                'job_name':         job_name,
            }

            # master configuration settings
            master_opt_dict = {
                'master_db':        'dbname=template1',
                'completed_wals':   '%%(slave)s:%%(walmgr_data)s/logs.complete',
                'partial_wals':     '%%(slave)s:%%(walmgr_data)s/logs.partial',
                'full_backup':      '%%(slave)s:%%(walmgr_data)s/data.master',
                'config_backup':    '%%(slave)s:%%(walmgr_data)s/config.backup',
                'keep_symlinks':    '1',
                'compression':      '0',
                'walmgr_data':      '~/walshipping',
                'logfile':          '~/log/%(job_name)s.log',
                'pidfile':          '~/pid/%(job_name)s.pid',
                'use_skylog':       '1',
            }

            # slave configuration settings
            slave_opt_dict = {
                'completed_wals':   '%%(walmgr_data)s/logs.complete',
                'partial_wals':     '%%(walmgr_data)s/logs.partial',
                'full_backup':      '%%(walmgr_data)s/data.master',
                'config_backup':    '%%(walmgr_data)s/config.backup',
                'walmgr_data':      '~/walshipping',
                'logfile':          '~/log/%(job_name)s.log',
                'pidfile':          '~/pid/%(job_name)s.pid',
                'use_skylog':       '1',
            }

            if self.options.init_master:
                opt_dict.update(master_opt_dict)
            elif self.options.init_slave:
                opt_dict.update(slave_opt_dict)

            self.is_master = self.options.init_master

            config = skytools.Config(self.service_name, None,
                user_defs = opt_dict, override = self.cf_override)
        else:
            # default to regular config handling
            config = skytools.DBScript.load_config(self)

            self.is_master = config.has_option('master_data')

        # create the log and pid files if needed
        for cfk in [ "logfile", "pidfile" ]:
            if config.has_option(cfk):
                dirname = os.path.dirname(config.getfile(cfk))
                if not os.path.isdir(dirname):
                    os.makedirs(dirname)

        return config

    def __init__(self, args):
        skytools.DBScript.__init__(self, 'walmgr', args)
        self.set_single_loop(1)

        self.not_really = self.options.not_really
        self.pg_backup = 0
        self.walchunk = None
        self.script = os.path.abspath(sys.argv[0])

        if len(self.args) > 1:
            # normal operations, cfgfile and command
            self.cfgfile = self.args[0]
            self.cmd = self.args[1]
            self.args = self.args[2:]
        else:
            if self.options.init_master:
                self.cmd = 'init_master'
            elif self.options.init_slave:
                self.cmd = 'init_slave'
            elif self.options.synchronous_standby_names is not None:
                self.cmd = "synch-standby"
            else:
                usage(1)

            self.cfgfile = None
            self.args = []

        if self.cmd not in ('sync', 'syncdaemon'):
            # don't let pidfile interfere with normal operations, but
            # disallow concurrent syncing
            self.pidfile = None

        cmdtab = {
            'init_master':   self.walmgr_init_master,
            'init_slave':    self.walmgr_init_slave,
            'setup':         self.walmgr_setup,
            'stop':          self.master_stop,
            'backup':        self.run_backup,
            'listbackups':   self.list_backups,
            'restore':       self.restore_database,
            'periodic':      self.master_periodic,
            'sync':          self.master_sync,
            'syncdaemon':    self.master_syncdaemon,
            'pause':         self.slave_pause,
            'continue':      self.slave_continue,
            'boot':          self.slave_boot,
            'createslave':   self.slave_createslave,
            'cleanup':       self.walmgr_cleanup,
            'synch-standby': self.master_synch_standby,
            'xlock':         self.slave_lock_backups_exit,
            'xrelease':      self.slave_resume_backups,
            'xrotate':       self.slave_rotate_backups,
            'xpurgewals':    self.slave_purge_wals,
            'xarchive':      self.master_xarchive,
            'xrestore':      self.xrestore,
            'xpartialsync':  self.slave_append_partial,
        }

        if not cmdtab.has_key(self.cmd):
            usage(1)
        self.work = cmdtab[self.cmd]

    def assert_is_master(self, master_required):
        if self.is_master != master_required:
            self.log.warning("Action not available on current node.")
            sys.exit(1)

    def pg_start_backup(self, code):
        q = "select pg_start_backup('FullBackup')"
        self.log.info("Execute SQL: %s; [%s]", q, self.cf.get("master_db"))
        if self.not_really:
            self.pg_backup = 1
            return
        db = self.get_database("master_db")
        db.cursor().execute(q)
        db.commit()
        self.close_database("master_db")
        self.pg_backup = 1

    def pg_stop_backup(self):
        if not self.pg_backup:
            return

        q = "select pg_stop_backup()"
        self.log.info("Execute SQL: %s; [%s]", q, self.cf.get("master_db"))
        if self.not_really:
            return
        db = self.get_database("master_db")
        db.cursor().execute(q)
        db.commit()
        self.close_database("master_db")

    def signal_postmaster(self, data_dir, sgn):
        pidfile = os.path.join(data_dir, "postmaster.pid")
        if not os.path.isfile(pidfile):
            self.log.info("postmaster is not running (pidfile not present)")
            return False
        buf = open(pidfile, "r").readline()
        pid = int(buf.strip())
        self.log.debug("Signal %d to process %d", sgn, pid)
        if sgn == 0 or not self.not_really:
            try:
                os.kill(pid, sgn)
            except OSError, ex:
                if ex.errno == errno.ESRCH:
                    self.log.info("postmaster is not running (no process at indicated PID)")
                    return False
                else:
                    raise
        return True

    def exec_rsync(self,args,die_on_error=False):
        cmdline = [ "rsync", "-a", "--quiet" ]
        if self.cf.getint("compression", 0) > 0:
            cmdline.append("-z")
        cmdline += args

        cmd = "' '".join(cmdline)
        self.log.debug("Execute rsync cmd: %r", cmd)
        if self.not_really:
            return 0
        res = os.spawnvp(os.P_WAIT, cmdline[0], cmdline)
        if res == 24:
            self.log.info("Some files vanished, but thats OK")
            res = 0
        elif res != 0:
            self.log.fatal("rsync exec failed, res=%d", res)
            if die_on_error:
                sys.exit(1)
        return res

    def exec_big_rsync(self, args):
        if self.exec_rsync(args) != 0:
            self.log.fatal("Big rsync failed")
            self.pg_stop_backup()
            sys.exit(1)

    def rsync_log_directory(self, source_dir, dst_loc):
        """rsync a pg_log or pg_xlog directory - ignore most of the
        directory contents, and pay attention to symlinks
        """
        keep_symlinks = self.cf.getint("keep_symlinks", 1)

        subdir = os.path.basename(source_dir)
        if not os.path.exists(source_dir):
            self.log.info("%s does not exist, skipping", subdir)
            return

        cmdline = []

        # if this is a symlink, copy it's target first
        if os.path.islink(source_dir) and keep_symlinks:
            self.log.info('%s is a symlink, attempting to create link target', subdir)

            # expand the link
            link = os.readlink(source_dir)
            if not link.startswith("/"):
                link = os.path.join(os.getcwd(), link)
            link_target = os.path.join(link, "")

            slave_host = self.cf.get("slave")
            remote_target = "%s:%s" % (slave_host, link_target)
            options = [ "--include=archive_status", "--exclude=/**" ]
            if self.exec_rsync( options + [ link_target, remote_target ]):
                # unable to create the link target, just convert the links
                # to directories in PGDATA
                self.log.warning('Unable to create symlinked %s on target, copying', subdir)
                cmdline += [ "--copy-unsafe-links" ]

        cmdline += [ "--exclude=pg_log/*" ]
        cmdline += [ "--exclude=pg_xlog/archive_status/*" ]
        cmdline += [ "--include=pg_xlog/archive_status" ]
        cmdline += [ "--exclude=pg_xlog/*" ]

        self.exec_big_rsync(cmdline + [ source_dir, dst_loc ])

    def exec_cmd(self, cmdline, allow_error=False):
        cmd = "' '".join(cmdline)
        self.log.debug("Execute cmd: %r", cmd)
        if self.not_really:
            return

        process = subprocess.Popen(cmdline,stdout=subprocess.PIPE)
        output = process.communicate()
        res = process.returncode

        if res != 0 and not allow_error:
            self.log.fatal("exec failed, res=%d (%r)", res, cmdline)
            sys.exit(1)
        return (res,output[0])

    def exec_system(self, cmdline):
        self.log.debug("Execute cmd: %r", cmdline)
        if self.not_really:
            return 0
        return os.WEXITSTATUS(os.system(cmdline))

    def chdir(self, loc):
        self.log.debug("chdir: %r", loc)
        if self.not_really:
            return
        try:
            os.chdir(loc)
        except os.error:
            self.log.fatal("CHDir failed")
            self.pg_stop_backup()
            sys.exit(1)

    def parse_conninfo(self,conninfo):
        """Extract host,user and port from primary-conninfo"""
        m = re.match("^.*\s*host\s*=\s*([^\s]+)\s*.*$", conninfo)
        if m:
            host = m.group(1)
        else:
            host = 'localhost'
        m =  re.match("^.*\s*user\s*=\s*([^\s]+)\s*.*$", conninfo)
        if m:
            user = m.group(1)
        else:
            user = os.environ['USER']
        m = re.match("^.*\s*port\s*=\s*([^\s]+)\s*.*$", conninfo)
        if m:
            port = m.group(1)
        else:
            port = '5432'

        m = re.match("^.*\s*sslmode\s*=\s*([^\s]+)\s*.*$", conninfo)
        if m:
            sslmode = m.group(1)
        else:
            sslmode = None

        return host,port,user,sslmode


    def get_last_complete(self):
        """Get the name of last xarchived segment."""

        data_dir = self.cf.getfile("master_data")
        fn = os.path.join(data_dir, ".walshipping.last")
        try:
            last = open(fn, "r").read().strip()
            return last
        except:
            self.log.info("Failed to read %s", fn)
            return None

    def set_last_complete(self, last):
        """Set the name of last xarchived segment."""

        data_dir = self.cf.getfile("master_data")
        fn = os.path.join(data_dir, ".walshipping.last")
        fn_tmp = fn + ".new"
        try:
            f = open(fn_tmp, "w")
            f.write(last)
            f.close()
            os.rename(fn_tmp, fn)
        except:
            self.log.fatal("Cannot write to %s", fn)


    def master_stop(self):
        """Deconfigure archiving, attempt to stop syncdaemon"""
        data_dir = self.cf.getfile("master_data")
        restart_cmd = self.cf.getfile("master_restart_cmd", "")

        self.assert_is_master(True)
        self.log.info("Disabling WAL archiving")

        self.master_configure_archiving(False, restart_cmd)

        # if we have a restart command, then use it, otherwise signal
        if restart_cmd:
            self.log.info("Restarting postmaster")
            self.exec_system(restart_cmd)
        else:
            self.log.info("Sending SIGHUP to postmaster")
            self.signal_postmaster(data_dir, signal.SIGHUP)

        # stop any running syncdaemons
        pidfile = self.cf.getfile("pidfile", "")
        if os.path.exists(pidfile):
            self.log.info('Pidfile %s exists, attempting to stop syncdaemon.', pidfile)
            self.exec_cmd([self.script, self.cfgfile, "syncdaemon", "-s"])

        self.log.info("Done")

    def walmgr_cleanup(self):
        """
        Clean up any walmgr files on slave and master.
        """

        if not self.is_master:
            # remove walshipping directory
            dirname = self.cf.getfile("walmgr_data")
            self.log.info("Removing walmgr data directory: %s", dirname)
            if not self.not_really:
                shutil.rmtree(dirname)

            # remove backup 8.3/main.X directories
            backups = glob.glob(self.cf.getfile("slave_data") + ".[0-9]")
            for dirname in backups:
                self.log.info("Removing backup main directory: %s", dirname)
                if not self.not_really:
                    shutil.rmtree(dirname)

            ssh_dir = os.path.expanduser("~/.ssh")
            auth_file = os.path.join(ssh_dir, "authorized_keys")

            if self.options.ssh_remove_key and os.path.isfile(auth_file):
                # remove master key from ssh authorized keys, simple substring match should do
                keys = ""
                for key in open(auth_file):
                    if not self.options.ssh_remove_key in key:
                        keys += key
                    else:
                        self.log.info("Removed %s from %s", self.options.ssh_remove_key, auth_file)

                self.log.info("Overwriting authorized_keys file")

                if not self.not_really:
                    tmpfile = auth_file + ".walmgr.tmp"
                    f = open(tmpfile, "w")
                    f.write(keys)
                    f.close()
                    os.rename(tmpfile, auth_file)
                else:
                    self.log.debug("authorized_keys:\n%s", keys)

            # remove password from .pgpass
            primary_conninfo = self.cf.get("primary_conninfo", "")
            if self.options.remove_password and primary_conninfo and not self.not_really:
                pg = Pgpass('~/.pgpass')
                host, port, user, _ = self.parse_conninfo(primary_conninfo)
                if pg.remove_user(host, port, user):
                    self.log.info("Removing line from .pgpass")
                    pg.write()

        # get rid of the configuration file, both master and slave
        self.log.info("Removing config file: %s", self.cfgfile)
        if not self.not_really:
            os.remove(self.cfgfile)

    def master_synch_standby(self):
        """Manage synchronous_standby_names parameter"""

        if self.options.synchronous_standby_names is None:
            if len(self.args) < 1:
                die(1, "usage: synch-standby SYNCHRONOUS_STANDBY_NAMES")

            names = self.args[0]
            self.assert_is_master(True)
        else:
            # as synchronous_standby_names is available since 9.1
            # we can override DEFAULT_PG_VERSION
            global DEFAULT_PG_VERSION
            DEFAULT_PG_VERSION = "9.1"

            self.guess_locations()
            self.override_cf_option('master_config', self.postgres_conf)
            self.override_cf_option('master_data', self.pgdata)
            self.override_cf_option('master_db', 'dbname=template1')
            names = self.options.synchronous_standby_names

        cf = PostgresConfiguration(self, self.cf.getfile("master_config"))

        # list of slaves
        db = self.get_database("master_db")
        cur = db.cursor()
        cur.execute("select application_name from pg_stat_replication")
        slave_names = [slave[0] for slave in cur.fetchall()]
        self.close_database("master_db")

        if names.strip() == "":
            if not self.not_really:
                cf.set_synchronous_standby_names("")
            return

        if names.strip() == "*":
            if slave_names:
                if not self.not_really:
                    cf.set_synchronous_standby_names(names)
                return
            else:
                die(1,"At least one slave must be available when enabling synchronous mode")

        # ensure that at least one slave is available from new parameter value
        slave_found = None
        for new_synch_slave in re.findall(r"[^\s,]+",names):
            if new_synch_slave not in slave_names:
                self.log.warning("No slave available with name %s", new_synch_slave)
            else:
                slave_found = True
                break

        if not slave_found:
            die(1,"At least one slave must be available from new list when enabling synchronous mode")
        elif not self.not_really:
            cf.set_synchronous_standby_names(names)

    def master_configure_archiving(self, enable_archiving, can_restart):
        """Turn the archiving on or off"""

        cf = PostgresConfiguration(self, self.cf.getfile("master_config"))
        curr_archive_mode = cf.archive_mode()
        curr_wal_level = cf.wal_level()
        need_restart_warning = False

        if enable_archiving:
            # enable archiving
            cf_file = os.path.abspath(self.cf.filename)

            xarchive = "%s %s %s" % (self.script, cf_file, "xarchive %p %f")
            cf_params = { "archive_command": xarchive }

            if curr_archive_mode is not None:
                # archive mode specified in config, turn it on
                self.log.debug("found 'archive_mode' in config -- enabling it")
                cf_params["archive_mode"] = "on"

                if curr_archive_mode.lower() not in ('1', 'on', 'true') and not can_restart:
                    need_restart_warning = True

            if curr_wal_level is not None and curr_wal_level != 'hot_standby':
                # wal level set in config, enable it
                wal_level = self.cf.getboolean("hot_standby", False) and "hot_standby" or "archive"

                self.log.debug("found 'wal_level' in config -- setting to '%s'", wal_level)
                cf_params["wal_level"] = wal_level

                if curr_wal_level not in ("archive", "hot_standby") and not can_restart:
                    need_restart_warning = True

            if need_restart_warning:
                self.log.warning("database must be restarted to enable archiving")

        else:
            # disable archiving
            cf_params = dict()

            if can_restart:
                # can restart, disable archive mode and set wal_level to minimal

                cf_params['archive_command'] = ''

                if curr_archive_mode:
                    cf_params['archive_mode'] = 'off'
                if curr_wal_level:
                    cf_params['wal_level'] = 'minimal'
                    cf_params['max_wal_senders'] = '0'
            else:
                # not possible to change archive_mode or wal_level (requires restart),
                # so we just set the archive_command to /bin/true to avoid WAL pileup.
                self.log.info("database must be restarted to disable archiving")
                self.log.info("Setting archive_command to /bin/true to avoid WAL pileup")

                cf_params['archive_command'] = '/bin/true'

                # disable synchronous standbys, note that presently we don't care
                # if there is more than one standby.
                if cf.synchronous_standby_names():
                    cf_params['synchronous_standby_names'] = ''

        self.log.debug("modifying configuration: %s", cf_params)

        cf.modify(cf_params)
        cf.write()

    def slave_deconfigure_archiving(self, cf_file):
        """Disable archiving for the slave. This is done by setting
        archive_command to a trivial command, so that archiving can be
        re-enabled without restarting postgres. Needed when slave is
        booted with postgresql.conf from master."""

        self.log.debug("Disable archiving in %s", cf_file)

        cf = PostgresConfiguration(self, cf_file)
        cf_params = { "archive_command": "/bin/true" }

        self.log.debug("modifying configuration: %s", cf_params)
        cf.modify(cf_params)
        cf.write()

    def remote_mkdir(self, remdir):
        tmp = remdir.split(":", 1)
        if len(tmp) < 1:
            raise Exception("cannot find pathname")
        elif len(tmp) < 2:
            self.exec_cmd([ "mkdir", "-p", tmp[0] ])
        else:
            host, path = tmp
            cmdline = ["ssh", "-nT", host, "mkdir", "-p", path]
            self.exec_cmd(cmdline)

    def remote_walmgr(self, command, stdin_disabled = True, allow_error=False):
        """Pass a command to slave WalManager"""

        sshopt = "-T"
        if stdin_disabled:
            sshopt += "n"

        slave_config = self.cf.getfile("slave_config")
        if not slave_config:
            raise Exception("slave_config not specified in %s" % self.cfgfile)

        slave_host = self.cf.get("slave")
        cmdline = [ "ssh", sshopt, "-o", "Batchmode=yes", "-o", "StrictHostKeyChecking=no",
                    slave_host, self.script, slave_config, command ]

        if self.not_really:
            cmdline += ["--not-really"]

        return self.exec_cmd(cmdline, allow_error)

    def remote_xlock(self):
        """
        Obtain the backup lock to ensure that several backups are not
        run in parralel. If someone already has the lock we check if
        this is from a previous (failed) backup. If that is the case,
        the lock is released and re-obtained.
        """
        xlock_cmd = "xlock %d" % os.getpid()
        ret = self.remote_walmgr(xlock_cmd, allow_error=True)
        if ret[0] != 0:
            # lock failed.
            try:
                lock_pid = int(ret[1])
            except ValueError:
                self.log.fatal("Invalid pid in backup lock")
                sys.exit(1)

            try:
                os.kill(lock_pid, 0)
                self.log.fatal("Backup lock already taken")
                sys.exit(1)
            except OSError:
                # no process, carry on
                self.remote_walmgr("xrelease")
                self.remote_walmgr(xlock_cmd)

    def override_cf_option(self, option, value):
        """Set a configuration option, if it is unset"""
        if not self.cf.has_option(option):
            self.cf.cf.set('walmgr', option, value)

    def guess_locations(self):
        """
        Guess PGDATA and configuration file locations.
        """

        # find the PGDATA directory
        if self.options.pgdata:
            self.pgdata = self.options.pgdata
        elif 'PGDATA' in os.environ:
            self.pgdata = os.environ['PGDATA']
        else:
            self.pgdata = "~/%s/main" % DEFAULT_PG_VERSION

        self.pgdata = os.path.expanduser(self.pgdata)
        if not os.path.isdir(self.pgdata):
            die(1, 'Postgres data directory not found: %s' % self.pgdata)

        postmaster_opts = os.path.join(self.pgdata, 'postmaster.opts')
        self.postgres_bin = ""
        self.postgres_conf = ""

        if os.path.exists(postmaster_opts):
            # postmaster_opts exists, attempt to guess various paths

            # get unquoted args from opts file
            cmdline = [ k.strip('"') for k in open(postmaster_opts).read().split() ]

            if cmdline:
                self.postgres_bin = os.path.dirname(cmdline[0])
                cmdline = cmdline[1:]

            for item in cmdline:
                if item.startswith("config_file="):
                    self.postgres_conf = item.split("=")[1]

            if not self.postgres_conf:
                self.postgres_conf = os.path.join(self.pgdata, "postgresql.conf")

        else:
            # no postmaster opts, resort to guessing

            self.log.info('postmaster.opts not found, resorting to guesses')

            # use the directory of first postgres executable from path
            for path in os.environ['PATH'].split(os.pathsep):
                path = os.path.expanduser(path)
                exe = os.path.join(path, "postgres")
                if os.path.isfile(exe):
                    self.postgres_bin = path
                    break
            else:
                # not found, use Debian default
                self.postgres_bin = "/usr/lib/postgresql/%s/bin" % DEFAULT_PG_VERSION

            if os.path.exists(self.pgdata):
                self.postgres_conf = os.path.join(self.pgdata, "postgresql.conf")
            else:
                self.postgres_conf = "/etc/postgresql/%s/main/postgresql.conf" % DEFAULT_PG_VERSION

        if not os.path.isdir(self.postgres_bin):
            die(1, "Postgres bin directory not found.")

        if not os.path.isfile(self.postgres_conf):
            if not self.options.init_slave:
                # postgres_conf is required for master
                die(1, "Configuration file not found: %s" % self.postgres_conf)

        # Attempt to guess the init.d script name
        script_suffixes = [ "9.1", "9.0", "8.4", "8.3", "8.2", "8.1", "8.0" ]
        self.initd_script = "/etc/init.d/postgresql"
        if not os.path.exists(self.initd_script):
            for suffix in script_suffixes:
                try_file = "%s-%s" % (self.initd_script, suffix)
                if os.path.exists(try_file):
                    self.initd_script = try_file
                    break
            else:
                self.initd_script = "%s -m fast -D %s" % \
                    (os.path.join(self.postgres_bin, "pg_ctl"), os.path.abspath(self.pgdata))

    def write_walmgr_config(self, config_data):
        cf_name = os.path.join(os.path.expanduser(self.options.config_dir),
                    self.cf.get("job_name") + ".ini")

        dirname = os.path.dirname(cf_name)
        if not os.path.isdir(dirname):
            self.log.info('Creating config directory: %s', dirname)
            os.makedirs(dirname)

        self.log.info('Writing configuration file: %s', cf_name)
        self.log.debug("config data:\n%s", config_data)
        if not self.not_really:
            cf = open(cf_name, "w")
            cf.write(config_data)
            cf.close()

    def walmgr_init_master(self):
        """
        Initialize configuration file, generate SSH key pair if needed.
        """

        self.guess_locations()

        if not self.options.slave:
            die(1, 'Specify slave host name with "--slave" option.')

        self.override_cf_option('master_bin', self.postgres_bin)
        self.override_cf_option('master_config', self.postgres_conf)
        self.override_cf_option('master_data', self.pgdata)

        # assume that slave config is in the same location as master's
        # can override with --set slave_config=
        slave_walmgr_dir = os.path.abspath(os.path.expanduser(self.options.config_dir))
        self.override_cf_option('slave_config', os.path.join(slave_walmgr_dir, "wal-slave.ini"))

        master_config = """[walmgr]
job_name            = %(job_name)s
logfile             = %(logfile)s
pidfile             = %(pidfile)s
use_skylog          = 1

master_db           = %(master_db)s
master_data         = %(master_data)s
master_config       = %(master_config)s
master_bin          = %(master_bin)s

slave               = %(slave)s
slave_config        = %(slave_config)s

walmgr_data         = %(walmgr_data)s
completed_wals      = %(completed_wals)s
partial_wals        = %(partial_wals)s
full_backup         = %(full_backup)s
config_backup       = %(config_backup)s

keep_symlinks       = %(keep_symlinks)s
compression         = %(compression)s
"""

        try:
            opt_dict = dict([(k, self.cf.get(k)) for k in self.cf.options()])
            opt_dict['slave'] = self.options.slave
            master_config = master_config % opt_dict
        except KeyError, e:
            die(1, 'Required setting missing: %s' % e)

        self.write_walmgr_config(master_config)

        # generate SSH key pair if requested
        if self.options.ssh_keygen:
            keyfile = os.path.expanduser("~/.ssh/id_dsa")
            if os.path.isfile(keyfile):
                self.log.info("SSH key %s already exists, skipping", keyfile)
            else:
                self.log.info("Generating ssh key: %s", keyfile)
                cmdline = ["ssh-keygen", "-t", "dsa", "-N", "", "-q", "-f", keyfile ]
                self.log.debug(' '.join(cmdline))
                if not self.not_really:
                    subprocess.call(cmdline)
                key = open(keyfile + ".pub").read().strip()
                self.log.info("public key: %s", key)

    def walmgr_init_slave(self):
        """
        Initialize configuration file, move SSH pubkey into place.
        """
        self.guess_locations()

        self.override_cf_option('slave_bin', self.postgres_bin)
        self.override_cf_option('slave_data', self.pgdata)
        self.override_cf_option('slave_config_dir', os.path.dirname(self.postgres_conf))

        if self.initd_script:
            self.override_cf_option('slave_start_cmd', "%s start" % self.initd_script)
            self.override_cf_option('slave_stop_cmd', "%s stop" % self.initd_script)

        slave_config = """[walmgr]
job_name             = %(job_name)s
logfile              = %(logfile)s
use_skylog           = %(use_skylog)s

slave_data           = %(slave_data)s
slave_bin            = %(slave_bin)s
slave_stop_cmd       = %(slave_stop_cmd)s
slave_start_cmd      = %(slave_start_cmd)s
slave_config_dir     = %(slave_config_dir)s

walmgr_data          = %(walmgr_data)s
completed_wals       = %(completed_wals)s
partial_wals         = %(partial_wals)s
full_backup          = %(full_backup)s
config_backup        = %(config_backup)s
"""

        if self.options.primary_conninfo:
            self.override_cf_option('primary_conninfo', self.options.primary_conninfo)
            slave_config += """
primary_conninfo     = %(primary_conninfo)s
"""

        try:
            opt_dict = dict([(k, self.cf.get(k)) for k in self.cf.options()])
            slave_config = slave_config % opt_dict
        except KeyError, e:
            die(1, 'Required setting missing: %s' % e)

        self.write_walmgr_config(slave_config)

        if self.options.ssh_add_key:
            # add the named public key to authorized hosts
            ssh_dir = os.path.expanduser("~/.ssh")
            auth_file = os.path.join(ssh_dir, "authorized_keys")

            if not os.path.isdir(ssh_dir):
                self.log.info("Creating directory: %s", ssh_dir)
                if not self.not_really:
                    os.mkdir(ssh_dir)

            self.log.debug("Reading public key from %s", self.options.ssh_add_key)
            master_pubkey = open(self.options.ssh_add_key).read()

            key_present = False
            if os.path.isfile(auth_file):
                for key in open(auth_file):
                    if key == master_pubkey:
                        self.log.info("Key already present in %s, skipping", auth_file)
                        key_present = True

            if not key_present:
                self.log.info("Adding %s to %s", self.options.ssh_add_key, auth_file)
                if not self.not_really:
                    af = open(auth_file, "a")
                    af.write(master_pubkey)
                    af.close()

        if self.options.add_password and self.options.primary_conninfo:
            # add password to pgpass

            self.log.debug("Reading password from file %s", self.options.add_password)
            pwd = open(self.options.add_password).readline().rstrip('\n\r')

            pg = Pgpass('~/.pgpass')
            host, port, user, _ = self.parse_conninfo(self.options.primary_conninfo)
            pg.ensure_user(host, port, user, pwd)
            pg.write()

            self.log.info("Added password from %s to .pgpass", self.options.add_password)



    def walmgr_setup(self):
        if self.is_master:
            self.log.info("Configuring WAL archiving")

            data_dir = self.cf.getfile("master_data")
            restart_cmd = self.cf.getfile("master_restart_cmd", "")

            self.master_configure_archiving(True, restart_cmd)

            # if we have a restart command, then use it, otherwise signal
            if restart_cmd:
                self.log.info("Restarting postmaster")
                self.exec_system(restart_cmd)
            else:
                self.log.info("Sending SIGHUP to postmaster")
                self.signal_postmaster(data_dir, signal.SIGHUP)

            # ask slave to init
            self.remote_walmgr("setup")
            self.log.info("Done")
        else:
            # create slave directory structure
            def mkdirs(dir):
                if not os.path.exists(dir):
                    self.log.debug("Creating directory %s", dir)
                    if not self.not_really:
                        os.makedirs(dir)

            mkdirs(self.cf.getfile("completed_wals"))
            mkdirs(self.cf.getfile("partial_wals"))
            mkdirs(self.cf.getfile("full_backup"))

            cf_backup = self.cf.getfile("config_backup", "")
            if cf_backup:
                mkdirs(cf_backup)

    def master_periodic(self):
        """
        Run periodic command on master node.

        We keep time using .walshipping.last file, so this has to be run before
        set_last_complete()
        """

        self.assert_is_master(True)

        try:
            command_interval = self.cf.getint("command_interval", 0)
            periodic_command = self.cf.get("periodic_command", "")

            if periodic_command:
                check_file = os.path.join(self.cf.getfile("master_data"), ".walshipping.periodic")

                elapsed = 0
                if os.path.isfile(check_file):
                    elapsed = time.time() - os.stat(check_file).st_mtime

                self.log.info("Running periodic command: %s", periodic_command)
                if not elapsed or elapsed > command_interval:
                    if not self.not_really:
                        rc = os.WEXITSTATUS(self.exec_system(periodic_command))
                        if rc != 0:
                            self.log.error("Periodic command exited with status %d", rc)
                            # dont update timestamp - try again next time
                        else:
                            open(check_file,"w").write("1")
                else:
                    self.log.debug("%d seconds elapsed, not enough to run periodic.", elapsed)
        except Exception, det:
            self.log.error("Failed to run periodic command: %s", det)

    def master_backup(self):
        """
        Copy master data directory to slave.

        1. Obtain backup lock on slave.
        2. Rotate backups on slave
        3. Perform backup as usual
        4. Purge unneeded WAL-s from slave
        5. Release backup lock
        """

        self.remote_xlock()
        errors = False

        try:
            self.pg_start_backup("FullBackup")
            self.remote_walmgr("xrotate")

            data_dir = self.cf.getfile("master_data")
            dst_loc = self.cf.getfile("full_backup")
            if dst_loc[-1] != "/":
                dst_loc += "/"

            master_spc_dir = os.path.join(data_dir, "pg_tblspc")
            slave_spc_dir = dst_loc + "tmpspc"

            # copy data
            self.chdir(data_dir)
            cmdline = [
                    "--delete",
                    "--exclude", ".*",
                    "--exclude", "*.pid",
                    "--exclude", "*.opts",
                    "--exclude", "*.conf",
                    "--exclude", "pg_xlog",
                    "--exclude", "pg_tblspc",
                    "--exclude", "pg_log",
                    "--exclude", "base/pgsql_tmp",
                    "--copy-unsafe-links",
                    ".", dst_loc]
            self.exec_big_rsync(cmdline)

            # copy tblspc first, to test
            if os.path.isdir(master_spc_dir):
                self.log.info("Checking tablespaces")
                list = os.listdir(master_spc_dir)
                if len(list) > 0:
                    self.remote_mkdir(slave_spc_dir)
                for tblspc in list:
                    if tblspc[0] == ".":
                        continue
                    tfn = os.path.join(master_spc_dir, tblspc)
                    if not os.path.islink(tfn):
                        self.log.info("Suspicious pg_tblspc entry: %s", tblspc)
                        continue
                    spc_path = os.path.realpath(tfn)
                    self.log.info("Got tablespace %s: %s", tblspc, spc_path)
                    dstfn = slave_spc_dir + "/" + tblspc

                    try:
                        os.chdir(spc_path)
                    except Exception, det:
                        self.log.warning("Broken link: %s", det)
                        continue
                    cmdline = [ "--delete", "--exclude", ".*", "--copy-unsafe-links", ".", dstfn]
                    self.exec_big_rsync(cmdline)

            # copy the pg_log and pg_xlog directories, these may be
            # symlinked to nonstandard location, so pay attention
            self.rsync_log_directory(os.path.join(data_dir, "pg_log"),  dst_loc)
            self.rsync_log_directory(os.path.join(data_dir, "pg_xlog"), dst_loc)

            # copy config files
            conf_dst_loc = self.cf.getfile("config_backup", "")
            if conf_dst_loc:
                master_conf_dir = os.path.dirname(self.cf.getfile("master_config"))
                self.log.info("Backup conf files from %s", master_conf_dir)
                self.chdir(master_conf_dir)
                cmdline = [
                     "--include", "*.conf",
                     "--exclude", "*",
                     ".", conf_dst_loc]
                self.exec_big_rsync(cmdline)

            self.remote_walmgr("xpurgewals")
        except Exception, e:
            self.log.error(e)
            errors = True
        finally:
            try:
                self.pg_stop_backup()
            except:
                pass

        try:
            self.remote_walmgr("xrelease")
        except:
            pass

        if not errors:
            self.log.info("Full backup successful")
        else:
            self.log.error("Full backup failed.")

    def slave_backup(self):
        """
        Create backup on slave host.

        1. Obtain backup lock
        2. Pause WAL apply
        3. Wait for WAL apply to complete (look at PROGRESS file)
        4. Rotate old backups
        5. Copy data directory to data.master
        6. Create backup label and history file.
        7. Purge unneeded WAL-s
        8. Resume WAL apply
        9. Release backup lock
        """
        self.assert_is_master(False)
        if self.slave_lock_backups() != 0:
            self.log.error("Cannot obtain backup lock.")
            sys.exit(1)

        try:
            self.slave_pause(waitcomplete=1)

            try:
                self.slave_rotate_backups()
                src = self.cf.getfile("slave_data")
                dst = self.cf.getfile("full_backup")

                start_time = time.localtime()
                cmdline = ["cp", "-a", src, dst ]
                self.log.info("Executing %s", " ".join(cmdline))
                if not self.not_really:
                    self.exec_cmd(cmdline)
                stop_time = time.localtime()

                # Obtain the last restart point information
                ctl = PgControlData(self.cf.getfile("slave_bin", ""), dst, True)

                # TODO: The newly created backup directory probably still contains
                # backup_label.old and recovery.conf files. Remove these.

                if not ctl.is_valid:
                    self.log.warning("Unable to determine last restart point, backup_label not created.")
                else:
                    # Write backup label and history file

                    backup_label = \
"""START WAL LOCATION: %(xlogid)X/%(xrecoff)X (file %(wal_name)s)
CHECKPOINT LOCATION: %(xlogid)X/%(xrecoff)X
START TIME: %(start_time)s
LABEL: SlaveBackup"
"""
                    backup_history = \
"""START WAL LOCATION: %(xlogid)X/%(xrecoff)X (file %(wal_name)s)
STOP WAL LOCATION: %(xlogid)X/%(xrecoff)X (file %(wal_name)s)
CHECKPOINT LOCATION: %(xlogid)X/%(xrecoff)X
START TIME: %(start_time)s
LABEL: SlaveBackup"
STOP TIME: %(stop_time)s
"""

                    label_params = {
                        "xlogid":       ctl.xlogid,
                        "xrecoff":      ctl.xrecoff,
                        "wal_name":     ctl.wal_name,
                        "start_time":   time.strftime("%Y-%m-%d %H:%M:%S %Z", start_time),
                        "stop_time":    time.strftime("%Y-%m-%d %H:%M:%S %Z", stop_time),
                    }

                    # Write the label
                    filename = os.path.join(dst, "backup_label")
                    if self.not_really:
                        self.log.info("Writing backup label to %s", filename)
                    else:
                        lf = open(filename, "w")
                        lf.write(backup_label % label_params)
                        lf.close()

                    # Now the history
                    histfile = "%s.%08X.backup" % (ctl.wal_name, ctl.xrecoff % ctl.wal_size)
                    completed_wals = self.cf.getfile("completed_wals")
                    filename = os.path.join(completed_wals, histfile)
                    if os.path.exists(filename):
                        self.log.warning("%s: already exists, refusing to overwrite.", filename)
                    else:
                        if self.not_really:
                            self.log.info("Writing backup history to %s", filename)
                        else:
                            lf = open(filename, "w")
                            lf.write(backup_history % label_params)
                            lf.close()

                self.slave_purge_wals()
            finally:
                self.slave_continue()
        finally:
            self.slave_resume_backups()

    def run_backup(self):
        if self.is_master:
            self.master_backup()
        else:
            self.slave_backup()

    def master_xarchive(self):
        """Copy a complete WAL segment to slave."""

        self.assert_is_master(True)

        if len(self.args) < 2:
            die(1, "usage: xarchive srcpath srcname")
        srcpath = self.args[0]
        srcname = self.args[1]

        start_time = time.time()
        self.log.debug("%s: start copy", srcname)

        self.master_periodic()

        dst_loc = self.cf.getfile("completed_wals")
        if dst_loc[-1] != "/":
            dst_loc += "/"

        # copy data
        self.exec_rsync([ srcpath, dst_loc ], True)

        # sync the buffers to disk - this is should reduce the chance
        # of WAL file corruption in case the slave crashes.
        slave = self.cf.get("slave")
        cmdline = ["ssh", "-nT", slave, "sync" ]
        self.exec_cmd(cmdline)

        # slave has the file now, set markers
        self.set_last_complete(srcname)

        self.log.debug("%s: done", srcname)
        end_time = time.time()
        self.stat_add('count', 1)
        self.stat_add('duration', end_time - start_time)
        self.send_stats()

    def slave_append_partial(self):
        """
        Read 'bytes' worth of data from stdin, append to the partial log file
        starting from 'offset'. On error it is assumed that master restarts
        from zero.

        The resulting file is always padded to XLOG_SEGMENT_SIZE bytes to
        simplify recovery.
        """

        def fail(message):
            self.log.error("Slave: %s: %s", filename, message)
            sys.exit(1)

        self.assert_is_master(False)
        if len(self.args) < 3:
            die(1, "usage: xpartialsync <filename> <offset> <bytes>")

        filename = self.args[0]
        offset = int(self.args[1])
        bytes = int(self.args[2])

        data = sys.stdin.read(bytes)
        if len(data) != bytes:
            fail("not enough data, expected %d, got %d" % (bytes, len(data)))

        chunk = WalChunk(filename, offset, bytes)
        self.log.debug("Slave: adding to %s", chunk)

        name = os.path.join(self.cf.getfile("partial_wals"), filename)

        if self.not_really:
            self.log.info("Adding to partial: %s", name)
            return

        try:
            xlog = open(name, (offset == 0) and "w+" or "r+")
        except:
            fail("unable to open partial WAL: %s" % name)
        xlog.seek(offset)
        xlog.write(data)

        # padd the file to 16MB boundary, use sparse files
        padsize = XLOG_SEGMENT_SIZE - xlog.tell()
        if padsize > 0:
            xlog.seek(XLOG_SEGMENT_SIZE-1)
            xlog.write('\0')

        xlog.close()

    def master_send_partial(self, xlog_dir, chunk, daemon_mode):
        """
        Send the partial log chunk to slave. Use SSH with input redirection for the copy,
        consider other options if the overhead becomes visible.
        """

        try:
            xlog = open(os.path.join(xlog_dir, chunk.filename))
        except IOError, det:
            self.log.warning("Cannot access file %s", chunk.filename)
            return

        xlog.seek(chunk.pos)

        # Fork the sync process
        childpid = os.fork()
        syncstart = time.time()
        if childpid == 0:
            os.dup2(xlog.fileno(), sys.stdin.fileno())
            try:
                self.remote_walmgr("xpartialsync %s %d %d" % (chunk.filename, chunk.pos, chunk.bytes), False)
            except:
                os._exit(1)
            os._exit(0)
        chunk.sync_time += (time.time() - syncstart)

        status = os.waitpid(childpid, 0)
        rc = os.WEXITSTATUS(status[1])
        if rc == 0:
            log = daemon_mode and self.log.debug or self.log.info
            log("sent to slave: %s" % chunk)
            chunk.pos += chunk.bytes
            chunk.sync_count += 1
        else:
            # Start from zero after an error
            chunk.pos = 0
            self.log.error("xpartialsync exited with status %d, restarting from zero.", rc)
            time.sleep(5)

    def master_syncdaemon(self):
        self.assert_is_master(True)
        self.set_single_loop(0)
        self.master_sync(True)

    def master_sync(self, daemon_mode=False):
        """
        Copy partial WAL segments to slave.

        On 8.2 set use_xlog_functions=1 in config file - this enables record based
        walshipping. On 8.0 the only option is to sync files.

        If daemon_mode is specified it never switches from record based shipping to
        file based shipping.
        """

        self.assert_is_master(True)

        use_xlog_functions = self.cf.getint("use_xlog_functions", False)
        data_dir = self.cf.getfile("master_data")
        xlog_dir = os.path.join(data_dir, "pg_xlog")
        master_bin = self.cf.getfile("master_bin", "")

        dst_loc = os.path.join(self.cf.getfile("partial_wals"), "")

        db = None
        if use_xlog_functions:
            try:
                db = self.get_database("master_db", autocommit=1)
            except:
                self.log.warning("Database unavailable, record based log shipping not possible.")
                if daemon_mode:
                    return

        if db:
            cur = db.cursor()
            cur.execute("select file_name, file_offset from pg_xlogfile_name_offset(pg_current_xlog_location())")
            (file_name, file_offs) = cur.fetchone()

            if not self.walchunk or self.walchunk.filename != file_name:
                # Switched to new WAL segment. Don't bother to copy the last bits - it
                # will be obsoleted by the archive_command.
                if self.walchunk and self.walchunk.sync_count > 0:
                    self.log.info("Switched in %d seconds, %f sec in %d interim syncs, avg %f",
                            time.time() - self.walchunk.start_time,
                            self.walchunk.sync_time,
                            self.walchunk.sync_count,
                            self.walchunk.sync_time / self.walchunk.sync_count)
                self.walchunk = WalChunk(file_name, 0, file_offs)
            else:
                self.walchunk.bytes = file_offs - self.walchunk.pos

            if self.walchunk.bytes > 0:
                self.master_send_partial(xlog_dir, self.walchunk, daemon_mode)
        else:
            files = os.listdir(xlog_dir)
            files.sort()

            last = self.get_last_complete()
            if last:
                self.log.info("%s: last complete", last)
            else:
                self.log.info("last complete not found, copying all")

            # obtain the last checkpoint wal name, this can be used for
            # limiting the amount of WAL files to copy if the database
            # has been cleanly shut down
            ctl = PgControlData(master_bin, data_dir, False)
            checkpoint_wal = None
            if ctl.is_valid:
                if not ctl.is_shutdown:
                    # cannot rely on the checkpoint wal, should use some other method
                    self.log.info("Database state is not 'shut down', copying all")
                else:
                    # ok, the database is shut down, we can use last checkpoint wal
                    checkpoint_wal = ctl.wal_name
                    self.log.info("last checkpoint wal: %s", checkpoint_wal)
            else:
                self.log.info("Unable to obtain control file information, copying all")

            for fn in files:
                # check if interesting file
                if len(fn) < 10:
                    continue
                if fn[0] < "0" or fn[0] > '9':
                    continue
                if fn.find(".") > 0:
                    continue
                # check if too old
                if last:
                    dot = last.find(".")
                    if dot > 0:
                        xlast = last[:dot]
                        if fn < xlast:
                            continue
                    else:
                        if fn <= last:
                            continue
                # check if too new
                if checkpoint_wal and fn > checkpoint_wal:
                    continue

                # got interesting WAL
                xlog = os.path.join(xlog_dir, fn)
                # copy data
                self.log.info('Syncing %s', xlog)
                if self.exec_rsync([xlog, dst_loc], not daemon_mode) != 0:
                    self.log.error('Cannot sync %s', xlog)
                    break
            else:
                self.log.info("Partial copy done")

    def xrestore(self):
        if len(self.args) < 2:
            die(1, "usage: xrestore srcname dstpath [last restartpoint wal]")
        srcname = self.args[0]
        dstpath = self.args[1]
        lstname = None
        if len(self.args) > 2:
            lstname = self.args[2]
        if self.is_master:
            self.master_xrestore(srcname, dstpath)
        else:
            self.slave_xrestore_unsafe(srcname, dstpath, os.getppid(), lstname)

    def slave_xrestore(self, srcname, dstpath):
        loop = 1
        ppid = os.getppid()
        while loop:
            try:
                self.slave_xrestore_unsafe(srcname, dstpath, ppid)
                loop = 0
            except SystemExit, d:
                sys.exit(1)
            except Exception, d:
                exc, msg, tb = sys.exc_info()
                self.log.fatal("xrestore %s crashed: %s: '%s' (%s: %r)",
                        srcname, exc, str(msg).rstrip(),
                        tb, traceback.format_tb(tb))
                del tb
                time.sleep(10)
                self.log.info("Re-exec: %r", sys.argv)
                os.execv(sys.argv[0], sys.argv)

    def master_xrestore(self, srcname, dstpath):
        """
        Restore the xlog file from slave.
        """
        paths = [ self.cf.getfile("completed_wals"), self.cf.getfile("partial_wals") ]

        self.log.info("Restore %s to %s", srcname, dstpath)
        for src in paths:
            self.log.debug("Looking in %s", src)
            srcfile = os.path.join(src, srcname)
            if self.exec_rsync([srcfile, dstpath]) == 0:
                return
        self.log.warning("Could not restore file %s", srcname)

    def is_parent_alive(self, parent_pid):
        if os.getppid() != parent_pid or parent_pid <= 1:
            return False
        return True

    def slave_xrestore_unsafe(self, srcname, dstpath, parent_pid, lstname = None):
        srcdir = self.cf.getfile("completed_wals")
        partdir = self.cf.getfile("partial_wals")
        pausefile = os.path.join(srcdir, "PAUSE")
        stopfile = os.path.join(srcdir, "STOP")
        prgrfile = os.path.join(srcdir, "PROGRESS")
        prxlogfile = os.path.join(srcdir,"PG_RECEIVEXLOG")
        srcfile = os.path.join(srcdir, srcname)
        partfile = os.path.join(partdir, srcname)

        # if we are using streaming replication, exit immediately
        # if the srcfile is not here yet
        primary_conninfo = self.cf.get("primary_conninfo", "")
        if primary_conninfo and not os.path.isfile(srcfile):
            self.log.info("%s: not found (ignored)", srcname)

            # remove PG_RECEIVEXLOG file if it's present
            if os.path.isfile(prxlogfile):
                os.remove(prxlogfile)

            sys.exit(1)

        # assume that postgres has processed the WAL file and is
        # asking for next - hence work not in progress anymore
        if os.path.isfile(prgrfile):
            os.remove(prgrfile)

        # loop until srcfile or stopfile appears
        while 1:
            if os.path.isfile(pausefile):
                self.log.info("pause requested, sleeping")
                time.sleep(20)
                continue

            if os.path.isfile(srcfile):
                self.log.info("%s: Found", srcname)
                break

            # ignore .history files
            unused, ext = os.path.splitext(srcname)
            if ext == ".history":
                self.log.info("%s: not found, ignoring", srcname)
                sys.exit(1)

            # if stopping, include also partial wals
            if os.path.isfile(stopfile):
                if os.path.isfile(partfile):
                    self.log.info("%s: found partial", srcname)
                    srcfile = partfile
                    break
                else:
                    self.log.info("%s: not found, stopping", srcname)
                    sys.exit(1)

            # nothing to do, just in case check if parent is alive
            if not self.is_parent_alive(parent_pid):
                self.log.warning("Parent dead, quitting")
                sys.exit(1)

            # nothing to do, sleep
            self.log.debug("%s: not found, sleeping", srcname)
            time.sleep(1)

        # got one, copy it
        cmdline = ["cp", srcfile, dstpath]
        self.exec_cmd(cmdline)

        if self.cf.getint("keep_backups", 0) == 0:
            # cleanup only if we don't keep backup history, keep the files needed
            # to roll forward from last restart point. If the restart point is not
            # handed to us (i.e 8.3 or later), then calculate it ourselves.
            # Note that historic WAL files are removed during backup rotation
            if lstname == None:
                lstname = self.last_restart_point(srcname)
                self.log.debug("calculated restart point: %s", lstname)
            else:
                self.log.debug("using supplied restart point: %s", lstname)
            self.log.debug("%s: copy done, cleanup", srcname)
            self.slave_cleanup(lstname)

        # create a PROGRESS file to notify that postgres is processing the WAL
        open(prgrfile, "w").write("1")

        # it would be nice to have apply time too
        self.stat_add('count', 1)
        self.send_stats()

    def restore_database(self, restore_config=True):
        """Restore the database from backup

        If setname is specified, the contents of that backup set directory are
        restored instead of "full_backup". Also copy is used instead of rename to
        restore the directory (unless a pg_xlog directory has been specified).

        Restore to altdst if specified. Complain if it exists.
        """

        setname = len(self.args) > 0 and self.args[0] or None
        altdst  = len(self.args) > 1 and self.args[1] or None

        if not self.is_master:
            data_dir = self.cf.getfile("slave_data")
            stop_cmd = self.cf.getfile("slave_stop_cmd", "")
            start_cmd = self.cf.getfile("slave_start_cmd")
            pidfile = os.path.join(data_dir, "postmaster.pid")
        else:
            if not setname or not altdst:
                die(1, "Source and target directories must be specified if running on master node.")
            data_dir = altdst
            stop_cmd = None
            pidfile = None

        if setname:
            full_dir = os.path.join(self.cf.getfile("walmgr_data"), setname)
        else:
            full_dir = self.cf.getfile("full_backup")

        # stop postmaster if ordered
        if stop_cmd and os.path.isfile(pidfile):
            self.log.info("Stopping postmaster: %s", stop_cmd)
            self.exec_system(stop_cmd)
            time.sleep(3)

        # is it dead?
        if pidfile and os.path.isfile(pidfile):
            self.log.info("Pidfile exists, checking if process is running.")
            if self.signal_postmaster(data_dir, 0):
                self.log.fatal("Postmaster still running.  Cannot continue.")
                sys.exit(1)

        # find name for data backup
        i = 0
        while 1:
            bak = "%s.%d" % (data_dir.rstrip("/"), i)
            if not os.path.isdir(bak):
                break
            i += 1

        if self.is_master:
            print >>sys.stderr, "About to restore to directory %s. The postgres cluster should be shut down." % data_dir
            if not yesno("Is postgres shut down on %s ?" % data_dir):
                die(1, "Shut it down and try again.")

        if not self.is_master:
            createbackup = True
        elif os.path.isdir(data_dir):
            createbackup = yesno("Create backup of %s?" % data_dir)
        else:
            # nothing to back up
            createbackup = False

        # see if we have to make a backup of the data directory
        backup_datadir = self.cf.getboolean('backup_datadir', True)

        if os.path.isdir(data_dir) and not backup_datadir:
            self.log.warning('backup_datadir is disabled, deleting old data dir')
            shutil.rmtree(data_dir)

        if not setname and os.path.isdir(data_dir) and backup_datadir:
            # compatibility mode - restore without a set name and data directory exists
            self.log.info("Data directory already exists, moving it out of the way.")
            createbackup = True

        # move old data away
        if createbackup and os.path.isdir(data_dir):
            self.log.info("Move %s to %s", data_dir, bak)
            if not self.not_really:
                os.rename(data_dir, bak)

        # move new data, copy if setname specified
        self.log.info("%s %s to %s", setname and "Copy" or "Move", full_dir, data_dir)

        if self.cf.getfile('slave_pg_xlog', ''):
            link_xlog_dir = True
            exclude_pg_xlog = '--exclude=pg_xlog'
        else:
            link_xlog_dir = False
            exclude_pg_xlog = ''

        if not self.not_really:
            if not setname and not link_xlog_dir:
                os.rename(full_dir, data_dir)
            else:
                rsync_args=["--delete", "--no-relative", "--exclude=pg_xlog/*"]
                if exclude_pg_xlog:
                    rsync_args.append(exclude_pg_xlog)
                rsync_args += [os.path.join(full_dir, ""), data_dir]

                self.exec_rsync(rsync_args, True)

                if link_xlog_dir:
                   os.symlink(self.cf.getfile('slave_pg_xlog'), "%s/pg_xlog" % data_dir)

                if (self.is_master and createbackup and os.path.isdir(bak)):
                    # restore original xlog files to data_dir/pg_xlog
                    # symlinked directories are dereferenced
                    self.exec_cmd(["cp", "-rL", "%s/pg_xlog/" % full_dir, "%s/pg_xlog" % data_dir ])
                else:
                    # create an archive_status directory
                    xlog_dir = os.path.join(data_dir, "pg_xlog")
                    archive_path = os.path.join(xlog_dir, "archive_status")
                    if not os.path.exists(archive_path):
                        os.mkdir(archive_path, 0700)
        else:
            data_dir = full_dir

        # copy configuration files to rotated backup directory
        if createbackup and os.path.isdir(bak):
            for cf in ('postgresql.conf', 'pg_hba.conf', 'pg_ident.conf'):
                cfsrc = os.path.join(bak, cf)
                cfdst = os.path.join(data_dir, cf)
                if os.path.exists(cfdst):
                    self.log.info("Already exists: %s", cfdst)
                elif os.path.exists(cfsrc):
                    self.log.debug("Copy %s to %s", cfsrc, cfdst)
                    if not self.not_really:
                        copy_conf(cfsrc, cfdst)

        # re-link tablespaces
        spc_dir = os.path.join(data_dir, "pg_tblspc")
        tmp_dir = os.path.join(data_dir, "tmpspc")
        if not os.path.isdir(spc_dir):
            # 8.3 requires its existence
            os.mkdir(spc_dir)
        if os.path.isdir(tmp_dir):
            self.log.info("Linking tablespaces to temporary location")

            # don't look into spc_dir, thus allowing
            # user to move them before.  re-link only those
            # that are still in tmp_dir
            list = os.listdir(tmp_dir)
            list.sort()

            for d in list:
                if d[0] == ".":
                    continue
                link_loc = os.path.abspath(os.path.join(spc_dir, d))
                link_dst = os.path.abspath(os.path.join(tmp_dir, d))
                self.log.info("Linking tablespace %s to %s", d, link_dst)
                if not self.not_really:
                    if os.path.islink(link_loc):
                        os.remove(link_loc)
                    os.symlink(link_dst, link_loc)


        # write recovery.conf
        rconf = os.path.join(data_dir, "recovery.conf")
        cf_file = os.path.abspath(self.cf.filename)

        # determine if we can use %r in restore_command
        ctl = PgControlData(self.cf.getfile("slave_bin", ""), data_dir, True)
        if ctl.pg_version > 830:
            self.log.debug('pg_version is %s, adding %%r to restore command', ctl.pg_version)
            restore_command = 'xrestore %f "%p" %r'
        else:
            if not ctl.is_valid:
                self.log.warning('unable to run pg_controldata, assuming pre 8.3 environment')
            else:
                self.log.debug('using pg_controldata to determine restart points')
            restore_command = 'xrestore %f "%p"'

        conf = "restore_command = '%s %s %s'\n" % (self.script, cf_file, restore_command)

        # do we have streaming replication (hot standby)
        primary_conninfo = self.cf.get("primary_conninfo", "")
        if primary_conninfo:
            conf += "standby_mode = 'on'\n"
            conf += "trigger_file = '%s'\n" % os.path.join(self.cf.getfile("completed_wals"), "STOP")
            conf += "primary_conninfo = '%s'\n" % primary_conninfo
            conf += "archive_cleanup_command = '%s %s %%r'\n" % \
                (os.path.join(self.cf.getfile("slave_bin"), "pg_archivecleanup"),
                self.cf.getfile("completed_wals"))

        self.log.info("Write %s", rconf)
        if self.not_really:
            print conf
        else:
            f = open(rconf, "w")
            f.write(conf)
            f.close()

        # remove stopfile on slave
        if not self.is_master:
            stopfile = os.path.join(self.cf.getfile("completed_wals"), "STOP")
            if os.path.isfile(stopfile):
                self.log.info("Removing stopfile: %s", stopfile)
                if not self.not_really:
                    os.remove(stopfile)

            # attempt to restore configuration. Note that we cannot
            # postpone this to boot time, as the configuration is needed
            # to start postmaster.
            if restore_config:
                self.slave_restore_config()

            # run database in recovery mode
            self.log.info("Starting postmaster: %s", start_cmd)
            self.exec_system(start_cmd)
        else:
            self.log.info("Data files restored, recovery.conf created.")
            self.log.info("postgresql.conf and additional WAL files may need to be restored manually.")

    def slave_restore_config(self):
        """Restore the configuration files if target directory specified."""
        self.assert_is_master(False)

        cf_source_dir = self.cf.getfile("config_backup", "")
        cf_target_dir = self.cf.getfile("slave_config_dir", "")

        if not cf_source_dir:
            self.log.info("Configuration backup location not specified.")
            return

        if not cf_target_dir:
            self.log.info("Configuration directory not specified, config files not restored.")
            return

        if not os.path.exists(cf_target_dir):
            self.log.warning("Configuration directory does not exist: %s", cf_target_dir)
            return

        self.log.info("Restoring configuration files")
        for cf in ('postgresql.conf', 'pg_hba.conf', 'pg_ident.conf'):
            cfsrc = os.path.join(cf_source_dir, cf)
            cfdst = os.path.join(cf_target_dir, cf)

            if not os.path.isfile(cfsrc):
                self.log.warning("Missing configuration file backup: %s", cf)
                continue

            self.log.debug("Copy %s to %s", cfsrc, cfdst)
            if not self.not_really:
                copy_conf(cfsrc, cfdst)
                if cf == 'postgresql.conf':
                    self.slave_deconfigure_archiving(cfdst)

    def slave_boot(self):
        self.assert_is_master(False)

        srcdir = self.cf.getfile("completed_wals")
        datadir = self.cf.getfile("slave_data")
        stopfile = os.path.join(srcdir, "STOP")

        if self.not_really:
            self.log.info("Writing STOP file: %s", stopfile)
        else:
            open(stopfile, "w").write("1")
        self.log.info("Stopping recovery mode")

    def slave_createslave(self):
        self.assert_is_master(False)

        errors = False
        xlog_dir = self.cf.getfile("completed_wals")
        full_dir = self.cf.getfile("full_backup")
        prxloglock = os.path.join(xlog_dir,"PG_RECEIVEXLOG")
        pg_receivexlog = os.path.join(self.cf.getfile("slave_bin"), "pg_receivexlog")
        pg_basebackup = os.path.join(self.cf.getfile("slave_bin"), "pg_basebackup")

        # check if pg_receivexlog is available
        if not os.access(pg_receivexlog, os.X_OK):
            die(1, "pg_receivexlog not available")

        # check if pg_receivexlog is already running
        if os.path.isfile(prxloglock):
            pidstring = open(prxloglock,"r").read()
            try:
                pid =int(pidstring)
                try:
                    os.kill(pid, 0)
                except OSError, e:
                    if e.errno == errno.EPERM:
                        self.log.fatal("Found pg_receivexlog lock file %s, pid %d in use", prxloglock, pid)
                        sys.exit(1)
                    elif e.errno == errno.ESRCH:
                        self.log.info("Ignoring stale pg_receivexlog lock file")
                        if not self.not_really:
                            os.remove(prxloglock)
                else:
                    self.log.fatal("pg_receivexlog is already running in %s, pid %d", xlog_dir, pid)
                    sys.exit(1)
            except ValueError:
                self.log.fatal("pg_receivexlog lock file %s does not contain a pid: %s", prxloglock, pidstring) 
                sys.exit(1)

        # create directories
        self.walmgr_setup()

        # ensure that backup destination is 0700
        if not self.not_really:
            os.chmod(full_dir,0700)

        self.args = [str(os.getpid())]
        if self.slave_lock_backups() != 0:
            self.log.fatal("Cannot obtain backup lock.")
            sys.exit(1)

        # get host and user from primary_conninfo
        primary_conninfo = self.cf.get("primary_conninfo", "")
        if not primary_conninfo:
            die(1, "primary_conninfo missing")
        host, port, user, sslmode = self.parse_conninfo(primary_conninfo)

        # change sslmode for pg_receivexlog and pg_basebackup
        envssl=None
        if sslmode:
            envssl={"PGSSLMODE": sslmode}

        try:
            # determine postgres version, we cannot use pg_control version number since
            # 9.0 and 9.1 are using the same number in controlfile
            pg_ver = ""
            try:
                cmdline = [os.path.join(self.cf.getfile("slave_bin"), "postgres"),'-V']
                process = subprocess.Popen(cmdline, stdout=subprocess.PIPE)
                output = process.communicate()
                pg_ver = output[0].split()[2]
                self.log.debug("PostgreSQL version: %s" % pg_ver)
            except:
                pass

            # create pg_receivexlog process
            cmdline = [pg_receivexlog,'-D', xlog_dir, '-h', host, '-U', user, '-p', port, '-w']
            self.log.info("Starting pg_receivexlog")

            if not self.not_really:
                p_rxlog = subprocess.Popen(cmdline,env=envssl)

                # create pg_receivexlog lock file
                open(prxloglock, "w").write(str(p_rxlog.pid))

            # leave error checking for pg_basebackup
            # if pg_basebackup command fails then pg_receivexlog is not working either

            # start backup
            self.log.info("Starting pg_basebackup")
            cmdline = [pg_basebackup, '-D', full_dir, '-h', host, '-U', user, '-p', port, '-w']
            if not self.not_really:
                p_basebackup = subprocess.Popen(cmdline, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=envssl)
                output = p_basebackup.communicate()
                res = p_basebackup.returncode

                if res != 0:
                    raise Exception("exec failed, res=%d (%r), %s" % (res, cmdline, output[1]))

                # fix skipped ssl symlinks (only relevant for 9.1)
                if pg_ver.startswith('9.1.'):
                    for line in output[1].splitlines():
                        m = re.match('WARNING:  skipping special file "\./server\.(crt|key)"', line)
                        if m:
                            # create symlinks
                            if m.group(1) == 'crt':
                                os.symlink('/etc/ssl/certs/ssl-cert-snakeoil.pem',
                                        os.path.join(full_dir,'server.crt'))
                            elif m.group(1) == 'key':
                                os.symlink('/etc/ssl/private/ssl-cert-snakeoil.key',
                                        os.path.join(full_dir,'server.key'))

            self.log.info("pg_basebackup finished successfully")

            # restore
            self.args = []
            self.restore_database(False)

            # wait for recovery
            while os.path.isfile(prxloglock) and not self.not_really:
                time.sleep(5)

        except Exception, e:
            self.log.error(e)
            errors = True

        finally:
            # stop pg_receivexlog
            try:
                if not self.not_really:
                    os.kill(p_rxlog.pid, signal.SIGTERM)
                self.log.info("pg_receivelog stopped")
            except Exception, det:
                self.log.warning("Failed to stop pg_receivexlog: %s", det)

            # cleanup
            if os.path.isfile(prxloglock):
                os.remove(prxloglock)

            if not self.not_really:
                for f in os.listdir(xlog_dir):
                    if f.endswith('.partial'):
                        self.log.debug("Removing %s", os.path.join(xlog_dir,f))
                        os.remove(os.path.join(xlog_dir,f))

            if not self.not_really and os.path.isdir(full_dir):
                shutil.rmtree(full_dir)

            self.slave_resume_backups()

        if not errors:
            self.log.info("Streaming replication standby created successfully")
        else:
            self.log.error("Failed to create streaming replication standby")
            sys.exit(1)


    def slave_pause(self, waitcomplete=0):
        """Pause the WAL apply, wait until last file applied if needed"""
        self.assert_is_master(False)
        srcdir = self.cf.getfile("completed_wals")
        pausefile = os.path.join(srcdir, "PAUSE")
        if not self.not_really:
            open(pausefile, "w").write("1")
        else:
            self.log.info("Writing PAUSE file: %s", pausefile)
        self.log.info("Pausing recovery mode")

        # wait for log apply to complete
        if waitcomplete:
            prgrfile = os.path.join(srcdir, "PROGRESS")
            stopfile = os.path.join(srcdir, "STOP")
            if os.path.isfile(stopfile):
                self.log.warning("Recovery is stopped, backup is invalid if the database is open.")
                return
            while os.path.isfile(prgrfile):
                self.log.info("Waiting for WAL processing to complete ...")
                if self.not_really:
                    return
                time.sleep(1)

    def slave_continue(self):
        self.assert_is_master(False)
        srcdir = self.cf.getfile("completed_wals")
        pausefile = os.path.join(srcdir, "PAUSE")
        if os.path.isfile(pausefile):
            if not self.not_really:
                os.remove(pausefile)
            self.log.info("Continuing with recovery")
        else:
            self.log.info("Recovery not paused?")

    def slave_lock_backups_exit(self):
        """Exit with lock acquired status"""
        self.assert_is_master(False)
        sys.exit(self.slave_lock_backups())

    def slave_lock_backups(self):
        """Create lock file to deny other concurrent backups"""
        srcdir = self.cf.getfile("completed_wals")
        lockfile = os.path.join(srcdir, "BACKUPLOCK")
        if os.path.isfile(lockfile):
            self.log.warning("Somebody already has the backup lock.")
            lockfilehandle = open(lockfile,"r")
            pidstring = lockfilehandle.read();
            try:
                pid = int(pidstring)
                print("%d" % pid)
            except ValueError:
                self.log.error("lock file does not contain a pid: %s", pidstring)
            return 1

        if not self.not_really:
            f = open(lockfile, "w")
            if len(self.args) > 0:
                f.write(self.args[0])
            f.close()
        self.log.info("Backup lock obtained.")
        return 0

    def slave_resume_backups(self):
        """Remove backup lock file, allow other backups to run"""
        self.assert_is_master(False)
        srcdir = self.cf.getfile("completed_wals")
        lockfile = os.path.join(srcdir, "BACKUPLOCK")
        if os.path.isfile(lockfile):
            if not self.not_really:
                os.remove(lockfile)
            self.log.info("Backup lock released.")
        else:
            self.log.info("Backup lock not held.")

    def list_backups(self):
        """List available backups. On master this just calls slave listbackups via SSH"""
        if self.is_master:
            self.remote_walmgr("listbackups")
        else:
            backups = self.get_backup_list(self.cf.getfile("full_backup"))
            if backups:
                print "\nList of backups:\n"
                print "%-15s %-24s %-11s %-24s" % \
                    ("Backup set", "Timestamp", "Label", "First WAL")
                print "%s %s %s %s" % (15*'-', 24*'-', 11*'-',24*'-')
                for backup in backups:
                    lbl = BackupLabel(backup)
                    print "%-15s %-24.24s %-11.11s %-24s" % \
                        (os.path.basename(backup), lbl.start_time,
                        lbl.label_string, lbl.first_wal)
                print
            else:
                print "\nNo backups found.\n"

    def get_first_walname(self,backupdir):
        """Returns the name of the first needed WAL segment for backupset"""
        label = BackupLabel(backupdir)
        if not label.first_wal:
            self.log.error("WAL name not found at %s", backupdir)
            return None
        return label.first_wal

    def last_restart_point(self,walname):
        """
        Determine the WAL file of the last restart point (recovery checkpoint).
        For 8.3 this could be done with %r parameter to restore_command, for 8.2
        we need to consult control file (parse pg_controldata output).
        """
        slave_data = self.cf.getfile("slave_data")
        backup_label = os.path.join(slave_data, "backup_label")
        if os.path.exists(backup_label):
            # Label file still exists, use it for determining the restart point
            lbl = BackupLabel(slave_data)
            self.log.debug("Last restart point from backup_label: %s", lbl.first_wal)
            return lbl.first_wal

        ctl = PgControlData(self.cf.getfile("slave_bin", ""), ".", True)
        if not ctl.is_valid:
            # No restart point information, use the given wal name
            self.log.warning("Unable to determine last restart point")
            return walname

        self.log.debug("Last restart point: %s", ctl.wal_name)
        return ctl.wal_name

    def order_backupdirs(self,prefix,a,b):
        """Compare the backup directory indexes numerically"""
        prefix = os.path.abspath(prefix)

        a_indx = a[len(prefix)+1:]
        if not a_indx:
            a_indx = -1
        b_indx = b[len(prefix)+1:]
        if not b_indx:
            b_indx = -1
        return cmp(int(a_indx), int(b_indx))

    def get_backup_list(self,dst_loc):
        """Return the list of backup directories"""
        dirlist = glob.glob(os.path.abspath(dst_loc) + "*")
        dirlist.sort(lambda x,y: self.order_backupdirs(dst_loc, x,y))
        backupdirs = [ dir for dir in dirlist
            if os.path.isdir(dir) and os.path.isfile(os.path.join(dir, "backup_label"))
                or os.path.isfile(os.path.join(dir, "backup_label.old"))]
        return backupdirs

    def slave_purge_wals(self):
        """
        Remove WAL files not needed for recovery
        """
        self.assert_is_master(False)
        backups = self.get_backup_list(self.cf.getfile("full_backup"))
        if backups:
            lastwal = self.get_first_walname(backups[-1])
            if lastwal:
                self.log.info("First useful WAL file is: %s", lastwal)
                self.slave_cleanup(lastwal)
        else:
            self.log.debug("No WAL-s to clean up.")

    def slave_rotate_backups(self):
        """
        Rotate backups by increasing backup directory suffixes. Note that since
        we also have to make room for next backup, we actually have
        keep_backups - 1 backups available after this.

        Unneeded WAL files are not removed here, handled by xpurgewals command instead.
        """
        self.assert_is_master(False)
        dst_loc = self.cf.getfile("full_backup")
        maxbackups = self.cf.getint("keep_backups", 0)
        archive_command = self.cf.get("archive_command", "")

        backupdirs = self.get_backup_list(dst_loc)
        if not backupdirs or maxbackups < 1:
            self.log.debug("Nothing to rotate")

        # remove expired backups
        while len(backupdirs) >= maxbackups and len(backupdirs) > 0:
            last = backupdirs.pop()

            # if archive_command is set, run it before removing the directory
            # Resume only if archive command succeeds.
            if archive_command:
                cmdline = archive_command.replace("$BACKUPDIR", last)
                self.log.info("Executing archive_command: %s", cmdline)
                rc = self.exec_system(cmdline)
                if rc != 0:
                    self.log.error("Backup archiving returned %d, exiting!", rc)
                    sys.exit(1)

            self.log.info("Removing expired backup directory: %s", last)
            if self.not_really:
                continue
            cmdline = [ "rm", "-r", last ]
            self.exec_cmd(cmdline)

        # bump the suffixes if base directory exists
        if os.path.isdir(dst_loc):
            backupdirs.sort(lambda x,y: self.order_backupdirs(dst_loc, y,x))
            for dir in backupdirs:
                (name, index) = os.path.splitext(dir)
                if not re.match('\.[0-9]+$', index):
                    name = name + index
                    index = 0
                else:
                    index = int(index[1:])+1
                self.log.debug("Rename %s to %s.%s", dir, name, index)
                if self.not_really:
                    continue
                os.rename(dir, "%s.%s" % (name,index))

    def slave_cleanup(self, last_applied):
        completed_wals = self.cf.getfile("completed_wals")
        partial_wals = self.cf.getfile("partial_wals")

        self.log.debug("cleaning completed wals before %s", last_applied)
        self.del_wals(completed_wals, last_applied)

        if os.path.isdir(partial_wals):
            self.log.debug("cleaning partial wals before %s", last_applied)
            self.del_wals(partial_wals, last_applied)
        else:
            self.log.warning("partial_wals dir does not exist: %s", partial_wals)

        self.log.debug("cleaning done")

    def del_wals(self, path, last):
        dot = last.find(".")
        if dot > 0:
            last = last[:dot]
        list = os.listdir(path)
        list.sort()
        cur_last = None
        n = len(list)
        for i in range(n):
            fname = list[i]
            full = os.path.join(path, fname)
            if fname[0] < "0" or fname[0] > "9":
                continue
            if not fname.startswith(last[0:8]):
                # only look at WAL segments in a same timeline
                continue

            ok_del = 0
            if fname < last:
                self.log.debug("deleting %s", full)
                if not self.not_really:
                    try:
                        os.remove(full)
                    except:
                        # don't report the errors if the file has been already removed
                        # happens due to conflicts with pg_archivecleanup for instance.
                        pass
            cur_last = fname
        return cur_last

if __name__ == "__main__":
    script = WalMgr(sys.argv[1:])
    script.start()

########NEW FILE########
__FILENAME__ = catsql
#! /usr/bin/env python

"""Prints out SQL files with psql command execution.

Supported psql commands: \i, \cd, \q
Others are skipped.

Aditionally does some pre-processing for NDoc.
NDoc is looks nice but needs some hand-holding.

Bug:

- function def end detection searches for 'as'/'is' but does not check
  word boundaries - finds them even in function name.  That means in
  main conf, as/is must be disabled and $ ' added.  This script can
  remove the unnecessary AS from output.

Niceties:

- Ndoc includes function def in output only if def is after comment.
  But for SQL functions its better to have it after def.
  This script can swap comment and def.

- Optionally remove CREATE FUNCTION (OR REPLACE) from def to
  keep it shorter in doc.

Note:

- NDoc compares real function name and name in comment. if differ,
  it decides detection failed.

"""

import sys, os, re, getopt

def usage(x):
    print("usage: catsql [--ndoc] FILE [FILE ...]")
    sys.exit(x)

# NDoc specific changes
cf_ndoc = 0

# compile regexes
func_re = r"create\s+(or\s+replace\s+)?function\s+"
func_rc = re.compile(func_re, re.I)
comm_rc = re.compile(r"^\s*([#]\s*)?(?P<com>--.*)", re.I)
end_rc = re.compile(r"\b([;]|begin|declare|end)\b", re.I)
as_rc = re.compile(r"\s+as\s+", re.I)
cmd_rc = re.compile(r"^\\([a-z]*)(\s+.*)?", re.I)

# conversion func
def fix_func(ln):
    # if ndoc, replace AS with ' '
    if cf_ndoc:
        return as_rc.sub(' ', ln)
    else:
        return ln

# got function def
def proc_func(f, ln):
    # remove CREATE OR REPLACE
    if cf_ndoc:
        ln = func_rc.sub('', ln)

    ln = fix_func(ln)
    pre_list = [ln]
    comm_list = []
    while 1:
        ln = f.readline()
        if not ln:
            break

        com = None
        if cf_ndoc:
            com = comm_rc.search(ln)
        if cf_ndoc and com:
            pos = com.start('com')
            comm_list.append(ln[pos:])
        elif end_rc.search(ln):
            break
        elif len(comm_list) > 0:
            break
        else:
            pre_list.append(fix_func(ln))

    if len(comm_list) > 2:
        map(sys.stdout.write, comm_list)
        map(sys.stdout.write, pre_list)
    else:
        map(sys.stdout.write, pre_list)
        map(sys.stdout.write, comm_list)
    if ln:
        sys.stdout.write(fix_func(ln))

def cat_file(fn):
    sys.stdout.write("\n")
    f = open(fn)
    while 1:
        ln = f.readline()
        if not ln:
            break
        m = cmd_rc.search(ln)
        if m:
            cmd = m.group(1)
            if cmd == "i":          # include a file
                fn2 = m.group(2).strip()
                cat_file(fn2)
            elif cmd == "q":        # quit
                sys.exit(0)
            elif cmd == "cd":       # chdir
                cd_dir = m.group(2).strip()
                os.chdir(cd_dir)
            else:                   # skip all others
                pass
        else:
            if func_rc.search(ln):  # function header
                proc_func(f, ln)
            else:                   # normal sql
                sys.stdout.write(ln)
    sys.stdout.write("\n")

def main():
    global cf_ndoc

    try:
        opts, args = getopt.gnu_getopt(sys.argv[1:], 'h', ['ndoc'])
    except getopt.error, d:
        print(str(d))
        usage(1)
    for o, v in opts:
        if o == "-h":
            usage(0)
        elif o == "--ndoc":
            cf_ndoc = 1
    for fn in args:
        cat_file(fn)

if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = data_maintainer
#!/usr/bin/env python

"""Generic script for processing large data sets in small batches.

Reads events from one datasource and commits them into another one,
either one by one or in batches.

Config template::

    [data_maintainer3]
    job_name        = dm_remove_expired_services

    # if source is database, you need to specify dbread and sql_get_pk_list
    dbread          = dbname=sourcedb_test
    sql_get_pk_list =
        select username
        from user_service
        where expire_date < now();

    # if source is csv file, you need to specify fileread and optionally csv_delimiter and csv_quotechar
    #fileread       = data.csv
    #csv_delimiter  = ,
    #csv_quotechar  = "

    dbwrite         = dbname=destdb port=1234 host=dbhost.com user=guest password=secret
    dbbefore        = dbname=destdb_test
    dbafter         = dbname=destdb_test
    dbcrash         = dbname=destdb_test
    dbthrottle      = dbname=queuedb_test

    # It is a good practice to include same where condition on target side as on read side,
    # to ensure that you are actually changing the same data you think you are,
    # especially when reading from replica database or when processing takes days.
    sql_modify =
        delete from user_service
        where username = %%(username)s
        and expire_date < now();

    # This will be run before executing the sql_get_pk_list query (optional)
    #sql_before_run =
    #    select * from somefunction1(%(job_name)s);

    # This will be run when the DM finishes (optional)
    #sql_after_run =
    #    select * from somefunction2(%(job_name)s);

    # Determines whether the sql_after_run query will be run in case the pk list query returns no rows
    #after_zero_rows = 1

    # This will be run if the DM crashes (optional)
    #sql_on_crash =
    #    select * from somefunction3(%(job_name)s);

    # This may be used to control throttling of the DM (optional)
    #sql_throttle =
    #    select lag>'5 minutes'::interval from pgq.get_consumer_info('failoverconsumer');

    # materialize query so that transaction should not be open while processing it (only used when source is a database)
    #with_hold       = 1

    # how many records process to fetch at once and if batch processing is used then
    # also how many records are processed in one commit
    #fetch_count     = 100

    # by default commit after each row (safe when behind plproxy, bouncer or whatever)
    # can be turned off for better performance when connected directly to database
    #autocommit      = 1

    # just for tuning to throttle how much load we let onto write database
    #commit_delay    = 0.0

    # quite often data_maintainer is run from crontab and then loop delay is not needed
    # in case it has to be run as daemon set loop delay in seconds
    #loop_delay      = 1

    logfile         = ~/log/%(job_name)s.log
    pidfile         = ~/pid/%(job_name)s.pid
    use_skylog      = 0
"""

import csv
import datetime
import os.path
import sys
import time

import pkgloader
pkgloader.require('skytools', '3.0')
import skytools


class DataSource (object):
    def __init__(self, log):
        self.log = log

    def open(self):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError

    def fetch(self, count):
        raise NotImplementedError


class DBDataSource (DataSource):
    def __init__(self, log, db, query, bres = None, with_hold = False):
        super(DBDataSource, self).__init__(log)
        self.db = db
        if with_hold:
            self.query = "DECLARE data_maint_cur NO SCROLL CURSOR WITH HOLD FOR %s" % query
        else:
            self.query = "DECLARE data_maint_cur NO SCROLL CURSOR FOR %s" % query
        self.bres = bres
        self.with_hold = with_hold

    def _run_query(self, query, params = None):
        self.cur.execute(query, params)
        self.log.debug(self.cur.query)
        self.log.debug(self.cur.statusmessage)

    def open(self):
        self.cur = self.db.cursor()
        self._run_query(self.query, self.bres)  # pass results from before_query into sql_pk

    def close(self):
        self.cur.execute("CLOSE data_maint_cur")
        if not self.with_hold:
            self.db.rollback()

    def fetch(self, count):
        self._run_query("FETCH FORWARD %i FROM data_maint_cur" % count)
        return self.cur.fetchall()


class CSVDataSource (DataSource):
    def __init__(self, log, filename, delimiter, quotechar):
        super(CSVDataSource, self).__init__(log)
        self.filename = filename
        self.delimiter = delimiter
        self.quotechar = quotechar

    def open(self):
        self.fp = open(self.filename, 'rb')
        self.reader = csv.DictReader(self.fp, delimiter = self.delimiter, quotechar = self.quotechar)

    def close(self):
        self.fp.close()

    def fetch(self, count):
        ret = []
        for row in self.reader:
            ret.append(row)
            count -= 1
            if count <= 0:
                break
        return ret


class DataMaintainer (skytools.DBScript):
    __doc__ = __doc__
    loop_delay = -1

    def __init__(self, args):
        super(DataMaintainer, self).__init__("data_maintainer3", args)

        # source file
        self.fileread = self.cf.get("fileread", "")
        if self.fileread:
            self.fileread = os.path.expanduser(self.fileread)
            self.set_single_loop(True)  # force single run if source is file

        self.csv_delimiter = self.cf.get("csv_delimiter", ',')
        self.csv_quotechar = self.cf.get("csv_quotechar", '"')

        # query for fetching the PK-s of the data set to be maintained
        self.sql_pk = self.cf.get("sql_get_pk_list", "")

        if (int(bool(self.sql_pk)) + int(bool(self.fileread))) in (0,2):
            raise skytools.UsageError("Either fileread or sql_get_pk_list must be specified in the configuration file")

        # query for changing data tuple ( autocommit )
        self.sql_modify = self.cf.get("sql_modify")

        # query to be run before starting the data maintainer,
        # useful for retrieving initialization parameters of the query
        self.sql_before = self.cf.get("sql_before_run", "")

        # query to be run after finishing the data maintainer
        self.sql_after = self.cf.get("sql_after_run", "")

        # whether to run the sql_after query in case of 0 rows
        self.after_zero_rows = self.cf.getint("after_zero_rows", 1)

        # query to be run if the process crashes
        self.sql_crash = self.cf.get("sql_on_crash", "")

        # query for checking if / how much to throttle
        self.sql_throttle = self.cf.get("sql_throttle", "")

        # how many records to fetch at once
        self.fetchcnt = self.cf.getint("fetchcnt", 100)
        self.fetchcnt = self.cf.getint("fetch_count", self.fetchcnt)

        # specifies if non-transactional cursor should be created (0 -> without hold)
        self.withhold = self.cf.getint("with_hold", 1)

        # execution mode (0 -> whole batch is committed / 1 -> autocommit)
        self.autocommit = self.cf.getint("autocommit", 1)

        # delay in seconds after each commit
        self.commit_delay = self.cf.getfloat("commit_delay", 0.0)

    def work(self):
        self.log.info('Starting..')
        self.started = self.lap_time = time.time()
        self.total_count = 0
        bres = {}

        if self.sql_before:
            bdb = self.get_database("dbbefore", autocommit=1)
            bcur = bdb.cursor()
            bcur.execute(self.sql_before)
            if bcur.statusmessage.startswith('SELECT'):
                res = bcur.fetchall()
                assert len(res)==1, "Result of a 'before' query must be 1 row"
                bres = res[0].copy()

        if self.sql_throttle:
            dbt = self.get_database("dbthrottle", autocommit=1)
            tcur = dbt.cursor()

        if self.autocommit:
            self.log.info("Autocommit after each modify")
            dbw = self.get_database("dbwrite", autocommit=1)
        else:
            self.log.info("Commit in %i record batches", self.fetchcnt)
            dbw = self.get_database("dbwrite", autocommit=0)

        if self.fileread:
            self.datasource = CSVDataSource(self.log, self.fileread, self.csv_delimiter, self.csv_quotechar)
        else:
            if self.withhold:
                dbr = self.get_database("dbread", autocommit=1)
            else:
                dbr = self.get_database("dbread", autocommit=0)
            self.datasource = DBDataSource(self.log, dbr, self.sql_pk, bres, self.withhold)

        self.datasource.open()
        mcur = dbw.cursor()

        while True: # loop while fetch returns fetch_count rows
            self.fetch_started = time.time()
            res = self.datasource.fetch(self.fetchcnt)
            count, lastitem = self.process_batch(res, mcur, bres)
            self.total_count += count
            if not self.autocommit:
                dbw.commit()
            self.stat_put("duration", time.time() - self.fetch_started)
            self.send_stats()
            if len(res) < self.fetchcnt or self.last_sigint:
                break
            if self.commit_delay > 0.0:
                time.sleep(self.commit_delay)
            if self.sql_throttle:
                self.throttle(tcur)
            self._print_count("--- Running count: %s duration: %s ---")

        if self.last_sigint:
            self.log.info("Exiting on user request")

        self.datasource.close()
        self.log.info("--- Total count: %s duration: %s ---",
                self.total_count, datetime.timedelta(0, round(time.time() - self.started)))

        if self.sql_after and (self.after_zero_rows > 0 or self.total_count > 0):
            adb = self.get_database("dbafter", autocommit=1)
            acur = adb.cursor()
            acur.execute(self.sql_after, lastitem)

    def process_batch(self, res, mcur, bres):
        """ Process events in autocommit mode reading results back and trying to make some sense out of them
        """
        try:
            count = 0
            item = bres.copy()
            for i in res:   # for each row in read query result
                item.update(i)
                mcur.execute(self.sql_modify, item)
                self.log.debug(mcur.query)
                if mcur.statusmessage.startswith('SELECT'): # if select was used we can expect some result
                    mres = mcur.fetchall()
                    for r in mres:
                        if 'stats' in r: # if specially handled column 'stats' is present
                            for k, v in skytools.db_urldecode(r['stats'] or '').items():
                                self.stat_increase(k, int(v))
                        self.log.debug(r)
                else:
                    self.stat_increase('processed', mcur.rowcount)
                    self.log.debug(mcur.statusmessage)
                if 'cnt' in item:
                    count += item['cnt']
                    self.stat_increase("count", item['cnt'])
                else:
                    count += 1
                    self.stat_increase("count")
                if self.last_sigint:
                    break
            return count, item
        except: # process has crashed, run sql_crash and re-raise the exception
            if self.sql_crash:
                dbc = self.get_database("dbcrash", autocommit=1)
                ccur = dbc.cursor()
                ccur.execute(self.sql_crash, item)
            raise

    def throttle(self, tcur):
        while not self.last_sigint:
            tcur.execute(self.sql_throttle)
            _r = tcur.fetchall()
            assert len(_r) == 1 and len(_r[0]) == 1, "Result of 'throttle' query must be 1 value"
            throttle = _r[0][0]
            if isinstance(throttle, bool):
                tt = float(throttle and 30)
            elif isinstance(throttle, (int, float)):
                tt = float(throttle)
            else:
                self.log.warn("Result of 'throttle' query must be boolean or numeric")
                break
            if tt > 0.0:
                self.log.debug("sleeping %f s", tt)
                time.sleep(tt)
            else:
                break
            self._print_count("--- Waiting count: %s duration: %s ---")

    def _print_count(self, text):
        if time.time() - self.lap_time > 60.0: # if one minute has passed print running totals
            self.log.info(text, self.total_count, datetime.timedelta(0, round(time.time() - self.started)))
            self.lap_time = time.time()


if __name__ == '__main__':
    script = DataMaintainer(sys.argv[1:])
    script.start()

########NEW FILE########
__FILENAME__ = find_sql_functions
#! /usr/bin/env python

"""Find and print out function signatures from .sql file.

Usage:
    find_sql_functions.py [-h] [-s] [-p PREFIX] FILE ...

Switches:
    -h         Show help
    -p PREFIX  Prefix each line with string
    -s         Check whether function is SECURITY DEFINER
"""

import sys, re, getopt

rx = r"""
^
create \s+ (?: or \s+ replace \s+ )?
function ( [^(]+ )
[(] ( [^)]* ) [)]
"""

rx_secdef = r"""security\s+definer"""


rc = re.compile(rx, re.I | re.M | re.X)
sc = re.compile(r"\s+")
rc_sec = re.compile(rx_secdef, re.I | re.X)

def grep_file(fn, cf_prefix, cf_secdef):
    sql = open(fn).read()
    pos = 0
    while 1:
        m = rc.search(sql, pos)
        if not m:
            break
        pos = m.end()

        m2 = rc.search(sql, pos)
        if m2:
            xpos = m2.end()
        else:
            xpos = len(sql)
        secdef = False
        m2 = rc_sec.search(sql, pos, xpos)
        if m2:
            secdef = True

        fname = m.group(1).strip()
        fargs = m.group(2)

        alist = fargs.split(',')
        tlist = []
        for a in alist:
            a = a.strip()
            toks = sc.split(a.lower())
            if toks[0] == "out":
                continue
            if toks[0] in ("in", "inout"):
                toks = toks[1:]
            # just take last item
            tlist.append(toks[-1])

        sig = "%s(%s)" % (fname, ", ".join(tlist))

        if cf_prefix:
            ln = "%s %s;" % (cf_prefix, sig)
        else:
            ln = "    %s(%s)," % (fname, ", ".join(tlist))

        if cf_secdef and secdef:
            ln = "%-72s -- SECDEF" % (ln)

        print ln

def main(argv):
    cf_secdef = 0
    cf_prefix = ''

    try:
        opts, args = getopt.getopt(argv, "hsp:")
    except getopt.error, d:
        print 'getopt:', d
        sys.exit(1)

    for o, a in opts:
        if o == '-h':
            print __doc__
            sys.exit(0)
        elif o == '-s':
            cf_secdef = 1
        elif o == '-p':
            cf_prefix = a
        else:
            print __doc__
            sys.exit(1)

    for fn in args:
        grep_file(fn, cf_prefix, cf_secdef)

if __name__ == '__main__':
    main(sys.argv[1:])


########NEW FILE########
__FILENAME__ = grantfu
#! /usr/bin/env python

# GrantFu - GRANT/REVOKE generator for Postgres
# 
# Copyright (c) 2005 Marko Kreen
# 
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
# 
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.


"""Generator for PostgreSQL permissions.

Loads config where roles, objects and their mapping is described
and generates grants based on them.

ConfigParser docs: http://docs.python.org/lib/module-ConfigParser.html

Example:
--------------------------------------------------------------------
[DEFAULT]
users = user1, user2      # users to handle
groups = group1, group2   # groups to handle
auto_seq = 0              # dont handle seqs (default)
                          # '!' after a table negates this setting for a table
seq_name = id             # the name for serial field (default: id)
seq_usage = 0             # should we grant "usage" or "select, update"
                          # for automatically handled sequences

# section names can be random, but if you want to see them
# in same order as in config file, then order them alphabetically
[1.section]
on.tables = testtbl, testtbl_id_seq,   # here we handle seq by hand
         table_with_seq!               # handle seq automatically
                                       # (table_with_seq_id_seq)
user1 = select
group1 = select, insert, update

# instead of 'tables', you may use 'functions', 'languages',
# 'schemas', 'tablespaces'
---------------------------------------------------------------------
"""

import sys, os, getopt
from ConfigParser import SafeConfigParser

__version__ = "1.0"

R_NEW = 0x01
R_DEFS = 0x02
G_DEFS = 0x04
R_ONLY = 0x80

def usage(err):
    sys.stderr.write("usage: %s [-r|-R] CONF_FILE\n" % sys.argv[0])
    sys.stderr.write("  -r   Generate also REVOKE commands\n")
    sys.stderr.write("  -R   Generate only REVOKE commands\n")
    sys.stderr.write("  -d   Also REVOKE default perms\n")
    sys.stderr.write("  -D   Only REVOKE default perms\n")
    sys.stderr.write("  -o   Generate default GRANTS\n")
    sys.stderr.write("  -v   Print program version\n")
    sys.stderr.write("  -t   Put everything in one big transaction\n")
    sys.exit(err)

class PConf(SafeConfigParser):
    "List support for ConfigParser"
    def __init__(self, defaults = None):
        SafeConfigParser.__init__(self, defaults)

    def get_list(self, sect, key):
        str = self.get(sect, key).strip()
        res = []
        if not str:
            return res
        for val in str.split(","):
            res.append(val.strip())
        return res

class GrantFu:
    def __init__(self, cf, revoke):
        self.cf = cf
        self.revoke = revoke

        # avoid putting grantfu vars into defaults, thus into every section
        self.group_list = []
        self.user_list = []
        self.auto_seq = 0
        self.seq_name = "id"
        self.seq_usage = 0
        if self.cf.has_option('GrantFu', 'groups'):
            self.group_list = self.cf.get_list('GrantFu', 'groups')
        if self.cf.has_option('GrantFu', 'users'):
            self.user_list += self.cf.get_list('GrantFu', 'users')
        if self.cf.has_option('GrantFu', 'roles'):
            self.user_list += self.cf.get_list('GrantFu', 'roles')
        if self.cf.has_option('GrantFu', 'auto_seq'):
            self.auto_seq = self.cf.getint('GrantFu', 'auto_seq')
        if self.cf.has_option('GrantFu', 'seq_name'):
            self.seq_name = self.cf.get('GrantFu', 'seq_name')
        if self.cf.has_option('GrantFu', 'seq_usage'):
            self.seq_usage = self.cf.getint('GrantFu', 'seq_usage')

        # make string of all subjects
        tmp = []
        for g in self.group_list:
            tmp.append("group " + g)
        for u in self.user_list:
            tmp.append(u)
        self.all_subjs = ", ".join(tmp)

        # per-section vars
        self.sect = None
        self.seq_list = []
        self.seq_allowed = []

    def process(self):
        if len(self.user_list) == 0 and len(self.group_list) == 0:
            return

        sect_list = self.cf.sections()
        sect_list.sort()
        for self.sect in sect_list:
            if self.sect == "GrantFu":
                continue
            print "\n-- %s --" % self.sect

            self.handle_tables()
            self.handle_other('on.databases', 'DATABASE')
            self.handle_other('on.functions', 'FUNCTION')
            self.handle_other('on.languages', 'LANGUAGE')
            self.handle_other('on.schemas', 'SCHEMA')
            self.handle_other('on.tablespaces', 'TABLESPACE')
            self.handle_other('on.sequences', 'SEQUENCE')
            self.handle_other('on.types', 'TYPE')
            self.handle_other('on.domains', 'DOMAIN')

    def handle_other(self, listname, obj_type):
        """Handle grants for all objects except tables."""

        if not self.sect_hasvar(listname):
            return

        # don't parse list, as in case of functions it may be complicated
        obj_str = obj_type + " " + self.sect_var(listname)
        
        if self.revoke & R_NEW:
            self.gen_revoke(obj_str)
        
        if self.revoke & R_DEFS:
            self.gen_revoke_defs(obj_str, obj_type)
        
        if not self.revoke & R_ONLY:
            self.gen_one_type(obj_str)

        if self.revoke & G_DEFS:
            self.gen_defs(obj_str, obj_type)

    def handle_tables(self):
        """Handle grants for tables and sequences.
        
        The tricky part here is the automatic handling of sequences."""

        if not self.sect_hasvar('on.tables'):
            return

        cleaned_list = []
        table_list = self.sect_list('on.tables')
        for table in table_list:
            if table[-1] == '!':
                table = table[:-1]
                if not self.auto_seq:
                    self.seq_list.append("%s_%s_seq" % (table, self.seq_name))
            else:
                if self.auto_seq:
                    self.seq_list.append("%s_%s_seq" % (table, self.seq_name))
            cleaned_list.append(table)
        obj_str = "TABLE " + ", ".join(cleaned_list)

        if self.revoke & R_NEW:
            self.gen_revoke(obj_str)
        if self.revoke & R_DEFS:
            self.gen_revoke_defs(obj_str, "TABLE")
        if not self.revoke & R_ONLY:
            self.gen_one_type(obj_str)
        if self.revoke & G_DEFS:
            self.gen_defs(obj_str, "TABLE")

        # cleanup
        self.seq_list = []
        self.seq_allowed = []

    def gen_revoke(self, obj_str):
        "Generate revoke for one section / subject type (user or group)"

        if len(self.seq_list) > 0:
            obj_str += ", " + ", ".join(self.seq_list)
        obj_str = obj_str.strip().replace('\n', '\n    ')
        print "REVOKE ALL ON %s\n  FROM %s CASCADE;" % (obj_str, self.all_subjs)

    def gen_revoke_defs(self, obj_str, obj_type):
        "Generate revoke defaults for one section"

        # process only things that have default grants to public
        if obj_type not in ('FUNCTION', 'DATABASE', 'LANGUAGE', 'TYPE', 'DOMAIN'):
            return

        defrole = 'public'

        # if the sections contains grants to 'public', dont drop
        if self.sect_hasvar(defrole):
            return

        obj_str = obj_str.strip().replace('\n', '\n    ')
        print "REVOKE ALL ON %s\n  FROM %s CASCADE;" % (obj_str, defrole)

    def gen_defs(self, obj_str, obj_type):
        "Generate defaults grants for one section"

        if obj_type == "FUNCTION":
            defgrants = "execute"
        elif obj_type == "DATABASE":
            defgrants = "connect, temp"
        elif obj_type in ("LANGUAGE", "TYPE", "DOMAIN"):
            defgrants = "usage"
        else:
            return

        defrole = 'public'

        obj_str = obj_str.strip().replace('\n', '\n    ')
        print "GRANT %s ON %s\n  TO %s;" % (defgrants, obj_str, defrole)

    def gen_one_subj(self, subj, fqsubj, obj_str):
        if not self.sect_hasvar(subj):
            return
        obj_str = obj_str.strip().replace('\n', '\n    ')
        perm = self.sect_var(subj).strip()
        if perm:
            print "GRANT %s ON %s\n  TO %s;" % (perm, obj_str, fqsubj)

        # check for seq perms
        if len(self.seq_list) > 0:
            loperm = perm.lower()
            if loperm.find("insert") >= 0 or loperm.find("all") >= 0:
                self.seq_allowed.append(fqsubj)

    def gen_one_type(self, obj_str):
        "Generate GRANT for one section / one object type in section"

        for u in self.user_list:
            self.gen_one_subj(u, u, obj_str)
        for g in self.group_list:
            self.gen_one_subj(g, "group " + g, obj_str)

        # if there was any seq perms, generate grants
        if len(self.seq_allowed) > 0:
            seq_str = ", ".join(self.seq_list)
            subj_str = ", ".join(self.seq_allowed)
            if self.seq_usage:
                cmd = "GRANT usage ON SEQUENCE %s\n  TO %s;"
            else:
                cmd = "GRANT select, update ON %s\n  TO %s;"
            print cmd % (seq_str, subj_str)

    def sect_var(self, name):
        return self.cf.get(self.sect, name).strip()

    def sect_list(self, name):
        return self.cf.get_list(self.sect, name)

    def sect_hasvar(self, name):
        return self.cf.has_option(self.sect, name)

def main():
    revoke = 0
    tx = False

    try:
        opts, args = getopt.getopt(sys.argv[1:], "vhrRdDot")
    except getopt.error, det:
        print "getopt error:", det
        usage(1)

    for o, v in opts:
        if o == "-h":
            usage(0)
        elif o == "-r":
            revoke |= R_NEW
        elif o == "-R":
            revoke |= R_NEW | R_ONLY
        elif o == "-d":
            revoke |= R_DEFS
        elif o == "-D":
            revoke |= R_DEFS | R_ONLY
        elif o == "-o":
            revoke |= G_DEFS
        elif o == "-t":
            tx = True
        elif o == "-v":
            print "GrantFu version", __version__
            sys.exit(0)

    if len(args) != 1:
        usage(1)

    # load config
    cf = PConf()
    cf.read(args[0])
    if not cf.has_section("GrantFu"):
        print "Incorrect config file, GrantFu sction missing"
        sys.exit(1)

    if tx:
        print "begin;\n"

    # revokes and default grants
    if revoke & (R_NEW | R_DEFS):
        g = GrantFu(cf, revoke | R_ONLY)
        g.process()
        revoke = revoke & R_ONLY

    # grants
    if revoke & R_ONLY == 0:
        g = GrantFu(cf, revoke & G_DEFS)
        g.process()

    if tx:
        print "\ncommit;\n"

if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = queue_loader
#! /usr/bin/env python

"""Load data from queue into tables, with optional partitioning.

Config template::

    [queue_loader]
    job_name =
    logfile =
    pidfile =

    db =

    #rename_tables =

    [DEFAULT]

    # fields - which fields to send through
    #fields = col1, col2, col3:renamed3
    #fields = *

    # table_mode - how to handle a table
    #
    # ignore - ignore this table
    # direct - update table directly
    # split - split data into partitions
    #table_mode = ignore

    # split_mode - how to split, if requested
    #
    # by-batch-time: use batch time for splitting
    # by-event-time: use event time for splitting
    # by-date-field:fld - use fld for splitting
    #split_mode = by-batch-time

    # split_part - partition name format
    #
    # %(table_name)s %(year)s %(month)s %(day)s %(hour)s
    #split_part = %(table_name)s_%(year)s_%(month)s_%(day)s

    # split_part_template - How to create new partition tables
    #
    # Available fields:
    # %(part)s
    # %(parent)s
    # %(pkey)s
    #
    ### Non-inherited partitions
    #split_part_template =
    #    create table %%(part)s (like %%(parent)s);
    #    alter table only %%(part)s add primary key (%%(pkey)s);
    #
    ### Inherited partitions
    #split_part_template =
    #    create table %%(part)s () inherits (%%(parent)s);
    #    alter table only %%(part)s add primary key (%%(pkey)s);


    # row_mode - How to apply the events
    #
    # plain - each event creates SQL statement to run
    # keep_latest - change updates to DELETE + INSERT
    # keep_all - change updates to inserts, ignore deletes
    # bulk - instead of statement-per-row, do bulk updates
    #row_mode = plain


    # bulk_mode - How to do the bulk update
    #
    # correct - inserts as COPY into table,
    #           update as COPY into temp table and single UPDATE from there
    #           delete as COPY into temp table and single DELETE from there
    # delete - as 'correct', but do update as DELETE + COPY
    # merged - as 'delete', but merge insert rows with update rows
    #bulk_mode=correct

    [table public.foo]
    mode =
    create_sql =
"""

import sys, time

import pkgloader
pkgloader.require('skytools', '3.0')

import skytools
from pgq.cascade.worker import CascadedWorker
from skytools import quote_ident, quote_fqident, UsageError

# TODO: auto table detect

# BulkLoader load method
METH_CORRECT = 0
METH_DELETE = 1
METH_MERGED = 2
LOAD_METHOD = METH_CORRECT
# BulkLoader hacks
AVOID_BIZGRES_BUG = 0
USE_LONGLIVED_TEMP_TABLES = True


class BasicLoader:
    """Apply events as-is."""
    def __init__(self, table_name, parent_name, log):
        self.table_name = table_name
        self.parent_name = parent_name
        self.sql_list = []
        self.log = log

    def add_row(self, op, data, pkey_list):
        if op == 'I':
            sql = skytools.mk_insert_sql(data, self.table_name, pkey_list)
        elif op == 'U':
            sql = skytools.mk_update_sql(data, self.table_name, pkey_list)
        elif op == 'D':
            sql = skytools.mk_delete_sql(data, self.table_name, pkey_list)
        else:
            raise Exception('bad operation: '+op)
        self.sql_list.append(sql)

    def flush(self, curs):
        if len(self.sql_list) > 0:
            curs.execute("\n".join(self.sql_list))
            self.sql_list = []


class KeepLatestLoader(BasicLoader):
    """Keep latest row version.

    Updates are changed to delete + insert, deletes are ignored.
    Makes sense only for partitioned tables.
    """
    def add_row(self, op, data, pkey_list):
        if op == 'U':
            BasicLoader.add_row(self, 'D', data, pkey_list)
            BasicLoader.add_row(self, 'I', data, pkey_list)
        elif op == 'I':
            BasicLoader.add_row(self, 'I', data, pkey_list)
        else:
            pass


class KeepAllLoader(BasicLoader):
    """Keep all row versions.

    Updates are changed to inserts, deletes are ignored.
    Makes sense only for partitioned tables.
    """
    def add_row(self, op, data, pkey_list):
        if op == 'U':
            op = 'I'
        elif op == 'D':
            return
        BasicLoader.add_row(self, op, data, pkey_list)


class BulkEvent(object):
    """Helper class for BulkLoader to store relevant data."""
    __slots__ = ('op', 'data', 'pk_data')
    def __init__(self, op, data, pk_data):
        self.op = op
        self.data = data
        self.pk_data = pk_data


class BulkLoader(BasicLoader):
    """Instead of statement-per event, load all data with one
    big COPY, UPDATE or DELETE statement.
    """
    fake_seq = 0
    def __init__(self, table_name, parent_name, log):
        """Init per-batch table data cache."""
        BasicLoader.__init__(self, table_name, parent_name, log)

        self.pkey_list = None
        self.dist_fields = None
        self.col_list = None

        self.ev_list = []
        self.pkey_ev_map = {}

    def reset(self):
        self.ev_list = []
        self.pkey_ev_map = {}

    def add_row(self, op, data, pkey_list):
        """Store new event."""

        # get pkey value
        if self.pkey_list is None:
            self.pkey_list = pkey_list
        if len(self.pkey_list) > 0:
            pk_data = (data[k] for k in self.pkey_list)
        elif op == 'I':
            # fake pkey, just to get them spread out
            pk_data = self.fake_seq
            self.fake_seq += 1
        else:
            raise Exception('non-pk tables not supported: %s' % self.table_name)

        # get full column list, detect added columns
        if not self.col_list:
            self.col_list = data.keys()
        elif self.col_list != data.keys():
            # ^ supposedly python guarantees same order in keys()
            self.col_list = data.keys()

        # add to list
        ev = BulkEvent(op, data, pk_data)
        self.ev_list.append(ev)

        # keep all versions of row data
        if ev.pk_data in self.pkey_ev_map:
            self.pkey_ev_map[ev.pk_data].append(ev)
        else:
            self.pkey_ev_map[ev.pk_data] = [ev]

    def prepare_data(self):
        """Got all data, prepare for insertion."""

        del_list = []
        ins_list = []
        upd_list = []
        for ev_list in self.pkey_ev_map.values():
            # rewrite list of I/U/D events to
            # optional DELETE and optional INSERT/COPY command
            exists_before = -1
            exists_after = 1
            for ev in ev_list:
                if ev.op == "I":
                    if exists_before < 0:
                        exists_before = 0
                    exists_after = 1
                elif ev.op == "U":
                    if exists_before < 0:
                        exists_before = 1
                    #exists_after = 1 # this shouldnt be needed
                elif ev.op == "D":
                    if exists_before < 0:
                        exists_before = 1
                    exists_after = 0
                else:
                    raise Exception('unknown event type: %s' % ev.op)

            # skip short-lived rows
            if exists_before == 0 and exists_after == 0:
                continue

            # take last event
            ev = ev_list[-1]

            # generate needed commands
            if exists_before and exists_after:
                upd_list.append(ev.data)
            elif exists_before:
                del_list.append(ev.data)
            elif exists_after:
                ins_list.append(ev.data)

        return ins_list, upd_list, del_list

    def flush(self, curs):
        ins_list, upd_list, del_list = self.prepare_data()

        # reorder cols
        col_list = self.pkey_list[:]
        for k in self.col_list:
            if k not in self.pkey_list:
                col_list.append(k)

        real_update_count = len(upd_list)

        #self.log.debug("process_one_table: %s  (I/U/D = %d/%d/%d)",
        #               tbl, len(ins_list), len(upd_list), len(del_list))

        # hack to unbroke stuff
        if LOAD_METHOD == METH_MERGED:
            upd_list += ins_list
            ins_list = []

        # fetch distribution fields
        if self.dist_fields is None:
            self.dist_fields = self.find_dist_fields(curs)

        key_fields = self.pkey_list[:]
        for fld in self.dist_fields:
            if fld not in key_fields:
                key_fields.append(fld)
        #self.log.debug("PKey fields: %s  Extra fields: %s",
        #               ",".join(cache.pkey_list), ",".join(extra_fields))

        # create temp table
        temp = self.create_temp_table(curs)
        tbl = self.table_name

        # where expr must have pkey and dist fields
        klist = []
        for pk in key_fields:
            exp = "%s.%s = %s.%s" % (quote_fqident(tbl), quote_ident(pk),
                                     quote_fqident(temp), quote_ident(pk))
            klist.append(exp)
        whe_expr = " and ".join(klist)

        # create del sql
        del_sql = "delete from only %s using %s where %s" % (
                  quote_fqident(tbl), quote_fqident(temp), whe_expr)

        # create update sql
        slist = []
        for col in col_list:
            if col not in key_fields:
                exp = "%s = %s.%s" % (quote_ident(col), quote_fqident(temp), quote_ident(col))
                slist.append(exp)
        upd_sql = "update only %s set %s from %s where %s" % (
                    quote_fqident(tbl), ", ".join(slist), quote_fqident(temp), whe_expr)

        # insert sql
        colstr = ",".join([quote_ident(c) for c in col_list])
        ins_sql = "insert into %s (%s) select %s from %s" % (
                  quote_fqident(tbl), colstr, colstr, quote_fqident(temp))

        temp_used = False

        # process deleted rows
        if len(del_list) > 0:
            #self.log.info("Deleting %d rows from %s", len(del_list), tbl)
            # delete old rows
            q = "truncate %s" % quote_fqident(temp)
            self.log.debug(q)
            curs.execute(q)
            # copy rows
            self.log.debug("COPY %d rows into %s", len(del_list), temp)
            skytools.magic_insert(curs, temp, del_list, col_list)
            # delete rows
            self.log.debug(del_sql)
            curs.execute(del_sql)
            self.log.debug("%s - %d", curs.statusmessage, curs.rowcount)
            if len(del_list) != curs.rowcount:
                self.log.warning("Delete mismatch: expected=%d deleted=%d",
                                 len(del_list), curs.rowcount)
            temp_used = True

        # process updated rows
        if len(upd_list) > 0:
            #self.log.info("Updating %d rows in %s", len(upd_list), tbl)
            # delete old rows
            q = "truncate %s" % quote_fqident(temp)
            self.log.debug(q)
            curs.execute(q)
            # copy rows
            self.log.debug("COPY %d rows into %s", len(upd_list), temp)
            skytools.magic_insert(curs, temp, upd_list, col_list)
            temp_used = True
            if LOAD_METHOD == METH_CORRECT:
                # update main table
                self.log.debug(upd_sql)
                curs.execute(upd_sql)
                self.log.debug("%s - %d", curs.statusmessage, curs.rowcount)
                # check count
                if len(upd_list) != curs.rowcount:
                    self.log.warning("Update mismatch: expected=%d updated=%d",
                                     len(upd_list), curs.rowcount)
            else:
                # delete from main table
                self.log.debug(del_sql)
                curs.execute(del_sql)
                self.log.debug(curs.statusmessage)
                # check count
                if real_update_count != curs.rowcount:
                    self.log.warning("Update mismatch: expected=%d deleted=%d",
                                     real_update_count, curs.rowcount)
                # insert into main table
                if AVOID_BIZGRES_BUG:
                    # copy again, into main table
                    self.log.debug("COPY %d rows into %s", len(upd_list), tbl)
                    skytools.magic_insert(curs, tbl, upd_list, col_list)
                else:
                    # better way, but does not work due bizgres bug
                    self.log.debug(ins_sql)
                    curs.execute(ins_sql)
                    self.log.debug(curs.statusmessage)

        # process new rows
        if len(ins_list) > 0:
            self.log.info("Inserting %d rows into %s", len(ins_list), tbl)
            skytools.magic_insert(curs, tbl, ins_list, col_list)

        # delete remaining rows
        if temp_used:
            if USE_LONGLIVED_TEMP_TABLES:
                q = "truncate %s" % quote_fqident(temp)
            else:
                # fscking problems with long-lived temp tables
                q = "drop table %s" % quote_fqident(temp)
            self.log.debug(q)
            curs.execute(q)

        self.reset()

    def create_temp_table(self, curs):
        # create temp table for loading
        tempname = self.table_name.replace('.', '_') + "_loadertmp"

        # check if exists
        if USE_LONGLIVED_TEMP_TABLES:
            if skytools.exists_temp_table(curs, tempname):
                self.log.debug("Using existing temp table %s", tempname)
                return tempname

        # bizgres crashes on delete rows
        arg = "on commit delete rows"
        arg = "on commit preserve rows"
        # create temp table for loading
        q = "create temp table %s (like %s) %s" % (
                quote_fqident(tempname), quote_fqident(self.table_name), arg)
        self.log.debug("Creating temp table: %s", q)
        curs.execute(q)
        return tempname

    def find_dist_fields(self, curs):
        if not skytools.exists_table(curs, "pg_catalog.mpp_distribution_policy"):
            return []
        schema, name = skytools.fq_name_parts(self.table_name)
        q = "select a.attname"\
            "  from pg_class t, pg_namespace n, pg_attribute a,"\
            "       mpp_distribution_policy p"\
            " where n.oid = t.relnamespace"\
            "   and p.localoid = t.oid"\
            "   and a.attrelid = t.oid"\
            "   and a.attnum = any(p.attrnums)"\
            "   and n.nspname = %s and t.relname = %s"
        curs.execute(q, [schema, name])
        res = []
        for row in curs.fetchall():
            res.append(row[0])
        return res


class TableHandler:
    """Basic partitioned loader.
    Splits events into partitions, if requested.
    Then applies them without further processing.
    """
    def __init__(self, rowhandler, table_name, table_mode, cf, log):
        self.part_map = {}
        self.rowhandler = rowhandler
        self.table_name = table_name
        self.quoted_name = quote_fqident(table_name)
        self.log = log
        if table_mode == 'direct':
            self.split = False
        elif table_mode == 'split':
            self.split = True
            smode = cf.get('split_mode', 'by-batch-time')
            sfield = None
            if smode.find(':') > 0:
                smode, sfield = smode.split(':', 1)
            self.split_field = sfield
            self.split_part = cf.get('split_part', '%(table_name)s_%(year)s_%(month)s_%(day)s')
            self.split_part_template = cf.get('split_part_template', '')
            if smode == 'by-batch-time':
                self.split_format = self.split_date_from_batch
            elif smode == 'by-event-time':
                self.split_format = self.split_date_from_event
            elif smode == 'by-date-field':
                self.split_format = self.split_date_from_field
            else:
                raise UsageError('Bad value for split_mode: '+smode)
            self.log.debug("%s: split_mode=%s, split_field=%s, split_part=%s",
                    self.table_name, smode, self.split_field, self.split_part)
        elif table_mode == 'ignore':
            pass
        else:
            raise UsageError('Bad value for table_mode: '+table_mode)

    def split_date_from_batch(self, ev, data, batch_info):
        d = batch_info['batch_end']
        vals = {
            'table_name': self.table_name,
            'year': "%04d" % d.year,
            'month': "%02d" % d.month,
            'day': "%02d" % d.day,
            'hour': "%02d" % d.hour,
        }
        dst = self.split_part % vals
        return dst

    def split_date_from_event(self, ev, data, batch_info):
        d = ev.ev_date
        vals = {
            'table_name': self.table_name,
            'year': "%04d" % d.year,
            'month': "%02d" % d.month,
            'day': "%02d" % d.day,
            'hour': "%02d" % d.hour,
        }
        dst = self.split_part % vals
        return dst

    def split_date_from_field(self, ev, data, batch_info):
        val = data[self.split_field]
        date, time = val.split(' ', 1)
        y, m, d = date.split('-')
        h, rest = time.split(':', 1)
        vals = {
            'table_name': self.table_name,
            'year': y,
            'month': m,
            'day': d,
            'hour': h,
        }
        dst = self.split_part % vals
        return dst

    def add(self, curs, ev, batch_info):
        data = skytools.db_urldecode(ev.data)
        op, pkeys = ev.type.split(':', 1)
        pkey_list = pkeys.split(',')
        if self.split:
            dst = self.split_format(ev, data, batch_info)
            if dst not in self.part_map:
                self.check_part(curs, dst, pkey_list)
        else:
            dst = self.table_name

        if dst not in self.part_map:
            self.part_map[dst] = self.rowhandler(dst, self.table_name, self.log)

        p = self.part_map[dst]
        p.add_row(op, data, pkey_list)

    def flush(self, curs):
        for part in self.part_map.values():
            part.flush(curs)

    def check_part(self, curs, dst, pkey_list):
        if skytools.exists_table(curs, dst):
            return
        if not self.split_part_template:
            raise UsageError('Partition %s does not exist and split_part_template not specified' % dst)

        vals = {
            'dest': quote_fqident(dst),
            'part': quote_fqident(dst),
            'parent': quote_fqident(self.table_name),
            'pkey': ",".join(pkey_list), # quoting?
        }
        sql = self.split_part_template % vals
        curs.execute(sql)


class IgnoreTable(TableHandler):
    """Do-nothing."""
    def add(self, curs, ev, batch_info):
        pass


class QueueLoader(CascadedWorker):
    """Loader script."""
    table_state = {}

    def reset(self):
        """Drop our caches on error."""
        self.table_state = {}
        CascadedWorker.reset(self)

    def init_state(self, tbl):
        cf = self.cf
        if tbl in cf.cf.sections():
            cf = cf.clone(tbl)
        table_mode = cf.get('table_mode', 'ignore')
        row_mode = cf.get('row_mode', 'plain')
        if table_mode == 'ignore':
            tblhandler = IgnoreTable
        else:
            tblhandler = TableHandler

        if row_mode == 'plain':
            rowhandler = BasicLoader
        elif row_mode == 'keep_latest':
            rowhandler = KeepLatestLoader
        elif row_mode == 'keep_all':
            rowhandler = KeepAllLoader
        elif row_mode == 'bulk':
            rowhandler = BulkLoader
        else:
            raise UsageError('Bad row_mode: '+row_mode)
        self.table_state[tbl] = tblhandler(rowhandler, tbl, table_mode, cf, self.log)

    def process_remote_event(self, src_curs, dst_curs, ev):
        t = ev.type[:2]
        if t not in ('I:', 'U:', 'D:'):
            CascadedWorker.process_remote_event(self, src_curs, dst_curs, ev)
            return

        tbl = ev.extra1
        if tbl not in self.table_state:
            self.init_state(tbl)
        st = self.table_state[tbl]
        st.add(dst_curs, ev, self._batch_info)

    def finish_remote_batch(self, src_db, dst_db, tick_id):
        curs = dst_db.cursor()
        for st in self.table_state.values():
            st.flush(curs)
        CascadedWorker.finish_remote_batch(self, src_db, dst_db, tick_id)


if __name__ == '__main__':
    script = QueueLoader('queue_loader', 'db', sys.argv[1:])
    script.start()


########NEW FILE########
__FILENAME__ = queue_mover
#! /usr/bin/env python

"""This script simply mover events from one queue to another.

Config parameters::

    ## Parameters for queue_mover

    src_db            = dbname=sourcedb
    dst_db            = dbname=targetdb

    dst_queue_name    = dest_queue
"""

import sys, os

import pkgloader
pkgloader.require('skytools', '3.0')

import pgq

class QueueMover(pgq.SerialConsumer):
    __doc__ = __doc__
    
    def __init__(self, args):
        pgq.SerialConsumer.__init__(self, "queue_mover3", "src_db", "dst_db", args)
        self.dst_queue_name = self.cf.get("dst_queue_name")

    def process_remote_batch(self, db, batch_id, ev_list, dst_db):

        # load data
        rows = []
        for ev in ev_list:
            data = [ev.type, ev.data, ev.extra1, ev.extra2, ev.extra3, ev.extra4, ev.time]
            rows.append(data)
        fields = ['type', 'data', 'extra1', 'extra2', 'extra3', 'extra4', 'time']

        # insert data
        curs = dst_db.cursor()
        pgq.bulk_insert_events(curs, rows, fields, self.dst_queue_name)

if __name__ == '__main__':
    script = QueueMover(sys.argv[1:])
    script.start()


########NEW FILE########
__FILENAME__ = queue_splitter
#! /usr/bin/env python

"""Puts events into queue specified by field from 'queue_field' config parameter.

Config parameters::

    ## Parameters for queue_splitter

    # database locations
    src_db            = dbname=sourcedb_test
    dst_db            = dbname=destdb_test

    # event fields from  where target queue name is read
    #queue_field       = extra1
"""

import sys

import pkgloader
pkgloader.require('skytools', '3.0')

import pgq

class QueueSplitter(pgq.SerialConsumer):
    __doc__ = __doc__

    def __init__(self, args):
        pgq.SerialConsumer.__init__(self, "queue_splitter3", "src_db", "dst_db", args)

    def process_remote_batch(self, db, batch_id, ev_list, dst_db):
        cache = {}
        queue_field = self.cf.get('queue_field', 'extra1')
        for ev in ev_list:
            row = [ev.type, ev.data, ev.extra1, ev.extra2, ev.extra3, ev.extra4, ev.time]
            queue = ev.__getattr__(queue_field)
            if queue not in cache:
                cache[queue] = []
            cache[queue].append(row)

        # should match the composed row
        fields = ['type', 'data', 'extra1', 'extra2', 'extra3', 'extra4', 'time']

        # now send them to right queues
        curs = dst_db.cursor()
        for queue, rows in cache.items():
            pgq.bulk_insert_events(curs, rows, fields, queue)

if __name__ == '__main__':
    script = QueueSplitter(sys.argv[1:])
    script.start()


########NEW FILE########
__FILENAME__ = scriptmgr
#! /usr/bin/env python

"""Bulk start/stop of scripts.

Reads a bunch of config files and maps them to scripts, then handles those.

Config template:

    [scriptmgr]
    job_name = scriptmgr_cphdb5
    config_list = ~/random/conf/*.ini
    logfile = ~/log/%(job_name)s.log
    pidfile = ~/pid/%(job_name)s.pid
    #use_skylog = 1

    # defaults for services
    [DEFAULT]
    cwd = ~/
    args = -v

    # service descriptions

    [cube_dispatcher]
    script = cube_dispatcher.py

    [table_dispatcher]
    script = table_dispatcher.py

    [bulk_loader]
    script = bulk_loader.py

    [londiste]
    script = londiste.py
    args = replay

    [pgqadm]
    script = pgqadm.py
    args = ticker

    # services to be ignored

    [log_checker]
    disabled = 1
"""

import sys, os, signal, glob, ConfigParser, time

import pkgloader
pkgloader.require('skytools', '3.0')
import skytools

try:
    import pwd
except ImportError:
    pwd = None

command_usage = """
%prog [options] INI CMD [subcmd args]

Commands:
  start -a | -t=service | jobname [...]    start job(s)
  stop -a | -t=service | jobname [...]     stop job(s)
  restart -a | -t=service | jobname [...]  restart job(s)
  reload -a | -t=service | jobname [...]   send reload signal
  status [-a | -t=service | jobname ...]
"""

def job_sort_cmp(j1, j2):
    d1 = j1['service'] + j1['job_name']
    d2 = j2['service'] + j2['job_name']
    if d1 < d2: return -1
    elif d1 > d2: return 1
    else: return 0

def launch_cmd(job, cmd):
    if job['user']:
        cmd = 'sudo -nH -u "%s" %s' % (job['user'], cmd)
    return os.system(cmd)

def full_path(job, fn):
    """Like os.path.expanduser() but works for other users.
    """
    if not fn:
        return fn
    if fn[0] == '~':
        if fn.find('/') > 0:
            user, rest = fn.split('/',1)
        else:
            user = fn
            rest = ''

        user = user[1:]
        if not user:
            user = job['user']

        # find home
        if user:
            home = pwd.getpwnam(user).pw_dir
        elif 'HOME' in os.environ:
            home = os.environ['HOME']
        else:
            home = os.pwd.getpwuid(os.getuid()).pw_dir

        if rest:
            return os.path.join(home, rest)
        else:
            return home
    # always return full path
    return os.path.join(job['cwd'], fn)

class ScriptMgr(skytools.DBScript):
    __doc__ = __doc__
    svc_list = []
    svc_map = {}
    config_list = []
    job_map = {}
    job_list = []
    def init_optparse(self, p = None):
        p = skytools.DBScript.init_optparse(self, p)
        p.add_option("-a", "--all", action="store_true", help="apply command to all jobs")
        p.add_option("-t", "--type", action="store", metavar="SVC", help="apply command to all jobs of this service type")
        p.add_option("-w", "--wait", action="store_true", help="wait for job(s) after signaling")
        p.set_usage(command_usage.strip())
        return p

    def load_jobs(self):
        self.svc_list = []
        self.svc_map = {}
        self.config_list = []

        # load services
        svc_list = self.cf.sections()
        svc_list.remove(self.service_name)
        with_user = 0
        without_user = 0
        for svc_name in svc_list:
            cf = self.cf.clone(svc_name)
            disabled = cf.getboolean('disabled', 0)
            defscript = None
            if disabled:
                defscript = '/disabled'
            svc = {
                'service': svc_name,
                'script': cf.getfile('script', defscript),
                'cwd': cf.getfile('cwd'),
                'disabled': disabled,
                'args': cf.get('args', ''),
                'user': cf.get('user', ''),
            }
            if svc['user']:
                with_user += 1
            else:
                without_user += 1
            self.svc_list.append(svc)
            self.svc_map[svc_name] = svc
        if with_user and without_user:
            raise skytools.UsageError("Invalid config - some jobs have user=, some don't")

        # generate config list
        for tmp in self.cf.getlist('config_list'):
            tmp = os.path.expanduser(tmp)
            tmp = os.path.expandvars(tmp)
            for fn in glob.glob(tmp):
                self.config_list.append(fn)

        # read jobs
        for fn in self.config_list:
            raw = ConfigParser.SafeConfigParser({'job_name':'?', 'service_name':'?'})
            raw.read(fn)

            # skip its own config
            if raw.has_section(self.service_name):
                continue

            got = 0
            for sect in raw.sections():
                if sect in self.svc_map:
                    got = 1
                    self.add_job(fn, sect)
            if not got:
                self.log.warning('Cannot find service for %s', fn)

    def add_job(self, cf_file, service_name):
        svc = self.svc_map[service_name]
        cf = skytools.Config(service_name, cf_file)
        disabled = svc['disabled']
        if not disabled:
            disabled = cf.getboolean('disabled', 0)
        job = {
            'disabled': disabled,
            'config': cf_file,
            'cwd': svc['cwd'],
            'script': svc['script'],
            'args': svc['args'],
            'user': svc['user'],
            'service': svc['service'],
            'job_name': cf.get('job_name'),
            'pidfile': cf.get('pidfile', ''),
        }

        if job['pidfile']:
            job['pidfile'] = full_path(job, job['pidfile'])

        self.job_list.append(job)
        self.job_map[job['job_name']] = job

    def cmd_status (self, jobs):
        for jn in jobs:
            try:
                job = self.job_map[jn]
            except KeyError:
                self.log.error ("Unknown job: %s", jn)
                continue
            pidfile = job['pidfile']
            name = job['job_name']
            svc = job['service']
            if job['disabled']:
                name += "  (disabled)"

            if not pidfile:
                print(" pidfile? [%s] %s" % (svc, name))
            elif os.path.isfile(pidfile):
                print(" OK       [%s] %s" % (svc, name))
            else:
                print(" STOPPED  [%s] %s" % (svc, name))

    def cmd_info (self, jobs):
        for jn in jobs:
            try:
                job = self.job_map[jn]
            except KeyError:
                self.log.error ("Unknown job: %s", jn)
                continue
            print(job)

    def cmd_start(self, job_name):
        job = self.get_job_by_name (job_name)
        if isinstance (job, int):
            return job # ret.code
        self.log.info('Starting %s', job_name)
        pidfile = job['pidfile']
        if not pidfile:
            self.log.warning("No pidfile for %s, cannot launch", job_name)
            return 0
        if os.path.isfile(pidfile):
            if skytools.signal_pidfile(pidfile, 0):
                self.log.warning("Script %s seems running", job_name)
                return 0
            else:
                self.log.info("Ignoring stale pidfile for %s", job_name)
        os.chdir(job['cwd'])
        cmd = "%(script)s %(config)s %(args)s -d" % job
        res = launch_cmd(job, cmd)
        self.log.debug(res)
        if res != 0:
            self.log.error('startup failed: %s', job_name)
            return 1
        else:
            return 0

    def cmd_stop(self, job_name):
        job = self.get_job_by_name (job_name)
        if isinstance (job, int):
            return job # ret.code
        self.log.info('Stopping %s', job_name)
        self.signal_job(job, signal.SIGINT)

    def cmd_reload(self, job_name):
        job = self.get_job_by_name (job_name)
        if isinstance (job, int):
            return job # ret.code
        self.log.info('Reloading %s', job_name)
        self.signal_job(job, signal.SIGHUP)

    def get_job_by_name (self, job_name):
        if job_name not in self.job_map:
            self.log.error ("Unknown job: %s", job_name)
            return 1
        job = self.job_map[job_name]
        if job['disabled']:
            self.log.info ("Skipping %s", job_name)
            return 0
        return job

    def wait_for_stop (self, job_name):
        job = self.get_job_by_name (job_name)
        if isinstance (job, int):
            return job # ret.code
        msg = False
        while True:
            if skytools.signal_pidfile (job['pidfile'], 0):
                if not msg:
                    self.log.info ("Waiting for %s to stop", job_name)
                    msg = True
                time.sleep (0.1)
            else:
                return 0

    def signal_job(self, job, sig):
        pidfile = job['pidfile']
        if not pidfile:
            self.log.warning("No pidfile for %s (%s)", job['job_name'], job['config'])
            return
        if os.path.isfile(pidfile):
            pid = int(open(pidfile).read())
            if job['user']:
                # run sudo + kill to avoid killing unrelated processes
                res = os.system("sudo -u %s kill %d" % (job['user'], pid))
                if res:
                    self.log.warning("Signaling %s failed", job['job_name'])
            else:
                # direct kill
                try:
                    os.kill(pid, sig)
                except Exception, det:
                    self.log.warning("Signaling %s failed: %s", job['job_name'], det)
        else:
            self.log.warning("Job %s not running", job['job_name'])

    def work(self):
        self.set_single_loop(1)
        self.job_list = []
        self.job_map = {}
        self.load_jobs()
        self.job_list.sort(job_sort_cmp)

        if len(self.args) < 2:
            print("need command")
            sys.exit(1)

        cmd = self.args[1]
        jobs = self.args[2:]

        if cmd in ["status", "info"] and len(jobs) == 0 and not self.options.type:
            self.options.all = True

        if len(jobs) == 0 and self.options.all:
            for job in self.job_list:
                jobs.append(job['job_name'])
        if len(jobs) == 0 and self.options.type:
            for job in self.job_list:
                if job['service'] == self.options.type:
                    jobs.append(job['job_name'])

        if cmd == "status":
            self.cmd_status(jobs)
            return
        elif cmd == "info":
            self.cmd_info(jobs)
            return

        if len(jobs) == 0:
            print("no jobs given?")
            sys.exit(1)

        if cmd == "start":
            err = 0
            for n in jobs:
                err += self.cmd_start(n)
            if err > 0:
                self.log.error('some scripts failed')
                sys.exit(1)
        elif cmd == "stop":
            for n in jobs:
                self.cmd_stop(n)
            if self.options.wait:
                for n in jobs:
                    self.wait_for_stop(n)
        elif cmd == "restart":
            for n in jobs:
                self.cmd_stop(n)
            if self.options.wait:
                for n in jobs:
                    self.wait_for_stop(n)
            else:
                time.sleep(2)
            for n in jobs:
                self.cmd_start(n)
        elif cmd == "reload":
            for n in jobs:
                self.cmd_reload(n)
        else:
            print("unknown command: " + cmd)
            sys.exit(1)

if __name__ == '__main__':
    script = ScriptMgr('scriptmgr', sys.argv[1:])
    script.start()

########NEW FILE########
__FILENAME__ = simple_consumer
#!/usr/bin/env python

"""Consumer that simply calls SQL query for each event.

Config::
    # source database
    src_db =

    # destination database
    dst_db =

    # query to call
    dst_query = select * from somefunc(%%(pgq.ev_data)s);

    ## Deprecated, use table_filter ##
    # filter for events (SQL fragment)
    consumer_filter = ev_extra1 = 'public.mytable1'
"""


import sys

import pkgloader
pkgloader.require('skytools', '3.0')

import pgq
import skytools

class SimpleConsumer(pgq.Consumer):
    __doc__ = __doc__

    def reload(self):
        super(SimpleConsumer, self).reload()
        self.dst_query = self.cf.get("dst_query")
        if self.cf.get("consumer_filter", ""):
            self.consumer_filter = self.cf.get("consumer_filter", "")

    def process_event(self, db, ev):
        curs = self.get_database('dst_db', autocommit = 1).cursor()

        if ev.ev_type[:2] not in ('I:', 'U:', 'D:'):
            return

        if ev.ev_data is None:
            payload = {}
        else:
            payload = skytools.db_urldecode(ev.ev_data)
        payload['pgq.tick_id'] = self.batch_info['cur_tick_id']
        payload['pgq.ev_id'] = ev.ev_id
        payload['pgq.ev_time'] = ev.ev_time
        payload['pgq.ev_type'] = ev.ev_type
        payload['pgq.ev_data'] = ev.ev_data
        payload['pgq.ev_extra1'] = ev.ev_extra1
        payload['pgq.ev_extra2'] = ev.ev_extra2
        payload['pgq.ev_extra3'] = ev.ev_extra3
        payload['pgq.ev_extra4'] = ev.ev_extra4

        self.log.debug(self.dst_query, payload)
        curs.execute(self.dst_query, payload)
        if curs.statusmessage[:6] == 'SELECT':
            res = curs.fetchall()
            self.log.debug(res)
        else:
            self.log.debug(curs.statusmessage)

if __name__ == '__main__':
    script = SimpleConsumer("simple_consumer3", "src_db", sys.argv[1:])
    script.start()

########NEW FILE########
__FILENAME__ = simple_local_consumer
#!/usr/bin/env python

"""Consumer that simply calls SQL query for each event.

It tracks completed batches in local file.

Config::
    # source database
    src_db =

    # destination database
    dst_db =

    # query to call
    dst_query = select * from somefunc(%%(pgq.ev_data)s);

    ## Use table_filter where possible instead of this ##
    # filter for events (SQL fragment)
    consumer_filter = ev_extra1 = 'public.mytable1'
"""


import sys

import pkgloader
pkgloader.require('skytools', '3.0')

import pgq
import skytools

class SimpleLocalConsumer(pgq.LocalConsumer):
    __doc__ = __doc__

    def reload(self):
        super(SimpleLocalConsumer, self).reload()
        self.dst_query = self.cf.get("dst_query")
        if self.cf.get("consumer_filter", ""):
            self.consumer_filter = self.cf.get("consumer_filter", "")

    def process_local_event(self, db, batch_id, ev):
        if ev.ev_type[:2] not in ('I:', 'U:', 'D:'):
            return

        if ev.ev_data is None:
            payload = {}
        else:
            payload = skytools.db_urldecode(ev.ev_data)

        payload['pgq.tick_id'] = self.batch_info['cur_tick_id']
        payload['pgq.ev_id'] = ev.ev_id
        payload['pgq.ev_time'] = ev.ev_time
        payload['pgq.ev_type'] = ev.ev_type
        payload['pgq.ev_data'] = ev.ev_data
        payload['pgq.ev_extra1'] = ev.ev_extra1
        payload['pgq.ev_extra2'] = ev.ev_extra2
        payload['pgq.ev_extra3'] = ev.ev_extra3
        payload['pgq.ev_extra4'] = ev.ev_extra4

        self.log.debug(self.dst_query, payload)
        retries, curs = self.execute_with_retry('dst_db', self.dst_query, payload)
        if curs.statusmessage[:6] == 'SELECT':
            res = curs.fetchall()
            self.log.debug(res)
        else:
            self.log.debug(curs.statusmessage)

if __name__ == '__main__':
    script = SimpleLocalConsumer("simple_local_consumer3", "src_db", sys.argv[1:])
    script.start()

########NEW FILE########
__FILENAME__ = skytools_upgrade
#! /usr/bin/env python

"""Upgrade script for versioned schemas."""

usage = """
    %prog [--user=U] [--host=H] [--port=P] --all
    %prog [--user=U] [--host=H] [--port=P] DB1 [ DB2 ... ]\
"""

import sys, os, re, optparse

import pkgloader
pkgloader.require('skytools', '3.0')
import skytools
from skytools.natsort import natsort_key


# schemas, where .upgrade.sql is enough
AUTO_UPGRADE = ('pgq', 'pgq_node', 'pgq_coop', 'londiste', 'pgq_ext')

# fetch list of databases
DB_LIST = "select datname from pg_database "\
          " where not datistemplate and datallowconn "\
          " order by 1"

# dont support upgrade from 2.x (yet?)
version_list = [
    # schema, ver, filename, recheck_func
    ['pgq', '3.0', None, None],
    ['londiste', '3.0', None, None],
    ['pgq_ext', '2.1', None, None],
]


def is_version_ge(a, b):
    """Return True if a is greater or equal than b."""
    va = natsort_key(a)
    vb = natsort_key(b)
    return va >= vb

def is_version_gt(a, b):
    """Return True if a is greater than b."""
    va = natsort_key(a)
    vb = natsort_key(b)
    return va > vb


def check_version(curs, schema, new_ver_str, recheck_func=None, force_gt=False):
    funcname = "%s.version" % schema
    if not skytools.exists_function(curs, funcname, 0):
        if recheck_func is not None:
            return recheck_func(curs), 'NULL'
        else:
            return 0, 'NULL'
    q = "select %s()" % funcname
    curs.execute(q)
    old_ver_str = curs.fetchone()[0]
    if force_gt:
        ok = is_version_gt(old_ver_str, new_ver_str)
    else:
        ok = is_version_ge(old_ver_str, new_ver_str)
    return ok, old_ver_str


class DbUpgrade(skytools.DBScript):
    """Upgrade all Skytools schemas in Postgres cluster."""

    def upgrade(self, dbname, db):
        """Upgrade all schemas in single db."""

        curs = db.cursor()
        ignore = {}
        for schema, ver, fn, recheck_func in version_list:
            # skip schema?
            if schema in ignore:
                continue
            if not skytools.exists_schema(curs, schema):
                ignore[schema] = 1
                continue

            # new enough?
            ok, oldver = check_version(curs, schema, ver, recheck_func, self.options.force)
            if ok:
                continue

            # too old schema, no way to upgrade
            if fn is None:
                self.log.info('%s: Cannot upgrade %s, too old version', dbname, schema)
                ignore[schema] = 1
                continue

            if self.options.not_really:
                self.log.info ("%s: Would upgrade '%s' version %s to %s", dbname, schema, oldver, ver)
                continue

            curs = db.cursor()
            curs.execute('begin')
            self.log.info("%s: Upgrading '%s' version %s to %s", dbname, schema, oldver, ver)
            skytools.installer_apply_file(db, fn, self.log)
            curs.execute('commit')

    def work(self):
        """Loop over databases."""

        self.set_single_loop(1)

        self.load_cur_versions()

        # loop over all dbs
        dblst = self.args
        if self.options.all:
            db = self.connect_db('postgres')
            curs = db.cursor()
            curs.execute(DB_LIST)
            dblst = []
            for row in curs.fetchall():
                dblst.append(row[0])
            self.close_database('db')
        elif not dblst:
            raise skytools.UsageError('Give --all or list of database names on command line')

        # loop over connstrs
        for dbname in dblst:
            if self.last_sigint:
                break
            self.log.info("%s: connecting", dbname)
            db = self.connect_db(dbname)
            self.upgrade(dbname, db)
            self.close_database('db')

    def load_cur_versions(self):
        """Load current version numbers from .upgrade.sql files."""

        vrc = re.compile(r"^ \s+ return \s+ '([0-9.]+)';", re.X | re.I | re.M)
        for s in AUTO_UPGRADE:
            fn = '%s.upgrade.sql' % s
            fqfn = skytools.installer_find_file(fn)
            try:
                f = open(fqfn, 'r')
            except IOError, d:
                raise skytools.UsageError('%s: cannot find upgrade file: %s [%s]' % (s, fqfn, str(d)))

            sql = f.read()
            f.close()
            m = vrc.search(sql)
            if not m:
                raise skytools.UsageError('%s: failed to detect version' % fqfn)

            ver = m.group(1)
            cur = [s, ver, fn, None]
            self.log.info("Loaded %s %s from %s", s, ver, fqfn)
            version_list.append(cur)

    def connect_db(self, dbname):
        """Create connect string, then connect."""

        elems = ["dbname='%s'" % dbname]
        if self.options.host:
            elems.append("host='%s'" % self.options.host)
        if self.options.port:
            elems.append("port='%s'" % self.options.port)
        if self.options.user:
            elems.append("user='%s'" % self.options.user)
        cstr = ' '.join(elems)
        return self.get_database('db', connstr = cstr, autocommit = 1)

    def init_optparse(self, parser=None):
        """Setup command-line flags."""
        p = skytools.DBScript.init_optparse(self, parser)
        p.set_usage(usage)
        g = optparse.OptionGroup(p, "options for skytools_upgrade")
        g.add_option("--all", action="store_true", help = 'upgrade all databases')
        g.add_option("--not-really", action = "store_true", dest = "not_really",
                     default = False, help = "don't actually do anything")
        g.add_option("--user", help = 'username to use')
        g.add_option("--host", help = 'hostname to use')
        g.add_option("--port", help = 'port to use')
        g.add_option("--force", action = "store_true",
                     help = 'upgrade even if schema versions are new enough')
        p.add_option_group(g)
        return p

    def load_config(self):
        """Disable config file."""
        return skytools.Config(self.service_name, None,
                user_defs = {'use_skylog': '0', 'job_name': 'db_upgrade'})

if __name__ == '__main__':
    script = DbUpgrade('skytools_upgrade', sys.argv[1:])
    script.start()

########NEW FILE########
__FILENAME__ = plainconsumer
#! /usr/bin/env python

import sys, time, skytools

from pgq.cascade.consumer import CascadedConsumer

class PlainCascadedConsumer(CascadedConsumer):
    def process_remote_event(self, src_curs, dst_curs, ev):
        ev.tag_done()

if __name__ == '__main__':
    script = PlainCascadedConsumer('nop_consumer', 'dst_db', sys.argv[1:])
    script.start()


########NEW FILE########
__FILENAME__ = plainworker
#! /usr/bin/env python

import sys, time, skytools

from pgq.cascade.worker import CascadedWorker

class PlainCascadedWorker(CascadedWorker):
    def process_remote_event(self, src_curs, dst_curs, ev):
        self.log.info("got events: %s / %s" % (ev.ev_type, ev.ev_data))
        ev.tag_done()

if __name__ == '__main__':
    script = PlainCascadedWorker('nop_worker', 'dst_db', sys.argv[1:])
    script.start()


########NEW FILE########
__FILENAME__ = testconsumer
#! /usr/bin/env python

import sys, time, skytools, pgq

class TestLocalConsumer(pgq.LocalConsumer):
    def process_local_event(self, src_db, batch_id, ev):
        self.log.info("event: type=%s data=%s", ev.type, ev.data)

if __name__ == '__main__':
    script = TestLocalConsumer('testconsumer', 'db', sys.argv[1:])
    script.start()


########NEW FILE########
__FILENAME__ = loadgen
#! /usr/bin/env python

import sys

import pkgloader
pkgloader.require('skytools', '3.0')
import skytools

class LoadGen(skytools.DBScript):
    seq = 1
    def work(self):
        db = self.get_database('db', autocommit = 1)
        curs = db.cursor()
        data = 'data %d' % self.seq
        curs.execute('insert into mytable (data) values (%s)', [data])
        self.seq += 1

if __name__ == '__main__':
    script = LoadGen('loadgen', sys.argv[1:])
    script.start()


########NEW FILE########
__FILENAME__ = regtest
#! /usr/bin/env python

import sys, time
import skytools.psycopgwrapper
import skytools._cquoting, skytools._pyquoting
from decimal import Decimal

# create a DictCursor row
class fake_cursor:
    index = {'id': 0, 'data': 1}
    description = ['x', 'x']
dbrow = skytools.psycopgwrapper._CompatRow(fake_cursor())
dbrow[0] = '123'
dbrow[1] = 'value'

def regtest(name, func, cases):
    bad = 0
    for dat, res in cases:
        res2 = func(dat)
        if res != res2:
            print("failure: %s(%s) = %s (expected %s)" % (name, repr(dat), repr(res2), repr(res)))
            bad += 1
    if bad:
        print("%-20s: failed" % name)
    else:
        print("%-20s: OK" % name)
            

sql_literal = [
    [None, "null"],
    ["", "''"],
    ["a'b", "'a''b'"],
    [r"a\'b", r"E'a\\''b'"],
    [1, "'1'"],
    [True, "'True'"],
    [Decimal(1), "'1'"],
]
regtest("quote_literal/c", skytools._cquoting.quote_literal, sql_literal)
regtest("quote_literal/py", skytools._pyquoting.quote_literal, sql_literal)

sql_copy = [
    [None, "\\N"],
    ["", ""],
    ["a'\tb", "a'\\tb"],
    [r"a\'b", r"a\\'b"],
    [1, "1"],
    [True, "True"],
    [u"qwe", "qwe"],
    [Decimal(1), "1"],
]
regtest("quote_copy/c", skytools._cquoting.quote_copy, sql_copy)
regtest("quote_copy/py", skytools._pyquoting.quote_copy, sql_copy)

sql_bytea_raw = [
    [None, None],
    ["", ""],
    ["a'\tb", "a'\\011b"],
    [r"a\'b", r"a\\'b"],
    ["\t\344", r"\011\344"],
]
regtest("quote_bytea_raw/c", skytools._cquoting.quote_bytea_raw, sql_bytea_raw)
regtest("quote_bytea_raw/py", skytools._pyquoting.quote_bytea_raw, sql_bytea_raw)

sql_ident = [
    ["", ""],
    ["a'\t\\\"b", '"a\'\t\\""b"'],
    ['abc_19', 'abc_19'],
    ['from', '"from"'],
    ['0foo', '"0foo"'],
    ['mixCase', '"mixCase"'],
]
regtest("quote_ident", skytools.quote_ident, sql_ident)

t_urlenc = [
    [{}, ""],
    [{'a': 1}, "a=1"],
    [{'a': None}, "a"],
    [{'qwe': 1, u'zz': u"qwe"}, "qwe=1&zz=qwe"],
    [{'a': '\000%&'}, "a=%00%25%26"],
    [dbrow, 'data=value&id=123'],
    [{'a': Decimal("1")}, "a=1"],
]
regtest("db_urlencode/c", skytools._cquoting.db_urlencode, t_urlenc)
regtest("db_urlencode/py", skytools._pyquoting.db_urlencode, t_urlenc)

t_urldec = [
    ["", {}],
    ["a=b&c", {'a': 'b', 'c': None}],
    ["&&b=f&&", {'b': 'f'}],
    [u"abc=qwe", {'abc': 'qwe'}],
    ["b=", {'b': ''}],
    ["b=%00%45", {'b': '\x00E'}],
]
regtest("db_urldecode/c", skytools._cquoting.db_urldecode, t_urldec)
regtest("db_urldecode/py", skytools._pyquoting.db_urldecode, t_urldec)

t_unesc = [
    ["", ""],
    ["\\N", "N"],
    ["abc", "abc"],
    [u"abc", "abc"],
    [r"\0\000\001\01\1", "\0\000\001\001\001"],
    [r"a\001b\tc\r\n", "a\001b\tc\r\n"],
]
regtest("unescape/c", skytools._cquoting.unescape, t_unesc)
regtest("unescape/py", skytools._pyquoting.unescape, t_unesc)


########NEW FILE########
__FILENAME__ = testconsumer
#! /usr/bin/env python

import sys, pgq

class TestConsumer(pgq.SetConsumer):
    pass

if __name__ == '__main__':
    script = TestConsumer('test_consumer', sys.argv[1:])
    script.start()


########NEW FILE########
__FILENAME__ = logtest
#! /usr/bin/env python

import sys, os, skytools

import skytools.skylog

class LogTest(skytools.DBScript):
    def work(self):
        self.log.error('test error')
        self.log.warning('test warning')
        self.log.info('test info')
        self.log.debug('test debug')

if __name__ == '__main__':
    script = LogTest('log_test', sys.argv[1:])
    script.start()


########NEW FILE########
