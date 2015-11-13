__FILENAME__ = mozilla_ev_oids
# Generated using extract_mozilla_ev_oids.py 
MOZILLA_EV_OIDS = ['2.16.840.1.114171.500.9', '1.2.392.200091.100.721.1', '1.3.6.1.4.1.6334.1.100.1', '2.16.756.1.89.1.2.1.1', '1.3.6.1.4.1.23223.2', '2.16.840.1.113733.1.7.23.6', '1.3.6.1.4.1.14370.1.6', '2.16.840.1.113733.1.7.48.1', '2.16.840.1.114404.1.1.2.4.1', '2.16.840.1.114404.1.1.2.4.1', '2.16.840.1.114404.1.1.2.4.1', '1.3.6.1.4.1.6449.1.2.1.5.1', '1.3.6.1.4.1.6449.1.2.1.5.1', '1.3.6.1.4.1.6449.1.2.1.5.1', '1.3.6.1.4.1.6449.1.2.1.5.1', '1.3.6.1.4.1.6449.1.2.1.5.1', '2.16.840.1.114413.1.7.23.3', '2.16.840.1.114413.1.7.23.3', '2.16.840.1.114413.1.7.23.3', '2.16.840.1.114414.1.7.23.3', '2.16.840.1.114414.1.7.23.3', '2.16.840.1.114414.1.7.23.3', '2.16.840.1.114412.2.1', '1.3.6.1.4.1.8024.0.2.100.1.2', '1.3.6.1.4.1.782.1.2.1.8.1', '2.16.840.1.114028.10.1.2', '1.3.6.1.4.1.4146.1.1', '1.3.6.1.4.1.4146.1.1', '1.3.6.1.4.1.4146.1.1', '2.16.578.1.26.1.3.3', '1.3.6.1.4.1.22234.2.5.2.3.1', '1.3.6.1.4.1.17326.10.14.2.1.2', '1.3.6.1.4.1.17326.10.8.12.1.2', '1.2.276.0.44.1.1.1.4', '1.3.6.1.4.1.34697.2.1', '1.3.6.1.4.1.34697.2.2', '1.3.6.1.4.1.34697.2.3', '1.3.6.1.4.1.34697.2.4', '1.2.616.1.113527.2.5.1.1', '1.3.6.1.4.1.14777.6.1.1', '1.3.6.1.4.1.14777.6.1.2', '1.2.40.0.17.1.22', '0.0.0.0']

########NEW FILE########
__FILENAME__ = PluginBase
#!/usr/bin/env python
#-------------------------------------------------------------------------------
# Name:         PluginBase.py
# Purpose:      Main abstract plugin class. All the plugins are
#               subclasses of PluginBase.
#
# Author:       aaron, alban
#
# Copyright:    2012 SSLyze developers
#
#   SSLyze is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 2 of the License, or
#   (at your option) any later version.
#
#   SSLyze is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with SSLyze.  If not, see <http://www.gnu.org/licenses/>.
#-------------------------------------------------------------------------------

import abc
from optparse import make_option

class PluginInterface:
    """
    This object tells SSLyze what the plugin does: its title, description, and
    which command line option(s) it implements.
    Every plugin should have a class attribute called interface that is an
    instance of PluginInterface.
    """

    def __init__(self, title, description):
        """
        Title and description are sent to optparse.OptionGroup().
        """
        self.title = title
        self.description = description
        self._options = []
        self._commands = []
        self._commands_as_text = []

    def add_option(self, option, help, dest=None):
        """
        Options are settings specific to one single plugin.
        They are sent to PluginBase._shared_settings.
        """

        self._options.append(self._make_option(option, help, dest))


    def add_command(self, command, help, dest=None, aggressive=False):
        """
        Commands are actions/scans the plugin implements, with
        PluginXXX.process_task().
        Note: dest to None if you don't need arguments.
        Setting aggressive to True means that the command will open
        many simultaneous connections to the server and should therefore
        not be run concurrently with other `aggressive` commands against
        a given server.
        """

        self._commands.append(self._make_option(command, help, dest))
        self._commands_as_text.append((command, aggressive))


    def get_commands(self):
        return self._commands


    def get_commands_as_text(self):
        return self._commands_as_text


    def get_options(self):
        return self._options


    @staticmethod
    def _make_option(command, help, dest):
        # If dest is something, store it, otherwise just use store_true
        action="store_true"
        if dest is not None:
            action="store"

        return make_option('--' + command, action=action, help=help, dest=dest)


class PluginResult:
    """
    Plugin.process_task() should return an instance of this class.
    """
    def __init__(self, text_result, xml_result):
        """
        @type text_result: [str]
        @param text_result: Printable version of the plugin's results.
        Each string within the list gets printed as a separate line.

        @type xml_result: xml.etree.ElementTree.Element
        @param xml_result: XML version of the plugin's results.
        """
        self._text_result = text_result
        self._xml_result = xml_result

    def get_xml_result(self):
        return self._xml_result

    def get_txt_result(self):
        return self._text_result



class PluginBase(object):
    """
    Base plugin abstract class. All plugins have to inherit from it.
    """
    __metaclass__ = abc.ABCMeta

    # _shared_settings contains read-only info available to all the plugins:
    # client certificate, timeoutvalue, etc...
    # TODO: Document it
    _shared_settings = None

    # Formatting stuff
    PLUGIN_TITLE_FORMAT = '  * {0}:'.format


    @classmethod
    def get_interface(plugin_class):
        """
        This method returns the AvailableCommands object for the current plugin.
        """
        return plugin_class.interface

    @abc.abstractmethod
    def process_task(self, target, command, args):
        """
        This method should implement what the plugin is expected to do / test
        when given a target=(host, ip_addr, port), a command line option, and
        a command line argument. It has to be defined in each plugin class.
        """
        return


########NEW FILE########
__FILENAME__ = PluginCertInfo
#!/usr/bin/env python
#-------------------------------------------------------------------------------
# Name:         PluginCertInfo.py
# Purpose:      Verifies the target server's certificate validity against
#               Mozilla's trusted root store, and prints relevant fields of the
#               certificate.
#
# Author:       aaron, alban
#
# Copyright:    2012 SSLyze developers
#
#   SSLyze is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 2 of the License, or
#   (at your option) any later version.
#
#   SSLyze is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with SSLyze.  If not, see <http://www.gnu.org/licenses/>.
#-------------------------------------------------------------------------------

from os.path import join, dirname
import imp
from xml.etree.ElementTree import Element

from plugins import PluginBase
from utils.ThreadPool import ThreadPool
from utils.SSLyzeSSLConnection import create_sslyze_connection
from nassl import X509_NAME_MISMATCH, X509_NAME_MATCHES_SAN, X509_NAME_MATCHES_CN
from nassl.SslClient import ClientCertificateRequested


TRUST_STORES_PATH = join(join(dirname(PluginBase.__file__), 'data'), 'trust_stores')

# We use the Mozilla store for additional things: OCSP and EV validation
MOZILLA_STORE_PATH = join(TRUST_STORES_PATH, 'mozilla.pem')

AVAILABLE_TRUST_STORES = \
    { MOZILLA_STORE_PATH :                       'Mozilla NSS - 01/2014',
      join(TRUST_STORES_PATH, 'microsoft.pem') : 'Microsoft - 04/2014',
      join(TRUST_STORES_PATH, 'apple.pem') :     'Apple - OS X 10.9.2',
      join(TRUST_STORES_PATH, 'java.pem') :      'Java 6 - Update 65'}


# Import Mozilla EV OIDs
MOZILLA_EV_OIDS = imp.load_source('mozilla_ev_oids',
                                  join(TRUST_STORES_PATH,  'mozilla_ev_oids.py')).MOZILLA_EV_OIDS



class PluginCertInfo(PluginBase.PluginBase):

    interface = PluginBase.PluginInterface(title="PluginCertInfo", description=(''))
    interface.add_command(
        command="certinfo",
        help= "Verifies the validity of the server(s) certificate(s) against "
            "various trust stores, checks for support for OCSP stapling, and "
            "prints relevant fields of "
            "the certificate. CERTINFO should be 'basic' or 'full'.",
        dest="certinfo")

    FIELD_FORMAT = '      {0:<35}{1}'.format
    TRUST_FORMAT = '\"{0}\" CA Store:'.format


    def process_task(self, target, command, arg):

        if arg == 'basic':
            textFunction  = self._get_basic_text
        elif arg == 'full':
            textFunction = self._get_full_text
        else:
            raise Exception("PluginCertInfo: Unknown command.")

        (host, _, _, _) = target
        threadPool = ThreadPool()

        for (storePath, _) in AVAILABLE_TRUST_STORES.iteritems():
            # Try to connect with each trust store
            threadPool.add_job((self._get_cert, (target, storePath)))

        # Start processing the jobs
        threadPool.start(len(AVAILABLE_TRUST_STORES))

        # Store the results as they come
        (verifyDict, verifyDictErr, x509Cert, ocspResp)  = ({}, {}, None, None)

        for (job, result) in threadPool.get_result():
            (_, (_, storePath)) = job
            (x509Cert, verifyStr, ocspResp) = result
            # Store the returned verify string for each trust store
            storeName = AVAILABLE_TRUST_STORES[storePath]
            verifyDict[storeName] = verifyStr

        if x509Cert is None:
            # This means none of the connections were successful. Get out
            for (job, exception) in threadPool.get_error():
                raise exception

        # Store thread pool errors
        for (job, exception) in threadPool.get_error():
            (_, (_, storePath)) = job
            errorMsg = str(exception.__class__.__name__) + ' - ' \
                        + str(exception)

            storeName = AVAILABLE_TRUST_STORES[storePath]
            verifyDictErr[storeName] = errorMsg

        threadPool.join()


        # Results formatting
        # Text output - certificate info
        outputTxt = [self.PLUGIN_TITLE_FORMAT('Certificate - Content')]
        outputTxt.extend(textFunction(x509Cert))


        # Text output - trust validation
        outputTxt.extend(['', self.PLUGIN_TITLE_FORMAT('Certificate - Trust')])

        # Hostname validation
        if self._shared_settings['sni']:
            outputTxt.append(self.FIELD_FORMAT("SNI enabled with virtual domain:",
                                               self._shared_settings['sni']))
        # TODO: Use SNI name for validation when --sni was used
        hostValDict = {
            X509_NAME_MATCHES_SAN : 'OK - Subject Alternative Name matches',
            X509_NAME_MATCHES_CN :  'OK - Common Name matches',
            X509_NAME_MISMATCH :    'FAILED - Certificate does NOT match ' + host
        }
        outputTxt.append(self.FIELD_FORMAT("Hostname Validation:",
                                            hostValDict[x509Cert.matches_hostname(host)]))

        # Path validation that was successful
        for (storeName, verifyStr) in verifyDict.iteritems():
            verifyTxt = 'OK - Certificate is trusted' if (verifyStr in 'ok') else 'FAILED - Certificate is NOT Trusted: ' + verifyStr

            # EV certs - Only Mozilla supported for now
            if (verifyStr in 'ok') and ('Mozilla' in storeName):
                if (self._is_ev_certificate(x509Cert)):
                    verifyTxt += ', Extended Validation'
            outputTxt.append(self.FIELD_FORMAT(self.TRUST_FORMAT(storeName), verifyTxt))


        # Path validation that ran into errors
        for (storeName, errorMsg) in verifyDictErr.iteritems():
            verifyTxt = 'ERROR: ' + errorMsg
            outputTxt.append(self.FIELD_FORMAT(self.TRUST_FORMAT(storeName), verifyTxt))


        # Text output - OCSP stapling
        outputTxt.extend(['', self.PLUGIN_TITLE_FORMAT('Certificate - OCSP Stapling')])
        outputTxt.extend(self._get_ocsp_text(ocspResp))


        # XML output
        outputXml = Element(command, argument = arg, title = 'Certificate Information')

        # XML output - certificate info:  always return the full certificate
        certAttrib = { 'sha1Fingerprint' : x509Cert.get_SHA1_fingerprint() }
        if self._shared_settings['sni']:
            certAttrib['suppliedServerNameIndication'] = self._shared_settings['sni']

        certXml = Element('certificate', attrib = certAttrib)

        # Add certificate in PEM format
        PEMcertXml = Element('asPEM')
        PEMcertXml.text = x509Cert.as_pem().strip()
        certXml.append(PEMcertXml)

        for (key, value) in x509Cert.as_dict().items():
            certXml.append(_keyvalue_pair_to_xml(key, value))

        outputXml.append(certXml)


        # XML output - trust
        trustXml = Element('certificateValidation')

        # Hostname validation
        hostValBool = 'False' if (x509Cert.matches_hostname(host) == X509_NAME_MISMATCH) \
                              else 'True'
        hostXml = Element('hostnameValidation', serverHostname = host,
                           certificateMatchesServerHostname = hostValBool)
        trustXml.append(hostXml)

        # Path validation - OK
        for (storeName, verifyStr) in verifyDict.iteritems():
            pathXmlAttrib = { 'usingTrustStore' : storeName,
                              'validationResult' : verifyStr}

            # EV certs - Only Mozilla supported for now
            if (verifyStr in 'ok') and ('Mozilla' in storeName):
                    pathXmlAttrib['isExtendedValidationCertificate'] = str(self._is_ev_certificate(x509Cert))

            trustXml.append(Element('pathValidation', attrib = pathXmlAttrib))

        # Path validation - Errors
        for (storeName, errorMsg) in verifyDictErr.iteritems():
            pathXmlAttrib = { 'usingTrustStore' : storeName,
                              'error' : errorMsg}

            trustXml.append(Element('pathValidation', attrib = pathXmlAttrib))


        outputXml.append(trustXml)


        # XML output - OCSP Stapling
        if ocspResp is None:
            oscpAttr =  {'error' : 'Server did not send back an OCSP response'}
            ocspXml = Element('ocspStapling', attrib = oscpAttr)
        else:
            oscpAttr =  {'isTrustedByMozillaCAStore' : str(ocspResp.verify(MOZILLA_STORE_PATH))}
            ocspXml = Element('ocspResponse', attrib = oscpAttr)

            for (key, value) in ocspResp.as_dict().items():
                ocspXml.append(_keyvalue_pair_to_xml(key,value))

        outputXml.append(ocspXml)

        return PluginBase.PluginResult(outputTxt, outputXml)


# FORMATTING FUNCTIONS

    def _get_ocsp_text(self, ocspResp):

        if ocspResp is None:
            return [self.FIELD_FORMAT('Not supported: server did not send back an OCSP response.', '')]

        ocspRespDict = ocspResp.as_dict()
        ocspRespTrustTxt = 'Response is Trusted' if ocspResp.verify(MOZILLA_STORE_PATH) \
            else 'Response is NOT Trusted'

        ocspRespTxt = [
            self.FIELD_FORMAT('OCSP Response Status:', ocspRespDict['responseStatus']),
            self.FIELD_FORMAT('Validation w/ Mozilla\'s CA Store:', ocspRespTrustTxt),
            self.FIELD_FORMAT('Responder Id:', ocspRespDict['responderID'])]

        if 'successful' not in ocspRespDict['responseStatus']:
            return ocspRespTxt

        ocspRespTxt.extend( [
            self.FIELD_FORMAT('Cert Status:', ocspRespDict['responses'][0]['certStatus']),
            self.FIELD_FORMAT('Cert Serial Number:', ocspRespDict['responses'][0]['certID']['serialNumber']),
            self.FIELD_FORMAT('This Update:', ocspRespDict['responses'][0]['thisUpdate']),
            self.FIELD_FORMAT('Next Update:', ocspRespDict['responses'][0]['nextUpdate'])])

        return ocspRespTxt


    @staticmethod
    def _is_ev_certificate(cert):
        certDict = cert.as_dict()
        try:
            policy = certDict['extensions']['X509v3 Certificate Policies']['Policy']
            if policy[0] in MOZILLA_EV_OIDS:
                return True
        except:
            return False
        return False


    @staticmethod
    def _get_full_text(cert):
        return [cert.as_text()]


    def _get_basic_text(self, cert):
        certDict = cert.as_dict()

        try: # Extract the CN if there's one
            commonName = certDict['subject']['commonName']
        except KeyError:
            commonName = 'None'

        basicTxt = [
            self.FIELD_FORMAT("SHA1 Fingerprint:", cert.get_SHA1_fingerprint()),
            self.FIELD_FORMAT("Common Name:", commonName),
            self.FIELD_FORMAT("Issuer:", certDict['issuer']),
            self.FIELD_FORMAT("Serial Number:", certDict['serialNumber']),
            self.FIELD_FORMAT("Not Before:", certDict['validity']['notBefore']),
            self.FIELD_FORMAT("Not After:", certDict['validity']['notAfter']),
            self.FIELD_FORMAT("Signature Algorithm:", certDict['signatureAlgorithm']),
            self.FIELD_FORMAT("Key Size:", certDict['subjectPublicKeyInfo']['publicKeySize']),
            self.FIELD_FORMAT("Exponent:", "{0} (0x{0:x})".format(int(certDict['subjectPublicKeyInfo']['publicKey']['exponent'])))]

        try: # Print the SAN extension if there's one
            basicTxt.append(self.FIELD_FORMAT('X509v3 Subject Alternative Name:',
                                              certDict['extensions']['X509v3 Subject Alternative Name']))
        except KeyError:
            pass

        return basicTxt


    def _get_cert(self, target, storePath):
        """
        Connects to the target server and uses the supplied trust store to
        validate the server's certificate. Returns the server's certificate and
        OCSP response.
        """
        (_, _, _, sslVersion) = target
        sslConn = create_sslyze_connection(target, self._shared_settings,
                                           sslVersion,
                                           sslVerifyLocations=storePath)

        # Enable OCSP stapling
        sslConn.set_tlsext_status_ocsp()

        try: # Perform the SSL handshake
            sslConn.connect()

            ocspResp = sslConn.get_tlsext_status_ocsp_resp()
            x509Cert = sslConn.get_peer_certificate()
            (_, verifyStr) = sslConn.get_certificate_chain_verify_result()

        except ClientCertificateRequested: # The server asked for a client cert
            # We can get the server cert anyway
            ocspResp = sslConn.get_tlsext_status_ocsp_resp()
            x509Cert = sslConn.get_peer_certificate()
            (_, verifyStr) = sslConn.get_certificate_chain_verify_result()

        finally:
            sslConn.close()

        return (x509Cert, verifyStr, ocspResp)


# XML generation
def _create_xml_node(key, value=''):
    key = key.replace(' ', '').strip() # Remove spaces
    key = key.replace('/', '').strip() # Remove slashes (S/MIME Capabilities)

    # Things that would generate invalid XML
    if key[0].isdigit(): # Tags cannot start with a digit
            key = 'oid-' + key

    xml_node = Element(key)
    xml_node.text = value.decode( "utf-8" ).strip()
    return xml_node


def _keyvalue_pair_to_xml(key, value=''):

    if type(value) is str: # value is a string
        key_xml = _create_xml_node(key, value)

    elif type(value) is int:
        key_xml = _create_xml_node(key, str(value))

    elif value is None: # no value
        key_xml = _create_xml_node(key)

    elif type(value) is list:
        key_xml = _create_xml_node(key)
        for val in value:
            key_xml.append(_keyvalue_pair_to_xml('listEntry', val))

    elif type(value) is dict: # value is a list of subnodes
        key_xml = _create_xml_node(key)
        for subkey in value.keys():
            key_xml.append(_keyvalue_pair_to_xml(subkey, value[subkey]))
    else:
        raise Exception()

    return key_xml


########NEW FILE########
__FILENAME__ = PluginCompression
#!/usr/bin/env python
#-------------------------------------------------------------------------------
# Name:         PluginCompression.py
# Purpose:      Tests the server for Zlib compression support.
#
# Author:       tritter, alban
#
# Copyright:    2012 SSLyze developers
#
#   SSLyze is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 2 of the License, or
#   (at your option) any later version.
#
#   SSLyze is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with SSLyze.  If not, see <http://www.gnu.org/licenses/>.
#-------------------------------------------------------------------------------

from xml.etree.ElementTree import Element


from plugins import PluginBase

from utils.SSLyzeSSLConnection import create_sslyze_connection
from nassl.SslClient import ClientCertificateRequested


class PluginCompression(PluginBase.PluginBase):

    interface = PluginBase.PluginInterface(title="PluginCompression", description="")
    interface.add_command(
        command="compression",
        help="Tests the server(s) for Zlib compression support.")


    def process_task(self, target, command, args):

        OUT_FORMAT = '      {0:<35}{1}'.format

        sslConn = create_sslyze_connection(target, self._shared_settings)

        # Make sure OpenSSL was built with support for compression to avoid false negatives
        if 'zlib compression' not in sslConn.get_available_compression_methods():
            raise RuntimeError('OpenSSL was not built with support for zlib / compression. Did you build nassl yourself ?')

        try: # Perform the SSL handshake
            sslConn.connect()
            compName = sslConn.get_current_compression_method()
        except ClientCertificateRequested: # The server asked for a client cert
            compName = sslConn.get_current_compression_method()
        finally:
            sslConn.close()

        # Text output
        if compName:
            compTxt = 'Supported'
        else:
            compTxt = 'Disabled'

        cmdTitle = 'Compression'
        txtOutput = [self.PLUGIN_TITLE_FORMAT(cmdTitle)]
        txtOutput.append(OUT_FORMAT("DEFLATE Compression:", compTxt))

        # XML output
        xmlOutput = Element(command, title=cmdTitle)
        if compName:
            xmlNode = Element('compressionMethod', type="DEFLATE")
            xmlOutput.append(xmlNode)

        return PluginBase.PluginResult(txtOutput, xmlOutput)


########NEW FILE########
__FILENAME__ = PluginHeartbleed
#!/usr/bin/env python
#-------------------------------------------------------------------------------
# Name:         PluginHeartbleed.py
# Purpose:      Tests the target server for CVE-2014-0160.
#
# Author:       alban
#
# Copyright:    2014 SSLyze developers
#
#   SSLyze is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 2 of the License, or
#   (at your option) any later version.
#
#   SSLyze is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with SSLyze.  If not, see <http://www.gnu.org/licenses/>.
#-------------------------------------------------------------------------------

import socket, new
from xml.etree.ElementTree import Element

from plugins import PluginBase
from utils.SSLyzeSSLConnection import create_sslyze_connection, SSLHandshakeRejected
from nassl._nassl import OpenSSLError, WantX509LookupError, WantReadError
from nassl import TLSV1, TLSV1_1, TLSV1_2, SSLV23, SSLV3


class PluginHeartbleed(PluginBase.PluginBase):

    interface = PluginBase.PluginInterface("PluginHeartbleed",  "")
    interface.add_command(
        command="heartbleed",
        help=(
            "Tests the server(s) for the OpenSSL Heartbleed vulnerability (experimental)."))


    def process_task(self, target, command, args):

        OUT_FORMAT = '      {0:<35}{1}'.format
        (host, ip, port, sslVersion) = target

        if sslVersion == SSLV23: # Could not determine the preferred  SSL version - client cert was required ?
            sslVersion = TLSV1 # Default to TLS 1.0
            target = (host, ip, port, sslVersion)

        sslConn = create_sslyze_connection(target, self._shared_settings)
        sslConn.sslVersion = sslVersion # Needed by the heartbleed payload

        # Awful hack #1: replace nassl.sslClient.do_handshake() with a heartbleed
        # checking SSL handshake so that all the SSLyze options
        # (startTLS, proxy, etc.) still work
        sslConn.do_handshake = new.instancemethod(do_handshake_with_heartbleed, sslConn, None)

        heartbleed = None
        try: # Perform the SSL handshake
            sslConn.connect()
        except HeartbleedSent:
            # Awful hack #2: directly read the underlying network socket
            heartbleed = sslConn._sock.recv(16381)
        finally:
            sslConn.close()

        # Text output
        if heartbleed is None:
            raise Exception("Error: connection failed.")
        elif '\x01\x01\x01\x01\x01\x01\x01\x01\x01' in heartbleed:
            # Server replied with our hearbeat payload
            heartbleedTxt = 'VULNERABLE'
            heartbleedXml = 'True'
        else:
            heartbleedTxt = 'NOT vulnerable'
            heartbleedXml = 'False'

        cmdTitle = 'Heartbleed'
        txtOutput = [self.PLUGIN_TITLE_FORMAT(cmdTitle)]
        txtOutput.append(OUT_FORMAT("OpenSSL Heartbleed:", heartbleedTxt))

        # XML output
        xmlOutput = Element(command, title=cmdTitle)
        if heartbleed:
            xmlNode = Element('heartbleed', isVulnerable=heartbleedXml)
            xmlOutput.append(xmlNode)

        return PluginBase.PluginResult(txtOutput, xmlOutput)




def heartbleed_payload(sslVersion):
    # This heartbleed payload does not exploit the server
    # https://blog.mozilla.org/security/2014/04/12/testing-for-heartbleed-vulnerability-without-exploiting-the-server/

    SSL_VERSION_MAPPING = {
        SSLV3 :  '\x00', # Surprising that it works with SSL 3 which doesn't define TLS extensions
        TLSV1 :  '\x01',
        TLSV1_1: '\x02',
        TLSV1_2: '\x03'}

    payload = ('\x18'           # Record type - Heartbeat
        '\x03{0}'               # TLS version
        '\x00\x03'              # Record length
        '\x01'                  # Heartbeat type - Request
        '\x00\x00')             # Heartbeat length

    payload = ('\x18'           # Record type - Heartbeat
        '\x03{0}'               # TLS version
        '\x40\x00'              # Record length
        '\x01'                  # Heartbeat type - Request
        '\x3f\xfd')             # Heartbeat length

    payload += '\x01'*16381     # Heartbeat data

    payload += (                # Second Heartbeat request with no padding
        '\x18'                  # Record type - Heartbeat
        '\x03{0}'
        '\x00\x03\x01\x00\x00'
    )

    return payload.format(SSL_VERSION_MAPPING[sslVersion])


class HeartbleedSent(SSLHandshakeRejected):
    # Awful hack #3: Use an exception to hack the handshake's control flow in
    # a super obscure way
    pass


def do_handshake_with_heartbleed(self):
    # This is nassl's code for do_handshake() modified to send a heartbleed
    # payload that will send the heartbleed checking payload
    # I copied nassl's code here so I could leave anything heartbleed-related
    # outside of the nassl code base
    try:
        if self._ssl.do_handshake() == 1:
            self._handshakeDone = True
            return True # Handshake was successful

    except WantReadError:
        # OpenSSL is expecting more data from the peer
        # Send available handshake data to the peer
        # In this heartbleed handshake we only send the client hello
        lenToRead = self._networkBio.pending()
        while lenToRead:
            # Get the data from the SSL engine
            handshakeDataOut = self._networkBio.read(lenToRead)
            # Send it to the peer
            self._sock.send(handshakeDataOut)
            lenToRead = self._networkBio.pending()

        # Send the heartbleed payload after the client hello
        self._sock.send(heartbleed_payload(self.sslVersion))

        # Recover the peer's encrypted response
        # In this heartbleed handshake we only receive the server hello
        handshakeDataIn = self._sock.recv(2048)
        if len(handshakeDataIn) == 0:
            raise IOError('Nassl SSL handshake failed: peer did not send data back.')
        # Pass the data to the SSL engine
        self._networkBio.write(handshakeDataIn)

        # Signal that we sent the heartbleed payload and just stop the handshake
        raise HeartbleedSent("")


    except WantX509LookupError:
        # Server asked for a client certificate and we didn't provide one
        # Heartbleed should work anyway
        self._sock.send(heartbleed_payload(self.sslVersion)) # The heartbleed payload
        raise HeartbleedSent("") # Signal that we sent the heartbleed payload


########NEW FILE########
__FILENAME__ = PluginHSTS
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:         PluginHSTS.py
# Purpose:      Checks if the server supports RFC 6797 HTTP Strict Transport
#               Security by checking if the server responds with the
#               Strict-Transport-Security field in the header.
#
#               Note: There is currently no support for hsts pinning.
#
#               This plugin is based on the plugin written by Tom Samstag
#               (tecknicaltom) and reworked, integrated and adapted to the
#               new sslyze plugin API by Joachim Strömbergson.
#
# Author:       tecknicaltom, joachims, alban
#
# Copyright:    2013 SSLyze developers
#
#   SSLyze is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 2 of the License, or
#   (at your option) any later version.
#
#   SSLyze is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with SSLyze.  If not, see <http://www.gnu.org/licenses/>.
#-------------------------------------------------------------------------------

from xml.etree.ElementTree import Element
from utils.HTTPResponseParser import parse_http_response
from utils.SSLyzeSSLConnection import create_sslyze_connection
from plugins import PluginBase
from urlparse import urlparse
import Cookie


class PluginHSTS(PluginBase.PluginBase):

    interface = PluginBase.PluginInterface(title="PluginHSTS", description=(''))
    interface.add_command(
        command="hsts",
        help="Checks support for HTTP Strict Transport Security "
             "(HSTS) by collecting any Strict-Transport-Security field present in "
             "the HTTP response sent back by the server(s).",
        dest=None)


    def process_task(self, target, command, args):


        if self._shared_settings['starttls']:
            raise Exception('Cannot use --hsts with --starttls.')

        FIELD_FORMAT = '      {0:<35}{1}'.format

        hsts_supported = self._get_hsts_header(target)
        if hsts_supported:
            hsts_timeout = hsts_supported
            hsts_supported = True

        # Text output
        cmd_title = 'HTTP Strict Transport Security'
        txt_result = [self.PLUGIN_TITLE_FORMAT(cmd_title)]
        if hsts_supported:
            txt_result.append(FIELD_FORMAT("Supported:", hsts_timeout))
        else:
            txt_result.append(FIELD_FORMAT("Not supported: server did not send an HSTS header.", ""))

        # XML output
        xml_hsts_attr = {'sentHstsHeader': str(hsts_supported)}
        if hsts_supported:
            xml_hsts_attr['hstsHeaderValue'] = hsts_timeout
        xml_hsts = Element('hsts', attrib = xml_hsts_attr)

        xml_result = Element('hsts', title = cmd_title)
        xml_result.append(xml_hsts)

        return PluginBase.PluginResult(txt_result, xml_result)



    def _get_hsts_header(self, target):

        hstsHeader = None
        MAX_REDIRECT = 5
        nb_redirect = 0
        httpGetFormat = 'GET {0} HTTP/1.0\r\nHost: {1}\r\n{2}Connection: close\r\n\r\n'.format
        httpPath = '/'
        httpAppend = ''    
        
        while nb_redirect < MAX_REDIRECT:
            sslConn = create_sslyze_connection(target, self._shared_settings)
            
            # Perform the SSL handshake
            sslConn.connect()
            
            sslConn.write(httpGetFormat(httpPath, target[0], httpAppend))
            httpResp = parse_http_response(sslConn.read(2048))
            sslConn.close()
            
            if httpResp.version == 9 :
                # HTTP 0.9 => Probably not an HTTP response
                raise Exception('Server did not return an HTTP response')
            elif 300 <= httpResp.status < 400:
                redirectHeader = httpResp.getheader('Location', None)
                cookieHeader = httpResp.getheader('Set-Cookie', None)
                
                if redirectHeader is None:
                    break
                
                o = urlparse(redirectHeader)
                httpPath = o.path
                
                # Handle absolute redirection URL
                if o.hostname:
                    if o.port:
                        port = o.port
                    else:
                        if o.scheme == 'https':
                            port = 443
                        elif o.scheme == 'http':
                            # We would have to use urllib for http: URLs
                            raise Exception("Error: server sent a redirection to HTTP.")
                        else:
                            port = target[2]
                        
                    target = (o.hostname, o.hostname, port, target[3])
                
                # Handle cookies
                if cookieHeader:
                    cookie = Cookie.SimpleCookie(cookieHeader)
                    
                    if cookie:
                        httpAppend = 'Cookie:' + cookie.output(attrs=[], header='', sep=';') + '\r\n'
                
                nb_redirect+=1
            else:
                hstsHeader = httpResp.getheader('strict-transport-security', None)
                break
        
        return hstsHeader



########NEW FILE########
__FILENAME__ = PluginOpenSSLCipherSuites
#!/usr/bin/env python
#-------------------------------------------------------------------------------
# Name:         PluginOpenSSLCipherSuites.py
# Purpose:      Scans the target server for supported OpenSSL cipher suites.
#
# Author:       alban
#
# Copyright:    2012 SSLyze developers
#
#   SSLyze is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 2 of the License, or
#   (at your option) any later version.
#
#   SSLyze is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with SSLyze.  If not, see <http://www.gnu.org/licenses/>.
#-------------------------------------------------------------------------------

from xml.etree.ElementTree import Element

from plugins import PluginBase
from utils.ThreadPool import ThreadPool
from utils.SSLyzeSSLConnection import create_sslyze_connection, SSLHandshakeRejected
from nassl import SSLV2, SSLV3, TLSV1, TLSV1_1, TLSV1_2
from nassl.SslClient import SslClient


class PluginOpenSSLCipherSuites(PluginBase.PluginBase):


    interface = PluginBase.PluginInterface(
        "PluginOpenSSLCipherSuites",
        "Scans the server(s) for supported OpenSSL cipher suites.")
    interface.add_command(
        command="sslv2",
        help="Lists the SSL 2.0 OpenSSL cipher suites supported by the server(s).",
        aggressive=False)
    interface.add_command(
        command="sslv3",
        help="Lists the SSL 3.0 OpenSSL cipher suites supported by the server(s).",
        aggressive=True)
    interface.add_command(
        command="tlsv1",
        help="Lists the TLS 1.0 OpenSSL cipher suites supported by the server(s).",
        aggressive=True)
    interface.add_command(
        command="tlsv1_1",
        help="Lists the TLS 1.1 OpenSSL cipher suites supported by the server(s).",
        aggressive=True)
    interface.add_command(
        command="tlsv1_2",
        help="Lists the TLS 1.2 OpenSSL cipher suites supported by the server(s).",
        aggressive=True)
    interface.add_option(
        option='http_get',
        help="Option - For each cipher suite, sends an HTTP GET request after "
        "completing the SSL handshake and returns the HTTP status code.")
    interface.add_option(
        option='hide_rejected_ciphers',
        help="Option - Hides the (usually long) list of cipher suites that were"
        " rejected by the server(s).")


    def process_task(self, target, command, args):

        MAX_THREADS = 15
        sslVersionDict = {'sslv2': SSLV2,
                       'sslv3': SSLV3,
                       'tlsv1': TLSV1,
                       'tlsv1_1': TLSV1_1,
                       'tlsv1_2': TLSV1_2}
        try:
            sslVersion = sslVersionDict[command]
        except KeyError:
            raise Exception("PluginOpenSSLCipherSuites: Unknown command.")

        # Get the list of available cipher suites for the given ssl version
        sslClient = SslClient(sslVersion=sslVersion)
        sslClient.set_cipher_list('ALL:COMPLEMENTOFALL')
        cipher_list = sslClient.get_cipher_list()

        # Create a thread pool
        NB_THREADS = min(len(cipher_list), MAX_THREADS) # One thread per cipher
        thread_pool = ThreadPool()

        # Scan for every available cipher suite
        for cipher in cipher_list:
            thread_pool.add_job((self._test_ciphersuite,
                                 (target, sslVersion, cipher)))

        # Scan for the preferred cipher suite
        thread_pool.add_job((self._pref_ciphersuite,
                             (target, sslVersion)))

        # Start processing the jobs
        thread_pool.start(NB_THREADS)

        result_dicts = {'preferredCipherSuite':{}, 'acceptedCipherSuites':{},
                        'rejectedCipherSuites':{}, 'errors':{}}

        # Store the results as they come
        for completed_job in thread_pool.get_result():
            (job, result) = completed_job
            if result is not None:
                (result_type, ssl_cipher, keysize, msg) = result
                (result_dicts[result_type])[ssl_cipher] = (msg, keysize)

        # Store thread pool errors
        for failed_job in thread_pool.get_error():
            (job, exception) = failed_job
            ssl_cipher = str(job[1][2])
            error_msg = str(exception.__class__.__name__) + ' - ' + str(exception)
            result_dicts['errors'][ssl_cipher] = (error_msg, None)

        thread_pool.join()

        # Generate results
        return PluginBase.PluginResult(self._generate_text_output(result_dicts, command),
                                       self._generate_xml_output(result_dicts, command))


# == INTERNAL FUNCTIONS ==

# FORMATTING FUNCTIONS
    def _generate_text_output(self, resultDicts, sslVersion):

        cipherFormat = '                 {0:<32}{1:<35}'.format
        titleFormat =  '      {0:<32} '.format
        keysizeFormat = '{0:<30}{1:<14}'.format

        txtTitle = self.PLUGIN_TITLE_FORMAT(sslVersion.upper() + ' Cipher Suites')
        txtOutput = []

        dictTitles = [('preferredCipherSuite', 'Preferred:'),
                      ('acceptedCipherSuites', 'Accepted:'),
                      ('errors', 'Undefined - An unexpected error happened:'),
                      ('rejectedCipherSuites', 'Rejected:')]

        if self._shared_settings['hide_rejected_ciphers']:
            dictTitles.pop(3)
            #txtOutput.append('')
            #txtOutput.append(titleFormat('Rejected:  Hidden'))

        for (resultKey, resultTitle) in dictTitles:

            # Sort the cipher suites by results
            result_list = sorted(resultDicts[resultKey].iteritems(),
                                 key=lambda (k,v): (v,k), reverse=True)

            # Add a new line and title
            if len(resultDicts[resultKey]) == 0: # No ciphers
                pass # Hide empty results
                # txtOutput.append(titleFormat(resultTitle + ' None'))
            else:
                #txtOutput.append('')
                txtOutput.append(titleFormat(resultTitle))

                # Add one line for each ciphers
                for (cipherTxt, (msg, keysize)) in result_list:
                    if keysize:
                        # Display ANON as the key size for anonymous ciphers
                        if 'ADH' in cipherTxt or 'AECDH' in cipherTxt:
                            keysize = 'ANON'
                        else:
                            keysize = str(keysize) + ' bits'
                        cipherTxt = keysizeFormat(cipherTxt, keysize)

                    txtOutput.append(cipherFormat(cipherTxt, msg))
        if txtOutput == []:
            # Server rejected all cipher suites
            txtOutput = [txtTitle, '      Server rejected all cipher suites.']
        else:
            txtOutput = [txtTitle] + txtOutput


        return txtOutput


    @staticmethod
    def _generate_xml_output(result_dicts, command):

        xmlOutput = Element(command, title=command.upper() + ' Cipher Suites')

        for (resultKey, resultDict) in result_dicts.items():
            xmlNode = Element(resultKey)

            # Sort the cipher suites by name to make the XML diff-able
            resultList = sorted(resultDict.items(),
                                 key=lambda (k,v): (k,v), reverse=False)

            # Add one element for each ciphers
            for (sslCipher, (msg, keysize)) in resultList:
                cipherXmlAttr = {'name' : sslCipher, 'connectionStatus' : msg}

                if keysize:
                    cipherXmlAttr['keySize'] = str(keysize)

                # Add an Anonymous attribute for anonymous ciphers
                cipherXmlAttr['anonymous'] = str(True) if 'ADH' in sslCipher or 'AECDH' in sslCipher else str(False)
                cipherXml = Element('cipherSuite', attrib = cipherXmlAttr)

                xmlNode.append(cipherXml)

            xmlOutput.append(xmlNode)

        return xmlOutput


# SSL FUNCTIONS
    def _test_ciphersuite(self, target, ssl_version, ssl_cipher):
        """
        Initiates a SSL handshake with the server, using the SSL version and
        cipher suite specified.
        """
        sslConn = create_sslyze_connection(target, self._shared_settings, ssl_version)
        sslConn.set_cipher_list(ssl_cipher)

        try: # Perform the SSL handshake
            sslConn.connect()

        except SSLHandshakeRejected as e:
            return 'rejectedCipherSuites', ssl_cipher, None, str(e)

        except:
            raise

        else:
            ssl_cipher = sslConn.get_current_cipher_name()
            keysize = sslConn.get_current_cipher_bits()
            status_msg = sslConn.post_handshake_check()
            return 'acceptedCipherSuites', ssl_cipher, keysize, status_msg

        finally:
            sslConn.close()


    def _pref_ciphersuite(self, target, ssl_version):
        """
        Initiates a SSL handshake with the server, using the SSL version and cipher
        suite specified.
        """
        sslConn = create_sslyze_connection(target, self._shared_settings, ssl_version)

        try: # Perform the SSL handshake
            sslConn.connect()
            ssl_cipher = sslConn.get_current_cipher_name()
            keysize = sslConn.get_current_cipher_bits()
            status_msg = sslConn.post_handshake_check()
            return 'preferredCipherSuite', ssl_cipher, keysize, status_msg

        except:
            return None

        finally:
            sslConn.close()


########NEW FILE########
__FILENAME__ = PluginSessionRenegotiation
#!/usr/bin/env python
#-------------------------------------------------------------------------------
# Name:         PluginSessionRenegotiation.py
# Purpose:      Tests the target server for insecure renegotiation.
#
# Author:       alban
#
# Copyright:    2012 SSLyze developers
#
#   SSLyze is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 2 of the License, or
#   (at your option) any later version.
#
#   SSLyze is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with SSLyze.  If not, see <http://www.gnu.org/licenses/>.
#-------------------------------------------------------------------------------

import socket
from xml.etree.ElementTree import Element

from plugins import PluginBase
from utils.SSLyzeSSLConnection import create_sslyze_connection
from nassl._nassl import OpenSSLError


class PluginSessionRenegotiation(PluginBase.PluginBase):

    interface = PluginBase.PluginInterface("PluginSessionRenegotiation",  "")
    interface.add_command(
        command="reneg",
        help=(
            "Tests the server(s) for client-initiated "
            'renegotiation and secure renegotiation support.'))


    def process_task(self, target, command, args):

        (clientReneg, secureReneg) = self._test_renegotiation(target)

        # Text output
        clientTxt = 'Honored' if clientReneg else 'Rejected'
        secureTxt = 'Supported' if secureReneg else 'Not supported'
        cmdTitle = 'Session Renegotiation'
        txtOutput = [self.PLUGIN_TITLE_FORMAT(cmdTitle)]

        outFormat = '      {0:<35}{1}'.format
        txtOutput.append(outFormat('Client-initiated Renegotiations:', clientTxt))
        txtOutput.append(outFormat('Secure Renegotiation:', secureTxt))

        # XML output
        xmlReneg = Element('sessionRenegotiation',
                           attrib = {'canBeClientInitiated' : str(clientReneg),
                                     'isSecure' : str(secureReneg)})

        xmlOutput = Element(command, title=cmdTitle)
        xmlOutput.append(xmlReneg)

        return PluginBase.PluginResult(txtOutput, xmlOutput)


    def _test_renegotiation(self, target):
        """
        Checks whether the server honors session renegotiation requests and
        whether it supports secure renegotiation.
        """
        sslConn = create_sslyze_connection(target, self._shared_settings)

        try: # Perform the SSL handshake
            sslConn.connect()
            secureReneg = sslConn.get_secure_renegotiation_support()

            try: # Let's try to renegotiate
                sslConn.do_renegotiate()
                clientReneg = True

            # Errors caused by a server rejecting the renegotiation
            except socket.error as e:
                if 'connection was forcibly closed' in str(e.args):
                    clientReneg = False
                elif 'reset by peer' in str(e.args):
                    clientReneg = False
                else:
                    raise
            #except socket.timeout as e:
            #    result_reneg = 'Rejected (timeout)'
            except OpenSSLError as e:
                if 'handshake failure' in str(e.args):
                    clientReneg = False
                elif 'no renegotiation' in str(e.args):
                    clientReneg = False
                else:
                    raise

            # Should be last as socket errors are also IOError
            except IOError as e:
                if 'Nassl SSL handshake failed' in str(e.args):
                    clientReneg = False
                else:
                    raise

        finally:
            sslConn.close()

        return (clientReneg, secureReneg)

########NEW FILE########
__FILENAME__ = PluginSessionResumption
#!/usr/bin/env python
#-------------------------------------------------------------------------------
# Name:         PluginSessionResumption.py
# Purpose:      Analyzes the server's SSL session resumption capabilities.
#
# Author:       alban
#
# Copyright:    2012 SSLyze developers
#
#   SSLyze is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 2 of the License, or
#   (at your option) any later version.
#
#   SSLyze is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with SSLyze.  If not, see <http://www.gnu.org/licenses/>.
#-------------------------------------------------------------------------------
from xml.etree.ElementTree import Element

from plugins import PluginBase
from utils.ThreadPool import ThreadPool

from nassl import SSL_OP_NO_TICKET
from utils.SSLyzeSSLConnection import create_sslyze_connection


class PluginSessionResumption(PluginBase.PluginBase):

    interface = PluginBase.PluginInterface(
        title="PluginSessionResumption",
        description=(
            "Analyzes the target server's SSL session "
            "resumption capabilities."))
    interface.add_command(
        command="resum",
        help=(
            "Tests the server(s) for session ressumption support using "
            "session IDs and TLS session tickets (RFC 5077)."))
    interface.add_command(
        command="resum_rate",
        help=(
            "Performs 100 session resumptions with the server(s), "
            "in order to estimate the session resumption rate."),
        aggressive=True)


    def process_task(self, target, command, args):

        if command == 'resum':
            result = self._command_resum(target)
        elif command == 'resum_rate':
            result = self._command_resum_rate(target)
        else:
            raise Exception("PluginSessionResumption: Unknown command.")

        return result


    def _command_resum_rate(self, target):
        """
        Performs 100 session resumptions with the server in order to estimate
        the session resumption rate.
        """
        # Create a thread pool and process the jobs
        NB_THREADS = 20
        MAX_RESUM = 100
        thread_pool = ThreadPool()
        for _ in xrange(MAX_RESUM):
            thread_pool.add_job((self._resume_with_session_id, (target, )))
        thread_pool.start(NB_THREADS)

        # Format session ID results
        (txt_resum, xml_resum) = self._format_resum_id_results(thread_pool, MAX_RESUM)

        # Text output
        cmd_title = 'Resumption Rate with Session IDs'
        txt_result = [self.PLUGIN_TITLE_FORMAT(cmd_title)+' '+ txt_resum[0]]
        txt_result.extend(txt_resum[1:])

        # XML output
        xml_result = Element('resum_rate', title = cmd_title)
        xml_result.append(xml_resum)

        thread_pool.join()
        return PluginBase.PluginResult(txt_result, xml_result)


    def _command_resum(self, target):
        """
        Tests the server for session resumption support using session IDs and
        TLS session tickets (RFC 5077).
        """
        NB_THREADS = 5
        MAX_RESUM = 5
        thread_pool = ThreadPool()

        for _ in xrange(MAX_RESUM): # Test 5 resumptions with session IDs
            thread_pool.add_job((self._resume_with_session_id,
                                 (target,), 'session_id'))
        thread_pool.start(NB_THREADS)

        # Test TLS tickets support while threads are running
        try:
            (ticket_supported, ticket_reason) = self._resume_with_session_ticket(target)
            ticket_error = None
        except Exception as e:
            ticket_error = str(e.__class__.__name__) + ' - ' + str(e)

        # Format session ID results
        (txt_resum, xml_resum) = self._format_resum_id_results(thread_pool, MAX_RESUM)

        if ticket_error:
            ticket_txt = 'ERROR: ' + ticket_error
        else:
            ticket_txt = 'Supported' if ticket_supported \
                                     else 'Not Supported - ' + ticket_reason+'.'

        cmd_title = 'Session Resumption'
        txt_result = [self.PLUGIN_TITLE_FORMAT(cmd_title)]
        RESUM_FORMAT = '      {0:<35}{1}'.format

        txt_result.append(RESUM_FORMAT('With Session IDs:', txt_resum[0]))
        txt_result.extend(txt_resum[1:])
        txt_result.append(RESUM_FORMAT('With TLS Session Tickets:', ticket_txt))

        # XML output
        xml_resum_ticket_attr = {}
        if ticket_error:
            xml_resum_ticket_attr['error'] = ticket_error
        else:
            xml_resum_ticket_attr['isSupported'] = str(ticket_supported)
            if not ticket_supported:
                xml_resum_ticket_attr['reason'] = ticket_reason

        xml_resum_ticket = Element('sessionResumptionWithTLSTickets', attrib = xml_resum_ticket_attr)
        xml_result = Element('resum', title=cmd_title)
        xml_result.append(xml_resum)
        xml_result.append(xml_resum_ticket)

        thread_pool.join()
        return PluginBase.PluginResult(txt_result, xml_result)


    @staticmethod
    def _format_resum_id_results(thread_pool, MAX_RESUM):
        # Count successful/failed resumptions
        nb_resum = 0
        for completed_job in thread_pool.get_result():
            (job, (is_supported, reason_str)) = completed_job
            if is_supported:
                nb_resum += 1

        # Count errors and store error messages
        error_list = []
        for failed_job in thread_pool.get_error():
            (job, exception) = failed_job
            error_msg = str(exception.__class__.__name__) + ' - ' + str(exception)
            error_list.append(error_msg)
        nb_error = len(error_list)

        nb_failed = MAX_RESUM - nb_error - nb_resum

        # Text output
        SESSID_FORMAT = '{4} ({0} successful, {1} failed, {2} errors, {3} total attempts).{5}'.format
        sessid_try = ''
        if nb_resum == MAX_RESUM:
            sessid_stat = 'Supported'
        elif nb_failed == MAX_RESUM:
            sessid_stat = 'Not supported'
        elif nb_error == MAX_RESUM:
            sessid_stat = 'ERROR'
        else:
            sessid_stat = 'Partially supported'
            sessid_try = ' Try --resum_rate.'
        sessid_txt = SESSID_FORMAT(str(nb_resum), str(nb_failed), str(nb_error),
                                   str(MAX_RESUM), sessid_stat, sessid_try)

        ERRORS_FORMAT ='        ERROR #{0}: {1}'.format
        txt_result = [sessid_txt]
        # Add error messages
        if error_list:
            i=0
            for error_msg in error_list:
                i+=1
                txt_result.append(ERRORS_FORMAT(str(i), error_msg))

        # XML output
        sessid_xml = str(nb_resum == MAX_RESUM)
        xml_resum_id_attr = {'totalAttempts':str(MAX_RESUM),
                             'errors' : str(nb_error), 'isSupported' : sessid_xml,
                             'successfulAttempts':str(nb_resum),'failedAttempts':str(nb_failed)}
        xml_resum_id = Element('sessionResumptionWithSessionIDs', attrib = xml_resum_id_attr)
        # Add errors
        if error_list:
            for error_msg in error_list:
                xml_resum_error = Element('error')
                xml_resum_error.text = error_msg
                xml_resum_id.append(xml_resum_error)

        return txt_result, xml_resum_id


    def _resume_with_session_id(self, target):
        """
        Performs one session resumption using Session IDs.
        """

        session1 = self._resume_ssl_session(target)
        try: # Recover the session ID
            session1_id = self._extract_session_id(session1)
        except IndexError:
            return False, 'Session ID not assigned'

        # Try to resume that SSL session
        session2 = self._resume_ssl_session(target, session1)
        try: # Recover the session ID
            session2_id = self._extract_session_id(session2)
        except IndexError:
            return False, 'Session ID not assigned'

        # Finally, compare the two Session IDs
        if session1_id != session2_id:
            return False, 'Session ID assigned but not accepted'

        return True, ''


    def _resume_with_session_ticket(self, target):
        """
        Performs one session resumption using TLS Session Tickets.
        """

        # Connect to the server and keep the SSL session
        session1 = self._resume_ssl_session(target, tlsTicket=True)
        try: # Recover the TLS ticket
            session1_tls_ticket = self._extract_tls_session_ticket(session1)
        except IndexError:
            return False, 'TLS ticket not assigned'

        # Try to resume that session using the TLS ticket
        session2 = self._resume_ssl_session(target, session1, tlsTicket=True)
        try: # Recover the TLS ticket
            session2_tls_ticket = self._extract_tls_session_ticket(session2)
        except IndexError:
            return False, 'TLS ticket not assigned'

        # Finally, compare the two TLS Tickets
        if session1_tls_ticket != session2_tls_ticket:
            return False, 'TLS ticket assigned but not accepted'

        return True, ''


    @staticmethod
    def _extract_session_id(ssl_session):
        """
        Extracts the SSL session ID from a SSL session object or raises IndexError
        if the session ID was not set.
        """
        session_string = ( (ssl_session.as_text()).split("Session-ID:") )[1]
        session_id = ( session_string.split("Session-ID-ctx:") )[0]
        return session_id


    @staticmethod
    def _extract_tls_session_ticket(ssl_session):
        """
        Extracts the TLS session ticket from a SSL session object or raises
        IndexError if the ticket was not set.
        """
        session_string = ( (ssl_session.as_text()).split("TLS session ticket:") )[1]
        session_tls_ticket = ( session_string.split("Compression:") )[0]
        return session_tls_ticket


    def _resume_ssl_session(self, target, sslSession=None, tlsTicket=False):
        """
        Connect to the server and returns the session object that was assigned
        for that connection.
        If ssl_session is given, tries to resume that session.
        """
        sslConn = create_sslyze_connection(target, self._shared_settings)
        if not tlsTicket:
        # Need to disable TLS tickets to test session IDs, according to rfc5077:
        # If a ticket is presented by the client, the server MUST NOT attempt
        # to use the Session ID in the ClientHello for stateful session resumption
            sslConn.set_options(SSL_OP_NO_TICKET) # Turning off TLS tickets.

        if sslSession:
            sslConn.set_session(sslSession)

        try: # Perform the SSL handshake
            sslConn.connect()
            newSession = sslConn.get_session() # Get session data
        finally:
            sslConn.close()

        return newSession

########NEW FILE########
__FILENAME__ = sslyze
#!/usr/bin/env python
#-------------------------------------------------------------------------------
# Name:         sslyze.py
# Purpose:      Main module of SSLyze.
#
# Author:       aaron, alban
#
# Copyright:    2012 SSLyze developers
#
#   SSLyze is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 2 of the License, or
#   (at your option) any later version.
#
#   SSLyze is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with SSLyze.  If not, see <http://www.gnu.org/licenses/>.
#-------------------------------------------------------------------------------

from time import time
from itertools import cycle
from multiprocessing import Process, JoinableQueue
from xml.etree.ElementTree import Element, tostring
from xml.dom import minidom
import sys

from plugins import PluginsFinder

try:
    from utils.CommandLineParser import CommandLineParser, CommandLineParsingError
    from utils.ServersConnectivityTester import ServersConnectivityTester
except ImportError:
    print '\nERROR: Could not import nassl Python module. Did you clone SSLyze\'s repo ? \n' +\
    'Please download the right pre-compiled package as described in the README.'
    sys.exit()


PROJECT_VERSION = 'SSLyze v1.0 dev'
PROJECT_URL = "https://github.com/isecPartners/sslyze"
PROJECT_EMAIL = 'sslyze@isecpartners.com'
PROJECT_DESC = 'Fast and full-featured SSL scanner'

MAX_PROCESSES = 12
MIN_PROCESSES = 3


# Todo: Move formatting stuff to another file
SCAN_FORMAT = 'Scan Results For {0}:{1} - {2}:{1}'


class WorkerProcess(Process):

    def __init__(self, priority_queue_in, queue_in, queue_out, available_commands, shared_settings):
        Process.__init__(self)
        self.priority_queue_in = priority_queue_in
        self.queue_in = queue_in
        self.queue_out = queue_out
        self.available_commands = available_commands
        self.shared_settings = shared_settings

    def run(self):
        """
        The process will first complete tasks it gets from self.queue_in.
        Once it gets notified that all the tasks have been completed,
        it terminates.
        """
        from plugins.PluginBase import PluginResult
        # Plugin classes are unpickled by the multiprocessing module
        # without state info. Need to assign shared_settings here
        for plugin_class in self.available_commands.itervalues():
            plugin_class._shared_settings = self.shared_settings

        # Start processing task in the priority queue first
        current_queue_in = self.priority_queue_in
        while True:

            task = current_queue_in.get() # Grab a task from queue_in
            if task is None: # All tasks have been completed
                current_queue_in.task_done()

                if (current_queue_in == self.priority_queue_in):
                    # All high priority tasks have been completed
                    current_queue_in = self.queue_in # Switch to low priority tasks
                    continue
                else:
                    # All the tasks have been completed
                    self.queue_out.put(None) # Pass on the sentinel to result_queue and exit
                    break

            (target, command, args) = task
            # Instantiate the proper plugin
            plugin_instance = self.available_commands[command]()

            try: # Process the task
                result = plugin_instance.process_task(target, command, args)
            except Exception as e: # Generate txt and xml results
                #raise
                txt_result = ['Unhandled exception when processing --' +
                              command + ': ', str(e.__class__.__module__) +
                              '.' + str(e.__class__.__name__) + ' - ' + str(e)]
                xml_result = Element(command, exception=txt_result[1])
                result = PluginResult(txt_result, xml_result)

            # Send the result to queue_out
            self.queue_out.put((target, command, result))
            current_queue_in.task_done()

        return


def _format_title(title):
    return ' ' + title.upper()+ '\n' + ' ' + ('-' * len(title))


def _format_xml_target_result(target, result_list):
    (host, ip, port, sslVersion) = target
    target_xml = Element('target', host=host, ip=ip, port=str(port))
    result_list.sort(key=lambda result: result[0]) # Sort results

    for (command, plugin_result) in result_list:
        target_xml.append(plugin_result.get_xml_result())

    return target_xml


def _format_txt_target_result(target, result_list):
    (host, ip, port, sslVersion) = target
    target_result_str = ''

    for (command, plugin_result) in result_list:
        # Print the result of each separate command
        target_result_str += '\n'
        for line in plugin_result.get_txt_result():
            target_result_str += line + '\n'

    scan_txt = SCAN_FORMAT.format(host, str(port), ip)
    return _format_title(scan_txt) + '\n' + target_result_str + '\n\n'


def main():

    #--PLUGINS INITIALIZATION--
    start_time = time()
    print '\n\n\n' + _format_title('Registering available plugins')
    sslyze_plugins = PluginsFinder()
    available_plugins = sslyze_plugins.get_plugins()
    available_commands = sslyze_plugins.get_commands()
    print ''
    for plugin in available_plugins:
        print '  ' + plugin.__name__
    print '\n\n'

    # Create the command line parser and the list of available options
    sslyze_parser = CommandLineParser(available_plugins, PROJECT_VERSION)

    try: # Parse the command line
        (command_list, target_list, shared_settings) = sslyze_parser.parse_command_line()
    except CommandLineParsingError as e:
        print e.get_error_msg()
        return


    #--PROCESSES INITIALIZATION--
    # Three processes per target from MIN_PROCESSES up to MAX_PROCESSES
    nb_processes = max(MIN_PROCESSES, min(MAX_PROCESSES, len(target_list)*3))
    if command_list.https_tunnel:
        nb_processes = 1 # Let's not kill the proxy

    task_queue = JoinableQueue() # Processes get tasks from task_queue and
    result_queue = JoinableQueue() # put the result of each task in result_queue

    # Spawn a pool of processes, and pass them the queues
    process_list = []
    for _ in xrange(nb_processes):
        priority_queue = JoinableQueue() # Each process gets a priority queue
        p = WorkerProcess(priority_queue, task_queue, result_queue, available_commands, \
                          shared_settings)
        p.start()
        process_list.append((p, priority_queue)) # Keep track of each process and priority_queue


    #--TESTING SECTION--
    # Figure out which hosts are up and fill the task queue with work to do
    print _format_title('Checking host(s) availability')


    targets_OK = []
    targets_ERR = []

    # Each server gets assigned a priority queue for aggressive commands
    # so that they're never run in parallel against this single server
    cycle_priority_queues = cycle(process_list)
    target_results = ServersConnectivityTester.test_server_list(target_list,
                                                                shared_settings)
    for target in target_results:
        if target is None:
            break # None is a sentinel here

        # Send tasks to worker processes
        targets_OK.append(target)
        (_, current_priority_queue) = cycle_priority_queues.next()

        for command in available_commands:
            if getattr(command_list, command):
                args = command_list.__dict__[command]

                if command in sslyze_plugins.get_aggressive_commands():
                    # Aggressive commands should not be run in parallel against
                    # a given server so we use the priority queues to prevent this
                    current_priority_queue.put( (target, command, args) )
                else:
                    # Normal commands get put in the standard/shared queue
                    task_queue.put( (target, command, args) )

    for exception in target_results:
        targets_ERR.append(exception)

    print ServersConnectivityTester.get_printable_result(targets_OK, targets_ERR)
    print '\n\n'

    # Put a 'None' sentinel in the queue to let the each process know when every
    # task has been completed
    for (proc, priority_queue) in process_list:
        task_queue.put(None) # One sentinel in the task_queue per proc
        priority_queue.put(None) # One sentinel in each priority_queue

    # Keep track of how many tasks have to be performed for each target
    task_num=0
    for command in available_commands:
        if getattr(command_list, command):
            task_num+=1


    # --REPORTING SECTION--
    processes_running = nb_processes

    # XML output
    xml_output_list = []

    # Each host has a list of results
    result_dict = {}
    for target in targets_OK:
        result_dict[target] = []

    # If all processes have stopped, all the work is done
    while processes_running:
        result = result_queue.get()

        if result is None: # Getting None means that one process was done
            processes_running -= 1

        else: # Getting an actual result
            (target, command, plugin_result) = result
            result_dict[target].append((command, plugin_result))

            if len(result_dict[target]) == task_num: # Done with this target
                # Print the results and update the xml doc
                print _format_txt_target_result(target, result_dict[target])
                if shared_settings['xml_file']:
                    xml_output_list.append(_format_xml_target_result(target, result_dict[target]))

        result_queue.task_done()


    # --TERMINATE--

    # Make sure all the processes had time to terminate
    task_queue.join()
    result_queue.join()
    #[process.join() for process in process_list] # Causes interpreter shutdown errors
    exec_time = time()-start_time

    # Output XML doc to a file if needed
    if shared_settings['xml_file']:
        result_xml_attr = {'httpsTunnel':str(shared_settings['https_tunnel_host']),
                           'totalScanTime' : str(exec_time),
                           'defaultTimeout' : str(shared_settings['timeout']),
                           'startTLS' : str(shared_settings['starttls'])}

        result_xml = Element('results', attrib = result_xml_attr)

        # Sort results in alphabetical order to make the XML files (somewhat) diff-able
        xml_output_list.sort(key=lambda xml_elem: xml_elem.attrib['host'])
        for xml_element in xml_output_list:
            result_xml.append(xml_element)

        xml_final_doc = Element('document', title = "SSLyze Scan Results",
                                SSLyzeVersion = PROJECT_VERSION,
                                SSLyzeWeb = PROJECT_URL)
        # Add the list of invalid targets
        xml_final_doc.append(ServersConnectivityTester.get_xml_result(targets_ERR))
        # Add the output of the plugins
        xml_final_doc.append(result_xml)

        # Hack: Prettify the XML file so it's (somewhat) diff-able
        xml_final_pretty = minidom.parseString(tostring(xml_final_doc, encoding='UTF-8'))
        with open(shared_settings['xml_file'],'w') as xml_file:
            xml_file.write(xml_final_pretty.toprettyxml(indent="  ", encoding="utf-8" ))


    print _format_title('Scan Completed in {0:.2f} s'.format(exec_time))


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = CommandLineParser
#!/usr/bin/env python
#-------------------------------------------------------------------------------
# Name:         CommandLineParser.py
# Purpose:      Command line parsing utilities for SSLyze.
#
# Author:       aaron, alban
#
# Copyright:    2012 SSLyze developers
#
#   SSLyze is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 2 of the License, or
#   (at your option) any later version.
#
#   SSLyze is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with SSLyze.  If not, see <http://www.gnu.org/licenses/>.
#-------------------------------------------------------------------------------

from optparse import OptionParser, OptionGroup
from urlparse import urlparse

# Client cert/key checking
from nassl.SslClient import SslClient
from nassl import _nassl, SSL_FILETYPE_ASN1, SSL_FILETYPE_PEM


class CommandLineParsingError(Exception):

    PARSING_ERROR_FORMAT = '  Command line error: {0}\n  Use -h for help.'

    def get_error_msg(self):
        return self.PARSING_ERROR_FORMAT.format(self)


class CommandLineParser():

    # Defines what --regular means
    REGULAR_CMD = ['sslv2', 'sslv3', 'tlsv1', 'tlsv1_1', 'tlsv1_2', 'reneg',
                   'resum', 'certinfo', 'http_get', 'hide_rejected_ciphers',
                   'compression', 'heartbleed']
    SSLYZE_USAGE = 'usage: %prog [options] target1.com target2.com:443 etc...'

    # StartTLS options
    START_TLS_PROTS = ['smtp', 'xmpp', 'pop3', 'ftp', 'imap', 'ldap', 'rdp', 'auto']
    START_TLS_USAGE = 'STARTTLS should be one of: ' + str(START_TLS_PROTS) +  \
        '. The \'auto\' option will cause SSLyze to deduce the protocol' + \
        ' (ftp, imap, etc.) from the supplied port number, for each target servers.'

    # Default values
    DEFAULT_RETRY_ATTEMPTS = 4
    DEFAULT_TIMEOUT = 5


    def __init__(self, available_plugins, sslyze_version):
        """
        Generates SSLyze's command line parser.
        """

        self._parser = OptionParser(version=sslyze_version,
                                    usage=self.SSLYZE_USAGE)

        # Add generic command line options to the parser
        self._add_default_options()

        # Add plugin-specific options to the parser
        self._add_plugin_options(available_plugins)

        # Add the --regular command line parameter as a shortcut if possible
        regular_help = 'Regular HTTPS scan; shortcut for'
        for cmd in self.REGULAR_CMD:
            regular_help += ' --' + cmd
            if cmd == 'certinfo': # gah
                regular_help += '=basic'

            if not self._parser.has_option('--' + cmd):
                return

        self._parser.add_option('--regular', action="store_true", dest=None,
                    help=regular_help)


    def parse_command_line(self):
        """
        Parses the command line used to launch SSLyze.
        """

        (args_command_list, args_target_list) = self._parser.parse_args()

        # Handle the --targets_in command line and fill args_target_list
        if args_command_list.targets_in:
            if args_target_list:
                raise CommandLineParsingError("Cannot use --targets_list and specify targets within the command line.")

            try: # Read targets from a file
                with open(args_command_list.targets_in) as f:
                    for target in f.readlines():
                        if target.strip(): # Ignore empty lines
                            if not target.startswith('#'): # Ignore comment lines
                                args_target_list.append(target.strip())
            except IOError:
                raise CommandLineParsingError("Can't read targets from input file '%s'." %  args_command_list.targets_in)

        if not args_target_list:
            raise CommandLineParsingError('No targets to scan.')

        # Handle the --regular command line parameter as a shortcut
        if self._parser.has_option('--regular'):
            if getattr(args_command_list, 'regular'):
                setattr(args_command_list, 'regular', False)
                for cmd in self.REGULAR_CMD:
                    setattr(args_command_list, cmd, True)
                setattr(args_command_list, 'certinfo', 'basic') # Special case

        # Create the shared_settings object from looking at the command line
        shared_settings = self._process_parsing_results(args_command_list)

        return args_command_list, args_target_list, shared_settings


    def _add_default_options(self):
        """
        Adds default command line options to the parser.
        """

        # Client certificate options
        clientcert_group = OptionGroup(self._parser,
            'Client certificate support', '')
        clientcert_group.add_option(
            '--cert',
            help='Client certificate filename.',
            dest='cert')
        clientcert_group.add_option(
            '--certform',
            help= 'Client certificate format. DER or PEM (default).',
            dest='certform',
            default='PEM')
        clientcert_group.add_option(
            '--key',
            help= 'Client private key filename.',
            dest='key')
        clientcert_group.add_option(
            '--keyform',
            help= 'Client private key format. DER or PEM (default).',
            dest='keyform',
            default='PEM')
        clientcert_group.add_option(
            '--pass',
            help= 'Client private key passphrase.',
            dest='keypass',
            default='')
        self._parser.add_option_group(clientcert_group)

        # XML output
        self._parser.add_option(
            '--xml_out',
            help='Writes the scan results as an XML document to the file XML_FILE.',
            dest='xml_file',
            default=None)

        # Read targets from input file
        self._parser.add_option(
            '--targets_in',
            help='Reads the list of targets to scan from the file TARGETS_IN. It should contain one host:port per line.',
            dest='targets_in',
            default=None)

        # Timeout
        self._parser.add_option(
            '--timeout',
            help= (
                'Sets the timeout value in seconds used for every socket '
                'connection made to the target server(s). Default is ' +
                str(self.DEFAULT_TIMEOUT) + 's.'),
            type='int',
            dest='timeout',
            default=self.DEFAULT_TIMEOUT)


        # Control connection retry attempts
        self._parser.add_option(
            '--nb_retries',
            help= (
                'Sets the number retry attempts for all network connections '
                'initiated throughout the scan. Increase this value if you are '
                'getting a lot of timeout/connection errors when scanning a '
                'specific server. Decrease this value to increase the speed '
                'of the scans; results may however return connection errors. '
                'Default is '
                + str(self.DEFAULT_RETRY_ATTEMPTS) + ' connection attempts.'),
            type='int',
            dest='nb_retries',
            default=self.DEFAULT_RETRY_ATTEMPTS)


        # HTTP CONNECT Proxy
        self._parser.add_option(
            '--https_tunnel',
            help= (
                'Tunnels all traffic to the target server(s) through an HTTP '
                'CONNECT proxy. HTTP_TUNNEL should be the proxy\'s URL: '
                '\'http://USER:PW@HOST:PORT/\'. For proxies requiring '
                'authentication, only Basic Authentication is supported.'),
            dest='https_tunnel',
            default=None)

        # STARTTLS
        self._parser.add_option(
            '--starttls',
            help= (
                'Performs StartTLS handshakes when connecting to the target '
                'server(s). ' + self.START_TLS_USAGE),
            dest='starttls',
            default=None)

        self._parser.add_option(
            '--xmpp_to',
            help= (
                'Optional setting for STARTTLS XMPP. '
                ' XMPP_TO should be the hostname to be put in the \'to\' attribute '
                'of the XMPP stream. Default is the server\'s hostname.'),
            dest='xmpp_to',
            default=None)

        # Server Name Indication
        self._parser.add_option(
            '--sni',
            help= (
                'Use Server Name Indication to specify the hostname to connect to.'
                ' Will only affect TLS 1.0+ connections.'),
            dest='sni',
            default=None)

    def _add_plugin_options(self, available_plugins):
        """
        Recovers the list of command line options implemented by the available
        plugins and adds them to the command line parser.
        """

        for plugin_class in available_plugins:
            plugin_desc = plugin_class.get_interface()

            # Add the current plugin's commands to the parser
            group = OptionGroup(self._parser, plugin_desc.title,
                                plugin_desc.description)
            for cmd in plugin_desc.get_commands():
                    group.add_option(cmd)

            # Add the current plugin's options to the parser
            for option in plugin_desc.get_options():
                    group.add_option(option)

            self._parser.add_option_group(group)


    def _process_parsing_results(self, args_command_list):
        """
        Performs various sanity checks on the command line that was used to
        launch SSLyze.
        Returns the shared_settings object to be fed to plugins.
        """

        shared_settings = {}
        # Sanity checks on the client cert options
        if bool(args_command_list.cert) ^ bool(args_command_list.key):
            raise CommandLineParsingError('No private key or certificate file were given. See --cert and --key.')

        # Private key and cert formats
        if args_command_list.certform == 'DER':
            args_command_list.certform = SSL_FILETYPE_ASN1
        elif args_command_list.certform == 'PEM':
            args_command_list.certform = SSL_FILETYPE_PEM
        else:
            raise CommandLineParsingError('--certform should be DER or PEM.')

        if args_command_list.keyform == 'DER':
            args_command_list.keyform = SSL_FILETYPE_ASN1
        elif args_command_list.keyform == 'PEM':
            args_command_list.keyform = SSL_FILETYPE_PEM
        else:
            raise CommandLineParsingError('--keyform should be DER or PEM.')

        # Let's try to open the cert and key files
        if args_command_list.cert:
            try:
                open(args_command_list.cert,"r")
            except:
                raise CommandLineParsingError('Could not open the client certificate file "' + str(args_command_list.cert) + '".')

        if args_command_list.key:
            try:
                open(args_command_list.key,"r")
            except:
                raise CommandLineParsingError('Could not open the client private key file "' + str(args_command_list.key) + '"')

            # Try to load the cert and key in OpenSSL
            try:
                sslClient = SslClient()
                sslClient.use_private_key(args_command_list.cert,
                                        args_command_list.certform,
                                        args_command_list.key,
                                        args_command_list.keyform,
                                        args_command_list.keypass)
            except _nassl.OpenSSLError as e:
                if 'bad decrypt' in str(e.args):
                    raise CommandLineParsingError('Could not decrypt the private key. Wrong passphrase ?')
                raise CommandLineParsingError('Could not load the certificate or the private key. Passphrase needed ?')



        # HTTP CONNECT proxy
        shared_settings['https_tunnel_host'] = None
        if args_command_list.https_tunnel:

            # Parse the proxy URL
            parsedUrl = urlparse(args_command_list.https_tunnel)

            if not parsedUrl.netloc:
                raise CommandLineParsingError(
                    'Invalid Proxy URL for --https_tunnel, discarding all tasks.')

            if parsedUrl.scheme in 'http':
               defaultPort = 80
            elif parsedUrl.scheme in 'https':
               defaultPort = 443
            else:
                raise CommandLineParsingError(
                    'Invalid URL scheme for --https_tunnel, discarding all tasks.')

            if not parsedUrl.hostname:
                raise CommandLineParsingError(
                    'Invalid Proxy URL for --https_tunnel, discarding all tasks.')

            try :
                shared_settings['https_tunnel_port'] = parsedUrl.port if parsedUrl.port else defaultPort
            except ValueError: # The supplied port was not a number
                raise CommandLineParsingError(
                    'Invalid Proxy URL for --https_tunnel, discarding all tasks.')

            shared_settings['https_tunnel_host'] = parsedUrl.hostname
            shared_settings['https_tunnel_user'] = parsedUrl.username
            shared_settings['https_tunnel_password'] = parsedUrl.password


        # STARTTLS
        if args_command_list.starttls:
            if args_command_list.starttls not in self.START_TLS_PROTS:
                raise CommandLineParsingError(self.START_TLS_USAGE)

        if args_command_list.starttls and args_command_list.https_tunnel:
            raise CommandLineParsingError(
                'Cannot have --https_tunnel and --starttls at the same time.')

        # Number of connection retries
        if args_command_list.nb_retries < 1:
            raise CommandLineParsingError(
                'Cannot have a number smaller than 1 for --nb_retries.')

        # All good, let's save the data
        for key, value in args_command_list.__dict__.iteritems():
            shared_settings[key] = value

        return shared_settings


########NEW FILE########
__FILENAME__ = HTTPResponseParser

# Utility to parse HTTP responses
# http://pythonwise.blogspot.com/2010/02/parse-http-response.html
from StringIO import StringIO
from httplib import HTTPResponse

class FakeSocket(StringIO):
    def makefile(self, *args, **kw):
        return self

def parse_http_response(fp):
    socket = FakeSocket(fp)
    response = HTTPResponse(socket)
    response.begin()

    return response


########NEW FILE########
__FILENAME__ = ServersConnectivityTester
#!/usr/bin/env python
#-------------------------------------------------------------------------------
# Name:         ServersConnectivityTester.py
# Purpose:      Initial checks to figure out which servers supplied by the
#               user are actually reachable.
#
# Author:       alban
#
# Copyright:    2013 SSLyze developers
#
#   SSLyze is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 2 of the License, or
#   (at your option) any later version.
#
#   SSLyze is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with SSLyze.  If not, see <http://www.gnu.org/licenses/>.
#-------------------------------------------------------------------------------

import socket
from xml.etree.ElementTree import Element
from ThreadPool import ThreadPool
from nassl import SSLV23, SSLV3, TLSV1, TLSV1_2
from SSLyzeSSLConnection import create_sslyze_connection, StartTLSError, ProxyError


class InvalidTargetError(Exception):

    RESULT_FORMAT = '\n   {0:<35} => WARNING: {1}; discarding corresponding tasks.'

    def __init__(self, target_str, error_msg):
        self._target_str = target_str
        self._error_msg = error_msg

    def get_error_txt(self):
        return self.RESULT_FORMAT.format(self._target_str, self._error_msg )

    def get_error_xml(self):
        errorXml = Element('invalidTarget', error = self._error_msg)
        errorXml.text = self._target_str
        return errorXml



class TargetStringParser(object):
    """Utility class to parse a 'host:port' string taken from the command line
    into a valid (host,port) tuple. Supports IPV6 addresses."""

    ERR_BAD_PORT = 'Not a valid host:port'
    ERR_NO_IPV6 = 'IPv6 is not supported on this platform'

    @classmethod
    def parse_target_str(cls, target_str, default_port):


        if '[' in target_str:
            return cls._parse_ipv6_target_str(target_str, default_port)
        else: # Fallback to ipv4
            return cls._parse_ipv4_target_str(target_str, default_port)


    @classmethod
    def _parse_ipv4_target_str(cls, target_str, default_port):

        if ':' in target_str:
            host = (target_str.split(':'))[0] # hostname or ipv4 address
            try:
                port = int((target_str.split(':'))[1])
            except: # Port is not an int
                raise InvalidTargetError(target_str, cls.ERR_BAD_PORT)
        else:
            host = target_str
            port = default_port

        return host, port

    @classmethod
    def _parse_ipv6_target_str(cls, target_str, default_port):

        if not socket.has_ipv6:
            raise InvalidTargetError(target_str, cls.ERR_NO_IPV6)

        port = default_port
        target_split = (target_str.split(']'))
        ipv6_addr = target_split[0].split('[')[1]
        if ':' in target_split[1]: # port was specified
            try:
                port = int(target_split[1].rsplit(':')[1])
            except: # Port is not an int
                raise InvalidTargetError(target_str, cls.ERR_BAD_PORT)
        return ipv6_addr, port



class ServersConnectivityTester(object):
    """Utility class to connect to a list of servers and return a list of
    online and offline servers."""

    HOST_FORMAT = '{0[0]}:{0[2]}'
    IP_FORMAT = '{0[1]}:{0[2]}'
    TARGET_OK_FORMAT = '\n   {0:<35} => {1}'

    MAX_THREADS = 50

    DEFAULT_PORTS = {'smtp'     : 25,
                     'xmpp'     : 5222,
                     'ftp'      : 21,
                     'pop3'     : 110,
                     'ldap'     : 389,
                     'imap'     : 143,
                     'rdp'      : 3389,
                     'default'  : 443}

    ERR_TIMEOUT = 'Could not connect (timeout)'
    ERR_NAME_NOT_RESOLVED = 'Could not resolve hostname'
    ERR_REJECTED = 'Connection rejected'

    @classmethod
    def test_server_list(cls, target_list, shared_settings):
        """
        Tests connectivity with each server of the target_list and returns
        the list of online servers.
        """

        # Use a thread pool to connect to each server
        thread_pool = ThreadPool()
        for target_str in target_list:
            thread_pool.add_job((cls._test_server, (target_str, shared_settings)))

        nb_threads = min(len(target_list), cls.MAX_THREADS)
        thread_pool.start(nb_threads)

        # Return valid targets
        for (job, target) in thread_pool.get_result():
            yield target

        # Use None as a sentinel
        yield None

        # Return invalid targets
        for (job, exception) in thread_pool.get_error():
            yield exception

        thread_pool.join()
        return


    @classmethod
    def get_printable_result(cls, targets_OK, targets_ERR):
        """
        Returns a text meant to be displayed to the user and presenting the
        results of the connectivity testing.
        """
        result_str = ''
        for target in targets_OK:
            result_str += cls.TARGET_OK_FORMAT.format(cls.HOST_FORMAT.format(target),
                                                       cls.IP_FORMAT.format(target))

        for exception in targets_ERR:
            result_str += exception.get_error_txt()

        return result_str


    @classmethod
    def get_xml_result(cls, targets_ERR):
        """
        Returns XML containing the list of every target that returned an error
        during the connectivity testing.
        """
        resultXml = Element('invalidTargets')
        for exception in targets_ERR:
            resultXml.append(exception.get_error_xml())

        return resultXml


    @classmethod
    def _test_server(cls, targetStr, shared_settings):
        """Test connectivity to one single server."""

        # Parse the target string
        try:
            defaultPort = cls.DEFAULT_PORTS[shared_settings['starttls']]
        except KeyError:
            defaultPort = cls.DEFAULT_PORTS['default']
        (host, port) = TargetStringParser.parse_target_str(targetStr, defaultPort)


        # First try to connect and do StartTLS if needed
        sslCon = create_sslyze_connection((host, host, port, SSLV23), shared_settings)
        try:
            sslCon.do_pre_handshake()
            ipAddr = sslCon._sock.getpeername()[0]

        # Socket errors
        except socket.timeout: # Host is down
            raise InvalidTargetError(targetStr, cls.ERR_TIMEOUT)
        except socket.gaierror:
            raise InvalidTargetError(targetStr, cls.ERR_NAME_NOT_RESOLVED)
        except socket.error: # Connection Refused
            raise InvalidTargetError(targetStr, cls.ERR_REJECTED)

        # StartTLS errors
        except StartTLSError as e:
            raise InvalidTargetError(targetStr, e[0])

        # Proxy errors
        except ProxyError as e:
            raise InvalidTargetError(targetStr, e[0])

        finally:
            sslCon.close()


        # Then try to do SSL handshakes just to figure out the SSL version
        # supported by the server; the plugins need to know this in advance.
        # If the handshakes fail, we keep going anyway; maybe the server
        # only supports exotic cipher suites
        sslSupport = SSLV23
        # No connection retry when testing connectivity
        tweak_shared_settings = shared_settings.copy()
        tweak_shared_settings['nb_retries'] = 1
        for sslVersion in [TLSV1, SSLV23, SSLV3, TLSV1_2]:
            sslCon = create_sslyze_connection((host, ipAddr, port, sslVersion),
                                              tweak_shared_settings)
            try:
                sslCon.connect()
            except:
                pass
            else:
                sslSupport = sslVersion
                break
            finally:
                sslCon.close()


        return host, ipAddr, port, sslSupport

########NEW FILE########
__FILENAME__ = SSLyzeSSLConnection
#!/usr/bin/env python
#-------------------------------------------------------------------------------
# Name:         SSLyzeSSLConnection.py
# Purpose:      The SSL connection class that all SSLyze Plugins should be
#               using. It takes care of creating the right connections based
#               on the command line arguments supplied by the user.
#
# Author:       alban
#
# Copyright:    2013 SSLyze developers
#
#   SSLyze is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 2 of the License, or
#   (at your option) any later version.
#
#   SSLyze is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with SSLyze.  If not, see <http://www.gnu.org/licenses/>.
#-------------------------------------------------------------------------------

from base64 import b64decode, b64encode
from urllib import quote, unquote

import socket, struct, time, random
from HTTPResponseParser import parse_http_response
from nassl import _nassl, SSL_VERIFY_NONE
from nassl.SslClient import SslClient, ClientCertificateRequested



def create_sslyze_connection(target, shared_settings, sslVersion=None, sslVerifyLocations=None):
    """
    Utility function to create the proper SSLConnection based on what's
    in the shared_settings. All plugins should use this for their SSL
    connections.
    """
    (host, ip, port, sslSupport) = target
    # Override SSL version if one was specified
    # Otherwise use the one supported by the server
    if sslVersion is not None:
        target = (host, ip, port, sslVersion)

    # Create the proper connection
    timeout = shared_settings['timeout']
    startTls = shared_settings['starttls']

    STARTTLS_DISPATCH = { 'smtp' :  SMTPConnection,
                          587 :     SMTPConnection,
                          25 :      SMTPConnection,
                          'xmpp':   XMPPConnection,
                          5222 :    XMPPConnection,
                          5269 :    XMPPConnection,
                          'pop3' :  POP3Connection,
                          109 :     POP3Connection,
                          110 :     POP3Connection,
                          'imap' :  IMAPConnection,
                          143 :     IMAPConnection,
                          220 :     IMAPConnection,
                          'ftp' :   FTPConnection,
                          21 :      FTPConnection,
                          'ldap' :  LDAPConnection,
                          3268 :    LDAPConnection,
                          389 :     LDAPConnection,
                          'rdp' :   RDPConnection,
                          3389 :    RDPConnection }

    if shared_settings['starttls']:

        if shared_settings['starttls'] in STARTTLS_DISPATCH.keys():
            # Protocol was given in the command line
            connectionClass = STARTTLS_DISPATCH[startTls]

        elif shared_settings['starttls'] == 'auto':
            # We use the port number to deduce the protocol
            if port in STARTTLS_DISPATCH.keys():
                connectionClass = STARTTLS_DISPATCH[port]
            else:
                connectionClass = SSLConnection

        # XMPP configuration
        if connectionClass == XMPPConnection:
            sslConn = connectionClass(target, sslVerifyLocations, timeout,
                                      shared_settings['nb_retries'],
                                      shared_settings['xmpp_to'])
        else:
            sslConn = connectionClass(target, sslVerifyLocations, timeout,
                                      shared_settings['nb_retries'])


    elif shared_settings['https_tunnel_host']:
        # Using an HTTP CONNECT proxy to tunnel SSL traffic
        if shared_settings['http_get']:
            sslConn = HTTPSTunnelConnection(target, sslVerifyLocations, timeout,
                                            shared_settings['nb_retries'],
                                            shared_settings['https_tunnel_host'],
                                            shared_settings['https_tunnel_port'],
                                            shared_settings['https_tunnel_user'],
                                            shared_settings['https_tunnel_password']
                                            )
        else:
            sslConn = SSLTunnelConnection(target, sslVerifyLocations, timeout,
                                          shared_settings['nb_retries'],
                                          shared_settings['https_tunnel_host'],
                                          shared_settings['https_tunnel_port'],
                                          shared_settings['https_tunnel_user'],
                                          shared_settings['https_tunnel_password']
                                          )

    elif shared_settings['http_get']:
        sslConn = HTTPSConnection(target, sslVerifyLocations, timeout,
                                  shared_settings['nb_retries'])
    else:
        sslConn = SSLConnection(target, sslVerifyLocations, timeout,
                                shared_settings['nb_retries'])


    # Load client certificate and private key
    # These parameters should have been validated when parsing the command line
    if shared_settings['cert']:
        sslConn.use_private_key(shared_settings['cert'], shared_settings['certform'],
            shared_settings['key'], shared_settings['keyform'], shared_settings['keypass'])

    # Add Server Name Indication
    if shared_settings['sni']:
        try:
            sslConn.set_tlsext_host_name(shared_settings['sni'])
        except ValueError:
            # This gets raised if we're using SSLv2 which doesn't support SNI (or TLS extensions in general)
            pass

    # Restrict cipher list to make the client hello smaller
    sslConn.set_cipher_list('HIGH:MEDIUM:-aNULL:-eNULL:-3DES:-SRP:-PSK:-CAMELLIA')

    return sslConn



class SSLHandshakeRejected(IOError):
    """
    The server explicitly rejected the SSL handshake.
    """
    pass



class StartTLSError(IOError):
    """
    The server rejected the StartTLS negotiation.
    """
    pass



class ProxyError(IOError):
    """
    The proxy was offline or did not return HTTP 200 to our CONNECT request.
    """
    pass



class SSLConnection(SslClient):
    """Base SSL connection class."""

    # The following errors mean that the server explicitly rejected the
    # handshake. The goal to differentiate rejected handshakes from random
    # network errors such as the server going offline, etc.
    HANDSHAKE_REJECTED_SOCKET_ERRORS = \
        {'was forcibly closed' : 'Received FIN',
         'reset by peer' : 'Received RST'}

    HANDSHAKE_REJECTED_SSL_ERRORS = \
        {'sslv3 alert handshake failure' : 'Alert handshake failure',
         'no ciphers available' : 'No ciphers available',
         'excessive message size' : 'Excessive message size',
         'bad mac decode' : 'Bad mac decode',
         'wrong version number' : 'Wrong version number',
         'no cipher match' : 'No cipher match',
         'bad decompression' : 'Bad decompression',
         'peer error no cipher' : 'Peer error no cipher',
         'no cipher list' : 'No ciphers list',
         'insufficient security' : 'Insufficient security',
         'block type is not 01' : 'block type is not 01'} # Actually an RSA error


    def __init__(self, (host, ip, port, sslVersion), sslVerifyLocations,
                 timeout, maxAttempts):
        super(SSLConnection, self).__init__(None, sslVersion, SSL_VERIFY_NONE,
                                            sslVerifyLocations)
        self._timeout = timeout
        self._sock = None
        self._host = host
        self._ip = ip
        self._port = port
        self._maxAttempts = maxAttempts


    def do_pre_handshake(self):
        # Just a TCP connection
        self._sock = socket.create_connection((self._ip, self._port), self._timeout)


    def connect(self):

        retryAttempts = 0
        delay = 0
        while True:
            try:
                # Sleep if it's a retry attempt
                time.sleep(delay)

                # StartTLS negotiation or proxy setup if needed
                self.do_pre_handshake()

                try: # SSL handshake
                    self.do_handshake()

                # The goal here to differentiate rejected SSL handshakes (which will
                # raise SSLHandshakeRejected) from random network errors
                except socket.error as e:
                    for error_msg in self.HANDSHAKE_REJECTED_SOCKET_ERRORS.keys():
                        if error_msg in str(e.args):
                            raise SSLHandshakeRejected('TCP / ' + self.HANDSHAKE_REJECTED_SOCKET_ERRORS[error_msg])
                    raise # Unknown socket error
                except IOError as e:
                    if 'Nassl SSL handshake failed' in str(e.args):
                        raise SSLHandshakeRejected('TLS / Unexpected EOF')
                    raise
                except _nassl.OpenSSLError as e:
                    for error_msg in self.HANDSHAKE_REJECTED_SSL_ERRORS.keys():
                        if error_msg in str(e.args):
                            raise SSLHandshakeRejected('TLS / ' + self.HANDSHAKE_REJECTED_SSL_ERRORS[error_msg])
                    raise # Unknown SSL error if we get there
                except ClientCertificateRequested:
                    # Server expected a client certificate and we didn't provide one
                    raise

            # Pass on exceptions for rejected handshakes
            except SSLHandshakeRejected:
                raise
            except ClientCertificateRequested:
                raise

            # Attempt to retry connection if a network error occurred
            except:
                retryAttempts += 1
                if retryAttempts == self._maxAttempts:
                    # Exhausted the number of retry attempts, give up
                    raise
                elif retryAttempts == 1:
                    delay = random.random()
                else: # Exponential back off
                    delay = min(6, 2*delay) # Cap max delay at 6 seconds

            else: # No network error occurred
                break


    def close(self):
        self.shutdown()
        if self._sock:
            self._sock.close()


    def post_handshake_check(self):
        return ''



class HTTPSConnection(SSLConnection):
    """SSL connection class that sends an HTTP GET request after the SSL
    handshake."""

    HTTP_GET_REQ = 'GET / HTTP/1.0\r\nHost: {0}\r\nConnection: close\r\n\r\n'

    GET_RESULT_FORMAT = 'HTTP {0} {1}{2}'

    ERR_HTTP_TIMEOUT = 'Timeout on HTTP GET'
    ERR_NOT_HTTP = 'Server response was not HTTP'


    def post_handshake_check(self):

        try: # Send an HTTP GET to the server and store the HTTP Status Code
            self.write(self.HTTP_GET_REQ.format(self._host))
            # Parse the response and print the Location header
            httpResp = parse_http_response(self.read(2048))
            if httpResp.version == 9 :
                # HTTP 0.9 => Probably not an HTTP response
                result = self.ERR_NOT_HTTP
            else:
                redirect = ''
                if 300 <= httpResp.status < 400:
                    # Add redirection URL to the result
                    redirect = ' - ' + httpResp.getheader('Location', None)

                result = self.GET_RESULT_FORMAT.format(httpResp.status,
                                                       httpResp.reason,
                                                       redirect)
        except socket.timeout:
            result = self.ERR_HTTP_TIMEOUT

        return result



class SSLTunnelConnection(SSLConnection):
    """SSL connection class that connects to a server through a CONNECT proxy."""

    HTTP_CONNECT_REQ = 'CONNECT {0}:{1} HTTP/1.1\r\n\r\n'
    HTTP_CONNECT_REQ_PROXY_AUTH_BASIC = 'CONNECT {0}:{1} HTTP/1.1\r\nProxy-Authorization: Basic {2}\r\n\r\n'

    ERR_CONNECT_REJECTED = 'The proxy rejected the CONNECT request for this host'
    ERR_PROXY_OFFLINE = 'Could not connect to the proxy: "{0}"'


    def __init__(self, (host, ip, port, sslVersion), sslVerifyLocations, timeout, 
                    maxAttempts, tunnelHost, tunnelPort, tunnelUser=None, tunnelPassword=None):

        super(SSLTunnelConnection, self).__init__((host, ip, port, sslVersion),
                                                  sslVerifyLocations, timeout,
                                                  maxAttempts)
        self._tunnelHost = tunnelHost
        self._tunnelPort = tunnelPort
        self._tunnelBasicAuth = None
        if tunnelUser is not None:
            self._tunnelBasicAuth = b64encode('%s:%s' % (quote(tunnelUser), quote(tunnelPassword)))


    def do_pre_handshake(self):

        try: # Connect to the proxy first
            self._sock = socket.create_connection((self._tunnelHost,
                                                   self._tunnelPort),
                                                   self._timeout)
        except socket.timeout as e:
            raise ProxyError(self.ERR_PROXY_OFFLINE.format(e[0]))
        except socket.error as e:
            raise ProxyError(self.ERR_PROXY_OFFLINE.format(e[1]))

        # Send a CONNECT request with the host we want to tunnel to
        if self._tunnelBasicAuth is None:
            self._sock.send(self.HTTP_CONNECT_REQ.format(self._host, self._port))
        else:
            self._sock.send(self.HTTP_CONNECT_REQ_PROXY_AUTH_BASIC.format(self._host, self._port,
                                        self._tunnelBasicAuth))
        httpResp = parse_http_response(self._sock.recv(2048))

        # Check if the proxy was able to connect to the host
        if httpResp.status != 200:
            raise ProxyError(self.ERR_CONNECT_REJECTED)



class HTTPSTunnelConnection(SSLTunnelConnection, HTTPSConnection):
    """SSL connection class that connects to a server through a CONNECT proxy
    and sends an HTTP GET request after the SSL handshake."""



class SMTPConnection(SSLConnection):
    """SSL connection class that performs an SMTP StartTLS negotiation
    before the SSL handshake and sends a NOOP after the handshake."""

    ERR_SMTP_REJECTED = 'SMTP EHLO was rejected'
    ERR_NO_SMTP_STARTTLS = 'SMTP STARTTLS not supported'


    def do_pre_handshake(self):

        self._sock = socket.create_connection((self._ip, self._port), self._timeout)
        # Get the SMTP banner
        self._sock.recv(2048)

        # Send a EHLO and wait for the 250 status
        self._sock.send('EHLO sslyze.scan\r\n')
        if '250 ' not in self._sock.recv(2048):
            raise StartTLSError(self.ERR_SMTP_REJECTED)

        # Send a STARTTLS
        self._sock.send('STARTTLS\r\n')
        if '220'  not in self._sock.recv(2048):
            raise StartTLSError(self.ERR_NO_SMTP_STARTTLS)


    def post_handshake_check(self):
        try:
            self.write('NOOP\r\n')
            result = self.read(2048).strip()
        except socket.timeout:
            result = 'Timeout on SMTP NOOP'
        return result



class XMPPConnection(SSLConnection):
    """SSL connection class that performs an XMPP StartTLS negotiation
    before the SSL handshake."""

    ERR_XMPP_REJECTED = 'Error opening XMPP stream, try --xmpp_to'
    ERR_XMPP_HOST_UNKNOWN = 'Error opening XMPP stream: server returned host-unknown error, try --xmpp_to'
    ERR_XMPP_NO_STARTTLS = 'XMPP STARTTLS not supported'

    XMPP_OPEN_STREAM = ("<stream:stream xmlns='jabber:client' xmlns:stream='"
        "http://etherx.jabber.org/streams' xmlns:tls='http://www.ietf.org/rfc/"
        "rfc2595.txt' to='{0}' xml:lang='en' version='1.0'>" )
    XMPP_STARTTLS = "<starttls xmlns='urn:ietf:params:xml:ns:xmpp-tls'/>"


    def __init__(self, (host, ip, port, sslVersion), sslVerifyLocations,
                 timeout, maxAttempts, xmpp_to=None):

        super(XMPPConnection, self).__init__((host, ip, port, sslVersion),
                                                  sslVerifyLocations, timeout,
                                                  maxAttempts)

        self._xmpp_to = xmpp_to
        if xmpp_to is None:
            self._xmpp_to = host


    def do_pre_handshake(self):
        """
        Connect to a host on a given (SSL) port, send a STARTTLS command,
        and perform the SSL handshake.
        """
        # Open an XMPP stream
        self._sock = socket.create_connection((self._ip, self._port), self._timeout)
        self._sock.send(self.XMPP_OPEN_STREAM.format(self._xmpp_to))


        # Get the server's features and check for an error
        serverResp = self._sock.recv(4096)
        if '<stream:error>' in serverResp:
            raise StartTLSError(self.ERR_XMPP_REJECTED)
        elif '</stream:features>' not in serverResp:
            # Get all the server features before initiating startTLS
            self._sock.recv(4096)

        # Send a STARTTLS message
        self._sock.send(self.XMPP_STARTTLS)
        xmpp_resp = self._sock.recv(2048)

        if 'host-unknown' in xmpp_resp:
            raise StartTLSError(self.ERR_XMPP_HOST_UNKNOWN)

        if 'proceed'  not in xmpp_resp:
            raise StartTLSError(self.ERR_XMPP_NO_STARTTLS)



class LDAPConnection(SSLConnection):
    """SSL connection class that performs an LDAP StartTLS negotiation
    before the SSL handshake."""

    ERR_NO_STARTTLS = 'LDAP AUTH TLS was rejected'

    START_TLS_CMD = bytearray(b'0\x1d\x02\x01\x01w\x18\x80\x161.3.6.1.4.1.1466.20037')
    START_TLS_OK = 'Start TLS request accepted.'


    def do_pre_handshake(self):
        """
        Connect to a host on a given (SSL) port, send a STARTTLS command,
        and perform the SSL handshake.
        """
        self._sock = socket.create_connection((self._ip, self._port), self._timeout)

        # Send Start TLS
        self._sock.send(self.START_TLS_CMD)
        if self.START_TLS_OK  not in self._sock.recv(2048):
            raise StartTLSError(self.ERR_NO_STARTTLS)



class RDPConnection(SSLConnection):
    """SSL connection class that performs an RDP StartTLS negotiation
    before the SSL handshake."""

    ERR_NO_STARTTLS = 'RDP AUTH TLS was rejected'

    START_TLS_CMD = bytearray(b'\x03\x00\x00\x13\x0E\xE0\x00\x00\x00\x00\x00\x01\x00\x08\x00\x03\x00\x00\x00')
    START_TLS_OK = 'Start TLS request accepted.'

    def do_pre_handshake(self):
        """
        Connect to a host on a given (SSL) port, send a STARTTLS command,
        and perform the SSL handshake.
        """
        self._sock = socket.create_connection((self._host, self._port), self._timeout)

        self._sock.send(self.START_TLS_CMD)
        data = self._sock.recv(4)
        if not data or len(data) != 4 or data[:2] != '\x03\x00' :
            raise StartTLSError(self.ERR_NO_STARTTLS)
        packet_len = struct.unpack(">H", data[2:])[0] - 4
        data = self._sock.recv(packet_len)

        if not data or len(data) != packet_len :
            raise StartTLSError(self.ERR_NO_STARTTLS)



class GenericStartTLSConnection(SSLConnection):
    """SSL connection class that performs a StartTLS negotiation
    before the SSL handshake. Used for POP3, IMAP and FTP."""

    # To be defined in subclasses
    ERR_NO_STARTTLS = ''
    START_TLS_CMD = ''
    START_TLS_OK = ''

    def do_pre_handshake(self):
        """
        Connect to a host on a given (SSL) port, send a STARTTLS command,
        and perform the SSL handshake.
        """
        self._sock = socket.create_connection((self._ip, self._port), self._timeout)

        # Grab the banner
        self._sock.recv(2048)

        # Send Start TLS
        self._sock.send(self.START_TLS_CMD)
        if self.START_TLS_OK  not in self._sock.recv(2048):
            raise StartTLSError(self.ERR_NO_STARTTLS)



class IMAPConnection(GenericStartTLSConnection):
    """SSL connection class that performs an IMAP StartTLS negotiation
    before the SSL handshake."""

    ERR_NO_STARTTLS = 'IMAP START TLS was rejected'

    START_TLS_CMD = '. STARTTLS\r\n'
    START_TLS_OK = '. OK'



class POP3Connection(GenericStartTLSConnection):
    """SSL connection class that performs a POP3 StartTLS negotiation
    before the SSL handshake."""

    ERR_NO_STARTTLS = 'POP START TLS was rejected'

    START_TLS_CMD = 'STLS\r\n'
    START_TLS_OK = '+OK'



class FTPConnection(GenericStartTLSConnection):
    """SSL connection class that performs an FTP StartTLS negotiation
    before the SSL handshake."""

    ERR_NO_STARTTLS = 'FTP AUTH TLS was rejected'

    START_TLS_CMD = 'AUTH TLS\r\n'
    START_TLS_OK = '234'



########NEW FILE########
__FILENAME__ = ThreadPool
#!/usr/bin/env python
#-------------------------------------------------------------------------------
# Name:         ThreadPool.py
# Purpose:      Generic, simple thread pool used in some of the plugins.
#
# Author:       alban
#
# Copyright:    2012 SSLyze developers
#
#   SSLyze is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 2 of the License, or
#   (at your option) any later version.
#
#   SSLyze is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with SSLyze.  If not, see <http://www.gnu.org/licenses/>.
#-------------------------------------------------------------------------------

import threading
from Queue import Queue


class _ThreadPoolSentinel:
    pass


class ThreadPool:
    """
    Generic Thread Pool used in some of the plugins.
    Any unhandled exception happening in the work function goes to the error
    queue that can be read using get_error().
    Anything else goes to the result queue that can be read using get_result().
    """
    def  __init__(self):
        self._active_threads = 0
        self._job_q = Queue()
        self._result_q = Queue()
        self._error_q = Queue()
        self._thread_list = []

    def add_job(self, job):
        self._job_q.put(job)

    def get_error(self):
        active_threads = self._active_threads
        while (active_threads) or (not self._error_q.empty()):
            error = self._error_q.get()
            if isinstance(error, _ThreadPoolSentinel): # One thread was done
                active_threads -= 1
                self._error_q.task_done()
                continue

            else: # Getting an actual error
                self._error_q.task_done()
                yield error


    def get_result(self):
        active_threads = self._active_threads
        while (active_threads) or (not self._result_q.empty()):
            result = self._result_q.get()
            if isinstance(result, _ThreadPoolSentinel): # One thread was done
                active_threads -= 1
                self._result_q.task_done()
                continue

            else: # Getting an actual result
                self._result_q.task_done()
                yield result


    def start(self, nb_threads):
        """
        Should only be called once all the jobs have been added using add_job().
        """
        if self._active_threads:
            raise Exception('Threads already started.')

        # Create thread pool
        for _ in xrange(nb_threads):
            worker = threading.Thread(
                target=_work_function,
                args=(self._job_q, self._result_q, self._error_q))
            worker.start()
            self._thread_list.append(worker)
            self._active_threads += 1

        # Put sentinels to let the threads know when there's no more jobs
        [self._job_q.put(_ThreadPoolSentinel()) for worker in self._thread_list]


    def join(self): # Clean exit
        self._job_q.join()
        [worker.join() for worker in self._thread_list]
        self._active_threads = 0
        self._result_q.join()
        self._error_q.join()


def _work_function(job_q, result_q, error_q):
    """Work function expected to run within threads."""
    while True:
        job = job_q.get()

        if isinstance(job, _ThreadPoolSentinel): # All the work is done, get out
            result_q.put(_ThreadPoolSentinel())
            error_q.put(_ThreadPoolSentinel())
            job_q.task_done()
            break

        function = job[0]
        args = job[1]
        try:
            result = function(*args)
        except Exception as e:
            error_q.put((job, e))
        else:
            result_q.put((job, result))
        finally:
            job_q.task_done()
            

########NEW FILE########
