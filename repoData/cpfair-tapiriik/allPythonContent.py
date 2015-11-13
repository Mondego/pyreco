__FILENAME__ = email_cron
from tapiriik.database import db
from tapiriik.web.email import generate_message_from_template, send_email
from tapiriik.services import Service
from tapiriik.settings import WITHDRAWN_SERVICES
from datetime import datetime, timedelta
import os
import math
os.environ["DJANGO_SETTINGS_MODULE"] = "tapiriik.settings"

# Renewal emails
now = datetime.utcnow()
expiry_window_open = now - timedelta(days=28)
expiry_window_close = now
expired_payments = db.payments.find({"Expiry": {"$gt": expiry_window_open, "$lt": expiry_window_close}, "ReminderEmailSent": {"$ne": True}})

for expired_payment in expired_payments:
	connected_user = db.users.find_one({"Payments._id": expired_payment["_id"]})
	print("Composing renewal email for %s" % expired_payment["Email"])
	if not connected_user:
		print("...no associated user")
		continue
	connected_services_names = [Service.FromID(x["Service"]).DisplayName for x in connected_user["ConnectedServices"] if x["Service"] not in WITHDRAWN_SERVICES]

	if len(connected_services_names) == 0:
		connected_services_names = ["fitness tracking"]
	elif len(connected_services_names) == 1:
		connected_services_names.append("other fitness tracking")
	if len(connected_services_names) > 1:
		connected_services_names = ", ".join(connected_services_names[:-1]) + " and " + connected_services_names[-1] + " accounts"
	else:
		connected_services_names = connected_services_names[0] + " accounts"

	subscription_days = round((expired_payment["Expiry"] - expired_payment["Timestamp"]).total_seconds() / (60 * 60 * 24))
	subscription_fuzzy_time_map = {
		(0, 8): "few days",
		(8, 31): "few weeks",
		(31, 150): "few months",
		(150, 300): "half a year",
		(300, 999): "year"
	}
	subscription_fuzzy_time = [v for k,v in subscription_fuzzy_time_map.items() if k[0] <= subscription_days and k[1] > subscription_days][0]

	activity_records = db.activity_records.find_one({"UserID": connected_user["_id"]})
	total_distance_synced = None
	if activity_records:
		total_distance_synced = sum([x["Distance"] for x in activity_records["Activities"] if x["Distance"]])
		total_distance_synced = math.floor(total_distance_synced/1000 / 100) * 100

	context = {
		"account_list": connected_services_names,
		"subscription_days": subscription_days,
		"subscription_fuzzy_time": subscription_fuzzy_time,
		"distance": total_distance_synced
	}
	message, plaintext_message = generate_message_from_template("email/payment_renew.html", context)
	send_email(expired_payment["Email"], "tapiriik automatic synchronization expiry", message, plaintext_message=plaintext_message)
	db.payments.update({"_id": expired_payment["_id"]}, {"$set": {"ReminderEmailSent": True}})
	print("...sent")

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tapiriik.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = runtests
import tapiriik.database
tapiriik.database.db = tapiriik.database._connection["tapiriik_test"]
tapiriik.database.cachedb = tapiriik.database._connection["tapiriik_cache_test"]

from tapiriik.testing import *
import unittest
unittest.main()

tapiriik.database._connection.drop_database("tapiriik_test")
tapiriik.database._connection.drop_database("tapiriik_cache_test")

########NEW FILE########
__FILENAME__ = stats_cron
from tapiriik.database import db
from datetime import datetime, timedelta

# total distance synced
distanceSyncedAggr = db.sync_stats.aggregate([{"$group": {"_id": None, "total": {"$sum": "$Distance"}}}])["result"]
if distanceSyncedAggr:
    distanceSynced = distanceSyncedAggr[0]["total"]
else:
    distanceSynced = 0

# last 24hr, for rate calculation
lastDayDistanceSyncedAggr = db.sync_stats.aggregate([{"$match": {"Timestamp": {"$gt": datetime.utcnow() - timedelta(hours=24)}}}, {"$group": {"_id": None, "total": {"$sum": "$Distance"}}}])["result"]
if lastDayDistanceSyncedAggr:
    lastDayDistanceSynced = lastDayDistanceSyncedAggr[0]["total"]
else:
    lastDayDistanceSynced = 0

# similarly, last 1hr
lastHourDistanceSyncedAggr = db.sync_stats.aggregate([{"$match": {"Timestamp": {"$gt": datetime.utcnow() - timedelta(hours=1)}}}, {"$group": {"_id": None, "total": {"$sum": "$Distance"}}}])["result"]
if lastHourDistanceSyncedAggr:
    lastHourDistanceSynced = lastHourDistanceSyncedAggr[0]["total"]
else:
    lastHourDistanceSynced = 0
# sync wait time, to save making 1 query/sec-user-browser
queueHead = list(db.users.find({"NextSynchronization": {"$lte": datetime.utcnow()}, "SynchronizationWorker": None, "SynchronizationHostRestriction": {"$exists": False}}, {"NextSynchronization": 1}).sort("NextSynchronization").limit(10))
queueHeadTime = timedelta(0)
if len(queueHead):
    for queuedUser in queueHead:
        queueHeadTime += datetime.utcnow() - queuedUser["NextSynchronization"]
    queueHeadTime /= len(queueHead)

# sync time utilization
db.sync_worker_stats.remove({"Timestamp": {"$lt": datetime.utcnow() - timedelta(hours=1)}})  # clean up old records
timeUsedAgg = db.sync_worker_stats.aggregate([{"$group": {"_id": None, "total": {"$sum": "$TimeTaken"}}}])["result"]
totalSyncOps = db.sync_worker_stats.count()
if timeUsedAgg:
    timeUsed = timeUsedAgg[0]["total"]
    avgSyncTime = timeUsed / totalSyncOps
else:
    timeUsed = 0
    avgSyncTime = 0

# error/pending/locked stats
lockedSyncRecords = db.users.aggregate([
                                       {"$match": {"SynchronizationWorker": {"$ne": None}}},
                                       {"$group": {"_id": None, "count": {"$sum": 1}}}
                                       ])
if len(lockedSyncRecords["result"]) > 0:
    lockedSyncRecords = lockedSyncRecords["result"][0]["count"]
else:
    lockedSyncRecords = 0

pendingSynchronizations = db.users.aggregate([
                                             {"$match": {"NextSynchronization": {"$lt": datetime.utcnow()}}},
                                             {"$group": {"_id": None, "count": {"$sum": 1}}}
                                             ])
if len(pendingSynchronizations["result"]) > 0:
    pendingSynchronizations = pendingSynchronizations["result"][0]["count"]
else:
    pendingSynchronizations = 0

usersWithErrors = db.users.aggregate([
                                     {"$match": {"NonblockingSyncErrorCount": {"$gt": 0}}},
                                     {"$group": {"_id": None, "count": {"$sum": 1}}}
                                     ])
if len(usersWithErrors["result"]) > 0:
    usersWithErrors = usersWithErrors["result"][0]["count"]
else:
    usersWithErrors = 0


totalErrors = db.users.aggregate([
   {"$group": {"_id": None,
               "total": {"$sum": "$NonblockingSyncErrorCount"}}}
])

if len(totalErrors["result"]) > 0:
    totalErrors = totalErrors["result"][0]["total"]
else:
    totalErrors = 0

db.sync_status_stats.insert({
        "Timestamp": datetime.utcnow(),
        "Locked": lockedSyncRecords,
        "Pending": pendingSynchronizations,
        "ErrorUsers": usersWithErrors,
        "TotalErrors": totalErrors,
        "SyncTimeUsed": timeUsed,
        "SyncQueueHeadTime": queueHeadTime.total_seconds()
})

db.stats.update({}, {"$set": {"TotalDistanceSynced": distanceSynced, "LastDayDistanceSynced": lastDayDistanceSynced, "LastHourDistanceSynced": lastHourDistanceSynced, "TotalSyncTimeUsed": timeUsed, "AverageSyncDuration": avgSyncTime, "LastHourSynchronizationCount": totalSyncOps, "QueueHeadTime": queueHeadTime.total_seconds(), "Updated": datetime.utcnow()}}, upsert=True)


def aggregateCommonErrors():
    from bson.code import Code
    # The exception message always appears right before "LOCALS:"
    map_operation = Code(
        "function(){"
            "var errorMatch = new RegExp(/\\n([^\\n]+)\\n\\nLOCALS:/);"
            "if (!this.SyncErrors) return;"
            "var id = this._id;"
            "this.SyncErrors.forEach(function(error){"
                "var message = error.Message.match(errorMatch)[1];"
                "emit(message.substring(0, 60),{count:1, connections:[id], exemplar:message});"
            "});"
        "}"
        )
    reduce_operation = Code(
        "function(key, item){"
            "var reduced = {count:0, connections:[]};"
            "var connection_collections = [];"
            "item.forEach(function(error){"
                "reduced.count+=error.count;"
                "reduced.exemplar = error.exemplar;"
                "connection_collections.push(error.connections);"
            "});"
            "reduced.connections = reduced.connections.concat.apply(reduced.connections, connection_collections);"
            "return reduced;"
        "}")
    db.connections.map_reduce(map_operation, reduce_operation, "common_sync_errors") #, finalize=finalize_operation
    # We don't need to do anything with the result right now, just leave it there to appear in the dashboard

aggregateCommonErrors()

########NEW FILE########
__FILENAME__ = sync_cpulimit
import os
import time
import subprocess

cpulimit_procs = {}
worker_cpu_limit = int(os.environ.get("TAPIRIIK_WORKER_CPU_LIMIT", 4))

while True:
    active_pids = [pid for pid in os.listdir('/proc') if pid.isdigit()] # Sorry, operating systems without procfs
    for pid in active_pids:
        try:
            proc_cmd = open("/proc/%s/cmdline" % pid, "r").read()
        except IOError:
            continue
        else:
            if "sync_worker.py" in proc_cmd:
                if pid not in cpulimit_procs or cpulimit_procs[pid].poll():
                    cpulimit_procs[pid] = subprocess.Popen(["cpulimit", "-l", str(worker_cpu_limit), "-p", pid])

    for k in list(cpulimit_procs.keys()):
        if cpulimit_procs[k].poll():
            cpulimit_procs[k].wait()
            del cpulimit_procs[k]

    time.sleep(1)

########NEW FILE########
__FILENAME__ = sync_poll_triggers
from tapiriik.database import db
from tapiriik.requests_lib import patch_requests_source_address
from tapiriik.settings import RABBITMQ_BROKER_URL, MONGO_HOST
from tapiriik import settings
from datetime import datetime

if isinstance(settings.HTTP_SOURCE_ADDR, list):
    settings.HTTP_SOURCE_ADDR = settings.HTTP_SOURCE_ADDR[0]
    patch_requests_source_address((settings.HTTP_SOURCE_ADDR, 0))

from tapiriik.services import Service
from celery import Celery
from datetime import datetime

class _celeryConfig:
	CELERY_ROUTES = {
		"sync_poll_triggers.trigger_poll": {"queue": "tapiriik-poll"}
	}
	CELERYD_CONCURRENCY = 1 # Otherwise the GC rate limiting breaks since file locking is per-process.

celery_app = Celery('sync_poll_triggers', broker=RABBITMQ_BROKER_URL)
celery_app.config_from_object(_celeryConfig())

@celery_app.task()
def trigger_poll(service_id, index):
    svc = Service.FromID(service_id)
    affected_connection_external_ids = svc.PollPartialSyncTrigger(index)
    print("Triggering %d connections via %s-%d" % (len(affected_connection_external_ids), service_id, index))
    db.connections.update({"Service": service_id, "ExternalID": {"$in": affected_connection_external_ids}}, {"$set":{"TriggerPartialSync": True, "TriggerPartialSyncTimestamp": datetime.utcnow()}}, multi=True)
    db.poll_stats.insert({"Service": service_id, "Index": index, "Timestamp": datetime.utcnow(), "TriggerCount": len(affected_connection_external_ids)})

def schedule_trigger_poll():
	schedule_data = list(db.trigger_poll_scheduling.find())
	print("Scheduler run at %s" % datetime.now())
	for svc in Service.List():
		if svc.PartialSyncTriggerRequiresPolling:
			print("Checking %s's %d poll indexes" % (svc.ID, svc.PartialSyncTriggerPollMultiple))
			for idx in range(svc.PartialSyncTriggerPollMultiple):
				svc_schedule = [x for x in schedule_data if x["Service"] == svc.ID and x["Index"] == idx]
				if not svc_schedule:
					svc_schedule = {"Service": svc.ID, "Index": idx, "LastScheduled": datetime.min}
				else:
					svc_schedule = svc_schedule[0]

				if datetime.utcnow() - svc_schedule["LastScheduled"] > svc.PartialSyncTriggerPollInterval:
					svc_schedule["LastScheduled"] = datetime.utcnow()
					trigger_poll.apply_async(args=[svc.ID, idx], expires=svc.PartialSyncTriggerPollInterval.total_seconds(), time_limit=svc.PartialSyncTriggerPollInterval.total_seconds())
					db.trigger_poll_scheduling.update({"Service": svc.ID, "Index": idx}, svc_schedule, upsert=True)

if __name__ == "__main__":
	schedule_trigger_poll()
########NEW FILE########
__FILENAME__ = sync_watchdog
from tapiriik.database import db
from tapiriik.sync import SyncStep
import os
import signal
import socket
from datetime import timedelta, datetime

print("Sync watchdog run at %s" % datetime.now())

host = socket.gethostname()

for worker in db.sync_workers.find({"Host": host}):
    # Does the process still exist?
    alive = True
    try:
        os.kill(worker["Process"], 0)
    except os.error:
        print("%s is no longer alive" % worker)
        alive = False

    # Has it been stalled for too long?
    if worker["State"] == SyncStep.List:
        timeout = timedelta(minutes=45)  # This can take a loooooooong time
    else:
        timeout = timedelta(minutes=10)  # But everything else shouldn't

    if alive and worker["Heartbeat"] < datetime.utcnow() - timeout:
        print("%s timed out" % worker)
        os.kill(worker["Process"], signal.SIGKILL)
        alive = False

    # Clear it from the database if it's not alive.
    if not alive:
        db.sync_workers.remove({"_id": worker["_id"]})
        # Unlock users attached to it.
        for user in db.users.find({"SynchronizationWorker": worker["Process"], "SynchronizationHost": host}):
            print("\t Unlocking %s" % user["_id"])
        db.users.update({"SynchronizationWorker": worker["Process"], "SynchronizationHost": host}, {"$unset":{"SynchronizationWorker": True}}, multi=True)

########NEW FILE########
__FILENAME__ = sync_worker
from tapiriik.requests_lib import patch_requests_with_default_timeout, patch_requests_source_address
from tapiriik import settings
from tapiriik.database import db
import time
from datetime import datetime, timedelta
import os
import signal
import sys
import subprocess
import socket

Run = True
RecycleInterval = 1 # Time spent rebooting workers < time spent wrangling Python memory management.
NoQueueMinCycleTime = timedelta(seconds=30) # No need to hammer the database given the number of sync workers I have

oldCwd = os.getcwd()
WorkerVersion = subprocess.Popen(["git", "rev-parse", "HEAD"], stdout=subprocess.PIPE, cwd=os.path.dirname(__file__)).communicate()[0].strip()
os.chdir(oldCwd)

def sync_interrupt(signal, frame):
    global Run
    Run = False

signal.signal(signal.SIGINT, sync_interrupt)
signal.signal(signal.SIGUSR2, sync_interrupt)

def sync_heartbeat(state):
    db.sync_workers.update({"Process": os.getpid(), "Host": socket.gethostname()}, {"$set": {"Heartbeat": datetime.utcnow(), "State": state}})

print("Sync worker starting at " + datetime.now().ctime() + " \n -> PID " + str(os.getpid()))
db.sync_workers.update({"Process": os.getpid(), "Host": socket.gethostname()}, {"Process": os.getpid(), "Heartbeat": datetime.utcnow(), "Startup":  datetime.utcnow(),  "Version": WorkerVersion, "Host": socket.gethostname(), "Index": settings.WORKER_INDEX, "State": "startup"}, upsert=True)
sys.stdout.flush()

patch_requests_with_default_timeout(timeout=60)

if isinstance(settings.HTTP_SOURCE_ADDR, list):
    settings.HTTP_SOURCE_ADDR = settings.HTTP_SOURCE_ADDR[settings.WORKER_INDEX % len(settings.HTTP_SOURCE_ADDR)]
    patch_requests_source_address((settings.HTTP_SOURCE_ADDR, 0))

print(" -> Index %s\n -> Interface %s" % (settings.WORKER_INDEX, settings.HTTP_SOURCE_ADDR))

# We defer including the main body of the application till here so the settings aren't captured before we've set them up.
# The better way would be to defer initializing services until they're requested, but it's 10:30 and this will work just as well.
from tapiriik.sync import Sync

while Run:
    cycleStart = datetime.utcnow() # Avoid having synchronization fall down during DST setback
    processed_user_count = Sync.PerformGlobalSync(heartbeat_callback=sync_heartbeat, version=WorkerVersion)
    RecycleInterval -= processed_user_count
    # When there's no queue, all the workers sit sending 1000s of the queries to the database server
    if processed_user_count == 0:
        # Put this before the recycle shutdown, otherwise it'll quit and get rebooted ASAP
        remaining_cycle_time = NoQueueMinCycleTime - (datetime.utcnow() - cycleStart)
        if remaining_cycle_time > timedelta(0):
            print("Pausing for %ss" % remaining_cycle_time.total_seconds())
            sync_heartbeat("idle-spin")
            time.sleep(remaining_cycle_time.total_seconds())
    if RecycleInterval <= 0:
    	break
    sync_heartbeat("idle")

print("Sync worker shutting down cleanly")
db.sync_workers.remove({"Process": os.getpid(), "Host": socket.gethostname()})
sys.stdout.flush()

########NEW FILE########
__FILENAME__ = credential_storage
from Crypto.Cipher import AES
from Crypto import Random
import hashlib
from tapiriik.settings import CREDENTIAL_STORAGE_KEY

#### note about tapiriik and credential storage ####
# Some services require a username and password for every action - so they need to be stored in recoverable form
# (namely: Garmin Connect's current "API")
# I've done my best to mitigate the risk that these credentials ever be compromised, but the risk can never be eliminated
# If you're not comfortable with it, you can opt to not have your credentials stored, instead entering them on every sync

class CredentialStore:
    def GenerateIV():
        return Random.new().read(AES.block_size)

    def Encrypt(cred):
        iv = CredentialStore.GenerateIV();
        cipher = AES.new(CREDENTIAL_STORAGE_KEY, AES.MODE_CFB, iv)
        data = cipher.encrypt(cred.encode("UTF-8"))
        return [iv, data]

    def Decrypt(data):
        iv = data[0]
        data = data[1]
        cipher = AES.new(CREDENTIAL_STORAGE_KEY, AES.MODE_CFB, iv)
        cred = cipher.decrypt(data).decode("UTF-8")
        return cred

########NEW FILE########
__FILENAME__ = payment
from datetime import datetime, timedelta
from tapiriik.database import db
from tapiriik.settings import PAYMENT_AMOUNT, PAYMENT_SYNC_DAYS
from bson.objectid import ObjectId

class Payments:
    def LogPayment(id, amount, initialAssociatedAccount, email):
        # pro-rate their expiry date
        expires_in_days = min(PAYMENT_SYNC_DAYS, float(amount) / float(PAYMENT_AMOUNT) * float(PAYMENT_SYNC_DAYS))
        # would use upsert, except that would reset the timestamp value
        existingRecord = db.payments.find_one({"Txn": id})
        if existingRecord is None:
            existingRecord = {
                "Txn": id,
                "Timestamp": datetime.utcnow(),
                "Expiry": datetime.utcnow() + timedelta(days=expires_in_days),
                "Amount": amount,
                "InitialAssociatedAccount": initialAssociatedAccount,
                "Email": email
            }
            db.payments.insert(existingRecord)
        return existingRecord

    def GetPayment(id=None, email=None):
        if id:
            return db.payments.find_one({"Txn": id})
        elif email:
            res = db.payments.find({"Email": email, "Expiry":{"$gt": datetime.utcnow()}}, limit=1)
            for payment in res:
                return payment

    def GenerateClaimCode(user, payment):
        db.payments_claim.remove({"Txn": payment["Txn"]})  # Remove any old codes, just to reduce the number kicking around at any one time.
        return str(db.payments_claim.insert({"Txn": payment["Txn"], "User": user["_id"], "Timestamp": datetime.utcnow()}))  # Return is the new _id, aka the claim code.

    def HasOutstandingClaimCode(user):
        return db.payments_claim.find_one({"User": user["_id"]}) is not None

    def ConsumeClaimCode(code):
        claim = db.payments_claim.find_one({"_id": ObjectId(code)})
        if not claim:
            return (None, None)
        db.payments_claim.remove(claim)
        return (db.users.find_one({"_id": claim["User"]}), db.payments.find_one({"Txn": claim["Txn"]}))


########NEW FILE########
__FILENAME__ = totp
import time
import base64
import math
import hmac
import hashlib
import struct


class TOTP:
    def Get(secret):
        counter = struct.pack(">Q", int(time.time() / 30))
        key = base64.b32decode(secret.upper().encode())
        csp = hmac.new(key, counter, hashlib.sha1)
        res = csp.digest()
        offset = res[19] & 0xf
        code_pre = struct.unpack(">I", res[offset:offset + 4])[0]
        code_pre = code_pre & 0x7fffffff
        return int(code_pre % (math.pow(10, 6)))

########NEW FILE########
__FILENAME__ = tz
from tapiriik.database import tzdb
from bson.son import SON

def TZLookup(lat, lng):
	pt = [lng, lat]
	res = tzdb.boundaries.find_one({"Boundary": {"$geoIntersects": {"$geometry": {"type":"Point", "coordinates": pt}}}}, {"TZID": True})
	if not res:
		res = tzdb.boundaries.find_one({"Boundary": SON([("$near", {"$geometry": {"type": "Point", "coordinates": pt}}), ("$maxDistance", 200000)])}, {"TZID": True})
	res = res["TZID"] if res else None
	if not res or res == "uninhabited":
		res = round(lng / 15)
	return res

########NEW FILE########
__FILENAME__ = requests_lib
# For whatever reason there's no built-in way to specify a global timeout for requests operations.
# socket.setdefaulttimeout doesn't work since requests overriddes the default with its own default.
# There's probably a better way to do this in requests 2.x, but...

def patch_requests_with_default_timeout(timeout):
	import requests
	old_request = requests.Session.request
	def new_request(*args, **kwargs):
		if "timeout" not in kwargs:
			kwargs["timeout"] = timeout
		return old_request(*args, **kwargs)
	requests.Session.request = new_request

def patch_requests_no_verify_ssl():
	import requests
	old_request = requests.Session.request
	def new_request(*args, **kwargs):
		kwargs.update({"verify": False})
		return old_request(*args, **kwargs)
	requests.Session.request = new_request

# Not really patching requests here, but...
def patch_requests_source_address(new_source_address):
	import socket
	old_create_connection = socket.create_connection
	def new_create_connection(address, timeout=None, source_address=None):
		if address[1] in [80, 443]:
			return old_create_connection(address, timeout, new_source_address)
		else:
			return old_create_connection(address, timeout, source_address)
	socket.create_connection = new_create_connection

def patch_requests_user_agent(user_agent):
	import requests
	old_request = requests.Session.request
	def new_request(*args, **kwargs):
		headers = kwargs.get("headers",{})
		headers["User-Agent"] = user_agent
		kwargs["headers"] = headers
		return old_request(*args, **kwargs)
	requests.Session.request = new_request

########NEW FILE########
__FILENAME__ = api
class ServiceExceptionScope:
    Account = "account"
    Service = "service"

class ServiceException(Exception):
    def __init__(self, message, scope=ServiceExceptionScope.Service, block=False, user_exception=None):
        Exception.__init__(self, message)
        self.Message = message
        self.UserException = user_exception
        self.Block = block
        self.Scope = scope

    def __str__(self):
        return self.Message + " (user " + str(self.UserException) + " )"

class ServiceWarning(ServiceException):
    pass

class APIException(ServiceException):
    pass

class APIWarning(ServiceWarning):
    pass

# Theoretically, APIExcludeActivity should actually be a ServiceException with block=True, scope=Activity
# It's on the to-do list.

class APIExcludeActivity(Exception):
    def __init__(self, message, activity=None, activityId=None, permanent=True, userException=None):
        Exception.__init__(self, message)
        self.Message = message
        self.Activity = activity
        self.ExternalActivityID = activityId
        self.Permanent = permanent
        self.UserException = userException

    def __str__(self):
        return self.Message + " (activity " + str(self.ExternalActivityID) + ")"

class UserExceptionType:
    # Account-level exceptions (not a hardcoded thing, just to keep these seperate)
    Authorization = "auth"
    AccountFull = "full"
    AccountExpired = "expired"
    AccountUnpaid = "unpaid" # vs. expired, which implies it was at some point function, via payment or trial or otherwise.

    # Activity-level exceptions
    FlowException = "flow"
    Private = "private"
    NotTriggered = "notrigger"
    MissingCredentials = "credentials_missing" # They forgot to check the "Remember these details" box
    NotConfigured = "config_missing" # Don't think this error is even possible any more.
    StationaryUnsupported = "stationary"
    NonGPSUnsupported = "nongps"
    TypeUnsupported = "type_unsupported"
    DownloadError = "download"
    ListingError = "list" # Cases when a service fails listing, so nothing can be uploaded to it.
    UploadError = "upload"
    SanityError = "sanity"
    Corrupt = "corrupt" # Kind of a scary term for what's generally "some data is missing"
    Untagged = "untagged"
    LiveTracking = "live"
    UnknownTZ = "tz_unknown"
    System = "system"
    Other = "other"

class UserException:
    def __init__(self, type, extra=None, intervention_required=False, clear_group=None):
        self.Type = type
        self.Extra = extra # Unimplemented - displayed as part of the error message.
        self.InterventionRequired = intervention_required # Does the user need to dismiss this error?
        self.ClearGroup = clear_group if clear_group else type # Used to group error messages displayed to the user, and let them clear a group that share a common cause.

########NEW FILE########
__FILENAME__ = devices
class DeviceIdentifierType:
	FIT = "fit"
	TCX = "tcx"

class FITDeviceIdentifier:
	def __init__(self, manufacturer, product=None):
		self.Type = DeviceIdentifierType.FIT
		self.Manufacturer = manufacturer
		self.Product = product

class TCXDeviceIdentifier:
	def __init__(self, name, productId=None):
		self.Type = DeviceIdentifierType.TCX
		self.Name = name
		self.ProductID = productId

class DeviceIdentifier:
	_identifierGroups = []

	def AddIdentifierGroup(*identifiers):
		DeviceIdentifier._identifierGroups.append(identifiers)

	def FindMatchingIdentifierOfType(type, query):
		for group in DeviceIdentifier._identifierGroups:
			for identifier in group:
				if identifier.Type != type:
					continue
				compareDict = dict(identifier.__dict__)
				compareDict.update(query)
				if compareDict == identifier.__dict__: # At the time it felt like a better idea than iterating through keys?
					return identifier

	def FindEquivalentIdentifierOfType(type, identifier):
		if not identifier:
			return
		if identifier.Type == type:
			return identifier # We preemptively do this, so international variants have a chance of being preserved
		for group in DeviceIdentifier._identifierGroups:
			if identifier not in group:
				continue
			for altIdentifier in group:
				if altIdentifier.Type == type:
					return altIdentifier

class Device:
	def __init__(self, identifier, serial=None, verMaj=None, verMin=None):
		self.Identifier = identifier
		self.Serial = serial
		self.VersionMajor = verMaj
		self.VersionMinor = verMin


# I think Garmin devices' TCX ProductID match their FIT garmin_product id
# And, since the FIT SDK is lagging behind:
#  - Forerunner 620 is 1623

def _garminIdentifier(name, *fitIds):
	return [TCXDeviceIdentifier("Garmin %s" % name, fitIds[0])] + [FITDeviceIdentifier(1, fitId) for fitId in fitIds]

# This list is REGEXed from the FIT SDK - I have no clue what some of the entries are...
# Some products have international variants with different FIT IDs - the first ID given is used for TCX
# DeviceIdentifier.AddIdentifierGroup(*_garminIdentifier("HRM1", 1)) - Garmin Connect reports itself as ID 1 too.
DeviceIdentifier.AddIdentifierGroup(*_garminIdentifier("AXH01", 2))
DeviceIdentifier.AddIdentifierGroup(*_garminIdentifier("AXB01", 3))
DeviceIdentifier.AddIdentifierGroup(*_garminIdentifier("AXB02", 4))
DeviceIdentifier.AddIdentifierGroup(*_garminIdentifier("HRM2SS", 5))
DeviceIdentifier.AddIdentifierGroup(*_garminIdentifier("DSI_ALF02", 6))
DeviceIdentifier.AddIdentifierGroup(*_garminIdentifier("Forerunner 301", 473, 474, 475, 494))
DeviceIdentifier.AddIdentifierGroup(*_garminIdentifier("Forerunner 405", 717, 987))
DeviceIdentifier.AddIdentifierGroup(*_garminIdentifier("Forerunner 50", 782))
DeviceIdentifier.AddIdentifierGroup(*_garminIdentifier("Forerunner 60", 988))
DeviceIdentifier.AddIdentifierGroup(*_garminIdentifier("DSI_ALF01", 1011))
DeviceIdentifier.AddIdentifierGroup(*_garminIdentifier("Forerunner 310XT", 1018, 1446))
DeviceIdentifier.AddIdentifierGroup(*_garminIdentifier("Edge 500", 1036, 1199, 1213, 1387, 1422))
DeviceIdentifier.AddIdentifierGroup(*_garminIdentifier("Forerunner 110", 1124, 1274))
DeviceIdentifier.AddIdentifierGroup(*_garminIdentifier("Edge 800", 1169, 1333, 1334, 1497, 1386))
DeviceIdentifier.AddIdentifierGroup(*_garminIdentifier("Chirp", 1253))
DeviceIdentifier.AddIdentifierGroup(*_garminIdentifier("Edge 200", 1325, 1555))
DeviceIdentifier.AddIdentifierGroup(*_garminIdentifier("Forerunner 910XT", 1328, 1537, 1600, 1664))
DeviceIdentifier.AddIdentifierGroup(*_garminIdentifier("ALF04", 1341))
DeviceIdentifier.AddIdentifierGroup(*_garminIdentifier("Forerunner 610", 1345, 1410))
DeviceIdentifier.AddIdentifierGroup(*_garminIdentifier("Forerunner 210", 1360)) # In the SDK this is marked as "JAPAN" :S
DeviceIdentifier.AddIdentifierGroup(*_garminIdentifier("Forerunner 70", 1436))
DeviceIdentifier.AddIdentifierGroup(*_garminIdentifier("AMX", 1461))
DeviceIdentifier.AddIdentifierGroup(*_garminIdentifier("Forerunner 10", 1482, 1688))
DeviceIdentifier.AddIdentifierGroup(*_garminIdentifier("Swim", 1499))
DeviceIdentifier.AddIdentifierGroup(*_garminIdentifier("Fenix", 1551))
DeviceIdentifier.AddIdentifierGroup(*_garminIdentifier("Edge 510", 1561, 1742, 1821))
DeviceIdentifier.AddIdentifierGroup(*_garminIdentifier("Edge 810", 1567, 1721, 1822, 1823))
DeviceIdentifier.AddIdentifierGroup(*_garminIdentifier("Tempe", 1570))
DeviceIdentifier.AddIdentifierGroup(*_garminIdentifier("VIRB Elite", 1735)) # Where's the VIRB Proletariat?
DeviceIdentifier.AddIdentifierGroup(*_garminIdentifier("Edge Touring", 1736))
DeviceIdentifier.AddIdentifierGroup(*_garminIdentifier("HRM Run", 1752))
DeviceIdentifier.AddIdentifierGroup(*_garminIdentifier("SDM4", 10007))
DeviceIdentifier.AddIdentifierGroup(*_garminIdentifier("Training Center", 20119))

DeviceIdentifier.AddIdentifierGroup(*_garminIdentifier("Forerunner 620", 1623))


########NEW FILE########
__FILENAME__ = dropbox
from tapiriik.settings import WEB_ROOT, DROPBOX_APP_KEY, DROPBOX_APP_SECRET, DROPBOX_FULL_APP_KEY, DROPBOX_FULL_APP_SECRET
from tapiriik.services.service_base import ServiceAuthenticationType, ServiceBase
from tapiriik.services.api import APIException, ServiceExceptionScope, UserException, UserExceptionType, APIExcludeActivity, ServiceException
from tapiriik.services.interchange import ActivityType, UploadedActivity
from tapiriik.services.exception_tools import strip_context
from tapiriik.services.gpx import GPXIO
from tapiriik.services.tcx import TCXIO
from tapiriik.database import cachedb
from dropbox import client, rest, session
from django.core.urlresolvers import reverse
import re
import lxml
from datetime import datetime
import logging
import bson
logger = logging.getLogger(__name__)

class DropboxService(ServiceBase):
    ID = "dropbox"
    DisplayName = "Dropbox"
    DisplayAbbreviation = "DB"
    AuthenticationType = ServiceAuthenticationType.OAuth
    AuthenticationNoFrame = True  # damn dropbox, spoiling my slick UI
    Configurable = True
    ReceivesStationaryActivities = False

    ActivityTaggingTable = {  # earlier items have precedence over
        ActivityType.Running: "run",
        ActivityType.MountainBiking: "m(oun)?t(ai)?n\s*bik(e|ing)",
        ActivityType.Cycling: "(cycl(e|ing)|bik(e|ing))",
        ActivityType.Walking: "walk",
        ActivityType.Hiking: "hik(e|ing)",
        ActivityType.DownhillSkiing: "(downhill|down(hill)?\s*ski(ing)?)",
        ActivityType.CrossCountrySkiing: "(xc|cross.*country)\s*ski(ing)?",
        ActivityType.Snowboarding: "snowboard(ing)?",
        ActivityType.Skating: "skat(e|ing)?",
        ActivityType.Swimming: "swim",
        ActivityType.Wheelchair: "wheelchair",
        ActivityType.Rowing: "row",
        ActivityType.Elliptical: "elliptical",
        ActivityType.Other: "(other|unknown)"
    }
    ConfigurationDefaults = {"SyncRoot": "/", "UploadUntagged": False, "Format":"tcx", "Filename":"%Y-%m-%d_#NAME_#TYPE"}

    SupportsHR = SupportsCadence = True

    SupportedActivities = ActivityTaggingTable.keys()

    def __init__(self):
        self.OutstandingReqTokens = {}

    def _getClient(self, serviceRec):
        if serviceRec.Authorization["Full"]:
            sess = session.DropboxSession(DROPBOX_FULL_APP_KEY, DROPBOX_FULL_APP_SECRET, "dropbox")
        else:
            sess = session.DropboxSession(DROPBOX_APP_KEY, DROPBOX_APP_SECRET, "app_folder")
        sess.set_token(serviceRec.Authorization["Key"], serviceRec.Authorization["Secret"])
        return client.DropboxClient(sess)

    def WebInit(self):
        self.UserAuthorizationURL = reverse("oauth_redirect", kwargs={"service": "dropbox"})
        pass

    def RequiresConfiguration(self, svcRec):
        return svcRec.Authorization["Full"] and ("SyncRoot" not in svcRec.Config or not len(svcRec.Config["SyncRoot"]))

    def GenerateUserAuthorizationURL(self, level=None):
        full = level == "full"
        if full:
            sess = session.DropboxSession(DROPBOX_FULL_APP_KEY, DROPBOX_FULL_APP_SECRET, "dropbox")
        else:
            sess = session.DropboxSession(DROPBOX_APP_KEY, DROPBOX_APP_SECRET, "app_folder")

        reqToken = sess.obtain_request_token()
        self.OutstandingReqTokens[reqToken.key] = reqToken
        return sess.build_authorize_url(reqToken, oauth_callback=WEB_ROOT + reverse("oauth_return", kwargs={"service": "dropbox", "level": "full" if full else "normal"}))

    def _getUserId(self, serviceRec):
        info = self._getClient(serviceRec).account_info()
        return info['uid']

    def RetrieveAuthorizationToken(self, req, level):
        from tapiriik.services import Service
        tokenKey = req.GET["oauth_token"]
        token = self.OutstandingReqTokens[tokenKey]
        del self.OutstandingReqTokens[tokenKey]
        full = level == "full"
        if full:
            sess = session.DropboxSession(DROPBOX_FULL_APP_KEY, DROPBOX_FULL_APP_SECRET, "dropbox")
        else:
            sess = session.DropboxSession(DROPBOX_APP_KEY, DROPBOX_APP_SECRET, "app_folder")

        accessToken = sess.obtain_access_token(token)

        uid = int(req.GET["uid"])  # duh!
        return (uid, {"Key": accessToken.key, "Secret": accessToken.secret, "Full": full})

    def RevokeAuthorization(self, serviceRecord):
        pass  # :(

    def ConfigurationUpdating(self, svcRec, newConfig, oldConfig):
        from tapiriik.sync import Sync
        from tapiriik.auth import User
        if newConfig["SyncRoot"] != oldConfig["SyncRoot"]:
            Sync.ScheduleImmediateSync(User.AuthByService(svcRec), True)
            cachedb.dropbox_cache.update({"ExternalID": svcRec.ExternalID}, {"$unset": {"Structure": None}})

    def _raiseDbException(self, e):
        if e.status == 401:
            raise APIException("Authorization error - status " + str(e.status) + " reason " + str(e.error_msg) + " body " + str(e.body), block=True, user_exception=UserException(UserExceptionType.Authorization, intervention_required=True))
        if e.status == 507:
            raise APIException("Dropbox quota error", block=True, user_exception=UserException(UserExceptionType.AccountFull, intervention_required=True))
        raise APIException("API failure - status " + str(e.status) + " reason " + str(e.reason) + " body " + str(e.error_msg))

    def _folderRecurse(self, structCache, dbcl, path):
        hash = None
        existingRecord = [x for x in structCache if x["Path"] == path]
        children = [x for x in structCache if x["Path"].startswith(path) and x["Path"] != path]
        existingRecord = existingRecord[0] if len(existingRecord) else None
        if existingRecord:
            hash = existingRecord["Hash"]
        try:
            dirmetadata = dbcl.metadata(path, hash=hash)
        except rest.ErrorResponse as e:
            if e.status == 304:
                for child in children:
                    self._folderRecurse(structCache, dbcl, child["Path"])  # still need to recurse for children
                return  # nothing new to update here
            if e.status == 404:
                # dir doesn't exist any more, delete it and all children
                structCache[:] = (x for x in structCache if x != existingRecord and x not in children)
                return
            self._raiseDbException(e)
        if not existingRecord:
            existingRecord = {"Files": [], "Path": dirmetadata["path"]}
            structCache.append(existingRecord)

        existingRecord["Hash"] = dirmetadata["hash"]
        existingRecord["Files"] = []
        curDirs = []
        for file in dirmetadata["contents"]:
            if file["is_dir"]:
                curDirs.append(file["path"])
                self._folderRecurse(structCache, dbcl, file["path"])
            else:
                if not file["path"].lower().endswith(".gpx") and not file["path"].lower().endswith(".tcx"):
                    continue  # another kind of file
                existingRecord["Files"].append({"Rev": file["rev"], "Path": file["path"]})
        structCache[:] = (x for x in structCache if x["Path"] in curDirs or x not in children)  # delete ones that don't exist

    def _tagActivity(self, text):
        for act, pattern in self.ActivityTaggingTable.items():
            if re.search(pattern, text, re.IGNORECASE):
                return act
        return None

    def _getActivity(self, serviceRecord, dbcl, path):
        activityData = None

        try:
            f, metadata = dbcl.get_file_and_metadata(path)
        except rest.ErrorResponse as e:
            self._raiseDbException(e)

        if not activityData:
            activityData = f.read()


        try:
            if path.lower().endswith(".tcx"):
                act = TCXIO.Parse(activityData)
            else:
                act = GPXIO.Parse(activityData)
        except ValueError as e:
            raise APIExcludeActivity("Invalid GPX/TCX " + str(e), activityId=path, userException=UserException(UserExceptionType.Corrupt))
        except lxml.etree.XMLSyntaxError as e:
            raise APIExcludeActivity("LXML parse error " + str(e), activityId=path, userException=UserException(UserExceptionType.Corrupt))
        return act, metadata["rev"]

    def DownloadActivityList(self, svcRec, exhaustive=False):
        dbcl = self._getClient(svcRec)
        if not svcRec.Authorization["Full"]:
            syncRoot = "/"
        else:
            syncRoot = svcRec.Config["SyncRoot"]
        cache = cachedb.dropbox_cache.find_one({"ExternalID": svcRec.ExternalID})
        if cache is None:
            cache = {"ExternalID": svcRec.ExternalID, "Structure": [], "Activities": {}}
        if "Structure" not in cache:
            cache["Structure"] = []
        self._folderRecurse(cache["Structure"], dbcl, syncRoot)

        activities = []
        exclusions = []

        for dir in cache["Structure"]:
            for file in dir["Files"]:
                path = file["Path"]
                if svcRec.Authorization["Full"]:
                    relPath = path.replace(syncRoot, "", 1)
                else:
                    relPath = path.replace("/Apps/tapiriik/", "", 1)  # dropbox api is meh api

                hashedRelPath = self._hash_path(relPath)
                if hashedRelPath in cache["Activities"]:
                    existing = cache["Activities"][hashedRelPath]
                else:
                    existing = None

                if not existing:
                    # Continue to use the old records keyed by UID where possible
                    existing = [(k, x) for k, x in cache["Activities"].items() if "Path" in x and x["Path"] == relPath]  # path is relative to syncroot to reduce churn if they relocate it
                    existing = existing[0] if existing else None
                    if existing is not None:
                        existUID, existing = existing
                        existing["UID"] = existUID

                if existing and existing["Rev"] == file["Rev"]:
                    # don't need entire activity loaded here, just UID
                    act = UploadedActivity()
                    act.UID = existing["UID"]
                    try:
                        act.StartTime = datetime.strptime(existing["StartTime"], "%H:%M:%S %d %m %Y %z")
                    except:
                        act.StartTime = datetime.strptime(existing["StartTime"], "%H:%M:%S %d %m %Y") # Exactly one user has managed to break %z :S
                    if "EndTime" in existing:  # some cached activities may not have this, it is not essential
                        act.EndTime = datetime.strptime(existing["EndTime"], "%H:%M:%S %d %m %Y %z")
                else:
                    logger.debug("Retrieving %s (%s)" % (path, "outdated meta cache" if existing else "not in meta cache"))
                    # get the full activity
                    try:
                        act, rev = self._getActivity(svcRec, dbcl, path)
                    except APIExcludeActivity as e:
                        logger.info("Encountered APIExcludeActivity %s" % str(e))
                        exclusions.append(strip_context(e))
                        continue

                    try:
                        act.EnsureTZ()
                    except:
                        pass # We tried.

                    if hasattr(act, "OriginatedFromTapiriik") and not act.CountTotalWaypoints():
                        # This is one of the files created when TCX export was hopelessly broken for non-GPS activities.
                        # Right now, no activities in dropbox from tapiriik should be devoid of waypoints - since dropbox doesn't receive stationary activities
                        # In the future when this changes, will obviously have to modify this code to also look at modification dates or similar.
                        if ".tcx.summary-data" in path:
                            logger.info("...summary file already moved")
                        else:
                            logger.info("...moving summary-only file")
                            dbcl.file_move(path, path.replace(".tcx", ".tcx.summary-data"))
                        continue # DON'T include in listing - it'll be regenerated
                    del act.Laps
                    act.Laps = []  # Yeah, I'll process the activity twice, but at this point CPU time is more plentiful than RAM.
                    cache["Activities"][hashedRelPath] = {"Rev": rev, "UID": act.UID, "StartTime": act.StartTime.strftime("%H:%M:%S %d %m %Y %z"), "EndTime": act.EndTime.strftime("%H:%M:%S %d %m %Y %z")}
                tagRes = self._tagActivity(relPath)
                act.ServiceData = {"Path": path, "Tagged":tagRes is not None}

                act.Type = tagRes if tagRes is not None else ActivityType.Other

                logger.debug("Activity s/t %s" % act.StartTime)

                activities.append(act)

        if "_id" in cache:
            cachedb.dropbox_cache.save(cache)
        else:
            cachedb.dropbox_cache.insert(cache)
        return activities, exclusions

    def DownloadActivity(self, serviceRecord, activity):
        # activity might not be populated at this point, still possible to bail out
        if not activity.ServiceData["Tagged"]:
            if not (hasattr(serviceRecord, "Config") and "UploadUntagged" in serviceRecord.Config and serviceRecord.Config["UploadUntagged"]):
                raise APIExcludeActivity("Activity untagged", permanent=False, activityId=activity.ServiceData["Path"], userException=UserException(UserExceptionType.Untagged))

        # activity might already be populated, if not download it again
        path = activity.ServiceData["Path"]
        dbcl = self._getClient(serviceRecord)
        fullActivity, rev = self._getActivity(serviceRecord, dbcl, path)
        fullActivity.Type = activity.Type
        fullActivity.ServiceDataCollection = activity.ServiceDataCollection
        activity = fullActivity

        # Dropbox doesn't support stationary activities yet.
        if activity.CountTotalWaypoints() <= 1:
            raise APIExcludeActivity("Too few waypoints", activityId=path, userException=UserException(UserExceptionType.Corrupt))

        return activity

    def _hash_path(self, path):
        import hashlib
        # Can't use the raw file path as a dict key in Mongo, since who knows what'll be in it (periods especially)
        # Used the activity UID for the longest time, but that causes inefficiency when >1 file represents the same activity
        # So, this:
        csp = hashlib.new("md5")
        csp.update(path.encode('utf-8'))
        return csp.hexdigest()

    def _clean_activity_name(self, name):
        # https://www.dropbox.com/help/145/en
        return re.sub("[><:\"|?*]", "", re.sub("[/\\\]", "-", name))

    def _format_file_name(self, format, activity):
        name_pattern = re.compile("#NAME", re.IGNORECASE)
        type_pattern = re.compile("#TYPE", re.IGNORECASE)
        name = activity.StartTime.strftime(format)
        name = name_pattern.sub(self._clean_activity_name(activity.Name) if activity.Name and len(activity.Name) > 0 and activity.Name.lower() != activity.Type.lower() else "", name)
        name = type_pattern.sub(activity.Type, name)
        name = re.sub(r"([\W_])\1+", r"\1", name) # To handle cases where the activity is unnamed
        name = re.sub(r"^([\W_])|([\W_])$", "", name) # To deal with trailing-seperator weirdness (repeated seperator handled by prev regexp)
        return name

    def UploadActivity(self, serviceRecord, activity):
        format = serviceRecord.GetConfiguration()["Format"]
        if format == "tcx":
            if "tcx" in activity.PrerenderedFormats:
                logger.debug("Using prerendered TCX")
                data = activity.PrerenderedFormats["tcx"]
            else:
                data = TCXIO.Dump(activity)
        else:
            if "gpx" in activity.PrerenderedFormats:
                logger.debug("Using prerendered GPX")
                data = activity.PrerenderedFormats["gpx"]
            else:
                data = GPXIO.Dump(activity)

        dbcl = self._getClient(serviceRecord)
        fname = self._format_file_name(serviceRecord.GetConfiguration()["Filename"], activity)[:250] + "." + format # DB has a max path component length of 255 chars, and we have to save for the file ext (4) and the leading slash (1)

        if not serviceRecord.Authorization["Full"]:
            fpath = "/" + fname
        else:
            fpath = serviceRecord.Config["SyncRoot"] + "/" + fname

        try:
            metadata = dbcl.put_file(fpath, data.encode("UTF-8"))
        except rest.ErrorResponse as e:
            self._raiseDbException(e)
        # fake this in so we don't immediately redownload the activity next time 'round
        cache = cachedb.dropbox_cache.find_one({"ExternalID": serviceRecord.ExternalID})
        cache["Activities"][self._hash_path("/" + fname)] = {"Rev": metadata["rev"], "UID": activity.UID, "StartTime": activity.StartTime.strftime("%H:%M:%S %d %m %Y %z"), "EndTime": activity.EndTime.strftime("%H:%M:%S %d %m %Y %z")}
        cachedb.dropbox_cache.update({"ExternalID": serviceRecord.ExternalID}, cache)  # not upsert, hope the record exists at this time...
        return fpath

    def DeleteCachedData(self, serviceRecord):
        cachedb.dropbox_cache.remove({"ExternalID": serviceRecord.ExternalID})

########NEW FILE########
__FILENAME__ = endomondo
from tapiriik.settings import WEB_ROOT, ENDOMONDO_CLIENT_KEY, ENDOMONDO_CLIENT_SECRET, SECRET_KEY
from tapiriik.services.service_base import ServiceAuthenticationType, ServiceBase
from tapiriik.services.interchange import UploadedActivity, ActivityType, ActivityStatistic, ActivityStatisticUnit, Waypoint, WaypointType, Location, Lap
from tapiriik.services.api import APIException, APIExcludeActivity, UserException, UserExceptionType

from django.core.urlresolvers import reverse
from datetime import timedelta, datetime
import dateutil.parser
from requests_oauthlib import OAuth1Session
import logging
import pytz
import json
import os
import hashlib

logger = logging.getLogger(__name__)


class EndomondoService(ServiceBase):
    ID = "endomondo"
    DisplayName = "Endomondo"
    DisplayAbbreviation = "EN"
    AuthenticationType = ServiceAuthenticationType.OAuth
    UserProfileURL = "http://www.endomondo.com/profile/{0}"
    UserActivityURL = "http://www.endomondo.com/workouts/{1}/{0}"

    PartialSyncRequiresTrigger = True
    AuthenticationNoFrame = True

    ConfigurationDefaults = {
        "DeviceRegistered": False,
    }

    # The complete list:
    # running,cycling transportation,cycling sport,mountain biking,skating,roller skiing,skiing cross country,skiing downhill,snowboarding,kayaking,kite surfing,rowing,sailing,windsurfing,fitness walking,golfing,hiking,orienteering,walking,riding,swimming,spinning,other,aerobics,badminton,baseball,basketball,boxing,stair climbing,cricket,cross training,dancing,fencing,american football,rugby,soccer,handball,hockey,pilates,polo,scuba diving,squash,table tennis,tennis,beach volley,volleyball,weight training,yoga,martial arts,gymnastics,step counter,crossfit,treadmill running,skateboarding,surfing,snowshoeing,wheelchair,climbing,treadmill walking
    _activityMappings = {
        "running": ActivityType.Running,
        "cycling transportation": ActivityType.Cycling,
        "cycling sport": ActivityType.Cycling,
        "mountain biking": ActivityType.MountainBiking,
        "skating": ActivityType.Skating,
        "skiing cross country": ActivityType.CrossCountrySkiing,
        "skiing downhill": ActivityType.DownhillSkiing,
        "snowboarding": ActivityType.Snowboarding,
        "rowing": ActivityType.Rowing,
        "fitness walking": ActivityType.Walking,
        "hiking": ActivityType.Walking,
        "orienteering": ActivityType.Walking,
        "walking": ActivityType.Walking,
        "swimming": ActivityType.Swimming,
        "other": ActivityType.Other,
        "treadmill running": ActivityType.Running,
        "snowshoeing": ActivityType.Walking,
        "wheelchair": ActivityType.Wheelchair,
        "treadmill walking": ActivityType.Walking
    }

    _reverseActivityMappings = {
        "running": ActivityType.Running,
        "cycling sport": ActivityType.Cycling,
        "mountain biking": ActivityType.MountainBiking,
        "skating": ActivityType.Skating,
        "skiing cross country": ActivityType.CrossCountrySkiing,
        "skiing downhill": ActivityType.DownhillSkiing,
        "snowboarding": ActivityType.Snowboarding,
        "rowing": ActivityType.Rowing,
        "walking": ActivityType.Walking,
        "swimming": ActivityType.Swimming,
        "other": ActivityType.Other,
        "snowshoeing": ActivityType.Walking,
        "wheelchair": ActivityType.Wheelchair,
    }

    SupportedActivities = list(_activityMappings.values())

    ReceivesNonGPSActivitiesWithOtherSensorData = False

    _oauth_token_secrets = {}

    def WebInit(self):
        self.UserAuthorizationURL = reverse("oauth_redirect", kwargs={"service": "endomondo"})

    def _oauthSession(self, connection=None, **params):
        if connection:
            params["resource_owner_key"] = connection.Authorization["Token"]
            params["resource_owner_secret"] = connection.Authorization["Secret"]
        return OAuth1Session(ENDOMONDO_CLIENT_KEY, client_secret=ENDOMONDO_CLIENT_SECRET, **params)

    def GenerateUserAuthorizationURL(self, level=None):
        oauthSession = self._oauthSession(callback_uri=WEB_ROOT + reverse("oauth_return", kwargs={"service": "endomondo"}))
        tokens = oauthSession.fetch_request_token("https://api.endomondo.com/oauth/request_token")
        self._oauth_token_secrets[tokens["oauth_token"]] = tokens["oauth_token_secret"]
        return oauthSession.authorization_url("https://www.endomondo.com/oauth/authorize")

    def RetrieveAuthorizationToken(self, req, level):
        oauthSession = self._oauthSession(resource_owner_secret=self._oauth_token_secrets[req.GET["oauth_token"]])
        oauthSession.parse_authorization_response(req.get_full_path())
        tokens = oauthSession.fetch_access_token("https://api.endomondo.com/oauth/access_token")
        userInfo = oauthSession.get("https://api.endomondo.com/api/1/user")
        userInfo = userInfo.json()
        return (userInfo["id"], {"Token": tokens["oauth_token"], "Secret": tokens["oauth_token_secret"]})

    def RevokeAuthorization(self, serviceRecord):
        pass

    def _parseDate(self, date):
        return datetime.strptime(date, "%Y-%m-%d %H:%M:%S UTC").replace(tzinfo=pytz.utc)

    def _formatDate(self, date):
        return datetime.strftime(date.astimezone(pytz.utc), "%Y-%m-%d %H:%M:%S UTC")

    def DownloadActivityList(self, serviceRecord, exhaustive=False):
        oauthSession = self._oauthSession(serviceRecord)

        activities = []
        exclusions = []

        page_url = "https://api.endomondo.com/api/1/workouts"

        while True:
            resp = oauthSession.get(page_url)
            try:
                respList = resp.json()["data"]
            except ValueError:
                raise APIException("Error decoding activity list resp %s %s" % (resp.status_code, resp.text))
            for actInfo in respList:
                activity = UploadedActivity()
                activity.StartTime = self._parseDate(actInfo["start_time"])
                print("Activity s/t %s" % activity.StartTime)
                if "is_tracking" in actInfo and actInfo["is_tracking"]:
                    exclusions.append(APIExcludeActivity("Not complete", activityId=actInfo["id"], permanent=False, userException=UserException(UserExceptionType.LiveTracking)))
                    continue

                if "end_time" in actInfo:
                    activity.EndTime = self._parseDate(actInfo["end_time"])

                if actInfo["sport"] in self._activityMappings:
                    activity.Type = self._activityMappings[actInfo["sport"]]

                # "duration" is timer time
                if "duration_total" in actInfo:
                    activity.Stats.TimerTime = ActivityStatistic(ActivityStatisticUnit.Seconds, value=float(actInfo["duration_total"]))

                if "distance_total" in actInfo:
                    activity.Stats.Distance = ActivityStatistic(ActivityStatisticUnit.Kilometers, value=float(actInfo["distance_total"]))

                if "calories_total" in actInfo:
                    activity.Stats.Energy = ActivityStatistic(ActivityStatisticUnit.Kilocalories, value=float(actInfo["calories_total"]))

                activity.Stats.Elevation = ActivityStatistic(ActivityStatisticUnit.Meters)

                if "altitude_max" in actInfo:
                    activity.Stats.Elevation.Max = float(actInfo["altitude_max"])

                if "altitude_min" in actInfo:
                    activity.Stats.Elevation.Min = float(actInfo["altitude_min"])

                if "total_ascent" in actInfo:
                    activity.Stats.Elevation.Gain = float(actInfo["total_ascent"])

                if "total_descent" in actInfo:
                    activity.Stats.Elevation.Loss = float(actInfo["total_descent"])

                activity.Stats.Speed = ActivityStatistic(ActivityStatisticUnit.KilometersPerHour)
                if "speed_max" in actInfo:
                    activity.Stats.Speed.Max = float(actInfo["speed_max"])

                if "heart_rate_avg" in actInfo:
                    activity.Stats.HR = ActivityStatistic(ActivityStatisticUnit.BeatsPerMinute, avg=float(actInfo["heart_rate_avg"]))

                if "heart_rate_max" in actInfo:
                    activity.Stats.HR.update(ActivityStatistic(ActivityStatisticUnit.BeatsPerMinute, max=float(actInfo["heart_rate_max"])))

                if "cadence_avg" in actInfo:
                    activity.Stats.Cadence = ActivityStatistic(ActivityStatisticUnit.RevolutionsPerMinute, avg=int(actInfo["cadence_avg"]))

                if "cadence_max" in actInfo:
                    activity.Stats.Cadence.update(ActivityStatistic(ActivityStatisticUnit.RevolutionsPerMinute, max=int(actInfo["cadence_max"])))

                if "title" in actInfo:
                    activity.Name = actInfo["title"]

                activity.ServiceData = {"WorkoutID": int(actInfo["id"])}

                activity.CalculateUID()
                activities.append(activity)

            paging = resp.json()["paging"]
            if "next" not in paging or not paging["next"] or not exhaustive:
                break
            else:
                page_url = paging["next"]

        return activities, exclusions

    def SubscribeToPartialSyncTrigger(self, serviceRecord):
        resp = self._oauthSession(serviceRecord).put("https://api.endomondo.com/api/1/subscriptions/workout/%s" % serviceRecord.ExternalID)
        assert resp.status_code in [200, 201] # Created, or already existed
        serviceRecord.SetPartialSyncTriggerSubscriptionState(True)

    def UnsubscribeFromPartialSyncTrigger(self, serviceRecord):
        resp = self._oauthSession(serviceRecord).delete("https://api.endomondo.com/api/1/subscriptions/workout/%s" % serviceRecord.ExternalID)
        assert resp.status_code in [204, 500] # Docs say otherwise, but no-subscription-found is 500
        serviceRecord.SetPartialSyncTriggerSubscriptionState(False)

    def ServiceRecordIDsForPartialSyncTrigger(self, req):
        data = json.loads(req.body.decode("UTF-8"))
        delta_external_ids = [int(x["id"]) for x in data["data"]]
        return delta_external_ids

    def DownloadActivity(self, serviceRecord, activity):
        resp = self._oauthSession(serviceRecord).get("https://api.endomondo.com/api/1/workouts/%d" % activity.ServiceData["WorkoutID"], params={"fields": "points"})
        try:
            resp = resp.json()
        except ValueError:
            res_txt = resp.text
            raise APIException("Parse failure in Endomondo activity download: %s" % resp.status_code)
        lap = Lap(stats=activity.Stats, startTime=activity.StartTime, endTime=activity.EndTime)
        activity.Laps = [lap]

        activity.GPS = False

        for pt in resp["points"]:
            wp = Waypoint()
            wp.Timestamp = self._parseDate(pt["time"])

            if ("lat" in pt and "lng" in pt) or "alt" in pt:
                wp.Location = Location()
                if "lat" in pt and "lng" in pt:
                    wp.Location.Latitude = pt["lat"]
                    wp.Location.Longitude = pt["lng"]
                    activity.GPS = True
                if "alt" in pt:
                    wp.Location.Altitude = pt["alt"]

            if "hr" in pt:
                wp.HR = pt["hr"]

            if "cad" in pt:
                wp.Cadence = pt["cad"]

            lap.Waypoints.append(wp)
        activity.Stationary = len(lap.Waypoints) == 0
        return activity

    def _deviceId(self, serviceRecord):
        csp = hashlib.new("md5")
        csp.update(str(serviceRecord.ExternalID).encode("utf-8"))
        csp.update(SECRET_KEY.encode("utf-8"))
        return "tap-" + csp.hexdigest()

    def UploadActivity(self, serviceRecord, activity):
        session = self._oauthSession(serviceRecord)
        device_id = self._deviceId(serviceRecord)
        if not serviceRecord.GetConfiguration()["DeviceRegistered"]:
            device_info = {
                "name": "tapiriik",
                "vendor": "tapiriik",
                "model": "tapiriik",
                "os": "tapiriik",
                "os_version": "1",
                "app_variant": "tapiriik",
                "app_version": "1"
            }
            device_add_resp = session.post("https://api.endomondo.com/api/1/device/%s" % device_id, data=json.dumps(device_info))
            if device_add_resp.status_code != 200:
                raise APIException("Could not add device %s %s" % (device_add_resp.status_code, device_add_resp.text))
            serviceRecord.SetConfiguration({"DeviceRegistered": True})

        activity_id = "tap-" + activity.UID + "-" + str(os.getpid())

        upload_data = {
            "device_id": device_id,
            "sport": [k for k,v in self._reverseActivityMappings.items() if v == activity.Type][0],
            "start_time": self._formatDate(activity.StartTime),
            "end_time": self._formatDate(activity.EndTime),
            "points": []
        }

        if activity.Name:
            upload_data["title"] = activity.Name

        if activity.Notes:
            upload_data["notes"] = activity.Notes

        if activity.Stats.Distance.Value is not None:
            upload_data["distance_total"] = activity.Stats.Distance.asUnits(ActivityStatisticUnit.Kilometers).Value

        if activity.Stats.TimerTime.Value is not None:
            upload_data["duration_total"] = activity.Stats.TimerTime.asUnits(ActivityStatisticUnit.Seconds).Value
        elif activity.Stats.MovingTime.Value is not None:
            upload_data["duration_total"] = activity.Stats.MovingTime.asUnits(ActivityStatisticUnit.Seconds).Value
        else:
            upload_data["duration_total"] = (activity.EndTime - activity.StartTime).total_seconds()

        if activity.Stats.Energy.Value is not None:
            upload_data["calories_total"] = activity.Stats.Energy.asUnits(ActivityStatisticUnit.Kilocalories).Value

        elev_stats = activity.Stats.Elevation.asUnits(ActivityStatisticUnit.Meters)
        if elev_stats.Max is not None:
            upload_data["altitude_max"] = elev_stats.Max
        if elev_stats.Min is not None:
            upload_data["altitude_min"] = elev_stats.Min
        if elev_stats.Gain is not None:
            upload_data["total_ascent"] = elev_stats.Gain
        if elev_stats.Loss is not None:
            upload_data["total_descent"] = elev_stats.Loss

        speed_stats = activity.Stats.Speed.asUnits(ActivityStatisticUnit.KilometersPerHour)
        if speed_stats.Max is not None:
            upload_data["speed_max"] = speed_stats.Max

        hr_stats = activity.Stats.HR.asUnits(ActivityStatisticUnit.BeatsPerMinute)
        if hr_stats.Average is not None:
            upload_data["heart_rate_avg"] = hr_stats.Average
        if hr_stats.Max is not None:
            upload_data["heart_rate_max"] = hr_stats.Max

        if activity.Stats.Cadence.Average is not None:
            upload_data["cadence_avg"] = activity.Stats.Cadence.asUnits(ActivityStatisticUnit.RevolutionsPerMinute).Average
        elif activity.Stats.RunCadence.Average is not None:
            upload_data["cadence_avg"] = activity.Stats.RunCadence.asUnits(ActivityStatisticUnit.StepsPerMinute).Average

        if activity.Stats.Cadence.Max is not None:
            upload_data["cadence_max"] = activity.Stats.Cadence.asUnits(ActivityStatisticUnit.RevolutionsPerMinute).Max
        elif activity.Stats.RunCadence.Max is not None:
            upload_data["cadence_max"] = activity.Stats.RunCadence.asUnits(ActivityStatisticUnit.StepsPerMinute).Max

        for wp in activity.GetFlatWaypoints():
            pt = {
                "time": self._formatDate(wp.Timestamp),
            }
            if wp.Location:
                if wp.Location.Latitude is not None and wp.Location.Longitude is not None:
                    pt["lat"] = wp.Location.Latitude
                    pt["lng"] = wp.Location.Longitude
                if wp.Location.Altitude is not None:
                    pt["alt"] = wp.Location.Altitude
            if wp.HR is not None:
                pt["hr"] = round(wp.HR)
            if wp.Cadence is not None:
                pt["cad"] = round(wp.Cadence)
            elif wp.RunCadence is not None:
                pt["cad"] = round(wp.RunCadence)

            if wp.Type == WaypointType.Pause:
                pt["inst"] = "pause"
            elif wp.Type == WaypointType.Resume:
                pt["inst"] = "resume"
            upload_data["points"].append(pt)

        if len(upload_data["points"]):
            upload_data["points"][0]["inst"] = "start"
            upload_data["points"][-1]["inst"] = "stop"

        upload_resp = session.post("https://api.endomondo.com/api/1/workouts/%s" % activity_id, data=json.dumps(upload_data))
        if upload_resp.status_code != 200:
            raise APIException("Could not upload activity %s %s" % (upload_resp.status_code, upload_resp.text))

        return upload_resp.json()["id"]

    def DeleteCachedData(self, serviceRecord):
        pass

########NEW FILE########
__FILENAME__ = exception_tools
def strip_context(exc):
	exc.__context__ = exc.__cause__ = exc.__traceback__ = None
	return exc
########NEW FILE########
__FILENAME__ = fit
from datetime import datetime, timedelta
from .interchange import WaypointType, ActivityStatisticUnit, ActivityType, LapIntensity, LapTriggerMethod
from .devices import DeviceIdentifier, DeviceIdentifierType
import struct
import sys
import pytz

class FITFileType:
	Activity = 4 # The only one we care about now.

class FITManufacturer:
	DEVELOPMENT = 255 # $1500/year for one of these numbers.

class FITEvent:
	Timer = 0
	Lap = 9
	Activity = 26

class FITEventType:
	Start = 0
	Stop = 1

# It's not a coincidence that these enums match the ones in interchange perfectly
class FITLapIntensity:
	Active = 0
	Rest = 1
	Warmup = 2
	Cooldown = 3

class FITLapTriggerMethod:
    Manual = 0
    Time = 1
    Distance = 2
    PositionStart = 3
    PositionLap = 4
    PositionWaypoint = 5
    PositionMarked = 6
    SessionEnd = 7
    FitnessEquipment = 8


class FITActivityType:
	GENERIC = 0
	RUNNING = 1
	CYCLING = 2
	TRANSITION = 3
	FITNESS_EQUIPMENT = 4
	SWIMMING = 5
	WALKING = 6
	ALL = 254

class FITMessageDataType:
	def __init__(self, name, typeField, size, packFormat, invalid, formatter=None):
		self.Name = name
		self.TypeField = typeField
		self.Size = size
		self.PackFormat = packFormat
		self.Formatter = formatter
		self.InvalidValue = invalid

class FITMessageTemplate:
	def __init__(self, name, number, *args, fields=None):
		self.Name = name
		self.Number = number
		self.Fields = {}
		self.FieldNameSet = set()
		self.FieldNameList = []
		if len(args) == 1 and type(args[0]) is dict:
			fields = args[0]
			self.Fields = fields
			self.FieldNameSet = set(fields.keys()) # It strikes me that keys might already be a set?
		else:
			# Supply fields in order NUM, NAME, TYPE
			for x in range(0, int(len(args)/3)):
				n = x * 3
				self.Fields[args[n+1]] = {"Name": args[n+1], "Number": args[n], "Type": args[n+2]}
				self.FieldNameSet.add(args[n+1])
		sortedFields = list(self.Fields.values())
		sortedFields.sort(key = lambda x: x["Number"])
		self.FieldNameList = [x["Name"] for x in sortedFields] # *ordered*


class FITMessageGenerator:
	def __init__(self):
		self._types = {}
		self._messageTemplates = {}
		self._definitions = {}
		self._result = []
		# All our convience functions for preparing the field types to be packed.
		def stringFormatter(input):
			raise Exception("Not implemented")
		def dateTimeFormatter(input):
			# UINT32
			# Seconds since UTC 00:00 Dec 31 1989. If <0x10000000 = system time
			if input is None:
				return struct.pack("<I", 0xFFFFFFFF)
			delta = round((input - datetime(hour=0, minute=0, month=12, day=31, year=1989)).total_seconds())
			return struct.pack("<I", delta)
		def msecFormatter(input):
			# UINT32
			if input is None:
				return struct.pack("<I", 0xFFFFFFFF)
			return struct.pack("<I", round((input if type(input) is not timedelta else input.total_seconds()) * 1000))
		def mmPerSecFormatter(input):
			# UINT16
			if input is None:
				return struct.pack("<H", 0xFFFF)
			return struct.pack("<H", round(input * 1000))
		def cmFormatter(input):
			# UINT32
			if input is None:
				return struct.pack("<I", 0xFFFFFFFF)
			return struct.pack("<I", round(input * 100))
		def altitudeFormatter(input):
			# UINT16
			if input is None:
				return struct.pack("<H", 0xFFFF)
			return struct.pack("<H", round((input + 500) * 5)) # Increments of 1/5, offset from -500m :S
		def semicirclesFormatter(input):
			# SINT32
			if input is None:
				return struct.pack("<i", 0x7FFFFFFF) # FIT-defined invalid value
			return struct.pack("<i", round(input * (2 ** 31 / 180)))
		def versionFormatter(input):
			# UINT16
			if input is None:
				return struct.pack("<H", 0xFFFF)
			return struct.pack("<H", round(input * 100))


		def defType(name, *args, **kwargs):

			aliases = [name] if type(name) is not list else name
			# Cheap cheap cheap
			for alias in aliases:
				self._types[alias] = FITMessageDataType(alias, *args, **kwargs)

		defType(["enum", "file"], 0x00, 1, "B", 0xFF)
		defType("sint8", 0x01, 1, "b", 0x7F)
		defType("uint8", 0x02, 1, "B", 0xFF)
		defType("sint16", 0x83, 2, "h", 0x7FFF)
		defType(["uint16", "manufacturer"], 0x84, 2, "H", 0xFFFF)
		defType("sint32", 0x85, 4, "i", 0x7FFFFFFF)
		defType("uint32", 0x86, 4, "I", 0xFFFFFFFF)
		defType("string", 0x07, None, None, 0x0, formatter=stringFormatter)
		defType("float32", 0x88, 4, "f", 0xFFFFFFFF)
		defType("float64", 0x89, 8, "d", 0xFFFFFFFFFFFFFFFF)
		defType("uint8z", 0x0A, 1, "B", 0x00)
		defType("uint16z", 0x0B, 2, "H", 0x00)
		defType("uint32z", 0x0C, 4, "I", 0x00)
		defType("byte", 0x0D, 1, "B", 0xFF) # This isn't totally correct, docs say "an array of bytes"

		# Not strictly FIT fields, but convenient.
		defType("date_time", 0x86, 4, None, 0xFFFFFFFF, formatter=dateTimeFormatter)
		defType("duration_msec", 0x86, 4, None, 0xFFFFFFFF, formatter=msecFormatter)
		defType("distance_cm", 0x86, 4, None, 0xFFFFFFFF, formatter=cmFormatter)
		defType("mmPerSec", 0x84, 2, None, 0xFFFF, formatter=mmPerSecFormatter)
		defType("semicircles", 0x85, 4, None, 0x7FFFFFFF, formatter=semicirclesFormatter)
		defType("altitude", 0x84, 2, None, 0xFFFF, formatter=altitudeFormatter)
		defType("version", 0x84, 2, None, 0xFFFF, formatter=versionFormatter)

		def defMsg(name, *args):
			self._messageTemplates[name] = FITMessageTemplate(name, *args)

		defMsg("file_id", 0,
			0, "type", "file",
			1, "manufacturer", "manufacturer",
			2, "product", "uint16",
			3, "serial_number", "uint32z",
			4, "time_created", "date_time",
			5, "number", "uint16")

		defMsg("file_creator", 49,
			0, "software_version", "uint16",
			1, "hardware_version", "uint8")

		defMsg("activity", 34,
			253, "timestamp", "date_time",
			1, "num_sessions", "uint16",
			2, "type", "enum",
			3, "event", "enum", # Required
			4, "event_type", "enum",
			5, "local_timestamp", "date_time")

		defMsg("session", 18,
			253, "timestamp", "date_time",
			2, "start_time", "date_time", # Vs timestamp, which was whenever the record was "written"/end of the session
			7, "total_elapsed_time", "duration_msec", # Including pauses
			8, "total_timer_time", "duration_msec", # Excluding pauses
			59, "total_moving_time", "duration_msec",
			5, "sport", "enum",
			6, "sub_sport", "enum",
			0, "event", "enum",
			1, "event_type", "enum",
			9, "total_distance", "distance_cm",
			11,"total_calories", "uint16",
			14, "avg_speed", "mmPerSec",
			15, "max_speed", "mmPerSec",
			16, "avg_heart_rate", "uint8",
			17, "max_heart_rate", "uint8",
			18, "avg_cadence", "uint8",
			19, "max_cadence", "uint8",
			20, "avg_power", "uint16",
			21, "max_power", "uint16",
			22, "total_ascent", "uint16",
			23, "total_descent", "uint16",
			49, "avg_altitude", "altitude",
			50, "max_altitude", "altitude",
			71, "min_altitude", "altitude",
			57, "avg_temperature", "sint8",
			58, "max_temperature", "sint8")

		defMsg("lap", 19,
			253, "timestamp", "date_time",
			0, "event", "enum",
			1, "event_type", "enum",
			25, "sport", "enum",
			23, "intensity", "enum",
			24, "lap_trigger", "enum",
			2, "start_time", "date_time", # Vs timestamp, which was whenever the record was "written"/end of the session
			7, "total_elapsed_time", "duration_msec", # Including pauses
			8, "total_timer_time", "duration_msec", # Excluding pauses
			52, "total_moving_time", "duration_msec",
			9, "total_distance", "distance_cm",
			11,"total_calories", "uint16",
			13, "avg_speed", "mmPerSec",
			14, "max_speed", "mmPerSec",
			15, "avg_heart_rate", "uint8",
			16, "max_heart_rate", "uint8",
			17, "avg_cadence", "uint8", # FIT rolls run and bike cadence into one
			18, "max_cadence", "uint8",
			19, "avg_power", "uint16",
			20, "max_power", "uint16",
			21, "total_ascent", "uint16",
			22, "total_descent", "uint16",
			42, "avg_altitude", "altitude",
			43, "max_altitude", "altitude",
			62, "min_altitude", "altitude",
			50, "avg_temperature", "sint8",
			51, "max_temperature", "sint8"
			)

		defMsg("record", 20,
			253, "timestamp", "date_time",
			0, "position_lat", "semicircles",
			1, "position_long", "semicircles",
			2, "altitude", "altitude",
			3, "heart_rate", "uint8",
			4, "cadence", "uint8",
			5, "distance", "distance_cm",
			6, "speed", "mmPerSec",
			7, "power", "uint16",
			13, "temperature", "sint8",
			33, "calories", "uint16",
			)

		defMsg("event", 21,
			253, "timestamp", "date_time",
			0, "event", "enum",
			1, "event_type", "enum")

		defMsg("device_info", 23,
			253, "timestamp", "date_time",
			0, "device_index", "uint8",
			1, "device_type", "uint8",
			2, "manufacturer", "manufacturer",
			3, "serial_number", "uint32z",
			4, "product", "uint16",
			5, "software_version", "version"
			)

	def _write(self, contents):
		self._result.append(contents)

	def GetResult(self):
		return b''.join(self._result)

	def _defineMessage(self, local_no, global_message, field_names):
		assert local_no < 16 and local_no >= 0
		if set(field_names) - set(global_message.FieldNameList):
			raise ValueError("Attempting to use undefined fields %s" % (set(field_names) - set(global_message.FieldNameList)))
		messageHeader = 0b01000000
		messageHeader = messageHeader | local_no

		local_fields = {}

		arch = 0 # Little-endian
		global_no = global_message.Number
		field_count = len(field_names)
		pack_tuple = (messageHeader, 0, arch, global_no, field_count)
		for field_name in global_message.FieldNameList:
			if field_name in field_names:
				field = global_message.Fields[field_name]
				field_type = self._types[field["Type"]]
				pack_tuple += (field["Number"], field_type.Size, field_type.TypeField)
				local_fields[field_name] = field
		self._definitions[local_no] = FITMessageTemplate(global_message.Name, local_no, local_fields)
		self._write(struct.pack("<BBBHB" + ("BBB" * field_count), *pack_tuple))
		return self._definitions[local_no]


	def GenerateMessage(self, name, **kwargs):
		globalDefn = self._messageTemplates[name]

		# Create a subset of the global message's fields
		localFieldNamesSet = set()
		for fieldName in kwargs:
			localFieldNamesSet.add(fieldName)

		# I'll look at this later
		compressTS = False

		# Are these fields covered by an existing local message type?
		active_definition = None
		for defn_n in self._definitions:
			defn = self._definitions[defn_n]
			if defn.Name == name:
				if defn.FieldNameSet == localFieldNamesSet:
					active_definition = defn

		# If not, create a new local message type with these fields
		if not active_definition:
			active_definition_no = len(self._definitions)
			active_definition = self._defineMessage(active_definition_no, globalDefn, localFieldNamesSet)

		if compressTS and active_definition.Number > 3:
			raise Exception("Can't use compressed timestamp when local message number > 3")

		messageHeader = 0
		if compressTS:
			messageHeader = messageHeader | (1 << 7)
			tsOffsetVal = -1 # TODO
			messageHeader = messageHeader | (active_definition.Number << 4)
		else:
			messageHeader = messageHeader | active_definition.Number

		packResult = [struct.pack("<B", messageHeader)]
		for field_name in active_definition.FieldNameList:
			field = active_definition.Fields[field_name]
			field_type = self._types[field["Type"]]
			try:
				if field_type.Formatter:
					result = field_type.Formatter(kwargs[field_name])
				else:
					sanitized_value = kwargs[field_name]
					if sanitized_value is None:
						result = struct.pack("<" + field_type.PackFormat, field_type.InvalidValue)
					else:
						if field_type.PackFormat in ["B","b", "H", "h", "I", "i"]:
							sanitized_value = round(sanitized_value)
						try:
							result = struct.pack("<" + field_type.PackFormat, sanitized_value)
						except struct.error as e: # I guess more specific exception types were too much to ask for.
							if "<=" in str(e) or "out of range" in str(e):
								result = struct.pack("<" + field_type.PackFormat, field_type.InvalidValue)
							else:
								raise
			except Exception as e:
				raise Exception("Failed packing %s=%s - %s" % (field_name, kwargs[field_name], e))
			packResult.append(result)
		self._write(b''.join(packResult))


class FITIO:

	_sportMap = {
		ActivityType.Other: 0,
		ActivityType.Running: 1,
		ActivityType.Cycling: 2,
		ActivityType.MountainBiking: 2,
		ActivityType.Elliptical: 4,
		ActivityType.Swimming: 5,
	}
	_subSportMap = {
		# ActivityType.MountainBiking: 8 there's an issue with cadence upload and this type with GC, so...
	}
	def _calculateCRC(bytestring, crc=0):
		crc_table = [0x0000, 0xCC01, 0xD801, 0x1400, 0xF001, 0x3C00, 0x2800, 0xE401, 0xA001, 0x6C00, 0x7800, 0xB401, 0x5000, 0x9C01, 0x8801, 0x4400]
		for byte in bytestring:
			tmp = crc_table[crc & 0xF]
			crc = (crc >> 4) & 0x0FFF
			crc = crc ^ tmp ^ crc_table[byte & 0xF]

			tmp = crc_table[crc & 0xF]
			crc = (crc >> 4) & 0x0FFF
			crc = crc ^ tmp ^ crc_table[(byte >> 4) & 0xF]
		return crc

	def _generateHeader(dataLength):
		# We need to call this once the final records are assembled and their length is known, to avoid having to seek back
		header_len = 12
		protocolVer = 16 # The FIT SDK code provides these in a very rounabout fashion
		profileVer = 810
		tag = ".FIT"
		return struct.pack("<BBHI4s", header_len, protocolVer, profileVer, dataLength, tag.encode("ASCII"))

	def Parse(raw_file):
		raise Exception("Not implemented")

	def Dump(act):
		def toUtc(ts):
			if ts.tzinfo:
				return ts.astimezone(pytz.utc).replace(tzinfo=None)
			else:
				raise ValueError("Need TZ data to produce FIT file")
		fmg = FITMessageGenerator()

		creatorInfo = {
			"manufacturer": FITManufacturer.DEVELOPMENT,
			"serial_number": 0,
			"product": 15706
		}
		devInfo = {
			"manufacturer": FITManufacturer.DEVELOPMENT,
			"product": 15706,
			"device_index": 0
		}
		if act.Device:
			# GC can get along with out this, Strava needs it
			devId = DeviceIdentifier.FindEquivalentIdentifierOfType(DeviceIdentifierType.FIT, act.Device.Identifier)
			if devId:
				creatorInfo = {
					"manufacturer": devId.Manufacturer,
					"product": devId.Product,
				}
				devInfo = {
					"manufacturer": devId.Manufacturer,
					"product": devId.Product,
					"device_index": 0 # Required for GC
				}
				if act.Device.Serial:
					creatorInfo["serial_number"] = int(act.Device.Serial) # I suppose some devices might eventually have alphanumeric serial #s
					devInfo["serial_number"] = int(act.Device.Serial)
				if act.Device.VersionMajor is not None:
					assert act.Device.VersionMinor is not None
					devInfo["software_version"] = act.Device.VersionMajor + act.Device.VersionMinor / 100

		fmg.GenerateMessage("file_id", type=FITFileType.Activity, time_created=toUtc(act.StartTime), **creatorInfo)
		fmg.GenerateMessage("device_info", **devInfo)

		sport = FITIO._sportMap[act.Type] if act.Type in FITIO._sportMap else 0
		subSport = FITIO._subSportMap[act.Type] if act.Type in FITIO._subSportMap else 0

		session_stats = {
			"total_elapsed_time": act.EndTime - act.StartTime,
		}

		# FIT doesn't have different fields for this, but it does have a different interpretation - we eventually need to divide by two in the running case.
		# Further complicating the issue is that most sites don't differentiate the two, so they'll end up putting the run cadence back into the bike field.
		use_run_cadence = act.Type in [ActivityType.Running, ActivityType.Walking, ActivityType.Hiking]
		def _resolveRunCadence(bikeCad, runCad):
			nonlocal use_run_cadence
			if use_run_cadence:
				return runCad if runCad is not None else (bikeCad if bikeCad is not None else None)
			else:
				return bikeCad

		def _mapStat(dict, key, value):
			if value is not None:
				dict[key] = value

		_mapStat(session_stats, "total_moving_time", act.Stats.MovingTime.asUnits(ActivityStatisticUnit.Seconds).Value)
		_mapStat(session_stats, "total_timer_time", act.Stats.TimerTime.asUnits(ActivityStatisticUnit.Seconds).Value)
		_mapStat(session_stats, "total_distance", act.Stats.Distance.asUnits(ActivityStatisticUnit.Meters).Value)
		_mapStat(session_stats, "total_calories", act.Stats.Energy.asUnits(ActivityStatisticUnit.Kilocalories).Value)
		_mapStat(session_stats, "avg_speed", act.Stats.Speed.asUnits(ActivityStatisticUnit.MetersPerSecond).Average)
		_mapStat(session_stats, "max_speed", act.Stats.Speed.asUnits(ActivityStatisticUnit.MetersPerSecond).Max)
		_mapStat(session_stats, "avg_heart_rate", act.Stats.HR.Average)
		_mapStat(session_stats, "max_heart_rate", act.Stats.HR.Max)
		_mapStat(session_stats, "avg_cadence", _resolveRunCadence(act.Stats.Cadence.Average, act.Stats.RunCadence.Average))
		_mapStat(session_stats, "max_cadence", _resolveRunCadence(act.Stats.Cadence.Max, act.Stats.RunCadence.Max))
		_mapStat(session_stats, "avg_power", act.Stats.Power.Average)
		_mapStat(session_stats, "max_power", act.Stats.Power.Max)
		_mapStat(session_stats, "total_ascent", act.Stats.Elevation.asUnits(ActivityStatisticUnit.Meters).Gain)
		_mapStat(session_stats, "total_descent", act.Stats.Elevation.asUnits(ActivityStatisticUnit.Meters).Loss)
		_mapStat(session_stats, "avg_altitude", act.Stats.Elevation.asUnits(ActivityStatisticUnit.Meters).Average)
		_mapStat(session_stats, "max_altitude", act.Stats.Elevation.asUnits(ActivityStatisticUnit.Meters).Max)
		_mapStat(session_stats, "min_altitude", act.Stats.Elevation.asUnits(ActivityStatisticUnit.Meters).Min)
		_mapStat(session_stats, "avg_temperature", act.Stats.Temperature.asUnits(ActivityStatisticUnit.DegreesCelcius).Average)
		_mapStat(session_stats, "max_temperature", act.Stats.Temperature.asUnits(ActivityStatisticUnit.DegreesCelcius).Max)

		inPause = False
		for lap in act.Laps:
			for wp in lap.Waypoints:
				if wp.Type == WaypointType.Resume and inPause:
					fmg.GenerateMessage("event", timestamp=toUtc(wp.Timestamp), event=FITEvent.Timer, event_type=FITEventType.Start)
					inPause = False
				elif wp.Type == WaypointType.Pause and not inPause:
					fmg.GenerateMessage("event", timestamp=toUtc(wp.Timestamp), event=FITEvent.Timer, event_type=FITEventType.Stop)
					inPause = True

				rec_contents = {"timestamp": toUtc(wp.Timestamp)}
				if wp.Location:
					rec_contents.update({"position_lat": wp.Location.Latitude, "position_long": wp.Location.Longitude})
					if wp.Location.Altitude is not None:
						rec_contents.update({"altitude": wp.Location.Altitude})
				if wp.HR is not None:
					rec_contents.update({"heart_rate": wp.HR})
				if wp.RunCadence is not None:
					rec_contents.update({"cadence": wp.RunCadence})
				if wp.Cadence is not None:
					rec_contents.update({"cadence": wp.Cadence})
				if wp.Power is not None:
					rec_contents.update({"power": wp.Power})
				if wp.Temp is not None:
					rec_contents.update({"temperature": wp.Temp})
				if wp.Calories is not None:
					rec_contents.update({"calories": wp.Calories})
				if wp.Distance is not None:
					rec_contents.update({"distance": wp.Distance})
				if wp.Speed is not None:
					rec_contents.update({"speed": wp.Speed})
				fmg.GenerateMessage("record", **rec_contents)
			# Man, I love copy + paste and multi-cursor editing
			# But seriously, I'm betting that, some time down the road, a stat will pop up in X but not in Y, so I won't feel so bad about the C&P abuse
			lap_stats = {}
			_mapStat(lap_stats, "total_elapsed_time", lap.EndTime - lap.StartTime)
			_mapStat(lap_stats, "total_moving_time", lap.Stats.MovingTime.asUnits(ActivityStatisticUnit.Seconds).Value)
			_mapStat(lap_stats, "total_timer_time", lap.Stats.TimerTime.asUnits(ActivityStatisticUnit.Seconds).Value)
			_mapStat(lap_stats, "total_distance", lap.Stats.Distance.asUnits(ActivityStatisticUnit.Meters).Value)
			_mapStat(lap_stats, "total_calories", lap.Stats.Energy.asUnits(ActivityStatisticUnit.Kilocalories).Value)
			_mapStat(lap_stats, "avg_speed", lap.Stats.Speed.asUnits(ActivityStatisticUnit.MetersPerSecond).Average)
			_mapStat(lap_stats, "max_speed", lap.Stats.Speed.asUnits(ActivityStatisticUnit.MetersPerSecond).Max)
			_mapStat(lap_stats, "avg_heart_rate", lap.Stats.HR.Average)
			_mapStat(lap_stats, "max_heart_rate", lap.Stats.HR.Max)
			_mapStat(lap_stats, "avg_cadence", _resolveRunCadence(lap.Stats.Cadence.Average, lap.Stats.RunCadence.Average))
			_mapStat(lap_stats, "max_cadence", _resolveRunCadence(lap.Stats.Cadence.Max, lap.Stats.RunCadence.Max))
			_mapStat(lap_stats, "avg_power", lap.Stats.Power.Average)
			_mapStat(lap_stats, "max_power", lap.Stats.Power.Max)
			_mapStat(lap_stats, "total_ascent", lap.Stats.Elevation.asUnits(ActivityStatisticUnit.Meters).Gain)
			_mapStat(lap_stats, "total_descent", lap.Stats.Elevation.asUnits(ActivityStatisticUnit.Meters).Loss)
			_mapStat(lap_stats, "avg_altitude", lap.Stats.Elevation.asUnits(ActivityStatisticUnit.Meters).Average)
			_mapStat(lap_stats, "max_altitude", lap.Stats.Elevation.asUnits(ActivityStatisticUnit.Meters).Max)
			_mapStat(lap_stats, "min_altitude", lap.Stats.Elevation.asUnits(ActivityStatisticUnit.Meters).Min)
			_mapStat(lap_stats, "avg_temperature", lap.Stats.Temperature.asUnits(ActivityStatisticUnit.DegreesCelcius).Average)
			_mapStat(lap_stats, "max_temperature", lap.Stats.Temperature.asUnits(ActivityStatisticUnit.DegreesCelcius).Max)

			# These are some really... stupid lookups.
			# Oh well, futureproofing.
			lap_stats["intensity"] = ({
					LapIntensity.Active: FITLapIntensity.Active,
					LapIntensity.Rest: FITLapIntensity.Rest,
					LapIntensity.Warmup: FITLapIntensity.Warmup,
					LapIntensity.Cooldown: FITLapIntensity.Cooldown,
				})[lap.Intensity]
			lap_stats["lap_trigger"] = ({
					LapTriggerMethod.Manual: FITLapTriggerMethod.Manual,
					LapTriggerMethod.Time: FITLapTriggerMethod.Time,
					LapTriggerMethod.Distance: FITLapTriggerMethod.Distance,
					LapTriggerMethod.PositionStart: FITLapTriggerMethod.PositionStart,
					LapTriggerMethod.PositionLap: FITLapTriggerMethod.PositionLap,
					LapTriggerMethod.PositionWaypoint: FITLapTriggerMethod.PositionWaypoint,
					LapTriggerMethod.PositionMarked: FITLapTriggerMethod.PositionMarked,
					LapTriggerMethod.SessionEnd: FITLapTriggerMethod.SessionEnd,
					LapTriggerMethod.FitnessEquipment: FITLapTriggerMethod.FitnessEquipment,
				})[lap.Trigger]
			fmg.GenerateMessage("lap", timestamp=toUtc(lap.EndTime), start_time=toUtc(lap.StartTime), event=FITEvent.Lap, event_type=FITEventType.Start, sport=sport, **lap_stats)


		# These need to be at the end for Strava
		fmg.GenerateMessage("session", timestamp=toUtc(act.EndTime), start_time=toUtc(act.StartTime), sport=sport, sub_sport=subSport, event=FITEvent.Timer, event_type=FITEventType.Start, **session_stats)
		fmg.GenerateMessage("activity", timestamp=toUtc(act.EndTime), local_timestamp=act.EndTime.replace(tzinfo=None), num_sessions=1, type=FITActivityType.GENERIC, event=FITEvent.Activity, event_type=FITEventType.Stop)

		records = fmg.GetResult()
		header = FITIO._generateHeader(len(records))
		crc = FITIO._calculateCRC(records, FITIO._calculateCRC(header))
		return header + records + struct.pack("<H", crc)

########NEW FILE########
__FILENAME__ = garminconnect
from tapiriik.settings import WEB_ROOT, HTTP_SOURCE_ADDR, GARMIN_CONNECT_USER_WATCH_ACCOUNTS
from tapiriik.services.service_base import ServiceAuthenticationType, ServiceBase
from tapiriik.services.service_record import ServiceRecord
from tapiriik.services.interchange import UploadedActivity, ActivityType, ActivityStatistic, ActivityStatisticUnit, Waypoint, Location, Lap
from tapiriik.services.api import APIException, APIWarning, APIExcludeActivity, UserException, UserExceptionType
from tapiriik.services.statistic_calculator import ActivityStatisticCalculator
from tapiriik.services.tcx import TCXIO
from tapiriik.services.gpx import GPXIO
from tapiriik.services.fit import FITIO
from tapiriik.services.sessioncache import SessionCache
from tapiriik.database import cachedb, db

from django.core.urlresolvers import reverse
import pytz
from datetime import datetime, timedelta
import requests
import os
import math
import logging
import time
import json
import re
import random
from urllib.parse import urlencode
logger = logging.getLogger(__name__)

class GarminConnectService(ServiceBase):
    ID = "garminconnect"
    DisplayName = "Garmin Connect"
    DisplayAbbreviation = "GC"
    AuthenticationType = ServiceAuthenticationType.UsernamePassword
    RequiresExtendedAuthorizationDetails = True
    PartialSyncRequiresTrigger = len(GARMIN_CONNECT_USER_WATCH_ACCOUNTS) > 0
    PartialSyncTriggerPollInterval = timedelta(minutes=20)
    PartialSyncTriggerPollMultiple = len(GARMIN_CONNECT_USER_WATCH_ACCOUNTS.keys())

    ConfigurationDefaults = {
        "WatchUserKey": None,
        "WatchUserLastID": 0
    }

    _activityMappings = {
                                "running": ActivityType.Running,
                                "cycling": ActivityType.Cycling,
                                "mountain_biking": ActivityType.MountainBiking,
                                "walking": ActivityType.Walking,
                                "hiking": ActivityType.Hiking,
                                "resort_skiing_snowboarding": ActivityType.DownhillSkiing,
                                "cross_country_skiing": ActivityType.CrossCountrySkiing,
                                "skate_skiing": ActivityType.CrossCountrySkiing, # Well, it ain't downhill?
                                "backcountry_skiing_snowboarding": ActivityType.CrossCountrySkiing,  # ish
                                "skating": ActivityType.Skating,
                                "swimming": ActivityType.Swimming,
                                "rowing": ActivityType.Rowing,
                                "elliptical": ActivityType.Elliptical,
                                "fitness_equipment": ActivityType.Gym,
                                "all": ActivityType.Other  # everything will eventually resolve to this
    }

    _reverseActivityMappings = {  # Removes ambiguities when mapping back to their activity types
                                "running": ActivityType.Running,
                                "cycling": ActivityType.Cycling,
                                "mountain_biking": ActivityType.MountainBiking,
                                "walking": ActivityType.Walking,
                                "hiking": ActivityType.Hiking,
                                "resort_skiing_snowboarding": ActivityType.DownhillSkiing,
                                "cross_country_skiing": ActivityType.CrossCountrySkiing,
                                "skating": ActivityType.Skating,
                                "swimming": ActivityType.Swimming,
                                "rowing": ActivityType.Rowing,
                                "elliptical": ActivityType.Elliptical,
                                "fitness_equipment": ActivityType.Gym,
                                "other": ActivityType.Other  # I guess? (vs. "all" that is)
    }

    SupportedActivities = list(_activityMappings.values())

    SupportsHR = SupportsCadence = True

    _sessionCache = SessionCache(lifetime=timedelta(minutes=30), freshen_on_get=True)

    _unitMap = {
        "mph": ActivityStatisticUnit.MilesPerHour,
        "kph": ActivityStatisticUnit.KilometersPerHour,
        "hmph": ActivityStatisticUnit.HectometersPerHour,
        "hydph": ActivityStatisticUnit.HundredYardsPerHour,
        "celcius": ActivityStatisticUnit.DegreesCelcius,
        "fahrenheit": ActivityStatisticUnit.DegreesFahrenheit,
        "mile": ActivityStatisticUnit.Miles,
        "kilometer": ActivityStatisticUnit.Kilometers,
        "foot": ActivityStatisticUnit.Feet,
        "meter": ActivityStatisticUnit.Meters,
        "yard": ActivityStatisticUnit.Yards,
        "kilocalorie": ActivityStatisticUnit.Kilocalories,
        "bpm": ActivityStatisticUnit.BeatsPerMinute,
        "stepsPerMinute": ActivityStatisticUnit.DoubledStepsPerMinute,
        "rpm": ActivityStatisticUnit.RevolutionsPerMinute,
        "watt": ActivityStatisticUnit.Watts,
        "second": ActivityStatisticUnit.Seconds,
        "ms": ActivityStatisticUnit.Milliseconds
    }

    def __init__(self):
        cachedHierarchy = cachedb.gc_type_hierarchy.find_one()
        if not cachedHierarchy:
            rawHierarchy = requests.get("http://connect.garmin.com/proxy/activity-service-1.2/json/activity_types").text
            self._activityHierarchy = json.loads(rawHierarchy)["dictionary"]
            cachedb.gc_type_hierarchy.insert({"Hierarchy": rawHierarchy})
        else:
            self._activityHierarchy = json.loads(cachedHierarchy["Hierarchy"])["dictionary"]
        rate_lock_path = "/tmp/gc_rate.%s.lock" % HTTP_SOURCE_ADDR
        # Ensure the rate lock file exists (...the easy way)
        open(rate_lock_path, "a").close()
        self._rate_lock = open(rate_lock_path, "r+")

    def _rate_limit(self):
        import fcntl, struct, time
        min_period = 1  # I appear to been banned from Garmin Connect while determining this.
        print("Waiting for lock")
        fcntl.flock(self._rate_lock,fcntl.LOCK_EX)
        try:
            print("Have lock")
            self._rate_lock.seek(0)
            last_req_start = self._rate_lock.read()
            if not last_req_start:
                last_req_start = 0
            else:
                last_req_start = float(last_req_start)

            wait_time = max(0, min_period - (time.time() - last_req_start))
            time.sleep(wait_time)

            self._rate_lock.seek(0)
            self._rate_lock.write(str(time.time()))
            self._rate_lock.flush()

            print("Rate limited for %f" % wait_time)
        finally:
            fcntl.flock(self._rate_lock,fcntl.LOCK_UN)

    def _get_session(self, record=None, email=None, password=None, skip_cache=False):
        from tapiriik.auth.credential_storage import CredentialStore
        cached = self._sessionCache.Get(record.ExternalID if record else email)
        if cached and not skip_cache:
                return cached
        if record:
            #  longing for C style overloads...
            password = CredentialStore.Decrypt(record.ExtendedAuthorization["Password"])
            email = CredentialStore.Decrypt(record.ExtendedAuthorization["Email"])

        session = requests.Session()
        self._rate_limit()
        gcPreResp = session.get("http://connect.garmin.com/", allow_redirects=False)
        # New site gets this redirect, old one does not
        if gcPreResp.status_code == 200:
            self._rate_limit()
            gcPreResp = session.get("https://connect.garmin.com/signin", allow_redirects=False)
            req_count = int(re.search("j_id(\d+)", gcPreResp.text).groups(1)[0])
            params = {"login": "login", "login:loginUsernameField": email, "login:password": password, "login:signInButton": "Sign In"}
            auth_retries = 3 # Did I mention Garmin Connect is silly?
            for retries in range(auth_retries):
                params["javax.faces.ViewState"] = "j_id%d" % req_count
                req_count += 1
                self._rate_limit()
                resp = session.post("https://connect.garmin.com/signin", data=params, allow_redirects=False)
                if resp.status_code >= 500 and resp.status_code < 600:
                    raise APIException("Remote API failure")
                if resp.status_code != 302:  # yep
                    if "errorMessage" in resp.text:
                        if retries < auth_retries - 1:
                            time.sleep(1)
                            continue
                        else:
                            raise APIException("Invalid login", block=True, user_exception=UserException(UserExceptionType.Authorization, intervention_required=True))
                    else:
                        raise APIException("Mystery login error %s" % resp.text)
                break
        elif gcPreResp.status_code == 302:
            # JSIG CAS, cool I guess.
            # Not quite OAuth though, so I'll continue to collect raw credentials.
            # Commented stuff left in case this ever breaks because of missing parameters...
            data = {
                "username": email,
                "password": password,
                "_eventId": "submit",
                "embed": "true",
                # "displayNameRequired": "false"
            }
            params = {
                "service": "http://connect.garmin.com/post-auth/login",
                # "redirectAfterAccountLoginUrl": "http://connect.garmin.com/post-auth/login",
                # "redirectAfterAccountCreationUrl": "http://connect.garmin.com/post-auth/login",
                # "webhost": "olaxpw-connect00.garmin.com",
                "clientId": "GarminConnect",
                # "gauthHost": "https://sso.garmin.com/sso",
                # "rememberMeShown": "true",
                # "rememberMeChecked": "false",
                "consumeServiceTicket": "false",
                # "id": "gauth-widget",
                # "embedWidget": "false",
                # "cssUrl": "https://static.garmincdn.com/com.garmin.connect/ui/src-css/gauth-custom.css",
                # "source": "http://connect.garmin.com/en-US/signin",
                # "createAccountShown": "true",
                # "openCreateAccount": "false",
                # "usernameShown": "true",
                # "displayNameShown": "false",
                # "initialFocus": "true",
                # "locale": "en"
            }
            # I may never understand what motivates people to mangle a perfectly good protocol like HTTP in the ways they do...
            preResp = session.get("https://sso.garmin.com/sso/login", params=params)
            if preResp.status_code != 200:
                raise APIException("SSO prestart error %s %s" % (preResp.status_code, preResp.text))
            data["lt"] = re.search("name=\"lt\"\s+value=\"([^\"]+)\"", preResp.text).groups(1)[0]

            ssoResp = session.post("https://sso.garmin.com/sso/login", params=params, data=data, allow_redirects=False)
            if ssoResp.status_code != 200:
                raise APIException("SSO error %s %s" % (ssoResp.status_code, ssoResp.text))

            ticket_match = re.search("ticket=([^']+)'", ssoResp.text)
            if not ticket_match:
                raise APIException("Invalid login", block=True, user_exception=UserException(UserExceptionType.Authorization, intervention_required=True))
            ticket = ticket_match.groups(1)[0]

            # ...AND WE'RE NOT DONE YET!

            self._rate_limit()
            gcRedeemResp1 = session.get("http://connect.garmin.com/post-auth/login", params={"ticket": ticket}, allow_redirects=False)
            if gcRedeemResp1.status_code != 302:
                raise APIException("GC redeem 1 error %s %s" % (gcRedeemResp1.status_code, gcRedeemResp1.text))

            self._rate_limit()
            gcRedeemResp2 = session.get(gcRedeemResp1.headers["location"], allow_redirects=False)
            if gcRedeemResp2.status_code != 302:
                raise APIException("GC redeem 2 error %s %s" % (gcRedeemResp2.status_code, gcRedeemResp2.text))

        else:
            raise APIException("Unknown GC prestart response %s %s" % (gcPreResp.status_code, gcPreResp.text))

        self._sessionCache.Set(record.ExternalID if record else email, session)


        return session

    def WebInit(self):
        self.UserAuthorizationURL = WEB_ROOT + reverse("auth_simple", kwargs={"service": self.ID})

    def Authorize(self, email, password):
        from tapiriik.auth.credential_storage import CredentialStore
        session = self._get_session(email=email, password=password)
        # TODO: http://connect.garmin.com/proxy/userprofile-service/socialProfile/ has the proper immutable user ID, not that anyone ever changes this one...
        self._rate_limit()
        username = session.get("http://connect.garmin.com/user/username").json()["username"]
        if not len(username):
            raise APIException("Unable to retrieve username", block=True, user_exception=UserException(UserExceptionType.Authorization, intervention_required=True))
        return (username, {}, {"Email": CredentialStore.Encrypt(email), "Password": CredentialStore.Encrypt(password)})


    def _resolveActivityType(self, act_type):
        # Mostly there are two levels of a hierarchy, so we don't really need this as the parent is included in the listing.
        # But maybe they'll change that some day?
        while act_type not in self._activityMappings:
            try:
                act_type = [x["parent"]["key"] for x in self._activityHierarchy if x["key"] == act_type][0]
            except IndexError:
                raise ValueError("Activity type not found in activity hierarchy")
        return self._activityMappings[act_type]

    def DownloadActivityList(self, serviceRecord, exhaustive=False):
        #http://connect.garmin.com/proxy/activity-search-service-1.0/json/activities?&start=0&limit=50
        session = self._get_session(record=serviceRecord)
        page = 1
        pageSz = 100
        activities = []
        exclusions = []
        while True:
            logger.debug("Req with " + str({"start": (page - 1) * pageSz, "limit": pageSz}))
            self._rate_limit()

            retried_auth = False
            while True:
                res = session.get("http://connect.garmin.com/proxy/activity-search-service-1.0/json/activities", params={"start": (page - 1) * pageSz, "limit": pageSz})
                # It's 10 PM and I have no clue why it's throwing these errors, maybe we just need to log in again?
                if res.status_code == 403 and not retried_auth:
                    retried_auth = True
                    session = self._get_session(serviceRecord, skip_cache=True)
                else:
                    break
            try:
                res = res.json()["results"]
            except ValueError:
                res_txt = res.text # So it can capture in the log message
                raise APIException("Parse failure in GC list resp: %s" % res.status_code)
            if "activities" not in res:
                break  # No activities on this page - empty account.
            for act in res["activities"]:
                act = act["activity"]
                if "sumDistance" not in act:
                    exclusions.append(APIExcludeActivity("No distance", activityId=act["activityId"], userException=UserException(UserExceptionType.Corrupt)))
                    continue
                activity = UploadedActivity()

                # Don't really know why sumSampleCountTimestamp doesn't appear in swim activities - they're definitely timestamped...
                activity.Stationary = "sumSampleCountSpeed" not in act and "sumSampleCountTimestamp" not in act
                activity.GPS = "endLatitude" in act

                activity.Private = act["privacy"]["key"] == "private"

                try:
                    activity.TZ = pytz.timezone(act["activityTimeZone"]["key"])
                except pytz.exceptions.UnknownTimeZoneError:
                    activity.TZ = pytz.FixedOffset(float(act["activityTimeZone"]["offset"]) * 60)

                logger.debug("Name " + act["activityName"]["value"] + ":")
                if len(act["activityName"]["value"].strip()) and act["activityName"]["value"] != "Untitled": # This doesn't work for internationalized accounts, oh well.
                    activity.Name = act["activityName"]["value"]

                if len(act["activityDescription"]["value"].strip()):
                    activity.Notes = act["activityDescription"]["value"]

                # beginTimestamp/endTimestamp is in UTC
                activity.StartTime = pytz.utc.localize(datetime.utcfromtimestamp(float(act["beginTimestamp"]["millis"])/1000))
                if "sumElapsedDuration" in act:
                    activity.EndTime = activity.StartTime + timedelta(0, round(float(act["sumElapsedDuration"]["value"])))
                elif "sumDuration" in act:
                    activity.EndTime = activity.StartTime + timedelta(minutes=float(act["sumDuration"]["minutesSeconds"].split(":")[0]), seconds=float(act["sumDuration"]["minutesSeconds"].split(":")[1]))
                else:
                    activity.EndTime = pytz.utc.localize(datetime.utcfromtimestamp(float(act["endTimestamp"]["millis"])/1000))
                logger.debug("Activity s/t " + str(activity.StartTime) + " on page " + str(page))
                activity.AdjustTZ()

                # TODO: fix the distance stats to account for the fact that this incorrectly reported km instead of meters for the longest time.
                activity.Stats.Distance = ActivityStatistic(self._unitMap[act["sumDistance"]["uom"]], value=float(act["sumDistance"]["value"]))

                activity.Type = self._resolveActivityType(act["activityType"]["key"])

                activity.CalculateUID()
                
                activity.ServiceData = {"ActivityID": int(act["activityId"])}

                activities.append(activity)
            logger.debug("Finished page " + str(page) + " of " + str(res["search"]["totalPages"]))
            if not exhaustive or int(res["search"]["totalPages"]) == page:
                break
            else:
                page += 1
        return activities, exclusions

    def _downloadActivitySummary(self, serviceRecord, activity):
        activityID = activity.ServiceData["ActivityID"]
        session = self._get_session(record=serviceRecord)
        self._rate_limit()
        res = session.get("http://connect.garmin.com/proxy/activity-service-1.3/json/activity/" + str(activityID))



        try:
            raw_data = res.json()
        except ValueError:
            raise APIException("Failure downloading activity summary %s:%s" % (res.status_code, res.text))
        stat_map = {}
        def mapStat(gcKey, statKey, type):
            stat_map[gcKey] = {
                "key": statKey,
                "attr": type
            }

        def applyStats(gc_dict, stats_obj):
            for gc_key, stat in stat_map.items():
                if gc_key in gc_dict:
                    value = float(gc_dict[gc_key]["value"])
                    units = self._unitMap[gc_dict[gc_key]["uom"]]
                    if math.isinf(value):
                        continue # GC returns the minimum speed as "-Infinity" instead of 0 some times :S
                    getattr(stats_obj, stat["key"]).update(ActivityStatistic(units, **({stat["attr"]: value})))

        mapStat("SumMovingDuration", "MovingTime", "value")
        mapStat("SumDuration", "TimerTime", "value")
        mapStat("SumDistance", "Distance", "value")
        mapStat("MinSpeed", "Speed", "min")
        mapStat("MaxSpeed", "Speed", "max")
        mapStat("WeightedMeanSpeed", "Speed", "avg")
        mapStat("MinAirTemperature", "Temperature", "min")
        mapStat("MaxAirTemperature", "Temperature", "max")
        mapStat("WeightedMeanAirTemperature", "Temperature", "avg")
        mapStat("SumEnergy", "Energy", "value")
        mapStat("MaxHeartRate", "HR", "max")
        mapStat("WeightedMeanHeartRate", "HR", "avg")
        mapStat("MaxDoubleCadence", "RunCadence", "max")
        mapStat("WeightedMeanDoubleCadence", "RunCadence", "avg")
        mapStat("MaxBikeCadence", "Cadence", "max")
        mapStat("WeightedMeanBikeCadence", "Cadence", "avg")
        mapStat("MinPower", "Power", "min")
        mapStat("MaxPower", "Power", "max")
        mapStat("WeightedMeanPower", "Power", "avg")
        mapStat("MinElevation", "Elevation", "min")
        mapStat("MaxElevation", "Elevation", "max")
        mapStat("GainElevation", "Elevation", "gain")
        mapStat("LossElevation", "Elevation", "loss")

        applyStats(raw_data["activity"]["activitySummary"], activity.Stats)

        for lap_data in raw_data["activity"]["totalLaps"]["lapSummaryList"]:
            lap = Lap()
            if "BeginTimestamp" in lap_data:
                lap.StartTime = pytz.utc.localize(datetime.utcfromtimestamp(float(lap_data["BeginTimestamp"]["value"]) / 1000))
            if "EndTimestamp" in lap_data:
                lap.EndTime = pytz.utc.localize(datetime.utcfromtimestamp(float(lap_data["EndTimestamp"]["value"]) / 1000))

            elapsed_duration = None
            if "SumElapsedDuration" in lap_data:
                elapsed_duration = timedelta(seconds=round(float(lap_data["SumElapsedDuration"]["value"])))
            elif "SumDuration" in lap_data:
                elapsed_duration = timedelta(seconds=round(float(lap_data["SumDuration"]["value"])))

            if lap.StartTime and elapsed_duration:
                # Always recalculate end time based on duration, if we have the start time
                lap.EndTime = lap.StartTime + elapsed_duration
            if not lap.StartTime and lap.EndTime and elapsed_duration:
                # Sometimes calculate start time based on duration
                lap.StartTime = lap.EndTime - elapsed_duration

            if not lap.StartTime or not lap.EndTime:
                # Garmin Connect is weird.
                raise APIExcludeActivity("Activity lap has no BeginTimestamp or EndTimestamp", userException=UserException(UserExceptionType.Corrupt))

            applyStats(lap_data, lap.Stats)
            activity.Laps.append(lap)

        # In Garmin Land, max can be smaller than min for this field :S
        if activity.Stats.Power.Max is not None and activity.Stats.Power.Min is not None and activity.Stats.Power.Min > activity.Stats.Power.Max:
            activity.Stats.Power.Min = None

    def DownloadActivity(self, serviceRecord, activity):
        # First, download the summary stats and lap stats
        self._downloadActivitySummary(serviceRecord, activity)

        if len(activity.Laps) == 1:
            activity.Stats = activity.Laps[0].Stats # They must be identical to pass the verification

        if activity.Stationary:
            # Nothing else to download
            return activity

        # https://connect.garmin.com/proxy/activity-service-1.3/json/activityDetails/####
        activityID = activity.ServiceData["ActivityID"]
        session = self._get_session(record=serviceRecord)
        self._rate_limit()
        res = session.get("http://connect.garmin.com/proxy/activity-service-1.3/json/activityDetails/" + str(activityID) + "?maxSize=999999999")
        try:
            raw_data = res.json()["com.garmin.activity.details.json.ActivityDetails"]
        except ValueError:
            raise APIException("Activity data parse error for %s: %s" % (res.status_code, res.text))

        if "measurements" not in raw_data:
            activity.Stationary = True # We were wrong, oh well
            return activity

        attrs_map = {}
        def _map_attr(gc_key, wp_key, units, in_location=False, is_timestamp=False):
            attrs_map[gc_key] = {
                "key": wp_key,
                "to_units": units,
                "in_location": in_location, # Blegh
                "is_timestamp": is_timestamp # See above
            }

        _map_attr("directSpeed", "Speed", ActivityStatisticUnit.MetersPerSecond)
        _map_attr("sumDistance", "Distance", ActivityStatisticUnit.Meters)
        _map_attr("directHeartRate", "HR", ActivityStatisticUnit.BeatsPerMinute)
        _map_attr("directBikeCadence", "Cadence", ActivityStatisticUnit.RevolutionsPerMinute)
        _map_attr("directDoubleCadence", "RunCadence", ActivityStatisticUnit.StepsPerMinute) # 2*x mystery solved
        _map_attr("directAirTemperature", "Temp", ActivityStatisticUnit.DegreesCelcius)
        _map_attr("directPower", "Power", ActivityStatisticUnit.Watts)
        _map_attr("directElevation", "Altitude", ActivityStatisticUnit.Meters, in_location=True)
        _map_attr("directLatitude", "Latitude", None, in_location=True)
        _map_attr("directLongitude", "Longitude", None, in_location=True)
        _map_attr("directTimestamp", "Timestamp", None, is_timestamp=True)

        # Figure out which metrics we'll be seeing in this activity
        attrs_indexed = {}
        attr_count = len(raw_data["measurements"])
        for measurement in raw_data["measurements"]:
            key = measurement["key"]
            if key in attrs_map:
                if attrs_map[key]["to_units"]:
                    attrs_map[key]["from_units"] = self._unitMap[measurement["unit"]]
                    if attrs_map[key]["to_units"] == attrs_map[key]["from_units"]:
                        attrs_map[key]["to_units"] = attrs_map[key]["from_units"] = None
                attrs_indexed[measurement["metricsIndex"]] = attrs_map[key]

        # Process the data frames
        frame_idx = 0
        active_lap_idx = 0
        for frame in raw_data["metrics"]:
            wp = Waypoint()
            for idx, attr in attrs_indexed.items():
                value = frame["metrics"][idx]
                target_obj = wp
                if attr["in_location"]:
                    if not wp.Location:
                        wp.Location = Location()
                    target_obj = wp.Location

                # Handle units
                if attr["is_timestamp"]:
                    value = pytz.utc.localize(datetime.utcfromtimestamp(value / 1000))
                elif attr["to_units"]:
                    value = ActivityStatistic.convertValue(value, attr["from_units"], attr["to_units"])

                # Write the value (can't use __dict__ because __slots__)
                setattr(target_obj, attr["key"], value)

            # Fix up lat/lng being zero (which appear to represent missing coords)
            if wp.Location and wp.Location.Latitude == 0 and wp.Location.Longitude == 0:
                wp.Location.Latitude = None
                wp.Location.Longitude = None
            # Bump the active lap if required
            while (active_lap_idx < len(activity.Laps) - 1 and # Not the last lap
                   activity.Laps[active_lap_idx + 1].StartTime <= wp.Timestamp):
                active_lap_idx += 1
            activity.Laps[active_lap_idx].Waypoints.append(wp)
            frame_idx += 1

        return activity

    def UploadActivity(self, serviceRecord, activity):
        #/proxy/upload-service-1.1/json/upload/.fit
        fit_file = FITIO.Dump(activity)
        files = {"data": ("tap-sync-" + str(os.getpid()) + "-" + activity.UID + ".fit", fit_file)}
        session = self._get_session(record=serviceRecord)
        self._rate_limit()
        res = session.post("http://connect.garmin.com/proxy/upload-service-1.1/json/upload/.fit", files=files)
        res = res.json()["detailedImportResult"]

        if len(res["successes"]) == 0:
            raise APIException("Unable to upload activity %s" % res)
        if len(res["successes"]) > 1:
            raise APIException("Uploaded succeeded, resulting in too many activities")
        actid = res["successes"][0]["internalId"]

        name = activity.Name # Capture in logs
        notes = activity.Notes
        encoding_headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"} # GC really, really needs this part, otherwise it throws obscure errors like "Invalid signature for signature method HMAC-SHA1"
        warnings = []
        try:
            if activity.Name and activity.Name.strip():
                self._rate_limit()
                res = session.post("http://connect.garmin.com/proxy/activity-service-1.2/json/name/" + str(actid), data=urlencode({"value": activity.Name}).encode("UTF-8"), headers=encoding_headers)
                try:
                    res = res.json()
                except:
                    raise APIWarning("Activity name request failed - %s" % res.text)
                if "display" not in res or res["display"]["value"] != activity.Name:
                    raise APIWarning("Unable to set activity name")
        except APIWarning as e:
            warnings.append(e)

        try:
            if activity.Notes and activity.Notes.strip():
                self._rate_limit()
                res = session.post("http://connect.garmin.com/proxy/activity-service-1.2/json/description/" + str(actid), data=urlencode({"value": activity.Notes}).encode("UTF-8"), headers=encoding_headers)
                try:
                    res = res.json()
                except:
                    raise APIWarning("Activity notes request failed - %s" % res.text)
                if "display" not in res or res["display"]["value"] != activity.Notes:
                    raise APIWarning("Unable to set activity notes")
        except APIWarning as e:
            warnings.append(e)

        try:
            if activity.Type not in [ActivityType.Running, ActivityType.Cycling, ActivityType.Other]:
                # Set the legit activity type - whatever it is, it's not supported by the TCX schema
                acttype = [k for k, v in self._reverseActivityMappings.items() if v == activity.Type]
                if len(acttype) == 0:
                    raise APIWarning("GarminConnect does not support activity type " + activity.Type)
                else:
                    acttype = acttype[0]
                self._rate_limit()
                res = session.post("http://connect.garmin.com/proxy/activity-service-1.2/json/type/" + str(actid), data={"value": acttype})
                res = res.json()
                if "activityType" not in res or res["activityType"]["key"] != acttype:
                    raise APIWarning("Unable to set activity type")
        except APIWarning as e:
            warnings.append(e)

        try:
            if activity.Private:
                self._rate_limit()
                res = session.post("http://connect.garmin.com/proxy/activity-service-1.2/json/privacy/" + str(actid), data={"value": "private"})
                res = res.json()
                if "definition" not in res or res["definition"]["key"] != "private":
                    raise APIWarning("Unable to set activity privacy")
        except APIWarning as e:
            warnings.append(e)

        if len(warnings):
            raise APIWarning(str(warnings)) # Meh
        return actid

    def _user_watch_user(self, serviceRecord):
        if not serviceRecord.GetConfiguration()["WatchUserKey"]:
            user_key = random.choice(list(GARMIN_CONNECT_USER_WATCH_ACCOUNTS.keys()))
            logger.info("Assigning %s a new watch user %s" % (serviceRecord.ExternalID, user_key))
            serviceRecord.SetConfiguration({"WatchUserKey": user_key})
            return GARMIN_CONNECT_USER_WATCH_ACCOUNTS[user_key]
        else:
            return GARMIN_CONNECT_USER_WATCH_ACCOUNTS[serviceRecord.GetConfiguration()["WatchUserKey"]]

    def SubscribeToPartialSyncTrigger(self, serviceRecord):
        # PUT http://connect.garmin.com/proxy/userprofile-service/connection/request/cpfair
        # (the poll worker finishes the connection)
        user_name = self._user_watch_user(serviceRecord)["Name"]
        logger.info("Requesting connection to %s from %s" % (user_name, serviceRecord.ExternalID))
        self._rate_limit()
        resp = self._get_session(record=serviceRecord).put("http://connect.garmin.com/proxy/userprofile-service/connection/request/%s" % user_name)
        try:
            assert resp.status_code == 200
            assert resp.json()["requestStatus"] == "Created"
        except:
            raise APIException("Connection request failed with user watch account %s: %s %s" % (user_name, resp.status_code, resp.text))

        serviceRecord.SetPartialSyncTriggerSubscriptionState(True)

    def UnsubscribeFromPartialSyncTrigger(self, serviceRecord):
        # GET http://connect.garmin.com/proxy/userprofile-service/socialProfile/connections to get the ID
        #  {"fullName":null,"userConnections":[{"userId":5754439,"displayName":"TapiirikAPITEST","fullName":null,"location":null,"profileImageUrlMedium":null,"profileImageUrlSmall":null,"connectionRequestId":1566024,"userConnectionStatus":2,"userRoles":["ROLE_CONNECTUSER","ROLE_FITNESS_USER"],"userPro":false}]}
        # PUT http://connect.garmin.com/proxy/userprofile-service/connection/end/1904201
        # Unfortunately there's no way to delete a pending request - the poll worker will do this from the other end
        active_watch_user = self._user_watch_user(serviceRecord)
        session = self._get_session(email=active_watch_user["Username"], password=active_watch_user["Password"])
        self._rate_limit()
        connections = session.get("http://connect.garmin.com/proxy/userprofile-service/socialProfile/connections").json()

        for connection in connections["userConnections"]:
            if connection["displayName"] == serviceRecord.ExternalID:
                self._rate_limit()
                dc_resp = session.put("http://connect.garmin.com/proxy/userprofile-service/connection/end/%s" % connection["connectionRequestId"])
                if dc_resp.status_code != 200:
                    raise APIException("Error disconnecting user watch accunt %s from %s: %s %s" % (active_watch_user, connection["displayName"], dc_resp.status_code, dc_resp.text))

        serviceRecord.SetConfiguration({"WatchUserKey": None})

        serviceRecord.SetPartialSyncTriggerSubscriptionState(False)

    def ShouldForcePartialSyncTrigger(self, serviceRecord):
        # The poll worker can't see private activities.
        return serviceRecord.GetConfiguration()["sync_private"]


    def PollPartialSyncTrigger(self, multiple_index):
        # TODO: ensure the appropriate users are connected
        # GET http://connect.garmin.com/proxy/userprofile-service/connection/pending to get ID
        #  [{"userId":6244126,"displayName":"tapiriik-sync-ulukhaktok","fullName":"tapiriik sync ulukhaktok","profileImageUrlSmall":null,"connectionRequestId":1904086,"requestViewed":true,"userRoles":["ROLE_CONNECTUSER"],"userPro":false}]
        # PUT http://connect.garmin.com/proxy/userprofile-service/connection/accept/1904086
        # ...later...
        # GET http://connect.garmin.com/proxy/activitylist-service/activities/comments/subscriptionFeed?start=1&limit=10

        # First, accept any pending connections
        watch_user_key = sorted(list(GARMIN_CONNECT_USER_WATCH_ACCOUNTS.keys()))[multiple_index]
        watch_user = GARMIN_CONNECT_USER_WATCH_ACCOUNTS[watch_user_key]
        session = self._get_session(email=watch_user["Username"], password=watch_user["Password"])

        # Then, check for users with new activities
        self._rate_limit()
        watch_activities_resp = session.get("http://connect.garmin.com/proxy/activitylist-service/activities/subscriptionFeed?limit=1000")
        try:
            watch_activities = watch_activities_resp.json()
        except ValueError:
            raise Exception("Could not parse new activities list: %s %s" % (watch_activities_resp.status_code, watch_activities_resp.text))

        active_user_pairs = [(x["ownerDisplayName"], x["activityId"]) for x in watch_activities["activityList"]]
        active_user_pairs.sort(key=lambda x: x[1]) # Highest IDs last (so they make it into the dict, supplanting lower IDs where appropriate)
        active_users = dict(active_user_pairs)

        active_user_recs = [ServiceRecord(x) for x in db.connections.find({"ExternalID": {"$in": list(active_users.keys())}}, {"Config": 1, "ExternalID": 1, "Service": 1})]

        if len(active_user_recs) != len(active_users.keys()):
            logger.warning("Mismatch %d records found for %d active users" % (len(active_user_recs), len(active_users.keys())))

        to_sync_ids = []
        for active_user_rec in active_user_recs:
            last_active_id = active_user_rec.GetConfiguration()["WatchUserLastID"]
            this_active_id = active_users[active_user_rec.ExternalID]
            if this_active_id > last_active_id:
                to_sync_ids.append(active_user_rec.ExternalID)
                active_user_rec.SetConfiguration({"WatchUserLastID": this_active_id, "WatchUserKey": watch_user_key})

        self._rate_limit()
        pending_connections_resp = session.get("http://connect.garmin.com/proxy/userprofile-service/connection/pending")
        try:
            pending_connections = pending_connections_resp.json()
        except ValueError:
            logger.error("Could not parse pending connection requests: %s %s" % (pending_connections_resp.status_code, pending_connections_resp.text))
        else:
            valid_pending_connections_external_ids = [x["ExternalID"] for x in db.connections.find({"Service": "garminconnect", "ExternalID": {"$in": [x["displayName"] for x in pending_connections]}}, {"ExternalID": 1})]
            logger.info("Accepting %d, denying %d connection requests for %s" % (len(valid_pending_connections_external_ids), len(pending_connections) - len(valid_pending_connections_external_ids), watch_user_key))
            for pending_connect in pending_connections:
                if pending_connect["displayName"] in valid_pending_connections_external_ids:
                    self._rate_limit()
                    connect_resp = session.put("http://connect.garmin.com/proxy/userprofile-service/connection/accept/%s" % pending_connect["connectionRequestId"])
                    if connect_resp.status_code != 200:
                        logger.error("Error accepting request on watch account %s: %s %s" % (watch_user["Name"], connect_resp.status_code, connect_resp.text))
                else:
                    self._rate_limit()
                    ignore_resp = session.put("http://connect.garmin.com/proxy/userprofile-service/connection/decline/%s" % pending_connect["connectionRequestId"])


        return to_sync_ids

    def RevokeAuthorization(self, serviceRecord):
        # nothing to do here...
        pass

    def DeleteCachedData(self, serviceRecord):
        # nothing cached...
        pass

########NEW FILE########
__FILENAME__ = gpx
from lxml import etree
from pytz import UTC
import copy
import dateutil.parser
from datetime import datetime
from .interchange import WaypointType, Activity, Waypoint, Location, Lap
from .statistic_calculator import ActivityStatisticCalculator

class GPXIO:
    Namespaces = {
        None: "http://www.topografix.com/GPX/1/1",
        "gpxtpx": "http://www.garmin.com/xmlschemas/TrackPointExtension/v1",
        "gpxdata": "http://www.cluetrust.com/XML/GPXDATA/1/0",
        "gpxext": "http://www.garmin.com/xmlschemas/GpxExtensions/v3"
    }

    def Parse(gpxData, suppress_validity_errors=False):
        ns = copy.deepcopy(GPXIO.Namespaces)
        ns["gpx"] = ns[None]
        del ns[None]
        act = Activity()

        act.GPS = True # All valid GPX files have GPS data

        try:
            root = etree.XML(gpxData)
        except:
            root = etree.fromstring(gpxData)

        xmeta = root.find("gpx:metadata", namespaces=ns)
        if xmeta is not None:
            xname = xmeta.find("gpx:name", namespaces=ns)
            if xname is not None:
                act.Name = xname.text
        xtrk = root.find("gpx:trk", namespaces=ns)

        if xtrk is None:
            raise ValueError("Invalid GPX")

        xtrksegs = xtrk.findall("gpx:trkseg", namespaces=ns)
        startTime = None
        endTime = None

        for xtrkseg in xtrksegs:
            lap = Lap()
            for xtrkpt in xtrkseg.findall("gpx:trkpt", namespaces=ns):
                wp = Waypoint()

                wp.Timestamp = dateutil.parser.parse(xtrkpt.find("gpx:time", namespaces=ns).text)
                wp.Timestamp.replace(tzinfo=UTC)
                if startTime is None or wp.Timestamp < startTime:
                    startTime = wp.Timestamp
                if endTime is None or wp.Timestamp > endTime:
                    endTime = wp.Timestamp

                wp.Location = Location(float(xtrkpt.attrib["lat"]), float(xtrkpt.attrib["lon"]), None)
                eleEl = xtrkpt.find("gpx:ele", namespaces=ns)
                if eleEl is not None:
                    wp.Location.Altitude = float(eleEl.text)
                extEl = xtrkpt.find("gpx:extensions", namespaces=ns)
                if extEl is not None:
                    gpxtpxExtEl = extEl.find("gpxtpx:TrackPointExtension", namespaces=ns)
                    if gpxtpxExtEl is not None:
                        hrEl = gpxtpxExtEl.find("gpxtpx:hr", namespaces=ns)
                        if hrEl is not None:
                            wp.HR = float(hrEl.text)
                        cadEl = gpxtpxExtEl.find("gpxtpx:cad", namespaces=ns)
                        if cadEl is not None:
                            wp.Cadence = float(cadEl.text)
                        tempEl = gpxtpxExtEl.find("gpxtpx:atemp", namespaces=ns)
                        if tempEl is not None:
                            wp.Temp = float(tempEl.text)
                    gpxdataHR = extEl.find("gpxdata:hr", namespaces=ns)
                    if gpxdataHR is not None:
                        wp.HR = float(gpxdataHR.text)
                    gpxdataCadence = extEl.find("gpxdata:cadence", namespaces=ns)
                    if gpxdataCadence is not None:
                        wp.Cadence = float(gpxdataCadence.text)
                lap.Waypoints.append(wp)
            act.Laps.append(lap)
            if not len(lap.Waypoints) and not suppress_validity_errors:
                raise ValueError("Track segment without points")
            elif len(lap.Waypoints):
                lap.StartTime = lap.Waypoints[0].Timestamp
                lap.EndTime = lap.Waypoints[-1].Timestamp

        if not len(act.Laps) and not suppress_validity_errors:
            raise ValueError("File with no track segments")

        if act.CountTotalWaypoints():
            act.GetFlatWaypoints()[0].Type = WaypointType.Start
            act.GetFlatWaypoints()[-1].Type = WaypointType.End
            act.Stats.Distance.Value = ActivityStatisticCalculator.CalculateDistance(act)

            if len(act.Laps) == 1:
                # GPX encodes no real per-lap/segment statistics, so this is the only case where we can fill this in.
                # I've made an exception for the activity's total distance, but only because I want it later on for stats.
                act.Laps[0].Stats = act.Stats

        act.Stationary = False
        act.StartTime = startTime
        act.EndTime = endTime

        act.CalculateUID()
        return act

    def Dump(activity):
        GPXTPX = "{" + GPXIO.Namespaces["gpxtpx"] + "}"
        root = etree.Element("gpx", nsmap=GPXIO.Namespaces)
        root.attrib["creator"] = "tapiriik-sync"
        meta = etree.SubElement(root, "metadata")
        trk = etree.SubElement(root, "trk")
        if activity.Stationary:
            raise ValueError("Please don't use GPX for stationary activities.")
        if activity.Name is not None:
            etree.SubElement(meta, "name").text = activity.Name
            etree.SubElement(trk, "name").text = activity.Name

        inPause = False
        for lap in activity.Laps:
            trkseg = etree.SubElement(trk, "trkseg")
            for wp in lap.Waypoints:
                if wp.Location is None or wp.Location.Latitude is None or wp.Location.Longitude is None:
                    continue  # drop the point
                if wp.Type == WaypointType.Pause:
                    if inPause:
                        continue  # this used to be an exception, but I don't think that was merited
                    inPause = True
                if inPause and wp.Type != WaypointType.Pause:
                    inPause = False
                trkpt = etree.SubElement(trkseg, "trkpt")
                if wp.Timestamp.tzinfo is None:
                    raise ValueError("GPX export requires TZ info")
                etree.SubElement(trkpt, "time").text = wp.Timestamp.astimezone(UTC).isoformat()
                trkpt.attrib["lat"] = str(wp.Location.Latitude)
                trkpt.attrib["lon"] = str(wp.Location.Longitude)
                if wp.Location.Altitude is not None:
                    etree.SubElement(trkpt, "ele").text = str(wp.Location.Altitude)
                if wp.HR is not None or wp.Cadence is not None or wp.Temp is not None or wp.Calories is not None or wp.Power is not None:
                    exts = etree.SubElement(trkpt, "extensions")
                    gpxtpxexts = etree.SubElement(exts, GPXTPX + "TrackPointExtension")
                    if wp.HR is not None:
                        etree.SubElement(gpxtpxexts, GPXTPX + "hr").text = str(int(wp.HR))
                    if wp.Cadence is not None:
                        etree.SubElement(gpxtpxexts, GPXTPX + "cad").text = str(int(wp.Cadence))
                    if wp.Temp is not None:
                        etree.SubElement(gpxtpxexts, GPXTPX + "atemp").text = str(wp.Temp)

        return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8").decode("UTF-8")

########NEW FILE########
__FILENAME__ = interchange
from datetime import timedelta, datetime
from tapiriik.database import cachedb
from tapiriik.database.tz import TZLookup
import hashlib
import pytz


class ActivityType:  # taken from RK API docs. The text values have no meaning except for debugging
    Running = "Running"
    Cycling = "Cycling"
    MountainBiking = "MtnBiking"
    Walking = "Walking"
    Hiking = "Hiking"
    DownhillSkiing = "DownhillSkiing"
    CrossCountrySkiing = "XCSkiing"
    Snowboarding = "Snowboarding"
    Skating = "Skating"
    Swimming = "Swimming"
    Wheelchair = "Wheelchair"
    Rowing = "Rowing"
    Elliptical = "Elliptical"
    Gym = "Gym"
    Other = "Other"

    def List():
        return [ActivityType.Running, ActivityType.Cycling, ActivityType.MountainBiking, ActivityType.Walking, ActivityType.Hiking, ActivityType.DownhillSkiing, ActivityType.CrossCountrySkiing, ActivityType.Snowboarding, ActivityType.Skating, ActivityType.Swimming, ActivityType.Wheelchair, ActivityType.Rowing, ActivityType.Elliptical, ActivityType.Other]

    # The right-most element is the "most specific."
    _hierarchy = [
        [Cycling, MountainBiking],
        [Running, Walking, Hiking]
    ]
    def PickMostSpecific(types):
        types = [x for x in types if x and x is not ActivityType.Other]
        if len(types) == 0:
            return ActivityType.Other
        most_specific = types[0]
        for definition in ActivityType._hierarchy:
            if len([x for x in types if x in definition]) == len(types):
                for act_type in types:
                    if definition.index(most_specific) < definition.index(act_type):
                        most_specific = act_type
        return most_specific

    def AreVariants(types):
        for definition in ActivityType._hierarchy:
            if len([x for x in types if x in definition]) == len(types):
                return True
        return False


class Activity:
    def __init__(self, startTime=None, endTime=None, actType=ActivityType.Other, distance=None, name=None, notes=None, tz=None, lapList=None, private=False, fallbackTz=None, stationary=None, gps=None, device=None):
        self.StartTime = startTime
        self.EndTime = endTime
        self.Type = actType
        self.Laps = lapList if lapList is not None else []
        self.Stats = ActivityStatistics(distance=distance)
        self.TZ = tz
        self.FallbackTZ = fallbackTz
        self.Name = name
        self.Notes = notes
        self.Private = private
        self.Stationary = stationary
        self.GPS = gps
        self.PrerenderedFormats = {}
        self.Device = device

    def CalculateUID(self):
        if not self.StartTime:
            return  # don't even try
        csp = hashlib.new("md5")
        roundedStartTime = self.StartTime
        roundedStartTime = roundedStartTime - timedelta(microseconds=roundedStartTime.microsecond)
        if self.TZ:
            roundedStartTime = roundedStartTime.astimezone(self.TZ)
        csp.update(roundedStartTime.strftime("%Y-%m-%d %H:%M:%S").encode('utf-8'))  # exclude TZ for compat
        self.UID = csp.hexdigest()

    def CountTotalWaypoints(self):
        return sum([len(x.Waypoints) for x in self.Laps])

    def GetFlatWaypoints(self):
        return [wp for waypoints in [x.Waypoints for x in self.Laps] for wp in waypoints]

    def GetFirstWaypointWithLocation(self):
        loc_wp = None
        for lap in self.Laps:
            for wp in lap.Waypoints:
                if wp.Location is not None and wp.Location.Latitude is not None and wp.Location.Longitude is not None:
                    loc_wp = wp.Location
                    break
        return loc_wp

    def DefineTZ(self):
        """ run localize() on all contained dates to tag them with the activity TZ (doesn't change values) """
        if self.TZ is None:
            raise ValueError("TZ not set")
        if self.StartTime and self.StartTime.tzinfo is None:
            self.StartTime = self.TZ.localize(self.StartTime)
        if self.EndTime and self.EndTime.tzinfo is None:
            self.EndTime = self.TZ.localize(self.EndTime)
        for lap in self.Laps:
            lap.StartTime = self.TZ.localize(lap.StartTime) if lap.StartTime.tzinfo is None else lap.StartTime
            lap.EndTime = self.TZ.localize(lap.EndTime) if lap.EndTime.tzinfo is None else lap.EndTime
            for wp in lap.Waypoints:
                if wp.Timestamp.tzinfo is None:
                    wp.Timestamp = self.TZ.localize(wp.Timestamp)
        self.CalculateUID()

    def AdjustTZ(self):
        """ run astimezone() on all contained dates to align them with the activity TZ (requires non-naive DTs) """
        if self.TZ is None:
            raise ValueError("TZ not set")
        self.StartTime = self.StartTime.astimezone(self.TZ)
        self.EndTime = self.EndTime.astimezone(self.TZ)

        for lap in self.Laps:
            lap.StartTime = lap.StartTime.astimezone(self.TZ)
            lap.EndTime = lap.EndTime.astimezone(self.TZ)
            for wp in lap.Waypoints:
                    wp.Timestamp = wp.Timestamp.astimezone(self.TZ)
        self.CalculateUID()

    def CalculateTZ(self, loc=None, recalculate=False):
        if self.TZ and not recalculate:
            return self.TZ
        if loc is None:
            loc = self.GetFirstWaypointWithLocation()
            if loc is None and self.FallbackTZ is None:
                raise Exception("Can't find TZ without a waypoint with a location, or a fallback TZ")
        if loc is None:
            # At this point, we'll resort to the fallback TZ.
            if self.FallbackTZ is None:
                raise Exception("Can't find TZ without a waypoint with a location, specified location, or fallback TZ")
            self.TZ = self.FallbackTZ
            return self.TZ
        # I guess at some point it will be faster to perform a full lookup than digging through this table.
        cachedTzData = cachedb.tz_cache.find_one({"Latitude": loc.Latitude, "Longitude": loc.Longitude})
        if cachedTzData is None:
            res = TZLookup(loc.Latitude, loc.Longitude)
            cachedTzData = {"TZ": res, "Latitude": loc.Latitude, "Longitude": loc.Longitude}
            cachedb.tz_cache.insert(cachedTzData)

        if type(cachedTzData["TZ"]) != str:
            self.TZ = pytz.FixedOffset(cachedTzData["TZ"] * 60)
        else:
            self.TZ = pytz.timezone(cachedTzData["TZ"])
        return self.TZ

    def EnsureTZ(self, recalculate=False):
        self.CalculateTZ(recalculate=recalculate)
        if self.StartTime.tzinfo is None:
            self.DefineTZ()
        else:
            self.AdjustTZ()

    def CheckSanity(self):
        """ Started out as a function that checked to make sure the activity itself is sane.
            Now we perform a lot of checks to make sure all the objects were initialized properly
            I'm undecided on this front...
                - Forcing the .NET model of "XYZCollection"s that enforce integrity seems wrong
                - Enforcing them in constructors makes using the classes a pain
        """
        if "ServiceDataCollection" in self.__dict__:
            srcs = self.ServiceDataCollection  # this is just so I can see the source of the activity in the exception message
        if len(self.Laps) == 0:
                raise ValueError("No laps")
        wptCt = sum([len(x.Waypoints) for x in self.Laps])
        if self.Stationary is None:
            raise ValueError("Activity is undecidedly stationary")
        if self.GPS is None:
            raise ValueError("Activity is undecidedly GPS-tracked")
        if not self.Stationary:
            if wptCt == 0:
                raise ValueError("Exactly 0 waypoints")
            if wptCt == 1:
                raise ValueError("Only 1 waypoint")
        if self.Stats.Distance.Value is not None and self.Stats.Distance.asUnits(ActivityStatisticUnit.Meters).Value > 1000 * 1000:
            raise ValueError("Exceedingly long activity (distance)")
        if self.StartTime.replace(tzinfo=None) > (datetime.now() + timedelta(days=5)):
            raise ValueError("Activity is from the future")
        if self.StartTime.replace(tzinfo=None) < datetime(1995, 1, 1):
            raise ValueError("Activity falls implausibly far in the past")
        if self.EndTime and self.EndTime.replace(tzinfo=None) > (datetime.now() + timedelta(days=5 + 5)): # Based on the 5-day activity length limit imposed later.
            raise ValueError("Activity ends in the future")

        if self.StartTime and self.EndTime:
            # We can only do these checks if the activity has both start and end times (Dropbox)
            if (self.EndTime - self.StartTime).total_seconds() < 0:
                raise ValueError("Event finishes before it starts")
            if (self.EndTime - self.StartTime).total_seconds() == 0:
                raise ValueError("0-duration activity")
            if (self.EndTime - self.StartTime).total_seconds() > 60 * 60 * 24 * 5:
                raise ValueError("Exceedingly long activity (time)")

        if len(self.Laps) == 1:
            if self.Laps[0].Stats != self.Stats:
                raise ValueError("Activity with 1 lap has mismatching statistics between activity and lap")
        altLow = None
        altHigh = None
        pointsWithLocation = 0
        unpausedPoints = 0
        for lap in self.Laps:
            if not lap.StartTime:
                raise ValueError("Lap has no start time")
            if not lap.EndTime:
                raise ValueError("Lap has no end time")
            for wp in lap.Waypoints:
                if wp.Type != WaypointType.Pause:
                    unpausedPoints += 1
                if wp.Location:
                    if wp.Location.Latitude == 0 and wp.Location.Longitude == 0:
                        raise ValueError("Invalid lat/lng")
                    if (wp.Location.Latitude is not None and (wp.Location.Latitude > 90 or wp.Location.Latitude < -90)) or (wp.Location.Longitude is not None and (wp.Location.Longitude > 180 or wp.Location.Longitude < -180)):
                        raise ValueError("Out of range lat/lng")
                    if wp.Location.Altitude is not None and (altLow is None or wp.Location.Altitude < altLow):
                        altLow = wp.Location.Altitude
                    if wp.Location.Altitude is not None and (altHigh is None or wp.Location.Altitude > altHigh):
                        altHigh = wp.Location.Altitude
                if wp.Location and wp.Location.Latitude is not None and wp.Location.Longitude is not None:
                    pointsWithLocation += 1
        if unpausedPoints == 1:
            raise ValueError("0 < n <= 1 unpaused points in activity")
        if pointsWithLocation == 1:
            raise ValueError("0 < n <= 1 geographic points in activity") # Make RK happy
        if altLow is not None and altLow == altHigh and altLow == 0:  # some activities have very sporadic altitude data, we'll let it be...
            raise ValueError("Invalid altitudes / no change from " + str(altLow))

    def CleanStats(self):
        """
            Some devices/apps populate fields with patently false values, e.g. HR avg = 1bpm, calories = 0kcal
            So, rather than propagating these, or bailing, we silently strip them, in hopes that destinations will do a better job of calculating them.
            Most of the upper limits match the FIT spec
        """
        def _cleanStatsObj(stats):
            ranges = {
                "Power": [ActivityStatisticUnit.Watts, 0, 5000],
                "Speed": [ActivityStatisticUnit.KilometersPerHour, 0, 150],
                "Elevation": [ActivityStatisticUnit.Meters, -500, 8850], # Props for bringing your Forerunner up Everest
                "HR": [ActivityStatisticUnit.BeatsPerMinute, 15, 300], # Please visit the ER before you email me about these limits
                "Cadence": [ActivityStatisticUnit.RevolutionsPerMinute, 0, 255], # FIT
                "RunCadence": [ActivityStatisticUnit.StepsPerMinute, 0, 255], # FIT
                "Strides": [ActivityStatisticUnit.Strides, 1, 9999999],
                "Temperature": [ActivityStatisticUnit.DegreesCelcius, -62, 50],
                "Energy": [ActivityStatisticUnit.Kilocalories, 1, 65535], # FIT
                "Distance": [ActivityStatisticUnit.Kilometers, 0, 1000] # You can let me know when you ride 1000 km and I'll up this.
            }
            checkFields = ["Average", "Max", "Min", "Value"]
            for key in ranges:
                stat = stats.__dict__[key].asUnits(ranges[key][0])
                for field in checkFields:
                    value = stat.__dict__[field]
                    if value is not None and (value < ranges[key][1] or value > ranges[key][2]):
                        stats.__dict__[key]._samples[field] = 0 # Need to update the original, not the asUnits copy
                        stats.__dict__[key].__dict__[field] = None

        _cleanStatsObj(self.Stats)
        for lap in self.Laps:
            _cleanStatsObj(lap.Stats)

    def CleanWaypoints(self):
        # Similarly, we sometimes get complete nonsense like negative distance
        waypoints = self.GetFlatWaypoints()
        for wp in waypoints:
            if wp.Distance and wp.Distance < 0:
                wp.Distance = 0
            if wp.Speed and wp.Speed < 0:
                wp.Speed = 0
            if wp.Cadence and wp.Cadence < 0:
                wp.Cadence = 0
            if wp.RunCadence and wp.RunCadence < 0:
                wp.RunCadence = 0
            if wp.Power and wp.Power < 0:
                wp.Power = 0
            if wp.Calories and wp.Calories < 0:
                wp.Calories = 0 # Are there any devices that track your caloric intake? Interesting idea...
            if wp.HR and wp.HR < 0:
                wp.HR = 0

    def __str__(self):
        return "Activity (" + self.Type + ") Start " + str(self.StartTime) + " " + str(self.TZ) + " End " + str(self.EndTime) + " stat " + str(self.Stationary)
    __repr__ = __str__

    def __eq__(self, other):
        # might need to fix this for TZs?
        return self.StartTime == other.StartTime and self.EndTime == other.EndTime and self.Type == other.Type and self.Laps == other.Laps and self.Stats.Distance == other.Stats.Distance and self.Name == other.Name

    def __ne__(self, other):
        return not self.__eq__(other)


class UploadedActivity (Activity):
    pass  # will contain list of which service instances contain this activity - not really merited

class LapIntensity:
    Active = 0
    Rest = 1
    Warmup = 2
    Cooldown = 3

class LapTriggerMethod:
    Manual = 0
    Time = 1
    Distance = 2
    PositionStart = 3
    PositionLap = 4
    PositionWaypoint = 5
    PositionMarked = 6
    SessionEnd = 7
    FitnessEquipment = 8

class Lap:
    def __init__(self, startTime=None, endTime=None, intensity=LapIntensity.Active, trigger=LapTriggerMethod.Manual, stats=None, waypointList=None):
        self.StartTime = startTime
        self.EndTime = endTime
        self.Trigger = trigger
        self.Intensity = intensity
        self.Stats = stats if stats else ActivityStatistics()
        self.Waypoints = waypointList if waypointList else []

    def __str__(self):
        return str(self.StartTime) + "-" + str(self.EndTime) + " " + str(self.Intensity) + " (" + str(self.Trigger) + ") " + str(len(self.Waypoints)) + " wps"
    __repr__ = __str__

class ActivityStatistics:
    _statKeyList = ["Distance", "TimerTime", "MovingTime", "Energy", "Speed", "Elevation", "HR", "Cadence", "RunCadence", "Strides", "Temperature", "Power"]
    def __init__(self, distance=None, timer_time=None, moving_time=None, avg_speed=None, max_speed=None, max_elevation=None, min_elevation=None, gained_elevation=None, lost_elevation=None, avg_hr=None, max_hr=None, avg_cadence=None, max_cadence=None, avg_run_cadence=None, max_run_cadence=None, strides=None, min_temp=None, avg_temp=None, max_temp=None, kcal=None, avg_power=None, max_power=None):
        self.Distance = ActivityStatistic(ActivityStatisticUnit.Meters, value=distance)
        self.TimerTime = ActivityStatistic(ActivityStatisticUnit.Seconds, value=timer_time)
        self.MovingTime = ActivityStatistic(ActivityStatisticUnit.Seconds, value=moving_time)
        self.Energy = ActivityStatistic(ActivityStatisticUnit.Kilocalories, value=kcal)
        self.Speed = ActivityStatistic(ActivityStatisticUnit.KilometersPerHour, avg=avg_speed, max=max_speed)
        self.Elevation = ActivityStatistic(ActivityStatisticUnit.Meters, max=max_elevation, min=min_elevation, gain=gained_elevation, loss=lost_elevation)
        self.HR = ActivityStatistic(ActivityStatisticUnit.BeatsPerMinute, avg=avg_hr, max=max_hr)
        self.Cadence = ActivityStatistic(ActivityStatisticUnit.RevolutionsPerMinute, avg=avg_cadence, max=max_cadence)
        self.RunCadence = ActivityStatistic(ActivityStatisticUnit.StepsPerMinute, avg=avg_run_cadence, max=max_run_cadence)
        self.Strides = ActivityStatistic(ActivityStatisticUnit.Strides, value=strides)
        self.Temperature = ActivityStatistic(ActivityStatisticUnit.DegreesCelcius, avg=avg_temp, max=max_temp, min=min_temp)
        self.Power = ActivityStatistic(ActivityStatisticUnit.Watts, avg=avg_power, max=max_power)

    def coalesceWith(self, other_stats):
        for stat in ActivityStatistics._statKeyList:
            self.__dict__[stat].coalesceWith(other_stats.__dict__[stat])
    # Could overload +, but...
    def sumWith(self, other_stats):
        for stat in ActivityStatistics._statKeyList:
            self.__dict__[stat].sumWith(other_stats.__dict__[stat])
    # Magic dict is meh
    def update(self, other_stats):
        for stat in ActivityStatistics._statKeyList:
            self.__dict__[stat].update(other_stats.__dict__[stat])
    def __eq__(self, other):
        if not other:
            return False
        for stat in ActivityStatistics._statKeyList:
            if not self.__dict__[stat] == other.__dict__[stat]:
                return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

class ActivityStatistic:
    def __init__(self, units, value=None, avg=None, min=None, max=None, gain=None, loss=None):
        self.Value = value
        self.Average = avg
        self.Min = min
        self.Max = max
        self.Gain = gain
        self.Loss = loss

        # Nothing outside of this class should be accessing _samples (though CleanStats gets a pass)
        self._samples = {}
        self._samples["Value"] = 1 if value is not None else 0
        self._samples["Average"] = 1 if avg is not None else 0
        self._samples["Min"] = 1 if min is not None else 0
        self._samples["Max"] = 1 if max is not None else 0
        self._samples["Gain"] = 1 if gain is not None else 0
        self._samples["Loss"] = 1 if loss is not None else 0

        self.Units = units

    def asUnits(self, units):
        if units == self.Units:
            return self
        newStat = ActivityStatistic(units)
        existing_dict = dict(self.__dict__)
        del existing_dict["Units"]
        del existing_dict["_samples"]
        ActivityStatistic.convertUnitsInDict(existing_dict, self.Units, units)
        newStat.__dict__ = existing_dict
        newStat.Units = units
        newStat._samples = self._samples
        return newStat

    def convertUnitsInDict(values_dict, from_units, to_units):
        for key, value in values_dict.items():
            if value is None:
                continue
            values_dict[key] = ActivityStatistic.convertValue(value, from_units, to_units)

    def convertValue(value, from_units, to_units):
        conversions = {
            (ActivityStatisticUnit.KilometersPerHour, ActivityStatisticUnit.HectometersPerHour): 10,
            (ActivityStatisticUnit.KilometersPerHour, ActivityStatisticUnit.MilesPerHour): 0.621371,
            (ActivityStatisticUnit.MilesPerHour, ActivityStatisticUnit.HundredYardsPerHour): 17.6,
            (ActivityStatisticUnit.MetersPerSecond, ActivityStatisticUnit.KilometersPerHour): 3.6,
            (ActivityStatisticUnit.DegreesCelcius, ActivityStatisticUnit.DegreesFahrenheit): (lambda C: C*9/5 + 32, lambda F: (F-32) * 5/9),
            (ActivityStatisticUnit.Kilometers, ActivityStatisticUnit.Meters): 1000,
            (ActivityStatisticUnit.Meters, ActivityStatisticUnit.Feet): 3.281,
            (ActivityStatisticUnit.Meters, ActivityStatisticUnit.Yards): 1.09361,
            (ActivityStatisticUnit.Miles, ActivityStatisticUnit.Feet): 5280,
            (ActivityStatisticUnit.Kilocalories, ActivityStatisticUnit.Kilojoules): 4.184,
            (ActivityStatisticUnit.StepsPerMinute, ActivityStatisticUnit.DoubledStepsPerMinute): 2
        }
        def recurseFindConversionPath(unit, target, stack):
            assert(unit != target)
            for transform in conversions.keys():
                if unit in transform:
                    if transform in stack:
                        continue  # Prevent circular conversion
                    if target in transform:
                        # We've arrived at the end
                        return stack + [transform]
                    else:
                        next_unit = transform[0] if transform[1] == unit else transform[1]
                        result = recurseFindConversionPath(next_unit, target, stack + [transform])
                        if result:
                            return result
            return None

        conversionPath = recurseFindConversionPath(from_units, to_units, [])
        if not conversionPath:
            raise ValueError("No conversion from %s to %s" % (from_units, to_units))
        for transform in conversionPath:
            if type(conversions[transform]) is float or type(conversions[transform]) is int:
                if from_units == transform[0]:
                    value = value * conversions[transform]
                    from_units = transform[1]
                else:
                    value = value / conversions[transform]
                    from_units = transform[0]
            else:
                if from_units == transform[0]:
                    func = conversions[transform][0] if type(conversions[transform]) is tuple else conversions[transform]
                    value = func(value)
                    from_units = transform[1]
                else:
                    if type(conversions[transform]) is not tuple:
                        raise ValueError("No transform function for %s to %s" % (from_units, to_units))
                    value = conversions[transform][1](value)
                    from_units = transform[0]
        return value

    def coalesceWith(self, stat):
        stat = stat.asUnits(self.Units)

        items = ["Value", "Max", "Min", "Average", "Gain", "Loss"]
        my_items = self.__dict__
        other_items = stat.__dict__
        my_samples = self._samples
        other_samples = stat._samples
        for item in items:
            # Only average if there's a second value
            if other_items[item] is not None:
                # We need to override this so we can be lazy elsewhere and just assign values (.Average = ...) and don't have to use .update(ActivityStatistic(blah, blah, blah))
                other_samples[item] = other_samples[item] if other_samples[item] else 1
                if my_items[item] is None:
                    # We don't have this item's value, nothing to do really.
                    my_items[item] = other_items[item]
                    my_samples[item] = other_samples[item]
                else:
                    my_items[item] += (other_items[item] - my_items[item]) / ((my_samples[item] + 1 / other_samples[item]))
                    my_samples[item] += other_samples[item]

    def sumWith(self, stat):
        """ Used if you want to sum up, for instance, laps' stats to get the activity's stats
            Not all items can be simply summed (min/max), and sum just shouldn't (average)
        """
        stat = stat.asUnits(self.Units)
        summable_items = ["Value", "Gain", "Loss"]
        other_items = stat.__dict__
        for item in summable_items:
            if item in other_items and other_items[item] is not None:
                if self.__dict__[item] is not None:
                    self.__dict__[item] += other_items[item]
                    self._samples[item] = 1 # Break the chain of coalesceWith() calls - this is an entirely fresh "measurement"
                else:
                    self.__dict__[item] = other_items[item]
                    self._samples[item] = stat._samples[item]
        self.Average = None
        self._samples["Average"] = 0

        if self.Max is None or (stat.Max is not None and stat.Max > self.Max):
            self.Max = stat.Max
            self._samples["Max"] = stat._samples["Max"]
        if self.Min is None or (stat.Min is not None and stat.Min < self.Min):
            self.Min = stat.Min
            self._samples["Min"] = stat._samples["Min"]

    def update(self, stat):
        stat = stat.asUnits(self.Units)
        items = ["Value", "Max", "Min", "Average", "Gain", "Loss"]
        other_items = stat.__dict__
        for item in items:
            if item in other_items and other_items[item] is not None:
                self.__dict__[item] = other_items[item]
                self._samples[item] = stat._samples[item]

    def __eq__(self, other):
        if not other:
            return False
        return self.Units == other.Units and self.Value == other.Value and self.Average == other.Average and self.Max == other.Max and self.Min == other.Min and self.Gain == other.Gain and self.Loss == other.Loss

    def __ne__(self, other):
        return not self.__eq__(other)



class ActivityStatisticUnit:
    Seconds = "s"
    Milliseconds = "ms"
    Meters = "m"
    Kilometers = "km"
    Feet = "f"
    Yards = "yd"
    Miles = "mi"
    DegreesCelcius = "ºC"
    DegreesFahrenheit = "ºF"
    KilometersPerHour = "km/h"
    HectometersPerHour = "hm/h" # Silly Garmin Connect!
    MetersPerSecond = "m/s"
    MilesPerHour = "mph"
    HundredYardsPerHour = "hydph" # Hundred instead of Hecto- because imperial :<
    BeatsPerMinute = "BPM"
    RevolutionsPerMinute = "RPM"
    StepsPerMinute = "SPM"
    DoubledStepsPerMinute = "2SPM" # Garmin Connect is still weird.
    Strides = "strides"
    Kilocalories = "kcal"
    Kilojoules = "kj"
    Watts = "W"


class WaypointType:
    Start = 0   # Start of activity
    Regular = 1 # Normal
    Pause = 11  # All waypoints within a paused period should have this type
    Resume = 12 # The first waypoint after a paused period
    End = 100   # End of activity

class Waypoint:
    __slots__ = ["Timestamp", "Location", "HR", "Calories", "Power", "Temp", "Cadence", "RunCadence", "Type", "Distance", "Speed"]
    def __init__(self, timestamp=None, ptType=WaypointType.Regular, location=None, hr=None, power=None, calories=None, cadence=None, runCadence=None, temp=None, distance=None, speed=None):
        self.Timestamp = timestamp
        self.Location = location
        self.HR = hr # BPM
        self.Calories = calories # kcal
        self.Power = power  # Watts. I doubt there will ever be more parameters than this in terms of interchange
        self.Temp = temp  # degrees C. never say never
        self.Cadence = cadence  # RPM. dammit this better be the last one
        self.RunCadence = runCadence  # SPM. screw it
        self.Distance = distance # meters. I don't even care any more.
        self.Speed = speed # m/sec. neghhhhh
        self.Type = ptType

    def __eq__(self, other):
        return self.Timestamp == other.Timestamp and self.Location == other.Location and self.HR == other.HR and self.Calories == other.Calories and self.Temp == other.Temp and self.Cadence == other.Cadence and self.Type == other.Type and self.Power == other.Power and self.RunCadence == other.RunCadence and self.Distance == other.Distance and self.Speed == other.Speed

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return str(self.Type) + "@" + str(self.Timestamp) + " " + ((str(self.Location.Latitude) + "|" + str(self.Location.Longitude) + "^" + str(round(self.Location.Altitude) if self.Location.Altitude is not None else None)) if self.Location is not None else "") + "\n\tHR " + str(self.HR) + " CAD " + str(self.Cadence) + " RCAD " + str(self.RunCadence) + " TEMP " + str(self.Temp) + " PWR " + str(self.Power) + " CAL " + str(self.Calories) + " SPD " + str(self.Speed) + " DST " + str(self.Distance)
    __repr__ = __str__


class Location:
    __slots__ = ["Latitude", "Longitude", "Altitude"]
    def __init__(self, lat=None, lon=None, alt=None):
        self.Latitude = lat
        self.Longitude = lon
        self.Altitude = alt

    def __eq__(self, other):
        if not other:
            return False
        return self.Latitude == other.Latitude and self.Longitude == other.Longitude and self.Altitude == other.Altitude

    def __ne__(self, other):
        return not self.__eq__(other)

########NEW FILE########
__FILENAME__ = pwx
from lxml import etree
import copy
import dateutil.parser
from datetime import timedelta
from .interchange import WaypointType, ActivityType, Activity, Waypoint, Location, Lap, ActivityStatistic, ActivityStatisticUnit

class PWXIO:
    Namespaces = {
        None: "http://www.peaksware.com/PWX/1/0"
    }

    _sportTypeMappings = {
        "Bike": ActivityType.Cycling,
        "Run": ActivityType.Running,
        "Walk": ActivityType.Walking,
        "Swim": ActivityType.Swimming,
        "Mountain Bike": ActivityType.MountainBiking,
        "XC Ski": ActivityType.CrossCountrySkiing,
        "Rowing": ActivityType.Rowing,
        "Other": ActivityType.Other
    }

    _reverseSportTypeMappings = {
        ActivityType.Cycling: "Bike",
        ActivityType.Running: "Run",
        ActivityType.Walking: "Walk",
        ActivityType.Hiking: "Walk", # Hilly walking?
        ActivityType.Swimming: "Swim",
        ActivityType.MountainBiking: "Mountain Bike",
        ActivityType.CrossCountrySkiing: "XC Ski",
        ActivityType.DownhillSkiing: "XC Ski", # For whatever reason there's no "ski" type
        ActivityType.Rowing: "Rowing",
        ActivityType.Other: "Other",
    }

    def Parse(pwxData, activity=None):
        ns = copy.deepcopy(PWXIO.Namespaces)
        ns["pwx"] = ns[None]
        del ns[None]

        activity = activity if activity else Activity()

        try:
            root = etree.XML(pwxData)
        except:
            root = etree.fromstring(pwxData)

        xworkout = root.find("pwx:workout", namespaces=ns)

        xsportType = xworkout.find("pwx:sportType", namespaces=ns)
        if xsportType is not None:
            sportType = xsportType.text
            if sportType in PWXIO._sportTypeMappings:
                if PWXIO._sportTypeMappings[sportType] != ActivityType.Other:
                    activity.Type = PWXIO._sportTypeMappings[sportType]

        xtitle = xworkout.find("pwx:title", namespaces=ns)
        if xtitle is not None:
            activity.Name = xtitle.text

        xcmt = xworkout.find("pwx:cmt", namespaces=ns)
        if xcmt is not None:
            activity.Notes = xcmt.text

        xtime = xworkout.find("pwx:time", namespaces=ns)
        if xtime is None:
            raise ValueError("Can't parse PWX without time")

        activity.StartTime = dateutil.parser.parse(xtime.text)

        def _minMaxAvg(xminMaxAvg):
            return {"min": float(xminMaxAvg.attrib["min"]) if "min" in xminMaxAvg.attrib else None, "max": float(xminMaxAvg.attrib["max"]) if "max" in xminMaxAvg.attrib else None, "avg": float(xminMaxAvg.attrib["avg"])  if "avg" in xminMaxAvg.attrib else None} # Most useful line ever

        def _readSummaryData(xsummary, obj, time_ref):
            obj.StartTime = time_ref + timedelta(seconds=float(xsummary.find("pwx:beginning", namespaces=ns).text))
            obj.EndTime = obj.StartTime + timedelta(seconds=float(xsummary.find("pwx:duration", namespaces=ns).text))

            # "duration - durationstopped = moving time. duration stopped may be zero." - Ben
            stoppedEl = xsummary.find("pwx:durationstopped", namespaces=ns)
            if stoppedEl is not None:
                obj.Stats.TimerTime = ActivityStatistic(ActivityStatisticUnit.Seconds, value=(obj.EndTime - obj.StartTime).total_seconds() - float(stoppedEl.text))
            else:
                obj.Stats.TimerTime = ActivityStatistic(ActivityStatisticUnit.Seconds, value=(obj.EndTime - obj.StartTime).total_seconds())

            hrEl = xsummary.find("pwx:hr", namespaces=ns)
            if hrEl is not None:
                obj.Stats.HR = ActivityStatistic(ActivityStatisticUnit.BeatsPerMinute, **_minMaxAvg(hrEl))

            spdEl = xsummary.find("pwx:spd", namespaces=ns)
            if spdEl is not None:
                obj.Stats.Speed = ActivityStatistic(ActivityStatisticUnit.MetersPerSecond, **_minMaxAvg(spdEl))

            pwrEl = xsummary.find("pwx:pwr", namespaces=ns)
            if pwrEl is not None:
                obj.Stats.Power = ActivityStatistic(ActivityStatisticUnit.Watts, **_minMaxAvg(pwrEl))

            cadEl = xsummary.find("pwx:cad", namespaces=ns)
            if cadEl is not None:
                obj.Stats.Cadence = ActivityStatistic(ActivityStatisticUnit.RevolutionsPerMinute, **_minMaxAvg(cadEl))

            distEl = xsummary.find("pwx:dist", namespaces=ns)
            if distEl is not None:
                obj.Stats.Distance = ActivityStatistic(ActivityStatisticUnit.Meters, value=float(distEl.text))

            altEl = xsummary.find("pwx:alt", namespaces=ns)
            if altEl is not None:
                obj.Stats.Elevation = ActivityStatistic(ActivityStatisticUnit.Meters, **_minMaxAvg(altEl))

            climbEl = xsummary.find("pwx:climbingelevation", namespaces=ns)
            if climbEl is not None:
                obj.Stats.Elevation.update(ActivityStatistic(ActivityStatisticUnit.Meters, gain=float(climbEl.text)))

            descEl = xsummary.find("pwx:descendingelevation", namespaces=ns)
            if descEl is not None:
                obj.Stats.Elevation.update(ActivityStatistic(ActivityStatisticUnit.Meters, loss=float(descEl.text)))

            tempEl = xsummary.find("pwx:temp", namespaces=ns)
            if tempEl is not None:
                obj.Stats.Temperature = ActivityStatistic(ActivityStatisticUnit.DegreesCelcius, **_minMaxAvg(tempEl))

        _readSummaryData(xworkout.find("pwx:summarydata", namespaces=ns), activity, time_ref=activity.StartTime)

        laps = []
        xsegments = xworkout.findall("pwx:segment", namespaces=ns)

        for xsegment in xsegments:
            lap = Lap()
            _readSummaryData(xsegment.find("pwx:summarydata", namespaces=ns), lap, time_ref=activity.StartTime)
            laps.append(lap)

        if len(laps) == 1:
            laps[0].Stats.update(activity.Stats)
            activity.Stats = laps[0].Stats
        elif not len(laps):
            laps = [Lap(startTime=activity.StartTime, endTime=activity.EndTime, stats=activity.Stats)]

        xsamples = xworkout.findall("pwx:sample", namespaces=ns)

        currentLapIdx = 0
        for xsample in xsamples:
            wp = Waypoint()
            wp.Timestamp = activity.StartTime + timedelta(seconds=float(xsample.find("pwx:timeoffset", namespaces=ns).text))

            # Just realized how terribly inefficient doing the search-if-set pattern is. I'll change everything over to iteration... eventually
            for xsampleData in xsample:
                tag = xsampleData.tag[34:] # {http://www.peaksware.com/PWX/1/0} is 34 chars. I'll show myself out.
                if tag == "hr":
                    wp.HR = int(xsampleData.text)
                elif tag == "spd":
                    wp.Speed = float(xsampleData.text)
                elif tag == "pwr":
                    wp.Power = float(xsampleData.text)
                elif tag == "cad":
                    wp.Cadence = int(xsampleData.text)
                elif tag == "dist":
                    wp.Distance = float(xsampleData.text)
                elif tag == "temp":
                    wp.Temp = float(xsampleData.text)
                elif tag == "alt":
                    if wp.Location is None:
                        wp.Location = Location()
                    wp.Location.Altitude = float(xsampleData.text)
                elif tag == "lat":
                    if wp.Location is None:
                        wp.Location = Location()
                    wp.Location.Latitude = float(xsampleData.text)
                elif tag == "lon":
                    if wp.Location is None:
                        wp.Location = Location()
                    wp.Location.Longitude = float(xsampleData.text)
            assert wp.Location is None or ((wp.Location.Latitude is None) == (wp.Location.Longitude is None)) # You never know...

            # If we've left one lap, move to the next immediately
            while currentLapIdx < len(laps) - 1 and wp.Timestamp > laps[currentLapIdx].EndTime:
                currentLapIdx += 1

            laps[currentLapIdx].Waypoints.append(wp)
        activity.Laps = laps
        activity.Stationary = activity.CountTotalWaypoints() == 0
        if not activity.Stationary:
            flatWp = activity.GetFlatWaypoints()
            flatWp[0].Type = WaypointType.Start
            flatWp[-1].Type = WaypointType.End
            if activity.EndTime < flatWp[-1].Timestamp: # Work around the fact that TP doesn't preserve elapsed time.
                activity.EndTime = flatWp[-1].Timestamp
        return activity

    def Dump(activity):
        xroot = etree.Element("pwx", nsmap=PWXIO.Namespaces)

        xroot.attrib["creator"] = "tapiriik"
        xroot.attrib["version"] = "1.0"

        xworkout = etree.SubElement(xroot, "workout")

        if activity.Type in PWXIO._reverseSportTypeMappings:
            etree.SubElement(xworkout, "sportType").text = PWXIO._reverseSportTypeMappings[activity.Type]

        if activity.Name:
            etree.SubElement(xworkout, "title").text = activity.Name

        if activity.Notes:
            etree.SubElement(xworkout, "cmt").text = activity.Notes

        xdevice = etree.SubElement(xworkout, "device")

        # By Ben's request
        etree.SubElement(xdevice, "make").text = "tapiriik"
        if hasattr(activity, "SourceConnection"):
            etree.SubElement(xdevice, "model").text = activity.SourceConnection.Service.ID

        etree.SubElement(xworkout, "time").text = activity.StartTime.replace(tzinfo=None).isoformat()

        def _writeMinMaxAvg(xparent, name, stat, naturalValue=False):
            if stat.Min is None and stat.Max is None and stat.Average is None:
                return
            xstat = etree.SubElement(xparent, name)
            if stat.Min is not None:
                xstat.attrib["min"] = str(stat.Min)
            if stat.Max is not None:
                xstat.attrib["max"] = str(stat.Max)
            if stat.Average is not None:
                xstat.attrib["avg"] = str(stat.Average)

        def _writeSummaryData(xparent, obj, time_ref):
            xsummary = etree.SubElement(xparent, "summarydata")
            etree.SubElement(xsummary, "beginning").text = str((obj.StartTime - time_ref).total_seconds())
            etree.SubElement(xsummary, "duration").text = str((obj.EndTime - obj.StartTime).total_seconds())

            if obj.Stats.TimerTime.Value is not None:
                etree.SubElement(xsummary, "durationstopped").text = str((obj.EndTime - obj.StartTime).total_seconds() - obj.Stats.TimerTime.asUnits(ActivityStatisticUnit.Seconds).Value)

            altStat = obj.Stats.Elevation.asUnits(ActivityStatisticUnit.Meters)

            _writeMinMaxAvg(xsummary, "hr", obj.Stats.HR.asUnits(ActivityStatisticUnit.BeatsPerMinute))
            _writeMinMaxAvg(xsummary, "spd", obj.Stats.Speed.asUnits(ActivityStatisticUnit.MetersPerSecond))
            _writeMinMaxAvg(xsummary, "pwr", obj.Stats.Power.asUnits(ActivityStatisticUnit.Watts))
            if obj.Stats.Cadence.Min is not None or obj.Stats.Cadence.Max is not None or obj.Stats.Cadence.Average is not None:
                _writeMinMaxAvg(xsummary, "cad", obj.Stats.Cadence.asUnits(ActivityStatisticUnit.RevolutionsPerMinute))
            else:
                _writeMinMaxAvg(xsummary, "cad", obj.Stats.RunCadence.asUnits(ActivityStatisticUnit.StepsPerMinute))
            if obj.Stats.Distance.Value:
                etree.SubElement(xsummary, "dist").text = str(obj.Stats.Distance.asUnits(ActivityStatisticUnit.Meters).Value)
            _writeMinMaxAvg(xsummary, "alt", altStat)
            _writeMinMaxAvg(xsummary, "temp", obj.Stats.Temperature.asUnits(ActivityStatisticUnit.DegreesCelcius))

            if altStat.Gain is not None:
                etree.SubElement(xsummary, "climbingelevation").text = str(altStat.Gain)
            if altStat.Loss is not None:
                etree.SubElement(xsummary, "descendingelevation").text = str(altStat.Loss)

        _writeSummaryData(xworkout, activity, time_ref=activity.StartTime)

        for lap in activity.Laps:
            xsegment = etree.SubElement(xworkout, "segment")
            _writeSummaryData(xsegment, lap, time_ref=activity.StartTime)

        for wp in activity.GetFlatWaypoints():
            xsample = etree.SubElement(xworkout, "sample")
            etree.SubElement(xsample, "timeoffset").text = str((wp.Timestamp - activity.StartTime).total_seconds())

            if wp.HR is not None:
                etree.SubElement(xsample, "hr").text = str(round(wp.HR))

            if wp.Speed is not None:
                etree.SubElement(xsample, "spd").text = str(wp.Speed)

            if wp.Power is not None:
                etree.SubElement(xsample, "pwr").text = str(round(wp.Power))

            if wp.Cadence is not None:
                etree.SubElement(xsample, "cad").text = str(round(wp.Cadence))
            else:
                if wp.RunCadence is not None:
                    etree.SubElement(xsample, "cad").text = str(round(wp.RunCadence))

            if wp.Distance is not None:
                etree.SubElement(xsample, "dist").text = str(wp.Distance)

            if wp.Location is not None:
                if wp.Location.Longitude is not None:
                    etree.SubElement(xsample, "lat").text = str(wp.Location.Latitude)
                    etree.SubElement(xsample, "lon").text = str(wp.Location.Longitude)
                if wp.Location.Altitude is not None:
                    etree.SubElement(xsample, "alt").text = str(wp.Location.Altitude)

            if wp.Temp is not None:
                etree.SubElement(xsample, "temp").text = str(wp.Temp)


        return etree.tostring(xroot, pretty_print=True, xml_declaration=True, encoding="UTF-8").decode("UTF-8")

########NEW FILE########
__FILENAME__ = rwgps
import os
import math
from datetime import datetime, timedelta

import pytz
import requests
from django.core.urlresolvers import reverse

from tapiriik.settings import WEB_ROOT, RWGPS_APIKEY
from tapiriik.services.service_base import ServiceAuthenticationType, ServiceBase
from tapiriik.database import cachedb
from tapiriik.services.interchange import UploadedActivity, ActivityType, Waypoint, WaypointType, Location
from tapiriik.services.api import APIException, APIWarning, APIExcludeActivity, UserException, UserExceptionType
from tapiriik.services.tcx import TCXIO
from tapiriik.services.sessioncache import SessionCache

import logging
logger = logging.getLogger(__name__)

class RideWithGPSService(ServiceBase):
    ID = "rwgps"
    DisplayName = "Ride With GPS"
    DisplayAbbreviation = "RWG"
    AuthenticationType = ServiceAuthenticationType.UsernamePassword
    RequiresExtendedAuthorizationDetails = True

    # RWGPS does has a "recreation_types" list, but it is not actually used anywhere (yet)
    # (This is a subset of the things returned by that list for future reference...)
    _activityMappings = {
                                "running": ActivityType.Running,
                                "cycling": ActivityType.Cycling,
                                "mountain biking": ActivityType.MountainBiking,
                                "Hiking": ActivityType.Hiking,
                                "all": ActivityType.Other  # everything will eventually resolve to this
    }

    SupportedActivities = list(_activityMappings.values())

    SupportsHR = SupportsCadence = True

    _sessionCache = SessionCache(lifetime=timedelta(minutes=30), freshen_on_get=True)

    def _add_auth_params(self, params=None, record=None):
        """
        Adds apikey and authorization (email/password) to the passed-in params,
        returns modified params dict.
        """
        from tapiriik.auth.credential_storage import CredentialStore
        if params is None:
            params = {}
        params['apikey'] = RWGPS_APIKEY
        if record:
            cached = self._sessionCache.Get(record.ExternalID)
            if cached:
                return cached
            password = CredentialStore.Decrypt(record.ExtendedAuthorization["Password"])
            email = CredentialStore.Decrypt(record.ExtendedAuthorization["Email"])
            params['email'] = email
            params['password'] = password
        return params

    def WebInit(self):
        self.UserAuthorizationURL = WEB_ROOT + reverse("auth_simple", kwargs={"service": self.ID})

    def Authorize(self, email, password):
        from tapiriik.auth.credential_storage import CredentialStore
        res = requests.get("https://ridewithgps.com/users/current.json",
                           params={'email': email, 'password': password, 'apikey': RWGPS_APIKEY})
        res.raise_for_status()
        res = res.json()
        if res["user"] is None:
            raise APIException("Invalid login", block=True, user_exception=UserException(UserExceptionType.Authorization, intervention_required=True))
        member_id = res["user"]["id"]
        if not member_id:
            raise APIException("Unable to retrieve id", block=True, user_exception=UserException(UserExceptionType.Authorization, intervention_required=True))
        return (member_id, {}, {"Email": CredentialStore.Encrypt(email), "Password": CredentialStore.Encrypt(password)})

    def _duration_to_seconds(self, s):
        """
        Converts a duration in form HH:MM:SS to number of seconds for use in timedelta construction.
        """
        hours, minutes, seconds = (["0", "0"] + s.split(":"))[-3:]
        hours = int(hours)
        minutes = int(minutes)
        seconds = float(seconds)
        total_seconds = int(hours + 60000 * minutes + 1000 * seconds)
        return total_seconds

    def DownloadActivityList(self, serviceRecord, exhaustive=False):
        # http://ridewithgps.com/users/1/trips.json?limit=200&order_by=created_at&order_dir=asc
        # offset also supported
        page = 1
        pageSz = 50
        activities = []
        exclusions = []
        while True:
            logger.debug("Req with " + str({"start": (page - 1) * pageSz, "limit": pageSz}))
            # TODO: take advantage of their nice ETag support
            params = {"offset": (page - 1) * pageSz, "limit": pageSz}
            params = self._add_auth_params(params, record=serviceRecord)

            res = requests.get("http://ridewithgps.com/users/{}/trips.json".format(serviceRecord.ExternalID), params=params)
            res = res.json()
            total_pages = math.ceil(int(res["results_count"]) / pageSz)
            for act in res["results"]:
                if "first_lat" not in act or "last_lat" not in act:
                    exclusions.append(APIExcludeActivity("No points", activityId=act["activityId"], userException=UserException(UserExceptionType.Corrupt)))
                    continue
                if "distance" not in act:
                    exclusions.append(APIExcludeActivity("No distance", activityId=act["activityId"], userException=UserException(UserExceptionType.Corrupt)))
                    continue
                activity = UploadedActivity()

                activity.TZ = pytz.timezone(act["time_zone"])

                logger.debug("Name " + act["name"] + ":")
                if len(act["name"].strip()):
                    activity.Name = act["name"]

                activity.StartTime = pytz.utc.localize(datetime.strptime(act["departed_at"], "%Y-%m-%dT%H:%M:%SZ"))
                activity.EndTime = activity.StartTime + timedelta(seconds=self._duration_to_seconds(act["duration"]))
                logger.debug("Activity s/t " + str(activity.StartTime) + " on page " + str(page))
                activity.AdjustTZ()

                activity.Distance = float(act["distance"])  # This value is already in meters...
                # Activity type is not implemented yet in RWGPS results; we will assume cycling, though perhaps "OTHER" wouuld be correct
                activity.Type = ActivityType.Cycling

                activity.CalculateUID()
                activity.UploadedTo = [{"Connection": serviceRecord, "ActivityID": act["id"]}]
                activities.append(activity)
            logger.debug("Finished page {} of {}".format(page, total_pages))
            if not exhaustive or total_pages == page or total_pages == 0:
                break
            else:
                page += 1
        return activities, exclusions

    def DownloadActivity(self, serviceRecord, activity):
        # https://ridewithgps.com/trips/??????.gpx
        activityID = [x["ActivityID"] for x in activity.UploadedTo if x["Connection"] == serviceRecord][0]
        res = requests.get("https://ridewithgps.com/trips/{}.tcx".format(activityID),
                           params=self._add_auth_params({'sub_format': 'history'}, record=serviceRecord))
        try:
            TCXIO.Parse(res.content, activity)
        except ValueError as e:
            raise APIExcludeActivity("TCX parse error " + str(e), userException=UserException(UserExceptionType.Corrupt))

        return activity

    def UploadActivity(self, serviceRecord, activity):
        # https://ridewithgps.com/trips.json

        tcx_file = TCXIO.Dump(activity)
        files = {"data_file": ("tap-sync-" + str(os.getpid()) + "-" + activity.UID + ".tcx", tcx_file)}
        params = {}
        params['trip[name]'] = activity.Name
        params['trip[visibility]'] = 1 if activity.Private else 0 # Yes, this logic seems backwards but it's how it works

        res = requests.post("https://ridewithgps.com/trips.json", files=files,
                            params=self._add_auth_params(params, record=serviceRecord))
        if res.status_code % 100 == 4:
            raise APIException("Invalid login", block=True, user_exception=UserException(UserExceptionType.Authorization, intervention_required=True))
        res.raise_for_status()
        res = res.json()
        if res["success"] != 1:
            raise APIException("Unable to upload activity")


    def RevokeAuthorization(self, serviceRecord):
        # nothing to do here...
        pass

    def DeleteCachedData(self, serviceRecord):
        # nothing cached...
        pass

########NEW FILE########
__FILENAME__ = runkeeper
from tapiriik.settings import WEB_ROOT, RUNKEEPER_CLIENT_ID, RUNKEEPER_CLIENT_SECRET, AGGRESSIVE_CACHE
from tapiriik.services.service_base import ServiceAuthenticationType, ServiceBase
from tapiriik.services.service_record import ServiceRecord
from tapiriik.services.stream_sampling import StreamSampler
from tapiriik.services.api import APIException, UserException, UserExceptionType, APIExcludeActivity
from tapiriik.services.interchange import UploadedActivity, ActivityType, ActivityStatistic, ActivityStatisticUnit, WaypointType, Waypoint, Location, Lap
from tapiriik.database import cachedb
from django.core.urlresolvers import reverse
from datetime import datetime, timedelta
import requests
import urllib.parse
import json
import logging
logger = logging.getLogger(__name__)


class RunKeeperService(ServiceBase):
    ID = "runkeeper"
    DisplayName = "RunKeeper"
    DisplayAbbreviation = "RK"
    AuthenticationType = ServiceAuthenticationType.OAuth
    UserProfileURL = "http://runkeeper.com/user/{0}/profile"
    AuthenticationNoFrame = True  # Chrome update broke this

    _activityMappings = {"Running": ActivityType.Running,
                         "Cycling": ActivityType.Cycling,
                         "Mountain Biking": ActivityType.MountainBiking,
                         "Walking": ActivityType.Walking,
                         "Hiking": ActivityType.Hiking,
                         "Downhill Skiing": ActivityType.DownhillSkiing,
                         "Cross-Country Skiing": ActivityType.CrossCountrySkiing,
                         "Snowboarding": ActivityType.Snowboarding,
                         "Skating": ActivityType.Skating,
                         "Swimming": ActivityType.Swimming,
                         "Wheelchair": ActivityType.Wheelchair,
                         "Rowing": ActivityType.Rowing,
                         "Elliptical": ActivityType.Elliptical,
                         "Other": ActivityType.Other}
    SupportedActivities = list(_activityMappings.values())

    SupportsHR = True
    SupportsCalories = True

    _wayptTypeMappings = {"start": WaypointType.Start, "end": WaypointType.End, "pause": WaypointType.Pause, "resume": WaypointType.Resume}

    def WebInit(self):
        self.UserAuthorizationURL = "https://runkeeper.com/apps/authorize?client_id=" + RUNKEEPER_CLIENT_ID + "&response_type=code&redirect_uri=" + WEB_ROOT + reverse("oauth_return", kwargs={"service": "runkeeper"})

    def RetrieveAuthorizationToken(self, req, level):
        from tapiriik.services import Service

        #  might consider a real OAuth client
        code = req.GET.get("code")
        params = {"grant_type": "authorization_code", "code": code, "client_id": RUNKEEPER_CLIENT_ID, "client_secret": RUNKEEPER_CLIENT_SECRET, "redirect_uri": WEB_ROOT + reverse("oauth_return", kwargs={"service": "runkeeper"})}

        response = requests.post("https://runkeeper.com/apps/token", data=urllib.parse.urlencode(params), headers={"Content-Type": "application/x-www-form-urlencoded"})
        if response.status_code != 200:
            raise APIException("Invalid code")
        token = response.json()["access_token"]

        # hacky, but also totally their fault for not giving the user id in the token req
        existingRecord = Service.GetServiceRecordWithAuthDetails(self, {"Token": token})
        if existingRecord is None:
            uid = self._getUserId(ServiceRecord({"Authorization": {"Token": token}}))  # meh
        else:
            uid = existingRecord.ExternalID

        return (uid, {"Token": token})

    def RevokeAuthorization(self, serviceRecord):
        resp = requests.post("https://runkeeper.com/apps/de-authorize", data={"access_token": serviceRecord.Authorization["Token"]})
        if resp.status_code != 204 and resp.status_code != 200:
            raise APIException("Unable to deauthorize RK auth token, status " + str(resp.status_code) + " resp " + resp.text)
        pass

    def _apiHeaders(self, serviceRecord):
        return {"Authorization": "Bearer " + serviceRecord.Authorization["Token"]}

    def _getAPIUris(self, serviceRecord):
        if hasattr(self, "_uris"):  # cache these for the life of the batch job at least? hope so
            return self._uris
        else:
            response = requests.get("https://api.runkeeper.com/user/", headers=self._apiHeaders(serviceRecord))

            if response.status_code != 200:
                if response.status_code == 401 or response.status_code == 403:
                    raise APIException("No authorization to retrieve user URLs", block=True, user_exception=UserException(UserExceptionType.Authorization, intervention_required=True))
                raise APIException("Unable to retrieve user URLs" + str(response))

            uris = response.json()
            for k in uris.keys():
                if type(uris[k]) == str:
                    uris[k] = "https://api.runkeeper.com" + uris[k]
            self._uris = uris
            return uris

    def _getUserId(self, serviceRecord):
        resp = requests.get("https://api.runkeeper.com/user/", headers=self._apiHeaders(serviceRecord))
        data = resp.json()
        return data["userID"]

    def DownloadActivityList(self, serviceRecord, exhaustive=False):
        uris = self._getAPIUris(serviceRecord)

        allItems = []

        pageUri = uris["fitness_activities"]

        while True:
            response = requests.get(pageUri, headers=self._apiHeaders(serviceRecord))
            if response.status_code != 200:
                if response.status_code == 401 or response.status_code == 403:
                    raise APIException("No authorization to retrieve activity list", block=True, user_exception=UserException(UserExceptionType.Authorization, intervention_required=True))
                raise APIException("Unable to retrieve activity list " + str(response) + " " + response.text)
            data = response.json()
            allItems += data["items"]
            if not exhaustive or "next" not in data or data["next"] == "":
                break
            pageUri = "https://api.runkeeper.com" + data["next"]

        activities = []
        exclusions = []
        for act in allItems:
            try:
                activity = self._populateActivity(act)
            except KeyError as e:
                exclusions.append(APIExcludeActivity("Missing key in activity data " + str(e), activityId=act["uri"], userException=UserException(UserExceptionType.Corrupt)))
                continue

            logger.debug("\tActivity s/t " + str(activity.StartTime))
            if (activity.StartTime - activity.EndTime).total_seconds() == 0:
                exclusions.append(APIExcludeActivity("0-length", activityId=act["uri"]))
                continue  # these activites are corrupted
            activity.ServiceData = {"ActivityID": act["uri"]}
            activities.append(activity)
        return activities, exclusions

    def _populateActivity(self, rawRecord):
        ''' Populate the 1st level of the activity object with all details required for UID from RK API data '''
        activity = UploadedActivity()
        #  can stay local + naive here, recipient services can calculate TZ as required
        activity.StartTime = datetime.strptime(rawRecord["start_time"], "%a, %d %b %Y %H:%M:%S")
        activity.Stats.MovingTime = ActivityStatistic(ActivityStatisticUnit.Seconds, value=float(rawRecord["duration"])) # P. sure this is moving time
        activity.EndTime = activity.StartTime + timedelta(seconds=float(rawRecord["duration"])) # this is inaccurate with pauses - excluded from hash
        activity.Stats.Distance = ActivityStatistic(ActivityStatisticUnit.Meters, value=rawRecord["total_distance"])
        # I'm fairly sure this is how the RK calculation works. I remember I removed something exactly like this from ST.mobi, but I trust them more than I trust myself to get the speed right.
        if (activity.EndTime - activity.StartTime).total_seconds() > 0:
            activity.Stats.Speed = ActivityStatistic(ActivityStatisticUnit.KilometersPerHour, avg=activity.Stats.Distance.asUnits(ActivityStatisticUnit.Kilometers).Value / ((activity.EndTime - activity.StartTime).total_seconds() / 60 / 60))
        activity.Stats.Energy = ActivityStatistic(ActivityStatisticUnit.Kilocalories, value=rawRecord["total_calories"] if "total_calories" in rawRecord else None)
        if rawRecord["type"] in self._activityMappings:
            activity.Type = self._activityMappings[rawRecord["type"]]
        activity.GPS = rawRecord["has_path"]
        activity.CalculateUID()
        return activity

    def DownloadActivity(self, serviceRecord, activity):
        activityID = activity.ServiceData["ActivityID"]
        if AGGRESSIVE_CACHE:
            ridedata = cachedb.rk_activity_cache.find_one({"uri": activityID})
        if not AGGRESSIVE_CACHE or ridedata is None:
            response = requests.get("https://api.runkeeper.com" + activityID, headers=self._apiHeaders(serviceRecord))
            if response.status_code != 200:
                if response.status_code == 401 or response.status_code == 403:
                    raise APIException("No authorization to download activity" + activityID, block=True, user_exception=UserException(UserExceptionType.Authorization, intervention_required=True))
                raise APIException("Unable to download activity " + activityID + " response " + str(response) + " " + response.text)
            ridedata = response.json()
            ridedata["Owner"] = serviceRecord.ExternalID
            if AGGRESSIVE_CACHE:
                cachedb.rk_activity_cache.insert(ridedata)

        if "is_live" in ridedata and ridedata["is_live"] is True:
            raise APIExcludeActivity("Not complete", activityId=activityID, permanent=False, userException=UserException(UserExceptionType.LiveTracking))

        if "userID" in ridedata and int(ridedata["userID"]) != int(serviceRecord.ExternalID):
            raise APIExcludeActivity("Not the user's own activity", activityId=activityID, userException=UserException(UserExceptionType.Other))

        self._populateActivityWaypoints(ridedata, activity)

        if "climb" in ridedata:
            activity.Stats.Elevation = ActivityStatistic(ActivityStatisticUnit.Meters, gain=float(ridedata["climb"]))
        if "average_heart_rate" in ridedata:
            activity.Stats.HR = ActivityStatistic(ActivityStatisticUnit.BeatsPerMinute, avg=float(ridedata["average_heart_rate"]))
        activity.Stationary = activity.CountTotalWaypoints() <= 1

        # This could cause confusion, since when I upload activities to RK I populate the notes field with the activity name. My response is to... well... not sure.
        activity.Notes = ridedata["notes"] if "notes" in ridedata else None
        activity.Private = ridedata["share"] == "Just Me"
        return activity

    def _populateActivityWaypoints(self, rawData, activity):
        ''' populate the Waypoints collection from RK API data '''
        lap = Lap(stats=activity.Stats, startTime=activity.StartTime, endTime=activity.EndTime)
        activity.Laps = [lap]

        print(rawData.keys())
        streamData = {}
        for stream in ["path", "heart_rate", "calories", "distance"]:
            if stream in rawData and len(rawData[stream]):
                if stream == "path":
                    # The path stream doesn't follow the same naming convention, so we cheat and put everything in.
                    streamData[stream] = [(x["timestamp"], x) for x in rawData[stream]]
                else:
                    streamData[stream] = [(x["timestamp"], x[stream]) for x in rawData[stream]] # Change up format for StreamSampler

        def _addWaypoint(timestamp, path=None, heart_rate=None, calories=None, distance=None):
            waypoint = Waypoint(activity.StartTime + timedelta(seconds=timestamp))
            if path:
                waypoint.Location = Location(path["latitude"], path["longitude"], path["altitude"] if "altitude" in path and float(path["altitude"]) != 0 else None)  # if you're running near sea level, well...
                waypoint.Type = self._wayptTypeMappings[path["type"]] if path["type"] in self._wayptTypeMappings else WaypointType.Regular
            waypoint.HR = heart_rate
            waypoint.Calories = calories
            waypoint.Distance = distance

            lap.Waypoints.append(waypoint)
        activity.Stationary = len(lap.Waypoints) == 0
        if not activity.Stationary:
            lap.Waypoints[0].Type = WaypointType.Start
            lap.Waypoints[-1].Type = WaypointType.End

        StreamSampler.SampleWithCallback(_addWaypoint, streamData)

    def UploadActivity(self, serviceRecord, activity):
        #  assembly dict to post to RK
        uploadData = self._createUploadData(activity)
        uris = self._getAPIUris(serviceRecord)
        headers = self._apiHeaders(serviceRecord)
        headers["Content-Type"] = "application/vnd.com.runkeeper.NewFitnessActivity+json"
        response = requests.post(uris["fitness_activities"], headers=headers, data=json.dumps(uploadData))

        if response.status_code != 201:
            if response.status_code == 401 or response.status_code == 403:
                raise APIException("No authorization to upload activity " + activity.UID, block=True, user_exception=UserException(UserExceptionType.Authorization, intervention_required=True))
            raise APIException("Unable to upload activity " + activity.UID + " response " + str(response) + " " + response.text)
        return response.headers["location"]

    def _createUploadData(self, activity):
        ''' create data dict for posting to RK API '''
        record = {}

        record["type"] = [key for key in self._activityMappings if self._activityMappings[key] == activity.Type][0]
        record["start_time"] = activity.StartTime.strftime("%a, %d %b %Y %H:%M:%S")
        if activity.Stats.MovingTime.Value is not None:
            record["duration"] = activity.Stats.MovingTime.asUnits(ActivityStatisticUnit.Seconds).Value
        elif activity.Stats.TimerTime.Value is not None:
            record["duration"] = activity.Stats.TimerTime.asUnits(ActivityStatisticUnit.Seconds).Value
        else:
            record["duration"] = (activity.EndTime - activity.StartTime).total_seconds()

        if activity.Stats.HR.Average is not None:
            record["average_heart_rate"] = int(activity.Stats.HR.Average)
        if activity.Stats.Energy.Value is not None:
            record["total_calories"] = activity.Stats.Energy.asUnits(ActivityStatisticUnit.Kilocalories).Value
        if activity.Stats.Distance.Value is not None:
            record["total_distance"] = activity.Stats.Distance.asUnits(ActivityStatisticUnit.Meters).Value
        if activity.Name:
            record["notes"] = activity.Name  # not symetric, but better than nothing
        if activity.Private:
            record["share"] = "Just Me"

        if activity.CountTotalWaypoints() > 1:
            inPause = False
            for lap in activity.Laps:
                for waypoint in lap.Waypoints:
                    timestamp = (waypoint.Timestamp - activity.StartTime).total_seconds()

                    if waypoint.Type in self._wayptTypeMappings.values():
                        wpType = [key for key, value in self._wayptTypeMappings.items() if value == waypoint.Type][0]
                    else:
                        wpType = "gps"  # meh

                    if not inPause and waypoint.Type == WaypointType.Pause:
                        inPause = True
                    elif inPause and waypoint.Type == WaypointType.Pause:
                        continue # RK gets all crazy when you send it multiple pause waypoints in a row.
                    elif inPause and waypoint.Type != WaypointType.Pause:
                        inPause = False

                    if waypoint.Location is not None and waypoint.Location.Latitude is not None and waypoint.Location.Longitude is not None:
                        if "path" not in record:
                            record["path"] = []
                        pathPt = {"timestamp": timestamp,
                                  "latitude": waypoint.Location.Latitude,
                                  "longitude": waypoint.Location.Longitude,
                                  "type": wpType}
                        pathPt["altitude"] = waypoint.Location.Altitude if waypoint.Location.Altitude is not None else 0  # this is straight of of their "example calls" page
                        record["path"].append(pathPt)

                    if waypoint.HR is not None:
                        if "heart_rate" not in record:
                            record["heart_rate"] = []
                        record["heart_rate"].append({"timestamp": timestamp, "heart_rate": round(waypoint.HR)})

                    if waypoint.Calories is not None:
                        if "calories" not in record:
                            record["calories"] = []
                        record["calories"].append({"timestamp": timestamp, "calories": waypoint.Calories})

                    if waypoint.Distance is not None:
                        if "distance" not in record:
                            record["distance"] = []
                        record["distance"].append({"timestamp": timestamp, "distance": waypoint.Distance})

        return record

    def DeleteCachedData(self, serviceRecord):
        cachedb.rk_activity_cache.remove({"Owner": serviceRecord.ExternalID})

########NEW FILE########
__FILENAME__ = service
from tapiriik.services import *
from .service_record import ServiceRecord
from tapiriik.database import db, cachedb
from bson.objectid import ObjectId

# Really don't know why I didn't make most of this part of the ServiceBase.
class Service:
    _serviceMappings = {
                        "runkeeper": RunKeeper,
                        "strava": Strava,
                        "endomondo": Endomondo,
                        "dropbox": Dropbox,
                        "garminconnect": GarminConnect,
                        "sporttracks": SportTracks,
                        "rwgps": RideWithGPS,
                        "trainingpeaks": TrainingPeaks
                        }

    # These options are used as the back for all service record's configurations
    _globalConfigurationDefaults = {
        "sync_private": False,
        "allow_activity_flow_exception_bypass_via_self": False
    }

    def FromID(id):
        if id in Service._serviceMappings:
            return Service._serviceMappings[id]
        raise ValueError

    def List():
        return [RunKeeper, Strava, GarminConnect, SportTracks, Dropbox, TrainingPeaks, RideWithGPS, Endomondo]

    def PreferredDownloadPriorityList():
        # Ideally, we'd make an informed decision based on whatever features the activity had
        # ...but that would require either a) downloading it from evry service or b) storing a lot more activity metadata
        # So, I think this will do for now
        return [
            GarminConnect, # The reference
            SportTracks, # Pretty much equivalent to GC, no temperature (not that GC temperature works all thar well now, but I digress)
            TrainingPeaks, # No seperate run cadence, but has temperature
            Dropbox, # Equivalent to any of the above
            RideWithGPS, # Uses TCX for everything, so same as Dropbox
            Strava, # No laps
            Endomondo, # No laps, no cadence
            RunKeeper, # No laps, no cadence, no power
        ]

    def WebInit():
        from tapiriik.settings import WEB_ROOT
        from django.core.urlresolvers import reverse
        for itm in Service.List():
            itm.WebInit()
            itm.UserDisconnectURL = WEB_ROOT + reverse("auth_disconnect", kwargs={"service": itm.ID})

    def GetServiceRecordWithAuthDetails(service, authDetails):
        return ServiceRecord(db.connections.find_one({"Service": service.ID, "Authorization": authDetails}))

    def GetServiceRecordByID(uid):
        return ServiceRecord(db.connections.find_one({"_id": ObjectId(uid)}))

    def EnsureServiceRecordWithAuth(service, uid, authDetails, extendedAuthDetails=None, persistExtendedAuthDetails=False):
        if persistExtendedAuthDetails and not service.RequiresExtendedAuthorizationDetails:
            raise ValueError("Attempting to persist extended auth details on service that doesn't use them")
        # think this entire block could be replaced with an upsert...

        serviceRecord = ServiceRecord(db.connections.find_one({"ExternalID": uid, "Service": service.ID}))
        if serviceRecord is None:
            db.connections.insert({"ExternalID": uid, "Service": service.ID, "SynchronizedActivities": [], "Authorization": authDetails, "ExtendedAuthorization": extendedAuthDetails if persistExtendedAuthDetails else None})
            serviceRecord = ServiceRecord(db.connections.find_one({"ExternalID": uid, "Service": service.ID}))
            serviceRecord.ExtendedAuthorization = extendedAuthDetails # So SubscribeToPartialSyncTrigger can use it (we don't save the whole record after this point)
            if service.PartialSyncTriggerRequiresPolling:
                service.SubscribeToPartialSyncTrigger(serviceRecord) # The subscription is attached more to the remote account than to the local one, so we subscribe/unsubscribe here rather than in User.ConnectService, etc.
        elif serviceRecord.Authorization != authDetails or (hasattr(serviceRecord, "ExtendedAuthorization") and serviceRecord.ExtendedAuthorization != extendedAuthDetails):
            db.connections.update({"ExternalID": uid, "Service": service.ID}, {"$set": {"Authorization": authDetails, "ExtendedAuthorization": extendedAuthDetails if persistExtendedAuthDetails else None}})

        # if not persisted, these details are stored in the cache db so they don't get backed up
        if service.RequiresExtendedAuthorizationDetails:
            if not persistExtendedAuthDetails:
                cachedb.extendedAuthDetails.update({"ID": serviceRecord._id}, {"ID": serviceRecord._id, "ExtendedAuthorization": extendedAuthDetails}, upsert=True)
            else:
                cachedb.extendedAuthDetails.remove({"ID": serviceRecord._id})
        return serviceRecord

    def PersistExtendedAuthDetails(serviceRecord):
        if not serviceRecord.HasExtendedAuthorizationDetails():
            raise ValueError("No extended auth details to persist")
        if serviceRecord.ExtendedAuthorization:
            # Already persisted, nothing to do
            return
        extAuthRecord = cachedb.extendedAuthDetails.find_one({"ID": serviceRecord._id})
        if not extAuthRecord:
            raise ValueError("Service record claims to have extended auth, facts suggest otherwise")
        else:
            extAuth = extAuthRecord["ExtendedAuthorization"]
        db.connections.update({"_id": serviceRecord._id}, {"$set": {"ExtendedAuthorization": extAuth}})
        cachedb.extendedAuthDetails.remove({"ID": serviceRecord._id})

    def DeleteServiceRecord(serviceRecord):
        svc = serviceRecord.Service
        svc.DeleteCachedData(serviceRecord)
        if svc.PartialSyncTriggerRequiresPolling:
            svc.UnsubscribeFromPartialSyncTrigger(serviceRecord)
        svc.RevokeAuthorization(serviceRecord)
        cachedb.extendedAuthDetails.remove({"ID": serviceRecord._id})
        db.connections.remove({"_id": serviceRecord._id})

########NEW FILE########
__FILENAME__ = service_base
class ServiceAuthenticationType:
    OAuth = "oauth"
    UsernamePassword = "direct"

class InvalidServiceOperationException(Exception):
    pass

class ServiceBase:
    # Short ID used everywhere in logging and DB storage
    ID = None
    # Full display name given to users
    DisplayName = None
    # 2-3 letter abbreviated name
    DisplayAbbreviation = None

    # One of ServiceAuthenticationType
    AuthenticationType = None

    # Enables extended auth ("Save these details") functionality
    RequiresExtendedAuthorizationDetails = False

    # URL to direct user to when starting authentication
    UserAuthorizationURL = None

    # Don't attempt to IFrame the OAuth login
    AuthenticationNoFrame = False

    # List of ActivityTypes
    SupportedActivities = None

    # Used only in tests
    SupportsHR = SupportsCalories = SupportsCadence = SupportsTemp = SupportsPower = False

    # Does it?
    ReceivesStationaryActivities = True
    ReceivesNonGPSActivitiesWithOtherSensorData = True

    # Causes synchronizations to be skipped until...
    #  - One is triggered (via IDs returned by ServiceRecordIDsForPartialSyncTrigger or PollPartialSyncTrigger)
    #  - One is necessitated (non-partial sync, possibility of uploading new activities, etc)
    PartialSyncRequiresTrigger = False
    # Timedelta for polling to happen at (or None for no polling)
    PartialSyncTriggerPollInterval = None
    # How many times to call the polling method per interval (this is for the multiple_index kwarg)
    PartialSyncTriggerPollMultiple = 1

    @property
    def PartialSyncTriggerRequiresPolling(self):
        return self.PartialSyncRequiresTrigger and self.PartialSyncTriggerPollInterval

    # Adds the Setup button to the service configuration pane, and not much else
    Configurable = False
    # Defaults for per-service configuration
    ConfigurationDefaults = {}

    # For the diagnostics dashboard
    UserProfileURL = UserActivityURL = None

    def RequiresConfiguration(self, serviceRecord):  # Should convert this into a real property
        return False  # True means no sync until user configures

    def WebInit(self):
        pass

    def GenerateUserAuthorizationURL(self, level=None):
        raise NotImplementedError

    def Authorize(self, email, password, store=False):
        raise NotImplementedError

    def RevokeAuthorization(self, serviceRecord):
        raise NotImplementedError

    def DownloadActivityList(self, serviceRecord, exhaustive=False):
        raise NotImplementedError

    def DownloadActivity(self, serviceRecord, activity):
        raise NotImplementedError

    def UploadActivity(self, serviceRecord, activity):
        raise NotImplementedError

    def DeleteCachedData(self, serviceRecord):
        raise NotImplementedError

    def SubscribeToPartialSyncTrigger(self, serviceRecord):
        if self.PartialSyncRequiresTrigger:
            raise NotImplementedError
        else:
            raise InvalidServiceOperationException

    def UnsubscribeFromPartialSyncTrigger(self, serviceRecord):
        if self.PartialSyncRequiresTrigger:
            raise NotImplementedError
        else:
            raise InvalidServiceOperationException

    def ShouldForcePartialSyncTrigger(self, serviceRecord):
        if self.PartialSyncRequiresTrigger:
            return False
        else:
            raise InvalidServiceOperationException

    def PollPartialSyncTrigger(self, multiple_index):
        if self.PartialSyncRequiresTrigger and self.PartialSyncTriggerPollInterval:
            raise NotImplementedError
        else:
            raise InvalidServiceOperationException

    def ServiceRecordIDsForPartialSyncTrigger(self, req):
        raise NotImplementedError

    def ConfigurationUpdating(self, serviceRecord, newConfig, oldConfig):
        pass

########NEW FILE########
__FILENAME__ = service_record
from tapiriik.database import cachedb, db
import copy

class ServiceRecord:
    def __new__(cls, dbRec):
        if not dbRec:
            return None
        return super(ServiceRecord, cls).__new__(cls)
    def __init__(self, dbRec):
        self.__dict__.update(dbRec)
    def __repr__(self):
        return "<ServiceRecord> " + str(self.__dict__)

    def __eq__(self, other):
        return self._id == other._id

    def __ne__(self, other):
        return not self.__eq__(other)

    def __deepcopy__(self, x):
        return ServiceRecord(self.__dict__)

    ExcludedActivities = {}
    Config = {}
    PartialSyncTriggerSubscribed = False

    @property
    def Service(self):
        from tapiriik.services import Service
        return Service.FromID(self.__dict__["Service"])

    def HasExtendedAuthorizationDetails(self, persisted_only=False):
        if not self.Service.RequiresExtendedAuthorizationDetails:
            return False
        if "ExtendedAuthorization" in self.__dict__ and self.ExtendedAuthorization:
            return True
        if persisted_only:
            return False
        return cachedb.extendedAuthDetails.find({"ID": self._id}).limit(1).count()

    def SetPartialSyncTriggerSubscriptionState(self, subscribed):
        db.connections.update({"_id": self._id}, {"$set": {"PartialSyncTriggerSubscribed": subscribed}})

    def GetConfiguration(self):
        from tapiriik.services import Service
        svc = self.Service
        config = copy.deepcopy(Service._globalConfigurationDefaults)
        config.update(svc.ConfigurationDefaults)
        config.update(self.Config)
        return config

    def SetConfiguration(self, config, no_save=False, drop_existing=False):
        from tapiriik.services import Service
        sparseConfig = {}
        if not drop_existing:
            sparseConfig = copy.deepcopy(self.GetConfiguration())
        sparseConfig.update(config)

        svc = self.Service
        svc.ConfigurationUpdating(self, config, self.GetConfiguration())
        keys_to_delete = []
        for k, v in sparseConfig.items():
            if (k in svc.ConfigurationDefaults and svc.ConfigurationDefaults[k] == v) or (k in Service._globalConfigurationDefaults and Service._globalConfigurationDefaults[k] == v):
                keys_to_delete.append(k)  # it's the default, we can not store it
        for k in keys_to_delete:
            del sparseConfig[k]
        self.Config = sparseConfig
        if not no_save:
            db.connections.update({"_id": self._id}, {"$set": {"Config": sparseConfig}})

########NEW FILE########
__FILENAME__ = sessioncache
from datetime import datetime

class SessionCache:
	def __init__(self, lifetime, freshen_on_get=False):
		self._lifetime = lifetime
		self._autorefresh = freshen_on_get
		self._cache = {}

	def Get(self, pk, freshen=False):
		if pk not in self._cache:
			return
		record = self._cache[pk]
		if record.Expired():
			del self._cache[pk]
			return None
		if self._autorefresh or freshen:
			record.Refresh()
		return record.Get()

	def Set(self, pk, value):
		self._cache[pk] = SessionCacheRecord(value, self._lifetime)

class SessionCacheRecord:
	def __init__(self, data, lifetime):
		self._value = data
		self._lifetime = lifetime
		self.Refresh()

	def Expired(self):
		return self._timestamp < datetime.utcnow() - self._lifetime

	def Refresh(self):
		self._timestamp = datetime.utcnow()

	def Get(self):
		return self._value

########NEW FILE########
__FILENAME__ = sporttracks
from tapiriik.settings import WEB_ROOT, SPORTTRACKS_OPENFIT_ENDPOINT, SPORTTRACKS_CLIENT_ID, SPORTTRACKS_CLIENT_SECRET
from tapiriik.services.service_base import ServiceAuthenticationType, ServiceBase
from tapiriik.services.interchange import UploadedActivity, ActivityType, ActivityStatistic, ActivityStatisticUnit, Waypoint, WaypointType, Location, LapIntensity, Lap
from tapiriik.services.api import APIException, UserException, UserExceptionType, APIExcludeActivity
from tapiriik.services.sessioncache import SessionCache
from tapiriik.database import cachedb
from django.core.urlresolvers import reverse
import pytz
from datetime import timedelta
import dateutil.parser
from dateutil.tz import tzutc
import requests
import json
import re
import urllib.parse

import logging
logger = logging.getLogger(__name__)

class SportTracksService(ServiceBase):
    ID = "sporttracks"
    DisplayName = "SportTracks"
    DisplayAbbreviation = "ST"
    AuthenticationType = ServiceAuthenticationType.OAuth
    OpenFitEndpoint = SPORTTRACKS_OPENFIT_ENDPOINT
    SupportsHR = True

    """ Other   Basketball
        Other   Boxing
        Other   Climbing
        Other   Driving
        Other   Flying
        Other   Football
        Other   Gardening
        Other   Kitesurf
        Other   Sailing
        Other   Soccer
        Other   Tennis
        Other   Volleyball
        Other   Windsurf
        Running Hashing
        Running Hills
        Running Intervals
        Running Orienteering
        Running Race
        Running Road
        Running Showshoe
        Running Speed
        Running Stair
        Running Track
        Running Trail
        Running Treadmill
        Cycling Hills
        Cycling Indoor
        Cycling Intervals
        Cycling Mountain
        Cycling Race
        Cycling Road
        Cycling Rollers
        Cycling Spinning
        Cycling Track
        Cycling Trainer
        Swimming    Open Water
        Swimming    Pool
        Swimming    Race
        Walking Geocaching
        Walking Hiking
        Walking Nordic
        Walking Photography
        Walking Snowshoe
        Walking Treadmill
        Skiing  Alpine
        Skiing  Nordic
        Skiing  Roller
        Skiing  Snowboard
        Rowing  Canoe
        Rowing  Kayak
        Rowing  Kitesurf
        Rowing  Ocean Kayak
        Rowing  Rafting
        Rowing  Rowing Machine
        Rowing  Sailing
        Rowing  Standup Paddling
        Rowing  Windsurf
        Skating Board
        Skating Ice
        Skating Inline
        Skating Race
        Skating Track
        Gym Aerobics
        Gym Elliptical
        Gym Plyometrics
        Gym Rowing Machine
        Gym Spinning
        Gym Stair Climber
        Gym Stationary Bike
        Gym Strength
        Gym Stretching
        Gym Treadmill
        Gym Yoga
    """

    _activityMappings = {
        "running": ActivityType.Running,
        "cycling": ActivityType.Cycling,
        "mountain": ActivityType.MountainBiking,
        "walking": ActivityType.Walking,
        "hiking": ActivityType.Hiking,
        "snowboarding": ActivityType.Snowboarding,
        "skiing": ActivityType.DownhillSkiing,
        "nordic": ActivityType.CrossCountrySkiing,
        "skating": ActivityType.Skating,
        "swimming": ActivityType.Swimming,
        "rowing": ActivityType.Rowing,
        "elliptical": ActivityType.Elliptical,
        "gym": ActivityType.Gym,
        "other": ActivityType.Other
    }

    _reverseActivityMappings = {
        ActivityType.Running: "running",
        ActivityType.Cycling: "cycling",
        ActivityType.Walking: "walking",
        ActivityType.MountainBiking: "cycling: mountain",
        ActivityType.Hiking: "walking: hiking",
        ActivityType.CrossCountrySkiing: "skiing: nordic",  #  Equipment.Bindings.IsToeOnly ??
        ActivityType.DownhillSkiing: "skiing",
        ActivityType.Snowboarding: "skiing: snowboarding",
        ActivityType.Skating: "skating",
        ActivityType.Swimming: "swimming",
        ActivityType.Rowing: "rowing",
        ActivityType.Elliptical: "gym: elliptical",
        ActivityType.Gym: "gym",
        ActivityType.Other: "other"
    }

    SupportedActivities = list(_reverseActivityMappings.keys())

    _tokenCache = SessionCache(lifetime=timedelta(minutes=115), freshen_on_get=False)

    def WebInit(self):
        self.UserAuthorizationURL = "https://api.sporttracks.mobi/oauth2/authorize?response_type=code&client_id=%s&state=mobi_api" % SPORTTRACKS_CLIENT_ID

    def _getAuthHeaders(self, serviceRecord=None):
        token = self._tokenCache.Get(serviceRecord.ExternalID)
        if not token:
            if not serviceRecord.Authorization or "RefreshToken" not in serviceRecord.Authorization:
                # When I convert the existing users, people who didn't check the remember-credentials box will be stuck in limbo
                raise APIException("User not upgraded to OAuth", block=True, user_exception=UserException(UserExceptionType.Authorization, intervention_required=True))

            # Use refresh token to get access token
            # Hardcoded return URI to get around the lack of URL reversing without loading up all the Django stuff
            params = {"grant_type": "refresh_token", "refresh_token": serviceRecord.Authorization["RefreshToken"], "client_id": SPORTTRACKS_CLIENT_ID, "client_secret": SPORTTRACKS_CLIENT_SECRET, "redirect_uri": "https://tapiriik.com/auth/return/sporttracks"}
            response = requests.post("https://api.sporttracks.mobi/oauth2/token", data=urllib.parse.urlencode(params), headers={"Content-Type": "application/x-www-form-urlencoded"})
            if response.status_code != 200:
                if response.status_code >= 400 and response.status_code < 500:
                    raise APIException("Could not retrieve refreshed token %s %s" % (response.status_code, response.text), block=True, user_exception=UserException(UserExceptionType.Authorization, intervention_required=True))
                raise APIException("Could not retrieve refreshed token %s %s" % (response.status_code, response.text))
            token = response.json()["access_token"]
            self._tokenCache.Set(serviceRecord.ExternalID, token)

        return {"Authorization": "Bearer %s" % token}

    def RetrieveAuthorizationToken(self, req, level):
        from tapiriik.services import Service
        #  might consider a real OAuth client
        code = req.GET.get("code")
        params = {"grant_type": "authorization_code", "code": code, "client_id": SPORTTRACKS_CLIENT_ID, "client_secret": SPORTTRACKS_CLIENT_SECRET, "redirect_uri": WEB_ROOT + reverse("oauth_return", kwargs={"service": "sporttracks"})}

        response = requests.post("https://api.sporttracks.mobi/oauth2/token", data=urllib.parse.urlencode(params), headers={"Content-Type": "application/x-www-form-urlencoded"})
        if response.status_code != 200:
            print(response.text)
            raise APIException("Invalid code")
        access_token = response.json()["access_token"]
        refresh_token = response.json()["refresh_token"]

        existingRecord = Service.GetServiceRecordWithAuthDetails(self, {"Token": access_token})
        if existingRecord is None:
            uid_res = requests.post("https://api.sporttracks.mobi/api/v2/system/connect", headers={"Authorization": "Bearer %s" % access_token})
            uid = uid_res.json()["user"]["uid"]
        else:
            uid = existingRecord.ExternalID

        return (uid, {"RefreshToken": refresh_token})

    def RevokeAuthorization(self, serviceRecord):
        pass  # Can't revoke these tokens :(

    def DeleteCachedData(self, serviceRecord):
        cachedb.sporttracks_meta_cache.remove({"ExternalID": serviceRecord.ExternalID})

    def DownloadActivityList(self, serviceRecord, exhaustive=False):
        headers = self._getAuthHeaders(serviceRecord)
        activities = []
        exclusions = []
        pageUri = self.OpenFitEndpoint + "/fitnessActivities.json"

        activity_tz_cache_raw = cachedb.sporttracks_meta_cache.find_one({"ExternalID": serviceRecord.ExternalID})
        activity_tz_cache_raw = activity_tz_cache_raw if activity_tz_cache_raw else {"Activities":[]}
        activity_tz_cache = dict([(x["ActivityURI"], x["TZ"]) for x in activity_tz_cache_raw["Activities"]])

        while True:
            logger.debug("Req against " + pageUri)
            res = requests.get(pageUri, headers=headers)
            try:
                res = res.json()
            except ValueError:
                raise APIException("Could not decode activity list response %s %s" % (res.status_code, res.text))
            for act in res["items"]:
                activity = UploadedActivity()
                activity.ServiceData = {"ActivityURI": act["uri"]}

                if len(act["name"].strip()):
                    activity.Name = act["name"]
                    # Longstanding ST.mobi bug causes it to return negative partial-hour timezones as "-2:-30" instead of "-2:30"
                fixed_start_time = re.sub(r":-(\d\d)", r":\1", act["start_time"])
                activity.StartTime = dateutil.parser.parse(fixed_start_time)
                if isinstance(activity.StartTime.tzinfo, tzutc):
                    activity.TZ = pytz.utc # The dateutil tzutc doesn't have an _offset value.
                else:
                    activity.TZ = pytz.FixedOffset(activity.StartTime.tzinfo.utcoffset(activity.StartTime).total_seconds() / 60)  # Convert the dateutil lame timezones into pytz awesome timezones.

                activity.StartTime = activity.StartTime.replace(tzinfo=activity.TZ)
                activity.EndTime = activity.StartTime + timedelta(seconds=float(act["duration"]))
                activity.Stats.TimerTime = ActivityStatistic(ActivityStatisticUnit.Seconds, value=float(act["duration"]))  # OpenFit says this excludes paused times.

                # Sometimes activities get returned with a UTC timezone even when they are clearly not in UTC.
                if activity.TZ == pytz.utc:
                    if act["uri"] in activity_tz_cache:
                        activity.TZ = pytz.FixedOffset(activity_tz_cache[act["uri"]])
                    else:
                        # So, we get the first location in the activity and calculate the TZ from that.
                        try:
                            firstLocation = self._downloadActivity(serviceRecord, activity, returnFirstLocation=True)
                        except APIExcludeActivity:
                            pass
                        else:
                            try:
                                activity.CalculateTZ(firstLocation, recalculate=True)
                            except:
                                # We tried!
                                pass
                            else:
                                activity.AdjustTZ()
                            finally:
                                activity_tz_cache[act["uri"]] = activity.StartTime.utcoffset().total_seconds() / 60

                logger.debug("Activity s/t " + str(activity.StartTime))
                activity.Stats.Distance = ActivityStatistic(ActivityStatisticUnit.Meters, value=float(act["total_distance"]))

                types = [x.strip().lower() for x in act["type"].split(":")]
                types.reverse()  # The incoming format is like "walking: hiking" and we want the most specific first
                activity.Type = None
                for type_key in types:
                    if type_key in self._activityMappings:
                        activity.Type = self._activityMappings[type_key]
                        break
                if not activity.Type:
                    exclusions.append(APIExcludeActivity("Unknown activity type %s" % act["type"], activityId=act["uri"], userException=UserException(UserExceptionType.Other)))
                    continue

                activity.CalculateUID()
                activities.append(activity)
            if not exhaustive or "next" not in res or not len(res["next"]):
                break
            else:
                pageUri = res["next"]
        logger.debug("Writing back meta cache")
        cachedb.sporttracks_meta_cache.update({"ExternalID": serviceRecord.ExternalID}, {"ExternalID": serviceRecord.ExternalID, "Activities": [{"ActivityURI": k, "TZ": v} for k, v in activity_tz_cache.items()]}, upsert=True)
        return activities, exclusions

    def _downloadActivity(self, serviceRecord, activity, returnFirstLocation=False):
        activityURI = activity.ServiceData["ActivityURI"]
        headers = self._getAuthHeaders(serviceRecord)
        activityData = requests.get(activityURI, headers=headers)
        activityData = activityData.json()

        if "clock_duration" in activityData:
            activity.EndTime = activity.StartTime + timedelta(seconds=float(activityData["clock_duration"]))

        activity.Private = "sharing" in activityData and activityData["sharing"] != "public"

        activity.GPS = False # Gets set back if there is GPS data

        if "notes" in activityData:
            activity.Notes = activityData["notes"]

        activity.Stats.Energy = ActivityStatistic(ActivityStatisticUnit.Kilojoules, value=float(activityData["calories"]))

        activity.Stats.Elevation = ActivityStatistic(ActivityStatisticUnit.Meters, gain=float(activityData["elevation_gain"]) if "elevation_gain" in activityData else None, loss=float(activityData["elevation_loss"]) if "elevation_loss" in activityData else None)

        activity.Stats.HR = ActivityStatistic(ActivityStatisticUnit.BeatsPerMinute, avg=activityData["avg_heartrate"] if "avg_heartrate" in activityData else None, max=activityData["max_heartrate"] if "max_heartrate" in activityData else None)
        activity.Stats.Cadence = ActivityStatistic(ActivityStatisticUnit.RevolutionsPerMinute, avg=activityData["avg_cadence"] if "avg_cadence" in activityData else None, max=activityData["max_cadence"] if "max_cadence" in activityData else None)
        activity.Stats.Power = ActivityStatistic(ActivityStatisticUnit.Watts, avg=activityData["avg_power"] if "avg_power" in activityData else None, max=activityData["max_power"] if "max_power" in activityData else None)

        laps_info = []
        laps_starts = []
        if "laps" in activityData:
            laps_info = activityData["laps"]
            for lap in activityData["laps"]:
                laps_starts.append(dateutil.parser.parse(lap["start_time"]))
        lap = None
        for lapinfo in laps_info:
            lap = Lap()
            activity.Laps.append(lap)
            lap.StartTime = dateutil.parser.parse(lapinfo["start_time"])
            lap.EndTime = lap.StartTime + timedelta(seconds=lapinfo["clock_duration"])
            if "type" in lapinfo:
                lap.Intensity = LapIntensity.Active if lapinfo["type"] == "ACTIVE" else LapIntensity.Rest
            if "distance" in lapinfo:
                lap.Stats.Distance = ActivityStatistic(ActivityStatisticUnit.Meters, value=float(lapinfo["distance"]))
            if "duration" in lapinfo:
                lap.Stats.TimerTime = ActivityStatistic(ActivityStatisticUnit.Seconds, value=lapinfo["duration"])
            if "calories" in lapinfo:
                lap.Stats.Energy = ActivityStatistic(ActivityStatisticUnit.Kilojoules, value=lapinfo["calories"])
            if "elevation_gain" in lapinfo:
                lap.Stats.Elevation.update(ActivityStatistic(ActivityStatisticUnit.Meters, gain=float(lapinfo["elevation_gain"])))
            if "elevation_loss" in lapinfo:
                lap.Stats.Elevation.update(ActivityStatistic(ActivityStatisticUnit.Meters, loss=float(lapinfo["elevation_loss"])))
            if "max_speed" in lapinfo:
                lap.Stats.Speed.update(ActivityStatistic(ActivityStatisticUnit.MetersPerSecond, max=float(lapinfo["max_speed"])))
            if "max_speed" in lapinfo:
                lap.Stats.Speed.update(ActivityStatistic(ActivityStatisticUnit.MetersPerSecond, max=float(lapinfo["max_speed"])))
            if "avg_speed" in lapinfo:
                lap.Stats.Speed.update(ActivityStatistic(ActivityStatisticUnit.MetersPerSecond, avg=float(lapinfo["avg_speed"])))
            if "max_heartrate" in lapinfo:
                lap.Stats.HR.update(ActivityStatistic(ActivityStatisticUnit.BeatsPerMinute, max=float(lapinfo["max_heartrate"])))
            if "avg_heartrate" in lapinfo:
                lap.Stats.HR.update(ActivityStatistic(ActivityStatisticUnit.BeatsPerMinute, avg=float(lapinfo["avg_heartrate"])))
        if lap is None: # No explicit laps => make one that encompasses the entire activity
            lap = Lap()
            activity.Laps.append(lap)
            lap.Stats = activity.Stats
            lap.StartTime = activity.StartTime
            lap.EndTime = activity.EndTime
        elif len(activity.Laps) == 1:
            activity.Stats.update(activity.Laps[0].Stats) # Lap stats have a bit more info generally.
            activity.Laps[0].Stats = activity.Stats

        timerStops = []
        if "timer_stops" in activityData:
            for stop in activityData["timer_stops"]:
                timerStops.append([dateutil.parser.parse(stop[0]), dateutil.parser.parse(stop[1])])

        def isInTimerStop(timestamp):
            for stop in timerStops:
                if timestamp >= stop[0] and timestamp < stop[1]:
                    return True
                if timestamp >= stop[1]:
                    return False
            return False

        # Collate the individual streams into our waypoints.
        # Global sample rate is variable - will pick the next nearest stream datapoint.
        # Resampling happens on a lookbehind basis - new values will only appear their timestamp has been reached/passed

        wasInPause = False
        currentLapIdx = 0
        lap = activity.Laps[currentLapIdx]

        streams = []
        for stream in ["location", "elevation", "heartrate", "power", "cadence", "distance"]:
            if stream in activityData:
                streams.append(stream)
        stream_indices = dict([(stream, -1) for stream in streams]) # -1 meaning the stream has yet to start
        stream_lengths = dict([(stream, len(activityData[stream])/2) for stream in streams])
        # Data comes as "stream":[timestamp,value,timestamp,value,...]
        stream_values = {}
        for stream in streams:
            values = []
            for x in range(0,int(len(activityData[stream])/2)):
                values.append((activityData[stream][x * 2], activityData[stream][x * 2 + 1]))
            stream_values[stream] = values

        currentOffset = 0

        def streamVal(stream):
            nonlocal stream_values, stream_indices
            return stream_values[stream][stream_indices[stream]][1]

        def hasStreamData(stream):
            nonlocal stream_indices, streams
            return stream in streams and stream_indices[stream] >= 0

        while True:
            advance_stream = None
            advance_offset = None
            for stream in streams:
                if stream_indices[stream] + 1 == stream_lengths[stream]:
                    continue # We're at the end - can't advance
                if advance_offset is None or stream_values[stream][stream_indices[stream] + 1][0] - currentOffset < advance_offset:
                    advance_offset = stream_values[stream][stream_indices[stream] + 1][0] - currentOffset
                    advance_stream = stream
            if not advance_stream:
                break # We've hit the end of every stream, stop
            # Advance streams sharing the current timestamp
            for stream in streams:
                if stream == advance_stream:
                    continue # For clarity, we increment this later
                if stream_indices[stream] + 1 == stream_lengths[stream]:
                    continue # We're at the end - can't advance
                if stream_values[stream][stream_indices[stream] + 1][0] == stream_values[advance_stream][stream_indices[advance_stream] + 1][0]:
                    stream_indices[stream] += 1
            stream_indices[advance_stream] += 1 # Advance the key stream for this waypoint
            currentOffset = stream_values[advance_stream][stream_indices[advance_stream]][0] # Update the current time offset

            waypoint = Waypoint(activity.StartTime + timedelta(seconds=currentOffset))

            if hasStreamData("location"):
                waypoint.Location = Location(streamVal("location")[0], streamVal("location")[1], None)
                activity.GPS = True
                if returnFirstLocation:
                    return waypoint.Location

            if hasStreamData("elevation"):
                if not waypoint.Location:
                    waypoint.Location = Location(None, None, None)
                waypoint.Location.Altitude = streamVal("elevation")

            if hasStreamData("heartrate"):
                waypoint.HR = streamVal("heartrate")

            if hasStreamData("power"):
                waypoint.Power = streamVal("power")

            if hasStreamData("cadence"):
                waypoint.Cadence = streamVal("cadence")

            if hasStreamData("distance"):
                waypoint.Distance = streamVal("distance")

            inPause = isInTimerStop(waypoint.Timestamp)
            waypoint.Type = WaypointType.Regular if not inPause else WaypointType.Pause
            if wasInPause and not inPause:
                waypoint.Type = WaypointType.Resume
            wasInPause = inPause

            # We only care if it's possible to start a new lap, i.e. there are more left
            if currentLapIdx + 1 < len(laps_starts):
                if laps_starts[currentLapIdx + 1] < waypoint.Timestamp:
                    # A new lap has started
                    currentLapIdx += 1
                    lap = activity.Laps[currentLapIdx]

            lap.Waypoints.append(waypoint)

        if returnFirstLocation:
            return None  # I guess there were no waypoints?
        if activity.CountTotalWaypoints():
            activity.GetFlatWaypoints()[0].Type = WaypointType.Start
            activity.GetFlatWaypoints()[-1].Type = WaypointType.End
            activity.Stationary = False
        else:
            activity.Stationary = True

        return activity

    def DownloadActivity(self, serviceRecord, activity):
        return self._downloadActivity(serviceRecord, activity)

    def UploadActivity(self, serviceRecord, activity):
        activityData = {}
        # Props to the SportTracks API people for seamlessly supprting activities with or without TZ data.
        activityData["start_time"] = activity.StartTime.isoformat()
        if activity.Name:
            activityData["name"] = activity.Name
        if activity.Notes:
            activityData["notes"] = activity.Notes
        activityData["sharing"] = "public" if not activity.Private else "private"
        activityData["type"] = self._reverseActivityMappings[activity.Type]

        def _resolveDuration(obj):
            if obj.Stats.TimerTime.Value is not None:
                return obj.Stats.TimerTime.asUnits(ActivityStatisticUnit.Seconds).Value
            if obj.Stats.MovingTime.Value is not None:
                return obj.Stats.MovingTime.asUnits(ActivityStatisticUnit.Seconds).Value
            return (obj.EndTime - obj.StartTime).total_seconds()

        def _mapStat(dict, key, val, naturalValue=False):
            if val is not None:
                if naturalValue:
                    val = round(val)
                dict[key] = val
        _mapStat(activityData, "clock_duration", (activity.EndTime - activity.StartTime).total_seconds())
        _mapStat(activityData, "duration", _resolveDuration(activity)) # This has to be set, otherwise all time shows up as "stopped" :(
        _mapStat(activityData, "total_distance", activity.Stats.Distance.asUnits(ActivityStatisticUnit.Meters).Value)
        _mapStat(activityData, "calories", activity.Stats.Energy.asUnits(ActivityStatisticUnit.Kilojoules).Value, naturalValue=True)
        _mapStat(activityData, "elevation_gain", activity.Stats.Elevation.Gain)
        _mapStat(activityData, "elevation_loss", activity.Stats.Elevation.Loss)
        _mapStat(activityData, "max_speed", activity.Stats.Speed.Max)
        _mapStat(activityData, "avg_heartrate", activity.Stats.HR.Average)
        _mapStat(activityData, "max_heartrate", activity.Stats.HR.Max)
        _mapStat(activityData, "avg_cadence", activity.Stats.Cadence.Average)
        _mapStat(activityData, "max_cadence", activity.Stats.Cadence.Max)
        _mapStat(activityData, "avg_power", activity.Stats.Power.Average)
        _mapStat(activityData, "max_power", activity.Stats.Power.Max)

        activityData["laps"] = []
        lapNum = 0
        for lap in activity.Laps:
            lapNum += 1
            lapinfo = {
                "number": lapNum,
                "start_time": lap.StartTime.isoformat(),
                "type": "REST" if lap.Intensity == LapIntensity.Rest else "ACTIVE"
            }
            _mapStat(lapinfo, "clock_duration", (lap.EndTime - lap.StartTime).total_seconds()) # Required too.
            _mapStat(lapinfo, "duration", _resolveDuration(lap)) # This field is required for laps to be created.
            _mapStat(lapinfo, "distance", lap.Stats.Distance.asUnits(ActivityStatisticUnit.Meters).Value) # Probably required.
            _mapStat(lapinfo, "calories", lap.Stats.Energy.asUnits(ActivityStatisticUnit.Kilojoules).Value, naturalValue=True)
            _mapStat(lapinfo, "elevation_gain", lap.Stats.Elevation.Gain)
            _mapStat(lapinfo, "elevation_loss", lap.Stats.Elevation.Loss)
            _mapStat(lapinfo, "max_speed", lap.Stats.Speed.Max)
            _mapStat(lapinfo, "avg_heartrate", lap.Stats.HR.Average)
            _mapStat(lapinfo, "max_heartrate", lap.Stats.HR.Max)

            activityData["laps"].append(lapinfo)
        if not activity.Stationary:
            timer_stops = []
            timer_stopped_at = None

            def stream_append(stream, wp, data):
                stream += [round((wp.Timestamp - activity.StartTime).total_seconds()), data]

            location_stream = []
            distance_stream = []
            elevation_stream = []
            heartrate_stream = []
            power_stream = []
            cadence_stream = []
            for lap in activity.Laps:
                for wp in lap.Waypoints:
                    if wp.Location and wp.Location.Latitude and wp.Location.Longitude:
                        stream_append(location_stream, wp, [wp.Location.Latitude, wp.Location.Longitude])
                    if wp.HR:
                        stream_append(heartrate_stream, wp, round(wp.HR))
                    if wp.Distance:
                        stream_append(distance_stream, wp, wp.Distance)
                    if wp.Cadence or wp.RunCadence:
                        stream_append(cadence_stream, wp, round(wp.Cadence) if wp.Cadence else round(wp.RunCadence))
                    if wp.Power:
                        stream_append(power_stream, wp, wp.Power)
                    if wp.Location and wp.Location.Altitude:
                        stream_append(elevation_stream, wp, wp.Location.Altitude)
                    if wp.Type == WaypointType.Pause and not timer_stopped_at:
                        timer_stopped_at = wp.Timestamp
                    if wp.Type != WaypointType.Pause and timer_stopped_at:
                        timer_stops.append([timer_stopped_at, wp.Timestamp])
                        timer_stopped_at = None

            activityData["elevation"] = elevation_stream
            activityData["heartrate"] = heartrate_stream
            activityData["power"] = power_stream
            activityData["cadence"] = cadence_stream
            activityData["distance"] = distance_stream
            activityData["location"] = location_stream
            activityData["timer_stops"] = [[y.isoformat() for y in x] for x in timer_stops]

        headers = self._getAuthHeaders(serviceRecord)
        headers.update({"Content-Type": "application/json"})
        upload_resp = requests.post(self.OpenFitEndpoint + "/fitnessActivities.json", data=json.dumps(activityData), headers=headers)
        if upload_resp.status_code != 200:
            if upload_resp.status_code == 401:
                raise APIException("ST.mobi trial expired", block=True, user_exception=UserException(UserExceptionType.AccountExpired, intervention_required=True))
            raise APIException("Unable to upload activity %s" % upload_resp.text)
        return upload_resp.json()["uris"][0]



########NEW FILE########
__FILENAME__ = statistic_calculator
from datetime import timedelta
from .interchange import WaypointType

class ActivityStatisticCalculator:
    ImplicitPauseTime = timedelta(minutes=1, seconds=5)

    def CalculateDistance(act, startWpt=None, endWpt=None):
        import math
        dist = 0
        altHold = None  # seperate from the lastLoc variable, since we want to hold the altitude as long as required
        lastTimestamp = lastLoc = None

        flatWaypoints = act.GetFlatWaypoints()

        if not startWpt:
            startWpt = flatWaypoints[0]
        if not endWpt:
            endWpt = flatWaypoints[-1]

        for x in range(flatWaypoints.index(startWpt), flatWaypoints.index(endWpt) + 1):
            timeDelta = flatWaypoints[x].Timestamp - lastTimestamp if lastTimestamp else None
            lastTimestamp = flatWaypoints[x].Timestamp

            if flatWaypoints[x].Type == WaypointType.Pause or (timeDelta and timeDelta > ActivityStatisticCalculator.ImplicitPauseTime):
                lastLoc = None  # don't count distance while paused
                continue

            loc = flatWaypoints[x].Location
            if loc is None or loc.Longitude is None or loc.Latitude is None:
                # Used to throw an exception in this case, but the TCX schema allows for location-free waypoints, so we'll just patch over it.
                continue

            if loc and lastLoc:
                altHold = lastLoc.Altitude if lastLoc.Altitude is not None else altHold
                latRads = loc.Latitude * math.pi / 180
                meters_lat_degree = 1000 * 111.13292 + 1.175 * math.cos(4 * latRads) - 559.82 * math.cos(2 * latRads)
                meters_lon_degree = 1000 * 111.41284 * math.cos(latRads) - 93.5 * math.cos(3 * latRads)
                dx = (loc.Longitude - lastLoc.Longitude) * meters_lon_degree
                dy = (loc.Latitude - lastLoc.Latitude) * meters_lat_degree
                if loc.Altitude is not None and altHold is not None:  # incorporate the altitude when possible
                    dz = loc.Altitude - altHold
                else:
                    dz = 0
                dist += math.sqrt(dx ** 2 + dy ** 2 + dz ** 2)
            lastLoc = loc

        return dist

    def CalculateTimerTime(act, startWpt=None, endWpt=None):
        flatWaypoints = []
        for lap in act.Laps:
            flatWaypoints.append(lap.Waypoints)

        if len(flatWaypoints) < 3:
            # Either no waypoints, or one at the start and one at the end
            raise ValueError("Not enough waypoints to calculate timer time")
        duration = timedelta(0)
        if not startWpt:
            startWpt = flatWaypoints[0]
        if not endWpt:
            endWpt = flatWaypoints[-1]
        lastTimestamp = None
        for x in range(flatWaypoints.index(startWpt), flatWaypoints.index(endWpt) + 1):
            wpt = flatWaypoints[x]
            delta = wpt.Timestamp - lastTimestamp if lastTimestamp else None
            lastTimestamp = wpt.Timestamp
            if wpt.Type is WaypointType.Pause:
                lastTimestamp = None
            elif delta and delta > act.ImplicitPauseTime:
                delta = None  # Implicit pauses
            if delta:
                duration += delta
        if duration.total_seconds() == 0 and startWpt is None and endWpt is None:
            raise ValueError("Zero-duration activity")
        return duration

    def CalculateAverageMaxHR(act, startWpt=None, endWpt=None):
        flatWaypoints = act.GetFlatWaypoints()

        # Python can handle 600+ digit numbers, think it can handle this
        maxHR = 0
        cumulHR = 0
        samples = 0

        if not startWpt:
            startWpt = flatWaypoints[0]
        if not endWpt:
            endWpt = flatWaypoints[-1]

        for x in range(flatWaypoints.index(startWpt), flatWaypoints.index(endWpt) + 1):
            wpt = flatWaypoints[x]
            if wpt.HR:
                if wpt.HR > maxHR:
                    maxHR = wpt.HR
                cumulHR += wpt.HR
                samples += 1

        if not samples:
            return None, None

        cumulHR = cumulHR / samples
        return cumulHR, maxHR



########NEW FILE########
__FILENAME__ = strava
from tapiriik.settings import WEB_ROOT, STRAVA_CLIENT_SECRET, STRAVA_CLIENT_ID
from tapiriik.services.service_base import ServiceAuthenticationType, ServiceBase
from tapiriik.services.service_record import ServiceRecord
from tapiriik.database import cachedb
from tapiriik.services.interchange import UploadedActivity, ActivityType, ActivityStatistic, ActivityStatisticUnit, Waypoint, WaypointType, Location, Lap
from tapiriik.services.api import APIException, UserException, UserExceptionType, APIExcludeActivity
from tapiriik.services.fit import FITIO

from django.core.urlresolvers import reverse
from datetime import datetime, timedelta
from urllib.parse import urlencode
import calendar
import requests
import os
import logging
import pytz
import re
import time

logger = logging.getLogger(__name__)

class StravaService(ServiceBase):
    ID = "strava"
    DisplayName = "Strava"
    DisplayAbbreviation = "STV"
    AuthenticationType = ServiceAuthenticationType.OAuth
    UserProfileURL = "http://www.strava.com/athletes/{0}"
    UserActivityURL = "http://app.strava.com/activities/{1}"
    AuthenticationNoFrame = True  # They don't prevent the iframe, it just looks really ugly.
    LastUpload = None

    SupportsHR = SupportsCadence = SupportsTemp = SupportsPower = True

    # For mapping common->Strava; no ambiguity in Strava activity type
    _activityTypeMappings = {
        ActivityType.Cycling: "Ride",
        ActivityType.MountainBiking: "Ride",
        ActivityType.Hiking: "Hike",
        ActivityType.Running: "Run",
        ActivityType.Walking: "Walk",
        ActivityType.Snowboarding: "Snowboard",
        ActivityType.Skating: "IceSkate",
        ActivityType.CrossCountrySkiing: "NordicSki",
        ActivityType.DownhillSkiing: "AlpineSki",
        ActivityType.Swimming: "Swim",
        ActivityType.Gym: "Workout"
    }

    # For mapping Strava->common
    _reverseActivityTypeMappings = {
        "Ride": ActivityType.Cycling,
        "MountainBiking": ActivityType.MountainBiking,
        "Run": ActivityType.Running,
        "Hike": ActivityType.Hiking,
        "Walk": ActivityType.Walking,
        "AlpineSki": ActivityType.DownhillSkiing,
        "NordicSki": ActivityType.CrossCountrySkiing,
        "BackcountrySki": ActivityType.DownhillSkiing,
        "Swim": ActivityType.Swimming,
        "IceSkate": ActivityType.Skating,
        "Workout": ActivityType.Gym
    }

    SupportedActivities = list(_activityTypeMappings.keys())

    def WebInit(self):
        params = {'scope':'write view_private',
                  'client_id':STRAVA_CLIENT_ID,
                  'response_type':'code',
                  'redirect_uri':WEB_ROOT + reverse("oauth_return", kwargs={"service": "strava"})}
        self.UserAuthorizationURL = \
           "https://www.strava.com/oauth/authorize?" + urlencode(params)

    def _logAPICall(self, endpoint, opkey, error):
        cachedb.strava_apicall_stats.insert({"Endpoint": endpoint, "Opkey": opkey, "Error": error, "Timestamp": datetime.utcnow()})

    def _apiHeaders(self, serviceRecord):
        return {"Authorization": "access_token " + serviceRecord.Authorization["OAuthToken"]}

    def RetrieveAuthorizationToken(self, req, level):
        code = req.GET.get("code")
        params = {"grant_type": "authorization_code", "code": code, "client_id": STRAVA_CLIENT_ID, "client_secret": STRAVA_CLIENT_SECRET, "redirect_uri": WEB_ROOT + reverse("oauth_return", kwargs={"service": "strava"})}

        response = requests.post("https://www.strava.com/oauth/token", data=params)
        self._logAPICall("auth-token", None, response.status_code != 200)
        if response.status_code != 200:
            raise APIException("Invalid code")
        data = response.json()

        authorizationData = {"OAuthToken": data["access_token"]}
        # Retrieve the user ID, meh.
        id_resp = requests.get("https://www.strava.com/api/v3/athlete", headers=self._apiHeaders(ServiceRecord({"Authorization": authorizationData})))
        self._logAPICall("auth-extid", None, None)
        return (id_resp.json()["id"], authorizationData)

    def RevokeAuthorization(self, serviceRecord):
        #  you can't revoke the tokens strava distributes :\
        pass

    def DownloadActivityList(self, svcRecord, exhaustive=False):
        activities = []
        exclusions = []
        before = earliestDate = None

        while True:
            if before is not None and before < 0:
                break # Caused by activities that "happened" before the epoch. We generally don't care about those activities...
            logger.debug("Req with before=" + str(before) + "/" + str(earliestDate))
            resp = requests.get("https://www.strava.com/api/v3/athletes/" + str(svcRecord.ExternalID) + "/activities", headers=self._apiHeaders(svcRecord), params={"before": before})
            self._logAPICall("list", (svcRecord.ExternalID, str(earliestDate)), resp.status_code == 401)
            if resp.status_code == 401:
                raise APIException("No authorization to retrieve activity list", block=True, user_exception=UserException(UserExceptionType.Authorization, intervention_required=True))

            earliestDate = None

            reqdata = resp.json()

            if not len(reqdata):
                break  # No more activities to see

            for ride in reqdata:
                activity = UploadedActivity()
                activity.TZ = pytz.timezone(re.sub("^\([^\)]+\)\s*", "", ride["timezone"]))  # Comes back as "(GMT -13:37) The Stuff/We Want""
                activity.StartTime = pytz.utc.localize(datetime.strptime(ride["start_date"], "%Y-%m-%dT%H:%M:%SZ"))
                logger.debug("\tActivity s/t %s: %s" % (activity.StartTime, ride["name"]))
                if not earliestDate or activity.StartTime < earliestDate:
                    earliestDate = activity.StartTime
                    before = calendar.timegm(activity.StartTime.astimezone(pytz.utc).timetuple())

                manual = False  # Determines if we bother to "download" the activity afterwards
                if ride["start_latlng"] is None or ride["end_latlng"] is None:
                    manual = True

                activity.EndTime = activity.StartTime + timedelta(0, ride["elapsed_time"])
                activity.ServiceData = {"ActivityID": ride["id"], "Manual": manual}

                if ride["type"] not in self._reverseActivityTypeMappings:
                    exclusions.append(APIExcludeActivity("Unsupported activity type %s" % ride["type"], activityId=ride["id"], userException=UserException(UserExceptionType.Other)))
                    logger.debug("\t\tUnknown activity")
                    continue

                activity.Type = self._reverseActivityTypeMappings[ride["type"]]
                activity.Stats.Distance = ActivityStatistic(ActivityStatisticUnit.Meters, value=ride["distance"])
                if "max_speed" in ride or "average_speed" in ride:
                    activity.Stats.Speed = ActivityStatistic(ActivityStatisticUnit.MetersPerSecond, avg=ride["average_speed"] if "average_speed" in ride else None, max=ride["max_speed"] if "max_speed" in ride else None)
                activity.Stats.MovingTime = ActivityStatistic(ActivityStatisticUnit.Seconds, value=ride["moving_time"] if "moving_time" in ride and ride["moving_time"] > 0 else None)  # They don't let you manually enter this, and I think it returns 0 for those activities.
                # Strava doesn't handle "timer time" to the best of my knowledge - although they say they do look at the FIT total_timer_time field, so...?
                if "average_watts" in ride:
                    activity.Stats.Power = ActivityStatistic(ActivityStatisticUnit.Watts, avg=ride["average_watts"])
                if "average_heartrate" in ride:
                    activity.Stats.HR.update(ActivityStatistic(ActivityStatisticUnit.BeatsPerMinute, avg=ride["average_heartrate"]))
                if "max_heartrate" in ride:
                    activity.Stats.HR.update(ActivityStatistic(ActivityStatisticUnit.BeatsPerMinute, max=ride["max_heartrate"]))
                if "average_cadence" in ride:
                    activity.Stats.Cadence.update(ActivityStatistic(ActivityStatisticUnit.RevolutionsPerMinute, avg=ride["average_cadence"]))
                if "average_temp" in ride:
                    activity.Stats.Temperature.update(ActivityStatistic(ActivityStatisticUnit.DegreesCelcius, avg=ride["average_temp"]))
                if "calories" in ride:
                    activity.Stats.Energy = ActivityStatistic(ActivityStatisticUnit.Kilocalories, value=ride["calories"])
                activity.Name = ride["name"]
                activity.Private = ride["private"]
                activity.Stationary = manual
                activity.GPS = "start_latlng" in ride and ride["start_latlng"]
                activity.AdjustTZ()
                activity.CalculateUID()
                activities.append(activity)

            if not exhaustive or not earliestDate:
                break

        return activities, exclusions

    def DownloadActivity(self, svcRecord, activity):
        if activity.ServiceData["Manual"]:  # I should really add a param to DownloadActivity for this value as opposed to constantly doing this
            # We've got as much information as we're going to get - we need to copy it into a Lap though.
            activity.Laps = [Lap(startTime=activity.StartTime, endTime=activity.EndTime, stats=activity.Stats)]
            return activity
        activityID = activity.ServiceData["ActivityID"]

        streamdata = requests.get("https://www.strava.com/api/v3/activities/" + str(activityID) + "/streams/time,altitude,heartrate,cadence,watts,temp,moving,latlng", headers=self._apiHeaders(svcRecord))
        if streamdata.status_code == 401:
            self._logAPICall("download", (svcRecord.ExternalID, str(activity.StartTime)), "auth")
            raise APIException("No authorization to download activity", block=True, user_exception=UserException(UserExceptionType.Authorization, intervention_required=True))

        try:
            streamdata = streamdata.json()
        except:
            raise APIException("Stream data returned is not JSON")

        if "message" in streamdata and streamdata["message"] == "Record Not Found":
            self._logAPICall("download", (svcRecord.ExternalID, str(activity.StartTime)), "missing")
            raise APIException("Could not find activity")

        ridedata = {}
        for stream in streamdata:
            ridedata[stream["type"]] = stream["data"]

        lap = Lap(stats=activity.Stats, startTime=activity.StartTime, endTime=activity.EndTime) # Strava doesn't support laps, but we need somewhere to put the waypoints.
        activity.Laps = [lap]
        lap.Waypoints = []

        hasHR = "heartrate" in ridedata and len(ridedata["heartrate"]) > 0
        hasCadence = "cadence" in ridedata and len(ridedata["cadence"]) > 0
        hasTemp = "temp" in ridedata and len(ridedata["temp"]) > 0
        hasPower = ("watts" in ridedata and len(ridedata["watts"]) > 0)
        hasAltitude = "altitude" in ridedata and len(ridedata["altitude"]) > 0
        hasMovingData = "moving" in ridedata and len(ridedata["moving"]) > 0
        moving = True

        if "error" in ridedata:
            self._logAPICall("download", (svcRecord.ExternalID, str(activity.StartTime)), "data")
            raise APIException("Strava error " + ridedata["error"])

        hasLocation = False
        waypointCt = len(ridedata["time"])
        for idx in range(0, waypointCt - 1):
            latlng = ridedata["latlng"][idx]

            waypoint = Waypoint(activity.StartTime + timedelta(0, ridedata["time"][idx]))
            latlng = ridedata["latlng"][idx]
            waypoint.Location = Location(latlng[0], latlng[1], None)
            if waypoint.Location.Longitude == 0 and waypoint.Location.Latitude == 0:
                waypoint.Location.Longitude = None
                waypoint.Location.Latitude = None
            else:  # strava only returns 0 as invalid coords, so no need to check for null (update: ??)
                hasLocation = True
            if hasAltitude:
                waypoint.Location.Altitude = float(ridedata["altitude"][idx])

            if idx == 0:
                waypoint.Type = WaypointType.Start
            elif idx == waypointCt - 2:
                waypoint.Type = WaypointType.End
            elif hasMovingData and not moving and ridedata["moving"][idx] is True:
                waypoint.Type = WaypointType.Resume
                moving = True
            elif hasMovingData and ridedata["moving"][idx] is False:
                waypoint.Type = WaypointType.Pause
                moving = False

            if hasHR:
                waypoint.HR = ridedata["heartrate"][idx]
            if hasCadence:
                waypoint.Cadence = ridedata["cadence"][idx]
            if hasTemp:
                waypoint.Temp = ridedata["temp"][idx]
            if hasPower:
                waypoint.Power = ridedata["watts"][idx]
            lap.Waypoints.append(waypoint)
        if not hasLocation:
            self._logAPICall("download", (svcRecord.ExternalID, str(activity.StartTime)), "faulty")
            raise APIExcludeActivity("No waypoints with location", activityId=activityID, userException=UserException(UserExceptionType.Corrupt))
        self._logAPICall("download", (svcRecord.ExternalID, str(activity.StartTime)), None)
        return activity

    def UploadActivity(self, serviceRecord, activity):
        logger.info("Activity tz " + str(activity.TZ) + " dt tz " + str(activity.StartTime.tzinfo) + " starttime " + str(activity.StartTime))

        if self.LastUpload is not None:
            while (datetime.now() - self.LastUpload).total_seconds() < 5:
                time.sleep(1)
                logger.debug("Inter-upload cooldown")
        source_svc = None
        if hasattr(activity, "ServiceDataCollection"):
            source_svc = str(list(activity.ServiceDataCollection.keys())[0])

        upload_id = None
        if activity.CountTotalWaypoints():
            req = {
                    "data_type": "fit",
                    "activity_name": activity.Name,
                    "description": activity.Notes, # Paul Mach said so.
                    "activity_type": self._activityTypeMappings[activity.Type],
                    "private": 1 if activity.Private else 0}

            if "fit" in activity.PrerenderedFormats:
                logger.debug("Using prerendered FIT")
                fitData = activity.PrerenderedFormats["fit"]
            else:
                # TODO: put the fit back into PrerenderedFormats once there's more RAM to go around and there's a possibility of it actually being used.
                fitData = FITIO.Dump(activity)
            files = {"file":("tap-sync-" + activity.UID + "-" + str(os.getpid()) + ("-" + source_svc if source_svc else "") + ".fit", fitData)}

            response = requests.post("http://www.strava.com/api/v3/uploads", data=req, files=files, headers=self._apiHeaders(serviceRecord))
            if response.status_code != 201:
                if response.status_code == 401:
                    raise APIException("No authorization to upload activity " + activity.UID + " response " + response.text + " status " + str(response.status_code), block=True, user_exception=UserException(UserExceptionType.Authorization, intervention_required=True))
                if "duplicate of activity" in response.text:
                    logger.debug("Duplicate")
                    self.LastUpload = datetime.now()
                    return # Fine by me. The majority of these cases were caused by a dumb optimization that meant existing activities on services were never flagged as such if tapiriik didn't have to synchronize them elsewhere.
                raise APIException("Unable to upload activity " + activity.UID + " response " + response.text + " status " + str(response.status_code))

            upload_id = response.json()["id"]
            while not response.json()["activity_id"]:
                time.sleep(5)
                response = requests.get("http://www.strava.com/api/v3/uploads/%s" % upload_id, headers=self._apiHeaders(serviceRecord))
                logger.debug("Waiting for upload - status %s id %s" % (response.json()["status"], response.json()["activity_id"]))
                if response.json()["error"]:
                    error = response.json()["error"]
                    if "duplicate of activity" in error:
                        self.LastUpload = datetime.now()
                        logger.debug("Duplicate")
                        return # I guess we're done here?
                    raise APIException("Strava failed while processing activity - last status %s" % response.text)
            upload_id = response.json()["activity_id"]
        else:
            localUploadTS = activity.StartTime.strftime("%Y-%m-%d %H:%M:%S")
            req = {
                    "name": activity.Name if activity.Name else activity.StartTime.strftime("%d/%m/%Y"), # This is required
                    "description": activity.Notes,
                    "type": self._activityTypeMappings[activity.Type],
                    "private": 1 if activity.Private else 0,
                    "start_date_local": localUploadTS,
                    "distance": activity.Stats.Distance.asUnits(ActivityStatisticUnit.Meters).Value,
                    "elapsed_time": round((activity.EndTime - activity.StartTime).total_seconds())
                }
            headers = self._apiHeaders(serviceRecord)
            response = requests.post("https://www.strava.com/api/v3/activities", data=req, headers=headers)
            # FFR this method returns the same dict as the activity listing, as REST services are wont to do.
            if response.status_code != 201:
                if response.status_code == 401:
                    raise APIException("No authorization to upload activity " + activity.UID + " response " + response.text + " status " + str(response.status_code), block=True, user_exception=UserException(UserExceptionType.Authorization, intervention_required=True))
                raise APIException("Unable to upload stationary activity " + activity.UID + " response " + response.text + " status " + str(response.status_code))
            upload_id = response.json()["id"]

        self.LastUpload = datetime.now()
        return upload_id

    def DeleteCachedData(self, serviceRecord):
        cachedb.strava_cache.remove({"Owner": serviceRecord.ExternalID})
        cachedb.strava_activity_cache.remove({"Owner": serviceRecord.ExternalID})

########NEW FILE########
__FILENAME__ = stream_sampling
class StreamSampler:
    def SampleWithCallback(callback, streams):
        """
            *streams should be a dict in format {"stream1":[(ts1,val1), (ts2, val2)...]...} where ts is a numerical offset from the activity start.
            Expect callback(time_offset, stream1=value1, stream2=value2) in chronological order. Stream values may be None
        """

        # Collate the individual streams into discrete waypoints.
        # There is no global sampling rate - waypoints are created for every new datapoint in any stream (simultaneous datapoints are included in the same waypoint)
        # Resampling is based on the last known value of the stream - no interpolation or nearest-neighbour.

        streamData = streams
        streams = list(streams.keys())
        print("Handling streams %s" % streams)

        stream_indices = dict([(stream, -1) for stream in streams]) # -1 meaning the stream has yet to start
        stream_lengths = dict([(stream, len(streamData[stream])) for stream in streams])

        currentTimeOffset = 0

        while True:
            advance_stream = None
            advance_offset = None
            for stream in streams:
                if stream_indices[stream] + 1 == stream_lengths[stream]:
                    continue # We're at the end - can't advance
                if advance_offset is None or streamData[stream][stream_indices[stream] + 1][0] - currentTimeOffset < advance_offset:
                    advance_offset = streamData[stream][stream_indices[stream] + 1][0] - currentTimeOffset
                    advance_stream = stream
            if not advance_stream:
                break # We've hit the end of every stream, stop
            # Update the current time offset based on the key advancing stream (others may still be behind)
            currentTimeOffset = streamData[advance_stream][stream_indices[advance_stream] + 1][0]
            # Advance streams with the current timestamp, including advance_stream
            for stream in streams:
                if stream_indices[stream] + 1 == stream_lengths[stream]:
                    continue # We're at the end - can't advance
                if streamData[stream][stream_indices[stream] + 1][0] == currentTimeOffset: # Don't need to consider <, as then that stream would be advance_stream
                    stream_indices[stream] += 1
            callbackDataArgs = {}
            for stream in streams:
                if stream_indices[stream] >= 0:
                    callbackDataArgs[stream] = streamData[stream][stream_indices[stream]][1]
            callback(currentTimeOffset, **callbackDataArgs)

########NEW FILE########
__FILENAME__ = tcx
from lxml import etree
from pytz import UTC
import copy
import dateutil.parser
from datetime import timedelta
from .interchange import WaypointType, Activity, ActivityStatistic, ActivityStatistics, ActivityStatisticUnit, ActivityType, Waypoint, Location, Lap, LapIntensity, LapTriggerMethod
from .devices import DeviceIdentifier, DeviceIdentifierType, Device


class TCXIO:
    Namespaces = {
        None: "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2",
        "ns2": "http://www.garmin.com/xmlschemas/UserProfile/v2",
        "tpx": "http://www.garmin.com/xmlschemas/ActivityExtension/v2",
        "ns4": "http://www.garmin.com/xmlschemas/ProfileExtension/v1",
        "ns5": "http://www.garmin.com/xmlschemas/ActivityGoals/v1",
        "xsi": "http://www.w3.org/2001/XMLSchema-instance"
    }

    def Parse(tcxData, act=None):
        ns = copy.deepcopy(TCXIO.Namespaces)
        ns["tcx"] = ns[None]
        del ns[None]

        act = act if act else Activity()

        act.GPS = False

        try:
            root = etree.XML(tcxData)
        except:
            root = etree.fromstring(tcxData)


        xacts = root.find("tcx:Activities", namespaces=ns)
        if xacts is None:
            raise ValueError("No activities element in TCX")

        xact = xacts.find("tcx:Activity", namespaces=ns)
        if xact is None:
            raise ValueError("No activity element in TCX")

        xauthor = root.find("tcx:Author", namespaces=ns)
        if xauthor is not None:
            xauthorname = xauthor.find("tcx:Name", namespaces=ns)
            if xauthorname is not None:
                if xauthorname.text == "tapiriik":
                    act.OriginatedFromTapiriik = True

        if not act.Type or act.Type == ActivityType.Other:
            if xact.attrib["Sport"] == "Biking":
                act.Type = ActivityType.Cycling
            elif xact.attrib["Sport"] == "Running":
                act.Type = ActivityType.Running

        xcreator = xact.find("tcx:Creator", namespaces=ns)
        if xcreator is not None and xcreator.attrib["{" + TCXIO.Namespaces["xsi"] + "}type"] == "Device_t":
            devId = DeviceIdentifier.FindMatchingIdentifierOfType(DeviceIdentifierType.TCX, {"ProductID": int(xcreator.find("tcx:ProductID", namespaces=ns).text)}) # Who knows if this is unique in the TCX ecosystem? We'll find out!
            xver = xcreator.find("tcx:Version", namespaces=ns)
            act.Device = Device(devId, int(xcreator.find("tcx:UnitId", namespaces=ns).text), verMaj=int(xver.find("tcx:VersionMajor", namespaces=ns).text), verMin=int(xver.find("tcx:VersionMinor", namespaces=ns).text)) # ID vs Id: ???

        xlaps = xact.findall("tcx:Lap", namespaces=ns)
        startTime = None
        endTime = None
        for xlap in xlaps:

            lap = Lap()
            act.Laps.append(lap)

            lap.StartTime = dateutil.parser.parse(xlap.attrib["StartTime"])
            totalTimeEL = xlap.find("tcx:TotalTimeSeconds", namespaces=ns)
            if totalTimeEL is None:
                raise ValueError("Missing lap TotalTimeSeconds")
            lap.Stats.TimerTime = ActivityStatistic(ActivityStatisticUnit.Seconds, float(totalTimeEL.text))

            lap.EndTime = lap.StartTime + timedelta(seconds=float(totalTimeEL.text))

            distEl = xlap.find("tcx:DistanceMeters", namespaces=ns)
            energyEl = xlap.find("tcx:Calories", namespaces=ns)
            triggerEl = xlap.find("tcx:TriggerMethod", namespaces=ns)
            intensityEl = xlap.find("tcx:Intensity", namespaces=ns)

            # Some applications slack off and omit these, despite the fact that they're required in the spec.
            # I will, however, require lap distance, because, seriously.
            if distEl is None:
                raise ValueError("Missing lap DistanceMeters")

            lap.Stats.Distance = ActivityStatistic(ActivityStatisticUnit.Meters, float(distEl.text))
            if energyEl is not None and energyEl.text:
                lap.Stats.Energy = ActivityStatistic(ActivityStatisticUnit.Kilocalories, float(energyEl.text))
                if lap.Stats.Energy.Value == 0:
                    lap.Stats.Energy.Value = None # It's dumb to make this required, but I digress.

            if intensityEl is not None:
                lap.Intensity = LapIntensity.Active if intensityEl.text == "Active" else LapIntensity.Rest
            else:
                lap.Intensity = LapIntensity.Active

            if triggerEl is not None:
                lap.Trigger = ({
                    "Manual": LapTriggerMethod.Manual,
                    "Distance": LapTriggerMethod.Distance,
                    "Location": LapTriggerMethod.PositionMarked,
                    "Time": LapTriggerMethod.Time,
                    "HeartRate": LapTriggerMethod.Manual # I guess - no equivalent in FIT
                    })[triggerEl.text]
            else:
                lap.Trigger = LapTriggerMethod.Manual # One would presume

            maxSpdEl = xlap.find("tcx:MaximumSpeed", namespaces=ns)
            if maxSpdEl is not None:
                lap.Stats.Speed = ActivityStatistic(ActivityStatisticUnit.MetersPerSecond, max=float(maxSpdEl.text))

            avgHREl = xlap.find("tcx:AverageHeartRateBpm", namespaces=ns)
            if avgHREl is not None:
                lap.Stats.HR = ActivityStatistic(ActivityStatisticUnit.BeatsPerMinute, avg=float(avgHREl.find("tcx:Value", namespaces=ns).text))

            maxHREl = xlap.find("tcx:MaximumHeartRateBpm", namespaces=ns)
            if maxHREl is not None:
                lap.Stats.HR.update(ActivityStatistic(ActivityStatisticUnit.BeatsPerMinute, max=float(maxHREl.find("tcx:Value", namespaces=ns).text)))

            # WF fills these in with invalid values.
            lap.Stats.HR.Max = lap.Stats.HR.Max if lap.Stats.HR.Max and lap.Stats.HR.Max > 10 else None
            lap.Stats.HR.Average = lap.Stats.HR.Average if lap.Stats.HR.Average and lap.Stats.HR.Average > 10 else None

            cadEl = xlap.find("tcx:Cadence", namespaces=ns)
            if cadEl is not None:
                lap.Stats.Cadence = ActivityStatistic(ActivityStatisticUnit.RevolutionsPerMinute, avg=float(cadEl.text))

            extsEl = xlap.find("tcx:Extensions", namespaces=ns)
            if extsEl is not None:
                lxEls = extsEl.findall("tpx:LX", namespaces=ns)
                for lxEl in lxEls:
                    avgSpeedEl = lxEl.find("tpx:AvgSpeed", namespaces=ns)
                    if avgSpeedEl is not None:
                        lap.Stats.Speed.update(ActivityStatistic(ActivityStatisticUnit.MetersPerSecond, avg=float(avgSpeedEl.text)))
                    maxBikeCadEl = lxEl.find("tpx:MaxBikeCadence", namespaces=ns)
                    if maxBikeCadEl is not None:
                        lap.Stats.Cadence.update(ActivityStatistic(ActivityStatisticUnit.RevolutionsPerMinute, max=float(maxBikeCadEl.text)))
                    maxPowerEl = lxEl.find("tpx:MaxWatts", namespaces=ns)
                    if maxPowerEl is not None:
                        lap.Stats.Power.update(ActivityStatistic(ActivityStatisticUnit.Watts, max=float(maxPowerEl.text)))
                    avgPowerEl = lxEl.find("tpx:AvgWatts", namespaces=ns)
                    if avgPowerEl is not None:
                        lap.Stats.Power.update(ActivityStatistic(ActivityStatisticUnit.Watts, avg=float(avgPowerEl.text)))
                    maxRunCadEl = lxEl.find("tpx:MaxRunCadence", namespaces=ns)
                    if maxRunCadEl is not None:
                        lap.Stats.RunCadence.update(ActivityStatistic(ActivityStatisticUnit.StepsPerMinute, max=float(maxRunCadEl.text)))
                    avgRunCadEl = lxEl.find("tpx:AvgRunCadence", namespaces=ns)
                    if avgRunCadEl is not None:
                        lap.Stats.RunCadence.update(ActivityStatistic(ActivityStatisticUnit.StepsPerMinute, avg=float(avgRunCadEl.text)))
                    stepsEl = lxEl.find("tpx:Steps", namespaces=ns)
                    if stepsEl is not None:
                        lap.Stats.Strides.update(ActivityStatistic(ActivityStatisticUnit.Strides, value=float(stepsEl.text)))

            xtrkseg = xlap.find("tcx:Track", namespaces=ns)
            if xtrkseg is None:
                # Some TCX files have laps with no track - not sure if it's valid or not.
                continue
            for xtrkpt in xtrkseg.findall("tcx:Trackpoint", namespaces=ns):
                wp = Waypoint()
                tsEl = xtrkpt.find("tcx:Time", namespaces=ns)
                if tsEl is None:
                    raise ValueError("Trackpoint without timestamp")
                wp.Timestamp = dateutil.parser.parse(tsEl.text)
                wp.Timestamp.replace(tzinfo=UTC)
                if startTime is None or wp.Timestamp < startTime:
                    startTime = wp.Timestamp
                if endTime is None or wp.Timestamp > endTime:
                    endTime = wp.Timestamp
                xpos = xtrkpt.find("tcx:Position", namespaces=ns)
                if xpos is not None:
                    act.GPS = True
                    wp.Location = Location(float(xpos.find("tcx:LatitudeDegrees", namespaces=ns).text), float(xpos.find("tcx:LongitudeDegrees", namespaces=ns).text), None)
                eleEl = xtrkpt.find("tcx:AltitudeMeters", namespaces=ns)
                if eleEl is not None:
                    wp.Location = wp.Location if wp.Location else Location(None, None, None)
                    wp.Location.Altitude = float(eleEl.text)
                distEl = xtrkpt.find("tcx:DistanceMeters", namespaces=ns)
                if distEl is not None:
                    wp.Distance = float(distEl.text)

                hrEl = xtrkpt.find("tcx:HeartRateBpm", namespaces=ns)
                if hrEl is not None:
                    wp.HR = float(hrEl.find("tcx:Value", namespaces=ns).text)
                cadEl = xtrkpt.find("tcx:Cadence", namespaces=ns)
                if cadEl is not None:
                    wp.Cadence = float(cadEl.text)
                extsEl = xtrkpt.find("tcx:Extensions", namespaces=ns)
                if extsEl is not None:
                    tpxEl = extsEl.find("tpx:TPX", namespaces=ns)
                    if tpxEl is not None:
                        powerEl = tpxEl.find("tpx:Watts", namespaces=ns)
                        if powerEl is not None:
                            wp.Power = float(powerEl.text)
                        speedEl = tpxEl.find("tpx:Speed", namespaces=ns)
                        if speedEl is not None:
                            wp.Speed = float(speedEl.text)
                        runCadEl = tpxEl.find("tpx:RunCadence", namespaces=ns)
                        if runCadEl is not None:
                            wp.RunCadence = float(runCadEl.text)
                lap.Waypoints.append(wp)
                xtrkpt.clear()
                del xtrkpt
            if len(lap.Waypoints):
                lap.EndTime = lap.Waypoints[-1].Timestamp

        act.StartTime = act.Laps[0].StartTime if len(act.Laps) else act.StartTime
        act.EndTime = act.Laps[-1].EndTime if len(act.Laps) else act.EndTime

        if act.CountTotalWaypoints():
            act.Stationary = False
            act.GetFlatWaypoints()[0].Type = WaypointType.Start
            act.GetFlatWaypoints()[-1].Type = WaypointType.End
        else:
            act.Stationary = True
        if len(act.Laps) == 1:
            act.Laps[0].Stats.update(act.Stats) # External source is authorative
            act.Stats = act.Laps[0].Stats
        else:
            sum_stats = ActivityStatistics() # Blank
            for lap in act.Laps:
                sum_stats.sumWith(lap.Stats)
            sum_stats.update(act.Stats)
            act.Stats = sum_stats

        act.CalculateUID()
        return act

    def Dump(activity):

        root = etree.Element("TrainingCenterDatabase", nsmap=TCXIO.Namespaces)
        activities = etree.SubElement(root, "Activities")
        act = etree.SubElement(activities, "Activity")


        author = etree.SubElement(root, "Author")
        author.attrib["{" + TCXIO.Namespaces["xsi"] + "}type"] = "Application_t"
        etree.SubElement(author, "Name").text = "tapiriik"
        build = etree.SubElement(author, "Build")
        version = etree.SubElement(build, "Version")
        etree.SubElement(version, "VersionMajor").text = "0"
        etree.SubElement(version, "VersionMinor").text = "0"
        etree.SubElement(version, "BuildMajor").text = "0"
        etree.SubElement(version, "BuildMinor").text = "0"
        etree.SubElement(author, "LangID").text = "en"
        etree.SubElement(author, "PartNumber").text = "000-00000-00"

        dateFormat = "%Y-%m-%dT%H:%M:%S.000Z"

        if activity.Name is not None:
            etree.SubElement(act, "Notes").text = activity.Name

        if activity.Type == ActivityType.Cycling:
            act.attrib["Sport"] = "Biking"
        elif activity.Type == ActivityType.Running:
            act.attrib["Sport"] = "Running"
        else:
            act.attrib["Sport"] = "Other"

        etree.SubElement(act, "Id").text = activity.StartTime.astimezone(UTC).strftime(dateFormat)

        def _writeStat(parent, elName, value, wrapValue=False, naturalValue=False, default=None):
                if value is not None or default is not None:
                    xstat = etree.SubElement(parent, elName)
                    if wrapValue:
                        xstat = etree.SubElement(xstat, "Value")
                    value = value if value is not None else default
                    xstat.text = str(value) if not naturalValue else str(int(value))

        xlaps = []
        for lap in activity.Laps:
            xlap = etree.SubElement(act, "Lap")
            xlaps.append(xlap)

            xlap.attrib["StartTime"] = lap.StartTime.astimezone(UTC).strftime(dateFormat)

            _writeStat(xlap, "TotalTimeSeconds", lap.Stats.TimerTime.asUnits(ActivityStatisticUnit.Seconds).Value if lap.Stats.TimerTime.Value else None, default=(lap.EndTime - lap.StartTime).total_seconds())
            _writeStat(xlap, "DistanceMeters", lap.Stats.Distance.asUnits(ActivityStatisticUnit.Meters).Value)
            _writeStat(xlap, "MaximumSpeed", lap.Stats.Speed.asUnits(ActivityStatisticUnit.MetersPerSecond).Max)
            _writeStat(xlap, "Calories", lap.Stats.Energy.asUnits(ActivityStatisticUnit.Kilocalories).Value, default=0, naturalValue=True)
            _writeStat(xlap, "AverageHeartRateBpm", lap.Stats.HR.Average, naturalValue=True, wrapValue=True)
            _writeStat(xlap, "MaximumHeartRateBpm", lap.Stats.HR.Max, naturalValue=True, wrapValue=True)

            etree.SubElement(xlap, "Intensity").text = "Resting" if lap.Intensity == LapIntensity.Rest else "Active"

            _writeStat(xlap, "Cadence", lap.Stats.Cadence.Average, naturalValue=True)

            etree.SubElement(xlap, "TriggerMethod").text = ({
                LapTriggerMethod.Manual: "Manual",
                LapTriggerMethod.Distance: "Distance",
                LapTriggerMethod.PositionMarked: "Location",
                LapTriggerMethod.Time: "Time",
                LapTriggerMethod.PositionStart: "Location",
                LapTriggerMethod.PositionLap: "Location",
                LapTriggerMethod.PositionMarked: "Location",
                LapTriggerMethod.SessionEnd: "Manual",
                LapTriggerMethod.FitnessEquipment: "Manual"
                })[lap.Trigger]

            if len([x for x in [lap.Stats.Cadence.Max, lap.Stats.RunCadence.Max, lap.Stats.RunCadence.Average, lap.Stats.Strides.Value, lap.Stats.Power.Max, lap.Stats.Power.Average, lap.Stats.Speed.Average] if x is not None]):
                exts = etree.SubElement(xlap, "Extensions")
                lapext = etree.SubElement(exts, "LX")
                lapext.attrib["xmlns"] = "http://www.garmin.com/xmlschemas/ActivityExtension/v2"
                _writeStat(lapext, "MaxBikeCadence", lap.Stats.Cadence.Max, naturalValue=True)
                # This dividing-by-two stuff is getting silly
                _writeStat(lapext, "MaxRunCadence", lap.Stats.RunCadence.Max if lap.Stats.RunCadence.Max is not None else None, naturalValue=True)
                _writeStat(lapext, "AvgRunCadence", lap.Stats.RunCadence.Average if lap.Stats.RunCadence.Average is not None else None, naturalValue=True)
                _writeStat(lapext, "Steps", lap.Stats.Strides.Value, naturalValue=True)
                _writeStat(lapext, "MaxWatts", lap.Stats.Power.asUnits(ActivityStatisticUnit.Watts).Max, naturalValue=True)
                _writeStat(lapext, "AvgWatts", lap.Stats.Power.asUnits(ActivityStatisticUnit.Watts).Average, naturalValue=True)
                _writeStat(lapext, "AvgSpeed", lap.Stats.Speed.asUnits(ActivityStatisticUnit.MetersPerSecond).Average)

        inPause = False
        for lap in activity.Laps:
            xlap = xlaps[activity.Laps.index(lap)]
            track = None
            for wp in lap.Waypoints:
                if wp.Type == WaypointType.Pause:
                    if inPause:
                        continue  # this used to be an exception, but I don't think that was merited
                    inPause = True
                if inPause and wp.Type != WaypointType.Pause:
                    inPause = False
                if track is None:  # Defer creating the track until there are points
                    track = etree.SubElement(xlap, "Track") # TODO - pauses should create new tracks instead of new laps?
                trkpt = etree.SubElement(track, "Trackpoint")
                if wp.Timestamp.tzinfo is None:
                    raise ValueError("TCX export requires TZ info")
                etree.SubElement(trkpt, "Time").text = wp.Timestamp.astimezone(UTC).strftime(dateFormat)
                if wp.Location:
                    if wp.Location.Latitude is not None and wp.Location.Longitude is not None:
                        pos = etree.SubElement(trkpt, "Position")
                        etree.SubElement(pos, "LatitudeDegrees").text = str(wp.Location.Latitude)
                        etree.SubElement(pos, "LongitudeDegrees").text = str(wp.Location.Longitude)

                    if wp.Location.Altitude is not None:
                        etree.SubElement(trkpt, "AltitudeMeters").text = str(wp.Location.Altitude)

                if wp.Distance is not None:
                    etree.SubElement(trkpt, "DistanceMeters").text = str(wp.Distance)
                if wp.HR is not None:
                    xhr = etree.SubElement(trkpt, "HeartRateBpm")
                    xhr.attrib["{" + TCXIO.Namespaces["xsi"] + "}type"] = "HeartRateInBeatsPerMinute_t"
                    etree.SubElement(xhr, "Value").text = str(int(wp.HR))
                if wp.Cadence is not None:
                    etree.SubElement(trkpt, "Cadence").text = str(int(wp.Cadence))
                if wp.Power is not None or wp.RunCadence is not None or wp.Speed is not None:
                    exts = etree.SubElement(trkpt, "Extensions")
                    gpxtpxexts = etree.SubElement(exts, "TPX")
                    gpxtpxexts.attrib["xmlns"] = "http://www.garmin.com/xmlschemas/ActivityExtension/v2"
                    if wp.Speed is not None:
                        etree.SubElement(gpxtpxexts, "Speed").text = str(wp.Speed)
                    if wp.RunCadence is not None:
                        etree.SubElement(gpxtpxexts, "RunCadence").text = str(int(wp.RunCadence))
                    if wp.Power is not None:
                        etree.SubElement(gpxtpxexts, "Watts").text = str(int(wp.Power))
            if track is not None:
                exts = xlap.find("Extensions")
                if exts is not None:
                    track.addnext(exts)

        if activity.Device and activity.Device.Identifier:
            devId = DeviceIdentifier.FindEquivalentIdentifierOfType(DeviceIdentifierType.TCX, activity.Device.Identifier)
            if devId:
                xcreator = etree.SubElement(act, "Creator")
                xcreator.attrib["{" + TCXIO.Namespaces["xsi"] + "}type"] = "Device_t"
                etree.SubElement(xcreator, "Name").text = devId.Name
                etree.SubElement(xcreator, "UnitId").text = str(activity.Device.Serial) if activity.Device.Serial else "0"
                etree.SubElement(xcreator, "ProductID").text = str(devId.ProductID)
                xver = etree.SubElement(xcreator, "Version")
                etree.SubElement(xver, "VersionMajor").text = str(activity.Device.VersionMajor) if activity.Device.VersionMajor else "0" # Blegh.
                etree.SubElement(xver, "VersionMinor").text = str(activity.Device.VersionMinor) if activity.Device.VersionMinor else "0"
                etree.SubElement(xver, "BuildMajor").text = "0"
                etree.SubElement(xver, "BuildMinor").text = "0"


        return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8").decode("UTF-8")

########NEW FILE########
__FILENAME__ = trainingpeaks
from tapiriik.settings import WEB_ROOT
from tapiriik.services.service_base import ServiceAuthenticationType, ServiceBase
from tapiriik.services.interchange import UploadedActivity, ActivityType, ActivityStatistic, ActivityStatisticUnit
from tapiriik.services.api import APIException, UserException, UserExceptionType, APIExcludeActivity
from tapiriik.services.pwx import PWXIO
from lxml import etree

from django.core.urlresolvers import reverse
from datetime import datetime, timedelta
import dateutil.parser
import requests
import logging
import re

logger = logging.getLogger(__name__)

class TrainingPeaksService(ServiceBase):
    ID = "trainingpeaks"
    DisplayName = "TrainingPeaks"
    DisplayAbbreviation = "TP"
    AuthenticationType = ServiceAuthenticationType.UsernamePassword
    RequiresExtendedAuthorizationDetails = True
    ReceivesStationaryActivities = False

    SupportsHR = SupportsCadence = SupportsTemp = SupportsPower = True

    # Not-so-coincidentally, similar to PWX.
    _workoutTypeMappings = {
        "Bike": ActivityType.Cycling,
        "Run": ActivityType.Running,
        "Walk": ActivityType.Walking,
        "Swim": ActivityType.Swimming,
        "MTB": ActivityType.MountainBiking,
        "XC-Ski": ActivityType.CrossCountrySkiing,
        "Rowing": ActivityType.Rowing,
        "X-Train": ActivityType.Other,
        "Strength": ActivityType.Other,
        "Race": ActivityType.Other,
        "Custom": ActivityType.Other,
        "Other": ActivityType.Other,
    }
    SupportedActivities = ActivityType.List() # All.

    def WebInit(self):
        self.UserAuthorizationURL = WEB_ROOT + reverse("auth_simple", kwargs={"service": self.ID})

    def _authData(self, serviceRecord):
        from tapiriik.auth.credential_storage import CredentialStore
        password = CredentialStore.Decrypt(serviceRecord.ExtendedAuthorization["Password"])
        username = CredentialStore.Decrypt(serviceRecord.ExtendedAuthorization["Username"])
        return {"username": username, "password": password}

    def Authorize(self, email, password):
        from tapiriik.auth.credential_storage import CredentialStore
        resp = requests.post("https://www.trainingpeaks.com/tpwebservices/service.asmx/AuthenticateAccount", data={"username":email, "password": password})
        if resp.status_code != 200:
            raise APIException("Invalid login")
        sess_guid = etree.XML(resp.content).text
        cookies = {"mySession_Production": sess_guid}
        resp = requests.get("https://www.trainingpeaks.com/m/Shared/PersonInfo.js", cookies=cookies)
        accountIsPremium = re.search("currentAthlete\.IsBasicUser\s*=\s*(true|false);", resp.text).group(1) == "false"
        personId = re.search("currentAthlete\.PersonId\s*=\s*(\d+);", resp.text).group(1)
        # Yes, I have it on good authority that this is checked further on on the remote end.
        if not accountIsPremium:
            raise APIException("Account not premium", block=True, user_exception=UserException(UserExceptionType.AccountUnpaid, intervention_required=True, extra=personId))
        return (personId, {}, {"Username": CredentialStore.Encrypt(email), "Password": CredentialStore.Encrypt(password)})

    def RevokeAuthorization(self, serviceRecord):
        pass  # No auth tokens to revoke...

    def DeleteCachedData(self, serviceRecord):
        pass  # No cached data...

    def DownloadActivityList(self, svcRecord, exhaustive=False):
        ns = {
            "tpw": "http://www.trainingpeaks.com/TPWebServices/",
            "xsi": "http://www.w3.org/2001/XMLSchema-instance"
            }
        activities = []
        exclusions = []

        reqData = self._authData(svcRecord)

        limitDateFormat = "%d %B %Y"

        if exhaustive:
            listEnd = datetime.now() + timedelta(days=1.5) # Who knows which TZ it's in
            listStart = datetime(day=1, month=1, year=1980) # The beginning of time
        else:
            listEnd = datetime.now() + timedelta(days=1.5) # Who knows which TZ it's in
            listStart = listEnd - timedelta(days=20) # Doesn't really matter

        lastActivityDay = None
        discoveredWorkoutIds = []
        while True:
            reqData.update({"startDate": listStart.strftime(limitDateFormat), "endDate": listEnd.strftime(limitDateFormat)})
            print("Requesting %s to %s" % (listStart, listEnd))
            resp = requests.post("https://www.trainingpeaks.com/tpwebservices/service.asmx/GetWorkoutsForAthlete", data=reqData)
            xresp = etree.XML(resp.content)
            for xworkout in xresp:
                activity = UploadedActivity()

                workoutId = xworkout.find("tpw:WorkoutId", namespaces=ns).text

                workoutDayEl = xworkout.find("tpw:WorkoutDay", namespaces=ns)
                startTimeEl = xworkout.find("tpw:StartTime", namespaces=ns)

                workoutDay = dateutil.parser.parse(workoutDayEl.text)
                startTime = dateutil.parser.parse(startTimeEl.text) if startTimeEl is not None and startTimeEl.text else None

                if lastActivityDay is None or workoutDay.replace(tzinfo=None) > lastActivityDay:
                    lastActivityDay = workoutDay.replace(tzinfo=None)

                if startTime is None:
                    continue # Planned but not executed yet.
                activity.StartTime = startTime

                endTimeEl = xworkout.find("tpw:TimeTotalInSeconds", namespaces=ns)
                if not endTimeEl.text:
                    exclusions.append(APIExcludeActivity("Activity has no duration", activityId=workoutId, userException=UserException(UserExceptionType.Corrupt)))
                    continue

                activity.EndTime = activity.StartTime + timedelta(seconds=float(endTimeEl.text))

                distEl = xworkout.find("tpw:DistanceInMeters", namespaces=ns)
                if distEl.text:
                    activity.Stats.Distance = ActivityStatistic(ActivityStatisticUnit.Meters, value=float(distEl.text))
                # PWX is damn near comprehensive, no need to fill in any of the other statisitcs here, really

                if workoutId in discoveredWorkoutIds:
                    continue # There's the possibility of query overlap, if there are multiple activities on a single day that fall across the query return limit
                discoveredWorkoutIds.append(workoutId)

                workoutTypeEl = xworkout.find("tpw:WorkoutTypeDescription", namespaces=ns)
                if workoutTypeEl.text:
                    if workoutTypeEl.text == "Day Off":
                        continue # TrainingPeaks has some weird activity types...
                    if workoutTypeEl.text not in self._workoutTypeMappings:
                        exclusions.append(APIExcludeActivity("Activity type %s unknown" % workoutTypeEl.text, activityId=workoutId, userException=UserException(UserExceptionType.Corrupt)))
                        continue
                    activity.Type = self._workoutTypeMappings[workoutTypeEl.text]

                activity.ServiceData = {"WorkoutID": workoutId}
                activity.CalculateUID()
                activities.append(activity)

            if not exhaustive:
                break

            # Since TP only lets us query by date range, to get full activity history we need to query successively smaller ranges
            if len(xresp):
                if listStart == lastActivityDay:
                    break # This wouldn't work if you had more than #MaxQueryReturn activities on that day - but that number is probably 50+
                listStart = lastActivityDay
            else:
                break # We're done

        return activities, exclusions

    def DownloadActivity(self, svcRecord, activity):
        params = self._authData(svcRecord)
        params.update({"workoutIds": activity.ServiceData["WorkoutID"], "personId": svcRecord.ExternalID})
        resp = requests.get("https://www.trainingpeaks.com/tpwebservices/service.asmx/GetExtendedWorkoutsForAccessibleAthlete", params=params)
        activity = PWXIO.Parse(resp.content, activity)

        activity.GPS = False
        flat_wps = activity.GetFlatWaypoints()
        for wp in flat_wps:
            if wp.Location and wp.Location.Latitude and wp.Location.Longitude:
                activity.GPS = True
                break

        return activity

    def UploadActivity(self, svcRecord, activity):
        pwxdata = PWXIO.Dump(activity)
        params = self._authData(svcRecord)
        resp = requests.post("https://www.trainingpeaks.com/TPWebServices/EasyFileUpload.ashx", params=params, data=pwxdata.encode("UTF-8"))
        if resp.text != "OK":
            raise APIException("Unable to upload activity response " + resp.text + " status " + str(resp.status_code))

########NEW FILE########
__FILENAME__ = settings
import os

# Django settings for tapiriik project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

ALLOWED_HOSTS = ["tapiriik.com", "localhost"]

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/var/www/example.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
STATIC_ROOT = 'C:/wamp/www/tapiriik/tapiriik/static/'

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

STATICFILES_STORAGE = 'pipeline.storage.PipelineCachedStorage'

PIPELINE_JS = {
    'tapiriik-js': {
        'source_filenames': (
          'js/jquery.address-1.5.min.js',
          'js/tapiriik.js',
        ),
        'output_filename': 'js/tapiriik.min.js',
    },
    'tapiriik-user-js': {
        'source_filenames': (
          'js/jstz.min.js',
          'js/tapiriik-ng.js',
        ),
        'output_filename': 'js/tapiriik-user.min.js',
    }
}

PIPELINE_CSS = {
    'tapiriik-css': {
        'source_filenames': (
          'css/style.css',
        ),
        'output_filename': 'css/style.min.css',
    },
}

PIPELINE_DISABLE_WRAPPER = True

# Make this unique, and don't share it with anybody.
# and yes, this is overriden in local_settings.py
SECRET_KEY = 'vag26gs^t+_y0msoemqo%_5gb*th(i!v$l6##bq9tu2ggcsn13'

# key used in credential storage - please see note in credential_storage.py
CREDENTIAL_STORAGE_KEY = b"NotTheRealKeyFYI"

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'tapiriik.web.startup.Startup',
    'tapiriik.web.startup.ServiceWebStartup',
    'tapiriik.auth.SessionAuth'
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"  # file-based sessions on windows are terrible

ROOT_URLCONF = 'tapiriik.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'tapiriik.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    "I:/wamp/www/tapiriik/tapiriik/web/templates",
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'tapiriik.web.views.ab_experiment_context',
    'tapiriik.web.context_processors.user',
    'tapiriik.web.context_processors.config',
    'tapiriik.web.context_processors.js_bridge',
    'tapiriik.web.context_processors.stats',
    'tapiriik.web.context_processors.providers',
    'django.core.context_processors.static',)

INSTALLED_APPS = (
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'tapiriik.web',
    'pipeline'
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'console': {
            'level': 'ERROR',
            'class': 'logging.StreamHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins', 'console'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

TEST_RUNNER = 'tapiriik.testing.MongoDBTestRunner'

MONGO_HOST = "localhost"

WEB_ROOT = 'http://localhost:8000'

PP_WEBSCR = "https://www.sandbox.paypal.com/cgi-bin/webscr"
PP_BUTTON_ID = "XD6G9Z7VMRM3Q"
PP_RECEIVER_ID = "NR6NTNSRT7NDJ"
PAYMENT_AMOUNT = 2
PAYMENT_SYNC_DAYS = 365.25
PAYMENT_CURRENCY = "USD"

# Hidden from regular signup
SOFT_LAUNCH_SERVICES = ["endomondo"]

# Visibly disabled + excluded from synchronization
DISABLED_SERVICES = []

# Services no longer available - will be removed across the site + excluded from sync.
WITHDRAWN_SERVICES = []

# Where to put per-user sync logs
USER_SYNC_LOGS = "./"

# Set at startup
SITE_VER = "unknown"

# Cache lots of stuff to make local debugging faster
AGGRESSIVE_CACHE = True

# Diagnostics auth, None = no auth
DIAG_AUTH_TOTP_SECRET = DIAG_AUTH_PASSWORD = None

SPORTTRACKS_OPENFIT_ENDPOINT = "https://api.sporttracks.mobi/api/v2"

EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
EMAIL_FILE_PATH = './sent_emails'

WORKER_INDEX = int(os.environ.get("TAPIRIIK_WORKER_INDEX", 0))

# Used for distributing outgoing calls across multiple interfaces

HTTP_SOURCE_ADDR = "0.0.0.0"

RABBITMQ_BROKER_URL = "amqp://guest@localhost//"

GARMIN_CONNECT_USER_WATCH_ACCOUNTS = {}

from .local_settings import *

########NEW FILE########
__FILENAME__ = activity_record
from datetime import datetime
from tapiriik.services.interchange import ActivityStatisticUnit
from tapiriik.services.api import UserException

class ActivityRecord:
    def __init__(self, dbRec=None):
        self.StartTime = None
        self.EndTime = None
        self.Name = None
        self.Notes = None
        self.Type = None
        self.Distance = None
        self.Stationary = None
        self.Private = None
        self.UIDs = []
        self.PresentOnServices = {}
        self.NotPresentOnServices = {}

        # It's practically an ORM!
        if dbRec:
            self.__dict__.update(dbRec)

    def __repr__(self):
        return "<ActivityRecord> " + str(self.__dict__)

    def __deepcopy__(self, x):
        return ActivityRecord(self.__dict__)

    def FromActivity(activity):
        record = ActivityRecord()
        record.SetActivity(activity)
        return record

    def SetActivity(self, activity):
        self.StartTime = activity.StartTime
        self.EndTime = activity.EndTime
        self.Name = activity.Name
        self.Notes = activity.Notes
        self.Type = activity.Type
        self.Distance = activity.Stats.Distance.asUnits(ActivityStatisticUnit.Meters).Value
        self.Stationary = activity.Stationary
        self.Private = activity.Private
        self.UIDs = activity.UIDs

    def MarkAsPresentOn(self, serviceRecord):
        if serviceRecord.Service.ID not in self.PresentOnServices:
            self.PresentOnServices[serviceRecord.Service.ID] = ActivityServicePrescence(listTimestamp=datetime.utcnow())
        else:
            self.PresentOnServices[serviceRecord.Service.ID].ProcessedTimestamp = datetime.utcnow()
        if serviceRecord.Service.ID in self.NotPresentOnServices:
            del self.NotPresentOnServices[serviceRecord.Service.ID]

    def MarkAsSynchronizedTo(self, serviceRecord):
        if serviceRecord.Service.ID not in self.PresentOnServices:
            self.PresentOnServices[serviceRecord.Service.ID] = ActivityServicePrescence(syncTimestamp=datetime.utcnow())
        else:
            self.PresentOnServices[serviceRecord.Service.ID].SynchronizedTimestamp = datetime.utcnow()
        if serviceRecord.Service.ID in self.NotPresentOnServices:
            del self.NotPresentOnServices[serviceRecord.Service.ID]

    def MarkAsNotPresentOtherwise(self, userException):
        self.MarkAsNotPresentOn(None, userException)

    def MarkAsNotPresentOn(self, serviceRecord, userException):
        rec_id = serviceRecord.Service.ID if serviceRecord else None
        if rec_id not in self.NotPresentOnServices:
            self.NotPresentOnServices[rec_id] = ActivityServicePrescence(listTimestamp=datetime.utcnow(), userException=userException)
        else:
            record = self.NotPresentOnServices[rec_id]
            record.ProcessedTimestamp = datetime.utcnow()
            record.UserException = userException


class ActivityServicePrescence:
    def __init__(self, listTimestamp=None, syncTimestamp=None, userException=None):
        self.ProcessedTimestamp = listTimestamp
        self.SynchronizedTimestamp = syncTimestamp
        # If these is a UserException then this object is actually indicating the abscence of an activity from a service.
        if userException is not None and not isinstance(userException, UserException):
            raise ValueError("Provided UserException %s is not a UserException" % userException)
        self.UserException = userException


########NEW FILE########
__FILENAME__ = sync
from tapiriik.database import db, cachedb
from tapiriik.services import Service, ServiceRecord, APIExcludeActivity, ServiceException, ServiceExceptionScope, ServiceWarning, UserException, UserExceptionType
from tapiriik.settings import USER_SYNC_LOGS, DISABLED_SERVICES, WITHDRAWN_SERVICES
from .activity_record import ActivityRecord, ActivityServicePrescence
from datetime import datetime, timedelta
import sys
import os
import socket
import traceback
import pprint
import copy
import random
import logging
import logging.handlers
import pytz

# Set this up seperate from the logger used in this scope, so services logging messages are caught and logged into user's files.
_global_logger = logging.getLogger("tapiriik")

_global_logger.setLevel(logging.DEBUG)
logging_console_handler = logging.StreamHandler(sys.stdout)
logging_console_handler.setLevel(logging.DEBUG)
logging_console_handler.setFormatter(logging.Formatter('%(message)s'))
_global_logger.addHandler(logging_console_handler)

logger = logging.getLogger("tapiriik.sync.worker")

def _formatExc():
    try:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        tb = exc_traceback
        while tb.tb_next:
            tb = tb.tb_next
        frame = tb.tb_frame
        locals_trimmed = []
        for local_name, local_val in frame.f_locals.items():
            value_full = pprint.pformat(local_val)
            if len(value_full) > 1000:
                value_full = value_full[:500] + "..." + value_full[-500:]
            locals_trimmed.append(str(local_name) + "=" + value_full)
        exc = '\n'.join(traceback.format_exception(exc_type, exc_value, exc_traceback)) + "\nLOCALS:\n" + '\n'.join(locals_trimmed)
        logger.exception("Service exception")
        return exc
    finally:
        del exc_traceback, exc_value, exc_type

# It's practically an ORM!

def _packServiceException(step, e):
    res = {"Step": step, "Message": e.Message + "\n" + _formatExc(), "Block": e.Block, "Scope": e.Scope}
    if e.UserException:
        res["UserException"] = _packUserException(e.UserException)
    return res

def _packUserException(userException):
    if userException:
        return {"Type": userException.Type, "Extra": userException.Extra, "InterventionRequired": userException.InterventionRequired, "ClearGroup": userException.ClearGroup}

def _unpackUserException(raw):
    if not raw:
        return None
    if "UserException" in raw:
        raw = raw["UserException"]
    if not raw:
        return None
    if "Type" not in raw:
        return None
    return UserException(raw["Type"], extra=raw["Extra"], intervention_required=raw["InterventionRequired"], clear_group=raw["ClearGroup"])

class Sync:

    SyncInterval = timedelta(hours=1)
    SyncIntervalJitter = timedelta(minutes=5)
    MinimumSyncInterval = timedelta(seconds=30)
    MaximumIntervalBeforeExhaustiveSync = timedelta(days=14)  # Based on the general page size of 50 activites, this would be >3/day...

    def ScheduleImmediateSync(user, exhaustive=None):
        if exhaustive is None:
            db.users.update({"_id": user["_id"]}, {"$set": {"NextSynchronization": datetime.utcnow()}})
        else:
            db.users.update({"_id": user["_id"]}, {"$set": {"NextSynchronization": datetime.utcnow(), "NextSyncIsExhaustive": exhaustive}})

    def SetNextSyncIsExhaustive(user, exhaustive=False):
        db.users.update({"_id": user["_id"]}, {"$set": {"NextSyncIsExhaustive": exhaustive}})

    def PerformGlobalSync(heartbeat_callback=None, version=None):
        from tapiriik.auth import User
        users = db.users.find({
                "NextSynchronization": {"$lte": datetime.utcnow()},
                "SynchronizationWorker": None,
                "$or": [
                    {"SynchronizationHostRestriction": {"$exists": False}},
                    {"SynchronizationHostRestriction": socket.gethostname()}
                    ]
            }).sort("NextSynchronization").limit(1)
        userCt = 0
        for user in users:
            userCt += 1
            syncStart = datetime.utcnow()

            # Always to an exhaustive sync if there were errors
            #   Sometimes services report that uploads failed even when they succeeded.
            #   If a partial sync was done, we'd be assuming that the accounts were consistent past the first page
            #       e.g. If an activity failed to upload far in the past, it would never be attempted again.
            #   So we need to verify the full state of the accounts.
            # But, we can still do a partial sync if there are *only* blocking errors
            #   In these cases, the block will protect that service from being improperly manipulated (though tbqh I can't come up with a situation where this would happen, it's more of a performance thing).
            #   And, when the block is cleared, NextSyncIsExhaustive is set.

            exhaustive = "NextSyncIsExhaustive" in user and user["NextSyncIsExhaustive"] is True
            if "NonblockingSyncErrorCount" in user and user["NonblockingSyncErrorCount"] > 0:
                exhaustive = True

            try:
                Sync.PerformUserSync(user, exhaustive, null_next_sync_on_unlock=True, heartbeat_callback=heartbeat_callback)
            except SynchronizationConcurrencyException:
                pass  # another worker picked them
            else:
                nextSync = None
                if User.HasActivePayment(user):
                    nextSync = datetime.utcnow() + Sync.SyncInterval + timedelta(seconds=random.randint(-Sync.SyncIntervalJitter.total_seconds(), Sync.SyncIntervalJitter.total_seconds()))
                db.users.update({"_id": user["_id"]}, {"$set": {"NextSynchronization": nextSync, "LastSynchronization": datetime.utcnow(), "LastSynchronizationVersion": version}, "$unset": {"NextSyncIsExhaustive": None}})
                syncTime = (datetime.utcnow() - syncStart).total_seconds()
                db.sync_worker_stats.insert({"Timestamp": datetime.utcnow(), "Worker": os.getpid(), "Host": socket.gethostname(), "TimeTaken": syncTime})
        return userCt

    def PerformUserSync(user, exhaustive=False, null_next_sync_on_unlock=False, heartbeat_callback=None):
        SynchronizationTask(user).Run(exhaustive=exhaustive, null_next_sync_on_unlock=null_next_sync_on_unlock, heartbeat_callback=heartbeat_callback)


class SynchronizationTask:
    _logFormat = '[%(levelname)-8s] %(asctime)s (%(name)s:%(lineno)d) %(message)s'
    _logDateFormat = '%Y-%m-%d %H:%M:%S'

    def __init__(self, user):
        self.user = user

    def _lockUser(self):
        db.users.update({"_id": self.user["_id"], "SynchronizationWorker": None}, {"$set": {"SynchronizationWorker": os.getpid(), "SynchronizationHost": socket.gethostname(), "SynchronizationStartTime": datetime.utcnow()}})
        lockCheck = db.users.find_one({"_id": self.user["_id"], "SynchronizationWorker": os.getpid(), "SynchronizationHost": socket.gethostname()})
        if lockCheck is None:
            raise SynchronizationConcurrencyException  # failed to get lock

    def _unlockUser(self, null_next_sync_on_unlock):
        update_values = {"$unset": {"SynchronizationWorker": None}}
        if null_next_sync_on_unlock:
            # Sometimes another worker would pick this record in the timespan between this update and the one in PerformGlobalSync that sets the true next sync time.
            # Hence, an option to unset the NextSynchronization in the same operation that releases the lock on the row.
            update_values["$unset"]["NextSynchronization"] = None
        db.users.update({"_id": self.user["_id"], "SynchronizationWorker": os.getpid(), "SynchronizationHost": socket.gethostname()}, update_values)

    def _loadServiceData(self):
        self._connectedServiceIds = [x["ID"] for x in self.user["ConnectedServices"]]
        self._serviceConnections = [ServiceRecord(x) for x in db.connections.find({"_id": {"$in": self._connectedServiceIds}})]

    def _updateSyncProgress(self, step, progress):
        db.users.update({"_id": self.user["_id"]}, {"$set": {"SynchronizationProgress": progress, "SynchronizationStep": step}})

    def _initializeUserLogging(self):
        self._logging_file_handler = logging.handlers.RotatingFileHandler(USER_SYNC_LOGS + str(self.user["_id"]) + ".log", maxBytes=0, backupCount=10)
        self._logging_file_handler.setFormatter(logging.Formatter(self._logFormat, self._logDateFormat))
        self._logging_file_handler.doRollover()
        _global_logger.addHandler(self._logging_file_handler)

    def _closeUserLogging(self):
        _global_logger.removeHandler(self._logging_file_handler)
        self._logging_file_handler.flush()
        self._logging_file_handler.close()

    def _loadExtendedAuthData(self):
        self._extendedAuthDetails = list(cachedb.extendedAuthDetails.find({"ID": {"$in": self._connectedServiceIds}}))

    def _destroyExtendedAuthData(self):
        cachedb.extendedAuthDetails.remove({"ID": {"$in": self._connectedServiceIds}})

    def _initializePersistedSyncErrorsAndExclusions(self):
        self._syncErrors = {}
        self._syncExclusions = {}

        for conn in self._serviceConnections:
            if hasattr(conn, "SyncErrors"):
                # Remove non-blocking errors
                self._syncErrors[conn._id] = [x for x in conn.SyncErrors if "Block" in x and x["Block"]]
                del conn.SyncErrors
            else:
                self._syncErrors[conn._id] = []

            # Remove temporary exclusions (live tracking etc).
            self._syncExclusions[conn._id] = dict((k, v) for k, v in (conn.ExcludedActivities if conn.ExcludedActivities else {}).items() if v["Permanent"])

            if conn.ExcludedActivities:
                del conn.ExcludedActivities  # Otherwise the exception messages get really, really, really huge and break mongodb.

    def _writeBackSyncErrorsAndExclusions(self):
        nonblockingSyncErrorsCount = 0
        blockingSyncErrorsCount = 0
        syncExclusionCount = 0
        for conn in self._serviceConnections:
            update_values = {
                "$set": {
                    "SyncErrors": self._syncErrors[conn._id],
                    "ExcludedActivities": self._syncExclusions[conn._id]
                }
            }

            if not self._isServiceExcluded(conn):
                # Only reset the trigger if we succesfully got through the entire sync without bailing on this particular connection
                update_values["$unset"] = {"TriggerPartialSync": None}

            db.connections.update({"_id": conn._id}, update_values)
            nonblockingSyncErrorsCount += len([x for x in self._syncErrors[conn._id] if "Block" not in x or not x["Block"]])
            blockingSyncErrorsCount += len([x for x in self._syncErrors[conn._id] if "Block" in x and x["Block"]])
            syncExclusionCount += len(self._syncExclusions[conn._id].items())

        db.users.update({"_id": self.user["_id"]}, {"$set": {"NonblockingSyncErrorCount": nonblockingSyncErrorsCount, "BlockingSyncErrorCount": blockingSyncErrorsCount, "SyncExclusionCount": syncExclusionCount}})

    def _writeBackActivityRecords(self):
        def _activityPrescences(prescences):
            return dict([(svcId if svcId else "",
                {
                    "Processed": presc.ProcessedTimestamp,
                    "Synchronized": presc.SynchronizedTimestamp,
                    "Exception": _packUserException(presc.UserException)
                }) for svcId, presc in prescences.items()])

        self._activityRecords.sort(key=lambda x: x.StartTime.replace(tzinfo=None), reverse=True)
        composed_records = [
            {
                "StartTime": x.StartTime,
                "EndTime": x.EndTime,
                "Type": x.Type,
                "Name": x.Name,
                "Notes": x.Notes,
                "Private": x.Private,
                "Stationary": x.Stationary,
                "Distance": x.Distance,
                "UIDs": list(x.UIDs),
                "Prescence": _activityPrescences(x.PresentOnServices),
                "Abscence": _activityPrescences(x.NotPresentOnServices)
            }
            for x in self._activityRecords
        ]

        db.activity_records.update(
            {"UserID": self.user["_id"]},
            {
                "$set": {
                    "UserID": self.user["_id"],
                    "Activities": composed_records
                }
            },
            upsert=True
        )

    def _initializeActivityRecords(self):
        raw_records = db.activity_records.find_one({"UserID": self.user["_id"]})
        self._activityRecords = []
        if not raw_records:
            return
        else:
            raw_records = raw_records["Activities"]
            for raw_record in raw_records:
                if "UIDs" not in raw_record:
                    continue # From the few days where this was rolled out without this key...
                rec = ActivityRecord(raw_record)
                rec.UIDs = set(rec.UIDs)
                # Did I mention I should really start using an ORM-type deal any day now?
                for svc, absent in rec.Abscence.items():
                    rec.NotPresentOnServices[svc] = ActivityServicePrescence(absent["Processed"], absent["Synchronized"], _unpackUserException(absent["Exception"]))
                for svc, present in rec.Prescence.items():
                    rec.PresentOnServices[svc] = ActivityServicePrescence(present["Processed"], present["Synchronized"], _unpackUserException(present["Exception"]))
                del rec.Prescence
                del rec.Abscence
                rec.Touched = False
                self._activityRecords.append(rec)

    def _findOrCreateActivityRecord(self, activity):
        for record in self._activityRecords:
            if record.UIDs & activity.UIDs:
                record.Touched = True
                return record
        record = ActivityRecord.FromActivity(activity)
        record.Touched = True
        self._activityRecords.append(record)
        return record

    def _dropUntouchedActivityRecords(self):
        self._activityRecords[:] = [x for x in self._activityRecords if x.Touched]

    def _excludeService(self, serviceRecord, userException):
        self._excludedServices[serviceRecord._id] = userException if userException else None

    def _isServiceExcluded(self, serviceRecord):
        return serviceRecord._id in self._excludedServices

    def _getServiceExclusionUserException(self, serviceRecord):
        return self._excludedServices[serviceRecord._id]

    def _determineRecipientServices(self, activity):
        recipientServices = []
        for conn in self._serviceConnections:
            if conn._id in activity.ServiceDataCollection:
                # The activity record is updated earlier for these, blegh.
                pass
            elif hasattr(conn, "SynchronizedActivities") and len([x for x in activity.UIDs if x in conn.SynchronizedActivities]):
                pass
            elif activity.Type not in conn.Service.SupportedActivities:
                logger.debug("\t...%s doesn't support type %s" % (conn.Service.ID, activity.Type))
                activity.Record.MarkAsNotPresentOn(conn, UserException(UserExceptionType.TypeUnsupported))
            else:
                recipientServices.append(conn)
        return recipientServices

    def _coalesceDatetime(self, a, b, knownTz=None):
        """ Returns the most informative (TZ-wise) datetime of those provided - defaulting to the first if they are equivalently descriptive """
        if not b:
            if knownTz and a and not a.tzinfo:
                return a.replace(tzinfo=knownTz)
            return a
        if not a:
            if knownTz and b and not b.tzinfo:
                return b.replace(tzinfo=knownTz)
            return b
        if a.tzinfo and not b.tzinfo:
            return a
        elif b.tzinfo and not a.tzinfo:
            return b
        else:
            if knownTz and not a.tzinfo:
                return a.replace(tzinfo=knownTz)
            return a

    def _accumulateActivities(self, conn, svcActivities, no_add=False):
        # Yep, abs() works on timedeltas
        activityStartLeeway = timedelta(minutes=3)
        activityStartTZOffsetLeeway = timedelta(seconds=10)
        timezoneErrorPeriod = timedelta(hours=38)
        from tapiriik.services.interchange import ActivityType
        for act in svcActivities:
            act.UIDs = set([act.UID])
            if not hasattr(act, "ServiceDataCollection"):
                act.ServiceDataCollection = {}
            if hasattr(act, "ServiceData") and act.ServiceData is not None:
                act.ServiceDataCollection[conn._id] = act.ServiceData
                del act.ServiceData
            if act.TZ and not hasattr(act.TZ, "localize"):
                raise ValueError("Got activity with TZ type " + str(type(act.TZ)) + " instead of a pytz timezone")
            # Used to ensureTZ() right here - doubt it's needed any more?
            existElsewhere = [
                              x for x in self._activities if
                              (
                                  # Identical
                                  x.UID == act.UID
                                  or
                                  # Check to see if the self._activities are reasonably close together to be considered duplicate
                                  (x.StartTime is not None and
                                   act.StartTime is not None and
                                   (act.StartTime.tzinfo is not None) == (x.StartTime.tzinfo is not None) and
                                   abs(act.StartTime-x.StartTime) < activityStartLeeway
                                  )
                                  or
                                  # Try comparing the time as if it were TZ-aware and in the expected TZ (this won't actually change the value of the times being compared)
                                  (x.StartTime is not None and
                                   act.StartTime is not None and
                                   (act.StartTime.tzinfo is not None) != (x.StartTime.tzinfo is not None) and
                                   abs(act.StartTime.replace(tzinfo=None)-x.StartTime.replace(tzinfo=None)) < activityStartLeeway
                                  )
                                  or
                                  # Sometimes wacky stuff happens and we get two activities with the same mm:ss but different hh, because of a TZ issue somewhere along the line.
                                  # So, we check for any activities +/- 14, wait, 38 hours that have the same minutes and seconds values.
                                  #  (14 hours because Kiribati, and later, 38 hours because of some really terrible import code that existed on a service that shall not be named).
                                  # There's a very low chance that two activities in this period would intersect and be merged together.
                                  # But, given the fact that most users have maybe 0.05 activities per this period, it's an acceptable tradeoff.
                                  (x.StartTime is not None and
                                   act.StartTime is not None and
                                   abs(act.StartTime.replace(tzinfo=None)-x.StartTime.replace(tzinfo=None)) < timezoneErrorPeriod and
                                   abs(act.StartTime.replace(tzinfo=None).replace(hour=0) - x.StartTime.replace(tzinfo=None).replace(hour=0)) < activityStartTZOffsetLeeway
                                   )
                                  or
                                  # Similarly, for half-hour time zones (there are a handful of quarter-hour ones, but I've got to draw a line somewhere, even if I revise it several times)
                                  (x.StartTime is not None and
                                   act.StartTime is not None and
                                   abs(act.StartTime.replace(tzinfo=None)-x.StartTime.replace(tzinfo=None)) < timezoneErrorPeriod and
                                   abs(act.StartTime.replace(tzinfo=None).replace(hour=0) - x.StartTime.replace(tzinfo=None).replace(hour=0)) > timedelta(minutes=30) - (activityStartTZOffsetLeeway / 2) and
                                   abs(act.StartTime.replace(tzinfo=None).replace(hour=0) - x.StartTime.replace(tzinfo=None).replace(hour=0)) < timedelta(minutes=30) + (activityStartTZOffsetLeeway / 2)
                                   )
                               )
                                and
                                # Prevents closely-spaced activities of known different type from being lumped together - esp. important for manually-enetered ones
                                (x.Type == ActivityType.Other or act.Type == ActivityType.Other or x.Type == act.Type or ActivityType.AreVariants([act.Type, x.Type]))
                              ]
            if len(existElsewhere) > 0:
                existingActivity = existElsewhere[0]
                # we don't merge the exclude values here, since at this stage the services have the option of just not returning those activities
                if act.TZ is not None and existingActivity.TZ is None:
                    existingActivity.TZ = act.TZ
                    existingActivity.DefineTZ()
                existingActivity.FallbackTZ = existingActivity.FallbackTZ if existingActivity.FallbackTZ else act.FallbackTZ
                # tortuous merging logic is tortuous
                existingActivity.StartTime = self._coalesceDatetime(existingActivity.StartTime, act.StartTime)
                existingActivity.EndTime = self._coalesceDatetime(existingActivity.EndTime, act.EndTime, knownTz=existingActivity.StartTime.tzinfo)
                existingActivity.Name = existingActivity.Name if existingActivity.Name else act.Name
                existingActivity.Notes = existingActivity.Notes if existingActivity.Notes else act.Notes
                existingActivity.Laps = existingActivity.Laps if len(existingActivity.Laps) > len(act.Laps) else act.Laps
                existingActivity.Type = ActivityType.PickMostSpecific([existingActivity.Type, act.Type])
                existingActivity.Private = existingActivity.Private or act.Private
                if act.Stationary is not None:
                    if existingActivity.Stationary is None:
                        existingActivity.Stationary = act.Stationary
                    else:
                        existingActivity.Stationary = existingActivity.Stationary and act.Stationary # Let's be optimistic here
                else:
                    pass # Nothing to do - existElsewhere is either more speicifc or equivalently indeterminate
                if act.GPS is not None:
                    if existingActivity.GPS is None:
                        existingActivity.GPS = act.GPS
                    else:
                        existingActivity.GPS = act.GPS or existingActivity.GPS
                else:
                    pass # Similarly
                existingActivity.Stats.coalesceWith(act.Stats)

                serviceDataCollection = dict(act.ServiceDataCollection)
                serviceDataCollection.update(existingActivity.ServiceDataCollection)
                existingActivity.ServiceDataCollection = serviceDataCollection

                existingActivity.UIDs |= act.UIDs  # I think this is merited
                act.UIDs = existingActivity.UIDs  # stop the circular inclusion, not that it matters
                continue
            if not no_add:
                self._activities.append(act)

    def _determineEligibleRecipientServices(self, activity, recipientServices):
        from tapiriik.auth import User
        eligibleServices = []
        for destinationSvcRecord in recipientServices:
            if self._isServiceExcluded(destinationSvcRecord):
                logger.info("\t\tExcluded " + destinationSvcRecord.Service.ID)
                activity.Record.MarkAsNotPresentOn(destinationSvcRecord, self._getServiceExclusionUserException(destinationSvcRecord))
                continue  # we don't know for sure if it needs to be uploaded, hold off for now
            flowException = True

            sources = [[y for y in self._serviceConnections if y._id == x][0] for x in activity.ServiceDataCollection.keys()]
            for src in sources:
                if src.Service.ID in WITHDRAWN_SERVICES:
                    continue # They can't see this service to change the configuration.
                if not User.CheckFlowException(self.user, src, destinationSvcRecord):
                    flowException = False
                    break

            if flowException:
                logger.info("\t\tFlow exception for " + destinationSvcRecord.Service.ID)
                activity.Record.MarkAsNotPresentOn(destinationSvcRecord, UserException(UserExceptionType.FlowException))
                continue

            destSvc = destinationSvcRecord.Service
            if destSvc.RequiresConfiguration(destinationSvcRecord):
                logger.info("\t\t" + destSvc.ID + " not configured")
                activity.Record.MarkAsNotPresentOn(destinationSvcRecord, UserException(UserExceptionType.NotConfigured))
                continue  # not configured, so we won't even try
            if not destSvc.ReceivesStationaryActivities and activity.Stationary:
                logger.info("\t\t" + destSvc.ID + " doesn't receive stationary activities")
                activity.Record.MarkAsNotPresentOn(destinationSvcRecord, UserException(UserExceptionType.StationaryUnsupported))
                continue # Missing this originally, no wonder...
            # ReceivesNonGPSActivitiesWithOtherSensorData doesn't matter if the activity is stationary.
            # (and the service accepts stationary activities - guaranteed immediately above)
            if not activity.Stationary:
                if not (destSvc.ReceivesNonGPSActivitiesWithOtherSensorData or activity.GPS):
                    logger.info("\t\t" + destSvc.ID + " doesn't receive non-GPS activities")
                    activity.Record.MarkAsNotPresentOn(destinationSvcRecord, UserException(UserExceptionType.NonGPSUnsupported))
                    continue
            eligibleServices.append(destinationSvcRecord)
        return eligibleServices

    def _accumulateExclusions(self, serviceRecord, exclusions):
        if type(exclusions) is not list:
            exclusions = [exclusions]
        for exclusion in exclusions:
            identifier = exclusion.Activity.UID if exclusion.Activity else exclusion.ExternalActivityID
            if not identifier:
                raise ValueError("Activity excluded with no identifying information")
            identifier = str(identifier).replace(".", "_")
            self._syncExclusions[serviceRecord._id][identifier] = {"Message": exclusion.Message, "Activity": str(exclusion.Activity) if exclusion.Activity else None, "ExternalActivityID": exclusion.ExternalActivityID, "Permanent": exclusion.Permanent, "Effective": datetime.utcnow(), "UserException": _packUserException(exclusion.UserException)}

    def _ensurePartialSyncPollingSubscription(self, conn):
        if conn.Service.PartialSyncRequiresTrigger and not conn.PartialSyncTriggerSubscribed:
            if conn.Service.RequiresExtendedAuthorizationDetails and not conn.ExtendedAuthorization:
                logger.info("No ext auth details, cannot subscribe")
                return # We (probably) can't subscribe unless we have their credentials. May need to change this down the road.
            try:
                conn.Service.SubscribeToPartialSyncTrigger(conn)
            except ServiceException as e:
                logger.exception("Failure while subscribing to partial sync trigger")

    def _primeExtendedAuthDetails(self, conn):
        if conn.Service.RequiresExtendedAuthorizationDetails:
            if not hasattr(conn, "ExtendedAuthorization") or not conn.ExtendedAuthorization:
                extAuthDetails = [x["ExtendedAuthorization"] for x in self._extendedAuthDetails if x["ID"] == conn._id]
                if not len(extAuthDetails):
                    conn.ExtendedAuthorization = None
                    return
                # The connection never gets saved in full again, so we can sub these in here at no risk.
                conn.ExtendedAuthorization = extAuthDetails[0]

    def _downloadActivityList(self, conn, exhaustive, no_add=False):
        svc = conn.Service
        # Bail out as appropriate for the entire account (_syncErrors contains only blocking errors at this point)
        if [x for x in self._syncErrors[conn._id] if x["Scope"] == ServiceExceptionScope.Account]:
            raise SynchronizationCompleteException()

        # ...and for this specific service
        if [x for x in self._syncErrors[conn._id] if x["Scope"] == ServiceExceptionScope.Service]:
            logger.info("Service %s is blocked:" % conn.Service.ID)
            self._excludeService(conn, _unpackUserException([x for x in self._syncErrors[conn._id] if x["Scope"] == ServiceExceptionScope.Service][0]))
            return

        if svc.ID in DISABLED_SERVICES or svc.ID in WITHDRAWN_SERVICES:
            logger.info("Service %s is widthdrawn" % conn.Service.ID)
            self._excludeService(conn, UserException(UserExceptionType.Other))
            return

        if svc.RequiresExtendedAuthorizationDetails:
            if not conn.ExtendedAuthorization:
                logger.info("No extended auth details for " + svc.ID)
                self._excludeService(conn, UserException(UserExceptionType.MissingCredentials))
                return

        try:
            logger.info("\tRetrieving list from " + svc.ID)
            svcActivities, svcExclusions = svc.DownloadActivityList(conn, exhaustive)
        except (ServiceException, ServiceWarning) as e:
            self._syncErrors[conn._id].append(_packServiceException(SyncStep.List, e))
            self._excludeService(conn, e.UserException)
            if not issubclass(e.__class__, ServiceWarning):
                return
        except Exception as e:
            self._syncErrors[conn._id].append({"Step": SyncStep.List, "Message": _formatExc()})
            self._excludeService(conn, UserException(UserExceptionType.ListingError))
            return
        self._accumulateExclusions(conn, svcExclusions)
        self._accumulateActivities(conn, svcActivities, no_add=no_add)

    def _estimateFallbackTZ(self, activities):
        from collections import Counter
        # With the hope that the majority of the activity records returned will have TZs, and the user's current TZ will constitute the majority.
        TZOffsets = [x.StartTime.utcoffset().total_seconds() / 60 for x in activities if x.TZ is not None]
        mode = Counter(TZOffsets).most_common(1)
        if not len(mode):
            if "Timezone" in self.user:
                return pytz.timezone(self.user["Timezone"])
            return None
        return pytz.FixedOffset(mode[0][0])

    def _applyFallbackTZ(self):
        # Attempt to assign fallback TZs to all stationary/potentially-stationary activities, since we may not be able to determine TZ any other way.
        fallbackTZ = self._estimateFallbackTZ(self._activities)
        if fallbackTZ:
            logger.info("Setting fallback TZs to %s" % fallbackTZ )
            for act in self._activities:
                act.FallbackTZ = fallbackTZ

    def _processActivityOrigins(self):
        logger.info("Reading activity origins")
        origins = list(db.activity_origins.find({"ActivityUID": {"$in": [x.UID for x in self._activities]}}))
        activitiesWithOrigins = [x["ActivityUID"] for x in origins]

        logger.info("Populating origins")
        # Populate origins
        for activity in self._activities:
            if len(activity.ServiceDataCollection.keys()) == 1:
                if not len(self._excludedServices):  # otherwise it could be incorrectly recorded
                    # we can log the origin of this activity
                    if activity.UID not in activitiesWithOrigins:  # No need to hammer the database updating these when they haven't changed
                        logger.info("\t\t Updating db with origin for proceeding activity")
                        db.activity_origins.insert({"ActivityUID": activity.UID, "Origin": {"Service": [[y for y in self._serviceConnections if y._id == x][0] for x in activity.ServiceDataCollection.keys()][0].Service.ID, "ExternalID": [[y.ExternalID for y in self._serviceConnections if y._id == x][0] for x in activity.ServiceDataCollection.keys()][0]}})
                    activity.Origin = [[y for y in self._serviceConnections if y._id == x][0] for x in activity.ServiceDataCollection.keys()][0]
            else:
                if activity.UID in activitiesWithOrigins:
                    knownOrigin = [x for x in origins if x["ActivityUID"] == activity.UID]
                    connectedOrigins = [x for x in self._serviceConnections if knownOrigin[0]["Origin"]["Service"] == x.Service.ID and knownOrigin[0]["Origin"]["ExternalID"] == x.ExternalID]
                    if len(connectedOrigins) > 0:  # they might have disconnected it
                        activity.Origin = connectedOrigins[0]
                    else:
                        activity.Origin = ServiceRecord(knownOrigin[0]["Origin"])  # I have it on good authority that this will work

    def _updateSynchronizedActivities(self, activity):
        # Locally mark this activity as present on the appropriate services.
        # These needs to happen regardless of whether the activity is going to be synchronized.
        #   Before, I had moved this under all the eligibility/recipient checks, but that could cause persistent duplicate self._activities when the user had already manually uploaded the same activity to multiple sites.
        updateServicesWithExistingActivity = False
        for serviceWithExistingActivityId in activity.ServiceDataCollection.keys():
            serviceWithExistingActivity = [x for x in self._serviceConnections if x._id == serviceWithExistingActivityId][0]
            if not hasattr(serviceWithExistingActivity, "SynchronizedActivities") or not (activity.UIDs <= set(serviceWithExistingActivity.SynchronizedActivities)):
                updateServicesWithExistingActivity = True
                break

        if updateServicesWithExistingActivity:
            logger.debug("\t\tUpdating SynchronizedActivities")
            db.connections.update({"_id": {"$in": list(activity.ServiceDataCollection.keys())}},
                                  {"$addToSet": {"SynchronizedActivities": {"$each": list(activity.UIDs)}}},
                                  multi=True)

    def _updateActivityRecordInitialPrescence(self, activity):
        for connWithExistingActivityId in activity.ServiceDataCollection.keys():
            connWithExistingActivity = [x for x in self._serviceConnections if x._id == connWithExistingActivityId][0]
            activity.Record.MarkAsPresentOn(connWithExistingActivity)
        for conn in self._serviceConnections:
            if hasattr(conn, "SynchronizedActivities") and len([x for x in activity.UIDs if x in conn.SynchronizedActivities]):
                activity.Record.MarkAsPresentOn(conn)

    def _downloadActivity(self, activity):
        act = None
        actAvailableFromSvcIds = activity.ServiceDataCollection.keys()
        actAvailableFromSvcs = [[x for x in self._serviceConnections if x._id == dlSvcRecId][0] for dlSvcRecId in actAvailableFromSvcIds]

        servicePriorityList = Service.PreferredDownloadPriorityList()
        actAvailableFromSvcs.sort(key=lambda x: servicePriorityList.index(x.Service))

        # TODO: redo this, it was completely broken:
        # Prefer retrieving the activity from its original source.

        for dlSvcRecord in actAvailableFromSvcs:
            dlSvc = dlSvcRecord.Service
            logger.info("\tfrom " + dlSvc.ID)
            if activity.UID in self._syncExclusions[dlSvcRecord._id]:
                activity.Record.MarkAsNotPresentOtherwise(_unpackUserException(self._syncExclusions[dlSvcRecord._id][activity.UID]))
                logger.info("\t\t...has activity exclusion logged")
                continue
            if self._isServiceExcluded(dlSvcRecord):
                activity.Record.MarkAsNotPresentOtherwise(self._getServiceExclusionUserException(dlSvcRecord))
                logger.info("\t\t...service became excluded after listing") # Because otherwise we'd never have been trying to download from it in the first place.
                continue

            workingCopy = copy.copy(activity)  # we can hope
            # Load in the service data in the same place they left it.
            workingCopy.ServiceData = workingCopy.ServiceDataCollection[dlSvcRecord._id] if dlSvcRecord._id in workingCopy.ServiceDataCollection else None
            try:
                workingCopy = dlSvc.DownloadActivity(dlSvcRecord, workingCopy)
            except (ServiceException, ServiceWarning) as e:
                self._syncErrors[dlSvcRecord._id].append(_packServiceException(SyncStep.Download, e))
                if e.Block and e.Scope == ServiceExceptionScope.Service: # I can't imagine why the same would happen at the account level, so there's no behaviour to immediately abort the sync in that case.
                    self._excludeService(dlSvcRecord, e.UserException)
                if not issubclass(e.__class__, ServiceWarning):
                    activity.Record.MarkAsNotPresentOtherwise(e.UserException)
                    continue
            except APIExcludeActivity as e:
                logger.info("\t\texcluded by service: %s" % e.Message)
                e.Activity = workingCopy
                self._accumulateExclusions(dlSvcRecord, e)
                activity.Record.MarkAsNotPresentOtherwise(e.UserException)
                continue
            except Exception as e:
                self._syncErrors[dlSvcRecord._id].append({"Step": SyncStep.Download, "Message": _formatExc()})
                activity.Record.MarkAsNotPresentOtherwise(UserException(UserExceptionType.DownloadError))
                continue

            if workingCopy.Private and not dlSvcRecord.GetConfiguration()["sync_private"]:
                logger.info("\t\t...is private and restricted from sync")  # Sync exclusion instead?
                activity.Record.MarkAsNotPresentOtherwise(UserException(UserExceptionType.Private))
                continue
            try:
                workingCopy.CheckSanity()
            except:
                logger.info("\t\t...failed sanity check")
                self._accumulateExclusions(dlSvcRecord, APIExcludeActivity("Sanity check failed " + _formatExc(), activity=workingCopy))
                activity.Record.MarkAsNotPresentOtherwise(UserException(UserExceptionType.SanityError))
                continue
            else:
                act = workingCopy
                act.SourceConnection = dlSvcRecord
                break  # succesfully got the activity + passed sanity checks, can stop now
        # If nothing was downloaded at this point, the activity record will show the most recent error - which is fine enough, since only one service is needed to get the activity.
        return act, dlSvc

    def _uploadActivity(self, activity, destinationServiceRec):
        destSvc = destinationServiceRec.Service
        try:
            return destSvc.UploadActivity(destinationServiceRec, activity)
        except (ServiceException, ServiceWarning) as e:
            self._syncErrors[destinationServiceRec._id].append(_packServiceException(SyncStep.Upload, e))
            if e.Block and e.Scope == ServiceExceptionScope.Service: # Similarly, no behaviour to immediately abort the sync if an account-level exception is raised
                self._excludeService(destinationServiceRec, e.UserException)
            if not issubclass(e.__class__, ServiceWarning):
                activity.Record.MarkAsNotPresentOn(destinationServiceRec, e.UserException if e.UserException else UserException(UserExceptionType.UploadError))
                raise UploadException()
        except Exception as e:
            self._syncErrors[destinationServiceRec._id].append({"Step": SyncStep.Upload, "Message": _formatExc()})
            activity.Record.MarkAsNotPresentOn(destinationServiceRec, UserException(UserExceptionType.UploadError))
            raise UploadException()

    def Run(self, exhaustive=False, null_next_sync_on_unlock=False, heartbeat_callback=None):
        if len(self.user["ConnectedServices"]) <= 1:
            return # Done and done!
        from tapiriik.services.interchange import ActivityStatisticUnit

        # Mark this user as in-progress.
        self._lockUser()

        # Reset their progress
        self._updateSyncProgress(SyncStep.List, 0)

        self._initializeUserLogging()

        logger.info("Beginning sync for " + str(self.user["_id"]) + "(exhaustive: " + str(exhaustive) + ")")

        # Sets up serviceConnections
        self._loadServiceData()

        self._loadExtendedAuthData()

        self._activities = []
        self._excludedServices = {}
        self._deferredServices = []

        self._initializePersistedSyncErrorsAndExclusions()

        self._initializeActivityRecords()

        try:
            try:
                for conn in self._serviceConnections:
                    # If we're not going to be doing anything anyways, stop now
                    if len(self._serviceConnections) - len(self._excludedServices) <= 1:
                        raise SynchronizationCompleteException()

                    self._primeExtendedAuthDetails(conn)

                    logger.info("Ensuring partial sync poll subscription")
                    self._ensurePartialSyncPollingSubscription(conn)

                    if not exhaustive and conn.Service.PartialSyncRequiresTrigger and "TriggerPartialSync" not in conn.__dict__ and not conn.Service.ShouldForcePartialSyncTrigger(conn):
                        logger.info("Service %s has not been triggered" % conn.Service.ID)
                        self._deferredServices.append(conn._id)
                        continue

                    if heartbeat_callback:
                        heartbeat_callback(SyncStep.List)

                    self._updateSyncProgress(SyncStep.List, conn.Service.ID)
                    self._downloadActivityList(conn, exhaustive)

                self._applyFallbackTZ()

                self._processActivityOrigins()

                # Makes reading the logs much easier.
                self._activities = sorted(self._activities, key=lambda v: v.StartTime.replace(tzinfo=None), reverse=True)

                totalActivities = len(self._activities)
                processedActivities = 0

                for activity in self._activities:
                    logger.info(str(activity) + " " + str(activity.UID[:3]) + " from " + str([[y.Service.ID for y in self._serviceConnections if y._id == x][0] for x in activity.ServiceDataCollection.keys()]))
                    logger.info(" Name: %s Notes: %s Distance: %s%s" % (activity.Name[:15] if activity.Name else "", activity.Notes[:15] if activity.Notes else "", activity.Stats.Distance.Value, activity.Stats.Distance.Units))
                    try:
                        activity.Record = self._findOrCreateActivityRecord(activity) # Make it a member of the activity, to avoid passing it around as a seperate parameter everywhere.

                        self._updateSynchronizedActivities(activity)
                        self._updateActivityRecordInitialPrescence(activity)

                        # We don't always know if the activity is private before it's downloaded, but we can check anyways since it saves a lot of time.
                        if activity.Private:
                            actAvailableFromConnIds = activity.ServiceDataCollection.keys()
                            actAvailableFromConns = [[x for x in self._serviceConnections if x._id == dlSvcRecId][0] for dlSvcRecId in actAvailableFromConnIds]
                            override_private = False
                            for conn in actAvailableFromConns:
                                if conn.GetConfiguration()["sync_private"]:
                                    override_private = True
                                    break

                            if not override_private:
                                logger.info("\t\t...is private and restricted from sync (pre-download)")  # Sync exclusion instead?
                                activity.Record.MarkAsNotPresentOtherwise(UserException(UserExceptionType.Private))
                                raise ActivityShouldNotSynchronizeException()

                        recipientServices = None
                        eligibleServices = None
                        while True:
                            # recipientServices are services that don't already have this activity
                            recipientServices = self._determineRecipientServices(activity)
                            if len(recipientServices) == 0:
                                totalActivities -= 1  # doesn't count
                                raise ActivityShouldNotSynchronizeException()

                            # eligibleServices are services that are permitted to receive this activity - taking into account flow exceptions, excluded services, unfufilled configuration requirements, etc.
                            eligibleServices = self._determineEligibleRecipientServices(activity=activity, recipientServices=recipientServices)

                            if not len(eligibleServices):
                                logger.info("\t\t...has no eligible destinations")
                                totalActivities -= 1  # Again, doesn't really count.
                                raise ActivityShouldNotSynchronizeException()

                            has_deferred = False
                            for conn in eligibleServices:
                                if conn._id in self._deferredServices:
                                    logger.info("Doing deferred list from %s" % conn.Service.ID)
                                    # no_add since...
                                    #  a) we're iterating over the list it'd be adding to, and who knows what will happen then
                                    #  b) for the current use of deferred services, we don't care about new activities
                                    self._downloadActivityList(conn, exhaustive, no_add=True)
                                    self._deferredServices.remove(conn._id)
                                    has_deferred = True

                            # If we had deferred listing activities from a service, we have to repeat this loop to consider the new info
                            # Otherwise, once was enough
                            if not has_deferred:
                                break


                        # This is after the above exit points since they're the most frequent (& cheapest) cases - want to avoid DB churn
                        if heartbeat_callback:
                            heartbeat_callback(SyncStep.Download)

                        if processedActivities == 0:
                            syncProgress = 0
                        elif totalActivities <= 0:
                            syncProgress = 1
                        else:
                            syncProgress = max(0, min(1, processedActivities / totalActivities))
                        self._updateSyncProgress(SyncStep.Download, syncProgress)

                        # The second most important line of logging in the application...
                        logger.info("\t\t...to " + str([x.Service.ID for x in recipientServices]))

                        # Download the full activity record
                        full_activity, activitySource = self._downloadActivity(activity)

                        if full_activity is None:  # couldn't download it from anywhere, or the places that had it said it was broken
                            # The activity record gets updated in _downloadActivity
                            processedActivities += 1  # we tried
                            raise ActivityShouldNotSynchronizeException()

                        full_activity.CleanStats()
                        full_activity.CleanWaypoints()

                        try:
                            full_activity.EnsureTZ()
                        except:
                            logger.error("\tCould not determine TZ")
                            self._accumulateExclusions(full_activity.SourceConnection, APIExcludeActivity("Could not determine TZ", activity=full_activity, permanent=False))
                            activity.Record.MarkAsNotPresentOtherwise(UserException(UserExceptionType.UnknownTZ))
                            raise ActivityShouldNotSynchronizeException()
                        else:
                            logger.debug("\tDetermined TZ %s" % full_activity.TZ)

                        activity.Record.SetActivity(activity) # Update with whatever more accurate information we may have.

                        full_activity.Record = activity.Record # Some services don't return the same object, so this gets lost, which is meh, but...

                        for destinationSvcRecord in eligibleServices:
                            if heartbeat_callback:
                                heartbeat_callback(SyncStep.Upload)
                            destSvc = destinationSvcRecord.Service
                            if not destSvc.ReceivesStationaryActivities and full_activity.Stationary:
                                logger.info("\t\t...marked as stationary during download")
                                activity.Record.MarkAsNotPresentOn(destinationSvcRecord, UserException(UserExceptionType.StationaryUnsupported))
                                continue
                            if not full_activity.Stationary:
                                if not (destSvc.ReceivesNonGPSActivitiesWithOtherSensorData or full_activity.GPS):
                                    logger.info("\t\t...marked as non-GPS during download")
                                    activity.Record.MarkAsNotPresentOn(destinationSvcRecord, UserException(UserExceptionType.NonGPSUnsupported))
                                    continue

                            uploaded_external_id = None
                            logger.info("\t  Uploading to " + destSvc.ID)
                            try:
                                uploaded_external_id = self._uploadActivity(full_activity, destinationSvcRecord)
                            except UploadException:
                                continue # At this point it's already been added to the error collection, so we can just bail.
                            logger.info("\t  Uploaded")

                            activity.Record.MarkAsSynchronizedTo(destinationSvcRecord)

                            if uploaded_external_id:
                                # record external ID, for posterity (and later debugging)
                                db.uploaded_activities.insert({"ExternalID": uploaded_external_id, "Service": destSvc.ID, "UserExternalID": destinationSvcRecord.ExternalID, "Timestamp": datetime.utcnow()})
                            # flag as successful
                            db.connections.update({"_id": destinationSvcRecord._id},
                                                  {"$addToSet": {"SynchronizedActivities": {"$each": list(activity.UIDs)}}})

                            db.sync_stats.update({"ActivityID": activity.UID}, {"$addToSet": {"DestinationServices": destSvc.ID, "SourceServices": activitySource.ID}, "$set": {"Distance": activity.Stats.Distance.asUnits(ActivityStatisticUnit.Meters).Value, "Timestamp": datetime.utcnow()}}, upsert=True)
                        del full_activity
                        processedActivities += 1
                    except ActivityShouldNotSynchronizeException:
                        continue
                    finally:
                        del activity

            except SynchronizationCompleteException:
                # This gets thrown when there is obviously nothing left to do - but we still need to clean things up.
                logger.info("SynchronizationCompleteException thrown")

            logger.info("Writing back service data")
            self._writeBackSyncErrorsAndExclusions()

            if exhaustive:
                # Clean up potentially orphaned records, since we know everything is here.
                logger.info("Clearing old activity records")
                self._dropUntouchedActivityRecords()

            logger.info("Writing back activity records")
            self._writeBackActivityRecords()

            logger.info("Finalizing")
            # Clear non-persisted extended auth details.
            self._destroyExtendedAuthData()
            # Unlock the user.
            self._unlockUser(null_next_sync_on_unlock)

        except SynchronizationConcurrencyException:
            raise # Don't spit out the "Core sync exception" error
        except:
            # oops.
            logger.exception("Core sync exception")
            raise
        else:
            logger.info("Finished sync for %s" % self.user["_id"])
        finally:
            self._closeUserLogging()


class UploadException(Exception):
    pass

class ActivityShouldNotSynchronizeException(Exception):
    pass

class SynchronizationCompleteException(Exception):
    pass


class SynchronizationConcurrencyException(Exception):
    pass


class SyncStep:
    List = "list"
    Download = "download"
    Upload = "upload"

########NEW FILE########
__FILENAME__ = gpx
from tapiriik.testing.testtools import TestTools, TapiriikTestCase
from tapiriik.services.gpx import GPXIO


class GPXTests(TapiriikTestCase):
    def test_constant_representation(self):
        ''' ensures that gpx import/export is symetric '''

        svcA, other = TestTools.create_mock_services()
        svcA.SupportsHR = svcA.SupportsCadence = svcA.SupportsTemp = True
        svcA.SupportsPower = svcA.SupportsCalories = False
        act = TestTools.create_random_activity(svcA, tz=True)

        mid = GPXIO.Dump(act)

        act2 = GPXIO.Parse(bytes(mid,"UTF-8"))
        act2.TZ = act.TZ  # we need to fake this since local TZ isn't defined in GPX files, and TZ discovery will flail with random activities
        act2.AdjustTZ()
        act.Stats.Distance = act2.Stats.Distance = None  # same here

        self.assertActivitiesEqual(act2, act)

########NEW FILE########
__FILENAME__ = interchange
from unittest import TestCase

from tapiriik.testing.testtools import TestTools, TapiriikTestCase

from tapiriik.sync import Sync
from tapiriik.services import Service
from tapiriik.services.interchange import Activity, ActivityType, Waypoint, WaypointType
from tapiriik.sync import Sync

from datetime import datetime, timedelta
import random


class InterchangeTests(TapiriikTestCase):

    def test_round_precise_time(self):
        ''' Some services might return really exact times, while others would round to the second - needs to be accounted for in hash algo '''
        actA = Activity()
        actA.StartTime = datetime(1, 2, 3, 4, 5, 6, 7)
        actB = Activity()
        actB.StartTime = datetime(1, 2, 3, 4, 5, 6, 7) + timedelta(0, 0.1337)

        actA.CalculateUID()
        actB.CalculateUID()

        self.assertEqual(actA.UID, actB.UID)

    def test_constant_representation(self):
        ''' ensures that all services' API clients are consistent through a simulated download->upload cycle '''
        #  runkeeper
        rkSvc = Service.FromID("runkeeper")
        act = TestTools.create_random_activity(rkSvc, rkSvc.SupportedActivities[0])
        record = rkSvc._createUploadData(act)
        returnedAct = rkSvc._populateActivity(record)
        act.Name = None  # RK doesn't have a "name" field, so it's fudged into the notes, but not really
        rkSvc._populateActivityWaypoints(record, returnedAct)
        self.assertActivitiesEqual(returnedAct, act)

        #  can't test Strava well this way, the upload and download formats are entirely different

        #  endomondo - only waypoints at this point, the activity metadata is somewhat out-of-band
        eSvc = Service.FromID("endomondo")

        act = TestTools.create_random_activity(eSvc, eSvc.SupportedActivities[0])
        oldWaypoints = act.Waypoints
        self.assertEqual(oldWaypoints[0].Calories, None)
        record = eSvc._createUploadData(act)
        eSvc._populateActivityFromTrackData(act, record)
        self.assertEqual(oldWaypoints, act.Waypoints)

    def test_duration_calculation(self):
        ''' ensures that true-duration calculation is being reasonable '''
        act = TestTools.create_blank_activity()
        act.StartTime = datetime.now()
        act.EndTime = act.StartTime + timedelta(hours=3)

        # No waypoints
        self.assertRaises(ValueError, act.GetTimerTime)

        # Too few waypoints
        act.Waypoints = [Waypoint(timestamp=act.StartTime), Waypoint(timestamp=act.EndTime)]
        self.assertRaises(ValueError, act.GetTimerTime)

        # straight-up calculation
        act.EndTime = act.StartTime + timedelta(seconds=14)
        act.Waypoints = [Waypoint(timestamp=act.StartTime),
                         Waypoint(timestamp=act.StartTime + timedelta(seconds=2)),
                         Waypoint(timestamp=act.StartTime + timedelta(seconds=6)),
                         Waypoint(timestamp=act.StartTime + timedelta(seconds=10)),
                         Waypoint(timestamp=act.StartTime + timedelta(seconds=14))]
        self.assertEqual(act.GetTimerTime(), timedelta(seconds=14))

        # pauses
        act.EndTime = act.StartTime + timedelta(seconds=14)
        act.Waypoints = [Waypoint(timestamp=act.StartTime),
                         Waypoint(timestamp=act.StartTime + timedelta(seconds=2)),
                         Waypoint(timestamp=act.StartTime + timedelta(seconds=6), ptType=WaypointType.Pause),
                         Waypoint(timestamp=act.StartTime + timedelta(seconds=9), ptType=WaypointType.Pause),
                         Waypoint(timestamp=act.StartTime + timedelta(seconds=10), ptType=WaypointType.Resume),
                         Waypoint(timestamp=act.StartTime + timedelta(seconds=14))]
        self.assertEqual(act.GetTimerTime(), timedelta(seconds=10))

        # laps - NO effect
        act.EndTime = act.StartTime + timedelta(seconds=14)
        act.Waypoints = [Waypoint(timestamp=act.StartTime),
                         Waypoint(timestamp=act.StartTime + timedelta(seconds=2)),
                         Waypoint(timestamp=act.StartTime + timedelta(seconds=6), ptType=WaypointType.Lap),
                         Waypoint(timestamp=act.StartTime + timedelta(seconds=9)),
                         Waypoint(timestamp=act.StartTime + timedelta(seconds=10), ptType=WaypointType.Lap),
                         Waypoint(timestamp=act.StartTime + timedelta(seconds=14))]
        self.assertEqual(act.GetTimerTime(), timedelta(seconds=14))

        # multiple pauses + ending after pause
        act.EndTime = act.StartTime + timedelta(seconds=20)
        act.Waypoints = [Waypoint(timestamp=act.StartTime),
                         Waypoint(timestamp=act.StartTime + timedelta(seconds=2)),
                         Waypoint(timestamp=act.StartTime + timedelta(seconds=6), ptType=WaypointType.Pause),
                         Waypoint(timestamp=act.StartTime + timedelta(seconds=9), ptType=WaypointType.Pause),
                         Waypoint(timestamp=act.StartTime + timedelta(seconds=10), ptType=WaypointType.Resume),
                         Waypoint(timestamp=act.StartTime + timedelta(seconds=12)),
                         Waypoint(timestamp=act.StartTime + timedelta(seconds=16)),
                         Waypoint(timestamp=act.StartTime + timedelta(seconds=17), ptType=WaypointType.Pause),
                         Waypoint(timestamp=act.StartTime + timedelta(seconds=20), ptType=WaypointType.End)]
        self.assertEqual(act.GetTimerTime(), timedelta(seconds=13))

        # implicit pauses (>1m5s)
        act.EndTime = act.StartTime + timedelta(seconds=20)
        act.Waypoints = [Waypoint(timestamp=act.StartTime),
                         Waypoint(timestamp=act.StartTime + timedelta(seconds=2)),
                         Waypoint(timestamp=act.StartTime + timedelta(seconds=6)),
                         Waypoint(timestamp=act.StartTime + timedelta(seconds=120)),
                         Waypoint(timestamp=act.StartTime + timedelta(seconds=124)),
                         Waypoint(timestamp=act.StartTime + timedelta(seconds=130))]
        self.assertEqual(act.GetTimerTime(), timedelta(seconds=16))

        # mixed pauses - would this ever happen?? Either way, the explicit pause should override the implicit one and cause otherwise-ignored time to be counted
        act.EndTime = act.StartTime + timedelta(seconds=23)
        act.Waypoints = [Waypoint(timestamp=act.StartTime),
                         Waypoint(timestamp=act.StartTime + timedelta(seconds=2)),
                         Waypoint(timestamp=act.StartTime + timedelta(seconds=6)),
                         Waypoint(timestamp=act.StartTime + timedelta(seconds=20), ptType=WaypointType.Pause),
                         Waypoint(timestamp=act.StartTime + timedelta(seconds=24), ptType=WaypointType.Resume),
                         Waypoint(timestamp=act.StartTime + timedelta(seconds=30))]
        self.assertEqual(act.GetTimerTime(), timedelta(seconds=26))

    def test_activity_specificity_resolution(self):
        # Mountain biking is more specific than just cycling
        self.assertEqual(ActivityType.PickMostSpecific([ActivityType.Cycling, ActivityType.MountainBiking]), ActivityType.MountainBiking)

        # But not once we mix in an unrelated activity - pick the first
        self.assertEqual(ActivityType.PickMostSpecific([ActivityType.Cycling, ActivityType.MountainBiking, ActivityType.Swimming]), ActivityType.Cycling)

        # Duplicates
        self.assertEqual(ActivityType.PickMostSpecific([ActivityType.Cycling, ActivityType.MountainBiking, ActivityType.MountainBiking]), ActivityType.MountainBiking)

        # One
        self.assertEqual(ActivityType.PickMostSpecific([ActivityType.MountainBiking]), ActivityType.MountainBiking)

        # With None
        self.assertEqual(ActivityType.PickMostSpecific([None, ActivityType.MountainBiking]), ActivityType.MountainBiking)

        # All None
        self.assertEqual(ActivityType.PickMostSpecific([None, None]), ActivityType.Other)

        # Never pick 'Other' given a better option
        self.assertEqual(ActivityType.PickMostSpecific([ActivityType.Other, ActivityType.MountainBiking]), ActivityType.MountainBiking)

        # Normal w/ Other + None
        self.assertEqual(ActivityType.PickMostSpecific([ActivityType.Other, ActivityType.Cycling, None, ActivityType.MountainBiking]), ActivityType.MountainBiking)

########NEW FILE########
__FILENAME__ = statistics
from unittest import TestCase

from tapiriik.testing.testtools import TapiriikTestCase

from tapiriik.services.interchange import ActivityStatistic, ActivityStatisticUnit


class StatisticTests(TapiriikTestCase):

    def test_unitconv_temp(self):
        stat = ActivityStatistic(ActivityStatisticUnit.DegreesCelcius, value=0)
        self.assertEqual(stat.asUnits(ActivityStatisticUnit.DegreesFahrenheit).Value, 32)

        stat = ActivityStatistic(ActivityStatisticUnit.DegreesCelcius, value=-40)
        self.assertEqual(stat.asUnits(ActivityStatisticUnit.DegreesFahrenheit).Value, -40)

        stat = ActivityStatistic(ActivityStatisticUnit.DegreesFahrenheit, value=-40)
        self.assertEqual(stat.asUnits(ActivityStatisticUnit.DegreesCelcius).Value, -40)

        stat = ActivityStatistic(ActivityStatisticUnit.DegreesFahrenheit, value=32)
        self.assertEqual(stat.asUnits(ActivityStatisticUnit.DegreesCelcius).Value, 0)

    def test_unitconv_distance_nonmetric(self):
        stat = ActivityStatistic(ActivityStatisticUnit.Miles, value=1)
        self.assertEqual(stat.asUnits(ActivityStatisticUnit.Feet).Value, 5280)

        stat = ActivityStatistic(ActivityStatisticUnit.Feet, value=5280/2)
        self.assertEqual(stat.asUnits(ActivityStatisticUnit.Miles).Value, 0.5)

    def test_unitconv_distance_metric(self):
        stat = ActivityStatistic(ActivityStatisticUnit.Kilometers, value=1)
        self.assertEqual(stat.asUnits(ActivityStatisticUnit.Meters).Value, 1000)

        stat = ActivityStatistic(ActivityStatisticUnit.Meters, value=250)
        self.assertEqual(stat.asUnits(ActivityStatisticUnit.Kilometers).Value, 0.25)

    def test_unitconv_distance_cross(self):
        stat = ActivityStatistic(ActivityStatisticUnit.Kilometers, value=1)
        self.assertAlmostEqual(stat.asUnits(ActivityStatisticUnit.Miles).Value, 0.6214, places=4)

        stat = ActivityStatistic(ActivityStatisticUnit.Miles, value=1)
        self.assertAlmostEqual(stat.asUnits(ActivityStatisticUnit.Kilometers).Value, 1.609, places=3)

        stat = ActivityStatistic(ActivityStatisticUnit.Miles, value=1)
        self.assertAlmostEqual(stat.asUnits(ActivityStatisticUnit.Meters).Value, 1609, places=0)

    def test_unitconv_velocity_metric(self):
        stat = ActivityStatistic(ActivityStatisticUnit.MetersPerSecond, value=100)
        self.assertEqual(stat.asUnits(ActivityStatisticUnit.KilometersPerHour).Value, 360)

        stat = ActivityStatistic(ActivityStatisticUnit.KilometersPerHour, value=50)
        self.assertAlmostEqual(stat.asUnits(ActivityStatisticUnit.MetersPerSecond).Value, 13.89, places=2)

    def test_unitconv_velocity_cross(self):
        stat = ActivityStatistic(ActivityStatisticUnit.KilometersPerHour, value=100)
        self.assertAlmostEqual(stat.asUnits(ActivityStatisticUnit.MilesPerHour).Value, 62, places=0)

        stat = ActivityStatistic(ActivityStatisticUnit.MilesPerHour, value=60)
        self.assertAlmostEqual(stat.asUnits(ActivityStatisticUnit.KilometersPerHour).Value, 96.5, places=0)

    def test_unitconv_impossible(self):
        stat = ActivityStatistic(ActivityStatisticUnit.KilometersPerHour, value=100)
        self.assertRaises(ValueError, stat.asUnits, ActivityStatisticUnit.Meters)

        stat = ActivityStatistic(ActivityStatisticUnit.DegreesCelcius, value=100)
        self.assertRaises(ValueError, stat.asUnits, ActivityStatisticUnit.Miles)

    def test_unitconv_noop(self):
        stat = ActivityStatistic(ActivityStatisticUnit.KilometersPerHour, value=100)
        self.assertEqual(stat.asUnits(ActivityStatisticUnit.KilometersPerHour).Value, 100)

    def test_stat_coalesce(self):
        stat1 = ActivityStatistic(ActivityStatisticUnit.Meters, value=1)
        stat2 = ActivityStatistic(ActivityStatisticUnit.Meters, value=2)
        stat1.coalesceWith(stat2)
        self.assertEqual(stat1.Value, 1.5)

    def test_stat_coalesce_missing(self):
        stat1 = ActivityStatistic(ActivityStatisticUnit.Meters, value=None)
        stat2 = ActivityStatistic(ActivityStatisticUnit.Meters, value=2)
        stat1.coalesceWith(stat2)
        self.assertEqual(stat1.Value, 2)

        stat1 = ActivityStatistic(ActivityStatisticUnit.Meters, value=1)
        stat2 = ActivityStatistic(ActivityStatisticUnit.Meters, value=None)
        stat1.coalesceWith(stat2)
        self.assertEqual(stat1.Value, 1)

    def test_stat_coalesce_multi(self):
        stat1 = ActivityStatistic(ActivityStatisticUnit.Meters, value=1)
        stat2 = ActivityStatistic(ActivityStatisticUnit.Meters, value=2)
        stat3 = ActivityStatistic(ActivityStatisticUnit.Meters, value=3)
        stat4 = ActivityStatistic(ActivityStatisticUnit.Meters, value=4)
        stat5 = ActivityStatistic(ActivityStatisticUnit.Meters, value=5)
        stat1.coalesceWith(stat2)
        stat1.coalesceWith(stat3)
        stat1.coalesceWith(stat4)
        stat1.coalesceWith(stat5)
        self.assertEqual(stat1.Value, 3)

    def test_stat_coalesce_multi_mixed(self):
        stat1 = ActivityStatistic(ActivityStatisticUnit.Meters, value=1)
        stat2 = ActivityStatistic(ActivityStatisticUnit.Meters, value=2)
        stat3 = ActivityStatistic(ActivityStatisticUnit.Meters, value=3)
        stat4 = ActivityStatistic(ActivityStatisticUnit.Meters, value=4)
        stat5 = ActivityStatistic(ActivityStatisticUnit.Meters, value=5)
        stat5.coalesceWith(stat2)
        stat5.coalesceWith(stat3)
        stat1.coalesceWith(stat5)
        stat1.coalesceWith(stat4)

        self.assertEqual(stat1.Value, 3)

    def test_stat_coalesce_multi_mixed2(self):
        stat1 = ActivityStatistic(ActivityStatisticUnit.Meters, value=1)
        stat2 = ActivityStatistic(ActivityStatisticUnit.Meters, value=2)
        stat3 = ActivityStatistic(ActivityStatisticUnit.Meters, value=3)
        stat4 = ActivityStatistic(ActivityStatisticUnit.Meters, value=4)
        stat5 = ActivityStatistic(ActivityStatisticUnit.Meters, value=5)
        stat5.coalesceWith(stat2)
        stat3.coalesceWith(stat5)
        stat4.coalesceWith(stat3)
        stat1.coalesceWith(stat4)

        self.assertEqual(stat1.Value, 3)

    def test_stat_coalesce_multi_missingmixed(self):
        stat1 = ActivityStatistic(ActivityStatisticUnit.Meters, value=1)
        stat2 = ActivityStatistic(ActivityStatisticUnit.Meters, value=2)
        stat3 = ActivityStatistic(ActivityStatisticUnit.Meters, value=None)
        stat4 = ActivityStatistic(ActivityStatisticUnit.Meters, value=None)
        stat5 = ActivityStatistic(ActivityStatisticUnit.Meters, value=5)
        stat5.coalesceWith(stat2)
        stat3.coalesceWith(stat5)
        stat4.coalesceWith(stat3)
        stat1.coalesceWith(stat4)

        self.assertAlmostEqual(stat1.Value, 8/3)

    def test_stat_coalesce_multi_missingmixed_multivalued(self):
        stat1 = ActivityStatistic(ActivityStatisticUnit.Meters, value=None, min=None)
        stat2 = ActivityStatistic(ActivityStatisticUnit.Meters, value=2, max=2)
        stat3 = ActivityStatistic(ActivityStatisticUnit.Meters, value=None, gain=3)
        stat4 = ActivityStatistic(ActivityStatisticUnit.Meters, value=None, loss=4)
        stat5 = ActivityStatistic(ActivityStatisticUnit.Meters, value=5, min=3)
        stat5.coalesceWith(stat2)
        stat3.coalesceWith(stat5)
        stat4.coalesceWith(stat3)
        stat1.coalesceWith(stat4)

        self.assertAlmostEqual(stat1.Value, 7/2)
        self.assertEqual(stat1.Min, 3)
        self.assertEqual(stat1.Max, 2)
        self.assertEqual(stat1.Gain, 3)
        self.assertEqual(stat1.Loss, 4)
########NEW FILE########
__FILENAME__ = sync
from tapiriik.testing.testtools import TestTools, TapiriikTestCase

from tapiriik.sync import Sync
from tapiriik.services import Service
from tapiriik.services.api import APIExcludeActivity
from tapiriik.services.interchange import Activity, ActivityType
from tapiriik.auth import User

from datetime import datetime, timedelta, tzinfo
import random
import pytz
import copy


class UTC(tzinfo):
    """UTC"""

    def utcoffset(self, dt):
        return timedelta(0)

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return timedelta(0)


class SyncTests(TapiriikTestCase):

    def test_svc_level_dupe(self):
        ''' check that service-level duplicate activities are caught (no DB involvement) '''

        svcA, svcB = TestTools.create_mock_services()
        recA = TestTools.create_mock_svc_record(svcA)
        recB = TestTools.create_mock_svc_record(svcB)

        actA = Activity()
        actA.StartTime = datetime(1, 2, 3, 4, 5, 6, 7)
        actA.ServiceDataCollection = TestTools.create_mock_servicedatacollection(svcA, record=recA)
        actB = Activity()
        actB.StartTime = actA.StartTime
        actB.ServiceDataCollection = TestTools.create_mock_servicedatacollection(svcB, record=recB)

        actA.CalculateUID()
        actB.CalculateUID()

        activities = []



        Sync._accumulateActivities(recA, [actA], activities)
        Sync._accumulateActivities(recB, [actB], activities)

        self.assertEqual(len(activities), 1)

    def test_svc_level_dupe_tz_uniform(self):
        ''' check that service-level duplicate activities with the same TZs are caught '''
        svcA, svcB = TestTools.create_mock_services()
        recA = TestTools.create_mock_svc_record(svcA)
        recB = TestTools.create_mock_svc_record(svcB)
        actA = Activity()
        actA.StartTime = pytz.timezone("America/Denver").localize(datetime(1, 2, 3, 4, 5, 6, 7))
        actA.ServiceDataCollection = TestTools.create_mock_servicedatacollection(svcA, record=recA)
        actB = Activity()
        actB.StartTime = actA.StartTime
        actB.ServiceDataCollection = TestTools.create_mock_servicedatacollection(svcB, record=recB)

        actA.CalculateUID()
        actB.CalculateUID()

        activities = []
        Sync._accumulateActivities(recA, [actA], activities)
        Sync._accumulateActivities(recB, [actB], activities)

        self.assertEqual(len(activities), 1)

    def test_svc_level_dupe_tz_nonuniform(self):
        ''' check that service-level duplicate activities with non-uniform TZs are caught '''
        svcA, svcB = TestTools.create_mock_services()
        recA = TestTools.create_mock_svc_record(svcA)
        recB = TestTools.create_mock_svc_record(svcB)
        actA = Activity()
        actA.StartTime = datetime(1, 2, 3, 4, 5, 6, 7)
        actA.ServiceDataCollection = TestTools.create_mock_servicedatacollection(svcA, record=recA)
        actB = Activity()
        actB.StartTime = pytz.timezone("America/Denver").localize(actA.StartTime)
        actB.ServiceDataCollection = TestTools.create_mock_servicedatacollection(svcB, record=recB)

        actA.CalculateUID()
        actB.CalculateUID()

        activities = []
        Sync._accumulateActivities(recA, [actA], activities)
        Sync._accumulateActivities(recB, [actB], activities)

        self.assertEqual(len(activities), 1)

    def test_svc_level_dupe_tz_irregular(self):
        ''' check that service-level duplicate activities with irregular TZs are caught '''
        svcA, svcB = TestTools.create_mock_services()
        recA = TestTools.create_mock_svc_record(svcA)
        recB = TestTools.create_mock_svc_record(svcB)
        actA = Activity()
        actA.StartTime = pytz.timezone("America/Edmonton").localize(datetime(1, 2, 3, 4, 5, 6, 7))
        actA.ServiceDataCollection = TestTools.create_mock_servicedatacollection(svcA, record=recA)
        actB = Activity()
        actB.StartTime = actA.StartTime.astimezone(pytz.timezone("America/Iqaluit"))
        actB.ServiceDataCollection = TestTools.create_mock_servicedatacollection(svcB, record=recB)

        actA.CalculateUID()
        actB.CalculateUID()

        activities = []
        Sync._accumulateActivities(recA, [actA], activities)
        Sync._accumulateActivities(recB, [actB], activities)

        self.assertEqual(len(activities), 1)

    def test_svc_level_dupe_time_leeway(self):
        ''' check that service-level duplicate activities within the defined time leeway are caught '''
        svcA, svcB = TestTools.create_mock_services()
        recA = TestTools.create_mock_svc_record(svcA)
        recB = TestTools.create_mock_svc_record(svcB)
        actA = Activity()
        actA.StartTime = datetime(1, 2, 3, 4, 5, 6, 7)
        actA.ServiceDataCollection = TestTools.create_mock_servicedatacollection(svcA, record=recA)
        actA.Type = set(svcA.SupportedActivities).intersection(set(svcB.SupportedActivities)).pop()
        actB = Activity()
        actB.StartTime = datetime(1, 2, 3, 4, 6, 6, 7)
        actB.ServiceDataCollection = TestTools.create_mock_servicedatacollection(svcB, record=recB)
        actB.Type = actA.Type

        actA.CalculateUID()
        actB.CalculateUID()

        activities = []
        Sync._accumulateActivities(recA, [actA], activities)
        Sync._accumulateActivities(recB, [actB], activities)

        self.assertIn(actA.UID, actA.UIDs)
        self.assertIn(actB.UID, actA.UIDs)
        self.assertIn(actA.UID, actB.UIDs)
        self.assertIn(actB.UID, actB.UIDs)

        # we need to fake up the service records to avoid having to call the actual sync method where these values are normally preset
        recA = TestTools.create_mock_svc_record(svcA)
        recB = TestTools.create_mock_svc_record(svcB)
        recA.SynchronizedActivities = [actA.UID]
        recB.SynchronizedActivities = [actB.UID]

        recipientServicesA = Sync._determineRecipientServices(actA, [recA, recB])
        recipientServicesB = Sync._determineRecipientServices(actB, [recA, recB])

        self.assertEqual(len(recipientServicesA), 0)
        self.assertEqual(len(recipientServicesB), 0)
        self.assertEqual(len(activities), 1)

    def test_svc_supported_activity_types(self):
        ''' check that only activities are only sent to services which support them '''
        svcA, svcB = TestTools.create_mock_services()
        recA = TestTools.create_mock_svc_record(svcA)
        recB = TestTools.create_mock_svc_record(svcB)
        svcA.SupportedActivities = [ActivityType.CrossCountrySkiing]
        svcB.SupportedActivities = [ActivityType.Cycling]

        actA = Activity()
        actA.StartTime = datetime(1, 2, 3, 4, 5, 6, 7)
        actA.ServiceDataCollection = TestTools.create_mock_servicedatacollection(svcA, record=recA)
        actA.Type = svcA.SupportedActivities[0]
        actB = Activity()
        actB.StartTime = datetime(5, 6, 7, 8, 9, 10, 11)
        actB.ServiceDataCollection = TestTools.create_mock_servicedatacollection(svcB, record=recB)
        actB.Type = [x for x in svcB.SupportedActivities if x != actA.Type][0]

        actA.CalculateUID()
        actB.CalculateUID()

        allConns = [recA, recB]

        activities = []
        Sync._accumulateActivities(recA, [actA], activities)
        Sync._accumulateActivities(recB, [actB], activities)

        syncToA = Sync._determineRecipientServices(actA, allConns)
        syncToB = Sync._determineRecipientServices(actB, allConns)

        self.assertEqual(len(syncToA), 0)
        self.assertEqual(len(syncToB), 0)

        svcB.SupportedActivities = svcA.SupportedActivities

        syncToA = Sync._determineRecipientServices(actA, allConns)
        syncToB = Sync._determineRecipientServices(actB, allConns)

        self.assertEqual(len(syncToA), 1)
        self.assertEqual(len(syncToB), 0)

        svcB.SupportedActivities = svcA.SupportedActivities = [ActivityType.CrossCountrySkiing, ActivityType.Cycling]

        syncToA = Sync._determineRecipientServices(actA, allConns)
        syncToB = Sync._determineRecipientServices(actB, allConns)

        self.assertEqual(len(syncToA), 1)
        self.assertEqual(len(syncToB), 1)

    def test_accumulate_exclusions(self):
        svcA, svcB = TestTools.create_mock_services()
        recA = TestTools.create_mock_svc_record(svcA)

        exclusionstore = {recA._id: {}}
        # regular
        exc = APIExcludeActivity("Messag!e", activityId=3.14)
        Sync._accumulateExclusions(recA, exc, exclusionstore)
        self.assertTrue("3_14" in exclusionstore[recA._id])
        self.assertEqual(exclusionstore[recA._id]["3_14"]["Message"], "Messag!e")
        self.assertEqual(exclusionstore[recA._id]["3_14"]["Activity"], None)
        self.assertEqual(exclusionstore[recA._id]["3_14"]["ExternalActivityID"], 3.14)
        self.assertEqual(exclusionstore[recA._id]["3_14"]["Permanent"], True)

        # updating
        act = TestTools.create_blank_activity(svcA)
        act.UID = "3_14"  # meh
        exc = APIExcludeActivity("Messag!e2", activityId=42, permanent=False, activity=act)
        Sync._accumulateExclusions(recA, exc, exclusionstore)
        self.assertTrue("3_14" in exclusionstore[recA._id])
        self.assertEqual(exclusionstore[recA._id]["3_14"]["Message"], "Messag!e2")
        self.assertNotEqual(exclusionstore[recA._id]["3_14"]["Activity"], None)  # Who knows what the string format will be down the road?
        self.assertEqual(exclusionstore[recA._id]["3_14"]["ExternalActivityID"], 42)
        self.assertEqual(exclusionstore[recA._id]["3_14"]["Permanent"], False)

        # multiple, retaining existing
        exc2 = APIExcludeActivity("INM", activityId=13)
        exc3 = APIExcludeActivity("FNIM", activityId=37)
        Sync._accumulateExclusions(recA, [exc2, exc3], exclusionstore)
        self.assertTrue("3_14" in exclusionstore[recA._id])
        self.assertTrue("37" in exclusionstore[recA._id])
        self.assertTrue("13" in exclusionstore[recA._id])

        # don't allow with no identifiers
        exc4 = APIExcludeActivity("nooooo")
        self.assertRaises(ValueError, Sync._accumulateExclusions, recA, [exc4], exclusionstore)

    def test_activity_deduplicate_normaltz(self):
        ''' ensure that we can't deduplicate activities with non-pytz timezones '''
        svcA, svcB = TestTools.create_mock_services()
        recA = TestTools.create_mock_svc_record(svcA)
        recB = TestTools.create_mock_svc_record(svcB)
        actA = TestTools.create_random_activity(svcA, tz=UTC())

        actB = Activity()
        actB.StartTime = actA.StartTime.replace(tzinfo=None) + timedelta(seconds=10)
        actB.EndTime = actA.EndTime.replace(tzinfo=None)
        actB.ServiceDataCollection = TestTools.create_mock_servicedatacollection(svcB, record=recB)
        actA.Name = "Not this"
        actB.Name = "Heya"
        actB.Type = ActivityType.Walking
        actA.CalculateUID()
        actB.CalculateUID()

        activities = []
        Sync._accumulateActivities(recB, [copy.deepcopy(actB)], activities)
        self.assertRaises(ValueError, Sync._accumulateActivities, recA, [copy.deepcopy(actA)], activities)

    def test_activity_deduplicate_tzerror(self):
        ''' Test that probably-duplicate activities with starttimes like 09:12:22 and 15:12:22 (on the same day) are recognized as one '''
        svcA, svcB = TestTools.create_mock_services()
        recA = TestTools.create_mock_svc_record(svcA)
        recB = TestTools.create_mock_svc_record(svcB)
        actA = TestTools.create_random_activity(svcA, tz=pytz.timezone("America/Iqaluit"))
        actB = Activity()
        actB.StartTime = actA.StartTime.replace(tzinfo=pytz.timezone("America/Denver")) + timedelta(hours=5)
        actB.ServiceDataCollection = TestTools.create_mock_servicedatacollection(svcB)
        actA.Name = "Not this"
        actB.Name = "Heya"
        actB.Type = ActivityType.Walking
        actA.CalculateUID()
        actB.CalculateUID()

        activities = []
        Sync._accumulateActivities(recB, [copy.deepcopy(actB)], activities)
        Sync._accumulateActivities(recA, [copy.deepcopy(actA)], activities)

        self.assertEqual(len(activities), 1)

        # Ensure that it is an exact match
        actB.StartTime = actA.StartTime.replace(tzinfo=pytz.timezone("America/Denver")) + timedelta(hours=5, seconds=1)
        activities = []
        Sync._accumulateActivities(recB, [copy.deepcopy(actB)], activities)
        Sync._accumulateActivities(recA, [copy.deepcopy(actA)], activities)

        self.assertEqual(len(activities), 2)

        # Ensure that overly large differences >38hr - not possible via TZ differences & shamefully bad import/export code on the part of some services - are not deduplicated
        actB.StartTime = actA.StartTime.replace(tzinfo=pytz.timezone("America/Denver")) + timedelta(hours=50)
        activities = []
        Sync._accumulateActivities(recB, [copy.deepcopy(actB)], activities)
        Sync._accumulateActivities(recA, [copy.deepcopy(actA)], activities)

        self.assertEqual(len(activities), 2)

    def test_activity_coalesce(self):
        ''' ensure that activity data is getting coalesced by _accumulateActivities '''
        svcA, svcB = TestTools.create_mock_services()
        recA = TestTools.create_mock_svc_record(svcA)
        recB = TestTools.create_mock_svc_record(svcB)
        actA = TestTools.create_random_activity(svcA, tz=pytz.timezone("America/Iqaluit"))
        actB = Activity()
        actB.StartTime = actA.StartTime.replace(tzinfo=None)
        actB.ServiceDataCollection = TestTools.create_mock_servicedatacollection(svcB)
        actA.Name = "Not this"
        actA.Private = True
        actB.Name = "Heya"
        actB.Type = ActivityType.Walking
        actA.CalculateUID()
        actB.CalculateUID()

        activities = []
        Sync._accumulateActivities(recB, [copy.deepcopy(actB)], activities)
        Sync._accumulateActivities(recA, [copy.deepcopy(actA)], activities)

        self.assertEqual(len(activities), 1)
        act = activities[0]

        self.assertEqual(act.StartTime, actA.StartTime)
        self.assertEqual(act.EndTime, actA.EndTime)
        self.assertEqual(act.EndTime.tzinfo, actA.StartTime.tzinfo)
        self.assertEqual(act.StartTime.tzinfo, actA.StartTime.tzinfo)
        self.assertEqual(act.Waypoints, actA.Waypoints)
        self.assertTrue(act.Private)  # Most restrictive setting
        self.assertEqual(act.Name, actB.Name)  # The first activity takes priority.
        self.assertEqual(act.Type, actB.Type)  # Same here.
        self.assertTrue(list(actB.ServiceDataCollection.keys())[0] in act.ServiceDataCollection)
        self.assertTrue(list(actA.ServiceDataCollection.keys())[0] in act.ServiceDataCollection)

        activities = []
        Sync._accumulateActivities(recA, [copy.deepcopy(actA)], activities)
        Sync._accumulateActivities(recB, [copy.deepcopy(actB)], activities)

        self.assertEqual(len(activities), 1)
        act = activities[0]

        self.assertEqual(act.StartTime, actA.StartTime)
        self.assertEqual(act.EndTime, actA.EndTime)
        self.assertEqual(act.EndTime.tzinfo, actA.StartTime.tzinfo)
        self.assertEqual(act.StartTime.tzinfo, actA.StartTime.tzinfo)
        self.assertEqual(act.Waypoints, actA.Waypoints)
        self.assertEqual(act.Name, actA.Name)  # The first activity takes priority.
        self.assertEqual(act.Type, actB.Type)  # Exception: ActivityType.Other does not take priority
        self.assertTrue(list(actB.ServiceDataCollection.keys())[0] in act.ServiceDataCollection)
        self.assertTrue(list(actA.ServiceDataCollection.keys())[0] in act.ServiceDataCollection)

        actA.Type = ActivityType.CrossCountrySkiing
        activities = []
        Sync._accumulateActivities(recA, [copy.deepcopy(actA)], activities)
        Sync._accumulateActivities(recB, [copy.deepcopy(actB)], activities)

        self.assertEqual(len(activities), 1)
        act = activities[0]
        self.assertEqual(act.Type, actA.Type)  # Here, it will take priority.



    def test_eligibility_excluded(self):
        user = TestTools.create_mock_user()
        svcA, svcB = TestTools.create_mock_services()
        recA = TestTools.create_mock_svc_record(svcA)
        recB = TestTools.create_mock_svc_record(svcB)
        act = TestTools.create_blank_activity(svcA, record=recB)
        recipientServices = [recA, recB]
        excludedServices = [recA]
        eligible = Sync._determineEligibleRecipientServices(activity=act, connectedServices=recipientServices, recipientServices=recipientServices, excludedServices=excludedServices, user=user)
        self.assertTrue(recB in eligible)
        self.assertTrue(recA not in eligible)

    def test_eligibility_config(self):
        user = TestTools.create_mock_user()
        svcA, svcB = TestTools.create_mock_services()
        svcA.Configurable = True
        svcA.RequiresConfiguration = lambda x: True
        recA = TestTools.create_mock_svc_record(svcA)
        recB = TestTools.create_mock_svc_record(svcB)
        act = TestTools.create_blank_activity(svcA, record=recB)
        recipientServices = [recA, recB]
        excludedServices = []
        eligible = Sync._determineEligibleRecipientServices(activity=act, connectedServices=recipientServices, recipientServices=recipientServices, excludedServices=excludedServices, user=user)
        self.assertTrue(recB in eligible)
        self.assertTrue(recA not in eligible)

    def test_eligibility_flowexception(self):
        user = TestTools.create_mock_user()
        svcA, svcB = TestTools.create_mock_services()
        recA = TestTools.create_mock_svc_record(svcA)
        recB = TestTools.create_mock_svc_record(svcB)
        act = TestTools.create_blank_activity(svcA, record=recA)
        act.Origin = recA
        User.SetFlowException(user, recA, recB, flowToTarget=False)
        recipientServices = [recA, recB]
        excludedServices = []
        eligible = Sync._determineEligibleRecipientServices(activity=act, connectedServices=recipientServices, recipientServices=recipientServices, excludedServices=excludedServices, user=user)
        self.assertTrue(recA in eligible)
        self.assertFalse(recB in eligible)

    def test_eligibility_flowexception_shortcircuit(self):
        user = TestTools.create_mock_user()
        svcA, svcB = TestTools.create_mock_services()
        svcC = TestTools.create_mock_service("mockC")
        recA = TestTools.create_mock_svc_record(svcA)
        recB = TestTools.create_mock_svc_record(svcB)
        recC = TestTools.create_mock_svc_record(svcC)
        act = TestTools.create_blank_activity(svcA, record=recA)
        User.SetFlowException(user, recA, recC, flowToTarget=False)

        # Behaviour with known origin and no override set
        act.Origin = recA
        recipientServices = [recC, recB]
        excludedServices = []
        eligible = Sync._determineEligibleRecipientServices(activity=act, connectedServices=[recA, recB, recC], recipientServices=recipientServices, excludedServices=excludedServices, user=user)
        self.assertTrue(recA not in eligible)
        self.assertTrue(recB in eligible)
        self.assertTrue(recC not in eligible)

        # Enable alternate routing
        recB.SetConfiguration({"allow_activity_flow_exception_bypass_via_self":True}, no_save=True)
        self.assertTrue(recB.GetConfiguration()["allow_activity_flow_exception_bypass_via_self"])
        # We should now be able to arrive at recC via recB
        act.Origin = recA
        recipientServices = [recC, recB]
        excludedServices = []
        eligible = Sync._determineEligibleRecipientServices(activity=act, connectedServices=[recA, recB, recC], recipientServices=recipientServices, excludedServices=excludedServices, user=user)
        self.assertTrue(recA not in eligible)
        self.assertTrue(recB in eligible)
        self.assertTrue(recC in eligible)

    def test_eligibility_flowexception_reverse(self):
        user = TestTools.create_mock_user()
        svcA, svcB = TestTools.create_mock_services()
        recA = TestTools.create_mock_svc_record(svcA)
        recB = TestTools.create_mock_svc_record(svcB)
        act = TestTools.create_blank_activity(svcA, record=recB)
        act.Origin = recB
        User.SetFlowException(user, recA, recB, flowToSource=False)
        recipientServices = [recA, recB]
        excludedServices = []
        eligible = Sync._determineEligibleRecipientServices(activity=act, connectedServices=recipientServices, recipientServices=recipientServices, excludedServices=excludedServices, user=user)
        self.assertFalse(recA in eligible)
        self.assertTrue(recB in eligible)

    def test_eligibility_flowexception_both(self):
        user = TestTools.create_mock_user()
        svcA, svcB = TestTools.create_mock_services()
        recA = TestTools.create_mock_svc_record(svcA)
        recB = TestTools.create_mock_svc_record(svcB)
        act = TestTools.create_blank_activity(svcA, record=recB)
        act.Origin = recB
        User.SetFlowException(user, recA, recB, flowToSource=False, flowToTarget=False)
        recipientServices = [recA, recB]
        excludedServices = []
        eligible = Sync._determineEligibleRecipientServices(activity=act, connectedServices=recipientServices, recipientServices=recipientServices, excludedServices=excludedServices, user=user)
        self.assertFalse(recA in eligible)
        self.assertTrue(recB in eligible)

        act.Origin = recA
        act.ServiceDataCollection = TestTools.create_mock_servicedatacollection(svcA, record=recA)
        eligible = Sync._determineEligibleRecipientServices(activity=act, connectedServices=recipientServices, recipientServices=recipientServices, excludedServices=excludedServices, user=user)
        self.assertTrue(recA in eligible)
        self.assertFalse(recB in eligible)

    def test_eligibility_flowexception_none(self):
        user = TestTools.create_mock_user()
        svcA, svcB = TestTools.create_mock_services()
        recA = TestTools.create_mock_svc_record(svcA)
        recB = TestTools.create_mock_svc_record(svcB)
        act = TestTools.create_blank_activity(svcA, record=recB)
        act.Origin = recB
        User.SetFlowException(user, recA, recB, flowToSource=False, flowToTarget=False)
        recipientServices = [recA]
        excludedServices = []
        eligible = Sync._determineEligibleRecipientServices(activity=act, connectedServices=[recA, recB], recipientServices=recipientServices, excludedServices=excludedServices, user=user)
        self.assertTrue(recA not in eligible)
        self.assertTrue(recB not in eligible)

        recipientServices = [recB]
        act.Origin = recA
        act.ServiceDataCollection = TestTools.create_mock_servicedatacollection(svcA, record=recA)
        eligible = Sync._determineEligibleRecipientServices(activity=act, connectedServices=[recA, recB], recipientServices=recipientServices, excludedServices=excludedServices, user=user)
        self.assertTrue(recA not in eligible)
        self.assertTrue(recB not in eligible)

    def test_eligibility_flowexception_change(self):
        user = TestTools.create_mock_user()
        svcA, svcB = TestTools.create_mock_services()
        recA = TestTools.create_mock_svc_record(svcA)
        recB = TestTools.create_mock_svc_record(svcB)
        act = TestTools.create_blank_activity(svcA, record=recB)
        act.Origin = recB

        recipientServices = [recA]
        excludedServices = []


        User.SetFlowException(user, recA, recB, flowToSource=False, flowToTarget=True)
        eligible = Sync._determineEligibleRecipientServices(activity=act, connectedServices=[recA, recB], recipientServices=recipientServices, excludedServices=excludedServices, user=user)
        self.assertTrue(recA not in eligible)
        self.assertTrue(recB not in eligible)

        recipientServices = [recB]
        act.Origin = recA
        act.ServiceDataCollection = TestTools.create_mock_servicedatacollection(svcA, record=recA)
        User.SetFlowException(user, recA, recB, flowToSource=True, flowToTarget=False)
        eligible = Sync._determineEligibleRecipientServices(activity=act, connectedServices=[recA, recB], recipientServices=recipientServices, excludedServices=excludedServices, user=user)
        self.assertTrue(recA not in eligible)
        self.assertTrue(recB not in eligible)

        User.SetFlowException(user, recA, recB, flowToSource=False, flowToTarget=False)
        eligible = Sync._determineEligibleRecipientServices(activity=act, connectedServices=[recA, recB], recipientServices=recipientServices, excludedServices=excludedServices, user=user)
        self.assertTrue(recA not in eligible)
        self.assertTrue(recB not in eligible)

        recipientServices = [recA, recB]
        User.SetFlowException(user, recA, recB, flowToSource=True, flowToTarget=True)
        eligible = Sync._determineEligibleRecipientServices(activity=act, connectedServices=[recA, recB], recipientServices=recipientServices, excludedServices=excludedServices, user=user)
        self.assertTrue(recA in eligible)
        self.assertTrue(recB in eligible)

        eligible = Sync._determineEligibleRecipientServices(activity=act, connectedServices=[recA, recB], recipientServices=recipientServices, excludedServices=excludedServices, user=user)
        self.assertTrue(recA in eligible)
        self.assertTrue(recB in eligible)
########NEW FILE########
__FILENAME__ = testtools
from unittest import TestCase

from tapiriik.services import Service, ServiceRecord, ServiceBase
from tapiriik.services.interchange import Activity, ActivityType, ActivityStatistic, ActivityStatisticUnit, Waypoint, WaypointType, Location

from datetime import datetime, timedelta
import random
import pytz
from tapiriik.database import db


class MockServiceA(ServiceBase):
    ID = "mockA"
    SupportedActivities = [ActivityType.Rowing]


class MockServiceB(ServiceBase):
    ID = "mockB"
    SupportedActivities = [ActivityType.Rowing, ActivityType.Wheelchair]


class TapiriikTestCase(TestCase):
    def assertActivitiesEqual(self, a, b):
        ''' compare activity records with more granular asserts '''
        if a == b:
            return
        else:
            self.assertEqual(a.StartTime, b.StartTime)
            self.assertEqual(a.EndTime, b.EndTime)
            self.assertEqual(a.Type, b.Type)
            self.assertEqual(a.Stats.Distance, b.Stats.Distance)
            self.assertEqual(a.Name, b.Name)
            self.assertEqual(len(a.Waypoints), len(b.Waypoints))
            for idx in range(0, len(a.Waypoints) - 1):
                self.assertEqual(a.Waypoints[idx].Timestamp.astimezone(pytz.utc), b.Waypoints[idx].Timestamp.astimezone(pytz.utc))
                self.assertEqual(a.Waypoints[idx].Location.Latitude, b.Waypoints[idx].Location.Latitude)
                self.assertEqual(a.Waypoints[idx].Location.Longitude, b.Waypoints[idx].Location.Longitude)
                self.assertEqual(a.Waypoints[idx].Location.Altitude, b.Waypoints[idx].Location.Altitude)
                self.assertEqual(a.Waypoints[idx].Type, b.Waypoints[idx].Type)
                self.assertEqual(a.Waypoints[idx].HR, b.Waypoints[idx].HR)
                self.assertEqual(a.Waypoints[idx].Calories, b.Waypoints[idx].Calories)
                self.assertEqual(a.Waypoints[idx].Power, b.Waypoints[idx].Power)
                self.assertEqual(a.Waypoints[idx].Cadence, b.Waypoints[idx].Cadence)
                self.assertEqual(a.Waypoints[idx].Temp, b.Waypoints[idx].Temp)

                self.assertEqual(a.Waypoints[idx].Location, b.Waypoints[idx].Location)
                self.assertEqual(a.Waypoints[idx], b.Waypoints[idx])
            self.assertEqual(a, b)


class TestTools:
    def create_mock_user():
        db.test.insert({"asd":"asdd"})
        return {"_id": str(random.randint(1, 1000))}

    def create_mock_svc_record(svc):
        return ServiceRecord({"Service": svc.ID, "_id": str(random.randint(1, 1000)), "ExternalID": str(random.randint(1,1000))})

    def create_mock_servicedata(svc, record=None):
        return {"ActivityID": random.randint(1, 1000), "Connection": record}

    def create_mock_servicedatacollection(svc, record=None):
        record = record if record else TestTools.create_mock_svc_record(svc)
        return {record._id: TestTools.create_mock_servicedata(svc, record=record)}

    def create_blank_activity(svc=None, actType=ActivityType.Other, record=None):
        act = Activity()
        act.Type = actType
        if svc:
            record = record if record else TestTools.create_mock_svc_record(svc)
            act.ServiceDataCollection = TestTools.create_mock_servicedatacollection(svc, record=record)
        act.StartTime = datetime.now()
        act.EndTime = act.StartTime + timedelta(seconds=42)
        act.CalculateUID()
        return act

    def create_random_activity(svc=None, actType=ActivityType.Other, tz=False, record=None):
        ''' creates completely random activity with valid waypoints and data '''
        act = TestTools.create_blank_activity(svc, actType, record=record)

        if tz is True:
            tz = pytz.timezone(pytz.all_timezones[random.randint(0, len(pytz.all_timezones) - 1)])
            act.TZ = tz
        elif tz is not False:
            act.TZ = tz

        if len(act.Waypoints) > 0:
            raise ValueError("Waypoint list already populated")
        # this is entirely random in case the testing account already has events in it (API doesn't support delete, etc)
        act.StartTime = datetime(random.randint(2000, 2020), random.randint(1, 12), random.randint(1, 28), random.randint(0, 23), random.randint(0, 59), random.randint(0, 59))
        if tz is not False:
            if hasattr(tz, "localize"):
                act.StartTime = tz.localize(act.StartTime)
            else:
                act.StartTime = act.StartTime.replace(tzinfo=tz)
        act.EndTime = act.StartTime + timedelta(0, random.randint(60 * 5, 60 * 60))  # don't really need to upload 1000s of pts to test this...
        act.Stats.Distance = ActivityStatistic(ActivityStatisticUnit.Meters, value=random.random() * 10000)
        act.Name = str(random.random())
        paused = False
        waypointTime = act.StartTime
        backToBackPauses = False
        while waypointTime < act.EndTime:
            wp = Waypoint()
            if waypointTime == act.StartTime:
                wp.Type = WaypointType.Start
            wp.Timestamp = waypointTime
            wp.Location = Location(random.random() * 180 - 90, random.random() * 180 - 90, random.random() * 1000)  # this is gonna be one intense activity

            if not (wp.HR == wp.Cadence == wp.Calories == wp.Power == wp.Temp == None):
                raise ValueError("Waypoint did not initialize cleanly")
            if svc.SupportsHR:
                wp.HR = float(random.randint(90, 180))
            if svc.SupportsPower:
                wp.Power = float(random.randint(0, 1000))
            if svc.SupportsCalories:
                wp.Calories = float(random.randint(0, 500))
            if svc.SupportsCadence:
                wp.Cadence = float(random.randint(0, 100))
            if svc.SupportsTemp:
                wp.Temp = float(random.randint(0, 100))

            if (random.randint(40, 50) == 42 or backToBackPauses) and not paused:  # pause quite often
                wp.Type = WaypointType.Pause
                paused = True

            elif paused:
                paused = False
                wp.Type = WaypointType.Resume
                backToBackPauses = not backToBackPauses

            waypointTime += timedelta(0, int(random.random() + 9.5))  # 10ish seconds

            if waypointTime > act.EndTime:
                wp.Timestamp = act.EndTime
                wp.Type = WaypointType.End
            act.Waypoints.append(wp)
        if len(act.Waypoints) == 0:
            raise ValueError("No waypoints populated")
        return act

    def create_mock_service(id):
        mock = MockServiceA()
        mock.ID = id
        Service._serviceMappings[id] = mock
        return mock

    def create_mock_services():
        mockA = MockServiceA()
        mockB = MockServiceB()
        Service._serviceMappings["mockA"] = mockA
        Service._serviceMappings["mockB"] = mockB
        return (mockA, mockB)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.generic import TemplateView

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', 'tapiriik.web.views.dashboard', name='dashboard'),

    url(r'^auth/redirect/(?P<service>[^/]+)$', 'tapiriik.web.views.oauth.authredirect', {}, name='oauth_redirect', ),
    url(r'^auth/redirect/(?P<service>[^/]+)/(?P<level>.+)$', 'tapiriik.web.views.oauth.authredirect', {}, name='oauth_redirect', ),
    url(r'^auth/return/(?P<service>[^/]+)$', 'tapiriik.web.views.oauth.authreturn', {}, name='oauth_return', ),
    url(r'^auth/return/(?P<service>[^/]+)/(?P<level>.+)$', 'tapiriik.web.views.oauth.authreturn', {}, name='oauth_return', ),  # django's URL magic couldn't handle the equivalent regex
    url(r'^auth/deauth/(?P<service>.+)$', 'tapiriik.web.views.oauth.deauth', {}, name='oauth_deauth', ),
    url(r'^auth/login/(?P<service>.+)$', 'tapiriik.web.views.auth_login', {}, name='auth_simple', ),
    url(r'^auth/login-ajax/(?P<service>.+)$', 'tapiriik.web.views.auth_login_ajax', {}, name='auth_simple_ajax', ),
    url(r'^auth/persist-ajax/(?P<service>.+)$', 'tapiriik.web.views.auth_persist_extended_auth_ajax', {}, name='auth_persist_extended_auth_ajax', ),
    url(r'^auth/disconnect/(?P<service>.+)$', 'tapiriik.web.views.auth_disconnect', {}, name='auth_disconnect', ),
    url(r'^auth/disconnect-ajax/(?P<service>.+)$', 'tapiriik.web.views.auth_disconnect_ajax', {}, name='auth_disconnect_ajax', ),
    url(r'^auth/logout$', 'tapiriik.web.views.auth_logout', {}, name='auth_logout', ),

    url(r'^account/setemail$', 'tapiriik.web.views.account_setemail', {}, name='account_set_email', ),
    url(r'^account/settz$', 'tapiriik.web.views.account_settimezone', {}, name='account_set_timezone', ),

    url(r'^configure/save/(?P<service>.+)?$', 'tapiriik.web.views.config.config_save', {}, name='config_save', ),
    url(r'^configure/dropbox$', 'tapiriik.web.views.config.dropbox', {}, name='dropbox_config', ),
    url(r'^configure/flow/save/(?P<service>.+)?$', 'tapiriik.web.views.config.config_flow_save', {}, name='config_flow_save', ),
    url(r'^settings/?$', 'tapiriik.web.views.settings.settings', {}, name='settings_panel', ),

    url(r'^dropbox/browse-ajax/?$', 'tapiriik.web.views.dropbox.browse', {}, name='dropbox_browse_ajax', ),
    url(r'^dropbox/browse-ajax/(?P<path>.+)?$', 'tapiriik.web.views.dropbox.browse', {}, name='dropbox_browse_ajax', ),

    url(r'^sync/status$', 'tapiriik.web.views.sync_status', {}, name='sync_status'),
    url(r'^sync/schedule/now$', 'tapiriik.web.views.sync_schedule_immediate', {}, name='sync_schedule_immediate'),
    url(r'^sync/errors/(?P<service>[^/]+)/clear/(?P<group>.+)$', 'tapiriik.web.views.sync_clear_errorgroup', {}, name='sync_clear_errorgroup'),

    url(r'^activities$', 'tapiriik.web.views.activities_dashboard', {}, name='activities_dashboard'),
    url(r'^activities/fetch$', 'tapiriik.web.views.activities_fetch_json', {}, name='activities_fetch_json'),

    url(r'^sync/remote_callback/trigger_partial_sync/(?P<service>.+)$', 'tapiriik.web.views.sync_trigger_partial_sync_callback', {}, name='sync_trigger_partial_sync_callback'),

    url(r'^diagnostics/$', 'tapiriik.web.views.diag_dashboard', {}, name='diagnostics_dashboard'),
    url(r'^diagnostics/user/unsu$', 'tapiriik.web.views.diag_unsu', {}, name='diagnostics_unsu'),
    url(r'^diagnostics/user/(?P<user>.+)$', 'tapiriik.web.views.diag_user', {}, name='diagnostics_user'),
    url(r'^diagnostics/payments/$', 'tapiriik.web.views.diag_payments', {}, name='diagnostics_payments'),
    url(r'^diagnostics/login$', 'tapiriik.web.views.diag_login', {}, name='diagnostics_login'),

    url(r'^supported-activities$', 'tapiriik.web.views.supported_activities', {}, name='supported_activities'),
    url(r'^supported-services-poll$', 'tapiriik.web.views.supported_services_poll', {}, name='supported_services_poll'),

    url(r'^payments/claim$', 'tapiriik.web.views.payments_claim', {}, name='payments_claim'),
    url(r'^payments/claim-ajax$', 'tapiriik.web.views.payments_claim_ajax', {}, name='payments_claim_ajax'),
    url(r'^payments/claim-wait-ajax$', 'tapiriik.web.views.payments_claim_wait_ajax', {}, name='payments_claim_wait_ajax'),
    url(r'^payments/claim/(?P<code>[a-f0-9]+)$', 'tapiriik.web.views.payments_claim_return', {}, name='payments_claim_return'),
    url(r'^payments/return$', 'tapiriik.web.views.payments_return', {}, name='payments_return'),
    url(r'^payments/ipn$', 'tapiriik.web.views.payments_ipn', {}, name='payments_ipn'),

    url(r'^ab/begin/(?P<key>[^/]+)$', 'tapiriik.web.views.ab_web_experiment_begin', {}, name='ab_web_experiment_begin'),

    url(r'^privacy$', 'tapiriik.web.views.privacy.privacy', name='privacy'),

    url(r'^trainingpeaks_premium$', 'tapiriik.web.views.trainingpeaks_premium.trainingpeaks_premium', name='trainingpeaks_premium'),

    url(r'^garmin_connect_users$', TemplateView.as_view(template_name='static/garmin_connect_users.html'), name='garmin_connect_users'),

    url(r'^faq$', TemplateView.as_view(template_name='static/faq.html'), name='faq'),
    url(r'^credits$', TemplateView.as_view(template_name='static/credits.html'), name='credits'),
    url(r'^contact$', TemplateView.as_view(template_name='static/contact.html'), name='contact'),
    # Examples:
    # url(r'^$', 'tapiriik.views.home', name='home'),
    # url(r'^tapiriik/', include('tapiriik.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
)

urlpatterns += staticfiles_urlpatterns()

########NEW FILE########
__FILENAME__ = context_processors
from tapiriik.services import Service
from tapiriik.auth import User
from tapiriik.sync import Sync
from tapiriik.settings import SITE_VER, PP_WEBSCR, PP_BUTTON_ID, SOFT_LAUNCH_SERVICES, DISABLED_SERVICES, WITHDRAWN_SERVICES
from tapiriik.database import db
import json


def providers(req):
    return {"service_providers": Service.List()}

def config(req):
    in_diagnostics = "diagnostics" in req.path
    return {"config": {"minimumSyncInterval": Sync.MinimumSyncInterval.seconds, "siteVer": SITE_VER, "pp": {"url": PP_WEBSCR, "buttonId": PP_BUTTON_ID}, "soft_launch": SOFT_LAUNCH_SERVICES, "disabled_services": DISABLED_SERVICES, "withdrawn_services": WITHDRAWN_SERVICES, "in_diagnostics": in_diagnostics}, "hidden_infotips": req.COOKIES.get("infotip_hide", None)}

def user(req):
    return {"user":req.user}

def js_bridge(req):
    serviceInfo = {}

    for svc in Service.List():
        if svc.ID in WITHDRAWN_SERVICES:
            continue
        if req.user is not None:
            svcRec = User.GetConnectionRecord(req.user, svc.ID)  # maybe make the auth handler do this only once?
        else:
            svcRec = None
        info = {
            "DisplayName": svc.DisplayName,
            "DisplayAbbreviation": svc.DisplayAbbreviation,
            "AuthenticationType": svc.AuthenticationType,
            "UsesExtendedAuth": svc.RequiresExtendedAuthorizationDetails,
            "AuthorizationURL": svc.UserAuthorizationURL,
            "NoFrame": svc.AuthenticationNoFrame,
            "Configurable": svc.Configurable,
            "RequiresConfiguration": False  # by default
        }
        if svcRec:
            if svc.Configurable:
                if svc.ID == "dropbox":  # dirty hack alert, but better than dumping the auth details in their entirety
                    info["AccessLevel"] = "full" if svcRec.Authorization["Full"] else "normal"
                    info["RequiresConfiguration"] = svc.RequiresConfiguration(svcRec)
            info["Config"] = svcRec.GetConfiguration()
            info["HasExtendedAuth"] = svcRec.HasExtendedAuthorizationDetails()
            info["PersistedExtendedAuth"] = svcRec.HasExtendedAuthorizationDetails(persisted_only=True)
            info["ExternalID"] = svcRec.ExternalID
        info["BlockFlowTo"] = []
        info["Connected"] = svcRec is not None
        serviceInfo[svc.ID] = info
    if req.user is not None:
        flowExc = User.GetFlowExceptions(req.user)
        for exc in flowExc:
            if exc["Source"]["Service"] not in serviceInfo or exc["Target"]["Service"] not in serviceInfo:
                continue # Withdrawn services
            if "ExternalID" in serviceInfo[exc["Source"]["Service"]] and exc["Source"]["ExternalID"] != serviceInfo[exc["Source"]["Service"]]["ExternalID"]:
                continue  # this is an old exception for a different connection
            if "ExternalID" in serviceInfo[exc["Target"]["Service"]] and exc["Target"]["ExternalID"] != serviceInfo[exc["Target"]["Service"]]["ExternalID"]:
                continue  # same as above
            serviceInfo[exc["Source"]["Service"]]["BlockFlowTo"].append(exc["Target"]["Service"])
    return {"js_bridge_serviceinfo": json.dumps(serviceInfo)}


def stats(req):
    return {"stats": db.stats.find_one()}

########NEW FILE########
__FILENAME__ = email
from django.template.loader import get_template
from django.template import Context
from django.core.mail import EmailMultiAlternatives
from django.conf import settings

def generate_message_from_template(template, context):
	context["STATIC_URL"] = settings.STATIC_URL
	# Mandrill is set up to inline the CSS and generate a plaintext copy.
	html_message = get_template(template).render(Context(context)).strip()
	context["plaintext"] = True
	plaintext_message = get_template(template).render(Context(context)).strip()
	return html_message, plaintext_message

def send_email(recipient_list, subject, html_message, plaintext_message=None):
	if type(recipient_list) is not list:
		recipient_list = [recipient_list]

	email = EmailMultiAlternatives(subject=subject, body=plaintext_message, from_email="tapiriik <mailer@tapiriik.com>", to=recipient_list, headers={"Reply-To": "contact@tapiriik.com"})
	email.attach_alternative(html_message, "text/html")
	email.send()
########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = startup
from django.core.exceptions import MiddlewareNotUsed
import tapiriik.settings
import subprocess


class ServiceWebStartup:
    def __init__(self):
        from tapiriik.services import Service
        Service.WebInit()
        raise MiddlewareNotUsed


class Startup:
    def __init__(self):
        tapiriik.settings.SITE_VER = subprocess.Popen(["git", "rev-parse", "HEAD"], stdout=subprocess.PIPE).communicate()[0].strip()
        raise MiddlewareNotUsed

########NEW FILE########
__FILENAME__ = displayutils
from django import template
from django.utils.timesince import timesince
from datetime import datetime
import json
register = template.Library()

@register.filter(name="utctimesince")
def utctimesince(value):
    return timesince(value, now=datetime.utcnow())

@register.filter(name="format_meters")
def meters_to_kms(value):
    try:
        return round(value / 1000)
    except:
        return "NaN"

@register.filter(name="format_daily_meters_hourly_rate")
def meters_per_day_to_km_per_hour(value):
    try:
        return (value / 24) / 1000
    except:
        return "0"

@register.filter(name="format_seconds_minutes")
def meters_to_kms(value):
    try:
        return round(value / 60, 1)
    except:
        return "NaN"

@register.filter(name='json')
def jsonit(obj):
    return json.dumps(obj)

@register.filter(name='dict_get')
def dict_get(tdict, key):
    if type(tdict) is not dict:
        tdict = tdict.__dict__
    return tdict.get(key, None)


@register.filter(name='format')
def format(format, var):
    return format.format(var)

@register.simple_tag
def stringformat(value, *args):
    return value.format(*args)

@register.filter(name="percentage")
def percentage(value, *args):
    if not value:
        return "NaN"
    try:
        return str(round(float(value) * 100)) + "%"
    except ValueError:
        return value


def do_infotip(parser, token):
    tagname, infotipId = token.split_contents()
    nodelist = parser.parse(('endinfotip',))
    parser.delete_first_token()
    return InfoTipNode(nodelist, infotipId)

class InfoTipNode(template.Node):
    def __init__(self, nodelist, infotipId):
        self.nodelist = nodelist
        self.infotipId = infotipId
    def render(self, context):
        hidden_infotips = context.get('hidden_infotips', None)
        if hidden_infotips and self.infotipId in hidden_infotips:
            return ""
        output = self.nodelist.render(context)
        return "<p class=\"infotip\" id=\"%s\">%s</p>" % (self.infotipId, output)

register.tag("infotip", do_infotip)
########NEW FILE########
__FILENAME__ = services
from django import template
from tapiriik.services import Service, ServiceRecord
from tapiriik.database import db
register = template.Library()


@register.filter(name="svc_ids")
def IDs(value):
    return [x["Service"] for x in value]


@register.filter(name="svc_providers_except")
def exceptSvc(value):
    connections = [y["Service"] for y in value]
    return [x for x in Service.List() if x.ID not in connections]



@register.filter(name="svc_populate_conns")
def fullRecords(conns):
    return [ServiceRecord(x) for x in db.connections.find({"_id": {"$in": [x["ID"] for x in conns]}})]

########NEW FILE########
__FILENAME__ = users
from django import template
from tapiriik.auth import User, Payments
from tapiriik.database import db
register = template.Library()


@register.filter(name="has_active_payment")
def HasActivePayment(user):
    return User.HasActivePayment(user)

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = ab
from tapiriik.database import db
from django.http import HttpResponse
from django.views.decorators.http import require_POST
import zlib
from datetime import datetime


_experiments = {}


def ab_register_experiment(key, variants):
	_experiments[key] = {"Variants": variants}

def ab_select_variant(key, userKey):
	selector = 0
	selector = zlib.adler32(bytes(str(key), "UTF-8"), selector)
	selector = zlib.adler32(bytes(str(userKey), "UTF-8"), selector)
	selector = selector % len(_experiments[key]["Variants"])
	return _experiments[key]["Variants"][selector]

def ab_experiment_begin(key, userKey):
	db.ab_experiments.insert({"User": userKey, "Experiment": key, "Begin": datetime.utcnow(), "Variant": ab_select_variant(key, userKey)})

def ab_user_experiment_begin(key, request):
	ab_experiment_begin(key, request.user["_id"])

def ab_experiment_complete(key, userKey, result):
	active_experiment = db.ab_experiments.find({"User": userKey, "Experiment": key, "Result": {"$exists": False}}, {"_id": 1}).sort("Begin", -1).limit(1)[0]
	db.ab_experiments.update({"_id": active_experiment["_id"]}, {"$set": {"Result": result}})

def ab_user_experiment_complete(key, request, result):
	ab_experiment_complete(key, request.user["_id"], result)

@require_POST
def ab_web_experiment_begin(request, key):
	if not request.user:
		return HttpResponse(status=403)
	if key not in _experiments:
		return HttpResponse(status=404)
	ab_user_experiment_begin(key, request)
	return HttpResponse()

def ab_experiment_context(request):
	context = {}
	if request.user:
		for key in _experiments.keys():
			context["ab_%s_%s" % (key, ab_select_variant(key, request.user["_id"]))] = True
	return context

########NEW FILE########
__FILENAME__ = account
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.shortcuts import redirect
from tapiriik.auth import User


@require_POST
def account_setemail(req):
    if not req.user:
        return HttpResponse(status=403)
    User.SetEmail(req.user, req.POST["email"])
    return redirect("dashboard")

@require_POST
def account_settimezone(req):
    if not req.user:
        return HttpResponse(status=403)
    User.SetTimezone(req.user, req.POST["timezone"])
    return HttpResponse()

########NEW FILE########
__FILENAME__ = activities_dashboard
from django.shortcuts import render, redirect
from django.http import HttpResponse
from tapiriik.database import db
from tapiriik.settings import WITHDRAWN_SERVICES
import json
import datetime

def activities_dashboard(req):
    if not req.user:
        return redirect("/")
    return render(req, "activities-dashboard.html")

def activities_fetch_json(req):
    if not req.user:
        return HttpResponse(status=403)

    retrieve_fields = [
        "Activities.Prescence",
        "Activities.Abscence",
        "Activities.Type",
        "Activities.Name",
        "Activities.StartTime",
        "Activities.EndTime",
        "Activities.Private",
        "Activities.Stationary"
    ]
    activityRecords = db.activity_records.find_one({"UserID": req.user["_id"]}, dict([(x, 1) for x in retrieve_fields]))
    if not activityRecords:
        return HttpResponse("[]", content_type="application/json")
    cleanedRecords = []
    for activity in activityRecords["Activities"]:
        # Strip down the record since most of this info isn't displayed
        for presence in activity["Prescence"]:
            del activity["Prescence"][presence]["Exception"]
        for abscence in activity["Abscence"]:
            if activity["Abscence"][abscence]["Exception"]:
                del activity["Abscence"][abscence]["Exception"]["InterventionRequired"]
                del activity["Abscence"][abscence]["Exception"]["ClearGroup"]
        # Don't really need these seperate at this point
        activity["Prescence"].update(activity["Abscence"])
        for svc in WITHDRAWN_SERVICES:
            if svc in activity["Prescence"]:
                del activity["Prescence"][svc]
        del activity["Abscence"]
        cleanedRecords.append(activity)


    dthandler = lambda obj: obj.isoformat() if isinstance(obj, datetime.datetime)  or isinstance(obj, datetime.date) else None

    return HttpResponse(json.dumps(cleanedRecords, default=dthandler), content_type="application/json")
########NEW FILE########
__FILENAME__ = auth
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.shortcuts import render, redirect
from tapiriik.services import Service
from tapiriik.auth import User
import json


def auth_login(req, service):
    return redirect("/#/auth/%s" % service)


@require_POST
def auth_login_ajax(req, service):
    res = auth_do(req, service)
    return HttpResponse(json.dumps({"success": res == True, "result": res}), mimetype='application/json')


def auth_do(req, service):
    svc = Service.FromID(service)
    from tapiriik.services.api import APIException
    try:
        if svc.RequiresExtendedAuthorizationDetails:
            uid, authData, extendedAuthData = svc.Authorize(req.POST["username"], req.POST["password"])
        else:
            uid, authData = svc.Authorize(req.POST["username"], req.POST["password"])
    except APIException as e:
        if e.UserException is not None:
            return {"type": e.UserException.Type, "extra": e.UserException.Extra}
        return False
    if authData is not None:
        serviceRecord = Service.EnsureServiceRecordWithAuth(svc, uid, authData, extendedAuthDetails=extendedAuthData if svc.RequiresExtendedAuthorizationDetails else None, persistExtendedAuthDetails=bool(req.POST.get("persist", None)))
        # auth by this service connection
        existingUser = User.AuthByService(serviceRecord)
        # only log us in as this different user in the case that we don't already have an account
        if existingUser is not None and req.user is None:
            User.Login(existingUser, req)
        else:
            User.Ensure(req)
        # link service to user account, possible merge happens behind the scenes (but doesn't effect active user)
        User.ConnectService(req.user, serviceRecord)
        return True
    return False

@require_POST
def auth_persist_extended_auth_ajax(req, service):
    svc = Service.FromID(service)
    svcId = [x["ID"] for x in req.user["ConnectedServices"] if x["Service"] == svc.ID]
    if len(svcId) == 0:
        return HttpResponse(status=404)
    else:
        svcId = svcId[0]
    svcRec = Service.GetServiceRecordByID(svcId)
    if svcRec.HasExtendedAuthorizationDetails():
        Service.PersistExtendedAuthDetails(svcRec)
    return HttpResponse()

def auth_disconnect(req, service):
    if not req.user:
        return redirect("dashboard")
    if "action" in req.POST:
        if req.POST["action"] == "disconnect":
            auth_disconnect_do(req, service)
        return redirect("dashboard")
    return render(req, "auth/disconnect.html", {"serviceid": service, "service": Service.FromID(service)})


@require_POST  # don't want this getting called by just anything
def auth_disconnect_ajax(req, service):
    try:
        status = auth_disconnect_do(req, service)
    except Exception as e:
        raise
        return HttpResponse(json.dumps({"success": False, "error": str(e)}), mimetype='application/json', status=500)
    return HttpResponse(json.dumps({"success": status}), mimetype='application/json')


def auth_disconnect_do(req, service):
    svc = Service.FromID(service)
    svcId = [x["ID"] for x in req.user["ConnectedServices"] if x["Service"] == svc.ID]
    if len(svcId) == 0:
        return
    else:
        svcId = svcId[0]
    svcRec = Service.GetServiceRecordByID(svcId)
    Service.DeleteServiceRecord(svcRec)
    User.DisconnectService(svcRec)
    return True

@require_POST
def auth_logout(req):
    User.Logout(req)
    return redirect("/")
########NEW FILE########
__FILENAME__ = dashboard
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie


@ensure_csrf_cookie
def dashboard(req):
    return render(req, "dashboard.html")

########NEW FILE########
__FILENAME__ = diagnostics
from django.shortcuts import render, redirect
from tapiriik.settings import DIAG_AUTH_TOTP_SECRET, DIAG_AUTH_PASSWORD, SITE_VER
from tapiriik.database import db
from tapiriik.sync import Sync
from tapiriik.auth import TOTP, DiagnosticsUser
from bson.objectid import ObjectId
import hashlib
import json
from datetime import datetime, timedelta

def diag_requireAuth(view):
    def authWrapper(req, *args, **kwargs):
        if not DiagnosticsUser.IsAuthenticated(req):
            return redirect("diagnostics_login")
        return view(req, *args, **kwargs)
    return authWrapper

@diag_requireAuth
def diag_dashboard(req):
    context = {}

    context["lockedSyncUsers"] = list(db.users.find({"SynchronizationWorker": {"$ne": None}}))
    context["lockedSyncRecords"] = len(context["lockedSyncUsers"])

    pendingSynchronizations = db.users.aggregate([
                                                 {"$match": {"NextSynchronization": {"$lt": datetime.utcnow()}}},
                                                 {"$group": {"_id": None, "count": {"$sum": 1}}}
                                                 ])
    if len(pendingSynchronizations["result"]) > 0:
        context["pendingSynchronizations"] = pendingSynchronizations["result"][0]["count"]
    else:
        context["pendingSynchronizations"] = 0

    context["userCt"] = db.users.count()
    context["autosyncCt"] = db.users.find({"NextSynchronization": {"$ne": None}}).count()

    context["errorUsersCt"] = db.users.find({"NonblockingSyncErrorCount": {"$gt": 0}}).count()
    context["exclusionUsers"] = db.users.find({"SyncExclusionCount": {"$gt": 0}}).count()

    context["allWorkers"] = list(db.sync_workers.find())
    context["allWorkerPIDs"] = [x["Process"] for x in context["allWorkers"]]
    context["activeWorkers"] = [x for x in context["allWorkers"] if x["Heartbeat"] > datetime.utcnow() - timedelta(seconds=30)]
    context["stalledWorkers"] = [x for x in context["allWorkers"] if x["Heartbeat"] < datetime.utcnow() - timedelta(seconds=30)]
    context["stalledWorkerPIDs"] = [x["Process"] for x in context["stalledWorkers"]]

    syncErrorListing = list(db.common_sync_errors.find().sort("value", -1))
    syncErrorsAffectingServices = [service for error in syncErrorListing for service in error["value"]["connections"]]
    syncErrorsAffectingUsers = list(db.users.find({"ConnectedServices.ID": {"$in": syncErrorsAffectingServices}}))
    syncErrorSummary = []
    autoSyncErrorSummary = []
    for error in syncErrorListing:
        serviceSet = set(error["value"]["connections"])
        affected_auto_users = [{"id":user["_id"], "highlight": "LastSynchronization" in user and user["LastSynchronization"] > datetime.utcnow() - timedelta(minutes=5), "outdated": user["LastSynchronizationVersion"] != SITE_VER if "LastSynchronizationVersion" in user else True} for user in syncErrorsAffectingUsers if set([conn["ID"] for conn in user["ConnectedServices"]]) & serviceSet and "NextSynchronization" in user and user["NextSynchronization"] is not None]
        affected_users = [{"id": user["_id"], "highlight": False, "outdated": False} for user in syncErrorsAffectingUsers if set([conn["ID"] for conn in user["ConnectedServices"]]) & serviceSet and ("NextSynchronization" not in user or user["NextSynchronization"] is None)]
        if len(affected_auto_users):
            autoSyncErrorSummary.append({"message": error["value"]["exemplar"], "count": int(error["value"]["count"]), "affected_users": affected_auto_users})
        if len(affected_users):
            syncErrorSummary.append({"message": error["value"]["exemplar"], "count": int(error["value"]["count"]), "affected_users": affected_users})

    context["autoSyncErrorSummary"] = autoSyncErrorSummary
    context["syncErrorSummary"] = syncErrorSummary

    delta = False
    if "deleteStalledWorker" in req.POST:
        db.sync_workers.remove({"Process": int(req.POST["pid"])})
        delta = True
    if "unlockOrphaned" in req.POST:
        orphanedUserIDs = [x["_id"] for x in context["lockedSyncUsers"] if x["SynchronizationWorker"] not in context["allWorkerPIDs"]]
        db.users.update({"_id":{"$in":orphanedUserIDs}}, {"$unset": {"SynchronizationWorker": None}}, multi=True)
        delta = True

    if delta:
        return redirect("diagnostics_dashboard")

    return render(req, "diag/dashboard.html", context)


@diag_requireAuth
def diag_user(req, user):
    try:
        userRec = db.users.find_one({"_id": ObjectId(user)})
    except:
        userRec = None
    if not userRec:
        searchOpts = [{"Payments.Txn": user}, {"Payments.Email": user}]
        try:
            searchOpts.append({"AncestorAccounts": ObjectId(user)})
            searchOpts.append({"ConnectedServices.ID": ObjectId(user)})
        except:
            pass # Invalid format for ObjectId
        userRec = db.users.find_one({"$or": searchOpts})
        if not userRec:
            searchOpts = [{"ExternalID": user}]
            try:
                searchOpts.append({"ExternalID": int(user)})
            except:
                pass # Not an int
            svcRec = db.connections.find_one({"$or": searchOpts})
            if svcRec:
                userRec = db.users.find_one({"ConnectedServices.ID": svcRec["_id"]})
        if userRec:
            return redirect("diagnostics_user", user=userRec["_id"])
    if not userRec:
        return render(req, "diag/error_user_not_found.html")
    delta = True # Easier to set this to false in the one no-change case.
    if "sync" in req.POST:
        Sync.ScheduleImmediateSync(userRec, req.POST["sync"] == "Full")
    elif "unlock" in req.POST:
        db.users.update({"_id": ObjectId(user)}, {"$unset": {"SynchronizationWorker": None}})
    elif "lock" in req.POST:
        db.users.update({"_id": ObjectId(user)}, {"$set": {"SynchronizationWorker": 1}})
    elif "hostrestrict" in req.POST:
        host = req.POST["host"]
        if host:
            db.users.update({"_id": ObjectId(user)}, {"$set": {"SynchronizationHostRestriction": host}})
        else:
            db.users.update({"_id": ObjectId(user)}, {"$unset": {"SynchronizationHostRestriction": None}})
    elif "substitute" in req.POST:
        req.session["substituteUserid"] = user
        return redirect("dashboard")
    elif "svc_setauth" in req.POST and len(req.POST["authdetails"]):
        db.connections.update({"_id": ObjectId(req.POST["id"])}, {"$set":{"Authorization": json.loads(req.POST["authdetails"])}})
    elif "svc_setconfig" in req.POST and len(req.POST["config"]):
        db.connections.update({"_id": ObjectId(req.POST["id"])}, {"$set":{"Config": json.loads(req.POST["config"])}})
    elif "svc_unlink" in req.POST:
        from tapiriik.services import Service
        from tapiriik.auth import User
        svcRec = Service.GetServiceRecordByID(req.POST["id"])
        try:
            Service.DeleteServiceRecord(svcRec)
        except:
            pass
        try:
            User.DisconnectService(svcRec)
        except:
            pass
    elif "svc_marksync" in req.POST:
        db.connections.update({"_id": ObjectId(req.POST["id"])},
                              {"$addToSet": {"SynchronizedActivities": req.POST["uid"]}},
                              multi=False)
    elif "svc_clearexc" in req.POST:
        db.connections.update({"_id": ObjectId(req.POST["id"])}, {"$unset": {"ExcludedActivities": 1}})
    elif "svc_clearacts" in req.POST:
        db.connections.update({"_id": ObjectId(req.POST["id"])}, {"$unset": {"SynchronizedActivities": 1}})
        Sync.SetNextSyncIsExhaustive(userRec, True)
    else:
        delta = False

    if delta:
        return redirect("diagnostics_user", user=user)
    return render(req, "diag/user.html", {"user": userRec})


@diag_requireAuth
def diag_unsu(req):
    if "substituteUserid" in req.session:
        user = req.session["substituteUserid"]
        del req.session["substituteUserid"]
        return redirect("diagnostics_user", user=user)
    else:
        return redirect("dashboard")

@diag_requireAuth
def diag_payments(req):
    payments = list(db.payments.find())
    for payment in payments:
        payment["Accounts"] = [x["_id"] for x in db.users.find({"Payments.Txn": payment["Txn"]}, {"_id":1})]
    return render(req, "diag/payments.html", {"payments": payments})

def diag_login(req):
    if "password" in req.POST:
        if hashlib.sha512(req.POST["password"].encode("utf-8")).hexdigest().upper() == DIAG_AUTH_PASSWORD and TOTP.Get(DIAG_AUTH_TOTP_SECRET) == int(req.POST["totp"]):
            DiagnosticsUser.Authorize(req)
            return redirect("diagnostics_dashboard")
    return render(req, "diag/login.html")

########NEW FILE########
__FILENAME__ = privacy
from django.shortcuts import render
from tapiriik.services import Service
from tapiriik.settings import WITHDRAWN_SERVICES
from tapiriik.auth import User
def privacy(request):

    OPTIN = "<span class=\"optin policy\">Opt-in</span>"
    NO = "<span class=\"no policy\">No</span>"
    YES = "<span class=\"yes policy\">Yes</span>"
    CACHED = "<span class=\"cached policy\">Cached</span>"
    SEEBELOW = "See below"

    services = dict([[x.ID, {"DisplayName": x.DisplayName, "ID": x.ID}] for x in Service.List() if x.ID not in WITHDRAWN_SERVICES])

    services["garminconnect"].update({"email": OPTIN, "password": OPTIN, "tokens": NO, "metadata": YES, "data":NO})
    services["strava"].update({"email": NO, "password": NO, "tokens": YES, "metadata": YES, "data":NO})
    services["sporttracks"].update({"email": NO, "password": NO, "tokens": YES, "metadata": YES, "data":NO})
    services["dropbox"].update({"email": NO, "password": NO, "tokens": YES, "metadata": YES, "data":CACHED})
    services["runkeeper"].update({"email": NO, "password": NO, "tokens": YES, "metadata": YES, "data":NO})
    services["rwgps"].update({"email": OPTIN, "password": OPTIN, "tokens": NO, "metadata": YES, "data":NO})
    services["trainingpeaks"].update({"email": OPTIN, "password": OPTIN, "tokens": NO, "metadata": YES, "data":NO})
    services["endomondo"].update({"email": NO, "password": NO, "tokens": YES, "metadata": YES, "data":NO})

    def user_services_sort(service):
        if not request.user:
            return 0
        if User.IsServiceConnected(request.user, service["ID"]):
            return 0
        else:
            return 1

    services_list = sorted(services.values(), key=user_services_sort)
    return render(request, "privacy.html", {"services": services_list})
########NEW FILE########
__FILENAME__ = settings
from django.shortcuts import render, redirect
from tapiriik.auth import User

def settings(request):
    available_settings = {
        "allow_activity_flow_exception_bypass_via_self":
            {"Title": "Route activities via",
            "Description": "Allows activities to flow through this service to avoid a flow exception that would otherwise prevent them arriving at a destination.",
            "Field": "checkbox"
            },
        "sync_private":
            {"Title": "Sync private activities",
            "Description": "By default, all activities will be synced. Unsetting this will prevent private activities being taken from this service.",
            "Field": "checkbox",
            "Available": ["strava", "runkeeper"]
            }
    }
    conns = User.GetConnectionRecordsByUser(request.user)

    for key, setting in available_settings.items():
        available_settings[key]["Values"] = {}

    for conn in conns:
        config = conn.GetConfiguration()
        for key, setting in available_settings.items():
            if request.method == "POST":
                formkey = key + "_" + conn.Service.ID
                if setting["Field"] == "checkbox":
                    config[key] = formkey in request.POST
            available_settings[key]["Values"][conn.Service.ID] = config[key]

        if request.method == "POST":
            conn.SetConfiguration(config)
    if request.method == "POST":
        return redirect("settings_panel")

    return render(request, "settings.html", {"user": request.user, "settings": available_settings})

########NEW FILE########
__FILENAME__ = supported_activities
from django.shortcuts import render


def supported_activities(req):
    # so as not to force people to read REGEX to understand what they can name their activities
    ELLIPSES = "&hellip;"
    activities = {}
    activities["Running"] = ["run", "running"]
    activities["Cycling"] = ["cycling", "cycle", "bike", "biking"]
    activities["Mountain biking"] = ["mtnbiking", "mtnbiking", "mountainbike", "mountainbiking"]
    activities["Walking"] = ["walking", "walk"]
    activities["Hiking"] = ["hike", "hiking"]
    activities["Downhill skiing"] = ["downhill", "downhill skiing", "downhill-skiing", "downhillskiing", ELLIPSES]
    activities["Cross-country skiing"] = ["xcskiing", "xc-skiing", "xc-ski", "crosscountry-skiing", ELLIPSES]
    activities["Snowboarding"] = ["snowboarding", "snowboard"]
    activities["Skating"] = ["skate", "skating"]
    activities["Swimming"] = ["swim", "swimming"]
    activities["Wheelchair"] = ["wheelchair"]
    activities["Rowing"] = ["rowing", "row"]
    activities["Elliptical"] = ["elliptical"]
    activities["Other"] = ["other", "unknown"]
    activityList = []
    for act, synonyms in activities.items():
        activityList.append({"name": act, "synonyms": synonyms})
    return render(req, "supported-activities.html", {"actMap": activityList})

########NEW FILE########
__FILENAME__ = supported_services
from django.shortcuts import render, redirect

def supported_services_poll(req):
	return render(req, "supported-services-poll.html", {"voter_key": req.user["_id"] if req.user else ""}) # Should probably do something with ancestor accounts?
########NEW FILE########
__FILENAME__ = sync
import json
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from tapiriik.auth import User
from tapiriik.sync import Sync
from tapiriik.database import db
from tapiriik.services import Service
from datetime import datetime
import zlib


def sync_status(req):
    if not req.user:
        return HttpResponse(status=403)

    stats = db.stats.find_one()
    syncHash = 1  # Just used to refresh the dashboard page, until I get on the Angular bandwagon.
    conns = User.GetConnectionRecordsByUser(req.user)
    errorCodes = []
    for conn in conns:
        syncHash = zlib.adler32(bytes(conn.HasExtendedAuthorizationDetails()), syncHash)
        if not hasattr(conn, "SyncErrors"):
            continue
        for err in conn.SyncErrors:
            syncHash = zlib.adler32(bytes(str(err), "UTF-8"), syncHash)
            if "Code" in err and err["Code"] is not None and len(err["Code"]) > 0:
                errorCodes.append(err["Code"])
            else:
                errorCodes.append("SYS-" + err["Step"])

    sync_status_dict = {"NextSync": (req.user["NextSynchronization"].ctime() + " UTC") if "NextSynchronization" in req.user and req.user["NextSynchronization"] is not None else None,
                        "LastSync": (req.user["LastSynchronization"].ctime() + " UTC") if "LastSynchronization" in req.user and req.user["LastSynchronization"] is not None else None,
                        "Synchronizing": "SynchronizationWorker" in req.user,
                        "SynchronizationProgress": req.user["SynchronizationProgress"] if "SynchronizationProgress" in req.user else None,
                        "SynchronizationStep": req.user["SynchronizationStep"] if "SynchronizationStep" in req.user else None,
                        "SynchronizationWaitTime": None, # I wish.
                        "Errors": errorCodes,
                        "Hash": syncHash}

    if stats and "QueueHeadTime" in stats:
        sync_status_dict["SynchronizationWaitTime"] = (stats["QueueHeadTime"] - (datetime.utcnow() - req.user["NextSynchronization"]).total_seconds()) if "NextSynchronization" in req.user and req.user["NextSynchronization"] is not None else None

    return HttpResponse(json.dumps(sync_status_dict), mimetype="application/json")

@require_POST
def sync_schedule_immediate(req):
    if not req.user:
        return HttpResponse(status=401)
    if "LastSynchronization" in req.user and req.user["LastSynchronization"] is not None and datetime.utcnow() - req.user["LastSynchronization"] < Sync.MinimumSyncInterval:
        return HttpResponse(status=403)
    exhaustive = None
    if "LastSynchronization" in req.user and req.user["LastSynchronization"] is not None and datetime.utcnow() - req.user["LastSynchronization"] > Sync.MaximumIntervalBeforeExhaustiveSync:
        exhaustive = True
    Sync.ScheduleImmediateSync(req.user, exhaustive)
    return HttpResponse()

@require_POST
def sync_clear_errorgroup(req, service, group):
    if not req.user:
        return HttpResponse(status=401)

    rec = User.GetConnectionRecord(req.user, service)
    if not rec:
        return HttpResponse(status=404)

    # Prevent this becoming a vehicle for rapid synchronization
    to_clear_count = 0
    for x in rec.SyncErrors:
        if "UserException" in x and "ClearGroup" in x["UserException"] and x["UserException"]["ClearGroup"] == group:
            to_clear_count += 1

    if to_clear_count > 0:
            db.connections.update({"_id": rec._id}, {"$pull":{"SyncErrors":{"UserException.ClearGroup": group}}})
            db.users.update({"_id": req.user["_id"]}, {'$inc':{"BlockingSyncErrorCount":-to_clear_count}}) # In the interests of data integrity, update the summary counts immediately as opposed to waiting for a sync to complete.
            Sync.ScheduleImmediateSync(req.user, True) # And schedule them for an immediate full resynchronization, so the now-unblocked services can be brought up to speed.            return HttpResponse()
            return HttpResponse()

    return HttpResponse(status=404)

@csrf_exempt
@require_POST
def sync_trigger_partial_sync_callback(req, service):
    svc = Service.FromID(service)
    affected_connection_external_ids = svc.ServiceRecordIDsForPartialSyncTrigger(req)
    db.connections.update({"Service": service, "ExternalID": {"$in": affected_connection_external_ids}}, {"$set":{"TriggerPartialSync": True, "TriggerPartialSyncTimestamp": datetime.utcnow()}}, multi=True)
    # Will turn this on once there's a sync-delay option
    # db.users.update({"ConnectedServices.ID": {"$in": affected_connection_ids}}, {"$set": {"NextSynchronization": datetime.utcnow()}}, multi=True) # It would be nicer to use the Sync.Schedule... method, but I want to cleanly do this in bulk
    return HttpResponse(status=204)


########NEW FILE########
__FILENAME__ = trainingpeaks_premium
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.utils.http import urlencode
@csrf_exempt
def trainingpeaks_premium(request):
	ctx = {}
	if "password" in request.POST:
		ctx = {"password": request.POST["password"], "username": request.POST["username"], "personId": request.POST["personId"]}

	return render(request, "trainingpeaks_premium.html", ctx)
########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for tapiriik project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.

"""
import os

# We defer to a DJANGO_SETTINGS_MODULE already in the environment. This breaks
# if running multiple sites in the same mod_wsgi process. To fix this, use
# mod_wsgi daemon mode with each site in its own daemon process, or use
# os.environ["DJANGO_SETTINGS_MODULE"] = "tapiriik.settings"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tapiriik.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
__FILENAME__ = tz_ingest
# This file isn't called in normal operation, just to update the TZ boundary DB.
# Should be called with `tz_world.*` files from http://efele.net/maps/tz/world/ in the working directory.
# Requires pyshp and shapely for py3k (from https://github.com/mwtoews/shapely/tree/py3)

import shapefile
from shapely.geometry import Polygon, mapping
import pymongo
from tapiriik.database import tzdb

print("Dropping boundaries collection")
tzdb.drop_collection("boundaries")

print("Setting up index")
tzdb.boundaries.ensure_index([("Boundary", pymongo.GEOSPHERE)])

print("Reading shapefile")
records = []
sf = shapefile.Reader("tz_world.shp")
shapeRecs = sf.shapeRecords()

ct = 0
total = len(shapeRecs)
for shape in shapeRecs:
	tzid = shape.record[0]
	print("%3d%% %s" % (round(ct * 100 / total), tzid))
	ct += 1
	polygon = Polygon(list(shape.shape.points))
	if not polygon.is_valid:
		polygon = polygon.buffer(0) # Resolves issues with most self-intersecting geometry
		assert polygon.is_valid
	record = {"TZID": tzid, "Boundary": mapping(polygon)}
	tzdb.boundaries.insert(record) # Would be bulk insert, but that makes it a pain to debug geometry issues

########NEW FILE########
