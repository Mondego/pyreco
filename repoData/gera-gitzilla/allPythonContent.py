__FILENAME__ = hooks

"""
hooks - git hooks provided by gitzilla.

"""

import re
import sys
from utils import get_changes, init_bugzilla, get_bug_status, notify_and_exit
from gitzilla import sDefaultSeparator, sDefaultFormatSpec, oDefaultBugRegex, sDefaultRefPrefix
from gitzilla import NullLogger
import traceback


def post_receive(sBZUrl, sBZUser=None, sBZPasswd=None, sFormatSpec=None, oBugRegex=None, sSeparator=None, logger=None, bz_init=None, sRefPrefix=None, bIncludeDiffStat=True, aasPushes=None):
  """
  a post-recieve hook handler which extracts bug ids and adds the commit
  info to the comment. If multiple bug ids are found, the comment is added
  to each of those bugs.

  sBZUrl is the base URL for the Bugzilla installation. If sBZUser and
  sBZPasswd are None, then it uses the ~/.bugz_cookie cookiejar.

  oBugRegex specifies the regex used to search for the bug id in the commit
  messages. It MUST provide a named group called 'bug' which contains the bug
  id (all digits only). If oBugRegex is None, a default bug regex is used,
  which is:

      r"bug\s*(?:#|)\s*(?P<bug>\d+)"

  This matches forms such as:
    - bug 123
    - bug #123
    - BUG # 123
    - Bug#123
    - bug123

  The format spec is appended to "--pretty=format:" and passed to
  "git whatchanged". See the git whatchanged manpage for more info on the
  format spec. Newlines are automatically converted to the "--pretty"
  equivalent, which is '%n'.

  If sFormatSpec is None, a default format spec is used.

  The separator is a string that would never occur in a commit message.
  If sSeparator is None, a default separator is used, which should be
  good enough for everyone.

  If a logger is provided, it would be used for all the logging. If logger
  is None, logging will be disabled. The logger must be a Python
  logging.Logger instance.

  The function bz_init(url, username, password) is invoked to instantiate the
  bugz.bugzilla.Bugz instance. If this is None, the default method is used.

  sRefPrefix is the string prefix of the git reference. If a git reference
  does not start with this, its commits will be ignored. 'refs/heads/' by default.

  aasPushes is a list of (sOldRev, sNewRev, sRefName) tuples, for when these
  aren't read from stdin (gerrit integration).
  """
  if sFormatSpec is None:
    sFormatSpec = sDefaultFormatSpec

  if sSeparator is None:
    sSeparator = sDefaultSeparator

  if oBugRegex is None:
    oBugRegex = oDefaultBugRegex

  if logger is None:
    logger = NullLogger

  if bz_init is None:
    bz_init = init_bugzilla

  if sRefPrefix is None:
    sRefPrefix = sDefaultRefPrefix

  oBZ = bz_init(sBZUrl, sBZUser, sBZPasswd)

  def gPushes():
    for sLine in iter(sys.stdin.readline, ""):
      yield sLine.strip().split(" ")

  if not aasPushes:
    aasPushes = gPushes()

  sPrevRev = None
  for asPush in aasPushes:
    (sOldRev, sNewRev, sRefName) = asPush
    if not sRefName.startswith(sRefPrefix):
      logger.debug("ignoring ref: '%s'" % (sRefName,))
      continue

    if sPrevRev is None:
      sPrevRev = sOldRev
    logger.debug("oldrev: '%s', newrev: '%s'" % (sOldRev, sNewRev))
    asChangeLogs = get_changes(sOldRev, sNewRev, sFormatSpec, sSeparator, bIncludeDiffStat, sRefName, sRefPrefix)

    for sMessage in asChangeLogs:
      logger.debug("Considering commit:\n%s" % (sMessage,))
      oMatch = re.search(oBugRegex, sMessage)
      if oMatch is None:
        logger.info("Bug id not found in commit:\n%s" % (sMessage,))
        continue
      for oMatch in re.finditer(oBugRegex, sMessage):
        iBugId = int(oMatch.group("bug"))
        logger.debug("Found bugid %d" % (iBugId,))
        try:
          oBZ.modify(iBugId, comment=sMessage)
        except Exception, e:
          logger.exception("Could not add comment to bug %d" % (iBugId,))



def update(oBugRegex=None, asAllowedStatuses=None, sSeparator=None, sBZUrl=None, sBZUser=None, sBZPasswd=None, logger=None, bz_init=None, sRefPrefix=None, bRequireBugNumber=True):
  """
  an update hook handler which rejects commits without a bug reference.
  This looks at the sys.argv array, so make sure you don't modify it before
  calling this function.

  oBugRegex specifies the regex used to search for the bug id in the commit
  messages. It MUST provide a named group called 'bug' which contains the bug
  id (all digits only). If oBugRegex is None, a default bug regex is used,
  which is:

      r"bug\s*(?:#|)\s*(?P<bug>\d+)"

  This matches forms such as:
    - bug 123
    - bug #123
    - BUG # 123
    - Bug#123
    - bug123

  asAllowedStatuses is an array containing allowed statuses for the found
  bugs. If a bug is not in one of these states, the commit will be rejected.
  If asAllowedStatuses is None, status checking is diabled.

  The separator is a string that would never occur in a commit message.
  If sSeparator is None, a default separator is used, which should be
  good enough for everyone.

  sBZUrl specifies the base URL for the Bugzilla installation.  sBZUser and
  sBZPasswd are the bugzilla credentials.

  If a logger is provided, it would be used for all the logging. If logger
  is None, logging will be disabled. The logger must be a Python
  logging.Logger instance.

  The function bz_init(url, username, password) is invoked to instantiate the
  bugz.bugzilla.Bugz instance. If this is None, the default method is used.

  sRefPrefix is the string prefix of the git reference. If a git reference
  does not start with this, its commits will be ignored. 'refs/heads/' by default.

  bRequireBugNumber, if True, requires that a bug number appears in the
  commit message (otherwise it will be rejected).
  """
  if oBugRegex is None:
    oBugRegex = oDefaultBugRegex

  if sSeparator is None:
    sSeparator = sDefaultSeparator

  if logger is None:
    logger = NullLogger

  if bz_init is None:
    bz_init = init_bugzilla

  if sRefPrefix is None:
    sRefPrefix = sDefaultRefPrefix

  sFormatSpec = sDefaultFormatSpec

  if asAllowedStatuses is not None:
    # sanity checking
    if sBZUrl is None:
      raise ValueError("Bugzilla info required for status checks")

  # create and cache bugzilla instance
  oBZ = bz_init(sBZUrl, sBZUser, sBZPasswd)
  # check auth
  try:
    oBZ.auth()
  except:
    logger.error("Could not login to Bugzilla", exc_info=1)
    notify_and_exit("Could not login to Bugzilla. Check your auth details and settings")

  (sRefName, sOldRev, sNewRev) = sys.argv[1:4]
  if not sRefName.startswith(sRefPrefix):
    logger.debug("ignoring ref: '%s'" % (sRefName,))
    return

  logger.debug("oldrev: '%s', newrev: '%s'" % (sOldRev, sNewRev))

  asChangeLogs = get_changes(sOldRev, sNewRev, sFormatSpec, sSeparator, False, sRefName, sRefPrefix)

  for sMessage in asChangeLogs:
    logger.debug("Checking for bug refs in commit:\n%s" % (sMessage,))
    oMatch = re.search(oBugRegex, sMessage)
    if oMatch is None:
      if bRequireBugNumber:
        logger.error("No bug ref found in commit:\n%s" % (sMessage,))
        notify_and_exit("No bug ref found in commit:\n%s" % (sMessage,))
      else:
        logger.debug("No bug ref found, but none required.")
    else:
      if asAllowedStatuses is not None:
        # check all bug statuses
        for oMatch in re.finditer(oBugRegex, sMessage):
          iBugId = int(oMatch.group("bug"))
          logger.debug("Found bug id %d" % (iBugId,))
          try:
            sStatus = get_bug_status(oBZ, iBugId)
            if sStatus is None:
              notify_and_exit("Bug %d does not exist" % (iBugId,))
          except Exception, e:
            logger.exception("Could not get status for bug %d" % (iBugId,))
            notify_and_exit("Could not get staus for bug %d" % (iBugId,))

          logger.debug("status for bug %d is %s" % (iBugId, sStatus))
          if sStatus not in asAllowedStatuses:
            logger.info("Cannot accept commit for bug %d in state %s" % (iBugId, sStatus))
            notify_and_exit("Bug %d['%s'] is not in %s" % (iBugId, sStatus, asAllowedStatuses))


########NEW FILE########
__FILENAME__ = hookscripts

"""
hookscripts - ready to use hook scripts for gitzilla.

These pick up configuration values from the environment.

"""

import os
import re
import sys
import gitzilla.hooks
import logging
import ConfigParser
import bugz

DEFAULT = 'DEFAULT'

def to_bool(v):
  if isinstance(v, str):
    return v.lower() in ["yes", "true", "t", "1"]
  else:
    return bool(v)

def get_or_default(conf, section, option, default=None):
  if conf.has_option(section, option):
    return conf.get(section, option)
  elif conf.has_option(DEFAULT, option):
    return conf.get(DEFAULT, option)
  return default


def has_option_or_default(conf, section, option):
  return conf.has_option(section, option) or conf.has_option(DEFAULT, option)


def bz_auth_from_config(config, sRepo):
  sBZUser = None
  sBZPasswd = None

  if has_option_or_default(config, sRepo, "bugzilla_user") and has_option_or_default(config, sRepo, "bugzilla_password"):
    sBZUser = get_or_default(config, sRepo, "bugzilla_user")
    sBZPasswd = get_or_default(config, sRepo, "bugzilla_password")

  return (sBZUser, sBZPasswd)



def get_bz_data(siteconfig, userconfig):
  sRepo = os.getcwd()

  bAllowDefaultAuth = False

  sBZUrl = get_or_default(siteconfig, sRepo, "bugzilla_url")
  if not sBZUrl:
    print "missing/incomplete bugzilla conf (no bugzilla_url)"
    sys.exit(1)

  sUserOption = get_or_default(siteconfig, sRepo, "user_config", "allow")
  sUserOption = {"deny": "deny", "force": "force"}.get(sUserOption, "allow")

  (sBZUser, sBZPasswd) = bz_auth_from_config(userconfig, sRepo)

  # ignore auth from site-config if "force"
  if sUserOption == "force":
    bAllowDefaultAuth = False

  # for 'allow', get the auth from user config but allow fallback
  if sUserOption == "allow":
    bAllowDefaultAuth = True

  # ignore auth from user config is "deny"
  if sUserOption == "deny":
    (sBZUser, sBZPasswd) = bz_auth_from_config(siteconfig, sRepo)
    if None in (sBZUser, sBZPasswd):
      raise ValueError("No default Bugzilla auth found. Cannot use user-auth because user_config is set to 'deny'")

  return (sBZUrl, sBZUser, sBZPasswd, bAllowDefaultAuth)



def get_logger(siteconfig):
  sRepo = os.getcwd()
  logger = None
  if has_option_or_default(siteconfig, sRepo, "logfile"):
    logger = logging.getLogger("gitzilla")
    logger.addHandler(logging.FileHandler(get_or_default(siteconfig, sRepo, "logfile")))
    # default to debug, but switch to info if asked.
    sLogLevel = get_or_default(siteconfig, sRepo, "loglevel", "debug")
    logger.setLevel({"info": logging.INFO}.get(sLogLevel, logging.DEBUG))

  return logger


def get_bug_regex(siteconfig):
  sRepo = os.getcwd()
  oBugRegex = None
  if has_option_or_default(siteconfig, sRepo, "bug_regex"):
    oBugRegex = re.compile(get_or_default(siteconfig, sRepo, "bug_regex"),
                           re.MULTILINE | re.DOTALL | re.IGNORECASE)

  return oBugRegex


def make_bz_init(siteconfig, bAllowDefaultAuth):
  # return a bz_init function which does the right thing.

  def bz_init(sBZUrl, sBZUser, sBZPasswd):
    # if username/passwd are none, then modify the Bugz instance so that
    # Bugz.get_input and getpass.getpass get the username and passwd
    # from the siteconfig.
    if sBZUrl is None:
      raise ValueError("No Bugzilla URL specified")

    sSiteUser = sBZUser
    sSitePasswd = sBZPasswd

    sRepo = os.getcwd()

    if None in (sBZUser, sBZPasswd):
      if bAllowDefaultAuth:
        # get data from siteconfig
        (sSiteUser, sSitePasswd) = bz_auth_from_config(siteconfig, sRepo)

    oBZ = bugz.bugzilla.Bugz(sBZUrl, user=sBZUser, password=sBZPasswd)

    def auth_error(*args):
      raise ValueError("no Bugzilla auth found!")

    if sSiteUser is None:
      oBZ.get_input = auth_error
    else:
      oBZ.get_input = lambda prompt: sSiteUser
    import getpass
    if sSitePasswd is None:
      getpass.getpass = auth_error
    else:
      getpass.getpass = lambda: sSitePasswd
    return oBZ

  return bz_init


def post_receive(aasPushes=None):
  """
  The gitzilla-post-receive hook script.

  The configuration is picked up from /etc/gitzillarc and ~/.gitzillarc

  The user specific configuration is allowed to override the bugzilla
  username and password.

  aasPushes is a list of (sOldRev, sNewRev, sRefName) tuples, for when these
  aren't read from stdin (gerrit integration).
  """
  siteconfig = ConfigParser.RawConfigParser()
  siteconfig.readfp(file("/etc/gitzillarc"))
  sRepo = os.getcwd()

  userconfig = ConfigParser.RawConfigParser()
  userconfig.read(os.path.expanduser("~/.gitzillarc"))

  (sBZUrl, sBZUser, sBZPasswd, bAllowDefaultAuth) = get_bz_data(siteconfig, userconfig)

  logger = get_logger(siteconfig)
  oBugRegex = get_bug_regex(siteconfig)
  sRefPrefix = get_or_default(siteconfig, sRepo, "git_ref_prefix")
  sSeparator = get_or_default(siteconfig, sRepo, "separator")
  sFormatSpec = get_or_default(siteconfig, sRepo, "formatspec")
  bIncludeDiffStat = to_bool(get_or_default(siteconfig, sRepo, "include_diffstat", True))

  bz_init = make_bz_init(siteconfig, bAllowDefaultAuth)

  gitzilla.hooks.post_receive(sBZUrl, sBZUser, sBZPasswd, sFormatSpec,
                              oBugRegex, sSeparator, logger, bz_init,
                              sRefPrefix, bIncludeDiffStat, aasPushes)



def update():
  """
  The gitzilla-update hook script.

  The configuration is picked up from /etc/gitzillarc and ~/.gitzillarc

  The user specific configuration is allowed to override the bugzilla
  username and password.
  """
  siteconfig = ConfigParser.RawConfigParser()
  siteconfig.readfp(file("/etc/gitzillarc"))
  sRepo = os.getcwd()

  logger = get_logger(siteconfig)
  oBugRegex = get_bug_regex(siteconfig)
  sRefPrefix = get_or_default(siteconfig, sRepo, "git_ref_prefix")
  sSeparator = get_or_default(siteconfig, sRepo, "separator")

  bRequireBugNumber = to_bool(get_or_default(siteconfig, sRepo, "require_bug_ref", True))
  asAllowedStatuses = None
  if has_option_or_default(siteconfig, sRepo, "allowed_bug_states"):
    asAllowedStatuses = map(lambda x: x.strip(),
                get_or_default(siteconfig, sRepo, "allowed_bug_states").split(","))

  # and the bugzilla info.
  userconfig = ConfigParser.RawConfigParser()
  userconfig.read(os.path.expanduser("~/.gitzillarc"))
  (sBZUrl, sBZUser, sBZPasswd, bAllowDefaultAuth) = get_bz_data(siteconfig, userconfig)

  bz_init = make_bz_init(siteconfig, bAllowDefaultAuth)

  gitzilla.hooks.update(oBugRegex, asAllowedStatuses, sSeparator, sBZUrl,
                        sBZUser, sBZPasswd, logger, bz_init, sRefPrefix,
                        bRequireBugNumber)



########NEW FILE########
__FILENAME__ = utils

"""
utils module for gitzilla

"""

import os
import sys
import subprocess
import bugz.bugzilla


sNoCommitRev = "0000000000000000000000000000000000000000"

def execute(asCommand, bSplitLines=False, bIgnoreErrors=False):
  """
  Utility function to execute a command and return the output.
  """
  p = subprocess.Popen(asCommand,
                       stdin=subprocess.PIPE,
                       stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT,
                       shell=False,
                       close_fds=True,
                       universal_newlines=True,
                       env=None)
  if bSplitLines:
    data = p.stdout.readlines()
  else:
    data = p.stdout.read()
  iRetCode = p.wait()
  if iRetCode and not bIgnoreErrors:
    print >>sys.stderr, 'Failed to execute command: %s\n%s' % (asCommand, data)
    sys.exit(-1)

  return data


def init_bugzilla(sBZUrl, sBZUser, sBZPasswd):
  """
  initializes and returns a bugz.bugzilla.Bugz instance.

  This may be overridden in custom hook scripts in order to expand auth
  support.
  """
  if sBZUrl is None:
    raise ValueError("No Bugzilla URL specified")

  oBZ = bugz.bugzilla.Bugz(sBZUrl, user=sBZUser, password=sBZPasswd)
  return oBZ



def get_changes(sOldRev, sNewRev, sFormatSpec, sSeparator, bIncludeDiffStat, sRefName, sRefPrefix):
  """
  returns an array of chronological changes, between sOldRev and sNewRev,
  according to the format spec sFormatSpec.

  Gets changes which are only on the specified ref, excluding changes
  also present on other refs starting with sRefPrefix.
  """
  if sOldRev == sNoCommitRev:
    sCommitRange = sNewRev
  elif sNewRev == sNoCommitRev:
    sCommitRange = sOldRev
  else:
    sCommitRange = "%s..%s" % (sOldRev, sNewRev)

  sFormatSpec = sFormatSpec.strip("\n").replace("\n", "%n")

  if bIncludeDiffStat:
    sCommand = "whatchanged"
  else:
    sCommand = "log"

  asCommand = ['git', sCommand,
               "--format=format:%s%s" % (sSeparator, sFormatSpec)]

  # exclude all changes which are also found on other refs
  # and hence have already been processed.
  if sRefName is not None:
    asAllRefs = execute(
        ['git', 'for-each-ref', '--format=%(refname)', sRefPrefix],
        bSplitLines=True)
    asAllRefs = map(lambda x: x.strip(), asAllRefs)
    asOtherRefs = filter(lambda x: x != sRefName, asAllRefs)
    asNotOtherRefs = execute(
        ['git', 'rev-parse', '--not'] + asOtherRefs,
        bSplitLines=True)
    asNotOtherRefs = map(lambda x: x.strip(), asNotOtherRefs)
    asCommand += asNotOtherRefs

  asCommand.append(sCommitRange)
  sChangeLog = execute(asCommand)
  asChangeLogs = sChangeLog.split(sSeparator)
  asChangeLogs.reverse()

  return asChangeLogs[:-1]



def post_to_bugzilla(iBugId, sComment, sBZUrl, sBZUser, sBZPasswd):
  """
  posts the comment to the given bug id.
  """
  if sBZUrl is None:
    raise ValueError("No Bugzilla URL specified")

  oBZ = bugz.bugzilla.Bugz(sBZUrl, user=sBZUser, password=sBZPasswd)
  oBZ.modify(iBugId, comment=sComment)



def get_bug_status(oBugz, iBugId):
  """
  given the bugz.bugzilla.Bugz instance and the bug id, returns the bug
  status.
  """
  oBug = oBugz.get(iBugId)
  if oBug is None:
    return None
  return oBug.getroot().find("bug/bug_status").text


def notify_and_exit(sMsg):
  """
  notifies the error and exits.
  """
  print """

======================================================================
Cannot accept commit.

%s

======================================================================

""" % (sMsg,)
  sys.exit(1)


########NEW FILE########
__FILENAME__ = utilscripts

"""
utilscripts - utility scripts for gitzilla.

"""

import os
import sys
import bugz.bugzilla
import getpass

def generate_cookiefile():
  """
  asks the user for Bugzilla credentials and generates a cookiefile.
  """
  if len(sys.argv) < 2:
    print """Usage:
    %s <bugzilla_base_url>
""" % sys.argv[0]
    sys.exit(1)

  sBZUrl = sys.argv[1]
  sLogin = os.getlogin()
  sUsername = raw_input("username [%s]: " % (sLogin,))
  sPassword = getpass.getpass("password: ")

  if sUsername == "":
    sUsername = sLogin

  oBZ = bugz.bugzilla.Bugz(sBZUrl, user=sUsername, password=sPassword)
  oBZ.auth()




########NEW FILE########
