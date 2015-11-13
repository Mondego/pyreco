__FILENAME__ = api
import os
import sqlite3
from . import config

'''
api.py -  vFeed - Open Source Cross-linked and Aggregated Local Vulnerability Database

'''
class vFeed(object):

    def __init__(self, cveID):

        self.vfeed_db = config.database['vfeed_db']
        self.vfeed_db_url = config.database['primary']['url']
        self.oval_url = config.gbVariables['oval_url']
        self.edb_url = config.gbVariables['edb_url']
        self.bid_url = config.gbVariables['bid_url']
        
        self.cveID = cveID.upper()
        self._check_env(self.vfeed_db)
        self._db_init()
        self._vrfy_cve()

    def _vrfy_cve(self):
        try:
            self.cur.execute('SELECT * FROM nvd_db WHERE cveid=?', self.query)
            self.data = self.cur.fetchone()
            if self.data is None:
                print '[warning] Entry %s is missed from vFeed Database' % self.cveID
                print '[hint] Update your local vfeed.db'
                exit(0)
        except Exception, e:
            print '[exception]:', e
            exit(0)

        return self.data

    def _check_env(self, file):

        if not os.path.isfile(file):
            print '[error] ' + file + ' is missing.'
            print '[db_error] try python vfeedcli.py update '
            exit(0)

    def _db_init(self):

        try:
            self.conn = sqlite3.connect(self.vfeed_db)
            self.cur = self.conn.cursor()
            self.query = (self.cveID,)
            return (self.cur, self.query)
        except Exception, e:
            print '[error] something occurred while opening the database', self.vfeed_db
            print '[exception]:', e
            exit(0)

    def get_cve(self):
        '''
            CVE verification and basic information extraction
            Returning : dictionary of data (published, modified, description)
        '''

        self.cveInfo = {}

        if self.data:
            self.cveInfo['summary'] = str(self.data[3])
            self.cveInfo['published'] = str(self.data[1])
            self.cveInfo['modified'] = str(self.data[2])

        return self.cveInfo

    def get_cvss(self):
        '''
            CVSS scores extraction
            Returning : dictionary Base, Impact and  Exploit Scores
        '''
        self._vrfy_cve()
        self.cvssScore = {}

        if self.data:
            self.cvssScore['base'] = str(self.data[4])
            self.cvssScore['impact'] = str(self.data[5])
            self.cvssScore['exploit'] = str(self.data[6])
            self.cvssScore['access_vector'] = str(self.data[7])
            self.cvssScore['access_complexity'] = str(self.data[8])
            self.cvssScore['authentication'] = str(self.data[9])      
            self.cvssScore['confidentiality_impact'] = str(self.data[10])
            self.cvssScore['integrity_impact'] = str(self.data[11])
            self.cvssScore['availability_impact'] = str(self.data[12])

        return self.cvssScore

    def get_refs(self):
        '''
        Returning:  CVE references links and their IDs as dictionay
        '''
        self.cnt = 0
        self.cveReferences = {}
        self.cur.execute(
            'SELECT * FROM cve_reference WHERE cveid=?', self.query)

        for self.data in self.cur.fetchall():
            self.cveReferences[self.cnt] = {
                'id': str(self.data[0]),
                'link': str(self.data[1]),
            }
            self.cnt += 1
        return self.cveReferences

    def get_osvdb(self):
        '''
        Returning:  OSVDB (Open Sourced Vulnerability Database) ids as dictionay
        http://www.osvdb.org/
        '''
        self.cnt = 0
        self.OSVDB_id = {}
        self.cur.execute(
            'SELECT * FROM map_cve_osvdb WHERE cveid=?', self.query)

        for self.data in self.cur.fetchall():
            self.OSVDB_id[self.cnt] = {
                'id': str(self.data[0]),
            }
            self.cnt += 1
        return self.OSVDB_id        
    
    def get_scip(self):
        '''
        Returning:  SCIP ids and links as dictionay
        http://www.scip.ch
        '''
        self.cnt = 0
        self.SCIP_id = {}
        self.cur.execute(
            'SELECT * FROM map_cve_scip WHERE cveid=?', self.query)

        for self.data in self.cur.fetchall():
            self.SCIP_id[self.cnt] = {
                'id': str(self.data[0]),
                'link': str(self.data[1]),
            }
            self.cnt += 1
        return self.SCIP_id    

    def get_certvn(self):
        '''
        Returning:  CERT VU ids and links as dictionay
        http://www.cert.org/kb/
        '''
        self.cnt = 0
        self.CERTVN_id = {}
        self.cur.execute(
            'SELECT * FROM map_cve_certvn WHERE cveid=?', self.query)

        for self.data in self.cur.fetchall():
            self.CERTVN_id[self.cnt] = {
                'id': str(self.data[0]),
                'link': str(self.data[1]),
            }
            self.cnt += 1
        return self.CERTVN_id    

    def get_iavm(self):
        '''
        Returning:  IAVM Ids, DISA keys and title as dictionay
        IAVM stands for Information Assurance Vulnerability Management
        http://www.prim.osd.mil/cap/iavm_req.html?p=1.1.1.1.3
        '''
        self.cnt = 0
        self.IAVM_id = {}
        self.cur.execute(
            'SELECT * FROM map_cve_iavm WHERE cveid=?', self.query)

        for self.data in self.cur.fetchall():
            self.IAVM_id[self.cnt] = {
                'id': str(self.data[0]),
                'key': str(self.data[1]),
                'title': str(self.data[2]),
            }
            self.cnt += 1
        return self.IAVM_id   

    def get_cwe(self):
        '''
        Returning:  CWE references as dictionary
        '''
        self.cnt = 0
        self.cnt2 = 0
        self.CWE_id = {}
        
        self.cur.execute('SELECT * FROM cve_cwe WHERE cveid=?', self.query)
        
        
        for self.data in self.cur.fetchall():
            self.cwe_id = str(self.data[0])
            self.query2 = (self.cwe_id,)
            self.cur.execute('SELECT * FROM cwe_db WHERE cweid=?', self.query2)
                        
            for self.data2 in self.cur.fetchall():
                self.CWE_id[self.cnt] = {
                   'id': self.cwe_id,
                   'title' : str(self.data2[1]),
                }

            self.cnt += 1

        return self.CWE_id

    def get_capec(self):
        '''
        Returning:  CAPEC references as dictionary
        '''
        
        self.cnt = 0
        self.CWE_id = self.get_cwe()
        self.CAPEC_id = {}
        
        if self.CWE_id:
            for i in range(0, len(self.CWE_id)):
                self.query2 = (self.CWE_id[i]['id'],)
                self.cur.execute('SELECT * FROM cwe_capec WHERE cweid=?', self.query2)
                
                for self.data2 in self.cur.fetchall():                    
                    self.cwe_id = self.CWE_id[i]['id']
                    
                    self.CAPEC_id[self.cnt] = {
                       'cwe' : self.cwe_id,
                       'id': str(self.data2[0]),
                    }
                    
                    self.cnt += 1
        
        return self.CAPEC_id


    def get_category(self):
        '''
        Returning:  CWE Weakness Categories (as Top 2011 ....) references as dictionary
        '''       
        self.cnt = 0
        self.CWE_id = self.get_cwe()
        self.CATEGORY_id = {}
        
        if self.CWE_id:
            for i in range(0, len(self.CWE_id)):
                self.query2 = (self.CWE_id[i]['id'],)
                self.cur.execute('SELECT * FROM cwe_category WHERE cweid=?', self.query2)
                
                for self.data2 in self.cur.fetchall():                                                            
                    self.CATEGORY_id[self.cnt] = {
                       'id' : str(self.data2[0]),
                       'title': str(self.data2[1]),
                    }
                    
                    self.cnt += 1

        return self.CATEGORY_id

    def get_cpe(self):
        '''
        Returning:  CPE references as dictionary
        '''
        self.cnt = 0
        self.CPE_id = {}
        self.cur.execute('SELECT * FROM cve_cpe WHERE cveid=?', self.query)

        for self.data in self.cur.fetchall():
            self.CPE_id[self.cnt] = {
                'id': str(self.data[0]),
            }
            self.cnt += 1

        return self.CPE_id

    def get_ms(self):
        '''
        Returning:  Microsoft Patch references as dictionary
        '''
        self.cnt = 0
        self.MS_id = {}
        self.cur.execute('SELECT * FROM map_cve_ms WHERE cveid=?', self.query)

        for self.data in self.cur.fetchall():
            self.MS_id[self.cnt] = {
                'id': str(self.data[0]),
                'title': str(self.data[1]),
            }
            self.cnt += 1

        return self.MS_id
    

    def get_kb(self):
        '''
        Returning:  Microsoft KB bulletins as dictionary
        '''
        self.cnt = 0
        self.KB_id = {}
        self.cur.execute(
            'SELECT * FROM map_cve_mskb WHERE cveid=?', self.query)

        for self.data in self.cur.fetchall():
            self.KB_id[self.cnt] = {
                'id': str(self.data[0]),
                'title': str(self.data[1]),
            }
            self.cnt += 1

        return self.KB_id

    def get_aixapar(self):
        '''
        Returning:  IBM AIX APAR as dictionary
        '''
        self.cnt = 0
        self.AIXAPAR_id = {}
        self.cur.execute(
            'SELECT * FROM map_cve_aixapar WHERE cveid=?', self.query)

        for self.data in self.cur.fetchall():
            self.AIXAPAR_id[self.cnt] = {
                'id': str(self.data[0]),
            }
            self.cnt += 1

        return self.AIXAPAR_id

    def get_bid(self):
        '''
        Returning:  BID ids and url link
        '''
        self.cnt = 0
        self.BID_id = {}
        self.cur.execute(
            'SELECT * FROM map_cve_bid WHERE cveid=?', self.query)

        for self.data in self.cur.fetchall():
            self.BID_id[self.cnt] = {
                'id': str(self.data[0]),
                'link': self.bid_url + str(self.data[0]),
            }
            self.cnt += 1
        return self.BID_id
    
    
    
    def get_redhat(self):
        '''
        Returning:  Redhat IDs & Bugzilla
        '''
        self.cnt = 0
        self.cnt2 = 0
        self.REDHAT_id = {}
        self.BUGZILLA_id = {}

        self.cur.execute(
            'SELECT * FROM map_cve_redhat WHERE cveid=?', self.query)

        for self.data in self.cur.fetchall():
            self.REDHAT_id[self.cnt] = {
                'id': str(self.data[0]),
                'oval': str(self.data[1]),
                'title': str(self.data[2]),
            }

            # Querying the mapped redhat id and bugzilla id table. New query is set.
            self.query2 = (self.REDHAT_id[self.cnt]['id'],)
            self.cur.execute('SELECT * FROM map_redhat_bugzilla WHERE redhatid=?', self.query2)

            for self.data2 in self.cur.fetchall():
                self.BUGZILLA_id[self.cnt2] = {
                    'date_issue': str(self.data2[0]),
                    'id': str(self.data2[1]),
                    'title': str(self.data2[2]),
                }
                self.cnt2 += 1
            self.cnt += 1

        return (self.REDHAT_id, self.BUGZILLA_id)

    def get_debian(self):
        '''
        Returning:  Debian IDs as dictionary
        '''
        self.cnt = 0
        self.DEBIAN_id = {}
        self.cur.execute(
            'SELECT * FROM map_cve_debian WHERE cveid=?', self.query)

        for self.data in self.cur.fetchall():
            self.DEBIAN_id[self.cnt] = {
                'id': str(self.data[0]),
            }
            self.cnt += 1

        return self.DEBIAN_id

    def get_suse(self):
        '''
        Returning:  SUSE IDs as dictionary
        '''
        self.cnt = 0
        self.SUSE_id = {}
        self.cur.execute(
            'SELECT * FROM map_cve_suse WHERE cveid=?', self.query)

        for self.data in self.cur.fetchall():
            self.SUSE_id[self.cnt] = {
                'id': str(self.data[0]),
            }
            self.cnt += 1

        return self.SUSE_id

    def get_ubuntu(self):
        '''
        Returning:  UBUNTU IDs as dictionary
        '''
        self.cnt = 0
        self.UBUNTU_id = {}
        self.cur.execute(
            'SELECT * FROM map_cve_ubuntu WHERE cveid=?', self.query)

        for self.data in self.cur.fetchall():
            self.UBUNTU_id[self.cnt] = {
                'id': str(self.data[0]),
            }
            self.cnt += 1

        return self.UBUNTU_id

    def get_gentoo(self):
        '''
        Returning:  GENTOO IDs as dictionary
        '''
        self.cnt = 0
        self.GENTOO_id = {}
        self.cur.execute(
            'SELECT * FROM map_cve_gentoo WHERE cveid=?', self.query)

        for self.data in self.cur.fetchall():
            self.GENTOO_id[self.cnt] = {
                'id': str(self.data[0]),
            }
            self.cnt += 1

        return self.GENTOO_id

    def get_fedora(self):
        '''
        Returning:  FEDORA IDs as dictionary
        '''
        self.cnt = 0
        self.FEDORA_id = {}
        self.cur.execute(
            'SELECT * FROM map_cve_fedora WHERE cveid=?', self.query)

        for self.data in self.cur.fetchall():
            self.FEDORA_id[self.cnt] = {
                'id': str(self.data[0]),
            }
            self.cnt += 1

        return self.FEDORA_id

    def get_mandriva(self):
        '''
        Returning:  MANDRIVA IDs as dictionary
        '''
        self.cnt = 0
        self.MANDRIVA_id = {}
        self.cur.execute(
            'SELECT * FROM map_cve_mandriva WHERE cveid=?', self.query)

        for self.data in self.cur.fetchall():
            self.MANDRIVA_id[self.cnt] = {
                'id': str(self.data[0]),
            }
            self.cnt += 1

        return self.MANDRIVA_id

    def get_vmware(self):
        '''
        Returning:  VMWARE IDs as dictionary
        '''
        self.cnt = 0
        self.VMWARE_id = {}
        self.cur.execute(
            'SELECT * FROM map_cve_vmware WHERE cveid=?', self.query)

        for self.data in self.cur.fetchall():
            self.VMWARE_id[self.cnt] = {
                'id': str(self.data[0]),
            }
            self.cnt += 1

        return self.VMWARE_id


    def get_cisco(self):
        '''
        Returning:  Cisco SA Advisory ids as dictionary
        '''
        self.cnt = 0
        self.CISCO_id = {}
        self.cur.execute('SELECT * FROM map_cve_cisco WHERE cveid=?', self.query)

        for self.data in self.cur.fetchall():
            self.CISCO_id[self.cnt] = {
                'id': str(self.data[0]),
            }
            self.cnt += 1

        return self.CISCO_id


    def get_oval(self):
        '''
        Returning:  OVAL references file and their IDs as dictionay
        '''
        self.cnt = 0
        self.OVAL_id = {}
        self.cur.execute(
            'SELECT * FROM map_cve_oval WHERE cveid=?', self.query)

        for self.data in self.cur.fetchall():
            self.OVAL_id[self.cnt] = {
                'id': str(self.data[0]),
                'file': self.oval_url + str(self.data[0]),
            }
            self.cnt += 1
        return self.OVAL_id

    def get_nessus(self):
        '''
        Returning:  Nessus id, Script Name, Family Script, File Scripts as dictionay
        '''
        self.cnt = 0
        self.NESSUS_id = {}
        self.cur.execute(
            'SELECT * FROM map_cve_nessus WHERE cveid=?', self.query)

        for self.data in self.cur.fetchall():
            self.NESSUS_id[self.cnt] = {
                'id': str(self.data[0]),
                'file': str(self.data[1]),
                'name': str(self.data[2]),
                'family': str(self.data[3]),
            }
            self.cnt += 1
        return self.NESSUS_id

    def get_openvas(self):
        '''
        Returning:  OpenVAS id, Script Name, Family Script, File Scripts as dictionay
        '''
        self.cnt = 0
        self.OPENVAS_id = {}
        self.cur.execute(
            'SELECT * FROM map_cve_openvas WHERE cveid=?', self.query)
         
        for self.data in self.cur.fetchall():
            self.OPENVAS_id[self.cnt] = {
                'id': str(self.data[0]),
                'file': str(self.data[1]),
                'name': str(self.data[2]),
                'family': str(self.data[3]),
            }
            self.cnt += 1
        return self.OPENVAS_id


    def get_edb(self):
        '''
        Returning:  ExploitDB ids and exploit file link
        '''
        self.cnt = 0
        self.EDB_id = {}
        self.cur.execute(
            'SELECT * FROM map_cve_exploitdb WHERE cveid=?', self.query)

        for self.data in self.cur.fetchall():
            self.EDB_id[self.cnt] = {
                'id': str(self.data[0]),
                'file': self.edb_url + str(self.data[0]),
            }
            self.cnt += 1
        return self.EDB_id

    def get_milw0rm(self):
        '''
        Returning:  milw0rm ids
        '''
        self.cnt = 0
        self.MILWORM_id = {}
        self.cur.execute(
            'SELECT * FROM map_cve_milw0rm WHERE cveid=?', self.query)

        for self.data in self.cur.fetchall():
            self.MILWORM_id[self.cnt] = {
                'id': str(self.data[0]),
            }
            self.cnt += 1
        return self.MILWORM_id


    def get_saint(self):
        '''
        Returning:  Saint Corporation Exploits ids and files
        '''
        self.cnt = 0
        self.SAINT_id = {}
        self.cur.execute(
            'SELECT * FROM map_cve_saint WHERE cveid=?', self.query)

        for self.data in self.cur.fetchall():
            self.SAINT_id[self.cnt] = {
                'id': str(self.data[0]),
                'title': str(self.data[1]),
                'file': str(self.data[2]),
            }
            self.cnt += 1

        return self.SAINT_id

    def get_msf(self):
        '''
        Returning:  Metasploit Exploits ids, files link and exploit title
        '''
        self.cnt = 0
        self.MSF_id = {}
        self.cur.execute(
            'SELECT * FROM map_cve_msf WHERE cveid=?', self.query)

        for self.data in self.cur.fetchall():
            self.MSF_id[self.cnt] = {
                'id': str(self.data[0]),
                'file': str(self.data[1]),
                'title': str(self.data[2]),
            }
            self.cnt += 1
        return self.MSF_id


    def get_snort(self):
        '''
        Returning:  Snort references as dictionary
        '''
        self.cnt = 0
        self.SNORT_id = {}
        self.cur.execute('SELECT * FROM map_cve_snort WHERE cveid=?', self.query)
        
        for self.data in self.cur.fetchall():
            self.SNORT_id[self.cnt] = {
                'id': str(self.data[0]),
                'signature': str(self.data[1]),
                'classtype': str(self.data[2]),
            }
            self.cnt += 1

        return self.SNORT_id

    def get_suricata(self):
        '''
        Returning:  Suricata references as dictionary
        '''
        self.cnt = 0
        self.SURICATA_id = {}
        self.cur.execute('SELECT * FROM map_cve_suricata WHERE cveid=?', self.query)
        
        for self.data in self.cur.fetchall():
            self.SURICATA_id[self.cnt] = {
                'id': str(self.data[0]),
                'signature': str(self.data[1]),
                'classtype': str(self.data[2]),
            }
            self.cnt += 1

        return self.SURICATA_id

    def get_hp(self):
        '''
        Returning:  HP references as dictionary
        '''
        self.cnt = 0
        self.HP_id = {}
        self.cur.execute(
            'SELECT * FROM map_cve_hp WHERE cveid=?', self.query)

        for self.data in self.cur.fetchall():
            self.HP_id[self.cnt] = {
                'id': str(self.data[0]),
                'link': str(self.data[1]),
            }
            self.cnt += 1
        return self.HP_id

        
    def get_risk(self):
        '''
        Returning:  Severity Level, Highest Severity Level, CWE Category (Top 2011, OWASP...) and PCI Status
        topVulnerable means cvssBase=cvssImpact=cvssExploit =  10
        '''

        self.Risk = {}
        self.cvssScore = self.get_cvss()
        self.topAlert = self._isTopAlert()
        self.isTopVulnerable = False
        self.PCIstatus = "Passed"
        cve_entry = self._vrfy_cve()
       
        if cve_entry is None or self.cvssScore['base'] == "not_defined":
            self.levelSeverity = "not_calculated -- Reason: CVSS is not defined"
            self.isTopVulnerable = "not_calculated -- Reason: CVSS is not defined"
            self.PCIstatus = "not_calculated -- Reason: CVSS is not defined"
        elif 'impact' in self.cvssScore and 'exploit' in self.cvssScore\
        and self.cvssScore['base'] == "10.0" and self.cvssScore['impact'] == "10.0"\
        and self.cvssScore['exploit'] == "10.0":
            self.levelSeverity = "High"
            self.isTopVulnerable = True
            self.PCIstatus = "Failed"
        elif self.cvssScore['base'] >= "7.0":
            self.levelSeverity = "High"
            self.PCIstatus = "Failed"
        elif self.cvssScore['base'] >= "4.0" and self.cvssScore['base'] <= "6.9":
            self.levelSeverity = "Moderate"
        elif self.cvssScore['base'] >= "0.1" and self.cvssScore['base'] <= "3.9":
            self.levelSeverity = "Low"
        
        # if a top alert is found then PCI status should be failed.
        if self.topAlert:
            self.PCIstatus = "Failed"        
        
        self.Risk = {'severitylevel': self.levelSeverity,
                     'topvulnerable': self.isTopVulnerable,
                     'pciCompliance': self.PCIstatus,
                     'topAlert' : self.topAlert 
                     }
          
        return self.Risk


    def _isTopAlert(self):
        
        '''
        Returning:  The CWE Category such as CWE/SANS 2011, OWASP 2010....

        '''
        
        self.topAlert = ""
        # get_cwe should be invoked to get the number of CWEs associated with a CVEs. Rare cases where CVE has more than 1 CWE.
        
        self.CWE_id = self.get_cwe()
        self.CATEGORY_id = self.get_category()
        self.TopCategories = ['CWE-929','CWE-930','CWE-931','CWE-932','CWE-933','CWE-934','CWE-935','CWE-936','CWE-937','CWE-938','CWE-810','CWE-811','CWE-812','CWE-813', 'CWE-814', 'CWE-815','CWE-816','CWE-817','CWE-818','CWE-819','CWE-864','CWE-865','CWE-691']

        '''
        CWE-864 --> 2011 Top 25 - Insecure Interaction Between Components
        CWE-865 --> 2011 Top 25 - Risky Resource Management
        CWE-691 --> Insufficient Control Flow Management
        CWE-810 --> OWASP Top Ten 2010 Category A1 - Injection
        CWE-811 --> OWASP Top Ten 2010 Category A2
        CWE-812 --> OWASP Top Ten 2010 Category A3
        CWE-813 --> OWASP Top Ten 2010 Category A4
        CWE-814 --> OWASP Top Ten 2010 Category A5 
        CWE-815 --> OWASP Top Ten 2010 Category A6
        CWE-816 --> OWASP Top Ten 2010 Category A7
        CWE-817 --> OWASP Top Ten 2010 Category A8 
        CWE-818 --> OWASP Top Ten 2010 Category A9
        CWE-819 --> OWASP Top Ten 2010 Category A10
        CWE-929 --> OWASP Top Ten 2013 Category A1 - Injection
        CWE-930 --> OWASP Top Ten 2013 Category A2 - Broken Authentication and Session Management
        CWE-931 --> OWASP Top Ten 2013 Category A3 - Cross-Site Scripting (XSS)
        CWE-932 --> OWASP Top Ten 2013 Category A4 - Insecure Direct Object References
        CWE-933 --> OWASP Top Ten 2013 Category A5 - Security Misconfiguration
        CWE-934 --> OWASP Top Ten 2013 Category A6 - Sensitive Data Exposure
        CWE-935 --> OWASP Top Ten 2013 Category A7 - Missing Function Level Access Control
        CWE-936 --> OWASP Top Ten 2013 Category A8 - Cross-Site Request Forgery (CSRF)
        CWE-937 --> OWASP Top Ten 2013 Category A9 - Using Components with Known Vulnerabilities
        CWE-938 --> OWASP Top Ten 2013 Category A10 - Unvalidated Redirects and Forwards

        
        '''
        
        if self.CATEGORY_id:
            for i in range(len(self.CWE_id), len(self.CATEGORY_id) + len(self.CWE_id) ):
                # Checking for top CWE 2011, OWASP Top Ten 2010 and OWASP Top 2013
                for self.cat_id in self.TopCategories:
                    if self.CATEGORY_id[i]['id'] == self.cat_id:
                        self.topAlert += self.CATEGORY_id[i]['title'] + " | "
                        
        
        return self.topAlert

########NEW FILE########
__FILENAME__ = config
'''
vFeed Framework - The Open Source Cross Linked Local Vulnerability Database

Name : config.py -  Configuration File
Purpose : Configuration File. Handles global variables and database URLs.
'''

author = {
    '__name__': 'NJ OUCHN @toolswatch',
    '__email__': 'hacker@toolswatch.org',
    '__website__': 'https://github.com/toolswatch/vFeed',
}


product = {
    '__title__': 'vFeed - Open Source Cross-linked and Aggregated Local Vulnerability Database',
    '__website__': 'http://www.toolswatch.org/vfeed',
    '__mainRepository__': 'https://github.com/toolswatch/vFeed',
    '__build__': 'beta 0.4.8',
}


database = {
    'default': 'primary',
    'vfeed_db': 'vfeed.db',

    'primary': {
        'description': 'primary repository',
        'url': 'http://www.toolswatch.org/vfeed/',
        'vfeed_db': 'vfeed.db',
        'vfeed_db_compressed': 'vfeed.db.tgz',
        'updateStatus': 'update.dat',
    },


    'secondary': {
        'description': 'secondary repository (not effective yet)',
        'url': 'http://www.vfeed.org/',
        'vfeed_db': 'vfeed.db',
        'vfeed_db_compressed': 'vfeed.db.tgz',
        'updateStatus': 'update.dat',
    },

}

gbVariables = {
    'cve_url': 'http://cve.mitre.org/cgi-bin/cvename.cgi?name=',
    'bid_url': 'http://www.securityfocus.com/bid/',
    'certvn_url':'http://www.kb.cert.org/vuls/id/',
    'edb_url': 'http://www.exploit-db.com/exploits/',
    'oval_url': 'http://oval.mitre.org/repository/data/getDef?id=',
    'redhat_oval_url': 'https://www.redhat.com/security/data/oval/com.redhat.rhsa-',
    'cwe_url' : 'http://cwe.mitre.org/data/definitions/',
    'capec_url' : 'http://capec.mitre.org/data/definitions/',
    'scip_url'  : 'http://www.scip.ch/?vuldb',
    'osvdb_url'  : 'http://www.osvdb.org/show/osvdb/',
    'milw0rm_url' : 'http://www.milw0rm.com/exploits/',
    'ms_bulletin_url' : 'http://technet.microsoft.com/en-us/security/bulletin/',    
    'ms_kb_url' : 'http://support.microsoft.com/default.aspx?scid=kb;en-us;',
}

########NEW FILE########
__FILENAME__ = exportxml

from time import gmtime, strftime
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement, Comment
from xml.dom import minidom

from . import vFeed
from . import config


'''
exportxml.py -  Class to export CVE into the vFeed structured XML format


'''

class vFeedXML(object):
    '''
    Produce the vFeed XML format
    The XML file is the flagship feature of the vFeed Concept

    '''
    def __init__(self, cveID):
        
        
        self.cve_url = config.gbVariables['cve_url']
        self.redhat_oval_url = config.gbVariables['redhat_oval_url']
        self.cwe_url = config.gbVariables['cwe_url']
        self.capec_url = config.gbVariables['capec_url']
        self.osvdb_url = config.gbVariables['osvdb_url']
        self.milw0rm_url = config.gbVariables['milw0rm_url']
        self.ms_bulletin_url  = config.gbVariables['ms_bulletin_url']
        self.ms_kb_url  = config.gbVariables['ms_kb_url']
        self.bid_url = config.gbVariables['bid_url']
        
        #Invoking the vFeed api with CVE object
        self.cveID = cveID.upper()
        self.vfeed = vFeed(cveID)
        
       # Calling all available methods
        self.cveInfo = self.vfeed.get_cve()
        self.cveRef = self.vfeed.get_refs()
        self.cveBID = self.vfeed.get_bid()
        self.SCIP_id = self.vfeed.get_scip()
        self.CERTVN_id = self.vfeed.get_certvn()
        self.IAVM_id = self.vfeed.get_iavm()
        self.OSVDB_id = self.vfeed.get_osvdb()
        self.CPE_id = self.vfeed.get_cpe()
        self.CWE_id = self.vfeed.get_cwe()
        self.CAPEC_id = self.vfeed.get_capec()
        self.Risk = self.vfeed.get_risk()
        self.cvssScore = self.vfeed.get_cvss()
        self.MS_id = self.vfeed.get_ms()
        self.KB_id = self.vfeed.get_kb()
        self.AIXAPAR_id = self.vfeed.get_aixapar()
        self.REDHAT_id, self.BUGZILLA_id = self.vfeed.get_redhat()
        self.DEBIAN_id = self.vfeed.get_debian()
        self.FEDORA_id = self.vfeed.get_fedora()
        self.SUSE_id = self.vfeed.get_suse()
        self.GENTOO_id = self.vfeed.get_gentoo()
        self.UBUNTU_id = self.vfeed.get_ubuntu()
        self.CISCO_id = self.vfeed.get_cisco()
        self.MANDRIVA_id = self.vfeed.get_mandriva()
        self.VMWARE_id = self.vfeed.get_vmware()
        self.OVAL_id = self.vfeed.get_oval()
        self.NESSUS_id = self.vfeed.get_nessus()
        self.OPENVAS_id = self.vfeed.get_openvas()
        self.EDB_id = self.vfeed.get_edb()
        self.SAINT_id = self.vfeed.get_saint()
        self.MSF_id = self.vfeed.get_msf()
        self.MILWORM_id = self.vfeed.get_milw0rm()
        self.SNORT_id = self.vfeed.get_snort()
        self.SURICATA_id = self.vfeed.get_suricata()
        self.HP_id = self.vfeed.get_hp()
    
    def export(self):
        '''
            exporting data to the vFeed XML format
            Output : CVE_xxxx_xxx_.xml file
        '''
        # define id
        self.vfeedid = self.cveID.replace('self.cveID', 'vFeed')
        self.vfeedfile = self.cveID.replace('-', '_') + '.xml'
    
        # define generation time
        self.generated_on = strftime("%a, %d %b %Y %H:%M:%S", gmtime())
    
        # define the vFeed XML attributes
        self.root = Element('vFeed')
        self.root.set('xmlns:xsi', "http://www.w3.org/2001/XMLSchema-instance")
        self.root.set('xmlns:meta', "http://www.toolswatch.org/vfeed/")
        self.root.set('xmlns', "http://www.toolswatch.org/vfeed/")
        self.root.set('xsi:schemaLocation', "http://www.toolswatch.org/vfeed/ http://www.toolswatch.org/vfeed/vFeed.xsd")
    
        self.root.append(Comment('#####################################'))
        self.root.append(Comment(config.product['__title__']))
        self.root.append(Comment('Generated by vFeedApi.py'))
    
        self.head = SubElement(self.root, 'release')
        self.project_name = SubElement(self.head, 'name')
        self.project_name.text = 'vFeed XML for %s' % self.cveID
    
        self.project_version = SubElement(self.head, 'version')
        self.project_version.text = config.product['__build__']
    
        self.project_author = SubElement(self.head, 'author')
        self.project_author.text = config.author['__name__']
    
        self.project_url = SubElement(self.head, 'url')
        self.project_url.text = config.author['__website__']
    
        self.date_generated = SubElement(self.head, 'date_generated')
        self.date_generated.text = self.generated_on
    
        # Exporting  Vulnerability Summary
    
        self.root.append(Comment('#####################################'))
        self.root.append(Comment('Entry ID'))
        self.entry_head = SubElement(self.root, 'entry',
                                     {'exported': self.vfeedfile,
                                      'id': self.vfeedid,
                                      })
    
        self.vul_summary_date = SubElement(self.entry_head, 'date',
                                           {'published': self.cveInfo['published'],
                                            'modified': self.cveInfo['modified'],
                                            })
    
        self.vul_summary = SubElement(self.entry_head, 'summary')
        self.vul_summary.text = self.cveInfo['summary']
        self.vul_summary_ref = SubElement(self.entry_head, 'cve_ref')
        self.vul_summary_ref.text = self.cve_url + self.cveID
    
        # Exporting references as they come from NVD XML
    
        self.entry_head.append(
            Comment('#####################################'))
        self.entry_head.append(Comment('Official References'))
        self.references_head = SubElement(self.entry_head, 'references')
    
        for i in range(0, len(self.cveRef)):
            self.source_head = SubElement(self.references_head, 'ref',
                                          {'url': self.cveRef[i]['link'],
                                           'source': self.cveRef[i]['id'],
                                           })


        self.entry_head.append(
            Comment('#####################################'))
        self.entry_head.append(Comment('vFeed Mapped References'))
        self.mappedrefs_head = SubElement(self.entry_head, 'crossReferences')


        # Exporting extra SCIP ref from Mapping
        
        for i in range(0, len(self.SCIP_id)):
            self.source_head = SubElement(self.mappedrefs_head, 'ref',
                                          {'url': self.SCIP_id[i]['link'],
                                           'id': self.SCIP_id[i]['id'],
                                           'source': "SCIP",
                                           })
 
         # Exporting extra CERT VN ref from Mapping
        
        for i in range(0, len(self.CERTVN_id)):
            self.source_head = SubElement(self.mappedrefs_head, 'ref',
                                          {'url': self.CERTVN_id[i]['link'],
                                           'id': self.CERTVN_id[i]['id'],
                                           'source': "CERT-VN",
                                           })
        
        # Exporting IAVM ref from Mapping

        for i in range(0, len(self.IAVM_id)):
            self.source_head = SubElement(self.mappedrefs_head, 'ref',
                                          {'vmskey': self.IAVM_id[i]['key'],
                                           'id': self.IAVM_id[i]['id'],
                                           'title': self.IAVM_id[i]['title'],
                                           'source': "DISA/IAVM",
                                           })

        # Exporting BID ref from Mapping

        for i in range(0, len(self.cveBID)):
            self.source_head = SubElement(self.mappedrefs_head, 'ref',
                                          {'id': self.cveBID[i]['id'],
                                           'url': self.cveBID[i]['link'],
                                           'source': "SecurityFocus",
                                           })

        # Exporting OSVDB ref from Mapping
        
        for i in range(0, len(self.OSVDB_id)):
            self.source_head = SubElement(self.mappedrefs_head, 'ref',
                                          {
                                           'id': self.OSVDB_id[i]['id'],
                                           'url': self.osvdb_url + self.OSVDB_id[i]['id'],
                                           'source': "OSVDB",
                                           })
            
        # Exporting Targets CPEs ids
    
        if self.CPE_id:
            self.entry_head.append(
                Comment('#####################################'))
            self.entry_head.append(
                Comment('Vulnerable Targets according to CPE'))
            self.vulnerabletargets_head = SubElement(
                self.entry_head, 'vulnerableTargets',
                {'totalCPE': str(len(self.CPE_id)), })
    
            for i in range(0, len(self.CPE_id)):
                self.cpe_head = SubElement(self.vulnerabletargets_head, 'cpe',
                                           {'id': self.CPE_id[i]['id'],
                                            })
    
        # Exporting Risk Scoring
    
        self.entry_head.append(
            Comment('#####################################'))
        self.entry_head.append(Comment('Risk Scoring Evaluation'))
        self.riskscoring_head = SubElement(self.entry_head, 'riskScoring')
    
        self.risk_head = SubElement(self.riskscoring_head, 'severityLevel',
                                    {'status': self.Risk['severitylevel'],
                                     })
    
        self.risk_head = SubElement(self.riskscoring_head, 'cvss',
                                    {
                                     'base': self.cvssScore['base'],
                                     'impact': self.cvssScore['impact'],
                                     'exploit': self.cvssScore['exploit'],
                                     })
    
        self.risk_head = SubElement(self.riskscoring_head, 'cvssVector',
                                    {'AV': self.cvssScore['access_vector'],
                                     'AC': self.cvssScore['access_complexity'],
                                     'Au': self.cvssScore['authentication'],
                                     'C': self.cvssScore['confidentiality_impact'],
                                     'I': self.cvssScore['integrity_impact'],
                                     'A': self.cvssScore['availability_impact'],
                                     })
    
        self.risk_head = SubElement(self.riskscoring_head, 'topVulnerable',
                                    {'status': str(self.Risk['topvulnerable']),
                                     })
    
        self.risk_head = SubElement(self.riskscoring_head, 'topAlert',
                                    {'status': str(self.Risk['topAlert']),
                                     })
    
        self.risk_head = SubElement(self.riskscoring_head, 'pciCompliance',
                                    {'status': self.Risk['pciCompliance'],
                                     })
    
    # Exporting Patch Management
    
        self.entry_head.append(
            Comment('#####################################'))
        self.entry_head.append(Comment('Patch Management'))
        self.patchmanagement_head = SubElement(
            self.entry_head, 'patchManagement')
    
        ## Exporting Microsoft MS Patches
    
        for i in range(0, len(self.MS_id)):
            self.patch_head = SubElement(self.patchmanagement_head, 'patch',
                                         {'id': self.MS_id[i]['id'],
                                          'title': self.MS_id[i]['title'],
                                          'source': 'microsoft',
                                          'url' : self.ms_bulletin_url + self.MS_id[i]['id'],
                                          })
    
        ## Exporting Microsoft KB Patches
    
        for i in range(0, len(self.KB_id)):
            self.patch_head = SubElement(self.patchmanagement_head, 'patch',
                                         {'id': self.KB_id[i]['id'],
                                          'title': self.KB_id[i]['title'],
                                          'source': 'microsoft KB',
                                          'url' : self.ms_kb_url + self.KB_id[i]['id'],
                                          })
    
        ## Exporting IBM AIXAPAR Patches
        for i in range(0, len(self.AIXAPAR_id)):
            self.patch_head = SubElement(self.patchmanagement_head, 'patch',
                                         {'id': self.AIXAPAR_id[i]['id'],
                                          'source': 'IBM',
                                          })
    
        ## Exporting REDHAT Patches
    
        for i in range(0, len(self.REDHAT_id)):
            self.patch_head = SubElement(self.patchmanagement_head, 'patch',
                                         {'id': self.REDHAT_id[i]['id'],
                                          'title': self.REDHAT_id[i]['title'],
                                          'source': 'REDHAT',
                                          })
    
        for i in range(0, len(self.BUGZILLA_id)):
            self.patch_head = SubElement(self.patchmanagement_head, 'patch',
                                         {'date_issue': self.BUGZILLA_id[i]['date_issue'],
                                          'id': self.BUGZILLA_id[i]['id'],
                                          'title': self.BUGZILLA_id[i]['title'],
                                          'source': 'BUGZILLA',
                                          })
    
        ## Exporting SUSE Patches
        for i in range(0, len(self.SUSE_id)):
            self.patch_head = SubElement(self.patchmanagement_head, 'patch',
                                         {'id': self.SUSE_id[i]['id'],
                                          'source': 'SUSE',
                                          })
    
        ## Exporting DEBIAN Patches
    
        for i in range(0, len(self.DEBIAN_id)):
            self.patch_head = SubElement(self.patchmanagement_head, 'patch',
                                         {'id': self.DEBIAN_id[i]['id'],
                                          'source': 'DEBIAN',
                                          })
    
        ## Exporting MANDRIVA Patches
    
        for i in range(0, len(self.MANDRIVA_id)):
            self.patch_head = SubElement(self.patchmanagement_head, 'patch',
                                         {'id': self.MANDRIVA_id[i]['id'],
                                          'source': 'MANDRIVA',
                                          })

        ## Exporting VMWARE Patches
    
        for i in range(0, len(self.VMWARE_id)):
            self.patch_head = SubElement(self.patchmanagement_head, 'patch',
                                         {'id': self.VMWARE_id[i]['id'],
                                          'source': 'VMWARE',
                                          })


        ## Exporting CISCO Patches
    
        for i in range(0, len(self.CISCO_id)):
            self.patch_head = SubElement(self.patchmanagement_head, 'patch',
                                         {'id': self.CISCO_id[i]['id'],
                                          'source': 'CISCO',
                                          })

        ## Exporting UBUNTU Patches
    
        for i in range(0, len(self.UBUNTU_id)):
            self.patch_head = SubElement(self.patchmanagement_head, 'patch',
                                         {'id': self.UBUNTU_id[i]['id'],
                                          'source': 'UBUNTU',
                                          })
            
        ## Exporting GENTOO Patches
    
        for i in range(0, len(self.GENTOO_id)):
            self.patch_head = SubElement(self.patchmanagement_head, 'patch',
                                         {'id': self.GENTOO_id[i]['id'],
                                          'source': 'GENTOO',
                                          })    
        
        ## Exporting FEDORA Patches
    
        for i in range(0, len(self.FEDORA_id)):
            self.patch_head = SubElement(self.patchmanagement_head, 'patch',
                                         {'id': self.FEDORA_id[i]['id'],
                                          'source': 'FEDORA',
                                          })  

        ## Exporting HP Patches
    
        for i in range(0, len(self.HP_id)):
            self.patch_head = SubElement(self.patchmanagement_head, 'patch',
                                         {'id': self.HP_id[i]['id'],
                                          'link': self.HP_id[i]['link'],
                                          'source': 'Hewlett-Packard',
                                          })  


        # Attack and Weaknesses Patterns
        
        if self.CWE_id:
    
            self.entry_head.append(
                Comment('#####################################'))
            self.entry_head.append(Comment('Attack and Weaknesses Categories. Useful when performing classification of threats'))
            self.attackclassification_head = SubElement(
                self.entry_head, 'attackPattern')
    
            for i in range(0, len(self.CWE_id)):
                self.cwe_id_url = self.CWE_id[i]['id'].split("CWE-")
                self.attackPattern_head = SubElement(
                    self.attackclassification_head, 'cwe',
                    {'standard': 'CWE - Common Weakness Enumeration',
                                                    'id': self.CWE_id[i]['id'],
                                                    'title': self.CWE_id[i]['title'],
                                                    'url' : self.cwe_url+self.cwe_id_url[1]
                     })
    
    
            for i in range(len(self.CWE_id), len(self.CAPEC_id) + len(self.CWE_id)):
                self.attackPattern_head = SubElement(
                    self.attackclassification_head, 'capec',
                    {'standard': 'CAPEC - Common Attack Pattern Enumeration and Classification',
                                                    'relatedCWE': self.CAPEC_id[i]['cwe'],
                                                    'id': self.CAPEC_id[i]['id'],
                                                    'url' : self.capec_url + self.CAPEC_id[i]['id']
                     })
    
    
        # Exporting Assessment, security tests and exploitation
        
        self.entry_head.append(
            Comment('#####################################'))
        self.entry_head.append(Comment('Assessment and security Tests. The IDs and source could be leveraged to test the vulnerability'))
        self.securitytest_head = SubElement(self.entry_head, 'assessment')
    
        ## Exporting OVAL ids
        for i in range(0, len(self.OVAL_id)):
            self.ovalChecks_head = SubElement(self.securitytest_head, 'check',
                                              {'type': 'Local Security Testing',
                                               'id': self.OVAL_id[i]['id'],
                                               'utility': "OVAL Interpreter",
                                               'file': self.OVAL_id[i]['file'],
                                               })
    
        for i in range(0, len(self.REDHAT_id)):
            try:
                self.ovalChecks_head = SubElement(self.securitytest_head, 'check',
                                                  {'type': 'Local Security Testing',
                                                   'id': self.REDHAT_id[i]['oval'],
                                                   'utility': "OVAL Interpreter",
                                                   'file': self.redhat_oval_url + self.REDHAT_id[i]['oval'].split('oval:com.redhat.rhsa:def:')[1] + '.xml',
                                                   })
            except:
                pass
    
        ## Exporting Nessus attributes
        for i in range(0, len(self.NESSUS_id)):
            self.nessusChecks_head = SubElement(
                self.securitytest_head, 'check',
                {'type': 'Remote Security Testing',
                 'id': self.NESSUS_id[i]['id'],
                 'name': self.NESSUS_id[i]['name'],
                 'family': self.NESSUS_id[i]['family'],
                 'file': self.NESSUS_id[i]['file'],
                 'utility': "Nessus Vulnerability Scanner",
                 })
     
        ## Exporting OpenVAS attributes
        for i in range(0, len(self.OPENVAS_id)):
            self.openvasChecks_head = SubElement(
                self.securitytest_head, 'check',
                {'type': 'Remote Security Testing',
                 'id': self.OPENVAS_id[i]['id'],
                 'name': self.OPENVAS_id[i]['name'],
                 'family': self.OPENVAS_id[i]['family'],
                 'file': self.OPENVAS_id[i]['file'],
                 'utility': "OpenVAS Vulnerability Scanner",
                 })           
            
        ## Exporting EDB ids
        for i in range(0, len(self.EDB_id)):
            self.exploitChecks_head = SubElement(
                self.securitytest_head, 'check',
                {'type': 'Exploitation',
                 'utility': "exploit-db",
                 'id': self.EDB_id[i]['id'],
                 'file': self.EDB_id[i]['file'],
                 })
    
        ## Exporting Milw0rm ids 
        for i in range(0, len(self.MILWORM_id)):
            self.exploitChecks_head = SubElement(
                self.securitytest_head, 'check',
                {'type': 'Exploitation',
                 'utility': "milw0rm",
                 'id': self.MILWORM_id[i]['id'],
                 'file': self.milw0rm_url + self.MILWORM_id[i]['id'],
                 })


        ## Exporting SAINT ids
        for i in range(0, len(self.SAINT_id)):
            self.exploitChecks_head = SubElement(
                self.securitytest_head, 'check',
                {'type': 'Exploitation',
                 'utility': "saintExploit",
                 'id': self.SAINT_id[i]['id'],
                 'title': self.SAINT_id[i]['title'],
                 'file': self.SAINT_id[i]['file'],
                 })
    
        ## Exporting MSF - Metasploit ids
        for i in range(0, len(self.MSF_id)):
            self.exploitChecks_head = SubElement(
                self.securitytest_head, 'check',
                {'type': 'Exploitation',
                 'utility': "Metasploit",
                 'id': self.MSF_id[i]['id'],
                 'title': self.MSF_id[i]['title'],
                 'script': self.MSF_id[i]['file'],
                 })


        # Exporting Defense rules
        
        self.entry_head.append(
            Comment('#####################################'))
        self.entry_head.append(Comment('Defense and IDS rules. The IDs and source could be leveraged to deploy effective rules'))
        self.defense_head = SubElement(self.entry_head, 'defense')
    
            ## Exporting Snort Rules
        for i in range(0, len(self.SNORT_id)):
            self.idsRules_head = SubElement(
                self.defense_head, 'rule',
                {'type': 'Defense',
                 'utility': "Snort",
                 'id': self.SNORT_id[i]['id'],
                 'signature': self.SNORT_id[i]['signature'],
                 'classtype': self.SNORT_id[i]['classtype'],
                 })
 
             ## Exporting Suricata Rules
        for i in range(0, len(self.SURICATA_id)):
            self.idsRules_head = SubElement(
                self.defense_head, 'rule',
                {'type': 'Defense',
                 'utility': "Suricata",
                 'id': self.SURICATA_id[i]['id'],
                 'signature': self.SURICATA_id[i]['signature'],
                 'classtype': self.SURICATA_id[i]['classtype'],
                 })
  
 
                    
        self.xmlfile = open(self.vfeedfile, 'w+')
        print '[info] vFeed xml file %s exported for %s' % (self.vfeedfile, self.cveID)
        print >> self.xmlfile, self.prettify(self.root)
    
    def prettify(self, elem):
        """Return a pretty-printed XML string for the Element.
        This function found on internet.
        So thanks to its author whenever he is.
        """
        rough_string = ElementTree.tostring(elem, 'UTF-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")

########NEW FILE########
__FILENAME__ = info
from . import config

'''
info.py -  vFeed - Open Source Cross-linked and Aggregated Local Vulnerability Database

Class vFeedInfo : supplying the vFeed information
'''


class vFeedInfo(object):
    def __init__(self):
        self.vFeedInfo = {}

    def get_version(self):
        self.vFeedInfo['title'] = config.product['__title__']
        self.vFeedInfo['build'] = config.product['__build__']
        return self.vFeedInfo

    def get_owner(self):

        self.vFeedInfo['author'] = config.author['__name__']
        self.vFeedInfo['email'] = config.author['__email__']
        self.vFeedInfo['website'] = config.author['__website__']
        return self.vFeedInfo

    def get_config(self):

        self.vFeedInfo['primary'] = config.database['primary']
        self.vFeedInfo['secondary'] = config.database['secondary']
        return self.vFeedInfo
########NEW FILE########
__FILENAME__ = stats
import sqlite3
from . import config

'''
stats.py -  vfeed.db class for statistics

'''
class vFeedStats(object):

    def __init__(self):

        self.configData = config.database['primary'] 
        self.vfeed_db  = self.configData['vfeed_db']
        self.conn = sqlite3.connect(self.vfeed_db)
        self.cur = self.conn.cursor()
        

    def stats(self):


        print"---------------------------------------------------------------"
        print "vFeed.db Statistics"
        print "Distinct values of CVEs and associated third party references"
 
        self.cur.execute("SELECT * from stat_vfeed_kpi; ") 
        
        for self.data in self.cur.fetchall():
            print 'Database build (latest update date):', str(self.data[0])
            print"---------------------------------------------------------------"
            print ""            
            print '[+] Vulnerability Information and References'
            print '\t[-] Common Vulnerability Enumeration (CVE):', self.data[1]
            print '\t[-] Affected Products or Common Platform Enumeration (CPE):', self.data[2]
            print '\t[-] Common Weakness Enumeration (CWE) types:', self.data[3]
            print '\t[-] Common Attack Pattern Enumeration and Classification (CAPEC) types:', self.data[4]
            print '\t[-] SecurityFocus BID:', self.data[5]
            print '\t[-] OSVDB - Open Source Vulnerability Database advisories:', self.data[6]
            print '\t[-] CERT.org Vulnerability Notes:', self.data[7]
            print '\t[-] DOD-CERT Information Assurance Vulnerability Alert (IAVA):', self.data[8]
            print '\t[-] Scip AG Security Advisories:', self.data[9]

            print '\n[+] Third Party Vendors Patches and Advisories'
            print '\t[-] IBM AIX APARs Patches Advisories:', self.data[10]
            print '\t[-] Suse Patches Advisories:', self.data[11]
            print '\t[-] Ubuntu Patches Advisories:', self.data[12]
            print '\t[-] VMware Patches Advisories:', self.data[13]
            print '\t[-] Cisco Patches Advisories:', self.data[14]
            print '\t[-] Debian Patches Advisories:', self.data[15]
            print '\t[-] Fedora Patches Advisories:', self.data[16]
            print '\t[-] Gentoo Patches Advisories:', self.data[17]
            print '\t[-] HP (Hewlett Packard) Patches Advisories:', self.data[18]
            print '\t[-] Mandriva Patches Advisories:', self.data[19]
            print '\t[-] Microsoft Bulletins Advisories:', self.data[20]
            print '\t[-] Microsoft KB Advisories:', self.data[21]
            print '\t[-] Redhat Patches Advisories:', self.data[22]
            print '\t[-] Redhat Bugzilla Advisories:', self.data[23]
            
            print '\n[+] Exploits and Proof of Concepts'
            print '\t[-] Exploit-DB Proof of Concepts and exploits:', self.data[24]
            print '\t[-] Metasploit Exploits or Modules:', self.data[25]
            print '\t[-] Milw0rm Proof of Concepts and exploits:', self.data[26]
            print '\t[-] Saint Corporation Proof of Concepts and exploits:', self.data[27]
            
            print '\n[+] Third Party Security Scanners Scripts'
            print '\t[-] Nessus Security Scripts:', self.data[28]
            print '\t[-] OpenVAS Security Scripts:', self.data[29]
            print '\t[-] Open Vulnerability Assessment Language (OVAL) definitions:', self.data[30]
 
            print '\n[+] Open Source Intrusion Detection Rules'
            print '\t[-] Snort Detection Rules:', self.data[31]
            print '\t[-] Suricata Detection Rules:', self.data[32]


    def latest_cve(self):


        print"---------------------------------------------------------------"
        print "vFeed.db Statistics : Latest added CVEs"
        self.cur.execute("SELECT count(DISTINCT new_cve_id) FROM stat_new_cve; ") 
        self.latest_cve = self.cur.fetchone()
        print '%s total added new CVEs' %self.latest_cve[0]
        print"---------------------------------------------------------------"

        self.cur.execute("SELECT * FROM stat_new_cve; ")
        for self.data in self.cur.fetchall():
            print self.data[0]
            # if you want to display also the CVE summary, just replace with print self.data[0], self.data[1] 
########NEW FILE########
__FILENAME__ = update
import os,sys
import urllib2
import tarfile
import hashlib
from . import vFeed
from . import config

'''
update.py -  Class to update the vfeed.db correlated and aggregated vulnerability database

'''

class vFeedUpdate(object):
    '''
    Download the vfeed.db tgz'd file
    Check for the checksum and decompress
    Do not interrupt the process. If something wrong, it will flag it
    The support for proxy will be added later on (or if you got the guts to do it, be my guest)
    '''
    def __init__(self):
        
        self.configData = config.database['primary']
        self.vfeed_db_primary_url =  self.configData['url']
        self.vfeed_db_compressed  = self.configData['vfeed_db_compressed']
        self.vfeed_db  = self.configData['vfeed_db']
        self.updateStatus = self.configData['updateStatus']     
        self.urlCompressed = self.vfeed_db_primary_url + self.vfeed_db_compressed
        self.urlUpdate = self.vfeed_db_primary_url + self.updateStatus
        
    def update(self):
        '''
            Download the db and decompress it
            Output : vfeed.db
        '''
    
        if not os.path.isfile(self.vfeed_db):
            print '[install] getting fresh copy of %s. It may take a while ...' %self.vfeed_db
            self._updateDB(self.urlCompressed)
            print '\n[info] decompressing %s ...' %self.vfeed_db_compressed
            self._uncompress()
            self.cleaning()
            exit(0)
            
        if os.path.isfile(self.vfeed_db):
            print '[info] checking for the latest %s ' %self.vfeed_db
            self._checkDBversion()
    
    def _updateDB(self,url):
        '''
        This function was found on internet.
        So thanks to its author wherever he is.
        '''
        
        self.filename = url.split('/')[-1]
        self.u = urllib2.urlopen(url)
        self.f = open(self.filename, 'wb')
        self.meta = self.u.info()
        self.filesize = int(self.meta.getheaders("Content-Length")[0])
        
        self.filesize_dl = 0
        self.block_sz = 8192
        while True:
            sys.stdout.flush()
            self.buffer = self.u.read(self.block_sz)
            if not self.buffer:
                break
        
            self.filesize_dl += len(self.buffer)
            self.f.write(self.buffer)
            self.status = r"%10d [%3.0f %%]" % (self.filesize_dl, self.filesize_dl * 100. / self.filesize)
            self.status = self.status + chr(8)*(len(self.status)+1)
            sys.stdout.write("\r[progress %3.0f %%] receiving %d out of %s Bytes of %s " % (self.filesize_dl * 100. / self.filesize, self.filesize_dl,self.filesize,self.filename))
            sys.stdout.flush()
        
        self.f.close()
    
        
    def _uncompress(self):
        '''
        uncompress the tgz db
        '''        
        if not os.path.isfile(self.vfeed_db_compressed):
            print '[error] ' + self.vfeed_db_compressed + ' not found'
            print '[info] Get manually your copy from %s' % self.config.database['primary']['url']
            exit(0)
        
        try:
            tar = tarfile.open(self.vfeed_db_compressed, 'r:gz')
            tar.extractall('.')
            self.tar.close            
        except:
            print '[error] Database not extracted.'
         
     
    def _checkDBversion(self):
        '''
        updating the existing vfeed database if needed
        '''
        self._updateDB(self.urlUpdate)     
        self.hashLocal = self.checksumfile(self.vfeed_db)
        with open(self.updateStatus,'r') as f:
            self.output = f.read()
            self.hashRemote = self.output.split(',')[1]
        
        if self.hashRemote <> self.hashLocal:
            print '[New Update] Downloading the recent vFeed Database %s from %s' %(self.vfeed_db_compressed,self.vfeed_db_primary_url)            
            self._updateDB(self.urlCompressed)
            print '[info] Decompressing %s ...' %self.vfeed_db_compressed
            self._uncompress()
            self.cleaning()
            exit(0)
            
        if self.hashRemote == self.hashLocal:
            print '\n[info] You have the latest %s vulnerability database' %self.vfeed_db
            self.cleaning()
            
    def checksumfile(self,file):
        '''
        returning the sha1 hash value 
        '''
        self.sha1 = hashlib.sha1()
        self.f = open(file, 'rb')
        try:
            self.sha1.update(self.f.read())
        finally:
            self.f.close()
        return self.sha1.hexdigest()
    
    def cleaning(self):
        '''
        Cleaning the tgz and .dat temporary files 
        '''
        print '[info] Cleaning compressed database and update file'
        try:
            if os.path.isfile(self.vfeed_db_compressed):
                os.remove(self.vfeed_db_compressed)
            if os.path.isfile(self.updateStatus):
                os.remove(self.updateStatus)
        except:
            print '[exception] Already cleaned'
    
########NEW FILE########
__FILENAME__ = vfeedcli
#!/usr/bin/env python
import sys

from vfeed import vFeed, vFeedInfo, vFeedXML, vFeedUpdate, vFeedStats

'''
vFeed - Open Source Cross-linked and Aggregated Local Vulnerability Database
Wiki Documentation https://github.com/toolswatch/vFeed/wiki

'''

def get_help():
    info = vFeedInfo()
    print ''
    print '-----------------------------------------------------------------------------'
    print info.get_version()['title']
    print '                                                          version ' + info.get_version()['build']
    print '                                         ' + info.get_owner()['website']
    print '-----------------------------------------------------------------------------'
    print ''
    print '[usage 1]: python' + str(sys.argv[0]) + ' <Method> <CVE>'
    print '[info] Available vFeed methods:'
    print 'Information  ==> get_cve | get_cpe | get_cwe | get_capec | get_category | get_iavm'
    print 'References   ==> get_refs | get_scip | get_osvdb | get_certvn | get_bid'
    print 'Risk         ==> get_risk | get_cvss'
    print 'Patchs 1/2   ==> get_ms | get_kb | get_aixapar | get_redhat | get_suse | get_debian | get_hp'
    print 'Patchs 2/2   ==> get_mandriva | get_cisco | get_ubuntu | get_gentoo | get_fedora | get_vmware'
    print 'Assessment   ==> get_oval | get_nessus | get_openvas '
    print 'Defense      ==> get_snort | get_suricata'
    print 'Exploitation ==> get_milw0rm | get_edb | get_saint | get_msf'
    print ''
    print '----------'
    print '[usage 2]: python ' + str(sys.argv[0]) + ' export <CVE>'
    print '[info]: This method will export the CVE as vFeed XML format'
    print ''
    print '----------'
    print '[usage 3]: python ' + str(sys.argv[0]) + ' stats or latest_cve'
    print '[info]: Available stats methods'
    print 'Global statistics   ==> stats'
    print 'Latest Added CVEs   ==> latest_cve '
    print ''
    print '----------'
    print '[Update]: python ' + str(sys.argv[0]) + ' update'
    print '[info]: This method will update the SQLite vfeed database to its latest release'
    exit(0)

def call_get_cve(vfeed):
    cveInfo = vfeed.get_cve()
    if cveInfo:
        print '[cve_description]:', cveInfo['summary']
        print '[cve_published]:', cveInfo['published']
        print '[cve_modified]:', cveInfo['modified']


def call_get_cvss(vfeed):
    cvssScore = vfeed.get_cvss()
    if cvssScore:
        print '[cvss_base]:', cvssScore['base']
        print '[cvss_impact]:', cvssScore['impact']
        print '[cvss_exploit]:', cvssScore['exploit']
        print '[AV (access vector)]:', cvssScore['access_vector']
        print '[AC (access complexity)]:', cvssScore['access_complexity']
        print '[Au (authentication)]:', cvssScore['authentication']    
        print '[C (confidentiality impact)]:', cvssScore['confidentiality_impact']     
        print '[I (integrity impact)]:', cvssScore['integrity_impact']     
        print '[A (availability impact)]:', cvssScore['availability_impact']

def call_get_refs(vfeed):

    cveRef = vfeed.get_refs()
    for i in range(0, len(cveRef)):
        print '[reference_id]:', cveRef[i]['id']
        print '[reference_link]', cveRef[i]['link']
    print ''
    print '[stats] %d Reference(s)' % len(cveRef)


def call_get_osvdb(vfeed):

    cveOSVDB = vfeed.get_osvdb()
    for i in range(0, len(cveOSVDB)):
        print '[osvdb_id]:', cveOSVDB[i]['id']
    print ''
    print '[stats] %d OSVDB id(s)' % len(cveOSVDB)


def call_get_scip(vfeed):

    cveSCIP = vfeed.get_scip()
    for i in range(0, len(cveSCIP)):
        print '[scip_id]:', cveSCIP[i]['id']
        print '[scip_link]', cveSCIP[i]['link']
    print ''
    print '[stats] %d Scip id(s)' % len(cveSCIP)

def call_get_bid(vfeed):

    cveBID = vfeed.get_bid()
    for i in range(0, len(cveBID)):
        print '[bid_id]:', cveBID[i]['id']
        print '[bid_link]', cveBID[i]['link']
    print ''
    print '[stats] %d BID id(s)' % len(cveBID)


def call_get_certvn(vfeed):

    cveCERTVN = vfeed.get_certvn()
    for i in range(0, len(cveCERTVN)):
        print '[certvn_id]:', cveCERTVN[i]['id']
        print '[certvn_link]', cveCERTVN[i]['link']
    print ''
    print '[stats] %d CERT-VN id(s)' % len(cveCERTVN)
    
def call_get_iavm(vfeed):

    cveIAVM = vfeed.get_iavm()
    for i in range(0, len(cveIAVM)):
        print '[iavm_title]', cveIAVM[i]['title']
        print '[iavm_id]:', cveIAVM[i]['id']
        print '[disa_key]:', cveIAVM[i]['key']
    print ''
    print '[stats] %d Iavm id(s)' % len(cveIAVM)


def call_get_cwe(vfeed):

    cveCWE = vfeed.get_cwe()
    for i in range(0, len(cveCWE)):
        print '[cwe_id]:', cveCWE[i]['id']
        print '[cwe_title]:', cveCWE[i]['title']
    print ''
    print '[stats] %d CWE id(s) ' % len(cveCWE)


def call_get_capec(vfeed):

    cveCAPEC = vfeed.get_capec()
    #get_cwe is invoked because CAPEC is related to CWE base
    cveCWE = vfeed.get_cwe()
    for i in range(len(cveCWE), len(cveCAPEC) + len(cveCWE)):
        print '[capec_id]: %s associated with %s ' %(cveCAPEC[i]['id'],cveCAPEC[i]['cwe'])
    print ''
    print '[stats] %d CAPEC id(s) ' % len(cveCAPEC)

def call_get_category(vfeed):

    cveCATEGORY = vfeed.get_category()
    #get_cwe is invoked because CAPEC is related to CWE base
    cveCWE = vfeed.get_cwe()
    for i in range(len(cveCWE), len(cveCATEGORY) + len(cveCWE)):
        print '[category] : %s --> %s ' %(cveCATEGORY[i]['id'],cveCATEGORY[i]['title'])
    print ''


def call_get_cpe(vfeed):

    cveCPE = vfeed.get_cpe()
    for i in range(0, len(cveCPE)):
        print '[cpe_id]:', cveCPE[i]['id']

    print ''
    print '[stats] %d CPE id(s)' % len(cveCPE)


def call_get_oval(vfeed):

    cveOVAL = vfeed.get_oval()
    for i in range(0, len(cveOVAL)):
        print '[oval_id]:', cveOVAL[i]['id']
        print '[oval_file]:', cveOVAL[i]['file']

    print ''
    print '[stats] %d OVAL Definition id(s)' % len(cveOVAL)

def call_get_snort(vfeed):

    cveSnort = vfeed.get_snort()
    for i in range(0, len(cveSnort)):
        print '[snort_id]:', cveSnort[i]['id']
        print '[snort_signature]:', cveSnort[i]['signature']
        print '[snort_classtype]:', cveSnort[i]['classtype']

    print ''
    print '[stats] %d Snort Rule(s)' % len(cveSnort)


def call_get_suricata(vfeed):

    cveSuricata = vfeed.get_suricata()
    for i in range(0, len(cveSuricata)):
        print '[suricata_id]:', cveSuricata[i]['id']
        print '[suricata_signature]:', cveSuricata[i]['signature']
        print '[suricata_classtype]:', cveSuricata[i]['classtype']

    print ''
    print '[stats] %d Suricata Rule(s)' % len(cveSuricata)


def call_get_nessus(vfeed):

    cveNessus = vfeed.get_nessus()
    for i in range(0, len(cveNessus)):
        print '[nessus_id]:', cveNessus[i]['id']
        print '[nessus_name]:', cveNessus[i]['name']
        print '[nessus_file]:', cveNessus[i]['file']
        print '[nessus_family]:', cveNessus[i]['family']

    print ''
    print '[stats] %d Nessus testing script(s)' % len(cveNessus)

def call_get_openvas(vfeed):
    
    cveOpenvas = vfeed.get_openvas()
    for i in range(0, len(cveOpenvas)):
        print '[openvas_id]:', cveOpenvas[i]['id']
        print '[openvas_name]:', cveOpenvas[i]['name']
        print '[openvas_file]:', cveOpenvas[i]['file']
        print '[openvas_family]:', cveOpenvas[i]['family']

    print ''
    print '[stats] %d OpenVAS testing script(s)' % len(cveOpenvas)
    
def call_get_edb(vfeed):

    cveEDB = vfeed.get_edb()
    for i in range(0, len(cveEDB)):
        print '[edb_id]:', cveEDB[i]['id']
        print '[edb_exploit]:', cveEDB[i]['file']

    print ''
    print '[stats] %d ExploitDB id(s)' % len(cveEDB)


def call_get_milw0rm(vfeed):

    cveMILW = vfeed.get_milw0rm()
    for i in range(0, len(cveMILW)):
        print '[milw0rm_id]:', cveMILW[i]['id']

    print ''
    print '[stats] %d Milw0rm id(s)' % len(cveMILW)

def call_get_saint(vfeed):

    cveSAINT = vfeed.get_saint()
    for i in range(0, len(cveSAINT)):
        print '[saintexploit_id]:', cveSAINT[i]['id']
        print '[saintexploit_title]:', cveSAINT[i]['title']
        print '[saintexploit_file]:', cveSAINT[i]['file']

    print ''
    print '[stats] %d SaintExploit id(s)' % len(cveSAINT)


def call_get_msf(vfeed):

    cveMSF = vfeed.get_msf()
    for i in range(0, len(cveMSF)):
        print '[msf_id]:', cveMSF[i]['id']
        print '[msf_title]:', cveMSF[i]['title']
        print '[msf_file]:', cveMSF[i]['file']

    print ''
    print '[stats] %d Metasploit Exploits/Plugins' % len(cveMSF)


def call_get_ms(vfeed):

    cveMS = vfeed.get_ms()
    for i in range(0, len(cveMS)):
        print '[Microsoft_ms_id]:', cveMS[i]['id']
        print '[Microsoft_ms_title]:', cveMS[i]['title']

    print ''
    print '[stats] %d Microsoft MS Patch(s)' % len(cveMS)


def call_get_kb(vfeed):

    cveKB = vfeed.get_kb()
    for i in range(0, len(cveKB)):
        print '[Microsoft_kb_id]:', cveKB[i]['id']
        print '[Microsoft_kb_id]:', cveKB[i]['title']  
    print ''
    print '[stats] %d Microsoft KB bulletin(s)' % len(cveKB)


def call_get_aixapar(vfeed):

    cveAIX = vfeed.get_aixapar()
    for i in range(0, len(cveAIX)):
        print '[IBM_AIXAPAR_id]:', cveAIX[i]['id']

    print ''
    print '[stats] %d IBM AIX APAR(s)' % len(cveAIX)


def call_get_redhat(vfeed):

    cveRHEL, cveBUGZILLA = vfeed.get_redhat()
    for i in range(0, len(cveRHEL)):
        print '[redhat_id]:', cveRHEL[i]['id']
        print '[redhat_patch_title]:', cveRHEL[i]['title']
        print '[redhat_oval_id]:', cveRHEL[i]['oval']

    print ''
    print '[stats] %d Redhat id(s)' % len(cveRHEL)
    print ''
    
    for i in range(0, len(cveBUGZILLA)):
        print '[redhat_bugzilla_issued]:', cveBUGZILLA[i]['date_issue']
        print '[redhat_bugzilla__id]:', cveBUGZILLA[i]['id']
        print '[redhat_bugzilla__title]:', cveBUGZILLA[i]['title']
    
    print ''
    print '[stats] %d Bugzilla id(s)' %len(cveBUGZILLA)


def call_get_suse(vfeed):

    cveSUSE = vfeed.get_suse()
    for i in range(0, len(cveSUSE)):
        print '[suse_id]:', cveSUSE[i]['id']

    print ''
    print '[stats] %d Suse id(s)' % len(cveSUSE)

def call_get_cisco(vfeed):

    cveCISCO = vfeed.get_cisco()
    for i in range(0, len(cveCISCO)):
        print '[cisco_id]:', cveCISCO[i]['id']

    print ''
    print '[stats] %d Cisco id(s)' % len(cveCISCO)

def call_get_ubuntu(vfeed):

    cveUBUNTU = vfeed.get_ubuntu()
    for i in range(0, len(cveUBUNTU)):
        print '[ubuntu_id]:', cveUBUNTU[i]['id']

    print ''
    print '[stats] %d Ubuntu id(s)' % len(cveUBUNTU)

def call_get_gentoo(vfeed):

    cveGENTOO = vfeed.get_gentoo()
    for i in range(0, len(cveGENTOO)):
        print '[gentoo_id]:', cveGENTOO[i]['id']

    print ''
    print '[stats] %d Gentoo id(s)' % len(cveGENTOO)

def call_get_fedora(vfeed):

    cveFEDORA = vfeed.get_fedora()
    for i in range(0, len(cveFEDORA)):
        print '[fedora_id]:', cveFEDORA[i]['id']

    print ''
    print '[stats] %d Fedora id(s)' % len(cveFEDORA)



def call_get_debian(vfeed):

    cveDEBIAN = vfeed.get_debian()
    for i in range(0, len(cveDEBIAN)):
        print '[debian_id]:', cveDEBIAN[i]['id']

    print ''
    print '[stats] %d Debian id(s)' % len(cveDEBIAN)


def call_get_mandriva(vfeed):

    cveMANDRIVA = vfeed.get_mandriva()
    for i in range(0, len(cveMANDRIVA)):
        print '[mandriva_id]:', cveMANDRIVA[i]['id']

    print ''
    print '[stats] %d Mandriva id(s)' % len(cveMANDRIVA)

def call_get_vmware(vfeed):

    cveVMWARE = vfeed.get_vmware()
    for i in range(0, len(cveVMWARE)):
        print '[vmware_id]:', cveVMWARE[i]['id']

    print ''
    print '[stats] %d VMware id(s)' % len(cveVMWARE)

def call_get_hp(vfeed):

    cveHP = vfeed.get_hp()
    for i in range(0, len(cveHP)):
        print '[hp_id]:', cveHP[i]['id']
        print '[hp_link]', cveHP[i]['link']
    print ''
    print '[stats] %d HP id(s)' % len(cveHP)
    
def call_get_risk(vfeed):

    cveRISK = vfeed.get_risk()
    cvssScore = vfeed.get_cvss()

    print 'Severity:', cveRISK['severitylevel']
    print 'Top vulnerablity:', cveRISK['topvulnerable']
    print '\t[cvss_base]:', cvssScore['base']
    print '\t[cvss_impact]:', cvssScore['impact']
    print '\t[cvss_exploit]:', cvssScore['exploit']
    print 'PCI compliance:', cveRISK['pciCompliance']
    print 'is Top alert:', cveRISK['topAlert']

def main():

    if len(sys.argv) == 3:
        myCVE = sys.argv[2]
        apiMethod = sys.argv[1]
        
        if apiMethod == "export":
            vfeed = vFeedXML(myCVE)
            vfeed.export()
            exit(0)
    
        vfeed = vFeed(myCVE)
        try:
            globals()['call_%s' % apiMethod](vfeed)
        except:
            print'[error] the method %s is not implemented' % apiMethod
        else:
            exit(0)
   
    elif len(sys.argv) == 2:
        apiMethod = sys.argv[1]
        if apiMethod == "update":
            db = vFeedUpdate()
            db.update()
            exit(0)
        
        if apiMethod == "stats":
            stat = vFeedStats()
            stat.stats()
            exit(0)           
            
        if apiMethod == "latest_cve":
            stat = vFeedStats()
            stat.latest_cve()
            exit(0)    
        
        
        
        else:
           get_help()
    else:
        get_help() 

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = vfeed_calls_samples
#!/usr/bin/env python


from vfeed import vFeed, vFeedInfo, vFeedXML

'''
vfeed_calls_sample.py -  Sample script to call methods from your programs
Wiki documentation https://github.com/toolswatch/vFeed/wiki

'''

# create an instance of the class vFeedInfo
print '[instance] creating an instance with vFeedApi.vFeedInfo() '
info = vFeedInfo()

print '[invoking] the get_version() method '
print 'version: ', info.get_version()['build']

print '[invoking] the get_owner() method '
print 'author (if you want to get in touch and say hello):', info.get_owner()['author']

print '[invoking] the get_config() method (note that the values are returned in dict. You can then read any key value you need ..'
print 'vFeed global config returned as dict:', info.get_config()['primary']


# Invoking the vFeed class

#cve = "cve-2007-5243"
#cve = "cve-2013-3238"
cve = "cve-2013-3661"
print '[setting] using cve ', cve

# create an instance of the class vFeed and pass the cve
print '[instance] creating an instance with vFeedApi.vFeed(cve) '
vfeed = vFeed(cve)


print '[invoking] the get_cve() method '
# invoking the get_cve method
cveInfo = vfeed.get_cve()

if cveInfo:

# returned data is a dictionary with 3 keys.
    print 'description: ', cveInfo['summary']
    print 'published date: ', cveInfo['published']
    print 'modified date: ', cveInfo['modified']


# invoking the get_cvss method

print '[invoking] the get_cvss() method '
cvssScore = vfeed.get_cvss()

if cvssScore:
    print 'base score:', cvssScore['base']
    print 'impact score:', cvssScore['impact']
    print 'exploit score:', cvssScore['exploit']
    print 'AV (access vector):', cvssScore['access_vector']
    print 'AC (access complexity):', cvssScore['access_complexity']
    print 'Au (authentication):', cvssScore['authentication']    
    print 'C (confidentiality impact):', cvssScore['confidentiality_impact']     
    print 'I (integrity impact):', cvssScore['integrity_impact']     
    print 'A (availability impact):', cvssScore['availability_impact']
        

# invoking the get_refs method (it's not longer get_refserences)
print '[invoking] the get_refs() method '
cverefs = vfeed.get_refs()
for i in range(0, len(cverefs)):
    print 'refs id:', cverefs[i]['id']
    print 'refs link', cverefs[i]['link']
print 'total found refs', len(cverefs)

# invoking the get_cwe method
print '[invoking] the get_cwe() method '
cvecwe = vfeed.get_cwe()
for i in range(0, len(cvecwe)):
    print 'cwe id:', cvecwe[i]['id']
    print 'cwe title:', cvecwe[i]['title']
print 'total found cwe', len(cvecwe)

## invoking the get_capec method
print '[invoking] the get_capec() method '
cvecapec = vfeed.get_capec()
cvecwe = vfeed.get_cwe()

for i in range(len(cvecwe), len(cvecapec) + len(cvecwe)):
    print 'capec id %s associated with %s ' %(cvecapec[i]['id'],cvecapec[i]['cwe'])

print 'total found capec', len(cvecapec)

# invoking the get_category method
print '[invoking] the get_category() method '
cvecategory = vfeed.get_category()
cvecwe = vfeed.get_cwe()

for i in range(len(cvecwe), len(cvecategory) + len(cvecwe)):
    print '%s is listed in %s --> %s ' %(cve, cvecategory[i]['id'],cvecategory[i]['title'])


print '[invoking] the get_cpe() method '
cvecpe = vfeed.get_cpe()
for i in range(0, len(cvecpe)):
    print 'cpe id:', cvecpe[i]['id']
print 'total found cpe', len(cvecpe)


print '[invoking] the get_debian() method '
cveDEB = vfeed.get_debian()

for i in range(0, len(cveDEB)):
    print 'debian id:', cveDEB[i]['id']
print 'total found debian', len(cveDEB)



print '[invoking] the get_oval() method '
cveoval = vfeed.get_oval()
for i in range(0, len(cveoval)):
    print 'oval id:', cveoval[i]['id']
    print 'oval file', cveoval[i]['file']
print 'total found oval', len(cveoval)

print '[invoking] the get_nessus() method '
cvenessus = vfeed.get_nessus()

for i in range(0, len(cvenessus)):
    print 'nessus id:', cvenessus[i]['id']
    print 'nessus name', cvenessus[i]['name']
    print 'nessus file', cvenessus[i]['file']
    print 'nessus family', cvenessus[i]['family']
print 'total found nessus', len(cvenessus)

print '[invoking] the get_edb() method '
cveedb = vfeed.get_edb()

for i in range(0, len(cveedb)):
    print 'edb id:', cveedb[i]['id']
    print 'edb file', cveedb[i]['file']
print 'total found edb', len(cveedb)

print '[invoking] the get_saint() method '
cvesaintexp = vfeed.get_saint()
for i in range(0, len(cvesaintexp)):
    print 'saint Exploit id:', cvesaintexp[i]['id']
    print 'saint Exploit Title:', cvesaintexp[i]['title']
    print 'saint Exploit File:', cvesaintexp[i]['file']
print 'total found saint Exploit', len(cvesaintexp)

print '[invoking] the get_msf() method '
cvemsfexp = vfeed.get_msf()
for i in range(0, len(cvemsfexp)):
    print 'msf Exploit id:', cvemsfexp[i]['id']
    print '\tmsf Exploit Title:', cvemsfexp[i]['title']
    print '\tmsf Exploit File:', cvemsfexp[i]['file']
print 'total found msf Exploit', len(cvemsfexp)



print '[Generating XML] Invoking the exportXML() method '
##cve = "cve-2008-1447"
cve = "cve-2013-3661"
print '[New Instance] Creating new instance with cve ', cve
vfeed = vFeedXML(cve)
vfeed.export()


########NEW FILE########
