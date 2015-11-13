__FILENAME__ = client
#!/usr/bin/python
# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

"""Pythonic simple SOAP Client implementation"""

from __future__ import unicode_literals
import sys
if sys.version > '3':
    unicode = str

try:
    import cPickle as pickle
except ImportError:
    import pickle
import hashlib
import logging
import os
import tempfile

from . import __author__, __copyright__, __license__, __version__, TIMEOUT
from .simplexml import SimpleXMLElement, TYPE_MAP, REVERSE_TYPE_MAP, Struct
from .transport import get_http_wrapper, set_http_wrapper, get_Http
# Utility functions used throughout wsdl_parse, moved aside for readability
from .helpers import fetch, sort_dict, make_key, process_element, \
                     postprocess_element, get_message, preprocess_schema, \
                     get_local_name, get_namespace_prefix, TYPE_MAP, urlsplit


log = logging.getLogger(__name__)


class SoapFault(RuntimeError):
    def __init__(self, faultcode, faultstring):
        self.faultcode = faultcode
        self.faultstring = faultstring
        RuntimeError.__init__(self, faultcode, faultstring)

    def __unicode__(self):
        return '%s: %s' % (self.faultcode, self.faultstring)

    if sys.version > '3':
        __str__ = __unicode__
    else:
        def __str__(self):
            return self.__unicode__().encode('ascii', 'ignore')

    def __repr__(self):
        return "SoapFault(%s, %s)" % (repr(self.faultcode),
                                      repr(self.faultstring))


# soap protocol specification & namespace
soap_namespaces = dict(
    soap11='http://schemas.xmlsoap.org/soap/envelope/',
    soap='http://schemas.xmlsoap.org/soap/envelope/',
    soapenv='http://schemas.xmlsoap.org/soap/envelope/',
    soap12='http://www.w3.org/2003/05/soap-env',
    soap12env="http://www.w3.org/2003/05/soap-envelope",
)


class SoapClient(object):
    """Simple SOAP Client (simil PHP)"""
    def __init__(self, location=None, action=None, namespace=None,
                 cert=None, exceptions=True, proxy=None, ns=None,
                 soap_ns=None, wsdl=None, wsdl_basedir='', cache=False, cacert=None,
                 sessions=False, soap_server=None, timeout=TIMEOUT,
                 http_headers=None, trace=False,
                 username=None, password=None,
                 ):
        """
        :param http_headers: Additional HTTP Headers; example: {'Host': 'ipsec.example.com'}
        """
        self.certssl = cert
        self.keyssl = None
        self.location = location        # server location (url)
        self.action = action            # SOAP base action
        self.namespace = namespace      # message
        self.exceptions = exceptions    # lanzar execpiones? (Soap Faults)
        self.xml_request = self.xml_response = ''
        self.http_headers = http_headers or {}
        # extract the base directory / url for wsdl relative imports:
        if wsdl and wsdl_basedir == '':
            # parse the wsdl url, strip the scheme and filename
            url_scheme, netloc, path, query, fragment = urlsplit(wsdl)
            wsdl_basedir = os.path.dirname(netloc + path)
            
        self.wsdl_basedir = wsdl_basedir
        
        # shortcut to print all debugging info and sent / received xml messages
        if trace:
            if trace is True:
                level = logging.DEBUG           # default logging level
            else:
                level = trace                   # use the provided level
            logging.basicConfig(level=level)
            log.setLevel(level)
        
        if not soap_ns and not ns:
            self.__soap_ns = 'soap'  # 1.1
        elif not soap_ns and ns:
            self.__soap_ns = 'soapenv'  # 1.2
        else:
            self.__soap_ns = soap_ns

        # SOAP Server (special cases like oracle, jbossas6 or jetty)
        self.__soap_server = soap_server

        # SOAP Header support
        self.__headers = {}         # general headers
        self.__call_headers = None  # Struct to be marshalled for RPC Call

        # check if the Certification Authority Cert is a string and store it
        if cacert and cacert.startswith('-----BEGIN CERTIFICATE-----'):
            fd, filename = tempfile.mkstemp()
            f = os.fdopen(fd, 'w+b', -1)
            log.debug("Saving CA certificate to %s" % filename)
            f.write(cacert)
            cacert = filename
            f.close()
        self.cacert = cacert

        # Create HTTP wrapper
        Http = get_Http()
        self.http = Http(timeout=timeout, cacert=cacert, proxy=proxy, sessions=sessions)
        if username and password:
            if hasattr(self.http, 'add_credentials'):
                self.http.add_credentials(username, password)
            

        # namespace prefix, None to use xmlns attribute or False to not use it:
        self.__ns = ns
        if not ns:
            self.__xml = """<?xml version="1.0" encoding="UTF-8"?>
<%(soap_ns)s:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:xsd="http://www.w3.org/2001/XMLSchema"
    xmlns:%(soap_ns)s="%(soap_uri)s">
<%(soap_ns)s:Header/>
<%(soap_ns)s:Body>
    <%(method)s xmlns="%(namespace)s">
    </%(method)s>
</%(soap_ns)s:Body>
</%(soap_ns)s:Envelope>"""
        else:
            self.__xml = """<?xml version="1.0" encoding="UTF-8"?>
<%(soap_ns)s:Envelope xmlns:%(soap_ns)s="%(soap_uri)s" xmlns:%(ns)s="%(namespace)s">
<%(soap_ns)s:Header/>
<%(soap_ns)s:Body>
    <%(ns)s:%(method)s>
    </%(ns)s:%(method)s>
</%(soap_ns)s:Body>
</%(soap_ns)s:Envelope>"""

        # parse wsdl url
        self.services = wsdl and self.wsdl_parse(wsdl, cache=cache)
        self.service_port = None                 # service port for late binding

    def __getattr__(self, attr):
        """Return a pseudo-method that can be called"""
        if not self.services:  # not using WSDL?
            return lambda self=self, *args, **kwargs: self.call(attr, *args, **kwargs)
        else:  # using WSDL:
            return lambda *args, **kwargs: self.wsdl_call(attr, *args, **kwargs)

    def call(self, method, *args, **kwargs):
        """Prepare xml request and make SOAP call, returning a SimpleXMLElement.

        If a keyword argument called "headers" is passed with a value of a
        SimpleXMLElement object, then these headers will be inserted into the
        request.
        """
        #TODO: method != input_message
        # Basic SOAP request:
        xml = self.__xml % dict(method=method,              # method tag name
                                namespace=self.namespace,   # method ns uri
                                ns=self.__ns,               # method ns prefix
                                soap_ns=self.__soap_ns,     # soap prefix & uri
                                soap_uri=soap_namespaces[self.__soap_ns])
        request = SimpleXMLElement(xml, namespace=self.__ns and self.namespace, 
                                        prefix=self.__ns)

        request_headers = kwargs.pop('headers', None)

        # serialize parameters
        if kwargs:
            parameters = list(kwargs.items())
        else:
            parameters = args
        if parameters and isinstance(parameters[0], SimpleXMLElement):
            # merge xmlelement parameter ("raw" - already marshalled)
            if parameters[0].children() is not None:
                for param in parameters[0].children():
                    getattr(request, method).import_node(param)
                for k,v in parameters[0].attributes().items():
                    getattr(request, method)[k] = v
        elif parameters:
            # marshall parameters:
            use_ns = None if (self.__soap_server == "jetty" or self.qualified is False) else True
            for k, v in parameters:  # dict: tag=valor
                if hasattr(v, "namespaces") and use_ns:
                    ns = v.namespaces.get(None, True)
                else:
                    ns = use_ns
                getattr(request, method).marshall(k, v, ns=ns)
        elif self.__soap_server in ('jbossas6',):
            # JBossAS-6 requires no empty method parameters!
            delattr(request("Body", ns=list(soap_namespaces.values()),), method)

        # construct header and parameters (if not wsdl given) except wsse
        if self.__headers and not self.services:
            self.__call_headers = dict([(k, v) for k, v in self.__headers.items()
                                        if not k.startswith('wsse:')])
        # always extract WS Security header and send it
        if 'wsse:Security' in self.__headers:
            #TODO: namespaces too hardwired, clean-up...
            header = request('Header', ns=list(soap_namespaces.values()),)
            k = 'wsse:Security'
            v = self.__headers[k]
            header.marshall(k, v, ns=False, add_children_ns=False)
            header(k)['xmlns:wsse'] = 'http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd'
            #<wsse:UsernameToken xmlns:wsu='http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd'>
        if self.__call_headers:
            header = request('Header', ns=list(soap_namespaces.values()),)
            for k, v in self.__call_headers.items():
                ##if not self.__ns:
                ##    header['xmlns']
                if isinstance(v, SimpleXMLElement):
                    # allows a SimpleXMLElement to be constructed and inserted
                    # rather than a dictionary. marshall doesn't allow ns: prefixes
                    # in dict key names
                    header.import_node(v)
                else:
                    header.marshall(k, v, ns=self.__ns, add_children_ns=False)
        if request_headers:
            header = request('Header', ns=list(soap_namespaces.values()),)
            for subheader in request_headers.children():
                header.import_node(subheader)

        self.xml_request = request.as_xml()
        self.xml_response = self.send(method, self.xml_request)
        response = SimpleXMLElement(self.xml_response, namespace=self.namespace,
                                    jetty=self.__soap_server in ('jetty',))
        if self.exceptions and response("Fault", ns=list(soap_namespaces.values()), error=False):
            raise SoapFault(unicode(response.faultcode), unicode(response.faultstring))
        return response

    def send(self, method, xml):
        """Send SOAP request using HTTP"""
        if self.location == 'test': return
        # location = '%s' % self.location #?op=%s" % (self.location, method)
        location = str(self.location)

        if self.services:
            soap_action = str(self.action)
        else:
            soap_action = str(self.action) + method

        headers = {
            'Content-type': 'text/xml; charset="UTF-8"',
            'Content-length': str(len(xml)),
            'SOAPAction': '"%s"' % soap_action
        }
        headers.update(self.http_headers)
        log.info("POST %s" % location)
        log.debug('\n'.join(["%s: %s" % (k, v) for k, v in headers.items()]))
        log.debug(xml)

        response, content = self.http.request(
            location, 'POST', body=xml, headers=headers)
        self.response = response
        self.content = content

        log.debug('\n'.join(["%s: %s" % (k, v) for k, v in response.items()]))
        log.debug(content)
        return content

    def get_operation(self, method):
        # try to find operation in wsdl file
        soap_ver = self.__soap_ns.startswith('soap12') and 'soap12' or 'soap11'
        if not self.service_port:
            for service_name, service in self.services.items():
                for port_name, port in [port for port in service['ports'].items()]:
                    if port['soap_ver'] == soap_ver:
                        self.service_port = service_name, port_name
                        break
                else:
                    raise RuntimeError('Cannot determine service in WSDL: '
                                       'SOAP version: %s' % soap_ver)
        else:
            port = self.services[self.service_port[0]]['ports'][self.service_port[1]]
        if not self.location:
            self.location = port['location']
        operation = port['operations'].get(method)
        if not operation:
            raise RuntimeError('Operation %s not found in WSDL: '
                               'Service/Port Type: %s' %
                               (method, self.service_port))
        return operation

    def wsdl_call(self, method, *args, **kwargs):
        """Pre and post process SOAP call, input and output parameters using WSDL"""
        soap_uri = soap_namespaces[self.__soap_ns]
        operation = self.get_operation(method)

        # get i/o type declarations:
        input = operation['input']
        output = operation['output']
        header = operation.get('header')
        if 'action' in operation:
            self.action = operation['action']
        
        if 'namespace' in operation:
            self.namespace = operation['namespace'] or ''
            self.qualified = operation['qualified']            

        # construct header and parameters
        if header:
            self.__call_headers = sort_dict(header, self.__headers)
        method, params = self.wsdl_call_get_params(method, input, *args, **kwargs)

        # call remote procedure
        response = self.call(method, *params)
        # parse results:
        resp = response('Body', ns=soap_uri).children().unmarshall(output)
        return resp and list(resp.values())[0]  # pass Response tag children

    def wsdl_call_get_params(self, method, input, *args, **kwargs):
        """Build params from input and args/kwargs"""
        params = inputname = inputargs = None
        all_args = {}
        if input:
            inputname = list(input.keys())[0]
            inputargs = input[inputname]

        if input and args:
            # convert positional parameters to named parameters:
            d = {}
            for idx, arg in enumerate(args):
                key = list(inputargs.keys())[idx]
                if isinstance(arg, dict):
                    if key not in arg:
                        raise KeyError('Unhandled key %s. use client.help(method)' % key)
                    d[key] = arg[key]
                else:
                    d[key] = arg
            all_args.update({inputname: d})

        if input and (kwargs or all_args):
            if kwargs:
                all_args.update({inputname: kwargs})
            valid, errors, warnings = self.wsdl_validate_params(input, all_args)
            if not valid:
                raise ValueError('Invalid Args Structure. Errors: %s' % errors)
            # sort and filter parameters acording wsdl input structure
            tree = sort_dict(input, all_args)
            root = list(tree.values())[0]
            params = []
            # make a params tuple list suitable for self.call(method, *params)
            for k, v in root.items():
                # fix referenced namespaces as info is lost when calling call 
                root_ns = root.namespaces[k]
                if not root.references[k] and isinstance(v, Struct):
                    v.namespaces[None] = root_ns
                params.append((k, v))
            # TODO: check style and document attributes
            if self.__soap_server in ('axis', ):
                # use the operation name
                method = method
            else:
                # use the message (element) name
                method = inputname
        #elif not input:
            #TODO: no message! (see wsmtxca.dummy)
        else:
            params = kwargs and kwargs.items()

        return (method, params)

    def wsdl_validate_params(self, struct, value):
        """Validate the arguments (actual values) for the parameters structure. 
           Fail for any invalid arguments or type mismatches."""
        errors = []
        warnings = []
        valid = True

        # Determine parameter type
        if type(struct) == type(value):
            typematch = True
        if not isinstance(struct, dict) and isinstance(value, dict):
            typematch = True    # struct can be a dict or derived (Struct)
        else:
            typematch = False

        if struct == str:
            struct = unicode        # fix for py2 vs py3 string handling
        
        if not isinstance(struct, (list, dict, tuple)) and struct in TYPE_MAP.keys():
            if not type(value) == struct:
                try:
                    struct(value)       # attempt to cast input to parameter type
                except:
                    valid = False
                    errors.append('Type mismatch for argument value. parameter(%s): %s, value(%s): %s' % (type(struct), struct, type(value), value))

        elif isinstance(struct, list) and len(struct) == 1 and not isinstance(value, list):
            # parameter can have a dict in a list: [{}] indicating a list is allowed, but not needed if only one argument.
            next_valid, next_errors, next_warnings = self.wsdl_validate_params(struct[0], value)
            if not next_valid:
                valid = False
            errors.extend(next_errors)
            warnings.extend(next_warnings)

        # traverse tree
        elif isinstance(struct, dict):
            if struct and value:
                for key in value:
                    if key not in struct:
                        valid = False
                        errors.append('Argument key %s not in parameter. parameter: %s, args: %s' % (key, struct, value))
                    else:
                        next_valid, next_errors, next_warnings = self.wsdl_validate_params(struct[key], value[key])
                        if not next_valid:
                            valid = False
                        errors.extend(next_errors)
                        warnings.extend(next_warnings)
                for key in struct:
                    if key not in value:
                        warnings.append('Parameter key %s not in args. parameter: %s, value: %s' % (key, struct, value))
            elif struct and not value:
                warnings.append('parameter keys not in args. parameter: %s, args: %s' % (struct, value))
            elif not struct and value:
                valid = False
                errors.append('Args keys not in parameter. parameter: %s, args: %s' % (struct, value))
            else:
                pass
        elif isinstance(struct, list):
            struct_list_value = struct[0]
            for item in value:
                next_valid, next_errors, next_warnings = self.wsdl_validate_params(struct_list_value, item)
                if not next_valid:
                    valid = False
                errors.extend(next_errors)
                warnings.extend(next_warnings)
        elif not typematch:
            valid = False
            errors.append('Type mismatch. parameter(%s): %s, value(%s): %s' % (type(struct), struct, type(value), value))

        return (valid, errors, warnings)

    def help(self, method):
        """Return operation documentation and invocation/returned value example"""
        operation = self.get_operation(method)
        input = operation.get('input')
        input = input and input.values() and list(input.values())[0]
        if isinstance(input, dict):
            input = ", ".join("%s=%s" % (k, repr(v)) for k, v in input.items())
        elif isinstance(input, list):
            input = repr(input)
        output = operation.get('output')
        if output:
            output = list(operation['output'].values())[0]
        headers = operation.get('headers') or None
        return "%s(%s)\n -> %s:\n\n%s\nHeaders: %s" % (
            method,
            input or '',
            output and output or '',
            operation.get('documentation', ''),
            headers,
        )

    def wsdl_parse(self, url, cache=False):
        """Parse Web Service Description v1.1"""

        log.debug('Parsing wsdl url: %s' % url)
        # Try to load a previously parsed wsdl:
        force_download = False
        if cache:
            # make md5 hash of the url for caching...
            filename_pkl = '%s.pkl' % hashlib.md5(url).hexdigest()
            if isinstance(cache, basestring):
                filename_pkl = os.path.join(cache, filename_pkl)
            if os.path.exists(filename_pkl):
                log.debug('Unpickle file %s' % (filename_pkl, ))
                f = open(filename_pkl, 'r')
                pkl = pickle.load(f)
                f.close()
                # sanity check:
                if pkl['version'][:-1] != __version__.split(' ')[0][:-1] or pkl['url'] != url:
                    import warnings
                    warnings.warn('version or url mismatch! discarding cached wsdl', RuntimeWarning)
                    log.debug('Version: %s %s' % (pkl['version'], __version__))
                    log.debug('URL: %s %s' % (pkl['url'], url))
                    force_download = True
                else:
                    self.namespace = pkl['namespace']
                    self.documentation = pkl['documentation']
                    return pkl['services']

        soap_ns = {
            'http://schemas.xmlsoap.org/wsdl/soap/': 'soap11',
            'http://schemas.xmlsoap.org/wsdl/soap12/': 'soap12',
        }
        wsdl_uri = 'http://schemas.xmlsoap.org/wsdl/'
        xsd_uri = 'http://www.w3.org/2001/XMLSchema'
        xsi_uri = 'http://www.w3.org/2001/XMLSchema-instance'

        # always return an unicode object:
        REVERSE_TYPE_MAP['string'] = str

        # Open uri and read xml:
        xml = fetch(url, self.http, cache, force_download, self.wsdl_basedir)
        # Parse WSDL XML:
        wsdl = SimpleXMLElement(xml, namespace=wsdl_uri)

        # Extract useful data:
        self.namespace = ""
        self.documentation = unicode(wsdl('documentation', error=False)) or ''

        # some wsdl are splitted down in several files, join them:
        imported_wsdls = {}
        for element in wsdl.children() or []:
            if element.get_local_name() in ('import'):
                wsdl_namespace = element['namespace']
                wsdl_location = element['location']
                if wsdl_location is None:
                    log.warning('WSDL location not provided for %s!' % wsdl_namespace)
                    continue
                if wsdl_location in imported_wsdls:
                    log.warning('WSDL %s already imported!' % wsdl_location)
                    continue
                imported_wsdls[wsdl_location] = wsdl_namespace
                log.debug('Importing wsdl %s from %s' % (wsdl_namespace, wsdl_location))
                # Open uri and read xml:
                xml = fetch(wsdl_location, self.http, cache, force_download, self.wsdl_basedir)
                # Parse imported XML schema (recursively):
                imported_wsdl = SimpleXMLElement(xml, namespace=xsd_uri)
                # merge the imported wsdl into the main document:
                wsdl.import_node(imported_wsdl)
                # warning: do not process schemas to avoid infinite recursion!


        # detect soap prefix and uri (xmlns attributes of <definitions>)
        xsd_ns = None
        soap_uris = {}
        for k, v in wsdl[:]:
            if v in soap_ns and k.startswith('xmlns:'):
                soap_uris[get_local_name(k)] = v
            if v == xsd_uri and k.startswith('xmlns:'):
                xsd_ns = get_local_name(k)

        services = {}
        bindings = {}            # binding_name: binding
        operations = {}          # operation_name: operation
        port_type_bindings = {}  # port_type_name: binding
        messages = {}            # message: element
        elements = {}            # element: type def

        for service in wsdl("service", error=False) or []:
            service_name = service['name']
            if not service_name:
                continue  # empty service?
            serv = services.setdefault(service_name, {'ports': {}})
            serv['documentation'] = service['documentation'] or ''
            for port in service.port:
                binding_name = get_local_name(port['binding'])
                address = port('address', ns=list(soap_uris.values()), error=False)
                location = address and address['location'] or None
                soap_uri = address and soap_uris.get(address.get_prefix())
                soap_ver = soap_uri and soap_ns.get(soap_uri)
                bindings[binding_name] = {'name': binding_name,
                                          'service_name': service_name,
                                          'location': location,
                                          'soap_uri': soap_uri,
                                          'soap_ver': soap_ver, }
                serv['ports'][port['name']] = bindings[binding_name]

        # create an default service if none is given in the wsdl:
        if not services:
            serv = services[''] = {'ports': {'': None}} 

        for binding in wsdl.binding:
            binding_name = binding['name']
            soap_binding = binding('binding', ns=list(soap_uris.values()), error=False)
            transport = soap_binding and soap_binding['transport'] or None
            style = soap_binding and soap_binding['style'] or None  # rpc
            port_type_name = get_local_name(binding['type'])
            # create the binding in the default service: 
            if not binding_name in bindings:
                bindings[binding_name] = {'name': binding_name, 'style': style,
                                          'service_name': '', 'location': '', 
                                          'soap_uri': '', 'soap_ver': 'soap11'}
                serv['ports'][''] = bindings[binding_name]
            bindings[binding_name].update({
                'port_type_name': port_type_name,
                'transport': transport, 'operations': {},
            })
            if port_type_name not in port_type_bindings:
                port_type_bindings[port_type_name] = []
            port_type_bindings[port_type_name].append(bindings[binding_name])
            operations[binding_name] = {}
            for operation in binding.operation:
                op_name = operation['name']
                op = operation('operation', ns=list(soap_uris.values()), error=False)
                action = op and op['soapAction']
                d = operations[binding_name].setdefault(op_name, {})
                bindings[binding_name]['operations'][op_name] = d
                d.update({'name': op_name})
                d['parts'] = {}
                # input and/or ouput can be not present!
                input = operation('input', error=False)
                body = input and input('body', ns=list(soap_uris.values()), error=False)
                d['parts']['input_body'] = body and body['parts'] or None
                output = operation('output', error=False)
                body = output and output('body', ns=list(soap_uris.values()), error=False)
                d['parts']['output_body'] = body and body['parts'] or None
                # parse optional header messages (some implementations use more than one!)
                d['parts']['input_headers']  = []
                headers = input and input('header', ns=list(soap_uris.values()), error=False)
                for header in headers or []:
                    hdr = {'message': header['message'], 'part': header['part']}
                    d['parts']['input_headers'].append(hdr)
                d['parts']['output_headers']  = []
                headers = output and output('header', ns=list(soap_uris.values()), error=False)
                for header in headers or []:
                    hdr = {'message': header['message'], 'part': header['part']}
                    d['parts']['output_headers'].append(hdr)
                if action:
                    d['action'] = action

        # check axis2 namespace at schema types attributes (europa.eu checkVat)
        if "http://xml.apache.org/xml-soap" in dict(wsdl[:]).values(): 
            # get the sub-namespace in the first schema element (see issue 8)
            if wsdl('types', error=False):
                schema = wsdl.types('schema', ns=xsd_uri)
                attrs = dict(schema[:])
                self.namespace = attrs.get('targetNamespace', self.namespace)
            if not self.namespace or self.namespace == "urn:DefaultNamespace":
                self.namespace = wsdl['targetNamespace'] or self.namespace
                
        imported_schemas = {}
        global_namespaces = {None: self.namespace}

        # process current wsdl schema (if any):
        if wsdl('types', error=False):
            for schema in wsdl.types('schema', ns=xsd_uri):
                preprocess_schema(schema, imported_schemas, elements, xsd_uri, 
                                  self.__soap_server, self.http, cache, 
                                  force_download, self.wsdl_basedir, 
                                  global_namespaces=global_namespaces)

        # 2nd phase: alias, postdefined elements, extend bases, convert lists
        postprocess_element(elements, [])

        for message in wsdl.message:
            for part in message('part', error=False) or []:
                element = {}
                element_name = part['element']
                if not element_name:
                    # some implementations (axis) uses type instead
                    element_name = part['type']
                type_ns = get_namespace_prefix(element_name)
                type_uri = wsdl.get_namespace_uri(type_ns)
                part_name = part['name'] or None
                if type_uri == xsd_uri:
                    element_name = get_local_name(element_name)
                    fn = REVERSE_TYPE_MAP.get(element_name, None)
                    element = {part_name: fn}
                    # emulate a true Element (complexType) for rpc style
                    if (message['name'], part_name) not in messages:
                        od = Struct()
                        od.namespaces[None] = type_uri
                        messages[(message['name'], part_name)] = {message['name']: od}
                    else:
                        od = messages[(message['name'], part_name)].values()[0]
                    od.namespaces[part_name] = type_uri
                    od.references[part_name] = False
                    od.update(element)
                else:
                    element_name = get_local_name(element_name)
                    fn = elements.get(make_key(element_name, 'element', type_uri))
                    if not fn:
                        # some axis servers uses complexType for part messages (rpc)
                        fn = elements.get(make_key(element_name, 'complexType', type_uri))
                        od = Struct()
                        od[part_name] = fn
                        od.namespaces[None] = type_uri
                        od.namespaces[part_name] = type_uri
                        od.references[part_name] = False
                        element = {message['name']: od}
                    else:
                        element = {element_name: fn}
                    messages[(message['name'], part_name)] = element

        for port_type in wsdl.portType:
            port_type_name = port_type['name']

            for binding in port_type_bindings.get(port_type_name, []):
                for operation in port_type.operation:
                    op_name = operation['name']
                    op = operations[binding['name']][op_name]
                    op['style'] = operation['style'] or binding.get('style')
                    op['parameter_order'] = (operation['parameterOrder'] or "").split(" ")
                    op['documentation'] = unicode(operation('documentation', error=False)) or ''
                    if binding['soap_ver']:
                        #TODO: separe operation_binding from operation (non SOAP?)
                        if operation('input', error=False):
                            input_msg = get_local_name(operation.input['message'])
                            input_headers = op['parts'].get('input_headers')
                            headers = {}    # base header message structure
                            for input_header in input_headers:
                                header_msg = get_local_name(input_header.get('message'))
                                header_part = get_local_name(input_header.get('part'))
                                # warning: some implementations use a separate message!
                                hdr = get_message(messages, header_msg or input_msg, header_part)
                                if hdr:
                                    headers.update(hdr)
                                else:
                                    pass # not enought info to search the header message:
                            op['input'] = get_message(messages, input_msg, op['parts'].get('input_body'), op['parameter_order'])
                            op['header'] = headers
                            try:
                                element = list(op['input'].values())[0]
                                ns_uri = element.namespaces[None]
                                qualified = element.qualified
                            except (AttributeError, KeyError) as e:
                                # TODO: fix if no parameters parsed or "variants"
                                ns = get_namespace_prefix(operation.input['message'])
                                ns_uri = operation.get_namespace_uri(ns)
                                qualified = None
                            if ns_uri:
                                op['namespace'] = ns_uri
                                op['qualified'] = qualified
                        else:
                            op['input'] = None
                            op['header'] = None
                        if operation('output', error=False):
                            output_msg = get_local_name(operation.output['message'])
                            op['output'] = get_message(messages, output_msg, op['parts'].get('output_body'))
                        else:
                            op['output'] = None

        # dump the full service/port/operation map
        #log.debug(pprint.pformat(services))

        # Save parsed wsdl (cache)
        if cache:
            f = open(filename_pkl, "wb")
            pkl = {
                'version': __version__.split(' ')[0],
                'url': url,
                'namespace': self.namespace,
                'documentation': self.documentation,
                'services': services,
            }
            pickle.dump(pkl, f)
            f.close()

        return services

    def __setitem__(self, item, value):
        """Set SOAP Header value - this header will be sent for every request."""
        self.__headers[item] = value

    def close(self):
        """Finish the connection and remove temp files"""
        self.http.close()
        if self.cacert.startswith(tempfile.gettempdir()):
            log.debug('removing %s' % self.cacert)
            os.unlink(self.cacert)


def parse_proxy(proxy_str):
    """Parses proxy address user:pass@host:port into a dict suitable for httplib2"""
    proxy_dict = {}
    if proxy_str is None:
        return
    if '@' in proxy_str:
        user_pass, host_port = proxy_str.split('@')
    else:
        user_pass, host_port = '', proxy_str
    if ':' in host_port:
        host, port = host_port.split(':')
        proxy_dict['proxy_host'], proxy_dict['proxy_port'] = host, int(port)
    if ':' in user_pass:
        proxy_dict['proxy_user'], proxy_dict['proxy_pass'] = user_pass.split(':')
    return proxy_dict


if __name__ == '__main__':
    pass

########NEW FILE########
__FILENAME__ = helpers
#!/usr/bin/python
# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation; either version 3, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

"""Pythonic simple SOAP Client helpers"""


from __future__ import unicode_literals
import sys
if sys.version > '3':
    basestring = unicode = str

import datetime
from decimal import Decimal
import os
import logging
import hashlib
import warnings

try:
    import urllib2
    from urlparse import urlsplit
except ImportError:
    from urllib import request as urllib2
    from urllib.parse import urlsplit

from . import __author__, __copyright__, __license__, __version__


log = logging.getLogger(__name__)


def fetch(url, http, cache=False, force_download=False, wsdl_basedir=''):
    """Download a document from a URL, save it locally if cache enabled"""

    # check / append a valid schema if not given:
    url_scheme, netloc, path, query, fragment = urlsplit(url)
    if not url_scheme in ('http', 'https', 'file'):
        for scheme in ('http', 'https', 'file'):
            try:
                path = os.path.normpath(os.path.join(wsdl_basedir, url))
                if not url.startswith("/") and scheme in ('http', 'https'):
                    tmp_url = "%s://%s" % (scheme, path)
                else:
                    tmp_url = "%s:%s" % (scheme, path)
                log.debug('Scheme not found, trying %s' % scheme)
                return fetch(tmp_url, http, cache, force_download, wsdl_basedir)
            except Exception as e:
                log.error(e)
        raise RuntimeError('No scheme given for url: %s' % url)

    # make md5 hash of the url for caching...
    filename = '%s.xml' % hashlib.md5(url.encode('utf8')).hexdigest()
    if isinstance(cache, basestring):
        filename = os.path.join(cache, filename)
    if cache and os.path.exists(filename) and not force_download:
        log.info('Reading file %s' % filename)
        f = open(filename, 'r')
        xml = f.read()
        f.close()
    else:
        if url_scheme == 'file':
            log.info('Fetching url %s using urllib2' % url)
            f = urllib2.urlopen(url)
            xml = f.read()
        else:
            log.info('GET %s using %s' % (url, http._wrapper_version))
            response, xml = http.request(url, 'GET', None, {})
        if cache:
            log.info('Writing file %s' % filename)
            if not os.path.isdir(cache):
                os.makedirs(cache)
            f = open(filename, 'w')
            f.write(xml)
            f.close()
    return xml


def sort_dict(od, d):
    """Sort parameters (same order as xsd:sequence)"""
    if isinstance(od, dict):
        ret = Struct()
        for k in od.keys():
            v = d.get(k)
            # don't append null tags!
            if v is not None:
                if isinstance(v, dict):
                    v = sort_dict(od[k], v)
                elif isinstance(v, list):
                    v = [sort_dict(od[k][0], v1) for v1 in v]
                ret[k] = v
        if hasattr(od, 'namespaces'):
            ret.namespaces.update(od.namespaces)
            ret.references.update(od.references)
            ret.qualified = od.qualified
        return ret
    else:
        return d


def make_key(element_name, element_type, namespace):
    """Return a suitable key for elements"""
    # only distinguish 'element' vs other types
    if element_type in ('complexType', 'simpleType'):
        eltype = 'complexType'
    else:
        eltype = element_type
    if eltype not in ('element', 'complexType', 'simpleType'):
        raise RuntimeError("Unknown element type %s = %s" % (element_name, eltype))
    return (element_name, eltype, namespace)


def process_element(elements, element_name, node, element_type, xsd_uri, 
                    dialect, namespace, qualified=None,
                    soapenc_uri='http://schemas.xmlsoap.org/soap/encoding/',
                    struct=None):
    """Parse and define simple element types as Struct objects"""

    log.debug('Processing element %s %s' % (element_name, element_type))

    # iterate over inner tags of the element definition:
    for tag in node:
        
        # sanity checks (skip superfluous xml tags, resolve aliases, etc.):
        if tag.get_local_name() in ('annotation', 'documentation'):
            continue
        elif tag.get_local_name() in ('element', 'restriction', 'list'):
            log.debug('%s has no children! %s' % (element_name, tag))
            children = tag  # element "alias"?
            alias = True
        elif tag.children():
            children = tag.children()
            alias = False
        else:
            log.debug('%s has no children! %s' % (element_name, tag))
            continue  # TODO: abstract?

        # check if extending a previous processed element ("extension"):
        new_struct = struct is None
        if new_struct:
            struct = Struct()
            struct.namespaces[None] = namespace   # set the default namespace
            struct.qualified = qualified

        # iterate over the element's components (sub-elements):
        for e in children:

            # extract type information from xml attributes / children:
            t = e['type']
            if not t:
                t = e['itemType']  # xs:list
            if not t:
                t = e['base']  # complexContent (extension)!
            if not t:
                t = e['ref']   # reference to another element
            if not t:
                # "anonymous" elements had no type attribute but children
                if e['name'] and e.children():
                    # create a type name to process the children
                    t = "%s_%s" % (element_name, e['name'])  
                    c = e.children()
                    et = c.get_local_name()
                    c = c.children()
                    process_element(elements, t, c, et, xsd_uri, dialect, 
                                    namespace, qualified)
                else:
                    t = 'anyType'  # no type given!

            # extract namespace uri and type from xml attribute:
            t = t.split(":")
            if len(t) > 1:
                ns, type_name = t
            else:
                ns, type_name = None, t[0]
            if element_name == type_name and not alias and len(children) > 1:
                continue   # abort to prevent infinite recursion
            uri = ns and e.get_namespace_uri(ns) or xsd_uri

            # look for the conversion function (python type) 
            if uri in (xsd_uri, soapenc_uri) and type_name != 'Array':
                # look for the type, None == any
                fn = REVERSE_TYPE_MAP.get(type_name, None)
                if tag.get_local_name() == 'list':
                    # simple list type (values separated by spaces)
                    fn = lambda s: [fn(v) for v in s.split(" ")]
            elif (uri == soapenc_uri and type_name == 'Array'):
                # arrays of simple types (look at the attribute tags):
                fn = []
                for a in e.children():
                    for k, v in a[:]:
                        if k.endswith(":arrayType"):
                            type_name = v
                            fn_namespace = None
                            if ":" in type_name:
                                fn_uri, type_name = type_name.split(":")
                                fn_namespace = e.get_namespace_uri(fn_uri)
                            if "[]" in type_name:
                                type_name = type_name[:type_name.index("[]")]
                            # get the scalar conversion function (if any)
                            fn_array = REVERSE_TYPE_MAP.get(type_name, None)
                            if fn_array is None and type_name != "anyType" and fn_namespace:
                                # get the complext element:
                                ref_type = "complexType"
                                key = make_key(type_name, ref_type, fn_namespace)
                                fn_complex = elements.setdefault(key, Struct())
                                # create an indirect struct {type_name: ...}:
                                fn_array = Struct()
                                fn_array[type_name] = fn_complex
                                fn_array.namespaces[None] = fn_namespace   # set the default namespace
                                fn_array.qualified = qualified
                            fn.append(fn_array)
            else:
                # not a simple python type / conversion function not available
                fn = None

            if not fn:
                # simple / complex type, postprocess later
                if ns:
                    fn_namespace = uri       # use the specified namespace
                else:
                    fn_namespace = namespace # use parent namespace (default)
                for k, v in e[:]:
                    if k.startswith("xmlns:"):
                        # get the namespace uri from the element
                        fn_namespace = v        
                # create and store an empty python element (dict) filled later
                if not e['ref']:
                    ref_type = "complexType"
                else:
                    ref_type = "element"
                key = make_key(type_name, ref_type, fn_namespace)
                fn = elements.setdefault(key, Struct())

            if e['maxOccurs'] == 'unbounded' or (uri == soapenc_uri and type_name == 'Array'):
                # it's an array... TODO: compound arrays? and check ns uri!
                if isinstance(fn, Struct):
                    if len(children) > 1 or (dialect in ('jetty', )):
                        # Jetty style support
                        # {'ClassName': [{'attr1': val1, 'attr2': val2}]
                        fn.array = True
                    else:
                        # .NET style support (backward compatibility)
                        # [{'ClassName': {'attr1': val1, 'attr2': val2}]
                        struct.array = True
                else:
                    if len(children) > 1 or dialect in ('jetty',):
                        # Jetty style support
                        # scalar array support {'attr1': [val1]}
                        fn = [fn]
                    else:
                        # Jetty.NET style support (backward compatibility)
                        # scalar array support [{'attr1': val1}]
                        struct.array = True

            # store the sub-element python type (function) in the element dict
            if (e['name'] is not None and not alias) or e['ref']:
                e_name = e['name'] or type_name  # for refs, use the type name
                struct[e_name] = fn
                struct.references[e_name] = e['ref']                    
                struct.namespaces[e_name] = namespace  # set the element namespace
            else:
                log.debug('complexContent/simpleType/element %s = %s' % (element_name, type_name))
                # use None to point this is a complex element reference
                struct.refers_to = fn
            if e is not None and e.get_local_name() == 'extension' and e.children():
                # extend base element (if ComplexContent only!):
                if isinstance(fn, Struct) and fn.refers_to:
                    base_struct = fn.refers_to
                else:
                    # TODO: check if this actually works for SimpleContent
                    base_struct = None
                # extend base element:
                process_element(elements, element_name, e.children(), 
                                element_type, xsd_uri, dialect, namespace, 
                                qualified, struct=base_struct)

        # add the processed element to the main dictionary (if not extension):
        if new_struct:
            key = make_key(element_name, element_type, namespace)
            elements.setdefault(key, Struct()).update(struct)


def postprocess_element(elements, processed):
    """Fix unresolved references"""
    # (elements referenced before its definition, thanks .net)
    # avoid already processed elements:
    if elements in processed:
        return
    processed.append(elements)
    
    for k, v in elements.items():
        if isinstance(v, Struct):
            if v != elements:  # TODO: fix recursive elements
                try:
                    postprocess_element(v, processed)
                except RuntimeError as e:  # maximum recursion depth exceeded
                    warnings.warn(unicode(e), RuntimeWarning)
            if v.refers_to:  # extension base?
                if isinstance(v.refers_to, dict):
                    for i, kk in enumerate(v.refers_to):
                        # extend base -keep orginal order-
                        if isinstance(v.refers_to, Struct):
                            elements[k].insert(kk, v.refers_to[kk], i)
                            # update namespace (avoid ArrayOfKeyValueOfanyTypeanyType)
                            if isinstance(v.refers_to, Struct) and v.refers_to.namespaces and kk:
                                elements[k].namespaces[kk] = v.refers_to.namespaces[kk]
                                elements[k].references[kk] = v.refers_to.references[kk]
                    # clean the reference:
                    v.refers_to = None
                else:  # "alias", just replace
                    ##log.debug('Replacing %s = %s' % (k, v.refers_to))
                    elements[k] = v.refers_to
            if v.array:
                elements[k] = [v]  # convert arrays to python lists
        if isinstance(v, list):
            for n in v:  # recurse list
                if isinstance(n, (Struct, list)):
                    #if n != elements:  # TODO: fix recursive elements
                    postprocess_element(n, processed)


def get_message(messages, message_name, part_name, parameter_order=None):
    if part_name:
        # get the specific part of the message:
        return messages.get((message_name, part_name))
    else:
        # get the first part for the specified message:
        parts = {}
        for (message_name_key, part_name_key), message in messages.items():
            if message_name_key == message_name:
                parts[part_name_key] = message
        if len(parts)>1:
            # merge (sorted by parameter_order for rpc style)
            new_msg = None
            for part_name_key in parameter_order:
                part = parts.get(part_name_key)
                if not part:
                    log.error('Part %s not found for %s' % (part_name_key, message_name))
                elif not new_msg:
                    new_msg = part.copy()
                else:
                    new_msg[message_name].update(part[message_name])
            return new_msg
        elif parts:
            return list(parts.values())[0]
            #return parts.values()[0]



get_local_name = lambda s: s and str((':' in s) and s.split(':')[1] or s)
get_namespace_prefix = lambda s: s and str((':' in s) and s.split(':')[0] or None)


def preprocess_schema(schema, imported_schemas, elements, xsd_uri, dialect, 
                      http, cache, force_download, wsdl_basedir, 
                      global_namespaces=None, qualified=False):
    """Find schema elements and complex types"""

    from .simplexml import SimpleXMLElement    # here to avoid recursive imports

    # analyze the namespaces used in this schema
    local_namespaces = {}
    for k, v in schema[:]:
        if k.startswith("xmlns"):
            local_namespaces[get_local_name(k)] = v
        if k == 'targetNamespace':
            # URI namespace reference for this schema
            if v == "urn:DefaultNamespace":
                v = global_namespaces[None]
            local_namespaces[None] = v
        if k == 'elementFormDefault':
            qualified = (v == "qualified")
    # add schema namespaces to the global namespace dict = {URI: ns prefix}
    for ns in local_namespaces.values():
        if ns not in global_namespaces:
            global_namespaces[ns] = 'ns%s' % len(global_namespaces)
            
    for element in schema.children() or []:
        if element.get_local_name() in ('import', 'include',):
            schema_namespace = element['namespace']
            schema_location = element['schemaLocation']
            if schema_location is None:
                log.debug('Schema location not provided for %s!' % schema_namespace)
                continue
            if schema_location in imported_schemas:
                log.debug('Schema %s already imported!' % schema_location)
                continue
            imported_schemas[schema_location] = schema_namespace
            log.debug('Importing schema %s from %s' % (schema_namespace, schema_location))
            # Open uri and read xml:
            xml = fetch(schema_location, http, cache, force_download, wsdl_basedir)
            
            # recalculate base path for relative schema locations 
            path = os.path.normpath(os.path.join(wsdl_basedir, schema_location))
            path = os.path.dirname(path)

            # Parse imported XML schema (recursively):
            imported_schema = SimpleXMLElement(xml, namespace=xsd_uri)
            preprocess_schema(imported_schema, imported_schemas, elements, 
                              xsd_uri, dialect, http, cache, force_download, 
                              path, global_namespaces, qualified)

        element_type = element.get_local_name()
        if element_type in ('element', 'complexType', "simpleType"):
            namespace = local_namespaces[None]          # get targetNamespace
            element_ns = global_namespaces[ns]          # get the prefix
            element_name = element['name']
            log.debug("Parsing Element %s: %s" % (element_type, element_name))
            if element.get_local_name() == 'complexType':
                children = element.children()
            elif element.get_local_name() == 'simpleType':
                children = element('restriction', ns=xsd_uri, error=False)
                if not children:
                    children = element.children()       # xs:list
            elif element.get_local_name() == 'element' and element['type']:
                children = element
            else:
                children = element.children()
                if children:
                    children = children.children()
                elif element.get_local_name() == 'element':
                    children = element
            if children:
                process_element(elements, element_name, children, element_type,
                                xsd_uri, dialect, namespace, qualified)


# simplexml utilities:

try:
    _strptime = datetime.datetime.strptime
except AttributeError:  # python2.4
    _strptime = lambda s, fmt: datetime.datetime(*(time.strptime(s, fmt)[:6]))


# Functions to serialize/deserialize special immutable types:
def datetime_u(s):
    fmt = "%Y-%m-%dT%H:%M:%S"
    try:
        return _strptime(s, fmt)
    except ValueError:
        try:
            # strip utc offset
            if s[-3] == ":" and s[-6] in (' ', '-', '+'):
                warnings.warn('removing unsupported UTC offset', RuntimeWarning)
                s = s[:-6]
            # parse microseconds
            try:
                return _strptime(s, fmt + ".%f")
            except:
                return _strptime(s, fmt)
        except ValueError:
            # strip microseconds (not supported in this platform)
            if "." in s:
                warnings.warn('removing unsuppported microseconds', RuntimeWarning)
                s = s[:s.index(".")]
            return _strptime(s, fmt)


datetime_m = lambda dt: dt.isoformat()
date_u = lambda s: _strptime(s[0:10], "%Y-%m-%d").date()
date_m = lambda d: d.strftime("%Y-%m-%d")
time_u = lambda s: _strptime(s, "%H:%M:%S").time()
time_m = lambda d: d.strftime("%H%M%S")
bool_u = lambda s: {'0': False, 'false': False, '1': True, 'true': True}[s]
bool_m = lambda s: {False: 'false', True: 'true'}[s]


# aliases:
class Alias(object):
    def __init__(self, py_type, xml_type):
        self.py_type, self.xml_type = py_type, xml_type

    def __call__(self, value):
        return self.py_type(value)

    def __repr__(self):
        return "<alias '%s' for '%s'>" % (self.xml_type, self.py_type)

if sys.version > '3':
    long = Alias(int, 'long')
byte = Alias(str, 'byte')
short = Alias(int, 'short')
double = Alias(float, 'double')
integer = Alias(long, 'integer')
DateTime = datetime.datetime
Date = datetime.date
Time = datetime.time
duration = Alias(str, 'duration')

# Define convertion function (python type): xml schema type
TYPE_MAP = {
    unicode: 'string',
    bool: 'boolean',
    short: 'short',
    byte: 'byte',
    int: 'int',
    long: 'long',
    integer: 'integer',
    float: 'float',
    double: 'double',
    Decimal: 'decimal',
    datetime.datetime: 'dateTime',
    datetime.date: 'date',
    datetime.time: 'time',
    duration: 'duration',
}
TYPE_MARSHAL_FN = {
    datetime.datetime: datetime_m,
    datetime.date: date_m,
    datetime.time: time_m,
    bool: bool_m,
}
TYPE_UNMARSHAL_FN = {
    datetime.datetime: datetime_u,
    datetime.date: date_u,
    datetime.time: time_u,
    bool: bool_u,
    str: unicode,
}

REVERSE_TYPE_MAP = dict([(v, k) for k, v in TYPE_MAP.items()])

REVERSE_TYPE_MAP.update({
    'base64Binary': str,
})

# insert str here to avoid collision in REVERSE_TYPE_MAP (i.e. decoding errors)
if str not in TYPE_MAP:
    TYPE_MAP[str] = 'string'    


class Struct(dict):
    """Minimal ordered dictionary to represent elements (i.e. xsd:sequences)"""
    
    def __init__(self):
        self.__keys = []
        self.array = False
        self.namespaces = {}     # key: element, value: namespace URI
        self.references = {}     # key: element, value: reference name
        self.refers_to = None    # "symbolic linked" struct
        self.qualified = None

    def __setitem__(self, key, value):
        if key not in self.__keys:
            self.__keys.append(key)
        dict.__setitem__(self, key, value)

    def insert(self, key, value, index=0):
        if key not in self.__keys:
            self.__keys.insert(index, key)
        dict.__setitem__(self, key, value)

    def __delitem__(self, key):
        if key in self.__keys:
            self.__keys.remove(key)
        dict.__delitem__(self, key)

    def __iter__(self):
        return iter(self.__keys)

    def keys(self):
        return self.__keys

    def items(self):
        return [(key, self[key]) for key in self.__keys]

    def update(self, other):
        for k, v in other.items():
            self[k] = v
        # do not change if we are an array but the other is not:
        if isinstance(other, Struct) and not self.array:
            self.array = other.array
        if isinstance(other, Struct):
            # TODO: check replacing default ns is a regression 
            self.namespaces.update(other.namespaces)
            self.references.update(other.references)
            self.qualified = other.qualified
            self.refers_to = other.refers_to

    def copy(self):
        "Make a duplicate"
        new = Struct()
        new.update(self)
        return new

    def __str__(self):
        return "%s" % dict.__str__(self)

    def __repr__(self):
        try:
            s = "{%s}" % ", ".join(['%s: %s' % (repr(k), repr(v)) for k, v in self.items()])
        except RuntimeError as e:  # maximum recursion depth exceeded
            s = "{%s}" % ", ".join(['%s: %s' % (repr(k), unicode(e)) for k, v in self.items()])
            warnings.warn(unicode(e), RuntimeWarning)
        if self.array and False:
            s = "[%s]" % s
        return s

########NEW FILE########
__FILENAME__ = server
#!/usr/bin/python
# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

"""Pythonic simple SOAP Server implementation"""


from __future__ import unicode_literals
import sys
if sys.version > '3':
    unicode = str


import datetime
import sys
import logging
import warnings
import re
import traceback
try:
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
except ImportError:
    from http.server import BaseHTTPRequestHandler, HTTPServer

from . import __author__, __copyright__, __license__, __version__
from .simplexml import SimpleXMLElement, TYPE_MAP, Date, Decimal

log = logging.getLogger(__name__)

# Deprecated?
NS_RX = re.compile(r'xmlns:(\w+)="(.+?)"')


class SoapDispatcher(object):
    """Simple Dispatcher for SOAP Server"""

    def __init__(self, name, documentation='', action='', location='',
                 namespace=None, prefix=False,
                 soap_uri="http://schemas.xmlsoap.org/soap/envelope/",
                 soap_ns='soap',
                 namespaces={},
                 pretty=False,
                 debug=False,
                 **kwargs):
        """
        :param namespace: Target namespace; xmlns=targetNamespace
        :param prefix: Prefix for target namespace; xmlns:prefix=targetNamespace
        :param namespaces: Specify additional namespaces; example: {'external': 'http://external.mt.moboperator'}
        :param pretty: Prettifies generated xmls
        :param debug: Use to add tracebacks in generated xmls.

        Multiple namespaces
        ===================

        It is possible to support multiple namespaces.
        You need to specify additional namespaces by passing `namespace` parameter.

        >>> dispatcher = SoapDispatcher(
        ...    name = "MTClientWS",
        ...    location = "http://localhost:8008/ws/MTClientWS",
        ...    action = 'http://localhost:8008/ws/MTClientWS', # SOAPAction
        ...    namespace = "http://external.mt.moboperator", prefix="external",
        ...    documentation = 'moboperator MTClientWS',
        ...    namespaces = {
        ...        'external': 'http://external.mt.moboperator',
        ...        'model': 'http://model.common.mt.moboperator'
        ...    },
        ...    ns = True)

        Now the registered method must return node names with namespaces' prefixes.

        >>> def _multi_ns_func(self, serviceMsisdn):
        ...    ret = {
        ...        'external:activateSubscriptionsReturn': [
        ...            {'model:code': '0'},
        ...            {'model:description': 'desc'},
        ...        ]}
        ...    return ret

        Our prefixes will be changed to those used by the client.
        """
        self.methods = {}
        self.name = name
        self.documentation = documentation
        self.action = action  # base SoapAction
        self.location = location
        self.namespace = namespace  # targetNamespace
        self.prefix = prefix
        self.soap_ns = soap_ns
        self.soap_uri = soap_uri
        self.namespaces = namespaces
        self.pretty = pretty
        self.debug = debug

    @staticmethod
    def _extra_namespaces(xml, ns):
        """Extends xml with extra namespaces.
        :param ns: dict with namespaceUrl:prefix pairs
        :param xml: XML node to modify
        """
        if ns:
            _tpl = 'xmlns:%s="%s"'
            _ns_str = " ".join([_tpl % (prefix, uri) for uri, prefix in ns.items() if uri not in xml])
            xml = xml.replace('/>', ' ' + _ns_str + '/>')
        return xml

    def register_function(self, name, fn, returns=None, args=None, doc=None):
        self.methods[name] = fn, returns, args, doc or getattr(fn, "__doc__", "")

    def dispatch(self, xml, action=None, fault=None):
        """Receive and process SOAP call, returns the xml"""
        # a dict can be sent in fault to expose it to the caller
        # default values:
        prefix = self.prefix
        ret = None
        if fault is None:
            fault = {}
        soap_ns, soap_uri = self.soap_ns, self.soap_uri
        soap_fault_code = 'VersionMismatch'
        name = None

        # namespaces = [('model', 'http://model.common.mt.moboperator'), ('external', 'http://external.mt.moboperator')]
        _ns_reversed = dict(((v, k) for k, v in self.namespaces.items()))  # Switch keys-values
        # _ns_reversed = {'http://external.mt.moboperator': 'external', 'http://model.common.mt.moboperator': 'model'}

        try:
            request = SimpleXMLElement(xml, namespace=self.namespace)

            # detect soap prefix and uri (xmlns attributes of Envelope)
            for k, v in request[:]:
                if v in ("http://schemas.xmlsoap.org/soap/envelope/",
                         "http://www.w3.org/2003/05/soap-env",
                         "http://www.w3.org/2003/05/soap-envelope",):
                    soap_ns = request.attributes()[k].localName
                    soap_uri = request.attributes()[k].value

                # If the value from attributes on Envelope is in additional namespaces
                elif v in self.namespaces.values():
                    _ns = request.attributes()[k].localName
                    _uri = request.attributes()[k].value
                    _ns_reversed[_uri] = _ns  # update with received alias
                    # Now we change 'external' and 'model' to the received forms i.e. 'ext' and 'mod'
                # After that we know how the client has prefixed additional namespaces

            ns = NS_RX.findall(xml)
            for k, v in ns:
                if v in self.namespaces.values():
                    _ns_reversed[v] = k

            soap_fault_code = 'Client'

            # parse request message and get local method
            method = request('Body', ns=soap_uri).children()(0)
            if action:
                # method name = action
                name = action[len(self.action)+1:-1]
                prefix = self.prefix
            if not action or not name:
                # method name = input message name
                name = method.get_local_name()
                prefix = method.get_prefix()

            log.debug('dispatch method: %s', name)
            function, returns_types, args_types, doc = self.methods[name]
            log.debug('returns_types %s', returns_types)

            # de-serialize parameters (if type definitions given)
            if args_types:
                args = method.children().unmarshall(args_types)
            elif args_types is None:
                args = {'request': method}  # send raw request
            else:
                args = {}  # no parameters

            soap_fault_code = 'Server'
            # execute function
            ret = function(**args)
            log.debug('dispathed method returns: %s', ret)

        except Exception:  # This shouldn't be one huge try/except
            import sys
            etype, evalue, etb = sys.exc_info()
            log.error(traceback.format_exc())
            if self.debug:
                detail = ''.join(traceback.format_exception(etype, evalue, etb))
                detail += '\n\nXML REQUEST\n\n' + xml
            else:
                detail = None
            fault.update({'faultcode': "%s.%s" % (soap_fault_code, etype.__name__),
                     'faultstring': evalue,
                     'detail': detail})

        # build response message
        if not prefix:
            xml = """<%(soap_ns)s:Envelope xmlns:%(soap_ns)s="%(soap_uri)s"/>"""
        else:
            xml = """<%(soap_ns)s:Envelope xmlns:%(soap_ns)s="%(soap_uri)s"
                       xmlns:%(prefix)s="%(namespace)s"/>"""

        xml %= {    # a %= {} is a shortcut for a = a % {}
            'namespace': self.namespace,
            'prefix': prefix,
            'soap_ns': soap_ns,
            'soap_uri': soap_uri
        }

        # Now we add extra namespaces
        xml = SoapDispatcher._extra_namespaces(xml, _ns_reversed)

        # Change our namespace alias to that given by the client.
        # We put [('model', 'http://model.common.mt.moboperator'), ('external', 'http://external.mt.moboperator')]
        # mix it with {'http://external.mt.moboperator': 'ext', 'http://model.common.mt.moboperator': 'mod'}
        mapping = dict(((k, _ns_reversed[v]) for k, v in self.namespaces.items()))  # Switch keys-values and change value
        # and get {'model': u'mod', 'external': u'ext'}

        response = SimpleXMLElement(xml,
                                    namespace=self.namespace,
                                    namespaces_map=mapping,
                                    prefix=prefix)

        response['xmlns:xsi'] = "http://www.w3.org/2001/XMLSchema-instance"
        response['xmlns:xsd'] = "http://www.w3.org/2001/XMLSchema"

        body = response.add_child("%s:Body" % soap_ns, ns=False)

        if fault:
            # generate a Soap Fault (with the python exception)
            body.marshall("%s:Fault" % soap_ns, fault, ns=False)
        else:
            # return normal value
            res = body.add_child("%sResponse" % name, ns=prefix)
            if not prefix:
                res['xmlns'] = self.namespace  # add target namespace

            # serialize returned values (response) if type definition available
            if returns_types:
                # TODO: full sanity check of type structure (recursive)
                complex_type = isinstance(ret, dict)
                if complex_type:
                    # check if type mapping correlates with return value
                    types_ok = all([k in returns_types for k in ret.keys()])
                    if not types_ok:
                        warnings.warn("Return value doesn't match type structure: "
                                     "%s vs %s" % (str(returns_types), str(ret)))
                if not complex_type or not types_ok:
                    # backward compatibility for scalar and simple types
                    res.marshall(list(returns_types.keys())[0], ret, )
                else:
                    # new style for complex classes
                    for k, v in ret.items():
                        res.marshall(k, v)
            elif returns_types is None:
                # merge xmlelement returned
                res.import_node(ret)
            elif returns_types == {}:
                log.warning('Given returns_types is an empty dict.')

        return response.as_xml(pretty=self.pretty)

    # Introspection functions:

    def list_methods(self):
        """Return a list of aregistered operations"""
        return [(method, doc) for method, (function, returns, args, doc) in self.methods.items()]

    def help(self, method=None):
        """Generate sample request and response messages"""
        (function, returns, args, doc) = self.methods[method]
        xml = """
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
<soap:Body><%(method)s xmlns="%(namespace)s"/></soap:Body>
</soap:Envelope>""" % {'method': method, 'namespace': self.namespace}
        request = SimpleXMLElement(xml, namespace=self.namespace, prefix=self.prefix)
        if args:
            items = args.items()
        elif args is None:
            items = [('value', None)]
        else:
            items = []
        for k, v in items:
            request(method).marshall(k, v, add_comments=True, ns=False)

        xml = """
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
<soap:Body><%(method)sResponse xmlns="%(namespace)s"/></soap:Body>
</soap:Envelope>""" % {'method': method, 'namespace': self.namespace}
        response = SimpleXMLElement(xml, namespace=self.namespace, prefix=self.prefix)
        if returns:
            items = returns.items()
        elif args is None:
            items = [('value', None)]
        else:
            items = []
        for k, v in items:
            response('%sResponse' % method).marshall(k, v, add_comments=True, ns=False)

        return request.as_xml(pretty=True), response.as_xml(pretty=True), doc

    def wsdl(self):
        """Generate Web Service Description v1.1"""
        xml = """<?xml version="1.0"?>
<wsdl:definitions name="%(name)s"
          targetNamespace="%(namespace)s"
          xmlns:tns="%(namespace)s"
          xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
          xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"
          xmlns:xsd="http://www.w3.org/2001/XMLSchema">
    <wsdl:documentation xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/">%(documentation)s</wsdl:documentation>

    <wsdl:types>
       <xsd:schema targetNamespace="%(namespace)s"
              elementFormDefault="qualified"
              xmlns:xsd="http://www.w3.org/2001/XMLSchema">
       </xsd:schema>
    </wsdl:types>

</wsdl:definitions>
""" % {'namespace': self.namespace, 'name': self.name, 'documentation': self.documentation}
        wsdl = SimpleXMLElement(xml)

        for method, (function, returns, args, doc) in self.methods.items():
            # create elements:

            def parse_element(name, values, array=False, complex=False):
                if not complex:
                    element = wsdl('wsdl:types')('xsd:schema').add_child('xsd:element')
                    complex = element.add_child("xsd:complexType")
                else:
                    complex = wsdl('wsdl:types')('xsd:schema').add_child('xsd:complexType')
                    element = complex
                element['name'] = name
                if values:
                    items = values
                elif values is None:
                    items = [('value', None)]
                else:
                    items = []
                if not array and items:
                    all = complex.add_child("xsd:all")
                elif items:
                    all = complex.add_child("xsd:sequence")
                for k, v in items:
                    e = all.add_child("xsd:element")
                    e['name'] = k
                    if array:
                        e[:] = {'minOccurs': "0", 'maxOccurs': "unbounded"}
                    if v in TYPE_MAP.keys():
                        t = 'xsd:%s' % TYPE_MAP[v]
                    elif v is None:
                        t = 'xsd:anyType'
                    elif isinstance(v, list):
                        n = "ArrayOf%s%s" % (name, k)
                        l = []
                        for d in v:
                            l.extend(d.items())
                        parse_element(n, l, array=True, complex=True)
                        t = "tns:%s" % n
                    elif isinstance(v, dict):
                        n = "%s%s" % (name, k)
                        parse_element(n, v.items(), complex=True)
                        t = "tns:%s" % n
                    else:
                        raise TypeError("unknonw type v for marshalling" % str(v))
                    e.add_attribute('type', t)

            parse_element("%s" % method, args and args.items())
            parse_element("%sResponse" % method, returns and returns.items())

            # create messages:
            for m, e in ('Input', ''), ('Output', 'Response'):
                message = wsdl.add_child('wsdl:message')
                message['name'] = "%s%s" % (method, m)
                part = message.add_child("wsdl:part")
                part[:] = {'name': 'parameters',
                           'element': 'tns:%s%s' % (method, e)}

        # create ports
        portType = wsdl.add_child('wsdl:portType')
        portType['name'] = "%sPortType" % self.name
        for method, (function, returns, args, doc) in self.methods.items():
            op = portType.add_child('wsdl:operation')
            op['name'] = method
            if doc:
                op.add_child("wsdl:documentation", doc)
            input = op.add_child("wsdl:input")
            input['message'] = "tns:%sInput" % method
            output = op.add_child("wsdl:output")
            output['message'] = "tns:%sOutput" % method

        # create bindings
        binding = wsdl.add_child('wsdl:binding')
        binding['name'] = "%sBinding" % self.name
        binding['type'] = "tns:%sPortType" % self.name
        soapbinding = binding.add_child('soap:binding')
        soapbinding['style'] = "document"
        soapbinding['transport'] = "http://schemas.xmlsoap.org/soap/http"
        for method in self.methods.keys():
            op = binding.add_child('wsdl:operation')
            op['name'] = method
            soapop = op.add_child('soap:operation')
            soapop['soapAction'] = self.action + method
            soapop['style'] = 'document'
            input = op.add_child("wsdl:input")
            ##input.add_attribute('name', "%sInput" % method)
            soapbody = input.add_child("soap:body")
            soapbody["use"] = "literal"
            output = op.add_child("wsdl:output")
            ##output.add_attribute('name', "%sOutput" % method)
            soapbody = output.add_child("soap:body")
            soapbody["use"] = "literal"

        service = wsdl.add_child('wsdl:service')
        service["name"] = "%sService" % self.name
        service.add_child('wsdl:documentation', text=self.documentation)
        port = service.add_child('wsdl:port')
        port["name"] = "%s" % self.name
        port["binding"] = "tns:%sBinding" % self.name
        soapaddress = port.add_child('soap:address')
        soapaddress["location"] = self.location
        return wsdl.as_xml(pretty=True)


class SOAPHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        """User viewable help information and wsdl"""
        args = self.path[1:].split("?")
        if self.path != "/" and args[0] not in self.server.dispatcher.methods.keys():
            self.send_error(404, "Method not found: %s" % args[0])
        else:
            if self.path == "/":
                # return wsdl if no method supplied
                response = self.server.dispatcher.wsdl()
            else:
                # return supplied method help (?request or ?response messages)
                req, res, doc = self.server.dispatcher.help(args[0])
                if len(args) == 1 or args[1] == "request":
                    response = req
                else:
                    response = res
            self.send_response(200)
            self.send_header("Content-type", "text/xml")
            self.end_headers()
            self.wfile.write(response)

    def do_POST(self):
        """SOAP POST gateway"""
        request = self.rfile.read(int(self.headers.get('content-length')))
        # convert xml request to unicode (according to request headers)
        if sys.version < '3':
            encoding = self.headers.getparam("charset")
        else:
            encoding = self.headers.get_param("charset")
        request = request.decode(encoding)
        fault = {}
        # execute the method
        response = self.server.dispatcher.dispatch(request, fault=fault)
        # check if fault dict was completed (faultcode, faultstring, detail)
        if fault:
            self.send_response(500)
        else:
            self.send_response(200)
        self.send_header("Content-type", "text/xml")
        self.end_headers()
        self.wfile.write(response)


class WSGISOAPHandler(object):

    def __init__(self, dispatcher):
        self.dispatcher = dispatcher

    def __call__(self, environ, start_response):
        return self.handler(environ, start_response)

    def handler(self, environ, start_response):
        if environ['REQUEST_METHOD'] == 'GET':
            return self.do_get(environ, start_response)
        elif environ['REQUEST_METHOD'] == 'POST':
            return self.do_post(environ, start_response)
        else:
            start_response('405 Method not allowed', [('Content-Type', 'text/plain')])
            return ['Method not allowed']

    def do_get(self, environ, start_response):
        path = environ.get('PATH_INFO').lstrip('/')
        query = environ.get('QUERY_STRING')
        if path != "" and path not in self.dispatcher.methods.keys():
            start_response('404 Not Found', [('Content-Type', 'text/plain')])
            return ["Method not found: %s" % path]
        elif path == "":
            # return wsdl if no method supplied
            response = self.dispatcher.wsdl()
        else:
            # return supplied method help (?request or ?response messages)
            req, res, doc = self.dispatcher.help(path)
            if len(query) == 0 or query == "request":
                response = req
            else:
                response = res
        start_response('200 OK', [('Content-Type', 'text/xml'), ('Content-Length', str(len(response)))])
        return [response]

    def do_post(self, environ, start_response):
        length = int(environ['CONTENT_LENGTH'])
        request = environ['wsgi.input'].read(length)
        response = self.dispatcher.dispatch(request)
        start_response('200 OK', [('Content-Type', 'text/xml'), ('Content-Length', str(len(response)))])
        return [response]


if __name__ == "__main__":

    dispatcher = SoapDispatcher(
        name="PySimpleSoapSample",
        location="http://localhost:8008/",
        action='http://localhost:8008/',  # SOAPAction
        namespace="http://example.com/pysimplesoapsamle/", prefix="ns0",
        documentation='Example soap service using PySimpleSoap',
        trace=True, debug=True,
        ns=True)

    def adder(p, c, dt=None):
        """Add several values"""
        dt = dt + datetime.timedelta(365)
        return {'ab': p['a'] + p['b'], 'dd': c[0]['d'] + c[1]['d'], 'dt': dt}

    def dummy(in0):
        """Just return input"""
        return in0

    def echo(request):
        """Copy request->response (generic, any type)"""
        return request.value

    dispatcher.register_function(
        'Adder', adder,
        returns={'AddResult': {'ab': int, 'dd': unicode, 'dt': datetime.date}},
        args={'p': {'a': int, 'b': int}, 'dt': Date, 'c': [{'d': Decimal}]}
    )

    dispatcher.register_function(
        'Dummy', dummy,
        returns={'out0': str},
        args={'in0': str}
    )

    dispatcher.register_function('Echo', echo)

    if '--local' in sys.argv:

        wsdl = dispatcher.wsdl()

        for method, doc in dispatcher.list_methods():
            request, response, doc = dispatcher.help(method)

    if '--serve' in sys.argv:
        log.info("Starting server...")
        httpd = HTTPServer(("", 8008), SOAPHandler)
        httpd.dispatcher = dispatcher
        httpd.serve_forever()

    if '--wsgi-serve' in sys.argv:
        log.info("Starting wsgi server...")
        from wsgiref.simple_server import make_server
        application = WSGISOAPHandler(dispatcher)
        wsgid = make_server('', 8008, application)
        wsgid.serve_forever()

    if '--consume' in sys.argv:
        from .client import SoapClient
        client = SoapClient(
            location="http://localhost:8008/",
            action='http://localhost:8008/',  # SOAPAction
            namespace="http://example.com/sample.wsdl",
            soap_ns='soap',
            trace=True,
            ns=False
        )
        p = {'a': 1, 'b': 2}
        c = [{'d': '1.20'}, {'d': '2.01'}]
        response = client.Adder(p=p, dt='2010-07-24', c=c)
        result = response.AddResult
        log.info(int(result.ab))
        log.info(str(result.dd))
        
    if '--consume-wsdl' in sys.argv:
        from .client import SoapClient
        client = SoapClient(
            wsdl="http://localhost:8008/",
        )
        p = {'a': 1, 'b': 2}
        c = [{'d': '1.20'}, {'d': '2.01'}]
        dt = datetime.date.today()
        response = client.Adder(p=p, dt=dt, c=c)
        result = response['AddResult']
        log.info(int(result['ab']))
        log.info(str(result['dd']))


########NEW FILE########
__FILENAME__ = simplexml
#!/usr/bin/python
# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

"""Simple XML manipulation"""


from __future__ import unicode_literals
import sys
if sys.version > '3':
    basestring = str
    unicode = str

import logging
import re
import time
import xml.dom.minidom

from . import __author__, __copyright__, __license__, __version__

# Utility functions used for marshalling, moved aside for readability
from .helpers import TYPE_MAP, TYPE_MARSHAL_FN, TYPE_UNMARSHAL_FN, \
                     REVERSE_TYPE_MAP, Struct, Date, Decimal

log = logging.getLogger(__name__)


class SimpleXMLElement(object):
    """Simple XML manipulation (simil PHP)"""

    def __init__(self, text=None, elements=None, document=None,
                 namespace=None, prefix=None, namespaces_map={}, jetty=False):
        """
        :param namespaces_map: How to map our namespace prefix to that given by the client;
          {prefix: received_prefix}
        """
        self.__namespaces_map = namespaces_map
        _rx = "|".join(namespaces_map.keys())  # {'external': 'ext', 'model': 'mod'} -> 'external|model'
        self.__ns_rx = re.compile(r"^(%s):.*$" % _rx)  # And now we build an expression ^(external|model):.*$
                                                       # to find prefixes in all xml nodes i.e.: <model:code>1</model:code>
                                                       # and later change that to <mod:code>1</mod:code>
        self.__ns = namespace
        self.__prefix = prefix
        self.__jetty = jetty                           # special list support

        if text is not None:
            try:
                self.__document = xml.dom.minidom.parseString(text)
            except:
                log.error(text)
                raise
            self.__elements = [self.__document.documentElement]
        else:
            self.__elements = elements
            self.__document = document

    def add_child(self, name, text=None, ns=True):
        """Adding a child tag to a node"""
        if not ns or self.__ns is False:
            ##log.debug('adding %s without namespace', name)
            element = self.__document.createElement(name)
        else:
            ##log.debug('adding %s ns "%s" %s', name, self.__ns, ns)
            if isinstance(ns, basestring):
                element = self.__document.createElement(name)
                if ns:
                    element.setAttribute("xmlns", ns)
            elif self.__prefix:
                element = self.__document.createElementNS(self.__ns, "%s:%s" % (self.__prefix, name))
            else:
                element = self.__document.createElementNS(self.__ns, name)
        # don't append null tags!
        if text is not None:
            element.appendChild(self.__document.createTextNode(text))
        self._element.appendChild(element)
        return SimpleXMLElement(
            elements=[element],
            document=self.__document,
            namespace=self.__ns,
            prefix=self.__prefix,
            jetty=self.__jetty,
            namespaces_map=self.__namespaces_map
        )

    def __setattr__(self, tag, text):
        """Add text child tag node (short form)"""
        if tag.startswith("_"):
            object.__setattr__(self, tag, text)
        else:
            ##log.debug('__setattr__(%s, %s)', tag, text)
            self.add_child(tag, text)

    def __delattr__(self, tag):
        """Remove a child tag (non recursive!)"""
        elements = [__element for __element in self._element.childNodes
                    if __element.nodeType == __element.ELEMENT_NODE]
        for element in elements:
            self._element.removeChild(element)

    def add_comment(self, data):
        """Add an xml comment to this child"""
        comment = self.__document.createComment(data)
        self._element.appendChild(comment)

    def as_xml(self, filename=None, pretty=False):
        """Return the XML representation of the document"""
        if not pretty:
            return self.__document.toxml('UTF-8')
        else:
            return self.__document.toprettyxml(encoding='UTF-8')

    if sys.version > '3':
        def __repr__(self):
            """Return the XML representation of this tag"""
            return self._element.toxml()
    else:
        def __repr__(self):
            """Return the XML representation of this tag"""
            # NOTE: do not use self.as_xml('UTF-8') as it returns the whole xml doc
            return self._element.toxml('UTF-8')

    def get_name(self):
        """Return the tag name of this node"""
        return self._element.tagName

    def get_local_name(self):
        """Return the tag local name (prefix:name) of this node"""
        return self._element.localName

    def get_prefix(self):
        """Return the namespace prefix of this node"""
        return self._element.prefix

    def get_namespace_uri(self, ns):
        """Return the namespace uri for a prefix"""
        element = self._element
        while element is not None and element.attributes is not None:
            try:
                return element.attributes['xmlns:%s' % ns].value
            except KeyError:
                element = element.parentNode

    def attributes(self):
        """Return a dict of attributes for this tag"""
        #TODO: use slice syntax [:]?
        return self._element.attributes

    def __getitem__(self, item):
        """Return xml tag attribute value or a slice of attributes (iter)"""
        ##log.debug('__getitem__(%s)', item)
        if isinstance(item, basestring):
            if self._element.hasAttribute(item):
                return self._element.attributes[item].value
        elif isinstance(item, slice):
            # return a list with name:values
            return list(self._element.attributes.items())[item]
        else:
            # return element by index (position)
            element = self.__elements[item]
            return SimpleXMLElement(
                elements=[element],
                document=self.__document,
                namespace=self.__ns,
                prefix=self.__prefix,
                jetty=self.__jetty,
                namespaces_map=self.__namespaces_map
            )

    def add_attribute(self, name, value):
        """Set an attribute value from a string"""
        self._element.setAttribute(name, value)

    def __setitem__(self, item, value):
        """Set an attribute value"""
        if isinstance(item, basestring):
            self.add_attribute(item, value)
        elif isinstance(item, slice):
            # set multiple attributes at once
            for k, v in value.items():
                self.add_attribute(k, v)

    def __call__(self, tag=None, ns=None, children=False, root=False,
                 error=True, ):
        """Search (even in child nodes) and return a child tag by name"""
        try:
            if root:
                # return entire document
                return SimpleXMLElement(
                    elements=[self.__document.documentElement],
                    document=self.__document,
                    namespace=self.__ns,
                    prefix=self.__prefix,
                    jetty=self.__jetty,
                    namespaces_map=self.__namespaces_map
                )
            if tag is None:
                # if no name given, iterate over siblings (same level)
                return self.__iter__()
            if children:
                # future: filter children? by ns?
                return self.children()
            elements = None
            if isinstance(tag, int):
                # return tag by index
                elements = [self.__elements[tag]]
            if ns and not elements:
                for ns_uri in isinstance(ns, (tuple, list)) and ns or (ns, ):
                    ##log.debug('searching %s by ns=%s', tag, ns_uri)
                    elements = self._element.getElementsByTagNameNS(ns_uri, tag)
                    if elements:
                        break
            if self.__ns and not elements:
                ##log.debug('searching %s by ns=%s', tag, self.__ns)
                elements = self._element.getElementsByTagNameNS(self.__ns, tag)
            if not elements:
                ##log.debug('searching %s', tag)
                elements = self._element.getElementsByTagName(tag)
            if not elements:
                ##log.debug(self._element.toxml())
                if error:
                    raise AttributeError("No elements found")
                else:
                    return
            return SimpleXMLElement(
                elements=elements,
                document=self.__document,
                namespace=self.__ns,
                prefix=self.__prefix,
                jetty=self.__jetty,
                namespaces_map=self.__namespaces_map)
        except AttributeError as e:
            raise AttributeError("Tag not found: %s (%s)" % (tag, e))

    def __getattr__(self, tag):
        """Shortcut for __call__"""
        return self.__call__(tag)

    def __iter__(self):
        """Iterate over xml tags at this level"""
        try:
            for __element in self.__elements:
                yield SimpleXMLElement(
                    elements=[__element],
                    document=self.__document,
                    namespace=self.__ns,
                    prefix=self.__prefix,
                    jetty=self.__jetty,
                    namespaces_map=self.__namespaces_map)
        except:
            raise

    def __dir__(self):
        """List xml children tags names"""
        return [node.tagName for node
                in self._element.childNodes
                if node.nodeType != node.TEXT_NODE]

    def children(self):
        """Return xml children tags element"""
        elements = [__element for __element in self._element.childNodes
                    if __element.nodeType == __element.ELEMENT_NODE]
        if not elements:
            return None
            #raise IndexError("Tag %s has no children" % self._element.tagName)
        return SimpleXMLElement(
            elements=elements,
            document=self.__document,
            namespace=self.__ns,
            prefix=self.__prefix,
            jetty=self.__jetty,
            namespaces_map=self.__namespaces_map
        )

    def __len__(self):
        """Return element count"""
        return len(self.__elements)

    def __contains__(self, item):
        """Search for a tag name in this element or child nodes"""
        return self._element.getElementsByTagName(item)

    def __unicode__(self):
        """Returns the unicode text nodes of the current element"""
        rc = ''
        for node in self._element.childNodes:
            if node.nodeType == node.TEXT_NODE:
                rc = rc + node.data
        return rc

    if sys.version > '3':
        __str__ = __unicode__
    else:
        def __str__(self):
            return self.__unicode__().encode('utf-8')

    def __int__(self):
        """Returns the integer value of the current element"""
        return int(self.__str__())

    def __float__(self):
        """Returns the float value of the current element"""
        try:
            return float(self.__str__())
        except:
            raise IndexError(self._element.toxml())

    _element = property(lambda self: self.__elements[0])

    def unmarshall(self, types, strict=True):
        #import pdb; pdb.set_trace()

        """Convert to python values the current serialized xml element"""
        # types is a dict of {tag name: convertion function}
        # strict=False to use default type conversion if not specified
        # example: types={'p': {'a': int,'b': int}, 'c': [{'d':str}]}
        #   expected xml: <p><a>1</a><b>2</b></p><c><d>hola</d><d>chau</d>
        #   returnde value: {'p': {'a':1,'b':2}, `'c':[{'d':'hola'},{'d':'chau'}]}
        d = {}
        for node in self():
            name = str(node.get_local_name())
            ref_name_type = None
            # handle multirefs: href="#id0"
            if 'href' in node.attributes().keys():
                href = node['href'][1:]
                for ref_node in self(root=True)("multiRef"):
                    if ref_node['id'] == href:
                        node = ref_node
                        ref_name_type = ref_node['xsi:type'].split(":")[1]
                        break             

            try:
                if isinstance(types, dict):
                    fn = types[name]
                    # custom array only in the response (not defined in the WSDL):
                    # <results soapenc:arrayType="xsd:string[199]>
                    if any([k for k,v in node[:] if 'arrayType' in k]) and not isinstance(fn, list):
                        fn = [fn]
                else:
                    fn = types
            except (KeyError, ) as e:
                xmlns = node['xmlns'] or node.get_namespace_uri(node.get_prefix())
                if 'xsi:type' in node.attributes().keys():
                    xsd_type = node['xsi:type'].split(":")[1]
                    try:
                        # get fn type from SOAP-ENC:arrayType="xsd:string[28]"
                        if xsd_type == 'Array':
                            array_type = [k for k,v in node[:] if 'arrayType' in k][0]
                            xsd_type = node[array_type].split(":")[1]
                            if "[" in xsd_type:
                                xsd_type = xsd_type[:xsd_type.index("[")]
                            fn = [REVERSE_TYPE_MAP[xsd_type]]
                        else:
                            fn = REVERSE_TYPE_MAP[xsd_type]
                    except:
                        fn = None  # ignore multirefs!
                elif xmlns == "http://www.w3.org/2001/XMLSchema":
                    # self-defined schema, return the SimpleXMLElement
                    # TODO: parse to python types if <s:element ref="s:schema"/>
                    fn = None
                elif None in types:
                    # <s:any/>, return the SimpleXMLElement 
                    # TODO: check position of None if inside <s:sequence>
                    fn = None
                elif strict:
                    raise TypeError("Tag: %s invalid (type not found)" % (name,))
                else:
                    # if not strict, use default type conversion
                    fn = str

            if isinstance(fn, list):
                # append to existing list (if any) - unnested dict arrays -
                value = d.setdefault(name, [])
                children = node.children()
                # TODO: check if this was really needed (get first child only)
                ##if len(fn[0]) == 1 and children:
                ##    children = children()
                if fn and not isinstance(fn[0], dict):
                    # simple arrays []
                    for child in (children or []):
                        tmp_dict = child.unmarshall(fn[0], strict)
                        value.extend(tmp_dict.values())
                elif (self.__jetty and len(fn[0]) > 1):
                    # Jetty array style support [{k, v}]
                    for parent in node:
                        tmp_dict = {}    # unmarshall each value & mix
                        for child in (node.children() or []):
                            tmp_dict.update(child.unmarshall(fn[0], strict))
                        value.append(tmp_dict)
                else:  # .Net / Java
                    for child in (children or []):
                        value.append(child.unmarshall(fn[0], strict))

            elif isinstance(fn, tuple):
                value = []
                _d = {}
                children = node.children()
                as_dict = len(fn) == 1 and isinstance(fn[0], dict)

                for child in (children and children() or []):  # Readability counts
                    if as_dict:
                        _d.update(child.unmarshall(fn[0], strict))  # Merging pairs
                    else:
                        value.append(child.unmarshall(fn[0], strict))
                if as_dict:
                    value.append(_d)

                if name in d:
                    _tmp = list(d[name])
                    _tmp.extend(value)
                    value = tuple(_tmp)
                else:
                    value = tuple(value)

            elif isinstance(fn, dict):
                ##if ref_name_type is not None:
                ##    fn = fn[ref_name_type]
                children = node.children()
                value = children and children.unmarshall(fn, strict)
            else:
                if fn is None:  # xsd:anyType not unmarshalled
                    value = node
                elif unicode(node) or (fn == str and unicode(node) != ''):
                    try:
                        # get special deserialization function (if any)
                        fn = TYPE_UNMARSHAL_FN.get(fn, fn)
                        if fn == str:
                            # always return an unicode object:
                            # (avoid encoding errors in py<3!)
                            value = unicode(node)
                        else:
                            value = fn(unicode(node))
                    except (ValueError, TypeError) as e:
                        raise ValueError("Tag: %s: %s" % (name, e))
                else:
                    value = None
            d[name] = value
        return d

    def _update_ns(self, name):
        """Replace the defined namespace alias with tohse used by the client."""
        pref = self.__ns_rx.search(name)
        if pref:
            pref = pref.groups()[0]
            try:
                name = name.replace(pref, self.__namespaces_map[pref])
            except KeyError:
                log.warning('Unknown namespace alias %s' % name)
        return name

    def marshall(self, name, value, add_child=True, add_comments=False,
                 ns=False, add_children_ns=True):
        """Analyze python value and add the serialized XML element using tag name"""
        # Change node name to that used by a client
        name = self._update_ns(name)

        if isinstance(value, dict):  # serialize dict (<key>value</key>)
            # for the first parent node, use the document target namespace
            # (ns==True) or use the namespace string uri if passed (elements)
            child = add_child and self.add_child(name, ns=ns) or self
            for k, v in value.items():
                if not add_children_ns:
                    ns = False
                elif hasattr(value, 'namespaces'):
                    # for children, use the wsdl element target namespace:
                    ns = value.namespaces.get(k)
                else:
                    # simple type
                    ns = None
                child.marshall(k, v, add_comments=add_comments, ns=ns)
        elif isinstance(value, tuple):  # serialize tuple (<key>value</key>)
            child = add_child and self.add_child(name, ns=ns) or self
            if not add_children_ns:
                ns = False
            for k, v in value:
                getattr(self, name).marshall(k, v, add_comments=add_comments, ns=ns)
        elif isinstance(value, list):  # serialize lists
            child = self.add_child(name, ns=ns)
            if not add_children_ns:
                ns = False
            if add_comments:
                child.add_comment("Repetitive array of:")
            for t in value:
                child.marshall(name, t, False, add_comments=add_comments, ns=ns)
        elif isinstance(value, basestring):  # do not convert strings or unicodes
            self.add_child(name, value, ns=ns)
        elif value is None:  # sent a empty tag?
            self.add_child(name, ns=ns)
        elif value in TYPE_MAP.keys():
            # add commented placeholders for simple tipes (for examples/help only)
            child = self.add_child(name, ns=ns)
            child.add_comment(TYPE_MAP[value])
        else:  # the rest of object types are converted to string
            # get special serialization function (if any)
            fn = TYPE_MARSHAL_FN.get(type(value), str)
            self.add_child(name, fn(value), ns=ns)

    def import_node(self, other):
        x = self.__document.importNode(other._element, True)  # deep copy
        self._element.appendChild(x)

########NEW FILE########
__FILENAME__ = transport
#!/usr/bin/python
# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

"""Pythonic simple SOAP Client transport"""


import logging
import sys
try:
    import urllib2
    from cookielib import CookieJar
except ImportError:
    from urllib import request as urllib2
    from http.cookiejar import CookieJar

from . import __author__, __copyright__, __license__, __version__, TIMEOUT
from .simplexml import SimpleXMLElement, TYPE_MAP, Struct

log = logging.getLogger(__name__)

#
# Socket wrapper to enable socket.TCP_NODELAY - this greatly speeds up transactions in Linux
# WARNING: this will modify the standard library socket module, use with care!
# TODO: implement this as a transport faciliy
#       (to pass options directly to httplib2 or pycurl)
#       be aware of metaclasses and socks.py (SocksiPy) used by httplib2

if False:
    import socket
    realsocket = socket.socket
    def socketwrap(family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0):
        sockobj = realsocket(family, type, proto)
        if type == socket.SOCK_STREAM:
            sockobj.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        return sockobj
    socket.socket = socketwrap

#
# We store metadata about what available transport mechanisms we have available.
#
_http_connectors = {}  # libname: classimpl mapping
_http_facilities = {}  # functionalitylabel: [sequence of libname] mapping


class TransportBase:
    @classmethod
    def supports_feature(cls, feature_name):
        return cls._wrapper_name in _http_facilities[feature_name]

#
# httplib2 support.
#
try:
    import httplib2
    if sys.version > '3' and httplib2.__version__ <= "0.7.7":
        import http.client
        # httplib2 workaround: check_hostname needs a SSL context with either 
        #                      CERT_OPTIONAL or CERT_REQUIRED
        # see https://code.google.com/p/httplib2/issues/detail?id=173
        orig__init__ = http.client.HTTPSConnection.__init__ 
        def fixer(self, host, port, key_file, cert_file, timeout, context,
                        check_hostname, *args, **kwargs):
            chk = kwargs.get('disable_ssl_certificate_validation', True) ^ True
            orig__init__(self, host, port=port, key_file=key_file,
                cert_file=cert_file, timeout=timeout, context=context,
                check_hostname=chk)
        http.client.HTTPSConnection.__init__ = fixer
except ImportError:
    TIMEOUT = None  # timeout not supported by urllib2
    pass
else:
    class Httplib2Transport(httplib2.Http, TransportBase):
        _wrapper_version = "httplib2 %s" % httplib2.__version__
        _wrapper_name = 'httplib2'

        def __init__(self, timeout, proxy=None, cacert=None, sessions=False):
            ##httplib2.debuglevel=4
            kwargs = {}
            if proxy:
                import socks
                kwargs['proxy_info'] = httplib2.ProxyInfo(proxy_type=socks.PROXY_TYPE_HTTP, **proxy)
                log.info("using proxy %s" % proxy)

            # set optional parameters according supported httplib2 version
            if httplib2.__version__ >= '0.3.0':
                kwargs['timeout'] = timeout
            if httplib2.__version__ >= '0.7.0':
                kwargs['disable_ssl_certificate_validation'] = cacert is None
                kwargs['ca_certs'] = cacert
            httplib2.Http.__init__(self, **kwargs)

    _http_connectors['httplib2'] = Httplib2Transport
    _http_facilities.setdefault('proxy', []).append('httplib2')
    _http_facilities.setdefault('cacert', []).append('httplib2')

    import inspect
    if 'timeout' in inspect.getargspec(httplib2.Http.__init__)[0]:
        _http_facilities.setdefault('timeout', []).append('httplib2')


#
# urllib2 support.
#
class urllib2Transport(TransportBase):
    _wrapper_version = "urllib2 %s" % urllib2.__version__
    _wrapper_name = 'urllib2'

    def __init__(self, timeout=None, proxy=None, cacert=None, sessions=False):
        if (timeout is not None) and not self.supports_feature('timeout'):
            raise RuntimeError('timeout is not supported with urllib2 transport')
        if proxy:
            raise RuntimeError('proxy is not supported with urllib2 transport')
        if cacert:
            raise RuntimeError('cacert is not support with urllib2 transport')

        self.request_opener = urllib2.urlopen
        if sessions:
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(CookieJar()))
            self.request_opener = opener.open

        self._timeout = timeout

    def request(self, url, method="GET", body=None, headers={}):
        req = urllib2.Request(url, body, headers)
        try:
            f = self.request_opener(req, timeout=self._timeout)
            return f.info(), f.read()
        except urllib2.HTTPError as f:
            if f.code != 500:
                raise
            return f.info(), f.read()

_http_connectors['urllib2'] = urllib2Transport
_http_facilities.setdefault('sessions', []).append('urllib2')

import sys
if sys.version_info >= (2, 6):
    _http_facilities.setdefault('timeout', []).append('urllib2')
del sys

#
# pycurl support.
# experimental: pycurl seems faster + better proxy support (NTLM) + ssl features
#
try:
    import pycurl
except ImportError:
    pass
else:
    try:
        from cStringIO import StringIO
    except ImportError:
        try:
            from StringIO import StringIO
        except ImportError:
            from io import StringIO

    class pycurlTransport(TransportBase):
        _wrapper_version = pycurl.version
        _wrapper_name = 'pycurl'

        def __init__(self, timeout, proxy=None, cacert=None, sessions=False):
            self.timeout = timeout
            self.proxy = proxy or {}
            self.cacert = cacert

        def request(self, url, method, body, headers):
            c = pycurl.Curl()
            c.setopt(pycurl.URL, url)
            if 'proxy_host' in self.proxy:
                c.setopt(pycurl.PROXY, self.proxy['proxy_host'])
            if 'proxy_port' in self.proxy:
                c.setopt(pycurl.PROXYPORT, self.proxy['proxy_port'])
            if 'proxy_user' in self.proxy:
                c.setopt(pycurl.PROXYUSERPWD, "%(proxy_user)s:%(proxy_pass)s" % self.proxy)
            self.buf = StringIO()
            c.setopt(pycurl.WRITEFUNCTION, self.buf.write)
            #c.setopt(pycurl.READFUNCTION, self.read)
            #self.body = StringIO(body)
            #c.setopt(pycurl.HEADERFUNCTION, self.header)
            if self.cacert:
                c.setopt(c.CAINFO, self.cacert)
            c.setopt(pycurl.SSL_VERIFYPEER, self.cacert and 1 or 0)
            c.setopt(pycurl.SSL_VERIFYHOST, self.cacert and 2 or 0)
            c.setopt(pycurl.CONNECTTIMEOUT, self.timeout / 6)
            c.setopt(pycurl.TIMEOUT, self.timeout)
            if method == 'POST':
                c.setopt(pycurl.POST, 1)
                c.setopt(pycurl.POSTFIELDS, body)
            if headers:
                hdrs = ['%s: %s' % (k, v) for k, v in headers.items()]
                log.debug(hdrs)
                c.setopt(pycurl.HTTPHEADER, hdrs)
            c.perform()
            c.close()
            return {}, self.buf.getvalue()

    _http_connectors['pycurl'] = pycurlTransport
    _http_facilities.setdefault('proxy', []).append('pycurl')
    _http_facilities.setdefault('cacert', []).append('pycurl')
    _http_facilities.setdefault('timeout', []).append('pycurl')


class DummyTransport:
    """Testing class to load a xml response"""

    def __init__(self, xml_response):
        self.xml_response = xml_response

    def request(self, location, method, body, headers):
        log.debug("%s %s", method, location)
        log.debug(headers)
        log.debug(body)
        return {}, self.xml_response


def get_http_wrapper(library=None, features=[]):
    # If we are asked for a specific library, return it.
    if library is not None:
        try:
            return _http_connectors[library]
        except KeyError:
            raise RuntimeError('%s transport is not available' % (library,))

    # If we haven't been asked for a specific feature either, then just return our favourite
    # implementation.
    if not features:
        return _http_connectors.get('httplib2', _http_connectors['urllib2'])

    # If we are asked for a connector which supports the given features, then we will
    # try that.
    current_candidates = _http_connectors.keys()
    new_candidates = []
    for feature in features:
        for candidate in current_candidates:
            if candidate in _http_facilities.get(feature, []):
                new_candidates.append(candidate)
        current_candidates = new_candidates
        new_candidates = []

    # Return the first candidate in the list.
    try:
        candidate_name = current_candidates[0]
    except IndexError:
        raise RuntimeError("no transport available which supports these features: %s" % (features,))
    else:
        return _http_connectors[candidate_name]


def set_http_wrapper(library=None, features=[]):
    """Set a suitable HTTP connection wrapper."""
    global Http
    Http = get_http_wrapper(library, features)
    return Http


def get_Http():
    """Return current transport class"""
    global Http
    return Http


# define the default HTTP connection class (it can be changed at runtime!):
set_http_wrapper()

########NEW FILE########
__FILENAME__ = afip_test
#!/usr/bin/python
# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

"""Argentina AFIP (IRS) Electronic Invoice & Currency Exchange Control"""

from decimal import Decimal
import os
import unittest
from pysimplesoap.client import SimpleXMLElement, SoapClient, SoapFault, parse_proxy, set_http_wrapper

from .dummy_utils import DummyHTTP, TEST_DIR


WSDLs = [
    "https://wsaahomo.afip.gov.ar/ws/services/LoginCms?wsdl",
    "https://wsaa.afip.gov.ar/ws/services/LoginCms?wsdl",
    "https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL",
    "https://servicios1.afip.gov.ar/wsfev1/service.asmx?WSDL",
    "https://fwshomo.afip.gov.ar/wsmtxca/services/MTXCAService?wsdl",
    "https://serviciosjava.afip.gob.ar/wsmtxca/services/MTXCAService?wsdl",
    "https://wswhomo.afip.gov.ar/wsfexv1/service.asmx?WSDL",
    "https://servicios1.afip.gov.ar/wsfexv1/service.asmx?WSDL",
]

wrapper = None
cache = "./cache"
proxy_dict = None
cacert = None


class TestIssues(unittest.TestCase):

    def test_wsaa_exception(self):
        """Test WSAA for SoapFault"""
        WSDL = "https://wsaa.afip.gov.ar/ws/services/LoginCms?wsdl"
        client = SoapClient(wsdl=WSDL, ns="web")
        try:
            resultado = client.loginCms('31867063')
        except SoapFault as e:
            self.assertEqual(e.faultcode, 'ns1:cms.bad')

        try:
            resultado = client.loginCms(in0='31867063')
        except SoapFault as e:
            self.assertEqual(e.faultcode, 'ns1:cms.bad')

    def test_wsfev1_dummy(self):
        """Test Argentina AFIP Electronic Invoice WSFEv1 dummy method"""
        client = SoapClient(
            wsdl="https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL",
            cache=None
        )
        result = client.FEDummy()['FEDummyResult']
        self.assertEqual(result['AppServer'], "OK")
        self.assertEqual(result['DbServer'], "OK")
        self.assertEqual(result['AuthServer'], "OK")

    def test_wsfexv1_dummy(self):
        """Test Argentina AFIP Electronic Invoice WSFEXv1 dummy method"""
        client = SoapClient(
            wsdl="https://wswhomo.afip.gov.ar/wsfexv1/service.asmx?WSDL",
            cache=None
        )
        result = client.FEXDummy()['FEXDummyResult']
        self.assertEqual(result['AppServer'], "OK")
        self.assertEqual(result['DbServer'], "OK")
        self.assertEqual(result['AuthServer'], "OK")

    def test_wsbfe_dummy(self):
        """Test Argentina AFIP Electronic Invoice WSBFE dummy method"""
        client = SoapClient(
            wsdl="https://wswhomo.afip.gov.ar/wsbfe/service.asmx?WSDL",
            cache=None
        )
        result = client.BFEDummy()['BFEDummyResult']
        self.assertEqual(result['AppServer'], "OK")
        self.assertEqual(result['DbServer'], "OK")
        self.assertEqual(result['AuthServer'], "OK")

    def test_wsmtxca_dummy(self):
        """Test Argentina AFIP Electronic Invoice WSMTXCA dummy method"""
        client = SoapClient(
            wsdl="https://fwshomo.afip.gov.ar/wsmtxca/services/MTXCAService?wsdl",
            cache=None, ns='ser'
        )
        result = client.dummy()
        self.assertEqual(result['appserver'], "OK")
        self.assertEqual(result['dbserver'], "OK")
        self.assertEqual(result['authserver'], "OK")

    def test_wscoc_dummy(self):
        """Test Argentina AFIP Foreign Exchange Control WSCOC dummy method"""
        client = SoapClient(
            wsdl="https://fwshomo.afip.gov.ar/wscoc/COCService?wsdl",
            cache=None, ns='ser'
        )
        result = client.dummy()['dummyReturn']
        self.assertEqual(result['appserver'], "OK")
        self.assertEqual(result['dbserver'], "OK")
        self.assertEqual(result['authserver'], "OK")

    def test_wsfexv1_getcmp(self):
        """Test Argentina AFIP Electronic Invoice WSFEXv1 GetCMP method"""
        # create the proxy and parse the WSDL
        client = SoapClient(
            wsdl="https://wswhomo.afip.gov.ar/wsfexv1/service.asmx?WSDL",
            cache=None
        )
        # load saved xml
        xml = open(os.path.join(TEST_DIR, "wsfexv1_getcmp.xml")).read()
        client.http = DummyHTTP(xml)
        # call RPC
        ret = client.FEXGetCMP(
            Auth={'Token': "", 'Sign': "", 'Cuit': "0"},
            Cmp={
                'Cbte_tipo': "19",
                'Punto_vta': "3",
                'Cbte_nro': "38",
            })
        # analyze result
        result = ret['FEXGetCMPResult']
        self.assertEqual(result['FEXErr']['ErrCode'], 0)
        self.assertEqual(result['FEXErr']['ErrMsg'], 'OK')
        self.assertEqual(result['FEXEvents']['EventCode'], 0)
        resultget = result['FEXResultGet']
        self.assertEqual(resultget['Obs'], None)
        self.assertEqual(resultget['Cae'], '61473001385110')
        self.assertEqual(resultget['Fch_venc_Cae'], '20111202')
        self.assertEqual(resultget['Fecha_cbte'], '20111122')
        self.assertEqual(resultget['Punto_vta'], 3)
        self.assertEqual(resultget['Resultado'], "A")
        self.assertEqual(resultget['Cbte_nro'], 38)
        self.assertEqual(resultget['Imp_total'], Decimal('130.21'))
        self.assertEqual(resultget['Cbte_tipo'], 19)

########NEW FILE########
__FILENAME__ = cfdi_mx_test
#!/usr/bin/python
# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

"""Mexico SAT (IRS) Electronic Invoice (Comprobantes Fiscales Digitales)"""

from decimal import Decimal
import os
import unittest
from pysimplesoap.client import SoapClient, SoapFault

import sys
if sys.version > '3':
    basestring = str
    long = int


class TestCFDI(unittest.TestCase):

    def test_obtener_token(self):
            
        # Concetarse al webservice (en producción, ver cache y otros parametros):
        WSDL = "http://pruebas.ecodex.com.mx:2044/ServicioSeguridad.svc?wsdl"
        client = SoapClient(wsdl=WSDL, ns="ns0", soap_ns="soapenv")

        # llamo al método remoto:
        retval = client.ObtenerToken(RFC="AAA010101AAA", TransaccionID=1234)
        # muestro los resultados:
        self.assertIsInstance(retval['Token'], basestring)
        self.assertIsInstance(retval['TransaccionID'], long)
 
    def test_cancela(self):
            
        # Concetarse al webservice (en producción, ver cache y otros parametros):
        WSDL = "https://wsdexpruebas.ecodex.com.mx:2045/ServicioCancelacion.svc?wsdl"
        client = SoapClient(wsdl=WSDL, ns="cfdi", soap_ns="soapenv")
  
        try:
            r  = client.CancelaMultiple(
                    ListaCancelar=[{"guid": "abcdabcd-abcd-abcd-acbd-abcdabcdabcd"}], 
                    RFC="AAA010101AAA", 
                    Token="62cb344df85acab90c3a68174ed5e452b3c50b2a", 
                    TransaccionID=1234)
        except SoapFault as sf:
            self.assertIn("El Token no es valido o ya expiro", str(sf.faultstring))
            
        ##for res in r['Resultado']:
        ##    rc = res['ResultadoCancelacion']
        ##    print rc['UUID'], rc['Estatus']
        ##    print res['TransaccionID']
            
    def test_timbrado(self):
        # this tests "infinite recursion" issues
        
        # Concetarse al webservice (en producción, ver cache y otros parametros):
        WSDL = "https://digitalinvoicecfdi.com.mx/WS_WSDI/DigitalInvoice.WebServices.WSDI.Timbrado.svc?wsdl"
        #WSDL = "federico.wsdl"
        client = SoapClient(wsdl=WSDL, ns="ns0", soap_ns="soapenv")

        # llamo al método remoto:
        try:
            retval = client.TimbrarTest(comprobanteBytesZipped="1234")
        except SoapFault as sf:
            self.assertIn("verifying security for the message", str(sf.faultstring))

        # muestro los resultados:
        ##print retval['TimbrarTestResult']


########NEW FILE########
__FILENAME__ = client_test
#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import sys
if sys.version > '3':
    long = int

if __name__ == "__main__":
    import sys

    if '--web2py' in sys.argv:
        # test local sample webservice exposed by web2py
        from client import SoapClient
        if not '--wsdl' in sys.argv:
            client = SoapClient(
                location="http://127.0.0.1:8000/webservices/sample/call/soap",
                action='http://127.0.0.1:8000/webservices/sample/call/soap',  # SOAPAction
                namespace="http://127.0.0.1:8000/webservices/sample/call/soap",
                soap_ns='soap', ns=False, exceptions=True)
        else:
            client = SoapClient(wsdl="http://127.0.0.1:8000/webservices/sample/call/soap?WSDL")
        response = client.Dummy()
        print('dummy', response)
        response = client.Echo(value='hola')
        print('echo', repr(response))
        response = client.AddIntegers(a=1, b=2)
        if not '--wsdl' in sys.argv:
            result = response.AddResult  # manully convert returned type
            print(int(result))
        else:
            result = response['AddResult']
            print(result, type(result), "auto-unmarshalled")

    if '--raw' in sys.argv:
        # raw (unmarshalled parameter) local sample webservice exposed by web2py
        from client import SoapClient
        client = SoapClient(
            location="http://127.0.0.1:8000/webservices/sample/call/soap",
            action='http://127.0.0.1:8000/webservices/sample/call/soap',  # SOAPAction
            namespace="http://127.0.0.1:8000/webservices/sample/call/soap",
            soap_ns='soap', ns=False)
        params = SimpleXMLElement("""<?xml version="1.0" encoding="UTF-8"?><AddIntegers><a>3</a><b>2</b></AddIntegers>""")  # manully convert returned type
        response = client.call('AddIntegers', params)
        result = response.AddResult
        print(int(result))  # manully convert returned type

    if '--ctg' in sys.argv:
        # test AFIP Agriculture webservice
        client = SoapClient(
            location="https://fwshomo.afip.gov.ar/wsctg/services/CTGService",
            action='http://impl.service.wsctg.afip.gov.ar/CTGService/',  # SOAPAction
            namespace="http://impl.service.wsctg.afip.gov.ar/CTGService/",
            ns=True)
        response = client.dummy()
        result = response.dummyResponse
        print(str(result.appserver))
        print(str(result.dbserver))
        print(str(result.authserver))

    if '--wsfe' in sys.argv:
        # Demo & Test (AFIP Electronic Invoice):
        ta_string = open("TA.xml").read()   # read access ticket (wsaa.py)
        ta = SimpleXMLElement(ta_string)
        token = str(ta.credentials.token)
        sign = str(ta.credentials.sign)
        cuit = long(20267565393)
        id = 1234
        cbte = 199
        client = SoapClient(
            location="https://wswhomo.afip.gov.ar/wsfe/service.asmx",
            action='http://ar.gov.afip.dif.facturaelectronica/',  # SOAPAction
            namespace="http://ar.gov.afip.dif.facturaelectronica/")
        results = client.FERecuperaQTYRequest(
            argAuth={"Token": token, "Sign": sign, "cuit": long(cuit)}
        )
        if int(results.FERecuperaQTYRequestResult.RError.percode) != 0:
            print("Percode: %s" % results.FERecuperaQTYRequestResult.RError.percode)
            print("MSGerror: %s" % results.FERecuperaQTYRequestResult.RError.perrmsg)
        else:
            print(int(results.FERecuperaQTYRequestResult.qty.value))

    if '--feriados' in sys.argv:
        # Demo & Test: Argentina Holidays (Ministerio del Interior):
        # this webservice seems disabled
        from datetime import datetime, timedelta
        client = SoapClient(
            location="http://webservices.mininterior.gov.ar/Feriados/Service.svc",
            action='http://tempuri.org/IMyService/',  # SOAPAction
            namespace="http://tempuri.org/FeriadoDS.xsd")
        dt1 = datetime.today() - timedelta(days=60)
        dt2 = datetime.today() + timedelta(days=60)
        feriadosXML = client.FeriadosEntreFechasas_xml(dt1=dt1.isoformat(), dt2=dt2.isoformat())
        print(feriadosXML)

    if '--wsdl-parse' in sys.argv:
        if '--proxy' in sys.argv:
            proxy = parse_proxy("localhost:8000")
        else:
            proxy = None
        if '--wrapper' in sys.argv:
            set_http_wrapper("pycurl")
        client = SoapClient(proxy=proxy)
        # Test PySimpleSOAP WSDL
        ##client.wsdl("file:C:/test.wsdl", debug=True)
        # Test Java Axis WSDL:
        client.wsdl_parse('https://wsaahomo.afip.gov.ar/ws/services/LoginCms?wsdl', debug=True)
        # Test .NET 2.0 WSDL:
        client.wsdl_parse('https://wswhomo.afip.gov.ar/wsfe/service.asmx?WSDL', debug=True)
        client.wsdl_parse('https://wswhomo.afip.gov.ar/wsfex/service.asmx?WSDL', debug=True)
        client.wsdl_parse('https://testdia.afip.gov.ar/Dia/Ws/wDigDepFiel/wDigDepFiel.asmx?WSDL', debug=True)
        client.services = client.wsdl_parse('https://wswhomo.afip.gov.ar/wsfexv1/service.asmx?WSDL', debug=True)
        print(client.help("FEXGetCMP"))
        # Test JBoss WSDL:
        client.wsdl_parse('https://fwshomo.afip.gov.ar/wsctg/services/CTGService?wsdl', debug=True)
        client.wsdl_parse('https://wsaahomo.afip.gov.ar/ws/services/LoginCms?wsdl', debug=True)

    if '--wsdl-client' in sys.argv:
        import time
        t0 = time.time()
        for i in range(100):
            print(i)
            client = SoapClient(wsdl='https://wswhomo.afip.gov.ar/wsfex/service.asmx?WSDL', cache="cache")
            #results = client.FEXDummy()
            #print(results['FEXDummyResult']['AppServer'])
            #print(results['FEXDummyResult']['DbServer'])
            #print(results['FEXDummyResult']['AuthServer'])
        t1 = time.time()
        print("Total time", t1 - t0)

    if '--wsdl-client' in sys.argv:
        ta_string = open("TA.xml").read()   # read access ticket (wsaa.py)
        ta = SimpleXMLElement(ta_string)
        token = str(ta.credentials.token)
        sign = str(ta.credentials.sign)
        response = client.FEXGetCMP(
            Auth={"Token": token, "Sign": sign, "Cuit": 20267565393},
            Cmp={"Tipo_cbte": 19, "Punto_vta": 1, "Cbte_nro": 1})
        result = response['FEXGetCMPResult']
        #if False: print(result)  # ?
        if 'FEXErr' in result:
            print("FEXError:", result['FEXErr']['ErrCode'], result['FEXErr']['ErrCode'])
        cbt = result['FEXResultGet']
        print(cbt['Cae'])
        FEX_event = result['FEXEvents']
        print(FEX_event['EventCode'], FEX_event['EventMsg'])

    if '--wsdl-ctg' in sys.argv:
        client = SoapClient(wsdl='https://fwshomo.afip.gov.ar/wsctg/services/CTGService?wsdl',
                            ns="ctg")
        results = client.dummy()
        print(results)
        print(results['DummyResponse']['appserver'])
        print(results['DummyResponse']['dbserver'])
        print(results['DummyResponse']['authserver'])
        ta_string = open("TA.xml").read()  # read access ticket (wsaa.py)
        ta = SimpleXMLElement(ta_string)
        token = str(ta.credentials.token)
        sign = str(ta.credentials.sign)
        print(client.help("obtenerProvincias"))
        response = client.obtenerProvincias(auth={"token": token, "sign": sign, "cuitRepresentado": 20267565393})
        print("response=", response)
        for ret in response:
            print(ret['return']['codigoProvincia'], ret['return']['descripcionProvincia'].encode("latin1"))
        prueba = dict(
            numeroCartaDePorte=512345678, codigoEspecie=23,
            cuitRemitenteComercial=20267565393, cuitDestino=20267565393, cuitDestinatario=20267565393,
            codigoLocalidadOrigen=3058, codigoLocalidadDestino=3059,
            codigoCosecha='0910', pesoNetoCarga=1000, cantHoras=1,
            patenteVehiculo='CZO985', cuitTransportista=20267565393,
            numeroCTG="43816783", transaccion='10000001681', observaciones='',
        )

        response = client.solicitarCTG(
            auth={"token": token, "sign": sign, "cuitRepresentado": 20267565393},
            solicitarCTGRequest=prueba)

        print(response['return']['numeroCTG'])

    if '--libtest' in sys.argv:
        import time
        results = {}
        for lib in 'httplib2', 'urllib2', 'pycurl':
            print("testing library", lib)
            set_http_wrapper(lib)
            print(Http._wrapper_version)
            for proxy in None, parse_proxy("localhost:8000"):
                print("proxy", proxy)
                try:
                    client = SoapClient(wsdl='https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL',
                                        cache="cache", proxy=proxy)
                    t0 = time.time()
                    print("starting...",)
                    for i in range(20):
                        print(i,)
                        client.FEDummy()
                    t1 = time.time()
                    result = t1 - t0
                except Exception as e:
                    result = "Failed: %s" % e
                print("Total time", result)
                results.setdefault(lib, {})[proxy and 'proxy' or 'direct'] = result
        print("\nResults:")
        for k, v in list(results.items()):
            for k2, v2 in list(v.items()):
                print(k, k2, v2)

########NEW FILE########
__FILENAME__ = dummy_utils
import os

TEST_DIR = os.path.dirname(os.path.abspath(__file__))


from pysimplesoap.transport import DummyTransport as DummyHTTP

########NEW FILE########
__FILENAME__ = issues_test
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import unittest
import httplib2
import socket
from xml.parsers.expat import ExpatError
from pysimplesoap.client import SoapClient, SimpleXMLElement, SoapFault
from .dummy_utils import DummyHTTP, TEST_DIR

import sys
if sys.version > '3':
    basestring = str
    unicode = str


class TestIssues(unittest.TestCase):

    def test_issue19(self):
        """Test xsd namespace found under schema elementes"""
        client = SoapClient(
            wsdl='http://uat.destin8.co.uk:80/ChiefEDI/ChiefEDI?wsdl'
        )

    def test_issue34(self):
        """Test soap_server SoapClient constructor parameter"""
        client = SoapClient(
            wsdl="http://eklima.met.no/metdata/MetDataService?WSDL",
            soap_server="oracle", cache=None
        )
        ##print(client.help("getStationsProperties"))
        ##print(client.help("getValidLanguages"))

        # fix bad wsdl: server returns "getValidLanguagesResponse"
        # instead of "getValidLanguages12Response"
        met_data = client.services['MetDataService']['ports']['MetDataServicePort']
        languages = met_data['operations']['getValidLanguages']
        output = languages['output']['getValidLanguages13Response']
        languages['output'] = {'getValidLanguagesResponse': output}

        lang = client.getValidLanguages()

        self.assertEqual(lang, {'return': ['no', 'en', 'ny']})

    def test_issue35_raw(self):

        client = SoapClient(
            location="http://wennekers.epcc.ed.ac.uk:8080"
                     "/axis/services/MetadataCatalogue",
            action=""
        )
        response = client.call(
            "doEnsembleURIQuery",
            ("queryFormat", "Xpath"),
            ("queryString", "/markovChain"),
            ("startIndex", 0),
            ("maxResults", -1)
        )
        self.assertEqual(str(response.statusCode), "MDC_INVALID_REQUEST")
        #print(str(response.queryTime))
        self.assertEqual(int(response.totalResults), 0)
        self.assertEqual(int(response.startIndex), 0)
        self.assertEqual(int(response.numberOfResults), 0)

        for result in response.results:
            str(result)

    def test_issue35_wsdl(self):
        """Test positional parameters, multiRefs and axis messages"""

        client = SoapClient(
            wsdl="http://wennekers.epcc.ed.ac.uk:8080/axis/services/MetadataCatalogue?WSDL",
            soap_server="axis"
        )
        response = client.doEnsembleURIQuery(
            queryFormat="Xpath", queryString="/markovChain",
            startIndex=0, maxResults=-1
        )

        ret = response['doEnsembleURIQueryReturn']
        self.assertEqual(ret['statusCode'], "MDC_INVALID_REQUEST")
        self.assertEqual(ret['totalResults'], 0)
        self.assertEqual(ret['startIndex'], 0)
        self.assertEqual(ret['numberOfResults'], 0)

    def test_issue8_raw(self):
        """Test europa.eu tax service (namespace - raw call)"""

        client = SoapClient(
            location="http://ec.europa.eu/taxation_customs/vies/services/checkVatService",
            action='',  # SOAPAction
            namespace="urn:ec.europa.eu:taxud:vies:services:checkVat:types"
        )
        vat = 'IE6388047V'
        code = vat[:2]
        number = vat[2:]
        res = client.checkVat(countryCode=code, vatNumber=number)
        self.assertEqual(unicode(res('countryCode')), "IE")
        self.assertEqual(unicode(res('vatNumber')), "6388047V")
        self.assertEqual(unicode(res('name')), "GOOGLE IRELAND LIMITED")
        self.assertEqual(unicode(res('address')), "1ST & 2ND FLOOR ,GORDON HOUSE ,"
                                              "BARROW STREET ,DUBLIN 4")

    def test_issue8_wsdl(self):
        """Test europa.eu tax service (namespace - wsdl call)"""
        URL='http://ec.europa.eu/taxation_customs/vies/checkVatService.wsdl'
        client = SoapClient(wsdl=URL)
        # check the correct target namespace:
        self.assertEqual(client.namespace,
                         "urn:ec.europa.eu:taxud:vies:services:checkVat:types")
        # call the webservice to check everything else:
        vat = 'BE0897290877'
        code = vat[:2]
        number = vat[2:]
        res = client.checkVat(countryCode=code, vatNumber=number)
        # check returned values:
        self.assertEqual(res['name'], "SPRL B2CK")
        self.assertEqual(res['address'], "RUE DE ROTTERDAM 4 B21\n"
                                         "4000  LIEGE")

    ## NOTE: Missing file "ups.wsdl"
    ##def test_ups(self):
    ##    "Test UPS tracking service"
    ##    WSDL = "file:ups.wsdl"
    ##    client = SoapClient(wsdl=WSDL, ns="web")
    ##    print(client.help("ProcessTrack"))

    def test_issue43(self):

        client = SoapClient(
            wsdl="https://api.clarizen.com/v1.0/Clarizen.svc"
        )

        client.help("Login")
        client.help("Logout")
        client.help("Query")
        client.help("Metadata")
        client.help("Execute")

    def test_issue44(self):
        """Test namespace"""    
        client = SoapClient(wsdl="https://api.clarizen.com/v1.0/Clarizen.svc")        
        try:
            response = client.Login(userName="foo",password="bar")
        except Exception as e:
            self.assertEquals(e.faultcode, 's:InvalidUserNameOrPassword')

    def test_issue46(self):
        """Example for sending an arbitrary header using SimpleXMLElement"""

        # fake connection (just to test xml_request):
        client = SoapClient(
            location="https://localhost:666/",
            namespace='http://localhost/api'
        )

        # Using WSDL, the equivalent is:
        # client['MyTestHeader'] = {'username': 'test', 'password': 'test'}

        headers = SimpleXMLElement("<Headers/>")
        my_test_header = headers.add_child("MyTestHeader")
        my_test_header['xmlns'] = "service"
        my_test_header.marshall('username', 'test')
        my_test_header.marshall('password', 'password')

        try:
            client.methodname(headers=headers)
        except:
            open("issue46.xml", "wb").write(client.xml_request)
            self.assert_('<soap:Header><MyTestHeader xmlns="service">'
                            '<username>test</username>'
                            '<password>password</password>'
                         '</MyTestHeader></soap:Header>' in client.xml_request.decode(),
                         "header not in request!")

    def test_issue47_wsdl(self):
        """Separate Header message WSDL (carizen)"""

        client = SoapClient(wsdl="https://api.clarizen.com/v1.0/Clarizen.svc")

        session = client['Session'] = {'ID': '1234'}

        try:
            client.Logout()
        except:
            open("issue47_wsdl.xml", "wb").write(client.xml_request)
            self.assert_('<soap:Header><Session>'
                            '<ID>1234</ID>'
                         '</Session></soap:Header>' in client.xml_request.decode(),
                         "Session header not in request!")

    def test_issue47_raw(self):
        """Same example (clarizen), with raw headers (no wsdl)!"""
        client = SoapClient(
            location="https://api.clarizen.com/v1.0/Clarizen.svc",
            namespace='http://clarizen.com/api'
        )

        headers = SimpleXMLElement("<Headers/>", namespace="http://clarizen.com/api",
                                   prefix="ns1")
        session = headers.add_child("Session")
        session['xmlns'] = "http://clarizen.com/api"
        session.marshall('ID', '1234')

        client.location = "https://api.clarizen.com/v1.0/Clarizen.svc"
        client.action = "http://clarizen.com/api/IClarizen/Logout"
        try:
            client.call("Logout", headers=headers)
        except:
            open("issue47_raw.xml", "wb").write(client.xml_request)
            self.assert_('<soap:Header><ns1:Session xmlns="http://clarizen.com/api">'
                            '<ID>1234</ID>'
                         '</ns1:Session></soap:Header>' in client.xml_request.decode(),
                         "Session header not in request!")

    def test_issue49(self):
        """Test netsuite wsdl"""    
        client = SoapClient(wsdl="https://webservices.netsuite.com/wsdl/v2011_2_0/netsuite.wsdl")        
        try:
            response = client.login(passport=dict(email="joe@example.com", password="secret", account='hello', role={'name': 'joe'}))
        except Exception as e:
            # It returns "This document you requested has moved temporarily."
            pass

    def test_issue57(self):
        """Test SalesForce wsdl"""
        # open the attached sfdc_enterprise_v20.wsdl to the issue in googlecode 
        client = SoapClient(wsdl="https://pysimplesoap.googlecode.com/issues/attachment?aid=570000001&name=sfdc_enterprise_v20.wsdl&token=bD6VTXMx8p4GJQHGhlQI1ISorSA%3A1399085346613")        
        try:
            response = client.login(username="john", password="doe")
        except Exception as e:
            # It returns "This document you requested has moved temporarily."
            self.assertEqual(e.faultcode, 'INVALID_LOGIN')
                     
    def test_issue60(self):
        """Verify unmarshalling of custom xsi:type="SOAPENC:Array" """
        wsdl_url = 'http://peopleask.ooz.ie/soap.wsdl' 
        client = SoapClient(wsdl=wsdl_url, soap_server="unknown", trace=False)
        questions = client.GetQuestionsAbout(query="money")
        self.assertIsInstance(questions, list)
        for question in questions:
            self.assertIsNotNone(question)
            self.assertNotEqual(question, "")

                            
    def test_issue66(self):
        """Verify marshaled requests can be sent with no children"""
        # fake connection (just to test xml_request):
        client = SoapClient(
            location="https://localhost:666/",
            namespace='http://localhost/api'
        )

        request = SimpleXMLElement("<ChildlessRequest/>")
        try:
            client.call('ChildlessRequest', request)
        except:
            open("issue66.xml", "wb").write(client.xml_request)
            self.assert_('<ChildlessRequest' in client.xml_request.decode(),
                         "<ChildlessRequest not in request!")
            self.assert_('</ChildlessRequest>' in client.xml_request.decode(),
                         "</ChildlessRequest> not in request!")

    def test_issue69(self):
        """Boolean value not converted correctly during marshall"""
        span = SimpleXMLElement('<span><name>foo</name></span>')
        span.marshall('value', True)
        d = {'span': {'name': str, 'value': bool}}
        e = {'span': {'name': 'foo', 'value': True}}
        self.assertEqual(span.unmarshall(d), e)

    def test_issue78(self):
        """Example for sending an arbitrary header using SimpleXMLElement and WSDL"""

        # fake connection (just to test xml_request):
        client = SoapClient(
            wsdl='http://dczorgwelzijn-test.qmark.nl/qmwise4/qmwise.asmx?wsdl'
        )

        # Using WSDL, the easier form is but this doesn't allow for namespaces to be used.
        # If the server requires these (buggy server?) the dictionary method won't work
        # and marshall will not marshall 'ns:username' style keys
        # client['MyTestHeader'] = {'username': 'test', 'password': 'test'}

        namespace = 'http://questionmark.com/QMWISe/'
        ns = 'qmw'
        header = SimpleXMLElement('<Headers/>', namespace=namespace, prefix=ns)
        security = header.add_child("Security")
        security['xmlns:qmw'] = namespace
        security.marshall('ClientID', 'NAME', ns=ns)
        security.marshall('Checksum', 'PASSWORD', ns=ns)
        client['Security'] = security

        try:
            client.GetParticipantList()
        except:
            #open("issue78.xml", "wb").write(client.xml_request)
            #print(client.xml_request)
            header = '<soap:Header>' \
                         '<qmw:Security xmlns:qmw="http://questionmark.com/QMWISe/">' \
                             '<qmw:ClientID>NAME</qmw:ClientID>' \
                             '<qmw:Checksum>PASSWORD</qmw:Checksum>' \
                         '</qmw:Security>' \
                     '</soap:Header>'
            xml = SimpleXMLElement(client.xml_request)
            self.assertEquals(str(xml.ClientID), "NAME")
            self.assertEquals(str(xml.Checksum), "PASSWORD")

    def test_issue80(self):
        """Test services.conzoom.eu/addit/ wsdl"""    
        client = SoapClient(wsdl="http://services.conzoom.eu/addit/AddItService.svc?wsdl")        
        client.help("GetValues")

    def atest_issue80(self):
        """Test Issue in sending a webservice request with soap12"""    
        client = SoapClient(wsdl="http://testserver:7007/testapp/services/testService?wsdl",
                            soap_ns='soap12', trace=False, soap_server='oracle')        
        try:
            result = client.hasRole(userId='test123', role='testview')
        except httplib2.ServerNotFoundError:
	        pass

    def test_issue89(self):
        """Setting attributes for request tag."""
        # fake connection (just to test xml_request):
        client = SoapClient(
            location="https://localhost:666/",
            namespace='http://localhost/api'
        )
        request = SimpleXMLElement(
            """<?xml version="1.0" encoding="UTF-8"?><test a="b"><a>3</a></test>"""
        ) # manually make request msg
        try:
            client.call('test', request)
        except:
            open("issue89.xml", "wb").write(client.xml_request)
            self.assert_('<test a="b" xmlns="http://localhost/api">' in client.xml_request.decode(),
                         "attribute not in request!")

    def test_issue93(self):
        """Response with <xs:schema> and <xs:any>"""
        # attached sample response to the ticket:
        xml = """
<?xml version="1.0" encoding="utf-8"?><soap:Envelope xmlns:soap="http://schemas.
xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance
" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:wsa="http://schemas.xmlsoap
.org/ws/2004/08/addressing"><soap:Header><wsa:Action>http://smbsaas/websitepanel
/enterpriseserver/AddPackageResponse</wsa:Action><wsa:MessageID>urn:uuid:af841fc
e-4607-4e4b-910e-252d1f1857fb</wsa:MessageID><wsa:RelatesTo>urn:uuid:fea15079-42
57-424b-8da7-8c9a29ec52ce</wsa:RelatesTo><wsa:To>http://schemas.xmlsoap.org/ws/2
004/08/addressing/role/anonymous</wsa:To></soap:Header><soap:Body><AddPackageRes
ponse xmlns="http://smbsaas/websitepanel/enterpriseserver"><AddPackageResult><Re
sult>798</Result><ExceedingQuotas><xs:schema id="NewDataSet" xmlns="" xmlns:xs="
http://www.w3.org/2001/XMLSchema" xmlns:msdata="urn:schemas-microsoft-com:xml-ms
data"><xs:element name="NewDataSet" msdata:IsDataSet="true" msdata:UseCurrentLoc
ale="true"><xs:complexType><xs:choice minOccurs="0" maxOccurs="unbounded"><xs:el
ement name="Table"><xs:complexType><xs:sequence><xs:element name="QuotaID" type=
"xs:int" minOccurs="0" /><xs:element name="QuotaName" type="xs:string" minOccurs
="0" /><xs:element name="QuotaValue" type="xs:int" minOccurs="0" /></xs:sequence
></xs:complexType></xs:element></xs:choice></xs:complexType></xs:element></xs:sc
hema><diffgr:diffgram xmlns:msdata="urn:schemas-microsoft-com:xml-msdata" xmlns:
diffgr="urn:schemas-microsoft-com:xml-diffgram-v1" /></ExceedingQuotas></AddPack
ageResult></AddPackageResponse></soap:Body></soap:Envelope>
"""
        xml = xml.replace("\n","").replace("\r","")
        # parse the wsdl attached to the ticket
        client = SoapClient(wsdl="https://pysimplesoap.googlecode.com/issues/attachment?aid=930004001&name=wsdl.txt&token=MIcIgTXvGmzpfFgLM-noYLehzwU%3A1399083528469", trace=False)        
        # put the sample response (no call to the real webservice is made...)
        client.http = DummyHTTP(xml)
        result = client.AddPackage(657, 33, 'Services', 'Comment', 1, datetime.datetime.now())
        # check unmarshalled results:
        self.assertEquals(result['AddPackageResult']['Result'], 798)
        # the schema is also returned as a SimpleXMLElement object (unmarshalled), get the xml:
        self.assertEquals(repr(result['AddPackageResult']['ExceedingQuotas']['schema']['element']),
            '<xs:element msdata:IsDataSet="true" msdata:UseCurrentLocale="true" name="NewDataSet"><xs:complexType><xs:choice maxOccurs="unbounded" minOccurs="0"><xs:element name="Table"><xs:complexType><xs:sequence><xs:element minOccurs="0" name="QuotaID" type="xs:int"/><xs:element minOccurs="0" name="QuotaName" type="xs:string"/><xs:element minOccurs="0" name="QuotaValue" type="xs:int"/></xs:sequence></xs:complexType></xs:element></xs:choice></xs:complexType></xs:element>')
        # the any is also returned as a SimpleXMLElement object (unmarshalled)
        self.assertEquals(str(result['AddPackageResult']['ExceedingQuotas']['diffgram']), '')

    def test_issue94(self):
        """Test wather forecast web service."""
        client = SoapClient(wsdl='http://www.restfulwebservices.net/wcf/WeatherForecastService.svc?wsdl')
        ret = client.GetCitiesByCountry('korea')
        for d in ret['GetCitiesByCountryResult']:
            #print d['string']
            self.assertEquals(d.keys()[0], 'string')
        self.assertEquals(len(ret['GetCitiesByCountryResult']), 53)
        self.assertEquals(len(ret['GetCitiesByCountryResult'][0]), 1)
        self.assertEquals(ret['GetCitiesByCountryResult'][0]['string'], 'KWANGJU')

    def test_issue101(self):
        """automatic relative import support"""

        client = SoapClient(wsdl="https://raw.github.com/vadimcomanescu/vmwarephp/master/library/Vmwarephp/Wsdl/vimService.wsdl")
        try:
            client.Login(parameters={'userName': 'username', 'password': 'password'})
        except IOError:
            pass
        try:
            client.Logout()
        except IOError:
            pass

    def test_issue104(self):
        """SoapClient did not build all arguments for Marketo."""
        method = 'getLead'
        args = {'leadKey': {'keyType': 'IDNUM', 'keyValue': '1'}}

        # fake connection (just to test xml_request):
        client = SoapClient(wsdl='http://app.marketo.com/soap/mktows/2_1?WSDL')
        input = client.get_operation(method)['input']

        params = ('paramsGetLead', [('leadKey', {'keyType': 'IDNUM', 'keyValue': '1'})])

        self.assertEqual(params, client.wsdl_call_get_params(method, input, args))
        self.assertEqual(params, client.wsdl_call_get_params(method, input, leadKey=args['leadKey']))

    def test_issue109(self):
        """Test multirefs and string arrays"""

        WSDL = 'http://usqcd.jlab.org/mdc-service/services/ILDGMDCService?wsdl'

        client = SoapClient(wsdl=WSDL,soap_server='axis')
        response = client.doEnsembleURIQuery("Xpath", "/markovChain", 0, -1)

        ret = response['doEnsembleURIQueryReturn']
        self.assertIsInstance(ret['numberOfResults'], int)
        self.assertIsInstance(ret['results'], list)
        self.assertIsInstance(ret['results'][0], basestring)
        self.assertIsInstance(ret['queryTime'], basestring)
        self.assertEqual(ret['statusCode'], "MDC_SUCCESS")

    def test_issue109bis(self):
        """Test string arrays not defined in the wsdl (but sent in the response)"""

        WSDL = 'http://globe-meta.ifh.de:8080/axis/services/ILDG_MDC?wsdl'

        client = SoapClient(wsdl=WSDL,soap_server='axis')
        response = client.doEnsembleURIQuery("Xpath", "/markovChain", 0, -1)

        ret = response['doEnsembleURIQueryReturn']
        self.assertIsInstance(ret['numberOfResults'], int)
        self.assertIsInstance(ret['results'], list)
        self.assertIsInstance(ret['results'][0], basestring)

    def test_issue113(self):
        """Test target namespace in wsdl import"""
        WSDL = "https://test.paymentgate.ru/testpayment/webservices/merchant-ws?wsdl"
        client = SoapClient(wsdl=WSDL)
        try:
            client.getOrderStatusExtended(order={'merchantOrderNumber':'1'})
        except SoapFault as sf:
            # ignore exception caused by missing credentials sent in this test:
            if sf.faultstring != "An error was discovered processing the <wsse:Security> header":
                raise

        # verify the correct namespace:
        xml = SimpleXMLElement(client.xml_request)
        ns_uri = xml.getOrderStatusExtended['xmlns']
        self.assertEqual(ns_uri,
                         "http://engine.paymentgate.ru/webservices/merchant")

    def test_issue105(self):
        """Test target namespace in wsdl (conflicting import)"""
        WSDL = "https://api.dc2.computing.cloud.it/WsEndUser/v2.4/WsEndUser.svc?wsdl"
        client = SoapClient(wsdl=WSDL)
        try:
            client.SetEnqueueServerStop(serverId=37)
        except SoapFault as sf:
            # ignore exception caused by missing credentials sent in this test:
            if sf.faultstring != "An error occurred when verifying security for the message.":
                raise

        # verify the correct namespace:
        xml = SimpleXMLElement(client.xml_request)
        ns_uri = xml.SetEnqueueServerStop['xmlns']
        self.assertEqual(ns_uri,
                         "https://api.computing.cloud.it/WsEndUser")

    def test_issue114(self):
        """Test no schema in wsdl (Lotus-Domino)"""
        WSDL = "https://pysimplesoap.googlecode.com/issues/attachment?aid=1140000000&name=WebRequest.xml&token=QVf8DlJ1qmKRH8LAbU4eSe2Ban0%3A1399084258723"
        # WSDL= "file:WebRequest.xml"
        try:
            client = SoapClient(wsdl=WSDL, soap_server="axis")
            #print client.help("CREATEREQUEST")
            ret = client.CREATEREQUEST(LOGIN="hello", REQUESTTYPE=1, REQUESTCONTENT="test")
        except ExpatError:
            # the service seems to be expecting basic auth
            pass
        except SoapFault as sf:
            # todo: check as service is returning DOM failure
            # verify the correct namespace:
            xml = SimpleXMLElement(client.xml_request)
            ns_uri = xml.CREATEREQUEST['xmlns']
            self.assertEqual(ns_uri, "http://tps.ru")

    def test_issue116(self):
        """Test string conversion and encoding of a SoapFault exception"""
        exception = SoapFault('000', 'fault stríng')
        exception_string = str(exception)
        self.assertTrue(isinstance(exception_string, str))
        if sys.version < '3':
            self.assertEqual(exception_string, '000: fault strng')
        else:
            self.assertEqual(exception_string, '000: fault stríng')

    def test_issue122(self):
        """Test multiple separate messages in input header"""
        APIURL = "https://ecommercetest.collector.se/v3.0/InvoiceServiceV31.svc?singleWsdl"
        client = SoapClient(wsdl=APIURL)

        # set headers (first two were not correctly handled
        client['Username'] = 'user'
        client['Password'] = 'pass'
        client['ClientIpAddress'] = '127.0.0.1'

        variables = {
            "CountryCode": "SE",
            "RegNo": "1234567890",
        }

        expected_xml = ("<soap:Header>"
                        "<Username>user</Username>"
                        "<Password>pass</Password>"
                        "<ClientIpAddress>127.0.0.1</ClientIpAddress>"
                        "</soap:Header>")
        try:
            response = client.GetAddress(**variables)
        except SoapFault:
            self.assertIn(expected_xml, client.xml_request)

    def test_issue123(self):
        """Basic test for WSDL lacking service tag """
        wsdl = "http://www.onvif.org/onvif/ver10/device/wsdl/devicemgmt.wsdl"
        client = SoapClient(wsdl=wsdl)
        # this could cause infinite recursion (TODO: investigate)
        #client.help("CreateUsers")
        #client.help("GetServices")
        # this is not a real webservice (just specification) catch HTTP error
        try: 
            client.GetServices(IncludeCapability=True)
        except Exception as e:
            self.assertEqual(str(e), "RelativeURIError: Only absolute URIs are allowed. uri = ")

    def test_issue127(self):
        """Test relative schema locations in imports"""
        client = SoapClient(wsdl = 'https://eisoukr.musala.com:9443/IrmInboundMediationWeb/sca/MTPLPolicyWSExport/WEB-INF/wsdl/wsdl/IrmInboundMediation_MTPLPolicyWSExport.wsdl')
        try:
            resp = client.voidMTPLPolicy()
        except Exception as e:
            self.assertIn('InvalidSecurity', e.faultcode)

    def test_issue128(self):
        ""
        client = SoapClient(
                wsdl = "https://apiapac.lumesse-talenthub.com/HRIS/SOAP/Candidate?WSDL",
                location = "https://apiapac.lumesse-talenthub.com/HRIS/SOAP/Candidate?api_key=azhmc6m8sq2gf2jqwywa37g4",
                ns = True
                )
        # basic test as no test case was provided
        try:
            resp = client.getContracts()
        except:
            self.assertEqual(client.xml_response, '<h1>Gateway Timeout</h1>')

    def test_issue129(self):
        """Test RPC style (axis) messages (including parameter order)"""
        wsdl_url = 'file:tests/data/teca_server_wsdl.xml'
        client = SoapClient(wsdl=wsdl_url, soap_server='axis')
        client.help("contaVolumi")
        response = client.contaVolumi(user_id=1234, valoreIndice=["IDENTIFIER", ""])
        self.assertEqual(response, {'contaVolumiReturn': 0})

    def test_issue130(self):
        """Test complex Array (axis) """
        wsdl_url = 'file:tests/data/teca_server_wsdl.xml'
        client = SoapClient(wsdl=wsdl_url, soap_server='axis', trace=False)
        #print client.help("find")
        #response = client.find(25, ['SUBJECT', 'Ethos'], 10, 0)
        port = client.services[u'WsTecaServerService']['ports']['tecaServer']
        op = port['operations']['find']
        out = op['output']['findResponse']['findReturn']
        # findReturn should be a list of Contenitore
        self.assertIsInstance(out, list)
        element = out[0]['Contenitore']
        for key in [u'EMail', u'bloccato', u'classe', u'codice', u'creatoDa', 
                    u'creatoIl', u'dbName', u'dbPort', u'dbUrl', u'username']:
            self.assertIn(key, element)
        # valoriDigitali should be a list of anyType (None)
        self.assertIsInstance(element[u'valoriDigitali'], list)
        self.assertIsNone(element[u'valoriDigitali'][0])

    def test_issue139(self):
        """Test MKS wsdl (extension)"""
        # open the attached Integrity_10_2Service to the issue in googlecode 
        client = SoapClient(wsdl="https://pysimplesoap.googlecode.com/issues/attachment?aid=1390000000&name=Integrity_10_2.wsdl&token=3VG47As2K-EupP9GgotYckgb0Bc%3A1399064656814")
        #print client.help("getItemsByCustomQuery")
        try:
            response = client.getItemsByCustomQuery(arg0={'Username': 'user', 'Password' : 'pass', 'InputField' : 'ID', 'QueryDefinition' : 'query'})
        except httplib2.ServerNotFoundError:
	        pass

    def test_issue141(self):
        """Test voxone VoxAPI wsdl (ref element)"""
        import datetime
        import hmac
        import hashlib

        client = SoapClient(wsdl="http://sandbox.voxbone.com/VoxAPI/services/VoxAPI?wsdl", cache=None)
        client.help("GetPOPList")

        key = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S:%f000000")
        password="fwefewfewfew"
        usertoken={'Username': "oihfweohf", 'Key': key, 'Hash': hmac.new(key, password, digestmod=hashlib.sha1).hexdigest()}
        try:
            response = client.GetPOPList(UserToken=usertoken)
            result = response['GetPOPListResponse']
        except SoapFault as sf:
            # ignore exception caused by missing credentials sent in this test:
            if sf.faultstring != "Either your username or password is invalid":
                raise

    def test_issue143(self):
        """Test webservice.vso.dunes.ch wsdl (array sub-element)"""
        wsdl_url = 'file:tests/data/vco.wsdl' 
        try:
            vcoWS = SoapClient(wsdl=wsdl_url, soap_server="axis", trace=False)
            workflowInputs = [{'name': 'vmName', 'type': 'string', 'value': 'VMNAME'}]
            workflowToken = vcoWS.executeWorkflow(workflowId='my_uuid', username="my_user", password="my_password", workflowInputs=workflowInputs)
        except httplib2.ServerNotFoundError:
            #import pdb;pdb.set_trace()
            print vcoWS.xml_response
            pass


if __name__ == '__main__':
    #unittest.main()
    suite = unittest.TestSuite()
    suite.addTest(TestIssues('test_issue34'))
    suite.addTest(TestIssues('test_issue93'))
    suite.addTest(TestIssues('test_issue57'))
    suite.addTest(TestIssues('test_issue60'))
    suite.addTest(TestIssues('test_issue80'))
    suite.addTest(TestIssues('test_issue101'))
    suite.addTest(TestIssues('test_issue114'))
    #suite.addTest(TestIssues('test_issue123'))
    suite.addTest(TestIssues('test_issue127'))
    #suite.addTest(TestIssues('test_issue130'))
    suite.addTest(TestIssues('test_issue141'))
    suite.addTest(TestIssues('test_issue143'))
    unittest.TextTestRunner().run(suite)

########NEW FILE########
__FILENAME__ = licencias_test
#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import os
import unittest
from pysimplesoap.client import SoapClient, SoapFault

from .dummy_utils import DummyHTTP, TEST_DIR


class TestIssues(unittest.TestCase):
    internal = 1

    def setUp(self):
        self.xml = open(os.path.join(TEST_DIR, "licencias.xml")).read()

    def test_buscar_personas_raw(self):

        url = "http://www.testgobi.dpi.sfnet/licencias/web/soap.php"
        client = SoapClient(location=url, ns="web",
                            namespace="http://wwwdesagobi.dpi.sfnet:8080/licencias/web/",
                            action=url)
        # load dummy response (for testing)
        client.http = DummyHTTP(self.xml)
        client['AuthHeaderElement'] = {'username': 'mariano', 'password': 'clave'}
        response = client.PersonaSearch(persona=(('numero_documento', '99999999'),
                                                 ('apellido_paterno', ''),
                                                 ('apellido_materno', ''),
                                                 ('nombres', ''),
                                                 ))

        # the raw response is a SimpleXmlElement object:

        self.assertEqual(str(response.result.item[0]("xsd:string")[0]), "resultado")
        self.assertEqual(str(response.result.item[0]("xsd:string")[1]), "true")
        self.assertEqual(str(response.result.item[1]("xsd:string")[0]), "codigo")
        self.assertEqual(str(response.result.item[1]("xsd:string")[1]), "WS01-01")
        self.assertEqual(str(response.result.item[2]("xsd:string")[0]), "mensaje")
        self.assertEqual(str(response.result.item[2]("xsd:string")[1]), "Se encontraron 1 personas.")
        self.assertEqual(str(response.result.item[2]("xsd:string")[0]), "mensaje")
        self.assertEqual(str(response.result.item[2]("xsd:string")[1]), "Se encontraron 1 personas.")

        self.assertEqual(str(response.result.item[3]("xsd:anyType")[0]), "datos")
        self.assertEqual(str(response.result.item[3]("xsd:anyType")[1]("ns2:Map").item[0].key), "lic_ps_ext_id")
        self.assertEqual(str(response.result.item[3]("xsd:anyType")[1]("ns2:Map").item[0].value), "123456")
        self.assertEqual(str(response.result.item[3]("xsd:anyType")[1]("ns2:Map").item[10].key), "fecha_nacimiento")
        self.assertEqual(str(response.result.item[3]("xsd:anyType")[1]("ns2:Map").item[10].value), "1985-10-02 00:00:00")

    def test_buscar_personas_wsdl(self):
        WSDL = "file://" + os.path.join(TEST_DIR, "licencias.wsdl")
        client = SoapClient(wsdl=WSDL, ns="web")
        print(client.help("PersonaSearch"))
        client['AuthHeaderElement'] = {'username': 'mariano', 'password': 'clave'}
        client.http = DummyHTTP(self.xml)
        resultado = client.PersonaSearch(numero_documento='31867063')
        print(resultado)

        # each resultado['result'][i]['item'] is xsd:anyType, so it is not unmarshalled
        # they are SimpleXmlElement (see test_buscar_personas_raw)
        self.assertEqual(str(resultado['result'][0]['item']('xsd:string')[0]), "resultado")
        self.assertEqual(str(resultado['result'][1]['item']('xsd:string')[1]), "WS01-01")
        self.assertEqual(str(resultado['result'][3]['item']('xsd:anyType')[1]("ns2:Map").item[10].value), "1985-10-02 00:00:00")

########NEW FILE########
__FILENAME__ = nfp_br_test
#!/usr/bin/python
# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

"""Brazil - Sao Paulo "Electronic Invoice"  (Nota Fiscal Paulista)"""

from __future__ import unicode_literals

from decimal import Decimal
import os
import unittest
from pysimplesoap.client import SoapClient, SoapFault, SimpleXMLElement

import sys
if sys.version > '3':
    basestring = str
    long = int

# Documentation: http://www.nfp.fazenda.sp.gov.br/MIWSCF.pdf
WSDL = 'https://www.nfp.fazenda.sp.gov.br/ws/arquivocf.asmx?WSDL'

HEADER_XML = """<Autenticacao Usuario="%s" Senha="%s" CNPJ="%s" 
                CategoriaUsuario="%d" xmlns="https://www.nfp.sp.gov.br/ws" />"""

# TODO: support attributes in headers / parameters

class TestNFP(unittest.TestCase):
 
    def test_enviar(self):
        "Prueba da envio de arquivos de cupons fiscais"
        
        # create the client webservice
        client = SoapClient(wsdl=WSDL, soap_ns="soap12env")
        # set user login credentials in the soap header: 
        client['Autenticacao'] = SimpleXMLElement(HEADER_XML % ("user","password", "fed_tax_num", 1))
        # call the webservice
        response = client.Enviar(NomeArquivo="file_name", ConteudoArquivo="content", EnvioNormal=True, Observacoes="")
        self.assertEqual(response['EnviarResult'], '206|CNPJ informado inv\xe1lido')            

    def test_consultar(self):
        "consulta ao resultado do processamento dos arquivos de cupons fiscai"
        # create the client webservice
        client = SoapClient(wsdl=WSDL, soap_ns="soap12env")
        # set user login credentials in the soap header: 
        client['Autenticacao'] = SimpleXMLElement(HEADER_XML % ("user","password", "fed_tax_num", 1))
        # call the webservice
        response = client.Consultar(Protocolo="")
        self.assertEqual(response['ConsultarResult'], '999|O protocolo informado n\xe3o \xe9 um n\xfamero v\xe1lido')

    def test_retificar(self):
        "Prueba da retifica de arquivos de cupons fiscais"
        
        # create the client webservice
        client = SoapClient(wsdl=WSDL, soap_ns="soap12env")
        # set user login credentials in the soap header: 
        client['Autenticacao'] = SimpleXMLElement(HEADER_XML % ("user","password", "fed_tax_num", 1))
        # call the webservice
        response = client.Retificar(NomeArquivo="file_name", ConteudoArquivo="content", EnvioNormal=True, Observacoes="")
        self.assertEqual(response['RetificarResult'], '206|CNPJ informado inv\xe1lido')
        

########NEW FILE########
__FILENAME__ = server_multins_test
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import logging
import unittest
from pysimplesoap.server import SoapDispatcher

# log = logging.getLogger('pysimplesoap.server')
# log.setLevel(logging.DEBUG)
# log = logging.getLogger('pysimplesoap.simplexml')
# log.setLevel(logging.DEBUG)

REQ = """
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ext="http://external.mt.moboperator" xmlns:mod="http://model.common.mt.moboperator">
   <soapenv:Header/>
   <soapenv:Body>
      <ext:activateSubscriptions>
         <ext:serviceMsisdn>791</ext:serviceMsisdn>
         <ext:serviceName>abc</ext:serviceName>
         <ext:activations>
            <!--1 or more repetitions:-->
            <mod:items>
               <mod:msisdn>791000000</mod:msisdn>
               <!--1 or more repetitions:-->
               <mod:properties>
                  <mod:name>x</mod:name>
                  <mod:value>2</mod:value>
               </mod:properties>
               <mod:parameters> ::260013456789</mod:parameters>
            </mod:items>
         </ext:activations>
      </ext:activateSubscriptions>
   </soapenv:Body>
</soapenv:Envelope>"""

REQ1 = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Header/><soapenv:Body><p727:updateDeliveryStatus xmlns:p727="http://external.mt.moboperator"><p727:serviceMsisdn>51072</p727:serviceMsisdn><p727:serviceName>IPLA</p727:serviceName><p727:messageDeliveryStatuses><p924:items xmlns:p924="http://model.common.mt.moboperator"><p924:msisdn>48726401494</p924:msisdn><p924:status>380</p924:status><p924:deliveryId>33946812</p924:deliveryId></p924:items></p727:messageDeliveryStatuses></p727:updateDeliveryStatus></soapenv:Body></soapenv:Envelope>"""

SINGLE_NS_RESP = """<?xml version="1.0" encoding="UTF-8"?><soapenv:Envelope xmlns:ext="http://external.mt.moboperator" xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Body><ext:activateSubscriptionsResponse><activateSubscriptionsReturn><code>0</code><description>desc</description><items><msisdn>791000000</msisdn><properties><name>x</name><value>2</value></properties><status>0</status></items></activateSubscriptionsReturn></ext:activateSubscriptionsResponse></soapenv:Body></soapenv:Envelope>"""

MULTI_NS_RESP = """<?xml version="1.0" encoding="UTF-8"?><soapenv:Envelope xmlns:ext="http://external.mt.moboperator" xmlns:mod="http://model.common.mt.moboperator" xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Body><ext:activateSubscriptionsResponse><ext:activateSubscriptionsReturn><mod:code>0</mod:code><mod:description>desc</mod:description><mod:items><mod:msisdn>791000000</mod:msisdn><mod:properties><mod:name>x</mod:name><mod:value>2</mod:value></mod:properties><mod:status>0</mod:status></mod:items></ext:activateSubscriptionsReturn></ext:activateSubscriptionsResponse></soapenv:Body></soapenv:Envelope>"""
MULTI_NS_RESP1 = """<?xml version="1.0" encoding="UTF-8"?><soapenv:Envelope xmlns:p727="http://external.mt.moboperator" xmlns:p924="http://model.common.mt.moboperator" xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Body><p727:updateDeliveryStatusResponse><p727:updateDeliveryStatusReturn><p924:code>0</p924:code><p924:description>desc</p924:description></p727:updateDeliveryStatusReturn></p727:updateDeliveryStatusResponse></soapenv:Body></soapenv:Envelope>"""


class TestServerMultiNS(unittest.TestCase):

    def _single_ns_func(self, serviceMsisdn, serviceName, activations=[]):
        code = 0
        desc = 'desc'

        results = [{
            'items': [
                {'msisdn': '791000000'},
                {'properties': [{'name': 'x'}, {'value': '2'}]},
                {'status': '0'}
            ]}]

        ret = {
            'activateSubscriptionsReturn': [
                {'code': code},
                {'description': desc},
            ]}
        ret['activateSubscriptionsReturn'].extend(results)
        return ret

    _single_ns_func.returns = {'non-empty-dict': 1}
    _single_ns_func.args = {
        'serviceMsisdn': str,
        'serviceName': str,
        'activations': [
            {'items': {
                    'msisdn': str,
                    'status': int,
                    'parameters': str,
                    'properties': ({
                            'name': str,
                            'value': str
                        },
                    )
                }
            }
        ]
    }

    def _updateDeliveryStatus(self, serviceMsisdn, serviceName, messageDeliveryStatuses=[]):
        code = 0
        desc = 'desc'
        return {
            'external:updateDeliveryStatusReturn': [
                {'model:code': code},
                {'model:description': desc}
            ]
        }
    _updateDeliveryStatus.returns = {'non-empty-dict': 1}
    _updateDeliveryStatus.args = {
        'serviceMsisdn': str,
        'serviceName': str,
        'messageDeliveryStatuses': [
            {'items': {
                    'msisdn': str,
                    'status': int,
                    'deliveryId': str,
                    'properties': ({
                            'name': str,
                            'value': int
                        },
                    )
                }
            }
        ]
    }

    def _multi_ns_func(self, serviceMsisdn, serviceName, activations=[]):
        code = 0
        desc = 'desc'

        results = [{
            'model:items': [
                {'model:msisdn': '791000000'},
                {'model:properties': [{'model:name': 'x'}, {'model:value': '2'}]},
                {'model:status': '0'}
            ]}]

        ret = {
            'external:activateSubscriptionsReturn': [
                {'model:code': code},
                {'model:description': desc},
            ]}
        ret['external:activateSubscriptionsReturn'].extend(results)
        return ret

    _multi_ns_func.returns = {'non-empty-dict': 1}
    _multi_ns_func.args = {
        'serviceMsisdn': str,
        'serviceName': str,
        'activations': [
            {'items': {
                    'msisdn': str,
                    'status': int,
                    'parameters': str,
                    'properties': ({
                            'name': str,
                            'value': str
                        },
                    )
                }
            }
        ]
    }

    def test_single_ns(self):
        dispatcher = SoapDispatcher(
            name="MTClientWS",
            location="http://localhost:8008/ws/MTClientWS",
            action='http://localhost:8008/ws/MTClientWS',  # SOAPAction
            namespace="http://external.mt.moboperator", prefix="external",
            documentation='moboperator MTClientWS',
            ns=True,
            pretty=False,
            debug=True)

        dispatcher.register_function('activateSubscriptions',
            self._single_ns_func,
            returns=self._single_ns_func.returns,
            args=self._single_ns_func.args)

        # I don't fully know if that is a valid response for a given request,
        # but I tested it, to be sure that a multi namespace function
        # doesn't brake anything.
        self.assertEqual(dispatcher.dispatch(REQ), SINGLE_NS_RESP)

    def test_multi_ns(self):
        dispatcher = SoapDispatcher(
            name="MTClientWS",
            location="http://localhost:8008/ws/MTClientWS",
            action='http://localhost:8008/ws/MTClientWS',  # SOAPAction
            namespace="http://external.mt.moboperator", prefix="external",
            documentation='moboperator MTClientWS',
            namespaces={
                'external': 'http://external.mt.moboperator',
                'model': 'http://model.common.mt.moboperator'
            },
            ns=True,
            pretty=False,
            debug=True)

        dispatcher.register_function('activateSubscriptions',
            self._multi_ns_func,
            returns=self._multi_ns_func.returns,
            args=self._multi_ns_func.args)
        dispatcher.register_function('updateDeliveryStatus',
            self._updateDeliveryStatus,
            returns=self._updateDeliveryStatus.returns,
            args=self._updateDeliveryStatus.args)

        self.assertEqual(dispatcher.dispatch(REQ), MULTI_NS_RESP)
        self.assertEqual(dispatcher.dispatch(REQ1), MULTI_NS_RESP1)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = simplexmlelement_test
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import sys
import datetime
import unittest
from pysimplesoap.simplexml import SimpleXMLElement

PY2 = sys.version < '3'

class TestSimpleXMLElement(unittest.TestCase):
    def eq(self, value, expectation, msg=None):
        if msg is not None:
            msg += ' %s' % value
            self.assertEqual(value, expectation, msg)
        else:
            self.assertEqual(value, expectation, value)

    def test_attributes_access(self):
        span = SimpleXMLElement('<span><a href="python.org.ar">pyar</a><prueba><i>1</i><float>1.5</float></prueba></span>')
        text = "pyar"
        self.eq(str(span.a), text, 'Access by __getattr__:')
        self.eq(str(span.a), text, 'Access by __getattr__:')
        self.eq(str(span('a')), text, 'Access by __call__:')
        self.eq(str(span.a(0)), text, 'Access by __call__ on attribute:')
        self.eq(span.a['href'], "python.org.ar", 'Access by __getitem__:')
        self.eq(int(span.prueba.i), 1, 'Casting to int:')
        self.eq(float(span.prueba.float), 1.5, 'Casting to float:')

    def test_to_xml(self):
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?><span><a href="python.org.ar">'
            'pyar</a><prueba><i>1</i><float>1.5</float></prueba></span>')
        self.eq(SimpleXMLElement(xml).as_xml(), xml if PY2 else xml.encode('utf-8'))

        xml = (
            '<?xml version="1.0" encoding="UTF-8"?><span><a href="google.com">'
            'google</a><a>yahoo</a><a>hotmail</a></span>')
        self.eq(SimpleXMLElement(xml).as_xml(), xml if PY2 else xml.encode('utf-8'))

    def test_unmarshall(self):
        span = SimpleXMLElement('<span><name>foo</name><value>3</value></span>')
        d = {'span': {'name': str, 'value': int}}
        e = {'span': {'name': 'foo', 'value': 3}}
        self.eq(span.unmarshall(d), e)

        span = SimpleXMLElement('<span><name>foo</name><name>bar</name></span>')
        d = {'span': [{'name': str}]}
        e = {'span': [{'name': 'foo'}, {'name': 'bar'}]}
        self.eq(span.unmarshall(d), e)

        span = SimpleXMLElement('<activations><items><number>01234</number><status>1</status></items><items><number>04321</number><status>0</status></items></activations>')
        d = {'activations': [
                {'items': {
                    'number': str,
                    'status': int
                }}
            ]}

        e = {'activations': [{'items': {'number': '01234', 'status': 1}}, {'items': {'number': '04321', 'status': 0}}]}
        self.eq(span.unmarshall(d), e)

    def test_adv_unmarshall(self):
        xml = """
        <activations>
            <items>
                <number>01234</number>
                <status>1</status>
                <properties>
                    <name>foo</name>
                    <value>3</value>
                </properties>
                <properties>
                    <name>bar</name>
                    <value>4</value>
                </properties>
            </items>
            <items>
                <number>04321</number>
                <status>0</status>
            </items>
        </activations>
        """
        span = SimpleXMLElement(xml)
        d = {'activations': [
                {'items': {
                    'number': str,
                    'status': int,
                    'properties': ({
                        'name': str,
                        'value': int
                    }, )
                }}
            ]}

        e = {'activations': [
                {'items': {'number': '01234', 'status': 1, 'properties': ({'name': 'foo', 'value': 3}, {'name': 'bar', 'value': 4})}},
                {'items': {'number': '04321', 'status': 0}}
            ]}
        self.eq(span.unmarshall(d), e)

    def test_tuple_unmarshall(self):
        xml = """
        <foo>
            <boo>
                <bar>abc</bar>
                <baz>1</baz>
            </boo>
            <boo>
                <bar>qwe</bar>
                <baz>2</baz>
            </boo>
        </foo>
        """
        span = SimpleXMLElement(xml)
        d = {'foo': {
                'boo': ({'bar': str, 'baz': int}, )
        }}

        e = {'foo': {
                'boo': (
                {'bar': 'abc', 'baz': 1},
                {'bar': 'qwe', 'baz': 2},
            )}}
        self.eq(span.unmarshall(d), e)

    def test_basic(self):
        span = SimpleXMLElement(
            '<span><a href="python.org.ar">pyar</a>'
            '<prueba><i>1</i><float>1.5</float></prueba></span>')
        span1 = SimpleXMLElement(
            '<span><a href="google.com">google</a>'
            '<a>yahoo</a><a>hotmail</a></span>')
        self.eq([str(a) for a in span1.a()], ['google', 'yahoo', 'hotmail'])

        span1.add_child('a', 'altavista')
        span1.b = "ex msn"
        d = {'href': 'http://www.bing.com/', 'alt': 'Bing'}
        span1.b[:] = d
        self.eq(sorted([(k, v) for k, v in span1.b[:]]), sorted(d.items()))

        xml = (
            '<?xml version="1.0" encoding="UTF-8"?><span>'
            '<a href="google.com">google</a><a>yahoo</a>'
            '<a>hotmail</a><a>altavista</a>'
            '<b alt="Bing" href="http://www.bing.com/">ex msn</b></span>')
        self.eq(span1.as_xml(), xml if PY2 else xml.encode('utf-8'))
        self.assertTrue('b' in span1)

        span.import_node(span1)
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?><span>'
            '<a href="python.org.ar">pyar</a><prueba><i>1</i>'
            '<float>1.5</float></prueba><span><a href="google.com">google</a>'
            '<a>yahoo</a><a>hotmail</a><a>altavista</a>'
            '<b alt="Bing" href="http://www.bing.com/">ex msn</b>'
            '</span></span>')
        self.eq(span.as_xml(), xml if PY2 else xml.encode('utf-8'))

        types = {'when': datetime.datetime}
        when = datetime.datetime.now()
        dt = SimpleXMLElement('<when>%s</when>' % when.isoformat())
        self.eq(dt.unmarshall(types)['when'], when)

    def test_repr(self):
        xml = '<foo><bar z="1">123</bar></foo>'
        el = SimpleXMLElement(xml)
        el_repr = repr(el)
        self.assertTrue(isinstance(el_repr, str))
        self.eq(el_repr, xml)

    def test_str(self):
        xml = '<foo>BÀr</foo>'
        # minidom must always parse encoded string in python 2
        el = SimpleXMLElement(xml.encode('utf-8') if PY2 else xml)
        el_str = str(el)
        self.assertTrue(isinstance(el_str, str))

        if PY2: # str is bytestring in py2
            self.eq(el_str, 'BÀr'.encode('utf-8'))
        else:
            self.eq(el_str, 'BÀr')

    @unittest.skipUnless(PY2, 'unicode() conversion not present in py3')
    def test_unicode(self):
        xml = '<foo>BÀr</foo>'
        el = SimpleXMLElement(xml.encode('utf-8'))
        el_unicode = unicode(el)
        self.assertTrue(isinstance(el_unicode, unicode))
        self.eq(el_unicode, 'BÀr')

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = soapdispatcher_test
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import unittest
from pysimplesoap.server import SoapDispatcher
from pysimplesoap.simplexml import Date, Decimal


def adder(p, c, dt=None):
    "Add several values"
    dt = dt + datetime.timedelta(365)
    return {'ab': p['a'] + p['b'], 'dd': c[0]['d'] + c[1]['d'], 'dt': dt}


def dummy(in0):
    "Just return input"
    return in0


def echo(request):
    "Copy request->response (generic, any type)"
    return request.value


class TestSoapDispatcher(unittest.TestCase):
    def eq(self, value, expectation, msg=None):
        if msg is not None:
            msg += ' %s' % value
            self.assertEqual(value, expectation, msg)
        else:
            self.assertEqual(value, expectation, "%s\n---\n%s" % (value, expectation))

    def setUp(self):
        self.dispatcher = SoapDispatcher(
            name="PySimpleSoapSample",
            location="http://localhost:8008/",
            action='http://localhost:8008/',  # SOAPAction
            namespace="http://example.com/pysimplesoapsamle/", prefix="ns0",
            documentation='Example soap service using PySimpleSoap',
            debug=True,
            ns=True)

        self.dispatcher.register_function('Adder', adder,
            returns={'AddResult': {'ab': int, 'dd': str}},
            args={'p': {'a': int, 'b': int}, 'dt': Date, 'c': [{'d': Decimal}]})

        self.dispatcher.register_function('Dummy', dummy,
            returns={'out0': str},
            args={'in0': str})

        self.dispatcher.register_function('Echo', echo)

    def test_classic_dialect(self):
        # adder local test (clasic soap dialect)
        resp = """<?xml version="1.0" encoding="UTF-8"?><soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soap:Body><AdderResponse xmlns="http://example.com/pysimplesoapsamle/"><dd>5000000.3</dd><ab>3</ab><dt>2011-07-24</dt></AdderResponse></soap:Body></soap:Envelope>"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
    <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
       <soap:Body>
         <Adder xmlns="http://example.com/sample.wsdl">
           <p><a>1</a><b>2</b></p><c><d>5000000.1</d><d>.2</d></c><dt>2010-07-24</dt>
        </Adder>
       </soap:Body>
    </soap:Envelope>"""
        self.eq(self.dispatcher.dispatch(xml), resp)

    def test_modern_dialect(self):
        # adder local test (modern soap dialect, SoapUI)
        resp = """<?xml version="1.0" encoding="UTF-8"?><soapenv:Envelope xmlns:pys="http://example.com/pysimplesoapsamle/" xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Body><pys:AdderResponse><dd>15.021</dd><ab>12</ab><dt>1970-07-20</dt></pys:AdderResponse></soapenv:Body></soapenv:Envelope>"""
        xml = """
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:pys="http://example.com/pysimplesoapsamle/">
   <soapenv:Header/>
   <soapenv:Body>
      <pys:Adder>
         <pys:p><pys:a>9</pys:a><pys:b>3</pys:b></pys:p>
         <pys:dt>1969-07-20<!--1969-07-20T21:28:00--></pys:dt>
         <pys:c><pys:d>10.001</pys:d><pys:d>5.02</pys:d></pys:c>
      </pys:Adder>
   </soapenv:Body>
</soapenv:Envelope>
    """
        self.eq(self.dispatcher.dispatch(xml), resp)

    def test_echo(self):
        # echo local test (generic soap service)
        resp = """<?xml version="1.0" encoding="UTF-8"?><soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soap:Body><EchoResponse xmlns="http://example.com/pysimplesoapsamle/"><value xsi:type="xsd:string">Hello world</value></EchoResponse></soap:Body></soap:Envelope>"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
    <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
                   xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                   xmlns:xsd="http://www.w3.org/2001/XMLSchema">
       <soap:Body>
         <Echo xmlns="http://example.com/sample.wsdl">
           <value xsi:type="xsd:string">Hello world</value>
        </Echo>
       </soap:Body>
    </soap:Envelope>"""
        self.eq(self.dispatcher.dispatch(xml), resp)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = sri_ec_test
#!/usr/bin/python
# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

"""Ecuador S.R.I. Electronic Invoice (Emisión de Documentos Electrónicos)"""

from __future__ import unicode_literals

from decimal import Decimal
import os
import unittest
from pysimplesoap.client import SoapClient, SoapFault

import sys
if sys.version > '3':
    basestring = str
    long = int

# Documentation: http://www.sri.gob.ec/web/10138/145


class TestSRI(unittest.TestCase):
 
    def test_validar(self):
        "Prueba de envío de un comprovante electrónico"
        WSDL = 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantes?wsdl'
        # https://cel.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantes?wsdl
        client = SoapClient(wsdl=WSDL, ns="ec")
        ret = client.validarComprobante(xml="cid:1218403525359")
        self.assertEquals(ret, {'RespuestaRecepcionComprobante': {'comprobantes': [{'comprobante': {'mensajes': [{'mensaje': {'identificador': '35', 'mensaje': 'ARCHIVO NO CUMPLE ESTRUCTURA XML', 'informacionAdicional': 'Content is not allowed in prolog.', 'tipo': 'ERROR'}}], 'claveAcceso': 'N/A'}}], 'estado': 'DEVUELTA'}})
            

    def test_autorizar(self):
            
        WSDL = 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantes?wsdl'
        # https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantes?wsdl
        client = SoapClient(wsdl=WSDL, ns="ec")
        ret = client.autorizacionComprobante(claveAccesoComprobante="1702201205176001321000110010030001000011234567816")
        self.assertEquals(ret, {'RespuestaAutorizacionComprobante': {'autorizaciones': [], 'claveAccesoConsultada': '1702201205176001321000110010030001000011234567816', 'numeroComprobantes': '0'}})


########NEW FILE########
__FILENAME__ = suite
# -*- coding: utf-8 -*-

import unittest


def add(suite, module):
    suite.addTest(unittest.TestLoader().loadTestsFromModule(module))


def test():
    # TODO: automagicaly import modules test/*_test.py
    from . import soapdispatcher_test
    from . import simplexmlelement_test
    from . import issues_test
    from . import afip_test
    from . import server_multins_test
    # licencias_tests is for internal use, wsdl is not published
    # from . import licencias_test
    # from . import trazamed_test
    from . import cfdi_mx_test
    from . import sri_ec_test
    from . import nfp_br_test

    suite = unittest.TestSuite()

    add(suite, soapdispatcher_test)
    add(suite, simplexmlelement_test)
    add(suite, issues_test)
    add(suite, afip_test)
    add(suite, server_multins_test)
    ##add(suite, licencias_test)
    ##add(suite, trazamed_test)
    add(suite, cfdi_mx_test)
    add(suite, sri_ec_test)
    add(suite, nfp_br_test)

    unittest.TextTestRunner(verbosity=2).run(suite)

if __name__ == '__main__':
    test()

########NEW FILE########
__FILENAME__ = trazamed_test
#!/usr/bin/python
# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
from __future__ import unicode_literals

"""Argentina National Medical Drug Traceability Program (ANMAT - PAMI - INSSJP)"""

__author__ = "Mariano Reingart <reingart@gmail.com>"
__copyright__ = "Copyright (C) 2011 Mariano Reingart"
__license__ = "GPL 3.0"

import datetime
import os
import unittest
import sys
import time
if sys.version > '3':
    basestring = unicode = str

from pysimplesoap.client import SoapClient, SoapFault, parse_proxy, \
                                set_http_wrapper


WSDL = "https://186.153.145.2:9050/trazamed.WebService?wsdl"
        #https://186.153.145.2:9050/trazamed.WebService?wsdl
LOCATION = "https://186.153.145.2:9050/trazamed.WebService"
#WSDL = "https://trazabilidad.pami.org.ar:9050/trazamed.WebService?wsdl"


class TestTrazamed(unittest.TestCase):
    internal = 1

    def setUp(self):

        self.client = SoapClient(
            wsdl=WSDL,
            cache=None,
            ns="tzmed",
            soap_ns="soapenv",
            soap_server="jetty")                # needed to handle list

        # fix location (localhost:9050 is erroneous in the WSDL)
        self.client.services['IWebServiceService']['ports']['IWebServicePort']['location'] = LOCATION

        # Set WSSE security credentials
        self.client['wsse:Security'] = {
            'wsse:UsernameToken': {
                'wsse:Username': 'testwservice',
                'wsse:Password': 'testwservicepsw',
                }
            }

    def test_send_medicamentos(self):
        #self.client.help("sendMedicamentos")

        # Create the complex type (medicament data transfer object):
        medicamentosDTO = dict(
            f_evento=datetime.datetime.now().strftime("%d/%m/%Y"),
            h_evento=datetime.datetime.now().strftime("%H:%M"),
            gln_origen="9999999999918", gln_destino="glnws",
            n_remito="1234", n_factura="1234",
            vencimiento=(datetime.datetime.now() +
                         datetime.timedelta(30)).strftime("%d/%m/%Y"),
            gtin="GTIN1", lote=datetime.datetime.now().strftime("%Y"),
            numero_serial=int(time.time()),
            id_obra_social=None, id_evento=134,
            cuit_origen="20267565393", cuit_destino="20267565393",
            apellido="Reingart", nombres="Mariano",
            tipo_documento="96", n_documento="26756539", sexo="M",
            direccion="Saraza", numero="1234", piso="", depto="",
            localidad="Hurlingham", provincia="Buenos Aires",
            n_postal="1688", fecha_nacimiento="01/01/2000",
            telefono="5555-5555",
            )

        # Call the webservice to inform a medicament:
        res = self.client.sendMedicamentos(
            arg0=medicamentosDTO,
            arg1='pruebasws',
            arg2='pruebasws',
        )

        # Analyze the response:
        ret = res['return']
        self.assertIsInstance(ret['codigoTransaccion'], basestring)
        self.assertEqual(ret['resultado'], True)

    def test_send_medicamentos_dh_serie(self):
        self.client.help("sendMedicamentosDHSerie")

        # Create the complex type (medicament data transfer object):
        medicamentosDTODHSerie = dict(
            f_evento=datetime.datetime.now().strftime("%d/%m/%Y"),
            h_evento=datetime.datetime.now().strftime("%H:%M"),
            gln_origen="9999999999918", gln_destino="glnws",
            n_remito="1234", n_factura="1234",
            vencimiento=(datetime.datetime.now() +
                         datetime.timedelta(30)).strftime("%d/%m/%Y"),
            gtin="GTIN1", lote=datetime.datetime.now().strftime("%Y"),
            desde_numero_serial=int(time.time()) + 1,
            hasta_numero_serial=int(time.time()) - 1,
            id_obra_social=None, id_evento=134,
            )

        # Call the webservice to inform a medicament:
        res = self.client.sendMedicamentosDHSerie(
            arg0=medicamentosDTODHSerie,
            arg1='pruebasws',
            arg2='pruebasws',
        )

        # Analyze the response:
        ret = res['return']
        
        # Check the results:
        self.assertIsInstance(ret['codigoTransaccion'], basestring)
        self.assertEqual(ret['errores'][0]['_c_error'], '3004')
        self.assertEqual(ret['errores'][0]['_d_error'], "El campo Hasta Nro Serial debe ser mayor o igual al campo Desde Nro Serial.")
        self.assertEqual(ret['resultado'], False)

    def test_get_transacciones_no_confirmadas(self):

        # Call the webservice to query all the un-confirmed transactions:
        res = self.client.getTransaccionesNoConfirmadas(
                arg0='pruebasws',
                arg1='pruebasws',
                arg10='01/01/2013',
                arg11='31/12/2013',
            )

        # Analyze the response:
        ret = res['return']

        # Check the results (a list should be returned):
        self.assertIsInstance(ret['list'], list)

        for transaccion_plain_ws in ret['list']:
            # each item of the list is a dict (transaccionPlainWS complex type):
            # {'_f_evento': u'20/06/2012', '_numero_serial': u'04', ...}
            # check the keys returned in the complex type:
            for key in ['_f_evento', '_f_transaccion', '_lote', 
                        '_numero_serial', '_razon_social_destino',
                        '_gln_destino', '_n_remito', '_vencimiento',
                        '_d_evento', '_id_transaccion_global',
                        '_razon_social_origen', '_n_factura', '_gln_origen',
                        '_id_transaccion', '_gtin', '_nombre']:
                self.assertIn(key, transaccion_plain_ws)


if __name__ == '__main__':
    unittest.main()


########NEW FILE########
