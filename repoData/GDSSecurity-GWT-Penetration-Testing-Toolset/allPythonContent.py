__FILENAME__ = gwtenum
#!/usr/bin/env python

'''

    GwtEnum v0.2
    Copyright (C) 2010 Ron Gutierrez

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

'''

import urllib2
import re
import pprint
import base64
import getpass
from optparse import OptionParser

desc = "A tool for enumerating GWT RPC methods"
methods = []
proxy_url = ""
basic_auth_encoded = ""
        
def get_global_val( varname, html_file ):
    for html_line in html_file:
        match = re.match( ".*," + re.escape(varname) +
            "\=\'([A-Za-z0-9_\.\!\@\#\$\%\^\&\*\(\)" 
            "\-\+\=\:\;\"\|\\\\/\?\>\,\<\~\`]+)\',", html_line )
        if not match is None:
            return match.group(1)


if __name__ == "__main__":
    parser = OptionParser( usage="usage: %prog [options]", 
        description=desc, 
        version='%prog 0.10' )
    
    parser.add_option('-p', '--proxy', 
        help="Proxy Host and Port (ie. -p \"http://proxy.internet.net:8080\")", 
        action="store" )
        
    parser.add_option('-b', '--basicauth', 
        help="User Basic Authentication ( Will be prompted for creds )", 
        action="store_true" )
        
    parser.add_option('-k', '--cookies', 
        help="Cookies to use when requesting the GWT Javascript Files (ie. -c \"JSESSIONID=AAAAAA\")", 
        action="store")
        
    parser.add_option('-u', '--url', 
        help="Required: GWT Application Entrypoint Javascript File (ie. *.nocache.js )", 
        action="store")
    
    (options, args) = parser.parse_args()
        
    if options.url is None:
        print( "\nMissing URL\n" )
        parser.print_help()
        exit()
            
    url = options.url
    gwt_docroot = '/'.join(url.split('/')[:-1])+'/'	
            
    req = urllib2.Request(url)
    
    handlers = [ urllib2.HTTPHandler() ]
    
    if url.startswith( "https://" ):
        try:
            import ssl
        except ImportError:
            print "SSL support not installed - exiting"
            exit()
            
        handlers.append( urllib2.HTTPSHandler() )
    
    if options.proxy:
        handlers.append( urllib2.ProxyHandler( {'http':'http://'+options.proxy}) )
        
    opener = urllib2.build_opener(*handlers)
    urllib2.install_opener( opener )
    
    if options.basicauth:
        username = raw_input( "Basic Auth Username: " )
        password = getpass.getpass( "Basic Auth Password: " )
        basic_auth_encoded = base64.encodestring( '%s:%s' % (username, password) ).strip()
        req.add_header( "Authorization", "Basic %s" % basic_auth_encoded )
    
    if options.cookies:
        req.add_header( "Cookie", options.cookies )
        
    response = urllib2.urlopen(req)
    the_page = response.read()
    
    html_files = re.findall( "([A-Z0-9]{30,35})", the_page )
    if html_files is None:
        print( "\nNo Cached HTML Files found\n" )
        exit()
        
    all_rpc_files = []
    how_many_html_files_to_read = 1
    
    for html_file in html_files:
        if how_many_html_files_to_read == 0:
           break
        how_many_html_files_to_read -= 1

        async_error_mess = ""
        invoke_method = ""
        cache_html = "%s%s.cache.html" % (gwt_docroot, html_file )
        print( "Analyzing %s" % cache_html )
        
        req = urllib2.Request( cache_html )
        
        if options.cookies:
            req.add_header( "Cookie", options.cookies )
            
        if options.basicauth:
            req.add_header( "Authorization", "Basic %s" % basic_auth_encoded )
                
        try:       
            response = urllib2.urlopen(req)     
        except urllib2.HTTPError:
            print( "404: Failed to Retrieve %s" % cache_html )
            continue
            
        the_page = response.readlines()
 
        for line in the_page:
        
            # Service and Method name Enumeration
            rpc_method_match = re.match( "^function \w+\(.*method\:([A-Za-z0-9_\$]+),.*$", line )
            
            if rpc_method_match:
                if rpc_method_match.group(1) == "a":
                    continue
                  
                rpc_js_function = rpc_method_match.group(0).split(';')
                service_and_method = ""
                
                method_name = get_global_val( rpc_method_match.group(1), the_page )
                if method_name is None:
                    continue
                    
                methods.append(  "%s( " % method_name.replace( '_Proxy.', '.' ) )
                
                # Parameter Enumeration
                for i in range(0, len(rpc_js_function)):
                    try_match = re.match( "^try{.*$", rpc_js_function[i] )
                    if try_match:
                        i += 1
                        func_match = re.match( "^([A-Za-z0-9_\$]+)\(.*", rpc_js_function[i] )
                        payload_function = ""
                        if func_match:
                            payload_function = func_match.group(1)
                        
                        i += 1
                        param_match = re.match( "^"+re.escape(payload_function)+
                            "\([A-Za-z0-9_\$]+\.[A-Za-z0-9_\$]+,([A-Za-z0-9_\$]+)\)", 
                            rpc_js_function[i] )
                            
                        num_of_params = 0
                        if param_match:
                            num_of_params = int(get_global_val( param_match.group(1), the_page ))
                        
                        for j in range( 0, num_of_params ):
                            i += 1
                            
                            param_var_match = re.match( "^"+re.escape(payload_function)+
                                "\([A-Za-z0-9_\$]+\.[A-Za-z0-9_\$]+,[A-Za-z0-9_\$]+\+"
                                "[A-Za-z0-9_\$]+\([A-Za-z0-9_\$]+,([A-Za-z0-9_\$]+)\)\)$", 
                                rpc_js_function[i] )
                                
                            if param_var_match:
                                param = get_global_val( param_var_match.group(1), the_page )
                                methods[-1] = methods[-1]+param+","
                             
                        a_method = methods[-1][:-1]
                        methods[-1] = a_method + " )"
                        break
    
    line_decor = "\n===========================\n"
    print( "\n%sEnumerated Methods%s" % ( line_decor, line_decor ) )
    methods = sorted(list(set(methods))) #uniq
        
    for method in methods:
        print( method )
    
    print( "\n\n" )

########NEW FILE########
__FILENAME__ = gwtfuzzer
# -*- coding: utf-8 -*-
#!/usr/bin/env python

"""

    GwtFuzzer v0.1
    Copyright (C) 2010 Ron Gutierrez

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""

import urllib2
import urllib
import os
import os.path
import time
from GWTParser import GWTParser
from gds.pub.burp import parse
from itertools import product
from optparse import OptionParser

'''
    Globals
'''

attacklog = []
param_manip_log = []


def replay( burpobj, fuzzified, attackstr, gwtparsed, log ):
    global options
    
    headers = burpobj.get_request_headers()

    if options.cookies is not None:   
        headers["Cookie"] = options.cookies
        
    headers["Content-Length"] = str(len(fuzzified))
    
    req = urllib2.Request(burpobj.url.geturl(), fuzzified, headers )
    
    handlers = [ urllib2.HTTPHandler() ]

    if options.proxy is not None:    
        handlers.append( urllib2.ProxyHandler( {'http':options.proxy} ) )
        
    opener = urllib2.build_opener(*handlers)
    urllib2.install_opener( opener )

    errors_found = []    
    try:    
        resp = urllib2.urlopen(req)
        data = resp.read()
        
        # Check for error messages
        errors_found = check_errors(data)

        # Check to see if a exception message was returned        
        if is_exception(data):
            errors_found.append( "GWT Exception Returned" )
        
        # Success        
        log.append( { 'method':gwtparsed.rpc_deserialized[2]+"."+gwtparsed.rpc_deserialized[3],
            'request_url':burpobj.url.geturl(),
                            'request_headers':headers,
                           'request_payload':fuzzified,
                           'attack': attackstr,
                           'response_status':200,
                           'response_content':data,
                           'response_size':len(data),
                           'errors_found':errors_found })
        
    except urllib2.HTTPError, e:
        # Request did not return a 200 OK
        log.append( {'method':gwtparsed.rpc_deserialized[2]+"."+gwtparsed.rpc_deserialized[3],
            'request_url':burpobj.url.geturl(),
                           'request_headers':headers,
                           'request_payload':fuzzified,
                           'attack': attackstr,
                           'response_status':e.code,
                           'response_content':e.read(),
                           'response_size':len(e.read()),
                           'errors_found':errors_found })
    except urllib2.URLError, e:
        # Host could not be reached
        log.append( {'method':gwtparsed.rpc_deserialized[2]+"."+gwtparsed.rpc_deserialized[3],
            'request_url':burpobj.url.geturl(),
                           'request_headers':headers,
                           'request_payload':fuzzified,
                           'attack': attackstr,
                           'response_status':'Python URLError Exception',
                           'response_content':e.reason(),
                           'response_size':0,
                           'errors_found':errors_found})
        
        print( "Request failed: "+burpobj.url.geturl()+"("+e.reason+")" )


def check_errors( data ):
    global errors
    found = []

    for error in errors:
        if data.find( error ) != -1:
            found.append( error )
            print( "found "+error )

    return found


def is_exception( data ):
    if data.find( "//EX[", 0, 8 ) != -1:
        return True

    return False


def escape( str ):
    return str.replace( '<', '&lt;' ).replace( '>', '&gt;' ).replace( '"', '&quot' ).replace( '\'', '&#39;')


def filter_gwt_reqs( parsed ):
    filtered = []
    for burpobj in parsed:
        headers = burpobj.get_request_headers()
        if "Content-Type" in headers:
            if headers["Content-Type"].find("text/x-gwt-rpc") != -1:
                filtered.append( burpobj )
            
    return filtered    


def get_number_range( num ):
    if num < options.idrange:
        return 0, num+options.idrange

    begin = int(num)-int(options.idrange)
    end = int(num)+int(options.idrange) 
    return begin, end 


def load_strings( list, filename ):
    if os.path.exists( filename ):
        f = open( filename, 'r' )

        for line in f:
            if line.find( "# ", 0, 2 ) == -1: # Ignore FuzzDB comments
                list.append( line.strip() )
               
        f.close()
    else:
        print( "Error: "+filename+" does not exist" )
        exit()

      
def fuzz( burpobj ):
    global options, attacks, attacklog, param_manip_log

    # Parse the gwt string
    gwtparsed = GWTParser()
    gwtparsed.deserialize( burpobj.get_request_body() )
    
    gwtlist = burpobj.get_request_body().split('|')

    # This is where the magic happens.. Special Thanks to Marcin W.

    # Test all GWT requests using the attack strings submitted
    for( idx, param ), fuzzy in product( enumerate(gwtlist), attacks ):
        # Check to see if index was marked as a fuzzible string value by GWTParse
        if idx in gwtparsed.fuzzmarked and gwtparsed.fuzzmarked[idx] == "%s":
            fuzzified = "%s|%s|%s" %('|'.join(gwtlist[:idx]), fuzzy.replace('|','\!'), '|'.join(gwtlist[idx+1:]))
            replay( burpobj, fuzzified, fuzzy, gwtparsed, attacklog ) # Submit the request

    # Test all GWT request for Parameter Manipulation
    for idx, param in enumerate( gwtlist ):
        if idx in gwtparsed.fuzzmarked and gwtparsed.fuzzmarked[idx] == "%d":
            begin, end = get_number_range( param )
            for i in range( int(begin), int(end) ):
                fuzzified = "%s|%s|%s" %('|'.join(gwtlist[:idx]), str(i), '|'.join(gwtlist[idx+1:]))
                replay( burpobj, fuzzified, str(i), gwtparsed, param_manip_log ) #Submit the request
            

def reportfuzz( logdir ):
    global attacklog
        
    f = open( logdir+"//gwtfuzz.html", 'w' )

    f.write( '''
    <html>
    <head>
        <title>GWTFuzz Results</title>
        <style type="text/css">
            td, th{
                font-family: sans-serif;
                font-size: 12px;
                border: thin solid black;
                word-wrap: break-word;
                border-spacing: 0;
                padding: 1px 1px 1px 1px;
            }

            tr.error{
                background-color: #FFCC66;
            }
        </style>        
    </head>
    <body>
    <h2>Fuzz Results</h2>
    <table cellspacing=0 style="border: thin solid black;">
    <tr>
        <td>ID</th>
        <th>Endpoint URL</th>
        <th>RPC Method</th>
        <th>Attack</th>
        <th>Request Data</th>
        <th>Resp Status</th>
        <th>Resp Size</th>
        <th>Resp Content</th>
        <th>Errors Found</th>
    </tr>''' )
    
    for idx, entry in enumerate(attacklog):
        if len(entry['errors_found']) > 0:
            f.write( '<tr class="error">' )
        elif entry['response_status'] != 200:
            f.write( '<tr class="error">' )
        else:
            f.write( '<tr>' )
            
        f.write( '<td style="max-width:300px;text-align:right">'+str(idx)+'</td>' +
                 '<td style="max-width:300px;">'+escape(entry['request_url'])+'</td>' +
                 '<td style="max-wdth:300px;">'+escape(entry['method'])+'</td>' +
                 '<td style="max-width:300px;text-align:center">'+escape(entry['attack'])+'</td>' +
               '<td style="max-width:450px;">'+escape(entry['request_payload'])+'</td>' +
               '<td style="width=10px;max-width:10px;text-align:right">'+str(entry['response_status'])+'</td>' +
               '<td style="width=10px;max-width:10px;text-align:right">'+str(entry['response_size'])+'</td>' +
               '<td style="max-width:150px;"><a href="responses/'+str(idx)+'.txt" target="_new">View Response</a></td>' +
                '<td style="max-width:100px;">' )

        errorstr = ""
        
        for error in entry['errors_found']:
            errorstr = errorstr + escape(error) + ", "

        errorstr = errorstr[:-2]

        f.write( errorstr+'</td></tr>' )

        # Write the HTTP response into a text file
        f2 = open( logdir+'//responses/'+str(idx)+'.txt', 'w' ) 
        f2.write( entry['response_content'] )
        f2.close()
    
    f.write( '</table></body></html>' )
    f.close()

    print( "Results saved to "+logdir )    

def reportparam( logdir ):
    global param_manip_log
    
    f = open( logdir+"//param_manip.html", 'w' )

    f.write( '''
    <html>
    <head>
        <title>GWT Parameter Manipulation Results</title>
        <style type="text/css">
            td, th{
                font-family: sans-serif;
                font-size: 12px;
                border: thin solid black;
                word-wrap: break-word;
                border-spacing: 0;
                padding: 1px 1px 1px 1px;
            }
            tr.status{
                background-color: #FFCC66;
            }

            tr.error{
                background-color: #FF3333;
            }
        </style>        
    </head>
    <body>
    <h2>GWT Parameter Manipulation Results</h2>
    <table cellspacing=0 style="border: thin solid black;">
    <tr>
        <td>ID</th>
        <th>Endpoint URL</th>
        <th>RPC Method</th>
        <th>Attack</th>
        <th>Request Data</th>
        <th>Resp Status</th>
        <th>Resp Size</th>
        <th>Resp Content</th>
    </tr>''' )
    
    for idx, entry in enumerate(param_manip_log):     
        f.write( '<tr><td style="max-width:300px;text-align:right">'+str(idx)+'</td>' +
                 '<td style="max-width:300px;">'+escape(entry['request_url'])+'</td>' +
                 '<td style="max-wdth:300px;">'+escape(entry['method'])+'</td>' +
                 '<td style="max-width:300px;text-align:center">'+escape(entry['attack'])+'</td>' +
               '<td style="max-width:450px;">'+escape(entry['request_payload'])+'</td>' +
               '<td style="width=10px;max-width:10px;text-align:right">'+str(entry['response_status'])+'</td>' +
               '<td style="width=10px;max-width:10px;text-align:right">'+str(entry['response_size'])+'</td>' +
               '<td style="max-width:150px;"><a href="responses/p'+str(idx)+'.txt" target="_new">View Response</a></td></tr>' +
                '<td style="max-width:100px;">' )
            
        # Write the HTTP response into a text file
        f2 = open( logdir+'//responses//p'+str(idx)+'.txt', 'w' ) 
        f2.write( entry['response_content'] )
        f2.close()
    
    f.write( '</table></body></html>' )
    f.close()    

      
if __name__ == "__main__":
    global options, attacks, errors
    attacks = []
    errors = []
    
    parser = OptionParser( usage="usage: %prog [options]",
                           description='Automates the fuzzing of GWT RPC requests',
                           version='%prog 0.10' )

    parser.add_option('-b', '--burp',
                      help='Burp logfile to fuzz',
                      action='store' )

    parser.add_option('-f', '--fuzzfile',
                      help='File containing attack strings',
                      action='store' )

    parser.add_option('-e', '--errorfile',
                      help='File containing error messages',
                      action='store' )

    parser.add_option('-o', '--output',
                      help='Directory to store results',
                      action='store' )

    parser.add_option('-k', '--cookies',
                      help='Cookies to use when requesting GWT RPC pages',
                      action='store' )

    parser.add_option('-p', '--proxy',
                      help='Proxy Host and Port (e.g. -p "http://proxy.internet.net:8080"',
                      action='store' )

    parser.add_option('-i', '--idrange',
                      help='Range of decrements and increments to test parameter manipulation with',
                      action='store' )

    (options, args) = parser.parse_args()

    if options.burp is None:
        print( "\nError: Missing Burp log file\n" )
        parser.print_help()
        exit()
    elif options.fuzzfile is None:
        print( "\nError: Missing fuzz file\n" )
        parser.print_help()
        exit()

    if options.idrange and options.idrange < 1:
        options.idrange = 100
        print( "Invalid ID Range Entered: ID Range has been set to 100\n" )
    elif options.idrange is None:
        options.idrange = 100
        print( "ID Range for Parameter Manipulation Testing has been set to 100\n" )
        
    parsed = None

    # Parse the Burp log using the GDS Burp API    
    if os.path.exists( options.burp ):
        print( "Parsing Burp logfile" )
        parsed = parse( options.burp )
    else:
        print( "\nBurp log file entered does not exist\n" )
        exit()

    logdir = ""
    
    if options.output and os.path.exists( options.output ):
        print( "Error: Output directory already exists." )
        exit()
    elif options.output:
        logdir = options.output
    else:
        logdir = "gwtfuzz_results"+time.strftime("%Y%m%d%H%M%S")

    os.mkdir( logdir )
    os.mkdir( logdir+"//responses" )

    if options.fuzzfile:
        load_strings(attacks, options.fuzzfile)

    if options.errorfile:
        load_strings(errors, options.errorfile)
        
    # Filter out the GWT RPC Requests from the log    
    filtered = filter_gwt_reqs(parsed)

    print( "Fuzzing has commenced" )    
    # Fuzz each GWT RPC Request
    for burpobj in filtered:
        fuzz( burpobj )

    # Generate Parameter Manipulation Report
    reportparam( logdir )
    
    reportfuzz( logdir )
    

########NEW FILE########
__FILENAME__ = gwtparse
# -*- coding: utf-8 -*-
#!/usr/bin/env python

"""

    GwtParse v0.2
    Copyright (C) 2010 Ron Gutierrez

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""

import os
from optparse import OptionParser
from GWTParser import GWTParser

desc = "A tool for parsing GWT RPC Requests"

if __name__ == "__main__":
    parser = OptionParser(usage='usage: %prog [options]', description=desc, version='%prog 0.10')
    
    parser.add_option('-p', '--pretty', help="Output the GWT RPC Request in a human readible format", action="store_true")
    parser.add_option('-s', '--surround', help="String used to surround all fuzzable values", action="store", dest="surround_value")
    parser.add_option('-r', '--replace', help="String used to replace all fuzzable values", action="store", dest="replace_value")
    parser.add_option('-b', '--burp', help="Generates Burp Intruder Output", default=False, action="store_true")
    parser.add_option('-i', '--input', help="RPC Request Payload (Required)", action="store", dest="rpc_request")
    parser.add_option('-w', '--write', help="Writes Fuzz String to a new output file", action="store" )
    parser.add_option('-a', '--append', help="Appends Fuzz String to an existing output file", action="store" )
    
    (options, args) = parser.parse_args()

    if options.rpc_request:
    
        if options.surround_value and options.replace_value and options.burp:
            print( "\nCannot choose more then one output format.\n" )
            parser.print_help()
            exit()
        
        if options.surround_value and options.replace_value:
            print( "\nCannot choose more then one output format.\n" )
            parser.print_help()
            exit()
            
        if options.surround_value and options.burp:
            print( "\nCannot choose more then one output format.\n" )
            parser.print_help()
            exit()
            
        if options.replace_value and options.burp:
            print( "\nCannot choose more then one output format.\n" )
            parser.print_help()
            exit()
            
        gwt = GWTParser()
        
        if options.surround_value:
            gwt.surround_value = options.surround_value
        elif options.replace_value:
            gwt.replace_value = options.replace_value
        elif options.burp:
            gwt.burp = options.burp
        
        
        if options.write:
            if os.path.exists(options.write):
                print( "Output file entered already exists" )
                exit()
                
            fout = open( options.write, "w" )
            gwt.fout = fout
            
        elif options.append:
            fout = open( options.append, "a" )
            gwt.fout = fout
        
        gwt.deserialize( options.rpc_request )
        
        if options.pretty:
            gwt.display()
        
        gwt.get_fuzzstr()
        
        if gwt.fout:
            gwt.fout.close()
        
    else:
        print( "\nMissing RPC Request Payload\n" )
        parser.print_help()
        
    
    

########NEW FILE########
__FILENAME__ = GWTParser
# -*- coding: utf-8 -*-
#!/usr/bin/env python

"""

    GwtParse v0.2
    Copyright (C) 2010 Ron Gutierrez

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""

import sys
import re
import pprint
from Parameter import Parameter

reload(sys)
sys.setdefaultencoding('utf-8')


#################################################
#
#   Java Primitive Types and Object Wrappers
#
#################################################

FUZZ_STRING = "%s"
FUZZ_DIGIT = "%d"

STRING_OBJECT = "java.lang.String"
INTEGER_OBJECT = "java.lang.Integer"
DOUBLE_OBJECT = "java.lang.Double"
FLOAT_OBJECT = "java.lang.Float"
BYTE_OBJECT = "java.lang.Byte"
BOOLEAN_OBJECT = "java.lang.Boolean"
SHORT_OBJECT = "java.lang.Short"
CHAR_OBJECT = "java.lang.Char"
LONG_OBJECT = "java.lang.Long"

PRIMITIVES_WRAPPER = [ STRING_OBJECT, INTEGER_OBJECT, DOUBLE_OBJECT, FLOAT_OBJECT, BYTE_OBJECT, BOOLEAN_OBJECT, SHORT_OBJECT, CHAR_OBJECT ]

LONG = "J"
DOUBLE = "D"
FLOAT = "F"
INT = "I"
BYTE = "B"
SHORT = "S"
BOOLEAN = "Z"
CHAR = "C"

PRIMITIVES = [ "J", "D", "F", "I", "B", "S", "Z", "C" ] 
NUMERICS = [ INT, CHAR, BOOLEAN, BYTE, SHORT, INTEGER_OBJECT, CHAR_OBJECT, BYTE_OBJECT, BOOLEAN_OBJECT, SHORT_OBJECT ]

ARRAYLIST = "java.util.ArrayList"
LINKEDLIST = "java.util.LinkedList"
VECTOR = "java.util.Vector"

ListTypes = [ ARRAYLIST, LINKEDLIST, VECTOR ]

prev_index = 0
INDENTATION = 15

# Indicates that obfuscated type names should be used in the RPC payload.
FLAG_ELIDE_TYPE_NAMES = 0x1

# Indicates that RPC token is included in the RPC payload.
FLAG_RPC_TOKEN_INCLUDED = 0x2

# Bit mask representing all valid flags.
VALID_FLAGS_MASK = 0x3

class GWTParser(object):
    
    def _cleanup(self):
        self.data = []
        self.rpc_deserialized = []
        self.rpc_list = []
        self.indices = []
        self.data_types = []
        self.parameters = []
        self.stream_version = 0
        self.flags = 0
        self.columns = 0
        self.parameter_idx = 0
        self.fuzzmarked = dict()
        
    '''
    Sets a value as fuzzable
    '''
    def _set_fuzzable( self, idx, fuzz_value ):
        fuzz_idx = int(idx)+2
        
        if self.surround_value:
            if not fuzz_idx in self.fuzzmarked:
                self.rpc_list_fuzzable[fuzz_idx] = self.surround_value+self.rpc_list_fuzzable[fuzz_idx]+self.surround_value
        
        elif self.replace_value:
            self.rpc_list_fuzzable[fuzz_idx] = self.replace_value
        
        elif self.burp:
            if not fuzz_idx in self.fuzzmarked:
                self.rpc_list_fuzzable[fuzz_idx] = '§'+self.rpc_list_fuzzable[fuzz_idx]+'§'
                
        else:
            self.rpc_list_fuzzable[fuzz_idx] = fuzz_value
        
        self.fuzzmarked[fuzz_idx] = fuzz_value
        
            
    '''
    Check if the next index value is an integer or a data index
    '''
    def _nextval_is_an_integer(self, curr_index):
        if len(self.indices) == 0:
            return False
        
        # If the index is out of data array scope
        if int(self.indices[0]) <= 4 or int(self.indices[0]) > self.columns:
            return True
            
        # If next index is the increment of the previous    
        if int(curr_index) == int(self.indices[0])-1:
            if len(self.indices) > 1:
                if int(self.indices[0]) == int(self.indices[1]):
                        return True
        
        return False
        

    '''
    Put back the index that was pop previously
    '''
    def _indice_rollback(self, prev_index):
        self.indices_read -= 1
        self.indices.insert(0,prev_index)
        
        
    ''' 
    Is the next value an object type name
    '''
    def _is_an_object(self, value):
        obj_check = re.compile( ".*/\d+" )
        match = obj_check.match(value)
        
        if match:
            return True

        return False

    ''' 
    Check to see if the type is an array of primitives
    '''
    def _is_a_primitive_array(self, data_type):
        arr_check = re.compile( "\[(\w)/\d+" )
        match = arr_check.match(data_type)
        
        if match and match.group(1) in PRIMITIVES:
            self.parameters[self.pidx].typename = match.group(1)
            self.parameters[self.pidx].is_array = True
            return True
            
        return False
    
    '''
    Is the passed in value the subtype value for the current parameters typename
    '''
    def _is_object_subtype( self, data_type ):
        typename = ""
        
        if self.parameters[self.pidx].is_list:
            typename = self.parameters[self.pidx].subtype
        else:
            typename = self.parameters[self.pidx].typename
    
        subtype_check = re.compile( typename+"/\d+" )
        match = subtype_check.match( data_type )

        if match:
            return True
        
        return False
    
    '''
    Check to see if the type is array of objects
    '''
    def _is_an_object_array( self, data_type):
        arr_check = re.compile( "\[L(.*);/\d+" )
        match = arr_check.match(data_type)

        if match:
            self.parameters[self.pidx].typename = match.group(1)
            self.parameters[self.pidx].is_array = True
            return True
            
        return False
        
    '''
    Check to see if data_type is a ListType
    '''
    def _is_list_type( self, data_type ):
        if self._get_typename(data_type) in ListTypes:
            return True
            
        return False
        
    
    '''
    Check to see if the index passed in is an integer value
        - This check needs some major work
    '''
    def _indice_is_intval( self, idx ):
        # If the index is out of data array scope
        if int(self.indices[int(idx)]) <= 4 or int(self.indices[int(idx)]) > self.columns:
            return True
        
        return False
                    
    
    '''
    Check to see if the remaining method parameters are all numeric
    '''
    def _remaining_params_are_numeric( self, tracker_idx):      
        for i in range( self.pidx+1, len(self.parameters)):
            if not self._get_typename(self.parameters[i].typename) in NUMERICS:
                return False
                
        return True
        
    
    '''
    Checks to see whether we should stop reading values into a custom object
    '''
    def _is_end_of_object( self, prev_index, value ):   
        tracker_idx = 0
        found = False
        
        if self._remaining_params_are_numeric( tracker_idx ):

            if len(self.indices) == len(self.parameters[self.pidx+1:]):
                prev_index = self.indices[0]
                self._add_stringval(value)
                return True
            else:
                return False
                
        if len(self.parameters[self.pidx+1:]) == len(self.indices):
            prev_index = self.indices[0]
            self._add_stringval(value)
            return True
            
        for i in range( self.pidx+1, len( self.parameters ) ):
                    
            # Look Into the Future and see if the parameter values are still there
            for j in range( tracker_idx, len(self.indices) ):
                
                if self._get_typename(self.parameters[i].typename) in NUMERICS: 
                    
                    if self._indice_is_intval(j):
                        found = True
                        tracker_idx = j
                        continue
                    
                elif self._get_typename(self.parameters[i].typename) == STRING_OBJECT:
                    
                    # If the index is out of data array scope
                    if int(self.indices[j]) <= 4 or int(self.indices[j]) > self.columns:
                        continue
                                            
                    if self._is_an_object( self.data[int(self.indices[j])] ) is False:
                        found = True
                        tracker_idx = j
                        break
                    
                else:
                    # If the index is out of data array scope
                    if int(self.indices[j]) <= 4 or int(self.indices[j]) > self.columns:
                        continue
                        
                    # This must be a custom object. Check for the subtype..
                    if self._get_typename(self.data[int(self.indices[j])]) == self._get_typename(self.parameters[i].typename):
                        found = True
                        tracker_idx = j
                        break
                        
            if not found:
                return True # Did not find the next parameter so the current value is the next method param
            else:
                found = False 
                
        return False
            
    '''
    Removes the "/" and digits from a typename
    '''
    def _get_typename( self, data_type):
        subtype_check = re.compile( "(.*)/\d+" )
        match = subtype_check.match(data_type)
        
        if match:
            return match.group(1)
        
        return data_type
    
    
    '''
    Get the next index or integer value
    '''
    def _pop_index(self):
        try:
            self.indices_read += 1
            index = int(self.indices.pop(0))
        except TypeError:
            print ("Invalid Integer given for indices")
            sys.exit()
    
        return index
    
    
    '''
    Get the next float value
    '''
    def _pop_float_index(self):
        try:
            self.indices_read += 1
            index = float(self.indices.pop(0))
        except TypeError:
            print ("Invalid float value read")
            sys.exit()
    
        return index
    
    
    '''
    Pop the next index value and then return the corresponding value
    from the data table
    '''
    def _get_nextval(self):
        return self.data[self._pop_index()]
    
    
    def _add_intval(self):
        if self.parameters[self.pidx].flag:
            self.parameters[self.pidx].values[self.aidx].values.append(self._pop_index())
        elif self.parameters[self.pidx].is_list and self.parameters[self.pidx].is_custom_obj:
            self.parameters[self.pidx].values[self.lidx].values.append(self._pop_index())
        else:
            self.parameters[self.pidx].values.append(self._pop_index())
    
    
    def _add_stringval(self, value):
        if self.parameters[self.pidx].flag:
            self.parameters[self.pidx].values[self.aidx].values.append(value)
        elif self.parameters[self.pidx].is_list and self.parameters[self.pidx].is_custom_obj:
            self.parameters[self.pidx].values[self.lidx].values.append(value)
        else:
            self.parameters[self.pidx].values.append(value)
        
        
    ###################################
    #
    # Parsing Methods
    #
    ####################################
    
    def _parse_read_string(self):
        self._set_fuzzable( self.indices[0], FUZZ_STRING )
        
        if self.parameters[self.pidx].flag:
            self.parameters[self.pidx].values[self.aidx].append(self._get_nextval())
        else:
            if self.parameters[self.pidx].is_list:
                subtype = self._get_nextval()
                
            self.parameters[self.pidx].values.append(self._get_nextval())
    
    
    def _parse_read_int_byte_short_char(self, is_wrapper=False):
        if is_wrapper:
            subtype = self._get_nextval()
        
        self._set_fuzzable( self.indices_read+self.columns, FUZZ_DIGIT )
        
        if self.parameters[self.pidx].flag:
            self.parameters[self.pidx].values[self.aidx].values.append(self._pop_index())
        else:
            self.parameters[self.pidx].values.append(self._pop_index())
        
        
    def _parse_read_long(self, is_wrapper=False):
        if is_wrapper:
            subtype = self._get_nextval()
            
        value1 = self._pop_float_index()
        value2 = self._pop_float_index()
        
        self._set_fuzzable( self.indices_read+self.columns-2, FUZZ_DIGIT )
        self._set_fuzzable( self.indices_read+self.columns-1, FUZZ_DIGIT )
        
        
        if value2 > 0:  
            self.parameters[self.pidx].values.append( str(value1) + str(value2) )
        else:
            self.parameters[self.pidx].values.append( str(value1) )
    
    
    def _parse_read_double_float(self, is_wrapper=False):
        if is_wrapper:
            subtype = self._get_nextval()
            
        self._set_fuzzable( self.indices_read+self.columns, FUZZ_DIGIT )
        self.parameters[self.pidx].values.append(self._pop_float_index())
    
    def _parse_primitive_array(self):
        subtype = self._get_nextval()
        how_many = self._pop_index()
        
        for i in range(how_many):
            self._parse_value( self.parameters[self.pidx].typename )
        
    def _parse_object_array(self):
        if self.parameters[self.pidx].flag is False:
            subtype = self._get_nextval()
            
        how_many = self._pop_index()
        
        self.aidx = 0 
        for i in range(how_many):
            self._parse_value(self.parameters[self.pidx].typename )
            self.aidx += 1
        
    def _parse_read_boolean(self):      
        self._set_fuzzable( self.indices_read+self.columns, FUZZ_DIGIT )
        int_value = self._pop_index()
            
        if int_value == 1:
            self.parameters[self.pidx].values.append( "true" )
        else:
            self.parameters[self.pidx].values.append( "false" )
                
    def _parse_read_list(self, list_type, set_list_flag=True):
        if self.parameters[self.pidx].flag is False:
            
            if set_list_flag:
                self.parameters[self.pidx].is_list = True
                
            self.parameters[self.pidx].typename = list_type
            subtype = self._get_nextval()
            
        else:
            self.parameters[self.pidx].values[self.aidx].typename = list_type
            
        how_many = self._pop_index()
        self.lidx = 0
        
        for i in range(how_many):
        
            prev_index = self.indices[0]
            
            if self.parameters[self.pidx].flag: # Reading a List within a Custom Object
                subtype = self._get_typename(self._get_nextval())
                self.parameters[self.pidx].values[self.aidx].subtype = subtype
                self._indice_rollback(prev_index)
                self._parse_value(subtype)
                
            else: # Read values within a List Method Parameter
                self.parameters[self.pidx].subtype = self._get_typename(self._get_nextval())
                self._indice_rollback(prev_index)
                self._parse_value(self.parameters[self.pidx].subtype)
    
            self.lidx += 1
    
    
    def _parse_read_object(self,name):
        
        if len( self.indices ) > 0:
            prev_index = self.indices[0]
        
        self.parameters[self.pidx].is_custom_obj = True
        value = self._get_nextval()
        
        if self.parameters[self.pidx].is_array and self.parameters[self.pidx].is_custom_obj:
            customParam = Parameter( value )
            customParam.is_custom_obj = True
            self.parameters[self.pidx].values.append( customParam )
            self.parameters[self.pidx].flag = True
        
        if self.parameters[self.pidx].is_list and self.parameters[self.pidx].is_custom_obj:
            customParam = Parameter(value)
            customParam.is_custom_obj = True
            self.parameters[self.pidx].values.append(customParam)
        
        # If this is the final parameter just read the remaining data as member variables
        if len(self.parameters)-1 == self.pidx:

            while len(self.indices) > 0: # Read till the end of the index table
                
                if self._nextval_is_an_integer( prev_index ):

                    prev_index = self.indices[0]
                    self._set_fuzzable( self.indices_read+self.columns, FUZZ_DIGIT )
                    self._add_intval()
                    continue
                    
                else:
                    prev_index = self.indices[0]
                    value = self._get_nextval()
                    
                if self.parameters[self.pidx].is_array or self.parameters[self.pidx].is_list: # Am I reading an array of objects?   
                
                    if self._is_object_subtype(value): # Did I just read in an object subtype?
                        self._indice_rollback(prev_index)
                        break # Stop reading object and move onto the next object in the array
                    
                if self._is_list_type( value ):
                
                    if self.parameters[self.pidx].flag is False:
                        self._indice_rollback(prev_index)
                        
                    self._parse_read_list(self._get_typename(value), False)
                    
                elif self._is_an_object(value): # Is the value I just read in a subtype for another class
                    prev_index = self.indices[0]

                else:
                    self._add_stringval(value)
                    self._set_fuzzable( prev_index, FUZZ_STRING )
                    
        else: # There are more parameters so we must be careful with the parsing

            while len(self.indices) > 0: 
            
                if self._nextval_is_an_integer( prev_index ):
                    self._set_fuzzable( self.indices_read+self.columns, FUZZ_DIGIT )
                    prev_index = self.indices[0]
                    self._add_intval()
                else:
                    prev_index = self.indices[0]
                    value = self._get_nextval()
                            
                    if self.parameters[self.pidx].is_array or self.parameters[self.pidx].is_list:
                    
                        if self._is_object_subtype(value):
                            self._indice_rollback(prev_index)
                            break;
                
                    if self._is_end_of_object( prev_index, value ):

                        if self.parameters[self.pidx].is_list or self.parameters[self.pidx].is_array:
                            self.pidx += 1
                            self._indice_rollback(prev_index)
                            self._parse_value( self.parameters[self.pidx].typename )
                            
                        else:
                            if not self._get_typename(self.parameters[self.pidx+1].typename) in NUMERICS:
                                self._indice_rollback(prev_index)
                            break
                            
                    elif self._is_an_object( value ):
                        continue
                        
                    else: # store value
                        self._set_fuzzable( prev_index, FUZZ_STRING )
                        prev_index = self.indices[0]
                        self._add_stringval(value)                      
            
        self.parameters[self.pidx].flag = False
                            
    '''
    Split the object into a list and remove the last element
    The RPC String ends with a '|' so this will create an empty element
    '''
    def _read_string_into_list(self):
        # This copy is used to keep track of fuzzable values
        self.rpc_list_fuzzable = list(self.rpc_string.split('|'))
        self.rpc_list_fuzzable.pop()
        
        # This copy is used to parsing and will have values removed during parsing
        self.rpc_list = self.rpc_string.split('|')
        self.rpc_list.pop()
    
    
    '''
    Store and remove the first three elements of the list
    '''
    def _get_headers(self):
        try:
            self.stream_version = int(self.rpc_list.pop(0))
            self.flags = int(self.rpc_list.pop(0))
            self.columns = int(self.rpc_list.pop(0))
        except TypeError:
            print ("Invalid Integer given for the stream_version or number of columns")
            sys.exit()
    
    
    '''
    Store the data inside of the serialized object
    I add in an empty string in the 0 Element in order to
    stay uniform with the indices table in the RPC Object
    '''
    def _get_data(self):
        self.data = self.rpc_list[0:self.columns]
        self.data.insert(0,"")
    
    
    '''
    Store the indices that are found at the end of the RPC serialized object
    '''
    def _get_indices(self):
        self.indices = self.rpc_list[self.columns:]
    
    
    '''
    Parses a value from the string table
    '''
    def _parse_value(self, data_type):
        
        if self._get_typename(data_type) == STRING_OBJECT:
            self._parse_read_string()
                    
        elif self._get_typename(data_type) == INT or data_type == BYTE or data_type == SHORT or data_type == CHAR:
            self._parse_read_int_byte_short_char()
            
        elif self._get_typename(data_type) == INTEGER_OBJECT or data_type == BYTE_OBJECT or data_type == SHORT_OBJECT or data_type == CHAR_OBJECT:
            self._parse_read_int_byte_short_char(True)
            
        elif self._get_typename(data_type) == LONG:
            self._parse_read_long()
            
        elif self._get_typename(data_type) == LONG_OBJECT:
            self._parse_read_long(True)
            
        elif self._get_typename(data_type) == DOUBLE or data_type == FLOAT:
            self._parse_read_double_float()
        
        elif self._get_typename(data_type) == DOUBLE_OBJECT or data_type == FLOAT_OBJECT:
            self._parse_read_double_float(True)
            
        elif self._is_a_primitive_array(data_type):
            self._parse_primitive_array()
            
        elif self._is_an_object_array(data_type):
            self._parse_object_array()

        elif self._get_typename(data_type) == BOOLEAN:
            self._parse_read_boolean()
        
        elif self._is_list_type(data_type):
            self._parse_read_list(data_type)
            
        else:
            self._parse_read_object(data_type)
            
    '''
    Parses the GWT-RPC Request Payload
    '''
    def _parse(self):
        self.rpc_deserialized = []
        self.parameters = [] # Stores Parameter names and values read in from the request
        self.pidx = 0 # Index value used to know which Parameter we are currently writing into
        self.indices_read = 1 # Keeps track how many indices we have read
        
        '''
        Store the first four values
        Hostname, Hash, Class Name, Method
        '''
        # rpc request has an rpc/xsrf token
        if (self.flags & FLAG_RPC_TOKEN_INCLUDED):
            self.rpc_deserialized.append(self._get_nextval()) # hostname
            self.rpc_deserialized.append(self._get_nextval()) # strong name
            
            self.rpc_token = {}
            self.rpc_token[self._get_nextval()] = self._get_nextval()
            
            self.rpc_deserialized.append(self._get_nextval()) # interface
            self.rpc_deserialized.append(self._get_nextval()) # method
        
        else:
            for i in range(4):
                self.rpc_deserialized.append(self._get_nextval())
        
        for index in self.indices:
            num_of_params = self._pop_index() # Number of Method parameters
            
            for i in range(num_of_params):
                self.parameters.append( Parameter(self._get_nextval()) )
                
            for param in self.parameters:
                if num_of_params > self.pidx: # If parameter index is greater than number of params then we are done
                    self._parse_value(param.typename)
                    self.pidx += 1
    
    
    '''
    Handles the parsing of the RPC string
    '''
    def deserialize(self, rpc_string):
        self._cleanup()
        self.rpc_string = rpc_string
        self._read_string_into_list()
        self._get_headers()
        self._get_data()
        self._get_indices()
        try:
            self._parse()
        except IndexError:
            print( "Encountered Error During Parsing" )
    
    def get_fuzzstr(self):
        fuzzstr = "|".join( self.rpc_list_fuzzable )+"|"
        
        if self.fout:   
            self.fout.write( fuzzstr+"\n" )
            
        else:
            print( "\nGWT RPC Payload Fuzz String\n" )
            print( fuzzstr+"\n" )
        
    '''
    Prints out the deserialized method call in a user friendly format
    '''
    def display(self):
    
        if self.fout:
            self.fout.write("==================================\n")
            self.fout.write(str("Serialized Object:").rjust(INDENTATION) + "\n" + self.rpc_string + "\n\n")
            self.fout.write(str("Stream Version:").rjust(INDENTATION) + "\t" + str(self.stream_version)+"\n")
            self.fout.write(str("Flags:").rjust(INDENTATION) + "\t" + str(self.flags+"\n"))
            self.fout.write(str("Column Numbers:").rjust(INDENTATION) + "\t" + str(self.columns)+"\n")
            self.fout.write(str("Host:").rjust(INDENTATION) + "\t" + self.rpc_deserialized[0]+"\n")
            self.fout.write(str("Hash:").rjust(INDENTATION) + "\t" + self.rpc_deserialized[1]+"\n")
            self.fout.write(str("Class Name:").rjust(INDENTATION) + "\t" + self.rpc_deserialized[2]+"\n")
            self.fout.write(str("Method:").rjust(INDENTATION) + "\t" + self.rpc_deserialized[3] + "\n")
            self.fout.write(str("# of Params:").rjust(INDENTATION) + "\t" + str(len(self.parameters)) + "\n")
            self.fout.write(str("Parameters:").rjust(INDENTATION)+"\n")
        else:   
            print (str("\nSerialized Object:").rjust(INDENTATION) + "\n" + self.rpc_string + "\n")
            print (str("Stream Version:").rjust(INDENTATION) + "\t" + str(self.stream_version))
            print (str("Flags:").rjust(INDENTATION) + "\t" + str(self.flags))
            print (str("Column Numbers:").rjust(INDENTATION) + "\t" + str(self.columns))
            print (str("Host:").rjust(INDENTATION) + "\t" + self.rpc_deserialized[0])
            print (str("Hash:").rjust(INDENTATION) + "\t" + self.rpc_deserialized[1])
            print (str("Class Name:").rjust(INDENTATION) + "\t" + self.rpc_deserialized[2])
            print (str("Method:").rjust(INDENTATION) + "\t" + self.rpc_deserialized[3])
            print (str("# of Params:").rjust(INDENTATION) + "\t" + str(len(self.parameters)) + "\n")
            print (str("Parameters:").rjust(INDENTATION))
        
        for parameter in self.parameters:
            if self.fout:
                pprint.pprint(parameter.__dict__, stream=self.fout, indent="1")
            else:
                pprint.pprint(parameter.__dict__, indent="1")
             
        print( "\n" )
             
        if self.fout:
            self.fout.write( "\n" )
        else:
            print ("\n")
            
    def __init__( self ):
        self.burp = False
        self.surround_value = ""
        self.replace_value = ""
        self.fout = None

########NEW FILE########
__FILENAME__ = Parameter
#!/usr/bin/env python

class Parameter(object):
    
    def __init__(self, tn ):
        self.typename = tn
        self.values = []
        self.flag = False
        self.is_custom_obj = False
        self.is_list = False
        self.is_array = False
        
    def _add_value(self, val):
        values.append( val )
    
    def _set_flag(self, flag_value ):
        self.flag = flag_value

    def __repr__(self):
        return "<Parameter %r>" % self.__dict__ 
########NEW FILE########
