__FILENAME__ = auth
import daemon.daemonfunctions as hrdf

REALM=''

def authenticate(path, arguments, function_reference, request):

    auth = request.authorization
    if not auth:
        # Require authentication on every other call
        return False
        
    username = auth.username
    password = auth.password
    funcname = function_reference.__name__

    authed = hrdf.authenticate(username, password, funcname)

    return authed

########NEW FILE########
__FILENAME__ = config
import os

os.environ['HANDYREP_CONFIG'] = '/srv/handyrep//handyrep/handyrep.conf'
########NEW FILE########
__FILENAME__ = daemonfunctions
from handyrep import HandyRep
import os
import sys
import json
import re

# startup function

def startup_hr():
    # get handyrep config location.  if not set,
    # default is in the local directory, which is almost never right
    # try argv
    global hr
    if len(sys.argv) > 1:
        hrloc = sys.argv[1]
    else:
        # try environment variable next
        hrloc = os.getenv("HANDYREP_CONFIG")

    if not hrloc:
        # need to go to handyrep base directory without relying on CWD
        # since CWD doesn't exist in webserver context
        hrloc = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))),"handyrep.conf")
    hr = HandyRep(hrloc)
    return True

# invokable functions

# helper function to interpret string True values
def is_true(bolval):
    if type(bolval) is bool:
        return bolval
    else:
        if bolval.lower() in ["true", "t", "on", "1", "yes"]:
            return True
        else:
            return False

def is_false(bolval):
    if type(bolval) is bool:
        return bolval == False
    else:
        if bolval.lower() in ["false", "f", "off", "0", "no"]:
            return True
        else:
            return False

def read_log(numlines=20):
    nlines = int(numlines)
    return hr.read_log(nlines)

def set_verbose(verbose="True"):
    vbs = is_true(verbose)
    return hr.set_verbose(vbs)

def get_setting(category="handyrep", setting=None):
    if not setting:
        return { "result" : "FAIL",
            "details" : "setting name is required" }
    else:
        return json.dumps(hr.get_setting([category, setting,]))

def verify_all():
    return hr.verify_all()

def verify_server(servername):
    return hr.verify_server(servername)

def reload_conf(config_file='handyrep.conf'):
    return hr.reload_conf(config_file)

def get_master_name():
    return json.dumps(hr.get_master_name())

def poll(servername=None):
    if not servername:
        return { "result" : "FAIL",
            "details" : "server name required" }
    else:
        return hr.poll(servername)

def poll_all():
    return hr.poll_all()

def poll_master():
    return hr.poll_master()

def get_status(check_type="cached"):
    return hr.get_status(check_type)

def get_server_info(servername=None, verify="False"):
    vfy = is_true(verify)
    return hr.get_server_info(servername, vfy)

def get_servers_by_role(serverrole="replica",verify="False"):
    vfy = is_true(verify)
    return hr.get_servers_by_role(serverrole, vfy)

def get_cluster_status(verify="False"):
    vfy = is_true(verify)
    return hr.get_cluster_status(vfy)

def restart_master(whichmaster=None):
    return hr.restart_master(whichmaster)

def manual_failover(newmaster=None, remaster=None):
    return hr.manual_failover(newmaster, remaster)

def shutdown(servername=None):
    if not servername:
        return { "result" : "ERROR",
            "details" : "server name is required" }
    else:
        return hr.shutdown(servername)

def startup(servername=None):
    if not servername:
        return { "result" : "FAIL",
            "details" : "server name is required" }
    else:
        return hr.startup(servername)

def restart(servername=None):
    if not servername:
        return { "result" : "FAIL",
            "details" : "server name is required" }
    else:
        return hr.restart(servername)

def promote(newmaster):
    if not newmaster:
        return { "result" : "FAIL",
            "details" : "new master name is required" }
    else:
        return hr.promote(newmaster)

def remaster(replicaserver=None, newmaster=None):
    if not replicaserver:
        return { "result" : "FAIL",
            "details" : "replica name is required" }
    else:
        return hr.remaster(replicaserver, newmaster)

# dumb simple string-to-type kwargs converter for add_server and alter_server_def
# only supports strings, integers and booleans.
def map_server_args(sargs):
    nargs = {}
    for arg, val in sargs.iteritems():
        if arg in [ "port", "lag_limit", "failover_priority" ]:
            nargs[arg] = int(val)
        elif re.match(r'\d+$',val):
            nargs[arg] = int(val)
        elif val in ["true","True"]:
            nargs[arg] = True
        elif val in ["False","false"]:
            nargs[arg] = False
        else:
            nargs[arg] = val

    return nargs

def add_server(servername=None, **kwargs):
    if not servername:
        return { "result" : "FAIL",
            "details" : "server name is required" }
    else:
        margs = map_server_args(kwargs)
        return hr.add_server(servername, **margs)

def clone(replicaserver=None,reclone="False",clonefrom=None):
    recl = is_true(reclone)
    if not replicaserver:
        return { "result" : "FAIL",
            "details" : "replica name is required" }
    else:
        return hr.clone(replicaserver, recl, clonefrom)

def disable(servername):
    if not servername:
        return { "result" : "FAIL",
            "details" : "server name is required" }
    else:
        return hr.disable(servername)

def enable(servername):
    if not servername:
        return { "result" : "FAIL",
            "details" : "server name is required" }
    else:
        return hr.enable(servername)

def remove(servername):
    if not servername:
        return { "result" : "FAIL",
            "details" : "server name is required" }
    else:
        return hr.remove(servername)

def add_server(servername, **serverprops):
    if not servername:
        return { "result" : "FAIL",
            "details" : "server name is required" }
    else:
        margs = map_server_args(serverprops)
        return hr.add_server(servername, **margs)

def alter_server_def(servername, **serverprops):
    if not servername:
        return { "result" : "FAIL",
            "details" : "server name is required" }
    else:
        margs = map_server_args(serverprops)
        return hr.alter_server_def(servername, **margs)

def connection_failover(newmaster=None):
    if not newmaster:
        return { "result" : "FAIL",
            "details" : "new master name required" }
    else:
        return hr.connection_failover(newmaster)

def connection_proxy_init():
    return hr.connection_proxy_init()

def start_archiving():
    return hr.start_archiving()

def stop_archiving():
    return hr.stop_archiving()

def cleanup_archive():
    return hr.cleanup_archive()

# periodic

def failover_check(pollno=None):
    return hr.failover_check_cycle(pollno)


# authentication

def authenticate(username, userpass, funcname):
    return hr.authenticate_bool(username, userpass, funcname)

########NEW FILE########
__FILENAME__ = invokable
import daemon.daemonfunctions as hrdf

def read_log(numlines=20):
    return hrdf.read_log(numlines)

def set_verbose(verbose="True"):
    return hrdf.set_verbose(verbose)

def get_setting(category="handyrep", setting=None):
    return hrdf.get_setting(category, setting)

def verify_all():
    return hrdf.verify_all()

def verify_server(servername):
    return hrdf.verify_server(servername)

def reload_conf(config_file='handyrep.conf'):
    return hrdf.reload_conf(config_file)

def get_master_name():
    return hrdf.get_master_name()

def poll(servername=None):
    return hrdf.poll(servername)

def poll_all():
    return hrdf.poll_all()

def poll_master():
    return hrdf.poll_master()

def get_status(check_type="cached"):
    return hrdf.get_status(check_type)

def get_server_info(servername=None, verify="False"):
    return hrdf.get_server_info(servername, verify)

def get_servers_by_role(serverrole="replica",verify="False"):
    return hrdf.get_servers_by_role(serverrole, verify)

def get_cluster_status(verify="False"):
    return hrdf.get_cluster_status(verify)

def restart_master(whichmaster=None):
    return hrdf.restart_master(whichmaster)

def manual_failover(newmaster=None, remaster=None):
    return hrdf.manual_failover(newmaster, remaster)

def shutdown(servername=None):
    return hrdf.shutdown(servername)

def startup(servername=None):
    return hrdf.startup(servername)

def restart(servername=None):
    return hrdf.restart(servername)

def promote(newmaster=None):
    return hrdf.promote(newmaster)

def remaster(replicaserver=None, newmaster=None):
    return hrdf.remaster(replicaserver, newmaster)

def clone(replicaserver=None,reclone="False",clonefrom=None):
    return hrdf.clone(replicaserver, reclone, clonefrom)

def disable(servername):
    return hrdf.disable(servername)

def enable(servername):
    return hrdf.enable(servername)

def remove(servername):
    return hrdf.remove(servername)

def alter_server_def(servername, **kwargs):
    return hrdf.alter_server_def(servername, **kwargs)

def add_server(servername, **kwargs):
    return hrdf.add_server(servername, **kwargs)

def connection_failover(newmaster=None):
    return hrdf.connection_failover(newmaster)

def connection_proxy_init():
    return hrdf.connection_proxy_init()

def start_archiving():
    return hrdf.start_archving()

def stop_archiving():
    return hrdf.stop_archiving()

def cleanup_archive():
    return hrdf.cleanup_archive()

INVOKABLE = {
    "read_log" : read_log,
    "get_setting" : get_setting,
    "set_verbose" : set_verbose,
    "verify_all" : verify_all,
    "verify_server" : verify_server,
    "reload_conf" : reload_conf,
    "get_master_name" : get_master_name,
    "poll" : poll,
    "poll_all" : poll_all,
    "poll_master" : poll_master,
    "get_status" : get_status,
    "get_server_info" : get_server_info,
    "get_servers_by_role" : get_servers_by_role,
    "get_cluster_status" : get_cluster_status,
    "restart_master" : restart_master,
    "manual_failover" : manual_failover,
    "shutdown" : shutdown,
    "startup" : startup,
    "restart" : restart,
    "promote" : promote,
    "remaster" : remaster,
    "add_server" : add_server,
    "clone" : clone,
    "disable" : disable,
    "enable" : enable,
    "remove" : remove,
    "alter_server_def" : alter_server_def,
    "add_server" : add_server,
    "connection_failover" : connection_failover,
    "connection_proxy_init" : connection_proxy_init,
    "start_archiving" : start_archiving,
    "stop_archiving" : stop_archiving,
    "cleanup_archive" : cleanup_archive
}


########NEW FILE########
__FILENAME__ = periodic
import daemon.daemonfunctions as hrdf

def failover_check(poll_cycle):
    if poll_cycle is None:
        pollno = 1
    else:
        pollno = poll_cycle

    #print "failover check no. %d" % pollno

    # need to wrap this in try fail so that the failover
    # check doesn't go away if we hit a python bug
    try:
        pollresult = hrdf.failover_check(pollno)
    except Exception as e:
        pollresult = { "result" : "FAIL",
            "details" : "Failover check encountered error: %s" % repr(e) }

    return pollresult

PERIODIC = {
    'failover_check': failover_check,
}

########NEW FILE########
__FILENAME__ = startup
import daemon.daemonfunctions as hrdf

def startup():
    print "startup was run"
    hrdf.startup_hr()
    return True
########NEW FILE########
__FILENAME__ = handyrep
from fabric.api import execute, sudo, run, env, task, local, settings
from fabric.network import disconnect_all
from fabric.contrib.files import upload_template
from lib.config import ReadConfig
from lib.error import CustomError
from lib.dbfunctions import get_one_val, get_one_row, execute_it
import json
from datetime import datetime, timedelta
import logging
import time
import importlib
from plugins.failplugin import failplugin
from lib.misc_utils import ts_string, string_ts, now_string, succeeded, failed, return_dict, exstr, get_nested_val, notnone, notfalse, lock_fabric, fabric_unlock_all
import psycopg2
import psycopg2.extensions
import os
import sys

class HandyRep(object):

    def __init__(self,config_file='handyrep.conf'):
        # read and validate the config file
        config = ReadConfig(config_file)
        # get the absolute location of -validate.conf
        # in order to support web services execution
        validconf = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config/handyrep-validate.conf')
        self.conf = config.read(validconf)
        self.conf["handyrep"]["config_file"] = config_file

        opts = {
         'datefmt': "%Y-%m-%d %H:%M:%S",
         'format':  "%(asctime)-12s %(message)s",
        }
        if self.conf["handyrep"]["config_file"] == 'stdout':
          opts['stream'] = sys.stdout
        else:
          opts['filename'] = self.conf["handyrep"]["log_file"]
        try:
            logging.basicConfig(**opts)
        except Exception as ex:
            raise CustomError("STARTUP","unable to open designated log file: %s" % exstr(ex))
        # initialize log stack
        initmsg = json.dumps({ "ts" : ts_string(datetime.now()),
            "category" : "STARTUP",
            "message" : "Handyrep Starting Up",
            "iserror" : False,
            "alert" : None})
        self.log_stack = [initmsg,]
        self.servers = {}
        self.tabname = """ "%s"."%s" """ % (self.conf["handyrep"]["handyrep_schema"],self.conf["handyrep"]["handyrep_table"],)
        self.status = { "status": "unknown",
            "status_no" : 0,
            "pid" : os.getpid(),
            "status_message" : "status not checked yet",
            "status_ts" : '1970-01-01 00:00:00' }
        self.sync_config(True)
        # return a handyrep object
        return None

    def log(self, category, message, iserror=False, alert_type=None):
        logmsg = json.dumps({ "ts" : ts_string(datetime.now()),
            "category" : category,
            "message" : message,
            "iserror" : iserror,
            "alert" : alert_type})
        if iserror:
            logging.error(logmsg)
        else:
            if self.conf["handyrep"]["log_verbose"]:
                logging.info(logmsg)
            
        if alert_type:
            self.push_alert(alert_type, category, message)

        self.push_log_stack(logmsg)
        
        return True

    def push_log_stack(self, logmsg):
        # pushes recent log items onto a stack of 100 messages
        # so that the user can get the log in json format.
        # and so that users logging to stdout can look at the log
        if len(self.log_stack) > 100:
            self.log_stack.pop(0)

        self.log_stack.append(logmsg)
        return True

    def return_log(self, success, details, extra = {}):
        if not success:
            self.log("HANDYREP",details, True)
        else:
            self.log("HANDYREP",details)
        return return_dict(success, details, extra)

    def read_log(self, numlines=20):
        # reads the last N lines of the log
        # reads from the stack if less than 100 lines; otherwise reads
        # from disk
        # uses byte position to make it more efficient
        # also, if stdout, we can only pull log from the array
        if numlines <= 100 or self.conf["handyrep"]["log_file"] == 'stdout':
            return list(reversed(self.log_stack))[0:numlines]
        else:
            lbytes = numlines * 100
            with open(self.conf["handyrep"]["log_file"], "r") as logf:
                logf.seek (0, 2)           # Seek @ EOF
                fsize = logf.tell()        # Get Size
                logf.seek (max (fsize-lbytes, 0), 0)
                lines = logf.readlines()       # Read to end

            lines = lines[-numlines:]    # Get last 10 lines
        return list(reversed(lines))

    def get_setting(self, setting_name):
        if type(setting_name) is list:
            # prevent getting passwords this way
            if setting_name[0] == "passwords":
                return None
            else:
                return get_nested_val(self.conf, *setting_name)
        else:
            # if category not supplied, then use "handyrep"
            return get_nested_val(self.conf, "handyrep", "setting_name")

    def set_verbose(self, verbose=True):
        self.conf["handyrep"]["log_verbose"] = verbose
        return verbose

    def push_alert(self, alert_type, category, message):
        if self.conf["handyrep"]["push_alert_method"]:
            alert = self.get_plugin(self.conf["handyrep"]["push_alert_method"])
            return alert.run(alert_type, category, message)
        else:
            return return_dict(True,"push alerts are disabled in config")

    def status_no(self, status):
        statdict = { "unknown" : 0,
                    "healthy" : 1,
                    "lagged" : 2,
                    "warning" : 3,
                    "unavailable" : 4,
                    "down" : 5 }
        return statdict[status]

    def is_server_failure(self, oldstatus, newstatus):
        # tests old against new status to see if a
        # server has failed
        statdict = { "unknown" : [],
                    "healthy" : ["unavailable","down",],
                    "lagged" : ["unavailable","down",],
                    "warning" : ["unavailable","down",],
                    "unavailable" : [],
                    "down" : [] }
        return newstatus in statdict[oldstatus]

    def is_server_recovery(self, oldstatus, newstatus):
        # tests old against new status to see if a server has
        # recovered
        statdict = { "unknown" : [],
                    "healthy" : [],
                    "lagged" : [],
                    "warning" : ["healthy","lagged",],
                    "unavailable" : ["healthy","lagged",],
                    "down" : ["healthy","lagged","warning",] }
        return newstatus in statdict[oldstatus]

    def clusterstatus(self):
        # compute the cluster status based on
        # the status of the individual servers
        # in the cluster
        # returns full status dictionary
        # first see if we have a master and its status
        mastername = self.get_master_name()
        
        if not mastername:
            return { "status" : "down",
                    "status_no" : 5,
                    "status_ts" : now_string(),
                    "status_message" : "no master server configured or found" }
                    
        masterstat = self.servers[mastername]
        if masterstat["status_no"] > 3:
            return { "status" : "down",
                    "status_no" : 5,
                    "status_ts" : now_string(),
                    "status_message" : "master is down or unavailable" }
        elif masterstat["status_no"] > 1:
            return { "status" : "warning",
                    "status_no" : 3,
                    "status_ts" : now_string(),
                    "status_message" : "master has one or more issues" }
        # now loop through the replicas, checking status
        replicacount = 0
        failedcount = 0
        for servname, servinfo in self.servers.iteritems():
            # enabled replicas only
            if servinfo["role"] == "replica" and servinfo["enabled"]:
                replicacount += 1
                if servinfo["status_no"] > 3:
                    failedcount += 1

        if failedcount:
            return { "status" : "warning",
                    "status_no" : 3,
                    "status_ts" : now_string(),
                    "status_message" : "%d replicas are down" % failedcount }
        elif replicacount == 0:
            return { "status" : "warning",
                    "status_no" : 3,
                    "status_ts" : now_string(),
                    "status_message" : "no configured replica for this cluster" }
        else:
            return { "status" : "healthy",
                    "status_no" : 1,
                    "status_ts" : now_string(),
                    "status_message" : "" }
        

    def status_update(self, servername, newstatus, newmessage=None):
        # function for updating server statuses
        # returns nothing, because we're not going to check it
        # check if server status has changed.
        # if not, update timestamp and exit
        servconf = self.servers[servername]
        if servconf["status"] == newstatus:
            servconf["status_ts"] = now_string()
            return
        # if status has changed, log the vector and quantity of change
        newstatno = self.status_no(newstatus)
        self.log(servername, "server status changed from %s to %s" % (servconf["status"],newstatus,))
        if newstatno > servconf["status"]:
            if self.is_server_recovery(servconf["status"],newstatus):
                # if it's a recovery, then let's log it
                self.log("RECOVERY", "server %s has recovered" % servername)
        else:
            if self.is_server_failure(servconf["status"],newstatus):
                self.log("FAILURE", "server %s has failed, details: %s" % (servername, newmessage,), True, "WARNING")

        # then update status for this server
        servconf.update({ "status" : newstatus,
                        "status_no": newstatno,
                        "status_ts" : now_string(),
                        "status_message" : newmessage })
                        
        # compute status for the whole cluster
        clusterstatus = self.status
        newcluster = self.clusterstatus()
        # has cluster status changed?
        # if so, figure out vector and quantity of change
        if clusterstatus["status_no"] < newcluster["status_no"]:
            # we've had a failure, push it
            if newcluster["status"] == "warning":
                self.log("STATUS_WARNING", "replication cluster is not fully operational, see logs for details", True, "WARNING")
            else:
                self.log("CLUSTER_DOWN", "database replication cluster is DOWN", True, "CRITICAL")
        elif clusterstatus["status_no"] > newcluster["status_no"]:
            self.log("RECOVERY", "database replication cluster has recovered to status %s" % newcluster["status"])
            
        self.status = newcluster
        self.write_servers()
        return

    def no_master_status(self):
        # called when we suddenly find that there's no enabled master
        # available
        self.status.update({ "status" : "down",
                    "status_no" : 5,
                    "status_message" : "no configured and enabled master found",
                    "status_ts" : now_string()})
        self.log("CONFIG","No configured and enabled master found", True, "WARNING")
        return

    def cluster_status_update(self, newstatus, newstatus_message=""):
        # called during certain operations
        # such as failover in order to change
        self.log("STATUS", "cluster status changed to %s: %s", newstatus, newstatus_message)
        self.status.update({ "status" : newstatus,
            "status_no" : self.status_no(newstatus),
            "status_message" : newstatus_message,
            "status_ts" : now_string() })
        # don't return anything, we don't check it
        return

    def check_hr_master(self):
        # check plugin method to see
        hrs_method = self.get_plugin(self.conf["handyrep"]["master_check_method"])
        # return result
        hrstatus = hrs_method.run(self.conf["handyrep"]["master_check_parameters"])
        return hrstatus

    def verify_servers(self):
        # check each server definition against
        # the reality
        allgood = True
        for someserver, servdetails in self.servers.iteritems():
            if servdetails["enabled"]:
                if servdetails["role"] == "master":
                    if not self.verify_master(someserver):
                        allgood = False
                else:
                    if not self.verify_replica(someserver):
                        allgood = False
            # return false if serverdefs don't match
            # success otherwise
        return allgood

    def read_serverfile(self):
        try:
            servfile = open(self.conf["handyrep"]["server_file"],'r')
        except:
            return None

        try:
            serverdata = json.load(servfile)
        except:
            return None
        else:
            servfile.close()
            return serverdata

    def failwait(self):
        time.sleep(self.conf["failover"]["fail_retry_interval"])
        return

    def init_handyrep_db(self):
        # initialize the handrep schema
        # per settings
        htable = self.conf["handyrep"]["handyrep_table"]
        hschema = self.conf["handyrep"]["handyrep_schema"]
        mconn = self.master_connection()
        mcur = mconn.cursor()
        has_tab = get_one_val(mcur, """SELECT count(*) FROM
            pg_stat_user_tables
            WHERE relname = %s and schemaname = %s""",[htable, hschema,])
        if not has_tab:
            self.log('DATABASE','No handyrep table found, creating one')
            # need schema test here for 9.2:
            has_schema = get_one_val(mcur, """SELECT count(*) FROM pg_namespace WHERE nspname = %s""",[hschema,])
            if not has_schema:
                execute_it(mcur, """CREATE SCHEMA "%s" """ % hschema, [])

            execute_it(mcur, """CREATE TABLE %s ( updated timestamptz, config JSON, servers JSON, status JSON, last_ip inet, last_sync timestamptz )""" % self.tabname, [])
            execute_it(mcur, "INSERT INTO" + self.tabname + " VALUES ( %s, %s, %s, %s, inet_client_addr(), now() )""",(self.status["status_ts"], json.dumps(self.conf), json.dumps(self.servers),json.dumps(self.status),))

        # done
        mconn.commit()
        mconn.close()
        return True

    def check_pid(self, serverdata):
        # checks the PID kept in the servers.save file
        # on startup or any full config sync
        # if it doesn't match the current PID and the other PID
        # is actually running, exit with error
        oldpid = get_nested_val(serverdata, "status", "pid")
        newpid = os.getpid()
        #print "oldpid: %d, newpid: %d" % (oldpid, newpid,)
        if oldpid:
            if oldpid <> newpid:
                try:
                    os.kill(oldpid, 0)
                except OSError:
                    return newpid
                else:
                    raise CustomError("HANDYREP","Another HandyRep is running on this server with pid %d" % oldpid)
        else:
            return newpid

    def sync_config(self, write_servers = True):
        # read serverdata from file
        # this function does a 3-way sync of data
        # looking for the very latest server configuration
        # between the config file, the servers.save file
        # and the database
        # if the serverfile is more updated, use that
        # if the database is more updated, use that
        # if neither is present, or if the OVERRIDE conf
        # option is present, then use the config file
        # also checks the PID of the HR process stored in
        # servers.save in order to verify that we're not
        # running two HR daemons
        use_conf = "conf"
        self.log('HANDYREP',"Synching configuration")
        if not self.conf["handyrep"]["override_server_file"]:
            serverdata = self.read_serverfile()
            if serverdata:
                self.check_pid(serverdata)
                servfiledate = serverdata["status"]["status_ts"]
            else:
                servfiledate = None
            # open the handyrep table on the master if possible
            try:
                sconn = self.best_connection()
                scur = sconn.cursor()
                dbconf = get_one_row(scur,"""SELECT updated, config, servers, status FROM %s """ % self.tabname)
            except:
                dbconf = None
                
            if dbconf:
                # we have both, check which one is more recent
                if serverdata:
                    if servfiledate > dbconf[0]:
                        use_conf = "file"
                    elif servfiledate < dbconf[0]:
                        use_conf = "db"
                else:
                    use_conf = "db"
            else:
                if servfiledate:
                    use_conf = "file"
        # by now, we should know which one to use:
        if use_conf == "conf":
            self.log("HANDYREP","config file is latest, using")
            # merge server defaults and server config
            for server in self.conf["servers"].keys():
                # set self.servers to the merger of settings
                self.servers[server] = self.merge_server_settings(server)
                
            # populate self.status
            self.status.update(self.clusterstatus())

        elif use_conf == "file":
            self.log("HANDYREP","servers file is latest, using")
            # set self.servers to the file data
            self.servers = serverdata["servers"]
            # set self.status from the file
            self.status = serverdata["status"]
            
        elif use_conf == "db":
            self.log("HANDYREP","database table config is latest, using")
            # set self.servers to servers field
            self.servers = dbconf[2]
            # set self.status to status field
            self.status = dbconf[3]

        # update the pid
        self.status["pid"] = os.getpid()
        # write all servers
        if write_servers:
            self.write_servers()
        # don't bother to return anything in particular
        # we don't check it
        return
 
    def reload_conf(self, config_file=None):
        self.log("HANDYREP","reloading configuration file")

        newconf = notfalse(config_file, self.conf["handyrep"]["config_file"], "handyrep.conf")
            
        validconf = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config/handyrep-validate.conf')
        try:
            config = ReadConfig(newconf)
            self.conf = config.read(validconf)
        except:
            return return_dict(False, 'configuration file could not be loaded, see logs')
        
        return return_dict(True, 'configuration file reloaded')

    def write_servers(self):
    # write server data to all locations
        self.log("CONFIG","writing server config to file and database")
        # write server data to file
        try:
            servfile = open(self.conf["handyrep"]["server_file"],"w")
            servout = { "servers" : self.servers,
                        "status": self.status }
            json.dump(servout, servfile)
        except:
            self.log("FILEERROR","Unable to sync configuration to servers file due to permissions or configuration error", True)
            return False
        finally:
            try:
                servfile.close()
            except:
                pass
        # if possible, update the table via the master:
        if self.get_master_name():
            try:
                sconn = self.master_connection()
                scur = sconn.cursor()
            except Exception as ex:
                self.log("DBCONN","Unable to sync configuration to database due to failed connection to master: %s" % exstr(ex), True)
                sconn = None

            if sconn:
                dbconf = get_one_row(scur,"""SELECT * FROM %s """ % self.tabname)
                if dbconf:
                    try:
                        scur.execute("UPDATE " + self.tabname + """ SET updated = %s,
                        config = %s, servers = %s, status = %s,
                        last_ip = inet_client_addr(), last_sync = now()""",(self.status["status_ts"], json.dumps(self.conf), json.dumps(self.servers),json.dumps(self.status),))
                    except Exception as e:
                            # something else is wrong, abort
                        sconn.close()
                        self.log("DBCONN","Unable to write HandyRep table to database for unknown reasons, please fix: %s" % exstr(e), True)
                        return False
                else:
                    self.init_handyrep_db()
                sconn.commit()
                sconn.close()
                return True
        else:
            self.log("CONFIG","Unable to save config, status to database since there is no configured master", True, "WARNING")
            return False

    def get_master_name(self):
        for servname, servdata in self.servers.iteritems():
            if servdata["role"] == "master" and servdata["enabled"]:
                return servname
        # no master?  return None and let the calling function
        # handle it
        return None

    def poll(self, servername):
        # poll servers, according to role
        servrole = self.servers[servername]["role"]
        if servrole == "master":
            return self.poll_master()
        elif servrole == "replica":
            return self.poll_server(servername)
        elif servrole in ["pgbouncer", "proxy",]:
            return self.poll_proxies(servername)
        else:
            return return_dict(False, "no polling defined server role %s" % servrole)

    def poll_master(self):
        # check master using poll method
        self.log("HANDYREP","polling master")
        poll = self.get_plugin(self.conf["failover"]["poll_method"])
        master =self.get_master_name()
        if master:
            check = poll.run(master)
            if failed(check):
                self.status_update(master, "down", "master does not respond to polling")
            else:
                # if master was down, recover it
                # but don't eliminate warnings
                if self.servers[master]["status_no"] in [0,4,5,] :
                    self.status_update(master, "healthy", "master responding to polling")
                else:
                    # update timestamp but don't change message/status
                    self.status_update(master, self.servers[master]["status"])
            return check
        else:
            self.no_master_status()
            return return_dict( False, "No configured master found, poll failed" )

    def poll_server(self, replicaserver):
        # check replica using poll method
        self.log("HANDYREP","polling server %s" % replicaserver)
        if not replicaserver in self.servers:
            return return_dict( False, "Requested server not configured" )
        poll = self.get_plugin(self.conf["failover"]["poll_method"])
        check = poll.run(replicaserver)
        if succeeded(check):
            # if responding, improve the status if it's 
            if self.servers[replicaserver]["status"] in ["unknown","down","unavailable"]:
                self.status_update(replicaserver, "healthy", "server responding to polling")
            else:
                # update timestamp but don't change message/status
                self.status_update(replicaserver, self.servers[replicaserver]["status"])
        else:
            self.status_update(replicaserver, "unavailable", "server not responding to polling")
        return check

    def poll_all(self):
        # polls all servers.  fails if the master is
        # unavailable, doesn't really care about replicas
        # also returns whether or not it's OK
        # to fail over, as verify_all does
        self.log("POLL", "Polling all servers: start")
        master_count = 0
        rep_count = 0
        ret = return_dict(False, "no servers to poll", {"failover_ok" : False })
        ret["servers"] = {}
        for servname, servdeets in self.servers.iteritems():
            if servdeets["enabled"]:
                if servdeets["role"] == "master":
                    master_count += 1
                    pollrep = self.poll_master()
                    ret["servers"].update(pollrep)
                    if succeeded(pollrep):
                        ret.update(return_dict(True, "master is working"))
                    ret["servers"][servname] = pollrep
                elif servdeets["role"] == "replica":
                    pollrep = self.poll_server(servname)
                    if succeeded(pollrep):
                        rep_count += 1
                        ret["failover_ok"] = True
                    ret["servers"][servname] = pollrep
                # other types of servers are ignored

        # check master count
        if master_count == 0:
            self.no_master_status()
            ret.update(return_dict(False, "No configured master found", {"failover_ok": False}))
        elif master_count > 1:
            # we don't allow more than one master
            self.cluster_status_update("down", "Multiple master servers found")
            ret.update(return_dict(False, "Multiple masters found", {"failover_ok" : False}))

        # do we have any good replicas?
        if rep_count == 0:
            ret.update({"details":ret["details"] + " and no working replica found","failover_ok":False})

        # finally, poll proxies.  we ignore this for the overall
        # result of the poll, it's just so we update statuses
        self.poll_proxies()
        
        self.write_servers()
        self.log("POLL", "Polling all servers: end")
        return ret

    def poll_proxies(self, proxyserver=None):
        # polls all the connection proxies
        if self.conf["failover"]["poll_connection_proxy"] and self.conf["failover"]["connection_failover_method"]:
            polprox = self.get_plugin(self.conf["failover"]["connection_failover_method"])
            polres = polprox.poll(proxyserver)
            return polres
        else:
            return return_dict(True, "no proxies to poll")
            

    def verify_master(self):
        # check that you can ssh
        self.log("VERIFY","Verifying master")
        issues = {}
        master = self.get_master_name()
        if not master:
            self.no_master_status()
            return return_dict(False, "No master configured")
        if not self.test_ssh(master):
            self.status_update(master, "warning","cannot SSH to master")
            issues["ssh"] = "cannot SSH to master"
        # connect to master
        try:
            mconn = self.master_connection()
        except Exception as ex:
            self.status_update(master, "warning","cannot psql to master")
            issues["psql"] = "cannot psql to master: %s" % exstr(ex)

        #if both psql and ssh down, we're down:
        if "ssh" in issues and "psql" in issues:
            self.status_update(master, "unavailable", "psql and ssh both failing")
            return return_dict(False, "master not responding", issues)
        # if we have ssh but not psql, see if we can check if pg is running
        elif "ssh" not in issues and "psql" in issues:
            # try polling first, maybe master is just full up on connections
            if succeeded(self.poll_master()):
                self.status_update(master, "warning", "master running but we cannot connect")
                return return_dict(True, "master running but we cannot connect", issues)
            else:
                # ok, let's ssh in and see if we can check the status
                checkpg = self.pg_service_status(master)
                if succeeded(checkpg):
                    # postgres is up, just misconfigured
                    self.status_update(master, "warning", "master running but we cannot connect")
                    return return_dict(True, "master running but we cannot connect", issues)
                else:
                    self.status_update(master, "down", "master is down")
                    return return_dict(False, "master is down", issues)
        # if we have psql, check writability
        else:
            mcur = mconn.cursor()
            # check that you can do a simple write
            try:
                self.conf["handyrep"]["handyrep_schema"]
                mcur.execute("""CREATE TEMPORARY TABLE handyrep_temptest ( testval text );""");
            except Exception as ex:
                mconn.close()
                self.status_update(master, "down","master running but cannot write to disk")
                return return_dict(False, "master is running by writes are frozen: %s" % exstr(ex))
            # return success,
            mconn.close()
            if issues:
                self.status_update(master, "warning", "passed verification check but no SSH access")
            else:
                self.status_update(master, "healthy", "passed verification check")
                
            return return_dict(True, "master OK")

    def verify_replica(self, replicaserver):
        # replica verification for when the whole cluster
        # is running.  not for when in a failover state;
        # then you should use check_replica instead
        self.log("VERIFY","Verifying replica %s" % replicaserver)
        issues = {}
        if replicaserver not in self.servers:
            return return_dict(False, "Server %s not found in configuration" % replicaserver)
        
        if not self.test_ssh(replicaserver):
            self.status_update(replicaserver, "warning","cannot SSH to server")
            issues["ssh"] = "cannot SSH to server"
        
        try:
            rconn = self.connection(replicaserver)
        except Exception as ex:
            self.status_update(replicaserver, "warning", "cannot psql to server")
            issues["psql"] = "cannot psql to server: %s" % exstr(ex)

        # if we had any issues connecting ...
        if "ssh" in issues and "psql" in issues:
            self.status_update(replicaserver, "unavailable", "psql and ssh both failing")
            return return_dict(False, "server not responding", issues)
        # if we have ssh but not psql, see if we can check if pg is running
        elif "ssh" not in issues and "psql" in issues:
            # try polling first, maybe master is just full up on connections
            if succeeded(self.poll_server(replicaserver)):
                self.status_update(replicaserver, "warning", "server running but we cannot connect")
                return return_dict(True, "server running but we cannot connect", issues)
            else:
                # ok, let's ssh in and see if we can psql
                checkpg = self.pg_service_status(replicaserver)
                if succeeded(checkpg):
                    # postgres is up, just misconfigured
                    self.status_update(replicaserver, "warning", "server running but we cannot connect")
                    return return_dict(True, "server running but we cannot connect", issues)
                else:
                    self.status_update(replicaserver, "down", "server is down")
                    return return_dict(False, "server is down", issues)
                
        # if we have psql, check replication status
        else:
        # check that it's in replication
            rcur = rconn.cursor()
            isrep = self.is_replica(rcur)
            rconn.close()
            if not isrep:
                self.status_update(replicaserver, "warning", "replica is running but is not in replication")
                return return_dict(False, "replica is not in replication")
        # poll the replica status table
        # which lets us know status and lag
        repstatus = self.get_plugin(self.conf["failover"]["replication_status_method"])
        repinfo = repstatus.run(replicaserver)
        # if the above fails, we can't connect to the master
        if failed(repinfo):
            # check that the master is already known to be down
            master = self.get_master_name()
            if master:
                if self.servers[master]["status_no"] in [4, 5,]:
                    # ok, we knew the master was down already,  don't change the status
                    # of the replica, just the status message
                        self.status_update(replicaserver, self.servers[replicaserver]["status"], "master down, keeping old replication status")
                else:
                    # something else is wrong, set replica to warning
                    self.status_update(replicaserver, "warning", "cannot check replication status")
            else:
                # no master? oh-oh
                # well, we certainly don't want to fail over ...
                self.status_update(replicaserver, "warning", "cannot check replication status because there is no configured master")
                
            return return_dict(True, "cannot check replication status")

        # check that we're in replication
        if not repinfo["replicating"]:
            self.status_update(replicaserver, "unavailable", "replica is not in replication")
            return return_dict(False, "replica is not in replication")
        # check replica lag
        if repinfo["lag"] > self.servers[replicaserver]["lag_limit"]:
            self.status_update(replicaserver, "lagged", "lagging %d %s" % repinfo["lag"], repinfo["lag_unit"])
            return return_dict(True, "replica is lagged but running")
        else:
        # otherwise, return success
            self.status_update(replicaserver, "healthy", "replica is all good")
            return return_dict(True, "replica OK")

    def verify_server(self, servername):
        if not self.servers[servername]["enabled"]:
            # disabled servers always return success
            # after all, they're supposed to be disabled
            return return_dict(True, "server disabled")

        servrole = self.servers[servername]["role"]
        if servrole == "master":
            return self.verify_master()
        elif servrole == "replica":
            return self.verify_replica(servername)
        elif servrole in ["pgbouncer", "proxy",]:
            return self.poll_proxies(servername)
        else:
            return return_dict(False, "no polling defined server role %s" % servrole)

    def verify_all(self):
        # verify all servers, preparatory to listing
        # information
        # returns success unless the master is down
        # also returns failover_ok, which tells us
        # if there's an OK failover situation
        self.log("VERIFY", "Verifying all servers: start")
        vertest = return_dict(False, "no master found")
        vertest["servers"] = {}
        master_count = 0
        rep_count = 0

        #we need to verify the master first, so that
        #we don't mistakenly decide that the replicas
        #are disabled
        mcheck = self.verify_master()
        mserver = self.get_master_name()
        if succeeded(mcheck):
            vertest.update({ "result" : "SUCCESS",
                "details" : "master check passed",
                "failover_ok" : True })
            vertest["servers"][mserver] = mcheck
        else:
            vertest.update({ "result" : "FAIL",
                "details" : "master check failed",
                "failover_ok" : True })
            vertest["servers"][mserver] = mcheck
        
        for server, servdetail in self.servers.iteritems():
            if servdetail["enabled"]:
                if servdetail["role"] == "master":
                    master_count += 1
                elif servdetail["role"] == "replica":
                    vertest["servers"][server] = self.verify_replica(server)
                    if succeeded(vertest["servers"][server]):
                        rep_count += 1

        # check masters
        if master_count == 0:
            self.no_master_status()
            vertest.update(return_dict(False, "No configured master found", {"failover_ok": False}))
        elif master_count > 1:
            # we don't allow more than one master
            self.cluster_status_update("down", "Multiple master servers found")
            vertest.update(return_dict(False, "Multiple masters found", {"failover_ok" : False}))

                # do we have any good replicas?
        if rep_count == 0:
            vertest.update({"details" : vertest["details"] + " and no working replica found","failover_ok":False})

        # poll proxies.  we ignore this for the overall
        # result of the poll, it's just so we update statuses
        self.poll_proxies()

        # do some archive housekeeping if we're archiving
        if self.conf["archive"]["archiving"]:
            # invoke the poll method of the archive script, just
            # in case anything is required
            self.poll_archiving()
            # do archive deletion cleanup, if required
            self.cleanup_archive()

        self.write_servers()
        self.log("VERIFY", "Verifying all servers: end")
        return vertest

    def check_replica(self, replicaserver):
        # replica check prior to failover
        # checks the replicas and sees if they're lagged
        # without connecting to the master
        # this is mostly like verify_replica, except
        # that failure criteria are different
        # if we can't psql, ssh, and confirm that it's
        # in replication, fail.
        # also return lag status
        self.log("FAILOVER","checking replica %s" % replicaserver)
        # test control access
        checkpg = self.pg_service_status(replicaserver)
        if failed(checkpg):
            # update status if server not already down
            if self.servers[replicaserver]["status_no"] < 4:
                self.status_update(replicaserver, "warning", "no control connection to server")
            return return_dict(False, "no control connection to server")
        
        # test psql access
        try:
            rconn = self.connection(replicaserver)
        except Exception as e:
            # update status if not already down
            if self.servers[replicaserver]["status_no"] < 4:
                self.status_update(replicaserver, "warning", "cannot psql to server")
            return return_dict(False, "cannot psql to server")

        # check that it's in replication
        rcur = rconn.cursor()
        isrep = self.is_replica(rcur)
        rconn.close()
        if not isrep:
            self.status_update(replicaserver, "warning", "server is not in replication")
            return return_dict(False, "server not in replication")
        # looks like we're good
        # we're not going to check lag status, because
        # that's presumed to be part of the replica selection
        return return_dict(True, "replica OK")

    def is_master(self, servername):
        if self.servers[servername]["role"] == 'master' and self.servers[servername]["enabled"]:
            return True
        else:
            return False

    def is_available(self, servername):
        return ( self.servers[servername]["enabled"] and self.servers[servername]["status_no"] < 4 )
            

    def failover_check(self, verify=False):
        # core function of handyrep
        # periodic check of the master
        # to see if we need to initiate failover
        # if auto-failover
        # check if we're the hr master
        self.log("CHECK", "Failover check: start")
        hrmaster = self.check_hr_master()
        if succeeded(hrmaster):
            if not hrmaster["is_master"]:
            # we're not the master, return success
            # and don't do anything
                self.log("CHECK", "server is not HR master")
                return return_dict(True, "this server is not the Handyrep master, skipping")
        else:
            # we errored abort
            self.log("CHECK", "server is not HR master")
            return return_dict(False, "hr master check errored, cannot proceed")
            
        # if not verify, try polling the master first
        # otherwise go straight to verify
        if not verify:
            vercheck = self.poll_all()
            # if the master poll failed, verify the master
            if failed(vercheck):
                mcheck = self.verify_master()
                if succeeded(mcheck):
                    vercheck.update(return_dict(True, "master poll failed, but master is running"))
        else:
            vercheck = self.verify_all()

        if failed(vercheck):
            # maybe restart it?  depends on config
            if self.conf["failover"]["restart_master"]:
                if succeeded(self.restart_master()):
                    self.write_servers()
                    self.log("CHECK", "Master was down; restarted", True)
                    self.log("CHECK", "Failover check: end")
                    return return_dict(True, "master restarted")
            
            # otherwise, check if autofailover is configured
            # and if it's OK to failover
            if self.conf["failover"]["auto_failover"] and vercheck["failover_ok"]:
                failit = self.auto_failover()
                if succeeded(failit):
                    return self.failover_check_return(return_dict(True, "failed over to new master"))
                else:
                    return self.failover_check_return(return_dict(False, "master down, failover failed"))
            elif not self.conf["failover"]["auto_failover"]:
                return self.failover_check_return(return_dict(False, "master down, auto_failover not enabled"))
            else:
                return self.failover_check_return(return_dict(False, "master down or split-brain, auto_failover is unsafe"))
        else:
            return self.failover_check_return(vercheck)

    def failover_check_return(self, vercheck):
        self.write_servers()
        if failed(vercheck):
            self.log("CHECK", vercheck["details"], True)
        else:
            self.log("CHECK", vercheck["details"])

        self.log("CHECK", "Failover check: end")
        return vercheck

    def failover_check_cycle(self, poll_num):
        # same as failover check, only desinged to work with
        # hdaemons periodic in order to return the cycle information
        # periodic expects
        # check the poll cycle number
        if poll_num == 1:
            verifyit = True
        else:
            verifyit = False
        # do a failover check:
        fcheck = self.failover_check(verifyit)
        if succeeded(fcheck):
            # on success, increment the poll cycle
            poll_next = poll_num + 1
            if poll_next >= self.conf["failover"]["verify_frequency"]:
                poll_next = 1
        else:
            # on fail, do a full verify next time
            poll_next = 1
        # sleep for poll interval seconds
        return self.conf["failover"]["poll_interval"], poll_next

    def pg_service_status(self, servername):
        # check the service status on the master
        restart_cmd = self.get_plugin(self.servers[servername]["restart_method"])
        return restart_cmd.run(servername, "status")

    def restart_master(self, whichmaster=None):
        # attempt to restart the master on the
        # master server
        self.log("MASTER","Attempting to restart master")
        if whichmaster:
            master = whichmaster
        else:
            master = self.get_master_name()

        restart_cmd = self.get_plugin(self.servers[master]["restart_method"])
        restart_result = restart_cmd.run(master, "restart")
        if succeeded(restart_result):
            # wait recovery_wait for it to come up
            tries = (self.conf["failover"]["recovery_retries"])
            for mpoll in range(1,tries):
                if self.poll_server(master):
                    self.status_update(master, "healthy", "restarted successfully")
                    self.servers[master]["enabled"] = True
                    return self.return_log(True, "restarted master successfully")
                else:
                    time.sleep(self.conf["failover"]["fail_retry_interval"])
        # no success yet?  then we're down
        self.status_update(master, "down", "unable to restart master")
        return self.return_log(False, "unable to restart master")

    def auto_failover(self):
        oldmaster = self.get_master_name()
        oldstatus = self.status["status"]
        self.cluster_status_update("warning","failing over")
        # poll replicas for new master
        # according to selection_method
        replicas = self.select_new_master()
        if not replicas:
            # no valid masters found, abort
            self.cluster_status_update(oldstatus,"No viable replicas found, aborting failover")
            self.log("FAILOVER","Unable to fail over, no viable replicas", True, "CRITICAL")
            return return_dict(False, "Unable to fail over, no viable replicas")
            
        # find out if we're remastering
        remaster = self.conf["failover"]["remaster"]
        # attempt STONITH
        if failed(self.shutdown_old_master(oldmaster)):
            # if failed, try to rewrite connections instead:
                if self.conf["failover"]["connection_failover"]:
                    if succeeded(self.connection_failover(replicas[0])):
                        self.status_update(oldmaster, "unavailable", "old master did not shut down, changed connection config")
                    # and we can continue
                    else:
                    # we can't shut down the old master, reset and abort
                        self.connection_failover(oldmaster)
                        self.log("FAILOVER", "Could not shut down old master, aborting failover", True, "CRITICAL")
                        self.cluster_status_update(oldstatus, "Failover aborted: Unable to shut down old master")
                        return return_dict(False, "Failover aborted, shutdown failed")
                else:
                    self.log("FAILOVER", "Could not shut down old master, aborting failover", True, "CRITICAL")
                    self.cluster_status_update(oldstatus, "Failover aborted: Unable to shut down old master")
                    return return_dict(False, "Failover aborted, shutdown failed")

        # attempt replica promotion
        for replica in replicas:
            if succeeded(self.check_replica(replica)):
                if succeeded(self.promote(replica)):
                    # if remastering, attempt to remaster
                    if remaster:
                        for servername, servinfo in self.servers.iteritems():
                            if servinfo["role"] == "replica" and servinfo["enabled"]:
                                # don't check result, we do that in
                                # the remaster procedure
                                self.remaster(servername, newmaster)
                    # fail over connections:
                    if succeeded(self.connection_failover(replica)):
                        # update statuses
                        self.status = self.clusterstatus()
                        self.write_servers()
                        # run post-failover scripts
                        # we don't fail back if they fail, though
                        if failed(self.extra_failover_commands(replica)):
                            self.cluster_status_update("warning","postfailover commands failed")
                            return return_dict(True, "Failed over, but postfailover scripts did not succeed")
                            
                        return return_dict(True, "Failover to %s succeeded" % replica)
                    else:
                        # augh.  promotion succeeded but we can't fail over
                        # the connections.  abort
                        self.log("FAILOVER","Promoted new master but unable to fail over connections", True, "CRITICAL")
                        self.cluster_status_update("down","Promoted new master but unable to fail over connections")
                        return return_dict(False, "Promoted new master but unable to fail over connections")

        # if we've gotten to this point, then we've failed at promoting
        # any replicas, time to panic
        if succeeded(self.restart_master(oldmaster)):
            self.status_update(oldmaster, "warning", "attempted failover and did not succeed, please check servers")
        else:
            self.status_update(oldmaster, "down","Unable to promote any replicas")
            
        self.log("FAILOVER","Unable to promote any replicas",True, "CRITICAL")
        return return_dict(False, "Unable to promote any replicas")

    def manual_failover(self, newmaster=None, remaster=None):
        # attempt failover to a replica when requested
        # by user.  this is a bit different from auto-failover
        # because it's assumed that we have a known-good state
        # to revert to
        # get master name
        oldmaster = self.get_master_name()
        oldstatus = self.servers[oldmaster]["status"]
        self.status_update(oldmaster, "warning", "currently failing over")
        if not newmaster:
            # returns a list of potential new masters
            # this step should check all of them
            replicas = self.select_new_master()
            if not replicas:
                # no valid masters found, abort
                self.log("FAILOVER","No viable new masters found", True, "CRITICAL")
                self.status_update(oldmaster, oldstatus, "No viable replicas found, aborting failover and reverting")
                return return_dict(False, "No viable replicas found, aborting failover and reverting")
        else:
            if self.check_replica(newmaster):
                replicas = [newmaster,]
            else:
                self.log("FAILOVER","New master not operating", True, "CRITICAL")
                self.status_update(oldmaster, oldstatus, "New master not viable, aborting failover and reverting")
                return return_dict(False, "New master not viable, aborting failover and reverting")
        # if remaster not set, get from settings
        if not remaster:
            remaster = self.conf["failover"]["remaster"]
        # attempt STONITH
        if failed(self.shutdown_old_master(oldmaster)):
            # we can't shut down the old master, reset and abort
            if succeeded(self.restart_master()):
                self.log("FAILOVER","Unable to shut down old master, aborting and rolling back", True, "WARNING")
                return return_dict(False, "Unable to shut down old master, aborting and rolling back")
            else:
                self.log("FAILOVER","Unable to shut down or restart master", True, "CRITICAL")
                return return_dict(False, "Unable to shut down or restart old master")
        # attempt replica promotion
        for replica in replicas:
            if succeeded(self.check_replica(replica)):
                if succeeded(self.promote(replica)):
                    # if remastering, attempt to remaster
                    if remaster:
                        for servername, servinfo in self.servers.iteritems():
                            if servinfo["role"] == "replica" and servinfo["enabled"]:
                                # don't check result, we do that in
                                # the remaster procedure
                                self.remaster(servname, newmaster)
                    # fail over connections:
                    if succeeded(self.connection_failover(newmaster)):
                        # run post-failover scripts
                        # we don't fail back if they fail, though
                        if failed(self.extra_failover_commands(newmaster)):
                            self.cluster_status_update("warning","postfailover commands failed")
                            self.log("FAILOVER", "Failed over, but postfailover scripts did not succeed", True)
                            return return_dict(True, "Failed over, but postfailover scripts did not succeed")
                        else:
                            self.log("FAILOVER","Failover to %s completed" % newmaster, True)
                            self.servers[oldmaster]["enabled"] = False
                            self.status = self.clusterstatus()
                            return return_dict(True, "Failover completed")
                    else:
                        # augh.  promotion succeeded but we can't fail over
                        # the connections.  abort
                        self.log("FAILOVER","Promoted new master but unable to fail over connections", True, "CRITICAL")
                        self.cluster_status_update("down","Promoted new master but unable to fail over connections")
                        return return_dict(False, "Failed over master but unable to fail over connections")

        # if we've gotten to this point, then we've failed at promoting
        # any replicas -- reset an abort
        if succeeded(self.restart_master(oldmaster)):
            self.log("FAILOVER", "attempted failover and did not succeed, please check servers", True, "CRITICAL")
            self.status_update(oldmaster, "warning", "attempted failover and did not succeed, please check servers")
        else:
            self.log("FAILOVER", "Unable to promote any replicas, cluster is down", True, "CRITICAL")
            self.status_update(oldmaster, "down","Unable to promote any replicas")
        return return_dict(False, "Unable to promote any replicas")

    def shutdown_old_master(self, oldmaster):
        # test if we can ssh to master and run shutdown
        if self.shutdown(oldmaster):
            # if shutdown works, return True
            self.status_update(oldmaster, "down", "Master is shut down")
            self.servers[oldmaster]["enabled"] = False
            return return_dict(True, "Master is shut down")
        else:
            # we can't connect to the old master
            # by ssh, try PG
            try:
                dbconn = self.connection(oldmaster)
                dbconn.close()
            except Exception as e:
            # connection failed, looks like the
            # master is gone
                self.status_update(oldmaster, "unavailable", "Master cannot be reached for shutdown")
                self.servers[oldmaster]["enabled"] = False
                return self.return_log(True, "master is not responding to connections")
            else:
                # we couldn't shut down the master, even
                # thought we can contact it -- failure
                self.log("SHUTDOWN","Attempted to shut down master server, shutdown failed", True, "CRITICAL")
                self.status_update(oldmaster, "warning", "attempted shutdown, master did not respond")
                return return_dict(False, "Cannot shut down master, postgres still running")

    def shutdown(self, servername):
        # shutdown server
        shutdown = self.get_plugin(self.servers[servername]["restart_method"])
        shut = shutdown.run(servername, "stop")
        if succeeded(shut):
            # update server info
            self.status_update(servername, "down", "server has been shut down")
            return self.return_log(True, "shutdown of %s succeeded" % servername)
        else:
            # poll for shut down
            is_shut = False
            for i in range(1,self.conf["failover"]["fail_retries"]):
                self.failwait()
                if failed(self.poll_server(servername)):
                    is_shut = True
                    break

            if is_shut:
                return self.return_log(True, "shutdown of %s succeeded" % servername)
            else:
                return self.return_log(False, "server %s does not shut down" % servername)

    def startup(self, servername):
        # check if server is enabled
        if not self.servers[servername]["enabled"]:
            return return_dict(False, "server %s is disabled.  Please enable it before starting it")
        # start server
        startup = self.get_plugin(self.servers[servername]["restart_method"])
        started = startup.run(servername, "start")
        # poll to check availability
        if succeeded(started):
            if failed(self.poll(servername)):
                # not available?  wait a bit and try again
                time.sleep(10)
                if succeeded(self.poll(servername)):
                    self.status_update(servername, "healthy", "server started")
                    return self.return_log(True, "server %s started" % servername)
                else:
                    self.status_update(servername, "unavailable", "server restarted, but does not respond")
                    return self.return_log(False, "server %s restarted, but does not respond" % servername)
            else:
                self.status_update(servername, "healthy", "server started")
                return self.return_log(True, "server %s started" % servername)
        else:
            self.status_update(servername, "down", "server does not start")
            return self.return_log(False, "server %s does not start" % servername )

    def restart(self, servername):
        # start server
        # this method is a bit more complex
        if not self.servers[servername]["enabled"]:
            return return_dict(False, "server %s is disabled.  Please enable it before restarting it")
        # if restart fails, we see if the server is running, and try
        # a startup
        startup = self.get_plugin(self.servers[servername]["restart_method"])
        started = startup.run(servername, "restart")
        # poll to check availability
        if failed(started):
            # maybe we failed because PostgreSQL isn't running?
            if succeeded(self.poll(servername)):
                # failed abort
                # update status if server is known-good
                if self.servers[servername]["status_no"] < 3:
                    self.update_status(servername, "warning", "server does not respond to restart commands")
                return self.return_log(False, "server %s does not respond to restart commands" % servername)
            else:
                # if not running, try a straight start command
                started = startup.run(servername, "start")

        if succeeded(started):
            if failed(self.poll_server(servername)):
                # not available?  wait a bit and try again
                time.sleep(10)
                if succeeded(self.poll_server(servername)):
                    self.status_update(servername, "healthy", "server started")
                    return self.return_log(True, "server %s started" % servername)
                else:
                    self.status_update(servername, "unavailable", "server restarted, but does not respond")
                    return self.return_log(False, "server %s restarted, but does not respond" % servername)
            else:
                self.status_update(servername, "healthy", "server started")
                return self.return_log(True, "server %s started" % servername)
        else:
            self.status_update(servername, "down", "server does not start")
            return self.return_log(False, "server %s does not start" % servername )


    def get_replicas_by_status(self, repstatus):
        reps = []
        for rep, repdetail in self.servers.iteritems():
            if repdetail["enabled"] and (repdetail["status"] == repstatus):
                reps.append(rep)
                
        return reps

    def promote(self, newmaster):
        # send promotion command
        promotion_command = self.get_plugin(self.servers[newmaster]["promotion_method"])
        promoted = promotion_command.run(newmaster)
        nmconn = None
        if succeeded(promoted):
            # check that we can still connect with the replica, error if not
            try:
                nmconn = self.connection(newmaster)
                nmcur = nmconn.cursor()
            except:
                nmconn = None
                # promoted, now we can't connect? oh-oh
                self.status_update(newmaster, "unavailable", "server promoted, now can't connect")
                return self.return_log(False, "server %s promoted, now can't connect" % newmaster)

            # poll for out-of-replication
            for i in range(1,self.conf["failover"]["recovery_retries"]):
                repstat = get_one_val(nmcur, "SELECT pg_is_in_recovery()")
                if repstat:
                    time.sleep(self.conf["failover"]["fail_retry_interval"])
                else:
                    nmconn.close()
                    self.servers[newmaster]["role"] = "master"
                    self.servers[newmaster]["enabled"] = True
                    self.status_update(newmaster, "healthy", "promoted to new master")
                    return self.return_log(True, "replica %s promoted to master" % newmaster)
                
        if nmconn:            
            nmconn.close()
        # if we get here, promotion failed, better re-verify the server
        self.verify_replica(newmaster)
        self.log("FAILOVER","Replica promotion of %s failed" % newmaster, True)
        return return_dict(False, "promotion failed")
            

    def get_replica_list(self):
        reps = []
        reps.append(self.get_replicas_by_status("healthy"))
        reps.append(self.get_replicas_by_status("lagged"))
        return reps

    def select_new_master(self):
        # first check all replicas
        selection = self.get_plugin(self.conf["failover"]["selection_method"])
        reps = selection.run()
        return reps

    def remaster(self, replicaserver, newmaster=None):
        # use master from settings if not supplied
        if not newmaster:
            newmaster = self.get_master_name()
        # change replica config
        remastered = self.push_replica_conf(replicaserver, newmaster)
        if succeeded(remastered):
            # restart replica
            remastered = self.restart(replicaserver)
            
        if failed(remastered):
            self.verify_server(replicaserver)
            self.log("REMASTER","remastering of server %s failed" % replicaserver, True)
            return return_dict(False, "remastering failed")
        else:
            self.log("REMASTER", "remastered %s" % replicaserver)
            return return_dict(True, "remastering succeeded")

    def add_server(self, servername, **serverprops):
        # add all of the data for a new server
        # hostname is required
        if "hostname" not in (serverprops):
            raise CustomError("USER","Hostname is required for new servers")
        # role defaults to "replica"
        if "role" not in (serverprops):
            serverprops["role"] = "replica"
        # this server will be added as enabled=False
        serverprops["enabled"] = False
        # so that we can clone it up later
        # add rest of settings
        self.servers[servername] = self.merge_server_settings(servername, serverprops)
        # save everything
        self.write_servers()
        return return_dict(True, "new server saved")

    def clone(self, replicaserver, reclone=False, clonefrom=None):
        # use config master if not supplied
        if clonefrom:
            cloprops = self.servers[clonefrom]
            if cloprops["enabled"] and cloprops["status_no"] < 4:
                clomaster = clonefrom
            else:
                return return_dict(False, "you may not clone from a server which is non-operational")
        else:
            clomaster = self.get_master_name()
        # abort if this is the master
        if replicaserver == self.get_master_name():
            return return_dict(False, "You may not clone over the master")
        # abort if this is already an active replica
        # and the user didn't call the reclone flag
        if reclone:
            if failed(self.shutdown(replicaserver)):
                self.log("CLONE","Unable to shut down replica, aborting reclone.", True)
                # reverify server
                self.verify_server(replicaserver)
                return return_dict(False, "Unable to shut down replica")

        elif self.servers[replicaserver]["enabled"] and self.servers[replicaserver]["status"] in ("healthy","lagged","warning","unknown"):
                return return_dict(False, "Cloning over a running server requires the Reclone flag")
        # clone using clone_method
        self.servers[replicaserver]["role"] = "replica"
        clone = self.get_plugin(self.servers[replicaserver]["clone_method"])
        tryclone = clone.run(replicaserver, clomaster, reclone)
        if failed(tryclone):
            return tryclone
        # write recovery.conf, assuming it's configured
        if failed(self.push_replica_conf(replicaserver)):
            self.log("CLONE","Cloning %s failed" % replicaserver, True)
            return return_dict(False, "cloning failed, could not push replica config")
        # same for archiving script
        if failed(self.push_archive_script(replicaserver)):
            self.log("CLONE","Cloning %s failed" % replicaserver, True)
            return return_dict(False, "cloning failed, could not push archiving config")
        # start replica
        self.servers[replicaserver]["enabled"] = True
        if succeeded(self.startup(replicaserver)):
            self.status_update(replicaserver, "healthy", "cloned successfully")
            self.log("CLONE","Successfully cloned to %s" % replicaserver)
            return return_dict(True, "cloning succeeded")
        else:
            self.servers[replicaserver]["enabled"] = False
            self.log("CLONE","Cloning %s failed" % replicaserver, True)
            return return_dict(False, "cloning failed, could not start replica")

    def disable(self, servername):
        # shutdown replica.  Don't check result, we don't really care
        self.shutdown(servername)
        # disable from servers.save
        self.servers[servername]["enabled"] = False
        self.write_servers()
        return self.return_log(True, "server %s disabled" % servername)

    def enable(self, servername):
        # check for obvious conflicts
        if self.servers[servername]["role"] == "master":
            if self.get_master_name():
                return return_dict(False, "you may not start up a second master.  Disable the other master first")
        # update server data
        self.servers[servername]["enabled"] = True
        # check if we're up and update status
        if self.servers[servername]["role"] in ("master", "replica"):
            self.verify_server(servername)
            self.write_servers()
        else:
            self.write_servers()
        return self.return_log(True, "server %s enabled" % servername)

    def remove(self, servername):
        # clean no-longer-used serve entry from table
        if self.servers[servername]["enabled"]:
            return return_dict(False, "You many not remove a currently enabled server from configuration.")
        else:
            self.servers.pop(servername, None)
            self.write_servers()
            return self.return_log(True, "Server %s removed from configuration" % servername)

    def get_status(self, check_type="cached"):
        # returns status of all server resources
        if check_type == "poll":
            self.poll_all()
        elif check_type == "verify":
            self.verify_all()

        servall = {}
        for servname, servdeets in self.servers.iteritems():
            servin = dict((k,v) for k,v in servdeets.iteritems() if k in ["hostname","status","status_no","status_message","enabled","status_ts", "role"])
            servall[servname] = servin

        return { "cluster" : self.status,
            "servers" : servall }

    def postfailover_scripts(self, newmaster):
        pscripts = self.conf["extra_failover_commands"]

    def get_server_info(self, servername=None, verify=False):
        # returns config of all servers
        # if sync:
        if verify:
            # verify_servers
            if servername:
                self.verify_server(servername)
            else:
                self.verify_all()
        if servername:
            # otherwise return just the one
            serv = { servername : self.servers[servername] }
            return serv
        else:
            # if all, return all servers
            return self.servers

    def get_servers_by_role(self, serverrole, verify=True):
        # roles: master, replica
        # if sync:
        if verify:
            if servername:
                self.verify_server(servername)
            else:
                self.verify_all()
        # return master if master
        if serverrole == "master":
            master =self.get_master_name()
            mastdeets = { 'master': self.servers[master] }
            return mastdeets
        else:
            # if replicas, return all running replicas
            reps = {}
            for rep, repdeets in self.servers.iteritems:
                if repdeets["enabled"] and repdeets["role"] == "replica":
                    reps[rep] = repdeets

            return reps

    def get_cluster_status(self, verify=False):
        if verify:
            self.verify_all()
        return self.status

    def merge_server_settings(self, servername, newdict=None):
        # does 3-way merge of server settings:
        # server_defaults, saved server settings
        # and any new supplied dict
        # make a dictionary copy
        sdict = dict(self.conf["server_defaults"])
        if servername in self.conf["servers"]:
            sdict.update(self.conf["servers"][servername])
        if servername in self.servers:
            sdict.update(self.servers[servername])
        if newdict:
            sdict.update(newdict)
        # finally, add status fields
        # and other defaults
        statusdef = { "status" : "unknown",
                    "status_no" : 0,
                    "status_ts" : ts_string(datetime.now()),
                    "status_message" : "",
                    "role" : "replica",
                    "enabled" : False,
                    "failover_priority" : 999}
        statusdef.update(sdict)
        return statusdef
                    

    def validate_server_settings(self, servername, serverdict=None):
        # check all settings or prospective settings
        # for a server.  in the process, merge changed
        # settings with full set of settings
        # merge old or default settings into new dict
        # returns JSON
        newdict = self.merge_server_settings(servername, serverdict)
        # check that we have all required settings
        issues = {}
        if "hostname" not in newdict.keys():
            return return_dict(False, "hostname not provided")
        # check ssh
        if not self.test_ssh_newhost(newdict["hostname"], newdict["ssh_key"], newdict["ssh_user"]):
            issues.update({ "ssh" : "FAIL" })
        # check postgres connection
        try:
            tconn = self.adhoc_connection(dbhost=newdict["hostname"],dbport=newdict["port"],dbpass=newdict["pgpass"],dbname=self.conf["handyrep"]["handyrep_db"])
        except Exception as e:
            issues.update({ "psql" : "FAIL" })
        else:
            tconn.close()
        # run test_new() methods for each named pluginred: TBD
        # not sure how to do this, since we haven't yet merged
        # the changes into .servers
        if not issues:
            return return_dict(True, "server verified")
        else:
            return return_dict(False, "verification failed", issues)

    def alter_server_def(self, servername, **serverprops):
        # check for changes to server config which aren't allowed
        olddef = self.servers[servername]
        
        if "role" in serverprops:
            # can't change a replica to a master this way, or vice-versa
            # unless the server is already disabled
            newrole = serverprops["role"]
            if serverprops["role"] <> olddef["role"] and olddef["enabled"] and (olddef["role"] in ["replica", "master",] or serverprops["role"] in ["replica", "master",]):
                return return_dict(False, "Changes to server role for enabled servers in replication not allowed.  Use promote, disable and/or clone instead")
        else:
            newrole = olddef["role"]

        if newrole in ("replica", "master"):
            inreplication = True

        if "status" in serverprops or "status_no" in serverprops or "status_ts" in serverprops:
            return return_dict(False, "You may not manually change server status")

        # verify servers
        # validate new settings
        # NOT currently validating settings
        # because of the insolvable catch-22 in doing so
        #valids = self.validate_server_settings(servername, serverprops)
        #if failed(valids):
        #    valids.update(return_dict(False, "the settings you supplied do not validate"))
        #    return valids
        # merge and sync server config
        self.servers[servername] = self.merge_server_settings(servername, serverprops)
        
        # enable servers
        if "enabled" in serverprops and inreplication:
            # are we enabling or disabling the server?
            if serverprops["enabled"] and not olddef["enabled"]:
                self.enable(servername)
            elif not serverprops["enabled"] and olddef["enabled"]:
                self.disable(servername)
        
        self.write_servers()
        # exit with success
        return self.return_log(True, "Server %s definition changed" % servername, {"definition" : self.servers[servername]})

    def push_replica_conf(self, replicaserver, newmaster=None):
        # write new recovery.conf per servers.save
        self.log("ARCHIVE", "Pushing replica configuration for %s" % replicaserver)
        servconf = self.servers[replicaserver]
        rectemp = servconf["recovery_template"]
        archconf = self.conf["archive"]
        recparam = {}
        # get recover-from-archive from archiving plugin
        if archconf["archiving"] and archconf["archive_script_method"]:
            arch = self.get_plugin(archconf["archive_script_method"])
            recparam["archive_recovery_line"] = arch.recoveryline()
        else:
            recparam["archive_recovery_line"] = ''
                
        # build the connection string
        if not newmaster:
            newmaster = self.get_master_name()
        masterconf = self.servers[newmaster]
        
        recparam["replica_connection"] = "host=%s port=%s user=%s application_name=%s" % (masterconf["hostname"], masterconf["port"], self.conf["handyrep"]["replication_user"], replicaserver,)

        if self.conf["passwords"]["replication_pass"]:
            recparam["replica_connection"] = "%s password=%s" % (recparam["replica_connection"],self.conf["passwords"]["replication_pass"])
        
        # set up fabric
        lock_fabric(True)
        env.key_filename = self.servers[replicaserver]["ssh_key"]
        env.user = self.servers[replicaserver]["ssh_user"]
        env.disable_known_hosts = True
        env.host_string = self.servers[replicaserver]["hostname"]
        # push the config
        try:
            upload_template( rectemp, servconf["replica_conf"], use_jinja=True, context=recparam, template_dir=self.conf["handyrep"]["templates_dir"], use_sudo=True)
            sudo( "chown %s %s" % (self.conf["handyrep"]["postgres_superuser"], servconf["replica_conf"] ), quiet=True)
            sudo( "chmod 700 %s" % (servconf["replica_conf"] ), quiet=True)
            
        except Exception as ex:
            self.disconnect_and_unlock()
            self.status_update(replicaserver, "warning", "could not change configuration file")
            return self.return_log(False, "could not push new replication configuration: %s" % exstr(ex))
        
        self.disconnect_and_unlock()

        # restart the replica if it was running
        if self.is_available(replicaserver):
            if failed(self.restart(replicaserver)):
                self.status_update(replicaserver, "warning", "changed config but could not restart server")
                return self.return_log(False, "changed config but could not restart server %s" % replicaserver)

        self.log("CONFIG","Changed configuration for %s" % replicaserver)
        return return_dict(True, "pushed new replication configuration")
        

    def push_archive_script(self, servername):
        # write a wal_archive executable script
        # to the server
        # calls plugin
        self.log("HANDYREP","Pushing new archive configuration to %s" % servername)
        if self.conf["archive"]["archiving"] and self.conf["archive"]["archive_script_method"]:
            arch = self.get_plugin(self.conf["archive"]["archive_script_method"])
            archit = arch.run(servername)
            return archit
        else:
            return return_dict(True, "archiving not configured, so ignoring this")


    def connection_failover(self, newmaster):
        # fail over connections as part of
        # automatic or manual failover
        # returns success if not configured
        confail_name = self.conf["failover"]["connection_failover_method"]
        if confail_name:
            confail = self.get_plugin(confail_name)
            confailed = confail.run(newmaster)
            if succeeded(confailed):
                self.log("FAILOVER","Connections failed over to new master %s" % newmaster)
            else:
                self.log("FAILOVER","Could not fail over new connections to new master %s" % newmaster, True, "WARNING")
            return confailed
        else:
            return return_dict(True, "no connection failover configured")

    def connection_proxy_init(self):
        # initialize connection configuration
        # as part of initial setup
        # requires connection failover to be set up in the first place
        # returns success if not configured in order to
        # avoid errors on automated processses
        confail_name = self.conf["failover"]["connection_failover_method"]
        if confail_name:
            confail = self.get_plugin(confail_name)
            confailed = confail.init()
            if succeeded(confailed):
                self.log("FAILOVER","Initialized connection proxy configuration")
            else:
                self.log("FAILOVER","Could not initialize connection configuration", True)
            return confailed
        else:
            return return_dict(True, "no connection failover configured")

    def extra_failover_commands(self, newmaster):
        # runs extra commands after failover, based on
        # the new server configuration
        # output of these commands is logged, but
        # no action is taken if they fail
        some_failed = False
        for fcmd, fdeets in self.conf["extra_failover_commands"].iteritems():
            failcall = self.get_plugin(fdeets["command"])
            failres = failcall.run(newmaster, *fdeets["parameters"])
            if failed(failres):
                some_failed = True
                self.log("FAILOVER","Post-failover command %s failed with error %s" % (fcmd, failres["details"],),True, "WARNING")

        if some_failed:
            return return_dict(False, "One or more post-failover commands failed")
        else:
            return return_dict(True, "Post-failover commands executed")
        

    def start_archiving(self):
        # pushes a new archive script to the master
        # and initializes archiving
        # but WITHOUT changing postgresql.conf, so
        # you still need to do that
        archconf = self.conf["archive"]
        if archconf["archiving"] and archconf["archive_script_method"]:
            arch = self.get_plugin(archconf["archive_script_method"])
            startit = arch.start()
            self.log("ARCHIVE", "Archiving enabled")
            return startit
        else:
            return return_dict(False, "Cannot start archiving because it is not configured.")

    def stop_archiving(self):
        # pushes a NOARCHIVING touch file to the master
        # does not actually verify that archiving has stopped though
        archconf = self.conf["archive"]
        if archconf["archiving"] and archconf["archive_script_method"]:
            arch = self.get_plugin(archconf["archive_script_method"])
            startit = arch.stop()
            self.log("ARCHIVE", "Archiving disabled")
            return startit
        else:
            return return_dict(False, "Cannot stop archiving because it is not configured.")

    def poll_archiving(self):
        # polls the archiving servers according to the archive method
        # in many cases this returns nothing
        archconf = self.conf["archive"]
        if archconf["archiving"] and archconf["archive_script_method"]:
            arch = self.get_plugin(archconf["archive_script_method"])
            archpoll = arch.poll()
            return archpoll
        else:
            return return_dict(True, "archiving is disabled")

    def cleanup_archive(self):
        # runs the archive delete method, if any
        if self.conf["archive"]["archiving"] and self.conf["archive"]["archive_delete_method"]:
                self.log("ARCHIVE", "Running archive cleanup")
                adel = self.get_plugin(self.conf["archive"]["archive_delete_method"])
                adeldone = adel.run()
                return adeldone
        else:
            return return_dict(True, "archive cleanup is disabled")

    def get_plugin(self, pluginname):
        # call method from the plugins class
        # if this errors, we return a class
        # which will fail whenever it's called
        try:
            getmodule = importlib.import_module("plugins.%s" % pluginname)
            getclass = getattr(getmodule, pluginname)
            getinstance = getclass(self.conf, self.servers)
        except:
            getinstance = failplugin(pluginname)

        return getinstance

    def connection(self, servername, autocommit=False):
        connect_string = "dbname=%s host=%s port=%s user=%s application_name=handyrep " % (self.conf["handyrep"]["handyrep_db"], self.servers[servername]["hostname"], self.servers[servername]["port"], self.conf["handyrep"]["handyrep_user"],)

        if self.conf["passwords"]["handyrep_db_pass"]:
                connect_string += " password=%s " % self.conf["passwords"]["handyrep_db_pass"]

        try:
            conn = psycopg2.connect( connect_string )
        except:
            self.log("DBCONN","ERROR: Unable to connect to Postgres using the connections string %s" % connect_string)
            raise CustomError("DBCONN","ERROR: Unable to connect to Postgres using the connections string %s" % connect_string)

        if autocommit:
            conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

        return conn

    def adhoc_connection(self, **kwargs):

        if "dbname" in kwargs:
            if kwargs["dbname"]:
                connect_string = " dbname=%s " % kwargs["dbhost"]
        else:
            connect_string = " dbname=%s " % self.conf["handyrep"]["handyrep_db"]

        if "dbhost" in kwargs:
            if kwargs["dbhost"]:
                connect_string += " host=%s " % kwargs["dbhost"]

        if "dbuser" in kwargs:
            if kwargs["dbuser"]:
                connect_string += " user=%s " % kwargs["dbuser"]
        else:
                connect_string += " user=%s " % self.conf["handyrep"]["handyrep_user"]

        if "dbpass" in kwargs:
            if kwargs["dbpass"]:
                connect_string += " password=%s " % kwargs["dbpass"]
        else:
            if self.conf["handyrep"]["handyrep_pw"]:
                connect_string += " password=%s " % self.conf["handyrep"]["handyrep_pw"]

        if "dbport" in kwargs:
            if kwargs["dbport"]:
                connect_string += " port=%s " % kwargs["dbport"]

        if "appname" in kwargs:
            if kwargs["appname"]:
                connect_string += " application_name=%s " % kwargs["appname"]
        else:
            connect_string += " application_name=handyrep "

        try:
            conn = psycopg2.connect( connect_string )
        except:
            raise CustomError("DBCONN","ERROR: Unable to connect to Postgres using the connections string %s" % connect_string) 

        if "autocommit" in kwargs:
            if kwargs["autocommit"]:
                conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

        return conn

    def is_replica(self, rcur):
        try:
            reptest = get_one_val(rcur,"SELECT pg_is_in_recovery();")
        except Exception as ex:
            raise CustomError("QUERY","Unable to check replica status", ex)

        return reptest

    def master_connection(self, mautocommit=False):
        # connect to the master.  if unable to
        # or if it's not really the master, fail
        master = self.get_master_name()
        if not master:
            raise CustomError("CONFIG","No master server found in server configuration")
        
        try:
            mconn = self.connection(master, autocommit=mautocommit)
        except:
            raise CustomError("DBCONN","Unable to connect to configured master server.")

        reptest = self.is_replica(mconn.cursor())
        if reptest:
            mconn.close()
            self.log("CONFIG", "Server configured as the master is actually a replica, aborting connection.", True)
            raise CustomError("CONFIG","Server configured as the master is actually a replica, aborting connection.")
        
        return mconn
        

    def best_connection(self, autocommit=False):
        # loop through the available servers, starting with the master
        # until we can connect to one of them
        try:
            bconn = master_connection()
        except:
        # master didn't work?  try again with replicas
            for someserver in self.servers.keys():
                try:
                    bconn = self.connection(someserver, autocommit)
                except:
                    continue
                else:
                    return bconn
        # still nothing?  error out
        raise CustomError('DBCONN',"FATAL: no accessible database servers in current server list.  Update the configuration manually and try again.")

    def test_ssh(self, servername):
        try:
            lock_fabric()
            env.key_filename = self.servers[servername]["ssh_key"]
            env.user = self.servers[servername]["ssh_user"]
            env.disable_known_hosts = True
            env.host_string = self.servers[servername]["hostname"]
            command = self.conf["handyrep"]["test_ssh_command"]
            testit = run(command, quiet=True, warn_only=True)
        except:
            return False

        result = testit.succeeded
        self.disconnect_and_unlock()
        return result

    def test_ssh_newhost(self, hostname, ssh_key, ssh_user ):
        try:
            lock_fabric()
            env.key_filename = ssh_key
            env.user = ssh_user
            env.disable_known_hosts = True
            env.host_string = hostname
            command = self.conf["handyrep"]["test_ssh_command"]
            testit = run(command, warn_only=True, quiet=True)
        except Exception as ex:
            print exstr(ex)
            return False

        result = testit.succeeded
        self.disconnect_and_unlock()
        return result

    def authenticate(self, username, userpass, funcname):
        # simple authentication function which
        # authenticates the user against the passwords
        # set in handyrep.conf
        # should probably be replaced with something more sophisticated
        # you'll notice we ignore the username, for example
        authit = self.get_plugin(self.conf["handyrep"]["authentication_method"])
        authed = authit.run(username, userpass, funcname)
        return authed

    def authenticate_bool(self, username, userpass, funcname):
        # simple boolean response to the above for the web daemon
        return succeeded(self.authenticate(username, userpass, funcname))

    def disconnect_and_unlock(self):
        disconnect_all()
        lock_fabric(False)
        return True

########NEW FILE########
__FILENAME__ = hdaemon
import inspect
from threading import Thread
import time
import json
import sys

from flask import Flask, request, jsonify, Response

import daemon.config as config

from daemon.invokable import INVOKABLE
from daemon.periodic import PERIODIC
from daemon.startup import startup
from daemon.auth import authenticate, REALM

#

# Cute hack:
# Since there's no STDOUT.sync = true in Python,
# Make stdout unbuffered by redirecting stdout to stderr :-)
sys.stdout = sys.stderr
app = Flask(__name__)

#

@app.route("/<func>")
def invoke(func):
    try:
        function_reference = INVOKABLE[func]
    except KeyError:
        return jsonify({ 'Error' : 'Undefined function ' + func }) 
        
    arguments = {}
        
    for key in request.args.keys():
        arg = request.args.getlist(key)
        if len(arg) == 1:
            arguments[key] = arg[0]
        else:
            arguments[key] = arg
    
    
    if inspect.getargspec(function_reference).keywords is None:
        kwargs = inspect.getargspec(function_reference).args

        diff = set(arguments.keys()).difference(set(kwargs))
    
        if diff:
            return jsonify({ 'Error' : 'Undefined argument: ' + ', '.join(diff) })
        
    if not authenticate(func, arguments, function_reference, request):
        return Response("Could not authenticate", 401,
            {'WWW-Authenticate': 'Basic realm="%s"' % REALM})
    
    result = function_reference(**arguments)
    
    if not isinstance(result, basestring):
        result = json.dumps(result)
        
    return Response(result, mimetype='application/json')
    


def run_periodic(func):
    try:
        function_reference = PERIODIC[func]
    except KeyError:
        return  
    
    argument = None
    result = None
    
    while(True):
        result = function_reference(argument)

        if result is None or type(result) is not tuple or len(result) != 2:
            break
        
        sleep_period = int(result[0])
        
        if sleep_period > 0:
            time.sleep(sleep_period)
        
        argument = result[1]

    print func, "exiting with return", result


startup()

for func_name in PERIODIC.keys():
    t = Thread(target=run_periodic, args=(func_name,) )
    t.daemon = True
    t.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0")

########NEW FILE########
__FILENAME__ = config
from configobj import ConfigObj, Section
from error import CustomError
from validate import Validator
from datetime import datetime
import re
import os

class ReadConfig(object):

    def __init__(self, configfile):
        self.configfile = configfile

    def read(self, validationfile=None):
        try:
            if validationfile:
                config = ConfigObj(self.configfile,configspec=validationfile,stringify=True)
            else:
                config = ConfigObj(self.configfile)
        except:
            raise CustomError('CONFIG','Could not read configuration file %s' % self.configfile)

        if validationfile:
            validator = Validator()
            ctest = config.validate(validator)
            if not ctest:
                raise CustomError('CONFIG','Configuration file has bad format or out-of-range values')

        cdict = self.convertdict(config)
        return cdict

    def plainread(self):
        try:
            config = ConfigObj(self.configfile)
        except:
            raise CustomError('CONFIG','Could not read configuration file %s' % self.configfile)
        return config
    
    def validate(self, validationfile):
        try:
            config = ConfigObj(self.configfile, configspec=validationfile, stringify=True)
        except:
            raise CustomError('CONFIG','Could not read configuration file %s' % self.configfile)
        validator = Validator()
        result = config.validate(validator)
        return result

    def convertdict(self, config):
        # takes a configobj configuration object
        # and converts it to a dictionary
        newdict = {}
        for dkey, dval in config.iteritems():
            if type(dval) == dict:
                newdict[dkey] = self.convertdict(dval)
            elif re.search(r'Section', str(type(dval))):
                newdict[dkey] = self.convertdict(dval)
            else:
                newdict[dkey] = dval

        return newdict

    def readtypes(self, cdict):
        # method to read a config dict and
        # change the dates and datetimes into datetime types
        # change on, off into booleans
        newdict = {}
        datere = re.compile(r'\d{4}-\d{1,2}-\d{1,2}',flags=re.U),
        for dkey, dval in cdict.iteritems():
            if type(dval) == str:
                # test for booleans first
                if dval.lower() in ('true','t','on'):
                    newdict[dkey] = True
                elif dval.lower() in ('false','f','off'):
                    newdict[dkey] = False
                elif re.match(datere,dval):
                    try:
                        nval = datetime.strptime(dval,'%Y-%m-%d')
                        newdict[dkey] = nval
                    except:
                        try:
                            nval = datetime.strptime(dval,'%Y-%m-%d %H:%M:%S')
                            newdict[dkey] = nval
                        except:
                            newdict[dkey] = dval
                else:
                    newdict[dkey] = dval
            elif type(dval) == dict:
                newdict[dkey] = self.readtypes(dval)
            elif re.search(r'Section', str(type(dval))):
                newdict[dkey] = self.readtypes(dval)
            else:
                newdict[dkey] = dval

        return newdict

    

########NEW FILE########
__FILENAME__ = dbfunctions
import re
import psycopg2, psycopg2.extensions
from lib.error import CustomError
import logging

# contains an assortment of random functions to make
# handling activity on psycopg2 database connections
# a bit easier

# construct a connection string and open aS postgresql
# connection using kwargs format instead of a DSN

def log_activity( message, always_log=False ):
    if always_log:
        logging.info(message)
    return

def get_pg_conn( dbname, **kwargs ):

    if not dbname:
        logging.error("No database name supplied")
        raise CustomError("DBCONN","ERROR: a target database is required.")

    connect_string = "dbname=%s " % dbname

    if "dbhost" in kwargs:
        if kwargs["dbhost"]:
            connect_string += " host=%s " % kwargs["dbhost"]

    if "dbuser" in kwargs:
        if kwargs["dbuser"]:
            connect_string += " user=%s " % kwargs["dbuser"]

    if "dbpass" in kwargs:
        if kwargs["dbpass"]:
            connect_string += " password=%s " % kwargs["dbpass"]

    if "dbport" in kwargs:
        if kwargs["dbport"]:
            connect_string += " port=%s " % kwargs["dbport"]

    if "appname" in kwargs:
        if kwargs["appname"]:
            connect_string += " application_name=%s " % kwargs["appname"]

    try:
        conn = psycopg2.connect( connect_string )
    except:
        raise CustomError("DBCONN","ERROR: Unable to connect to Postgres using the connections string %s" % connect_string)

    if "autocommit" in kwargs:
        if kwargs["autocommit"]:
            conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

    return conn

# test if a value is a number
def is_number(val):
    try:
        nval = float(val)
    except ValueError:
        return False

    return True

# do proper quote escaping for values to be inserted
# into postgres as part of an INSERT statement
def escape_val( val ):
    val = str(val)
    #if empty string, pass through
    if val == '':
        return "''"
    # check for special words true, false, and null
    specialvals = [ 'TRUE', 'FALSE', 'NULL' ]
    if val.upper() in specialvals:
        return val.upper()
    # if it's a number, don't escape it:
    if is_number(val):
        return val
    # if it's an array, it's already escaped:
    if re.match('ARRAY\[.*', val) or re.match('{.*', val):
        return "'" + val + "'"
    # if it's a string, escape all '
    val = val.replace("'","''")
    # now quote it
    val = "'" + val + "'"
    return val

# make a value string from an array
# including shifting date an timestamp values
def value_string_shift ( vallist, tslist, datelist, ref_ts, ref_date ):
    newlist = []
    for valpos, value in enumerate(vallist):
        if valpos in tslist:
            # it's a timestamp, shift it
            newval = "'%s' + INTERVAL '%s'" % (ref_ts, value, )
        elif valpos in datelist:
            # if it's a date, shift it
            newval = "'%s' + %s" % (ref_date, value )
        else:
            newval = escape_val(value)

        newlist.append(newval)

    return newlist

def insert_col_list( coldict ):
    targetlist = ', '.join(coldict.keys())
    return targetlist

def insert_values_list( coldict ):
    collist = []
    for colname, colval in coldict.iteritems():
        if colval:
            collist.append('%(' + colname + ')s')
        else:
            collist.append("DEFAULT")

    vallist = ', '.join(collist)
    return vallist

def simple_insert_statement ( tablename, coldict ):
    insertstr = "INSERT INTO %s ( %s ) VALUES ( %s ) " % (tablename, insert_col_list(coldict),insert_values_list(coldict),)
    return insertstr

def execute_it(cur, statement, params=[]):
    try:
        cur.execute(statement, params)
    except Exception, e:
        log_activity(e.pgerror, True)
        return False
    return True

def get_one_row(cur, statement, params=[]):
    try:
        cur.execute(statement, params)
    except Exception, e:
        log_activity(e.pgerror, True)
        return None
    return cur.fetchone()

def get_one_val(cur, statement, params=[]):
    try:
        cur.execute(statement, params)
    except Exception, e:
        log_activity(e.pgerror, True)
        return None
    val = cur.fetchone()
    if val is not None:
        return val[0]
    else:
        return None



########NEW FILE########
__FILENAME__ = error

class CustomError(Exception):
    def __init__(self, errortype, message, parenterror=None):
        self.errortype = errortype
        self.message = message
        if parenterror:
            template = "{0}:\n{1!r}"
            errmsg = template.format(type(parenterror).__name__, parenterror.args)
            self.upstack = errmsg
        else:
            self.upstack = ""

    def __str__(self):
        if self.upstack:
            return "%s: %s FROM %s" % (self.errortype, self.message, self.upstack)
        else:
            return self.errortype + ': ' + self.message

    def errortype(self):
        return self.errortype

    def message(self):
        return self.message

    def upstack(self):
        return self.upstack
########NEW FILE########
__FILENAME__ = misc_utils
# this module contains a bunch of miscellaneous
# formatting and general glue functions for handyrep
# none of these functions expect access to the dictionaries

from datetime import datetime
import threading

def ts_string(some_ts):
    return datetime.strftime(some_ts, '%Y-%m-%d %H:%M:%S')

def string_ts(some_string):
    try:
        return datetime.strptime(some_string, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        return None

def now_string():
    return ts_string(datetime.now())

def succeeded(resdict):
    #checks a return_dict for success
    return (resdict["result"] == "SUCCESS")

def failed(resdict):
    # checks a return_dict for failure
    return (resdict["result"] == "FAIL")

def return_dict(succeeded, details=None, extra=None):
    # quick function for returning a dictionary of
    # results from complex functions
    if succeeded:
        result = "SUCCESS"
    else:
        result = "FAIL"

    if extra:
        extra.update({ "result" : result, "details" : details })
        return extra
    else:
        return { "result" : result, "details" : details }

def exstr(errorobj):
    template = "{0}:\n{1!r}"
    message = template.format(type(errorobj).__name__, errorobj.args)
    if not message:
        message = str(errorobj)
    return message

def get_nested_val(mydict, *args):
    newdict = mydict
    for key in args:
        try:
            newdict = newdict[key]
        except:
            return None

    return newdict

# returns the first non-None in a list
def notnone(*args):
    for arg in args:
        if arg is not None:
            return arg

    return None

# returns the first populated value in a list
def notfalse(*args):
    for arg in args:
        if arg:
            return arg

    return None

# rlock function for locking fabric access
# we need to do this because fabric is not multi-threaded

def lock_fabric(locked=True):
    lock = threading.RLock()
    if locked:
        lock.acquire()
        return True
    else:
        try:
            lock.release()
        except RuntimeError:
            # ignore it if we didn't have the lock
            return False

def fabric_unlock_all():
    unlocked = True
    while unlocked:
        unlocked = lock_fabric(False)

    return True
########NEW FILE########
__FILENAME__ = archive_barman_staging
# archiving script plugin
# designed for systems with only two PostgreSQL servers
# where the archive logs are written to whichever server
# is the replica at the time, and a separate barman server
# wal files are copied to an additional staging directory
# before being copied off to the barman server by a local cron
# job on each server
# this cron job is NOT managed by HandyRep at this time

# this means that we give each server the other server
# as its replica target

# depending on settings, may automatically disable
# archive replication if the replica is down

# configuration with examples
'''
        archive_directory = /var/lib/postgresql/wal_archive
        archive_script_path =  /var/lib/postgresql/archive.sh
        archive_script_template = archive.sh.barman_staging.template
        stop_archiving_file = /var/lib/postgresql/NOARCHIVING
        archivecleanup_path = /usr/lib/postgresql/9.3/bin/pg_archivecleanup
        disable_on_fail = False
        barman_staging_dir = /var/wal_spool/
'''

from plugins.handyrepplugin import HandyRepPlugin

class archive_barman_staging(HandyRepPlugin):

    def run(self, servername):
        # pushes archive script
        # which is set up for two-server archiving
        self.log("ARCHIVE","pushing archive script")
        archiveinfo = self.conf["archive"]
        myconf = self.get_myconf()
        otherserv = self.other_server(servername)
        if not otherserv:
            return self.rd(False, "no other server configured for archving")
        
        archdict = { "archive_directory" : myconf["archive_directory"],
            "no_archive_file" : "stop_archiving_file",
            "archive_host" : otherserv,
            "staging_dir" : myconf["barman_staging_dir"] }
        pushit = self.push_template(servername, myconf["archive_script_template"], myconf["archive_script_path"], archdict, self.conf["handyrep"]["postgres_superuser"],
        700)
        if self.failed(pushit):
            return pushit

        pushit = self.push_template(servername, myconf["copy_script_template"], myconf["copy_script_location"], archdict, self.conf["handyrep"]["postgres_superuser"], 700)
        if self.failed(pushit):
            return pushit

        # if that worked, let's make sure the rest of the setup is complete
        # make archive directory
        if not self.file_exists(otherserv, myconf["archive_directory"]):
            createcmd = "mkdir %s" % myconf["archive_directory"]
            self.run_as_postgres(otherserv, [createcmd,])
        # make barman directory
        if not self.file_exists(servername, myconf["barman_staging_dir"]):
            createcmd = "mkdir %s" % myconf["barman_staging_dir"]
            self.run_as_postgres(servername, [createcmd,])

        return self.rd(True, "archive script pushed")

    def recoveryline(self):
        # returns archive recovery line for recovery.conf
        myconf = self.get_myconf()
        restcmd = """restore_command = 'cp %s""" % myconf["archive_directory"]
        restcmd += "/%f %p'\n\n"
        restcmd += "archive_cleanup_command = '%s %s" % (myconf["archivecleanup_path"], myconf["archive_directory"],) + " %r'\n"
        return restcmd

    def poll(self):
        # what it does is checks to see if the
        # replica is unsshable
        # and then disables archiving depending
        # on settings via the stop archiving file
        self.log("ARCHIVE","Polling Archving")

        # first, though, we need to spool wal logs off to
        # the barman server
        # try the currently enabled barman server
        master = self.get_master()

        repservs = self.get_servers(role="replica")
        myconf = self.get_myconf()
        if not repservs:
            return self.rd("False","no currently configured replica")
        else:
            if myconf["disable_on_fail"]:
                repstat = self.servers[repservs[0]]["status_no"]
                if not self.get_master_name():
                    return self.rd(False, "no configured master")
                
                if repstat > 3:
                    # replica is down, check that we can ssh to it
                    sshcheck = self.run_as_handyrep(repservs[0], [self.conf["handyrep"]["test_ssh_command"],])
                    if self.failed(sshcheck):
                        touchit = "touch %s" % myconf["stop_archiving_file"]
                        disabled = self.run_as_postgres(self.get_master_name(),[touchit,])
                        if succeeded(disabled):
                            self.log("ARCHIVE","Archiving disabled due to replica failure", True)
                            return self.rd(True, "disabled archiving")
                        else:
                            self.log("ARCHIVE","Unable to disable archiving despite replica failure", True)
                            return self.rd(False, "Unable to disable archiving")
                    else:
                        return self.rd(True, "replica responds to ssh")
            else:
                return self.rd(True, "auto-disable not configured")

    def stop(self):
        # halts archiving on the master
        # by pushing a noarchving file
        myconf = self.get_myconf()
        touchit = "touch %s" % myconf["stop_archiving_file"]
        disabled = self.run_as_postgres(self.get_master_name(),[touchit,])
        if self.succeeded(disabled):
            return self.rd(True, "Created noarchiving touch file")
        else:
            return self.rd(False, "Unable to create noarchiving file")

    def start(self):
        # push template first
        myconf = self.get_myconf()
        master = self.get_master_name()
        if self.failed(self.run(master)):
            return self.rd(False, "unable to update archving script")

        touchit = "rm -f %s" % myconf["stop_archiving_file"]
        enabled = self.run_as_postgres(master,[touchit,])
        if self.succeeded(enabled):
            return self.rd(True, "Removed noarchiving touch file")
        else:
            return self.rd(False, "Unable to remove noarchiving file")

    def test(self):
        if self.failed(self.test_plugin_conf("archive_barman_staging","archive_directory","archivecleanup_path","stop_archiving_file","archive_script_template","archive_script_path","barman_staging_dir")):
            return self.rd(False, "archive_barman_staging is not configured")
        else:
            if self.failed(self.run_as_postgres(self.get_master_name(), [self.conf["handyrep"]["test_ssh_command"],])):
                return self.rd(False, "cannot ssh as postgres to master")
            else:
                return self.rd(True, "archive_two_servers configured")

    def other_server(self, servername):
        # returns the name of the other server
        for serv, servdeets in self.servers.iteritems():
            if servdeets["enabled"] and serv <> servername and servdeets["role"] in ["master","replica",]:
                return serv

        return None


        

########NEW FILE########
__FILENAME__ = archive_delete_find
# plugin method for deleting files from an archive
# using the linux "find" commmand.
# this only works if you have a configuration
# with a single archive server which is
# defined in the servers dictionary

from plugins.handyrepplugin import HandyRepPlugin

class archive_delete_find(HandyRepPlugin):
    # plugin to delete old archive files from a shared archive
    # using linux "find" command

    def run(self):
        archiveinfo = self.conf["archive"]
        myconf = self.get_myconf()
        delmin = (as_int(myconf["archive_delete_hours"]) * 60)
        archiveserver = self.get_archiveserver()
        if not archiveserver:
            return self.rd(False, "no archive server is defined")
        
        find_delete = """find %s -regextype 'posix-extended' -maxdepth 1  -mmin +%d -regex '.*[0-9A-F]{24}' -delete""" % (myconf["archive_directory"],delmin,)
        adelete = self.run_as_root(archiveserver,[find_delete,])
        if self.succeeded(adelete):
            return adelete
        else:
            adelete.update( {"details" : "archive cleaning failed due to error: %s" % adelete["details"]})
            return adelete

    def test(self):
        archserv = self.get_archiveserver()
        if not archserv:
            return self.rd(False, "no archive server is defined")

        if self.failed(self.test_plugin_conf("archive_delete_find", "archive_directory", "archive_delete_hours")):
            return self.rd(False, "archive_delete_find is not configured correctly")
        else:
            return self.rd(True, "archive_delete_find is configured")

    def get_archiveserver(self):
        # assumes that there's only one enabled archive server
        archservs = self.get_servers(role="archive")
        if archservs:
            return archservs[0]
        else:
            return None

########NEW FILE########
__FILENAME__ = archive_local_dir
# archiving script plugin
# archives to locally mounted directory
# on master server; intended for use
# with SANs and similar setups

from plugins.handyrepplugin import HandyRepPlugin

class archive_local_dir(HandyRepPlugin):

    def run(self, servername):
        # pushes archive script
        # which is set up for two-server archiving
        archiveinfo = self.conf["archive"]
        myconf = self.get_myconf()
        
        archdict = { "archive_directory" : myconf["archive_directory"],
            "no_archive_file" : "stop_archiving_file"}
        pushit = self.push_template(servername, myconf["archive_script_template"], myconf["archive_script_path"], archdict, self.conf["handyrep"]["postgres_superuser"],
        700)
        return pushit

    def recoveryline(self):
        # returns archive recovery line for recovery.conf
        myconf = self.get_myconf()
        restcmd = "restore_command = cp %s" % myconf["archive_directory"]
        restcmd += "/%f %p\n\n"
        
        if self.is_true(myconf["cleanup_archive"]):
            restcmd += "archive_cleanup_command = '%s %s" % (myconf["archive_directory"], myconf["archivecleanup_path"],) + "%r'\n"
            
        return restcmd

    def poll(self):
        # does nothing
        return self.rd(True, "Nothing to poll")

    def stop(self):
        # halts archiving on the master
        # by pushing a noarchving file
        myconf = self.get_myconf()
        touchit = "touch %s" % myconf["stop_archiving_file"]
        disabled = self.run_as_postgres(self.get_master_name(),[touchit,])
        if succeeded(touchit):
            return self.rd(True, "Created noarchiving touch file")
        else:
            return self.rd(False, "Unable to create noarchiving file")

    def start(self):
        # push template first
        master = self.get_master_name()
        myconf = self.get_myconf()
        if failed(self.run(master)):
            return self.rd(False, "unable to update archving script")

        touchit = "rm -f %s" % myconf["stop_archiving_file"]
        disabled = self.run_as_postgres(master,[touchit,])
        if succeeded(touchit):
            return self.rd(True, "Removed noarchiving touch file")
        else:
            return self.rd(False, "Unable to remove noarchiving file")

    def test(self):
        if self.failed(self.test_plugin_conf("archive_local_dir","archive_directory","archivecleanup_path","stop_archving_file","archive_script_template","archive_script_path")):
            return self.rd(False, "archive_local_dir is not configured")
        else:
            return self.rd(True, "archive_local_dir is configured")


########NEW FILE########
__FILENAME__ = archive_two_servers
# archiving script plugin
# designed for systems with only two PostgreSQL servers
# where the archive logs are written to whichever server
# is the replica at the time
# this means that we give each server the other server
# as its replica target

# WARNING: Assumes that there's only two enabled servers
# in the configuration.  Will break if there are more
# than two!

# depending on settings, may automatically disable
# archive replication if the replica is down

from plugins.handyrepplugin import HandyRepPlugin

class archive_two_servers(HandyRepPlugin):

    def run(self, servername):
        # pushes archive script
        # which is set up for two-server archiving
        archiveinfo = self.conf["archive"]
        myconf = self.get_myconf()
        otherserv = self.other_server(servername)
        if not otherserv:
            return self.rd(False, "no other server configured for archving")
        
        archdict = { "archive_directory" : myconf["archive_directory"],
            "no_archive_file" : myconf["stop_archiving_file"],
            "archive_host" : otherserv }
        pushit = self.push_template(servername, myconf["archive_script_template"], myconf["archive_script_path"], archdict, self.conf["handyrep"]["postgres_superuser"],
        700)
        if self.failed(pushit):
            return pushit

        # if that worked, let's make sure the rest of the setup is complete
        # make archive directory
        if not self.file_exists(otherserv, myconf["archive_directory"]):
            createcmd = "mkdir %s" % myconf["archive_directory"]
            self.run_as_postgres(otherserv, [createcmd,])

        return self.rd(True, "archive script pushed")

    def recoveryline(self):
        # returns archive recovery line for recovery.conf
        myconf = self.get_myconf()
        restcmd = """restore_command = 'cp %s""" % myconf["archive_directory"]
        restcmd += "/%f %p'\n\n"
        restcmd += "archive_cleanup_command = '%s %s" % (myconf["archivecleanup_path"], myconf["archive_directory"],) + " %r'\n"
        return restcmd

    def poll(self):
        # doesn't actually poll archive server
        # what it does is checks to see if the
        # replica is unsshable
        # and then disables archiving depending
        # on settings via the stop archiving file
        repservs = self.get_servers(role="replica")
        myconf = self.get_myconf()
        if not repservs:
            return self.rd("False","no currently configured replica")
        else:
            if myconf["disable_on_fail"]:
                repstat = self.servers[repservs[0]]["status_no"]
                if not self.get_master_name():
                    return self.rd(False, "no configured master")
                
                if repstat > 3:
                    # replica is down, check that we can ssh to it
                    sshcheck = self.run_as_handyrep(repservs[0], [self.conf["handyrep"]["test_ssh_command"],])
                    if self.failed(sshcheck):
                        touchit = "touch %s" % myconf["stop_archiving_file"]
                        disabled = self.run_as_postgres(self.get_master_name(),[touchit,])
                        if succeeded(disabled):
                            self.log("ARCHIVE","Archiving disabled due to replica failure", True)
                            return self.rd(True, "disabled archiving")
                        else:
                            self.log("ARCHIVE","Unable to disable archiving despite replica failure", True)
                            return self.rd(False, "Unable to disable archiving")
                    else:
                        return self.rd(True, "replica responds to ssh")
            else:
                return self.rd(True, "auto-disable not configured")

    def stop(self):
        # halts archiving on the master
        # by pushing a noarchving file
        myconf = self.get_myconf()
        touchit = "touch %s" % myconf["stop_archiving_file"]
        disabled = self.run_as_postgres(self.get_master_name(),[touchit,])
        if self.succeeded(disabled):
            return self.rd(True, "Created noarchiving touch file")
        else:
            return self.rd(False, "Unable to create noarchiving file")

    def start(self):
        # push template first
        myconf = self.get_myconf()
        master = self.get_master_name()
        if self.failed(self.run(master)):
            return self.rd(False, "unable to update archving script")

        touchit = "rm -f %s" % myconf["stop_archiving_file"]
        enabled = self.run_as_postgres(master,[touchit,])
        if self.succeeded(enabled):
            return self.rd(True, "Removed noarchiving touch file")
        else:
            return self.rd(False, "Unable to remove noarchiving file")

    def test(self):
        if self.failed(self.test_plugin_conf("archive_two_servers","archive_directory","archivecleanup_path","stop_archiving_file","archive_script_template","archive_script_path")):
            return self.rd(False, "archive_two_servers is not configured")
        else:
            if self.failed(self.run_as_postgres(self.get_master_name(), [self.conf["handyrep"]["test_ssh_command"],])):
                return self.rd(False, "cannot ssh as postgres to master")
            else:
                return self.rd(True, "archive_two_servers configured")

    def other_server(self, servername):
        # returns the name of the other server
        for serv, servdeets in self.servers.iteritems():
            if servdeets["enabled"] and serv <> servername and servdeets["role"] in ["master","replica",]:
                return serv

        return None

########NEW FILE########
__FILENAME__ = clone_basebackup
# simple cloning plugin for cloning via basebackup
# does NOT deal with things like tablespaces and relocated WAL

from plugins.handyrepplugin import HandyRepPlugin

class clone_basebackup(HandyRepPlugin):

    def run(self, servername, clonefrom, reclone):
        # clear the remote directory if recloning
        if reclone:
            delcmd = "rm -rf %s/*" % self.servers[servername]["pgdata"]
            delit = self.run_as_root(servername, [delcmd,])
            if self.failed(delit):
                return self.rd(False, "Unable to clear PGDATA directory, aborting")

        # run pgbasebackup
        myconf = self.get_conf("plugins","clone_basebackup")
        if myconf:
            bbparam = { "path" : myconf["basebackup_path"],
                "extra" : myconf["extra_parameters"] }
            if not bbparam["extra"]:
                bbparam["extra"]=""
        else:
            bbparam = { "path" : "pg_basebackup", "extra" : "" }

        bbparam.update({ "pgdata" : self.servers[servername]["pgdata"],
            "host" : self.servers[clonefrom]["hostname"],
            "port" : self.servers[clonefrom]["port"],
            "user" : self.conf["handyrep"]["replication_user"],
            "pass" : self.conf["passwords"]["replication_pass"]})
        pgbbcmd = "%(path)s -x -D %(pgdata)s -h %(host)s -p %(port)d -U %(user)s %(extra)s" % bbparam
        cloneit = self.run_as_replication(servername, [pgbbcmd,])
        return cloneit

    def test(self,servername):
        #check if we have a config
        if self.failed(self.test_plugin_conf("clone_basebackup","basebackup_path")):
            return self.rd(False, "clone_basebackup not properly configured")
        #check if the basebackup executable
        #is available on the server
        if self.failed(self.run_as_postgres(servername,"%s --help" % self.conf["plugins"]["clone_basebackup"]["basebackup_path"])):
            return self.rd(False, "pg_basebackup executable not found")

        return self.rd(True, "clone_basebackup works")

########NEW FILE########
__FILENAME__ = clone_rsync
#plugin for cloning via Rsync.
#currently deals with a linked WAL directory, but NOT with tablespaces.
#assumes passwordless rsync

from plugins.handyrepplugin import HandyRepPlugin
import os.path

class clone_rsync(HandyRepPlugin):

    def run(self, servername, clonefrom=None, reclone=False):
        # we assume that upstream has already checked that it is safe
        # to reclone, so we don't worry about it
        if not clonefrom:
            clonefrom = self.get_master_name()

        myconf = self.get_myconf()
        # issue pg_stop_backup() on the master
        mconn = self.master_connection(mautocommit=True)
        if not mconn:
            return self.rd(False, "unable to connect to master server to start cloning")

        blabel = "hr_clone_%s" % servername
        mcur = mconn.cursor()
        bstart = self.execute_it(mcur, "SELECT pg_start_backup(%s, TRUE)", [blabel,])
        mconn.close()
        if not bstart:
            return self.rd(False, "unable to start backup for cloning")

        # rsync PGDATA on the replica
        synccmd = self.rsync_command(servername, clonefrom)
        syncit = self.run_as_postgres(servername, [synccmd,])
        if self.failed(syncit):
            self.stop_backup(servername)
            return self.rd(False, "unable to rsync files")

        # wipe the replica's wal_location
        # we don't create this wal location, since there's
        # no reason for it to have been deleted.
        repwal = self.wal_path(servername)
        if self.file_exists(servername, repwal):
            syncit = self.run_as_postgres(servername, ["rm -rf %s/*" % repwal,])
        else:
            syncit = self.run_as_postgres(servername, ["mkdir %s" % repwal,])

        # failed?  something's wrong
        if self.failed(syncit):
            self.stop_backup(servername)
            return self.rd(False, "unable to rsync files; WAL directory is missing or broken")

        # stop backup
        syncit = self.stop_backup(servername)
        
        # yay, done!
        if self.succeeded(syncit):
            return self.rd(True, "cloning succeeded")
        else:
            return self.rd(False, "cloning failed; could not stop backup")

    def wal_path(self, servername):
        myconf = self.get_myconf()
        if "wal_location" in self.servers[servername]:
            if self.servers[servername]["wal_location"]:
                return self.servers[servername]["wal_location"]

        return os.path.join(self.servers[servername]["pgdata"], "pg_xlog")

    def rsync_command(self, servername, clonefrom):
        # create rsync command line
        myconf = self.get_myconf()
        if self.is_true(myconf["use_compression"]):
            compopt = " -z "
        else:
            compopt = ""

        if myconf["rsync_path"]:
            rsloc = myconf["rsync_path"]
        else:
            rsloc = "rsync"

        if self.is_true(myconf["use_ssh"]):
            if myconf["ssh_path"]:
                sshloc = myconf["ssh_path"]
            else:
                sshloc = "ssh"
                
            sshopt = """ -e "%s -o Compression=no -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -c arcfour" """ % sshloc

        mastdata = "%s:%s" % (self.servers[clonefrom]["hostname"], self.servers[clonefrom]["pgdata"],)
        repdata = self.servers[servername]["pgdata"]
        rscmd = """%s -av --delete --exclude postmaster.pid --exclude recovery.conf --exclude recovery.done --exclude postgresql.conf --exclude pg_log --exclude pg_xlog %s %s %s/* %s""" % (rsloc, compopt, sshopt, mastdata, repdata,)
        return rscmd

    def stop_backup(self, servername):
        
        mconn = self.master_connection(mautocommit=True)
        if not mconn:
            return self.rd(False, "unable to connect to master server to stop backup")

        mcur = mconn.cursor()
        bstart = self.execute_it(mcur, "SELECT pg_stop_backup()")
        mconn.close()
        
        if not bstart:
            return self.rd(False, "unable to stop backup")
        else:
            return self.rd(True, "backup stopped")

    def test(self,servername):
        #check if we have a config
        if self.failed(self.test_plugin_conf("clone_rsync","rsync_path")):
            return self.rd(False, "clone_rsync not properly configured")
        #check if the basebackup executable
        #is available on the server
        if self.failed(self.run_as_postgres(servername,"%s --help" % self.conf["plugins"]["clone_rsync"]["rsync_path"])):
            return self.rd(False, "rsync executable not found")

        return self.rd(True, "clone_rsync works")

########NEW FILE########
__FILENAME__ = failplugin
# generic failure plugin
# designed to substitute for a real plugin when
# the real plugin errors out
# this way we can hand a readable error message up the stack

from plugins.handyrepplugin import HandyRepPlugin

class failplugin(HandyRepPlugin):

    # override init so we can capture the plugin name
    def __init__(self, pluginname):
        self.pluginname = pluginname
        return

    def run(self, *args, **kwargs):
        return self.rd( False,"broken plugin called or no such plugin exists: %s" % self.pluginname )

    def test(self, *args, **kwargs):
        return self.rd( False,"broken plugin called or no such plugin exists: %s" % self.pluginname )

    def poll(self, *args, **kwargs):
        return self.rd( False,"broken plugin called or no such plugin exists: %s" % self.pluginname )

    def start(self, *args, **kwargs):
        return self.rd( False,"broken plugin called or no such plugin exists: %s" % self.pluginname )

    def stop(self, *args, **kwargs):
        return self.rd( False,"broken plugin called or no such plugin exists: %s" % self.pluginname )

########NEW FILE########
__FILENAME__ = handyrepplugin
from fabric.api import sudo, run, env, local, settings, shell_env
from fabric.network import disconnect_all
from fabric.contrib.files import upload_template, exists
#from fabric.context_managers import shell_env
from lib.error import CustomError
from lib.dbfunctions import get_one_val, get_one_row, execute_it, get_pg_conn
from lib.misc_utils import ts_string, string_ts, now_string, succeeded, failed, return_dict, exstr, lock_fabric, fabric_unlock_all
import json
from datetime import datetime, timedelta
import logging
import time
import psycopg2
import psycopg2.extensions
from os.path import join
from subprocess import call
import re
import threading

class HandyRepPlugin(object):

    def __init__(self, conf, servers):
        self.conf = conf
        self.servers = servers
        return

    def sudorun(self, servername, commands, runas, passwd="", sshpass=None):
        # generic function to run one or more commands
        # as a specific remote user.  returns the results
        # of the last command run.  aborts when any
        # command fails
        lock_fabric()
        if sshpass:
            env.password = sshpass
        else:
            env.key_filename = self.servers[servername]["ssh_key"]
            
        env.user = self.servers[servername]["ssh_user"]
        env.disable_known_hosts = True
        env.host_string = self.servers[servername]["hostname"]
        rundict = return_dict(True, "no commands provided", {"return_code" : None })
        if passwd is None:
            pgpasswd = ""
        else:
            pgpasswd = passwd

        for command in commands:
            try:
                with shell_env(PGPASSWORD=pgpasswd):
                    runit = sudo(command, user=runas, warn_only=True,pty=False, quiet=True)
                rundict.update({ "details" : runit ,
                    "return_code" : runit.return_code })
                if runit.succeeded:
                    rundict.update({"result":"SUCCESS"})
                else:
                    rundict.update({"result":"FAIL"})
                    break
            except Exception as ex:
                rundict = { "result" : "FAIL",
                    "details" : "connection failure: %s" % self.exstr(ex),
                    "return_code" : None }
                break
        
        self.disconnect_and_unlock()
        return rundict

    def run_as_postgres(self, servername, commands):
        pguser = self.conf["handyrep"]["postgres_superuser"]
        pwd = self.conf["passwords"]["superuser_pass"]
        return self.sudorun(servername, commands, pguser, pwd)

    def run_as_replication(self, servername, commands):
        # we actually use the command-line superuser for this
        # since the replication user doesn't generally have a shell
        # account
        pguser = self.conf["handyrep"]["postgres_superuser"]
        pwd = self.conf["passwords"]["replication_pass"]
        return self.sudorun(servername, commands, pguser, pwd)

    def run_as_root(self, servername, commands):
        return self.sudorun(servername, commands, "root")

    def run_as_handyrep(self, servername, commands):
        # runs a set of commands as the "handyrep" user
        # exiting when the first command fails
        # returns a dic with the results of the last command
        # run
        lock_fabric()
        env.key_filename = self.servers[servername]["ssh_key"]
        env.user = self.servers[servername]["ssh_user"]
        env.disable_known_hosts = True
        env.host_string = self.servers[servername]["hostname"]
        rundict = { "result": "SUCCESS",
            "details" : "no commands provided",
            "return_code" : None }
        for command in commands:
            try:
                runit = run(command, warn_only=True, quiet=True)
                rundict.update({ "details" : runit ,
                    "return_code" : runit.return_code })
                if runit.succeeded:
                    rundict.update({"result":"SUCCESS"})
                else:
                    rundict.update({"result":"FAIL"})
                    break
            except Exception as ex:
                rundict = { "result" : "FAIL",
                    "details" : "connection failure: %s" % exstr(ex),
                    "return_code" : None }
                break

        self.disconnect_and_unlock()
        return rundict

    def run_local(self, commands):
        # run a bunch of commands on the local machine
        # as the handyrep user
        # exit on the first failure
        rundict = { "result": "SUCCESS",
            "details" : "no commands provided",
            "return_code" : None }
        for command in commands:
            try:
                runit = call(command, shell=True)
                rundict.update({ "details" : "ran command %s" % command ,
                    "return_code" : runit })
            except Exception as ex:
                rundict = { "result" : "FAIL",
                    "details" : "execution failure: %s" % self.exstr(ex),
                    "return_code" : None }
                break

        return rundict

    def file_exists(self, servername, filepath):
        # checks whether a particular file or directory path
        # exists
        # returns only true or false rather than RD
        env.key_filename = self.servers[servername]["ssh_key"]
        env.user = self.servers[servername]["ssh_user"]
        env.disable_known_hosts = True
        env.host_string = self.servers[servername]["hostname"]
        if exists(filepath, use_sudo=True):
            return True
        else:
            return False

    def push_template(self, servername, templatename, destination, template_params, new_owner=None, file_mode=700):
        # renders a template file and pushes it to the
        # target location on an external server
        # not implemented for writing to localhost at this time
        lock_fabric()
        env.key_filename = self.servers[servername]["ssh_key"]
        env.user = self.servers[servername]["ssh_user"]
        env.disable_known_hosts = True
        env.host_string = self.servers[servername]["hostname"]
        try:
            upload_template( templatename, destination, use_jinja=True, context=template_params, template_dir=self.conf["handyrep"]["templates_dir"], use_sudo=True )
            if file_mode:
                sudo("chmod %d %s" % (file_mode, destination,), quiet=True)
            if new_owner:
                sudo("chown %s %s" % (new_owner, destination,), quiet=True)
        except:
            retdict = return_dict(False, "could not push template %s to server %s" % (templatename, servername,))
        else:
            retdict = return_dict(True, "pushed template")
        finally:
            self.disconnect_and_unlock()

        return retdict

    def get_conf(self, *args):
        # a "safe" configuration reader
        # gets a single option or returns None if that option isn't set
        # instead of erroring
        myconf = self.conf
        for key in args:
            try:
                myconf = myconf[key]
            except:
                return None

        return myconf

    def pluginconf(self, confkey):
        # gets the config dictionary for the plugin
        # or returns an empty dict if none
        conf = self.get_conf("plugins",self.__class__.__name__,confkey)
        return conf

    def get_myconf(self):
        confname = self.__class__.__name__
        if confname in self.conf["plugins"]:
            return self.conf["plugins"][confname]
        else:
            return None

    def get_serverinfo(self, *args):
        # a "safe" configuration reader for server configuration
        # gets a single option or returns None if that option isn't set
        # instead of erroring
        myconf = self.servers
        for key in args:
            try:
                myconf = myconf[key]
            except:
                return None

        return myconf

    def log(self, category, message, iserror=False):
        if iserror:
            logging.error("%s: %s" % (category, message,))
        else:
            logging.info("%s: %s" % (category, message,))
        return

    def get_master_name(self):
        for servname, servdata in self.servers.iteritems():
            if servdata["role"] == "master" and servdata["enabled"]:
                return servname
        # no master?  return None and let the calling function
        # handle it
        return None

    def connection(self, servername, autocommit=False):
        # connects as the handyrep user to a remote database
        connect_string = "dbname=%s host=%s port=%s user=%s application_name=handyrep " % (self.conf["handyrep"]["handyrep_db"], self.servers[servername]["hostname"], self.servers[servername]["port"], self.conf["handyrep"]["handyrep_user"],)

        if self.conf["passwords"]["handyrep_db_pass"]:
                connect_string += " password=%s " % self.conf["passwords"]["handyrep_db_pass"]

        try:
            conn = psycopg2.connect( connect_string )
        except:
            raise CustomError("DBCONN","ERROR: Unable to connect to Postgres using the connections string %s" % connect_string)

        if autocommit:
            conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

        return conn

    def master_connection(self, mautocommit=False):
        # connect to the master.  if unable to
        # or if it's not really the master, fail
        master = self.get_master_name()
        if not master:
            raise CustomError("CONFIG","No master server found in server configuration")

        try:
            mconn = self.connection(master, autocommit=mautocommit)
        except:
            raise CustomError("DBCONN","Unable to connect to configured master server.")

        return mconn

    def failwait(self):
        time.sleep(self.conf["failover"]["fail_retry_interval"])
        return

    def sorted_replicas(self, maxstatus=2):
        # returns a list of currently enabled and running replicas
        # sorted by failover_priority
        goodreps = {}
        for serv, servdeets in self.servers.iteritems():
            if servdeets["enabled"] and servdeets["status_no"] <= maxstatus and servdeets["role"] == "replica":
                goodreps[serv] = servdeets["failover_priority"]

        sreps = sorted(goodreps,key=goodreps.get)
        return sreps

    def test_plugin_conf(self, pluginname, *args):
        # loops through the list of given parameters and
        # makes sure they all exist and are populated
        pconf = self.get_conf("plugins",pluginname)
        if not pconf:
            return self.rd(False, "configuration for %s not found" % pluginname)
        
        missing_params = []
        for param in args:
            if param in pconf:
                if not pconf[param]:
                    missing_params.append(param)
            else:
                missing_params.append(param)

        if len(missing_params) > 0:
            return self.rd(False, "missing parameters: %s" % ','.join(missing_params))
        else:
            return self.rd(True, "config passed")

    def get_servers(self, **kwargs):
        # loops through self.servers, returning
        # servers whose criteria match kwargs
        # returns a list of server names
        servlist = []
        # append "enabled" to criteria if not supplied
        if "enabled" not in kwargs:
            kwargs.update({ "enabled" : True })
        elif kwargs["enabled"] is None:
            # if None, then the user doesn't care
            # about enabled status
            del kwargs["enabled"]

        for serv, servdeets in self.servers.iteritems():
            if all((tag in servdeets and servdeets[tag] == val) for tag, val in kwargs.iteritems()):
                servlist.append(serv)

        return servlist

    # type conversion functions for config files

    def is_true(self, confstr):
        if confstr:
            if type(confstr) is bool:
                return confstr
            if confstr.lower() in ("1","on","true","yes"):
                return True
            else:
                return False
        else:
            return False

    def as_int(self, confstr):
        if confstr:
            if type(confstr) is int:
                return confstr
            else:
                if re.match(r'\d+$',confstr):
                    return int(confstr)
                else:
                    return None
        else:
            return None

    def disconnect_and_unlock(self):
        disconnect_all()
        lock_fabric(False)
        return True

    # the functions below are shell functions for stuff in
    # misc_utils and dbfunctions  they're created here so that
    # users don't need to reimport them when writing functions

    def ts_string(self, some_ts):
        return ts_string(some_ts)

    def string_ts(self, some_string):
        return string_ts(some_string)

    def now_string(self):
        return now_string()

    def succeeded(self, retdict):
        return succeeded(retdict)

    def failed(self, retdict):
        return failed(retdict)

    def rd(self, success, details, extra={}):
        return return_dict(success,details,extra)

    def get_one_val(self, cur, statement, params=[]):
        return get_one_val(cur, statement, params)

    def get_one_row(self, cur, statement, params=[]):
        return get_one_row(cur, statement, params)

    def execute_it(self, cur, statement, params=[]):
        return execute_it(cur, statement, params)

    def exstr(self, errorobj):
        return exstr(errorobj)

    
########NEW FILE########
__FILENAME__ = haproxy_update
# simple haproxy plugin for updating haproxy configuration.
# creates 3 pools - general, master & slaves
# this assumes defaults are set in /etc/haproxy/haproxy.conf

from plugins.handyrepplugin import HandyRepPlugin
from fabric.contrib.files import upload_template

class haproxy_update(HandyRepPlugin):

    def run(self, *args):
 
		myconf = self.get_conf("plugins","haproxy_update")

		haproxytemp = myconf["haproxy_template"]

		bbparam = { "hap_pg_cfg" : "/home/handyrep/haproxy_pg_conf.cfg" }		
		haproxycmd = "haproxy -f /etc/haproxy/haproxy.cfg -f %(hap_pg_cfg)s -p /var/run/haproxy.pid -st $(cat /var/run/haproxy.pid)" % bbparam
			
		haproxy_cfg = {}
		haproxy_cfg["pool_port"] = myconf["pool_port"] 
		haproxy_cfg["master_pool_port"] = myconf["master_pool_port"] 
		haproxy_cfg["slave_pool_port"] = myconf["slave_pool_port"] 
		haproxy_cfg["pg_port"] = self.get_conf("server_defaults","port") 
		haproxy_cfg["master_server"] = self.get_master_name() 
		haproxy_cfg["slave_servers"] = self.sorted_replicas()

		for haproxyserv in self.get_servers(role='haproxy'):			
			# upload_template to haproxy server		
			self.push_template(haproxyserv, haproxytemp, myconf["hap_pg_cfg"], haproxy_cfg, new_owner=None, file_mode=755)
			# update the haproxy memory configuration
				updated = self.run_as_root(haproxyserv, [haproxycmd,])
        return updated

    def test(self):
        #check if we have a config
        if self.failed(self.test_plugin_conf("haproxy_update","haproxy_template","hap_pg_cfg")):
            return self.rd(False, "haproxy_update not properly configured")
        #check if the basebackup executable
        #is available on the server
        #if self.failed(self.run_as_postgres(servername,"%s --help" % self.conf["plugins"]["clone_basebackup"]["basebackup_path"])):
        #    return self.rd(False, "pg_basebackup executable not found")

        return self.rd(True, "haproxy_update works")

########NEW FILE########
__FILENAME__ = ldap_auth
# authenticates against an
# LDAP server.  all users are assumed to be in
# a specific LDAP group.  The below was tested to
# work with Microsoft AD/LDAP, so it might need changes
# to generically support other kinds of LDAP servers

# this auth module requires the dictionary lookup password
# to be stored in plain text in the configuration file
# since the alternative is to make users log in with their
# CN, we do it anyway

# requires python_ldap module

# configuration:
'''
    [[ldap_auth]]
        uri = ldap://ldap.corp.com/
        bind_dn = 'cn=pgauth,cn=Users,dc=corp,dc=com'
        base_dn = 'dc=corp,dc=com'
        hr_group = DBA
        log_auth = False
        debug_auth = False
'''

import ldap

from plugins.handyrepplugin import HandyRepPlugin

class ldap_auth(HandyRepPlugin):

    def run(self, username, userpass, funcname=None):

        myconf = self.get_myconf()

        group = myconf["hr_group"]

        users = search_for_user(username)
        if not users:
            return self.exit_log("User %s not found" % username)
        elif len(users) > 1:
            return self.exit_log("More than one user found for %s" % username)
        else:
            user = users[0]

        if not is_user_in_group(user, group):
            return self.exit_log('Error: %s is not in group %s.' % (username, group))

        if not authenticate(user, password):
            return self.exit_log("Incorrect password for %s" % user)
        else:
            return self.exit_log("Authenticated")


    def test(self):
        if self.failed(self.test_plugin_conf("ldap_auth","uri","bind_dn","base_dn","hr_group")):
            return self.rd(False, "plugin ldap_auth is not correctly configured")
        else:
            return self.rd(True, "ldap_auth has all configuration variables")


    def exit_log (self, success, message):
        myconf = self.get_myconf()
        if success:
            if is_true(myconf["log_auth"]):
                self.log("AUTH", "user %s authenticated" % username)

            return self.rd(success, message)
        else:
            self.log("AUTH", "user %s failed to authenticate", is_true(myconf["log_auth"]))
            
            if is_true(myconf["debug_auth"]):
                return self.rd(success, message)
            else:
                return self.rd(success, "Authentication Failed")


    def search_for_user(self, username):
        """
        Search for a user by username (e.g., 'qweaver').
        Return the a list of matching LDAP objects.
        Normally there will be just one matching object, representing the
        requested user.

        """
        myconf = self.get_myconf()
        user_dn = 'cn=Users,' + myconf["base_dn"]
        
        l = ldap.initialize(myconf["uri"])
        l.bind_s(myconf["bind_dn"], self.conf["passwords"]["bind_password"])
        matching_users = l.search_s(
            user_dn,
            ldap.SCOPE_SUBTREE,
            filterstr='(samaccountname={un})'.format(un=username)
            )
        return matching_users


    def dump_user(self, user):
        """
        Take an LDAP user object and return is as a pretty-printed string.
        Example usage:

        user_list = search_for_user('qweaver')
        user = user_list[0]
        print dump_user(user)

        """
        myconf = self.get_myconf()
        cn = user[0]
        fields = user[1]

        print 'Found user "{cn}":\n-----'.format(cn = cn)
        for key in sorted(fields.keys()):
            print key, '=', fields[key]


    def is_user_in_group(self, user, group):
        """
        Take an LDAP user object and a group name. Return True if the user
        is in the group, False otherwise.

        """

        cn = user[0]
        fields = user[1]
        myconf = self.get_myconf()

        memberships = None
        try:
            memberships = fields['memberOf']
        except KeyError:
            # The user isn't a member of *any* groups.
            return False

        group_dn = "CN=%s,OU=Groups,%s" % ( group, myconf["base_dn"] )

        for mem in memberships:
            # Bit of hard-coding here.
            if mem == group_dn:
                return True
        return False


    def authenticate(self, user, password):
        """
        Take an LDAP user object and a cleartext password string.
        Return True if AD successfully authenticates the user with the password,
        False otherwise.

        """
        myconf = self.get_myconf()
        l = ldap.initialize(myconf["uri"])

        fields = user[1]
        dn = fields['distinguishedName'][0]

        try:
            l.bind_s(dn, password)
        except ldap.LDAPError as lde:
            print "LDAP authen failed for user '{dn}'. Exception says:\n{desc}\n".format(
                dn=dn,
                desc=lde.message['desc'],
                )
            return False
        else:
            return True



########NEW FILE########
__FILENAME__ = multi_pgbouncer
# plugin method for failing over connections
# using pgbouncer
# rewrites the list of databases

# plugin for users running multiple pgbouncer servers
# requires that each pgbouncer server be in the servers dictionary
# as role "pgbouncer" and enabled.

# further, this plugin requires that the handyrep user, DB and password be set
# up on pgbouncer as a valid connection string.

from plugins.handyrepplugin import HandyRepPlugin

class multi_pgbouncer(HandyRepPlugin):

    def run(self, newmaster=None):
        # used for failover of all pgbouncer servers
        if newmaster:
            master = newmaster
        else:
            master = self.get_master_name()
        blist = self.bouncer_list()
        faillist = []
        for bserv in blist:
            bpush = self.push_config(bserv, master)
            if self.failed(bpush):
                self.set_bouncer_status(bserv, "unavailable", 4, "unable to reconfigure pgbouncer server for failover")
                faillist.append(bserv)

        if faillist:
            # report failure if we couldn't reconfigure any of the servers
            return self.rd(False, "some pgbouncer servers did not change their configuration at failover: %s" % ','.join(faillist))
        else:
            return self.rd(True, "pgbouncer failover successful")

    def init(self, bouncerserver=None):
        # used to initialize proxy servers with the correct connections
        # either for just the supplied bouncer server, or for all of them
        if bouncerserver:
            blist = [bouncerserver,]
        else:
            blist = self.bouncer_list()

        master = self.get_master_name()
        faillist = []
        for bserv in blist:
            bpush = self.push_config(bserv, master)
            # if we can't push a config, then add this bouncer server to the list
            # of failed servers and mark it unavailable
            if self.failed(bpush):
                self.set_bouncer_status(bserv, "unavailable", 4, "unable to reconfigure pgbouncer server for failover")
                faillist.append(bserv)
            else:
                try:
                    pgbcn = self.connection(bserv)
                except:
                    self.set_bouncer_status(bserv, "unavailable", 4, "pgbouncer configured, but does not accept connections")
                    faillist.append(bserv)
                else:
                    pgbcn.close()
                    self.set_bouncer_status(bserv, "healthy", 1, "pgbouncer initialized")

        if faillist:
            # report failure if we couldn't reconfigure any of the servers
            return self.rd(False, "some pgbouncer servers could not be initialized: %s" % ','.join(faillist))
        else:
            return self.rd(True, "pgbouncer initialization successful")
        

    def set_bouncer_status(self, bouncerserver, status, status_no, status_message):
        self.servers[bouncerserver]["status"] = status
        self.servers[bouncerserver]["status_no"] = status_no
        self.servers[bouncerserver]["status_message"] = status_message
        self.servers[bouncerserver]["status_ts"] = self.now_string()
        return

    def push_config(self, bouncerserver, newmaster=None):
        # pushes a new config to the named pgbouncer server
        # and restarts it
        if newmaster:
            master = newmaster
        else:
            master = self.get_master_name()
        # get configuration
        dbsect = { "dbsection" : self.dbconnect_list(master), "port" : self.servers[bouncerserver]["port"] }
        # push new config
        myconf = self.conf["plugins"]["multi_pgbouncer"]
        writeconf = self.push_template(bouncerserver,myconf["template"],myconf["config_location"],dbsect,myconf["owner"])
        if self.failed(writeconf):
            return self.rd(False, "could not push new pgbouncer configuration to pgbouncer server")
        # restart pgbouncer
        restart_command = "%s -u %s -d -R %s" % (myconf["pgbouncerbin"],myconf["owner"],myconf["config_location"],)
        rsbouncer = self.run_as_root(bouncerserver,[restart_command,])
        if self.succeeded(rsbouncer):
            return self.rd(True, "pgbouncer configuration updated")
        else:
            return self.rd(False, "unable to restart pgbouncer")

    def bouncer_list(self):
        # gets a list of currently enabled pgbouncers
        blist = []
        for serv, servdeets in self.servers.iteritems():
            if servdeets["role"] == "pgbouncer" and servdeets["enabled"]:
                blist.append(serv)

        return blist


    def test(self):
        #check that we have all config variables required
        if self.failed( self.test_plugin_conf("multi_pgbouncer","pgbouncerbin","template","owner","config_location","database_list","readonly_suffix","all_replicas")):
            return self.rd(False, "multi-pgbouncer failover is not configured" )
        #check that we can connect to the pgbouncer servers
        blist = self.bouncer_list()
        if len(blist) == 0:
            return self.rd(False, "No pgbouncer servers defined")
        
        faillist = []
        for bserv in blist:
            if self.failed(self.run_as_root(bserv,self.conf["handyrep"]["test_ssh_command"])):
                faillist.append(bserv)

        if failist:
            return self.rd(False, "cannot SSH to some pgbouncer servers: %s" % ','.join(faillist))
        
        return self.rd(True, "pgbouncer setup is correct")
    

    def poll(self, bouncerserver=None):
        if bouncerserver:
            blist = [bouncerserver,]
        else:
            blist = self.bouncer_list()

        if len(blist) == 0:
            return self.rd(False, "No pgbouncer servers defined")

        faillist = []
        for bserv in blist:
            try:
                pgbcn = self.connection(bserv)
            except:
                self.set_bouncer_status(bserv, "unavailable", 4, "pgbouncer does not accept connections")
                faillist.append(bserv)
            else:
                pgbcn.close()
                self.set_bouncer_status(bserv, "healthy", 1, "pgbouncer responding")
                
        if faillist:
            # report failure if any previously enabled bouncers are down
            return self.rd(False, "some pgbouncer servers are not responding: %s" % ','.join(faillist))
        else:
            return self.rd(True, "all pgbouncers responding")

    def dbconnect_list(self, master):
        # creates the list of database aliases and target
        # servers for pgbouncer
        # build master string first
        myconf = self.conf["plugins"]["multi_pgbouncer"]
        dblist = myconf["database_list"]
        # add in the handyrep db if the user has forgotten it
        if self.conf["handyrep"]["handyrep_db"] not in dblist:
            dblist.append(self.conf["handyrep"]["handyrep_db"])
        constr = self.dbconnect_line(dblist, self.servers[master]["hostname"], self.servers[master]["port"], "", myconf["extra_connect_param"])
        replicas = self.sorted_replicas()
        if self.is_true(myconf["all_replicas"]):
            #if we're doing all replicas, we need to put them in as _ro0, _ro1, etc.
            # if there's no replicas, set ro1 to go to the master:
            if len(replicas) == 0 or (len(replicas) == 1 and master in replicas):
                rsuff = "%s%d" % (myconf["readonly_suffix"],1,)
                constr += self.dbconnect_line(myconf["database_list"], self.servers[master]["hostname"], self.servers[master]["port"], rsuff, myconf["extra_connect_param"])
            else:
                for rep in replicas:
                    if not rep == master:
                        rsuff = "%s%d" % (myconf["readonly_suffix"],repno,)
                        constr += self.dbconnect_line(myconf["database_list"], self.servers[rep]["hostname"], self.servers[rep]["port"], rsuff, myconf["extra_connect_param"])
                        repno += 1
        else:
            # only one readonly replica, setting it up with _ro
            if len(replicas) > 0:
                if replicas[0] == master:
                    # avoid the master
                    replicas.pop(0)
                    
            if len(replicas) > 0:
                constr += self.dbconnect_line(myconf["database_list"], self.servers[replicas[0]]["hostname"], self.servers[replicas[0]]["port"], myconf["readonly_suffix"], myconf["extra_connect_param"])
            else:
                # if no replicas, read-only connections should go to the master
                constr += self.dbconnect_line(myconf["database_list"], self.servers[master]["hostname"], self.servers[master]["port"], myconf["readonly_suffix"], myconf["extra_connect_param"])

        return constr


    def dbconnect_line(self, database_list, hostname, portno, suffix, extra):
        confout = ""
        if extra:
            nex = extra
        else:
            nex = ""
        for dbname in database_list:
            confout += "%s%s = dbname=%s host=%s port=%s %s \n" % (dbname, suffix, dbname, hostname, portno, nex,)

        return confout

    
########NEW FILE########
__FILENAME__ = multi_pgbouncer_bigip
# plugin method for failing over connections
# using pgbouncer
# rewrites the list of databases

# plugin for users running multiple pgbouncer servers
# requires that each pgbouncer server be in the servers dictionary
# as role "pgbouncer" and enabled.

# also intended to be run with the latest pgbouncer update which supports
# include files for pgbouncer, instead of writing directly to pgbouncer.ini;
# will not work correctly on standard pgbouncer
# this plugin expects you to configure pgbouncer.ini, and to set up the
# %include directives

# further, this plugin requires that the handyrep user, DB and password be set
# up on pgbouncer as a valid connection string.

# configuration:
'''
    [[multi_pgbouncer_bigip]]
        pgbouncerbin = "/usr/sbin/pgbouncer"
        dblist_template = pgbouncer_dblist.ini.template
        owner = postgres
        config_location = "/etc/pgbouncer/pgbouncer.ini"
        dblist_location = "/etc/pgbouncer/db_cluster1.ini"
        database_list = postgres, libdata, pgbench
        readonly_suffix = _ro
        all_replicas = False
        extra_connect_param =
'''

from plugins.handyrepplugin import HandyRepPlugin

class multi_pgbouncer_bigip(HandyRepPlugin):

    def run(self, newmaster=None):
        # used for failover of all pgbouncer servers
        if newmaster:
            master = newmaster
        else:
            master = self.get_master_name()
        blist = self.bouncer_list()
        faillist = []
        disablelist = []
        for bserv in blist:
            bpush = self.push_config(bserv, master)
            if self.failed(bpush):
                self.set_bouncer_status(bserv, "unavailable", 4, "unable to reconfigure pgbouncer server for failover")
                # bad bouncer, better disable it at BigIP
                if failed(self.disable_bouncer(bserv)):
                    faillist.append(bserv)
                else:
                    disablelist.append(bserv)

        if faillist:
            # report failure if we couldn't reconfigure any of the servers
            return self.rd(False, "some pgbouncer servers did not change their configuration at failover, and could not be removed from bigip: %s" % ','.join(faillist))
        elif disablelist:
            if ( len(disablelist) + len(faillist) ) == len(blist):
                return self.rd(False, "all pgbouncers not responding and disabled")
            else:
                return self.rd(True, "some pgbouncers failed over, but others had to be disabled in BigIP: %s" % ','.join(disablelist))
        else:
            return self.rd(True, "pgbouncer failover successful")

    def init(self, bouncerserver=None):
        # used to initialize proxy servers with the correct connections
        # either for just the supplied bouncer server, or for all of them
        if bouncerserver:
            blist = [bouncerserver,]
        else:
            blist = self.bouncer_list()

        master = self.get_master_name()
        faillist = []
        for bserv in blist:
            bpush = self.push_config(bserv, master)
            # if we can't push a config, then add this bouncer server to the list
            # of failed servers and mark it unavailable
            if self.failed(bpush):
                self.set_bouncer_status(bserv, "unavailable", 4, "unable to reconfigure pgbouncer server for failover")
                faillist.append(bserv)
            else:
                try:
                    pgbcn = self.connection(bserv)
                except:
                    self.set_bouncer_status(bserv, "unavailable", 4, "pgbouncer configured, but does not accept connections")
                    faillist.append(bserv)
                else:
                    pgbcn.close()
                    self.set_bouncer_status(bserv, "healthy", 1, "pgbouncer initialized")

        if faillist:
            # report failure if we couldn't reconfigure any of the servers
            return self.rd(False, "some pgbouncer servers could not be initialized: %s" % ','.join(faillist))
        else:
            return self.rd(True, "pgbouncer initialization successful")
        

    def set_bouncer_status(self, bouncerserver, status, status_no, status_message):
        self.servers[bouncerserver]["status"] = status
        self.servers[bouncerserver]["status_no"] = status_no
        self.servers[bouncerserver]["status_message"] = status_message
        self.servers[bouncerserver]["status_ts"] = self.now_string()
        return

    def push_config(self, bouncerserver, newmaster=None):
        # pushes a new config to the named pgbouncer server
        # and restarts it
        if newmaster:
            master = newmaster
        else:
            master = self.get_master_name()
        # get configuration
        dbsect = { "dbsection" : self.dbconnect_list(master) }
        # push new config
        myconf = self.get_myconf()
        writeconf = self.push_template(bouncerserver,myconf["dblist_template"],myconf["dblist_location"],dbsect,myconf["owner"])
        if self.failed(writeconf):
            return self.rd(False, "could not push new pgbouncer configuration to pgbouncer server")
        # restart pgbouncer
        restart_command = "%s -u %s -d -R %s" % (myconf["pgbouncerbin"],myconf["owner"],myconf["config_location"],)
        rsbouncer = self.run_as_root(bouncerserver,[restart_command,])
        if self.succeeded(rsbouncer):
            return self.rd(True, "pgbouncer configuration updated")
        else:
            return self.rd(False, "unable to restart pgbouncer")

    def bouncer_list(self):
        # gets a list of currently enabled pgbouncers
        blist = []
        for serv, servdeets in self.servers.iteritems():
            if servdeets["role"] == "pgbouncer" and servdeets["enabled"]:
                blist.append(serv)

        return blist


    def test(self):
        #check that we have all config variables required
        if self.failed( self.test_plugin_conf("multi_pgbouncer_bigip","pgbouncerbin","dblist_template","owner","config_location","dblist_location", "database_list","readonly_suffix","all_replicas","bigip_user","tmsh_path")):
            return self.rd(False, "multi-pgbouncer-bigip failover is not configured" )
        #check that we can connect to the pgbouncer servers
        blist = self.bouncer_list()
        if len(blist) == 0:
            return self.rd(False, "No pgbouncer servers defined")
        
        faillist = []
        for bserv in blist:
            if self.failed(self.run_as_root(bserv,self.conf["handyrep"]["test_ssh_command"])):
                faillist.append(bserv + ' SSH failed')

            if not "ip_address" in self.servers[bserv]:
                faillist.append(bserv + ' no IP address')
            else:
                if not self.servers[bserv]["ip_address"]:
                    faillist.append(bserv + ' no IP address')

        if failist:
            return self.rd(False, "some pgbouncer servers are incorrectly configured: %s" % ','.join(faillist))

        if not self.get_bigip():
            return self.rd(False, "BigIP server is not configured")
        
        return self.rd(True, "pgbouncer setup is correct")


    def get_bigip(self):
        # checkfor bigip server
        isbig = None
        for serv, servdeets in self.servers.iteritems():
            if servdeets["role"] == "bigip" and servdeets["enabled"]:
                isbig = serv

        return isbig

    def poll(self, bouncerserver=None):
        if bouncerserver:
            blist = [bouncerserver,]
        else:
            blist = self.bouncer_list()

        if len(blist) == 0:
            return self.rd(False, "No pgbouncer servers defined")

        faillist = []
        for bserv in blist:
            try:
                pgbcn = self.connection(bserv)
            except:
                self.set_bouncer_status(bserv, "unavailable", 4, "pgbouncer does not accept connections")
                faillist.append(bserv)
            else:
                pgbcn.close()
                self.set_bouncer_status(bserv, "healthy", 1, "pgbouncer responding")
                
        if faillist:
            # report failure if any previously enabled bouncers are down
            return self.rd(False, "some pgbouncer servers are not responding: %s" % ','.join(faillist))
        else:
            return self.rd(True, "all pgbouncers responding")

    def dbconnect_list(self, master):
        # creates the list of database aliases and target
        # servers for pgbouncer
        # build master string first
        myconf = self.get_myconf()
        dblist = myconf["database_list"]
        # add in the handyrep db if the user has forgotten it
        if self.conf["handyrep"]["handyrep_db"] not in dblist:
            dblist.append(self.conf["handyrep"]["handyrep_db"])
        constr = self.dbconnect_line(dblist, self.servers[master]["hostname"], self.servers[master]["port"], "", myconf["extra_connect_param"])
        replicas = self.sorted_replicas()
        if self.is_true(myconf["all_replicas"]):
            #if we're doing all replicas, we need to put them in as _ro0, _ro1, etc.
            # if there's no replicas, set ro1 to go to the master:
            if len(replicas) == 0 or (len(replicas) == 1 and master in replicas):
                rsuff = "%s%d" % (myconf["readonly_suffix"],1,)
                constr += self.dbconnect_line(myconf["database_list"], self.servers[master]["hostname"], self.servers[master]["port"], rsuff, myconf["extra_connect_param"])
            else:
                for rep in replicas:
                    if not rep == master:
                        rsuff = "%s%d" % (myconf["readonly_suffix"],repno,)
                        constr += self.dbconnect_line(myconf["database_list"], self.servers[rep]["hostname"], self.servers[rep]["port"], rsuff, myconf["extra_connect_param"])
                        repno += 1
        else:
            # only one readonly replica, setting it up with _ro
            if len(replicas) > 0:
                if replicas[0] == master:
                    # avoid the master
                    replicas.pop(0)
                    
            if len(replicas) > 0:
                constr += self.dbconnect_line(myconf["database_list"], self.servers[replicas[0]]["hostname"], self.servers[replicas[0]]["port"], myconf["readonly_suffix"], myconf["extra_connect_param"])
            else:
                # if no replicas, read-only connections should go to the master
                constr += self.dbconnect_line(myconf["database_list"], self.servers[master]["hostname"], self.servers[master]["port"], myconf["readonly_suffix"], myconf["extra_connect_param"])

        return constr

    def dbconnect_line(self, database_list, hostname, portno, suffix, extra):
        confout = ""
        if extra:
            nex = extra
        else:
            nex = ""
        for dbname in database_list:
            confout += "%s%s = dbname=%s host=%s port=%s %s \n" % (dbname, suffix, dbname, hostname, portno, nex,)

        return confout

    def disable_bouncer(self, bouncername):
        # calls BigIP via ssh to disable one or more pgbouncers
        # if that pgbouncer isn't responding during a failover
        myconf = self.conf["plugins"]["multi_pgbouncer_bigip"]
        disablecmd = "%s modify ltm node %s state user-down" % (myconf["tmsh_path"], self.servers[bouncername]["ip_address"],)
        bigserv = self.get_bigip()
        sshpasswd = self.get_conf("passwords","bigip_password")
        if bigserv:
            disableit = self.sudorun(bouncername,bigserv, [disablecmd,], myconf["bigip_user"], sshpass=sshpasswd)
            if self.succeeded(disableit):
                return self.rd(True, "bouncer %s disabled" % bouncername)
            else:
                return self.rd(False, "bouncer %s could not be disabled" % bouncername)
        else:
            return self.rd(False, "bouncer %s could not be disabled because bigip is not configured" % bouncername)
    
########NEW FILE########
__FILENAME__ = multi_pgbouncer_pacemaker
# plugin method for failing over connections
# using pgbouncer
# rewrites the list of databases

# plugin for users running multiple pgbouncer servers
# requires that each pgbouncer server be in the servers dictionary
# as role "pgbouncer" and enabled.

# this plugin is for users who have pgbouncer configured to be managed by
# Linux pacemaker.  In such a configuration, HandyRep should NOT restart
# pgbouncer if it's down, so we check up status before restarting.
# we also assume that if pgbouncer is down, it's supposed to be down

# further, this plugin requires that the handyrep user, DB and password be set
# up on pgbouncer as a valid connection string.

from plugins.handyrepplugin import HandyRepPlugin

class multi_pgbouncer_pacemaker(HandyRepPlugin):

    def run(self, newmaster=None):
        # used for failover of all pgbouncer servers
        if newmaster:
            master = newmaster
        else:
            master = self.get_master_name()
        blist = self.bouncer_list()
        faillist = []
        for bserv in blist:
            bpush = self.push_config(bserv, master)
            if self.failed(bpush):
                self.set_bouncer_status(bserv, "unavilable", 4, "unable to reconfigure pgbouncer server for failover")
                faillist.append(bserv)
        
        if faillist:
            # report failure if we couldn't reconfigure any of the servers
            return self.rd(False, "some pgbouncer servers did not change their configuration at failover: %s" % ','.join(faillist))
        else:
            return self.rd(True, "pgbouncer failover successful")

    def init(self, bouncerserver=None):
        # used to initialize proxy servers with the correct connections
        # either for just the supplied bouncer server, or for all of them
        if bouncerserver:
            blist = [bouncerserver,]
        else:
            blist = self.bouncer_list()

        master = self.get_master_name()
        faillist = []
        for bserv in blist:
            bpush = self.push_config(bserv, master)
            # if we can't push a config, then add this bouncer server to the list
            # of failed servers and mark it unavailable
            if self.failed(bpush):
                self.set_bouncer_status(bserv, "unavailable", 4, "unable to reconfigure pgbouncer server for failover")
                faillist.append(bserv)

        if faillist:
            # report failure if we couldn't reconfigure any of the servers
            return self.rd(False, "some pgbouncer servers could not be initialized: %s" % ','.join(faillist))
        else:
            return self.rd(True, "pgbouncer initialization successful")
        

    def set_bouncer_status(self, bouncerserver, status, status_no, status_message):
        self.servers[bouncerserver]["status"] = status
        self.servers[bouncerserver]["status_no"] = status_no
        self.servers[bouncerserver]["status_message"] = status_message
        self.servers[bouncerserver]["status_ts"] = self.now_string()
        return

    def push_config(self, bouncerserver, newmaster=None):
        # pushes a new config to the named pgbouncer server
        # and restarts it
        if newmaster:
            master = newmaster
        else:
            master = self.get_master_name()
        # get configuration
        dbsect = { "dbsection" : self.dbconnect_list(master), "port" : self.servers[bouncerserver]["port"] }
        # push new config
        myconf = self.get_myconf()
        writeconf = self.push_template(bouncerserver,myconf["template"],myconf["config_location"],dbsect,myconf["owner"])
        if self.failed(writeconf):
            return self.rd(False, "could not push new pgbouncer configuration to pgbouncer server")
        # restart pgbouncer
        restart = self.restart_if_running(bouncerserver)
        return restart

    def bouncer_list(self):
        # gets a list of currently enabled pgbouncers
        blist = []
        for serv, servdeets in self.servers.iteritems():
            if servdeets["role"] == "pgbouncer" and servdeets["enabled"]:
                blist.append(serv)

        return blist

    def restart_if_running(self, bouncerserver):
        # restarts a bouncer only if it was already running
        # also updates status
        myconf = self.get_myconf()
        try:
            pgbcn = self.connection(bouncerserver)
        except:
            self.set_bouncer_status(bouncerserver, "down", 5, "this pgbouncer server is down")
            return self.rd(True, "Bouncer not running so not restarted")

        pgbcn.close()
        self.set_bouncer_status(bouncerserver, "healthy", 1, "pgbouncer responding")

        restart_command = "%s -u %s -d -R %s" % (myconf["pgbouncerbin"],myconf["owner"],myconf["config_location"],)
        rsbouncer = self.run_as_root(bouncerserver,[restart_command,])
        if self.succeeded(rsbouncer):
            return self.rd(True, "pgbouncer configuration updated")
        else:
            return self.rd(False, "unable to restart pgbouncer")

    def test(self):
        #check that we have all config variables required
        if self.failed( self.test_plugin_conf("multi_pgbouncer_pacemaker","pgbouncerbin","template","owner","config_location","database_list","readonly_suffix","all_replicas")):
            return self.rd(False, "multi-pgbouncer failover is not configured" )
        #check that we can connect to the pgbouncer servers
        blist = self.bouncer_list()
        if len(blist) == 0:
            return self.rd(False, "No pgbouncer servers defined")
        
        faillist = []
        for bserv in blist:
            if self.failed(self.run_as_root(bserv,[self.conf["handyrep"]["test_ssh_command"],])):
                faillist.append(bserv)

        if faillist:
            return self.rd(False, "cannot SSH to some pgbouncer servers: %s" % ','.join(faillist))
        
        return self.rd(True, "pgbouncer setup is correct")
    

    def poll(self, bouncerserver=None):
        if bouncerserver:
            blist = [bouncerserver,]
        else:
            blist = self.bouncer_list()

        if len(blist) == 0:
            return self.rd(False, "No pgbouncer servers defined")

        faillist = []
        for bserv in blist:
            try:
                pgbcn = self.connection(bserv)
            except:
                self.set_bouncer_status(bserv, "down", 5, "pgbouncer not accepting connections")
                faillist.append(bserv)
            else:
                pgbcn.close()
                self.set_bouncer_status(bserv, "healthy", 1, "pgbouncer responding")
                
        if faillist:
            # check that at least one bouncer is up
            if len(faillist) >= len(blist):
                self.log("PROXY","All pgbouncer servers are down", True)
                return self.rd(False, "All pgbouncers are down")
            else:
                return self.rd(True, "One pgbouncer is responding")
        else:
            return self.rd(True, "all pgbouncers responding")

    def dbconnect_list(self, master):
        # creates the list of database aliases and target
        # servers for pgbouncer
        # build master string first
        myconf = self.get_myconf()
        dblist = myconf["database_list"]
        # add in the handyrep db if the user has forgotten it
        if self.conf["handyrep"]["handyrep_db"] not in dblist:
            dblist.append(self.conf["handyrep"]["handyrep_db"])
        constr = self.dbconnect_line(dblist, self.servers[master]["hostname"], self.servers[master]["port"], "", myconf["extra_connect_param"])
        replicas = self.sorted_replicas()
        if self.is_true(myconf["all_replicas"]):
            #if we're doing all replicas, we need to put them in as _ro0, _ro1, etc.
            # if there's no replicas, set ro1 to go to the master:
            if len(replicas) == 0 or (len(replicas) == 1 and master in replicas):
                rsuff = "%s%d" % (myconf["readonly_suffix"],1,)
                constr += self.dbconnect_line(myconf["database_list"], self.servers[master]["hostname"], self.servers[master]["port"], rsuff, myconf["extra_connect_param"])
            else:
                for rep in replicas:
                    if not rep == master:
                        rsuff = "%s%d" % (myconf["readonly_suffix"],repno,)
                        constr += self.dbconnect_line(myconf["database_list"], self.servers[rep]["hostname"], self.servers[rep]["port"], rsuff, myconf["extra_connect_param"])
                        repno += 1
        else:
            # only one readonly replica, setting it up with _ro
            if len(replicas) > 0:
                if replicas[0] == master:
                    # avoid the master
                    replicas.pop(0)
                    
            if len(replicas) > 0:
                constr += self.dbconnect_line(myconf["database_list"], self.servers[replicas[0]]["hostname"], self.servers[replicas[0]]["port"], myconf["readonly_suffix"], myconf["extra_connect_param"])
            else:
                # if no replicas, read-only connections should go to the master
                constr += self.dbconnect_line(myconf["database_list"], self.servers[master]["hostname"], self.servers[master]["port"], myconf["readonly_suffix"], myconf["extra_connect_param"])

        return constr


    def dbconnect_line(self, database_list, hostname, portno, suffix, extra):
        confout = ""
        if extra:
            nex = extra
        else:
            nex = ""
        for dbname in database_list:
            confout += "%s%s = dbname=%s host=%s port=%s %s \n" % (dbname, suffix, dbname, hostname, portno, nex,)

        return confout

    
########NEW FILE########
__FILENAME__ = one_hr_master
# simplest handyrep master selector: makes the assumption
# that there is only one handyrep server in the system
# and always returns True

from plugins.handyrepplugin import HandyRepPlugin

class one_hr_master(HandyRepPlugin):

    def run(self, params=None):
        return self.rd( True, "only one HR server", {"is_master" : True} )

    def test(self, params=None):
        return self.rd( True, "", {"is_master" : True} )
########NEW FILE########
__FILENAME__ = poll_connect
# plugin method for polling servers for uptime
# using a connection attempt to the database
# used for postgresql versions before 9.3.
# somewhat unreliable because we can't tell why
# we couldn't connect.
# for 9.3 and later use poll_isready instead

# does do repeated polling per fail_retries, since we need to do different
# kinds of polling in different plugins

from plugins.handyrepplugin import HandyRepPlugin

class poll_connect(HandyRepPlugin):

    def run(self, servername):
        retries = self.conf["failover"]["fail_retries"] + 1
        for i in range(1, retries):
            try:
                conn = self.connection(servername)
            except:
                pass
            else:
                conn.close()
                return self.rd(True, "poll succeeded")

        return(False, "could not connect to server in %d tries" % retries)
        
    def test(self):
        # checks that we can connect to the master
        # will fail if we can't, so this isn't a terribly good test
        # since it might just be that the master is down
        master = self.get_master_name()
        if not master:
            return self.rd(False, "master not configured, aborting")
        try:
            conn = self.connection(master)
        except:
            return self.rd(False, "unable to connect to master for polling")
        else:
            conn.close()
            return self.rd(True, "poll succeeded")
########NEW FILE########
__FILENAME__ = poll_isready
# plugin method for polling servers for uptime
# using 9.3's pg_isready utility.  requires PostgreSQL 9.3
# to be installed on the Handyrep server

# does do repeated polling per fail_retries, since we need to do different
# kinds of polling in different plugins

from plugins.handyrepplugin import HandyRepPlugin

class poll_isready(HandyRepPlugin):

    def get_pollcmd(self, servername):
        cmd = self.pluginconf("isready_path")
        serv = self.servers[servername]
        if not cmd:
            cmd = "pg_isready"
        return '%s -h %s -p %s -q' % (cmd, serv["hostname"], serv["port"],)

    def run(self, servername):
        pollcmd = self.get_pollcmd(servername)
        runit = self.run_local([pollcmd,])
        # did we have invalid parameters?
        if self.succeeded(runit):
            if runit["return_code"] in [0,1,]:
                return self.rd(True, "poll succeeded", {"return_code" : runit["return_code"]})
            elif runit["return_code"] == 3 or runit["return_code"] is None:
                return self.rd(False, "invalid configuration for pg_isready", {"return_code" : runit["return_code"]})
            else:
                # got some other kind of failure, let's poll some more
                # we poll for fail_retries tries, with waits of fail_retry_interval
                retries = self.conf["failover"]["fail_retries"]
                for i in range(1,retries):
                    self.failwait()
                    runit = self.run_local([pollcmd,])
                    if self.succeeded(runit):
                        if runit["return_code"] in [0,1,]:
                            return self.rd(True, "poll self.succeeded", {"return_code" : runit["return_code"]})

                # if we've gotten here, then all polls have self.failed
                return self.rd(False, "polling self.failed after %d tries" % retries)
        else:
            return self.rd(False, "invalid configuration for pg_isready", {"return_code" : None })
        
    def test(self):
        # just checks that we can run the poll command, not the result
        # find the master server, make sure we can poll it
        master = self.get_master_name()
        if not master:
            return self.rd(False, "master not configured, aborting")
        pollcmd = self.get_pollcmd(master)
        runit = self.run_local([pollcmd,])
        if self.succeeded(runit) or runit["return_code"] in [0,1,2]:
            return self.rd(True, "polling works")
        else:
            return self.rd(False, "invalid configuration for pg_isready")
########NEW FILE########
__FILENAME__ = promote_pg_ctl
# plugin method for promoting a replica
# by running "pg_ctl promote" on the remote server
# does not do follow-up checks on promotion; those are
# done by the calling code

from plugins.handyrepplugin import HandyRepPlugin

class promote_pg_ctl(HandyRepPlugin):

    def get_pg_ctl_cmd(self, servername, runmode):
        cmd = self.get_conf("plugins", "promote_pg_ctl","pg_ctl_path")
        dbloc = self.servers[servername]["pgconf"]
        extra = self.get_conf("plugins", "promote_pg_ctl","pg_ctl_flags")
        if not cmd:
            cmd = "pg_ctl"
        return "%s -D %s %s %s" % (cmd, dbloc, extra, runmode,)

    def run(self, servername):
        startcmd = self.get_pg_ctl_cmd(servername, "promote")
        runit = self.run_as_postgres(servername, [startcmd,])
        return runit
        
    def test(self, servername):
        startcmd = self.get_pg_ctl_cmd(servername, "status")
        runit = self.run_as_postgres(servername, [startcmd,])
        return runit
########NEW FILE########
__FILENAME__ = push_email_alert_simple
# simple plugin for emailing
# push alerts to one specific email address

from plugins.handyrepplugin import HandyRepPlugin

import smtplib

from email.mime.text import MIMEText

class push_email_alert_simple(HandyRepPlugin):

    def run(self, alert_type, category, message):
        myconf = get_myconf()
        clustname = self.conf["handyrep"]["cluster_name"]

    msgtext = "HandyRep Server Alert:

Cluster: %s

Category: %s

Message: %s""" % (clustname, category, message,)

    msg = MIMEText(msgtext)
    if myconf["subject"]:
        subjtag = myconf["subject"]
    else:
        subjtag = "[HandyRepAlert]"

    msg["Subject"] = "%s: %s %s %s" % (subjtag, clustname, alert_type, category,)
    msg["From"] = myconf["email_from"]
    msg["To"] = myconf["email_to"]

    if self.is_true(myconf["use_ssl"]):
        sendit = smtplib.SMTP_SSL()
    else:
        sendit = smtplib.SMTP()

    if myconf["smtpport"]:
        smport = self.as_int(myconf["smtpport"])
    else:
        smport = 26

    try:
        sendit.connect(myconf["smtpserver"], smport)
    except:
        self.log("ALERT","Unable to connect to mail server",True)
        return self.rd(False, "Cannot connect to mail server")
    
    if myconf["smtpserver"] <> "localhost":
        try:
            sendit.ehlo()

            if self.is_true(myconf["use_tls"]):
                sendit.starttls()
                sendit.ehlo()

            sendit.login(myconf["username"], myconf["smtp_pass"])
        except:
            sendit.quit()
            self.log("ALERT","Unable to log in to mail server",True)
            return self.rd(False, "Cannot log in to mail server")

    try:
        sendit.sendmail(efrom, [eto,], msg.as_string())
        sendit.quit()
    except:
        self.log("ALERT","Cannot send mail via mail server",True)
        return self.rd(False, "Cannot send mail via mail server")

    return self.rd(True, "Alert mail sent")


    def test(self):
        # check for required configuration
        if self.failed(self.test_plugin_conf("push_email_alert_simple","email_to", "email_from", "smtpserver")):
            return self.rd(False, "plugin push_email_alert_simple is not correctly configured")
        else:
            return self.rd(True, "plugin passes")
########NEW FILE########
__FILENAME__ = replication_mb_lag_93
# plugin which checks replication status
# and estimated MB of data lagged for each replica
# based on pg_stat_replication from PostgreSQL 9.3;
# may work with other versions, or not

# returns: success == ran successfully
# replication : am I replcating or not?
# lag : how much lag do I have?

from plugins.handyrepplugin import HandyRepPlugin

class replication_mb_lag_93(HandyRepPlugin):

    def run(self, replicaserver):
        master = self.get_master_name()
        if not master:
            return self.rd(False, "master not configured")
        else:
            try:
                mconn = self.connection(master)
            except:
                return self.rd(False, "could not connect to master")

        mcur = mconn.cursor()
        replag = self.get_one_val(mcur, """SELECT pg_xlog_location_diff(sent_location, replay_location)/(1024^2)
        FROM pg_stat_replication
        WHERE application_name = %s""", [replicaserver,])
        if replag is not None:
            self.servers[replicaserver]["lag"] = replag
            return self.rd(True, "server is replicatting", { "replicating" : True, "lag" : replag })
        else:
            return self.rd(True, "server %s is not currently in replication", { "replicating" : False, "lag" : 0 })

    def test(self, replicaserver):
        # test is the same as run
        return self.run(replicaserver)

########NEW FILE########
__FILENAME__ = restart_pg_ctl
# plugin method for start/stop/restart/reload of a postgresql
# server using pg_ctl and the data directory
# also works as a template plugin example

from plugins.handyrepplugin import HandyRepPlugin

class restart_pg_ctl(HandyRepPlugin):

    def run(self, servername, runmode):
        if runmode == "start":
            return self.start(servername)
        elif runmode == "stop":
            return self.stop(servername)
        elif runmode == "faststop":
            return self.stop(servername, True)
        elif runmode == "restart":
            return self.restart(servername)
        elif runmode == "reload":
            return self.reloadpg(servername)
        elif runmode == "status":
            return self.status(servername)
        else:
            return self.rd( False, "unsupported restart mode %s" % runmode )

    def test(self, servername):
        try:
            res = self.status(servername)
        except:
            return self.rd( False, "test of pg_ctl on server %s failed" % servername)
        else:
            return self.rd( True, "test of pg_ctl on server %s passed" % servername)

    def get_pg_ctl_cmd(self, servername, runmode):
        cmd = self.get_conf("plugins", "restart_pg_ctl","pg_ctl_path")
        dbloc = self.servers[servername]["pgconf"]
        extra = self.get_conf("plugins", "restart_pg_ctl","pg_ctl_flags")
        dbdata = self.servers[servername]["pgdata"]
        if not cmd:
            cmd = "pg_ctl"
        return "%s -D %s %s -l %s/startup.log -w -t 20 %s" % (cmd, dbloc, extra, dbdata, runmode,)

    def start(self, servername):
        startcmd = self.get_pg_ctl_cmd(servername, "start")
        runit = self.run_as_postgres(servername, [startcmd,])
        return runit

    def stop(self, servername):
        startcmd = self.get_pg_ctl_cmd(servername, "-m fast stop")
        runit = self.run_as_postgres(servername, [startcmd,])
        return runit

    def faststop(self, servername):
        startcmd = self.get_pg_ctl_cmd(servername, "-m immediate stop")
        runit = self.run_as_postgres(servername, [startcmd,])
        return runit

    def restart(self, servername):
        startcmd = self.get_pg_ctl_cmd(servername, "-m fast restart")
        runit = self.run_as_postgres(servername, [startcmd,])
        return runit
        
    def reloadpg(self, servername):
        startcmd = self.get_pg_ctl_cmd(servername, "reload")
        runit = self.run_as_postgres(servername, [startcmd,])
        return runit

    def status(self, servername):
        startcmd = self.get_pg_ctl_cmd(servername, "status")
        runit = self.run_as_postgres(servername, [startcmd,])
        return runit
########NEW FILE########
__FILENAME__ = restart_service
# plugin method for start/stop/restart/reload of a postgresql
# server using service and the data directory
# also works as a template plugin example

from plugins.handyrepplugin import HandyRepPlugin

class restart_service(HandyRepPlugin):

    def run(self, servername, runmode):
        if runmode == "start":
            return self.start(servername)
        elif runmode == "stop":
            return self.stop(servername)
        # there's no real faststop method with services
        elif runmode == "faststop":
            return self.stop(servername)
        elif runmode == "restart":
            return self.restart(servername)
        elif runmode == "reload":
            return self.reloadpg(servername)
        elif runmode == "status":
            return self.status(servername)
        else:
            return self.rd( False, "unsupported restart mode %s" % runmode )

    def test(self, servername):
        try:
            res = self.status(servername)
        except:
            return self.rd( False, "test of service control on server %s failed" % servername)
        else:
            return self.rd( True, "test of service control on server %s passed" % servername)


    def get_service_cmd(self, servername, runmode):
        myconf = self.get_myconf()
        if myconf["service_name"]:
            return "service %s %s" % (myconf["service_name"], runmode,)
        else:
            return "service postgresql %s" % (runmode,)

    def start(self, servername):
        startcmd = self.get_service_cmd(servername, "start")
        runit = self.run_as_root(servername, [startcmd,])
        return runit

    def stop(self, servername):
        startcmd = self.get_service_cmd(servername, "stop")
        runit = self.run_as_root(servername, [startcmd,])
        return runit

    def restart(self, servername):
        startcmd = self.get_service_cmd(servername, "restart")
        runit = self.run_as_root(servername, [startcmd,])
        return runit
        
    def reloadpg(self, servername):
        startcmd = self.get_service_cmd(servername, "reload")
        runit = self.run_as_root(servername, [startcmd,])
        return runit

    def status(self, servername):
        startcmd = self.get_service_cmd(servername, "status")
        runit = self.run_as_root(servername, [startcmd,])
        return runit
########NEW FILE########
__FILENAME__ = select_replica_furthest_ahead
# plugin to select a new replica based receive position
# for each replica, with a maximum threshold of replay
# lag.
# requires PostgreSQL 9.2 or later.

from plugins.handyrepplugin import HandyRepPlugin

class select_replica_furthest_ahead(HandyRepPlugin):

    def run(self):
        # assemble a list of servers, and get their
        # current position and lag information
        self.sortsrv = {}
        myconf = self.get_myconf()
        for serv, servdeets in self.servers.iteritems():
            if servdeets["enabled"] and servdeets["status_no"] in ( 1, 2 ) and servdeets["role"] == "replica":
                # get lag and receive position
                repconn = connection(serv)
                repcur = repconn.cursor()
                reppos = self.get_one_row(repcur, """SELECT pg_xlog_location_diff(
                        pg_current_xlog_location(), '0/0000000'),
                        pg_xlog_location_diff(
                        pg_last_xlog_receive_location(),
                        pg_last_xlog_replay_location()
                        )/1000000""")
                repconn.close()
                if reppos[1] <= float(myconf["max_replay_lag"]):
                    self.sortsrv[serv] = { "position" : reppos,
                        "lagged" : 0 }
                else:
                    self.sortsrv[serv] = { "position" : reppos,
                        "lagged" : 1 }
        sortedreps = sorted(self.sortsrv, key=self.servsort, reverse=True)
        return sortedreps

    def servsort(self, key):
        return self.sortsrv[key]["status_sort"], self.sortsrv[key]["priority"]

    def test(self):
        if self.failed(self.test_plugin_conf("select_replica_priority","max_replay_lag"):
            return self.rd( False, "select_replica_futhest_ahead is not configured correctly" )
        else:
            return self.rd( True, "select_replica_furthest_ahead passes" )

########NEW FILE########
__FILENAME__ = select_replica_priority
# plugin to select a new replica based on the "priority"
# assigned by users in the server definitions
# as with all replica selection, it returns a LIST
# of replicas
# sorts replicas first by status ( healthy then lagged)
# then sorts them by priority

from plugins.handyrepplugin import HandyRepPlugin

class select_replica_priority(HandyRepPlugin):

    def run(self):
        # assemble a list of servers, their status
        # numbers and priorities
        self.sortsrv = {}
        for serv, servdeets in self.servers.iteritems():
            if servdeets["enabled"] and servdeets["status_no"] in ( 1, 2 ) and servdeets["role"] == "replica":
                self.sortsrv[serv] = { "priority" : servdeets["failover_priority"],
                    "status_sort" : servdeets["status_no"] }

        sortedreps = sorted(self.sortsrv, key=self.servsort)
        return sortedreps

    def servsort(self, key):
        return self.sortsrv[key]["status_sort"], self.sortsrv[key]["priority"]

    def test(self):
        return self.rd( True, "sort by priority always succeeds" )

########NEW FILE########
__FILENAME__ = simple_password_auth
# simple authentication using just the two
# passwords saved in the "passwords" section of handyrep.conf
# defines a read-only vs. admin role
# ignores the username

from plugins.handyrepplugin import HandyRepPlugin

class simple_password_auth(HandyRepPlugin):

    def run(self, username, userpass, funcname):

        myconf = self.get_myconf()
        # get list of readonly functions, if any
        rofunclist = myconf["ro_function_list"]

        # try admin password
        if userpass == self.conf["passwords"]["admin_password"]:
            return self.rd(True, "password accepted")
        elif userpass == self.conf["passwords"]["read_password"]:
            if funcname in rofunclist:
                return self.rd(True, "password accepted")
            else:
                return self.rd(False, "That feature requires admin access")
        else:
            return self.rd(False, "password rejected")

    def test(self):
        if self.failed(self.test_plugin_conf("simple_password_auth","ro_function_list")):
            return self.rd(False, "plugin simple_password_auth is not correctly configured")
        else:
            if self.get_conf("passwords","admin_password") and self.get_conf("passwords","read_password"):
                return self.rd(True, "plugin passes")
            else:
                return self.rd(False, "passwords not set for simple_password_auth")


########NEW FILE########
__FILENAME__ = successplugin
# generic success plugin
# designed to substitute for a real plugin when
# we don't care about the result, we always want
# to return success
# accepts and ignores args and kwargs so that we can
# swap it in for real plugins

from plugins.handyrepplugin import HandyRepPlugin

class successplugin(HandyRepPlugin):

    def run(self, *args, **kwargs):
        return self.rd( True, "success plugin always succeeds" )

    def test(self, *args, **kwargs):
        return self.rd( True, "success plugin always succeeds" )

########NEW FILE########
__FILENAME__ = zero_auth
# authentication plugin for zero authentication
# setups.  always succeeds

from plugins.handyrepplugin import HandyRepPlugin

class zero_auth(HandyRepPlugin):

    def run(self, username, userpass, funcname):
        return self.rd( True, "authenticated" )

    def test(self):
        return self.rd( True, "tested" )

########NEW FILE########
__FILENAME__ = config
__author__ = 'kaceymiriholston'

import os

basedir = os.path.abspath(os.path.dirname(__file__))

CSRF_ENABLED = True
SECRET_KEY = 'GUI-secret-key-597621139'
########NEW FILE########
__FILENAME__ = Dictionary
__author__ = 'kaceymiriholston'

Functions = {
    'get_status': {'function_name': 'get_status','description': 'Returns all status information for the cluster.', 'short_description': 'Cluster status information',
        'params': [{'param_name': 'check_type', 'param_default': 'cached',
        'param_description': "allows you to specify that the server is to poll or fully verify all servers before "
                             "returning status information.", 'param_type': 'choice', 'required': False,
        'param_options': [{ 'option_name': 'poll', 'description': 'Specify that the server is to poll all servers before returning status information.'},
         {'option_name': 'cached', 'description': "Just return information from HandyRep's last check."},
         {'option_name': 'verify', 'description': 'Specify that the server is to fully verify all servers before returning status information.'}]}],
        'result_information': '<p>This function returns status at two levels: for the cluster as a whole, and for each individual '
                           'server. In both cases, status information consists of four fields:</p><h4>status</h4>'
                           '<p style="padding-left:2em">one of "unknown","healthy","lagged","warning","unavailable", or "down". see below '
                           'for explanation of these statuses.</p><h4>status_no</h4><p style="padding-left:2em">status number corresponding to above, '
                           'for creating alert thresholds.</p><h4>status_ts</h4><p style="padding-left:2em">the last timestamp when status '
                           'was checked, in unix standard format</p><h4>status_message</h4><p style="padding-left:2em">a message about the '
                           'last issue found which causes a change in status. May not be complete or representative.</p>'
                           '<h4>The individual servers also contain their name(hostname), their role(role) and if they are enabled'
                           '(enabled).</h4><h3>Status meaning</h3><h3 style="padding-left:1em">Cluster Status Data</h3>'
                           '<h4 style="padding-left:1.3em">0: "unknown"</h4><p style="padding-left:2em">status checks have not been run. This status '
                           'should only exist for a very short time.</p><h4 style="padding-left:1.3em">1 : "healthy"</h4><p style="padding-left:2em">cluster has a viable master, and all replicas are "healthy" or "lagged" '
                           '</p><h4 style="padding-left:1.3em">3 : "warning"</h4><p style="padding-left:2em">cluster has a viable master, but has one or more issues, including connnection problems, failure to fail over, or downed replicas.'
                           '</p><h4 style="padding-left:1.3em">5 : "down"</h4><p style="padding-left:2em">cluster has no working master, or is in an indeterminate state and requires administrator intervention'
                           '</p><h3 style="padding-left:1em">Individual Servers Status Data</h3>'
                           '<h4 style="padding-left:1.3em">0: "unknown"</h4><p style="padding-left:2em">server has not been checked yet.'
                           '</p><h4 style="padding-left:1.3em">1 : "healthy"</h4><p style="padding-left:2em">server is operating normally'
                           '</p><h4 style="padding-left:1.3em">2 : "lagged"</h4><p style="padding-left:2em">for replicas, indicates that the replica is running but has exceeded the configured lag threshold.'
                           '</p><h4 style="padding-left:1.3em">3 : "warning"</h4><p style="padding-left:2em">server is operating, but has one or more issues, such as inability to ssh, or out-of-connections.'
                           '</p><h4 style="padding-left:1.3em">4 : "unavailable"</h4><p style="padding-left:2em">cannot determine status of server because we cannot connect to it.'
                           '</p><h4 style="padding-left:1.3em">5 : "down"</h4><p style="padding-left:2em">.server is verified down'
                           '</p>'},

    'get_cluster_status':{ 'function_name': 'get_cluster_status','description': 'Returns the cluster status fields for the cluster. ',
        'short_description': 'Cluster status fields', 'params': [{'param_name': 'verify', 'param_default': False,
        'param_description': "A true value will verify all cluster data, a false value will just return cached data.", 'param_type': 'bool',
        'required': False,'param_options': None}],
        'result_information': '<p>This function returns status for the cluster as a whole. Status information consists of four fields:</p><h4>status</h4>'
                           '<p style="padding-left:2em">one of "unknown","healthy","lagged","warning","unavailable", or "down". see below '
                           'for explanation of these statuses.</p><h4>status_no</h4><p style="padding-left:2em">status number corresponding to above, '
                           'for creating alert thresholds.</p><h4>status_ts</h4><p style="padding-left:2em">the last timestamp when status '
                           'was checked, in unix standard format</p><h4>status_message</h4><p style="padding-left:2em">a message about the '
                           'last issue found which causes a change in status. May not be complete or representative.</p>'
                           '<h4>The individual servers also contain their name(hostname), their role(role) and if they are enabled'
                           '(enabled).</h4><h3>Status meaning</h3><h3 style="padding-left:1em">Cluster Status Data</h3>'
                           '<h4 style="padding-left:1.3em">0: "unknown"</h4><p style="padding-left:2em">status checks have not been run. This status '
                           'should only exist for a very short time.</p><h4 style="padding-left:1.3em">1 : "healthy"</h4><p style="padding-left:2em">cluster has a viable master, and all replicas are "healthy" or "lagged" '
                           '</p><h4 style="padding-left:1.3em">3 : "warning"</h4><p style="padding-left:2em">cluster has a viable master, but has one or more issues, including connnection problems, failure to fail over, or downed replicas.'
                           '</p><h4 style="padding-left:1.3em">5 : "down"</h4><p style="padding-left:2em">cluster has no working master, or is in an indeterminate state and requires administrator intervention'
                           '</p>'},

    'get_master_name': {'function_name': 'get_master_name','description': 'Returns the name of the current master.',
        'short_description': 'Current master\'s name', 'params': None, 'result_information': 'This function returns the name of the '
                    'current master. If there is no configured master, or the master has been disabled, it will return "None".'},

    'get_server_info':{'function_name': 'get_server_info', 'description': 'Returns server configuration and status details for the named server(s).',
        'short_description': 'Configuration & Status detail', 'params': [{'param_name': 'servername', 'param_default': 'None','param_description': 'The server whose data to return. If None, '
       'or blank, return all servers.', 'param_type': 'text', 'required': False, 'param_options': None},
                {'param_name': 'verify', 'param_default': False, 'param_description': 'A true value will verify all server data, a false value will just return cached data.',
                 'param_type': 'bool', 'required': False, 'param_options': None}], 'result_information': 'This function returns server configuration and status details for this server.'},

    'read_log': {'function_name': 'read_log','description': 'Retrieves the last N lines of the handyrep log and presents them as a list in reverse chonological order.',
        'short_description': 'handyrep log lines', 'params': [{'param_name': 'numlines', 'param_default': None, 'param_description': 'How many lines of the log to retrieve.', 'param_type':'text',
                'required': False, 'param_options': None}], 'result_information': "This function retrieves the last N lines of the handyrep log and presents them as a list in reverse chonological order." },

    'get_setting' :{'function_name': 'get_setting','description': 'Retrieves a single configuration setting. Can not retrieve nested settings.', 'short_description': 'A configuration setting', 'params': [{'param_name': 'category',
                'param_default': None, 'param_description': 'Section of the config the setting is in.', 'param_type':'text', 'required': False,
                'param_options': None},{'param_name': 'setting', 'param_default': None, 'param_description': 'The individual setting name.', 'param_type': 'text',
                'required': True, 'param_options': None}], 'result_information': "This function retrieves a single configuration setting."},

    'set_verbose':{ 'function_name': 'set_verbose','description': 'Toggles verbose logging.', 'short_description': 'Toggles verbose logging', 'params': [{'param_name': 'verbose',
        'param_default': True ,'param_description': 'True for verbose.', 'param_type': 'bool', 'required': False, 'param_options': None}],
                    'result_information': 'This function returns whether the toggle was successful.'},

    'poll_master':{ 'function_name': 'poll_master','description': 'Uses the configured polling method to check the master for availability. '
                    'Updates the status dictionary in the process. Can only determine up/down, and cannot determine if '
                    'the master has issues; as a result, will not change "warning" to "healthy". Also checks that the master '
                    'is actually a master and not a replica.', 'short_description': 'Check master availability', 'params': None,
            'result_information': '<p>This function returns a result, a human readable details line and a return_code linked to the sucess or failure of the function</p>'
                           '<h3>result</h3><h4 style="padding-left:1em">SUCCESS</h4><p style="padding-left:2em">The '
                           'current master is responding to polling.</p><h4 style="padding-left:1em">FAIL</h4><p style="padding-left:2em">The '
                           'current master is not responding to polling, or the handyrep or polling method configuration is wrong.</p>'},

    'poll':{'function_name': 'poll', 'description': 'Uses the configured polling method to check the designated server for '
                    'availability. Updates the status dictionary in the process. Can only determine up/down, and cannot '
                    'determine if the master has issues; as a result, will not change "warning" to "healthy".', 'short_description': 'Check server availability',
            'params': [{'param_name': 'servername', 'param_default': None, 'param_description': 'Server to poll.', 'param_type': 'text', 'required': False,
                 'param_options': None}], 'result_information': '<p>This function returns a result, a human readable details line and a return_code linked to the sucess or failure of the function</p>'
                           '<h3>result</h3><h4 style="padding-left:1em">SUCCESS</h4><p style="padding-left:2em">The '
                           'current master is responding to polling.</p><h4 style="padding-left:1em">FAIL</h4><p style="padding-left:2em">The '
                           'current master is not responding to polling, or the handyrep or polling method configuration is wrong.</p>'},

    'poll_all':{'function_name': 'poll_all', 'description': 'Polls all servers using the configured polling method. Also checks the '
                    'number of currently enabled and running masters and replicas. Updates the status dictionary.',
        'short_description': 'Check all servers availability', 'params': None,
        'result_information': '<p>This function returns information on the cluster and the servers. This information includes the'
                           'failover status, the results in human readable and boolean format and a details, human readable message.</p>'
                           '<h3>result</h3><h4 style="padding-left:1em">SUCCESS</h4><p style="padding-left:2em">The master is running.</p>'
                            '<h4 style="padding-left:1em">FAIL</h4><p style="padding-left:2em">The master is down, or no master is configured, or multiple masters are configured.</p>'
                            '<h4>failover_ok</h4><p style="padding-left:1em">Boolean field indicating whether it is OK to fail over. Basically a check that there is one master and at least one working replica.</p>'},

    'verify_server':{'function_name': 'verify_server', 'description': "Checks that the replica is running and is in replication, or "
                    "Checks the master server to make sure it's fully operating, including checking that we can connect, "
                    "we can write data, and that ssh and control commands are available. Updates the status dictionary.",
            'short_description': 'Verify a server',
            'params': [{'param_name': 'servername', 'param_default': None, 'param_description': 'Server name.', 'param_type': 'text', 'required': False,
                 'param_options': None}], 'result_information': '<p>This function results depends on if you are verifying a master or replica</p>'
                    '<h3>result</h3><h4 style="padding-left:1em">SUCCESS (master)</h4><p style="padding-left:2em">'
                    'The master is verified to be running, although it may have known non-fatal issues.</p>'
                    '<h4 style="padding-left:1em">SUCCESS (replica)</h4><p style="padding-left:2em">'
                    'The replica is verified to be running, although it may have known non-fatal issues.</p>'
                    '<h4 style="padding-left:1em">FAIL (master)</h4><p style="padding-left:2em">'
                    'The master is verified to be not running, unresponsive, or may be blocking data writes.</p>'
                    '<h4 style="padding-left:1em">FAIL (replica)</h4><p style="padding-left:2em">'
                    'The replica is verified to be not running, unresponsive, or may be running but not in replication.</p>'
                    '<h3>ssh (for both)</h3><p style="padding-left:1em">Text field, which, if it exists, shows an error '
                    'message from attempts to connect to the master via ssh.</p><h3>psql (for both)</h3><p style="padding-left:1em">'
                    'Text field which, if it exists, shows an error message from attempts to make a psql connection to the master.</p>'
                    '<h3>details</h3><p style="padding-left:1em"> Human readable message.</p>'},


    'verify_all':{'function_name': 'verify_all', 'description': 'Does complete check of all enabled servers in the server list. '
                    'Updates the status dictionary. Returns detailed check information about each server.',
            'short_description': 'Check all servers', 'params': None,
            'result_information': '<p>This function returns information about the cluster and each server.</p><h3>Cluster Information</h3>'
                           '<h4 style="padding-left:1em">failover_ok</h4><p style="padding-left:2em">'
                    'True means at least one replica is healthy and available for failover.</p>'
                    '<h4 style="padding-left:1em">result</h4><p style="padding-left:2em">'
                    'SUCCESS = the master is up and running. FAIL = the master is not running, or master configuration '
                    'is messed up (no masters, two masters, etc.)</p> <h4 style="padding-left:1em">details</h4><p style="padding-left:2em">'
                    'Human readable statement of what is going on.<h3>Server Information</h3>'
                           '<h4 style="padding-left:1em">psql</h4><p style="padding-left:2em">'
                    'Text field which, if it exists, shows an error message from attempts to make a psql connection to the master</p>'
                    '<h4 style="padding-left:1em">result</h4><p style="padding-left:2em">'
                    'SUCCESS = the master is up and running. FAIL = the master is not running, or master configuration '
                    'is messed up (no masters, two masters, etc.)</p> <h4 style="padding-left:1em">details</h4><p style="padding-left:2em">'
                    'Human readable statement of what is going on.'},

    'init_handyrep_db':{'function_name': 'init_handyrep_db', 'description': 'Creates the initial handyrep schema and table.',
                        'short_description':'Creates schema and table', 'params': None, 'result_information': 'This function returns'
                        'data related to the success of the creation of the schema and table.'
                        '<p>It fails if it cannot connect to the master, or does not have permissions to create schemas and tables, or if the cited database does not exist.</p>'},

    'reload_conf':{'function_name': 'reload_conf', 'description': 'Reload handyrep configuration from the handyrep.conf file. '
                'Allows changing of configuration files.', 'short_description': 'Reload configuration', 'params': [{'param_name': 'config_file', 'param_default': None, 'param_description':
        'File path location of the configuration file. Defaults to "handyrep.conf" in the working directory.', 'param_type': 'text',
        'required': False, 'param_options': None}], 'result_information': 'This function returns'
                        'data related to the success of the creation of the schema and table.'},

    'shutdown':{'function_name': 'shutdown', 'description': 'Shut down the designated server. Checks to make sure that the server '
        'is actually down.', 'short_description': 'Shutdown server', 'params': [{'param_name': 'servername', 'param_default': None,'param_description': 'The name of the server to shut down', 'param_type': 'text',
        'required': True, 'param_options': None}], 'result_information': 'This function returns data related to the success '
        'of the shutdown of the server.<h3>result</h3><h4 style="padding-left:1em">SUCCESS</h4><p style="padding-left:2em">The server is shut down.</p><h4 style="padding-left:1em">FAIL</h4><p style="padding-left:2em">The server will not shut down. check details.</p>'},

     'startup':{'function_name': 'startup', 'description': 'Starts the designated server. Checks to make sure that the server is actually up.',
        'short_description': 'Startup server', 'params': [{'param_name': 'servername', 'param_default': None,'param_description': 'The name of the server to start.', 'param_type': 'text',
        'required': True, 'param_options': None}], 'result_information': 'This function returns data related to the success '
        'of the startup of the server.<h3>result</h3><h4 style="padding-left:1em">SUCCESS</h4><p style="padding-left:2em">The server is running.</p><h4 style="padding-left:1em">FAIL</h4><p style="padding-left:2em">The server will not start, check details.</p>'},

    'restart':{'function_name': 'restart', 'description': 'restarts the designated server. Checks to make sure that the server is actually up.',
     'short_description': 'Restart server', 'params': [{'param_name': 'servername', 'param_default': None,'param_description': 'The name of the server to start.', 'param_type': 'text',
        'required': True, 'param_options': None}], 'result_information': 'This function returns data related to the success '
        'of the restart of the server.<h3>result</h3><h4 style="padding-left:1em">SUCCESS</h4><p style="padding-left:2em">The server is running.</p><h4 style="padding-left:1em">FAIL</h4><p style="padding-left:2em">The server will not restart, check details.</p>'},


    'promote':{'function_name': 'promote', 'description': 'Promotes the designated replica to become a master or standalone. Does '
        'NOT do other failover procedures. Does not prevent creating two masters.', 'short_description': 'Promote replica', 'params': [{'param_name': 'newmaster',
        'param_default': None, 'param_description': 'The name of the server to start.', 'param_type': 'text','required': True, 'param_options': None}],
               'result_information': 'This function returns data related to the success '
        'of the promotion of the server.<h3>result</h3><h4 style="padding-left:1em">SUCCESS</h4><p style="padding-left:2em">The server has been promoted.</p><h4 style="padding-left:1em">FAIL</h4><p style="padding-left:2em">The server could not be promoted, check details.</p>'},

    'manual_failover':{'function_name': 'manual_failover', 'description': 'Fail over to a new master, presumably for planned downtimes, '
        'maintenance, or server migrations.', 'short_description': 'Fail over to new master', 'params': [{'param_name': 'newmaster', 'param_default': None, 'param_description': 'Server to fail '
        'over to. If not supplied, use the same master selection process as auto-failover.', 'param_type': 'text', 'required': False,
        'param_options': None}, {'param_name': 'remaster', 'param_default': None,'param_description': 'Whether or not to remaster '
        'all other servers to replicate from the new master. If not supplied, setting in handyrep.conf is used.', 'param_type': 'bool',
        'required': False, 'param_options': None}], 'result_information': 'This function returns data related to the success '
        'of the failover of the server.<h3>result</h3><h4 style="padding-left:1em">SUCCESS</h4><p style="padding-left:2em">'
        'The server failed over to the new master successfully. Check details in case postfailover commands failed.</p>'
        '<h4 style="padding-left:1em">FAIL</h4><p style="padding-left:2em">The server is unable to fail over to the new '
        'master. Cluster may have been left in an indeterminate state, check details.</p>'},

     'clone':{'function_name': 'clone', 'description': 'Create a clone from the master, and starts it up. Uses the configured '
        'cloning method and plugin.', 'short_description': 'Clone master and Start it', 'params': [{'param_name': 'replicaserver', 'param_default': None,
        'param_description': 'The new replica to clone to.', 'param_type': 'text', 'required': False, 'param_options': None},
        {'param_name': 'reclone', 'param_default': False, 'param_description': 'Whether to clone over an existing replica, if any. '
                'If set to False (the default), clone will abort if this server has an operational PostgreSQL on it.', 'param_type': 'bool',
        'required': False, 'param_options': None},
        {'param_name': 'clonefrom','param_default': 'current master', 'param_description': 'The server to clone from. Defaults to the current master.', 'param_type': 'text',
        'required': False, 'param_options': None}], 'result_information': 'This function returns data related to the success '
        'of the clone of the master.<h3>result</h3><h4 style="padding-left:1em">SUCCESS</h4><p style="padding-left:2em">'
        'The replica was cloned and is running.</p>'
        '<h4 style="padding-left:1em">FAIL</h4><p style="padding-left:2em">Either cloning or starting up the new replica '
        'failed, or you attempted to clone over an existing running server.</p>'},

    'enable':{'function_name': 'enable', 'description': 'Enable a server definition already created. Also verifies the server defintion.',
            'short_description': 'Enable server definition', 'params': [{'param_name': 'servername', 'param_default': None,
            'param_description': 'The server to enable.', 'param_type': 'text', 'required': False,'param_options': None}],
        'result_information': 'This function returns data related to the success of whether the server defination is enabled.'
        '<h3>result</h3><h4 style="padding-left:1em">SUCCESS</h4><p style="padding-left:2em">The server was enabled.</p>'
        '<h4 style="padding-left:1em">FAIL</h4><p style="padding-left:2em">The server definition failed to enable </p>'},

    'disable':{'function_name': 'disable', 'description': 'Mark an existing server disabled so that it is no longer checked. '
        'Also attempts to shut down the indicated server.', 'short_description': 'Disable server for checking', 'params': [{'param_name': 'servername',
        'param_default': None, 'param_description': 'The server to disable.', 'param_type': 'text', 'required': False, 'param_options': None}],
        'result_information': 'This function returns data related to the success of whether the server is disabled.'
        '<h3>result</h3><h4 style="padding-left:1em">SUCCESS</h4><p style="padding-left:2em">The server was disabled.</p>'
        '<h4 style="padding-left:1em">FAIL</h4><p style="padding-left:2em">The server was not disabled </p>'},

    'remove':{'function_name': 'remove', 'description': 'Delete the definition of a disabled server.', 'short_description': 'Delete server definition', 'params':
        [{'param_name': 'servername', 'param_default': None,'param_description': 'The server to disable.', 'param_type': 'text', 'required': False, 'param_options': None}],
              'result_information': 'This function returns data related to the success of whether the server was removed.'
        '<h3>result</h3><h4 style="padding-left:1em">SUCCESS</h4><p style="padding-left:2em">The server definition was deleted.</p>'
        '<h4 style="padding-left:1em">FAIL</h4><p style="padding-left:2em">The server definition is still enabled, so it can\'t be deleted. </p>'},

    'alter_server_def':{'function_name': 'alter_server_def', 'description': 'Change details of a server after initialization. Required '
        'because the .conf file is not considered the canonical information about servers once servers.save has been created.',
        'short_description': 'Change server details', 'params': [{'param_name': 'servername', 'param_default': None, 'param_description': 'The existing server whose details are to be changed.',
        'param_type': 'text', 'required': False,  'param_options': None}, {'param_name': 'serverprops', 'param_default': None, 'param_description': 'a set of '
        'key-value pairs for settings to change. Settings may be "changed" to the existing value, so it is permissible '
        'to pass in an entire dictionary of the server config with one changed setting.', 'param_type': 'text',
        'required': False, 'param_options': None}], 'result_information': 'This function returns data related to the current status of the server after it was altered.'
        '<h3>definition</h3><h4>The resulting new definition for the server.</h4><h3>result</h3><h4 style="padding-left:1em">SUCCESS</h4><p style="padding-left:2em">The server definition was altered.</p>'
        '<h4 style="padding-left:1em">FAIL</h4><p style="padding-left:2em">The server definition failed to change.</p>'},

    'add_server':{'function_name': 'add_server', 'description': 'Add a new server to a running handyrep. Needed because handyrep.conf is not considered the canonical source of server information once handyrep has been started.',
        'short_description': 'Add a server', 'params': [{'param_name': 'servername', 'param_default': None, 'param_description': 'The existing server whose details are to be changed.',
        'param_type': 'text', 'required': False, 'param_options': None}, {'param_name': 'serverprops', 'param_default': None, 'param_description': 'a set of key-value '
        'pairs for settings to change. Settings may be "changed" to the existing value, so it is permissible to pass in '
        'an entire dictionary of the server config with one changed setting.', 'param_type': 'text', 'required': False, 'param_options': None}],
        'result_information': 'This function returns data related to the current status of the server after it was added.'
        '<h3>definition</h3><h4>The resulting new definition for the server.</h4><h3>result</h3><h4 style="padding-left:1em">SUCCESS</h4><p style="padding-left:2em">The server was added.</p>'
        '<h4 style="padding-left:1em">FAIL</h4><p style="padding-left:2em">The server addition failed.</p>'},

    'cleanup_archive':{'function_name': 'cleanup_archive', 'description': 'Delete old WALs from a shared WAL archive, according to the '
        'expiration settings in handyrep.conf. Uses the configured archive deletion plugin.',
        'short_description': 'Delete old WALs', 'params': None, 'result_information': 'This function returns data related to the success of whether the WALs were deleted.'
        '<h3>result</h3><h4 style="padding-left:1em">SUCCESS</h4><p style="padding-left:2em">Archives deleted, or archiving is disabled so no action taken.</p>'
        '<h4 style="padding-left:1em">FAIL</h4><p style="padding-left:2em">Archives could not be deleted, possibly because of a permissions or configuration issue. </p>'},

    'connection_proxy_init':{'function_name': 'connection_proxy_init', 'description': 'Set up the connection proxy configuration according to the '
        'configured connection failover plugin. Not all connection proxy plugins support initialization.', 'short_description': 'Connection proxy config','params': None,
                              'result_information': 'This function returns data related to the success of whether the connection proxy configuration was initialized.'
        '<h3>result</h3><h4 style="padding-left:1em">SUCCESS</h4><p style="padding-left:2em">Proxy configuration pushed, or connection failover is not being used.</p>'
        '<h4 style="padding-left:1em">FAIL</h4><p style="padding-left:2em">Error in pushing new configuration, or proxy does not support initialization. </p>'},

    'start_archiving':{'function_name': 'start_archiving', 'description': "Start archiving on the master. This call will push an archive.sh script and remove any noarchiving file, if defined and present (all of this is via plugin methods). It does not set archiving=on in postgresql.conf, so if archiving has not begun after running this, that's the first thing to check.",
                       'short_description': 'Start archiving on the master.','params': None, 'result_information':'This function returns whether archiving was started successfully.'
                        '<p> <b>SUCCESS</b> means archiving should be enabled.</p><p><b>FAIL</b> means either archving is not configured, or was unable to modify the master.</p>'},

    'stop_archiving': {'function_name': 'stop_archiving', 'description': "Stops copying of WAL files on the master. Implemented via the archving plugin. Most archving plugins implement this via a noarchving touch file. This does mean that if the master's disk is 100% full, it will not work.",
                       'short_description': 'Stops copying of WAL files on the master.','params': None, 'result_information':"This function returns whether archiving was stopped successfully."
                        "<p> <b>SUCCESS</b> means noarchving flag is set, or archiving is otherwise disabled.</p><p><b>FAIL</b> means could not disable archiving, either because it is not configured, or because there's something wrong with the master.</p>"},
}

master = {True:("get_server_info", "poll", "verify_server", "alter_server_def", "disable", "restart", "shutdown"), False:("get_server_info", "alter_server_def", "enable", "clone", "remove")}
replica = {True:("get_server_info", "poll", "verify_server", "alter_server_def", "disable", "restart", "shutdown", "manual_failover", "promote", "clone"), False:("get_server_info", "alter_server_def", "enable", "clone", "remove")}
other = {True:("get_server_info", "alter_server_def", "disable"), False:("get_server_info", "alter_server_def", "enable", "remove")}
cluster_functions = ("get_status", "get_cluster_status", "get_master_name", "read_log", "get_setting", "set_verbose",
"verify_all", "poll_all", "init_handyrep_db", "add_server", "connection_proxy_init", "cleanup_archive", "start_archiving",
"stop_archiving", "reload_conf")
########NEW FILE########
__FILENAME__ = forms
__author__ = 'kaceymiriholston'
from flask.ext.wtf import Form
from wtforms import TextField, BooleanField
from wtforms.validators import Required
import Dictionary

class AddressForm(Form):
    address = TextField('address', validators = [Required()])
    username = TextField('username', validators = [Required()])
    password = TextField('password', validators = [Required()])

class FunctionForm(Form):
    textdata = TextField('textdata')
    true_false = BooleanField(default = False)

class ClusterForm(Form):
    textdata1 = TextField('textdata')
    textdata2 = TextField('textdata')
    true_false = BooleanField(default=False)






########NEW FILE########
__FILENAME__ = views
__author__ = 'kaceymiriholston'
from flask import render_template, redirect, url_for, request, abort, make_response

import requests, json

from GUI_app import app
import Dictionary
from forms import AddressForm, FunctionForm, ClusterForm


global handyrep_address
handyrep_address = None
global username
username = None
global password
password = None
global function_parameters
function_parameters = {}

def get_status():
    url_to_send = "{address}/get_status".format(address=handyrep_address)
    status = requests.get(url_to_send, auth=(username, password)).json()
    return status

def get_server_info(server_name):
    params = {"servername": str(server_name)}
    url_to_send = "{address}/get_server_info".format(address=handyrep_address)
    request= requests.get(url_to_send,params=params, auth=(username,password))
    return request.json()

@app.route('/logout/')
def logout():
    global handyrep_address
    handyrep_address = None
    global username
    username = None
    global password
    password = None
    return redirect('/index')


@app.route('/login/', methods=['GET', 'POST'])
def login():
    form = AddressForm()
    if form.validate_on_submit():
        global handyrep_address
        handyrep_address = form.address.data
        global username
        username = form.username.data
        global password
        password = form.password.data
        url_to_send = "{address}/get_master_name".format(address=handyrep_address)
        try:
            r = requests.get(url_to_send, auth=(username, password))
        except:
            message = "There is something wrong with the address, please try again."
            handyrep_address = None
            username = None
            password = None

            return render_template('login.html', form=form, message=message)
        if r.status_code in range(400, 500):
            if r.status_code == 404:
                return redirect(url_for("page_not_found"))
            message = "Please check username and password"

            return render_template('login.html', form=form, message=message)
        return redirect(request.args.get('next') or '/index')

    return render_template('login.html', form=form)


@app.route('/')
@app.route('/index/')
def index():
    if handyrep_address is None or username is None or password is None:
        return redirect(url_for("login"))
    status = get_status()
    return render_template("index.html", status=status)

@app.route('/server/<server_name>')
def server_actions(server_name):
    if handyrep_address is None or username is None or password is None:
        return redirect(url_for("login"))
    #status information
    status = get_status()
    #server information
    server_info = get_server_info(server_name)
    if server_info.get(server_name)["role"] == "master" or server_info.get(server_name)["role"] == "replica":
        functions = getattr(Dictionary, server_info.get(server_name)["role"])
    else:
        functions = Dictionary.other
    final_functions = sorted(functions.get(server_info.get(server_name)["enabled"]))
    return render_template("server_page.html", status=status, info=server_info, functions=final_functions)

@app.route('/cluster')
def cluster_actions():
    if handyrep_address is None or username is None or password is None:
        return redirect(url_for("login"))
    #status information
    status = get_status()
    #server information
    server_info = None
    final_functions = sorted(Dictionary.cluster_functions)
    return render_template("server_page.html", status=status, info=server_info, functions=final_functions)

@app.route('/server/<server_name>/<function>', methods=['GET', 'POST'])
def function_detail(server_name, function):
    if handyrep_address is None or username is None or password is None:
        return redirect(url_for("login"))
    #status information
    status = get_status()
    #function parameters
    server_info = get_server_info(server_name)
    function_info = Dictionary.Functions.get(function)
    if len(function_info["params"]) > 1:
        form = FunctionForm()
        if form.validate_on_submit():
            for params in function_info["params"]:
                if params["param_name"] == "servername" or params["param_name"] == "replicaserver":
                        continue
                if params["required"] and getattr(form, 'textdata').data == "":
                    message = "Please enter the required field."
                    return render_template("function_data.html", status=status, info=server_info, form=form, function = function_info, message=message)
                if params['param_type'] == 'bool':
                    if not getattr(form, 'true_false').data == params["param_default"] :#Don't want to send blank data:
                        function_parameters[params['param_name']] = getattr(form, 'true_false').data
                elif not getattr(form, 'textdata').data == "":
                    if params["param_default"] and str(getattr(form, 'textdata').raw_data[0]).lower() == params["param_default"].lower() :#Don't want to send blank data:
                        pass
                    else:
                        function_parameters[params['param_name']] = str(getattr(form, 'textdata').raw_data[0])
            return redirect(url_for("results", server_name = server_name, function=function))
        for params in function_info["params"]:
            if params["param_name"] == "servername":
                function_parameters["servername"] = server_name
            elif params["param_name"] == "replicaserver":
                function_parameters["replicaserver"] = server_name
            else:
                if params["param_default"]:
                    if params["param_type"] == "text":
                        if params["param_default"] == "current master":
                            url_to_send = "{address}/get_master_name".format(address=handyrep_address)
                            r = requests.get(url_to_send, auth=(username, password))
                            getattr(form, 'textdata').data = r.json()
                        else:
                            getattr(form, 'textdata').data = params["param_default"]
                    if params["param_type"] == "bool":
                        getattr(form, 'true_false').data = params["param_default"]
    elif len(function_info["params"]) == 1 and (function_info.get("params")[0].get("param_name") == "servername" or function_info.get("params")[0].get("param_name") == "newmaster"):
        if function_info.get("params")[0].get("param_name") == "newmaster":
            function_parameters["newmaster"] = server_name
        else:
            function_parameters["servername"] = server_name
        return redirect(url_for("results", server_name = server_name, function=function))
    return render_template("function_data.html", status=status, info=server_info, form=form, function = function_info)

@app.route('/cluster/<function>', methods=['GET', 'POST'])
def cluster_function_detail(function):
    global function_parameters
    if handyrep_address is None or username is None or password is None:
        return redirect(url_for("login"))
    #status information
    status = get_status()
    #function parameters
    server_info = None
    function_info = Dictionary.Functions[function]
    if not function_info['params']:
        function_parameters = None
        return redirect(url_for("results", server_name="cluster", function=function))
    form = ClusterForm()
    if form.validate_on_submit():
        for index, param in enumerate(function_info["params"]):
            if not param["param_type"] == 'bool':
                if param["required"] and getattr(form, 'textdata%d'%(index+1)).data == "":
                    message = "Please enter the required field."
                    return render_template("cluster_function_data.html", status=status, info=server_info, form=form, function = function_info, message=message)
                if not getattr(form, 'textdata%d' %(index+1)).data == "":
                    if param["param_default"] and str(getattr(form, 'textdata%d' %(index+1)).raw_data[0]).lower() == param["param_default"].lower() :#Don't want to send blank data:
                        pass
                    else:
                        function_parameters[param['param_name']] = str(getattr(form, 'textdata%d'%(index+1)).raw_data[0])
            else:
                if not getattr(form, 'true_false').data == param["param_default"] :#Don't send default data
                    function_parameters[param['param_name']] = getattr(form, 'true_false').data
        return redirect(url_for("results", server_name = "cluster", function=function))

    ##fill in defaults - currently only items with one form field have defaults
    if function_info["params"][0]["param_default"]:
        if function_info["params"][0]["param_type"] == "bool":
            getattr(form, 'true_false').data = function_info["params"][0]["param_default"]
        else:
            getattr(form, 'textdata1').data = function_info["params"][0]["param_default"]
    return render_template("cluster_function_data.html", status=status, info=server_info, form=form, function = function_info)


@app.route("/server/<server_name>/<function>/results/")
def results(server_name, function):
    global function_parameters
    if handyrep_address is None or username is None or password is None:
        function_parameters = {}
        return redirect(url_for("login"))

    print function_parameters
    if server_name == "cluster":
        server_info = None
    else:
        server_info = get_server_info(server_name)

    function_info = Dictionary.Functions.get(function)
    url_to_send = "{address}/{function}".format(address=handyrep_address, function = function)
    if function_parameters is None:
        x = requests.get(url_to_send, auth=(username, password))
    else:
        x = requests.get(url_to_send, params=function_parameters, auth=(username, password))
    if not x.status_code == requests.codes.OK:
        if x.status_code == 500:
            function_parameters = {}
            abort(500)
        result_to_send = "Parameters were not entered correctly. Please renter them. Remember, handyrep is case sensitive."
    else:
        result_to_send = x.json()
        #status information
    status = get_status()
    function_parameters = {}
    return render_template("results.html", status=status, info=server_info, results=function_parameters, result_to_send=result_to_send, function = function_info)




@app.errorhandler(404)
def page_not_found(error):
    return render_template('page_not_found.html'), 404

@app.errorhandler(500)
def app_error(error):
    return render_template('500_error.html'), 500



########NEW FILE########
__FILENAME__ = handyrepGUI

from GUI_app import app
app.run(debug=True)
#app.run(host="0.0.0.0")

########NEW FILE########
