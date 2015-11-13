__FILENAME__ = argparser
# -*- coding: utf-8 -*-

from log import logging
import out


COMMANDS_DICT = {
    # User
    "user": {
        "help": "Show information about active user.",
        "flags": {
            "--full": {"help": "Show full information.",
                       "value": True,
                       "default": False},
        }
    },
    "login": {
        "help": "Authorize in Evernote.",
    },
    "logout": {
        "help": "Logout from Evernote.",
        "flags": {
            "--force": {"help": "Don't ask about logging out.",
                        "value": True,
                        "default": False},
        }
    },
    "settings": {
        "help": "Show and edit current settings.",
        "arguments": {
            "--editor": {"help": "Set the editor, which use to "
                                 "edit and create notes.",
                         "emptyValue": '#GET#'},
        }
    },

    # Notes
    "create": {
        "help": "Create note in evernote.",
        "arguments": {
            "--title":      {"altName": "-t",
                             "help": "The note title.",
                             "required": True},
            "--content":    {"altName": "-c",
                             "help": "The note content."},
            "--tags":       {"altName": "-tg",
                             "help": "One tag or the list of tags which"
                                     " will be added to the note."},
            "--notebook":   {"altName": "-nb",
                             "help": "Set the notebook where to save note."}
        }
    },
    "edit": {
        "help": "Edit note in Evernote.",
        "firstArg": "--note",
        "arguments": {
            "--note":       {"altName": "-n",
                             "help": "The name or ID from the "
                                     "previous search of a note to edit."},
            "--title":      {"altName": "-t",
                             "help": "Set new title of the note."},
            "--content":    {"altName": "-c",
                             "help": "Set new content of the note."},
            "--tags":       {"altName": "-tg",
                             "help": "Set new list o tags for the note."},
            "--notebook":   {"altName": "-nb",
                             "help": "Assign new notebook for the note."}
        }
    },
    "remove": {
        "help": "Remove note from Evernote.",
        "firstArg": "--note",
        "arguments": {
            "--note":  {"altName": "-n",
                        "help": "The name or ID from the previous "
                                "search of a note to remove."},
        },
        "flags": {
            "--force": {"altName": "-f",
                        "help": "Don't ask about removing.",
                        "value": True,
                        "default": False},
        }
    },
    "show": {
        "help": "Output note in the terminal.",
        "firstArg": "--note",
        "arguments": {
            "--note": {"altName": "-n",
                       "help": "The name or ID from the previous "
                               "search of a note to show."},
        }
    },
    "find": {
        "help": "Search notes in Evernote.",
        "firstArg": "--search",
        "arguments": {
            "--search":     {"altName": "-s",
                             "help": "Text to search.",
                             "emptyValue": "*"},
            "--tags":       {"altName": "-tg",
                             "help": "Notes with which tag/tags to search."},
            "--notebooks":  {"altName": "-nb",
                             "help": "In which notebook search the note."},
            "--date":       {"altName": "-d",
                             "help": "Set date in format dd.mm.yyyy or "
                                     "date range dd.mm.yyyy-dd.mm.yyyy."},
            "--count":      {"altName": "-cn",
                             "help": "How many notes show in the result list.",
                             "type": int},
        },
        "flags": {
            "--with-url":       {"altName": "-wu",
                                 "help": "Add direct url of each note "
                                         "in results to Evernote web-version.",
                                 "value": True,
                                 "default": False},
            "--exact-entry":    {"altName": "-ee",
                                 "help": "Search for exact "
                                         "entry of the request.",
                                 "value": True,
                                 "default": False},
            "--content-search": {"altName": "-cs",
                                 "help": "Search by content, not by title.",
                                 "value": True,
                                 "default": False},
        }
    },

    # Notebooks
    "notebook-list": {
        "help": "Show the list of existing notebooks in your Evernote.",
    },
    "notebook-create": {
        "help": "Create new notebook.",
        "arguments": {
            "--title": {"altName": "-t",
                        "help": "Set the title of new notebook."},
        }
    },
    "notebook-edit": {
        "help": "Edit/rename notebook.",
        "firstArg": "--notebook",
        "arguments": {
            "--notebook":   {"altName": "-nb",
                             "help": "The name of a notebook to rename."},
            "--title":      {"altName": "-t",
                             "help": "Set the new name of notebook."},
        }
    },

    # Tags
    "tag-list": {
        "help": "Show the list of existing tags in your Evernote.",
    },
    "tag-create": {
        "help": "Create new tag.",
        "arguments": {
            "--title": {"altName": "-t", "help": "Set the title of new tag."},
        }
    },
    "tag-edit": {
        "help": "Edit/rename tag.",
        "firstArg": "--tagname",
        "arguments": {
            "--tagname":    {"altName": "-tgn",
                             "help": "The name of a tag to rename."},
            "--title":      {"altName": "-t",
                             "help": "Set the new name of tag."},
        }
    },
}
"""
    "tag-remove": {
        "help": "Remove tag.",
        "firstArg": "--tagname",
        "arguments": {
            "--tagname": {"help": "The name of a tag to remove."},
        },
        "flags": {
            "--force": {"help": "Don't ask about removing.", "value": True, "default": False},
        }
    },
    "notebook-remove": {
        "help": "Remove notebook.",
        "firstArg": "--notebook",
        "arguments": {
            "--notebook": {"help": "The name of a notebook to remove."},
        },
        "flags": {
            "--force": {"help": "Don't ask about removing.", "value": True, "default": False},
        }
    },
"""


class argparser(object):

    COMMANDS = COMMANDS_DICT
    sys_argv = None

    def __init__(self, sys_argv):
        self.sys_argv = sys_argv
        self.LVL = len(sys_argv)
        self.INPUT = sys_argv

        # list of commands
        self.CMD_LIST = self.COMMANDS.keys()
        # command
        self.CMD = None if self.LVL == 0 else self.INPUT[0]
        # list of possible arguments of the command line
        self.CMD_ARGS = self.COMMANDS[self.CMD]['arguments'] if self.LVL > 0 and self.CMD in self.COMMANDS and 'arguments' in self.COMMANDS[self.CMD] else {}
        # list of possible flags of the command line
        self.CMD_FLAGS = self.COMMANDS[self.CMD]['flags'] if self.LVL > 0 and self.CMD in self.COMMANDS and 'flags' in self.COMMANDS[self.CMD] else {}
        # list of entered arguments and their values
        self.INP = [] if self.LVL <= 1 else self.INPUT[1:]

        logging.debug("CMD_LIST : %s", str(self.CMD_LIST))
        logging.debug("CMD: %s", str(self.CMD))
        logging.debug("CMD_ARGS : %s", str(self.CMD_ARGS))
        logging.debug("CMD_FLAGS : %s", str(self.CMD_FLAGS))
        logging.debug("INP : %s", str(self.INP))

    def parse(self):
        self.INP_DATA = {}

        if self.CMD is None:
            out.printAbout()
            return False

        if self.CMD == "autocomplete":
            # substitute arguments for AutoComplete
            # 1 offset to make the argument as 1 is autocomplete
            self.__init__(self.sys_argv[1:])
            self.printAutocomplete()
            return False

        if self.CMD == "--help":
            self.printHelp()
            return False

        if self.CMD not in self.COMMANDS:
            self.printErrorCommand()
            return False

        if "--help" in self.INP:
            self.printHelp()
            return False

        # prepare data
        for arg, params in (self.CMD_ARGS.items() + self.CMD_FLAGS.items()):
            # set values by default
            if 'default' in params:
                self.INP_DATA[arg] = params['default']

            # replace `altName` entered arguments on full
            if 'altName' in params and params['altName'] in self.INP:
                self.INP[self.INP.index(params['altName'])] = arg

        activeArg = None
        ACTIVE_CMD = None
        # check and insert first argument by default
        if 'firstArg' in self.COMMANDS[self.CMD]:
            firstArg = self.COMMANDS[self.CMD]['firstArg']
            if len(self.INP) > 0:
                # Check that first argument is a default argument
                # and another argument.
                if self.INP[0] not in (self.CMD_ARGS.keys() +
                                       self.CMD_FLAGS.keys()):
                    self.INP = [firstArg, ] + self.INP
            else:
                self.INP = [firstArg, ]

        for item in self.INP:
            # check what are waiting the argument
            if activeArg is None:
                # actions for the argument
                if item in self.CMD_ARGS:
                    activeArg = item
                    ACTIVE_CMD = self.CMD_ARGS[activeArg]

                # actions for the flag
                elif item in self.CMD_FLAGS:
                    self.INP_DATA[item] = self.CMD_FLAGS[item]["value"]

                # error. parameter is not found
                else:
                    self.printErrorArgument(item)
                    return False

            else:
                activeArgTmp = None
                # values it is parameter
                if item in self.CMD_ARGS or item in self.CMD_FLAGS:
                    # active argument is "emptyValue"
                    if "emptyValue" in ACTIVE_CMD:
                        activeArgTmp = item # remember the new "active" argument
                        item = ACTIVE_CMD['emptyValue']  # set the active atgument to emptyValue
                    # Error, "active" argument has no values
                    else:
                        self.printErrorArgument(activeArg, item)
                        return False

                if 'type' in ACTIVE_CMD:
                    convType = ACTIVE_CMD['type']
                    if convType not in (int, str):
                        logging.error("Unsupported argument type: %s", convType)
                        return False

                    try:
                        item = convType(item)
                    except:
                        self.printErrorArgument(activeArg, item)
                        return False

                self.INP_DATA[activeArg] = item
                activeArg = activeArgTmp  # this is either a new "active" argument or emptyValue.

        # if there are still active arguments
        if activeArg is not None:
            # if the active argument is emptyValue
            if 'emptyValue' in ACTIVE_CMD:
                self.INP_DATA[activeArg] = ACTIVE_CMD['emptyValue']

            # An error argument
            else:
                self.printErrorArgument(activeArg, "")
                return False

        # check whether there is a necessary argument request
        for arg, params in (self.CMD_ARGS.items() + self.CMD_FLAGS.items()):
            if 'required' in params and arg not in self.INP:
                self.printErrorReqArgument(arg)
                return False

        # trim -- and ->_
        self.INP_DATA = dict([key.lstrip("-").replace("-", "_"), val] for key, val in self.INP_DATA.items())
        return self.INP_DATA

    def printAutocomplete(self):
        # checking later values
        LAST_VAL = self.INP[-1] if self.LVL > 1 else None
        PREV_LAST_VAL = self.INP[-2] if self.LVL > 2 else None
        ARGS_FLAGS_LIST = self.CMD_ARGS.keys() + self.CMD_FLAGS.keys()

        # print root grid
        if self.CMD is None:
            self.printGrid(self.CMD_LIST)

        # work with root commands
        elif not self.INP:

            # print arguments if a root command is found
            if self.CMD in self.CMD_LIST:
                self.printGrid(ARGS_FLAGS_LIST)

            # autocomplete for sub-commands
            else:
                # filter out irrelevant commands
                self.printGrid([item for item in self.CMD_LIST if item.startswith(self.CMD)])

        # processing arguments
        else:

            # filter out arguments that have not been input
            if PREV_LAST_VAL in self.CMD_ARGS or LAST_VAL in self.CMD_FLAGS:
                self.printGrid([item for item in ARGS_FLAGS_LIST if item not in self.INP])

            # autocomplete for part of the command
            elif PREV_LAST_VAL not in self.CMD_ARGS:
                self.printGrid([item for item in ARGS_FLAGS_LIST if item not in self.INP and item.startswith(LAST_VAL)])

            # processing of the arguments
            else:
                print ""  # "Please_input_%s" % INP_ARG.replace('-', '')

    def printGrid(self, list):
        out.printLine(" ".join(list))

    def printErrorCommand(self):
        out.printLine('Unexpected command "%s"' % (self.CMD))
        self.printHelp()

    def printErrorReqArgument(self, errorArg):
        out.printLine('Not found required argument "%s" '
                      'for command "%s" ' % (errorArg, self.CMD))
        self.printHelp()

    def printErrorArgument(self, errorArg, errorVal=None):
        if errorVal is None:
            out.printLine('Unexpected argument "%s" '
                          'for command "%s"' % (errorArg, self.CMD))
        else:
            out.printLine('Unexpected value "%s" '
                          'for argument "%s"' % (errorVal, errorArg))
        self.printHelp()

    def printHelp(self):
        if self.CMD is None or self.CMD not in self.COMMANDS:
            tab = len(max(self.COMMANDS.keys(), key=len))
            out.printLine("Available commands:")
            for cmd in self.COMMANDS:
                out.printLine("%s : %s" % (cmd.rjust(tab, " "),
                                           self.COMMANDS[cmd]['help']))

        else:

            tab = len(max(self.CMD_ARGS.keys() +
                          self.CMD_FLAGS.keys(), key=len))

            out.printLine("Options for: %s" % self.CMD)
            out.printLine("Available arguments:")
            for arg in self.CMD_ARGS:
                out.printLine("%s : %s%s" % (
                    arg.rjust(tab, " "),
                    '[default] ' if 'firstArg' in self.COMMANDS[self.CMD] and self.COMMANDS[self.CMD]['firstArg'] == arg else '',
                    self.CMD_ARGS[arg]['help']))

            if self.CMD_FLAGS:
                out.printLine("Available flags:")
                for flag in self.CMD_FLAGS:
                    out.printLine("%s : %s" % (flag.rjust(tab, " "),
                                               self.CMD_FLAGS[flag]['help']))

########NEW FILE########
__FILENAME__ = config
# -*- coding: utf-8 -*-

import os
import sys

# !!! DO NOT EDIT !!! >>>
USER_BASE_URL = "www.evernote.com"
USER_STORE_URI = "https://www.evernote.com/edam/user"
CONSUMER_KEY = "skaizer-5314"
CONSUMER_SECRET = "6f4f9183b3120801"

USER_BASE_URL_SANDBOX = "sandbox.evernote.com"
USER_STORE_URI_SANDBOX = "https://sandbox.evernote.com/edam/user"
CONSUMER_KEY_SANDBOX = "skaizer-1250"
CONSUMER_SECRET_SANDBOX = "ed0fcc0c97c032a5"
# !!! DO NOT EDIT !!! <<<

# Evernote config

VERSION = 0.1

IS_IN_TERMINAL = sys.stdin.isatty()
IS_OUT_TERMINAL = sys.stdout.isatty()

# Application path
APP_DIR = os.path.join(os.getenv("HOME") or os.getenv("USERPROFILE"),  ".geeknote")
ERROR_LOG = os.path.join(APP_DIR, "error.log")

# Set default system editor
DEF_UNIX_EDITOR = "nano"
DEF_WIN_EDITOR = "notepad.exe"
EDITOR_OPEN = "WRITE"

DEV_MODE = False
DEBUG = False

# Url view the note
NOTE_URL = "https://%domain%/Home.action?#n=%s"

# validate config
try:
    if not os.path.exists(APP_DIR):
        os.mkdir(APP_DIR)
except Exception, e:
    sys.stdout.write("Can not create application dirictory : %s" % APP_DIR)
    exit()

if DEV_MODE:
    USER_STORE_URI = USER_STORE_URI_SANDBOX
    CONSUMER_KEY = CONSUMER_KEY_SANDBOX
    CONSUMER_SECRET = CONSUMER_SECRET_SANDBOX
    USER_BASE_URL = USER_BASE_URL_SANDBOX

NOTE_URL = NOTE_URL.replace('%domain%', USER_BASE_URL)

########NEW FILE########
__FILENAME__ = editor
# -*- coding: utf-8 -*-

import os
import sys
import tempfile
from bs4 import BeautifulSoup
import threading
import hashlib
import html2text as html2text
import markdown2 as markdown
import tools
import out
import re
import config
from storage import Storage
from log import logging
from xml.sax.saxutils import escape, unescape

class EditorThread(threading.Thread):

    def __init__(self, editor):
        threading.Thread.__init__(self)
        self.editor = editor

    def run(self):
        self.editor.edit()


class Editor(object):
    # escape() and unescape() takes care of &, < and >.

    @staticmethod
    def getHtmlEscapeTable():
        return {'"': "&quot;",
                "'": "&apos;",
                '\n': "<br />"}

    @staticmethod
    def getHtmlUnescapeTable():
        return {v:k for k, v in Editor.getHtmlEscapeTable().items()}

    @staticmethod
    def HTMLEscape(text):
        return escape(text, Editor.getHtmlEscapeTable())

    @staticmethod
    def HTMLUnescape(text):
        return unescape(text, Editor.getHtmlUnescapeTable())

    @staticmethod
    def ENMLtoText(contentENML):
        html2text.BODY_WIDTH = 0
        soup = BeautifulSoup(contentENML.decode('utf-8'))

        for section in soup.select('li > p'):
            section.replace_with( section.contents[0] )

        for section in soup.select('li > br'):
            if section.next_sibling:
                next_sibling = section.next_sibling.next_sibling
                if next_sibling:
                    if next_sibling.find('li'):
                        section.extract()
                else:
                    section.extract()

        content = html2text.html2text(soup.prettify())
        content = re.sub(r' *\n', os.linesep, content)
        return content.encode('utf-8')

    @staticmethod
    def wrapENML(contentHTML):
        body = '<?xml version="1.0" encoding="UTF-8"?>\n'\
           '<!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">\n'\
           '<en-note>%s</en-note>' % contentHTML
        return body

    @staticmethod
    def textToENML(content, raise_ex=False, format='markdown'):
        """
        Create an ENML format of note.
        """
        if not isinstance(content, str):
            content = ""
        try:
            content = unicode(content, "utf-8")
            # add 2 space before new line in paragraph for creating br tags
            content = re.sub(r'([^\r\n])([\r\n])([^\r\n])', r'\1  \n\3', content)
            if format=='markdown':
              contentHTML = markdown.markdown(content).encode("utf-8")
              # Non-Pretty HTML output
              contentHTML = str(BeautifulSoup(contentHTML, 'html.parser'))
            else:
              contentHTML = Editor.HTMLEscape(content)
            return Editor.wrapENML(contentHTML)
        except:
            if raise_ex:
                raise Exception("Error while parsing text to html."
                                " Content must be an UTF-8 encode.")

            logging.error("Error while parsing text to html. "
                          "Content must be an UTF-8 encode.")
            out.failureMessage("Error while parsing text to html. "
                               "Content must be an UTF-8 encode.")
            return tools.exit()

    def __init__(self, content):
        if not isinstance(content, str):
            raise Exception("Note content must be an instance "
                            "of string, '%s' given." % type(content))
            
        (tempfileHandler, tempfileName) = tempfile.mkstemp(suffix=".markdown")
        os.write(tempfileHandler, self.ENMLtoText(content))
        os.close(tempfileHandler)
        
        self.content = content
        self.tempfile = tempfileName

    def getTempfileChecksum(self):
        with open(self.tempfile, 'rb') as fileHandler:
            checksum = hashlib.md5()
            while True:
                data = fileHandler.read(8192)
                if not data:
                    break
                checksum.update(data)

            return checksum.hexdigest()

    def edit(self):
        """
        Call the system editor, that types as a default in the system.
        Editing goes in markdown format, and then the markdown
        converts into HTML, before uploading to Evernote.
        """

        # Try to find default editor in the system.
        storage = Storage()
        editor = storage.getUserprop('editor')

        if not editor:
            editor = os.environ.get("editor")

        if not editor:
            editor = os.environ.get("EDITOR")

        if not editor:
            # If default editor is not finded, then use nano as a default.
            if sys.platform == 'win32':
                editor = config.DEF_WIN_EDITOR
            else:
                editor = config.DEF_UNIX_EDITOR

        # Make a system call to open file for editing.
        logging.debug("launch system editor: %s %s" % (editor, self.tempfile))

        out.preloader.stop()
        os.system(editor + " " + self.tempfile)
        out.preloader.launch()
        newContent = open(self.tempfile, 'r').read()

        return newContent

########NEW FILE########
__FILENAME__ = gclient
# -*- coding: utf-8 -*-

"""
From old version API
"""

from evernote.edam.error.ttypes import EDAMSystemException, EDAMUserException
import evernote.edam.userstore.UserStore as UserStore
import thrift.protocol.TBinaryProtocol as TBinaryProtocol
from thrift.Thrift import TType, TMessageType
from thrift.transport import TTransport
try:
    from thrift.protocol import fastbinary
except:
    fastbinary = None


class getNoteStoreUrl_args(object):
    """
    Attributes:
     - authenticationToken
    """

    thrift_spec = (None, (1, TType.STRING, 'authenticationToken', None, None, ), )

    def __init__(self, authenticationToken=None,):
        self.authenticationToken = authenticationToken

    def read(self, iprot):
        if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
            fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
            return
        iprot.readStructBegin()
        while True:
            (fname, ftype, fid) = iprot.readFieldBegin()
            if ftype == TType.STOP:
                break
            if fid == 1:
                if ftype == TType.STRING:
                    self.authenticationToken = iprot.readString()
                else:
                    iprot.skip(ftype)
            else:
                iprot.skip(ftype)
            iprot.readFieldEnd()
        iprot.readStructEnd()

    def write(self, oprot):
        if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
            oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
            return
        oprot.writeStructBegin('getNoteStoreUrl_args')
        if self.authenticationToken is not None:
            oprot.writeFieldBegin('authenticationToken', TType.STRING, 1)
            oprot.writeString(self.authenticationToken)
            oprot.writeFieldEnd()
        oprot.writeFieldStop()
        oprot.writeStructEnd()

    def validate(self):
        return

    def __repr__(self):
        L = ['%s=%r' % (key, value)
             for key, value in self.__dict__.iteritems()]
        return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not (self == other)


class getNoteStoreUrl_result(object):
    """
    Attributes:
     - success
     - userException
     - systemException
    """

    thrift_spec = (
        (0, TType.STRING, 'success', None, None,),
        (1, TType.STRUCT, 'userException', (EDAMUserException,
                                            EDAMUserException.thrift_spec), None,),
        (2, TType.STRUCT, 'systemException', (EDAMSystemException, EDAMSystemException.thrift_spec), None,)
    )

    def __init__(self, success=None, userException=None, systemException=None,):
        self.success = success
        self.userException = userException
        self.systemException = systemException

    def read(self, iprot):
        if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
            fastbinary.decode_binary(self, iprot.trans,
                                     (self.__class__, self.thrift_spec))
            return
        iprot.readStructBegin()
        while True:
            (fname, ftype, fid) = iprot.readFieldBegin()
            if ftype == TType.STOP:
                break
            if fid == 0:
                if ftype == TType.STRING:
                    self.success = iprot.readString()
                else:
                    iprot.skip(ftype)
            elif fid == 1:
                if ftype == TType.STRUCT:
                    self.userException = EDAMUserException()
                    self.userException.read(iprot)
                else:
                    iprot.skip(ftype)
            elif fid == 2:
                if ftype == TType.STRUCT:
                    self.systemException = EDAMSystemException()
                    self.systemException.read(iprot)
                else:
                    iprot.skip(ftype)
            else:
                iprot.skip(ftype)
            iprot.readFieldEnd()
        iprot.readStructEnd()

    def write(self, oprot):
        if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated:
            if self.thrift_spec is not None and fastbinary is not None:
                oprot.trans.write(fastbinary.encode_binary(self, (self.__class__,
                                                                  self.thrift_spec)))
                return
        oprot.writeStructBegin('getNoteStoreUrl_result')
        if self.success is not None:
            oprot.writeFieldBegin('success', TType.STRING, 0)
            oprot.writeString(self.success)
            oprot.writeFieldEnd()
        if self.userException is not None:
            oprot.writeFieldBegin('userException', TType.STRUCT, 1)
            self.userException.write(oprot)
            oprot.writeFieldEnd()
        if self.systemException is not None:
            oprot.writeFieldBegin('systemException', TType.STRUCT, 2)
            self.systemException.write(oprot)
            oprot.writeFieldEnd()
        oprot.writeFieldStop()
        oprot.writeStructEnd()

    def validate(self):
        return

    def __repr__(self):
        L = ['%s=%r' % (key, value)
             for key, value in self.__dict__.iteritems()]
        return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not (self == other)


class CustomClient(UserStore.Client):
    '''
    Getting from old version API
    '''

    def getNoteStoreUrl(self, authenticationToken):
        """
        Returns the URL that should be used to talk to the NoteStore for the
        account represented by the provided authenticationToken.
        This method isn't needed by most clients, who can retrieve the correct
        NoteStore URL from the AuthenticationResult returned from the authenticate
        or refreshAuthentication calls. This method is typically only needed
        to look up the correct URL for a long-lived session token (e.g. for an
        OAuth web service).

        Parameters:
         - authenticationToken
        """
        self.send_getNoteStoreUrl(authenticationToken)
        return self.recv_getNoteStoreUrl()

    def send_getNoteStoreUrl(self, authenticationToken):
        self._oprot.writeMessageBegin('getNoteStoreUrl',
                                      TMessageType.CALL,
                                      self._seqid)
        args = getNoteStoreUrl_args()
        args.authenticationToken = authenticationToken
        args.write(self._oprot)
        self._oprot.writeMessageEnd()
        self._oprot.trans.flush()

    def recv_getNoteStoreUrl(self, ):
        (fname, mtype, rseqid) = self._iprot.readMessageBegin()
        if mtype == TMessageType.EXCEPTION:
            x = UserStore.TApplicationException()
            x.read(self._iprot)
            self._iprot.readMessageEnd()
            raise x
        result = getNoteStoreUrl_result()
        result.read(self._iprot)
        self._iprot.readMessageEnd()
        if result.success is not None:
            return result.success
        if result.userException is not None:
            raise result.userException
        if result.systemException is not None:
            raise result.systemException
        raise UserStore.TApplicationException(
            UserStore.TApplicationException.MISSING_RESULT,
            "getNoteStoreUrl failed: unknown result"
        )


GUserStore = UserStore
GUserStore.Client = CustomClient

########NEW FILE########
__FILENAME__ = geeknote
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import traceback
import time
import sys
import os
import re

import thrift.protocol.TBinaryProtocol as TBinaryProtocol
import thrift.transport.THttpClient as THttpClient

import evernote.edam.userstore.constants as UserStoreConstants
import evernote.edam.notestore.NoteStore as NoteStore
import evernote.edam.error.ttypes as Errors
import evernote.edam.type.ttypes as Types

import config
import tools
import out
from editor import Editor, EditorThread
from gclient import GUserStore as UserStore
from argparser import argparser
from oauth import GeekNoteAuth
from storage import Storage
from log import logging


def GeekNoneDBConnectOnly(func):
    """ operator to disable evernote connection
    or create instance of GeekNote """
    def wrapper(*args, **kwargs):
        GeekNote.skipInitConnection = True
        return func(*args, **kwargs)
    return wrapper


class GeekNote(object):

    userStoreUri = config.USER_STORE_URI
    consumerKey = config.CONSUMER_KEY
    consumerSecret = config.CONSUMER_SECRET
    authToken = None
    userStore = None
    noteStore = None
    storage = None
    skipInitConnection = False

    def __init__(self, skipInitConnection=False):
        if skipInitConnection:
            self.skipInitConnection = True

        self.getStorage()

        if self.skipInitConnection is True:
            return

        self.getUserStore()

        if not self.checkAuth():
            self.auth()

    def EdamException(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception, e:
                logging.error("Error: %s : %s", func.__name__, str(e))

                if not hasattr(e, 'errorCode'):
                    out.failureMessage("Sorry, operation has failed!!!.")
                    tools.exit()

                errorCode = int(e.errorCode)

                # auth-token error, re-auth
                if errorCode == 9:
                    storage = Storage()
                    storage.removeUser()
                    GeekNote()
                    return func(*args, **kwargs)

                elif errorCode == 3:
                    out.failureMessage("Sorry, you do not have permissions "
                                       "to do this operation.")

                else:
                    return False

                tools.exit()

        return wrapper

    def getStorage(self):
        if GeekNote.storage:
            return GeekNote.storage

        GeekNote.storage = Storage()
        return GeekNote.storage

    def getUserStore(self):
        if GeekNote.userStore:
            return GeekNote.userStore

        userStoreHttpClient = THttpClient.THttpClient(self.userStoreUri)
        userStoreProtocol = TBinaryProtocol.TBinaryProtocol(userStoreHttpClient)
        GeekNote.userStore = UserStore.Client(userStoreProtocol)

        self.checkVersion()

        return GeekNote.userStore

    def getNoteStore(self):
        if GeekNote.noteStore:
            return GeekNote.noteStore

        noteStoreUrl = self.getUserStore().getNoteStoreUrl(self.authToken)
        noteStoreHttpClient = THttpClient.THttpClient(noteStoreUrl)
        noteStoreProtocol = TBinaryProtocol.TBinaryProtocol(noteStoreHttpClient)
        GeekNote.noteStore = NoteStore.Client(noteStoreProtocol)

        return GeekNote.noteStore

    def checkVersion(self):
        versionOK = self.getUserStore().checkVersion("Python EDAMTest",
                                       UserStoreConstants.EDAM_VERSION_MAJOR,
                                       UserStoreConstants.EDAM_VERSION_MINOR)
        if not versionOK:
            logging.error("Old EDAM version")
            return tools.exit()

    def checkAuth(self):
        self.authToken = self.getStorage().getUserToken()
        logging.debug("oAuth token : %s", self.authToken)
        if self.authToken:
            return True
        return False

    def auth(self):
        GNA = GeekNoteAuth()
        self.authToken = GNA.getToken()
        userInfo = self.getUserInfo()
        if not isinstance(userInfo, object):
            logging.error("User info not get")
            return False

        self.getStorage().createUser(self.authToken, userInfo)
        return True

    def getUserInfo(self):
        return self.getUserStore().getUser(self.authToken)

    def removeUser(self):
        return self.getStorage().removeUser()

    @EdamException
    def findNotes(self, keywords, count, createOrder=False, offset=0):
        """ WORK WITH NOTEST """
        noteFilter = NoteStore.NoteFilter(order=Types.NoteSortOrder.RELEVANCE)
        if createOrder:
            noteFilter.order = Types.NoteSortOrder.CREATED

        if keywords:
            noteFilter.words = keywords
        return self.getNoteStore().findNotes(self.authToken, noteFilter, offset, count)

    @EdamException
    def loadNoteContent(self, note):
        """ modify Note object """
        if not isinstance(note, object):
            raise Exception("Note content must be an "
                            "instanse of Note, '%s' given." % type(note))

        note.content = self.getNoteStore().getNoteContent(self.authToken, note.guid)
        # fill the tags in
        if note.tagGuids and not note.tagNames:
          note.tagNames = [];
          for guid in note.tagGuids:
            tag = self.getNoteStore().getTag(self.authToken,guid)
            note.tagNames.append(tag.name)

    @EdamException
    def createNote(self, title, content, tags=None, notebook=None, created=None):
        note = Types.Note()
        note.title = title
        note.content = content
        note.created = created

        if tags:
            note.tagNames = tags

        if notebook:
            note.notebookGuid = notebook

        logging.debug("New note : %s", note)

        return self.getNoteStore().createNote(self.authToken, note)

    @EdamException
    def updateNote(self, guid, title=None, content=None,
                   tags=None, notebook=None):
        note = Types.Note()
        note.guid = guid
        if title:
            note.title = title

        if content:
            note.content = content

        if tags:
            note.tagNames = tags

        if notebook:
            note.notebookGuid = notebook

        logging.debug("Update note : %s", note)

        self.getNoteStore().updateNote(self.authToken, note)
        return True

    @EdamException
    def removeNote(self, guid):
        logging.debug("Delete note with guid: %s", guid)

        self.getNoteStore().deleteNote(self.authToken, guid)
        return True

    @EdamException
    def findNotebooks(self):
        """ WORK WITH NOTEBOOKS """
        return self.getNoteStore().listNotebooks(self.authToken)

    @EdamException
    def createNotebook(self, name):
        notebook = Types.Notebook()
        notebook.name = name

        logging.debug("New notebook : %s", notebook)

        result = self.getNoteStore().createNotebook(self.authToken, notebook)
        return result

    @EdamException
    def updateNotebook(self, guid, name):
        notebook = Types.Notebook()
        notebook.name = name
        notebook.guid = guid

        logging.debug("Update notebook : %s", notebook)

        self.getNoteStore().updateNotebook(self.authToken, notebook)
        return True

    @EdamException
    def removeNotebook(self, guid):
        logging.debug("Delete notebook : %s", guid)

        self.getNoteStore().expungeNotebook(self.authToken, guid)
        return True

    @EdamException
    def findTags(self):
        """ WORK WITH TAGS """
        return self.getNoteStore().listTags(self.authToken)

    @EdamException
    def createTag(self, name):
        tag = Types.Tag()
        tag.name = name

        logging.debug("New tag : %s", tag)

        result = self.getNoteStore().createTag(self.authToken, tag)
        return result

    @EdamException
    def updateTag(self, guid, name):
        tag = Types.Tag()
        tag.name = name
        tag.guid = guid

        logging.debug("Update tag : %s", tag)

        self.getNoteStore().updateTag(self.authToken, tag)
        return True

    @EdamException
    def removeTag(self, guid):
        logging.debug("Delete tag : %s", guid)

        self.getNoteStore().expungeTag(self.authToken, guid)
        return True


class GeekNoteConnector(object):
    evernote = None
    storage = None

    def connectToEvertone(self):
        out.preloader.setMessage("Connect to Evernote...")
        self.evernote = GeekNote()

    def getEvernote(self):
        if self.evernote:
            return self.evernote

        self.connectToEvertone()
        return self.evernote

    def getStorage(self):
        if self.storage:
            return self.storage

        self.storage = self.getEvernote().getStorage()
        return self.storage

class User(GeekNoteConnector):
    """ Work with auth User """

    @GeekNoneDBConnectOnly
    def user(self, full=None):
        if not self.getEvernote().checkAuth():
            out.failureMessage("You not logged in.")
            return tools.exit()

        if full:
            info = self.getEvernote().getUserInfo()
        else:
            info = self.getStorage().getUserInfo()
        out.showUser(info, full)

    @GeekNoneDBConnectOnly
    def login(self):
        if self.getEvernote().checkAuth():
            out.successMessage("You have already logged in.")
            return tools.exit()

        if self.getEvernote().auth():
            out.successMessage("You have successfully logged in.")
        else:
            out.failureMessage("Login error.")
            return tools.exit()

    @GeekNoneDBConnectOnly
    def logout(self, force=None):
        if not self.getEvernote().checkAuth():
            out.successMessage("You have already logged out.")
            return tools.exit()

        if not force and not out.confirm('Are you sure you want to logout?'):
            return tools.exit()

        result = self.getEvernote().removeUser()
        if result:
            out.successMessage("You have successfully logged out.")
        else:
            out.failureMessage("Logout error.")
            return tools.exit()

    @GeekNoneDBConnectOnly
    def settings(self, editor=None):
        storage = self.getStorage()
        if editor:
            if editor == '#GET#':
                editor = storage.getUserprop('editor')
                if not editor:
                    editor = config.DEF_WIN_EDITOR if sys.platform == 'win32' else config.DEF_UNIX_EDITOR
                out.successMessage("Current editor is: %s" % editor)
            else:
                storage.setUserprop('editor', editor)
                out.successMessage("Changes have been saved.")
        else:
            settings = ('Geeknote',
                        '*' * 30,
                        'Version: %s' % config.VERSION,
                        'App dir: %s' % config.APP_DIR,
                        'Error log: %s' % config.ERROR_LOG,
                        'Current editor: %s' % storage.getUserprop('editor'))

            user_settings = storage.getUserprops()

            if user_settings:
                user = user_settings[1]['info']
                settings += ('*' * 30,
                             'Username: %s' % user.username,
                             'Id: %s' % user.id,
                             'Email: %s' % user.email)

            out.printLine('\n'.join(settings))


class Tags(GeekNoteConnector):
    """ Work with auth Notebooks """

    def list(self):
        result = self.getEvernote().findTags()
        out.printList(result)

    def create(self, title):
        self.connectToEvertone()
        out.preloader.setMessage("Creating tag...")
        result = self.getEvernote().createTag(name=title)

        if result:
            out.successMessage("Tag has been successfully created.")
        else:
            out.failureMessage("Error while the process of creating the tag.")
            return tools.exit()

        return result

    def edit(self, tagname, title):
        tag = self._searchTag(tagname)

        out.preloader.setMessage("Updating tag...")
        result = self.getEvernote().updateTag(guid=tag.guid, name=title)

        if result:
            out.successMessage("Tag has been successfully updated.")
        else:
            out.failureMessage("Error while the updating the tag.")
            return tools.exit()

    def remove(self, tagname, force=None):
        tag = self._searchTag(tagname)

        if not force and not out.confirm('Are you sure you want to '
                                         'delete this tag: "%s"?' % tag.name):
            return tools.exit()

        out.preloader.setMessage("Deleting tag...")
        result = self.getEvernote().removeTag(guid=tag.guid)

        if result:
            out.successMessage("Tag has been successfully removed.")
        else:
            out.failureMessage("Error while removing the tag.")

    def _searchTag(self, tag):
        result = self.getEvernote().findTags()
        tag = [item for item in result if item.name == tag]

        if tag:
            tag = tag[0]
        else:
            tag = out.SelectSearchResult(result)

        logging.debug("Selected tag: %s" % str(tag))
        return tag


class Notebooks(GeekNoteConnector):
    """ Work with auth Notebooks """

    def list(self):
        result = self.getEvernote().findNotebooks()
        out.printList(result)

    def create(self, title):
        self.connectToEvertone()
        out.preloader.setMessage("Creating notebook...")
        result = self.getEvernote().createNotebook(name=title)

        if result:
            out.successMessage("Notebook has been successfully created.")
        else:
            out.failureMessage("Error while the process "
                               "of creating the notebook.")
            return tools.exit()

        return result

    def edit(self, notebook, title):
        notebook = self._searchNotebook(notebook)

        out.preloader.setMessage("Updating notebook...")
        result = self.getEvernote().updateNotebook(guid=notebook.guid,
                                                   name=title)

        if result:
            out.successMessage("Notebook has been successfully updated.")
        else:
            out.failureMessage("Error while the updating the notebook.")
            return tools.exit()

    def remove(self, notebook, force=None):
        notebook = self._searchNotebook(notebook)

        if not force and not out.confirm('Are you sure you want to delete'
                                         ' this notebook: "%s"?' % notebook.name):
            return tools.exit()

        out.preloader.setMessage("Deleting notebook...")
        result = self.getEvernote().removeNotebook(guid=notebook.guid)

        if result:
            out.successMessage("Notebook has been successfully removed.")
        else:
            out.failureMessage("Error while removing the notebook.")

    def _searchNotebook(self, notebook):

        result = self.getEvernote().findNotebooks()
        notebook = [item for item in result if item.name == notebook]

        if notebook:
            notebook = notebook[0]
        else:
            notebook = out.SelectSearchResult(result)

        logging.debug("Selected notebook: %s" % str(notebook))
        return notebook

    def getNoteGUID(self, notebook):
        if len(notebook) == 36 and notebook.find("-") == 4:
            return notebook

        result = self.getEvernote().findNotebooks()
        notebook = [item for item in result if item.name == notebook]
        if notebook:
            return notebook[0].guid
        else:
            return None


class Notes(GeekNoteConnector):
    """ Work with Notes """

    findExactOnUpdate = False
    selectFirstOnUpdate = False

    def __init__(self, findExactOnUpdate=False, selectFirstOnUpdate=False):
        self.findExactOnUpdate = bool(findExactOnUpdate)
        self.selectFirstOnUpdate = bool(selectFirstOnUpdate)

    def _editWithEditorInThread(self, inputData, note = None):
        if note:
            self.getEvernote().loadNoteContent(note)
            editor = Editor(note.content)
        else:
            editor = Editor('')
        thread = EditorThread(editor)
        thread.start()

        result = True
        prevChecksum = editor.getTempfileChecksum()
        while True:
            if prevChecksum != editor.getTempfileChecksum() and result:
                newContent = open(editor.tempfile, 'r').read()
                inputData['content'] = Editor.textToENML(newContent)
                if not note:
                    result = self.getEvernote().createNote(**inputData)
                    # TODO: log error if result is False or None
                    if result:
                        note = result
                    else:
                        result = False
                else:
                    result = bool(self.getEvernote().updateNote(guid=note.guid, **inputData))
                    # TODO: log error if result is False

                if result:
                    prevChecksum = editor.getTempfileChecksum()

            if not thread.isAlive():
                # check if thread is alive here before sleep to avoid losing data saved during this 5 secs
                break
            time.sleep(5)
        return result
        
    def create(self, title, content=None, tags=None, notebook=None):

        self.connectToEvertone()

        # Optional Content.
        content = content or " "

        inputData = self._parceInput(title, content, tags, notebook)

        if inputData['content'] == config.EDITOR_OPEN:
            result = self._editWithEditorInThread(inputData)
        else:
            out.preloader.setMessage("Creating note...")
            result = bool(self.getEvernote().createNote(**inputData))

        if result:
            out.successMessage("Note has been successfully created.")
        else:
            out.failureMessage("Error while creating the note.")

    def edit(self, note, title=None, content=None, tags=None, notebook=None):

        self.connectToEvertone()
        note = self._searchNote(note)

        inputData = self._parceInput(title, content, tags, notebook, note)

        if inputData['content'] == config.EDITOR_OPEN:
            result = self._editWithEditorInThread(inputData, note)
        else:
            out.preloader.setMessage("Saving note...")
            result = bool(self.getEvernote().updateNote(guid=note.guid, **inputData))

        if result:
            out.successMessage("Note has been successfully saved.")
        else:
            out.failureMessage("Error while saving the note.")

    def remove(self, note, force=None):

        self.connectToEvertone()
        note = self._searchNote(note)

        if not force and not out.confirm('Are you sure you want to '
                                         'delete this note: "%s"?' % note.title):
            return tools.exit()

        out.preloader.setMessage("Deleting note...")
        result = self.getEvernote().removeNote(note.guid)

        if result:
            out.successMessage("Note has been successful deleted.")
        else:
            out.failureMessage("Error while deleting the note.")

    def show(self, note):

        self.connectToEvertone()

        note = self._searchNote(note)

        out.preloader.setMessage("Loading note...")
        self.getEvernote().loadNoteContent(note)

        out.showNote(note)

    def _parceInput(self, title=None, content=None, tags=None, notebook=None, note=None):
        result = {
            "title": title,
            "content": content,
            "tags": tags,
            "notebook": notebook,
        }
        result = tools.strip(result)

        # if get note without params
        if note and title is None and content is None and tags is None and notebook is None:
            content = config.EDITOR_OPEN

        if title is None and note:
            result['title'] = note.title

        if content:
            if content != config.EDITOR_OPEN:
                if isinstance(content, str) and os.path.isfile(content):
                    logging.debug("Load content from the file")
                    content = open(content, "r").read()

                logging.debug("Convert content")
                content = Editor.textToENML(content)
            result['content'] = content

        if tags:
            result['tags'] = tools.strip(tags.split(','))

        if notebook:
            notepadGuid = Notebooks().getNoteGUID(notebook)
            if notepadGuid is None:
                newNotepad = Notebooks().create(notebook)
                notepadGuid = newNotepad.guid

            result['notebook'] = notepadGuid
            logging.debug("Search notebook")

        return result

    def _searchNote(self, note):
        note = tools.strip(note)

        # load search result
        result = self.getStorage().getSearch()
        if result and tools.checkIsInt(note) and 1 <= int(note) <= len(result.notes):
            note = result.notes[int(note) - 1]

        else:
            request = self._createSearchRequest(search=note)

            logging.debug("Search notes: %s" % request)
            result = self.getEvernote().findNotes(request, 20)

            logging.debug("Search notes result: %s" % str(result))
            if result.totalNotes == 0:
                out.successMessage("Notes have not been found.")
                return tools.exit()

            elif result.totalNotes == 1 or self.selectFirstOnUpdate:
                note = result.notes[0]

            else:
                logging.debug("Choose notes: %s" % str(result.notes))
                note = out.SelectSearchResult(result.notes)

        logging.debug("Selected note: %s" % str(note))
        return note

    def find(self, search=None, tags=None, notebooks=None,
             date=None, exact_entry=None, content_search=None,
             with_url=None, count=None, ):

        request = self._createSearchRequest(search, tags, notebooks,
                                            date, exact_entry,
                                            content_search)

        if not count:
            count = 20
        else:
            count = int(count)

        logging.debug("Search count: %s", count)

        createFilter = True if search == "*" else False
        result = self.getEvernote().findNotes(request, count, createFilter)

        # Reduces the count by the amount of notes already retrieved
        update_count = lambda c: max(c - len(result.notes), 0)
        
        count = update_count(count)
        
        # Evernote api will only return so many notes in one go. Checks for more 
        # notes to come whilst obeying count rules
        while ((result.totalNotes != len(result.notes)) and count != 0):
            offset = len(result.notes)
            result.notes += self.getEvernote().findNotes(request, count,
                    createFilter, offset).notes
            count = update_count(count)

        if result.totalNotes == 0:
            out.successMessage("Notes have not been found.")

        # save search result
        # print result
        self.getStorage().setSearch(result)

        out.SearchResult(result.notes, request, showUrl=with_url)

    def _createSearchRequest(self, search=None, tags=None,
                             notebooks=None, date=None,
                             exact_entry=None, content_search=None):

        request = ""
        if notebooks:
            for notebook in tools.strip(notebooks.split(',')):
                if notebook.startswith('-'):
                    request += '-notebook:"%s" ' % tools.strip(notebook[1:])
                else:
                    request += 'notebook:"%s" ' % tools.strip(notebook)

        if tags:
            for tag in tools.strip(tags.split(',')):

                if tag.startswith('-'):
                    request += '-tag:"%s" ' % tag[1:]
                else:
                    request += 'tag:"%s" ' % tag

        if date:
            date = tools.strip(date.split('-'))
            try:
                dateStruct = time.strptime(date[0] + " 00:00:00", "%d.%m.%Y %H:%M:%S")
                request += 'created:%s ' % time.strftime("%Y%m%d", time.localtime(time.mktime(dateStruct)))
                if len(date) == 2:
                    dateStruct = time.strptime(date[1] + " 00:00:00", "%d.%m.%Y %H:%M:%S")
                request += '-created:%s ' % time.strftime("%Y%m%d", time.localtime(time.mktime(dateStruct) + 60 * 60 * 24))
            except ValueError, e:
                out.failureMessage('Incorrect date format in --date attribute. '
                                   'Format: %s' % time.strftime("%d.%m.%Y", time.strptime('19991231', "%Y%m%d")))
                return tools.exit()

        if search:
            search = tools.strip(search)
            if exact_entry or self.findExactOnUpdate:
                search = '"%s"' % search

            if content_search:
                request += "%s" % search
            else:
                request += "intitle:%s" % search

        logging.debug("Search request: %s", request)
        return request


def modifyArgsByStdinStream():
    """Parse the stdin stream for arguments"""
    content = sys.stdin.read()
    content = tools.stdinEncode(content)

    if not content:
        out.failureMessage("Input stream is empty.")
        return tools.exit()

    title = ' '.join(content.split(' ', 5)[:-1])
    title = re.sub(r'(\r\n|\r|\n)', r' ', title)
    if not title:
        out.failureMessage("Error while creating title of note from stream.")
        return tools.exit()
    elif len(title) > 50:
        title = title[0:50] + '...'

    ARGS = {
        'title': title,
        'content': content
    }

    return ('create', ARGS)


def main(args=None):
    try:
        # if terminal
        if config.IS_IN_TERMINAL:
            sys_argv = sys.argv[1:]
            if isinstance(args, list):
                sys_argv = args

            sys_argv = tools.decodeArgs(sys_argv)

            COMMAND = sys_argv[0] if len(sys_argv) >= 1 else None

            aparser = argparser(sys_argv)
            ARGS = aparser.parse()

        # if input stream
        else:
            COMMAND, ARGS = modifyArgsByStdinStream()

        # error or help
        if COMMAND is None or ARGS is False:
            return tools.exit()

        logging.debug("CLI options: %s", str(ARGS))

        # Users
        if COMMAND == 'user':
            User().user(**ARGS)

        if COMMAND == 'login':
            User().login(**ARGS)

        if COMMAND == 'logout':
            User().logout(**ARGS)

        if COMMAND == 'settings':
            User().settings(**ARGS)

        # Notes
        if COMMAND == 'create':
            Notes().create(**ARGS)

        if COMMAND == 'edit':
            Notes().edit(**ARGS)

        if COMMAND == 'remove':
            Notes().remove(**ARGS)

        if COMMAND == 'show':
            Notes().show(**ARGS)

        if COMMAND == 'find':
            Notes().find(**ARGS)

        # Notebooks
        if COMMAND == 'notebook-list':
            Notebooks().list(**ARGS)

        if COMMAND == 'notebook-create':
            Notebooks().create(**ARGS)

        if COMMAND == 'notebook-edit':
            Notebooks().edit(**ARGS)

        if COMMAND == 'notebook-remove':
            Notebooks().remove(**ARGS)

        # Tags
        if COMMAND == 'tag-list':
            Tags().list(**ARGS)

        if COMMAND == 'tag-create':
            Tags().create(**ARGS)

        if COMMAND == 'tag-edit':
            Tags().edit(**ARGS)

        if COMMAND == 'tag-remove':
            Tags().remove(**ARGS)

    except (KeyboardInterrupt, SystemExit, tools.ExitException):
        pass

    except Exception, e:
        traceback.print_exc()
        logging.error("App error: %s", str(e))

    # exit preloader
    tools.exit()

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = gnsync
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import argparse
import glob
import logging
import string

from geeknote import GeekNote
from storage import Storage
from editor import Editor
import tools

# set default logger (write log to file)
def_logpath = os.path.join(os.getenv('USERPROFILE') or os.getenv('HOME'),  'GeekNoteSync.log')
formatter = logging.Formatter('%(asctime)-15s : %(message)s')
handler = logging.FileHandler(def_logpath)
handler.setFormatter(formatter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)


def log(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception, e:
            logger.error("%s", str(e))
    return wrapper


@log
def reset_logpath(logpath):
    """
    Reset logpath to path from command line
    """
    global logger

    if not logpath:
        return

    # remove temporary log file if it's empty
    if os.path.isfile(def_logpath):
        if os.path.getsize(def_logpath) == 0:
            os.remove(def_logpath)

    # save previous handlers
    handlers = logger.handlers

    # remove old handlers
    for handler in handlers:
        logger.removeHandler(handler)

    # try to set new file handler
    handler = logging.FileHandler(logpath)
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class GNSync:

    notebook_name = None
    path = None
    mask = None
    twoway = None

    notebook_guid = None
    all_set = False

    @log
    def __init__(self, notebook_name, path, mask, format, twoway=False):
        # check auth
        if not Storage().getUserToken():
            raise Exception("Auth error. There is not any oAuthToken.")

        #set path
        if not path:
            raise Exception("Path to sync directories does not select.")

        if not os.path.exists(path):
            raise Exception("Path to sync directories does not exist.")

        self.path = path

        #set mask
        if not mask:
            mask = "*.*"

        self.mask = mask

        #set format
        if not format:
            format = "plain"

        self.format = format

        if format == "markdown":
            self.extension = ".md"
        else:
            self.extension = ".txt"

        self.twoway = twoway

        logger.info('Sync Start')

        #set notebook
        self.notebook_guid,\
        self.notebook_name = self._get_notebook(notebook_name, path)

        # all is Ok
        self.all_set = True

    @log
    def sync(self):
        """
        Synchronize files to notes
        """
        if not self.all_set:
            return

        files = self._get_files()
        notes = self._get_notes()

        for f in files:
            has_note = False
            for n in notes:
                if f['name'] == n.title:
                    has_note = True
                    if f['mtime'] > n.updated:
                        self._update_note(f, n)
                        break

            if not has_note:
                self._create_note(f)

        if self.twoway:
            for n in notes:
                has_file = False
                for f in files:
                    if f['name'] == n.title:
                        has_file = True
                        if f['mtime'] < n.updated:
                            self._update_file(f, n)
                            break

                if not has_file:
                    self._create_file(n)

        logger.info('Sync Complete')

    @log
    def _update_note(self, file_note, note):
        """
        Updates note from file
        """
        content = self._get_file_content(file_note['path'])

        result = GeekNote().updateNote(
            guid=note.guid,
            title=note.title,
            content=content,
            notebook=self.notebook_guid)

        if result:
            logger.info('Note "{0}" was updated'.format(note.title))
        else:
            raise Exception('Note "{0}" was not updated'.format(note.title))

        return result

    @log
    def _update_file(self, file_note, note):
        """
        Updates file from note
        """
        GeekNote().loadNoteContent(note)
        content = Editor.ENMLtoText(note.content)
        open(file_note['path'], "w").write(content)

    @log
    def _create_note(self, file_note):
        """
        Creates note from file
        """

        content = self._get_file_content(file_note['path'])

        if content is None:
            return

        result = GeekNote().createNote(
            title=file_note['name'],
            content=content,
            notebook=self.notebook_guid,
            created=file_note['mtime'])

        if result:
            logger.info('Note "{0}" was created'.format(file_note['name']))
        else:
            raise Exception('Note "{0}" was not' \
                            ' created'.format(file_note['name']))

        return result

    @log
    def _create_file(self, note):
        """
        Creates file from note
        """
        GeekNote().loadNoteContent(note)
        content = Editor.ENMLtoText(note.content)
        path = os.path.join(self.path, note.title + self.extension)
        open(path, "w").write(content)
        return True

    @log
    def _get_file_content(self, path):
        """
        Get file content.
        """
        content = open(path, "r").read()

        # strip unprintable characters
        content = ''.join(s for s in content if s in string.printable)
        content = Editor.textToENML(content=content, raise_ex=True, format=self.format)
        
        if content is None:
            logger.warning("File {0}. Content must be " \
                           "an UTF-8 encode.".format(path))
            return None

        return content

    @log
    def _get_notebook(self, notebook_name, path):
        """
        Get notebook guid and name.
        Takes default notebook if notebook's name does not select.
        """
        notebooks = GeekNote().findNotebooks()

        if not notebook_name:
            notebook_name = os.path.basename(os.path.realpath(path))

        notebook = [item for item in notebooks if item.name == notebook_name]
        guid = None
        if notebook:
            guid = notebook[0].guid

        if not guid:
            notebook = GeekNote().createNotebook(notebook_name)

            if(notebook):
                logger.info('Notebook "{0}" was' \
                            ' created'.format(notebook_name))
            else:
                raise Exception('Notebook "{0}" was' \
                                ' not created'.format(notebook_name))

            guid = notebook.guid

        return (guid, notebook_name)

    @log
    def _get_files(self):
        """
        Get files by self.mask from self.path dir.
        """

        file_paths = glob.glob(os.path.join(self.path, self.mask))

        files = []
        for f in file_paths:
            if os.path.isfile(f):
                file_name = os.path.basename(f)
                file_name = os.path.splitext(file_name)[0]

                mtime = int(os.path.getmtime(f) * 1000)

                files.append({'path': f, 'name': file_name, 'mtime': mtime})

        return files

    @log
    def _get_notes(self):
        """
        Get notes from evernote.
        """
        keywords = 'notebook:"{0}"'.format(tools.strip(self.notebook_name))
        return GeekNote().findNotes(keywords, 10000).notes


def main():
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument('--path', '-p', action='store', help='Path to synchronize directory')
        parser.add_argument('--mask', '-m', action='store', help='Mask of files to synchronize. Default is "*.*"')
        parser.add_argument('--format', '-f', action='store', default='plain', choices=['plain', 'markdown'], help='The format of the file contents. Default is "plain". Valid values are "plain" and "markdown"')
        parser.add_argument('--notebook', '-n', action='store', help='Notebook name for synchronize. Default is default notebook')
        parser.add_argument('--logpath', '-l', action='store', help='Path to log file. Default is GeekNoteSync in home dir')
        parser.add_argument('--two-way', '-t', action='store', help='Two-way sync')

        args = parser.parse_args()

        path = args.path if args.path else None
        mask = args.mask if args.mask else None
        format = args.format if args.format else None
        notebook = args.notebook if args.notebook else None
        logpath = args.logpath if args.logpath else None
        twoway = True if args.two_way else False

        reset_logpath(logpath)

        GNS = GNSync(notebook, path, mask, format, twoway)
        GNS.sync()

    except (KeyboardInterrupt, SystemExit, tools.ExitException):
        pass

    except Exception, e:
        logger.error(str(e))

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = log
# -*- coding: utf-8 -*-

import logging
import config

if config.DEBUG:
    FORMAT = "%(filename)s %(funcName)s %(lineno)d : %(message)s"
    logging.basicConfig(format=FORMAT, level=logging.DEBUG)
else:
    FORMAT = "%(asctime)-15s %(module)s %(funcName)s %(lineno)d : %(message)s"
    logging.basicConfig(format=FORMAT, filename=config.ERROR_LOG)

########NEW FILE########
__FILENAME__ = oauth
# -*- coding: utf-8 -*-

import httplib
import time
import Cookie
import uuid
from urllib import urlencode, unquote
from urlparse import urlparse

import out
import tools
import config
from log import logging


class GeekNoteAuth(object):

    consumerKey = config.CONSUMER_KEY
    consumerSecret = config.CONSUMER_SECRET

    url = {
        "base": config.USER_BASE_URL,
        "oauth": "/OAuth.action?oauth_token=%s",
        "access": "/OAuth.action",
        "token" : "/oauth",
        "login" : "/Login.action",
        "tfa"   : "/OTCAuth.action",
    }

    cookies = {}

    postData = {
        'login': {
            'login': 'Sign in',
            'username': '',
            'password': '',
            'targetUrl': None,
        },
        'access': {
            'authorize': 'Authorize',
            'oauth_token': None,
            'oauth_callback': None,
            'embed': 'false',
        },
        'tfa': {
            'code': '',
            'login': 'Sign in',
        },
    }

    username = None
    password = None
    tmpOAuthToken = None
    verifierToken = None
    OAuthToken = None
    incorrectLogin = 0
    incorrectCode = 0
    code = None

    def getTokenRequestData(self, **kwargs):
        params = {
            'oauth_consumer_key': self.consumerKey,
            'oauth_signature': self.consumerSecret + '%26',
            'oauth_signature_method': 'PLAINTEXT',
            'oauth_timestamp': str(int(time.time())),
            'oauth_nonce': uuid.uuid4().hex
        }

        if kwargs:
            params = dict(params.items() + kwargs.items())

        return params

    def loadPage(self, url, uri=None, method="GET", params=""):
        if not url:
            logging.error("Request URL undefined")
            tools.exit()

        if not uri:
            urlData = urlparse(url)
            url = urlData.netloc
            uri = urlData.path + '?' + urlData.query

        # prepare params, append to uri
        if params:
            params = urlencode(params)
            if method == "GET":
                uri += ('?' if uri.find('?') == -1 else '&') + params
                params = ""

        # insert local cookies in request
        headers = {
            "Cookie": '; '.join([key + '=' + self.cookies[key] for key in self.cookies.keys()])
        }

        if method == "POST":
            headers["Content-type"] = "application/x-www-form-urlencoded"

        logging.debug("Request URL: %s:/%s > %s # %s", url,
                      uri, unquote(params), headers["Cookie"])

        conn = httplib.HTTPSConnection(url)
        conn.request(method, uri, params, headers)
        response = conn.getresponse()
        data = response.read()
        conn.close()

        logging.debug("Response : %s > %s",
                      response.status,
                      response.getheaders())
        result = tools.Struct(status=response.status,
                              location=response.getheader('location', None),
                              data=data)

        # update local cookies
        sk = Cookie.SimpleCookie(response.getheader("Set-Cookie", ""))
        for key in sk:
            self.cookies[key] = sk[key].value

        return result

    def parseResponse(self, data):
        data = unquote(data)
        return dict(item.split('=', 1) for item in data.split('?')[-1].split('&'))

    def getToken(self):
        out.preloader.setMessage('Authorize...')
        self.getTmpOAuthToken()

        self.login()

        out.preloader.setMessage('Allow Access...')
        self.allowAccess()

        out.preloader.setMessage('Getting Token...')
        self.getOAuthToken()

        #out.preloader.stop()
        return self.OAuthToken

    def getTmpOAuthToken(self):
        response = self.loadPage(self.url['base'],
                                 self.url['token'],
                                 "GET",
                                 self.getTokenRequestData(
                                     oauth_callback="https://" + self.url['base']
                                 ))

        if response.status != 200:
            logging.error("Unexpected response status on get "
                          "temporary oauth_token 200 != %s", response.status)
            tools.exit()

        responseData = self.parseResponse(response.data)
        if 'oauth_token' not in responseData:
            logging.error("OAuth temporary not found")
            tools.exit()

        self.tmpOAuthToken = responseData['oauth_token']

        logging.debug("Temporary OAuth token : %s", self.tmpOAuthToken)

    def handleTwoFactor(self):
        self.code = out.GetUserAuthCode()
        self.postData['tfa']['code'] = self.code
        response = self.loadPage(self.url['base'], self.url['tfa']+";jsessionid="+self.cookies['JSESSIONID'], "POST", self.postData['tfa'])
        if not response.location and response.status == 200:
            if self.incorrectCode < 3:
                out.preloader.stop()
                out.printLine('Sorry, incorrect two factor code')
                out.preloader.setMessage('Authorize...')
                self.incorrectCode += 1
                return self.handleTwoFactor()
            else:
                logging.error("Incorrect two factor code")

        if not response.location:
            logging.error("Target URL was not found in the response on login")
            tools.exit()

    def login(self):
        response = self.loadPage(self.url['base'],
                                 self.url['login'],
                                 "GET",
                                 {'oauth_token': self.tmpOAuthToken})

        if response.status != 200:
            logging.error("Unexpected response status "
                          "on login 200 != %s", response.status)
            tools.exit()

        if 'JSESSIONID' not in self.cookies:
            logging.error("Not found value JSESSIONID in the response cookies")
            tools.exit()

        # get login/password
        self.username, self.password = out.GetUserCredentials()

        self.postData['login']['username'] = self.username
        self.postData['login']['password'] = self.password
        self.postData['login']['targetUrl'] = self.url['oauth'] % self.tmpOAuthToken
        response = self.loadPage(self.url['base'],
                                 self.url['login'] + ";jsessionid=" + self.cookies['JSESSIONID'],
                                 "POST",
                                 self.postData['login'])

        if not response.location and response.status == 200:
            if self.incorrectLogin < 3:
                out.preloader.stop()
                out.printLine('Sorry, incorrect login or password')
                out.preloader.setMessage('Authorize...')
                self.incorrectLogin += 1
                return self.login()
            else:
                logging.error("Incorrect login or password")

        if not response.location:
            logging.error("Target URL was not found in the response on login")
            tools.exit()

        if response.status == 302:
            # the user has enabled two factor auth
            return self.handleTwoFactor()


        logging.debug("Success authorize, redirect to access page")

        #self.allowAccess(response.location)

    def allowAccess(self):
        access = self.postData['access']
        access['oauth_token'] = self.tmpOAuthToken
        access['oauth_callback'] = "https://" + self.url['base']
        response = self.loadPage(self.url['base'],
                                 self.url['access'],
                                 "POST", access)

        if response.status != 302:
            logging.error("Unexpected response status on allowing "
                          "access 302 != %s", response.status)
            tools.exit()

        responseData = self.parseResponse(response.location)
        if 'oauth_verifier' not in responseData:
            logging.error("OAuth verifier not found")
            tools.exit()

        self.verifierToken = responseData['oauth_verifier']

        logging.debug("OAuth verifier token take")

        #self.getOAuthToken(verifier)

    def getOAuthToken(self):
        response = self.loadPage(self.url['base'],
                                 self.url['token'],
                                 "GET",
                                 self.getTokenRequestData(
                                     oauth_token=self.tmpOAuthToken,
                                     oauth_verifier=self.verifierToken))

        if response.status != 200:
            logging.error("Unexpected response status on "
                          "getting oauth token 200 != %s", response.status)
            tools.exit()

        responseData = self.parseResponse(response.data)
        if 'oauth_token' not in responseData:
            logging.error("OAuth token not found")
            tools.exit()

        logging.debug("OAuth token take : %s", responseData['oauth_token'])
        self.OAuthToken = responseData['oauth_token']

########NEW FILE########
__FILENAME__ = out
# -*- coding: utf-8 -*-

import getpass
import thread
import time
import sys

import tools
from editor import Editor
import config


def preloaderPause(fn, *args, **kwargs):
    def wrapped(*args, **kwargs):

        if not preloader.isLaunch:
            return fn(*args, **kwargs)

        preloader.stop()
        result = fn(*args, **kwargs)
        preloader.launch()

        return result

    return wrapped


def preloaderStop(fn, *args, **kwargs):
    def wrapped(*args, **kwargs):

        if not preloader.isLaunch:
            return fn(*args, **kwargs)

        preloader.stop()
        result = fn(*args, **kwargs)
        return result

    return wrapped


class preloader(object):

    progress = (">  ", ">> ", ">>>", " >>", "  >", "   ")
    clearLine = "\r" + " " * 40 + "\r"
    message = None
    isLaunch = False
    counter = 0

    @staticmethod
    def setMessage(message, needLaunch=True):
        preloader.message = message
        if not preloader.isLaunch and needLaunch:
            preloader.launch()

    @staticmethod
    def launch():
        if not config.IS_OUT_TERMINAL:
            return
        preloader.counter = 0
        preloader.isLaunch = True
        thread.start_new_thread(preloader.draw, ())

    @staticmethod
    def stop():
        if not config.IS_OUT_TERMINAL:
            return
        preloader.counter = -1
        printLine(preloader.clearLine, "")
        preloader.isLaunch = False

    @staticmethod
    def exit():
        preloader.stop()
        thread.exit()

    @staticmethod
    def draw():
        try:
            if not preloader.isLaunch:
                return

            while preloader.counter >= 0:
                printLine(preloader.clearLine, "")
                preloader.counter += 1
                printLine("%s : %s" % (preloader.progress[preloader.counter % len(preloader.progress)], preloader.message), "")

                time.sleep(0.3)
        except:
            pass


@preloaderPause
def GetUserCredentials():
    """Prompts the user for a username and password."""
    try:
        login = None
        password = None
        if login is None:
            login = rawInput("Login: ")

        if password is None:
            password = rawInput("Password: ", True)
    except (KeyboardInterrupt, SystemExit):
        tools.exit()

    return (login, password)

@preloaderPause
def GetUserAuthCode():
    """Prompts the user for a two factor auth code."""
    try:
        code = None
        if code is None:
          code = rawInput("Two-Factor Authentication Code: ")
    except (KeyboardInterrupt, SystemExit):
        tools.exit()

    return code

@preloaderStop
def SearchResult(listItems, request, **kwargs):
    """Print search results."""
    printLine("Search request: %s" % request)
    printList(listItems, **kwargs)


@preloaderStop
def SelectSearchResult(listItems, **kwargs):
    """Select a search result."""
    return printList(listItems, showSelector=True, **kwargs)


@preloaderStop
def confirm(message):
    printLine(message)
    try:
        while True:
            answer = rawInput("Yes/No: ")
            if answer.lower() in ["yes", "ye", "y"]:
                return True
            if answer.lower() in ["no", "n"]:
                return False
            failureMessage('Incorrect answer "%s", '
                           'please try again:\n' % answer)
    except (KeyboardInterrupt, SystemExit):
        tools.exit()


@preloaderStop
def showNote(note):
    separator("#", "TITLE")
    printLine(note.title)
    separator("=", "META")
    printLine("Created: %s" %
              (printDate(note.created).ljust(15, " ")))
    printLine("Updated: %s" %
              (printDate(note.updated).ljust(15, " ")))
    separator("-", "CONTENT")
    if note.tagNames:
        printLine("Tags: %s" % ', '.join(note.tagNames))

    printLine(Editor.ENMLtoText(note.content))


@preloaderStop
def showUser(user, fullInfo):
    def line(key, value):
        if value:
            printLine("%s : %s" % (key.ljust(16, " "), value))

    separator("#", "USER INFO")
    line('Username', user.username)
    line('Name', user.name)
    line('Email', user.email)

    if fullInfo:
        limit = (int(user.accounting.uploadLimit) / 1024 / 1024)
        endlimit = time.gmtime(user.accounting.uploadLimitEnd / 1000)
        line('Upload limit', "%.2f" % limit)
        line('Upload limit end', time.strftime("%d.%m.%Y", endlimit))


@preloaderStop
def successMessage(message):
    """ Displaying a message. """
    printLine(message, "\n")


@preloaderStop
def failureMessage(message):
    """ Displaying a message."""
    printLine(message, "\n")


def separator(symbol="", title=""):
    size = 40
    if title:
        sw = (size - len(title) + 2) / 2
        printLine("%s %s %s" % (symbol * sw,
                                title,
                                symbol * (sw - (len(title) + 1) % 2)))

    else:
        printLine(symbol * size + "\n")


@preloaderStop
def printList(listItems, title="", showSelector=False,
              showByStep=20, showUrl=False):

    if title:
        separator("=", title)

    total = len(listItems)
    printLine("Total found: %d" % total)
    for key, item in enumerate(listItems):
        key += 1

        printLine("%s : %s%s%s" % (
            str(key).rjust(3, " "),
            printDate(item.created).ljust(18, " ") if hasattr(item, 'created') else '',
            item.title if hasattr(item, 'title') else item.name,
            " " + (">>> " + config.NOTE_URL % item.guid) if showUrl else '',))

        if key % showByStep == 0 and key < total:
            printLine("-- More --", "\r")
            tools.getch()
            printLine(" " * 12, "\r")

    if showSelector:
        printLine("  0 : -Cancel-")
        try:
            while True:
                num = rawInput(": ")
                if tools.checkIsInt(num) and 1 <= int(num) <= total:
                    return listItems[int(num) - 1]
                if num == '0':
                    exit(1)
                failureMessage('Incorrect number "%s", '
                               'please try again:\n' % num)
        except (KeyboardInterrupt, SystemExit):
            tools.exit()


def rawInput(message, isPass=False):
    if isPass:
        data = getpass.getpass(message)
    else:
        data = raw_input(message)
    return tools.stdinEncode(data)


def printDate(timestamp):
    return time.strftime("%d/%m/%Y %H:%M", time.localtime(timestamp/1000))

def printLine(line, endLine="\n"):
    message = line + endLine
    message = tools.stdoutEncode(message)
    try:
        sys.stdout.write(message)
    except:
        pass
    sys.stdout.flush()


def printAbout():
    printLine('Version: %s' % str(config.VERSION))
    printLine('Geeknote - a command line client for Evernote.')
    printLine('Use geeknote --help to read documentation.')
    printLine('And visit www.geeknote.me to check for updates.')

########NEW FILE########
__FILENAME__ = storage
# -*- coding: utf-8 -*-

import os
import datetime
import pickle

from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import logging
import config

db_path = os.path.join(config.APP_DIR, 'database.db')
engine = create_engine('sqlite:///' + db_path)
Base = declarative_base()


class Userprop(Base):
    __tablename__ = 'user_props'

    id = Column(Integer, primary_key=True)
    key = Column(String(255))
    value = Column(PickleType())

    def __init__(self, key, value):
        self.key = key
        self.value = value

    def __repr__(self):
        return "<Userprop('{0}','{1})>".format(self.key, self.value)


class Setting(Base):
    __tablename__ = 'settings'

    id = Column(Integer, primary_key=True)
    key = Column(String(255))
    value = Column(String(1000))

    def __init__(self, key, value):
        self.key = key
        self.value = value

    def __repr__(self):
        return "<Setting('{0}','{1})>".format(self.key, self.value)


class Notebook(Base):
    __tablename__ = 'notebooks'

    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    guid = Column(String(1000))
    timestamp = Column(DateTime(), nullable=False)

    def __init__(self, guid, name):
        self.guid = guid
        self.name = name
        self.timestamp = datetime.datetime.now()

    def __repr__(self):
        return "<Notebook('{0}')>".format(self.name)


class Tag(Base):
    __tablename__ = 'tags'

    id = Column(Integer, primary_key=True)
    tag = Column(String(255))
    guid = Column(String(1000))
    timestamp = Column(DateTime(), nullable=False)

    def __init__(self, guid, tag):
        self.guid = guid
        self.tag = tag
        self.timestamp = datetime.datetime.now()

    def __repr__(self):
        return "<Tag('{0}')>".format(self.tag)


class Search(Base):
    __tablename__ = 'search'

    id = Column(Integer, primary_key=True)
    search_obj = Column(PickleType())
    timestamp = Column(DateTime(), nullable=False)

    def __init__(self, search_obj):
        self.search_obj = search_obj
        self.timestamp = datetime.datetime.now()

    def __repr__(self):
        return "<Search('{0}')>".format(self.timestamp)


class Storage(object):
    """
    Class for using database.
    """
    session = None

    def __init__(self):
        logging.debug("Storage engine : %s", engine)
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        self.session = Session()

    def logging(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception, e:
                logging.error("%s : %s", func.__name__, str(e))
                return False
        return wrapper

    @logging
    def createUser(self, oAuthToken, info_obj):
        """
        Create user. oAuthToken must be not empty string
        info_obj must be not empty string
        Previous user and user's properties will be removed
        return True if all done
        return False if something wrong
        """
        if not oAuthToken:
            raise Exception("Empty oAuth token")

        if not info_obj:
            raise Exception("Empty user info")

        for item in self.session.query(Userprop).all():
            self.session.delete(item)

        self.setUserprop('oAuthToken', oAuthToken)
        self.setUserprop('info', info_obj)

        return True

    @logging
    def removeUser(self):
        """
        Remove user.
        return True if all done
        return False if something wrong
        """
        for item in self.session.query(Userprop).all():
            self.session.delete(item)
        self.session.commit()
        return True

    @logging
    def getUserToken(self):
        """
        Get user's oAuth token
        return oAuth token if it exists
        return None if there is not oAuth token yet
        return False if something wrong
        """
        return self.getUserprop('oAuthToken')

    @logging
    def getUserInfo(self):
        """
        Get user's oAuth token
        return oAuth token if it exists
        return None if there is not oAuth token yet
        return False if something wrong
        """
        return self.getUserprop('info')

    @logging
    def getUserprops(self):
        """
        Get all user's properties
        return list of dict if all done
        return [] there are not any user's properties yet
        return False if something wrong
        """
        props = self.session.query(Userprop).all()
        return [{item.key: pickle.loads(item.value)} for item in props]

    @logging
    def getUserprop(self, key):
        """
        Get user's property by key
        return property's value
        return False if something wrong
        """
        instance = self.session.query(Userprop).filter_by(key=key).first()
        if instance:
            return pickle.loads(instance.value)
        else:
            return None

    @logging
    def setUserprop(self, key, value):
        """
        Set single user's property. User's property must have key and value
        return True if all done
        return False if something wrong
        """
        value = pickle.dumps(value)

        instance = self.session.query(Userprop).filter_by(key=key).first()
        if instance:
            instance.value = value
        else:
            instance = Userprop(key, value)
            self.session.add(instance)

        self.session.commit()
        return True

    @logging
    def setSettings(self, settings):
        """
        Set multuple settings. Settings must be an instanse dict
        return True if all done
        return False if something wrong
        """
        if not isinstance(settings, dict):
            raise Exception("Wrong settings")

        for key in settings.keys():
            if not settings[key]:
                raise Exception("Wrong setting's item")

            instance = self.session.query(Setting).filter_by(key=key).first()
            if instance:
                instance.value = pickle.dumps(settings[key])
            else:
                instance = Setting(key, pickle.dumps(settings[key]))
                self.session.add(instance)

        self.session.commit()
        return True

    @logging
    def getSettings(self):
        """
        Get all settings
        return list of dict if all done
        return [] there are not any settings yet
        return False if something wrong
        """
        settings = self.session.query(Setting).all()
        result = {}
        for item in settings:
            result[item.key] = item.value
        return result

    @logging
    def setSetting(self, key, value):
        """
        Set single setting. Settings must have key and value
        return True if all done
        return False if something wrong
        """
        instance = self.session.query(Setting).filter_by(key=key).first()
        if instance:
            instance.value = value
        else:
            instance = Setting(key, value)
            self.session.add(instance)

        self.session.commit()
        return True

    @logging
    def getSetting(self, key):
        """
        Get setting by key
        return setting's value
        return False if something wrong
        """
        instance = self.session.query(Setting).filter_by(key=key).first()
        if instance:
            return str(instance.value)
        else:
            return None

    @logging
    def setTags(self, tags):
        """
        Set tags. Tags must be an instanse of dict
        Previous tags items will be removed
        return True if all done
        return False if something wrong
        """
        if not isinstance(tags, dict):
            raise Exception("Wrong tags")

        for item in self.session.query(Tag).all():
            self.session.delete(item)

        for key in tags.keys():
            if not tags[key]:
                raise Exception("Wrong tag's item")

            instance = Tag(key, tags[key])
            self.session.add(instance)

        self.session.commit()
        return True

    @logging
    def getTags(self):
        """
        Get all tags
        return list of dicts of tags if all done
        return [] there are not any tags yet
        return False if something wrong
        """
        tags = self.session.query(Tag).all()
        result = {}
        for item in tags:
            result[item.guid] = item.tag
        return result

    @logging
    def setNotebooks(self, notebooks):
        """
        Set notebooks. Notebooks must be an instanse of dict
        Previous notebooks items will be removed
        return True if all done
        return False if something wrong
        """
        if not isinstance(notebooks, dict):
            raise Exception("Wrong notebooks")

        for item in self.session.query(Notebook).all():
            self.session.delete(item)

        for key in notebooks.keys():
            if not notebooks[key]:
                raise Exception("Wrong notebook's item")

            instance = Notebook(key, notebooks[key])
            self.session.add(instance)

        self.session.commit()
        return True

    @logging
    def getNotebooks(self):
        """
        Get all notebooks
        return list of notebooks if all done
        return [] there are not any notebooks yet
        return False if something wrong
        """
        notebooks = self.session.query(Notebook).all()
        result = {}
        for item in notebooks:
            result[item.guid] = item.name
        return result

    @logging
    def setSearch(self, search_obj):
        """
        Set searching.
        Previous searching items will be removed
        return True if all done
        return False if something wrong
        """
        for item in self.session.query(Search).all():
            self.session.delete(item)

        search = pickle.dumps(search_obj)
        instance = Search(search)
        self.session.add(instance)

        self.session.commit()
        return True

    @logging
    def getSearch(self):
        """
        Get last searching
        return list of dicts of last searching if all done
        return [] there are not any searching yet
        return False if something wrong
        """
        search = self.session.query(Search).first()
        if search:
            return pickle.loads(search.search_obj)
        else:
            return None

########NEW FILE########
__FILENAME__ = tools
# -*- coding: utf-8 -*-

import out
import sys
import time


def checkIsInt(value):
    try:
        int(value)
        return True
    except ValueError:
        return False


def getch():
    """
    Interrupting program until pressed any key
    """
    try:
        import msvcrt
        return msvcrt.getch()

    except ImportError:
        import sys
        import tty
        import termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch


def strip(data):
    if not data:
        return data

    if isinstance(data, dict):
        items = data.iteritems()
        return dict([[key.strip(' \t\n\r\"\''), val] for key, val in items])

    if isinstance(data, list):
        return map(lambda val: val.strip(' \t\n\r\"\''), data)

    if isinstance(data, str):
        return data.strip(' \t\n\r\"\'')

    raise Exception("Unexpected args type: "
                    "%s. Expect list or dict" % type(data))


class ExitException(Exception):
    pass


def exit(message='exit'):
    out.preloader.exit()
    time.sleep(0.33)
    raise ExitException(message)


def KeyboardInterruptSignalHendler(signal, frame):
    exit()


class Struct:
    def __init__(self, **entries):
        self.__dict__.update(entries)


def decodeArgs(args):
    return map(lambda val: stdinEncode(val), args)


def stdoutEncode(data):
    try:
        return data.decode("utf8").encode(sys.stdout.encoding)
    except:
        return data


def stdinEncode(data):
    try:
        return data.decode(sys.stdin.encoding).encode("utf8")
    except:
        return data

########NEW FILE########
__FILENAME__ = argparserTest
# -*- coding: utf-8 -*-

from geeknote.argparser import *
from cStringIO import StringIO
import sys
import unittest


class testArgparser(unittest.TestCase):

    def setUp(self):
        sys.stdout = StringIO()  # set fake stdout

        # добавляем тестовые данные
        COMMANDS_DICT['testing'] = {
            "help": "Create note",
            "firstArg": "--test_req_arg",
            "arguments": {
                "--test_req_arg": {"altName": "-tra",
                                   "help": "Set note title",
                                   "required": True},
                "--test_arg": {"altName": "-ta",
                               "help": "Add tag to note",
                               "emptyValue": None},
                "--test_arg2": {"altName": "-ta2", "help": "Add tag to note"},
            },
            "flags": {
                "--test_flag": {"altName": "-tf",
                                "help": "Add tag to note",
                                "value": True,
                                "default": False},
            }
        }

    def testEmptyCommand(self):
        parser = argparser([])
        self.assertFalse(parser.parse(), False)

    def testErrorCommands(self):
        parser = argparser(["testing_err", ])
        self.assertFalse(parser.parse(), False)

    def testErrorArg(self):
        parser = argparser(["testing", "test_def_val", "--test_arg_err"])
        self.assertEqual(parser.parse(), False)

    def testErrorNoArg(self):
        parser = argparser(["testing"])
        self.assertEqual(parser.parse(), False)

    def testErrorReq(self):
        parser = argparser(["testing", "--test_arg", "test_val"])
        self.assertEqual(parser.parse(), False)

    def testErrorVal(self):
        parser = argparser(["testing", "--test_req_arg", '--test_arg'])
        self.assertEqual(parser.parse(), False)

    def testErrorFlag(self):
        parser = argparser(["testing", "--test_flag", 'test_val'])
        self.assertEqual(parser.parse(), False)

    def testSuccessCommand1(self):
        parser = argparser(["testing", "--test_req_arg", "test_req_val",
                            "--test_flag", "--test_arg", "test_val"])
        self.assertEqual(parser.parse(), {"test_req_arg": "test_req_val",
                                          "test_flag": True,
                                          "test_arg": "test_val"})

    def testSuccessCommand2(self):
        parser = argparser(["testing", "test_req_val", "--test_flag",
                            "--test_arg", "test_val"])
        self.assertEqual(parser.parse(), {"test_req_arg": "test_req_val",
                                          "test_flag": True,
                                          "test_arg": "test_val"})

    def testSuccessCommand3(self):
        parser = argparser(["testing", "test_def_val"])
        self.assertEqual(parser.parse(), {"test_req_arg": "test_def_val",
                                          "test_flag": False})

    def testSuccessCommand4(self):
        parser = argparser(["testing", "test_def_val", "--test_arg"])
        self.assertEqual(parser.parse(), {"test_req_arg": "test_def_val",
                                          "test_arg": None,
                                          "test_flag": False})

    def testSuccessCommand5(self):
        parser = argparser(["testing", "test_def_val", "--test_arg",
                            "--test_arg2", "test_arg2_val"])
        self.assertEqual(parser.parse(), {"test_req_arg": "test_def_val",
                                          "test_arg": None,
                                          "test_arg2": "test_arg2_val",
                                          "test_flag": False})

    def testSuccessShortAttr(self):
        parser = argparser(["testing", "test_def_val", "-ta",
                            "-ta2", "test_arg2_val"])
        self.assertEqual(parser.parse(), {"test_req_arg": "test_def_val",
                                          "test_arg": None,
                                          "test_arg2": "test_arg2_val",
                                          "test_flag": False})

    def testSuccessShortAttr2(self):
        parser = argparser(["testing", "-tra", "test_def_val", "-tf"])
        self.assertEqual(parser.parse(), {"test_req_arg": "test_def_val",
                                          "test_flag": True})

########NEW FILE########
__FILENAME__ = editorTest
# -*- coding: utf-8 -*-

from geeknote.editor import Editor
import unittest


class testEditor(unittest.TestCase):

    def setUp(self):
        self.MD_TEXT = """# Header 1

## Header 2

Line 1

_Line 2_

**Line 3**

"""
        self.HTML_TEXT = "<h1>Header 1</h1><h2>Header 2</h2><p>Line 1</p><p>"\
                         "<em>Line 2</em></p><p><strong>Line 3</strong></p>"

    def test_TextToENML(self):
        self.assertEqual(Editor.textToENML(self.MD_TEXT),
                         Editor.wrapENML(self.HTML_TEXT))

    def test_ENMLToText(self):
        wrapped = Editor.wrapENML(self.HTML_TEXT)
        self.assertEqual(Editor.ENMLtoText(wrapped), self.MD_TEXT)

    def test_wrapENML_success(self):
        text = "test"
        result = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">
<en-note>test</en-note>'''
        self.assertEqual(Editor.wrapENML(text), result)

    def test_wrapENML_without_argument_fail(self):
        self.assertRaises(TypeError, Editor.wrapENML)

########NEW FILE########
__FILENAME__ = gclientTests
# -*- coding: utf-8 -*-

import unittest

from geeknote.gclient import CustomClient
from geeknote.geeknote import UserStore


class testGclient(unittest.TestCase):

    def test_patched_client(self):
        self.assertEquals(UserStore.Client, CustomClient)

    def test_patched_client_contain_methods(self):
        METHODS = dir(UserStore.Client)
        self.assertIn('getNoteStoreUrl', METHODS)
        self.assertIn('send_getNoteStoreUrl', METHODS)
        self.assertIn('recv_getNoteStoreUrl', METHODS)

########NEW FILE########
__FILENAME__ = geeknoteTest
# -*- coding: utf-8 -*-

import time
import unittest
from geeknote.geeknote import *
from geeknote import tools
from geeknote.editor import Editor

class GeekNoteOver(GeekNote):
    def __init__(self):
        pass

    def loadNoteContent(self, note):
        note.content = "note content"


class NotesOver(Notes):
    def connectToEvertone(self):
        self.evernote = GeekNoteOver()


class testNotes(unittest.TestCase):

    def setUp(self):
        self.notes = NotesOver()
        self.testNote = tools.Struct(title="note title")

    def test_parceInput1(self):
        testData = self.notes._parceInput("title", "test body", "tag1")
        self.assertTrue(isinstance(testData, dict))
        if not isinstance(testData, dict):
            return

        self.assertEqual(testData['title'], "title")
        self.assertEqual(testData['content'], Editor.textToENML("test body"))
        self.assertEqual(testData["tags"], ["tag1", ])

    def test_parceInput2(self):
        testData = self.notes._parceInput("title", "WRITE", "tag1, tag2",
                                          None, self.testNote)
        self.assertTrue(isinstance(testData, dict))
        if not isinstance(testData, dict):
            return

        self.assertEqual(testData['title'], "title")
        self.assertEqual(
            testData['content'],
            "WRITE"
        )
        self.assertEqual(testData["tags"], ["tag1", "tag2"])

    def test_editWithEditorInThread(self):
        testData = self.notes._parceInput("title", "WRITE", "tag1, tag2",
                                          None, self.testNote)
        print ('')
        print ('')
        print (testData)
        print ('')
        print ('')

        self.notes._editWithEditorInThread(testData)
        
    def test_createSearchRequest1(self):
        testRequest = self.notes._createSearchRequest(
            search="test text",
            tags="tag1",
            notebooks="test notebook",
            date="01.01.2000",
            exact_entry=True,
            content_search=True
        )
        response = 'notebook:"test notebook" tag:"tag1" ' \
                   'created:20000101 -created:20000102 "test text"'
        self.assertEqual(testRequest, response)

    def test_createSearchRequest2(self):
        testRequest = self.notes._createSearchRequest(
            search="test text",
            tags="tag1, tag2",
            notebooks="notebook1, notebook2",
            date="31.12.1999-31.12.2000",
            exact_entry=False,
            content_search=False
        )
        response = 'notebook:"notebook1" notebook:"notebook2" tag:"tag1"' \
                   ' tag:"tag2" created:19991231 -created:20010101 ' \
                   'intitle:test text'
        self.assertEqual(testRequest, response)

    def testError_createSearchRequest1(self):
        testRequest = self.notes._createSearchRequest(search="test text",
                                                      date="12.31.1999")
        self.assertEqual(testRequest, 'exit')

########NEW FILE########
__FILENAME__ = outTest
#!/usr/bin/env python

import sys
import unittest
from cStringIO import StringIO
from geeknote.config import VERSION
from geeknote.out import printDate, printLine, printAbout,\
    separator, failureMessage, successMessage, showUser, showNote, \
    printList, SearchResult
from geeknote import out


class AccountingStub(object):
    uploadLimit = 100
    uploadLimitEnd = 100000


class UserStub(object):
    username = 'testusername'
    name = 'testname'
    email = 'testemail'
    accounting = AccountingStub()


class NoteStub(object):
    title = 'testnote'
    created = 10000
    updated = 100000
    content = '##note content'
    tagNames = ['tag1', 'tag2', 'tag3']
    guid = 12345


class outTestsWithHackedStdout(unittest.TestCase):

    def setUp(self):
        sys.stdout = StringIO()  # set fake stdout

    def test_print_line(self):
        printLine('test')
        sys.stdout.seek(0)
        self.assertEquals(sys.stdout.read(), 'test\n')

    def test_print_line_other_endline_success(self):
        printLine('test', endLine='\n\r')
        sys.stdout.seek(0)
        self.assertEquals(sys.stdout.read(), 'test\n\r')

    def test_print_about_success(self):
        about = '''Version: %s
Geeknote - a command line client for Evernote.
Use geeknote --help to read documentation.
And visit www.geeknote.me to check for updates.\n''' % VERSION
        printAbout()
        sys.stdout.seek(0)
        self.assertEquals(sys.stdout.read(), about)

    def test_separator_with_title_success(self):
        line = '------------------- test ------------------\n'
        separator(symbol='-', title='test')
        sys.stdout.seek(0)
        self.assertEquals(sys.stdout.read(), line)

    def test_separator_without_title_success(self):
        line = '----------------------------------------\n\n'
        separator(symbol='-')
        sys.stdout.seek(0)
        self.assertEquals(sys.stdout.read(), line)

    def test_separator_empty_args_success(self):
        separator()
        sys.stdout.seek(0)
        self.assertEquals(sys.stdout.read(), '\n\n')

    def test_failure_message_success(self):
        failureMessage('fail')
        sys.stdout.seek(0)
        self.assertEquals(sys.stdout.read(), 'fail\n')

    def test_success_message_success(self):
        successMessage('success')
        sys.stdout.seek(0)
        self.assertEquals(sys.stdout.read(), 'success\n')

    def test_show_user_without_fullinfo_success(self):
        showUser(UserStub(), {})
        info = '''################ USER INFO ################
Username         : testusername
Name             : testname
Email            : testemail\n'''
        sys.stdout.seek(0)
        self.assertEquals(sys.stdout.read(), info)

    def test_show_user_with_fullinfo_success(self):
        showUser(UserStub(), True)
        info = '''################ USER INFO ################
Username         : testusername
Name             : testname
Email            : testemail
Upload limit     : 0.00
Upload limit end : 01.01.1970\n'''
        sys.stdout.seek(0)
        self.assertEquals(sys.stdout.read(), info)

    def test_show_note_success(self):
        note = '''################## TITLE ##################
testnote
=================== META ==================
Created: 01.01.1970      Updated:01.01.1970     \n'''\
'''----------------- CONTENT -----------------
Tags: tag1, tag2, tag3
##note content\n\n\n'''
        showNote(NoteStub())
        sys.stdout.seek(0)
        self.assertEquals(sys.stdout.read(), note)

    def test_print_list_without_title_success(self):
        notes_list = '''Total found: 2
  1 : 01.01.1970  testnote
  2 : 01.01.1970  testnote\n'''
        printList([NoteStub() for _ in xrange(2)])
        sys.stdout.seek(0)
        self.assertEquals(sys.stdout.read(), notes_list)

    def test_print_list_with_title_success(self):
        notes_list = '''=================== test ==================
Total found: 2
  1 : 01.01.1970  testnote
  2 : 01.01.1970  testnote\n'''
        printList([NoteStub() for _ in xrange(2)], title='test')
        sys.stdout.seek(0)
        self.assertEquals(sys.stdout.read(), notes_list)

    def test_print_list_with_urls_success(self):
        notes_list = '''=================== test ==================
Total found: 2
  1 : 01.01.1970  testnote >>> https://www.evernote.com/Home.action?#n=12345
  2 : 01.01.1970  testnote >>> https://www.evernote.com/Home.action?#n=12345
'''
        printList([NoteStub() for _ in xrange(2)], title='test', showUrl=True)
        sys.stdout.seek(0)
        self.assertEquals(sys.stdout.read(), notes_list)

    def test_print_list_with_selector_success(self):
        out.rawInput = lambda x: 2
        notes_list = '''=================== test ==================
Total found: 2
  1 : 01.01.1970  testnote
  2 : 01.01.1970  testnote
  0 : -Cancel-\n'''
        out.printList([NoteStub() for _ in xrange(2)], title='test', showSelector=True)
        sys.stdout.seek(0)
        self.assertEquals(sys.stdout.read(), notes_list)

    def test_search_result_success(self):
        result = '''Search request: test
Total found: 2
  1 : 01.01.1970  testnote
  2 : 01.01.1970  testnote\n'''
        SearchResult([NoteStub() for _ in xrange(2)], 'test')
        sys.stdout.seek(0)
        self.assertEquals(sys.stdout.read(), result)

    def test_print_date(self):
        self.assertEquals(printDate(1000000), '01.01.1970')

########NEW FILE########
__FILENAME__ = storageTest
# -*- coding: utf-8 -*-

import unittest
from sqlalchemy.engine import create_engine
from sqlalchemy.orm.session import sessionmaker
from geeknote import storage
import pickle


def hacked_init(self):
    '''Hack for testing'''
    engine = create_engine('sqlite:///:memory:', echo=False)
    storage.Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    self.session = Session()


class storageTest(unittest.TestCase):
    def setUp(self):
        stor = storage.Storage
        stor.__init__ = hacked_init
        self.storage = stor()
        self.otoken = 'testoauthtoken'
        self.userinfo = {'email': 'test@mail.com'}
        self.tags = {u'tag': 1, u'tag2': 2, u'tag3': 'lol'}
        self.notebooks = {u'notebook': u'mylaptop'}
        self.storage.createUser(self.otoken,
                                self.userinfo)

    def test_create_user_without_token_fail(self):
        self.assertFalse(self.storage.createUser(None, self.userinfo))

    def test_create_user_without_info_fail(self):
        self.assertFalse(self.storage.createUser(self.otoken, None))

    def test_remove_user_success(self):
        self.assertTrue(self.storage.removeUser())

    def test_get_user_token_success(self):
        self.assertEquals(self.storage.getUserToken(), self.otoken)

    def test_get_user_info_success(self):
        self.assertEquals(self.storage.getUserInfo(), self.userinfo)

    def test_get_user_props_success(self):
        props = [{u'oAuthToken': 'testoauthtoken'},
                 {u'info': {'email': 'test@mail.com'}}]
        self.assertEquals(self.storage.getUserprops(), props)

    def test_get_user_props_exists_success(self):
        self.assertEquals(self.storage.getUserprop('info'),
                             self.userinfo)

    def test_get_user_prop_not_exists(self):
        self.assertFalse(self.storage.getUserprop('some_prop'))

    def test_set_new_user_prop(self):
        self.assertFalse(self.storage.getUserprop('kkey'))
        self.assertTrue(self.storage.setUserprop('some_key', 'some_value'))
        self.assertEquals(self.storage.getUserprop('some_key'), 'some_value')

    def test_set_exists_user_prop(self):
        newmail = {'email': 'new_email@mail.com'}
        self.assertEquals(self.storage.getUserprop('info'), self.userinfo)
        self.assertTrue(self.storage.setUserprop('info', newmail), newmail)
        self.assertEquals(self.storage.getUserprop('info'), newmail)

    def test_get_empty_settings(self):
        self.assertEquals(self.storage.getSettings(), {})

    def test_set_settings_success(self):
        self.storage.setSettings({'editor': 'vim'})
        self.assertEquals(self.storage.getSettings(),
                             {u'editor': u"S'vim'\np0\n."})

    def test_set_setting_error_type_fail(self):
        self.assertFalse(self.storage.setSettings('editor'))

    def test_set_setting_none_value_fail(self):
        self.assertFalse(self.storage.setSettings({'key': None}))

    def test_update_settings_fail(self):
        self.storage.setSettings({'editor': 'vim'})
        self.assertTrue(self.storage.setSettings({'editor': 'nano'}))
        self.assertEquals(self.storage.getSettings(),
                             {u'editor': u"S'nano'\np0\n."})

    def test_get_setting_exist_success(self):
        self.storage.setSettings({'editor': 'vim'})
        editor = self.storage.getSetting('editor')
        self.assertEquals(pickle.loads(editor), 'vim')

    def test_set_setting_true(self):
        editor = 'nano'
        self.assertTrue(self.storage.setSetting('editor', editor))
        self.assertEquals(self.storage.getSetting('editor'), editor)

    def test_get_setting_not_exist_fail(self):
        self.assertFalse(self.storage.getSetting('editor'))

    def test_set_tags_success(self):
        self.assertTrue(self.storage.setTags(self.tags))

    def test_set_tags_error_type_fail(self):
        self.assertFalse(self.storage.setTags('tag'))

    def test_set_tags_none_value_fail(self):
        self.assertFalse(self.storage.setTags({'tag': None}))

    def test_get_tags_success(self):
        tags = {u'tag': u'1', u'tag2': u'2', u'tag3': u'lol'}
        self.assertTrue(self.storage.setTags(self.tags))
        self.assertEquals(self.storage.getTags(), tags)

    def test_replace_tags_success(self):
        tags = {u'tag': u'1', u'tag2': u'2', u'tag3': u'3'}
        self.assertTrue(self.storage.setTags(self.tags))
        self.tags[u'tag3'] = 3
        self.assertTrue(self.storage.setTags(self.tags))
        self.assertEquals(self.storage.getTags(), tags)

    def test_set_notebooks_success(self):
        self.assertEquals(self.storage.getNotebooks(), {})
        self.storage.setNotebooks(self.notebooks)
        self.assertEquals(self.storage.getNotebooks(), self.notebooks)

    def test_replace_notebooks_success(self):
        newnotebooks = {u'notebook': u'android'}
        self.storage.setNotebooks(self.notebooks)
        self.storage.setNotebooks(newnotebooks)
        self.assertEquals(self.storage.getNotebooks(), newnotebooks)

    def test_get_empty_search_success(self):
        self.assertFalse(self.storage.getSearch())

    def test_get_search_exists_success(self):
        query = 'my query'
        self.assertTrue(self.storage.setSearch(query))
        self.assertEquals(self.storage.getSearch(), query)

    def test_set_notebooks_error_type_fail(self):
        self.assertFalse(self.storage.setNotebooks('book'))

    def test_set_notebooks_none_value_fail(self):
        self.assertFalse(self.storage.setNotebooks({'book': None}))

    def test_set_search_true(self):
        self.assertTrue(self.storage.setSearch('my query'))


class modelsTest(unittest.TestCase):
    def test_rept_userprop(self):
        userprop = storage.Userprop(key='test',
                                    value='value')
        self.assertEquals(userprop.__repr__(),
                         "<Userprop('test','value)>")

    def test_repr_setting(self):
        setting = storage.Setting(key='test',
                                  value='value')
        self.assertEquals(setting.__repr__(),
                         "<Setting('test','value)>")

    def test_repr_notebook(self):
        notebook = storage.Notebook(name='notebook',
                                    guid='testguid')
        self.assertEquals(notebook.__repr__(),
                         "<Notebook('notebook')>")

    def test_repr_tag(self):
        tag = storage.Tag(tag='testtag',
                          guid='testguid')
        self.assertEquals(tag.__repr__(), "<Tag('testtag')>")

    def test_repr_search(self):
        search = storage.Search(search_obj='query')
        self.assertEquals(search.__repr__(),
                         "<Search('%s')>" % search.timestamp)

########NEW FILE########
__FILENAME__ = toolsTest
# -*- coding: utf-8 -*-

import unittest
from geeknote.tools import checkIsInt, strip, decodeArgs,\
    stdinEncode, stdoutEncode, Struct


class testTools(unittest.TestCase):

    def test_check_is_int_success(self):
        self.assertTrue(checkIsInt(1))

    def test_check_is_int_float_success(self):
        self.assertTrue(checkIsInt(1.1))

    def test_check_is_int_false(self):
        self.assertTrue(checkIsInt('1'))

    def test_strip_none_data_success(self):
        self.assertFalse(strip(None))

    def test_strip_dict_data_success(self):
        data = {'key \t\n\r\"\'': 'test'}
        self.assertEquals(strip(data), {'key': 'test'})

    def test_strip_list_data_success(self):
        data = ['key \t\n\r\"\'', 'value \t\n\r\"\'']
        self.assertEquals(strip(data), ['key', 'value'])

    def test_strip_str_data_success(self):
        data = 'text text text \t\n\r\"\''
        self.assertEquals(strip(data), 'text text text')

    def test_strip_int_data_false(self):
        self.assertRaises(Exception, strip, 1)

    def test_struct_success(self):
        struct = Struct(key='value')
        self.assertEquals(struct.__dict__, {'key': 'value'})

    def test_decode_args_success(self):
        result = [1, '2', 'test', '\xc2\xae',
                  '\xd1\x82\xd0\xb5\xd1\x81\xd1\x82']
        self.assertEquals(decodeArgs([1, '2', 'test', '®', 'тест']), result)

    def test_stdinEncode_success(self):
        self.assertEquals(stdinEncode('тест'), 'тест')
        self.assertEquals(stdinEncode('test'), 'test')
        self.assertEquals(stdinEncode('®'), '®')
        self.assertEquals(stdinEncode(1), 1)

    def test_stdoutEncode_success(self):
        self.assertEquals(stdoutEncode('тест'), 'тест')
        self.assertEquals(stdoutEncode('test'), 'test')
        self.assertEquals(stdoutEncode('®'), '®')
        self.assertEquals(stdoutEncode(1), 1)

########NEW FILE########
