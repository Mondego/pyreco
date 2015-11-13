__FILENAME__ = auth
#    CUPS Cloudprint - Print via Google Cloud Print
#    Copyright (C) 2011 Simon Cadman
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import json
import os
import sys
from oauth2client import client
from oauth2client import multistore_file
from cloudprintrequestor import CloudPrintRequestor
from ccputils import Utils
from oauth2client.client import AccessTokenRefreshError

class Auth:

    clientid = "843805314553.apps.googleusercontent.com"
    clientsecret = 'MzTBsY4xlrD_lxkmwFbBrvBv'
    config = '/etc/cloudprint.conf'

    @staticmethod
    def RenewToken(interactive, requestor, credentials, storage, userid):
        try:
            credentials.refresh(requestor)
        except AccessTokenRefreshError as e:
            if not interactive:
                    message = "ERROR: Failed to renew token "
                    message += "(error: "
                    message += str(e)
                    message += "), "
                    message += "please re-run "
                    message += "/usr/share/cloudprint-cups/"
                    message += "setupcloudprint.py\n"
                    sys.stderr.write(message)
                    sys.exit(1)
            else:
                    message = "Failed to renew token (error: "
                    message += str(e) + "), "
                    message += "authentication needs to be "
                    message += "setup again:\n"
                    sys.stderr.write(message)
                    Auth.AddAccount(storage, userid)
                    credentials = storage.get()
        return credentials
        
    @staticmethod
    def DeleteAccount(userid=None):
        """Delete an account from the configuration file

        Args:
          storage: storage, instance of storage to store credentials in.
          userid: string, reference for the account

        Returns:
          deleted: boolean , true on success
        """
        storage = multistore_file.get_credential_storage(
            Auth.config,
            Auth.clientid,
            userid,
            ['https://www.googleapis.com/auth/cloudprint'])
        return storage.delete()

    @staticmethod
    def AddAccount(storage, userid=None,
                   permissions=['https://www.googleapis.com/auth/cloudprint']):
        """Adds an account to the configuration file

        Args:
          storage: storage, instance of storage to store credentials in.
          userid: string, reference for the account

        Returns:
          credentials: A credentials instance with the account details
        """
        if userid is None:
            userid = raw_input(
                "Name for this user account ( eg something@gmail.com )? ")

        while True:
            flow = client.OAuth2WebServerFlow(client_id=Auth.clientid,
                                              client_secret=Auth.clientsecret,
                                              scope=permissions,
                                              user_agent=userid)
            auth_uri = flow.step1_get_authorize_url()
            message = "Open this URL, grant access to CUPS Cloud Print,"
            message += "then provide the code displayed : \n\n"
            message += auth_uri + "\n"
            print message
            code = raw_input('Code from Google: ')
            try:
                print ""
                credentials = flow.step2_exchange(code)
                storage.put(credentials)

                # fix permissions
                Utils.FixFilePermissions(Auth.config)

                return credentials
            except Exception as e:
                message = "\nThe code does not seem to be valid ( "
                message += str(e) + " ), please try again.\n"
                print message

    @staticmethod
    def SetupAuth(interactive=False,
                  permissions=['https://www.googleapis.com/auth/cloudprint']):
        """Sets up requestors with authentication tokens

        Args:
          interactive: boolean, when set to true can prompt user, otherwise
                       returns False if authentication fails

        Returns:
          requestor, storage: Authenticated requestors and an instance
                              of storage
        """
        modifiedconfig = False

        # parse config file and extract useragents, which we use for account
        # names
        userids = []
        if os.path.exists(Auth.config):
            content_file = open(Auth.config, 'r')
            content = content_file.read()
            data = json.loads(content)
            for user in data['data']:
                userids.append(str(user['credential']['user_agent']))
        else:
            modifiedconfig = True

        if len(userids) == 0:
            userids = [None]

        requestors = []
        for userid in userids:
            storage = multistore_file.get_credential_storage(
                Auth.config,
                Auth.clientid,
                userid,
                permissions)
            credentials = storage.get()

            if not credentials and interactive:
                credentials = Auth.AddAccount(storage, userid, permissions)
                modifiedconfig = True
                if userid is None:
                    userid = credentials.user_agent

            if credentials:
                # renew if expired
                requestor = CloudPrintRequestor()
                if credentials.access_token_expired:
                    Auth.RenewToken(interactive, requestor, credentials, storage, userid)
                requestor = credentials.authorize(requestor)
                requestor.setAccount(userid)
                requestors.append(requestor)

        # fix permissions
        if modifiedconfig:
            Utils.FixFilePermissions(Auth.config)

        if not credentials:
            return False, False
        else:
            return requestors, storage

    @staticmethod
    def GetAccountNames(requestors):
        requestorAccounts = []
        for requestor in requestors:
            requestorAccounts.append(requestor.getAccount())
        return requestorAccounts

########NEW FILE########
__FILENAME__ = backend
#! /bin/sh
"true" '''\'
if command -v python2 > /dev/null; then
  exec python2 "$0" "$@"
else
  exec python "$0" "$@"
fi
exit $?
'''

#    CUPS Cloudprint - Print via Google Cloud Print
#    Copyright (C) 2011 Simon Cadman
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

if __name__ == '__main__':  # pragma: no cover
    import sys
    import os
    import subprocess
    import logging

    libpath = "/usr/local/share/cloudprint-cups/"
    if not os.path.exists(libpath):
        libpath = "/usr/share/cloudprint-cups"
    sys.path.insert(0, libpath)

    from auth import Auth
    from printermanager import PrinterManager
    from ccputils import Utils

    Utils.SetupLogging()

    # line below is replaced on commit
    CCPVersion = "20140521 163500"
    Utils.ShowVersion(CCPVersion)

    if len(sys.argv) != 1 and len(sys.argv) < 6 or len(sys.argv) > 7:
        sys.stderr.write(
            "ERROR: Usage: %s job-id user title copies options [file]\n" % sys.argv[0])
        sys.exit(0)

    if len(sys.argv) >= 4 and sys.argv[3] == "Set Default Options":
        print "ERROR: Unimplemented command: " + sys.argv[3]
        logging.error("Unimplemented command: " + sys.argv[3])
        sys.exit(0)

    if len(sys.argv) == 7:
        prog, jobID, userName, jobTitle, copies, printOptions, printFile = sys.argv
    if len(sys.argv) == 6:
        prog, jobID, userName, jobTitle, copies, printOptions = sys.argv
        printFile = None

    requestors, storage = Auth.SetupAuth(False)
    if not requestors:
        sys.stderr.write("ERROR: config is invalid or missing\n")
        logging.error("backend tried to run with invalid config")
        sys.exit(1)
    printer_manager = PrinterManager(requestors)

    if len(sys.argv) == 1:
        print 'network cloudprint "Unknown" "Google Cloud Print"'

        printers = printer_manager.getPrinters()
        if printers is not None:
            try:
                for printer in printers:
                    print printer.getCUPSBackendDescription()
            except Exception as error:
                sys.stderr.write("ERROR: " + error)
                logging.error(error)
                sys.exit(1)
        sys.exit(0)

    # if no printfile, put stdin to a temp file
    if printFile is None:
        tmpDir = os.getenv('TMPDIR')
        if not tmpDir:
            tmpDir = "/tmp"
        tempFile = '%s/%s-%s-cupsjob-%s' % \
            (tmpDir, jobID, userName, str(os.getpid()))

        OUT = open(tempFile, 'w')

        if not OUT:
            print "ERROR: Cannot write " + tempFile
            sys.exit(1)

        for line in sys.stdin:
            OUT.write(line)

        OUT.close()

        printFile = tempFile

        # Backends should only produce multiple copies if a file name is
        # supplied (see CUPS Software Programmers Manual)
        copies = 1

    uri = os.getenv('DEVICE_URI')
    cupsprintername = os.getenv('PRINTER')
    if uri is None:
        message = 'URI must be "cloudprint://<account name>/<cloud printer id>"!\n'
        sys.stdout.write(message)
        sys.exit(255)

    logging.info("Printing file " + printFile)
    optionsstring = ' '.join(["'%s'" % option for option in sys.argv])
    logging.info("Device is %s , printername is %s, params are: %s" %
        (uri, cupsprintername, optionsstring))

    pdfFile = printFile + ".pdf"
    if Utils.which("ps2pdf") is None:
        convertToPDFParams = ["pstopdf", printFile, pdfFile]
    else:
        convertToPDFParams = ["ps2pdf", "-dPDFSETTINGS=/printer",
                              "-dUseCIEColor", printFile, pdfFile]

    result = 0

    logging.info('is this a pdf? ' + printFile)
    if not os.path.exists(printFile):
        sys.stderr.write('ERROR: file "%s" not found\n' % printFile)
        result = 1
    elif not Utils.fileIsPDF(printFile):
        sys.stderr.write("INFO: Converting print job to PDF\n")
        if subprocess.call(convertToPDFParams) != 0:
            sys.stderr.write("ERROR: Failed to convert file to pdf\n")
            result = 1
        else:
            logging.info("Converted to PDF as " + pdfFile)
    else:
        pdfFile = printFile + '.pdf'
        os.rename(printFile, pdfFile)
        logging.info("Using %s as is already PDF" % pdfFile)

    if result == 0:
        sys.stderr.write("INFO: Sending document to Cloud Print\n")
        logging.info("Sending %s to cloud" % pdfFile)

        printer = printer_manager.getPrinterByURI(uri)
        if printer is None:
            print "ERROR: PrinterManager '%s' not found" % uri
            result = 1
        elif printer.submitJob('pdf', pdfFile, jobTitle, cupsprintername, printOptions):
            print "INFO: Successfully printed"
            result = 0
        else:
            print "ERROR: Failed to submit job to cloud print"
            result = 1

        logging.info(pdfFile + " sent to cloud print, deleting")
        if os.path.exists(printFile):
            os.unlink(printFile)
        sys.stderr.write("INFO: Cleaning up temporary files\n")
        logging.info("Deleted " + printFile)
        if os.path.exists(pdfFile):
            os.unlink(pdfFile)
        logging.info("Deleted " + pdfFile)
        if result != 0:
            sys.stderr.write("INFO: Printing Failed\n")
            logging.info("Failed printing")
        else:
            sys.stderr.write("INFO: Printing Successful\n")
            logging.info("Completed printing")

    sys.exit(result)

########NEW FILE########
__FILENAME__ = ccputils
#    CUPS Cloudprint - Print via Google Cloud Print
#    Copyright (C) 2014 Simon Cadman
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import subprocess
import os
import logging
import sys
import grp
import mimetypes
import base64


class Utils:

    logpath = '/var/log/cups/cloudprint_log'
    
    # Countries where letter sized paper is used, according to:
    # http://en.wikipedia.org/wiki/Letter_(paper_size)
    _LETTER_COUNTRIES = set(('US', 'CA', 'MX', 'BO', 'CO', 'VE', 'PH', 'CL'))

    @staticmethod
    def FixFilePermissions(filename):
        filePermissions = True
        fileOwnerships = True
        currentStat = None
        if os.path.exists(filename):
            currentStat = os.stat(filename)

        if currentStat is None or currentStat.st_mode != 0o100660:
            try:
                os.chmod(filename, 0o100660)
            except:
                filePermissions = False
                sys.stderr.write(
                    "DEBUG: Cannot alter " +
                    filename +
                    " file permissions\n")
                pass

        if currentStat is None or currentStat.st_gid != Utils.GetLPID():
            try:
                os.chown(filename, -1, Utils.GetLPID())
            except:
                fileOwnerships = False
                sys.stderr.write(
                    "DEBUG: Cannot alter " +
                    filename +
                    " file ownership\n")
                pass

        return filePermissions, fileOwnerships

    @staticmethod
    def SetupLogging(logpath=None):
        returnValue = True
        logformat = "%(asctime)s|%(levelname)s|%(message)s"
        dateformat = "%Y-%m-%d %H:%M:%S"
        if logpath is None:
            logpath = Utils.logpath
        try:
            logging.basicConfig(
                filename=logpath,
                level=logging.INFO,
                format=logformat,
                datefmt=dateformat)
            Utils.FixFilePermissions(logpath)
        except:
            logging.basicConfig(
                level=logging.INFO,
                format=logformat,
                datefmt=dateformat)
            logging.error("Unable to write to log file " + logpath)
            returnValue = False
        return returnValue

    @staticmethod
    def fileIsPDF(filename):
        """Check if a file is or isnt a PDF

        Args:
        filename: string, name of the file to check
        Returns:
        boolean: True = is a PDF, False = not a PDF.
        """
        p = subprocess.Popen(["file", filename.lstrip('-')], stdout=subprocess.PIPE)
        output = p.communicate()[0]
        return "PDF document" in output

    @staticmethod
    def is_exe(fpath):
        return os.path.exists(fpath) and os.access(fpath, os.X_OK)

    @staticmethod
    def which(program):
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if Utils.is_exe(exe_file):
                return exe_file
        return None

    @staticmethod
    def GetLPID(default='lp', alternative='cups', useFiles=True,
                blacklistedGroups=['adm', 'wheel', 'root'],
                useFilesOnly=False):
        blacklistedGroupIds = []
        for group in blacklistedGroups:
            try:
                blacklistedGroupIds.append(grp.getgrnam(group).gr_gid)
            except:
                logging.debug("Group " + group + " not found")

        if useFiles:
            # check files in order
            for cupsConfigFile in ['/var/log/cups/access_log',
                                   '/etc/cups/ppd',
                                   '/usr/local/etc/cups/ppd']:
                if os.path.exists(cupsConfigFile):
                    configGid = os.stat(cupsConfigFile).st_gid
                    if configGid not in blacklistedGroupIds:
                        return configGid
                    else:
                        logging.debug(
                            "Group " +
                            group +
                            " excluded as blacklisted")

        if useFilesOnly:
            return None

        # try lp first, then cups
        lpgrp = None
        try:
            lpgrp = grp.getgrnam(default)
        except:
            try:
                lpgrp = grp.getgrnam(alternative)
            except:
                pass
        if lpgrp is None:
            return None
        else:
            return lpgrp.gr_gid

    @staticmethod
    def ShowVersion(CCPVersion):
        if len(sys.argv) == 2 and sys.argv[1] == 'version':
            print "CUPS Cloud Print Version " + CCPVersion
            sys.exit(0)
        return False

    @staticmethod
    def ReadFile(pathname):
        """Read contents of a file and return content.

        Args:
          pathname: string, (path)name of file.
        Returns:
          string: contents of file.
        """
        try:
            f = open(pathname, 'rb')
            s = f.read()
            return s
        except IOError as e:
            print 'ERROR: Error opening %s\n%s', pathname, e
            return None

    @staticmethod
    def WriteFile(file_name, data):
        """Write contents of data to a file_name.

        Args:
          file_name: string, (path)name of file.
          data: string, contents to write to file.
        Returns:
          boolean: True = success, False = errors.
        """
        status = True

        try:
            f = open(file_name, 'wb')
            f.write(data)
            f.close()
        except IOError as e:
            status = False

        return status

    @staticmethod
    def Base64Encode(pathname):
        """Convert a file to a base64 encoded file.

        Args:
          pathname: path name of file to base64 encode..
        Returns:
          string, name of base64 encoded file.
        For more info on data urls, see:
          http://en.wikipedia.org/wiki/Data_URI_scheme
        """
        b64_pathname = pathname + '.b64'
        file_type = mimetypes.guess_type(
            pathname)[0] or 'application/octet-stream'
        data = Utils.ReadFile(pathname)
        if data is None:
            return None

        # Convert binary data to base64 encoded data.
        header = 'data:%s;base64,' % file_type
        b64data = header + base64.b64encode(data)

        if Utils.WriteFile(b64_pathname, b64data):
            return b64_pathname
        else:
            return None
    
    @staticmethod
    def GetLanguage(locale):
        language = 'en'
        if len(locale) < 1 or locale[0] == None:
            return language
        defaultlocale = locale[0]
        language = defaultlocale
        if '_' in language:
            language = language.split("_")[0]
        return language

    @staticmethod
    def GetDefaultPaperType(locale):
        defaultpapertype = "Letter"
        if len(locale) < 1 or locale[0] == None:
            return defaultpapertype
        if len(locale[0].split('_')) > 1 and locale[0].split('_')[1] not in Utils._LETTER_COUNTRIES:
            defaultpapertype = "A4"
        return defaultpapertype

########NEW FILE########
__FILENAME__ = cloudprintrequestor
#    CUPS Cloudprint - Print via Google Cloud Print
#    Copyright (C) 2011 Simon Cadman
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
import httplib2
import json


class CloudPrintRequestor(httplib2.Http):

    CLOUDPRINT_URL = 'https://www.google.com/cloudprint'
    account = None

    def setAccount(self, account):
        """Sets the account name

        Args:
          filename: string, name of the account
        """
        self.account = account

    def getAccount(self):
        """Gets the account name

        Return:
          string: Account name.
        """
        return self.account

    def doRequest(self, path, headers=None, data=None, boundary=None, testResponse=None,
                  endpointurl=None):
        """Sends a request to Google Cloud Print

        Args:
          path: string, path part of url
          headers: list, headers to send to GCP
          data: string, body part of request
          boundary: string, boundary part of http forms
        Return:
          list: Decoded json response from Google.
        """
        # force useragent to CCP
        if headers is None:
            headers = {}
        headers['user-agent'] = "CUPS Cloud Print"

        url = '%s/%s' % (self.CLOUDPRINT_URL, path)
        if endpointurl is not None:
            url = '%s/%s' % (endpointurl, path)

        # use test response for testing
        if testResponse is None:
            if data is None:
                headers, response = self.request(url, "GET", headers=headers)
            else:
                headers['Content-Length'] = str(len(data))
                contenttype = 'multipart/form-data;boundary=%s' % boundary
                headers['Content-Type'] = contenttype
                headers, response = self.request(
                    url, "POST", body=data, headers=headers)
        else:
            response = testResponse

        try:
            decodedresponse = json.loads(response)
        except ValueError as e:
            print "ERROR: Failed to decode JSON, value was: " + response
            raise e

        return decodedresponse

    def search(self):
        return self.doRequest('search?connection_status=ALL&client=webui')

    def printer(self, printerid):
        return self.doRequest('printer?printerid=%s' % printerid)

    def submit(self, edata, boundary):
        return self.doRequest('submit', data=edata, boundary=boundary)

########NEW FILE########
__FILENAME__ = deleteaccount
#! /bin/sh
"true" '''\'
if command -v python2 > /dev/null; then
  exec python2 "$0" "$@"
else
  exec python "$0" "$@"
fi
exit $?
'''

#    CUPS Cloudprint - Print via Google Cloud Print
#    Copyright (C) 2011 Simon Cadman
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

if __name__ == '__main__':  # pragma: no cover
    from auth import Auth
    from printermanager import PrinterManager

    from ccputils import Utils
    Utils.SetupLogging()

    # line below is replaced on commit
    CCPVersion = "20140501 203545"
    Utils.ShowVersion(CCPVersion)

    while True:
        result, storage = Auth.SetupAuth(False)
        if not result:
            print "No accounts are currently setup"
            break
        else:
            requestors = result
            print "You currently have these accounts configured: "
            i = 0
            accounts = []
            for requestor in requestors:
                i += 1
                accounts.append(requestor.getAccount())
                print str(i) + ") " + requestor.getAccount()
            print "0) Exit"
            answer = raw_input("Which account to delete (1-" + str(i) + ") ? ")
            if (answer.isdigit() and int(answer) <= i and int(answer) >= 1):
                if (Auth.DeleteAccount(accounts[int(answer) - 1]) is None):
                    print accounts[int(answer) - 1] + " deleted."
                    deleteprintersanswer = raw_input(
                        "Also delete associated printers? ")
                    if deleteprintersanswer.lower().startswith("y"):
                        printer_manager = PrinterManager(requestors)
                        printers, connection = \
                            printer_manager.getCUPSPrintersForAccount(accounts[int(answer) - 1])
                        if len(printers) == 0:
                            print "No printers to delete"
                        else:
                            for cupsPrinter in printers:
                                print "Deleting " + cupsPrinter['printer-info']
                                deleteReturnValue = connection.deletePrinter(
                                    cupsPrinter['printer-info'])
                                if deleteReturnValue is not None:
                                    errormessage = "Error deleting printer: "
                                    errormessage += str(deleteReturnValue)
                                    print errormessage
                    else:
                        print "Not deleting associated printers"
                else:
                    errormessage = "Error deleting stored "
                    errormessage += "credentials, perhaps "
                    errormessage += Auth.config + " is not writable?"
                    print errormessage
            elif (answer == "0"):
                break
            else:
                print "Invalid response, use '0' to exit"

########NEW FILE########
__FILENAME__ = dynamicppd
#! /bin/sh
"true" '''\'
if command -v python2 > /dev/null; then
  exec python2 "$0" "$@"
else
  exec python "$0" "$@"
fi
exit $?
'''

#    CUPS Cloudprint - Print via Google Cloud Print
#    Copyright (C) 2013 Simon Cadman
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
import os
import sys


def doList(sys, printer_manager):
    """Lists Google Cloud Print printers."""
    printers = printer_manager.getPrinters()
    if printers is None:
        sys.stderr.write("ERROR: No Printers Found\n")
        sys.exit(1)
    for printer in printers:
        print printer.getCUPSDriverDescription()
    sys.exit(0)


def doCat():
    """Prints a PPD to stdout, per argv arguments."""
    ppdname = sys.argv[2]
    ppdparts = ppdname.split(":")
    if len(ppdparts) < 3 or ppdparts[0] != 'cupscloudprint' or not ppdparts[2].endswith('.ppd'):
        sys.stderr.write("ERROR: PPD name is invalid\n")
        sys.exit(1)

    accountName = ppdparts[1]
    printerId = ppdparts[2].rsplit('.', 1)[0]

    printer = printer_manager.getPrinter(printerId, accountName)

    if printer is None:
        sys.stderr.write("ERROR: PPD %s Not Found\n" % ppdname)
        sys.exit(1)

    print printer.generatePPD()

    sys.exit(0)


def showUsage():
    sys.stderr.write("ERROR: Usage: %s [list|version|cat drivername]\n" % sys.argv[0])
    sys.exit(1)

if __name__ == '__main__':  # pragma: no cover

    libpath = "/usr/local/share/cloudprint-cups/"
    if not os.path.exists(libpath):
        libpath = "/usr/share/cloudprint-cups"
    sys.path.insert(0, libpath)

    from auth import Auth
    from printermanager import PrinterManager
    from ccputils import Utils

    if len(sys.argv) < 2:
        showUsage()

    Utils.SetupLogging()

    # line below is replaced on commit
    CCPVersion = "20140521 163500"
    Utils.ShowVersion(CCPVersion)

    requestors, storage = Auth.SetupAuth(False)
    if not requestors:
        sys.stderr.write("ERROR: config is invalid or missing\n")
        logging.error("backend tried to run with invalid config")
        sys.exit(1)

    printer_manager = PrinterManager(requestors)

    if sys.argv[1] == 'list':
        doList(sys, printer_manager)

    elif sys.argv[1] == 'cat':
        if len(sys.argv) == 2 or sys.argv[2] == "":
            showUsage()
        doCat()

    showUsage()

########NEW FILE########
__FILENAME__ = listcloudprinters
#! /bin/sh
"true" '''\'
if command -v python2 > /dev/null; then
  exec python2 "$0" "$@"
else
  exec python "$0" "$@"
fi
exit $?
'''

#    CUPS Cloudprint - Print via Google Cloud Print
#    Copyright (C) 2011 Simon Cadman
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

if __name__ == '__main__':  # pragma: no cover

    import sys
    from auth import Auth
    from printermanager import PrinterManager
    from ccputils import Utils
    Utils.SetupLogging()

    # line below is replaced on commit
    CCPVersion = "20140501 203545"
    Utils.ShowVersion(CCPVersion)

    requestors, storage = Auth.SetupAuth(True)
    printer_manager = PrinterManager(requestors)
    printers = printer_manager.getPrinters()
    if printers is None:
        print "No Printers Found"
        sys.exit(1)

    for printer in printers:
        print printer.getListDescription()

########NEW FILE########
__FILENAME__ = anyjson
# Copyright (C) 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utility module to import a JSON module

Hides all the messy details of exactly where
we get a simplejson module from.
"""

__author__ = 'jcgregorio@google.com (Joe Gregorio)'


try: # pragma: no cover
  # Should work for Python2.6 and higher.
  import json as simplejson
except ImportError: # pragma: no cover
  try:
    import simplejson
  except ImportError:
    # Try to import from django, should work on App Engine
    from django.utils import simplejson

########NEW FILE########
__FILENAME__ = client
# Copyright (C) 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""An OAuth 2.0 client.

Tools for interacting with OAuth 2.0 protected resources.
"""

__author__ = 'jcgregorio@google.com (Joe Gregorio)'

import base64
import clientsecrets
import copy
import datetime
import httplib2
import logging
import os
import sys
import time
import urllib
import urlparse

from anyjson import simplejson

HAS_OPENSSL = False
try: # pragma: no cover 
  from oauth2client.crypt import Signer
  from oauth2client.crypt import make_signed_jwt
  from oauth2client.crypt import verify_signed_jwt_with_certs
  HAS_OPENSSL = True
except ImportError: # pragma: no cover 
  pass

try: # pragma: no cover 
  from urlparse import parse_qsl
except ImportError: # pragma: no cover 
  from cgi import parse_qsl

logger = logging.getLogger(__name__)

# Expiry is stored in RFC3339 UTC format
EXPIRY_FORMAT = '%Y-%m-%dT%H:%M:%SZ'

# Which certs to use to validate id_tokens received.
ID_TOKEN_VERIFICATON_CERTS = 'https://www.googleapis.com/oauth2/v1/certs'

# Constant to use for the out of band OAuth 2.0 flow.
OOB_CALLBACK_URN = 'urn:ietf:wg:oauth:2.0:oob'


class Error(Exception):
  """Base error for this module."""
  pass


class FlowExchangeError(Error):
  """Error trying to exchange an authorization grant for an access token."""
  pass


class AccessTokenRefreshError(Error):
  """Error trying to refresh an expired access token."""
  pass

class UnknownClientSecretsFlowError(Error):
  """The client secrets file called for an unknown type of OAuth 2.0 flow. """
  pass


class AccessTokenCredentialsError(Error):
  """Having only the access_token means no refresh is possible."""
  pass


class VerifyJwtTokenError(Error):
  """Could on retrieve certificates for validation."""
  pass


def _abstract(): # pragma: no cover 
  raise NotImplementedError('You need to override this function')


class MemoryCache(object):
  """httplib2 Cache implementation which only caches locally."""

  def __init__(self):
    self.cache = {}

  def get(self, key):
    return self.cache.get(key)

  def set(self, key, value):
    self.cache[key] = value

  def delete(self, key):
    self.cache.pop(key, None)


class Credentials(object):
  """Base class for all Credentials objects.

  Subclasses must define an authorize() method that applies the credentials to
  an HTTP transport.

  Subclasses must also specify a classmethod named 'from_json' that takes a JSON
  string as input and returns an instaniated Credentials object.
  """

  NON_SERIALIZED_MEMBERS = ['store']

  def authorize(self, http):
    """Take an httplib2.Http instance (or equivalent) and
    authorizes it for the set of credentials, usually by
    replacing http.request() with a method that adds in
    the appropriate headers and then delegates to the original
    Http.request() method.
    """
    _abstract()

  def refresh(self, http):
    """Forces a refresh of the access_token.

    Args:
      http: httplib2.Http, an http object to be used to make the refresh
        request.
    """
    _abstract()

  def apply(self, headers):
    """Add the authorization to the headers.

    Args:
      headers: dict, the headers to add the Authorization header to.
    """
    _abstract()

  def _to_json(self, strip):
    """Utility function for creating a JSON representation of an instance of Credentials.

    Args:
      strip: array, An array of names of members to not include in the JSON.

    Returns:
       string, a JSON representation of this instance, suitable to pass to
       from_json().
    """
    t = type(self)
    d = copy.copy(self.__dict__)
    for member in strip:
      if member in d:
        del d[member]
    if 'token_expiry' in d and isinstance(d['token_expiry'], datetime.datetime):
      d['token_expiry'] = d['token_expiry'].strftime(EXPIRY_FORMAT)
    # Add in information we will need later to reconsistitue this instance.
    d['_class'] = t.__name__
    d['_module'] = t.__module__
    return simplejson.dumps(d)

  def to_json(self):
    """Creating a JSON representation of an instance of Credentials.

    Returns:
       string, a JSON representation of this instance, suitable to pass to
       from_json().
    """
    return self._to_json(Credentials.NON_SERIALIZED_MEMBERS)

  def new_from_json(cls, s):
    """Utility class method to instantiate a Credentials subclass from a JSON
    representation produced by to_json().

    Args:
      s: string, JSON from to_json().

    Returns:
      An instance of the subclass of Credentials that was serialized with
      to_json().
    """
    data = simplejson.loads(s)
    # Find and call the right classmethod from_json() to restore the object.
    module = data['_module']
    try:
      m = __import__(module)
    except ImportError:
      # In case there's an object from the old package structure, update it
      module = module.replace('.apiclient', '')
      m = __import__(module)

    m = __import__(module, fromlist=module.split('.')[:-1])
    kls = getattr(m, data['_class'])
    from_json = getattr(kls, 'from_json')
    return from_json(s)

  new_from_json = classmethod(new_from_json)

  def from_json(cls, s):
    """Instantiate a Credentials object from a JSON description of it.

    The JSON should have been produced by calling .to_json() on the object.

    Args:
      data: dict, A deserialized JSON object.

    Returns:
      An instance of a Credentials subclass.
    """
    return Credentials()

  from_json = classmethod(from_json)


class Flow(object):
  """Base class for all Flow objects."""
  pass


class Storage(object):
  """Base class for all Storage objects.

  Store and retrieve a single credential.  This class supports locking
  such that multiple processes and threads can operate on a single
  store.
  """

  def acquire_lock(self):
    """Acquires any lock necessary to access this Storage.

    This lock is not reentrant.
    """
    pass

  def release_lock(self):
    """Release the Storage lock.

    Trying to release a lock that isn't held will result in a
    RuntimeError.
    """
    pass

  def locked_get(self):
    """Retrieve credential.

    The Storage lock must be held when this is called.

    Returns:
      oauth2client.client.Credentials
    """
    _abstract()

  def locked_put(self, credentials):
    """Write a credential.

    The Storage lock must be held when this is called.

    Args:
      credentials: Credentials, the credentials to store.
    """
    _abstract()

  def locked_delete(self):
    """Delete a credential.

    The Storage lock must be held when this is called.
    """
    _abstract()

  def get(self):
    """Retrieve credential.

    The Storage lock must *not* be held when this is called.

    Returns:
      oauth2client.client.Credentials
    """
    self.acquire_lock()
    try:
      return self.locked_get()
    finally:
      self.release_lock()

  def put(self, credentials):
    """Write a credential.

    The Storage lock must be held when this is called.

    Args:
      credentials: Credentials, the credentials to store.
    """
    self.acquire_lock()
    try:
      self.locked_put(credentials)
    finally:
      self.release_lock()

  def delete(self):
    """Delete credential.

    Frees any resources associated with storing the credential.
    The Storage lock must *not* be held when this is called.

    Returns:
      None
    """
    self.acquire_lock()
    try:
      return self.locked_delete()
    finally:
      self.release_lock()


class OAuth2Credentials(Credentials):
  """Credentials object for OAuth 2.0.

  Credentials can be applied to an httplib2.Http object using the authorize()
  method, which then adds the OAuth 2.0 access token to each request.

  OAuth2Credentials objects may be safely pickled and unpickled.
  """

  def __init__(self, access_token, client_id, client_secret, refresh_token,
               token_expiry, token_uri, user_agent, id_token=None):
    """Create an instance of OAuth2Credentials.

    This constructor is not usually called by the user, instead
    OAuth2Credentials objects are instantiated by the OAuth2WebServerFlow.

    Args:
      access_token: string, access token.
      client_id: string, client identifier.
      client_secret: string, client secret.
      refresh_token: string, refresh token.
      token_expiry: datetime, when the access_token expires.
      token_uri: string, URI of token endpoint.
      user_agent: string, The HTTP User-Agent to provide for this application.
      id_token: object, The identity of the resource owner.

    Notes:
      store: callable, A callable that when passed a Credential
        will store the credential back to where it came from.
        This is needed to store the latest access_token if it
        has expired and been refreshed.
    """
    self.access_token = access_token
    self.client_id = client_id
    self.client_secret = client_secret
    self.refresh_token = refresh_token
    self.store = None
    self.token_expiry = token_expiry
    self.token_uri = token_uri
    self.user_agent = user_agent
    self.id_token = id_token

    # True if the credentials have been revoked or expired and can't be
    # refreshed.
    self.invalid = False

  def authorize(self, http):
    """Authorize an httplib2.Http instance with these credentials.

    The modified http.request method will add authentication headers to each
    request and will refresh access_tokens when a 401 is received on a
    request. In addition the http.request method has a credentials property,
    http.request.credentials, which is the Credentials object that authorized
    it.

    Args:
       http: An instance of httplib2.Http
           or something that acts like it.

    Returns:
       A modified instance of http that was passed in.

    Example:

      h = httplib2.Http()
      h = credentials.authorize(h)

    You can't create a new OAuth subclass of httplib2.Authenication
    because it never gets passed the absolute URI, which is needed for
    signing. So instead we have to overload 'request' with a closure
    that adds in the Authorization header and then calls the original
    version of 'request()'.
    """
    request_orig = http.request

    # The closure that will replace 'httplib2.Http.request'.
    def new_request(uri, method='GET', body=None, headers=None,
                    redirections=httplib2.DEFAULT_MAX_REDIRECTS,
                    connection_type=None):
      if not self.access_token:
        logger.info('Attempting refresh to obtain initial access_token')
        self._refresh(request_orig)

      # Modify the request headers to add the appropriate
      # Authorization header.
      if headers is None:
        headers = {}
      self.apply(headers)

      if self.user_agent is not None:
        if 'user-agent' in headers:
          headers['user-agent'] = self.user_agent + ' ' + headers['user-agent']
        else:
          headers['user-agent'] = self.user_agent

      resp, content = request_orig(uri, method, body, headers,
                                   redirections, connection_type)

      if resp.status == 401:
        logger.info('Refreshing due to a 401')
        self._refresh(request_orig)
        self.apply(headers)
        return request_orig(uri, method, body, headers,
                            redirections, connection_type)
      else:
        return (resp, content)

    # Replace the request method with our own closure.
    http.request = new_request

    # Set credentials as a property of the request method.
    setattr(http.request, 'credentials', self)

    return http

  def refresh(self, http):
    """Forces a refresh of the access_token.

    Args:
      http: httplib2.Http, an http object to be used to make the refresh
        request.
    """
    self._refresh(http.request)

  def apply(self, headers):
    """Add the authorization to the headers.

    Args:
      headers: dict, the headers to add the Authorization header to.
    """
    headers['Authorization'] = 'Bearer ' + self.access_token

  def to_json(self):
    return self._to_json(Credentials.NON_SERIALIZED_MEMBERS)

  def from_json(cls, s):
    """Instantiate a Credentials object from a JSON description of it. The JSON
    should have been produced by calling .to_json() on the object.

    Args:
      data: dict, A deserialized JSON object.

    Returns:
      An instance of a Credentials subclass.
    """
    data = simplejson.loads(s)
    if 'token_expiry' in data and not isinstance(data['token_expiry'],
        datetime.datetime):
      try:
        data['token_expiry'] = datetime.datetime.strptime(
            data['token_expiry'], EXPIRY_FORMAT)
      except:
        data['token_expiry'] = None
    retval = OAuth2Credentials(
        data['access_token'],
        data['client_id'],
        data['client_secret'],
        data['refresh_token'],
        data['token_expiry'],
        data['token_uri'],
        data['user_agent'],
        data.get('id_token', None))
    retval.invalid = data['invalid']
    return retval
  
  from_json = classmethod(from_json)

  def access_token_expired(self):
    """True if the credential is expired or invalid.

    If the token_expiry isn't set, we assume the token doesn't expire.
    """
    if self.invalid:
      return True

    if not self.token_expiry:
      return False

    now = datetime.datetime.utcnow()
    if now >= self.token_expiry:
      logger.info('access_token is expired. Now: %s, token_expiry: %s',
                  now, self.token_expiry)
      return True
    return False
  access_token_expired = property(access_token_expired)

  def set_store(self, store):
    """Set the Storage for the credential.

    Args:
      store: Storage, an implementation of Stroage object.
        This is needed to store the latest access_token if it
        has expired and been refreshed.  This implementation uses
        locking to check for updates before updating the
        access_token.
    """
    self.store = store

  def _updateFromCredential(self, other):
    """Update this Credential from another instance."""
    self.__dict__.update(other.__getstate__())

  def __getstate__(self):
    """Trim the state down to something that can be pickled."""
    d = copy.copy(self.__dict__)
    del d['store']
    return d

  def __setstate__(self, state):
    """Reconstitute the state of the object from being pickled."""
    self.__dict__.update(state)
    self.store = None

  def _generate_refresh_request_body(self):
    """Generate the body that will be used in the refresh request."""
    body = urllib.urlencode({
        'grant_type': 'refresh_token',
        'client_id': self.client_id,
        'client_secret': self.client_secret,
        'refresh_token': self.refresh_token,
        })
    return body

  def _generate_refresh_request_headers(self):
    """Generate the headers that will be used in the refresh request."""
    headers = {
        'content-type': 'application/x-www-form-urlencoded',
    }

    if self.user_agent is not None:
      headers['user-agent'] = self.user_agent

    return headers

  def _refresh(self, http_request):
    """Refreshes the access_token.

    This method first checks by reading the Storage object if available.
    If a refresh is still needed, it holds the Storage lock until the
    refresh is completed.

    Args:
      http_request: callable, a callable that matches the method signature of
        httplib2.Http.request, used to make the refresh request.

    Raises:
      AccessTokenRefreshError: When the refresh fails.
    """
    if not self.store:
      self._do_refresh_request(http_request)
    else:
      self.store.acquire_lock()
      try:
        new_cred = self.store.locked_get()
        if (new_cred and not new_cred.invalid and
            new_cred.access_token != self.access_token):
          logger.info('Updated access_token read from Storage')
          self._updateFromCredential(new_cred)
        else:
          self._do_refresh_request(http_request)
      finally:
        self.store.release_lock()

  def _do_refresh_request(self, http_request):
    """Refresh the access_token using the refresh_token.

    Args:
      http_request: callable, a callable that matches the method signature of
        httplib2.Http.request, used to make the refresh request.

    Raises:
      AccessTokenRefreshError: When the refresh fails.
    """
    body = self._generate_refresh_request_body()
    headers = self._generate_refresh_request_headers()

    logger.info('Refreshing access_token')
    resp, content = http_request(
        self.token_uri, method='POST', body=body, headers=headers)
    if resp.status == 200:
      # TODO(jcgregorio) Raise an error if loads fails?
      d = simplejson.loads(content)
      self.access_token = d['access_token']
      self.refresh_token = d.get('refresh_token', self.refresh_token)
      if 'expires_in' in d:
        self.token_expiry = datetime.timedelta(
            seconds=int(d['expires_in'])) + datetime.datetime.utcnow()
      else:
        self.token_expiry = None
      if self.store:
        self.store.locked_put(self)
    else:
      # An {'error':...} response body means the token is expired or revoked,
      # so we flag the credentials as such.
      logger.info('Failed to retrieve access token: %s' % content)
      error_msg = 'Invalid response %s.' % resp['status']
      try:
        d = simplejson.loads(content)
        if 'error' in d:
          error_msg = d['error']
          self.invalid = True
          if self.store:
            self.store.locked_put(self)
      except:
        pass
      raise AccessTokenRefreshError(error_msg)


class AccessTokenCredentials(OAuth2Credentials):
  """Credentials object for OAuth 2.0.

  Credentials can be applied to an httplib2.Http object using the
  authorize() method, which then signs each request from that object
  with the OAuth 2.0 access token.  This set of credentials is for the
  use case where you have acquired an OAuth 2.0 access_token from
  another place such as a JavaScript client or another web
  application, and wish to use it from Python. Because only the
  access_token is present it can not be refreshed and will in time
  expire.

  AccessTokenCredentials objects may be safely pickled and unpickled.

  Usage:
    credentials = AccessTokenCredentials('<an access token>',
      'my-user-agent/1.0')
    http = httplib2.Http()
    http = credentials.authorize(http)

  Exceptions:
    AccessTokenCredentialsExpired: raised when the access_token expires or is
      revoked.
  """

  def __init__(self, access_token, user_agent):
    """Create an instance of OAuth2Credentials

    This is one of the few types if Credentials that you should contrust,
    Credentials objects are usually instantiated by a Flow.

    Args:
      access_token: string, access token.
      user_agent: string, The HTTP User-Agent to provide for this application.

    Notes:
      store: callable, a callable that when passed a Credential
        will store the credential back to where it came from.
    """
    super(AccessTokenCredentials, self).__init__(
        access_token,
        None,
        None,
        None,
        None,
        None,
        user_agent)

  def from_json(cls, s):
    data = simplejson.loads(s)
    retval = AccessTokenCredentials(
        data['access_token'],
        data['user_agent'])
    return retval
  from_json = classmethod(from_json)

  def _refresh(self, http_request):
    raise AccessTokenCredentialsError(
        "The access_token is expired or invalid and can't be refreshed.")


class AssertionCredentials(OAuth2Credentials):
  """Abstract Credentials object used for OAuth 2.0 assertion grants.

  This credential does not require a flow to instantiate because it
  represents a two legged flow, and therefore has all of the required
  information to generate and refresh its own access tokens.  It must
  be subclassed to generate the appropriate assertion string.

  AssertionCredentials objects may be safely pickled and unpickled.
  """

  def __init__(self, assertion_type, user_agent,
               token_uri='https://accounts.google.com/o/oauth2/token',
               **unused_kwargs):
    """Constructor for AssertionFlowCredentials.

    Args:
      assertion_type: string, assertion type that will be declared to the auth
          server
      user_agent: string, The HTTP User-Agent to provide for this application.
      token_uri: string, URI for token endpoint. For convenience
        defaults to Google's endpoints but any OAuth 2.0 provider can be used.
    """
    super(AssertionCredentials, self).__init__(
        None,
        None,
        None,
        None,
        None,
        token_uri,
        user_agent)
    self.assertion_type = assertion_type

  def _generate_refresh_request_body(self):
    assertion = self._generate_assertion()

    body = urllib.urlencode({
        'assertion_type': self.assertion_type,
        'assertion': assertion,
        'grant_type': 'assertion',
        })

    return body

  def _generate_assertion(self):
    """Generate the assertion string that will be used in the access token
    request.
    """
    _abstract()

if HAS_OPENSSL:
  # PyOpenSSL is not a prerequisite for oauth2client, so if it is missing then
  # don't create the SignedJwtAssertionCredentials or the verify_id_token()
  # method.

  class SignedJwtAssertionCredentials(AssertionCredentials):
    """Credentials object used for OAuth 2.0 Signed JWT assertion grants.

    This credential does not require a flow to instantiate because it
    represents a two legged flow, and therefore has all of the required
    information to generate and refresh its own access tokens.
    """

    MAX_TOKEN_LIFETIME_SECS = 3600 # 1 hour in seconds

    def __init__(self,
        service_account_name,
        private_key,
        scope,
        private_key_password='notasecret',
        user_agent=None,
        token_uri='https://accounts.google.com/o/oauth2/token',
        **kwargs):
      """Constructor for SignedJwtAssertionCredentials.

      Args:
        service_account_name: string, id for account, usually an email address.
        private_key: string, private key in P12 format.
        scope: string or list of strings, scope(s) of the credentials being
          requested.
        private_key_password: string, password for private_key.
        user_agent: string, HTTP User-Agent to provide for this application.
        token_uri: string, URI for token endpoint. For convenience
          defaults to Google's endpoints but any OAuth 2.0 provider can be used.
        kwargs: kwargs, Additional parameters to add to the JWT token, for
          example prn=joe@xample.org."""

      super(SignedJwtAssertionCredentials, self).__init__(
          'http://oauth.net/grant_type/jwt/1.0/bearer',
          user_agent,
          token_uri=token_uri,
          )

      if type(scope) is list:
        scope = ' '.join(scope)
      self.scope = scope

      self.private_key = private_key
      self.private_key_password = private_key_password
      self.service_account_name = service_account_name
      self.kwargs = kwargs

    def from_json(cls, s):
      data = simplejson.loads(s)
      retval = SignedJwtAssertionCredentials(
          data['service_account_name'],
          data['private_key'],
          data['private_key_password'],
          data['scope'],
          data['user_agent'],
          data['token_uri'],
          data['kwargs']
          )
      retval.invalid = data['invalid']
      return retval
    from_json = classmethod(from_json)

    def _generate_assertion(self):
      """Generate the assertion that will be used in the request."""
      now = long(time.time())
      payload = {
          'aud': self.token_uri,
          'scope': self.scope,
          'iat': now,
          'exp': now + SignedJwtAssertionCredentials.MAX_TOKEN_LIFETIME_SECS,
          'iss': self.service_account_name
      }
      payload.update(self.kwargs)
      logger.debug(str(payload))

      return make_signed_jwt(
          Signer.from_string(self.private_key, self.private_key_password),
          payload)

  # Only used in verify_id_token(), which is always calling to the same URI
  # for the certs.
  _cached_http = httplib2.Http(MemoryCache())

  def verify_id_token(id_token, audience, http=None,
      cert_uri=ID_TOKEN_VERIFICATON_CERTS):
    """Verifies a signed JWT id_token.

    Args:
      id_token: string, A Signed JWT.
      audience: string, The audience 'aud' that the token should be for.
      http: httplib2.Http, instance to use to make the HTTP request. Callers
        should supply an instance that has caching enabled.
      cert_uri: string, URI of the certificates in JSON format to
        verify the JWT against.

    Returns:
      The deserialized JSON in the JWT.

    Raises:
      oauth2client.crypt.AppIdentityError if the JWT fails to verify.
    """
    if http is None:
      http = _cached_http

    resp, content = http.request(cert_uri)

    if resp.status == 200:
      certs = simplejson.loads(content)
      return verify_signed_jwt_with_certs(id_token, certs, audience)
    else:
      raise VerifyJwtTokenError('Status code: %d' % resp.status)


def _urlsafe_b64decode(b64string):
  # Guard against unicode strings, which base64 can't handle.
  b64string = b64string.encode('ascii')
  padded = b64string + '=' * (4 - len(b64string) % 4)
  return base64.urlsafe_b64decode(padded)


def _extract_id_token(id_token):
  """Extract the JSON payload from a JWT.

  Does the extraction w/o checking the signature.

  Args:
    id_token: string, OAuth 2.0 id_token.

  Returns:
    object, The deserialized JSON payload.
  """
  segments = id_token.split('.')

  if (len(segments) != 3):
    raise VerifyJwtTokenError(
      'Wrong number of segments in token: %s' % id_token)

  return simplejson.loads(_urlsafe_b64decode(segments[1]))

def credentials_from_code(client_id, client_secret, scope, code,
                        redirect_uri = 'postmessage',
                        http=None, user_agent=None,
                        token_uri='https://accounts.google.com/o/oauth2/token'):
  """Exchanges an authorization code for an OAuth2Credentials object.

  Args:
    client_id: string, client identifier.
    client_secret: string, client secret.
    scope: string or list of strings, scope(s) to request.
    code: string, An authroization code, most likely passed down from
      the client
    redirect_uri: string, this is generally set to 'postmessage' to match the
      redirect_uri that the client specified
    http: httplib2.Http, optional http instance to use to do the fetch
    token_uri: string, URI for token endpoint. For convenience
      defaults to Google's endpoints but any OAuth 2.0 provider can be used.
  Returns:
    An OAuth2Credentials object.

  Raises:
    FlowExchangeError if the authorization code cannot be exchanged for an
     access token
  """
  flow = OAuth2WebServerFlow(client_id, client_secret, scope, user_agent,
                             'https://accounts.google.com/o/oauth2/auth',
                             token_uri)

  # We primarily make this call to set up the redirect_uri in the flow object
  uriThatWeDontReallyUse = flow.step1_get_authorize_url(redirect_uri)
  credentials = flow.step2_exchange(code, http)
  return credentials


def credentials_from_clientsecrets_and_code(filename, scope, code,
                                            message = None,
                                            redirect_uri = 'postmessage',
                                            http=None):
  """Returns OAuth2Credentials from a clientsecrets file and an auth code.

  Will create the right kind of Flow based on the contents of the clientsecrets
  file or will raise InvalidClientSecretsError for unknown types of Flows.

  Args:
    filename: string, File name of clientsecrets.
    scope: string or list of strings, scope(s) to request.
    code: string, An authroization code, most likely passed down from
      the client
    message: string, A friendly string to display to the user if the
      clientsecrets file is missing or invalid. If message is provided then
      sys.exit will be called in the case of an error. If message in not
      provided then clientsecrets.InvalidClientSecretsError will be raised.
    redirect_uri: string, this is generally set to 'postmessage' to match the
      redirect_uri that the client specified
    http: httplib2.Http, optional http instance to use to do the fetch

  Returns:
    An OAuth2Credentials object.

  Raises:
    FlowExchangeError if the authorization code cannot be exchanged for an
     access token
    UnknownClientSecretsFlowError if the file describes an unknown kind of Flow.
    clientsecrets.InvalidClientSecretsError if the clientsecrets file is
      invalid.
  """
  flow = flow_from_clientsecrets(filename, scope, message)
  # We primarily make this call to set up the redirect_uri in the flow object
  uriThatWeDontReallyUse = flow.step1_get_authorize_url(redirect_uri)
  credentials = flow.step2_exchange(code, http)
  return credentials


class OAuth2WebServerFlow(Flow):
  """Does the Web Server Flow for OAuth 2.0.

  OAuth2Credentials objects may be safely pickled and unpickled.
  """

  def __init__(self, client_id, client_secret, scope, user_agent=None,
               auth_uri='https://accounts.google.com/o/oauth2/auth',
               token_uri='https://accounts.google.com/o/oauth2/token',
               **kwargs):
    """Constructor for OAuth2WebServerFlow.

    Args:
      client_id: string, client identifier.
      client_secret: string client secret.
      scope: string or list of strings, scope(s) of the credentials being
        requested.
      user_agent: string, HTTP User-Agent to provide for this application.
      auth_uri: string, URI for authorization endpoint. For convenience
        defaults to Google's endpoints but any OAuth 2.0 provider can be used.
      token_uri: string, URI for token endpoint. For convenience
        defaults to Google's endpoints but any OAuth 2.0 provider can be used.
      **kwargs: dict, The keyword arguments are all optional and required
                        parameters for the OAuth calls.
    """
    self.client_id = client_id
    self.client_secret = client_secret
    if type(scope) is list:
      scope = ' '.join(scope)
    self.scope = scope
    self.user_agent = user_agent
    self.auth_uri = auth_uri
    self.token_uri = token_uri
    self.params = {
        'access_type': 'offline',
        }
    self.params.update(kwargs)
    self.redirect_uri = None

  def step1_get_authorize_url(self, redirect_uri=OOB_CALLBACK_URN):
    """Returns a URI to redirect to the provider.

    Args:
      redirect_uri: string, Either the string 'urn:ietf:wg:oauth:2.0:oob' for
          a non-web-based application, or a URI that handles the callback from
          the authorization server.

    If redirect_uri is 'urn:ietf:wg:oauth:2.0:oob' then pass in the
    generated verification code to step2_exchange,
    otherwise pass in the query parameters received
    at the callback uri to step2_exchange.
    """

    self.redirect_uri = redirect_uri
    query = {
        'response_type': 'code',
        'client_id': self.client_id,
        'redirect_uri': redirect_uri,
        'scope': self.scope,
        }
    query.update(self.params)
    parts = list(urlparse.urlparse(self.auth_uri))
    query.update(dict(parse_qsl(parts[4]))) # 4 is the index of the query part
    parts[4] = urllib.urlencode(query)
    return urlparse.urlunparse(parts)

  def step2_exchange(self, code, http=None):
    """Exhanges a code for OAuth2Credentials.

    Args:
      code: string or dict, either the code as a string, or a dictionary
        of the query parameters to the redirect_uri, which contains
        the code.
      http: httplib2.Http, optional http instance to use to do the fetch

    Returns:
      An OAuth2Credentials object that can be used to authorize requests.

    Raises:
      FlowExchangeError if a problem occured exchanging the code for a
      refresh_token.
    """

    if not (isinstance(code, str) or isinstance(code, unicode)):
      if 'code' not in code:
        if 'error' in code:
          error_msg = code['error']
        else:
          error_msg = 'No code was supplied in the query parameters.'
        raise FlowExchangeError(error_msg)
      else:
        code = code['code']

    body = urllib.urlencode({
        'grant_type': 'authorization_code',
        'client_id': self.client_id,
        'client_secret': self.client_secret,
        'code': code,
        'redirect_uri': self.redirect_uri,
        'scope': self.scope,
        })
    headers = {
        'content-type': 'application/x-www-form-urlencoded',
    }

    if self.user_agent is not None:
      headers['user-agent'] = self.user_agent

    if http is None:
      http = httplib2.Http()

    resp, content = http.request(self.token_uri, method='POST', body=body,
                                 headers=headers)
    if resp.status == 200:
      # TODO(jcgregorio) Raise an error if simplejson.loads fails?
      d = simplejson.loads(content)
      access_token = d['access_token']
      refresh_token = d.get('refresh_token', None)
      token_expiry = None
      if 'expires_in' in d:
        token_expiry = datetime.datetime.utcnow() + datetime.timedelta(
            seconds=int(d['expires_in']))

      if 'id_token' in d:
        d['id_token'] = _extract_id_token(d['id_token'])

      logger.debug('Successfully retrieved access token: %s' % content)
      return OAuth2Credentials(access_token, self.client_id,
                               self.client_secret, refresh_token, token_expiry,
                               self.token_uri, self.user_agent,
                               id_token=d.get('id_token', None))
    else:
      logger.debug('Failed to retrieve access token: %s' % content)
      error_msg = 'Invalid response %s.' % resp['status']
      try:
        d = simplejson.loads(content)
        if 'error' in d:
          error_msg = d['error']
      except:
        pass

      raise FlowExchangeError(error_msg)

def flow_from_clientsecrets(filename, scope, message=None):
  """Create a Flow from a clientsecrets file.

  Will create the right kind of Flow based on the contents of the clientsecrets
  file or will raise InvalidClientSecretsError for unknown types of Flows.

  Args:
    filename: string, File name of client secrets.
    scope: string or list of strings, scope(s) to request.
    message: string, A friendly string to display to the user if the
      clientsecrets file is missing or invalid. If message is provided then
      sys.exit will be called in the case of an error. If message in not
      provided then clientsecrets.InvalidClientSecretsError will be raised.

  Returns:
    A Flow object.

  Raises:
    UnknownClientSecretsFlowError if the file describes an unknown kind of Flow.
    clientsecrets.InvalidClientSecretsError if the clientsecrets file is
      invalid.
  """
  try:
    client_type, client_info = clientsecrets.loadfile(filename)
    if client_type in [clientsecrets.TYPE_WEB, clientsecrets.TYPE_INSTALLED]:
        return OAuth2WebServerFlow(
            client_info['client_id'],
            client_info['client_secret'],
            scope,
            None, # user_agent
            client_info['auth_uri'],
            client_info['token_uri'])
  except clientsecrets.InvalidClientSecretsError:
    if message:
      sys.exit(message)
    else:
      raise
  else:
    raise UnknownClientSecretsFlowError(
        'This OAuth 2.0 flow is unsupported: "%s"' * client_type)

########NEW FILE########
__FILENAME__ = clientsecrets
# Copyright (C) 2011 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utilities for reading OAuth 2.0 client secret files.

A client_secrets.json file contains all the information needed to interact with
an OAuth 2.0 protected service.
"""

__author__ = 'jcgregorio@google.com (Joe Gregorio)'


from anyjson import simplejson

# Properties that make a client_secrets.json file valid.
TYPE_WEB = 'web'
TYPE_INSTALLED = 'installed'

VALID_CLIENT = {
    TYPE_WEB: {
        'required': [
            'client_id',
            'client_secret',
            'redirect_uris',
            'auth_uri',
            'token_uri'],
        'string': [
            'client_id',
            'client_secret'
            ]
        },
    TYPE_INSTALLED: {
        'required': [
            'client_id',
            'client_secret',
            'redirect_uris',
            'auth_uri',
            'token_uri'],
        'string': [
            'client_id',
            'client_secret'
            ]
      }
    }

class Error(Exception):
  """Base error for this module."""
  pass


class InvalidClientSecretsError(Error):
  """Format of ClientSecrets file is invalid."""
  pass


def _validate_clientsecrets(obj):
  if obj is None or len(obj) != 1:
    raise InvalidClientSecretsError('Invalid file format.')
  client_type = obj.keys()[0]
  if client_type not in VALID_CLIENT.keys():
    raise InvalidClientSecretsError('Unknown client type: %s.' % client_type)
  client_info = obj[client_type]
  for prop_name in VALID_CLIENT[client_type]['required']:
    if prop_name not in client_info:
      raise InvalidClientSecretsError(
        'Missing property "%s" in a client type of "%s".' % (prop_name,
                                                           client_type))
  for prop_name in VALID_CLIENT[client_type]['string']:
    if client_info[prop_name].startswith('[['):
      raise InvalidClientSecretsError(
        'Property "%s" is not configured.' % prop_name)
  return client_type, client_info


def load(fp):
  obj = simplejson.load(fp)
  return _validate_clientsecrets(obj)


def loads(s):
  obj = simplejson.loads(s)
  return _validate_clientsecrets(obj)


def loadfile(filename):
  try:
    fp = file(filename, 'r')
    try:
      obj = simplejson.load(fp)
    finally:
      fp.close()
  except IOError:
    raise InvalidClientSecretsError('File not found: "%s"' % filename)
  return _validate_clientsecrets(obj)

########NEW FILE########
__FILENAME__ = crypt
# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import base64
import hashlib
import logging
import time

from OpenSSL import crypto
from anyjson import simplejson


CLOCK_SKEW_SECS = 300  # 5 minutes in seconds
AUTH_TOKEN_LIFETIME_SECS = 300  # 5 minutes in seconds
MAX_TOKEN_LIFETIME_SECS = 86400  # 1 day in seconds


class AppIdentityError(Exception):
  pass


class Verifier(object):
  """Verifies the signature on a message."""

  def __init__(self, pubkey):
    """Constructor.

    Args:
      pubkey, OpenSSL.crypto.PKey, The public key to verify with.
    """
    self._pubkey = pubkey

  def verify(self, message, signature):
    """Verifies a message against a signature.

    Args:
      message: string, The message to verify.
      signature: string, The signature on the message.

    Returns:
      True if message was singed by the private key associated with the public
      key that this object was constructed with.
    """
    try:
      crypto.verify(self._pubkey, signature, message, 'sha256')
      return True
    except:
      return False

  def from_string(key_pem, is_x509_cert):
    """Construct a Verified instance from a string.

    Args:
      key_pem: string, public key in PEM format.
      is_x509_cert: bool, True if key_pem is an X509 cert, otherwise it is
        expected to be an RSA key in PEM format.

    Returns:
      Verifier instance.

    Raises:
      OpenSSL.crypto.Error if the key_pem can't be parsed.
    """
    if is_x509_cert:
      pubkey = crypto.load_certificate(crypto.FILETYPE_PEM, key_pem)
    else:
      pubkey = crypto.load_privatekey(crypto.FILETYPE_PEM, key_pem)
    return Verifier(pubkey)
  from_string = staticmethod(from_string)


class Signer(object):
  """Signs messages with a private key."""

  def __init__(self, pkey):
    """Constructor.

    Args:
      pkey, OpenSSL.crypto.PKey, The private key to sign with.
    """
    self._key = pkey

  def sign(self, message):
    """Signs a message.

    Args:
      message: string, Message to be signed.

    Returns:
      string, The signature of the message for the given key.
    """
    return crypto.sign(self._key, message, 'sha256')

  def from_string(key, password='notasecret'):
    """Construct a Signer instance from a string.

    Args:
      key: string, private key in P12 format.
      password: string, password for the private key file.

    Returns:
      Signer instance.

    Raises:
      OpenSSL.crypto.Error if the key can't be parsed.
    """
    pkey = crypto.load_pkcs12(key, password).get_privatekey()
    return Signer(pkey)
  from_string = staticmethod(from_string)


def _urlsafe_b64encode(raw_bytes):
  return base64.urlsafe_b64encode(raw_bytes).rstrip('=')


def _urlsafe_b64decode(b64string):
  # Guard against unicode strings, which base64 can't handle.
  b64string = b64string.encode('ascii')
  padded = b64string + '=' * (4 - len(b64string) % 4)
  return base64.urlsafe_b64decode(padded)


def _json_encode(data):
  return simplejson.dumps(data, separators = (',', ':'))


def make_signed_jwt(signer, payload):
  """Make a signed JWT.

  See http://self-issued.info/docs/draft-jones-json-web-token.html.

  Args:
    signer: crypt.Signer, Cryptographic signer.
    payload: dict, Dictionary of data to convert to JSON and then sign.

  Returns:
    string, The JWT for the payload.
  """
  header = {'typ': 'JWT', 'alg': 'RS256'}

  segments = [
          _urlsafe_b64encode(_json_encode(header)),
          _urlsafe_b64encode(_json_encode(payload)),
  ]
  signing_input = '.'.join(segments)

  signature = signer.sign(signing_input)
  segments.append(_urlsafe_b64encode(signature))

  logging.debug(str(segments))

  return '.'.join(segments)


def verify_signed_jwt_with_certs(jwt, certs, audience):
  """Verify a JWT against public certs.

  See http://self-issued.info/docs/draft-jones-json-web-token.html.

  Args:
    jwt: string, A JWT.
    certs: dict, Dictionary where values of public keys in PEM format.
    audience: string, The audience, 'aud', that this JWT should contain. If
      None then the JWT's 'aud' parameter is not verified.

  Returns:
    dict, The deserialized JSON payload in the JWT.

  Raises:
    AppIdentityError if any checks are failed.
  """
  segments = jwt.split('.')

  if (len(segments) != 3):
    raise AppIdentityError(
      'Wrong number of segments in token: %s' % jwt)
  signed = '%s.%s' % (segments[0], segments[1])

  signature = _urlsafe_b64decode(segments[2])

  # Parse token.
  json_body = _urlsafe_b64decode(segments[1])
  try:
    parsed = simplejson.loads(json_body)
  except:
    raise AppIdentityError('Can\'t parse token: %s' % json_body)

  # Check signature.
  verified = False
  for (keyname, pem) in certs.items():
    verifier = Verifier.from_string(pem, True)
    if (verifier.verify(signed, signature)):
      verified = True
      break
  if not verified:
    raise AppIdentityError('Invalid token signature: %s' % jwt)

  # Check creation timestamp.
  iat = parsed.get('iat')
  if iat is None:
    raise AppIdentityError('No iat field in token: %s' % json_body)
  earliest = iat - CLOCK_SKEW_SECS

  # Check expiration timestamp.
  now = long(time.time())
  exp = parsed.get('exp')
  if exp is None:
    raise AppIdentityError('No exp field in token: %s' % json_body)
  if exp >= now + MAX_TOKEN_LIFETIME_SECS:
    raise AppIdentityError(
      'exp field too far in future: %s' % json_body)
  latest = exp + CLOCK_SKEW_SECS

  if now < earliest:
    raise AppIdentityError('Token used too early, %d < %d: %s' %
      (now, earliest, json_body))
  if now > latest:
    raise AppIdentityError('Token used too late, %d > %d: %s' %
      (now, latest, json_body))

  # Check audience.
  if audience is not None:
    aud = parsed.get('aud')
    if aud is None:
      raise AppIdentityError('No aud field in token: %s' % json_body)
    if aud != audience:
      raise AppIdentityError('Wrong recipient, %s != %s: %s' %
          (aud, audience, json_body))

  return parsed

########NEW FILE########
__FILENAME__ = locked_file
# Copyright 2011 Google Inc. All Rights Reserved.

"""Locked file interface that should work on Unix and Windows pythons.

This module first tries to use fcntl locking to ensure serialized access
to a file, then falls back on a lock file if that is unavialable.

Usage:
    f = LockedFile('filename', 'r+b', 'rb')
    f.open_and_lock()
    if f.is_locked():
      print 'Acquired filename with r+b mode'
      f.file_handle().write('locked data')
    else:
      print 'Aquired filename with rb mode'
    f.unlock_and_close()
"""

__author__ = 'cache@google.com (David T McWherter)'

import errno
import logging
import os
import time

logger = logging.getLogger(__name__)


class AlreadyLockedException(Exception):
  """Trying to lock a file that has already been locked by the LockedFile."""
  pass


class _Opener(object):
  """Base class for different locking primitives."""

  def __init__(self, filename, mode, fallback_mode):
    """Create an Opener.

    Args:
      filename: string, The pathname of the file.
      mode: string, The preferred mode to access the file with.
      fallback_mode: string, The mode to use if locking fails.
    """
    self._locked = False
    self._filename = filename
    self._mode = mode
    self._fallback_mode = fallback_mode
    self._fh = None

  def is_locked(self):
    """Was the file locked."""
    return self._locked

  def file_handle(self):
    """The file handle to the file.  Valid only after opened."""
    return self._fh

  def filename(self):
    """The filename that is being locked."""
    return self._filename

  def open_and_lock(self, timeout, delay):
    """Open the file and lock it.

    Args:
      timeout: float, How long to try to lock for.
      delay: float, How long to wait between retries.
    """
    pass

  def unlock_and_close(self):
    """Unlock and close the file."""
    pass


class _PosixOpener(_Opener):
  """Lock files using Posix advisory lock files."""

  def open_and_lock(self, timeout, delay):
    """Open the file and lock it.

    Tries to create a .lock file next to the file we're trying to open.

    Args:
      timeout: float, How long to try to lock for.
      delay: float, How long to wait between retries.

    Raises:
      AlreadyLockedException: if the lock is already acquired.
      IOError: if the open fails.
    """
    if self._locked:
      raise AlreadyLockedException('File %s is already locked' %
                                   self._filename)
    self._locked = False

    try:
      self._fh = open(self._filename, self._mode)
    except IOError, e:
      # If we can't access with _mode, try _fallback_mode and don't lock.
      if e.errno == errno.EACCES:
        self._fh = open(self._filename, self._fallback_mode)
        return

    lock_filename = self._posix_lockfile(self._filename)
    start_time = time.time()
    while True:
      try:
        self._lock_fd = os.open(lock_filename,
                                os.O_CREAT|os.O_EXCL|os.O_RDWR)
        self._locked = True
        break

      except OSError, e:
        if e.errno != errno.EEXIST:
          raise
        if (time.time() - start_time) >= timeout:
          logger.warn('Could not acquire lock %s in %s seconds' % (
              lock_filename, timeout))
          # Close the file and open in fallback_mode.
          if self._fh:
            self._fh.close()
          self._fh = open(self._filename, self._fallback_mode)
          return
        time.sleep(delay)

  def unlock_and_close(self):
    """Unlock a file by removing the .lock file, and close the handle."""
    if self._locked:
      lock_filename = self._posix_lockfile(self._filename)
      os.unlink(lock_filename)
      os.close(self._lock_fd)
      self._locked = False
      self._lock_fd = None
    if self._fh:
      self._fh.close()

  def _posix_lockfile(self, filename):
    """The name of the lock file to use for posix locking."""
    return '%s.lock' % filename


try:
  import fcntl

  class _FcntlOpener(_Opener):
    """Open, lock, and unlock a file using fcntl.lockf."""

    def open_and_lock(self, timeout, delay):
      """Open the file and lock it.

      Args:
        timeout: float, How long to try to lock for.
        delay: float, How long to wait between retries

      Raises:
        AlreadyLockedException: if the lock is already acquired.
        IOError: if the open fails.
      """
      if self._locked:
        raise AlreadyLockedException('File %s is already locked' %
                                     self._filename)
      start_time = time.time()

      try:
        self._fh = open(self._filename, self._mode)
      except IOError, e:
        # If we can't access with _mode, try _fallback_mode and don't lock.
        if e.errno == errno.EACCES or e.errno == errno.EPERM:
          self._fh = open(self._filename, self._fallback_mode)
          return

      # We opened in _mode, try to lock the file.
      while True:
        try:
          fcntl.lockf(self._fh.fileno(), fcntl.LOCK_EX)
          self._locked = True
          return
        except IOError, e:
          # If not retrying, then just pass on the error.
          if timeout == 0:
            raise e
          if e.errno != errno.EACCES:
            raise e
          # We could not acquire the lock.  Try again.
          if (time.time() - start_time) >= timeout:
            logger.warn('Could not lock %s in %s seconds' % (
                self._filename, timeout))
            if self._fh:
              self._fh.close()
            self._fh = open(self._filename, self._fallback_mode)
            return
          time.sleep(delay)

    def unlock_and_close(self):
      """Close and unlock the file using the fcntl.lockf primitive."""
      if self._locked:
        fcntl.lockf(self._fh.fileno(), fcntl.LOCK_UN)
      self._locked = False
      if self._fh:
        self._fh.close()
except ImportError:
  _FcntlOpener = None


try:
  import pywintypes
  import win32con
  import win32file

  class _Win32Opener(_Opener):
    """Open, lock, and unlock a file using windows primitives."""

    # Error #33:
    #  'The process cannot access the file because another process'
    FILE_IN_USE_ERROR = 33

    # Error #158:
    #  'The segment is already unlocked.'
    FILE_ALREADY_UNLOCKED_ERROR = 158

    def open_and_lock(self, timeout, delay):
      """Open the file and lock it.

      Args:
        timeout: float, How long to try to lock for.
        delay: float, How long to wait between retries

      Raises:
        AlreadyLockedException: if the lock is already acquired.
        IOError: if the open fails.
      """
      if self._locked:
        raise AlreadyLockedException('File %s is already locked' %
                                     self._filename)
      start_time = time.time()

      try:
        self._fh = open(self._filename, self._mode)
      except IOError, e:
        # If we can't access with _mode, try _fallback_mode and don't lock.
        if e.errno == errno.EACCES:
          self._fh = open(self._filename, self._fallback_mode)
          return

      # We opened in _mode, try to lock the file.
      while True:
        try:
          hfile = win32file._get_osfhandle(self._fh.fileno())
          win32file.LockFileEx(
              hfile,
              (win32con.LOCKFILE_FAIL_IMMEDIATELY|
               win32con.LOCKFILE_EXCLUSIVE_LOCK), 0, -0x10000,
              pywintypes.OVERLAPPED())
          self._locked = True
          return
        except pywintypes.error, e:
          if timeout == 0:
            raise e

          # If the error is not that the file is already in use, raise.
          if e[0] != _Win32Opener.FILE_IN_USE_ERROR:
            raise

          # We could not acquire the lock.  Try again.
          if (time.time() - start_time) >= timeout:
            logger.warn('Could not lock %s in %s seconds' % (
                self._filename, timeout))
            if self._fh:
              self._fh.close()
            self._fh = open(self._filename, self._fallback_mode)
            return
          time.sleep(delay)

    def unlock_and_close(self):
      """Close and unlock the file using the win32 primitive."""
      if self._locked:
        try:
          hfile = win32file._get_osfhandle(self._fh.fileno())
          win32file.UnlockFileEx(hfile, 0, -0x10000, pywintypes.OVERLAPPED())
        except pywintypes.error, e:
          if e[0] != _Win32Opener.FILE_ALREADY_UNLOCKED_ERROR:
            raise
      self._locked = False
      if self._fh:
        self._fh.close()
except ImportError:
  _Win32Opener = None


class LockedFile(object):
  """Represent a file that has exclusive access."""

  def __init__(self, filename, mode, fallback_mode, use_native_locking=True):
    """Construct a LockedFile.

    Args:
      filename: string, The path of the file to open.
      mode: string, The mode to try to open the file with.
      fallback_mode: string, The mode to use if locking fails.
      use_native_locking: bool, Whether or not fcntl/win32 locking is used.
    """
    opener = None
    if not opener and use_native_locking:
      if _Win32Opener:
        opener = _Win32Opener(filename, mode, fallback_mode)
      if _FcntlOpener:
        opener = _FcntlOpener(filename, mode, fallback_mode)

    if not opener:
      opener = _PosixOpener(filename, mode, fallback_mode)

    self._opener = opener

  def filename(self):
    """Return the filename we were constructed with."""
    return self._opener._filename

  def file_handle(self):
    """Return the file_handle to the opened file."""
    return self._opener.file_handle()

  def is_locked(self):
    """Return whether we successfully locked the file."""
    return self._opener.is_locked()

  def open_and_lock(self, timeout=0, delay=0.05):
    """Open the file, trying to lock it.

    Args:
      timeout: float, The number of seconds to try to acquire the lock.
      delay: float, The number of seconds to wait between retry attempts.

    Raises:
      AlreadyLockedException: if the lock is already acquired.
      IOError: if the open fails.
    """
    self._opener.open_and_lock(timeout, delay)

  def unlock_and_close(self):
    """Unlock and close a file."""
    self._opener.unlock_and_close()

########NEW FILE########
__FILENAME__ = multistore_file
# Copyright 2011 Google Inc. All Rights Reserved.

"""Multi-credential file store with lock support.

This module implements a JSON credential store where multiple
credentials can be stored in one file.  That file supports locking
both in a single process and across processes.

The credential themselves are keyed off of:
* client_id
* user_agent
* scope

The format of the stored data is like so:
{
  'file_version': 1,
  'data': [
    {
      'key': {
        'clientId': '<client id>',
        'userAgent': '<user agent>',
        'scope': '<scope>'
      },
      'credential': {
        # JSON serialized Credentials.
      }
    }
  ]
}
"""

__author__ = 'jbeda@google.com (Joe Beda)'

import base64
import errno
import logging
import os
import threading

from anyjson import simplejson
from client import Storage as BaseStorage
from client import Credentials
from locked_file import LockedFile

logger = logging.getLogger(__name__)

# A dict from 'filename'->_MultiStore instances
_multistores = {}
_multistores_lock = threading.Lock()


class Error(Exception):
  """Base error for this module."""
  pass


class NewerCredentialStoreError(Error):
  """The credential store is a newer version that supported."""
  pass


def get_credential_storage(filename, client_id, user_agent, scope,
                           warn_on_readonly=True):
  """Get a Storage instance for a credential.

  Args:
    filename: The JSON file storing a set of credentials
    client_id: The client_id for the credential
    user_agent: The user agent for the credential
    scope: string or list of strings, Scope(s) being requested
    warn_on_readonly: if True, log a warning if the store is readonly

  Returns:
    An object derived from client.Storage for getting/setting the
    credential.
  """
  filename = os.path.realpath(os.path.expanduser(filename))
  _multistores_lock.acquire()
  try:
    multistore = _multistores.setdefault(
        filename, _MultiStore(filename, warn_on_readonly))
  finally:
    _multistores_lock.release()
  if type(scope) is list:
    scope = ' '.join(scope)
  return multistore._get_storage(client_id, user_agent, scope)


class _MultiStore(object):
  """A file backed store for multiple credentials."""

  def __init__(self, filename, warn_on_readonly=True):
    """Initialize the class.

    This will create the file if necessary.
    """
    self._file = LockedFile(filename, 'r+b', 'rb')
    self._thread_lock = threading.Lock()
    self._read_only = False
    self._warn_on_readonly = warn_on_readonly

    self._create_file_if_needed()

    # Cache of deserialized store.  This is only valid after the
    # _MultiStore is locked or _refresh_data_cache is called.  This is
    # of the form of:
    #
    # (client_id, user_agent, scope) -> OAuth2Credential
    #
    # If this is None, then the store hasn't been read yet.
    self._data = None

  class _Storage(BaseStorage):
    """A Storage object that knows how to read/write a single credential."""

    def __init__(self, multistore, client_id, user_agent, scope):
      self._multistore = multistore
      self._client_id = client_id
      self._user_agent = user_agent
      self._scope = scope

    def acquire_lock(self):
      """Acquires any lock necessary to access this Storage.

      This lock is not reentrant.
      """
      self._multistore._lock()

    def release_lock(self):
      """Release the Storage lock.

      Trying to release a lock that isn't held will result in a
      RuntimeError.
      """
      self._multistore._unlock()

    def locked_get(self):
      """Retrieve credential.

      The Storage lock must be held when this is called.

      Returns:
        oauth2client.client.Credentials
      """
      credential = self._multistore._get_credential(
          self._client_id, self._user_agent, self._scope)
      if credential:
        credential.set_store(self)
      return credential

    def locked_put(self, credentials):
      """Write a credential.

      The Storage lock must be held when this is called.

      Args:
        credentials: Credentials, the credentials to store.
      """
      self._multistore._update_credential(credentials, self._scope)

    def locked_delete(self):
      """Delete a credential.

      The Storage lock must be held when this is called.

      Args:
        credentials: Credentials, the credentials to store.
      """
      return self._multistore._delete_credential(self._client_id, self._user_agent,
          self._scope)

  def _create_file_if_needed(self):
    """Create an empty file if necessary.

    This method will not initialize the file. Instead it implements a
    simple version of "touch" to ensure the file has been created.
    """
    if not os.path.exists(self._file.filename()):
      old_umask = os.umask(0177)
      try:
        open(self._file.filename(), 'a+b').close()
      finally:
        os.umask(old_umask)

  def _lock(self):
    """Lock the entire multistore."""
    self._thread_lock.acquire()
    self._file.open_and_lock()
    if not self._file.is_locked():
      self._read_only = True
      if self._warn_on_readonly:
        logger.warn('The credentials file (%s) is not writable. Opening in '
                    'read-only mode. Any refreshed credentials will only be '
                    'valid for this run.' % self._file.filename())
    if os.path.getsize(self._file.filename()) == 0:
      logger.debug('Initializing empty multistore file')
      # The multistore is empty so write out an empty file.
      self._data = {}
      self._write()
    elif not self._read_only or self._data is None:
      # Only refresh the data if we are read/write or we haven't
      # cached the data yet.  If we are readonly, we assume is isn't
      # changing out from under us and that we only have to read it
      # once.  This prevents us from whacking any new access keys that
      # we have cached in memory but were unable to write out.
      self._refresh_data_cache()

  def _unlock(self):
    """Release the lock on the multistore."""
    self._file.unlock_and_close()
    self._thread_lock.release()

  def _locked_json_read(self):
    """Get the raw content of the multistore file.

    The multistore must be locked when this is called.

    Returns:
      The contents of the multistore decoded as JSON.
    """
    assert self._thread_lock.locked()
    self._file.file_handle().seek(0)
    return simplejson.load(self._file.file_handle())

  def _locked_json_write(self, data):
    """Write a JSON serializable data structure to the multistore.

    The multistore must be locked when this is called.

    Args:
      data: The data to be serialized and written.
    """
    assert self._thread_lock.locked()
    if self._read_only:
      return False
    self._file.file_handle().seek(0)
    simplejson.dump(data, self._file.file_handle(), sort_keys=True, indent=2)
    return self._file.file_handle().truncate()

  def _refresh_data_cache(self):
    """Refresh the contents of the multistore.

    The multistore must be locked when this is called.

    Raises:
      NewerCredentialStoreError: Raised when a newer client has written the
        store.
    """
    self._data = {}
    try:
      raw_data = self._locked_json_read()
    except Exception:
      logger.warn('Credential data store could not be loaded. '
                  'Will ignore and overwrite.')
      return

    version = 0
    try:
      version = raw_data['file_version']
    except Exception:
      logger.warn('Missing version for credential data store. It may be '
                  'corrupt or an old version. Overwriting.')
    if version > 1:
      raise NewerCredentialStoreError(
          'Credential file has file_version of %d. '
          'Only file_version of 1 is supported.' % version)

    credentials = []
    try:
      credentials = raw_data['data']
    except (TypeError, KeyError):
      pass

    for cred_entry in credentials:
      try:
        (key, credential) = self._decode_credential_from_json(cred_entry)
        self._data[key] = credential
      except:
        # If something goes wrong loading a credential, just ignore it
        logger.info('Error decoding credential, skipping', exc_info=True)

  def _decode_credential_from_json(self, cred_entry):
    """Load a credential from our JSON serialization.

    Args:
      cred_entry: A dict entry from the data member of our format

    Returns:
      (key, cred) where the key is the key tuple and the cred is the
        OAuth2Credential object.
    """
    raw_key = cred_entry['key']
    client_id = raw_key['clientId']
    user_agent = raw_key['userAgent']
    scope = raw_key['scope']
    key = (client_id, user_agent, scope)
    credential = None
    credential = Credentials.new_from_json(simplejson.dumps(cred_entry['credential']))
    return (key, credential)

  def _write(self):
    """Write the cached data back out.

    The multistore must be locked.
    """
    raw_data = {'file_version': 1}
    raw_creds = []
    raw_data['data'] = raw_creds
    for (cred_key, cred) in self._data.items():
      raw_key = {
          'clientId': cred_key[0],
          'userAgent': cred_key[1],
          'scope': cred_key[2]
          }
      raw_cred = simplejson.loads(cred.to_json())
      raw_creds.append({'key': raw_key, 'credential': raw_cred})
    return self._locked_json_write(raw_data)

  def _get_credential(self, client_id, user_agent, scope):
    """Get a credential from the multistore.

    The multistore must be locked.

    Args:
      client_id: The client_id for the credential
      user_agent: The user agent for the credential
      scope: A string for the scope(s) being requested

    Returns:
      The credential specified or None if not present
    """
    key = (client_id, user_agent, scope)

    return self._data.get(key, None)

  def _update_credential(self, cred, scope):
    """Update a credential and write the multistore.

    This must be called when the multistore is locked.

    Args:
      cred: The OAuth2Credential to update/set
      scope: The scope(s) that this credential covers
    """
    key = (cred.client_id, cred.user_agent, scope)
    self._data[key] = cred
    self._write()

  def _delete_credential(self, client_id, user_agent, scope):
    """Delete a credential and write the multistore.

    This must be called when the multistore is locked.

    Args:
      client_id: The client_id for the credential
      user_agent: The user agent for the credential
      scope: The scope(s) that this credential covers
    """
    key = (client_id, user_agent, scope)
    try:
      del self._data[key]
    except KeyError:
      pass
    return self._write()

  def _get_storage(self, client_id, user_agent, scope):
    """Get a Storage object to get/set a credential.

    This Storage is a 'view' into the multistore.

    Args:
      client_id: The client_id for the credential
      user_agent: The user agent for the credential
      scope: A string for the scope(s) being requested

    Returns:
      A Storage object that can be used to get/set this cred
    """
    return self._Storage(self, client_id, user_agent, scope)

########NEW FILE########
__FILENAME__ = pre-commit
#! /bin/sh
"true" '''\'
if command -v python2 > /dev/null; then
  exec python2 "$0" "$@"
else
  exec python "$0" "$@"
fi
exit $?
'''

#    CUPS Cloudprint - Print via Google Cloud Print
#    Copyright (C) 2013 Simon Cadman
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

if __name__ == '__main__':  # pragma: no cover

    import fileinput
    import re
    import sys
    import glob
    import subprocess
    import os
    from datetime import datetime

    searchRegex = 'CCPVersion = "(\d)+ (\d){6}"'
    replaceValue = 'CCPVersion = "' + \
        datetime.utcnow().strftime('%Y%m%d %H%M%S') + '"'

    p = subprocess.Popen(
        ["git",
         "diff",
         "--cached",
         "--name-only"],
        stdout=subprocess.PIPE)
    output = p.communicate()[0]
    result = p.returncode
    if result != 0:
        sys.exit(result)
    files = output.split("\n")
    for file in files:
        if len(file) > 0 and os.path.exists(file):
            testfile = open(file, "r")
            fileNeedsUpdating = False
            for line in testfile:
                if '# line below is replaced on commit' in line:
                    fileNeedsUpdating = True
                    break
            testfile.close()

            if fileNeedsUpdating:
                replaceLine = False
                for line in fileinput.input(file, inplace=1):
                    if replaceLine:
                        line = re.sub(searchRegex, replaceValue, line)
                    if '# line below is replaced on commit' in line:
                        replaceLine = True
                    else:
                        replaceLine = False
                    sys.stdout.write(line)

                p = subprocess.Popen(
                    ["git",
                     "add",
                     file.lstrip('-')],
                    stdout=subprocess.PIPE)
                output = p.communicate()[0]
                result = p.returncode
                if result != 0:
                    sys.exit(result)

########NEW FILE########
__FILENAME__ = printer
#    CUPS Cloudprint - Print via Google Cloud Print
#    Copyright (C) 2011 Simon Cadman
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
import cups
import hashlib
import json
import locale
import logging
import mimetools
import os
import re
import urllib
import subprocess

from ccputils import Utils


class Printer(object):
    _PPD_TEMPLATE_HEAD = """*PPD-Adobe: "4.3"
*%%%%%%%% PPD file for Cloud Print with CUPS.
*FormatVersion: "4.3"
*FileVersion: "1.0"
*LanguageVersion: English
*LanguageEncoding: ISOLatin1
*cupsLanguages: \"%(language)s\"
*cupsFilter: "application/vnd.cups-postscript 100 -"
*cupsFilter: "application/vnd.cups-pdf 0 -"
*PCFileName: "ccp.ppd"
*Product: "(Google Cloud Print)"
*Manufacturer: "Google"
*ModelName: "Google Cloud Print"
*ShortNickName: "Google Cloud Print"
*NickName: "Google Cloud Print, 1.0"
*PSVersion: "(3010.000) 550"
*LanguageLevel: "3"
*ColorDevice: True
*DefaultColorSpace: RGB
*FileSystem: False
*Throughput: "1"
*LandscapeOrientation: Minus90
*TTRasterizer: Type42
*%% Driver-defined attributes...
*1284DeviceID: "MFG:GOOGLE;DRV:GCP;CMD:POSTSCRIPT;MDL:%(uri)s;"
*OpenUI *PageSize/Media Size: PickOne
*%(language)s.Translation PageSize/Media Size: ""
*OrderDependency: 10 AnySetup *PageSize
*DefaultPageSize: %(defaultpapertype)s.Fullbleed
*PageSize Letter.Fullbleed/US Letter: "<</PageSize[612 792]/ImagingBBox null>>setpagedevice"
*%(language)s.PageSize Letter.Fullbleed/US Letter: ""
*PageSize Legal.Fullbleed/US Legal: "<</PageSize[612 1008]/ImagingBBox null>>setpagedevice"
*%(language)s.PageSize Legal.Fullbleed/US Legal: ""
*PageSize A4.Fullbleed/A4: "<</PageSize[595 842]/ImagingBBox null>>setpagedevice"
*%(language)s.PageSize A4.Fullbleed/A4: ""
*CloseUI: *PageSize
*OpenUI *PageRegion/Page Region: PickOne
*%(language)s.Translation PageRegion/Page Region: ""
*OrderDependency: 10 AnySetup *PageRegion
*DefaultPageRegion: %(defaultpapertype)s.Fullbleed
*PageRegion Letter.Fullbleed/US Letter: "<</PageSize[612 792]/ImagingBBox null>>setpagedevice"
*%(language)s.PageRegion Letter.Fullbleed/US Letter: ""
*PageRegion Legal.Fullbleed/US Legal: "<</PageSize[612 1008]/ImagingBBox null>>setpagedevice"
*%(language)s.PageRegion Legal.Fullbleed/US Legal: ""
*PageRegion A4.Fullbleed/A4: "<</PageSize[595 842]/ImagingBBox null>>setpagedevice"
*%(language)s.PageRegion A4.Fullbleed/A4: ""
*CloseUI: *PageRegion
*DefaultImageableArea: %(defaultpapertype)s.Fullbleed
*ImageableArea Letter.Fullbleed/US Letter: "0 0 612 792"
*ImageableArea Legal.Fullbleed/US Legal: "0 0 612 1008"
*ImageableArea A4.Fullbleed/A4: "0 0 595 842"
*DefaultPaperDimension: %(defaultpapertype)s.Fullbleed
*PaperDimension Letter.Fullbleed/US Letter: "612 792"
*PaperDimension Legal.Fullbleed/US Legal: "612 1008"
*PaperDimension A4.Fullbleed/A4: "595 842"
"""

    _PPD_TEMPLATE_FOOT = """*DefaultFont: Courier
*Font AvantGarde-Book: Standard "(1.05)" Standard ROM
*Font AvantGarde-BookOblique: Standard "(1.05)" Standard ROM
*Font AvantGarde-Demi: Standard "(1.05)" Standard ROM
*Font AvantGarde-DemiOblique: Standard "(1.05)" Standard ROM
*Font Bookman-Demi: Standard "(1.05)" Standard ROM
*Font Bookman-DemiItalic: Standard "(1.05)" Standard ROM
*Font Bookman-Light: Standard "(1.05)" Standard ROM
*Font Bookman-LightItalic: Standard "(1.05)" Standard ROM
*Font Courier: Standard "(1.05)" Standard ROM
*Font Courier-Bold: Standard "(1.05)" Standard ROM
*Font Courier-BoldOblique: Standard "(1.05)" Standard ROM
*Font Courier-Oblique: Standard "(1.05)" Standard ROM
*Font Helvetica: Standard "(1.05)" Standard ROM
*Font Helvetica-Bold: Standard "(1.05)" Standard ROM
*Font Helvetica-BoldOblique: Standard "(1.05)" Standard ROM
*Font Helvetica-Narrow: Standard "(1.05)" Standard ROM
*Font Helvetica-Narrow-Bold: Standard "(1.05)" Standard ROM
*Font Helvetica-Narrow-BoldOblique: Standard "(1.05)" Standard ROM
*Font Helvetica-Narrow-Oblique: Standard "(1.05)" Standard ROM
*Font Helvetica-Oblique: Standard "(1.05)" Standard ROM
*Font NewCenturySchlbk-Bold: Standard "(1.05)" Standard ROM
*Font NewCenturySchlbk-BoldItalic: Standard "(1.05)" Standard ROM
*Font NewCenturySchlbk-Italic: Standard "(1.05)" Standard ROM
*Font NewCenturySchlbk-Roman: Standard "(1.05)" Standard ROM
*Font Palatino-Bold: Standard "(1.05)" Standard ROM
*Font Palatino-BoldItalic: Standard "(1.05)" Standard ROM
*Font Palatino-Italic: Standard "(1.05)" Standard ROM
*Font Palatino-Roman: Standard "(1.05)" Standard ROM
*Font Symbol: Special "(001.005)" Special ROM
*Font Times-Bold: Standard "(1.05)" Standard ROM
*Font Times-BoldItalic: Standard "(1.05)" Standard ROM
*Font Times-Italic: Standard "(1.05)" Standard ROM
*Font Times-Roman: Standard "(1.05)" Standard ROM
*Font ZapfChancery-MediumItalic: Standard "(1.05)" Standard ROM
*Font ZapfDingbats: Special "(001.005)" Special ROM
*% End of cloudprint.ppd, 04169 bytes."""

    _PROTOCOL = 'cloudprint://'
    _BACKEND_DESCRIPTION =\
        'network %s "%s" "%s" "MFG:Google;MDL:Cloud Print;DES:GoogleCloudPrint;"'
    _BACKEND_DESCRIPTION_PLUS_LOCATION =\
        'network %s "%s" "%s" "MFG:Google;MDL:Cloud Print;DES:GoogleCloudPrint;" "%s"'

    _DEVICE_DESCRIPTION = '"%s" en "Google" "%s (%s)" "MFG:GOOGLE;DRV:GCP;CMD:POSTSCRIPT;MDL:%s;"'
    
    _PPD_NAME = 'cupscloudprint:%s:%s.ppd'

    _RESERVED_CAPABILITY_WORDS = set((
        'Duplex', 'Resolution', 'Attribute', 'Choice', 'ColorDevice', 'ColorModel', 'ColorProfile',
        'Copyright', 'CustomMedia', 'Cutter', 'Darkness', 'DriverType', 'FileName', 'Filter',
        'Filter', 'Finishing', 'Font', 'Group', 'HWMargins', 'InputSlot', 'Installable',
        'LocAttribute', 'ManualCopies', 'Manufacturer', 'MaxSize', 'MediaSize', 'MediaType',
        'MinSize', 'ModelName', 'ModelNumber', 'Option', 'PCFileName', 'SimpleColorProfile',
        'Throughput', 'UIConstraints', 'VariablePaperSize', 'Version', 'Color', 'Background',
        'Stamp', 'DestinationColorProfile'
    ))

    _CONVERTCOMMAND = 'convert'

    def __init__(self, fields, requestor):
        self._fields = fields
        self._requestor = requestor

    def getAccount(self):
        return self._requestor.getAccount()

    def getRequestor(self):
        return self._requestor

    def _getMimeBoundary(self):
        if not hasattr(self, '_mime_boundary'):
            self._mime_boundary = mimetools.choose_boundary()
        return self._mime_boundary

    def __getitem__(self, key):
        if key == 'capabilities' and key not in self._fields:
            self._fields = self._fetchDetails()
            if key not in self._fields:
                # Make sure to only fetch details once.
                self._fields[key] = None

        return self._fields[key]

    def __contains__(self, key):
        return key in self._fields

    def _fetchDetails(self):
        responseobj = self._requestor.printer(self['id'])
        return responseobj['printers'][0]

    def getURI(self):
        """Generates a URI for the Cloud Print Printer.

        Returns:
          URI for the printer
        """
        account = urllib.quote(self.getAccount().encode('ascii', 'replace'))
        printer_id = urllib.quote(self['id'].encode('ascii', 'replace'))
        return "%s%s/%s" % (self._PROTOCOL, account, printer_id)

    def getListDescription(self):
        return '%s - %s - %s' % (
            self.getDisplayName().encode('ascii', 'replace'), self.getURI(), self.getAccount())

    def getLocation(self):
        """Gets the location of the printer, or '' if location not available."""

        # Look for hints of a location tag.
        if 'tags' in self:
            for tag in self['tags']:
                if '=' not in tag:
                    continue
                key, value = tag.split('=', 1)
                if 'location' in key:
                    return value

        return ''

    def getCUPSBackendDescription(self):
        display_name = self.getDisplayName()

        location = self.getLocation()
        if location:
            name_and_location = '%s (%s)' % (display_name, location)
            return self._BACKEND_DESCRIPTION_PLUS_LOCATION %\
                (self.getURI(), display_name, name_and_location, location)
        else:
            return self._BACKEND_DESCRIPTION % (self.getURI(), display_name, display_name)

    def getCUPSDriverDescription(self):
        name = self.getDisplayName().encode('ascii', 'replace')
        return self._DEVICE_DESCRIPTION % (
                self.getPPDName(), name, self.getAccount(), self.getURI())

    def getDisplayName(self):
        """Gets a name that carbon-based lifeforms can read.

        For example, "HP LaserJet 2000", not "HP_LaserJet-2000".

        Returns:
          A name that makes sense when displayed to a non-technical user
        """

        if 'displayName' in self and self['displayName']:
            return self['displayName']
        else:
            return self['name']

    def getPPDName(self):
        return self._PPD_NAME % (
            self.getAccount().encode('ascii', 'replace').replace(' ', '-'),
            self['id'].encode('ascii', 'replace').replace(' ', '-'))

    def generatePPD(self):
        """Generates a PPD string for this printer."""
        defaultlocale = locale.getdefaultlocale()
        language = Utils.GetLanguage(defaultlocale)
        defaultpapertype = Utils.GetDefaultPaperType(defaultlocale)
        ppd = self._PPD_TEMPLATE_HEAD % \
            {'language': language, 'defaultpapertype': defaultpapertype, 'uri': self.getURI()}
        if self['capabilities'] is not None:
            addedCapabilities = []
            for capability in self['capabilities']:
                originCapabilityName = None
                internalCapabilityName = \
                    self._getInternalName(capability, 'capability', None, addedCapabilities)
                addedCapabilities.append(internalCapabilityName)
                if 'displayName' in capability and len(capability['displayName']) > 0:
                    originCapabilityName = self._sanitizeText(capability['displayName'])
                elif 'psk:DisplayName' in capability and len(capability['psk:DisplayName']) > 0:
                    originCapabilityName = self._sanitizeText(capability['psk:DisplayName'])
                else:
                    originCapabilityName = self._sanitizeText(capability['name'])
                if capability['type'] == 'Feature':
                    ppd += '*OpenUI *%s/%s: PickOne\n' % \
                        (internalCapabilityName, internalCapabilityName)
                    # translation of capability, allows use of 8
                    # bit chars
                    ppd += '*%s.Translation %s/%s: ""\n' % \
                        (language, internalCapabilityName, originCapabilityName)
                    addedOptions = []
                    for option in capability['options']:
                        originOptionName = None
                        if 'displayName' in option and len(option['displayName']) > 0:
                            originOptionName = self._sanitizeText(option['displayName'])
                        elif 'psk:DisplayName' in option and len(option['psk:DisplayName']) > 0:
                            originOptionName = self._sanitizeText(option['psk:DisplayName'])
                        else:
                            originOptionName = self._sanitizeText(option['name'])
                        internalOptionName = self._getInternalName(
                            option, 'option', capability['name'], addedOptions)
                        addedOptions.append(internalOptionName)
                        if 'default' in option and option['default']:
                            ppd += '*Default%s: %s\n' % (internalCapabilityName, internalOptionName)
                        ppd += '*%s %s:%s\n' % \
                            (internalCapabilityName, internalOptionName, internalOptionName)
                        # translation of option, allows use of 8
                        # bit chars
                        value = ''
                        if 'ppd:value' in option:
                            value = option['ppd:value']
                        ppd += '*%s.%s %s/%s: "%s"\n' % (
                            language, internalCapabilityName, internalOptionName, originOptionName,
                            value)

                    ppd += '*CloseUI: *%s\n' % internalCapabilityName

        ppd += self._PPD_TEMPLATE_FOOT
        return ppd

    @staticmethod
    def _sanitizeText(text):
        return re.sub(r'(:|;| )', '_', text).replace('/', '-').encode('utf8', 'ignore')

    @staticmethod
    def _getInternalName(details, internalType, capabilityName=None, existingList=[]):
        returnValue = None
        fixedNameMap = {}

        # use fixed options for options we recognise
        if internalType == "option":
            # option
            if capabilityName == "psk:JobDuplexAllDocumentsContiguously":
                fixedNameMap['psk:OneSided'] = "None"
                fixedNameMap['psk:TwoSidedShortEdge'] = "DuplexTumble"
                fixedNameMap['psk:TwoSidedLongEdge'] = "DuplexNoTumble"
            if capabilityName == "psk:PageOrientation":
                fixedNameMap['psk:Landscape'] = "Landscape"
                fixedNameMap['psk:Portrait'] = "Portrait"
        else:
            # capability
            fixedNameMap['ns1:Colors'] = "ColorModel"
            fixedNameMap['ns1:PrintQualities'] = "OutputMode"
            fixedNameMap['ns1:InputBins'] = "InputSlot"
            fixedNameMap['psk:JobDuplexAllDocumentsContiguously'] = "Duplex"
            fixedNameMap['psk:PageOrientation'] = "Orientation"

        for itemName in fixedNameMap:
            if details['name'] == itemName:
                returnValue = fixedNameMap[itemName]
                break

        if 'displayName' in details and len(details['displayName']) > 0:
            name = details['displayName']
        elif 'psk:DisplayName' in details and len(details['psk:DisplayName']) > 0:
            name = details['psk:DisplayName']
        else:
            name = details['name']

        sanitisedName = Printer._sanitizeText(name)

        if sanitisedName in Printer._RESERVED_CAPABILITY_WORDS:
            sanitisedName = 'GCP_' + sanitisedName

        # only sanitise, no hash
        if returnValue is None and\
                len(sanitisedName) <= 30 and\
                sanitisedName.decode("utf-8", 'ignore').encode("ascii", "ignore") == sanitisedName:
            returnValue = sanitisedName

        if returnValue is None:
            returnValue = hashlib.sha256(sanitisedName).hexdigest()[:7]

        if returnValue not in existingList:
            return returnValue

        origReturnValue = returnValue

        if "GCP_" + origReturnValue not in existingList:
            return "GCP_" + origReturnValue

        # max 100 rotations, prevent infinite loop
        for i in range(1, 100):
            if returnValue in existingList:
                returnValue = "GCP_" + str(i) + "_" + origReturnValue

        # TODO: need to error if limit hit, or run out of chars allowed etc

        return returnValue

    def _encodeMultiPart(self, fields, file_type='application/xml'):
        """Encodes list of parameters for HTTP multipart format.

        Args:
          fields: list of tuples containing name and value of parameters.
          file_type: string if file type different than application/xml.
        Returns:
          A string to be sent as data for the HTTP post request.
        """
        lines = []
        for (key, value) in fields:
            lines.append('--' + self._getMimeBoundary())
            lines.append('Content-Disposition: form-data; name="%s"' % key)
            lines.append('')  # blank line
            lines.append(str(value))
        lines.append('--%s--' % self._getMimeBoundary())
        lines.append('')  # blank line
        return '\r\n'.join(lines)

    @staticmethod
    def _getOverrideCapabilities(overrideoptionsstring):
        overrideoptions = overrideoptionsstring.split(' ')
        overridecapabilities = {}

        ignorecapabilities = ['Orientation']
        for optiontext in overrideoptions:
            if '=' in optiontext:
                optionparts = optiontext.split('=')
                option = optionparts[0]
                if option in ignorecapabilities:
                    continue

                value = optionparts[1]
                overridecapabilities[option] = value

            # landscape
            if optiontext == 'landscape' or optiontext == 'nolandscape':
                overridecapabilities['Orientation'] = 'Landscape'

        return overridecapabilities

    @staticmethod
    def _getCapabilitiesDict(attrs, printercapabilities, overridecapabilities):
        capabilities = {"capabilities": []}
        for attr in attrs:
            if attr['name'].startswith('Default'):
                # gcp setting, reverse back to GCP capability
                gcpname = None
                hashname = attr['name'].replace('Default', '')

                # find item name from hashes
                gcpoption = None
                addedCapabilities = []
                for capability in printercapabilities:
                    if hashname == Printer._getInternalName(capability, 'capability'):
                        gcpname = capability['name']
                        for option in capability['options']:
                            internalCapability = Printer._getInternalName(
                                option, 'option', gcpname, addedCapabilities)
                            addedCapabilities.append(internalCapability)
                            if attr['value'] == internalCapability:
                                gcpoption = option['name']
                                break
                        addedOptions = []
                        for overridecapability in overridecapabilities:
                            if 'Default' + overridecapability == attr['name']:
                                selectedoption = overridecapabilities[
                                    overridecapability]
                                for option in capability['options']:
                                    internalOption = Printer._getInternalName(
                                        option, 'option', gcpname, addedOptions)
                                    addedOptions.append(internalOption)
                                    if selectedoption == internalOption:
                                        gcpoption = option['name']
                                        break
                                break
                        break

                # hardcoded to feature type temporarily
                if gcpname is not None and gcpoption is not None:
                    capabilities['capabilities'].append(
                        {'type': 'Feature', 'name': gcpname, 'options': [{'name': gcpoption}]})
        return capabilities

    @staticmethod
    def _attrListToArray(attrs):
        return ({'name': attr.name, 'value': attr.value} for attr in attrs)

    def _getCapabilities(self, cupsprintername, overrideoptionsstring):
        """Gets capabilities of printer and maps them against list

        Args:
          overrideoptionsstring: override for print job
        Returns:
          List of capabilities
        """
        connection = cups.Connection()
        overridecapabilities = self._getOverrideCapabilities(overrideoptionsstring)
        overrideDefaultDefaults = {'Duplex': 'None'}

        for capability in overrideDefaultDefaults:
            if capability not in overridecapabilities:
                overridecapabilities[capability] = overrideDefaultDefaults[capability]
        attrs = cups.PPD(connection.getPPD(cupsprintername)).attributes
        attrArray = self._attrListToArray(attrs)
        return self._getCapabilitiesDict(attrArray, self['capabilities'], overridecapabilities)

    def submitJob(self, jobtype, jobfile, jobname, cupsprintername, options=""):
        """Submits a job to printerid with content of dataUrl.

        Args:
          jobtype: string, must match the dictionary keys in content and content_type.
          jobfile: string, points to source for job. Could be a pathname or id string.
          jobname: string, name of the print job ( usually page name ).
          options: string, key-value pair of options from print job.

        Returns:
          True if submitted, False otherwise
        """
        rotate = 0

        for optiontext in options.split(' '):

            # landscape
            if optiontext == 'landscape':
                # landscape
                rotate = 90

            # nolandscape - already rotates
            if optiontext == 'nolandscape':
                # rotate back
                rotate = 270

        if jobtype == 'pdf':
            if not os.path.exists(jobfile):
                print "ERROR: PDF doesnt exist"
                return False
            if rotate > 0:
                command = [self._CONVERTCOMMAND, '-density', '300x300', jobfile.lstrip('-'),
                           '-rotate', str(rotate), jobfile.lstrip('-')]
                p = subprocess.Popen(command, stdout=subprocess.PIPE)
                output = p.communicate()[0]
                result = p.returncode
                if result != 0:
                    print "ERROR: Failed to rotate PDF"
                    logging.error("Failed to rotate pdf: " + str(command))
                    logging.error(output)
                    return False
            b64file = Utils.Base64Encode(jobfile)
            if b64file is None:
                print "ERROR: Cannot write to file: " + jobfile + ".b64"
                return False
            fdata = Utils.ReadFile(b64file)
            os.unlink(b64file)
        elif jobtype in ['png', 'jpeg']:
            if not os.path.exists(jobfile):
                print "ERROR: File doesnt exist"
                return False
            fdata = Utils.ReadFile(jobfile)
        else:
            print "ERROR: Unknown job type"
            return False

        if jobname == "":
            title = "Untitled page"
        else:
            title = jobname

        content = {'pdf': fdata,
                   'jpeg': jobfile,
                   'png': jobfile,
                   }
        content_type = {'pdf': 'dataUrl',
                        'jpeg': 'image/jpeg',
                        'png': 'image/png',
                        }
        headers = [
            ('printerid', self['id']),
            ('title', title),
            ('content', content[jobtype]),
            ('contentType', content_type[jobtype]),
            ('capabilities', json.dumps(self._getCapabilities(cupsprintername, options)))
        ]
        logging.info('Capability headers are: %s', headers[4])
        data = self._encodeMultiPart(headers, content_type[jobtype])

        try:
            responseobj = self.getRequestor().submit(data, self._getMimeBoundary())
            if responseobj['success']:
                return True
            else:
                print 'ERROR: Error response from Cloud Print for type %s: %s' %\
                    (jobtype, responseobj['message'])
                return False

        except Exception as error_msg:
            print 'ERROR: Print job %s failed with %s' % (jobtype, error_msg)
            return False

########NEW FILE########
__FILENAME__ = printermanager
#    CUPS Cloudprint - Print via Google Cloud Print
#    Copyright (C) 2011 Simon Cadman
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
import cups
import json
import urllib
import os
import mimetools
import re
import hashlib
import subprocess
import logging
from auth import Auth
from urlparse import urlparse
from ccputils import Utils
from printer import Printer


class PrinterManager:
    BOUNDARY = mimetools.choose_boundary()
    CRLF = '\r\n'
    PROTOCOL = 'cloudprint://'
    requestors = None
    requestor = None
    cachedPrinterDetails = {}
    reservedCapabilityWords = set((
        'Duplex', 'Resolution', 'Attribute', 'Choice', 'ColorDevice', 'ColorModel', 'ColorProfile',
        'Copyright', 'CustomMedia', 'Cutter', 'Darkness', 'DriverType', 'FileName', 'Filter',
        'Filter', 'Finishing', 'Font', 'Group', 'HWMargins', 'InputSlot', 'Installable',
        'LocAttribute', 'ManualCopies', 'Manufacturer', 'MaxSize', 'MediaSize', 'MediaType',
        'MinSize', 'ModelName', 'ModelNumber', 'Option', 'PCFileName', 'SimpleColorProfile',
        'Throughput', 'UIConstraints', 'VariablePaperSize', 'Version', 'Color', 'Background',
        'Stamp', 'DestinationColorProfile'
    ))
    URIFormatLatest = 1
    URIFormat20140307 = 2
    URIFormat20140210 = 3
    backendDescription =\
        'network %s "%s" "Google Cloud Print" "MFG:Google;MDL:Cloud Print;DES:GoogleCloudPrint;"'

    def __init__(self, requestors):
        """Create an instance of PrinterManager, with authorised requestor

        Args:
          requestors: list or CloudPrintRequestor instance, A list of
          requestors, or a single requestor to use for all Cloud Print
          requests.
        """
        if requestors is not None:
            if isinstance(requestors, list):
                self.requestors = requestors
            else:
                self.requestors = [requestors]

    def getCUPSPrintersForAccount(self, account):
        connection = cups.Connection()
        cupsprinters = connection.getPrinters()
        accountPrinters = []
        for cupsprinter in cupsprinters:
            printer = self.getPrinterByURI(cupsprinters[cupsprinter]['device-uri'])
            if printer is not None:
                if printer.getAccount() == account:
                    accountPrinters.append(cupsprinters[cupsprinter])
        return accountPrinters, connection

    def getPrinter(self, printerId, accountName):
        """Fetch one printer, including capabilities.

        Args:
          printerId: something like e64b1063-80e7-a87e-496c-3caa8cb7d736
          accountName: email address (account) printer is associated with

        Returns:
          A Printer object, or None if printer not found."""

        for requestor in self.requestors:
            if accountName != requestor.getAccount():
                continue

            response = requestor.printer(printerId)
            if not response['success'] or 'printers' not in response or not response['printers']:
                break

            return Printer(response['printers'][0], requestor)

        return None

    def getPrinters(self, accountName=None):
        """Fetch a list of printers

        Returns:
          list: list of printers for the accounts.
        """
        if not hasattr(self, '_printers'):
            self._printers = []
            for requestor in self.requestors:
                if accountName is not None and accountName != requestor.getAccount():
                    continue

                responseobj = requestor.search()
                if 'printers' in responseobj:
                    for printer_info in responseobj['printers']:
                        self._printers.append(Printer(printer_info, requestor))

        return self._printers

    def sanitizePrinterName(self, name):
        """Sanitizes printer name for CUPS

        Args:
          name: string, name of printer from Google Cloud Print

        Returns:
          string: CUPS-friendly name for the printer
        """
        return re.sub('[^a-zA-Z0-9\-_]', '', name.encode('ascii', 'replace').replace(' ', '_'))

    def addPrinter(self, printername, printer, connection, ppd=None):
        """Adds a printer to CUPS

        Args:
          printername: string, name of the printer to add
          uri: string, uri of the Cloud Print device
          connection: connection, CUPS connection

        Returns:
          None
        """
        # fix printer name
        printername = self.sanitizePrinterName(printername)
        result = None
        printerppdname = None
        try:
            if ppd is None:
                printerppdname = printer.getPPDName()
            else:
                printerppdname = ppd
            location = printer.getLocation()
            if not location:
                location = 'Google Cloud Print'

            result = connection.addPrinter(
                name=printername, ppdname=printerppdname, info=printername,
                location=location, device=printer.getURI())
            connection.enablePrinter(printername)
            connection.acceptJobs(printername)
            connection.setPrinterShared(printername, False)
        except Exception as error:
            result = error
        if result is None:
            print "Added " + printername
            return True
        else:
            print "Error adding: " + printername, result
            return False

    @staticmethod
    def _getAccountNameAndPrinterIdFromURI(uri):
        splituri = uri.rsplit('/', 2)
        accountName = urllib.unquote(splituri[1])
        printerId = urllib.unquote(splituri[2])
        return accountName, printerId

    def parseLegacyURI(self, uristring, requestors):
        """Parses previous CUPS Cloud Print URIs, only used for upgrades

        Args:
          uristring: string, uri of the Cloud Print device

        Returns:
          string: account name
          string: google cloud print printer name
          string: google cloud print printer id
          int: format id
        """
        printerName = None
        accountName = None
        printerId = None
        uri = urlparse(uristring)
        pathparts = uri.path.strip('/').split('/')
        if len(pathparts) == 2:
            formatId = PrinterManager.URIFormat20140307
            printerId = urllib.unquote(pathparts[1])
            accountName = urllib.unquote(pathparts[0])
            printerName = urllib.unquote(uri.netloc)
        else:
            if urllib.unquote(uri.netloc) not in Auth.GetAccountNames(requestors):
                formatId = PrinterManager.URIFormat20140210
                printerName = urllib.unquote(uri.netloc)
                accountName = urllib.unquote(pathparts[0])
            else:
                formatId = PrinterManager.URIFormatLatest
                printerId = urllib.unquote(pathparts[0])
                printerName = None
                accountName = urllib.unquote(uri.netloc)

        return accountName, printerName, printerId, formatId

    def findRequestorForAccount(self, account):
        """Searches the requestors in the printer object for the requestor for a specific account

        Args:
          account: string, account name
        Return:
          requestor: Single requestor object for the account, or None if no account found
        """
        for requestor in self.requestors:
            if requestor.getAccount() == account:
                return requestor

    def getPrinterByURI(self, uri):
        accountName, printerId = self._getAccountNameAndPrinterIdFromURI(uri)
        return self.getPrinter(printerId, accountName)

    def getPrinterIDByDetails(self, account, printername, printerid):
        """Gets printer id and requestor by printer

        Args:
          uri: string, printer uri
        Return:
          printer id: Single requestor object for the account, or None if no account found
          requestor: Single requestor object for the account
        """
        # find requestor based on account
        requestor = self.findRequestorForAccount(urllib.unquote(account))
        if requestor is None:
            return None, None

        if printerid is not None:
            return printerid, requestor
        else:
            return None, None

########NEW FILE########
__FILENAME__ = refreshtokens
#! /bin/sh
"true" '''\'
if command -v python2 > /dev/null; then
  exec python2 "$0" "$@"
else
  exec python "$0" "$@"
fi
exit $?
'''

#    CUPS Cloudprint - Print via Google Cloud Print
#    Copyright (C) 2014 Simon Cadman
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

if __name__ == '__main__':  # pragma: no cover

    from auth import Auth
    from printermanager import PrinterManager
    from ccputils import Utils
    Utils.SetupLogging()

    # line below is replaced on commit
    CCPVersion = "20140501 203545"
    Utils.ShowVersion(CCPVersion)

    requestors, storage = Auth.SetupAuth(False)

########NEW FILE########
__FILENAME__ = reportissues
#! /bin/sh
"true" '''\'
if command -v python2 > /dev/null; then
  exec python2 "$0" "$@"
else
  exec python "$0" "$@"
fi
exit $?
'''

#    CUPS Cloudprint - Print via Google Cloud Print
#    Copyright (C) 2013 Simon Cadman
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

if __name__ == '__main__':  # pragma: no cover

    import sys
    import os
    import subprocess
    libpath = "/usr/local/share/cloudprint-cups/"
    if not os.path.exists(libpath):
        libpath = "/usr/share/cloudprint-cups"
    sys.path.insert(0, libpath)

    from auth import Auth
    from printermanager import PrinterManager
    from ccputils import Utils
    Utils.SetupLogging()

    # line below is replaced on commit
    CCPVersion = "20140521 163500"
    Utils.ShowVersion(CCPVersion)

    requestors, storage = Auth.SetupAuth(True)
    printer_manager = PrinterManager(requestors)
    printers = printer_manager.getPrinters()
    if printers is None:
        print "ERROR: No Printers Found"
        sys.exit(1)

    for printer in printers:
        print printer.getCUPSDriverDescription()
        ppdname = printer.getPPDName()
        p = subprocess.Popen(
            (os.path.join(libpath, 'dynamicppd.py'), 'cat', ppdname.lstrip('-')),
            stdout=subprocess.PIPE)
        ppddata = p.communicate()[0]
        result = p.returncode
        tempfile = open('/tmp/.ppdfile', 'w')
        tempfile.write(ppddata)
        tempfile.close()

        p = subprocess.Popen(['cupstestppd', '/tmp/.ppdfile'], stdout=subprocess.PIPE)
        testdata = p.communicate()[0]
        result = p.returncode
        print "Result of cupstestppd was " + str(result)
        print "".join(testdata)
        if result != 0:
            print "cupstestppd errored: "
            print ppddata
            print "\n"

        os.unlink('/tmp/.ppdfile')

########NEW FILE########
__FILENAME__ = listdrivefiles
#! /bin/sh
"true" '''\'
if command -v python2 > /dev/null; then
  exec python2 "$0" "$@"
else
  exec python "$0" "$@"
fi
exit $?
'''

#    CUPS Cloudprint - Print via Google Cloud Print
#    Copyright (C) 2011 Simon Cadman
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

def getDriveFiles(requestors):
    returnValue = []
    for requestor in requestors:
        responseobj = requestor.doRequest(
            'files', endpointurl="https://www.googleapis.com/drive/v2")
        if 'error' in responseobj:
            print "Errored fetching files from drive"
        else:
            for item in responseobj['items']:
                returnValue.append(item)
    if len(returnValue) == 0:
        return None
    return returnValue

if __name__ == '__main__':  # pragma: no cover
    import sys
    import logging
    sys.path.insert(0, ".")

    from auth import Auth
    from ccputils import Utils
    Utils.SetupLogging()

    # line below is replaced on commit
    CCPVersion = "20140501 203545"
    Utils.ShowVersion(CCPVersion)

    requestors, storage = Auth.SetupAuth(True,
        permissions=['https://www.googleapis.com/auth/cloudprint', 'https://www.googleapis.com/auth/drive.readonly'])
    files = getDriveFiles(requestors)
    if files is None:
        print "No Files Found"
        sys.exit(1)

    for drivefile in files:
        if len(sys.argv) == 2 and drivefile['title'] == sys.argv[1] + '.pdf':
            print drivefile['fileSize']
            sys.exit(0)
        elif len(sys.argv) != 2:
            print drivefile['title']

########NEW FILE########
__FILENAME__ = mockrequestor
#    CUPS Cloudprint - Print via Google Cloud Print
#    Copyright (C) 2011 Simon Cadman
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
import json
import urllib
import sys
sys.path.insert(0, ".")
from cloudprintrequestor import CloudPrintRequestor

class MockRequestor(CloudPrintRequestor):

    printers = []

    def mockSearch(self, path, headers, data, boundary):
        return json.dumps({'printers': self.printers})

    def mockSubmit(self, path, headers, data, boundary):
        if 'FAIL PAGE' in data:
            result = {
                'success': False,
                'message': 'FAIL PAGE was in message'}
        elif 'TEST PAGE WITH EXCEPTION' in data:
            raise Exception("Test exception")
        else:   
            result = {'success': True}
        return json.dumps(result)

    def mockPrinter(self, path, headers, data, boundary):
        printername = path.split('=')[1]
        foundPrinter = None
        for printer in self.printers:
            if printer['id'] == printername:
                foundPrinter = printer
                break

        if foundPrinter is None:
            return json.dumps(None)

        result = {'success' : True, 'printers': [foundPrinter]}
        return json.dumps(result)

    def doRequest(self, path, headers=None, data=None, boundary=None):
        if (path.startswith('search?')):
            return json.loads(self.mockSearch(path, headers, data, boundary))
        if (path.startswith('printer?')):
            return json.loads(self.mockPrinter(path, headers, data, boundary))
        if (path == 'submit'):
            return json.loads(self.mockSubmit(path, headers, data, boundary))
        return None

########NEW FILE########
__FILENAME__ = test_auth
#    CUPS Cloudprint - Print via Google Cloud Print
#    Copyright (C) 2011 Simon Cadman
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
import json
import urllib
import cups
import os
import stat
import grp
import pytest
import logging
import sys
sys.path.insert(0, ".")

from auth import Auth
from mockrequestor import MockRequestor
from oauth2client import client
from oauth2client import multistore_file
from ccputils import Utils


def setup_function(function):
    # setup mock requestors
    global requestors
    requestors = []

    # account without special chars
    mockRequestorInstance1 = MockRequestor()
    mockRequestorInstance1.setAccount('testaccount1')
    mockRequestorInstance1.printers = []
    requestors.append(mockRequestorInstance1)

    Auth.config = '/tmp/cloudprint.conf'


def teardown_function(function):
    if os.path.exists(Auth.config):
        os.unlink(Auth.config)
    logging.shutdown()
    reload(logging)


def test_fixConfigPermissions():
    configfile = open(Auth.config, "w")
    configfile.close()

    os.chmod(Auth.config, 0000)
    assert '0000' == oct(os.stat(Auth.config)[stat.ST_MODE])[-4:]
    assert True == Utils.FixFilePermissions(Auth.config)[0]
    assert '0660' == oct(os.stat(Auth.config)[stat.ST_MODE])[-4:]

    origconfig = Auth.config
    Auth.config = '/tmp/filethatdoesntexist'
    assert (False, False) == Utils.FixFilePermissions(Auth.config)
    Auth.config = origconfig


@pytest.mark.skipif(
    grp.getgrnam('lp').gr_gid not in (os.getgroups()) and os.getuid() != 0,
    reason="will only pass if running user part of lp group or root")
def test_fixConfigOwnerships():
    configfile = open(Auth.config, "w")
    configfile.close()

    assert Utils.GetLPID() != os.stat(Auth.config).st_gid
    assert True == Utils.FixFilePermissions(Auth.config)[1]
    assert Utils.GetLPID() == os.stat(Auth.config).st_gid


def test_setupAuth():
    testUserName = 'testaccount1'

    # create initial file
    assert os.path.exists(Auth.config) == False
    assert Auth.SetupAuth(False) == (False, False)
    assert os.path.exists(Auth.config) == True

    # ensure permissions are correct after creating config
    assert '0660' == oct(os.stat(Auth.config)[stat.ST_MODE])[-4:]

    # add dummy details
    storage = multistore_file.get_credential_storage(
        Auth.config,
        Auth.clientid,
        'testuseraccount',
        ['https://www.googleapis.com/auth/cloudprint'])

    credentials = client.OAuth2Credentials('test', Auth.clientid,
                                           'testsecret', 'testtoken', 1,
                                           'https://www.googleapis.com/auth/cloudprint', testUserName)
    storage.put(credentials)

    # ensure permissions are correct after populating config
    assert '0660' == oct(os.stat(Auth.config)[stat.ST_MODE])[-4:]

    # re-run to test getting credentials
    requestors, storage = Auth.SetupAuth(False)
    assert requestors is not None
    assert storage is not None

    # check deleting account
    assert Auth.DeleteAccount(testUserName) is None
    requestors, storage = Auth.SetupAuth(False)
    assert requestors == False
    assert storage == False

def test_setupAuthInteractive():
    
    # ensure running setup in interactive mode tries to read stdin
    with pytest.raises(IOError):
        Auth.SetupAuth(True)

def test_renewToken():
    global requestors
    storage = multistore_file.get_credential_storage(
        Auth.config,
        Auth.clientid,
        'testuseraccount',
        ['https://www.googleapis.com/auth/cloudprint'])
    
    credentials = client.OAuth2Credentials('test', Auth.clientid,
                                           'testsecret', 'testtoken', 1,
                                           'https://www.googleapis.com/auth/cloudprint', 'testaccount1')
    
    # test renewing token exits in non-interactive mode
    with pytest.raises(SystemExit):
        Auth.RenewToken(False, requestors[0], credentials,storage, 'test')
        
    # test renewing interactively tries to read from stdin
    with pytest.raises(IOError):
        assert Auth.RenewToken(True, requestors[0], credentials,storage, 'test') == False

@pytest.mark.skipif(
    grp.getgrnam('lp').gr_gid not in (os.getgroups()) and os.getuid() != 0,
    reason="will only pass if running user part of lp group or root")
def test_setupAuthOwnership():
    assert Auth.SetupAuth(False) == (False, False)

    # ensure ownership is correct after creating config
    assert Utils.GetLPID() == os.stat(Auth.config).st_gid

    # add dummy details
    storage = multistore_file.get_credential_storage(
        Auth.config,
        Auth.clientid,
        'testuseraccount',
        ['https://www.googleapis.com/auth/cloudprint'])

    credentials = client.OAuth2Credentials('test', Auth.clientid,
                                           'testsecret', 'testtoken', 1,
                                           'https://www.googleapis.com/auth/cloudprint', 'testaccount1')
    storage.put(credentials)

    # ensure ownership is correct after populating config
    assert Utils.GetLPID() == os.stat(Auth.config).st_gid

########NEW FILE########
__FILENAME__ = test_ccputils
#    CUPS Cloudprint - Print via Google Cloud Print
#    Copyright (C) 2011 Simon Cadman
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
import os
import logging
import sys
import pytest
sys.path.insert(0, ".")

from ccputils import Utils

def teardown_function(function):
    logging.shutdown()
    reload(logging)

def test_SetupLogging():
    testLogFile = '/tmp/testccp.log'
    assert os.path.exists(testLogFile) == False
    assert Utils.SetupLogging(testLogFile) == True
    logging.error('test_setupLogging error test')
    assert os.path.exists(testLogFile) == True
    os.unlink(testLogFile)

def test_SetupLoggingDefault():
    testLogFile = '/tmp/testccp.log'
    assert os.path.exists(testLogFile) == False
    Utils.logpath = testLogFile
    assert Utils.SetupLogging() == True
    logging.error('test_setupLogging error test')
    assert os.path.exists(testLogFile) == True
    os.unlink(testLogFile)

def test_SetupLoggingFails():
    testLogFile = '/tmp/dirthatdoesntexist/testccp.log'
    assert os.path.exists(testLogFile) == False
    assert Utils.SetupLogging(testLogFile) == False
    assert os.path.exists(testLogFile) == False

def test_fileIsPDFFails():
    assert Utils.fileIsPDF('testing/testfiles/NotPdf.txt') == False

def test_fileIsPDFSucceeds():
    assert Utils.fileIsPDF('testing/testfiles/Test Page.pdf') == True

def test_fileIsPDFErrors():
    assert Utils.fileIsPDF("-dsadsa") == False

def test_whichFails():
    assert Utils.which('dsaph9oaghd9ahdsadsadsadsadasd') is None

def test_whichSucceeds():
    assert Utils.which(
        'bash') in (
        '/bin/bash',
        '/usr/bin/bash',
        '/usr/sbin/bash')

def test_isExeSucceeds():
    if os.path.exists('/usr/bin/sh'):
        assert Utils.is_exe("/usr/bin/sh") == True
    else:
        assert Utils.is_exe("/bin/sh") == True


def test_isExeFails():
    assert Utils.is_exe("/dev/null") == False


def test_getLPID():
    assert int(Utils.GetLPID()) > 0
    assert Utils.GetLPID() is not None

    import grp

    workingPrintGroupName = 'lp'
    try:
        grp.getgrnam(workingPrintGroupName)
    except:
        workingPrintGroupName = 'cups'
        pass

    assert Utils.GetLPID('brokendefault', 'brokenalternative', False) is None
    assert int(
        Utils.GetLPID(
            'brokendefault',
            workingPrintGroupName,
            False)) > 0
    assert Utils.GetLPID(
        'brokendefault',
        workingPrintGroupName,
        False) is not None

    # test blacklist works
    assert Utils.GetLPID(
        workingPrintGroupName,
        'brokenalternative',
        True,
        [workingPrintGroupName,
         'brokendefault',
         'adm',
         'wheel',
         'root'],
        True) is None

def test_showVersion():
    assert Utils.ShowVersion("12345") == False
    sys.argv = ['testfile', 'version']
    with pytest.raises(SystemExit):
        Utils.ShowVersion("12345")

def test_readFile():
    Utils.WriteFile('/tmp/testfile', 'data')
    assert Utils.ReadFile('/tmp/testfile') == 'data'
    assert Utils.ReadFile('/tmp/filethatdoesntexist') is None
    os.unlink('/tmp/testfile')

def test_writeFile():
    Utils.WriteFile('/tmp/testfile', 'data') == True
    Utils.WriteFile('/tmp/testfile/dsadsaasd', 'data') == False
    os.unlink('/tmp/testfile')

def test_base64encode():
    Utils.WriteFile('/tmp/testfile', 'data') == True
    assert Utils.Base64Encode('/tmp/testfile') == '/tmp/testfile.b64'
    assert Utils.ReadFile(
        '/tmp/testfile.b64') == 'data:application/octet-stream;base64,ZGF0YQ=='
    os.unlink('/tmp/testfile.b64')

    os.mkdir('/tmp/testfile.b64')
    assert Utils.Base64Encode('/tmp/testfile') is None
    os.unlink('/tmp/testfile')
    os.rmdir('/tmp/testfile.b64')

    assert Utils.Base64Encode('/tmp/testfile/dsiahdisa') is None

def test_GetLanguage():
    assert Utils.GetLanguage(['en_GB',]) == "en"
    assert Utils.GetLanguage(['en_US',]) == "en"
    assert Utils.GetLanguage(['fr_CA',]) == "fr"
    assert Utils.GetLanguage(['fr_FR',]) == "fr"
    assert Utils.GetLanguage(['it_IT',]) == "it"
    assert Utils.GetLanguage(['en',]) == "en"
    assert Utils.GetLanguage([None,None]) == "en"
    
def test_GetDefaultPaperType():
    assert Utils.GetDefaultPaperType(['en_GB',]) == "A4"
    assert Utils.GetDefaultPaperType(['en_US',]) == "Letter"
    assert Utils.GetDefaultPaperType([None,None]) == "Letter"
########NEW FILE########
__FILENAME__ = test_cloudprintrequestor
#    CUPS Cloudprint - Print via Google Cloud Print
#    Copyright (C) 2011 Simon Cadman
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
import json
import pytest
import logging
import sys
sys.path.insert(0, ".")

from cloudprintrequestor import CloudPrintRequestor

global requestor


def teardown_function(function):
    logging.shutdown()
    reload(logging)


def setup_function(function):
    global requestor
    requestor = CloudPrintRequestor()


def test_requestor():
    global requestor
    requestor.setAccount('testdetails')
    assert requestor.getAccount() == 'testdetails'


def test_request():
    global requestor
    assert requestor.doRequest(
        path="test",
        testResponse=json.dumps("randomstring1233")) == "randomstring1233"
    with pytest.raises(ValueError):
        assert requestor.doRequest(path="test", testResponse="")

    assert requestor.doRequest(
        path="test",
        testResponse=json.dumps("randomstring1233"),
        endpointurl=requestor.CLOUDPRINT_URL) == "randomstring1233"
    with pytest.raises(ValueError):
        assert requestor.doRequest(
            path="test",
            testResponse="",
            endpointurl=requestor.CLOUDPRINT_URL)

    # test doing actual requests, not supplying test reponse data
    # we expect them to fail due to missing auth data
    with pytest.raises(ValueError):
        requestor.doRequest(path="printers")
    with pytest.raises(ValueError):
        requestor.doRequest(path="submit", data="test")
    
########NEW FILE########
__FILENAME__ = test_printer
#    CUPS Cloudprint - Print via Google Cloud Print
#    Copyright (C) 2011 Simon Cadman
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
import cups
import urllib
import logging
import sys
import subprocess
import os
import pytest
sys.path.insert(0, ".")
from printermanager import PrinterManager
from mockrequestor import MockRequestor
from ccputils import Utils

global printers, printerManagerInstance

testCapabilities1 = [{'name': 'ns1:Colors',
                      'displayName' : 'Colors',
                      'type': 'Feature',
                      'options' : 
                      [{'default': True, 'name': 'test', 'displayName' : 'testdisplay'}, {'name': 'test2'}] },
                     {'name': 'ns1:Size',
                      'psk:DisplayName' : 'Size',
                      'type': 'Feature',
                      'options' : 
                      [{'default': True, 'name': 'big', 'psk:DisplayName' : 'testdisplay big'}, {'name': 'small'}] },
                     {'name': 'ns1:Something',
                      'type': 'Feature',
                      'options' : 
                      [{'default': True, 'name': 'one'}, {'name': 'two', 'ppd:value' : 'testval'}] },
                     {'name': 'ns1:TestReservedWord',
                      'type': 'Feature',
                      'options' : 
                      [{'default': True, 'name': 'Resolution'}, {'name': 'two', 'ppd:value' : 'testval'}] },
                     {'name': 'ns1:TestReservedWord',
                      'type': 'Feature',
                      'options' : 
                      [{'default': True, 'name': 'Resolution'}, {'name': 'two', 'ppd:value' : 'testval'}] },
                     {'name': 'ns1:TestReservedWord',
                      'type': 'Feature',
                      'options' : 
                      [{'default': True, 'name': 'Resolution'}, {'name': 'two', 'ppd:value' : 'testval'}] }]

def setup_function(function):
    # setup mock requestors
    global printers, printerManagerInstance

    mockRequestorInstance = MockRequestor()
    mockRequestorInstance.setAccount('testaccount2@gmail.com')
    mockRequestorInstance.printers = [{'name': 'Save to Google Drive',
                                        'id': '__test_save_docs',
                                        'capabilities': testCapabilities1},
                                      {'name': 'Save to Google Drive 2',
                                       'displayName' : 'Save to Google Drive 2 DisplayName',
                                        'id': '__test_save_docs_2' },
                                     ]
                                        
    printerManagerInstance = PrinterManager(mockRequestorInstance)
    printers = printerManagerInstance.getPrinters()

def teardown_function(function):
    global requestors
    requestors = None
    logging.shutdown()
    reload(logging)

def test_getAccount():
    global printers
    for printer in printers:
        assert printer.getAccount() == "testaccount2@gmail.com"
    
def test_getRequestor():
    global printers
    for printer in printers:
        requestor = printer.getRequestor()
        assert requestor.__class__.__name__ == "MockRequestor"
        assert requestor.getAccount() == 'testaccount2@gmail.com'

def test_getMimeBoundary():
    global printers
    for printer in printers:
        assert printer._getMimeBoundary() != 'test_boundry'
        assert len(printer._getMimeBoundary()) > 30
        assert len(printer._getMimeBoundary()) < 50
        
        printer._mime_boundary = 'test_boundry'
        assert printer._getMimeBoundary() == 'test_boundry'
        
def test_getCapabilitiesItems():
    global printers
    printer = printers[0]
    correctCapabilities = testCapabilities1
    assert printer._fields['capabilities'] == correctCapabilities
    assert printer._fields['capabilities'] == printer['capabilities']
    del printer._fields['capabilities']
    assert 'capabilities' not in printer._fields
    assert printer['capabilities'] == correctCapabilities
    assert printer._fields['capabilities'] == printer['capabilities']
    
def test_getCapabilitiesItemsMissing():
    global printers
    printer = printers[1]
    assert 'capabilities' not in printer._fields
    assert printer['capabilities'] == None
    
def test_contains():
    global printers
    for printer in printers:
        assert 'testvalue' not in printer
        printer._fields['testvalue'] = 'test'
        assert 'testvalue' in printer
        del printer._fields['testvalue']
        assert 'testvalue' not in printer

def test_fetchDetails():
    global printers
    assert printers[0]._fetchDetails() == {'name': 'Save to Google Drive', 
                                           'id': '__test_save_docs',
                                            'capabilities': testCapabilities1}
    assert printers[1]._fetchDetails() == {'displayName' : 'Save to Google Drive 2 DisplayName', 'id': '__test_save_docs_2', 'name': 'Save to Google Drive 2'}
    
def test_getURI():
    global printers
    assert printers[0].getURI() == "cloudprint://testaccount2%40gmail.com/__test_save_docs"
    assert printers[1].getURI() == "cloudprint://testaccount2%40gmail.com/__test_save_docs_2"
    
def test_getDisplayName():
    global printers
    assert printers[0].getDisplayName() == "Save to Google Drive"
    assert printers[1].getDisplayName() == "Save to Google Drive 2 DisplayName"
    
def test_getListDescription():
    global printers
    assert printers[0].getListDescription() == "Save to Google Drive - cloudprint://testaccount2%40gmail.com/__test_save_docs - testaccount2@gmail.com"
    assert printers[1].getListDescription() == "Save to Google Drive 2 DisplayName - cloudprint://testaccount2%40gmail.com/__test_save_docs_2 - testaccount2@gmail.com"
    
def test_getCUPSBackendDescription():
    global printers
    assert printers[0].getCUPSBackendDescription() == 'network cloudprint://testaccount2%40gmail.com/__test_save_docs "Save to Google Drive" "Save to Google Drive" "MFG:Google;MDL:Cloud Print;DES:GoogleCloudPrint;"'
    assert printers[1].getCUPSBackendDescription() == 'network cloudprint://testaccount2%40gmail.com/__test_save_docs_2 "Save to Google Drive 2 DisplayName" "Save to Google Drive 2 DisplayName" "MFG:Google;MDL:Cloud Print;DES:GoogleCloudPrint;"'
    
def test_getCUPSDriverDescription():
    global printers
    assert printers[0].getCUPSDriverDescription() == '"cupscloudprint:testaccount2@gmail.com:__test_save_docs.ppd" en "Google" "Save to Google Drive (testaccount2@gmail.com)" "MFG:GOOGLE;DRV:GCP;CMD:POSTSCRIPT;MDL:cloudprint://testaccount2%40gmail.com/__test_save_docs;"'
    assert printers[1].getCUPSDriverDescription() == '"cupscloudprint:testaccount2@gmail.com:__test_save_docs_2.ppd" en "Google" "Save to Google Drive 2 DisplayName (testaccount2@gmail.com)" "MFG:GOOGLE;DRV:GCP;CMD:POSTSCRIPT;MDL:cloudprint://testaccount2%40gmail.com/__test_save_docs_2;"'
    
def test_getPPDName():
    global printers
    assert printers[0].getPPDName() == "cupscloudprint:testaccount2@gmail.com:__test_save_docs.ppd"
    assert printers[1].getPPDName() == "cupscloudprint:testaccount2@gmail.com:__test_save_docs_2.ppd"
    
def test_generatePPD():
    global printers
    for printer in printers:
        ppddata = printer.generatePPD()
        assert isinstance(ppddata,basestring)
        
        # test ppd data is valid
        tempfile = open('/tmp/.ppdfile', 'w')
        tempfile.write(ppddata)
        tempfile.close()
        
        p = subprocess.Popen(['cupstestppd', '/tmp/.ppdfile'], stdout=subprocess.PIPE)
        testdata = p.communicate()[0]
        os.unlink('/tmp/.ppdfile')
        assert p.returncode == 0
    
def test_sanitizeText():
    global printers
    assert printers[0]._sanitizeText("") == ""
    assert printers[0]._sanitizeText("TESTSTRING") == "TESTSTRING"
    assert printers[0]._sanitizeText("TEST:; STRING /2") == "TEST___STRING_-2"
    assert printers[0]._sanitizeText("TEST:; STRING /2") == "TEST___STRING_-2"
    
def test_getInternalName():
    global printers
    printerItem = printers[0]

    internalCapabilityTests = []
    # load test file and try all those
    for filelineno, line in enumerate(open('testing/testfiles/capabilitylist')):
        internalCapabilityTests.append({'name': line.decode("utf-8")})

    for internalTest in internalCapabilityTests:
        assert printerItem._getInternalName(internalTest, 'capability') not in printerItem._RESERVED_CAPABILITY_WORDS
        assert ':' not in printerItem._getInternalName(internalTest, 'capability')
        assert ' ' not in printerItem._getInternalName(internalTest, 'capability')
        assert len(printerItem._getInternalName(internalTest,'capability')) <= 30
        assert len(printerItem._getInternalName(internalTest,'capability')) >= 1

    for internalTest in internalCapabilityTests:
        for capabilityName in ["psk:JobDuplexAllDocumentsContiguously","other", "psk:PageOrientation"]:
            assert printerItem._getInternalName(internalTest,'option',capabilityName) not in printerItem._RESERVED_CAPABILITY_WORDS
            assert ':' not in printerItem._getInternalName(internalTest,'option',capabilityName)
            assert ' ' not in printerItem._getInternalName(internalTest,'option')
            assert len(printerItem._getInternalName(internalTest,'option',capabilityName)) <= 30
            assert len(printerItem._getInternalName(internalTest,'option',capabilityName)) >= 1
            
def test_encodeMultiPart():
    global printers
    assert isinstance(printers[0]._encodeMultiPart([('test','testvalue')]),basestring)
    assert 'testvalue' in printers[0]._encodeMultiPart([('test','testvalue')])
    assert 'Content-Disposition: form-data; name="test"' in printers[0]._encodeMultiPart([('test','testvalue')])

def test_getOverrideCapabilities():
    global printers
    printerItem = printers[0]
    assert printerItem._getOverrideCapabilities("") == {}
    assert printerItem._getOverrideCapabilities("landscape") == {'Orientation': 'Landscape'}
    assert printerItem._getOverrideCapabilities("nolandscape") == {'Orientation': 'Landscape'}
    assert printerItem._getOverrideCapabilities("test=one") == {'test': 'one'}
    assert printerItem._getOverrideCapabilities("test=one anothertest=two") == {'test': 'one','anothertest': 'two'}
    assert printerItem._getOverrideCapabilities("test=one anothertest=two Orientation=yes") == {'test': 'one','anothertest': 'two'}
    
def test_GetCapabilitiesDict():
    global printers
    printerItem = printers[0]
    assert printerItem._getCapabilitiesDict({},{},{}) == {"capabilities": []}
    assert printerItem._getCapabilitiesDict([{'name': 'test'}],{},{}) == {"capabilities": []}
    assert printerItem._getCapabilitiesDict([{'name': 'Default' + 'test', 'value': 'test'}],[{'name': printerItem._getInternalName({'name': "test"}, 'capability'),'value': printerItem._getInternalName({'name': "test123"},
                                              'option', printerItem._getInternalName({'name': "Defaulttest"}, 'capability'), []),
                                              'options': [{'name': 'test'}, {'name': 'test2'}]}], {}) == {'capabilities': [{'name': 'test', 'options': [{'name': 'test'}], 'type': 'Feature'}]}
    assert printerItem._getCapabilitiesDict([{'name': 'Default' + 'test', 'value': 'test'}],
                                            [{'name': printerItem._getInternalName({'name': "test"}, 'capability'),
                                             'value': printerItem._getInternalName({'name': "test123"},
                                             'option', printerItem._getInternalName({'name': "Defaulttest"}, 'capability'), []),
                                             'options': [{'name': 'test'}, {'name': 'test2'}]}], {'test': 'test2'}) == {'capabilities': [{'name': 'test', 'options': [{'name': 'test2'}], 'type': 'Feature'}]}

def test_attrListToArray():
    global printers
    assert len(list(printers[0]._attrListToArray({}))) == 0

def test_getCapabilities():
    global printers, printerManagerInstance
    printer = printers[0]
    connection = cups.Connection()
    
    # get test ppd
    ppdid = 'MFG:GOOGLE;DRV:GCP;CMD:POSTSCRIPT;MDL:'
    ppds = connection.getPPDs(ppd_device_id=ppdid)
    printerppdname, printerppd = ppds.popitem()
    
    assert printerManagerInstance.addPrinter(
        printer['name'],
        printer,
        connection,
        printerppdname) is not None
    emptyoptions = printer._getCapabilities(printerManagerInstance.sanitizePrinterName(printer['name']),"landscape")
    assert isinstance(emptyoptions, dict)
    assert isinstance(emptyoptions['capabilities'], list)
    assert len(emptyoptions['capabilities']) == 0
    connection.deletePrinter(printerManagerInstance.sanitizePrinterName(printer['name']))
    
def test_submitJob():
    global printers, printerManagerInstance
    printer = printers[0]
    connection = cups.Connection()
    testprintername = printerManagerInstance.sanitizePrinterName(printer['name'])
    
    # get test ppd
    ppdid = 'MFG:GOOGLE;DRV:GCP;CMD:POSTSCRIPT;MDL:'
    ppds = connection.getPPDs(ppd_device_id=ppdid)
    printerppdname, printerppd = ppds.popitem()
    
    assert printerManagerInstance.addPrinter(
        printer['name'],
        printer,
        connection,
        printerppdname) is not None
    
    # test submitting job
    assert printer.submitJob(
        'pdf',
        'testing/testfiles/Test Page.pdf',
        'Test Page',
        testprintername) == True
    assert printer.submitJob(
        'pdf',
        'testing/testfiles/Test Page Doesnt Exist.pdf',
        'Test Page',
        testprintername) == False
    assert printer.submitJob(
        'pdf',
        'testing/testfiles/Test Page Corrupt.pdf',
        'Test Page',
        testprintername, 'landscape') == False

    # test submitting job with rotate
    assert printer.submitJob(
        'pdf',
        'testing/testfiles/Test Page.pdf',
        'Test Page',
        testprintername,
        "landscape") == True
    assert printer.submitJob(
        'pdf',
        'testing/testfiles/Test Page.pdf',
        'Test Page',
        testprintername,
        "nolandscape") == True

    # test submitting job with no name
    assert printer.submitJob(
        'pdf',
        'testing/testfiles/Test Page.pdf',
        '',
        testprintername) == True
    assert printer.submitJob(
        'pdf',
        'testing/testfiles/Test Page Doesnt Exist.pdf',
        '',
        testprintername) == False

    # png
    assert printer.submitJob(
        'png',
        'testing/testfiles/Test Page.png',
        'Test Page',
        testprintername) == True
    assert printer.submitJob(
        'png',
        'testing/testfiles/Test Page Doesnt Exist.png',
        'Test Page',
        testprintername) == False

    # ps
    assert printer.submitJob(
        'ps',
        'testing/testfiles/Test Page.ps',
        'Test Page',
        testprintername) == False
    assert printer.submitJob(
        'ps',
        'testing/testfiles/Test Page Doesnt Exist.ps',
        'Test Page',
        testprintername) == False

    # test failure of print job
    assert printer.submitJob(
        'pdf',
        'testing/testfiles/Test Page.pdf',
        'FAIL PAGE',
        testprintername) == False

    # test failure of print job with exception
    assert printer.submitJob(
        'pdf',
        'testing/testfiles/Test Page.pdf',
        'TEST PAGE WITH EXCEPTION',
        testprintername) == False

    # delete test printer
    connection.deletePrinter(testprintername)
    
@pytest.mark.skipif(
    os.getuid() == 0,
    reason="will only pass if running tests as non-root user")
def test_submitJobFileCreationFails():
    global printers, printerManagerInstance
    printer = printers[0]
    connection = cups.Connection()
    testprintername = printerManagerInstance.sanitizePrinterName(printer['name'])
    
    # get test ppd
    ppdid = 'MFG:GOOGLE;DRV:GCP;CMD:POSTSCRIPT;MDL:'
    ppds = connection.getPPDs(ppd_device_id=ppdid)
    printerppdname, printerppd = ppds.popitem()
    
    assert printerManagerInstance.addPrinter(
        printer['name'],
        printer,
        connection,
        printerppdname) is not None
    
    # test failure of print job because b64 version of file exists
    Utils.WriteFile('testing/testfiles/Test Page.pdf.b64', 'test')
    os.chmod('testing/testfiles/Test Page.pdf.b64',0)
    assert printer.submitJob(
        'pdf',
        'testing/testfiles/Test Page.pdf',
        'Test Page',
        testprintername) == False
    os.unlink('testing/testfiles/Test Page.pdf.b64')
    
    # delete test printer
    connection.deletePrinter(testprintername)

########NEW FILE########
__FILENAME__ = test_printermanager
#    CUPS Cloudprint - Print via Google Cloud Print
#    Copyright (C) 2011 Simon Cadman
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
import cups
import urllib
import logging
import sys
sys.path.insert(0, ".")

from printermanager import PrinterManager
from mockrequestor import MockRequestor

global requestors, printerManagerInstance


def setup_function(function):
    # setup mock requestors
    global requestors
    requestors = []

    # account without special chars
    mockRequestorInstance1 = MockRequestor()
    mockRequestorInstance1.setAccount('testaccount1')
    mockRequestorInstance1.printers = []
    requestors.append(mockRequestorInstance1)

    # with @ symbol
    mockRequestorInstance2 = MockRequestor()
    mockRequestorInstance2.setAccount('testaccount2@gmail.com')
    mockRequestorInstance2.printers = [{'name': 'Save to Google Drive',
                                        'id': '__test_save_docs',
                                        'capabilities': [{'name': 'ns1:Colors',
                                                          'type': 'Feature'}]},
                                       ]
    requestors.append(mockRequestorInstance2)

    # 1 letter
    mockRequestorInstance3 = MockRequestor()
    mockRequestorInstance3.setAccount('t')
    mockRequestorInstance3.printers = []
    requestors.append(mockRequestorInstance3)

    # instantiate printer item
    if function != test_instantiate:
        test_instantiate()


def teardown_function(function):
    global requestors
    requestors = None
    logging.shutdown()
    reload(logging)

def test_parseURI():
    global printerManagerInstance, requestors
    accountName, printerid = printerManagerInstance._getAccountNameAndPrinterIdFromURI(
        "cloudprint://testaccount2%40gmail.com/testid")
    assert printerid == "testid"
    assert accountName == "testaccount2@gmail.com"

def test_parseLegacyURI():
    global printerManagerInstance, requestors

    # 20140210 format
    account, printername, printerid, formatid = printerManagerInstance.parseLegacyURI(
        "cloudprint://printername/testaccount2%40gmail.com/", requestors)
    assert formatid == printerManagerInstance.URIFormat20140210
    assert account == "testaccount2@gmail.com"
    assert printername == "printername"
    assert printerid is None

    # 20140307 format
    account, printername, printerid, formatid = printerManagerInstance.parseLegacyURI(
        "cloudprint://printername/testaccount2%40gmail.com/testid", requestors)
    assert formatid == printerManagerInstance.URIFormat20140307
    assert account == "testaccount2@gmail.com"
    assert printername == "printername"
    assert printerid == "testid"

    # 20140308+ format
    account, printername, printerid, formatid = printerManagerInstance.parseLegacyURI(
        "cloudprint://testaccount2%40gmail.com/testid", requestors)
    assert formatid == printerManagerInstance.URIFormatLatest
    assert account == "testaccount2@gmail.com"
    assert printerid == "testid"
    assert printername is None

def test_getPrinterIDByDetails():
    printerid, requestor = printerManagerInstance.getPrinterIDByDetails(
        "testaccount2@gmail.com", "printername", "testid")
    assert printerid == "testid"
    assert isinstance(requestor, MockRequestor)
    assert requestor.getAccount() == 'testaccount2@gmail.com'
    
    # test fails
    printerid, requestor = printerManagerInstance.getPrinterIDByDetails(
        "accountthatdoesntexist", "printernamethatdoesntexist", "testidthatdoesntexist")
    assert printerid is None
    assert requestor is None
    
    printerid, requestor = printerManagerInstance.getPrinterIDByDetails(
        "testaccount2@gmail.com", "printernamethatdoesntexist", None)
    assert printerid is None
    assert requestor is None


def test_getCUPSPrintersForAccount():
    global printerManagerInstance, requestors

    foundprinters, connection = printerManagerInstance.getCUPSPrintersForAccount(
        requestors[0].getAccount())
    assert foundprinters == []
    assert isinstance(connection, cups.Connection)

    # total printer
    totalPrinters = 0
    for requestor in requestors:
        totalPrinters += len(requestor.printers)

    fullprintersforaccount = printerManagerInstance.getPrinters(requestors[1].getAccount())
    assert len(fullprintersforaccount) == len(requestors[1].printers)

    fullprinters = printerManagerInstance.getPrinters()
    assert len(fullprinters) == totalPrinters

    printers = printerManagerInstance.getPrinters()
    assert len(printers) == totalPrinters
    printer = printers[0]

    # get ppd
    ppdid = 'MFG:GOOGLE;DRV:GCP;CMD:POSTSCRIPT;MDL:'
    ppds = connection.getPPDs(ppd_device_id=ppdid)
    printerppdname, printerppd = ppds.popitem()

    # test add printer to cups
    assert printerManagerInstance.addPrinter(
        printer['name'],
        printer,
        connection,
        printerppdname) is not None
    foundprinters, newconnection = printerManagerInstance.getCUPSPrintersForAccount(
        requestors[1].getAccount())
    # delete test printer
    connection.deletePrinter(printerManagerInstance.sanitizePrinterName(printer['name']))

    assert isinstance(foundprinters, list)
    assert len(foundprinters) == 1
    assert isinstance(connection, cups.Connection)


def test_instantiate():
    global requestors, printerManagerInstance
    # verify adding single requestor works
    printerManagerInstance = PrinterManager(requestors[0])
    assert printerManagerInstance.requestors[0] == requestors[0]
    assert len(printerManagerInstance.requestors) == 1

    # verify adding whole array of requestors works
    printerManagerInstance = PrinterManager(requestors)
    assert printerManagerInstance.requestors == requestors
    assert len(printerManagerInstance.requestors) == len(requestors)

def test_GetPrinterByURIFails():
    global printerManagerInstance, requestors

    # ensure invalid account returns None/None
    printerIdNoneTest = printerManagerInstance.getPrinterByURI(
        'cloudprint://testprinter/accountthatdoesntexist')
    assert printerIdNoneTest is None

    # ensure invalid printer on valid account returns None/None
    printerIdNoneTest = printerManagerInstance.getPrinterByURI(
        'cloudprint://testprinter/' + urllib.quote(requestors[0].getAccount()))
    assert printerIdNoneTest is None


def test_addPrinterFails():
    global printerManagerInstance
    assert printerManagerInstance.addPrinter('', None, '') == False

def test_invalidRequest():
    testMock = MockRequestor()
    assert testMock.doRequest('thisrequestisinvalid') is None

def test_printers():
    global printerManagerInstance, requestors

    # test cups connection
    connection = cups.Connection()
    cupsprinters = connection.getPrinters()

    # total printer
    totalPrinters = 0
    for requestor in requestors:
        totalPrinters += len(requestor.printers)
    
    # test getting printers for specific account
    printersforaccount = printerManagerInstance.getPrinters(requestors[1].getAccount())
    assert len(printersforaccount) == len(requestors[1].printers)
    
    printers = printerManagerInstance.getPrinters()
    import re
    assert len(printers) == totalPrinters
    for printer in printers:

        # name
        assert isinstance(printer['name'],basestring)
        assert len(printer['name']) > 0

        # account
        assert isinstance(printer.getAccount(),basestring)
        assert len(printer.getAccount()) > 0

        # id
        assert isinstance(printer['id'],basestring)
        assert len(printer['id']) > 0

        # test encoding and decoding printer details to/from uri
        uritest = re.compile(
            "cloudprint://(.*)/" + urllib.quote(printer['id']))
        assert isinstance(printer.getURI(),basestring)
        assert len(printer.getURI()) > 0
        assert uritest.match(printer.getURI()) is not None

        accountName, printerId = printerManagerInstance._getAccountNameAndPrinterIdFromURI(printer.getURI())
        assert isinstance(accountName,basestring)
        assert isinstance(printerId,basestring)
        assert accountName == printer.getAccount()
        assert printerId == printer['id']

        # get ppd
        ppdid = 'MFG:GOOGLE;DRV:GCP;CMD:POSTSCRIPT;MDL:'
        ppds = connection.getPPDs(ppd_device_id=ppdid)
        printerppdname, printerppd = ppds.popitem()

        # test add printer to cups
        assert printerManagerInstance.addPrinter(
            printer['name'],
            printer,
            connection,
            printerppdname) is not None
        testprintername = printerManagerInstance.sanitizePrinterName(printer['name'])

        # test printer actually added to cups
        cupsPrinters = connection.getPrinters()
        found = False
        for cupsPrinter in cupsPrinters:
            if (cupsPrinters[cupsPrinter]['printer-info'] == testprintername):
                found = True
                break

        assert found == True
        
        # delete test printer
        connection.deletePrinter(testprintername)

########NEW FILE########
__FILENAME__ = upgrade
#! /bin/sh
"true" '''\'
if command -v python2 > /dev/null; then
  exec python2 "$0" "$@"
else
  exec python "$0" "$@"
fi
exit $?
'''

#    CUPS Cloudprint - Print via Google Cloud Print
#    Copyright (C) 2011 Simon Cadman
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

if __name__ == '__main__':  # pragma: no cover

    import sys
    import cups
    import subprocess
    import os
    import json
    import logging
    import urllib
    from oauth2client import client
    from oauth2client import multistore_file
    from auth import Auth
    from ccputils import Utils
    from printermanager import PrinterManager
    Utils.SetupLogging()

    # line below is replaced on commit
    CCPVersion = "20140501 203545"
    Utils.ShowVersion(CCPVersion)

    if not os.path.exists("/etc/cloudprint.conf"):
        sys.stderr.write(
            "Config is invalid or missing, not running on fresh install\n")
        logging.warning("Upgrade tried to run on fresh install")
        sys.exit(0)

    requestors, storage = Auth.SetupAuth(False)
    if not requestors:
        sys.stderr.write("Config is invalid or missing\n")
        logging.error("Upgrade tried to run with invalid config")
        sys.exit(0)
    printer_manager = PrinterManager(requestors)

    logging.info("Upgrading to " + CCPVersion)

    try:
        connection = cups.Connection()
    except Exception as e:
        sys.stderr.write("Could not connect to CUPS: " + e.message + "\n")
        sys.exit(0)
    cupsprinters = connection.getPrinters()

    if os.path.exists(Auth.config):
        Utils.FixFilePermissions(Auth.config)

        try:
            content_file = open(Auth.config, 'r')
            content = content_file.read()
            data = json.loads(content)
        except Exception as e:
            sys.stderr.write(
                "Unable to read config file: " +
                e.message +
                "\n\n")
            sys.exit(0)

    else:
        errormessage = "\nRun: /usr/share/cloudprint-cups/"
        errormessage += "setupcloudprint.py to"
        errormessage += " setup your Google Credentials"
        errormessage += " and add your printers to CUPS\n\n"
        sys.stderr.write(errormessage)
        sys.exit(0)

    from ccputils import Utils
    if Utils.which('lpadmin') is None:
        errormessage = "lpadmin command not found"
        errormessage += ", you may need to run this script as root\n"
        sys.stderr.write(errormessage)
        sys.exit(1)

    try:
        print "Fetching list of available ppds..."
        allppds = connection.getPPDs()
        print "List retrieved successfully"
    except Exception as e:
        sys.stderr.write("Error connecting to CUPS: " + str(e) + "\n")
        sys.exit(1)

    for device in cupsprinters:
        try:
            if (cupsprinters[device]["device-uri"].find("cloudprint://") == 0):
                account, printername, printerid, formatid = \
                    printer_manager.parseLegacyURI(
                        cupsprinters[device]["device-uri"],
                        requestors)
                if formatid != PrinterManager.URIFormatLatest:
                    # not latest format, needs upgrading
                    updatingmessage = "Updating "
                    updatingmessage += cupsprinters[device]["printer-info"]
                    updatingmessage += " with new id uri format"
                    print updatingmessage
                    printerid, requestor = printer_manager.getPrinterIDByDetails(
                        account, printername, printerid)
                    if printerid is not None:
                        newDeviceURI = printer_manager.printerNameToUri(
                            urllib.unquote(account),
                            printerid)
                        cupsprinters[device]["device-uri"] = newDeviceURI
                        p = subprocess.Popen(
                            ["lpadmin",
                             "-p",
                             cupsprinters[device]["printer-info"].lstrip('-'),
                                "-v",
                                newDeviceURI],
                            stdout=subprocess.PIPE)
                        output = p.communicate()[0]
                        result = p.returncode
                        sys.stderr.write(output)
                    else:
                        errormessage = cupsprinters[device]["printer-info"]
                        errormessage += " not found, "
                        errormessage += "you should delete and "
                        errormessage += "re-add this printer"
                        print errormessage
                        continue
                else:
                    print "Updating " + cupsprinters[device]["printer-info"]

                ppdid = 'MFG:GOOGLE;DRV:GCP;CMD:POSTSCRIPT;MDL:' + \
                    cupsprinters[device]["device-uri"] + ';'

                # just needs updating
                printerppdname = None
                for ppd in allppds:
                    if allppds[ppd]['ppd-device-id'] == ppdid:
                        printerppdname = ppd
                if printerppdname is not None:
                    p = subprocess.Popen(
                        ["lpadmin",
                         "-p",
                         cupsprinters[device]["printer-info"].lstrip('-'),
                            "-m",
                            printerppdname.lstrip('-')],
                        stdout=subprocess.PIPE)
                    output = p.communicate()[0]
                    result = p.returncode
                    sys.stderr.write(output)
                else:
                    errormessage = cupsprinters[device]["printer-info"]
                    errormessage += " not found, you should delete and"
                    errormessage += " re-add this printer"
                    print errormessage
        except Exception as e:
            sys.stderr.write("Error connecting to CUPS: " + str(e) + "\n")

########NEW FILE########
