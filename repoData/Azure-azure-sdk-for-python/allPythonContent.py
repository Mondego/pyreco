__FILENAME__ = batchclient
#-------------------------------------------------------------------------
# Copyright (c) Microsoft.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#--------------------------------------------------------------------------
import sys
import uuid

from azure import (
    _update_request_uri_query,
    WindowsAzureError,
    WindowsAzureBatchOperationError,
    _get_children_from_path,
    url_unquote,
    _ERROR_CANNOT_FIND_PARTITION_KEY,
    _ERROR_CANNOT_FIND_ROW_KEY,
    _ERROR_INCORRECT_TABLE_IN_BATCH,
    _ERROR_INCORRECT_PARTITION_KEY_IN_BATCH,
    _ERROR_DUPLICATE_ROW_KEY_IN_BATCH,
    _ERROR_BATCH_COMMIT_FAIL,
    )
from azure.http import HTTPError, HTTPRequest, HTTPResponse
from azure.http.httpclient import _HTTPClient
from azure.storage import (
    _update_storage_table_header,
    METADATA_NS,
    _sign_storage_table_request,
    )
from xml.dom import minidom

_DATASERVICES_NS = 'http://schemas.microsoft.com/ado/2007/08/dataservices'

if sys.version_info < (3,):
    def _new_boundary():
        return str(uuid.uuid1())
else:
    def _new_boundary():
        return str(uuid.uuid1()).encode('utf-8')


class _BatchClient(_HTTPClient):

    '''
    This is the class that is used for batch operation for storage table
    service. It only supports one changeset.
    '''

    def __init__(self, service_instance, account_key, account_name,
                 protocol='http'):
        _HTTPClient.__init__(self, service_instance, account_name=account_name,
                             account_key=account_key, protocol=protocol)
        self.is_batch = False
        self.batch_requests = []
        self.batch_table = ''
        self.batch_partition_key = ''
        self.batch_row_keys = []

    def get_request_table(self, request):
        '''
        Extracts table name from request.uri. The request.uri has either
        "/mytable(...)" or "/mytable" format.

        request: the request to insert, update or delete entity
        '''
        if '(' in request.path:
            pos = request.path.find('(')
            return request.path[1:pos]
        else:
            return request.path[1:]

    def get_request_partition_key(self, request):
        '''
        Extracts PartitionKey from request.body if it is a POST request or from
        request.path if it is not a POST request. Only insert operation request
        is a POST request and the PartitionKey is in the request body.

        request: the request to insert, update or delete entity
        '''
        if request.method == 'POST':
            doc = minidom.parseString(request.body)
            part_key = _get_children_from_path(
                doc, 'entry', 'content', (METADATA_NS, 'properties'),
                (_DATASERVICES_NS, 'PartitionKey'))
            if not part_key:
                raise WindowsAzureError(_ERROR_CANNOT_FIND_PARTITION_KEY)
            return part_key[0].firstChild.nodeValue
        else:
            uri = url_unquote(request.path)
            pos1 = uri.find('PartitionKey=\'')
            pos2 = uri.find('\',', pos1)
            if pos1 == -1 or pos2 == -1:
                raise WindowsAzureError(_ERROR_CANNOT_FIND_PARTITION_KEY)
            return uri[pos1 + len('PartitionKey=\''):pos2]

    def get_request_row_key(self, request):
        '''
        Extracts RowKey from request.body if it is a POST request or from
        request.path if it is not a POST request. Only insert operation request
        is a POST request and the Rowkey is in the request body.

        request: the request to insert, update or delete entity
        '''
        if request.method == 'POST':
            doc = minidom.parseString(request.body)
            row_key = _get_children_from_path(
                doc, 'entry', 'content', (METADATA_NS, 'properties'),
                (_DATASERVICES_NS, 'RowKey'))
            if not row_key:
                raise WindowsAzureError(_ERROR_CANNOT_FIND_ROW_KEY)
            return row_key[0].firstChild.nodeValue
        else:
            uri = url_unquote(request.path)
            pos1 = uri.find('RowKey=\'')
            pos2 = uri.find('\')', pos1)
            if pos1 == -1 or pos2 == -1:
                raise WindowsAzureError(_ERROR_CANNOT_FIND_ROW_KEY)
            row_key = uri[pos1 + len('RowKey=\''):pos2]
            return row_key

    def validate_request_table(self, request):
        '''
        Validates that all requests have the same table name. Set the table
        name if it is the first request for the batch operation.

        request: the request to insert, update or delete entity
        '''
        if self.batch_table:
            if self.get_request_table(request) != self.batch_table:
                raise WindowsAzureError(_ERROR_INCORRECT_TABLE_IN_BATCH)
        else:
            self.batch_table = self.get_request_table(request)

    def validate_request_partition_key(self, request):
        '''
        Validates that all requests have the same PartitiionKey. Set the
        PartitionKey if it is the first request for the batch operation.

        request: the request to insert, update or delete entity
        '''
        if self.batch_partition_key:
            if self.get_request_partition_key(request) != \
                self.batch_partition_key:
                raise WindowsAzureError(_ERROR_INCORRECT_PARTITION_KEY_IN_BATCH)
        else:
            self.batch_partition_key = self.get_request_partition_key(request)

    def validate_request_row_key(self, request):
        '''
        Validates that all requests have the different RowKey and adds RowKey
        to existing RowKey list.

        request: the request to insert, update or delete entity
        '''
        if self.batch_row_keys:
            if self.get_request_row_key(request) in self.batch_row_keys:
                raise WindowsAzureError(_ERROR_DUPLICATE_ROW_KEY_IN_BATCH)
        else:
            self.batch_row_keys.append(self.get_request_row_key(request))

    def begin_batch(self):
        '''
        Starts the batch operation. Intializes the batch variables

        is_batch: batch operation flag.
        batch_table: the table name of the batch operation
        batch_partition_key: the PartitionKey of the batch requests.
        batch_row_keys: the RowKey list of adding requests.
        batch_requests: the list of the requests.
        '''
        self.is_batch = True
        self.batch_table = ''
        self.batch_partition_key = ''
        self.batch_row_keys = []
        self.batch_requests = []

    def insert_request_to_batch(self, request):
        '''
        Adds request to batch operation.

        request: the request to insert, update or delete entity
        '''
        self.validate_request_table(request)
        self.validate_request_partition_key(request)
        self.validate_request_row_key(request)
        self.batch_requests.append(request)

    def commit_batch(self):
        ''' Resets batch flag and commits the batch requests. '''
        if self.is_batch:
            self.is_batch = False
            self.commit_batch_requests()

    def commit_batch_requests(self):
        ''' Commits the batch requests. '''

        batch_boundary = b'batch_' + _new_boundary()
        changeset_boundary = b'changeset_' + _new_boundary()

        # Commits batch only the requests list is not empty.
        if self.batch_requests:
            request = HTTPRequest()
            request.method = 'POST'
            request.host = self.batch_requests[0].host
            request.path = '/$batch'
            request.headers = [
                ('Content-Type', 'multipart/mixed; boundary=' + \
                    batch_boundary.decode('utf-8')),
                ('Accept', 'application/atom+xml,application/xml'),
                ('Accept-Charset', 'UTF-8')]

            request.body = b'--' + batch_boundary + b'\n'
            request.body += b'Content-Type: multipart/mixed; boundary='
            request.body += changeset_boundary + b'\n\n'

            content_id = 1

            # Adds each request body to the POST data.
            for batch_request in self.batch_requests:
                request.body += b'--' + changeset_boundary + b'\n'
                request.body += b'Content-Type: application/http\n'
                request.body += b'Content-Transfer-Encoding: binary\n\n'
                request.body += batch_request.method.encode('utf-8')
                request.body += b' http://'
                request.body += batch_request.host.encode('utf-8')
                request.body += batch_request.path.encode('utf-8')
                request.body += b' HTTP/1.1\n'
                request.body += b'Content-ID: '
                request.body += str(content_id).encode('utf-8') + b'\n'
                content_id += 1

                # Add different headers for different type requests.
                if not batch_request.method == 'DELETE':
                    request.body += \
                        b'Content-Type: application/atom+xml;type=entry\n'
                    for name, value in batch_request.headers:
                        if name == 'If-Match':
                            request.body += name.encode('utf-8') + b': '
                            request.body += value.encode('utf-8') + b'\n'
                            break
                    request.body += b'Content-Length: '
                    request.body += str(len(batch_request.body)).encode('utf-8')
                    request.body += b'\n\n'
                    request.body += batch_request.body + b'\n'
                else:
                    for name, value in batch_request.headers:
                        # If-Match should be already included in
                        # batch_request.headers, but in case it is missing,
                        # just add it.
                        if name == 'If-Match':
                            request.body += name.encode('utf-8') + b': '
                            request.body += value.encode('utf-8') + b'\n\n'
                            break
                    else:
                        request.body += b'If-Match: *\n\n'

            request.body += b'--' + changeset_boundary + b'--' + b'\n'
            request.body += b'--' + batch_boundary + b'--'

            request.path, request.query = _update_request_uri_query(request)
            request.headers = _update_storage_table_header(request)
            auth = _sign_storage_table_request(request,
                                               self.account_name,
                                               self.account_key)
            request.headers.append(('Authorization', auth))

            # Submit the whole request as batch request.
            response = self.perform_request(request)
            if response.status >= 300:
                raise HTTPError(response.status,
                                _ERROR_BATCH_COMMIT_FAIL,
                                self.respheader,
                                response.body)

            # http://www.odata.org/documentation/odata-version-2-0/batch-processing/
            # The body of a ChangeSet response is either a response for all the
            # successfully processed change request within the ChangeSet,
            # formatted exactly as it would have appeared outside of a batch, 
            # or a single response indicating a failure of the entire ChangeSet.
            responses = self._parse_batch_response(response.body)
            if responses and responses[0].status >= 300:
                self._report_batch_error(responses[0])

    def cancel_batch(self):
        ''' Resets the batch flag. '''
        self.is_batch = False

    def _parse_batch_response(self, body):
        parts = body.split(b'--changesetresponse_')

        responses = []
        for part in parts:
            httpLocation = part.find(b'HTTP/')
            if httpLocation > 0:
                response = self._parse_batch_response_part(part[httpLocation:])
                responses.append(response)

        return responses

    def _parse_batch_response_part(self, part):
        lines = part.splitlines();

        # First line is the HTTP status/reason
        status, _, reason = lines[0].partition(b' ')[2].partition(b' ')

        # Followed by headers and body
        headers = []
        body = b''
        isBody = False
        for line in lines[1:]:
            if line == b'' and not isBody:
                isBody = True
            elif isBody:
                body += line
            else:
                headerName, _, headerVal = line.partition(b':')
                headers.append((headerName.lower(), headerVal))

        return HTTPResponse(int(status), reason.strip(), headers, body)

    def _report_batch_error(self, response):
        xml = response.body.decode('utf-8')
        doc = minidom.parseString(xml)

        n = _get_children_from_path(doc, (METADATA_NS, 'error'), 'code')
        code = n[0].firstChild.nodeValue if n and n[0].firstChild else ''

        n = _get_children_from_path(doc, (METADATA_NS, 'error'), 'message')
        message = n[0].firstChild.nodeValue if n and n[0].firstChild else xml

        raise WindowsAzureBatchOperationError(message, code)

########NEW FILE########
__FILENAME__ = httpclient
#-------------------------------------------------------------------------
# Copyright (c) Microsoft.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#--------------------------------------------------------------------------
import base64
import os
import sys

if sys.version_info < (3,):
    from httplib import (
        HTTPSConnection,
        HTTPConnection,
        HTTP_PORT,
        HTTPS_PORT,
        )
else:
    from http.client import (
        HTTPSConnection,
        HTTPConnection,
        HTTP_PORT,
        HTTPS_PORT,
        )

from azure.http import HTTPError, HTTPResponse
from azure import _USER_AGENT_STRING


class _HTTPClient(object):

    '''
    Takes the request and sends it to cloud service and returns the response.
    '''

    def __init__(self, service_instance, cert_file=None, account_name=None,
                 account_key=None, service_namespace=None, issuer=None,
                 protocol='https'):
        '''
        service_instance: service client instance.
        cert_file:
            certificate file name/location. This is only used in hosted
            service management.
        account_name: the storage account.
        account_key:
            the storage account access key for storage services or servicebus
            access key for service bus service.
        service_namespace: the service namespace for service bus.
        issuer: the issuer for service bus service.
        '''
        self.service_instance = service_instance
        self.status = None
        self.respheader = None
        self.message = None
        self.cert_file = cert_file
        self.account_name = account_name
        self.account_key = account_key
        self.service_namespace = service_namespace
        self.issuer = issuer
        self.protocol = protocol
        self.proxy_host = None
        self.proxy_port = None
        self.proxy_user = None
        self.proxy_password = None
        self.use_httplib = self.should_use_httplib()

    def should_use_httplib(self):
        if sys.platform.lower().startswith('win') and self.cert_file:
            # On Windows, auto-detect between Windows Store Certificate
            # (winhttp) and OpenSSL .pem certificate file (httplib).
            #
            # We used to only support certificates installed in the Windows
            # Certificate Store.
            #   cert_file example: CURRENT_USER\my\CertificateName
            #
            # We now support using an OpenSSL .pem certificate file,
            # for a consistent experience across all platforms.
            #   cert_file example: account\certificate.pem
            #
            # When using OpenSSL .pem certificate file on Windows, make sure
            # you are on CPython 2.7.4 or later.

            # If it's not an existing file on disk, then treat it as a path in
            # the Windows Certificate Store, which means we can't use httplib.
            if not os.path.isfile(self.cert_file):
                return False

        return True

    def set_proxy(self, host, port, user, password):
        '''
        Sets the proxy server host and port for the HTTP CONNECT Tunnelling.

        host: Address of the proxy. Ex: '192.168.0.100'
        port: Port of the proxy. Ex: 6000
        user: User for proxy authorization.
        password: Password for proxy authorization.
        '''
        self.proxy_host = host
        self.proxy_port = port
        self.proxy_user = user
        self.proxy_password = password

    def get_connection(self, request):
        ''' Create connection for the request. '''
        protocol = request.protocol_override \
            if request.protocol_override else self.protocol
        target_host = request.host
        target_port = HTTP_PORT if protocol == 'http' else HTTPS_PORT

        if not self.use_httplib:
            import azure.http.winhttp
            connection = azure.http.winhttp._HTTPConnection(
                target_host, cert_file=self.cert_file, protocol=protocol)
            proxy_host = self.proxy_host
            proxy_port = self.proxy_port
        else:
            if ':' in target_host:
                target_host, _, target_port = target_host.rpartition(':')
            if self.proxy_host:
                proxy_host = target_host
                proxy_port = target_port
                host = self.proxy_host
                port = self.proxy_port
            else:
                host = target_host
                port = target_port

            if protocol == 'http':
                connection = HTTPConnection(host, int(port))
            else:
                connection = HTTPSConnection(
                    host, int(port), cert_file=self.cert_file)

        if self.proxy_host:
            headers = None
            if self.proxy_user and self.proxy_password:
                auth = base64.encodestring(
                    "{0}:{1}".format(self.proxy_user, self.proxy_password))
                headers = {'Proxy-Authorization': 'Basic {0}'.format(auth)}
            connection.set_tunnel(proxy_host, int(proxy_port), headers)

        return connection

    def send_request_headers(self, connection, request_headers):
        if self.use_httplib:
            if self.proxy_host:
                for i in connection._buffer:
                    if i.startswith("Host: "):
                        connection._buffer.remove(i)
                connection.putheader(
                    'Host', "{0}:{1}".format(connection._tunnel_host,
                                             connection._tunnel_port))

        for name, value in request_headers:
            if value:
                connection.putheader(name, value)

        connection.putheader('User-Agent', _USER_AGENT_STRING)
        connection.endheaders()

    def send_request_body(self, connection, request_body):
        if request_body:
            assert isinstance(request_body, bytes)
            connection.send(request_body)
        elif (not isinstance(connection, HTTPSConnection) and
              not isinstance(connection, HTTPConnection)):
            connection.send(None)

    def perform_request(self, request):
        ''' Sends request to cloud service server and return the response. '''
        connection = self.get_connection(request)
        try:
            connection.putrequest(request.method, request.path)

            if not self.use_httplib:
                if self.proxy_host and self.proxy_user:
                    connection.set_proxy_credentials(
                        self.proxy_user, self.proxy_password)

            self.send_request_headers(connection, request.headers)
            self.send_request_body(connection, request.body)

            resp = connection.getresponse()
            self.status = int(resp.status)
            self.message = resp.reason
            self.respheader = headers = resp.getheaders()

            # for consistency across platforms, make header names lowercase
            for i, value in enumerate(headers):
                headers[i] = (value[0].lower(), value[1])

            respbody = None
            if resp.length is None:
                respbody = resp.read()
            elif resp.length > 0:
                respbody = resp.read(resp.length)

            response = HTTPResponse(
                int(resp.status), resp.reason, headers, respbody)
            if self.status >= 300:
                raise HTTPError(self.status, self.message,
                                self.respheader, respbody)

            return response
        finally:
            connection.close()

########NEW FILE########
__FILENAME__ = winhttp
#-------------------------------------------------------------------------
# Copyright (c) Microsoft.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#--------------------------------------------------------------------------
from ctypes import (
    c_void_p,
    c_long,
    c_ulong,
    c_longlong,
    c_ulonglong,
    c_short,
    c_ushort,
    c_wchar_p,
    c_byte,
    byref,
    Structure,
    Union,
    POINTER,
    WINFUNCTYPE,
    HRESULT,
    oledll,
    WinDLL,
    )
import ctypes
import sys

if sys.version_info >= (3,):
    def unicode(text):
        return text

#------------------------------------------------------------------------------
#  Constants that are used in COM operations
VT_EMPTY = 0
VT_NULL = 1
VT_I2 = 2
VT_I4 = 3
VT_BSTR = 8
VT_BOOL = 11
VT_I1 = 16
VT_UI1 = 17
VT_UI2 = 18
VT_UI4 = 19
VT_I8 = 20
VT_UI8 = 21
VT_ARRAY = 8192

HTTPREQUEST_PROXYSETTING_PROXY = 2
HTTPREQUEST_SETCREDENTIALS_FOR_PROXY = 1

HTTPREQUEST_PROXY_SETTING = c_long
HTTPREQUEST_SETCREDENTIALS_FLAGS = c_long
#------------------------------------------------------------------------------
# Com related APIs that are used.
_ole32 = oledll.ole32
_oleaut32 = WinDLL('oleaut32')
_CLSIDFromString = _ole32.CLSIDFromString
_CoInitialize = _ole32.CoInitialize
_CoInitialize.argtypes = [c_void_p]

_CoCreateInstance = _ole32.CoCreateInstance

_SysAllocString = _oleaut32.SysAllocString
_SysAllocString.restype = c_void_p
_SysAllocString.argtypes = [c_wchar_p]

_SysFreeString = _oleaut32.SysFreeString
_SysFreeString.argtypes = [c_void_p]

# SAFEARRAY*
# SafeArrayCreateVector(_In_ VARTYPE vt,_In_ LONG lLbound,_In_ ULONG
# cElements);
_SafeArrayCreateVector = _oleaut32.SafeArrayCreateVector
_SafeArrayCreateVector.restype = c_void_p
_SafeArrayCreateVector.argtypes = [c_ushort, c_long, c_ulong]

# HRESULT
# SafeArrayAccessData(_In_ SAFEARRAY *psa, _Out_ void **ppvData);
_SafeArrayAccessData = _oleaut32.SafeArrayAccessData
_SafeArrayAccessData.argtypes = [c_void_p, POINTER(c_void_p)]

# HRESULT
# SafeArrayUnaccessData(_In_ SAFEARRAY *psa);
_SafeArrayUnaccessData = _oleaut32.SafeArrayUnaccessData
_SafeArrayUnaccessData.argtypes = [c_void_p]

# HRESULT
# SafeArrayGetUBound(_In_ SAFEARRAY *psa, _In_ UINT nDim, _Out_ LONG
# *plUbound);
_SafeArrayGetUBound = _oleaut32.SafeArrayGetUBound
_SafeArrayGetUBound.argtypes = [c_void_p, c_ulong, POINTER(c_long)]


#------------------------------------------------------------------------------

class BSTR(c_wchar_p):

    ''' BSTR class in python. '''

    def __init__(self, value):
        super(BSTR, self).__init__(_SysAllocString(value))

    def __del__(self):
        _SysFreeString(self)


class VARIANT(Structure):

    '''
    VARIANT structure in python. Does not match the definition in
    MSDN exactly & it is only mapping the used fields.  Field names are also
    slighty different.
    '''

    class _tagData(Union):

        class _tagRecord(Structure):
            _fields_ = [('pvoid', c_void_p), ('precord', c_void_p)]

        _fields_ = [('llval', c_longlong),
                    ('ullval', c_ulonglong),
                    ('lval', c_long),
                    ('ulval', c_ulong),
                    ('ival', c_short),
                    ('boolval', c_ushort),
                    ('bstrval', BSTR),
                    ('parray', c_void_p),
                    ('record', _tagRecord)]

    _fields_ = [('vt', c_ushort),
                ('wReserved1', c_ushort),
                ('wReserved2', c_ushort),
                ('wReserved3', c_ushort),
                ('vdata', _tagData)]

    @staticmethod
    def create_empty():
        variant = VARIANT()
        variant.vt = VT_EMPTY
        variant.vdata.llval = 0
        return variant

    @staticmethod
    def create_safearray_from_str(text):
        variant = VARIANT()
        variant.vt = VT_ARRAY | VT_UI1

        length = len(text)
        variant.vdata.parray = _SafeArrayCreateVector(VT_UI1, 0, length)
        pvdata = c_void_p()
        _SafeArrayAccessData(variant.vdata.parray, byref(pvdata))
        ctypes.memmove(pvdata, text, length)
        _SafeArrayUnaccessData(variant.vdata.parray)

        return variant

    @staticmethod
    def create_bstr_from_str(text):
        variant = VARIANT()
        variant.vt = VT_BSTR
        variant.vdata.bstrval = BSTR(text)
        return variant

    @staticmethod
    def create_bool_false():
        variant = VARIANT()
        variant.vt = VT_BOOL
        variant.vdata.boolval = 0
        return variant

    def is_safearray_of_bytes(self):
        return self.vt == VT_ARRAY | VT_UI1

    def str_from_safearray(self):
        assert self.vt == VT_ARRAY | VT_UI1
        pvdata = c_void_p()
        count = c_long()
        _SafeArrayGetUBound(self.vdata.parray, 1, byref(count))
        count = c_long(count.value + 1)
        _SafeArrayAccessData(self.vdata.parray, byref(pvdata))
        text = ctypes.string_at(pvdata, count)
        _SafeArrayUnaccessData(self.vdata.parray)
        return text

    def __del__(self):
        _VariantClear(self)

# HRESULT VariantClear(_Inout_ VARIANTARG *pvarg);
_VariantClear = _oleaut32.VariantClear
_VariantClear.argtypes = [POINTER(VARIANT)]


class GUID(Structure):

    ''' GUID structure in python. '''

    _fields_ = [("data1", c_ulong),
                ("data2", c_ushort),
                ("data3", c_ushort),
                ("data4", c_byte * 8)]

    def __init__(self, name=None):
        if name is not None:
            _CLSIDFromString(unicode(name), byref(self))


class _WinHttpRequest(c_void_p):

    '''
    Maps the Com API to Python class functions. Not all methods in
    IWinHttpWebRequest are mapped - only the methods we use.
    '''
    _AddRef = WINFUNCTYPE(c_long) \
        (1, 'AddRef')
    _Release = WINFUNCTYPE(c_long) \
        (2, 'Release')
    _SetProxy = WINFUNCTYPE(HRESULT,
                            HTTPREQUEST_PROXY_SETTING,
                            VARIANT,
                            VARIANT) \
        (7, 'SetProxy')
    _SetCredentials = WINFUNCTYPE(HRESULT,
                                  BSTR,
                                  BSTR,
                                  HTTPREQUEST_SETCREDENTIALS_FLAGS) \
        (8, 'SetCredentials')
    _Open = WINFUNCTYPE(HRESULT, BSTR, BSTR, VARIANT) \
        (9, 'Open')
    _SetRequestHeader = WINFUNCTYPE(HRESULT, BSTR, BSTR) \
        (10, 'SetRequestHeader')
    _GetResponseHeader = WINFUNCTYPE(HRESULT, BSTR, POINTER(c_void_p)) \
        (11, 'GetResponseHeader')
    _GetAllResponseHeaders = WINFUNCTYPE(HRESULT, POINTER(c_void_p)) \
        (12, 'GetAllResponseHeaders')
    _Send = WINFUNCTYPE(HRESULT, VARIANT) \
        (13, 'Send')
    _Status = WINFUNCTYPE(HRESULT, POINTER(c_long)) \
        (14, 'Status')
    _StatusText = WINFUNCTYPE(HRESULT, POINTER(c_void_p)) \
        (15, 'StatusText')
    _ResponseText = WINFUNCTYPE(HRESULT, POINTER(c_void_p)) \
        (16, 'ResponseText')
    _ResponseBody = WINFUNCTYPE(HRESULT, POINTER(VARIANT)) \
        (17, 'ResponseBody')
    _ResponseStream = WINFUNCTYPE(HRESULT, POINTER(VARIANT)) \
        (18, 'ResponseStream')
    _WaitForResponse = WINFUNCTYPE(HRESULT, VARIANT, POINTER(c_ushort)) \
        (21, 'WaitForResponse')
    _Abort = WINFUNCTYPE(HRESULT) \
        (22, 'Abort')
    _SetTimeouts = WINFUNCTYPE(HRESULT, c_long, c_long, c_long, c_long) \
        (23, 'SetTimeouts')
    _SetClientCertificate = WINFUNCTYPE(HRESULT, BSTR) \
        (24, 'SetClientCertificate')

    def open(self, method, url):
        '''
        Opens the request.

        method: the request VERB 'GET', 'POST', etc.
        url: the url to connect
        '''
        _WinHttpRequest._SetTimeouts(self, 0, 65000, 65000, 65000)

        flag = VARIANT.create_bool_false()
        _method = BSTR(method)
        _url = BSTR(url)
        _WinHttpRequest._Open(self, _method, _url, flag)

    def set_request_header(self, name, value):
        ''' Sets the request header. '''

        _name = BSTR(name)
        _value = BSTR(value)
        _WinHttpRequest._SetRequestHeader(self, _name, _value)

    def get_all_response_headers(self):
        ''' Gets back all response headers. '''

        bstr_headers = c_void_p()
        _WinHttpRequest._GetAllResponseHeaders(self, byref(bstr_headers))
        bstr_headers = ctypes.cast(bstr_headers, c_wchar_p)
        headers = bstr_headers.value
        _SysFreeString(bstr_headers)
        return headers

    def send(self, request=None):
        ''' Sends the request body. '''

        # Sends VT_EMPTY if it is GET, HEAD request.
        if request is None:
            var_empty = VARIANT.create_empty()
            _WinHttpRequest._Send(self, var_empty)
        else:  # Sends request body as SAFEArray.
            _request = VARIANT.create_safearray_from_str(request)
            _WinHttpRequest._Send(self, _request)

    def status(self):
        ''' Gets status of response. '''

        status = c_long()
        _WinHttpRequest._Status(self, byref(status))
        return int(status.value)

    def status_text(self):
        ''' Gets status text of response. '''

        bstr_status_text = c_void_p()
        _WinHttpRequest._StatusText(self, byref(bstr_status_text))
        bstr_status_text = ctypes.cast(bstr_status_text, c_wchar_p)
        status_text = bstr_status_text.value
        _SysFreeString(bstr_status_text)
        return status_text

    def response_body(self):
        '''
        Gets response body as a SAFEARRAY and converts the SAFEARRAY to str.
        If it is an xml file, it always contains 3 characters before <?xml,
        so we remove them.
        '''
        var_respbody = VARIANT()
        _WinHttpRequest._ResponseBody(self, byref(var_respbody))
        if var_respbody.is_safearray_of_bytes():
            respbody = var_respbody.str_from_safearray()
            if respbody[3:].startswith(b'<?xml') and\
               respbody.startswith(b'\xef\xbb\xbf'):
                respbody = respbody[3:]
            return respbody
        else:
            return ''

    def set_client_certificate(self, certificate):
        '''Sets client certificate for the request. '''
        _certificate = BSTR(certificate)
        _WinHttpRequest._SetClientCertificate(self, _certificate)

    def set_tunnel(self, host, port):
        ''' Sets up the host and the port for the HTTP CONNECT Tunnelling.'''
        url = host
        if port:
            url = url + u':' + port

        var_host = VARIANT.create_bstr_from_str(url)
        var_empty = VARIANT.create_empty()

        _WinHttpRequest._SetProxy(
            self, HTTPREQUEST_PROXYSETTING_PROXY, var_host, var_empty)

    def set_proxy_credentials(self, user, password):
        _WinHttpRequest._SetCredentials(
            self, BSTR(user), BSTR(password),
            HTTPREQUEST_SETCREDENTIALS_FOR_PROXY)

    def __del__(self):
        if self.value is not None:
            _WinHttpRequest._Release(self)


class _Response(object):

    ''' Response class corresponding to the response returned from httplib
    HTTPConnection. '''

    def __init__(self, _status, _status_text, _length, _headers, _respbody):
        self.status = _status
        self.reason = _status_text
        self.length = _length
        self.headers = _headers
        self.respbody = _respbody

    def getheaders(self):
        '''Returns response headers.'''
        return self.headers

    def read(self, _length):
        '''Returns resonse body. '''
        return self.respbody[:_length]


class _HTTPConnection(object):

    ''' Class corresponding to httplib HTTPConnection class. '''

    def __init__(self, host, cert_file=None, key_file=None, protocol='http'):
        ''' initialize the IWinHttpWebRequest Com Object.'''
        self.host = unicode(host)
        self.cert_file = cert_file
        self._httprequest = _WinHttpRequest()
        self.protocol = protocol
        clsid = GUID('{2087C2F4-2CEF-4953-A8AB-66779B670495}')
        iid = GUID('{016FE2EC-B2C8-45F8-B23B-39E53A75396B}')
        _CoInitialize(None)
        _CoCreateInstance(byref(clsid), 0, 1, byref(iid),
                          byref(self._httprequest))

    def close(self):
        pass

    def set_tunnel(self, host, port=None, headers=None):
        ''' Sets up the host and the port for the HTTP CONNECT Tunnelling. '''
        self._httprequest.set_tunnel(unicode(host), unicode(str(port)))

    def set_proxy_credentials(self, user, password):
        self._httprequest.set_proxy_credentials(
            unicode(user), unicode(password))

    def putrequest(self, method, uri):
        ''' Connects to host and sends the request. '''

        protocol = unicode(self.protocol + '://')
        url = protocol + self.host + unicode(uri)
        self._httprequest.open(unicode(method), url)

        # sets certificate for the connection if cert_file is set.
        if self.cert_file is not None:
            self._httprequest.set_client_certificate(unicode(self.cert_file))

    def putheader(self, name, value):
        ''' Sends the headers of request. '''
        if sys.version_info < (3,):
            name = str(name).decode('utf-8')
            value = str(value).decode('utf-8')
        self._httprequest.set_request_header(name, value)

    def endheaders(self):
        ''' No operation. Exists only to provide the same interface of httplib
        HTTPConnection.'''
        pass

    def send(self, request_body):
        ''' Sends request body. '''
        if not request_body:
            self._httprequest.send()
        else:
            self._httprequest.send(request_body)

    def getresponse(self):
        ''' Gets the response and generates the _Response object'''
        status = self._httprequest.status()
        status_text = self._httprequest.status_text()

        resp_headers = self._httprequest.get_all_response_headers()
        fixed_headers = []
        for resp_header in resp_headers.split('\n'):
            if (resp_header.startswith('\t') or\
                resp_header.startswith(' ')) and fixed_headers:
                # append to previous header
                fixed_headers[-1] += resp_header
            else:
                fixed_headers.append(resp_header)

        headers = []
        for resp_header in fixed_headers:
            if ':' in resp_header:
                pos = resp_header.find(':')
                headers.append(
                    (resp_header[:pos].lower(), resp_header[pos + 1:].strip()))

        body = self._httprequest.response_body()
        length = len(body)

        return _Response(status, status_text, length, headers, body)

########NEW FILE########
__FILENAME__ = servicebusservice
#-------------------------------------------------------------------------
# Copyright (c) Microsoft.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#--------------------------------------------------------------------------
import os
import time

from azure import (
    WindowsAzureError,
    SERVICE_BUS_HOST_BASE,
    _convert_response_to_feeds,
    _dont_fail_not_exist,
    _dont_fail_on_exist,
    _get_request_body,
    _get_request_body_bytes_only,
    _int_or_none,
    _str,
    _update_request_uri_query,
    url_quote,
    url_unquote,
    _validate_not_none,
    )
from azure.http import (
    HTTPError,
    HTTPRequest,
    )
from azure.http.httpclient import _HTTPClient
from azure.servicebus import (
    AZURE_SERVICEBUS_NAMESPACE,
    AZURE_SERVICEBUS_ACCESS_KEY,
    AZURE_SERVICEBUS_ISSUER,
    _convert_topic_to_xml,
    _convert_response_to_topic,
    _convert_queue_to_xml,
    _convert_response_to_queue,
    _convert_subscription_to_xml,
    _convert_response_to_subscription,
    _convert_rule_to_xml,
    _convert_response_to_rule,
    _convert_xml_to_queue,
    _convert_xml_to_topic,
    _convert_xml_to_subscription,
    _convert_xml_to_rule,
    _create_message,
    _service_bus_error_handler,
    )

# Token cache for Authentication
# Shared by the different instances of ServiceBusService
_tokens = {}


class ServiceBusService(object):

    def __init__(self, service_namespace=None, account_key=None, issuer=None,
                 x_ms_version='2011-06-01', host_base=SERVICE_BUS_HOST_BASE):
        # x_ms_version is not used, but the parameter is kept for backwards
        # compatibility
        self.requestid = None
        self.service_namespace = service_namespace
        self.account_key = account_key
        self.issuer = issuer
        self.host_base = host_base

        # Get service namespace, account key and issuer.
        # If they are set when constructing, then use them, else find them
        # from environment variables.
        if not self.service_namespace:
            self.service_namespace = os.environ.get(AZURE_SERVICEBUS_NAMESPACE)
        if not self.account_key:
            self.account_key = os.environ.get(AZURE_SERVICEBUS_ACCESS_KEY)
        if not self.issuer:
            self.issuer = os.environ.get(AZURE_SERVICEBUS_ISSUER)

        if not self.service_namespace or \
           not self.account_key or not self.issuer:
            raise WindowsAzureError(
                'You need to provide servicebus namespace, access key and Issuer')

        self._httpclient = _HTTPClient(service_instance=self,
                                       service_namespace=self.service_namespace,
                                       account_key=self.account_key,
                                       issuer=self.issuer)
        self._filter = self._httpclient.perform_request

    def with_filter(self, filter):
        '''
        Returns a new service which will process requests with the specified
        filter.  Filtering operations can include logging, automatic retrying,
        etc...  The filter is a lambda which receives the HTTPRequest and
        another lambda.  The filter can perform any pre-processing on the
        request, pass it off to the next lambda, and then perform any
        post-processing on the response.
        '''
        res = ServiceBusService(self.service_namespace, self.account_key,
                                self.issuer)
        old_filter = self._filter

        def new_filter(request):
            return filter(request, old_filter)

        res._filter = new_filter
        return res

    def set_proxy(self, host, port, user=None, password=None):
        '''
        Sets the proxy server host and port for the HTTP CONNECT Tunnelling.

        host: Address of the proxy. Ex: '192.168.0.100'
        port: Port of the proxy. Ex: 6000
        user: User for proxy authorization.
        password: Password for proxy authorization.
        '''
        self._httpclient.set_proxy(host, port, user, password)

    def create_queue(self, queue_name, queue=None, fail_on_exist=False):
        '''
        Creates a new queue. Once created, this queue's resource manifest is
        immutable.

        queue_name: Name of the queue to create.
        queue: Queue object to create.
        fail_on_exist:
            Specify whether to throw an exception when the queue exists.
        '''
        _validate_not_none('queue_name', queue_name)
        request = HTTPRequest()
        request.method = 'PUT'
        request.host = self._get_host()
        request.path = '/' + _str(queue_name) + ''
        request.body = _get_request_body(_convert_queue_to_xml(queue))
        request.path, request.query = _update_request_uri_query(request)
        request.headers = self._update_service_bus_header(request)
        if not fail_on_exist:
            try:
                self._perform_request(request)
                return True
            except WindowsAzureError as ex:
                _dont_fail_on_exist(ex)
                return False
        else:
            self._perform_request(request)
            return True

    def delete_queue(self, queue_name, fail_not_exist=False):
        '''
        Deletes an existing queue. This operation will also remove all
        associated state including messages in the queue.

        queue_name: Name of the queue to delete.
        fail_not_exist:
            Specify whether to throw an exception if the queue doesn't exist.
        '''
        _validate_not_none('queue_name', queue_name)
        request = HTTPRequest()
        request.method = 'DELETE'
        request.host = self._get_host()
        request.path = '/' + _str(queue_name) + ''
        request.path, request.query = _update_request_uri_query(request)
        request.headers = self._update_service_bus_header(request)
        if not fail_not_exist:
            try:
                self._perform_request(request)
                return True
            except WindowsAzureError as ex:
                _dont_fail_not_exist(ex)
                return False
        else:
            self._perform_request(request)
            return True

    def get_queue(self, queue_name):
        '''
        Retrieves an existing queue.

        queue_name: Name of the queue.
        '''
        _validate_not_none('queue_name', queue_name)
        request = HTTPRequest()
        request.method = 'GET'
        request.host = self._get_host()
        request.path = '/' + _str(queue_name) + ''
        request.path, request.query = _update_request_uri_query(request)
        request.headers = self._update_service_bus_header(request)
        response = self._perform_request(request)

        return _convert_response_to_queue(response)

    def list_queues(self):
        '''
        Enumerates the queues in the service namespace.
        '''
        request = HTTPRequest()
        request.method = 'GET'
        request.host = self._get_host()
        request.path = '/$Resources/Queues'
        request.path, request.query = _update_request_uri_query(request)
        request.headers = self._update_service_bus_header(request)
        response = self._perform_request(request)

        return _convert_response_to_feeds(response, _convert_xml_to_queue)

    def create_topic(self, topic_name, topic=None, fail_on_exist=False):
        '''
        Creates a new topic. Once created, this topic resource manifest is
        immutable.

        topic_name: Name of the topic to create.
        topic: Topic object to create.
        fail_on_exist:
            Specify whether to throw an exception when the topic exists.
        '''
        _validate_not_none('topic_name', topic_name)
        request = HTTPRequest()
        request.method = 'PUT'
        request.host = self._get_host()
        request.path = '/' + _str(topic_name) + ''
        request.body = _get_request_body(_convert_topic_to_xml(topic))
        request.path, request.query = _update_request_uri_query(request)
        request.headers = self._update_service_bus_header(request)
        if not fail_on_exist:
            try:
                self._perform_request(request)
                return True
            except WindowsAzureError as ex:
                _dont_fail_on_exist(ex)
                return False
        else:
            self._perform_request(request)
            return True

    def delete_topic(self, topic_name, fail_not_exist=False):
        '''
        Deletes an existing topic. This operation will also remove all
        associated state including associated subscriptions.

        topic_name: Name of the topic to delete.
        fail_not_exist:
            Specify whether throw exception when topic doesn't exist.
        '''
        _validate_not_none('topic_name', topic_name)
        request = HTTPRequest()
        request.method = 'DELETE'
        request.host = self._get_host()
        request.path = '/' + _str(topic_name) + ''
        request.path, request.query = _update_request_uri_query(request)
        request.headers = self._update_service_bus_header(request)
        if not fail_not_exist:
            try:
                self._perform_request(request)
                return True
            except WindowsAzureError as ex:
                _dont_fail_not_exist(ex)
                return False
        else:
            self._perform_request(request)
            return True

    def get_topic(self, topic_name):
        '''
        Retrieves the description for the specified topic.

        topic_name: Name of the topic.
        '''
        _validate_not_none('topic_name', topic_name)
        request = HTTPRequest()
        request.method = 'GET'
        request.host = self._get_host()
        request.path = '/' + _str(topic_name) + ''
        request.path, request.query = _update_request_uri_query(request)
        request.headers = self._update_service_bus_header(request)
        response = self._perform_request(request)

        return _convert_response_to_topic(response)

    def list_topics(self):
        '''
        Retrieves the topics in the service namespace.
        '''
        request = HTTPRequest()
        request.method = 'GET'
        request.host = self._get_host()
        request.path = '/$Resources/Topics'
        request.path, request.query = _update_request_uri_query(request)
        request.headers = self._update_service_bus_header(request)
        response = self._perform_request(request)

        return _convert_response_to_feeds(response, _convert_xml_to_topic)

    def create_rule(self, topic_name, subscription_name, rule_name, rule=None,
                    fail_on_exist=False):
        '''
        Creates a new rule. Once created, this rule's resource manifest is
        immutable.

        topic_name: Name of the topic.
        subscription_name: Name of the subscription.
        rule_name: Name of the rule.
        fail_on_exist:
            Specify whether to throw an exception when the rule exists.
        '''
        _validate_not_none('topic_name', topic_name)
        _validate_not_none('subscription_name', subscription_name)
        _validate_not_none('rule_name', rule_name)
        request = HTTPRequest()
        request.method = 'PUT'
        request.host = self._get_host()
        request.path = '/' + _str(topic_name) + '/subscriptions/' + \
            _str(subscription_name) + \
            '/rules/' + _str(rule_name) + ''
        request.body = _get_request_body(_convert_rule_to_xml(rule))
        request.path, request.query = _update_request_uri_query(request)
        request.headers = self._update_service_bus_header(request)
        if not fail_on_exist:
            try:
                self._perform_request(request)
                return True
            except WindowsAzureError as ex:
                _dont_fail_on_exist(ex)
                return False
        else:
            self._perform_request(request)
            return True

    def delete_rule(self, topic_name, subscription_name, rule_name,
                    fail_not_exist=False):
        '''
        Deletes an existing rule.

        topic_name: Name of the topic.
        subscription_name: Name of the subscription.
        rule_name:
            Name of the rule to delete.  DEFAULT_RULE_NAME=$Default.
            Use DEFAULT_RULE_NAME to delete default rule for the subscription.
        fail_not_exist:
            Specify whether throw exception when rule doesn't exist.
        '''
        _validate_not_none('topic_name', topic_name)
        _validate_not_none('subscription_name', subscription_name)
        _validate_not_none('rule_name', rule_name)
        request = HTTPRequest()
        request.method = 'DELETE'
        request.host = self._get_host()
        request.path = '/' + _str(topic_name) + '/subscriptions/' + \
            _str(subscription_name) + \
            '/rules/' + _str(rule_name) + ''
        request.path, request.query = _update_request_uri_query(request)
        request.headers = self._update_service_bus_header(request)
        if not fail_not_exist:
            try:
                self._perform_request(request)
                return True
            except WindowsAzureError as ex:
                _dont_fail_not_exist(ex)
                return False
        else:
            self._perform_request(request)
            return True

    def get_rule(self, topic_name, subscription_name, rule_name):
        '''
        Retrieves the description for the specified rule.

        topic_name: Name of the topic.
        subscription_name: Name of the subscription.
        rule_name: Name of the rule.
        '''
        _validate_not_none('topic_name', topic_name)
        _validate_not_none('subscription_name', subscription_name)
        _validate_not_none('rule_name', rule_name)
        request = HTTPRequest()
        request.method = 'GET'
        request.host = self._get_host()
        request.path = '/' + _str(topic_name) + '/subscriptions/' + \
            _str(subscription_name) + \
            '/rules/' + _str(rule_name) + ''
        request.path, request.query = _update_request_uri_query(request)
        request.headers = self._update_service_bus_header(request)
        response = self._perform_request(request)

        return _convert_response_to_rule(response)

    def list_rules(self, topic_name, subscription_name):
        '''
        Retrieves the rules that exist under the specified subscription.

        topic_name: Name of the topic.
        subscription_name: Name of the subscription.
        '''
        _validate_not_none('topic_name', topic_name)
        _validate_not_none('subscription_name', subscription_name)
        request = HTTPRequest()
        request.method = 'GET'
        request.host = self._get_host()
        request.path = '/' + \
            _str(topic_name) + '/subscriptions/' + \
            _str(subscription_name) + '/rules/'
        request.path, request.query = _update_request_uri_query(request)
        request.headers = self._update_service_bus_header(request)
        response = self._perform_request(request)

        return _convert_response_to_feeds(response, _convert_xml_to_rule)

    def create_subscription(self, topic_name, subscription_name,
                            subscription=None, fail_on_exist=False):
        '''
        Creates a new subscription. Once created, this subscription resource
        manifest is immutable.

        topic_name: Name of the topic.
        subscription_name: Name of the subscription.
        fail_on_exist:
            Specify whether throw exception when subscription exists.
        '''
        _validate_not_none('topic_name', topic_name)
        _validate_not_none('subscription_name', subscription_name)
        request = HTTPRequest()
        request.method = 'PUT'
        request.host = self._get_host()
        request.path = '/' + \
            _str(topic_name) + '/subscriptions/' + _str(subscription_name) + ''
        request.body = _get_request_body(
            _convert_subscription_to_xml(subscription))
        request.path, request.query = _update_request_uri_query(request)
        request.headers = self._update_service_bus_header(request)
        if not fail_on_exist:
            try:
                self._perform_request(request)
                return True
            except WindowsAzureError as ex:
                _dont_fail_on_exist(ex)
                return False
        else:
            self._perform_request(request)
            return True

    def delete_subscription(self, topic_name, subscription_name,
                            fail_not_exist=False):
        '''
        Deletes an existing subscription.

        topic_name: Name of the topic.
        subscription_name: Name of the subscription to delete.
        fail_not_exist:
            Specify whether to throw an exception when the subscription
            doesn't exist.
        '''
        _validate_not_none('topic_name', topic_name)
        _validate_not_none('subscription_name', subscription_name)
        request = HTTPRequest()
        request.method = 'DELETE'
        request.host = self._get_host()
        request.path = '/' + \
            _str(topic_name) + '/subscriptions/' + _str(subscription_name) + ''
        request.path, request.query = _update_request_uri_query(request)
        request.headers = self._update_service_bus_header(request)
        if not fail_not_exist:
            try:
                self._perform_request(request)
                return True
            except WindowsAzureError as ex:
                _dont_fail_not_exist(ex)
                return False
        else:
            self._perform_request(request)
            return True

    def get_subscription(self, topic_name, subscription_name):
        '''
        Gets an existing subscription.

        topic_name: Name of the topic.
        subscription_name: Name of the subscription.
        '''
        _validate_not_none('topic_name', topic_name)
        _validate_not_none('subscription_name', subscription_name)
        request = HTTPRequest()
        request.method = 'GET'
        request.host = self._get_host()
        request.path = '/' + \
            _str(topic_name) + '/subscriptions/' + _str(subscription_name) + ''
        request.path, request.query = _update_request_uri_query(request)
        request.headers = self._update_service_bus_header(request)
        response = self._perform_request(request)

        return _convert_response_to_subscription(response)

    def list_subscriptions(self, topic_name):
        '''
        Retrieves the subscriptions in the specified topic.

        topic_name: Name of the topic.
        '''
        _validate_not_none('topic_name', topic_name)
        request = HTTPRequest()
        request.method = 'GET'
        request.host = self._get_host()
        request.path = '/' + _str(topic_name) + '/subscriptions/'
        request.path, request.query = _update_request_uri_query(request)
        request.headers = self._update_service_bus_header(request)
        response = self._perform_request(request)

        return _convert_response_to_feeds(response,
                                          _convert_xml_to_subscription)

    def send_topic_message(self, topic_name, message=None):
        '''
        Enqueues a message into the specified topic. The limit to the number
        of messages which may be present in the topic is governed by the
        message size in MaxTopicSizeInBytes. If this message causes the topic
        to exceed its quota, a quota exceeded error is returned and the
        message will be rejected.

        topic_name: Name of the topic.
        message: Message object containing message body and properties.
        '''
        _validate_not_none('topic_name', topic_name)
        _validate_not_none('message', message)
        request = HTTPRequest()
        request.method = 'POST'
        request.host = self._get_host()
        request.path = '/' + _str(topic_name) + '/messages'
        request.headers = message.add_headers(request)
        request.body = _get_request_body_bytes_only(
            'message.body', message.body)
        request.path, request.query = _update_request_uri_query(request)
        request.headers = self._update_service_bus_header(request)
        self._perform_request(request)

    def peek_lock_subscription_message(self, topic_name, subscription_name,
                                       timeout='60'):
        '''
        This operation is used to atomically retrieve and lock a message for
        processing. The message is guaranteed not to be delivered to other
        receivers during the lock duration period specified in buffer
        description. Once the lock expires, the message will be available to
        other receivers (on the same subscription only) during the lock
        duration period specified in the topic description. Once the lock
        expires, the message will be available to other receivers. In order to
        complete processing of the message, the receiver should issue a delete
        command with the lock ID received from this operation. To abandon
        processing of the message and unlock it for other receivers, an Unlock
        Message command should be issued, or the lock duration period can
        expire.

        topic_name: Name of the topic.
        subscription_name: Name of the subscription.
        timeout: Optional. The timeout parameter is expressed in seconds.
        '''
        _validate_not_none('topic_name', topic_name)
        _validate_not_none('subscription_name', subscription_name)
        request = HTTPRequest()
        request.method = 'POST'
        request.host = self._get_host()
        request.path = '/' + \
            _str(topic_name) + '/subscriptions/' + \
            _str(subscription_name) + '/messages/head'
        request.query = [('timeout', _int_or_none(timeout))]
        request.path, request.query = _update_request_uri_query(request)
        request.headers = self._update_service_bus_header(request)
        response = self._perform_request(request)

        return _create_message(response, self)

    def unlock_subscription_message(self, topic_name, subscription_name,
                                    sequence_number, lock_token):
        '''
        Unlock a message for processing by other receivers on a given
        subscription. This operation deletes the lock object, causing the
        message to be unlocked. A message must have first been locked by a
        receiver before this operation is called.

        topic_name: Name of the topic.
        subscription_name: Name of the subscription.
        sequence_number:
            The sequence number of the message to be unlocked as returned in
            BrokerProperties['SequenceNumber'] by the Peek Message operation.
        lock_token:
            The ID of the lock as returned by the Peek Message operation in
            BrokerProperties['LockToken']
        '''
        _validate_not_none('topic_name', topic_name)
        _validate_not_none('subscription_name', subscription_name)
        _validate_not_none('sequence_number', sequence_number)
        _validate_not_none('lock_token', lock_token)
        request = HTTPRequest()
        request.method = 'PUT'
        request.host = self._get_host()
        request.path = '/' + _str(topic_name) + \
                       '/subscriptions/' + str(subscription_name) + \
                       '/messages/' + _str(sequence_number) + \
                       '/' + _str(lock_token) + ''
        request.path, request.query = _update_request_uri_query(request)
        request.headers = self._update_service_bus_header(request)
        self._perform_request(request)

    def read_delete_subscription_message(self, topic_name, subscription_name,
                                         timeout='60'):
        '''
        Read and delete a message from a subscription as an atomic operation.
        This operation should be used when a best-effort guarantee is
        sufficient for an application; that is, using this operation it is
        possible for messages to be lost if processing fails.

        topic_name: Name of the topic.
        subscription_name: Name of the subscription.
        timeout: Optional. The timeout parameter is expressed in seconds.
        '''
        _validate_not_none('topic_name', topic_name)
        _validate_not_none('subscription_name', subscription_name)
        request = HTTPRequest()
        request.method = 'DELETE'
        request.host = self._get_host()
        request.path = '/' + _str(topic_name) + \
                       '/subscriptions/' + _str(subscription_name) + \
                       '/messages/head'
        request.query = [('timeout', _int_or_none(timeout))]
        request.path, request.query = _update_request_uri_query(request)
        request.headers = self._update_service_bus_header(request)
        response = self._perform_request(request)

        return _create_message(response, self)

    def delete_subscription_message(self, topic_name, subscription_name,
                                    sequence_number, lock_token):
        '''
        Completes processing on a locked message and delete it from the
        subscription. This operation should only be called after processing a
        previously locked message is successful to maintain At-Least-Once
        delivery assurances.

        topic_name: Name of the topic.
        subscription_name: Name of the subscription.
        sequence_number:
            The sequence number of the message to be deleted as returned in
            BrokerProperties['SequenceNumber'] by the Peek Message operation.
        lock_token:
            The ID of the lock as returned by the Peek Message operation in
            BrokerProperties['LockToken']
        '''
        _validate_not_none('topic_name', topic_name)
        _validate_not_none('subscription_name', subscription_name)
        _validate_not_none('sequence_number', sequence_number)
        _validate_not_none('lock_token', lock_token)
        request = HTTPRequest()
        request.method = 'DELETE'
        request.host = self._get_host()
        request.path = '/' + _str(topic_name) + \
                       '/subscriptions/' + _str(subscription_name) + \
                       '/messages/' + _str(sequence_number) + \
                       '/' + _str(lock_token) + ''
        request.path, request.query = _update_request_uri_query(request)
        request.headers = self._update_service_bus_header(request)
        self._perform_request(request)

    def send_queue_message(self, queue_name, message=None):
        '''
        Sends a message into the specified queue. The limit to the number of
        messages which may be present in the topic is governed by the message
        size the MaxTopicSizeInMegaBytes. If this message will cause the queue
        to exceed its quota, a quota exceeded error is returned and the
        message will be rejected.

        queue_name: Name of the queue.
        message: Message object containing message body and properties.
        '''
        _validate_not_none('queue_name', queue_name)
        _validate_not_none('message', message)
        request = HTTPRequest()
        request.method = 'POST'
        request.host = self._get_host()
        request.path = '/' + _str(queue_name) + '/messages'
        request.headers = message.add_headers(request)
        request.body = _get_request_body_bytes_only('message.body',
                                                    message.body)
        request.path, request.query = _update_request_uri_query(request)
        request.headers = self._update_service_bus_header(request)
        self._perform_request(request)

    def peek_lock_queue_message(self, queue_name, timeout='60'):
        '''
        Automically retrieves and locks a message from a queue for processing.
        The message is guaranteed not to be delivered to other receivers (on
        the same subscription only) during the lock duration period specified
        in the queue description. Once the lock expires, the message will be
        available to other receivers. In order to complete processing of the
        message, the receiver should issue a delete command with the lock ID
        received from this operation. To abandon processing of the message and
        unlock it for other receivers, an Unlock Message command should be
        issued, or the lock duration period can expire.

        queue_name: Name of the queue.
        timeout: Optional. The timeout parameter is expressed in seconds.
        '''
        _validate_not_none('queue_name', queue_name)
        request = HTTPRequest()
        request.method = 'POST'
        request.host = self._get_host()
        request.path = '/' + _str(queue_name) + '/messages/head'
        request.query = [('timeout', _int_or_none(timeout))]
        request.path, request.query = _update_request_uri_query(request)
        request.headers = self._update_service_bus_header(request)
        response = self._perform_request(request)

        return _create_message(response, self)

    def unlock_queue_message(self, queue_name, sequence_number, lock_token):
        '''
        Unlocks a message for processing by other receivers on a given
        subscription. This operation deletes the lock object, causing the
        message to be unlocked. A message must have first been locked by a
        receiver before this operation is called.

        queue_name: Name of the queue.
        sequence_number:
            The sequence number of the message to be unlocked as returned in
            BrokerProperties['SequenceNumber'] by the Peek Message operation.
        lock_token:
            The ID of the lock as returned by the Peek Message operation in
            BrokerProperties['LockToken']
        '''
        _validate_not_none('queue_name', queue_name)
        _validate_not_none('sequence_number', sequence_number)
        _validate_not_none('lock_token', lock_token)
        request = HTTPRequest()
        request.method = 'PUT'
        request.host = self._get_host()
        request.path = '/' + _str(queue_name) + \
                       '/messages/' + _str(sequence_number) + \
                       '/' + _str(lock_token) + ''
        request.path, request.query = _update_request_uri_query(request)
        request.headers = self._update_service_bus_header(request)
        self._perform_request(request)

    def read_delete_queue_message(self, queue_name, timeout='60'):
        '''
        Reads and deletes a message from a queue as an atomic operation. This
        operation should be used when a best-effort guarantee is sufficient
        for an application; that is, using this operation it is possible for
        messages to be lost if processing fails.

        queue_name: Name of the queue.
        timeout: Optional. The timeout parameter is expressed in seconds.
        '''
        _validate_not_none('queue_name', queue_name)
        request = HTTPRequest()
        request.method = 'DELETE'
        request.host = self._get_host()
        request.path = '/' + _str(queue_name) + '/messages/head'
        request.query = [('timeout', _int_or_none(timeout))]
        request.path, request.query = _update_request_uri_query(request)
        request.headers = self._update_service_bus_header(request)
        response = self._perform_request(request)

        return _create_message(response, self)

    def delete_queue_message(self, queue_name, sequence_number, lock_token):
        '''
        Completes processing on a locked message and delete it from the queue.
        This operation should only be called after processing a previously
        locked message is successful to maintain At-Least-Once delivery
        assurances.

        queue_name: Name of the queue.
        sequence_number:
            The sequence number of the message to be deleted as returned in
            BrokerProperties['SequenceNumber'] by the Peek Message operation.
        lock_token:
            The ID of the lock as returned by the Peek Message operation in
            BrokerProperties['LockToken']
        '''
        _validate_not_none('queue_name', queue_name)
        _validate_not_none('sequence_number', sequence_number)
        _validate_not_none('lock_token', lock_token)
        request = HTTPRequest()
        request.method = 'DELETE'
        request.host = self._get_host()
        request.path = '/' + _str(queue_name) + \
                       '/messages/' + _str(sequence_number) + \
                       '/' + _str(lock_token) + ''
        request.path, request.query = _update_request_uri_query(request)
        request.headers = self._update_service_bus_header(request)
        self._perform_request(request)

    def receive_queue_message(self, queue_name, peek_lock=True, timeout=60):
        '''
        Receive a message from a queue for processing.

        queue_name: Name of the queue.
        peek_lock:
            Optional. True to retrieve and lock the message. False to read and
            delete the message. Default is True (lock).
        timeout: Optional. The timeout parameter is expressed in seconds.
        '''
        if peek_lock:
            return self.peek_lock_queue_message(queue_name, timeout)
        else:
            return self.read_delete_queue_message(queue_name, timeout)

    def receive_subscription_message(self, topic_name, subscription_name,
                                     peek_lock=True, timeout=60):
        '''
        Receive a message from a subscription for processing.

        topic_name: Name of the topic.
        subscription_name: Name of the subscription.
        peek_lock:
            Optional. True to retrieve and lock the message. False to read and
            delete the message. Default is True (lock).
        timeout: Optional. The timeout parameter is expressed in seconds.
        '''
        if peek_lock:
            return self.peek_lock_subscription_message(topic_name,
                                                       subscription_name,
                                                       timeout)
        else:
            return self.read_delete_subscription_message(topic_name,
                                                         subscription_name,
                                                         timeout)

    def _get_host(self):
        return self.service_namespace + self.host_base

    def _perform_request(self, request):
        try:
            resp = self._filter(request)
        except HTTPError as ex:
            return _service_bus_error_handler(ex)

        return resp

    def _update_service_bus_header(self, request):
        ''' Add additional headers for service bus. '''

        if request.method in ['PUT', 'POST', 'MERGE', 'DELETE']:
            request.headers.append(('Content-Length', str(len(request.body))))

        # if it is not GET or HEAD request, must set content-type.
        if not request.method in ['GET', 'HEAD']:
            for name, _ in request.headers:
                if 'content-type' == name.lower():
                    break
            else:
                request.headers.append(
                    ('Content-Type',
                     'application/atom+xml;type=entry;charset=utf-8'))

        # Adds authoriaztion header for authentication.
        request.headers.append(
            ('Authorization', self._sign_service_bus_request(request)))

        return request.headers

    def _sign_service_bus_request(self, request):
        ''' return the signed string with token. '''

        return 'WRAP access_token="' + \
               self._get_token(request.host, request.path) + '"'

    def _token_is_expired(self, token):
        ''' Check if token expires or not. '''
        time_pos_begin = token.find('ExpiresOn=') + len('ExpiresOn=')
        time_pos_end = token.find('&', time_pos_begin)
        token_expire_time = int(token[time_pos_begin:time_pos_end])
        time_now = time.mktime(time.localtime())

        # Adding 30 seconds so the token wouldn't be expired when we send the
        # token to server.
        return (token_expire_time - time_now) < 30

    def _get_token(self, host, path):
        '''
        Returns token for the request.

        host: the service bus service request.
        path: the service bus service request.
        '''
        wrap_scope = 'http://' + host + path + self.issuer + self.account_key

        # Check whether has unexpired cache, return cached token if it is still
        # usable.
        if wrap_scope in _tokens:
            token = _tokens[wrap_scope]
            if not self._token_is_expired(token):
                return token

        # get token from accessconstrol server
        request = HTTPRequest()
        request.protocol_override = 'https'
        request.host = host.replace('.servicebus.', '-sb.accesscontrol.')
        request.method = 'POST'
        request.path = '/WRAPv0.9'
        request.body = ('wrap_name=' + url_quote(self.issuer) +
                        '&wrap_password=' + url_quote(self.account_key) +
                        '&wrap_scope=' +
                        url_quote('http://' + host + path)).encode('utf-8')
        request.headers.append(('Content-Length', str(len(request.body))))
        resp = self._httpclient.perform_request(request)

        token = resp.body.decode('utf-8')
        token = url_unquote(token[token.find('=') + 1:token.rfind('&')])
        _tokens[wrap_scope] = token

        return token

########NEW FILE########
__FILENAME__ = servicebusmanagementservice
#-------------------------------------------------------------------------
# Copyright (c) Microsoft.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#--------------------------------------------------------------------------
from azure import (
    MANAGEMENT_HOST,
    _convert_response_to_feeds,
    _str,
    _validate_not_none,
    )
from azure.servicemanagement import (
    _ServiceBusManagementXmlSerializer,
    )
from azure.servicemanagement.servicemanagementclient import (
    _ServiceManagementClient,
    )


class ServiceBusManagementService(_ServiceManagementClient):

    def __init__(self, subscription_id=None, cert_file=None,
                 host=MANAGEMENT_HOST):
        super(ServiceBusManagementService, self).__init__(
            subscription_id, cert_file, host)

    #--Operations for service bus ----------------------------------------
    def get_regions(self):
        '''
        Get list of available service bus regions.
        '''
        response = self._perform_get(
            self._get_path('services/serviceBus/Regions/', None),
            None)

        return _convert_response_to_feeds(
            response,
            _ServiceBusManagementXmlSerializer.xml_to_region)

    def list_namespaces(self):
        '''
        List the service bus namespaces defined on the account.
        '''
        response = self._perform_get(
            self._get_path('services/serviceBus/Namespaces/', None),
            None)

        return _convert_response_to_feeds(
            response,
            _ServiceBusManagementXmlSerializer.xml_to_namespace)

    def get_namespace(self, name):
        '''
        Get details about a specific namespace.

        name: Name of the service bus namespace.
        '''
        response = self._perform_get(
            self._get_path('services/serviceBus/Namespaces', name),
            None)

        return _ServiceBusManagementXmlSerializer.xml_to_namespace(
            response.body)

    def create_namespace(self, name, region):
        '''
        Create a new service bus namespace.

        name: Name of the service bus namespace to create.
        region: Region to create the namespace in.
        '''
        _validate_not_none('name', name)

        return self._perform_put(
            self._get_path('services/serviceBus/Namespaces', name),
            _ServiceBusManagementXmlSerializer.namespace_to_xml(region))

    def delete_namespace(self, name):
        '''
        Delete a service bus namespace.

        name: Name of the service bus namespace to delete.
        '''
        _validate_not_none('name', name)

        return self._perform_delete(
            self._get_path('services/serviceBus/Namespaces', name),
            None)

    def check_namespace_availability(self, name):
        '''
        Checks to see if the specified service bus namespace is available, or
        if it has already been taken.

        name: Name of the service bus namespace to validate.
        '''
        _validate_not_none('name', name)

        response = self._perform_get(
            self._get_path('services/serviceBus/CheckNamespaceAvailability',
                           None) + '/?namespace=' + _str(name), None)

        return _ServiceBusManagementXmlSerializer.xml_to_namespace_availability(
            response.body)

########NEW FILE########
__FILENAME__ = servicemanagementclient
#-------------------------------------------------------------------------
# Copyright (c) Microsoft.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#--------------------------------------------------------------------------
import os

from azure import (
    WindowsAzureError,
    MANAGEMENT_HOST,
    _get_request_body,
    _parse_response,
    _str,
    _update_request_uri_query,
    )
from azure.http import (
    HTTPError,
    HTTPRequest,
    )
from azure.http.httpclient import _HTTPClient
from azure.servicemanagement import (
    AZURE_MANAGEMENT_CERTFILE,
    AZURE_MANAGEMENT_SUBSCRIPTIONID,
    _management_error_handler,
    _parse_response_for_async_op,
    _update_management_header,
    )


class _ServiceManagementClient(object):

    def __init__(self, subscription_id=None, cert_file=None,
                 host=MANAGEMENT_HOST):
        self.requestid = None
        self.subscription_id = subscription_id
        self.cert_file = cert_file
        self.host = host

        if not self.cert_file:
            if AZURE_MANAGEMENT_CERTFILE in os.environ:
                self.cert_file = os.environ[AZURE_MANAGEMENT_CERTFILE]

        if not self.subscription_id:
            if AZURE_MANAGEMENT_SUBSCRIPTIONID in os.environ:
                self.subscription_id = os.environ[
                    AZURE_MANAGEMENT_SUBSCRIPTIONID]

        if not self.cert_file or not self.subscription_id:
            raise WindowsAzureError(
                'You need to provide subscription id and certificate file')

        self._httpclient = _HTTPClient(
            service_instance=self, cert_file=self.cert_file)
        self._filter = self._httpclient.perform_request

    def with_filter(self, filter):
        '''Returns a new service which will process requests with the
        specified filter.  Filtering operations can include logging, automatic
        retrying, etc...  The filter is a lambda which receives the HTTPRequest
        and another lambda.  The filter can perform any pre-processing on the
        request, pass it off to the next lambda, and then perform any
        post-processing on the response.'''
        res = type(self)(self.subscription_id, self.cert_file, self.host)
        old_filter = self._filter

        def new_filter(request):
            return filter(request, old_filter)

        res._filter = new_filter
        return res

    def set_proxy(self, host, port, user=None, password=None):
        '''
        Sets the proxy server host and port for the HTTP CONNECT Tunnelling.

        host: Address of the proxy. Ex: '192.168.0.100'
        port: Port of the proxy. Ex: 6000
        user: User for proxy authorization.
        password: Password for proxy authorization.
        '''
        self._httpclient.set_proxy(host, port, user, password)

    #--Helper functions --------------------------------------------------
    def _perform_request(self, request):
        try:
            resp = self._filter(request)
        except HTTPError as ex:
            return _management_error_handler(ex)

        return resp

    def _perform_get(self, path, response_type):
        request = HTTPRequest()
        request.method = 'GET'
        request.host = self.host
        request.path = path
        request.path, request.query = _update_request_uri_query(request)
        request.headers = _update_management_header(request)
        response = self._perform_request(request)

        if response_type is not None:
            return _parse_response(response, response_type)

        return response

    def _perform_put(self, path, body, async=False):
        request = HTTPRequest()
        request.method = 'PUT'
        request.host = self.host
        request.path = path
        request.body = _get_request_body(body)
        request.path, request.query = _update_request_uri_query(request)
        request.headers = _update_management_header(request)
        response = self._perform_request(request)

        if async:
            return _parse_response_for_async_op(response)

        return None

    def _perform_post(self, path, body, response_type=None, async=False):
        request = HTTPRequest()
        request.method = 'POST'
        request.host = self.host
        request.path = path
        request.body = _get_request_body(body)
        request.path, request.query = _update_request_uri_query(request)
        request.headers = _update_management_header(request)
        response = self._perform_request(request)

        if response_type is not None:
            return _parse_response(response, response_type)

        if async:
            return _parse_response_for_async_op(response)

        return None

    def _perform_delete(self, path, async=False):
        request = HTTPRequest()
        request.method = 'DELETE'
        request.host = self.host
        request.path = path
        request.path, request.query = _update_request_uri_query(request)
        request.headers = _update_management_header(request)
        response = self._perform_request(request)

        if async:
            return _parse_response_for_async_op(response)

        return None

    def _get_path(self, resource, name):
        path = '/' + self.subscription_id + '/' + resource
        if name is not None:
            path += '/' + _str(name)
        return path

########NEW FILE########
__FILENAME__ = servicemanagementservice
#-------------------------------------------------------------------------
# Copyright (c) Microsoft.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#--------------------------------------------------------------------------
from azure import (
    WindowsAzureError,
    MANAGEMENT_HOST,
    _str,
    _validate_not_none,
    )
from azure.servicemanagement import (
    AffinityGroups,
    AffinityGroup,
    AvailabilityResponse,
    Certificate,
    Certificates,
    DataVirtualHardDisk,
    Deployment,
    Disk,
    Disks,
    Locations,
    Operation,
    HostedService,
    HostedServices,
    Images,
    OperatingSystems,
    OperatingSystemFamilies,
    OSImage,
    PersistentVMRole,
    StorageService,
    StorageServices,
    Subscription,
    SubscriptionCertificate,
    SubscriptionCertificates,
    VirtualNetworkSites,
    _XmlSerializer,
    )
from azure.servicemanagement.servicemanagementclient import (
    _ServiceManagementClient,
    )

class ServiceManagementService(_ServiceManagementClient):

    def __init__(self, subscription_id=None, cert_file=None,
                 host=MANAGEMENT_HOST):
        super(ServiceManagementService, self).__init__(
            subscription_id, cert_file, host)

    #--Operations for storage accounts -----------------------------------
    def list_storage_accounts(self):
        '''
        Lists the storage accounts available under the current subscription.
        '''
        return self._perform_get(self._get_storage_service_path(),
                                 StorageServices)

    def get_storage_account_properties(self, service_name):
        '''
        Returns system properties for the specified storage account.

        service_name: Name of the storage service account.
        '''
        _validate_not_none('service_name', service_name)
        return self._perform_get(self._get_storage_service_path(service_name),
                                 StorageService)

    def get_storage_account_keys(self, service_name):
        '''
        Returns the primary and secondary access keys for the specified
        storage account.

        service_name: Name of the storage service account.
        '''
        _validate_not_none('service_name', service_name)
        return self._perform_get(
            self._get_storage_service_path(service_name) + '/keys',
            StorageService)

    def regenerate_storage_account_keys(self, service_name, key_type):
        '''
        Regenerates the primary or secondary access key for the specified
        storage account.

        service_name: Name of the storage service account.
        key_type:
            Specifies which key to regenerate. Valid values are:
            Primary, Secondary
        '''
        _validate_not_none('service_name', service_name)
        _validate_not_none('key_type', key_type)
        return self._perform_post(
            self._get_storage_service_path(
                service_name) + '/keys?action=regenerate',
            _XmlSerializer.regenerate_keys_to_xml(
                key_type),
            StorageService)

    def create_storage_account(self, service_name, description, label,
                               affinity_group=None, location=None,
                               geo_replication_enabled=True,
                               extended_properties=None):
        '''
        Creates a new storage account in Windows Azure.

        service_name:
            A name for the storage account that is unique within Windows Azure.
            Storage account names must be between 3 and 24 characters in length
            and use numbers and lower-case letters only.
        description:
            A description for the storage account. The description may be up
            to 1024 characters in length.
        label:
            A name for the storage account. The name may be up to 100
            characters in length. The name can be used to identify the storage
            account for your tracking purposes.
        affinity_group:
            The name of an existing affinity group in the specified
            subscription. You can specify either a location or affinity_group,
            but not both.
        location:
            The location where the storage account is created. You can specify
            either a location or affinity_group, but not both.
        geo_replication_enabled:
            Specifies whether the storage account is created with the
            geo-replication enabled. If the element is not included in the
            request body, the default value is true. If set to true, the data
            in the storage account is replicated across more than one
            geographic location so as to enable resilience in the face of
            catastrophic service loss.
        extended_properties:
            Dictionary containing name/value pairs of storage account
            properties. You can have a maximum of 50 extended property
            name/value pairs. The maximum length of the Name element is 64
            characters, only alphanumeric characters and underscores are valid
            in the Name, and the name must start with a letter. The value has
            a maximum length of 255 characters.
        '''
        _validate_not_none('service_name', service_name)
        _validate_not_none('description', description)
        _validate_not_none('label', label)
        if affinity_group is None and location is None:
            raise WindowsAzureError(
                'location or affinity_group must be specified')
        if affinity_group is not None and location is not None:
            raise WindowsAzureError(
                'Only one of location or affinity_group needs to be specified')
        return self._perform_post(
            self._get_storage_service_path(),
            _XmlSerializer.create_storage_service_input_to_xml(
                service_name,
                description,
                label,
                affinity_group,
                location,
                geo_replication_enabled,
                extended_properties),
            async=True)

    def update_storage_account(self, service_name, description=None,
                               label=None, geo_replication_enabled=None,
                               extended_properties=None):
        '''
        Updates the label, the description, and enables or disables the
        geo-replication status for a storage account in Windows Azure.

        service_name: Name of the storage service account.
        description:
            A description for the storage account. The description may be up
            to 1024 characters in length.
        label:
            A name for the storage account. The name may be up to 100
            characters in length. The name can be used to identify the storage
            account for your tracking purposes.
        geo_replication_enabled:
            Specifies whether the storage account is created with the
            geo-replication enabled. If the element is not included in the
            request body, the default value is true. If set to true, the data
            in the storage account is replicated across more than one
            geographic location so as to enable resilience in the face of
            catastrophic service loss.
        extended_properties:
            Dictionary containing name/value pairs of storage account
            properties. You can have a maximum of 50 extended property
            name/value pairs. The maximum length of the Name element is 64
            characters, only alphanumeric characters and underscores are valid
            in the Name, and the name must start with a letter. The value has
            a maximum length of 255 characters.
        '''
        _validate_not_none('service_name', service_name)
        return self._perform_put(
            self._get_storage_service_path(service_name),
            _XmlSerializer.update_storage_service_input_to_xml(
                description,
                label,
                geo_replication_enabled,
                extended_properties))

    def delete_storage_account(self, service_name):
        '''
        Deletes the specified storage account from Windows Azure.

        service_name: Name of the storage service account.
        '''
        _validate_not_none('service_name', service_name)
        return self._perform_delete(
            self._get_storage_service_path(service_name))

    def check_storage_account_name_availability(self, service_name):
        '''
        Checks to see if the specified storage account name is available, or
        if it has already been taken.

        service_name: Name of the storage service account.
        '''
        _validate_not_none('service_name', service_name)
        return self._perform_get(
            self._get_storage_service_path() +
            '/operations/isavailable/' +
            _str(service_name) + '',
            AvailabilityResponse)

    #--Operations for hosted services ------------------------------------
    def list_hosted_services(self):
        '''
        Lists the hosted services available under the current subscription.
        '''
        return self._perform_get(self._get_hosted_service_path(),
                                 HostedServices)

    def get_hosted_service_properties(self, service_name, embed_detail=False):
        '''
        Retrieves system properties for the specified hosted service. These
        properties include the service name and service type; the name of the
        affinity group to which the service belongs, or its location if it is
        not part of an affinity group; and optionally, information on the
        service's deployments.

        service_name: Name of the hosted service.
        embed_detail:
            When True, the management service returns properties for all
            deployments of the service, as well as for the service itself.
        '''
        _validate_not_none('service_name', service_name)
        _validate_not_none('embed_detail', embed_detail)
        return self._perform_get(
            self._get_hosted_service_path(service_name) +
            '?embed-detail=' +
            _str(embed_detail).lower(),
            HostedService)

    def create_hosted_service(self, service_name, label, description=None,
                              location=None, affinity_group=None,
                              extended_properties=None):
        '''
        Creates a new hosted service in Windows Azure.

        service_name:
            A name for the hosted service that is unique within Windows Azure.
            This name is the DNS prefix name and can be used to access the
            hosted service.
        label:
            A name for the hosted service. The name can be up to 100 characters
            in length. The name can be used to identify the storage account for
            your tracking purposes.
        description:
            A description for the hosted service. The description can be up to
            1024 characters in length.
        location:
            The location where the hosted service will be created. You can
            specify either a location or affinity_group, but not both.
        affinity_group:
            The name of an existing affinity group associated with this
            subscription. This name is a GUID and can be retrieved by examining
            the name element of the response body returned by
            list_affinity_groups. You can specify either a location or
            affinity_group, but not both.
        extended_properties:
            Dictionary containing name/value pairs of storage account
            properties. You can have a maximum of 50 extended property
            name/value pairs. The maximum length of the Name element is 64
            characters, only alphanumeric characters and underscores are valid
            in the Name, and the name must start with a letter. The value has
            a maximum length of 255 characters.
        '''
        _validate_not_none('service_name', service_name)
        _validate_not_none('label', label)
        if affinity_group is None and location is None:
            raise WindowsAzureError(
                'location or affinity_group must be specified')
        if affinity_group is not None and location is not None:
            raise WindowsAzureError(
                'Only one of location or affinity_group needs to be specified')
        return self._perform_post(self._get_hosted_service_path(),
                                  _XmlSerializer.create_hosted_service_to_xml(
                                      service_name,
                                      label,
                                      description,
                                      location,
                                      affinity_group,
                                      extended_properties))

    def update_hosted_service(self, service_name, label=None, description=None,
                              extended_properties=None):
        '''
        Updates the label and/or the description for a hosted service in
        Windows Azure.

        service_name: Name of the hosted service.
        label:
            A name for the hosted service. The name may be up to 100 characters
            in length. You must specify a value for either Label or
            Description, or for both. It is recommended that the label be
            unique within the subscription. The name can be used
            identify the hosted service for your tracking purposes.
        description:
            A description for the hosted service. The description may be up to
            1024 characters in length. You must specify a value for either
            Label or Description, or for both.
        extended_properties:
            Dictionary containing name/value pairs of storage account
            properties. You can have a maximum of 50 extended property
            name/value pairs. The maximum length of the Name element is 64
            characters, only alphanumeric characters and underscores are valid
            in the Name, and the name must start with a letter. The value has
            a maximum length of 255 characters.
        '''
        _validate_not_none('service_name', service_name)
        return self._perform_put(self._get_hosted_service_path(service_name),
                                 _XmlSerializer.update_hosted_service_to_xml(
                                     label,
                                     description,
                                     extended_properties))

    def delete_hosted_service(self, service_name):
        '''
        Deletes the specified hosted service from Windows Azure.

        service_name: Name of the hosted service.
        '''
        _validate_not_none('service_name', service_name)
        return self._perform_delete(self._get_hosted_service_path(service_name))

    def get_deployment_by_slot(self, service_name, deployment_slot):
        '''
        Returns configuration information, status, and system properties for
        a deployment.

        service_name: Name of the hosted service.
        deployment_slot:
            The environment to which the hosted service is deployed. Valid
            values are: staging, production
        '''
        _validate_not_none('service_name', service_name)
        _validate_not_none('deployment_slot', deployment_slot)
        return self._perform_get(
            self._get_deployment_path_using_slot(
                service_name, deployment_slot),
            Deployment)

    def get_deployment_by_name(self, service_name, deployment_name):
        '''
        Returns configuration information, status, and system properties for a
        deployment.

        service_name: Name of the hosted service.
        deployment_name: The name of the deployment.
        '''
        _validate_not_none('service_name', service_name)
        _validate_not_none('deployment_name', deployment_name)
        return self._perform_get(
            self._get_deployment_path_using_name(
                service_name, deployment_name),
            Deployment)

    def create_deployment(self, service_name, deployment_slot, name,
                          package_url, label, configuration,
                          start_deployment=False,
                          treat_warnings_as_error=False,
                          extended_properties=None):
        '''
        Uploads a new service package and creates a new deployment on staging
        or production.

        service_name: Name of the hosted service.
        deployment_slot:
            The environment to which the hosted service is deployed. Valid
            values are: staging, production
        name:
            The name for the deployment. The deployment name must be unique
            among other deployments for the hosted service.
        package_url:
            A URL that refers to the location of the service package in the
            Blob service. The service package can be located either in a
            storage account beneath the same subscription or a Shared Access
            Signature (SAS) URI from any storage account.
        label:
            A name for the hosted service. The name can be up to 100 characters
            in length. It is recommended that the label be unique within the
            subscription. The name can be used to identify the hosted service
            for your tracking purposes.
        configuration:
            The base-64 encoded service configuration file for the deployment.
        start_deployment:
            Indicates whether to start the deployment immediately after it is
            created. If false, the service model is still deployed to the
            virtual machines but the code is not run immediately. Instead, the
            service is Suspended until you call Update Deployment Status and
            set the status to Running, at which time the service will be
            started. A deployed service still incurs charges, even if it is
            suspended.
        treat_warnings_as_error:
            Indicates whether to treat package validation warnings as errors.
            If set to true, the Created Deployment operation fails if there
            are validation warnings on the service package.
        extended_properties:
            Dictionary containing name/value pairs of storage account
            properties. You can have a maximum of 50 extended property
            name/value pairs. The maximum length of the Name element is 64
            characters, only alphanumeric characters and underscores are valid
            in the Name, and the name must start with a letter. The value has
            a maximum length of 255 characters.
        '''
        _validate_not_none('service_name', service_name)
        _validate_not_none('deployment_slot', deployment_slot)
        _validate_not_none('name', name)
        _validate_not_none('package_url', package_url)
        _validate_not_none('label', label)
        _validate_not_none('configuration', configuration)
        return self._perform_post(
            self._get_deployment_path_using_slot(
                service_name, deployment_slot),
            _XmlSerializer.create_deployment_to_xml(
                name,
                package_url,
                label,
                configuration,
                start_deployment,
                treat_warnings_as_error,
                extended_properties),
            async=True)

    def delete_deployment(self, service_name, deployment_name):
        '''
        Deletes the specified deployment.

        service_name: Name of the hosted service.
        deployment_name: The name of the deployment.
        '''
        _validate_not_none('service_name', service_name)
        _validate_not_none('deployment_name', deployment_name)
        return self._perform_delete(
            self._get_deployment_path_using_name(
                service_name, deployment_name),
            async=True)

    def swap_deployment(self, service_name, production, source_deployment):
        '''
        Initiates a virtual IP swap between the staging and production
        deployment environments for a service. If the service is currently
        running in the staging environment, it will be swapped to the
        production environment. If it is running in the production
        environment, it will be swapped to staging.

        service_name: Name of the hosted service.
        production: The name of the production deployment.
        source_deployment: The name of the source deployment.
        '''
        _validate_not_none('service_name', service_name)
        _validate_not_none('production', production)
        _validate_not_none('source_deployment', source_deployment)
        return self._perform_post(self._get_hosted_service_path(service_name),
                                  _XmlSerializer.swap_deployment_to_xml(
                                      production, source_deployment),
                                  async=True)

    def change_deployment_configuration(self, service_name, deployment_name,
                                        configuration,
                                        treat_warnings_as_error=False,
                                        mode='Auto', extended_properties=None):
        '''
        Initiates a change to the deployment configuration.

        service_name: Name of the hosted service.
        deployment_name: The name of the deployment.
        configuration:
            The base-64 encoded service configuration file for the deployment.
        treat_warnings_as_error:
            Indicates whether to treat package validation warnings as errors.
            If set to true, the Created Deployment operation fails if there
            are validation warnings on the service package.
        mode:
            If set to Manual, WalkUpgradeDomain must be called to apply the
            update. If set to Auto, the Windows Azure platform will
            automatically apply the update To each upgrade domain for the
            service. Possible values are: Auto, Manual
        extended_properties:
            Dictionary containing name/value pairs of storage account
            properties. You can have a maximum of 50 extended property
            name/value pairs. The maximum length of the Name element is 64
            characters, only alphanumeric characters and underscores are valid
            in the Name, and the name must start with a letter. The value has
            a maximum length of 255 characters.
        '''
        _validate_not_none('service_name', service_name)
        _validate_not_none('deployment_name', deployment_name)
        _validate_not_none('configuration', configuration)
        return self._perform_post(
            self._get_deployment_path_using_name(
                service_name, deployment_name) + '/?comp=config',
            _XmlSerializer.change_deployment_to_xml(
                configuration,
                treat_warnings_as_error,
                mode,
                extended_properties),
            async=True)

    def update_deployment_status(self, service_name, deployment_name, status):
        '''
        Initiates a change in deployment status.

        service_name: Name of the hosted service.
        deployment_name: The name of the deployment.
        status:
            The change to initiate to the deployment status. Possible values
            include: Running, Suspended
        '''
        _validate_not_none('service_name', service_name)
        _validate_not_none('deployment_name', deployment_name)
        _validate_not_none('status', status)
        return self._perform_post(
            self._get_deployment_path_using_name(
                service_name, deployment_name) + '/?comp=status',
            _XmlSerializer.update_deployment_status_to_xml(
                status),
            async=True)

    def upgrade_deployment(self, service_name, deployment_name, mode,
                           package_url, configuration, label, force,
                           role_to_upgrade=None, extended_properties=None):
        '''
        Initiates an upgrade.

        service_name: Name of the hosted service.
        deployment_name: The name of the deployment.
        mode:
            If set to Manual, WalkUpgradeDomain must be called to apply the
            update. If set to Auto, the Windows Azure platform will
            automatically apply the update To each upgrade domain for the
            service. Possible values are: Auto, Manual
        package_url:
            A URL that refers to the location of the service package in the
            Blob service. The service package can be located either in a
            storage account beneath the same subscription or a Shared Access
            Signature (SAS) URI from any storage account.
        configuration:
            The base-64 encoded service configuration file for the deployment.
        label:
            A name for the hosted service. The name can be up to 100 characters
            in length. It is recommended that the label be unique within the
            subscription. The name can be used to identify the hosted service
            for your tracking purposes.
        force:
            Specifies whether the rollback should proceed even when it will
            cause local data to be lost from some role instances. True if the
            rollback should proceed; otherwise false if the rollback should
            fail.
        role_to_upgrade: The name of the specific role to upgrade.
        extended_properties:
            Dictionary containing name/value pairs of storage account
            properties. You can have a maximum of 50 extended property
            name/value pairs. The maximum length of the Name element is 64
            characters, only alphanumeric characters and underscores are valid
            in the Name, and the name must start with a letter. The value has
            a maximum length of 255 characters.
        '''
        _validate_not_none('service_name', service_name)
        _validate_not_none('deployment_name', deployment_name)
        _validate_not_none('mode', mode)
        _validate_not_none('package_url', package_url)
        _validate_not_none('configuration', configuration)
        _validate_not_none('label', label)
        _validate_not_none('force', force)
        return self._perform_post(
            self._get_deployment_path_using_name(
                service_name, deployment_name) + '/?comp=upgrade',
            _XmlSerializer.upgrade_deployment_to_xml(
                mode,
                package_url,
                configuration,
                label,
                role_to_upgrade,
                force,
                extended_properties),
            async=True)

    def walk_upgrade_domain(self, service_name, deployment_name,
                            upgrade_domain):
        '''
        Specifies the next upgrade domain to be walked during manual in-place
        upgrade or configuration change.

        service_name: Name of the hosted service.
        deployment_name: The name of the deployment.
        upgrade_domain:
            An integer value that identifies the upgrade domain to walk.
            Upgrade domains are identified with a zero-based index: the first
            upgrade domain has an ID of 0, the second has an ID of 1, and so on.
        '''
        _validate_not_none('service_name', service_name)
        _validate_not_none('deployment_name', deployment_name)
        _validate_not_none('upgrade_domain', upgrade_domain)
        return self._perform_post(
            self._get_deployment_path_using_name(
                service_name, deployment_name) + '/?comp=walkupgradedomain',
            _XmlSerializer.walk_upgrade_domain_to_xml(
                upgrade_domain),
            async=True)

    def rollback_update_or_upgrade(self, service_name, deployment_name, mode,
                                   force):
        '''
        Cancels an in progress configuration change (update) or upgrade and
        returns the deployment to its state before the upgrade or
        configuration change was started.

        service_name: Name of the hosted service.
        deployment_name: The name of the deployment.
        mode:
            Specifies whether the rollback should proceed automatically.
                auto - The rollback proceeds without further user input.
                manual - You must call the Walk Upgrade Domain operation to
                         apply the rollback to each upgrade domain.
        force:
            Specifies whether the rollback should proceed even when it will
            cause local data to be lost from some role instances. True if the
            rollback should proceed; otherwise false if the rollback should
            fail.
        '''
        _validate_not_none('service_name', service_name)
        _validate_not_none('deployment_name', deployment_name)
        _validate_not_none('mode', mode)
        _validate_not_none('force', force)
        return self._perform_post(
            self._get_deployment_path_using_name(
                service_name, deployment_name) + '/?comp=rollback',
            _XmlSerializer.rollback_upgrade_to_xml(
                mode, force),
            async=True)

    def reboot_role_instance(self, service_name, deployment_name,
                             role_instance_name):
        '''
        Requests a reboot of a role instance that is running in a deployment.

        service_name: Name of the hosted service.
        deployment_name: The name of the deployment.
        role_instance_name: The name of the role instance.
        '''
        _validate_not_none('service_name', service_name)
        _validate_not_none('deployment_name', deployment_name)
        _validate_not_none('role_instance_name', role_instance_name)
        return self._perform_post(
            self._get_deployment_path_using_name(
                service_name, deployment_name) + \
                    '/roleinstances/' + _str(role_instance_name) + \
                    '?comp=reboot',
            '',
            async=True)

    def reimage_role_instance(self, service_name, deployment_name,
                              role_instance_name):
        '''
        Requests a reimage of a role instance that is running in a deployment.

        service_name: Name of the hosted service.
        deployment_name: The name of the deployment.
        role_instance_name: The name of the role instance.
        '''
        _validate_not_none('service_name', service_name)
        _validate_not_none('deployment_name', deployment_name)
        _validate_not_none('role_instance_name', role_instance_name)
        return self._perform_post(
            self._get_deployment_path_using_name(
                service_name, deployment_name) + \
                    '/roleinstances/' + _str(role_instance_name) + \
                    '?comp=reimage',
            '',
            async=True)

    def check_hosted_service_name_availability(self, service_name):
        '''
        Checks to see if the specified hosted service name is available, or if
        it has already been taken.

        service_name: Name of the hosted service.
        '''
        _validate_not_none('service_name', service_name)
        return self._perform_get(
            '/' + self.subscription_id +
            '/services/hostedservices/operations/isavailable/' +
            _str(service_name) + '',
            AvailabilityResponse)

    #--Operations for service certificates -------------------------------
    def list_service_certificates(self, service_name):
        '''
        Lists all of the service certificates associated with the specified
        hosted service.

        service_name: Name of the hosted service.
        '''
        _validate_not_none('service_name', service_name)
        return self._perform_get(
            '/' + self.subscription_id + '/services/hostedservices/' +
            _str(service_name) + '/certificates',
            Certificates)

    def get_service_certificate(self, service_name, thumbalgorithm, thumbprint):
        '''
        Returns the public data for the specified X.509 certificate associated
        with a hosted service.

        service_name: Name of the hosted service.
        thumbalgorithm: The algorithm for the certificate's thumbprint.
        thumbprint: The hexadecimal representation of the thumbprint.
        '''
        _validate_not_none('service_name', service_name)
        _validate_not_none('thumbalgorithm', thumbalgorithm)
        _validate_not_none('thumbprint', thumbprint)
        return self._perform_get(
            '/' + self.subscription_id + '/services/hostedservices/' +
            _str(service_name) + '/certificates/' +
            _str(thumbalgorithm) + '-' + _str(thumbprint) + '',
            Certificate)

    def add_service_certificate(self, service_name, data, certificate_format,
                                password):
        '''
        Adds a certificate to a hosted service.

        service_name: Name of the hosted service.
        data: The base-64 encoded form of the pfx file.
        certificate_format:
            The service certificate format. The only supported value is pfx.
        password: The certificate password.
        '''
        _validate_not_none('service_name', service_name)
        _validate_not_none('data', data)
        _validate_not_none('certificate_format', certificate_format)
        _validate_not_none('password', password)
        return self._perform_post(
            '/' + self.subscription_id + '/services/hostedservices/' +
            _str(service_name) + '/certificates',
            _XmlSerializer.certificate_file_to_xml(
                data, certificate_format, password),
            async=True)

    def delete_service_certificate(self, service_name, thumbalgorithm,
                                   thumbprint):
        '''
        Deletes a service certificate from the certificate store of a hosted
        service.

        service_name: Name of the hosted service.
        thumbalgorithm: The algorithm for the certificate's thumbprint.
        thumbprint: The hexadecimal representation of the thumbprint.
        '''
        _validate_not_none('service_name', service_name)
        _validate_not_none('thumbalgorithm', thumbalgorithm)
        _validate_not_none('thumbprint', thumbprint)
        return self._perform_delete(
            '/' + self.subscription_id + '/services/hostedservices/' +
            _str(service_name) + '/certificates/' +
            _str(thumbalgorithm) + '-' + _str(thumbprint),
            async=True)

    #--Operations for management certificates ----------------------------
    def list_management_certificates(self):
        '''
        The List Management Certificates operation lists and returns basic
        information about all of the management certificates associated with
        the specified subscription. Management certificates, which are also
        known as subscription certificates, authenticate clients attempting to
        connect to resources associated with your Windows Azure subscription.
        '''
        return self._perform_get('/' + self.subscription_id + '/certificates',
                                 SubscriptionCertificates)

    def get_management_certificate(self, thumbprint):
        '''
        The Get Management Certificate operation retrieves information about
        the management certificate with the specified thumbprint. Management
        certificates, which are also known as subscription certificates,
        authenticate clients attempting to connect to resources associated
        with your Windows Azure subscription.

        thumbprint: The thumbprint value of the certificate.
        '''
        _validate_not_none('thumbprint', thumbprint)
        return self._perform_get(
            '/' + self.subscription_id + '/certificates/' + _str(thumbprint),
            SubscriptionCertificate)

    def add_management_certificate(self, public_key, thumbprint, data):
        '''
        The Add Management Certificate operation adds a certificate to the
        list of management certificates. Management certificates, which are
        also known as subscription certificates, authenticate clients
        attempting to connect to resources associated with your Windows Azure
        subscription.

        public_key:
            A base64 representation of the management certificate public key.
        thumbprint:
            The thumb print that uniquely identifies the management
            certificate.
        data: The certificate's raw data in base-64 encoded .cer format.
        '''
        _validate_not_none('public_key', public_key)
        _validate_not_none('thumbprint', thumbprint)
        _validate_not_none('data', data)
        return self._perform_post(
            '/' + self.subscription_id + '/certificates',
            _XmlSerializer.subscription_certificate_to_xml(
                public_key, thumbprint, data))

    def delete_management_certificate(self, thumbprint):
        '''
        The Delete Management Certificate operation deletes a certificate from
        the list of management certificates. Management certificates, which
        are also known as subscription certificates, authenticate clients
        attempting to connect to resources associated with your Windows Azure
        subscription.

        thumbprint:
            The thumb print that uniquely identifies the management
            certificate.
        '''
        _validate_not_none('thumbprint', thumbprint)
        return self._perform_delete(
            '/' + self.subscription_id + '/certificates/' + _str(thumbprint))

    #--Operations for affinity groups ------------------------------------
    def list_affinity_groups(self):
        '''
        Lists the affinity groups associated with the specified subscription.
        '''
        return self._perform_get(
            '/' + self.subscription_id + '/affinitygroups',
            AffinityGroups)

    def get_affinity_group_properties(self, affinity_group_name):
        '''
        Returns the system properties associated with the specified affinity
        group.

        affinity_group_name: The name of the affinity group.
        '''
        _validate_not_none('affinity_group_name', affinity_group_name)
        return self._perform_get(
            '/' + self.subscription_id + '/affinitygroups/' +
            _str(affinity_group_name) + '',
            AffinityGroup)

    def create_affinity_group(self, name, label, location, description=None):
        '''
        Creates a new affinity group for the specified subscription.

        name: A name for the affinity group that is unique to the subscription.
        label:
            A name for the affinity group. The name can be up to 100 characters
            in length.
        location:
            The data center location where the affinity group will be created.
            To list available locations, use the list_location function.
        description:
            A description for the affinity group. The description can be up to
            1024 characters in length.
        '''
        _validate_not_none('name', name)
        _validate_not_none('label', label)
        _validate_not_none('location', location)
        return self._perform_post(
            '/' + self.subscription_id + '/affinitygroups',
            _XmlSerializer.create_affinity_group_to_xml(name,
                                                        label,
                                                        description,
                                                        location))

    def update_affinity_group(self, affinity_group_name, label,
                              description=None):
        '''
        Updates the label and/or the description for an affinity group for the
        specified subscription.

        affinity_group_name: The name of the affinity group.
        label:
            A name for the affinity group. The name can be up to 100 characters
            in length.
        description:
            A description for the affinity group. The description can be up to
            1024 characters in length.
        '''
        _validate_not_none('affinity_group_name', affinity_group_name)
        _validate_not_none('label', label)
        return self._perform_put(
            '/' + self.subscription_id + '/affinitygroups/' +
            _str(affinity_group_name),
            _XmlSerializer.update_affinity_group_to_xml(label, description))

    def delete_affinity_group(self, affinity_group_name):
        '''
        Deletes an affinity group in the specified subscription.

        affinity_group_name: The name of the affinity group.
        '''
        _validate_not_none('affinity_group_name', affinity_group_name)
        return self._perform_delete('/' + self.subscription_id + \
                                    '/affinitygroups/' + \
                                    _str(affinity_group_name))

    #--Operations for locations ------------------------------------------
    def list_locations(self):
        '''
        Lists all of the data center locations that are valid for your
        subscription.
        '''
        return self._perform_get('/' + self.subscription_id + '/locations',
                                 Locations)

    #--Operations for tracking asynchronous requests ---------------------
    def get_operation_status(self, request_id):
        '''
        Returns the status of the specified operation. After calling an
        asynchronous operation, you can call Get Operation Status to determine
        whether the operation has succeeded, failed, or is still in progress.

        request_id: The request ID for the request you wish to track.
        '''
        _validate_not_none('request_id', request_id)
        return self._perform_get(
            '/' + self.subscription_id + '/operations/' + _str(request_id),
            Operation)

    #--Operations for retrieving operating system information ------------
    def list_operating_systems(self):
        '''
        Lists the versions of the guest operating system that are currently
        available in Windows Azure.
        '''
        return self._perform_get(
            '/' + self.subscription_id + '/operatingsystems',
            OperatingSystems)

    def list_operating_system_families(self):
        '''
        Lists the guest operating system families available in Windows Azure,
        and also lists the operating system versions available for each family.
        '''
        return self._perform_get(
            '/' + self.subscription_id + '/operatingsystemfamilies',
            OperatingSystemFamilies)

    #--Operations for retrieving subscription history --------------------
    def get_subscription(self):
        '''
        Returns account and resource allocation information on the specified
        subscription.
        '''
        return self._perform_get('/' + self.subscription_id + '',
                                 Subscription)

    #--Operations for virtual machines -----------------------------------
    def get_role(self, service_name, deployment_name, role_name):
        '''
        Retrieves the specified virtual machine.

        service_name: The name of the service.
        deployment_name: The name of the deployment.
        role_name: The name of the role.
        '''
        _validate_not_none('service_name', service_name)
        _validate_not_none('deployment_name', deployment_name)
        _validate_not_none('role_name', role_name)
        return self._perform_get(
            self._get_role_path(service_name, deployment_name, role_name),
            PersistentVMRole)

    def create_virtual_machine_deployment(self, service_name, deployment_name,
                                          deployment_slot, label, role_name,
                                          system_config, os_virtual_hard_disk,
                                          network_config=None,
                                          availability_set_name=None,
                                          data_virtual_hard_disks=None,
                                          role_size=None,
                                          role_type='PersistentVMRole',
                                          virtual_network_name=None):
        '''
        Provisions a virtual machine based on the supplied configuration.

        service_name: Name of the hosted service.
        deployment_name:
            The name for the deployment. The deployment name must be unique
            among other deployments for the hosted service.
        deployment_slot:
            The environment to which the hosted service is deployed. Valid
            values are: staging, production
        label:
            Specifies an identifier for the deployment. The label can be up to
            100 characters long. The label can be used for tracking purposes.
        role_name: The name of the role.
        system_config:
            Contains the metadata required to provision a virtual machine from
            a Windows or Linux OS image.  Use an instance of
            WindowsConfigurationSet or LinuxConfigurationSet.
        os_virtual_hard_disk:
            Contains the parameters Windows Azure uses to create the operating
            system disk for the virtual machine.
        network_config:
            Encapsulates the metadata required to create the virtual network
            configuration for a virtual machine. If you do not include a
            network configuration set you will not be able to access the VM
            through VIPs over the internet. If your virtual machine belongs to
            a virtual network you can not specify which subnet address space
            it resides under.
        availability_set_name:
            Specifies the name of an availability set to which to add the
            virtual machine. This value controls the virtual machine
            allocation in the Windows Azure environment. Virtual machines
            specified in the same availability set are allocated to different
            nodes to maximize availability.
        data_virtual_hard_disks:
            Contains the parameters Windows Azure uses to create a data disk
            for a virtual machine.
        role_size:
            The size of the virtual machine to allocate. The default value is
            Small. Possible values are: ExtraSmall, Small, Medium, Large,
            ExtraLarge. The specified value must be compatible with the disk
            selected in the OSVirtualHardDisk values.
        role_type:
            The type of the role for the virtual machine. The only supported
            value is PersistentVMRole.
        virtual_network_name:
            Specifies the name of an existing virtual network to which the
            deployment will belong.
        '''
        _validate_not_none('service_name', service_name)
        _validate_not_none('deployment_name', deployment_name)
        _validate_not_none('deployment_slot', deployment_slot)
        _validate_not_none('label', label)
        _validate_not_none('role_name', role_name)
        _validate_not_none('system_config', system_config)
        _validate_not_none('os_virtual_hard_disk', os_virtual_hard_disk)
        return self._perform_post(
            self._get_deployment_path_using_name(service_name),
            _XmlSerializer.virtual_machine_deployment_to_xml(
                deployment_name,
                deployment_slot,
                label,
                role_name,
                system_config,
                os_virtual_hard_disk,
                role_type,
                network_config,
                availability_set_name,
                data_virtual_hard_disks,
                role_size,
                virtual_network_name),
            async=True)

    def add_role(self, service_name, deployment_name, role_name, system_config,
                 os_virtual_hard_disk, network_config=None,
                 availability_set_name=None, data_virtual_hard_disks=None,
                 role_size=None, role_type='PersistentVMRole'):
        '''
        Adds a virtual machine to an existing deployment.

        service_name: The name of the service.
        deployment_name: The name of the deployment.
        role_name: The name of the role.
        system_config:
            Contains the metadata required to provision a virtual machine from
            a Windows or Linux OS image.  Use an instance of
            WindowsConfigurationSet or LinuxConfigurationSet.
        os_virtual_hard_disk:
            Contains the parameters Windows Azure uses to create the operating
            system disk for the virtual machine.
        network_config:
            Encapsulates the metadata required to create the virtual network
            configuration for a virtual machine. If you do not include a
            network configuration set you will not be able to access the VM
            through VIPs over the internet. If your virtual machine belongs to
            a virtual network you can not specify which subnet address space
            it resides under.
        availability_set_name:
            Specifies the name of an availability set to which to add the
            virtual machine. This value controls the virtual machine allocation
            in the Windows Azure environment. Virtual machines specified in the
            same availability set are allocated to different nodes to maximize
            availability.
        data_virtual_hard_disks:
            Contains the parameters Windows Azure uses to create a data disk
            for a virtual machine.
        role_size:
            The size of the virtual machine to allocate. The default value is
            Small. Possible values are: ExtraSmall, Small, Medium, Large,
            ExtraLarge. The specified value must be compatible with the disk
            selected in the OSVirtualHardDisk values.
        role_type:
            The type of the role for the virtual machine. The only supported
            value is PersistentVMRole.
        '''
        _validate_not_none('service_name', service_name)
        _validate_not_none('deployment_name', deployment_name)
        _validate_not_none('role_name', role_name)
        _validate_not_none('system_config', system_config)
        _validate_not_none('os_virtual_hard_disk', os_virtual_hard_disk)
        return self._perform_post(
            self._get_role_path(service_name, deployment_name),
            _XmlSerializer.add_role_to_xml(
                role_name,
                system_config,
                os_virtual_hard_disk,
                role_type,
                network_config,
                availability_set_name,
                data_virtual_hard_disks,
                role_size),
            async=True)

    def update_role(self, service_name, deployment_name, role_name,
                    os_virtual_hard_disk=None, network_config=None,
                    availability_set_name=None, data_virtual_hard_disks=None,
                    role_size=None, role_type='PersistentVMRole'):
        '''
        Updates the specified virtual machine.

        service_name: The name of the service.
        deployment_name: The name of the deployment.
        role_name: The name of the role.
        os_virtual_hard_disk:
            Contains the parameters Windows Azure uses to create the operating
            system disk for the virtual machine.
        network_config:
            Encapsulates the metadata required to create the virtual network
            configuration for a virtual machine. If you do not include a
            network configuration set you will not be able to access the VM
            through VIPs over the internet. If your virtual machine belongs to
            a virtual network you can not specify which subnet address space
            it resides under.
        availability_set_name:
            Specifies the name of an availability set to which to add the
            virtual machine. This value controls the virtual machine allocation
            in the Windows Azure environment. Virtual machines specified in the
            same availability set are allocated to different nodes to maximize
            availability.
        data_virtual_hard_disks:
            Contains the parameters Windows Azure uses to create a data disk
            for a virtual machine.
        role_size:
            The size of the virtual machine to allocate. The default value is
            Small. Possible values are: ExtraSmall, Small, Medium, Large,
            ExtraLarge. The specified value must be compatible with the disk
            selected in the OSVirtualHardDisk values.
        role_type:
            The type of the role for the virtual machine. The only supported
            value is PersistentVMRole.
        '''
        _validate_not_none('service_name', service_name)
        _validate_not_none('deployment_name', deployment_name)
        _validate_not_none('role_name', role_name)
        return self._perform_put(
            self._get_role_path(service_name, deployment_name, role_name),
            _XmlSerializer.update_role_to_xml(
                role_name,
                os_virtual_hard_disk,
                role_type,
                network_config,
                availability_set_name,
                data_virtual_hard_disks,
                role_size),
            async=True)

    def delete_role(self, service_name, deployment_name, role_name):
        '''
        Deletes the specified virtual machine.

        service_name: The name of the service.
        deployment_name: The name of the deployment.
        role_name: The name of the role.
        '''
        _validate_not_none('service_name', service_name)
        _validate_not_none('deployment_name', deployment_name)
        _validate_not_none('role_name', role_name)
        return self._perform_delete(
            self._get_role_path(service_name, deployment_name, role_name),
            async=True)

    def capture_role(self, service_name, deployment_name, role_name,
                     post_capture_action, target_image_name,
                     target_image_label, provisioning_configuration=None):
        '''
        The Capture Role operation captures a virtual machine image to your
        image gallery. From the captured image, you can create additional
        customized virtual machines.

        service_name: The name of the service.
        deployment_name: The name of the deployment.
        role_name: The name of the role.
        post_capture_action:
            Specifies the action after capture operation completes. Possible
            values are: Delete, Reprovision.
        target_image_name:
            Specifies the image name of the captured virtual machine.
        target_image_label:
            Specifies the friendly name of the captured virtual machine.
        provisioning_configuration:
            Use an instance of WindowsConfigurationSet or LinuxConfigurationSet.
        '''
        _validate_not_none('service_name', service_name)
        _validate_not_none('deployment_name', deployment_name)
        _validate_not_none('role_name', role_name)
        _validate_not_none('post_capture_action', post_capture_action)
        _validate_not_none('target_image_name', target_image_name)
        _validate_not_none('target_image_label', target_image_label)
        return self._perform_post(
            self._get_role_instance_operations_path(
                service_name, deployment_name, role_name),
            _XmlSerializer.capture_role_to_xml(
                post_capture_action,
                target_image_name,
                target_image_label,
                provisioning_configuration),
            async=True)

    def start_role(self, service_name, deployment_name, role_name):
        '''
        Starts the specified virtual machine.

        service_name: The name of the service.
        deployment_name: The name of the deployment.
        role_name: The name of the role.
        '''
        _validate_not_none('service_name', service_name)
        _validate_not_none('deployment_name', deployment_name)
        _validate_not_none('role_name', role_name)
        return self._perform_post(
            self._get_role_instance_operations_path(
                service_name, deployment_name, role_name),
            _XmlSerializer.start_role_operation_to_xml(),
            async=True)

    def start_roles(self, service_name, deployment_name, role_names):
        '''
        Starts the specified virtual machines.

        service_name: The name of the service.
        deployment_name: The name of the deployment.
        role_names: The names of the roles, as an enumerable of strings.
        '''
        _validate_not_none('service_name', service_name)
        _validate_not_none('deployment_name', deployment_name)
        _validate_not_none('role_names', role_names)
        return self._perform_post(
            self._get_roles_operations_path(service_name, deployment_name),
            _XmlSerializer.start_roles_operation_to_xml(role_names),
            async=True)

    def restart_role(self, service_name, deployment_name, role_name):
        '''
        Restarts the specified virtual machine.

        service_name: The name of the service.
        deployment_name: The name of the deployment.
        role_name: The name of the role.
        '''
        _validate_not_none('service_name', service_name)
        _validate_not_none('deployment_name', deployment_name)
        _validate_not_none('role_name', role_name)
        return self._perform_post(
            self._get_role_instance_operations_path(
                service_name, deployment_name, role_name),
            _XmlSerializer.restart_role_operation_to_xml(
            ),
            async=True)

    def shutdown_role(self, service_name, deployment_name, role_name,
                      post_shutdown_action='Stopped'):
        '''
        Shuts down the specified virtual machine.

        service_name: The name of the service.
        deployment_name: The name of the deployment.
        role_name: The name of the role.
        post_shutdown_action:
            Specifies how the Virtual Machine should be shut down. Values are:
                Stopped
                    Shuts down the Virtual Machine but retains the compute
                    resources. You will continue to be billed for the resources
                    that the stopped machine uses.
                StoppedDeallocated
                    Shuts down the Virtual Machine and releases the compute
                    resources. You are not billed for the compute resources that
                    this Virtual Machine uses. If a static Virtual Network IP
                    address is assigned to the Virtual Machine, it is reserved.
        '''
        _validate_not_none('service_name', service_name)
        _validate_not_none('deployment_name', deployment_name)
        _validate_not_none('role_name', role_name)
        _validate_not_none('post_shutdown_action', post_shutdown_action)
        return self._perform_post(
            self._get_role_instance_operations_path(
                service_name, deployment_name, role_name),
            _XmlSerializer.shutdown_role_operation_to_xml(post_shutdown_action),
            async=True)

    def shutdown_roles(self, service_name, deployment_name, role_names,
                       post_shutdown_action='Stopped'):
        '''
        Shuts down the specified virtual machines.

        service_name: The name of the service.
        deployment_name: The name of the deployment.
        role_names: The names of the roles, as an enumerable of strings.
        post_shutdown_action:
            Specifies how the Virtual Machine should be shut down. Values are:
                Stopped
                    Shuts down the Virtual Machine but retains the compute
                    resources. You will continue to be billed for the resources
                    that the stopped machine uses.
                StoppedDeallocated
                    Shuts down the Virtual Machine and releases the compute
                    resources. You are not billed for the compute resources that
                    this Virtual Machine uses. If a static Virtual Network IP
                    address is assigned to the Virtual Machine, it is reserved.
        '''
        _validate_not_none('service_name', service_name)
        _validate_not_none('deployment_name', deployment_name)
        _validate_not_none('role_names', role_names)
        _validate_not_none('post_shutdown_action', post_shutdown_action)
        return self._perform_post(
            self._get_roles_operations_path(service_name, deployment_name),
            _XmlSerializer.shutdown_roles_operation_to_xml(
                role_names, post_shutdown_action),
            async=True)

    #--Operations for virtual machine images -----------------------------
    def list_os_images(self):
        '''
        Retrieves a list of the OS images from the image repository.
        '''
        return self._perform_get(self._get_image_path(),
                                 Images)

    def get_os_image(self, image_name):
        '''
        Retrieves an OS image from the image repository.
        '''
        return self._perform_get(self._get_image_path(image_name),
                                 OSImage)

    def add_os_image(self, label, media_link, name, os):
        '''
        Adds an OS image that is currently stored in a storage account in your
        subscription to the image repository.

        label: Specifies the friendly name of the image.
        media_link:
            Specifies the location of the blob in Windows Azure blob store
            where the media for the image is located. The blob location must
            belong to a storage account in the subscription specified by the
            <subscription-id> value in the operation call. Example:
            http://example.blob.core.windows.net/disks/mydisk.vhd
        name:
            Specifies a name for the OS image that Windows Azure uses to
            identify the image when creating one or more virtual machines.
        os:
            The operating system type of the OS image. Possible values are:
            Linux, Windows
        '''
        _validate_not_none('label', label)
        _validate_not_none('media_link', media_link)
        _validate_not_none('name', name)
        _validate_not_none('os', os)
        return self._perform_post(self._get_image_path(),
                                  _XmlSerializer.os_image_to_xml(
                                      label, media_link, name, os),
                                  async=True)

    def update_os_image(self, image_name, label, media_link, name, os):
        '''
        Updates an OS image that in your image repository.

        image_name: The name of the image to update.
        label:
            Specifies the friendly name of the image to be updated. You cannot
            use this operation to update images provided by the Windows Azure
            platform.
        media_link:
            Specifies the location of the blob in Windows Azure blob store
            where the media for the image is located. The blob location must
            belong to a storage account in the subscription specified by the
            <subscription-id> value in the operation call. Example:
            http://example.blob.core.windows.net/disks/mydisk.vhd
        name:
            Specifies a name for the OS image that Windows Azure uses to
            identify the image when creating one or more VM Roles.
        os:
            The operating system type of the OS image. Possible values are:
            Linux, Windows
        '''
        _validate_not_none('image_name', image_name)
        _validate_not_none('label', label)
        _validate_not_none('media_link', media_link)
        _validate_not_none('name', name)
        _validate_not_none('os', os)
        return self._perform_put(self._get_image_path(image_name),
                                 _XmlSerializer.os_image_to_xml(
                                     label, media_link, name, os),
                                 async=True)

    def delete_os_image(self, image_name, delete_vhd=False):
        '''
        Deletes the specified OS image from your image repository.

        image_name: The name of the image.
        delete_vhd: Deletes the underlying vhd blob in Azure storage.
        '''
        _validate_not_none('image_name', image_name)
        path = self._get_image_path(image_name)
        if delete_vhd:
            path += '?comp=media'
        return self._perform_delete(path, async=True)

    #--Operations for virtual machine disks ------------------------------
    def get_data_disk(self, service_name, deployment_name, role_name, lun):
        '''
        Retrieves the specified data disk from a virtual machine.

        service_name: The name of the service.
        deployment_name: The name of the deployment.
        role_name: The name of the role.
        lun: The Logical Unit Number (LUN) for the disk.
        '''
        _validate_not_none('service_name', service_name)
        _validate_not_none('deployment_name', deployment_name)
        _validate_not_none('role_name', role_name)
        _validate_not_none('lun', lun)
        return self._perform_get(
            self._get_data_disk_path(
                service_name, deployment_name, role_name, lun),
            DataVirtualHardDisk)

    def add_data_disk(self, service_name, deployment_name, role_name, lun,
                      host_caching=None, media_link=None, disk_label=None,
                      disk_name=None, logical_disk_size_in_gb=None,
                      source_media_link=None):
        '''
        Adds a data disk to a virtual machine.

        service_name: The name of the service.
        deployment_name: The name of the deployment.
        role_name: The name of the role.
        lun:
            Specifies the Logical Unit Number (LUN) for the disk. The LUN
            specifies the slot in which the data drive appears when mounted
            for usage by the virtual machine. Valid LUN values are 0 through 15.
        host_caching:
            Specifies the platform caching behavior of data disk blob for
            read/write efficiency. The default vault is ReadOnly. Possible
            values are: None, ReadOnly, ReadWrite
        media_link:
            Specifies the location of the blob in Windows Azure blob store
            where the media for the disk is located. The blob location must
            belong to the storage account in the subscription specified by the
            <subscription-id> value in the operation call. Example:
            http://example.blob.core.windows.net/disks/mydisk.vhd
        disk_label:
            Specifies the description of the data disk. When you attach a disk,
            either by directly referencing a media using the MediaLink element
            or specifying the target disk size, you can use the DiskLabel
            element to customize the name property of the target data disk.
        disk_name:
            Specifies the name of the disk. Windows Azure uses the specified
            disk to create the data disk for the machine and populates this
            field with the disk name.
        logical_disk_size_in_gb:
            Specifies the size, in GB, of an empty disk to be attached to the
            role. The disk can be created as part of disk attach or create VM
            role call by specifying the value for this property. Windows Azure
            creates the empty disk based on size preference and attaches the
            newly created disk to the Role.
        source_media_link:
            Specifies the location of a blob in account storage which is
            mounted as a data disk when the virtual machine is created.
        '''
        _validate_not_none('service_name', service_name)
        _validate_not_none('deployment_name', deployment_name)
        _validate_not_none('role_name', role_name)
        _validate_not_none('lun', lun)
        return self._perform_post(
            self._get_data_disk_path(service_name, deployment_name, role_name),
            _XmlSerializer.data_virtual_hard_disk_to_xml(
                host_caching,
                disk_label,
                disk_name,
                lun,
                logical_disk_size_in_gb,
                media_link,
                source_media_link),
            async=True)

    def update_data_disk(self, service_name, deployment_name, role_name, lun,
                         host_caching=None, media_link=None, updated_lun=None,
                         disk_label=None, disk_name=None,
                         logical_disk_size_in_gb=None):
        '''
        Updates the specified data disk attached to the specified virtual
        machine.

        service_name: The name of the service.
        deployment_name: The name of the deployment.
        role_name: The name of the role.
        lun:
            Specifies the Logical Unit Number (LUN) for the disk. The LUN
            specifies the slot in which the data drive appears when mounted
            for usage by the virtual machine. Valid LUN values are 0 through
            15.
        host_caching:
            Specifies the platform caching behavior of data disk blob for
            read/write efficiency. The default vault is ReadOnly. Possible
            values are: None, ReadOnly, ReadWrite
        media_link:
            Specifies the location of the blob in Windows Azure blob store
            where the media for the disk is located. The blob location must
            belong to the storage account in the subscription specified by
            the <subscription-id> value in the operation call. Example:
            http://example.blob.core.windows.net/disks/mydisk.vhd
        updated_lun:
            Specifies the Logical Unit Number (LUN) for the disk. The LUN
            specifies the slot in which the data drive appears when mounted
            for usage by the virtual machine. Valid LUN values are 0 through 15.
        disk_label:
            Specifies the description of the data disk. When you attach a disk,
            either by directly referencing a media using the MediaLink element
            or specifying the target disk size, you can use the DiskLabel
            element to customize the name property of the target data disk.
        disk_name:
            Specifies the name of the disk. Windows Azure uses the specified
            disk to create the data disk for the machine and populates this
            field with the disk name.
        logical_disk_size_in_gb:
            Specifies the size, in GB, of an empty disk to be attached to the
            role. The disk can be created as part of disk attach or create VM
            role call by specifying the value for this property. Windows Azure
            creates the empty disk based on size preference and attaches the
            newly created disk to the Role.
        '''
        _validate_not_none('service_name', service_name)
        _validate_not_none('deployment_name', deployment_name)
        _validate_not_none('role_name', role_name)
        _validate_not_none('lun', lun)
        return self._perform_put(
            self._get_data_disk_path(
                service_name, deployment_name, role_name, lun),
            _XmlSerializer.data_virtual_hard_disk_to_xml(
                host_caching,
                disk_label,
                disk_name,
                updated_lun,
                logical_disk_size_in_gb,
                media_link,
                None),
            async=True)

    def delete_data_disk(self, service_name, deployment_name, role_name, lun, delete_vhd=False):
        '''
        Removes the specified data disk from a virtual machine.

        service_name: The name of the service.
        deployment_name: The name of the deployment.
        role_name: The name of the role.
        lun: The Logical Unit Number (LUN) for the disk.
        delete_vhd: Deletes the underlying vhd blob in Azure storage.
        '''
        _validate_not_none('service_name', service_name)
        _validate_not_none('deployment_name', deployment_name)
        _validate_not_none('role_name', role_name)
        _validate_not_none('lun', lun)
        path = self._get_data_disk_path(service_name, deployment_name, role_name, lun)
        if delete_vhd:
            path += '?comp=media'
        return self._perform_delete(path, async=True)

    #--Operations for virtual machine disks ------------------------------
    def list_disks(self):
        '''
        Retrieves a list of the disks in your image repository.
        '''
        return self._perform_get(self._get_disk_path(),
                                 Disks)

    def get_disk(self, disk_name):
        '''
        Retrieves a disk from your image repository.
        '''
        return self._perform_get(self._get_disk_path(disk_name),
                                 Disk)

    def add_disk(self, has_operating_system, label, media_link, name, os):
        '''
        Adds a disk to the user image repository. The disk can be an OS disk
        or a data disk.

        has_operating_system:
            Specifies whether the disk contains an operation system. Only a
            disk with an operating system installed can be mounted as OS Drive.
        label: Specifies the description of the disk.
        media_link:
            Specifies the location of the blob in Windows Azure blob store
            where the media for the disk is located. The blob location must
            belong to the storage account in the current subscription specified
            by the <subscription-id> value in the operation call. Example:
            http://example.blob.core.windows.net/disks/mydisk.vhd
        name:
            Specifies a name for the disk. Windows Azure uses the name to
            identify the disk when creating virtual machines from the disk.
        os: The OS type of the disk. Possible values are: Linux, Windows
        '''
        _validate_not_none('has_operating_system', has_operating_system)
        _validate_not_none('label', label)
        _validate_not_none('media_link', media_link)
        _validate_not_none('name', name)
        _validate_not_none('os', os)
        return self._perform_post(self._get_disk_path(),
                                  _XmlSerializer.disk_to_xml(
                                      has_operating_system,
                                      label,
                                      media_link,
                                      name,
                                      os))

    def update_disk(self, disk_name, has_operating_system, label, media_link,
                    name, os):
        '''
        Updates an existing disk in your image repository.

        disk_name: The name of the disk to update.
        has_operating_system:
            Specifies whether the disk contains an operation system. Only a
            disk with an operating system installed can be mounted as OS Drive.
        label: Specifies the description of the disk.
        media_link:
            Specifies the location of the blob in Windows Azure blob store
            where the media for the disk is located. The blob location must
            belong to the storage account in the current subscription specified
            by the <subscription-id> value in the operation call. Example:
            http://example.blob.core.windows.net/disks/mydisk.vhd
        name:
            Specifies a name for the disk. Windows Azure uses the name to
            identify the disk when creating virtual machines from the disk.
        os: The OS type of the disk. Possible values are: Linux, Windows
        '''
        _validate_not_none('disk_name', disk_name)
        _validate_not_none('has_operating_system', has_operating_system)
        _validate_not_none('label', label)
        _validate_not_none('media_link', media_link)
        _validate_not_none('name', name)
        _validate_not_none('os', os)
        return self._perform_put(self._get_disk_path(disk_name),
                                 _XmlSerializer.disk_to_xml(
                                     has_operating_system,
                                     label,
                                     media_link,
                                     name,
                                     os))

    def delete_disk(self, disk_name, delete_vhd=False):
        '''
        Deletes the specified data or operating system disk from your image
        repository.

        disk_name: The name of the disk to delete.
        delete_vhd: Deletes the underlying vhd blob in Azure storage.
        '''
        _validate_not_none('disk_name', disk_name)
        path = self._get_disk_path(disk_name)
        if delete_vhd:
            path += '?comp=media'
        return self._perform_delete(path)

    #--Operations for virtual networks  ------------------------------
    def list_virtual_network_sites(self):
        '''
        Retrieves a list of the virtual networks.
        '''
        return self._perform_get(self._get_virtual_network_site_path(), VirtualNetworkSites)
  
      #--Helper functions --------------------------------------------------
    def _get_virtual_network_site_path(self):
        return self._get_path('services/networking/virtualnetwork', None)

    def _get_storage_service_path(self, service_name=None):
        return self._get_path('services/storageservices', service_name)

    def _get_hosted_service_path(self, service_name=None):
        return self._get_path('services/hostedservices', service_name)

    def _get_deployment_path_using_slot(self, service_name, slot=None):
        return self._get_path('services/hostedservices/' + _str(service_name) +
                              '/deploymentslots', slot)

    def _get_deployment_path_using_name(self, service_name,
                                        deployment_name=None):
        return self._get_path('services/hostedservices/' + _str(service_name) +
                              '/deployments', deployment_name)

    def _get_role_path(self, service_name, deployment_name, role_name=None):
        return self._get_path('services/hostedservices/' + _str(service_name) +
                              '/deployments/' + deployment_name +
                              '/roles', role_name)

    def _get_role_instance_operations_path(self, service_name, deployment_name,
                                           role_name=None):
        return self._get_path('services/hostedservices/' + _str(service_name) +
                              '/deployments/' + deployment_name +
                              '/roleinstances', role_name) + '/Operations'

    def _get_roles_operations_path(self, service_name, deployment_name):
        return self._get_path('services/hostedservices/' + _str(service_name) +
                              '/deployments/' + deployment_name +
                              '/roles/Operations', None)

    def _get_data_disk_path(self, service_name, deployment_name, role_name,
                            lun=None):
        return self._get_path('services/hostedservices/' + _str(service_name) +
                              '/deployments/' + _str(deployment_name) +
                              '/roles/' + _str(role_name) + '/DataDisks', lun)

    def _get_disk_path(self, disk_name=None):
        return self._get_path('services/disks', disk_name)

    def _get_image_path(self, image_name=None):
        return self._get_path('services/images', image_name)

########NEW FILE########
__FILENAME__ = blobservice
#-------------------------------------------------------------------------
# Copyright (c) Microsoft.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#--------------------------------------------------------------------------
from azure import (
    WindowsAzureError,
    BLOB_SERVICE_HOST_BASE,
    DEV_BLOB_HOST,
    _ERROR_VALUE_NEGATIVE,
    _ERROR_PAGE_BLOB_SIZE_ALIGNMENT,
    _convert_class_to_xml,
    _dont_fail_not_exist,
    _dont_fail_on_exist,
    _encode_base64,
    _get_request_body,
    _get_request_body_bytes_only,
    _int_or_none,
    _parse_enum_results_list,
    _parse_response,
    _parse_response_for_dict,
    _parse_response_for_dict_filter,
    _parse_response_for_dict_prefix,
    _parse_simple_list,
    _str,
    _str_or_none,
    _update_request_uri_query_local_storage,
    _validate_type_bytes,
    _validate_not_none,
    )
from azure.http import HTTPRequest
from azure.storage import (
    Container,
    ContainerEnumResults,
    PageList,
    PageRange,
    SignedIdentifiers,
    StorageServiceProperties,
    _convert_block_list_to_xml,
    _convert_response_to_block_list,
    _create_blob_result,
    _parse_blob_enum_results_list,
    _update_storage_blob_header,
    )
from azure.storage.storageclient import _StorageClient
from os import path
import sys
if sys.version_info >= (3,):
    from io import BytesIO
else:
    from cStringIO import StringIO as BytesIO

# Keep this value sync with _ERROR_PAGE_BLOB_SIZE_ALIGNMENT
_PAGE_SIZE = 512

class BlobService(_StorageClient):

    '''
    This is the main class managing Blob resources.
    '''

    def __init__(self, account_name=None, account_key=None, protocol='https',
                 host_base=BLOB_SERVICE_HOST_BASE, dev_host=DEV_BLOB_HOST):
        '''
        account_name: your storage account name, required for all operations.
        account_key: your storage account key, required for all operations.
        protocol: Optional. Protocol. Defaults to https.
        host_base:
            Optional. Live host base url. Defaults to Azure url. Override this
            for on-premise.
        dev_host: Optional. Dev host url. Defaults to localhost.
        '''
        self._BLOB_MAX_DATA_SIZE = 64 * 1024 * 1024
        self._BLOB_MAX_CHUNK_DATA_SIZE = 4 * 1024 * 1024
        super(BlobService, self).__init__(
            account_name, account_key, protocol, host_base, dev_host)

    def make_blob_url(self, container_name, blob_name, account_name=None,
                      protocol=None, host_base=None):
        '''
        Creates the url to access a blob.

        container_name: Name of container.
        blob_name: Name of blob.
        account_name:
            Name of the storage account. If not specified, uses the account
            specified when BlobService was initialized.
        protocol:
            Protocol to use: 'http' or 'https'. If not specified, uses the
            protocol specified when BlobService was initialized.
        host_base:
            Live host base url.  If not specified, uses the host base specified
            when BlobService was initialized.
        '''
        if not account_name:
            account_name = self.account_name
        if not protocol:
            protocol = self.protocol
        if not host_base:
            host_base = self.host_base

        return '{0}://{1}{2}/{3}/{4}'.format(protocol,
                                             account_name,
                                             host_base,
                                             container_name,
                                             blob_name)

    def list_containers(self, prefix=None, marker=None, maxresults=None,
                        include=None):
        '''
        The List Containers operation returns a list of the containers under
        the specified account.

        prefix:
            Optional. Filters the results to return only containers whose names
            begin with the specified prefix.
        marker:
            Optional. A string value that identifies the portion of the list to
            be returned with the next list operation.
        maxresults:
            Optional. Specifies the maximum number of containers to return.
        include:
            Optional. Include this parameter to specify that the container's
            metadata be returned as part of the response body. set this
            parameter to string 'metadata' to get container's metadata.
        '''
        request = HTTPRequest()
        request.method = 'GET'
        request.host = self._get_host()
        request.path = '/?comp=list'
        request.query = [
            ('prefix', _str_or_none(prefix)),
            ('marker', _str_or_none(marker)),
            ('maxresults', _int_or_none(maxresults)),
            ('include', _str_or_none(include))
        ]
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_blob_header(
            request, self.account_name, self.account_key)
        response = self._perform_request(request)

        return _parse_enum_results_list(response,
                                        ContainerEnumResults,
                                        "Containers",
                                        Container)

    def create_container(self, container_name, x_ms_meta_name_values=None,
                         x_ms_blob_public_access=None, fail_on_exist=False):
        '''
        Creates a new container under the specified account. If the container
        with the same name already exists, the operation fails.

        container_name: Name of container to create.
        x_ms_meta_name_values:
            Optional. A dict with name_value pairs to associate with the
            container as metadata. Example:{'Category':'test'}
        x_ms_blob_public_access:
            Optional. Possible values include: container, blob
        fail_on_exist:
            specify whether to throw an exception when the container exists.
        '''
        _validate_not_none('container_name', container_name)
        request = HTTPRequest()
        request.method = 'PUT'
        request.host = self._get_host()
        request.path = '/' + _str(container_name) + '?restype=container'
        request.headers = [
            ('x-ms-meta-name-values', x_ms_meta_name_values),
            ('x-ms-blob-public-access', _str_or_none(x_ms_blob_public_access))
        ]
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_blob_header(
            request, self.account_name, self.account_key)
        if not fail_on_exist:
            try:
                self._perform_request(request)
                return True
            except WindowsAzureError as ex:
                _dont_fail_on_exist(ex)
                return False
        else:
            self._perform_request(request)
            return True

    def get_container_properties(self, container_name, x_ms_lease_id=None):
        '''
        Returns all user-defined metadata and system properties for the
        specified container.

        container_name: Name of existing container.
        x_ms_lease_id:
            If specified, get_container_properties only succeeds if the
            container's lease is active and matches this ID.
        '''
        _validate_not_none('container_name', container_name)
        request = HTTPRequest()
        request.method = 'GET'
        request.host = self._get_host()
        request.path = '/' + _str(container_name) + '?restype=container'
        request.headers = [('x-ms-lease-id', _str_or_none(x_ms_lease_id))]
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_blob_header(
            request, self.account_name, self.account_key)
        response = self._perform_request(request)

        return _parse_response_for_dict(response)

    def get_container_metadata(self, container_name, x_ms_lease_id=None):
        '''
        Returns all user-defined metadata for the specified container. The
        metadata will be in returned dictionary['x-ms-meta-(name)'].

        container_name: Name of existing container.
        x_ms_lease_id:
            If specified, get_container_metadata only succeeds if the
            container's lease is active and matches this ID.
        '''
        _validate_not_none('container_name', container_name)
        request = HTTPRequest()
        request.method = 'GET'
        request.host = self._get_host()
        request.path = '/' + \
            _str(container_name) + '?restype=container&comp=metadata'
        request.headers = [('x-ms-lease-id', _str_or_none(x_ms_lease_id))]
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_blob_header(
            request, self.account_name, self.account_key)
        response = self._perform_request(request)

        return _parse_response_for_dict_prefix(response, prefixes=['x-ms-meta'])

    def set_container_metadata(self, container_name,
                               x_ms_meta_name_values=None, x_ms_lease_id=None):
        '''
        Sets one or more user-defined name-value pairs for the specified
        container.

        container_name: Name of existing container.
        x_ms_meta_name_values:
            A dict containing name, value for metadata.
            Example: {'category':'test'}
        x_ms_lease_id:
            If specified, set_container_metadata only succeeds if the
            container's lease is active and matches this ID.
        '''
        _validate_not_none('container_name', container_name)
        request = HTTPRequest()
        request.method = 'PUT'
        request.host = self._get_host()
        request.path = '/' + \
            _str(container_name) + '?restype=container&comp=metadata'
        request.headers = [
            ('x-ms-meta-name-values', x_ms_meta_name_values),
            ('x-ms-lease-id', _str_or_none(x_ms_lease_id)),
        ]
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_blob_header(
            request, self.account_name, self.account_key)
        self._perform_request(request)

    def get_container_acl(self, container_name, x_ms_lease_id=None):
        '''
        Gets the permissions for the specified container.

        container_name: Name of existing container.
        x_ms_lease_id:
            If specified, get_container_acl only succeeds if the
            container's lease is active and matches this ID.
        '''
        _validate_not_none('container_name', container_name)
        request = HTTPRequest()
        request.method = 'GET'
        request.host = self._get_host()
        request.path = '/' + \
            _str(container_name) + '?restype=container&comp=acl'
        request.headers = [('x-ms-lease-id', _str_or_none(x_ms_lease_id))]
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_blob_header(
            request, self.account_name, self.account_key)
        response = self._perform_request(request)

        return _parse_response(response, SignedIdentifiers)

    def set_container_acl(self, container_name, signed_identifiers=None,
                          x_ms_blob_public_access=None, x_ms_lease_id=None):
        '''
        Sets the permissions for the specified container.

        container_name: Name of existing container.
        signed_identifiers: SignedIdentifers instance
        x_ms_blob_public_access:
            Optional. Possible values include: container, blob
        x_ms_lease_id:
            If specified, set_container_acl only succeeds if the
            container's lease is active and matches this ID.
        '''
        _validate_not_none('container_name', container_name)
        request = HTTPRequest()
        request.method = 'PUT'
        request.host = self._get_host()
        request.path = '/' + \
            _str(container_name) + '?restype=container&comp=acl'
        request.headers = [
            ('x-ms-blob-public-access', _str_or_none(x_ms_blob_public_access)),
            ('x-ms-lease-id', _str_or_none(x_ms_lease_id)),
        ]
        request.body = _get_request_body(
            _convert_class_to_xml(signed_identifiers))
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_blob_header(
            request, self.account_name, self.account_key)
        self._perform_request(request)

    def delete_container(self, container_name, fail_not_exist=False,
                         x_ms_lease_id=None):
        '''
        Marks the specified container for deletion.

        container_name: Name of container to delete.
        fail_not_exist:
            Specify whether to throw an exception when the container doesn't
            exist.
        x_ms_lease_id: Required if the container has an active lease.
        '''
        _validate_not_none('container_name', container_name)
        request = HTTPRequest()
        request.method = 'DELETE'
        request.host = self._get_host()
        request.path = '/' + _str(container_name) + '?restype=container'
        request.headers = [('x-ms-lease-id', _str_or_none(x_ms_lease_id))]
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_blob_header(
            request, self.account_name, self.account_key)
        if not fail_not_exist:
            try:
                self._perform_request(request)
                return True
            except WindowsAzureError as ex:
                _dont_fail_not_exist(ex)
                return False
        else:
            self._perform_request(request)
            return True

    def lease_container(self, container_name, x_ms_lease_action,
                        x_ms_lease_id=None, x_ms_lease_duration=60,
                        x_ms_lease_break_period=None,
                        x_ms_proposed_lease_id=None):
        '''
        Establishes and manages a lock on a container for delete operations.
        The lock duration can be 15 to 60 seconds, or can be infinite.

        container_name: Name of existing container.
        x_ms_lease_action:
            Required. Possible values: acquire|renew|release|break|change
        x_ms_lease_id: Required if the container has an active lease.
        x_ms_lease_duration:
            Specifies the duration of the lease, in seconds, or negative one
            (-1) for a lease that never expires. A non-infinite lease can be
            between 15 and 60 seconds. A lease duration cannot be changed
            using renew or change. For backwards compatibility, the default is
            60, and the value is only used on an acquire operation.
        x_ms_lease_break_period:
            Optional. For a break operation, this is the proposed duration of
            seconds that the lease should continue before it is broken, between
            0 and 60 seconds. This break period is only used if it is shorter
            than the time remaining on the lease. If longer, the time remaining
            on the lease is used. A new lease will not be available before the
            break period has expired, but the lease may be held for longer than
            the break period. If this header does not appear with a break
            operation, a fixed-duration lease breaks after the remaining lease
            period elapses, and an infinite lease breaks immediately.
        x_ms_proposed_lease_id:
            Optional for acquire, required for change. Proposed lease ID, in a
            GUID string format.
        '''
        _validate_not_none('container_name', container_name)
        _validate_not_none('x_ms_lease_action', x_ms_lease_action)
        request = HTTPRequest()
        request.method = 'PUT'
        request.host = self._get_host()
        request.path = '/' + \
            _str(container_name) + '?restype=container&comp=lease'
        request.headers = [
            ('x-ms-lease-id', _str_or_none(x_ms_lease_id)),
            ('x-ms-lease-action', _str_or_none(x_ms_lease_action)),
            ('x-ms-lease-duration',
             _str_or_none(
                 x_ms_lease_duration if x_ms_lease_action == 'acquire'\
                     else None)),
            ('x-ms-lease-break-period', _str_or_none(x_ms_lease_break_period)),
            ('x-ms-proposed-lease-id', _str_or_none(x_ms_proposed_lease_id)),
        ]
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_blob_header(
            request, self.account_name, self.account_key)
        response = self._perform_request(request)

        return _parse_response_for_dict_filter(
            response,
            filter=['x-ms-lease-id', 'x-ms-lease-time'])

    def list_blobs(self, container_name, prefix=None, marker=None,
                   maxresults=None, include=None, delimiter=None):
        '''
        Returns the list of blobs under the specified container.

        container_name: Name of existing container.
        prefix:
            Optional. Filters the results to return only blobs whose names
            begin with the specified prefix.
        marker:
            Optional. A string value that identifies the portion of the list
            to be returned with the next list operation. The operation returns
            a marker value within the response body if the list returned was
            not complete. The marker value may then be used in a subsequent
            call to request the next set of list items. The marker value is
            opaque to the client.
        maxresults:
            Optional. Specifies the maximum number of blobs to return,
            including all BlobPrefix elements. If the request does not specify
            maxresults or specifies a value greater than 5,000, the server will
            return up to 5,000 items. Setting maxresults to a value less than
            or equal to zero results in error response code 400 (Bad Request).
        include:
            Optional. Specifies one or more datasets to include in the
            response. To specify more than one of these options on the URI,
            you must separate each option with a comma. Valid values are:
                snapshots:
                    Specifies that snapshots should be included in the
                    enumeration. Snapshots are listed from oldest to newest in
                    the response.
                metadata:
                    Specifies that blob metadata be returned in the response.
                uncommittedblobs:
                    Specifies that blobs for which blocks have been uploaded,
                    but which have not been committed using Put Block List
                    (REST API), be included in the response.
                copy:
                    Version 2012-02-12 and newer. Specifies that metadata
                    related to any current or previous Copy Blob operation
                    should be included in the response.
        delimiter:
            Optional. When the request includes this parameter, the operation
            returns a BlobPrefix element in the response body that acts as a
            placeholder for all blobs whose names begin with the same
            substring up to the appearance of the delimiter character. The
            delimiter may be a single character or a string.
        '''
        _validate_not_none('container_name', container_name)
        request = HTTPRequest()
        request.method = 'GET'
        request.host = self._get_host()
        request.path = '/' + \
            _str(container_name) + '?restype=container&comp=list'
        request.query = [
            ('prefix', _str_or_none(prefix)),
            ('delimiter', _str_or_none(delimiter)),
            ('marker', _str_or_none(marker)),
            ('maxresults', _int_or_none(maxresults)),
            ('include', _str_or_none(include))
        ]
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_blob_header(
            request, self.account_name, self.account_key)
        response = self._perform_request(request)

        return _parse_blob_enum_results_list(response)

    def set_blob_service_properties(self, storage_service_properties,
                                    timeout=None):
        '''
        Sets the properties of a storage account's Blob service, including
        Windows Azure Storage Analytics. You can also use this operation to
        set the default request version for all incoming requests that do not
        have a version specified.

        storage_service_properties: a StorageServiceProperties object.
        timeout: Optional. The timeout parameter is expressed in seconds.
        '''
        _validate_not_none('storage_service_properties',
                           storage_service_properties)
        request = HTTPRequest()
        request.method = 'PUT'
        request.host = self._get_host()
        request.path = '/?restype=service&comp=properties'
        request.query = [('timeout', _int_or_none(timeout))]
        request.body = _get_request_body(
            _convert_class_to_xml(storage_service_properties))
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_blob_header(
            request, self.account_name, self.account_key)
        self._perform_request(request)

    def get_blob_service_properties(self, timeout=None):
        '''
        Gets the properties of a storage account's Blob service, including
        Windows Azure Storage Analytics.

        timeout: Optional. The timeout parameter is expressed in seconds.
        '''
        request = HTTPRequest()
        request.method = 'GET'
        request.host = self._get_host()
        request.path = '/?restype=service&comp=properties'
        request.query = [('timeout', _int_or_none(timeout))]
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_blob_header(
            request, self.account_name, self.account_key)
        response = self._perform_request(request)

        return _parse_response(response, StorageServiceProperties)

    def get_blob_properties(self, container_name, blob_name,
                            x_ms_lease_id=None):
        '''
        Returns all user-defined metadata, standard HTTP properties, and
        system properties for the blob.

        container_name: Name of existing container.
        blob_name: Name of existing blob.
        x_ms_lease_id: Required if the blob has an active lease.
        '''
        _validate_not_none('container_name', container_name)
        _validate_not_none('blob_name', blob_name)
        request = HTTPRequest()
        request.method = 'HEAD'
        request.host = self._get_host()
        request.path = '/' + _str(container_name) + '/' + _str(blob_name) + ''
        request.headers = [('x-ms-lease-id', _str_or_none(x_ms_lease_id))]
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_blob_header(
            request, self.account_name, self.account_key)
        response = self._perform_request(request)

        return _parse_response_for_dict(response)

    def set_blob_properties(self, container_name, blob_name,
                            x_ms_blob_cache_control=None,
                            x_ms_blob_content_type=None,
                            x_ms_blob_content_md5=None,
                            x_ms_blob_content_encoding=None,
                            x_ms_blob_content_language=None,
                            x_ms_lease_id=None):
        '''
        Sets system properties on the blob.

        container_name: Name of existing container.
        blob_name: Name of existing blob.
        x_ms_blob_cache_control:
            Optional. Modifies the cache control string for the blob.
        x_ms_blob_content_type: Optional. Sets the blob's content type.
        x_ms_blob_content_md5: Optional. Sets the blob's MD5 hash.
        x_ms_blob_content_encoding: Optional. Sets the blob's content encoding.
        x_ms_blob_content_language: Optional. Sets the blob's content language.
        x_ms_lease_id: Required if the blob has an active lease.
        '''
        _validate_not_none('container_name', container_name)
        _validate_not_none('blob_name', blob_name)
        request = HTTPRequest()
        request.method = 'PUT'
        request.host = self._get_host()
        request.path = '/' + \
            _str(container_name) + '/' + _str(blob_name) + '?comp=properties'
        request.headers = [
            ('x-ms-blob-cache-control', _str_or_none(x_ms_blob_cache_control)),
            ('x-ms-blob-content-type', _str_or_none(x_ms_blob_content_type)),
            ('x-ms-blob-content-md5', _str_or_none(x_ms_blob_content_md5)),
            ('x-ms-blob-content-encoding',
             _str_or_none(x_ms_blob_content_encoding)),
            ('x-ms-blob-content-language',
             _str_or_none(x_ms_blob_content_language)),
            ('x-ms-lease-id', _str_or_none(x_ms_lease_id))
        ]
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_blob_header(
            request, self.account_name, self.account_key)
        self._perform_request(request)

    def put_blob(self, container_name, blob_name, blob, x_ms_blob_type,
                 content_encoding=None, content_language=None,
                 content_md5=None, cache_control=None,
                 x_ms_blob_content_type=None, x_ms_blob_content_encoding=None,
                 x_ms_blob_content_language=None, x_ms_blob_content_md5=None,
                 x_ms_blob_cache_control=None, x_ms_meta_name_values=None,
                 x_ms_lease_id=None, x_ms_blob_content_length=None,
                 x_ms_blob_sequence_number=None):
        '''
        Creates a new block blob or page blob, or updates the content of an
        existing block blob.

        See put_block_blob_from_* and put_page_blob_from_* for high level
        functions that handle the creation and upload of large blobs with
        automatic chunking and progress notifications.

        container_name: Name of existing container.
        blob_name: Name of blob to create or update.
        blob:
            For BlockBlob:
                Content of blob as bytes (size < 64MB). For larger size, you
                must call put_block and put_block_list to set content of blob.
            For PageBlob:
                Use None and call put_page to set content of blob.
        x_ms_blob_type: Required. Could be BlockBlob or PageBlob.
        content_encoding:
            Optional. Specifies which content encodings have been applied to
            the blob. This value is returned to the client when the Get Blob
            (REST API) operation is performed on the blob resource. The client
            can use this value when returned to decode the blob content.
        content_language:
            Optional. Specifies the natural languages used by this resource.
        content_md5:
            Optional. An MD5 hash of the blob content. This hash is used to
            verify the integrity of the blob during transport. When this header
            is specified, the storage service checks the hash that has arrived
            with the one that was sent. If the two hashes do not match, the
            operation will fail with error code 400 (Bad Request).
        cache_control:
            Optional. The Blob service stores this value but does not use or
            modify it.
        x_ms_blob_content_type: Optional. Set the blob's content type.
        x_ms_blob_content_encoding: Optional. Set the blob's content encoding.
        x_ms_blob_content_language: Optional. Set the blob's content language.
        x_ms_blob_content_md5: Optional. Set the blob's MD5 hash.
        x_ms_blob_cache_control: Optional. Sets the blob's cache control.
        x_ms_meta_name_values: A dict containing name, value for metadata.
        x_ms_lease_id: Required if the blob has an active lease.
        x_ms_blob_content_length:
            Required for page blobs. This header specifies the maximum size
            for the page blob, up to 1 TB. The page blob size must be aligned
            to a 512-byte boundary.
        x_ms_blob_sequence_number:
            Optional. Set for page blobs only. The sequence number is a
            user-controlled value that you can use to track requests. The
            value of the sequence number must be between 0 and 2^63 - 1. The
            default value is 0.
        '''
        _validate_not_none('container_name', container_name)
        _validate_not_none('blob_name', blob_name)
        _validate_not_none('x_ms_blob_type', x_ms_blob_type)
        request = HTTPRequest()
        request.method = 'PUT'
        request.host = self._get_host()
        request.path = '/' + _str(container_name) + '/' + _str(blob_name) + ''
        request.headers = [
            ('x-ms-blob-type', _str_or_none(x_ms_blob_type)),
            ('Content-Encoding', _str_or_none(content_encoding)),
            ('Content-Language', _str_or_none(content_language)),
            ('Content-MD5', _str_or_none(content_md5)),
            ('Cache-Control', _str_or_none(cache_control)),
            ('x-ms-blob-content-type', _str_or_none(x_ms_blob_content_type)),
            ('x-ms-blob-content-encoding',
             _str_or_none(x_ms_blob_content_encoding)),
            ('x-ms-blob-content-language',
             _str_or_none(x_ms_blob_content_language)),
            ('x-ms-blob-content-md5', _str_or_none(x_ms_blob_content_md5)),
            ('x-ms-blob-cache-control', _str_or_none(x_ms_blob_cache_control)),
            ('x-ms-meta-name-values', x_ms_meta_name_values),
            ('x-ms-lease-id', _str_or_none(x_ms_lease_id)),
            ('x-ms-blob-content-length',
             _str_or_none(x_ms_blob_content_length)),
            ('x-ms-blob-sequence-number',
             _str_or_none(x_ms_blob_sequence_number))
        ]
        request.body = _get_request_body_bytes_only('blob', blob)
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_blob_header(
            request, self.account_name, self.account_key)
        self._perform_request(request)

    def put_block_blob_from_path(self, container_name, blob_name, file_path,
                                 content_encoding=None, content_language=None,
                                 content_md5=None, cache_control=None,
                                 x_ms_blob_content_type=None,
                                 x_ms_blob_content_encoding=None,
                                 x_ms_blob_content_language=None,
                                 x_ms_blob_content_md5=None,
                                 x_ms_blob_cache_control=None,
                                 x_ms_meta_name_values=None,
                                 x_ms_lease_id=None, progress_callback=None):
        '''
        Creates a new block blob from a file path, or updates the content of an
        existing block blob, with automatic chunking and progress notifications.

        container_name: Name of existing container.
        blob_name: Name of blob to create or update.
        file_path: Path of the file to upload as the blob content.
        content_encoding:
            Optional. Specifies which content encodings have been applied to
            the blob. This value is returned to the client when the Get Blob
            (REST API) operation is performed on the blob resource. The client
            can use this value when returned to decode the blob content.
        content_language:
            Optional. Specifies the natural languages used by this resource.
        content_md5:
            Optional. An MD5 hash of the blob content. This hash is used to
            verify the integrity of the blob during transport. When this header
            is specified, the storage service checks the hash that has arrived
            with the one that was sent. If the two hashes do not match, the
            operation will fail with error code 400 (Bad Request).
        cache_control:
            Optional. The Blob service stores this value but does not use or
            modify it.
        x_ms_blob_content_type: Optional. Set the blob's content type.
        x_ms_blob_content_encoding: Optional. Set the blob's content encoding.
        x_ms_blob_content_language: Optional. Set the blob's content language.
        x_ms_blob_content_md5: Optional. Set the blob's MD5 hash.
        x_ms_blob_cache_control: Optional. Sets the blob's cache control.
        x_ms_meta_name_values: A dict containing name, value for metadata.
        x_ms_lease_id: Required if the blob has an active lease.
        progress_callback:
            Callback for progress with signature function(current, total) where
            current is the number of bytes transfered so far, and total is the
            size of the blob, or None if the total size is unknown.
        '''
        _validate_not_none('container_name', container_name)
        _validate_not_none('blob_name', blob_name)
        _validate_not_none('file_path', file_path)
        request = HTTPRequest()
        request.method = 'PUT'
        request.host = self._get_host()
        request.path = '/' + _str(container_name) + '/' + _str(blob_name) + ''
        request.headers = [
            ('x-ms-blob-type', 'BlockBlob'),
            ('Content-Encoding', _str_or_none(content_encoding)),
            ('Content-Language', _str_or_none(content_language)),
            ('Content-MD5', _str_or_none(content_md5)),
            ('Cache-Control', _str_or_none(cache_control)),
            ('x-ms-blob-content-type', _str_or_none(x_ms_blob_content_type)),
            ('x-ms-blob-content-encoding',
             _str_or_none(x_ms_blob_content_encoding)),
            ('x-ms-blob-content-language',
             _str_or_none(x_ms_blob_content_language)),
            ('x-ms-blob-content-md5', _str_or_none(x_ms_blob_content_md5)),
            ('x-ms-blob-cache-control', _str_or_none(x_ms_blob_cache_control)),
            ('x-ms-meta-name-values', x_ms_meta_name_values),
            ('x-ms-lease-id', _str_or_none(x_ms_lease_id)),
        ]

        count = path.getsize(file_path)
        with open(file_path, 'rb') as stream:
            self.put_block_blob_from_file(container_name,
                                          blob_name,
                                          stream,
                                          count,
                                          content_encoding,
                                          content_language,
                                          content_md5,
                                          cache_control,
                                          x_ms_blob_content_type,
                                          x_ms_blob_content_encoding,
                                          x_ms_blob_content_language,
                                          x_ms_blob_content_md5,
                                          x_ms_blob_cache_control,
                                          x_ms_meta_name_values,
                                          x_ms_lease_id,
                                          progress_callback)

    def put_block_blob_from_file(self, container_name, blob_name, stream,
                                 count=None, content_encoding=None,
                                 content_language=None, content_md5=None,
                                 cache_control=None,
                                 x_ms_blob_content_type=None,
                                 x_ms_blob_content_encoding=None,
                                 x_ms_blob_content_language=None,
                                 x_ms_blob_content_md5=None,
                                 x_ms_blob_cache_control=None,
                                 x_ms_meta_name_values=None,
                                 x_ms_lease_id=None, progress_callback=None):
        '''
        Creates a new block blob from a file/stream, or updates the content of
        an existing block blob, with automatic chunking and progress
        notifications.

        container_name: Name of existing container.
        blob_name: Name of blob to create or update.
        stream: Opened file/stream to upload as the blob content.
        count:
            Number of bytes to read from the stream. This is optional, but
            should be supplied for optimal performance.
        content_encoding:
            Optional. Specifies which content encodings have been applied to
            the blob. This value is returned to the client when the Get Blob
            (REST API) operation is performed on the blob resource. The client
            can use this value when returned to decode the blob content.
        content_language:
            Optional. Specifies the natural languages used by this resource.
        content_md5:
            Optional. An MD5 hash of the blob content. This hash is used to
            verify the integrity of the blob during transport. When this header
            is specified, the storage service checks the hash that has arrived
            with the one that was sent. If the two hashes do not match, the
            operation will fail with error code 400 (Bad Request).
        cache_control:
            Optional. The Blob service stores this value but does not use or
            modify it.
        x_ms_blob_content_type: Optional. Set the blob's content type.
        x_ms_blob_content_encoding: Optional. Set the blob's content encoding.
        x_ms_blob_content_language: Optional. Set the blob's content language.
        x_ms_blob_content_md5: Optional. Set the blob's MD5 hash.
        x_ms_blob_cache_control: Optional. Sets the blob's cache control.
        x_ms_meta_name_values: A dict containing name, value for metadata.
        x_ms_lease_id: Required if the blob has an active lease.
        progress_callback:
            Callback for progress with signature function(current, total) where
            current is the number of bytes transfered so far, and total is the
            size of the blob, or None if the total size is unknown.
        '''
        _validate_not_none('container_name', container_name)
        _validate_not_none('blob_name', blob_name)
        _validate_not_none('stream', stream)
        request = HTTPRequest()
        request.method = 'PUT'
        request.host = self._get_host()
        request.path = '/' + _str(container_name) + '/' + _str(blob_name) + ''
        request.headers = [
            ('x-ms-blob-type', 'BlockBlob'),
            ('Content-Encoding', _str_or_none(content_encoding)),
            ('Content-Language', _str_or_none(content_language)),
            ('Content-MD5', _str_or_none(content_md5)),
            ('Cache-Control', _str_or_none(cache_control)),
            ('x-ms-blob-content-type', _str_or_none(x_ms_blob_content_type)),
            ('x-ms-blob-content-encoding',
             _str_or_none(x_ms_blob_content_encoding)),
            ('x-ms-blob-content-language',
             _str_or_none(x_ms_blob_content_language)),
            ('x-ms-blob-content-md5', _str_or_none(x_ms_blob_content_md5)),
            ('x-ms-blob-cache-control', _str_or_none(x_ms_blob_cache_control)),
            ('x-ms-meta-name-values', x_ms_meta_name_values),
            ('x-ms-lease-id', _str_or_none(x_ms_lease_id)),
        ]

        if count and count < self._BLOB_MAX_DATA_SIZE:
            if progress_callback:
                progress_callback(0, count)

            data = stream.read(count)
            self.put_blob(container_name,
                          blob_name,
                          data,
                          'BlockBlob',
                          content_encoding,
                          content_language,
                          content_md5,
                          cache_control,
                          x_ms_blob_content_type,
                          x_ms_blob_content_encoding,
                          x_ms_blob_content_language,
                          x_ms_blob_content_md5,
                          x_ms_blob_cache_control,
                          x_ms_meta_name_values,
                          x_ms_lease_id)

            if progress_callback:
                progress_callback(count, count)
        else:
            if progress_callback:
                progress_callback(0, count)

            self.put_blob(container_name,
                          blob_name,
                          None,
                          'BlockBlob',
                          content_encoding,
                          content_language,
                          content_md5,
                          cache_control,
                          x_ms_blob_content_type,
                          x_ms_blob_content_encoding,
                          x_ms_blob_content_language,
                          x_ms_blob_content_md5,
                          x_ms_blob_cache_control,
                          x_ms_meta_name_values,
                          x_ms_lease_id)

            remain_bytes = count
            block_ids = []
            block_index = 0
            index = 0
            while True:
                request_count = self._BLOB_MAX_CHUNK_DATA_SIZE\
                    if remain_bytes is None else min(
                        remain_bytes,
                        self._BLOB_MAX_CHUNK_DATA_SIZE)
                data = stream.read(request_count)
                if data:
                    length = len(data)
                    index += length
                    remain_bytes = remain_bytes - \
                        length if remain_bytes else None
                    block_id = '{0:08d}'.format(block_index)
                    self.put_block(container_name, blob_name,
                                   data, block_id, x_ms_lease_id=x_ms_lease_id)
                    block_ids.append(block_id)
                    block_index += 1
                    if progress_callback:
                        progress_callback(index, count)
                else:
                    break

            self.put_block_list(container_name, blob_name, block_ids)

    def put_block_blob_from_bytes(self, container_name, blob_name, blob,
                                  index=0, count=None, content_encoding=None,
                                  content_language=None, content_md5=None,
                                  cache_control=None,
                                  x_ms_blob_content_type=None,
                                  x_ms_blob_content_encoding=None,
                                  x_ms_blob_content_language=None,
                                  x_ms_blob_content_md5=None,
                                  x_ms_blob_cache_control=None,
                                  x_ms_meta_name_values=None,
                                  x_ms_lease_id=None, progress_callback=None):
        '''
        Creates a new block blob from an array of bytes, or updates the content
        of an existing block blob, with automatic chunking and progress
        notifications.

        container_name: Name of existing container.
        blob_name: Name of blob to create or update.
        blob: Content of blob as an array of bytes.
        index: Start index in the array of bytes.
        count:
            Number of bytes to upload. Set to None or negative value to upload
            all bytes starting from index.
        content_encoding:
            Optional. Specifies which content encodings have been applied to
            the blob. This value is returned to the client when the Get Blob
            (REST API) operation is performed on the blob resource. The client
            can use this value when returned to decode the blob content.
        content_language:
            Optional. Specifies the natural languages used by this resource.
        content_md5:
            Optional. An MD5 hash of the blob content. This hash is used to
            verify the integrity of the blob during transport. When this header
            is specified, the storage service checks the hash that has arrived
            with the one that was sent. If the two hashes do not match, the
            operation will fail with error code 400 (Bad Request).
        cache_control:
            Optional. The Blob service stores this value but does not use or
            modify it.
        x_ms_blob_content_type: Optional. Set the blob's content type.
        x_ms_blob_content_encoding: Optional. Set the blob's content encoding.
        x_ms_blob_content_language: Optional. Set the blob's content language.
        x_ms_blob_content_md5: Optional. Set the blob's MD5 hash.
        x_ms_blob_cache_control: Optional. Sets the blob's cache control.
        x_ms_meta_name_values: A dict containing name, value for metadata.
        x_ms_lease_id: Required if the blob has an active lease.
        progress_callback:
            Callback for progress with signature function(current, total) where
            current is the number of bytes transfered so far, and total is the
            size of the blob, or None if the total size is unknown.
        '''
        _validate_not_none('container_name', container_name)
        _validate_not_none('blob_name', blob_name)
        _validate_not_none('blob', blob)
        _validate_not_none('index', index)
        _validate_type_bytes('blob', blob)
        request = HTTPRequest()
        request.method = 'PUT'
        request.host = self._get_host()
        request.path = '/' + _str(container_name) + '/' + _str(blob_name) + ''
        request.headers = [
            ('x-ms-blob-type', 'BlockBlob'),
            ('Content-Encoding', _str_or_none(content_encoding)),
            ('Content-Language', _str_or_none(content_language)),
            ('Content-MD5', _str_or_none(content_md5)),
            ('Cache-Control', _str_or_none(cache_control)),
            ('x-ms-blob-content-type', _str_or_none(x_ms_blob_content_type)),
            ('x-ms-blob-content-encoding',
             _str_or_none(x_ms_blob_content_encoding)),
            ('x-ms-blob-content-language',
             _str_or_none(x_ms_blob_content_language)),
            ('x-ms-blob-content-md5', _str_or_none(x_ms_blob_content_md5)),
            ('x-ms-blob-cache-control', _str_or_none(x_ms_blob_cache_control)),
            ('x-ms-meta-name-values', x_ms_meta_name_values),
            ('x-ms-lease-id', _str_or_none(x_ms_lease_id)),
        ]

        if index < 0:
            raise TypeError(_ERROR_VALUE_NEGATIVE.format('index'))

        if count is None or count < 0:
            count = len(blob) - index

        if count < self._BLOB_MAX_DATA_SIZE:
            if progress_callback:
                progress_callback(0, count)

            data = blob[index: index + count]
            self.put_blob(container_name,
                          blob_name,
                          data,
                          'BlockBlob',
                          content_encoding,
                          content_language,
                          content_md5,
                          cache_control,
                          x_ms_blob_content_type,
                          x_ms_blob_content_encoding,
                          x_ms_blob_content_language,
                          x_ms_blob_content_md5,
                          x_ms_blob_cache_control,
                          x_ms_meta_name_values,
                          x_ms_lease_id)

            if progress_callback:
                progress_callback(count, count)
        else:
            stream = BytesIO(blob)
            stream.seek(index)

            self.put_block_blob_from_file(container_name,
                                          blob_name,
                                          stream,
                                          count,
                                          content_encoding,
                                          content_language,
                                          content_md5,
                                          cache_control,
                                          x_ms_blob_content_type,
                                          x_ms_blob_content_encoding,
                                          x_ms_blob_content_language,
                                          x_ms_blob_content_md5,
                                          x_ms_blob_cache_control,
                                          x_ms_meta_name_values,
                                          x_ms_lease_id,
                                          progress_callback)

    def put_block_blob_from_text(self, container_name, blob_name, text,
                                 text_encoding='utf-8',
                                 content_encoding=None, content_language=None,
                                 content_md5=None, cache_control=None,
                                 x_ms_blob_content_type=None,
                                 x_ms_blob_content_encoding=None,
                                 x_ms_blob_content_language=None,
                                 x_ms_blob_content_md5=None,
                                 x_ms_blob_cache_control=None,
                                 x_ms_meta_name_values=None,
                                 x_ms_lease_id=None, progress_callback=None):
        '''
        Creates a new block blob from str/unicode, or updates the content of an
        existing block blob, with automatic chunking and progress notifications.

        container_name: Name of existing container.
        blob_name: Name of blob to create or update.
        text: Text to upload to the blob.
        text_encoding: Encoding to use to convert the text to bytes.
        content_encoding:
            Optional. Specifies which content encodings have been applied to
            the blob. This value is returned to the client when the Get Blob
            (REST API) operation is performed on the blob resource. The client
            can use this value when returned to decode the blob content.
        content_language:
            Optional. Specifies the natural languages used by this resource.
        content_md5:
            Optional. An MD5 hash of the blob content. This hash is used to
            verify the integrity of the blob during transport. When this header
            is specified, the storage service checks the hash that has arrived
            with the one that was sent. If the two hashes do not match, the
            operation will fail with error code 400 (Bad Request).
        cache_control:
            Optional. The Blob service stores this value but does not use or
            modify it.
        x_ms_blob_content_type: Optional. Set the blob's content type.
        x_ms_blob_content_encoding: Optional. Set the blob's content encoding.
        x_ms_blob_content_language: Optional. Set the blob's content language.
        x_ms_blob_content_md5: Optional. Set the blob's MD5 hash.
        x_ms_blob_cache_control: Optional. Sets the blob's cache control.
        x_ms_meta_name_values: A dict containing name, value for metadata.
        x_ms_lease_id: Required if the blob has an active lease.
        progress_callback:
            Callback for progress with signature function(current, total) where
            current is the number of bytes transfered so far, and total is the
            size of the blob, or None if the total size is unknown.
        '''
        _validate_not_none('container_name', container_name)
        _validate_not_none('blob_name', blob_name)
        _validate_not_none('text', text)
        request = HTTPRequest()
        request.method = 'PUT'
        request.host = self._get_host()
        request.path = '/' + _str(container_name) + '/' + _str(blob_name) + ''
        request.headers = [
            ('x-ms-blob-type', 'BlockBlob'),
            ('Content-Encoding', _str_or_none(content_encoding)),
            ('Content-Language', _str_or_none(content_language)),
            ('Content-MD5', _str_or_none(content_md5)),
            ('Cache-Control', _str_or_none(cache_control)),
            ('x-ms-blob-content-type', _str_or_none(x_ms_blob_content_type)),
            ('x-ms-blob-content-encoding',
             _str_or_none(x_ms_blob_content_encoding)),
            ('x-ms-blob-content-language',
             _str_or_none(x_ms_blob_content_language)),
            ('x-ms-blob-content-md5', _str_or_none(x_ms_blob_content_md5)),
            ('x-ms-blob-cache-control', _str_or_none(x_ms_blob_cache_control)),
            ('x-ms-meta-name-values', x_ms_meta_name_values),
            ('x-ms-lease-id', _str_or_none(x_ms_lease_id)),
        ]

        if not isinstance(text, bytes):
            _validate_not_none('text_encoding', text_encoding)
            text = text.encode(text_encoding)

        self.put_block_blob_from_bytes(container_name,
                                       blob_name,
                                       text,
                                       0,
                                       len(text),
                                       content_encoding,
                                       content_language,
                                       content_md5,
                                       cache_control,
                                       x_ms_blob_content_type,
                                       x_ms_blob_content_encoding,
                                       x_ms_blob_content_language,
                                       x_ms_blob_content_md5,
                                       x_ms_blob_cache_control,
                                       x_ms_meta_name_values,
                                       x_ms_lease_id,
                                       progress_callback)

    def put_page_blob_from_path(self, container_name, blob_name, file_path,
                                content_encoding=None, content_language=None,
                                content_md5=None, cache_control=None,
                                x_ms_blob_content_type=None,
                                x_ms_blob_content_encoding=None,
                                x_ms_blob_content_language=None,
                                x_ms_blob_content_md5=None,
                                x_ms_blob_cache_control=None,
                                x_ms_meta_name_values=None,
                                x_ms_lease_id=None,
                                x_ms_blob_sequence_number=None,
                                progress_callback=None):
        '''
        Creates a new page blob from a file path, or updates the content of an
        existing page blob, with automatic chunking and progress notifications.

        container_name: Name of existing container.
        blob_name: Name of blob to create or update.
        file_path: Path of the file to upload as the blob content.
        content_encoding:
            Optional. Specifies which content encodings have been applied to
            the blob. This value is returned to the client when the Get Blob
            (REST API) operation is performed on the blob resource. The client
            can use this value when returned to decode the blob content.
        content_language:
            Optional. Specifies the natural languages used by this resource.
        content_md5:
            Optional. An MD5 hash of the blob content. This hash is used to
            verify the integrity of the blob during transport. When this header
            is specified, the storage service checks the hash that has arrived
            with the one that was sent. If the two hashes do not match, the
            operation will fail with error code 400 (Bad Request).
        cache_control:
            Optional. The Blob service stores this value but does not use or
            modify it.
        x_ms_blob_content_type: Optional. Set the blob's content type.
        x_ms_blob_content_encoding: Optional. Set the blob's content encoding.
        x_ms_blob_content_language: Optional. Set the blob's content language.
        x_ms_blob_content_md5: Optional. Set the blob's MD5 hash.
        x_ms_blob_cache_control: Optional. Sets the blob's cache control.
        x_ms_meta_name_values: A dict containing name, value for metadata.
        x_ms_lease_id: Required if the blob has an active lease.
        x_ms_blob_sequence_number:
            Optional. Set for page blobs only. The sequence number is a
            user-controlled value that you can use to track requests. The
            value of the sequence number must be between 0 and 2^63 - 1. The
            default value is 0.
        progress_callback:
            Callback for progress with signature function(current, total) where
            current is the number of bytes transfered so far, and total is the
            size of the blob, or None if the total size is unknown.
        '''
        _validate_not_none('container_name', container_name)
        _validate_not_none('blob_name', blob_name)
        _validate_not_none('file_path', file_path)

        count = path.getsize(file_path)
        with open(file_path, 'rb') as stream:
            self.put_page_blob_from_file(container_name,
                                         blob_name,
                                         stream,
                                         count,
                                         content_encoding,
                                         content_language,
                                         content_md5,
                                         cache_control,
                                         x_ms_blob_content_type,
                                         x_ms_blob_content_encoding,
                                         x_ms_blob_content_language,
                                         x_ms_blob_content_md5,
                                         x_ms_blob_cache_control,
                                         x_ms_meta_name_values,
                                         x_ms_lease_id,
                                         x_ms_blob_sequence_number,
                                         progress_callback)

    def put_page_blob_from_file(self, container_name, blob_name, stream, count,
                                content_encoding=None, content_language=None,
                                content_md5=None, cache_control=None,
                                x_ms_blob_content_type=None,
                                x_ms_blob_content_encoding=None,
                                x_ms_blob_content_language=None,
                                x_ms_blob_content_md5=None,
                                x_ms_blob_cache_control=None,
                                x_ms_meta_name_values=None,
                                x_ms_lease_id=None,
                                x_ms_blob_sequence_number=None,
                                progress_callback=None):
        '''
        Creates a new page blob from a file/stream, or updates the content of an
        existing page blob, with automatic chunking and progress notifications.

        container_name: Name of existing container.
        blob_name: Name of blob to create or update.
        stream: Opened file/stream to upload as the blob content.
        count:
            Number of bytes to read from the stream. This is required, a page
            blob cannot be created if the count is unknown.
        content_encoding:
            Optional. Specifies which content encodings have been applied to
            the blob. This value is returned to the client when the Get Blob
            (REST API) operation is performed on the blob resource. The client
            can use this value when returned to decode the blob content.
        content_language:
            Optional. Specifies the natural languages used by this resource.
        content_md5:
            Optional. An MD5 hash of the blob content. This hash is used to
            verify the integrity of the blob during transport. When this header
            is specified, the storage service checks the hash that has arrived
            with the one that was sent. If the two hashes do not match, the
            operation will fail with error code 400 (Bad Request).
        cache_control:
            Optional. The Blob service stores this value but does not use or
            modify it.
        x_ms_blob_content_type: Optional. Set the blob's content type.
        x_ms_blob_content_encoding: Optional. Set the blob's content encoding.
        x_ms_blob_content_language: Optional. Set the blob's content language.
        x_ms_blob_content_md5: Optional. Set the blob's MD5 hash.
        x_ms_blob_cache_control: Optional. Sets the blob's cache control.
        x_ms_meta_name_values: A dict containing name, value for metadata.
        x_ms_lease_id: Required if the blob has an active lease.
        x_ms_blob_sequence_number:
            Optional. Set for page blobs only. The sequence number is a
            user-controlled value that you can use to track requests. The
            value of the sequence number must be between 0 and 2^63 - 1. The
            default value is 0.
        progress_callback:
            Callback for progress with signature function(current, total) where
            current is the number of bytes transfered so far, and total is the
            size of the blob, or None if the total size is unknown.
        '''
        _validate_not_none('container_name', container_name)
        _validate_not_none('blob_name', blob_name)
        _validate_not_none('stream', stream)
        _validate_not_none('count', count)

        if count < 0:
            raise TypeError(_ERROR_VALUE_NEGATIVE.format('count'))

        if count % _PAGE_SIZE != 0:
            raise TypeError(_ERROR_PAGE_BLOB_SIZE_ALIGNMENT.format(count))

        if progress_callback:
            progress_callback(0, count)

        self.put_blob(container_name,
                      blob_name,
                      b'',
                      'PageBlob',
                      content_encoding,
                      content_language,
                      content_md5,
                      cache_control,
                      x_ms_blob_content_type,
                      x_ms_blob_content_encoding,
                      x_ms_blob_content_language,
                      x_ms_blob_content_md5,
                      x_ms_blob_cache_control,
                      x_ms_meta_name_values,
                      x_ms_lease_id,
                      count,
                      x_ms_blob_sequence_number)

        remain_bytes = count
        page_start = 0
        while True:
            request_count = min(remain_bytes, self._BLOB_MAX_CHUNK_DATA_SIZE)
            data = stream.read(request_count)
            if data:
                length = len(data)
                remain_bytes = remain_bytes - length
                page_end = page_start + length - 1
                self.put_page(container_name,
                              blob_name,
                              data,
                              'bytes={0}-{1}'.format(page_start, page_end),
                              'update',
                              x_ms_lease_id=x_ms_lease_id)
                page_start = page_start + length

                if progress_callback:
                    progress_callback(page_start, count)
            else:
                break

    def put_page_blob_from_bytes(self, container_name, blob_name, blob,
                                 index=0, count=None, content_encoding=None,
                                 content_language=None, content_md5=None,
                                 cache_control=None,
                                 x_ms_blob_content_type=None,
                                 x_ms_blob_content_encoding=None,
                                 x_ms_blob_content_language=None,
                                 x_ms_blob_content_md5=None,
                                 x_ms_blob_cache_control=None,
                                 x_ms_meta_name_values=None,
                                 x_ms_lease_id=None,
                                 x_ms_blob_sequence_number=None,
                                 progress_callback=None):
        '''
        Creates a new page blob from an array of bytes, or updates the content
        of an existing page blob, with automatic chunking and progress
        notifications.

        container_name: Name of existing container.
        blob_name: Name of blob to create or update.
        blob: Content of blob as an array of bytes.
        index: Start index in the array of bytes.
        count:
            Number of bytes to upload. Set to None or negative value to upload
            all bytes starting from index.
        content_encoding:
            Optional. Specifies which content encodings have been applied to
            the blob. This value is returned to the client when the Get Blob
            (REST API) operation is performed on the blob resource. The client
            can use this value when returned to decode the blob content.
        content_language:
            Optional. Specifies the natural languages used by this resource.
        content_md5:
            Optional. An MD5 hash of the blob content. This hash is used to
            verify the integrity of the blob during transport. When this header
            is specified, the storage service checks the hash that has arrived
            with the one that was sent. If the two hashes do not match, the
            operation will fail with error code 400 (Bad Request).
        cache_control:
            Optional. The Blob service stores this value but does not use or
            modify it.
        x_ms_blob_content_type: Optional. Set the blob's content type.
        x_ms_blob_content_encoding: Optional. Set the blob's content encoding.
        x_ms_blob_content_language: Optional. Set the blob's content language.
        x_ms_blob_content_md5: Optional. Set the blob's MD5 hash.
        x_ms_blob_cache_control: Optional. Sets the blob's cache control.
        x_ms_meta_name_values: A dict containing name, value for metadata.
        x_ms_lease_id: Required if the blob has an active lease.
        x_ms_blob_sequence_number:
            Optional. Set for page blobs only. The sequence number is a
            user-controlled value that you can use to track requests. The
            value of the sequence number must be between 0 and 2^63 - 1. The
            default value is 0.
        progress_callback:
            Callback for progress with signature function(current, total) where
            current is the number of bytes transfered so far, and total is the
            size of the blob, or None if the total size is unknown.
        '''
        _validate_not_none('container_name', container_name)
        _validate_not_none('blob_name', blob_name)
        _validate_not_none('blob', blob)
        _validate_type_bytes('blob', blob)

        if index < 0:
            raise TypeError(_ERROR_VALUE_NEGATIVE.format('index'))

        if count is None or count < 0:
            count = len(blob) - index

        stream = BytesIO(blob)
        stream.seek(index)

        self.put_page_blob_from_file(container_name,
                                     blob_name,
                                     stream,
                                     count,
                                     content_encoding,
                                     content_language,
                                     content_md5,
                                     cache_control,
                                     x_ms_blob_content_type,
                                     x_ms_blob_content_encoding,
                                     x_ms_blob_content_language,
                                     x_ms_blob_content_md5,
                                     x_ms_blob_cache_control,
                                     x_ms_meta_name_values,
                                     x_ms_lease_id,
                                     x_ms_blob_sequence_number,
                                     progress_callback)

    def get_blob(self, container_name, blob_name, snapshot=None,
                 x_ms_range=None, x_ms_lease_id=None,
                 x_ms_range_get_content_md5=None):
        '''
        Reads or downloads a blob from the system, including its metadata and
        properties.

        See get_blob_to_* for high level functions that handle the download
        of large blobs with automatic chunking and progress notifications.

        container_name: Name of existing container.
        blob_name: Name of existing blob.
        snapshot:
            Optional. The snapshot parameter is an opaque DateTime value that,
            when present, specifies the blob snapshot to retrieve.
        x_ms_range:
            Optional. Return only the bytes of the blob in the specified range.
        x_ms_lease_id: Required if the blob has an active lease.
        x_ms_range_get_content_md5:
            Optional. When this header is set to true and specified together
            with the Range header, the service returns the MD5 hash for the
            range, as long as the range is less than or equal to 4 MB in size.
        '''
        _validate_not_none('container_name', container_name)
        _validate_not_none('blob_name', blob_name)
        request = HTTPRequest()
        request.method = 'GET'
        request.host = self._get_host()
        request.path = '/' + _str(container_name) + '/' + _str(blob_name) + ''
        request.headers = [
            ('x-ms-range', _str_or_none(x_ms_range)),
            ('x-ms-lease-id', _str_or_none(x_ms_lease_id)),
            ('x-ms-range-get-content-md5',
             _str_or_none(x_ms_range_get_content_md5))
        ]
        request.query = [('snapshot', _str_or_none(snapshot))]
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_blob_header(
            request, self.account_name, self.account_key)
        response = self._perform_request(request, None)

        return _create_blob_result(response)

    def get_blob_to_path(self, container_name, blob_name, file_path,
                         open_mode='wb', snapshot=None, x_ms_lease_id=None,
                         progress_callback=None):
        '''
        Downloads a blob to a file path, with automatic chunking and progress
        notifications.

        container_name: Name of existing container.
        blob_name: Name of existing blob.
        file_path: Path of file to write to.
        open_mode: Mode to use when opening the file.
        snapshot:
            Optional. The snapshot parameter is an opaque DateTime value that,
            when present, specifies the blob snapshot to retrieve.
        x_ms_lease_id: Required if the blob has an active lease.
        progress_callback:
            Callback for progress with signature function(current, total) where
            current is the number of bytes transfered so far, and total is the
            size of the blob.
        '''
        _validate_not_none('container_name', container_name)
        _validate_not_none('blob_name', blob_name)
        _validate_not_none('file_path', file_path)
        _validate_not_none('open_mode', open_mode)

        with open(file_path, open_mode) as stream:
            self.get_blob_to_file(container_name,
                                  blob_name,
                                  stream,
                                  snapshot,
                                  x_ms_lease_id,
                                  progress_callback)

    def get_blob_to_file(self, container_name, blob_name, stream,
                         snapshot=None, x_ms_lease_id=None,
                         progress_callback=None):
        '''
        Downloads a blob to a file/stream, with automatic chunking and progress
        notifications.

        container_name: Name of existing container.
        blob_name: Name of existing blob.
        stream: Opened file/stream to write to.
        snapshot:
            Optional. The snapshot parameter is an opaque DateTime value that,
            when present, specifies the blob snapshot to retrieve.
        x_ms_lease_id: Required if the blob has an active lease.
        progress_callback:
            Callback for progress with signature function(current, total) where
            current is the number of bytes transfered so far, and total is the
            size of the blob.
        '''
        _validate_not_none('container_name', container_name)
        _validate_not_none('blob_name', blob_name)
        _validate_not_none('stream', stream)

        props = self.get_blob_properties(container_name, blob_name)
        blob_size = int(props['content-length'])

        if blob_size < self._BLOB_MAX_DATA_SIZE:
            if progress_callback:
                progress_callback(0, blob_size)

            data = self.get_blob(container_name,
                                 blob_name,
                                 snapshot,
                                 x_ms_lease_id=x_ms_lease_id)

            stream.write(data)

            if progress_callback:
                progress_callback(blob_size, blob_size)
        else:
            if progress_callback:
                progress_callback(0, blob_size)

            index = 0
            while index < blob_size:
                chunk_range = 'bytes={}-{}'.format(
                    index,
                    index + self._BLOB_MAX_CHUNK_DATA_SIZE - 1)
                data = self.get_blob(
                    container_name, blob_name, x_ms_range=chunk_range)
                length = len(data)
                index += length
                if length > 0:
                    stream.write(data)
                    if progress_callback:
                        progress_callback(index, blob_size)
                    if length < self._BLOB_MAX_CHUNK_DATA_SIZE:
                        break
                else:
                    break

    def get_blob_to_bytes(self, container_name, blob_name, snapshot=None,
                          x_ms_lease_id=None, progress_callback=None):
        '''
        Downloads a blob as an array of bytes, with automatic chunking and
        progress notifications.

        container_name: Name of existing container.
        blob_name: Name of existing blob.
        snapshot:
            Optional. The snapshot parameter is an opaque DateTime value that,
            when present, specifies the blob snapshot to retrieve.
        x_ms_lease_id: Required if the blob has an active lease.
        progress_callback:
            Callback for progress with signature function(current, total) where
            current is the number of bytes transfered so far, and total is the
            size of the blob.
        '''
        _validate_not_none('container_name', container_name)
        _validate_not_none('blob_name', blob_name)

        stream = BytesIO()
        self.get_blob_to_file(container_name,
                              blob_name,
                              stream,
                              snapshot,
                              x_ms_lease_id,
                              progress_callback)

        return stream.getvalue()

    def get_blob_to_text(self, container_name, blob_name, text_encoding='utf-8',
                         snapshot=None, x_ms_lease_id=None,
                         progress_callback=None):
        '''
        Downloads a blob as unicode text, with automatic chunking and progress
        notifications.

        container_name: Name of existing container.
        blob_name: Name of existing blob.
        text_encoding: Encoding to use when decoding the blob data.
        snapshot:
            Optional. The snapshot parameter is an opaque DateTime value that,
            when present, specifies the blob snapshot to retrieve.
        x_ms_lease_id: Required if the blob has an active lease.
        progress_callback:
            Callback for progress with signature function(current, total) where
            current is the number of bytes transfered so far, and total is the
            size of the blob.
        '''
        _validate_not_none('container_name', container_name)
        _validate_not_none('blob_name', blob_name)
        _validate_not_none('text_encoding', text_encoding)

        result = self.get_blob_to_bytes(container_name,
                                        blob_name,
                                        snapshot,
                                        x_ms_lease_id,
                                        progress_callback)

        return result.decode(text_encoding)

    def get_blob_metadata(self, container_name, blob_name, snapshot=None,
                          x_ms_lease_id=None):
        '''
        Returns all user-defined metadata for the specified blob or snapshot.

        container_name: Name of existing container.
        blob_name: Name of existing blob.
        snapshot:
            Optional. The snapshot parameter is an opaque DateTime value that,
            when present, specifies the blob snapshot to retrieve.
        x_ms_lease_id: Required if the blob has an active lease.
        '''
        _validate_not_none('container_name', container_name)
        _validate_not_none('blob_name', blob_name)
        request = HTTPRequest()
        request.method = 'GET'
        request.host = self._get_host()
        request.path = '/' + \
            _str(container_name) + '/' + _str(blob_name) + '?comp=metadata'
        request.headers = [('x-ms-lease-id', _str_or_none(x_ms_lease_id))]
        request.query = [('snapshot', _str_or_none(snapshot))]
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_blob_header(
            request, self.account_name, self.account_key)
        response = self._perform_request(request)

        return _parse_response_for_dict_prefix(response, prefixes=['x-ms-meta'])

    def set_blob_metadata(self, container_name, blob_name,
                          x_ms_meta_name_values=None, x_ms_lease_id=None):
        '''
        Sets user-defined metadata for the specified blob as one or more
        name-value pairs.

        container_name: Name of existing container.
        blob_name: Name of existing blob.
        x_ms_meta_name_values: Dict containing name and value pairs.
        x_ms_lease_id: Required if the blob has an active lease.
        '''
        _validate_not_none('container_name', container_name)
        _validate_not_none('blob_name', blob_name)
        request = HTTPRequest()
        request.method = 'PUT'
        request.host = self._get_host()
        request.path = '/' + \
            _str(container_name) + '/' + _str(blob_name) + '?comp=metadata'
        request.headers = [
            ('x-ms-meta-name-values', x_ms_meta_name_values),
            ('x-ms-lease-id', _str_or_none(x_ms_lease_id))
        ]
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_blob_header(
            request, self.account_name, self.account_key)
        self._perform_request(request)

    def lease_blob(self, container_name, blob_name, x_ms_lease_action,
                   x_ms_lease_id=None, x_ms_lease_duration=60,
                   x_ms_lease_break_period=None, x_ms_proposed_lease_id=None):
        '''
        Establishes and manages a one-minute lock on a blob for write
        operations.

        container_name: Name of existing container.
        blob_name: Name of existing blob.
        x_ms_lease_action:
            Required. Possible values: acquire|renew|release|break|change
        x_ms_lease_id: Required if the blob has an active lease.
        x_ms_lease_duration:
            Specifies the duration of the lease, in seconds, or negative one
            (-1) for a lease that never expires. A non-infinite lease can be
            between 15 and 60 seconds. A lease duration cannot be changed
            using renew or change. For backwards compatibility, the default is
            60, and the value is only used on an acquire operation.
        x_ms_lease_break_period:
            Optional. For a break operation, this is the proposed duration of
            seconds that the lease should continue before it is broken, between
            0 and 60 seconds. This break period is only used if it is shorter
            than the time remaining on the lease. If longer, the time remaining
            on the lease is used. A new lease will not be available before the
            break period has expired, but the lease may be held for longer than
            the break period. If this header does not appear with a break
            operation, a fixed-duration lease breaks after the remaining lease
            period elapses, and an infinite lease breaks immediately.
        x_ms_proposed_lease_id:
            Optional for acquire, required for change. Proposed lease ID, in a
            GUID string format.
        '''
        _validate_not_none('container_name', container_name)
        _validate_not_none('blob_name', blob_name)
        _validate_not_none('x_ms_lease_action', x_ms_lease_action)
        request = HTTPRequest()
        request.method = 'PUT'
        request.host = self._get_host()
        request.path = '/' + \
            _str(container_name) + '/' + _str(blob_name) + '?comp=lease'
        request.headers = [
            ('x-ms-lease-id', _str_or_none(x_ms_lease_id)),
            ('x-ms-lease-action', _str_or_none(x_ms_lease_action)),
            ('x-ms-lease-duration', _str_or_none(x_ms_lease_duration\
                if x_ms_lease_action == 'acquire' else None)),
            ('x-ms-lease-break-period', _str_or_none(x_ms_lease_break_period)),
            ('x-ms-proposed-lease-id', _str_or_none(x_ms_proposed_lease_id)),
        ]
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_blob_header(
            request, self.account_name, self.account_key)
        response = self._perform_request(request)

        return _parse_response_for_dict_filter(
            response,
            filter=['x-ms-lease-id', 'x-ms-lease-time'])

    def snapshot_blob(self, container_name, blob_name,
                      x_ms_meta_name_values=None, if_modified_since=None,
                      if_unmodified_since=None, if_match=None,
                      if_none_match=None, x_ms_lease_id=None):
        '''
        Creates a read-only snapshot of a blob.

        container_name: Name of existing container.
        blob_name: Name of existing blob.
        x_ms_meta_name_values: Optional. Dict containing name and value pairs.
        if_modified_since: Optional. Datetime string.
        if_unmodified_since: DateTime string.
        if_match:
            Optional. snapshot the blob only if its ETag value matches the
            value specified.
        if_none_match: Optional. An ETag value
        x_ms_lease_id: Required if the blob has an active lease.
        '''
        _validate_not_none('container_name', container_name)
        _validate_not_none('blob_name', blob_name)
        request = HTTPRequest()
        request.method = 'PUT'
        request.host = self._get_host()
        request.path = '/' + \
            _str(container_name) + '/' + _str(blob_name) + '?comp=snapshot'
        request.headers = [
            ('x-ms-meta-name-values', x_ms_meta_name_values),
            ('If-Modified-Since', _str_or_none(if_modified_since)),
            ('If-Unmodified-Since', _str_or_none(if_unmodified_since)),
            ('If-Match', _str_or_none(if_match)),
            ('If-None-Match', _str_or_none(if_none_match)),
            ('x-ms-lease-id', _str_or_none(x_ms_lease_id))
        ]
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_blob_header(
            request, self.account_name, self.account_key)
        response = self._perform_request(request)

        return _parse_response_for_dict_filter(
            response,
            filter=['x-ms-snapshot', 'etag', 'last-modified'])

    def copy_blob(self, container_name, blob_name, x_ms_copy_source,
                  x_ms_meta_name_values=None,
                  x_ms_source_if_modified_since=None,
                  x_ms_source_if_unmodified_since=None,
                  x_ms_source_if_match=None, x_ms_source_if_none_match=None,
                  if_modified_since=None, if_unmodified_since=None,
                  if_match=None, if_none_match=None, x_ms_lease_id=None,
                  x_ms_source_lease_id=None):
        '''
        Copies a blob to a destination within the storage account.

        container_name: Name of existing container.
        blob_name: Name of existing blob.
        x_ms_copy_source:
            URL up to 2 KB in length that specifies a blob. A source blob in
            the same account can be private, but a blob in another account
            must be public or accept credentials included in this URL, such as
            a Shared Access Signature. Examples:
            https://myaccount.blob.core.windows.net/mycontainer/myblob
            https://myaccount.blob.core.windows.net/mycontainer/myblob?snapshot=<DateTime>
        x_ms_meta_name_values: Optional. Dict containing name and value pairs.
        x_ms_source_if_modified_since:
            Optional. An ETag value. Specify this conditional header to copy
            the source blob only if its ETag matches the value specified.
        x_ms_source_if_unmodified_since:
            Optional. An ETag value. Specify this conditional header to copy
            the blob only if its ETag does not match the value specified.
        x_ms_source_if_match:
            Optional. A DateTime value. Specify this conditional header to
            copy the blob only if the source blob has been modified since the
            specified date/time.
        x_ms_source_if_none_match:
            Optional. An ETag value. Specify this conditional header to copy
            the source blob only if its ETag matches the value specified.
        if_modified_since: Optional. Datetime string.
        if_unmodified_since: DateTime string.
        if_match:
            Optional. Snapshot the blob only if its ETag value matches the
            value specified.
        if_none_match: Optional. An ETag value
        x_ms_lease_id: Required if the blob has an active lease.
        x_ms_source_lease_id:
            Optional. Specify this to perform the Copy Blob operation only if
            the lease ID given matches the active lease ID of the source blob.
        '''
        _validate_not_none('container_name', container_name)
        _validate_not_none('blob_name', blob_name)
        _validate_not_none('x_ms_copy_source', x_ms_copy_source)

        if x_ms_copy_source.startswith('/'):
            # Backwards compatibility for earlier versions of the SDK where
            # the copy source can be in the following formats:
            # - Blob in named container:
            #     /accountName/containerName/blobName
            # - Snapshot in named container:
            #     /accountName/containerName/blobName?snapshot=<DateTime>
            # - Blob in root container:
            #     /accountName/blobName
            # - Snapshot in root container:
            #     /accountName/blobName?snapshot=<DateTime>
            account, _, source =\
                x_ms_copy_source.partition('/')[2].partition('/')
            x_ms_copy_source = self.protocol + '://' + \
                account + self.host_base + '/' + source

        request = HTTPRequest()
        request.method = 'PUT'
        request.host = self._get_host()
        request.path = '/' + _str(container_name) + '/' + _str(blob_name) + ''
        request.headers = [
            ('x-ms-copy-source', _str_or_none(x_ms_copy_source)),
            ('x-ms-meta-name-values', x_ms_meta_name_values),
            ('x-ms-source-if-modified-since',
             _str_or_none(x_ms_source_if_modified_since)),
            ('x-ms-source-if-unmodified-since',
             _str_or_none(x_ms_source_if_unmodified_since)),
            ('x-ms-source-if-match', _str_or_none(x_ms_source_if_match)),
            ('x-ms-source-if-none-match',
             _str_or_none(x_ms_source_if_none_match)),
            ('If-Modified-Since', _str_or_none(if_modified_since)),
            ('If-Unmodified-Since', _str_or_none(if_unmodified_since)),
            ('If-Match', _str_or_none(if_match)),
            ('If-None-Match', _str_or_none(if_none_match)),
            ('x-ms-lease-id', _str_or_none(x_ms_lease_id)),
            ('x-ms-source-lease-id', _str_or_none(x_ms_source_lease_id))
        ]
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_blob_header(
            request, self.account_name, self.account_key)
        response = self._perform_request(request)

        return _parse_response_for_dict(response)

    def abort_copy_blob(self, container_name, blob_name, x_ms_copy_id,
                        x_ms_lease_id=None):
        '''
         Aborts a pending copy_blob operation, and leaves a destination blob
         with zero length and full metadata.

         container_name: Name of destination container.
         blob_name: Name of destination blob.
         x_ms_copy_id:
            Copy identifier provided in the x-ms-copy-id of the original
            copy_blob operation.
         x_ms_lease_id:
            Required if the destination blob has an active infinite lease.
        '''
        _validate_not_none('container_name', container_name)
        _validate_not_none('blob_name', blob_name)
        _validate_not_none('x_ms_copy_id', x_ms_copy_id)
        request = HTTPRequest()
        request.method = 'PUT'
        request.host = self._get_host()
        request.path = '/' + _str(container_name) + '/' + \
            _str(blob_name) + '?comp=copy&copyid=' + \
            _str(x_ms_copy_id)
        request.headers = [
            ('x-ms-lease-id', _str_or_none(x_ms_lease_id)),
            ('x-ms-copy-action', 'abort'),
        ]
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_blob_header(
            request, self.account_name, self.account_key)
        self._perform_request(request)

    def delete_blob(self, container_name, blob_name, snapshot=None,
                    x_ms_lease_id=None):
        '''
        Marks the specified blob or snapshot for deletion. The blob is later
        deleted during garbage collection.

        To mark a specific snapshot for deletion provide the date/time of the
        snapshot via the snapshot parameter.

        container_name: Name of existing container.
        blob_name: Name of existing blob.
        snapshot:
            Optional. The snapshot parameter is an opaque DateTime value that,
            when present, specifies the blob snapshot to delete.
        x_ms_lease_id: Required if the blob has an active lease.
        '''
        _validate_not_none('container_name', container_name)
        _validate_not_none('blob_name', blob_name)
        request = HTTPRequest()
        request.method = 'DELETE'
        request.host = self._get_host()
        request.path = '/' + _str(container_name) + '/' + _str(blob_name) + ''
        request.headers = [('x-ms-lease-id', _str_or_none(x_ms_lease_id))]
        request.query = [('snapshot', _str_or_none(snapshot))]
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_blob_header(
            request, self.account_name, self.account_key)
        self._perform_request(request)

    def put_block(self, container_name, blob_name, block, blockid,
                  content_md5=None, x_ms_lease_id=None):
        '''
        Creates a new block to be committed as part of a blob.

        container_name: Name of existing container.
        blob_name: Name of existing blob.
        block: Content of the block.
        blockid:
            Required. A value that identifies the block. The string must be
            less than or equal to 64 bytes in size.
        content_md5:
            Optional. An MD5 hash of the block content. This hash is used to
            verify the integrity of the blob during transport. When this
            header is specified, the storage service checks the hash that has
            arrived with the one that was sent.
        x_ms_lease_id: Required if the blob has an active lease.
        '''
        _validate_not_none('container_name', container_name)
        _validate_not_none('blob_name', blob_name)
        _validate_not_none('block', block)
        _validate_not_none('blockid', blockid)
        request = HTTPRequest()
        request.method = 'PUT'
        request.host = self._get_host()
        request.path = '/' + \
            _str(container_name) + '/' + _str(blob_name) + '?comp=block'
        request.headers = [
            ('Content-MD5', _str_or_none(content_md5)),
            ('x-ms-lease-id', _str_or_none(x_ms_lease_id))
        ]
        request.query = [('blockid', _encode_base64(_str_or_none(blockid)))]
        request.body = _get_request_body_bytes_only('block', block)
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_blob_header(
            request, self.account_name, self.account_key)
        self._perform_request(request)

    def put_block_list(self, container_name, blob_name, block_list,
                       content_md5=None, x_ms_blob_cache_control=None,
                       x_ms_blob_content_type=None,
                       x_ms_blob_content_encoding=None,
                       x_ms_blob_content_language=None,
                       x_ms_blob_content_md5=None, x_ms_meta_name_values=None,
                       x_ms_lease_id=None):
        '''
        Writes a blob by specifying the list of block IDs that make up the
        blob. In order to be written as part of a blob, a block must have been
        successfully written to the server in a prior Put Block (REST API)
        operation.

        container_name: Name of existing container.
        blob_name: Name of existing blob.
        block_list: A str list containing the block ids.
        content_md5:
            Optional. An MD5 hash of the block content. This hash is used to
            verify the integrity of the blob during transport. When this header
            is specified, the storage service checks the hash that has arrived
            with the one that was sent.
        x_ms_blob_cache_control:
            Optional. Sets the blob's cache control. If specified, this
            property is stored with the blob and returned with a read request.
        x_ms_blob_content_type:
            Optional. Sets the blob's content type. If specified, this property
            is stored with the blob and returned with a read request.
        x_ms_blob_content_encoding:
            Optional. Sets the blob's content encoding. If specified, this
            property is stored with the blob and returned with a read request.
        x_ms_blob_content_language:
            Optional. Set the blob's content language. If specified, this
            property is stored with the blob and returned with a read request.
        x_ms_blob_content_md5:
            Optional. An MD5 hash of the blob content. Note that this hash is
            not validated, as the hashes for the individual blocks were
            validated when each was uploaded.
        x_ms_meta_name_values: Optional. Dict containing name and value pairs.
        x_ms_lease_id: Required if the blob has an active lease.
        '''
        _validate_not_none('container_name', container_name)
        _validate_not_none('blob_name', blob_name)
        _validate_not_none('block_list', block_list)
        request = HTTPRequest()
        request.method = 'PUT'
        request.host = self._get_host()
        request.path = '/' + \
            _str(container_name) + '/' + _str(blob_name) + '?comp=blocklist'
        request.headers = [
            ('Content-MD5', _str_or_none(content_md5)),
            ('x-ms-blob-cache-control', _str_or_none(x_ms_blob_cache_control)),
            ('x-ms-blob-content-type', _str_or_none(x_ms_blob_content_type)),
            ('x-ms-blob-content-encoding',
             _str_or_none(x_ms_blob_content_encoding)),
            ('x-ms-blob-content-language',
             _str_or_none(x_ms_blob_content_language)),
            ('x-ms-blob-content-md5', _str_or_none(x_ms_blob_content_md5)),
            ('x-ms-meta-name-values', x_ms_meta_name_values),
            ('x-ms-lease-id', _str_or_none(x_ms_lease_id))
        ]
        request.body = _get_request_body(
            _convert_block_list_to_xml(block_list))
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_blob_header(
            request, self.account_name, self.account_key)
        self._perform_request(request)

    def get_block_list(self, container_name, blob_name, snapshot=None,
                       blocklisttype=None, x_ms_lease_id=None):
        '''
        Retrieves the list of blocks that have been uploaded as part of a
        block blob.

        container_name: Name of existing container.
        blob_name: Name of existing blob.
        snapshot:
            Optional. Datetime to determine the time to retrieve the blocks.
        blocklisttype:
            Specifies whether to return the list of committed blocks, the list
            of uncommitted blocks, or both lists together. Valid values are:
            committed, uncommitted, or all.
        x_ms_lease_id: Required if the blob has an active lease.
        '''
        _validate_not_none('container_name', container_name)
        _validate_not_none('blob_name', blob_name)
        request = HTTPRequest()
        request.method = 'GET'
        request.host = self._get_host()
        request.path = '/' + \
            _str(container_name) + '/' + _str(blob_name) + '?comp=blocklist'
        request.headers = [('x-ms-lease-id', _str_or_none(x_ms_lease_id))]
        request.query = [
            ('snapshot', _str_or_none(snapshot)),
            ('blocklisttype', _str_or_none(blocklisttype))
        ]
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_blob_header(
            request, self.account_name, self.account_key)
        response = self._perform_request(request)

        return _convert_response_to_block_list(response)

    def put_page(self, container_name, blob_name, page, x_ms_range,
                 x_ms_page_write, timeout=None, content_md5=None,
                 x_ms_lease_id=None, x_ms_if_sequence_number_lte=None,
                 x_ms_if_sequence_number_lt=None,
                 x_ms_if_sequence_number_eq=None,
                 if_modified_since=None, if_unmodified_since=None,
                 if_match=None, if_none_match=None):
        '''
        Writes a range of pages to a page blob.

        container_name: Name of existing container.
        blob_name: Name of existing blob.
        page: Content of the page.
        x_ms_range:
            Required. Specifies the range of bytes to be written as a page.
            Both the start and end of the range must be specified. Must be in
            format: bytes=startByte-endByte. Given that pages must be aligned
            with 512-byte boundaries, the start offset must be a modulus of
            512 and the end offset must be a modulus of 512-1. Examples of
            valid byte ranges are 0-511, 512-1023, etc.
        x_ms_page_write:
            Required. You may specify one of the following options:
                update (lower case):
                    Writes the bytes specified by the request body into the
                    specified range. The Range and Content-Length headers must
                    match to perform the update.
                clear (lower case):
                    Clears the specified range and releases the space used in
                    storage for that range. To clear a range, set the
                    Content-Length header to zero, and the Range header to a
                    value that indicates the range to clear, up to maximum
                    blob size.
        timeout: the timeout parameter is expressed in seconds.
        content_md5:
            Optional. An MD5 hash of the page content. This hash is used to
            verify the integrity of the page during transport. When this header
            is specified, the storage service compares the hash of the content
            that has arrived with the header value that was sent. If the two
            hashes do not match, the operation will fail with error code 400
            (Bad Request).
        x_ms_lease_id: Required if the blob has an active lease.
        x_ms_if_sequence_number_lte:
            Optional. If the blob's sequence number is less than or equal to
            the specified value, the request proceeds; otherwise it fails.
        x_ms_if_sequence_number_lt:
            Optional. If the blob's sequence number is less than the specified
            value, the request proceeds; otherwise it fails.
        x_ms_if_sequence_number_eq:
            Optional. If the blob's sequence number is equal to the specified
            value, the request proceeds; otherwise it fails.
        if_modified_since:
            Optional. A DateTime value. Specify this conditional header to
            write the page only if the blob has been modified since the
            specified date/time. If the blob has not been modified, the Blob
            service fails.
        if_unmodified_since:
            Optional. A DateTime value. Specify this conditional header to
            write the page only if the blob has not been modified since the
            specified date/time. If the blob has been modified, the Blob
            service fails.
        if_match:
            Optional. An ETag value. Specify an ETag value for this conditional
            header to write the page only if the blob's ETag value matches the
            value specified. If the values do not match, the Blob service fails.
        if_none_match:
            Optional. An ETag value. Specify an ETag value for this conditional
            header to write the page only if the blob's ETag value does not
            match the value specified. If the values are identical, the Blob
            service fails.
        '''
        _validate_not_none('container_name', container_name)
        _validate_not_none('blob_name', blob_name)
        _validate_not_none('page', page)
        _validate_not_none('x_ms_range', x_ms_range)
        _validate_not_none('x_ms_page_write', x_ms_page_write)
        request = HTTPRequest()
        request.method = 'PUT'
        request.host = self._get_host()
        request.path = '/' + \
            _str(container_name) + '/' + _str(blob_name) + '?comp=page'
        request.headers = [
            ('x-ms-range', _str_or_none(x_ms_range)),
            ('Content-MD5', _str_or_none(content_md5)),
            ('x-ms-page-write', _str_or_none(x_ms_page_write)),
            ('x-ms-lease-id', _str_or_none(x_ms_lease_id)),
            ('x-ms-if-sequence-number-le',
             _str_or_none(x_ms_if_sequence_number_lte)),
            ('x-ms-if-sequence-number-lt',
             _str_or_none(x_ms_if_sequence_number_lt)),
            ('x-ms-if-sequence-number-eq',
             _str_or_none(x_ms_if_sequence_number_eq)),
            ('If-Modified-Since', _str_or_none(if_modified_since)),
            ('If-Unmodified-Since', _str_or_none(if_unmodified_since)),
            ('If-Match', _str_or_none(if_match)),
            ('If-None-Match', _str_or_none(if_none_match))
        ]
        request.query = [('timeout', _int_or_none(timeout))]
        request.body = _get_request_body_bytes_only('page', page)
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_blob_header(
            request, self.account_name, self.account_key)
        self._perform_request(request)

    def get_page_ranges(self, container_name, blob_name, snapshot=None,
                        range=None, x_ms_range=None, x_ms_lease_id=None):
        '''
        Retrieves the page ranges for a blob.

        container_name: Name of existing container.
        blob_name: Name of existing blob.
        snapshot:
            Optional. The snapshot parameter is an opaque DateTime value that,
            when present, specifies the blob snapshot to retrieve information
            from.
        range:
            Optional. Specifies the range of bytes over which to list ranges,
            inclusively. If omitted, then all ranges for the blob are returned.
        x_ms_range:
            Optional. Specifies the range of bytes to be written as a page.
            Both the start and end of the range must be specified. Must be in
            format: bytes=startByte-endByte. Given that pages must be aligned
            with 512-byte boundaries, the start offset must be a modulus of
            512 and the end offset must be a modulus of 512-1. Examples of
            valid byte ranges are 0-511, 512-1023, etc.
        x_ms_lease_id: Required if the blob has an active lease.
        '''
        _validate_not_none('container_name', container_name)
        _validate_not_none('blob_name', blob_name)
        request = HTTPRequest()
        request.method = 'GET'
        request.host = self._get_host()
        request.path = '/' + \
            _str(container_name) + '/' + _str(blob_name) + '?comp=pagelist'
        request.headers = [
            ('Range', _str_or_none(range)),
            ('x-ms-range', _str_or_none(x_ms_range)),
            ('x-ms-lease-id', _str_or_none(x_ms_lease_id))
        ]
        request.query = [('snapshot', _str_or_none(snapshot))]
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_blob_header(
            request, self.account_name, self.account_key)
        response = self._perform_request(request)

        return _parse_simple_list(response, PageList, PageRange, "page_ranges")

########NEW FILE########
__FILENAME__ = cloudstorageaccount
#-------------------------------------------------------------------------
# Copyright (c) Microsoft.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#--------------------------------------------------------------------------
from azure.storage.blobservice import BlobService
from azure.storage.tableservice import TableService
from azure.storage.queueservice import QueueService


class CloudStorageAccount(object):

    """
    Provides a factory for creating the blob, queue, and table services
    with a common account name and account key.  Users can either use the
    factory or can construct the appropriate service directly.
    """

    def __init__(self, account_name=None, account_key=None):
        self.account_name = account_name
        self.account_key = account_key

    def create_blob_service(self):
        return BlobService(self.account_name, self.account_key)

    def create_table_service(self):
        return TableService(self.account_name, self.account_key)

    def create_queue_service(self):
        return QueueService(self.account_name, self.account_key)

########NEW FILE########
__FILENAME__ = queueservice
#-------------------------------------------------------------------------
# Copyright (c) Microsoft.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#--------------------------------------------------------------------------
from azure import (
    WindowsAzureConflictError,
    WindowsAzureError,
    DEV_QUEUE_HOST,
    QUEUE_SERVICE_HOST_BASE,
    xml_escape,
    _convert_class_to_xml,
    _dont_fail_not_exist,
    _dont_fail_on_exist,
    _get_request_body,
    _int_or_none,
    _parse_enum_results_list,
    _parse_response,
    _parse_response_for_dict_filter,
    _parse_response_for_dict_prefix,
    _str,
    _str_or_none,
    _update_request_uri_query_local_storage,
    _validate_not_none,
    _ERROR_CONFLICT,
    )
from azure.http import (
    HTTPRequest,
    HTTP_RESPONSE_NO_CONTENT,
    )
from azure.storage import (
    Queue,
    QueueEnumResults,
    QueueMessagesList,
    StorageServiceProperties,
    _update_storage_queue_header,
    )
from azure.storage.storageclient import _StorageClient


class QueueService(_StorageClient):

    '''
    This is the main class managing queue resources.
    '''

    def __init__(self, account_name=None, account_key=None, protocol='https',
                 host_base=QUEUE_SERVICE_HOST_BASE, dev_host=DEV_QUEUE_HOST):
        '''
        account_name: your storage account name, required for all operations.
        account_key: your storage account key, required for all operations.
        protocol: Optional. Protocol. Defaults to http.
        host_base:
            Optional. Live host base url. Defaults to Azure url. Override this
            for on-premise.
        dev_host: Optional. Dev host url. Defaults to localhost.
        '''
        super(QueueService, self).__init__(
            account_name, account_key, protocol, host_base, dev_host)

    def get_queue_service_properties(self, timeout=None):
        '''
        Gets the properties of a storage account's Queue Service, including
        Windows Azure Storage Analytics.

        timeout: Optional. The timeout parameter is expressed in seconds.
        '''
        request = HTTPRequest()
        request.method = 'GET'
        request.host = self._get_host()
        request.path = '/?restype=service&comp=properties'
        request.query = [('timeout', _int_or_none(timeout))]
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_queue_header(
            request, self.account_name, self.account_key)
        response = self._perform_request(request)

        return _parse_response(response, StorageServiceProperties)

    def list_queues(self, prefix=None, marker=None, maxresults=None,
                    include=None):
        '''
        Lists all of the queues in a given storage account.

        prefix:
            Filters the results to return only queues with names that begin
            with the specified prefix.
        marker:
            A string value that identifies the portion of the list to be
            returned with the next list operation. The operation returns a
            NextMarker element within the response body if the list returned
            was not complete. This value may then be used as a query parameter
            in a subsequent call to request the next portion of the list of
            queues. The marker value is opaque to the client.
        maxresults:
            Specifies the maximum number of queues to return. If maxresults is
            not specified, the server will return up to 5,000 items.
        include:
            Optional. Include this parameter to specify that the container's
            metadata be returned as part of the response body.
        '''
        request = HTTPRequest()
        request.method = 'GET'
        request.host = self._get_host()
        request.path = '/?comp=list'
        request.query = [
            ('prefix', _str_or_none(prefix)),
            ('marker', _str_or_none(marker)),
            ('maxresults', _int_or_none(maxresults)),
            ('include', _str_or_none(include))
        ]
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_queue_header(
            request, self.account_name, self.account_key)
        response = self._perform_request(request)

        return _parse_enum_results_list(
            response, QueueEnumResults, "Queues", Queue)

    def create_queue(self, queue_name, x_ms_meta_name_values=None,
                     fail_on_exist=False):
        '''
        Creates a queue under the given account.

        queue_name: name of the queue.
        x_ms_meta_name_values:
            Optional. A dict containing name-value pairs to associate with the
            queue as metadata.
        fail_on_exist: Specify whether throw exception when queue exists.
        '''
        _validate_not_none('queue_name', queue_name)
        request = HTTPRequest()
        request.method = 'PUT'
        request.host = self._get_host()
        request.path = '/' + _str(queue_name) + ''
        request.headers = [('x-ms-meta-name-values', x_ms_meta_name_values)]
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_queue_header(
            request, self.account_name, self.account_key)
        if not fail_on_exist:
            try:
                response = self._perform_request(request)
                if response.status == HTTP_RESPONSE_NO_CONTENT:
                    return False
                return True
            except WindowsAzureError as ex:
                _dont_fail_on_exist(ex)
                return False
        else:
            response = self._perform_request(request)
            if response.status == HTTP_RESPONSE_NO_CONTENT:
                raise WindowsAzureConflictError(
                    _ERROR_CONFLICT.format(response.message))
            return True

    def delete_queue(self, queue_name, fail_not_exist=False):
        '''
        Permanently deletes the specified queue.

        queue_name: Name of the queue.
        fail_not_exist:
            Specify whether throw exception when queue doesn't exist.
        '''
        _validate_not_none('queue_name', queue_name)
        request = HTTPRequest()
        request.method = 'DELETE'
        request.host = self._get_host()
        request.path = '/' + _str(queue_name) + ''
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_queue_header(
            request, self.account_name, self.account_key)
        if not fail_not_exist:
            try:
                self._perform_request(request)
                return True
            except WindowsAzureError as ex:
                _dont_fail_not_exist(ex)
                return False
        else:
            self._perform_request(request)
            return True

    def get_queue_metadata(self, queue_name):
        '''
        Retrieves user-defined metadata and queue properties on the specified
        queue. Metadata is associated with the queue as name-values pairs.

        queue_name: Name of the queue.
        '''
        _validate_not_none('queue_name', queue_name)
        request = HTTPRequest()
        request.method = 'GET'
        request.host = self._get_host()
        request.path = '/' + _str(queue_name) + '?comp=metadata'
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_queue_header(
            request, self.account_name, self.account_key)
        response = self._perform_request(request)

        return _parse_response_for_dict_prefix(
            response,
            prefixes=['x-ms-meta', 'x-ms-approximate-messages-count'])

    def set_queue_metadata(self, queue_name, x_ms_meta_name_values=None):
        '''
        Sets user-defined metadata on the specified queue. Metadata is
        associated with the queue as name-value pairs.

        queue_name: Name of the queue.
        x_ms_meta_name_values:
            Optional. A dict containing name-value pairs to associate with the
            queue as metadata.
        '''
        _validate_not_none('queue_name', queue_name)
        request = HTTPRequest()
        request.method = 'PUT'
        request.host = self._get_host()
        request.path = '/' + _str(queue_name) + '?comp=metadata'
        request.headers = [('x-ms-meta-name-values', x_ms_meta_name_values)]
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_queue_header(
            request, self.account_name, self.account_key)
        self._perform_request(request)

    def put_message(self, queue_name, message_text, visibilitytimeout=None,
                    messagettl=None):
        '''
        Adds a new message to the back of the message queue. A visibility
        timeout can also be specified to make the message invisible until the
        visibility timeout expires. A message must be in a format that can be
        included in an XML request with UTF-8 encoding. The encoded message can
        be up to 64KB in size for versions 2011-08-18 and newer, or 8KB in size
        for previous versions.

        queue_name: Name of the queue.
        message_text: Message content.
        visibilitytimeout:
            Optional. If not specified, the default value is 0. Specifies the
            new visibility timeout value, in seconds, relative to server time.
            The new value must be larger than or equal to 0, and cannot be
            larger than 7 days. The visibility timeout of a message cannot be
            set to a value later than the expiry time. visibilitytimeout
            should be set to a value smaller than the time-to-live value.
        messagettl:
            Optional. Specifies the time-to-live interval for the message, in
            seconds. The maximum time-to-live allowed is 7 days. If this
            parameter is omitted, the default time-to-live is 7 days.
        '''
        _validate_not_none('queue_name', queue_name)
        _validate_not_none('message_text', message_text)
        request = HTTPRequest()
        request.method = 'POST'
        request.host = self._get_host()
        request.path = '/' + _str(queue_name) + '/messages'
        request.query = [
            ('visibilitytimeout', _str_or_none(visibilitytimeout)),
            ('messagettl', _str_or_none(messagettl))
        ]
        request.body = _get_request_body(
            '<?xml version="1.0" encoding="utf-8"?> \
<QueueMessage> \
    <MessageText>' + xml_escape(_str(message_text)) + '</MessageText> \
</QueueMessage>')
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_queue_header(
            request, self.account_name, self.account_key)
        self._perform_request(request)

    def get_messages(self, queue_name, numofmessages=None,
                     visibilitytimeout=None):
        '''
        Retrieves one or more messages from the front of the queue.

        queue_name: Name of the queue.
        numofmessages:
            Optional. A nonzero integer value that specifies the number of
            messages to retrieve from the queue, up to a maximum of 32. If
            fewer are visible, the visible messages are returned. By default,
            a single message is retrieved from the queue with this operation.
        visibilitytimeout:
            Specifies the new visibility timeout value, in seconds, relative
            to server time. The new value must be larger than or equal to 1
            second, and cannot be larger than 7 days, or larger than 2 hours
            on REST protocol versions prior to version 2011-08-18. The
            visibility timeout of a message can be set to a value later than
            the expiry time.
        '''
        _validate_not_none('queue_name', queue_name)
        request = HTTPRequest()
        request.method = 'GET'
        request.host = self._get_host()
        request.path = '/' + _str(queue_name) + '/messages'
        request.query = [
            ('numofmessages', _str_or_none(numofmessages)),
            ('visibilitytimeout', _str_or_none(visibilitytimeout))
        ]
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_queue_header(
            request, self.account_name, self.account_key)
        response = self._perform_request(request)

        return _parse_response(response, QueueMessagesList)

    def peek_messages(self, queue_name, numofmessages=None):
        '''
        Retrieves one or more messages from the front of the queue, but does
        not alter the visibility of the message.

        queue_name: Name of the queue.
        numofmessages:
            Optional. A nonzero integer value that specifies the number of
            messages to peek from the queue, up to a maximum of 32. By default,
            a single message is peeked from the queue with this operation.
        '''
        _validate_not_none('queue_name', queue_name)
        request = HTTPRequest()
        request.method = 'GET'
        request.host = self._get_host()
        request.path = '/' + _str(queue_name) + '/messages?peekonly=true'
        request.query = [('numofmessages', _str_or_none(numofmessages))]
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_queue_header(
            request, self.account_name, self.account_key)
        response = self._perform_request(request)

        return _parse_response(response, QueueMessagesList)

    def delete_message(self, queue_name, message_id, popreceipt):
        '''
        Deletes the specified message.

        queue_name: Name of the queue.
        message_id: Message to delete.
        popreceipt:
            Required. A valid pop receipt value returned from an earlier call
            to the Get Messages or Update Message operation.
        '''
        _validate_not_none('queue_name', queue_name)
        _validate_not_none('message_id', message_id)
        _validate_not_none('popreceipt', popreceipt)
        request = HTTPRequest()
        request.method = 'DELETE'
        request.host = self._get_host()
        request.path = '/' + \
            _str(queue_name) + '/messages/' + _str(message_id) + ''
        request.query = [('popreceipt', _str_or_none(popreceipt))]
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_queue_header(
            request, self.account_name, self.account_key)
        self._perform_request(request)

    def clear_messages(self, queue_name):
        '''
        Deletes all messages from the specified queue.

        queue_name: Name of the queue.
        '''
        _validate_not_none('queue_name', queue_name)
        request = HTTPRequest()
        request.method = 'DELETE'
        request.host = self._get_host()
        request.path = '/' + _str(queue_name) + '/messages'
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_queue_header(
            request, self.account_name, self.account_key)
        self._perform_request(request)

    def update_message(self, queue_name, message_id, message_text, popreceipt,
                       visibilitytimeout):
        '''
        Updates the visibility timeout of a message. You can also use this
        operation to update the contents of a message.

        queue_name: Name of the queue.
        message_id: Message to update.
        message_text: Content of message.
        popreceipt:
            Required. A valid pop receipt value returned from an earlier call
            to the Get Messages or Update Message operation.
        visibilitytimeout:
            Required. Specifies the new visibility timeout value, in seconds,
            relative to server time. The new value must be larger than or equal
            to 0, and cannot be larger than 7 days. The visibility timeout of a
            message cannot be set to a value later than the expiry time. A
            message can be updated until it has been deleted or has expired.
        '''
        _validate_not_none('queue_name', queue_name)
        _validate_not_none('message_id', message_id)
        _validate_not_none('message_text', message_text)
        _validate_not_none('popreceipt', popreceipt)
        _validate_not_none('visibilitytimeout', visibilitytimeout)
        request = HTTPRequest()
        request.method = 'PUT'
        request.host = self._get_host()
        request.path = '/' + \
            _str(queue_name) + '/messages/' + _str(message_id) + ''
        request.query = [
            ('popreceipt', _str_or_none(popreceipt)),
            ('visibilitytimeout', _str_or_none(visibilitytimeout))
        ]
        request.body = _get_request_body(
            '<?xml version="1.0" encoding="utf-8"?> \
<QueueMessage> \
    <MessageText>' + xml_escape(_str(message_text)) + '</MessageText> \
</QueueMessage>')
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_queue_header(
            request, self.account_name, self.account_key)
        response = self._perform_request(request)

        return _parse_response_for_dict_filter(
            response,
            filter=['x-ms-popreceipt', 'x-ms-time-next-visible'])

    def set_queue_service_properties(self, storage_service_properties,
                                     timeout=None):
        '''
        Sets the properties of a storage account's Queue service, including
        Windows Azure Storage Analytics.

        storage_service_properties: StorageServiceProperties object.
        timeout: Optional. The timeout parameter is expressed in seconds.
        '''
        _validate_not_none('storage_service_properties',
                           storage_service_properties)
        request = HTTPRequest()
        request.method = 'PUT'
        request.host = self._get_host()
        request.path = '/?restype=service&comp=properties'
        request.query = [('timeout', _int_or_none(timeout))]
        request.body = _get_request_body(
            _convert_class_to_xml(storage_service_properties))
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_queue_header(
            request, self.account_name, self.account_key)
        self._perform_request(request)

########NEW FILE########
__FILENAME__ = sharedaccesssignature
#-------------------------------------------------------------------------
# Copyright (c) Microsoft.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#--------------------------------------------------------------------------
from azure import url_quote
from azure.storage import _sign_string, X_MS_VERSION

#-------------------------------------------------------------------------
# Constants for the share access signature
SIGNED_START = 'st'
SIGNED_EXPIRY = 'se'
SIGNED_RESOURCE = 'sr'
SIGNED_PERMISSION = 'sp'
SIGNED_IDENTIFIER = 'si'
SIGNED_SIGNATURE = 'sig'
SIGNED_VERSION = 'sv'
RESOURCE_BLOB = 'b'
RESOURCE_CONTAINER = 'c'
SIGNED_RESOURCE_TYPE = 'resource'
SHARED_ACCESS_PERMISSION = 'permission'

#--------------------------------------------------------------------------


class WebResource(object):

    '''
    Class that stands for the resource to get the share access signature

    path: the resource path.
    properties: dict of name and values. Contains 2 item: resource type and
            permission
    request_url: the url of the webresource include all the queries.
    '''

    def __init__(self, path=None, request_url=None, properties=None):
        self.path = path
        self.properties = properties or {}
        self.request_url = request_url


class Permission(object):

    '''
    Permission class. Contains the path and query_string for the path.

    path: the resource path
    query_string: dict of name, values. Contains SIGNED_START, SIGNED_EXPIRY
            SIGNED_RESOURCE, SIGNED_PERMISSION, SIGNED_IDENTIFIER,
            SIGNED_SIGNATURE name values.
    '''

    def __init__(self, path=None, query_string=None):
        self.path = path
        self.query_string = query_string


class SharedAccessPolicy(object):

    ''' SharedAccessPolicy class. '''

    def __init__(self, access_policy, signed_identifier=None):
        self.id = signed_identifier
        self.access_policy = access_policy


class SharedAccessSignature(object):

    '''
    The main class used to do the signing and generating the signature.

    account_name:
        the storage account name used to generate shared access signature
    account_key: the access key to genenerate share access signature
    permission_set: the permission cache used to signed the request url.
    '''

    def __init__(self, account_name, account_key, permission_set=None):
        self.account_name = account_name
        self.account_key = account_key
        self.permission_set = permission_set

    def generate_signed_query_string(self, path, resource_type,
                                     shared_access_policy,
                                     version=X_MS_VERSION):
        '''
        Generates the query string for path, resource type and shared access
        policy.

        path: the resource
        resource_type: could be blob or container
        shared_access_policy: shared access policy
        version:
            x-ms-version for storage service, or None to get a signed query
            string compatible with pre 2012-02-12 clients, where the version
            is not included in the query string.
        '''

        query_string = {}
        if shared_access_policy.access_policy.start:
            query_string[
                SIGNED_START] = shared_access_policy.access_policy.start

        if version:
            query_string[SIGNED_VERSION] = version
        query_string[SIGNED_EXPIRY] = shared_access_policy.access_policy.expiry
        query_string[SIGNED_RESOURCE] = resource_type
        query_string[
            SIGNED_PERMISSION] = shared_access_policy.access_policy.permission

        if shared_access_policy.id:
            query_string[SIGNED_IDENTIFIER] = shared_access_policy.id

        query_string[SIGNED_SIGNATURE] = self._generate_signature(
            path, shared_access_policy, version)
        return query_string

    def sign_request(self, web_resource):
        ''' sign request to generate request_url with sharedaccesssignature
        info for web_resource.'''

        if self.permission_set:
            for shared_access_signature in self.permission_set:
                if self._permission_matches_request(
                        shared_access_signature, web_resource,
                        web_resource.properties[
                            SIGNED_RESOURCE_TYPE],
                        web_resource.properties[SHARED_ACCESS_PERMISSION]):
                    if web_resource.request_url.find('?') == -1:
                        web_resource.request_url += '?'
                    else:
                        web_resource.request_url += '&'

                    web_resource.request_url += self._convert_query_string(
                        shared_access_signature.query_string)
                    break
        return web_resource

    def _convert_query_string(self, query_string):
        ''' Converts query string to str. The order of name, values is very
        important and can't be wrong.'''

        convert_str = ''
        if SIGNED_START in query_string:
            convert_str += SIGNED_START + '=' + \
                url_quote(query_string[SIGNED_START]) + '&'
        convert_str += SIGNED_EXPIRY + '=' + \
            url_quote(query_string[SIGNED_EXPIRY]) + '&'
        convert_str += SIGNED_PERMISSION + '=' + \
            query_string[SIGNED_PERMISSION] + '&'
        convert_str += SIGNED_RESOURCE + '=' + \
            query_string[SIGNED_RESOURCE] + '&'

        if SIGNED_IDENTIFIER in query_string:
            convert_str += SIGNED_IDENTIFIER + '=' + \
                query_string[SIGNED_IDENTIFIER] + '&'
        if SIGNED_VERSION in query_string:
            convert_str += SIGNED_VERSION + '=' + \
                query_string[SIGNED_VERSION] + '&'
        convert_str += SIGNED_SIGNATURE + '=' + \
            url_quote(query_string[SIGNED_SIGNATURE]) + '&'
        return convert_str

    def _generate_signature(self, path, shared_access_policy, version):
        ''' Generates signature for a given path and shared access policy. '''

        def get_value_to_append(value, no_new_line=False):
            return_value = ''
            if value:
                return_value = value
            if not no_new_line:
                return_value += '\n'
            return return_value

        if path[0] != '/':
            path = '/' + path

        canonicalized_resource = '/' + self.account_name + path

        # Form the string to sign from shared_access_policy and canonicalized
        # resource. The order of values is important.
        string_to_sign = \
            (get_value_to_append(shared_access_policy.access_policy.permission) +
             get_value_to_append(shared_access_policy.access_policy.start) +
             get_value_to_append(shared_access_policy.access_policy.expiry) +
             get_value_to_append(canonicalized_resource))

        if version:
            string_to_sign += get_value_to_append(shared_access_policy.id)
            string_to_sign += get_value_to_append(version, True)
        else:
            string_to_sign += get_value_to_append(shared_access_policy.id, True)

        return self._sign(string_to_sign)

    def _permission_matches_request(self, shared_access_signature,
                                    web_resource, resource_type,
                                    required_permission):
        ''' Check whether requested permission matches given
        shared_access_signature, web_resource and resource type. '''

        required_resource_type = resource_type
        if required_resource_type == RESOURCE_BLOB:
            required_resource_type += RESOURCE_CONTAINER

        for name, value in shared_access_signature.query_string.items():
            if name == SIGNED_RESOURCE and \
                required_resource_type.find(value) == -1:
                return False
            elif name == SIGNED_PERMISSION and \
                required_permission.find(value) == -1:
                return False

        return web_resource.path.find(shared_access_signature.path) != -1

    def _sign(self, string_to_sign):
        ''' use HMAC-SHA256 to sign the string and convert it as base64
        encoded string. '''

        return _sign_string(self.account_key, string_to_sign)

########NEW FILE########
__FILENAME__ = storageclient
#-------------------------------------------------------------------------
# Copyright (c) Microsoft.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#--------------------------------------------------------------------------
import os
import sys

from azure import (
    WindowsAzureError,
    DEV_ACCOUNT_NAME,
    DEV_ACCOUNT_KEY,
    _ERROR_STORAGE_MISSING_INFO,
    )
from azure.http import HTTPError
from azure.http.httpclient import _HTTPClient
from azure.storage import _storage_error_handler

#--------------------------------------------------------------------------
# constants for azure app setting environment variables
AZURE_STORAGE_ACCOUNT = 'AZURE_STORAGE_ACCOUNT'
AZURE_STORAGE_ACCESS_KEY = 'AZURE_STORAGE_ACCESS_KEY'
EMULATED = 'EMULATED'

#--------------------------------------------------------------------------


class _StorageClient(object):

    '''
    This is the base class for BlobManager, TableManager and QueueManager.
    '''

    def __init__(self, account_name=None, account_key=None, protocol='https',
                 host_base='', dev_host=''):
        '''
        account_name: your storage account name, required for all operations.
        account_key: your storage account key, required for all operations.
        protocol: Optional. Protocol. Defaults to http.
        host_base:
            Optional. Live host base url. Defaults to Azure url. Override this
            for on-premise.
        dev_host: Optional. Dev host url. Defaults to localhost.
        '''
        self.account_name = account_name
        self.account_key = account_key
        self.requestid = None
        self.protocol = protocol
        self.host_base = host_base
        self.dev_host = dev_host

        # the app is not run in azure emulator or use default development
        # storage account and key if app is run in emulator.
        self.use_local_storage = False

        # check whether it is run in emulator.
        if EMULATED in os.environ:
            self.is_emulated = os.environ[EMULATED].lower() != 'false'
        else:
            self.is_emulated = False

        # get account_name and account key. If they are not set when
        # constructing, get the account and key from environment variables if
        # the app is not run in azure emulator or use default development
        # storage account and key if app is run in emulator.
        if not self.account_name or not self.account_key:
            if self.is_emulated:
                self.account_name = DEV_ACCOUNT_NAME
                self.account_key = DEV_ACCOUNT_KEY
                self.protocol = 'http'
                self.use_local_storage = True
            else:
                self.account_name = os.environ.get(AZURE_STORAGE_ACCOUNT)
                self.account_key = os.environ.get(AZURE_STORAGE_ACCESS_KEY)

        if not self.account_name or not self.account_key:
            raise WindowsAzureError(_ERROR_STORAGE_MISSING_INFO)

        self._httpclient = _HTTPClient(
            service_instance=self,
            account_key=self.account_key,
            account_name=self.account_name,
            protocol=self.protocol)
        self._batchclient = None
        self._filter = self._perform_request_worker

    def with_filter(self, filter):
        '''
        Returns a new service which will process requests with the specified
        filter.  Filtering operations can include logging, automatic retrying,
        etc...  The filter is a lambda which receives the HTTPRequest and
        another lambda.  The filter can perform any pre-processing on the
        request, pass it off to the next lambda, and then perform any
        post-processing on the response.
        '''
        res = type(self)(self.account_name, self.account_key, self.protocol)
        old_filter = self._filter

        def new_filter(request):
            return filter(request, old_filter)

        res._filter = new_filter
        return res

    def set_proxy(self, host, port, user=None, password=None):
        '''
        Sets the proxy server host and port for the HTTP CONNECT Tunnelling.

        host: Address of the proxy. Ex: '192.168.0.100'
        port: Port of the proxy. Ex: 6000
        user: User for proxy authorization.
        password: Password for proxy authorization.
        '''
        self._httpclient.set_proxy(host, port, user, password)

    def _get_host(self):
        if self.use_local_storage:
            return self.dev_host
        else:
            return self.account_name + self.host_base

    def _perform_request_worker(self, request):
        return self._httpclient.perform_request(request)

    def _perform_request(self, request, text_encoding='utf-8'):
        '''
        Sends the request and return response. Catches HTTPError and hand it
        to error handler
        '''
        try:
            if self._batchclient is not None:
                return self._batchclient.insert_request_to_batch(request)
            else:
                resp = self._filter(request)

            if sys.version_info >= (3,) and isinstance(resp, bytes) and \
                text_encoding:
                resp = resp.decode(text_encoding)

        except HTTPError as ex:
            _storage_error_handler(ex)

        return resp

########NEW FILE########
__FILENAME__ = tableservice
#-------------------------------------------------------------------------
# Copyright (c) Microsoft.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#--------------------------------------------------------------------------
from azure import (
    WindowsAzureError,
    TABLE_SERVICE_HOST_BASE,
    DEV_TABLE_HOST,
    _convert_class_to_xml,
    _convert_response_to_feeds,
    _dont_fail_not_exist,
    _dont_fail_on_exist,
    _get_request_body,
    _int_or_none,
    _parse_response,
    _parse_response_for_dict,
    _parse_response_for_dict_filter,
    _str,
    _str_or_none,
    _update_request_uri_query_local_storage,
    _validate_not_none,
    )
from azure.http import HTTPRequest
from azure.http.batchclient import _BatchClient
from azure.storage import (
    StorageServiceProperties,
    _convert_entity_to_xml,
    _convert_response_to_entity,
    _convert_table_to_xml,
    _convert_xml_to_entity,
    _convert_xml_to_table,
    _sign_storage_table_request,
    _update_storage_table_header,
    )
from azure.storage.storageclient import _StorageClient


class TableService(_StorageClient):

    '''
    This is the main class managing Table resources.
    '''

    def __init__(self, account_name=None, account_key=None, protocol='https',
                 host_base=TABLE_SERVICE_HOST_BASE, dev_host=DEV_TABLE_HOST):
        '''
        account_name: your storage account name, required for all operations.
        account_key: your storage account key, required for all operations.
        protocol: Optional. Protocol. Defaults to http.
        host_base:
            Optional. Live host base url. Defaults to Azure url. Override this
            for on-premise.
        dev_host: Optional. Dev host url. Defaults to localhost.
        '''
        super(TableService, self).__init__(
            account_name, account_key, protocol, host_base, dev_host)

    def begin_batch(self):
        if self._batchclient is None:
            self._batchclient = _BatchClient(
                service_instance=self,
                account_key=self.account_key,
                account_name=self.account_name)
        return self._batchclient.begin_batch()

    def commit_batch(self):
        try:
            ret = self._batchclient.commit_batch()
        finally:
            self._batchclient = None
        return ret

    def cancel_batch(self):
        self._batchclient = None

    def get_table_service_properties(self):
        '''
        Gets the properties of a storage account's Table service, including
        Windows Azure Storage Analytics.
        '''
        request = HTTPRequest()
        request.method = 'GET'
        request.host = self._get_host()
        request.path = '/?restype=service&comp=properties'
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_table_header(request)
        response = self._perform_request(request)

        return _parse_response(response, StorageServiceProperties)

    def set_table_service_properties(self, storage_service_properties):
        '''
        Sets the properties of a storage account's Table Service, including
        Windows Azure Storage Analytics.

        storage_service_properties: StorageServiceProperties object.
        '''
        _validate_not_none('storage_service_properties',
                           storage_service_properties)
        request = HTTPRequest()
        request.method = 'PUT'
        request.host = self._get_host()
        request.path = '/?restype=service&comp=properties'
        request.body = _get_request_body(
            _convert_class_to_xml(storage_service_properties))
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_table_header(request)
        response = self._perform_request(request)

        return _parse_response_for_dict(response)

    def query_tables(self, table_name=None, top=None, next_table_name=None):
        '''
        Returns a list of tables under the specified account.

        table_name: Optional.  The specific table to query.
        top: Optional. Maximum number of tables to return.
        next_table_name:
            Optional. When top is used, the next table name is stored in
            result.x_ms_continuation['NextTableName']
        '''
        request = HTTPRequest()
        request.method = 'GET'
        request.host = self._get_host()
        if table_name is not None:
            uri_part_table_name = "('" + table_name + "')"
        else:
            uri_part_table_name = ""
        request.path = '/Tables' + uri_part_table_name + ''
        request.query = [
            ('$top', _int_or_none(top)),
            ('NextTableName', _str_or_none(next_table_name))
        ]
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_table_header(request)
        response = self._perform_request(request)

        return _convert_response_to_feeds(response, _convert_xml_to_table)

    def create_table(self, table, fail_on_exist=False):
        '''
        Creates a new table in the storage account.

        table:
            Name of the table to create. Table name may contain only
            alphanumeric characters and cannot begin with a numeric character.
            It is case-insensitive and must be from 3 to 63 characters long.
        fail_on_exist: Specify whether throw exception when table exists.
        '''
        _validate_not_none('table', table)
        request = HTTPRequest()
        request.method = 'POST'
        request.host = self._get_host()
        request.path = '/Tables'
        request.body = _get_request_body(_convert_table_to_xml(table))
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_table_header(request)
        if not fail_on_exist:
            try:
                self._perform_request(request)
                return True
            except WindowsAzureError as ex:
                _dont_fail_on_exist(ex)
                return False
        else:
            self._perform_request(request)
            return True

    def delete_table(self, table_name, fail_not_exist=False):
        '''
        table_name: Name of the table to delete.
        fail_not_exist:
            Specify whether throw exception when table doesn't exist.
        '''
        _validate_not_none('table_name', table_name)
        request = HTTPRequest()
        request.method = 'DELETE'
        request.host = self._get_host()
        request.path = '/Tables(\'' + _str(table_name) + '\')'
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_table_header(request)
        if not fail_not_exist:
            try:
                self._perform_request(request)
                return True
            except WindowsAzureError as ex:
                _dont_fail_not_exist(ex)
                return False
        else:
            self._perform_request(request)
            return True

    def get_entity(self, table_name, partition_key, row_key, select=''):
        '''
        Get an entity in a table; includes the $select options.

        partition_key: PartitionKey of the entity.
        row_key: RowKey of the entity.
        select: Property names to select.
        '''
        _validate_not_none('table_name', table_name)
        _validate_not_none('partition_key', partition_key)
        _validate_not_none('row_key', row_key)
        _validate_not_none('select', select)
        request = HTTPRequest()
        request.method = 'GET'
        request.host = self._get_host()
        request.path = '/' + _str(table_name) + \
            '(PartitionKey=\'' + _str(partition_key) + \
            '\',RowKey=\'' + \
            _str(row_key) + '\')?$select=' + \
            _str(select) + ''
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_table_header(request)
        response = self._perform_request(request)

        return _convert_response_to_entity(response)

    def query_entities(self, table_name, filter=None, select=None, top=None,
                       next_partition_key=None, next_row_key=None):
        '''
        Get entities in a table; includes the $filter and $select options.

        table_name: Table to query.
        filter:
            Optional. Filter as described at
            http://msdn.microsoft.com/en-us/library/windowsazure/dd894031.aspx
        select: Optional. Property names to select from the entities.
        top: Optional. Maximum number of entities to return.
        next_partition_key:
            Optional. When top is used, the next partition key is stored in
            result.x_ms_continuation['NextPartitionKey']
        next_row_key:
            Optional. When top is used, the next partition key is stored in
            result.x_ms_continuation['NextRowKey']
        '''
        _validate_not_none('table_name', table_name)
        request = HTTPRequest()
        request.method = 'GET'
        request.host = self._get_host()
        request.path = '/' + _str(table_name) + '()'
        request.query = [
            ('$filter', _str_or_none(filter)),
            ('$select', _str_or_none(select)),
            ('$top', _int_or_none(top)),
            ('NextPartitionKey', _str_or_none(next_partition_key)),
            ('NextRowKey', _str_or_none(next_row_key))
        ]
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_table_header(request)
        response = self._perform_request(request)

        return _convert_response_to_feeds(response, _convert_xml_to_entity)

    def insert_entity(self, table_name, entity,
                      content_type='application/atom+xml'):
        '''
        Inserts a new entity into a table.

        table_name: Table name.
        entity:
            Required. The entity object to insert. Could be a dict format or
            entity object.
        content_type: Required. Must be set to application/atom+xml
        '''
        _validate_not_none('table_name', table_name)
        _validate_not_none('entity', entity)
        _validate_not_none('content_type', content_type)
        request = HTTPRequest()
        request.method = 'POST'
        request.host = self._get_host()
        request.path = '/' + _str(table_name) + ''
        request.headers = [('Content-Type', _str_or_none(content_type))]
        request.body = _get_request_body(_convert_entity_to_xml(entity))
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_table_header(request)
        response = self._perform_request(request)

        return _convert_response_to_entity(response)

    def update_entity(self, table_name, partition_key, row_key, entity,
                      content_type='application/atom+xml', if_match='*'):
        '''
        Updates an existing entity in a table. The Update Entity operation
        replaces the entire entity and can be used to remove properties.

        table_name: Table name.
        partition_key: PartitionKey of the entity.
        row_key: RowKey of the entity.
        entity:
            Required. The entity object to insert. Could be a dict format or
            entity object.
        content_type: Required. Must be set to application/atom+xml
        if_match:
            Optional. Specifies the condition for which the merge should be
            performed. To force an unconditional merge, set to the wildcard
            character (*).
        '''
        _validate_not_none('table_name', table_name)
        _validate_not_none('partition_key', partition_key)
        _validate_not_none('row_key', row_key)
        _validate_not_none('entity', entity)
        _validate_not_none('content_type', content_type)
        request = HTTPRequest()
        request.method = 'PUT'
        request.host = self._get_host()
        request.path = '/' + \
            _str(table_name) + '(PartitionKey=\'' + \
            _str(partition_key) + '\',RowKey=\'' + _str(row_key) + '\')'
        request.headers = [
            ('Content-Type', _str_or_none(content_type)),
            ('If-Match', _str_or_none(if_match))
        ]
        request.body = _get_request_body(_convert_entity_to_xml(entity))
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_table_header(request)
        response = self._perform_request(request)

        return _parse_response_for_dict_filter(response, filter=['etag'])

    def merge_entity(self, table_name, partition_key, row_key, entity,
                     content_type='application/atom+xml', if_match='*'):
        '''
        Updates an existing entity by updating the entity's properties. This
        operation does not replace the existing entity as the Update Entity
        operation does.

        table_name: Table name.
        partition_key: PartitionKey of the entity.
        row_key: RowKey of the entity.
        entity:
            Required. The entity object to insert. Can be a dict format or
            entity object.
        content_type: Required. Must be set to application/atom+xml
        if_match:
            Optional. Specifies the condition for which the merge should be
            performed. To force an unconditional merge, set to the wildcard
            character (*).
        '''
        _validate_not_none('table_name', table_name)
        _validate_not_none('partition_key', partition_key)
        _validate_not_none('row_key', row_key)
        _validate_not_none('entity', entity)
        _validate_not_none('content_type', content_type)
        request = HTTPRequest()
        request.method = 'MERGE'
        request.host = self._get_host()
        request.path = '/' + \
            _str(table_name) + '(PartitionKey=\'' + \
            _str(partition_key) + '\',RowKey=\'' + _str(row_key) + '\')'
        request.headers = [
            ('Content-Type', _str_or_none(content_type)),
            ('If-Match', _str_or_none(if_match))
        ]
        request.body = _get_request_body(_convert_entity_to_xml(entity))
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_table_header(request)
        response = self._perform_request(request)

        return _parse_response_for_dict_filter(response, filter=['etag'])

    def delete_entity(self, table_name, partition_key, row_key,
                      content_type='application/atom+xml', if_match='*'):
        '''
        Deletes an existing entity in a table.

        table_name: Table name.
        partition_key: PartitionKey of the entity.
        row_key: RowKey of the entity.
        content_type: Required. Must be set to application/atom+xml
        if_match:
            Optional. Specifies the condition for which the delete should be
            performed. To force an unconditional delete, set to the wildcard
            character (*).
        '''
        _validate_not_none('table_name', table_name)
        _validate_not_none('partition_key', partition_key)
        _validate_not_none('row_key', row_key)
        _validate_not_none('content_type', content_type)
        _validate_not_none('if_match', if_match)
        request = HTTPRequest()
        request.method = 'DELETE'
        request.host = self._get_host()
        request.path = '/' + \
            _str(table_name) + '(PartitionKey=\'' + \
            _str(partition_key) + '\',RowKey=\'' + _str(row_key) + '\')'
        request.headers = [
            ('Content-Type', _str_or_none(content_type)),
            ('If-Match', _str_or_none(if_match))
        ]
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_table_header(request)
        self._perform_request(request)

    def insert_or_replace_entity(self, table_name, partition_key, row_key,
                                 entity, content_type='application/atom+xml'):
        '''
        Replaces an existing entity or inserts a new entity if it does not
        exist in the table. Because this operation can insert or update an
        entity, it is also known as an "upsert" operation.

        table_name: Table name.
        partition_key: PartitionKey of the entity.
        row_key: RowKey of the entity.
        entity:
            Required. The entity object to insert. Could be a dict format or
            entity object.
        content_type: Required. Must be set to application/atom+xml
        '''
        _validate_not_none('table_name', table_name)
        _validate_not_none('partition_key', partition_key)
        _validate_not_none('row_key', row_key)
        _validate_not_none('entity', entity)
        _validate_not_none('content_type', content_type)
        request = HTTPRequest()
        request.method = 'PUT'
        request.host = self._get_host()
        request.path = '/' + \
            _str(table_name) + '(PartitionKey=\'' + \
            _str(partition_key) + '\',RowKey=\'' + _str(row_key) + '\')'
        request.headers = [('Content-Type', _str_or_none(content_type))]
        request.body = _get_request_body(_convert_entity_to_xml(entity))
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_table_header(request)
        response = self._perform_request(request)

        return _parse_response_for_dict_filter(response, filter=['etag'])

    def insert_or_merge_entity(self, table_name, partition_key, row_key,
                               entity, content_type='application/atom+xml'):
        '''
        Merges an existing entity or inserts a new entity if it does not exist
        in the table. Because this operation can insert or update an entity,
        it is also known as an "upsert" operation.

        table_name: Table name.
        partition_key: PartitionKey of the entity.
        row_key: RowKey of the entity.
        entity:
            Required. The entity object to insert. Could be a dict format or
            entity object.
        content_type: Required. Must be set to application/atom+xml
        '''
        _validate_not_none('table_name', table_name)
        _validate_not_none('partition_key', partition_key)
        _validate_not_none('row_key', row_key)
        _validate_not_none('entity', entity)
        _validate_not_none('content_type', content_type)
        request = HTTPRequest()
        request.method = 'MERGE'
        request.host = self._get_host()
        request.path = '/' + \
            _str(table_name) + '(PartitionKey=\'' + \
            _str(partition_key) + '\',RowKey=\'' + _str(row_key) + '\')'
        request.headers = [('Content-Type', _str_or_none(content_type))]
        request.body = _get_request_body(_convert_entity_to_xml(entity))
        request.path, request.query = _update_request_uri_query_local_storage(
            request, self.use_local_storage)
        request.headers = _update_storage_table_header(request)
        response = self._perform_request(request)

        return _parse_response_for_dict_filter(response, filter=['etag'])

    def _perform_request_worker(self, request):
        auth = _sign_storage_table_request(request,
                                           self.account_name,
                                           self.account_key)
        request.headers.append(('Authorization', auth))
        return self._httpclient.perform_request(request)

########NEW FILE########
__FILENAME__ = clean
#-------------------------------------------------------------------------
# Copyright (c) Microsoft.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#--------------------------------------------------------------------------

from azure import *
from azure.storage import *
from azure.servicebus import *
from azuretest.util import *

print('WARNING!!!')
print('')
print('This program cleans the storage account and the service namespace')
print('specified by the unit test credentials file')
print('(windowsazurecredentials.json) located in your home directory.')
print('')
print('You should not run this program while tests are running as this will')
print('interfere with the tests.')
print('')
print('The following will be deleted from the storage account:')
print(' - All containers')
print(' - All tables')
print(' - All queues')
print('')
print('The following will be deleted from the service namespace:')
print(' - All queues')
print(' - All topics')
print('')
print('Enter YES to proceed, or anything else to cancel')
print('')

input = raw_input('>')
if input == 'YES':
    print('Cleaning storage account...')

    bc = BlobService(credentials.getStorageServicesName(),
                     credentials.getStorageServicesKey())

    ts = TableService(credentials.getStorageServicesName(),
                      credentials.getStorageServicesKey())

    qs = QueueService(credentials.getStorageServicesName(),
                      credentials.getStorageServicesKey())

    for container in bc.list_containers():
        bc.delete_container(container.name)

    for table in ts.query_tables():
        ts.delete_table(table.name)

    for queue in qs.list_queues():
        qs.delete_queue(queue.name)

    print('Cleaning service namespace...')

    sbs = ServiceBusService(credentials.getServiceBusNamespace(),
                            credentials.getServiceBusKey(),
                            'owner')

    for queue in sbs.list_queues():
        sbs.delete_queue(queue.name)

    for topic in sbs.list_topics():
        sbs.delete_topic(topic.name)

    print('Done.')
else:
    print('Canceled.')

########NEW FILE########
__FILENAME__ = doctest_blobservice
#-------------------------------------------------------------------------
# Copyright (c) Microsoft.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#--------------------------------------------------------------------------

"""
How to: Create a Container
--------------------------
>>> from azure.storage import *
>>> blob_service = BlobService(name, key)
>>> blob_service.create_container('mycontainer')
True

>>> blob_service.create_container('mycontainer2', x_ms_blob_public_access='container')
True

>>> blob_service.set_container_acl('mycontainer', x_ms_blob_public_access='container')

How to: Upload a Blob into a Container
--------------------------------------
>>> myblob = 'hello blob'
>>> blob_service.put_blob('mycontainer', 'myblob', myblob, x_ms_blob_type='BlockBlob')

How to: List the Blobs in a Container
-------------------------------------
>>> blobs = blob_service.list_blobs('mycontainer')
>>> for blob in blobs:
...     print(blob.name)
myblob

How to: Download Blobs
----------------------
>>> blob = blob_service.get_blob('mycontainer', 'myblob')
>>> print(blob)
hello blob

How to: Delete a Blob
---------------------
>>> blob_service.delete_blob('mycontainer', 'myblob')

>>> blob_service.delete_container('mycontainer')
True

>>> blob_service.delete_container('mycontainer2')
True

"""
from util import credentials

name = credentials.getStorageServicesName()
key = credentials.getStorageServicesKey()

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = doctest_queueservice
#-------------------------------------------------------------------------
# Copyright (c) Microsoft.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#--------------------------------------------------------------------------

"""
How To: Create a Queue
----------------------
>>> from azure.storage import *
>>> queue_service = QueueService(name, key)
>>> queue_service.create_queue('taskqueue')
True

How To: Insert a Message into a Queue
-------------------------------------
>>> queue_service.put_message('taskqueue', 'Hello World')

How To: Peek at the Next Message
--------------------------------
>>> messages = queue_service.peek_messages('taskqueue')
>>> for message in messages:
...     print(message.message_text)
... 
Hello World

How To: Dequeue the Next Message
--------------------------------
>>> messages = queue_service.get_messages('taskqueue')
>>> for message in messages:
...     print(message.message_text)
...     queue_service.delete_message('taskqueue', message.message_id, message.pop_receipt)
Hello World

How To: Change the Contents of a Queued Message
-----------------------------------------------
>>> queue_service.put_message('taskqueue', 'Hello World')
>>> messages = queue_service.get_messages('taskqueue')
>>> for message in messages:
...     res = queue_service.update_message('taskqueue', message.message_id, 'Hello World Again', message.pop_receipt, 0)

How To: Additional Options for Dequeuing Messages
-------------------------------------------------
>>> queue_service.put_message('taskqueue', 'Hello World')
>>> messages = queue_service.get_messages('taskqueue', numofmessages=16, visibilitytimeout=5*60)
>>> for message in messages:
...     print(message.message_text)
...     queue_service.delete_message('taskqueue', message.message_id, message.pop_receipt)
Hello World Again
Hello World

How To: Get the Queue Length
----------------------------
>>> queue_metadata = queue_service.get_queue_metadata('taskqueue')
>>> count = queue_metadata['x-ms-approximate-messages-count']
>>> count
u'0'

How To: Delete a Queue
----------------------
>>> queue_service.delete_queue('taskqueue')
True

"""
from util import credentials

name = credentials.getStorageServicesName()
key = credentials.getStorageServicesKey()

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = doctest_servicebusservicequeue
#-------------------------------------------------------------------------
# Copyright (c) Microsoft.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#--------------------------------------------------------------------------

"""
How To: Create a Queue
----------------------
>>> from azure.servicebus import *
>>> bus_service = ServiceBusService(ns, key, 'owner')
>>> bus_service.create_queue('taskqueue')
True

>>> queue_options = Queue()
>>> queue_options.max_size_in_megabytes = '5120'
>>> queue_options.default_message_time_to_live = 'PT1M'
>>> bus_service.create_queue('taskqueue2', queue_options)
True

How to Send Messages to a Queue
-------------------------------
>>> msg = Message('Test Message')
>>> bus_service.send_queue_message('taskqueue', msg)

How to Receive Messages from a Queue
------------------------------------
>>> msg = bus_service.receive_queue_message('taskqueue')
>>> print(msg.body)
Test Message

>>> msg = Message('Test Message')
>>> bus_service.send_queue_message('taskqueue', msg)

>>> msg = bus_service.receive_queue_message('taskqueue', peek_lock=True)
>>> print(msg.body)
Test Message
>>> msg.delete()


>>> bus_service.delete_queue('taskqueue')
True

>>> bus_service.delete_queue('taskqueue2')
True

"""
from util import credentials

ns = credentials.getServiceBusNamespace()
key = credentials.getServiceBusKey()

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = doctest_servicebusservicetopic
#-------------------------------------------------------------------------
# Copyright (c) Microsoft.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#--------------------------------------------------------------------------

"""
How to Create a Topic
---------------------
>>> from azure.servicebus import *
>>> bus_service = ServiceBusService(ns, key, 'owner')
>>> bus_service.create_topic('mytopic')
True

>>> topic_options = Topic()
>>> topic_options.max_size_in_megabytes = '5120'
>>> topic_options.default_message_time_to_live = 'PT1M'
>>> bus_service.create_topic('mytopic2', topic_options)
True

How to Create Subscriptions
---------------------------
>>> bus_service.create_subscription('mytopic', 'AllMessages')
True

>>> bus_service.create_subscription('mytopic', 'HighMessages')
True

>>> rule = Rule()
>>> rule.filter_type = 'SqlFilter'
>>> rule.filter_expression = 'messagenumber > 3'
>>> bus_service.create_rule('mytopic', 'HighMessages', 'HighMessageFilter', rule)
True

>>> bus_service.delete_rule('mytopic', 'HighMessages', DEFAULT_RULE_NAME)
True

>>> bus_service.create_subscription('mytopic', 'LowMessages')
True

>>> rule = Rule()
>>> rule.filter_type = 'SqlFilter'
>>> rule.filter_expression = 'messagenumber <= 3'
>>> bus_service.create_rule('mytopic', 'LowMessages', 'LowMessageFilter', rule)
True

>>> bus_service.delete_rule('mytopic', 'LowMessages', DEFAULT_RULE_NAME)
True

How to Send Messages to a Topic
-------------------------------
>>> for i in range(5):
...     msg = Message('Msg ' + str(i), custom_properties={'messagenumber':i})
...     bus_service.send_topic_message('mytopic', msg)

How to Receive Messages from a Subscription
-------------------------------------------
>>> msg = bus_service.receive_subscription_message('mytopic', 'LowMessages')
>>> print(msg.body)
Msg 0

>>> msg = bus_service.receive_subscription_message('mytopic', 'LowMessages', peek_lock=True)
>>> print(msg.body)
Msg 1
>>> msg.delete()

How to Delete Topics and Subscriptions
--------------------------------------
>>> bus_service.delete_subscription('mytopic', 'HighMessages')
True

>>> bus_service.delete_queue('mytopic')
True

>>> bus_service.delete_queue('mytopic2')
True

"""
from util import credentials

ns = credentials.getServiceBusNamespace()
key = credentials.getServiceBusKey()

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = doctest_tableservice
#-------------------------------------------------------------------------
# Copyright (c) Microsoft.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#--------------------------------------------------------------------------

"""
How To: Create a Table
----------------------
>>> from azure.storage import *
>>> table_service = TableService(name, key)
>>> table_service.create_table('tasktable')
True

How to Add an Entity to a Table
-------------------------------
>>> task = {'PartitionKey': 'tasksSeattle', 'RowKey': '1', 'description' : 'Take out the trash', 'priority' : 200}
>>> entity = table_service.insert_entity('tasktable', task)

>>> task = Entity()
>>> task.PartitionKey = 'tasksSeattle'
>>> task.RowKey = '2'
>>> task.description = 'Wash the car'
>>> task.priority = 100
>>> entity = table_service.insert_entity('tasktable', task)

How to Update an Entity
-----------------------
>>> task = {'description' : 'Take out the garbage', 'priority' : 250}
>>> entity = table_service.update_entity('tasktable', 'tasksSeattle', '1', task)

>>> task = {'description' : 'Take out the garbage again', 'priority' : 250}
>>> entity = table_service.insert_or_replace_entity('tasktable', 'tasksSeattle', '1', task)

>>> task = {'description' : 'Buy detergent', 'priority' : 300}
>>> entity = table_service.insert_or_replace_entity('tasktable', 'tasksSeattle', '3', task)


How to Change a Group of Entities
---------------------------------
>>> task10 = {'PartitionKey': 'tasksSeattle', 'RowKey': '10', 'description' : 'Go grocery shopping', 'priority' : 400}
>>> task11 = {'PartitionKey': 'tasksSeattle', 'RowKey': '11', 'description' : 'Clean the bathroom', 'priority' : 100}
>>> table_service.begin_batch()
>>> table_service.insert_entity('tasktable', task10)
>>> table_service.insert_entity('tasktable', task11)
>>> table_service.commit_batch()

How to Query for an Entity
--------------------------
>>> task = table_service.get_entity('tasktable', 'tasksSeattle', '1')
>>> print(task.description)
Take out the garbage again
>>> print(task.priority)
250

>>> task = table_service.get_entity('tasktable', 'tasksSeattle', '10')
>>> print(task.description)
Go grocery shopping
>>> print(task.priority)
400

How to Query a Set of Entities
------------------------------
>>> tasks = table_service.query_entities('tasktable', "PartitionKey eq 'tasksSeattle'")
>>> for task in tasks:
...     print(task.description)
...     print(task.priority)
Take out the garbage again
250
Go grocery shopping
400
Clean the bathroom
100
Wash the car
100
Buy detergent
300

How to Query a Subset of Entity Properties
------------------------------------------
>>> tasks = table_service.query_entities('tasktable', "PartitionKey eq 'tasksSeattle'", 'description')
>>> for task in tasks:
...     print(task.description)
Take out the garbage again
Go grocery shopping
Clean the bathroom
Wash the car
Buy detergent

How to Delete an Entity
-----------------------
>>> table_service.delete_entity('tasktable', 'tasksSeattle', '1')

How to Delete a Table
---------------------
>>> table_service.delete_table('tasktable')
True

"""
from util import credentials

name = credentials.getStorageServicesName()
key = credentials.getStorageServicesKey()

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = test_affinitygroupmanagementservice
﻿#-------------------------------------------------------------------------
# Copyright (c) Microsoft.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#--------------------------------------------------------------------------
import unittest

from azure.servicemanagement import (
    AffinityGroups,
    AffinityGroup,
    Locations,
    ServiceManagementService,
    )
from util import (
    AzureTestCase,
    credentials,
    getUniqueName,
    set_service_options,
    )

#------------------------------------------------------------------------------


class AffinityGroupManagementServiceTest(AzureTestCase):

    def setUp(self):
        self.sms = ServiceManagementService(credentials.getSubscriptionId(),
                                            credentials.getManagementCertFile())
        set_service_options(self.sms)

        self.affinity_group_name = getUniqueName('utaffgrp')
        self.hosted_service_name = None
        self.storage_account_name = None

    def tearDown(self):
        try:
            if self.hosted_service_name is not None:
                self.sms.delete_hosted_service(self.hosted_service_name)
        except:
            pass

        try:
            if self.storage_account_name is not None:
                self.sms.delete_storage_account(self.storage_account_name)
        except:
            pass

        try:
            self.sms.delete_affinity_group(self.affinity_group_name)
        except:
            pass

    #--Helpers-----------------------------------------------------------------
    def _create_affinity_group(self, name):
        result = self.sms.create_affinity_group(
            name, 'tstmgmtaffgrp', 'West US', 'tstmgmt affinity group')
        self.assertIsNone(result)

    def _affinity_group_exists(self, name):
        try:
            props = self.sms.get_affinity_group_properties(name)
            return props is not None
        except:
            return False

    #--Test cases for affinity groups ------------------------------------
    def test_list_affinity_groups(self):
        # Arrange
        self._create_affinity_group(self.affinity_group_name)

        # Act
        result = self.sms.list_affinity_groups()

        # Assert
        self.assertIsNotNone(result)
        self.assertTrue(len(result) > 0)

        group = None
        for temp in result:
            if temp.name == self.affinity_group_name:
                group = temp
                break

        self.assertIsNotNone(group)
        self.assertIsNotNone(group.name)
        self.assertIsNotNone(group.label)
        self.assertIsNotNone(group.description)
        self.assertIsNotNone(group.location)
        self.assertIsNotNone(group.capabilities)
        self.assertTrue(len(group.capabilities) > 0)

    def test_get_affinity_group_properties(self):
        # Arrange
        self.hosted_service_name = getUniqueName('utsvc')
        self.storage_account_name = getUniqueName('utstorage')
        self._create_affinity_group(self.affinity_group_name)
        self.sms.create_hosted_service(
            self.hosted_service_name,
            'affgrptestlabel',
            'affgrptestdesc',
            None,
            self.affinity_group_name)
        self.sms.create_storage_account(
            self.storage_account_name,
            self.storage_account_name + 'desc',
            self.storage_account_name + 'label',
            self.affinity_group_name)

        # Act
        result = self.sms.get_affinity_group_properties(
            self.affinity_group_name)

        # Assert
        self.assertIsNotNone(result)
        self.assertEqual(result.name, self.affinity_group_name)
        self.assertIsNotNone(result.label)
        self.assertIsNotNone(result.description)
        self.assertIsNotNone(result.location)
        self.assertIsNotNone(result.hosted_services[0])
        self.assertEqual(
            result.hosted_services[0].service_name, self.hosted_service_name)
        self.assertEqual(
            result.hosted_services[0].hosted_service_properties.affinity_group,
            self.affinity_group_name)
        # not sure why azure does not return any storage service
        self.assertTrue(len(result.capabilities) > 0)

    def test_create_affinity_group(self):
        # Arrange
        label = 'tstmgmtaffgrp'
        description = 'tstmgmt affinity group'

        # Act
        result = self.sms.create_affinity_group(
            self.affinity_group_name, label, 'West US', description)

        # Assert
        self.assertIsNone(result)
        self.assertTrue(self._affinity_group_exists(self.affinity_group_name))

    def test_update_affinity_group(self):
        # Arrange
        self._create_affinity_group(self.affinity_group_name)
        label = 'tstlabelupdate'
        description = 'testmgmt affinity group update'

        # Act
        result = self.sms.update_affinity_group(
            self.affinity_group_name, label, description)

        # Assert
        self.assertIsNone(result)
        props = self.sms.get_affinity_group_properties(
            self.affinity_group_name)
        self.assertEqual(props.label, label)
        self.assertEqual(props.description, description)

    def test_delete_affinity_group(self):
        # Arrange
        self._create_affinity_group(self.affinity_group_name)

        # Act
        result = self.sms.delete_affinity_group(self.affinity_group_name)

        # Assert
        self.assertIsNone(result)
        self.assertFalse(self._affinity_group_exists(self.affinity_group_name))

    #--Test cases for locations ------------------------------------------
    def test_list_locations(self):
        # Arrange

        # Act
        result = self.sms.list_locations()

        # Assert
        self.assertIsNotNone(result)
        self.assertTrue(len(result) > 0)
        self.assertIsNotNone(result[0].name)
        self.assertIsNotNone(result[0].display_name)
        self.assertIsNotNone(result[0].available_services)
        self.assertTrue(len(result[0].available_services) > 0)

#------------------------------------------------------------------------------
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_blobservice
﻿# coding: utf-8

#-------------------------------------------------------------------------
# Copyright (c) Microsoft.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#--------------------------------------------------------------------------
import base64
import datetime
import os
import random
import sys
import time
import unittest
if sys.version_info < (3,):
    from httplib import HTTPConnection
else:
    from http.client import HTTPConnection

from azure import (
    WindowsAzureError,
    WindowsAzureConflictError,
    WindowsAzureMissingResourceError,
    BLOB_SERVICE_HOST_BASE,
    )
from azure.http import (
    HTTPRequest,
    HTTPResponse,
    )
from azure.storage import (
    AccessPolicy,
    BlobBlockList,
    BlobResult,
    Logging,
    Metrics,
    PageList,
    PageRange,
    SignedIdentifier,
    SignedIdentifiers,
    StorageServiceProperties,
    )
from azure.storage.blobservice import BlobService
from azure.storage.storageclient import (
    AZURE_STORAGE_ACCESS_KEY,
    AZURE_STORAGE_ACCOUNT,
    EMULATED,
    DEV_ACCOUNT_NAME,
    DEV_ACCOUNT_KEY,
    )
from azure.storage.sharedaccesssignature import (
    Permission,
    SharedAccessSignature,
    SharedAccessPolicy,
    WebResource,
    RESOURCE_BLOB,
    RESOURCE_CONTAINER,
    SHARED_ACCESS_PERMISSION,
    SIGNED_EXPIRY,
    SIGNED_IDENTIFIER,
    SIGNED_PERMISSION,
    SIGNED_RESOURCE,
    SIGNED_RESOURCE_TYPE,
    SIGNED_SIGNATURE,
    SIGNED_START,
    )
from util import (
    AzureTestCase,
    credentials,
    getUniqueName,
    set_service_options,
    )

#------------------------------------------------------------------------------


class BlobServiceTest(AzureTestCase):

    def setUp(self):
        self.bs = BlobService(credentials.getStorageServicesName(),
                              credentials.getStorageServicesKey())
        set_service_options(self.bs)

        self.bs2 = BlobService(credentials.getRemoteStorageServicesName(),
                               credentials.getRemoteStorageServicesKey())
        set_service_options(self.bs2)

        # test chunking functionality by reducing the threshold
        # for chunking and the size of each chunk, otherwise
        # the tests would take too long to execute
        self.bs._BLOB_MAX_DATA_SIZE = 64 * 1024
        self.bs._BLOB_MAX_CHUNK_DATA_SIZE = 4 * 1024

        self.container_name = getUniqueName('utcontainer')
        self.container_lease_id = None
        self.additional_container_names = []
        self.remote_container_name = None

    def tearDown(self):
        self.cleanup()
        return super(BlobServiceTest, self).tearDown()

    def cleanup(self):
        if self.container_lease_id:
            try:
                self.bs.lease_container(
                    self.container_name, 'release', self.container_lease_id)
            except:
                pass
        try:
            self.bs.delete_container(self.container_name)
        except:
            pass

        for name in self.additional_container_names:
            try:
                self.bs.delete_container(name)
            except:
                pass

        if self.remote_container_name:
            try:
                self.bs2.delete_container(self.remote_container_name)
            except:
                pass

    #--Helpers-----------------------------------------------------------------
    def _create_container(self, container_name):
        self.bs.create_container(container_name, None, None, True)

    def _create_container_and_block_blob(self, container_name, blob_name,
                                         blob_data):
        self._create_container(container_name)
        resp = self.bs.put_blob(
            container_name, blob_name, blob_data, 'BlockBlob')
        self.assertIsNone(resp)

    def _create_container_and_page_blob(self, container_name, blob_name,
                                        content_length):
        self._create_container(container_name)
        resp = self.bs.put_blob(self.container_name, blob_name, b'',
                                'PageBlob',
                                x_ms_blob_content_length=str(content_length))
        self.assertIsNone(resp)

    def _create_container_and_block_blob_with_random_data(self, container_name,
                                                          blob_name,
                                                          block_count,
                                                          block_size):
        self._create_container_and_block_blob(container_name, blob_name, '')
        block_list = []
        for i in range(0, block_count):
            block_id = '{0:04d}'.format(i)
            block_data = os.urandom(block_size)
            self.bs.put_block(container_name, blob_name, block_data, block_id)
            block_list.append(block_id)
        self.bs.put_block_list(container_name, blob_name, block_list)

    def _blob_exists(self, container_name, blob_name):
        resp = self.bs.list_blobs(container_name)
        for blob in resp:
            if blob.name == blob_name:
                return True
        return False

    def _create_remote_container_and_block_blob(self, source_blob_name, data,
                                                x_ms_blob_public_access):
        self.remote_container_name = getUniqueName('remotectnr')
        self.bs2.create_container(
            self.remote_container_name,
            x_ms_blob_public_access=x_ms_blob_public_access)
        self.bs2.put_block_blob_from_bytes(
            self.remote_container_name, source_blob_name, data)
        source_blob_url = self.bs2.make_blob_url(
            self.remote_container_name, source_blob_name)
        return source_blob_url

    def _wait_for_async_copy(self, container_name, blob_name):
        count = 0
        props = self.bs.get_blob_properties(container_name, blob_name)
        while props['x-ms-copy-status'] != 'success':
            count = count + 1
            if count > 5:
                self.assertTrue(
                    False, 'Timed out waiting for async copy to complete.')
            time.sleep(5)
            props = self.bs.get_blob_properties(container_name, blob_name)
        self.assertEqual(props['x-ms-copy-status'], 'success')

    def _make_blob_sas_url(self, account_name, account_key, container_name,
                           blob_name):
        sas = SharedAccessSignature(account_name, account_key)
        resource = '%s/%s' % (container_name, blob_name)
        permission = self._get_permission(sas, RESOURCE_BLOB, resource, 'r')
        sas.permission_set = [permission]

        web_rsrc = WebResource()
        web_rsrc.properties[SIGNED_RESOURCE_TYPE] = RESOURCE_BLOB
        web_rsrc.properties[SHARED_ACCESS_PERMISSION] = 'r'
        web_rsrc.path = '/{0}'.format(resource)
        web_rsrc.request_url = \
            'https://{0}.blob.core.windows.net/{1}/{2}'.format(account_name,
                                                               container_name,
                                                               blob_name)
        web_rsrc = sas.sign_request(web_rsrc)
        return web_rsrc.request_url

    def assertBlobEqual(self, container_name, blob_name, expected_data):
        actual_data = self.bs.get_blob(container_name, blob_name)
        self.assertEqual(actual_data, expected_data)

    def assertBlobLengthEqual(self, container_name, blob_name, expected_length):
        props = self.bs.get_blob_properties(container_name, blob_name)
        self.assertEqual(int(props['content-length']), expected_length)

    def _get_oversized_binary_data(self):
        '''Returns random binary data exceeding the size threshold for
        chunking blob upload.'''
        size = self.bs._BLOB_MAX_DATA_SIZE + 12345
        return os.urandom(size)

    def _get_expected_progress(self, blob_size, unknown_size=False):
        result = []
        index = 0
        total = None if unknown_size else blob_size
        while (index < blob_size):
            result.append((index, total))
            index += self.bs._BLOB_MAX_CHUNK_DATA_SIZE
        result.append((blob_size, total))
        return result

    def _get_oversized_page_blob_binary_data(self):
        '''Returns random binary data exceeding the size threshold for
        chunking blob upload.'''
        size = self.bs._BLOB_MAX_DATA_SIZE + 16384
        return os.urandom(size)

    def _get_oversized_text_data(self):
        '''Returns random unicode text data exceeding the size threshold for
        chunking blob upload.'''
        size = self.bs._BLOB_MAX_DATA_SIZE + 12345
        text = u''
        words = [u'hello', u'world', u'python', u'啊齄丂狛狜']
        while (len(text) < size):
            index = random.randint(0, len(words) - 1)
            text = text + u' ' + words[index]

        return text

    def _get_permission(self, sas, resource_type, resource_path, permission):
        date_format = "%Y-%m-%dT%H:%M:%SZ"
        start = datetime.datetime.utcnow() - datetime.timedelta(minutes=1)
        expiry = start + datetime.timedelta(hours=1)

        sap = SharedAccessPolicy(AccessPolicy(start.strftime(date_format),
                                              expiry.strftime(date_format),
                                              permission))

        signed_query = sas.generate_signed_query_string(resource_path,
                                                        resource_type,
                                                        sap)

        return Permission('/' + resource_path, signed_query)

    def _get_signed_web_resource(self, sas, resource_type, resource_path,
                                 permission):
        web_rsrc = WebResource()
        web_rsrc.properties[SIGNED_RESOURCE_TYPE] = resource_type
        web_rsrc.properties[SHARED_ACCESS_PERMISSION] = permission
        web_rsrc.path = '/' + resource_path
        web_rsrc.request_url = '/' + resource_path

        return sas.sign_request(web_rsrc)

    def _get_request(self, host, url):
        return self._web_request('GET', host, url)

    def _put_request(self, host, url, content, headers):
        return self._web_request('PUT', host, url, content, headers)

    def _del_request(self, host, url):
        return self._web_request('DELETE', host, url)

    def _web_request(self, method, host, url, content=None, headers=None):
        if content and not isinstance(content, bytes):
            raise TypeError('content should be bytes')

        connection = HTTPConnection(host)
        try:
            connection.putrequest(method, url)
            connection.putheader(
                'Content-Type', 'application/octet-stream;Charset=UTF-8')
            if headers:
                for name, val in headers.items():
                    connection.putheader(name, val)
            if content is not None:
                connection.putheader('Content-Length', str(len(content)))
            connection.endheaders()
            if content is not None:
                connection.send(content)

            resp = connection.getresponse()
            resp.getheaders()
            respbody = None
            if resp.length is None:
                respbody = resp.read()
            elif resp.length > 0:
                respbody = resp.read(resp.length)

            return respbody
        finally:
            connection.close()

    #--Test cases for blob service --------------------------------------------
    def test_create_blob_service_missing_arguments(self):
        # Arrange
        if AZURE_STORAGE_ACCOUNT in os.environ:
            del os.environ[AZURE_STORAGE_ACCOUNT]
        if AZURE_STORAGE_ACCESS_KEY in os.environ:
            del os.environ[AZURE_STORAGE_ACCESS_KEY]
        if EMULATED in os.environ:
            del os.environ[EMULATED]

        # Act
        with self.assertRaises(WindowsAzureError):
            bs = BlobService()

        # Assert

    def test_create_blob_service_env_variables(self):
        # Arrange
        os.environ[
            AZURE_STORAGE_ACCOUNT] = credentials.getStorageServicesName()
        os.environ[
            AZURE_STORAGE_ACCESS_KEY] = credentials.getStorageServicesKey()

        # Act
        bs = BlobService()

        if AZURE_STORAGE_ACCOUNT in os.environ:
            del os.environ[AZURE_STORAGE_ACCOUNT]
        if AZURE_STORAGE_ACCESS_KEY in os.environ:
            del os.environ[AZURE_STORAGE_ACCESS_KEY]

        # Assert
        self.assertIsNotNone(bs)
        self.assertEqual(bs.account_name, credentials.getStorageServicesName())
        self.assertEqual(bs.account_key, credentials.getStorageServicesKey())
        self.assertEqual(bs.is_emulated, False)

    def test_create_blob_service_emulated_true(self):
        # Arrange
        os.environ[EMULATED] = 'true'

        # Act
        bs = BlobService()

        if EMULATED in os.environ:
            del os.environ[EMULATED]

        # Assert
        self.assertIsNotNone(bs)
        self.assertEqual(bs.account_name, DEV_ACCOUNT_NAME)
        self.assertEqual(bs.account_key, DEV_ACCOUNT_KEY)
        self.assertEqual(bs.is_emulated, True)

    def test_create_blob_service_emulated_false(self):
        # Arrange
        os.environ[EMULATED] = 'false'

        # Act
        with self.assertRaises(WindowsAzureError):
            bs = BlobService()

        if EMULATED in os.environ:
            del os.environ[EMULATED]

        # Assert

    def test_create_blob_service_emulated_false_env_variables(self):
        # Arrange
        os.environ[EMULATED] = 'false'
        os.environ[
            AZURE_STORAGE_ACCOUNT] = credentials.getStorageServicesName()
        os.environ[
            AZURE_STORAGE_ACCESS_KEY] = credentials.getStorageServicesKey()

        # Act
        bs = BlobService()

        if EMULATED in os.environ:
            del os.environ[EMULATED]
        if AZURE_STORAGE_ACCOUNT in os.environ:
            del os.environ[AZURE_STORAGE_ACCOUNT]
        if AZURE_STORAGE_ACCESS_KEY in os.environ:
            del os.environ[AZURE_STORAGE_ACCESS_KEY]

        # Assert
        self.assertIsNotNone(bs)
        self.assertEqual(bs.account_name, credentials.getStorageServicesName())
        self.assertEqual(bs.account_key, credentials.getStorageServicesKey())
        self.assertEqual(bs.is_emulated, False)

    #--Test cases for containers -----------------------------------------
    def test_create_container_no_options(self):
        # Arrange

        # Act
        created = self.bs.create_container(self.container_name)

        # Assert
        self.assertTrue(created)

    def test_create_container_no_options_fail_on_exist(self):
        # Arrange

        # Act
        created = self.bs.create_container(
            self.container_name, None, None, True)

        # Assert
        self.assertTrue(created)

    def test_create_container_with_already_existing_container(self):
        # Arrange

        # Act
        created1 = self.bs.create_container(self.container_name)
        created2 = self.bs.create_container(self.container_name)

        # Assert
        self.assertTrue(created1)
        self.assertFalse(created2)

    def test_create_container_with_already_existing_container_fail_on_exist(self):
        # Arrange

        # Act
        created = self.bs.create_container(self.container_name)
        with self.assertRaises(WindowsAzureError):
            self.bs.create_container(self.container_name, None, None, True)

        # Assert
        self.assertTrue(created)

    def test_create_container_with_public_access_container(self):
        # Arrange

        # Act
        created = self.bs.create_container(
            self.container_name, None, 'container')

        # Assert
        self.assertTrue(created)
        acl = self.bs.get_container_acl(self.container_name)
        self.assertIsNotNone(acl)

    def test_create_container_with_public_access_blob(self):
        # Arrange

        # Act
        created = self.bs.create_container(self.container_name, None, 'blob')

        # Assert
        self.assertTrue(created)
        acl = self.bs.get_container_acl(self.container_name)
        self.assertIsNotNone(acl)

    def test_create_container_with_metadata(self):
        # Arrange

        # Act
        created = self.bs.create_container(
            self.container_name, {'hello': 'world', 'number': '42'})

        # Assert
        self.assertTrue(created)
        md = self.bs.get_container_metadata(self.container_name)
        self.assertIsNotNone(md)
        self.assertEqual(md['x-ms-meta-hello'], 'world')
        self.assertEqual(md['x-ms-meta-number'], '42')

    def test_list_containers_no_options(self):
        # Arrange
        self.bs.create_container(self.container_name)

        # Act
        containers = self.bs.list_containers()
        for container in containers:
            name = container.name

        # Assert
        self.assertIsNotNone(containers)
        self.assertGreaterEqual(len(containers), 1)
        self.assertIsNotNone(containers[0])
        self.assertNamedItemInContainer(containers, self.container_name)

    def test_list_containers_with_prefix(self):
        # Arrange
        self.bs.create_container(self.container_name)

        # Act
        containers = self.bs.list_containers(self.container_name)

        # Assert
        self.assertIsNotNone(containers)
        self.assertEqual(len(containers), 1)
        self.assertIsNotNone(containers[0])
        self.assertEqual(containers[0].name, self.container_name)
        self.assertIsNone(containers[0].metadata)

    def test_list_containers_with_include_metadata(self):
        # Arrange
        self.bs.create_container(self.container_name)
        resp = self.bs.set_container_metadata(
            self.container_name, {'hello': 'world', 'number': '43'})

        # Act
        containers = self.bs.list_containers(
            self.container_name, None, None, 'metadata')

        # Assert
        self.assertIsNotNone(containers)
        self.assertGreaterEqual(len(containers), 1)
        self.assertIsNotNone(containers[0])
        self.assertNamedItemInContainer(containers, self.container_name)
        self.assertEqual(containers[0].metadata['hello'], 'world')
        self.assertEqual(containers[0].metadata['number'], '43')

    def test_list_containers_with_maxresults_and_marker(self):
        # Arrange
        self.additional_container_names = [self.container_name + 'a',
                                           self.container_name + 'b',
                                           self.container_name + 'c',
                                           self.container_name + 'd']
        for name in self.additional_container_names:
            self.bs.create_container(name)

        # Act
        containers1 = self.bs.list_containers(self.container_name, None, 2)
        containers2 = self.bs.list_containers(
            self.container_name, containers1.next_marker, 2)

        # Assert
        self.assertIsNotNone(containers1)
        self.assertEqual(len(containers1), 2)
        self.assertNamedItemInContainer(containers1, self.container_name + 'a')
        self.assertNamedItemInContainer(containers1, self.container_name + 'b')
        self.assertIsNotNone(containers2)
        self.assertEqual(len(containers2), 2)
        self.assertNamedItemInContainer(containers2, self.container_name + 'c')
        self.assertNamedItemInContainer(containers2, self.container_name + 'd')

    def test_set_container_metadata(self):
        # Arrange
        self.bs.create_container(self.container_name)

        # Act
        resp = self.bs.set_container_metadata(
            self.container_name, {'hello': 'world', 'number': '43'})

        # Assert
        self.assertIsNone(resp)
        md = self.bs.get_container_metadata(self.container_name)
        self.assertIsNotNone(md)
        self.assertEqual(md['x-ms-meta-hello'], 'world')
        self.assertEqual(md['x-ms-meta-number'], '43')

    def test_set_container_metadata_with_lease_id(self):
        # Arrange
        self.bs.create_container(self.container_name)
        lease = self.bs.lease_container(self.container_name, 'acquire')
        self.container_lease_id = lease['x-ms-lease-id']

        # Act
        resp = self.bs.set_container_metadata(
            self.container_name,
            {'hello': 'world', 'number': '43'},
            lease['x-ms-lease-id'])

        # Assert
        self.assertIsNone(resp)
        md = self.bs.get_container_metadata(self.container_name)
        self.assertIsNotNone(md)
        self.assertEqual(md['x-ms-meta-hello'], 'world')
        self.assertEqual(md['x-ms-meta-number'], '43')

    def test_set_container_metadata_with_non_matching_lease_id(self):
        # Arrange
        self.bs.create_container(self.container_name)
        lease = self.bs.lease_container(self.container_name, 'acquire')
        self.container_lease_id = lease['x-ms-lease-id']

        # Act
        non_matching_lease_id = '00000000-1111-2222-3333-444444444444'
        with self.assertRaises(WindowsAzureError):
            self.bs.set_container_metadata(
                self.container_name,
                {'hello': 'world', 'number': '43'},
                non_matching_lease_id)

        # Assert

    def test_set_container_metadata_with_non_existing_container(self):
        # Arrange

        # Act
        with self.assertRaises(WindowsAzureError):
            self.bs.set_container_metadata(
                self.container_name, {'hello': 'world', 'number': '43'})

        # Assert

    def test_get_container_metadata(self):
        # Arrange
        self.bs.create_container(self.container_name)
        self.bs.set_container_acl(self.container_name, None, 'container')
        self.bs.set_container_metadata(
            self.container_name, {'hello': 'world', 'number': '42'})
        lease = self.bs.lease_container(self.container_name, 'acquire')
        self.container_lease_id = lease['x-ms-lease-id']

        # Act
        md = self.bs.get_container_metadata(self.container_name)

        # Assert
        self.assertIsNotNone(md)
        self.assertEqual(2, len(md))
        self.assertEqual(md['x-ms-meta-hello'], 'world')
        self.assertEqual(md['x-ms-meta-number'], '42')

    def test_get_container_metadata_with_lease_id(self):
        # Arrange
        self.bs.create_container(self.container_name)
        self.bs.set_container_acl(self.container_name, None, 'container')
        self.bs.set_container_metadata(
            self.container_name, {'hello': 'world', 'number': '42'})
        lease = self.bs.lease_container(self.container_name, 'acquire')
        self.container_lease_id = lease['x-ms-lease-id']

        # Act
        md = self.bs.get_container_metadata(
            self.container_name, lease['x-ms-lease-id'])

        # Assert
        self.assertIsNotNone(md)
        self.assertEqual(2, len(md))
        self.assertEqual(md['x-ms-meta-hello'], 'world')
        self.assertEqual(md['x-ms-meta-number'], '42')

    def test_get_container_metadata_with_non_matching_lease_id(self):
        # Arrange
        self.bs.create_container(self.container_name)
        self.bs.set_container_acl(self.container_name, None, 'container')
        self.bs.set_container_metadata(
            self.container_name, {'hello': 'world', 'number': '42'})
        lease = self.bs.lease_container(self.container_name, 'acquire')
        self.container_lease_id = lease['x-ms-lease-id']

        # Act
        non_matching_lease_id = '00000000-1111-2222-3333-444444444444'
        with self.assertRaises(WindowsAzureError):
            self.bs.get_container_metadata(
                self.container_name, non_matching_lease_id)

        # Assert

    def test_get_container_metadata_with_non_existing_container(self):
        # Arrange

        # Act
        with self.assertRaises(WindowsAzureError):
            self.bs.get_container_metadata(self.container_name)

        # Assert

    def test_get_container_properties(self):
        # Arrange
        self.bs.create_container(self.container_name)
        self.bs.set_container_acl(self.container_name, None, 'container')
        self.bs.set_container_metadata(
            self.container_name, {'hello': 'world', 'number': '42'})
        lease = self.bs.lease_container(self.container_name, 'acquire')
        self.container_lease_id = lease['x-ms-lease-id']

        # Act
        props = self.bs.get_container_properties(self.container_name)

        # Assert
        self.assertIsNotNone(props)
        self.assertEqual(props['x-ms-meta-hello'], 'world')
        self.assertEqual(props['x-ms-meta-number'], '42')
        self.assertEqual(props['x-ms-lease-duration'], 'fixed')
        self.assertEqual(props['x-ms-lease-state'], 'leased')
        self.assertEqual(props['x-ms-lease-status'], 'locked')

    def test_get_container_properties_with_lease_id(self):
        # Arrange
        self.bs.create_container(self.container_name)
        self.bs.set_container_acl(self.container_name, None, 'container')
        self.bs.set_container_metadata(
            self.container_name, {'hello': 'world', 'number': '42'})
        lease = self.bs.lease_container(self.container_name, 'acquire')
        self.container_lease_id = lease['x-ms-lease-id']

        # Act
        props = self.bs.get_container_properties(
            self.container_name, lease['x-ms-lease-id'])

        # Assert
        self.assertIsNotNone(props)
        self.assertEqual(props['x-ms-meta-hello'], 'world')
        self.assertEqual(props['x-ms-meta-number'], '42')
        self.assertEqual(props['x-ms-lease-duration'], 'fixed')
        self.assertEqual(props['x-ms-lease-status'], 'locked')
        self.assertEqual(props['x-ms-lease-state'], 'leased')

    def test_get_container_properties_with_non_matching_lease_id(self):
        # Arrange
        self.bs.create_container(self.container_name)
        self.bs.set_container_acl(self.container_name, None, 'container')
        self.bs.set_container_metadata(
            self.container_name, {'hello': 'world', 'number': '42'})
        lease = self.bs.lease_container(self.container_name, 'acquire')
        self.container_lease_id = lease['x-ms-lease-id']

        # Act
        non_matching_lease_id = '00000000-1111-2222-3333-444444444444'
        with self.assertRaises(WindowsAzureError):
            self.bs.get_container_properties(
                self.container_name, non_matching_lease_id)

        # Assert

    def test_get_container_properties_with_non_existing_container(self):
        # Arrange

        # Act
        with self.assertRaises(WindowsAzureError):
            self.bs.get_container_properties(self.container_name)

        # Assert

    def test_get_container_acl(self):
        # Arrange
        self.bs.create_container(self.container_name)

        # Act
        acl = self.bs.get_container_acl(self.container_name)

        # Assert
        self.assertIsNotNone(acl)
        self.assertEqual(len(acl.signed_identifiers), 0)

    def test_get_container_acl_iter(self):
        # Arrange
        self.bs.create_container(self.container_name)

        # Act
        acl = self.bs.get_container_acl(self.container_name)
        for signed_identifier in acl:
            pass

        # Assert
        self.assertIsNotNone(acl)
        self.assertEqual(len(acl.signed_identifiers), 0)
        self.assertEqual(len(acl), 0)

    def test_get_container_acl_with_lease_id(self):
        # Arrange
        self.bs.create_container(self.container_name)
        lease = self.bs.lease_container(self.container_name, 'acquire')
        self.container_lease_id = lease['x-ms-lease-id']

        # Act
        acl = self.bs.get_container_acl(
            self.container_name, lease['x-ms-lease-id'])

        # Assert
        self.assertIsNotNone(acl)
        self.assertEqual(len(acl.signed_identifiers), 0)

    def test_get_container_acl_with_non_matching_lease_id(self):
        # Arrange
        self.bs.create_container(self.container_name)
        lease = self.bs.lease_container(self.container_name, 'acquire')
        self.container_lease_id = lease['x-ms-lease-id']

        # Act
        non_matching_lease_id = '00000000-1111-2222-3333-444444444444'
        with self.assertRaises(WindowsAzureError):
            self.bs.get_container_acl(
                self.container_name, non_matching_lease_id)

        # Assert

    def test_get_container_acl_with_non_existing_container(self):
        # Arrange

        # Act
        with self.assertRaises(WindowsAzureError):
            self.bs.get_container_acl(self.container_name)

        # Assert

    def test_set_container_acl(self):
        # Arrange
        self.bs.create_container(self.container_name)

        # Act
        resp = self.bs.set_container_acl(self.container_name)

        # Assert
        self.assertIsNone(resp)
        acl = self.bs.get_container_acl(self.container_name)
        self.assertIsNotNone(acl)

    def test_set_container_acl_with_lease_id(self):
        # Arrange
        self.bs.create_container(self.container_name)
        lease = self.bs.lease_container(self.container_name, 'acquire')
        self.container_lease_id = lease['x-ms-lease-id']

        # Act
        resp = self.bs.set_container_acl(
            self.container_name, x_ms_lease_id=lease['x-ms-lease-id'])

        # Assert
        self.assertIsNone(resp)
        acl = self.bs.get_container_acl(self.container_name)
        self.assertIsNotNone(acl)

    def test_set_container_acl_with_non_matching_lease_id(self):
        # Arrange
        self.bs.create_container(self.container_name)
        lease = self.bs.lease_container(self.container_name, 'acquire')
        self.container_lease_id = lease['x-ms-lease-id']

        # Act
        non_matching_lease_id = '00000000-1111-2222-3333-444444444444'
        with self.assertRaises(WindowsAzureError):
            self.bs.set_container_acl(
                self.container_name, x_ms_lease_id=non_matching_lease_id)

        # Assert

    def test_set_container_acl_with_public_access_container(self):
        # Arrange
        self.bs.create_container(self.container_name)

        # Act
        resp = self.bs.set_container_acl(
            self.container_name, None, 'container')

        # Assert
        self.assertIsNone(resp)
        acl = self.bs.get_container_acl(self.container_name)
        self.assertIsNotNone(acl)

    def test_set_container_acl_with_public_access_blob(self):
        # Arrange
        self.bs.create_container(self.container_name)

        # Act
        resp = self.bs.set_container_acl(self.container_name, None, 'blob')

        # Assert
        self.assertIsNone(resp)
        acl = self.bs.get_container_acl(self.container_name)
        self.assertIsNotNone(acl)

    def test_set_container_acl_with_empty_signed_identifiers(self):
        # Arrange
        self.bs.create_container(self.container_name)

        # Act
        identifiers = SignedIdentifiers()

        resp = self.bs.set_container_acl(self.container_name, identifiers)

        # Assert
        self.assertIsNone(resp)
        acl = self.bs.get_container_acl(self.container_name)
        self.assertIsNotNone(acl)
        self.assertEqual(len(acl.signed_identifiers), 0)

    def test_set_container_acl_with_signed_identifiers(self):
        # Arrange
        self.bs.create_container(self.container_name)

        # Act
        si = SignedIdentifier()
        si.id = 'testid'
        si.access_policy.start = '2011-10-11'
        si.access_policy.expiry = '2011-10-12'
        si.access_policy.permission = 'r'
        identifiers = SignedIdentifiers()
        identifiers.signed_identifiers.append(si)

        resp = self.bs.set_container_acl(self.container_name, identifiers)

        # Assert
        self.assertIsNone(resp)
        acl = self.bs.get_container_acl(self.container_name)
        self.assertIsNotNone(acl)
        self.assertEqual(len(acl.signed_identifiers), 1)
        self.assertEqual(len(acl), 1)
        self.assertEqual(acl.signed_identifiers[0].id, 'testid')
        self.assertEqual(acl[0].id, 'testid')

    def test_set_container_acl_with_non_existing_container(self):
        # Arrange

        # Act
        with self.assertRaises(WindowsAzureError):
            self.bs.set_container_acl(self.container_name, None, 'container')

        # Assert

    def test_lease_container_acquire_and_release(self):
        # Arrange
        self.bs.create_container(self.container_name)

        # Act
        lease = self.bs.lease_container(self.container_name, 'acquire')
        self.container_lease_id = lease['x-ms-lease-id']
        lease = self.bs.lease_container(
            self.container_name,
            'release',
            x_ms_lease_id=lease['x-ms-lease-id'])
        self.container_lease_id = None

        # Assert

    def test_lease_container_renew(self):
        # Arrange
        self.bs.create_container(self.container_name)
        lease = self.bs.lease_container(
            self.container_name, 'acquire', x_ms_lease_duration=15)
        self.container_lease_id = lease['x-ms-lease-id']
        time.sleep(10)

        # Act
        renewed_lease = self.bs.lease_container(
            self.container_name, 'renew', x_ms_lease_id=lease['x-ms-lease-id'])

        # Assert
        self.assertEqual(lease['x-ms-lease-id'],
                         renewed_lease['x-ms-lease-id'])
        time.sleep(5)
        with self.assertRaises(WindowsAzureError):
            self.bs.delete_container(self.container_name)
        time.sleep(10)
        self.bs.delete_container(self.container_name)

    def test_lease_container_break_period(self):
        # Arrange
        self.bs.create_container(self.container_name)

        # Act
        lease = self.bs.lease_container(
            self.container_name, 'acquire', x_ms_lease_duration=15)
        self.container_lease_id = lease['x-ms-lease-id']

        # Assert
        self.bs.lease_container(self.container_name,
                                'break',
                                x_ms_lease_id=lease['x-ms-lease-id'],
                                x_ms_lease_break_period=5)
        time.sleep(5)
        with self.assertRaises(WindowsAzureError):
            self.bs.delete_container(
                self.container_name, x_ms_lease_id=lease['x-ms-lease-id'])

    def test_lease_container_break_released_lease_fails(self):
        # Arrange
        self.bs.create_container(self.container_name)
        lease = self.bs.lease_container(self.container_name, 'acquire')
        self.container_lease_id = lease['x-ms-lease-id']
        self.bs.lease_container(
            self.container_name, 'release', lease['x-ms-lease-id'])

        # Act
        with self.assertRaises(WindowsAzureError):
            self.bs.lease_container(
                self.container_name, 'break', lease['x-ms-lease-id'])

        # Assert

    def test_lease_container_acquire_after_break_fails(self):
        # Arrange
        self.bs.create_container(self.container_name)
        lease = self.bs.lease_container(self.container_name, 'acquire')
        self.container_lease_id = lease['x-ms-lease-id']
        self.bs.lease_container(
            self.container_name, 'break', lease['x-ms-lease-id'])

        # Act
        with self.assertRaises(WindowsAzureError):
            self.bs.lease_container(self.container_name, 'acquire')

        # Assert

    def test_lease_container_with_duration(self):
        # Arrange
        self.bs.create_container(self.container_name)

        # Act
        lease = self.bs.lease_container(
            self.container_name, 'acquire', x_ms_lease_duration=15)
        self.container_lease_id = lease['x-ms-lease-id']

        # Assert
        with self.assertRaises(WindowsAzureError):
            self.bs.lease_container(self.container_name, 'acquire')
        time.sleep(15)
        lease = self.bs.lease_container(self.container_name, 'acquire')
        self.container_lease_id = lease['x-ms-lease-id']

    def test_lease_container_with_proposed_lease_id(self):
        # Arrange
        self.bs.create_container(self.container_name)

        # Act
        lease_id = '55e97f64-73e8-4390-838d-d9e84a374321'
        lease = self.bs.lease_container(
            self.container_name, 'acquire', x_ms_proposed_lease_id=lease_id)
        self.container_lease_id = lease['x-ms-lease-id']

        # Assert
        self.assertIsNotNone(lease)
        self.assertEqual(lease['x-ms-lease-id'], lease_id)

    def test_lease_container_change_lease_id(self):
        # Arrange
        self.bs.create_container(self.container_name)

        # Act
        lease_id = '29e0b239-ecda-4f69-bfa3-95f6af91464c'
        lease1 = self.bs.lease_container(self.container_name, 'acquire')
        self.container_lease_id = lease1['x-ms-lease-id']
        lease2 = self.bs.lease_container(self.container_name,
                                         'change',
                                         x_ms_lease_id=lease1['x-ms-lease-id'],
                                         x_ms_proposed_lease_id=lease_id)
        self.container_lease_id = lease2['x-ms-lease-id']

        # Assert
        self.assertIsNotNone(lease1)
        self.assertIsNotNone(lease2)
        self.assertNotEqual(lease1['x-ms-lease-id'], lease_id)
        self.assertEqual(lease2['x-ms-lease-id'], lease_id)

    def test_delete_container_with_existing_container(self):
        # Arrange
        self.bs.create_container(self.container_name)

        # Act
        deleted = self.bs.delete_container(self.container_name)

        # Assert
        self.assertTrue(deleted)
        containers = self.bs.list_containers()
        self.assertNamedItemNotInContainer(containers, self.container_name)

    def test_delete_container_with_existing_container_fail_not_exist(self):
        # Arrange
        self.bs.create_container(self.container_name)

        # Act
        deleted = self.bs.delete_container(self.container_name, True)

        # Assert
        self.assertTrue(deleted)
        containers = self.bs.list_containers()
        self.assertNamedItemNotInContainer(containers, self.container_name)

    def test_delete_container_with_non_existing_container(self):
        # Arrange

        # Act
        deleted = self.bs.delete_container(self.container_name)

        # Assert
        self.assertFalse(deleted)

    def test_delete_container_with_non_existing_container_fail_not_exist(self):
        # Arrange

        # Act
        with self.assertRaises(WindowsAzureError):
            self.bs.delete_container(self.container_name, True)

        # Assert

    def test_delete_container_with_lease_id(self):
        # Arrange
        self.bs.create_container(self.container_name)
        lease = self.bs.lease_container(
            self.container_name, 'acquire', x_ms_lease_duration=15)
        self.container_lease_id = lease['x-ms-lease-id']

        # Act
        deleted = self.bs.delete_container(
            self.container_name, x_ms_lease_id=lease['x-ms-lease-id'])

        # Assert
        self.assertTrue(deleted)
        containers = self.bs.list_containers()
        self.assertNamedItemNotInContainer(containers, self.container_name)

    def test_delete_container_without_lease_id(self):
        # Arrange
        self.bs.create_container(self.container_name)
        lease = self.bs.lease_container(
            self.container_name, 'acquire', x_ms_lease_duration=15)
        self.container_lease_id = lease['x-ms-lease-id']

        # Act
        with self.assertRaises(WindowsAzureError):
            self.bs.delete_container(self.container_name)

        # Assert

    #--Test cases for blob service ---------------------------------------
    def test_set_blob_service_properties(self):
        # Arrange

        # Act
        props = StorageServiceProperties()
        props.metrics.enabled = False
        resp = self.bs.set_blob_service_properties(props)

        # Assert
        self.assertIsNone(resp)
        received_props = self.bs.get_blob_service_properties()
        self.assertFalse(received_props.metrics.enabled)

    def test_set_blob_service_properties_with_timeout(self):
        # Arrange

        # Act
        props = StorageServiceProperties()
        props.logging.write = True
        resp = self.bs.set_blob_service_properties(props, 5)

        # Assert
        self.assertIsNone(resp)
        received_props = self.bs.get_blob_service_properties()
        self.assertTrue(received_props.logging.write)

    def test_get_blob_service_properties(self):
        # Arrange

        # Act
        props = self.bs.get_blob_service_properties()

        # Assert
        self.assertIsNotNone(props)
        self.assertIsInstance(props.logging, Logging)
        self.assertIsInstance(props.metrics, Metrics)

    def test_get_blob_service_properties_with_timeout(self):
        # Arrange

        # Act
        props = self.bs.get_blob_service_properties(5)

        # Assert
        self.assertIsNotNone(props)
        self.assertIsInstance(props.logging, Logging)
        self.assertIsInstance(props.metrics, Metrics)

    #--Test cases for blobs ----------------------------------------------
    def test_make_blob_url(self):
        # Arrange

        # Act
        res = self.bs.make_blob_url('vhds', 'my.vhd')

        # Assert
        self.assertEqual(res, 'https://' + credentials.getStorageServicesName()
                         + '.blob.core.windows.net/vhds/my.vhd')

    def test_make_blob_url_with_account_name(self):
        # Arrange

        # Act
        res = self.bs.make_blob_url('vhds', 'my.vhd', account_name='myaccount')

        # Assert
        self.assertEqual(
            res, 'https://myaccount.blob.core.windows.net/vhds/my.vhd')

    def test_make_blob_url_with_protocol(self):
        # Arrange

        # Act
        res = self.bs.make_blob_url('vhds', 'my.vhd', protocol='http')

        # Assert
        self.assertEqual(res, 'http://' + credentials.getStorageServicesName()
                         + '.blob.core.windows.net/vhds/my.vhd')

    def test_make_blob_url_with_host_base(self):
        # Arrange

        # Act
        res = self.bs.make_blob_url(
            'vhds', 'my.vhd', host_base='.blob.internal.net')

        # Assert
        self.assertEqual(res, 'https://' + credentials.getStorageServicesName()
                         + '.blob.internal.net/vhds/my.vhd')

    def test_make_blob_url_with_all(self):
        # Arrange

        # Act
        res = self.bs.make_blob_url(
            'vhds', 'my.vhd', account_name='myaccount', protocol='http',
            host_base='.blob.internal.net')

        # Assert
        self.assertEqual(res, 'http://myaccount.blob.internal.net/vhds/my.vhd')

    def test_list_blobs(self):
        # Arrange
        self._create_container(self.container_name)
        data = b'hello world'
        self.bs.put_blob(self.container_name, 'blob1', data, 'BlockBlob')
        self.bs.put_blob(self.container_name, 'blob2', data, 'BlockBlob')

        # Act
        resp = self.bs.list_blobs(self.container_name)
        for blob in resp:
            name = blob.name

        # Assert
        self.assertIsNotNone(resp)
        self.assertGreaterEqual(len(resp), 2)
        self.assertIsNotNone(resp[0])
        self.assertNamedItemInContainer(resp, 'blob1')
        self.assertNamedItemInContainer(resp, 'blob2')
        self.assertEqual(resp[0].properties.content_length, 11)
        self.assertEqual(resp[1].properties.content_type,
                         'application/octet-stream Charset=UTF-8')

    def test_list_blobs_leased_blob(self):
        # Arrange
        self._create_container(self.container_name)
        data = b'hello world'
        self.bs.put_blob(self.container_name, 'blob1', data, 'BlockBlob')
        lease = self.bs.lease_blob(self.container_name, 'blob1', 'acquire')

        # Act
        resp = self.bs.list_blobs(self.container_name)
        for blob in resp:
            name = blob.name

        # Assert
        self.assertIsNotNone(resp)
        self.assertGreaterEqual(len(resp), 1)
        self.assertIsNotNone(resp[0])
        self.assertNamedItemInContainer(resp, 'blob1')
        self.assertEqual(resp[0].properties.content_length, 11)
        self.assertEqual(resp[0].properties.lease_duration, 'fixed')
        self.assertEqual(resp[0].properties.lease_status, 'locked')
        self.assertEqual(resp[0].properties.lease_state, 'leased')

    def test_list_blobs_with_prefix(self):
        # Arrange
        self._create_container(self.container_name)
        data = b'hello world'
        self.bs.put_blob(self.container_name, 'bloba1', data, 'BlockBlob')
        self.bs.put_blob(self.container_name, 'bloba2', data, 'BlockBlob')
        self.bs.put_blob(self.container_name, 'blobb1', data, 'BlockBlob')

        # Act
        resp = self.bs.list_blobs(self.container_name, 'bloba')

        # Assert
        self.assertIsNotNone(resp)
        self.assertEqual(len(resp), 2)
        self.assertEqual(len(resp.blobs), 2)
        self.assertEqual(len(resp.prefixes), 0)
        self.assertEqual(resp.prefix, 'bloba')
        self.assertNamedItemInContainer(resp, 'bloba1')
        self.assertNamedItemInContainer(resp, 'bloba2')

    def test_list_blobs_with_prefix_and_delimiter(self):
        # Arrange
        self._create_container(self.container_name)
        data = b'hello world'
        self.bs.put_blob(self.container_name,
                         'documents/music/pop/thriller.mp3', data, 'BlockBlob')
        self.bs.put_blob(self.container_name,
                         'documents/music/rock/stairwaytoheaven.mp3', data,
                         'BlockBlob')
        self.bs.put_blob(self.container_name,
                         'documents/music/rock/hurt.mp3', data, 'BlockBlob')
        self.bs.put_blob(self.container_name,
                         'documents/music/rock/metallica/one.mp3', data,
                         'BlockBlob')
        self.bs.put_blob(self.container_name,
                         'documents/music/unsorted1.mp3', data, 'BlockBlob')
        self.bs.put_blob(self.container_name,
                         'documents/music/unsorted2.mp3', data, 'BlockBlob')
        self.bs.put_blob(self.container_name,
                         'documents/pictures/birthday/kid.jpg', data,
                         'BlockBlob')
        self.bs.put_blob(self.container_name,
                         'documents/pictures/birthday/cake.jpg', data,
                         'BlockBlob')

        # Act
        resp = self.bs.list_blobs(
            self.container_name, 'documents/music/', delimiter='/')

        # Assert
        self.assertIsNotNone(resp)
        self.assertEqual(len(resp), 2)
        self.assertEqual(len(resp.blobs), 2)
        self.assertEqual(len(resp.prefixes), 2)
        self.assertEqual(resp.prefix, 'documents/music/')
        self.assertEqual(resp.delimiter, '/')
        self.assertNamedItemInContainer(resp, 'documents/music/unsorted1.mp3')
        self.assertNamedItemInContainer(resp, 'documents/music/unsorted2.mp3')
        self.assertNamedItemInContainer(
            resp.blobs, 'documents/music/unsorted1.mp3')
        self.assertNamedItemInContainer(
            resp.blobs, 'documents/music/unsorted2.mp3')
        self.assertNamedItemInContainer(resp.prefixes, 'documents/music/pop/')
        self.assertNamedItemInContainer(resp.prefixes, 'documents/music/rock/')

    def test_list_blobs_with_maxresults(self):
        # Arrange
        self._create_container(self.container_name)
        data = b'hello world'
        self.bs.put_blob(self.container_name, 'bloba1', data, 'BlockBlob')
        self.bs.put_blob(self.container_name, 'bloba2', data, 'BlockBlob')
        self.bs.put_blob(self.container_name, 'bloba3', data, 'BlockBlob')
        self.bs.put_blob(self.container_name, 'blobb1', data, 'BlockBlob')

        # Act
        blobs = self.bs.list_blobs(self.container_name, None, None, 2)

        # Assert
        self.assertIsNotNone(blobs)
        self.assertEqual(len(blobs), 2)
        self.assertNamedItemInContainer(blobs, 'bloba1')
        self.assertNamedItemInContainer(blobs, 'bloba2')

    def test_list_blobs_with_maxresults_and_marker(self):
        # Arrange
        self._create_container(self.container_name)
        data = b'hello world'
        self.bs.put_blob(self.container_name, 'bloba1', data, 'BlockBlob')
        self.bs.put_blob(self.container_name, 'bloba2', data, 'BlockBlob')
        self.bs.put_blob(self.container_name, 'bloba3', data, 'BlockBlob')
        self.bs.put_blob(self.container_name, 'blobb1', data, 'BlockBlob')

        # Act
        blobs1 = self.bs.list_blobs(self.container_name, None, None, 2)
        blobs2 = self.bs.list_blobs(
            self.container_name, None, blobs1.next_marker, 2)

        # Assert
        self.assertEqual(len(blobs1), 2)
        self.assertEqual(len(blobs2), 2)
        self.assertNamedItemInContainer(blobs1, 'bloba1')
        self.assertNamedItemInContainer(blobs1, 'bloba2')
        self.assertNamedItemInContainer(blobs2, 'bloba3')
        self.assertNamedItemInContainer(blobs2, 'blobb1')

    def test_list_blobs_with_include_snapshots(self):
        # Arrange
        self._create_container(self.container_name)
        data = b'hello world'
        self.bs.put_blob(self.container_name, 'blob1', data, 'BlockBlob')
        self.bs.put_blob(self.container_name, 'blob2', data, 'BlockBlob')
        self.bs.snapshot_blob(self.container_name, 'blob1')

        # Act
        blobs = self.bs.list_blobs(self.container_name, include='snapshots')

        # Assert
        self.assertEqual(len(blobs), 3)
        self.assertEqual(blobs[0].name, 'blob1')
        self.assertNotEqual(blobs[0].snapshot, '')
        self.assertEqual(blobs[1].name, 'blob1')
        self.assertEqual(blobs[1].snapshot, '')
        self.assertEqual(blobs[2].name, 'blob2')
        self.assertEqual(blobs[2].snapshot, '')

    def test_list_blobs_with_include_metadata(self):
        # Arrange
        self._create_container(self.container_name)
        data = b'hello world'
        self.bs.put_blob(self.container_name, 'blob1', data, 'BlockBlob',
                         x_ms_meta_name_values={'number': '1', 'name': 'bob'})
        self.bs.put_blob(self.container_name, 'blob2', data, 'BlockBlob',
                         x_ms_meta_name_values={'number': '2', 'name': 'car'})
        self.bs.snapshot_blob(self.container_name, 'blob1')

        # Act
        blobs = self.bs.list_blobs(self.container_name, include='metadata')

        # Assert
        self.assertEqual(len(blobs), 2)
        self.assertEqual(blobs[0].name, 'blob1')
        self.assertEqual(blobs[0].metadata['number'], '1')
        self.assertEqual(blobs[0].metadata['name'], 'bob')
        self.assertEqual(blobs[1].name, 'blob2')
        self.assertEqual(blobs[1].metadata['number'], '2')
        self.assertEqual(blobs[1].metadata['name'], 'car')

    def test_list_blobs_with_include_uncommittedblobs(self):
        # Arrange
        self._create_container(self.container_name)
        data = b'hello world'
        self.bs.put_block(self.container_name, 'blob1', b'AAA', '1')
        self.bs.put_block(self.container_name, 'blob1', b'BBB', '2')
        self.bs.put_block(self.container_name, 'blob1', b'CCC', '3')
        self.bs.put_blob(self.container_name, 'blob2', data, 'BlockBlob',
                         x_ms_meta_name_values={'number': '2', 'name': 'car'})

        # Act
        blobs = self.bs.list_blobs(
            self.container_name, include='uncommittedblobs')

        # Assert
        self.assertEqual(len(blobs), 2)
        self.assertEqual(blobs[0].name, 'blob1')
        self.assertEqual(blobs[1].name, 'blob2')

    def test_list_blobs_with_include_copy(self):
        # Arrange
        self._create_container(self.container_name)
        data = b'hello world'
        self.bs.put_blob(self.container_name, 'blob1', data,
                         'BlockBlob',
                         x_ms_meta_name_values={'status': 'original'})
        sourceblob = 'https://{0}.blob.core.windows.net/{1}/{2}'.format(
            credentials.getStorageServicesName(),
            self.container_name,
            'blob1')
        self.bs.copy_blob(self.container_name, 'blob1copy',
                          sourceblob, {'status': 'copy'})

        # Act
        blobs = self.bs.list_blobs(self.container_name, include='copy')

        # Assert
        self.assertEqual(len(blobs), 2)
        self.assertEqual(blobs[0].name, 'blob1')
        self.assertEqual(blobs[1].name, 'blob1copy')
        self.assertEqual(blobs[1].properties.content_length, 11)
        self.assertEqual(blobs[1].properties.content_type,
                         'application/octet-stream Charset=UTF-8')
        self.assertEqual(blobs[1].properties.content_encoding, '')
        self.assertEqual(blobs[1].properties.content_language, '')
        self.assertNotEqual(blobs[1].properties.content_md5, '')
        self.assertEqual(blobs[1].properties.blob_type, 'BlockBlob')
        self.assertEqual(blobs[1].properties.lease_status, 'unlocked')
        self.assertEqual(blobs[1].properties.lease_state, 'available')
        self.assertNotEqual(blobs[1].properties.copy_id, '')
        self.assertEqual(blobs[1].properties.copy_source, sourceblob)
        self.assertEqual(blobs[1].properties.copy_status, 'success')
        self.assertEqual(blobs[1].properties.copy_progress, '11/11')
        self.assertNotEqual(blobs[1].properties.copy_completion_time, '')

    def test_list_blobs_with_include_multiple(self):
        # Arrange
        self._create_container(self.container_name)
        data = b'hello world'
        self.bs.put_blob(self.container_name, 'blob1', data, 'BlockBlob',
                         x_ms_meta_name_values={'number': '1', 'name': 'bob'})
        self.bs.put_blob(self.container_name, 'blob2', data, 'BlockBlob',
                         x_ms_meta_name_values={'number': '2', 'name': 'car'})
        self.bs.snapshot_blob(self.container_name, 'blob1')

        # Act
        blobs = self.bs.list_blobs(
            self.container_name, include='snapshots,metadata')

        # Assert
        self.assertEqual(len(blobs), 3)
        self.assertEqual(blobs[0].name, 'blob1')
        self.assertNotEqual(blobs[0].snapshot, '')
        self.assertEqual(blobs[0].metadata['number'], '1')
        self.assertEqual(blobs[0].metadata['name'], 'bob')
        self.assertEqual(blobs[1].name, 'blob1')
        self.assertEqual(blobs[1].snapshot, '')
        self.assertEqual(blobs[1].metadata['number'], '1')
        self.assertEqual(blobs[1].metadata['name'], 'bob')
        self.assertEqual(blobs[2].name, 'blob2')
        self.assertEqual(blobs[2].snapshot, '')
        self.assertEqual(blobs[2].metadata['number'], '2')
        self.assertEqual(blobs[2].metadata['name'], 'car')

    def test_put_blob_block_blob(self):
        # Arrange
        self._create_container(self.container_name)

        # Act
        data = b'hello world'
        resp = self.bs.put_blob(
            self.container_name, 'blob1', data, 'BlockBlob')

        # Assert
        self.assertIsNone(resp)

    def test_put_blob_block_blob_unicode_python_27(self):
        '''Test for auto-encoding of unicode text (backwards compatibility).'''
        if sys.version_info >= (3,):
            return

        # Arrange
        self._create_container(self.container_name)

        # Act
        data = u'啊齄丂狛狜'
        resp = self.bs.put_blob(
            self.container_name, 'blob1', data, 'BlockBlob')

        # Assert
        self.assertIsNone(resp)
        blob = self.bs.get_blob(self.container_name, 'blob1')
        self.assertEqual(blob, data.encode('utf-8'))

    def test_put_blob_block_blob_unicode_python_33(self):
        if sys.version_info < (3,):
            return

        # Arrange
        self._create_container(self.container_name)

        # Act
        data = u'hello world'
        with self.assertRaises(TypeError):
            resp = self.bs.put_blob(
                self.container_name, 'blob1', data, 'BlockBlob')

        # Assert

    def test_put_blob_page_blob(self):
        # Arrange
        self._create_container(self.container_name)

        # Act
        resp = self.bs.put_blob(self.container_name, 'blob1',
                                b'', 'PageBlob',
                                x_ms_blob_content_length='1024')

        # Assert
        self.assertIsNone(resp)

    def test_put_blob_with_lease_id(self):
        # Arrange
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world')
        lease = self.bs.lease_blob(self.container_name, 'blob1', 'acquire')
        lease_id = lease['x-ms-lease-id']

        # Act
        data = b'hello world again'
        resp = self.bs.put_blob(
            self.container_name, 'blob1', data, 'BlockBlob',
            x_ms_lease_id=lease_id)

        # Assert
        self.assertIsNone(resp)
        blob = self.bs.get_blob(
            self.container_name, 'blob1', x_ms_lease_id=lease_id)
        self.assertEqual(blob, b'hello world again')

    def test_put_blob_with_metadata(self):
        # Arrange
        self._create_container(self.container_name)

        # Act
        data = b'hello world'
        resp = self.bs.put_blob(
            self.container_name, 'blob1', data, 'BlockBlob',
            x_ms_meta_name_values={'hello': 'world', 'number': '42'})

        # Assert
        self.assertIsNone(resp)
        md = self.bs.get_blob_metadata(self.container_name, 'blob1')
        self.assertEqual(md['x-ms-meta-hello'], 'world')
        self.assertEqual(md['x-ms-meta-number'], '42')

    def test_get_blob_with_existing_blob(self):
        # Arrange
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world')

        # Act
        blob = self.bs.get_blob(self.container_name, 'blob1')

        # Assert
        self.assertIsInstance(blob, BlobResult)
        self.assertEqual(blob, b'hello world')

    def test_get_blob_with_snapshot(self):
        # Arrange
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world')
        snapshot = self.bs.snapshot_blob(self.container_name, 'blob1')

        # Act
        blob = self.bs.get_blob(
            self.container_name, 'blob1', snapshot['x-ms-snapshot'])

        # Assert
        self.assertIsInstance(blob, BlobResult)
        self.assertEqual(blob, b'hello world')

    def test_get_blob_with_snapshot_previous(self):
        # Arrange
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world')
        snapshot = self.bs.snapshot_blob(self.container_name, 'blob1')
        self.bs.put_blob(self.container_name, 'blob1',
                         b'hello world again', 'BlockBlob')

        # Act
        blob_previous = self.bs.get_blob(
            self.container_name, 'blob1', snapshot['x-ms-snapshot'])
        blob_latest = self.bs.get_blob(self.container_name, 'blob1')

        # Assert
        self.assertIsInstance(blob_previous, BlobResult)
        self.assertIsInstance(blob_latest, BlobResult)
        self.assertEqual(blob_previous, b'hello world')
        self.assertEqual(blob_latest, b'hello world again')

    def test_get_blob_with_range(self):
        # Arrange
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world')

        # Act
        blob = self.bs.get_blob(
            self.container_name, 'blob1', x_ms_range='bytes=0-5')

        # Assert
        self.assertIsInstance(blob, BlobResult)
        self.assertEqual(blob, b'hello ')

    def test_get_blob_with_range_and_get_content_md5(self):
        # Arrange
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world')

        # Act
        blob = self.bs.get_blob(self.container_name, 'blob1',
                                x_ms_range='bytes=0-5',
                                x_ms_range_get_content_md5='true')

        # Assert
        self.assertIsInstance(blob, BlobResult)
        self.assertEqual(blob, b'hello ')
        self.assertEqual(
            blob.properties['content-md5'], '+BSJN3e8wilf/wXwDlCNpg==')

    def test_get_blob_with_lease(self):
        # Arrange
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world')
        lease = self.bs.lease_blob(self.container_name, 'blob1', 'acquire')
        lease_id = lease['x-ms-lease-id']

        # Act
        blob = self.bs.get_blob(
            self.container_name, 'blob1', x_ms_lease_id=lease_id)
        self.bs.lease_blob(self.container_name, 'blob1', 'release', lease_id)

        # Assert
        self.assertIsInstance(blob, BlobResult)
        self.assertEqual(blob, b'hello world')

    def test_get_blob_on_leased_blob_without_lease_id(self):
        # Arrange
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world')
        self.bs.lease_blob(self.container_name, 'blob1', 'acquire')

        # Act
        # get_blob is allowed without lease id
        blob = self.bs.get_blob(self.container_name, 'blob1')

        # Assert
        self.assertIsInstance(blob, BlobResult)
        self.assertEqual(blob, b'hello world')

    def test_get_blob_with_non_existing_container(self):
        # Arrange

        # Act
        with self.assertRaises(WindowsAzureError):
            self.bs.get_blob(self.container_name, 'blob1')

        # Assert

    def test_get_blob_with_non_existing_blob(self):
        # Arrange
        self._create_container(self.container_name)

        # Act
        with self.assertRaises(WindowsAzureError):
            self.bs.get_blob(self.container_name, 'blob1')

        # Assert

    def test_set_blob_properties_with_existing_blob(self):
        # Arrange
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world')

        # Act
        resp = self.bs.set_blob_properties(
            self.container_name, 'blob1', x_ms_blob_content_language='spanish')

        # Assert
        self.assertIsNone(resp)
        props = self.bs.get_blob_properties(self.container_name, 'blob1')
        self.assertEqual(props['content-language'], 'spanish')

    def test_set_blob_properties_with_non_existing_container(self):
        # Arrange

        # Act
        with self.assertRaises(WindowsAzureError):
            self.bs.set_blob_properties(
                self.container_name, 'blob1',
                x_ms_blob_content_language='spanish')

        # Assert

    def test_set_blob_properties_with_non_existing_blob(self):
        # Arrange
        self._create_container(self.container_name)

        # Act
        with self.assertRaises(WindowsAzureError):
            self.bs.set_blob_properties(
                self.container_name, 'blob1',
                x_ms_blob_content_language='spanish')

        # Assert

    def test_get_blob_properties_with_existing_blob(self):
        # Arrange
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world')

        # Act
        props = self.bs.get_blob_properties(self.container_name, 'blob1')

        # Assert
        self.assertIsNotNone(props)
        self.assertEqual(props['x-ms-blob-type'], 'BlockBlob')
        self.assertEqual(props['content-length'], '11')
        self.assertEqual(props['x-ms-lease-status'], 'unlocked')

    def test_get_blob_properties_with_leased_blob(self):
        # Arrange
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world')
        lease = self.bs.lease_blob(self.container_name, 'blob1', 'acquire')

        # Act
        props = self.bs.get_blob_properties(self.container_name, 'blob1')

        # Assert
        self.assertIsNotNone(props)
        self.assertEqual(props['x-ms-blob-type'], 'BlockBlob')
        self.assertEqual(props['content-length'], '11')
        self.assertEqual(props['x-ms-lease-status'], 'locked')
        self.assertEqual(props['x-ms-lease-state'], 'leased')
        self.assertEqual(props['x-ms-lease-duration'], 'fixed')

    def test_get_blob_properties_with_non_existing_container(self):
        # Arrange

        # Act
        with self.assertRaises(WindowsAzureError):
            self.bs.get_blob_properties(self.container_name, 'blob1')

        # Assert

    def test_get_blob_properties_with_non_existing_blob(self):
        # Arrange
        self._create_container(self.container_name)

        # Act
        with self.assertRaises(WindowsAzureError):
            self.bs.get_blob_properties(self.container_name, 'blob1')

        # Assert

    def test_get_blob_metadata_with_existing_blob(self):
        # Arrange
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world')

        # Act
        md = self.bs.get_blob_metadata(self.container_name, 'blob1')

        # Assert
        self.assertIsNotNone(md)

    def test_set_blob_metadata_with_existing_blob(self):
        # Arrange
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world')

        # Act
        resp = self.bs.set_blob_metadata(
            self.container_name,
            'blob1',
            {'hello': 'world', 'number': '42', 'UP': 'UPval'})

        # Assert
        self.assertIsNone(resp)
        md = self.bs.get_blob_metadata(self.container_name, 'blob1')
        self.assertEqual(3, len(md))
        self.assertEqual(md['x-ms-meta-hello'], 'world')
        self.assertEqual(md['x-ms-meta-number'], '42')
        self.assertEqual(md['x-ms-meta-up'], 'UPval')

    def test_delete_blob_with_existing_blob(self):
        # Arrange
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world')

        # Act
        resp = self.bs.delete_blob(self.container_name, 'blob1')

        # Assert
        self.assertIsNone(resp)

    def test_delete_blob_with_non_existing_blob(self):
        # Arrange
        self._create_container(self.container_name)

        # Act
        with self.assertRaises(WindowsAzureError):
            self.bs.delete_blob (self.container_name, 'blob1')

        # Assert

    def test_delete_blob_snapshot(self):
        # Arrange
        self._create_container(self.container_name)
        blob_name = 'blob1'
        data = b'hello world'
        self.bs.put_blob(self.container_name, blob_name, data, 'BlockBlob')
        res = self.bs.snapshot_blob(self.container_name, blob_name)
        snapshot = res['x-ms-snapshot']
        blobs = self.bs.list_blobs(self.container_name, include='snapshots')
        self.assertEqual(len(blobs), 2)

        # Act
        self.bs.delete_blob(self.container_name, blob_name, snapshot=snapshot)

        # Assert
        blobs = self.bs.list_blobs(self.container_name, include='snapshots')
        self.assertEqual(len(blobs), 1)
        self.assertEqual(blobs[0].name, blob_name)
        self.assertEqual(blobs[0].snapshot, '')

    def test_copy_blob_with_existing_blob(self):
        # Arrange
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world')

        # Act
        sourceblob = '/{0}/{1}/{2}'.format(credentials.getStorageServicesName(),
                                           self.container_name,
                                           'blob1')
        resp = self.bs.copy_blob(self.container_name, 'blob1copy', sourceblob)

        # Assert
        self.assertIsNotNone(resp)
        self.assertEqual(resp['x-ms-copy-status'], 'success')
        self.assertIsNotNone(resp['x-ms-copy-id'])
        copy = self.bs.get_blob(self.container_name, 'blob1copy')
        self.assertEqual(copy, b'hello world')

    def test_copy_blob_async_public_blob(self):
        # Arrange
        self._create_container(self.container_name)
        data = b'12345678' * 1024 * 1024
        source_blob_name = 'sourceblob'
        source_blob_url = self._create_remote_container_and_block_blob(
            source_blob_name, data, 'container')

        # Act
        target_blob_name = 'targetblob'
        copy_resp = self.bs.copy_blob(
            self.container_name, target_blob_name, source_blob_url)

        # Assert
        self.assertEqual(copy_resp['x-ms-copy-status'], 'pending')
        self._wait_for_async_copy(self.container_name, target_blob_name)
        self.assertBlobEqual(self.container_name, target_blob_name, data)

    def test_copy_blob_async_private_blob(self):
        # Arrange
        self._create_container(self.container_name)
        data = b'12345678' * 1024 * 1024
        source_blob_name = 'sourceblob'
        source_blob_url = self._create_remote_container_and_block_blob(
            source_blob_name, data, None)

        # Act
        target_blob_name = 'targetblob'
        with self.assertRaises(WindowsAzureMissingResourceError):
            self.bs.copy_blob(self.container_name,
                              target_blob_name, source_blob_url)

        # Assert

    def test_copy_blob_async_private_blob_with_sas(self):
        # Arrange
        self._create_container(self.container_name)
        data = b'12345678' * 1024 * 1024
        source_blob_name = 'sourceblob'
        self._create_remote_container_and_block_blob(
            source_blob_name, data, None)
        source_blob_url = self._make_blob_sas_url(
            credentials.getRemoteStorageServicesName(),
            credentials.getRemoteStorageServicesKey(
            ),
            self.remote_container_name,
            source_blob_name)

        # Act
        target_blob_name = 'targetblob'
        copy_resp = self.bs.copy_blob(
            self.container_name, target_blob_name, source_blob_url)

        # Assert
        self.assertEqual(copy_resp['x-ms-copy-status'], 'pending')
        self._wait_for_async_copy(self.container_name, target_blob_name)
        self.assertBlobEqual(self.container_name, target_blob_name, data)

    def test_abort_copy_blob(self):
        # Arrange
        self._create_container(self.container_name)
        data = b'12345678' * 1024 * 1024
        source_blob_name = 'sourceblob'
        source_blob_url = self._create_remote_container_and_block_blob(
            source_blob_name, data, 'container')

        # Act
        target_blob_name = 'targetblob'
        copy_resp = self.bs.copy_blob(
            self.container_name, target_blob_name, source_blob_url)
        self.assertEqual(copy_resp['x-ms-copy-status'], 'pending')
        self.bs.abort_copy_blob(
            self.container_name, 'targetblob', copy_resp['x-ms-copy-id'])

        # Assert
        target_blob = self.bs.get_blob(self.container_name, target_blob_name)
        self.assertEqual(target_blob, b'')
        self.assertEqual(target_blob.properties['x-ms-copy-status'], 'aborted')

    def test_abort_copy_blob_with_synchronous_copy_fails(self):
        # Arrange
        source_blob_name = 'sourceblob'
        self._create_container_and_block_blob(
            self.container_name, source_blob_name, b'hello world')
        source_blob_url = self.bs.make_blob_url(
            self.container_name, source_blob_name)

        # Act
        target_blob_name = 'targetblob'
        copy_resp = self.bs.copy_blob(
            self.container_name, target_blob_name, source_blob_url)
        with self.assertRaises(WindowsAzureError):
            self.bs.abort_copy_blob(
                self.container_name,
                target_blob_name,
                copy_resp['x-ms-copy-id'])

        # Assert
        self.assertEqual(copy_resp['x-ms-copy-status'], 'success')

    def test_snapshot_blob(self):
        # Arrange
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world')

        # Act
        resp = self.bs.snapshot_blob(self.container_name, 'blob1')

        # Assert
        self.assertIsNotNone(resp)
        self.assertIsNotNone(resp['x-ms-snapshot'])

    def test_lease_blob_acquire_and_release(self):
        # Arrange
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world')

        # Act
        resp1 = self.bs.lease_blob(self.container_name, 'blob1', 'acquire')
        resp2 = self.bs.lease_blob(
            self.container_name, 'blob1', 'release', resp1['x-ms-lease-id'])
        resp3 = self.bs.lease_blob(self.container_name, 'blob1', 'acquire')

        # Assert
        self.assertIsNotNone(resp1)
        self.assertIsNotNone(resp2)
        self.assertIsNotNone(resp3)

    def test_lease_blob_with_duration(self):
        # Arrange
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world')

        # Act
        resp1 = self.bs.lease_blob(
            self.container_name, 'blob1', 'acquire', x_ms_lease_duration=15)
        resp2 = self.bs.put_blob(self.container_name, 'blob1', b'hello 2',
                                 'BlockBlob',
                                 x_ms_lease_id=resp1['x-ms-lease-id'])
        time.sleep(15)
        with self.assertRaises(WindowsAzureError):
            self.bs.put_blob(self.container_name, 'blob1', b'hello 3',
                             'BlockBlob', x_ms_lease_id=resp1['x-ms-lease-id'])

        # Assert
        self.assertIsNotNone(resp1)
        self.assertIsNone(resp2)

    def test_lease_blob_with_proposed_lease_id(self):
        # Arrange
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world')

        # Act
        lease_id = 'a0e6c241-96ea-45a3-a44b-6ae868bc14d0'
        resp1 = self.bs.lease_blob(
            self.container_name, 'blob1', 'acquire',
            x_ms_proposed_lease_id=lease_id)

        # Assert
        self.assertIsNotNone(resp1)
        self.assertEqual(resp1['x-ms-lease-id'], lease_id)

    def test_lease_blob_change_lease_id(self):
        # Arrange
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world')

        # Act
        lease_id = 'a0e6c241-96ea-45a3-a44b-6ae868bc14d0'
        resp1 = self.bs.lease_blob(self.container_name, 'blob1', 'acquire')
        resp2 = self.bs.lease_blob(self.container_name, 'blob1', 'change',
                                   x_ms_lease_id=resp1['x-ms-lease-id'],
                                   x_ms_proposed_lease_id=lease_id)

        # Assert
        self.assertIsNotNone(resp1)
        self.assertIsNotNone(resp2)
        self.assertNotEqual(resp1['x-ms-lease-id'], lease_id)
        self.assertEqual(resp2['x-ms-lease-id'], lease_id)

    def test_lease_blob_renew_released_lease_fails(self):
        # Arrange
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world')

        # Act
        resp1 = self.bs.lease_blob(self.container_name, 'blob1', 'acquire')
        resp2 = self.bs.lease_blob(
            self.container_name, 'blob1', 'release', resp1['x-ms-lease-id'])
        with self.assertRaises(WindowsAzureConflictError):
            self.bs.lease_blob(self.container_name, 'blob1',
                               'renew', resp1['x-ms-lease-id'])

        # Assert
        self.assertIsNotNone(resp1)
        self.assertIsNotNone(resp2)

    def test_lease_blob_break_period(self):
        # Arrange
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world')

        # Act
        resp1 = self.bs.lease_blob(self.container_name, 'blob1', 'acquire',
                                   x_ms_lease_duration=15)
        resp2 = self.bs.lease_blob(self.container_name, 'blob1',
                                   'break', resp1['x-ms-lease-id'],
                                   x_ms_lease_break_period=5)
        resp3 = self.bs.put_blob(self.container_name, 'blob1', b'hello 2',
                                 'BlockBlob',
                                 x_ms_lease_id=resp1['x-ms-lease-id'])
        time.sleep(5)
        with self.assertRaises(WindowsAzureError):
            self.bs.put_blob(self.container_name, 'blob1', b'hello 3',
                             'BlockBlob', x_ms_lease_id=resp1['x-ms-lease-id'])

        # Assert
        self.assertIsNotNone(resp1)
        self.assertIsNotNone(resp2)
        self.assertIsNone(resp3)

    def test_lease_blob_break_released_lease_fails(self):
        # Arrange
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world')
        lease = self.bs.lease_blob(self.container_name, 'blob1', 'acquire')
        self.bs.lease_blob(self.container_name, 'blob1',
                           'release', lease['x-ms-lease-id'])

        # Act
        with self.assertRaises(WindowsAzureConflictError):
            self.bs.lease_blob(self.container_name, 'blob1',
                               'break', lease['x-ms-lease-id'])

        # Assert

    def test_lease_blob_acquire_after_break_fails(self):
        # Arrange
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world')
        lease = self.bs.lease_blob(self.container_name, 'blob1', 'acquire')
        self.bs.lease_blob(self.container_name, 'blob1',
                           'break', lease['x-ms-lease-id'])

        # Act
        with self.assertRaises(WindowsAzureConflictError):
            self.bs.lease_blob(self.container_name, 'blob1', 'acquire')

        # Assert

    def test_lease_blob_acquire_and_renew(self):
        # Arrange
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world')

        # Act
        resp1 = self.bs.lease_blob(self.container_name, 'blob1', 'acquire')
        resp2 = self.bs.lease_blob(
            self.container_name, 'blob1', 'renew', resp1['x-ms-lease-id'])

        # Assert
        self.assertIsNotNone(resp1)
        self.assertIsNotNone(resp2)

    def test_lease_blob_acquire_twice_fails(self):
        # Arrange
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world')
        resp1 = self.bs.lease_blob(self.container_name, 'blob1', 'acquire')

        # Act
        with self.assertRaises(WindowsAzureError):
            self.bs.lease_blob(self.container_name, 'blob1', 'acquire')
        resp2 = self.bs.lease_blob(
            self.container_name, 'blob1', 'release', resp1['x-ms-lease-id'])

        # Assert
        self.assertIsNotNone(resp1)
        self.assertIsNotNone(resp2)

    def test_put_block(self):
        # Arrange
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'')

        # Act
        for i in range(5):
            resp = self.bs.put_block(self.container_name,
                                     'blob1',
                                     u'block {0}'.format(i).encode('utf-8'),
                                     str(i))
            self.assertIsNone(resp)

        # Assert

    def test_put_block_unicode_python_27(self):
        '''Test for auto-encoding of unicode text (backwards compatibility).'''
        if sys.version_info >= (3,):
            return

        # Arrange
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'')

        # Act
        resp = self.bs.put_block(self.container_name, 'blob1', u'啊齄', '1')
        self.assertIsNone(resp)
        resp = self.bs.put_block(self.container_name, 'blob1', u'丂狛狜', '2')
        self.assertIsNone(resp)
        resp = self.bs.put_block_list(self.container_name, 'blob1', ['1', '2'])
        self.assertIsNone(resp)

        # Assert
        blob = self.bs.get_blob(self.container_name, 'blob1')
        self.assertEqual(blob, u'啊齄丂狛狜'.encode('utf-8'))

    def test_put_block_unicode_python_33(self):
        if sys.version_info < (3,):
            return

        # Arrange
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'')

        # Act
        with self.assertRaises(TypeError):
            resp = self.bs.put_block(self.container_name, 'blob1', u'啊齄', '1')

        # Assert

    def test_put_block_list(self):
        # Arrange
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'')
        self.bs.put_block(self.container_name, 'blob1', b'AAA', '1')
        self.bs.put_block(self.container_name, 'blob1', b'BBB', '2')
        self.bs.put_block(self.container_name, 'blob1', b'CCC', '3')

        # Act
        resp = self.bs.put_block_list(
            self.container_name, 'blob1', ['1', '2', '3'])

        # Assert
        self.assertIsNone(resp)
        blob = self.bs.get_blob(self.container_name, 'blob1')
        self.assertEqual(blob, b'AAABBBCCC')

    def test_get_block_list_no_blocks(self):
        # Arrange
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'')

        # Act
        block_list = self.bs.get_block_list(
            self.container_name, 'blob1', None, 'all')

        # Assert
        self.assertIsNotNone(block_list)
        self.assertIsInstance(block_list, BlobBlockList)
        self.assertEqual(len(block_list.uncommitted_blocks), 0)
        self.assertEqual(len(block_list.committed_blocks), 0)

    def test_get_block_list_uncommitted_blocks(self):
        # Arrange
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'')
        self.bs.put_block(self.container_name, 'blob1', b'AAA', '1')
        self.bs.put_block(self.container_name, 'blob1', b'BBB', '2')
        self.bs.put_block(self.container_name, 'blob1', b'CCC', '3')

        # Act
        block_list = self.bs.get_block_list(
            self.container_name, 'blob1', None, 'all')

        # Assert
        self.assertIsNotNone(block_list)
        self.assertIsInstance(block_list, BlobBlockList)
        self.assertEqual(len(block_list.uncommitted_blocks), 3)
        self.assertEqual(len(block_list.committed_blocks), 0)

    def test_get_block_list_committed_blocks(self):
        # Arrange
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'')
        self.bs.put_block(self.container_name, 'blob1', b'AAA', '1')
        self.bs.put_block(self.container_name, 'blob1', b'BBB', '2')
        self.bs.put_block(self.container_name, 'blob1', b'CCC', '3')
        self.bs.put_block_list(self.container_name, 'blob1', ['1', '2', '3'])

        # Act
        block_list = self.bs.get_block_list(
            self.container_name, 'blob1', None, 'all')

        # Assert
        self.assertIsNotNone(block_list)
        self.assertIsInstance(block_list, BlobBlockList)
        self.assertEqual(len(block_list.uncommitted_blocks), 0)
        self.assertEqual(len(block_list.committed_blocks), 3)

    def test_put_page_update(self):
        # Arrange
        self._create_container_and_page_blob(
            self.container_name, 'blob1', 1024)

        # Act
        data = b'abcdefghijklmnop' * 32
        resp = self.bs.put_page(
            self.container_name, 'blob1', data, 'bytes=0-511', 'update')

        # Assert
        self.assertIsNone(resp)

    def test_put_page_clear(self):
        # Arrange
        self._create_container_and_page_blob(
            self.container_name, 'blob1', 1024)

        # Act
        resp = self.bs.put_page(
            self.container_name, 'blob1', b'', 'bytes=0-511', 'clear')

        # Assert
        self.assertIsNone(resp)

    def test_put_page_if_sequence_number_lt_success(self):
        # Arrange
        self._create_container(self.container_name)
        data = b'ab' * 256
        start_sequence = 10
        self.bs.put_blob(self.container_name, 'blob1', None, 'PageBlob',
                         x_ms_blob_content_length=512,
                         x_ms_blob_sequence_number=start_sequence)

        # Act
        self.bs.put_page(self.container_name, 'blob1', data, 'bytes=0-511',
                         'update',
                         x_ms_if_sequence_number_lt=start_sequence + 1)

        # Assert
        self.assertBlobEqual(self.container_name, 'blob1', data)

    def test_put_page_if_sequence_number_lt_failure(self):
        # Arrange
        self._create_container(self.container_name)
        data = b'ab' * 256
        start_sequence = 10
        self.bs.put_blob(self.container_name, 'blob1', None, 'PageBlob',
                         x_ms_blob_content_length=512,
                         x_ms_blob_sequence_number=start_sequence)

        # Act
        with self.assertRaises(WindowsAzureError):
            self.bs.put_page(self.container_name, 'blob1', data, 'bytes=0-511',
                             'update',
                             x_ms_if_sequence_number_lt=start_sequence)

        # Assert

    def test_put_page_if_sequence_number_lte_success(self):
        # Arrange
        self._create_container(self.container_name)
        data = b'ab' * 256
        start_sequence = 10
        self.bs.put_blob(self.container_name, 'blob1', None, 'PageBlob',
                         x_ms_blob_content_length=512,
                         x_ms_blob_sequence_number=start_sequence)

        # Act
        self.bs.put_page(self.container_name, 'blob1', data, 'bytes=0-511',
                         'update', x_ms_if_sequence_number_lte=start_sequence)

        # Assert
        self.assertBlobEqual(self.container_name, 'blob1', data)

    def test_put_page_if_sequence_number_lte_failure(self):
        # Arrange
        self._create_container(self.container_name)
        data = b'ab' * 256
        start_sequence = 10
        self.bs.put_blob(self.container_name, 'blob1', None, 'PageBlob',
                         x_ms_blob_content_length=512,
                         x_ms_blob_sequence_number=start_sequence)

        # Act
        with self.assertRaises(WindowsAzureError):
            self.bs.put_page(self.container_name, 'blob1', data, 'bytes=0-511',
                             'update',
                             x_ms_if_sequence_number_lte=start_sequence - 1)

        # Assert

    def test_put_page_if_sequence_number_eq_success(self):
        # Arrange
        self._create_container(self.container_name)
        data = b'ab' * 256
        start_sequence = 10
        self.bs.put_blob(self.container_name, 'blob1', None, 'PageBlob',
                         x_ms_blob_content_length=512,
                         x_ms_blob_sequence_number=start_sequence)

        # Act
        self.bs.put_page(self.container_name, 'blob1', data, 'bytes=0-511',
                         'update', x_ms_if_sequence_number_eq=start_sequence)

        # Assert
        self.assertBlobEqual(self.container_name, 'blob1', data)

    def test_put_page_if_sequence_number_eq_failure(self):
        # Arrange
        self._create_container(self.container_name)
        data = b'ab' * 256
        start_sequence = 10
        self.bs.put_blob(self.container_name, 'blob1', None, 'PageBlob',
                         x_ms_blob_content_length=512,
                         x_ms_blob_sequence_number=start_sequence)

        # Act
        with self.assertRaises(WindowsAzureError):
            self.bs.put_page(self.container_name, 'blob1', data, 'bytes=0-511',
                             'update',
                             x_ms_if_sequence_number_eq=start_sequence - 1)

        # Assert

    def test_put_page_unicode_python_27(self):
        '''Test for auto-encoding of unicode text (backwards compatibility).'''
        if sys.version_info >= (3,):
            return

        # Arrange
        self._create_container_and_page_blob(self.container_name, 'blob1', 512)

        # Act
        data = u'abcdefghijklmnop' * 32
        resp = self.bs.put_page(
            self.container_name, 'blob1', data, 'bytes=0-511', 'update')

        # Assert
        self.assertIsNone(resp)
        blob = self.bs.get_blob(self.container_name, 'blob1')
        self.assertEqual(blob, data.encode('utf-8'))

    def test_put_page_unicode_python_33(self):
        '''Test for auto-encoding of unicode text (backwards compatibility).'''
        if sys.version_info < (3,):
            return

        # Arrange
        self._create_container_and_page_blob(self.container_name, 'blob1', 512)

        # Act
        data = u'abcdefghijklmnop' * 32
        with self.assertRaises(TypeError):
            self.bs.put_page(self.container_name, 'blob1',
                             data, 'bytes=0-511', 'update')

        # Assert

    def test_get_page_ranges_no_pages(self):
        # Arrange
        self._create_container_and_page_blob(
            self.container_name, 'blob1', 1024)

        # Act
        ranges = self.bs.get_page_ranges(self.container_name, 'blob1')

        # Assert
        self.assertIsNotNone(ranges)
        self.assertIsInstance(ranges, PageList)
        self.assertEqual(len(ranges.page_ranges), 0)

    def test_get_page_ranges_2_pages(self):
        # Arrange
        self._create_container_and_page_blob(
            self.container_name, 'blob1', 2048)
        data = b'abcdefghijklmnop' * 32
        resp1 = self.bs.put_page(
            self.container_name, 'blob1', data, 'bytes=0-511', 'update')
        resp2 = self.bs.put_page(
            self.container_name, 'blob1', data, 'bytes=1024-1535', 'update')

        # Act
        ranges = self.bs.get_page_ranges(self.container_name, 'blob1')

        # Assert
        self.assertIsNotNone(ranges)
        self.assertIsInstance(ranges, PageList)
        self.assertEqual(len(ranges.page_ranges), 2)
        self.assertEqual(ranges.page_ranges[0].start, 0)
        self.assertEqual(ranges.page_ranges[0].end, 511)
        self.assertEqual(ranges.page_ranges[1].start, 1024)
        self.assertEqual(ranges.page_ranges[1].end, 1535)

    def test_get_page_ranges_iter(self):
        # Arrange
        self._create_container_and_page_blob(
            self.container_name, 'blob1', 2048)
        data = b'abcdefghijklmnop' * 32
        resp1 = self.bs.put_page(
            self.container_name, 'blob1', data, 'bytes=0-511', 'update')
        resp2 = self.bs.put_page(
            self.container_name, 'blob1', data, 'bytes=1024-1535', 'update')

        # Act
        ranges = self.bs.get_page_ranges(self.container_name, 'blob1')
        for range in ranges:
            pass

        # Assert
        self.assertEqual(len(ranges), 2)
        self.assertIsInstance(ranges[0], PageRange)
        self.assertIsInstance(ranges[1], PageRange)

    def test_with_filter(self):
        # Single filter
        if sys.version_info < (3,):
            strtype = (str, unicode)
            strornonetype = (str, unicode, type(None))
        else:
            strtype = str
            strornonetype = (str, type(None))

        called = []

        def my_filter(request, next):
            called.append(True)
            self.assertIsInstance(request, HTTPRequest)
            for header in request.headers:
                self.assertIsInstance(header, tuple)
                for item in header:
                    self.assertIsInstance(item, strornonetype)
            self.assertIsInstance(request.host, strtype)
            self.assertIsInstance(request.method, strtype)
            self.assertIsInstance(request.path, strtype)
            self.assertIsInstance(request.query, list)
            self.assertIsInstance(request.body, strtype)
            response = next(request)

            self.assertIsInstance(response, HTTPResponse)
            self.assertIsInstance(response.body, (bytes, type(None)))
            self.assertIsInstance(response.headers, list)
            for header in response.headers:
                self.assertIsInstance(header, tuple)
                for item in header:
                    self.assertIsInstance(item, strtype)
            self.assertIsInstance(response.status, int)
            return response

        bc = self.bs.with_filter(my_filter)
        bc.create_container(self.container_name + '0', None, None, False)

        self.assertTrue(called)

        del called[:]

        bc.delete_container(self.container_name + '0')

        self.assertTrue(called)
        del called[:]

        # Chained filters
        def filter_a(request, next):
            called.append('a')
            return next(request)

        def filter_b(request, next):
            called.append('b')
            return next(request)

        bc = self.bs.with_filter(filter_a).with_filter(filter_b)
        bc.create_container(self.container_name + '1', None, None, False)

        self.assertEqual(called, ['b', 'a'])

        bc.delete_container(self.container_name + '1')

        self.assertEqual(called, ['b', 'a', 'b', 'a'])

    def test_unicode_create_container_unicode_name(self):
        # Arrange
        self.container_name = self.container_name + u'啊齄丂狛狜'

        # Act
        with self.assertRaises(WindowsAzureError):
            # not supported - container name must be alphanumeric, lowercase
            self.bs.create_container(self.container_name)

        # Assert

    def test_unicode_get_blob_unicode_name(self):
        # Arrange
        self._create_container_and_block_blob(
            self.container_name, '啊齄丂狛狜', b'hello world')

        # Act
        blob = self.bs.get_blob(self.container_name, '啊齄丂狛狜')

        # Assert
        self.assertIsInstance(blob, BlobResult)
        self.assertEqual(blob, b'hello world')

    def test_put_blob_block_blob_unicode_data(self):
        # Arrange
        self._create_container(self.container_name)

        # Act
        data = u'hello world啊齄丂狛狜'.encode('utf-8')
        resp = self.bs.put_blob(
            self.container_name, 'blob1', data, 'BlockBlob')

        # Assert
        self.assertIsNone(resp)

    def test_unicode_get_blob_unicode_data(self):
        # Arrange
        blob_data = u'hello world啊齄丂狛狜'.encode('utf-8')
        self._create_container_and_block_blob(
            self.container_name, 'blob1', blob_data)

        # Act
        blob = self.bs.get_blob(self.container_name, 'blob1')

        # Assert
        self.assertIsInstance(blob, BlobResult)
        self.assertEqual(blob, blob_data)

    def test_unicode_get_blob_binary_data(self):
        # Arrange
        base64_data = 'AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8gISIjJCUmJygpKissLS4vMDEyMzQ1Njc4OTo7PD0+P0BBQkNERUZHSElKS0xNTk9QUVJTVFVWV1hZWltcXV5fYGFiY2RlZmdoaWprbG1ub3BxcnN0dXZ3eHl6e3x9fn+AgYKDhIWGh4iJiouMjY6PkJGSk5SVlpeYmZqbnJ2en6ChoqOkpaanqKmqq6ytrq+wsbKztLW2t7i5uru8vb6/wMHCw8TFxsfIycrLzM3Oz9DR0tPU1dbX2Nna29zd3t/g4eLj5OXm5+jp6uvs7e7v8PHy8/T19vf4+fr7/P3+/wABAgMEBQYHCAkKCwwNDg8QERITFBUWFxgZGhscHR4fICEiIyQlJicoKSorLC0uLzAxMjM0NTY3ODk6Ozw9Pj9AQUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVpbXF1eX2BhYmNkZWZnaGlqa2xtbm9wcXJzdHV2d3h5ent8fX5/gIGCg4SFhoeIiYqLjI2Oj5CRkpOUlZaXmJmam5ydnp+goaKjpKWmp6ipqqusra6vsLGys7S1tre4ubq7vL2+v8DBwsPExcbHyMnKy8zNzs/Q0dLT1NXW19jZ2tvc3d7f4OHi4+Tl5ufo6err7O3u7/Dx8vP09fb3+Pn6+/z9/v8AAQIDBAUGBwgJCgsMDQ4PEBESExQVFhcYGRobHB0eHyAhIiMkJSYnKCkqKywtLi8wMTIzNDU2Nzg5Ojs8PT4/QEFCQ0RFRkdISUpLTE1OT1BRUlNUVVZXWFlaW1xdXl9gYWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXp7fH1+f4CBgoOEhYaHiImKi4yNjo+QkZKTlJWWl5iZmpucnZ6foKGio6SlpqeoqaqrrK2ur7CxsrO0tba3uLm6u7y9vr/AwcLDxMXGx8jJysvMzc7P0NHS09TV1tfY2drb3N3e3+Dh4uPk5ebn6Onq6+zt7u/w8fLz9PX29/j5+vv8/f7/AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8gISIjJCUmJygpKissLS4vMDEyMzQ1Njc4OTo7PD0+P0BBQkNERUZHSElKS0xNTk9QUVJTVFVWV1hZWltcXV5fYGFiY2RlZmdoaWprbG1ub3BxcnN0dXZ3eHl6e3x9fn+AgYKDhIWGh4iJiouMjY6PkJGSk5SVlpeYmZqbnJ2en6ChoqOkpaanqKmqq6ytrq+wsbKztLW2t7i5uru8vb6/wMHCw8TFxsfIycrLzM3Oz9DR0tPU1dbX2Nna29zd3t/g4eLj5OXm5+jp6uvs7e7v8PHy8/T19vf4+fr7/P3+/w=='
        binary_data = base64.b64decode(base64_data)

        self._create_container_and_block_blob(
            self.container_name, 'blob1', binary_data)

        # Act
        blob = self.bs.get_blob(self.container_name, 'blob1')

        # Assert
        self.assertIsInstance(blob, BlobResult)
        self.assertEqual(blob, binary_data)

    def test_no_sas_private_blob(self):
        # Arrange
        data = b'a private blob cannot be read without a shared access signature'
        self._create_container_and_block_blob(
            self.container_name, 'blob1.txt', data)
        res_path = self.container_name + '/blob1.txt'

        # Act
        host = credentials.getStorageServicesName() + BLOB_SERVICE_HOST_BASE
        url = '/' + res_path
        respbody = self._get_request(host, url)

        # Assert
        self.assertNotEqual(data, respbody)
        self.assertNotEqual(-1, respbody.decode('utf-8')
                            .find('ResourceNotFound'))

    def test_no_sas_public_blob(self):
        # Arrange
        data = b'a public blob can be read without a shared access signature'
        self.bs.create_container(self.container_name, None, 'blob')
        self.bs.put_blob(self.container_name, 'blob1.txt', data, 'BlockBlob')
        res_path = self.container_name + '/blob1.txt'

        # Act
        host = credentials.getStorageServicesName() + BLOB_SERVICE_HOST_BASE
        url = '/' + res_path
        respbody = self._get_request(host, url)

        # Assert
        self.assertEqual(data, respbody)

    def test_shared_read_access_blob(self):
        # Arrange
        data = b'shared access signature with read permission on blob'
        self._create_container_and_block_blob(
            self.container_name, 'blob1.txt', data)
        sas = SharedAccessSignature(credentials.getStorageServicesName(),
                                    credentials.getStorageServicesKey())
        res_path = self.container_name + '/blob1.txt'
        res_type = RESOURCE_BLOB

        # Act
        sas.permission_set = [
            self._get_permission(sas, res_type, res_path, 'r')]
        web_rsrc = self._get_signed_web_resource(sas, res_type, res_path, 'r')
        host = credentials.getStorageServicesName() + BLOB_SERVICE_HOST_BASE
        url = web_rsrc.request_url
        respbody = self._get_request(host, url)

        # Assert
        self.assertEqual(data, respbody)

    def test_shared_write_access_blob(self):
        # Arrange
        data = b'shared access signature with write permission on blob'
        updated_data = b'updated blob data'
        self._create_container_and_block_blob(
            self.container_name, 'blob1.txt', data)
        sas = SharedAccessSignature(credentials.getStorageServicesName(),
                                    credentials.getStorageServicesKey())
        res_path = self.container_name + '/blob1.txt'
        res_type = RESOURCE_BLOB

        # Act
        sas.permission_set = [
            self._get_permission(sas, res_type, res_path, 'w')]
        web_rsrc = self._get_signed_web_resource(sas, res_type, res_path, 'w')
        host = credentials.getStorageServicesName() + BLOB_SERVICE_HOST_BASE
        url = web_rsrc.request_url
        headers = {'x-ms-blob-type': 'BlockBlob'}
        respbody = self._put_request(host, url, updated_data, headers)

        # Assert
        blob = self.bs.get_blob(self.container_name, 'blob1.txt')
        self.assertEqual(updated_data, blob)

    def test_shared_delete_access_blob(self):
        # Arrange
        data = b'shared access signature with delete permission on blob'
        self._create_container_and_block_blob(
            self.container_name, 'blob1.txt', data)
        sas = SharedAccessSignature(credentials.getStorageServicesName(),
                                    credentials.getStorageServicesKey())
        res_path = self.container_name + '/blob1.txt'
        res_type = RESOURCE_BLOB

        # Act
        sas.permission_set = [
            self._get_permission(sas, res_type, res_path, 'd')]
        web_rsrc = self._get_signed_web_resource(sas, res_type, res_path, 'd')
        host = credentials.getStorageServicesName() + BLOB_SERVICE_HOST_BASE
        url = web_rsrc.request_url
        respbody = self._del_request(host, url)

        # Assert
        with self.assertRaises(WindowsAzureError):
            blob = self.bs.get_blob(self.container_name, 'blob1.txt')

    def test_shared_access_container(self):
        # Arrange
        data = b'shared access signature with read permission on container'
        self._create_container_and_block_blob(
            self.container_name, 'blob1.txt', data)
        sas = SharedAccessSignature(credentials.getStorageServicesName(),
                                    credentials.getStorageServicesKey())
        res_path = self.container_name
        res_type = RESOURCE_CONTAINER

        # Act
        sas.permission_set = [
            self._get_permission(sas, res_type, res_path, 'r')]
        web_rsrc = self._get_signed_web_resource(
            sas, res_type, res_path + '/blob1.txt', 'r')
        host = credentials.getStorageServicesName() + BLOB_SERVICE_HOST_BASE
        url = web_rsrc.request_url
        respbody = self._get_request(host, url)

        # Assert
        self.assertEqual(data, respbody)

    def test_get_blob_to_bytes(self):
        # Arrange
        blob_name = 'blob1'
        data = b'abcdefghijklmnopqrstuvwxyz'
        self._create_container_and_block_blob(
            self.container_name, blob_name, data)

        # Act
        resp = self.bs.get_blob_to_bytes(self.container_name, blob_name)

        # Assert
        self.assertEqual(data, resp)

    def test_get_blob_to_bytes_chunked_download(self):
        # Arrange
        blob_name = 'blob1'
        data = self._get_oversized_binary_data()
        self._create_container_and_block_blob(
            self.container_name, blob_name, data)

        # Act
        resp = self.bs.get_blob_to_bytes(self.container_name, blob_name)

        # Assert
        self.assertEqual(data, resp)

    def test_get_blob_to_bytes_with_progress(self):
        # Arrange
        blob_name = 'blob1'
        data = b'abcdefghijklmnopqrstuvwxyz'
        self._create_container_and_block_blob(
            self.container_name, blob_name, data)

        # Act
        progress = []

        def callback(current, total):
            progress.append((current, total))

        resp = self.bs.get_blob_to_bytes(
            self.container_name, blob_name, progress_callback=callback)

        # Assert
        self.assertEqual(data, resp)
        self.assertEqual(progress, self._get_expected_progress(len(data)))

    def test_get_blob_to_bytes_with_progress_chunked_download(self):
        # Arrange
        blob_name = 'blob1'
        data = self._get_oversized_binary_data()
        self._create_container_and_block_blob(
            self.container_name, blob_name, data)

        # Act
        progress = []

        def callback(current, total):
            progress.append((current, total))

        resp = self.bs.get_blob_to_bytes(
            self.container_name, blob_name, progress_callback=callback)

        # Assert
        self.assertEqual(data, resp)
        self.assertEqual(progress, self._get_expected_progress(len(data)))

    def test_get_blob_to_file(self):
        # Arrange
        blob_name = 'blob1'
        data = b'abcdefghijklmnopqrstuvwxyz'
        file_path = 'blob_output.temp.dat'
        self._create_container_and_block_blob(
            self.container_name, blob_name, data)

        # Act
        with open(file_path, 'wb') as stream:
            resp = self.bs.get_blob_to_file(
                self.container_name, blob_name, stream)

        # Assert
        self.assertIsNone(resp)
        with open(file_path, 'rb') as stream:
            actual = stream.read()
            self.assertEqual(data, actual)

    def test_get_blob_to_file_chunked_download(self):
        # Arrange
        blob_name = 'blob1'
        data = self._get_oversized_binary_data()
        file_path = 'blob_output.temp.dat'
        self._create_container_and_block_blob(
            self.container_name, blob_name, data)

        # Act
        with open(file_path, 'wb') as stream:
            resp = self.bs.get_blob_to_file(
                self.container_name, blob_name, stream)

        # Assert
        self.assertIsNone(resp)
        with open(file_path, 'rb') as stream:
            actual = stream.read()
            self.assertEqual(data, actual)

    def test_get_blob_to_file_with_progress(self):
        # Arrange
        blob_name = 'blob1'
        data = b'abcdefghijklmnopqrstuvwxyz'
        file_path = 'blob_output.temp.dat'
        self._create_container_and_block_blob(
            self.container_name, blob_name, data)

        # Act
        progress = []

        def callback(current, total):
            progress.append((current, total))

        with open(file_path, 'wb') as stream:
            resp = self.bs.get_blob_to_file(
                self.container_name, blob_name, stream,
                progress_callback=callback)

        # Assert
        self.assertIsNone(resp)
        with open(file_path, 'rb') as stream:
            actual = stream.read()
            self.assertEqual(data, actual)
        self.assertEqual(progress, self._get_expected_progress(len(data)))

    def test_get_blob_to_file_with_progress_chunked_download(self):
        # Arrange
        blob_name = 'blob1'
        data = self._get_oversized_binary_data()
        file_path = 'blob_output.temp.dat'
        self._create_container_and_block_blob(
            self.container_name, blob_name, data)

        # Act
        progress = []

        def callback(current, total):
            progress.append((current, total))

        with open(file_path, 'wb') as stream:
            resp = self.bs.get_blob_to_file(
                self.container_name, blob_name, stream,
                progress_callback=callback)

        # Assert
        self.assertIsNone(resp)
        with open(file_path, 'rb') as stream:
            actual = stream.read()
            self.assertEqual(data, actual)
        self.assertEqual(progress, self._get_expected_progress(len(data)))

    def test_get_blob_to_path(self):
        # Arrange
        blob_name = 'blob1'
        data = b'abcdefghijklmnopqrstuvwxyz'
        file_path = 'blob_output.temp.dat'
        self._create_container_and_block_blob(
            self.container_name, blob_name, data)

        # Act
        resp = self.bs.get_blob_to_path(
            self.container_name, blob_name, file_path)

        # Assert
        self.assertIsNone(resp)
        with open(file_path, 'rb') as stream:
            actual = stream.read()
            self.assertEqual(data, actual)

    def test_get_blob_to_path_chunked_downlad(self):
        # Arrange
        blob_name = 'blob1'
        data = self._get_oversized_binary_data()
        file_path = 'blob_output.temp.dat'
        self._create_container_and_block_blob(
            self.container_name, blob_name, data)

        # Act
        resp = self.bs.get_blob_to_path(
            self.container_name, blob_name, file_path)

        # Assert
        self.assertIsNone(resp)
        with open(file_path, 'rb') as stream:
            actual = stream.read()
            self.assertEqual(data, actual)

    def test_get_blob_to_path_with_progress(self):
        # Arrange
        blob_name = 'blob1'
        data = b'abcdefghijklmnopqrstuvwxyz'
        file_path = 'blob_output.temp.dat'
        self._create_container_and_block_blob(
            self.container_name, blob_name, data)

        # Act
        progress = []

        def callback(current, total):
            progress.append((current, total))

        resp = self.bs.get_blob_to_path(
            self.container_name, blob_name, file_path,
            progress_callback=callback)

        # Assert
        self.assertIsNone(resp)
        with open(file_path, 'rb') as stream:
            actual = stream.read()
            self.assertEqual(data, actual)
        self.assertEqual(progress, self._get_expected_progress(len(data)))

    def test_get_blob_to_path_with_progress_chunked_downlad(self):
        # Arrange
        blob_name = 'blob1'
        data = self._get_oversized_binary_data()
        file_path = 'blob_output.temp.dat'
        self._create_container_and_block_blob(
            self.container_name, blob_name, data)

        # Act
        progress = []

        def callback(current, total):
            progress.append((current, total))

        resp = self.bs.get_blob_to_path(
            self.container_name, blob_name, file_path,
            progress_callback=callback)

        # Assert
        self.assertIsNone(resp)
        with open(file_path, 'rb') as stream:
            actual = stream.read()
            self.assertEqual(data, actual)
        self.assertEqual(progress, self._get_expected_progress(len(data)))

    def test_get_blob_to_path_with_mode(self):
        # Arrange
        blob_name = 'blob1'
        data = b'abcdefghijklmnopqrstuvwxyz'
        file_path = 'blob_output.temp.dat'
        self._create_container_and_block_blob(
            self.container_name, blob_name, data)
        with open(file_path, 'wb') as stream:
            stream.write(b'abcdef')

        # Act
        resp = self.bs.get_blob_to_path(
            self.container_name, blob_name, file_path, 'a+b')

        # Assert
        self.assertIsNone(resp)
        with open(file_path, 'rb') as stream:
            actual = stream.read()
            self.assertEqual(b'abcdef' + data, actual)

    def test_get_blob_to_path_with_mode_chunked_download(self):
        # Arrange
        blob_name = 'blob1'
        data = self._get_oversized_binary_data()
        file_path = 'blob_output.temp.dat'
        self._create_container_and_block_blob(
            self.container_name, blob_name, data)
        with open(file_path, 'wb') as stream:
            stream.write(b'abcdef')

        # Act
        resp = self.bs.get_blob_to_path(
            self.container_name, blob_name, file_path, 'a+b')

        # Assert
        self.assertIsNone(resp)
        with open(file_path, 'rb') as stream:
            actual = stream.read()
            self.assertEqual(b'abcdef' + data, actual)

    def test_get_blob_to_text(self):
        # Arrange
        blob_name = 'blob1'
        text = u'hello 啊齄丂狛狜 world'
        data = text.encode('utf-8')
        self._create_container_and_block_blob(
            self.container_name, blob_name, data)

        # Act
        resp = self.bs.get_blob_to_text(self.container_name, blob_name)

        # Assert
        self.assertEqual(text, resp)

    def test_get_blob_to_text_with_encoding(self):
        # Arrange
        blob_name = 'blob1'
        text = u'hello 啊齄丂狛狜 world'
        data = text.encode('utf-16')
        self._create_container_and_block_blob(
            self.container_name, blob_name, data)

        # Act
        resp = self.bs.get_blob_to_text(
            self.container_name, blob_name, 'utf-16')

        # Assert
        self.assertEqual(text, resp)

    def test_get_blob_to_text_chunked_download(self):
        # Arrange
        blob_name = 'blob1'
        text = self._get_oversized_text_data()
        data = text.encode('utf-8')
        self._create_container_and_block_blob(
            self.container_name, blob_name, data)

        # Act
        resp = self.bs.get_blob_to_text(self.container_name, blob_name)

        # Assert
        self.assertEqual(text, resp)

    def test_get_blob_to_text_with_progress(self):
        # Arrange
        blob_name = 'blob1'
        text = u'hello 啊齄丂狛狜 world'
        data = text.encode('utf-8')
        self._create_container_and_block_blob(
            self.container_name, blob_name, data)

        # Act
        progress = []

        def callback(current, total):
            progress.append((current, total))

        resp = self.bs.get_blob_to_text(
            self.container_name, blob_name, progress_callback=callback)

        # Assert
        self.assertEqual(text, resp)
        self.assertEqual(progress, self._get_expected_progress(len(data)))

    def test_get_blob_to_text_with_encoding_and_progress(self):
        # Arrange
        blob_name = 'blob1'
        text = u'hello 啊齄丂狛狜 world'
        data = text.encode('utf-16')
        self._create_container_and_block_blob(
            self.container_name, blob_name, data)

        # Act
        progress = []

        def callback(current, total):
            progress.append((current, total))

        resp = self.bs.get_blob_to_text(
            self.container_name, blob_name, 'utf-16',
            progress_callback=callback)

        # Assert
        self.assertEqual(text, resp)
        self.assertEqual(progress, self._get_expected_progress(len(data)))

    def test_put_block_blob_from_bytes(self):
        # Arrange
        self._create_container(self.container_name)

        # Act
        data = b'abcdefghijklmnopqrstuvwxyz'
        resp = self.bs.put_block_blob_from_bytes(
            self.container_name, 'blob1', data)

        # Assert
        self.assertIsNone(resp)
        self.assertEqual(data, self.bs.get_blob(self.container_name, 'blob1'))

    def test_put_block_blob_from_bytes_with_progress(self):
        # Arrange
        self._create_container(self.container_name)
        data = b'abcdefghijklmnopqrstuvwxyz'

        # Act
        progress = []

        def callback(current, total):
            progress.append((current, total))

        resp = self.bs.put_block_blob_from_bytes(
            self.container_name, 'blob1', data, progress_callback=callback)

        # Assert
        self.assertIsNone(resp)
        self.assertEqual(data, self.bs.get_blob(self.container_name, 'blob1'))
        self.assertEqual(progress, self._get_expected_progress(len(data)))

    def test_put_block_blob_from_bytes_with_index(self):
        # Arrange
        self._create_container(self.container_name)

        # Act
        data = b'abcdefghijklmnopqrstuvwxyz'
        resp = self.bs.put_block_blob_from_bytes(
            self.container_name, 'blob1', data, 3)

        # Assert
        self.assertIsNone(resp)
        self.assertEqual(b'defghijklmnopqrstuvwxyz',
                         self.bs.get_blob(self.container_name, 'blob1'))

    def test_put_block_blob_from_bytes_with_index_and_count(self):
        # Arrange
        self._create_container(self.container_name)

        # Act
        data = b'abcdefghijklmnopqrstuvwxyz'
        resp = self.bs.put_block_blob_from_bytes(
            self.container_name, 'blob1', data, 3, 5)

        # Assert
        self.assertIsNone(resp)
        self.assertEqual(
            b'defgh', self.bs.get_blob(self.container_name, 'blob1'))

    def test_put_block_blob_from_bytes_chunked_upload(self):
        # Arrange
        self._create_container(self.container_name)
        blob_name = 'blob1'
        data = self._get_oversized_binary_data()

        # Act
        resp = self.bs.put_block_blob_from_bytes(
            self.container_name, blob_name, data)

        # Assert
        self.assertIsNone(resp)
        self.assertBlobLengthEqual(self.container_name, blob_name, len(data))
        self.assertBlobEqual(self.container_name, blob_name, data)

    def test_put_block_blob_from_bytes_with_progress_chunked_upload(self):
        # Arrange
        self._create_container(self.container_name)
        blob_name = 'blob1'
        data = self._get_oversized_binary_data()

        # Act
        progress = []

        def callback(current, total):
            progress.append((current, total))

        resp = self.bs.put_block_blob_from_bytes(
            self.container_name, blob_name, data, progress_callback=callback)

        # Assert
        self.assertIsNone(resp)
        self.assertBlobLengthEqual(self.container_name, blob_name, len(data))
        self.assertBlobEqual(self.container_name, blob_name, data)
        self.assertEqual(progress, self._get_expected_progress(len(data)))

    def test_put_block_blob_from_bytes_chunked_upload_with_index_and_count(self):
        # Arrange
        self._create_container(self.container_name)
        blob_name = 'blob1'
        data = self._get_oversized_binary_data()
        index = 33
        blob_size = len(data) - 66

        # Act
        resp = self.bs.put_block_blob_from_bytes(
            self.container_name, blob_name, data, index, blob_size)

        # Assert
        self.assertIsNone(resp)
        self.assertBlobLengthEqual(self.container_name, blob_name, blob_size)
        self.assertBlobEqual(self.container_name, blob_name,
                             data[index:index + blob_size])

    def test_put_block_blob_from_path_chunked_upload(self):
        # Arrange
        self._create_container(self.container_name)
        blob_name = 'blob1'
        data = self._get_oversized_binary_data()
        file_path = 'blob_input.temp.dat'
        with open(file_path, 'wb') as stream:
            stream.write(data)

        # Act
        resp = self.bs.put_block_blob_from_path(
            self.container_name, blob_name, file_path)

        # Assert
        self.assertIsNone(resp)
        self.assertBlobLengthEqual(self.container_name, blob_name, len(data))
        self.assertBlobEqual(self.container_name, blob_name, data)

    def test_put_block_blob_from_path_with_progress_chunked_upload(self):
        # Arrange
        self._create_container(self.container_name)
        blob_name = 'blob1'
        data = self._get_oversized_binary_data()
        file_path = 'blob_input.temp.dat'
        with open(file_path, 'wb') as stream:
            stream.write(data)

        # Act
        progress = []

        def callback(current, total):
            progress.append((current, total))

        resp = self.bs.put_block_blob_from_path(
            self.container_name, blob_name, file_path,
            progress_callback=callback)

        # Assert
        self.assertIsNone(resp)
        self.assertBlobLengthEqual(self.container_name, blob_name, len(data))
        self.assertBlobEqual(self.container_name, blob_name, data)
        self.assertEqual(progress, self._get_expected_progress(len(data)))

    def test_put_block_blob_from_file_chunked_upload(self):
        # Arrange
        self._create_container(self.container_name)
        blob_name = 'blob1'
        data = self._get_oversized_binary_data()
        file_path = 'blob_input.temp.dat'
        with open(file_path, 'wb') as stream:
            stream.write(data)

        # Act
        with open(file_path, 'rb') as stream:
            resp = self.bs.put_block_blob_from_file(
                self.container_name, blob_name, stream)

        # Assert
        self.assertIsNone(resp)
        self.assertBlobLengthEqual(self.container_name, blob_name, len(data))
        self.assertBlobEqual(self.container_name, blob_name, data)

    def test_put_block_blob_from_file_with_progress_chunked_upload(self):
        # Arrange
        self._create_container(self.container_name)
        blob_name = 'blob1'
        data = self._get_oversized_binary_data()
        file_path = 'blob_input.temp.dat'
        with open(file_path, 'wb') as stream:
            stream.write(data)

        # Act
        progress = []

        def callback(current, total):
            progress.append((current, total))

        with open(file_path, 'rb') as stream:
            resp = self.bs.put_block_blob_from_file(
                self.container_name, blob_name, stream,
                progress_callback=callback)

        # Assert
        self.assertIsNone(resp)
        self.assertBlobLengthEqual(self.container_name, blob_name, len(data))
        self.assertBlobEqual(self.container_name, blob_name, data)
        self.assertEqual(
            progress,
            self._get_expected_progress(len(data), unknown_size=True))

    def test_put_block_blob_from_file_chunked_upload_with_count(self):
        # Arrange
        self._create_container(self.container_name)
        blob_name = 'blob1'
        data = self._get_oversized_binary_data()
        file_path = 'blob_input.temp.dat'
        with open(file_path, 'wb') as stream:
            stream.write(data)

        # Act
        blob_size = len(data) - 301
        with open(file_path, 'rb') as stream:
            resp = self.bs.put_block_blob_from_file(
                self.container_name, blob_name, stream, blob_size)

        # Assert
        self.assertIsNone(resp)
        self.assertBlobLengthEqual(self.container_name, blob_name, blob_size)
        self.assertBlobEqual(self.container_name, blob_name, data[:blob_size])

    def test_put_block_blob_from_text(self):
        # Arrange
        self._create_container(self.container_name)
        blob_name = 'blob1'
        text = u'hello 啊齄丂狛狜 world'
        data = text.encode('utf-8')

        # Act
        resp = self.bs.put_block_blob_from_text(
            self.container_name, blob_name, text)

        # Assert
        self.assertIsNone(resp)
        self.assertBlobLengthEqual(self.container_name, blob_name, len(data))
        self.assertBlobEqual(self.container_name, blob_name, data)

    def test_put_block_blob_from_text_with_encoding(self):
        # Arrange
        self._create_container(self.container_name)
        blob_name = 'blob1'
        text = u'hello 啊齄丂狛狜 world'
        data = text.encode('utf-16')

        # Act
        resp = self.bs.put_block_blob_from_text(
            self.container_name, blob_name, text, 'utf-16')

        # Assert
        self.assertIsNone(resp)
        self.assertBlobLengthEqual(self.container_name, blob_name, len(data))
        self.assertBlobEqual(self.container_name, blob_name, data)

    def test_put_block_blob_from_text_with_encoding_and_progress(self):
        # Arrange
        self._create_container(self.container_name)
        blob_name = 'blob1'
        text = u'hello 啊齄丂狛狜 world'
        data = text.encode('utf-16')

        # Act
        progress = []

        def callback(current, total):
            progress.append((current, total))

        resp = self.bs.put_block_blob_from_text(
            self.container_name, blob_name, text, 'utf-16',
            progress_callback=callback)

        # Assert
        self.assertIsNone(resp)
        self.assertBlobLengthEqual(self.container_name, blob_name, len(data))
        self.assertBlobEqual(self.container_name, blob_name, data)
        self.assertEqual(progress, self._get_expected_progress(len(data)))

    def test_put_block_blob_from_text_chunked_upload(self):
        # Arrange
        self._create_container(self.container_name)
        blob_name = 'blob1'
        data = self._get_oversized_text_data()
        encoded_data = data.encode('utf-8')

        # Act
        resp = self.bs.put_block_blob_from_text(
            self.container_name, blob_name, data)

        # Assert
        self.assertIsNone(resp)
        self.assertBlobLengthEqual(
            self.container_name, blob_name, len(encoded_data))
        self.assertBlobEqual(self.container_name, blob_name, encoded_data)

    def test_put_page_blob_from_bytes(self):
        # Arrange
        self._create_container(self.container_name)

        # Act
        data = os.urandom(2048)
        resp = self.bs.put_page_blob_from_bytes(
            self.container_name, 'blob1', data)

        # Assert
        self.assertIsNone(resp)
        self.assertEqual(data, self.bs.get_blob(self.container_name, 'blob1'))

    def test_put_page_blob_from_bytes_with_progress(self):
        # Arrange
        self._create_container(self.container_name)

        # Act
        progress = []

        def callback(current, total):
            progress.append((current, total))

        data = os.urandom(2048)
        resp = self.bs.put_page_blob_from_bytes(
            self.container_name, 'blob1', data, progress_callback=callback)

        # Assert
        self.assertIsNone(resp)
        self.assertEqual(data, self.bs.get_blob(self.container_name, 'blob1'))
        self.assertEqual(progress, self._get_expected_progress(len(data)))

    def test_put_page_blob_from_bytes_with_index(self):
        # Arrange
        self._create_container(self.container_name)
        index = 1024

        # Act
        data = os.urandom(2048)
        resp = self.bs.put_page_blob_from_bytes(
            self.container_name, 'blob1', data, index)

        # Assert
        self.assertIsNone(resp)
        self.assertEqual(data[index:],
                         self.bs.get_blob(self.container_name, 'blob1'))

    def test_put_page_blob_from_bytes_with_index_and_count(self):
        # Arrange
        self._create_container(self.container_name)
        index = 512
        count = 1024

        # Act
        data = os.urandom(2048)
        resp = self.bs.put_page_blob_from_bytes(
            self.container_name, 'blob1', data, index, count)

        # Assert
        self.assertIsNone(resp)
        self.assertEqual(data[index:index + count],
                         self.bs.get_blob(self.container_name, 'blob1'))

    def test_put_page_blob_from_bytes_chunked_upload(self):
        # Arrange
        self._create_container(self.container_name)
        blob_name = 'blob1'
        data = self._get_oversized_page_blob_binary_data()

        # Act
        resp = self.bs.put_page_blob_from_bytes(
            self.container_name, blob_name, data)

        # Assert
        self.assertIsNone(resp)
        self.assertBlobLengthEqual(self.container_name, blob_name, len(data))
        self.assertBlobEqual(self.container_name, blob_name, data)

    def test_put_page_blob_from_bytes_chunked_upload_with_index_and_count(self):
        # Arrange
        self._create_container(self.container_name)
        blob_name = 'blob1'
        data = self._get_oversized_page_blob_binary_data()
        index = 512
        count = len(data) - 1024

        # Act
        resp = self.bs.put_page_blob_from_bytes(
            self.container_name, blob_name, data, index, count)

        # Assert
        self.assertIsNone(resp)
        self.assertBlobLengthEqual(self.container_name, blob_name, count)
        self.assertBlobEqual(self.container_name,
                             blob_name, data[index:index + count])

    def test_put_page_blob_from_path_chunked_upload(self):
        # Arrange
        self._create_container(self.container_name)
        blob_name = 'blob1'
        data = self._get_oversized_page_blob_binary_data()
        file_path = 'blob_input.temp.dat'
        with open(file_path, 'wb') as stream:
            stream.write(data)

        # Act
        resp = self.bs.put_page_blob_from_path(
            self.container_name, blob_name, file_path)

        # Assert
        self.assertIsNone(resp)
        self.assertBlobLengthEqual(self.container_name, blob_name, len(data))
        self.assertBlobEqual(self.container_name, blob_name, data)

    def test_put_page_blob_from_path_with_progress_chunked_upload(self):
        # Arrange
        self._create_container(self.container_name)
        blob_name = 'blob1'
        data = self._get_oversized_page_blob_binary_data()
        file_path = 'blob_input.temp.dat'
        with open(file_path, 'wb') as stream:
            stream.write(data)

        # Act
        progress = []

        def callback(current, total):
            progress.append((current, total))

        resp = self.bs.put_page_blob_from_path(
            self.container_name, blob_name, file_path,
            progress_callback=callback)

        # Assert
        self.assertIsNone(resp)
        self.assertBlobLengthEqual(self.container_name, blob_name, len(data))
        self.assertBlobEqual(self.container_name, blob_name, data)
        self.assertEqual(progress, self._get_expected_progress(len(data)))

    def test_put_page_blob_from_file_chunked_upload(self):
        # Arrange
        self._create_container(self.container_name)
        blob_name = 'blob1'
        data = self._get_oversized_page_blob_binary_data()
        file_path = 'blob_input.temp.dat'
        with open(file_path, 'wb') as stream:
            stream.write(data)

        # Act
        blob_size = len(data)
        with open(file_path, 'rb') as stream:
            resp = self.bs.put_page_blob_from_file(
                self.container_name, blob_name, stream, blob_size)

        # Assert
        self.assertIsNone(resp)
        self.assertBlobLengthEqual(self.container_name, blob_name, blob_size)
        self.assertBlobEqual(self.container_name, blob_name, data[:blob_size])

    def test_put_page_blob_from_file_with_progress_chunked_upload(self):
        # Arrange
        self._create_container(self.container_name)
        blob_name = 'blob1'
        data = self._get_oversized_page_blob_binary_data()
        file_path = 'blob_input.temp.dat'
        with open(file_path, 'wb') as stream:
            stream.write(data)

        # Act
        progress = []

        def callback(current, total):
            progress.append((current, total))

        blob_size = len(data)
        with open(file_path, 'rb') as stream:
            resp = self.bs.put_page_blob_from_file(
                self.container_name, blob_name, stream, blob_size,
                progress_callback=callback)

        # Assert
        self.assertIsNone(resp)
        self.assertBlobLengthEqual(self.container_name, blob_name, blob_size)
        self.assertBlobEqual(self.container_name, blob_name, data[:blob_size])
        self.assertEqual(progress, self._get_expected_progress(len(data)))

    def test_put_page_blob_from_file_chunked_upload_truncated(self):
        # Arrange
        self._create_container(self.container_name)
        blob_name = 'blob1'
        data = self._get_oversized_page_blob_binary_data()
        file_path = 'blob_input.temp.dat'
        with open(file_path, 'wb') as stream:
            stream.write(data)

        # Act
        blob_size = len(data) - 512
        with open(file_path, 'rb') as stream:
            resp = self.bs.put_page_blob_from_file(
                self.container_name, blob_name, stream, blob_size)

        # Assert
        self.assertIsNone(resp)
        self.assertBlobLengthEqual(self.container_name, blob_name, blob_size)
        self.assertBlobEqual(self.container_name, blob_name, data[:blob_size])

    def test_put_page_blob_from_file_with_progress_chunked_upload_truncated(self):
        # Arrange
        self._create_container(self.container_name)
        blob_name = 'blob1'
        data = self._get_oversized_page_blob_binary_data()
        file_path = 'blob_input.temp.dat'
        with open(file_path, 'wb') as stream:
            stream.write(data)

        # Act
        progress = []

        def callback(current, total):
            progress.append((current, total))

        blob_size = len(data) - 512
        with open(file_path, 'rb') as stream:
            resp = self.bs.put_page_blob_from_file(
                self.container_name, blob_name, stream, blob_size,
                progress_callback=callback)

        # Assert
        self.assertIsNone(resp)
        self.assertBlobLengthEqual(self.container_name, blob_name, blob_size)
        self.assertBlobEqual(self.container_name, blob_name, data[:blob_size])
        self.assertEqual(progress, self._get_expected_progress(blob_size))

#------------------------------------------------------------------------------
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_cloudstorageaccount
#-------------------------------------------------------------------------
# Copyright (c) Microsoft.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#--------------------------------------------------------------------------
import unittest

from azure import WindowsAzureError
from azure.storage import (
    BlobService,
    CloudStorageAccount,
    QueueService,
    TableService,
    )
from util import (
    AzureTestCase,
    credentials,
    getUniqueName,
    )

#------------------------------------------------------------------------------


class CloudStorageAccountTest(AzureTestCase):

    def setUp(self):
        self.account = CloudStorageAccount(
            account_name=credentials.getStorageServicesName(),
            account_key=credentials.getStorageServicesKey())

    #--Test cases --------------------------------------------------------
    def test_create_blob_service(self):
        # Arrange

        # Act
        service = self.account.create_blob_service()

        # Assert
        self.assertIsNotNone(service)
        self.assertIsInstance(service, BlobService)
        self.assertEqual(service.account_name,
                         credentials.getStorageServicesName())
        self.assertEqual(service.account_key,
                         credentials.getStorageServicesKey())

    def test_create_blob_service_empty_credentials(self):
        # Arrange

        # Act
        bad_account = CloudStorageAccount('', '')
        with self.assertRaises(WindowsAzureError):
            service = bad_account.create_blob_service()

        # Assert

    def test_create_table_service(self):
        # Arrange

        # Act
        service = self.account.create_table_service()

        # Assert
        self.assertIsNotNone(service)
        self.assertIsInstance(service, TableService)
        self.assertEqual(service.account_name,
                         credentials.getStorageServicesName())
        self.assertEqual(service.account_key,
                         credentials.getStorageServicesKey())

    def test_create_queue_service(self):
        # Arrange

        # Act
        service = self.account.create_queue_service()

        # Assert
        self.assertIsNotNone(service)
        self.assertIsInstance(service, QueueService)
        self.assertEqual(service.account_name,
                         credentials.getStorageServicesName())
        self.assertEqual(service.account_key,
                         credentials.getStorageServicesKey())

#------------------------------------------------------------------------------
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_managementcertificatemanagementservice
﻿#-------------------------------------------------------------------------
# Copyright (c) Microsoft.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#--------------------------------------------------------------------------
import unittest

from azure.servicemanagement import ServiceManagementService
from util import (
    AzureTestCase,
    credentials,
    getUniqueName,
    set_service_options,
    )

MANAGEMENT_CERT_PUBLICKEY = 'MIIBCgKCAQEAsjULNM53WPLkht1rbrDob/e4hZTHzj/hlLoBt2X3cNRc6dOPsMucxbMdchbCqAFa5RIaJvF5NDKqZuUSwq6bttD71twzy9bQ03EySOcRBad1VyqAZQ8DL8nUGSnXIUh+tpz4fDGM5f3Ly9NX8zfGqG3sT635rrFlUp3meJC+secCCwTLOOcIs3KQmuB+pMB5Y9rPhoxcekFfpq1pKtis6pmxnVbiL49kr6UUL6RQRDwik4t1jttatXLZqHETTmXl0Y0wS5AcJUXVAn5AL2kybULoThop2v01/E0NkPtFPAqLVs/kKBahniNn9uwUo+LS9FA8rWGu0FY4CZEYDfhb+QIDAQAB'
MANAGEMENT_CERT_DATA = 'MIIC9jCCAeKgAwIBAgIQ00IFaqV9VqVJxI+wZka0szAJBgUrDgMCHQUAMBUxEzARBgNVBAMTClB5dGhvblRlc3QwHhcNMTIwODMwMDAyNTMzWhcNMzkxMjMxMjM1OTU5WjAVMRMwEQYDVQQDEwpQeXRob25UZXN0MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAsjULNM53WPLkht1rbrDob/e4hZTHzj/hlLoBt2X3cNRc6dOPsMucxbMdchbCqAFa5RIaJvF5NDKqZuUSwq6bttD71twzy9bQ03EySOcRBad1VyqAZQ8DL8nUGSnXIUh+tpz4fDGM5f3Ly9NX8zfGqG3sT635rrFlUp3meJC+secCCwTLOOcIs3KQmuB+pMB5Y9rPhoxcekFfpq1pKtis6pmxnVbiL49kr6UUL6RQRDwik4t1jttatXLZqHETTmXl0Y0wS5AcJUXVAn5AL2kybULoThop2v01/E0NkPtFPAqLVs/kKBahniNn9uwUo+LS9FA8rWGu0FY4CZEYDfhb+QIDAQABo0owSDBGBgNVHQEEPzA9gBBS6knRHo54LppngxVCCzZVoRcwFTETMBEGA1UEAxMKUHl0aG9uVGVzdIIQ00IFaqV9VqVJxI+wZka0szAJBgUrDgMCHQUAA4IBAQAnZbP3YV+08wI4YTg6MOVA+j1njd0kVp35FLehripmaMNE6lgk3Vu1MGGl0JnvMr3fNFGFzRske/jVtFxlHE5H/CoUzmyMQ+W06eV/e995AduwTKsS0ZgYn0VoocSXWst/nyhpKOcbJgAOohOYxgsGI1JEqQgjyeqzcCIhw/vlWiA3V8bSiPnrC9vwhH0eB025hBd2VbEGDz2nWCYkwtuOLMTvkmLi/oFw3GOfgagZKk8k/ZPffMCafz+yR3vb1nqAjncrVcJLI8amUfpxhjZYexo8MbxBA432M6w8sjXN+uLCl7ByWZ4xs4vonWgkmjeObtU37SIzolHT4dxIgaP2'
MANAGEMENT_CERT_THUMBRINT = 'BEA4B74BD6B915E9DD6A01FB1B8C3C1740F517F2'

#------------------------------------------------------------------------------


class ManagementCertificateManagementServiceTest(AzureTestCase):

    def setUp(self):
        self.sms = ServiceManagementService(credentials.getSubscriptionId(),
                                            credentials.getManagementCertFile())
        set_service_options(self.sms)

        self.certificate_thumbprints = []

    def tearDown(self):
        for thumbprint in self.certificate_thumbprints:
            try:
                self.sms.delete_management_certificate(thumbprint)
            except:
                pass

    #--Helpers-----------------------------------------------------------------
    def _create_management_certificate(self, cert):
        self.certificate_thumbprints.append(cert.thumbprint)
        result = self.sms.add_management_certificate(cert.public_key,
                                                     cert.thumbprint,
                                                     cert.data)
        self.assertIsNone(result)

    def _management_certificate_exists(self, thumbprint):
        try:
            props = self.sms.get_management_certificate(thumbprint)
            return props is not None
        except:
            return False

    #--Test cases for management certificates ----------------------------
    def test_list_management_certificates(self):
        # Arrange
        local_cert = _local_certificate()
        self._create_management_certificate(local_cert)

        # Act
        result = self.sms.list_management_certificates()

        # Assert
        self.assertIsNotNone(result)
        self.assertTrue(len(result) > 0)

        cert = None
        for temp in result:
            if temp.subscription_certificate_thumbprint == \
                local_cert.thumbprint:
                cert = temp
                break

        self.assertIsNotNone(cert)
        self.assertIsNotNone(cert.created)
        self.assertEqual(cert.subscription_certificate_public_key,
                         local_cert.public_key)
        self.assertEqual(cert.subscription_certificate_data, local_cert.data)
        self.assertEqual(cert.subscription_certificate_thumbprint,
                         local_cert.thumbprint)

    def test_get_management_certificate(self):
        # Arrange
        local_cert = _local_certificate()
        self._create_management_certificate(local_cert)

        # Act
        result = self.sms.get_management_certificate(local_cert.thumbprint)

        # Assert
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.created)
        self.assertEqual(result.subscription_certificate_public_key,
                         local_cert.public_key)
        self.assertEqual(result.subscription_certificate_data, local_cert.data)
        self.assertEqual(result.subscription_certificate_thumbprint,
                         local_cert.thumbprint)

    def test_add_management_certificate(self):
        # Arrange
        local_cert = _local_certificate()

        # Act
        self.certificate_thumbprints.append(local_cert.thumbprint)
        result = self.sms.add_management_certificate(local_cert.public_key,
                                                     local_cert.thumbprint,
                                                     local_cert.data)

        # Assert
        self.assertIsNone(result)
        self.assertTrue(
            self._management_certificate_exists(local_cert.thumbprint))

    def test_delete_management_certificate(self):
        # Arrange
        local_cert = _local_certificate()
        self._create_management_certificate(local_cert)

        # Act
        result = self.sms.delete_management_certificate(local_cert.thumbprint)

        # Assert
        self.assertIsNone(result)
        self.assertFalse(
            self._management_certificate_exists(local_cert.thumbprint))


class LocalCertificate(object):

    def __init__(self, thumbprint='', data='', public_key=''):
        self.thumbprint = thumbprint
        self.data = data
        self.public_key = public_key


def _local_certificate():
    # It would be nice to dynamically create this data, so that it is unique
    # But for now, we always create the same certificate
    return LocalCertificate(MANAGEMENT_CERT_THUMBRINT,
                            MANAGEMENT_CERT_DATA,
                            MANAGEMENT_CERT_PUBLICKEY)

#------------------------------------------------------------------------------
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_queueservice
﻿# coding: utf-8

#-------------------------------------------------------------------------
# Copyright (c) Microsoft.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#--------------------------------------------------------------------------
import unittest

from azure import WindowsAzureError
from azure.storage.queueservice import QueueService
from util import (
    AzureTestCase,
    credentials,
    getUniqueName,
    set_service_options,
    )

#------------------------------------------------------------------------------
TEST_QUEUE_PREFIX = 'mytestqueue'
#------------------------------------------------------------------------------


class QueueServiceTest(AzureTestCase):

    def setUp(self):
        self.qs = QueueService(credentials.getStorageServicesName(),
                               credentials.getStorageServicesKey())
        set_service_options(self.qs)

        self.test_queues = []
        self.creatable_queues = []
        for i in range(10):
            self.test_queues.append(getUniqueName(TEST_QUEUE_PREFIX + str(i)))
        for i in range(4):
            self.creatable_queues.append(
                getUniqueName('mycreatablequeue' + str(i)))
        for queue_name in self.test_queues:
            self.qs.create_queue(queue_name)

    def tearDown(self):
        self.cleanup()
        return super(QueueServiceTest, self).tearDown()

    def cleanup(self):
        for queue_name in self.test_queues:
            try:
                self.qs.delete_queue(queue_name)
            except:
                pass
        for queue_name in self.creatable_queues:
            try:
                self.qs.delete_queue(queue_name)
            except:
                pass

    def test_get_service_properties(self):
        # This api doesn't apply to local storage
        if self.qs.use_local_storage:
            return

        # Action
        properties = self.qs.get_queue_service_properties()

        # Asserts
        self.assertIsNotNone(properties)
        self.assertIsNotNone(properties.logging)
        self.assertIsNotNone(properties.logging.retention_policy)
        self.assertIsNotNone(properties.logging.version)
        self.assertIsNotNone(properties.metrics)
        self.assertIsNotNone(properties.metrics.retention_policy)
        self.assertIsNotNone(properties.metrics.version)

    def test_set_service_properties(self):
        # This api doesn't apply to local storage
        if self.qs.use_local_storage:
            return

        # Action
        queue_properties = self.qs.get_queue_service_properties()
        queue_properties.logging.read = True
        self.qs.set_queue_service_properties(queue_properties)
        properties = self.qs.get_queue_service_properties()

        # Asserts
        self.assertIsNotNone(properties)
        self.assertIsNotNone(properties.logging)
        self.assertIsNotNone(properties.logging.retention_policy)
        self.assertIsNotNone(properties.logging.version)
        self.assertIsNotNone(properties.metrics)
        self.assertIsNotNone(properties.metrics.retention_policy)
        self.assertIsNotNone(properties.metrics.version)
        self.assertTrue(properties.logging.read)

    def test_create_queue(self):
        # Action
        self.qs.create_queue(self.creatable_queues[0])
        result = self.qs.get_queue_metadata(self.creatable_queues[0])
        self.qs.delete_queue(self.creatable_queues[0])

        # Asserts
        self.assertIsNotNone(result)
        self.assertEqual(result['x-ms-approximate-messages-count'], '0')

    def test_create_queue_already_exist(self):
        # Action
        created1 = self.qs.create_queue(self.creatable_queues[0])
        created2 = self.qs.create_queue(self.creatable_queues[0])

        # Asserts
        self.assertTrue(created1)
        self.assertFalse(created2)

    def test_create_queue_fail_on_exist(self):
        # Action
        created = self.qs.create_queue(self.creatable_queues[0], None, True)
        with self.assertRaises(WindowsAzureError):
            self.qs.create_queue(self.creatable_queues[0], None, True)

        # Asserts
        self.assertTrue(created)

    def test_create_queue_with_options(self):
        # Action
        self.qs.create_queue(
            self.creatable_queues[1],
            x_ms_meta_name_values={'val1': 'test', 'val2': 'blah'})
        result = self.qs.get_queue_metadata(self.creatable_queues[1])

        # Asserts
        self.assertIsNotNone(result)
        self.assertEqual(3, len(result))
        self.assertEqual(result['x-ms-approximate-messages-count'], '0')
        self.assertEqual('test', result['x-ms-meta-val1'])
        self.assertEqual('blah', result['x-ms-meta-val2'])

    def test_delete_queue_not_exist(self):
        # Action
        deleted = self.qs.delete_queue(self.creatable_queues[0])

        # Asserts
        self.assertFalse(deleted)

    def test_delete_queue_fail_not_exist_not_exist(self):
        # Action
        with self.assertRaises(WindowsAzureError):
            self.qs.delete_queue(self.creatable_queues[0], True)

        # Asserts

    def test_delete_queue_fail_not_exist_already_exist(self):
        # Action
        created = self.qs.create_queue(self.creatable_queues[0])
        deleted = self.qs.delete_queue(self.creatable_queues[0], True)

        # Asserts
        self.assertTrue(created)
        self.assertTrue(deleted)

    def test_list_queues(self):
        # Action
        queues = self.qs.list_queues()
        for queue in queues:
            pass

        # Asserts
        self.assertIsNotNone(queues)
        self.assertEqual('', queues.marker)
        self.assertEqual(0, queues.max_results)
        self.assertTrue(len(self.test_queues) <= len(queues))

    def test_list_queues_with_options(self):
        # Action
        queues_1 = self.qs.list_queues(prefix=TEST_QUEUE_PREFIX, maxresults=3)
        queues_2 = self.qs.list_queues(
            prefix=TEST_QUEUE_PREFIX,
            marker=queues_1.next_marker,
            include='metadata')

        # Asserts
        self.assertIsNotNone(queues_1)
        self.assertEqual(3, len(queues_1))
        self.assertEqual(3, queues_1.max_results)
        self.assertEqual('', queues_1.marker)
        self.assertIsNotNone(queues_1[0])
        self.assertIsNone(queues_1[0].metadata)
        self.assertNotEqual('', queues_1[0].name)
        self.assertNotEqual('', queues_1[0].url)
        # Asserts
        self.assertIsNotNone(queues_2)
        self.assertTrue(len(self.test_queues) - 3 <= len(queues_2))
        self.assertEqual(0, queues_2.max_results)
        self.assertEqual(queues_1.next_marker, queues_2.marker)
        self.assertIsNotNone(queues_2[0])
        self.assertIsNotNone(queues_2[0].metadata)
        self.assertNotEqual('', queues_2[0].name)
        self.assertNotEqual('', queues_2[0].url)

    def test_set_queue_metadata(self):
        # Action
        self.qs.create_queue(self.creatable_queues[2])
        self.qs.set_queue_metadata(
            self.creatable_queues[2],
            x_ms_meta_name_values={'val1': 'test', 'val2': 'blah'})
        result = self.qs.get_queue_metadata(self.creatable_queues[2])
        self.qs.delete_queue(self.creatable_queues[2])

        # Asserts
        self.assertIsNotNone(result)
        self.assertEqual(3, len(result))
        self.assertEqual('0', result['x-ms-approximate-messages-count'])
        self.assertEqual('test', result['x-ms-meta-val1'])
        self.assertEqual('blah', result['x-ms-meta-val2'])

    def test_put_message(self):
        # Action.  No exception means pass. No asserts needed.
        self.qs.put_message(self.test_queues[0], 'message1')
        self.qs.put_message(self.test_queues[0], 'message2')
        self.qs.put_message(self.test_queues[0], 'message3')
        self.qs.put_message(self.test_queues[0], 'message4')

    def test_get_messages(self):
        # Action
        self.qs.put_message(self.test_queues[1], 'message1')
        self.qs.put_message(self.test_queues[1], 'message2')
        self.qs.put_message(self.test_queues[1], 'message3')
        self.qs.put_message(self.test_queues[1], 'message4')
        result = self.qs.get_messages(self.test_queues[1])

        # Asserts
        self.assertIsNotNone(result)
        self.assertEqual(1, len(result))
        message = result[0]
        self.assertIsNotNone(message)
        self.assertNotEqual('', message.message_id)
        self.assertEqual('message1', message.message_text)
        self.assertNotEqual('', message.pop_receipt)
        self.assertEqual('1', message.dequeue_count)
        self.assertNotEqual('', message.insertion_time)
        self.assertNotEqual('', message.expiration_time)
        self.assertNotEqual('', message.time_next_visible)

    def test_get_messages_with_options(self):
        # Action
        self.qs.put_message(self.test_queues[2], 'message1')
        self.qs.put_message(self.test_queues[2], 'message2')
        self.qs.put_message(self.test_queues[2], 'message3')
        self.qs.put_message(self.test_queues[2], 'message4')
        result = self.qs.get_messages(
            self.test_queues[2], numofmessages=4, visibilitytimeout=20)

        # Asserts
        self.assertIsNotNone(result)
        self.assertEqual(4, len(result))

        for message in result:
            self.assertIsNotNone(message)
            self.assertNotEqual('', message.message_id)
            self.assertNotEqual('', message.message_text)
            self.assertNotEqual('', message.pop_receipt)
            self.assertEqual('1', message.dequeue_count)
            self.assertNotEqual('', message.insertion_time)
            self.assertNotEqual('', message.expiration_time)
            self.assertNotEqual('', message.time_next_visible)

    def test_peek_messages(self):
        # Action
        self.qs.put_message(self.test_queues[3], 'message1')
        self.qs.put_message(self.test_queues[3], 'message2')
        self.qs.put_message(self.test_queues[3], 'message3')
        self.qs.put_message(self.test_queues[3], 'message4')
        result = self.qs.peek_messages(self.test_queues[3])

        # Asserts
        self.assertIsNotNone(result)
        self.assertEqual(1, len(result))
        message = result[0]
        self.assertIsNotNone(message)
        self.assertNotEqual('', message.message_id)
        self.assertNotEqual('', message.message_text)
        self.assertEqual('', message.pop_receipt)
        self.assertEqual('0', message.dequeue_count)
        self.assertNotEqual('', message.insertion_time)
        self.assertNotEqual('', message.expiration_time)
        self.assertEqual('', message.time_next_visible)

    def test_peek_messages_with_options(self):
        # Action
        self.qs.put_message(self.test_queues[4], 'message1')
        self.qs.put_message(self.test_queues[4], 'message2')
        self.qs.put_message(self.test_queues[4], 'message3')
        self.qs.put_message(self.test_queues[4], 'message4')
        result = self.qs.peek_messages(self.test_queues[4], numofmessages=4)

        # Asserts
        self.assertIsNotNone(result)
        self.assertEqual(4, len(result))
        for message in result:
            self.assertIsNotNone(message)
            self.assertNotEqual('', message.message_id)
            self.assertNotEqual('', message.message_text)
            self.assertEqual('', message.pop_receipt)
            self.assertEqual('0', message.dequeue_count)
            self.assertNotEqual('', message.insertion_time)
            self.assertNotEqual('', message.expiration_time)
            self.assertEqual('', message.time_next_visible)

    def test_clear_messages(self):
        # Action
        self.qs.put_message(self.test_queues[5], 'message1')
        self.qs.put_message(self.test_queues[5], 'message2')
        self.qs.put_message(self.test_queues[5], 'message3')
        self.qs.put_message(self.test_queues[5], 'message4')
        self.qs.clear_messages(self.test_queues[5])
        result = self.qs.peek_messages(self.test_queues[5])

        # Asserts
        self.assertIsNotNone(result)
        self.assertEqual(0, len(result))

    def test_delete_message(self):
        # Action
        self.qs.put_message(self.test_queues[6], 'message1')
        self.qs.put_message(self.test_queues[6], 'message2')
        self.qs.put_message(self.test_queues[6], 'message3')
        self.qs.put_message(self.test_queues[6], 'message4')
        result = self.qs.get_messages(self.test_queues[6])
        self.qs.delete_message(
            self.test_queues[6], result[0].message_id, result[0].pop_receipt)
        result2 = self.qs.get_messages(self.test_queues[6], numofmessages=32)

        # Asserts
        self.assertIsNotNone(result2)
        self.assertEqual(3, len(result2))

    def test_update_message(self):
        # Action
        self.qs.put_message(self.test_queues[7], 'message1')
        list_result1 = self.qs.get_messages(self.test_queues[7])
        self.qs.update_message(self.test_queues[7],
                               list_result1[0].message_id,
                               'new text',
                               list_result1[0].pop_receipt,
                               visibilitytimeout=0)
        list_result2 = self.qs.get_messages(self.test_queues[7])

        # Asserts
        self.assertIsNotNone(list_result2)
        message = list_result2[0]
        self.assertIsNotNone(message)
        self.assertNotEqual('', message.message_id)
        self.assertEqual('new text', message.message_text)
        self.assertNotEqual('', message.pop_receipt)
        self.assertEqual('2', message.dequeue_count)
        self.assertNotEqual('', message.insertion_time)
        self.assertNotEqual('', message.expiration_time)
        self.assertNotEqual('', message.time_next_visible)

    def test_with_filter(self):
        # Single filter
        called = []

        def my_filter(request, next):
            called.append(True)
            return next(request)
        qc = self.qs.with_filter(my_filter)
        qc.put_message(self.test_queues[7], 'message1')

        self.assertTrue(called)

        del called[:]

        # Chained filters
        def filter_a(request, next):
            called.append('a')
            return next(request)

        def filter_b(request, next):
            called.append('b')
            return next(request)

        qc = self.qs.with_filter(filter_a).with_filter(filter_b)
        qc.put_message(self.test_queues[7], 'message1')

        self.assertEqual(called, ['b', 'a'])

    def test_unicode_create_queue_unicode_name(self):
        # Action
        self.creatable_queues[0] = u'啊齄丂狛狜'

        with self.assertRaises(WindowsAzureError):
            # not supported - queue name must be alphanumeric, lowercase
            self.qs.create_queue(self.creatable_queues[0])

        # Asserts

    def test_unicode_get_messages_unicode_data(self):
        # Action
        self.qs.put_message(self.test_queues[1], u'message1㚈')
        result = self.qs.get_messages(self.test_queues[1])

        # Asserts
        self.assertIsNotNone(result)
        self.assertEqual(1, len(result))
        message = result[0]
        self.assertIsNotNone(message)
        self.assertNotEqual('', message.message_id)
        self.assertEqual(u'message1㚈', message.message_text)
        self.assertNotEqual('', message.pop_receipt)
        self.assertEqual('1', message.dequeue_count)
        self.assertNotEqual('', message.insertion_time)
        self.assertNotEqual('', message.expiration_time)
        self.assertNotEqual('', message.time_next_visible)

    def test_unicode_update_message_unicode_data(self):
        # Action
        self.qs.put_message(self.test_queues[7], 'message1')
        list_result1 = self.qs.get_messages(self.test_queues[7])
        self.qs.update_message(self.test_queues[7],
                               list_result1[0].message_id,
                               u'啊齄丂狛狜',
                               list_result1[0].pop_receipt,
                               visibilitytimeout=0)
        list_result2 = self.qs.get_messages(self.test_queues[7])

        # Asserts
        self.assertIsNotNone(list_result2)
        message = list_result2[0]
        self.assertIsNotNone(message)
        self.assertNotEqual('', message.message_id)
        self.assertEqual(u'啊齄丂狛狜', message.message_text)
        self.assertNotEqual('', message.pop_receipt)
        self.assertEqual('2', message.dequeue_count)
        self.assertNotEqual('', message.insertion_time)
        self.assertNotEqual('', message.expiration_time)
        self.assertNotEqual('', message.time_next_visible)

#------------------------------------------------------------------------------
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_servicebusmanagementservice
#-------------------------------------------------------------------------
# Copyright (c) Microsoft.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#--------------------------------------------------------------------------
import time
import unittest

from azure import (
    WindowsAzureError,
    WindowsAzureMissingResourceError,
    )
from azure.servicemanagement import ServiceBusManagementService
from util import (
    AzureTestCase,
    credentials,
    getUniqueName,
    set_service_options,
    )

#------------------------------------------------------------------------------


class ServiceBusManagementServiceTest(AzureTestCase):

    def setUp(self):
        self.sms = ServiceBusManagementService(
            credentials.getSubscriptionId(),
            credentials.getManagementCertFile())
        set_service_options(self.sms)

        self.sb_namespace = getUniqueName('uts')

    def tearDown(self):
        try:
            self.sms.delete_namespace(self.sb_namespace)
        except:
            pass

    #--Helpers-----------------------------------------------------------------
    def _namespace_exists(self, name):
        try:
            ns = self.sms.get_namespace(name)
            # treat it as non-existent if it is in process of being removed
            return ns.status != 'Removing'
        except:
            return False

    def _wait_for_namespace_active(self, name):
        count = 0
        ns = self.sms.get_namespace(name)
        while ns.status != 'Active':
            count = count + 1
            if count > 120:
                self.assertTrue(
                    False,
                    'Timed out waiting for service bus namespace activation.')
            time.sleep(5)
            ns = self.sms.get_namespace(name)

    #--Operations for service bus ----------------------------------------
    def test_get_regions(self):
        # Arrange

        # Act
        result = self.sms.get_regions()

        # Assert
        self.assertIsNotNone(result)
        self.assertTrue(len(result) > 0)
        for region in result:
            self.assertTrue(len(region.code) > 0)
            self.assertTrue(len(region.fullname) > 0)

    def test_list_namespaces(self):
        # Arrange

        # Act
        result = self.sms.list_namespaces()

        # Assert
        self.assertIsNotNone(result)
        self.assertTrue(len(result) > 0)
        for ns in result:
            self.assertTrue(len(ns.name) > 0)
            self.assertTrue(len(ns.region) > 0)

    def test_get_namespace(self):
        # Arrange
        name = credentials.getServiceBusNamespace()

        # Act
        result = self.sms.get_namespace(name)

        # Assert
        self.assertIsNotNone(result)
        self.assertEqual(result.name, name)
        self.assertIsNotNone(result.region)
        self.assertIsNotNone(result.default_key)
        self.assertIsNotNone(result.status)
        self.assertIsNotNone(result.created_at)
        self.assertIsNotNone(result.acs_management_endpoint)
        self.assertIsNotNone(result.servicebus_endpoint)
        self.assertIsNotNone(result.connection_string)
        self.assertEqual(result.subscription_id,
                         credentials.getSubscriptionId().replace('-', ''))
        self.assertTrue(result.enabled)

    def test_get_namespace_with_non_existing_namespace(self):
        # Arrange
        name = self.sb_namespace

        # Act
        with self.assertRaises(WindowsAzureMissingResourceError):
            self.sms.get_namespace(name)

        # Assert

    def test_check_namespace_availability_not_available(self):
        # arrange
        name = credentials.getServiceBusNamespace()

        # act
        availability = self.sms.check_namespace_availability(name)

        # assert
        self.assertFalse(availability.result)

    def test_check_namespace_availability_available(self):
        # arrange
        name = 'someunusedname'

        # act
        availability = self.sms.check_namespace_availability(name)

        # assert
        self.assertTrue(availability.result)

    def test_create_namespace(self):
        # Arrange
        name = self.sb_namespace
        region = 'West US'

        # Act
        result = self.sms.create_namespace(name, region)
        self._wait_for_namespace_active(name)

        # Assert
        self.assertIsNone(result)
        self.assertTrue(self._namespace_exists(name))

    def test_create_namespace_with_existing_namespace(self):
        # Arrange
        name = self.sb_namespace
        region = 'West US'
        self.sms.create_namespace(name, region)
        self._wait_for_namespace_active(name)

        # Act
        with self.assertRaises(WindowsAzureError):
            self.sms.create_namespace(name, region)

        # Assert

    def test_delete_namespace(self):
        # Arrange
        name = self.sb_namespace
        region = 'West US'
        self.sms.create_namespace(name, region)
        self._wait_for_namespace_active(name)

        # Act
        result = self.sms.delete_namespace(name)

        # Assert
        self.assertIsNone(result)
        self.assertFalse(self._namespace_exists(name))

    def test_delete_namespace_with_non_existing_namespace(self):
        # Arrange
        name = self.sb_namespace

        # Act
        with self.assertRaises(WindowsAzureMissingResourceError):
            self.sms.delete_namespace(name)

        # Assert

#------------------------------------------------------------------------------
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_servicebusservice
﻿# coding: utf-8

#-------------------------------------------------------------------------
# Copyright (c) Microsoft.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#--------------------------------------------------------------------------
import base64
import os
import random
import sys
import time
import unittest

from datetime import datetime
from azure import WindowsAzureError
from azure.http import HTTPError
from azure.servicebus import (
    AZURE_SERVICEBUS_NAMESPACE,
    AZURE_SERVICEBUS_ACCESS_KEY,
    AZURE_SERVICEBUS_ISSUER,
    Message,
    Queue,
    Rule,
    ServiceBusService,
    Subscription,
    Topic,
    )
from util import (
    AzureTestCase,
    credentials,
    getUniqueName,
    set_service_options,
    )

#------------------------------------------------------------------------------


class ServiceBusTest(AzureTestCase):

    def setUp(self):
        self.sbs = ServiceBusService(credentials.getServiceBusNamespace(),
                                     credentials.getServiceBusKey(),
                                     'owner')
        set_service_options(self.sbs)

        self.queue_name = getUniqueName('utqueue')
        self.topic_name = getUniqueName('uttopic')

        self.additional_queue_names = []
        self.additional_topic_names = []

    def tearDown(self):
        self.cleanup()
        return super(ServiceBusTest, self).tearDown()

    def cleanup(self):
        try:
            self.sbs.delete_queue(self.queue_name)
        except:
            pass

        for name in self.additional_queue_names:
            try:
                self.sbs.delete_queue(name)
            except:
                pass

        try:
            self.sbs.delete_topic(self.topic_name)
        except:
            pass

        for name in self.additional_topic_names:
            try:
                self.sbs.delete_topic(name)
            except:
                pass

    #--Helpers-----------------------------------------------------------------
    def _create_queue(self, queue_name):
        self.sbs.create_queue(queue_name, None, True)

    def _create_queue_and_send_msg(self, queue_name, msg):
        self._create_queue(queue_name)
        self.sbs.send_queue_message(queue_name, msg)

    def _create_topic(self, topic_name):
        self.sbs.create_topic(topic_name, None, True)

    def _create_topic_and_subscription(self, topic_name, subscription_name):
        self._create_topic(topic_name)
        self._create_subscription(topic_name, subscription_name)

    def _create_subscription(self, topic_name, subscription_name):
        self.sbs.create_subscription(topic_name, subscription_name, None, True)

    #--Test cases for service bus service -------------------------------------
    def test_create_service_bus_missing_arguments(self):
        # Arrange
        if AZURE_SERVICEBUS_NAMESPACE in os.environ:
            del os.environ[AZURE_SERVICEBUS_NAMESPACE]
        if AZURE_SERVICEBUS_ACCESS_KEY in os.environ:
            del os.environ[AZURE_SERVICEBUS_ACCESS_KEY]
        if AZURE_SERVICEBUS_ISSUER in os.environ:
            del os.environ[AZURE_SERVICEBUS_ISSUER]

        # Act
        with self.assertRaises(WindowsAzureError):
            sbs = ServiceBusService()

        # Assert

    def test_create_service_bus_env_variables(self):
        # Arrange
        os.environ[
            AZURE_SERVICEBUS_NAMESPACE] = credentials.getServiceBusNamespace()
        os.environ[
            AZURE_SERVICEBUS_ACCESS_KEY] = credentials.getServiceBusKey()
        os.environ[AZURE_SERVICEBUS_ISSUER] = 'owner'

        # Act
        sbs = ServiceBusService()

        if AZURE_SERVICEBUS_NAMESPACE in os.environ:
            del os.environ[AZURE_SERVICEBUS_NAMESPACE]
        if AZURE_SERVICEBUS_ACCESS_KEY in os.environ:
            del os.environ[AZURE_SERVICEBUS_ACCESS_KEY]
        if AZURE_SERVICEBUS_ISSUER in os.environ:
            del os.environ[AZURE_SERVICEBUS_ISSUER]

        # Assert
        self.assertIsNotNone(sbs)
        self.assertEqual(sbs.service_namespace,
                         credentials.getServiceBusNamespace())
        self.assertEqual(sbs.account_key, credentials.getServiceBusKey())
        self.assertEqual(sbs.issuer, 'owner')

    #--Test cases for queues --------------------------------------------------
    def test_create_queue_no_options(self):
        # Arrange

        # Act
        created = self.sbs.create_queue(self.queue_name)

        # Assert
        self.assertTrue(created)

    def test_create_queue_no_options_fail_on_exist(self):
        # Arrange

        # Act
        created = self.sbs.create_queue(self.queue_name, None, True)

        # Assert
        self.assertTrue(created)

    def test_create_queue_with_options(self):
        # Arrange

        # Act
        queue_options = Queue()
        queue_options.default_message_time_to_live = 'PT1M'
        queue_options.duplicate_detection_history_time_window = 'PT5M'
        queue_options.enable_batched_operations = False
        queue_options.dead_lettering_on_message_expiration = False
        queue_options.lock_duration = 'PT1M'
        queue_options.max_delivery_count = 15
        queue_options.max_size_in_megabytes = 5120
        queue_options.message_count = 0
        queue_options.requires_duplicate_detection = False
        queue_options.requires_session = False
        queue_options.size_in_bytes = 0
        created = self.sbs.create_queue(self.queue_name, queue_options)

        # Assert
        self.assertTrue(created)
        queue = self.sbs.get_queue(self.queue_name)
        self.assertEqual('PT1M', queue.default_message_time_to_live)
        self.assertEqual('PT5M', queue.duplicate_detection_history_time_window)
        self.assertEqual(False, queue.enable_batched_operations)
        self.assertEqual(False, queue.dead_lettering_on_message_expiration)
        self.assertEqual('PT1M', queue.lock_duration)
        self.assertEqual(15, queue.max_delivery_count)
        self.assertEqual(5120, queue.max_size_in_megabytes)
        self.assertEqual(0, queue.message_count)
        self.assertEqual(False, queue.requires_duplicate_detection)
        self.assertEqual(False, queue.requires_session)
        self.assertEqual(0, queue.size_in_bytes)

    def test_create_queue_with_already_existing_queue(self):
        # Arrange

        # Act
        created1 = self.sbs.create_queue(self.queue_name)
        created2 = self.sbs.create_queue(self.queue_name)

        # Assert
        self.assertTrue(created1)
        self.assertFalse(created2)

    def test_create_queue_with_already_existing_queue_fail_on_exist(self):
        # Arrange

        # Act
        created = self.sbs.create_queue(self.queue_name)
        with self.assertRaises(WindowsAzureError):
            self.sbs.create_queue(self.queue_name, None, True)

        # Assert
        self.assertTrue(created)

    def test_get_queue_with_existing_queue(self):
        # Arrange
        self._create_queue(self.queue_name)

        # Act
        queue = self.sbs.get_queue(self.queue_name)

        # Assert
        self.assertIsNotNone(queue)
        self.assertEqual(queue.name, self.queue_name)

    def test_get_queue_with_non_existing_queue(self):
        # Arrange

        # Act
        with self.assertRaises(WindowsAzureError):
            resp = self.sbs.get_queue(self.queue_name)

        # Assert

    def test_list_queues(self):
        # Arrange
        self._create_queue(self.queue_name)

        # Act
        queues = self.sbs.list_queues()
        for queue in queues:
            name = queue.name

        # Assert
        self.assertIsNotNone(queues)
        self.assertNamedItemInContainer(queues, self.queue_name)

    def test_list_queues_with_special_chars(self):
        # Arrange
        # Name must start and end with an alphanumeric and can only contain
        # letters, numbers, periods, hyphens, forward slashes and underscores.
        other_queue_name = self.queue_name + 'txt/.-_123'
        self.additional_queue_names = [other_queue_name]
        self._create_queue(other_queue_name)

        # Act
        queues = self.sbs.list_queues()

        # Assert
        self.assertIsNotNone(queues)
        self.assertNamedItemInContainer(queues, other_queue_name)

    def test_delete_queue_with_existing_queue(self):
        # Arrange
        self._create_queue(self.queue_name)

        # Act
        deleted = self.sbs.delete_queue(self.queue_name)

        # Assert
        self.assertTrue(deleted)
        queues = self.sbs.list_queues()
        self.assertNamedItemNotInContainer(queues, self.queue_name)

    def test_delete_queue_with_existing_queue_fail_not_exist(self):
        # Arrange
        self._create_queue(self.queue_name)

        # Act
        deleted = self.sbs.delete_queue(self.queue_name, True)

        # Assert
        self.assertTrue(deleted)
        queues = self.sbs.list_queues()
        self.assertNamedItemNotInContainer(queues, self.queue_name)

    def test_delete_queue_with_non_existing_queue(self):
        # Arrange

        # Act
        deleted = self.sbs.delete_queue(self.queue_name)

        # Assert
        self.assertFalse(deleted)

    def test_delete_queue_with_non_existing_queue_fail_not_exist(self):
        # Arrange

        # Act
        with self.assertRaises(WindowsAzureError):
            self.sbs.delete_queue(self.queue_name, True)

        # Assert

    def test_send_queue_message(self):
        # Arrange
        self._create_queue(self.queue_name)
        sent_msg = Message(b'send message')

        # Act
        self.sbs.send_queue_message(self.queue_name, sent_msg)

        # Assert

    def test_receive_queue_message_read_delete_mode(self):
        # Assert
        sent_msg = Message(b'receive message')
        self._create_queue_and_send_msg(self.queue_name, sent_msg)

        # Act
        received_msg = self.sbs.receive_queue_message(self.queue_name, False)

        # Assert
        self.assertIsNotNone(received_msg)
        self.assertEqual(sent_msg.body, received_msg.body)

    def test_receive_queue_message_read_delete_mode_throws_on_delete(self):
        # Assert
        sent_msg = Message(b'receive message')
        self._create_queue_and_send_msg(self.queue_name, sent_msg)

        # Act
        received_msg = self.sbs.receive_queue_message(self.queue_name, False)
        with self.assertRaises(WindowsAzureError):
            received_msg.delete()

        # Assert

    def test_receive_queue_message_read_delete_mode_throws_on_unlock(self):
        # Assert
        sent_msg = Message(b'receive message')
        self._create_queue_and_send_msg(self.queue_name, sent_msg)

        # Act
        received_msg = self.sbs.receive_queue_message(self.queue_name, False)
        with self.assertRaises(WindowsAzureError):
            received_msg.unlock()

        # Assert

    def test_receive_queue_message_peek_lock_mode(self):
        # Arrange
        sent_msg = Message(b'peek lock message')
        self._create_queue_and_send_msg(self.queue_name, sent_msg)

        # Act
        received_msg = self.sbs.receive_queue_message(self.queue_name, True)

        # Assert
        self.assertIsNotNone(received_msg)
        self.assertEqual(sent_msg.body, received_msg.body)

    def test_receive_queue_message_delete(self):
        # Arrange
        sent_msg = Message(b'peek lock message delete')
        self._create_queue_and_send_msg(self.queue_name, sent_msg)

        # Act
        received_msg = self.sbs.receive_queue_message(self.queue_name, True)
        received_msg.delete()

        # Assert
        self.assertIsNotNone(received_msg)
        self.assertEqual(sent_msg.body, received_msg.body)

    def test_receive_queue_message_unlock(self):
        # Arrange
        sent_msg = Message(b'peek lock message unlock')
        self._create_queue_and_send_msg(self.queue_name, sent_msg)

        # Act
        received_msg = self.sbs.receive_queue_message(self.queue_name, True)
        received_msg.unlock()

        # Assert
        received_again_msg = self.sbs.receive_queue_message(
            self.queue_name, True)
        received_again_msg.delete()
        self.assertIsNotNone(received_msg)
        self.assertIsNotNone(received_again_msg)
        self.assertEqual(sent_msg.body, received_msg.body)
        self.assertEqual(received_again_msg.body, received_msg.body)

    def test_send_queue_message_with_custom_message_type(self):
        # Arrange
        self._create_queue(self.queue_name)

        # Act
        sent_msg = Message(
            b'<text>peek lock message custom message type</text>',
            type='text/xml')
        self.sbs.send_queue_message(self.queue_name, sent_msg)
        received_msg = self.sbs.receive_queue_message(self.queue_name, True, 5)
        received_msg.delete()

        # Assert
        self.assertIsNotNone(received_msg)
        self.assertEqual('text/xml', received_msg.type)

    def test_send_queue_message_with_custom_message_properties(self):
        # Arrange
        self._create_queue(self.queue_name)

        # Act
        props = {'hello': 'world',
                 'number': 42,
                 'active': True,
                 'deceased': False,
                 'large': 8555111000,
                 'floating': 3.14,
                 'dob': datetime(2011, 12, 14)}
        sent_msg = Message(b'message with properties', custom_properties=props)
        self.sbs.send_queue_message(self.queue_name, sent_msg)
        received_msg = self.sbs.receive_queue_message(self.queue_name, True, 5)
        received_msg.delete()

        # Assert
        self.assertIsNotNone(received_msg)
        self.assertEqual(received_msg.custom_properties['hello'], 'world')
        self.assertEqual(received_msg.custom_properties['number'], 42)
        self.assertEqual(received_msg.custom_properties['active'], True)
        self.assertEqual(received_msg.custom_properties['deceased'], False)
        self.assertEqual(received_msg.custom_properties['large'], 8555111000)
        self.assertEqual(received_msg.custom_properties['floating'], 3.14)
        self.assertEqual(
            received_msg.custom_properties['dob'], datetime(2011, 12, 14))

    def test_receive_queue_message_timeout_5(self):
        # Arrange
        self._create_queue(self.queue_name)

        # Act
        start = time.clock()
        received_msg = self.sbs.receive_queue_message(self.queue_name, True, 5)
        duration = time.clock() - start

        # Assert
        self.assertTrue(duration > 3 and duration < 7)
        self.assertIsNotNone(received_msg)
        self.assertIsNone(received_msg.body)

    def test_receive_queue_message_timeout_50(self):
        # Arrange
        self._create_queue(self.queue_name)

        # Act
        start = time.clock()
        received_msg = self.sbs.receive_queue_message(
            self.queue_name, True, 50)
        duration = time.clock() - start

        # Assert
        self.assertTrue(duration > 48 and duration < 52)
        self.assertIsNotNone(received_msg)
        self.assertIsNone(received_msg.body)

    #--Test cases for topics/subscriptions ------------------------------------
    def test_create_topic_no_options(self):
        # Arrange

        # Act
        created = self.sbs.create_topic(self.topic_name)

        # Assert
        self.assertTrue(created)

    def test_create_topic_no_options_fail_on_exist(self):
        # Arrange

        # Act
        created = self.sbs.create_topic(self.topic_name, None, True)

        # Assert
        self.assertTrue(created)

    def test_create_topic_with_options(self):
        # Arrange

        # Act
        topic_options = Topic()
        topic_options.default_message_time_to_live = 'PT1M'
        topic_options.duplicate_detection_history_time_window = 'PT5M'
        topic_options.enable_batched_operations = False
        topic_options.max_size_in_megabytes = 5120
        topic_options.requires_duplicate_detection = False
        topic_options.size_in_bytes = 0
        # TODO: MaximumNumberOfSubscriptions is not supported?
        created = self.sbs.create_topic(self.topic_name, topic_options)

        # Assert
        self.assertTrue(created)
        topic = self.sbs.get_topic(self.topic_name)
        self.assertEqual('PT1M', topic.default_message_time_to_live)
        self.assertEqual('PT5M', topic.duplicate_detection_history_time_window)
        self.assertEqual(False, topic.enable_batched_operations)
        self.assertEqual(5120, topic.max_size_in_megabytes)
        self.assertEqual(False, topic.requires_duplicate_detection)
        self.assertEqual(0, topic.size_in_bytes)

    def test_create_topic_with_already_existing_topic(self):
        # Arrange

        # Act
        created1 = self.sbs.create_topic(self.topic_name)
        created2 = self.sbs.create_topic(self.topic_name)

        # Assert
        self.assertTrue(created1)
        self.assertFalse(created2)

    def test_create_topic_with_already_existing_topic_fail_on_exist(self):
        # Arrange

        # Act
        created = self.sbs.create_topic(self.topic_name)
        with self.assertRaises(WindowsAzureError):
            self.sbs.create_topic(self.topic_name, None, True)

        # Assert
        self.assertTrue(created)

    def test_topic_backwards_compatibility_warning(self):
        # Arrange
        topic_options = Topic()
        topic_options.max_size_in_megabytes = 5120

        # Act
        val = topic_options.max_size_in_mega_bytes

        # Assert
        self.assertEqual(val, 5120)

        # Act
        topic_options.max_size_in_mega_bytes = 1024

        # Assert
        self.assertEqual(topic_options.max_size_in_megabytes, 1024)

    def test_get_topic_with_existing_topic(self):
        # Arrange
        self._create_topic(self.topic_name)

        # Act
        topic = self.sbs.get_topic(self.topic_name)

        # Assert
        self.assertIsNotNone(topic)
        self.assertEqual(topic.name, self.topic_name)

    def test_get_topic_with_non_existing_topic(self):
        # Arrange

        # Act
        with self.assertRaises(WindowsAzureError):
            self.sbs.get_topic(self.topic_name)

        # Assert

    def test_list_topics(self):
        # Arrange
        self._create_topic(self.topic_name)

        # Act
        topics = self.sbs.list_topics()
        for topic in topics:
            name = topic.name

        # Assert
        self.assertIsNotNone(topics)
        self.assertNamedItemInContainer(topics, self.topic_name)

    def test_list_topics_with_special_chars(self):
        # Arrange
        # Name must start and end with an alphanumeric and can only contain
        # letters, numbers, periods, hyphens, forward slashes and underscores.
        other_topic_name = self.topic_name + 'txt/.-_123'
        self.additional_topic_names = [other_topic_name]
        self._create_topic(other_topic_name)

        # Act
        topics = self.sbs.list_topics()

        # Assert
        self.assertIsNotNone(topics)
        self.assertNamedItemInContainer(topics, other_topic_name)

    def test_delete_topic_with_existing_topic(self):
        # Arrange
        self._create_topic(self.topic_name)

        # Act
        deleted = self.sbs.delete_topic(self.topic_name)

        # Assert
        self.assertTrue(deleted)
        topics = self.sbs.list_topics()
        self.assertNamedItemNotInContainer(topics, self.topic_name)

    def test_delete_topic_with_existing_topic_fail_not_exist(self):
        # Arrange
        self._create_topic(self.topic_name)

        # Act
        deleted = self.sbs.delete_topic(self.topic_name, True)

        # Assert
        self.assertTrue(deleted)
        topics = self.sbs.list_topics()
        self.assertNamedItemNotInContainer(topics, self.topic_name)

    def test_delete_topic_with_non_existing_topic(self):
        # Arrange

        # Act
        deleted = self.sbs.delete_topic(self.topic_name)

        # Assert
        self.assertFalse(deleted)

    def test_delete_topic_with_non_existing_topic_fail_not_exist(self):
        # Arrange

        # Act
        with self.assertRaises(WindowsAzureError):
            self.sbs.delete_topic(self.topic_name, True)

        # Assert

    def test_create_subscription(self):
        # Arrange
        self._create_topic(self.topic_name)

        # Act
        created = self.sbs.create_subscription(
            self.topic_name, 'MySubscription')

        # Assert
        self.assertTrue(created)

    def test_create_subscription_with_options(self):
        # Arrange
        self._create_topic(self.topic_name)

        # Act
        subscription_options = Subscription()
        subscription_options.dead_lettering_on_filter_evaluation_exceptions = False
        subscription_options.dead_lettering_on_message_expiration = False
        subscription_options.default_message_time_to_live = 'PT15M'
        subscription_options.enable_batched_operations = False
        subscription_options.lock_duration = 'PT1M'
        subscription_options.max_delivery_count = 15
        #message_count is read-only
        subscription_options.message_count = 0
        subscription_options.requires_session = False
        created = self.sbs.create_subscription(
            self.topic_name, 'MySubscription', subscription_options)

        # Assert
        self.assertTrue(created)
        subscription = self.sbs.get_subscription(
            self.topic_name, 'MySubscription')
        self.assertEqual(
            False, subscription.dead_lettering_on_filter_evaluation_exceptions)
        self.assertEqual(
            False, subscription.dead_lettering_on_message_expiration)
        self.assertEqual('PT15M', subscription.default_message_time_to_live)
        self.assertEqual(False, subscription.enable_batched_operations)
        self.assertEqual('PT1M', subscription.lock_duration)
        # self.assertEqual(15, subscription.max_delivery_count) #no idea why
        # max_delivery_count is always 10
        self.assertEqual(0, subscription.message_count)
        self.assertEqual(False, subscription.requires_session)

    def test_create_subscription_fail_on_exist(self):
        # Arrange
        self._create_topic(self.topic_name)

        # Act
        created = self.sbs.create_subscription(
            self.topic_name, 'MySubscription', None, True)

        # Assert
        self.assertTrue(created)

    def test_create_subscription_with_already_existing_subscription(self):
        # Arrange
        self._create_topic(self.topic_name)

        # Act
        created1 = self.sbs.create_subscription(
            self.topic_name, 'MySubscription')
        created2 = self.sbs.create_subscription(
            self.topic_name, 'MySubscription')

        # Assert
        self.assertTrue(created1)
        self.assertFalse(created2)

    def test_create_subscription_with_already_existing_subscription_fail_on_exist(self):
        # Arrange
        self._create_topic(self.topic_name)

        # Act
        created = self.sbs.create_subscription(
            self.topic_name, 'MySubscription')
        with self.assertRaises(WindowsAzureError):
            self.sbs.create_subscription(
                self.topic_name, 'MySubscription', None, True)

        # Assert
        self.assertTrue(created)

    def test_list_subscriptions(self):
        # Arrange
        self._create_topic_and_subscription(self.topic_name, 'MySubscription2')

        # Act
        subscriptions = self.sbs.list_subscriptions(self.topic_name)

        # Assert
        self.assertIsNotNone(subscriptions)
        self.assertEqual(len(subscriptions), 1)
        self.assertEqual(subscriptions[0].name, 'MySubscription2')

    def test_get_subscription_with_existing_subscription(self):
        # Arrange
        self._create_topic_and_subscription(self.topic_name, 'MySubscription3')

        # Act
        subscription = self.sbs.get_subscription(
            self.topic_name, 'MySubscription3')

        # Assert
        self.assertIsNotNone(subscription)
        self.assertEqual(subscription.name, 'MySubscription3')

    def test_get_subscription_with_non_existing_subscription(self):
        # Arrange
        self._create_topic_and_subscription(self.topic_name, 'MySubscription3')

        # Act
        with self.assertRaises(WindowsAzureError):
            self.sbs.get_subscription(self.topic_name, 'MySubscription4')

        # Assert

    def test_delete_subscription_with_existing_subscription(self):
        # Arrange
        self._create_topic(self.topic_name)
        self._create_subscription(self.topic_name, 'MySubscription4')
        self._create_subscription(self.topic_name, 'MySubscription5')

        # Act
        deleted = self.sbs.delete_subscription(
            self.topic_name, 'MySubscription4')

        # Assert
        self.assertTrue(deleted)
        subscriptions = self.sbs.list_subscriptions(self.topic_name)
        self.assertIsNotNone(subscriptions)
        self.assertEqual(len(subscriptions), 1)
        self.assertEqual(subscriptions[0].name, 'MySubscription5')

    def test_delete_subscription_with_existing_subscription_fail_not_exist(self):
        # Arrange
        self._create_topic(self.topic_name)
        self._create_subscription(self.topic_name, 'MySubscription4')
        self._create_subscription(self.topic_name, 'MySubscription5')

        # Act
        deleted = self.sbs.delete_subscription(
            self.topic_name, 'MySubscription4', True)

        # Assert
        self.assertTrue(deleted)
        subscriptions = self.sbs.list_subscriptions(self.topic_name)
        self.assertIsNotNone(subscriptions)
        self.assertEqual(len(subscriptions), 1)
        self.assertEqual(subscriptions[0].name, 'MySubscription5')

    def test_delete_subscription_with_non_existing_subscription(self):
        # Arrange
        self._create_topic(self.topic_name)

        # Act
        deleted = self.sbs.delete_subscription(
            self.topic_name, 'MySubscription')

        # Assert
        self.assertFalse(deleted)

    def test_delete_subscription_with_non_existing_subscription_fail_not_exist(self):
        # Arrange
        self._create_topic(self.topic_name)

        # Act
        with self.assertRaises(WindowsAzureError):
            self.sbs.delete_subscription(
                self.topic_name, 'MySubscription', True)

        # Assert

    def test_create_rule_no_options(self):
        # Arrange
        self._create_topic_and_subscription(self.topic_name, 'MySubscription')

        # Act
        created = self.sbs.create_rule(
            self.topic_name, 'MySubscription', 'MyRule1')

        # Assert
        self.assertTrue(created)

    def test_create_rule_no_options_fail_on_exist(self):
        # Arrange
        self._create_topic_and_subscription(self.topic_name, 'MySubscription')

        # Act
        created = self.sbs.create_rule(
            self.topic_name, 'MySubscription', 'MyRule1', None, True)

        # Assert
        self.assertTrue(created)

    def test_create_rule_with_already_existing_rule(self):
        # Arrange
        self._create_topic_and_subscription(self.topic_name, 'MySubscription')

        # Act
        created1 = self.sbs.create_rule(
            self.topic_name, 'MySubscription', 'MyRule1')
        created2 = self.sbs.create_rule(
            self.topic_name, 'MySubscription', 'MyRule1')

        # Assert
        self.assertTrue(created1)
        self.assertFalse(created2)

    def test_create_rule_with_already_existing_rule_fail_on_exist(self):
        # Arrange
        self._create_topic_and_subscription(self.topic_name, 'MySubscription')

        # Act
        created = self.sbs.create_rule(
            self.topic_name, 'MySubscription', 'MyRule1')
        with self.assertRaises(WindowsAzureError):
            self.sbs.create_rule(
                self.topic_name, 'MySubscription', 'MyRule1', None, True)

        # Assert
        self.assertTrue(created)

    def test_create_rule_with_options_sql_filter(self):
        # Arrange
        self._create_topic_and_subscription(self.topic_name, 'MySubscription')

        # Act
        rule1 = Rule()
        rule1.filter_type = 'SqlFilter'
        rule1.filter_expression = 'number > 40'
        created = self.sbs.create_rule(
            self.topic_name, 'MySubscription', 'MyRule1', rule1)

        # Assert
        self.assertTrue(created)

    def test_create_rule_with_options_true_filter(self):
        # Arrange
        self._create_topic_and_subscription(self.topic_name, 'MySubscription')

        # Act
        rule1 = Rule()
        rule1.filter_type = 'TrueFilter'
        rule1.filter_expression = '1=1'
        created = self.sbs.create_rule(
            self.topic_name, 'MySubscription', 'MyRule1', rule1)

        # Assert
        self.assertTrue(created)

    def test_create_rule_with_options_false_filter(self):
        # Arrange
        self._create_topic_and_subscription(self.topic_name, 'MySubscription')

        # Act
        rule1 = Rule()
        rule1.filter_type = 'FalseFilter'
        rule1.filter_expression = '1=0'
        created = self.sbs.create_rule(
            self.topic_name, 'MySubscription', 'MyRule1', rule1)

        # Assert
        self.assertTrue(created)

    def test_create_rule_with_options_correlation_filter(self):
        # Arrange
        self._create_topic_and_subscription(self.topic_name, 'MySubscription')

        # Act
        rule1 = Rule()
        rule1.filter_type = 'CorrelationFilter'
        rule1.filter_expression = 'myid'
        created = self.sbs.create_rule(
            self.topic_name, 'MySubscription', 'MyRule1', rule1)

        # Assert
        self.assertTrue(created)

    def test_create_rule_with_options_empty_rule_action(self):
        # Arrange
        self._create_topic_and_subscription(self.topic_name, 'MySubscription')

        # Act
        rule1 = Rule()
        rule1.action_type = 'EmptyRuleAction'
        rule1.action_expression = ''
        created = self.sbs.create_rule(
            self.topic_name, 'MySubscription', 'MyRule1', rule1)

        # Assert
        self.assertTrue(created)

    def test_create_rule_with_options_sql_rule_action(self):
        # Arrange
        self._create_topic_and_subscription(self.topic_name, 'MySubscription')

        # Act
        rule1 = Rule()
        rule1.action_type = 'SqlRuleAction'
        rule1.action_expression = "SET number = 5"
        created = self.sbs.create_rule(
            self.topic_name, 'MySubscription', 'MyRule1', rule1)

        # Assert
        self.assertTrue(created)

    def test_list_rules(self):
        # Arrange
        self._create_topic_and_subscription(self.topic_name, 'MySubscription')
        resp = self.sbs.create_rule(
            self.topic_name, 'MySubscription', 'MyRule2')

        # Act
        rules = self.sbs.list_rules(self.topic_name, 'MySubscription')

        # Assert
        self.assertEqual(len(rules), 2)

    def test_get_rule_with_existing_rule(self):
        # Arrange
        self._create_topic_and_subscription(self.topic_name, 'MySubscription')

        # Act
        rule = self.sbs.get_rule(self.topic_name, 'MySubscription', '$Default')

        # Assert
        self.assertIsNotNone(rule)
        self.assertEqual(rule.name, '$Default')

    def test_get_rule_with_non_existing_rule(self):
        # Arrange
        self._create_topic_and_subscription(self.topic_name, 'MySubscription')

        # Act
        with self.assertRaises(WindowsAzureError):
            self.sbs.get_rule(self.topic_name,
                              'MySubscription', 'NonExistingRule')

        # Assert

    def test_get_rule_with_existing_rule_with_options(self):
        # Arrange
        self._create_topic_and_subscription(self.topic_name, 'MySubscription')
        sent_rule = Rule()
        sent_rule.filter_type = 'SqlFilter'
        sent_rule.filter_expression = 'number > 40'
        sent_rule.action_type = 'SqlRuleAction'
        sent_rule.action_expression = 'SET number = 5'
        self.sbs.create_rule(
            self.topic_name, 'MySubscription', 'MyRule1', sent_rule)

        # Act
        received_rule = self.sbs.get_rule(
            self.topic_name, 'MySubscription', 'MyRule1')

        # Assert
        self.assertIsNotNone(received_rule)
        self.assertEqual(received_rule.name, 'MyRule1')
        self.assertEqual(received_rule.filter_type, sent_rule.filter_type)
        self.assertEqual(received_rule.filter_expression,
                         sent_rule.filter_expression)
        self.assertEqual(received_rule.action_type, sent_rule.action_type)
        self.assertEqual(received_rule.action_expression,
                         sent_rule.action_expression)

    def test_delete_rule_with_existing_rule(self):
        # Arrange
        self._create_topic_and_subscription(self.topic_name, 'MySubscription')
        resp = self.sbs.create_rule(
            self.topic_name, 'MySubscription', 'MyRule3')
        resp = self.sbs.create_rule(
            self.topic_name, 'MySubscription', 'MyRule4')

        # Act
        deleted1 = self.sbs.delete_rule(
            self.topic_name, 'MySubscription', 'MyRule4')
        deleted2 = self.sbs.delete_rule(
            self.topic_name, 'MySubscription', '$Default')

        # Assert
        self.assertTrue(deleted1)
        self.assertTrue(deleted2)
        rules = self.sbs.list_rules(self.topic_name, 'MySubscription')
        self.assertIsNotNone(rules)
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0].name, 'MyRule3')

    def test_delete_rule_with_existing_rule_fail_not_exist(self):
        # Arrange
        self._create_topic_and_subscription(self.topic_name, 'MySubscription')
        resp = self.sbs.create_rule(
            self.topic_name, 'MySubscription', 'MyRule3')
        resp = self.sbs.create_rule(
            self.topic_name, 'MySubscription', 'MyRule4')

        # Act
        deleted1 = self.sbs.delete_rule(
            self.topic_name, 'MySubscription', 'MyRule4', True)
        deleted2 = self.sbs.delete_rule(
            self.topic_name, 'MySubscription', '$Default', True)

        # Assert
        self.assertTrue(deleted1)
        self.assertTrue(deleted2)
        rules = self.sbs.list_rules(self.topic_name, 'MySubscription')
        self.assertIsNotNone(rules)
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0].name, 'MyRule3')

    def test_delete_rule_with_non_existing_rule(self):
        # Arrange
        self._create_topic_and_subscription(self.topic_name, 'MySubscription')

        # Act
        deleted = self.sbs.delete_rule(
            self.topic_name, 'MySubscription', 'NonExistingRule')

        # Assert
        self.assertFalse(deleted)

    def test_delete_rule_with_non_existing_rule_fail_not_exist(self):
        # Arrange
        self._create_topic_and_subscription(self.topic_name, 'MySubscription')

        # Act
        with self.assertRaises(WindowsAzureError):
            self.sbs.delete_rule(
                self.topic_name, 'MySubscription', 'NonExistingRule', True)

        # Assert

    def test_send_topic_message(self):
        # Arrange
        self._create_topic_and_subscription(self.topic_name, 'MySubscription')
        sent_msg = Message(b'subscription message')

        # Act
        self.sbs.send_topic_message(self.topic_name, sent_msg)

        # Assert

    def test_receive_subscription_message_read_delete_mode(self):
        # Arrange
        self._create_topic_and_subscription(self.topic_name, 'MySubscription')
        sent_msg = Message(b'subscription message')
        self.sbs.send_topic_message(self.topic_name, sent_msg)

        # Act
        received_msg = self.sbs.receive_subscription_message(
            self.topic_name, 'MySubscription', False)

        # Assert
        self.assertIsNotNone(received_msg)
        self.assertEqual(sent_msg.body, received_msg.body)

    def test_receive_subscription_message_read_delete_mode_throws_on_delete(self):
        # Arrange
        self._create_topic_and_subscription(self.topic_name, 'MySubscription')
        sent_msg = Message(b'subscription message')
        self.sbs.send_topic_message(self.topic_name, sent_msg)

        # Act
        received_msg = self.sbs.receive_subscription_message(
            self.topic_name, 'MySubscription', False)
        with self.assertRaises(WindowsAzureError):
            received_msg.delete()

        # Assert

    def test_receive_subscription_message_read_delete_mode_throws_on_unlock(self):
        # Arrange
        self._create_topic_and_subscription(self.topic_name, 'MySubscription')
        sent_msg = Message(b'subscription message')
        self.sbs.send_topic_message(self.topic_name, sent_msg)

        # Act
        received_msg = self.sbs.receive_subscription_message(
            self.topic_name, 'MySubscription', False)
        with self.assertRaises(WindowsAzureError):
            received_msg.unlock()

        # Assert

    def test_receive_subscription_message_peek_lock_mode(self):
        # Arrange
        self._create_topic_and_subscription(self.topic_name, 'MySubscription')
        sent_msg = Message(b'subscription message')
        self.sbs.send_topic_message(self.topic_name, sent_msg)

        # Act
        received_msg = self.sbs.receive_subscription_message(
            self.topic_name, 'MySubscription', True, 5)

        # Assert
        self.assertIsNotNone(received_msg)
        self.assertEqual(sent_msg.body, received_msg.body)

    def test_receive_subscription_message_delete(self):
        # Arrange
        self._create_topic_and_subscription(self.topic_name, 'MySubscription')
        sent_msg = Message(b'subscription message')
        self.sbs.send_topic_message(self.topic_name, sent_msg)

        # Act
        received_msg = self.sbs.receive_subscription_message(
            self.topic_name, 'MySubscription', True, 5)
        received_msg.delete()

        # Assert
        self.assertIsNotNone(received_msg)
        self.assertEqual(sent_msg.body, received_msg.body)

    def test_receive_subscription_message_unlock(self):
        # Arrange
        self._create_topic_and_subscription(self.topic_name, 'MySubscription')
        sent_msg = Message(b'subscription message')
        self.sbs.send_topic_message(self.topic_name, sent_msg)

        # Act
        received_msg = self.sbs.receive_subscription_message(
            self.topic_name, 'MySubscription', True)
        received_msg.unlock()

        # Assert
        received_again_msg = self.sbs.receive_subscription_message(
            self.topic_name, 'MySubscription', True)
        received_again_msg.delete()
        self.assertIsNotNone(received_msg)
        self.assertIsNotNone(received_again_msg)
        self.assertEqual(sent_msg.body, received_msg.body)
        self.assertEqual(received_again_msg.body, received_msg.body)

    def test_with_filter(self):
         # Single filter
        called = []

        def my_filter(request, next):
            called.append(True)
            return next(request)

        sbs = self.sbs.with_filter(my_filter)
        sbs.create_topic(self.topic_name + '0', None, True)

        self.assertTrue(called)

        del called[:]

        sbs.delete_topic(self.topic_name + '0')

        self.assertTrue(called)
        del called[:]

        # Chained filters
        def filter_a(request, next):
            called.append('a')
            return next(request)

        def filter_b(request, next):
            called.append('b')
            return next(request)

        sbs = self.sbs.with_filter(filter_a).with_filter(filter_b)
        sbs.create_topic(self.topic_name + '0', None, True)

        self.assertEqual(called, ['b', 'a'])

        sbs.delete_topic(self.topic_name + '0')

        self.assertEqual(called, ['b', 'a', 'b', 'a'])

    def test_two_identities(self):
        # In order to run this test, 2 service bus service identities are
        # created using the sbaztool available at:
        # http://code.msdn.microsoft.com/windowsazure/Authorization-SBAzTool-6fd76d93
        #
        # Use the following commands to create 2 identities and grant access
        # rights.
        # Replace <servicebusnamespace> with the namespace specified in the
        # test .json file
        # Replace <servicebuskey> with the key specified in the test .json file
        # This only needs to be executed once, after the service bus namespace
        # is created.
        #
        # sbaztool makeid user1 NoHEoD6snlvlhZm7yek9Etxca3l0CYjfc19ICIJZoUg= -n <servicebusnamespace> -k <servicebuskey>
        # sbaztool grant Send /path1 user1 -n <servicebusnamespace> -k <servicebuskey>
        # sbaztool grant Listen /path1 user1 -n <servicebusnamespace> -k <servicebuskey>
        # sbaztool grant Manage /path1 user1 -n <servicebusnamespace> -k
        # <servicebuskey>

        # sbaztool makeid user2 Tb6K5qEgstyRBwp86JEjUezKj/a+fnkLFnibfgvxvdg= -n <servicebusnamespace> -k <servicebuskey>
        # sbaztool grant Send /path2 user2 -n <servicebusnamespace> -k <servicebuskey>
        # sbaztool grant Listen /path2 user2 -n <servicebusnamespace> -k <servicebuskey>
        # sbaztool grant Manage /path2 user2 -n <servicebusnamespace> -k
        # <servicebuskey>

        sbs1 = ServiceBusService(credentials.getServiceBusNamespace(),
                                 'NoHEoD6snlvlhZm7yek9Etxca3l0CYjfc19ICIJZoUg=',
                                 'user1')
        sbs2 = ServiceBusService(credentials.getServiceBusNamespace(),
                                 'Tb6K5qEgstyRBwp86JEjUezKj/a+fnkLFnibfgvxvdg=',
                                 'user2')

        queue1_name = 'path1/queue' + str(random.randint(1, 10000000))
        queue2_name = 'path2/queue' + str(random.randint(1, 10000000))

        try:
            # Create queues, success
            sbs1.create_queue(queue1_name)
            sbs2.create_queue(queue2_name)

            # Receive messages, success
            msg = sbs1.receive_queue_message(queue1_name, True, 1)
            self.assertIsNone(msg.body)
            msg = sbs1.receive_queue_message(queue1_name, True, 1)
            self.assertIsNone(msg.body)
            msg = sbs2.receive_queue_message(queue2_name, True, 1)
            self.assertIsNone(msg.body)
            msg = sbs2.receive_queue_message(queue2_name, True, 1)
            self.assertIsNone(msg.body)

            # Receive messages, failure
            with self.assertRaises(HTTPError):
                msg = sbs1.receive_queue_message(queue2_name, True, 1)
            with self.assertRaises(HTTPError):
                msg = sbs2.receive_queue_message(queue1_name, True, 1)
        finally:
            try:
                sbs1.delete_queue(queue1_name)
            except:
                pass
            try:
                sbs2.delete_queue(queue2_name)
            except:
                pass

    def test_unicode_create_queue_unicode_name(self):
        # Arrange
        self.queue_name = self.queue_name + u'啊齄丂狛狜'

        # Act
        with self.assertRaises(WindowsAzureError):
            created = self.sbs.create_queue(self.queue_name)

        # Assert

    def test_send_queue_message_unicode_python_27(self):
        '''Test for auto-encoding of unicode text (backwards compatibility).'''
        if sys.version_info >= (3,):
            return

        # Arrange
        data = u'receive message啊齄丂狛狜'
        sent_msg = Message(data)
        self._create_queue(self.queue_name)

        # Act
        self.sbs.send_queue_message(self.queue_name, sent_msg)

        # Assert
        received_msg = self.sbs.receive_queue_message(self.queue_name, False)
        self.assertIsNotNone(received_msg)
        self.assertEqual(received_msg.body, data.encode('utf-8'))

    def test_send_queue_message_unicode_python_33(self):
        if sys.version_info < (3,):
            return

        # Arrange
        data = u'receive message啊齄丂狛狜'
        sent_msg = Message(data)
        self._create_queue(self.queue_name)

        # Act
        with self.assertRaises(TypeError):
            self.sbs.send_queue_message(self.queue_name, sent_msg)

        # Assert

    def test_unicode_receive_queue_message_unicode_data(self):
        # Assert
        sent_msg = Message(u'receive message啊齄丂狛狜'.encode('utf-8'))
        self._create_queue_and_send_msg(self.queue_name, sent_msg)

        # Act
        received_msg = self.sbs.receive_queue_message(self.queue_name, False)

        # Assert
        self.assertIsNotNone(received_msg)
        self.assertEqual(sent_msg.body, received_msg.body)

    def test_unicode_receive_queue_message_binary_data(self):
        # Arrange
        base64_data = 'AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8gISIjJCUmJygpKissLS4vMDEyMzQ1Njc4OTo7PD0+P0BBQkNERUZHSElKS0xNTk9QUVJTVFVWV1hZWltcXV5fYGFiY2RlZmdoaWprbG1ub3BxcnN0dXZ3eHl6e3x9fn+AgYKDhIWGh4iJiouMjY6PkJGSk5SVlpeYmZqbnJ2en6ChoqOkpaanqKmqq6ytrq+wsbKztLW2t7i5uru8vb6/wMHCw8TFxsfIycrLzM3Oz9DR0tPU1dbX2Nna29zd3t/g4eLj5OXm5+jp6uvs7e7v8PHy8/T19vf4+fr7/P3+/wABAgMEBQYHCAkKCwwNDg8QERITFBUWFxgZGhscHR4fICEiIyQlJicoKSorLC0uLzAxMjM0NTY3ODk6Ozw9Pj9AQUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVpbXF1eX2BhYmNkZWZnaGlqa2xtbm9wcXJzdHV2d3h5ent8fX5/gIGCg4SFhoeIiYqLjI2Oj5CRkpOUlZaXmJmam5ydnp+goaKjpKWmp6ipqqusra6vsLGys7S1tre4ubq7vL2+v8DBwsPExcbHyMnKy8zNzs/Q0dLT1NXW19jZ2tvc3d7f4OHi4+Tl5ufo6err7O3u7/Dx8vP09fb3+Pn6+/z9/v8AAQIDBAUGBwgJCgsMDQ4PEBESExQVFhcYGRobHB0eHyAhIiMkJSYnKCkqKywtLi8wMTIzNDU2Nzg5Ojs8PT4/QEFCQ0RFRkdISUpLTE1OT1BRUlNUVVZXWFlaW1xdXl9gYWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXp7fH1+f4CBgoOEhYaHiImKi4yNjo+QkZKTlJWWl5iZmpucnZ6foKGio6SlpqeoqaqrrK2ur7CxsrO0tba3uLm6u7y9vr/AwcLDxMXGx8jJysvMzc7P0NHS09TV1tfY2drb3N3e3+Dh4uPk5ebn6Onq6+zt7u/w8fLz9PX29/j5+vv8/f7/AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8gISIjJCUmJygpKissLS4vMDEyMzQ1Njc4OTo7PD0+P0BBQkNERUZHSElKS0xNTk9QUVJTVFVWV1hZWltcXV5fYGFiY2RlZmdoaWprbG1ub3BxcnN0dXZ3eHl6e3x9fn+AgYKDhIWGh4iJiouMjY6PkJGSk5SVlpeYmZqbnJ2en6ChoqOkpaanqKmqq6ytrq+wsbKztLW2t7i5uru8vb6/wMHCw8TFxsfIycrLzM3Oz9DR0tPU1dbX2Nna29zd3t/g4eLj5OXm5+jp6uvs7e7v8PHy8/T19vf4+fr7/P3+/w=='
        binary_data = base64.b64decode(base64_data)
        sent_msg = Message(binary_data)
        self._create_queue_and_send_msg(self.queue_name, sent_msg)

        # Act
        received_msg = self.sbs.receive_queue_message(self.queue_name, False)

        # Assert
        self.assertIsNotNone(received_msg)
        self.assertEqual(sent_msg.body, received_msg.body)

    def test_unicode_create_subscription_unicode_name(self):
        # Arrange
        self._create_topic(self.topic_name)

        # Act
        with self.assertRaises(WindowsAzureError):
            created = self.sbs.create_subscription(
                self.topic_name, u'MySubscription啊齄丂狛狜')

        # Assert

    def test_unicode_create_rule_unicode_name(self):
        # Arrange
        self._create_topic_and_subscription(self.topic_name, 'MySubscription')

        # Act
        with self.assertRaises(WindowsAzureError):
            created = self.sbs.create_rule(
                self.topic_name, 'MySubscription', 'MyRule啊齄丂狛狜')

        # Assert

    def test_send_topic_message_unicode_python_27(self):
        '''Test for auto-encoding of unicode text (backwards compatibility).'''
        if sys.version_info >= (3,):
            return

        # Arrange
        data = u'receive message啊齄丂狛狜'
        sent_msg = Message(data)
        self._create_topic_and_subscription(self.topic_name, 'MySubscription')

        # Act
        self.sbs.send_topic_message(self.topic_name, sent_msg)

        # Assert
        received_msg = self.sbs.receive_subscription_message(
            self.topic_name, 'MySubscription', False)
        self.assertIsNotNone(received_msg)
        self.assertEqual(received_msg.body, data.encode('utf-8'))

    def test_send_topic_message_unicode_python_33(self):
        if sys.version_info < (3,):
            return

        # Arrange
        data = u'receive message啊齄丂狛狜'
        sent_msg = Message(data)
        self._create_topic_and_subscription(self.topic_name, 'MySubscription')

        # Act
        with self.assertRaises(TypeError):
            self.sbs.send_topic_message(self.topic_name, sent_msg)

        # Assert

    def test_unicode_receive_subscription_message_unicode_data(self):
        # Arrange
        self._create_topic_and_subscription(self.topic_name, 'MySubscription')
        sent_msg = Message(u'subscription message啊齄丂狛狜'.encode('utf-8'))
        self.sbs.send_topic_message(self.topic_name, sent_msg)

        # Act
        received_msg = self.sbs.receive_subscription_message(
            self.topic_name, 'MySubscription', False)

        # Assert
        self.assertIsNotNone(received_msg)
        self.assertEqual(sent_msg.body, received_msg.body)

    def test_unicode_receive_subscription_message_binary_data(self):
        # Arrange
        base64_data = 'AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8gISIjJCUmJygpKissLS4vMDEyMzQ1Njc4OTo7PD0+P0BBQkNERUZHSElKS0xNTk9QUVJTVFVWV1hZWltcXV5fYGFiY2RlZmdoaWprbG1ub3BxcnN0dXZ3eHl6e3x9fn+AgYKDhIWGh4iJiouMjY6PkJGSk5SVlpeYmZqbnJ2en6ChoqOkpaanqKmqq6ytrq+wsbKztLW2t7i5uru8vb6/wMHCw8TFxsfIycrLzM3Oz9DR0tPU1dbX2Nna29zd3t/g4eLj5OXm5+jp6uvs7e7v8PHy8/T19vf4+fr7/P3+/wABAgMEBQYHCAkKCwwNDg8QERITFBUWFxgZGhscHR4fICEiIyQlJicoKSorLC0uLzAxMjM0NTY3ODk6Ozw9Pj9AQUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVpbXF1eX2BhYmNkZWZnaGlqa2xtbm9wcXJzdHV2d3h5ent8fX5/gIGCg4SFhoeIiYqLjI2Oj5CRkpOUlZaXmJmam5ydnp+goaKjpKWmp6ipqqusra6vsLGys7S1tre4ubq7vL2+v8DBwsPExcbHyMnKy8zNzs/Q0dLT1NXW19jZ2tvc3d7f4OHi4+Tl5ufo6err7O3u7/Dx8vP09fb3+Pn6+/z9/v8AAQIDBAUGBwgJCgsMDQ4PEBESExQVFhcYGRobHB0eHyAhIiMkJSYnKCkqKywtLi8wMTIzNDU2Nzg5Ojs8PT4/QEFCQ0RFRkdISUpLTE1OT1BRUlNUVVZXWFlaW1xdXl9gYWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXp7fH1+f4CBgoOEhYaHiImKi4yNjo+QkZKTlJWWl5iZmpucnZ6foKGio6SlpqeoqaqrrK2ur7CxsrO0tba3uLm6u7y9vr/AwcLDxMXGx8jJysvMzc7P0NHS09TV1tfY2drb3N3e3+Dh4uPk5ebn6Onq6+zt7u/w8fLz9PX29/j5+vv8/f7/AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8gISIjJCUmJygpKissLS4vMDEyMzQ1Njc4OTo7PD0+P0BBQkNERUZHSElKS0xNTk9QUVJTVFVWV1hZWltcXV5fYGFiY2RlZmdoaWprbG1ub3BxcnN0dXZ3eHl6e3x9fn+AgYKDhIWGh4iJiouMjY6PkJGSk5SVlpeYmZqbnJ2en6ChoqOkpaanqKmqq6ytrq+wsbKztLW2t7i5uru8vb6/wMHCw8TFxsfIycrLzM3Oz9DR0tPU1dbX2Nna29zd3t/g4eLj5OXm5+jp6uvs7e7v8PHy8/T19vf4+fr7/P3+/w=='
        binary_data = base64.b64decode(base64_data)
        self._create_topic_and_subscription(self.topic_name, 'MySubscription')
        sent_msg = Message(binary_data)
        self.sbs.send_topic_message(self.topic_name, sent_msg)

        # Act
        received_msg = self.sbs.receive_subscription_message(
            self.topic_name, 'MySubscription', False)

        # Assert
        self.assertIsNotNone(received_msg)
        self.assertEqual(sent_msg.body, received_msg.body)

#------------------------------------------------------------------------------
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_servicemanagementservice
﻿#-------------------------------------------------------------------------
# Copyright (c) Microsoft.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#--------------------------------------------------------------------------

import base64
import os
import time
import unittest

from azure.servicemanagement import (
    CertificateSetting,
    ConfigurationSet,
    ConfigurationSetInputEndpoint,
    KeyPair,
    LinuxConfigurationSet,
    Listener,
    OSVirtualHardDisk,
    PublicKey,
    ServiceManagementService,
    WindowsConfigurationSet,
    )
from azure.storage.blobservice import BlobService
from util import (
    AzureTestCase,
    credentials,
    getUniqueName,
    set_service_options,
    )

SERVICE_CERT_FORMAT = 'pfx'
SERVICE_CERT_PASSWORD = 'Python'
SERVICE_CERT_DATA = 'MIIJ7AIBAzCCCagGCSqGSIb3DQEHAaCCCZkEggmVMIIJkTCCBfoGCSqGSIb3DQEHAaCCBesEggXnMIIF4zCCBd8GCyqGSIb3DQEMCgECoIIE/jCCBPowHAYKKoZIhvcNAQwBAzAOBAhxOU59DvbmnAICB9AEggTYNM2UfOCtA1G0fhKNmu79z8/yUm5ybh5JamZqZ4Ra21wTc1khmVmWr0OAYhttaKtqtHfyFv7UY/cojg+fdOPCI+Fa8qQI7oXGEU7hS4O7VH3R/bDESctPB4TRdhjb88hLC+CdQc64PwjHFoaUHEQHFMsi7ujbi1u4Xg8YRqg4eKoG0AAraEQgyS3+1oWndtUOdqvOAsAG/bshiK47pgxMTgHpYjtOMtjcPqrwYq5aZQNWdJMXjl4JnmGJpO1dGqlSyr3uJuPobuq18diFS+JMJk/nQt50GF/SkscQn3TCLc6g6AjuKqdnSQTM34eNkZanKyyBuRmVUvM+zcKP6riiRDB86wrfNcT3sPDh9x6BSiTaxWKDk4IziWUMy8WJ/qItaVm2klIyez9JeEgcN2PhI2B1SFxH2qliyCmJ+308RFJHlQZDNZhpTRNgkulYfiswr5xOVEcU7J6eithmmD72xANSiiTbtFH10Bu10FN4SbSvOYQiGIjDVG4awAPVC9gURm88PciIimz1ne0WN3Ioj92BTC78kNoMI7+NDiVV01W+/CNK8J1WCTkKWRxTui8Ykm2z63gh9KmSZyEstFDFIz2WbJEKM8N4vjzGpNhRYOHpxFaCm2E/yoNj4MyHmo9XGtYsqhA0Jy12Wmx/fVGeZb3Az8Y5MYCQasc9XwvzACf2+RKsz6ey7jTb+Exo0gQB13PNFLEs83R57bDa8vgQupYBFcsamw/RvqmXn8sGw53kd71VVElrfaCNluvAFrLPdaH3F/+J8KHdV7Xs9A1ITvgpHbw2BnQBPwH3pSXZYh5+7it6WSNIHbv8h33Ue+vPLby5Huhg86R4nZkjJbeQXsfVpvC+llhOBHUX+UJth76a/d0iAewPO90rDNx+Nqff+Q7hPoUgxE8HtrbhZNY3qNFfyRGLbCZJpb+6DE7WsDSogFE5gY7gnmJwtT+FBlIocysaBn1NMH8fo/2zyuAOUfjHvuIR+K/NzcMdn5WL7bYjmvJwRIAaPScZV56NzNbZdHsHAU2ujvE+sGNmwr4wz3Db6Q9VfzkNWEzDmRlYEsRYNqQ/E7O2KQWETzZSGTEXgz57APE0d/cOprX+9PXZTdqqjOCU12YLtJobIcBZz+AFPMJRlY+pjuIu8wTzbWX7yoek3zmN9iZAZT5gNYCwIwo06Of2gvgssQ4X53QmJc/oD6WSyZpcS67JOQ8bHXIT1Lg9FBAfgXWEQ+BwIBK1SEJYlZJm0JkJ3Og7t3rgAmuv5YOfbFLo484946izfQeoUF5qrn/qSiqNOnYNMLvaXWT2pWE9V6u8max0l5dA5qNR772ahMQEH1iZu/K8gKfQ/z6Ea1yxFVwGtf9uNSuvS2M3MFa4Dos8FtxxQgOIEoiV4qc2yQIyiAKYusRI+K3PMnqSyg9S3eh0LCbuI8CYESpolrFCMyNFSwJpM+pUDA5GkRM/gYGLAhtZtLxgZBZYn81DgiRmk4igRIjNKWcy5l0eWN5KPBQve0QVXFB9z0A2GqOGEHJTZS5rww61hVaNyp2nBa8Mrd9afnogoEcb1SBRsU5QTsP91XGj8zdljL2t+jJDNUxi6nbNQN6onRY1ewpdCKxFzFyR/75nrEPBd8UrDTZ7k/FcNxIlAA2KPH2Dt3r8EZfEKDGBzTATBgkqhkiG9w0BCRUxBgQEAQAAADBXBgkqhkiG9w0BCRQxSh5IAGUANAA1ADcAOQAyAGYAYQAtAGUAMQA3AGUALQA0ADEAMgAzAC0AOQBiAGYANwAtADEAZQBjADkAMQA4ADMAOQAxAGIAOAAxMF0GCSsGAQQBgjcRATFQHk4ATQBpAGMAcgBvAHMAbwBmAHQAIABTAHQAcgBvAG4AZwAgAEMAcgB5AHAAdABvAGcAcgBhAHAAaABpAGMAIABQAHIAbwB2AGkAZABlAHIwggOPBgkqhkiG9w0BBwagggOAMIIDfAIBADCCA3UGCSqGSIb3DQEHATAcBgoqhkiG9w0BDAEGMA4ECLA43UrS9nGWAgIH0ICCA0isAHOSVK2C8XAZpu2dTiJfB51QqgbUuZ4QdPu+INKT3x5x775SMC2wbFEjvjhA3hys6D/ALV4q97JpKc6YUDZMP4zl2yYx6Pr6chTudRCwlrAKqk0Sp0IBZrxZBVBgRsz9pt3VRR9bI9ElHD8j/ahZ+Hx+mxlfUePrabOqlzw9FVmrqBIhhmAs9Ax0l5mvY3p7ww1Vm0K2sVdOZdsKx27Cf7rg4rC6JJ3tPvTfJDUkTCPFgFtam+vZSiMoYbz00Kj2uPBJbkpG2ngjK8ONHzWq8PF6K6Feut5vrjeswR/bm9gGPtrjAU0qBuP5YfJqei6zvs+hXzYOcnnhxFlfHz/QvVJM9losSm17kq0SSqG4HD1XF6C6eiH3pySa2mnw3kEivulBYFUO2jmSGroNlwz6/LVoM+801h0vJayFxP7xRntQr0z5agzyNfCZ8249dgJ4y2UJmSRArdv5h+gYXIra2pNRHVUfPFTIZw3Yf5Uhz83ta3JxIM0BCtwQBsWpJSs3q9tokLQa/wJY6Qj5pVw3pxv+497DrOVCiCwAI3GVTa0QylscKFMnEjxIpYCLDNnY0fRXDYA94AfhDkdjlXLMFZLuwRrfTHqfyaDuFdq9cT2FuhM1J73reMriMGfu+UzTTWd4UZa/mGGRZM9eWvrIvgkvLQr+T250wa7igbJwh3FXRm7TqZSkLOpW3p+Losw0GJIz2k5DW61gkPYY0hMwzpniDrN8pc5BCo8Wtb4UBfW5+J5oQn2oKj2B3BuflL+jgYjXb6YRe1TTstJWmTR4/CrZc2ecNHTMGYlr7bOptaGcw9z/JaCjdoElUNSITVj6TQCa//jko+tdbM1cCtzE7Ty8ARs2XghxbhgLV5KyYZ0q06/tYvaT0vx4PZi64X1weIEmcHJRgdz9dC3+8SrtABoxxft9MD7DvtRNcWiZ+qdKfKEsGgZXYAPgYg/xObaiR9Sz2QGYv1BqoNAtalJLscn7UmGZnzjgyvD3GpvxPnZIZr3pAAyWZKUsL7eFCDjwJu/DlUni31ZI0sNJvcJZkWl5gGtuoTf3q4v80wKlNFVsUCrWRosITNlQun8Q+0NR6MZp8vvMKfRnJr7CkcZOAa7rzZjGF+EwOzAfMAcGBSsOAwIaBBQyyvu2Rm6lFW3e9sQk83bjO1g2pAQU8PYpZ4LXqCe9cmNgCFNqmt4fCOQCAgfQ'
SERVICE_CERT_DATA_PUBLIC = 'MIIC9jCCAeKgAwIBAgIQ00IFaqV9VqVJxI+wZka0szAJBgUrDgMCHQUAMBUxEzARBgNVBAMTClB5dGhvblRlc3QwHhcNMTIwODMwMDAyNTMzWhcNMzkxMjMxMjM1OTU5WjAVMRMwEQYDVQQDEwpQeXRob25UZXN0MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAsjULNM53WPLkht1rbrDob/e4hZTHzj/hlLoBt2X3cNRc6dOPsMucxbMdchbCqAFa5RIaJvF5NDKqZuUSwq6bttD71twzy9bQ03EySOcRBad1VyqAZQ8DL8nUGSnXIUh+tpz4fDGM5f3Ly9NX8zfGqG3sT635rrFlUp3meJC+secCCwTLOOcIs3KQmuB+pMB5Y9rPhoxcekFfpq1pKtis6pmxnVbiL49kr6UUL6RQRDwik4t1jttatXLZqHETTmXl0Y0wS5AcJUXVAn5AL2kybULoThop2v01/E0NkPtFPAqLVs/kKBahniNn9uwUo+LS9FA8rWGu0FY4CZEYDfhb+QIDAQABo0owSDBGBgNVHQEEPzA9gBBS6knRHo54LppngxVCCzZVoRcwFTETMBEGA1UEAxMKUHl0aG9uVGVzdIIQ00IFaqV9VqVJxI+wZka0szAJBgUrDgMCHQUAA4IBAQAnZbP3YV+08wI4YTg6MOVA+j1njd0kVp35FLehripmaMNE6lgk3Vu1MGGl0JnvMr3fNFGFzRske/jVtFxlHE5H/CoUzmyMQ+W06eV/e995AduwTKsS0ZgYn0VoocSXWst/nyhpKOcbJgAOohOYxgsGI1JEqQgjyeqzcCIhw/vlWiA3V8bSiPnrC9vwhH0eB025hBd2VbEGDz2nWCYkwtuOLMTvkmLi/oFw3GOfgagZKk8k/ZPffMCafz+yR3vb1nqAjncrVcJLI8amUfpxhjZYexo8MbxBA432M6w8sjXN+uLCl7ByWZ4xs4vonWgkmjeObtU37SIzolHT4dxIgaP2'
SERVICE_CERT_THUMBPRINT = 'BEA4B74BD6B915E9DD6A01FB1B8C3C1740F517F2'
SERVICE_CERT_THUMBALGO = 'sha1'

DEPLOYMENT_ORIGINAL_CONFIG = '''<ServiceConfiguration serviceName="WindowsAzure1" xmlns="http://schemas.microsoft.com/ServiceHosting/2008/10/ServiceConfiguration" osFamily="1" osVersion="*" schemaVersion="2012-05.1.7">
  <Role name="WorkerRole1">
    <Instances count="2" />
    <ConfigurationSettings>
      <Setting name="Microsoft.WindowsAzure.Plugins.Diagnostics.ConnectionString" value="UseDevelopmentStorage=true" />
    </ConfigurationSettings>
  </Role>
</ServiceConfiguration>'''

DEPLOYMENT_UPDATE_CONFIG = '''<ServiceConfiguration serviceName="WindowsAzure1" xmlns="http://schemas.microsoft.com/ServiceHosting/2008/10/ServiceConfiguration" osFamily="1" osVersion="*" schemaVersion="2012-05.1.7">
  <Role name="WorkerRole1">
    <Instances count="4" />
    <ConfigurationSettings>
      <Setting name="Microsoft.WindowsAzure.Plugins.Diagnostics.ConnectionString" value="UseDevelopmentStorage=true" />
    </ConfigurationSettings>
  </Role>
</ServiceConfiguration>'''

CSPKG_PATH = 'data/WindowsAzure1.cspkg'
DATA_VHD_PATH = 'data/testhd'

# This blob must be created manually before running the unit tests,
# they must be present in the storage account listed in the credentials file.
LINUX_OS_VHD_URL = credentials.getLinuxOSVHD()

# The easiest way to create a Linux OS vhd is to use the Azure management
# portal to create a Linux VM, and have it store the VHD in the
# storage account listed in the credentials file.  Then stop the VM,
# and use the following code to copy the VHD to another blob (if you
# try to use the VM's VHD directly without making a copy, you will get
# conflict errors).

# sourceblob = '/{0}/{1}/{2}'.format(credentials.getStorageServicesName(), 'vhdcontainername', 'vhdblobname')
# self.bc.copy_blob('vhdcontainername', 'targetvhdblobname', sourceblob)
#
# in the credentials file, set:
#    "linuxosvhd" : "http://storageservicesname.blob.core.windows.net/vhdcontainername/targetvhdblobname",


#------------------------------------------------------------------------------
class ServiceManagementServiceTest(AzureTestCase):

    def setUp(self):
        self.sms = ServiceManagementService(credentials.getSubscriptionId(),
                                            credentials.getManagementCertFile())
        set_service_options(self.sms)

        self.bc = BlobService(credentials.getStorageServicesName(),
                              credentials.getStorageServicesKey())
        set_service_options(self.bc)

        self.hosted_service_name = getUniqueName('utsvc')
        self.container_name = getUniqueName('utctnr')
        self.disk_name = getUniqueName('utdisk')
        self.os_image_name = getUniqueName('utosimg')
        self.data_disk_info = None

    def tearDown(self):
        if self.data_disk_info is not None:
            try:
                disk = self.sms.get_data_disk(
                    self.data_disk_info[0], self.data_disk_info[1],
                    self.data_disk_info[2], self.data_disk_info[3])
                try:
                    result = self.sms.delete_data_disk(
                        self.data_disk_info[0], self.data_disk_info[1],
                        self.data_disk_info[2], self.data_disk_info[3])
                    self._wait_for_async(result.request_id)
                except:
                    pass
                try:
                    self.sms.delete_disk(disk.disk_name)
                except:
                    pass
            except:
                pass

        disk_names = [self.disk_name]

        try:
            # Can't delete a hosted service if it has deployments, so delete
            # those first
            props = self.sms.get_hosted_service_properties(
                self.hosted_service_name, True)
            for deployment in props.deployments:
                try:
                    for role in deployment.role_list:
                        role_props = self.sms.get_role(
                            self.hosted_service_name,
                            deployment.name,
                            role.role_name)
                        if role_props.os_virtual_hard_disk.disk_name \
                            not in disk_names:
                            disk_names.append(
                                role_props.os_virtual_hard_disk.disk_name)
                except:
                    pass

                try:
                    result = self.sms.delete_deployment(
                        self.hosted_service_name, deployment.name)
                    self._wait_for_async(result.request_id)
                except:
                    pass
            self.sms.delete_hosted_service(self.hosted_service_name)
        except:
            pass

        try:
            result = self.sms.delete_os_image(self.os_image_name)
            self._wait_for_async(result.request_id)
        except:
            pass

        for disk_name in disk_names:
            try:
                self.sms.delete_disk(disk_name)
            except:
                pass

        try:
            self.bc.delete_container(self.container_name)
        except:
            pass

    #--Helpers-----------------------------------------------------------------
    def _wait_for_async(self, request_id):
        count = 0
        result = self.sms.get_operation_status(request_id)
        while result.status == 'InProgress':
            count = count + 1
            if count > 120:
                self.assertTrue(
                    False, 'Timed out waiting for async operation to complete.')
            time.sleep(5)
            result = self.sms.get_operation_status(request_id)
        self.assertEqual(result.status, 'Succeeded')

    def _wait_for_deployment(self, service_name, deployment_name,
                             status='Running'):
        count = 0
        props = self.sms.get_deployment_by_name(service_name, deployment_name)
        while props.status != status:
            count = count + 1
            if count > 120:
                self.assertTrue(
                    False, 'Timed out waiting for deployment status.')
            time.sleep(5)
            props = self.sms.get_deployment_by_name(
                service_name, deployment_name)

    def _wait_for_role(self, service_name, deployment_name, role_instance_name,
                       status='ReadyRole'):
        count = 0
        props = self.sms.get_deployment_by_name(service_name, deployment_name)
        while self._get_role_instance_status(props, role_instance_name) != status:
            count = count + 1
            if count > 120:
                self.assertTrue(
                    False, 'Timed out waiting for role instance status.')
            time.sleep(5)
            props = self.sms.get_deployment_by_name(
                service_name, deployment_name)

    def _wait_for_rollback_allowed(self, service_name, deployment_name):
        count = 0
        props = self.sms.get_deployment_by_name(service_name, deployment_name)
        while props.rollback_allowed == False:
            count = count + 1
            if count > 120:
                self.assertTrue(
                    False, 'Timed out waiting for rollback allowed.')
            time.sleep(5)
            props = self.sms.get_deployment_by_name(
                service_name, deployment_name)

    def _get_role_instance_status(self, deployment, role_instance_name):
        for role_instance in deployment.role_instance_list:
            if role_instance.instance_name == role_instance_name:
                return role_instance.instance_status
        return None

    def _create_hosted_service(self, name, location=None, affinity_group=None):
        if not location and not affinity_group:
            location = 'West US'

        result = self.sms.create_hosted_service(
            name,
            name + 'label',
            name + 'description',
            location,
            affinity_group,
            {'ext1': 'val1', 'ext2': 42})
        self.assertIsNone(result)

    def _hosted_service_exists(self, name):
        try:
            props = self.sms.get_hosted_service_properties(name)
            return props is not None
        except:
            return False

    def _create_service_certificate(self, service_name, data, format,
                                    password):
        result = self.sms.add_service_certificate(service_name, data,
                                                  format, password)
        self._wait_for_async(result.request_id)

    def _service_certificate_exists(self, service_name, thumbalgorithm,
                                    thumbprint):
        try:
            props = self.sms.get_service_certificate(
                service_name, thumbalgorithm, thumbprint)
            return props is not None
        except:
            return False

    def _deployment_exists(self, service_name, deployment_name):
        try:
            props = self.sms.get_deployment_by_name(
                service_name, deployment_name)
            return props is not None
        except:
            return False

    def _create_container_and_block_blob(self, container_name, blob_name,
                                         blob_data):
        self.bc.create_container(container_name, None, 'container', False)
        resp = self.bc.put_blob(
            container_name, blob_name, blob_data, 'BlockBlob')
        self.assertIsNone(resp)

    def _create_container_and_page_blob(self, container_name, blob_name,
                                        content_length):
        self.bc.create_container(container_name, None, 'container', False)
        resp = self.bc.put_blob(container_name, blob_name, '',
                                'PageBlob',
                                x_ms_blob_content_length=str(content_length))
        self.assertIsNone(resp)

    def _upload_file_to_block_blob(self, file_path, blob_name):
        data = open(file_path, 'rb').read()
        url = 'http://' + \
            credentials.getStorageServicesName() + \
            '.blob.core.windows.net/' + self.container_name + '/' + blob_name
        self._create_container_and_block_blob(
            self.container_name, blob_name, data)
        return url

    def _upload_chunks(self, file_path, blob_name, chunk_size):
        index = 0
        with open(file_path, 'rb') as f:
            while True:
                data = f.read(chunk_size)
                if data:
                    length = len(data)
                    self.bc.put_page(
                        self.container_name, blob_name, data,
                        'bytes=' + str(index) + '-' + str(index + length - 1),
                        'update')
                    index += length
                else:
                    break

    def _upload_file_to_page_blob(self, file_path, blob_name):
        url = 'http://' + \
            credentials.getStorageServicesName() + \
            '.blob.core.windows.net/' + self.container_name + '/' + blob_name
        content_length = os.path.getsize(file_path)
        self._create_container_and_page_blob(
            self.container_name, blob_name, content_length)
        self._upload_chunks(file_path, blob_name, 262144)
        return url

    def _upload_default_package_to_storage_blob(self, blob_name):
        return self._upload_file_to_block_blob(CSPKG_PATH, blob_name)

    def _upload_disk_to_storage_blob(self, blob_name):
        return self._upload_file_to_page_blob(DATA_VHD_PATH, blob_name)

    def _add_deployment(self, service_name, deployment_name,
                        deployment_slot='Production'):
        configuration = base64.b64encode(DEPLOYMENT_ORIGINAL_CONFIG)
        package_url = self._upload_default_package_to_storage_blob(
            deployment_name + 'Blob')
        result = self.sms.create_deployment(
            service_name, deployment_slot, deployment_name, package_url,
            deployment_name + 'label', configuration, False, False,
            {'dep1': 'val1', 'dep2': 'val2'})
        self._wait_for_async(result.request_id)

    def _create_hosted_service_with_deployment(self, service_name,
                                               deployment_name):
        self._create_hosted_service(service_name)
        self._add_deployment(service_name, deployment_name)

    def _role_exists(self, service_name, deployment_name, role_name):
        try:
            props = self.sms.get_role(service_name, deployment_name, role_name)
            return props is not None
        except:
            return False

    def _create_disk(self, disk_name, os, url):
        result = self.sms.add_disk(False, disk_name, url, disk_name, os)
        self.assertIsNone(result)

    def _disk_exists(self, disk_name):
        try:
            disk = self.sms.get_disk(disk_name)
            return disk is not None
        except:
            return False

    def _create_os_image(self, name, blob_url, os):
        result = self.sms.add_os_image(name + 'label', blob_url, name, os)
        self._wait_for_async(result.request_id)

    def _os_image_exists(self, image_name):
        try:
            image = self.sms.get_os_image(image_name)
            return image is not None
        except:
            return False

    def _blob_exists(self, container_name, blob_name):
        try:
            props = self.bc.get_blob_properties(container_name, blob_name)
            return props is not None
        except:
            return False

    def _data_disk_exists(self, service_name, deployment_name, role_name, lun):
        try:
            props = self.sms.get_data_disk(
                service_name, deployment_name, role_name, lun)
            return props is not None
        except:
            return False

    def _add_data_disk_from_blob_url(self, service_name, deployment_name,
                                     role_name, lun, label):
        url = self._upload_disk_to_storage_blob('disk')
        result = self.sms.add_data_disk(
            service_name, deployment_name, role_name, lun, None, None, label,
            None, None, url)
        self._wait_for_async(result.request_id)

    def _linux_image_name(self):
        return self._image_from_category('Canonical')

    def _windows_image_name(self):
        return self._image_from_category('Microsoft Windows Server Group')

    def _host_name_from_role_name(self, role_name):
        return 'hn' + role_name[-13:]

    def _image_from_category(self, category):
        # return the first one listed, which should be the most stable
        return [i.name for i in self.sms.list_os_images() \
            if category in i.category][0]

    def _windows_role(self, role_name, subnet_name=None, port='59913'):
        host_name = self._host_name_from_role_name(role_name)
        system = self._windows_config(host_name)
        os_hd = self._os_hd(self._windows_image_name(),
                            self.container_name,
                            role_name + '.vhd')
        network = self._network_config(subnet_name, port)
        return (system, os_hd, network)

    def _linux_role(self, role_name, subnet_name=None, port='59913'):
        host_name = self._host_name_from_role_name(role_name)
        system = self._linux_config(host_name)
        os_hd = self._os_hd(self._linux_image_name(),
                            self.container_name,
                            role_name + '.vhd')
        network = self._network_config(subnet_name, port)
        return (system, os_hd, network)

    def _windows_config(self, hostname):
        system = WindowsConfigurationSet(
            hostname, 'u7;9jbp!', False, False, 'Pacific Standard Time',
            'azureuser')
        system.domain_join = None
        system.stored_certificate_settings.stored_certificate_settings.append(
            CertificateSetting(SERVICE_CERT_THUMBPRINT, 'My', 'LocalMachine'))
        listener = Listener('Https', SERVICE_CERT_THUMBPRINT)
        system.win_rm.listeners.listeners.append(listener)
        return system

    def _linux_config(self, hostname):
        pk = PublicKey(SERVICE_CERT_THUMBPRINT,
                       u'/home/unittest/.ssh/authorized_keys')
        pair = KeyPair(SERVICE_CERT_THUMBPRINT, u'/home/unittest/.ssh/id_rsa')
        system = LinuxConfigurationSet(hostname, 'unittest', 'u7;9jbp!', True)
        system.ssh.public_keys.public_keys.append(pk)
        system.ssh.key_pairs.key_pairs.append(pair)
        return system

    def _network_config(self, subnet_name=None, port='59913'):
        network = ConfigurationSet()
        network.configuration_set_type = 'NetworkConfiguration'
        network.input_endpoints.input_endpoints.append(
            ConfigurationSetInputEndpoint('utendpoint', 'tcp', port, '3394'))
        if subnet_name:
            network.subnet_names.append(subnet_name)
        return network

    def _os_hd(self, image_name, target_container_name, target_blob_name):
        media_link = 'http://' + \
            credentials.getStorageServicesName() + \
            '.blob.core.windows.net/' + target_container_name + '/' + \
            target_blob_name
        os_hd = OSVirtualHardDisk(image_name, media_link,
                                  disk_label=target_blob_name)
        return os_hd

    def _create_vm_linux(self, service_name, deployment_name, role_name):
        self._create_hosted_service(service_name)
        self._create_service_certificate(
            service_name,
            SERVICE_CERT_DATA, SERVICE_CERT_FORMAT, SERVICE_CERT_PASSWORD)

        system, os_hd, network = self._linux_role(role_name)

        result = self.sms.create_virtual_machine_deployment(
            service_name, deployment_name, 'production',
            deployment_name + 'label', role_name, system, os_hd,
            network, role_size='Small')

        self._wait_for_async(result.request_id)
        self._wait_for_deployment(service_name, deployment_name)
        self._wait_for_role(service_name, deployment_name, role_name)
        self._assert_role_instance_endpoint(
            service_name, deployment_name, 'utendpoint', 'tcp', '59913', '3394')

    def _create_vm_windows(self, service_name, deployment_name, role_name):
        self._create_hosted_service(service_name)
        self._create_service_certificate(
            service_name,
            SERVICE_CERT_DATA, SERVICE_CERT_FORMAT, SERVICE_CERT_PASSWORD)

        system, os_hd, network = self._windows_role(role_name)

        result = self.sms.create_virtual_machine_deployment(
            service_name, deployment_name, 'production',
            deployment_name + 'label', role_name, system, os_hd,
            network, role_size='Small')

        self._wait_for_async(result.request_id)
        self._wait_for_deployment(service_name, deployment_name)
        self._wait_for_role(service_name, deployment_name, role_name)
        self._assert_role_instance_endpoint(
            service_name, deployment_name, 'utendpoint', 'tcp', '59913', '3394')

    def _assert_role_instance_endpoint(self, service_name, deployment_name,
                                       endpoint_name, protocol,
                                       public_port, local_port):
        deployment = self.sms.get_deployment_by_name(
            service_name, deployment_name)
        self.assertEqual(len(deployment.role_instance_list), 1)
        role_instance = deployment.role_instance_list[0]
        self.assertEqual(len(role_instance.instance_endpoints), 1)
        endpoint = role_instance.instance_endpoints[0]
        self.assertEqual(endpoint.name, endpoint_name)
        self.assertEqual(endpoint.protocol, protocol)
        self.assertEqual(endpoint.public_port, public_port)
        self.assertEqual(endpoint.local_port, local_port)

    def _add_role_windows(self, service_name, deployment_name, role_name, port):
        system, os_hd, network = self._windows_role(role_name, port=port)

        result = self.sms.add_role(service_name, deployment_name, role_name,
                                   system, os_hd, network)
        self._wait_for_async(result.request_id)
        self._wait_for_role(service_name, deployment_name, role_name)

    #--Test cases for hosted services ------------------------------------
    def test_list_hosted_services(self):
        # Arrange
        self._create_hosted_service(self.hosted_service_name)

        # Act
        result = self.sms.list_hosted_services()

        # Assert
        self.assertIsNotNone(result)
        self.assertTrue(len(result) > 0)

        service = None
        for temp in result:
            if temp.service_name == self.hosted_service_name:
                service = temp
                break

        self.assertIsNotNone(service)
        self.assertIsNotNone(service.service_name)
        self.assertIsNotNone(service.url)
        self.assertIsNotNone(service.hosted_service_properties)
        self.assertIsNotNone(service.hosted_service_properties.affinity_group)
        self.assertIsNotNone(service.hosted_service_properties.date_created)
        self.assertIsNotNone(
            service.hosted_service_properties.date_last_modified)
        self.assertIsNotNone(service.hosted_service_properties.description)
        self.assertIsNotNone(service.hosted_service_properties.label)
        self.assertIsNotNone(service.hosted_service_properties.location)
        self.assertIsNotNone(service.hosted_service_properties.status)
        self.assertIsNotNone(
            service.hosted_service_properties.extended_properties['ext1'])
        self.assertIsNotNone(
            service.hosted_service_properties.extended_properties['ext2'])
        self.assertIsNone(service.deployments)

    def test_get_hosted_service_properties(self):
        # Arrange
        self._create_hosted_service(self.hosted_service_name)

        # Act
        result = self.sms.get_hosted_service_properties(
            self.hosted_service_name)

        # Assert
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.service_name)
        self.assertIsNotNone(result.url)
        self.assertIsNotNone(result.hosted_service_properties)
        self.assertIsNotNone(result.hosted_service_properties.affinity_group)
        self.assertIsNotNone(result.hosted_service_properties.date_created)
        self.assertIsNotNone(
            result.hosted_service_properties.date_last_modified)
        self.assertIsNotNone(result.hosted_service_properties.description)
        self.assertIsNotNone(result.hosted_service_properties.label)
        self.assertIsNotNone(result.hosted_service_properties.location)
        self.assertIsNotNone(result.hosted_service_properties.status)
        self.assertIsNotNone(
            result.hosted_service_properties.extended_properties['ext1'])
        self.assertIsNotNone(
            result.hosted_service_properties.extended_properties['ext2'])
        self.assertIsNone(result.deployments)

    def test_get_hosted_service_properties_with_embed_detail(self):
        # Arrange
        deployment_name = 'utdeployment'
        self._create_hosted_service_with_deployment(
            self.hosted_service_name, deployment_name)

        # Act
        result = self.sms.get_hosted_service_properties(
            self.hosted_service_name, True)

        # Assert
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.service_name)
        self.assertIsNotNone(result.url)
        self.assertIsNotNone(result.hosted_service_properties)
        self.assertIsNotNone(result.hosted_service_properties.affinity_group)
        self.assertIsNotNone(result.hosted_service_properties.date_created)
        self.assertIsNotNone(
            result.hosted_service_properties.date_last_modified)
        self.assertIsNotNone(result.hosted_service_properties.description)
        self.assertIsNotNone(result.hosted_service_properties.label)
        self.assertIsNotNone(result.hosted_service_properties.location)
        self.assertIsNotNone(result.hosted_service_properties.status)
        self.assertIsNotNone(
            result.hosted_service_properties.extended_properties['ext1'])
        self.assertIsNotNone(
            result.hosted_service_properties.extended_properties['ext2'])

        self.assertIsNotNone(result.deployments)
        self.assertIsNotNone(result.deployments[0].configuration)
        self.assertIsNotNone(result.deployments[0].created_time)
        self.assertIsNotNone(result.deployments[0].deployment_slot)
        self.assertIsNotNone(result.deployments[0].extended_properties['dep1'])
        self.assertIsNotNone(result.deployments[0].extended_properties['dep2'])
        self.assertIsNotNone(result.deployments[0].label)
        self.assertIsNotNone(result.deployments[0].last_modified_time)
        self.assertFalse(result.deployments[0].locked)
        self.assertEqual(result.deployments[0].name, deployment_name)
        self.assertIsNone(result.deployments[0].persistent_vm_downtime_info)
        self.assertIsNotNone(result.deployments[0].private_id)
        self.assertIsNotNone(result.deployments[0].role_list[0].os_version)
        self.assertEqual(result.deployments[0]
                         .role_list[0].role_name, 'WorkerRole1')
        self.assertFalse(result.deployments[0].rollback_allowed)
        self.assertIsNotNone(result.deployments[0].sdk_version)
        self.assertIsNotNone(result.deployments[0].status)
        self.assertIsNotNone(result.deployments[0].upgrade_domain_count)
        self.assertIsNone(result.deployments[0].upgrade_status)
        self.assertIsNotNone(result.deployments[0].url)
        self.assertIsNotNone(result.deployments[0].role_instance_list[0].fqdn)
        self.assertIsNotNone(
            result.deployments[0].role_instance_list[0].instance_error_code)
        self.assertIsNotNone(
            result.deployments[0].role_instance_list[0].instance_fault_domain)
        self.assertIsNotNone(
            result.deployments[0].role_instance_list[0].instance_name)
        self.assertIsNotNone(
            result.deployments[0].role_instance_list[0].instance_size)
        self.assertIsNotNone(
            result.deployments[0].role_instance_list[0].instance_state_details)
        self.assertIsNotNone(
            result.deployments[0].role_instance_list[0].instance_status)
        self.assertIsNotNone(
            result.deployments[0].role_instance_list[0].instance_upgrade_domain)
        self.assertIsNotNone(
            result.deployments[0].role_instance_list[0].ip_address)
        self.assertIsNotNone(
            result.deployments[0].role_instance_list[0].power_state)
        self.assertEqual(
            result.deployments[0].role_instance_list[0].role_name, 'WorkerRole1')

    def test_create_hosted_service(self):
        # Arrange
        label = 'pythonlabel'
        description = 'python hosted service description'
        location = 'West US'

        # Act
        result = self.sms.create_hosted_service(
            self.hosted_service_name, label, description, location, None,
            {'ext1': 'val1', 'ext2': 'val2'})

        # Assert
        self.assertIsNone(result)
        self.assertTrue(self._hosted_service_exists(self.hosted_service_name))

    def test_update_hosted_service(self):
        # Arrange
        self._create_hosted_service(self.hosted_service_name)
        label = 'ptvslabelupdate'
        description = 'ptvs description update'

        # Act
        result = self.sms.update_hosted_service(
            self.hosted_service_name, label, description,
            {'ext1': 'val1update', 'ext2': 'val2update', 'ext3': 'brandnew'})

        # Assert
        self.assertIsNone(result)
        props = self.sms.get_hosted_service_properties(
            self.hosted_service_name)
        self.assertEqual(props.hosted_service_properties.label, label)
        self.assertEqual(
            props.hosted_service_properties.description, description)
        self.assertEqual(
            props.hosted_service_properties.extended_properties['ext1'],
            'val1update')
        self.assertEqual(
            props.hosted_service_properties.extended_properties['ext2'],
            'val2update')
        self.assertEqual(
            props.hosted_service_properties.extended_properties['ext3'],
            'brandnew')

    def test_delete_hosted_service(self):
        # Arrange
        self._create_hosted_service(self.hosted_service_name)

        # Act
        result = self.sms.delete_hosted_service(self.hosted_service_name)

        # Assert
        self.assertIsNone(result)
        self.assertFalse(self._hosted_service_exists(self.hosted_service_name))

    def test_get_deployment_by_slot(self):
        # Arrange
        deployment_name = 'utdeployment'
        self._create_hosted_service_with_deployment(
            self.hosted_service_name, deployment_name)

        # Act
        result = self.sms.get_deployment_by_slot(
            self.hosted_service_name, 'Production')

        # Assert
        self.assertIsNotNone(result)
        self.assertEqual(result.name, deployment_name)
        self.assertEqual(result.deployment_slot, 'Production')
        self.assertIsNotNone(result.label)
        self.assertIsNotNone(result.configuration)

    def test_get_deployment_by_name(self):
        # Arrange
        deployment_name = 'utdeployment'
        self._create_hosted_service_with_deployment(
            self.hosted_service_name, deployment_name)

        # Act
        result = self.sms.get_deployment_by_name(
            self.hosted_service_name, deployment_name)

        # Assert
        self.assertIsNotNone(result)
        self.assertEqual(result.name, deployment_name)
        self.assertEqual(result.deployment_slot, 'Production')
        self.assertIsNotNone(result.label)
        self.assertIsNotNone(result.configuration)

    def test_create_deployment(self):
        # Arrange
        self._create_hosted_service(self.hosted_service_name)
        configuration = base64.b64encode(DEPLOYMENT_ORIGINAL_CONFIG)
        package_url = self._upload_default_package_to_storage_blob(
            'WindowsAzure1Blob')

        # Act
        result = self.sms.create_deployment(
            self.hosted_service_name, 'production', 'WindowsAzure1',
            package_url, 'deploylabel', configuration)
        self._wait_for_async(result.request_id)

        # Assert
        self.assertTrue(
            self._deployment_exists(self.hosted_service_name, 'WindowsAzure1'))

    def test_delete_deployment(self):
        # Arrange
        deployment_name = 'utdeployment'
        self._create_hosted_service_with_deployment(
            self.hosted_service_name, deployment_name)

        # Act
        result = self.sms.delete_deployment(
            self.hosted_service_name, deployment_name)
        self._wait_for_async(result.request_id)

        # Assert
        self.assertFalse(
            self._deployment_exists(self.hosted_service_name, deployment_name))

    def test_swap_deployment(self):
        # Arrange
        production_deployment_name = 'utdeployprod'
        staging_deployment_name = 'utdeploystag'
        self._create_hosted_service(self.hosted_service_name)
        self._add_deployment(self.hosted_service_name,
                             production_deployment_name, 'Production')
        self._add_deployment(self.hosted_service_name,
                             staging_deployment_name, 'Staging')

        # Act
        result = self.sms.swap_deployment(
            self.hosted_service_name,
            production_deployment_name,
            staging_deployment_name)
        self._wait_for_async(result.request_id)

        # Assert
        deploy = self.sms.get_deployment_by_slot(
            self.hosted_service_name, 'Production')
        self.assertIsNotNone(deploy)
        self.assertEqual(deploy.name, staging_deployment_name)
        self.assertEqual(deploy.deployment_slot, 'Production')

        deploy = self.sms.get_deployment_by_slot(
            self.hosted_service_name, 'Staging')
        self.assertIsNotNone(deploy)
        self.assertEqual(deploy.name, production_deployment_name)
        self.assertEqual(deploy.deployment_slot, 'Staging')

    def test_change_deployment_configuration(self):
        # Arrange
        deployment_name = 'utdeployment'
        self._create_hosted_service_with_deployment(
            self.hosted_service_name, deployment_name)
        configuration = base64.b64encode(DEPLOYMENT_UPDATE_CONFIG)

        # Act
        result = self.sms.change_deployment_configuration(
            self.hosted_service_name, deployment_name, configuration)
        self._wait_for_async(result.request_id)

        # Assert
        props = self.sms.get_deployment_by_name(
            self.hosted_service_name, deployment_name)
        self.assertTrue(props.configuration.find('Instances count="4"') >= 0)

    def test_update_deployment_status(self):
        # Arrange
        deployment_name = 'utdeployment'
        self._create_hosted_service_with_deployment(
            self.hosted_service_name, deployment_name)

        # Act
        result = self.sms.update_deployment_status(
            self.hosted_service_name, deployment_name, 'Suspended')
        self._wait_for_async(result.request_id)

        # Assert
        props = self.sms.get_deployment_by_name(
            self.hosted_service_name, deployment_name)
        self.assertEqual(props.status, 'Suspended')

    def test_upgrade_deployment(self):
        # Arrange
        deployment_name = 'utdeployment'
        self._create_hosted_service_with_deployment(
            self.hosted_service_name, deployment_name)
        package_url = self._upload_default_package_to_storage_blob('updated')
        configuration = base64.b64encode(DEPLOYMENT_UPDATE_CONFIG)

        # Act
        result = self.sms.upgrade_deployment(
            self.hosted_service_name, deployment_name, 'Auto',
            package_url, configuration, 'upgraded', True)
        self._wait_for_async(result.request_id)

        # Assert
        props = self.sms.get_deployment_by_name(
            self.hosted_service_name, deployment_name)
        self.assertEqual(props.label, 'upgraded')
        self.assertTrue(props.configuration.find('Instances count="4"') >= 0)

    def test_walk_upgrade_domain(self):
        # Arrange
        deployment_name = 'utdeployment'
        self._create_hosted_service_with_deployment(
            self.hosted_service_name, deployment_name)
        package_url = self._upload_default_package_to_storage_blob('updated')
        configuration = base64.b64encode(DEPLOYMENT_UPDATE_CONFIG)
        result = self.sms.upgrade_deployment(
            self.hosted_service_name, deployment_name, 'Manual',
            package_url, configuration, 'upgraded', True)
        self._wait_for_async(result.request_id)

        # Act
        result = self.sms.walk_upgrade_domain(
            self.hosted_service_name, deployment_name, 0)
        self._wait_for_async(result.request_id)

        # Assert
        props = self.sms.get_deployment_by_name(
            self.hosted_service_name, deployment_name)
        self.assertEqual(props.label, 'upgraded')
        self.assertTrue(props.configuration.find('Instances count="4"') >= 0)

    def test_rollback_update_or_upgrade(self):
        # Arrange
        deployment_name = 'utdeployment'
        self._create_hosted_service_with_deployment(
            self.hosted_service_name, deployment_name)
        package_url = self._upload_default_package_to_storage_blob(
            'updated207')
        configuration = base64.b64encode(DEPLOYMENT_UPDATE_CONFIG)

        self.sms.upgrade_deployment(self.hosted_service_name, deployment_name,
                                    'Auto', package_url, configuration,
                                    'upgraded', True)
        self._wait_for_rollback_allowed(
            self.hosted_service_name, deployment_name)

        # Act
        result = self.sms.rollback_update_or_upgrade(
            self.hosted_service_name, deployment_name, 'Auto', True)
        self._wait_for_async(result.request_id)

        # Assert
        props = self.sms.get_deployment_by_name(
            self.hosted_service_name, deployment_name)
        self.assertTrue(props.configuration.find('Instances count="2"') >= 0)

    def test_reboot_role_instance(self):
        # Arrange
        role_instance_name = 'WorkerRole1_IN_0'
        deployment_name = 'utdeployment'
        self._create_hosted_service_with_deployment(
            self.hosted_service_name, deployment_name)
        result = self.sms.update_deployment_status(
            self.hosted_service_name, deployment_name, 'Running')
        self._wait_for_async(result.request_id)
        self._wait_for_deployment(self.hosted_service_name, deployment_name)
        self._wait_for_role(self.hosted_service_name, deployment_name,
                            role_instance_name)

        # Act
        result = self.sms.reboot_role_instance(
            self.hosted_service_name, deployment_name, role_instance_name)
        self._wait_for_async(result.request_id)

        # Assert
        props = self.sms.get_deployment_by_name(
            self.hosted_service_name, deployment_name)
        status = self._get_role_instance_status(props, role_instance_name)
        self.assertTrue(status == 'StoppedVM' or status == 'ReadyRole')

    def test_reimage_role_instance(self):
        # Arrange
        role_instance_name = 'WorkerRole1_IN_0'
        deployment_name = 'utdeployment'
        self._create_hosted_service_with_deployment(
            self.hosted_service_name, deployment_name)
        result = self.sms.update_deployment_status(
            self.hosted_service_name, deployment_name, 'Running')
        self._wait_for_async(result.request_id)
        self._wait_for_deployment(self.hosted_service_name, deployment_name)
        self._wait_for_role(self.hosted_service_name, deployment_name,
                            role_instance_name)

        # Act
        result = self.sms.reimage_role_instance(
            self.hosted_service_name, deployment_name, role_instance_name)
        self._wait_for_async(result.request_id)

        # Assert
        props = self.sms.get_deployment_by_name(
            self.hosted_service_name, deployment_name)
        status = self._get_role_instance_status(props, role_instance_name)
        self.assertTrue(status == 'StoppedVM' or status == 'ReadyRole')

    def test_check_hosted_service_name_availability_not_available(self):
        # Arrange
        self._create_hosted_service(self.hosted_service_name)

        # Act
        result = self.sms.check_hosted_service_name_availability(
            self.hosted_service_name)

        # Assert
        self.assertIsNotNone(result)
        self.assertFalse(result.result)

    def test_check_hosted_service_name_availability_available(self):
        # Arrange

        # Act
        result = self.sms.check_hosted_service_name_availability(
            self.hosted_service_name)

        # Assert
        self.assertIsNotNone(result)
        self.assertTrue(result.result)

    #--Test cases for service certificates -------------------------------
    def test_list_service_certificates(self):
        # Arrange
        self._create_hosted_service(self.hosted_service_name)
        self._create_service_certificate(
            self.hosted_service_name, SERVICE_CERT_DATA, SERVICE_CERT_FORMAT, SERVICE_CERT_PASSWORD)

        # Act
        result = self.sms.list_service_certificates(self.hosted_service_name)

        # Assert
        self.assertIsNotNone(result)
        self.assertTrue(len(result) > 0)

        url_part = '/' + self.hosted_service_name + '/'
        cert = None
        for temp in result:
            if url_part in temp.certificate_url:
                cert = temp
                break

        self.assertIsNotNone(cert)
        self.assertIsNotNone(cert.certificate_url)
        self.assertEqual(cert.thumbprint, SERVICE_CERT_THUMBPRINT)
        self.assertEqual(cert.thumbprint_algorithm, SERVICE_CERT_THUMBALGO)
        self.assertEqual(cert.data, SERVICE_CERT_DATA_PUBLIC)

    def test_get_service_certificate(self):
        # Arrange
        self._create_hosted_service(self.hosted_service_name)
        self._create_service_certificate(
            self.hosted_service_name,
            SERVICE_CERT_DATA, SERVICE_CERT_FORMAT, SERVICE_CERT_PASSWORD)

        # Act
        result = self.sms.get_service_certificate(
            self.hosted_service_name,
            SERVICE_CERT_THUMBALGO, SERVICE_CERT_THUMBPRINT)

        # Assert
        self.assertIsNotNone(result)
        self.assertEqual(result.certificate_url, '')
        self.assertEqual(result.thumbprint, '')
        self.assertEqual(result.thumbprint_algorithm, '')
        self.assertEqual(result.data, SERVICE_CERT_DATA_PUBLIC)

    def test_add_service_certificate(self):
        # Arrange
        self._create_hosted_service(self.hosted_service_name)

        # Act
        result = self.sms.add_service_certificate(
            self.hosted_service_name,
            SERVICE_CERT_DATA, SERVICE_CERT_FORMAT, SERVICE_CERT_PASSWORD)
        self._wait_for_async(result.request_id)

        # Assert
        self.assertTrue(self._service_certificate_exists(
            self.hosted_service_name,
            SERVICE_CERT_THUMBALGO, SERVICE_CERT_THUMBPRINT))

    def test_delete_service_certificate(self):
        # Arrange
        self._create_hosted_service(self.hosted_service_name)
        self._create_service_certificate(
            self.hosted_service_name,
            SERVICE_CERT_DATA, SERVICE_CERT_FORMAT, SERVICE_CERT_PASSWORD)

        # Act
        result = self.sms.delete_service_certificate(
            self.hosted_service_name,
            SERVICE_CERT_THUMBALGO, SERVICE_CERT_THUMBPRINT)
        self._wait_for_async(result.request_id)

        # Assert
        self.assertFalse(self._service_certificate_exists(
            self.hosted_service_name,
            SERVICE_CERT_THUMBALGO, SERVICE_CERT_THUMBPRINT))

    #--Test cases for retrieving operating system information ------------
    def test_list_operating_systems(self):
        # Arrange

        # Act
        result = self.sms.list_operating_systems()

        # Assert
        self.assertIsNotNone(result)
        self.assertTrue(len(result) > 20)
        self.assertIsNotNone(result[0].family)
        self.assertIsNotNone(result[0].family_label)
        self.assertIsNotNone(result[0].is_active)
        self.assertIsNotNone(result[0].is_default)
        self.assertIsNotNone(result[0].label)
        self.assertIsNotNone(result[0].version)

    def test_list_operating_system_families(self):
        # Arrange

        # Act
        result = self.sms.list_operating_system_families()

        # Assert
        self.assertIsNotNone(result)
        self.assertTrue(len(result) > 0)
        self.assertIsNotNone(result[0].name)
        self.assertIsNotNone(result[0].label)
        self.assertTrue(len(result[0].operating_systems) > 0)
        self.assertIsNotNone(result[0].operating_systems[0].version)
        self.assertIsNotNone(result[0].operating_systems[0].label)
        self.assertIsNotNone(result[0].operating_systems[0].is_default)
        self.assertIsNotNone(result[0].operating_systems[0].is_active)

    #--Test cases for retrieving subscription history --------------------
    def test_get_subscription(self):
        # Arrange

        # Act
        result = self.sms.get_subscription()

        # Assert
        self.assertIsNotNone(result)
        self.assertEqual(result.subscription_id,
                         credentials.getSubscriptionId())
        self.assertIsNotNone(result.account_admin_live_email_id)
        self.assertIsNotNone(result.service_admin_live_email_id)
        self.assertIsNotNone(result.subscription_name)
        self.assertIsNotNone(result.subscription_status)
        self.assertTrue(result.current_core_count >= 0)
        self.assertTrue(result.current_hosted_services >= 0)
        self.assertTrue(result.current_storage_accounts >= 0)
        self.assertTrue(result.max_core_count > 0)
        self.assertTrue(result.max_dns_servers > 0)
        self.assertTrue(result.max_hosted_services > 0)
        self.assertTrue(result.max_local_network_sites > 0)
        self.assertTrue(result.max_storage_accounts > 0)
        self.assertTrue(result.max_virtual_network_sites > 0)

    #--Test cases for virtual machines -----------------------------------
    def test_get_role_linux(self):
        # Arrange
        service_name = self.hosted_service_name
        deployment_name = self.hosted_service_name
        role_name = self.hosted_service_name

        self._create_vm_linux(service_name, deployment_name, role_name)

        # Act
        result = self.sms.get_role(service_name, deployment_name, role_name)

        # Assert
        self.assertIsNotNone(result)
        self.assertEqual(result.role_name, role_name)
        self.assertIsNotNone(result.role_size)
        self.assertIsNotNone(result.role_type)
        self.assertIsNotNone(result.os_virtual_hard_disk)
        self.assertIsNotNone(result.os_virtual_hard_disk.disk_label)
        self.assertIsNotNone(result.os_virtual_hard_disk.disk_name)
        self.assertIsNotNone(result.os_virtual_hard_disk.host_caching)
        self.assertIsNotNone(result.os_virtual_hard_disk.media_link)
        self.assertIsNotNone(result.os_virtual_hard_disk.os)
        self.assertIsNotNone(result.os_virtual_hard_disk.source_image_name)
        self.assertIsNotNone(result.data_virtual_hard_disks)
        self.assertIsNotNone(result.configuration_sets)
        self.assertIsNotNone(result.configuration_sets[0])
        self.assertIsNotNone(
            result.configuration_sets[0].configuration_set_type)
        self.assertIsNotNone(result.configuration_sets[0].input_endpoints)
        self.assertIsNotNone(
            result.configuration_sets[0].input_endpoints[0].protocol)
        self.assertIsNotNone(
            result.configuration_sets[0].input_endpoints[0].port)
        self.assertIsNotNone(
            result.configuration_sets[0].input_endpoints[0].name)
        self.assertIsNotNone(
            result.configuration_sets[0].input_endpoints[0].local_port)

    def test_get_role_windows(self):
        # Arrange
        service_name = self.hosted_service_name
        deployment_name = self.hosted_service_name
        role_name = self.hosted_service_name

        self._create_vm_windows(service_name, deployment_name, role_name)

        # Act
        result = self.sms.get_role(service_name, deployment_name, role_name)

        # Assert
        self.assertIsNotNone(result)
        self.assertEqual(result.role_name, role_name)
        self.assertIsNotNone(result.role_size)
        self.assertIsNotNone(result.role_type)
        self.assertIsNotNone(result.os_virtual_hard_disk)
        self.assertIsNotNone(result.os_virtual_hard_disk.disk_label)
        self.assertIsNotNone(result.os_virtual_hard_disk.disk_name)
        self.assertIsNotNone(result.os_virtual_hard_disk.host_caching)
        self.assertIsNotNone(result.os_virtual_hard_disk.media_link)
        self.assertIsNotNone(result.os_virtual_hard_disk.os)
        self.assertIsNotNone(result.os_virtual_hard_disk.source_image_name)
        self.assertIsNotNone(result.data_virtual_hard_disks)
        self.assertIsNotNone(result.configuration_sets)
        self.assertIsNotNone(result.configuration_sets[0])
        self.assertIsNotNone(
            result.configuration_sets[0].configuration_set_type)
        self.assertIsNotNone(result.configuration_sets[0].input_endpoints)
        self.assertIsNotNone(
            result.configuration_sets[0].input_endpoints[0].protocol)
        self.assertIsNotNone(
            result.configuration_sets[0].input_endpoints[0].port)
        self.assertIsNotNone(
            result.configuration_sets[0].input_endpoints[0].name)
        self.assertIsNotNone(
            result.configuration_sets[0].input_endpoints[0].local_port)
        self.assertTrue(len(result.default_win_rm_certificate_thumbprint) > 0)

    def test_create_virtual_machine_deployment_linux(self):
        # Arrange
        service_name = self.hosted_service_name
        deployment_name = self.hosted_service_name
        role_name = self.hosted_service_name
        deployment_label = deployment_name + 'label'

        self._create_hosted_service(service_name)
        self._create_service_certificate(
            service_name,
            SERVICE_CERT_DATA, SERVICE_CERT_FORMAT, SERVICE_CERT_PASSWORD)

        # Act
        system, os_hd, network = self._linux_role(role_name)

        result = self.sms.create_virtual_machine_deployment(
            service_name, deployment_name, 'production', deployment_label,
            role_name, system, os_hd, network, role_size='Small')

        self._wait_for_async(result.request_id)
        self._wait_for_deployment(service_name, deployment_name)
        self._wait_for_role(service_name, deployment_name, role_name)

        # Assert
        self.assertTrue(
            self._role_exists(service_name, deployment_name, role_name))
        deployment = self.sms.get_deployment_by_name(
            service_name, deployment_name)
        self.assertEqual(deployment.label, deployment_label)

    def test_create_virtual_machine_deployment_windows(self):
        # Arrange
        service_name = self.hosted_service_name
        deployment_name = self.hosted_service_name
        role_name = self.hosted_service_name
        deployment_label = deployment_name + 'label'

        self._create_hosted_service(service_name)
        self._create_service_certificate(
            service_name,
            SERVICE_CERT_DATA, SERVICE_CERT_FORMAT, SERVICE_CERT_PASSWORD)

        # Act
        system, os_hd, network = self._windows_role(role_name)

        result = self.sms.create_virtual_machine_deployment(
            service_name, deployment_name, 'production', deployment_label,
            role_name, system, os_hd, network, role_size='Small')

        self._wait_for_async(result.request_id)
        self._wait_for_deployment(service_name, deployment_name)
        self._wait_for_role(service_name, deployment_name, role_name)

        # Assert
        self.assertTrue(
            self._role_exists(service_name, deployment_name, role_name))
        deployment = self.sms.get_deployment_by_name(
            service_name, deployment_name)
        self.assertEqual(deployment.label, deployment_label)

    def test_create_virtual_machine_deployment_windows_virtual_network(self):
        # this test requires the following manual resources to be created
        # use the azure portal to create them
        affinity_group = 'utaffgrpdonotdelete'    # affinity group, any region
        # storage account in affinity group
        storage_name = 'utstoragedonotdelete'
        # virtual network in affinity group
        virtual_network_name = 'utnetdonotdelete'
        subnet_name = 'Subnet-1'                  # subnet in virtual network

        # Arrange
        service_name = self.hosted_service_name
        deployment_name = self.hosted_service_name
        role_name = self.hosted_service_name
        deployment_label = deployment_name + 'label'

        self._create_hosted_service(
            service_name, affinity_group=affinity_group)
        self._create_service_certificate(
            service_name, SERVICE_CERT_DATA, 'pfx', SERVICE_CERT_PASSWORD)

        # Act
        system, os_hd, network = self._windows_role(role_name, subnet_name)

        result = self.sms.create_virtual_machine_deployment(
            service_name, deployment_name, 'production', deployment_label,
            role_name, system, os_hd, network,
            role_size='Small', virtual_network_name=virtual_network_name)

        self._wait_for_async(result.request_id)
        self._wait_for_deployment(service_name, deployment_name)
        self._wait_for_role(service_name, deployment_name, role_name)

        # Assert
        self.assertTrue(
            self._role_exists(service_name, deployment_name, role_name))
        deployment = self.sms.get_deployment_by_name(
            service_name, deployment_name)
        self.assertEqual(deployment.label, deployment_label)

    def test_add_role_linux(self):
        # Arrange
        service_name = self.hosted_service_name
        deployment_name = self.hosted_service_name
        role_name1 = self.hosted_service_name + 'a'
        role_name2 = self.hosted_service_name + 'b'

        self._create_vm_linux(service_name, deployment_name, role_name1)

        # Act
        system, os_hd, network = self._linux_role(role_name2, port='59914')
        network = None

        result = self.sms.add_role(service_name, deployment_name, role_name2,
                                   system, os_hd, network)
        self._wait_for_async(result.request_id)
        self._wait_for_role(service_name, deployment_name, role_name2)

        # Assert
        self.assertTrue(
            self._role_exists(service_name, deployment_name, role_name1))
        self.assertTrue(
            self._role_exists(service_name, deployment_name, role_name2))

        svc = self.sms.get_hosted_service_properties(service_name, True)
        role_instances = svc.deployments[0].role_instance_list
        self.assertEqual(role_instances[0].host_name,
                         self._host_name_from_role_name(role_name1))
        self.assertEqual(role_instances[1].host_name,
                         self._host_name_from_role_name(role_name2))

    def test_add_role_windows(self):
        # Arrange
        service_name = self.hosted_service_name
        deployment_name = self.hosted_service_name
        role_name1 = self.hosted_service_name + 'a'
        role_name2 = self.hosted_service_name + 'b'

        self._create_vm_windows(service_name, deployment_name, role_name1)

        # Act
        system, os_hd, network = self._windows_role(role_name2, port='59914')

        result = self.sms.add_role(service_name, deployment_name, role_name2, 
                                   system, os_hd, network)
        self._wait_for_async(result.request_id)
        self._wait_for_role(service_name, deployment_name, role_name2)

        # Assert
        self.assertTrue(
            self._role_exists(service_name, deployment_name, role_name1))
        self.assertTrue(
            self._role_exists(service_name, deployment_name, role_name2))

        svc = self.sms.get_hosted_service_properties(service_name, True)
        role_instances = svc.deployments[0].role_instance_list
        self.assertEqual(role_instances[0].host_name,
                         self._host_name_from_role_name(role_name1))
        self.assertEqual(role_instances[1].host_name,
                         self._host_name_from_role_name(role_name2))

    def test_update_role(self):
        service_name = self.hosted_service_name
        deployment_name = self.hosted_service_name
        role_name = self.hosted_service_name

        self._create_vm_windows(service_name, deployment_name, role_name)

        network = ConfigurationSet()
        network.configuration_set_type = 'NetworkConfiguration'
        network.input_endpoints.input_endpoints.append(
            ConfigurationSetInputEndpoint('endupdate', 'tcp', '50055', '5555'))

        # Act
        result = self.sms.update_role(service_name, deployment_name, role_name,
                                      network_config=network,
                                      role_size='Medium')
        self._wait_for_async(result.request_id)
        self._wait_for_role(service_name, deployment_name, role_name)

        # Assert
        role = self.sms.get_role(service_name, deployment_name, role_name)
        self.assertEqual(role.role_size, 'Medium')

    def test_delete_role(self):
        # Arrange
        service_name = self.hosted_service_name
        deployment_name = self.hosted_service_name
        role_name1 = self.hosted_service_name + 'a'
        role_name2 = self.hosted_service_name + 'b'

        self._create_vm_windows(service_name, deployment_name, role_name1)
        self._add_role_windows(service_name, deployment_name, role_name2, '59914')

        # Act
        result = self.sms.delete_role(service_name, deployment_name, role_name2)
        self._wait_for_async(result.request_id)

        # Assert
        self.assertTrue(
            self._role_exists(service_name, deployment_name, role_name1))
        self.assertFalse(
            self._role_exists(service_name, deployment_name, role_name2))

    def test_shutdown_start_and_restart_role(self):
        # Arrange
        service_name = self.hosted_service_name
        deployment_name = self.hosted_service_name
        role_name = self.hosted_service_name

        self._create_vm_windows(service_name, deployment_name, role_name)

        # Act
        result = self.sms.shutdown_role(service_name, deployment_name, role_name)
        self._wait_for_async(result.request_id)
        self._wait_for_role(service_name, deployment_name, role_name, 'StoppedVM')

        # Act
        result = self.sms.start_role(service_name, deployment_name, role_name)
        self._wait_for_async(result.request_id)
        self._wait_for_role(service_name, deployment_name, role_name)

        # Act
        result = self.sms.restart_role(service_name, deployment_name, role_name)
        self._wait_for_async(result.request_id)
        self._wait_for_role(service_name, deployment_name, role_name)

        # Act
        result = self.sms.shutdown_role(service_name, deployment_name,
                                        role_name, 'StoppedDeallocated')
        self._wait_for_async(result.request_id)
        self._wait_for_role(service_name, deployment_name, role_name,
                            'StoppedDeallocated')

    def test_shutdown_and_start_roles(self):
        # Arrange
        service_name = self.hosted_service_name
        deployment_name = self.hosted_service_name
        role_name1 = self.hosted_service_name + 'a'
        role_name2 = self.hosted_service_name + 'b'

        self._create_vm_windows(service_name, deployment_name, role_name1)
        self._add_role_windows(service_name, deployment_name, role_name2, '59914')

        # Act
        result = self.sms.shutdown_roles(service_name, deployment_name,
                                         [role_name1, role_name2])
        self._wait_for_async(result.request_id)
        self._wait_for_role(service_name, deployment_name, role_name1,
                            'StoppedVM')
        self._wait_for_role(service_name, deployment_name, role_name2,
                            'StoppedVM')

        # Act
        result = self.sms.start_roles(service_name, deployment_name,
                                      [role_name1, role_name2])
        self._wait_for_async(result.request_id)
        self._wait_for_role(service_name, deployment_name, role_name1)
        self._wait_for_role(service_name, deployment_name, role_name2)

    def test_capture_role(self):
        # Arrange
        service_name = self.hosted_service_name
        deployment_name = self.hosted_service_name
        role_name = self.hosted_service_name

        self._create_vm_windows(service_name, deployment_name, role_name)

        result = self.sms.shutdown_role(service_name, deployment_name, role_name)
        self._wait_for_async(result.request_id)
        self._wait_for_role(service_name, deployment_name, role_name, 'StoppedVM')

        image_name = self.os_image_name
        image_label = role_name + 'captured'

        # Act
        result = self.sms.capture_role(
            service_name, deployment_name, role_name, 'Delete', image_name,
            image_label)
        self._wait_for_async(result.request_id)

        # Assert
        self.assertTrue(self._os_image_exists(self.os_image_name))

    #--Test cases for virtual machine images -----------------------------
    def test_list_os_images(self):
        # Arrange
        media_url = LINUX_OS_VHD_URL
        os = 'Linux'
        self._create_os_image(self.os_image_name, media_url, os)

        # Act
        result = self.sms.list_os_images()

        # Assert
        self.assertIsNotNone(result)
        self.assertTrue(len(result) > 0)

        image = None
        for temp in result:
            if temp.name == self.os_image_name:
                image = temp
                break

        self.assertIsNotNone(image)
        self.assertIsNotNone(image.affinity_group)
        self.assertIsNotNone(image.category)
        self.assertIsNotNone(image.description)
        self.assertIsNotNone(image.eula)
        self.assertIsNotNone(image.label)
        self.assertIsNotNone(image.location)
        self.assertIsNotNone(image.logical_size_in_gb)
        self.assertEqual(image.media_link, media_url)
        self.assertEqual(image.name, self.os_image_name)
        self.assertEqual(image.os, os)

    def test_get_os_image(self):
        # Arrange
        media_url = LINUX_OS_VHD_URL
        os = 'Linux'
        self._create_os_image(self.os_image_name, media_url, os)

        # Act
        result = self.sms.get_os_image(self.os_image_name)

        # Assert
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.affinity_group)
        self.assertIsNotNone(result.category)
        self.assertIsNotNone(result.description)
        self.assertIsNotNone(result.eula)
        self.assertIsNotNone(result.label)
        self.assertIsNotNone(result.location)
        self.assertIsNotNone(result.logical_size_in_gb)
        self.assertEqual(result.media_link, media_url)
        self.assertEqual(result.name, self.os_image_name)
        self.assertEqual(result.os, os)

    def test_add_os_image(self):
        # Arrange

        # Act
        result = self.sms.add_os_image(
            'utcentosimg', LINUX_OS_VHD_URL, self.os_image_name, 'Linux')
        self._wait_for_async(result.request_id)

        # Assert
        self.assertTrue(self._os_image_exists(self.os_image_name))

    def test_update_os_image(self):
        # Arrange
        self._create_os_image(self.os_image_name, LINUX_OS_VHD_URL, 'Linux')

        # Act
        result = self.sms.update_os_image(
            self.os_image_name, 'newlabel', LINUX_OS_VHD_URL,
            self.os_image_name, 'Linux')
        self._wait_for_async(result.request_id)

        # Assert
        image = self.sms.get_os_image(self.os_image_name)
        self.assertEqual(image.label, 'newlabel')
        self.assertEqual(image.os, 'Linux')

    def test_delete_os_image(self):
        # Arrange
        self._create_os_image(self.os_image_name, LINUX_OS_VHD_URL, 'Linux')

        # Act
        result = self.sms.delete_os_image(self.os_image_name)
        self._wait_for_async(result.request_id)

        # Assert
        self.assertFalse(self._os_image_exists(self.os_image_name))

    #--Test cases for virtual machine disks ------------------------------
    def test_get_data_disk(self):
        # Arrange
        service_name = self.hosted_service_name
        deployment_name = self.hosted_service_name
        role_name = self.hosted_service_name

        self._create_vm_windows(service_name, deployment_name, role_name)

        lun = 1
        self._add_data_disk_from_blob_url(
            service_name, deployment_name, role_name, lun, 'mylabel')
        self.data_disk_info = (service_name, deployment_name, role_name, lun)

        # Act
        result = self.sms.get_data_disk(
            service_name, deployment_name, role_name, lun)

        # Assert
        self.assertIsNotNone(result)
        self.assertEqual(result.disk_label, 'mylabel')
        self.assertIsNotNone(result.disk_name)
        self.assertIsNotNone(result.host_caching)
        self.assertIsNotNone(result.logical_disk_size_in_gb)
        self.assertEqual(result.lun, lun)
        self.assertIsNotNone(result.media_link)

        service_props = self.sms.get_hosted_service_properties(service_name, True)
        hd = service_props.deployments[0].role_list[0].data_virtual_hard_disks[0]
        self.assertEqual(result.disk_label, hd.disk_label)
        self.assertEqual(result.disk_name, hd.disk_name)
        self.assertEqual(result.host_caching, hd.host_caching)
        self.assertEqual(result.logical_disk_size_in_gb, hd.logical_disk_size_in_gb)
        self.assertEqual(result.lun, hd.lun)
        self.assertEqual(result.media_link, hd.media_link)

    def test_add_data_disk_from_disk_name(self):
        # Arrange
        service_name = self.hosted_service_name
        deployment_name = self.hosted_service_name
        role_name = self.hosted_service_name

        self._create_vm_windows(service_name, deployment_name, role_name)

        lun = 2
        url = self._upload_disk_to_storage_blob('disk')
        self._create_disk(self.disk_name, 'Windows', url)
        self.data_disk_info = (service_name, deployment_name, role_name, lun)

        # Act
        result = self.sms.add_data_disk(
            service_name, deployment_name, role_name, lun, None, None,
            'testdisklabel', self.disk_name)
        self._wait_for_async(result.request_id)

        # Assert
        self.assertTrue(
            self._data_disk_exists(service_name, deployment_name,
                                   role_name, lun))

    def test_add_data_disk_from_blob_url(self):
        # Arrange
        service_name = self.hosted_service_name
        deployment_name = self.hosted_service_name
        role_name = self.hosted_service_name

        self._create_vm_windows(service_name, deployment_name, role_name)

        lun = 3
        label = 'disk' + str(lun)
        url = self._upload_disk_to_storage_blob('disk')
        self.data_disk_info = (service_name, deployment_name, role_name, lun)

        # Act
        result = self.sms.add_data_disk(
            service_name, deployment_name, role_name, lun, None, None, label,
            None, None, url)
        self._wait_for_async(result.request_id)

        # Assert
        self.assertTrue(
            self._data_disk_exists(service_name, deployment_name,
                                   role_name, lun))

    def test_update_data_disk(self):
        # Arrange
        service_name = self.hosted_service_name
        deployment_name = self.hosted_service_name
        role_name = self.hosted_service_name

        self._create_vm_windows(service_name, deployment_name, role_name)

        lun = 1
        updated_lun = 10
        self._add_data_disk_from_blob_url(
            service_name, deployment_name, role_name, lun, 'mylabel')
        self.data_disk_info = (service_name, deployment_name, role_name, lun)

        # Act
        result = self.sms.update_data_disk(
            service_name, deployment_name, role_name, lun, None, None,
            updated_lun)
        self._wait_for_async(result.request_id)
        self.data_disk_info = (
            service_name, deployment_name, role_name, updated_lun)

        # Assert
        self.assertFalse(
            self._data_disk_exists(service_name, deployment_name,
                                   role_name, lun))
        self.assertTrue(
            self._data_disk_exists(service_name, deployment_name,
                                   role_name, updated_lun))

    def test_delete_data_disk(self):
        # Arrange
        service_name = self.hosted_service_name
        deployment_name = self.hosted_service_name
        role_name = self.hosted_service_name

        self._create_vm_windows(service_name, deployment_name, role_name)

        lun = 5
        url = self._upload_disk_to_storage_blob('disk')
        self._create_disk(self.disk_name, 'Windows', url)
        result = self.sms.add_data_disk(
            service_name, deployment_name, role_name, lun, None, None,
            'testdisklabel', self.disk_name)
        self._wait_for_async(result.request_id)

        # Act
        result = self.sms.delete_data_disk(
            service_name, deployment_name, role_name, lun)
        self._wait_for_async(result.request_id)

        # Assert
        self.assertFalse(
            self._data_disk_exists(service_name, deployment_name,
                                   role_name, lun))

    #--Test cases for virtual machine disks ------------------------------
    def test_list_disks(self):
        # Arrange
        url = self._upload_disk_to_storage_blob('disk')
        self._create_disk(self.disk_name, 'Windows', url)

        # Act
        result = self.sms.list_disks()

        # Assert
        self.assertIsNotNone(result)
        self.assertTrue(len(result) > 0)

        disk = None
        for temp in result:
            if temp.name == self.disk_name:
                disk = temp
                break

        self.assertIsNotNone(disk)
        self.assertIsNotNone(disk.os)
        self.assertIsNotNone(disk.location)
        self.assertIsNotNone(disk.logical_disk_size_in_gb)
        self.assertIsNotNone(disk.media_link)
        self.assertIsNotNone(disk.name)
        self.assertIsNotNone(disk.source_image_name)

    def test_get_disk_unattached(self):
        # Arrange
        url = self._upload_disk_to_storage_blob('disk')
        self._create_disk(self.disk_name, 'Windows', url)

        # Act
        result = self.sms.get_disk(self.disk_name)

        # Assert
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.os)
        self.assertIsNotNone(result.location)
        self.assertIsNotNone(result.logical_disk_size_in_gb)
        self.assertEqual(result.media_link, url)
        self.assertEqual(result.name, self.disk_name)
        self.assertIsNotNone(result.source_image_name)
        self.assertIsNone(result.attached_to)

    def test_get_disk_attached(self):
        # Arrange
        service_name = self.hosted_service_name
        deployment_name = self.hosted_service_name
        role_name = self.hosted_service_name

        self._create_vm_windows(service_name, deployment_name, role_name)

        lun = 6
        url = self._upload_disk_to_storage_blob('disk')
        self._create_disk(self.disk_name, 'Windows', url)
        self.data_disk_info = (service_name, deployment_name, role_name, lun)
        result = self.sms.add_data_disk(
            service_name, deployment_name, role_name, lun, None, None,
            'testdisklabel', self.disk_name)
        self._wait_for_async(result.request_id)

        # Act
        result = self.sms.get_disk(self.disk_name)

        # Assert
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.os)
        self.assertIsNotNone(result.location)
        self.assertIsNotNone(result.logical_disk_size_in_gb)
        self.assertIsNotNone(result.media_link)
        self.assertIsNotNone(result.name)
        self.assertIsNotNone(result.source_image_name)
        self.assertIsNotNone(result.attached_to)
        self.assertEqual(result.attached_to.deployment_name, deployment_name)
        self.assertEqual(result.attached_to.hosted_service_name, service_name)
        self.assertEqual(result.attached_to.role_name, role_name)

    def test_add_disk(self):
        # Arrange
        url = self._upload_disk_to_storage_blob('disk')

        # Act
        result = self.sms.add_disk(
            False, 'ptvslabel', url, self.disk_name, 'Windows')

        # Assert
        self.assertIsNone(result)
        self.assertTrue(self._disk_exists(self.disk_name))

    def test_update_disk(self):
        # Arrange
        url = self._upload_disk_to_storage_blob('disk')
        urlupdate = self._upload_disk_to_storage_blob('diskupdate')
        self._create_disk(self.disk_name, 'Windows', url)

        # Act
        result = self.sms.update_disk(
            self.disk_name, False, 'ptvslabelupdate', urlupdate,
            self.disk_name, 'Windows')

        # Assert
        self.assertIsNone(result)
        disk = self.sms.get_disk(self.disk_name)
        self.assertEqual(disk.name, self.disk_name)
        self.assertEqual(disk.label, 'ptvslabelupdate')
        self.assertEqual(disk.media_link, url)

    def test_delete_disk(self):
        # Arrange
        url = self._upload_disk_to_storage_blob('disk')
        self._create_disk(self.disk_name, 'Windows', url)

        # Act
        result = self.sms.delete_disk(self.disk_name)

        # Assert
        self.assertIsNone(result)
        self.assertFalse(self._disk_exists(self.disk_name))


#------------------------------------------------------------------------------
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_sharedaccesssignature
#-------------------------------------------------------------------------
# Copyright (c) Microsoft.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#--------------------------------------------------------------------------
import unittest

from azure import (
    DEV_ACCOUNT_NAME,
    DEV_ACCOUNT_KEY,
    )
from azure.storage import AccessPolicy, X_MS_VERSION
from azure.storage.sharedaccesssignature import (
    Permission,
    SharedAccessPolicy,
    SharedAccessSignature,
    WebResource,
    RESOURCE_BLOB,
    RESOURCE_CONTAINER,
    SHARED_ACCESS_PERMISSION,
    SIGNED_EXPIRY,
    SIGNED_IDENTIFIER,
    SIGNED_PERMISSION,
    SIGNED_RESOURCE,
    SIGNED_RESOURCE_TYPE,
    SIGNED_SIGNATURE,
    SIGNED_START,
    )
from util import (
    AzureTestCase,
    credentials,
    getUniqueName,
    )

#------------------------------------------------------------------------------


class SharedAccessSignatureTest(AzureTestCase):

    def setUp(self):
        self.sas = SharedAccessSignature(account_name=DEV_ACCOUNT_NAME,
                                         account_key=DEV_ACCOUNT_KEY)

    def tearDown(self):
        return super(SharedAccessSignatureTest, self).tearDown()

    def test_generate_signature_container(self):
        accss_plcy = AccessPolicy()
        accss_plcy.start = '2011-10-11'
        accss_plcy.expiry = '2011-10-12'
        accss_plcy.permission = 'r'
        signed_identifier = 'YWJjZGVmZw=='
        sap = SharedAccessPolicy(accss_plcy, signed_identifier)
        signature = self.sas._generate_signature('images',
                                                 sap,
                                                 X_MS_VERSION)
        self.assertEqual(signature,
                         '1AWckmWSNrNCjh9krPXoD4exAgZWQQr38gG6z/ymkhQ=')

    def test_generate_signature_blob(self):
        accss_plcy = AccessPolicy()
        accss_plcy.start = '2011-10-11T11:03:40Z'
        accss_plcy.expiry = '2011-10-12T11:53:40Z'
        accss_plcy.permission = 'r'
        sap = SharedAccessPolicy(accss_plcy)

        signature = self.sas._generate_signature('images/pic1.png',
                                                 sap,
                                                 X_MS_VERSION)
        self.assertEqual(signature,
                         'ju4tX0G79vPxMOkBb7UfNVEgrj9+ZnSMutpUemVYHLY=')

    def test_blob_signed_query_string(self):
        accss_plcy = AccessPolicy()
        accss_plcy.start = '2011-10-11'
        accss_plcy.expiry = '2011-10-12'
        accss_plcy.permission = 'w'
        sap = SharedAccessPolicy(accss_plcy)
        qry_str = self.sas.generate_signed_query_string('images/pic1.png',
                                                        RESOURCE_BLOB,
                                                        sap)
        self.assertEqual(qry_str[SIGNED_START], '2011-10-11')
        self.assertEqual(qry_str[SIGNED_EXPIRY], '2011-10-12')
        self.assertEqual(qry_str[SIGNED_RESOURCE], RESOURCE_BLOB)
        self.assertEqual(qry_str[SIGNED_PERMISSION], 'w')
        self.assertEqual(qry_str[SIGNED_SIGNATURE],
                         '8I8E8TImfR2TIAcMDq8rF+IhhYyvowXpxSfF1kxnWLQ=')

    def test_container_signed_query_string(self):
        accss_plcy = AccessPolicy()
        accss_plcy.start = '2011-10-11'
        accss_plcy.expiry = '2011-10-12'
        accss_plcy.permission = 'r'
        signed_identifier = 'YWJjZGVmZw=='
        sap = SharedAccessPolicy(accss_plcy, signed_identifier)
        qry_str = self.sas.generate_signed_query_string('images',
                                                        RESOURCE_CONTAINER,
                                                        sap)
        self.assertEqual(qry_str[SIGNED_START], '2011-10-11')
        self.assertEqual(qry_str[SIGNED_EXPIRY], '2011-10-12')
        self.assertEqual(qry_str[SIGNED_RESOURCE], RESOURCE_CONTAINER)
        self.assertEqual(qry_str[SIGNED_PERMISSION], 'r')
        self.assertEqual(qry_str[SIGNED_IDENTIFIER], 'YWJjZGVmZw==')
        self.assertEqual(qry_str[SIGNED_SIGNATURE],
                         '1AWckmWSNrNCjh9krPXoD4exAgZWQQr38gG6z/ymkhQ=')

    def test_sign_request(self):
        accss_plcy = AccessPolicy()
        accss_plcy.start = '2011-10-11'
        accss_plcy.expiry = '2011-10-12'
        accss_plcy.permission = 'r'
        sap = SharedAccessPolicy(accss_plcy)
        qry_str = self.sas.generate_signed_query_string('images/pic1.png',
                                                        RESOURCE_BLOB,
                                                        sap)

        permission = Permission()
        permission.path = '/images/pic1.png'
        permission.query_string = qry_str
        self.sas.permission_set = [permission]

        web_rsrc = WebResource()
        web_rsrc.properties[SIGNED_RESOURCE_TYPE] = RESOURCE_BLOB
        web_rsrc.properties[SHARED_ACCESS_PERMISSION] = 'r'
        web_rsrc.path = '/images/pic1.png?comp=metadata'
        web_rsrc.request_url = '/images/pic1.png?comp=metadata'

        web_rsrc = self.sas.sign_request(web_rsrc)

        self.assertEqual(web_rsrc.request_url,
                         '/images/pic1.png?comp=metadata&' +
                         self.sas._convert_query_string(qry_str))

#------------------------------------------------------------------------------
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_storagemanagementservice
﻿# coding: utf-8

#-------------------------------------------------------------------------
# Copyright (c) Microsoft.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#--------------------------------------------------------------------------
import time
import unittest

from azure import WindowsAzureError
from azure.servicemanagement import ServiceManagementService
from util import (
    AzureTestCase,
    credentials,
    getUniqueName,
    set_service_options,
    )

#------------------------------------------------------------------------------


class StorageManagementServiceTest(AzureTestCase):

    def setUp(self):
        self.sms = ServiceManagementService(credentials.getSubscriptionId(),
                                            credentials.getManagementCertFile())
        set_service_options(self.sms)

        self.storage_account_name = getUniqueName('utstor')

    def tearDown(self):
        try:
            self.sms.delete_storage_account(self.storage_account_name)
        except:
            pass

    #--Helpers-----------------------------------------------------------------
    def _wait_for_async(self, request_id):
        count = 0
        result = self.sms.get_operation_status(request_id)
        while result.status == 'InProgress':
            count = count + 1
            if count > 120:
                self.assertTrue(
                    False, 'Timed out waiting for async operation to complete.')
            time.sleep(5)
            result = self.sms.get_operation_status(request_id)
        self.assertEqual(result.status, 'Succeeded')

    def _create_storage_account(self, name):
        result = self.sms.create_storage_account(
            name,
            name + 'description',
            name + 'label',
            None,
            'West US',
            False,
            {'ext1': 'val1', 'ext2': 42})
        self._wait_for_async(result.request_id)

    def _storage_account_exists(self, name):
        try:
            props = self.sms.get_storage_account_properties(name)
            return props is not None
        except:
            return False

    #--Test cases for storage accounts -----------------------------------
    def test_list_storage_accounts(self):
        # Arrange
        self._create_storage_account(self.storage_account_name)

        # Act
        result = self.sms.list_storage_accounts()

        # Assert
        self.assertIsNotNone(result)
        self.assertTrue(len(result) > 0)

        storage = None
        for temp in result:
            if temp.service_name == self.storage_account_name:
                storage = temp
                break

        self.assertIsNotNone(storage)
        self.assertIsNotNone(storage.service_name)
        self.assertIsNone(storage.storage_service_keys)
        self.assertIsNotNone(storage.storage_service_properties)
        self.assertIsNotNone(storage.storage_service_properties.affinity_group)
        self.assertIsNotNone(storage.storage_service_properties.description)
        self.assertIsNotNone(
            storage.storage_service_properties.geo_primary_region)
        self.assertIsNotNone(
            storage.storage_service_properties.geo_replication_enabled)
        self.assertIsNotNone(
            storage.storage_service_properties.geo_secondary_region)
        self.assertIsNotNone(storage.storage_service_properties.label)
        self.assertIsNotNone(
            storage.storage_service_properties.last_geo_failover_time)
        self.assertIsNotNone(storage.storage_service_properties.location)
        self.assertIsNotNone(storage.storage_service_properties.status)
        self.assertIsNotNone(
            storage.storage_service_properties.status_of_primary)
        self.assertIsNotNone(
            storage.storage_service_properties.status_of_secondary)
        self.assertIsNotNone(storage.storage_service_properties.endpoints)
        self.assertTrue(len(storage.storage_service_properties.endpoints) > 0)
        self.assertIsNotNone(storage.extended_properties)
        self.assertTrue(len(storage.extended_properties) > 0)

    def test_get_storage_account_properties(self):
        # Arrange
        self._create_storage_account(self.storage_account_name)

        # Act
        result = self.sms.get_storage_account_properties(
            self.storage_account_name)

        # Assert
        self.assertIsNotNone(result)
        self.assertEqual(result.service_name, self.storage_account_name)
        self.assertIsNotNone(result.url)
        self.assertIsNone(result.storage_service_keys)
        self.assertIsNotNone(result.storage_service_properties)
        self.assertIsNotNone(result.storage_service_properties.affinity_group)
        self.assertIsNotNone(result.storage_service_properties.description)
        self.assertIsNotNone(
            result.storage_service_properties.geo_primary_region)
        self.assertIsNotNone(
            result.storage_service_properties.geo_replication_enabled)
        self.assertIsNotNone(
            result.storage_service_properties.geo_secondary_region)
        self.assertIsNotNone(result.storage_service_properties.label)
        self.assertIsNotNone(
            result.storage_service_properties.last_geo_failover_time)
        self.assertIsNotNone(result.storage_service_properties.location)
        self.assertIsNotNone(result.storage_service_properties.status)
        self.assertIsNotNone(
            result.storage_service_properties.status_of_primary)
        self.assertIsNotNone(
            result.storage_service_properties.status_of_secondary)
        self.assertIsNotNone(result.storage_service_properties.endpoints)
        self.assertTrue(len(result.storage_service_properties.endpoints) > 0)
        self.assertIsNotNone(result.extended_properties)
        self.assertTrue(len(result.extended_properties) > 0)
        self.assertIsNotNone(result.capabilities)
        self.assertTrue(len(result.capabilities) > 0)

    def test_get_storage_account_keys(self):
        # Arrange
        self._create_storage_account(self.storage_account_name)

        # Act
        result = self.sms.get_storage_account_keys(self.storage_account_name)

        # Assert
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.url)
        self.assertIsNotNone(result.service_name)
        self.assertIsNotNone(result.storage_service_keys.primary)
        self.assertIsNotNone(result.storage_service_keys.secondary)
        self.assertIsNone(result.storage_service_properties)

    def test_regenerate_storage_account_keys(self):
        # Arrange
        self._create_storage_account(self.storage_account_name)
        previous = self.sms.get_storage_account_keys(self.storage_account_name)

        # Act
        result = self.sms.regenerate_storage_account_keys(
            self.storage_account_name, 'Secondary')

        # Assert
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.url)
        self.assertIsNotNone(result.service_name)
        self.assertIsNotNone(result.storage_service_keys.primary)
        self.assertIsNotNone(result.storage_service_keys.secondary)
        self.assertIsNone(result.storage_service_properties)
        self.assertEqual(result.storage_service_keys.primary,
                         previous.storage_service_keys.primary)
        self.assertNotEqual(result.storage_service_keys.secondary,
                            previous.storage_service_keys.secondary)

    def test_create_storage_account(self):
        # Arrange
        description = self.storage_account_name + 'description'
        label = self.storage_account_name + 'label'

        # Act
        result = self.sms.create_storage_account(
            self.storage_account_name,
            description,
            label,
            None,
            'West US',
            True,
            {'ext1': 'val1', 'ext2': 42})
        self._wait_for_async(result.request_id)

        # Assert
        self.assertTrue(
            self._storage_account_exists(self.storage_account_name))

    def test_update_storage_account(self):
        # Arrange
        self._create_storage_account(self.storage_account_name)
        description = self.storage_account_name + 'descriptionupdate'
        label = self.storage_account_name + 'labelupdate'

        # Act
        result = self.sms.update_storage_account(
            self.storage_account_name,
            description,
            label,
            False,
            {'ext1': 'val1update', 'ext2': 53, 'ext3': 'brandnew'})

        # Assert
        self.assertIsNone(result)
        props = self.sms.get_storage_account_properties(
            self.storage_account_name)
        self.assertEqual(
            props.storage_service_properties.description, description)
        self.assertEqual(props.storage_service_properties.label, label)
        self.assertEqual(props.extended_properties['ext1'], 'val1update')
        self.assertEqual(props.extended_properties['ext2'], '53')
        self.assertEqual(props.extended_properties['ext3'], 'brandnew')

    def test_delete_storage_account(self):
        # Arrange
        self._create_storage_account(self.storage_account_name)

        # Act
        result = self.sms.delete_storage_account(self.storage_account_name)

        # Assert
        self.assertIsNone(result)
        self.assertFalse(
            self._storage_account_exists(self.storage_account_name))

    def test_check_storage_account_name_availability_not_available(self):
        # Arrange
        self._create_storage_account(self.storage_account_name)

        # Act
        result = self.sms.check_storage_account_name_availability(
            self.storage_account_name)

        # Assert
        self.assertIsNotNone(result)
        self.assertFalse(result.result)

    def test_check_storage_account_name_availability_available(self):
        # Arrange

        # Act
        result = self.sms.check_storage_account_name_availability(
            self.storage_account_name)

        # Assert
        self.assertIsNotNone(result)
        self.assertTrue(result.result)

    def test_unicode_create_storage_account_unicode_name(self):
        # Arrange
        self.storage_account_name = self.storage_account_name + u'啊齄丂狛狜'
        description = 'description'
        label = 'label'

        # Act
        with self.assertRaises(WindowsAzureError):
            # not supported - queue name must be alphanumeric, lowercase
            result = self.sms.create_storage_account(
                self.storage_account_name,
                description,
                label,
                None,
                'West US',
                True,
                {'ext1': 'val1', 'ext2': 42})
            self._wait_for_async(result.request_id)

        # Assert

    def test_unicode_create_storage_account_unicode_description_label(self):
        # Arrange
        description = u'啊齄丂狛狜'
        label = u'丂狛狜'

        # Act
        result = self.sms.create_storage_account(
            self.storage_account_name,
            description,
            label,
            None,
            'West US',
            True,
            {'ext1': 'val1', 'ext2': 42})
        self._wait_for_async(result.request_id)

        # Assert
        result = self.sms.get_storage_account_properties(
            self.storage_account_name)
        self.assertEqual(
            result.storage_service_properties.description, description)
        self.assertEqual(result.storage_service_properties.label, label)

    def test_unicode_create_storage_account_unicode_property_value(self):
        # Arrange
        description = 'description'
        label = 'label'

        # Act
        result = self.sms.create_storage_account(
            self.storage_account_name,
            description,
            label,
            None,
            'West US',
            True,
            {'ext1': u'丂狛狜', 'ext2': 42})
        self._wait_for_async(result.request_id)

        # Assert
        result = self.sms.get_storage_account_properties(
            self.storage_account_name)
        self.assertEqual(
            result.storage_service_properties.description, description)
        self.assertEqual(result.storage_service_properties.label, label)
        self.assertEqual(result.extended_properties['ext1'], u'丂狛狜')

#------------------------------------------------------------------------------
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_tableservice
﻿# coding: utf-8

#-------------------------------------------------------------------------
# Copyright (c) Microsoft.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#--------------------------------------------------------------------------
import base64
import time
import unittest

from datetime import datetime
from azure import WindowsAzureError, WindowsAzureBatchOperationError
from azure.storage import (
    Entity,
    EntityProperty,
    StorageServiceProperties,
    TableService,
    )
from util import (
    AzureTestCase,
    credentials,
    getUniqueName,
    set_service_options,
    )

#------------------------------------------------------------------------------

MAX_RETRY = 60
#------------------------------------------------------------------------------


class TableServiceTest(AzureTestCase):

    def setUp(self):
        self.ts = TableService(credentials.getStorageServicesName(),
                               credentials.getStorageServicesKey())
        set_service_options(self.ts)

        self.table_name = getUniqueName('uttable')
        self.additional_table_names = []

    def tearDown(self):
        self.cleanup()
        return super(TableServiceTest, self).tearDown()

    def cleanup(self):
        try:
            self.ts.delete_table(self.table_name)
        except:
            pass

        for name in self.additional_table_names:
            try:
                self.ts.delete_table(name)
            except:
                pass

    #--Helpers-----------------------------------------------------------------
    def _create_table(self, table_name):
        '''
        Creates a table with the specified name.
        '''
        self.ts.create_table(table_name, True)

    def _create_table_with_default_entities(self, table_name, entity_count):
        '''
        Creates a table with the specified name and adds entities with the
        default set of values. PartitionKey is set to 'MyPartition' and RowKey
        is set to a unique counter value starting at 1 (as a string).
        '''
        entities = []
        self._create_table(table_name)
        for i in range(1, entity_count + 1):
            entities.append(self.ts.insert_entity(
                table_name,
                self._create_default_entity_dict('MyPartition', str(i))))
        return entities

    def _create_default_entity_class(self, partition, row):
        '''
        Creates a class-based entity with fixed values, using all
        of the supported data types.
        '''
        entity = Entity()
        entity.PartitionKey = partition
        entity.RowKey = row
        entity.age = 39
        entity.sex = 'male'
        entity.married = True
        entity.deceased = False
        entity.optional = None
        entity.ratio = 3.1
        entity.large = 9333111000
        entity.Birthday = datetime(1973, 10, 4)
        entity.birthday = datetime(1970, 10, 4)
        entity.binary = None
        entity.other = EntityProperty('Edm.Int64', 20)
        entity.clsid = EntityProperty(
            'Edm.Guid', 'c9da6455-213d-42c9-9a79-3e9149a57833')
        return entity

    def _create_default_entity_dict(self, partition, row):
        '''
        Creates a dictionary-based entity with fixed values, using all
        of the supported data types.
        '''
        return {'PartitionKey': partition,
                'RowKey': row,
                'age': 39,
                'sex': 'male',
                'married': True,
                'deceased': False,
                'optional': None,
                'ratio': 3.1,
                'large': 9333111000,
                'Birthday': datetime(1973, 10, 4),
                'birthday': datetime(1970, 10, 4),
                'other': EntityProperty('Edm.Int64', 20),
                'clsid': EntityProperty(
                    'Edm.Guid',
                    'c9da6455-213d-42c9-9a79-3e9149a57833')}

    def _create_updated_entity_dict(self, partition, row):
        '''
        Creates a dictionary-based entity with fixed values, with a
        different set of values than the default entity. It
        adds fields, changes field values, changes field types,
        and removes fields when compared to the default entity.
        '''
        return {'PartitionKey': partition,
                'RowKey': row,
                'age': 'abc',
                'sex': 'female',
                'sign': 'aquarius',
                'birthday': datetime(1991, 10, 4)}

    def _assert_default_entity(self, entity):
        '''
        Asserts that the entity passed in matches the default entity.
        '''
        self.assertEqual(entity.age, 39)
        self.assertEqual(entity.sex, 'male')
        self.assertEqual(entity.married, True)
        self.assertEqual(entity.deceased, False)
        self.assertFalse(hasattr(entity, "aquarius"))
        self.assertEqual(entity.ratio, 3.1)
        self.assertEqual(entity.large, 9333111000)
        self.assertEqual(entity.Birthday, datetime(1973, 10, 4))
        self.assertEqual(entity.birthday, datetime(1970, 10, 4))
        self.assertEqual(entity.other, 20)
        self.assertIsInstance(entity.clsid, EntityProperty)
        self.assertEqual(entity.clsid.type, 'Edm.Guid')
        self.assertEqual(entity.clsid.value,
                         'c9da6455-213d-42c9-9a79-3e9149a57833')

    def _assert_updated_entity(self, entity):
        '''
        Asserts that the entity passed in matches the updated entity.
        '''
        self.assertEqual(entity.age, 'abc')
        self.assertEqual(entity.sex, 'female')
        self.assertFalse(hasattr(entity, "married"))
        self.assertFalse(hasattr(entity, "deceased"))
        self.assertEqual(entity.sign, 'aquarius')
        self.assertFalse(hasattr(entity, "optional"))
        self.assertFalse(hasattr(entity, "ratio"))
        self.assertFalse(hasattr(entity, "large"))
        self.assertFalse(hasattr(entity, "Birthday"))
        self.assertEqual(entity.birthday, datetime(1991, 10, 4))
        self.assertFalse(hasattr(entity, "other"))
        self.assertFalse(hasattr(entity, "clsid"))

    def _assert_merged_entity(self, entity):
        '''
        Asserts that the entity passed in matches the default entity
        merged with the updated entity.
        '''
        self.assertEqual(entity.age, 'abc')
        self.assertEqual(entity.sex, 'female')
        self.assertEqual(entity.sign, 'aquarius')
        self.assertEqual(entity.married, True)
        self.assertEqual(entity.deceased, False)
        self.assertEqual(entity.sign, 'aquarius')
        self.assertEqual(entity.ratio, 3.1)
        self.assertEqual(entity.large, 9333111000)
        self.assertEqual(entity.Birthday, datetime(1973, 10, 4))
        self.assertEqual(entity.birthday, datetime(1991, 10, 4))
        self.assertEqual(entity.other, 20)
        self.assertIsInstance(entity.clsid, EntityProperty)
        self.assertEqual(entity.clsid.type, 'Edm.Guid')
        self.assertEqual(entity.clsid.value,
                         'c9da6455-213d-42c9-9a79-3e9149a57833')

    #--Test cases for table service -------------------------------------------
    def test_get_set_table_service_properties(self):
        table_properties = self.ts.get_table_service_properties()
        self.ts.set_table_service_properties(table_properties)

        tests = [('logging.delete', True),
                 ('logging.delete', False),
                 ('logging.read', True),
                 ('logging.read', False),
                 ('logging.write', True),
                 ('logging.write', False),
                 ]
        for path, value in tests:
            # print path
            cur = table_properties
            for component in path.split('.')[:-1]:
                cur = getattr(cur, component)

            last_attr = path.split('.')[-1]
            setattr(cur, last_attr, value)
            self.ts.set_table_service_properties(table_properties)

            retry_count = 0
            while retry_count < MAX_RETRY:
                table_properties = self.ts.get_table_service_properties()
                cur = table_properties
                for component in path.split('.'):
                    cur = getattr(cur, component)
                if value == cur:
                    break
                time.sleep(1)
                retry_count += 1

            self.assertEqual(value, cur)

    def test_table_service_retention_single_set(self):
        table_properties = self.ts.get_table_service_properties()
        table_properties.logging.retention_policy.enabled = False
        table_properties.logging.retention_policy.days = 5

        # TODO: Better error, ValueError?
        self.assertRaises(WindowsAzureError,
                          self.ts.set_table_service_properties,
                          table_properties)

        table_properties = self.ts.get_table_service_properties()
        table_properties.logging.retention_policy.days = None
        table_properties.logging.retention_policy.enabled = True

        # TODO: Better error, ValueError?
        self.assertRaises(WindowsAzureError,
                          self.ts.set_table_service_properties,
                          table_properties)

    def test_table_service_set_both(self):
        table_properties = self.ts.get_table_service_properties()
        table_properties.logging.retention_policy.enabled = True
        table_properties.logging.retention_policy.days = 5
        self.ts.set_table_service_properties(table_properties)
        table_properties = self.ts.get_table_service_properties()
        self.assertEqual(
            True, table_properties.logging.retention_policy.enabled)

        self.assertEqual(5, table_properties.logging.retention_policy.days)

    #--Test cases for tables --------------------------------------------------
    def test_create_table(self):
        # Arrange

        # Act
        created = self.ts.create_table(self.table_name)

        # Assert
        self.assertTrue(created)

    def test_create_table_fail_on_exist(self):
        # Arrange

        # Act
        created = self.ts.create_table(self.table_name, True)

        # Assert
        self.assertTrue(created)

    def test_create_table_with_already_existing_table(self):
        # Arrange

        # Act
        created1 = self.ts.create_table(self.table_name)
        created2 = self.ts.create_table(self.table_name)

        # Assert
        self.assertTrue(created1)
        self.assertFalse(created2)

    def test_create_table_with_already_existing_table_fail_on_exist(self):
        # Arrange

        # Act
        created = self.ts.create_table(self.table_name)
        with self.assertRaises(WindowsAzureError):
            self.ts.create_table(self.table_name, True)

        # Assert
        self.assertTrue(created)

    def test_query_tables(self):
        # Arrange
        self._create_table(self.table_name)

        # Act
        tables = self.ts.query_tables()
        for table in tables:
            pass

        # Assert
        tableNames = [x.name for x in tables]
        self.assertGreaterEqual(len(tableNames), 1)
        self.assertGreaterEqual(len(tables), 1)
        self.assertIn(self.table_name, tableNames)

    def test_query_tables_with_table_name(self):
        # Arrange
        self._create_table(self.table_name)

        # Act
        tables = self.ts.query_tables(self.table_name)
        for table in tables:
            pass

        # Assert
        self.assertEqual(len(tables), 1)
        self.assertEqual(tables[0].name, self.table_name)

    def test_query_tables_with_table_name_no_tables(self):
        # Arrange

        # Act
        with self.assertRaises(WindowsAzureError):
            self.ts.query_tables(self.table_name)

        # Assert

    def test_query_tables_with_top(self):
        # Arrange
        self.additional_table_names = [
            self.table_name + suffix for suffix in 'abcd']
        for name in self.additional_table_names:
            self.ts.create_table(name)

        # Act
        tables = self.ts.query_tables(None, 3)
        for table in tables:
            pass

        # Assert
        self.assertEqual(len(tables), 3)

    def test_query_tables_with_top_and_next_table_name(self):
        # Arrange
        self.additional_table_names = [
            self.table_name + suffix for suffix in 'abcd']
        for name in self.additional_table_names:
            self.ts.create_table(name)

        # Act
        tables_set1 = self.ts.query_tables(None, 3)
        tables_set2 = self.ts.query_tables(
            None, 3, tables_set1.x_ms_continuation['NextTableName'])

        # Assert
        self.assertEqual(len(tables_set1), 3)
        self.assertGreaterEqual(len(tables_set2), 1)
        self.assertLessEqual(len(tables_set2), 3)

    def test_delete_table_with_existing_table(self):
        # Arrange
        self._create_table(self.table_name)

        # Act
        deleted = self.ts.delete_table(self.table_name)

        # Assert
        self.assertTrue(deleted)
        tables = self.ts.query_tables()
        self.assertNamedItemNotInContainer(tables, self.table_name)

    def test_delete_table_with_existing_table_fail_not_exist(self):
        # Arrange
        self._create_table(self.table_name)

        # Act
        deleted = self.ts.delete_table(self.table_name, True)

        # Assert
        self.assertTrue(deleted)
        tables = self.ts.query_tables()
        self.assertNamedItemNotInContainer(tables, self.table_name)

    def test_delete_table_with_non_existing_table(self):
        # Arrange

        # Act
        deleted = self.ts.delete_table(self.table_name)

        # Assert
        self.assertFalse(deleted)

    def test_delete_table_with_non_existing_table_fail_not_exist(self):
        # Arrange

        # Act
        with self.assertRaises(WindowsAzureError):
            self.ts.delete_table(self.table_name, True)

        # Assert

    #--Test cases for entities ------------------------------------------
    def test_insert_entity_dictionary(self):
        # Arrange
        self._create_table(self.table_name)

        # Act
        dict = self._create_default_entity_dict('MyPartition', '1')
        resp = self.ts.insert_entity(self.table_name, dict)

        # Assert
        self.assertIsNotNone(resp)

    def test_insert_entity_class_instance(self):
        # Arrange
        self._create_table(self.table_name)

        # Act
        entity = self._create_default_entity_class('MyPartition', '1')
        resp = self.ts.insert_entity(self.table_name, entity)

        # Assert
        self.assertIsNotNone(resp)

    def test_insert_entity_conflict(self):
        # Arrange
        self._create_table_with_default_entities(self.table_name, 1)

        # Act
        with self.assertRaises(WindowsAzureError):
            self.ts.insert_entity(
                self.table_name,
                self._create_default_entity_dict('MyPartition', '1'))

        # Assert

    def test_get_entity(self):
        # Arrange
        self._create_table_with_default_entities(self.table_name, 1)

        # Act
        resp = self.ts.get_entity(self.table_name, 'MyPartition', '1')

        # Assert
        self.assertEqual(resp.PartitionKey, 'MyPartition')
        self.assertEqual(resp.RowKey, '1')
        self._assert_default_entity(resp)

    def test_get_entity_not_existing(self):
        # Arrange
        self._create_table(self.table_name)

        # Act
        with self.assertRaises(WindowsAzureError):
            self.ts.get_entity(self.table_name, 'MyPartition', '1')

        # Assert

    def test_get_entity_with_select(self):
        # Arrange
        self._create_table_with_default_entities(self.table_name, 1)

        # Act
        resp = self.ts.get_entity(
            self.table_name, 'MyPartition', '1', 'age,sex')

        # Assert
        self.assertEqual(resp.age, 39)
        self.assertEqual(resp.sex, 'male')
        self.assertFalse(hasattr(resp, "birthday"))
        self.assertFalse(hasattr(resp, "married"))
        self.assertFalse(hasattr(resp, "deceased"))

    def test_query_entities(self):
        # Arrange
        self._create_table_with_default_entities(self.table_name, 2)

        # Act
        resp = self.ts.query_entities(self.table_name)

        # Assert
        self.assertEqual(len(resp), 2)
        for entity in resp:
            self.assertEqual(entity.PartitionKey, 'MyPartition')
            self._assert_default_entity(entity)
        self.assertEqual(resp[0].RowKey, '1')
        self.assertEqual(resp[1].RowKey, '2')

    def test_query_entities_with_filter(self):
        # Arrange
        self._create_table_with_default_entities(self.table_name, 2)
        self.ts.insert_entity(
            self.table_name,
            self._create_default_entity_dict('MyOtherPartition', '3'))

        # Act
        resp = self.ts.query_entities(
            self.table_name, "PartitionKey eq 'MyPartition'")

        # Assert
        self.assertEqual(len(resp), 2)
        for entity in resp:
            self.assertEqual(entity.PartitionKey, 'MyPartition')
            self._assert_default_entity(entity)

    def test_query_entities_with_select(self):
        # Arrange
        self._create_table_with_default_entities(self.table_name, 2)

        # Act
        resp = self.ts.query_entities(self.table_name, None, 'age,sex')

        # Assert
        self.assertEqual(len(resp), 2)
        self.assertEqual(resp[0].age, 39)
        self.assertEqual(resp[0].sex, 'male')
        self.assertFalse(hasattr(resp[0], "birthday"))
        self.assertFalse(hasattr(resp[0], "married"))
        self.assertFalse(hasattr(resp[0], "deceased"))

    def test_query_entities_with_top(self):
        # Arrange
        self._create_table_with_default_entities(self.table_name, 3)

        # Act
        resp = self.ts.query_entities(self.table_name, None, None, 2)

        # Assert
        self.assertEqual(len(resp), 2)

    def test_query_entities_with_top_and_next(self):
        # Arrange
        self._create_table_with_default_entities(self.table_name, 5)

        # Act
        resp1 = self.ts.query_entities(self.table_name, None, None, 2)
        resp2 = self.ts.query_entities(
            self.table_name, None, None, 2,
            resp1.x_ms_continuation['NextPartitionKey'],
            resp1.x_ms_continuation['NextRowKey'])
        resp3 = self.ts.query_entities(
            self.table_name, None, None, 2,
            resp2.x_ms_continuation['NextPartitionKey'],
            resp2.x_ms_continuation['NextRowKey'])

        # Assert
        self.assertEqual(len(resp1), 2)
        self.assertEqual(len(resp2), 2)
        self.assertEqual(len(resp3), 1)
        self.assertEqual(resp1[0].RowKey, '1')
        self.assertEqual(resp1[1].RowKey, '2')
        self.assertEqual(resp2[0].RowKey, '3')
        self.assertEqual(resp2[1].RowKey, '4')
        self.assertEqual(resp3[0].RowKey, '5')

    def test_update_entity(self):
        # Arrange
        self._create_table_with_default_entities(self.table_name, 1)

        # Act
        sent_entity = self._create_updated_entity_dict('MyPartition', '1')
        resp = self.ts.update_entity(
            self.table_name, 'MyPartition', '1', sent_entity)

        # Assert
        self.assertIsNotNone(resp)
        received_entity = self.ts.get_entity(
            self.table_name, 'MyPartition', '1')
        self._assert_updated_entity(received_entity)

    def test_update_entity_with_if_matches(self):
        # Arrange
        entities = self._create_table_with_default_entities(self.table_name, 1)

        # Act
        sent_entity = self._create_updated_entity_dict('MyPartition', '1')
        resp = self.ts.update_entity(
            self.table_name,
            'MyPartition', '1', sent_entity, if_match=entities[0].etag)

        # Assert
        self.assertIsNotNone(resp)
        received_entity = self.ts.get_entity(
            self.table_name, 'MyPartition', '1')
        self._assert_updated_entity(received_entity)

    def test_update_entity_with_if_doesnt_match(self):
        # Arrange
        entities = self._create_table_with_default_entities(self.table_name, 1)

        # Act
        sent_entity = self._create_updated_entity_dict('MyPartition', '1')
        with self.assertRaises(WindowsAzureError):
            self.ts.update_entity(
                self.table_name, 'MyPartition', '1', sent_entity,
                if_match=u'W/"datetime\'2012-06-15T22%3A51%3A44.9662825Z\'"')

        # Assert

    def test_insert_or_merge_entity_with_existing_entity(self):
        # Arrange
        self._create_table_with_default_entities(self.table_name, 1)

        # Act
        sent_entity = self._create_updated_entity_dict('MyPartition', '1')
        resp = self.ts.insert_or_merge_entity(
            self.table_name, 'MyPartition', '1', sent_entity)

        # Assert
        self.assertIsNotNone(resp)
        received_entity = self.ts.get_entity(
            self.table_name, 'MyPartition', '1')
        self._assert_merged_entity(received_entity)

    def test_insert_or_merge_entity_with_non_existing_entity(self):
        # Arrange
        self._create_table(self.table_name)

        # Act
        sent_entity = self._create_updated_entity_dict('MyPartition', '1')
        resp = self.ts.insert_or_merge_entity(
            self.table_name, 'MyPartition', '1', sent_entity)

        # Assert
        self.assertIsNotNone(resp)
        received_entity = self.ts.get_entity(
            self.table_name, 'MyPartition', '1')
        self._assert_updated_entity(received_entity)

    def test_insert_or_replace_entity_with_existing_entity(self):
        # Arrange
        self._create_table_with_default_entities(self.table_name, 1)

        # Act
        sent_entity = self._create_updated_entity_dict('MyPartition', '1')
        resp = self.ts.insert_or_replace_entity(
            self.table_name, 'MyPartition', '1', sent_entity)

        # Assert
        self.assertIsNotNone(resp)
        received_entity = self.ts.get_entity(
            self.table_name, 'MyPartition', '1')
        self._assert_updated_entity(received_entity)

    def test_insert_or_replace_entity_with_non_existing_entity(self):
        # Arrange
        self._create_table(self.table_name)

        # Act
        sent_entity = self._create_updated_entity_dict('MyPartition', '1')
        resp = self.ts.insert_or_replace_entity(
            self.table_name, 'MyPartition', '1', sent_entity)

        # Assert
        self.assertIsNotNone(resp)
        received_entity = self.ts.get_entity(
            self.table_name, 'MyPartition', '1')
        self._assert_updated_entity(received_entity)

    def test_merge_entity(self):
        # Arrange
        self._create_table_with_default_entities(self.table_name, 1)

        # Act
        sent_entity = self._create_updated_entity_dict('MyPartition', '1')
        resp = self.ts.merge_entity(
            self.table_name, 'MyPartition', '1', sent_entity)

        # Assert
        self.assertIsNotNone(resp)
        received_entity = self.ts.get_entity(
            self.table_name, 'MyPartition', '1')
        self._assert_merged_entity(received_entity)

    def test_merge_entity_not_existing(self):
        # Arrange
        self._create_table(self.table_name)

        # Act
        sent_entity = self._create_updated_entity_dict('MyPartition', '1')
        with self.assertRaises(WindowsAzureError):
            self.ts.merge_entity(
                self.table_name, 'MyPartition', '1', sent_entity)

        # Assert

    def test_merge_entity_with_if_matches(self):
        # Arrange
        entities = self._create_table_with_default_entities(self.table_name, 1)

        # Act
        sent_entity = self._create_updated_entity_dict('MyPartition', '1')
        resp = self.ts.merge_entity(
            self.table_name, 'MyPartition', '1',
            sent_entity, if_match=entities[0].etag)

        # Assert
        self.assertIsNotNone(resp)
        received_entity = self.ts.get_entity(
            self.table_name, 'MyPartition', '1')
        self._assert_merged_entity(received_entity)

    def test_merge_entity_with_if_doesnt_match(self):
        # Arrange
        entities = self._create_table_with_default_entities(self.table_name, 1)

        # Act
        sent_entity = self._create_updated_entity_dict('MyPartition', '1')
        with self.assertRaises(WindowsAzureError):
            self.ts.merge_entity(
                self.table_name, 'MyPartition', '1', sent_entity,
                if_match=u'W/"datetime\'2012-06-15T22%3A51%3A44.9662825Z\'"')

        # Assert

    def test_delete_entity(self):
        # Arrange
        self._create_table_with_default_entities(self.table_name, 1)

        # Act
        resp = self.ts.delete_entity(self.table_name, 'MyPartition', '1')

        # Assert
        self.assertIsNone(resp)
        with self.assertRaises(WindowsAzureError):
            self.ts.get_entity(self.table_name, 'MyPartition', '1')

    def test_delete_entity_not_existing(self):
        # Arrange
        self._create_table(self.table_name)

        # Act
        with self.assertRaises(WindowsAzureError):
            self.ts.delete_entity(self.table_name, 'MyPartition', '1')

        # Assert

    def test_delete_entity_with_if_matches(self):
        # Arrange
        entities = self._create_table_with_default_entities(self.table_name, 1)

        # Act
        resp = self.ts.delete_entity(
            self.table_name, 'MyPartition', '1', if_match=entities[0].etag)

        # Assert
        self.assertIsNone(resp)
        with self.assertRaises(WindowsAzureError):
            self.ts.get_entity(self.table_name, 'MyPartition', '1')

    def test_delete_entity_with_if_doesnt_match(self):
        # Arrange
        entities = self._create_table_with_default_entities(self.table_name, 1)

        # Act
        with self.assertRaises(WindowsAzureError):
            self.ts.delete_entity(
                self.table_name, 'MyPartition', '1',
                if_match=u'W/"datetime\'2012-06-15T22%3A51%3A44.9662825Z\'"')

        # Assert

    #--Test cases for batch ---------------------------------------------
    def test_with_filter_single(self):
        called = []

        def my_filter(request, next):
            called.append(True)
            return next(request)

        tc = self.ts.with_filter(my_filter)
        tc.create_table(self.table_name)

        self.assertTrue(called)

        del called[:]

        tc.delete_table(self.table_name)

        self.assertTrue(called)
        del called[:]

    def test_with_filter_chained(self):
        called = []

        def filter_a(request, next):
            called.append('a')
            return next(request)

        def filter_b(request, next):
            called.append('b')
            return next(request)

        tc = self.ts.with_filter(filter_a).with_filter(filter_b)
        tc.create_table(self.table_name)

        self.assertEqual(called, ['b', 'a'])

        tc.delete_table(self.table_name)

    def test_batch_insert(self):
        # Arrange
        self._create_table(self.table_name)

        # Act
        entity = Entity()
        entity.PartitionKey = '001'
        entity.RowKey = 'batch_insert'
        entity.test = EntityProperty('Edm.Boolean', 'true')
        entity.test2 = 'value'
        entity.test3 = 3
        entity.test4 = EntityProperty('Edm.Int64', '1234567890')
        entity.test5 = datetime.utcnow()

        self.ts.begin_batch()
        self.ts.insert_entity(self.table_name, entity)
        self.ts.commit_batch()

        # Assert
        result = self.ts.get_entity(self.table_name, '001', 'batch_insert')
        self.assertIsNotNone(result)

    def test_batch_update(self):
        # Arrange
        self._create_table(self.table_name)

        # Act
        entity = Entity()
        entity.PartitionKey = '001'
        entity.RowKey = 'batch_update'
        entity.test = EntityProperty('Edm.Boolean', 'true')
        entity.test2 = 'value'
        entity.test3 = 3
        entity.test4 = EntityProperty('Edm.Int64', '1234567890')
        entity.test5 = datetime.utcnow()
        self.ts.insert_entity(self.table_name, entity)

        entity = self.ts.get_entity(self.table_name, '001', 'batch_update')
        self.assertEqual(3, entity.test3)
        entity.test2 = 'value1'
        self.ts.begin_batch()
        self.ts.update_entity(self.table_name, '001', 'batch_update', entity)
        self.ts.commit_batch()
        entity = self.ts.get_entity(self.table_name, '001', 'batch_update')

        # Assert
        self.assertEqual('value1', entity.test2)

    def test_batch_merge(self):
        # Arrange
        self._create_table(self.table_name)

        # Act
        entity = Entity()
        entity.PartitionKey = '001'
        entity.RowKey = 'batch_merge'
        entity.test = EntityProperty('Edm.Boolean', 'true')
        entity.test2 = 'value'
        entity.test3 = 3
        entity.test4 = EntityProperty('Edm.Int64', '1234567890')
        entity.test5 = datetime.utcnow()
        self.ts.insert_entity(self.table_name, entity)

        entity = self.ts.get_entity(self.table_name, '001', 'batch_merge')
        self.assertEqual(3, entity.test3)
        entity = Entity()
        entity.PartitionKey = '001'
        entity.RowKey = 'batch_merge'
        entity.test2 = 'value1'
        self.ts.begin_batch()
        self.ts.merge_entity(self.table_name, '001', 'batch_merge', entity)
        self.ts.commit_batch()
        entity = self.ts.get_entity(self.table_name, '001', 'batch_merge')

        # Assert
        self.assertEqual('value1', entity.test2)
        self.assertEqual(1234567890, entity.test4)

    def test_batch_update_if_match(self):
        # Arrange
        entities = self._create_table_with_default_entities(self.table_name, 1)

        # Act
        sent_entity = self._create_updated_entity_dict('MyPartition', '1')
        self.ts.begin_batch()
        resp = self.ts.update_entity(
            self.table_name,
            'MyPartition', '1', sent_entity, if_match=entities[0].etag)
        self.ts.commit_batch()

        # Assert
        self.assertIsNone(resp)
        received_entity = self.ts.get_entity(
            self.table_name, 'MyPartition', '1')
        self._assert_updated_entity(received_entity)

    def test_batch_update_if_doesnt_match(self):
        # Arrange
        entities = self._create_table_with_default_entities(self.table_name, 2)

        # Act
        sent_entity1 = self._create_updated_entity_dict('MyPartition', '1')
        sent_entity2 = self._create_updated_entity_dict('MyPartition', '2')
        self.ts.begin_batch()
        self.ts.update_entity(
            self.table_name, 'MyPartition', '1', sent_entity1,
            if_match=u'W/"datetime\'2012-06-15T22%3A51%3A44.9662825Z\'"')
        self.ts.update_entity(
            self.table_name, 'MyPartition', '2', sent_entity2)
        try:
            self.ts.commit_batch()
        except WindowsAzureBatchOperationError as error:
            self.assertEqual(error.code, 'UpdateConditionNotSatisfied')
            self.assertTrue(str(error).startswith('0:The update condition specified in the request was not satisfied.'))
        else:
            self.fail('WindowsAzureBatchOperationError was expected')

        # Assert
        received_entity = self.ts.get_entity(
            self.table_name, 'MyPartition', '1')
        self._assert_default_entity(received_entity)
        received_entity = self.ts.get_entity(
            self.table_name, 'MyPartition', '2')
        self._assert_default_entity(received_entity)

    def test_batch_insert_replace(self):
        # Arrange
        self._create_table(self.table_name)

        # Act
        entity = Entity()
        entity.PartitionKey = '001'
        entity.RowKey = 'batch_insert_replace'
        entity.test = EntityProperty('Edm.Boolean', 'true')
        entity.test2 = 'value'
        entity.test3 = 3
        entity.test4 = EntityProperty('Edm.Int64', '1234567890')
        entity.test5 = datetime.utcnow()
        self.ts.begin_batch()
        self.ts.insert_or_replace_entity(
            self.table_name, entity.PartitionKey, entity.RowKey, entity)
        self.ts.commit_batch()

        entity = self.ts.get_entity(
            self.table_name, '001', 'batch_insert_replace')

        # Assert
        self.assertIsNotNone(entity)
        self.assertEqual('value', entity.test2)
        self.assertEqual(1234567890, entity.test4)

    def test_batch_insert_merge(self):
        # Arrange
        self._create_table(self.table_name)

        # Act
        entity = Entity()
        entity.PartitionKey = '001'
        entity.RowKey = 'batch_insert_merge'
        entity.test = EntityProperty('Edm.Boolean', 'true')
        entity.test2 = 'value'
        entity.test3 = 3
        entity.test4 = EntityProperty('Edm.Int64', '1234567890')
        entity.test5 = datetime.utcnow()
        self.ts.begin_batch()
        self.ts.insert_or_merge_entity(
            self.table_name, entity.PartitionKey, entity.RowKey, entity)
        self.ts.commit_batch()

        entity = self.ts.get_entity(
            self.table_name, '001', 'batch_insert_merge')

        # Assert
        self.assertIsNotNone(entity)
        self.assertEqual('value', entity.test2)
        self.assertEqual(1234567890, entity.test4)

    def test_batch_delete(self):
        # Arrange
        self._create_table(self.table_name)

        # Act
        entity = Entity()
        entity.PartitionKey = '001'
        entity.RowKey = 'batch_delete'
        entity.test = EntityProperty('Edm.Boolean', 'true')
        entity.test2 = 'value'
        entity.test3 = 3
        entity.test4 = EntityProperty('Edm.Int64', '1234567890')
        entity.test5 = datetime.utcnow()
        self.ts.insert_entity(self.table_name, entity)

        entity = self.ts.get_entity(self.table_name, '001', 'batch_delete')
        #self.assertEqual(3, entity.test3)
        self.ts.begin_batch()
        self.ts.delete_entity(self.table_name, '001', 'batch_delete')
        self.ts.commit_batch()

    def test_batch_inserts(self):
        # Arrange
        self._create_table(self.table_name)

        # Act
        entity = Entity()
        entity.PartitionKey = 'batch_inserts'
        entity.test = EntityProperty('Edm.Boolean', 'true')
        entity.test2 = 'value'
        entity.test3 = 3
        entity.test4 = EntityProperty('Edm.Int64', '1234567890')

        self.ts.begin_batch()
        for i in range(100):
            entity.RowKey = str(i)
            self.ts.insert_entity(self.table_name, entity)
        self.ts.commit_batch()

        entities = self.ts.query_entities(
            self.table_name, "PartitionKey eq 'batch_inserts'", '')

        # Assert
        self.assertIsNotNone(entities)
        self.assertEqual(100, len(entities))

    def test_batch_all_operations_together(self):
        # Arrange
        self._create_table(self.table_name)

         # Act
        entity = Entity()
        entity.PartitionKey = '003'
        entity.RowKey = 'batch_all_operations_together-1'
        entity.test = EntityProperty('Edm.Boolean', 'true')
        entity.test2 = 'value'
        entity.test3 = 3
        entity.test4 = EntityProperty('Edm.Int64', '1234567890')
        entity.test5 = datetime.utcnow()
        self.ts.insert_entity(self.table_name, entity)
        entity.RowKey = 'batch_all_operations_together-2'
        self.ts.insert_entity(self.table_name, entity)
        entity.RowKey = 'batch_all_operations_together-3'
        self.ts.insert_entity(self.table_name, entity)
        entity.RowKey = 'batch_all_operations_together-4'
        self.ts.insert_entity(self.table_name, entity)

        self.ts.begin_batch()
        entity.RowKey = 'batch_all_operations_together'
        self.ts.insert_entity(self.table_name, entity)
        entity.RowKey = 'batch_all_operations_together-1'
        self.ts.delete_entity(
            self.table_name, entity.PartitionKey, entity.RowKey)
        entity.RowKey = 'batch_all_operations_together-2'
        entity.test3 = 10
        self.ts.update_entity(
            self.table_name, entity.PartitionKey, entity.RowKey, entity)
        entity.RowKey = 'batch_all_operations_together-3'
        entity.test3 = 100
        self.ts.merge_entity(
            self.table_name, entity.PartitionKey, entity.RowKey, entity)
        entity.RowKey = 'batch_all_operations_together-4'
        entity.test3 = 10
        self.ts.insert_or_replace_entity(
            self.table_name, entity.PartitionKey, entity.RowKey, entity)
        entity.RowKey = 'batch_all_operations_together-5'
        self.ts.insert_or_merge_entity(
            self.table_name, entity.PartitionKey, entity.RowKey, entity)
        self.ts.commit_batch()

        # Assert
        entities = self.ts.query_entities(
            self.table_name, "PartitionKey eq '003'", '')
        self.assertEqual(5, len(entities))

    def test_batch_same_row_operations_fail(self):
        # Arrange
        self._create_table(self.table_name)
        entity = self._create_default_entity_dict('001', 'batch_negative_1')
        self.ts.insert_entity(self.table_name, entity)

        # Act
        with self.assertRaises(WindowsAzureError):
            self.ts.begin_batch()

            entity = self._create_updated_entity_dict(
                '001', 'batch_negative_1')
            self.ts.update_entity(
                self.table_name,
                entity['PartitionKey'],
                entity['RowKey'], entity)

            entity = self._create_default_entity_dict(
                '001', 'batch_negative_1')
            self.ts.merge_entity(
                self.table_name,
                entity['PartitionKey'],
                entity['RowKey'], entity)

        self.ts.cancel_batch()

        # Assert

    def test_batch_different_partition_operations_fail(self):
        # Arrange
        self._create_table(self.table_name)
        entity = self._create_default_entity_dict('001', 'batch_negative_1')
        self.ts.insert_entity(self.table_name, entity)

        # Act
        with self.assertRaises(WindowsAzureError):
            self.ts.begin_batch()

            entity = self._create_updated_entity_dict(
                '001', 'batch_negative_1')
            self.ts.update_entity(
                self.table_name, entity['PartitionKey'], entity['RowKey'],
                entity)

            entity = self._create_default_entity_dict(
                '002', 'batch_negative_1')
            self.ts.insert_entity(self.table_name, entity)

        self.ts.cancel_batch()

        # Assert

    def test_batch_different_table_operations_fail(self):
        # Arrange
        other_table_name = self.table_name + 'other'
        self.additional_table_names = [other_table_name]
        self._create_table(self.table_name)
        self._create_table(other_table_name)

        # Act
        with self.assertRaises(WindowsAzureError):
            self.ts.begin_batch()

            entity = self._create_default_entity_dict(
                '001', 'batch_negative_1')
            self.ts.insert_entity(self.table_name, entity)

            entity = self._create_default_entity_dict(
                '001', 'batch_negative_2')
            self.ts.insert_entity(other_table_name, entity)

        self.ts.cancel_batch()

    def test_unicode_property_value(self):
        ''' regression test for github issue #57'''
        # Act
        self._create_table(self.table_name)
        self.ts.insert_entity(
            self.table_name,
            {'PartitionKey': 'test', 'RowKey': 'test1', 'Description': u'ꀕ'})
        self.ts.insert_entity(
            self.table_name,
            {'PartitionKey': 'test', 'RowKey': 'test2', 'Description': 'ꀕ'})
        resp = self.ts.query_entities(
            self.table_name, "PartitionKey eq 'test'")
        # Assert
        self.assertEqual(len(resp), 2)
        self.assertEqual(resp[0].Description, u'ꀕ')
        self.assertEqual(resp[1].Description, u'ꀕ')

    def test_unicode_property_name(self):
        # Act
        self._create_table(self.table_name)
        self.ts.insert_entity(
            self.table_name,
            {'PartitionKey': 'test', 'RowKey': 'test1', u'啊齄丂狛狜': u'ꀕ'})
        self.ts.insert_entity(
            self.table_name,
            {'PartitionKey': 'test', 'RowKey': 'test2', u'啊齄丂狛狜': 'hello'})
        resp = self.ts.query_entities(
            self.table_name, "PartitionKey eq 'test'")
        # Assert
        self.assertEqual(len(resp), 2)
        self.assertEqual(resp[0].__dict__[u'啊齄丂狛狜'], u'ꀕ')
        self.assertEqual(resp[1].__dict__[u'啊齄丂狛狜'], u'hello')

    def test_unicode_create_table_unicode_name(self):
        # Arrange
        self.table_name = self.table_name + u'啊齄丂狛狜'

        # Act
        with self.assertRaises(WindowsAzureError):
            # not supported - table name must be alphanumeric, lowercase
            self.ts.create_table(self.table_name)

        # Assert

    def test_empty_and_spaces_property_value(self):
        # Act
        self._create_table(self.table_name)
        self.ts.insert_entity(
            self.table_name,
            {
                'PartitionKey': 'test',
                'RowKey': 'test1',
                'EmptyByte': '',
                'EmptyUnicode': u'',
                'SpacesOnlyByte': '   ',
                'SpacesOnlyUnicode': u'   ',
                'SpacesBeforeByte': '   Text',
                'SpacesBeforeUnicode': u'   Text',
                'SpacesAfterByte': 'Text   ',
                'SpacesAfterUnicode': u'Text   ',
                'SpacesBeforeAndAfterByte': '   Text   ',
                'SpacesBeforeAndAfterUnicode': u'   Text   ',
            })
        resp = self.ts.get_entity(self.table_name, 'test', 'test1')
        
        # Assert
        self.assertIsNotNone(resp)
        self.assertEqual(resp.EmptyByte, '')
        self.assertEqual(resp.EmptyUnicode, u'')
        self.assertEqual(resp.SpacesOnlyByte, '   ')
        self.assertEqual(resp.SpacesOnlyUnicode, u'   ')
        self.assertEqual(resp.SpacesBeforeByte, '   Text')
        self.assertEqual(resp.SpacesBeforeUnicode, u'   Text')
        self.assertEqual(resp.SpacesAfterByte, 'Text   ')
        self.assertEqual(resp.SpacesAfterUnicode, u'Text   ')
        self.assertEqual(resp.SpacesBeforeAndAfterByte, '   Text   ')
        self.assertEqual(resp.SpacesBeforeAndAfterUnicode, u'   Text   ')

    def test_none_property_value(self):
        # Act
        self._create_table(self.table_name)
        self.ts.insert_entity(
            self.table_name,
            {
                'PartitionKey': 'test',
                'RowKey': 'test1',
                'NoneValue': None,
            })
        resp = self.ts.get_entity(self.table_name, 'test', 'test1')

        # Assert
        self.assertIsNotNone(resp)
        self.assertFalse(hasattr(resp, 'NoneValue'))

    def test_binary_property_value(self):
        # Act
        binary_data = b'\x01\x02\x03\x04\x05\x06\x07\x08\t\n'
        self._create_table(self.table_name)
        self.ts.insert_entity(
            self.table_name,
            {
                'PartitionKey': 'test',
                'RowKey': 'test1',
                'binary': EntityProperty('Edm.Binary', binary_data)
            })
        resp = self.ts.get_entity(self.table_name, 'test', 'test1')

        # Assert
        self.assertIsNotNone(resp)
        self.assertEqual(resp.binary.type, 'Edm.Binary')
        self.assertEqual(resp.binary.value, binary_data)

#------------------------------------------------------------------------------
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = util
#-------------------------------------------------------------------------
# Copyright (c) Microsoft.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#--------------------------------------------------------------------------
import json
import os
import random
import sys
import time
import unittest

if sys.version_info < (3,):
    from exceptions import RuntimeError

#------------------------------------------------------------------------------


class Credentials(object):

    '''
    Azure credentials needed to run Azure client tests.
    '''

    def __init__(self):
        credentialsFilename = "windowsazurecredentials.json"
        tmpName = os.path.join(os.getcwd(), credentialsFilename)
        if not os.path.exists(tmpName):
            if "USERPROFILE" in os.environ:
                tmpName = os.path.join(os.environ["USERPROFILE"],
                                       credentialsFilename)
            elif "HOME" in os.environ:
                tmpName = os.path.join(os.environ["HOME"],
                                       credentialsFilename)
        if not os.path.exists(tmpName):
            errMsg = "Cannot run Azure tests when the expected config file containing Azure credentials, '{0}', does not exist!".format(
                tmpName)
            raise RuntimeError(errMsg)

        with open(tmpName, "r") as f:
            self.ns = json.load(f)

    def getManagementCertFile(self):
        return self.ns[u'managementcertfile']

    def getSubscriptionId(self):
        return self.ns[u'subscriptionid']

    def getServiceBusKey(self):
        return self.ns[u'servicebuskey']

    def getServiceBusNamespace(self):
        return self.ns[u'servicebusns']

    def getStorageServicesKey(self):
        return self.ns[u'storageserviceskey']

    def getStorageServicesName(self):
        return self.ns[u'storageservicesname']

    def getRemoteStorageServicesKey(self):
        ''' Key for remote storage account (different location). '''
        return self.ns[u'remotestorageserviceskey']

    def getRemoteStorageServicesName(self):
        ''' Name for remote storage account (different location). '''
        return self.ns[u'remotestorageservicesname']

    def getLinuxOSVHD(self):
        return self.ns[u'linuxosvhd']

    def getProxyHost(self):
        ''' Optional. Address of the proxy server. '''
        if u'proxyhost' in self.ns:
            return self.ns[u'proxyhost']
        return None

    def getProxyPort(self):
        ''' Optional. Port of the proxy server. '''
        if u'proxyport' in self.ns:
            return self.ns[u'proxyport']
        return None

    def getProxyUser(self):
        ''' Optional. User name for proxy server authentication. '''
        if u'proxyuser' in self.ns:
            return self.ns[u'proxyuser']
        return None

    def getProxyPassword(self):
        ''' Optional. Password for proxy server authentication. '''
        if u'proxypassword' in self.ns:
            return self.ns[u'proxypassword']
        return None

    def getUseHttplibOverride(self):
        ''' Optional. When specified, it will override the value of
        use_httplib that is set by the auto-detection in httpclient.py.
        When testing management APIs, make sure to specify a value that is
        compatible with the value of 'managementcertfile' ie. True for a .pem
        certificate file path, False for a Windows Certificate Store path.
        '''
        if u'usehttpliboverride' in self.ns:
            return self.ns[u'usehttpliboverride'].lower() != 'false'
        return None

credentials = Credentials()


def getUniqueName(base_name):
    '''
    Returns a unique identifier for this particular test run so
    parallel test runs using the same Azure keys do not interfere
    with one another.
    '''
    cur_time = str(time.time())
    for bad in ["-", "_", " ", "."]:
        cur_time = cur_time.replace(bad, "")
    cur_time = cur_time.lower().strip()
    return base_name + str(random.randint(10, 99)) + cur_time[:12]


def set_service_options(service):
    useHttplibOverride = credentials.getUseHttplibOverride()
    if useHttplibOverride is not None:
        # Override the auto-detection of what type of connection to create.
        # This allows testing of both httplib and winhttp on Windows.
        service._httpclient.use_httplib = useHttplibOverride

    service.set_proxy(credentials.getProxyHost(),
                      credentials.getProxyPort(),
                      credentials.getProxyUser(),
                      credentials.getProxyPassword())


class AzureTestCase(unittest.TestCase):

    def assertNamedItemInContainer(self, container, item_name, msg=None):
        for item in container:
            if item.name == item_name:
                return

        standardMsg = '{0} not found in {1}'.format(
            repr(item_name), repr(container))
        self.fail(self._formatMessage(msg, standardMsg))

    def assertNamedItemNotInContainer(self, container, item_name, msg=None):
        for item in container:
            if item.name == item_name:
                standardMsg = '{0} unexpectedly found in {1}'.format(
                    repr(item_name), repr(container))
                self.fail(self._formatMessage(msg, standardMsg))

########NEW FILE########
