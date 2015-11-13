__FILENAME__ = document
# -*- coding: utf-8 -*-

import libreoffice

class document(object):
    def __init__(self, data):
        self.data = data

    def get_opendocument(self):
        raise NotImplemented()

class opendocument(document):
    def get_open_document(self):
        return self.data

    def set_dimensions(self, width, height):
        raise NotImplemented()

class binary_office_file(document)
    def get_opendocument(self):
        client = libreoffice.libreoffice_client()
        return client.convert_by_stream(self.data)



########NEW FILE########
__FILENAME__ = document_type
# -*- coding: utf-8 -*-
import zipfile
import StringIO

class types(object):
    oasis_open_document = "oasis_open_document (any version)"
    pdf = "portable document format (any version)"
    xml = "xml"
    html = "html"
    exception = "exception"
    unknown_type = "unknown file type"

def detect_document_type(data):
    if isinstance(data, Exception):
        return types.exception
    if isinstance(data, str):
        data = StringIO.StringIO(data)
    try:
        # 1. Sniff for OpenDocument
        magic_bytes_open_document = 'PK'
        data.seek(0)
        first_bytes = data.read(len(magic_bytes_open_document))
        if first_bytes.decode("utf-8") == magic_bytes_open_document: # 1.1 Ok it's a ZIP but...
            archive = zipfile.ZipFile(data)
            if 'mimetype' in archive.namelist() and archive.read('mimetype') == 'application/vnd.oasis.opendocument.text': # 1.2 ...if it doesn't have these files it's not an OpenDocument
                return types.oasis_open_document
        # 2. Sniff for PDF
        magic_bytes_pdf = '%PDF'
        data.seek(0)
        first_bytes = data.read(len(magic_bytes_pdf))
        if first_bytes.decode("utf-8") == magic_bytes_pdf:
            return types.pdf
        # 3. Sniff for HTML and XML
        data.seek(0)
        first_bytes = data.read(200).decode("utf-8") #200 bytes in, because sometimes there's a really long doctype
        #print first_bytes
        if first_bytes.count("<html") > 0:
            return types.html
        if first_bytes.count("<?xml") > 0:
            return types.xml
    except UnicodeDecodeError, exception:
        pass
    finally:
        data.seek(0)
    return types.unknown_type

########NEW FILE########
__FILENAME__ = docvert
# -*- coding: utf-8 -*-
import tempfile
import StringIO
import os.path
import document_type
import docvert_exception
import docvert_pipeline
import docvert_storage
import docvert_libreoffice
import docvert_xml
import opendocument
import urllib2

docvert_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
version = '5.1'
http_timeout = 10

class converter_type(object):
    python_streaming_to_libreoffice = "python streaming to libreoffice"

def process_conversion(files=None, urls=None, pipeline_id=None, pipeline_type="pipelines", auto_pipeline_id=None, storage_type_name=docvert_storage.storage_type.memory_based, converter=converter_type.python_streaming_to_libreoffice, suppress_errors=False):
    if files is None and urls is None:
        raise docvert_exception.needs_files_or_urls()
    if pipeline_id is None:
        raise docvert_exception.unrecognised_pipeline("Unknown pipeline '%s'" % pipeline_id)
    storage = docvert_storage.get_storage(storage_type_name)

    def _title(name, files, data):
        filename = os.path.basename(name).replace('\\','-').replace('/','-').replace(':','-')
        if len(filename) == 0:
            filename = "document.odt"
        if files.has_key(filename):
            if data and hasattr(files[filename], 'read') and files[filename].getvalue() == data:
                return filename
            unique = 1
            potential_filename = filename
            while files.has_key(potential_filename):
                unique += 1
                if filename.count("."):
                    potential_filename = filename.replace(".", "%i." % unique, 1)
                else:
                    potential_filename = filename + str(unique)
            filename = potential_filename
        return filename

    for filename, data in files.iteritems():
        storage.set_friendly_name(filename, filename)

    for url in urls:
        try:
            data = urllib2.urlopen(url, None, http_timeout).read()
            doc_type = document_type.detect_document_type(data)
            if doc_type == document_type.types.html:
                data = html_to_opendocument(data, url)
            filename = _title(url, files, data)
            storage.set_friendly_name(filename, "%s (%s)" % (filename, url))
            files[filename] = StringIO.StringIO(data)
        except IOError, e:
            filename = _title(url, files, None)
            storage.set_friendly_name(filename, "%s (%s)" % (filename, url))
            files[filename] = Exception("Download error from %s: %s" % (url, e))
    for filename, data in files.iteritems():
        if storage.default_document is None:
            storage.default_document = filename
        doc_type = document_type.detect_document_type(data)
        if doc_type == document_type.types.exception:
            storage.add("%s/index.txt" % filename, str(data))
        elif doc_type != document_type.types.oasis_open_document:
            try:
                data = generate_open_document(data, converter)
                doc_type = document_type.types.oasis_open_document
            except Exception, e:
                if not suppress_errors:
                    raise e
                storage.add("%s/index.txt" % filename, str(e))
        if doc_type == document_type.types.oasis_open_document:
            if pipeline_id == "open document": #reserved term, for when people want the Open Document file back directly. Don't bother loading pipeline.
                storage.add("%s/index.odt" % filename, data)
                thumbnail = opendocument.extract_thumbnail(data)
                if thumbnail:
                    storage.add("%s/thumbnail.png" % filename, thumbnail)
            else:
                document_xml = opendocument.extract_useful_open_document_files(data, storage, filename)
                storage.add("%s/opendocument.xml" % filename, document_xml)
                process_pipeline(document_xml, pipeline_id, pipeline_type, auto_pipeline_id, storage, filename)
                storage.remove("%s/opendocument.xml" % filename)
    return storage

def process_pipeline(initial_pipeline_value, pipeline_id, pipeline_type, auto_pipeline_id, storage, storage_prefix=None):
    pipeline_definition = docvert_pipeline.get_pipeline_definition(pipeline_type, pipeline_id, auto_pipeline_id)
    pipeline = docvert_pipeline.pipeline_processor(storage, pipeline_definition['stages'], pipeline_definition['pipeline_directory'], storage_prefix)
    return pipeline.start(initial_pipeline_value)

def generate_open_document(data, converter=converter_type.python_streaming_to_libreoffice):
    if converter == converter_type.python_streaming_to_libreoffice:
        return docvert_libreoffice.get_client().convert_by_stream(data, docvert_libreoffice.LIBREOFFICE_OPEN_DOCUMENT)
    raise docvert_exception.unrecognised_converter("Unknown converter '%s'" % converter)

def html_to_opendocument(html, url):
    from BeautifulSoup import BeautifulSoup
    import htmlentitydefs
    import re

    def to_ncr(match):
        text = match.group(0)
        entity_string = text[1:-1]
        entity = htmlentitydefs.entitydefs.get(entity_string)
        if entity:
            if len(entity) > 1:
                return entity
            try:
                return "&#%s;" % ord(entity)
            except ValueError:
                pass
            except TypeError, e:
                print "TypeError on '%s'?" % entity
                raise
        return text

    soup = BeautifulSoup(html, convertEntities=BeautifulSoup.XML_ENTITIES)
    to_extract = soup.findAll('script')
    for item in to_extract:
        item.extract()
    pretty_xml = soup.html.prettify()
    pretty_xml = re.sub("&?\w+;", to_ncr, pretty_xml)
    pretty_xml = re.sub('&(\w+);', '&amp;\\1', pretty_xml)
    pretty_xml = pretty_xml.replace("& ", "&amp; ")
    #display_lines(pretty_xml, 5, 15)
    xml = docvert_xml.get_document(pretty_xml)
    storage = docvert_storage.get_storage(docvert_storage.storage_type.memory_based)
    result = process_pipeline(xml, 'default', 'html_to_opendocument', None, storage)
    #print result
    #print storage
    return result

def display_lines(data, start_line, end_line):
    data = data.split("\n")
    segment = data[start_line:end_line]
    for line in segment:
        print "%s%s" % (start_line, line)
        start_line += 1
    

def get_all_pipelines(include_default_autopipeline = True):
    def _title(name):
        if name.endswith('.default'):
            name = name[0:-len('.default')]
        return name.replace('_',' ').replace('-',' ').title()

    pipeline_types_path = os.path.join(docvert_root, "pipelines")
    pipeline_types = dict()
    for pipeline_type in os.listdir(pipeline_types_path):
        pipeline_types[pipeline_type] = list()
        for pipeline_directory in os.listdir(os.path.join(pipeline_types_path, pipeline_type)):
            if pipeline_directory == 'ssc': #don't show this pipeline publicly. it's not important.
                pass
            elif include_default_autopipeline is False and pipeline_type == "auto_pipelines" and "nothing" in pipeline_directory.lower():
                pass #print "Skipping?"
            else:
                pipeline_types[pipeline_type].append(dict(id=pipeline_directory, name=_title(pipeline_directory)))
    return pipeline_types
    


########NEW FILE########
__FILENAME__ = docvert_exception
# -*- coding: utf-8 -*-

class docvert_exception(Exception):
    pass

class needs_files_or_urls(docvert_exception):
    pass

class unrecognised_pipeline(docvert_exception):
    pass

class unrecognised_auto_pipeline(docvert_exception):
    pass

class unrecognised_converter(docvert_exception):
    pass

class converter_unable_to_generate_open_document(docvert_exception):
    pass

class converter_unable_to_generate_pdf(docvert_exception):
    pass

class unknown_docvert_process(docvert_exception):
    pass

class unable_to_serialize_opendocument(docvert_exception):
    pass

class unrecognised_pipeline_item(docvert_exception):
    pass

class unrecognised_storage_type(docvert_exception):
    pass

class unknown_pipeline_node(docvert_exception):
    pass

class unknown_docvert_process(docvert_exception):
    pass

class tests_disabled(docvert_exception):
    pass

class unable_to_generate_xml_document(docvert_exception):
    pass

class invalid_test_root_node(docvert_exception):
    pass

class invalid_test_child_node(docvert_exception):
    pass

class debug_exception(docvert_exception):
    def __init__(self, message, data, content_type):
        self.data = data
        self.content_type = content_type
        super(docvert_exception, self).__init__(message)

class debug_xml_exception(debug_exception):
    pass

########NEW FILE########
__FILENAME__ = docvert_html
# Based on code from
# http://stackoverflow.com/questions/257409/download-image-file-from-the-html-page-source-using-python
# but multithreaded, etc.
from BeautifulSoup import BeautifulSoup as bs
import urlparse
from urllib2 import urlopen
from urllib import urlretrieve
import os
import sys

def get_urls(url, storage, storage_prefix):
    """Downloads all the images at 'url' to /test/"""
    soup = bs(urlopen(url))
    parsed = list(urlparse.urlparse(url))

    for image in soup.findAll("img"):
        print "Image: %(src)s" % image
        filename = image["src"].split("/")[-1]
        parsed[2] = image["src"]
        storage_path = os.path.join(storage_prefix, filename)
        
        url = urlparse.urlunparse(parsed)
        if url.lower().startswith("http"):
            url = image["src"]
        data = urllib2.urlopen(url)

########NEW FILE########
__FILENAME__ = docvert_libreoffice
# -*- coding: utf-8 -*-
from os.path import abspath
from os.path import isfile
from os.path import splitext
import sys
from StringIO import StringIO
import document_type
import docvert_exception
import socket

DEFAULT_LIBREOFFICE_PORT = 2002
LIBREOFFICE_OPEN_DOCUMENT = 'writer8'
LIBREOFFICE_PDF = 'writer_pdf_Export'

client = None

try:
    import uno
except ImportError:
    sys.path.append('/opt/libreoffice/program/')
    sys.path.append('/usr/lib/libreoffice/program/')
    sys.path.append('/usr/share/libreoffice/program/')
    sys.path.append('/usr/lib/openoffice.org/program/')
    sys.path.append('/usr/lib/openoffice.org2.0/program/')
    try:
        import uno
    except ImportError:
        python_version_info = sys.version_info
        python_version = "%s.%s.%s" % (python_version_info[0], python_version_info[1], python_version_info[2])
        alternate_python_version = "2.6"
        the_command_they_ran = " ".join(sys.argv)
        if python_version.startswith("2.6."):
              alternate_python_version = "2.7"
        sys.stderr.write("Error: Unable to find Python UNO libraries in %s.\nAre Python UNO libraries somewhere else?\nAlternatively, Docvert is currently running Python %s so perhaps Python %s has Python UNO libraries? If so, then try calling %s with that version of python (either as 'python%s %s' or change the first line of %s)\nExiting...\n" % (sys.path, python_version, alternate_python_version, the_command_they_ran, alternate_python_version, the_command_they_ran, the_command_they_ran))
        sys.exit(0)
        
import unohelper
from com.sun.star.beans import PropertyValue
from com.sun.star.task import ErrorCodeIOException
from com.sun.star.uno import Exception as UnoException
from com.sun.star.connection import NoConnectException
from com.sun.star.io import XOutputStream

class output_stream_wrapper(unohelper.Base, XOutputStream):
    def __init__(self):
        self.data = StringIO()
        self.position = 0

    def writeBytes(self, bytes):
        self.data.write(bytes.value)
        self.position += len(bytes.value)

    def close(self):
        self.data.close()

    def flush(self):
        pass


class libreoffice_client(object):
    def __init__(self, port=DEFAULT_LIBREOFFICE_PORT):
        self._local_context = uno.getComponentContext()
        self._service_manager = self._local_context.ServiceManager
        resolver = self._service_manager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", self._local_context)
        try:
            context = resolver.resolve("uno:socket,host=localhost,port=%s;urp;StarOffice.ComponentContext" % port)
        except NoConnectException, exception:
            raise Exception, "Failed to connect to LibreOffice on port %s. %s\nIf you don't have a server then read README for 'OPTIONAL LIBRARIES' to see how to set one up." % (port, exception)
        self._desktop = context.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", context)

    def convert_by_stream(self, data, format=LIBREOFFICE_OPEN_DOCUMENT):
        input_stream = self._service_manager.createInstanceWithContext("com.sun.star.io.SequenceInputStream", self._local_context)
        data.seek(0)
        input_stream.initialize((uno.ByteSequence(data.read()),)) 
        document = self._desktop.loadComponentFromURL('private:stream', "_blank", 0, self._to_properties(InputStream=input_stream,ReadOnly=True))
        if not document:
            raise Exception, "Error making document"
        try:
            document.refresh()
        except AttributeError:
            pass
        output_stream = output_stream_wrapper()
        try:
            document.storeToURL('private:stream', self._to_properties(OutputStream=output_stream, FilterName=format))
        except Exception, e: #ignore any error, verify the output before complaining
            pass
        finally:
            document.close(True)
        if format == LIBREOFFICE_OPEN_DOCUMENT or format == LIBREOFFICE_PDF:
            doc_type = document_type.detect_document_type(output_stream.data)
            output_stream.data.seek(0)
            if format == LIBREOFFICE_OPEN_DOCUMENT and doc_type != document_type.types.oasis_open_document:
                raise docvert_exception.converter_unable_to_generate_open_document("Unable to generate OpenDocument, was detected as %s.\n\nAre you sure you tried to convert an office document? If so then it\nmight be a bug, so please contact http://docvert.org and we'll see\nif we can fix it. Thanks!" % doc_type)
            elif format == LIBREOFFICE_PDF and doc_type != document_type.types.pdf:
                raise docvert_exception.converter_unable_to_generate_pdf("Unable to generate PDF, was detected as %s. First 4 bytes = %s" % (doc_type, output_stream.data.read(4)))
        return output_stream.data

    def _to_properties(self, **args):
        props = []
        for key in args:
            prop = PropertyValue()
            prop.Name = key
            prop.Value = args[key]
            props.append(prop)
        return tuple(props)

def checkLibreOfficeStatus():
    try:
        libreoffice_client()
        return True
    except Exception:
        return False

def get_client():
    global client
    if client is None:
        client = libreoffice_client()
    return client


########NEW FILE########
__FILENAME__ = docvert_pipeline
# -*- coding: utf-8 -*-
import os
import lxml.etree
import docvert_exception

docvert_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_pipeline_definition(pipeline_type, pipeline_id, auto_pipeline_id):
    pipeline = get_pipeline_xml(pipeline_type, pipeline_id, auto_pipeline_id)
    pipeline['stages'] = process_stage_level( pipeline['xml'].getroot() )
    return pipeline

def process_stage_level(nodes):
    stages = list()
    for child_node in nodes:
        if child_node.tag != "stage":
            continue
        child = dict()
        child['attributes'] = child_node.attrib
        child['children'] = None
        if(len(child_node) > 0):
            child['children'] = process_stage_level(child_node)
        stages.append(child)
    return stages

def get_pipeline_xml(pipeline_type, pipeline_id, auto_pipeline_id):
    path = os.path.join(docvert_root, "pipelines", pipeline_type, pipeline_id, "pipeline.xml")
    if not os.path.exists(path):
        raise docvert_exception.unrecognised_pipeline("Unknown pipeline_id '%s' (checked %s)" % (pipeline_id, path))
    autopipeline_path = None
    xml = lxml.etree.parse(path)
    if xml.getroot().tag == "autopipeline":
        if auto_pipeline_id is None:
            raise docvert_exception.unrecognised_auto_pipeline("Unknown auto pipeline '%s'" % auto_pipeline_id)
        autopipeline_path = os.path.join(docvert_root, "pipelines", "auto_pipelines", auto_pipeline_id, "pipeline.xml")
        if not os.path.exists(path):
            raise docvert_exception.unrecognised_auto_pipeline("Unknown auto pipeline '%s'" % auto_pipeline_id)
        custom_stages = "".join(map(lxml.etree.tostring,xml.getroot()))
        autopipeline = ""
        try:        
            autopipeline_handle = open(autopipeline_path)
        except IOError, e:
            autopipeline_path_with_default = os.path.join(docvert_root, "pipelines", "auto_pipelines", "%s.default" % auto_pipeline_id, "pipeline.xml")
            autopipeline_handle = open(autopipeline_path_with_default)
        autopipeline = autopipeline_handle.read().replace('{{custom-stages}}', custom_stages)
        xml = lxml.etree.fromstring(autopipeline)
        xml = xml.getroottree()
        #print autopipeline
    return dict(xml=xml, pipeline_directory=os.path.dirname(path), path=path, autopath=autopipeline_path)

class pipeline_processor(object):
    """ Processes through a list() of pipeline_item(s) """
    def __init__(self, storage, pipeline_items, pipeline_directory, pipeline_storage_prefix=None, depth=None):
        self.storage = storage
        self.pipeline_items = pipeline_items
        self.pipeline_directory = pipeline_directory
        self.pipeline_storage_prefix = pipeline_storage_prefix
        self.depth = list() if depth is None else depth

    def start(self, pipeline_value):
        for item in self.pipeline_items:
            process = item['attributes']['process']
            namespace = 'core.pipeline_type'
            full_pipeline_type = "%s.%s" % (namespace, process.lower())
            #try:
            stage_module = __import__(full_pipeline_type, {}, {}, [full_pipeline_type.rsplit(".", 1)[-1]])
            stage_class = getattr(stage_module, process)
            stage_instance = stage_class(self.storage, self.pipeline_directory, item['attributes'], self.pipeline_storage_prefix, item['children'], self.depth)
            pipeline_value = stage_instance.stage(pipeline_value)
            #except ImportError, exception:
            #    raise exception
            #    raise docvert_exception.unknown_docvert_process('Unknown pipeline process of "%s" (at %s)' % (process, "%s.%s" % (namespace, process.lower()) ))
        return pipeline_value


########NEW FILE########
__FILENAME__ = docvert_storage
# -*- coding: utf-8 -*-
import zipfile
import StringIO
import time
import docvert_exception
import core.docvert_xml
import core.docvert_exception


class storage_type(object):
    file_based = "file based storage"
    memory_based = "memory based storage"

def get_storage(name):
    if name == storage_type.file_based:
        return storage_file_based()
    elif name == storage_type.memory_based:
        return storage_memory_based()
    raise docvert_exception.unrecognised_storage_type("Unknown storage type '%s'" % name)

class storage(object):
    _docvert_xml_namespace = '{docvert:5}'
    
    def __init__(self, *args, **kargs):
        raise NotImplemented()

    def __setitem__(self, key, value):
        self.add(key, value)

    def keys(self):
        return self.storage.keys()

    def has_key(self, key):
        return self.storage.has_key(key)

    def __getitem__(self, key):
        return self.get(key)

    def set_friendly_name(self, filename, friendly_name):
        raise NotImplemented()

    def add_tests(self, tests):
        if not hasattr(self, 'tests'):
            self.tests = []
        if type(tests) == type([]): #assume correctly formatted list
            return self.tests.extend(tests)
        document = core.docvert_xml.get_document(tests)
        if hasattr(document, 'getroottree'):
            document = document.getroottree()
        root = document.getroot()
        if root.tag != "%sgroup" % self._docvert_xml_namespace:
            raise docvert_exception.invalid_test_root_node("Error parsing test results. Expected a root node of 'group' but got '%s'" % root.tag)
        for child in root:
            if child.tag == "%spass" % self._docvert_xml_namespace:
                self.tests.append( {"status":"pass", "message":str(child.text)} )
            elif child.tag == "%sfail" % self._docvert_xml_namespace:
                self.tests.append(dict(status="fail", message=str(child.text)))
            else:
                raise invalid_test_child_node("Error parsing test results. Unexpected child element of '%s' %s" % (child.tag, child))

    def get_tests(self):
        if hasattr(self, 'tests'):
            return self.tests
        return list()

    def get_zip_name(self):
        raise NotImplemented("No implemented, yet...")

class storage_file_based(storage):
    def __init__(self):
        self.working_directory = tempfile.mkdtemp()
        self.created_at = time.time()
        self.default_document = None

    def add(self, path, data):
        handler = open(os.path.join(self.working_directory, path), 'w')
        handler.write(data)
        handler.close()

    def set_friendly_name(self, filename, friendly_name):
        raise NotImplemented()

    def get(self, path):
        handler = open(os.path.join(self.working_directory, path), 'r')
        return handler.read()

    def _dispose(self):
        os.removedirs(self.working_directory)

    def get_zip_name(self):
        raise NotImplemented("No implemented, yet...")

    def to_zip(self):
        raise NotImplemented("Not implemented, yet...")

    def __str__(self):
        return '<file based storage at path "%s">' % self.working_directory


class storage_memory_based(storage):
    def __init__(self):
        self.storage = dict()
        self.created_at = time.time()
        self.default_document = None
        self.friendly_names = dict()

    def add(self, path, data):
        self.storage[path] = data

    def set_friendly_name(self, filename, friendly_name):
        self.friendly_names[filename] = friendly_name

    def get_friendly_name_if_available(self, filename):
        if self.friendly_names.has_key(filename):
            return self.friendly_names[filename]
        return filename

    def keys(self):
        return self.storage.keys()

    def get(self, path):
        return self.storage[path]

    def remove(self, path):
        del self.storage[path]

    def __delitem__(self, path):
        del self.storage[path]

    def to_zip(self):
        zipdata = StringIO.StringIO()
        archive = zipfile.ZipFile(zipdata, 'w')
        for key, value in self.storage.iteritems():
            data = value
            if hasattr(value, "read"):
                data = value.seek(0)
                data = value.read()
            if not key.startswith("__"): #if it's not internal data
                archive.writestr(key.replace("\\", "/"), data)
        archive.close()
        return zipdata

    def get_zip_name(self):
        friendly_names = ", ".join(self.friendly_names.keys())
        if friendly_names != "":
            friendly_names = "-%s" % friendly_names
        zip_name = "%s%s" % (time.strftime("docvert-%Y%m%d%H%M"), friendly_names)
        return zip_name.replace("\"","").replace("\n","").replace("\r","").replace("\\","")

    def _dispose(self):
        pass

    def __str__(self):
        return '<memory based storage with these keys "%s">' % self.storage.keys()

########NEW FILE########
__FILENAME__ = docvert_url
#based on https://github.com/shazow/workerpool/wiki/Mass-Downloader
import os
import urllib2
import lib.workerpool

class DownloadUrl(lib.workerpool.Job):
    def __init__(self, url, http_timeout=10):
        self.url = url
        self.http_timeout = http_timeout

    def run(self):
        try:
            self.response = urllib2.urlopen(self.url, None, self.http_timeout).read()
        except urllib2.URLError, e:
            self.response = e

def download(urls, workerpool_size=5):
    pool = lib.workerpool.WorkerPool(size=workerpool_size)
    for url in urls:
        pool.put(DownloadUrl(url))
    pool.shutdown()
    pool.wait()
    print dir(pool)

def demo():
    download([
        'https://github.com/shazow/workerpool/wiki/Mass-Downloader',
        'http://yahoo.com',
        'http://twitter.com/',
        'http://www.google.com/',
        'http://www.stuff.co.nz/',
        'http://trademe.co.nz/',
        'http://av.com/',
        'http://reddit.com/',
        'http://slashdot.org/'
    ])

########NEW FILE########
__FILENAME__ = docvert_xml
# -*- coding: utf-8 -*-
import docvert_exception
import lxml.etree
import xml.sax.saxutils

def transform(data, xslt, params=None):
    if params is None:
        params = dict()
    xslt_document = get_document(xslt)
    xslt_processor = lxml.etree.XSLT(xslt_document)
    xml_document = get_document(data)
    params = convert_dict_to_params(params)
    return xslt_processor(xml_document, **params)

def relaxng(data, relaxng_path):
    relaxng_document = get_document(relaxng_path)
    xml_document = get_document(data)
    relaxng_processor = lxml.etree.RelaxNG(relaxng_document)
    is_valid = relaxng_processor.validate(xml_document)
    return dict(valid=is_valid, log=relaxng_processor.error_log)

def escape_text(text):
    return xml.sax.saxutils.escape(text)

def get_document(data):
    if isinstance(data, lxml.etree._Element):
        return data
    elif isinstance(data, lxml.etree._XSLTResultTree):
        return data
    elif hasattr(data, 'read'):
        data.seek(0)
        return lxml.etree.XML(data.read())
    elif data[0:1] == "/" or data[0:1] == "\\": #path
        return lxml.etree.XML(file(data).read())
    elif data[0:1] == "<": #xml
        return lxml.etree.XML(data)
    else: #last ditch attempt...
        return lxml.etree.XML(str(data))
    raise docvert_exception.unable_to_generate_xml_document()

def convert_dict_to_params(params):
    for key in params.keys():
        params[key] = "'%s'" % params[key]
    return params

########NEW FILE########
__FILENAME__ = opendocument
# -*- coding: utf-8 -*-
import zipfile
import StringIO
import lxml.etree
import os.path

def extract_useful_open_document_files(data, storage=None, prefix=None):
    archive = zipfile.ZipFile(data)
    archive_files = archive.namelist()
    xml_string = extract_xml(archive, archive_files)
    if storage is None: #we can't extract binaries
        return xml_string
    return extract_useful_binaries(archive, archive_files, storage, prefix, xml_string)

def extract_thumbnail(data):
    archive = zipfile.ZipFile(data)
    thumbnail_path = u'Thumbnails/thumbnail.png'
    archive_files = archive.namelist()
    if thumbnail_path in archive_files:
        return archive.open(thumbnail_path).read()
    return None


def extract_useful_binaries(archive, archive_files, storage, prefix, xml_string):
    xlink_namespace = "http://www.w3.org/1999/xlink"
    xpath_template = '//*[@{%s}href="%s"]' % (xlink_namespace, '%s')
    document = lxml.etree.fromstring(xml_string.getvalue())
    extensions = [".wmf", ".emf", ".svg", ".png", ".gif", ".bmp", ".jpg", ".jpe", ".jpeg"]
    index = 0
    for archive_path in archive_files:
        path_minus_extension, extension = os.path.splitext(archive_path)
        if extension in extensions:
            storage_path = u"%s/file%i.%s" % (prefix, index, extension)
            try:
                storage_path = u"%s/%s" % (prefix, os.path.basename(archive_path))
            except UnicodeDecodeError, e:
                pass
            #step 1. extract binaries
            storage[storage_path] = archive.open(archive_path).read() 
            #step 2. update XML references
            path_relative_to_xml = os.path.basename(archive_path)
            xpath = lxml.etree.ETXPath(xpath_template % archive_path)
            for match in xpath(document):
                match.attrib['{%s}href' % xlink_namespace] = storage_path
            index += 1
    return StringIO.StringIO(lxml.etree.tostring(document))

def extract_xml(archive, archive_files):
    xml_files_to_extract = ["content.xml", "meta.xml", "settings.xml", "styles.xml"]
    xml_string = StringIO.StringIO()
    xml_string.write('<docvert:root xmlns:docvert="docvert:5">')
    for xml_file_to_extract in xml_files_to_extract:
        if xml_file_to_extract in archive_files:
            xml_string.write('<docvert:external-file xmlns:docvert="docvert:5" docvert:name="%s">' % xml_file_to_extract)
            document = lxml.etree.fromstring(archive.open(xml_file_to_extract).read()) #parsing as XML to remove any doctype
            xml_string.write(lxml.etree.tostring(document))
            xml_string.write('</docvert:external-file>')
    xml_string.write('</docvert:root>')
    return xml_string
    
def generate_single_image_document(image_data, width, height):
    #print "Width/height: %s/%s" % (width,height) 
    #TODO: make document dimensions match image width/height
    content_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <office:document-content office:version="1.2" xmlns:chart="urn:oasis:names:tc:opendocument:xmlns:chart:1.0" xmlns:css3t="http://www.w3.org/TR/css3-text/" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dom="http://www.w3.org/2001/xml-events" xmlns:dr3d="urn:oasis:names:tc:opendocument:xmlns:dr3d:1.0" xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0" xmlns:field="urn:openoffice:names:experimental:ooo-ms-interop:xmlns:field:1.0" xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" xmlns:form="urn:oasis:names:tc:opendocument:xmlns:form:1.0" xmlns:formx="urn:openoffice:names:experimental:ooxml-odf-interop:xmlns:form:1.0" xmlns:math="http://www.w3.org/1998/Math/MathML" xmlns:meta="urn:oasis:names:tc:opendocument:xmlns:meta:1.0" xmlns:number="urn:oasis:names:tc:opendocument:xmlns:datastyle:1.0" xmlns:of="urn:oasis:names:tc:opendocument:xmlns:of:1.2" xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:officeooo="http://openoffice.org/2009/office" xmlns:ooo="http://openoffice.org/2004/office" xmlns:oooc="http://openoffice.org/2004/calc" xmlns:ooow="http://openoffice.org/2004/writer" xmlns:rpt="http://openoffice.org/2005/report" xmlns:script="urn:oasis:names:tc:opendocument:xmlns:script:1.0" xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0" xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" xmlns:tableooo="http://openoffice.org/2009/table" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" xmlns:xforms="http://www.w3.org/2002/xforms" xmlns:xhtml="http://www.w3.org/1999/xhtml" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
          <office:body>
            <office:text>
              %s
            </office:text>
          </office:body>
        </office:document-content>"""
    mimetype = 'application/vnd.oasis.opendocument.text'
    image_xml = """<text:p text:style-name="Standard">
        <draw:frame draw:name="graphics1" draw:style-name="fr1" svg:width="%s" svg:height="%s" text:anchor-type="char">
          <draw:image xlink:actuate="onLoad" xlink:href="%s" xlink:show="embed" xlink:type="simple"/>
        </draw:frame></text:p>"""
    image_path = "Pictures/image.png"
    manifest = """<?xml version="1.0" encoding="UTF-8"?>
        <manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0">
            <manifest:file-entry manifest:media-type="application/vnd.oasis.opendocument.text" manifest:version="1.2" manifest:full-path="/"/>
            <manifest:file-entry manifest:media-type="image/png" manifest:full-path="%s"/>
            <manifest:file-entry manifest:media-type="" manifest:full-path="Pictures/"/>
            <manifest:file-entry manifest:media-type="text/xml" manifest:full-path="content.xml"/>
            <manifest:file-entry manifest:media-type="text/xml" manifest:full-path="styles.xml"/>
        </manifest:manifest>"""
    styles_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <office:document-styles grddl:transformation="http://docs.oasis-open.org/office/1.2/xslt/odf2rdf.xsl" office:version="1.2" xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" xmlns:grddl="http://www.w3.org/2003/g/data-view#" xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0">
        <office:automatic-styles>
            <style:page-layout style:name="Mpm1">
              <style:page-layout-properties fo:background-color="#ffffff" fo:margin-bottom="0cm" fo:margin-left="0cm" fo:margin-right="0cm" fo:margin-top="0cm" fo:page-width="%s" fo:page-height="%s" style:footnote-max-height="0cm" style:layout-grid-base-height="0.635cm" style:layout-grid-base-width="0.369cm" style:layout-grid-color="#c0c0c0" style:layout-grid-display="false" style:layout-grid-lines="36" style:layout-grid-mode="none" style:layout-grid-print="false" style:layout-grid-ruby-below="false" style:layout-grid-ruby-height="0cm" style:layout-grid-snap-to-characters="true" style:num-format="1" style:print-orientation="portrait" style:writing-mode="lr-tb">
              </style:page-layout-properties>
            </style:page-layout>
          </office:automatic-styles>
          <office:master-styles>
            <style:master-page style:name="Standard" style:page-layout-name="Mpm1"/>
            <style:master-page style:display-name="First Page" style:name="First_20_Page" style:next-style-name="Standard" style:page-layout-name="Mpm1"/>
          </office:master-styles>
        </office:document-styles>"""
    image_xml = image_xml % (width, height, image_path) #filename doesn't matter
    zipio = StringIO.StringIO()
    archive = zipfile.ZipFile(zipio, 'w')
    archive.writestr('mimetype', mimetype)
    archive.writestr('content.xml', content_xml % image_xml)
    archive.writestr('styles.xml', styles_xml % (width, height))
    archive.writestr('META-INF/manifest.xml', manifest % image_path)
    archive.writestr(image_path, image_data)
    archive.close()
    zipio.seek(0)
    #pointer = file('/tmp/doc.odt', 'w')
    #pointer.write(zipio.read())
    #pointer.close()
    return zipio


########NEW FILE########
__FILENAME__ = compare
# -*- coding: utf-8 -*-
import os
import os.path
import lxml.etree
import pipeline_item
import core.docvert
import core.docvert_exception
import core.docvert_xml
import core.document_type
import core.opendocument

class Compare(pipeline_item.pipeline_stage):
    def stage(self, pipeline_value):
        if pipeline_value is None:
            raise pipeline_value_not_empty("A process type of Compare needs pipeline_value to compare with.")
        if not self.attributes.has_key('withFile'):
            raise needs_with_file_attribute("A process type of Compare needs a withFile attribute containing a filename/path.")
        compare_path = self.resolve_pipeline_resource(self.attributes['withFile'])
        if not os.path.exists(compare_path):
            raise generation_file_not_found("A process type of Compare couldn't find a file at %s" % compare_path)
        compare_data = file(compare_path)
        compare_xml = None
        doc_type = core.document_type.detect_document_type(compare_data)
        if doc_type == core.document_type.types.oasis_open_document:
            compare_xml = core.opendocument.extract_useful_open_document_files(compare_data)
        elif doc_type == core.document_type.types.xml:
            compare_xml = compare_data
        else:
            raise cannot_compare_with_non_xml_or_non_opendocument("Cannot compare withFile=%s with detected type of %s" % (compare_path, doc_type))
        turn_document_into_test_filename = "internal://turn-document-into-test.xsl"
        xslt_path = self.resolve_pipeline_resource(turn_document_into_test_filename)
        test_xslt = core.docvert_xml.transform(compare_data, xslt_path)
        storage_filename = "comparision-to-%s.xhtml" % self.attributes['withFile']
        storage_path = "%s/%s" % (self.pipeline_storage_prefix, storage_filename)
        if self.pipeline_storage_prefix is None:
            storage_path = storage_filename
        print storage_path
        storage[storage_path] = core.docvert_xml.transform(pipeline_value, test_as_xslt)
        return pipeline_value

class pipeline_value_not_empty(core.docvert_exception.docvert_exception):
    pass

class needs_with_file_attribute(core.docvert_exception.docvert_exception):
    pass

class generation_file_not_found(core.docvert_exception.docvert_exception):
    pass

class cannot_compare_with_non_xml_or_non_opendocument(core.docvert_exception.docvert_exception):
    pass


########NEW FILE########
__FILENAME__ = convertimages
# -*- coding: utf-8 -*-
import os
import os.path
import tempfile
import StringIO
import commands
import Image # Python PIL
import pipeline_item
import core.docvert_xml
import core.opendocument
import core.docvert_libreoffice
import lxml.etree

class ConvertImages(pipeline_item.pipeline_stage):
    synonym_formats = dict( #Not just synonyms, but types of files that are converted using the same code (eg, emf=wmf)
        emf='wmf',wmf='wmf',#horrible old vector
        pdf='pdf', ps='pdf', #moderately horrible vector
        svg='svg',#vector
        ani='png',apng='png',art='png',bef='png',bmf='png',bmp='png',cgm='png',cin='png',cpc='png',dpx='png',ecw='png',exr='png',fits='png',flic='png',fpx='png',gif='png',icer='png',ics='png',iff='png',iges='png',ilbm='png',jbig='png',jbig2='png',jng='png',jpe='png',jpg='png',jpeg='png',jp2='png',mng='png',miff='png',pbm='png',pcx='png',pgf='png',pgm='png',png='png',ppm='png',psp='png',raw='png',rad='png',rgbe='png',sgi='png',tga='png',tif='png',tiff='png',webp='png',xar='png',xbm='png',xcf='png',xpm='png' #bitmap
    )
    
    def stage(self, pipeline_value):
        self.intermediate_files = list()
        intermediate_file_extensions_to_retain = list()
        #TODO add format sniffing code
        conversions = dict()
        if not self.storage.has_key('__convertimages'):
            self.storage['__convertimages'] = dict()
        # 1. Parse conversion requests
        formats = ("%s," % self.attributes["formats"]).split(",")
        for format in formats:
            conversion = format.strip(" ._-\n\r").lower()
            if len(conversion) == 0: continue
            from_format, to_format = conversion.split("2")
            if self.synonym_formats.has_key(from_format):
                from_format = self.synonym_formats[from_format]
            if not conversions.has_key(from_format):
                conversions[from_format] = list()
            intermediate_file_extensions_to_retain.append(str(to_format))
            conversions[str(from_format)].append(str(to_format))

        # 2. Convert images
        # <stage process="ConvertImages" formats="wmf2png, wmf2svg, bmp2png" deleteOriginals="true" autoCrop="false" autoCropThreshold="20"/>
        storage_paths = self.storage.keys()
        for storage_path in storage_paths:
            if self.pipeline_storage_prefix and not storage_path.startswith(self.pipeline_storage_prefix):
                continue
            path, extension = os.path.splitext(storage_path)
            extension_minus_dot = str(extension[1:])
            for from_format, to_formats in conversions.iteritems():
                from_format_method = "convert_%s" % extension_minus_dot
                if extension_minus_dot == from_format and hasattr(self, from_format_method):
                    for to_format in to_formats:
                        pipeline_value = getattr(self, from_format_method)(storage_path, to_format, pipeline_value)

        # 3. Delete original images
        if self.attributes.has_key("deleteOriginals") and not self.attributes["deleteOriginals"].strip().lower() in ['false','f','n','0','']:
            for storage_path in storage_paths:
                if not storage_path.startswith(self.pipeline_storage_prefix):
                    continue
                extension = os.path.splitext(storage_path)[1][1:]
                #if conversions.has_key(extension):
                #    self.storage.remove(storage_path)

        for intermediate_file in self.intermediate_files:
            path, extension = os.path.splitext(intermediate_file)
            extension_minus_dot = str(extension[1:])
            if not extension_minus_dot in intermediate_file_extensions_to_retain:
                try:
                    del self.storage[intermediate_file]
                except KeyError, e:
                    pass

        return pipeline_value

    def convert_wmf(self, storage_path, to_format, pipeline_value, width=None, height=None):
        # We can't reliably parse wmf/emf here so use LibreOffice to generate PDF no matter the to_format
        path, extension = os.path.splitext(storage_path)
        pdf_path = "%s.pdf" % path
        if not self.storage.has_key(pdf_path):
            if width is None or height is None:
                width, height, pipeline_value = self.get_dimensions_from_xml(storage_path, pipeline_value, to_format)
            #print "Generate document for %s because %s doesn't exist\n%s\n\n" % (storage_path, pdf_path, self.storage.keys())
            opendocument = core.opendocument.generate_single_image_document(self.storage[storage_path], width, height)
            self.storage[pdf_path] = core.docvert_libreoffice.get_client().convert_by_stream(opendocument, core.docvert_libreoffice.LIBREOFFICE_PDF)
        else:
            #print "Cache hit! No need to generate %s" % pdf_path
            pass
        if to_format == 'pdf':
            return pipeline_value
        self.intermediate_files.append(pdf_path)
        from_format = 'pdf'
        if self.synonym_formats.has_key(from_format):
            from_format = self.synonym_formats[from_format]
        from_format_method = "convert_%s" % from_format
        return getattr(self, from_format_method)(pdf_path, to_format, pipeline_value, width, height)

    def convert_pdf(self, storage_path, to_format, pipeline_value, width=None, height=None):
        path, extension = os.path.splitext(storage_path)
        svg_path = "%s.svg" % path
        if not self.storage.has_key(svg_path):
            if width is None or height is None:
                width, height, pipeline_value = self.get_dimensions_from_xml(storage_path, pipeline_value)
            from_format = str(extension[1:])
            synonym_from_format = from_format
            if self.synonym_formats.has_key(synonym_from_format):
                synonym_from_format = self.synonym_formats[synonym_from_format]
            self.storage[svg_path] = self.run_conversion_command_with_temporary_files(storage_path, "pdf2svg %s %s")
        else:
            #print "Cache hit! No need to generate %s" % svg_path
            pass
        if to_format == 'svg':
            return pipeline_value
        self.intermediate_files.append(svg_path)
        from_format = 'svg'
        if self.synonym_formats.has_key(from_format):
            from_format = self.synonym_formats[from_format]
        from_format_method = "convert_%s" % from_format
        return getattr(self, from_format_method)(svg_path, to_format, pipeline_value, width, height)

    def convert_svg(self, storage_path, to_format, pipeline_value, width=None, height=None):
        path, extension = os.path.splitext(storage_path)
        png_path = "%s.png" % path
        if not self.storage.has_key(png_path):
            if width is None or height is None:
                width, height, pipeline_value = self.get_dimensions_from_xml(storage_path, pipeline_value)
            from_format = str(extension[1:])
            synonym_from_format = from_format
            if self.synonym_formats.has_key(synonym_from_format):
                synonym_from_format = self.synonym_formats[synonym_from_format]
            self.storage[png_path] = self.run_conversion_command_with_temporary_files(storage_path, "rsvg %s %s")
        else:
            #print "Cache hit! No need to generate %s" % png_path
            pass
        if to_format == 'png':
            return pipeline_value
        self.intermediate_files.append(png_path)
        from_format = 'svg'
        if self.synonym_formats.has_key(from_format):
            from_format = self.synonym_formats[from_format]
        from_format_method = "convert_%s" % from_format
        return getattr(self, from_format_method)(png_path, to_format, pipeline_value, width, height)
        
    def convert_png(self, storage_path, to_format, pipeline_value, width=None, height=None):
        #im = Image.open('icon.gif')
        #transparency = im.info['transparency'] 
        #im .save('icon.png', transparency=transparency)
        #print dir(Image)
        return pipeline_value

    def get_dimensions_from_xml(self, storage_path, pipeline_value, change_image_path_extension_to=None):
        def get_value(data):
            if hasattr(data, 'read'):
                data.seek(0)
                return data.read()
            return data
        path, extension = os.path.splitext(storage_path)
        if self.storage['__convertimages'].has_key(path): #intentionally extensionless because all formats of this single image are considered to have the same dimensions
            return (self.storage['__convertimages'][path]['width'], self.storage['__convertimages'][path]['height'], pipeline_value)

        default_dimensions = ('10cm', '10cm') #we had to choose something
        #if self.pipeline_storage_prefix:
        #    storage_path = storage_path[len(self.pipeline_storage_prefix) + 1:]
        xml = self.get_document(pipeline_value)
        namespaces = {'xlink':'http://www.w3.org/1999/xlink'}
        xpath = '//*[@xlink:href="%s"]/parent::*' % storage_path
        image_nodes = xml.xpath(xpath, namespaces=namespaces)
        if len(image_nodes) == 0: #can't do anything, might have been a thumbnail or unlinked image, but either way return 10cm square
            #images = xml.xpath('//*[@xlink:href]', namespaces=namespaces)
            #print "Could not find image node with %s. Document contains: \n%s\n%s. Prefix was %s" % (xpath, images[0], images[0].attrib, self.pipeline_storage_prefix)
            return default_dimensions[0], default_dimensions[1], pipeline_value
        #print "FOUND IMAGE!"
        image_node = image_nodes[0] #first image will be do fine. It's possible to have multiple tags with different width/height pointing at the same image but for now we'll discount that possibility
        oasis_opendocument_svg_namespace = 'urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0'
        width_attribute = "{%s}%s" % (oasis_opendocument_svg_namespace, 'width')
        height_attribute = "{%s}%s" % (oasis_opendocument_svg_namespace, 'height')
        #print "about to read width/height"
        try:
            width = image_node.attrib[width_attribute]
            height = image_node.attrib[height_attribute]
            #print "success... and %s" % change_image_path_extension_to
            if change_image_path_extension_to:
                path, extension = os.path.splitext(storage_path)
                xlink_href_attribute = "{%s}%s" % (namespaces['xlink'], 'href')
                change_image_path = '%s.%s' % (path, change_image_path_extension_to)
                #print "New image path is %s" % change_image_path
                image_nodes = image_node.xpath('*[@xlink:href="%s"]' % storage_path, namespaces=namespaces)
                for image_node in image_nodes:
                    #print "Value was %s" % image_node.attrib[xlink_href_attribute]
                    image_node.attrib[xlink_href_attribute] = change_image_path
                    #print "Value is %s" % image_node.attrib[xlink_href_attribute]
            self.storage['__convertimages'][path] = dict(width=width, height=height) #intentionally extensionless because all formats of this single image are considered to have the same dimensions
            return (width, height, lxml.etree.tostring(xml))
        except KeyError, e:
            pass
        return default_dimensions[0], default_dimensions[1], pipeline_value

    def get_document(self, pipeline_value):
        xml = core.docvert_xml.get_document(pipeline_value)
        if hasattr(xml, "getroottree"):
            xml = xml.getroottree()
        elif hasattr(xml, 'getroot'):
            xml = xml.getroot()
        return xml

    def run_conversion_command_with_temporary_files(self, from_storage_path, command_template):
        def get_value(data):
            if hasattr(data, 'read'):
                data.seek(0)
                return data.read()
            return data
        temporary_from_path = None
        temporary_to_path = None
        try:
            os_handle, temporary_from_path = tempfile.mkstemp()
            temporary_from_file = open(temporary_from_path, 'w')
            temporary_from_file.write(get_value(self.storage[from_storage_path]))
            temporary_from_file.flush()
            temporary_from_file.close()
            os_handle, temporary_to_path = tempfile.mkstemp()
            command = command_template % (temporary_from_path, temporary_to_path)
            std_response = commands.getstatusoutput(command)
            if os.path.getsize(temporary_to_path) == 0:
                raise Exception('Error in convertimages.py: No output data created. Command was "%s" which returned "%s"' % (command_template, std_response))
            temporary_to = open(temporary_to_path, 'r')
            to_data = temporary_to.read()
            temporary_to.close()
            return to_data
        finally:
            if temporary_from_path: os.remove(temporary_from_path)
            if temporary_to_path: os.remove(temporary_to_path)


"""
#NOTE: Poppler doesn't work on my [Matthew Holloway's] Ubuntu 10.10 machine. It seg faults so that's why I'm shelling out
#import cairo
#import poppler
os_handle, temporary_file_path = tempfile.mkstemp()
temporary_file = open(temporary_file_path, 'w')
temporary_file.write(get_value(self.storage[storage_path]))
temporary_file.flush()
print temporary_file_path
pdf = poppler.document_new_from_file(
    "file://%s" % temporary_file_path,
    password=None)
first_page = pdf.get_page(0)
surface = cairo.PDFSurface(surface_storage, width_float, height_float)
cairo_context = cairo.Context(surface)

first_page.render(cairo_context)
surface.write_to_png("/tmp/page0.png")
print dir(first_page)
temporary_file.close()
"""


########NEW FILE########
__FILENAME__ = debug
# -*- coding: utf-8 -*-
import lxml.etree
import pipeline_item
import core.docvert_exception

class Debug(pipeline_item.pipeline_stage):
    def stage(self, pipeline_value):
        def get_value(data):
            if hasattr(data, "read"):
                data.seek(0)
                return data.read()
            return data
        if isinstance(pipeline_value, lxml.etree._Element) or isinstance(pipeline_value, lxml.etree._XSLTResultTree):
            pipeline_value = lxml.etree.tostring(pipeline_value)
        elif hasattr(pipeline_value, 'read'):
            pipeline_value.seek(0)
            pipeline_value = pipeline_value.read()
        if get_value(pipeline_value) is None:
            raise core.docvert_exception.debug_exception("Current contents of pipeline", "Debug: pipeline_value is %s" % get_value(pipeline_value), "text/plain; charset=UTF-8")
        try:
            document = lxml.etree.fromstring(get_value(pipeline_value))
        except lxml.etree.XMLSyntaxError, exception:
            raise core.docvert_exception.debug_exception("Current contents of pipeline", "Error parsing as XML, here it is as plain text: %s\n%s" % (exception, pipeline_value), "text/plain; charset=UTF-8")
        help_text = "In debug mode we want to display an XML tree but if the root node is <html> or there's an HTML namespace then popular browsers will\nrender it as HTML so these have been changed. See core/pipeline_type/debug.py for the details."
        unit_tests = self.get_tests()
        if unit_tests:
            #help_text += "\n\nUnit tests so far in the pipeline:"
            help_text += "\n\nFailed unit tests so far in the pipeline:"
            for value in self.get_tests():
                #help_text += "\n\t%s:%s" % (value["status"], value["message"])
                if value["status"] == "fail":
                    help_text += "\n\tFail: %s" % (value["message"])

        content_type = 'text/xml'
        if self.attributes.has_key("contentType"):
            content_type = self.attributes['contentType']
        if self.attributes.has_key("zip"):
            content_type = 'application/zip'
            pipeline_value = self.storage.to_zip().getvalue()
        if content_type == 'text/xml':
            help_text += "\n\nConversion files:\n\t" + "\n\t".join(self.storage.keys())
            if hasattr(document, 'getroottree'):
                document = document.getroottree()
            if document.getroot().tag == "{http://www.w3.org/1999/xhtml}html":
                pipeline_value = "<root><!-- %s -->%s</root>" % (help_text, lxml.etree.tostring(document.getroot())) 
            else:
                pipeline_value = "<!-- %s -->%s" % (help_text, lxml.etree.tostring(document.getroot())) 
            pipeline_value = pipeline_value.replace('"http://www.w3.org/1999/xhtml"', '"XHTML_NAMESPACE_REPLACED_BY_DOCVERT_DURING_DEBUG_MODE"')
            xml_declaration = '<?xml version="1.0" ?>'
            if pipeline_value[0:5] != xml_declaration[0:5]:
                pipeline_value = xml_declaration + "\n" + pipeline_value
        raise core.docvert_exception.debug_xml_exception("Current contents of pipeline", pipeline_value, content_type)

########NEW FILE########
__FILENAME__ = docbooktoxhtml
# -*- coding: utf-8 -*-
import pipeline_item
import core.docvert_xml

class DocBookToXHTML(pipeline_item.pipeline_stage):

    def stage(self, pipeline_value):
        docbook_to_html_path = self.resolve_pipeline_resource('internal://docbook-to-html.xsl')
        return core.docvert_xml.transform(pipeline_value, docbook_to_html_path)




########NEW FILE########
__FILENAME__ = generate
# -*- coding: utf-8 -*-
import os
import os.path
import lxml.etree
import StringIO
import pipeline_item
import core.docvert
import core.opendocument
import core.document_type
import core.docvert_exception

class Generate(pipeline_item.pipeline_stage):
    def stage(self, pipeline_value):
        if not self.attributes.has_key('withFile'):
            raise needs_with_file_attribute("A process type of Generate needs a withFile attribute containing a filename/path.")
        path = self.resolve_pipeline_resource(self.attributes['withFile'])
        if not os.path.exists(path):
            raise generation_file_not_found("A process type of Generate couldn't find a file at %s" % path)
        data = file(path)
        doc_type = core.document_type.detect_document_type(data)
        if doc_type != core.document_type.types.oasis_open_document:
            data = core.docvert.generate_open_document(data)
        document_xml = core.opendocument.extract_useful_open_document_files(data, self.storage, os.path.basename(path))
        return document_xml

class needs_with_file_attribute(core.docvert_exception.docvert_exception):
    pass

class generation_file_not_found(core.docvert_exception.docvert_exception):
    pass

########NEW FILE########
__FILENAME__ = generatepostconversioneditorfiles
# -*- coding: utf-8 -*-
import os
import lxml.etree
import StringIO
import pipeline_item
import core.docvert_exception


class GeneratePostConversionEditorFiles(pipeline_item.pipeline_stage):
    def stage(self, pipeline_value):
        return pipeline_value




########NEW FILE########
__FILENAME__ = getpreface
# -*- coding: utf-8 -*-
import lxml.etree
import pipeline_item
import core.docvert_exception
import core.docvert_xml

class GetPreface(pipeline_item.pipeline_stage):
    def stage(self, pipeline_value):
        params = dict(
            loopDepth = 0,
            process = self.attributes['process'],
            customFilenameIndex = 'index.html',
            customFilenameSection = 'section#.html'
        )
        xslt_path = self.resolve_pipeline_resource('internal://each-page.xsl')
        return core.docvert_xml.transform(pipeline_value, xslt_path, params)



########NEW FILE########
__FILENAME__ = loop
# -*- coding: utf-8 -*-
import os
import pipeline_item
import copy
import core.docvert_exception
import core.docvert_pipeline
import core.docvert_xml
import lxml.etree

class Loop(pipeline_item.pipeline_stage):
    def stage(self, pipeline_value):
        if not self.attributes.has_key('numberOfTimes'):
            raise no_number_of_times_attribute("In process Loop there wasn't a numberOfTimes attribute.")
        
        numberOfTimes = self.attributes['numberOfTimes']
        if numberOfTimes.startswith('xpathCount:'):
            xpath = numberOfTimes[len('xpathCount:'):]
            xml = core.docvert_xml.get_document(pipeline_value)
            namespaces = {
                'xlink':'http://www.w3.org/1999/xlink',
                'db':'http://docbook.org/ns/docbook',
                'text':'urn:oasis:names:tc:opendocument:xmlns:text:1.0',
                'office':'urn:oasis:names:tc:opendocument:xmlns:office:1.0',
                'html':'http://www.w3.org/1999/xhtml',
                'xhtml':'http://www.w3.org/1999/xhtml'}
            nodes = xml.xpath(xpath, namespaces=namespaces)
            index = 0
            for node in nodes:
                index += 1
                child_depth = copy.copy(self.depth)
                child_depth.append(str(index))
                pipeline = core.docvert_pipeline.pipeline_processor(self.storage, self.child_stages, self.pipeline_directory, self.pipeline_storage_prefix, child_depth)
                child_pipeline_value = lxml.etree.tostring(pipeline_value)
                pipeline.start(child_pipeline_value) #discard return value
        elif numberOfTimes.startswith('substring:'):
            number = int(numberOfTimes[len('substring:'):])
            for index in range(1, number):
                pass
        elif numberOfTimes.startswith('number:'):
            number = int(numberOfTimes[len('number:'):])
            for index in range(1, number):
                pass
        return pipeline_value

class no_number_of_times_attribute(core.docvert_exception.docvert_exception):
    pass


########NEW FILE########
__FILENAME__ = normalizeopendocument
# -*- coding: utf-8 -*-
import lxml.etree
import pipeline_item
import core.docvert_xml

class NormalizeOpenDocument(pipeline_item.pipeline_stage):

    def stage(self, pipeline_value):
        normalize_opendocument_path = self.resolve_pipeline_resource('internal://normalize-opendocument.xsl')
        return core.docvert_xml.transform(pipeline_value, normalize_opendocument_path)





########NEW FILE########
__FILENAME__ = pipeline_item
# -*- coding: utf-8 -*-
import os.path

docvert_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class pipeline_stage(object):
    def __init__(self, storage, pipeline_directory, attributes, pipeline_storage_prefix=None, child_stages=None, depth=None):
        self.storage = storage
        self.pipeline_directory = pipeline_directory
        self.pipeline_id = os.path.basename(pipeline_directory)
        self.pipeline_id_namespace = os.path.basename(os.path.dirname(pipeline_directory))
        self.attributes = attributes
        self.pipeline_storage_prefix = pipeline_storage_prefix
        self.child_stages = child_stages
        self.depth = list() if depth is None else depth

    def resolve_pipeline_resource(self, resource_path):
        internal_prefix = 'internal://'
        if resource_path.startswith(internal_prefix):
            return os.path.join(docvert_root, 'core', 'transform', resource_path[len(internal_prefix):])
        return os.path.join(docvert_root, "pipelines", self.pipeline_id_namespace, self.pipeline_id, resource_path)

    def log(self, message, log_type='error'):
        log_filename = '%s.log' % log_type
        storage_path = log_filename
        if self.pipeline_storage_prefix is not None:
            storage_path = "%s/%s" % (self.pipeline_storage_prefix, log_filename)
        self.storage[storage_path] = message

    def add_tests(self, tests):
        self.storage.add_tests(tests)

    def get_tests(self):
        return self.storage.get_tests()


########NEW FILE########
__FILENAME__ = serialize
# -*- coding: utf-8 -*-
import os
import pipeline_item
import lxml.etree

class Serialize(pipeline_item.pipeline_stage):
    def stage(self, pipeline_value):
        storage_path = "%s/%s" % (self.pipeline_storage_prefix, self.attributes['toFile'])
        if self.pipeline_storage_prefix is None:
            storage_path = self.attributes['toFile']
        if '{customSection}' in storage_path:
            depth_string = 'section'
            depth_string += "-".join(self.depth)
            depth_string += ".html"
            storage_path = storage_path.replace('{customSection}', depth_string) 
        if hasattr(pipeline_value, 'read'):
            self.storage[storage_path] = str(pipeline_value)
        elif isinstance(pipeline_value, lxml.etree._Element) or isinstance(pipeline_value, lxml.etree._XSLTResultTree):
            self.storage[storage_path] = lxml.etree.tostring(pipeline_value)
        else:
            self.storage[storage_path] = str(pipeline_value)
        return pipeline_value



########NEW FILE########
__FILENAME__ = serializeopendocument
# -*- coding: utf-8 -*-
import cgi
import os
import zipfile
import lxml.etree
import StringIO
import pipeline_item
import core.docvert_exception

class SerializeOpenDocument(pipeline_item.pipeline_stage):
    def stage(self, pipeline_value):
        storage_path = "%s/%s" % (self.pipeline_storage_prefix, self.attributes['toFile'])
        if self.pipeline_storage_prefix is None:
            storage_path = self.attributes['toFile']
        if '{customSection}' in storage_path:
            depth_string = 'section'
            depth_string += "-".join(self.depth)
            depth_string += ".odt"
            storage_path = storage_path.replace('{customSection}', depth_string) 
        if not isinstance(pipeline_value, lxml.etree._Element) and not isinstance(pipeline_value, lxml.etree._XSLTResultTree):
            return pipeline_value
        zipdata = StringIO.StringIO()
        archive = zipfile.ZipFile(zipdata, 'w')
        archive.writestr('mimetype', 'application/vnd.oasis.opendocument.text')
        manifest_xml = '<?xml version="1.0" encoding="UTF-8"?>\n<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0">\n\t<manifest:file-entry manifest:media-type="application/vnd.oasis.opendocument.text" manifest:version="1.2" manifest:full-path="/"/>\n'
        root = pipeline_value.getroot()
        expected_lxml_root = '{docvert:5}root'
        if str(root.tag) != expected_lxml_root:
            raise core.docvert_exception.unable_to_serialize_opendocument("Can't serialize OpenDocument with a pipeline_value root node of '%s'." % root.tag)
        expected_lxml_child = '{docvert:5}external-file'
        for child in root.iterchildren():
            if str(child.tag) != expected_lxml_child:
                raise core.docvert_exception.unable_to_serialize_opendocument("Can't serialize OpenDocument with a pipeline_value child node of '%s'." % child.tag)
            filename = str(child.attrib['{docvert:5}name'])
            xml = "".join(map(lxml.etree.tostring, child.getchildren()))
            print "{%s]" % filename
            archive.writestr(filename, xml)
            manifest_xml += '\t<manifest:file-entry manifest:media-type="%s" manifest:full-path="%s"/>\n' % (cgi.escape('text/xml'), cgi.escape(filename))
        manifest_xml += '\t<manifest:file-entry media-type="" manifest:full-path="Pictures/"/>\n'
        imagetypes = {".svg":"image/svg+xml", ".png":"image/png", ".gif":"image/gif", ".bmp":"image/x-ms-bmp", ".jpg":"image/jpeg", ".jpe":"image/jpeg", ".jpeg":"image/jpeg"}
        for storage_key in self.storage.keys():
            if storage_key.startswith(self.pipeline_storage_prefix):
                extension = os.path.splitext(storage_key)[1]
                if extension in imagetypes.keys():
                    odt_path = "Pictures/%s" % os.path.basename(storage_key)
                    manifest_xml += '\t<manifest:file-entry media-type="%s" manifest:full-path="%s"/>\n' % (cgi.escape(imagetypes[extension]), cgi.escape(odt_path) )
                    archive.writestr(odt_path, self.storage[storage_key])
        manifest_xml += '</manifest:manifest>'
        archive.writestr('META-INF/manifest.xml', manifest_xml.encode("utf-8") )
        archive.close()
        zipdata.seek(0)
        self.storage.add(storage_path, zipdata.read())




########NEW FILE########
__FILENAME__ = splitpages
# -*- coding: utf-8 -*-
import lxml.etree
import pipeline_item
import core.docvert_exception
import core.docvert_xml

class SplitPages(pipeline_item.pipeline_stage):
    def stage(self, pipeline_value):
        depth_string = '-'.join(self.depth)
        params = dict(
            loopDepth = depth_string,
            process = self.attributes['process'],
            customFilenameIndex = 'index.html',
            customFilenameSection = 'section#.html'
        )
        xslt_path = self.resolve_pipeline_resource('internal://each-page.xsl')
        return core.docvert_xml.transform(pipeline_value, xslt_path, params)



########NEW FILE########
__FILENAME__ = test
# -*- coding: utf-8 -*-
import os
import os.path
import lxml.etree
import StringIO
import pipeline_item
import core.docvert_exception
import core.docvert
import core.docvert_xml


class Test(pipeline_item.pipeline_stage):
    def stage(self, pipeline_value):
        def get_size(data):
            if hasattr(data, 'read'):
                data.seek(0, os.SEEK_END)
                return data.tell()
            return len(data)

        if not (self.attributes.has_key("withFile") or self.attributes.has_key("extensionExist")):
            raise no_with_file_attribute("In process Test there wasn't a withFile or extensionExist attribute.")
        if pipeline_value is None:
            raise xml_empty("Cannot Test with %s because pipeline_value is None." % self.attributes['withFile'])
        test_result = None
        if self.attributes.has_key("withFile"):
            test_path = self.resolve_pipeline_resource(self.attributes['withFile'])
            if not os.path.exists(test_path):
                raise file_not_found("Test file not found at %s" % test_path)
            prefix = ""
            if self.attributes.has_key("prefix"):
                prefix = "%s: " % self.attributes["prefix"]
            if test_path.endswith(".rng"): # RelaxNG test
                relaxng_response = core.docvert_xml.relaxng(pipeline_value, test_path)
                node_name = "pass"
                if not relaxng_response["valid"]:
                    node_name = "fail"
                test_result = '<group xmlns="docvert:5"><%s>%s%s</%s></group>' % (node_name, prefix, core.docvert_xml.escape_text(str(relaxng_response["log"])), node_name)
            elif test_path.endswith(".txt"): # Substring test (new substring on each line)
                document_string = str(pipeline_value)
                if hasattr(pipeline_value, "read"):
                    document_string = pipeline_value.read()
                    pipeline_value.seek(0)
                test_result = '<group xmlns="docvert:5">'
                for line in open(test_path, 'r').readlines():
                    test_string = line[0:-1].strip()
                    if len(test_string) == 0: continue
                    node_name = "fail"
                    description = "doesn't contain"
                    occurences = document_string.count(test_string)
                    if occurences == 1:
                        node_name = "pass"
                        description = "contains one of"
                    elif occurences > 1:
                        node_name = "fail"
                        description = "contains %i of" % occurences
                    test_result += '<%s>%s%s</%s>' % (node_name, prefix, core.docvert_xml.escape_text('Document %s the string "%s"' % (description, test_string)), node_name)
                test_result += '</group>'
            else: #XSLT
                test_result = core.docvert_xml.transform(pipeline_value, test_path, dict(**self.attributes))
        elif self.attributes.has_key("extensionExist"):
            extension = self.attributes["extensionExist"]
            extension_exist_count = 1
            if self.attributes.has_key("extensionExistCount"):
                extension_exist_count = int(self.attributes["extensionExistCount"])
            original_extension_exist_count = extension_exist_count
            for key in self.storage.keys():
                if key.endswith('thumbnail.png'): #ignore any inbuilt thumbnails
                    continue
                if key.endswith(extension):
                    if self.pipeline_storage_prefix is None or (self.pipeline_storage_prefix and key.startswith(self.pipeline_storage_prefix)):
                        if get_size(self.storage[key]) > 0:
                            extension_exist_count -= 1
            test_result = "pass"
            text = 'There were %i files with the extension "%s" as expected.' % (original_extension_exist_count, extension)
            if extension_exist_count != 0:
                test_result = "fail"
                text = 'There were only %i (%i-%i) files instead of %i with the extension "%s". ' % (original_extension_exist_count - extension_exist_count, original_extension_exist_count, extension_exist_count, original_extension_exist_count, extension)
            test_result = '<group xmlns="docvert:5"><%s>%s</%s></group>' % (test_result, core.docvert_xml.escape_text(text), test_result)
        if self.attributes.has_key("debug"):
            raise core.docvert_exception.debug_xml_exception("Test Results", str(test_result), "text/xml; charset=UTF-8")
        self.add_tests(test_result)
        return pipeline_value        


class no_with_file_attribute(core.docvert_exception.docvert_exception):
    pass

class file_not_found(core.docvert_exception.docvert_exception):
    pass

class xml_empty(core.docvert_exception.docvert_exception):
    pass

########NEW FILE########
__FILENAME__ = transform
# -*- coding: utf-8 -*-
import os
import StringIO
import pipeline_item
import core.docvert_exception
import core.docvert_xml

class Transform(pipeline_item.pipeline_stage):
    def stage(self, pipeline_value):
        if not self.attributes.has_key("withFile"):
            raise no_with_file_attribute("In process Transform there wasn't a withFile attribute.")
        if pipeline_value is None:
            raise xml_empty("Cannot Transform with %s because pipeline_value is None." % self.attributes['withFile'])
        xslt_path = self.resolve_pipeline_resource(self.attributes['withFile'])
        if not os.path.exists(xslt_path):
            raise xslt_not_found("XSLT file not found at %s" % xslt_path)
        return core.docvert_xml.transform(pipeline_value, xslt_path)

class no_with_file_attribute(core.docvert_exception.docvert_exception):
    pass

class xslt_not_found(core.docvert_exception.docvert_exception):
    pass

class xml_empty(core.docvert_exception.docvert_exception):
    pass

########NEW FILE########
__FILENAME__ = transformopendocumenttodocbook
# -*- coding: utf-8 -*-
import lxml.etree
import pipeline_item
import core.docvert_xml
import core.docvert_exception

class TransformOpenDocumentToDocBook(pipeline_item.pipeline_stage):

    def stage(self, pipeline_value):
        normalize_opendocument_path = self.resolve_pipeline_resource('internal://normalize-opendocument.xsl')
        pipeline_value = core.docvert_xml.transform(pipeline_value, normalize_opendocument_path)
        if self.attributes.has_key("debugAfterOpenDocumentNormalization"):
            pipeline_value = lxml.etree.tostring(pipeline_value)
            raise core.docvert_exception.debug_xml_exception("Current contents of pipeline", pipeline_value, 'text/xml')
        opendocument_to_docbook_path = self.resolve_pipeline_resource('internal://opendocument-to-docbook.xsl')
        pipeline_value = core.docvert_xml.transform(pipeline_value, opendocument_to_docbook_path)
        normalize_docbook_path = self.resolve_pipeline_resource('internal://normalize-docbook.xsl')
        pipeline_value = core.docvert_xml.transform(pipeline_value, normalize_docbook_path)
        if self.attributes.has_key("debugAfterDocBookNormalization"):
            pipeline_value = lxml.etree.tostring(pipeline_value)
            raise core.docvert_exception.debug_xml_exception("Current contents of pipeline", pipeline_value, 'text/xml')
        return pipeline_value






########NEW FILE########
__FILENAME__ = writemetadata
# -*- coding: utf-8 -*-
import os
import pipeline_item
import core.docvert_exception
import core.docvert_xml
import lxml.etree

class WriteMetaData(pipeline_item.pipeline_stage):
    def stage(self, pipeline_value):
        opendocument_xml_path = "%s/%s" % (self.pipeline_storage_prefix, 'opendocument.xml')
        xslt_path = self.resolve_pipeline_resource('internal://extract-metadata.xsl')
        if not os.path.exists(xslt_path):
            raise xslt_not_found("XSLT file not found at %s" % xslt_path)
        metadata_xml_path = "%s/%s" % (self.pipeline_storage_prefix, 'docvert-meta.xml')
        metadata_xml = core.docvert_xml.transform(self.storage.get(opendocument_xml_path), xslt_path)
        if isinstance(metadata_xml, lxml.etree._Element) or isinstance(metadata_xml, lxml.etree._XSLTResultTree):
            metadata_xml = lxml.etree.tostring(metadata_xml)
        self.storage[metadata_xml_path] = metadata_xml
        return pipeline_value

class xslt_not_found(core.docvert_exception.docvert_exception):
    pass



########NEW FILE########
__FILENAME__ = docvert-cli
#!/usr/bin/env python2.6
# -*- coding: utf-8 -*-
import sys
import StringIO
import uuid
import os.path
import copy
import argparse
import tempfile
import core.docvert
import core.docvert_storage
import core.docvert_exception

version = core.docvert.version
pipeline_types = core.docvert.get_all_pipelines()
auto_pipelines = []
default_auto_pipeline = None
for auto_pipeline in pipeline_types['auto_pipelines']:
    auto_pipelines.append(auto_pipeline["id"])
    if auto_pipeline["id"].endswith(".default"):
        default_auto_pipeline = auto_pipeline["id"]

class PrintPipelines(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        print "List of all pipelines\n---------------------"
        for pipeline_type, pipelines in pipeline_types.iteritems():
            print "type: %s" % pipeline_type
            for pipeline in pipelines:
                print "      - %s" % pipeline['id']
            print ""
        exit()

parser = argparse.ArgumentParser(description='Converts Office files to OpenDocument, DocBook and HTML.', epilog='E.g.: ./docvert-cli.py doc/sample/sample-document.doc -p="web standards"')
parser.add_argument('--version', '-v', action='version', version='Docvert %s' % version)
parser.add_argument('infile', type=file, help='Path or Stdin of Office file to convert', default=sys.stdin, nargs='+')
parser.add_argument('--pipeline', '-p', help='Pipeline you wish to use.', required=True)
parser.add_argument('--response', '-r', help='Format of ZIP conversion response.', default='auto', choices=['auto','path','stdout'])
parser.add_argument('--autopipeline', '-a', help='AutoPipeline to use (when your pipeline requires it).', default=default_auto_pipeline, choices=auto_pipelines)
parser.add_argument('--url', '-u', help='URL to download and convert. Must be an Office file.')
parser.add_argument('--list-pipelines', '-l', action=PrintPipelines, help='List all pipeline types', nargs=0)
parser.add_argument('--pipelinetype', '-t', help='Pipeline type you wish to use.', default='pipelines', choices=pipeline_types.keys())

args = parser.parse_args() #stops here if there were no args or if they asked for --help

def process_commands(filesdata, pipeline_id, pipeline_type, auto_pipeline_id, after_conversion, url):
    docvert_4_default = '.default'
    if auto_pipeline_id and auto_pipeline_id.endswith(docvert_4_default):
        auto_pipeline_id = auto_pipeline_id[0:-len(docvert_4_default)]
    files = dict()
    file_index = 1
    for filedata in filesdata:
        files['document-%i.doc' % file_index] = filedata
        file_index += 1
    urls = list()
    if url != None:
        urls.append(url)
    try:
        response = core.docvert.process_conversion(files, urls, pipeline_id, pipeline_type, auto_pipeline_id)
    except core.docvert_exception.debug_exception, exception:
        print >> sys.stderr, "%s: %s" % (exception, exception.data)
    #TODO: when after_conversion="auto"
    if after_conversion == "stdout":
        print >> sys.stdout, response.to_zip().getvalue()
        exit()
    os_handle, zip_path = tempfile.mkstemp()
    zip_handler = open(zip_path, 'w')
    zip_handler.write(response.to_zip().getvalue())
    zip_handler.close()
    os.rename(zip_path, "%s.zip" % zip_path)
    print "Success! ZIP conversion at: %s.zip" % zip_path


   
process_commands(args.infile, args.pipeline, args.pipelinetype, args.autopipeline, args.response, args.url)


########NEW FILE########
__FILENAME__ = docvert-web
#!/usr/bin/env python2.6
# -*- coding: utf-8 -*-
import sys
import StringIO
import uuid
import os.path
import socket
import optparse
import cgi
docvert_root = os.path.dirname(os.path.abspath(__file__))
inbuilt_bottle_path = os.path.join(docvert_root, 'lib/bottle')
try:
    import bottle
    if not hasattr(bottle, 'static_file'):
        message = "Notice: Old version of Bottle at %s, instead using bundled version at %s%sbottle.py" % (bottle.__file__, inbuilt_bottle_path, os.sep)
        print message
        raise ImportError, message
except ImportError, exception:
    try:
        sys.path.insert(0, inbuilt_bottle_path)
        try:
            reload(bottle)
        except NameError:
            import bottle
    except ImportError:
        sys.stderr.write("Error: Unable to find Bottle libraries in %s. Exiting...\n" % sys.path)
        sys.exit(0)
import lib.bottlesession.bottlesession
bottle.debug(True)
import core.docvert
import core.docvert_storage
import core.docvert_exception
import core.document_type

# START DEFAULT CONFIG
theme='default'
host='localhost'
port=8080
# END CONFIG
parser = optparse.OptionParser()
parser.add_option("-p", "--port", dest="port", help="Port to run on", type="int")
parser.add_option("-H", "--host", dest="host", help="Hostname or IP run on", type="str")
(options, args) = parser.parse_args()
if options.port:
    port = options.port
if options.host:
    host = options.host
theme_directory='%s/core/web_service_themes' % docvert_root
bottle.TEMPLATE_PATH.append('%s/%s' % (theme_directory, theme))

# URL mappings

@bottle.route('/index', method='GET')
@bottle.route('/', method='GET')
@bottle.view('index')
def index():
    return dict(core.docvert.get_all_pipelines(False).items() + {"libreOfficeStatus": core.docvert_libreoffice.checkLibreOfficeStatus()}.items() )

@bottle.route('/static/:path#.*#', method='GET')
def static(path=''):
    return bottle.static_file(path, root=theme_directory)

@bottle.route('/lib/:path#.*#', method='GET')
def libstatic(path=None):
    return bottle.static_file(path, root='%s/lib' % docvert_root)

@bottle.route('/web-service.php', method='POST') #for legacy Docvert support
@bottle.route('/web-service', method='POST')
@bottle.view('web-service')
def webservice():
    files = dict()
    first_document_id = None
    there_was_at_least_one_thing_uploaded = False
    print bottle.request.files
    print len(bottle.request.files)
    print dir(bottle.request.files)
    for key, item in bottle.request.files.iteritems():
        print "2"
        there_was_at_least_one_thing_uploaded = True
        items = bottle.request.files.getall(key)
        for field_storage in items:
            filename = field_storage.filename
            unique = 1
            if files.has_key(filename) and files[filename].getvalue() == field_storage.value: #remove same file uploaded multiple times
                continue
            while files.has_key(filename):
                filename = field_storage.filename + str(unique)
                unique += 1
            try:
                filename = filename.decode("utf-8")
            except UnicodeDecodeException, exception:
                pass
            files[filename] = StringIO.StringIO(field_storage.value)
    pipeline_id = bottle.request.POST.get('pipeline')
    if pipeline_id.startswith('autopipeline:'): #Docvert 4.x
        pipeline_id = pipeline_id[len('autopipeline:'):]
    auto_pipeline_id = None
    if bottle.request.POST.get('break_up_pages_ui_version'):
        if bottle.request.POST.get('break_up_pages'):
            auto_pipeline_id = bottle.request.POST.get('autopipeline')
        if auto_pipeline_id is None:
            pipelines = core.docvert.get_all_pipelines().items()
            for pipelinetype_key, pipelinetype_value in pipelines:
                if pipelinetype_key == "auto_pipelines":
                    for pipeline in pipelinetype_value:
                        if "nothing" in pipeline["id"].lower():
                            auto_pipeline_id = pipeline["id"]
    else:
        auto_pipeline_id = bottle.request.POST.get('autopipeline')
    docvert_4_default = '.default'
    if auto_pipeline_id and auto_pipeline_id.endswith(docvert_4_default):
        auto_pipeline_id = auto_pipeline_id[0:-len(docvert_4_default)]
    after_conversion = bottle.request.POST.get('afterconversion')
    urls = bottle.request.POST.getall('upload_web[]')
    if len(urls) == 1 and urls[0] == '':
        urls = list()
    else:
        urls = set(urls)
    response = None
    if there_was_at_least_one_thing_uploaded is False: #while we could have counted len(files) or len(urls) the logic around those is more complex, and I don't want to show this error unless there was genuinely no files uploaded
        bottle.response.content_type = "text/html"
        return '<!DOCTYPE html><html><body><h1>Error: No files were uploaded</h1><p>Known issues that can cause this:</p><ul><li>Permissions problem on the server or browser: Try ensuring that your upload file has all read permissions set.</li><li>Chrome/Chromium can sometimes cause file upload problems (some combination of Chrome/Bottle, it\'s not a Docvert-specific bug). Sorry, but Firefox seems to work.</li></ul><hr><a href="/">Try again?</a></body></html>'
    try:
        response = core.docvert.process_conversion(files, urls, pipeline_id, 'pipelines', auto_pipeline_id, suppress_errors=True)
    except core.docvert_exception.debug_exception, exception:
        bottle.response.content_type = exception.content_type
        return exception.data
    conversion_id = "%s" % uuid.uuid4()
    if after_conversion == "downloadZip" or after_conversion == "zip":
        bottle.response.content_type = 'application/zip'
        bottle.response.headers['Content-Disposition'] = 'attachment; filename="%s.zip"' % response.get_zip_name()
        return response.to_zip().getvalue()
    pipeline_summary = "%s (%s)" % (pipeline_id, auto_pipeline_id)
    session_manager = lib.bottlesession.bottlesession.PickleSession()
    session = session_manager.get_session()
    session[conversion_id] = response
    conversions_tabs = dict()
    first_document_url = "conversions/%s/%s/" % (conversion_id, response.default_document)
    for filename in files.keys():
        thumbnail_path = "%s/thumbnail.png" % filename
        if response.has_key(thumbnail_path):
            thumbnail_path = None
        conversions_tabs[filename] = dict(friendly_name=response.get_friendly_name_if_available(filename), pipeline=pipeline_id, auto_pipeline=auto_pipeline_id, thumbnail_path=thumbnail_path)
    try:
        session_manager.save(session)
    except OSError, e:
        import traceback
        traceback.print_exc(file=sys.stdout)
        conversions_tabs = {'Session file problem': dict(friendly_name='Session file problem', pipeline=None, auto_pipeline=None, thumbnail_path=None) }
        first_document_url = "/bottle_session_file_problem"
    return dict(conversions=conversions_tabs, conversion_id=conversion_id, first_document_url=first_document_url)

@bottle.route('/favicon.ico', method='GET')
def favicon():
    return bottle.static_file('favicon.ico', root='%s/%s' % (theme_directory, theme))

@bottle.route('/bottle_session_file_problem', method='GET')
def bottle_session_file_problem():
    print '%s/lib/bottle' % docvert_root
    return bottle.static_file('bottle_session_file_problem.html', root='%s/lib/bottle' % docvert_root)

@bottle.route('/conversions/:conversion_id/:path#.*#')
def conversion_static_file(conversion_id, path):
    session_manager = lib.bottlesession.bottlesession.PickleSession()
    session = session_manager.get_session()
    if not session.has_key(conversion_id): # They don't have authorisation
        raise bottle.HTTPError(code=404)
    try:
        path = path.decode("utf-8")
    except UnicodeDecodeException, exception:
        pass
    filetypes = {".xml":"text/xml", ".html":"text/html", ".xhtml":"text/html", ".htm":"text/html", ".svg":"image/svg+xml", ".txt":"text/plain", ".png":"image/png", ".gif":"image/gif", ".bmp":"image/x-ms-bmp", ".jpg":"image/jpeg", ".jpe":"image/jpeg", ".jpeg":"image/jpeg", ".css":"text/css", ".js":"text/javascript", ".odt":"application/vnd.oasis.opendocument.text", ".odp":"application/vnd.oasis.opendocument.presentation", ".ods":"application/vnd.oasis.opendocument.spreadsheet", ".dbk":"application/docbook+xml"}
    if not session[conversion_id].has_key(path): # They have authorisation but that exact path doesn't exist, try fallbacks
        fallbacks = ["index.html", "index.htm", "index.xml", "index.php", "default.htm", "default.html", "index.asp", "default.aspx", "index.aspx", "default.aspx", "index.txt", "index.odt", "default.odt", "index.dbk", "default.dbk"]
        valid_fallback_path = None
        separator = "/"
        if path.endswith("/"):
            separator = ""
        for fallback in fallbacks:
            fallback_path = path+separator+fallback
            if session[conversion_id].has_key(fallback_path):
                valid_fallback_path = fallback_path
                break
        if valid_fallback_path is None:
            raise bottle.HTTPError(code=404)
        path = valid_fallback_path
        extension = os.path.splitext(path)[1]
        if extension == ".odt":
            bottle.response.content_type = filetypes[".html"]
            link_html = 'click here to download %s' % cgi.escape(os.path.basename(path))
            thumbnail_path = "%s/thumbnail.png" % path[0:path.rfind("/")]
            if session[conversion_id].has_key(thumbnail_path):
                link_html = '<img src="thumbnail.png"><br>' + link_html
            return '<!DOCTYPE html><html><head><title>%s</title><style type="text/css">body{font-family:sans-serif;font-size:small} a{text-decoration:none} p{text-align:center} img{clear:both;border: solid 1px #cccccc}</style></head><body><p><a href="%s">%s</a></p></body></html>' % (
                cgi.escape(path),
                cgi.escape(os.path.basename(path)),
                link_html
            )
    extension = os.path.splitext(path)[1]
    if filetypes.has_key(extension):
        bottle.response.content_type = filetypes[extension]
    else:
        bottle.response.content_type = "text/plain"
    return session[conversion_id][path]

@bottle.route('/conversions-zip/:conversion_id')
def conversion_zip(conversion_id):
    session_manager = lib.bottlesession.bottlesession.PickleSession()
    session = session_manager.get_session()
    if not session.has_key(conversion_id): # They don't have authorisation
        raise bottle.HTTPError(code=404)
    bottle.response.content_type = 'application/zip'
    bottle.response.headers['Content-Disposition'] = 'attachment; filename="%s.zip"' % session[conversion_id].get_zip_name()
    return session[conversion_id].to_zip().getvalue()

@bottle.route('/libreoffice-status', method='GET')
def libreoffice_status():
    return bottle.json_dumps( {"libreoffice-status":core.docvert_libreoffice.checkLibreOfficeStatus()} )

@bottle.route('/tests', method='GET')
@bottle.view('tests')
def tests():
    return core.docvert.get_all_pipelines()

@bottle.route('/web-service/tests/:test_id', method='GET')
def web_service_tests(test_id):
    suppress_error = bottle.request.GET.get('suppress_error') == "true"
    storage = core.docvert_storage.storage_memory_based()
    error_message = None
    if suppress_error:
        try:
            core.docvert.process_pipeline(None, test_id, "tests", None, storage)
        except Exception, exception:
            bottle.response.content_type = "text/plain"
            class_name = "%s" % type(exception).__name__
            return bottle.json_dumps([{"status":"fail", "message": "Unable to run tests due to exception. <%s> %s" % (class_name, exception)}])
    else:
        try:
            core.docvert.process_pipeline(None, test_id, "tests", None, storage)
        except (core.docvert_exception.debug_exception, core.docvert_exception.debug_xml_exception), exception:
            bottle.response.content_type = exception.content_type
            return exception.data
    return bottle.json_dumps(storage.tests)

@bottle.route('/tests/', method='GET')
def tests_wrongdir():
    bottle.redirect('/tests')

@bottle.route('/3rdparty/sscdocapi')
def third_party_sscdocapi():
    return bottle.static_file('sscdocapi.html', root='%s/core/3rd-party/' % docvert_root)    

try:
    bottle.run(host=host, port=port, quiet=False)
except socket.error, e:
    if 'address already in use' in str(e).lower():
        print 'ERROR: %s:%i already in use.\nTry another port? Use command line parameter -H HOST or -p PORT to change it.' % (host, port)
    else:
        raise


########NEW FILE########
__FILENAME__ = bottle
# -*- coding: utf-8 -*-
"""
Bottle is a fast and simple micro-framework for small web applications. It
offers request dispatching (Routes) with url parameter support, templates,
a built-in HTTP Server and adapters for many third party WSGI/HTTP-server and
template engines - all in a single file and with no dependencies other than the
Python Standard Library.

Homepage and documentation: http://bottle.paws.de/

Copyright (c) 2010, Marcel Hellkamp.
License: MIT (see LICENSE.txt for details)
"""

from __future__ import with_statement

__author__ = 'Marcel Hellkamp'
__version__ = '0.9.dev'
__license__ = 'MIT'

import base64
import cgi
import email.utils
import functools
import hmac
import httplib
import itertools
import mimetypes
import os
import re
import subprocess
import sys
import tempfile
import thread
import threading
import time
import warnings

from Cookie import SimpleCookie
from tempfile import TemporaryFile
from traceback import format_exc
from urllib import quote as urlquote
from urlparse import urlunsplit, urljoin

try: from collections import MutableMapping as DictMixin
except ImportError: # pragma: no cover
    from UserDict import DictMixin

try: from urlparse import parse_qs
except ImportError: # pragma: no cover
    from cgi import parse_qs

try: import cPickle as pickle
except ImportError: # pragma: no cover
    import pickle

try: from json import dumps as json_dumps
except ImportError: # pragma: no cover
    try: from simplejson import dumps as json_dumps
    except ImportError: # pragma: no cover
        try: from django.utils.simplejson import dumps as json_dumps
        except ImportError: # pragma: no cover
            json_dumps = None

if sys.version_info >= (3,0,0): # pragma: no cover
    # See Request.POST
    from io import BytesIO
    from io import TextIOWrapper
    class NCTextIOWrapper(TextIOWrapper):
        ''' Garbage collecting an io.TextIOWrapper(buffer) instance closes the
            wrapped buffer. This subclass keeps it open. '''
        def close(self): pass
    def touni(x, enc='utf8'):
        """ Convert anything to unicode """
        return str(x, encoding=enc) if isinstance(x, bytes) else str(x)
else:
    from StringIO import StringIO as BytesIO
    bytes = str
    NCTextIOWrapper = None
    def touni(x, enc='utf8'):
        """ Convert anything to unicode """
        return x if isinstance(x, unicode) else unicode(str(x), encoding=enc)

def tob(data, enc='utf8'):
    """ Convert anything to bytes """
    return data.encode(enc) if isinstance(data, unicode) else bytes(data)

# Convert strings and unicode to native strings
if sys.version_info >= (3,0,0):
    tonat = touni
else:
    tonat = tob
tonat.__doc__ = """ Convert anything to native strings """


# Backward compatibility
def depr(message, critical=False):
    if critical: raise DeprecationWarning(message)
    warnings.warn(message, DeprecationWarning, stacklevel=3)


# Small helpers

def makelist(data):
    if isinstance(data, (tuple, list, set, dict)): return list(data)
    elif data: return [data]
    else: return []


class DictProperty(object):
    ''' Property that maps to a key in a local dict-like attribute. '''
    def __init__(self, attr, key=None, read_only=False):
        self.attr, self.key, self.read_only = attr, key, read_only

    def __call__(self, func):
        functools.update_wrapper(self, func, updated=[])
        self.getter, self.key = func, self.key or func.__name__
        return self

    def __get__(self, obj, cls):
        if not obj: return self
        key, storage = self.key, getattr(obj, self.attr)
        if key not in storage: storage[key] = self.getter(obj)
        return storage[key]

    def __set__(self, obj, value):
        if self.read_only: raise ApplicationError("Read-Only property.")
        getattr(obj, self.attr)[self.key] = value

    def __delete__(self, obj):
        if self.read_only: raise ApplicationError("Read-Only property.")
        del getattr(obj, self.attr)[self.key]

def cached_property(func):
    ''' A property that, if accessed, replaces itself with the computed
        value. Subsequent accesses won't call the getter again. '''
    return DictProperty('__dict__')(func)

class lazy_attribute(object): # Does not need configuration -> lower-case name
    ''' A property that caches itself to the class object. '''
    def __init__(self, func):
        functools.update_wrapper(self, func, updated=[])
        self.getter = func
    
    def __get__(self, obj, cls):
        value = self.getter(cls)
        setattr(cls, self.__name__, value)
        return value


###############################################################################
# Exceptions and Events ########################################################
###############################################################################

class BottleException(Exception):
    """ A base class for exceptions used by bottle. """
    pass


class HTTPResponse(BottleException):
    """ Used to break execution and immediately finish the response """
    def __init__(self, output='', status=200, header=None):
        super(BottleException, self).__init__("HTTP Response %d" % status)
        self.status = int(status)
        self.output = output
        self.headers = HeaderDict(header) if header else None

    def apply(self, response):
        if self.headers:
            for key, value in self.headers.iterallitems():
                response.headers[key] = value
        response.status = self.status


class HTTPError(HTTPResponse):
    """ Used to generate an error page """
    def __init__(self, code=500, output='Unknown Error', exception=None, traceback=None, header=None):
        super(HTTPError, self).__init__(output, code, header)
        self.exception = exception
        self.traceback = traceback

    def __repr__(self):
        return template(ERROR_PAGE_TEMPLATE, e=self)






###############################################################################
# Routing ######################################################################
###############################################################################

class RouteError(BottleException):
    """ This is a base class for all routing related exceptions """


class RouteSyntaxError(RouteError):
    """ The route parser found something not supported by this router """


class RouteBuildError(RouteError):
    """ The route could not been built """


class Router(object):
    ''' A Router is an ordered collection of route->target pairs. It is used to
        efficiently match WSGI requests against a number of routes and return
        the first target that satisfies the request. A route is defined by a
        path-rule and a HTTP method.
        
        The path-rule is either a static path (e.g. `/contact`) or a dynamic
        path that contains wildcards (e.g. `/wiki/:page`). By default, wildcards
        consume characters up to the next slash (`/`). To change that, you may
        add a regular expression pattern (e.g. `/wiki/:page#[a-z]+#`).

        For performance reasons, static routes (rules without wildcards) are
        checked first. Dynamic routes are tested in order and the first
        matching rule returns. Try to avoid ambiguous or overlapping rules.

        The HTTP method string matches only on equality, with two exceptions:
          * ´GET´ routes also match ´HEAD´ requests if there is no appropriate
            ´HEAD´ route installed.
          * ´ANY´ routes do match if there is no other suitable route installed.
    '''
    default = '[^/]+'

    @lazy_attribute
    def syntax(cls):
        return re.compile(r'(?<!\\):([a-zA-Z_][a-zA-Z_0-9]*)?(?:#(.*?)#)?')

    def __init__(self):
        self.routes = {}  # A {rule: {method: target}} mapping
        self.rules  = []  # An ordered list of rules
        self.named  = {}  # A name->(rule, build_info) mapping
        self.static = {}  # Cache for static routes: {path: {method: target}}
        self.dynamic = [] # Cache for dynamic routes. See _compile()

    def add(self, rule, method, target, name=None):
        ''' Add a new route or overwrite an existing target. '''
        if rule in self.routes:
            self.routes[rule][method.upper()] = target
        else:
            self.routes[rule] = {method.upper(): target}
            self.rules.append(rule)
            if self.static or self.dynamic: # Clear precompiler cache.
                self.static, self.dynamic = {}, {}
        if name:
            self.named[name] = (rule, None)

    def delete(self, rule, method=None):
        ''' Delete an existing route. Omit `method` to delete all targets. '''
        if rule not in self.routes and rule in self.named:
            rule = self.named[rule][0]
        if rule in self.routes:
            if method: del self.routes[rule][method]
            else: self.routes[rule].clear()
            if not self.routes[rule]:
                del self.routes[rule]
                self.rules.remove(rule)

    def build(self, _name, *anon, **args):
        ''' Return a string that matches a named route. Use keyword arguments
            to fill out named wildcards. Remaining arguments are appended as a
            query string. Raises RouteBuildError or KeyError.'''
        if _name not in self.named:
            raise RouteBuildError("No route with that name.", _name)
        rule, pairs = self.named[_name]
        if not pairs:
            token = self.syntax.split(rule)
            parts = [p.replace('\\:',':') for p in token[::3]]
            names = token[1::3]
            if len(parts) > len(names): names.append(None)
            pairs = zip(parts, names)
            self.named[_name] = (rule, pairs)
        try:
            anon = list(anon)
            url = [s if k is None
                   else s+str(args.pop(k)) if k else s+str(anon.pop())
                   for s, k in pairs]
        except IndexError:
            msg = "Not enough arguments to fill out anonymous wildcards."
            raise RouteBuildError(msg)
        except KeyError, e:
            raise RouteBuildError(*e.args)
        
        if args: url += ['?', urlencode(args.iteritems())]
        return ''.join(url)

    def match(self, environ):
        ''' Return a (target, url_agrs) tuple or raise HTTPError(404/405). '''
        targets, urlargs = self._match_path(environ)
        if not targets:
            raise HTTPError(404, "Not found: " + environ['PATH_INFO'])
        environ['router.url_args'] = urlargs
        method = environ['REQUEST_METHOD'].upper()
        if method in targets:
            return targets[method], urlargs
        if method == 'HEAD' and 'GET' in targets:
            return targets['GET'], urlargs
        if 'ANY' in targets:
            return targets['ANY'], urlargs
        allowed = [verb for verb in targets if verb != 'ANY']
        if 'GET' in allowed and 'HEAD' not in allowed:
            allowed.append('HEAD')
        raise HTTPError(405, "Method not allowed.",
                        header=[('Allow',",".join(allowed))])

    def _match_path(self, environ):
        ''' Optimized PATH_INFO matcher. '''
        path = environ['PATH_INFO'] or '/'
        # Assume we are in a warm state. Search compiled rules first.
        match = self.static.get(path)
        if match: return match, {}
        for combined, rules in self.dynamic:
            match = combined.match(path)
            if not match: continue
            gpat, match = rules[match.lastindex - 1]
            return match, gpat.match(path).groupdict() if gpat else {}
        # Lazy-check if we are really in a warm state. If yes, stop here.
        if self.static or self.dynamic or not self.routes: return None, {}
        # Cold state: We have not compiled any rules yet. Do so and try again.
        if not environ.get('wsgi.run_once'):
            self._compile()
            return self._match_path(environ)
        # For run_once (CGI) environments, don't compile. Just check one by one.
        epath = path.replace(':','\\:') # Turn path into its own static rule.
        match = self.routes.get(epath) # This returns static rule only.
        if match: return match, {}
        for rule in self.rules:
            #: Skip static routes to reduce re.compile() calls.
            if rule.count(':') < rule.count('\\:'): continue
            match = self._compile_pattern(rule).match(path)
            if match: return self.routes[rule], match.groupdict()
        return None, {}

    def _compile(self):
        ''' Prepare static and dynamic search structures. '''
        self.static = {}
        self.dynamic = []
        def fpat_sub(m):
            return m.group(0) if len(m.group(1)) % 2 else m.group(1) + '(?:'
        for rule in self.rules:
            target = self.routes[rule]
            if not self.syntax.search(rule):
                self.static[rule.replace('\\:',':')] = target
                continue
            gpat = self._compile_pattern(rule)
            fpat = re.sub(r'(\\*)(\(\?P<[^>]*>|\((?!\?))', fpat_sub, gpat.pattern)
            gpat = gpat if gpat.groupindex else None
            try:
                combined = '%s|(%s)' % (self.dynamic[-1][0].pattern, fpat)
                self.dynamic[-1] = (re.compile(combined), self.dynamic[-1][1])
                self.dynamic[-1][1].append((gpat, target))
            except (AssertionError, IndexError), e: # AssertionError: Too many groups
                self.dynamic.append((re.compile('(^%s$)'%fpat),
                                    [(gpat, target)]))
            except re.error, e:
                raise RouteSyntaxError("Could not add Route: %s (%s)" % (rule, e))

    def _compile_pattern(self, rule):
        ''' Return a regular expression with named groups for each wildcard. '''
        out = ''
        for i, part in enumerate(self.syntax.split(rule)):
            if i%3 == 0:   out += re.escape(part.replace('\\:',':'))
            elif i%3 == 1: out += '(?P<%s>' % part if part else '(?:'
            else:          out += '%s)' % (part or '[^/]+')
        return re.compile('^%s$'%out)


        



###############################################################################
# Application Object ###########################################################
###############################################################################

class Bottle(object):
    """ WSGI application """

    def __init__(self, catchall=True, autojson=True, config=None):
        """ Create a new bottle instance.
            You usually don't do that. Use `bottle.app.push()` instead.
        """
        self.routes = [] # List of installed routes including metadata.
        self.callbacks = {} # Cache for wrapped callbacks.
        self.router = Router() # Maps to self.routes indices.

        self.mounts = {}
        self.error_handler = {}
        self.catchall = catchall
        self.config = config or {}
        self.serve = True
        self.castfilter = []
        if autojson and json_dumps:
            self.add_filter(dict, dict2json)
        self.hooks = {'before_request': [], 'after_request': []}

    def optimize(self, *a, **ka):
        depr("Bottle.optimize() is obsolete.")

    def mount(self, app, script_path):
        ''' Mount a Bottle application to a specific URL prefix '''
        if not isinstance(app, Bottle):
            raise TypeError('Only Bottle instances are supported for now.')
        script_path = '/'.join(filter(None, script_path.split('/')))
        path_depth = script_path.count('/') + 1
        if not script_path:
            raise TypeError('Empty script_path. Perhaps you want a merge()?')
        for other in self.mounts:
            if other.startswith(script_path):
                raise TypeError('Conflict with existing mount: %s' % other)
        @self.route('/%s/:#.*#' % script_path, method="ANY")
        def mountpoint():
            request.path_shift(path_depth)
            return app.handle(request.environ)
        self.mounts[script_path] = app

    def add_filter(self, ftype, func):
        ''' Register a new output filter. Whenever bottle hits a handler output
            matching `ftype`, `func` is applied to it. '''
        if not isinstance(ftype, type):
            raise TypeError("Expected type object, got %s" % type(ftype))
        self.castfilter = [(t, f) for (t, f) in self.castfilter if t != ftype]
        self.castfilter.append((ftype, func))
        self.castfilter.sort()

    def match_url(self, path, method='GET'):
        return self.match({'PATH_INFO': path, 'REQUEST_METHOD': method})
        
    def match(self, environ):
        """ Return a (callback, url-args) tuple or raise HTTPError. """
        target, args = self.router.match(environ)
        try:
            return self.callbacks[target], args
        except KeyError:
            callback, decorators = self.routes[target]
            wrapped = callback
            for wrapper in decorators[::-1]:
                wrapped = wrapper(wrapped)
            #for plugin in self.plugins or []:
            #    wrapped = plugin.apply(wrapped, rule)
            functools.update_wrapper(wrapped, callback)
            self.callbacks[target] = wrapped
            return wrapped, args

    def get_url(self, routename, **kargs):
        """ Return a string that matches a named route """
        scriptname = request.environ.get('SCRIPT_NAME', '').strip('/') + '/'
        location = self.router.build(routename, **kargs).lstrip('/')
        return urljoin(urljoin('/', scriptname), location)

    def route(self, path=None, method='GET', no_hooks=False, decorate=None,
              template=None, template_opts={}, callback=None, name=None,
              static=False):
        """ Decorator: Bind a callback function to a request path.

            :param path: The request path or a list of paths to listen to. See 
              :class:`Router` for syntax details. If no path is specified, it
              is automatically generated from the callback signature. See
              :func:`yieldroutes` for details.
            :param method: The HTTP method (POST, GET, ...) or a list of
              methods to listen to. (default: GET)
            :param decorate: A decorator or a list of decorators. These are
              applied to the callback in reverse order (on demand only).
            :param no_hooks: If true, application hooks are not triggered
              by this route. (default: False)
            :param template: The template to use for this callback.
              (default: no template)
            :param template_opts: A dict with additional template parameters.
            :param name: The name for this route. (default: None)
            :param callback: If set, the route decorator is directly applied
              to the callback and the callback is returned instead. This
              equals ``Bottle.route(...)(callback)``.
        """
        # @route can be used without any parameters
        if callable(path): path, callback = None, path
        # Build up the list of decorators
        decorators = makelist(decorate)
        if template:     decorators.insert(0, view(template, **template_opts))
        if not no_hooks: decorators.append(self._add_hook_wrapper)
        #decorators.append(partial(self.apply_plugins, skiplist))
        def wrapper(func):
            for rule in makelist(path) or yieldroutes(func):
                for verb in makelist(method):
                    if static:
                        rule = rule.replace(':','\\:')
                        depr("Use backslash to escape ':' in routes.")
                    #TODO: Prepare this for plugins
                    self.router.add(rule, verb, len(self.routes), name=name)
                    self.routes.append((func, decorators))
            return func
        return wrapper(callback) if callback else wrapper

    def _add_hook_wrapper(self, func):
        ''' Add hooks to a callable. See #84 '''
        @functools.wraps(func)
        def wrapper(*a, **ka):
            for hook in self.hooks['before_request']: hook()
            response.output = func(*a, **ka)
            for hook in self.hooks['after_request']: hook()
            return response.output
        return wrapper

    def get(self, path=None, method='GET', **kargs):
        """ Decorator: Bind a function to a GET request path.
            See :meth:'route' for details. """
        return self.route(path, method, **kargs)

    def post(self, path=None, method='POST', **kargs):
        """ Decorator: Bind a function to a POST request path.
            See :meth:'route' for details. """
        return self.route(path, method, **kargs)

    def put(self, path=None, method='PUT', **kargs):
        """ Decorator: Bind a function to a PUT request path.
            See :meth:'route' for details. """
        return self.route(path, method, **kargs)

    def delete(self, path=None, method='DELETE', **kargs):
        """ Decorator: Bind a function to a DELETE request path.
            See :meth:'route' for details. """
        return self.route(path, method, **kargs)

    def error(self, code=500):
        """ Decorator: Register an output handler for a HTTP error code"""
        def wrapper(handler):
            self.error_handler[int(code)] = handler
            return handler
        return wrapper

    def hook(self, name):
        """ Return a decorator that adds a callback to the specified hook. """
        def wrapper(func):
            self.add_hook(name, func)
            return func
        return wrapper

    def add_hook(self, name, func):
        ''' Add a callback from a hook. '''
        if name not in self.hooks:
            raise ValueError("Unknown hook name %s" % name)
        if name in ('after_request'):
            self.hooks[name].insert(0, func)
        else:
            self.hooks[name].append(func)

    def remove_hook(self, name, func):
        ''' Remove a callback from a hook. '''
        if name not in self.hooks:
            raise ValueError("Unknown hook name %s" % name)
        self.hooks[name].remove(func)

    def handle(self, environ):
        """ Execute the handler bound to the specified url and method and return
        its output. If catchall is true, exceptions are catched and returned as
        HTTPError(500) objects. """
        if not self.serve:
            return HTTPError(503, "Server stopped")
        try:
            handler, args = self.match(environ)
            return handler(**args)
        except HTTPResponse, e:
            return e
        except Exception, e:
            if isinstance(e, (KeyboardInterrupt, SystemExit, MemoryError))\
            or not self.catchall:
                raise
            return HTTPError(500, 'Unhandled exception', e, format_exc(10))

    def _cast(self, out, request, response, peek=None):
        """ Try to convert the parameter into something WSGI compatible and set
        correct HTTP headers when possible.
        Support: False, str, unicode, dict, HTTPResponse, HTTPError, file-like,
        iterable of strings and iterable of unicodes
        """
        # Filtered types (recursive, because they may return anything)
        for testtype, filterfunc in self.castfilter:
            if isinstance(out, testtype):
                return self._cast(filterfunc(out), request, response)

        # Empty output is done here
        if not out:
            response.headers['Content-Length'] = 0
            return []
        # Join lists of byte or unicode strings. Mixed lists are NOT supported
        if isinstance(out, (tuple, list))\
        and isinstance(out[0], (bytes, unicode)):
            out = out[0][0:0].join(out) # b'abc'[0:0] -> b''
        # Encode unicode strings
        if isinstance(out, unicode):
            out = out.encode(response.charset)
        # Byte Strings are just returned
        if isinstance(out, bytes):
            response.headers['Content-Length'] = str(len(out))
            return [out]
        # HTTPError or HTTPException (recursive, because they may wrap anything)
        if isinstance(out, HTTPError):
            out.apply(response)
            return self._cast(self.error_handler.get(out.status, repr)(out), request, response)
        if isinstance(out, HTTPResponse):
            out.apply(response)
            return self._cast(out.output, request, response)

        # File-like objects.
        if hasattr(out, 'read'):
            if 'wsgi.file_wrapper' in request.environ:
                return request.environ['wsgi.file_wrapper'](out)
            elif hasattr(out, 'close') or not hasattr(out, '__iter__'):
                return WSGIFileWrapper(out)

        # Handle Iterables. We peek into them to detect their inner type.
        try:
            out = iter(out)
            first = out.next()
            while not first:
                first = out.next()
        except StopIteration:
            return self._cast('', request, response)
        except HTTPResponse, e:
            first = e
        except Exception, e:
            first = HTTPError(500, 'Unhandled exception', e, format_exc(10))
            if isinstance(e, (KeyboardInterrupt, SystemExit, MemoryError))\
            or not self.catchall:
                raise
        # These are the inner types allowed in iterator or generator objects.
        if isinstance(first, HTTPResponse):
            return self._cast(first, request, response)
        if isinstance(first, bytes):
            return itertools.chain([first], out)
        if isinstance(first, unicode):
            return itertools.imap(lambda x: x.encode(response.charset),
                                  itertools.chain([first], out))
        return self._cast(HTTPError(500, 'Unsupported response type: %s'\
                                         % type(first)), request, response)

    def wsgi(self, environ, start_response):
        """ The bottle WSGI-interface. """
        try:
            environ['bottle.app'] = self
            request.bind(environ)
            response.bind()
            out = self.handle(environ)
            out = self._cast(out, request, response)
            # rfc2616 section 4.3
            if response.status in (100, 101, 204, 304) or request.method == 'HEAD':
                if hasattr(out, 'close'): out.close()
                out = []
            status = '%d %s' % (response.status, HTTP_CODES[response.status])
            start_response(status, response.headerlist)
            return out
        except (KeyboardInterrupt, SystemExit, MemoryError):
            raise
        except Exception, e:
            if not self.catchall: raise
            err = '<h1>Critical error while processing request: %s</h1>' \
                  % environ.get('PATH_INFO', '/')
            if DEBUG:
                err += '<h2>Error:</h2>\n<pre>%s</pre>\n' % repr(e)
                err += '<h2>Traceback:</h2>\n<pre>%s</pre>\n' % format_exc(10)
            environ['wsgi.errors'].write(err) #TODO: wsgi.error should not get html
            start_response('500 INTERNAL SERVER ERROR', [('Content-Type', 'text/html')])
            return [tob(err)]
        
    def __call__(self, environ, start_response):
        return self.wsgi(environ, start_response)






###############################################################################
# HTTP and WSGI Tools ##########################################################
###############################################################################

class Request(threading.local, DictMixin):
    """ Represents a single HTTP request using thread-local attributes.
        The Request object wraps a WSGI environment and can be used as such.
    """
    def __init__(self, environ=None):
        """ Create a new Request instance.
        
            You usually don't do this but use the global `bottle.request`
            instance instead.
        """
        self.bind(environ or {},)

    def bind(self, environ):
        """ Bind a new WSGI environment.
            
            This is done automatically for the global `bottle.request`
            instance on every request.
        """
        self.environ = environ
        # These attributes are used anyway, so it is ok to compute them here
        self.path = '/' + environ.get('PATH_INFO', '/').lstrip('/')
        self.method = environ.get('REQUEST_METHOD', 'GET').upper()

    @property
    def _environ(self):
        depr("Request._environ renamed to Request.environ")
        return self.environ

    def copy(self):
        ''' Returns a copy of self '''
        return Request(self.environ.copy())

    def path_shift(self, shift=1):
        ''' Shift path fragments from PATH_INFO to SCRIPT_NAME and vice versa.

           :param shift: The number of path fragments to shift. May be negative
                         to change the shift direction. (default: 1)
        '''
        script_name = self.environ.get('SCRIPT_NAME','/')
        self['SCRIPT_NAME'], self.path = path_shift(script_name, self.path, shift)
        self['PATH_INFO'] = self.path

    def __getitem__(self, key): return self.environ[key]
    def __delitem__(self, key): self[key] = ""; del(self.environ[key])
    def __iter__(self): return iter(self.environ)
    def __len__(self): return len(self.environ)
    def keys(self): return self.environ.keys()
    def __setitem__(self, key, value):
        """ Shortcut for Request.environ.__setitem__ """
        self.environ[key] = value
        todelete = []
        if key in ('PATH_INFO','REQUEST_METHOD'):
            self.bind(self.environ)
        elif key == 'wsgi.input': todelete = ('body','forms','files','params')
        elif key == 'QUERY_STRING': todelete = ('get','params')
        elif key.startswith('HTTP_'): todelete = ('headers', 'cookies')
        for key in todelete:
            if 'bottle.' + key in self.environ:
                del self.environ['bottle.' + key]

    @property
    def query_string(self):
        """ The part of the URL following the '?'. """
        return self.environ.get('QUERY_STRING', '')

    @property
    def fullpath(self):
        """ Request path including SCRIPT_NAME (if present). """
        return self.environ.get('SCRIPT_NAME', '').rstrip('/') + self.path

    @property
    def url(self):
        """ Full URL as requested by the client (computed).

            This value is constructed out of different environment variables
            and includes scheme, host, port, scriptname, path and query string. 
        """
        scheme = self.environ.get('wsgi.url_scheme', 'http')
        host   = self.environ.get('HTTP_X_FORWARDED_HOST')
        host   = host or self.environ.get('HTTP_HOST', None)
        if not host:
            host = self.environ.get('SERVER_NAME')
            port = self.environ.get('SERVER_PORT', '80')
            if (scheme, port) not in (('https','443'), ('http','80')):
                host += ':' + port
        parts = (scheme, host, urlquote(self.fullpath), self.query_string, '')
        return urlunsplit(parts)

    @property
    def content_length(self):
        """ Content-Length header as an integer, -1 if not specified """
        return int(self.environ.get('CONTENT_LENGTH', '') or -1)

    @property
    def header(self):
        depr("The Request.header property was renamed to Request.headers")
        return self.headers

    @DictProperty('environ', 'bottle.headers', read_only=True)
    def headers(self):
        ''' Request HTTP Headers stored in a :cls:`HeaderDict`. '''
        return WSGIHeaderDict(self.environ)

    @DictProperty('environ', 'bottle.get', read_only=True)
    def GET(self):
        """ The QUERY_STRING parsed into an instance of :class:`MultiDict`. """
        data = parse_qs(self.query_string, keep_blank_values=True)
        get = self.environ['bottle.get'] = MultiDict()
        for key, values in data.iteritems():
            for value in values:
                get[key] = value
        return get

    @DictProperty('environ', 'bottle.post', read_only=True)
    def POST(self):
        """ The combined values from :attr:`forms` and :attr:`files`. Values are
            either strings (form values) or instances of
            :class:`cgi.FieldStorage` (file uploads).
        """
        post = MultiDict()
        safe_env = {'QUERY_STRING':''} # Build a safe environment for cgi
        for key in ('REQUEST_METHOD', 'CONTENT_TYPE', 'CONTENT_LENGTH'):
            if key in self.environ: safe_env[key] = self.environ[key]
        if NCTextIOWrapper:
            fb = NCTextIOWrapper(self.body, encoding='ISO-8859-1', newline='\n')
        else:
            fb = self.body
        data = cgi.FieldStorage(fp=fb, environ=safe_env, keep_blank_values=True)
        for item in data.list or []:
            post[item.name] = item if item.filename else item.value
        return post

    @DictProperty('environ', 'bottle.forms', read_only=True)
    def forms(self):
        """ POST form values parsed into an instance of :class:`MultiDict`.

            This property contains form values parsed from an `url-encoded`
            or `multipart/form-data` encoded POST request bidy. The values are
            native strings.
        """
        forms = MultiDict()
        for name, item in self.POST.iterallitems():
            if not hasattr(item, 'filename'):
                forms[name] = item
        return forms

    @DictProperty('environ', 'bottle.files', read_only=True)
    def files(self):
        """ File uploads parsed into an instance of :class:`MultiDict`.

            This property contains file uploads parsed from an
            `multipart/form-data` encoded POST request body. The values are
            instances of :class:`cgi.FieldStorage`.
        """
        files = MultiDict()
        for name, item in self.POST.iterallitems():
            if hasattr(item, 'filename'):
                files[name] = item
        return files
        
    @DictProperty('environ', 'bottle.params', read_only=True)
    def params(self):
        """ A combined :class:`MultiDict` with values from :attr:`forms` and
            :attr:`GET`. File-uploads are not included. """
        params = MultiDict(self.GET)
        for key, value in self.forms.iterallitems():
            params[key] = value
        return params

    @DictProperty('environ', 'bottle.body', read_only=True)
    def _body(self):
        """ The HTTP request body as a seekable file-like object.

            This property returns a copy of the `wsgi.input` stream and should
            be used instead of `environ['wsgi.input']`.
         """
        maxread = max(0, self.content_length)
        stream = self.environ['wsgi.input']
        body = BytesIO() if maxread < MEMFILE_MAX else TemporaryFile(mode='w+b')
        while maxread > 0:
            part = stream.read(min(maxread, MEMFILE_MAX))
            if not part: break
            body.write(part)
            maxread -= len(part)
        self.environ['wsgi.input'] = body
        body.seek(0)
        return body
    
    @property
    def body(self):
        self._body.seek(0)
        return self._body

    @property
    def auth(self): #TODO: Tests and docs. Add support for digest. namedtuple?
        """ HTTP authorization data as a (user, passwd) tuple. (experimental)

            This implementation currently only supports basic auth and returns
            None on errors.
        """
        return parse_auth(self.headers.get('Authorization',''))

    @DictProperty('environ', 'bottle.cookies', read_only=True)
    def COOKIES(self):
        """ Cookies parsed into a dictionary. Secure cookies are NOT decoded
            automatically. See :meth:`get_cookie` for details.
        """
        raw_dict = SimpleCookie(self.headers.get('Cookie',''))
        cookies = {}
        for cookie in raw_dict.itervalues():
            cookies[cookie.key] = cookie.value
        return cookies

    def get_cookie(self, key, secret=None):
        """ Return the content of a cookie. To read a `Secure Cookies`, use the
            same `secret` as used to create the cookie (see
            :meth:`Response.set_cookie`). If anything goes wrong, None is
            returned.
        """
        value = self.COOKIES.get(key)
        if secret and value:
            dec = cookie_decode(value, secret) # (key, value) tuple or None
            return dec[1] if dec and dec[0] == key else None
        return value or None

    @property
    def is_ajax(self):
        ''' True if the request was generated using XMLHttpRequest '''
        #TODO: write tests
        return self.header.get('X-Requested-With') == 'XMLHttpRequest'



class Response(threading.local):
    """ Represents a single HTTP response using thread-local attributes.
    """

    def __init__(self):
        self.bind()

    def bind(self):
        """ Resets the Response object to its factory defaults. """
        self._COOKIES = None
        self.status = 200
        self.headers = HeaderDict()
        self.content_type = 'text/html; charset=UTF-8'

    @property
    def header(self):
        depr("Response.header renamed to Response.headers")
        return self.headers

    def copy(self):
        ''' Returns a copy of self. '''
        copy = Response()
        copy.status = self.status
        copy.headers = self.headers.copy()
        copy.content_type = self.content_type
        return copy

    def wsgiheader(self):
        ''' Returns a wsgi conform list of header/value pairs. '''
        for c in self.COOKIES.values():
            if c.OutputString() not in self.headers.getall('Set-Cookie'):
                self.headers.append('Set-Cookie', c.OutputString())
        # rfc2616 section 10.2.3, 10.3.5
        if self.status in (204, 304) and 'content-type' in self.headers:
            del self.headers['content-type']
        if self.status == 304:
            for h in ('allow', 'content-encoding', 'content-language',
                      'content-length', 'content-md5', 'content-range',
                      'content-type', 'last-modified'): # + c-location, expires?
                if h in self.headers:
                     del self.headers[h]
        return list(self.headers.iterallitems())
    headerlist = property(wsgiheader)

    @property
    def charset(self):
        """ Return the charset specified in the content-type header.
        
            This defaults to `UTF-8`.
        """
        if 'charset=' in self.content_type:
            return self.content_type.split('charset=')[-1].split(';')[0].strip()
        return 'UTF-8'

    @property
    def COOKIES(self):
        """ A dict-like SimpleCookie instance. Use :meth:`set_cookie` instead. """
        if not self._COOKIES:
            self._COOKIES = SimpleCookie()
        return self._COOKIES

    def set_cookie(self, key, value, secret=None, **kargs):
        ''' Add a cookie. If the `secret` parameter is set, this creates a
            `Secure Cookie` (described below).

            :param key: the name of the cookie.
            :param value: the value of the cookie.
            :param secret: required for secure cookies. (default: None)
            :param max_age: maximum age in seconds. (default: None)
            :param expires: a datetime object or UNIX timestamp. (defaut: None)
            :param domain: the domain that is allowed to read the cookie.
              (default: current domain)
            :param path: limits the cookie to a given path (default: /)

            If neither `expires` nor `max_age` are set (default), the cookie
            lasts only as long as the browser is not closed.

            Secure cookies may store any pickle-able object and are
            cryptographically signed to prevent manipulation. Keep in mind that
            cookies are limited to 4kb in most browsers.
            
            Warning: Secure cookies are not encrypted (the client can still see
            the content) and not copy-protected (the client can restore an old
            cookie). The main intention is to make pickling and unpickling
            save, not to store secret information at client side.
        '''
        if secret:
            value = touni(cookie_encode((key, value), secret))
        elif not isinstance(value, basestring):
            raise TypeError('Secret missing for non-string Cookie.')

        self.COOKIES[key] = value
        for k, v in kargs.iteritems():
            self.COOKIES[key][k.replace('_', '-')] = v

    def delete_cookie(self, key, **kwargs):
        ''' Delete a cookie. Be sure to use the same `domain` and `path`
            parameters as used to create the cookie. '''
        kwargs['max_age'] = -1
        kwargs['expires'] = 0
        self.set_cookie(key, '', **kwargs)

    def get_content_type(self):
        """ Current 'Content-Type' header. """
        return self.headers['Content-Type']

    def set_content_type(self, value):
        self.headers['Content-Type'] = value

    content_type = property(get_content_type, set_content_type, None,
                            get_content_type.__doc__)






###############################################################################
# Common Utilities #############################################################
###############################################################################

class MultiDict(DictMixin):
    """ A dict that remembers old values for each key """
    # collections.MutableMapping would be better for Python >= 2.6
    def __init__(self, *a, **k):
        self.dict = dict()
        for k, v in dict(*a, **k).iteritems():
            self[k] = v

    def __len__(self): return len(self.dict)
    def __iter__(self): return iter(self.dict)
    def __contains__(self, key): return key in self.dict
    def __delitem__(self, key): del self.dict[key]
    def keys(self): return self.dict.keys()
    def __getitem__(self, key): return self.get(key, KeyError, -1)
    def __setitem__(self, key, value): self.append(key, value)

    def append(self, key, value): self.dict.setdefault(key, []).append(value)
    def replace(self, key, value): self.dict[key] = [value]
    def getall(self, key): return self.dict.get(key) or []

    def get(self, key, default=None, index=-1):
        if key not in self.dict and default != KeyError:
            return [default][index]
        return self.dict[key][index]

    def iterallitems(self):
        for key, values in self.dict.iteritems():
            for value in values:
                yield key, value


class HeaderDict(MultiDict):
    """ Same as :class:`MultiDict`, but title()s the keys and overwrites by default. """
    def __contains__(self, key): return MultiDict.__contains__(self, self.httpkey(key))
    def __getitem__(self, key): return MultiDict.__getitem__(self, self.httpkey(key))
    def __delitem__(self, key): return MultiDict.__delitem__(self, self.httpkey(key))
    def __setitem__(self, key, value): self.replace(key, value)
    def get(self, key, default=None, index=-1): return MultiDict.get(self, self.httpkey(key), default, index)
    def append(self, key, value): return MultiDict.append(self, self.httpkey(key), str(value))
    def replace(self, key, value): return MultiDict.replace(self, self.httpkey(key), str(value))
    def getall(self, key): return MultiDict.getall(self, self.httpkey(key))
    def httpkey(self, key): return str(key).replace('_','-').title()


class WSGIHeaderDict(DictMixin):
    ''' This dict-like class wraps a WSGI environ dict and provides convenient
        access to HTTP_* fields. Keys and values are native strings
        (2.x bytes or 3.x unicode) and keys are case-insensitive. If the WSGI
        environment contains non-native string values, these are de- or encoded
        using a lossless 'latin1' character set.

        The API will remain stable even on changes to the relevant PEPs.
        Currently PEP 333, 444 and 3333 are supported. (PEP 444 is the only one
        that uses non-native strings.)
     '''

    def __init__(self, environ):
        self.environ = environ

    def _ekey(self, key): # Translate header field name to environ key.
        return 'HTTP_' + key.replace('-','_').upper()

    def raw(self, key, default=None):
        ''' Return the header value as is (may be bytes or unicode). '''
        return self.environ.get(self._ekey(key), default)

    def __getitem__(self, key):
        return tonat(self.environ[self._ekey(key)], 'latin1')

    def __setitem__(self, key, value):
        raise TypeError("%s is read-only." % self.__class__)

    def __delitem__(self, key):
        raise TypeError("%s is read-only." % self.__class__)

    def __iter__(self):
        for key in self.environ:
            if key[:5] == 'HTTP_':
                yield key[5:].replace('_', '-').title()

    def keys(self): return list(self)
    def __len__(self): return len(list(self))
    def __contains__(self, key): return self._ekey(key) in self.environ





class AppStack(list):
    """ A stack implementation. """

    def __call__(self):
        """ Return the current default app. """
        return self[-1]

    def push(self, value=None):
        """ Add a new Bottle instance to the stack """
        if not isinstance(value, Bottle):
            value = Bottle()
        self.append(value)
        return value

class WSGIFileWrapper(object):

   def __init__(self, fp, buffer_size=1024*64):
       self.fp, self.buffer_size = fp, buffer_size
       for attr in ('fileno', 'close', 'read', 'readlines'):
           if hasattr(fp, attr): setattr(self, attr, getattr(fp, attr))

   def __iter__(self):
       read, buff = self.fp.read, self.buffer_size
       while True:
           part = read(buff)
           if not part: break
           yield part






###############################################################################
# Application Helper ###########################################################
###############################################################################

def dict2json(d):
    response.content_type = 'application/json'
    return json_dumps(d)


def abort(code=500, text='Unknown Error: Application stopped.'):
    """ Aborts execution and causes a HTTP error. """
    raise HTTPError(code, text)


def redirect(url, code=303):
    """ Aborts execution and causes a 303 redirect """
    scriptname = request.environ.get('SCRIPT_NAME', '').rstrip('/') + '/'
    location = urljoin(request.url, urljoin(scriptname, url))
    raise HTTPResponse("", status=code, header=dict(Location=location))


def send_file(*a, **k): #BC 0.6.4
    """ Raises the output of static_file(). (deprecated) """
    raise static_file(*a, **k)


def static_file(filename, root, guessmime=True, mimetype=None, download=False):
    """ Opens a file in a safe way and returns a HTTPError object with status
        code 200, 305, 401 or 404. Sets Content-Type, Content-Length and
        Last-Modified header. Obeys If-Modified-Since header and HEAD requests.
    """
    root = os.path.abspath(root) + os.sep
    filename = os.path.abspath(os.path.join(root, filename.strip('/\\')))
    header = dict()

    if not filename.startswith(root):
        return HTTPError(403, "Access denied.")
    if not os.path.exists(filename) or not os.path.isfile(filename):
        return HTTPError(404, "File does not exist.")
    if not os.access(filename, os.R_OK):
        return HTTPError(403, "You do not have permission to access this file.")

    if not mimetype and guessmime:
        header['Content-Type'] = mimetypes.guess_type(filename)[0]
    else:
        header['Content-Type'] = mimetype if mimetype else 'text/plain'

    if download == True:
        download = os.path.basename(filename)
    if download:
        header['Content-Disposition'] = 'attachment; filename="%s"' % download

    stats = os.stat(filename)
    lm = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(stats.st_mtime))
    header['Last-Modified'] = lm
    ims = request.environ.get('HTTP_IF_MODIFIED_SINCE')
    if ims:
        ims = ims.split(";")[0].strip() # IE sends "<date>; length=146"
        ims = parse_date(ims)
        if ims is not None and ims >= int(stats.st_mtime):
            header['Date'] = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
            return HTTPResponse(status=304, header=header)
    header['Content-Length'] = stats.st_size
    if request.method == 'HEAD':
        return HTTPResponse('', header=header)
    else:
        return HTTPResponse(open(filename, 'rb'), header=header)






###############################################################################
# HTTP Utilities and MISC (TODO) ###############################################
###############################################################################

def debug(mode=True):
    """ Change the debug level.
    There is only one debug level supported at the moment."""
    global DEBUG
    DEBUG = bool(mode)


def parse_date(ims):
    """ Parse rfc1123, rfc850 and asctime timestamps and return UTC epoch. """
    try:
        ts = email.utils.parsedate_tz(ims)
        return time.mktime(ts[:8] + (0,)) - (ts[9] or 0) - time.timezone
    except (TypeError, ValueError, IndexError, OverflowError):
        return None


def parse_auth(header):
    """ Parse rfc2617 HTTP authentication header string (basic) and return (user,pass) tuple or None"""
    try:
        method, data = header.split(None, 1)
        if method.lower() == 'basic':
            name, pwd = base64.b64decode(data).split(':', 1)
            return name, pwd
    except (KeyError, ValueError, TypeError):
        return None


def _lscmp(a, b):
    ''' Compares two strings in a cryptographically save way:
        Runtime is not affected by a common prefix. '''
    return not sum(0 if x==y else 1 for x, y in zip(a, b)) and len(a) == len(b)


def cookie_encode(data, key):
    ''' Encode and sign a pickle-able object. Return a (byte) string '''
    msg = base64.b64encode(pickle.dumps(data, -1))
    sig = base64.b64encode(hmac.new(key, msg).digest())
    return tob('!') + sig + tob('?') + msg


def cookie_decode(data, key):
    ''' Verify and decode an encoded string. Return an object or None.'''
    data = tob(data)
    if cookie_is_encoded(data):
        sig, msg = data.split(tob('?'), 1)
        if _lscmp(sig[1:], base64.b64encode(hmac.new(key, msg).digest())):
            return pickle.loads(base64.b64decode(msg))
    return None


def cookie_is_encoded(data):
    ''' Return True if the argument looks like a encoded cookie.'''
    return bool(data.startswith(tob('!')) and tob('?') in data)


def yieldroutes(func):
    """ Return a generator for routes that match the signature (name, args) 
    of the func parameter. This may yield more than one route if the function
    takes optional keyword arguments. The output is best described by example::
    
        a()         -> '/a'
        b(x, y)     -> '/b/:x/:y'
        c(x, y=5)   -> '/c/:x' and '/c/:x/:y'
        d(x=5, y=6) -> '/d' and '/d/:x' and '/d/:x/:y'
    """
    import inspect # Expensive module. Only import if necessary.
    path = '/' + func.__name__.replace('__','/').lstrip('/')
    spec = inspect.getargspec(func)
    argc = len(spec[0]) - len(spec[3] or [])
    path += ('/:%s' * argc) % tuple(spec[0][:argc])
    yield path
    for arg in spec[0][argc:]:
        path += '/:%s' % arg
        yield path

def path_shift(script_name, path_info, shift=1):
    ''' Shift path fragments from PATH_INFO to SCRIPT_NAME and vice versa.

        :return: The modified paths.
        :param script_name: The SCRIPT_NAME path.
        :param script_name: The PATH_INFO path.
        :param shift: The number of path fragments to shift. May be negative to
          change the shift direction. (default: 1)
    '''
    if shift == 0: return script_name, path_info
    pathlist = path_info.strip('/').split('/')
    scriptlist = script_name.strip('/').split('/')
    if pathlist and pathlist[0] == '': pathlist = []
    if scriptlist and scriptlist[0] == '': scriptlist = []
    if shift > 0 and shift <= len(pathlist):
        moved = pathlist[:shift]
        scriptlist = scriptlist + moved
        pathlist = pathlist[shift:]
    elif shift < 0 and shift >= -len(scriptlist):
        moved = scriptlist[shift:]
        pathlist = moved + pathlist
        scriptlist = scriptlist[:shift]
    else:
        empty = 'SCRIPT_NAME' if shift < 0 else 'PATH_INFO'
        raise AssertionError("Cannot shift. Nothing left from %s" % empty)
    new_script_name = '/' + '/'.join(scriptlist)
    new_path_info = '/' + '/'.join(pathlist)
    if path_info.endswith('/') and pathlist: new_path_info += '/'
    return new_script_name, new_path_info



# Decorators
#TODO: Replace default_app() with app()

def validate(**vkargs):
    """
    Validates and manipulates keyword arguments by user defined callables.
    Handles ValueError and missing arguments by raising HTTPError(403).
    """
    def decorator(func):
        def wrapper(**kargs):
            for key, value in vkargs.iteritems():
                if key not in kargs:
                    abort(403, 'Missing parameter: %s' % key)
                try:
                    kargs[key] = value(kargs[key])
                except ValueError:
                    abort(403, 'Wrong parameter format for: %s' % key)
            return func(**kargs)
        return wrapper
    return decorator

def auth_basic(check, realm="private", text="Access denied"):
    ''' Callback decorator to require HTTP auth (basic).
        TODO: Add route(check_auth=...) parameter. '''
    def decorator(func):
      def wrapper(*a, **ka):
        user, password = request.auth or (None, None)
        if user is None or not check(user, password):
          response.headers['WWW-Authenticate'] = 'Basic realm="%s"' % realm
          return HTTPError(401, text)
        return func(*a, **ka)
      return wrapper
    return decorator 


def make_default_app_wrapper(name):
    ''' Return a callable that relays calls to the current default app. '''
    @functools.wraps(getattr(Bottle, name))
    def wrapper(*a, **ka):
        return getattr(app(), name)(*a, **ka)
    return wrapper

for name in 'route get post put delete error mount hook'.split():
    globals()[name] = make_default_app_wrapper(name)
url = make_default_app_wrapper('get_url')
del name

def default():
    depr("The default() decorator is deprecated. Use @error(404) instead.")
    return error(404)






###############################################################################
# Server Adapter ###############################################################
###############################################################################

class ServerAdapter(object):
    quiet = False
    def __init__(self, host='127.0.0.1', port=8080, **config):
        self.options = config
        self.host = host
        self.port = int(port)

    def run(self, handler): # pragma: no cover
        pass
        
    def __repr__(self):
        args = ', '.join(['%s=%s'%(k,repr(v)) for k, v in self.options.items()])
        return "%s(%s)" % (self.__class__.__name__, args)


class CGIServer(ServerAdapter):
    quiet = True
    def run(self, handler): # pragma: no cover
        from wsgiref.handlers import CGIHandler
        CGIHandler().run(handler) # Just ignore host and port here


class FlupFCGIServer(ServerAdapter):
    def run(self, handler): # pragma: no cover
        import flup.server.fcgi
        kwargs = {'bindAddress':(self.host, self.port)}
        kwargs.update(self.options) # allow to override bindAddress and others
        flup.server.fcgi.WSGIServer(handler, **kwargs).run()


class WSGIRefServer(ServerAdapter):
    def run(self, handler): # pragma: no cover
        from wsgiref.simple_server import make_server, WSGIRequestHandler
        if self.quiet:
            class QuietHandler(WSGIRequestHandler):
                def log_request(*args, **kw): pass
            self.options['handler_class'] = QuietHandler
        srv = make_server(self.host, self.port, handler, **self.options)
        srv.serve_forever()


class CherryPyServer(ServerAdapter):
    def run(self, handler): # pragma: no cover
        from cherrypy import wsgiserver
        server = wsgiserver.CherryPyWSGIServer((self.host, self.port), handler)
        server.start()


class PasteServer(ServerAdapter):
    def run(self, handler): # pragma: no cover
        from paste import httpserver
        if not self.quiet:
            from paste.translogger import TransLogger
            handler = TransLogger(handler)
        httpserver.serve(handler, host=self.host, port=str(self.port),
                         **self.options)
                         
class MeinheldServer(ServerAdapter):
    def run(self, handler):
        from meinheld import server
        server.listen((self.host, self.port))
        server.run(handler)

class FapwsServer(ServerAdapter):
    """ Extremely fast webserver using libev. See http://www.fapws.org/ """
    def run(self, handler): # pragma: no cover
        import fapws._evwsgi as evwsgi
        from fapws import base, config
        port = self.port
        if float(config.SERVER_IDENT[-2:]) > 0.4:
            # fapws3 silently changed its API in 0.5
            port = str(port)
        evwsgi.start(self.host, port)
        # fapws3 never releases the GIL. Complain upstream. I tried. No luck.
        if 'BOTTLE_CHILD' in os.environ and not self.quiet:
            print "WARNING: Auto-reloading does not work with Fapws3."
            print "         (Fapws3 breaks python thread support)"
        evwsgi.set_base_module(base)
        def app(environ, start_response):
            environ['wsgi.multiprocess'] = False
            return handler(environ, start_response)
        evwsgi.wsgi_cb(('', app))
        evwsgi.run()


class TornadoServer(ServerAdapter):
    """ The super hyped asynchronous server by facebook. Untested. """
    def run(self, handler): # pragma: no cover
        import tornado.wsgi
        import tornado.httpserver
        import tornado.ioloop
        container = tornado.wsgi.WSGIContainer(handler)
        server = tornado.httpserver.HTTPServer(container)
        server.listen(port=self.port)
        tornado.ioloop.IOLoop.instance().start()


class AppEngineServer(ServerAdapter):
    """ Adapter for Google App Engine. """
    quiet = True
    def run(self, handler):
        from google.appengine.ext.webapp import util
        # A main() function in the handler script enables 'App Caching'.
        # Lets makes sure it is there. This _really_ improves performance.
        module = sys.modules.get('__main__')
        if module and not hasattr(module, 'main'):
            module.main = lambda: util.run_wsgi_app(handler)
        util.run_wsgi_app(handler)


class TwistedServer(ServerAdapter):
    """ Untested. """
    def run(self, handler):
        from twisted.web import server, wsgi
        from twisted.python.threadpool import ThreadPool
        from twisted.internet import reactor
        thread_pool = ThreadPool()
        thread_pool.start()
        reactor.addSystemEventTrigger('after', 'shutdown', thread_pool.stop)
        factory = server.Site(wsgi.WSGIResource(reactor, thread_pool, handler))
        reactor.listenTCP(self.port, factory, interface=self.host)
        reactor.run()


class DieselServer(ServerAdapter):
    """ Untested. """
    def run(self, handler):
        from diesel.protocols.wsgi import WSGIApplication
        app = WSGIApplication(handler, port=self.port)
        app.run()


class GeventServer(ServerAdapter):
    """ Untested. """
    def run(self, handler):
        from gevent import wsgi
        #from gevent.hub import getcurrent
        #self.set_context_ident(getcurrent, weakref=True) # see contextlocal
        wsgi.WSGIServer((self.host, self.port), handler).serve_forever()


class GunicornServer(ServerAdapter):
    """ Untested. """
    def run(self, handler):
        from gunicorn.arbiter import Arbiter
        from gunicorn.config import Config
        handler.cfg = Config({'bind': "%s:%d" % (self.host, self.port), 'workers': 4})
        arbiter = Arbiter(handler)
        arbiter.run()


class EventletServer(ServerAdapter):
    """ Untested """
    def run(self, handler):
        from eventlet import wsgi, listen
        wsgi.server(listen((self.host, self.port)), handler)


class RocketServer(ServerAdapter):
    """ Untested. As requested in issue 63
        https://github.com/defnull/bottle/issues/#issue/63 """
    def run(self, handler):
        from rocket import Rocket
        server = Rocket((self.host, self.port), 'wsgi', { 'wsgi_app' : handler })
        server.start()

class BjoernServer(ServerAdapter):
    """ Screamingly fast server written in C: https://github.com/jonashaag/bjoern """
    def run(self, handler):
        from bjoern import run
        run(handler, self.host, self.port)


class AutoServer(ServerAdapter):
    """ Untested. """
    adapters = [PasteServer, CherryPyServer, TwistedServer, WSGIRefServer]
    def run(self, handler):
        for sa in self.adapters:
            try:
                return sa(self.host, self.port, **self.options).run(handler)
            except ImportError:
                pass


server_names = {
    'cgi': CGIServer,
    'flup': FlupFCGIServer,
    'wsgiref': WSGIRefServer,
    'cherrypy': CherryPyServer,
    'paste': PasteServer,
    'fapws3': FapwsServer,
    'tornado': TornadoServer,
    'gae': AppEngineServer,
    'twisted': TwistedServer,
    'diesel': DieselServer,
    'meinheld': MeinheldServer,
    'gunicorn': GunicornServer,
    'eventlet': EventletServer,
    'gevent': GeventServer,
    'rocket': RocketServer,
    'bjoern' : BjoernServer,
    'auto': AutoServer,
}






###############################################################################
# Application Control ##########################################################
###############################################################################


def _load(target, **vars):
    """ Fetch something from a module. The exact behaviour depends on the the
        target string:

        If the target is a valid python import path (e.g. `package.module`), 
        the rightmost part is returned as a module object.
        If the target contains a colon (e.g. `package.module:var`) the module
        variable specified after the colon is returned.
        If the part after the colon contains any non-alphanumeric characters
        (e.g. `package.module:func(var)`) the result of the expression
        is returned. The expression has access to keyword arguments supplied
        to this function.
        
        Example::
        >>> _load('bottle')
        <module 'bottle' from 'bottle.py'>
        >>> _load('bottle:Bottle')
        <class 'bottle.Bottle'>
        >>> _load('bottle:cookie_encode(v, secret)', v='foo', secret='bar')
        '!F+hN4dQxaDJ4QxxaZ+Z3jw==?gAJVA2Zvb3EBLg=='

    """
    module, target = target.split(":", 1) if ':' in target else (target, None)
    if module not in sys.modules:
        __import__(module)
    if not target:
        return sys.modules[module]
    if target.isalnum():
        return getattr(sys.modules[module], target)
    package_name = module.split('.')[0]
    vars[package_name] = sys.modules[package_name]
    return eval('%s.%s' % (module, target), vars)

def load_app(target):
    """ Load a bottle application based on a target string and return the
        application object.

        If the target is an import path (e.g. package.module), the application
        stack is used to isolate the routes defined in that module.
        If the target contains a colon (e.g. package.module:myapp) the
        module variable specified after the colon is returned instead.
    """
    tmp = app.push() # Create a new "default application"
    rv = _load(target) # Import the target module
    app.remove(tmp) # Remove the temporary added default application
    return rv if isinstance(rv, Bottle) else tmp


def run(app=None, server='wsgiref', host='127.0.0.1', port=8080,
        interval=1, reloader=False, quiet=False, **kargs):
    """ Start a server instance. This method blocks until the server terminates.

        :param app: WSGI application or target string supported by
               :func:`load_app`. (default: :func:`default_app`)
        :param server: Server adapter to use. See :data:`server_names` keys
               for valid names or pass a :class:`ServerAdapter` subclass.
               (default: `wsgiref`)
        :param host: Server address to bind to. Pass ``0.0.0.0`` to listens on
               all interfaces including the external one. (default: 127.0.0.1)
        :param port: Server port to bind to. Values below 1024 require root
               privileges. (default: 8080)
        :param reloader: Start auto-reloading server? (default: False)
        :param interval: Auto-reloader interval in seconds (default: 1)
        :param quiet: Suppress output to stdout and stderr? (default: False)
        :param options: Options passed to the server adapter.
     """
    app = app or default_app()
    if isinstance(app, basestring):
        app = load_app(app)
    if isinstance(server, basestring):
        server = server_names.get(server)
    if isinstance(server, type):
        server = server(host=host, port=port, **kargs)
    if not isinstance(server, ServerAdapter):
        raise RuntimeError("Server must be a subclass of ServerAdapter")
    server.quiet = server.quiet or quiet
    if not server.quiet and not os.environ.get('BOTTLE_CHILD'):
        print "Bottle server starting up (using %s)..." % repr(server)
        print "Listening on http://%s:%d/" % (server.host, server.port)
        print "Use Ctrl-C to quit."
        print
    try:
        if reloader:
            interval = min(interval, 1)
            if os.environ.get('BOTTLE_CHILD'):
                _reloader_child(server, app, interval)
            else:
                _reloader_observer(server, app, interval)
        else:
            server.run(app)
    except KeyboardInterrupt:
        pass
    if not server.quiet and not os.environ.get('BOTTLE_CHILD'):
        print "Shutting down..."


class FileCheckerThread(threading.Thread):
    ''' Thread that periodically checks for changed module files. '''

    def __init__(self, lockfile, interval):
        threading.Thread.__init__(self)
        self.lockfile, self.interval = lockfile, interval
        #1: lockfile to old; 2: lockfile missing
        #3: module file changed; 5: external exit
        self.status = 0

    def run(self):
        exists = os.path.exists
        mtime = lambda path: os.stat(path).st_mtime
        files = dict()
        for module in sys.modules.values():
            path = getattr(module, '__file__', '')
            if path[-4:] in ('.pyo', '.pyc'): path = path[:-1]
            if path and exists(path): files[path] = mtime(path)
        while not self.status:
            for path, lmtime in files.iteritems():
                if not exists(path) or mtime(path) > lmtime:
                    self.status = 3
            if not exists(self.lockfile):
                self.status = 2
            elif mtime(self.lockfile) < time.time() - self.interval - 5:
                self.status = 1
            if not self.status:
                time.sleep(self.interval)
        if self.status != 5:
            thread.interrupt_main()


def _reloader_child(server, app, interval):
    ''' Start the server and check for modified files in a background thread.
        As soon as an update is detected, KeyboardInterrupt is thrown in
        the main thread to exit the server loop. The process exists with status
        code 3 to request a reload by the observer process. If the lockfile
        is not modified in 2*interval second or missing, we assume that the
        observer process died and exit with status code 1 or 2.
    '''
    lockfile = os.environ.get('BOTTLE_LOCKFILE')
    bgcheck = FileCheckerThread(lockfile, interval)
    try:
        bgcheck.start()
        server.run(app)
    except KeyboardInterrupt:
        pass
    bgcheck.status, status = 5, bgcheck.status
    bgcheck.join() # bgcheck.status == 5 --> silent exit
    if status: sys.exit(status)


def _reloader_observer(server, app, interval):
    ''' Start a child process with identical commandline arguments and restart
        it as long as it exists with status code 3. Also create a lockfile and
        touch it (update mtime) every interval seconds.
    '''
    fd, lockfile = tempfile.mkstemp(prefix='bottle-reloader.', suffix='.lock')
    os.close(fd) # We only need this file to exist. We never write to it
    try:
        while os.path.exists(lockfile):
            args = [sys.executable] + sys.argv
            environ = os.environ.copy()
            environ['BOTTLE_CHILD'] = 'true'
            environ['BOTTLE_LOCKFILE'] = lockfile
            p = subprocess.Popen(args, env=environ)
            while p.poll() is None: # Busy wait...
                os.utime(lockfile, None) # I am alive!
                time.sleep(interval)
            if p.poll() != 3:
                if os.path.exists(lockfile): os.unlink(lockfile)
                sys.exit(p.poll())
            elif not server.quiet:
                print "Reloading server..."
    except KeyboardInterrupt:
        pass
    if os.path.exists(lockfile): os.unlink(lockfile)






###############################################################################
# Template Adapters ############################################################
###############################################################################

class TemplateError(HTTPError):
    def __init__(self, message):
        HTTPError.__init__(self, 500, message)


class BaseTemplate(object):
    """ Base class and minimal API for template adapters """
    extentions = ['tpl','html','thtml','stpl']
    settings = {} #used in prepare()
    defaults = {} #used in render()

    def __init__(self, source=None, name=None, lookup=[], encoding='utf8', **settings):
        """ Create a new template.
        If the source parameter (str or buffer) is missing, the name argument
        is used to guess a template filename. Subclasses can assume that
        self.source and/or self.filename are set. Both are strings.
        The lookup, encoding and settings parameters are stored as instance
        variables.
        The lookup parameter stores a list containing directory paths.
        The encoding parameter should be used to decode byte strings or files.
        The settings parameter contains a dict for engine-specific settings.
        """
        self.name = name
        self.source = source.read() if hasattr(source, 'read') else source
        self.filename = source.filename if hasattr(source, 'filename') else None
        self.lookup = map(os.path.abspath, lookup)
        self.encoding = encoding
        self.settings = self.settings.copy() # Copy from class variable
        self.settings.update(settings) # Apply 
        if not self.source and self.name:
            self.filename = self.search(self.name, self.lookup)
            if not self.filename:
                raise TemplateError('Template %s not found.' % repr(name))
        if not self.source and not self.filename:
            raise TemplateError('No template specified.')
        self.prepare(**self.settings)

    @classmethod
    def search(cls, name, lookup=[]):
        """ Search name in all directories specified in lookup.
        First without, then with common extensions. Return first hit. """
        if os.path.isfile(name): return name
        for spath in lookup:
            fname = os.path.join(spath, name)
            if os.path.isfile(fname):
                return fname
            for ext in cls.extentions:
                if os.path.isfile('%s.%s' % (fname, ext)):
                    return '%s.%s' % (fname, ext)

    @classmethod
    def global_config(cls, key, *args):
        ''' This reads or sets the global settings stored in class.settings. '''
        if args:
            cls.settings[key] = args[0]
        else:
            return cls.settings[key]

    def prepare(self, **options):
        """ Run preparations (parsing, caching, ...).
        It should be possible to call this again to refresh a template or to
        update settings.
        """
        raise NotImplementedError

    def render(self, *args, **kwargs):
        """ Render the template with the specified local variables and return
        a single byte or unicode string. If it is a byte string, the encoding
        must match self.encoding. This method must be thread-safe!
        Local variables may be provided in dictionaries (*args)
        or directly, as keywords (**kwargs).
        """
        raise NotImplementedError


class MakoTemplate(BaseTemplate):
    def prepare(self, **options):
        from mako.template import Template
        from mako.lookup import TemplateLookup
        options.update({'input_encoding':self.encoding})
        #TODO: This is a hack... https://github.com/defnull/bottle/issues#issue/8
        mylookup = TemplateLookup(directories=['.']+self.lookup, **options)
        if self.source:
            self.tpl = Template(self.source, lookup=mylookup)
        else: #mako cannot guess extentions. We can, but only at top level...
            name = self.name
            if not os.path.splitext(name)[1]:
                name += os.path.splitext(self.filename)[1]
            self.tpl = mylookup.get_template(name)

    def render(self, *args, **kwargs):
        for dictarg in args: kwargs.update(dictarg)
        _defaults = self.defaults.copy()
        _defaults.update(kwargs)
        return self.tpl.render(**_defaults)


class CheetahTemplate(BaseTemplate):
    def prepare(self, **options):
        from Cheetah.Template import Template
        self.context = threading.local()
        self.context.vars = {}
        options['searchList'] = [self.context.vars]
        if self.source:
            self.tpl = Template(source=self.source, **options)
        else:
            self.tpl = Template(file=self.filename, **options)

    def render(self, *args, **kwargs):
        for dictarg in args: kwargs.update(dictarg)
        self.context.vars.update(self.defaults)
        self.context.vars.update(kwargs)
        out = str(self.tpl)
        self.context.vars.clear()
        return [out]


class Jinja2Template(BaseTemplate):
    def prepare(self, filters=None, tests=None, **kwargs):
        from jinja2 import Environment, FunctionLoader
        if 'prefix' in kwargs: # TODO: to be removed after a while
            raise RuntimeError('The keyword argument `prefix` has been removed. '
                'Use the full jinja2 environment name line_statement_prefix instead.')
        self.env = Environment(loader=FunctionLoader(self.loader), **kwargs)
        if filters: self.env.filters.update(filters)
        if tests: self.env.tests.update(tests)
        if self.source:
            self.tpl = self.env.from_string(self.source)
        else:
            self.tpl = self.env.get_template(self.filename)

    def render(self, *args, **kwargs):
        for dictarg in args: kwargs.update(dictarg)
        _defaults = self.defaults.copy()
        _defaults.update(kwargs)
        return self.tpl.render(**_defaults).encode("utf-8")

    def loader(self, name):
        fname = self.search(name, self.lookup)
        if fname:
            with open(fname, "rb") as f:
                return f.read().decode(self.encoding)

class SimpleTALTemplate(BaseTemplate):
    ''' Untested! '''
    def prepare(self, **options):
        from simpletal import simpleTAL
        # TODO: add option to load METAL files during render
        if self.source:
            self.tpl = simpleTAL.compileHTMLTemplate(self.source)
        else:
            with open(self.filename, 'rb') as fp:
                self.tpl = simpleTAL.compileHTMLTemplate(tonat(fp.read()))

    def render(self, *args, **kwargs):
        from simpletal import simpleTALES
        from StringIO import StringIO
        for dictarg in args: kwargs.update(dictarg)
        # TODO: maybe reuse a context instead of always creating one
        context = simpleTALES.Context()
        for k,v in self.defaults.items():
            context.addGlobal(k, v)
        for k,v in kwargs.items():
            context.addGlobal(k, v)
        output = StringIO()
        self.tpl.expand(context, output)
        return output.getvalue()



class SimpleTemplate(BaseTemplate):
    blocks = ('if','elif','else','try','except','finally','for','while','with','def','class')
    dedent_blocks = ('elif', 'else', 'except', 'finally')

    @lazy_attribute
    def re_pytokens(cls):
        ''' This matches comments and all kinds of quoted strings but does
            NOT match comments (#...) within quoted strings. (trust me) '''
        return re.compile(r'''
            (''(?!')|""(?!")|'{6}|"{6}    # Empty strings (all 4 types)
             |'(?:[^\\']|\\.)+?'          # Single quotes (')
             |"(?:[^\\"]|\\.)+?"          # Double quotes (")
             |'{3}(?:[^\\]|\\.|\n)+?'{3}  # Triple-quoted strings (')
             |"{3}(?:[^\\]|\\.|\n)+?"{3}  # Triple-quoted strings (")
             |\#.*                        # Comments
            )''', re.VERBOSE)

    def prepare(self, escape_func=cgi.escape, noescape=False):
        self.cache = {}
        enc = self.encoding
        self._str = lambda x: touni(x, enc)
        self._escape = lambda x: escape_func(touni(x, enc))
        if noescape:
            self._str, self._escape = self._escape, self._str

    @classmethod
    def split_comment(cls, code):
        """ Removes comments (#...) from python code. """
        if '#' not in code: return code
        #: Remove comments only (leave quoted strings as they are)
        subf = lambda m: '' if m.group(0)[0]=='#' else m.group(0)
        return re.sub(cls.re_pytokens, subf, code)

    @cached_property
    def co(self):
        return compile(self.code, self.filename or '<string>', 'exec')

    @cached_property
    def code(self):
        stack = [] # Current Code indentation
        lineno = 0 # Current line of code
        ptrbuffer = [] # Buffer for printable strings and token tuple instances
        codebuffer = [] # Buffer for generated python code
        multiline = dedent = oneline = False
        template = self.source if self.source else open(self.filename).read()

        def yield_tokens(line):
            for i, part in enumerate(re.split(r'\{\{(.*?)\}\}', line)):
                if i % 2:
                    if part.startswith('!'): yield 'RAW', part[1:]
                    else: yield 'CMD', part
                else: yield 'TXT', part

        def flush(): # Flush the ptrbuffer
            if not ptrbuffer: return
            cline = ''
            for line in ptrbuffer:
                for token, value in line:
                    if token == 'TXT': cline += repr(value)
                    elif token == 'RAW': cline += '_str(%s)' % value
                    elif token == 'CMD': cline += '_escape(%s)' % value
                    cline +=  ', '
                cline = cline[:-2] + '\\\n'
            cline = cline[:-2]
            if cline[:-1].endswith('\\\\\\\\\\n'):
                cline = cline[:-7] + cline[-1] # 'nobr\\\\\n' --> 'nobr'
            cline = '_printlist([' + cline + '])'
            del ptrbuffer[:] # Do this before calling code() again
            code(cline)

        def code(stmt):
            for line in stmt.splitlines():
                codebuffer.append('  ' * len(stack) + line.strip())

        for line in template.splitlines(True):
            lineno += 1
            line = line if isinstance(line, unicode)\
                        else unicode(line, encoding=self.encoding)
            if lineno <= 2:
                m = re.search(r"%.*coding[:=]\s*([-\w\.]+)", line)
                if m: self.encoding = m.group(1)
                if m: line = line.replace('coding','coding (removed)')
            if line.strip()[:2].count('%') == 1:
                line = line.split('%',1)[1].lstrip() # Full line following the %
                cline = self.split_comment(line).strip()
                cmd = re.split(r'[^a-zA-Z0-9_]', cline)[0]
                flush() ##encodig (TODO: why?)
                if cmd in self.blocks or multiline:
                    cmd = multiline or cmd
                    dedent = cmd in self.dedent_blocks # "else:"
                    if dedent and not oneline and not multiline:
                        cmd = stack.pop()
                    code(line)
                    oneline = not cline.endswith(':') # "if 1: pass"
                    multiline = cmd if cline.endswith('\\') else False
                    if not oneline and not multiline:
                        stack.append(cmd)
                elif cmd == 'end' and stack:
                    code('#end(%s) %s' % (stack.pop(), line.strip()[3:]))
                elif cmd == 'include':
                    p = cline.split(None, 2)[1:]
                    if len(p) == 2:
                        code("_=_include(%s, _stdout, %s)" % (repr(p[0]), p[1]))
                    elif p:
                        code("_=_include(%s, _stdout)" % repr(p[0]))
                    else: # Empty %include -> reverse of %rebase
                        code("_printlist(_base)")
                elif cmd == 'rebase':
                    p = cline.split(None, 2)[1:]
                    if len(p) == 2:
                        code("globals()['_rebase']=(%s, dict(%s))" % (repr(p[0]), p[1]))
                    elif p:
                        code("globals()['_rebase']=(%s, {})" % repr(p[0]))
                else:
                    code(line)
            else: # Line starting with text (not '%') or '%%' (escaped)
                if line.strip().startswith('%%'):
                    line = line.replace('%%', '%', 1)
                ptrbuffer.append(yield_tokens(line))
        flush()
        return '\n'.join(codebuffer) + '\n'

    def subtemplate(self, _name, _stdout, *args, **kwargs):
        for dictarg in args: kwargs.update(dictarg)
        if _name not in self.cache:
            self.cache[_name] = self.__class__(name=_name, lookup=self.lookup)
        return self.cache[_name].execute(_stdout, kwargs)

    def execute(self, _stdout, *args, **kwargs):
        for dictarg in args: kwargs.update(dictarg)
        env = self.defaults.copy()
        env.update({'_stdout': _stdout, '_printlist': _stdout.extend,
               '_include': self.subtemplate, '_str': self._str,
               '_escape': self._escape})
        env.update(kwargs)
        eval(self.co, env)
        if '_rebase' in env:
            subtpl, rargs = env['_rebase']
            subtpl = self.__class__(name=subtpl, lookup=self.lookup)
            rargs['_base'] = _stdout[:] #copy stdout
            del _stdout[:] # clear stdout
            return subtpl.execute(_stdout, rargs)
        return env

    def render(self, *args, **kwargs):
        """ Render the template using keyword arguments as local variables. """
        for dictarg in args: kwargs.update(dictarg)
        stdout = []
        self.execute(stdout, kwargs)
        return ''.join(stdout)


def template(*args, **kwargs):
    '''
    Get a rendered template as a string iterator.
    You can use a name, a filename or a template string as first parameter.
    Template rendering arguments can be passed as dictionaries
    or directly (as keyword arguments).
    '''
    tpl = args[0] if args else None
    template_adapter = kwargs.pop('template_adapter', SimpleTemplate)
    if tpl not in TEMPLATES or DEBUG:
        settings = kwargs.pop('template_settings', {})
        lookup = kwargs.pop('template_lookup', TEMPLATE_PATH)
        if isinstance(tpl, template_adapter):
            TEMPLATES[tpl] = tpl
            if settings: TEMPLATES[tpl].prepare(**settings)
        elif "\n" in tpl or "{" in tpl or "%" in tpl or '$' in tpl:
            TEMPLATES[tpl] = template_adapter(source=tpl, lookup=lookup, **settings)
        else:
            TEMPLATES[tpl] = template_adapter(name=tpl, lookup=lookup, **settings)
    if not TEMPLATES[tpl]:
        abort(500, 'Template (%s) not found' % tpl)
    for dictarg in args[1:]: kwargs.update(dictarg)
    return TEMPLATES[tpl].render(kwargs)

mako_template = functools.partial(template, template_adapter=MakoTemplate)
cheetah_template = functools.partial(template, template_adapter=CheetahTemplate)
jinja2_template = functools.partial(template, template_adapter=Jinja2Template)
simpletal_template = functools.partial(template, template_adapter=SimpleTALTemplate)

def view(tpl_name, **defaults):
    ''' Decorator: renders a template for a handler.
        The handler can control its behavior like that:

          - return a dict of template vars to fill out the template
          - return something other than a dict and the view decorator will not
            process the template, but return the handler result as is.
            This includes returning a HTTPResponse(dict) to get,
            for instance, JSON with autojson or other castfilters.
    '''
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            if isinstance(result, (dict, DictMixin)):
                tplvars = defaults.copy()
                tplvars.update(result)
                return template(tpl_name, **tplvars)
            return result
        return wrapper
    return decorator

mako_view = functools.partial(view, template_adapter=MakoTemplate)
cheetah_view = functools.partial(view, template_adapter=CheetahTemplate)
jinja2_view = functools.partial(view, template_adapter=Jinja2Template)
simpletal_view = functools.partial(view, template_adapter=SimpleTALTemplate)





###############################################################################
# Constants and Globals ########################################################
###############################################################################

TEMPLATE_PATH = ['./', './views/']
TEMPLATES = {}
DEBUG = False
MEMFILE_MAX = 1024*100

#: A dict to map HTTP status codes (e.g. 404) to phrases (e.g. 'Not Found')
HTTP_CODES = httplib.responses
HTTP_CODES[418] = "I'm a teapot" # RFC 2324

#: The default template used for error pages. Override with @error()
ERROR_PAGE_TEMPLATE = """
%try:
    %from bottle import DEBUG, HTTP_CODES, request
    %status_name = HTTP_CODES.get(e.status, 'Unknown').title()
    <!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML 2.0//EN">
    <html>
        <head>
            <title>Error {{e.status}}: {{status_name}}</title>
            <style type="text/css">
              html {background-color: #eee; font-family: sans;}
              body {background-color: #fff; border: 1px solid #ddd; padding: 15px; margin: 15px;}
              pre {background-color: #eee; border: 1px solid #ddd; padding: 5px;}
            </style>
        </head>
        <body>
            <h1>Error {{e.status}}: {{status_name}}</h1>
            <p>Sorry, the requested URL <tt>{{request.url}}</tt> caused an error:</p>
            <pre>{{str(e.output)}}</pre>
            %if DEBUG and e.exception:
              <h2>Exception:</h2>
              <pre>{{repr(e.exception)}}</pre>
            %end
            %if DEBUG and e.traceback:
              <h2>Traceback:</h2>
              <pre>{{e.traceback}}</pre>
            %end
        </body>
    </html>
%except ImportError:
    <b>ImportError:</b> Could not generate the error page. Please add bottle to sys.path
%end
"""

#: A thread-save instance of :class:`Request` representing the `current` request.
request = Request()

#: A thread-save instance of :class:`Response` used to build the HTTP response.
response = Response()

#: A thread-save namepsace. Not used by Bottle.
local = threading.local()

# Initialize app stack (create first empty Bottle app)
# BC: 0.6.4 and needed for run()
app = default_app = AppStack()
app.push()

########NEW FILE########
__FILENAME__ = bottlesession
# -*- coding: utf-8 -*-
#  From https://github.com/linsomniac/bottlesession/blob/master/bottlesession.py
#
#  Bottle session manager.  See README for full documentation.
#
#  Written by: Sean Reifschneider <jafo@tummy.com>
#  Changes by: Matthew Holloway <matthew@holloway.co.nz>

from __future__ import with_statement
import os
import os.path
import pickle
import uuid
import hashlib
import time

try:
    import bottle
except ImportError:
    lib_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(os.path.join(lib_directory, 'bottle'))
    try:
        import bottle
    except ImportError:
        sys.stderr.write("Error: Unable to find Bottle libraries in %s. Exiting..." % sys.path)
        sys.exit(0)

class BaseSession(object):
	'''Base class which implements some of the basic functionality required for
	session managers.  Cannot be used directly.

	:param cookie_expires: Expiration time of session ID cookie, either `None`
			if the cookie is not to expire, a number of seconds in the future,
			or a datetime object.  (default: 30 days)
	'''
	def __init__(self, cookie_expires = 86400*30):
		self.cookie_expires = cookie_expires

	def load(self, sessionid):
		raise NotImplementedError

	def save(self, sessionid, data):
		raise NotImplementedError

	def make_session_id(self):
		return str(uuid.uuid4())

	def allocate_new_session_id(self):
		#  retry allocating a unique sessionid
		for i in xrange(100):
			sessionid = self.make_session_id()
			if not self.load(sessionid): return sessionid
		raise ValueError('Unable to allocate unique session')

	def get_session(self):
		#  get existing or create new session identifier
		sessionid = bottle.request.COOKIES.get('sessionid')
		if not sessionid:
			sessionid = self.allocate_new_session_id()
			bottle.response.set_cookie('sessionid', sessionid,
					path = '/', expires = self.cookie_expires)
		#  load existing or create new session
		data = self.load(sessionid)
		if not data:
			data = { 'sessionid' : sessionid, 'valid' : False }
			self.save(data)
		return data


class PickleSession(BaseSession):
	'''Class which stores session information in the file-system.

	:param session_dir: Directory that session information is stored in.
			(default: ``'/tmp'``).
	'''
	def __init__(self, session_dir = '/tmp', *args, **kwargs):
		super(PickleSession, self).__init__(*args, **kwargs)
		self.session_dir = session_dir

	def load(self, sessionid):
		filename = os.path.join(self.session_dir, 'docvert-session-%s' % sessionid)
		if not os.path.exists(filename): return None
		with open(filename, 'r') as fp: session = pickle.load(fp)
		return session

	def save(self, data):
		sessionid = data['sessionid']
		fileName = os.path.join(self.session_dir, 'docvert-session-%s' % sessionid)
		tmpName = fileName + '.' + str(uuid.uuid4())
		with open(tmpName, 'w') as fp: self.session = pickle.dump(data, fp)
		os.rename(tmpName, fileName)


class CookieSession(BaseSession):
	'''Session manager class which stores session in a signed browser cookie.

	:param cookie_name: Name of the cookie to store the session in.
			(default: ``session_data``)
	:param secret: Secret to be used for "secure cookie".  If ``None``,
			attempts will be made to generate a difficult to guess secret.
			However, this is probably only suitable for private web apps, and
			definitely only for a single web server.  You really should be
			using your own secret.  (default: ``None``)
	:param secret_file: File to read the secret from.  If ``secret`` is
			``None`` and ``secret_file`` is set, the first line of this file
			is read, and stripped, to produce the secret.
	'''

	def __init__(self, secret = None, secret_file = None, cookie_name = 'docvert_session', *args, **kwargs):
		super(CookieSession, self).__init__(*args, **kwargs)
		self.cookie_name = cookie_name
		if not secret and secret_file is not None:
			with open(secret_file, 'r') as fp:
				secret = fp.readline().strip()
		if not secret: 	#  generate a difficult to guess secret
			secret = str(uuid.uuid1()).split('-', 1)[1]
			with open('/proc/uptime', 'r') as fp:
				uptime = int(time.time() - float(fp.readline().split()[0]))
				secret += '-' + str(uptime)
			secret = hashlib.sha1(secret).hexdigest()
		self.secret = secret

	def load(self, sessionid):
		cookie = bottle.request.get_cookie(self.cookie_name, secret = self.secret)
		if cookie == None: return {}
		return pickle.loads(cookie)

	def save(self, data):
		bottle.response.set_cookie(
            self.cookie_name,
            pickle.dumps(data),
		    secret = self.secret, path = '/', expires = self.cookie_expires)


########NEW FILE########
__FILENAME__ = exceptions
# exceptions.py - Exceptions used in the operation of a worker pool
# Copyright (c) 2008 Andrey Petrov
#
# This module is part of workerpool and is released under
# the MIT license: http://www.opensource.org/licenses/mit-license.php

class TerminationNotice(Exception):
    "This exception is raised inside a thread when it's time for it to die."
    pass

########NEW FILE########
__FILENAME__ = jobs
# jobs.py - Generic jobs used with the worker pool
# Copyright (c) 2008 Andrey Petrov
#
# This module is part of workerpool and is released under
# the MIT license: http://www.opensource.org/licenses/mit-license.php

from exceptions import TerminationNotice

__all__ = ['Job', 'SuicideJob', 'SimpleJob']

class Job(object):
    "Interface for a Job object."
    def __init__(self):
        pass

    def run(self):
        "The actual task for the job should be implemented here."
        pass

class SuicideJob(Job):
    "A worker receiving this job will commit suicide."
    def run(self, **kw):
        raise TerminationNotice()

class SimpleJob(Job):
    """
    Given a `result` queue, a `method` pointer, and an `args` dictionary or
    list, the method will execute r = method(*args) or r = method(**args), 
    depending on args' type, and perform result.put(r).
    """
    def __init__(self, result, method, args=[]):
        self.result = result
        self.method = method
        self.args = args

    def run(self):
        if isinstance(self.args, list) or isinstance(self.args, tuple):
            r = self.method(*self.args)
        elif isinstance(self.args, dict):
            r = self.method(**self.args)
        self._return(r)

    def _return(self, r):
        "Handle return value by appending to the ``self.result`` queue."
        self.result.put(r)

########NEW FILE########
__FILENAME__ = pools
# workerpool.py - Module for distributing jobs to a pool of worker threads.
# Copyright (c) 2008 Andrey Petrov
#
# This module is part of workerpool and is released under
# the MIT license: http://www.opensource.org/licenses/mit-license.php


from Queue import Queue
if not hasattr(Queue, 'task_done'):
    # Graft Python 2.5's Queue functionality onto Python 2.4's implementation
    # TODO: The extra methods do nothing for now. Make them do something.
    from QueueWrapper import Queue

from workers import Worker
from jobs import SimpleJob, SuicideJob


__all__ = ['WorkerPool', 'default_worker_factory']


def default_worker_factory(job_queue):
    return Worker(job_queue)


class WorkerPool(Queue):
    """
    WorkerPool servers two functions: It is a Queue and a master of Worker
    threads. The Queue accepts Job objects and passes it on to Workers, who are
    initialized during the construction of the pool and by using grow().

    Jobs are inserted into the WorkerPool with the `put` method.
    Hint: Have the Job append its result into a shared queue that the caller
    holds and then the caller reads an expected number of results from it.

    The shutdown() method must be explicitly called to terminate the Worker
    threads when the pool is no longer needed.

    Construction parameters:

    size = 1
        Number of active worker threads the pool should contain.

    maxjobs = 0
        Maximum number of jobs to allow in the queue at a time. Will block on
        `put` if full.

    default_worker = default_worker_factory
        The default worker factory is called with one argument, which is the
        jobs Queue object that it will read from to acquire jobs. The factory
        will produce a Worker object which will be added to the pool.
    """
    def __init__(self, size=1, maxjobs=0, worker_factory=default_worker_factory):
        if not callable(worker_factory):
            raise TypeError("worker_factory must be callable")

        self.worker_factory = worker_factory # Used to build new workers
        self._size = 0 # Number of active workers we have

        # Initialize the Queue
        Queue.__init__(self, maxjobs) # The queue contains job that are read by workers
        self._jobs = self # Pointer to the queue, for backwards compatibility with version 0.9.1 and earlier

        # Hire some workers!
        for i in xrange(size):
            self.grow()

    def grow(self):
        "Add another worker to the pool."
        t = self.worker_factory(self)
        t.start()
        self._size += 1

    def shrink(self):
        "Get rid of one worker from the pool. Raises IndexError if empty."
        if self._size <= 0:
            raise IndexError("pool is already empty")
        self._size -= 1
        self.put(SuicideJob())

    def shutdown(self):
        "Retire the workers."
        for i in xrange(self.size()):
            self.put(SuicideJob())

    def size(self):
        "Approximate number of active workers (could be more if a shrinking is in progress)."
        return self._size

    def map(self, fn, *seq):
        "Perform a map operation distributed among the workers. Will block until done."
        results = Queue()
        args = zip(*seq)
        for seq in args:
            j = SimpleJob(results, fn, seq)
            self.put(j)

        # Aggregate results
        r = []
        for i in xrange(len(args)):
            r.append(results.get())

        return r

    def wait(self):
        "DEPRECATED: Use join() instead."
        self.join()

########NEW FILE########
__FILENAME__ = QueueWrapper
# NewQueue.py - Implements Python 2.5 Queue functionality for Python 2.4
# Copyright (c) 2008 Andrey Petrov
#
# This module is part of workerpool and is released under
# the MIT license: http://www.opensource.org/licenses/mit-license.php

# TODO: The extra methods provided here do nothing for now. Add real functionality to them someday.

from Queue import Queue as OldQueue

__all__ = ['Queue']

class Queue(OldQueue):
    def task_done(self):
        "Does nothing in Python 2.4"
        pass

    def join(self):
        "Does nothing in Python 2.4"
        pass

########NEW FILE########
__FILENAME__ = workers
# workers.py - Worker objects who become members of a worker pool
# Copyright (c) 2008 Andrey Petrov
#
# This module is part of workerpool and is released under
# the MIT license: http://www.opensource.org/licenses/mit-license.php

from threading import Thread
from jobs import Job, SimpleJob
from exceptions import TerminationNotice

__all__ = ['Worker', 'EquippedWorker']

class Worker(Thread):
    """
    A loyal worker who will pull jobs from the `jobs` queue and perform them.

    The run method will get jobs from the `jobs` queue passed into the
    constructor, and execute them. After each job, task_done() must be executed
    on the `jobs` queue in order for the pool to know when no more jobs are
    being processed.
    """

    def __init__(self, jobs):
        self.jobs = jobs
        Thread.__init__(self)

    def run(self):
        "Get jobs from the queue and perform them as they arrive."
        while 1:
            # Sleep until there is a job to perform.
            job = self.jobs.get()

            # Yawn. Time to get some work done.
            try:
                job.run()
                self.jobs.task_done()
            except TerminationNotice:
                self.jobs.task_done()
                break 

class EquippedWorker(Worker):
    """
    Each worker will create an instance of ``toolbox`` and hang on to it during
    its lifetime. This can be used to pass in a resource such as a persistent 
    connections to services that the worker will be using.

    The toolbox factory is called without arguments to produce an instance of
    an object which contains resources necessary for this Worker to perform.
    """
    # TODO: Should a variation of this become the default Worker someday?

    def __init__(self, jobs, toolbox_factory):
        self.toolbox = toolbox_factory()
        Worker.__init__(self, jobs)

    def run(self):
        "Get jobs from the queue and perform them as they arrive."
        while 1:
            job = self.jobs.get()
            try:
                job.run(toolbox=self.toolbox)
                self.jobs.task_done()
            except TerminationNotice:
                self.jobs.task_done()
                break

########NEW FILE########
