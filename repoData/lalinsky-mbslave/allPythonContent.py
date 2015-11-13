__FILENAME__ = config
import ConfigParser


class ConfigSection(object):
    pass


class SolrConfig(object):

    def __init__(self):
        self.enabled = False
        self.url = 'http://localhost:8983/solr/musicbrainz'
        self.index_artists = True
        self.index_labels = True
        self.index_releases = True
        self.index_release_groups = True
        self.index_recordings = True
        self.index_works = True

    def parse(self, parser, section):
        if parser.has_option(section, 'enabled'):
            self.enabled = parser.getboolean(section, 'enabled')
        if parser.has_option(section, 'url'):
            self.url = parser.get(section, 'url').rstrip('/')
        for name in ('artists', 'labels', 'releases', 'release_groups', 'recordings', 'works'):
            key = 'index_%s' % name
            if parser.has_option(section, key):
                setattr(self, key, parser.getboolean(section, key))


class MonitoringConfig(object):

    def __init__(self):
        self.enabled = False
        self.status_file = '/tmp/mbslave-status.xml'

    def parse(self, parser, section):
        if parser.has_option(section, 'enabled'):
            self.enabled = parser.getboolean(section, 'enabled')
        if parser.has_option(section, 'status_file'):
            self.status_file = parser.get(section, 'status_file')


class SchemasConfig(object):

    def __init__(self):
        self.mapping = {}

    def name(self, name):
        return self.mapping.get(name, name)

    def parse(self, parser, section):
        for name, value in parser.items(section):
            self.mapping[name] = value


class Config(object):

    def __init__(self, path):
        self.path = path
        self.cfg = ConfigParser.RawConfigParser()
        self.cfg.read(self.path)
        self.get = self.cfg.get
        self.has_option = self.cfg.has_option
        self.database = ConfigSection()
        self.solr = SolrConfig()
        if self.cfg.has_section('solr'):
            self.solr.parse(self.cfg, 'solr')
        self.monitoring = MonitoringConfig()
        if self.cfg.has_section('monitoring'):
            self.monitoring.parse(self.cfg, 'monitoring')
        self.schema = SchemasConfig()
        if self.cfg.has_section('schemas'):
            self.schema.parse(self.cfg, 'schemas')

    def make_psql_args(self):
        opts = {}
        opts['database'] = self.cfg.get('DATABASE', 'name')
        opts['user'] = self.cfg.get('DATABASE', 'user')
        if self.cfg.has_option('DATABASE', 'password'):
	        opts['password'] = self.cfg.get('DATABASE', 'password')
        if self.cfg.has_option('DATABASE', 'host'):
	        opts['host'] = self.cfg.get('DATABASE', 'host')
        if self.cfg.has_option('DATABASE', 'port'):
	        opts['port'] = self.cfg.get('DATABASE', 'port')
        return opts


########NEW FILE########
__FILENAME__ = monitoring
import os
from datetime import datetime
from xml.etree.ElementTree import ElementTree, Element, SubElement


def parse_time(s):
    if not s:
        return None
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")


def format_time(d):
    if not d:
        return ''
    return d.strftime("%Y-%m-%d %H:%M:%S")


class StatusReport(object):

    def __init__(self, schema_seq=None, replication_seq=None):
        self.schema_seq = schema_seq
        self.replication_seq = replication_seq
        self.last_replication_time = None
        self.last_finished_time = None

    def end(self):
        self.last_finished_time = datetime.now()

    def update(self, replication_seq):
        self.last_replication_time = datetime.now()
        self.replication_seq = replication_seq

    def load(self, path):
        if not os.path.exists(path):
            return
        tree = ElementTree()
        tree.parse(path)
        self.schema_seq = int(tree.find("schema_seq").text)
        self.replication_seq = int(tree.find("replication_seq").text)
        self.last_replication_time = parse_time(tree.find("last_updated").text)
        self.last_finished_time = parse_time(tree.find("last_finished").text)

    def save(self, path):
        status = Element("status")
        SubElement(status, "schema_seq").text = str(self.schema_seq or 0)
        SubElement(status, "replication_seq").text = str(self.replication_seq or 0)
        SubElement(status, "last_updated").text = format_time(self.last_replication_time)
        SubElement(status, "last_finished").text = format_time(self.last_finished_time)
        tree = ElementTree(status)
        tree.write(path, encoding="UTF-8", xml_declaration=True)



########NEW FILE########
__FILENAME__ = replication

class ReplicationHook(object):

    def __init__(self, cfg, db, schema):
        self.cfg = cfg
        self.db = db
        self.schema = schema

    def begin(self, seq):
        pass

    def after_commit(self):
        pass

    def before_commit(self):
        pass

    def after_commit(self):
        pass

    def before_delete(self, table, keys):
        pass

    def before_update(self, table, keys, values):
        pass

    def before_insert(self, table, values):
        pass

    def after_delete(self, table, keys):
        pass

    def after_update(self, table, keys, values):
        pass

    def after_insert(self, table, values):
        pass


########NEW FILE########
__FILENAME__ = search
import itertools
import urllib2
import psycopg2.extras
from contextlib import closing
from collections import namedtuple
from lxml import etree as ET
from lxml.builder import E

Entity = namedtuple('Entity', ['name', 'fields'])
Field = namedtuple('Field', ['name', 'column'])
MultiField = namedtuple('MultiField', ['name', 'column'])


class Schema(object):

    def __init__(self, entities):
        self.entities = entities
        self.entities_by_id = dict((e.name, e) for e in entities)

    def __getitem__(self, name):
        return self.entities_by_id[name]


class Entity(object):

    def __init__(self, name, fields):
        self.name = name
        self.fields = fields

    def iter_single_fields(self, name=None):
        for field in self.fields:
            if isinstance(field, Field):
                if name is not None and field.name != name:
                    continue
                yield field

    def iter_multi_fields(self, name=None):
        for field in self.fields:
            if isinstance(field, MultiField):
                if name is not None and field.name != name:
                    continue
                yield field


class Column(object):

    def __init__(self, name, foreign=None):
        self.name = name
        self.foreign = foreign


class ForeignColumn(Column):

    def __init__(self, table, name, foreign=None, null=False, backref=None):
        super(ForeignColumn, self).__init__(name, foreign=foreign)
        self.table = table
        self.null = null
        self.backref = backref


schema = Schema([
    Entity('artist', [
        Field('mbid', Column('gid')),
        Field('disambiguation', Column('comment')),
        Field('name', Column('name', ForeignColumn('artist_name', 'name'))),
        Field('sort_name', Column('sort_name', ForeignColumn('artist_name', 'name'))),
        Field('country', Column('country', ForeignColumn('country', 'name', null=True))),
        Field('country', Column('country', ForeignColumn('country', 'iso_code', null=True))),
        Field('gender', Column('gender', ForeignColumn('gender', 'name', null=True))),
        Field('type', Column('type', ForeignColumn('artist_type', 'name', null=True))),
        MultiField('mbid', ForeignColumn('artist_gid_redirect', 'gid', backref='new_id')),
        MultiField('ipi', ForeignColumn('artist_ipi', 'ipi')),
        MultiField('alias', ForeignColumn('artist_alias', 'name', ForeignColumn('artist_name', 'name'))),
    ]),
    Entity('label', [
        Field('mbid', Column('gid')),
        Field('disambiguation', Column('comment')),
        Field('code', Column('label_code')),
        Field('name', Column('name', ForeignColumn('label_name', 'name'))),
        Field('sort_name', Column('sort_name', ForeignColumn('label_name', 'name'))),
        Field('country', Column('country', ForeignColumn('country', 'name', null=True))),
        Field('country', Column('country', ForeignColumn('country', 'iso_code', null=True))),
        Field('type', Column('type', ForeignColumn('label_type', 'name', null=True))),
        MultiField('mbid', ForeignColumn('label_gid_redirect', 'gid', backref='new_id')),
        MultiField('ipi', ForeignColumn('label_ipi', 'ipi')),
        MultiField('alias', ForeignColumn('label_alias', 'name', ForeignColumn('label_name', 'name'))),
    ]),
    Entity('work', [
        Field('mbid', Column('gid')),
        Field('disambiguation', Column('comment')),
        Field('name', Column('name', ForeignColumn('work_name', 'name'))),
        Field('type', Column('type', ForeignColumn('work_type', 'name', null=True))),
        MultiField('mbid', ForeignColumn('work_gid_redirect', 'gid', backref='new_id')),
        MultiField('iswc', ForeignColumn('iswc', 'iswc')),
        MultiField('alias', ForeignColumn('work_alias', 'name', ForeignColumn('work_name', 'name'))),
    ]),
    Entity('release_group', [
        Field('mbid', Column('gid')),
        Field('disambiguation', Column('comment')),
        Field('name', Column('name', ForeignColumn('release_name', 'name'))),
        Field('type', Column('type', ForeignColumn('release_group_primary_type', 'name', null=True))),
        MultiField('mbid', ForeignColumn('release_group_gid_redirect', 'gid', backref='new_id')),
        MultiField('type',
            ForeignColumn('release_group_secondary_type_join', 'secondary_type',
                ForeignColumn('release_group_secondary_type', 'name'))),
        Field('artist', Column('artist_credit', ForeignColumn('artist_credit', 'name', ForeignColumn('artist_name', 'name')))),
        MultiField('alias', ForeignColumn('release', 'name', ForeignColumn('release_name', 'name'))),
    ]),
    Entity('release', [
        Field('mbid', Column('gid')),
        Field('disambiguation', Column('comment')),
        Field('barcode', Column('barcode')),
        Field('name', Column('name', ForeignColumn('release_name', 'name'))),
        Field('status', Column('status', ForeignColumn('release_status', 'name', null=True))),
        Field('type', Column('release_group', ForeignColumn('release_group', 'type', ForeignColumn('release_group_primary_type', 'name', null=True)))),
        Field('artist', Column('artist_credit', ForeignColumn('artist_credit', 'name', ForeignColumn('artist_name', 'name')))),
        Field('country', Column('country', ForeignColumn('country', 'name', null=True))),
        Field('country', Column('country', ForeignColumn('country', 'iso_code', null=True))),
        MultiField('mbid', ForeignColumn('release_gid_redirect', 'gid', backref='new_id')),
        MultiField('catno', ForeignColumn('release_label', 'catalog_number')),
        MultiField('label', ForeignColumn('release_label', 'label', ForeignColumn('label', 'name', ForeignColumn('label_name', 'name')))),
        Field('alias', Column('release_group', ForeignColumn('release_group', 'name', ForeignColumn('release_name', 'name')))),
    ]),
    Entity('recording', [
        Field('mbid', Column('gid')),
        Field('disambiguation', Column('comment')),
        Field('name', Column('name', ForeignColumn('track_name', 'name'))),
        Field('artist', Column('artist_credit', ForeignColumn('artist_credit', 'name', ForeignColumn('artist_name', 'name')))),
        MultiField('mbid', ForeignColumn('recording_gid_redirect', 'gid', backref='new_id')),
        MultiField('alias', ForeignColumn('track', 'name', ForeignColumn('track_name', 'name'))),
    ]),
])


SQL_SELECT_TPL = "SELECT\n%(columns)s\nFROM\n%(joins)s\nORDER BY %(sort_column)s"


SQL_TRIGGER = """
CREATE OR REPLACE FUNCTION mbslave_solr_%(op1)s_%(table)s() RETURNS trigger AS $$
BEGIN
    %(code)s
    RETURN NULL;
END;
$$ LANGUAGE 'plpgsql';

DROP TRIGGER IF EXISTS mbslave_solr_tr_%(op1)s_%(table)s ON musicbrainz.%(table)s;
CREATE TRIGGER mbslave_solr_tr_%(op1)s_%(table)s AFTER %(op2)s ON musicbrainz.%(table)s FOR EACH ROW EXECUTE PROCEDURE mbslave_solr_%(op1)s_%(table)s();
"""


def distinct_values(columns):
    return ' OR\n       '.join('OLD.%(c)s IS DISTINCT FROM NEW.%(c)s' % dict(c=c)
                               for c in columns)


def generate_trigger_update(path):
    condition = None
    for table, column in path[1:]:
        if not condition:
            condition = 'FROM musicbrainz.%s WHERE %s = NEW.id' % (table, column)
        else:
            condition = 'FROM musicbrainz.%s WHERE %s IN (SELECT id %s)' % (table, column, condition)
    return path[0][0], path[0][1], condition


def generate_triggers():
    ins_del_deps = {}
    deps = {}
    for entity in schema.entities:
        for field in entity.iter_single_fields():
            column = field.column
            path = [(entity.name, column.name)]
            while column.foreign:
                column = column.foreign
                path.insert(0, (column.table, column.name))
            for i in range(0, len(path)):
                table, column, values = generate_trigger_update(path[i:])
                deps.setdefault(table, {}).setdefault((entity.name, 'NEW', 'id', values), []).append(column)

        ins_del_deps.setdefault(entity.name, set()).add((entity.name, 'id'))

        for field in entity.iter_multi_fields():
            column = field.column
            backref = field.column.backref or entity.name
            path = []
            while column:
                path.insert(0, (column.table, column.name))
                column = column.foreign
            for i in range(0, len(path)):
                table, column, values = generate_trigger_update(path[i:])
                deps.setdefault(table, {}).setdefault((entity.name, 'NEW', backref, values), []).append(column)

            # Changed parent row
            deps.setdefault(field.column.table, {}).setdefault((entity.name, 'NEW', backref, None), []).append(backref)
            deps.setdefault(field.column.table, {}).setdefault((entity.name, 'OLD', backref, None), []).append(backref)

            # Inserted or deleted new child row
            ins_del_deps.setdefault(field.column.table, set()).add((entity.name, backref))

    for table, kinds in sorted(ins_del_deps.items()):
        sections = []
        for kind, pk in kinds:
            sections.append("INSERT INTO mbslave.mbslave_solr_queue (entity_type, entity_id) VALUES ('%s', NEW.%s);" % (kind, pk))
        code = '\n    '.join(sections)
        yield SQL_TRIGGER % dict(table=table, code=code, op1='ins', op2='INSERT')

    for table, kinds in sorted(ins_del_deps.items()):
        sections = []
        for kind, pk in kinds:
            sections.append("INSERT INTO mbslave.mbslave_solr_queue (entity_type, entity_id) VALUES ('%s', OLD.%s);" % (kind, pk))
        code = '\n    '.join(sections)
        yield SQL_TRIGGER % dict(table=table, code=code, op1='del', op2='DELETE')

    for table, fields in sorted(deps.items()):
        sections = []
        for columns in set(map(tuple, fields.values())):
            inserts = []
            for (kind, ver, pk, values), c in fields.items():
                if columns != tuple(c):
                    continue
                if not values:
                    values = "VALUES ('%s', %s.%s)" % (kind, ver, pk)
                else:
                    values = "SELECT '%s', %s %s" % (kind, pk, values)
                inserts.append("INSERT INTO mbslave.mbslave_solr_queue (entity_type, entity_id) %s;" % values)
            sections.append("IF %s\n    THEN\n        %s\n    END IF;" % (distinct_values(columns), "\n        ".join(inserts)))
        code = '\n    '.join(sections)
        yield SQL_TRIGGER % dict(table=table, code=code, op1='upd', op2='UPDATE')



def generate_iter_query(columns, joins, ids=()):
    id_column = columns[0]
    tpl = ["SELECT", "%(columns)s", "FROM", "%(joins)s"]
    if ids:
        tpl.append("WHERE %(id_column)s IN (%(ids)s)")
    tpl.append("ORDER BY %(id_column)s")
    sql_columns = ',\n'.join('  ' + i for i in columns)
    sql_joins = '\n'.join('  ' + i for i in joins)
    sql = "\n".join(tpl) % dict(columns=sql_columns, joins=sql_joins,
                                id_column=id_column, ids=placeholders(ids))
    return sql


def iter_main(db, kind, ids=()):
    entity = schema[kind]
    joins = [kind]
    tables = set([kind])
    columns = ['%s.id' % (kind,)]
    names = []
    for field in entity.iter_single_fields():
        table = kind
        column = field.column
        while column.foreign is not None:
            foreign_table = table + '__' + column.name + '__' + column.foreign.table
            if foreign_table not in tables:
                join = 'LEFT JOIN' if column.foreign.null else 'JOIN'
                joins.append('%(join)s %(parent)s AS %(label)s ON %(label)s.id = %(child)s.%(child_column)s' % dict(
                    join=join, parent=column.foreign.table, child=table, child_column=column.name, label=foreign_table))
                tables.add(foreign_table)
            table = foreign_table
            column = column.foreign
        columns.append('%s.%s' % (table, column.name))
        names.append(field.name)

    query = generate_iter_query(columns, joins, ids)
    cursor = db.cursor('cursor_' + kind)
    cursor.itersize = 100 * 1000
    cursor.execute(query, ids)
    for row in cursor:
        id = row[0]
        fields = [E.field(kind, name='kind'), E.field('%s:%s' % (kind, id), name='id')]
        for name, value in zip(names, row[1:]):
            if not value:
                continue
            if isinstance(value, str):
                value = value.decode('utf8')
            elif not isinstance(value, unicode):
                value = unicode(value)
            try:
                fields.append(E.field(value, name=name))
            except ValueError:
                continue # XXX
        yield id, fields


def iter_sub(db, kind, subtable, ids=()):
    entity = schema[kind]
    joins = []
    tables = set()
    columns = []
    names = []
    for field in entity.iter_multi_fields():
        if field.column.table != subtable:
            continue
        last_column = column = field.column
        table = column.table
        while True:
            if last_column is column:
                if table not in tables:
                    joins.append(table)
                    tables.add(table)
                    columns.append('%s.%s' % (table, column.backref or kind))
            else:
                foreign_table = table + '__' + last_column.name + '__' + column.table
                if foreign_table not in tables:
                    join = 'LEFT JOIN' if column.null else 'JOIN'
                    joins.append('%(join)s %(parent)s AS %(label)s ON %(label)s.id = %(child)s.%(child_column)s' % dict(
                        join=join, parent=column.table, child=table, child_column=last_column.name, label=foreign_table))
                    tables.add(foreign_table)
                table = foreign_table
            if column.foreign is None:
                break
            last_column = column
            column = column.foreign
        columns.append('%s.%s' % (table, column.name))
        names.append(field.name)

    query = generate_iter_query(columns, joins, ids)
    cursor = db.cursor('cursor_' + kind + '_' + subtable)
    cursor.itersize = 100 * 1000
    cursor.execute(query, ids)
    fields = []
    last_id = None
    for row in cursor:
        id = row[0]
        if last_id != id:
            if fields:
                yield last_id, fields
            last_id = id
            fields = []
        for name, value in zip(names, row[1:]):
            if not value:
                continue
            if isinstance(value, str):
                value = value.decode('utf8')
            elif not isinstance(value, unicode):
                value = unicode(value)
            try:
                fields.append(E.field(value, name=name))
            except ValueError:
                continue # XXX
    if fields:
        yield last_id, fields


def placeholders(ids):
    return ", ".join(["%s" for i in ids])


def grab_next(iter):
    try:
        return iter.next()
    except StopIteration:
        return None


def merge(main, *extra):
    current = map(grab_next, extra)
    for id, fields in main:
        for i, extra_item in enumerate(current):
            if extra_item is not None:
                if extra_item[0] == id:
                    fields.extend(extra_item[1])
                    current[i] = grab_next(extra[i])
        yield id, E.doc(*fields)


def fetch_entities(db, kind, ids=()):
    sources = [iter_main(db, kind, ids)]
    subtables = set()
    for field in schema[kind].iter_multi_fields():
        if field.column.table not in subtables:
            sources.append(iter_sub(db, kind, field.column.table, ids))
            subtables.add(field.column.table)
    return merge(*sources)


def fetch_artists(db, ids=()):
    return fetch_entities(db, 'artist', ids)


def fetch_labels(db, ids=()):
    return fetch_entities(db, 'label', ids)


def fetch_release_groups(db, ids=()):
    return fetch_entities(db, 'release_group', ids)


def fetch_recordings(db, ids=()):
    return fetch_entities(db, 'recording', ids)


def fetch_releases(db, ids=()):
    return fetch_entities(db, 'release', ids)


def fetch_works(db, ids=()):
    return fetch_entities(db, 'work', ids)


def fetch_all(cfg, db):
    return itertools.chain(
        fetch_artists(db) if cfg.solr.index_artists else [],
        fetch_labels(db) if cfg.solr.index_labels else [],
        fetch_recordings(db) if cfg.solr.index_recordings else [],
        fetch_release_groups(db) if cfg.solr.index_release_groups else [],
        fetch_releases(db) if cfg.solr.index_releases else [],
        fetch_works(db) if cfg.solr.index_works else [])


def fetch_all_updated(cfg, db):
    queue = cfg.schema.name("mbslave") + ".mbslave_solr_queue"
    updated = {}
    cursor = db.cursor()
    cursor.execute("SELECT id, entity_type, entity_id FROM " + queue)
    for id, kind, entity_id in cursor:
        if kind not in updated:
            updated[kind] = set()
        db.cursor().execute("DELETE FROM " + queue + " WHERE id = %s", (id,))
        updated[kind].add(entity_id)
    for kind, ids in updated.iteritems():
        if getattr(cfg.solr, 'index_%ss' % kind):
            missing = set(ids)
            for id, doc in fetch_entities(db, kind, list(ids)):
                missing.remove(id)
                yield E.add(doc)
            if missing:
                yield E.delete(*map(E.id, ['%s:%s' % (kind, id) for id in missing]))

########NEW FILE########
__FILENAME__ = mbslave-import
#!/usr/bin/env python

import tarfile
import sys
import os
from mbslave import Config, connect_db, parse_name, check_table_exists, fqn


def load_tar(filename, db, config, ignored_tables):
    print "Importing data from", filename
    tar = tarfile.open(filename, 'r:bz2')
    cursor = db.cursor()
    for member in tar:
        if not member.name.startswith('mbdump/'):
            continue
        name = member.name.split('/')[1].replace('_sanitised', '')
        schema, table = parse_name(config, name)
        fulltable = fqn(schema, table)
        if table in ignored_tables:
            print " - Ignoring", name
            continue
        if not check_table_exists(db, schema, table):
            print " - Skipping %s (table %s does not exist)" % (name, fulltable)
            continue
        cursor.execute("SELECT 1 FROM %s LIMIT 1" % fulltable)
        if cursor.fetchone():
            print " - Skipping %s (table %s already contains data)" % (name, fulltable)
            continue
        print " - Loading %s to %s" % (name, fulltable)
        cursor.copy_from(tar.extractfile(member), fulltable)
        db.commit()


config = Config(os.path.dirname(__file__) + '/mbslave.conf')
db = connect_db(config)

ignored_tables = set(config.get('TABLES', 'ignore').split(','))
for filename in sys.argv[1:]:
    load_tar(filename, db, config, ignored_tables)


########NEW FILE########
__FILENAME__ = mbslave-psql
#!/usr/bin/env python

import os
from optparse import OptionParser
from mbslave import Config, connect_db

parser = OptionParser()
parser.add_option("-S", "--no-schema", action="store_true", dest="public", default=False, help="don't configure the default schema")
parser.add_option("-s", "--schema", dest="schema", default='musicbrainz', help="default schema")
options, args = parser.parse_args()

config = Config(os.path.dirname(__file__) + '/mbslave.conf')

args = ['psql']
args.append('-U')
args.append(config.get('DATABASE', 'user'))
if config.has_option('DATABASE', 'host'):
	args.append('-h')
	args.append(config.get('DATABASE', 'host'))
if config.has_option('DATABASE', 'port'):
	args.append('-p')
	args.append(config.get('DATABASE', 'port'))
args.append(config.get('DATABASE', 'name'))

if not options.public:
    schema = config.schema.name(options.schema)
    os.environ['PGOPTIONS'] = '-c search_path=%s' % schema
if config.has_option('DATABASE', 'password'):
	os.environ['PGPASSWORD'] = config.get('DATABASE', 'password')
os.execvp("psql", args)

########NEW FILE########
__FILENAME__ = mbslave-remap-schema
#!/usr/bin/env python

import re
import os
import sys
from mbslave import Config

config = Config(os.path.dirname(__file__) + '/mbslave.conf')

def update_search_path(m):
    schemas = m.group(2).replace("'", '').split(',')
    schemas = [config.schema.name(s.strip()) for s in schemas]
    return m.group(1) + ', '.join(schemas) + ';'

def update_schema(m):
    return m.group(1) + config.schema.name(m.group(2)) + m.group(3)

for line in sys.stdin:
    line = re.sub(r'(SET search_path = )(.+?);', update_search_path, line)
    line = re.sub(r'(\b)(\w+)(\.)', update_schema, line)
    line = re.sub(r'( SCHEMA )(\w+)(;)', update_schema, line)
    sys.stdout.write(line)


########NEW FILE########
__FILENAME__ = mbslave-solr-export
#!/usr/bin/env python

import os
import itertools
from lxml import etree as ET
from lxml.builder import E
from mbslave import Config, connect_db
from mbslave.search import fetch_all

cfg = Config(os.path.join(os.path.dirname(__file__), 'mbslave.conf'))
db = connect_db(cfg, True)

print '<add>'
for id, doc in fetch_all(cfg, db):
    print ET.tostring(doc)
print '</add>'


########NEW FILE########
__FILENAME__ = mbslave-solr-generate-triggers
#!/usr/bin/env python

import os
import itertools
from lxml import etree as ET
from lxml.builder import E
from mbslave import Config, connect_db
from mbslave.search import generate_triggers

cfg = Config(os.path.join(os.path.dirname(__file__), 'mbslave.conf'))
db = connect_db(cfg)

print '\set ON_ERROR_STOP 1'
print 'BEGIN;'

for code in generate_triggers():
    print code

print 'COMMIT;'


########NEW FILE########
__FILENAME__ = mbslave-solr-update
#!/usr/bin/env python

import os
import urllib2
from cStringIO import StringIO
from lxml import etree as ET
from mbslave import Config, connect_db
from mbslave.search import fetch_all_updated

cfg = Config(os.path.join(os.path.dirname(__file__), 'mbslave.conf'))
db = connect_db(cfg, True)

xml = StringIO()
xml.write('<update>\n')
for doc in fetch_all_updated(cfg, db):
    xml.write(ET.tostring(doc))
    xml.write('\n')
xml.write('</update>\n')

req = urllib2.Request(cfg.solr.url + '/update?commit=true', xml.getvalue(),
    {'Content-Type': 'application/xml; encoding=UTF-8'})
resp = urllib2.urlopen(req)
the_page = resp.read()

doc = ET.fromstring(the_page)
status = doc.find("lst[@name='responseHeader']/int[@name='status']")
if status.text != '0':
    print the_page
    raise SystemExit(1)

db.commit()


########NEW FILE########
__FILENAME__ = mbslave-sync
#!/usr/bin/env python

import psycopg2
import tarfile
import sys
import os
import re
import urllib2
import shutil
import tempfile
from mbslave import Config, ReplicationHook, connect_db, parse_name, fqn
from mbslave.monitoring import StatusReport


def parse_data_fields(s):
    fields = {}
    for name, value in re.findall(r'''"([^"]+)"=('(?:''|[^'])*')? ''', s):
        if not value:
            value = None
        else:
            value = value[1:-1].replace("''", "'").replace("\\\\", "\\")
        fields[name] = value
    return fields


def parse_bool(s):
    return s == 't'


ESCAPES = (('\\b', '\b'), ('\\f', '\f'), ('\\n', '\n'), ('\\r', '\r'),
           ('\\t', '\t'), ('\\v', '\v'), ('\\\\', '\\'))

def unescape(s):
    if s == '\\N':
        return None
    for orig, repl in ESCAPES:
        s = s.replace(orig, repl)
    return s


def read_psql_dump(fp, types):
    for line in fp:
        values = map(unescape, line.rstrip('\r\n').split('\t'))
        for i, value in enumerate(values):
            if value is not None:
                values[i] = types[i](value)
        yield values


class PacketImporter(object):

    def __init__(self, db, config, ignored_tables, replication_seq, hook):
        self._db = db
        self._data = {}
        self._transactions = {}
        self._config = config
        self._ignored_tables = ignored_tables
        self._hook = hook
        self._replication_seq = replication_seq

    def load_pending_data(self, fp):
        dump = read_psql_dump(fp, [int, parse_bool, parse_data_fields])
        for id, key, values in dump:
            self._data[(id, key)] = values

    def load_pending(self, fp):
        dump = read_psql_dump(fp, [int, str, str, int])
        for id, table, type, xid in dump:
            schema, table = parse_name(self._config, table)
            transaction = self._transactions.setdefault(xid, [])
            transaction.append((id, schema, table, type))

    def process(self):
        cursor = self._db.cursor()
        stats = {}
        self._hook.begin(self._replication_seq)
        for xid in sorted(self._transactions.keys()):
            transaction = self._transactions[xid]
            #print ' - Running transaction', xid
            #print 'BEGIN; --', xid
            for id, schema, table, type in sorted(transaction):
                if table in self._ignored_tables:
                    continue
                fulltable = fqn(schema, table)
                if fulltable not in stats:
                    stats[fulltable] = {'d': 0, 'u': 0, 'i': 0}
                stats[fulltable][type] += 1
                keys = self._data.get((id, True), {})
                values = self._data.get((id, False), {})
                if type == 'd':
                    sql = 'DELETE FROM %s' % (fulltable,)
                    params = []
                    self._hook.before_delete(table, keys)
                elif type == 'u':
                    sql_values = ', '.join('%s=%%s' % i for i in values)
                    sql = 'UPDATE %s SET %s' % (fulltable, sql_values)
                    params = values.values()
                    self._hook.before_update(table, keys, values)
                elif type == 'i':
                    sql_columns = ', '.join(values.keys())
                    sql_values = ', '.join(['%s'] * len(values))
                    sql = 'INSERT INTO %s (%s) VALUES (%s)' % (fulltable, sql_columns, sql_values)
                    params = values.values()
                    self._hook.before_insert(table, values)
                if type == 'd' or type == 'u':
                    sql += ' WHERE ' + ' AND '.join('%s%s%%s' % (i, ' IS ' if keys[i] is None else '=') for i in keys.keys())
                    params.extend(keys.values())
                #print sql, params
                cursor.execute(sql, params)
                if type == 'd':
                    self._hook.after_delete(table, keys)
                elif type == 'u':
                    self._hook.after_update(table, keys, values)
                elif type == 'i':
                    self._hook.after_insert(table, values)
            #print 'COMMIT; --', xid
        print ' - Statistics:'
        for table in sorted(stats.keys()):
            print '   * %-30s\t%d\t%d\t%d' % (table, stats[table]['i'], stats[table]['u'], stats[table]['d'])
        self._hook.before_commit()
        self._db.commit()
        self._hook.after_commit()


def process_tar(fileobj, db, schema, ignored_tables, expected_schema_seq, replication_seq, hook):
    print "Processing", fileobj.name
    tar = tarfile.open(fileobj=fileobj, mode='r:bz2')
    importer = PacketImporter(db, schema, ignored_tables, replication_seq, hook)
    for member in tar:
        if member.name == 'SCHEMA_SEQUENCE':
            schema_seq = int(tar.extractfile(member).read().strip())
            if schema_seq != expected_schema_seq:
                raise Exception("Mismatched schema sequence, %d (database) vs %d (replication packet)" % (expected_schema_seq, schema_seq))
        elif member.name == 'TIMESTAMP':
            ts = tar.extractfile(member).read().strip()
            print ' - Packet was produced at', ts
        elif member.name in ('mbdump/Pending', 'mbdump/dbmirror_pending'):
            importer.load_pending(tar.extractfile(member))
        elif member.name in ('mbdump/PendingData', 'mbdump/dbmirror_pendingdata'):
            importer.load_pending_data(tar.extractfile(member))
    importer.process()


def download_packet(base_url, replication_seq):
    url = base_url + "/replication-%d.tar.bz2" % replication_seq
    print "Downloading", url
    try:
        data = urllib2.urlopen(url)
    except urllib2.HTTPError, e:
        if e.code == 404:
            return None
        raise
    tmp = tempfile.NamedTemporaryFile(suffix='.tar.bz2')
    shutil.copyfileobj(data, tmp)
    data.close()
    tmp.seek(0)
    return tmp

config = Config(os.path.dirname(__file__) + '/mbslave.conf')
db = connect_db(config)

base_url = config.get('MUSICBRAINZ', 'base_url')
ignored_tables = set(config.get('TABLES', 'ignore').split(','))

hook_class = ReplicationHook

cursor = db.cursor()
cursor.execute("SELECT current_schema_sequence, current_replication_sequence FROM %s.replication_control" % config.schema.name('musicbrainz'))
schema_seq, replication_seq = cursor.fetchone()

status = StatusReport(schema_seq, replication_seq)
if config.monitoring.enabled:
    status.load(config.monitoring.status_file)

while True:
    replication_seq += 1
    hook = hook_class(config, db, config)
    tmp = download_packet(base_url, replication_seq)
    if tmp is None:
        print 'Not found, stopping'
        status.end()
        break
    process_tar(tmp, db, config, ignored_tables, schema_seq, replication_seq, hook)
    tmp.close()
    status.update(replication_seq)

if config.monitoring.enabled:
    status.save(config.monitoring.status_file)


########NEW FILE########
