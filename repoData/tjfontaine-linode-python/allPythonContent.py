__FILENAME__ = api
#!/usr/bin/python
# vim:ts=2:sw=2:expandtab
"""
A Python library to perform low-level Linode API functions.

Copyright (c) 2010 Timothy J Fontaine <tjfontaine@gmail.com>
Copyright (c) 2010 Josh Wright <jshwright@gmail.com>
Copyright (c) 2010 Ryan Tucker <rtucker@gmail.com>
Copyright (c) 2008 James C Sinclair <james@irgeek.com>
Copyright (c) 2013 Tim Heckman <tim@timheckman.net>
Copyright (c) 2014 Magnus Appelquist <magnus.appelquist@cloudnet.se>

Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
"""

from decimal import Decimal
import logging
import urllib
import urllib2

try:
  import json
  FULL_BODIED_JSON = True
except:
  import simplejson as json
  FULL_BODIED_JSON = False

try:
  import requests
  from types import MethodType

  def requests_request(url, fields, headers):
    return requests.Request(method="POST", url=url, headers=headers, data=fields)

  def requests_open(request):
    r = request.prepare()
    s = requests.Session()
    s.verify = True
    response = s.send(r)
    response.read = MethodType(lambda x: x.text, response)
    return response

  URLOPEN = requests_open
  URLREQUEST = requests_request
except:
  try:
    import VEpycurl
    def vepycurl_request(url, fields, headers):
      return (url, fields, headers)

    def vepycurl_open(request):
      c = VEpycurl.VEpycurl(verifySSL=2)
      url, fields, headers = request
      nh = [ '%s: %s' % (k, v) for k,v in headers.items()]
      c.perform(url, fields, nh)
      return c.results()

    URLOPEN = vepycurl_open
    URLREQUEST = vepycurl_request
  except:
    import warnings
    ssl_message = 'using urllib instead of pycurl, urllib does not verify SSL remote certificates, there is a risk of compromised communication'
    warnings.warn(ssl_message, RuntimeWarning)

    def urllib_request(url, fields, headers):
      fields = urllib.urlencode(fields)
      return urllib2.Request(url, fields, headers)

    URLOPEN = urllib2.urlopen
    URLREQUEST = urllib_request


class MissingRequiredArgument(Exception):
  """Raised when a required parameter is missing."""
  
  def __init__(self, value):
    self.value = value
  def __str__(self):
    return repr(self.value)

class ApiError(Exception):
  """Raised when a Linode API call returns an error.

  Returns:
    [{u'ERRORCODE': Error code number,
      u'ERRORMESSAGE': 'Description of error'}]

  ErrorCodes that can be returned by any method, per Linode API specification:
    0: ok
    1: Bad request
    2: No action was requested
    3: The requested class does not exist
    4: Authentication failed
    5: Object not found
    6: A required property is missing for this action
    7: Property is invalid
    8: A data validation error has occurred
    9: Method Not Implemented
    10: Too many batched requests
    11: RequestArray isn't valid JSON or WDDX
    13: Permission denied
    30: Charging the credit card failed
    31: Credit card is expired
    40: Limit of Linodes added per hour reached
    41: Linode must have no disks before delete
  """
  
  def __init__(self, value):
    self.value = value
  def __str__(self):
    return repr(self.value)

class ApiInfo:
  valid_commands = {}
  valid_params   = {}

LINODE_API_URL = 'https://api.linode.com/api/'

VERSION = '0.0.1'

class LowerCaseDict(dict):
  def __init__(self, copy=None):
    if copy:
      if isinstance(copy, dict):
        for k,v in copy.items():
          dict.__setitem__(self, k.lower(), v)
      else:
        for k,v in copy:
          dict.__setitem__(self, k.lower(), v)

  def __getitem__(self, key):
    return dict.__getitem__(self, key.lower())

  def __setitem__(self, key, value):
    dict.__setitem__(self, key.lower(), value)

  def __contains__(self, key):
    return dict.__contains__(self, key.lower())

  def get(self, key, def_val=None):
    return dict.get(self, key.lower(), def_val)

  def setdefault(self, key, def_val=None):
    return dict.setdefault(self, key.lower(), def_val)

  def update(self, copy):
    for k,v in copy.items():
      dict.__setitem__(self, k.lower(), v)

  def fromkeys(self, iterable, value=None):
    d = self.__class__()
    for k in iterable:
      dict.__setitem__(d, k.lower(), value)
    return d

  def pop(self, key, def_val=None):
    return dict.pop(self, key.lower(), def_val)

class Api:
  """Linode API (version 2) client class.

  Instantiate with: Api(), or Api(optional parameters)

  Optional parameters:
        key - Your API key, from "My Profile" in the LPM (default: None)
        batching - Enable batching support (default: False)

  This interfaces with the Linode API (version 2) and receives a response
  via JSON, which is then parsed and returned as a dictionary (or list
  of dictionaries).

  In the event of API problems, raises ApiError:
        api.ApiError: [{u'ERRORCODE': 99,
                        u'ERRORMESSAGE': u'Error Message'}]

  If you do not specify a key, the only method you may use is
  user_getapikey(username, password).  This will retrieve and store
  the API key for a given user.

  Full documentation on the API can be found from Linode at:
        http://www.linode.com/api/
  """

  def __init__(self, key=None, batching=False):
    self.__key = key
    self.__urlopen = URLOPEN
    self.__request = URLREQUEST
    self.batching = batching
    self.__batch_cache = []

  @staticmethod
  def valid_commands():
    """Returns a list of API commands supported by this class."""
    return list(ApiInfo.valid_commands.keys())

  @staticmethod
  def valid_params():
    """Returns a list of all parameters used by methods of this class."""
    return list(ApiInfo.valid_params.keys())

  def batchFlush(self):
    """Initiates a batch flush.  Raises Exception if not in batching mode."""
    if not self.batching:
      raise Exception('Cannot flush requests when not batching')

    s = json.dumps(self.__batch_cache)
    self.__batch_cache = []
    request = { 'api_action' : 'batch', 'api_requestArray' : s }
    return self.__send_request(request)

  def __getattr__(self, name):
    """Return a callable for any undefined attribute and assume it's an API call"""
    if name.startswith('__'):
      raise AttributeError()

    def generic_request(*args, **kw):
      request = LowerCaseDict(kw)
      request['api_action'] = name.replace('_', '.')

      if self.batching:
        self.__batch_cache.append(request)
        logging.debug('Batched: %s', json.dumps(request))
      else:
        return self.__send_request(request)

    generic_request.__name__ = name
    return generic_request

  def __send_request(self, request):
    if self.__key:
      request['api_key'] = self.__key
    elif request['api_action'] != 'user.getapikey':
      raise Exception('Must call user_getapikey to fetch key')

    request['api_responseFormat'] = 'json'

    logging.debug('Parmaters '+str(request))
    #request = urllib.urlencode(request)

    headers = {
      'User-Agent': 'LinodePython/'+VERSION,
    }

    req = self.__request(LINODE_API_URL, request, headers)
    response = self.__urlopen(req)
    response = response.read()

    logging.debug('Raw Response: '+response)

    if FULL_BODIED_JSON:
      try:
        s = json.loads(response, parse_float=Decimal)
      except Exception, ex:
        print(response)
        raise ex
    else:
      # Stuck with simplejson, which won't let us parse_float
      s = json.loads(response)

    if isinstance(s, dict):
      s = LowerCaseDict(s)
      if len(s['ERRORARRAY']) > 0:
        if s['ERRORARRAY'][0]['ERRORCODE'] is not 0:
          raise ApiError(s['ERRORARRAY'])
      if s['ACTION'] == 'user.getapikey':
        self.__key = s['DATA']['API_KEY']
        logging.debug('API key is: '+self.__key)
      return s['DATA']
    else:
      return s

  def __api_request(required=[], optional=[], returns=[]):
    """Decorator to define required and optional paramters"""
    for k in required:
      k = k.lower()
      if k not in ApiInfo.valid_params:
        ApiInfo.valid_params[k] = True

    for k in optional:
      k = k.lower()
      if k not in ApiInfo.valid_params:
        ApiInfo.valid_params[k] = True

    def decorator(func):
      if func.__name__ not in ApiInfo.valid_commands:
        ApiInfo.valid_commands[func.__name__] = True

      def wrapper(self, **kw):
        request = LowerCaseDict()
        request['api_action'] = func.__name__.replace('_', '.')

        params = LowerCaseDict(kw)

        for k in required:
          if k not in params:
            raise MissingRequiredArgument(k)

        for k in params:
          request[k] = params[k]

        result = func(self, request)

        if result is not None:
          request = result

        if self.batching:
          self.__batch_cache.append(request)
          logging.debug('Batched: '+ json.dumps(request))
        else:
          return self.__send_request(request)

      wrapper.__name__ = func.__name__
      wrapper.__doc__ = func.__doc__
      wrapper.__dict__.update(func.__dict__)

      if (required or optional) and wrapper.__doc__:
        # Generate parameter documentation in docstring
        if len(wrapper.__doc__.split('\n')) is 1:  # one-liners need whitespace
          wrapper.__doc__ += '\n'
        wrapper.__doc__ += '\n    Keyword arguments (* = required):\n'
        wrapper.__doc__ += ''.join(['\t *%s\n' % p for p in required])
        wrapper.__doc__ += ''.join(['\t  %s\n' % p for p in optional])

      if returns and wrapper.__doc__:
        # we either have a list of dicts or a just plain dict
        if len(wrapper.__doc__.split('\n')) is 1:  # one-liners need whitespace
          wrapper.__doc__ += '\n' 
        if isinstance(returns, list):
          width = max(len(q) for q in returns[0].keys())
          wrapper.__doc__ += '\n    Returns list of dictionaries:\n\t[{\n'
          wrapper.__doc__ += ''.join(['\t  %-*s: %s\n'
                              % (width, p, returns[0][p]) for p in returns[0].keys()])
          wrapper.__doc__ += '\t }, ...]\n'
        else:
          width = max(len(q) for q in returns.keys())
          wrapper.__doc__ += '\n    Returns dictionary:\n\t {\n'
          wrapper.__doc__ += ''.join(['\t  %-*s: %s\n'
                              % (width, p, returns[p]) for p in returns.keys()])
          wrapper.__doc__ += '\t }\n'

      return wrapper
    return decorator

  @__api_request(optional=['LinodeID'],
                 returns=[{u'ALERT_BWIN_ENABLED': '0 or 1',
                           u'ALERT_BWIN_THRESHOLD': 'integer (Mb/sec?)',
                           u'ALERT_BWOUT_ENABLED': '0 or 1',
                           u'ALERT_BWOUT_THRESHOLD': 'integer (Mb/sec?)',
                           u'ALERT_BWQUOTA_ENABLED': '0 or 1',
                           u'ALERT_BWQUOTA_THRESHOLD': '0..100',
                           u'ALERT_CPU_ENABLED': '0 or 1',
                           u'ALERT_CPU_THRESHOLD': '0..400 (% CPU)',
                           u'ALERT_DISKIO_ENABLED': '0 or 1',
                           u'ALERT_DISKIO_THRESHOLD': 'integer (IO ops/sec?)',
                           u'BACKUPSENABLED': '0 or 1',
                           u'BACKUPWEEKLYDAY': '0..6 (day of week, 0 = Sunday)',
                           u'BACKUPWINDOW': 'some integer',
                           u'DATACENTERID': 'Datacenter ID',
                           u'LABEL': 'linode label',
                           u'LINODEID': 'Linode ID',
                           u'LPM_DISPLAYGROUP': 'group label',
                           u'STATUS': 'Status flag',
                           u'TOTALHD': 'available disk (GB)',
                           u'TOTALRAM': 'available RAM (MB)',
                           u'TOTALXFER': 'available bandwidth (GB/month)',
                           u'WATCHDOG': '0 or 1'}])
  def linode_list(self, request):
    """List information about your Linodes.

    Status flag values:
      -2: Boot Failed (not in use)
      -1: Being Created
       0: Brand New
       1: Running
       2: Powered Off
       3: Shutting Down (not in use)
       4: Saved to Disk (not in use)
    """
    pass

  @__api_request(required=['LinodeID'],
                 optional=['Label', 'lpm_displayGroup', 'Alert_cpu_enabled',
                           'Alert_cpu_threshold', 'Alert_diskio_enabled',
                           'Alert_diskio_threshold', 'Alert_bwin_enabled',
                           'Alert_bwin_threshold', 'Alert_bwout_enabled',
                           'Alert_bwout_threshold', 'Alert_bwquota_enabled',
                           'Alert_bwquota_threshold', 'backupWindow',
                           'backupWeeklyDay', 'watchdog'],
                 returns={u'LinodeID': 'LinodeID'})
  def linode_update(self, request):
    """Update information about, or settings for, a Linode.

    See linode_list.__doc__ for information on parameters.
    """
    pass

  @__api_request(required=['DatacenterID', 'PlanID', 'PaymentTerm'],
                 returns={u'LinodeID': 'New Linode ID'})
  def linode_create(self, request):
    """Create a new Linode.

    This will create a billing event.
    """
    pass

  @__api_request(required=['LinodeID'], returns={u'JobID': 'Job ID'})
  def linode_shutdown(self, request):
    """Submit a shutdown job for a Linode.

    On job submission, returns the job ID.  Does not wait for job
    completion (see linode_job_list).
    """
    pass

  @__api_request(required=['LinodeID'], optional=['ConfigID'],
                 returns={u'JobID': 'Job ID'})
  def linode_boot(self, request):
    """Submit a boot job for a Linode.

    On job submission, returns the job ID.  Does not wait for job
    completion (see linode_job_list).
    """
    pass

  @__api_request(required=['LinodeID'], optional=['skipChecks'],
                 returns={u'LinodeID': 'Destroyed Linode ID'})
  def linode_delete(self, request):
    """Completely, immediately, and totally deletes a Linode.
    Requires all disk images be deleted first, or that the optional
    skipChecks parameter be set.

    This will create a billing event.

    WARNING: Deleting your last Linode may disable services that
    require a paid account (e.g. DNS hosting).
    """
    pass

  @__api_request(required=['LinodeID'], optional=['ConfigID'],
                 returns={u'JobID': 'Job ID'})
  def linode_reboot(self, request):
    """Submit a reboot job for a Linode.
    
    On job submission, returns the job ID.  Does not wait for job
    completion (see linode_job_list).
    """
    pass

  @__api_request(required=['LinodeID', 'PlanID'])
  def linode_resize(self, request):
    """Resize a Linode from one plan to another.

    Immediately shuts the Linode down, charges/credits the account, and
    issues a migration to an appropriate host server.
    """
    pass

  @__api_request(required=['LinodeID'],
                 returns=[{u'Comments': 'comments field',
                           u'ConfigID': 'Config ID',
                           u'DiskList': "',,,,,,,,' disk array",
                           u'helper_depmod': '0 or 1',
                           u'helper_disableUpdateDB': '0 or 1',
                           u'helper_libtls': '0 or 1',
                           u'helper_xen': '0 or 1',
                           u'KernelID': 'Kernel ID',
                           u'Label': 'Profile name',
                           u'LinodeID': 'Linode ID',
                           u'RAMLimit': 'Max memory (MB), 0 is unlimited',
                           u'RootDeviceCustom': '',
                           u'RootDeviceNum': 'root partition (1=first, 0=RootDeviceCustom)',
                           u'RootDeviceRO': '0 or 1',
                           u'RunLevel': "in ['default', 'single', 'binbash'"}])
  def linode_config_list(self, request):
    """Lists all configuration profiles for a given Linode."""
    pass

  @__api_request(required=['LinodeID', 'ConfigID'],
                 optional=['KernelID', 'Label', 'Comments', 'RAMLimit',
                           'DiskList', 'RunLevel', 'RootDeviceNum',
                           'RootDeviceCustom', 'RootDeviceRO',
                           'helper_disableUpdateDB', 'helper_xen',
                           'helper_depmod'],
                 returns={u'ConfigID': 'Config ID'})
  def linode_config_update(self, request):
    """Updates a configuration profile."""
    pass

  @__api_request(required=['LinodeID', 'KernelID', 'Label', 'Disklist'],
                 optional=['Comments', 'RAMLimit', 'RunLevel',
                           'RootDeviceNum', 'RootDeviceCustom',
                           'RootDeviceRO', 'helper_disableUpdateDB',
                           'helper_xen', 'helper_depmod'],
                 returns={u'ConfigID': 'Config ID'})
  def linode_config_create(self, request):
    """Creates a configuration profile."""
    pass

  @__api_request(required=['LinodeID', 'ConfigID'],
                 returns={u'ConfigID': 'Config ID'})
  def linode_config_delete(self, request):
    """Deletes a configuration profile.  This does not delete the
    Linode itself, nor its disk images (see linode_disk_delete,
    linode_delete).
    """
    pass
  
  @__api_request(required=['LinodeID'],
                 returns=[{u'CREATE_DT': u'YYYY-MM-DD hh:mm:ss.0',
                           u'DISKID': 'Disk ID',
                           u'ISREADONLY': '0 or 1',
                           u'LABEL': 'Disk label',
                           u'LINODEID': 'Linode ID',
                           u'SIZE': 'Size of disk (MB)',
                           u'STATUS': 'Status flag',
                           u'TYPE': "in ['ext3', 'swap', 'raw']",
                           u'UPDATE_DT': u'YYYY-MM-DD hh:mm:ss.0'}])
  def linode_disk_list(self, request):
    """Lists all disk images associated with a Linode."""
    pass

  @__api_request(required=['LinodeID', 'DiskID'],
                 optional=['Label', 'isReadOnly'],
                 returns={u'DiskID': 'Disk ID'})
  def linode_disk_update(self, request):
    """Updates the information about a disk image."""
    pass

  @__api_request(required=['LinodeID', 'Type', 'Size', 'Label'],
                 optional=['isReadOnly'],
                 returns={u'DiskID': 'Disk ID', u'JobID': 'Job ID'})
  def linode_disk_create(self, request):
    """Submits a job to create a new disk image.

    On job submission, returns the disk ID and job ID.  Does not
    wait for job completion (see linode_job_list).
    """
    pass

  @__api_request(required=['LinodeID', 'DiskID'],
                 returns={u'DiskID': 'New Disk ID', u'JobID': 'Job ID'})
  def linode_disk_duplicate(self, request):
    """Submits a job to preform a bit-for-bit copy of a disk image.

    On job submission, returns the disk ID and job ID.  Does not
    wait for job completion (see linode_job_list).
    """
    pass

  @__api_request(required=['LinodeID', 'DiskID'],
                 returns={u'DiskID': 'Deleted Disk ID', u'JobID': 'Job ID'})
  def linode_disk_delete(self, request):
    """Submits a job to delete a disk image.

    WARNING: All data on the disk image will be lost forever.

    On job submission, returns the disk ID and job ID.  Does not
    wait for job completion (see linode_job_list).
    """
    pass

  @__api_request(required=['LinodeID', 'DiskID', 'Size'],
                 returns={u'DiskID': 'Disk ID', u'JobID': 'Job ID'})
  def linode_disk_resize(self, request):
    """Submits a job to resize a partition.

    On job submission, returns the disk ID and job ID.  Does not
    wait for job completion (see linode_job_list).
    """
    pass

  @__api_request(required=['LinodeID', 'DistributionID', 'rootPass', 'Label',
                           'Size'],
                 optional=['rootSSHKey'],
                 returns={u'DiskID': 'New Disk ID', u'JobID': 'Job ID'})
  def linode_disk_createfromdistribution(self, request):
    """Submits a job to create a disk image from a Linode template.

    On job submission, returns the disk ID and job ID.  Does not
    wait for job completion (see linode_job_list).
    """
    pass

  @__api_request(required=['LinodeID', 'StackScriptID', 'StackScriptUDFResponses',
                           'DistributionID', 'rootPass', 'Label', 'Size'],
                 returns={u'DiskID': 'New Disk ID', u'JobID': 'Job ID'})
  def linode_disk_createfromstackscript(self, request):
    """Submits a job to create a disk image from a Linode template.

    On job submission, returns the disk ID and job ID.  Does not
    wait for job completion (see linode_job_list). Note: the
    'StackScriptUDFResponses' must be a valid JSON string.
    """
    pass

  @__api_request(required=['LinodeID'],
                 returns={u'IPAddressID': 'New IP Address ID'})
  def linode_ip_addprivate(self, request):
    """Assigns a Private IP to a Linode.  Returns the IPAddressID
    that was added."""
    pass

  @__api_request(required=['LinodeID'], optional=['IPAddressID'],
                 returns=[{u'ISPUBLIC': '0 or 1',
                           u'IPADDRESS': '192.168.100.1',
                           u'IPADDRESSID': 'IP address ID',
                           u'LINODEID': 'Linode ID',
                           u'RDNS_NAME': 'reverse.dns.name.here'}])
  def linode_ip_list(self, request):
    """Lists a Linode's IP addresses."""
    pass

  @__api_request(required=['IPAddressID','Hostname'],
                 returns=[{u'HOSTNAME': 'reverse.dns.name.here',
                           u'IPADDRESS': '192.168.100.1',
                           u'IPADDRESSID': 'IP address ID'}])
  def linode_ip_setrdns(self, request):
    """Sets the reverse DNS name of a public Linode IP."""
    pass

  @__api_request(required=['LinodeID'], optional=['pendingOnly', 'JobID'],
                 returns=[{u'ACTION': "API action (e.g. u'linode.create')",
                           u'DURATION': "Duration spent processing or ''",
                           u'ENTERED_DT': 'yyyy-mm-dd hh:mm:ss.0',
                           u'HOST_FINISH_DT': "'yyyy-mm-dd hh:mm:ss.0' or ''",
                           u'HOST_MESSAGE': 'response from host',
                           u'HOST_START_DT': "'yyyy-mm-dd hh:mm:ss.0' or ''",
                           u'HOST_SUCCESS': "1 or ''",
                           u'JOBID': 'Job ID',
                           u'LABEL': 'Description of job',
                           u'LINODEID': 'Linode ID'}])
  def linode_job_list(self, request):
    """Returns the contents of the job queue."""
    pass

  @__api_request(optional=['isXen'],
                 returns=[{u'ISXEN': '0 or 1',
                           u'KERNELID': 'Kernel ID',
                           u'LABEL': 'kernel version string'}])
  def avail_kernels(self, request):
    """List available kernels."""
    pass

  @__api_request(returns=[{u'CREATE_DT': 'YYYY-MM-DD hh:mm:ss.0',
                           u'DISTRIBUTIONID': 'Distribution ID',
                           u'IS64BIT': '0 or 1',
                           u'LABEL': 'Description of image',
                           u'MINIMAGESIZE': 'MB required to deploy image'}])
  def avail_distributions(self, request):
    """Returns a list of available Linux Distributions."""
    pass

  @__api_request(returns=[{u'DATACENTERID': 'Datacenter ID',
                           u'LOCATION': 'City, ST, USA'}])
  def avail_datacenters(self, request):
    """Returns a list of Linode data center facilities."""
    pass

  @__api_request(returns=[{u'DISK': 'Maximum disk allocation (GB)',
                           u'LABEL': 'Name of plan',
                           u'PLANID': 'Plan ID',
                           u'PRICE': 'Monthly price (US dollars)',
                           u'HOURLY': 'Hourly price (US dollars)',
                           u'RAM': 'Maximum memory (MB)',
                           u'XFER': 'Allowed transfer (GB/mo)',
                           u'AVAIL': {u'Datacenter ID': 'Quantity'}}])
  def avail_linodeplans(self, request):
    """Returns a structure of Linode PlanIDs containing PlanIDs, and
    their availability in each datacenter.

    This plan is deprecated and will be removed in the future.
    """
    pass

  @__api_request(optional=['StackScriptID', 'DistributionID', 'DistributionVendor',
                            'keywords'],
                 returns=[{u'CREATE_DT': "'yyyy-mm-dd hh:mm:ss.0'",
                            u'DEPLOYMENTSACTIVE': 'The number of Scripts that Depend on this Script',
                            u'REV_DT': "'yyyy-mm-dd hh:mm:ss.0'",
                            u'DESCRIPTION': 'User defined description of the script',
                            u'SCRIPT': 'The actual source of the script',
                            u'ISPUBLIC': '0 or 1',
                            u'REV_NOTE': 'Comment regarding this revision',
                            u'LABEL': 'test',
                            u'LATESTREV': 'The number of the latest revision',
                            u'DEPLOYMENTSTOTAL': 'Number of times this script has been deployed',
                            u'STACKSCRIPTID': 'StackScript ID',
                            u'DISTRIBUTIONIDLIST': 'Comma separated list of distributions this script is available'}])
  def avail_stackscripts(self, request):
    """Returns a list of publicly available StackScript.
    """
    pass

  @__api_request(required=['username', 'password'],
                 returns={u'API_KEY': 'API key', u'USERNAME': 'Username'})
  def user_getapikey(self, request):
    """Given a username and password, returns the user's API key.  The
    key is remembered by this instance for future use.

    Please be advised that this will replace any previous key stored
    by the instance.
    """
    pass

  @__api_request(optional=['DomainID'],
                 returns=[{u'STATUS': 'Status flag',
                           u'RETRY_SEC': 'SOA Retry field',
                           u'DOMAIN': 'Domain name',
                           u'DOMAINID': 'Domain ID number',
                           u'DESCRIPTION': 'Description',
                           u'MASTER_IPS': 'Master nameservers (for slave zones)',
                           u'SOA_EMAIL': 'SOA e-mail address (user@domain)',
                           u'REFRESH_SEC': 'SOA Refresh field',
                           u'TYPE': 'Type of zone (master or slave)',
                           u'EXPIRE_SEC': 'SOA Expire field',
                           u'TTL_SEC': 'Default TTL'}])
  def domain_list(self, request):
    """Returns a list of domains associated with this account."""
    pass

  @__api_request(required=['DomainID'],
                 returns={u'DomainID': 'Domain ID number'})
  def domain_delete(self, request):
    """Deletes a given domain, by domainid."""
    pass

  @__api_request(required=['Domain', 'Type'],
                 optional=['SOA_Email', 'Refresh_sec', 'Retry_sec',
                           'Expire_sec', 'TTL_sec', 'status', 'master_ips'],
                 returns={u'DomainID': 'Domain ID number'})
  def domain_create(self, request):
    """Create a new domain.

    For type='master', SOA_Email is required.
    For type='slave', Master_IPs is required.

    Master_IPs is a comma or semicolon-delimited list of master IPs.
    Status is 1 (Active), 2 (EditMode), or 3 (Off).

    TTL values are rounded up to the nearest valid value:
    300, 3600, 7200, 14400, 28800, 57600, 86400, 172800,
    345600, 604800, 1209600, or 2419200 seconds.
    """
    pass

  @__api_request(required=['DomainID'],
                 optional=['Domain', 'Type', 'SOA_Email', 'Refresh_sec',
                           'Retry_sec', 'Expire_sec', 'TTL_sec', 'status',
                           'master_ips'],
                 returns={u'DomainID': 'Domain ID number'})
  def domain_update(self, request):
    """Updates the parameters of a given domain.

    TTL values are rounded up to the nearest valid value:
    300, 3600, 7200, 14400, 28800, 57600, 86400, 172800,
    345600, 604800, 1209600, or 2419200 seconds.
    """
    pass

  @__api_request(required=['DomainID'], optional=['ResourceID'],
                 returns=[{u'DOMAINID': 'Domain ID number',
                           u'PROTOCOL': 'Protocol (for SRV)',
                           u'TTL_SEC': 'TTL for record (0=default)',
                           u'WEIGHT': 'Weight (for SRV)',
                           u'NAME': 'The hostname or FQDN',
                           u'RESOURCEID': 'Resource ID number',
                           u'PRIORITY': 'Priority (for MX, SRV)',
                           u'TYPE': 'Resource Type (A, MX, etc)',
                           u'PORT': 'Port (for SRV)',
                           u'TARGET': 'The "right hand side" of the record'}])
  def domain_resource_list(self, request):
    """List the resources associated with a given DomainID."""
    pass

  @__api_request(required=['DomainID', 'Type'],
                 optional=['Name', 'Target', 'Priority', 'Weight',
                           'Port', 'Protocol', 'TTL_Sec'],
                 returns={u'ResourceID': 'Resource ID number'})
  def domain_resource_create(self, request):
    """Creates a resource within a given DomainID.

    TTL values are rounded up to the nearest valid value:
    300, 3600, 7200, 14400, 28800, 57600, 86400, 172800,
    345600, 604800, 1209600, or 2419200 seconds.

    For A and AAAA records, specify Target as "[remote_addr]" to
    use the source IP address of the request as the target, e.g.
    for updating pointers to dynamic IP addresses.
    """
    pass

  @__api_request(required=['DomainID', 'ResourceID'],
                 returns={u'ResourceID': 'Resource ID number'})
  def domain_resource_delete(self, request):
    """Deletes a Resource from a Domain."""
    pass

  @__api_request(required=['DomainID', 'ResourceID'],
                 optional=['Name', 'Target', 'Priority', 'Weight', 'Port',
                           'Protocol', 'TTL_Sec'],
                 returns={u'ResourceID': 'Resource ID number'})
  def domain_resource_update(self, request):
    """Updates a domain resource.

    TTL values are rounded up to the nearest valid value:
    300, 3600, 7200, 14400, 28800, 57600, 86400, 172800,
    345600, 604800, 1209600, or 2419200 seconds.

    For A and AAAA records, specify Target as "[remote_addr]" to
    use the source IP address of the request as the target, e.g.
    for updating pointers to dynamic IP addresses.
    """
    pass

  @__api_request(optional=['NodeBalancerID'],
                 returns=[{u'ADDRESS4': 'IPv4 IP address of the NodeBalancer',
                           u'ADDRESS6': 'IPv6 IP address of the NodeBalancer',
                           u'CLIENTCONNTHROTTLE': 'Allowed connections per second, per client IP',
                           u'HOSTNAME': 'NodeBalancer hostname',
                           u'LABEL': 'NodeBalancer label',
                           u'NODEBALANCERID': 'NodeBalancer ID',
                           u'STATUS': 'NodeBalancer status, as a string'}])
  def nodebalancer_list(self, request):
    """List information about your NodeBalancers."""
    pass

  @__api_request(required=['NodeBalancerID'],
                 optional=['Label',
                           'ClientConnThrottle'],
                 returns={u'NodeBalancerID': 'NodeBalancerID'})
  def nodebalancer_update(self, request):
    """Update information about, or settings for, a Nodebalancer.

    See nodebalancer_list.__doc__ for information on parameters.
    """
    pass

  @__api_request(required=['DatacenterID', 'PaymentTerm'],
                 returns={u'NodeBalancerID' : 'ID of the created NodeBalancer'})
  def nodebalancer_create(self, request):
    """Creates a NodeBalancer."""
    pass

  @__api_request(required=['NodeBalancerID'],
                 returns={u'NodeBalancerID': 'Destroyed NodeBalancer ID'})
  def nodebalancer_delete(self, request):
    """Immediately removes a NodeBalancer from your account and issues
       a pro-rated credit back to your account, if applicable."""
    pass

  @__api_request(required=['NodeBalancerID'],
                 optional=['ConfigID'],
                 returns=[{
                           u'ALGORITHM': 'Balancing algorithm.',
                           u'CHECK': 'Type of health check to perform.',
                           u'CHECK_ATTEMPTS': 'Number of failed probes allowed.',
                           u'CHECK_BODY': 'A regex against the expected result body.',
                           u'CHECK_INTERVAL': 'Seconds between health check probes.',
                           u'CHECK_PATH': 'The path of the health check request.',
                           u'CHECK_TIMEOUT': 'Seconds to wait before calling a failure.',
                           u'CONFIGID': 'ID of this config',
                           u'NODEBALANCERID': 'NodeBalancer ID.',
                           u'PORT': 'Port to bind to on public interface.',
                           u'PROTOCOL': 'The protocol to be used (tcp or http).',
                           u'STICKINESS': 'Session persistence.'}])
  def nodebalancer_config_list(self, request):
    """List information about your NodeBalancer Configs."""
    pass

  @__api_request(required=['ConfigID'],
                 optional=['Algorithm', 'check', 'check_attempts', 'check_body',
                           'check_interval', 'check_path', 'check_timeout',
                           'Port', 'Protocol', 'Stickiness'],
                 returns={u'ConfigID': 'The ConfigID you passed in the first place.'})
  def nodebalancer_config_update(self, request):
    """Update information about, or settings for, a Nodebalancer Config.

    See nodebalancer_config_list.__doc__ for information on parameters.
    """
    pass

  @__api_request(required=['NodeBalancerID'],
                 optional=['Algorithm', 'check', 'check_attempts', 'check_body',
                           'check_interval', 'check_path', 'check_timeout',
                           'Port', 'Protocol', 'Stickiness'],
                 returns={u'ConfigID': 'The ConfigID of the new Config.'})
  def nodebalancer_config_create(self, request):
    """Create a Nodebalancer Config.

    See nodebalancer_config_list.__doc__ for information on parameters.
    """
    pass

  @__api_request(required=['ConfigID'],
                 returns={u'ConfigID': 'Destroyed Config ID'})
  def nodebalancer_config_delete(self, request):
    """Deletes a NodeBalancer's Config."""
    pass

  @__api_request(required=['ConfigID'],
                 optional=['NodeID'],
                 returns=[{u'ADDRESS': 'Address:port combination for the node.',
                           u'CONFIGID': 'ConfigID of this node\'s config.',
                           u'LABEL': 'The backend node\'s label.',
                           u'MODE': 'Connection mode for this node.',
                           u'NODEBALANCERID': 'ID of this node\'s nodebalancer.',
                           u'NODEID': 'NodeID.',
                           u'STATUS': 'Node\'s status in the nodebalancer.',
                           u'WEIGHT': 'Load balancing weight.'}])
  def nodebalancer_node_list(self, request):
    """List information about your NodeBalancer Nodes."""
    pass

  @__api_request(required=['NodeID'],
                 optional=['Label', 'Address', 'Weight', 'Mode'],
                 returns={u'NodeID': 'The NodeID you passed in the first place.'})
  def nodebalancer_node_update(self, request):
    """Update information about, or settings for, a Nodebalancer Node.

    See nodebalancer_node_list.__doc__ for information on parameters.
    """
    pass

  @__api_request(required=['ConfigID', 'Label', 'Address'],
                 optional=['Weight', 'Mode'],
                 returns={u'NodeID': 'The NodeID of the new Node.'})
  def nodebalancer_node_create(self, request):
    """Create a Nodebalancer Node.

    See nodebalancer_node_list.__doc__ for information on parameters.
    """
    pass

  @__api_request(required=['NodeID'],
                 returns={u'NodeID': 'Destroyed Node ID'})
  def nodebalancer_node_delete(self, request):
    """Deletes a NodeBalancer Node."""
    pass

  @__api_request(optional=['StackScriptID'],
                 returns=[{u'CREATE_DT': "'yyyy-mm-dd hh:mm:ss.0'",
                            u'DEPLOYMENTSACTIVE': 'The number of Scripts that Depend on this Script',
                            u'REV_DT': "'yyyy-mm-dd hh:mm:ss.0'",
                            u'DESCRIPTION': 'User defined description of the script',
                            u'SCRIPT': 'The actual source of the script',
                            u'ISPUBLIC': '0 or 1',
                            u'REV_NOTE': 'Comment regarding this revision',
                            u'LABEL': 'test',
                            u'LATESTREV': 'The number of the latest revision',
                            u'DEPLOYMENTSTOTAL': 'Number of times this script has been deployed',
                            u'STACKSCRIPTID': 'StackScript ID',
                            u'DISTRIBUTIONIDLIST': 'Comma separated list of distributions this script is available'}])
  def stackscript_list(self, request):
    """List StackScripts you have created.
    """
    pass

  @__api_request(required=['Label', 'DistributionIDList', 'script'],
                 optional=['Description', 'isPublic', 'rev_note'],
                 returns={'STACKSCRIPTID' : 'ID of the created StackScript'})
  def stackscript_create(self, request):
    """Create a StackScript
    """
    pass

  @__api_request(required=['StackScriptID'],
                 optional=['Label', 'Description', 'DistributionIDList',
                           'isPublic', 'rev_note', 'script'])
  def stackscript_update(self, request):
    """Update an existing StackScript
    """
    pass

  @__api_request(required=['StackScriptID'])
  def stackscript_delete(self, request):
    """Delete an existing StackScript
    """
    pass

  @__api_request(returns=[{'Parameter' : 'Value'}])
  def test_echo(self, request):
    """Echo back any parameters
    """
    pass


########NEW FILE########
__FILENAME__ = deploy_abunch
#!/usr/bin/env python
"""
A Script to deploy a bunch of Linodes from a given stackscript

Copyright (c) 2011 Timothy J Fontaine <tjfontaine@gmail.com>

Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
"""

import json
import logging
import os.path
import re
import sys

from optparse import OptionParser
from getpass import getpass
from os import environ, linesep

import api

parser = OptionParser()
parser.add_option('-d', '--datacenter', dest="datacenter",
  help="datacenter to deploy to", metavar='DATACENTERID',
  action="store", type="int",
  )
parser.add_option('-c', '--count', dest="count",
  help="how many nodes to deploy", metavar="COUNT",
  action="store", type="int",
  )
parser.add_option('-s', '--stackscript', dest='stackscript',
  help='stackscript to deploy', metavar='STACKSCRIPTID',
  action='store', type='int',
  )
parser.add_option('-f', '--filename', dest='filename',
  help='filename with stackscript options', metavar='FILENAME',
  action='store',
  )
parser.add_option('-p', '--plan', dest='plan',
  help='linode plan that these nodes should be', metavar='PLANID',
  action='store', type='int',
  )
parser.add_option('-t', '--term', dest='term',
  help='payment term', metavar='TERM',
  action='store', type='choice', choices=('1','12','24'),
  )
parser.add_option('-D', '--distribution', dest='distribution',
  help='distribution to base deployment on', metavar='DISTRIBUTIONID',
  action='store', type='int',
  )
parser.add_option('-S', '--disksize', dest='disksize',
  help='size of the disk (in mb) that the stackscript should create',
  metavar='DISKSIZE', action='store', type='int',
  )
parser.add_option('-v', '--verbose', dest='verbose',
  help='enable debug logging in the api', action="store_true",
  default=False,
  )
parser.add_option('-k', '--kernel', dest='kernel',
  help='the kernel to assign to the configuration', metavar='KERNELID',
  action='store', type='int',
  )
parser.add_option('-B', '--boot', dest='boot',
  help='whether or not to issue a boot after a node is created',
  action='store_true', default=False,
  )

(options, args) = parser.parse_args()

if options.verbose:
  logging.basicConfig(level=logging.DEBUG)

try:
  if not options.count:
    raise Exception('Must specify how many nodes to create')

  if not options.datacenter:
    raise Exception('Must specify which datacenter to create nodes in')

  if not options.stackscript:
    raise Exception('Must specify which stackscript to deploy from')

  if not options.filename:
    raise Exception('Must specify filename of stackscript options')

  if not options.plan:
    raise Exception('Must specify the planid')

  if not options.term:
    raise Exception('Must speficy the payment term')

  if not options.distribution:
    raise Exception('Must speficy the distribution to deploy from')

  if not options.disksize:
    raise Exception('Must speficy the size of the disk to create')

  if not os.path.exists(options.filename):
    raise Exception('Options file must exist')

  if not options.kernel:
    raise Exception('Must specify a kernel to use for configuration')
except Exception, ex:
  sys.stderr.write(str(ex) + linesep)
  parser.print_help()
  sys.exit('All options are required (yes I see the contradiction)')

json_file = open(options.filename)

# Round trip to make sure we are valid
json_result = json.load(json_file)
stackscript_options = json.dumps(json_result)

if 'LINODE_API_KEY' in environ:
  api_key = environ['LINODE_API_KEY']
else:
  api_key = getpass('Enter API Key: ')

print 'Passwords  must contain at least two of these four character classes: lower case letters - upper case letters - numbers - punctuation'
root_pass = getpass('Enter the root password for all resulting nodes: ')
root_pass2 = getpass('Re-Enter the root password: ')

if root_pass != root_pass2:
  sys.exit('Passwords must match')

valid_pass = 0

if re.search(r'[A-Z]', root_pass):
  valid_pass += 1

if re.search(r'[a-z]', root_pass):
  valid_pass += 1

if re.search(r'[0-9]', root_pass):
  valid_pass += 1

if re.search(r'\W', root_pass):
  valid_pass += 1

if valid_pass < 2:
  sys.exit('Password too simple, only %d of 4 classes found' % (valid_pass))

linode_api = api.Api(api_key, batching=True)

needFlush = False

created_linodes = []

def deploy_set():
  linode_order = []
  for r in linode_api.batchFlush():
    # TODO XXX FIXME handle error states
    linodeid = r['DATA']['LinodeID']
    created_linodes.append(linodeid)
    linode_order.append(linodeid)
    linode_api.linode_disk_createfromstackscript(
      LinodeID=linodeid,
      StackScriptID=options.stackscript,
      StackScriptUDFResponses=stackscript_options,
      DistributionID=options.distribution,
      Label='From stackscript %d' % (options.stackscript),
      Size=options.disksize,
      rootPass=root_pass,
    )
  to_boot = []
  for r in linode_api.batchFlush():
    # TODO XXX FIXME handle error states
    linodeid = linode_order.pop(0)
    diskid = [str(r['DATA']['DiskID'])]
    for i in range(8): diskid.append('')
    linode_api.linode_config_create(
      LinodeID=linodeid,
      KernelID=options.kernel,
      Label='From stackscript %d' % (options.stackscript),
      DiskList=','.join(diskid),
    )
    if options.boot:
      to_boot.append(linodeid)
  linode_api.batchFlush()

  for l in to_boot:
    linode_api.linode_boot(LinodeID=l)

  if len(to_boot):
    linode_api.batchFlush()

for i in range(options.count):
  if needFlush and i % 25 == 0:
    needFlush = False
    deploy_set()
    
  linode_api.linode_create(
        DatacenterID=options.datacenter,
        PlanID=options.plan,
        PaymentTerm=options.term,
  )
  needFlush = True

if needFlush:
  needFlush = False
  deploy_set()

print 'List of created Linodes:'
print '[%s]' % (', '.join([str(l) for l in created_linodes]))

########NEW FILE########
__FILENAME__ = fields
from datetime import datetime

class Field(object):
  to_py = lambda self, value: value
  to_linode = to_py

  def __init__(self, field):
    self.field = field

class IntField(Field):
  def to_py(self, value):
    if value is not None and value != '':
      return int(value)

  to_linode = to_py

class FloatField(Field):
  def to_py(self, value):
    if value is not None:
      return float(value)

  to_linode = to_py

class CharField(Field):
  to_py = lambda self, value: str(value)
  to_linode = to_py

class BoolField(Field):
  def to_py(self, value):
    if value in (1, '1'): return True
    else: return False

  def to_linode(self, value):
    if value: return 1
    else: return 0

class ChoiceField(Field):
  to_py = lambda self, value: value

  def __init__(self, field, choices=[]):
    Field.__init__(self, field)
    self.choices = choices

  def to_linode(self, value):
    if value in self.choices:
      return value
    else:
      raise AttributeError

class ListField(Field):
  def __init__(self, field, type=Field(''), delim=','):
    Field.__init__(self, field)
    self.__type=type
    self.__delim=delim

  def to_linode(self, value):
    return self.__delim.join([str(self.__type.to_linode(v)) for v in value])

  def to_py(self, value):
    return [self.__type.to_py(v) for v in value.split(self.__delim) if v != '']

class DateTimeField(Field):
  to_py = lambda self, value: datetime.strptime(value, '%Y-%m-%d %H:%M:%S.0')
  to_linode = lambda self, value: value.strftime('%Y-%m-%d %H:%M:%S.0')

class ForeignField(Field):
  def __init__(self, field):
    self.field = field.primary_key
    self.__model = field

  def to_py(self, value):
    return self.__model.get(id=value)

  def to_linode(self, value):
    if isinstance(value, int):
      return value
    else:
      return value.id

########NEW FILE########
__FILENAME__ = methodcheck
#!/usr/bin/python
"""
A quick script to verify that api.py is in sync with Linode's
published list of methods.

Copyright (c) 2010 Josh Wright <jshwright@gmail.com>
Copyright (c) 2009 Ryan Tucker <rtucker@gmail.com>

Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
"""

#The list of subsections found in the API documentation. This should
#probably be discovered automatically in the future
api_subsections = ('linode', 'nodebalancer', 'stackscript', 'dns', 'utility')

import api
import re
import itertools
from HTMLParser import HTMLParser
from urllib import unquote
from urllib2 import urlopen

class SubsectionParser(HTMLParser):
    base_url = 'http://www.linode.com/api/'

    def __init__(self, subsection):
        HTMLParser.__init__(self)
        self.subsection_re = re.compile('/api/%s/(.*)$' % subsection)
        self.methods = []
        url = self.base_url + subsection
        req = urlopen(url)
        self.feed(req.read())

    def handle_starttag(self, tag, attrs):
        if tag == 'a' and attrs:
            attr_dict = dict(attrs)
            match = self.subsection_re.match(attr_dict.get('href', ''))
            if match:
                self.methods.append(unquote(match.group(1)).replace('.','_'))

local_methods = api.Api.valid_commands()
remote_methods = list(itertools.chain(*[SubsectionParser(subsection).methods for subsection in api_subsections]))

# Cross-check!
for i in local_methods:
    if i not in remote_methods:
        print('REMOTE Missing: ' + i)
for i in remote_methods:
    if i not in local_methods:
        print('LOCAL Missing:  ' + i)


########NEW FILE########
__FILENAME__ = oop
# vim:ts=2:sw=2:expandtab
"""
A Python library to provide level-level Linode API interaction.

Copyright (c) 2010 Timothy J Fontaine <tjfontaine@gmail.com>
Copyright (c) 2010 Josh Wright <jshwright@gmail.com>
Copyright (c) 2010 Ryan Tucker <rtucker@gmail.com>

Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
"""

import logging

from os import environ

from api import Api, LowerCaseDict
from fields import *

_id_cache = {}

ActiveContext = None

class LinodeObject(object):
  fields = None
  update_method = None
  create_method = None
  primary_key   = None
  list_method   = None

  def __init__(self, entry={}):
    entry = dict([(str(k), v) for k,v in entry.items()])
    self.__entry = LowerCaseDict(entry)

  def __getattr__(self, name):
    name = name.replace('_LinodeObject', '')
    if name == '__entry':
      return self.__dict__[name]
    elif name not in self.fields:
      raise AttributeError
    else:
      f= self.fields[name]
      value = None
      if f.field.lower() in self.__entry:
        value = self.__entry[f.field.lower()]
      return f.to_py(value)

  def __setattr__(self, name, value):
    name = name.replace('_LinodeObject', '')
    if name == '__entry':
      object.__setattr__(self, name, value)
    elif name not in self.fields:
      raise AttributeError
    else:
      f = self.fields[name]
      self.__entry[f.field.lower()] = f.to_linode(value)

  def __str__(self):
    s = []
    for k,v in self.fields.items():
      if v.field in self.__entry:
        value = v.to_py(self.__entry[v.field])
        if isinstance(value, list):
          s.append('%s: [%s]' % (k, ', '.join([str(x) for x in value])))
        else:
          s.append('%s: %s' % (k, str(value)))
    return '['+', '.join(s)+']'

  def save(self):
    if self.id:
      self.update()
    else:
      self.id = self.create_method(ActiveContext, **self.__entry)[self.primary_key]

  def update(self):
    self.update_method(ActiveContext, **self.__entry)

  @classmethod
  def __resolve_kwargs(self, kw):
    kwargs = {}
    for k, v in kw.items():
      f = self.fields[k.lower()]
      kwargs[f.field] = f.to_linode(v)
    return kwargs

  @classmethod
  def list(self, **kw):
    kwargs = self.__resolve_kwargs(kw)

    """
    if self not in _id_cache:
      _id_cache[self] = {}
    """

    for l in self.list_method(ActiveContext, **kwargs):
      l = LowerCaseDict(l)
      o = self(l)
      o.cache_add()
      yield o

  @classmethod
  def get(self, **kw):
    kwargs = self.__resolve_kwargs(kw)

    """
    if self not in _id_cache:
      _id_cache[self] = {}
    """

    result = None
    """
    for k,v in _id_cache[self].items():
      found = True
      for i, j in kwargs.items():
        if i not in v or v[i] != j:
          found = False
          break
      if not found:
        continue
      else:
        result = v
        break
    """


    if not result:
      result = LowerCaseDict(self.list_method(ActiveContext, **kwargs)[0])
      o = self(result)
      o.cache_add()
      return o
    else:
      return self(result)

  def cache_remove(self):
    pass
    """
    del _id_cache[self.__class__][self.__entry[self.primary_key]]
    """

  def cache_add(self):
    pass
    """
    key = self.__class__
    if key not in _id_cache:
      _id_cache[key] = {}

    _id_cache[key][self.__entry[self.primary_key]] = self.__entry
    """

class Datacenter(LinodeObject):
  fields = {
    'id'        : IntField('DatacenterID'),
    'location'  : CharField('Location'),
    'name'      : CharField('Location'),
  }

  list_method = Api.avail_datacenters
  primary_key =  'DatacenterID'

class LinodePlan(LinodeObject):
  fields = {
    'id'      : IntField('PlanID'),
    'label'   : CharField('Label'),
    'price'   : FloatField('Price'),
    'ram'     : IntField('Ram'),
    'xfer'    : IntField('Xfer'),
  }

  list_method = Api.avail_linodeplans
  primary_key = 'PlanID'

class Linode(LinodeObject):
  fields = {
    'id'                : IntField('LinodeID'),
    'datacenter'        : ForeignField(Datacenter),
    'plan'              : ForeignField(LinodePlan),
    'term'              : ChoiceField('PaymentTerm', choices=[1, 12, 24]),
    'name'              : CharField('Label'),
    'label'             : CharField('Label'),
    'group'             : Field('lpm_displayGroup'),
    'cpu_enabled'       : BoolField('Alert_cpu_enabled'),
    'cpu_threshold'     : IntField('Alert_cpu_threshold'),
    'diskio_enabled'    : BoolField('Alert_diskio_enabled'),
    'diskio_threshold'  : IntField('Alert_diskio_enabled'),
    'bwin_enabled'      : BoolField('Alert_bwin_enabled'),
    'bwin_threshold'    : IntField('Alert_bwin_threshold'),
    'bwout_enabled'     : BoolField('Alert_bwout_enabeld'),
    'bwout_threshold'   : IntField('Alert_bwout_threshold'),
    'bwquota_enabled'   : BoolField('Alert_bwquota_enabled'),
    'bwquota_threshold' : IntField('Alert_bwquota_threshold'),
    'backup_window'     : IntField('backupWindow'),
    'backup_weekly_day' : ChoiceField('backupWeeklyDay', choices=list(range(6))),
    'watchdog'          : BoolField('watchdog'),
    'total_ram'         : IntField('TotalRam'),
    'total_diskspace'   : IntField('TotalHD'),
    'total_xfer'        : IntField('TotalXfer'),
    'status'            : IntField('Status'),
  }

  update_method = Api.linode_update
  create_method = Api.linode_create
  primary_key   = 'LinodeID'
  list_method   = Api.linode_list

  def boot(self):
    ### TODO XXX FIXME return LinodeJob
    return ActiveContext.linode_boot(linodeid=self.id)['JobID']

  def shutdown(self):
    ### TODO XXX FIXME return LinodeJob
    return ActiveContext.linode_shutdown(linodeid=self.id)['JobID']

  def reboot(self):
    ### TODO XXX FIXME return LinodeJob
    return ActiveContext.linode_reboot(linodeid=self.id)['JobID']

  def delete(self):
    ActiveContext.linode_delete(linodeid=self.id)
    self.cache_remove()

class LinodeJob(LinodeObject):
  fields = {
    'id'            : IntField('JobID'),
    'linode'        : ForeignField(Linode),
    'label'         : CharField('Label'),
    'name'          : CharField('Label'),
    'entered'       : DateTimeField('ENTERED_DT'),
    'started'       : DateTimeField('HOST_START_DT'),
    'finished'      : DateTimeField('HOST_FINISH_DT'),
    'message'       : CharField('HOST_MESSAGE'),
    'duration'      : IntField('DURATION'),
    'success'       : BoolField('HOST_SUCCESS'),
    'pending_only'  : BoolField('PendingOnly'),
  }

  list_method = Api.linode_job_list
  primary_key = 'JobID'

class Distribution(LinodeObject):
  fields = {
    'id'        : IntField('DistributionID'),
    'label'     : CharField('Label'),
    'name'      : CharField('Label'),
    'min'       : IntField('MinImageSize'),
    '64bit'     : BoolField('Is64Bit'),
    'created'   : DateTimeField('CREATE_DT'),
  }

  list_method = Api.avail_distributions
  primary_key = 'DistributionID'

class LinodeDisk(LinodeObject):
  fields = {
    'id'      : IntField('DiskID'),
    'linode'  : ForeignField(Linode),
    'type'    : ChoiceField('Type', choices=['ext3', 'swap', 'raw']),
    'size'    : IntField('Size'),
    'name'    : CharField('Label'),
    'label'   : CharField('Label'),
    'status'  : IntField('Status'),
    'created' : DateTimeField('Create_DT'),
    'updated' : DateTimeField('Update_DT'),
    'readonly': BoolField('IsReadonly'),
  }

  update_method = Api.linode_disk_update
  create_method = Api.linode_disk_create
  primary_key   = 'DiskID'
  list_method   = Api.linode_disk_list

  def duplicate(self):
    ret = ActiveContext.linode_disk_duplicate(linodeid=self.linode.id, diskid=self.id)
    disk = LinodeDisk.get(linode=self.linode, id=ret['DiskID'])
    job = LinodeJob(linode=self.linode, id=ret['JobID'])
    return (disk, job)

  def resize(self, size):
    ret = ActiveContext.linode_disk_resize(linodeid=self.linode.id, diskid=self.id, size=size)
    return LinodeJob.get(linode=self.linode, id=ret['JobID'])

  def delete(self):
    ret = ActiveContext.linode_disk_delete(linodeid=self.linode.id, diskid=self.id)
    job = LinodeJob.get(linode=self.linode, id=ret['JobID'])
    self.cache_remove()
    return job

  @classmethod
  def create_from_distribution(self, linode, distribution, root_pass, label, size, ssh_key=None):
    l = ForeignField(Linode).to_linode(linode)
    d = ForeignField(Distribution).to_linode(distribution)
    ret = ActiveContext.linode_disk_createfromdistribution(linodeid=l, distributionid=d,
            rootpass=root_pass, label=label, size=size, rootsshkey=ssh_key)
    disk = self.get(id=ret['DiskID'], linode=linode)
    job = LinodeJob(id=ret['JobID'], linode=linode)
    return (disk, job)

class Kernel(LinodeObject):
  fields = {
    'id'    : IntField('KernelID'),
    'label' : CharField('Label'),
    'name'  : CharField('Label'),
    'is_xen': BoolField('IsXen'),
  }

  list_method = Api.avail_kernels
  primary_key = 'KernelID'

class LinodeConfig(LinodeObject):
  fields = {
    'id'                  : IntField('ConfigID'),
    'linode'              : ForeignField(Linode),
    'kernel'              : ForeignField(Kernel),
    'disklist'            : ListField('DiskList', type=ForeignField(LinodeDisk)),
    'name'                : CharField('Label'),
    'label'               : CharField('Label'),
    'comments'            : CharField('Comments'),
    'ram_limit'           : IntField('RAMLimit'),
    'root_device_num'     : IntField('RootDeviceNum'),
    'root_device_custom'  : IntField('RootDeviceCustom'),
    'root_device_readonly': BoolField('RootDeviceRO'),
    'disable_updatedb'    : BoolField('helper_disableUpdateDB'),
    'helper_xen'          : BoolField('helper_xen'),
    'helper_depmod'       : BoolField('helper_depmod'),
  }

  update_method = Api.linode_config_update
  create_method = Api.linode_config_create
  primary_key   = 'ConfigID'
  list_method   = Api.linode_config_list

  def delete(self):
    self.cache_remove()
    ActiveContext.linode_config_delete(linodeid=self.linode.id, configid=self.id)

class LinodeIP(LinodeObject):
  fields = {
    'id'        : IntField('IPAddressID'),
    'linode'    : ForeignField(Linode),
    'address'   : CharField('IPADDRESS'),
    'is_public' : BoolField('ISPUBLIC'),
    'rdns'      : CharField('RDNS_NAME'),
  }

  list_method = Api.linode_ip_list
  primary_key = 'IPAddressID'

class Domain(LinodeObject):
  fields = {
    'id'        : IntField('DomainID'),
    'domain'    : CharField('Domain'),
    'name'      : CharField('Domain'),
    'type'      : ChoiceField('Type', choices=['master', 'slave']),
    'soa_email' : CharField('SOA_Email'),
    'refresh'   : IntField('Refresh_sec'),
    'retry'     : IntField('Retry_sec'),
    'expire'    : IntField('Expire_sec'),
    'ttl'       : IntField('TTL_sec'),
    'status'    : ChoiceField('Status', choices=['0', '1', '2']),
    'master_ips': ListField('master_ips', type=CharField('master_ips')),
  }

  update_method = Api.domain_update
  create_method = Api.domain_create
  primary_key   = 'DomainID'
  list_method   = Api.domain_list

  STATUS_OFF  = 0
  STATUS_ON   = 1
  STATUS_EDIT = 2

  def delete(self):
    self.cache_remove()
    ActiveContext.domain_delete(domainid=self.id)

class Resource(LinodeObject):
  fields = {
    'id'        : IntField('ResourceID'),
    'domain'    : ForeignField(Domain),
    'name'      : CharField('Name'),
    'type'      : CharField('Type'),
    'target'    : CharField('Target'),
    'priority'  : IntField('Priority'),
    'weight'    : IntField('Weight'),
    'port'      : IntField('Port'),
    'protocol'  : CharField('Protocol'),
    'ttl'       : IntField('TTL_sec'),
  }

  update_method = Api.domain_resource_update
  create_method = Api.domain_resource_create
  primary_key   = 'ResourceID'
  list_method   = Api.domain_resource_list

  def delete(self):
    self.cache_remove()
    ActiveContext.domain_resource_delete(domainid=self.domain.id, resourceid=self.id)

  @classmethod
  def list_by_type(self, domain, only=None):
    resources = self.list(domain=domain)
    r_by_type = {
      'A'     : [],
      'CNAME' : [],
      'MX'    : [],
      'SRV'   : [],
      'TXT'   : [],
    }

    for r in resources: r_by_type[r.type.upper()].append(r)

    if only:
      return r_by_type[only.upper()]
    else:
      return r_by_type

def _iter_class(self, results):
  _id_cache[self] = {}
  results = LowerCaseDict(results)

  d = results['data']
  for i in d: self(i).cache_add()

def fill_cache():
  _api.batching = True
  _api.linode_list()
  _api.avail_linodeplans()
  _api.avail_datacenters()
  _api.avail_distributions()
  _api.avail_kernels()
  _api.domain_list()
  ret = _api.batchFlush()

  for i,k in enumerate([Linode, LinodePlan, Datacenter, Distribution, Kernel, Domain]):
    _iter_class(k, ret[i])

  for k in _id_cache[Linode].keys():
    _api.linode_config_list(linodeid=k)
    _api.linode_disk_list(linodeid=k)

  for k in _id_cache[Domain].keys():
    _api.domain_resource_list(domainid=k)

  ret = _api.batchFlush()

  for r in ret:
    r = LowerCaseDict(r)
    if r['action'] == 'linode.config.list':
      _iter_class(LinodeConfig, r)
    elif r['action'] == 'linode.disk.list':
      _iter_class(LinodeDisk, r)
    elif r['action'] == 'domain.resource.list':
      _iter_class(Resource, r)

  _api.batching = False

def setup_logging():
  logging.basicConfig(level=logging.DEBUG)

########NEW FILE########
__FILENAME__ = shell
#!/usr/bin/env python
# vim:ts=2:sw=2:expandtab
"""
A Python shell to interact with the Linode API

Copyright (c) 2008 Timothy J Fontaine <tjfontaine@gmail.com>

Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
"""

import api
import code
import decimal
import rlcompleter
import readline
import atexit
import os
try:
  import json
except:
  import simplejson as json

class DecimalEncoder(json.JSONEncoder):
  """Handle Decimal types when producing JSON.

  Hat tip: http://stackoverflow.com/questions/4019856/decimal-to-json
  """
  def default(self, o):
    if isinstance(o, decimal.Decimal):
      return float(o)
    return json.JSONEncoder.default(self, o)

class LinodeConsole(code.InteractiveConsole):
  def __init__(self, locals=None, filename="<console>",
      histfile=os.path.expanduser("~/.linode-console-history")):
    code.InteractiveConsole.__init__(self)
    self.init_history(histfile)
    
  def init_history(self, histfile):
    if hasattr(readline, "read_history_file"):
      try:
        readline.read_history_file(histfile)
      except IOError:
        pass
        atexit.register(self.save_history, histfile)

  def save_history(self, histfile):
    readline.write_history_file(histfile)

class LinodeComplete(rlcompleter.Completer):
  def complete(self, text, state):
    result = rlcompleter.Completer.complete(self, text, state)
    if result and result.find('__') > -1:
      result = ''
    return result


if __name__ == "__main__":
  from getpass import getpass
  from os import environ
  import getopt, sys
  if 'LINODE_API_KEY' in environ:
    key = environ['LINODE_API_KEY']
  else:
    key = getpass('Enter API Key: ')

  linode = api.Api(key)

  def usage(all=False):
    print('shell.py --<api action> [--parameter1=value [--parameter2=value [...]]]')
    print('Valid Actions')
    for a in sorted(linode.valid_commands()):
      print('\t--'+a)
    if all:
      print('Valid Named Parameters')
      for a in sorted(linode.valid_params()):
        print('\t--'+a+'=')
    else:
      print('To see valid parameters use: --help --all')

  options = []
  for arg in linode.valid_params():
    options.append(arg+'=')

  for arg in linode.valid_commands():
    options.append(arg)
  options.append('help')
  options.append('all')

  if len(sys.argv[1:]) > 0:
    try:
      optlist, args = getopt.getopt(sys.argv[1:], '', options)
    except getopt.GetoptError, err:
      print(str(err))
      usage()
      sys.exit(2)

    command = optlist[0][0].replace('--', '')

    params = {}
    for param,value in optlist[1:]:
      params[param.replace('--', '')] = value

    if command == 'help' or 'help' in params:
      usage('all' in params)
      sys.exit(2)

    if hasattr(linode, command):
      func = getattr(linode, command)
      try:
        print(json.dumps(func(**params), indent=2, cls=DecimalEncoder))
      except api.MissingRequiredArgument, mra:
        print('Missing option --%s' % mra.value.lower())
        print('')
        usage()
        sys.exit(2)
    else:
      if not command == 'help':
        print('Invalid action '+optlist[0][0].lower())

      usage()
      sys.exit(2)
  else:
    console = LinodeConsole()

    console.runcode('import readline,rlcompleter,api,shell,json')
    console.runcode('readline.parse_and_bind("tab: complete")')
    console.runcode('readline.set_completer(shell.LinodeComplete().complete)')
    console.runcode('def pp(text=None): print(json.dumps(text, indent=2, cls=shell.DecimalEncoder))')
    console.locals.update({'linode':linode})
    console.interact()

########NEW FILE########
__FILENAME__ = tests
import api
import unittest
import os
from getpass import getpass

class ApiTest(unittest.TestCase):

    def setUp(self):
        self.linode = api.Api(os.environ['LINODE_API_KEY'])

    def testAvailLinodeplans(self):
        available_plans = self.linode.avail_linodeplans()
        self.assertTrue(isinstance(available_plans, list))

    def testEcho(self):
        test_parameters = {'FOO': 'bar', 'FIZZ': 'buzz'}
        response = self.linode.test_echo(**test_parameters)
        self.assertTrue('FOO' in response)
        self.assertTrue('FIZZ' in response)
        self.assertEqual(test_parameters['FOO'], response['FOO'])
        self.assertEqual(test_parameters['FIZZ'], response['FIZZ'])

if __name__ == "__main__":
    if 'LINODE_API_KEY' not in os.environ:
        os.environ['LINODE_API_KEY'] = getpass('Enter API Key: ')
    unittest.main()

########NEW FILE########
__FILENAME__ = VEpycurl
"""
Copyright (C) 2009, Kenneth East
 
Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:
 
The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.
 
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
"""
 
#
# module for VEpycurl - the Very Easy interface to pycurl
#
 
from StringIO import StringIO
import urllib
import pycurl
import sys
import os
 
class VEpycurl() :
    """
    A VERY EASY interface to pycurl, v1.0
    Tested on 22Feb09 with python 2.5.1, py25-curl 7.19.0, libcurl/7.19.2, OS-X 10.5.6
    """
 
    def __init__(self,
                 userAgent      = 'Mozilla/4.0 (compatible; MSIE 8.0)',
                 followLocation = 1,            # follow redirects?
                 autoReferer    = 1,            # allow 'referer' to be set normally?
                 verifySSL      = 0,            # tell SSL to verify IDs?
                 useCookies     = True,         # will hold all pycurl cookies
                 useSOCKS       = False,        # use SOCKS5 proxy?
                 proxy          = 'localhost',  # SOCKS host
                 proxyPort      = 8080,         # SOCKS port
                 proxyType      = 5,            # SOCKS protocol
                 verbose        = False,
                 debug          = False,
                 ) :
        self.followLocation = followLocation
        self.autoReferer    = autoReferer
        self.verifySSL      = verifySSL
        self.useCookies     = useCookies
        self.useSOCKS       = useSOCKS
        self.proxy          = proxy
        self.proxyPort      = proxyPort
        self.proxyType      = proxyType
        self.pco = pycurl.Curl()
        self.pco.setopt(pycurl.USERAGENT,      userAgent)
        self.pco.setopt(pycurl.FOLLOWLOCATION, followLocation)
        self.pco.setopt(pycurl.MAXREDIRS,      20)
        self.pco.setopt(pycurl.CONNECTTIMEOUT, 30)
        self.pco.setopt(pycurl.AUTOREFERER,    autoReferer)
        # SSL verification (True/False)
        self.pco.setopt(pycurl.SSL_VERIFYPEER, verifySSL)
        self.pco.setopt(pycurl.SSL_VERIFYHOST, verifySSL)
        if useCookies == True :
            cjf = os.tmpfile() # potential security risk here; see python documentation
            self.pco.setopt(pycurl.COOKIEFILE, cjf.name)
            self.pco.setopt(pycurl.COOKIEJAR,  cjf.name)
        if useSOCKS :
            # if you wish to use SOCKS, it is configured through these parms
            self.pco.setopt(pycurl.PROXY,     proxy)
            self.pco.setopt(pycurl.PROXYPORT, proxyPort)
            self.pco.setopt(pycurl.PROXYTYPE, proxyType)
        if verbose :
            self.pco.setopt(pycurl.VERBOSE, 1)
        if debug :
            print 'PyCurl version info:'
            print pycurl.version_info()
            print
            self.pco.setopt(pycurl.DEBUGFUNCTION, self.debug)
        return
 
    def perform(self, url, fields=None, headers=None) :
        if fields :
            # This is a POST and we have fields to handle
            fields = urllib.urlencode(fields)
            self.pco.setopt(pycurl.POST,       1)
            self.pco.setopt(pycurl.POSTFIELDS, fields)
        else :
            # This is a GET, and we do nothing with fields
            pass
        pageContents = StringIO()
        self.pco.setopt(pycurl.WRITEFUNCTION,  pageContents.write)
        self.pco.setopt(pycurl.URL, url)
        if headers :
            self.pco.setopt(pycurl.HTTPHEADER, headers)
        self.pco.perform()
        self.pco.close()
        self.pc = pageContents
        return
 
    def results(self) :
        # return the page contents that were received in the most recent perform()
        # self.pc is a StringIO object
        self.pc.seek(0)
        return self.pc
 
    def debug(self, debug_type, debug_msg) :
        print 'debug(%d): %s' % (debug_type, debug_msg)
        return
 
try:
    # only call this once in a process.  see libcurl docs for more info.
    pycurl.global_init(pycurl.GLOBAL_ALL)
except:
    print 'Fatal error: call to pycurl.global_init() failed for some reason'
    sys.exit(1)

########NEW FILE########
