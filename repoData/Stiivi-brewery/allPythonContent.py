__FILENAME__ = common
import StringIO
import traceback
import sys

__all__ = [
    "FieldError",
    "StreamError",
    "StreamRuntimeError"
]

class FieldError(Exception):
    """Exception raised on field incompatibility or missing fields."""
    pass

class StreamError(Exception):
    """Exception raised on stream."""
    pass

class StreamRuntimeError(Exception):
    """Exception raised when a node fails during `run()` phase.

    Attributes:
        * `message`: exception message
        * `node`: node where exception was raised
        * `exception`: exception that was raised while running the node
        * `traceback`: stack traceback
        * `inputs`: array of field lists for each input
        * `output`: output field list
    """
    def __init__(self, message=None, node=None, exception=None):
        super(StreamRuntimeError, self).__init__()
        if message:
            self.message = message
        else:
            self.message = ""

        self.node = node
        self.exception = exception
        self.traceback = None
        self.inputs = []
        self.output = []
        self.attributes = {}

    def print_exception(self, output=None):
        """Prints exception and details in human readable form. You can specify IO stream object in
        `output` parameter. By default text is printed to standard output."""

        if not output:
            output = sys.stderr

        text = u"stream failed. reason: %s\n" % self.message
        text += u"exception: %s: \n" % self.exception.__class__.__name__

        text += u"node: %s\n" % self.node

        try:
            text += unicode(self.exception)
        except Exception, e:
            text += u"<unable to get exception string: %s>" % e

        text += "\ntraceback\n"

        try:
            l = traceback.format_list(traceback.extract_tb(self.traceback))
            text += "".join(l)
        except Exception as e:
            text += "<unable to get traceback string: %s>" % e

        text += "\n"

        if self.inputs:
            for i, fields in enumerate(self.inputs):
                text += "input %i:\n" % i
                input_text = ""
                for (index, field) in enumerate(fields):
                    input_text += u"% 5d %s (storage:%s analytical:%s)\n" \
                                % (index, field.name, field.storage_type, field.analytical_type)
                text += unicode(input_text)
        else:
            text += "input: none"

        text += "\n"

        if self.output:
            text += "output:\n"
            for field in self.output:
                text += u"    %s (storage:%s analytical:%s)\n" \
                            % (field.name, field.storage_type, field.analytical_type)
        else:
            text += "ouput: none"

        text += "\n"

        if self.attributes:
            text += "attributes:\n"
            for name, attribute in self.attributes.items():
                try:
                    value = unicode(attribute)
                except Exception, e:
                    value = "unable to convert to string (exception: %s)" % e
                text += "    %s: %s\n" % (name, value)
        else:
            text += "attributes: none"

        output.write(text)

    def __str__(self):
        s = StringIO.StringIO()
        try:
            self.print_exception(s)
            v = s.getvalue()
        except Exception, e:
            v = "Unable to print strem exception. Reason: %s (%s)" % (e, type(e))
        finally:
            s.close()

        return v

########NEW FILE########
__FILENAME__ = base
#!/usr/bin/env python
# -*- coding: utf-8 -*-

class ProbeSet(object):
    """Set of probes"""
    def __init__(self, probes=None):
        """Creates a probe-set which acts as multi-probe. `probes` should be
        a list of probes."""
        super(ProbeSet, self).__init__()
        self.probes = probes

    def probe(self, value):
        """Probe the value in all of the probes."""
        for probe in self.probes:
            probe.probe(value)

    def finalize(self):
        """Finalize all probes."""
        for probe in self.probes:
            probe.finalize()

class FieldTypeProbe(object):
    """Probe for guessing field data type

    Attributes:
        * field: name of a field which statistics are being presented
        * storage_types: found storage types
        * unique_storage_type: if there is only one storage type, then this is set to that type
    """
    def __init__(self, field):
        self.field = field

        self.storage_types = set()

        self.null_count = 0
        self.empty_string_count = 0

    def probe(self, value):
        storage_type = value.__class__
        self.storage_types.add(storage_type.__name__)

        if value is None:
            self.null_count += 1
        if value == '':
            self.empty_string_count += 1

    @property
    def unique_storage_type(self):
        """Return storage type if there is only one. This should always return a type in relational
        databases, but does not have to in databases such as MongoDB."""

        if len(self.storage_types) == 1:
            return list(self.storage_types)[0]
        return None

########NEW FILE########
__FILENAME__ = field_statistics
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Field statistics"""

class FieldStatistics(object):
    """Data quality statistics for a dataset field

    :Attributes:
        * `field`: name of a field for which statistics are being collected

        * `value_count`: number of records in which the field exist. In relationad database table this
          is equal to number of rows, in document based databse, such as MongoDB, it is number of
          documents that have a key present (being null or not)

        * `record_count`: total count of records in dataset. This should be set explicitly on
          finalisation. Seet :meth:`FieldStatistics.finalize`. In relational database this should be the
          same as `value_count`.

        * `value_ratio`: ratio of value count to record count, 1 for relational databases

        * `null_count`: number of records where field is null

        * `null_value_ratio`: ratio of records with nulls to total number of probed values =
          `null_value_ratio` / `value_count`

        * `null_record_ratio`: ratio of records with nulls to total number of records =
          `null_value_ratio` / `record_count`

        * `empty_string_count`: number of empty strings

        * `storage_types`: list of all encountered storage types (CSV, MongoDB, XLS might have different
          types within a field)

        * `unique_storage_type`: if there is only one storage type, then this is set to that type

        * `distict_values`: list of collected distinct values

        * `distinct_threshold`: number of distict values to collect, if count of distinct values is
          greather than threshold, collection is stopped and `distinct_overflow` will be set. Set to 0
          to get all values. Default is 10.
    """
    def __init__(self, key = None, distinct_threshold = 10):
        self.field = key
        self.value_count = 0
        self.record_count = 0
        self.value_ratio = 0

        self.distinct_values = set()
        self.distinct_overflow = False
        self.storage_types = set()

        self.null_count = 0
        self.null_value_ratio = 0
        self.null_record_ratio = 0
        self.empty_string_count = 0

        self.distinct_threshold = distinct_threshold

        self.unique_storage_type = None

        self.probes = []

    def probe(self, value):
        """Probe the value:

        * increase found value count
        * identify storage type
        * probe for null and for empty string

        * probe distinct values: if their count is less than ``distinct_threshold``. If there are more
          distinct values than the ``distinct_threshold``, then distinct_overflow flag is set and list
          of distinct values will be empty

        """

        storage_type = value.__class__
        self.storage_types.add(storage_type.__name__)

        self.value_count += 1

        # FIXME: check for existence in field.empty_values
        if value is None:
            self.null_count += 1

        if value == '':
            self.empty_string_count += 1

        self._probe_distinct(value)

        for probe in self.probes:
            probe.probe(value)

    def _probe_distinct(self, value):
        """"""
        if self.distinct_overflow:
            return

        # We are not testing lists, dictionaries and object IDs
        storage_type = value.__class__

        if not self.distinct_threshold or self.distinct_threshold == 0 or len(self.distinct_values) < self.distinct_threshold:
            try:
                self.distinct_values.add(value)
            except:
                # FIXME: Should somehow handle invalid values that can not be added
                pass
        else:
            self.distinct_overflow = True

    def finalize(self, record_count = None):
        """Compute final statistics.

        :Parameters:
            * `record_count`: final number of records in probed dataset.
                See :meth:`FieldStatistics` for more information.
        """
        if record_count:
            self.record_count = record_count
        else:
            self.record_count = self.value_count

        if self.record_count:
            self.value_ratio = float(self.value_count) / float(self.record_count)
            self.null_record_ratio = float(self.null_count) / float(self.record_count)

        if self.value_count:
            self.null_value_ratio = float(self.null_count) / float(self.value_count)

        if len(self.storage_types) == 1:
            self.unique_storage_type = list(self.storage_types)[0]

    def dict(self):
        """Return dictionary representation of receiver."""
        d = {
            "key": self.field,
            "value_count": self.value_count,
            "record_count": self.record_count,
            "value_ratio": self.value_ratio,
            "storage_types": list(self.storage_types),
            "null_count": self.null_count,
            "null_value_ratio": self.null_value_ratio,
            "null_record_ratio": self.null_record_ratio,
            "empty_string_count": self.empty_string_count,
            "unique_storage_type": self.unique_storage_type
        }

        if self.distinct_overflow:
            d["distinct_overflow"] = self.distinct_overflow,
            d["distinct_values"] = []
        else:
            d["distinct_values"] = list(self.distinct_values)

        return d

    def __repr__(self):
        return "FieldStatistics:%s" % (self.dict())


########NEW FILE########
__FILENAME__ = base
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Data stores, data sets and data sources
"""

# Data sources
# ============
#
# Should implement:
# * fields
# * prepare()
# * rows() - returns iterable with value tuples
# * records() - returns iterable with dictionaries of key-value pairs
#
# Data targets
# ============
# Should implement:
# * fields
# * prepare()
# * append(object) - appends object as row or record depending whether it is a dictionary or a list
# Optional (for performance):
# * append_row(row) - row is tuple of values, raises exception if there are more values than fields
# * append_record(record) - record is a dictionary, raises exception if dict key is not in field list

import urllib2
import urlparse
import brewery.dq
from brewery.metadata import collapse_record, Field

def open_resource(resource, mode = None):
    """Get file-like handle for a resource. Conversion:

    * if resource is a string and it is not URL or it is file:// URL, then opens a file
    * if resource is URL then opens urllib2 handle
    * otherwise assume that resource is a file-like handle

    Returns tuple: (handle, should_close) where `handle` is file-like object and `should_close` is
        a flag whether returned handle should be closed or not. Closed should be resources which
        where opened by this method, that is resources referenced by a string or URL.
    """

    if type(resource) == str or type(resource) == unicode:
        should_close = True
        parts = urlparse.urlparse(resource)
        if parts.scheme == '' or parts.scheme == 'file':
            if mode:
                handle = open(resource, mode=mode)
            else:
                handle = open(resource)
        else:
            handle = urllib2.urlopen(resource)
    else:
        should_close = False
        handle = resource

    return handle, should_close

class DataStream(object):
    """Shared methods for data targets and data sources"""

    def __init__(self):
        """
        A data stream object – abstract class.

        The subclasses should provide:

        * `fields`

        `fields` are :class:`FieldList` objects representing fields passed
        through the receiving stream - either read from data source
        (:meth:`DataSource.rows`) or written to data target
        (:meth:`DataTarget.append`).

        Subclasses should populate the `fields` property (or implenet an
        accessor).

        The subclasses might override:

        * `initialize()`
        * `finalize()`

        The class supports context management, for example::

            with ds.CSVDataSource("output.csv") as s:
                for row in s.rows():
                    print row

        In this case, the initialize() and finalize() methods are called
        automatically.
        """
        super(DataStream, self).__init__()

    def initialize(self):
        """Delayed stream initialisation code. Subclasses might override this
        method to implement file or handle opening, connecting to a database,
        doing web authentication, ... By default this method does nothing.

        The method does not take any arguments, it expects pre-configured
        object.
        """
        pass

    def finalize(self):
        """Subclasses might put finalisation code here, for example:

        * closing a file stream
        * sending data over network
        * writing a chart image to a file

        Default implementation does nothing.
        """
        pass

    # Context management
    #
    # See: http://docs.python.org/reference/datamodel.html#context-managers
    #
    def __enter__(self):
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.finalize()

class DataSource(DataStream):
    """Input data stream - for reading."""

    def __init__(self):
        """Abstrac class for data sources."""
        super(DataSource, self).__init__()

    def rows(self):
        """Return iterable object with tuples. This is one of two methods for reading from
        data source. Subclasses should implement this method.
        """
        raise NotImplementedError()

    def records(self):
        """Return iterable object with dict objects. This is one of two methods for reading from
        data source. Subclasses should implement this method.
        """
        raise NotImplementedError()

    def read_fields(self, limit = 0, collapse = False):
        """Read field descriptions from data source. You should use this for datasets that do not
        provide metadata directly, such as CSV files, document bases databases or directories with
        structured files. Does nothing in relational databases, as fields are represented by table
        columns and table metadata can obtained from database easily.

        Note that this method can be quite costly, as by default all records within dataset are read
        and analysed.

        After executing this method, stream ``fields`` is set to the newly read field list and may
        be configured (set more appropriate data types for example).

        :Arguments:
            - `limit`: read only specified number of records from dataset to guess field properties
            - `collapse`: whether records are collapsed into flat structure or not

        Returns: tuple with Field objects. Order of fields is datastore adapter specific.
        """

        keys = []
        probes = {}

        def probe_record(record, parent = None):
            for key, value in record.items():
                full_key = parent + "." + key if parent else key

                if self.expand and type(value) == dict:
                    probe_record(value, full_key)
                    continue

                if not full_key in probes:
                    probe = brewery.dq.FieldTypeProbe(full_key)
                    probes[full_key] = probe
                    keys.append(full_key)
                else:
                    probe = probes[full_key]
                probe.probe(value)

        count = 0
        for record in self.records():
            if collapse:
                record = collapse_record(record)

            probe_record(record)
            if limit and count >= limit:
                break
            count += 1

        fields = []

        for key in keys:
            probe = probes[key]
            field = Field(probe.field)

            storage_type = probe.unique_storage_type
            if not storage_type:
                field.storage_type = "unknown"
            elif storage_type == "unicode":
                field.storage_type = "string"
            else:
                field.storage_type = "unknown"
                field.concrete_storage_type = storage_type

            # FIXME: Set analytical type

            fields.append(field)

        self.fields = list(fields)
        return self.fields

class DataTarget(DataStream):
    """Output data stream - for writing.
    """
    def __init__(self):
        """Abstrac class for data targets."""
        super(DataTarget, self).__init__()

    def append(self, object):
        """Append an object into dataset. Object can be a tuple, array or a dict object. If tuple
        or array is used, then value position should correspond to field position in the field list,
        if dict is used, the keys should be valid field names.
        """
        raise NotImplementedError()


########NEW FILE########
__FILENAME__ = csv_streams
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import csv
import codecs
import cStringIO
import base
import brewery.metadata

class UTF8Recoder(object):
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8

    From: <http://docs.python.org/lib/csv-examples.html>
    """
    def __init__(self, f, encoding=None):
        if encoding:
            self.reader = codecs.getreader(encoding)(f)
        else: # already unicode so just return f
            self.reader = f

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode('utf-8')

def to_bool(value):
    """Return boolean value. Convert string to True when "true", "yes" or "on"
    """
    return bool(value) or lower(value) in ["true", "yes", "on"]

storage_conversion = {
    "unknown": None,
    "string": None,
    "text": None,
    "integer": int,
    "float": float,
    "boolean": to_bool,
    "date": None
}

class UnicodeReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", empty_as_null=False, **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = csv.reader(f, dialect=dialect, **kwds)
        self.converters = []
        self.empty_as_null = empty_as_null

    def set_fields(self, fields):
        self.converters = [storage_conversion[f.storage_type] for f in fields]

    def next(self):
        row = self.reader.next()
        result = []

        # FIXME: make this nicer, this is just quick hack
        for i, value in enumerate(row):
            if self.converters:
                f = self.converters[i]
            else:
                f = None

            if f:
                result.append(f(value))
            else:
                uni_str = unicode(value, "utf-8")
                if not uni_str and self.empty_as_null:
                    result.append(None)
                else:
                    result.append(uni_str)
            
        return result

    def __iter__(self):
        return self

class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.

    From: <http://docs.python.org/lib/csv-examples.html>
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        new_row = []
        for value in row:
            if type(value) == unicode or type(value) == str:
                new_row.append(value.encode("utf-8"))
            elif value is not None:
                new_row.append(unicode(value))
            else:
                new_row.append(None)
                
        self.writer.writerow(new_row)
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)

class CSVDataSource(base.DataSource):
    """docstring for ClassName
    
    Some code taken from OKFN Swiss library.
    """
    def __init__(self, resource, read_header=True, dialect=None, encoding=None,
                 detect_header=False, sample_size=200, skip_rows=None,
                 empty_as_null=True,fields=None, **reader_args):
        """Creates a CSV data source stream.
        
        :Attributes:
            * resource: file name, URL or a file handle with CVS data
            * read_header: flag determining whether first line contains header
              or not. ``True`` by default.
            * encoding: source character encoding, by default no conversion is
              performed.
            * detect_headers: try to determine whether data source has headers
              in first row or not
            * sample_size: maximum bytes to be read when detecting encoding
              and headers in file. By default it is set to 200 bytes to
              prevent loading huge CSV files at once.
            * skip_rows: number of rows to be skipped. Default: ``None``
            * empty_as_null: treat empty strings as ``Null`` values
            
        Note: avoid auto-detection when you are reading from remote URL
        stream.
        
        """
        self.read_header = read_header
        self.encoding = encoding
        self.detect_header = detect_header
        self.empty_as_null = empty_as_null
        
        self.sample_size = sample_size
        self.resource = resource
        self.reader_args = reader_args
        self.reader = None
        self.dialect = dialect
        
        self.close_file = False
        self.skip_rows = skip_rows
        self.fields = fields
        
    def initialize(self):
        """Initialize CSV source stream:
        
        #. perform autodetection if required:
            #. detect encoding from a sample data (if requested)
            #. detect whether CSV has headers from a sample data (if
            requested)
        #.  create CSV reader object
        #.  read CSV headers if requested and initialize stream fields
        
        If fields are explicitly set prior to initialization, and header
        reading is requested, then the header row is just skipped and fields
        that were set before are used. Do not set fields if you want to read
        the header.

        All fields are set to `storage_type` = ``string`` and
        `analytical_type` = ``unknown``.
        """

        self.file, self.close_file = base.open_resource(self.resource)

        handle = None
        
        if self.detect_header:
            
            sample = self.file.read(self.sample_size)

            # Encoding test
            sample = sample.encode('utf-8')
            sniffer = csv.Sniffer()
            self.read_header = sniffer.has_header(sample)

            self.file.seek(0)
            
        if self.dialect:
            if type(self.dialect) == str:
                dialect = csv.get_dialect(self.dialect)
            else:
                dialect = self.dialect
                
            self.reader_args["dialect"] = dialect

        # self.reader = csv.reader(handle, **self.reader_args)
        self.reader = UnicodeReader(self.file, encoding=self.encoding,
                                    empty_as_null=self.empty_as_null,
                                    **self.reader_args)

        if self.skip_rows:
            for i in range(0, self.skip_rows):
                self.reader.next()
                
        # Initialize field list
        if self.read_header:
            field_names = self.reader.next()
            
            # Fields set explicitly take priority over what is read from the
            # header. (Issue #17 might be somehow related)
            if not self.fields:
                fields = [ (name, "string", "default") for name in field_names]
                self.fields = brewery.metadata.FieldList(fields)
            
        if not self.fields:
            raise RuntimeError("Fields are not initialized. "
                               "Either read fields from CSV header or "
                               "set them manually")

        self.reader.set_fields(self.fields)
        
    def finalize(self):
        if self.file and self.close_file:
            self.file.close()

    def rows(self):
        if not self.reader:
            raise RuntimeError("Stream is not initialized")
        if not self.fields:
            raise RuntimeError("Fields are not initialized")
        return self.reader

    def records(self):
        fields = self.fields.names()
        for row in self.reader:
            yield dict(zip(fields, row))

class CSVDataTarget(base.DataTarget):
    def __init__(self, resource, write_headers=True, truncate=True, encoding="utf-8", 
                dialect=None,fields=None, **kwds):
        """Creates a CSV data target
        
        :Attributes:
            * resource: target object - might be a filename or file-like
              object
            * write_headers: write field names as headers into output file
            * truncate: remove data from file before writing, default: True
            
        """
        self.resource = resource
        self.write_headers = write_headers
        self.truncate = truncate
        self.encoding = encoding
        self.dialect = dialect
        self.fields = fields
        self.kwds = kwds

        self.close_file = False
        self.file = None
        
    def initialize(self):
        mode = "w" if self.truncate else "a"

        self.file, self.close_file = base.open_resource(self.resource, mode)

        self.writer = UnicodeWriter(self.file, encoding = self.encoding, 
                                    dialect = self.dialect, **self.kwds)
        
        if self.write_headers:
            self.writer.writerow(self.fields.names())

        self.field_names = self.fields.names()
        
    def finalize(self):
        if self.file and self.close_file:
            self.file.close()

    def append(self, obj):
        if type(obj) == dict:
            row = []
            for field in self.field_names:
                row.append(obj.get(field))
        else:
            row = obj
                
        self.writer.writerow(row)

########NEW FILE########
__FILENAME__ = elasticsearch_streams
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base
from brewery import dq
import time
from brewery.metadata import expand_record

try:
    from pyes.es import ES
except ImportError:
    from brewery.utils import MissingPackage
    pyes = MissingPackage("pyes", "ElasticSearch streams", "http://www.elasticsearch.org/")

class ESDataSource(base.DataSource):
    """docstring for ClassName
    """
    def __init__(self, document_type, database=None, host=None, port=None,
                 expand=False, **elasticsearch_args):
        """Creates a ElasticSearch data source stream.

        :Attributes:
            * document_type: elasticsearch document_type name
            * database: database name
            * host: elasticsearch database server host, default is ``localhost``
            * port: elasticsearch port, default is ``27017``
            * expand: expand dictionary values and treat children as top-level keys with dot '.'
                separated key path to the child..
        """
        self.document_type = document_type
        self.database_name = database
        self.host = host
        self.port = port
        self.elasticsearch_args = elasticsearch_args
        self.expand = expand
        self.connection = None
        self._fields = None

    def initialize(self):
        """Initialize ElasticSearch source stream:
        """
        args = self.elasticsearch_args.copy()
        server = ""
        if self.host:
            server = self.host
        if self.port:
            server += ":" + self.port

        self.connection = ES(server, **args)
        self.connection.default_indices = self.database_name
        self.connection.default_types = self.document_type

    def read_fields(self, limit=0):
        keys = []
        probes = {}

        def probe_record(record, parent=None):
            for key, value in record.items():
                if parent:
                    full_key = parent + "." + key
                else:
                    full_key = key

                if self.expand and type(value) == dict:
                    probe_record(value, full_key)
                    continue

                if not full_key in probes:
                    probe = dq.FieldTypeProbe(full_key)
                    probes[full_key] = probe
                    keys.append(full_key)
                else:
                    probe = probes[full_key]
                probe.probe(value)

        for record in self.document_type.find(limit=limit):
            probe_record(record)

        fields = []

        for key in keys:
            probe = probes[key]
            field = base.Field(probe.field)

            storage_type = probe.unique_storage_type
            if not storage_type:
                field.storage_type = "unknown"
            elif storage_type == "unicode":
                field.storage_type = "string"
            else:
                field.storage_type = "unknown"
                field.concrete_storage_type = storage_type

            # FIXME: Set analytical type

            fields.append(field)

        self.fields = list(fields)
        return self.fields

    def rows(self):
        if not self.connection:
            raise RuntimeError("Stream is not initialized")
        from pyes.query import MatchAllQuery
        fields = self.fields.names()
        results = self.connection.search(MatchAllQuery(), search_type="scan", timeout="5m", size="200")
        return ESRowIterator(results, fields)

    def records(self):
        if not self.connection:
            raise RuntimeError("Stream is not initialized")
        from pyes.query import MatchAllQuery
        results = self.connection.search(MatchAllQuery(), search_type="scan", timeout="5m", size="200")
        return ESRecordIterator(results, self.expand)

class ESRowIterator(object):
    """Wrapper for ElasticSearch ResultSet to be able to return rows() as tuples and records() as
    dictionaries"""
    def __init__(self, resultset, field_names):
        self.resultset = resultset
        self.field_names = field_names

    def __getitem__(self, index):
        record = self.resultset.__getitem__(index)

        array = []

        for field in self.field_names:
            value = record
            for key in field.split('.'):
                if key in value:
                    value = value[key]
                else:
                    break
            array.append(value)

        return tuple(array)

class ESRecordIterator(object):
    """Wrapper for ElasticSearch ResultSet to be able to return rows() as tuples and records() as
    dictionaries"""
    def __init__(self, resultset, expand=False):
        self.resultset = resultset
        self.expand = expand

    def __getitem__(self, index):
        def expand_record(record, parent=None):
            ret = {}
            for key, value in record.items():
                if parent:
                    full_key = parent + "." + key
                else:
                    full_key = key

                if type(value) == dict:
                    expanded = expand_record(value, full_key)
                    ret.update(expanded)
                else:
                    ret[full_key] = value
            return ret

        record = self.resultset.__getitem__(index)
        if not self.expand:
            return record
        else:
            return expand_record(record)

class ESDataTarget(base.DataTarget):
    """docstring for ClassName
    """
    def __init__(self, document_type, database="test", host="127.0.0.1", port="9200",
                 truncate=False, expand=False, **elasticsearch_args):
        """Creates a ElasticSearch data target stream.

        :Attributes:
            * document_ElasticSearch elasticsearch document_type name
            * database: database name
            * host: ElasticSearch database server host, default is ``localhost``
            * port: ElasticSearch port, default is ``9200``
            * expand: expand dictionary values and treat children as top-level keys with dot '.'
                separated key path to the child..
            * truncate: delete existing data in the document_type. Default: False
        """
        self.document_type = document_type
        self.database_name = database
        self.host = host
        self.port = port
        self.elasticsearch_args = elasticsearch_args
        self.expand = expand
        self.truncate = truncate
        self._fields = None

    def initialize(self):
        """Initialize ElasticSearch source stream:
        """
        from pyes.es import ES
        from pyes.exceptions import IndexAlreadyExistsException

        args = self.elasticsearch_args.copy()
        server = ""
        if self.host:
            server = self.host
        if self.port:
            server += ":" + self.port

        create = args.pop("create", False)
        replace = args.pop("replace", False)

        self.connection = ES(server, **args)
        self.connection.default_indices = self.database_name
        self.connection.default_types = self.document_type

        created = False
        if create:
            try:
                self.connection.create_index(self.database_name)
                self.connection.refresh(self.database_name)
                created = True
            except IndexAlreadyExistsException:
                pass

        if replace and not created:
            self.connection.delete_index_if_exists(self.database_name)
            time.sleep(2)
            self.connection.create_index(self.database_name)
            self.connection.refresh(self.database_name)

        if self.truncate:
            self.connection.delete_mapping(self.database_name, self.document_type)
            self.connection.refresh(self.database_name)

    def append(self, obj):
        record = obj
        if not isinstance(obj, dict):
            record = dict(zip(self.fields.names(), obj))

        if self.expand:
            record = expand_record(record)

        id = record.get('id') or record.get('_id')
        self.connection.index(record, self.database_name, self.document_type, id, bulk=True)

    def finalize(self):
        self.connection.flush_bulk(forced=True)

########NEW FILE########
__FILENAME__ = gdocs_streams
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base
import brewery.metadata as metadata
try:
    import gdata.spreadsheet.text_db
except:
    from brewery.utils import MissingPackage
    gdata = MissingPackage("gdata", "Google data (spreadsheet) source/target")

# Documentation:
# http://gdata-python-client.googlecode.com/svn/trunk/pydocs/

class GoogleSpreadsheetDataSource(base.DataSource):
    """Reading data from a google spreadsheet.
    
    Some code taken from OKFN Swiss library.
    """
    def __init__(self, spreadsheet_key=None, spreadsheet_name=None,
                worksheet_id=None, worksheet_name=None,
                query_string="",
                username=None, password=None):
        """Creates a Google Spreadsheet data source stream.
        
        :Attributes:
            * spreadsheet_key: The unique key for the spreadsheet, this 
                  usually in the the form 'pk23...We' or 'o23...423.12,,,3'.
            * spreadsheet_name: The title of the spreadsheets.
            * worksheet_id: ID of a worksheet
            * worksheet_name: name of a worksheet
            * query_string: optional query string for row selection
            * username: Google account user name
            * password: Google account password
            
        You should provide either spreadsheet_key or spreadsheet_name, if more than one spreadsheet with
        given name are found, then the first in list returned by Google is used.
        
        For worksheet selection you should provide either worksheet_id or worksheet_name. If more than
        one worksheet with given name are found, then the first in list returned by Google is used. If
        no worksheet_id nor worksheet_name are provided, then first worksheet in the workbook is used.
        
        For details on query string syntax see the section on sq under
        http://code.google.com/apis/spreadsheets/reference.html#list_Parameters
        """

        self.spreadsheet_key = spreadsheet_key
        self.spreadsheet_name = spreadsheet_name
        self.worksheet_id = worksheet_id
        self.worksheet_name = worksheet_name
        self.query_string = query_string
        self.username = username
        self.password = password

        self.client = None

        self._fields = None

    def initialize(self):
        """Connect to the Google documents, authenticate.
        """
            
        self.client = gdata.spreadsheet.text_db.DatabaseClient(username=self.username, password=self.password)

        dbs = self.client.GetDatabases(spreadsheet_key=self.spreadsheet_key,
                                        name=self.spreadsheet_name)

        if len(dbs) < 1:
            raise Exception("No spreadsheets with key '%s' or name '%s'" %
                                (self.spreadsheet_key, self.spreadsheet_key))

        db = dbs[0]
        worksheets = db.GetTables(worksheet_id=self.worksheet_id,
                                  name=self.worksheet_name)

        self.worksheet = worksheets[0]
        self.worksheet.LookupFields()

        # FIXME: try to determine field types from next row
        self._fields = metadata.FieldList(self.worksheet.fields)

    def rows(self):
        if not self.worksheet:
            raise RuntimeError("Stream is not initialized (no worksheet)")
        iterator = self.worksheet.FindRecords(self.query_string).__iter__()
        return GDocRowIterator(self.fields.names(), iterator)

    def records(self):
        if not self.worksheet:
            raise RuntimeError("Stream is not initialized (no worksheet)")
        iterator = self.worksheet.FindRecords(self.query_string).__iter__()
        return GDocRecordIterator(self.fields.names(), iterator)

class GDocRowIterator(object):
    """
    Iterator that returns immutable list (tuple) of values
    """
    def __init__(self, field_names, iterator):
        self.iterator = iterator
        self.field_names = field_names

    def __iter__(self):
        return self

    def next(self):
        record = self.iterator.next()
        content = record.content
        values = [content[field] for field in self.field_names]
        return list(values)

class GDocRecordIterator(object):
    """
    Iterator that returns records as dict objects
    """
    def __init__(self, field_names, iterator):
        self.iterator = iterator
        self.field_names = field_names

    def __iter__(self):
        return self

    def next(self):
        record = self.iterator.next()
        return record.content

########NEW FILE########
__FILENAME__ = html_target
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base

class SimpleHTMLDataTarget(base.DataTarget):
    def __init__(self, resource, html_header = True, html_footer = None, 
                 write_headers = True, table_attributes = None,
                ):
        """Creates a HTML data target with simple naive HTML generation. No package that generates
        document node tree is used, just plain string concatenation.
        
        :Attributes:
            * resource: target object - might be a filename or file-like object - you can stream
              HTML table data into existing opened file.
            * write_headers: create table headers, default: True. Field labels will be used,
              if field has no label, then fieln name will be used.
            * table_attributes: <table> node attributes such as ``class``, ``id``, ...
            * html_header: string to be used as HTML header. If set to ``None`` only <table> will
              be generated. If set to ``True`` then default header is used. Default is ``True``.
            * html_header: string to be used as HTML footer. Works in similar way as to html_header.

        Note: No HTML escaping is done. HTML tags in data might break the output.
        """

        self.resource = resource
        self.write_headers = write_headers
        self.table_attributes = table_attributes
        
        if html_header == True:
            self.html_header = """
            <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
            <html>
            <head>
            <meta http-equiv="Content-type" content="text/html; charset=utf-8" />
            </head>
            <body>
            """
        elif html_header and html_header != True:
            self.html_header = html_header
        else:
            self.html_header = ""
            
        if html_footer == True:
            self.html_footer = """
            </body>"""
        elif html_footer and html_footer != True:
            self.html_footer = html_footer
        else:
            self.html_footer = ""
        
    def initialize(self):
        self.handle, self.close_file = base.open_resource(self.resource, "w")

        if self.html_header:
            self.handle.write(self.html_header)

        attr_string = u""

        if self.table_attributes:
            for attr_value in self.table_attributes.items():
                attr_string += u' %s="%s"\n' % attr_value

        string = u"<table%s>\n" % attr_string
            
        if self.write_headers:
            string += u"<tr>"
            for field in self.fields:
                if field.label:
                    header = field.label
                else:
                    header = field.name
                
                string += u"  <th>%s</th>\n" % header

            string += u"</tr>\n"
            
        self.handle.write(string)
        
    def append(self, obj):
        if type(obj) == dict:
            row = []
            for field in self.fields.names():
                row.append(obj.get(field))
        else:
            row = obj

        string = u"<tr>"
        for value in row:
            string += u"  <td>%s</td>\n" % value

        string += u"</tr>\n"
        self.handle.write(string.encode('utf-8'))

    def finalize(self):
        string = u"</table>"
        self.handle.write(string)

        if self.html_footer:
            self.handle.write(self.html_footer)
        
        if self.close_file:
            self.handle.close()
        
########NEW FILE########
__FILENAME__ = mongo_streams
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base
import brewery.dq

try:
    import pymongo
except ImportError:
    from brewery.utils import MissingPackage
    pymongo = MissingPackage("pymongo", "MongoDB streams", "http://www.mongodb.org/downloads/")

class MongoDBDataSource(base.DataSource):
    """docstring for ClassName
    """
    def __init__(self, collection, database=None, host=None, port=None,
                 expand=False, **mongo_args):
        """Creates a MongoDB data source stream.

        :Attributes:
            * collection: mongo collection name
            * database: database name
            * host: mongo database server host, default is ``localhost``
            * port: mongo port, default is ``27017``
            * expand: expand dictionary values and treat children as top-level keys with dot '.'
                separated key path to the child..
        """

        self.collection_name = collection
        self.database_name = database
        self.host = host
        self.port = port
        self.mongo_args = mongo_args
        self.expand = expand

        self.collection = None
        self.fields = None

    def initialize(self):
        """Initialize Mongo source stream:
        """

        args = self.mongo_args.copy()
        if self.host:
            args["host"] = self.host
        if self.port:
            args["port"] = self.port

        self.connection = pymongo.connection.Connection(**args)
        self.database = self.connection[self.database_name]
        self.collection = self.database[self.collection_name]


    def read_fields(self, limit=0):
        keys = []
        probes = {}

        def probe_record(record, parent=None):
            for key, value in record.items():
                if parent:
                    full_key = parent + "." + key
                else:
                    full_key = key

                if self.expand and type(value) == dict:
                    probe_record(value, full_key)
                    continue

                if not full_key in probes:
                    probe = brewery.dq.FieldTypeProbe(full_key)
                    probes[full_key] = probe
                    keys.append(full_key)
                else:
                    probe = probes[full_key]
                probe.probe(value)

        for record in self.collection.find(limit=limit):
            probe_record(record)

        fields = []

        for key in keys:
            probe = probes[key]
            field = base.Field(probe.field)

            storage_type = probe.unique_storage_type
            if not storage_type:
                field.storage_type = "unknown"
            elif storage_type == "unicode":
                field.storage_type = "string"
            else:
                field.storage_type = "unknown"
                field.concrete_storage_type = storage_type

            # FIXME: Set analytical type

            fields.append(field)

        self.fields = list(fields)
        return self.fields

    def rows(self):
        if not self.collection:
            raise RuntimeError("Stream is not initialized")
        fields = self.fields.names
        iterator = self.collection.find(fields=fields)
        return MongoDBRowIterator(iterator, fields)

    def records(self):
        if not self.collection:
            raise RuntimeError("Stream is not initialized")
        # return MongoDBRowIterator(self.field_names, self.collection.find())
        if self.fields:
            fields = self.fields.names()
        else:
            fields = None
        iterator = self.collection.find(fields=fields)
        return MongoDBRecordIterator(iterator, self.expand)

class MongoDBRowIterator(object):
    """Wrapper for pymongo.cursor.Cursor to be able to return rows() as tuples and records() as
    dictionaries"""
    def __init__(self, cursor, field_names):
        self.cursor = cursor
        self.field_names = field_names

    def __iter__(self):
        return self

    def next(self):
        record = self.cursor.next()

        if not record:
            raise StopIteration

        array = []

        # FIXME: make use of self.expand

        for field in self.field_names:
            value = record
            for key in field.split('.'):
                if key in value:
                    value = value[key]
                else:
                    break
            array.append(value)

        return tuple(array)

def collapse_record(record, parent=None):
    ret = {}
    for key, value in record.items():
        if parent:
            full_key = parent + "." + key
        else:
            full_key = key

        if type(value) == dict:
            expanded = collapse_record(value, full_key)
            ret.update(expanded)
        else:
            ret[full_key] = value
    return ret

class MongoDBRecordIterator(object):
    """Wrapper for pymongo.cursor.Cursor to be able to return rows() as tuples and records() as
    dictionaries"""
    def __init__(self, cursor, expand=False):
        self.cursor = cursor
        self.expand = expand

    def __iter__(self):
        return self

    def next(self):
        record = self.cursor.next()

        if not record:
            raise StopIteration

        if not self.expand:
            return record
        else:
            return collapse_record(record)

class MongoDBDataTarget(base.DataTarget):
    """docstring for ClassName
    """
    def __init__(self, collection, database=None, host=None, port=None,
                 truncate=False, expand=False, **mongo_args):
        """Creates a MongoDB data target stream.

        :Attributes:
            * collection: mongo collection name
            * database: database name
            * host: mongo database server host, default is ``localhost``
            * port: mongo port, default is ``27017``
            * expand: expand dictionary values and treat children as top-level keys with dot '.'
                separated key path to the child..
            * truncate: delete existing data in the collection. Default: False
        """

        self.collection_name = collection
        self.database_name = database
        self.host = host
        self.port = port
        self.mongo_args = mongo_args
        self.expand = expand
        self.truncate = truncate

        self.collection = None
        self.fields = None

    def initialize(self):
        """Initialize Mongo source stream:
        """

        args = self.mongo_args.copy()
        if self.host:
            args["host"] = self.host
        if self.port:
            args["port"] = self.port

        self.connection = pymongo.connection.Connection(**args)
        self.database = self.connection[self.database_name]
        self.collection = self.database[self.collection_name]

        if self.truncate:
            self.collection.remove()

        self.field_names = self.fields.names()

    def append(self, obj):
        if type(obj) == dict:
            record = obj
        else:
            record = dict(zip(self.field_names, obj))

        if self.expand:
            record = base.expand_record(record)

        self.collection.insert(record)

########NEW FILE########
__FILENAME__ = sql_streams
# -*- coding: utf-8 -*-

import base
import brewery.metadata

try:
    import sqlalchemy

    # (sql type, storage type, analytical type)
    _sql_to_brewery_types = (
        (sqlalchemy.types.UnicodeText, "text", "typeless"),
        (sqlalchemy.types.Text, "text", "typeless"),
        (sqlalchemy.types.Unicode, "string", "set"),
        (sqlalchemy.types.String, "string", "set"),
        (sqlalchemy.types.Integer, "integer", "discrete"),
        (sqlalchemy.types.Numeric, "float", "range"),
        (sqlalchemy.types.DateTime, "date", "typeless"),
        (sqlalchemy.types.Date, "date", "typeless"),
        (sqlalchemy.types.Time, "unknown", "typeless"),
        (sqlalchemy.types.Interval, "unknown", "typeless"),
        (sqlalchemy.types.Boolean, "boolean", "flag"),
        (sqlalchemy.types.Binary, "unknown", "typeless")
    )

    concrete_sql_type_map = {
        "string": sqlalchemy.types.Unicode,
        "text": sqlalchemy.types.UnicodeText,
        "date": sqlalchemy.types.Date,
        "time": sqlalchemy.types.DateTime,
        "integer": sqlalchemy.types.Integer,
        "float": sqlalchemy.types.Numeric,
        "boolean": sqlalchemy.types.SmallInteger
    }
except:
    from brewery.utils import MissingPackage
    sqlalchemy = MissingPackage("sqlalchemy", "SQL streams", "http://www.sqlalchemy.org/",
                                comment = "Recommended version is > 0.7")
    _sql_to_brewery_types = ()
    concrete_sql_type_map = {}

def split_table_schema(table_name):
    """Get schema and table name from table reference.

    Returns: Tuple in form (schema, table)
    """

    split = table_name.split('.')
    if len(split) > 1:
        return (split[0], split[1])
    else:
        return (None, split[0])


class SQLContext(object):
    """Holds context of SQL store operations."""

    def __init__(self, url=None, connection=None, schema=None):
        """Creates a SQL context"""

        if not url and not connection:
            raise AttributeError("Either url or connection should be provided" \
                                 " for SQL data source")

        super(SQLContext, self).__init__()

        if connection:
            self.connection = connection
            self.should_close = False
        else:
            engine = sqlalchemy.create_engine(url)
            self.connection = engine.connect()
            self.should_close = True

        self.metadata = sqlalchemy.MetaData()
        self.metadata.bind = self.connection.engine
        self.schema = schema

    def close(self):
        if self.should_close and self.connection:
            self.connection.close()

    def table(self, name, autoload=True):
        """Get table by name"""

        return sqlalchemy.Table(name, self.metadata,
                                autoload=autoload, schema=self.schema)

def fields_from_table(table):
    """Get fields from a table. Field types are normalized to the Brewery
    data types. Analytical type is set according to a default conversion
    dictionary."""

    fields = []

    for column in table.columns:
        field = brewery.metadata.Field(name=column.name)
        field.concrete_storage_type = column.type

        for conv in _sql_to_brewery_types:
            if issubclass(column.type.__class__, conv[0]):
                field.storage_type = conv[1]
                field.analytical_type = conv[2]
                break

        if not field.storage_type:
            field.storaget_tpye = "unknown"

        if not field.analytical_type:
            field.analytical_type = "unknown"

        fields.append(field)

    return brewery.metadata.FieldList(fields)

def concrete_storage_type(field, type_map={}):
    """Derives a concrete storage type for the field based on field conversion
       dictionary"""

    concrete_type = field.concrete_storage_type

    if not isinstance(concrete_type, sqlalchemy.types.TypeEngine):
        if type_map:
            concrete_type = type_map.get(field.storage_type)

        if not concrete_type:
            concrete_type = concrete_sql_type_map.get(field.storage_type)

        if not concrete_type:
            raise ValueError("unable to find concrete storage type for field '%s' "
                             "of type '%s'" % (field.name, field.storage_type))

    return concrete_type

class SQLDataSource(base.DataSource):
    """docstring for ClassName
    """
    def __init__(self, connection=None, url=None,
                    table=None, statement=None, schema=None, autoinit = True,
                    **options):
        """Creates a relational database data source stream.

        :Attributes:
            * url: SQLAlchemy URL - either this or connection should be specified
            * connection: SQLAlchemy database connection - either this or url should be specified
            * table: table name
            * statement: SQL statement to be used as a data source (not supported yet)
            * autoinit: initialize on creation, no explicit initialize() is
              needed
            * options: SQL alchemy connect() options
        """

        super(SQLDataSource, self).__init__()

        if not table and not statement:
            raise AttributeError("Either table or statement should be " \
                                 "provided for SQL data source")

        if statement:
            raise NotImplementedError("SQL source stream based on statement " \
                                      "is not yet implemented")

        if not options:
            options = {}

        self.url = url
        self.connection = connection

        self.table_name = table
        self.statement = statement
        self.schema = schema
        self.options = options

        self.context = None
        self.table = None
        self.fields = None

        if autoinit:
            self.initialize()

    def initialize(self):
        """Initialize source stream. If the fields are not initialized, then
        they are read from the table.
        """
        if not self.context:
            self.context = SQLContext(self.url, self.connection, self.schema)
        if self.table is None:
            self.table = self.context.table(self.table_name)
        if not self.fields:
            self.read_fields()
        self.field_names = self.fields.names()

    def finalize(self):
        self.context.close()

    def read_fields(self):
        self.fields = fields_from_table(self.table)
        return self.fields

    def rows(self):
        if not self.context:
            raise RuntimeError("Stream is not initialized")
        return self.table.select().execute()

    def records(self):
        if not self.context:
            raise RuntimeError("Stream is not initialized")
        fields = self.field_names
        for row in self.rows():
            record = dict(zip(fields, row))
            yield record

class SQLDataTarget(base.DataTarget):
    """docstring for ClassName
    """
    def __init__(self, connection=None, url=None,
                    table=None, schema=None, truncate=False,
                    create=False, replace=False,
                    add_id_key=False, id_key_name=None,
                    buffer_size=None, fields=None, concrete_type_map=None,
                    **options):
        """Creates a relational database data target stream.

        :Attributes:
            * url: SQLAlchemy URL - either this or connection should be specified
            * connection: SQLAlchemy database connection - either this or url should be specified
            * table: table name
            * truncate: whether truncate table or not
            * create: whether create table on initialize() or not
            * replace: Set to True if creation should replace existing table or not, otherwise
              initialization will fail on attempt to create a table which already exists.
            * options: other SQLAlchemy connect() options
            * add_id_key: whether to add auto-increment key column or not. Works only if `create`
              is ``True``
            * id_key_name: name of the auto-increment key. Default is 'id'
            * buffer_size: size of INSERT buffer - how many records are collected before they are
              inserted using multi-insert statement. Default is 1000
            * fields : fieldlist for a new table

        Note: avoid auto-detection when you are reading from remote URL stream.

        """
        if not options:
            options = {}

        self.url = url
        self.connection = connection
        self.table_name = table
        self.schema = schema
        self.options = options
        self.replace = replace
        self.create = create
        self.truncate = truncate
        self.add_id_key = add_id_key

        self.table = None
        self.fields = fields

        self.concrete_type_map = concrete_type_map

        if id_key_name:
            self.id_key_name = id_key_name
        else:
            self.id_key_name = 'id'

        if buffer_size:
            self.buffer_size = buffer_size
        else:
            self.buffer_size = 1000

    def initialize(self):
        """Initialize source stream:
        """

        self.context = SQLContext(url=self.url,
                                  connection=self.connection,
                                  schema=self.schema)

        if self.create:
            self.table = self._create_table()
        else:
            self.table = self.context.table(self.table_name)

        if self.truncate:
            self.table.delete().execute()

        if not self.fields:
            self.fields = fields_from_table(self.table)

        self.field_names = self.fields.names()

        self.insert_command = self.table.insert()
        self._buffer = []

    def _create_table(self):
        """Create a table."""

        if not self.fields:
            raise Exception("Can not create a table: No fields provided")

        table = self.context.table(self.table_name, autoload=False)

        if table.exists():
            if self.replace:
                table = self.context.table(self.table_name, autoload=False)
                table.drop(checkfirst=False)
            else:
                raise ValueError("Table '%s' already exists" % self.table_name)

        table = sqlalchemy.Table(self.table_name, self.context.metadata, schema=self.schema)

        if self.add_id_key:
            id_key_name = self.id_key_name or 'id'

            sequence_name = "seq_" + self.table_name + "_" + id_key_name
            sequence = sqlalchemy.schema.Sequence(sequence_name, optional=True)

            col = sqlalchemy.schema.Column(id_key_name,
                                           sqlalchemy.types.Integer,
                                           sequence, primary_key=True)
            table.append_column(col)

        for field in self.fields:
            # FIXME: hey, what about duck-typing?
            if not isinstance(field, brewery.metadata.Field):
                raise ValueError("field %s is not subclass of brewery.metadata.Field" % (field))

            concrete_type = concrete_storage_type(field, self.concrete_type_map)

            col = sqlalchemy.schema.Column(field.name, concrete_type)
            table.append_column(col)

        table.create()

        return table


    def finalize(self):
        """Closes the stream, flushes buffered data"""

        self._flush()
        self.context.close()

    def append(self, obj):
        if type(obj) == dict:
            record = obj
        else:
            record = dict(zip(self.field_names, obj))

        self._buffer.append(record)
        if len(self._buffer) >= self.buffer_size:
            self._flush()

    def _flush(self):
        if len(self._buffer) > 0:
            self.context.connection.execute(self.insert_command, self._buffer)
            self._buffer = []

########NEW FILE########
__FILENAME__ = stream_auditor
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base
from brewery import dq

class StreamAuditor(base.DataTarget):
    """Target stream for auditing data values from stream. For more information about probed value
    properties, please refer to :class:`brewery.dq.FieldStatistics`"""
    def __init__(self, distinct_threshold = 10):
        super(StreamAuditor, self).__init__()

        self.record_count = 0
        self.stats = {}
        self.distinct_threshold = distinct_threshold
        self._field_names = None
        
    def initialize(self):
        self.record_count = 0

    def append(self, obj):
        """Probe row or record and update statistics."""
        self.record_count += 1
        
        if type(obj) == dict:
            self._probe_record(obj)
        else:
            self._probe_row(obj)
    
    def _probe_record(self, record):
        for field, value in record.items():
            stat = self._field_stat(field)
            stat.probe(value)

    def _probe_row(self, row):
        if not self.fields:
            raise ValueError("Fields are not initialized")
        for i, field in enumerate(self.fields.names()):
            stat = self._field_stat(field)
            value = row[i]
            stat.probe(value)

    def finalize(self):
        for key, stat in self.stats.items():
            stat.finalize(self.record_count)

    def _field_stat(self, field):
        """Get single field statistics. Create if does not exist"""
        if not field in self.stats:
            stat = dq.FieldStatistics(field, distinct_threshold = self.distinct_threshold)
            self.stats[field] = stat
        else:
            stat = self.stats[field]
        return stat
        
    @property        
    def field_statistics(self):
        """Return field statistics as dictionary: keys are field names, values are 
        :class:`brewery.dq.FieldStatistics` objects"""
        return self.stats


########NEW FILE########
__FILENAME__ = xls_streams
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base
import datetime
from brewery.metadata import FieldList

try:
    import xlrd
except:
    from brewery.utils import MissingPackage
    xlrd = MissingPackage("xlrd", "Reading MS Excel XLS Files", "http://pypi.python.org/pypi/xlrd")

class XLSDataSource(base.DataSource):
    """Reading Microsoft Excel XLS Files

    Requires the xlrd package (see pypi).

    Based on the OKFN Swiss library.
    """
    def __init__(self, resource, sheet=None, encoding=None, skip_rows=None, read_header=True):
        """Creates a XLS spreadsheet data source stream.
        
        :Attributes:
            * resource: file name, URL or file-like object
            * sheet: sheet index number (as int) or sheet name (as str)
            * read_header: flag determining whether first line contains header or not. 
                ``True`` by default.
        """
        self.resource = resource
        self.sheet_reference = sheet
        self.read_header = read_header
        self.header_row = 0
        self.skip_rows = skip_rows
        self._fields = None
        self.close_file = True
        self.encoding = encoding
        self.fields = None

    def initialize(self):
        """Initialize XLS source stream:
        """

        self.file, self.close_file = base.open_resource(self.resource)

        self.workbook = xlrd.open_workbook(file_contents=self.file.read(),
                                           encoding_override=self.encoding)

        if not self.sheet_reference:
            self.sheet_reference = 0

        if type(self.sheet_reference) == int:
            self.sheet = self.workbook.sheet_by_index(self.sheet_reference)
        else:
            self.sheet = self.workbook.sheet_by_name(self.sheet_reference)

        self.row_count = self.sheet.nrows

        self.read_fields()

    def finalize(self):
        if self.file and self.close_file:
            self.file.close()

    def rows(self):
        if not self.sheet:
            raise RuntimeError("XLS Stream is not initialized - there is no sheet")
        if not self.fields:
            raise RuntimeError("Fields are not initialized")
        return XLSRowIterator(self.workbook, self.sheet, self.skip_rows)

    def records(self):
        fields = self.fields.names()
        for row in self.rows():
            yield dict(zip(fields, row))

    def read_fields(self):
        # FIXME: be more sophisticated and read field types from next row
        if self.read_header:
            row = self.sheet.row_values(self.header_row)
            self.fields = FieldList(row)
            self.skip_rows = self.header_row + 1

class XLSRowIterator(object):
    """
    Iterator that reads XLS spreadsheet
    """
    def __init__(self, workbook, sheet, row_offset=0):
        self.workbook = workbook
        self.sheet = sheet
        self.row_count = sheet.nrows
        if row_offset:
            self.current_row = row_offset
        else:
            self.current_row = 0

    def __iter__(self):
        return self

    def next(self):
        if self.current_row >= self.row_count:
            raise StopIteration

        row = self.sheet.row(self.current_row)
        row = [self._cell_value(cell) for cell in row]
        self.current_row += 1
        return row

    def _cell_value(self, cell):
        """Convert Excel cell into value of a python type
        
        (from Swiss XlsReader.cell_to_python)"""

        # annoying need book argument for datemode
        # info on types: http://www.lexicon.net/sjmachin/xlrd.html#xlrd.Cell-class
        if cell.ctype == xlrd.XL_CELL_NUMBER:
            return float(cell.value)
        elif cell.ctype == xlrd.XL_CELL_DATE:
            # TODO: distinguish date and datetime
            args = xlrd.xldate_as_tuple(cell.value, self.workbook.datemode)
            try:
                return datetime.date(args[0], args[1], args[2])
            except Exception, inst:
                # print 'Error parsing excel date (%s): %s' % (args, inst)
                return None
        elif cell.ctype == xlrd.XL_CELL_BOOLEAN:
            return bool(cell.value)
        else:
            return cell.value

########NEW FILE########
__FILENAME__ = yaml_dir_streams
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base
import string
import os
import shutil

try:
    import yaml
except:
    from brewery.utils import MissingPackage
    yaml = MissingPackage("PyYAML", "YAML directory data source/target", "http://pyyaml.org/")

class YamlDirectoryDataSource(base.DataSource):
    """docstring for ClassName
    """
    def __init__(self, path, extension="yml", expand=False, filename_field=None):
        """Creates a YAML directory data source stream.
        
        The data source reads files from a directory and treats each file as single record. For example,
        following directory will contain 3 records::
        
            data/
                contract_0.yml
                contract_1.yml
                contract_2.yml
        
        Optionally one can specify a field where file name will be stored.
        
        
        :Attributes:
            * path: directory with YAML files
            * extension: file extension to look for, default is ``yml``,if none is given, then
              all regular files in the directory are read
            * expand: expand dictionary values and treat children as top-level keys with dot '.'
                separated key path to the child.. Default: False
            * filename_field: if present, then filename is streamed in a field with given name,
              or if record is requested, then filename will be in first field.
        
        """
        self.path = path
        self.expand = expand
        self.filename_field = filename_field
        self.extension = extension

    def initialize(self):
        pass

    def records(self):
        files = os.listdir(self.path)

        for base_name in files:
            split = os.path.splitext(base_name)
            if split[1] != self.extension:
                pass

            # Read yaml file
            handle = open(os.path.join(self.path, base_name), "r")
            record = yaml.load(handle)
            handle.close()

            # Include filename in output record if requested
            if self.filename_field:
                record[self.filename_field] = base_name

            yield record

    def rows(self):
        if not self.fields:
            raise Exception("Fields are not initialized, can not generate rows")
            
        field_names = self.fields.names()

        for record in self.records():
            row = [record.get(field) for field in field_names]
            yield row


class YamlDirectoryDataTarget(base.DataTarget):
    """docstring for YamlDirectoryDataTarget
    """
    def __init__(self, path, filename_template="record_${__index}.yml", expand=False,
                    filename_start_index=0, truncate=False):
        """Creates a directory data target with YAML files as records.
        
        :Attributes:
            * path: directory with YAML files
            * extension: file extension to use
            * expand: expand dictionary values and treat children as top-level keys with dot '.'
              separated key path to the child.. Default: False
            * filename_template: template string used for creating file names. ``${key}`` is replaced
              with record value for ``key``. ``__index`` is used for auto-generated file index from
              `filename_start_index`. Default filename template is ``record_${__index}.yml`` which
              results in filenames ``record_0.yml``, ``record_1.yml``, ...
            * filename_start_index - first value of ``__index`` filename template value, by default 0
            * filename_field: if present, then filename is taken from that field.
            * truncate: remove all existing files in the directory. Default is ``False``.

        """

        self.filename_template = filename_template
        self.filename_start_index = filename_start_index
        self.path = path
        self.expand = expand
        self.truncate = truncate

    def initialize(self):
        self.template = string.Template(self.filename_template)
        self.index = self.filename_start_index

        if os.path.exists(self.path):
            if not os.path.isdir(self.path):
                raise Exception("Path %s is not a directory" % self.path)
            elif self.truncate:
                shutil.rmtree(self.path)
                os.makedirs(self.path)
        else:
            os.makedirs(self.path)


    def append(self, obj):

        if type(obj) == dict:
            record = obj
        else:
            record = dict(zip(self.fields.names(), obj))

        base_name = self.template.substitute(__index=self.index, **record)
        path = os.path.join(self.path, base_name)

        handle = open(path, "w")
        yaml.safe_dump(record, stream=handle, encoding=None, default_flow_style=False)
        handle.close()

        self.index += 1

########NEW FILE########
__FILENAME__ = graph
from collections import OrderedDict
from brewery.utils import get_logger

class Graph(object):
    """Data processing stream"""
    def __init__(self, nodes=None, connections=None):
        """Creates a node graph with connections.

        :Parameters:
            * `nodes` - dictionary with keys as node names and values as nodes
            * `connections` - list of two-item tuples. Each tuple contains source and target node
              or source and target node name.
        """

        super(Graph, self).__init__()
        self.nodes = OrderedDict()
        self.connections = set()

        self.logger = get_logger()

        self._name_sequence = 1

        if nodes:
            try:
                for name, node in nodes.items():
                    self.add(node, name)
            except:
                raise ValueError("Nodes should be a dictionary, is %s" % type(nodes))

        if connections:
            for connection in connections:
                self.connect(connection[0], connection[1])

    def _generate_node_name(self):
        """Generates unique name for a node"""
        while 1:
            name = "node" + str(self._name_sequence)
            if name not in self.nodes.keys():
                break
            self._name_sequence += 1

        return name

    def add(self, node, name=None):
        """Add a `node` into the stream. Does not allow to add named node if
        node with given name already exists. Generate node name if not
        provided. Node name is generated as ``node`` + sequence number.
        Uniqueness is tested."""

        name = name or self._generate_node_name()

        if name in self.nodes:
            raise KeyError("Node with name %s already exists" % name)

        self.nodes[name] = node

        return name

    def node_name(self, node):
        """Returns name of `node`."""
        # There should not be more
        if not node:
            raise ValueError("No node provided")

        names = [key for key,value in self.nodes.items() if value==node]

        if len(names) == 1:
            return names[0]
        elif len(names) > 1:
            raise Exception("There are more references to the same node")
        else: # if len(names) == 0
            raise Exception("Can not find node '%s'" % node)

    def node(self, name):
        """Return node with name `name`."""
        return self.nodes[name]

    def rename_node(self, node, name):
        """Sets a name for `node`. Raises an exception if the `node` is not
        part of the stream, if `name` is empty or there is already node with
        the same name. """

        if not name:
            raise ValueError("No node name provided for rename")
        if name in self.nodes():
            raise ValueError("Node with name '%s' already exists" % name)

        old_name = self.node_name(node)

        del self.nodes[old_name]
        self.nodes[name] = node

    def coalesce_node(self, reference):
        """Coalesce node reference: `reference` should be either a node name
        or a node. Returns the node object."""

        if isinstance(reference, basestring):
            return self.nodes[reference]
        elif reference in self.nodes.values():
            return reference
        else:
            raise ValueError("Unable to find node '%s'" % reference)

    def remove(self, node):
        """Remove a `node` from the stream. Also all connections will be
        removed."""

        # Allow node name, get the real node object
        if isinstance(node, basestring):
            name = node
            node = self.nodes[name]
        else:
            name = self.node_name(node)

        del self.nodes[name]

        remove = [c for c in self.connections if c[0] == node or c[1] == node]

        for connection in remove:
            self.connections.remove(connection)

    def connect(self, source, target):
        """Connects source node and target node. Nodes can be provided as
        objects or names."""
        connection = (self.coalesce_node(source), self.coalesce_node(target))
        self.connections.add(connection)

    def remove_connection(self, source, target):
        """Remove connection between source and target nodes, if exists."""

        connection = (self.coalesce_node(source), self.coalesce_node(target))
        self.connections.discard(connection)

    def sorted_nodes(self):
        """
        Return topologically sorted nodes.

        Algorithm::

            L = Empty list that will contain the sorted elements
            S = Set of all nodes with no incoming edges
            while S is non-empty do
                remove a node n from S
                insert n into L
                for each node m with an edge e from n to m do
                    remove edge e from the graph
                    if m has no other incoming edges then
                        insert m into S
            if graph has edges then
                raise exception: graph has at least one cycle
            else
                return proposed topologically sorted order: L
        """
        def is_source(node, connections):
            for connection in connections:
                if node == connection[1]:
                    return False
            return True

        def source_connections(node, connections):
            conns = set()
            for connection in connections:
                if node == connection[0]:
                    conns.add(connection)
            return conns

        nodes = set(self.nodes.values())
        connections = self.connections.copy()
        sorted_nodes = []

        # Find source nodes:
        source_nodes = set([n for n in nodes if is_source(n, connections)])

        # while S is non-empty do
        while source_nodes:
            # remove a node n from S
            node = source_nodes.pop()
            # insert n into L
            sorted_nodes.append(node)

            # for each node m with an edge e from n to m do
            s_connections = source_connections(node, connections)
            for connection in s_connections:
                #     remove edge e from the graph
                m = connection[1]
                connections.remove(connection)
                #     if m has no other incoming edges then
                #         insert m into S
                if is_source(m, connections):
                    source_nodes.add(m)

        # if graph has edges then
        #     output error message (graph has at least one cycle)
        # else
        #     output message (proposed topologically sorted order: L)

        if connections:
            raise Exception("Steram has at least one cycle (%d connections left of %d)" % (len(connections), len(self.connections)))

        return sorted_nodes

    def node_targets(self, node):
        """Return nodes that `node` passes data into."""
        node = self.coalesce_node(node)
        nodes =[conn[1] for conn in self.connections if conn[0] == node]
        return nodes

    def node_sources(self, node):
        """Return nodes that provide data for `node`."""
        node = self.coalesce_node(node)
        nodes =[conn[0] for conn in self.connections if conn[1] == node]
        return nodes

########NEW FILE########
__FILENAME__ = metadata
import copy
import itertools
import functools
import re
# from collections import OrderedDict

__all__ = [
    "Field",
    "FieldList",
    "fieldlist", # FIXME remove this
    "expand_record",
    "collapse_record",
    "FieldMap",
    "storage_types",
    "analytical_types",
    "coalesce_value"
]

"""Abstracted field storage types"""
storage_types = ("unknown", "string", "text", "integer", "float",
                 "boolean", "date", "array")

"""Analytical types used by analytical nodes"""
analytical_types = ("default", "typeless", "flag", "discrete", "range",
                    "set", "ordered_set")

"""Mapping between storage types and their respective default analytical
types"""
# NOTE: For the time being, this is private
default_analytical_types = {
                "unknown": "typeless",
                "string": "typeless",
                "text": "typeless",
                "integer": "discrete",
                "float": "range",
                "date": "typeless",
                "array": "typeless"
            }

_valid_retype_attributes = ("storage_type",
                     "analytical_type",
                     "concrete_storage_type",
                     "missing_values")

# FIXME: Depreciated - why it is here, if we have FieldList class?!
def fieldlist(fields):
    # FIXME: print some warning here
    raise DeprecationWarning
    return FieldList(fields)

def expand_record(record, separator = '.'):
    """Expand record represented as dict object by treating keys as key paths separated by
    `separator`, which is by default ``.``. For example: ``{ "product.code": 10 }`` will become
    ``{ "product" = { "code": 10 } }``

    See :func:`brewery.collapse_record` for reverse operation.
    """
    result = {}
    for key, value in record.items():
        current = result
        path = key.split(separator)
        for part in path[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[path[-1]] = value
    return result

def collapse_record(record, separator = '.', root = None):
    """See :func:`brewery.expand_record` for reverse operation.
    """

    result = {}
    for key, value in record.items():
        if root:
            collapsed_key = root + separator + key
        else:
            collapsed_key = key

        if type(value) == dict:
            collapsed = collapse_record(value, separator, collapsed_key)
            result.update(collapsed)
        else:
            result[collapsed_key] = value
    return result

def to_field(obj):
    """Converts `obj` to a field object. `obj` can be ``str``, ``tuple``
    (``list``), ``dict`` object or :class:`Field` object. If it is `Field`
    instance, then same object is passed.

    If field is not a `Field` instance, then construction of new field is as follows:

    ``str``:
        `field name` is set

    ``tuple``:
        (`field_name`, `storaget_type`, `analytical_type`), the `field_name` is
        obligatory, rest is optional

    ``dict``
        contains key-value pairs for initializing a :class:`Field` object

    Attributes of a field that are not specified in the `obj` are filled as:
    `storage_type` is set to ``unknown``, `analytical_type` is set to
    ``typeless``
    """


    if isinstance(obj, Field):
        field = obj
    else:
        d = { "storage_type": "unknown" }

        if isinstance(obj, basestring):
            d["name"] = obj
        elif type(obj) == tuple or type(obj) == list:
            d["name"] = obj[0]
            try:
                d["storage_type"] = obj[1]
                try:
                    d["analytical_type"] = obj[2]
                except:
                    pass
            except:
                pass
        else: # assume dictionary
            d["name"] = obj["name"]
            d["label"] = obj.get("label")
            d["storage_type"] = obj.get("storage_type")
            d["analytical_type"] = obj.get("analytical_type")
            d["adapter_storage_type"] = obj.get("adapter_storage_type")

        if "analytical_type" not in d:
            storage_type = d.get("storage_type")
            if storage_type:
                deftype = default_analytical_types.get(storage_type)
                d["analytical_type"] = deftype or "typeless"
            else:
                d["analytical_type"] = "typeless"

        field = Field(**d)
    return field

class Field(object):
    """Metadata - information about a field in a dataset or in a datastream.

    :Attributes:
        * `name` - field name
        * `label` - optional human readable field label
        * `storage_type` - Normalized data storage type. The data storage type
          is abstracted
        * `concrete_storage_type` (optional, recommended) - Data store/database
          dependent storage type - this is the real name of data type as used
          in a database where the field comes from or where the field is going
          to be created (this might be null if unknown)
        * `analytical_type` - data type used in data mining algorithms
        * `missing_values` (optional) - Array of values that represent missing
          values in the dataset for given field
    """

    def __init__(self, name, storage_type="unknown",
                 analytical_type="typeless", concrete_storage_type=None,
                 missing_values=None, label=None):
        self.name = name
        self.label = label
        self.storage_type = storage_type
        self.analytical_type = analytical_type
        self.concrete_storage_type = concrete_storage_type
        self.missing_values = missing_values

    def to_dict(self):
        """Return dictionary representation of the field."""
        d = {
                "name": self.name,
                "label": self.label,
                "storage_type": self.storage_type,
                "analytical_type": self.analytical_type,
                "concrete_storage_type": self.concrete_storage_type,
                "missing_values": self.missing_values
            }
        return d

    def __str__(self):
        """Return field name as field string representation."""

        return self.name

    def __repr__(self):
        return "<%s(%s)>" % (self.__class__, self.to_dict())

    def __eq__(self, other):
        if self is other:
            return True
        if self.name != other.name or self.label != other.label:
            return False
        elif self.storage_type != other.storage_type or self.analytical_type != other.analytical_type:
            return False
        elif self.concrete_storage_type != other.concrete_storage_type:
            return False
        elif self.missing_values != other.missing_values:
            return False
        else:
            return True

    def __ne__(self,other):
        return not self.__eq__(other)

class FieldList(object):
    """List of fields"""
    def __init__(self, fields = None):
        """
        Create a list of :class:`Field` objects from a list of strings, dictionaries or tuples

        How fields are consutrcuted:

        * string: `field name` is set
        * tuple: (`field_name`, `storaget_type`, `analytical_type`), the `field_name` is
          obligatory, rest is optional
        * dict: contains key-value pairs for initializing a :class:`Field` object

        For strings and in if not explicitly specified in a tuple or a dict case, then following rules
        apply:

        * `storage_type` is set to ``unknown``
        * `analytical_type` is set to ``typeless``
        """
        super(FieldList, self).__init__()

        # FIXME: use OrderedDict (Python 2.7+)
        self._fields = []
        self._field_dict = {}
        self._field_names = []

        if fields:
            # Convert input to Field instances
            # This is convenience, so one can pass list of strsings, for example

            for field in fields:
                self.append(field)

    def append(self, field):
        """Appends a field to the list. This method requires `field` to be
        instance of `Field`"""

        field = to_field(field)
        self._fields.append(field)
        self._field_dict[field.name] = field
        self._field_names.append(field.name)

    def names(self, indexes = None):
        """Return names of fields in the list.

        :Parameters:
            * `indexes` - list of indexes for which field names should be collected. If set to
              ``None`` then all field names are collected - this is default behaviour.
        """

        if indexes:
            names = [self._field_names[i] for i in indexes]
            return names
        else:
            return self._field_names

    def indexes(self, fields):
        """Return a tuple with indexes of fields from ``fields`` in a data row. Fields
        should be a list of ``Field`` objects or strings.

        This method is useful when it is more desirable to process data as rows (arrays), not as
        dictionaries, for example for performance purposes.
        """

        indexes = [self.index(field) for field in fields]

        return tuple(indexes)

    def selectors(self, fields = None):
        """Return a list representing field selector - which fields are
        selected from a row."""

        sel_names = [str(field) for field in fields]

        selectors = [unicode(name) in sel_names for name in self.names()]
        return selectors

    def index(self, field):
        """Return index of a field"""

        try:
            index = self._field_names.index(unicode(field))
        except ValueError:
            raise KeyError("Field list has no field with name '%s'" % unicode(field))

        return index

    def fields(self, names = None):
        """Return a tuple with fields. `names` specifies which fields are returned. When names is
        ``None`` all fields are returned.
        """

        if not names:
            return self._fields

        fields = [self._field_dict[name] for name in names]

        return fields

    def field(self, name):
        """Return a field with name `name`"""

        if name in self._field_dict:
            return self._field_dict[name]
        raise KeyError("Field list has no field with name '%s'" % name)

    def __len__(self):
        return len(self._fields)

    def __getitem__(self, index):
        return self._fields[index]

    def __setitem__(self, index, new_field):
        field = self._fields[index]
        del self._field_dict[field.name]
        self._fields[index] = new_field
        self._field_names[index] = new_field.name
        self._field_dict[new_field.name] = new_field

    def __delitem__(self, index):
        field = self._fields[index]
        del self._field_dict[field.name]
        del self._fields[index]
        del self._field_names[index]

    def __iter__(self):
        return self._fields.__iter__()

    def __contains__(self, field):
        if type(field) == str or type(field) == unicode:
            return field in self._field_names

        return field in self._fields

    def __iconcat__(self, array):
        for field in array:
            self.append(field)

    def __concat__(self, array):
        fields = self.copy()
        fields += array
        return fields

    def __str__(self):
        return "[" + ", ".join(self.names()) + "]"

    def copy(self, fields = None):
        """Return a shallow copy of the list.

        :Parameters:
            * `fields` - list of fields to be copied.
        """
        if fields is not None:
            copy_fields = self.fields(fields)
            return FieldList(copy_fields)
        else:
            return FieldList(self._fields)

    def retype(self, dictionary):
        """Retype fields according to the dictionary. Dictionary contains
        field names as keys and field attribute dictionary as values."""

        for name, retype in dictionary.items():
            field = self._field_dict[name]
            for key, value in retype.items():
                if key in _valid_retype_attributes:
                    field.__setattr__(key, value)
                else:
                    raise Exception("Should not use retype to change field attribute '%s'", key)

class FieldMap(object):
    """Filters fields in a stream"""
    def __init__(self, rename = None, drop = None, keep=None):
        """Creates a field map. `rename` is a dictionary where keys are input
        field names and values are output field names. `drop` is list of
        field names that will be dropped from the stream. If `keep` is used,
        then all fields are dropped except those specified in `keep` list."""
        if drop and keep:
            raise Exception('Configuration error in FieldMap: you cant specify both keep and drop options.')
        super(FieldMap, self).__init__()

        if rename:
            self.rename = rename
        else:
            self.rename = {}

        self.drop = drop or []
        self.keep = keep or []

    def map(self, fields):
        """Map `fields` according to the FieldMap: rename or drop fields as specified. Returns
        a FieldList object."""
        output_fields = FieldList()

        for field in fields:
            if field.name in self.rename:
                # Create a copy and rename field if it is mapped
                new_field = copy.copy(field)
                new_field.name = self.rename[field.name]
            else:
                new_field = field

            if (self.drop and field.name not in self.drop) or \
                (self.keep and field.name in self.keep) or \
                not (self.keep or self.drop):
                output_fields.append(new_field)

        return output_fields


    def row_filter(self, fields):
        """Returns an object that will convert rows with structure specified in `fields`. You can
        use the object to filter fields from a row (list, array) according to this map.
        """
        return RowFieldFilter(self.field_selectors(fields))

    def field_selectors(self, fields):
        """Returns selectors of fields to be used by `itertools.compress()`.
        This is the preferred way of field filtering.
        """

        selectors = []

        for field in fields:
            flag = (self.drop and field.name not in self.drop) \
                    or (self.keep and field.name in self.keep) \
                    or not (self.keep or self.drop)
            selectors.append(flag)

        return selectors


class RowFieldFilter(object):
    """Class for filtering fields in array"""

    def __init__(self, selectors = None):
        """Create an instance of RowFieldFilter. `indexes` is a list of indexes that are passed
        to output."""
        super(RowFieldFilter, self).__init__()
        self.selectors = selectors or []

    def __call__(self, row):
        return self.filter(row)

    def filter(self, row):
        """Filter a `row` according to ``indexes``."""
        return list(itertools.compress(row, self.selectors))

def coalesce_value(value, storage_type, empty_values=None, strip=False):
    """Coalesces `value` to given storage `type`. `empty_values` is a dictionary
    where keys are storage type names and values are values to be used
    as empty value replacements."""
    if empty_values is None:
        empty_values={}
    if storage_type in ["string", "text"]:
        if strip:
            value = value.strip()
        elif value:
            value = unicode(value)

        if value == "" or value is None:
            value = empty_values.get("string")
    elif storage_type == "integer":
        # FIXME: use configurable thousands separator (now uses space)
        if strip:
            value = re.sub(r"\s", "", value.strip())

        try:
            value = int(value)
        except ValueError:
            value = empty_values.get("integer")
    elif storage_type == "float":
        # FIXME: use configurable thousands separator (now uses space)
        if strip:
            value = re.sub(r"\s", "", value.strip())

        try:
            value = float(value)
        except ValueError:
            value = empty_values.get("float")
    elif storage_type == "list":
        # FIXME: undocumented type
        value = value.split(",")

    return value

########NEW FILE########
__FILENAME__ = base
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import brewery.utils as utils
import heapq

__all__ = (
    "create_node",
    "node_dictionary",
    "node_catalogue",
    "get_node_info",
    "NodeFinished",
    "Node",
    "SourceNode",
    "TargetNode",
    "Stack"
)

# FIXME: temporary dictionary to record displayed warnings about __node_info__
_node_info_warnings = set()

def create_node(identifier, *args, **kwargs):
    """Creates a node of type specified by `identifier`. Options are passed to
    the node initializer"""

    d = node_dictionary()
    node_class = d[identifier]
    node = node_class(*args, **kwargs)
    return node

def node_dictionary():
    """Return a dictionary containing node name as key and node class as
    value. This will be depreciated soon in favour of
    :func:`node_catalogue()`"""

    classes = node_subclasses(Node)
    dictionary = {}

    for c in classes:
        try:
            name = c.identifier()
            dictionary[name] = c
        except AttributeError:
            # If node does not provide identifier, we consider it to be
            # private or abstract class
            pass

    return dictionary

def node_catalogue():
    """Returns a dictionary of information about all available nodes. Keys are
    node identifiers, values are dictionaries. The information dictionary contains
    all the keys from the node's `node_info` dictionary plus keys: `factory`
    with node class, `type` (if not provided) is set to one of ``source``,
    ``processing`` or ``target``.
    """

    classes = node_subclasses(Node)

    catalogue = {}

    for node_class in classes:
        try:
            name = node_class.identifier()
        except AttributeError:
            # If node does not provide identifier, we consider it to be
            # private or abstract class
            continue

        # Get copy of node info
        info = dict(get_node_info(node_class))
        info["name"] = name
        info["factory"] = node_class

        # Get node type based on superclass, if not provided

        if "type" not in info:
            if issubclass(node_class, SourceNode):
                info["type"] = "source"
            elif not issubclass(node_class, SourceNode) \
                    and not issubclass(node_class, TargetNode):
                info["type"] = "processing"
            elif issubclass(node_class, TargetNode):
                info["type"] = "target"
            else:
                info["type"] = "unknown"

        catalogue[name] = info

    return catalogue

def node_subclasses(root, abstract = False):
    """Get all subclasses of node.

    :Parameters:
        * `abstract`: If set to ``True`` all abstract classes are included as well. Default is
          ``False``
    """
    classes = []
    for c in utils.subclass_iterator(root):
        try:
            info = get_node_info(c)

            node_type = info.get("type")
            if node_type != "abstract":
                classes.append(c)
        except AttributeError:
            pass

    return classes

def get_node_info(cls):
    """Get node info attribute of a node - transient function during
    depreciation"""

    if hasattr(cls, "__node_info__") and cls not in _node_info_warnings:

        utils.get_logger().warn("depreciated __node_info__ present in %s, rename to node_info" \
                    " (this warning will be shown only once)" % str(cls))
        _node_info_warnings.add(cls)

        return cls.__node_info__
    else:
        return cls.node_info

class Stack(object):
    """A stack holding records from a pipe. Each record has a key. 
    At most `depth` records are stored based on their key order.
    """

    def __init__(self, depth):
        self.depth = depth
        self.heap = []
        self.elements = {}

    def push(self, key, value):
        """Push a `value` into rank `key` in the stack.
        If stack is full, remove the highest-key element. """
        if len(self.heap)<self.depth:
            heapq.heappush(self.heap, key)
            self.elements[key] = value
        else:
            oldkey = heapq.heappushpop(self.heap, key)
            self.elements[key] = value
            del self.elements[oldkey]

    def pop(self):
        """Pop an arbitrary element from the stack."""
        try:
            key = heapq.heappop(self.heap)
            return self.elements[key]
        except:
            raise StopIteration

    def items(self):
        """An iterator of all elements."""
        return self.elements.values()

class NodeFinished(Exception):
    """Exception raised when node has no active outputs - each output node signalised that it
    requires no more data."""
    pass

class Node(object):
    """Base class for procesing node

    .. abstract_node
    """
    def __init__(self):
        """Creates a new data processing node.

        :Attributes:
            * `inputs`: input pipes
            * `outputs`: output pipes
            * `description`: custom node annotation
        """

        super(Node, self).__init__()
        self.inputs = []
        self.outputs = []
        self._active_outputs = []
        self.description = None

        # Experimental: dictionary to be used to retype output fields
        # Currently used only in CSV source node.
        self._retype_dictionary = {}

    def initialize(self):
        """Initializes the node. Initialization is separated from creation. Put any Node subclass
        initialization in this method. Default implementation does nothing.

        .. note:
            Why the ``initialize()`` method? Node initiaization is different action from node object
            instance initialization in the ``__init__()`` method. Before executing node contents, the
            node has to be initialized - files or network connections opened, temporary tables created,
            data that are going to be used for configuration fetched, ... Initialization might require
            node to be fully configured first: all node attributes set to desired values.
        """
        pass

    def finalize(self):
        """Finalizes the node. Default implementation does nothing."""
        pass

    def run(self):
        """Main method for running the node code. Subclasses should implement this method.
        """

        raise NotImplementedError("Subclasses of Node should implement the run() method")

    @property
    def input(self):
        """Return single node imput if exists. Convenience property for nodes which process only one
        input. Raises exception if there are no inputs or are more than one imput."""

        if len(self.inputs) == 1:
            return self.inputs[0]
        else:
            raise Exception("Single input requested. Node has none or more than one input (%d)."
                                    % len(self.inputs))

    def add_input(self, pipe):
        if pipe not in self.inputs:
            self.inputs.append(pipe)
        else:
            raise Exception("Input %s already connected" % pipe)

    def add_output(self, pipe):
        if pipe not in self.outputs:
            self.outputs.append(pipe)
        else:
            raise Exception("Output %s already connected" % pipe)

    def retype(self, name, **attributes):
        """Retype an output field `name` to field `field`.

        .. note:

            This function is not set in stone and might change. Consider it to
            be experimental feature.
        """
        self._retype_dictionary[name] = attributes

    def reset_type(self, name):
        """Remove all retype information for field `name`"""
        del self._retype_dictionary[name]

    def put(self, obj):
        """Put row into all output pipes.

        Raises `NodeFinished` exception when node's target nodes are not receiving data anymore.
        In most cases this exception might be ignored, as it is handled in the node thread
        wrapper. If you want to perform necessary clean-up in the `run()` method before exiting,
        you should handle this exception and then re-reaise it or just simply return from `run()`.

        This method can be called only from node's `run()` method. Do not call it from
        `initialize()` or `finalize()`.
        """
        active_outputs = 0
        for output in self.outputs:
            if not output.closed():
                output.put(obj)
                active_outputs += 1

        # This is not very safe, as run() might not expect it
        if not active_outputs:
            raise NodeFinished

    def put_record(self, obj):
        """Put record into all output pipes. Convenience method. Not recommended to be used.

        .. warning::

        Depreciated.

        """
        for output in self.outputs:
            output.put_record(obj)

    @property
    def input_fields(self):
        """Return fields from input pipe, if there is one and only one input pipe."""
        return self.input.fields

    @property
    def output_fields(self):
        """Return fields passed to the output by the node.

        Subclasses should override this method. Default implementation returns same fields as
        input has, raises exception when there are more inputs or if there is no input
        connected."""
        if not len(self.inputs) == 1:
            raise ValueError("Can not get default list of output fields: node has more than one input"
                             " or no input is provided. Subclasses should override this method")

        if not self.input.fields:
            raise ValueError("Can not get default list of output fields: input pipe fields are not "
                             "initialized")

        return self.input.fields

    @property
    def output_field_names(self):
        """Convenience method for gettin names of fields generated by the node. For more information
        see :meth:`brewery.nodes.Node.output_fields`"""
        raise PendingDeprecationWarning
        return self.output_fields.names()

    @classmethod
    def identifier(cls):
        """Returns an identifier name of the node class. Identifier is used
        for construction of streams from dictionaries or for any other
        out-of-program constructions.

        Node identifier is specified in the `node_info` dictioanry as
        ``name``. If no explicit identifier is specified, then decamelized
        class name will be used with `node` suffix removed. For example:
        ``CSVSourceNode`` will be ``csv_source``.
        """

        logger = utils.get_logger()

        # FIXME: this is temporary warning
        info = get_node_info(cls)
        ident = None

        if info:
            ident = info.get("name")

        if not ident:
            ident = utils.to_identifier(utils.decamelize(cls.__name__))
            if ident.endswith("_node"):
                ident = ident[:-5]

        return ident

    def configure(self, config, protected = False):
        """Configure node.

        :Parameters:
            * `config` - a dictionary containing node attributes as keys and values as attribute
              values. Key ``type`` is ignored as it is used for node creation.
            * `protected` - if set to ``True`` only non-protected attributes are set. Attempt
              to set protected attribute will result in an exception. Use `protected` when you are
              configuring nodes through a user interface or a custom tool. Default is ``False``: all
              attributes can be set.

        If key in the `config` dictionary does not refer to a node attribute specified in node
        description, then it is ignored.
        """

        attributes = dict((a["name"], a) for a in get_node_info(self)["attributes"])

        for attribute, value in config.items():
            info = attributes.get(attribute)

            if not info:
                continue
                # raise KeyError("Unknown attribute '%s' in node %s" % (attribute, str(type(self))))

            if protected and info.get("protected"):
                # FIXME: use some custom exception
                raise Exception("Trying to set protected attribute '%s' of node '%s'" %
                                        (attribute, str(type(self))))
            else:
                setattr(self, attribute, value)

class SourceNode(Node):
    """Abstract class for all source nodes

    All source nodes should provide an attribute or implement a property (``@property``) called
    ``output_fields``.

    .. abstract_node

    """
    def __init__(self):
        super(SourceNode, self).__init__()

    @property
    def output_fields(self):
        raise NotImplementedError("SourceNode subclasses should implement output_fields")

    def add_input(self, pipe):
        raise Exception("Should not add input pipe to a source node")

class TargetNode(Node):
    """Abstract class for all target nodes

    .. abstract_node

    """
    def __init__(self):
        super(TargetNode, self).__init__()
        self.fields = None

    @property
    def output_fields(self):
        raise RuntimeError("Output fields asked from a target object.")

    def add_output(self, pipe):
        raise RuntimeError("Should not add output pipe to a target node")

########NEW FILE########
__FILENAME__ = field_nodes
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from .base import Node
from ..metadata import FieldMap, FieldList, Field
from ..common import FieldError

import re

class FieldMapNode(Node):
    """Node renames input fields or drops them from the stream.
    """
    node_info = {
        "type": "field",
        "label" : "Field Map",
        "description" : "Rename or drop fields from the stream.",
        "attributes" : [
            {
                "name": "map_fields",
                "label": "Map fields",
                "description": "Dictionary of input to output field name."
            },
            {
                "name": "drop_fields",
                "label": "drop fields",
                "description": "List of fields to be dropped from the stream - incompatible with keep_fields."
            },
            {
                "name": "keep_fields",
                "label": "keep fields",
                "description": "List of fields to keep from the stream - incompatible with drop_fields."
            }
        ]
    }

    def __init__(self, map_fields = None, drop_fields = None, keep_fields=None):
        super(FieldMapNode, self).__init__()

        if drop_fields and keep_fields:
            raise FieldError('Invalid configuration of FieldMapNode: you cant specify both keep_fields and drop_fields.')

        if map_fields:
            self.mapped_fields = map_fields
        else:
            self.mapped_fields = {}

        if drop_fields:
            self.dropped_fields = set(drop_fields)
        else:
            self.dropped_fields = set([])

        if keep_fields:
            self.kept_fields = set(keep_fields)
        else:
            self.kept_fields = set([])

        self._output_fields = []

    def rename_field(self, source, target):
        """Change field name"""
        self.mapped_fields[source] = target

    def drop_field(self, field):
        """Do not pass field from source to target"""
        self.dropped_fields.add(field)

    @property
    def output_fields(self):
        return self._output_fields

    def initialize(self):
        self.map = FieldMap(rename=self.mapped_fields, drop=self.dropped_fields, keep=self.kept_fields)
        self._output_fields = self.map.map(self.input.fields)
        self.filter = self.map.row_filter(self.input.fields)

    def run(self):
        self.mapped_field_names = self.mapped_fields.keys()

        for row in self.input.rows():
            row = self.filter.filter(row)
            self.put(row)

class TextSubstituteNode(Node):
    """Substitute text in a field using regular expression."""

    node_info = {
        "type": "field",
        "label" : "Text Substitute",
        "description" : "Substitute text in a field using regular expression.",
        "attributes" : [
            {
                "name": "field",
                "label": "substituted field",
                "description": "Field containing a string or text value where substition will "
                               "be applied"
            },
            {
                "name": "derived_field",
                "label": "derived field",
                "description": "Field where substition result will be stored. If not set, then "
                               "original field will be replaced with new value."
            },
            {
                "name": "substitutions",
                "label": "substitutions",
                "description": "List of substitutions: each substition is a two-element tuple "
                               "(`pattern`, `replacement`) where `pattern` is a regular expression "
                               "that will be replaced using `replacement`"
            }
        ]
    }

    def __init__(self, field, derived_field = None):
        """Creates a node for text replacement.

        :Attributes:
            * `field`: field to be used for substitution (should contain a string)
            * `derived_field`: new field to be created after substitutions. If set to ``None`` then the
              source field will be replaced with new substituted value. Default is ``None`` - same field
              replacement.

        """
        super(TextSubstituteNode, self).__init__()

        self.field = field
        self.derived_field = derived_field
        self.substitutions = []

    def add_substitution(self, pattern, repl):
        """Add replacement rule for field.

        :Parameters:
            * `pattern` - regular expression to be searched
            * `replacement` - string to be used as replacement, default is empty string
        """

        self.substitutions.append( (re.compile(pattern), repl) )

    # FIXME: implement this
    # @property
    # def output_fields(self):
    #     pass

    def run(self):
        pipe = self.input

        if self.derived_field:
            append = True
        else:
            append = False

        index = self.input_fields.index(self.field)

        for row in pipe.rows():
            value = row[index]
            for (pattern, repl) in self.substitutions:
                value = re.sub(pattern, repl, value)
            if append:
                row.append(value)
            else:
                row[index] = value

            self.put(row)


class StringStripNode(Node):
    """Strip spaces (orother specified characters) from string fields."""

    node_info = {
        "type": "field",
        "icon": "string_strip_node",
        "label" : "String Strip",
        "description" : "Strip characters.",
        "attributes" : [
            {
                "name": "fields",
                "description": "List of string fields to be stripped. If none specified, then all "
                               "fields of storage type `string` are stripped"
            },
            {
                "name": "chars",
                "description": "Characters to be stripped. "
                               "By default all white-space characters are stripped."
            }
        ]
    }

    def __init__(self, fields = None, chars = None):
        """Creates a node for string stripping.

        :Attributes:
            * `fields`: fields to be stripped
            * `chars`: characters to be stripped

        """
        super(StringStripNode, self).__init__()

        self.fields = fields
        self.chars = chars

    def run(self):

        if self.fields:
            fields = self.fields
        else:
            fields = []
            for field in self.input.fields:
                if field.storage_type == "string" or field.storage_type == "text":
                    fields.append(field)

        indexes = self.input_fields.indexes(fields)

        for row in self.input.rows():
            for index in indexes:
                value = row[index]
                if value:
                    row[index] = value.strip(self.chars)

            self.put(row)

class CoalesceValueToTypeNode(Node):
    """Coalesce values of selected fields, or fields of given type to match the type.

    * `string`, `text`
        * Strip strings
        * if non-string, then it is converted to a unicode string
        * Change empty strings to empty (null) values
    * `float`, `integer`
        * If value is of string type, perform string cleansing first and then convert them to
          respective numbers or to null on failure

    """

    node_info = {
        "type": "field",
        "icon": "coalesce_value_to_type_node",
        "description" : "Coalesce Value to Type",
        "attributes" : [
            {
                "name": "fields",
                "description": "List of fields to be cleansed. If none given then all fields "
                               "of known storage type are cleansed"
            },
            {
                "name": "types",
                "description": "List of field types to be coalesced (if no fields given)"
            },
            {
                "name": "empty_values",
                "description": "dictionary of type -> value pairs to be set when field is "
                               "considered empty (null)"
            }
        ]
    }

    def __init__(self, fields = None, types = None, empty_values = None):
        super(CoalesceValueToTypeNode, self).__init__()
        self.fields = fields
        self.types = types

        if empty_values:
            self.empty_values = empty_values
        else:
            self.empty_values = {}

    def initialize(self):
        if self.fields:
            fields = self.fields
        else:
            fields = self.input.fields

        self.string_fields = [f for f in fields if f.storage_type == "string"]
        self.integer_fields = [f for f in fields if f.storage_type == "integer"]
        self.float_fields = [f for f in fields if f.storage_type == "float"]

        self.string_indexes = self.input.fields.indexes(self.string_fields)
        self.integer_indexes = self.input.fields.indexes(self.integer_fields)
        self.float_indexes = self.input.fields.indexes(self.float_fields)

        self.string_none = self.empty_values.get("string")
        self.integer_none = self.empty_values.get("integer")
        self.float_none = self.empty_values.get("float")

    def run(self):

        for row in self.input.rows():
            for i in self.string_indexes:
                value = row[i]
                if type(value) == str or type(value) == unicode:
                    value = value.strip()
                elif value:
                    value = unicode(value)

                if not value:
                    value = self.string_none

                row[i] = value

            for i in self.integer_indexes:
                value = row[i]
                if type(value) == str or type(value) == unicode:
                    value = re.sub(r"\s", "", value.strip())

                if value is None:
                    value = self.integer_none
                else:
                    try:
                        value = int(value)
                    except ValueError:
                        value = self.integer_none

                row[i] = value

            for i in self.float_indexes:
                value = row[i]
                if type(value) == str or type(value) == unicode:
                    value = re.sub(r"\s", "", value.strip())

                if value is None:
                    value = self.float_none
                else:
                    try:
                        value = float(value)
                    except ValueError:
                        value = self.float_none

                row[i] = value

            self.put(row)

class ValueThresholdNode(Node):
    """Create a field that will refer to a value bin based on threshold(s). Values of `range` type
    can be compared against one or two thresholds to get low/high or low/medium/high value bins.

    *Note: this node is not yet implemented*

    The result is stored in a separate field that will be constructed from source field name and
    prefix/suffix.

    For example:
        * amount < 100 is low
        * 100 <= amount <= 1000 is medium
        * amount > 1000 is high

    Generated field will be `amount_threshold` and will contain one of three possible values:
    `low`, `medium`, `hight`

    Another possible use case might be for binning after data audit: we want to measure null
    record count and we set thresholds:

        * ratio < 5% is ok
        * 5% <= ratio <= 15% is fair
        * ratio > 15% is bad

    We set thresholds as ``(0.05, 0.15)`` and values to ``("ok", "fair", "bad")``

    """

    node_info = {
        "type": "field",
        "label" : "Value Threshold",
        "description" : "Bin values based on a threshold.",
        "attributes" : [
            {
                "name": "thresholds",
                "description": "List of fields of `range` type and threshold tuples "
                               "(field, low, high) or (field, low)"
            },
            {
                "name": "bin_names",
                "description": "Names of bins based on threshold. Default is low, medium, high"
            },
            {
                "name": "prefix",
                "description": "field prefix to be used, default is none."
            },
            {
                "name": "suffix",
                "description": "field suffix to be used, default is '_bin'"
            }
        ]
    }

    def __init__(self, thresholds=None, bin_names=None, prefix=None, suffix=None):
        super(ValueThresholdNode, self).__init__()
        self.thresholds = thresholds
        self.bin_names = bin_names
        self.prefix = prefix
        self.suffix = suffix
        self._output_fields = None

    @property
    def output_fields(self):
        return self._output_fields

    def initialize(self):
        field_names = [t[0] for t in self.thresholds]

        self._output_fields = FieldList()

        for field in self.input.fields:
            self._output_fields.append(field)

        if self.prefix:
            prefix = self.prefix
        else:
            prefix = ""

        if self.suffix:
            suffix = self.suffix
        else:
            suffix = "_bin"

        for name in field_names:
            field = Field(prefix + name + suffix)
            field.storage_type = "string"
            field.analytical_type = "set"
            self._output_fields.append(field)

        # Check input fields
        for name in field_names:
            if not name in self.input.fields:
                raise FieldError("No input field with name %s" % name)

        self.threshold_field_indexes = self.input.fields.indexes(field_names)

    def run(self):
        thresholds = []
        for t in self.thresholds:
            if len(t) == 1:
                # We have only field name, then use default threshold: 0
                thresholds.append( (0, ) )
            elif len(t) == 2:
                thresholds.append( (t[1], ) )
            elif len(t) >= 2:
                thresholds.append( (t[1], t[2]) )
            elif not t:
                raise ValueError("Invalid threshold specification: should be field name, low and optional high")

        if not self.bin_names:
            bin_names = ("low", "medium", "high")
        else:
            bin_names = self.bin_names

        for row in self.input.rows():
            for i, t in enumerate(thresholds):
                value = row[self.threshold_field_indexes[i]]
                bin = None
                if len(t) == 1:
                    if value < t[0]:
                        bin = bin_names[0]
                    else:
                        bin = bin_names[-1]
                elif len(t) > 1:
                    if value < t[0]:
                        bin = bin_names[0]
                    if value > t[1]:
                        bin = bin_names[-1]
                    else:
                        bin = bin_names[1]

                row.append(bin)
            self.put(row)

class DeriveNode(Node):
    """Dreive a new field from other fields using an expression or callable function.

    The parameter names of the callable function should reflect names of the fields:

    .. code-block:: python

        def get_half(i, **args):
            return i / 2

        node.formula = get_half

    You can use ``**record`` to catch all or rest of the fields as dictionary:

    .. code-block:: python

        def get_half(**record):
            return record["i"] / 2

        node.formula = get_half


    The formula can be also a string with python expression where local variables are record field
    values:

    .. code-block:: python

        node.formula = "i / 2"

    """

    node_info = {
        "label" : "Derive Node",
        "description" : "Derive a new field using an expression.",
        "attributes" : [
            {
                 "name": "field_name",
                 "description": "Derived field name",
                 "default": "new_field"
            },
            {
                 "name": "formula",
                 "description": "Callable or a string with python expression that will evaluate to "
                                "new field value"
            },
            {
                "name": "analytical_type",
                 "description": "Analytical type of the new field",
                 "default": "unknown"
            },
            {
                "name": "storage_type",
                 "description": "Storage type of the new field",
                 "default": "unknown"
            }
        ]
    }


    def __init__(self, formula = None, field_name = "new_field", analytical_type = "unknown",
                        storage_type = "unknown"):
        """Creates and initializes selection node
        """
        super(DeriveNode, self).__init__()
        self.formula = formula
        self.field_name = field_name
        self.analytical_type = analytical_type
        self.storage_type = storage_type
        self._output_fields = None

    @property
    def output_fields(self):
        return self._output_fields

    def initialize(self):
        if isinstance(self.formula, basestring):
            self._expression = compile(self.formula, "SelectNode condition", "eval")
            self._formula_callable = self._eval_expression
        else:
            self._formula_callable = self.formula

        self._output_fields = FieldList()

        for field in self.input.fields:
            self._output_fields.append(field)

        new_field = Field(self.field_name, analytical_type = self.analytical_type,
                                  storage_type = self.storage_type)
        self._output_fields.append(new_field)

    def _eval_expression(self, **record):
        return eval(self._expression, None, record)

    def run(self):
        for record in self.input.records():
            if self._formula_callable:
                record[self.field_name] = self._formula_callable(**record)
            else:
                record[self.field_name] = None

            self.put_record(record)

class BinningNode(Node):
    """Derive a bin/category field from a value.

    .. warning::

        Not yet implemented

    Binning modes:

    * fixed width (for example: by 100)
    * fixed number of fixed-width bins
    * n-tiles by count or by sum
    * record rank


    """

    node_info = {
        "type": "field",
        "label" : "Binning",
        "icon": "histogram_node",
        "description" : "Derive a field based on binned values (histogram)"
    }

########NEW FILE########
__FILENAME__ = record_nodes
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from .base import Node, Stack
from ..dq.field_statistics import FieldStatistics
from ..metadata import FieldMap, FieldList, Field
import logging
import itertools
import random

class SampleNode(Node):
    """Create a data sample from input stream. There are more sampling possibilities:

    * fixed number of records
    * % of records, random *(not yet implemented)*
    * get each n-th record *(not yet implemented)*

    Node can work in two modes: pass sample to the output or discard sample and pass the rest.
    The mode is controlled through the `discard` flag. When it is false, then sample is passed
    and rest is discarded. When it is true, then sample is discarded and rest is passed.

    """

    node_info = {
        "label" : "Sample Node",
        "description" : "Pass data sample from input to output.",
        "output" : "same fields as input",
        "attributes" : [
            {
                 "name": "size",
                 "description": "Size of the sample to be passed to the output",
                 "type": "integer"
            },
            {
                "name": "discard",
                 "description": "flag whether the sample is discarded or included",
                 "default": "True"
            }
        ]
    }


    def __init__(self, size = 1000, discard_sample = False, method = 'first'):
        """Creates and initializes sample node

        :Parameters:
            * `size` - number of records to be sampled
            * `discard_sample` - flag whether the sample is discarded or included. By default `False` -
              sample is included.
            * `mode` - sampling mode - ``first`` (default) - get first N items, ``nth`` - get one in n, ``random``
              - get random number - ``percent`` - get random percent. Note: mode is not yet implemented.
            """
        super(SampleNode, self).__init__()
        self.size = size
        self.discard_sample = discard_sample
        self.method = method
        # random nodes need a stack to hold intermediate records
        if method == "random":
            self.stack = Stack(size)
        else:
            self.stack = None
        if method == "percent" and ((size>100) or (size<0)):
            raise ValueError, "Sample size must be between 0 and 100 with 'percent' method."


    def run(self):
        pipe = self.input
        count = 0

        for row in pipe.rows():
            logging.debug("sampling row %d" % count)
            if self.method == "random":
                uniform = random.random()
                self.stack.push(key = uniform, value = row)
            elif self.method == "percent":
                if random.random() < float(self.size)/100.:
                    self.put(row)
                    count += 1
            else:
                self.put(row)
                count += 1
                if count >= self.size:
                    break
        # output items remaining in stack
        if self.stack:
            for row in self.stack.items():
                self.put(row)

class AppendNode(Node):
    """Sequentialy append input streams. Concatenation order reflects input stream order. The
    input streams should have same set of fields."""
    node_info = {
        "label" : "Append",
        "description" : "Concatenate input streams."
    }

    def __init__(self):
        """Creates a node that concatenates records from inputs. Order of input pipes matter."""
        super(AppendNode, self).__init__()

    @property
    def output_fields(self):
        if not self.inputs:
            raise ValueError("Can not get list of output fields: node has no input")

        return self.inputs[0].fields

    def run(self):
        """Append data objects from inputs sequentially."""
        for pipe in self.inputs:
            for row in pipe.rows():
                self.put(row)

class MergeNode(Node):
    """Merge two or more streams (join).

    Inputs are joined in a star-like fashion: one input is considered master and others are
    details adding information to the master. By default master is the first input.
    Joins are specified as list of tuples: (`input_tag`, `master_input_key`, `other_input_key`).

    Following configuration code shows how to add region and category details:

    .. code-block:: python

        node.keys = [ [1, "region_code", "code"],
                      [2, "category_code", "code"] ]

    Master input should have fields `region_code` and `category_code`, other inputs should have
    `code` field with respective values equal to master keys.

    .. code-block:: python

        node.keys = [ [1, "region_code", "code"],
                      [2, ("category_code", "year"), ("code", "year")] ]

    As a key you might use either name of a sigle field or list of fields for compound keys. If
    you use compound key, both keys should have same number of fields. For example, if there is
    categorisation based on year:

    The detail key might be omitted if it the same as in master input:

    .. code-block:: python

        node.keys = [ [1, "region_code"],
                      [2, "category_code"] ]

    Master input should have fields `region_code` and `category_code`, input #1 should have
    `region_code` field and input #2 should have `category_code` field.

    To filter-out fields you do not want in your output or to rename fields you can use `maps`. It
    should be a dictionary where keys are input tags and values are either
    :class:`FieldMap` objects or dictionaries with keys ``rename`` and ``drop``.

    Following example renames ``source_region_name`` field in input 0 and drops field `id` in
    input 1:

    .. code-block:: python

        node.maps = {
                        0: FieldMap(rename = {"source_region_name":"region_name"}),
                        1: FieldMap(drop = ["id"])
                    }

    It is the same as:

    .. code-block:: python

        node.maps = {
                        0: { "rename" = {"source_region_name":"region_name"} },
                        1: { "drop" = ["id"] }
                    }

    The first option is preferred, the dicitonary based option is provided for convenience
    in cases nodes are being constructed from external description (such as JSON dictionary).

    .. note::

        Limitations of current implementation (might be improved in the future):

        * only inner join between datasets: that means that only those input records are joined
          that will have matching keys
        * "detail" datasets should have unique keys, otherwise the behaviour is undefined
        * master is considered as the largest dataset

    How does it work: all records from detail inputs are read first. Then records from master
    input are read and joined with cached input records. It is recommended that the master dataset
    set is the largest from all inputs.

    """

    node_info = {
        "label" : "Merge Node",
        "description" : "Merge two or more streams",
        "attributes" : [
            {
                "name": "joins",
                "description": "Join specification (see node documentation)"
            },
            {
                "name": "master",
                "description": "Tag (index) of input dataset which will be considered as master"
            },
            {
                "name": "maps",
                "description": "Specification of which fields are passed from input and how they are going to be (re)named"
            },
            {
                "name": "join_types",
                "description": "Dictionary where keys are stream tags (indexes) and values are "
                               "types of join for the stream. Default is 'inner'. "
                               "-- **Not implemented**"
            }
        ]
    }

    def __init__(self, joins = None, master = None, maps = None):
        super(MergeNode, self).__init__()
        if joins:
            self.joins = joins
        else:
            self.joins = []

        if master:
            self.master = master
        else:
            self.master = 0

        self.maps = maps

        self._output_fields = []

    def initialize(self):
        pass
        # Check joins and normalize them first
        self._keys = {}
        self._kindexes = {}

        self.master_input = self.inputs[self.master]
        self.detail_inputs = []
        for (tag, pipe) in enumerate(self.inputs):
            if pipe is not self.master_input:
                self.detail_inputs.append( (tag, pipe) )

        for join in self.joins:
            joinlen = len(join)
            if joinlen == 3:
                (detail_tag, master_key, detail_key) = join
            elif joinlen == 2:
                # We use same key names for detail as master if no detail key is specified
                (detail_tag, master_key) = join
                detail_key = master_key
            else:
                raise Exception("Join specification should be a tuple/list of two or three elements.")

            # Convert to tuple if it is just a string (as expected later)
            if not (type(detail_key) == list or type(detail_key) == tuple):
                detail_key = (detail_key, )
            if not (type(master_key) == list or type(master_key) == tuple):
                master_key = (master_key, )

            if detail_tag == self.master:
                raise Exception("Can not join master to itself.")

            self._keys[detail_tag] = (detail_key, master_key)

            detail_input = self.inputs[detail_tag]

            # Get field indexes
            detail_indexes = detail_input.fields.indexes(detail_key)
            master_indexes = self.master_input.fields.indexes(master_key)
            self._kindexes[detail_tag] = (detail_indexes, master_indexes)

        # Prepare storage for input data
        self._input_rows = {}
        for (tag, pipe) in enumerate(self.inputs):
            self._input_rows[tag] = {}

        # Create map filters

        self._filters = {}
        self._maps = {}
        if self.maps:
            for (tag, fmap) in self.maps.items():
                if type(fmap) == dict:
                    fmap = FieldMap(rename = fmap.get("rename"), drop = fmap.get("drop"), keep=fmap.get("keep"))
                elif type(fmap) != FieldMap:
                    raise Exception("Unknown field map type: %s" % type(fmap) )
                f = fmap.row_filter(self.inputs[tag].fields)
                self._maps[tag] = fmap
                self._filters[tag] = f

        # Construct output fields
        fields = []
        for (tag, pipe) in enumerate(self.inputs):
            fmap = self._maps.get(tag, None)
            if fmap:
                fields += fmap.map(pipe.fields)
            else:
                fields += pipe.fields

        self._output_fields = FieldList(fields)



    @property
    def output_fields(self):
        return self._output_fields

    def run(self):
        """Only inner join is implemented"""
        # First, read details, then master. )
        for (tag, pipe) in self.detail_inputs:
            detail = self._input_rows[tag]

            key_indexes = self._kindexes[tag][0]
            self._read_input(tag, pipe, key_indexes, detail)

        rfilter = self._filters.get(self.master)

        for row in self.master_input.rows():
            if rfilter:
                joined_row = rfilter.filter(row[:])
            else:
                joined_row = row[:]

            joined = False
            for (tag, pipe) in self.detail_inputs:
                detail_data = self._input_rows[tag]

                # Create key from master
                key = []
                for i in self._kindexes[tag][1]:
                    key.append(row[i])
                key = tuple(key)

                detail = detail_data.get(tuple(key))

                if not detail:
                    joined = False
                    break
                else:
                    joined = True
                    joined_row += detail

            if joined:
                self.put(joined_row)

    def _read_input(self, tag, pipe, key_indexes, detail):
        rfilter = self._filters.get(tag)
        for row in pipe.rows():
            key = []
            for i in key_indexes:
                key.append(row[i])

            if rfilter:
                detail[tuple(key)] = rfilter.filter(row)
            else:
                detail[tuple(key)] = row

class DistinctNode(Node):
    """Node will pass distinct records with given distinct fields.

    If `discard` is ``False`` then first record with distinct keys is passed to the output. This is
    used to find all distinct key values.

    If `discard` is ``True`` then first record with distinct keys is discarded and all duplicate
    records with same key values are passed to the output. This mode is used to find duplicate
    records. For example: there should be only one invoice per organisation per month. Set
    `distinct_fields` to `organisaion` and `month`, sed `discard` to ``True``. Running this node
    should give no records on output if there are no duplicates.

    """
    node_info = {
        "label" : "Distinct Node",
        "description" : "Pass only distinct records (discard duplicates) or pass only duplicates",
        "attributes" : [
            {
                "name": "distinct_fields",
                "label": "distinct fields",
                "description": "List of key fields that will be considered when comparing records"
            },
            {
                "name": "discard",
                "label": "derived field",
                "description": "Field where substition result will be stored. If not set, then "
                               "original field will be replaced with new value."
            }
        ]
    }

    def __init__(self, distinct_fields = None, discard = False):
        """Creates a node that will pass distinct records with given distinct fields.

        :Parameters:
            * `distinct_fields` - list of names of key fields
            * `discard` - whether the distinct fields are discarded or kept. By default False.

        If `discard` is ``False`` then first record with distinct keys is passed to the output. This is
        used to find all distinct key values.

        If `discard` is ``True`` then first record with distinct keys is discarded and all duplicate
        records with same key values are passed to the output. This mode is used to find duplicate
        records. For example: there should be only one invoice per organisation per month. Set
        `distinct_fields` to `organisaion` and `month`, sed `discard` to ``True``. Running this node
        should give no records on output if there are no duplicates.

        """

        super(DistinctNode, self).__init__()
        if distinct_fields:
            self.distinct_fields = distinct_fields
        else:
            self.distinct_fields = []

        self.discard = discard

    def initialize(self):
        field_map = FieldMap(keep=self.distinct_fields)
        self.row_filter = field_map.row_filter(self.input_fields)

    def run(self):
        pipe = self.input
        self.distinct_values = set()

        # Just copy input to output if there are no distinct keys
        # FIXME: should issue a warning?
        if not self.distinct_fields:
            for row in pipe.rows():
                self.put(row)
            return

        for row in pipe.rows():
            # Construct key tuple from distinct fields
            key_tuple = tuple(self.row_filter(row))

            if key_tuple not in self.distinct_values:
                self.distinct_values.add(key_tuple)
                if not self.discard:
                    self.put(row)
            else:
                if self.discard:
                    # We already have one found record, which was discarded (because discard is true),
                    # now we pass duplicates
                    self.put(row)

class Aggregate(object):
    """Structure holding aggregate information (should be replaced by named tuples in Python 3)"""
    def __init__(self):
        self.count = 0
        self.sum = 0
        self.min = 0
        self.max = 0
        self.average = None

    def aggregate_value(self, value):
        self.count += 1
        self.sum += value
        self.min = min(self.min, value)
        self.max = max(self.max, value)

    def finalize(self):
        if self.count:
            self.average = self.sum / self.count
        else:
            self.average = None
class KeyAggregate(object):
    def __init__(self):
        self.count = 0
        self.field_aggregates = {}

class AggregateNode(Node):
    """Aggregate"""

    node_info = {
        "label" : "Aggregate Node",
        "description" : "Aggregate values grouping by key fields.",
        "output" : "Key fields followed by aggregations for each aggregated field. Last field is "
                   "record count.",
        "attributes" : [
            {
                 "name": "keys",
                 "description": "List of fields according to which records are grouped"
            },
            {
                "name": "record_count_field",
                 "description": "Name of a field where record count will be stored. "
                                "Default is `record_count`"
            },
            {
                "name": "measures",
                "description": "List of fields to be aggregated."
            }

        ]
    }

    def __init__(self, keys=None, measures=None, default_aggregations=None,
                 record_count_field="record_count"):
        """Creates a new node for aggregations. Supported aggregations: sum, avg, min, max"""

        super(AggregateNode, self).__init__()
        if default_aggregations is None:
            default_aggregations= ["sum"]
        if keys:
            self.key_fields = keys
        else:
            self.key_fields = []

        self.aggregations = {}
        self.record_count_field = record_count_field
        self.measures = measures or []

    def add_measure(self, field, aggregations = None):
        """Add aggregation for `field` """
        self.aggregations[field] = aggregations
        self.measures.append(field)

    @property
    def output_fields(self):
        # FIXME: use storage types based on aggregated field type
        fields = FieldList()

        if self.key_fields:
            for field in  self.input_fields.fields(self.key_fields):
                fields.append(field)

        for field in self.measures:
            fields.append(Field(field + "_sum", storage_type = "float", analytical_type = "range"))
            fields.append(Field(field + "_min", storage_type = "float", analytical_type = "range"))
            fields.append(Field(field + "_max", storage_type = "float", analytical_type = "range"))
            fields.append(Field(field + "_average", storage_type = "float", analytical_type = "range"))
        fields.append(Field(self.record_count_field, storage_type = "integer", analytical_type = "range"))

        return fields

    def run(self):
        pipe = self.input
        self.aggregates = {}
        self.keys = []
        self.counts = {}

        key_selectors = self.input_fields.selectors(self.key_fields)
        measure_indexes = self.input_fields.indexes(self.measures)

        for row in pipe.rows():
            # Create aggregation key
            key = tuple(itertools.compress(row, key_selectors))
            # Create new aggregate record for key if it does not exist
            #
            if key not in self.keys:
                self.keys.append(key)
                key_aggregate = KeyAggregate()
                self.aggregates[key] = key_aggregate
            else:
                key_aggregate = self.aggregates[key]

            # Create aggregations for each field to be aggregated
            #
            key_aggregate.count += 1
            for i in measure_indexes:
                if i not in key_aggregate.field_aggregates:
                    aggregate = Aggregate()
                    key_aggregate.field_aggregates[i] = aggregate
                else:
                    aggregate = key_aggregate.field_aggregates[i]
                value = row[i]

                aggregate.aggregate_value(value)

        # Pass results to output
        for key in self.keys:
            row = list(key[:])

            key_aggregate = self.aggregates[key]
            for i in measure_indexes:
                aggregate = key_aggregate.field_aggregates[i]
                aggregate.finalize()
                row.append(aggregate.sum)
                row.append(aggregate.min)
                row.append(aggregate.max)
                row.append(aggregate.average)

            row.append(key_aggregate.count)

            self.put(row)

class SelectNode(Node):
    """Select or discard records from the stream according to a predicate.

    The parameter names of the callable function should reflect names of the fields:

    .. code-block:: python

        def is_big_enough(i, **args):
            return i > 1000000

        node.condition = is_big_enough

    You can use ``**record`` to catch all or rest of the fields as dictionary:

    .. code-block:: python

        def is_big_enough(**record):
            return record["i"] > 1000000

        node.condition = is_big_enough


    The condition can be also a string with python expression where local variables are record field
    values:

    .. code-block:: python

        node.condition = "i > 1000000"

    """

    node_info = {
        "label" : "Select",
        "description" : "Select or discard records from the stream according to a predicate.",
        "output" : "same fields as input",
        "attributes" : [
            {
                 "name": "condition",
                 "description": "Callable or a string with python expression that will evaluate to "
                                "a boolean value"
            },
            {
                "name": "discard",
                 "description": "flag whether the records matching condition are discarded or included",
                 "default": "False"
            }
        ]
    }


    def __init__(self, condition = None, discard = False):
        """Creates and initializes selection node
        """
        super(SelectNode, self).__init__()
        self.condition = condition
        self.discard = discard

    def initialize(self):
        if isinstance(self.condition, basestring):
            self._expression = compile(self.condition, "SelectNode condition", "eval")
            self._condition_callable = self._eval_expression
        else:
            self._condition_callable = self.condition

    def _eval_expression(self, **record):
        return eval(self._expression, None, record)

    def run(self):
        for record in self.input.records():
            if self._condition_callable(**record):
                self.put_record(record)

class FunctionSelectNode(Node):
    """Select records that will be selected by a predicate function.


    Example: configure a node that will select records where `amount` field is greater than 100

    .. code-block:: python

        def select_greater_than(value, threshold):
            return value > threshold

        node.function = select_greater_than
        node.fields = ["amount"]
        node.kwargs = {"threshold": 100}

    The `discard` flag controls behaviour of the node: if set to ``True``, then selection is
    inversed and fields that function evaluates as ``True`` are discarded. Default is False -
    selected records are passed to the output.
    """

    node_info = {
        "label" : "Function Select",
        "description" : "Select records by a predicate function (python callable).",
        "output" : "same fields as input",
        "attributes" : [
            {
                 "name": "function",
                 "description": "Predicate function. Should be a callable object."
            },
            {
                 "name": "fields",
                 "description": "List of field names to be passed to the function."
            },
            {
                "name": "discard",
                 "description": "flag whether the selection is discarded or included",
                 "default": "True"
            },
            {
                 "name": "kwargs",
                 "description": "Keyword arguments passed to the predicate function"
            },
        ]
    }

    def __init__(self, function = None, fields = None, discard = False, **kwargs):
        """Creates a node that will select records based on condition `function`.

        :Parameters:
            * `function`: callable object that returns either True or False
            * `fields`: list of fields passed to the function
            * `discard`: if ``True``, then selection is inversed and fields that function
              evaluates as ``True`` are discarded. Default is False - selected records are passed
              to the output.
            * `kwargs`: additional arguments passed to the function

        """
        super(FunctionSelectNode, self).__init__()
        self.function = function
        self.fields = fields
        self.discard = discard
        self.kwargs = kwargs

    def initialize(self):
        self.indexes = self.input_fields.indexes(self.fields)

    def run(self):
        for row in self.input.rows():
            values = [row[index] for index in self.indexes]
            flag = self.function(*values, **self.kwargs)
            if (flag and not self.discard) or (not flag and self.discard):
                self.put(row)

class SetSelectNode(Node):
    """Select records where field value is from predefined set of values.

    Use case examples:

    * records from certain regions in `region` field
    * recprds where `quality` status field is `low` or `medium`

    """


    node_info = {
        "label" : "Set Select",
        "description" : "Select records by a predicate function.",
        "output" : "same fields as input",
        "attributes" : [
            {
                 "name": "field",
                 "description": "Field to be tested."
            },
            {
                 "name": "value_set",
                 "description": "set of values that will be used for record selection"
            },
            {
                "name": "discard",
                 "description": "flag whether the selection is discarded or included",
                 "default": "True"
            }
        ]
    }

    def __init__(self, field = None, value_set = None, discard = False):
        """Creates a node that will select records where `field` contains value from `value_set`.

        :Parameters:
            * `field`: field to be tested
            * `value_set`: set of values that will be used for record selection
            * `discard`: if ``True``, then selection is inversed and records that function
              evaluates as ``True`` are discarded. Default is False - selected records are passed
              to the output.

        """
        super(SetSelectNode, self).__init__()
        self.field = field
        self.value_set = value_set
        self.discard = discard

    def initialize(self):
        self.field_index = self.input_fields.index(self.field)

    def run(self):
        for row in self.input.rows():
            flag = row[self.field_index] in self.value_set
            if (flag and not self.discard) or (not flag and self.discard):
                self.put(row)

class AuditNode(Node):
    """Node chcecks stream for empty strings, not filled values, number distinct values.

    Audit note passes following fields to the output:

        * `field_name` - name of a field from input
        * `record_count` - number of records
        * `null_count` - number of records with null value for the field
        * `null_record_ratio` - ratio of null count to number of records
        * `empty_string_count` - number of strings that are empty (for fields of type string)
        * `distinct_count` - number of distinct values (if less than distinct threshold). Set
          to None if there are more distinct values than `distinct_threshold`.
    """

    node_info = {
        "icon" : "data_audit_node",
        "label" : "Data Audit",
        "description" : "Perform basic data audit.",
        "attributes" : [
            {
                "name": "distinct_threshold",
                "label": "distinct threshold",
                "description": "number of distinct values to be tested. If there are more "
                               "than the threshold, then values are not included any more "
                               "and result `distinct_values` is set to None "
            }
        ]
    }

    def __init__(self, distinct_threshold = 10):
        """Creates a field audit node.

        :Attributes:
            * `distinct_threshold` - number of distinct values to be tested. If there are more
            than the threshold, then values are not included any more and result `distinct_values`
            is set to None

        Audit note passes following fields to the output:

            * field_name - name of a field from input
            * record_count - number of records
            * null_count - number of records with null value for the field
            * null_record_ratio - ratio of null count to number of records
            * empty_string_count - number of strings that are empty (for fields of type string)
            * distinct_values - number of distinct values (if less than distinct threshold). Set
              to None if there are more distinct values than `distinct_threshold`.

        """
        super(AuditNode, self).__init__()
        self.distinct_threshold = distinct_threshold

    @property
    def output_fields(self):

        audit_record_fields = [
                               ("field_name", "string", "typeless"),
                               ("record_count", "integer", "range"),
                               ("null_count", "float", "range"),
                               ("null_record_ratio", "float", "range"),
                               ("empty_string_count", "integer", "range"),
                               ("distinct_count", "integer", "range")
                               ]

        fields = FieldList(audit_record_fields)
        return fields

    def initialize(self):
        self.stats = []
        for field in self.input_fields:
            stat = FieldStatistics(field.name, distinct_threshold = self.distinct_threshold)
            self.stats.append(stat)

    def run(self):
        for row in self.input.rows():
            for i, value in enumerate(row):
                self.stats[i].probe(value)

        for stat in self.stats:
            stat.finalize()
            if stat.distinct_overflow:
                dist_count = None
            else:
                dist_count = len(stat.distinct_values)

            row = [ stat.field,
                    stat.record_count,
                    stat.null_count,
                    stat.null_record_ratio,
                    stat.empty_string_count,
                    dist_count
                  ]

            self.put(row)


########NEW FILE########
__FILENAME__ = source_nodes
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from .base import SourceNode
from ..ds.csv_streams import CSVDataSource
from ..ds.elasticsearch_streams import ESDataSource
from ..ds.gdocs_streams import GoogleSpreadsheetDataSource
from ..ds.sql_streams import SQLDataSource
from ..ds.xls_streams import XLSDataSource
from ..ds.yaml_dir_streams import YamlDirectoryDataSource

class RowListSourceNode(SourceNode):
    """Source node that feeds rows (list/tuple of values) from a list (or any other iterable)
    object."""

    node_info = {
        "label" : "Row List Source",
        "description" : "Provide list of lists or tuples as data source.",
        "protected": True,
        "attributes" : [
            {
                 "name": "list",
                 "description": "List of rows represented as lists or tuples."
            },
            {
                 "name": "fields",
                 "description": "Fields in the list."
            }
        ]
    }
    def __init__(self, a_list = None, fields = None):
        if a_list:
            self.list = a_list
        else:
            self.list = []
        self.fields = fields

    @property
    def output_fields(self):
        if not self.fields:
            raise ValueError("Fields are not initialized")
        return self.fields

    def run(self):
        for row in self.list:
            self.put(row)

class RecordListSourceNode(SourceNode):
    """Source node that feeds records (dictionary objects) from a list (or any other iterable)
    object."""

    node_info = {
        "label" : "Record List Source",
        "description" : "Provide list of dict objects as data source.",
        "protected": True,
        "attributes" : [
            {
                 "name": "a_list",
                 "description": "List of records represented as dictionaries."
            },
            {
                 "name": "fields",
                 "description": "Fields in the list."
            }
        ]
    }

    def __init__(self, a_list=None, fields=None):
        super(RecordListSourceNode, self).__init__()
        if a_list:
            self.list = a_list
        else:
            self.list = []
        self.fields = fields

    @property
    def output_fields(self):
        if not self.fields:
            raise ValueError("Fields are not initialized")
        return self.fields

    def run(self):
        for record in self.list:
            self.put(record)

class StreamSourceNode(SourceNode):
    """Generic data stream source. Wraps a :mod:`brewery.ds` data source and feeds data to the
    output.

    The source data stream should configure fields on initialize().

    Note that this node is only for programatically created processing streams. Not useable
    in visual, web or other stream modelling tools.
    """

    node_info = {
        "label" : "Data Stream Source",
        "icon": "row_list_source_node",
        "description" : "Generic data stream data source node.",
        "protected": True,
        "attributes" : [
            {
                 "name": "stream",
                 "description": "Data stream object."
            }
        ]
    }

    def __init__(self, stream):
        super(StreamSourceNode, self).__init__()
        self.stream = stream

    def initialize(self):
        # if self.stream_type not in data_sources:
        #     raise ValueError("No data source of type '%s'" % stream_type)
        # stream_info = data_sources[self.stream_type]
        # if "class" not in stream_info:
        #     raise ValueError("No stream class specified for data source of type '%s'" % stream_type)

        # self.stream = stream_class(**kwargs)
        # self.stream.fields =
        self.stream.initialize()

    @property
    def output_fields(self):
        return self.stream.fields

    def run(self):
        for row in self.stream.rows():
            self.put(row)

    def finalize(self):
        self.stream.finalize()

class CSVSourceNode(SourceNode):
    """Source node that reads comma separated file from a filesystem or a remote URL.

    It is recommended to configure node fields before running. If you do not do so, fields are
    read from the file header if specified by `read_header` flag. Field storage types are set to
    `string` and analytical type is set to `typeless`.

    """
    node_info = {
        "label" : "CSV Source",
        "icon": "csv_file_source_node",
        "description" : "Read data from a comma separated values (CSV) file.",
        "attributes" : [
            {
                 "name": "resource",
                 "description": "File name or URL containing comma separated values",
            },
            {
                 "name": "fields",
                 "description": "fields contained in the file",
                 "type": "fields"
            },
            {
                 "name": "read_header",
                 "description": "flag determining whether first line contains header or not",
                 "type": "flag",
                 "default": "True"
            },
            {
                 "name": "skip_rows",
                 "description": "number of rows to be skipped",
                 "type": "flag"
            },
            {
                 "name": "encoding",
                 "description": "resource data encoding, by default no conversion is performed"
            },
            {
                 "name": "delimiter",
                 "description": "record delimiter character, default is comma ','"
            },
            {
                 "name": "quotechar",
                 "description": "character used for quoting string values, default is double quote"
            }
        ]
    }
    def __init__(self, resource = None, *args, **kwargs):
        super(CSVSourceNode, self).__init__()
        self.resource = resource
        self.args = args
        self.kwargs = kwargs
        self.stream = None
        self.fields = None
        self._output_fields = None

    @property
    def output_fields(self):
        if not self.stream:
            raise ValueError("Stream is not initialized")

        if not self._output_fields:
            raise ValueError("Fields are not initialized")

        return self._output_fields

    def initialize(self):
        self.stream = CSVDataSource(self.resource, *self.args, **self.kwargs)

        if self.fields:
            self.stream.fields = self.fields

        self.stream.initialize()

        # FIXME: this is experimental form of usage
        self._output_fields = self.stream.fields.copy()
        self._output_fields.retype(self._retype_dictionary)

    def run(self):
        for row in self.stream.rows():
            self.put(row)

    def finalize(self):
        self.stream.finalize()

class XLSSourceNode(SourceNode):
    """Source node that reads Excel XLS files.

    It is recommended to configure node fields before running. If you do not do so, fields are
    read from the file header if specified by `read_header` flag. Field storage types are set to
    `string` and analytical type is set to `typeless`.

    """
    node_info = {
        "label" : "XLS Source",
        "icon": "xls_file_source_node",
        "description" : "Read data from an Excel (XLS) spreadsheet file.",
        "attributes" : [
            {
                 "name": "resource",
                 "description": "File name or URL containing comma separated values"
            },
            {
                 "name": "fields",
                 "description": "fields contained in the file",
            },
            {
                 "name": "sheet",
                 "description": "Sheet index number (as int) or sheet name (as string)"
            },
            {
                 "name": "read_header",
                 "description": "flag determining whether first line contains header or not",
                 "default": "True"
            },
            {
                 "name": "skip_rows",
                 "description": "number of rows to be skipped"
            },
            {
                 "name": "encoding",
                 "description": "resource data encoding, by default no conversion is performed"
            }
        ]
    }
    def __init__(self, *args, **kwargs):
        super(XLSSourceNode, self).__init__()
        self.args = args
        self.kwargs = kwargs
        self.stream = None
        self._fields = None

    @property
    def output_fields(self):
        if not self.stream:
            raise ValueError("Stream is not initialized")

        if not self.stream.fields:
            raise ValueError("Fields are not initialized")

        return self.stream.fields

    def __set_fields(self, fields):
        self._fields = fields
        if self.stream:
            self.stream.fields = fields

    def __get_fields(self):
        return self._fields

    fields = property(__get_fields, __set_fields)

    def initialize(self):
        self.stream = XLSDataSource(*self.args, **self.kwargs)

        if self._fields:
            self.stream.fields = self._fields

        self.stream.initialize()
        self._fields = self.stream.fields

    def run(self):
        for row in self.stream.rows():
            self.put(row)

    def finalize(self):
        self.stream.finalize()


class YamlDirectorySourceNode(SourceNode):
    """Source node that reads data from a directory containing YAML files.

    The data source reads files from a directory and treats each file as single record. For example,
    following directory will contain 3 records::

        data/
            contract_0.yml
            contract_1.yml
            contract_2.yml

    Optionally one can specify a field where file name will be stored.
    """
    node_info = {
        "label" : "YAML Directory Source",
        "icon": "yaml_directory_source_node",
        "description" : "Read data from a directory containing YAML files",
        "protected": True,
        "attributes" : [
            {
                 "name": "path",
                 "description": "Path to a directory"
            },
            {
                 "name": "extension",
                 "description": "file extension to look for, default is yml. If none is given, "
                                "then all regular files in the directory are read.",
                 "default": "yml"
            },
            {
                 "name": "filename_field",
                 "description": "name of a new field that will contain file name",
                 "default": "True"
            }
        ]
    }
    def __init__(self, *args, **kwargs):
        super(YamlDirectorySourceNode, self).__init__()
        self.kwargs = kwargs
        self.args = args
        self.stream = None
        self.fields = None

    @property
    def output_fields(self):
        if not self.stream:
            raise ValueError("Stream is not initialized")

        if not self.stream.fields:
            raise ValueError("Fields are not initialized")

        return self.stream.fields

    def initialize(self):
        self.stream = YamlDirectoryDataSource(*self.args, **self.kwargs)

        self.stream.fields = self.fields
        self.stream.initialize()

    def run(self):
        for row in self.stream.rows():
            # logging.debug("putting yaml row. pipe status: %s" % self.outputs[0].stop_sending)
            self.put(row)

    def finalize(self):
        self.stream.finalize()

class GoogleSpreadsheetSourceNode(SourceNode):
    """Source node that reads Google Spreadsheet.

    You should provide either spreadsheet_key or spreadsheet_name, if more than one spreadsheet with
    given name are found, then the first in list returned by Google is used.

    For worksheet selection you should provide either worksheet_id or worksheet_name. If more than
    one worksheet with given name are found, then the first in list returned by Google is used. If
    no worksheet_id nor worksheet_name are provided, then first worksheet in the workbook is used.

    For details on query string syntax see the section on sq under
    http://code.google.com/apis/spreadsheets/reference.html#list_Parameters
    """
    node_info = {
        "label" : "Google Spreadsheet Source",
        "icon": "google_spreadsheet_source_node",
        "description" : "Read data from a Google Spreadsheet.",
        "attributes" : [
            {
                 "name": "spreadsheet_key",
                 "description": "The unique key for the spreadsheet"
            },
            {
                 "name": "spreadsheet_name",
                 "description": "The title of the spreadsheets",
            },
            {
                 "name": "worksheet_id",
                 "description": "ID of a worksheet"
            },
            {
                 "name": "worksheet_name",
                 "description": "name of a worksheet"
            },
            {
                 "name": "query_string",
                 "description": "optional query string for row selection"
            },
            {
                 "name": "username",
                 "description": "Google account user name"
            },
            {
                 "name": "password",
                 "description": "Google account password"
            }
        ]
    }
    def __init__(self, *args, **kwargs):
        super(GoogleSpreadsheetSourceNode, self).__init__()
        self.args = args
        self.kwargs = kwargs
        self.stream = None
        self._fields = None

    @property
    def output_fields(self):
        if not self.stream:
            raise ValueError("Stream is not initialized")

        if not self.stream.fields:
            raise ValueError("Fields are not initialized")

        return self.stream.fields

    def __getattr__(self, key):
        try:
            return getattr(self.stream, key)
        except AttributeError:
            return object.__getattr__(self, key)

    def __set_fields(self, fields):
        self._fields = fields
        if self.stream:
            self.stream.fields = fields

    def __get_fields(self):
        return self._fields

    fields = property(__get_fields, __set_fields)

    def initialize(self):
        self.stream = GoogleSpreadsheetDataSource(*self.args, **self.kwargs)

        if self._fields:
            self.stream.fields = self._fields

        self.stream.initialize()
        self._fields = self.stream.fields

    def run(self):
        for row in self.stream.rows():
            self.put(row)

    def finalize(self):
        self.stream.finalize()


class SQLSourceNode(SourceNode):
    """Source node that reads from a sql table.
    """
    node_info = {
        "label" : "SQL Source",
        "icon": "sql_source_node",
        "description" : "Read data from a sql table.",
        "attributes" : [
            {
                 "name": "uri",
                 "description": "SQLAlchemy URL"
            },
            {
                 "name": "table",
                 "description": "table name",
            },
        ]
    }
    def __init__(self, *args, **kwargs):
        super(SQLSourceNode, self).__init__()
        self.args = args
        self.kwargs = kwargs
        self.stream = None
        self._fields = None

    @property
    def output_fields(self):
        if not self.stream:
            raise ValueError("Stream is not initialized")

        if not self.stream.fields:
            raise ValueError("Fields are not initialized")

        return self.stream.fields

    def __set_fields(self, fields):
        self._fields = fields
        if self.stream:
            self.stream.fields = fields

    def __get_fields(self):
        return self._fields

    fields = property(__get_fields, __set_fields)

    def initialize(self):
        self.stream = SQLDataSource(*self.args, **self.kwargs)
        self.stream.initialize()
        self._fields = self.stream.fields

    def run(self):
        for row in self.stream.rows():
            self.put(row)

    def finalize(self):
        self.stream.finalize()

class ESSourceNode(SourceNode):
    """Source node that reads from an ElasticSearch index.
    
    See ElasticSearch home page for more information:
    http://www.elasticsearch.org/
    """

    node_info = {
        "label" : "ElasticSearch Source",
        "icon": "generic_node",
        "description" : "Read data from ElasticSearch engine",
        "attributes" : [
            {
                "name": "document_type",
                "description": "ElasticSearch document type name"
            },
            {
                "name": "expand",
                "description": "expand dictionary values and treat children as "\
                " top-level keys with dot '.' separated key path to the child"
            },
            {
                "name": "database",
                "description": "database name"
            },
            {
                "name": "host",
                "description": "database server host, default is localhost"
            },
            {
                "name": "port",
                "description": "database server port, default is 27017"
            }
        ]
    }
    def __init__(self, *args, **kwargs):
        super(ESSourceNode, self).__init__()
        self.args = args
        self.kwargs = kwargs
        self.stream = None
        self._fields = None

    @property
    def output_fields(self):
        if not self.stream:
            raise ValueError("Stream is not initialized")

        if not self.stream.fields:
            raise ValueError("Fields are not initialized")

        return self.stream.fields

    def __set_fields(self, fields):
        self._fields = fields
        if self.stream:
            self.stream.fields = fields

    def __get_fields(self):
        return self._fields

    fields = property(__get_fields, __set_fields)

    def initialize(self):
        self.stream = ESDataSource(*self.args, **self.kwargs)
        self.stream.initialize()
        self._fields = self.stream.fields

    def run(self):
        for row in self.stream.rows():
            self.put(row)

    def finalize(self):
        self.stream.finalize()

class GeneratorFunctionSourceNode(SourceNode):
    """Source node uses a callable to generate records."""

    node_info = {
        "label" : "Callable Generator Source",
        "description" : "Uses a callable as record generator",
        "protected": True,
        "attributes" : [
            {
                 "name": "function",
                 "description": "Function (or any callable)"
            },
            {
                 "name": "fields",
                 "description": "Fields the function generates"
            },
            {
                 "name": "args",
                 "description": "Function arguments"
            },
            {
                 "name": "kwargs",
                 "description": "Function key-value arguments"
            }
        ]
    }

    def __init__(self, function=None, fields=None, *args, **kwargs):
        super(GeneratorFunctionSourceNode, self).__init__()

        self.function = function
        self.fields = fields
        self.args = args
        self.kwargs = kwargs

    @property
    def output_fields(self):
        if not self.fields:
            raise ValueError("Fields are not initialized")
        return self.fields

    def run(self):
        for row in self.function(*self.args, **self.kwargs):
            self.put(row)


########NEW FILE########
__FILENAME__ = target_nodes
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from .base import TargetNode
from ..ds.csv_streams import CSVDataTarget
from ..ds.sql_streams import SQLDataTarget
import sys

class StreamTargetNode(TargetNode):
    """Generic data stream target. Wraps a :mod:`brewery.ds` data target and feeds data from the
    input to the target stream.

    The data target should match stream fields.

    Note that this node is only for programatically created processing streams. Not useable
    in visual, web or other stream modelling tools.
    """

    node_info = {
        "label" : "Data Stream Target",
        "icon": "row_list_target_node",
        "description" : "Generic data stream data target node.",
        "attributes" : [
            {
                 "name": "stream",
                 "description": "Data target object."
            }
        ]
    }

    def __init__(self, stream):
        super(StreamTargetNode, self).__init__()
        self.stream = stream

    def initialize(self):
        # if self.stream_type not in data_sources:
        #     raise ValueError("No data source of type '%s'" % stream_type)
        # stream_info = data_sources[self.stream_type]
        # if "class" not in stream_info:
        #     raise ValueError("No stream class specified for data source of type '%s'" % stream_type)

        # self.stream = stream_class(**kwargs)
        # self.stream.fields =
        self.stream.initialize()

    def run(self):
        for row in self.input.rows():
            self.stream.append(row)

    def finalize(self):
        self.stream.finalize()

class RowListTargetNode(TargetNode):
    """Target node that stores data from input in a list of rows (as tuples).

    To get list of fields, ask for `output_fields`.
    """

    node_info = {
        "label" : "Row List Target",
        "description" : "Store data as list of tuples",
        "attributes" : [
            {
                 "name": "rows",
                 "description": "Created list of tuples."
            }
        ]
    }

    def __init__(self, a_list = None):
        super(RowListTargetNode, self).__init__()
        if a_list:
            self.list = a_list
        else:
            self.list = []

    def run(self):
        self.list = []
        for row in self.input.rows():
            self.list.append(row)
    @property
    def rows(self):
        return self.list

class RecordListTargetNode(TargetNode):
    """Target node that stores data from input in a list of records (dictionary objects)
    object.

    To get list of fields, ask for `output_fields`.

    """

    node_info = {
        "label" : "Record List Target",
        "description" : "Store data as list of dictionaries (records)",
        "attributes" : [
            {
                 "name": "records",
                 "description": "Created list of records represented as dictionaries."
            }
        ]
    }
    def __init__(self, a_list = None):
        super(RecordListTargetNode, self).__init__()
        if a_list:
            self.list = a_list
        else:
            self.list = []

    def run(self):
        self.list = []
        for record in self.input.records():
            self.list.append(record)

    @property
    def records(self):
        return self.list

class CSVTargetNode(TargetNode):
    """Node that writes rows into a comma separated values (CSV) file.

    :Attributes:
        * resource: target object - might be a filename or file-like object
        * write_headers: write field names as headers into output file
        * truncate: remove data from file before writing, default: True

    """
    node_info = {
        "label" : "CSV Target",
        "description" : "Write rows as comma separated values into a file",
        "attributes" : [
            {
                 "name": "resource",
                 "description": "Target object - file name or IO object."
            },
            {
                 "name": "write_headers",
                 "description": "Flag determining whether to write field names as file headers."
            },
            {
                 "name": "truncate",
                 "description": "If set to ``True`` all data from file are removed. Default ``True``"
            }
        ]
    }

    def __init__(self, resource = None, *args, **kwargs):
        super(CSVTargetNode, self).__init__()
        self.resource = resource
        self.kwargs = kwargs
        self.args = args
        self.stream = None

    def initialize(self):
        self.stream = CSVDataTarget(self.resource, *self.args, **self.kwargs)

        self.stream.fields = self.input_fields
        self.stream.initialize()

    def run(self):
        for row in self.input.rows():
            self.stream.append(row)

    def finalize(self):
        self.stream.finalize()


class FormattedPrinterNode(TargetNode):
    """Target node that will print output based on format.

    Refer to the python formatting guide:

        http://docs.python.org/library/string.html

    Example:

    Consider we have a data with information about donations. We want to pretty print two fields:
    `project` and `requested_amount` in the form::

        Hlavicka - makovicka                                            27550.0
        Obecna kniznica - symbol moderneho vzdelavania                 132000.0
        Vzdelavanie na europskej urovni                                 60000.0

    Node for given format is created by:

    .. code-block:: python

        node = FormattedPrinterNode(format = u"{project:<50.50} {requested_amount:>20}")

    Following format can be used to print output from an audit node:

    .. code-block:: python

        node.header = u"field                            nulls      empty   distinct\\n" \\
                       "------------------------------------------------------------"
        node.format = u"{field_name:<30.30} {null_record_ratio: >7.2%} "\\
                       "{empty_string_count:>10} {distinct_count:>10}"

    Output will look similar to this::

        field                            nulls      empty   distinct
        ------------------------------------------------------------
        file                             0.00%          0         32
        source_code                      0.00%          0          2
        id                               9.96%          0        907
        receiver_name                    9.10%          0       1950
        project                          0.05%          0       3628
        requested_amount                22.90%          0        924
        received_amount                  4.98%          0        728
        source_comment                  99.98%          0          2

    """

    node_info = {
        "label" : "Formatted Printer",
        "icong": "formatted_printer_node",
        "description" : "Print input using a string formatter to an output IO stream",
        "attributes" : [
            {
                 "name": "format",
                 "description": "Format string to be used. Default is to print all field values "
                                "separated by tab character."
            },
            {
                 "name": "target",
                 "description": "IO object. If not set then sys.stdout will be used. "
                                "If it is a string, then it is considered a filename."
            },
            {
                 "name": "delimiter",
                 "description": "Record delimiter. By default it is new line character."
            },
            {
                 "name": "header",
                 "description": "Header string - will be printed before printing first record"
            },
            {
                 "name": "footer",
                 "description": "Footer string - will be printed after all records are printed"
            }
        ]
    }
    def __init__(self, format=None, target=sys.stdout, delimiter=None,
                 header=None, footer=None):
        super(FormattedPrinterNode, self).__init__()
        self.format = format

        self.target = target
        self.header = header
        self.footer = footer

        if delimiter:
            self.delimiter = delimiter
        else:
            self.delimiter = '\n'

        self.handle = None
        self.close_handle = False

    def initialize(self):
        if type(self.target) == str or type(self.target) == unicode:
            self.handle = open(self.target, "w")
            self.close_handle = True
        else:
            self.handle = self.target
            self.close_handle = False

    def run(self):

        names = self.input_fields.names()

        if self.format:
            format_string = self.format
        else:
            fields = []
            for name in names:
                fields.append(u"{" + name + u"}")

            format_string = u"" + u"\t".join(fields)

        if self.header is not None:
            self.handle.write(self.header)
            if self.delimiter:
                self.handle.write(self.delimiter)
        else:
            header_string = u"" + u"\t".join(names)
            self.handle.write(header_string)
            if self.delimiter:
                self.handle.write(self.delimiter)

        for record in self.input.records():
            self.handle.write(format_string.format(**record).encode("utf-8"))

            if self.delimiter:
                self.handle.write(self.delimiter)

        if self.footer:
            self.handle.write(self.footer)
            if self.delimiter:
                self.handle.write(self.delimiter)

        self.handle.flush()

    def finalize(self):
        if self.handle:
            self.handle.flush()
            if self.close_handle:
                self.handle.close()

class PrettyPrinterNode(TargetNode):
    """Target node that will pretty print output as a table.
    """

    node_info = {
        "label" : "Pretty Printer",
        "icong": "formatted_printer_node",
        "description" : "Print input using a pretty formatter to an output IO stream",
        "attributes" : [
            {
                 "name": "target",
                 "description": "IO object. If not set then sys.stdout will be used. "
                                "If it is a string, then it is considered a filename."
            },
            {
                 "name": "max_column_width",
                 "description": "Maximum column width. Default is unlimited. "\
                                "If set to None, then it is unlimited."
            },
            {
                 "name": "min_column_width",
                 "description": "Minimum column width. Default is 0 characters."
            }# ,
            #             {
            #                  "name": "sample",
            #                  "description": "Number of records to sample to get column width"
            #             },
        ]
    }
    def __init__(self, target=sys.stdout, max_column_width=None,
                 min_column_width=0, sample=None,
                 print_names=True, print_labels=False):

        super(PrettyPrinterNode, self).__init__()

        self.max_column_width = max_column_width
        self.min_column_width = min_column_width or 0
        self.sample = sample
        self.print_names = print_names
        self.print_labels = print_labels

        self.target = target
        self.handle = None
        self.close_handle = False

    def initialize(self):
        if type(self.target) == str or type(self.target) == unicode:
            self.handle = open(self.target, "w")
            self.close_handle = True
        else:
            self.handle = self.target
            self.close_handle = False

        self.widths = [0] * len(self.input.fields)
        self.names = self.input.fields.names()

        if self.print_names:
            self.labels = [f.label for f in self.input.fields]
        else:
            self.labels = [f.label or f.name for f in self.input.fields]

        self._update_widths(self.names)
        if self.print_labels:
            self._update_widths(self.labels)

    def _update_widths(self, row):
        for i, value in enumerate(row):
            self.widths[i] = max(self.widths[i], len(unicode(value)))

    def run(self):

        rows = []

        for row in self.input.rows():
            rows.append(row)
            self._update_widths(row)

        #
        # Create template
        #

        if self.max_column_width:
            self.widths = [min(w, self.max_column_width) for w in self.widths]
        self.widths = [max(w, self.min_column_width) for w in self.widths]
        fields = [u"{%d:%d}" % (i, w) for i,w in enumerate(self.widths)]
        template = u"|" + u"|".join(fields) + u"|\n"

        field_borders = [u"-"*w for w in self.widths]
        self.border = u"+" + u"+".join(field_borders) + u"+\n"

        self.handle.write(self.border)
        if self.print_names:
            self.handle.write(template.format(*self.names))
        if self.print_labels:
            self.handle.write(template.format(*self.labels))

        if self.print_names or self.print_labels:
            self.handle.write(self.border)

        for row in rows:
            self.handle.write(template.format(*row))

        self.handle.write(self.border)

        self.handle.flush()

    def finalize(self):
        if self.handle:
            self.handle.flush()
            if self.close_handle:
                self.handle.close()

class SQLTableTargetNode(TargetNode):
    """Feed data rows into a relational database table.
    """
    node_info = {
        "label": "SQL Table Target",
        "icon": "sql_table_target",
        "description" : "Feed data rows into a relational database table",
        "attributes" : [
            {
                 "name": "url",
                 "description": "Database URL in form: adapter://user:password@host/database"
            },
            {
                 "name": "connection",
                 "description": "SQLAlchemy database connection - either this or url should be specified",
            },
            {
                 "name": "table",
                 "description": "table name"
            },
            {
                 "name": "truncate",
                 "description": "If set to ``True`` all data table are removed prior to node "
                                "execution. Default is ``False`` - data are appended to the table"
            },
            {
                 "name": "create",
                 "description": "create table if it does not exist or not"
            },
            {
                 "name": "replace",
                 "description": "Set to True if creation should replace existing table or not, "
                                "otherwise node will fail on attempt to create a table which "
                                "already exists"
            },
            {
                "name": "buffer_size",
                "description": "how many records are collected before they are "
                              "inserted using multi-insert statement. "
                              "Default is 1000"
            },
            {
                 "name": "options",
                 "description": "other SQLAlchemy connect() options"
            }
        ]
    }

    def __init__(self, url=None, table=None, truncate=False, create=False,
                 replace=False, **kwargs):
        super(SQLTableTargetNode, self).__init__()
        self.url = url
        self.table = table
        self.truncate = truncate
        self.create = create
        self.replace = replace

        self.kwargs = kwargs
        self.stream = None

        # FIXME: document this
        self.concrete_type_map = None

    def initialize(self):
        self.stream = SQLDataTarget(url=self.url,
                                table=self.table,
                                truncate=self.truncate,
                                create=self.create,
                                replace=self.replace,
                                **self.kwargs)

        self.stream.fields = self.input_fields
        self.stream.concrete_type_map = self.concrete_type_map
        self.stream.initialize()

    def run(self):
        for row in self.input.rows():
            self.stream.append(row)

    def finalize(self):
        """Flush remaining records and close the connection if necessary"""
        self.stream.finalize()

# Original name is depreciated
DatabaseTableTargetNode = SQLTableTargetNode

########NEW FILE########
__FILENAME__ = scraperwiki
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from brewery import ds
from brewery.nodes import Node
import urllib

SWIKI_BASEURL = "http://api.scraperwiki.com/api/1.0/datastore/getdata"

class ScraperWikiDataSource(ds.CSVDataSource):
    def __init__(self, name):
        """Creates a data source that will read data from scraperwiki scraper"""
        self.scraper_name = name
        self.stream = None
        
        params = {
            "name": self.scraper_name,
            "format": "csv"
        }

        params_str = urllib.urlencode(params)
        data_url = SWIKI_BASEURL + "?" + params_str

        super(ScraperWikiDataSource, self).__init__(data_url, read_header = True, 
                                                    encoding = "utf-8")

class ScraperWikiSourceNode(Node):
    """Source node that reads data from a Scraper Wiki scraper.
    
    See: http://scraperwiki.com/
    """
    __node_info__ = {
        "label" : "Scraper Wiki Source",
        "icon": "generic_node",
        "description" : "Read data from a Scraper Wiki scraper.",
        "attributes" : [
            {
                 "name": "scraper",
                 "description": "Scraper name"
            }
        ]
    }

    def __init__(self, scraper = None):
        super(ScraperWikiSourceNode, self).__init__()
        self.scraper = scraper

    def initialize(self):
        self.stream = ScraperWikiDataSource(self.scraper)
        self.stream.initialize()

    @property
    def output_fields(self):
        return self.stream.fields
        
    def run(self):
        for row in self.stream.rows():
            self.put(row)
    
    def finalize(self):
        self.stream.finalize()
        
########NEW FILE########
__FILENAME__ = probes
"""Data probes"""

import utils
import re

__all__ = [
    "MissingValuesProbe",
    "StatisticsProbe",
    "DistinctProbe",
    "StorageTypeProbe",
    "MultiProbe",
    "CompletenessProbe"
]

class MultiProbe(object):
    """Probe with multiple probes"""
    def __init__(self, probes = None):
        if probes:
            self.probes = probes
        else:
            self.probes = []

    def probe(self, value):
        for probe in self.probes:
            probe.probe(value)


    def to_dict(self):
        d = {}
        for probe in self.probes:
            name = utils.to_identifier(utils.decamelize(probe.__class__.__name__))
            re.sub('_probe$', name, '')
            d[name] = probe.to_dict()

        return d

class MissingValuesProbe(object):
    """Data quality statistics for a dataset field

    :Attributes:
        * `count`: total count of null records
    """
    def __init__(self):
        self.count = 0

    def probe(self, value):
        """Probe the value.
        """

        if value is None:
            self.count += 1

    def to_dict(self):
        return {"count": self.count}

class CompletenessProbe(object):
    """Data quality statistics for a dataset field

    :Attributes:
        * `count`: total count of records
        * `unknown`: number of unknown records (NULL, None, nil, ...)
    """
    def __init__(self):
        self.count = 0
        self.unknown = 0

    def probe(self, value):
        """Probe the value.
        """
        self.count += 1
        if value is None:
            self.unknown += 1

    def to_dict(self):
        return {"count": self.count, "unknown": self.unknown}

class StatisticsProbe(object):
    """Data quality statistics for a dataset field

    :Attributes:
        * `min` - minimum value found
        * `max` - maxumum value found
        * `sum` - sum of values
        * `count` - count of values
        * `average` - average value
    """
    def __init__(self):
        self.min = None
        self.max = None
        self.sum = None
        self.count = 0
        self.fields = ["min", "max", "sum", "count"]

    @property
    def average(self):
        return self.sum / self.count

    def probe(self, value):
        self.count += 1
        if value is not None:
            if self.sum is None:
                self.sum = value
                self.min = value
                self.max = value
            else:
                self.sum += value
                self.min = min(self.min, value)
                self.max = max(self.max, value)

    def to_dict(self):
        return {"count": self.count, "min": self.min, "max": self.max,
                "sum": self.sum, "average": self.average }

class DistinctProbe(object):
    """Probe for distinct values."""
    def __init__(self, threshold = None):
        self.values = set([])
        self.overflow = False
        self.threshold = threshold
        self.fields = ["values", ("overflow", "integer")]

    def probe(self, value):
        self.overflow = self.threshold and len(self.values) >= self.threshold

        if not self.overflow:
            self.values.add(value)

class StorageTypeProbe(object):
    """Probe for guessing field data type

    Attributes:
        * field: name of a field which statistics are being presented
        * storage_types: found storage types
        * unique_storage_type: if there is only one storage type, then this is set to that type
    """
    def __init__(self):
        self.storage_types = set()

    def probe(self, value):
        storage_type = value.__class__
        self.storage_types.add(storage_type.__name__)

    @property
    def unique_storage_type(self):
        """Return storage type if there is only one. This should always return a type in relational
        databases, but does not have to in databases such as MongoDB."""

        if len(self.storage_types) == 1:
            return list(self.storage_types)[0]
        else:
            return None

    def to_dict(self):
        d = {
            "storage_types": [str(st) for st in self.storage_types],
            "unique_storage_type": self.unique_storage_type
        }
        return d

class ValueTypeProbe(object):
    """Probe for guessing field value data type. It should be one of:
       `int`, `float`, ...

    Attributes:
        * field: name of a field which statistics are being presented
        * storage_types: found storage types
        * unique_storage_type: if there is only one storage type, then this is set to that type
    """
    def __init__(self):
        self.int_count = 0
        self.float_count = 0
        self.date_count = 0
        # ISO datetime "%Y-%m-%dT%H:%M:%S" )

    def probe(self, value):
        storage_type = value.__class__
        self.storage_types.add(storage_type.__name__)

    @property
    def unique_storage_type(self):
        """Return storage type if there is only one. This should always return a type in relational
        databases, but does not have to in databases such as MongoDB."""

        if len(self.storage_types) == 1:
            return list(self.storage_types)[0]
        else:
            return None

    def to_dict(self):
        d = {
            "storage_types": [str(st) for st in self.storage_types],
            "unique_storage_type": self.unique_storage_type
        }
        return d

########NEW FILE########
__FILENAME__ = streams
# -*- coding: utf-8 -*-

import threading
import sys
from brewery.nodes.base import node_dictionary, TargetNode, NodeFinished
from brewery.utils import get_logger
from brewery.nodes import *
from brewery.common import *
from .graph import *

__all__ = [
    "Stream",
    "Pipe",
    "stream_from_dict",
    "create_builder"
]

JOIN_TIMEOUT = None

def stream_from_dict(desc):
    """Create a stream from dictionary `desc`."""
    stream = Stream()
    stream.update(desc)
    return stream

class SimpleDataPipe(object):
    """Dummy pipe for testing nodes"""
    def __init__(self):
        self.buffer = []
        self.fields = None
        self._closed = False

    def closed(self):
        return self._closed

    def rows(self):
        return self.buffer

    def records(self):
        """Get data objects from pipe as records (dict objects). This is convenience method with
        performance costs. Nodes are recommended to process rows instead."""
        if not self.fields:
            raise Exception("Can not provide records: fields for pipe are not initialized.")
        fields = self.fields.names()
        for row in self.rows():
            yield dict(zip(fields, row))

    def put_record(self, record):
        """Convenience method that will transform record into a row based on pipe fields."""
        row = [record.get(field) for field in self.fields.names()]

        self.put(row)

    def put(self, obj):
        self.buffer.append(obj)

    def done_receiving(self):
        self._closed = True
        pass

    def done_sending(self):
        pass

    def empty(self):
        self.buffer = []

class Pipe(SimpleDataPipe):
    """Data pipe:
    Contains buffer for data that should be thransferred to another node.
    Data are being sent t other node when the buffer is full. Pipe is one-directional where
    one thread is sending data to another thread. There is only one backward signalling: closing
    the pipe from remote object.


    """

    def __init__(self, buffer_size=1000):
        """Creates uni-drectional data pipe for passing data between two threads in batches of size
        `buffer_size`.

        If receiving node is finished with source data and does not want anything any more, it
        should send ``done_receiving()`` to the pipe. In most cases, stream runner will send
        ``done_receiving()`` to all input pipes when node's ``run()`` method is finished.

        If sending node is finished, it should send ``done_sending()`` to the pipe, however this
        is not necessary in most cases, as the method for running stream flushes outputs
        automatically on when node ``run()`` method is finished.
        """

        super(Pipe, self).__init__()
        self.buffer_size = buffer_size

        # Should it be deque or array?
        self.staging_buffer = []
        self._ready_buffer = None

        self._done_sending = False
        self._done_receiving = False
        self._closed = False

        # Taken from Python Queue implementation:

        # mutex must beheld whenever the queue is mutating.  All methods
        # that acquire mutex must release it before returning.  mutex
        # is shared between the three conditions, so acquiring and
        # releasing the conditions also acquires and releases mutex.
        self.mutex = threading.Lock()
        # Notify not_empty whenever an item is added to the queue; a
        # thread waiting to get is notified then.
        self.not_empty = threading.Condition(self.mutex)
        # Notify not_full whenever an item is removed from the queue;
        # a thread waiting to put is notified then.
        self.not_full = threading.Condition(self.mutex)

    def is_full(self):
        return len(self.staging_buffer) >= self.buffer_size

    def is_consumed(self):
        return self._ready_buffer is None

    def put(self, obj):
        """Put data object into the pipe buffer. When buffer is full it is enqueued and receiving node
        can get all buffered data objects.

        Puttin object into pipe is not thread safe. Only one thread sohuld write to the pipe.
        """
        self.staging_buffer.append(obj)

        if self.is_full():
            self._flush()
    def _note(self, note):
        # print note
        pass

    def _flush(self, close=False):
        self._note("P flushing: close? %s closed? %s" % (close, self._closed))
        self._note("P _nf acq?")
        self.not_full.acquire()
        if self._closed:
            self._note("P _not_full rel!")
            self.not_full.release()
            return
        elif len(self.staging_buffer) == 0:
            try:
                self._closed = close
                self.not_empty.notify()
            finally:
                self._note("P _not_full rel!")
                self.not_full.release()
            return

        try:
            self._note("P _not_full wait ...")
            while not self.is_consumed() and not self._closed:
                self.not_full.wait()
            self._note("P _not_full got <")
            if not self._closed:
                self._ready_buffer = self.staging_buffer
                self.staging_buffer = []
                self._closed = close
                self._note("P _not_empty notify >")
                self.not_empty.notify()

        finally:
            self._note("P _not_full rel!")
            self.not_full.release()

    def rows(self):
        """Get data object from pipe. If there is no buffer ready, wait until source object sends
        some data."""

        done_sending = False
        while not done_sending:
            self._note("C _not_empty acq?")
            self.not_empty.acquire()
            try:
                self._note("C _not_empty wait ...")
                while not self._ready_buffer and not self._closed:
                    self.not_empty.wait()
                self._note("C _not_empty got <")

                if self._ready_buffer:
                    rows = self._ready_buffer
                    self._ready_buffer = None
                    self._note("C _not_full notify >")
                    self.not_full.notify()

                    for row in rows:
                        yield row
                else:
                    self._note("C no buffer")


                done_sending = self._closed
            finally:
                self._note("_not_empty rel!")
                self.not_empty.release()

    def closed(self):
        """Return ``True`` if pipe is closed - not sending or not receiving data any more."""
        return self._closed

    def done_sending(self):
        """Close pipe from sender side"""
        self._flush(True)

    def done_receiving(self):
        """Close pipe from either side"""
        self._note("C not_empty acq? r")
        self.not_empty.acquire()
        self._note("C closing")
        self._closed = True
        self._note("C notif close")
        self.not_full.notify()
        self.not_empty.release()

        self._note("C not_empty rel! r")

class Stream(Graph):
    """Data processing stream"""
    def __init__(self, nodes=None, connections=None):
        """Creates a data stream.

        :Parameters:
            * `nodes` - dictionary with keys as node names and values as nodes
            * `connections` - list of two-item tuples. Each tuple contains source and target node
              or source and target node name.
            * `stream` - another stream or
        """
        super(Stream, self).__init__(nodes, connections)
        self.logger = get_logger()

        self.exceptions = []

    def fork(self):
        """Creates a construction fork of the stream. Used for constructing streams in functional
        fashion. Example::

            stream = Stream()

            fork = stream.fork()
            fork.csv_source("fork.csv")
            fork.formatted_printer()

            stream.run()

        Fork responds to node names as functions. The function arguments are the same as node
        constructor (__init__ method) arguments. Each call will append new node to the fork and
        will connect the new node to the previous node in the fork.

        To configure current node you can use ``fork.node``, like::

            fork.csv_source("fork.csv")
            fork.node.read_header = True

        To set actual node name use ``set_name()``::

            fork.csv_source("fork.csv")
            fork.set_name("source")

            ...

            source_node = stream.node("source")

        To fork a fork, just call ``fork()``
        """

        return _StreamFork(self)

    def update(self, nodes = None, connections = None):
        """Adds nodes and connections specified in the dictionary. Dictionary might contain
        node names instead of real classes. You can use this method for creating stream
        from a dictionary that was created from a JSON file, for example.
        """

        node_dict = node_dictionary()

        # FIXME: use either node type identifier or fully initialized node, not
        #        node class (Warning: might break some existing code,
        #        depreciate it first

        nodes = nodes or {}
        connections = connections or []

        for (name, obj) in nodes.items():
            if isinstance(obj, Node):
                node_instance = obj
            elif isinstance(obj, type) and issubclass(obj, Node):
                self.logger.warn("Using classes in Stream.update is depreciated")
                node_instance = obj()
            else:
                if not "type" in obj:
                    raise Exception("Node dictionary has no 'type' key")
                node_type = obj["type"]

                if node_type in node_dict:
                    node_class = node_dict[node_type]
                    node_instance = node_class()

                    node_instance.configure(obj)
                else:
                    raise Exception("No node class of type '%s'" % node_type)

            self.add(node_instance, name)

        if connections:
            for connection in connections:
                self.connect(connection[0], connection[1])

    def configure(self, config=None):
        """Configure node properties based on configuration. Only named nodes can be configured at the
        moment.

        `config` is a list of dictionaries with keys: ``node`` - node name, ``parameter`` - node parameter
        name, ``value`` - parameter value

        .. warning:

            This method might change to a list of dictionaries where one
            dictionary will represent one node, keys will be attributes.

        """

        # FIXME: this is wrong, it should be a single dict per node (or not?)
        # List of attributes:
        #     * can reflect a form for configuring whole stream
        #     * can have attribute order regardless of their node ownership
        # List of nodes:
        #     * bundled attributes in single dictioary
        # FIXME: this is inconsistent with node configuration! node.config()
        if config is None:
            config = {}
        configurations = {}

        # Collect configurations for each node

        for attribute in config:
            node_name = attribute["node"]
            attribute_name = attribute["attribute"]
            value = attribute.get("value")

            if not node_name in configurations:
                config = {}
                configurations[node_name] = config
            else:
                config = configurations[node_name]

            config[attribute_name] = value

        # Configure nodes

        for (node_name, config) in configurations.items():
            node = self.coalesce_node(node_name)
            node.configure(config)

    def _initialize(self):
        """Initializes the data processing stream:

        * sorts nodes based on connection dependencies
        * creates pipes between nodes
        * initializes each node
        * initializes pipe fields

        """

        self.logger.info("initializing stream")
        self.logger.debug("sorting nodes")
        sorted_nodes = self.sorted_nodes()
        self.pipes = []

        self.logger.debug("flushing pipes")
        for node in sorted_nodes:
            node.inputs = []
            node.outputs = []

        # Create pipes and connect nodes
        for node in sorted_nodes:
            self.logger.debug("creating pipes for node %s" % node)

            targets = self.node_targets(node)
            for target in targets:
                self.logger.debug("  connecting with %s" % (target))
                pipe = Pipe()
                node.add_output(pipe)
                target.add_input(pipe)
                self.pipes.append(pipe)

        # Initialize fields
        for node in sorted_nodes:
            self.logger.debug("initializing node of type %s" % node.__class__)
            self.logger.debug("  node has %d inputs and %d outputs"
                                % (len(node.inputs), len(node.outputs)))
            node.initialize()

            # Ignore target nodes
            if isinstance(node, TargetNode):
                self.logger.debug("  node is target, ignoring creation of output pipes")
                continue

            fields = node.output_fields
            self.logger.debug("  node output fields: %s" % fields.names())
            for output_pipe in node.outputs:
                output_pipe.fields = fields

    def run(self):
        """Run all nodes in the stream.

        Each node is being wrapped and run in a separate thread.

        When an exception occurs, the stream is stopped and all catched exceptions are stored in
        attribute `exceptions`.

        """
        self._initialize()

        # FIXME: do better exception handling here: what if both will raise exception?
        try:
            self._run()
        finally:
            self._finalize()

    def _run(self):
        self.logger.info("running stream")

        threads = []
        sorted_nodes = self.sorted_nodes()

        self.logger.debug("launching threads")
        for node in sorted_nodes:
            self.logger.debug("launching thread for node %s" % node_label(node))
            thread = _StreamNodeThread(node)
            thread.start()
            threads.append((thread, node))

        self.exceptions = []
        for (thread, node) in threads:
            self.logger.debug("joining thread for %s" % node_label(node))
            while True:
                thread.join(JOIN_TIMEOUT)
                if thread.isAlive():
                    pass
                    # self.logger.debug("thread join timed out")
                else:
                    if thread.exception:
                        self._add_thread_exception(thread)
                    else:
                        self.logger.debug("thread joined")
                    break
                if self.exceptions:
                    self.logger.info("node exception occured, trying to kill threads")
                    self.kill_threads()

        if self.exceptions:
            self.logger.info("run finished with exception")
            # Raising only first exception found
            raise self.exceptions[0]
        else:
            self.logger.info("run finished sucessfully")

    def _add_thread_exception(self, thread):
        """Create a StreamRuntimeError exception object and fill attributes with all necessary
        values.
        """
        node = thread.node
        exception = StreamRuntimeError(node=node, exception=thread.exception)

        exception.traceback = thread.traceback
        exception.inputs = [pipe.fields for pipe in node.inputs]

        if not isinstance(node, TargetNode):
            try:
                exception.ouputs = node.output_fields
            except:
                pass

        node_info = node.node_info

        attrs = {}
        if node_info and "attributes" in node_info:
            for attribute in node_info["attributes"]:
                attr_name = attribute.get("name")
                if attr_name:
                    try:
                        value = getattr(node, attr_name)
                    except AttributeError:
                        value = "<attribute %s does not exist>" % attr_name
                    except Exception , e:
                        value = e
                    attrs[attr_name] = value

        exception.attributes = attrs

        self.exceptions.append(exception)


    def kill_threads(self):
        self.logger.info("killing threads")

    def _finalize(self):
        self.logger.info("finalizing nodes")

        # FIXME: encapsulate finalization in exception handler, collect exceptions
        for node in self.sorted_nodes():
            self.logger.debug("finalizing node %s" % node_label(node))
            node.finalize()

def node_label(node):
    """Debug label for a node: node identifier with python object id."""
    return "%s(%s)" % (node.identifier() or str(type(node)), id(node))

class _StreamNodeThread(threading.Thread):
    def __init__(self, node):
        """Creates a stream node thread.

        :Attributes:
            * `node`: a Node object
            * `exception`: attribute will contain exception if one occurs during run()
            * `traceback`: will contain traceback if exception occurs

        """
        super(_StreamNodeThread, self).__init__()
        self.node = node
        self.exception = None
        self.traceback = None
        self.logger = get_logger()

    def run(self):
        """Wrapper method for running a node"""

        label = node_label(self.node)
        self.logger.debug("%s: start" % label)
        try:
            self.node.run()
        except NodeFinished:
            self.logger.info("node %s finished" % label)
        except Exception as e:
            tb = sys.exc_info()[2]
            self.traceback = tb

            self.logger.debug("node %s failed: %s" % (label, e.__class__.__name__), exc_info=sys.exc_info)
            self.exception = e

        # Flush pipes after node is finished
        self.logger.debug("%s: finished" % label)
        self.logger.debug("%s: flushing outputs" % label)
        for pipe in self.node.outputs:
            if not pipe.closed():
                pipe.done_sending()
        self.logger.debug("%s: flushed" % label)
        self.logger.debug("%s: stopping inputs" % label)
        for pipe in self.node.inputs:
            if not pipe.closed():
                pipe.done_sending()
        self.logger.debug("%s: stopped" % self)

class _StreamFork(object):
    """docstring for StreamFork"""
    def __init__(self, stream, node=None):
        """Creates a stream fork - class for building streams."""
        super(_StreamFork, self).__init__()
        self.stream = stream
        self.node = node

    def __iadd__(self, node):
        """Appends a node to the actual stream. The new node becomes actual node of the
        for."""

        self.stream.add(node)
        if self.node:
            self.stream.connect(self.node, node)
        self.node = node

        return self

    def set_name(self, name):
        """Sets name of current node."""
        self.stream.set_node_name(self.node, name)

    def fork(self):
        """Forks current fork. Returns a new fork with same actual node as the fork being
        forked."""
        fork = _StreamFork(self.stream, self.node)
        return fork

    def merge(self, obj, **kwargs):
        """Joins two streams using the MergeNode (please refer to the node documentaton
        for more information).

        `obj` is a fork or a node to be merged. `kwargs` are MergeNode configuration arguments,
        such as `joins`.

        """
        raise NotImplementedError
        # if type(obj) == StreamFork:
        #     node = obj.node
        # else:
        #     node = obj
        #
        # self.stream.append(node)
        #
        # merge = MergeNode(**kwargs)
        # self.stream.append(merge)
        # self.stream.connect()

    def append(self, obj):
        """Appends data from nodes using AppendNode"""
        raise NotImplementedError

    def __getattr__(self, name):
        """Returns node class"""
        # FIXME: use create_node here

        class_dict = node_dictionary()

        node_class = class_dict[name]

        constructor = _StreamForkConstructor(self, node_class)
        return constructor

class _StreamForkConstructor(object):
    """Helper class to append new node."""
    def __init__(self, fork, node_class):
        self.fork = fork
        self.node_class = node_class

    def __call__(self, *args, **kwargs):
        node = self.node_class(*args, **kwargs)
        print "CALLING %s - %s" % (self.node_class, node)
        self.fork += node
        return self.fork

def create_builder():
    """Creates a stream builder for incremental stream building."""
    stream = Stream()
    return stream.fork()


########NEW FILE########
__FILENAME__ = test_data_quality
import unittest
import brewery
import brewery.nodes
import brewery.probes as probes

class DataQualityTestCase(unittest.TestCase):
    def setUp(self):
        self.records = []
        for i in range(0,101):
            record = {}
            record["i"] = i
            record["bubble"] = i % 21 + 20

            # Some duplicates on key 'i'
            record["dup_i"] = i % 90

            # Some empty values
            if (i % 2) == 0:
                record["even"] = True
            else:
                record["even"] = None

            # Some missing values
            if (i % 7) == 0:
                record["seven"] = True

            if (i < 10) == 0:
                record["small"] = True
            else:
                record["small"] = False

            # Some set for distinct
            if (i % 3) == 0:
                record["type"] = "three"
            elif (i % 5) == 0:
                record["type"] = "five"
            elif (i % 7) == 0:
                record["type"] = "seven"
            else:
                record["type"] = "unknown"

            self.records.append(record)
        
    def test_completeness_probe(self):
        probe_i = probes.MissingValuesProbe()
        probe_even = probes.MissingValuesProbe()
        for record in self.records:
            probe_i.probe(record["i"])
            probe_even.probe(record["even"])
        
        self.assertEqual(0, probe_i.count)
        self.assertEqual(50, probe_even.count)
        
    def test_statistics_probe(self):
        probe_i = probes.StatisticsProbe()
        probe_bubble = probes.StatisticsProbe()

        for record in self.records:
            probe_i.probe(record["i"])
            probe_bubble.probe(record["bubble"])   
            
        self.assertEqual(0, probe_i.min)
        self.assertEqual(100, probe_i.max)
        self.assertEqual(50, probe_i.average)
        self.assertEqual(5050, probe_i.sum)

        self.assertEqual(20, probe_bubble.min)
        self.assertEqual(40, probe_bubble.max)
        self.assertEqual(2996, probe_bubble.sum)

    def test_distinct_probe(self):
        probe = probes.DistinctProbe()
        
        for record in self.records:
            probe.probe(record["type"])
        
        distinct = list(probe.values)
        distinct.sort()
        print "DISTINCT: %s" % distinct
        self.assertEqual(4, len(distinct))
        self.assertEqual(["five", "seven", "three", "unknown"], distinct)
        
########NEW FILE########
__FILENAME__ = test_data_source
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import os
import brewery.ds
import brewery

TESTS_PATH = os.path.dirname(os.path.abspath(__file__))

class DataSourceUtilsTestCase(unittest.TestCase):
    def test_expand_collapse(self):
        record = { "name": "foo", 
                    "entity.name": "bar", 
                    "entity.number" : 10, 
                    "entity.address.country": "Uganda" }
        ex_record = { "name": "foo", 
                     "entity": { "name": "bar", 
                                 "number" : 10, 
                                 "address": {"country": "Uganda" }
                                }
                    }
                
        self.assertEqual(ex_record, brewery.expand_record(record))
        self.assertEqual(record, brewery.collapse_record(ex_record))

# class DataStoreTestCase(unittest.TestCase):
#     def setUp(self):
#         pass
# 
#     def test_stores(self):
#         
#       self.assertRaisesRegexp(Exception, "datastore with name", brewery.ds.datastore, "foo")
#         desc = {"url":":memory:"}
#       self.assertRaisesRegexp(ValueError, "No adapter provided", brewery.ds.datastore, desc)
# 
#         desc = {"adapter":"foo", "path":":memory:"}
#       self.assertRaisesRegexp(KeyError, "Adapter.*foo.*not found", brewery.ds.datastore, desc)
# 
#         desc = {"adapter":"sqlalchemy", "url":"sqlite:///:memory:"}
#         ds = brewery.ds.datastore(desc)
#       self.assertEqual("sqlalchemy", ds.adapter_name)
 		
class DataSourceTestCase(unittest.TestCase):
    output_dir = None
    @classmethod
    def setUpClass(cls):
        DataSourceTestCase.output_dir = 'test_out'
        if not os.path.exists(DataSourceTestCase.output_dir):
            os.makedirs(DataSourceTestCase.output_dir)
    @classmethod
    def tearDownClass(cls):
        pass
        
    def setUp(self):
        self.data_dir = os.path.join(TESTS_PATH, 'data')
        self.output_dir = DataSourceTestCase.output_dir
    
    def data_file(self, file):
        return os.path.join(self.data_dir, file)
    def output_file(self, file):
        return os.path.join(self.output_dir, file)

    def read_source(self, source):
        count = 0
        max_fields = 0
        min_fields = 0
        self.rows = []
        for row in source.rows():
            count += 1
            max_fields = max(len(row), max_fields)
            min_fields = max(len(row), min_fields)
            self.rows.append(row)
            
        return { "count" : count, "max_fields": max_fields, "min_fields": min_fields }

    def test_file_source(self):
        # File
        src = brewery.ds.CSVDataSource(self.data_file('test.csv'))
        src.read_header = False
        # test = lambda: src.get_fields()
        self.assertRaises(RuntimeError, src.rows)
        
        src.read_header = True
        src.initialize()
        names = [field.name for field in src.fields]
        self.assertEqual(['id', 'name', 'type', 'location.name', 'location.code', 'amount'], names)

        result = self.read_source(src)
            
        self.assertEqual(6, result["max_fields"])
        self.assertEqual(6, result["min_fields"])
        self.assertEqual(8, result["count"])

    def test_csv_dialect(self):
        src = brewery.ds.CSVDataSource(self.data_file('test_tab.csv'), dialect = "foo")
        self.assertRaises(Exception, src.initialize)

        src = brewery.ds.CSVDataSource(self.data_file('test_tab.csv'), dialect = "excel-tab")
        src.initialize()
        result = self.read_source(src)
        self.assertEqual(3, result["max_fields"])
        self.assertEqual(3, result["min_fields"])
        self.assertEqual(8, result["count"])


    def test_csv_field_type(self):
        src = brewery.ds.CSVDataSource(self.data_file('test.csv'), skip_rows=1,read_header=False)
        fields = ['id', 'name', 'type', 'location.name', 'location.code', ['amount', 'integer']]
        src.fields = brewery.FieldList(fields)
        src.initialize()
        self.assertEqual("integer", src.fields[5].storage_type)

        result = self.read_source(src)
        self.assertEqual(True, isinstance(self.rows[0][1], basestring))
        self.assertEqual(True, isinstance(self.rows[0][5], int))
    
    def test_xls_source(self):
        src = brewery.ds.XLSDataSource(self.data_file('test.xls'))
        src.initialize()
        result = self.read_source(src)
        self.assertEqual(3, result["max_fields"])
        self.assertEqual(3, result["min_fields"])
        self.assertEqual(8, result["count"])

    def test_copy(self):
        src = brewery.ds.CSVDataSource(self.data_file('test_tab.csv'), dialect = "excel-tab")
        src.initialize()

        fields = src.fields

        target = brewery.ds.CSVDataTarget(self.output_file('test_out.csv'))
        target.fields = fields
        target.initialize()

        for row in src.rows():
            target.append(row)
        target.finalize()
        
        src2 = brewery.ds.CSVDataSource(self.output_file('test_out.csv'))
        src2.initialize()
        result = self.read_source(src2)
            
        self.assertEqual(3, result["max_fields"])
        self.assertEqual(3, result["min_fields"])
        self.assertEqual(8, result["count"])

    def test_row_record(self):
        pass
        # * Test whether all streams support correctly reading/writing both records and rows
        # * Streams should raise an exception when writing a row into a stream without initalized
        #   fields
        # * If fields are set to source stream, it should not return other fields as specified
    
    def test_auditor(self):
        src = brewery.ds.CSVDataSource(self.data_file('test.csv'))
        src.initialize()

        auditor = brewery.ds.StreamAuditor()
        auditor.fields = src.fields
        auditor.initialize()
        
        # Perform audit for each row from source:
        for row in src.rows():
            auditor.append(row)

        # Finalize results, close files, etc.
        auditor.finalize()

        # Get the field statistics
        stats = auditor.field_statistics
        
        self.assertEqual(len(stats), 6)
        stat = stats["type"].dict()
        self.assertTrue("record_count" in stat)
        self.assertTrue("unique_storage_type" in stat)
        utype = stat["unique_storage_type"]
        ftype = stat["storage_types"][0]
        self.assertEqual(utype, ftype)
        
        src.finalize()

    # def test_sqlite_source(self):
    #     return
    #     src = brewery.ds.RelationalDataSource(self.connection, "test_amounts")
    #     names = [field.name for field in src.fields]
    #     self.assertEqual(["trans_date", "subject", "amount"], names, 'Read fields do not match')
    # 
    #     date_field = src.fields[0]
    #     subject_field = src.fields[1]
    #     amount_field = src.fields[2]
    #     
    #     self.assertEqual("trans_date", date_field.name)
    #     self.assertEqual("date", date_field.storage_type)
    # 
    #     self.assertEqual("subject", subject_field.name)
    #     self.assertEqual("string", subject_field.storage_type)
    #     self.assertEqual("unknown", subject_field.analytical_type)
    # 
    #     self.assertEqual("amount", amount_field.name)
    #     self.assertEqual("numeric", amount_field.storage_type)
    #     self.assertEqual("range", amount_field.analytical_type)
		
    # def test_mongo_source(self):
    #     connection_desc = { "adapter": "mongodb", "host":"localhost", "database":"wdmmg"}
    #     ds = brewery.ds.datastore(connection_desc)
    #     src = brewery.ds.data_source(datastore = ds, dataset = "classifier")
        
		
if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_field_list
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import brewery
from brewery import ds

class FieldListCase(unittest.TestCase):
    def test_names(self):
        field = brewery.Field("bar")
        self.assertEqual("bar", str("bar"))
        self.assertEqual(field.name, str("bar"))

    def test_list_creation(self):
        fields = brewery.FieldList(["foo", "bar"])

        for field in fields:
            self.assertEqual(type(field), brewery.Field)

        self.assertEqual("foo", fields[0].name, 'message')
        self.assertEqual(2, len(fields))

    def test_list_add(self):
        fields = brewery.FieldList(["foo", "bar"])
        fields.append("baz")
        self.assertEqual(3, len(fields))
        
    def test_indexes(self):
        fields = brewery.FieldList(["a", "b", "c", "d"])
        indexes = fields.indexes( ["a", "c", "d"] )
        self.assertEqual((0,2,3), indexes)

        indexes = fields.indexes( fields.fields() )
        self.assertEqual((0,1,2,3), indexes)

    def test_deletion(self):
        fields = brewery.FieldList(["a", "b", "c", "d"])
        del fields[0]
        
        self.assertEqual(["b", "c", "d"], fields.names())
        
        del fields[2]
        self.assertEqual(["b", "c"], fields.names())
        
        self.assertRaises(KeyError, fields.field, "d")
        self.assertEqual(2, len(fields))
        
    def test_contains(self):
        fields = brewery.FieldList(["a", "b", "c", "d"])
        field = brewery.Field("a")
        
        self.assertEqual(True, "a" in fields)
        self.assertEqual(True, field in fields)
        
    def test_retype(self):
        fields = brewery.FieldList(["a", "b", "c", "d"])
        self.assertEqual("unknown", fields.field("a").storage_type)
        retype_dict = {"a": {"storage_type":"integer"}}
        fields.retype(retype_dict)
        self.assertEqual("integer", fields.field("a").storage_type)

        retype_dict = {"a": {"name":"foo"}}
        self.assertRaises(Exception, fields.retype, retype_dict)
        
    def test_selectors(self):
        fields = brewery.FieldList(["a", "b", "c", "d"])
        selectors = fields.selectors(["b", "d"])
        self.assertEqual([False, True, False, True], selectors)
    
    # FIXME: move this to separate metadata/data utils testing
    def test_coalesce(self):
        self.assertEqual(1, brewery.coalesce_value("1", "integer"))
        self.assertEqual("1", brewery.coalesce_value(1, "string"))
        self.assertEqual(1.5, brewery.coalesce_value("1.5", "float"))
        self.assertEqual(1000, brewery.coalesce_value("1 000", "integer", strip=True))
        self.assertEqual(['1','2','3'], brewery.coalesce_value("1,2,3", "list", strip=True))
        
    
########NEW FILE########
__FILENAME__ = test_forks
import unittest
import os
import brewery

class ForksTestCase(unittest.TestCase):
    def test_basic(self):
        main = brewery.create_builder()
        main.csv_source("foo")
        
        self.assertEqual(1, len(main.stream.nodes))
        self.assertEqual("csv_source", main.node.identifier())

########NEW FILE########
__FILENAME__ = test_nodes
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import brewery
from brewery import ds
import brewery.nodes
import random

class StackTestCase(unittest.TestCase):

    def test_pop_returns_single_element(self):
        stack = brewery.nodes.Stack(5)
        stack.push(key = 1, value = "testing")
        self.assertEqual(stack.pop(), "testing")

    def test_pop_fails_on_empty_stack(self):
        stack = brewery.nodes.Stack(5)
        self.assertRaises(StopIteration, stack.pop)

    def test_lowest_keys_saved(self):
        stack = brewery.nodes.Stack(2)
        for i in range(5):
            stack.push(key = 1-float(i)/10., value = i)
        results = list(stack.items())
        self.assertSetEqual(set(results), set([0, 1]))

    def test_at_most_k_items(self):
        k = 5
        stack = brewery.nodes.Stack(k)
        for i in range(2*k):
            stack.push(key = float(i)/10., value = i)
        self.assertEqual(len(stack.items()), k)

class NodesTestCase(unittest.TestCase):
    def setUp(self):
        self.input = brewery.streams.SimpleDataPipe()
        self.output = brewery.streams.SimpleDataPipe()
            
    def setup_node(self, node):
        node.inputs = [self.input]
        node.outputs = [self.output]

    def create_sample(self, count = 100, custom = None, pipe = None):
        if not pipe:
            pipe = self.input
        pipe.empty()
        pipe.fields = brewery.FieldList(["i", "q", "str", "custom"])
        for i in range(0, count):
            pipe.put([i, float(i)/4, "item-%s" % i, custom])

    def test_node_subclasses(self):
        nodes = brewery.nodes.node_dictionary().values()
        self.assertIn(brewery.nodes.CSVSourceNode, nodes)
        self.assertIn(brewery.nodes.AggregateNode, nodes)
        self.assertIn(brewery.nodes.ValueThresholdNode, nodes)
        self.assertNotIn(brewery.streams.Stream, nodes)

    def test_node_dictionary(self):
        d = brewery.nodes.node_dictionary()
        self.assertIn("aggregate", d)
        self.assertIn("csv_source", d)
        self.assertIn("csv_target", d)
        self.assertNotIn("source", d)
        self.assertNotIn("aggregate_node", d)

    def test_sample_node_first_n(self):
        node = brewery.nodes.SampleNode(size = 5, discard_sample = False, method = 'first')
        self.setup_node(node)
        self.create_sample()
        self.initialize_node(node)
        node.run()
        node.finalize()
        
        self.assertEqual(len(self.output.buffer), 5)
        self.assertAllRows()

    def test_sample_node_random_n_returns_n_valid_rows(self):
        node = brewery.nodes.SampleNode(size = 5, discard_sample = False, method = 'random')
        self.setup_node(node)
        self.create_sample()
        self.initialize_node(node)
        node.run()
        node.finalize()
        
        self.assertEqual(len(self.output.buffer), 5)
        self.assertAllRows()

    def test_percent_cannot_be_more_than_100(self):
        def callable():
            node = brewery.nodes.SampleNode(size = 101, discard_sample = False, method = 'percent')
        self.assertRaises(ValueError, callable)

    def test_100_percent_returns_all(self):
        node = brewery.nodes.SampleNode(size = 100, discard_sample = False, method = 'percent')
        self.setup_node(node)
        self.create_sample()
        self.initialize_node(node)
        node.run()
        node.finalize()
        
        self.assertListEqual(self.output.buffer, self.input.buffer)

    def test_0_percent_returns_none(self):
        node = brewery.nodes.SampleNode(size = 0, discard_sample = False, method = 'percent')
        self.setup_node(node)
        self.create_sample()
        self.initialize_node(node)
        node.run()
        node.finalize()
        
        self.assertEqual(len(self.output.buffer), 0)

    def test_sample_node_percent_same_seed(self):
        # Instead of testing for true randomness as in http://www.johndcook.com/Beautiful_Testing_ch10.pdf
        #we test for know properties of the PRNG.
        #    - returns the same for same seed 
        #    - returns different for different seed
        self.create_sample()

        results = []
        for i in range(5):
            random.seed(1517)
            # create a new output pipe for each replication
            node = brewery.nodes.SampleNode(size = 10, discard_sample = False, method = 'percent')
            self.setup_node(node)
            node.outputs.append(brewery.streams.SimpleDataPipe())
            self.initialize_node(node)
            node.run()
            node.finalize()
            results.append(node.outputs[1].buffer)
        
        for result in results:
            self.assertListEqual(result, results[0])

    def test_sample_node_random_same_seed(self):
        self.create_sample()

        results = []
        for i in range(5):
            random.seed(1517)
            # create a new output pipe for each replication
            node = brewery.nodes.SampleNode(size = 1, discard_sample = False, method = 'random')
            self.setup_node(node)
            node.outputs.append(brewery.streams.SimpleDataPipe())
            self.initialize_node(node)
            node.run()
            node.finalize()
            results.append(node.outputs[1].buffer)
        
        for result in results:
            self.assertListEqual(result, results[0])

    def test_sample_node_percent_different_seed(self):
        self.create_sample()

        results = []
        for i in range(5):
            random.seed(i)
            # create a new output pipe for each replication
            node = brewery.nodes.SampleNode(size = 10, discard_sample = False, method = 'percent')
            self.setup_node(node)
            node.outputs.append(brewery.streams.SimpleDataPipe())
            self.initialize_node(node)
            node.run()
            node.finalize()
            results.append(node.outputs[1].buffer)

        # no pair of results should be equal
        for i in range(5):
            for j in range(i+1,5):
                self.assertNotEqual(results[i], results[j])

    def test_sample_node_random_different_seed(self):
        self.create_sample()

        results = []
        for i in range(5):
            random.seed(i)
            # create a new output pipe for each replication
            node = brewery.nodes.SampleNode(size = 1, discard_sample = False, method = 'random')
            self.setup_node(node)
            node.outputs.append(brewery.streams.SimpleDataPipe())
            self.initialize_node(node)
            node.run()
            node.finalize()
            results.append(node.outputs[1].buffer)

        # no pair of results should be equal
        for i in range(5):
            for j in range(i+1,5):
                self.assertNotEqual(results[i], results[j])

    def test_replace_node(self):
        node = brewery.nodes.TextSubstituteNode("str")
        self.setup_node(node)
        self.create_sample(10)
        node.add_substitution("[1-5]", "X")
        node.add_substitution("-", " ")
        self.initialize_node(node)
        node.run()
        node.finalize()
    
        for result in self.output.records():
            value = result["str"]
            self.assertRegexpMatches(value, "^item [X6-90]*$")
        self.assertAllRows()

    def test_append_node(self):
        node = brewery.nodes.AppendNode()
        self.setup_node(node)

        pipe1 = brewery.streams.SimpleDataPipe()
        self.create_sample(4, custom = "a", pipe = pipe1)

        pipe2 = brewery.streams.SimpleDataPipe()
        self.create_sample(4, custom = "b", pipe = pipe2)
        
        node.inputs = [pipe1, pipe2]
        
        self.initialize_node(node)
        ifields = pipe1.fields
        ofields = node.output_fields
        self.assertEqual(ifields, ofields)

        node.run()
        node.finalize()

        results = self.output.buffer

        self.assertEqual(len(results), 8)
        
        actual = [r[3] for r in results]
        expected = ['a'] * 4 + ['b'] * 4
        self.assertEqual(expected, actual)
        self.assertAllRows()
        
    def test_field_map(self):
        node = brewery.nodes.FieldMapNode()
        
        self.setup_node(node)
        self.create_sample(custom = "foo")
        
        node.rename_field("i", "index")
        node.drop_field("q")
        self.initialize_node(node)

        self.assertEqual(['index', 'str', 'custom'], node.output_fields.names())
        
        node.run()
        
        keys = set([])

        for result in self.output.records():
            for key in result.keys():
                keys.add(key)

        keys = list(keys)
        keys.sort()

        self.assertEqual(["custom", "index", "str"], keys)
        self.assertAllRows()

    def create_distinct_sample(self, pipe = None):
        if not pipe:
            pipe = self.input
        pipe.empty()
        pipe.fields = brewery.FieldList(["id", "id2", "q", "type", "class"])
        for i in range(1, 10):
            pipe.put([i, i, float(i)/4, "a", "x"])
            pipe.put([i, i*10, float(i)/4, "a", "y"])
            pipe.put([i*10, i*100, float(i)/4, "b", "x"])
            pipe.put([i*100, i*1000, float(i)/4, "c", "y"])
        
    def test_distinct(self):
        node = brewery.nodes.DistinctNode()
        self.setup_node(node)
        self.create_distinct_sample()

        self.initialize_node(node)
        ifields = self.input.fields
        ofields = node.output_fields
        self.assertEqual(ifields, ofields)

        node.run()
        node.finalize()
        
        self.assertEqual(36, len(self.output.buffer)) 

        # Test one field distinct
        self.output.empty()
        self.create_distinct_sample()

        node.distinct_fields = ["type"]
        node.initialize()
        node.run()
        node.finalize()

        self.assertEqual(3, len(self.output.buffer)) 

        # Test two field distinct
        self.output.empty()
        self.create_distinct_sample()

        node.distinct_fields = ["type", "class"]
        node.initialize()
        node.run()
        node.finalize()

        self.assertEqual(4, len(self.output.buffer)) 
        
        # Test for duplicates by id
        self.output.empty()
        self.create_distinct_sample()

        node.distinct_fields = ["id"]
        node.discard = True
        node.initialize()
        node.run()
        node.finalize()
        
        values = []
        for row in self.output.buffer:
            values.append(row[0])

        self.assertEqual(9, len(self.output.buffer)) 

        # Test for duplicates by id2 (should be none)
        self.output.empty()
        self.create_distinct_sample()

        node.distinct_fields = ["id2"]
        node.discard = True
        node.initialize()
        node.run()
        node.finalize()
        
        values = []
        for row in self.output.buffer:
            values.append( row[1])

        self.assertEqual(0, len(self.output.buffer)) 
        self.assertAllRows()

    def record_results(self):
        return [r for r in self.output.records()]

    def initialize_node(self, node):
        node.initialize()
        for output in node.outputs:
            output.fields = node.output_fields

    def test_aggregate_node(self):
        node = brewery.nodes.AggregateNode()
        self.setup_node(node)
        self.create_distinct_sample()

        node.key_fields = ["type"]
        node.add_measure("id", ["sum"])
        self.initialize_node(node)
        
        fields = node.output_fields.names()
        a = ['type', 'id_sum', 'id_min', 'id_max', 'id_average', 'record_count']
        
        self.assertEqual(a, fields)
        
        node.run()
        node.finalize()

        results = self.record_results()
        self.assertEqual(3, len(results)) 

        counts = []
        sums = []
        for result in results:
            sums.append(result["id_sum"])
            counts.append(result["record_count"])

        self.assertEqual([90, 450, 4500], sums)
        self.assertEqual([18,9,9], counts)
        
        # Test no keys - only counts
        node = brewery.nodes.AggregateNode()
        self.setup_node(node)
        self.output.empty()
        self.create_distinct_sample()

        # Setup node
        node.add_measure("id", ["sum"])
        self.initialize_node(node)

        fields = node.output_fields.names()
        a = ['id_sum', 'id_min', 'id_max', 'id_average', 'record_count']
        self.assertEqual(a, fields)

        node.run()
        node.finalize()

        # Collect results
        results = self.record_results()
        self.assertEqual(1, len(results)) 
        counts = []
        sums = []
        for result in results:
            sums.append(result["id_sum"])
            counts.append(result["record_count"])

        self.assertEqual([36], counts)
        self.assertEqual([5040], sums)
        self.assertAllRows()

    def assertAllRows(self, pipe = None):
        if not pipe:
            pipe = self.output
            
        for row in pipe.rows():
            if not (type(row) == list or type(row) == tuple):
                self.fail('pipe should contain only rows (lists/tuples), found: %s' % type(row))

    def test_function_select(self):
        def select(value):
            return value < 5
        def select_greater_than(value, threshold):
            return value > threshold
            
        node = brewery.nodes.FunctionSelectNode(function = select, fields = ["i"])

        self.setup_node(node)
        self.create_sample()

        self.initialize_node(node)

        # Passed fields should be equal
        ifields = self.input.fields
        ofields = node.output_fields
        self.assertEqual(ifields, ofields)

        node.run()
        node.finalize()

        self.assertEqual(5, len(self.output.buffer)) 

        self.output.empty()
        x = lambda value: value < 10
        node.function = x
        self.setup_node(node)
        self.create_sample()

        self.initialize_node(node)
        node.run()
        node.finalize()

        self.assertEqual(10, len(self.output.buffer)) 
        
        # Test kwargs
        self.output.empty()
        self.setup_node(node)
        self.create_sample()
        node.function = select_greater_than
        node.kwargs = {"threshold" : 7}
        node.discard = True
        
        self.initialize_node(node)
        node.run()
        node.finalize()

        self.assertEqual(8, len(self.output.buffer)) 

    def test_select(self):
        def select_dict(**record):
            return record["i"] < 5
        def select_local(i, **args):
            return i < 5

        node = brewery.nodes.SelectNode(condition = select_dict)

        self.setup_node(node)
        self.create_sample()
        self.initialize_node(node)
        node.run()
        node.finalize()
        self.assertEqual(5, len(self.output.buffer)) 

        self.output.empty()
        self.setup_node(node)
        self.create_sample()
        node.condition = select_local
        self.initialize_node(node)
        node.run()
        node.finalize()
        self.assertEqual(5, len(self.output.buffer)) 

        self.output.empty()
        self.setup_node(node)
        self.create_sample()
        node.condition = "i < 5"
        self.initialize_node(node)
        node.run()
        node.finalize()
        self.assertEqual(5, len(self.output.buffer)) 

    def test_derive(self):
        def derive_dict(**record):
            return record["i"] * 10
        def derive_local(i, **args):
            return i * 10

        node = brewery.nodes.DeriveNode(formula = derive_dict)

        self.setup_node(node)
        self.create_sample()
        self.initialize_node(node)
        node.run()
        node.finalize()

        val = sum([row[4] for row in self.output.buffer])
        self.assertEqual(49500, val)

        self.output.empty()
        self.setup_node(node)
        self.create_sample()
        node.formula = derive_local
        self.initialize_node(node)
        node.run()
        node.finalize()
        val = sum([row[4] for row in self.output.buffer])
        self.assertEqual(49500, val)

        self.output.empty()
        self.setup_node(node)
        self.create_sample()
        node.formula = "i * 10"
        self.initialize_node(node)
        node.run()
        node.finalize()
        val = sum([row[4] for row in self.output.buffer])
        self.assertEqual(49500, val)

    def test_set_select(self):
        node = brewery.nodes.SetSelectNode(field = "type", value_set = ["a"])

        self.setup_node(node)
        self.create_distinct_sample()

        self.initialize_node(node)

        node.run()
        node.finalize()

        self.assertEqual(18, len(self.output.buffer)) 

    def test_audit(self):
        node = brewery.nodes.AuditNode()
        self.setup_node(node)
        self.create_distinct_sample()

        self.initialize_node(node)

        self.assertEqual(6, len(node.output_fields)) 

        node.run()
        node.finalize()

        self.assertEqual(5, len(self.output.buffer)) 
        
    def test_strip(self):
        node = brewery.nodes.StringStripNode(fields = ["custom"])

        self.setup_node(node)
        self.create_sample(custom = "  foo  ")

        self.initialize_node(node)

        node.run()
        node.finalize()

        self.assertEqual("foo", self.output.buffer[0][3]) 

    def test_strip_auto(self):
        fields = brewery.FieldList([("str1", "string"), 
                                       ("x","unknown"), 
                                       ("str2","string"), 
                                       ("f", "unknown")])
        self.input.fields = fields
        for i in range(0, 5):
            self.input.put([" foo ", " bar ", " baz ", " moo "])

        node = brewery.nodes.StringStripNode()

        self.setup_node(node)

        self.initialize_node(node)

        node.run()
        node.finalize()

        row = self.output.buffer[0]
        self.assertEqual(["foo", " bar ", "baz", " moo "], row) 

    def test_consolidate_type(self):
        fields = brewery.FieldList([("s", "string"), 
                                       ("i","integer"), 
                                       ("f","float"), 
                                       ("u", "unknown")])
        self.input.fields = fields
        sample = [
                    ["  foo  ", 123, 123, None],
                    [123, "123", "123", None],
                    [123.0, " 123  ", "  123  ", None],
                    ["  foo  ", "1 2 3", "1 2 3  . 0", None],
                    ["  foo  ", "fail", "fail", None],
                    [None, None, None, None]
                ]

        for row in sample:
            self.input.put(row)


        node = brewery.nodes.CoalesceValueToTypeNode()

        self.setup_node(node)

        self.initialize_node(node)

        node.run()
        node.finalize()

        strings = []
        integers = []
        floats = []

        for row in self.output.buffer:
            strings.append(row[0])
            integers.append(row[1])
            floats.append(row[2])

        self.assertEqual(["foo", "123", "123.0", "foo", "foo", None], strings) 
        self.assertEqual([123, 123, 123, 123, None, None], integers) 
        self.assertEqual([123, 123, 123, 123, None, None], floats) 

    def test_merge(self):
        node = brewery.nodes.MergeNode()
        self.create_distinct_sample()

        input2 = brewery.streams.SimpleDataPipe()
        input2.fields = brewery.FieldList(["type2", "name"])
        input2.put(["a", "apple"])
        input2.put(["b", "bananna"])
        input2.put(["c", "curry"])
        input2.put(["d", "dynamite"])

        input_len = len(self.input.buffer)

        node.inputs = [self.input, input2]
        node.outputs = [self.output]

        node.joins = [
                    (1, "type", "type2")
                ]

        node.maps = {
                        0: brewery.FieldMap(drop = ["id2"]),
                        1: brewery.FieldMap(drop = ["type2"])
                    }
        self.initialize_node(node)

        self.assertEqual(5, len(node.output_fields)) 

        node.run()
        node.finalize()

        self.assertEqual(5, len(self.output.buffer[0]))
        self.assertEqual(input_len, len(self.output.buffer)) 
        
    def test_generator_function(self):
        node = brewery.nodes.GeneratorFunctionSourceNode()
        def generator(start=0, end=10):
            for i in range(start,end):
                yield [i]
                
        node.function = generator
        node.fields = brewery.metadata.FieldList(["i"])
        node.outputs = [self.output]

        self.initialize_node(node)
        node.run()
        node.finalize()
        self.assertEqual(10, len(self.output.buffer))

        self.output.buffer = []
        node.args = [0,5]
        self.initialize_node(node)
        node.run()
        node.finalize()
        self.assertEqual(5, len(self.output.buffer))
        a = [row[0] for row in self.output.buffer]
        self.assertEqual([0,1,2,3,4], a)


########NEW FILE########
__FILENAME__ = test_node_stream
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import brewery
from brewery import ds
import unittest
import logging
import time
import StringIO

from brewery.streams import *
from brewery.nodes import *
from brewery.common import *

logging.basicConfig(level=logging.WARN)

class StreamBuildingTestCase(unittest.TestCase):
    def setUp(self):
        # Stream we have here:
        #
        #  source ---+---> csv_target
        #            |
        #            +---> sample ----> html_target
        
        
        self.stream = Stream()
        self.node1 = Node()
        self.node1.description = "source"
        self.stream.add(self.node1, "source")

        self.node2 = Node()
        self.node2.description = "csv_target"
        self.stream.add(self.node2, "csv_target")

        self.node4 = Node()
        self.node4.description = "html_target"
        self.stream.add(self.node4, "html_target")

        self.node3 = Node()
        self.node3.description = "sample"
        self.stream.add(self.node3, "sample")

        self.stream.connect("source", "sample")
        self.stream.connect("source", "csv_target")
        self.stream.connect("sample", "html_target")
    
    def test_connections(self):
        self.assertEqual(4, len(self.stream.nodes))
        self.assertEqual(3, len(self.stream.connections))

        self.assertRaises(KeyError, self.stream.connect, "sample", "unknown")

        node = Node()
        self.assertRaises(KeyError, self.stream.add, node, "sample")
        
        self.stream.remove("sample")
        self.assertEqual(3, len(self.stream.nodes))
        self.assertEqual(1, len(self.stream.connections))

    def test_node_sort(self):
        # FIXME: This test is bugged
        sorted_nodes = self.stream.sorted_nodes()

        nodes = [self.node1, self.node3, self.node2, self.node4]

        self.assertEqual(self.node1, sorted_nodes[0])
        # self.assertEqual(self.node4, sorted_nodes[-1])
        
        self.stream.connect("html_target", "source")
        self.assertRaises(Exception, self.stream.sorted_nodes)
        
    def test_update(self):
        nodes = {
                "source": {"type": "row_list_source"},
                "target": {"type": "record_list_target"},
                "aggtarget": {"type": "record_list_target"},
                "sample": {"type": "sample"},
                "map":  {"type": "field_map"},
                "aggregate": {"type": "aggregate", "keys": ["str"] }
            }
        connections = [
                ("source", "sample"),
                ("sample", "map"),
                ("map", "target"),
                ("source", "aggregate"),
                ("aggregate", "aggtarget")
            ]
        
        stream = Stream()
        stream.update(nodes, connections)
        self.assertTrue(isinstance(stream.node("source"), Node))
        self.assertTrue(isinstance(stream.node("aggregate"), AggregateNode))

        node = stream.node("aggregate")
        self.assertEqual(["str"], node.keys)

class FailNode(Node):
    node_info = {
        "attributes": [ {"name":"message"} ]
    }
    
    def __init__(self):
        self.message = "This is fail node and it failed as expected"
    def run(self):
        logging.debug("intentionally failing a node")
        raise Exception(self.message)

class SlowSourceNode(Node):
    node_info = {}
    @property
    def output_fields(self):
        return brewery.FieldList(["i"])
        
    def run(self):
        for cycle in range(0,10):
            for i in range(0, 1000):
                self.put([i])
            time.sleep(0.05)
        
class StreamInitializationTestCase(unittest.TestCase):
    def setUp(self):
        # Stream we have here:
        #
        #  source ---+---> aggregate ----> aggtarget
        #            |
        #            +---> sample ----> map ----> target

        self.fields = brewery.FieldList(["a", "b", "c", "str"])
        self.src_list = [[1,2,3,"a"], [4,5,6,"b"], [7,8,9,"a"]]
        self.target_list = []
        self.aggtarget_list = []
        
        nodes = {
            "source": RowListSourceNode(self.src_list, self.fields),
            "target": RecordListTargetNode(self.target_list),
            "aggtarget": RecordListTargetNode(self.aggtarget_list),
            "sample": SampleNode("sample"),
            "map": FieldMapNode(drop_fields = ["c"]),
            "aggregate": AggregateNode(keys = ["str"])
        }
        
        connections = [
            ("source", "sample"),
            ("sample", "map"),
            ("map", "target"),
            ("source", "aggregate"),
            ("aggregate", "aggtarget")
        ]

        self.stream = Stream(nodes, connections)

    def test_initialization(self):
        self.stream._initialize()

        target = self.stream.node("map")
        names = target.output_fields.names()
        self.assertEqual(['a', 'b', 'str'], names)

        agg = self.stream.node("aggregate")
        names = agg.output_fields.names()
        self.assertEqual(['str', 'record_count'], names)

    def test_run(self):
        self.stream.run()

        target = self.stream.node("target")
        data = target.list
        expected = [{'a': 1, 'b': 2, 'str': 'a'}, 
                    {'a': 4, 'b': 5, 'str': 'b'}, 
                    {'a': 7, 'b': 8, 'str': 'a'}]
        self.assertEqual(expected, data)

        target = self.stream.node("aggtarget")
        data = target.list
        expected = [{'record_count': 2, 'str': 'a'}, {'record_count': 1, 'str': 'b'}]
        self.assertEqual(expected, data)
        
    def test_run_removed(self):
        self.stream.remove("aggregate")
        self.stream.remove("aggtarget")
        self.stream.run()
        
    def test_fail_run(self):
        nodes = {
            "source": RowListSourceNode(self.src_list, self.fields),
            "fail": FailNode(),
            "target": RecordListTargetNode(self.target_list)
        }
        connections = [
            ("source", "fail"),
            ("fail", "target")
        ]
        stream = Stream(nodes, connections)

        self.assertRaisesRegexp(StreamRuntimeError, "This is fail node", stream.run)
        
        nodes["fail"].message = u"Unicode message: čučoriedka ľúbivo ťukala"

        try:
            stream.run()
        except StreamRuntimeError, e:
            handle = StringIO.StringIO()
            # This should not raise an exception
            e.print_exception(handle)
            handle.close()
            
    def test_fail_with_slow_source(self):
        nodes = {
            "source": SlowSourceNode(),
            "fail": FailNode(),
            "target": RecordListTargetNode(self.target_list)
        }
        connections = [
            ("source", "fail"),
            ("fail", "target")
        ]
        
        stream = Stream(nodes, connections)

        self.assertRaises(StreamRuntimeError, stream.run)
    
class StreamConfigurationTestCase(unittest.TestCase):
    def test_create_node(self):
        self.assertEqual(RowListSourceNode, type(create_node("row_list_source")))
        self.assertEqual(AggregateNode, type(create_node("aggregate")))
        
    def test_configure(self):
        config = {
            "resource": "http://foo.com/bar.csv",
            "fields": ["field1", "field2", "field3"]
        }

        node = CSVSourceNode(self)
        node.configure(config)
        self.assertEqual(config["resource"], node.resource)
        self.assertEqual(config["fields"], node.fields)
        
########NEW FILE########
__FILENAME__ = test_pipes
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import threading
import time
import brewery.streams as streams

class PipeTestCase(unittest.TestCase):
    def setUp(self):
        self.processed_count = 0
        self.pipe = None
        self.sent_count = 0

    def send_sample(self, sample_size = 10):
        for i in range(0, sample_size):
            self.sent_count += 1
            self.pipe.put(i)

    def send_sample_limit_watch(self, sample_size = 10):
        for i in range(0, sample_size):
            if self.pipe.closed():
                break
            self.sent_count += 1
            time.sleep(0.01)
            self.pipe.put(i)

    def source_function(self):
        self.send_sample(1000)
        self.pipe.done_sending()

    def source_limit_function(self):
        self.send_sample_limit_watch(1000)
        self.pipe.done_sending()


    def target_function(self):
        self.processed_count = 0
        for value in self.pipe.rows():
            self.processed_count += 1

    def target_limit_function(self):
        self.processed_count = 0
        for value in self.pipe.rows():
            self.processed_count += 1
            if self.processed_count >= 20:
                break
        self.pipe.done_receiving()


    def test_put_get(self):
        self.pipe = streams.Pipe(buffer_size = 10)
        src = threading.Thread(target=self.source_function)
        target = threading.Thread(target=self.target_function)
        src.start()
        target.start()
        target.join()
        src.join()
        self.assertEqual(self.processed_count, 1000)

    def test_early_get_finish(self):
        self.pipe = streams.Pipe(buffer_size = 10)
        src = threading.Thread(target=self.source_function)
        target = threading.Thread(target=self.target_limit_function)
        src.start()
        target.start()
        target.join()
        src.join()
        self.assertEqual(self.processed_count, 20)
        # self.assertEqual(self.sent_count, 1000)

    def test_early_get_finish_watched(self):
        self.pipe = streams.Pipe(buffer_size = 10)
        src = threading.Thread(target=self.source_limit_function)
        target = threading.Thread(target=self.target_limit_function)
        src.start()
        target.start()
        target.join()
        self.assertEqual(self.processed_count, 20)
        self.assertLess(self.sent_count, 1000)

class Pipe2TestCase(unittest.TestCase):

    def setUp(self):
        self.pipe = streams.Pipe(100)

    def stest_put_one(self):
        self.pipe.put(1)
        self.pipe.done_sending()
        for row in self.pipe.rows():
            pass
        self.assertEqual(1, row)

    def test_pget_one(self):
        for i in range(1,100):
            self.pipe.put(i)
        self.pipe.done_sending()

        row = None

        for row in self.pipe.rows():
            break

        self.assertEqual(1, row)

    def producer(self, count = 100, stop = None):
        from random import random as _random
        from time import sleep as _sleep

        counter = 0
        while counter < count:
            self.pipe.put(counter)
            _sleep(_random() * 0.00001)
            counter += 1
        self.pipe.done_sending()

    def consumer(self, count = None):
        self.consumed_count = 0
        for row in self.pipe.rows():
            self.consumed_count += 1
            if count and self.consumed_count >= count:
                break
        self.pipe.done_receiving()

    def test_sending(self):
        producer = threading.Thread(target = self.producer)
        consumer = threading.Thread(target = self.consumer)
        producer.start()
        consumer.start()
        producer.join()
        consumer.join()
        self.assertEqual(100, self.consumed_count)

        self.pipe = streams.Pipe(100)
        producer = threading.Thread(target = self.producer, kwargs = {"count": 200})
        consumer = threading.Thread(target = self.consumer)
        producer.start()
        consumer.start()
        producer.join()
        consumer.join()
        self.assertEqual(200, self.consumed_count)

        self.pipe = streams.Pipe(100)
        producer = threading.Thread(target = self.producer, kwargs = {"count": 150})
        consumer = threading.Thread(target = self.consumer)
        producer.start()
        consumer.start()
        producer.join()
        consumer.join()
        self.assertEqual(150, self.consumed_count)

    def test_receiving(self):
        self.pipe = streams.Pipe(100)
        producer = threading.Thread(target = self.producer, kwargs = {"count": 15})
        consumer = threading.Thread(target = self.consumer, kwargs = {"count": 5})
        producer.start()
        consumer.start()
        producer.join()
        consumer.join()
        self.assertEqual(5, self.consumed_count)

########NEW FILE########
__FILENAME__ = test_sql_streams

import unittest
import threading
import time
from brewery import ds
import brewery.metadata

from sqlalchemy import Table, Column, Integer, String, Text
from sqlalchemy import create_engine, MetaData

class SQLStreamsTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        self.metadata = MetaData()
        
        self.fields = brewery.metadata.FieldList([
                            ("category", "string"),
                            ("category_label", "string"), 
                            ("subcategory", "string"), 
                            ("subcategory_label", "string"), 
                            ("line_item", "string"),
                            ("year", "integer"), 
                            ("amount", "integer")])
        self.example_row = ["cat", "Category", "scat", "Sub-category", "foo", 2012, 100]
        
    def test_table_fields(self):
        table = Table('users', self.metadata,
                    Column('id', Integer, primary_key=True),
                    Column('login', String(32)),
                    Column('full_name', String(255)),
                    Column('profile', Text)
                )
        
        self.metadata.create_all(self.engine)
        
        stream = ds.SQLDataSource(connection=self.engine, table=str(table))
        
        fields = stream.fields
        
        self.assertEqual(4, len(fields))
        
    def test_target_no_existing_table(self):
        stream = ds.SQLDataTarget(connection=self.engine, table="test")
        self.assertRaises(Exception, stream.initialize)

    def test_target_create_table(self):
        stream = ds.SQLDataTarget(connection=self.engine, table="test", create=True)
        # Should raise an exception, because no fields are specified
        self.assertRaises(Exception, stream.initialize)

        stream.fields = self.fields
        stream.initialize()

        cnames = [str(c) for c in stream.table.columns]
        fnames = ["test."+f.name for f in self.fields]
        self.assertEqual(fnames, cnames)

        stream.finalize()
        
    def test_target_replace_table(self):
        table = Table('test', self.metadata,
                    Column('id', Integer, primary_key=True),
                    Column('login', String(32)),
                    Column('full_name', String(255)),
                    Column('profile', Text)
                )
        
        self.metadata.create_all(self.engine)

        stream = ds.SQLDataTarget(connection=self.engine, table="test", 
                                    create=True, replace = False)
        
        stream.fields = self.fields
        self.assertRaises(Exception, stream.initialize)

        stream = ds.SQLDataTarget(connection=self.engine, table="test", 
                                    create=True, replace = True)
        stream.fields = self.fields
        stream.initialize()
        cnames = [str(c) for c in stream.table.columns]
        fnames = ["test."+f.name for f in self.fields]
        self.assertEqual(fnames, cnames)
        stream.finalize()
        
    def test_target_concrete_type_map(self):
        ctm = {"string": String(123)}
        stream = ds.SQLDataTarget(connection=self.engine, table="test",
                                  create=True,
                                  fields=self.fields,
                                  concrete_type_map=ctm)
        stream.initialize()

        c = stream.table.c["line_item"]

        self.assertEqual(123, c.type.length)
########NEW FILE########
__FILENAME__ = test_suite
#!/usr/bin/env python
# -*- coding: utf-8 -*-

########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Brewery handy utilities"""

import re
import logging

logger_name = 'brewery'
logger = None

def get_logger():
    """Get brewery default logger"""
    global logger
    
    if logger:
        return logger
    else:
        return create_logger()
        
def create_logger():
    """Create a default logger"""
    global logger
    logger = logging.getLogger(logger_name)

    formatter = logging.Formatter(fmt='%(asctime)s %(levelname)s %(message)s')
    
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger

class MissingPackage(object):
    """Bogus class to handle missing optional packages - packages that are not necessarily required
    for brewery, but are needed for certain features."""
    
    def __init__(self, package, feature = None, source = None, comment = None):
        self.package = package
        self.feature = feature
        self.source = source
        self.comment = comment

    def __getattr__(self, name):
        if self.feature:
            use = " to be able to use: %s" % self.feature
        else:
            use = ""
            
        if self.source:
            source = " from %s" % self.source
        else:
            source = ""
            
        if self.comment:
            comment = ". %s" % self.comment
        else:
            comment = ""

        raise Exception("Optional package '%s' is not installed. Please install the package%s%s%s" % 
                            (self.package, source, use, comment))

class IgnoringDictionary(dict):
    """Simple dictionary extension that will ignore any keys of which values are empty (None/False)"""
    def setnoempty(self, key, value):
        """Set value in a dictionary if value is not null"""
        if value:
            self[key] = value

def subclass_iterator(cls, _seen=None):
    """
    Generator over all subclasses of a given class, in depth first order.

    Source: http://code.activestate.com/recipes/576949-find-all-subclasses-of-a-given-class/
    """

    if not isinstance(cls, type):
        raise TypeError('_subclass_iterator must be called with '
                        'new-style classes, not %.100r' % cls)

    _seen = _seen or set()

    try:
        subs = cls.__subclasses__()
    except TypeError: # fails only when cls is type
        subs = cls.__subclasses__(cls)
    for sub in subs:
        if sub not in _seen:
            _seen.add(sub)
            yield sub
            for sub in subclass_iterator(sub, _seen):
                yield sub

def decamelize(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1 \2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1 \2', s1)

def to_identifier(name):
    return re.sub(r' ', r'_', name).lower()
    


########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Brewery documentation build configuration file, created by
# sphinx-quickstart on Wed Dec 15 11:57:31 2010.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('..'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc']
autoclass_content = 'init'
autodoc_default_flags = ['members']
# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Brewery'
copyright = u'2010-2012, Stefan Urbanek'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
# import brewery

from brewery import __version__ as brewery_version
version = brewery_version
# The full version, including alpha/beta/rc tags.
release = brewery_version

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'Brewerydoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Brewery.tex', u'Brewery Documentation',
   u'Stefan Urbanek', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'brewery', u'Brewery Documentation',
     [u'Stefan Urbanek'], 1)
]

########NEW FILE########
__FILENAME__ = create_node_reference
from __future__ import print_function
import inspect
import sys
import re
import string
from brewery.nodes import *
import brewery

# sys.path.insert(0, "..")

node_types = [
    {"type": "source", "label": "Sources"},
    {"type": "record", "label": "Record Operations"},
    {"type": "field", "label": "Field Operations"},
    {"type": "target", "label": "Targets"},
]

def decamelize(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1 \2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1 \2', s1)

def underscore(name):
    return re.sub(r' ', r'_', name).lower()

def node_documentation(class_name, node):
    doc = {}
    documentation = inspect.getdoc(node)

    if not documentation:
        documentation = "no documentation"
    elif re.search(r".. +abstract_node", documentation):
        return None
        
    doc["documentation"] = documentation
        
    doc["class_name"] = class_name
    name = decamelize(class_name)
    doc["name"] = name
    doc["identifier"] = node.identifier()

    try:
        info = get_node_info(node)
    except Exception as e:
        info = {}

    node_type = info.get("type")

    if not node_type:
        if issubclass(node, SourceNode):
            node_type = "source"
        elif issubclass(node, TargetNode):
            node_type = "target"
        else:
            node_type = "record"

    doc["type"] = node_type
        
    icon = info.get("icon")
    if not icon:
        icon = underscore(name)

    doc["icon"] = icon
    
    label = info.get("label")
    if not label:
        label = name

    doc["label"] = label
    
    description = info.get("description")
    if description:
        doc["description"] = description
    else:
        doc["description"] = "no description"
    
    doc["output"] = info.get("output")
    doc["attributes"] = info.get("attributes")
    
    return doc

def write_node_doc(doc, f):
        
    doc["underline"] = "-" * len(doc["label"])
    
    f.write(".. _%s:\n\n" % doc["class_name"])
    temp = "${label}\n${underline}\n\n"
    temp += ".. image:: nodes/${icon}.png\n" \
                "   :align: right\n\n" \
                "**Synopsis:** *${description}*\n\n" \
                "**Identifier:** ${identifier} (class: :class:`brewery.nodes.${class_name}`)\n\n" \
                "${documentation}\n\n"
    
    template = string.Template(temp)
    docstring = template.substitute(doc)
    f.write(docstring)
    
    if doc["attributes"]:
        # f.write("\nAttributes\n----------\n")
        f.write("\n.. list-table:: Attributes\n")
        f.write("   :header-rows: 1\n")
        f.write("   :widths: 40 80\n\n")
        f.write("   * - attribute\n")
        f.write("     - description\n")

        for attribute in doc["attributes"]:
            f.write("   * - %s\n" % attribute.get("name"))
            f.write("     - %s\n" % attribute.get("description"))
    
    f.write("\n")
        

def document_nodes_in_module(module):
    nodes_by_type = {}
    
    output = open("node_reference.rst", "w")

    output.write("Node Reference\n"\
                 "++++++++++++++\n\n")

    for name, member in inspect.getmembers(module):
        if inspect.isclass(member) and issubclass(member, Node):
            doc = node_documentation(name, member)
            if doc:
                node_type = doc["type"]
                if node_type in nodes_by_type:
                    nodes_by_type[node_type].append(doc)
                else:
                    nodes_by_type[node_type] = [doc]
                    
    for type_info in node_types:
        label = type_info["label"]
        output.write("%s\n" % label)
        output.write("%s\n\n" % ("=" * len(label)))
        
        node_type = type_info["type"]
        if not node_type in nodes_by_type:
            continue
            
        for node_doc in nodes_by_type[type_info["type"]]:
            write_node_doc(node_doc, output)
    output.close()


document_nodes_in_module(brewery.nodes)
########NEW FILE########
__FILENAME__ = aggregate_remote_csv
"""
Data Brewery Example

Aggregate a remote CSV file.
"""
import brewery

main = brewery.create_builder()

main.csv_source("https://raw.github.com/Stiivi/cubes/master/examples/hello_world/data.csv")
main.node.fields = brewery.FieldList([
                                "category_code",
                                "category",
                                "subcategory_code",
                                "subcategory", 
                                "line_item", 
                                "year", 
                                ["amount", "float"] 
                            ])
main.aggregate(keys=["year", "category"], measures=["amount"])
main.field_map(keep_fields=["year", "category", "amount_sum"])
main.pretty_printer()

main.stream.run()

########NEW FILE########
__FILENAME__ = audit_unknown_csv
"""
Brewery Example - basic audit of "unknown" CSV file.

Shows:

* record count
* null count and ratio
* number of distinct values

"""

import brewery

# Create stream builder
main = brewery.create_builder()

URL = "http://databank.worldbank.org/databank/download/WDR2011%20Dataset.csv"

main.csv_source(URL,encoding="latin-1") # <-- source node
main.audit(distinct_threshold=None)

# Uncomment following later:
# main.value_threshold( [["null_record_ratio", 0.4]] )
# main.set_select( "null_record_ratio_bin", ["high"])

main.pretty_printer() # <-- target node

# Run the stream
main.stream.run()

########NEW FILE########
__FILENAME__ = generator_function
"""
Data Brewery - http://databrewery.org

Example: How to use a generator function as a streaming data source.

"""


import brewery
import random

# Create a generator function
def generator(count=10, low=0, high=100):
    for i in range(0, count):
        yield [i, random.randint(low, high)]
        
# Create stream builder (HOM-based)
main = brewery.create_builder()

main.generator_function_source(generator, fields=brewery.FieldList(["i", "roll"]))

# Configure node with this:
#
# main.node.kwargs = {"count":100, "high":10}

# Uncomment this:
#
# fork = main.fork()
# fork.csv_target("random.csv")

main.formatted_printer()
main.stream.run()

########NEW FILE########
__FILENAME__ = merge_multiple_files
"""
Brewery Example - merge multiple CSV files

Input: Multiple CSV files with different fields, but with common subset of
       fields.

Output: Single CSV file with all fields from all files and with additional
        column with origin file name 

Run:

    $ python merge_multiple_files.py
    
Afterwards display the CSV file:

    $ cat merged.csv | brewery pipe pretty_printer
    
And see the field completeness (data quality dimension):

    $ cat merged.csv | brewery pipe audit pretty_printer

"""
import brewery
from brewery import ds
import sys

# List of sources - you might want to keep this list in a json file

sources = [
    {"file": "grants_2008.csv", 
     "fields": ["receiver", "amount", "date"]},

    {"file": "grants_2009.csv", 
     "fields": ["id", "receiver", "amount", "contract_number", "date"]},

    {"file": "grants_2010.csv", 
     "fields": ["receiver", "subject", "requested_amount", "amount", "date"]}
]

# Create list of all fields and add filename to store information
# about origin of data records
all_fields = brewery.FieldList(["file"])

# Go through source definitions and collect the fields
for source in sources:
    for field in source["fields"]:
        if field not in all_fields:
            all_fields.append(field)
            
            
# Create and initialize a data target

out = ds.CSVDataTarget("merged.csv")
out.fields = brewery.FieldList(all_fields)
out.initialize()

# Append all sources

for source in sources:
    path = source["file"]

    # Initialize data source: skip reading of headers - we are preparing them ourselves
    # use XLSDataSource for XLS files
    # We ignore the fields in the header, because we have set-up fields
    # previously. We need to skip the header row.
    
    src = ds.CSVDataSource(path,read_header=False,skip_rows=1)
    src.fields = ds.FieldList(source["fields"])
    src.initialize()

    for record in src.records():

        # Add file reference into ouput - to know where the row comes from
        record["file"] = path
        out.append(record)

    # Close the source stream
    src.finalize()

########NEW FILE########
