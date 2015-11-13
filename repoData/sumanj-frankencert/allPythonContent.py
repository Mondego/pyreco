__FILENAME__ = franken_conf_parse
import ConfigParser
def parse_config(configfile):
    fconfig = {}

    parser = ConfigParser.SafeConfigParser(defaults={'max_extensions':'20', \
                                'max_depth': '3', \
                                'ext_mod_prob': '0.0', \
                                'flip_critical_prob': '0.25', \
                                'self_signed_prob': '0.25', \
                                'invalid_ts_prob': '0.0', \
                                'public_key_len': '1024', \
                                'hash_for_sign': 'sha1', \
                                'randomize_serial': 'True', \
                                            })
    if (configfile!=""):
        parser.read(configfile)
    
    fconfig = parser.defaults() 
    boolean_trues = ['true', 'yes', 'y', '1']

    fconfig["max_extensions"] = int(fconfig["max_extensions"])
    fconfig["max_depth"] = int(fconfig["max_depth"])
    fconfig["ext_mod_prob"] = float(fconfig["ext_mod_prob"])
    fconfig["flip_critical_prob"] = float(fconfig["flip_critical_prob"])
    fconfig["self_signed_prob"] = float(fconfig["self_signed_prob"])
    fconfig["invalid_ts_prob"] = float(fconfig["invalid_ts_prob"])
    fconfig["public_key_len"] = int(fconfig["public_key_len"])
    fconfig["randomize_serial"] = fconfig["randomize_serial"].lower() in boolean_trues
    
    return fconfig

########NEW FILE########
__FILENAME__ = franken_core
from OpenSSL import crypto
import random
import collections
import sys

def get_extension_dict(certs):
    d = collections.defaultdict(dict)
    for cert in certs:
        extensions = get_extensions(cert)
        for i,extension in enumerate(extensions):
            """
            PyOpenSSL's get_short_name return UNKN for all unknown extensions
            This is bad for a mapping, our patched PyOpenSSL code has a 
            get_oid function.
            """
            d[extension.get_oid()][extension.get_data()] = extension
    for k in d.keys():
        d[k] = d[k].values()
    return d

def get_extensions(cert):
    return  [cert.get_extension(i) \
                for i in range(0, cert.get_extension_count())]

def generate_cert(certificates, pkey, signing_key, issuer, max_extensions, \
                  extensions, flip_probability=0.25, \
                  ext_mod_probability=0.0, invalid_ts_probability = 0.0, \
                  hash_for_sign="sha1", randomize_serial=False):
    cert = crypto.X509()
   

    cert.set_pubkey(pkey)
    pick = random.choice(certificates)
    cert.set_notAfter(pick.get_notAfter())
    pick = random.choice(certificates)
    cert.set_notBefore(pick.get_notBefore())
    if randomize_serial:
        cert.set_serial_number(random.randint(2**128,2**159))
    else:
        pick = random.choice(certificates)
        cert.set_serial_number(pick.get_serial_number())
    pick = random.choice(certificates)
    cert.set_subject(pick.get_subject())
    if not issuer is None:
        cert.set_issuer(issuer)
    else:
        cert.set_issuer(cert.get_subject())

    # overwrite the timestamps if asked by the user
    if random.random() < invalid_ts_probability:
        if random.random() < 0.5:
            notvalidyet = b(datetime.now() + timedelta(days=1).\
                                strftime("%Y%m%d%H%M%SZ"))
            cert.set_notBefore(notvalidyet)
        else:
            expired = b(datetime.now() - timedelta(days=1).\
                                strftime("%Y%m%d%H%M%SZ"))
            cert.set_notBefore(expired)
                
        
    # handle the extensions
    # Currently we chose [0,max] extension types
    # then pick one entry randomly from each type
    # Hacked pyOpenSSL to support poking into the data
    # TODO: Multiple extensions of the same type?
    sample = random.randint(0, max_extensions)
    choices = random.sample(extensions.keys(), sample)
    new_extensions = [random.choice(extensions[name]) for name in choices]
    for extension in new_extensions:
        if random.random() < flip_probability:
            extension.set_critical(1 - extension.get_critical())
        if random.random() < ext_mod_probability:
            randstr = "".join( chr(random.randint(0, 255)) for i in range(7))
            extension.set_data(randstr)
        
    cert.add_extensions(new_extensions)
    if not issuer is None:
        cert.sign(signing_key, hash_for_sign)
    else:
        cert.sign(pkey,hash_for_sign)
    return pkey, cert

def generate(certificates, ca_cert, ca_key, fconfig, count=1, \
             extensions = None):

    certs = []

    flip_probability = fconfig["flip_critical_prob"]
    self_signed_probability = fconfig["self_signed_prob"]
    max_depth = fconfig["max_depth"]
    max_extensions = fconfig["max_extensions"]
    public_key_len = fconfig["public_key_len"]

    if extensions is None:
        extensions = get_extension_dict(certificates)

    max_extensions = min(max_extensions, len(extensions.keys()))
  
    #generate the key pairs once and reuse them for faster 
    #frankencert generation  
    pkeys = []
    for i in range(max_depth):
        pkey = crypto.PKey()
        pkey.generate_key(crypto.TYPE_RSA, public_key_len)
        pkeys.append(pkey)        

    progressbar_size = 10
    if (count>progressbar_size):
        step = count/progressbar_size
    else:
        step = 1 
    for i in range(count):
        if (i%step==0):
                sys.stdout.write(".")     
                sys.stdout.flush()     
            
        chain = []
        signing_key = ca_key
        issuer = ca_cert.get_subject()
        key = None
        length = random.randint(1,max_depth)
        if length == 1 and random.random() < self_signed_probability:
            issuer = None
        for j in range(length):
            key, cert = generate_cert(certificates, pkeys[j], signing_key, issuer, \
                         max_extensions, extensions, fconfig["flip_critical_prob"], \
                          fconfig["ext_mod_prob"], fconfig["invalid_ts_prob"], \
                        fconfig["hash_for_sign"], fconfig["randomize_serial"])
            signing_key = key
            issuer = cert.get_subject()
            chain.append(cert)
        certs.append((key,list(reversed(chain))))
    
    return certs

########NEW FILE########
__FILENAME__ = franken_generate
#!/usr/bin/env python
import franken_core
import franken_util
from OpenSSL import crypto 
import sys
import franken_conf_parse

if (len(sys.argv)<5):
    print "Usage: "+sys.argv[0]+" "+"seed_cert_path"+" ca_cert "+\
                " out_cert_path "+ " count " +" [config] "
    sys.exit(-1)

input_cert_path = sys.argv[1]
ca_cert_path = sys.argv[2]
out_cert_path = sys.argv[3]
n_outcert = int(sys.argv[4])

if (len(sys.argv)>5):
    configfile = sys.argv[5]
else:
    configfile = ""

fconf = franken_conf_parse.parse_config(configfile) 
certs = franken_util.load_dir(input_cert_path)
with open(ca_cert_path, 'rt') as ca_cert_file:
    ca_cert = crypto.load_certificate(crypto.FILETYPE_PEM, ca_cert_file.read())

with open(ca_cert_path, 'rt') as ca_key_file:
    ca_private_key = crypto.load_privatekey(crypto.FILETYPE_PEM, \
                                                ca_key_file.read()) 
sys.stdout.write("Generating frankencerts")
max_certs_in_mem = 200
nc = n_outcert/max_certs_in_mem
remaining_cnt = n_outcert
for i in range(nc+1):
    if (remaining_cnt > max_certs_in_mem):
        franken_certs = franken_core.generate(certs, ca_cert, ca_private_key, \
                                    fconf, count=max_certs_in_mem)
        remaining_cnt = remaining_cnt - max_certs_in_mem
    else:
        franken_certs = franken_core.generate(certs, ca_cert, ca_private_key, \
                                    fconf, count=remaining_cnt)
        remaining_cnt = 0
                
    franken_util.dump_certs(franken_certs, "frankencert", out_cert_path, max_certs_in_mem*i)
    del franken_certs

sys.stdout.write("\n")     
sys.stdout.flush()   

########NEW FILE########
__FILENAME__ = franken_util
#!/usr/bin/env python
import os
from OpenSSL import crypto
import subprocess
import sys

#write out all the certs
def dump_certs(certs, prefix, path, name_begin=0):
    for i,cert in enumerate(certs):
        key,certs = cert
        with open(os.path.join(path, "%s-%d.pem" % (prefix, name_begin+i)), \
                   "w") as f:
            f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key))
            for cert in certs:
                f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))


#load all certs from a directory
def load_dir(path):      
    certs = []        
    files = os.listdir(path)
    nfiles =  len(files)                                               
    files = map(lambda f : os.path.join(path, f), files)
    step = max(1,nfiles/10)
    count  = 0
    sys.stdout.write("Loading seed certificates") 
    for infile in files:
        count = (count+1) % step
        if (count==0):
            sys.stdout.write(".") 
            sys.stdout.flush()
        with open(infile) as f:
            buf = f.read()
            try:
                certs.append(crypto.load_certificate(crypto.FILETYPE_PEM, buf))
            except:
                print "Skipping: "+infile
    sys.stdout.write("\n")
    sys.stdout.flush()
 
    return certs

#recycle an existing certfile containing arbitrarily long cert chains 
#with new CA  
def recycle_cert(inpath, outpath, cafile, fix_timestamps):
    incerts = []
    with open(inpath) as f:
        buf = f.read()
        pattern = "-----BEGIN CERTIFICATE-----"
        index  = 0
        while True:
            index = buf.find(pattern, index)
            if (index==-1):
                break
            cert = crypto.load_certificate(crypto.FILETYPE_PEM, buf[index:])
            index = index + len(pattern)
            incerts.append(cert)
    with open(cafile) as f:
        buf = f.read()
        cacert = crypto.load_certificate(crypto.FILETYPE_PEM, buf)
    
    with open(cafile) as f:
        buf = f.read()
        cakey = crypto.load_privatekey(crypto.FILETYPE_PEM, buf)
    
    print len(incerts)
   
    pkeys = [] 
    for i in range(len(incerts)):
        pkey = crypto.PKey()
        pkey.generate_key(crypto.TYPE_RSA, 1024)
        pkeys.append(pkey)
    
    for i in range(len(incerts)):
        incerts[i].set_pubkey(pkeys[i])
        if (fix_timestamps):
            now = b(datetime.now().strftime("%Y%m%d%H%M%SZ"))
            expire  = b((datetime.now() + timedelta(days=100))\
                   .strftime("%Y%m%d%H%M%SZ"))
            incerts[i].set_notBefore(now)
            incerts[i].set_notAfter(expire)
   
        if (i==len(incerts)-1): 
            incerts[i].set_issuer(cacert.get_subject())
            incerts[i].sign(cakey,"sha1")
        else:    
            incerts[i].set_issuer(incerts[i+1].get_subject())
            incerts[i].sign(pkeys[i+1],"sha1")

    
    with open(outpath, "w") as f:
        f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, pkeys[0]))
        for i in range(len(incerts)):
            f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, incerts[i]))

#Print all certs in a file, openssl x509 only prints the first one 
#Uses the openssl x509 command, pretty hacky but it works 
def print_cert(inpath):
    output = ""

    with open(inpath) as f:
        buf = f.read()
        pattern = "-----BEGIN CERTIFICATE-----"
        index  = 0
        i = 0
        while True:
            index = buf.find(pattern, index)
            if (index==-1):
                break
            p = subprocess.Popen(["openssl", "x509", "-text"], \
                            stdout=subprocess.PIPE, stdin=subprocess.PIPE,\
                            stderr=subprocess.STDOUT)
            output += p.communicate(input=buf[index:])[0]
            index = index + len(pattern)
            i += 1
    print output.find("Certificate:")
    print output 

########NEW FILE########
__FILENAME__ = test_crypto
# Copyright (c) Jean-Paul Calderone
# See LICENSE file for details.

"""
Unit tests for L{OpenSSL.crypto}.
"""

from unittest import main

import os, re
from subprocess import PIPE, Popen
from datetime import datetime, timedelta

from OpenSSL.crypto import TYPE_RSA, TYPE_DSA, Error, PKey, PKeyType
from OpenSSL.crypto import X509, X509Type, X509Name, X509NameType
from OpenSSL.crypto import X509Req, X509ReqType
from OpenSSL.crypto import X509Extension, X509ExtensionType
from OpenSSL.crypto import load_certificate, load_privatekey
from OpenSSL.crypto import FILETYPE_PEM, FILETYPE_ASN1, FILETYPE_TEXT
from OpenSSL.crypto import dump_certificate, load_certificate_request
from OpenSSL.crypto import dump_certificate_request, dump_privatekey
from OpenSSL.crypto import PKCS7Type, load_pkcs7_data
from OpenSSL.crypto import PKCS12, PKCS12Type, load_pkcs12
from OpenSSL.crypto import CRL, Revoked, load_crl
from OpenSSL.crypto import NetscapeSPKI, NetscapeSPKIType
from OpenSSL.crypto import sign, verify
from OpenSSL.test.util import TestCase, bytes, b

def normalize_certificate_pem(pem):
    return dump_certificate(FILETYPE_PEM, load_certificate(FILETYPE_PEM, pem))


def normalize_privatekey_pem(pem):
    return dump_privatekey(FILETYPE_PEM, load_privatekey(FILETYPE_PEM, pem))


root_cert_pem = b("""-----BEGIN CERTIFICATE-----
MIIC7TCCAlagAwIBAgIIPQzE4MbeufQwDQYJKoZIhvcNAQEFBQAwWDELMAkGA1UE
BhMCVVMxCzAJBgNVBAgTAklMMRAwDgYDVQQHEwdDaGljYWdvMRAwDgYDVQQKEwdU
ZXN0aW5nMRgwFgYDVQQDEw9UZXN0aW5nIFJvb3QgQ0EwIhgPMjAwOTAzMjUxMjM2
NThaGA8yMDE3MDYxMTEyMzY1OFowWDELMAkGA1UEBhMCVVMxCzAJBgNVBAgTAklM
MRAwDgYDVQQHEwdDaGljYWdvMRAwDgYDVQQKEwdUZXN0aW5nMRgwFgYDVQQDEw9U
ZXN0aW5nIFJvb3QgQ0EwgZ8wDQYJKoZIhvcNAQEBBQADgY0AMIGJAoGBAPmaQumL
urpE527uSEHdL1pqcDRmWzu+98Y6YHzT/J7KWEamyMCNZ6fRW1JCR782UQ8a07fy
2xXsKy4WdKaxyG8CcatwmXvpvRQ44dSANMihHELpANTdyVp6DCysED6wkQFurHlF
1dshEaJw8b/ypDhmbVIo6Ci1xvCJqivbLFnbAgMBAAGjgbswgbgwHQYDVR0OBBYE
FINVdy1eIfFJDAkk51QJEo3IfgSuMIGIBgNVHSMEgYAwfoAUg1V3LV4h8UkMCSTn
VAkSjch+BK6hXKRaMFgxCzAJBgNVBAYTAlVTMQswCQYDVQQIEwJJTDEQMA4GA1UE
BxMHQ2hpY2FnbzEQMA4GA1UEChMHVGVzdGluZzEYMBYGA1UEAxMPVGVzdGluZyBS
b290IENBggg9DMTgxt659DAMBgNVHRMEBTADAQH/MA0GCSqGSIb3DQEBBQUAA4GB
AGGCDazMJGoWNBpc03u6+smc95dEead2KlZXBATOdFT1VesY3+nUOqZhEhTGlDMi
hkgaZnzoIq/Uamidegk4hirsCT/R+6vsKAAxNTcBjUeZjlykCJWy5ojShGftXIKY
w/njVbKMXrvc83qmTdGl3TAM0fxQIpqgcglFLveEBgzn
-----END CERTIFICATE-----
""")

root_key_pem = b("""-----BEGIN RSA PRIVATE KEY-----
MIICXQIBAAKBgQD5mkLpi7q6ROdu7khB3S9aanA0Zls7vvfGOmB80/yeylhGpsjA
jWen0VtSQke/NlEPGtO38tsV7CsuFnSmschvAnGrcJl76b0UOOHUgDTIoRxC6QDU
3claegwsrBA+sJEBbqx5RdXbIRGicPG/8qQ4Zm1SKOgotcbwiaor2yxZ2wIDAQAB
AoGBAPCgMpmLxzwDaUmcFbTJUvlLW1hoxNNYSu2jIZm1k/hRAcE60JYwvBkgz3UB
yMEh0AtLxYe0bFk6EHah11tMUPgscbCq73snJ++8koUw+csk22G65hOs51bVb7Aa
6JBe67oLzdtvgCUFAA2qfrKzWRZzAdhUirQUZgySZk+Xq1pBAkEA/kZG0A6roTSM
BVnx7LnPfsycKUsTumorpXiylZJjTi9XtmzxhrYN6wgZlDOOwOLgSQhszGpxVoMD
u3gByT1b2QJBAPtL3mSKdvwRu/+40zaZLwvSJRxaj0mcE4BJOS6Oqs/hS1xRlrNk
PpQ7WJ4yM6ZOLnXzm2mKyxm50Mv64109FtMCQQDOqS2KkjHaLowTGVxwC0DijMfr
I9Lf8sSQk32J5VWCySWf5gGTfEnpmUa41gKTMJIbqZZLucNuDcOtzUaeWZlZAkA8
ttXigLnCqR486JDPTi9ZscoZkZ+w7y6e/hH8t6d5Vjt48JVyfjPIaJY+km58LcN3
6AWSeGAdtRFHVzR7oHjVAkB4hutvxiOeiIVQNBhM6RSI9aBPMI21DoX2JRoxvNW2
cbvAhow217X9V0dVerEOKxnNYspXRrh36h7k4mQA+sDq
-----END RSA PRIVATE KEY-----
""")

server_cert_pem = b("""-----BEGIN CERTIFICATE-----
MIICKDCCAZGgAwIBAgIJAJn/HpR21r/8MA0GCSqGSIb3DQEBBQUAMFgxCzAJBgNV
BAYTAlVTMQswCQYDVQQIEwJJTDEQMA4GA1UEBxMHQ2hpY2FnbzEQMA4GA1UEChMH
VGVzdGluZzEYMBYGA1UEAxMPVGVzdGluZyBSb290IENBMCIYDzIwMDkwMzI1MTIz
NzUzWhgPMjAxNzA2MTExMjM3NTNaMBgxFjAUBgNVBAMTDWxvdmVseSBzZXJ2ZXIw
gZ8wDQYJKoZIhvcNAQEBBQADgY0AMIGJAoGBAL6m+G653V0tpBC/OKl22VxOi2Cv
lK4TYu9LHSDP9uDVTe7V5D5Tl6qzFoRRx5pfmnkqT5B+W9byp2NU3FC5hLm5zSAr
b45meUhjEJ/ifkZgbNUjHdBIGP9MAQUHZa5WKdkGIJvGAvs8UzUqlr4TBWQIB24+
lJ+Ukk/CRgasrYwdAgMBAAGjNjA0MB0GA1UdDgQWBBS4kC7Ij0W1TZXZqXQFAM2e
gKEG2DATBgNVHSUEDDAKBggrBgEFBQcDATANBgkqhkiG9w0BAQUFAAOBgQBh30Li
dJ+NlxIOx5343WqIBka3UbsOb2kxWrbkVCrvRapCMLCASO4FqiKWM+L0VDBprqIp
2mgpFQ6FHpoIENGvJhdEKpptQ5i7KaGhnDNTfdy3x1+h852G99f1iyj0RmbuFcM8
uzujnS8YXWvM7DM1Ilozk4MzPug8jzFp5uhKCQ==
-----END CERTIFICATE-----
""")

server_key_pem = normalize_privatekey_pem(b("""-----BEGIN RSA PRIVATE KEY-----
MIICWwIBAAKBgQC+pvhuud1dLaQQvzipdtlcTotgr5SuE2LvSx0gz/bg1U3u1eQ+
U5eqsxaEUceaX5p5Kk+QflvW8qdjVNxQuYS5uc0gK2+OZnlIYxCf4n5GYGzVIx3Q
SBj/TAEFB2WuVinZBiCbxgL7PFM1Kpa+EwVkCAduPpSflJJPwkYGrK2MHQIDAQAB
AoGAbwuZ0AR6JveahBaczjfnSpiFHf+mve2UxoQdpyr6ROJ4zg/PLW5K/KXrC48G
j6f3tXMrfKHcpEoZrQWUfYBRCUsGD5DCazEhD8zlxEHahIsqpwA0WWssJA2VOLEN
j6DuV2pCFbw67rfTBkTSo32ahfXxEKev5KswZk0JIzH3ooECQQDgzS9AI89h0gs8
Dt+1m11Rzqo3vZML7ZIyGApUzVan+a7hbc33nbGRkAXjHaUBJO31it/H6dTO+uwX
msWwNG5ZAkEA2RyFKs5xR5USTFaKLWCgpH/ydV96KPOpBND7TKQx62snDenFNNbn
FwwOhpahld+vqhYk+pfuWWUpQciE+Bu7ZQJASjfT4sQv4qbbKK/scePicnDdx9th
4e1EeB9xwb+tXXXUo/6Bor/AcUNwfiQ6Zt9PZOK9sR3lMZSsP7rMi7kzuQJABie6
1sXXjFH7nNJvRG4S39cIxq8YRYTy68II/dlB2QzGpKxV/POCxbJ/zu0CU79tuYK7
NaeNCFfH3aeTrX0LyQJAMBWjWmeKM2G2sCExheeQK0ROnaBC8itCECD4Jsve4nqf
r50+LF74iLXFwqysVCebPKMOpDWp/qQ1BbJQIPs7/A==
-----END RSA PRIVATE KEY-----
"""))

client_cert_pem = b("""-----BEGIN CERTIFICATE-----
MIICJjCCAY+gAwIBAgIJAKxpFI5lODkjMA0GCSqGSIb3DQEBBQUAMFgxCzAJBgNV
BAYTAlVTMQswCQYDVQQIEwJJTDEQMA4GA1UEBxMHQ2hpY2FnbzEQMA4GA1UEChMH
VGVzdGluZzEYMBYGA1UEAxMPVGVzdGluZyBSb290IENBMCIYDzIwMDkwMzI1MTIz
ODA1WhgPMjAxNzA2MTExMjM4MDVaMBYxFDASBgNVBAMTC3VnbHkgY2xpZW50MIGf
MA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDAZh/SRtNm5ntMT4qb6YzEpTroMlq2
rn+GrRHRiZ+xkCw/CGNhbtPir7/QxaUj26BSmQrHw1bGKEbPsWiW7bdXSespl+xK
iku4G/KvnnmWdeJHqsiXeUZtqurMELcPQAw9xPHEuhqqUJvvEoMTsnCEqGM+7Dtb
oCRajYyHfluARQIDAQABozYwNDAdBgNVHQ4EFgQUNQB+qkaOaEVecf1J3TTUtAff
0fAwEwYDVR0lBAwwCgYIKwYBBQUHAwIwDQYJKoZIhvcNAQEFBQADgYEAyv/Jh7gM
Q3OHvmsFEEvRI+hsW8y66zK4K5de239Y44iZrFYkt7Q5nBPMEWDj4F2hLYWL/qtI
9Zdr0U4UDCU9SmmGYh4o7R4TZ5pGFvBYvjhHbkSFYFQXZxKUi+WUxplP6I0wr2KJ
PSTJCjJOn3xo2NTKRgV1gaoTf2EhL+RG8TQ=
-----END CERTIFICATE-----
""")

client_key_pem = normalize_privatekey_pem(b("""-----BEGIN RSA PRIVATE KEY-----
MIICXgIBAAKBgQDAZh/SRtNm5ntMT4qb6YzEpTroMlq2rn+GrRHRiZ+xkCw/CGNh
btPir7/QxaUj26BSmQrHw1bGKEbPsWiW7bdXSespl+xKiku4G/KvnnmWdeJHqsiX
eUZtqurMELcPQAw9xPHEuhqqUJvvEoMTsnCEqGM+7DtboCRajYyHfluARQIDAQAB
AoGATkZ+NceY5Glqyl4mD06SdcKfV65814vg2EL7V9t8+/mi9rYL8KztSXGlQWPX
zuHgtRoMl78yQ4ZJYOBVo+nsx8KZNRCEBlE19bamSbQLCeQMenWnpeYyQUZ908gF
h6L9qsFVJepgA9RDgAjyDoS5CaWCdCCPCH2lDkdcqC54SVUCQQDseuduc4wi8h4t
V8AahUn9fn9gYfhoNuM0gdguTA0nPLVWz4hy1yJiWYQe0H7NLNNTmCKiLQaJpAbb
TC6vE8C7AkEA0Ee8CMJUc20BnGEmxwgWcVuqFWaKCo8jTH1X38FlATUsyR3krjW2
dL3yDD9NwHxsYP7nTKp/U8MV7U9IBn4y/wJBAJl7H0/BcLeRmuJk7IqJ7b635iYB
D/9beFUw3MUXmQXZUfyYz39xf6CDZsu1GEdEC5haykeln3Of4M9d/4Kj+FcCQQCY
si6xwT7GzMDkk/ko684AV3KPc/h6G0yGtFIrMg7J3uExpR/VdH2KgwMkZXisSMvw
JJEQjOMCVsEJlRk54WWjAkEAzoZNH6UhDdBK5F38rVt/y4SEHgbSfJHIAmPS32Kq
f6GGcfNpip0Uk7q7udTKuX7Q/buZi/C4YW7u3VKAquv9NA==
-----END RSA PRIVATE KEY-----
"""))

cleartextCertificatePEM = b("""-----BEGIN CERTIFICATE-----
MIIC7TCCAlagAwIBAgIIPQzE4MbeufQwDQYJKoZIhvcNAQEFBQAwWDELMAkGA1UE
BhMCVVMxCzAJBgNVBAgTAklMMRAwDgYDVQQHEwdDaGljYWdvMRAwDgYDVQQKEwdU
ZXN0aW5nMRgwFgYDVQQDEw9UZXN0aW5nIFJvb3QgQ0EwIhgPMjAwOTAzMjUxMjM2
NThaGA8yMDE3MDYxMTEyMzY1OFowWDELMAkGA1UEBhMCVVMxCzAJBgNVBAgTAklM
MRAwDgYDVQQHEwdDaGljYWdvMRAwDgYDVQQKEwdUZXN0aW5nMRgwFgYDVQQDEw9U
ZXN0aW5nIFJvb3QgQ0EwgZ8wDQYJKoZIhvcNAQEBBQADgY0AMIGJAoGBAPmaQumL
urpE527uSEHdL1pqcDRmWzu+98Y6YHzT/J7KWEamyMCNZ6fRW1JCR782UQ8a07fy
2xXsKy4WdKaxyG8CcatwmXvpvRQ44dSANMihHELpANTdyVp6DCysED6wkQFurHlF
1dshEaJw8b/ypDhmbVIo6Ci1xvCJqivbLFnbAgMBAAGjgbswgbgwHQYDVR0OBBYE
FINVdy1eIfFJDAkk51QJEo3IfgSuMIGIBgNVHSMEgYAwfoAUg1V3LV4h8UkMCSTn
VAkSjch+BK6hXKRaMFgxCzAJBgNVBAYTAlVTMQswCQYDVQQIEwJJTDEQMA4GA1UE
BxMHQ2hpY2FnbzEQMA4GA1UEChMHVGVzdGluZzEYMBYGA1UEAxMPVGVzdGluZyBS
b290IENBggg9DMTgxt659DAMBgNVHRMEBTADAQH/MA0GCSqGSIb3DQEBBQUAA4GB
AGGCDazMJGoWNBpc03u6+smc95dEead2KlZXBATOdFT1VesY3+nUOqZhEhTGlDMi
hkgaZnzoIq/Uamidegk4hirsCT/R+6vsKAAxNTcBjUeZjlykCJWy5ojShGftXIKY
w/njVbKMXrvc83qmTdGl3TAM0fxQIpqgcglFLveEBgzn
-----END CERTIFICATE-----
""")

cleartextPrivateKeyPEM = normalize_privatekey_pem(b("""\
-----BEGIN RSA PRIVATE KEY-----
MIICXQIBAAKBgQD5mkLpi7q6ROdu7khB3S9aanA0Zls7vvfGOmB80/yeylhGpsjA
jWen0VtSQke/NlEPGtO38tsV7CsuFnSmschvAnGrcJl76b0UOOHUgDTIoRxC6QDU
3claegwsrBA+sJEBbqx5RdXbIRGicPG/8qQ4Zm1SKOgotcbwiaor2yxZ2wIDAQAB
AoGBAPCgMpmLxzwDaUmcFbTJUvlLW1hoxNNYSu2jIZm1k/hRAcE60JYwvBkgz3UB
yMEh0AtLxYe0bFk6EHah11tMUPgscbCq73snJ++8koUw+csk22G65hOs51bVb7Aa
6JBe67oLzdtvgCUFAA2qfrKzWRZzAdhUirQUZgySZk+Xq1pBAkEA/kZG0A6roTSM
BVnx7LnPfsycKUsTumorpXiylZJjTi9XtmzxhrYN6wgZlDOOwOLgSQhszGpxVoMD
u3gByT1b2QJBAPtL3mSKdvwRu/+40zaZLwvSJRxaj0mcE4BJOS6Oqs/hS1xRlrNk
PpQ7WJ4yM6ZOLnXzm2mKyxm50Mv64109FtMCQQDOqS2KkjHaLowTGVxwC0DijMfr
I9Lf8sSQk32J5VWCySWf5gGTfEnpmUa41gKTMJIbqZZLucNuDcOtzUaeWZlZAkA8
ttXigLnCqR486JDPTi9ZscoZkZ+w7y6e/hH8t6d5Vjt48JVyfjPIaJY+km58LcN3
6AWSeGAdtRFHVzR7oHjVAkB4hutvxiOeiIVQNBhM6RSI9aBPMI21DoX2JRoxvNW2
cbvAhow217X9V0dVerEOKxnNYspXRrh36h7k4mQA+sDq
-----END RSA PRIVATE KEY-----
"""))

cleartextCertificateRequestPEM = b("""-----BEGIN CERTIFICATE REQUEST-----
MIIBnjCCAQcCAQAwXjELMAkGA1UEBhMCVVMxCzAJBgNVBAgTAklMMRAwDgYDVQQH
EwdDaGljYWdvMRcwFQYDVQQKEw5NeSBDb21wYW55IEx0ZDEXMBUGA1UEAxMORnJl
ZGVyaWNrIERlYW4wgZ8wDQYJKoZIhvcNAQEBBQADgY0AMIGJAoGBANp6Y17WzKSw
BsUWkXdqg6tnXy8H8hA1msCMWpc+/2KJ4mbv5NyD6UD+/SqagQqulPbF/DFea9nA
E0zhmHJELcM8gUTIlXv/cgDWnmK4xj8YkjVUiCdqKRAKeuzLG1pGmwwF5lGeJpXN
xQn5ecR0UYSOWj6TTGXB9VyUMQzCClcBAgMBAAGgADANBgkqhkiG9w0BAQUFAAOB
gQAAJGuF/R/GGbeC7FbFW+aJgr9ee0Xbl6nlhu7pTe67k+iiKT2dsl2ti68MVTnu
Vrb3HUNqOkiwsJf6kCtq5oPn3QVYzTa76Dt2y3Rtzv6boRSlmlfrgS92GNma8JfR
oICQk3nAudi6zl1Dix3BCv1pUp5KMtGn3MeDEi6QFGy2rA==
-----END CERTIFICATE REQUEST-----
""")

encryptedPrivateKeyPEM = b("""-----BEGIN RSA PRIVATE KEY-----
Proc-Type: 4,ENCRYPTED
DEK-Info: DES-EDE3-CBC,9573604A18579E9E

SHOho56WxDkT0ht10UTeKc0F5u8cqIa01kzFAmETw0MAs8ezYtK15NPdCXUm3X/2
a17G7LSF5bkxOgZ7vpXyMzun/owrj7CzvLxyncyEFZWvtvzaAhPhvTJtTIB3kf8B
8+qRcpTGK7NgXEgYBW5bj1y4qZkD4zCL9o9NQzsKI3Ie8i0239jsDOWR38AxjXBH
mGwAQ4Z6ZN5dnmM4fhMIWsmFf19sNyAML4gHenQCHhmXbjXeVq47aC2ProInJbrm
+00TcisbAQ40V9aehVbcDKtS4ZbMVDwncAjpXpcncC54G76N6j7F7wL7L/FuXa3A
fvSVy9n2VfF/pJ3kYSflLHH2G/DFxjF7dl0GxhKPxJjp3IJi9VtuvmN9R2jZWLQF
tfC8dXgy/P9CfFQhlinqBTEwgH0oZ/d4k4NVFDSdEMaSdmBAjlHpc+Vfdty3HVnV
rKXj//wslsFNm9kIwJGIgKUa/n2jsOiydrsk1mgH7SmNCb3YHgZhbbnq0qLat/HC
gHDt3FHpNQ31QzzL3yrenFB2L9osIsnRsDTPFNi4RX4SpDgNroxOQmyzCCV6H+d4
o1mcnNiZSdxLZxVKccq0AfRpHqpPAFnJcQHP6xyT9MZp6fBa0XkxDnt9kNU8H3Qw
7SJWZ69VXjBUzMlQViLuaWMgTnL+ZVyFZf9hTF7U/ef4HMLMAVNdiaGG+G+AjCV/
MbzjS007Oe4qqBnCWaFPSnJX6uLApeTbqAxAeyCql56ULW5x6vDMNC3dwjvS/CEh
11n8RkgFIQA0AhuKSIg3CbuartRsJnWOLwgLTzsrKYL4yRog1RJrtw==
-----END RSA PRIVATE KEY-----
""")

encryptedPrivateKeyPEMPassphrase = b("foobar")

# Some PKCS#7 stuff.  Generated with the openssl command line:
#
#    openssl crl2pkcs7 -inform pem -outform pem -certfile s.pem -nocrl
#
# with a certificate and key (but the key should be irrelevant) in s.pem
pkcs7Data = b("""\
-----BEGIN PKCS7-----
MIIDNwYJKoZIhvcNAQcCoIIDKDCCAyQCAQExADALBgkqhkiG9w0BBwGgggMKMIID
BjCCAm+gAwIBAgIBATANBgkqhkiG9w0BAQQFADB7MQswCQYDVQQGEwJTRzERMA8G
A1UEChMITTJDcnlwdG8xFDASBgNVBAsTC00yQ3J5cHRvIENBMSQwIgYDVQQDExtN
MkNyeXB0byBDZXJ0aWZpY2F0ZSBNYXN0ZXIxHTAbBgkqhkiG9w0BCQEWDm5ncHNA
cG9zdDEuY29tMB4XDTAwMDkxMDA5NTEzMFoXDTAyMDkxMDA5NTEzMFowUzELMAkG
A1UEBhMCU0cxETAPBgNVBAoTCE0yQ3J5cHRvMRIwEAYDVQQDEwlsb2NhbGhvc3Qx
HTAbBgkqhkiG9w0BCQEWDm5ncHNAcG9zdDEuY29tMFwwDQYJKoZIhvcNAQEBBQAD
SwAwSAJBAKy+e3dulvXzV7zoTZWc5TzgApr8DmeQHTYC8ydfzH7EECe4R1Xh5kwI
zOuuFfn178FBiS84gngaNcrFi0Z5fAkCAwEAAaOCAQQwggEAMAkGA1UdEwQCMAAw
LAYJYIZIAYb4QgENBB8WHU9wZW5TU0wgR2VuZXJhdGVkIENlcnRpZmljYXRlMB0G
A1UdDgQWBBTPhIKSvnsmYsBVNWjj0m3M2z0qVTCBpQYDVR0jBIGdMIGagBT7hyNp
65w6kxXlxb8pUU/+7Sg4AaF/pH0wezELMAkGA1UEBhMCU0cxETAPBgNVBAoTCE0y
Q3J5cHRvMRQwEgYDVQQLEwtNMkNyeXB0byBDQTEkMCIGA1UEAxMbTTJDcnlwdG8g
Q2VydGlmaWNhdGUgTWFzdGVyMR0wGwYJKoZIhvcNAQkBFg5uZ3BzQHBvc3QxLmNv
bYIBADANBgkqhkiG9w0BAQQFAAOBgQA7/CqT6PoHycTdhEStWNZde7M/2Yc6BoJu
VwnW8YxGO8Sn6UJ4FeffZNcYZddSDKosw8LtPOeWoK3JINjAk5jiPQ2cww++7QGG
/g5NDjxFZNDJP1dGiLAxPW6JXwov4v0FmdzfLOZ01jDcgQQZqEpYlgpuI5JEWUQ9
Ho4EzbYCOaEAMQA=
-----END PKCS7-----
""")

crlData = b("""\
-----BEGIN X509 CRL-----
MIIBWzCBxTANBgkqhkiG9w0BAQQFADBYMQswCQYDVQQGEwJVUzELMAkGA1UECBMC
SUwxEDAOBgNVBAcTB0NoaWNhZ28xEDAOBgNVBAoTB1Rlc3RpbmcxGDAWBgNVBAMT
D1Rlc3RpbmcgUm9vdCBDQRcNMDkwNzI2MDQzNDU2WhcNMTIwOTI3MDI0MTUyWjA8
MBUCAgOrGA8yMDA5MDcyNTIzMzQ1NlowIwICAQAYDzIwMDkwNzI1MjMzNDU2WjAM
MAoGA1UdFQQDCgEEMA0GCSqGSIb3DQEBBAUAA4GBAEBt7xTs2htdD3d4ErrcGAw1
4dKcVnIWTutoI7xxen26Wwvh8VCsT7i/UeP+rBl9rC/kfjWjzQk3/zleaarGTpBT
0yp4HXRFFoRhhSE/hP+eteaPXRgrsNRLHe9ZDd69wmh7J1wMDb0m81RG7kqcbsid
vrzEeLDRiiPl92dyyWmu
-----END X509 CRL-----
""")


# A broken RSA private key which can be used to test the error path through
# PKey.check.
inconsistentPrivateKeyPEM = b("""-----BEGIN RSA PRIVATE KEY-----
MIIBPAIBAAJBAKy+e3dulvXzV7zoTZWc5TzgApr8DmeQHTYC8ydfzH7EECe4R1Xh
5kwIzOuuFfn178FBiS84gngaNcrFi0Z5fAkCAwEaAQJBAIqm/bz4NA1H++Vx5Ewx
OcKp3w19QSaZAwlGRtsUxrP7436QjnREM3Bm8ygU11BjkPVmtrKm6AayQfCHqJoT
zIECIQDW0BoMoL0HOYM/mrTLhaykYAVqgIeJsPjvkEhTFXWBuQIhAM3deFAvWNu4
nklUQ37XsCT2c9tmNt1LAT+slG2JOTTRAiAuXDtC/m3NYVwyHfFm+zKHRzHkClk2
HjubeEgjpj32AQIhAJqMGTaZVOwevTXvvHwNeH+vRWsAYU/gbx+OQB+7VOcBAiEA
oolb6NMg/R3enNPvS1O4UU1H8wpaF77L4yiSWlE0p4w=
-----END RSA PRIVATE KEY-----
""")


class X509ExtTests(TestCase):
    """
    Tests for L{OpenSSL.crypto.X509Extension}.
    """

    def setUp(self):
        """
        Create a new private key and start a certificate request (for a test
        method to finish in one way or another).
        """
        # Basic setup stuff to generate a certificate
        self.pkey = PKey()
        self.pkey.generate_key(TYPE_RSA, 384)
        self.req = X509Req()
        self.req.set_pubkey(self.pkey)
        # Authority good you have.
        self.req.get_subject().commonName = "Yoda root CA"
        self.x509 = X509()
        self.subject = self.x509.get_subject()
        self.subject.commonName = self.req.get_subject().commonName
        self.x509.set_issuer(self.subject)
        self.x509.set_pubkey(self.pkey)
        now = b(datetime.now().strftime("%Y%m%d%H%M%SZ"))
        expire  = b((datetime.now() + timedelta(days=100)).strftime("%Y%m%d%H%M%SZ"))
        self.x509.set_notBefore(now)
        self.x509.set_notAfter(expire)


    def test_str(self):
        """
        The string representation of L{X509Extension} instances as returned by
        C{str} includes stuff.
        """
        # This isn't necessarily the best string representation.  Perhaps it
        # will be changed/improved in the future.
        self.assertEquals(
            str(X509Extension(b('basicConstraints'), True, b('CA:false'))),
            'CA:FALSE')


    def test_type(self):
        """
        L{X509Extension} and L{X509ExtensionType} refer to the same type object
        and can be used to create instances of that type.
        """
        self.assertIdentical(X509Extension, X509ExtensionType)
        self.assertConsistentType(
            X509Extension,
            'X509Extension', b('basicConstraints'), True, b('CA:true'))


    def test_construction(self):
        """
        L{X509Extension} accepts an extension type name, a critical flag,
        and an extension value and returns an L{X509ExtensionType} instance.
        """
        basic = X509Extension(b('basicConstraints'), True, b('CA:true'))
        self.assertTrue(
            isinstance(basic, X509ExtensionType),
            "%r is of type %r, should be %r" % (
                basic, type(basic), X509ExtensionType))

        comment = X509Extension(
            b('nsComment'), False, b('pyOpenSSL unit test'))
        self.assertTrue(
            isinstance(comment, X509ExtensionType),
            "%r is of type %r, should be %r" % (
                comment, type(comment), X509ExtensionType))


    def test_invalid_extension(self):
        """
        L{X509Extension} raises something if it is passed a bad extension
        name or value.
        """
        self.assertRaises(
            Error, X509Extension, b('thisIsMadeUp'), False, b('hi'))
        self.assertRaises(
            Error, X509Extension, b('basicConstraints'), False, b('blah blah'))

        # Exercise a weird one (an extension which uses the r2i method).  This
        # exercises the codepath that requires a non-NULL ctx to be passed to
        # X509V3_EXT_nconf.  It can't work now because we provide no
        # configuration database.  It might be made to work in the future.
        self.assertRaises(
            Error, X509Extension, b('proxyCertInfo'), True,
            b('language:id-ppl-anyLanguage,pathlen:1,policy:text:AB'))


    def test_get_critical(self):
        """
        L{X509ExtensionType.get_critical} returns the value of the
        extension's critical flag.
        """
        ext = X509Extension(b('basicConstraints'), True, b('CA:true'))
        self.assertTrue(ext.get_critical())
        ext = X509Extension(b('basicConstraints'), False, b('CA:true'))
        self.assertFalse(ext.get_critical())


    def test_get_short_name(self):
        """
        L{X509ExtensionType.get_short_name} returns a string giving the short
        type name of the extension.
        """
        ext = X509Extension(b('basicConstraints'), True, b('CA:true'))
        self.assertEqual(ext.get_short_name(), b('basicConstraints'))
        ext = X509Extension(b('nsComment'), True, b('foo bar'))
        self.assertEqual(ext.get_short_name(), b('nsComment'))


    def test_get_data(self):
        """
        L{X509Extension.get_data} returns a string giving the data of the
        extension.
        """
        ext = X509Extension(b('basicConstraints'), True, b('CA:true'))
        # Expect to get back the DER encoded form of CA:true.
        self.assertEqual(ext.get_data(), b('0\x03\x01\x01\xff'))


    def test_get_data_wrong_args(self):
        """
        L{X509Extension.get_data} raises L{TypeError} if passed any arguments.
        """
        ext = X509Extension(b('basicConstraints'), True, b('CA:true'))
        self.assertRaises(TypeError, ext.get_data, None)
        self.assertRaises(TypeError, ext.get_data, "foo")
        self.assertRaises(TypeError, ext.get_data, 7)


    def test_unused_subject(self):
        """
        The C{subject} parameter to L{X509Extension} may be provided for an
        extension which does not use it and is ignored in this case.
        """
        ext1 = X509Extension(
            b('basicConstraints'), False, b('CA:TRUE'), subject=self.x509)
        self.x509.add_extensions([ext1])
        self.x509.sign(self.pkey, 'sha1')
        # This is a little lame.  Can we think of a better way?
        text = dump_certificate(FILETYPE_TEXT, self.x509)
        self.assertTrue(b('X509v3 Basic Constraints:') in text)
        self.assertTrue(b('CA:TRUE') in text)


    def test_subject(self):
        """
        If an extension requires a subject, the C{subject} parameter to
        L{X509Extension} provides its value.
        """
        ext3 = X509Extension(
            b('subjectKeyIdentifier'), False, b('hash'), subject=self.x509)
        self.x509.add_extensions([ext3])
        self.x509.sign(self.pkey, 'sha1')
        text = dump_certificate(FILETYPE_TEXT, self.x509)
        self.assertTrue(b('X509v3 Subject Key Identifier:') in text)


    def test_missing_subject(self):
        """
        If an extension requires a subject and the C{subject} parameter is
        given no value, something happens.
        """
        self.assertRaises(
            Error, X509Extension, b('subjectKeyIdentifier'), False, b('hash'))


    def test_invalid_subject(self):
        """
        If the C{subject} parameter is given a value which is not an L{X509}
        instance, L{TypeError} is raised.
        """
        for badObj in [True, object(), "hello", [], self]:
            self.assertRaises(
                TypeError,
                X509Extension,
                'basicConstraints', False, 'CA:TRUE', subject=badObj)


    def test_unused_issuer(self):
        """
        The C{issuer} parameter to L{X509Extension} may be provided for an
        extension which does not use it and is ignored in this case.
        """
        ext1 = X509Extension(
            b('basicConstraints'), False, b('CA:TRUE'), issuer=self.x509)
        self.x509.add_extensions([ext1])
        self.x509.sign(self.pkey, 'sha1')
        text = dump_certificate(FILETYPE_TEXT, self.x509)
        self.assertTrue(b('X509v3 Basic Constraints:') in text)
        self.assertTrue(b('CA:TRUE') in text)


    def test_issuer(self):
        """
        If an extension requires a issuer, the C{issuer} parameter to
        L{X509Extension} provides its value.
        """
        ext2 = X509Extension(
            b('authorityKeyIdentifier'), False, b('issuer:always'),
            issuer=self.x509)
        self.x509.add_extensions([ext2])
        self.x509.sign(self.pkey, 'sha1')
        text = dump_certificate(FILETYPE_TEXT, self.x509)
        self.assertTrue(b('X509v3 Authority Key Identifier:') in text)
        self.assertTrue(b('DirName:/CN=Yoda root CA') in text)


    def test_missing_issuer(self):
        """
        If an extension requires an issue and the C{issuer} parameter is given
        no value, something happens.
        """
        self.assertRaises(
            Error,
            X509Extension,
            b('authorityKeyIdentifier'), False,
            b('keyid:always,issuer:always'))


    def test_invalid_issuer(self):
        """
        If the C{issuer} parameter is given a value which is not an L{X509}
        instance, L{TypeError} is raised.
        """
        for badObj in [True, object(), "hello", [], self]:
            self.assertRaises(
                TypeError,
                X509Extension,
                'authorityKeyIdentifier', False, 'keyid:always,issuer:always',
                issuer=badObj)



class PKeyTests(TestCase):
    """
    Unit tests for L{OpenSSL.crypto.PKey}.
    """
    def test_type(self):
        """
        L{PKey} and L{PKeyType} refer to the same type object and can be used
        to create instances of that type.
        """
        self.assertIdentical(PKey, PKeyType)
        self.assertConsistentType(PKey, 'PKey')


    def test_construction(self):
        """
        L{PKey} takes no arguments and returns a new L{PKey} instance.
        """
        self.assertRaises(TypeError, PKey, None)
        key = PKey()
        self.assertTrue(
            isinstance(key, PKeyType),
            "%r is of type %r, should be %r" % (key, type(key), PKeyType))


    def test_pregeneration(self):
        """
        L{PKeyType.bits} and L{PKeyType.type} return C{0} before the key is
        generated.  L{PKeyType.check} raises L{TypeError} before the key is
        generated.
        """
        key = PKey()
        self.assertEqual(key.type(), 0)
        self.assertEqual(key.bits(), 0)
        self.assertRaises(TypeError, key.check)


    def test_failedGeneration(self):
        """
        L{PKeyType.generate_key} takes two arguments, the first giving the key
        type as one of L{TYPE_RSA} or L{TYPE_DSA} and the second giving the
        number of bits to generate.  If an invalid type is specified or
        generation fails, L{Error} is raised.  If an invalid number of bits is
        specified, L{ValueError} or L{Error} is raised.
        """
        key = PKey()
        self.assertRaises(TypeError, key.generate_key)
        self.assertRaises(TypeError, key.generate_key, 1, 2, 3)
        self.assertRaises(TypeError, key.generate_key, "foo", "bar")
        self.assertRaises(Error, key.generate_key, -1, 0)

        self.assertRaises(ValueError, key.generate_key, TYPE_RSA, -1)
        self.assertRaises(ValueError, key.generate_key, TYPE_RSA, 0)

        # XXX RSA generation for small values of bits is fairly buggy in a wide
        # range of OpenSSL versions.  I need to figure out what the safe lower
        # bound for a reasonable number of OpenSSL versions is and explicitly
        # check for that in the wrapper.  The failure behavior is typically an
        # infinite loop inside OpenSSL.

        # self.assertRaises(Error, key.generate_key, TYPE_RSA, 2)

        # XXX DSA generation seems happy with any number of bits.  The DSS
        # says bits must be between 512 and 1024 inclusive.  OpenSSL's DSA
        # generator doesn't seem to care about the upper limit at all.  For
        # the lower limit, it uses 512 if anything smaller is specified.
        # So, it doesn't seem possible to make generate_key fail for
        # TYPE_DSA with a bits argument which is at least an int.

        # self.assertRaises(Error, key.generate_key, TYPE_DSA, -7)


    def test_rsaGeneration(self):
        """
        L{PKeyType.generate_key} generates an RSA key when passed
        L{TYPE_RSA} as a type and a reasonable number of bits.
        """
        bits = 128
        key = PKey()
        key.generate_key(TYPE_RSA, bits)
        self.assertEqual(key.type(), TYPE_RSA)
        self.assertEqual(key.bits(), bits)
        self.assertTrue(key.check())


    def test_dsaGeneration(self):
        """
        L{PKeyType.generate_key} generates a DSA key when passed
        L{TYPE_DSA} as a type and a reasonable number of bits.
        """
        # 512 is a magic number.  The DSS (Digital Signature Standard)
        # allows a minimum of 512 bits for DSA.  DSA_generate_parameters
        # will silently promote any value below 512 to 512.
        bits = 512
        key = PKey()
        key.generate_key(TYPE_DSA, bits)
        self.assertEqual(key.type(), TYPE_DSA)
        self.assertEqual(key.bits(), bits)
        self.assertRaises(TypeError, key.check)


    def test_regeneration(self):
        """
        L{PKeyType.generate_key} can be called multiple times on the same
        key to generate new keys.
        """
        key = PKey()
        for type, bits in [(TYPE_RSA, 512), (TYPE_DSA, 576)]:
             key.generate_key(type, bits)
             self.assertEqual(key.type(), type)
             self.assertEqual(key.bits(), bits)


    def test_inconsistentKey(self):
        """
        L{PKeyType.check} returns C{False} if the key is not consistent.
        """
        key = load_privatekey(FILETYPE_PEM, inconsistentPrivateKeyPEM)
        self.assertRaises(Error, key.check)


    def test_check_wrong_args(self):
        """
        L{PKeyType.check} raises L{TypeError} if called with any arguments.
        """
        self.assertRaises(TypeError, PKey().check, None)
        self.assertRaises(TypeError, PKey().check, object())
        self.assertRaises(TypeError, PKey().check, 1)



class X509NameTests(TestCase):
    """
    Unit tests for L{OpenSSL.crypto.X509Name}.
    """
    def _x509name(self, **attrs):
        # XXX There's no other way to get a new X509Name yet.
        name = X509().get_subject()
        attrs = list(attrs.items())
        # Make the order stable - order matters!
        def key(attr):
            return attr[1]
        attrs.sort(key=key)
        for k, v in attrs:
            setattr(name, k, v)
        return name


    def test_type(self):
        """
        The type of X509Name objects is L{X509NameType}.
        """
        self.assertIdentical(X509Name, X509NameType)
        self.assertEqual(X509NameType.__name__, 'X509Name')
        self.assertTrue(isinstance(X509NameType, type))

        name = self._x509name()
        self.assertTrue(
            isinstance(name, X509NameType),
            "%r is of type %r, should be %r" % (
                name, type(name), X509NameType))


    def test_onlyStringAttributes(self):
        """
        Attempting to set a non-L{str} attribute name on an L{X509NameType}
        instance causes L{TypeError} to be raised.
        """
        name = self._x509name()
        # Beyond these cases, you may also think that unicode should be
        # rejected.  Sorry, you're wrong.  unicode is automatically converted to
        # str outside of the control of X509Name, so there's no way to reject
        # it.
        self.assertRaises(TypeError, setattr, name, None, "hello")
        self.assertRaises(TypeError, setattr, name, 30, "hello")
        class evil(str):
            pass
        self.assertRaises(TypeError, setattr, name, evil(), "hello")


    def test_setInvalidAttribute(self):
        """
        Attempting to set any attribute name on an L{X509NameType} instance for
        which no corresponding NID is defined causes L{AttributeError} to be
        raised.
        """
        name = self._x509name()
        self.assertRaises(AttributeError, setattr, name, "no such thing", None)


    def test_attributes(self):
        """
        L{X509NameType} instances have attributes for each standard (?)
        X509Name field.
        """
        name = self._x509name()
        name.commonName = "foo"
        self.assertEqual(name.commonName, "foo")
        self.assertEqual(name.CN, "foo")
        name.CN = "baz"
        self.assertEqual(name.commonName, "baz")
        self.assertEqual(name.CN, "baz")
        name.commonName = "bar"
        self.assertEqual(name.commonName, "bar")
        self.assertEqual(name.CN, "bar")
        name.CN = "quux"
        self.assertEqual(name.commonName, "quux")
        self.assertEqual(name.CN, "quux")


    def test_copy(self):
        """
        L{X509Name} creates a new L{X509NameType} instance with all the same
        attributes as an existing L{X509NameType} instance when called with
        one.
        """
        name = self._x509name(commonName="foo", emailAddress="bar@example.com")

        copy = X509Name(name)
        self.assertEqual(copy.commonName, "foo")
        self.assertEqual(copy.emailAddress, "bar@example.com")

        # Mutate the copy and ensure the original is unmodified.
        copy.commonName = "baz"
        self.assertEqual(name.commonName, "foo")

        # Mutate the original and ensure the copy is unmodified.
        name.emailAddress = "quux@example.com"
        self.assertEqual(copy.emailAddress, "bar@example.com")


    def test_repr(self):
        """
        L{repr} passed an L{X509NameType} instance should return a string
        containing a description of the type and the NIDs which have been set
        on it.
        """
        name = self._x509name(commonName="foo", emailAddress="bar")
        self.assertEqual(
            repr(name),
            "<X509Name object '/emailAddress=bar/CN=foo'>")


    def test_comparison(self):
        """
        L{X509NameType} instances should compare based on their NIDs.
        """
        def _equality(a, b, assertTrue, assertFalse):
            assertTrue(a == b, "(%r == %r) --> False" % (a, b))
            assertFalse(a != b)
            assertTrue(b == a)
            assertFalse(b != a)

        def assertEqual(a, b):
            _equality(a, b, self.assertTrue, self.assertFalse)

        # Instances compare equal to themselves.
        name = self._x509name()
        assertEqual(name, name)

        # Empty instances should compare equal to each other.
        assertEqual(self._x509name(), self._x509name())

        # Instances with equal NIDs should compare equal to each other.
        assertEqual(self._x509name(commonName="foo"),
                    self._x509name(commonName="foo"))

        # Instance with equal NIDs set using different aliases should compare
        # equal to each other.
        assertEqual(self._x509name(commonName="foo"),
                    self._x509name(CN="foo"))

        # Instances with more than one NID with the same values should compare
        # equal to each other.
        assertEqual(self._x509name(CN="foo", organizationalUnitName="bar"),
                    self._x509name(commonName="foo", OU="bar"))

        def assertNotEqual(a, b):
            _equality(a, b, self.assertFalse, self.assertTrue)

        # Instances with different values for the same NID should not compare
        # equal to each other.
        assertNotEqual(self._x509name(CN="foo"),
                       self._x509name(CN="bar"))

        # Instances with different NIDs should not compare equal to each other.
        assertNotEqual(self._x509name(CN="foo"),
                       self._x509name(OU="foo"))

        def _inequality(a, b, assertTrue, assertFalse):
            assertTrue(a < b)
            assertTrue(a <= b)
            assertTrue(b > a)
            assertTrue(b >= a)
            assertFalse(a > b)
            assertFalse(a >= b)
            assertFalse(b < a)
            assertFalse(b <= a)

        def assertLessThan(a, b):
            _inequality(a, b, self.assertTrue, self.assertFalse)

        # An X509Name with a NID with a value which sorts less than the value
        # of the same NID on another X509Name compares less than the other
        # X509Name.
        assertLessThan(self._x509name(CN="abc"),
                       self._x509name(CN="def"))

        def assertGreaterThan(a, b):
            _inequality(a, b, self.assertFalse, self.assertTrue)

        # An X509Name with a NID with a value which sorts greater than the
        # value of the same NID on another X509Name compares greater than the
        # other X509Name.
        assertGreaterThan(self._x509name(CN="def"),
                          self._x509name(CN="abc"))


    def test_hash(self):
        """
        L{X509Name.hash} returns an integer hash based on the value of the
        name.
        """
        a = self._x509name(CN="foo")
        b = self._x509name(CN="foo")
        self.assertEqual(a.hash(), b.hash())
        a.CN = "bar"
        self.assertNotEqual(a.hash(), b.hash())


    def test_der(self):
        """
        L{X509Name.der} returns the DER encoded form of the name.
        """
        a = self._x509name(CN="foo", C="US")
        self.assertEqual(
            a.der(),
            b('0\x1b1\x0b0\t\x06\x03U\x04\x06\x13\x02US'
              '1\x0c0\n\x06\x03U\x04\x03\x13\x03foo'))


    def test_get_components(self):
        """
        L{X509Name.get_components} returns a C{list} of two-tuples of C{str}
        giving the NIDs and associated values which make up the name.
        """
        a = self._x509name()
        self.assertEqual(a.get_components(), [])
        a.CN = "foo"
        self.assertEqual(a.get_components(), [(b("CN"), b("foo"))])
        a.organizationalUnitName = "bar"
        self.assertEqual(
            a.get_components(),
            [(b("CN"), b("foo")), (b("OU"), b("bar"))])


class _PKeyInteractionTestsMixin:
    """
    Tests which involve another thing and a PKey.
    """
    def signable(self):
        """
        Return something with a C{set_pubkey}, C{set_pubkey}, and C{sign} method.
        """
        raise NotImplementedError()


    def test_signWithUngenerated(self):
        """
        L{X509Req.sign} raises L{ValueError} when pass a L{PKey} with no parts.
        """
        request = self.signable()
        key = PKey()
        self.assertRaises(ValueError, request.sign, key, 'MD5')


    def test_signWithPublicKey(self):
        """
        L{X509Req.sign} raises L{ValueError} when pass a L{PKey} with no
        private part as the signing key.
        """
        request = self.signable()
        key = PKey()
        key.generate_key(TYPE_RSA, 512)
        request.set_pubkey(key)
        pub = request.get_pubkey()
        self.assertRaises(ValueError, request.sign, pub, 'MD5')


    def test_signWithUnknownDigest(self):
        """
        L{X509Req.sign} raises L{ValueError} when passed a digest name which is
        not known.
        """
        request = self.signable()
        key = PKey()
        key.generate_key(TYPE_RSA, 512)
        self.assertRaises(ValueError, request.sign, key, "monkeys")


    def test_sign(self):
        """
        L{X509Req.sign} succeeds when passed a private key object and a valid
        digest function.  C{X509Req.verify} can be used to check the signature.
        """
        request = self.signable()
        key = PKey()
        key.generate_key(TYPE_RSA, 512)
        request.set_pubkey(key)
        request.sign(key, 'MD5')
        # If the type has a verify method, cover that too.
        if getattr(request, 'verify', None) is not None:
            pub = request.get_pubkey()
            self.assertTrue(request.verify(pub))
            # Make another key that won't verify.
            key = PKey()
            key.generate_key(TYPE_RSA, 512)
            self.assertRaises(Error, request.verify, key)




class X509ReqTests(TestCase, _PKeyInteractionTestsMixin):
    """
    Tests for L{OpenSSL.crypto.X509Req}.
    """
    def signable(self):
        """
        Create and return a new L{X509Req}.
        """
        return X509Req()


    def test_type(self):
        """
        L{X509Req} and L{X509ReqType} refer to the same type object and can be
        used to create instances of that type.
        """
        self.assertIdentical(X509Req, X509ReqType)
        self.assertConsistentType(X509Req, 'X509Req')


    def test_construction(self):
        """
        L{X509Req} takes no arguments and returns an L{X509ReqType} instance.
        """
        request = X509Req()
        self.assertTrue(
            isinstance(request, X509ReqType),
            "%r is of type %r, should be %r" % (request, type(request), X509ReqType))


    def test_version(self):
        """
        L{X509ReqType.set_version} sets the X.509 version of the certificate
        request.  L{X509ReqType.get_version} returns the X.509 version of
        the certificate request.  The initial value of the version is 0.
        """
        request = X509Req()
        self.assertEqual(request.get_version(), 0)
        request.set_version(1)
        self.assertEqual(request.get_version(), 1)
        request.set_version(3)
        self.assertEqual(request.get_version(), 3)


    def test_version_wrong_args(self):
        """
        L{X509ReqType.set_version} raises L{TypeError} if called with the wrong
        number of arguments or with a non-C{int} argument.
        L{X509ReqType.get_version} raises L{TypeError} if called with any
        arguments.
        """
        request = X509Req()
        self.assertRaises(TypeError, request.set_version)
        self.assertRaises(TypeError, request.set_version, "foo")
        self.assertRaises(TypeError, request.set_version, 1, 2)
        self.assertRaises(TypeError, request.get_version, None)


    def test_get_subject(self):
        """
        L{X509ReqType.get_subject} returns an L{X509Name} for the subject of
        the request and which is valid even after the request object is
        otherwise dead.
        """
        request = X509Req()
        subject = request.get_subject()
        self.assertTrue(
            isinstance(subject, X509NameType),
            "%r is of type %r, should be %r" % (subject, type(subject), X509NameType))
        subject.commonName = "foo"
        self.assertEqual(request.get_subject().commonName, "foo")
        del request
        subject.commonName = "bar"
        self.assertEqual(subject.commonName, "bar")


    def test_get_subject_wrong_args(self):
        """
        L{X509ReqType.get_subject} raises L{TypeError} if called with any
        arguments.
        """
        request = X509Req()
        self.assertRaises(TypeError, request.get_subject, None)


    def test_add_extensions(self):
        """
        L{X509Req.add_extensions} accepts a C{list} of L{X509Extension}
        instances and adds them to the X509 request.
        """
        request = X509Req()
        request.add_extensions([
                X509Extension(b('basicConstraints'), True, b('CA:false'))])
        # XXX Add get_extensions so the rest of this unit test can be written.


    def test_add_extensions_wrong_args(self):
        """
        L{X509Req.add_extensions} raises L{TypeError} if called with the wrong
        number of arguments or with a non-C{list}.  Or it raises L{ValueError}
        if called with a C{list} containing objects other than L{X509Extension}
        instances.
        """
        request = X509Req()
        self.assertRaises(TypeError, request.add_extensions)
        self.assertRaises(TypeError, request.add_extensions, object())
        self.assertRaises(ValueError, request.add_extensions, [object()])
        self.assertRaises(TypeError, request.add_extensions, [], None)



class X509Tests(TestCase, _PKeyInteractionTestsMixin):
    """
    Tests for L{OpenSSL.crypto.X509}.
    """
    pemData = cleartextCertificatePEM + cleartextPrivateKeyPEM

    extpem = """
-----BEGIN CERTIFICATE-----
MIIC3jCCAkegAwIBAgIJAJHFjlcCgnQzMA0GCSqGSIb3DQEBBQUAMEcxCzAJBgNV
BAYTAlNFMRUwEwYDVQQIEwxXZXN0ZXJib3R0b20xEjAQBgNVBAoTCUNhdGFsb2dp
eDENMAsGA1UEAxMEUm9vdDAeFw0wODA0MjIxNDQ1MzhaFw0wOTA0MjIxNDQ1Mzha
MFQxCzAJBgNVBAYTAlNFMQswCQYDVQQIEwJXQjEUMBIGA1UEChMLT3Blbk1ldGFk
aXIxIjAgBgNVBAMTGW5vZGUxLm9tMi5vcGVubWV0YWRpci5vcmcwgZ8wDQYJKoZI
hvcNAQEBBQADgY0AMIGJAoGBAPIcQMrwbk2nESF/0JKibj9i1x95XYAOwP+LarwT
Op4EQbdlI9SY+uqYqlERhF19w7CS+S6oyqx0DRZSk4Y9dZ9j9/xgm2u/f136YS1u
zgYFPvfUs6PqYLPSM8Bw+SjJ+7+2+TN+Tkiof9WP1cMjodQwOmdsiRbR0/J7+b1B
hec1AgMBAAGjgcQwgcEwCQYDVR0TBAIwADAsBglghkgBhvhCAQ0EHxYdT3BlblNT
TCBHZW5lcmF0ZWQgQ2VydGlmaWNhdGUwHQYDVR0OBBYEFIdHsBcMVVMbAO7j6NCj
03HgLnHaMB8GA1UdIwQYMBaAFL2h9Bf9Mre4vTdOiHTGAt7BRY/8MEYGA1UdEQQ/
MD2CDSouZXhhbXBsZS5vcmeCESoub20yLmV4bWFwbGUuY29thwSC7wgKgRNvbTJA
b3Blbm1ldGFkaXIub3JnMA0GCSqGSIb3DQEBBQUAA4GBALd7WdXkp2KvZ7/PuWZA
MPlIxyjS+Ly11+BNE0xGQRp9Wz+2lABtpgNqssvU156+HkKd02rGheb2tj7MX9hG
uZzbwDAZzJPjzDQDD7d3cWsrVcfIdqVU7epHqIadnOF+X0ghJ39pAm6VVadnSXCt
WpOdIpB8KksUTCzV591Nr1wd
-----END CERTIFICATE-----
    """
    def signable(self):
        """
        Create and return a new L{X509}.
        """
        return X509()


    def test_type(self):
        """
        L{X509} and L{X509Type} refer to the same type object and can be used
        to create instances of that type.
        """
        self.assertIdentical(X509, X509Type)
        self.assertConsistentType(X509, 'X509')


    def test_construction(self):
        """
        L{X509} takes no arguments and returns an instance of L{X509Type}.
        """
        certificate = X509()
        self.assertTrue(
            isinstance(certificate, X509Type),
            "%r is of type %r, should be %r" % (certificate,
                                                type(certificate),
                                                X509Type))
        self.assertEqual(type(X509Type).__name__, 'type')
        self.assertEqual(type(certificate).__name__, 'X509')
        self.assertEqual(type(certificate), X509Type)
        self.assertEqual(type(certificate), X509)


    def test_get_version_wrong_args(self):
        """
        L{X509.get_version} raises L{TypeError} if invoked with any arguments.
        """
        cert = X509()
        self.assertRaises(TypeError, cert.get_version, None)


    def test_set_version_wrong_args(self):
        """
        L{X509.set_version} raises L{TypeError} if invoked with the wrong number
        of arguments or an argument not of type C{int}.
        """
        cert = X509()
        self.assertRaises(TypeError, cert.set_version)
        self.assertRaises(TypeError, cert.set_version, None)
        self.assertRaises(TypeError, cert.set_version, 1, None)


    def test_version(self):
        """
        L{X509.set_version} sets the certificate version number.
        L{X509.get_version} retrieves it.
        """
        cert = X509()
        cert.set_version(1234)
        self.assertEquals(cert.get_version(), 1234)


    def test_get_serial_number_wrong_args(self):
        """
        L{X509.get_serial_number} raises L{TypeError} if invoked with any
        arguments.
        """
        cert = X509()
        self.assertRaises(TypeError, cert.get_serial_number, None)


    def test_serial_number(self):
        """
        The serial number of an L{X509Type} can be retrieved and modified with
        L{X509Type.get_serial_number} and L{X509Type.set_serial_number}.
        """
        certificate = X509()
        self.assertRaises(TypeError, certificate.set_serial_number)
        self.assertRaises(TypeError, certificate.set_serial_number, 1, 2)
        self.assertRaises(TypeError, certificate.set_serial_number, "1")
        self.assertRaises(TypeError, certificate.set_serial_number, 5.5)
        self.assertEqual(certificate.get_serial_number(), 0)
        certificate.set_serial_number(1)
        self.assertEqual(certificate.get_serial_number(), 1)
        certificate.set_serial_number(2 ** 32 + 1)
        self.assertEqual(certificate.get_serial_number(), 2 ** 32 + 1)
        certificate.set_serial_number(2 ** 64 + 1)
        self.assertEqual(certificate.get_serial_number(), 2 ** 64 + 1)
        certificate.set_serial_number(2 ** 128 + 1)
        self.assertEqual(certificate.get_serial_number(), 2 ** 128 + 1)


    def _setBoundTest(self, which):
        """
        L{X509Type.set_notBefore} takes a string in the format of an ASN1
        GENERALIZEDTIME and sets the beginning of the certificate's validity
        period to it.
        """
        certificate = X509()
        set = getattr(certificate, 'set_not' + which)
        get = getattr(certificate, 'get_not' + which)

        # Starts with no value.
        self.assertEqual(get(), None)

        # GMT (Or is it UTC?) -exarkun
        when = b("20040203040506Z")
        set(when)
        self.assertEqual(get(), when)

        # A plus two hours and thirty minutes offset
        when = b("20040203040506+0530")
        set(when)
        self.assertEqual(get(), when)

        # A minus one hour fifteen minutes offset
        when = b("20040203040506-0115")
        set(when)
        self.assertEqual(get(), when)

        # An invalid string results in a ValueError
        self.assertRaises(ValueError, set, b("foo bar"))

        # The wrong number of arguments results in a TypeError.
        self.assertRaises(TypeError, set)
        self.assertRaises(TypeError, set, b("20040203040506Z"), b("20040203040506Z"))
        self.assertRaises(TypeError, get, b("foo bar"))


    # XXX ASN1_TIME (not GENERALIZEDTIME)

    def test_set_notBefore(self):
        """
        L{X509Type.set_notBefore} takes a string in the format of an ASN1
        GENERALIZEDTIME and sets the beginning of the certificate's validity
        period to it.
        """
        self._setBoundTest("Before")


    def test_set_notAfter(self):
        """
        L{X509Type.set_notAfter} takes a string in the format of an ASN1
        GENERALIZEDTIME and sets the end of the certificate's validity period
        to it.
        """
        self._setBoundTest("After")


    def test_get_notBefore(self):
        """
        L{X509Type.get_notBefore} returns a string in the format of an ASN1
        GENERALIZEDTIME even for certificates which store it as UTCTIME
        internally.
        """
        cert = load_certificate(FILETYPE_PEM, self.pemData)
        self.assertEqual(cert.get_notBefore(), b("20090325123658Z"))


    def test_get_notAfter(self):
        """
        L{X509Type.get_notAfter} returns a string in the format of an ASN1
        GENERALIZEDTIME even for certificates which store it as UTCTIME
        internally.
        """
        cert = load_certificate(FILETYPE_PEM, self.pemData)
        self.assertEqual(cert.get_notAfter(), b("20170611123658Z"))


    def test_gmtime_adj_notBefore_wrong_args(self):
        """
        L{X509Type.gmtime_adj_notBefore} raises L{TypeError} if called with the
        wrong number of arguments or a non-C{int} argument.
        """
        cert = X509()
        self.assertRaises(TypeError, cert.gmtime_adj_notBefore)
        self.assertRaises(TypeError, cert.gmtime_adj_notBefore, None)
        self.assertRaises(TypeError, cert.gmtime_adj_notBefore, 123, None)


    def test_gmtime_adj_notBefore(self):
        """
        L{X509Type.gmtime_adj_notBefore} changes the not-before timestamp to be
        the current time plus the number of seconds passed in.
        """
        cert = load_certificate(FILETYPE_PEM, self.pemData)
        now = datetime.utcnow() + timedelta(seconds=100)
        cert.gmtime_adj_notBefore(100)
        self.assertEqual(cert.get_notBefore(), b(now.strftime("%Y%m%d%H%M%SZ")))


    def test_gmtime_adj_notAfter_wrong_args(self):
        """
        L{X509Type.gmtime_adj_notAfter} raises L{TypeError} if called with the
        wrong number of arguments or a non-C{int} argument.
        """
        cert = X509()
        self.assertRaises(TypeError, cert.gmtime_adj_notAfter)
        self.assertRaises(TypeError, cert.gmtime_adj_notAfter, None)
        self.assertRaises(TypeError, cert.gmtime_adj_notAfter, 123, None)


    def test_gmtime_adj_notAfter(self):
        """
        L{X509Type.gmtime_adj_notAfter} changes the not-after timestamp to be
        the current time plus the number of seconds passed in.
        """
        cert = load_certificate(FILETYPE_PEM, self.pemData)
        now = datetime.utcnow() + timedelta(seconds=100)
        cert.gmtime_adj_notAfter(100)
        self.assertEqual(cert.get_notAfter(), b(now.strftime("%Y%m%d%H%M%SZ")))


    def test_has_expired_wrong_args(self):
        """
        L{X509Type.has_expired} raises L{TypeError} if called with any
        arguments.
        """
        cert = X509()
        self.assertRaises(TypeError, cert.has_expired, None)


    def test_has_expired(self):
        """
        L{X509Type.has_expired} returns C{True} if the certificate's not-after
        time is in the past.
        """
        cert = X509()
        cert.gmtime_adj_notAfter(-1)
        self.assertTrue(cert.has_expired())


    def test_has_not_expired(self):
        """
        L{X509Type.has_expired} returns C{False} if the certificate's not-after
        time is in the future.
        """
        cert = X509()
        cert.gmtime_adj_notAfter(2)
        self.assertFalse(cert.has_expired())


    def test_digest(self):
        """
        L{X509.digest} returns a string giving ":"-separated hex-encoded words
        of the digest of the certificate.
        """
        cert = X509()
        self.assertEqual(
            cert.digest("md5"),
            b("A8:EB:07:F8:53:25:0A:F2:56:05:C5:A5:C4:C4:C7:15"))


    def _extcert(self, pkey, extensions):
        cert = X509()
        cert.set_pubkey(pkey)
        cert.get_subject().commonName = "Unit Tests"
        cert.get_issuer().commonName = "Unit Tests"
        when = b(datetime.now().strftime("%Y%m%d%H%M%SZ"))
        cert.set_notBefore(when)
        cert.set_notAfter(when)

        cert.add_extensions(extensions)
        return load_certificate(
            FILETYPE_PEM, dump_certificate(FILETYPE_PEM, cert))


    def test_extension_count(self):
        """
        L{X509.get_extension_count} returns the number of extensions that are
        present in the certificate.
        """
        pkey = load_privatekey(FILETYPE_PEM, client_key_pem)
        ca = X509Extension(b('basicConstraints'), True, b('CA:FALSE'))
        key = X509Extension(b('keyUsage'), True, b('digitalSignature'))
        subjectAltName = X509Extension(
            b('subjectAltName'), True, b('DNS:example.com'))

        # Try a certificate with no extensions at all.
        c = self._extcert(pkey, [])
        self.assertEqual(c.get_extension_count(), 0)

        # And a certificate with one
        c = self._extcert(pkey, [ca])
        self.assertEqual(c.get_extension_count(), 1)

        # And a certificate with several
        c = self._extcert(pkey, [ca, key, subjectAltName])
        self.assertEqual(c.get_extension_count(), 3)


    def test_get_extension(self):
        """
        L{X509.get_extension} takes an integer and returns an L{X509Extension}
        corresponding to the extension at that index.
        """
        pkey = load_privatekey(FILETYPE_PEM, client_key_pem)
        ca = X509Extension(b('basicConstraints'), True, b('CA:FALSE'))
        key = X509Extension(b('keyUsage'), True, b('digitalSignature'))
        subjectAltName = X509Extension(
            b('subjectAltName'), False, b('DNS:example.com'))

        cert = self._extcert(pkey, [ca, key, subjectAltName])

        ext = cert.get_extension(0)
        self.assertTrue(isinstance(ext, X509Extension))
        self.assertTrue(ext.get_critical())
        self.assertEqual(ext.get_short_name(), b('basicConstraints'))

        ext = cert.get_extension(1)
        self.assertTrue(isinstance(ext, X509Extension))
        self.assertTrue(ext.get_critical())
        self.assertEqual(ext.get_short_name(), b('keyUsage'))

        ext = cert.get_extension(2)
        self.assertTrue(isinstance(ext, X509Extension))
        self.assertFalse(ext.get_critical())
        self.assertEqual(ext.get_short_name(), b('subjectAltName'))

        self.assertRaises(IndexError, cert.get_extension, -1)
        self.assertRaises(IndexError, cert.get_extension, 4)
        self.assertRaises(TypeError, cert.get_extension, "hello")


    def test_invalid_digest_algorithm(self):
        """
        L{X509.digest} raises L{ValueError} if called with an unrecognized hash
        algorithm.
        """
        cert = X509()
        self.assertRaises(ValueError, cert.digest, "monkeys")


    def test_get_subject_wrong_args(self):
        """
        L{X509.get_subject} raises L{TypeError} if called with any arguments.
        """
        cert = X509()
        self.assertRaises(TypeError, cert.get_subject, None)


    def test_get_subject(self):
        """
        L{X509.get_subject} returns an L{X509Name} instance.
        """
        cert = load_certificate(FILETYPE_PEM, self.pemData)
        subj = cert.get_subject()
        self.assertTrue(isinstance(subj, X509Name))
        self.assertEquals(
            subj.get_components(),
            [(b('C'), b('US')), (b('ST'), b('IL')), (b('L'), b('Chicago')),
             (b('O'), b('Testing')), (b('CN'), b('Testing Root CA'))])


    def test_set_subject_wrong_args(self):
        """
        L{X509.set_subject} raises a L{TypeError} if called with the wrong
        number of arguments or an argument not of type L{X509Name}.
        """
        cert = X509()
        self.assertRaises(TypeError, cert.set_subject)
        self.assertRaises(TypeError, cert.set_subject, None)
        self.assertRaises(TypeError, cert.set_subject, cert.get_subject(), None)


    def test_set_subject(self):
        """
        L{X509.set_subject} changes the subject of the certificate to the one
        passed in.
        """
        cert = X509()
        name = cert.get_subject()
        name.C = 'AU'
        name.O = 'Unit Tests'
        cert.set_subject(name)
        self.assertEquals(
            cert.get_subject().get_components(),
            [(b('C'), b('AU')), (b('O'), b('Unit Tests'))])


    def test_get_issuer_wrong_args(self):
        """
        L{X509.get_issuer} raises L{TypeError} if called with any arguments.
        """
        cert = X509()
        self.assertRaises(TypeError, cert.get_issuer, None)


    def test_get_issuer(self):
        """
        L{X509.get_issuer} returns an L{X509Name} instance.
        """
        cert = load_certificate(FILETYPE_PEM, self.pemData)
        subj = cert.get_issuer()
        self.assertTrue(isinstance(subj, X509Name))
        comp = subj.get_components()
        self.assertEquals(
            comp,
            [(b('C'), b('US')), (b('ST'), b('IL')), (b('L'), b('Chicago')),
             (b('O'), b('Testing')), (b('CN'), b('Testing Root CA'))])


    def test_set_issuer_wrong_args(self):
        """
        L{X509.set_issuer} raises a L{TypeError} if called with the wrong
        number of arguments or an argument not of type L{X509Name}.
        """
        cert = X509()
        self.assertRaises(TypeError, cert.set_issuer)
        self.assertRaises(TypeError, cert.set_issuer, None)
        self.assertRaises(TypeError, cert.set_issuer, cert.get_issuer(), None)


    def test_set_issuer(self):
        """
        L{X509.set_issuer} changes the issuer of the certificate to the one
        passed in.
        """
        cert = X509()
        name = cert.get_issuer()
        name.C = 'AU'
        name.O = 'Unit Tests'
        cert.set_issuer(name)
        self.assertEquals(
            cert.get_issuer().get_components(),
            [(b('C'), b('AU')), (b('O'), b('Unit Tests'))])


    def test_get_pubkey_uninitialized(self):
        """
        When called on a certificate with no public key, L{X509.get_pubkey}
        raises L{OpenSSL.crypto.Error}.
        """
        cert = X509()
        self.assertRaises(Error, cert.get_pubkey)


    def test_subject_name_hash_wrong_args(self):
        """
        L{X509.subject_name_hash} raises L{TypeError} if called with any
        arguments.
        """
        cert = X509()
        self.assertRaises(TypeError, cert.subject_name_hash, None)


    def test_subject_name_hash(self):
        """
        L{X509.subject_name_hash} returns the hash of the certificate's subject
        name.
        """
        cert = load_certificate(FILETYPE_PEM, self.pemData)
        self.assertIn(
            cert.subject_name_hash(),
            [3350047874, # OpenSSL 0.9.8, MD5
             3278919224, # OpenSSL 1.0.0, SHA1
             ])


    def test_get_signature_algorithm(self):
        """
        L{X509Type.get_signature_algorithm} returns a string which means
        the algorithm used to sign the certificate.
        """
        cert = load_certificate(FILETYPE_PEM, self.pemData)
        self.assertEqual(
            b("sha1WithRSAEncryption"), cert.get_signature_algorithm())


    def test_get_undefined_signature_algorithm(self):
        """
        L{X509Type.get_signature_algorithm} raises L{ValueError} if the
        signature algorithm is undefined or unknown.
        """
        # This certificate has been modified to indicate a bogus OID in the
        # signature algorithm field so that OpenSSL does not recognize it.
        certPEM = """\
-----BEGIN CERTIFICATE-----
MIIC/zCCAmigAwIBAgIBATAGBgJ8BQUAMHsxCzAJBgNVBAYTAlNHMREwDwYDVQQK
EwhNMkNyeXB0bzEUMBIGA1UECxMLTTJDcnlwdG8gQ0ExJDAiBgNVBAMTG00yQ3J5
cHRvIENlcnRpZmljYXRlIE1hc3RlcjEdMBsGCSqGSIb3DQEJARYObmdwc0Bwb3N0
MS5jb20wHhcNMDAwOTEwMDk1MTMwWhcNMDIwOTEwMDk1MTMwWjBTMQswCQYDVQQG
EwJTRzERMA8GA1UEChMITTJDcnlwdG8xEjAQBgNVBAMTCWxvY2FsaG9zdDEdMBsG
CSqGSIb3DQEJARYObmdwc0Bwb3N0MS5jb20wXDANBgkqhkiG9w0BAQEFAANLADBI
AkEArL57d26W9fNXvOhNlZzlPOACmvwOZ5AdNgLzJ1/MfsQQJ7hHVeHmTAjM664V
+fXvwUGJLziCeBo1ysWLRnl8CQIDAQABo4IBBDCCAQAwCQYDVR0TBAIwADAsBglg
hkgBhvhCAQ0EHxYdT3BlblNTTCBHZW5lcmF0ZWQgQ2VydGlmaWNhdGUwHQYDVR0O
BBYEFM+EgpK+eyZiwFU1aOPSbczbPSpVMIGlBgNVHSMEgZ0wgZqAFPuHI2nrnDqT
FeXFvylRT/7tKDgBoX+kfTB7MQswCQYDVQQGEwJTRzERMA8GA1UEChMITTJDcnlw
dG8xFDASBgNVBAsTC00yQ3J5cHRvIENBMSQwIgYDVQQDExtNMkNyeXB0byBDZXJ0
aWZpY2F0ZSBNYXN0ZXIxHTAbBgkqhkiG9w0BCQEWDm5ncHNAcG9zdDEuY29tggEA
MA0GCSqGSIb3DQEBBAUAA4GBADv8KpPo+gfJxN2ERK1Y1l17sz/ZhzoGgm5XCdbx
jEY7xKfpQngV599k1xhl11IMqizDwu0855agrckg2MCTmOI9DZzDD77tAYb+Dk0O
PEVk0Mk/V0aIsDE9bolfCi/i/QWZ3N8s5nTWMNyBBBmoSliWCm4jkkRZRD0ejgTN
tgI5
-----END CERTIFICATE-----
"""
        cert = load_certificate(FILETYPE_PEM, certPEM)
        self.assertRaises(ValueError, cert.get_signature_algorithm)



class PKCS12Tests(TestCase):
    """
    Test for L{OpenSSL.crypto.PKCS12} and L{OpenSSL.crypto.load_pkcs12}.
    """
    pemData = cleartextCertificatePEM + cleartextPrivateKeyPEM

    def test_type(self):
        """
        L{PKCS12Type} is a type object.
        """
        self.assertIdentical(PKCS12, PKCS12Type)
        self.assertConsistentType(PKCS12, 'PKCS12')


    def test_empty_construction(self):
        """
        L{PKCS12} returns a new instance of L{PKCS12} with no certificate,
        private key, CA certificates, or friendly name.
        """
        p12 = PKCS12()
        self.assertEqual(None, p12.get_certificate())
        self.assertEqual(None, p12.get_privatekey())
        self.assertEqual(None, p12.get_ca_certificates())
        self.assertEqual(None, p12.get_friendlyname())


    def test_type_errors(self):
        """
        The L{PKCS12} setter functions (C{set_certificate}, C{set_privatekey},
        C{set_ca_certificates}, and C{set_friendlyname}) raise L{TypeError}
        when passed objects of types other than those expected.
        """
        p12 = PKCS12()
        self.assertRaises(TypeError, p12.set_certificate, 3)
        self.assertRaises(TypeError, p12.set_certificate, PKey())
        self.assertRaises(TypeError, p12.set_certificate, X509)
        self.assertRaises(TypeError, p12.set_privatekey, 3)
        self.assertRaises(TypeError, p12.set_privatekey, 'legbone')
        self.assertRaises(TypeError, p12.set_privatekey, X509())
        self.assertRaises(TypeError, p12.set_ca_certificates, 3)
        self.assertRaises(TypeError, p12.set_ca_certificates, X509())
        self.assertRaises(TypeError, p12.set_ca_certificates, (3, 4))
        self.assertRaises(TypeError, p12.set_ca_certificates, ( PKey(), ))
        self.assertRaises(TypeError, p12.set_friendlyname, 6)
        self.assertRaises(TypeError, p12.set_friendlyname, ('foo', 'bar'))


    def test_key_only(self):
        """
        A L{PKCS12} with only a private key can be exported using
        L{PKCS12.export} and loaded again using L{load_pkcs12}.
        """
        passwd = 'blah'
        p12 = PKCS12()
        pkey = load_privatekey(FILETYPE_PEM, cleartextPrivateKeyPEM)
        p12.set_privatekey(pkey)
        self.assertEqual(None, p12.get_certificate())
        self.assertEqual(pkey, p12.get_privatekey())
        try:
            dumped_p12 = p12.export(passphrase=passwd, iter=2, maciter=3)
        except Error:
            # Some versions of OpenSSL will throw an exception
            # for this nearly useless PKCS12 we tried to generate:
            # [('PKCS12 routines', 'PKCS12_create', 'invalid null argument')]
            return
        p12 = load_pkcs12(dumped_p12, passwd)
        self.assertEqual(None, p12.get_ca_certificates())
        self.assertEqual(None, p12.get_certificate())

        # OpenSSL fails to bring the key back to us.  So sad.  Perhaps in the
        # future this will be improved.
        self.assertTrue(isinstance(p12.get_privatekey(), (PKey, type(None))))


    def test_cert_only(self):
        """
        A L{PKCS12} with only a certificate can be exported using
        L{PKCS12.export} and loaded again using L{load_pkcs12}.
        """
        passwd = 'blah'
        p12 = PKCS12()
        cert = load_certificate(FILETYPE_PEM, cleartextCertificatePEM)
        p12.set_certificate(cert)
        self.assertEqual(cert, p12.get_certificate())
        self.assertEqual(None, p12.get_privatekey())
        try:
            dumped_p12 = p12.export(passphrase=passwd, iter=2, maciter=3)
        except Error:
            # Some versions of OpenSSL will throw an exception
            # for this nearly useless PKCS12 we tried to generate:
            # [('PKCS12 routines', 'PKCS12_create', 'invalid null argument')]
            return
        p12 = load_pkcs12(dumped_p12, passwd)
        self.assertEqual(None, p12.get_privatekey())

        # OpenSSL fails to bring the cert back to us.  Groany mcgroan.
        self.assertTrue(isinstance(p12.get_certificate(), (X509, type(None))))

        # Oh ho.  It puts the certificate into the ca certificates list, in
        # fact.  Totally bogus, I would think.  Nevertheless, let's exploit
        # that to check to see if it reconstructed the certificate we expected
        # it to.  At some point, hopefully this will change so that
        # p12.get_certificate() is actually what returns the loaded
        # certificate.
        self.assertEqual(
            cleartextCertificatePEM,
            dump_certificate(FILETYPE_PEM, p12.get_ca_certificates()[0]))


    def gen_pkcs12(self, cert_pem=None, key_pem=None, ca_pem=None, friendly_name=None):
        """
        Generate a PKCS12 object with components from PEM.  Verify that the set
        functions return None.
        """
        p12 = PKCS12()
        if cert_pem:
            ret = p12.set_certificate(load_certificate(FILETYPE_PEM, cert_pem))
            self.assertEqual(ret, None)
        if key_pem:
            ret = p12.set_privatekey(load_privatekey(FILETYPE_PEM, key_pem))
            self.assertEqual(ret, None)
        if ca_pem:
            ret = p12.set_ca_certificates((load_certificate(FILETYPE_PEM, ca_pem),))
            self.assertEqual(ret, None)
        if friendly_name:
            ret = p12.set_friendlyname(friendly_name)
            self.assertEqual(ret, None)
        return p12


    def check_recovery(self, p12_str, key=None, cert=None, ca=None, passwd='',
                       extra=()):
        """
        Use openssl program to confirm three components are recoverable from a
        PKCS12 string.
        """
        if key:
            recovered_key = _runopenssl(
                p12_str, "pkcs12", '-nocerts', '-nodes', '-passin',
                'pass:' + passwd, *extra)
            self.assertEqual(recovered_key[-len(key):], key)
        if cert:
            recovered_cert = _runopenssl(
                p12_str, "pkcs12", '-clcerts', '-nodes', '-passin',
                'pass:' + passwd, '-nokeys', *extra)
            self.assertEqual(recovered_cert[-len(cert):], cert)
        if ca:
            recovered_cert = _runopenssl(
                p12_str, "pkcs12", '-cacerts', '-nodes', '-passin',
                'pass:' + passwd, '-nokeys', *extra)
            self.assertEqual(recovered_cert[-len(ca):], ca)


    def test_load_pkcs12(self):
        """
        A PKCS12 string generated using the openssl command line can be loaded
        with L{load_pkcs12} and its components extracted and examined.
        """
        passwd = 'whatever'
        pem = client_key_pem + client_cert_pem
        p12_str = _runopenssl(
            pem, "pkcs12", '-export', '-clcerts', '-passout', 'pass:' + passwd)
        p12 = load_pkcs12(p12_str, passwd)
        # verify
        self.assertTrue(isinstance(p12, PKCS12))
        cert_pem = dump_certificate(FILETYPE_PEM, p12.get_certificate())
        self.assertEqual(cert_pem, client_cert_pem)
        key_pem = dump_privatekey(FILETYPE_PEM, p12.get_privatekey())
        self.assertEqual(key_pem, client_key_pem)
        self.assertEqual(None, p12.get_ca_certificates())


    def test_load_pkcs12_garbage(self):
        """
        L{load_pkcs12} raises L{OpenSSL.crypto.Error} when passed a string
        which is not a PKCS12 dump.
        """
        passwd = 'whatever'
        e = self.assertRaises(Error, load_pkcs12, 'fruit loops', passwd)
        self.assertEqual( e.args[0][0][0], 'asn1 encoding routines')
        self.assertEqual( len(e.args[0][0]), 3)


    def test_replace(self):
        """
        L{PKCS12.set_certificate} replaces the certificate in a PKCS12 cluster.
        L{PKCS12.set_privatekey} replaces the private key.
        L{PKCS12.set_ca_certificates} replaces the CA certificates.
        """
        p12 = self.gen_pkcs12(client_cert_pem, client_key_pem, root_cert_pem)
        p12.set_certificate(load_certificate(FILETYPE_PEM, server_cert_pem))
        p12.set_privatekey(load_privatekey(FILETYPE_PEM, server_key_pem))
        root_cert = load_certificate(FILETYPE_PEM, root_cert_pem)
        client_cert = load_certificate(FILETYPE_PEM, client_cert_pem)
        p12.set_ca_certificates([root_cert]) # not a tuple
        self.assertEqual(1, len(p12.get_ca_certificates()))
        self.assertEqual(root_cert, p12.get_ca_certificates()[0])
        p12.set_ca_certificates([client_cert, root_cert])
        self.assertEqual(2, len(p12.get_ca_certificates()))
        self.assertEqual(client_cert, p12.get_ca_certificates()[0])
        self.assertEqual(root_cert, p12.get_ca_certificates()[1])


    def test_friendly_name(self):
        """
        The I{friendlyName} of a PKCS12 can be set and retrieved via
        L{PKCS12.get_friendlyname} and L{PKCS12_set_friendlyname}, and a
        L{PKCS12} with a friendly name set can be dumped with L{PKCS12.export}.
        """
        passwd = 'Dogmeat[]{}!@#$%^&*()~`?/.,<>-_+=";:'
        p12 = self.gen_pkcs12(server_cert_pem, server_key_pem, root_cert_pem)
        for friendly_name in [b('Serverlicious'), None, b('###')]:
            p12.set_friendlyname(friendly_name)
            self.assertEqual(p12.get_friendlyname(), friendly_name)
            dumped_p12 = p12.export(passphrase=passwd, iter=2, maciter=3)
            reloaded_p12 = load_pkcs12(dumped_p12, passwd)
            self.assertEqual(
                p12.get_friendlyname(), reloaded_p12.get_friendlyname())
            # We would use the openssl program to confirm the friendly
            # name, but it is not possible.  The pkcs12 command
            # does not store the friendly name in the cert's
            # alias, which we could then extract.
            self.check_recovery(
                dumped_p12, key=server_key_pem, cert=server_cert_pem,
                ca=root_cert_pem, passwd=passwd)


    def test_various_empty_passphrases(self):
        """
        Test that missing, None, and '' passphrases are identical for PKCS12
        export.
        """
        p12 = self.gen_pkcs12(client_cert_pem, client_key_pem, root_cert_pem)
        passwd = ''
        dumped_p12_empty = p12.export(iter=2, maciter=0, passphrase=passwd)
        dumped_p12_none = p12.export(iter=3, maciter=2, passphrase=None)
        dumped_p12_nopw = p12.export(iter=9, maciter=4)
        for dumped_p12 in [dumped_p12_empty, dumped_p12_none, dumped_p12_nopw]:
            self.check_recovery(
                dumped_p12, key=client_key_pem, cert=client_cert_pem,
                ca=root_cert_pem, passwd=passwd)


    def test_removing_ca_cert(self):
        """
        Passing C{None} to L{PKCS12.set_ca_certificates} removes all CA
        certificates.
        """
        p12 = self.gen_pkcs12(server_cert_pem, server_key_pem, root_cert_pem)
        p12.set_ca_certificates(None)
        self.assertEqual(None, p12.get_ca_certificates())


    def test_export_without_mac(self):
        """
        Exporting a PKCS12 with a C{maciter} of C{-1} excludes the MAC
        entirely.
        """
        passwd = 'Lake Michigan'
        p12 = self.gen_pkcs12(server_cert_pem, server_key_pem, root_cert_pem)
        dumped_p12 = p12.export(maciter=-1, passphrase=passwd, iter=2)
        self.check_recovery(
            dumped_p12, key=server_key_pem, cert=server_cert_pem,
            passwd=passwd, extra=('-nomacver',))


    def test_load_without_mac(self):
        """
        Loading a PKCS12 without a MAC does something other than crash.
        """
        passwd = 'Lake Michigan'
        p12 = self.gen_pkcs12(server_cert_pem, server_key_pem, root_cert_pem)
        dumped_p12 = p12.export(maciter=-1, passphrase=passwd, iter=2)
        try:
            recovered_p12 = load_pkcs12(dumped_p12, passwd)
            # The person who generated this PCKS12 should be flogged,
            # or better yet we should have a means to determine
            # whether a PCKS12 had a MAC that was verified.
            # Anyway, libopenssl chooses to allow it, so the
            # pyopenssl binding does as well.
            self.assertTrue(isinstance(recovered_p12, PKCS12))
        except Error:
            # Failing here with an exception is preferred as some openssl
            # versions do.
            pass


    def test_zero_len_list_for_ca(self):
        """
        A PKCS12 with an empty CA certificates list can be exported.
        """
        passwd = 'Hobie 18'
        p12 = self.gen_pkcs12(server_cert_pem, server_key_pem)
        p12.set_ca_certificates([])
        self.assertEqual((), p12.get_ca_certificates())
        dumped_p12 = p12.export(passphrase=passwd, iter=3)
        self.check_recovery(
            dumped_p12, key=server_key_pem, cert=server_cert_pem,
            passwd=passwd)


    def test_export_without_args(self):
        """
        All the arguments to L{PKCS12.export} are optional.
        """
        p12 = self.gen_pkcs12(server_cert_pem, server_key_pem, root_cert_pem)
        dumped_p12 = p12.export()  # no args
        self.check_recovery(
            dumped_p12, key=server_key_pem, cert=server_cert_pem, passwd='')


    def test_key_cert_mismatch(self):
        """
        L{PKCS12.export} raises an exception when a key and certificate
        mismatch.
        """
        p12 = self.gen_pkcs12(server_cert_pem, client_key_pem, root_cert_pem)
        self.assertRaises(Error, p12.export)



# These quoting functions taken directly from Twisted's twisted.python.win32.
_cmdLineQuoteRe = re.compile(r'(\\*)"')
_cmdLineQuoteRe2 = re.compile(r'(\\+)\Z')
def cmdLineQuote(s):
    """
    Internal method for quoting a single command-line argument.

    @type: C{str}
    @param s: A single unquoted string to quote for something that is expecting
        cmd.exe-style quoting

    @rtype: C{str}
    @return: A cmd.exe-style quoted string

    @see: U{http://www.perlmonks.org/?node_id=764004}
    """
    s = _cmdLineQuoteRe2.sub(r"\1\1", _cmdLineQuoteRe.sub(r'\1\1\\"', s))
    return '"%s"' % s



def quoteArguments(arguments):
    """
    Quote an iterable of command-line arguments for passing to CreateProcess or
    a similar API.  This allows the list passed to C{reactor.spawnProcess} to
    match the child process's C{sys.argv} properly.

    @type arguments: C{iterable} of C{str}
    @param arguments: An iterable of unquoted arguments to quote

    @rtype: C{str}
    @return: A space-delimited string containing quoted versions of L{arguments}
    """
    return ' '.join(map(cmdLineQuote, arguments))



def _runopenssl(pem, *args):
    """
    Run the command line openssl tool with the given arguments and write
    the given PEM to its stdin.  Not safe for quotes.
    """
    if os.name == 'posix':
        command = "openssl " + " ".join([
                "'%s'" % (arg.replace("'", "'\\''"),) for arg in args])
    else:
        command = "openssl " + quoteArguments(args)
    proc = Popen(command, shell=True, stdin=PIPE, stdout=PIPE)
    proc.stdin.write(pem)
    proc.stdin.close()
    return proc.stdout.read()



class FunctionTests(TestCase):
    """
    Tests for free-functions in the L{OpenSSL.crypto} module.
    """

    def test_load_privatekey_invalid_format(self):
        """
        L{load_privatekey} raises L{ValueError} if passed an unknown filetype.
        """
        self.assertRaises(ValueError, load_privatekey, 100, root_key_pem)


    def test_load_privatekey_invalid_passphrase_type(self):
        """
        L{load_privatekey} raises L{TypeError} if passed a passphrase that is
        neither a c{str} nor a callable.
        """
        self.assertRaises(
            TypeError,
            load_privatekey,
            FILETYPE_PEM, encryptedPrivateKeyPEMPassphrase, object())


    def test_load_privatekey_wrong_args(self):
        """
        L{load_privatekey} raises L{TypeError} if called with the wrong number
        of arguments.
        """
        self.assertRaises(TypeError, load_privatekey)


    def test_load_privatekey_wrongPassphrase(self):
        """
        L{load_privatekey} raises L{OpenSSL.crypto.Error} when it is passed an
        encrypted PEM and an incorrect passphrase.
        """
        self.assertRaises(
            Error,
            load_privatekey, FILETYPE_PEM, encryptedPrivateKeyPEM, b("quack"))


    def test_load_privatekey_passphrase(self):
        """
        L{load_privatekey} can create a L{PKey} object from an encrypted PEM
        string if given the passphrase.
        """
        key = load_privatekey(
            FILETYPE_PEM, encryptedPrivateKeyPEM,
            encryptedPrivateKeyPEMPassphrase)
        self.assertTrue(isinstance(key, PKeyType))


    def test_load_privatekey_wrongPassphraseCallback(self):
        """
        L{load_privatekey} raises L{OpenSSL.crypto.Error} when it is passed an
        encrypted PEM and a passphrase callback which returns an incorrect
        passphrase.
        """
        called = []
        def cb(*a):
            called.append(None)
            return "quack"
        self.assertRaises(
            Error,
            load_privatekey, FILETYPE_PEM, encryptedPrivateKeyPEM, cb)
        self.assertTrue(called)


    def test_load_privatekey_passphraseCallback(self):
        """
        L{load_privatekey} can create a L{PKey} object from an encrypted PEM
        string if given a passphrase callback which returns the correct
        password.
        """
        called = []
        def cb(writing):
            called.append(writing)
            return encryptedPrivateKeyPEMPassphrase
        key = load_privatekey(FILETYPE_PEM, encryptedPrivateKeyPEM, cb)
        self.assertTrue(isinstance(key, PKeyType))
        self.assertEqual(called, [False])


    def test_load_privatekey_passphrase_exception(self):
        """
        An exception raised by the passphrase callback passed to
        L{load_privatekey} causes L{OpenSSL.crypto.Error} to be raised.

        This isn't as nice as just letting the exception pass through.  The
        behavior might be changed to that eventually.
        """
        def broken(ignored):
            raise RuntimeError("This is not working.")
        self.assertRaises(
            Error,
            load_privatekey,
            FILETYPE_PEM, encryptedPrivateKeyPEM, broken)


    def test_dump_privatekey_wrong_args(self):
        """
        L{dump_privatekey} raises L{TypeError} if called with the wrong number
        of arguments.
        """
        self.assertRaises(TypeError, dump_privatekey)


    def test_dump_privatekey_unknown_cipher(self):
        """
        L{dump_privatekey} raises L{ValueError} if called with an unrecognized
        cipher name.
        """
        key = PKey()
        key.generate_key(TYPE_RSA, 512)
        self.assertRaises(
            ValueError, dump_privatekey,
            FILETYPE_PEM, key, "zippers", "passphrase")


    def test_dump_privatekey_invalid_passphrase_type(self):
        """
        L{dump_privatekey} raises L{TypeError} if called with a passphrase which
        is neither a C{str} nor a callable.
        """
        key = PKey()
        key.generate_key(TYPE_RSA, 512)
        self.assertRaises(
            TypeError,
            dump_privatekey, FILETYPE_PEM, key, "blowfish", object())


    def test_dump_privatekey_invalid_filetype(self):
        """
        L{dump_privatekey} raises L{ValueError} if called with an unrecognized
        filetype.
        """
        key = PKey()
        key.generate_key(TYPE_RSA, 512)
        self.assertRaises(ValueError, dump_privatekey, 100, key)


    def test_dump_privatekey_passphrase(self):
        """
        L{dump_privatekey} writes an encrypted PEM when given a passphrase.
        """
        passphrase = b("foo")
        key = load_privatekey(FILETYPE_PEM, cleartextPrivateKeyPEM)
        pem = dump_privatekey(FILETYPE_PEM, key, "blowfish", passphrase)
        self.assertTrue(isinstance(pem, bytes))
        loadedKey = load_privatekey(FILETYPE_PEM, pem, passphrase)
        self.assertTrue(isinstance(loadedKey, PKeyType))
        self.assertEqual(loadedKey.type(), key.type())
        self.assertEqual(loadedKey.bits(), key.bits())


    def test_dump_certificate(self):
        """
        L{dump_certificate} writes PEM, DER, and text.
        """
        pemData = cleartextCertificatePEM + cleartextPrivateKeyPEM
        cert = load_certificate(FILETYPE_PEM, pemData)
        dumped_pem = dump_certificate(FILETYPE_PEM, cert)
        self.assertEqual(dumped_pem, cleartextCertificatePEM)
        dumped_der = dump_certificate(FILETYPE_ASN1, cert)
        good_der = _runopenssl(dumped_pem, "x509", "-outform", "DER")
        self.assertEqual(dumped_der, good_der)
        cert2 = load_certificate(FILETYPE_ASN1, dumped_der)
        dumped_pem2 = dump_certificate(FILETYPE_PEM, cert2)
        self.assertEqual(dumped_pem2, cleartextCertificatePEM)
        dumped_text = dump_certificate(FILETYPE_TEXT, cert)
        good_text = _runopenssl(dumped_pem, "x509", "-noout", "-text")
        self.assertEqual(dumped_text, good_text)


    def test_dump_privatekey(self):
        """
        L{dump_privatekey} writes a PEM, DER, and text.
        """
        key = load_privatekey(FILETYPE_PEM, cleartextPrivateKeyPEM)
        self.assertTrue(key.check())
        dumped_pem = dump_privatekey(FILETYPE_PEM, key)
        self.assertEqual(dumped_pem, cleartextPrivateKeyPEM)
        dumped_der = dump_privatekey(FILETYPE_ASN1, key)
        # XXX This OpenSSL call writes "writing RSA key" to standard out.  Sad.
        good_der = _runopenssl(dumped_pem, "rsa", "-outform", "DER")
        self.assertEqual(dumped_der, good_der)
        key2 = load_privatekey(FILETYPE_ASN1, dumped_der)
        dumped_pem2 = dump_privatekey(FILETYPE_PEM, key2)
        self.assertEqual(dumped_pem2, cleartextPrivateKeyPEM)
        dumped_text = dump_privatekey(FILETYPE_TEXT, key)
        good_text = _runopenssl(dumped_pem, "rsa", "-noout", "-text")
        self.assertEqual(dumped_text, good_text)


    def test_dump_certificate_request(self):
        """
        L{dump_certificate_request} writes a PEM, DER, and text.
        """
        req = load_certificate_request(FILETYPE_PEM, cleartextCertificateRequestPEM)
        dumped_pem = dump_certificate_request(FILETYPE_PEM, req)
        self.assertEqual(dumped_pem, cleartextCertificateRequestPEM)
        dumped_der = dump_certificate_request(FILETYPE_ASN1, req)
        good_der = _runopenssl(dumped_pem, "req", "-outform", "DER")
        self.assertEqual(dumped_der, good_der)
        req2 = load_certificate_request(FILETYPE_ASN1, dumped_der)
        dumped_pem2 = dump_certificate_request(FILETYPE_PEM, req2)
        self.assertEqual(dumped_pem2, cleartextCertificateRequestPEM)
        dumped_text = dump_certificate_request(FILETYPE_TEXT, req)
        good_text = _runopenssl(dumped_pem, "req", "-noout", "-text")
        self.assertEqual(dumped_text, good_text)
        self.assertRaises(ValueError, dump_certificate_request, 100, req)


    def test_dump_privatekey_passphraseCallback(self):
        """
        L{dump_privatekey} writes an encrypted PEM when given a callback which
        returns the correct passphrase.
        """
        passphrase = b("foo")
        called = []
        def cb(writing):
            called.append(writing)
            return passphrase
        key = load_privatekey(FILETYPE_PEM, cleartextPrivateKeyPEM)
        pem = dump_privatekey(FILETYPE_PEM, key, "blowfish", cb)
        self.assertTrue(isinstance(pem, bytes))
        self.assertEqual(called, [True])
        loadedKey = load_privatekey(FILETYPE_PEM, pem, passphrase)
        self.assertTrue(isinstance(loadedKey, PKeyType))
        self.assertEqual(loadedKey.type(), key.type())
        self.assertEqual(loadedKey.bits(), key.bits())


    def test_load_pkcs7_data(self):
        """
        L{load_pkcs7_data} accepts a PKCS#7 string and returns an instance of
        L{PKCS7Type}.
        """
        pkcs7 = load_pkcs7_data(FILETYPE_PEM, pkcs7Data)
        self.assertTrue(isinstance(pkcs7, PKCS7Type))



class PKCS7Tests(TestCase):
    """
    Tests for L{PKCS7Type}.
    """
    def test_type(self):
        """
        L{PKCS7Type} is a type object.
        """
        self.assertTrue(isinstance(PKCS7Type, type))
        self.assertEqual(PKCS7Type.__name__, 'PKCS7')

        # XXX This doesn't currently work.
        # self.assertIdentical(PKCS7, PKCS7Type)


    # XXX Opposite results for all these following methods

    def test_type_is_signed_wrong_args(self):
        """
        L{PKCS7Type.type_is_signed} raises L{TypeError} if called with any
        arguments.
        """
        pkcs7 = load_pkcs7_data(FILETYPE_PEM, pkcs7Data)
        self.assertRaises(TypeError, pkcs7.type_is_signed, None)


    def test_type_is_signed(self):
        """
        L{PKCS7Type.type_is_signed} returns C{True} if the PKCS7 object is of
        the type I{signed}.
        """
        pkcs7 = load_pkcs7_data(FILETYPE_PEM, pkcs7Data)
        self.assertTrue(pkcs7.type_is_signed())


    def test_type_is_enveloped_wrong_args(self):
        """
        L{PKCS7Type.type_is_enveloped} raises L{TypeError} if called with any
        arguments.
        """
        pkcs7 = load_pkcs7_data(FILETYPE_PEM, pkcs7Data)
        self.assertRaises(TypeError, pkcs7.type_is_enveloped, None)


    def test_type_is_enveloped(self):
        """
        L{PKCS7Type.type_is_enveloped} returns C{False} if the PKCS7 object is
        not of the type I{enveloped}.
        """
        pkcs7 = load_pkcs7_data(FILETYPE_PEM, pkcs7Data)
        self.assertFalse(pkcs7.type_is_enveloped())


    def test_type_is_signedAndEnveloped_wrong_args(self):
        """
        L{PKCS7Type.type_is_signedAndEnveloped} raises L{TypeError} if called
        with any arguments.
        """
        pkcs7 = load_pkcs7_data(FILETYPE_PEM, pkcs7Data)
        self.assertRaises(TypeError, pkcs7.type_is_signedAndEnveloped, None)


    def test_type_is_signedAndEnveloped(self):
        """
        L{PKCS7Type.type_is_signedAndEnveloped} returns C{False} if the PKCS7
        object is not of the type I{signed and enveloped}.
        """
        pkcs7 = load_pkcs7_data(FILETYPE_PEM, pkcs7Data)
        self.assertFalse(pkcs7.type_is_signedAndEnveloped())


    def test_type_is_data(self):
        """
        L{PKCS7Type.type_is_data} returns C{False} if the PKCS7 object is not of
        the type data.
        """
        pkcs7 = load_pkcs7_data(FILETYPE_PEM, pkcs7Data)
        self.assertFalse(pkcs7.type_is_data())


    def test_type_is_data_wrong_args(self):
        """
        L{PKCS7Type.type_is_data} raises L{TypeError} if called with any
        arguments.
        """
        pkcs7 = load_pkcs7_data(FILETYPE_PEM, pkcs7Data)
        self.assertRaises(TypeError, pkcs7.type_is_data, None)


    def test_get_type_name_wrong_args(self):
        """
        L{PKCS7Type.get_type_name} raises L{TypeError} if called with any
        arguments.
        """
        pkcs7 = load_pkcs7_data(FILETYPE_PEM, pkcs7Data)
        self.assertRaises(TypeError, pkcs7.get_type_name, None)


    def test_get_type_name(self):
        """
        L{PKCS7Type.get_type_name} returns a C{str} giving the type name.
        """
        pkcs7 = load_pkcs7_data(FILETYPE_PEM, pkcs7Data)
        self.assertEquals(pkcs7.get_type_name(), b('pkcs7-signedData'))


    def test_attribute(self):
        """
        If an attribute other than one of the methods tested here is accessed on
        an instance of L{PKCS7Type}, L{AttributeError} is raised.
        """
        pkcs7 = load_pkcs7_data(FILETYPE_PEM, pkcs7Data)
        self.assertRaises(AttributeError, getattr, pkcs7, "foo")



class NetscapeSPKITests(TestCase, _PKeyInteractionTestsMixin):
    """
    Tests for L{OpenSSL.crypto.NetscapeSPKI}.
    """
    def signable(self):
        """
        Return a new L{NetscapeSPKI} for use with signing tests.
        """
        return NetscapeSPKI()


    def test_type(self):
        """
        L{NetscapeSPKI} and L{NetscapeSPKIType} refer to the same type object
        and can be used to create instances of that type.
        """
        self.assertIdentical(NetscapeSPKI, NetscapeSPKIType)
        self.assertConsistentType(NetscapeSPKI, 'NetscapeSPKI')


    def test_construction(self):
        """
        L{NetscapeSPKI} returns an instance of L{NetscapeSPKIType}.
        """
        nspki = NetscapeSPKI()
        self.assertTrue(isinstance(nspki, NetscapeSPKIType))


    def test_invalid_attribute(self):
        """
        Accessing a non-existent attribute of a L{NetscapeSPKI} instance causes
        an L{AttributeError} to be raised.
        """
        nspki = NetscapeSPKI()
        self.assertRaises(AttributeError, lambda: nspki.foo)


    def test_b64_encode(self):
        """
        L{NetscapeSPKI.b64_encode} encodes the certificate to a base64 blob.
        """
        nspki = NetscapeSPKI()
        blob = nspki.b64_encode()
        self.assertTrue(isinstance(blob, bytes))



class RevokedTests(TestCase):
    """
    Tests for L{OpenSSL.crypto.Revoked}
    """
    def test_construction(self):
        """
        Confirm we can create L{OpenSSL.crypto.Revoked}.  Check
        that it is empty.
        """
        revoked = Revoked()
        self.assertTrue(isinstance(revoked, Revoked))
        self.assertEquals(type(revoked), Revoked)
        self.assertEquals(revoked.get_serial(), b('00'))
        self.assertEquals(revoked.get_rev_date(), None)
        self.assertEquals(revoked.get_reason(), None)


    def test_construction_wrong_args(self):
        """
        Calling L{OpenSSL.crypto.Revoked} with any arguments results
        in a L{TypeError} being raised.
        """
        self.assertRaises(TypeError, Revoked, None)
        self.assertRaises(TypeError, Revoked, 1)
        self.assertRaises(TypeError, Revoked, "foo")


    def test_serial(self):
        """
        Confirm we can set and get serial numbers from
        L{OpenSSL.crypto.Revoked}.  Confirm errors are handled
        with grace.
        """
        revoked = Revoked()
        ret = revoked.set_serial(b('10b'))
        self.assertEquals(ret, None)
        ser = revoked.get_serial()
        self.assertEquals(ser, b('010B'))

        revoked.set_serial(b('31ppp'))  # a type error would be nice
        ser = revoked.get_serial()
        self.assertEquals(ser, b('31'))

        self.assertRaises(ValueError, revoked.set_serial, b('pqrst'))
        self.assertRaises(TypeError, revoked.set_serial, 100)
        self.assertRaises(TypeError, revoked.get_serial, 1)
        self.assertRaises(TypeError, revoked.get_serial, None)
        self.assertRaises(TypeError, revoked.get_serial, "")


    def test_date(self):
        """
        Confirm we can set and get revocation dates from
        L{OpenSSL.crypto.Revoked}.  Confirm errors are handled
        with grace.
        """
        revoked = Revoked()
        date = revoked.get_rev_date()
        self.assertEquals(date, None)

        now = b(datetime.now().strftime("%Y%m%d%H%M%SZ"))
        ret = revoked.set_rev_date(now)
        self.assertEqual(ret, None)
        date = revoked.get_rev_date()
        self.assertEqual(date, now)


    def test_reason(self):
        """
        Confirm we can set and get revocation reasons from
        L{OpenSSL.crypto.Revoked}.  The "get" need to work
        as "set".  Likewise, each reason of all_reasons() must work.
        """
        revoked = Revoked()
        for r in revoked.all_reasons():
            for x in range(2):
                ret = revoked.set_reason(r)
                self.assertEquals(ret, None)
                reason = revoked.get_reason()
                self.assertEquals(
                    reason.lower().replace(b(' '), b('')),
                    r.lower().replace(b(' '), b('')))
                r = reason # again with the resp of get

        revoked.set_reason(None)
        self.assertEqual(revoked.get_reason(), None)


    def test_set_reason_wrong_arguments(self):
        """
        Calling L{OpenSSL.crypto.Revoked.set_reason} with other than
        one argument, or an argument which isn't a valid reason,
        results in L{TypeError} or L{ValueError} being raised.
        """
        revoked = Revoked()
        self.assertRaises(TypeError, revoked.set_reason, 100)
        self.assertRaises(ValueError, revoked.set_reason, b('blue'))


    def test_get_reason_wrong_arguments(self):
        """
        Calling L{OpenSSL.crypto.Revoked.get_reason} with any
        arguments results in L{TypeError} being raised.
        """
        revoked = Revoked()
        self.assertRaises(TypeError, revoked.get_reason, None)
        self.assertRaises(TypeError, revoked.get_reason, 1)
        self.assertRaises(TypeError, revoked.get_reason, "foo")



class CRLTests(TestCase):
    """
    Tests for L{OpenSSL.crypto.CRL}
    """
    cert = load_certificate(FILETYPE_PEM, cleartextCertificatePEM)
    pkey = load_privatekey(FILETYPE_PEM, cleartextPrivateKeyPEM)

    def test_construction(self):
        """
        Confirm we can create L{OpenSSL.crypto.CRL}.  Check
        that it is empty
        """
        crl = CRL()
        self.assertTrue( isinstance(crl, CRL) )
        self.assertEqual(crl.get_revoked(), None)


    def test_construction_wrong_args(self):
        """
        Calling L{OpenSSL.crypto.CRL} with any number of arguments
        results in a L{TypeError} being raised.
        """
        self.assertRaises(TypeError, CRL, 1)
        self.assertRaises(TypeError, CRL, "")
        self.assertRaises(TypeError, CRL, None)


    def test_export(self):
        """
        Use python to create a simple CRL with a revocation, and export
        the CRL in formats of PEM, DER and text.  Those outputs are verified
        with the openssl program.
        """
        crl = CRL()
        revoked = Revoked()
        now = b(datetime.now().strftime("%Y%m%d%H%M%SZ"))
        revoked.set_rev_date(now)
        revoked.set_serial(b('3ab'))
        revoked.set_reason(b('sUpErSeDEd'))
        crl.add_revoked(revoked)

        # PEM format
        dumped_crl = crl.export(self.cert, self.pkey, days=20)
        text = _runopenssl(dumped_crl, "crl", "-noout", "-text")
        text.index(b('Serial Number: 03AB'))
        text.index(b('Superseded'))
        text.index(b('Issuer: /C=US/ST=IL/L=Chicago/O=Testing/CN=Testing Root CA'))

        # DER format
        dumped_crl = crl.export(self.cert, self.pkey, FILETYPE_ASN1)
        text = _runopenssl(dumped_crl, "crl", "-noout", "-text", "-inform", "DER")
        text.index(b('Serial Number: 03AB'))
        text.index(b('Superseded'))
        text.index(b('Issuer: /C=US/ST=IL/L=Chicago/O=Testing/CN=Testing Root CA'))

        # text format
        dumped_text = crl.export(self.cert, self.pkey, type=FILETYPE_TEXT)
        self.assertEqual(text, dumped_text)


    def test_add_revoked_keyword(self):
        """
        L{OpenSSL.CRL.add_revoked} accepts its single argument as the
        I{revoked} keyword argument.
        """
        crl = CRL()
        revoked = Revoked()
        crl.add_revoked(revoked=revoked)
        self.assertTrue(isinstance(crl.get_revoked()[0], Revoked))


    def test_export_wrong_args(self):
        """
        Calling L{OpenSSL.CRL.export} with fewer than two or more than
        four arguments, or with arguments other than the certificate,
        private key, integer file type, and integer number of days it
        expects, results in a L{TypeError} being raised.
        """
        crl = CRL()
        self.assertRaises(TypeError, crl.export)
        self.assertRaises(TypeError, crl.export, self.cert)
        self.assertRaises(TypeError, crl.export, self.cert, self.pkey, FILETYPE_PEM, 10, "foo")

        self.assertRaises(TypeError, crl.export, None, self.pkey, FILETYPE_PEM, 10)
        self.assertRaises(TypeError, crl.export, self.cert, None, FILETYPE_PEM, 10)
        self.assertRaises(TypeError, crl.export, self.cert, self.pkey, None, 10)
        self.assertRaises(TypeError, crl.export, self.cert, FILETYPE_PEM, None)


    def test_export_unknown_filetype(self):
        """
        Calling L{OpenSSL.CRL.export} with a file type other than
        L{FILETYPE_PEM}, L{FILETYPE_ASN1}, or L{FILETYPE_TEXT} results
        in a L{ValueError} being raised.
        """
        crl = CRL()
        self.assertRaises(ValueError, crl.export, self.cert, self.pkey, 100, 10)


    def test_get_revoked(self):
        """
        Use python to create a simple CRL with two revocations.
        Get back the L{Revoked} using L{OpenSSL.CRL.get_revoked} and
        verify them.
        """
        crl = CRL()

        revoked = Revoked()
        now = b(datetime.now().strftime("%Y%m%d%H%M%SZ"))
        revoked.set_rev_date(now)
        revoked.set_serial(b('3ab'))
        crl.add_revoked(revoked)
        revoked.set_serial(b('100'))
        revoked.set_reason(b('sUpErSeDEd'))
        crl.add_revoked(revoked)

        revs = crl.get_revoked()
        self.assertEqual(len(revs), 2)
        self.assertEqual(type(revs[0]), Revoked)
        self.assertEqual(type(revs[1]), Revoked)
        self.assertEqual(revs[0].get_serial(), b('03AB'))
        self.assertEqual(revs[1].get_serial(), b('0100'))
        self.assertEqual(revs[0].get_rev_date(), now)
        self.assertEqual(revs[1].get_rev_date(), now)


    def test_get_revoked_wrong_args(self):
        """
        Calling L{OpenSSL.CRL.get_revoked} with any arguments results
        in a L{TypeError} being raised.
        """
        crl = CRL()
        self.assertRaises(TypeError, crl.get_revoked, None)
        self.assertRaises(TypeError, crl.get_revoked, 1)
        self.assertRaises(TypeError, crl.get_revoked, "")
        self.assertRaises(TypeError, crl.get_revoked, "", 1, None)


    def test_add_revoked_wrong_args(self):
        """
        Calling L{OpenSSL.CRL.add_revoked} with other than one
        argument results in a L{TypeError} being raised.
        """
        crl = CRL()
        self.assertRaises(TypeError, crl.add_revoked)
        self.assertRaises(TypeError, crl.add_revoked, 1, 2)
        self.assertRaises(TypeError, crl.add_revoked, "foo", "bar")


    def test_load_crl(self):
        """
        Load a known CRL and inspect its revocations.  Both
        PEM and DER formats are loaded.
        """
        crl = load_crl(FILETYPE_PEM, crlData)
        revs = crl.get_revoked()
        self.assertEqual(len(revs), 2)
        self.assertEqual(revs[0].get_serial(), b('03AB'))
        self.assertEqual(revs[0].get_reason(), None)
        self.assertEqual(revs[1].get_serial(), b('0100'))
        self.assertEqual(revs[1].get_reason(), b('Superseded'))

        der = _runopenssl(crlData, "crl", "-outform", "DER")
        crl = load_crl(FILETYPE_ASN1, der)
        revs = crl.get_revoked()
        self.assertEqual(len(revs), 2)
        self.assertEqual(revs[0].get_serial(), b('03AB'))
        self.assertEqual(revs[0].get_reason(), None)
        self.assertEqual(revs[1].get_serial(), b('0100'))
        self.assertEqual(revs[1].get_reason(), b('Superseded'))


    def test_load_crl_wrong_args(self):
        """
        Calling L{OpenSSL.crypto.load_crl} with other than two
        arguments results in a L{TypeError} being raised.
        """
        self.assertRaises(TypeError, load_crl)
        self.assertRaises(TypeError, load_crl, FILETYPE_PEM)
        self.assertRaises(TypeError, load_crl, FILETYPE_PEM, crlData, None)


    def test_load_crl_bad_filetype(self):
        """
        Calling L{OpenSSL.crypto.load_crl} with an unknown file type
        raises a L{ValueError}.
        """
        self.assertRaises(ValueError, load_crl, 100, crlData)


    def test_load_crl_bad_data(self):
        """
        Calling L{OpenSSL.crypto.load_crl} with file data which can't
        be loaded raises a L{OpenSSL.crypto.Error}.
        """
        self.assertRaises(Error, load_crl, FILETYPE_PEM, "hello, world")


class SignVerifyTests(TestCase):
    """
    Tests for L{OpenSSL.crypto.sign} and L{OpenSSL.crypto.verify}.
    """
    def test_sign_verify(self):
        """
        L{sign} generates a cryptographic signature which L{verify} can check.
        """
        content = b(
            "It was a bright cold day in April, and the clocks were striking "
            "thirteen. Winston Smith, his chin nuzzled into his breast in an "
            "effort to escape the vile wind, slipped quickly through the "
            "glass doors of Victory Mansions, though not quickly enough to "
            "prevent a swirl of gritty dust from entering along with him.")

        # sign the content with this private key
        priv_key = load_privatekey(FILETYPE_PEM, root_key_pem)
        # verify the content with this cert
        good_cert = load_certificate(FILETYPE_PEM, root_cert_pem)
        # certificate unrelated to priv_key, used to trigger an error
        bad_cert = load_certificate(FILETYPE_PEM, server_cert_pem)

        for digest in ['md5', 'sha1']:
            sig = sign(priv_key, content, digest)

            # Verify the signature of content, will throw an exception if error.
            verify(good_cert, sig, content, digest)

            # This should fail because the certificate doesn't match the
            # private key that was used to sign the content.
            self.assertRaises(Error, verify, bad_cert, sig, content, digest)

            # This should fail because we've "tainted" the content after
            # signing it.
            self.assertRaises(
                Error, verify,
                good_cert, sig, content + b("tainted"), digest)

        # test that unknown digest types fail
        self.assertRaises(
            ValueError, sign, priv_key, content, "strange-digest")
        self.assertRaises(
            ValueError, verify, good_cert, sig, content, "strange-digest")


    def test_sign_nulls(self):
        """
        L{sign} produces a signature for a string with embedded nulls.
        """
        content = b("Watch out!  \0  Did you see it?")
        priv_key = load_privatekey(FILETYPE_PEM, root_key_pem)
        good_cert = load_certificate(FILETYPE_PEM, root_cert_pem)
        sig = sign(priv_key, content, "sha1")
        verify(good_cert, sig, content, "sha1")


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_rand
# Copyright (c) Frederick Dean
# See LICENSE for details.

"""
Unit tests for L{OpenSSL.rand}.
"""

from unittest import main
import os
import stat

from OpenSSL.test.util import TestCase, b
from OpenSSL import rand


class RandTests(TestCase):
    def test_bytes_wrong_args(self):
        """
        L{OpenSSL.rand.bytes} raises L{TypeError} if called with the wrong
        number of arguments or with a non-C{int} argument.
        """
        self.assertRaises(TypeError, rand.bytes)
        self.assertRaises(TypeError, rand.bytes, None)
        self.assertRaises(TypeError, rand.bytes, 3, None)

    # XXX Test failure of the malloc() in rand_bytes.

    def test_bytes(self):
        """
        Verify that we can obtain bytes from rand_bytes() and
        that they are different each time.  Test the parameter
        of rand_bytes() for bad values.
        """
        b1 = rand.bytes(50)
        self.assertEqual(len(b1), 50)
        b2 = rand.bytes(num_bytes=50)  # parameter by name
        self.assertNotEqual(b1, b2)  #  Hip, Hip, Horay! FIPS complaince
        b3 = rand.bytes(num_bytes=0)
        self.assertEqual(len(b3), 0)
        exc = self.assertRaises(ValueError, rand.bytes, -1)
        self.assertEqual(str(exc), "num_bytes must not be negative")


    def test_add_wrong_args(self):
        """
        When called with the wrong number of arguments, or with arguments not of
        type C{str} and C{int}, L{OpenSSL.rand.add} raises L{TypeError}.
        """
        self.assertRaises(TypeError, rand.add)
        self.assertRaises(TypeError, rand.add, b("foo"), None)
        self.assertRaises(TypeError, rand.add, None, 3)
        self.assertRaises(TypeError, rand.add, b("foo"), 3, None)


    def test_add(self):
        """
        L{OpenSSL.rand.add} adds entropy to the PRNG.
        """
        rand.add(b('hamburger'), 3)


    def test_seed_wrong_args(self):
        """
        When called with the wrong number of arguments, or with a non-C{str}
        argument, L{OpenSSL.rand.seed} raises L{TypeError}.
        """
        self.assertRaises(TypeError, rand.seed)
        self.assertRaises(TypeError, rand.seed, None)
        self.assertRaises(TypeError, rand.seed, b("foo"), None)


    def test_seed(self):
        """
        L{OpenSSL.rand.seed} adds entropy to the PRNG.
        """
        rand.seed(b('milk shake'))


    def test_status_wrong_args(self):
        """
        L{OpenSSL.rand.status} raises L{TypeError} when called with any
        arguments.
        """
        self.assertRaises(TypeError, rand.status, None)


    def test_status(self):
        """
        L{OpenSSL.rand.status} returns C{True} if the PRNG has sufficient
        entropy, C{False} otherwise.
        """
        # It's hard to know what it is actually going to return.  Different
        # OpenSSL random engines decide differently whether they have enough
        # entropy or not.
        self.assertTrue(rand.status() in (1, 2))


    def test_egd_wrong_args(self):
        """
        L{OpenSSL.rand.egd} raises L{TypeError} when called with the wrong
        number of arguments or with arguments not of type C{str} and C{int}.
        """
        self.assertRaises(TypeError, rand.egd)
        self.assertRaises(TypeError, rand.egd, None)
        self.assertRaises(TypeError, rand.egd, "foo", None)
        self.assertRaises(TypeError, rand.egd, None, 3)
        self.assertRaises(TypeError, rand.egd, "foo", 3, None)


    def test_egd_missing(self):
        """
        L{OpenSSL.rand.egd} returns C{0} or C{-1} if the EGD socket passed
        to it does not exist.
        """
        result = rand.egd(self.mktemp())
        expected = (-1, 0)
        self.assertTrue(
            result in expected,
            "%r not in %r" % (result, expected))


    def test_cleanup_wrong_args(self):
        """
        L{OpenSSL.rand.cleanup} raises L{TypeError} when called with any
        arguments.
        """
        self.assertRaises(TypeError, rand.cleanup, None)


    def test_cleanup(self):
        """
        L{OpenSSL.rand.cleanup} releases the memory used by the PRNG and returns
        C{None}.
        """
        self.assertIdentical(rand.cleanup(), None)


    def test_load_file_wrong_args(self):
        """
        L{OpenSSL.rand.load_file} raises L{TypeError} when called the wrong
        number of arguments or arguments not of type C{str} and C{int}.
        """
        self.assertRaises(TypeError, rand.load_file)
        self.assertRaises(TypeError, rand.load_file, "foo", None)
        self.assertRaises(TypeError, rand.load_file, None, 1)
        self.assertRaises(TypeError, rand.load_file, "foo", 1, None)


    def test_write_file_wrong_args(self):
        """
        L{OpenSSL.rand.write_file} raises L{TypeError} when called with the
        wrong number of arguments or a non-C{str} argument.
        """
        self.assertRaises(TypeError, rand.write_file)
        self.assertRaises(TypeError, rand.write_file, None)
        self.assertRaises(TypeError, rand.write_file, "foo", None)


    def test_files(self):
        """
        Test reading and writing of files via rand functions.
        """
        # Write random bytes to a file
        tmpfile = self.mktemp()
        # Make sure it exists (so cleanup definitely succeeds)
        fObj = open(tmpfile, 'w')
        fObj.close()
        try:
            rand.write_file(tmpfile)
            # Verify length of written file
            size = os.stat(tmpfile)[stat.ST_SIZE]
            self.assertEquals(size, 1024)
            # Read random bytes from file
            rand.load_file(tmpfile)
            rand.load_file(tmpfile, 4)  # specify a length
        finally:
            # Cleanup
            os.unlink(tmpfile)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_ssl
# Copyright (C) Jean-Paul Calderone
# See LICENSE for details.

"""
Unit tests for L{OpenSSL.SSL}.
"""

from gc import collect
from errno import ECONNREFUSED, EINPROGRESS, EWOULDBLOCK
from sys import platform, version_info
from socket import error, socket
from os import makedirs
from os.path import join
from unittest import main
from weakref import ref

from OpenSSL.crypto import TYPE_RSA, FILETYPE_PEM
from OpenSSL.crypto import PKey, X509, X509Extension
from OpenSSL.crypto import dump_privatekey, load_privatekey
from OpenSSL.crypto import dump_certificate, load_certificate

from OpenSSL.SSL import OPENSSL_VERSION_NUMBER, SSLEAY_VERSION, SSLEAY_CFLAGS
from OpenSSL.SSL import SSLEAY_PLATFORM, SSLEAY_DIR, SSLEAY_BUILT_ON
from OpenSSL.SSL import SENT_SHUTDOWN, RECEIVED_SHUTDOWN
from OpenSSL.SSL import SSLv2_METHOD, SSLv3_METHOD, SSLv23_METHOD, TLSv1_METHOD
from OpenSSL.SSL import OP_NO_SSLv2, OP_NO_SSLv3, OP_SINGLE_DH_USE
from OpenSSL.SSL import (
    VERIFY_PEER, VERIFY_FAIL_IF_NO_PEER_CERT, VERIFY_CLIENT_ONCE, VERIFY_NONE)
from OpenSSL.SSL import (
    Error, SysCallError, WantReadError, ZeroReturnError, SSLeay_version)
from OpenSSL.SSL import Context, ContextType, Connection, ConnectionType

from OpenSSL.test.util import TestCase, bytes, b
from OpenSSL.test.test_crypto import (
    cleartextCertificatePEM, cleartextPrivateKeyPEM)
from OpenSSL.test.test_crypto import (
    client_cert_pem, client_key_pem, server_cert_pem, server_key_pem,
    root_cert_pem)

try:
    from OpenSSL.SSL import OP_NO_QUERY_MTU
except ImportError:
    OP_NO_QUERY_MTU = None
try:
    from OpenSSL.SSL import OP_COOKIE_EXCHANGE
except ImportError:
    OP_COOKIE_EXCHANGE = None
try:
    from OpenSSL.SSL import OP_NO_TICKET
except ImportError:
    OP_NO_TICKET = None

from OpenSSL.SSL import (
    SSL_ST_CONNECT, SSL_ST_ACCEPT, SSL_ST_MASK, SSL_ST_INIT, SSL_ST_BEFORE,
    SSL_ST_OK, SSL_ST_RENEGOTIATE,
    SSL_CB_LOOP, SSL_CB_EXIT, SSL_CB_READ, SSL_CB_WRITE, SSL_CB_ALERT,
    SSL_CB_READ_ALERT, SSL_CB_WRITE_ALERT, SSL_CB_ACCEPT_LOOP,
    SSL_CB_ACCEPT_EXIT, SSL_CB_CONNECT_LOOP, SSL_CB_CONNECT_EXIT,
    SSL_CB_HANDSHAKE_START, SSL_CB_HANDSHAKE_DONE)

# openssl dhparam 128 -out dh-128.pem (note that 128 is a small number of bits
# to use)
dhparam = """\
-----BEGIN DH PARAMETERS-----
MBYCEQCobsg29c9WZP/54oAPcwiDAgEC
-----END DH PARAMETERS-----
"""


def verify_cb(conn, cert, errnum, depth, ok):
    return ok


def socket_pair():
    """
    Establish and return a pair of network sockets connected to each other.
    """
    # Connect a pair of sockets
    port = socket()
    port.bind(('', 0))
    port.listen(1)
    client = socket()
    client.setblocking(False)
    client.connect_ex(("127.0.0.1", port.getsockname()[1]))
    client.setblocking(True)
    server = port.accept()[0]

    # Let's pass some unencrypted data to make sure our socket connection is
    # fine.  Just one byte, so we don't have to worry about buffers getting
    # filled up or fragmentation.
    server.send(b("x"))
    assert client.recv(1024) == b("x")
    client.send(b("y"))
    assert server.recv(1024) == b("y")

    # Most of our callers want non-blocking sockets, make it easy for them.
    server.setblocking(False)
    client.setblocking(False)

    return (server, client)



def handshake(client, server):
    conns = [client, server]
    while conns:
        for conn in conns:
            try:
                conn.do_handshake()
            except WantReadError:
                pass
            else:
                conns.remove(conn)


def _create_certificate_chain():
    """
    Construct and return a chain of certificates.

        1. A new self-signed certificate authority certificate (cacert)
        2. A new intermediate certificate signed by cacert (icert)
        3. A new server certificate signed by icert (scert)
    """
    caext = X509Extension(b('basicConstraints'), False, b('CA:true'))

    # Step 1
    cakey = PKey()
    cakey.generate_key(TYPE_RSA, 512)
    cacert = X509()
    cacert.get_subject().commonName = "Authority Certificate"
    cacert.set_issuer(cacert.get_subject())
    cacert.set_pubkey(cakey)
    cacert.set_notBefore(b("20000101000000Z"))
    cacert.set_notAfter(b("20200101000000Z"))
    cacert.add_extensions([caext])
    cacert.set_serial_number(0)
    cacert.sign(cakey, "sha1")

    # Step 2
    ikey = PKey()
    ikey.generate_key(TYPE_RSA, 512)
    icert = X509()
    icert.get_subject().commonName = "Intermediate Certificate"
    icert.set_issuer(cacert.get_subject())
    icert.set_pubkey(ikey)
    icert.set_notBefore(b("20000101000000Z"))
    icert.set_notAfter(b("20200101000000Z"))
    icert.add_extensions([caext])
    icert.set_serial_number(0)
    icert.sign(cakey, "sha1")

    # Step 3
    skey = PKey()
    skey.generate_key(TYPE_RSA, 512)
    scert = X509()
    scert.get_subject().commonName = "Server Certificate"
    scert.set_issuer(icert.get_subject())
    scert.set_pubkey(skey)
    scert.set_notBefore(b("20000101000000Z"))
    scert.set_notAfter(b("20200101000000Z"))
    scert.add_extensions([
            X509Extension(b('basicConstraints'), True, b('CA:false'))])
    scert.set_serial_number(0)
    scert.sign(ikey, "sha1")

    return [(cakey, cacert), (ikey, icert), (skey, scert)]



class _LoopbackMixin:
    """
    Helper mixin which defines methods for creating a connected socket pair and
    for forcing two connected SSL sockets to talk to each other via memory BIOs.
    """
    def _loopback(self):
        (server, client) = socket_pair()

        ctx = Context(TLSv1_METHOD)
        ctx.use_privatekey(load_privatekey(FILETYPE_PEM, server_key_pem))
        ctx.use_certificate(load_certificate(FILETYPE_PEM, server_cert_pem))
        server = Connection(ctx, server)
        server.set_accept_state()
        client = Connection(Context(TLSv1_METHOD), client)
        client.set_connect_state()

        handshake(client, server)

        server.setblocking(True)
        client.setblocking(True)
        return server, client


    def _interactInMemory(self, client_conn, server_conn):
        """
        Try to read application bytes from each of the two L{Connection}
        objects.  Copy bytes back and forth between their send/receive buffers
        for as long as there is anything to copy.  When there is nothing more
        to copy, return C{None}.  If one of them actually manages to deliver
        some application bytes, return a two-tuple of the connection from which
        the bytes were read and the bytes themselves.
        """
        wrote = True
        while wrote:
            # Loop until neither side has anything to say
            wrote = False

            # Copy stuff from each side's send buffer to the other side's
            # receive buffer.
            for (read, write) in [(client_conn, server_conn),
                                  (server_conn, client_conn)]:

                # Give the side a chance to generate some more bytes, or
                # succeed.
                try:
                    data = read.recv(2 ** 16)
                except WantReadError:
                    # It didn't succeed, so we'll hope it generated some
                    # output.
                    pass
                else:
                    # It did succeed, so we'll stop now and let the caller deal
                    # with it.
                    return (read, data)

                while True:
                    # Keep copying as long as there's more stuff there.
                    try:
                        dirty = read.bio_read(4096)
                    except WantReadError:
                        # Okay, nothing more waiting to be sent.  Stop
                        # processing this send buffer.
                        break
                    else:
                        # Keep track of the fact that someone generated some
                        # output.
                        wrote = True
                        write.bio_write(dirty)



class VersionTests(TestCase):
    """
    Tests for version information exposed by
    L{OpenSSL.SSL.SSLeay_version} and
    L{OpenSSL.SSL.OPENSSL_VERSION_NUMBER}.
    """
    def test_OPENSSL_VERSION_NUMBER(self):
        """
        L{OPENSSL_VERSION_NUMBER} is an integer with status in the low
        byte and the patch, fix, minor, and major versions in the
        nibbles above that.
        """
        self.assertTrue(isinstance(OPENSSL_VERSION_NUMBER, int))


    def test_SSLeay_version(self):
        """
        L{SSLeay_version} takes a version type indicator and returns
        one of a number of version strings based on that indicator.
        """
        versions = {}
        for t in [SSLEAY_VERSION, SSLEAY_CFLAGS, SSLEAY_BUILT_ON,
                  SSLEAY_PLATFORM, SSLEAY_DIR]:
            version = SSLeay_version(t)
            versions[version] = t
            self.assertTrue(isinstance(version, bytes))
        self.assertEqual(len(versions), 5)



class ContextTests(TestCase, _LoopbackMixin):
    """
    Unit tests for L{OpenSSL.SSL.Context}.
    """
    def test_method(self):
        """
        L{Context} can be instantiated with one of L{SSLv2_METHOD},
        L{SSLv3_METHOD}, L{SSLv23_METHOD}, or L{TLSv1_METHOD}.
        """
        for meth in [SSLv3_METHOD, SSLv23_METHOD, TLSv1_METHOD]:
            Context(meth)

        try:
            Context(SSLv2_METHOD)
        except ValueError:
            # Some versions of OpenSSL have SSLv2, some don't.
            # Difficult to say in advance.
            pass

        self.assertRaises(TypeError, Context, "")
        self.assertRaises(ValueError, Context, 10)


    def test_type(self):
        """
        L{Context} and L{ContextType} refer to the same type object and can be
        used to create instances of that type.
        """
        self.assertIdentical(Context, ContextType)
        self.assertConsistentType(Context, 'Context', TLSv1_METHOD)


    def test_use_privatekey(self):
        """
        L{Context.use_privatekey} takes an L{OpenSSL.crypto.PKey} instance.
        """
        key = PKey()
        key.generate_key(TYPE_RSA, 128)
        ctx = Context(TLSv1_METHOD)
        ctx.use_privatekey(key)
        self.assertRaises(TypeError, ctx.use_privatekey, "")


    def test_set_app_data_wrong_args(self):
        """
        L{Context.set_app_data} raises L{TypeError} if called with other than
        one argument.
        """
        context = Context(TLSv1_METHOD)
        self.assertRaises(TypeError, context.set_app_data)
        self.assertRaises(TypeError, context.set_app_data, None, None)


    def test_get_app_data_wrong_args(self):
        """
        L{Context.get_app_data} raises L{TypeError} if called with any
        arguments.
        """
        context = Context(TLSv1_METHOD)
        self.assertRaises(TypeError, context.get_app_data, None)


    def test_app_data(self):
        """
        L{Context.set_app_data} stores an object for later retrieval using
        L{Context.get_app_data}.
        """
        app_data = object()
        context = Context(TLSv1_METHOD)
        context.set_app_data(app_data)
        self.assertIdentical(context.get_app_data(), app_data)


    def test_set_options_wrong_args(self):
        """
        L{Context.set_options} raises L{TypeError} if called with the wrong
        number of arguments or a non-C{int} argument.
        """
        context = Context(TLSv1_METHOD)
        self.assertRaises(TypeError, context.set_options)
        self.assertRaises(TypeError, context.set_options, None)
        self.assertRaises(TypeError, context.set_options, 1, None)


    def test_set_timeout_wrong_args(self):
        """
        L{Context.set_timeout} raises L{TypeError} if called with the wrong
        number of arguments or a non-C{int} argument.
        """
        context = Context(TLSv1_METHOD)
        self.assertRaises(TypeError, context.set_timeout)
        self.assertRaises(TypeError, context.set_timeout, None)
        self.assertRaises(TypeError, context.set_timeout, 1, None)


    def test_get_timeout_wrong_args(self):
        """
        L{Context.get_timeout} raises L{TypeError} if called with any arguments.
        """
        context = Context(TLSv1_METHOD)
        self.assertRaises(TypeError, context.get_timeout, None)


    def test_timeout(self):
        """
        L{Context.set_timeout} sets the session timeout for all connections
        created using the context object.  L{Context.get_timeout} retrieves this
        value.
        """
        context = Context(TLSv1_METHOD)
        context.set_timeout(1234)
        self.assertEquals(context.get_timeout(), 1234)


    def test_set_verify_depth_wrong_args(self):
        """
        L{Context.set_verify_depth} raises L{TypeError} if called with the wrong
        number of arguments or a non-C{int} argument.
        """
        context = Context(TLSv1_METHOD)
        self.assertRaises(TypeError, context.set_verify_depth)
        self.assertRaises(TypeError, context.set_verify_depth, None)
        self.assertRaises(TypeError, context.set_verify_depth, 1, None)


    def test_get_verify_depth_wrong_args(self):
        """
        L{Context.get_verify_depth} raises L{TypeError} if called with any arguments.
        """
        context = Context(TLSv1_METHOD)
        self.assertRaises(TypeError, context.get_verify_depth, None)


    def test_verify_depth(self):
        """
        L{Context.set_verify_depth} sets the number of certificates in a chain
        to follow before giving up.  The value can be retrieved with
        L{Context.get_verify_depth}.
        """
        context = Context(TLSv1_METHOD)
        context.set_verify_depth(11)
        self.assertEquals(context.get_verify_depth(), 11)


    def _write_encrypted_pem(self, passphrase):
        """
        Write a new private key out to a new file, encrypted using the given
        passphrase.  Return the path to the new file.
        """
        key = PKey()
        key.generate_key(TYPE_RSA, 128)
        pemFile = self.mktemp()
        fObj = open(pemFile, 'w')
        pem = dump_privatekey(FILETYPE_PEM, key, "blowfish", passphrase)
        fObj.write(pem.decode('ascii'))
        fObj.close()
        return pemFile


    def test_set_passwd_cb_wrong_args(self):
        """
        L{Context.set_passwd_cb} raises L{TypeError} if called with the
        wrong arguments or with a non-callable first argument.
        """
        context = Context(TLSv1_METHOD)
        self.assertRaises(TypeError, context.set_passwd_cb)
        self.assertRaises(TypeError, context.set_passwd_cb, None)
        self.assertRaises(TypeError, context.set_passwd_cb, lambda: None, None, None)


    def test_set_passwd_cb(self):
        """
        L{Context.set_passwd_cb} accepts a callable which will be invoked when
        a private key is loaded from an encrypted PEM.
        """
        passphrase = b("foobar")
        pemFile = self._write_encrypted_pem(passphrase)
        calledWith = []
        def passphraseCallback(maxlen, verify, extra):
            calledWith.append((maxlen, verify, extra))
            return passphrase
        context = Context(TLSv1_METHOD)
        context.set_passwd_cb(passphraseCallback)
        context.use_privatekey_file(pemFile)
        self.assertTrue(len(calledWith), 1)
        self.assertTrue(isinstance(calledWith[0][0], int))
        self.assertTrue(isinstance(calledWith[0][1], int))
        self.assertEqual(calledWith[0][2], None)


    def test_passwd_callback_exception(self):
        """
        L{Context.use_privatekey_file} propagates any exception raised by the
        passphrase callback.
        """
        pemFile = self._write_encrypted_pem(b("monkeys are nice"))
        def passphraseCallback(maxlen, verify, extra):
            raise RuntimeError("Sorry, I am a fail.")

        context = Context(TLSv1_METHOD)
        context.set_passwd_cb(passphraseCallback)
        self.assertRaises(RuntimeError, context.use_privatekey_file, pemFile)


    def test_passwd_callback_false(self):
        """
        L{Context.use_privatekey_file} raises L{OpenSSL.SSL.Error} if the
        passphrase callback returns a false value.
        """
        pemFile = self._write_encrypted_pem(b("monkeys are nice"))
        def passphraseCallback(maxlen, verify, extra):
            return None

        context = Context(TLSv1_METHOD)
        context.set_passwd_cb(passphraseCallback)
        self.assertRaises(Error, context.use_privatekey_file, pemFile)


    def test_passwd_callback_non_string(self):
        """
        L{Context.use_privatekey_file} raises L{OpenSSL.SSL.Error} if the
        passphrase callback returns a true non-string value.
        """
        pemFile = self._write_encrypted_pem(b("monkeys are nice"))
        def passphraseCallback(maxlen, verify, extra):
            return 10

        context = Context(TLSv1_METHOD)
        context.set_passwd_cb(passphraseCallback)
        self.assertRaises(Error, context.use_privatekey_file, pemFile)


    def test_passwd_callback_too_long(self):
        """
        If the passphrase returned by the passphrase callback returns a string
        longer than the indicated maximum length, it is truncated.
        """
        # A priori knowledge!
        passphrase = b("x") * 1024
        pemFile = self._write_encrypted_pem(passphrase)
        def passphraseCallback(maxlen, verify, extra):
            assert maxlen == 1024
            return passphrase + b("y")

        context = Context(TLSv1_METHOD)
        context.set_passwd_cb(passphraseCallback)
        # This shall succeed because the truncated result is the correct
        # passphrase.
        context.use_privatekey_file(pemFile)


    def test_set_info_callback(self):
        """
        L{Context.set_info_callback} accepts a callable which will be invoked
        when certain information about an SSL connection is available.
        """
        (server, client) = socket_pair()

        clientSSL = Connection(Context(TLSv1_METHOD), client)
        clientSSL.set_connect_state()

        called = []
        def info(conn, where, ret):
            called.append((conn, where, ret))
        context = Context(TLSv1_METHOD)
        context.set_info_callback(info)
        context.use_certificate(
            load_certificate(FILETYPE_PEM, cleartextCertificatePEM))
        context.use_privatekey(
            load_privatekey(FILETYPE_PEM, cleartextPrivateKeyPEM))

        serverSSL = Connection(context, server)
        serverSSL.set_accept_state()

        while not called:
            for ssl in clientSSL, serverSSL:
                try:
                    ssl.do_handshake()
                except WantReadError:
                    pass

        # Kind of lame.  Just make sure it got called somehow.
        self.assertTrue(called)


    def _load_verify_locations_test(self, *args):
        """
        Create a client context which will verify the peer certificate and call
        its C{load_verify_locations} method with C{*args}.  Then connect it to a
        server and ensure that the handshake succeeds.
        """
        (server, client) = socket_pair()

        clientContext = Context(TLSv1_METHOD)
        clientContext.load_verify_locations(*args)
        # Require that the server certificate verify properly or the
        # connection will fail.
        clientContext.set_verify(
            VERIFY_PEER,
            lambda conn, cert, errno, depth, preverify_ok: preverify_ok)

        clientSSL = Connection(clientContext, client)
        clientSSL.set_connect_state()

        serverContext = Context(TLSv1_METHOD)
        serverContext.use_certificate(
            load_certificate(FILETYPE_PEM, cleartextCertificatePEM))
        serverContext.use_privatekey(
            load_privatekey(FILETYPE_PEM, cleartextPrivateKeyPEM))

        serverSSL = Connection(serverContext, server)
        serverSSL.set_accept_state()

        # Without load_verify_locations above, the handshake
        # will fail:
        # Error: [('SSL routines', 'SSL3_GET_SERVER_CERTIFICATE',
        #          'certificate verify failed')]
        handshake(clientSSL, serverSSL)

        cert = clientSSL.get_peer_certificate()
        self.assertEqual(cert.get_subject().CN, 'Testing Root CA')


    def test_load_verify_file(self):
        """
        L{Context.load_verify_locations} accepts a file name and uses the
        certificates within for verification purposes.
        """
        cafile = self.mktemp()
        fObj = open(cafile, 'w')
        fObj.write(cleartextCertificatePEM.decode('ascii'))
        fObj.close()

        self._load_verify_locations_test(cafile)


    def test_load_verify_invalid_file(self):
        """
        L{Context.load_verify_locations} raises L{Error} when passed a
        non-existent cafile.
        """
        clientContext = Context(TLSv1_METHOD)
        self.assertRaises(
            Error, clientContext.load_verify_locations, self.mktemp())


    def test_load_verify_directory(self):
        """
        L{Context.load_verify_locations} accepts a directory name and uses
        the certificates within for verification purposes.
        """
        capath = self.mktemp()
        makedirs(capath)
        # Hash values computed manually with c_rehash to avoid depending on
        # c_rehash in the test suite.  One is from OpenSSL 0.9.8, the other
        # from OpenSSL 1.0.0.
        for name in ['c7adac82.0', 'c3705638.0']:
            cafile = join(capath, name)
            fObj = open(cafile, 'w')
            fObj.write(cleartextCertificatePEM.decode('ascii'))
            fObj.close()

        self._load_verify_locations_test(None, capath)


    def test_load_verify_locations_wrong_args(self):
        """
        L{Context.load_verify_locations} raises L{TypeError} if called with
        the wrong number of arguments or with non-C{str} arguments.
        """
        context = Context(TLSv1_METHOD)
        self.assertRaises(TypeError, context.load_verify_locations)
        self.assertRaises(TypeError, context.load_verify_locations, object())
        self.assertRaises(TypeError, context.load_verify_locations, object(), object())
        self.assertRaises(TypeError, context.load_verify_locations, None, None, None)


    if platform == "win32":
        "set_default_verify_paths appears not to work on Windows.  "
        "See LP#404343 and LP#404344."
    else:
        def test_set_default_verify_paths(self):
            """
            L{Context.set_default_verify_paths} causes the platform-specific CA
            certificate locations to be used for verification purposes.
            """
            # Testing this requires a server with a certificate signed by one of
            # the CAs in the platform CA location.  Getting one of those costs
            # money.  Fortunately (or unfortunately, depending on your
            # perspective), it's easy to think of a public server on the
            # internet which has such a certificate.  Connecting to the network
            # in a unit test is bad, but it's the only way I can think of to
            # really test this. -exarkun

            # Arg, verisign.com doesn't speak TLSv1
            context = Context(SSLv3_METHOD)
            context.set_default_verify_paths()
            context.set_verify(
                VERIFY_PEER,
                lambda conn, cert, errno, depth, preverify_ok: preverify_ok)

            client = socket()
            client.connect(('verisign.com', 443))
            clientSSL = Connection(context, client)
            clientSSL.set_connect_state()
            clientSSL.do_handshake()
            clientSSL.send('GET / HTTP/1.0\r\n\r\n')
            self.assertTrue(clientSSL.recv(1024))


    def test_set_default_verify_paths_signature(self):
        """
        L{Context.set_default_verify_paths} takes no arguments and raises
        L{TypeError} if given any.
        """
        context = Context(TLSv1_METHOD)
        self.assertRaises(TypeError, context.set_default_verify_paths, None)
        self.assertRaises(TypeError, context.set_default_verify_paths, 1)
        self.assertRaises(TypeError, context.set_default_verify_paths, "")


    def test_add_extra_chain_cert_invalid_cert(self):
        """
        L{Context.add_extra_chain_cert} raises L{TypeError} if called with
        other than one argument or if called with an object which is not an
        instance of L{X509}.
        """
        context = Context(TLSv1_METHOD)
        self.assertRaises(TypeError, context.add_extra_chain_cert)
        self.assertRaises(TypeError, context.add_extra_chain_cert, object())
        self.assertRaises(TypeError, context.add_extra_chain_cert, object(), object())


    def _handshake_test(self, serverContext, clientContext):
        """
        Verify that a client and server created with the given contexts can
        successfully handshake and communicate.
        """
        serverSocket, clientSocket = socket_pair()

        server = Connection(serverContext, serverSocket)
        server.set_accept_state()

        client = Connection(clientContext, clientSocket)
        client.set_connect_state()

        # Make them talk to each other.
        # self._interactInMemory(client, server)
        for i in range(3):
            for s in [client, server]:
                try:
                    s.do_handshake()
                except WantReadError:
                    pass


    def test_add_extra_chain_cert(self):
        """
        L{Context.add_extra_chain_cert} accepts an L{X509} instance to add to
        the certificate chain.

        See L{_create_certificate_chain} for the details of the certificate
        chain tested.

        The chain is tested by starting a server with scert and connecting
        to it with a client which trusts cacert and requires verification to
        succeed.
        """
        chain = _create_certificate_chain()
        [(cakey, cacert), (ikey, icert), (skey, scert)] = chain

        # Dump the CA certificate to a file because that's the only way to load
        # it as a trusted CA in the client context.
        for cert, name in [(cacert, 'ca.pem'), (icert, 'i.pem'), (scert, 's.pem')]:
            fObj = open(name, 'w')
            fObj.write(dump_certificate(FILETYPE_PEM, cert).decode('ascii'))
            fObj.close()

        for key, name in [(cakey, 'ca.key'), (ikey, 'i.key'), (skey, 's.key')]:
            fObj = open(name, 'w')
            fObj.write(dump_privatekey(FILETYPE_PEM, key).decode('ascii'))
            fObj.close()

        # Create the server context
        serverContext = Context(TLSv1_METHOD)
        serverContext.use_privatekey(skey)
        serverContext.use_certificate(scert)
        # The client already has cacert, we only need to give them icert.
        serverContext.add_extra_chain_cert(icert)

        # Create the client
        clientContext = Context(TLSv1_METHOD)
        clientContext.set_verify(
            VERIFY_PEER | VERIFY_FAIL_IF_NO_PEER_CERT, verify_cb)
        clientContext.load_verify_locations('ca.pem')

        # Try it out.
        self._handshake_test(serverContext, clientContext)


    def test_use_certificate_chain_file(self):
        """
        L{Context.use_certificate_chain_file} reads a certificate chain from
        the specified file.

        The chain is tested by starting a server with scert and connecting
        to it with a client which trusts cacert and requires verification to
        succeed.
        """
        chain = _create_certificate_chain()
        [(cakey, cacert), (ikey, icert), (skey, scert)] = chain

        # Write out the chain file.
        chainFile = self.mktemp()
        fObj = open(chainFile, 'w')
        # Most specific to least general.
        fObj.write(dump_certificate(FILETYPE_PEM, scert).decode('ascii'))
        fObj.write(dump_certificate(FILETYPE_PEM, icert).decode('ascii'))
        fObj.write(dump_certificate(FILETYPE_PEM, cacert).decode('ascii'))
        fObj.close()

        serverContext = Context(TLSv1_METHOD)
        serverContext.use_certificate_chain_file(chainFile)
        serverContext.use_privatekey(skey)

        fObj = open('ca.pem', 'w')
        fObj.write(dump_certificate(FILETYPE_PEM, cacert).decode('ascii'))
        fObj.close()

        clientContext = Context(TLSv1_METHOD)
        clientContext.set_verify(
            VERIFY_PEER | VERIFY_FAIL_IF_NO_PEER_CERT, verify_cb)
        clientContext.load_verify_locations('ca.pem')

        self._handshake_test(serverContext, clientContext)

    # XXX load_client_ca
    # XXX set_session_id

    def test_get_verify_mode_wrong_args(self):
        """
        L{Context.get_verify_mode} raises L{TypeError} if called with any
        arguments.
        """
        context = Context(TLSv1_METHOD)
        self.assertRaises(TypeError, context.get_verify_mode, None)


    def test_get_verify_mode(self):
        """
        L{Context.get_verify_mode} returns the verify mode flags previously
        passed to L{Context.set_verify}.
        """
        context = Context(TLSv1_METHOD)
        self.assertEquals(context.get_verify_mode(), 0)
        context.set_verify(
            VERIFY_PEER | VERIFY_CLIENT_ONCE, lambda *args: None)
        self.assertEquals(
            context.get_verify_mode(), VERIFY_PEER | VERIFY_CLIENT_ONCE)


    def test_load_tmp_dh_wrong_args(self):
        """
        L{Context.load_tmp_dh} raises L{TypeError} if called with the wrong
        number of arguments or with a non-C{str} argument.
        """
        context = Context(TLSv1_METHOD)
        self.assertRaises(TypeError, context.load_tmp_dh)
        self.assertRaises(TypeError, context.load_tmp_dh, "foo", None)
        self.assertRaises(TypeError, context.load_tmp_dh, object())


    def test_load_tmp_dh_missing_file(self):
        """
        L{Context.load_tmp_dh} raises L{OpenSSL.SSL.Error} if the specified file
        does not exist.
        """
        context = Context(TLSv1_METHOD)
        self.assertRaises(Error, context.load_tmp_dh, "hello")


    def test_load_tmp_dh(self):
        """
        L{Context.load_tmp_dh} loads Diffie-Hellman parameters from the
        specified file.
        """
        context = Context(TLSv1_METHOD)
        dhfilename = self.mktemp()
        dhfile = open(dhfilename, "w")
        dhfile.write(dhparam)
        dhfile.close()
        context.load_tmp_dh(dhfilename)
        # XXX What should I assert here? -exarkun


    def test_set_cipher_list(self):
        """
        L{Context.set_cipher_list} accepts a C{str} naming the ciphers which
        connections created with the context object will be able to choose from.
        """
        context = Context(TLSv1_METHOD)
        context.set_cipher_list("hello world:EXP-RC4-MD5")
        conn = Connection(context, None)
        self.assertEquals(conn.get_cipher_list(), ["EXP-RC4-MD5"])



class ServerNameCallbackTests(TestCase, _LoopbackMixin):
    """
    Tests for L{Context.set_tlsext_servername_callback} and its interaction with
    L{Connection}.
    """
    def test_wrong_args(self):
        """
        L{Context.set_tlsext_servername_callback} raises L{TypeError} if called
        with other than one argument.
        """
        context = Context(TLSv1_METHOD)
        self.assertRaises(TypeError, context.set_tlsext_servername_callback)
        self.assertRaises(
            TypeError, context.set_tlsext_servername_callback, 1, 2)

    def test_old_callback_forgotten(self):
        """
        If L{Context.set_tlsext_servername_callback} is used to specify a new
        callback, the one it replaces is dereferenced.
        """
        def callback(connection):
            pass

        def replacement(connection):
            pass

        context = Context(TLSv1_METHOD)
        context.set_tlsext_servername_callback(callback)

        tracker = ref(callback)
        del callback

        context.set_tlsext_servername_callback(replacement)
        collect()
        self.assertIdentical(None, tracker())


    def test_no_servername(self):
        """
        When a client specifies no server name, the callback passed to
        L{Context.set_tlsext_servername_callback} is invoked and the result of
        L{Connection.get_servername} is C{None}.
        """
        args = []
        def servername(conn):
            args.append((conn, conn.get_servername()))
        context = Context(TLSv1_METHOD)
        context.set_tlsext_servername_callback(servername)

        # Lose our reference to it.  The Context is responsible for keeping it
        # alive now.
        del servername
        collect()

        # Necessary to actually accept the connection
        context.use_privatekey(load_privatekey(FILETYPE_PEM, server_key_pem))
        context.use_certificate(load_certificate(FILETYPE_PEM, server_cert_pem))

        # Do a little connection to trigger the logic
        server = Connection(context, None)
        server.set_accept_state()

        client = Connection(Context(TLSv1_METHOD), None)
        client.set_connect_state()

        self._interactInMemory(server, client)

        self.assertEqual([(server, None)], args)


    def test_servername(self):
        """
        When a client specifies a server name in its hello message, the callback
        passed to L{Contexts.set_tlsext_servername_callback} is invoked and the
        result of L{Connection.get_servername} is that server name.
        """
        args = []
        def servername(conn):
            args.append((conn, conn.get_servername()))
        context = Context(TLSv1_METHOD)
        context.set_tlsext_servername_callback(servername)

        # Necessary to actually accept the connection
        context.use_privatekey(load_privatekey(FILETYPE_PEM, server_key_pem))
        context.use_certificate(load_certificate(FILETYPE_PEM, server_cert_pem))

        # Do a little connection to trigger the logic
        server = Connection(context, None)
        server.set_accept_state()

        client = Connection(Context(TLSv1_METHOD), None)
        client.set_connect_state()
        client.set_tlsext_host_name(b("foo1.example.com"))

        self._interactInMemory(server, client)

        self.assertEqual([(server, b("foo1.example.com"))], args)



class ConnectionTests(TestCase, _LoopbackMixin):
    """
    Unit tests for L{OpenSSL.SSL.Connection}.
    """
    # XXX want_write
    # XXX want_read
    # XXX get_peer_certificate -> None
    # XXX sock_shutdown
    # XXX master_key -> TypeError
    # XXX server_random -> TypeError
    # XXX state_string
    # XXX connect -> TypeError
    # XXX connect_ex -> TypeError
    # XXX set_connect_state -> TypeError
    # XXX set_accept_state -> TypeError
    # XXX renegotiate_pending
    # XXX do_handshake -> TypeError
    # XXX bio_read -> TypeError
    # XXX recv -> TypeError
    # XXX send -> TypeError
    # XXX bio_write -> TypeError

    def test_type(self):
        """
        L{Connection} and L{ConnectionType} refer to the same type object and
        can be used to create instances of that type.
        """
        self.assertIdentical(Connection, ConnectionType)
        ctx = Context(TLSv1_METHOD)
        self.assertConsistentType(Connection, 'Connection', ctx, None)


    def test_get_context(self):
        """
        L{Connection.get_context} returns the L{Context} instance used to
        construct the L{Connection} instance.
        """
        context = Context(TLSv1_METHOD)
        connection = Connection(context, None)
        self.assertIdentical(connection.get_context(), context)


    def test_get_context_wrong_args(self):
        """
        L{Connection.get_context} raises L{TypeError} if called with any
        arguments.
        """
        connection = Connection(Context(TLSv1_METHOD), None)
        self.assertRaises(TypeError, connection.get_context, None)


    def test_set_context_wrong_args(self):
        """
        L{Connection.set_context} raises L{TypeError} if called with a
        non-L{Context} instance argument or with any number of arguments other
        than 1.
        """
        ctx = Context(TLSv1_METHOD)
        connection = Connection(ctx, None)
        self.assertRaises(TypeError, connection.set_context)
        self.assertRaises(TypeError, connection.set_context, object())
        self.assertRaises(TypeError, connection.set_context, "hello")
        self.assertRaises(TypeError, connection.set_context, 1)
        self.assertRaises(TypeError, connection.set_context, 1, 2)
        self.assertRaises(
            TypeError, connection.set_context, Context(TLSv1_METHOD), 2)
        self.assertIdentical(ctx, connection.get_context())


    def test_set_context(self):
        """
        L{Connection.set_context} specifies a new L{Context} instance to be used
        for the connection.
        """
        original = Context(SSLv23_METHOD)
        replacement = Context(TLSv1_METHOD)
        connection = Connection(original, None)
        connection.set_context(replacement)
        self.assertIdentical(replacement, connection.get_context())
        # Lose our references to the contexts, just in case the Connection isn't
        # properly managing its own contributions to their reference counts.
        del original, replacement
        collect()


    def test_set_tlsext_host_name_wrong_args(self):
        """
        If L{Connection.set_tlsext_host_name} is called with a non-byte string
        argument or a byte string with an embedded NUL or other than one
        argument, L{TypeError} is raised.
        """
        conn = Connection(Context(TLSv1_METHOD), None)
        self.assertRaises(TypeError, conn.set_tlsext_host_name)
        self.assertRaises(TypeError, conn.set_tlsext_host_name, object())
        self.assertRaises(TypeError, conn.set_tlsext_host_name, 123, 456)
        self.assertRaises(
            TypeError, conn.set_tlsext_host_name, b("with\0null"))

        if version_info >= (3,):
            # On Python 3.x, don't accidentally implicitly convert from text.
            self.assertRaises(
                TypeError,
                conn.set_tlsext_host_name, b("example.com").decode("ascii"))


    def test_get_servername_wrong_args(self):
        """
        L{Connection.get_servername} raises L{TypeError} if called with any
        arguments.
        """
        connection = Connection(Context(TLSv1_METHOD), None)
        self.assertRaises(TypeError, connection.get_servername, object())
        self.assertRaises(TypeError, connection.get_servername, 1)
        self.assertRaises(TypeError, connection.get_servername, "hello")


    def test_pending(self):
        """
        L{Connection.pending} returns the number of bytes available for
        immediate read.
        """
        connection = Connection(Context(TLSv1_METHOD), None)
        self.assertEquals(connection.pending(), 0)


    def test_pending_wrong_args(self):
        """
        L{Connection.pending} raises L{TypeError} if called with any arguments.
        """
        connection = Connection(Context(TLSv1_METHOD), None)
        self.assertRaises(TypeError, connection.pending, None)


    def test_connect_wrong_args(self):
        """
        L{Connection.connect} raises L{TypeError} if called with a non-address
        argument or with the wrong number of arguments.
        """
        connection = Connection(Context(TLSv1_METHOD), socket())
        self.assertRaises(TypeError, connection.connect, None)
        self.assertRaises(TypeError, connection.connect)
        self.assertRaises(TypeError, connection.connect, ("127.0.0.1", 1), None)


    def test_connect_refused(self):
        """
        L{Connection.connect} raises L{socket.error} if the underlying socket
        connect method raises it.
        """
        client = socket()
        context = Context(TLSv1_METHOD)
        clientSSL = Connection(context, client)
        exc = self.assertRaises(error, clientSSL.connect, ("127.0.0.1", 1))
        self.assertEquals(exc.args[0], ECONNREFUSED)


    def test_connect(self):
        """
        L{Connection.connect} establishes a connection to the specified address.
        """
        port = socket()
        port.bind(('', 0))
        port.listen(3)

        clientSSL = Connection(Context(TLSv1_METHOD), socket())
        clientSSL.connect(('127.0.0.1', port.getsockname()[1]))
        # XXX An assertion?  Or something?


    if platform == "darwin":
        "connect_ex sometimes causes a kernel panic on OS X 10.6.4"
    else:
        def test_connect_ex(self):
            """
            If there is a connection error, L{Connection.connect_ex} returns the
            errno instead of raising an exception.
            """
            port = socket()
            port.bind(('', 0))
            port.listen(3)

            clientSSL = Connection(Context(TLSv1_METHOD), socket())
            clientSSL.setblocking(False)
            result = clientSSL.connect_ex(port.getsockname())
            expected = (EINPROGRESS, EWOULDBLOCK)
            self.assertTrue(
                    result in expected, "%r not in %r" % (result, expected))


    def test_accept_wrong_args(self):
        """
        L{Connection.accept} raises L{TypeError} if called with any arguments.
        """
        connection = Connection(Context(TLSv1_METHOD), socket())
        self.assertRaises(TypeError, connection.accept, None)


    def test_accept(self):
        """
        L{Connection.accept} accepts a pending connection attempt and returns a
        tuple of a new L{Connection} (the accepted client) and the address the
        connection originated from.
        """
        ctx = Context(TLSv1_METHOD)
        ctx.use_privatekey(load_privatekey(FILETYPE_PEM, server_key_pem))
        ctx.use_certificate(load_certificate(FILETYPE_PEM, server_cert_pem))
        port = socket()
        portSSL = Connection(ctx, port)
        portSSL.bind(('', 0))
        portSSL.listen(3)

        clientSSL = Connection(Context(TLSv1_METHOD), socket())

        # Calling portSSL.getsockname() here to get the server IP address sounds
        # great, but frequently fails on Windows.
        clientSSL.connect(('127.0.0.1', portSSL.getsockname()[1]))

        serverSSL, address = portSSL.accept()

        self.assertTrue(isinstance(serverSSL, Connection))
        self.assertIdentical(serverSSL.get_context(), ctx)
        self.assertEquals(address, clientSSL.getsockname())


    def test_shutdown_wrong_args(self):
        """
        L{Connection.shutdown} raises L{TypeError} if called with the wrong
        number of arguments or with arguments other than integers.
        """
        connection = Connection(Context(TLSv1_METHOD), None)
        self.assertRaises(TypeError, connection.shutdown, None)
        self.assertRaises(TypeError, connection.get_shutdown, None)
        self.assertRaises(TypeError, connection.set_shutdown)
        self.assertRaises(TypeError, connection.set_shutdown, None)
        self.assertRaises(TypeError, connection.set_shutdown, 0, 1)


    def test_shutdown(self):
        """
        L{Connection.shutdown} performs an SSL-level connection shutdown.
        """
        server, client = self._loopback()
        self.assertFalse(server.shutdown())
        self.assertEquals(server.get_shutdown(), SENT_SHUTDOWN)
        self.assertRaises(ZeroReturnError, client.recv, 1024)
        self.assertEquals(client.get_shutdown(), RECEIVED_SHUTDOWN)
        client.shutdown()
        self.assertEquals(client.get_shutdown(), SENT_SHUTDOWN|RECEIVED_SHUTDOWN)
        self.assertRaises(ZeroReturnError, server.recv, 1024)
        self.assertEquals(server.get_shutdown(), SENT_SHUTDOWN|RECEIVED_SHUTDOWN)


    def test_set_shutdown(self):
        """
        L{Connection.set_shutdown} sets the state of the SSL connection shutdown
        process.
        """
        connection = Connection(Context(TLSv1_METHOD), socket())
        connection.set_shutdown(RECEIVED_SHUTDOWN)
        self.assertEquals(connection.get_shutdown(), RECEIVED_SHUTDOWN)


    def test_app_data_wrong_args(self):
        """
        L{Connection.set_app_data} raises L{TypeError} if called with other than
        one argument.  L{Connection.get_app_data} raises L{TypeError} if called
        with any arguments.
        """
        conn = Connection(Context(TLSv1_METHOD), None)
        self.assertRaises(TypeError, conn.get_app_data, None)
        self.assertRaises(TypeError, conn.set_app_data)
        self.assertRaises(TypeError, conn.set_app_data, None, None)


    def test_app_data(self):
        """
        Any object can be set as app data by passing it to
        L{Connection.set_app_data} and later retrieved with
        L{Connection.get_app_data}.
        """
        conn = Connection(Context(TLSv1_METHOD), None)
        app_data = object()
        conn.set_app_data(app_data)
        self.assertIdentical(conn.get_app_data(), app_data)


    def test_makefile(self):
        """
        L{Connection.makefile} is not implemented and calling that method raises
        L{NotImplementedError}.
        """
        conn = Connection(Context(TLSv1_METHOD), None)
        self.assertRaises(NotImplementedError, conn.makefile)


    def test_get_peer_cert_chain_wrong_args(self):
        """
        L{Connection.get_peer_cert_chain} raises L{TypeError} if called with any
        arguments.
        """
        conn = Connection(Context(TLSv1_METHOD), None)
        self.assertRaises(TypeError, conn.get_peer_cert_chain, 1)
        self.assertRaises(TypeError, conn.get_peer_cert_chain, "foo")
        self.assertRaises(TypeError, conn.get_peer_cert_chain, object())
        self.assertRaises(TypeError, conn.get_peer_cert_chain, [])


    def test_get_peer_cert_chain(self):
        """
        L{Connection.get_peer_cert_chain} returns a list of certificates which
        the connected server returned for the certification verification.
        """
        chain = _create_certificate_chain()
        [(cakey, cacert), (ikey, icert), (skey, scert)] = chain

        serverContext = Context(TLSv1_METHOD)
        serverContext.use_privatekey(skey)
        serverContext.use_certificate(scert)
        serverContext.add_extra_chain_cert(icert)
        serverContext.add_extra_chain_cert(cacert)
        server = Connection(serverContext, None)
        server.set_accept_state()

        # Create the client
        clientContext = Context(TLSv1_METHOD)
        clientContext.set_verify(VERIFY_NONE, verify_cb)
        client = Connection(clientContext, None)
        client.set_connect_state()

        self._interactInMemory(client, server)

        chain = client.get_peer_cert_chain()
        self.assertEqual(len(chain), 3)
        self.assertEqual(
            "Server Certificate", chain[0].get_subject().CN)
        self.assertEqual(
            "Intermediate Certificate", chain[1].get_subject().CN)
        self.assertEqual(
            "Authority Certificate", chain[2].get_subject().CN)


    def test_get_peer_cert_chain_none(self):
        """
        L{Connection.get_peer_cert_chain} returns C{None} if the peer sends no
        certificate chain.
        """
        ctx = Context(TLSv1_METHOD)
        ctx.use_privatekey(load_privatekey(FILETYPE_PEM, server_key_pem))
        ctx.use_certificate(load_certificate(FILETYPE_PEM, server_cert_pem))
        server = Connection(ctx, None)
        server.set_accept_state()
        client = Connection(Context(TLSv1_METHOD), None)
        client.set_connect_state()
        self._interactInMemory(client, server)
        self.assertIdentical(None, server.get_peer_cert_chain())



class ConnectionGetCipherListTests(TestCase):
    """
    Tests for L{Connection.get_cipher_list}.
    """
    def test_wrong_args(self):
        """
        L{Connection.get_cipher_list} raises L{TypeError} if called with any
        arguments.
        """
        connection = Connection(Context(TLSv1_METHOD), None)
        self.assertRaises(TypeError, connection.get_cipher_list, None)


    def test_result(self):
        """
        L{Connection.get_cipher_list} returns a C{list} of C{str} giving the
        names of the ciphers which might be used.
        """
        connection = Connection(Context(TLSv1_METHOD), None)
        ciphers = connection.get_cipher_list()
        self.assertTrue(isinstance(ciphers, list))
        for cipher in ciphers:
            self.assertTrue(isinstance(cipher, str))



class ConnectionSendTests(TestCase, _LoopbackMixin):
    """
    Tests for L{Connection.send}
    """
    def test_wrong_args(self):
        """
        When called with arguments other than a single string,
        L{Connection.send} raises L{TypeError}.
        """
        connection = Connection(Context(TLSv1_METHOD), None)
        self.assertRaises(TypeError, connection.send)
        self.assertRaises(TypeError, connection.send, object())
        self.assertRaises(TypeError, connection.send, "foo", "bar")


    def test_short_bytes(self):
        """
        When passed a short byte string, L{Connection.send} transmits all of it
        and returns the number of bytes sent.
        """
        server, client = self._loopback()
        count = server.send(b('xy'))
        self.assertEquals(count, 2)
        self.assertEquals(client.recv(2), b('xy'))

    try:
        memoryview
    except NameError:
        "cannot test sending memoryview without memoryview"
    else:
        def test_short_memoryview(self):
            """
            When passed a memoryview onto a small number of bytes,
            L{Connection.send} transmits all of them and returns the number of
            bytes sent.
            """
            server, client = self._loopback()
            count = server.send(memoryview(b('xy')))
            self.assertEquals(count, 2)
            self.assertEquals(client.recv(2), b('xy'))



class ConnectionSendallTests(TestCase, _LoopbackMixin):
    """
    Tests for L{Connection.sendall}.
    """
    def test_wrong_args(self):
        """
        When called with arguments other than a single string,
        L{Connection.sendall} raises L{TypeError}.
        """
        connection = Connection(Context(TLSv1_METHOD), None)
        self.assertRaises(TypeError, connection.sendall)
        self.assertRaises(TypeError, connection.sendall, object())
        self.assertRaises(TypeError, connection.sendall, "foo", "bar")


    def test_short(self):
        """
        L{Connection.sendall} transmits all of the bytes in the string passed to
        it.
        """
        server, client = self._loopback()
        server.sendall(b('x'))
        self.assertEquals(client.recv(1), b('x'))


    try:
        memoryview
    except NameError:
        "cannot test sending memoryview without memoryview"
    else:
        def test_short_memoryview(self):
            """
            When passed a memoryview onto a small number of bytes,
            L{Connection.sendall} transmits all of them.
            """
            server, client = self._loopback()
            server.sendall(memoryview(b('x')))
            self.assertEquals(client.recv(1), b('x'))


    def test_long(self):
        """
        L{Connection.sendall} transmits all of the bytes in the string passed to
        it even if this requires multiple calls of an underlying write function.
        """
        server, client = self._loopback()
        # Should be enough, underlying SSL_write should only do 16k at a time.
        # On Windows, after 32k of bytes the write will block (forever - because
        # no one is yet reading).
        message = b('x') * (1024 * 32 - 1) + b('y')
        server.sendall(message)
        accum = []
        received = 0
        while received < len(message):
            data = client.recv(1024)
            accum.append(data)
            received += len(data)
        self.assertEquals(message, b('').join(accum))


    def test_closed(self):
        """
        If the underlying socket is closed, L{Connection.sendall} propagates the
        write error from the low level write call.
        """
        server, client = self._loopback()
        server.sock_shutdown(2)
        self.assertRaises(SysCallError, server.sendall, "hello, world")



class ConnectionRenegotiateTests(TestCase, _LoopbackMixin):
    """
    Tests for SSL renegotiation APIs.
    """
    def test_renegotiate_wrong_args(self):
        """
        L{Connection.renegotiate} raises L{TypeError} if called with any
        arguments.
        """
        connection = Connection(Context(TLSv1_METHOD), None)
        self.assertRaises(TypeError, connection.renegotiate, None)


    def test_total_renegotiations_wrong_args(self):
        """
        L{Connection.total_renegotiations} raises L{TypeError} if called with
        any arguments.
        """
        connection = Connection(Context(TLSv1_METHOD), None)
        self.assertRaises(TypeError, connection.total_renegotiations, None)


    def test_total_renegotiations(self):
        """
        L{Connection.total_renegotiations} returns C{0} before any
        renegotiations have happened.
        """
        connection = Connection(Context(TLSv1_METHOD), None)
        self.assertEquals(connection.total_renegotiations(), 0)


#     def test_renegotiate(self):
#         """
#         """
#         server, client = self._loopback()

#         server.send("hello world")
#         self.assertEquals(client.recv(len("hello world")), "hello world")

#         self.assertEquals(server.total_renegotiations(), 0)
#         self.assertTrue(server.renegotiate())

#         server.setblocking(False)
#         client.setblocking(False)
#         while server.renegotiate_pending():
#             client.do_handshake()
#             server.do_handshake()

#         self.assertEquals(server.total_renegotiations(), 1)




class ErrorTests(TestCase):
    """
    Unit tests for L{OpenSSL.SSL.Error}.
    """
    def test_type(self):
        """
        L{Error} is an exception type.
        """
        self.assertTrue(issubclass(Error, Exception))
        self.assertEqual(Error.__name__, 'Error')



class ConstantsTests(TestCase):
    """
    Tests for the values of constants exposed in L{OpenSSL.SSL}.

    These are values defined by OpenSSL intended only to be used as flags to
    OpenSSL APIs.  The only assertions it seems can be made about them is
    their values.
    """
    # unittest.TestCase has no skip mechanism
    if OP_NO_QUERY_MTU is not None:
        def test_op_no_query_mtu(self):
            """
            The value of L{OpenSSL.SSL.OP_NO_QUERY_MTU} is 0x1000, the value of
            I{SSL_OP_NO_QUERY_MTU} defined by I{openssl/ssl.h}.
            """
            self.assertEqual(OP_NO_QUERY_MTU, 0x1000)
    else:
        "OP_NO_QUERY_MTU unavailable - OpenSSL version may be too old"


    if OP_COOKIE_EXCHANGE is not None:
        def test_op_cookie_exchange(self):
            """
            The value of L{OpenSSL.SSL.OP_COOKIE_EXCHANGE} is 0x2000, the value
            of I{SSL_OP_COOKIE_EXCHANGE} defined by I{openssl/ssl.h}.
            """
            self.assertEqual(OP_COOKIE_EXCHANGE, 0x2000)
    else:
        "OP_COOKIE_EXCHANGE unavailable - OpenSSL version may be too old"


    if OP_NO_TICKET is not None:
        def test_op_no_ticket(self):
            """
            The value of L{OpenSSL.SSL.OP_NO_TICKET} is 0x4000, the value of
            I{SSL_OP_NO_TICKET} defined by I{openssl/ssl.h}.
            """
            self.assertEqual(OP_NO_TICKET, 0x4000)
    else:
        "OP_NO_TICKET unavailable - OpenSSL version may be too old"



class MemoryBIOTests(TestCase, _LoopbackMixin):
    """
    Tests for L{OpenSSL.SSL.Connection} using a memory BIO.
    """
    def _server(self, sock):
        """
        Create a new server-side SSL L{Connection} object wrapped around
        C{sock}.
        """
        # Create the server side Connection.  This is mostly setup boilerplate
        # - use TLSv1, use a particular certificate, etc.
        server_ctx = Context(TLSv1_METHOD)
        server_ctx.set_options(OP_NO_SSLv2 | OP_NO_SSLv3 | OP_SINGLE_DH_USE )
        server_ctx.set_verify(VERIFY_PEER|VERIFY_FAIL_IF_NO_PEER_CERT|VERIFY_CLIENT_ONCE, verify_cb)
        server_store = server_ctx.get_cert_store()
        server_ctx.use_privatekey(load_privatekey(FILETYPE_PEM, server_key_pem))
        server_ctx.use_certificate(load_certificate(FILETYPE_PEM, server_cert_pem))
        server_ctx.check_privatekey()
        server_store.add_cert(load_certificate(FILETYPE_PEM, root_cert_pem))
        # Here the Connection is actually created.  If None is passed as the 2nd
        # parameter, it indicates a memory BIO should be created.
        server_conn = Connection(server_ctx, sock)
        server_conn.set_accept_state()
        return server_conn


    def _client(self, sock):
        """
        Create a new client-side SSL L{Connection} object wrapped around
        C{sock}.
        """
        # Now create the client side Connection.  Similar boilerplate to the
        # above.
        client_ctx = Context(TLSv1_METHOD)
        client_ctx.set_options(OP_NO_SSLv2 | OP_NO_SSLv3 | OP_SINGLE_DH_USE )
        client_ctx.set_verify(VERIFY_PEER|VERIFY_FAIL_IF_NO_PEER_CERT|VERIFY_CLIENT_ONCE, verify_cb)
        client_store = client_ctx.get_cert_store()
        client_ctx.use_privatekey(load_privatekey(FILETYPE_PEM, client_key_pem))
        client_ctx.use_certificate(load_certificate(FILETYPE_PEM, client_cert_pem))
        client_ctx.check_privatekey()
        client_store.add_cert(load_certificate(FILETYPE_PEM, root_cert_pem))
        client_conn = Connection(client_ctx, sock)
        client_conn.set_connect_state()
        return client_conn


    def test_memoryConnect(self):
        """
        Two L{Connection}s which use memory BIOs can be manually connected by
        reading from the output of each and writing those bytes to the input of
        the other and in this way establish a connection and exchange
        application-level bytes with each other.
        """
        server_conn = self._server(None)
        client_conn = self._client(None)

        # There should be no key or nonces yet.
        self.assertIdentical(server_conn.master_key(), None)
        self.assertIdentical(server_conn.client_random(), None)
        self.assertIdentical(server_conn.server_random(), None)

        # First, the handshake needs to happen.  We'll deliver bytes back and
        # forth between the client and server until neither of them feels like
        # speaking any more.
        self.assertIdentical(
            self._interactInMemory(client_conn, server_conn), None)

        # Now that the handshake is done, there should be a key and nonces.
        self.assertNotIdentical(server_conn.master_key(), None)
        self.assertNotIdentical(server_conn.client_random(), None)
        self.assertNotIdentical(server_conn.server_random(), None)
        self.assertEquals(server_conn.client_random(), client_conn.client_random())
        self.assertEquals(server_conn.server_random(), client_conn.server_random())
        self.assertNotEquals(server_conn.client_random(), server_conn.server_random())
        self.assertNotEquals(client_conn.client_random(), client_conn.server_random())

        # Here are the bytes we'll try to send.
        important_message = b('One if by land, two if by sea.')

        server_conn.write(important_message)
        self.assertEquals(
            self._interactInMemory(client_conn, server_conn),
            (client_conn, important_message))

        client_conn.write(important_message[::-1])
        self.assertEquals(
            self._interactInMemory(client_conn, server_conn),
            (server_conn, important_message[::-1]))


    def test_socketConnect(self):
        """
        Just like L{test_memoryConnect} but with an actual socket.

        This is primarily to rule out the memory BIO code as the source of
        any problems encountered while passing data over a L{Connection} (if
        this test fails, there must be a problem outside the memory BIO
        code, as no memory BIO is involved here).  Even though this isn't a
        memory BIO test, it's convenient to have it here.
        """
        server_conn, client_conn = self._loopback()

        important_message = b("Help me Obi Wan Kenobi, you're my only hope.")
        client_conn.send(important_message)
        msg = server_conn.recv(1024)
        self.assertEqual(msg, important_message)

        # Again in the other direction, just for fun.
        important_message = important_message[::-1]
        server_conn.send(important_message)
        msg = client_conn.recv(1024)
        self.assertEqual(msg, important_message)


    def test_socketOverridesMemory(self):
        """
        Test that L{OpenSSL.SSL.bio_read} and L{OpenSSL.SSL.bio_write} don't
        work on L{OpenSSL.SSL.Connection}() that use sockets.
        """
        context = Context(SSLv3_METHOD)
        client = socket()
        clientSSL = Connection(context, client)
        self.assertRaises( TypeError, clientSSL.bio_read, 100)
        self.assertRaises( TypeError, clientSSL.bio_write, "foo")
        self.assertRaises( TypeError, clientSSL.bio_shutdown )


    def test_outgoingOverflow(self):
        """
        If more bytes than can be written to the memory BIO are passed to
        L{Connection.send} at once, the number of bytes which were written is
        returned and that many bytes from the beginning of the input can be
        read from the other end of the connection.
        """
        server = self._server(None)
        client = self._client(None)

        self._interactInMemory(client, server)

        size = 2 ** 15
        sent = client.send("x" * size)
        # Sanity check.  We're trying to test what happens when the entire
        # input can't be sent.  If the entire input was sent, this test is
        # meaningless.
        self.assertTrue(sent < size)

        receiver, received = self._interactInMemory(client, server)
        self.assertIdentical(receiver, server)

        # We can rely on all of these bytes being received at once because
        # _loopback passes 2 ** 16 to recv - more than 2 ** 15.
        self.assertEquals(len(received), sent)


    def test_shutdown(self):
        """
        L{Connection.bio_shutdown} signals the end of the data stream from
        which the L{Connection} reads.
        """
        server = self._server(None)
        server.bio_shutdown()
        e = self.assertRaises(Error, server.recv, 1024)
        # We don't want WantReadError or ZeroReturnError or anything - it's a
        # handshake failure.
        self.assertEquals(e.__class__, Error)


    def _check_client_ca_list(self, func):
        """
        Verify the return value of the C{get_client_ca_list} method for server and client connections.

        @param func: A function which will be called with the server context
            before the client and server are connected to each other.  This
            function should specify a list of CAs for the server to send to the
            client and return that same list.  The list will be used to verify
            that C{get_client_ca_list} returns the proper value at various
            times.
        """
        server = self._server(None)
        client = self._client(None)
        self.assertEqual(client.get_client_ca_list(), [])
        self.assertEqual(server.get_client_ca_list(), [])
        ctx = server.get_context()
        expected = func(ctx)
        self.assertEqual(client.get_client_ca_list(), [])
        self.assertEqual(server.get_client_ca_list(), expected)
        self._interactInMemory(client, server)
        self.assertEqual(client.get_client_ca_list(), expected)
        self.assertEqual(server.get_client_ca_list(), expected)


    def test_set_client_ca_list_errors(self):
        """
        L{Context.set_client_ca_list} raises a L{TypeError} if called with a
        non-list or a list that contains objects other than X509Names.
        """
        ctx = Context(TLSv1_METHOD)
        self.assertRaises(TypeError, ctx.set_client_ca_list, "spam")
        self.assertRaises(TypeError, ctx.set_client_ca_list, ["spam"])
        self.assertIdentical(ctx.set_client_ca_list([]), None)


    def test_set_empty_ca_list(self):
        """
        If passed an empty list, L{Context.set_client_ca_list} configures the
        context to send no CA names to the client and, on both the server and
        client sides, L{Connection.get_client_ca_list} returns an empty list
        after the connection is set up.
        """
        def no_ca(ctx):
            ctx.set_client_ca_list([])
            return []
        self._check_client_ca_list(no_ca)


    def test_set_one_ca_list(self):
        """
        If passed a list containing a single X509Name,
        L{Context.set_client_ca_list} configures the context to send that CA
        name to the client and, on both the server and client sides,
        L{Connection.get_client_ca_list} returns a list containing that
        X509Name after the connection is set up.
        """
        cacert = load_certificate(FILETYPE_PEM, root_cert_pem)
        cadesc = cacert.get_subject()
        def single_ca(ctx):
            ctx.set_client_ca_list([cadesc])
            return [cadesc]
        self._check_client_ca_list(single_ca)


    def test_set_multiple_ca_list(self):
        """
        If passed a list containing multiple X509Name objects,
        L{Context.set_client_ca_list} configures the context to send those CA
        names to the client and, on both the server and client sides,
        L{Connection.get_client_ca_list} returns a list containing those
        X509Names after the connection is set up.
        """
        secert = load_certificate(FILETYPE_PEM, server_cert_pem)
        clcert = load_certificate(FILETYPE_PEM, server_cert_pem)

        sedesc = secert.get_subject()
        cldesc = clcert.get_subject()

        def multiple_ca(ctx):
            L = [sedesc, cldesc]
            ctx.set_client_ca_list(L)
            return L
        self._check_client_ca_list(multiple_ca)


    def test_reset_ca_list(self):
        """
        If called multiple times, only the X509Names passed to the final call
        of L{Context.set_client_ca_list} are used to configure the CA names
        sent to the client.
        """
        cacert = load_certificate(FILETYPE_PEM, root_cert_pem)
        secert = load_certificate(FILETYPE_PEM, server_cert_pem)
        clcert = load_certificate(FILETYPE_PEM, server_cert_pem)

        cadesc = cacert.get_subject()
        sedesc = secert.get_subject()
        cldesc = clcert.get_subject()

        def changed_ca(ctx):
            ctx.set_client_ca_list([sedesc, cldesc])
            ctx.set_client_ca_list([cadesc])
            return [cadesc]
        self._check_client_ca_list(changed_ca)


    def test_mutated_ca_list(self):
        """
        If the list passed to L{Context.set_client_ca_list} is mutated
        afterwards, this does not affect the list of CA names sent to the
        client.
        """
        cacert = load_certificate(FILETYPE_PEM, root_cert_pem)
        secert = load_certificate(FILETYPE_PEM, server_cert_pem)

        cadesc = cacert.get_subject()
        sedesc = secert.get_subject()

        def mutated_ca(ctx):
            L = [cadesc]
            ctx.set_client_ca_list([cadesc])
            L.append(sedesc)
            return [cadesc]
        self._check_client_ca_list(mutated_ca)


    def test_add_client_ca_errors(self):
        """
        L{Context.add_client_ca} raises L{TypeError} if called with a non-X509
        object or with a number of arguments other than one.
        """
        ctx = Context(TLSv1_METHOD)
        cacert = load_certificate(FILETYPE_PEM, root_cert_pem)
        self.assertRaises(TypeError, ctx.add_client_ca)
        self.assertRaises(TypeError, ctx.add_client_ca, "spam")
        self.assertRaises(TypeError, ctx.add_client_ca, cacert, cacert)


    def test_one_add_client_ca(self):
        """
        A certificate's subject can be added as a CA to be sent to the client
        with L{Context.add_client_ca}.
        """
        cacert = load_certificate(FILETYPE_PEM, root_cert_pem)
        cadesc = cacert.get_subject()
        def single_ca(ctx):
            ctx.add_client_ca(cacert)
            return [cadesc]
        self._check_client_ca_list(single_ca)


    def test_multiple_add_client_ca(self):
        """
        Multiple CA names can be sent to the client by calling
        L{Context.add_client_ca} with multiple X509 objects.
        """
        cacert = load_certificate(FILETYPE_PEM, root_cert_pem)
        secert = load_certificate(FILETYPE_PEM, server_cert_pem)

        cadesc = cacert.get_subject()
        sedesc = secert.get_subject()

        def multiple_ca(ctx):
            ctx.add_client_ca(cacert)
            ctx.add_client_ca(secert)
            return [cadesc, sedesc]
        self._check_client_ca_list(multiple_ca)


    def test_set_and_add_client_ca(self):
        """
        A call to L{Context.set_client_ca_list} followed by a call to
        L{Context.add_client_ca} results in using the CA names from the first
        call and the CA name from the second call.
        """
        cacert = load_certificate(FILETYPE_PEM, root_cert_pem)
        secert = load_certificate(FILETYPE_PEM, server_cert_pem)
        clcert = load_certificate(FILETYPE_PEM, server_cert_pem)

        cadesc = cacert.get_subject()
        sedesc = secert.get_subject()
        cldesc = clcert.get_subject()

        def mixed_set_add_ca(ctx):
            ctx.set_client_ca_list([cadesc, sedesc])
            ctx.add_client_ca(clcert)
            return [cadesc, sedesc, cldesc]
        self._check_client_ca_list(mixed_set_add_ca)


    def test_set_after_add_client_ca(self):
        """
        A call to L{Context.set_client_ca_list} after a call to
        L{Context.add_client_ca} replaces the CA name specified by the former
        call with the names specified by the latter cal.
        """
        cacert = load_certificate(FILETYPE_PEM, root_cert_pem)
        secert = load_certificate(FILETYPE_PEM, server_cert_pem)
        clcert = load_certificate(FILETYPE_PEM, server_cert_pem)

        cadesc = cacert.get_subject()
        sedesc = secert.get_subject()

        def set_replaces_add_ca(ctx):
            ctx.add_client_ca(clcert)
            ctx.set_client_ca_list([cadesc])
            ctx.add_client_ca(secert)
            return [cadesc, sedesc]
        self._check_client_ca_list(set_replaces_add_ca)


class InfoConstantTests(TestCase):
    """
    Tests for assorted constants exposed for use in info callbacks.
    """
    def test_integers(self):
        """
        All of the info constants are integers.

        This is a very weak test.  It would be nice to have one that actually
        verifies that as certain info events happen, the value passed to the
        info callback matches up with the constant exposed by OpenSSL.SSL.
        """
        for const in [
            SSL_ST_CONNECT, SSL_ST_ACCEPT, SSL_ST_MASK, SSL_ST_INIT,
            SSL_ST_BEFORE, SSL_ST_OK, SSL_ST_RENEGOTIATE,
            SSL_CB_LOOP, SSL_CB_EXIT, SSL_CB_READ, SSL_CB_WRITE, SSL_CB_ALERT,
            SSL_CB_READ_ALERT, SSL_CB_WRITE_ALERT, SSL_CB_ACCEPT_LOOP,
            SSL_CB_ACCEPT_EXIT, SSL_CB_CONNECT_LOOP, SSL_CB_CONNECT_EXIT,
            SSL_CB_HANDSHAKE_START, SSL_CB_HANDSHAKE_DONE]:

            self.assertTrue(isinstance(const, int))


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = util
# Copyright (C) Jean-Paul Calderone
# Copyright (C) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Helpers for the OpenSSL test suite, largely copied from
U{Twisted<http://twistedmatrix.com/>}.
"""

import shutil
import os, os.path
from tempfile import mktemp
from unittest import TestCase
import sys

from OpenSSL.crypto import Error, _exception_from_error_queue

if sys.version_info < (3, 0):
    def b(s):
        return s
    bytes = str
else:
    def b(s):
        return s.encode("charmap")
    bytes = bytes


class TestCase(TestCase):
    """
    L{TestCase} adds useful testing functionality beyond what is available
    from the standard library L{unittest.TestCase}.
    """
    def tearDown(self):
        """
        Clean up any files or directories created using L{TestCase.mktemp}.
        Subclasses must invoke this method if they override it or the
        cleanup will not occur.
        """
        if False and self._temporaryFiles is not None:
            for temp in self._temporaryFiles:
                if os.path.isdir(temp):
                    shutil.rmtree(temp)
                elif os.path.exists(temp):
                    os.unlink(temp)
        try:
            _exception_from_error_queue()
        except Error:
            e = sys.exc_info()[1]
            if e.args != ([],):
                self.fail("Left over errors in OpenSSL error queue: " + repr(e))


    def failUnlessIn(self, containee, container, msg=None):
        """
        Fail the test if C{containee} is not found in C{container}.

        @param containee: the value that should be in C{container}
        @param container: a sequence type, or in the case of a mapping type,
                          will follow semantics of 'if key in dict.keys()'
        @param msg: if msg is None, then the failure message will be
                    '%r not in %r' % (first, second)
        """
        if containee not in container:
            raise self.failureException(msg or "%r not in %r"
                                        % (containee, container))
        return containee
    assertIn = failUnlessIn

    def failUnlessIdentical(self, first, second, msg=None):
        """
        Fail the test if C{first} is not C{second}.  This is an
        obect-identity-equality test, not an object equality
        (i.e. C{__eq__}) test.

        @param msg: if msg is None, then the failure message will be
        '%r is not %r' % (first, second)
        """
        if first is not second:
            raise self.failureException(msg or '%r is not %r' % (first, second))
        return first
    assertIdentical = failUnlessIdentical


    def failIfIdentical(self, first, second, msg=None):
        """
        Fail the test if C{first} is C{second}.  This is an
        obect-identity-equality test, not an object equality
        (i.e. C{__eq__}) test.

        @param msg: if msg is None, then the failure message will be
        '%r is %r' % (first, second)
        """
        if first is second:
            raise self.failureException(msg or '%r is %r' % (first, second))
        return first
    assertNotIdentical = failIfIdentical


    def failUnlessRaises(self, exception, f, *args, **kwargs):
        """
        Fail the test unless calling the function C{f} with the given
        C{args} and C{kwargs} raises C{exception}. The failure will report
        the traceback and call stack of the unexpected exception.

        @param exception: exception type that is to be expected
        @param f: the function to call

        @return: The raised exception instance, if it is of the given type.
        @raise self.failureException: Raised if the function call does
            not raise an exception or if it raises an exception of a
            different type.
        """
        try:
            result = f(*args, **kwargs)
        except exception:
            inst = sys.exc_info()[1]
            return inst
        except:
            raise self.failureException('%s raised instead of %s'
                                        % (sys.exc_info()[0],
                                           exception.__name__,
                                          ))
        else:
            raise self.failureException('%s not raised (%r returned)'
                                        % (exception.__name__, result))
    assertRaises = failUnlessRaises


    _temporaryFiles = None
    def mktemp(self):
        """
        Pathetic substitute for twisted.trial.unittest.TestCase.mktemp.
        """
        if self._temporaryFiles is None:
            self._temporaryFiles = []
        temp = mktemp(dir=".")
        self._temporaryFiles.append(temp)
        return temp


    # Python 2.3 compatibility.
    def assertTrue(self, *a, **kw):
        return self.failUnless(*a, **kw)


    def assertFalse(self, *a, **kw):
        return self.failIf(*a, **kw)


    # Other stuff
    def assertConsistentType(self, theType, name, *constructionArgs):
        """
        Perform various assertions about C{theType} to ensure that it is a
        well-defined type.  This is useful for extension types, where it's
        pretty easy to do something wacky.  If something about the type is
        unusual, an exception will be raised.

        @param theType: The type object about which to make assertions.
        @param name: A string giving the name of the type.
        @param constructionArgs: Positional arguments to use with C{theType} to
            create an instance of it.
        """
        self.assertEqual(theType.__name__, name)
        self.assertTrue(isinstance(theType, type))
        instance = theType(*constructionArgs)
        self.assertIdentical(type(instance), theType)

########NEW FILE########
__FILENAME__ = tsafe
from OpenSSL import SSL
_ssl = SSL
del SSL

import threading
_RLock = threading.RLock
del threading

class Connection:
    def __init__(self, *args):
        self._ssl_conn = apply(_ssl.Connection, args)
        self._lock = _RLock()

    for f in ('get_context', 'pending', 'send', 'write', 'recv', 'read',
              'renegotiate', 'bind', 'listen', 'connect', 'accept',
              'setblocking', 'fileno', 'shutdown', 'close', 'get_cipher_list',
              'getpeername', 'getsockname', 'getsockopt', 'setsockopt',
              'makefile', 'get_app_data', 'set_app_data', 'state_string',
              'sock_shutdown', 'get_peer_certificate', 'get_peer_cert_chain', 'want_read',
              'want_write', 'set_connect_state', 'set_accept_state',
              'connect_ex', 'sendall'):
        exec("""def %s(self, *args):
            self._lock.acquire()
            try:
                return self._ssl_conn.%s(*args)
            finally:
                self._lock.release()\n""" % (f, f))


########NEW FILE########
__FILENAME__ = version
# Copyright (C) AB Strakt
# Copyright (C) Jean-Paul Calderone
# See LICENSE for details.

"""
pyOpenSSL - A simple wrapper around the OpenSSL library
"""

__version__ = '0.13'

########NEW FILE########
__FILENAME__ = anno-api
#! /usr/bin/env python
"""Add reference count annotations to the Python/C API Reference."""
__version__ = '$Revision: 1.1.1.1 $'

import getopt
import os
import sys

import refcounts


PREFIX_1 = r"\begin{cfuncdesc}{PyObject*}{"
PREFIX_2 = r"\begin{cfuncdesc}{PyVarObject*}{"


def main():
    rcfile = os.path.join(os.path.dirname(refcounts.__file__), os.pardir,
                          "api", "refcounts.dat")
    outfile = "-"
    opts, args = getopt.getopt(sys.argv[1:], "o:r:", ["output=", "refcounts="])
    for opt, arg in opts:
        if opt in ("-o", "--output"):
            outfile = arg
        elif opt in ("-r", "--refcounts"):
            rcfile = arg
    rcdict = refcounts.load(rcfile)
    if outfile == "-":
        output = sys.stdout
    else:
        output = open(outfile, "w")
    if not args:
        args = ["-"]
    for infile in args:
        if infile == "-":
            input = sys.stdin
        else:
            input = open(infile)
        while 1:
            line = input.readline()
            if not line:
                break
            prefix = None
            if line.startswith(PREFIX_1):
                prefix = PREFIX_1
            elif line.startswith(PREFIX_2):
                prefix = PREFIX_2
            if prefix:
                s = line[len(prefix):].split('}', 1)[0]
                try:
                    info = rcdict[s]
                except KeyError:
                    sys.stderr.write("No refcount data for %s\n" % s)
                else:
                    if info.result_type in ("PyObject*", "PyVarObject*"):
                        if info.result_refs is None:
                            rc = "Always \NULL{}"
                        else:
                            rc = info.result_refs and "New" or "Borrowed"
                            rc = rc + " reference"
                        line = (r"\begin{cfuncdesc}[%s]{%s}{"
                                % (rc, info.result_type)) \
                                + line[len(prefix):]
            output.write(line)
        if infile != "-":
            input.close()
    if outfile != "-":
        output.close()


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = buildindex
#! /usr/bin/env python

__version__ = '$Revision: 1.1.1.1 $'

import os
import re
import string
import sys


class Node:
    __rmjunk = re.compile("<#\d+#>")

    continuation = 0

    def __init__(self, link, str, seqno):
        self.links = [link]
        self.seqno = seqno
        # remove <#\d+#> left in by moving the data out of LaTeX2HTML
        str = self.__rmjunk.sub('', str)
        # build up the text
        self.text = split_entry_text(str)
        self.key = split_entry_key(str)

    def __cmp__(self, other):
        """Comparison operator includes sequence number, for use with
        list.sort()."""
        return self.cmp_entry(other) or cmp(self.seqno, other.seqno)

    def cmp_entry(self, other):
        """Comparison 'operator' that ignores sequence number."""
        c = 0
        for i in range(min(len(self.key), len(other.key))):
            c = (cmp_part(self.key[i], other.key[i])
                 or cmp_part(self.text[i], other.text[i]))
            if c:
                break
        return c or cmp(self.key, other.key) or cmp(self.text, other.text)

    def __repr__(self):
        return "<Node for %s (%s)>" % (string.join(self.text, '!'), self.seqno)

    def __str__(self):
        return string.join(self.key, '!')

    def dump(self):
        return "%s\1%s###%s\n" \
               % (string.join(self.links, "\1"),
                  string.join(self.text, '!'),
                  self.seqno)


def cmp_part(s1, s2):
    result = cmp(s1, s2)
    if result == 0:
        return 0
    l1 = string.lower(s1)
    l2 = string.lower(s2)
    minlen = min(len(s1), len(s2))
    if len(s1) < len(s2) and l1 == l2[:len(s1)]:
        result = -1
    elif len(s2) < len(s1) and l2 == l1[:len(s2)]:
        result = 1
    else:
        result = cmp(l1, l2) or cmp(s1, s2)
    return result


def split_entry(str, which):
    stuff = []
    parts = string.split(str, '!')
    parts = map(string.split, parts, ['@'] * len(parts))
    for entry in parts:
        if len(entry) != 1:
            key = entry[which]
        else:
            key = entry[0]
        stuff.append(key)
    return stuff


_rmtt = re.compile(r"""(.*)<tt(?: class=['"][a-z0-9]+["'])?>(.*)</tt>(.*)$""",
                   re.IGNORECASE)
_rmparens = re.compile(r"\(\)")

def split_entry_key(str):
    parts = split_entry(str, 1)
    for i in range(len(parts)):
        m = _rmtt.match(parts[i])
        if m:
            parts[i] = string.join(m.group(1, 2, 3), '')
        else:
            parts[i] = string.lower(parts[i])
        # remove '()' from the key:
        parts[i] = _rmparens.sub('', parts[i])
    return map(trim_ignored_letters, parts)


def split_entry_text(str):
    if '<' in str:
        m = _rmtt.match(str)
        if m:
            str = string.join(m.group(1, 2, 3), '')
    return split_entry(str, 1)


def load(fp):
    nodes = []
    rx = re.compile("(.*)\1(.*)###(.*)$")
    while 1:
        line = fp.readline()
        if not line:
            break
        m = rx.match(line)
        if m:
            link, str, seqno = m.group(1, 2, 3)
            nodes.append(Node(link, str, seqno))
    return nodes


def trim_ignored_letters(s):
    # ignore $ to keep environment variables with the
    # leading letter from the name
    s = string.lower(s)
    if s[0] == "$":
        return s[1:]
    else:
        return s

def get_first_letter(s):
    return string.lower(trim_ignored_letters(s)[0])


def split_letters(nodes):
    letter_groups = []
    if nodes:
        group = []
        append = group.append
        letter = get_first_letter(nodes[0].text[0])
        letter_groups.append((letter, group))
        for node in nodes:
            nletter = get_first_letter(node.text[0])
            if letter != nletter:
                letter = nletter
                group = []
                letter_groups.append((letter, group))
                append = group.append
            append(node)
    return letter_groups


# need a function to separate the nodes into columns...
def split_columns(nodes, columns=1):
    if columns <= 1:
        return [nodes]
    # This is a rough height; we may have to increase to avoid breaks before
    # a subitem.
    colheight = len(nodes) / columns
    numlong = len(nodes) % columns
    if numlong:
        colheight = colheight + 1
    else:
        numlong = columns
    cols = []
    for i in range(numlong):
        start = i * colheight
        end = start + colheight
        cols.append(nodes[start:end])
    del nodes[:end]
    colheight = colheight - 1
    try:
        numshort = len(nodes) / colheight
    except ZeroDivisionError:
        cols = cols + (columns - len(cols)) * [[]]
    else:
        for i in range(numshort):
            start = i * colheight
            end = start + colheight
            cols.append(nodes[start:end])
    #
    # If items continue across columns, make sure they are marked
    # as continuations so the user knows to look at the previous column.
    #
    for i in range(len(cols) - 1):
        try:
            prev = cols[i][-1]
            next = cols[i + 1][0]
        except IndexError:
            return cols
        else:
            n = min(len(prev.key), len(next.key))
            for j in range(n):
                if prev.key[j] != next.key[j]:
                    break
                next.continuation = j + 1
    return cols


DL_LEVEL_INDENT = "  "

def format_column(nodes):
    strings = ["<dl compact>"]
    append = strings.append
    level = 0
    previous = []
    for node in nodes:
        current = node.text
        count = 0
        for i in range(min(len(current), len(previous))):
            if previous[i] != current[i]:
                break
            count = i + 1
        if count > level:
            append("<dl compact>" * (count - level) + "\n")
            level = count
        elif level > count:
            append("\n")
            append(level * DL_LEVEL_INDENT)
            append("</dl>" * (level - count))
            level = count
        # else: level == count
        for i in range(count, len(current) - 1):
            term = node.text[i]
            level = level + 1
            if node.continuation > i:
                extra = " (continued)"
            else:
                extra = ""
            append("\n<dt>%s%s\n<dd>\n%s<dl compact>"
                   % (term, extra, level * DL_LEVEL_INDENT))
        append("\n%s<dt>%s%s</a>"
               % (level * DL_LEVEL_INDENT, node.links[0], node.text[-1]))
        for link in node.links[1:]:
            append(",\n%s    %s[Link]</a>" % (level * DL_LEVEL_INDENT, link))
        previous = current
    append("\n")
    append("</dl>" * (level + 1))
    return string.join(strings, '')


def format_nodes(nodes, columns=1):
    strings = []
    append = strings.append
    if columns > 1:
        colnos = range(columns)
        colheight = len(nodes) / columns
        if len(nodes) % columns:
            colheight = colheight + 1
        colwidth = 100 / columns
        append('<table width="100%"><tr valign="top">')
        for col in split_columns(nodes, columns):
            append('<td width="%d%%">\n' % colwidth)
            append(format_column(col))
            append("\n</td>")
        append("\n</tr></table>")
    else:
        append(format_column(nodes))
    append("\n<p>\n")
    return string.join(strings, '')


def format_letter(letter):
    if letter == '.':
        lettername = ". (dot)"
    elif letter == '_':
        lettername = "_ (underscore)"
    else:
        lettername = string.upper(letter)
    return "\n<hr>\n<h2><a name=\"letter-%s\">%s</a></h2>\n\n" \
           % (letter, lettername)


def format_html_letters(nodes, columns=1):
    letter_groups = split_letters(nodes)
    items = []
    for letter, nodes in letter_groups:
        s = "<b><a href=\"#letter-%s\">%s</a></b>" % (letter, letter)
        items.append(s)
    s = ["<hr><center>\n%s</center>\n" % string.join(items, " |\n")]
    for letter, nodes in letter_groups:
        s.append(format_letter(letter))
        s.append(format_nodes(nodes, columns))
    return string.join(s, '')

def format_html(nodes, columns):
    return format_nodes(nodes, columns)


def collapse(nodes):
    """Collapse sequences of nodes with matching keys into a single node.
    Destructive."""
    if len(nodes) < 2:
        return
    prev = nodes[0]
    i = 1
    while i < len(nodes):
        node = nodes[i]
        if not node.cmp_entry(prev):
            prev.links.append(node.links[0])
            del nodes[i]
        else:
            i = i + 1
            prev = node


def dump(nodes, fp):
    for node in nodes:
        fp.write(node.dump())


def process_nodes(nodes, columns, letters):
    nodes.sort()
    collapse(nodes)
    if letters:
        return format_html_letters(nodes, columns)
    else:
        return format_html(nodes, columns)


def main():
    import getopt
    ifn = "-"
    ofn = "-"
    columns = 1
    letters = 0
    opts, args = getopt.getopt(sys.argv[1:], "c:lo:",
                               ["columns=", "letters", "output="])
    for opt, val in opts:
        if opt in ("-o", "--output"):
            ofn = val
        elif opt in ("-c", "--columns"):
            columns = string.atoi(val)
        elif opt in ("-l", "--letters"):
            letters = 1
    if not args:
        args = [ifn]
    nodes = []
    for fn in args:
        nodes = nodes + load(open(fn))
    num_nodes = len(nodes)
    html = process_nodes(nodes, columns, letters)
    program = os.path.basename(sys.argv[0])
    if ofn == "-":
        sys.stdout.write(html)
        sys.stderr.write("\n%s: %d index nodes" % (program, num_nodes))
    else:
        open(ofn, "w").write(html)
        print
        print "%s: %d index nodes" % (program, num_nodes)


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = custlib
# Generate custlib.tex, which is a site-specific library document.

# Phase I: list all the things that can be imported

import glob, os, sys, string
modules={}

for modname in sys.builtin_module_names:
    modules[modname]=modname
    
for dir in sys.path:
    # Look for *.py files
    filelist=glob.glob(os.path.join(dir, '*.py'))
    for file in filelist: 
        path, file = os.path.split(file)
        base, ext=os.path.splitext(file)
        modules[string.lower(base)]=base

    # Look for shared library files
    filelist=(glob.glob(os.path.join(dir, '*.so')) + 
              glob.glob(os.path.join(dir, '*.sl')) +
              glob.glob(os.path.join(dir, '*.o')) )
    for file in filelist: 
        path, file = os.path.split(file)
        base, ext=os.path.splitext(file)
        if base[-6:]=='module': base=base[:-6]
        modules[string.lower(base)]=base

# Minor oddity: the types module is documented in libtypes2.tex
if modules.has_key('types'):
    del modules['types'] ; modules['types2']=None

# Phase II: find all documentation files (lib*.tex)
#           and eliminate modules that don't have one.

docs={}
filelist=glob.glob('lib*.tex')
for file in filelist:
    modname=file[3:-4]
    docs[modname]=modname

mlist=modules.keys()
mlist=filter(lambda x, docs=docs: docs.has_key(x), mlist)
mlist.sort()
mlist=map(lambda x, docs=docs: docs[x], mlist)

modules=mlist

# Phase III: write custlib.tex

# Write the boilerplate
# XXX should be fancied up.  
print """\documentstyle[twoside,11pt,myformat]{report}
\\title{Python Library Reference}
\\input{boilerplate}
\\makeindex                     % tell \\index to actually write the .idx file
\\begin{document}
\\pagenumbering{roman}
\\maketitle
\\input{copyright}
\\begin{abstract}
\\noindent This is a customized version of the Python Library Reference.
\\end{abstract}
\\pagebreak
{\\parskip = 0mm \\tableofcontents}
\\pagebreak\\pagenumbering{arabic}"""
    
for modname in mlist: 
    print "\\input{lib%s}" % (modname,)
    
# Write the end
print """\\input{custlib.ind}                   % Index
\\end{document}"""

########NEW FILE########
__FILENAME__ = cvsinfo
"""Utility class and function to get information about the CVS repository
based on checked-out files.
"""

import os


def get_repository_list(paths):
    d = {}
    for name in paths:
        if os.path.isfile(name):
            dir = os.path.dirname(name)
        else:
            dir = name
        rootfile = os.path.join(name, "CVS", "Root")
        root = open(rootfile).readline().strip()
        if not d.has_key(root):
            d[root] = RepositoryInfo(dir), [name]
        else:
            d[root][1].append(name)
    return d.values()


class RepositoryInfo:
    """Record holding information about the repository we want to talk to."""
    cvsroot_path = None
    branch = None

    # type is '', ':ext', or ':pserver:'
    type = ""

    def __init__(self, dir=None):
        if dir is None:
            dir = os.getcwd()
        dir = os.path.join(dir, "CVS")
        root = open(os.path.join(dir, "Root")).readline().strip()
        if root.startswith(":pserver:"):
            self.type = ":pserver:"
            root = root[len(":pserver:"):]
        elif ":" in root:
            if root.startswith(":ext:"):
                root = root[len(":ext:"):]
            self.type = ":ext:"
        self.repository = root
        if ":" in root:
            host, path = root.split(":", 1)
            self.cvsroot_path = path
        else:
            self.cvsroot_path = root
        fn = os.path.join(dir, "Tag")
        if os.path.isfile(fn):
            self.branch = open(fn).readline().strip()[1:]

    def get_cvsroot(self):
        return self.type + self.repository

    _repository_dir_cache = {}

    def get_repository_file(self, path):
        filename = os.path.abspath(path)
        if os.path.isdir(path):
            dir = path
            join = 0
        else:
            dir = os.path.dirname(path)
            join = 1
        try:
            repodir = self._repository_dir_cache[dir]
        except KeyError:
            repofn = os.path.join(dir, "CVS", "Repository")
            repodir = open(repofn).readline().strip()
            repodir = os.path.join(self.cvsroot_path, repodir)
            self._repository_dir_cache[dir] = repodir
        if join:
            fn = os.path.join(repodir, os.path.basename(path))
        else:
            fn = repodir
        return fn[len(self.cvsroot_path)+1:]

    def __repr__(self):
        return "<RepositoryInfo for %s>" % `self.get_cvsroot()`

########NEW FILE########
__FILENAME__ = indfix
#! /usr/bin/env python

"""Combine similar index entries into an entry and subentries.

For example:

    \item {foobar} (in module flotz), 23
    \item {foobar} (in module whackit), 4323

becomes

    \item {foobar}
      \subitem in module flotz, 23
      \subitem in module whackit, 4323

Note that an item which matches the format of a collapsable item but which
isn't part of a group of similar items is not modified.
"""
__version__ = '$Revision: 1.1.1.1 $'

import re
import string
import StringIO
import sys


def cmp_entries(e1, e2, lower=string.lower):
    return cmp(lower(e1[1]), lower(e2[1])) or cmp(e1, e2)


def dump_entries(write, entries):
    if len(entries) == 1:
        write("  \\item %s (%s)%s\n" % entries[0])
        return
    write("  \item %s\n" % entries[0][0])
    # now sort these in a case insensitive manner:
    if len(entries) > 0:
        entries.sort(cmp_entries)
    for xxx, subitem, pages in entries:
        write("    \subitem %s%s\n" % (subitem, pages))


breakable_re = re.compile(
    r"  \\item (.*) [(](.*)[)]((?:(?:, \d+)|(?:, \\[a-z]*\{\d+\}))+)")


def process(ifn, ofn=None):
    if ifn == "-":
        ifp = sys.stdin
    else:
        ifp = open(ifn)
    if ofn is None:
        ofn = ifn
    ofp = StringIO.StringIO()
    entries = []
    match = breakable_re.match
    write = ofp.write
    while 1:
        line = ifp.readline()
        if not line:
            break
        m = match(line)
        if m:
            entry = m.group(1, 2, 3)
            if entries and entries[-1][0] != entry[0]:
                dump_entries(write, entries)
                entries = []
            entries.append(entry)
        elif entries:
            dump_entries(write, entries)
            entries = []
            write(line)
        else:
            write(line)
    del write
    del match
    ifp.close()
    data = ofp.getvalue()
    ofp.close()
    if ofn == "-":
        ofp = sys.stdout
    else:
        ofp = open(ofn, "w")
    ofp.write(data)
    ofp.close()


def main():
    import getopt
    outfile = None
    opts, args = getopt.getopt(sys.argv[1:], "o:")
    for opt, val in opts:
        if opt in ("-o", "--output"):
            outfile = val
    filename = args[0]
    outfile = outfile or filename
    process(filename, outfile)


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = keywords
#! /usr/bin/env python

# This Python program sorts and reformats the table of keywords in ref2.tex

import string
l = []
try:
	while 1:
		l = l + string.split(raw_input())
except EOFError:
	pass
l.sort()
for x in l[:]:
	while l.count(x) > 1: l.remove(x)
ncols = 5
nrows = (len(l)+ncols-1)/ncols
for i in range(nrows):
	for j in range(i, len(l), nrows):
		print string.ljust(l[j], 10),
	print

########NEW FILE########
__FILENAME__ = refcounts
"""Support functions for loading the reference count data file."""
__version__ = '$Revision: 1.1.1.1 $'

import os
import string
import sys


# Determine the expected location of the reference count file:
try:
    p = os.path.dirname(__file__)
except NameError:
    p = sys.path[0]
p = os.path.normpath(os.path.join(os.getcwd(), p, os.pardir,
                                  "api", "refcounts.dat"))
DEFAULT_PATH = p
del p


def load(path=DEFAULT_PATH):
    return loadfile(open(path))


def loadfile(fp):
    d = {}
    while 1:
        line = fp.readline()
        if not line:
            break
        line = string.strip(line)
        if line[:1] in ("", "#"):
            # blank lines and comments
            continue
        parts = string.split(line, ":", 4)
        function, type, arg, refcount, comment = parts
        if refcount == "null":
            refcount = None
        elif refcount:
            refcount = int(refcount)
        else:
            refcount = None
        #
        # Get the entry, creating it if needed:
        #
        try:
            entry = d[function]
        except KeyError:
            entry = d[function] = Entry(function)
        #
        # Update the entry with the new parameter or the result information.
        #
        if arg:
            entry.args.append((arg, type, refcount))
        else:
            entry.result_type = type
            entry.result_refs = refcount
    return d


class Entry:
    def __init__(self, name):
        self.name = name
        self.args = []
        self.result_type = ''
        self.result_refs = None


def dump(d):
    """Dump the data in the 'canonical' format, with functions in
    sorted order."""
    items = d.items()
    items.sort()
    first = 1
    for k, entry in items:
        if first:
            first = 0
        else:
            print
        s = entry.name + ":%s:%s:%s:"
        if entry.result_refs is None:
            r = ""
        else:
            r = entry.result_refs
        print s % (entry.result_type, "", r)
        for t, n, r in entry.args:
            if r is None:
                r = ""
            print s % (t, n, r)


def main():
    d = load()
    dump(d)


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = docfixer
#! /usr/bin/env python

"""Perform massive transformations on a document tree created from the LaTeX
of the Python documentation, and dump the ESIS data for the transformed tree.
"""


import errno
import esistools
import re
import string
import sys
import xml.dom
import xml.dom.minidom

ELEMENT = xml.dom.Node.ELEMENT_NODE
ENTITY_REFERENCE = xml.dom.Node.ENTITY_REFERENCE_NODE
TEXT = xml.dom.Node.TEXT_NODE


class ConversionError(Exception):
    pass


ewrite = sys.stderr.write
try:
    # We can only do this trick on Unix (if tput is on $PATH)!
    if sys.platform != "posix" or not sys.stderr.isatty():
        raise ImportError
    import commands
except ImportError:
    bwrite = ewrite
else:
    def bwrite(s, BOLDON=commands.getoutput("tput bold"),
               BOLDOFF=commands.getoutput("tput sgr0")):
        ewrite("%s%s%s" % (BOLDON, s, BOLDOFF))


PARA_ELEMENT = "para"

DEBUG_PARA_FIXER = 0

if DEBUG_PARA_FIXER:
    def para_msg(s):
        ewrite("*** %s\n" % s)
else:
    def para_msg(s):
        pass


def get_first_element(doc, gi):
    for n in doc.childNodes:
        if n.nodeName == gi:
            return n

def extract_first_element(doc, gi):
    node = get_first_element(doc, gi)
    if node is not None:
        doc.removeChild(node)
    return node


def get_documentElement(node):
    result = None
    for child in node.childNodes:
        if child.nodeType == ELEMENT:
            result = child
    return result


def set_tagName(elem, gi):
    elem.nodeName = elem.tagName = gi


def find_all_elements(doc, gi):
    nodes = []
    if doc.nodeName == gi:
        nodes.append(doc)
    for child in doc.childNodes:
        if child.nodeType == ELEMENT:
            if child.tagName == gi:
                nodes.append(child)
            for node in child.getElementsByTagName(gi):
                nodes.append(node)
    return nodes

def find_all_child_elements(doc, gi):
    nodes = []
    for child in doc.childNodes:
        if child.nodeName == gi:
            nodes.append(child)
    return nodes


def find_all_elements_from_set(doc, gi_set):
    return __find_all_elements_from_set(doc, gi_set, [])

def __find_all_elements_from_set(doc, gi_set, nodes):
    if doc.nodeName in gi_set:
        nodes.append(doc)
    for child in doc.childNodes:
        if child.nodeType == ELEMENT:
            __find_all_elements_from_set(child, gi_set, nodes)
    return nodes


def simplify(doc, fragment):
    # Try to rationalize the document a bit, since these things are simply
    # not valid SGML/XML documents as they stand, and need a little work.
    documentclass = "document"
    inputs = []
    node = extract_first_element(fragment, "documentclass")
    if node is not None:
        documentclass = node.getAttribute("classname")
    node = extract_first_element(fragment, "title")
    if node is not None:
        inputs.append(node)
    # update the name of the root element
    node = get_first_element(fragment, "document")
    if node is not None:
        set_tagName(node, documentclass)
    while 1:
        node = extract_first_element(fragment, "input")
        if node is None:
            break
        inputs.append(node)
    if inputs:
        docelem = get_documentElement(fragment)
        inputs.reverse()
        for node in inputs:
            text = doc.createTextNode("\n")
            docelem.insertBefore(text, docelem.firstChild)
            docelem.insertBefore(node, text)
        docelem.insertBefore(doc.createTextNode("\n"), docelem.firstChild)
    while fragment.firstChild and fragment.firstChild.nodeType == TEXT:
        fragment.removeChild(fragment.firstChild)


def cleanup_root_text(doc):
    discards = []
    skip = 0
    for n in doc.childNodes:
        prevskip = skip
        skip = 0
        if n.nodeType == TEXT and not prevskip:
            discards.append(n)
        elif n.nodeName == "COMMENT":
            skip = 1
    for node in discards:
        doc.removeChild(node)


DESCRIPTOR_ELEMENTS = (
    "cfuncdesc", "cvardesc", "ctypedesc",
    "classdesc", "memberdesc", "memberdescni", "methoddesc", "methoddescni",
    "excdesc", "funcdesc", "funcdescni", "opcodedesc",
    "datadesc", "datadescni",
    )

def fixup_descriptors(doc, fragment):
    sections = find_all_elements(fragment, "section")
    for section in sections:
        find_and_fix_descriptors(doc, section)


def find_and_fix_descriptors(doc, container):
    children = container.childNodes
    for child in children:
        if child.nodeType == ELEMENT:
            tagName = child.tagName
            if tagName in DESCRIPTOR_ELEMENTS:
                rewrite_descriptor(doc, child)
            elif tagName == "subsection":
                find_and_fix_descriptors(doc, child)


def rewrite_descriptor(doc, descriptor):
    #
    # Do these things:
    #   1. Add an "index='no'" attribute to the element if the tagName
    #      ends in 'ni', removing the 'ni' from the name.
    #   2. Create a <signature> from the name attribute
    #   2a.Create an <args> if it appears to be available.
    #   3. Create additional <signature>s from <*line{,ni}> elements,
    #      if found.
    #   4. If a <versionadded> is found, move it to an attribute on the
    #      descriptor.
    #   5. Move remaining child nodes to a <description> element.
    #   6. Put it back together.
    #
    # 1.
    descname = descriptor.tagName
    index = 1
    if descname[-2:] == "ni":
        descname = descname[:-2]
        descriptor.setAttribute("index", "no")
        set_tagName(descriptor, descname)
        index = 0
    desctype = descname[:-4] # remove 'desc'
    linename = desctype + "line"
    if not index:
        linename = linename + "ni"
    # 2.
    signature = doc.createElement("signature")
    name = doc.createElement("name")
    signature.appendChild(doc.createTextNode("\n    "))
    signature.appendChild(name)
    name.appendChild(doc.createTextNode(descriptor.getAttribute("name")))
    descriptor.removeAttribute("name")
    # 2a.
    if descriptor.hasAttribute("var"):
        if descname != "opcodedesc":
            raise RuntimeError, \
                  "got 'var' attribute on descriptor other than opcodedesc"
        variable = descriptor.getAttribute("var")
        if variable:
            args = doc.createElement("args")
            args.appendChild(doc.createTextNode(variable))
            signature.appendChild(doc.createTextNode("\n    "))
            signature.appendChild(args)
        descriptor.removeAttribute("var")
    newchildren = [signature]
    children = descriptor.childNodes
    pos = skip_leading_nodes(children)
    if pos < len(children):
        child = children[pos]
        if child.nodeName == "args":
            # move <args> to <signature>, or remove if empty:
            child.parentNode.removeChild(child)
            if len(child.childNodes):
                signature.appendChild(doc.createTextNode("\n    "))
                signature.appendChild(child)
    signature.appendChild(doc.createTextNode("\n  "))
    # 3, 4.
    pos = skip_leading_nodes(children, pos)
    while pos < len(children) \
          and children[pos].nodeName in (linename, "versionadded"):
        if children[pos].tagName == linename:
            # this is really a supplemental signature, create <signature>
            oldchild = children[pos].cloneNode(1)
            try:
                sig = methodline_to_signature(doc, children[pos])
            except KeyError:
                print oldchild.toxml()
                raise
            newchildren.append(sig)
        else:
            # <versionadded added=...>
            descriptor.setAttribute(
                "added", children[pos].getAttribute("version"))
        pos = skip_leading_nodes(children, pos + 1)
    # 5.
    description = doc.createElement("description")
    description.appendChild(doc.createTextNode("\n"))
    newchildren.append(description)
    move_children(descriptor, description, pos)
    last = description.childNodes[-1]
    if last.nodeType == TEXT:
        last.data = string.rstrip(last.data) + "\n  "
    # 6.
    # should have nothing but whitespace and signature lines in <descriptor>;
    # discard them
    while descriptor.childNodes:
        descriptor.removeChild(descriptor.childNodes[0])
    for node in newchildren:
        descriptor.appendChild(doc.createTextNode("\n  "))
        descriptor.appendChild(node)
    descriptor.appendChild(doc.createTextNode("\n"))


def methodline_to_signature(doc, methodline):
    signature = doc.createElement("signature")
    signature.appendChild(doc.createTextNode("\n    "))
    name = doc.createElement("name")
    name.appendChild(doc.createTextNode(methodline.getAttribute("name")))
    methodline.removeAttribute("name")
    signature.appendChild(name)
    if len(methodline.childNodes):
        args = doc.createElement("args")
        signature.appendChild(doc.createTextNode("\n    "))
        signature.appendChild(args)
        move_children(methodline, args)
    signature.appendChild(doc.createTextNode("\n  "))
    return signature


def move_children(origin, dest, start=0):
    children = origin.childNodes
    while start < len(children):
        node = children[start]
        origin.removeChild(node)
        dest.appendChild(node)


def handle_appendix(doc, fragment):
    # must be called after simplfy() if document is multi-rooted to begin with
    docelem = get_documentElement(fragment)
    toplevel = docelem.tagName == "manual" and "chapter" or "section"
    appendices = 0
    nodes = []
    for node in docelem.childNodes:
        if appendices:
            nodes.append(node)
        elif node.nodeType == ELEMENT:
            appnodes = node.getElementsByTagName("appendix")
            if appnodes:
                appendices = 1
                parent = appnodes[0].parentNode
                parent.removeChild(appnodes[0])
                parent.normalize()
    if nodes:
        map(docelem.removeChild, nodes)
        docelem.appendChild(doc.createTextNode("\n\n\n"))
        back = doc.createElement("back-matter")
        docelem.appendChild(back)
        back.appendChild(doc.createTextNode("\n"))
        while nodes and nodes[0].nodeType == TEXT \
              and not string.strip(nodes[0].data):
            del nodes[0]
        map(back.appendChild, nodes)
        docelem.appendChild(doc.createTextNode("\n"))


def handle_labels(doc, fragment):
    for label in find_all_elements(fragment, "label"):
        id = label.getAttribute("id")
        if not id:
            continue
        parent = label.parentNode
        parentTagName = parent.tagName
        if parentTagName == "title":
            parent.parentNode.setAttribute("id", id)
        else:
            parent.setAttribute("id", id)
        # now, remove <label id="..."/> from parent:
        parent.removeChild(label)
        if parentTagName == "title":
            parent.normalize()
            children = parent.childNodes
            if children[-1].nodeType == TEXT:
                children[-1].data = string.rstrip(children[-1].data)


def fixup_trailing_whitespace(doc, wsmap):
    queue = [doc]
    while queue:
        node = queue[0]
        del queue[0]
        if wsmap.has_key(node.nodeName):
            ws = wsmap[node.tagName]
            children = node.childNodes
            children.reverse()
            if children[0].nodeType == TEXT:
                data = string.rstrip(children[0].data) + ws
                children[0].data = data
            children.reverse()
            # hack to get the title in place:
            if node.tagName == "title" \
               and node.parentNode.firstChild.nodeType == ELEMENT:
                node.parentNode.insertBefore(doc.createText("\n  "),
                                             node.parentNode.firstChild)
        for child in node.childNodes:
            if child.nodeType == ELEMENT:
                queue.append(child)


def normalize(doc):
    for node in doc.childNodes:
        if node.nodeType == ELEMENT:
            node.normalize()


def cleanup_trailing_parens(doc, element_names):
    d = {}
    for gi in element_names:
        d[gi] = gi
    rewrite_element = d.has_key
    queue = []
    for node in doc.childNodes:
        if node.nodeType == ELEMENT:
            queue.append(node)
    while queue:
        node = queue[0]
        del queue[0]
        if rewrite_element(node.tagName):
            children = node.childNodes
            if len(children) == 1 \
               and children[0].nodeType == TEXT:
                data = children[0].data
                if data[-2:] == "()":
                    children[0].data = data[:-2]
        else:
            for child in node.childNodes:
                if child.nodeType == ELEMENT:
                    queue.append(child)


def contents_match(left, right):
    left_children = left.childNodes
    right_children = right.childNodes
    if len(left_children) != len(right_children):
        return 0
    for l, r in map(None, left_children, right_children):
        nodeType = l.nodeType
        if nodeType != r.nodeType:
            return 0
        if nodeType == ELEMENT:
            if l.tagName != r.tagName:
                return 0
            # should check attributes, but that's not a problem here
            if not contents_match(l, r):
                return 0
        elif nodeType == TEXT:
            if l.data != r.data:
                return 0
        else:
            # not quite right, but good enough
            return 0
    return 1


def create_module_info(doc, section):
    # Heavy.
    node = extract_first_element(section, "modulesynopsis")
    if node is None:
        return
    set_tagName(node, "synopsis")
    lastchild = node.childNodes[-1]
    if lastchild.nodeType == TEXT \
       and lastchild.data[-1:] == ".":
        lastchild.data = lastchild.data[:-1]
    modauthor = extract_first_element(section, "moduleauthor")
    if modauthor:
        set_tagName(modauthor, "author")
        modauthor.appendChild(doc.createTextNode(
            modauthor.getAttribute("name")))
        modauthor.removeAttribute("name")
    platform = extract_first_element(section, "platform")
    if section.tagName == "section":
        modinfo_pos = 2
        modinfo = doc.createElement("moduleinfo")
        moddecl = extract_first_element(section, "declaremodule")
        name = None
        if moddecl:
            modinfo.appendChild(doc.createTextNode("\n    "))
            name = moddecl.attributes["name"].value
            namenode = doc.createElement("name")
            namenode.appendChild(doc.createTextNode(name))
            modinfo.appendChild(namenode)
            type = moddecl.attributes.get("type")
            if type:
                type = type.value
                modinfo.appendChild(doc.createTextNode("\n    "))
                typenode = doc.createElement("type")
                typenode.appendChild(doc.createTextNode(type))
                modinfo.appendChild(typenode)
        versionadded = extract_first_element(section, "versionadded")
        if versionadded:
            modinfo.setAttribute("added", versionadded.getAttribute("version"))
        title = get_first_element(section, "title")
        if title:
            children = title.childNodes
            if len(children) >= 2 \
               and children[0].nodeName == "module" \
               and children[0].childNodes[0].data == name:
                # this is it; morph the <title> into <short-synopsis>
                first_data = children[1]
                if first_data.data[:4] == " ---":
                    first_data.data = string.lstrip(first_data.data[4:])
                set_tagName(title, "short-synopsis")
                if children[-1].nodeType == TEXT \
                   and children[-1].data[-1:] == ".":
                    children[-1].data = children[-1].data[:-1]
                section.removeChild(title)
                section.removeChild(section.childNodes[0])
                title.removeChild(children[0])
                modinfo_pos = 0
            else:
                ewrite("module name in title doesn't match"
                       " <declaremodule/>; no <short-synopsis/>\n")
        else:
            ewrite("Unexpected condition: <section/> without <title/>\n")
        modinfo.appendChild(doc.createTextNode("\n    "))
        modinfo.appendChild(node)
        if title and not contents_match(title, node):
            # The short synopsis is actually different,
            # and needs to be stored:
            modinfo.appendChild(doc.createTextNode("\n    "))
            modinfo.appendChild(title)
        if modauthor:
            modinfo.appendChild(doc.createTextNode("\n    "))
            modinfo.appendChild(modauthor)
        if platform:
            modinfo.appendChild(doc.createTextNode("\n    "))
            modinfo.appendChild(platform)
        modinfo.appendChild(doc.createTextNode("\n  "))
        section.insertBefore(modinfo, section.childNodes[modinfo_pos])
        section.insertBefore(doc.createTextNode("\n  "), modinfo)
        #
        # The rest of this removes extra newlines from where we cut out
        # a lot of elements.  A lot of code for minimal value, but keeps
        # keeps the generated *ML from being too funny looking.
        #
        section.normalize()
        children = section.childNodes
        for i in range(len(children)):
            node = children[i]
            if node.nodeName == "moduleinfo":
                nextnode = children[i+1]
                if nextnode.nodeType == TEXT:
                    data = nextnode.data
                    if len(string.lstrip(data)) < (len(data) - 4):
                        nextnode.data = "\n\n\n" + string.lstrip(data)


def cleanup_synopses(doc, fragment):
    for node in find_all_elements(fragment, "section"):
        create_module_info(doc, node)


def fixup_table_structures(doc, fragment):
    for table in find_all_elements(fragment, "table"):
        fixup_table(doc, table)


def fixup_table(doc, table):
    # create the table head
    thead = doc.createElement("thead")
    row = doc.createElement("row")
    move_elements_by_name(doc, table, row, "entry")
    thead.appendChild(doc.createTextNode("\n    "))
    thead.appendChild(row)
    thead.appendChild(doc.createTextNode("\n    "))
    # create the table body
    tbody = doc.createElement("tbody")
    prev_row = None
    last_was_hline = 0
    children = table.childNodes
    for child in children:
        if child.nodeType == ELEMENT:
            tagName = child.tagName
            if tagName == "hline" and prev_row is not None:
                prev_row.setAttribute("rowsep", "1")
            elif tagName == "row":
                prev_row = child
    # save the rows:
    tbody.appendChild(doc.createTextNode("\n    "))
    move_elements_by_name(doc, table, tbody, "row", sep="\n    ")
    # and toss the rest:
    while children:
        child = children[0]
        nodeType = child.nodeType
        if nodeType == TEXT:
            if string.strip(child.data):
                raise ConversionError("unexpected free data in <%s>: %r"
                                      % (table.tagName, child.data))
            table.removeChild(child)
            continue
        if nodeType == ELEMENT:
            if child.tagName != "hline":
                raise ConversionError(
                    "unexpected <%s> in table" % child.tagName)
            table.removeChild(child)
            continue
        raise ConversionError(
            "unexpected %s node in table" % child.__class__.__name__)
    # nothing left in the <table>; add the <thead> and <tbody>
    tgroup = doc.createElement("tgroup")
    tgroup.appendChild(doc.createTextNode("\n  "))
    tgroup.appendChild(thead)
    tgroup.appendChild(doc.createTextNode("\n  "))
    tgroup.appendChild(tbody)
    tgroup.appendChild(doc.createTextNode("\n  "))
    table.appendChild(tgroup)
    # now make the <entry>s look nice:
    for row in table.getElementsByTagName("row"):
        fixup_row(doc, row)


def fixup_row(doc, row):
    entries = []
    map(entries.append, row.childNodes[1:])
    for entry in entries:
        row.insertBefore(doc.createTextNode("\n         "), entry)
#    row.appendChild(doc.createTextNode("\n      "))


def move_elements_by_name(doc, source, dest, name, sep=None):
    nodes = []
    for child in source.childNodes:
        if child.nodeName == name:
            nodes.append(child)
    for node in nodes:
        source.removeChild(node)
        dest.appendChild(node)
        if sep:
            dest.appendChild(doc.createTextNode(sep))


RECURSE_INTO_PARA_CONTAINERS = (
    "chapter", "abstract", "enumerate",
    "section", "subsection", "subsubsection",
    "paragraph", "subparagraph", "back-matter",
    "howto", "manual",
    "item", "itemize", "fulllineitems", "enumeration", "descriptionlist",
    "definitionlist", "definition",
    )

PARA_LEVEL_ELEMENTS = (
    "moduleinfo", "title", "verbatim", "enumerate", "item",
    "interpreter-session", "back-matter", "interactive-session",
    "opcodedesc", "classdesc", "datadesc",
    "funcdesc", "methoddesc", "excdesc", "memberdesc", "membderdescni",
    "funcdescni", "methoddescni", "excdescni",
    "tableii", "tableiii", "tableiv", "localmoduletable",
    "sectionauthor", "seealso", "itemize",
    # include <para>, so we can just do it again to get subsequent paras:
    PARA_ELEMENT,
    )

PARA_LEVEL_PRECEEDERS = (
    "setindexsubitem", "author",
    "stindex", "obindex", "COMMENT", "label", "input", "title",
    "versionadded", "versionchanged", "declaremodule", "modulesynopsis",
    "moduleauthor", "indexterm", "leader",
    )


def fixup_paras(doc, fragment):
    for child in fragment.childNodes:
        if child.nodeName in RECURSE_INTO_PARA_CONTAINERS:
            fixup_paras_helper(doc, child)
    descriptions = find_all_elements(fragment, "description")
    for description in descriptions:
        fixup_paras_helper(doc, description)


def fixup_paras_helper(doc, container, depth=0):
    # document is already normalized
    children = container.childNodes
    start = skip_leading_nodes(children)
    while len(children) > start:
        if children[start].nodeName in RECURSE_INTO_PARA_CONTAINERS:
            # Something to recurse into:
            fixup_paras_helper(doc, children[start])
        else:
            # Paragraph material:
            build_para(doc, container, start, len(children))
            if DEBUG_PARA_FIXER and depth == 10:
                sys.exit(1)
        start = skip_leading_nodes(children, start + 1)


def build_para(doc, parent, start, i):
    children = parent.childNodes
    after = start + 1
    have_last = 0
    BREAK_ELEMENTS = PARA_LEVEL_ELEMENTS + RECURSE_INTO_PARA_CONTAINERS
    # Collect all children until \n\n+ is found in a text node or a
    # member of BREAK_ELEMENTS is found.
    for j in range(start, i):
        after = j + 1
        child = children[j]
        nodeType = child.nodeType
        if nodeType == ELEMENT:
            if child.tagName in BREAK_ELEMENTS:
                after = j
                break
        elif nodeType == TEXT:
            pos = string.find(child.data, "\n\n")
            if pos == 0:
                after = j
                break
            if pos >= 1:
                child.splitText(pos)
                break
    else:
        have_last = 1
    if (start + 1) > after:
        raise ConversionError(
            "build_para() could not identify content to turn into a paragraph")
    if children[after - 1].nodeType == TEXT:
        # we may need to split off trailing white space:
        child = children[after - 1]
        data = child.data
        if string.rstrip(data) != data:
            have_last = 0
            child.splitText(len(string.rstrip(data)))
    para = doc.createElement(PARA_ELEMENT)
    prev = None
    indexes = range(start, after)
    indexes.reverse()
    for j in indexes:
        node = parent.childNodes[j]
        parent.removeChild(node)
        para.insertBefore(node, prev)
        prev = node
    if have_last:
        parent.appendChild(para)
        parent.appendChild(doc.createTextNode("\n\n"))
        return len(parent.childNodes)
    else:
        nextnode = parent.childNodes[start]
        if nextnode.nodeType == TEXT:
            if nextnode.data and nextnode.data[0] != "\n":
                nextnode.data = "\n" + nextnode.data
        else:
            newnode = doc.createTextNode("\n")
            parent.insertBefore(newnode, nextnode)
            nextnode = newnode
            start = start + 1
        parent.insertBefore(para, nextnode)
        return start + 1


def skip_leading_nodes(children, start=0):
    """Return index into children of a node at which paragraph building should
    begin or a recursive call to fixup_paras_helper() should be made (for
    subsections, etc.).

    When the return value >= len(children), we've built all the paras we can
    from this list of children.
    """
    i = len(children)
    while i > start:
        # skip over leading comments and whitespace:
        child = children[start]
        nodeType = child.nodeType
        if nodeType == TEXT:
            data = child.data
            shortened = string.lstrip(data)
            if shortened:
                if data != shortened:
                    # break into two nodes: whitespace and non-whitespace
                    child.splitText(len(data) - len(shortened))
                    return start + 1
                return start
            # all whitespace, just skip
        elif nodeType == ELEMENT:
            tagName = child.tagName
            if tagName in RECURSE_INTO_PARA_CONTAINERS:
                return start
            if tagName not in PARA_LEVEL_ELEMENTS + PARA_LEVEL_PRECEEDERS:
                return start
        start = start + 1
    return start


def fixup_rfc_references(doc, fragment):
    for rfcnode in find_all_elements(fragment, "rfc"):
        rfcnode.appendChild(doc.createTextNode(
            "RFC " + rfcnode.getAttribute("num")))


def fixup_signatures(doc, fragment):
    for child in fragment.childNodes:
        if child.nodeType == ELEMENT:
            args = child.getElementsByTagName("args")
            for arg in args:
                fixup_args(doc, arg)
                arg.normalize()
            args = child.getElementsByTagName("constructor-args")
            for arg in args:
                fixup_args(doc, arg)
                arg.normalize()


def fixup_args(doc, arglist):
    for child in arglist.childNodes:
        if child.nodeName == "optional":
            # found it; fix and return
            arglist.insertBefore(doc.createTextNode("["), child)
            optkids = child.childNodes
            while optkids:
                k = optkids[0]
                child.removeChild(k)
                arglist.insertBefore(k, child)
            arglist.insertBefore(doc.createTextNode("]"), child)
            arglist.removeChild(child)
            return fixup_args(doc, arglist)


def fixup_sectionauthors(doc, fragment):
    for sectauth in find_all_elements(fragment, "sectionauthor"):
        section = sectauth.parentNode
        section.removeChild(sectauth)
        set_tagName(sectauth, "author")
        sectauth.appendChild(doc.createTextNode(
            sectauth.getAttribute("name")))
        sectauth.removeAttribute("name")
        after = section.childNodes[2]
        title = section.childNodes[1]
        if title.nodeName != "title":
            after = section.childNodes[0]
        section.insertBefore(doc.createTextNode("\n  "), after)
        section.insertBefore(sectauth, after)


def fixup_verbatims(doc):
    for verbatim in find_all_elements(doc, "verbatim"):
        child = verbatim.childNodes[0]
        if child.nodeType == TEXT \
           and string.lstrip(child.data)[:3] == ">>>":
            set_tagName(verbatim, "interactive-session")


def add_node_ids(fragment, counter=0):
    fragment.node_id = counter
    for node in fragment.childNodes:
        counter = counter + 1
        if node.nodeType == ELEMENT:
            counter = add_node_ids(node, counter)
        else:
            node.node_id = counter
    return counter + 1


REFMODINDEX_ELEMENTS = ('refmodindex', 'refbimodindex',
                        'refexmodindex', 'refstmodindex')

def fixup_refmodindexes(fragment):
    # Locate <ref*modindex>...</> co-located with <module>...</>, and
    # remove the <ref*modindex>, replacing it with index=index on the
    # <module> element.
    nodes = find_all_elements_from_set(fragment, REFMODINDEX_ELEMENTS)
    d = {}
    for node in nodes:
        parent = node.parentNode
        d[parent.node_id] = parent
    del nodes
    map(fixup_refmodindexes_chunk, d.values())


def fixup_refmodindexes_chunk(container):
    # node is probably a <para>; let's see how often it isn't:
    if container.tagName != PARA_ELEMENT:
        bwrite("--- fixup_refmodindexes_chunk(%s)\n" % container)
    module_entries = find_all_elements(container, "module")
    if not module_entries:
        return
    index_entries = find_all_elements_from_set(container, REFMODINDEX_ELEMENTS)
    removes = []
    for entry in index_entries:
        children = entry.childNodes
        if len(children) != 0:
            bwrite("--- unexpected number of children for %s node:\n"
                   % entry.tagName)
            ewrite(entry.toxml() + "\n")
            continue
        found = 0
        module_name = entry.getAttribute("module")
        for node in module_entries:
            if len(node.childNodes) != 1:
                continue
            this_name = node.childNodes[0].data
            if this_name == module_name:
                found = 1
                node.setAttribute("index", "yes")
        if found:
            removes.append(entry)
    for node in removes:
        container.removeChild(node)


def fixup_bifuncindexes(fragment):
    nodes = find_all_elements(fragment, 'bifuncindex')
    d = {}
    # make sure that each parent is only processed once:
    for node in nodes:
        parent = node.parentNode
        d[parent.node_id] = parent
    del nodes
    map(fixup_bifuncindexes_chunk, d.values())


def fixup_bifuncindexes_chunk(container):
    removes = []
    entries = find_all_child_elements(container, "bifuncindex")
    function_entries = find_all_child_elements(container, "function")
    for entry in entries:
        function_name = entry.getAttribute("name")
        found = 0
        for func_entry in function_entries:
            t2 = func_entry.childNodes[0].data
            if t2[-2:] != "()":
                continue
            t2 = t2[:-2]
            if t2 == function_name:
                func_entry.setAttribute("index", "yes")
                func_entry.setAttribute("module", "__builtin__")
                if not found:
                    found = 1
                    removes.append(entry)
    for entry in removes:
        container.removeChild(entry)


def join_adjacent_elements(container, gi):
    queue = [container]
    while queue:
        parent = queue.pop()
        i = 0
        children = parent.childNodes
        nchildren = len(children)
        while i < (nchildren - 1):
            child = children[i]
            if child.nodeName == gi:
                if children[i+1].nodeName == gi:
                    ewrite("--- merging two <%s/> elements\n" % gi)
                    child = children[i]
                    nextchild = children[i+1]
                    nextchildren = nextchild.childNodes
                    while len(nextchildren):
                        node = nextchildren[0]
                        nextchild.removeChild(node)
                        child.appendChild(node)
                    parent.removeChild(nextchild)
                    continue
            if child.nodeType == ELEMENT:
                queue.append(child)
            i = i + 1


_token_rx = re.compile(r"[a-zA-Z][a-zA-Z0-9.-]*$")

def write_esis(doc, ofp, knownempty):
    for node in doc.childNodes:
        nodeType = node.nodeType
        if nodeType == ELEMENT:
            gi = node.tagName
            if knownempty(gi):
                if node.hasChildNodes():
                    raise ValueError, \
                          "declared-empty node <%s> has children" % gi
                ofp.write("e\n")
            for k, value in node.attributes.items():
                if _token_rx.match(value):
                    dtype = "TOKEN"
                else:
                    dtype = "CDATA"
                ofp.write("A%s %s %s\n" % (k, dtype, esistools.encode(value)))
            ofp.write("(%s\n" % gi)
            write_esis(node, ofp, knownempty)
            ofp.write(")%s\n" % gi)
        elif nodeType == TEXT:
            ofp.write("-%s\n" % esistools.encode(node.data))
        elif nodeType == ENTITY_REFERENCE:
            ofp.write("&%s\n" % node.nodeName)
        else:
            raise RuntimeError, "unsupported node type: %s" % nodeType


def convert(ifp, ofp):
    events = esistools.parse(ifp)
    toktype, doc = events.getEvent()
    fragment = doc.createDocumentFragment()
    events.expandNode(fragment)

    normalize(fragment)
    simplify(doc, fragment)
    handle_labels(doc, fragment)
    handle_appendix(doc, fragment)
    fixup_trailing_whitespace(doc, {
        "abstract": "\n",
        "title": "",
        "chapter": "\n\n",
        "section": "\n\n",
        "subsection": "\n\n",
        "subsubsection": "\n\n",
        "paragraph": "\n\n",
        "subparagraph": "\n\n",
        })
    cleanup_root_text(doc)
    cleanup_trailing_parens(fragment, ["function", "method", "cfunction"])
    cleanup_synopses(doc, fragment)
    fixup_descriptors(doc, fragment)
    fixup_verbatims(fragment)
    normalize(fragment)
    fixup_paras(doc, fragment)
    fixup_sectionauthors(doc, fragment)
    fixup_table_structures(doc, fragment)
    fixup_rfc_references(doc, fragment)
    fixup_signatures(doc, fragment)
    add_node_ids(fragment)
    fixup_refmodindexes(fragment)
    fixup_bifuncindexes(fragment)
    # Take care of ugly hacks in the LaTeX markup to avoid LaTeX and
    # LaTeX2HTML screwing with GNU-style long options (the '--' problem).
    join_adjacent_elements(fragment, "option")
    #
    d = {}
    for gi in events.parser.get_empties():
        d[gi] = gi
    if d.has_key("author"):
        del d["author"]
    if d.has_key("rfc"):
        del d["rfc"]
    knownempty = d.has_key
    #
    try:
        write_esis(fragment, ofp, knownempty)
    except IOError, (err, msg):
        # Ignore EPIPE; it just means that whoever we're writing to stopped
        # reading.  The rest of the output would be ignored.  All other errors
        # should still be reported,
        if err != errno.EPIPE:
            raise


def main():
    if len(sys.argv) == 1:
        ifp = sys.stdin
        ofp = sys.stdout
    elif len(sys.argv) == 2:
        ifp = open(sys.argv[1])
        ofp = sys.stdout
    elif len(sys.argv) == 3:
        ifp = open(sys.argv[1])
        import StringIO
        ofp = StringIO.StringIO()
    else:
        usage()
        sys.exit(2)
    convert(ifp, ofp)
    if len(sys.argv) == 3:
        fp = open(sys.argv[2], "w")
        fp.write(ofp.getvalue())
        fp.close()
        ofp.close()


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = esis2sgml
#! /usr/bin/env python

"""Convert ESIS events to SGML or XML markup.

This is limited, but seems sufficient for the ESIS generated by the
latex2esis.py script when run over the Python documentation.
"""

# This should have an explicit option to indicate whether the *INPUT* was
# generated from an SGML or an XML application.

import errno
import esistools
import os
import re
import string

from xml.sax.saxutils import escape


AUTOCLOSE = ()

EMPTIES_FILENAME = "../sgml/empties.dat"
LIST_EMPTIES = 0


_elem_map = {}
_attr_map = {}
_token_map = {}

_normalize_case = str

def map_gi(sgmlgi, map):
    uncased = _normalize_case(sgmlgi)
    try:
        return map[uncased]
    except IndexError:
        map[uncased] = sgmlgi
        return sgmlgi

def null_map_gi(sgmlgi, map):
    return sgmlgi


def format_attrs(attrs, xml=0):
    attrs = attrs.items()
    attrs.sort()
    parts = []
    append = parts.append
    for name, value in attrs:
        if xml:
            append('%s="%s"' % (name, escape(value)))
        else:
            # this is a little bogus, but should do for now
            if name == value and isnmtoken(value):
                append(value)
            elif istoken(value):
                if value == "no" + name:
                    append(value)
                else:
                    append("%s=%s" % (name, value))
            else:
                append('%s="%s"' % (name, escape(value)))
    if parts:
        parts.insert(0, '')
    return string.join(parts)


_nmtoken_rx = re.compile("[a-z][-._a-z0-9]*$", re.IGNORECASE)
def isnmtoken(s):
    return _nmtoken_rx.match(s) is not None

_token_rx = re.compile("[a-z0-9][-._a-z0-9]*$", re.IGNORECASE)
def istoken(s):
    return _token_rx.match(s) is not None


def convert(ifp, ofp, xml=0, autoclose=(), verbatims=()):
    if xml:
        autoclose = ()
    attrs = {}
    lastopened = None
    knownempties = []
    knownempty = 0
    lastempty = 0
    inverbatim = 0
    while 1:
        line = ifp.readline()
        if not line:
            break

        type = line[0]
        data = line[1:]
        if data and data[-1] == "\n":
            data = data[:-1]
        if type == "-":
            data = esistools.decode(data)
            data = escape(data)
            if not inverbatim:
                data = string.replace(data, "---", "&mdash;")
            ofp.write(data)
            if "\n" in data:
                lastopened = None
            knownempty = 0
            lastempty = 0
        elif type == "(":
            if data == "COMMENT":
                ofp.write("<!--")
                continue
            data = map_gi(data, _elem_map)
            if knownempty and xml:
                ofp.write("<%s%s/>" % (data, format_attrs(attrs, xml)))
            else:
                ofp.write("<%s%s>" % (data, format_attrs(attrs, xml)))
            if knownempty and data not in knownempties:
                # accumulate knowledge!
                knownempties.append(data)
            attrs = {}
            lastopened = data
            lastempty = knownempty
            knownempty = 0
            inverbatim = data in verbatims
        elif type == ")":
            if data == "COMMENT":
                ofp.write("-->")
                continue
            data = map_gi(data, _elem_map)
            if xml:
                if not lastempty:
                    ofp.write("</%s>" % data)
            elif data not in knownempties:
                if data in autoclose:
                    pass
                elif lastopened == data:
                    ofp.write("</>")
                else:
                    ofp.write("</%s>" % data)
            lastopened = None
            lastempty = 0
            inverbatim = 0
        elif type == "A":
            name, type, value = string.split(data, " ", 2)
            name = map_gi(name, _attr_map)
            attrs[name] = esistools.decode(value)
        elif type == "e":
            knownempty = 1
        elif type == "&":
            ofp.write("&%s;" % data)
            knownempty = 0
        else:
            raise RuntimeError, "unrecognized ESIS event type: '%s'" % type

    if LIST_EMPTIES:
        dump_empty_element_names(knownempties)


def dump_empty_element_names(knownempties):
    d = {}
    for gi in knownempties:
        d[gi] = gi
    knownempties.append("")
    if os.path.isfile(EMPTIES_FILENAME):
        fp = open(EMPTIES_FILENAME)
        while 1:
            line = fp.readline()
            if not line:
                break
            gi = string.strip(line)
            if gi:
                d[gi] = gi
    fp = open(EMPTIES_FILENAME, "w")
    gilist = d.keys()
    gilist.sort()
    fp.write(string.join(gilist, "\n"))
    fp.write("\n")
    fp.close()


def update_gi_map(map, names, fromsgml=1):
    for name in string.split(names, ","):
        if fromsgml:
            uncased = string.lower(name)
        else:
            uncased = name
        map[uncased] = name


def main():
    import getopt
    import sys
    #
    autoclose = AUTOCLOSE
    xml = 1
    xmldecl = 0
    elem_names = ''
    attr_names = ''
    value_names = ''
    verbatims = ('verbatim', 'interactive-session')
    opts, args = getopt.getopt(sys.argv[1:], "adesx",
                               ["autoclose=", "declare", "sgml", "xml",
                                "elements-map=", "attributes-map",
                                "values-map="])
    for opt, arg in opts:
        if opt in ("-d", "--declare"):
            xmldecl = 1
        elif opt == "-e":
            global LIST_EMPTIES
            LIST_EMPTIES = 1
        elif opt in ("-s", "--sgml"):
            xml = 0
        elif opt in ("-x", "--xml"):
            xml = 1
        elif opt in ("-a", "--autoclose"):
            autoclose = string.split(arg, ",")
        elif opt == "--elements-map":
            elem_names = ("%s,%s" % (elem_names, arg))[1:]
        elif opt == "--attributes-map":
            attr_names = ("%s,%s" % (attr_names, arg))[1:]
        elif opt == "--values-map":
            value_names = ("%s,%s" % (value_names, arg))[1:]
    #
    # open input streams:
    #
    if len(args) == 0:
        ifp = sys.stdin
        ofp = sys.stdout
    elif len(args) == 1:
        ifp = open(args[0])
        ofp = sys.stdout
    elif len(args) == 2:
        ifp = open(args[0])
        ofp = open(args[1], "w")
    else:
        usage()
        sys.exit(2)
    #
    # setup the name maps:
    #
    if elem_names or attr_names or value_names:
        # assume the origin was SGML; ignore case of the names from the ESIS
        # stream but set up conversion tables to get the case right on output
        global _normalize_case
        _normalize_case = string.lower
        update_gi_map(_elem_map, string.split(elem_names, ","))
        update_gi_map(_attr_map, string.split(attr_names, ","))
        update_gi_map(_values_map, string.split(value_names, ","))
    else:
        global map_gi
        map_gi = null_map_gi
    #
    # run the conversion:
    #
    try:
        if xml and xmldecl:
            opf.write('<?xml version="1.0" encoding="iso8859-1"?>\n')
        convert(ifp, ofp, xml=xml, autoclose=autoclose, verbatims=verbatims)
    except IOError, (err, msg):
        if err != errno.EPIPE:
            raise


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = esistools
"""Miscellaneous utility functions useful for dealing with ESIS streams."""

import re
import string

import xml.dom.pulldom

import xml.sax
import xml.sax.handler
import xml.sax.xmlreader


_data_match = re.compile(r"[^\\][^\\]*").match

def decode(s):
    r = ''
    while s:
        m = _data_match(s)
        if m:
            r = r + m.group()
            s = s[m.end():]
        elif s[1] == "\\":
            r = r + "\\"
            s = s[2:]
        elif s[1] == "n":
            r = r + "\n"
            s = s[2:]
        elif s[1] == "%":
            s = s[2:]
            n, s = s.split(";", 1)
            r = r + unichr(int(n))
        else:
            raise ValueError, "can't handle " + `s`
    return r


_charmap = {}
for c in map(chr, range(256)):
    _charmap[c] = c
_charmap["\n"] = r"\n"
_charmap["\\"] = r"\\"
del c

_null_join = ''.join
def encode(s):
    return _null_join(map(_charmap.get, s))


class ESISReader(xml.sax.xmlreader.XMLReader):
    """SAX Reader which reads from an ESIS stream.

    No verification of the document structure is performed by the
    reader; a general verifier could be used as the target
    ContentHandler instance.

    """
    _decl_handler = None
    _lexical_handler = None

    _public_id = None
    _system_id = None

    _buffer = ""
    _is_empty = 0
    _lineno = 0
    _started = 0

    def __init__(self, contentHandler=None, errorHandler=None):
        xml.sax.xmlreader.XMLReader.__init__(self)
        self._attrs = {}
        self._attributes = Attributes(self._attrs)
        self._locator = Locator()
        self._empties = {}
        if contentHandler:
            self.setContentHandler(contentHandler)
        if errorHandler:
            self.setErrorHandler(errorHandler)

    def get_empties(self):
        return self._empties.keys()

    #
    #  XMLReader interface
    #

    def parse(self, source):
        raise RuntimeError
        self._locator._public_id = source.getPublicId()
        self._locator._system_id = source.getSystemId()
        fp = source.getByteStream()
        handler = self.getContentHandler()
        if handler:
            handler.startDocument()
        lineno = 0
        while 1:
            token, data = self._get_token(fp)
            if token is None:
                break
            lineno = lineno + 1
            self._locator._lineno = lineno
            self._handle_token(token, data)
        handler = self.getContentHandler()
        if handler:
            handler.startDocument()

    def feed(self, data):
        if not self._started:
            handler = self.getContentHandler()
            if handler:
                handler.startDocument()
            self._started = 1
        data = self._buffer + data
        self._buffer = None
        lines = data.split("\n")
        if lines:
            for line in lines[:-1]:
                self._lineno = self._lineno + 1
                self._locator._lineno = self._lineno
                if not line:
                    e = xml.sax.SAXParseException(
                        "ESIS input line contains no token type mark",
                        None, self._locator)
                    self.getErrorHandler().error(e)
                else:
                    self._handle_token(line[0], line[1:])
            self._buffer = lines[-1]
        else:
            self._buffer = ""

    def close(self):
        handler = self.getContentHandler()
        if handler:
            handler.endDocument()
        self._buffer = ""

    def _get_token(self, fp):
        try:
            line = fp.readline()
        except IOError, e:
            e = SAXException("I/O error reading input stream", e)
            self.getErrorHandler().fatalError(e)
            return
        if not line:
            return None, None
        if line[-1] == "\n":
            line = line[:-1]
        if not line:
            e = xml.sax.SAXParseException(
                "ESIS input line contains no token type mark",
                None, self._locator)
            self.getErrorHandler().error(e)
            return
        return line[0], line[1:]

    def _handle_token(self, token, data):
        handler = self.getContentHandler()
        if token == '-':
            if data and handler:
                handler.characters(decode(data))
        elif token == ')':
            if handler:
                handler.endElement(decode(data))
        elif token == '(':
            if self._is_empty:
                self._empties[data] = 1
            if handler:
                handler.startElement(data, self._attributes)
            self._attrs.clear()
            self._is_empty = 0
        elif token == 'A':
            name, value = data.split(' ', 1)
            if value != "IMPLIED":
                type, value = value.split(' ', 1)
                self._attrs[name] = (decode(value), type)
        elif token == '&':
            # entity reference in SAX?
            pass
        elif token == '?':
            if handler:
                if ' ' in data:
                    target, data = string.split(data, None, 1)
                else:
                    target, data = data, ""
                handler.processingInstruction(target, decode(data))
        elif token == 'N':
            handler = self.getDTDHandler()
            if handler:
                handler.notationDecl(data, self._public_id, self._system_id)
            self._public_id = None
            self._system_id = None
        elif token == 'p':
            self._public_id = decode(data)
        elif token == 's':
            self._system_id = decode(data)
        elif token == 'e':
            self._is_empty = 1
        elif token == 'C':
            pass
        else:
            e = SAXParseException("unknown ESIS token in event stream",
                                  None, self._locator)
            self.getErrorHandler().error(e)

    def setContentHandler(self, handler):
        old = self.getContentHandler()
        if old:
            old.setDocumentLocator(None)
        if handler:
            handler.setDocumentLocator(self._locator)
        xml.sax.xmlreader.XMLReader.setContentHandler(self, handler)

    def getProperty(self, property):
        if property == xml.sax.handler.property_lexical_handler:
            return self._lexical_handler

        elif property == xml.sax.handler.property_declaration_handler:
            return self._decl_handler

        else:
            raise xml.sax.SAXNotRecognizedException("unknown property %s"
                                                    % `property`)

    def setProperty(self, property, value):
        if property == xml.sax.handler.property_lexical_handler:
            if self._lexical_handler:
                self._lexical_handler.setDocumentLocator(None)
            if value:
                value.setDocumentLocator(self._locator)
            self._lexical_handler = value

        elif property == xml.sax.handler.property_declaration_handler:
            if self._decl_handler:
                self._decl_handler.setDocumentLocator(None)
            if value:
                value.setDocumentLocator(self._locator)
            self._decl_handler = value

        else:
            raise xml.sax.SAXNotRecognizedException()

    def getFeature(self, feature):
        if feature == xml.sax.handler.feature_namespaces:
            return 1
        else:
            return xml.sax.xmlreader.XMLReader.getFeature(self, feature)

    def setFeature(self, feature, enabled):
        if feature == xml.sax.handler.feature_namespaces:
            pass
        else:
            xml.sax.xmlreader.XMLReader.setFeature(self, feature, enabled)


class Attributes(xml.sax.xmlreader.AttributesImpl):
    # self._attrs has the form {name: (value, type)}

    def getType(self, name):
        return self._attrs[name][1]

    def getValue(self, name):
        return self._attrs[name][0]

    def getValueByQName(self, name):
        return self._attrs[name][0]

    def __getitem__(self, name):
        return self._attrs[name][0]

    def get(self, name, default=None):
        if self._attrs.has_key(name):
            return self._attrs[name][0]
        return default

    def items(self):
        L = []
        for name, (value, type) in self._attrs.items():
            L.append((name, value))
        return L

    def values(self):
        L = []
        for value, type in self._attrs.values():
            L.append(value)
        return L


class Locator(xml.sax.xmlreader.Locator):
    _lineno = -1
    _public_id = None
    _system_id = None

    def getLineNumber(self):
        return self._lineno

    def getPublicId(self):
        return self._public_id

    def getSystemId(self):
        return self._system_id


def parse(stream_or_string, parser=None):
    if type(stream_or_string) in [type(""), type(u"")]:
        stream = open(stream_or_string)
    else:
        stream = stream_or_string
    if not parser:
        parser = ESISReader()
    return xml.dom.pulldom.DOMEventStream(stream, parser, (2 ** 14) - 20)

########NEW FILE########
__FILENAME__ = latex2esis
#! /usr/bin/env python

"""Generate ESIS events based on a LaTeX source document and
configuration data.

The conversion is not strong enough to work with arbitrary LaTeX
documents; it has only been designed to work with the highly stylized
markup used in the standard Python documentation.  A lot of
information about specific markup is encoded in the control table
passed to the convert() function; changing this table can allow this
tool to support additional LaTeX markups.

The format of the table is largely undocumented; see the commented
headers where the table is specified in main().  There is no provision 
to load an alternate table from an external file.
"""

import errno
import getopt
import os
import re
import string
import sys
import UserList
import xml.sax.saxutils

from types import ListType, StringType, TupleType

try:
    from xml.parsers.xmllib import XMLParser
except ImportError:
    from xmllib import XMLParser


from esistools import encode


DEBUG = 0


class LaTeXFormatError(Exception):
    pass


class LaTeXStackError(LaTeXFormatError):
    def __init__(self, found, stack):
        msg = "environment close for %s doesn't match;\n  stack = %s" \
              % (found, stack)
        self.found = found
        self.stack = stack[:]
        LaTeXFormatError.__init__(self, msg)


_begin_env_rx = re.compile(r"[\\]begin{([^}]*)}")
_end_env_rx = re.compile(r"[\\]end{([^}]*)}")
_begin_macro_rx = re.compile(r"[\\]([a-zA-Z]+[*]?) ?({|\s*\n?)")
_comment_rx = re.compile("%+ ?(.*)\n[ \t]*")
_text_rx = re.compile(r"[^]~%\\{}]+")
_optional_rx = re.compile(r"\s*[[]([^]]*)[]]")
# _parameter_rx is this complicated to allow {...} inside a parameter;
# this is useful to match tabular layout specifications like {c|p{24pt}}
_parameter_rx = re.compile("[ \n]*{(([^{}}]|{[^}]*})*)}")
_token_rx = re.compile(r"[a-zA-Z][a-zA-Z0-9.-]*$")
_start_group_rx = re.compile("[ \n]*{")
_start_optional_rx = re.compile("[ \n]*[[]")


ESCAPED_CHARS = "$%#^ {}&~"


def dbgmsg(msg):
    if DEBUG:
        sys.stderr.write(msg + "\n")

def pushing(name, point, depth):
    dbgmsg("pushing <%s> at %s" % (name, point))

def popping(name, point, depth):
    dbgmsg("popping </%s> at %s" % (name, point))


class _Stack(UserList.UserList):
    def append(self, entry):
        if type(entry) is not StringType:
            raise LaTeXFormatError("cannot push non-string on stack: "
                                   + `entry`)
        #dbgmsg("%s<%s>" % (" "*len(self.data), entry))
        self.data.append(entry)

    def pop(self, index=-1):
        entry = self.data[index]
        del self.data[index]
        #dbgmsg("%s</%s>" % (" "*len(self.data), entry))

    def __delitem__(self, index):
        entry = self.data[index]
        del self.data[index]
        #dbgmsg("%s</%s>" % (" "*len(self.data), entry))


def new_stack():
    if DEBUG:
        return _Stack()
    return []


class Conversion:
    def __init__(self, ifp, ofp, table):
        self.write = ofp.write
        self.ofp = ofp
        self.table = table
        self.line = string.join(map(string.rstrip, ifp.readlines()), "\n")
        self.preamble = 1

    def convert(self):
        self.subconvert()

    def subconvert(self, endchar=None, depth=0):
        #
        # Parses content, including sub-structures, until the character
        # 'endchar' is found (with no open structures), or until the end
        # of the input data is endchar is None.
        #
        stack = new_stack()
        line = self.line
        while line:
            if line[0] == endchar and not stack:
                self.line = line
                return line
            m = _comment_rx.match(line)
            if m:
                text = m.group(1)
                if text:
                    self.write("(COMMENT\n- %s \n)COMMENT\n-\\n\n"
                               % encode(text))
                line = line[m.end():]
                continue
            m = _begin_env_rx.match(line)
            if m:
                name = m.group(1)
                entry = self.get_env_entry(name)
                # re-write to use the macro handler
                line = r"\%s %s" % (name, line[m.end():])
                continue
            m = _end_env_rx.match(line)
            if m:
                # end of environment
                envname = m.group(1)
                entry = self.get_entry(envname)
                while stack and envname != stack[-1] \
                      and stack[-1] in entry.endcloses:
                    self.write(")%s\n" % stack.pop())
                if stack and envname == stack[-1]:
                    self.write(")%s\n" % entry.outputname)
                    del stack[-1]
                else:
                    raise LaTeXStackError(envname, stack)
                line = line[m.end():]
                continue
            m = _begin_macro_rx.match(line)
            if m:
                # start of macro
                macroname = m.group(1)
                if macroname == "c":
                    # Ugh!  This is a combining character...
                    endpos = m.end()
                    self.combining_char("c", line[endpos])
                    line = line[endpos + 1:]
                    continue
                entry = self.get_entry(macroname)
                if entry.verbatim:
                    # magic case!
                    pos = string.find(line, "\\end{%s}" % macroname)
                    text = line[m.end(1):pos]
                    stack.append(entry.name)
                    self.write("(%s\n" % entry.outputname)
                    self.write("-%s\n" % encode(text))
                    self.write(")%s\n" % entry.outputname)
                    stack.pop()
                    line = line[pos + len("\\end{%s}" % macroname):]
                    continue
                while stack and stack[-1] in entry.closes:
                    top = stack.pop()
                    topentry = self.get_entry(top)
                    if topentry.outputname:
                        self.write(")%s\n-\\n\n" % topentry.outputname)
                #
                if entry.outputname:
                    if entry.empty:
                        self.write("e\n")
                #
                params, optional, empty, environ = self.start_macro(macroname)
                # rip off the macroname
                if params:
                    line = line[m.end(1):]
                elif empty:
                    line = line[m.end(1):]
                else:
                    line = line[m.end():]
                opened = 0
                implied_content = 0

                # handle attribute mappings here:
                for pentry in params:
                    if pentry.type == "attribute":
                        if pentry.optional:
                            m = _optional_rx.match(line)
                            if m and entry.outputname:
                                line = line[m.end():]
                                self.dump_attr(pentry, m.group(1))
                        elif pentry.text and entry.outputname:
                            # value supplied by conversion spec:
                            self.dump_attr(pentry, pentry.text)
                        else:
                            m = _parameter_rx.match(line)
                            if not m:
                                raise LaTeXFormatError(
                                    "could not extract parameter %s for %s: %s"
                                    % (pentry.name, macroname, `line[:100]`))
                            if entry.outputname:
                                self.dump_attr(pentry, m.group(1))
                            line = line[m.end():]
                    elif pentry.type == "child":
                        if pentry.optional:
                            m = _optional_rx.match(line)
                            if m:
                                line = line[m.end():]
                                if entry.outputname and not opened:
                                    opened = 1
                                    self.write("(%s\n" % entry.outputname)
                                    stack.append(macroname)
                                stack.append(pentry.name)
                                self.write("(%s\n" % pentry.name)
                                self.write("-%s\n" % encode(m.group(1)))
                                self.write(")%s\n" % pentry.name)
                                stack.pop()
                        else:
                            if entry.outputname and not opened:
                                opened = 1
                                self.write("(%s\n" % entry.outputname)
                                stack.append(entry.name)
                            self.write("(%s\n" % pentry.name)
                            stack.append(pentry.name)
                            self.line = skip_white(line)[1:]
                            line = self.subconvert(
                                "}", len(stack) + depth + 1)[1:]
                            self.write(")%s\n" % stack.pop())
                    elif pentry.type == "content":
                        if pentry.implied:
                            implied_content = 1
                        else:
                            if entry.outputname and not opened:
                                opened = 1
                                self.write("(%s\n" % entry.outputname)
                                stack.append(entry.name)
                            line = skip_white(line)
                            if line[0] != "{":
                                raise LaTeXFormatError(
                                    "missing content for " + macroname)
                            self.line = line[1:]
                            line = self.subconvert("}", len(stack) + depth + 1)
                            if line and line[0] == "}":
                                line = line[1:]
                    elif pentry.type == "text" and pentry.text:
                        if entry.outputname and not opened:
                            opened = 1
                            stack.append(entry.name)
                            self.write("(%s\n" % entry.outputname)
                        #dbgmsg("--- text: %s" % `pentry.text`)
                        self.write("-%s\n" % encode(pentry.text))
                    elif pentry.type == "entityref":
                        self.write("&%s\n" % pentry.name)
                if entry.outputname:
                    if not opened:
                        self.write("(%s\n" % entry.outputname)
                        stack.append(entry.name)
                    if not implied_content:
                        self.write(")%s\n" % entry.outputname)
                        stack.pop()
                continue
            if line[0] == endchar and not stack:
                self.line = line[1:]
                return self.line
            if line[0] == "}":
                # end of macro or group
                macroname = stack[-1]
                if macroname:
                    conversion = self.table[macroname]
                    if conversion.outputname:
                        # otherwise, it was just a bare group
                        self.write(")%s\n" % conversion.outputname)
                del stack[-1]
                line = line[1:]
                continue
            if line[0] == "~":
                # don't worry about the "tie" aspect of this command
                line = line[1:]
                self.write("- \n")
                continue
            if line[0] == "{":
                stack.append("")
                line = line[1:]
                continue
            if line[0] == "\\" and line[1] in ESCAPED_CHARS:
                self.write("-%s\n" % encode(line[1]))
                line = line[2:]
                continue
            if line[:2] == r"\\":
                self.write("(BREAK\n)BREAK\n")
                line = line[2:]
                continue
            if line[:2] == r"\_":
                line = "_" + line[2:]
                continue
            if line[:2] in (r"\'", r'\"'):
                # combining characters...
                self.combining_char(line[1], line[2])
                line = line[3:]
                continue
            m = _text_rx.match(line)
            if m:
                text = encode(m.group())
                self.write("-%s\n" % text)
                line = line[m.end():]
                continue
            # special case because of \item[]
            # XXX can we axe this???
            if line[0] == "]":
                self.write("-]\n")
                line = line[1:]
                continue
            # avoid infinite loops
            extra = ""
            if len(line) > 100:
                extra = "..."
            raise LaTeXFormatError("could not identify markup: %s%s"
                                   % (`line[:100]`, extra))
        while stack:
            entry = self.get_entry(stack[-1])
            if entry.closes:
                self.write(")%s\n-%s\n" % (entry.outputname, encode("\n")))
                del stack[-1]
            else:
                break
        if stack:
            raise LaTeXFormatError("elements remain on stack: "
                                   + string.join(stack, ", "))
        # otherwise we just ran out of input here...

    # This is a really limited table of combinations, but it will have
    # to do for now.
    _combinations = {
        ("c", "c"): 0x00E7,
        ("'", "e"): 0x00E9,
        ('"', "o"): 0x00F6,
        }

    def combining_char(self, prefix, char):
        ordinal = self._combinations[(prefix, char)]
        self.write("-\\%%%d;\n" % ordinal)

    def start_macro(self, name):
        conversion = self.get_entry(name)
        parameters = conversion.parameters
        optional = parameters and parameters[0].optional
        return parameters, optional, conversion.empty, conversion.environment

    def get_entry(self, name):
        entry = self.table.get(name)
        if entry is None:
            dbgmsg("get_entry(%s) failing; building default entry!" % `name`)
            # not defined; build a default entry:
            entry = TableEntry(name)
            entry.has_content = 1
            entry.parameters.append(Parameter("content"))
            self.table[name] = entry
        return entry

    def get_env_entry(self, name):
        entry = self.table.get(name)
        if entry is None:
            # not defined; build a default entry:
            entry = TableEntry(name, 1)
            entry.has_content = 1
            entry.parameters.append(Parameter("content"))
            entry.parameters[-1].implied = 1
            self.table[name] = entry
        elif not entry.environment:
            raise LaTeXFormatError(
                name + " is defined as a macro; expected environment")
        return entry

    def dump_attr(self, pentry, value):
        if not (pentry.name and value):
            return
        if _token_rx.match(value):
            dtype = "TOKEN"
        else:
            dtype = "CDATA"
        self.write("A%s %s %s\n" % (pentry.name, dtype, encode(value)))


def convert(ifp, ofp, table):
    c = Conversion(ifp, ofp, table)
    try:
        c.convert()
    except IOError, (err, msg):
        if err != errno.EPIPE:
            raise


def skip_white(line):
    while line and line[0] in " %\n\t\r":
        line = string.lstrip(line[1:])
    return line



class TableEntry:
    def __init__(self, name, environment=0):
        self.name = name
        self.outputname = name
        self.environment = environment
        self.empty = not environment
        self.has_content = 0
        self.verbatim = 0
        self.auto_close = 0
        self.parameters = []
        self.closes = []
        self.endcloses = []

class Parameter:
    def __init__(self, type, name=None, optional=0):
        self.type = type
        self.name = name
        self.optional = optional
        self.text = ''
        self.implied = 0


class TableParser(XMLParser):
    def __init__(self, table=None):
        if table is None:
            table = {}
        self.__table = table
        self.__current = None
        self.__buffer = ''
        XMLParser.__init__(self)

    def get_table(self):
        for entry in self.__table.values():
            if entry.environment and not entry.has_content:
                p = Parameter("content")
                p.implied = 1
                entry.parameters.append(p)
                entry.has_content = 1
        return self.__table

    def start_environment(self, attrs):
        name = attrs["name"]
        self.__current = TableEntry(name, environment=1)
        self.__current.verbatim = attrs.get("verbatim") == "yes"
        if attrs.has_key("outputname"):
            self.__current.outputname = attrs.get("outputname")
        self.__current.endcloses = string.split(attrs.get("endcloses", ""))
    def end_environment(self):
        self.end_macro()

    def start_macro(self, attrs):
        name = attrs["name"]
        self.__current = TableEntry(name)
        self.__current.closes = string.split(attrs.get("closes", ""))
        if attrs.has_key("outputname"):
            self.__current.outputname = attrs.get("outputname")
    def end_macro(self):
        self.__table[self.__current.name] = self.__current
        self.__current = None

    def start_attribute(self, attrs):
        name = attrs.get("name")
        optional = attrs.get("optional") == "yes"
        if name:
            p = Parameter("attribute", name, optional=optional)
        else:
            p = Parameter("attribute", optional=optional)
        self.__current.parameters.append(p)
        self.__buffer = ''
    def end_attribute(self):
        self.__current.parameters[-1].text = self.__buffer

    def start_entityref(self, attrs):
        name = attrs["name"]
        p = Parameter("entityref", name)
        self.__current.parameters.append(p)

    def start_child(self, attrs):
        name = attrs["name"]
        p = Parameter("child", name, attrs.get("optional") == "yes")
        self.__current.parameters.append(p)
        self.__current.empty = 0

    def start_content(self, attrs):
        p = Parameter("content")
        p.implied = attrs.get("implied") == "yes"
        if self.__current.environment:
            p.implied = 1
        self.__current.parameters.append(p)
        self.__current.has_content = 1
        self.__current.empty = 0

    def start_text(self, attrs):
        self.__current.empty = 0
        self.__buffer = ''
    def end_text(self):
        p = Parameter("text")
        p.text = self.__buffer
        self.__current.parameters.append(p)

    def handle_data(self, data):
        self.__buffer = self.__buffer + data


def load_table(fp, table=None):
    parser = TableParser(table=table)
    parser.feed(fp.read())
    parser.close()
    return parser.get_table()


def main():
    global DEBUG
    #
    opts, args = getopt.getopt(sys.argv[1:], "D", ["debug"])
    for opt, arg in opts:
        if opt in ("-D", "--debug"):
            DEBUG = DEBUG + 1
    if len(args) == 0:
        ifp = sys.stdin
        ofp = sys.stdout
    elif len(args) == 1:
        ifp = open(args)
        ofp = sys.stdout
    elif len(args) == 2:
        ifp = open(args[0])
        ofp = open(args[1], "w")
    else:
        usage()
        sys.exit(2)

    table = load_table(open(os.path.join(sys.path[0], 'conversion.xml')))
    convert(ifp, ofp, table)


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = support
"""Miscellaneous support code shared by some of the tool scripts.

This includes option parsing code, HTML formatting code, and a couple of
useful helpers.

"""
__version__ = '$Revision: 1.1.1.1 $'


import getopt
import string
import sys


class Options:
    __short_args = "a:c:ho:"
    __long_args = [
        # script controls
        "columns=", "help", "output=",

        # content components
        "address=", "iconserver=",
        "title=", "uplink=", "uptitle="]

    outputfile = "-"
    columns = 1
    letters = 0
    uplink = "./"
    uptitle = "Python Documentation Index"

    def __init__(self):
        self.args = []
        self.variables = {"address": "",
                          "iconserver": "icons",
                          "imgtype": "gif",
                          "title": "Global Module Index",
                          }

    def add_args(self, short=None, long=None):
        if short:
            self.__short_args = self.__short_args + short
        if long:
            self.__long_args = self.__long_args + long

    def parse(self, args):
        try:
            opts, args = getopt.getopt(args, self.__short_args,
                                       self.__long_args)
        except getopt.error:
            sys.stdout = sys.stderr
            self.usage()
            sys.exit(2)
        self.args = self.args + args
        for opt, val in opts:
            if opt in ("-a", "--address"):
                val = string.strip(val)
                if val:
                    val = "<address>\n%s\n</address>\n" % val
                    self.variables["address"] = val
            elif opt in ("-h", "--help"):
                self.usage()
                sys.exit()
            elif opt in ("-o", "--output"):
                self.outputfile = val
            elif opt in ("-c", "--columns"):
                self.columns = int(val)
            elif opt == "--title":
                self.variables["title"] = val.strip()
            elif opt == "--uplink":
                self.uplink = val.strip()
            elif opt == "--uptitle":
                self.uptitle = val.strip()
            elif opt == "--iconserver":
                self.variables["iconserver"] = val.strip() or "."
            else:
                self.handle_option(opt, val)
        if self.uplink and self.uptitle:
            self.variables["uplinkalt"] = "up"
            self.variables["uplinkicon"] = "up"
        else:
            self.variables["uplinkalt"] = ""
            self.variables["uplinkicon"] = "blank"
        self.variables["uplink"] = self.uplink
        self.variables["uptitle"] = self.uptitle

    def handle_option(self, opt, val):
        raise getopt.error("option %s not recognized" % opt)

    def get_header(self):
        return HEAD % self.variables

    def get_footer(self):
        return TAIL % self.variables

    def get_output_file(self, filename=None):
        if filename is None:
            filename = self.outputfile
        if filename == "-":
            return sys.stdout
        else:
            return open(filename, "w")


NAVIGATION = '''\
<div class="navigation">
<table width="100%%" cellpadding="0" cellspacing="2">
<tr>
<td><img width="32" height="32" align="bottom" border="0" alt=""
 src="%(iconserver)s/blank.%(imgtype)s"></td>
<td><a href="%(uplink)s"
 title="%(uptitle)s"><img width="32" height="32" align="bottom" border="0"
 alt="%(uplinkalt)s"
 src="%(iconserver)s/%(uplinkicon)s.%(imgtype)s"></a></td>
<td><img width="32" height="32" align="bottom" border="0" alt=""
 src="%(iconserver)s/blank.%(imgtype)s"></td>
<td align="center" width="100%%">%(title)s</td>
<td><img width="32" height="32" align="bottom" border="0" alt=""
 src="%(iconserver)s/blank.%(imgtype)s"></td>
<td><img width="32" height="32" align="bottom" border="0" alt=""
 src="%(iconserver)s/blank.%(imgtype)s"></td>
<td><img width="32" height="32" align="bottom" border="0" alt=""
 src="%(iconserver)s/blank.%(imgtype)s"></td>
</tr></table>
<b class="navlabel">Up:</b> <span class="sectref"><a href="%(uplink)s"
 title="%(uptitle)s">%(uptitle)s</A></span>
<br></div>
'''

HEAD = '''\
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">
<html>
<head>
  <title>%(title)s</title>
  <meta name="description" content="%(title)s">
  <meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1">
  <link rel="STYLESHEET" href="lib/lib.css">
</head>
<body>
''' + NAVIGATION + '''\
<hr>

<h2>%(title)s</h2>

'''

TAIL = "<hr>\n" + NAVIGATION + '''\
%(address)s</body>
</html>
'''

########NEW FILE########
__FILENAME__ = toc2bkm
#! /usr/bin/env python

"""Convert a LaTeX .toc file to some PDFTeX magic to create that neat outline.

The output file has an extension of '.bkm' instead of '.out', since hyperref
already uses that extension.
"""

import getopt
import os
import re
import string
import sys


# Ench item in an entry is a tuple of:
#
#   Section #,  Title String,  Page #,  List of Sub-entries
#
# The return value of parse_toc() is such a tuple.

cline_re = r"""^
\\contentsline\ \{([a-z]*)}             # type of section in $1
\{(?:\\numberline\ \{([0-9.A-Z]+)})?     # section number
(.*)}                                   # title string
\{(\d+)}$"""                            # page number

cline_rx = re.compile(cline_re, re.VERBOSE)

OUTER_TO_INNER = -1

_transition_map = {
    ('chapter', 'section'): OUTER_TO_INNER,
    ('section', 'subsection'): OUTER_TO_INNER,
    ('subsection', 'subsubsection'): OUTER_TO_INNER,
    ('subsubsection', 'subsection'): 1,
    ('subsection', 'section'): 1,
    ('section', 'chapter'): 1,
    ('subsection', 'chapter'): 2,
    ('subsubsection', 'section'): 2,
    ('subsubsection', 'chapter'): 3,
    }

INCLUDED_LEVELS = ("chapter", "section", "subsection", "subsubsection")


def parse_toc(fp, bigpart=None):
    toc = top = []
    stack = [toc]
    level = bigpart or 'chapter'
    lineno = 0
    while 1:
        line = fp.readline()
        if not line:
            break
        lineno = lineno + 1
        m = cline_rx.match(line)
        if m:
            stype, snum, title, pageno = m.group(1, 2, 3, 4)
            title = clean_title(title)
            entry = (stype, snum, title, string.atoi(pageno), [])
            if stype == level:
                toc.append(entry)
            else:
                if stype not in INCLUDED_LEVELS:
                    # we don't want paragraphs & subparagraphs
                    continue
                direction = _transition_map[(level, stype)]
                if direction == OUTER_TO_INNER:
                    toc = toc[-1][-1]
                    stack.insert(0, toc)
                    toc.append(entry)
                else:
                    for i in range(direction):
                        del stack[0]
                        toc = stack[0]
                    toc.append(entry)
                level = stype
        else:
            sys.stderr.write("l.%s: " + line)
    return top


hackscore_rx = re.compile(r"\\hackscore\s*{[^}]*}")
raisebox_rx = re.compile(r"\\raisebox\s*{[^}]*}")
title_rx = re.compile(r"\\([a-zA-Z])+\s+")
title_trans = string.maketrans("", "")

def clean_title(title):
    title = raisebox_rx.sub("", title)
    title = hackscore_rx.sub(r"\\_", title)
    pos = 0
    while 1:
        m = title_rx.search(title, pos)
        if m:
            start = m.start()
            if title[start:start+15] != "\\textunderscore":
                title = title[:start] + title[m.end():]
            pos = start + 1
        else:
            break
    title = string.translate(title, title_trans, "{}")
    return title


def write_toc(toc, fp):
    for entry in toc:
        write_toc_entry(entry, fp, 0)

def write_toc_entry(entry, fp, layer):
    stype, snum, title, pageno, toc = entry
    s = "\\pdfoutline goto name{page%03d}" % pageno
    if toc:
        s = "%s count -%d" % (s, len(toc))
    if snum:
        title = "%s %s" % (snum, title)
    s = "%s {%s}\n" % (s, title)
    fp.write(s)
    for entry in toc:
        write_toc_entry(entry, fp, layer + 1)


def process(ifn, ofn, bigpart=None):
    toc = parse_toc(open(ifn), bigpart)
    write_toc(toc, open(ofn, "w"))


def main():
    bigpart = None
    opts, args = getopt.getopt(sys.argv[1:], "c:")
    if opts:
        bigpart = opts[0][1]
    if not args:
        usage()
        sys.exit(2)
    for filename in args:
        base, ext = os.path.splitext(filename)
        ext = ext or ".toc"
        process(base + ext, base + ".bkm", bigpart)


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = certgen
# -*- coding: latin-1 -*-
#
# Copyright (C) AB Strakt
# Copyright (C) Jean-Paul Calderone
# See LICENSE for details.

"""
Certificate generation module.
"""

from OpenSSL import crypto

TYPE_RSA = crypto.TYPE_RSA
TYPE_DSA = crypto.TYPE_DSA

def createKeyPair(type, bits):
    """
    Create a public/private key pair.

    Arguments: type - Key type, must be one of TYPE_RSA and TYPE_DSA
               bits - Number of bits to use in the key
    Returns:   The public/private key pair in a PKey object
    """
    pkey = crypto.PKey()
    pkey.generate_key(type, bits)
    return pkey

def createCertRequest(pkey, digest="md5", **name):
    """
    Create a certificate request.

    Arguments: pkey   - The key to associate with the request
               digest - Digestion method to use for signing, default is md5
               **name - The name of the subject of the request, possible
                        arguments are:
                          C     - Country name
                          ST    - State or province name
                          L     - Locality name
                          O     - Organization name
                          OU    - Organizational unit name
                          CN    - Common name
                          emailAddress - E-mail address
    Returns:   The certificate request in an X509Req object
    """
    req = crypto.X509Req()
    subj = req.get_subject()

    for (key,value) in name.items():
        setattr(subj, key, value)

    req.set_pubkey(pkey)
    req.sign(pkey, digest)
    return req

def createCertificate(req, (issuerCert, issuerKey), serial, (notBefore, notAfter), digest="md5"):
    """
    Generate a certificate given a certificate request.

    Arguments: req        - Certificate reqeust to use
               issuerCert - The certificate of the issuer
               issuerKey  - The private key of the issuer
               serial     - Serial number for the certificate
               notBefore  - Timestamp (relative to now) when the certificate
                            starts being valid
               notAfter   - Timestamp (relative to now) when the certificate
                            stops being valid
               digest     - Digest method to use for signing, default is md5
    Returns:   The signed certificate in an X509 object
    """
    cert = crypto.X509()
    cert.set_serial_number(serial)
    cert.gmtime_adj_notBefore(notBefore)
    cert.gmtime_adj_notAfter(notAfter)
    cert.set_issuer(issuerCert.get_subject())
    cert.set_subject(req.get_subject())
    cert.set_pubkey(req.get_pubkey())
    cert.sign(issuerKey, digest)
    return cert


########NEW FILE########
__FILENAME__ = mk_simple_certs
"""
Create certificates and private keys for the 'simple' example.
"""

from OpenSSL import crypto
from certgen import *   # yes yes, I know, I'm lazy
cakey = createKeyPair(TYPE_RSA, 1024)
careq = createCertRequest(cakey, CN='Certificate Authority')
cacert = createCertificate(careq, (careq, cakey), 0, (0, 60*60*24*365*5)) # five years
open('simple/CA.pkey', 'w').write(crypto.dump_privatekey(crypto.FILETYPE_PEM, cakey))
open('simple/CA.cert', 'w').write(crypto.dump_certificate(crypto.FILETYPE_PEM, cacert))
for (fname, cname) in [('client', 'Simple Client'), ('server', 'Simple Server')]:
    pkey = createKeyPair(TYPE_RSA, 1024)
    req = createCertRequest(pkey, CN=cname)
    cert = createCertificate(req, (cacert, cakey), 1, (0, 60*60*24*365*5)) # five years
    open('simple/%s.pkey' % (fname,), 'w').write(crypto.dump_privatekey(crypto.FILETYPE_PEM, pkey))
    open('simple/%s.cert' % (fname,), 'w').write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))

########NEW FILE########
__FILENAME__ = proxy
#!/usr/bin/env python
#
# This script demostrates how one can use pyOpenSSL to speak SSL over an HTTP
# proxy
# The challenge here is to start talking SSL over an already connected socket
#
# Author: Mihai Ibanescu <misa@redhat.com>
#
# $Id: proxy.py,v 1.2 2004/07/22 12:01:25 martin Exp $

import sys, socket, string
from OpenSSL import SSL

def usage(exit_code=0):
    print "Usage: %s server[:port] proxy[:port]" % sys.argv[0]
    print "  Connects SSL to the specified server (port 443 by default)"
    print "    using the specified proxy (port 8080 by default)"
    sys.exit(exit_code)

def main():
    # Command-line processing
    if len(sys.argv) != 3:
        usage(-1)

    server, proxy = sys.argv[1:3]

    run(split_host(server, 443), split_host(proxy, 8080))

def split_host(hostname, default_port=80):
    a = string.split(hostname, ':', 1)
    if len(a) == 1:
        a.append(default_port)
    return a[0], int(a[1])
    

# Connects to the server, through the proxy
def run(server, proxy):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect(proxy)
    except socket.error, e:
        print "Unable to connect to %s:%s %s" % (proxy[0], proxy[1], str(e))
        sys.exit(-1)

    # Use the CONNECT method to get a connection to the actual server
    s.send("CONNECT %s:%s HTTP/1.0\n\n" % (server[0], server[1]))
    print "Proxy response: %s" % string.strip(s.recv(1024))

    ctx = SSL.Context(SSL.SSLv23_METHOD)
    conn = SSL.Connection(ctx, s)

    # Go to client mode
    conn.set_connect_state()

    # start using HTTP

    conn.send("HEAD / HTTP/1.0\n\n")
    print "Sever response:"
    print "-" * 40
    while 1:
        try:
            buff = conn.recv(4096)
        except SSL.ZeroReturnError:
            # we're done
            break

        print buff,

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = SecureXMLRPCServer
"""
SecureXMLRPCServer module using pyOpenSSL 0.5
Written 0907.2002
by Michal Wallace
http://www.sabren.net/

This acts exactly like SimpleXMLRPCServer
from the standard python library, but
uses secure connections. The technique
and classes should work for any SocketServer
style server. However, the code has not
been extensively tested.

This code is in the public domain.
It is provided AS-IS WITH NO WARRANTY WHATSOEVER.
"""
import SocketServer
import os, socket
import SimpleXMLRPCServer
from OpenSSL import SSL

class SSLWrapper:
    """
    This whole class exists just to filter out a parameter
    passed in to the shutdown() method in SimpleXMLRPC.doPOST()
    """
    def __init__(self, conn):
        """
        Connection is not yet a new-style class,
        so I'm making a proxy instead of subclassing.
        """
        self.__dict__["conn"] = conn
    def __getattr__(self,name):
        return getattr(self.__dict__["conn"], name)
    def __setattr__(self,name, value):
        setattr(self.__dict__["conn"], name, value)
    def shutdown(self, how=1):
        """
        SimpleXMLRpcServer.doPOST calls shutdown(1),
        and Connection.shutdown() doesn't take
        an argument. So we just discard the argument.
        """
        self.__dict__["conn"].shutdown()
    def accept(self):
        """
        This is the other part of the shutdown() workaround.
        Since servers create new sockets, we have to infect
        them with our magic. :)
        """
        c, a = self.__dict__["conn"].accept()
        return (SSLWrapper(c), a)



class SecureTCPServer(SocketServer.TCPServer):
    """
    Just like TCPServer, but use a socket.
    This really ought to let you specify the key and certificate files.
    """
    def __init__(self, server_address, RequestHandlerClass):
        SocketServer.BaseServer.__init__(self, server_address, RequestHandlerClass)

        ## Same as normal, but make it secure:
        ctx = SSL.Context(SSL.SSLv23_METHOD)
        ctx.set_options(SSL.OP_NO_SSLv2)

        dir = os.curdir
        ctx.use_privatekey_file (os.path.join(dir, 'server.pkey'))
        ctx.use_certificate_file(os.path.join(dir, 'server.cert'))

        self.socket = SSLWrapper(SSL.Connection(ctx, socket.socket(self.address_family,
                                                                  self.socket_type)))
        self.server_bind()
        self.server_activate()


class SecureXMLRPCRequestHandler(SimpleXMLRPCServer.SimpleXMLRPCRequestHandler):
    def setup(self):
        """
        We need to use socket._fileobject Because SSL.Connection
        doesn't have a 'dup'. Not exactly sure WHY this is, but
        this is backed up by comments in socket.py and SSL/connection.c
        """
        self.connection = self.request # for doPOST
        self.rfile = socket._fileobject(self.request, "rb", self.rbufsize)
        self.wfile = socket._fileobject(self.request, "wb", self.wbufsize)
    

class SecureXMLRPCServer(SimpleXMLRPCServer.SimpleXMLRPCServer, SecureTCPServer):
    def __init__(self, addr,
                 requestHandler=SecureXMLRPCRequestHandler,
                 logRequests=1):
        """
        This is the exact same code as SimpleXMLRPCServer.__init__
        except it calls SecureTCPServer.__init__ instead of plain
        old TCPServer.__init__
        """
        self.funcs = {}
        self.logRequests = logRequests
        self.instance = None
        SecureTCPServer.__init__(self, addr, requestHandler)


########NEW FILE########
__FILENAME__ = client
# -*- coding: latin-1 -*-
#
# Copyright (C) AB Strakt
# Copyright (C) Jean-Paul Calderone
# See LICENSE for details.

"""
Simple SSL client, using blocking I/O
"""

from OpenSSL import SSL
import sys, os, select, socket

def verify_cb(conn, cert, errnum, depth, ok):
    # This obviously has to be updated
    print 'Got certificate: %s' % cert.get_subject()
    return ok

if len(sys.argv) < 3:
    print 'Usage: python[2] client.py HOST PORT'
    sys.exit(1)

dir = os.path.dirname(sys.argv[0])
if dir == '':
    dir = os.curdir

# Initialize context
ctx = SSL.Context(SSL.SSLv23_METHOD)
ctx.set_verify(SSL.VERIFY_PEER, verify_cb) # Demand a certificate
ctx.use_privatekey_file (os.path.join(dir, 'client.pkey'))
ctx.use_certificate_file(os.path.join(dir, 'client.cert'))
ctx.load_verify_locations(os.path.join(dir, 'CA.cert'))

# Set up client
sock = SSL.Connection(ctx, socket.socket(socket.AF_INET, socket.SOCK_STREAM))
sock.connect((sys.argv[1], int(sys.argv[2])))

while 1:
    line = sys.stdin.readline()
    if line == '':
        break
    try:
        sock.send(line)
        sys.stdout.write(sock.recv(1024))
        sys.stdout.flush()
    except SSL.Error:
        print 'Connection died unexpectedly'
        break


sock.shutdown()
sock.close()

########NEW FILE########
__FILENAME__ = server
# -*- coding: latin-1 -*-
#
# Copyright (C) AB Strakt
# Copyright (C) Jean-Paul Calderone
# See LICENSE for details.

"""
Simple echo server, using nonblocking I/O
"""

from OpenSSL import SSL
import sys, os, select, socket


def verify_cb(conn, cert, errnum, depth, ok):
    # This obviously has to be updated
    print 'Got certificate: %s' % cert.get_subject()
    return ok

if len(sys.argv) < 2:
    print 'Usage: python[2] server.py PORT'
    sys.exit(1)

dir = os.path.dirname(sys.argv[0])
if dir == '':
    dir = os.curdir

# Initialize context
ctx = SSL.Context(SSL.SSLv23_METHOD)
ctx.set_options(SSL.OP_NO_SSLv2)
ctx.set_verify(SSL.VERIFY_PEER|SSL.VERIFY_FAIL_IF_NO_PEER_CERT, verify_cb) # Demand a certificate
ctx.use_privatekey_file (os.path.join(dir, 'server.pkey'))
ctx.use_certificate_file(os.path.join(dir, 'server.cert'))
ctx.load_verify_locations(os.path.join(dir, 'CA.cert'))

# Set up server
server = SSL.Connection(ctx, socket.socket(socket.AF_INET, socket.SOCK_STREAM))
server.bind(('', int(sys.argv[1])))
server.listen(3) 
server.setblocking(0)

clients = {}
writers = {}

def dropClient(cli, errors=None):
    if errors:
        print 'Client %s left unexpectedly:' % (clients[cli],)
        print '  ', errors
    else:
        print 'Client %s left politely' % (clients[cli],)
    del clients[cli]
    if writers.has_key(cli):
        del writers[cli]
    if not errors:
        cli.shutdown()
    cli.close()

while 1:
    try:
        r,w,_ = select.select([server]+clients.keys(), writers.keys(), [])
    except:
        break

    for cli in r:
        if cli == server:
            cli,addr = server.accept()
            print 'Connection from %s' % (addr,)
            clients[cli] = addr

        else:
            try:
                ret = cli.recv(1024)
            except (SSL.WantReadError, SSL.WantWriteError, SSL.WantX509LookupError):
                pass
            except SSL.ZeroReturnError:
                dropClient(cli)
            except SSL.Error, errors:
                dropClient(cli, errors)
            else:
                if not writers.has_key(cli):
                    writers[cli] = ''
                writers[cli] = writers[cli] + ret

    for cli in w:
        try:
            ret = cli.send(writers[cli])
        except (SSL.WantReadError, SSL.WantWriteError, SSL.WantX509LookupError):
            pass
        except SSL.ZeroReturnError:
            dropClient(cli)
        except SSL.Error, errors:
            dropClient(cli, errors)
        else:
            writers[cli] = writers[cli][ret:]
            if writers[cli] == '':
                del writers[cli]

for cli in clients.keys():
    cli.close()
server.close()

########NEW FILE########
__FILENAME__ = client
# Copyright (C) Jean-Paul Calderone
# See LICENSE for details.

if __name__ == '__main__':
    import client
    raise SystemExit(client.main())

from sys import argv, stdout
from socket import socket

from OpenSSL.SSL import TLSv1_METHOD, Context, Connection

def main():
    """
    Connect to an SNI-enabled server and request a specific hostname, specified
    by argv[1], of it.
    """
    if len(argv) < 2:
        print 'Usage: %s <hostname>' % (argv[0],)
        return 1

    client = socket()

    print 'Connecting...',
    stdout.flush()
    client.connect(('127.0.0.1', 8443))
    print 'connected', client.getpeername()

    client_ssl = Connection(Context(TLSv1_METHOD), client)
    client_ssl.set_connect_state()
    client_ssl.set_tlsext_host_name(argv[1])
    client_ssl.do_handshake()
    print 'Server subject is', client_ssl.get_peer_certificate().get_subject()
    client_ssl.close()


########NEW FILE########
__FILENAME__ = server
# Copyright (C) Jean-Paul Calderone
# See LICENSE for details.

if __name__ == '__main__':
    import server
    raise SystemExit(server.main())

from sys import stdout
from socket import SOL_SOCKET, SO_REUSEADDR, socket

from OpenSSL.crypto import FILETYPE_PEM, load_privatekey, load_certificate
from OpenSSL.SSL import TLSv1_METHOD, Context, Connection

def load(domain):
    crt = open(domain + ".crt")
    key = open(domain + ".key")
    result = (
        load_privatekey(FILETYPE_PEM, key.read()),
        load_certificate(FILETYPE_PEM, crt.read()))
    crt.close()
    key.close()
    return result


def main():
    """
    Run an SNI-enabled server which selects between a few certificates in a
    C{dict} based on the handshake request it receives from a client.
    """
    port = socket()
    port.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    port.bind(('', 8443))
    port.listen(3)

    print 'Accepting...',
    stdout.flush()
    server, addr = port.accept()
    print 'accepted', addr

    server_context = Context(TLSv1_METHOD)
    server_context.set_tlsext_servername_callback(pick_certificate)

    server_ssl = Connection(server_context, server)
    server_ssl.set_accept_state()
    server_ssl.do_handshake()
    server.close()


certificates = {
    "example.invalid": load("example.invalid"),
    "another.invalid": load("another.invalid"),
    }


def pick_certificate(connection):
    try:
        key, cert = certificates[connection.get_servername()]
    except KeyError:
        pass
    else:
        new_context = Context(TLSv1_METHOD)
        new_context.use_privatekey(key)
        new_context.use_certificate(cert)
        connection.set_context(new_context)

########NEW FILE########
__FILENAME__ = test_crypto
# Copyright (c) Jean-Paul Calderone
# See LICENSE file for details.

"""
Unit tests for L{OpenSSL.crypto}.
"""

from unittest import main

import os, re
from subprocess import PIPE, Popen
from datetime import datetime, timedelta

from OpenSSL.crypto import TYPE_RSA, TYPE_DSA, Error, PKey, PKeyType
from OpenSSL.crypto import X509, X509Type, X509Name, X509NameType
from OpenSSL.crypto import X509Req, X509ReqType
from OpenSSL.crypto import X509Extension, X509ExtensionType
from OpenSSL.crypto import load_certificate, load_privatekey
from OpenSSL.crypto import FILETYPE_PEM, FILETYPE_ASN1, FILETYPE_TEXT
from OpenSSL.crypto import dump_certificate, load_certificate_request
from OpenSSL.crypto import dump_certificate_request, dump_privatekey
from OpenSSL.crypto import PKCS7Type, load_pkcs7_data
from OpenSSL.crypto import PKCS12, PKCS12Type, load_pkcs12
from OpenSSL.crypto import CRL, Revoked, load_crl
from OpenSSL.crypto import NetscapeSPKI, NetscapeSPKIType
from OpenSSL.crypto import sign, verify
from OpenSSL.test.util import TestCase, bytes, b

def normalize_certificate_pem(pem):
    return dump_certificate(FILETYPE_PEM, load_certificate(FILETYPE_PEM, pem))


def normalize_privatekey_pem(pem):
    return dump_privatekey(FILETYPE_PEM, load_privatekey(FILETYPE_PEM, pem))


root_cert_pem = b("""-----BEGIN CERTIFICATE-----
MIIC7TCCAlagAwIBAgIIPQzE4MbeufQwDQYJKoZIhvcNAQEFBQAwWDELMAkGA1UE
BhMCVVMxCzAJBgNVBAgTAklMMRAwDgYDVQQHEwdDaGljYWdvMRAwDgYDVQQKEwdU
ZXN0aW5nMRgwFgYDVQQDEw9UZXN0aW5nIFJvb3QgQ0EwIhgPMjAwOTAzMjUxMjM2
NThaGA8yMDE3MDYxMTEyMzY1OFowWDELMAkGA1UEBhMCVVMxCzAJBgNVBAgTAklM
MRAwDgYDVQQHEwdDaGljYWdvMRAwDgYDVQQKEwdUZXN0aW5nMRgwFgYDVQQDEw9U
ZXN0aW5nIFJvb3QgQ0EwgZ8wDQYJKoZIhvcNAQEBBQADgY0AMIGJAoGBAPmaQumL
urpE527uSEHdL1pqcDRmWzu+98Y6YHzT/J7KWEamyMCNZ6fRW1JCR782UQ8a07fy
2xXsKy4WdKaxyG8CcatwmXvpvRQ44dSANMihHELpANTdyVp6DCysED6wkQFurHlF
1dshEaJw8b/ypDhmbVIo6Ci1xvCJqivbLFnbAgMBAAGjgbswgbgwHQYDVR0OBBYE
FINVdy1eIfFJDAkk51QJEo3IfgSuMIGIBgNVHSMEgYAwfoAUg1V3LV4h8UkMCSTn
VAkSjch+BK6hXKRaMFgxCzAJBgNVBAYTAlVTMQswCQYDVQQIEwJJTDEQMA4GA1UE
BxMHQ2hpY2FnbzEQMA4GA1UEChMHVGVzdGluZzEYMBYGA1UEAxMPVGVzdGluZyBS
b290IENBggg9DMTgxt659DAMBgNVHRMEBTADAQH/MA0GCSqGSIb3DQEBBQUAA4GB
AGGCDazMJGoWNBpc03u6+smc95dEead2KlZXBATOdFT1VesY3+nUOqZhEhTGlDMi
hkgaZnzoIq/Uamidegk4hirsCT/R+6vsKAAxNTcBjUeZjlykCJWy5ojShGftXIKY
w/njVbKMXrvc83qmTdGl3TAM0fxQIpqgcglFLveEBgzn
-----END CERTIFICATE-----
""")

root_key_pem = b("""-----BEGIN RSA PRIVATE KEY-----
MIICXQIBAAKBgQD5mkLpi7q6ROdu7khB3S9aanA0Zls7vvfGOmB80/yeylhGpsjA
jWen0VtSQke/NlEPGtO38tsV7CsuFnSmschvAnGrcJl76b0UOOHUgDTIoRxC6QDU
3claegwsrBA+sJEBbqx5RdXbIRGicPG/8qQ4Zm1SKOgotcbwiaor2yxZ2wIDAQAB
AoGBAPCgMpmLxzwDaUmcFbTJUvlLW1hoxNNYSu2jIZm1k/hRAcE60JYwvBkgz3UB
yMEh0AtLxYe0bFk6EHah11tMUPgscbCq73snJ++8koUw+csk22G65hOs51bVb7Aa
6JBe67oLzdtvgCUFAA2qfrKzWRZzAdhUirQUZgySZk+Xq1pBAkEA/kZG0A6roTSM
BVnx7LnPfsycKUsTumorpXiylZJjTi9XtmzxhrYN6wgZlDOOwOLgSQhszGpxVoMD
u3gByT1b2QJBAPtL3mSKdvwRu/+40zaZLwvSJRxaj0mcE4BJOS6Oqs/hS1xRlrNk
PpQ7WJ4yM6ZOLnXzm2mKyxm50Mv64109FtMCQQDOqS2KkjHaLowTGVxwC0DijMfr
I9Lf8sSQk32J5VWCySWf5gGTfEnpmUa41gKTMJIbqZZLucNuDcOtzUaeWZlZAkA8
ttXigLnCqR486JDPTi9ZscoZkZ+w7y6e/hH8t6d5Vjt48JVyfjPIaJY+km58LcN3
6AWSeGAdtRFHVzR7oHjVAkB4hutvxiOeiIVQNBhM6RSI9aBPMI21DoX2JRoxvNW2
cbvAhow217X9V0dVerEOKxnNYspXRrh36h7k4mQA+sDq
-----END RSA PRIVATE KEY-----
""")

server_cert_pem = b("""-----BEGIN CERTIFICATE-----
MIICKDCCAZGgAwIBAgIJAJn/HpR21r/8MA0GCSqGSIb3DQEBBQUAMFgxCzAJBgNV
BAYTAlVTMQswCQYDVQQIEwJJTDEQMA4GA1UEBxMHQ2hpY2FnbzEQMA4GA1UEChMH
VGVzdGluZzEYMBYGA1UEAxMPVGVzdGluZyBSb290IENBMCIYDzIwMDkwMzI1MTIz
NzUzWhgPMjAxNzA2MTExMjM3NTNaMBgxFjAUBgNVBAMTDWxvdmVseSBzZXJ2ZXIw
gZ8wDQYJKoZIhvcNAQEBBQADgY0AMIGJAoGBAL6m+G653V0tpBC/OKl22VxOi2Cv
lK4TYu9LHSDP9uDVTe7V5D5Tl6qzFoRRx5pfmnkqT5B+W9byp2NU3FC5hLm5zSAr
b45meUhjEJ/ifkZgbNUjHdBIGP9MAQUHZa5WKdkGIJvGAvs8UzUqlr4TBWQIB24+
lJ+Ukk/CRgasrYwdAgMBAAGjNjA0MB0GA1UdDgQWBBS4kC7Ij0W1TZXZqXQFAM2e
gKEG2DATBgNVHSUEDDAKBggrBgEFBQcDATANBgkqhkiG9w0BAQUFAAOBgQBh30Li
dJ+NlxIOx5343WqIBka3UbsOb2kxWrbkVCrvRapCMLCASO4FqiKWM+L0VDBprqIp
2mgpFQ6FHpoIENGvJhdEKpptQ5i7KaGhnDNTfdy3x1+h852G99f1iyj0RmbuFcM8
uzujnS8YXWvM7DM1Ilozk4MzPug8jzFp5uhKCQ==
-----END CERTIFICATE-----
""")

server_key_pem = normalize_privatekey_pem(b("""-----BEGIN RSA PRIVATE KEY-----
MIICWwIBAAKBgQC+pvhuud1dLaQQvzipdtlcTotgr5SuE2LvSx0gz/bg1U3u1eQ+
U5eqsxaEUceaX5p5Kk+QflvW8qdjVNxQuYS5uc0gK2+OZnlIYxCf4n5GYGzVIx3Q
SBj/TAEFB2WuVinZBiCbxgL7PFM1Kpa+EwVkCAduPpSflJJPwkYGrK2MHQIDAQAB
AoGAbwuZ0AR6JveahBaczjfnSpiFHf+mve2UxoQdpyr6ROJ4zg/PLW5K/KXrC48G
j6f3tXMrfKHcpEoZrQWUfYBRCUsGD5DCazEhD8zlxEHahIsqpwA0WWssJA2VOLEN
j6DuV2pCFbw67rfTBkTSo32ahfXxEKev5KswZk0JIzH3ooECQQDgzS9AI89h0gs8
Dt+1m11Rzqo3vZML7ZIyGApUzVan+a7hbc33nbGRkAXjHaUBJO31it/H6dTO+uwX
msWwNG5ZAkEA2RyFKs5xR5USTFaKLWCgpH/ydV96KPOpBND7TKQx62snDenFNNbn
FwwOhpahld+vqhYk+pfuWWUpQciE+Bu7ZQJASjfT4sQv4qbbKK/scePicnDdx9th
4e1EeB9xwb+tXXXUo/6Bor/AcUNwfiQ6Zt9PZOK9sR3lMZSsP7rMi7kzuQJABie6
1sXXjFH7nNJvRG4S39cIxq8YRYTy68II/dlB2QzGpKxV/POCxbJ/zu0CU79tuYK7
NaeNCFfH3aeTrX0LyQJAMBWjWmeKM2G2sCExheeQK0ROnaBC8itCECD4Jsve4nqf
r50+LF74iLXFwqysVCebPKMOpDWp/qQ1BbJQIPs7/A==
-----END RSA PRIVATE KEY-----
"""))

client_cert_pem = b("""-----BEGIN CERTIFICATE-----
MIICJjCCAY+gAwIBAgIJAKxpFI5lODkjMA0GCSqGSIb3DQEBBQUAMFgxCzAJBgNV
BAYTAlVTMQswCQYDVQQIEwJJTDEQMA4GA1UEBxMHQ2hpY2FnbzEQMA4GA1UEChMH
VGVzdGluZzEYMBYGA1UEAxMPVGVzdGluZyBSb290IENBMCIYDzIwMDkwMzI1MTIz
ODA1WhgPMjAxNzA2MTExMjM4MDVaMBYxFDASBgNVBAMTC3VnbHkgY2xpZW50MIGf
MA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDAZh/SRtNm5ntMT4qb6YzEpTroMlq2
rn+GrRHRiZ+xkCw/CGNhbtPir7/QxaUj26BSmQrHw1bGKEbPsWiW7bdXSespl+xK
iku4G/KvnnmWdeJHqsiXeUZtqurMELcPQAw9xPHEuhqqUJvvEoMTsnCEqGM+7Dtb
oCRajYyHfluARQIDAQABozYwNDAdBgNVHQ4EFgQUNQB+qkaOaEVecf1J3TTUtAff
0fAwEwYDVR0lBAwwCgYIKwYBBQUHAwIwDQYJKoZIhvcNAQEFBQADgYEAyv/Jh7gM
Q3OHvmsFEEvRI+hsW8y66zK4K5de239Y44iZrFYkt7Q5nBPMEWDj4F2hLYWL/qtI
9Zdr0U4UDCU9SmmGYh4o7R4TZ5pGFvBYvjhHbkSFYFQXZxKUi+WUxplP6I0wr2KJ
PSTJCjJOn3xo2NTKRgV1gaoTf2EhL+RG8TQ=
-----END CERTIFICATE-----
""")

client_key_pem = normalize_privatekey_pem(b("""-----BEGIN RSA PRIVATE KEY-----
MIICXgIBAAKBgQDAZh/SRtNm5ntMT4qb6YzEpTroMlq2rn+GrRHRiZ+xkCw/CGNh
btPir7/QxaUj26BSmQrHw1bGKEbPsWiW7bdXSespl+xKiku4G/KvnnmWdeJHqsiX
eUZtqurMELcPQAw9xPHEuhqqUJvvEoMTsnCEqGM+7DtboCRajYyHfluARQIDAQAB
AoGATkZ+NceY5Glqyl4mD06SdcKfV65814vg2EL7V9t8+/mi9rYL8KztSXGlQWPX
zuHgtRoMl78yQ4ZJYOBVo+nsx8KZNRCEBlE19bamSbQLCeQMenWnpeYyQUZ908gF
h6L9qsFVJepgA9RDgAjyDoS5CaWCdCCPCH2lDkdcqC54SVUCQQDseuduc4wi8h4t
V8AahUn9fn9gYfhoNuM0gdguTA0nPLVWz4hy1yJiWYQe0H7NLNNTmCKiLQaJpAbb
TC6vE8C7AkEA0Ee8CMJUc20BnGEmxwgWcVuqFWaKCo8jTH1X38FlATUsyR3krjW2
dL3yDD9NwHxsYP7nTKp/U8MV7U9IBn4y/wJBAJl7H0/BcLeRmuJk7IqJ7b635iYB
D/9beFUw3MUXmQXZUfyYz39xf6CDZsu1GEdEC5haykeln3Of4M9d/4Kj+FcCQQCY
si6xwT7GzMDkk/ko684AV3KPc/h6G0yGtFIrMg7J3uExpR/VdH2KgwMkZXisSMvw
JJEQjOMCVsEJlRk54WWjAkEAzoZNH6UhDdBK5F38rVt/y4SEHgbSfJHIAmPS32Kq
f6GGcfNpip0Uk7q7udTKuX7Q/buZi/C4YW7u3VKAquv9NA==
-----END RSA PRIVATE KEY-----
"""))

cleartextCertificatePEM = b("""-----BEGIN CERTIFICATE-----
MIIC7TCCAlagAwIBAgIIPQzE4MbeufQwDQYJKoZIhvcNAQEFBQAwWDELMAkGA1UE
BhMCVVMxCzAJBgNVBAgTAklMMRAwDgYDVQQHEwdDaGljYWdvMRAwDgYDVQQKEwdU
ZXN0aW5nMRgwFgYDVQQDEw9UZXN0aW5nIFJvb3QgQ0EwIhgPMjAwOTAzMjUxMjM2
NThaGA8yMDE3MDYxMTEyMzY1OFowWDELMAkGA1UEBhMCVVMxCzAJBgNVBAgTAklM
MRAwDgYDVQQHEwdDaGljYWdvMRAwDgYDVQQKEwdUZXN0aW5nMRgwFgYDVQQDEw9U
ZXN0aW5nIFJvb3QgQ0EwgZ8wDQYJKoZIhvcNAQEBBQADgY0AMIGJAoGBAPmaQumL
urpE527uSEHdL1pqcDRmWzu+98Y6YHzT/J7KWEamyMCNZ6fRW1JCR782UQ8a07fy
2xXsKy4WdKaxyG8CcatwmXvpvRQ44dSANMihHELpANTdyVp6DCysED6wkQFurHlF
1dshEaJw8b/ypDhmbVIo6Ci1xvCJqivbLFnbAgMBAAGjgbswgbgwHQYDVR0OBBYE
FINVdy1eIfFJDAkk51QJEo3IfgSuMIGIBgNVHSMEgYAwfoAUg1V3LV4h8UkMCSTn
VAkSjch+BK6hXKRaMFgxCzAJBgNVBAYTAlVTMQswCQYDVQQIEwJJTDEQMA4GA1UE
BxMHQ2hpY2FnbzEQMA4GA1UEChMHVGVzdGluZzEYMBYGA1UEAxMPVGVzdGluZyBS
b290IENBggg9DMTgxt659DAMBgNVHRMEBTADAQH/MA0GCSqGSIb3DQEBBQUAA4GB
AGGCDazMJGoWNBpc03u6+smc95dEead2KlZXBATOdFT1VesY3+nUOqZhEhTGlDMi
hkgaZnzoIq/Uamidegk4hirsCT/R+6vsKAAxNTcBjUeZjlykCJWy5ojShGftXIKY
w/njVbKMXrvc83qmTdGl3TAM0fxQIpqgcglFLveEBgzn
-----END CERTIFICATE-----
""")

cleartextPrivateKeyPEM = normalize_privatekey_pem(b("""\
-----BEGIN RSA PRIVATE KEY-----
MIICXQIBAAKBgQD5mkLpi7q6ROdu7khB3S9aanA0Zls7vvfGOmB80/yeylhGpsjA
jWen0VtSQke/NlEPGtO38tsV7CsuFnSmschvAnGrcJl76b0UOOHUgDTIoRxC6QDU
3claegwsrBA+sJEBbqx5RdXbIRGicPG/8qQ4Zm1SKOgotcbwiaor2yxZ2wIDAQAB
AoGBAPCgMpmLxzwDaUmcFbTJUvlLW1hoxNNYSu2jIZm1k/hRAcE60JYwvBkgz3UB
yMEh0AtLxYe0bFk6EHah11tMUPgscbCq73snJ++8koUw+csk22G65hOs51bVb7Aa
6JBe67oLzdtvgCUFAA2qfrKzWRZzAdhUirQUZgySZk+Xq1pBAkEA/kZG0A6roTSM
BVnx7LnPfsycKUsTumorpXiylZJjTi9XtmzxhrYN6wgZlDOOwOLgSQhszGpxVoMD
u3gByT1b2QJBAPtL3mSKdvwRu/+40zaZLwvSJRxaj0mcE4BJOS6Oqs/hS1xRlrNk
PpQ7WJ4yM6ZOLnXzm2mKyxm50Mv64109FtMCQQDOqS2KkjHaLowTGVxwC0DijMfr
I9Lf8sSQk32J5VWCySWf5gGTfEnpmUa41gKTMJIbqZZLucNuDcOtzUaeWZlZAkA8
ttXigLnCqR486JDPTi9ZscoZkZ+w7y6e/hH8t6d5Vjt48JVyfjPIaJY+km58LcN3
6AWSeGAdtRFHVzR7oHjVAkB4hutvxiOeiIVQNBhM6RSI9aBPMI21DoX2JRoxvNW2
cbvAhow217X9V0dVerEOKxnNYspXRrh36h7k4mQA+sDq
-----END RSA PRIVATE KEY-----
"""))

cleartextCertificateRequestPEM = b("""-----BEGIN CERTIFICATE REQUEST-----
MIIBnjCCAQcCAQAwXjELMAkGA1UEBhMCVVMxCzAJBgNVBAgTAklMMRAwDgYDVQQH
EwdDaGljYWdvMRcwFQYDVQQKEw5NeSBDb21wYW55IEx0ZDEXMBUGA1UEAxMORnJl
ZGVyaWNrIERlYW4wgZ8wDQYJKoZIhvcNAQEBBQADgY0AMIGJAoGBANp6Y17WzKSw
BsUWkXdqg6tnXy8H8hA1msCMWpc+/2KJ4mbv5NyD6UD+/SqagQqulPbF/DFea9nA
E0zhmHJELcM8gUTIlXv/cgDWnmK4xj8YkjVUiCdqKRAKeuzLG1pGmwwF5lGeJpXN
xQn5ecR0UYSOWj6TTGXB9VyUMQzCClcBAgMBAAGgADANBgkqhkiG9w0BAQUFAAOB
gQAAJGuF/R/GGbeC7FbFW+aJgr9ee0Xbl6nlhu7pTe67k+iiKT2dsl2ti68MVTnu
Vrb3HUNqOkiwsJf6kCtq5oPn3QVYzTa76Dt2y3Rtzv6boRSlmlfrgS92GNma8JfR
oICQk3nAudi6zl1Dix3BCv1pUp5KMtGn3MeDEi6QFGy2rA==
-----END CERTIFICATE REQUEST-----
""")

encryptedPrivateKeyPEM = b("""-----BEGIN RSA PRIVATE KEY-----
Proc-Type: 4,ENCRYPTED
DEK-Info: DES-EDE3-CBC,9573604A18579E9E

SHOho56WxDkT0ht10UTeKc0F5u8cqIa01kzFAmETw0MAs8ezYtK15NPdCXUm3X/2
a17G7LSF5bkxOgZ7vpXyMzun/owrj7CzvLxyncyEFZWvtvzaAhPhvTJtTIB3kf8B
8+qRcpTGK7NgXEgYBW5bj1y4qZkD4zCL9o9NQzsKI3Ie8i0239jsDOWR38AxjXBH
mGwAQ4Z6ZN5dnmM4fhMIWsmFf19sNyAML4gHenQCHhmXbjXeVq47aC2ProInJbrm
+00TcisbAQ40V9aehVbcDKtS4ZbMVDwncAjpXpcncC54G76N6j7F7wL7L/FuXa3A
fvSVy9n2VfF/pJ3kYSflLHH2G/DFxjF7dl0GxhKPxJjp3IJi9VtuvmN9R2jZWLQF
tfC8dXgy/P9CfFQhlinqBTEwgH0oZ/d4k4NVFDSdEMaSdmBAjlHpc+Vfdty3HVnV
rKXj//wslsFNm9kIwJGIgKUa/n2jsOiydrsk1mgH7SmNCb3YHgZhbbnq0qLat/HC
gHDt3FHpNQ31QzzL3yrenFB2L9osIsnRsDTPFNi4RX4SpDgNroxOQmyzCCV6H+d4
o1mcnNiZSdxLZxVKccq0AfRpHqpPAFnJcQHP6xyT9MZp6fBa0XkxDnt9kNU8H3Qw
7SJWZ69VXjBUzMlQViLuaWMgTnL+ZVyFZf9hTF7U/ef4HMLMAVNdiaGG+G+AjCV/
MbzjS007Oe4qqBnCWaFPSnJX6uLApeTbqAxAeyCql56ULW5x6vDMNC3dwjvS/CEh
11n8RkgFIQA0AhuKSIg3CbuartRsJnWOLwgLTzsrKYL4yRog1RJrtw==
-----END RSA PRIVATE KEY-----
""")

encryptedPrivateKeyPEMPassphrase = b("foobar")

# Some PKCS#7 stuff.  Generated with the openssl command line:
#
#    openssl crl2pkcs7 -inform pem -outform pem -certfile s.pem -nocrl
#
# with a certificate and key (but the key should be irrelevant) in s.pem
pkcs7Data = b("""\
-----BEGIN PKCS7-----
MIIDNwYJKoZIhvcNAQcCoIIDKDCCAyQCAQExADALBgkqhkiG9w0BBwGgggMKMIID
BjCCAm+gAwIBAgIBATANBgkqhkiG9w0BAQQFADB7MQswCQYDVQQGEwJTRzERMA8G
A1UEChMITTJDcnlwdG8xFDASBgNVBAsTC00yQ3J5cHRvIENBMSQwIgYDVQQDExtN
MkNyeXB0byBDZXJ0aWZpY2F0ZSBNYXN0ZXIxHTAbBgkqhkiG9w0BCQEWDm5ncHNA
cG9zdDEuY29tMB4XDTAwMDkxMDA5NTEzMFoXDTAyMDkxMDA5NTEzMFowUzELMAkG
A1UEBhMCU0cxETAPBgNVBAoTCE0yQ3J5cHRvMRIwEAYDVQQDEwlsb2NhbGhvc3Qx
HTAbBgkqhkiG9w0BCQEWDm5ncHNAcG9zdDEuY29tMFwwDQYJKoZIhvcNAQEBBQAD
SwAwSAJBAKy+e3dulvXzV7zoTZWc5TzgApr8DmeQHTYC8ydfzH7EECe4R1Xh5kwI
zOuuFfn178FBiS84gngaNcrFi0Z5fAkCAwEAAaOCAQQwggEAMAkGA1UdEwQCMAAw
LAYJYIZIAYb4QgENBB8WHU9wZW5TU0wgR2VuZXJhdGVkIENlcnRpZmljYXRlMB0G
A1UdDgQWBBTPhIKSvnsmYsBVNWjj0m3M2z0qVTCBpQYDVR0jBIGdMIGagBT7hyNp
65w6kxXlxb8pUU/+7Sg4AaF/pH0wezELMAkGA1UEBhMCU0cxETAPBgNVBAoTCE0y
Q3J5cHRvMRQwEgYDVQQLEwtNMkNyeXB0byBDQTEkMCIGA1UEAxMbTTJDcnlwdG8g
Q2VydGlmaWNhdGUgTWFzdGVyMR0wGwYJKoZIhvcNAQkBFg5uZ3BzQHBvc3QxLmNv
bYIBADANBgkqhkiG9w0BAQQFAAOBgQA7/CqT6PoHycTdhEStWNZde7M/2Yc6BoJu
VwnW8YxGO8Sn6UJ4FeffZNcYZddSDKosw8LtPOeWoK3JINjAk5jiPQ2cww++7QGG
/g5NDjxFZNDJP1dGiLAxPW6JXwov4v0FmdzfLOZ01jDcgQQZqEpYlgpuI5JEWUQ9
Ho4EzbYCOaEAMQA=
-----END PKCS7-----
""")

crlData = b("""\
-----BEGIN X509 CRL-----
MIIBWzCBxTANBgkqhkiG9w0BAQQFADBYMQswCQYDVQQGEwJVUzELMAkGA1UECBMC
SUwxEDAOBgNVBAcTB0NoaWNhZ28xEDAOBgNVBAoTB1Rlc3RpbmcxGDAWBgNVBAMT
D1Rlc3RpbmcgUm9vdCBDQRcNMDkwNzI2MDQzNDU2WhcNMTIwOTI3MDI0MTUyWjA8
MBUCAgOrGA8yMDA5MDcyNTIzMzQ1NlowIwICAQAYDzIwMDkwNzI1MjMzNDU2WjAM
MAoGA1UdFQQDCgEEMA0GCSqGSIb3DQEBBAUAA4GBAEBt7xTs2htdD3d4ErrcGAw1
4dKcVnIWTutoI7xxen26Wwvh8VCsT7i/UeP+rBl9rC/kfjWjzQk3/zleaarGTpBT
0yp4HXRFFoRhhSE/hP+eteaPXRgrsNRLHe9ZDd69wmh7J1wMDb0m81RG7kqcbsid
vrzEeLDRiiPl92dyyWmu
-----END X509 CRL-----
""")


# A broken RSA private key which can be used to test the error path through
# PKey.check.
inconsistentPrivateKeyPEM = b("""-----BEGIN RSA PRIVATE KEY-----
MIIBPAIBAAJBAKy+e3dulvXzV7zoTZWc5TzgApr8DmeQHTYC8ydfzH7EECe4R1Xh
5kwIzOuuFfn178FBiS84gngaNcrFi0Z5fAkCAwEaAQJBAIqm/bz4NA1H++Vx5Ewx
OcKp3w19QSaZAwlGRtsUxrP7436QjnREM3Bm8ygU11BjkPVmtrKm6AayQfCHqJoT
zIECIQDW0BoMoL0HOYM/mrTLhaykYAVqgIeJsPjvkEhTFXWBuQIhAM3deFAvWNu4
nklUQ37XsCT2c9tmNt1LAT+slG2JOTTRAiAuXDtC/m3NYVwyHfFm+zKHRzHkClk2
HjubeEgjpj32AQIhAJqMGTaZVOwevTXvvHwNeH+vRWsAYU/gbx+OQB+7VOcBAiEA
oolb6NMg/R3enNPvS1O4UU1H8wpaF77L4yiSWlE0p4w=
-----END RSA PRIVATE KEY-----
""")


class X509ExtTests(TestCase):
    """
    Tests for L{OpenSSL.crypto.X509Extension}.
    """

    def setUp(self):
        """
        Create a new private key and start a certificate request (for a test
        method to finish in one way or another).
        """
        # Basic setup stuff to generate a certificate
        self.pkey = PKey()
        self.pkey.generate_key(TYPE_RSA, 384)
        self.req = X509Req()
        self.req.set_pubkey(self.pkey)
        # Authority good you have.
        self.req.get_subject().commonName = "Yoda root CA"
        self.x509 = X509()
        self.subject = self.x509.get_subject()
        self.subject.commonName = self.req.get_subject().commonName
        self.x509.set_issuer(self.subject)
        self.x509.set_pubkey(self.pkey)
        now = b(datetime.now().strftime("%Y%m%d%H%M%SZ"))
        expire  = b((datetime.now() + timedelta(days=100)).strftime("%Y%m%d%H%M%SZ"))
        self.x509.set_notBefore(now)
        self.x509.set_notAfter(expire)


    def test_str(self):
        """
        The string representation of L{X509Extension} instances as returned by
        C{str} includes stuff.
        """
        # This isn't necessarily the best string representation.  Perhaps it
        # will be changed/improved in the future.
        self.assertEquals(
            str(X509Extension(b('basicConstraints'), True, b('CA:false'))),
            'CA:FALSE')


    def test_type(self):
        """
        L{X509Extension} and L{X509ExtensionType} refer to the same type object
        and can be used to create instances of that type.
        """
        self.assertIdentical(X509Extension, X509ExtensionType)
        self.assertConsistentType(
            X509Extension,
            'X509Extension', b('basicConstraints'), True, b('CA:true'))


    def test_construction(self):
        """
        L{X509Extension} accepts an extension type name, a critical flag,
        and an extension value and returns an L{X509ExtensionType} instance.
        """
        basic = X509Extension(b('basicConstraints'), True, b('CA:true'))
        self.assertTrue(
            isinstance(basic, X509ExtensionType),
            "%r is of type %r, should be %r" % (
                basic, type(basic), X509ExtensionType))

        comment = X509Extension(
            b('nsComment'), False, b('pyOpenSSL unit test'))
        self.assertTrue(
            isinstance(comment, X509ExtensionType),
            "%r is of type %r, should be %r" % (
                comment, type(comment), X509ExtensionType))


    def test_invalid_extension(self):
        """
        L{X509Extension} raises something if it is passed a bad extension
        name or value.
        """
        self.assertRaises(
            Error, X509Extension, b('thisIsMadeUp'), False, b('hi'))
        self.assertRaises(
            Error, X509Extension, b('basicConstraints'), False, b('blah blah'))

        # Exercise a weird one (an extension which uses the r2i method).  This
        # exercises the codepath that requires a non-NULL ctx to be passed to
        # X509V3_EXT_nconf.  It can't work now because we provide no
        # configuration database.  It might be made to work in the future.
        self.assertRaises(
            Error, X509Extension, b('proxyCertInfo'), True,
            b('language:id-ppl-anyLanguage,pathlen:1,policy:text:AB'))


    def test_get_critical(self):
        """
        L{X509ExtensionType.get_critical} returns the value of the
        extension's critical flag.
        """
        ext = X509Extension(b('basicConstraints'), True, b('CA:true'))
        self.assertTrue(ext.get_critical())
        ext = X509Extension(b('basicConstraints'), False, b('CA:true'))
        self.assertFalse(ext.get_critical())


    def test_get_short_name(self):
        """
        L{X509ExtensionType.get_short_name} returns a string giving the short
        type name of the extension.
        """
        ext = X509Extension(b('basicConstraints'), True, b('CA:true'))
        self.assertEqual(ext.get_short_name(), b('basicConstraints'))
        ext = X509Extension(b('nsComment'), True, b('foo bar'))
        self.assertEqual(ext.get_short_name(), b('nsComment'))


    def test_get_data(self):
        """
        L{X509Extension.get_data} returns a string giving the data of the
        extension.
        """
        ext = X509Extension(b('basicConstraints'), True, b('CA:true'))
        # Expect to get back the DER encoded form of CA:true.
        self.assertEqual(ext.get_data(), b('0\x03\x01\x01\xff'))


    def test_get_data_wrong_args(self):
        """
        L{X509Extension.get_data} raises L{TypeError} if passed any arguments.
        """
        ext = X509Extension(b('basicConstraints'), True, b('CA:true'))
        self.assertRaises(TypeError, ext.get_data, None)
        self.assertRaises(TypeError, ext.get_data, "foo")
        self.assertRaises(TypeError, ext.get_data, 7)


    def test_unused_subject(self):
        """
        The C{subject} parameter to L{X509Extension} may be provided for an
        extension which does not use it and is ignored in this case.
        """
        ext1 = X509Extension(
            b('basicConstraints'), False, b('CA:TRUE'), subject=self.x509)
        self.x509.add_extensions([ext1])
        self.x509.sign(self.pkey, 'sha1')
        # This is a little lame.  Can we think of a better way?
        text = dump_certificate(FILETYPE_TEXT, self.x509)
        self.assertTrue(b('X509v3 Basic Constraints:') in text)
        self.assertTrue(b('CA:TRUE') in text)


    def test_subject(self):
        """
        If an extension requires a subject, the C{subject} parameter to
        L{X509Extension} provides its value.
        """
        ext3 = X509Extension(
            b('subjectKeyIdentifier'), False, b('hash'), subject=self.x509)
        self.x509.add_extensions([ext3])
        self.x509.sign(self.pkey, 'sha1')
        text = dump_certificate(FILETYPE_TEXT, self.x509)
        self.assertTrue(b('X509v3 Subject Key Identifier:') in text)


    def test_missing_subject(self):
        """
        If an extension requires a subject and the C{subject} parameter is
        given no value, something happens.
        """
        self.assertRaises(
            Error, X509Extension, b('subjectKeyIdentifier'), False, b('hash'))


    def test_invalid_subject(self):
        """
        If the C{subject} parameter is given a value which is not an L{X509}
        instance, L{TypeError} is raised.
        """
        for badObj in [True, object(), "hello", [], self]:
            self.assertRaises(
                TypeError,
                X509Extension,
                'basicConstraints', False, 'CA:TRUE', subject=badObj)


    def test_unused_issuer(self):
        """
        The C{issuer} parameter to L{X509Extension} may be provided for an
        extension which does not use it and is ignored in this case.
        """
        ext1 = X509Extension(
            b('basicConstraints'), False, b('CA:TRUE'), issuer=self.x509)
        self.x509.add_extensions([ext1])
        self.x509.sign(self.pkey, 'sha1')
        text = dump_certificate(FILETYPE_TEXT, self.x509)
        self.assertTrue(b('X509v3 Basic Constraints:') in text)
        self.assertTrue(b('CA:TRUE') in text)


    def test_issuer(self):
        """
        If an extension requires a issuer, the C{issuer} parameter to
        L{X509Extension} provides its value.
        """
        ext2 = X509Extension(
            b('authorityKeyIdentifier'), False, b('issuer:always'),
            issuer=self.x509)
        self.x509.add_extensions([ext2])
        self.x509.sign(self.pkey, 'sha1')
        text = dump_certificate(FILETYPE_TEXT, self.x509)
        self.assertTrue(b('X509v3 Authority Key Identifier:') in text)
        self.assertTrue(b('DirName:/CN=Yoda root CA') in text)


    def test_missing_issuer(self):
        """
        If an extension requires an issue and the C{issuer} parameter is given
        no value, something happens.
        """
        self.assertRaises(
            Error,
            X509Extension,
            b('authorityKeyIdentifier'), False,
            b('keyid:always,issuer:always'))


    def test_invalid_issuer(self):
        """
        If the C{issuer} parameter is given a value which is not an L{X509}
        instance, L{TypeError} is raised.
        """
        for badObj in [True, object(), "hello", [], self]:
            self.assertRaises(
                TypeError,
                X509Extension,
                'authorityKeyIdentifier', False, 'keyid:always,issuer:always',
                issuer=badObj)



class PKeyTests(TestCase):
    """
    Unit tests for L{OpenSSL.crypto.PKey}.
    """
    def test_type(self):
        """
        L{PKey} and L{PKeyType} refer to the same type object and can be used
        to create instances of that type.
        """
        self.assertIdentical(PKey, PKeyType)
        self.assertConsistentType(PKey, 'PKey')


    def test_construction(self):
        """
        L{PKey} takes no arguments and returns a new L{PKey} instance.
        """
        self.assertRaises(TypeError, PKey, None)
        key = PKey()
        self.assertTrue(
            isinstance(key, PKeyType),
            "%r is of type %r, should be %r" % (key, type(key), PKeyType))


    def test_pregeneration(self):
        """
        L{PKeyType.bits} and L{PKeyType.type} return C{0} before the key is
        generated.  L{PKeyType.check} raises L{TypeError} before the key is
        generated.
        """
        key = PKey()
        self.assertEqual(key.type(), 0)
        self.assertEqual(key.bits(), 0)
        self.assertRaises(TypeError, key.check)


    def test_failedGeneration(self):
        """
        L{PKeyType.generate_key} takes two arguments, the first giving the key
        type as one of L{TYPE_RSA} or L{TYPE_DSA} and the second giving the
        number of bits to generate.  If an invalid type is specified or
        generation fails, L{Error} is raised.  If an invalid number of bits is
        specified, L{ValueError} or L{Error} is raised.
        """
        key = PKey()
        self.assertRaises(TypeError, key.generate_key)
        self.assertRaises(TypeError, key.generate_key, 1, 2, 3)
        self.assertRaises(TypeError, key.generate_key, "foo", "bar")
        self.assertRaises(Error, key.generate_key, -1, 0)

        self.assertRaises(ValueError, key.generate_key, TYPE_RSA, -1)
        self.assertRaises(ValueError, key.generate_key, TYPE_RSA, 0)

        # XXX RSA generation for small values of bits is fairly buggy in a wide
        # range of OpenSSL versions.  I need to figure out what the safe lower
        # bound for a reasonable number of OpenSSL versions is and explicitly
        # check for that in the wrapper.  The failure behavior is typically an
        # infinite loop inside OpenSSL.

        # self.assertRaises(Error, key.generate_key, TYPE_RSA, 2)

        # XXX DSA generation seems happy with any number of bits.  The DSS
        # says bits must be between 512 and 1024 inclusive.  OpenSSL's DSA
        # generator doesn't seem to care about the upper limit at all.  For
        # the lower limit, it uses 512 if anything smaller is specified.
        # So, it doesn't seem possible to make generate_key fail for
        # TYPE_DSA with a bits argument which is at least an int.

        # self.assertRaises(Error, key.generate_key, TYPE_DSA, -7)


    def test_rsaGeneration(self):
        """
        L{PKeyType.generate_key} generates an RSA key when passed
        L{TYPE_RSA} as a type and a reasonable number of bits.
        """
        bits = 128
        key = PKey()
        key.generate_key(TYPE_RSA, bits)
        self.assertEqual(key.type(), TYPE_RSA)
        self.assertEqual(key.bits(), bits)
        self.assertTrue(key.check())


    def test_dsaGeneration(self):
        """
        L{PKeyType.generate_key} generates a DSA key when passed
        L{TYPE_DSA} as a type and a reasonable number of bits.
        """
        # 512 is a magic number.  The DSS (Digital Signature Standard)
        # allows a minimum of 512 bits for DSA.  DSA_generate_parameters
        # will silently promote any value below 512 to 512.
        bits = 512
        key = PKey()
        key.generate_key(TYPE_DSA, bits)
        self.assertEqual(key.type(), TYPE_DSA)
        self.assertEqual(key.bits(), bits)
        self.assertRaises(TypeError, key.check)


    def test_regeneration(self):
        """
        L{PKeyType.generate_key} can be called multiple times on the same
        key to generate new keys.
        """
        key = PKey()
        for type, bits in [(TYPE_RSA, 512), (TYPE_DSA, 576)]:
             key.generate_key(type, bits)
             self.assertEqual(key.type(), type)
             self.assertEqual(key.bits(), bits)


    def test_inconsistentKey(self):
        """
        L{PKeyType.check} returns C{False} if the key is not consistent.
        """
        key = load_privatekey(FILETYPE_PEM, inconsistentPrivateKeyPEM)
        self.assertRaises(Error, key.check)


    def test_check_wrong_args(self):
        """
        L{PKeyType.check} raises L{TypeError} if called with any arguments.
        """
        self.assertRaises(TypeError, PKey().check, None)
        self.assertRaises(TypeError, PKey().check, object())
        self.assertRaises(TypeError, PKey().check, 1)



class X509NameTests(TestCase):
    """
    Unit tests for L{OpenSSL.crypto.X509Name}.
    """
    def _x509name(self, **attrs):
        # XXX There's no other way to get a new X509Name yet.
        name = X509().get_subject()
        attrs = list(attrs.items())
        # Make the order stable - order matters!
        def key(attr):
            return attr[1]
        attrs.sort(key=key)
        for k, v in attrs:
            setattr(name, k, v)
        return name


    def test_type(self):
        """
        The type of X509Name objects is L{X509NameType}.
        """
        self.assertIdentical(X509Name, X509NameType)
        self.assertEqual(X509NameType.__name__, 'X509Name')
        self.assertTrue(isinstance(X509NameType, type))

        name = self._x509name()
        self.assertTrue(
            isinstance(name, X509NameType),
            "%r is of type %r, should be %r" % (
                name, type(name), X509NameType))


    def test_onlyStringAttributes(self):
        """
        Attempting to set a non-L{str} attribute name on an L{X509NameType}
        instance causes L{TypeError} to be raised.
        """
        name = self._x509name()
        # Beyond these cases, you may also think that unicode should be
        # rejected.  Sorry, you're wrong.  unicode is automatically converted to
        # str outside of the control of X509Name, so there's no way to reject
        # it.
        self.assertRaises(TypeError, setattr, name, None, "hello")
        self.assertRaises(TypeError, setattr, name, 30, "hello")
        class evil(str):
            pass
        self.assertRaises(TypeError, setattr, name, evil(), "hello")


    def test_setInvalidAttribute(self):
        """
        Attempting to set any attribute name on an L{X509NameType} instance for
        which no corresponding NID is defined causes L{AttributeError} to be
        raised.
        """
        name = self._x509name()
        self.assertRaises(AttributeError, setattr, name, "no such thing", None)


    def test_attributes(self):
        """
        L{X509NameType} instances have attributes for each standard (?)
        X509Name field.
        """
        name = self._x509name()
        name.commonName = "foo"
        self.assertEqual(name.commonName, "foo")
        self.assertEqual(name.CN, "foo")
        name.CN = "baz"
        self.assertEqual(name.commonName, "baz")
        self.assertEqual(name.CN, "baz")
        name.commonName = "bar"
        self.assertEqual(name.commonName, "bar")
        self.assertEqual(name.CN, "bar")
        name.CN = "quux"
        self.assertEqual(name.commonName, "quux")
        self.assertEqual(name.CN, "quux")


    def test_copy(self):
        """
        L{X509Name} creates a new L{X509NameType} instance with all the same
        attributes as an existing L{X509NameType} instance when called with
        one.
        """
        name = self._x509name(commonName="foo", emailAddress="bar@example.com")

        copy = X509Name(name)
        self.assertEqual(copy.commonName, "foo")
        self.assertEqual(copy.emailAddress, "bar@example.com")

        # Mutate the copy and ensure the original is unmodified.
        copy.commonName = "baz"
        self.assertEqual(name.commonName, "foo")

        # Mutate the original and ensure the copy is unmodified.
        name.emailAddress = "quux@example.com"
        self.assertEqual(copy.emailAddress, "bar@example.com")


    def test_repr(self):
        """
        L{repr} passed an L{X509NameType} instance should return a string
        containing a description of the type and the NIDs which have been set
        on it.
        """
        name = self._x509name(commonName="foo", emailAddress="bar")
        self.assertEqual(
            repr(name),
            "<X509Name object '/emailAddress=bar/CN=foo'>")


    def test_comparison(self):
        """
        L{X509NameType} instances should compare based on their NIDs.
        """
        def _equality(a, b, assertTrue, assertFalse):
            assertTrue(a == b, "(%r == %r) --> False" % (a, b))
            assertFalse(a != b)
            assertTrue(b == a)
            assertFalse(b != a)

        def assertEqual(a, b):
            _equality(a, b, self.assertTrue, self.assertFalse)

        # Instances compare equal to themselves.
        name = self._x509name()
        assertEqual(name, name)

        # Empty instances should compare equal to each other.
        assertEqual(self._x509name(), self._x509name())

        # Instances with equal NIDs should compare equal to each other.
        assertEqual(self._x509name(commonName="foo"),
                    self._x509name(commonName="foo"))

        # Instance with equal NIDs set using different aliases should compare
        # equal to each other.
        assertEqual(self._x509name(commonName="foo"),
                    self._x509name(CN="foo"))

        # Instances with more than one NID with the same values should compare
        # equal to each other.
        assertEqual(self._x509name(CN="foo", organizationalUnitName="bar"),
                    self._x509name(commonName="foo", OU="bar"))

        def assertNotEqual(a, b):
            _equality(a, b, self.assertFalse, self.assertTrue)

        # Instances with different values for the same NID should not compare
        # equal to each other.
        assertNotEqual(self._x509name(CN="foo"),
                       self._x509name(CN="bar"))

        # Instances with different NIDs should not compare equal to each other.
        assertNotEqual(self._x509name(CN="foo"),
                       self._x509name(OU="foo"))

        def _inequality(a, b, assertTrue, assertFalse):
            assertTrue(a < b)
            assertTrue(a <= b)
            assertTrue(b > a)
            assertTrue(b >= a)
            assertFalse(a > b)
            assertFalse(a >= b)
            assertFalse(b < a)
            assertFalse(b <= a)

        def assertLessThan(a, b):
            _inequality(a, b, self.assertTrue, self.assertFalse)

        # An X509Name with a NID with a value which sorts less than the value
        # of the same NID on another X509Name compares less than the other
        # X509Name.
        assertLessThan(self._x509name(CN="abc"),
                       self._x509name(CN="def"))

        def assertGreaterThan(a, b):
            _inequality(a, b, self.assertFalse, self.assertTrue)

        # An X509Name with a NID with a value which sorts greater than the
        # value of the same NID on another X509Name compares greater than the
        # other X509Name.
        assertGreaterThan(self._x509name(CN="def"),
                          self._x509name(CN="abc"))


    def test_hash(self):
        """
        L{X509Name.hash} returns an integer hash based on the value of the
        name.
        """
        a = self._x509name(CN="foo")
        b = self._x509name(CN="foo")
        self.assertEqual(a.hash(), b.hash())
        a.CN = "bar"
        self.assertNotEqual(a.hash(), b.hash())


    def test_der(self):
        """
        L{X509Name.der} returns the DER encoded form of the name.
        """
        a = self._x509name(CN="foo", C="US")
        self.assertEqual(
            a.der(),
            b('0\x1b1\x0b0\t\x06\x03U\x04\x06\x13\x02US'
              '1\x0c0\n\x06\x03U\x04\x03\x13\x03foo'))


    def test_get_components(self):
        """
        L{X509Name.get_components} returns a C{list} of two-tuples of C{str}
        giving the NIDs and associated values which make up the name.
        """
        a = self._x509name()
        self.assertEqual(a.get_components(), [])
        a.CN = "foo"
        self.assertEqual(a.get_components(), [(b("CN"), b("foo"))])
        a.organizationalUnitName = "bar"
        self.assertEqual(
            a.get_components(),
            [(b("CN"), b("foo")), (b("OU"), b("bar"))])


class _PKeyInteractionTestsMixin:
    """
    Tests which involve another thing and a PKey.
    """
    def signable(self):
        """
        Return something with a C{set_pubkey}, C{set_pubkey}, and C{sign} method.
        """
        raise NotImplementedError()


    def test_signWithUngenerated(self):
        """
        L{X509Req.sign} raises L{ValueError} when pass a L{PKey} with no parts.
        """
        request = self.signable()
        key = PKey()
        self.assertRaises(ValueError, request.sign, key, 'MD5')


    def test_signWithPublicKey(self):
        """
        L{X509Req.sign} raises L{ValueError} when pass a L{PKey} with no
        private part as the signing key.
        """
        request = self.signable()
        key = PKey()
        key.generate_key(TYPE_RSA, 512)
        request.set_pubkey(key)
        pub = request.get_pubkey()
        self.assertRaises(ValueError, request.sign, pub, 'MD5')


    def test_signWithUnknownDigest(self):
        """
        L{X509Req.sign} raises L{ValueError} when passed a digest name which is
        not known.
        """
        request = self.signable()
        key = PKey()
        key.generate_key(TYPE_RSA, 512)
        self.assertRaises(ValueError, request.sign, key, "monkeys")


    def test_sign(self):
        """
        L{X509Req.sign} succeeds when passed a private key object and a valid
        digest function.  C{X509Req.verify} can be used to check the signature.
        """
        request = self.signable()
        key = PKey()
        key.generate_key(TYPE_RSA, 512)
        request.set_pubkey(key)
        request.sign(key, 'MD5')
        # If the type has a verify method, cover that too.
        if getattr(request, 'verify', None) is not None:
            pub = request.get_pubkey()
            self.assertTrue(request.verify(pub))
            # Make another key that won't verify.
            key = PKey()
            key.generate_key(TYPE_RSA, 512)
            self.assertRaises(Error, request.verify, key)




class X509ReqTests(TestCase, _PKeyInteractionTestsMixin):
    """
    Tests for L{OpenSSL.crypto.X509Req}.
    """
    def signable(self):
        """
        Create and return a new L{X509Req}.
        """
        return X509Req()


    def test_type(self):
        """
        L{X509Req} and L{X509ReqType} refer to the same type object and can be
        used to create instances of that type.
        """
        self.assertIdentical(X509Req, X509ReqType)
        self.assertConsistentType(X509Req, 'X509Req')


    def test_construction(self):
        """
        L{X509Req} takes no arguments and returns an L{X509ReqType} instance.
        """
        request = X509Req()
        self.assertTrue(
            isinstance(request, X509ReqType),
            "%r is of type %r, should be %r" % (request, type(request), X509ReqType))


    def test_version(self):
        """
        L{X509ReqType.set_version} sets the X.509 version of the certificate
        request.  L{X509ReqType.get_version} returns the X.509 version of
        the certificate request.  The initial value of the version is 0.
        """
        request = X509Req()
        self.assertEqual(request.get_version(), 0)
        request.set_version(1)
        self.assertEqual(request.get_version(), 1)
        request.set_version(3)
        self.assertEqual(request.get_version(), 3)


    def test_version_wrong_args(self):
        """
        L{X509ReqType.set_version} raises L{TypeError} if called with the wrong
        number of arguments or with a non-C{int} argument.
        L{X509ReqType.get_version} raises L{TypeError} if called with any
        arguments.
        """
        request = X509Req()
        self.assertRaises(TypeError, request.set_version)
        self.assertRaises(TypeError, request.set_version, "foo")
        self.assertRaises(TypeError, request.set_version, 1, 2)
        self.assertRaises(TypeError, request.get_version, None)


    def test_get_subject(self):
        """
        L{X509ReqType.get_subject} returns an L{X509Name} for the subject of
        the request and which is valid even after the request object is
        otherwise dead.
        """
        request = X509Req()
        subject = request.get_subject()
        self.assertTrue(
            isinstance(subject, X509NameType),
            "%r is of type %r, should be %r" % (subject, type(subject), X509NameType))
        subject.commonName = "foo"
        self.assertEqual(request.get_subject().commonName, "foo")
        del request
        subject.commonName = "bar"
        self.assertEqual(subject.commonName, "bar")


    def test_get_subject_wrong_args(self):
        """
        L{X509ReqType.get_subject} raises L{TypeError} if called with any
        arguments.
        """
        request = X509Req()
        self.assertRaises(TypeError, request.get_subject, None)


    def test_add_extensions(self):
        """
        L{X509Req.add_extensions} accepts a C{list} of L{X509Extension}
        instances and adds them to the X509 request.
        """
        request = X509Req()
        request.add_extensions([
                X509Extension(b('basicConstraints'), True, b('CA:false'))])
        # XXX Add get_extensions so the rest of this unit test can be written.


    def test_add_extensions_wrong_args(self):
        """
        L{X509Req.add_extensions} raises L{TypeError} if called with the wrong
        number of arguments or with a non-C{list}.  Or it raises L{ValueError}
        if called with a C{list} containing objects other than L{X509Extension}
        instances.
        """
        request = X509Req()
        self.assertRaises(TypeError, request.add_extensions)
        self.assertRaises(TypeError, request.add_extensions, object())
        self.assertRaises(ValueError, request.add_extensions, [object()])
        self.assertRaises(TypeError, request.add_extensions, [], None)



class X509Tests(TestCase, _PKeyInteractionTestsMixin):
    """
    Tests for L{OpenSSL.crypto.X509}.
    """
    pemData = cleartextCertificatePEM + cleartextPrivateKeyPEM

    extpem = """
-----BEGIN CERTIFICATE-----
MIIC3jCCAkegAwIBAgIJAJHFjlcCgnQzMA0GCSqGSIb3DQEBBQUAMEcxCzAJBgNV
BAYTAlNFMRUwEwYDVQQIEwxXZXN0ZXJib3R0b20xEjAQBgNVBAoTCUNhdGFsb2dp
eDENMAsGA1UEAxMEUm9vdDAeFw0wODA0MjIxNDQ1MzhaFw0wOTA0MjIxNDQ1Mzha
MFQxCzAJBgNVBAYTAlNFMQswCQYDVQQIEwJXQjEUMBIGA1UEChMLT3Blbk1ldGFk
aXIxIjAgBgNVBAMTGW5vZGUxLm9tMi5vcGVubWV0YWRpci5vcmcwgZ8wDQYJKoZI
hvcNAQEBBQADgY0AMIGJAoGBAPIcQMrwbk2nESF/0JKibj9i1x95XYAOwP+LarwT
Op4EQbdlI9SY+uqYqlERhF19w7CS+S6oyqx0DRZSk4Y9dZ9j9/xgm2u/f136YS1u
zgYFPvfUs6PqYLPSM8Bw+SjJ+7+2+TN+Tkiof9WP1cMjodQwOmdsiRbR0/J7+b1B
hec1AgMBAAGjgcQwgcEwCQYDVR0TBAIwADAsBglghkgBhvhCAQ0EHxYdT3BlblNT
TCBHZW5lcmF0ZWQgQ2VydGlmaWNhdGUwHQYDVR0OBBYEFIdHsBcMVVMbAO7j6NCj
03HgLnHaMB8GA1UdIwQYMBaAFL2h9Bf9Mre4vTdOiHTGAt7BRY/8MEYGA1UdEQQ/
MD2CDSouZXhhbXBsZS5vcmeCESoub20yLmV4bWFwbGUuY29thwSC7wgKgRNvbTJA
b3Blbm1ldGFkaXIub3JnMA0GCSqGSIb3DQEBBQUAA4GBALd7WdXkp2KvZ7/PuWZA
MPlIxyjS+Ly11+BNE0xGQRp9Wz+2lABtpgNqssvU156+HkKd02rGheb2tj7MX9hG
uZzbwDAZzJPjzDQDD7d3cWsrVcfIdqVU7epHqIadnOF+X0ghJ39pAm6VVadnSXCt
WpOdIpB8KksUTCzV591Nr1wd
-----END CERTIFICATE-----
    """
    def signable(self):
        """
        Create and return a new L{X509}.
        """
        return X509()


    def test_type(self):
        """
        L{X509} and L{X509Type} refer to the same type object and can be used
        to create instances of that type.
        """
        self.assertIdentical(X509, X509Type)
        self.assertConsistentType(X509, 'X509')


    def test_construction(self):
        """
        L{X509} takes no arguments and returns an instance of L{X509Type}.
        """
        certificate = X509()
        self.assertTrue(
            isinstance(certificate, X509Type),
            "%r is of type %r, should be %r" % (certificate,
                                                type(certificate),
                                                X509Type))
        self.assertEqual(type(X509Type).__name__, 'type')
        self.assertEqual(type(certificate).__name__, 'X509')
        self.assertEqual(type(certificate), X509Type)
        self.assertEqual(type(certificate), X509)


    def test_get_version_wrong_args(self):
        """
        L{X509.get_version} raises L{TypeError} if invoked with any arguments.
        """
        cert = X509()
        self.assertRaises(TypeError, cert.get_version, None)


    def test_set_version_wrong_args(self):
        """
        L{X509.set_version} raises L{TypeError} if invoked with the wrong number
        of arguments or an argument not of type C{int}.
        """
        cert = X509()
        self.assertRaises(TypeError, cert.set_version)
        self.assertRaises(TypeError, cert.set_version, None)
        self.assertRaises(TypeError, cert.set_version, 1, None)


    def test_version(self):
        """
        L{X509.set_version} sets the certificate version number.
        L{X509.get_version} retrieves it.
        """
        cert = X509()
        cert.set_version(1234)
        self.assertEquals(cert.get_version(), 1234)


    def test_get_serial_number_wrong_args(self):
        """
        L{X509.get_serial_number} raises L{TypeError} if invoked with any
        arguments.
        """
        cert = X509()
        self.assertRaises(TypeError, cert.get_serial_number, None)


    def test_serial_number(self):
        """
        The serial number of an L{X509Type} can be retrieved and modified with
        L{X509Type.get_serial_number} and L{X509Type.set_serial_number}.
        """
        certificate = X509()
        self.assertRaises(TypeError, certificate.set_serial_number)
        self.assertRaises(TypeError, certificate.set_serial_number, 1, 2)
        self.assertRaises(TypeError, certificate.set_serial_number, "1")
        self.assertRaises(TypeError, certificate.set_serial_number, 5.5)
        self.assertEqual(certificate.get_serial_number(), 0)
        certificate.set_serial_number(1)
        self.assertEqual(certificate.get_serial_number(), 1)
        certificate.set_serial_number(2 ** 32 + 1)
        self.assertEqual(certificate.get_serial_number(), 2 ** 32 + 1)
        certificate.set_serial_number(2 ** 64 + 1)
        self.assertEqual(certificate.get_serial_number(), 2 ** 64 + 1)
        certificate.set_serial_number(2 ** 128 + 1)
        self.assertEqual(certificate.get_serial_number(), 2 ** 128 + 1)


    def _setBoundTest(self, which):
        """
        L{X509Type.set_notBefore} takes a string in the format of an ASN1
        GENERALIZEDTIME and sets the beginning of the certificate's validity
        period to it.
        """
        certificate = X509()
        set = getattr(certificate, 'set_not' + which)
        get = getattr(certificate, 'get_not' + which)

        # Starts with no value.
        self.assertEqual(get(), None)

        # GMT (Or is it UTC?) -exarkun
        when = b("20040203040506Z")
        set(when)
        self.assertEqual(get(), when)

        # A plus two hours and thirty minutes offset
        when = b("20040203040506+0530")
        set(when)
        self.assertEqual(get(), when)

        # A minus one hour fifteen minutes offset
        when = b("20040203040506-0115")
        set(when)
        self.assertEqual(get(), when)

        # An invalid string results in a ValueError
        self.assertRaises(ValueError, set, b("foo bar"))

        # The wrong number of arguments results in a TypeError.
        self.assertRaises(TypeError, set)
        self.assertRaises(TypeError, set, b("20040203040506Z"), b("20040203040506Z"))
        self.assertRaises(TypeError, get, b("foo bar"))


    # XXX ASN1_TIME (not GENERALIZEDTIME)

    def test_set_notBefore(self):
        """
        L{X509Type.set_notBefore} takes a string in the format of an ASN1
        GENERALIZEDTIME and sets the beginning of the certificate's validity
        period to it.
        """
        self._setBoundTest("Before")


    def test_set_notAfter(self):
        """
        L{X509Type.set_notAfter} takes a string in the format of an ASN1
        GENERALIZEDTIME and sets the end of the certificate's validity period
        to it.
        """
        self._setBoundTest("After")


    def test_get_notBefore(self):
        """
        L{X509Type.get_notBefore} returns a string in the format of an ASN1
        GENERALIZEDTIME even for certificates which store it as UTCTIME
        internally.
        """
        cert = load_certificate(FILETYPE_PEM, self.pemData)
        self.assertEqual(cert.get_notBefore(), b("20090325123658Z"))


    def test_get_notAfter(self):
        """
        L{X509Type.get_notAfter} returns a string in the format of an ASN1
        GENERALIZEDTIME even for certificates which store it as UTCTIME
        internally.
        """
        cert = load_certificate(FILETYPE_PEM, self.pemData)
        self.assertEqual(cert.get_notAfter(), b("20170611123658Z"))


    def test_gmtime_adj_notBefore_wrong_args(self):
        """
        L{X509Type.gmtime_adj_notBefore} raises L{TypeError} if called with the
        wrong number of arguments or a non-C{int} argument.
        """
        cert = X509()
        self.assertRaises(TypeError, cert.gmtime_adj_notBefore)
        self.assertRaises(TypeError, cert.gmtime_adj_notBefore, None)
        self.assertRaises(TypeError, cert.gmtime_adj_notBefore, 123, None)


    def test_gmtime_adj_notBefore(self):
        """
        L{X509Type.gmtime_adj_notBefore} changes the not-before timestamp to be
        the current time plus the number of seconds passed in.
        """
        cert = load_certificate(FILETYPE_PEM, self.pemData)
        now = datetime.utcnow() + timedelta(seconds=100)
        cert.gmtime_adj_notBefore(100)
        self.assertEqual(cert.get_notBefore(), b(now.strftime("%Y%m%d%H%M%SZ")))


    def test_gmtime_adj_notAfter_wrong_args(self):
        """
        L{X509Type.gmtime_adj_notAfter} raises L{TypeError} if called with the
        wrong number of arguments or a non-C{int} argument.
        """
        cert = X509()
        self.assertRaises(TypeError, cert.gmtime_adj_notAfter)
        self.assertRaises(TypeError, cert.gmtime_adj_notAfter, None)
        self.assertRaises(TypeError, cert.gmtime_adj_notAfter, 123, None)


    def test_gmtime_adj_notAfter(self):
        """
        L{X509Type.gmtime_adj_notAfter} changes the not-after timestamp to be
        the current time plus the number of seconds passed in.
        """
        cert = load_certificate(FILETYPE_PEM, self.pemData)
        now = datetime.utcnow() + timedelta(seconds=100)
        cert.gmtime_adj_notAfter(100)
        self.assertEqual(cert.get_notAfter(), b(now.strftime("%Y%m%d%H%M%SZ")))


    def test_has_expired_wrong_args(self):
        """
        L{X509Type.has_expired} raises L{TypeError} if called with any
        arguments.
        """
        cert = X509()
        self.assertRaises(TypeError, cert.has_expired, None)


    def test_has_expired(self):
        """
        L{X509Type.has_expired} returns C{True} if the certificate's not-after
        time is in the past.
        """
        cert = X509()
        cert.gmtime_adj_notAfter(-1)
        self.assertTrue(cert.has_expired())


    def test_has_not_expired(self):
        """
        L{X509Type.has_expired} returns C{False} if the certificate's not-after
        time is in the future.
        """
        cert = X509()
        cert.gmtime_adj_notAfter(2)
        self.assertFalse(cert.has_expired())


    def test_digest(self):
        """
        L{X509.digest} returns a string giving ":"-separated hex-encoded words
        of the digest of the certificate.
        """
        cert = X509()
        self.assertEqual(
            cert.digest("md5"),
            b("A8:EB:07:F8:53:25:0A:F2:56:05:C5:A5:C4:C4:C7:15"))


    def _extcert(self, pkey, extensions):
        cert = X509()
        cert.set_pubkey(pkey)
        cert.get_subject().commonName = "Unit Tests"
        cert.get_issuer().commonName = "Unit Tests"
        when = b(datetime.now().strftime("%Y%m%d%H%M%SZ"))
        cert.set_notBefore(when)
        cert.set_notAfter(when)

        cert.add_extensions(extensions)
        return load_certificate(
            FILETYPE_PEM, dump_certificate(FILETYPE_PEM, cert))


    def test_extension_count(self):
        """
        L{X509.get_extension_count} returns the number of extensions that are
        present in the certificate.
        """
        pkey = load_privatekey(FILETYPE_PEM, client_key_pem)
        ca = X509Extension(b('basicConstraints'), True, b('CA:FALSE'))
        key = X509Extension(b('keyUsage'), True, b('digitalSignature'))
        subjectAltName = X509Extension(
            b('subjectAltName'), True, b('DNS:example.com'))

        # Try a certificate with no extensions at all.
        c = self._extcert(pkey, [])
        self.assertEqual(c.get_extension_count(), 0)

        # And a certificate with one
        c = self._extcert(pkey, [ca])
        self.assertEqual(c.get_extension_count(), 1)

        # And a certificate with several
        c = self._extcert(pkey, [ca, key, subjectAltName])
        self.assertEqual(c.get_extension_count(), 3)


    def test_get_extension(self):
        """
        L{X509.get_extension} takes an integer and returns an L{X509Extension}
        corresponding to the extension at that index.
        """
        pkey = load_privatekey(FILETYPE_PEM, client_key_pem)
        ca = X509Extension(b('basicConstraints'), True, b('CA:FALSE'))
        key = X509Extension(b('keyUsage'), True, b('digitalSignature'))
        subjectAltName = X509Extension(
            b('subjectAltName'), False, b('DNS:example.com'))

        cert = self._extcert(pkey, [ca, key, subjectAltName])

        ext = cert.get_extension(0)
        self.assertTrue(isinstance(ext, X509Extension))
        self.assertTrue(ext.get_critical())
        self.assertEqual(ext.get_short_name(), b('basicConstraints'))

        ext = cert.get_extension(1)
        self.assertTrue(isinstance(ext, X509Extension))
        self.assertTrue(ext.get_critical())
        self.assertEqual(ext.get_short_name(), b('keyUsage'))

        ext = cert.get_extension(2)
        self.assertTrue(isinstance(ext, X509Extension))
        self.assertFalse(ext.get_critical())
        self.assertEqual(ext.get_short_name(), b('subjectAltName'))

        self.assertRaises(IndexError, cert.get_extension, -1)
        self.assertRaises(IndexError, cert.get_extension, 4)
        self.assertRaises(TypeError, cert.get_extension, "hello")


    def test_invalid_digest_algorithm(self):
        """
        L{X509.digest} raises L{ValueError} if called with an unrecognized hash
        algorithm.
        """
        cert = X509()
        self.assertRaises(ValueError, cert.digest, "monkeys")


    def test_get_subject_wrong_args(self):
        """
        L{X509.get_subject} raises L{TypeError} if called with any arguments.
        """
        cert = X509()
        self.assertRaises(TypeError, cert.get_subject, None)


    def test_get_subject(self):
        """
        L{X509.get_subject} returns an L{X509Name} instance.
        """
        cert = load_certificate(FILETYPE_PEM, self.pemData)
        subj = cert.get_subject()
        self.assertTrue(isinstance(subj, X509Name))
        self.assertEquals(
            subj.get_components(),
            [(b('C'), b('US')), (b('ST'), b('IL')), (b('L'), b('Chicago')),
             (b('O'), b('Testing')), (b('CN'), b('Testing Root CA'))])


    def test_set_subject_wrong_args(self):
        """
        L{X509.set_subject} raises a L{TypeError} if called with the wrong
        number of arguments or an argument not of type L{X509Name}.
        """
        cert = X509()
        self.assertRaises(TypeError, cert.set_subject)
        self.assertRaises(TypeError, cert.set_subject, None)
        self.assertRaises(TypeError, cert.set_subject, cert.get_subject(), None)


    def test_set_subject(self):
        """
        L{X509.set_subject} changes the subject of the certificate to the one
        passed in.
        """
        cert = X509()
        name = cert.get_subject()
        name.C = 'AU'
        name.O = 'Unit Tests'
        cert.set_subject(name)
        self.assertEquals(
            cert.get_subject().get_components(),
            [(b('C'), b('AU')), (b('O'), b('Unit Tests'))])


    def test_get_issuer_wrong_args(self):
        """
        L{X509.get_issuer} raises L{TypeError} if called with any arguments.
        """
        cert = X509()
        self.assertRaises(TypeError, cert.get_issuer, None)


    def test_get_issuer(self):
        """
        L{X509.get_issuer} returns an L{X509Name} instance.
        """
        cert = load_certificate(FILETYPE_PEM, self.pemData)
        subj = cert.get_issuer()
        self.assertTrue(isinstance(subj, X509Name))
        comp = subj.get_components()
        self.assertEquals(
            comp,
            [(b('C'), b('US')), (b('ST'), b('IL')), (b('L'), b('Chicago')),
             (b('O'), b('Testing')), (b('CN'), b('Testing Root CA'))])


    def test_set_issuer_wrong_args(self):
        """
        L{X509.set_issuer} raises a L{TypeError} if called with the wrong
        number of arguments or an argument not of type L{X509Name}.
        """
        cert = X509()
        self.assertRaises(TypeError, cert.set_issuer)
        self.assertRaises(TypeError, cert.set_issuer, None)
        self.assertRaises(TypeError, cert.set_issuer, cert.get_issuer(), None)


    def test_set_issuer(self):
        """
        L{X509.set_issuer} changes the issuer of the certificate to the one
        passed in.
        """
        cert = X509()
        name = cert.get_issuer()
        name.C = 'AU'
        name.O = 'Unit Tests'
        cert.set_issuer(name)
        self.assertEquals(
            cert.get_issuer().get_components(),
            [(b('C'), b('AU')), (b('O'), b('Unit Tests'))])


    def test_get_pubkey_uninitialized(self):
        """
        When called on a certificate with no public key, L{X509.get_pubkey}
        raises L{OpenSSL.crypto.Error}.
        """
        cert = X509()
        self.assertRaises(Error, cert.get_pubkey)


    def test_subject_name_hash_wrong_args(self):
        """
        L{X509.subject_name_hash} raises L{TypeError} if called with any
        arguments.
        """
        cert = X509()
        self.assertRaises(TypeError, cert.subject_name_hash, None)


    def test_subject_name_hash(self):
        """
        L{X509.subject_name_hash} returns the hash of the certificate's subject
        name.
        """
        cert = load_certificate(FILETYPE_PEM, self.pemData)
        self.assertIn(
            cert.subject_name_hash(),
            [3350047874, # OpenSSL 0.9.8, MD5
             3278919224, # OpenSSL 1.0.0, SHA1
             ])


    def test_get_signature_algorithm(self):
        """
        L{X509Type.get_signature_algorithm} returns a string which means
        the algorithm used to sign the certificate.
        """
        cert = load_certificate(FILETYPE_PEM, self.pemData)
        self.assertEqual(
            b("sha1WithRSAEncryption"), cert.get_signature_algorithm())


    def test_get_undefined_signature_algorithm(self):
        """
        L{X509Type.get_signature_algorithm} raises L{ValueError} if the
        signature algorithm is undefined or unknown.
        """
        # This certificate has been modified to indicate a bogus OID in the
        # signature algorithm field so that OpenSSL does not recognize it.
        certPEM = """\
-----BEGIN CERTIFICATE-----
MIIC/zCCAmigAwIBAgIBATAGBgJ8BQUAMHsxCzAJBgNVBAYTAlNHMREwDwYDVQQK
EwhNMkNyeXB0bzEUMBIGA1UECxMLTTJDcnlwdG8gQ0ExJDAiBgNVBAMTG00yQ3J5
cHRvIENlcnRpZmljYXRlIE1hc3RlcjEdMBsGCSqGSIb3DQEJARYObmdwc0Bwb3N0
MS5jb20wHhcNMDAwOTEwMDk1MTMwWhcNMDIwOTEwMDk1MTMwWjBTMQswCQYDVQQG
EwJTRzERMA8GA1UEChMITTJDcnlwdG8xEjAQBgNVBAMTCWxvY2FsaG9zdDEdMBsG
CSqGSIb3DQEJARYObmdwc0Bwb3N0MS5jb20wXDANBgkqhkiG9w0BAQEFAANLADBI
AkEArL57d26W9fNXvOhNlZzlPOACmvwOZ5AdNgLzJ1/MfsQQJ7hHVeHmTAjM664V
+fXvwUGJLziCeBo1ysWLRnl8CQIDAQABo4IBBDCCAQAwCQYDVR0TBAIwADAsBglg
hkgBhvhCAQ0EHxYdT3BlblNTTCBHZW5lcmF0ZWQgQ2VydGlmaWNhdGUwHQYDVR0O
BBYEFM+EgpK+eyZiwFU1aOPSbczbPSpVMIGlBgNVHSMEgZ0wgZqAFPuHI2nrnDqT
FeXFvylRT/7tKDgBoX+kfTB7MQswCQYDVQQGEwJTRzERMA8GA1UEChMITTJDcnlw
dG8xFDASBgNVBAsTC00yQ3J5cHRvIENBMSQwIgYDVQQDExtNMkNyeXB0byBDZXJ0
aWZpY2F0ZSBNYXN0ZXIxHTAbBgkqhkiG9w0BCQEWDm5ncHNAcG9zdDEuY29tggEA
MA0GCSqGSIb3DQEBBAUAA4GBADv8KpPo+gfJxN2ERK1Y1l17sz/ZhzoGgm5XCdbx
jEY7xKfpQngV599k1xhl11IMqizDwu0855agrckg2MCTmOI9DZzDD77tAYb+Dk0O
PEVk0Mk/V0aIsDE9bolfCi/i/QWZ3N8s5nTWMNyBBBmoSliWCm4jkkRZRD0ejgTN
tgI5
-----END CERTIFICATE-----
"""
        cert = load_certificate(FILETYPE_PEM, certPEM)
        self.assertRaises(ValueError, cert.get_signature_algorithm)



class PKCS12Tests(TestCase):
    """
    Test for L{OpenSSL.crypto.PKCS12} and L{OpenSSL.crypto.load_pkcs12}.
    """
    pemData = cleartextCertificatePEM + cleartextPrivateKeyPEM

    def test_type(self):
        """
        L{PKCS12Type} is a type object.
        """
        self.assertIdentical(PKCS12, PKCS12Type)
        self.assertConsistentType(PKCS12, 'PKCS12')


    def test_empty_construction(self):
        """
        L{PKCS12} returns a new instance of L{PKCS12} with no certificate,
        private key, CA certificates, or friendly name.
        """
        p12 = PKCS12()
        self.assertEqual(None, p12.get_certificate())
        self.assertEqual(None, p12.get_privatekey())
        self.assertEqual(None, p12.get_ca_certificates())
        self.assertEqual(None, p12.get_friendlyname())


    def test_type_errors(self):
        """
        The L{PKCS12} setter functions (C{set_certificate}, C{set_privatekey},
        C{set_ca_certificates}, and C{set_friendlyname}) raise L{TypeError}
        when passed objects of types other than those expected.
        """
        p12 = PKCS12()
        self.assertRaises(TypeError, p12.set_certificate, 3)
        self.assertRaises(TypeError, p12.set_certificate, PKey())
        self.assertRaises(TypeError, p12.set_certificate, X509)
        self.assertRaises(TypeError, p12.set_privatekey, 3)
        self.assertRaises(TypeError, p12.set_privatekey, 'legbone')
        self.assertRaises(TypeError, p12.set_privatekey, X509())
        self.assertRaises(TypeError, p12.set_ca_certificates, 3)
        self.assertRaises(TypeError, p12.set_ca_certificates, X509())
        self.assertRaises(TypeError, p12.set_ca_certificates, (3, 4))
        self.assertRaises(TypeError, p12.set_ca_certificates, ( PKey(), ))
        self.assertRaises(TypeError, p12.set_friendlyname, 6)
        self.assertRaises(TypeError, p12.set_friendlyname, ('foo', 'bar'))


    def test_key_only(self):
        """
        A L{PKCS12} with only a private key can be exported using
        L{PKCS12.export} and loaded again using L{load_pkcs12}.
        """
        passwd = 'blah'
        p12 = PKCS12()
        pkey = load_privatekey(FILETYPE_PEM, cleartextPrivateKeyPEM)
        p12.set_privatekey(pkey)
        self.assertEqual(None, p12.get_certificate())
        self.assertEqual(pkey, p12.get_privatekey())
        try:
            dumped_p12 = p12.export(passphrase=passwd, iter=2, maciter=3)
        except Error:
            # Some versions of OpenSSL will throw an exception
            # for this nearly useless PKCS12 we tried to generate:
            # [('PKCS12 routines', 'PKCS12_create', 'invalid null argument')]
            return
        p12 = load_pkcs12(dumped_p12, passwd)
        self.assertEqual(None, p12.get_ca_certificates())
        self.assertEqual(None, p12.get_certificate())

        # OpenSSL fails to bring the key back to us.  So sad.  Perhaps in the
        # future this will be improved.
        self.assertTrue(isinstance(p12.get_privatekey(), (PKey, type(None))))


    def test_cert_only(self):
        """
        A L{PKCS12} with only a certificate can be exported using
        L{PKCS12.export} and loaded again using L{load_pkcs12}.
        """
        passwd = 'blah'
        p12 = PKCS12()
        cert = load_certificate(FILETYPE_PEM, cleartextCertificatePEM)
        p12.set_certificate(cert)
        self.assertEqual(cert, p12.get_certificate())
        self.assertEqual(None, p12.get_privatekey())
        try:
            dumped_p12 = p12.export(passphrase=passwd, iter=2, maciter=3)
        except Error:
            # Some versions of OpenSSL will throw an exception
            # for this nearly useless PKCS12 we tried to generate:
            # [('PKCS12 routines', 'PKCS12_create', 'invalid null argument')]
            return
        p12 = load_pkcs12(dumped_p12, passwd)
        self.assertEqual(None, p12.get_privatekey())

        # OpenSSL fails to bring the cert back to us.  Groany mcgroan.
        self.assertTrue(isinstance(p12.get_certificate(), (X509, type(None))))

        # Oh ho.  It puts the certificate into the ca certificates list, in
        # fact.  Totally bogus, I would think.  Nevertheless, let's exploit
        # that to check to see if it reconstructed the certificate we expected
        # it to.  At some point, hopefully this will change so that
        # p12.get_certificate() is actually what returns the loaded
        # certificate.
        self.assertEqual(
            cleartextCertificatePEM,
            dump_certificate(FILETYPE_PEM, p12.get_ca_certificates()[0]))


    def gen_pkcs12(self, cert_pem=None, key_pem=None, ca_pem=None, friendly_name=None):
        """
        Generate a PKCS12 object with components from PEM.  Verify that the set
        functions return None.
        """
        p12 = PKCS12()
        if cert_pem:
            ret = p12.set_certificate(load_certificate(FILETYPE_PEM, cert_pem))
            self.assertEqual(ret, None)
        if key_pem:
            ret = p12.set_privatekey(load_privatekey(FILETYPE_PEM, key_pem))
            self.assertEqual(ret, None)
        if ca_pem:
            ret = p12.set_ca_certificates((load_certificate(FILETYPE_PEM, ca_pem),))
            self.assertEqual(ret, None)
        if friendly_name:
            ret = p12.set_friendlyname(friendly_name)
            self.assertEqual(ret, None)
        return p12


    def check_recovery(self, p12_str, key=None, cert=None, ca=None, passwd='',
                       extra=()):
        """
        Use openssl program to confirm three components are recoverable from a
        PKCS12 string.
        """
        if key:
            recovered_key = _runopenssl(
                p12_str, "pkcs12", '-nocerts', '-nodes', '-passin',
                'pass:' + passwd, *extra)
            self.assertEqual(recovered_key[-len(key):], key)
        if cert:
            recovered_cert = _runopenssl(
                p12_str, "pkcs12", '-clcerts', '-nodes', '-passin',
                'pass:' + passwd, '-nokeys', *extra)
            self.assertEqual(recovered_cert[-len(cert):], cert)
        if ca:
            recovered_cert = _runopenssl(
                p12_str, "pkcs12", '-cacerts', '-nodes', '-passin',
                'pass:' + passwd, '-nokeys', *extra)
            self.assertEqual(recovered_cert[-len(ca):], ca)


    def test_load_pkcs12(self):
        """
        A PKCS12 string generated using the openssl command line can be loaded
        with L{load_pkcs12} and its components extracted and examined.
        """
        passwd = 'whatever'
        pem = client_key_pem + client_cert_pem
        p12_str = _runopenssl(
            pem, "pkcs12", '-export', '-clcerts', '-passout', 'pass:' + passwd)
        p12 = load_pkcs12(p12_str, passwd)
        # verify
        self.assertTrue(isinstance(p12, PKCS12))
        cert_pem = dump_certificate(FILETYPE_PEM, p12.get_certificate())
        self.assertEqual(cert_pem, client_cert_pem)
        key_pem = dump_privatekey(FILETYPE_PEM, p12.get_privatekey())
        self.assertEqual(key_pem, client_key_pem)
        self.assertEqual(None, p12.get_ca_certificates())


    def test_load_pkcs12_garbage(self):
        """
        L{load_pkcs12} raises L{OpenSSL.crypto.Error} when passed a string
        which is not a PKCS12 dump.
        """
        passwd = 'whatever'
        e = self.assertRaises(Error, load_pkcs12, 'fruit loops', passwd)
        self.assertEqual( e.args[0][0][0], 'asn1 encoding routines')
        self.assertEqual( len(e.args[0][0]), 3)


    def test_replace(self):
        """
        L{PKCS12.set_certificate} replaces the certificate in a PKCS12 cluster.
        L{PKCS12.set_privatekey} replaces the private key.
        L{PKCS12.set_ca_certificates} replaces the CA certificates.
        """
        p12 = self.gen_pkcs12(client_cert_pem, client_key_pem, root_cert_pem)
        p12.set_certificate(load_certificate(FILETYPE_PEM, server_cert_pem))
        p12.set_privatekey(load_privatekey(FILETYPE_PEM, server_key_pem))
        root_cert = load_certificate(FILETYPE_PEM, root_cert_pem)
        client_cert = load_certificate(FILETYPE_PEM, client_cert_pem)
        p12.set_ca_certificates([root_cert]) # not a tuple
        self.assertEqual(1, len(p12.get_ca_certificates()))
        self.assertEqual(root_cert, p12.get_ca_certificates()[0])
        p12.set_ca_certificates([client_cert, root_cert])
        self.assertEqual(2, len(p12.get_ca_certificates()))
        self.assertEqual(client_cert, p12.get_ca_certificates()[0])
        self.assertEqual(root_cert, p12.get_ca_certificates()[1])


    def test_friendly_name(self):
        """
        The I{friendlyName} of a PKCS12 can be set and retrieved via
        L{PKCS12.get_friendlyname} and L{PKCS12_set_friendlyname}, and a
        L{PKCS12} with a friendly name set can be dumped with L{PKCS12.export}.
        """
        passwd = 'Dogmeat[]{}!@#$%^&*()~`?/.,<>-_+=";:'
        p12 = self.gen_pkcs12(server_cert_pem, server_key_pem, root_cert_pem)
        for friendly_name in [b('Serverlicious'), None, b('###')]:
            p12.set_friendlyname(friendly_name)
            self.assertEqual(p12.get_friendlyname(), friendly_name)
            dumped_p12 = p12.export(passphrase=passwd, iter=2, maciter=3)
            reloaded_p12 = load_pkcs12(dumped_p12, passwd)
            self.assertEqual(
                p12.get_friendlyname(), reloaded_p12.get_friendlyname())
            # We would use the openssl program to confirm the friendly
            # name, but it is not possible.  The pkcs12 command
            # does not store the friendly name in the cert's
            # alias, which we could then extract.
            self.check_recovery(
                dumped_p12, key=server_key_pem, cert=server_cert_pem,
                ca=root_cert_pem, passwd=passwd)


    def test_various_empty_passphrases(self):
        """
        Test that missing, None, and '' passphrases are identical for PKCS12
        export.
        """
        p12 = self.gen_pkcs12(client_cert_pem, client_key_pem, root_cert_pem)
        passwd = ''
        dumped_p12_empty = p12.export(iter=2, maciter=0, passphrase=passwd)
        dumped_p12_none = p12.export(iter=3, maciter=2, passphrase=None)
        dumped_p12_nopw = p12.export(iter=9, maciter=4)
        for dumped_p12 in [dumped_p12_empty, dumped_p12_none, dumped_p12_nopw]:
            self.check_recovery(
                dumped_p12, key=client_key_pem, cert=client_cert_pem,
                ca=root_cert_pem, passwd=passwd)


    def test_removing_ca_cert(self):
        """
        Passing C{None} to L{PKCS12.set_ca_certificates} removes all CA
        certificates.
        """
        p12 = self.gen_pkcs12(server_cert_pem, server_key_pem, root_cert_pem)
        p12.set_ca_certificates(None)
        self.assertEqual(None, p12.get_ca_certificates())


    def test_export_without_mac(self):
        """
        Exporting a PKCS12 with a C{maciter} of C{-1} excludes the MAC
        entirely.
        """
        passwd = 'Lake Michigan'
        p12 = self.gen_pkcs12(server_cert_pem, server_key_pem, root_cert_pem)
        dumped_p12 = p12.export(maciter=-1, passphrase=passwd, iter=2)
        self.check_recovery(
            dumped_p12, key=server_key_pem, cert=server_cert_pem,
            passwd=passwd, extra=('-nomacver',))


    def test_load_without_mac(self):
        """
        Loading a PKCS12 without a MAC does something other than crash.
        """
        passwd = 'Lake Michigan'
        p12 = self.gen_pkcs12(server_cert_pem, server_key_pem, root_cert_pem)
        dumped_p12 = p12.export(maciter=-1, passphrase=passwd, iter=2)
        try:
            recovered_p12 = load_pkcs12(dumped_p12, passwd)
            # The person who generated this PCKS12 should be flogged,
            # or better yet we should have a means to determine
            # whether a PCKS12 had a MAC that was verified.
            # Anyway, libopenssl chooses to allow it, so the
            # pyopenssl binding does as well.
            self.assertTrue(isinstance(recovered_p12, PKCS12))
        except Error:
            # Failing here with an exception is preferred as some openssl
            # versions do.
            pass


    def test_zero_len_list_for_ca(self):
        """
        A PKCS12 with an empty CA certificates list can be exported.
        """
        passwd = 'Hobie 18'
        p12 = self.gen_pkcs12(server_cert_pem, server_key_pem)
        p12.set_ca_certificates([])
        self.assertEqual((), p12.get_ca_certificates())
        dumped_p12 = p12.export(passphrase=passwd, iter=3)
        self.check_recovery(
            dumped_p12, key=server_key_pem, cert=server_cert_pem,
            passwd=passwd)


    def test_export_without_args(self):
        """
        All the arguments to L{PKCS12.export} are optional.
        """
        p12 = self.gen_pkcs12(server_cert_pem, server_key_pem, root_cert_pem)
        dumped_p12 = p12.export()  # no args
        self.check_recovery(
            dumped_p12, key=server_key_pem, cert=server_cert_pem, passwd='')


    def test_key_cert_mismatch(self):
        """
        L{PKCS12.export} raises an exception when a key and certificate
        mismatch.
        """
        p12 = self.gen_pkcs12(server_cert_pem, client_key_pem, root_cert_pem)
        self.assertRaises(Error, p12.export)



# These quoting functions taken directly from Twisted's twisted.python.win32.
_cmdLineQuoteRe = re.compile(r'(\\*)"')
_cmdLineQuoteRe2 = re.compile(r'(\\+)\Z')
def cmdLineQuote(s):
    """
    Internal method for quoting a single command-line argument.

    @type: C{str}
    @param s: A single unquoted string to quote for something that is expecting
        cmd.exe-style quoting

    @rtype: C{str}
    @return: A cmd.exe-style quoted string

    @see: U{http://www.perlmonks.org/?node_id=764004}
    """
    s = _cmdLineQuoteRe2.sub(r"\1\1", _cmdLineQuoteRe.sub(r'\1\1\\"', s))
    return '"%s"' % s



def quoteArguments(arguments):
    """
    Quote an iterable of command-line arguments for passing to CreateProcess or
    a similar API.  This allows the list passed to C{reactor.spawnProcess} to
    match the child process's C{sys.argv} properly.

    @type arguments: C{iterable} of C{str}
    @param arguments: An iterable of unquoted arguments to quote

    @rtype: C{str}
    @return: A space-delimited string containing quoted versions of L{arguments}
    """
    return ' '.join(map(cmdLineQuote, arguments))



def _runopenssl(pem, *args):
    """
    Run the command line openssl tool with the given arguments and write
    the given PEM to its stdin.  Not safe for quotes.
    """
    if os.name == 'posix':
        command = "openssl " + " ".join([
                "'%s'" % (arg.replace("'", "'\\''"),) for arg in args])
    else:
        command = "openssl " + quoteArguments(args)
    proc = Popen(command, shell=True, stdin=PIPE, stdout=PIPE)
    proc.stdin.write(pem)
    proc.stdin.close()
    return proc.stdout.read()



class FunctionTests(TestCase):
    """
    Tests for free-functions in the L{OpenSSL.crypto} module.
    """

    def test_load_privatekey_invalid_format(self):
        """
        L{load_privatekey} raises L{ValueError} if passed an unknown filetype.
        """
        self.assertRaises(ValueError, load_privatekey, 100, root_key_pem)


    def test_load_privatekey_invalid_passphrase_type(self):
        """
        L{load_privatekey} raises L{TypeError} if passed a passphrase that is
        neither a c{str} nor a callable.
        """
        self.assertRaises(
            TypeError,
            load_privatekey,
            FILETYPE_PEM, encryptedPrivateKeyPEMPassphrase, object())


    def test_load_privatekey_wrong_args(self):
        """
        L{load_privatekey} raises L{TypeError} if called with the wrong number
        of arguments.
        """
        self.assertRaises(TypeError, load_privatekey)


    def test_load_privatekey_wrongPassphrase(self):
        """
        L{load_privatekey} raises L{OpenSSL.crypto.Error} when it is passed an
        encrypted PEM and an incorrect passphrase.
        """
        self.assertRaises(
            Error,
            load_privatekey, FILETYPE_PEM, encryptedPrivateKeyPEM, b("quack"))


    def test_load_privatekey_passphrase(self):
        """
        L{load_privatekey} can create a L{PKey} object from an encrypted PEM
        string if given the passphrase.
        """
        key = load_privatekey(
            FILETYPE_PEM, encryptedPrivateKeyPEM,
            encryptedPrivateKeyPEMPassphrase)
        self.assertTrue(isinstance(key, PKeyType))


    def test_load_privatekey_wrongPassphraseCallback(self):
        """
        L{load_privatekey} raises L{OpenSSL.crypto.Error} when it is passed an
        encrypted PEM and a passphrase callback which returns an incorrect
        passphrase.
        """
        called = []
        def cb(*a):
            called.append(None)
            return "quack"
        self.assertRaises(
            Error,
            load_privatekey, FILETYPE_PEM, encryptedPrivateKeyPEM, cb)
        self.assertTrue(called)


    def test_load_privatekey_passphraseCallback(self):
        """
        L{load_privatekey} can create a L{PKey} object from an encrypted PEM
        string if given a passphrase callback which returns the correct
        password.
        """
        called = []
        def cb(writing):
            called.append(writing)
            return encryptedPrivateKeyPEMPassphrase
        key = load_privatekey(FILETYPE_PEM, encryptedPrivateKeyPEM, cb)
        self.assertTrue(isinstance(key, PKeyType))
        self.assertEqual(called, [False])


    def test_load_privatekey_passphrase_exception(self):
        """
        An exception raised by the passphrase callback passed to
        L{load_privatekey} causes L{OpenSSL.crypto.Error} to be raised.

        This isn't as nice as just letting the exception pass through.  The
        behavior might be changed to that eventually.
        """
        def broken(ignored):
            raise RuntimeError("This is not working.")
        self.assertRaises(
            Error,
            load_privatekey,
            FILETYPE_PEM, encryptedPrivateKeyPEM, broken)


    def test_dump_privatekey_wrong_args(self):
        """
        L{dump_privatekey} raises L{TypeError} if called with the wrong number
        of arguments.
        """
        self.assertRaises(TypeError, dump_privatekey)


    def test_dump_privatekey_unknown_cipher(self):
        """
        L{dump_privatekey} raises L{ValueError} if called with an unrecognized
        cipher name.
        """
        key = PKey()
        key.generate_key(TYPE_RSA, 512)
        self.assertRaises(
            ValueError, dump_privatekey,
            FILETYPE_PEM, key, "zippers", "passphrase")


    def test_dump_privatekey_invalid_passphrase_type(self):
        """
        L{dump_privatekey} raises L{TypeError} if called with a passphrase which
        is neither a C{str} nor a callable.
        """
        key = PKey()
        key.generate_key(TYPE_RSA, 512)
        self.assertRaises(
            TypeError,
            dump_privatekey, FILETYPE_PEM, key, "blowfish", object())


    def test_dump_privatekey_invalid_filetype(self):
        """
        L{dump_privatekey} raises L{ValueError} if called with an unrecognized
        filetype.
        """
        key = PKey()
        key.generate_key(TYPE_RSA, 512)
        self.assertRaises(ValueError, dump_privatekey, 100, key)


    def test_dump_privatekey_passphrase(self):
        """
        L{dump_privatekey} writes an encrypted PEM when given a passphrase.
        """
        passphrase = b("foo")
        key = load_privatekey(FILETYPE_PEM, cleartextPrivateKeyPEM)
        pem = dump_privatekey(FILETYPE_PEM, key, "blowfish", passphrase)
        self.assertTrue(isinstance(pem, bytes))
        loadedKey = load_privatekey(FILETYPE_PEM, pem, passphrase)
        self.assertTrue(isinstance(loadedKey, PKeyType))
        self.assertEqual(loadedKey.type(), key.type())
        self.assertEqual(loadedKey.bits(), key.bits())


    def test_dump_certificate(self):
        """
        L{dump_certificate} writes PEM, DER, and text.
        """
        pemData = cleartextCertificatePEM + cleartextPrivateKeyPEM
        cert = load_certificate(FILETYPE_PEM, pemData)
        dumped_pem = dump_certificate(FILETYPE_PEM, cert)
        self.assertEqual(dumped_pem, cleartextCertificatePEM)
        dumped_der = dump_certificate(FILETYPE_ASN1, cert)
        good_der = _runopenssl(dumped_pem, "x509", "-outform", "DER")
        self.assertEqual(dumped_der, good_der)
        cert2 = load_certificate(FILETYPE_ASN1, dumped_der)
        dumped_pem2 = dump_certificate(FILETYPE_PEM, cert2)
        self.assertEqual(dumped_pem2, cleartextCertificatePEM)
        dumped_text = dump_certificate(FILETYPE_TEXT, cert)
        good_text = _runopenssl(dumped_pem, "x509", "-noout", "-text")
        self.assertEqual(dumped_text, good_text)


    def test_dump_privatekey(self):
        """
        L{dump_privatekey} writes a PEM, DER, and text.
        """
        key = load_privatekey(FILETYPE_PEM, cleartextPrivateKeyPEM)
        self.assertTrue(key.check())
        dumped_pem = dump_privatekey(FILETYPE_PEM, key)
        self.assertEqual(dumped_pem, cleartextPrivateKeyPEM)
        dumped_der = dump_privatekey(FILETYPE_ASN1, key)
        # XXX This OpenSSL call writes "writing RSA key" to standard out.  Sad.
        good_der = _runopenssl(dumped_pem, "rsa", "-outform", "DER")
        self.assertEqual(dumped_der, good_der)
        key2 = load_privatekey(FILETYPE_ASN1, dumped_der)
        dumped_pem2 = dump_privatekey(FILETYPE_PEM, key2)
        self.assertEqual(dumped_pem2, cleartextPrivateKeyPEM)
        dumped_text = dump_privatekey(FILETYPE_TEXT, key)
        good_text = _runopenssl(dumped_pem, "rsa", "-noout", "-text")
        self.assertEqual(dumped_text, good_text)


    def test_dump_certificate_request(self):
        """
        L{dump_certificate_request} writes a PEM, DER, and text.
        """
        req = load_certificate_request(FILETYPE_PEM, cleartextCertificateRequestPEM)
        dumped_pem = dump_certificate_request(FILETYPE_PEM, req)
        self.assertEqual(dumped_pem, cleartextCertificateRequestPEM)
        dumped_der = dump_certificate_request(FILETYPE_ASN1, req)
        good_der = _runopenssl(dumped_pem, "req", "-outform", "DER")
        self.assertEqual(dumped_der, good_der)
        req2 = load_certificate_request(FILETYPE_ASN1, dumped_der)
        dumped_pem2 = dump_certificate_request(FILETYPE_PEM, req2)
        self.assertEqual(dumped_pem2, cleartextCertificateRequestPEM)
        dumped_text = dump_certificate_request(FILETYPE_TEXT, req)
        good_text = _runopenssl(dumped_pem, "req", "-noout", "-text")
        self.assertEqual(dumped_text, good_text)
        self.assertRaises(ValueError, dump_certificate_request, 100, req)


    def test_dump_privatekey_passphraseCallback(self):
        """
        L{dump_privatekey} writes an encrypted PEM when given a callback which
        returns the correct passphrase.
        """
        passphrase = b("foo")
        called = []
        def cb(writing):
            called.append(writing)
            return passphrase
        key = load_privatekey(FILETYPE_PEM, cleartextPrivateKeyPEM)
        pem = dump_privatekey(FILETYPE_PEM, key, "blowfish", cb)
        self.assertTrue(isinstance(pem, bytes))
        self.assertEqual(called, [True])
        loadedKey = load_privatekey(FILETYPE_PEM, pem, passphrase)
        self.assertTrue(isinstance(loadedKey, PKeyType))
        self.assertEqual(loadedKey.type(), key.type())
        self.assertEqual(loadedKey.bits(), key.bits())


    def test_load_pkcs7_data(self):
        """
        L{load_pkcs7_data} accepts a PKCS#7 string and returns an instance of
        L{PKCS7Type}.
        """
        pkcs7 = load_pkcs7_data(FILETYPE_PEM, pkcs7Data)
        self.assertTrue(isinstance(pkcs7, PKCS7Type))



class PKCS7Tests(TestCase):
    """
    Tests for L{PKCS7Type}.
    """
    def test_type(self):
        """
        L{PKCS7Type} is a type object.
        """
        self.assertTrue(isinstance(PKCS7Type, type))
        self.assertEqual(PKCS7Type.__name__, 'PKCS7')

        # XXX This doesn't currently work.
        # self.assertIdentical(PKCS7, PKCS7Type)


    # XXX Opposite results for all these following methods

    def test_type_is_signed_wrong_args(self):
        """
        L{PKCS7Type.type_is_signed} raises L{TypeError} if called with any
        arguments.
        """
        pkcs7 = load_pkcs7_data(FILETYPE_PEM, pkcs7Data)
        self.assertRaises(TypeError, pkcs7.type_is_signed, None)


    def test_type_is_signed(self):
        """
        L{PKCS7Type.type_is_signed} returns C{True} if the PKCS7 object is of
        the type I{signed}.
        """
        pkcs7 = load_pkcs7_data(FILETYPE_PEM, pkcs7Data)
        self.assertTrue(pkcs7.type_is_signed())


    def test_type_is_enveloped_wrong_args(self):
        """
        L{PKCS7Type.type_is_enveloped} raises L{TypeError} if called with any
        arguments.
        """
        pkcs7 = load_pkcs7_data(FILETYPE_PEM, pkcs7Data)
        self.assertRaises(TypeError, pkcs7.type_is_enveloped, None)


    def test_type_is_enveloped(self):
        """
        L{PKCS7Type.type_is_enveloped} returns C{False} if the PKCS7 object is
        not of the type I{enveloped}.
        """
        pkcs7 = load_pkcs7_data(FILETYPE_PEM, pkcs7Data)
        self.assertFalse(pkcs7.type_is_enveloped())


    def test_type_is_signedAndEnveloped_wrong_args(self):
        """
        L{PKCS7Type.type_is_signedAndEnveloped} raises L{TypeError} if called
        with any arguments.
        """
        pkcs7 = load_pkcs7_data(FILETYPE_PEM, pkcs7Data)
        self.assertRaises(TypeError, pkcs7.type_is_signedAndEnveloped, None)


    def test_type_is_signedAndEnveloped(self):
        """
        L{PKCS7Type.type_is_signedAndEnveloped} returns C{False} if the PKCS7
        object is not of the type I{signed and enveloped}.
        """
        pkcs7 = load_pkcs7_data(FILETYPE_PEM, pkcs7Data)
        self.assertFalse(pkcs7.type_is_signedAndEnveloped())


    def test_type_is_data(self):
        """
        L{PKCS7Type.type_is_data} returns C{False} if the PKCS7 object is not of
        the type data.
        """
        pkcs7 = load_pkcs7_data(FILETYPE_PEM, pkcs7Data)
        self.assertFalse(pkcs7.type_is_data())


    def test_type_is_data_wrong_args(self):
        """
        L{PKCS7Type.type_is_data} raises L{TypeError} if called with any
        arguments.
        """
        pkcs7 = load_pkcs7_data(FILETYPE_PEM, pkcs7Data)
        self.assertRaises(TypeError, pkcs7.type_is_data, None)


    def test_get_type_name_wrong_args(self):
        """
        L{PKCS7Type.get_type_name} raises L{TypeError} if called with any
        arguments.
        """
        pkcs7 = load_pkcs7_data(FILETYPE_PEM, pkcs7Data)
        self.assertRaises(TypeError, pkcs7.get_type_name, None)


    def test_get_type_name(self):
        """
        L{PKCS7Type.get_type_name} returns a C{str} giving the type name.
        """
        pkcs7 = load_pkcs7_data(FILETYPE_PEM, pkcs7Data)
        self.assertEquals(pkcs7.get_type_name(), b('pkcs7-signedData'))


    def test_attribute(self):
        """
        If an attribute other than one of the methods tested here is accessed on
        an instance of L{PKCS7Type}, L{AttributeError} is raised.
        """
        pkcs7 = load_pkcs7_data(FILETYPE_PEM, pkcs7Data)
        self.assertRaises(AttributeError, getattr, pkcs7, "foo")



class NetscapeSPKITests(TestCase, _PKeyInteractionTestsMixin):
    """
    Tests for L{OpenSSL.crypto.NetscapeSPKI}.
    """
    def signable(self):
        """
        Return a new L{NetscapeSPKI} for use with signing tests.
        """
        return NetscapeSPKI()


    def test_type(self):
        """
        L{NetscapeSPKI} and L{NetscapeSPKIType} refer to the same type object
        and can be used to create instances of that type.
        """
        self.assertIdentical(NetscapeSPKI, NetscapeSPKIType)
        self.assertConsistentType(NetscapeSPKI, 'NetscapeSPKI')


    def test_construction(self):
        """
        L{NetscapeSPKI} returns an instance of L{NetscapeSPKIType}.
        """
        nspki = NetscapeSPKI()
        self.assertTrue(isinstance(nspki, NetscapeSPKIType))


    def test_invalid_attribute(self):
        """
        Accessing a non-existent attribute of a L{NetscapeSPKI} instance causes
        an L{AttributeError} to be raised.
        """
        nspki = NetscapeSPKI()
        self.assertRaises(AttributeError, lambda: nspki.foo)


    def test_b64_encode(self):
        """
        L{NetscapeSPKI.b64_encode} encodes the certificate to a base64 blob.
        """
        nspki = NetscapeSPKI()
        blob = nspki.b64_encode()
        self.assertTrue(isinstance(blob, bytes))



class RevokedTests(TestCase):
    """
    Tests for L{OpenSSL.crypto.Revoked}
    """
    def test_construction(self):
        """
        Confirm we can create L{OpenSSL.crypto.Revoked}.  Check
        that it is empty.
        """
        revoked = Revoked()
        self.assertTrue(isinstance(revoked, Revoked))
        self.assertEquals(type(revoked), Revoked)
        self.assertEquals(revoked.get_serial(), b('00'))
        self.assertEquals(revoked.get_rev_date(), None)
        self.assertEquals(revoked.get_reason(), None)


    def test_construction_wrong_args(self):
        """
        Calling L{OpenSSL.crypto.Revoked} with any arguments results
        in a L{TypeError} being raised.
        """
        self.assertRaises(TypeError, Revoked, None)
        self.assertRaises(TypeError, Revoked, 1)
        self.assertRaises(TypeError, Revoked, "foo")


    def test_serial(self):
        """
        Confirm we can set and get serial numbers from
        L{OpenSSL.crypto.Revoked}.  Confirm errors are handled
        with grace.
        """
        revoked = Revoked()
        ret = revoked.set_serial(b('10b'))
        self.assertEquals(ret, None)
        ser = revoked.get_serial()
        self.assertEquals(ser, b('010B'))

        revoked.set_serial(b('31ppp'))  # a type error would be nice
        ser = revoked.get_serial()
        self.assertEquals(ser, b('31'))

        self.assertRaises(ValueError, revoked.set_serial, b('pqrst'))
        self.assertRaises(TypeError, revoked.set_serial, 100)
        self.assertRaises(TypeError, revoked.get_serial, 1)
        self.assertRaises(TypeError, revoked.get_serial, None)
        self.assertRaises(TypeError, revoked.get_serial, "")


    def test_date(self):
        """
        Confirm we can set and get revocation dates from
        L{OpenSSL.crypto.Revoked}.  Confirm errors are handled
        with grace.
        """
        revoked = Revoked()
        date = revoked.get_rev_date()
        self.assertEquals(date, None)

        now = b(datetime.now().strftime("%Y%m%d%H%M%SZ"))
        ret = revoked.set_rev_date(now)
        self.assertEqual(ret, None)
        date = revoked.get_rev_date()
        self.assertEqual(date, now)


    def test_reason(self):
        """
        Confirm we can set and get revocation reasons from
        L{OpenSSL.crypto.Revoked}.  The "get" need to work
        as "set".  Likewise, each reason of all_reasons() must work.
        """
        revoked = Revoked()
        for r in revoked.all_reasons():
            for x in range(2):
                ret = revoked.set_reason(r)
                self.assertEquals(ret, None)
                reason = revoked.get_reason()
                self.assertEquals(
                    reason.lower().replace(b(' '), b('')),
                    r.lower().replace(b(' '), b('')))
                r = reason # again with the resp of get

        revoked.set_reason(None)
        self.assertEqual(revoked.get_reason(), None)


    def test_set_reason_wrong_arguments(self):
        """
        Calling L{OpenSSL.crypto.Revoked.set_reason} with other than
        one argument, or an argument which isn't a valid reason,
        results in L{TypeError} or L{ValueError} being raised.
        """
        revoked = Revoked()
        self.assertRaises(TypeError, revoked.set_reason, 100)
        self.assertRaises(ValueError, revoked.set_reason, b('blue'))


    def test_get_reason_wrong_arguments(self):
        """
        Calling L{OpenSSL.crypto.Revoked.get_reason} with any
        arguments results in L{TypeError} being raised.
        """
        revoked = Revoked()
        self.assertRaises(TypeError, revoked.get_reason, None)
        self.assertRaises(TypeError, revoked.get_reason, 1)
        self.assertRaises(TypeError, revoked.get_reason, "foo")



class CRLTests(TestCase):
    """
    Tests for L{OpenSSL.crypto.CRL}
    """
    cert = load_certificate(FILETYPE_PEM, cleartextCertificatePEM)
    pkey = load_privatekey(FILETYPE_PEM, cleartextPrivateKeyPEM)

    def test_construction(self):
        """
        Confirm we can create L{OpenSSL.crypto.CRL}.  Check
        that it is empty
        """
        crl = CRL()
        self.assertTrue( isinstance(crl, CRL) )
        self.assertEqual(crl.get_revoked(), None)


    def test_construction_wrong_args(self):
        """
        Calling L{OpenSSL.crypto.CRL} with any number of arguments
        results in a L{TypeError} being raised.
        """
        self.assertRaises(TypeError, CRL, 1)
        self.assertRaises(TypeError, CRL, "")
        self.assertRaises(TypeError, CRL, None)


    def test_export(self):
        """
        Use python to create a simple CRL with a revocation, and export
        the CRL in formats of PEM, DER and text.  Those outputs are verified
        with the openssl program.
        """
        crl = CRL()
        revoked = Revoked()
        now = b(datetime.now().strftime("%Y%m%d%H%M%SZ"))
        revoked.set_rev_date(now)
        revoked.set_serial(b('3ab'))
        revoked.set_reason(b('sUpErSeDEd'))
        crl.add_revoked(revoked)

        # PEM format
        dumped_crl = crl.export(self.cert, self.pkey, days=20)
        text = _runopenssl(dumped_crl, "crl", "-noout", "-text")
        text.index(b('Serial Number: 03AB'))
        text.index(b('Superseded'))
        text.index(b('Issuer: /C=US/ST=IL/L=Chicago/O=Testing/CN=Testing Root CA'))

        # DER format
        dumped_crl = crl.export(self.cert, self.pkey, FILETYPE_ASN1)
        text = _runopenssl(dumped_crl, "crl", "-noout", "-text", "-inform", "DER")
        text.index(b('Serial Number: 03AB'))
        text.index(b('Superseded'))
        text.index(b('Issuer: /C=US/ST=IL/L=Chicago/O=Testing/CN=Testing Root CA'))

        # text format
        dumped_text = crl.export(self.cert, self.pkey, type=FILETYPE_TEXT)
        self.assertEqual(text, dumped_text)


    def test_add_revoked_keyword(self):
        """
        L{OpenSSL.CRL.add_revoked} accepts its single argument as the
        I{revoked} keyword argument.
        """
        crl = CRL()
        revoked = Revoked()
        crl.add_revoked(revoked=revoked)
        self.assertTrue(isinstance(crl.get_revoked()[0], Revoked))


    def test_export_wrong_args(self):
        """
        Calling L{OpenSSL.CRL.export} with fewer than two or more than
        four arguments, or with arguments other than the certificate,
        private key, integer file type, and integer number of days it
        expects, results in a L{TypeError} being raised.
        """
        crl = CRL()
        self.assertRaises(TypeError, crl.export)
        self.assertRaises(TypeError, crl.export, self.cert)
        self.assertRaises(TypeError, crl.export, self.cert, self.pkey, FILETYPE_PEM, 10, "foo")

        self.assertRaises(TypeError, crl.export, None, self.pkey, FILETYPE_PEM, 10)
        self.assertRaises(TypeError, crl.export, self.cert, None, FILETYPE_PEM, 10)
        self.assertRaises(TypeError, crl.export, self.cert, self.pkey, None, 10)
        self.assertRaises(TypeError, crl.export, self.cert, FILETYPE_PEM, None)


    def test_export_unknown_filetype(self):
        """
        Calling L{OpenSSL.CRL.export} with a file type other than
        L{FILETYPE_PEM}, L{FILETYPE_ASN1}, or L{FILETYPE_TEXT} results
        in a L{ValueError} being raised.
        """
        crl = CRL()
        self.assertRaises(ValueError, crl.export, self.cert, self.pkey, 100, 10)


    def test_get_revoked(self):
        """
        Use python to create a simple CRL with two revocations.
        Get back the L{Revoked} using L{OpenSSL.CRL.get_revoked} and
        verify them.
        """
        crl = CRL()

        revoked = Revoked()
        now = b(datetime.now().strftime("%Y%m%d%H%M%SZ"))
        revoked.set_rev_date(now)
        revoked.set_serial(b('3ab'))
        crl.add_revoked(revoked)
        revoked.set_serial(b('100'))
        revoked.set_reason(b('sUpErSeDEd'))
        crl.add_revoked(revoked)

        revs = crl.get_revoked()
        self.assertEqual(len(revs), 2)
        self.assertEqual(type(revs[0]), Revoked)
        self.assertEqual(type(revs[1]), Revoked)
        self.assertEqual(revs[0].get_serial(), b('03AB'))
        self.assertEqual(revs[1].get_serial(), b('0100'))
        self.assertEqual(revs[0].get_rev_date(), now)
        self.assertEqual(revs[1].get_rev_date(), now)


    def test_get_revoked_wrong_args(self):
        """
        Calling L{OpenSSL.CRL.get_revoked} with any arguments results
        in a L{TypeError} being raised.
        """
        crl = CRL()
        self.assertRaises(TypeError, crl.get_revoked, None)
        self.assertRaises(TypeError, crl.get_revoked, 1)
        self.assertRaises(TypeError, crl.get_revoked, "")
        self.assertRaises(TypeError, crl.get_revoked, "", 1, None)


    def test_add_revoked_wrong_args(self):
        """
        Calling L{OpenSSL.CRL.add_revoked} with other than one
        argument results in a L{TypeError} being raised.
        """
        crl = CRL()
        self.assertRaises(TypeError, crl.add_revoked)
        self.assertRaises(TypeError, crl.add_revoked, 1, 2)
        self.assertRaises(TypeError, crl.add_revoked, "foo", "bar")


    def test_load_crl(self):
        """
        Load a known CRL and inspect its revocations.  Both
        PEM and DER formats are loaded.
        """
        crl = load_crl(FILETYPE_PEM, crlData)
        revs = crl.get_revoked()
        self.assertEqual(len(revs), 2)
        self.assertEqual(revs[0].get_serial(), b('03AB'))
        self.assertEqual(revs[0].get_reason(), None)
        self.assertEqual(revs[1].get_serial(), b('0100'))
        self.assertEqual(revs[1].get_reason(), b('Superseded'))

        der = _runopenssl(crlData, "crl", "-outform", "DER")
        crl = load_crl(FILETYPE_ASN1, der)
        revs = crl.get_revoked()
        self.assertEqual(len(revs), 2)
        self.assertEqual(revs[0].get_serial(), b('03AB'))
        self.assertEqual(revs[0].get_reason(), None)
        self.assertEqual(revs[1].get_serial(), b('0100'))
        self.assertEqual(revs[1].get_reason(), b('Superseded'))


    def test_load_crl_wrong_args(self):
        """
        Calling L{OpenSSL.crypto.load_crl} with other than two
        arguments results in a L{TypeError} being raised.
        """
        self.assertRaises(TypeError, load_crl)
        self.assertRaises(TypeError, load_crl, FILETYPE_PEM)
        self.assertRaises(TypeError, load_crl, FILETYPE_PEM, crlData, None)


    def test_load_crl_bad_filetype(self):
        """
        Calling L{OpenSSL.crypto.load_crl} with an unknown file type
        raises a L{ValueError}.
        """
        self.assertRaises(ValueError, load_crl, 100, crlData)


    def test_load_crl_bad_data(self):
        """
        Calling L{OpenSSL.crypto.load_crl} with file data which can't
        be loaded raises a L{OpenSSL.crypto.Error}.
        """
        self.assertRaises(Error, load_crl, FILETYPE_PEM, "hello, world")


class SignVerifyTests(TestCase):
    """
    Tests for L{OpenSSL.crypto.sign} and L{OpenSSL.crypto.verify}.
    """
    def test_sign_verify(self):
        """
        L{sign} generates a cryptographic signature which L{verify} can check.
        """
        content = b(
            "It was a bright cold day in April, and the clocks were striking "
            "thirteen. Winston Smith, his chin nuzzled into his breast in an "
            "effort to escape the vile wind, slipped quickly through the "
            "glass doors of Victory Mansions, though not quickly enough to "
            "prevent a swirl of gritty dust from entering along with him.")

        # sign the content with this private key
        priv_key = load_privatekey(FILETYPE_PEM, root_key_pem)
        # verify the content with this cert
        good_cert = load_certificate(FILETYPE_PEM, root_cert_pem)
        # certificate unrelated to priv_key, used to trigger an error
        bad_cert = load_certificate(FILETYPE_PEM, server_cert_pem)

        for digest in ['md5', 'sha1']:
            sig = sign(priv_key, content, digest)

            # Verify the signature of content, will throw an exception if error.
            verify(good_cert, sig, content, digest)

            # This should fail because the certificate doesn't match the
            # private key that was used to sign the content.
            self.assertRaises(Error, verify, bad_cert, sig, content, digest)

            # This should fail because we've "tainted" the content after
            # signing it.
            self.assertRaises(
                Error, verify,
                good_cert, sig, content + b("tainted"), digest)

        # test that unknown digest types fail
        self.assertRaises(
            ValueError, sign, priv_key, content, "strange-digest")
        self.assertRaises(
            ValueError, verify, good_cert, sig, content, "strange-digest")


    def test_sign_nulls(self):
        """
        L{sign} produces a signature for a string with embedded nulls.
        """
        content = b("Watch out!  \0  Did you see it?")
        priv_key = load_privatekey(FILETYPE_PEM, root_key_pem)
        good_cert = load_certificate(FILETYPE_PEM, root_cert_pem)
        sig = sign(priv_key, content, "sha1")
        verify(good_cert, sig, content, "sha1")


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_rand
# Copyright (c) Frederick Dean
# See LICENSE for details.

"""
Unit tests for L{OpenSSL.rand}.
"""

from unittest import main
import os
import stat

from OpenSSL.test.util import TestCase, b
from OpenSSL import rand


class RandTests(TestCase):
    def test_bytes_wrong_args(self):
        """
        L{OpenSSL.rand.bytes} raises L{TypeError} if called with the wrong
        number of arguments or with a non-C{int} argument.
        """
        self.assertRaises(TypeError, rand.bytes)
        self.assertRaises(TypeError, rand.bytes, None)
        self.assertRaises(TypeError, rand.bytes, 3, None)

    # XXX Test failure of the malloc() in rand_bytes.

    def test_bytes(self):
        """
        Verify that we can obtain bytes from rand_bytes() and
        that they are different each time.  Test the parameter
        of rand_bytes() for bad values.
        """
        b1 = rand.bytes(50)
        self.assertEqual(len(b1), 50)
        b2 = rand.bytes(num_bytes=50)  # parameter by name
        self.assertNotEqual(b1, b2)  #  Hip, Hip, Horay! FIPS complaince
        b3 = rand.bytes(num_bytes=0)
        self.assertEqual(len(b3), 0)
        exc = self.assertRaises(ValueError, rand.bytes, -1)
        self.assertEqual(str(exc), "num_bytes must not be negative")


    def test_add_wrong_args(self):
        """
        When called with the wrong number of arguments, or with arguments not of
        type C{str} and C{int}, L{OpenSSL.rand.add} raises L{TypeError}.
        """
        self.assertRaises(TypeError, rand.add)
        self.assertRaises(TypeError, rand.add, b("foo"), None)
        self.assertRaises(TypeError, rand.add, None, 3)
        self.assertRaises(TypeError, rand.add, b("foo"), 3, None)


    def test_add(self):
        """
        L{OpenSSL.rand.add} adds entropy to the PRNG.
        """
        rand.add(b('hamburger'), 3)


    def test_seed_wrong_args(self):
        """
        When called with the wrong number of arguments, or with a non-C{str}
        argument, L{OpenSSL.rand.seed} raises L{TypeError}.
        """
        self.assertRaises(TypeError, rand.seed)
        self.assertRaises(TypeError, rand.seed, None)
        self.assertRaises(TypeError, rand.seed, b("foo"), None)


    def test_seed(self):
        """
        L{OpenSSL.rand.seed} adds entropy to the PRNG.
        """
        rand.seed(b('milk shake'))


    def test_status_wrong_args(self):
        """
        L{OpenSSL.rand.status} raises L{TypeError} when called with any
        arguments.
        """
        self.assertRaises(TypeError, rand.status, None)


    def test_status(self):
        """
        L{OpenSSL.rand.status} returns C{True} if the PRNG has sufficient
        entropy, C{False} otherwise.
        """
        # It's hard to know what it is actually going to return.  Different
        # OpenSSL random engines decide differently whether they have enough
        # entropy or not.
        self.assertTrue(rand.status() in (1, 2))


    def test_egd_wrong_args(self):
        """
        L{OpenSSL.rand.egd} raises L{TypeError} when called with the wrong
        number of arguments or with arguments not of type C{str} and C{int}.
        """
        self.assertRaises(TypeError, rand.egd)
        self.assertRaises(TypeError, rand.egd, None)
        self.assertRaises(TypeError, rand.egd, "foo", None)
        self.assertRaises(TypeError, rand.egd, None, 3)
        self.assertRaises(TypeError, rand.egd, "foo", 3, None)


    def test_egd_missing(self):
        """
        L{OpenSSL.rand.egd} returns C{0} or C{-1} if the EGD socket passed
        to it does not exist.
        """
        result = rand.egd(self.mktemp())
        expected = (-1, 0)
        self.assertTrue(
            result in expected,
            "%r not in %r" % (result, expected))


    def test_cleanup_wrong_args(self):
        """
        L{OpenSSL.rand.cleanup} raises L{TypeError} when called with any
        arguments.
        """
        self.assertRaises(TypeError, rand.cleanup, None)


    def test_cleanup(self):
        """
        L{OpenSSL.rand.cleanup} releases the memory used by the PRNG and returns
        C{None}.
        """
        self.assertIdentical(rand.cleanup(), None)


    def test_load_file_wrong_args(self):
        """
        L{OpenSSL.rand.load_file} raises L{TypeError} when called the wrong
        number of arguments or arguments not of type C{str} and C{int}.
        """
        self.assertRaises(TypeError, rand.load_file)
        self.assertRaises(TypeError, rand.load_file, "foo", None)
        self.assertRaises(TypeError, rand.load_file, None, 1)
        self.assertRaises(TypeError, rand.load_file, "foo", 1, None)


    def test_write_file_wrong_args(self):
        """
        L{OpenSSL.rand.write_file} raises L{TypeError} when called with the
        wrong number of arguments or a non-C{str} argument.
        """
        self.assertRaises(TypeError, rand.write_file)
        self.assertRaises(TypeError, rand.write_file, None)
        self.assertRaises(TypeError, rand.write_file, "foo", None)


    def test_files(self):
        """
        Test reading and writing of files via rand functions.
        """
        # Write random bytes to a file
        tmpfile = self.mktemp()
        # Make sure it exists (so cleanup definitely succeeds)
        fObj = open(tmpfile, 'w')
        fObj.close()
        try:
            rand.write_file(tmpfile)
            # Verify length of written file
            size = os.stat(tmpfile)[stat.ST_SIZE]
            self.assertEquals(size, 1024)
            # Read random bytes from file
            rand.load_file(tmpfile)
            rand.load_file(tmpfile, 4)  # specify a length
        finally:
            # Cleanup
            os.unlink(tmpfile)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_ssl
# Copyright (C) Jean-Paul Calderone
# See LICENSE for details.

"""
Unit tests for L{OpenSSL.SSL}.
"""

from gc import collect
from errno import ECONNREFUSED, EINPROGRESS, EWOULDBLOCK
from sys import platform, version_info
from socket import error, socket
from os import makedirs
from os.path import join
from unittest import main
from weakref import ref

from OpenSSL.crypto import TYPE_RSA, FILETYPE_PEM
from OpenSSL.crypto import PKey, X509, X509Extension
from OpenSSL.crypto import dump_privatekey, load_privatekey
from OpenSSL.crypto import dump_certificate, load_certificate

from OpenSSL.SSL import OPENSSL_VERSION_NUMBER, SSLEAY_VERSION, SSLEAY_CFLAGS
from OpenSSL.SSL import SSLEAY_PLATFORM, SSLEAY_DIR, SSLEAY_BUILT_ON
from OpenSSL.SSL import SENT_SHUTDOWN, RECEIVED_SHUTDOWN
from OpenSSL.SSL import SSLv2_METHOD, SSLv3_METHOD, SSLv23_METHOD, TLSv1_METHOD
from OpenSSL.SSL import OP_NO_SSLv2, OP_NO_SSLv3, OP_SINGLE_DH_USE
from OpenSSL.SSL import (
    VERIFY_PEER, VERIFY_FAIL_IF_NO_PEER_CERT, VERIFY_CLIENT_ONCE, VERIFY_NONE)
from OpenSSL.SSL import (
    Error, SysCallError, WantReadError, ZeroReturnError, SSLeay_version)
from OpenSSL.SSL import Context, ContextType, Connection, ConnectionType

from OpenSSL.test.util import TestCase, bytes, b
from OpenSSL.test.test_crypto import (
    cleartextCertificatePEM, cleartextPrivateKeyPEM)
from OpenSSL.test.test_crypto import (
    client_cert_pem, client_key_pem, server_cert_pem, server_key_pem,
    root_cert_pem)

try:
    from OpenSSL.SSL import OP_NO_QUERY_MTU
except ImportError:
    OP_NO_QUERY_MTU = None
try:
    from OpenSSL.SSL import OP_COOKIE_EXCHANGE
except ImportError:
    OP_COOKIE_EXCHANGE = None
try:
    from OpenSSL.SSL import OP_NO_TICKET
except ImportError:
    OP_NO_TICKET = None

from OpenSSL.SSL import (
    SSL_ST_CONNECT, SSL_ST_ACCEPT, SSL_ST_MASK, SSL_ST_INIT, SSL_ST_BEFORE,
    SSL_ST_OK, SSL_ST_RENEGOTIATE,
    SSL_CB_LOOP, SSL_CB_EXIT, SSL_CB_READ, SSL_CB_WRITE, SSL_CB_ALERT,
    SSL_CB_READ_ALERT, SSL_CB_WRITE_ALERT, SSL_CB_ACCEPT_LOOP,
    SSL_CB_ACCEPT_EXIT, SSL_CB_CONNECT_LOOP, SSL_CB_CONNECT_EXIT,
    SSL_CB_HANDSHAKE_START, SSL_CB_HANDSHAKE_DONE)

# openssl dhparam 128 -out dh-128.pem (note that 128 is a small number of bits
# to use)
dhparam = """\
-----BEGIN DH PARAMETERS-----
MBYCEQCobsg29c9WZP/54oAPcwiDAgEC
-----END DH PARAMETERS-----
"""


def verify_cb(conn, cert, errnum, depth, ok):
    return ok


def socket_pair():
    """
    Establish and return a pair of network sockets connected to each other.
    """
    # Connect a pair of sockets
    port = socket()
    port.bind(('', 0))
    port.listen(1)
    client = socket()
    client.setblocking(False)
    client.connect_ex(("127.0.0.1", port.getsockname()[1]))
    client.setblocking(True)
    server = port.accept()[0]

    # Let's pass some unencrypted data to make sure our socket connection is
    # fine.  Just one byte, so we don't have to worry about buffers getting
    # filled up or fragmentation.
    server.send(b("x"))
    assert client.recv(1024) == b("x")
    client.send(b("y"))
    assert server.recv(1024) == b("y")

    # Most of our callers want non-blocking sockets, make it easy for them.
    server.setblocking(False)
    client.setblocking(False)

    return (server, client)



def handshake(client, server):
    conns = [client, server]
    while conns:
        for conn in conns:
            try:
                conn.do_handshake()
            except WantReadError:
                pass
            else:
                conns.remove(conn)


def _create_certificate_chain():
    """
    Construct and return a chain of certificates.

        1. A new self-signed certificate authority certificate (cacert)
        2. A new intermediate certificate signed by cacert (icert)
        3. A new server certificate signed by icert (scert)
    """
    caext = X509Extension(b('basicConstraints'), False, b('CA:true'))

    # Step 1
    cakey = PKey()
    cakey.generate_key(TYPE_RSA, 512)
    cacert = X509()
    cacert.get_subject().commonName = "Authority Certificate"
    cacert.set_issuer(cacert.get_subject())
    cacert.set_pubkey(cakey)
    cacert.set_notBefore(b("20000101000000Z"))
    cacert.set_notAfter(b("20200101000000Z"))
    cacert.add_extensions([caext])
    cacert.set_serial_number(0)
    cacert.sign(cakey, "sha1")

    # Step 2
    ikey = PKey()
    ikey.generate_key(TYPE_RSA, 512)
    icert = X509()
    icert.get_subject().commonName = "Intermediate Certificate"
    icert.set_issuer(cacert.get_subject())
    icert.set_pubkey(ikey)
    icert.set_notBefore(b("20000101000000Z"))
    icert.set_notAfter(b("20200101000000Z"))
    icert.add_extensions([caext])
    icert.set_serial_number(0)
    icert.sign(cakey, "sha1")

    # Step 3
    skey = PKey()
    skey.generate_key(TYPE_RSA, 512)
    scert = X509()
    scert.get_subject().commonName = "Server Certificate"
    scert.set_issuer(icert.get_subject())
    scert.set_pubkey(skey)
    scert.set_notBefore(b("20000101000000Z"))
    scert.set_notAfter(b("20200101000000Z"))
    scert.add_extensions([
            X509Extension(b('basicConstraints'), True, b('CA:false'))])
    scert.set_serial_number(0)
    scert.sign(ikey, "sha1")

    return [(cakey, cacert), (ikey, icert), (skey, scert)]



class _LoopbackMixin:
    """
    Helper mixin which defines methods for creating a connected socket pair and
    for forcing two connected SSL sockets to talk to each other via memory BIOs.
    """
    def _loopback(self):
        (server, client) = socket_pair()

        ctx = Context(TLSv1_METHOD)
        ctx.use_privatekey(load_privatekey(FILETYPE_PEM, server_key_pem))
        ctx.use_certificate(load_certificate(FILETYPE_PEM, server_cert_pem))
        server = Connection(ctx, server)
        server.set_accept_state()
        client = Connection(Context(TLSv1_METHOD), client)
        client.set_connect_state()

        handshake(client, server)

        server.setblocking(True)
        client.setblocking(True)
        return server, client


    def _interactInMemory(self, client_conn, server_conn):
        """
        Try to read application bytes from each of the two L{Connection}
        objects.  Copy bytes back and forth between their send/receive buffers
        for as long as there is anything to copy.  When there is nothing more
        to copy, return C{None}.  If one of them actually manages to deliver
        some application bytes, return a two-tuple of the connection from which
        the bytes were read and the bytes themselves.
        """
        wrote = True
        while wrote:
            # Loop until neither side has anything to say
            wrote = False

            # Copy stuff from each side's send buffer to the other side's
            # receive buffer.
            for (read, write) in [(client_conn, server_conn),
                                  (server_conn, client_conn)]:

                # Give the side a chance to generate some more bytes, or
                # succeed.
                try:
                    data = read.recv(2 ** 16)
                except WantReadError:
                    # It didn't succeed, so we'll hope it generated some
                    # output.
                    pass
                else:
                    # It did succeed, so we'll stop now and let the caller deal
                    # with it.
                    return (read, data)

                while True:
                    # Keep copying as long as there's more stuff there.
                    try:
                        dirty = read.bio_read(4096)
                    except WantReadError:
                        # Okay, nothing more waiting to be sent.  Stop
                        # processing this send buffer.
                        break
                    else:
                        # Keep track of the fact that someone generated some
                        # output.
                        wrote = True
                        write.bio_write(dirty)



class VersionTests(TestCase):
    """
    Tests for version information exposed by
    L{OpenSSL.SSL.SSLeay_version} and
    L{OpenSSL.SSL.OPENSSL_VERSION_NUMBER}.
    """
    def test_OPENSSL_VERSION_NUMBER(self):
        """
        L{OPENSSL_VERSION_NUMBER} is an integer with status in the low
        byte and the patch, fix, minor, and major versions in the
        nibbles above that.
        """
        self.assertTrue(isinstance(OPENSSL_VERSION_NUMBER, int))


    def test_SSLeay_version(self):
        """
        L{SSLeay_version} takes a version type indicator and returns
        one of a number of version strings based on that indicator.
        """
        versions = {}
        for t in [SSLEAY_VERSION, SSLEAY_CFLAGS, SSLEAY_BUILT_ON,
                  SSLEAY_PLATFORM, SSLEAY_DIR]:
            version = SSLeay_version(t)
            versions[version] = t
            self.assertTrue(isinstance(version, bytes))
        self.assertEqual(len(versions), 5)



class ContextTests(TestCase, _LoopbackMixin):
    """
    Unit tests for L{OpenSSL.SSL.Context}.
    """
    def test_method(self):
        """
        L{Context} can be instantiated with one of L{SSLv2_METHOD},
        L{SSLv3_METHOD}, L{SSLv23_METHOD}, or L{TLSv1_METHOD}.
        """
        for meth in [SSLv3_METHOD, SSLv23_METHOD, TLSv1_METHOD]:
            Context(meth)

        try:
            Context(SSLv2_METHOD)
        except ValueError:
            # Some versions of OpenSSL have SSLv2, some don't.
            # Difficult to say in advance.
            pass

        self.assertRaises(TypeError, Context, "")
        self.assertRaises(ValueError, Context, 10)


    def test_type(self):
        """
        L{Context} and L{ContextType} refer to the same type object and can be
        used to create instances of that type.
        """
        self.assertIdentical(Context, ContextType)
        self.assertConsistentType(Context, 'Context', TLSv1_METHOD)


    def test_use_privatekey(self):
        """
        L{Context.use_privatekey} takes an L{OpenSSL.crypto.PKey} instance.
        """
        key = PKey()
        key.generate_key(TYPE_RSA, 128)
        ctx = Context(TLSv1_METHOD)
        ctx.use_privatekey(key)
        self.assertRaises(TypeError, ctx.use_privatekey, "")


    def test_set_app_data_wrong_args(self):
        """
        L{Context.set_app_data} raises L{TypeError} if called with other than
        one argument.
        """
        context = Context(TLSv1_METHOD)
        self.assertRaises(TypeError, context.set_app_data)
        self.assertRaises(TypeError, context.set_app_data, None, None)


    def test_get_app_data_wrong_args(self):
        """
        L{Context.get_app_data} raises L{TypeError} if called with any
        arguments.
        """
        context = Context(TLSv1_METHOD)
        self.assertRaises(TypeError, context.get_app_data, None)


    def test_app_data(self):
        """
        L{Context.set_app_data} stores an object for later retrieval using
        L{Context.get_app_data}.
        """
        app_data = object()
        context = Context(TLSv1_METHOD)
        context.set_app_data(app_data)
        self.assertIdentical(context.get_app_data(), app_data)


    def test_set_options_wrong_args(self):
        """
        L{Context.set_options} raises L{TypeError} if called with the wrong
        number of arguments or a non-C{int} argument.
        """
        context = Context(TLSv1_METHOD)
        self.assertRaises(TypeError, context.set_options)
        self.assertRaises(TypeError, context.set_options, None)
        self.assertRaises(TypeError, context.set_options, 1, None)


    def test_set_timeout_wrong_args(self):
        """
        L{Context.set_timeout} raises L{TypeError} if called with the wrong
        number of arguments or a non-C{int} argument.
        """
        context = Context(TLSv1_METHOD)
        self.assertRaises(TypeError, context.set_timeout)
        self.assertRaises(TypeError, context.set_timeout, None)
        self.assertRaises(TypeError, context.set_timeout, 1, None)


    def test_get_timeout_wrong_args(self):
        """
        L{Context.get_timeout} raises L{TypeError} if called with any arguments.
        """
        context = Context(TLSv1_METHOD)
        self.assertRaises(TypeError, context.get_timeout, None)


    def test_timeout(self):
        """
        L{Context.set_timeout} sets the session timeout for all connections
        created using the context object.  L{Context.get_timeout} retrieves this
        value.
        """
        context = Context(TLSv1_METHOD)
        context.set_timeout(1234)
        self.assertEquals(context.get_timeout(), 1234)


    def test_set_verify_depth_wrong_args(self):
        """
        L{Context.set_verify_depth} raises L{TypeError} if called with the wrong
        number of arguments or a non-C{int} argument.
        """
        context = Context(TLSv1_METHOD)
        self.assertRaises(TypeError, context.set_verify_depth)
        self.assertRaises(TypeError, context.set_verify_depth, None)
        self.assertRaises(TypeError, context.set_verify_depth, 1, None)


    def test_get_verify_depth_wrong_args(self):
        """
        L{Context.get_verify_depth} raises L{TypeError} if called with any arguments.
        """
        context = Context(TLSv1_METHOD)
        self.assertRaises(TypeError, context.get_verify_depth, None)


    def test_verify_depth(self):
        """
        L{Context.set_verify_depth} sets the number of certificates in a chain
        to follow before giving up.  The value can be retrieved with
        L{Context.get_verify_depth}.
        """
        context = Context(TLSv1_METHOD)
        context.set_verify_depth(11)
        self.assertEquals(context.get_verify_depth(), 11)


    def _write_encrypted_pem(self, passphrase):
        """
        Write a new private key out to a new file, encrypted using the given
        passphrase.  Return the path to the new file.
        """
        key = PKey()
        key.generate_key(TYPE_RSA, 128)
        pemFile = self.mktemp()
        fObj = open(pemFile, 'w')
        pem = dump_privatekey(FILETYPE_PEM, key, "blowfish", passphrase)
        fObj.write(pem.decode('ascii'))
        fObj.close()
        return pemFile


    def test_set_passwd_cb_wrong_args(self):
        """
        L{Context.set_passwd_cb} raises L{TypeError} if called with the
        wrong arguments or with a non-callable first argument.
        """
        context = Context(TLSv1_METHOD)
        self.assertRaises(TypeError, context.set_passwd_cb)
        self.assertRaises(TypeError, context.set_passwd_cb, None)
        self.assertRaises(TypeError, context.set_passwd_cb, lambda: None, None, None)


    def test_set_passwd_cb(self):
        """
        L{Context.set_passwd_cb} accepts a callable which will be invoked when
        a private key is loaded from an encrypted PEM.
        """
        passphrase = b("foobar")
        pemFile = self._write_encrypted_pem(passphrase)
        calledWith = []
        def passphraseCallback(maxlen, verify, extra):
            calledWith.append((maxlen, verify, extra))
            return passphrase
        context = Context(TLSv1_METHOD)
        context.set_passwd_cb(passphraseCallback)
        context.use_privatekey_file(pemFile)
        self.assertTrue(len(calledWith), 1)
        self.assertTrue(isinstance(calledWith[0][0], int))
        self.assertTrue(isinstance(calledWith[0][1], int))
        self.assertEqual(calledWith[0][2], None)


    def test_passwd_callback_exception(self):
        """
        L{Context.use_privatekey_file} propagates any exception raised by the
        passphrase callback.
        """
        pemFile = self._write_encrypted_pem(b("monkeys are nice"))
        def passphraseCallback(maxlen, verify, extra):
            raise RuntimeError("Sorry, I am a fail.")

        context = Context(TLSv1_METHOD)
        context.set_passwd_cb(passphraseCallback)
        self.assertRaises(RuntimeError, context.use_privatekey_file, pemFile)


    def test_passwd_callback_false(self):
        """
        L{Context.use_privatekey_file} raises L{OpenSSL.SSL.Error} if the
        passphrase callback returns a false value.
        """
        pemFile = self._write_encrypted_pem(b("monkeys are nice"))
        def passphraseCallback(maxlen, verify, extra):
            return None

        context = Context(TLSv1_METHOD)
        context.set_passwd_cb(passphraseCallback)
        self.assertRaises(Error, context.use_privatekey_file, pemFile)


    def test_passwd_callback_non_string(self):
        """
        L{Context.use_privatekey_file} raises L{OpenSSL.SSL.Error} if the
        passphrase callback returns a true non-string value.
        """
        pemFile = self._write_encrypted_pem(b("monkeys are nice"))
        def passphraseCallback(maxlen, verify, extra):
            return 10

        context = Context(TLSv1_METHOD)
        context.set_passwd_cb(passphraseCallback)
        self.assertRaises(Error, context.use_privatekey_file, pemFile)


    def test_passwd_callback_too_long(self):
        """
        If the passphrase returned by the passphrase callback returns a string
        longer than the indicated maximum length, it is truncated.
        """
        # A priori knowledge!
        passphrase = b("x") * 1024
        pemFile = self._write_encrypted_pem(passphrase)
        def passphraseCallback(maxlen, verify, extra):
            assert maxlen == 1024
            return passphrase + b("y")

        context = Context(TLSv1_METHOD)
        context.set_passwd_cb(passphraseCallback)
        # This shall succeed because the truncated result is the correct
        # passphrase.
        context.use_privatekey_file(pemFile)


    def test_set_info_callback(self):
        """
        L{Context.set_info_callback} accepts a callable which will be invoked
        when certain information about an SSL connection is available.
        """
        (server, client) = socket_pair()

        clientSSL = Connection(Context(TLSv1_METHOD), client)
        clientSSL.set_connect_state()

        called = []
        def info(conn, where, ret):
            called.append((conn, where, ret))
        context = Context(TLSv1_METHOD)
        context.set_info_callback(info)
        context.use_certificate(
            load_certificate(FILETYPE_PEM, cleartextCertificatePEM))
        context.use_privatekey(
            load_privatekey(FILETYPE_PEM, cleartextPrivateKeyPEM))

        serverSSL = Connection(context, server)
        serverSSL.set_accept_state()

        while not called:
            for ssl in clientSSL, serverSSL:
                try:
                    ssl.do_handshake()
                except WantReadError:
                    pass

        # Kind of lame.  Just make sure it got called somehow.
        self.assertTrue(called)


    def _load_verify_locations_test(self, *args):
        """
        Create a client context which will verify the peer certificate and call
        its C{load_verify_locations} method with C{*args}.  Then connect it to a
        server and ensure that the handshake succeeds.
        """
        (server, client) = socket_pair()

        clientContext = Context(TLSv1_METHOD)
        clientContext.load_verify_locations(*args)
        # Require that the server certificate verify properly or the
        # connection will fail.
        clientContext.set_verify(
            VERIFY_PEER,
            lambda conn, cert, errno, depth, preverify_ok: preverify_ok)

        clientSSL = Connection(clientContext, client)
        clientSSL.set_connect_state()

        serverContext = Context(TLSv1_METHOD)
        serverContext.use_certificate(
            load_certificate(FILETYPE_PEM, cleartextCertificatePEM))
        serverContext.use_privatekey(
            load_privatekey(FILETYPE_PEM, cleartextPrivateKeyPEM))

        serverSSL = Connection(serverContext, server)
        serverSSL.set_accept_state()

        # Without load_verify_locations above, the handshake
        # will fail:
        # Error: [('SSL routines', 'SSL3_GET_SERVER_CERTIFICATE',
        #          'certificate verify failed')]
        handshake(clientSSL, serverSSL)

        cert = clientSSL.get_peer_certificate()
        self.assertEqual(cert.get_subject().CN, 'Testing Root CA')


    def test_load_verify_file(self):
        """
        L{Context.load_verify_locations} accepts a file name and uses the
        certificates within for verification purposes.
        """
        cafile = self.mktemp()
        fObj = open(cafile, 'w')
        fObj.write(cleartextCertificatePEM.decode('ascii'))
        fObj.close()

        self._load_verify_locations_test(cafile)


    def test_load_verify_invalid_file(self):
        """
        L{Context.load_verify_locations} raises L{Error} when passed a
        non-existent cafile.
        """
        clientContext = Context(TLSv1_METHOD)
        self.assertRaises(
            Error, clientContext.load_verify_locations, self.mktemp())


    def test_load_verify_directory(self):
        """
        L{Context.load_verify_locations} accepts a directory name and uses
        the certificates within for verification purposes.
        """
        capath = self.mktemp()
        makedirs(capath)
        # Hash values computed manually with c_rehash to avoid depending on
        # c_rehash in the test suite.  One is from OpenSSL 0.9.8, the other
        # from OpenSSL 1.0.0.
        for name in ['c7adac82.0', 'c3705638.0']:
            cafile = join(capath, name)
            fObj = open(cafile, 'w')
            fObj.write(cleartextCertificatePEM.decode('ascii'))
            fObj.close()

        self._load_verify_locations_test(None, capath)


    def test_load_verify_locations_wrong_args(self):
        """
        L{Context.load_verify_locations} raises L{TypeError} if called with
        the wrong number of arguments or with non-C{str} arguments.
        """
        context = Context(TLSv1_METHOD)
        self.assertRaises(TypeError, context.load_verify_locations)
        self.assertRaises(TypeError, context.load_verify_locations, object())
        self.assertRaises(TypeError, context.load_verify_locations, object(), object())
        self.assertRaises(TypeError, context.load_verify_locations, None, None, None)


    if platform == "win32":
        "set_default_verify_paths appears not to work on Windows.  "
        "See LP#404343 and LP#404344."
    else:
        def test_set_default_verify_paths(self):
            """
            L{Context.set_default_verify_paths} causes the platform-specific CA
            certificate locations to be used for verification purposes.
            """
            # Testing this requires a server with a certificate signed by one of
            # the CAs in the platform CA location.  Getting one of those costs
            # money.  Fortunately (or unfortunately, depending on your
            # perspective), it's easy to think of a public server on the
            # internet which has such a certificate.  Connecting to the network
            # in a unit test is bad, but it's the only way I can think of to
            # really test this. -exarkun

            # Arg, verisign.com doesn't speak TLSv1
            context = Context(SSLv3_METHOD)
            context.set_default_verify_paths()
            context.set_verify(
                VERIFY_PEER,
                lambda conn, cert, errno, depth, preverify_ok: preverify_ok)

            client = socket()
            client.connect(('verisign.com', 443))
            clientSSL = Connection(context, client)
            clientSSL.set_connect_state()
            clientSSL.do_handshake()
            clientSSL.send('GET / HTTP/1.0\r\n\r\n')
            self.assertTrue(clientSSL.recv(1024))


    def test_set_default_verify_paths_signature(self):
        """
        L{Context.set_default_verify_paths} takes no arguments and raises
        L{TypeError} if given any.
        """
        context = Context(TLSv1_METHOD)
        self.assertRaises(TypeError, context.set_default_verify_paths, None)
        self.assertRaises(TypeError, context.set_default_verify_paths, 1)
        self.assertRaises(TypeError, context.set_default_verify_paths, "")


    def test_add_extra_chain_cert_invalid_cert(self):
        """
        L{Context.add_extra_chain_cert} raises L{TypeError} if called with
        other than one argument or if called with an object which is not an
        instance of L{X509}.
        """
        context = Context(TLSv1_METHOD)
        self.assertRaises(TypeError, context.add_extra_chain_cert)
        self.assertRaises(TypeError, context.add_extra_chain_cert, object())
        self.assertRaises(TypeError, context.add_extra_chain_cert, object(), object())


    def _handshake_test(self, serverContext, clientContext):
        """
        Verify that a client and server created with the given contexts can
        successfully handshake and communicate.
        """
        serverSocket, clientSocket = socket_pair()

        server = Connection(serverContext, serverSocket)
        server.set_accept_state()

        client = Connection(clientContext, clientSocket)
        client.set_connect_state()

        # Make them talk to each other.
        # self._interactInMemory(client, server)
        for i in range(3):
            for s in [client, server]:
                try:
                    s.do_handshake()
                except WantReadError:
                    pass


    def test_add_extra_chain_cert(self):
        """
        L{Context.add_extra_chain_cert} accepts an L{X509} instance to add to
        the certificate chain.

        See L{_create_certificate_chain} for the details of the certificate
        chain tested.

        The chain is tested by starting a server with scert and connecting
        to it with a client which trusts cacert and requires verification to
        succeed.
        """
        chain = _create_certificate_chain()
        [(cakey, cacert), (ikey, icert), (skey, scert)] = chain

        # Dump the CA certificate to a file because that's the only way to load
        # it as a trusted CA in the client context.
        for cert, name in [(cacert, 'ca.pem'), (icert, 'i.pem'), (scert, 's.pem')]:
            fObj = open(name, 'w')
            fObj.write(dump_certificate(FILETYPE_PEM, cert).decode('ascii'))
            fObj.close()

        for key, name in [(cakey, 'ca.key'), (ikey, 'i.key'), (skey, 's.key')]:
            fObj = open(name, 'w')
            fObj.write(dump_privatekey(FILETYPE_PEM, key).decode('ascii'))
            fObj.close()

        # Create the server context
        serverContext = Context(TLSv1_METHOD)
        serverContext.use_privatekey(skey)
        serverContext.use_certificate(scert)
        # The client already has cacert, we only need to give them icert.
        serverContext.add_extra_chain_cert(icert)

        # Create the client
        clientContext = Context(TLSv1_METHOD)
        clientContext.set_verify(
            VERIFY_PEER | VERIFY_FAIL_IF_NO_PEER_CERT, verify_cb)
        clientContext.load_verify_locations('ca.pem')

        # Try it out.
        self._handshake_test(serverContext, clientContext)


    def test_use_certificate_chain_file(self):
        """
        L{Context.use_certificate_chain_file} reads a certificate chain from
        the specified file.

        The chain is tested by starting a server with scert and connecting
        to it with a client which trusts cacert and requires verification to
        succeed.
        """
        chain = _create_certificate_chain()
        [(cakey, cacert), (ikey, icert), (skey, scert)] = chain

        # Write out the chain file.
        chainFile = self.mktemp()
        fObj = open(chainFile, 'w')
        # Most specific to least general.
        fObj.write(dump_certificate(FILETYPE_PEM, scert).decode('ascii'))
        fObj.write(dump_certificate(FILETYPE_PEM, icert).decode('ascii'))
        fObj.write(dump_certificate(FILETYPE_PEM, cacert).decode('ascii'))
        fObj.close()

        serverContext = Context(TLSv1_METHOD)
        serverContext.use_certificate_chain_file(chainFile)
        serverContext.use_privatekey(skey)

        fObj = open('ca.pem', 'w')
        fObj.write(dump_certificate(FILETYPE_PEM, cacert).decode('ascii'))
        fObj.close()

        clientContext = Context(TLSv1_METHOD)
        clientContext.set_verify(
            VERIFY_PEER | VERIFY_FAIL_IF_NO_PEER_CERT, verify_cb)
        clientContext.load_verify_locations('ca.pem')

        self._handshake_test(serverContext, clientContext)

    # XXX load_client_ca
    # XXX set_session_id

    def test_get_verify_mode_wrong_args(self):
        """
        L{Context.get_verify_mode} raises L{TypeError} if called with any
        arguments.
        """
        context = Context(TLSv1_METHOD)
        self.assertRaises(TypeError, context.get_verify_mode, None)


    def test_get_verify_mode(self):
        """
        L{Context.get_verify_mode} returns the verify mode flags previously
        passed to L{Context.set_verify}.
        """
        context = Context(TLSv1_METHOD)
        self.assertEquals(context.get_verify_mode(), 0)
        context.set_verify(
            VERIFY_PEER | VERIFY_CLIENT_ONCE, lambda *args: None)
        self.assertEquals(
            context.get_verify_mode(), VERIFY_PEER | VERIFY_CLIENT_ONCE)


    def test_load_tmp_dh_wrong_args(self):
        """
        L{Context.load_tmp_dh} raises L{TypeError} if called with the wrong
        number of arguments or with a non-C{str} argument.
        """
        context = Context(TLSv1_METHOD)
        self.assertRaises(TypeError, context.load_tmp_dh)
        self.assertRaises(TypeError, context.load_tmp_dh, "foo", None)
        self.assertRaises(TypeError, context.load_tmp_dh, object())


    def test_load_tmp_dh_missing_file(self):
        """
        L{Context.load_tmp_dh} raises L{OpenSSL.SSL.Error} if the specified file
        does not exist.
        """
        context = Context(TLSv1_METHOD)
        self.assertRaises(Error, context.load_tmp_dh, "hello")


    def test_load_tmp_dh(self):
        """
        L{Context.load_tmp_dh} loads Diffie-Hellman parameters from the
        specified file.
        """
        context = Context(TLSv1_METHOD)
        dhfilename = self.mktemp()
        dhfile = open(dhfilename, "w")
        dhfile.write(dhparam)
        dhfile.close()
        context.load_tmp_dh(dhfilename)
        # XXX What should I assert here? -exarkun


    def test_set_cipher_list(self):
        """
        L{Context.set_cipher_list} accepts a C{str} naming the ciphers which
        connections created with the context object will be able to choose from.
        """
        context = Context(TLSv1_METHOD)
        context.set_cipher_list("hello world:EXP-RC4-MD5")
        conn = Connection(context, None)
        self.assertEquals(conn.get_cipher_list(), ["EXP-RC4-MD5"])



class ServerNameCallbackTests(TestCase, _LoopbackMixin):
    """
    Tests for L{Context.set_tlsext_servername_callback} and its interaction with
    L{Connection}.
    """
    def test_wrong_args(self):
        """
        L{Context.set_tlsext_servername_callback} raises L{TypeError} if called
        with other than one argument.
        """
        context = Context(TLSv1_METHOD)
        self.assertRaises(TypeError, context.set_tlsext_servername_callback)
        self.assertRaises(
            TypeError, context.set_tlsext_servername_callback, 1, 2)

    def test_old_callback_forgotten(self):
        """
        If L{Context.set_tlsext_servername_callback} is used to specify a new
        callback, the one it replaces is dereferenced.
        """
        def callback(connection):
            pass

        def replacement(connection):
            pass

        context = Context(TLSv1_METHOD)
        context.set_tlsext_servername_callback(callback)

        tracker = ref(callback)
        del callback

        context.set_tlsext_servername_callback(replacement)
        collect()
        self.assertIdentical(None, tracker())


    def test_no_servername(self):
        """
        When a client specifies no server name, the callback passed to
        L{Context.set_tlsext_servername_callback} is invoked and the result of
        L{Connection.get_servername} is C{None}.
        """
        args = []
        def servername(conn):
            args.append((conn, conn.get_servername()))
        context = Context(TLSv1_METHOD)
        context.set_tlsext_servername_callback(servername)

        # Lose our reference to it.  The Context is responsible for keeping it
        # alive now.
        del servername
        collect()

        # Necessary to actually accept the connection
        context.use_privatekey(load_privatekey(FILETYPE_PEM, server_key_pem))
        context.use_certificate(load_certificate(FILETYPE_PEM, server_cert_pem))

        # Do a little connection to trigger the logic
        server = Connection(context, None)
        server.set_accept_state()

        client = Connection(Context(TLSv1_METHOD), None)
        client.set_connect_state()

        self._interactInMemory(server, client)

        self.assertEqual([(server, None)], args)


    def test_servername(self):
        """
        When a client specifies a server name in its hello message, the callback
        passed to L{Contexts.set_tlsext_servername_callback} is invoked and the
        result of L{Connection.get_servername} is that server name.
        """
        args = []
        def servername(conn):
            args.append((conn, conn.get_servername()))
        context = Context(TLSv1_METHOD)
        context.set_tlsext_servername_callback(servername)

        # Necessary to actually accept the connection
        context.use_privatekey(load_privatekey(FILETYPE_PEM, server_key_pem))
        context.use_certificate(load_certificate(FILETYPE_PEM, server_cert_pem))

        # Do a little connection to trigger the logic
        server = Connection(context, None)
        server.set_accept_state()

        client = Connection(Context(TLSv1_METHOD), None)
        client.set_connect_state()
        client.set_tlsext_host_name(b("foo1.example.com"))

        self._interactInMemory(server, client)

        self.assertEqual([(server, b("foo1.example.com"))], args)



class ConnectionTests(TestCase, _LoopbackMixin):
    """
    Unit tests for L{OpenSSL.SSL.Connection}.
    """
    # XXX want_write
    # XXX want_read
    # XXX get_peer_certificate -> None
    # XXX sock_shutdown
    # XXX master_key -> TypeError
    # XXX server_random -> TypeError
    # XXX state_string
    # XXX connect -> TypeError
    # XXX connect_ex -> TypeError
    # XXX set_connect_state -> TypeError
    # XXX set_accept_state -> TypeError
    # XXX renegotiate_pending
    # XXX do_handshake -> TypeError
    # XXX bio_read -> TypeError
    # XXX recv -> TypeError
    # XXX send -> TypeError
    # XXX bio_write -> TypeError

    def test_type(self):
        """
        L{Connection} and L{ConnectionType} refer to the same type object and
        can be used to create instances of that type.
        """
        self.assertIdentical(Connection, ConnectionType)
        ctx = Context(TLSv1_METHOD)
        self.assertConsistentType(Connection, 'Connection', ctx, None)


    def test_get_context(self):
        """
        L{Connection.get_context} returns the L{Context} instance used to
        construct the L{Connection} instance.
        """
        context = Context(TLSv1_METHOD)
        connection = Connection(context, None)
        self.assertIdentical(connection.get_context(), context)


    def test_get_context_wrong_args(self):
        """
        L{Connection.get_context} raises L{TypeError} if called with any
        arguments.
        """
        connection = Connection(Context(TLSv1_METHOD), None)
        self.assertRaises(TypeError, connection.get_context, None)


    def test_set_context_wrong_args(self):
        """
        L{Connection.set_context} raises L{TypeError} if called with a
        non-L{Context} instance argument or with any number of arguments other
        than 1.
        """
        ctx = Context(TLSv1_METHOD)
        connection = Connection(ctx, None)
        self.assertRaises(TypeError, connection.set_context)
        self.assertRaises(TypeError, connection.set_context, object())
        self.assertRaises(TypeError, connection.set_context, "hello")
        self.assertRaises(TypeError, connection.set_context, 1)
        self.assertRaises(TypeError, connection.set_context, 1, 2)
        self.assertRaises(
            TypeError, connection.set_context, Context(TLSv1_METHOD), 2)
        self.assertIdentical(ctx, connection.get_context())


    def test_set_context(self):
        """
        L{Connection.set_context} specifies a new L{Context} instance to be used
        for the connection.
        """
        original = Context(SSLv23_METHOD)
        replacement = Context(TLSv1_METHOD)
        connection = Connection(original, None)
        connection.set_context(replacement)
        self.assertIdentical(replacement, connection.get_context())
        # Lose our references to the contexts, just in case the Connection isn't
        # properly managing its own contributions to their reference counts.
        del original, replacement
        collect()


    def test_set_tlsext_host_name_wrong_args(self):
        """
        If L{Connection.set_tlsext_host_name} is called with a non-byte string
        argument or a byte string with an embedded NUL or other than one
        argument, L{TypeError} is raised.
        """
        conn = Connection(Context(TLSv1_METHOD), None)
        self.assertRaises(TypeError, conn.set_tlsext_host_name)
        self.assertRaises(TypeError, conn.set_tlsext_host_name, object())
        self.assertRaises(TypeError, conn.set_tlsext_host_name, 123, 456)
        self.assertRaises(
            TypeError, conn.set_tlsext_host_name, b("with\0null"))

        if version_info >= (3,):
            # On Python 3.x, don't accidentally implicitly convert from text.
            self.assertRaises(
                TypeError,
                conn.set_tlsext_host_name, b("example.com").decode("ascii"))


    def test_get_servername_wrong_args(self):
        """
        L{Connection.get_servername} raises L{TypeError} if called with any
        arguments.
        """
        connection = Connection(Context(TLSv1_METHOD), None)
        self.assertRaises(TypeError, connection.get_servername, object())
        self.assertRaises(TypeError, connection.get_servername, 1)
        self.assertRaises(TypeError, connection.get_servername, "hello")


    def test_pending(self):
        """
        L{Connection.pending} returns the number of bytes available for
        immediate read.
        """
        connection = Connection(Context(TLSv1_METHOD), None)
        self.assertEquals(connection.pending(), 0)


    def test_pending_wrong_args(self):
        """
        L{Connection.pending} raises L{TypeError} if called with any arguments.
        """
        connection = Connection(Context(TLSv1_METHOD), None)
        self.assertRaises(TypeError, connection.pending, None)


    def test_connect_wrong_args(self):
        """
        L{Connection.connect} raises L{TypeError} if called with a non-address
        argument or with the wrong number of arguments.
        """
        connection = Connection(Context(TLSv1_METHOD), socket())
        self.assertRaises(TypeError, connection.connect, None)
        self.assertRaises(TypeError, connection.connect)
        self.assertRaises(TypeError, connection.connect, ("127.0.0.1", 1), None)


    def test_connect_refused(self):
        """
        L{Connection.connect} raises L{socket.error} if the underlying socket
        connect method raises it.
        """
        client = socket()
        context = Context(TLSv1_METHOD)
        clientSSL = Connection(context, client)
        exc = self.assertRaises(error, clientSSL.connect, ("127.0.0.1", 1))
        self.assertEquals(exc.args[0], ECONNREFUSED)


    def test_connect(self):
        """
        L{Connection.connect} establishes a connection to the specified address.
        """
        port = socket()
        port.bind(('', 0))
        port.listen(3)

        clientSSL = Connection(Context(TLSv1_METHOD), socket())
        clientSSL.connect(('127.0.0.1', port.getsockname()[1]))
        # XXX An assertion?  Or something?


    if platform == "darwin":
        "connect_ex sometimes causes a kernel panic on OS X 10.6.4"
    else:
        def test_connect_ex(self):
            """
            If there is a connection error, L{Connection.connect_ex} returns the
            errno instead of raising an exception.
            """
            port = socket()
            port.bind(('', 0))
            port.listen(3)

            clientSSL = Connection(Context(TLSv1_METHOD), socket())
            clientSSL.setblocking(False)
            result = clientSSL.connect_ex(port.getsockname())
            expected = (EINPROGRESS, EWOULDBLOCK)
            self.assertTrue(
                    result in expected, "%r not in %r" % (result, expected))


    def test_accept_wrong_args(self):
        """
        L{Connection.accept} raises L{TypeError} if called with any arguments.
        """
        connection = Connection(Context(TLSv1_METHOD), socket())
        self.assertRaises(TypeError, connection.accept, None)


    def test_accept(self):
        """
        L{Connection.accept} accepts a pending connection attempt and returns a
        tuple of a new L{Connection} (the accepted client) and the address the
        connection originated from.
        """
        ctx = Context(TLSv1_METHOD)
        ctx.use_privatekey(load_privatekey(FILETYPE_PEM, server_key_pem))
        ctx.use_certificate(load_certificate(FILETYPE_PEM, server_cert_pem))
        port = socket()
        portSSL = Connection(ctx, port)
        portSSL.bind(('', 0))
        portSSL.listen(3)

        clientSSL = Connection(Context(TLSv1_METHOD), socket())

        # Calling portSSL.getsockname() here to get the server IP address sounds
        # great, but frequently fails on Windows.
        clientSSL.connect(('127.0.0.1', portSSL.getsockname()[1]))

        serverSSL, address = portSSL.accept()

        self.assertTrue(isinstance(serverSSL, Connection))
        self.assertIdentical(serverSSL.get_context(), ctx)
        self.assertEquals(address, clientSSL.getsockname())


    def test_shutdown_wrong_args(self):
        """
        L{Connection.shutdown} raises L{TypeError} if called with the wrong
        number of arguments or with arguments other than integers.
        """
        connection = Connection(Context(TLSv1_METHOD), None)
        self.assertRaises(TypeError, connection.shutdown, None)
        self.assertRaises(TypeError, connection.get_shutdown, None)
        self.assertRaises(TypeError, connection.set_shutdown)
        self.assertRaises(TypeError, connection.set_shutdown, None)
        self.assertRaises(TypeError, connection.set_shutdown, 0, 1)


    def test_shutdown(self):
        """
        L{Connection.shutdown} performs an SSL-level connection shutdown.
        """
        server, client = self._loopback()
        self.assertFalse(server.shutdown())
        self.assertEquals(server.get_shutdown(), SENT_SHUTDOWN)
        self.assertRaises(ZeroReturnError, client.recv, 1024)
        self.assertEquals(client.get_shutdown(), RECEIVED_SHUTDOWN)
        client.shutdown()
        self.assertEquals(client.get_shutdown(), SENT_SHUTDOWN|RECEIVED_SHUTDOWN)
        self.assertRaises(ZeroReturnError, server.recv, 1024)
        self.assertEquals(server.get_shutdown(), SENT_SHUTDOWN|RECEIVED_SHUTDOWN)


    def test_set_shutdown(self):
        """
        L{Connection.set_shutdown} sets the state of the SSL connection shutdown
        process.
        """
        connection = Connection(Context(TLSv1_METHOD), socket())
        connection.set_shutdown(RECEIVED_SHUTDOWN)
        self.assertEquals(connection.get_shutdown(), RECEIVED_SHUTDOWN)


    def test_app_data_wrong_args(self):
        """
        L{Connection.set_app_data} raises L{TypeError} if called with other than
        one argument.  L{Connection.get_app_data} raises L{TypeError} if called
        with any arguments.
        """
        conn = Connection(Context(TLSv1_METHOD), None)
        self.assertRaises(TypeError, conn.get_app_data, None)
        self.assertRaises(TypeError, conn.set_app_data)
        self.assertRaises(TypeError, conn.set_app_data, None, None)


    def test_app_data(self):
        """
        Any object can be set as app data by passing it to
        L{Connection.set_app_data} and later retrieved with
        L{Connection.get_app_data}.
        """
        conn = Connection(Context(TLSv1_METHOD), None)
        app_data = object()
        conn.set_app_data(app_data)
        self.assertIdentical(conn.get_app_data(), app_data)


    def test_makefile(self):
        """
        L{Connection.makefile} is not implemented and calling that method raises
        L{NotImplementedError}.
        """
        conn = Connection(Context(TLSv1_METHOD), None)
        self.assertRaises(NotImplementedError, conn.makefile)


    def test_get_peer_cert_chain_wrong_args(self):
        """
        L{Connection.get_peer_cert_chain} raises L{TypeError} if called with any
        arguments.
        """
        conn = Connection(Context(TLSv1_METHOD), None)
        self.assertRaises(TypeError, conn.get_peer_cert_chain, 1)
        self.assertRaises(TypeError, conn.get_peer_cert_chain, "foo")
        self.assertRaises(TypeError, conn.get_peer_cert_chain, object())
        self.assertRaises(TypeError, conn.get_peer_cert_chain, [])


    def test_get_peer_cert_chain(self):
        """
        L{Connection.get_peer_cert_chain} returns a list of certificates which
        the connected server returned for the certification verification.
        """
        chain = _create_certificate_chain()
        [(cakey, cacert), (ikey, icert), (skey, scert)] = chain

        serverContext = Context(TLSv1_METHOD)
        serverContext.use_privatekey(skey)
        serverContext.use_certificate(scert)
        serverContext.add_extra_chain_cert(icert)
        serverContext.add_extra_chain_cert(cacert)
        server = Connection(serverContext, None)
        server.set_accept_state()

        # Create the client
        clientContext = Context(TLSv1_METHOD)
        clientContext.set_verify(VERIFY_NONE, verify_cb)
        client = Connection(clientContext, None)
        client.set_connect_state()

        self._interactInMemory(client, server)

        chain = client.get_peer_cert_chain()
        self.assertEqual(len(chain), 3)
        self.assertEqual(
            "Server Certificate", chain[0].get_subject().CN)
        self.assertEqual(
            "Intermediate Certificate", chain[1].get_subject().CN)
        self.assertEqual(
            "Authority Certificate", chain[2].get_subject().CN)


    def test_get_peer_cert_chain_none(self):
        """
        L{Connection.get_peer_cert_chain} returns C{None} if the peer sends no
        certificate chain.
        """
        ctx = Context(TLSv1_METHOD)
        ctx.use_privatekey(load_privatekey(FILETYPE_PEM, server_key_pem))
        ctx.use_certificate(load_certificate(FILETYPE_PEM, server_cert_pem))
        server = Connection(ctx, None)
        server.set_accept_state()
        client = Connection(Context(TLSv1_METHOD), None)
        client.set_connect_state()
        self._interactInMemory(client, server)
        self.assertIdentical(None, server.get_peer_cert_chain())



class ConnectionGetCipherListTests(TestCase):
    """
    Tests for L{Connection.get_cipher_list}.
    """
    def test_wrong_args(self):
        """
        L{Connection.get_cipher_list} raises L{TypeError} if called with any
        arguments.
        """
        connection = Connection(Context(TLSv1_METHOD), None)
        self.assertRaises(TypeError, connection.get_cipher_list, None)


    def test_result(self):
        """
        L{Connection.get_cipher_list} returns a C{list} of C{str} giving the
        names of the ciphers which might be used.
        """
        connection = Connection(Context(TLSv1_METHOD), None)
        ciphers = connection.get_cipher_list()
        self.assertTrue(isinstance(ciphers, list))
        for cipher in ciphers:
            self.assertTrue(isinstance(cipher, str))



class ConnectionSendTests(TestCase, _LoopbackMixin):
    """
    Tests for L{Connection.send}
    """
    def test_wrong_args(self):
        """
        When called with arguments other than a single string,
        L{Connection.send} raises L{TypeError}.
        """
        connection = Connection(Context(TLSv1_METHOD), None)
        self.assertRaises(TypeError, connection.send)
        self.assertRaises(TypeError, connection.send, object())
        self.assertRaises(TypeError, connection.send, "foo", "bar")


    def test_short_bytes(self):
        """
        When passed a short byte string, L{Connection.send} transmits all of it
        and returns the number of bytes sent.
        """
        server, client = self._loopback()
        count = server.send(b('xy'))
        self.assertEquals(count, 2)
        self.assertEquals(client.recv(2), b('xy'))

    try:
        memoryview
    except NameError:
        "cannot test sending memoryview without memoryview"
    else:
        def test_short_memoryview(self):
            """
            When passed a memoryview onto a small number of bytes,
            L{Connection.send} transmits all of them and returns the number of
            bytes sent.
            """
            server, client = self._loopback()
            count = server.send(memoryview(b('xy')))
            self.assertEquals(count, 2)
            self.assertEquals(client.recv(2), b('xy'))



class ConnectionSendallTests(TestCase, _LoopbackMixin):
    """
    Tests for L{Connection.sendall}.
    """
    def test_wrong_args(self):
        """
        When called with arguments other than a single string,
        L{Connection.sendall} raises L{TypeError}.
        """
        connection = Connection(Context(TLSv1_METHOD), None)
        self.assertRaises(TypeError, connection.sendall)
        self.assertRaises(TypeError, connection.sendall, object())
        self.assertRaises(TypeError, connection.sendall, "foo", "bar")


    def test_short(self):
        """
        L{Connection.sendall} transmits all of the bytes in the string passed to
        it.
        """
        server, client = self._loopback()
        server.sendall(b('x'))
        self.assertEquals(client.recv(1), b('x'))


    try:
        memoryview
    except NameError:
        "cannot test sending memoryview without memoryview"
    else:
        def test_short_memoryview(self):
            """
            When passed a memoryview onto a small number of bytes,
            L{Connection.sendall} transmits all of them.
            """
            server, client = self._loopback()
            server.sendall(memoryview(b('x')))
            self.assertEquals(client.recv(1), b('x'))


    def test_long(self):
        """
        L{Connection.sendall} transmits all of the bytes in the string passed to
        it even if this requires multiple calls of an underlying write function.
        """
        server, client = self._loopback()
        # Should be enough, underlying SSL_write should only do 16k at a time.
        # On Windows, after 32k of bytes the write will block (forever - because
        # no one is yet reading).
        message = b('x') * (1024 * 32 - 1) + b('y')
        server.sendall(message)
        accum = []
        received = 0
        while received < len(message):
            data = client.recv(1024)
            accum.append(data)
            received += len(data)
        self.assertEquals(message, b('').join(accum))


    def test_closed(self):
        """
        If the underlying socket is closed, L{Connection.sendall} propagates the
        write error from the low level write call.
        """
        server, client = self._loopback()
        server.sock_shutdown(2)
        self.assertRaises(SysCallError, server.sendall, "hello, world")



class ConnectionRenegotiateTests(TestCase, _LoopbackMixin):
    """
    Tests for SSL renegotiation APIs.
    """
    def test_renegotiate_wrong_args(self):
        """
        L{Connection.renegotiate} raises L{TypeError} if called with any
        arguments.
        """
        connection = Connection(Context(TLSv1_METHOD), None)
        self.assertRaises(TypeError, connection.renegotiate, None)


    def test_total_renegotiations_wrong_args(self):
        """
        L{Connection.total_renegotiations} raises L{TypeError} if called with
        any arguments.
        """
        connection = Connection(Context(TLSv1_METHOD), None)
        self.assertRaises(TypeError, connection.total_renegotiations, None)


    def test_total_renegotiations(self):
        """
        L{Connection.total_renegotiations} returns C{0} before any
        renegotiations have happened.
        """
        connection = Connection(Context(TLSv1_METHOD), None)
        self.assertEquals(connection.total_renegotiations(), 0)


#     def test_renegotiate(self):
#         """
#         """
#         server, client = self._loopback()

#         server.send("hello world")
#         self.assertEquals(client.recv(len("hello world")), "hello world")

#         self.assertEquals(server.total_renegotiations(), 0)
#         self.assertTrue(server.renegotiate())

#         server.setblocking(False)
#         client.setblocking(False)
#         while server.renegotiate_pending():
#             client.do_handshake()
#             server.do_handshake()

#         self.assertEquals(server.total_renegotiations(), 1)




class ErrorTests(TestCase):
    """
    Unit tests for L{OpenSSL.SSL.Error}.
    """
    def test_type(self):
        """
        L{Error} is an exception type.
        """
        self.assertTrue(issubclass(Error, Exception))
        self.assertEqual(Error.__name__, 'Error')



class ConstantsTests(TestCase):
    """
    Tests for the values of constants exposed in L{OpenSSL.SSL}.

    These are values defined by OpenSSL intended only to be used as flags to
    OpenSSL APIs.  The only assertions it seems can be made about them is
    their values.
    """
    # unittest.TestCase has no skip mechanism
    if OP_NO_QUERY_MTU is not None:
        def test_op_no_query_mtu(self):
            """
            The value of L{OpenSSL.SSL.OP_NO_QUERY_MTU} is 0x1000, the value of
            I{SSL_OP_NO_QUERY_MTU} defined by I{openssl/ssl.h}.
            """
            self.assertEqual(OP_NO_QUERY_MTU, 0x1000)
    else:
        "OP_NO_QUERY_MTU unavailable - OpenSSL version may be too old"


    if OP_COOKIE_EXCHANGE is not None:
        def test_op_cookie_exchange(self):
            """
            The value of L{OpenSSL.SSL.OP_COOKIE_EXCHANGE} is 0x2000, the value
            of I{SSL_OP_COOKIE_EXCHANGE} defined by I{openssl/ssl.h}.
            """
            self.assertEqual(OP_COOKIE_EXCHANGE, 0x2000)
    else:
        "OP_COOKIE_EXCHANGE unavailable - OpenSSL version may be too old"


    if OP_NO_TICKET is not None:
        def test_op_no_ticket(self):
            """
            The value of L{OpenSSL.SSL.OP_NO_TICKET} is 0x4000, the value of
            I{SSL_OP_NO_TICKET} defined by I{openssl/ssl.h}.
            """
            self.assertEqual(OP_NO_TICKET, 0x4000)
    else:
        "OP_NO_TICKET unavailable - OpenSSL version may be too old"



class MemoryBIOTests(TestCase, _LoopbackMixin):
    """
    Tests for L{OpenSSL.SSL.Connection} using a memory BIO.
    """
    def _server(self, sock):
        """
        Create a new server-side SSL L{Connection} object wrapped around
        C{sock}.
        """
        # Create the server side Connection.  This is mostly setup boilerplate
        # - use TLSv1, use a particular certificate, etc.
        server_ctx = Context(TLSv1_METHOD)
        server_ctx.set_options(OP_NO_SSLv2 | OP_NO_SSLv3 | OP_SINGLE_DH_USE )
        server_ctx.set_verify(VERIFY_PEER|VERIFY_FAIL_IF_NO_PEER_CERT|VERIFY_CLIENT_ONCE, verify_cb)
        server_store = server_ctx.get_cert_store()
        server_ctx.use_privatekey(load_privatekey(FILETYPE_PEM, server_key_pem))
        server_ctx.use_certificate(load_certificate(FILETYPE_PEM, server_cert_pem))
        server_ctx.check_privatekey()
        server_store.add_cert(load_certificate(FILETYPE_PEM, root_cert_pem))
        # Here the Connection is actually created.  If None is passed as the 2nd
        # parameter, it indicates a memory BIO should be created.
        server_conn = Connection(server_ctx, sock)
        server_conn.set_accept_state()
        return server_conn


    def _client(self, sock):
        """
        Create a new client-side SSL L{Connection} object wrapped around
        C{sock}.
        """
        # Now create the client side Connection.  Similar boilerplate to the
        # above.
        client_ctx = Context(TLSv1_METHOD)
        client_ctx.set_options(OP_NO_SSLv2 | OP_NO_SSLv3 | OP_SINGLE_DH_USE )
        client_ctx.set_verify(VERIFY_PEER|VERIFY_FAIL_IF_NO_PEER_CERT|VERIFY_CLIENT_ONCE, verify_cb)
        client_store = client_ctx.get_cert_store()
        client_ctx.use_privatekey(load_privatekey(FILETYPE_PEM, client_key_pem))
        client_ctx.use_certificate(load_certificate(FILETYPE_PEM, client_cert_pem))
        client_ctx.check_privatekey()
        client_store.add_cert(load_certificate(FILETYPE_PEM, root_cert_pem))
        client_conn = Connection(client_ctx, sock)
        client_conn.set_connect_state()
        return client_conn


    def test_memoryConnect(self):
        """
        Two L{Connection}s which use memory BIOs can be manually connected by
        reading from the output of each and writing those bytes to the input of
        the other and in this way establish a connection and exchange
        application-level bytes with each other.
        """
        server_conn = self._server(None)
        client_conn = self._client(None)

        # There should be no key or nonces yet.
        self.assertIdentical(server_conn.master_key(), None)
        self.assertIdentical(server_conn.client_random(), None)
        self.assertIdentical(server_conn.server_random(), None)

        # First, the handshake needs to happen.  We'll deliver bytes back and
        # forth between the client and server until neither of them feels like
        # speaking any more.
        self.assertIdentical(
            self._interactInMemory(client_conn, server_conn), None)

        # Now that the handshake is done, there should be a key and nonces.
        self.assertNotIdentical(server_conn.master_key(), None)
        self.assertNotIdentical(server_conn.client_random(), None)
        self.assertNotIdentical(server_conn.server_random(), None)
        self.assertEquals(server_conn.client_random(), client_conn.client_random())
        self.assertEquals(server_conn.server_random(), client_conn.server_random())
        self.assertNotEquals(server_conn.client_random(), server_conn.server_random())
        self.assertNotEquals(client_conn.client_random(), client_conn.server_random())

        # Here are the bytes we'll try to send.
        important_message = b('One if by land, two if by sea.')

        server_conn.write(important_message)
        self.assertEquals(
            self._interactInMemory(client_conn, server_conn),
            (client_conn, important_message))

        client_conn.write(important_message[::-1])
        self.assertEquals(
            self._interactInMemory(client_conn, server_conn),
            (server_conn, important_message[::-1]))


    def test_socketConnect(self):
        """
        Just like L{test_memoryConnect} but with an actual socket.

        This is primarily to rule out the memory BIO code as the source of
        any problems encountered while passing data over a L{Connection} (if
        this test fails, there must be a problem outside the memory BIO
        code, as no memory BIO is involved here).  Even though this isn't a
        memory BIO test, it's convenient to have it here.
        """
        server_conn, client_conn = self._loopback()

        important_message = b("Help me Obi Wan Kenobi, you're my only hope.")
        client_conn.send(important_message)
        msg = server_conn.recv(1024)
        self.assertEqual(msg, important_message)

        # Again in the other direction, just for fun.
        important_message = important_message[::-1]
        server_conn.send(important_message)
        msg = client_conn.recv(1024)
        self.assertEqual(msg, important_message)


    def test_socketOverridesMemory(self):
        """
        Test that L{OpenSSL.SSL.bio_read} and L{OpenSSL.SSL.bio_write} don't
        work on L{OpenSSL.SSL.Connection}() that use sockets.
        """
        context = Context(SSLv3_METHOD)
        client = socket()
        clientSSL = Connection(context, client)
        self.assertRaises( TypeError, clientSSL.bio_read, 100)
        self.assertRaises( TypeError, clientSSL.bio_write, "foo")
        self.assertRaises( TypeError, clientSSL.bio_shutdown )


    def test_outgoingOverflow(self):
        """
        If more bytes than can be written to the memory BIO are passed to
        L{Connection.send} at once, the number of bytes which were written is
        returned and that many bytes from the beginning of the input can be
        read from the other end of the connection.
        """
        server = self._server(None)
        client = self._client(None)

        self._interactInMemory(client, server)

        size = 2 ** 15
        sent = client.send("x" * size)
        # Sanity check.  We're trying to test what happens when the entire
        # input can't be sent.  If the entire input was sent, this test is
        # meaningless.
        self.assertTrue(sent < size)

        receiver, received = self._interactInMemory(client, server)
        self.assertIdentical(receiver, server)

        # We can rely on all of these bytes being received at once because
        # _loopback passes 2 ** 16 to recv - more than 2 ** 15.
        self.assertEquals(len(received), sent)


    def test_shutdown(self):
        """
        L{Connection.bio_shutdown} signals the end of the data stream from
        which the L{Connection} reads.
        """
        server = self._server(None)
        server.bio_shutdown()
        e = self.assertRaises(Error, server.recv, 1024)
        # We don't want WantReadError or ZeroReturnError or anything - it's a
        # handshake failure.
        self.assertEquals(e.__class__, Error)


    def _check_client_ca_list(self, func):
        """
        Verify the return value of the C{get_client_ca_list} method for server and client connections.

        @param func: A function which will be called with the server context
            before the client and server are connected to each other.  This
            function should specify a list of CAs for the server to send to the
            client and return that same list.  The list will be used to verify
            that C{get_client_ca_list} returns the proper value at various
            times.
        """
        server = self._server(None)
        client = self._client(None)
        self.assertEqual(client.get_client_ca_list(), [])
        self.assertEqual(server.get_client_ca_list(), [])
        ctx = server.get_context()
        expected = func(ctx)
        self.assertEqual(client.get_client_ca_list(), [])
        self.assertEqual(server.get_client_ca_list(), expected)
        self._interactInMemory(client, server)
        self.assertEqual(client.get_client_ca_list(), expected)
        self.assertEqual(server.get_client_ca_list(), expected)


    def test_set_client_ca_list_errors(self):
        """
        L{Context.set_client_ca_list} raises a L{TypeError} if called with a
        non-list or a list that contains objects other than X509Names.
        """
        ctx = Context(TLSv1_METHOD)
        self.assertRaises(TypeError, ctx.set_client_ca_list, "spam")
        self.assertRaises(TypeError, ctx.set_client_ca_list, ["spam"])
        self.assertIdentical(ctx.set_client_ca_list([]), None)


    def test_set_empty_ca_list(self):
        """
        If passed an empty list, L{Context.set_client_ca_list} configures the
        context to send no CA names to the client and, on both the server and
        client sides, L{Connection.get_client_ca_list} returns an empty list
        after the connection is set up.
        """
        def no_ca(ctx):
            ctx.set_client_ca_list([])
            return []
        self._check_client_ca_list(no_ca)


    def test_set_one_ca_list(self):
        """
        If passed a list containing a single X509Name,
        L{Context.set_client_ca_list} configures the context to send that CA
        name to the client and, on both the server and client sides,
        L{Connection.get_client_ca_list} returns a list containing that
        X509Name after the connection is set up.
        """
        cacert = load_certificate(FILETYPE_PEM, root_cert_pem)
        cadesc = cacert.get_subject()
        def single_ca(ctx):
            ctx.set_client_ca_list([cadesc])
            return [cadesc]
        self._check_client_ca_list(single_ca)


    def test_set_multiple_ca_list(self):
        """
        If passed a list containing multiple X509Name objects,
        L{Context.set_client_ca_list} configures the context to send those CA
        names to the client and, on both the server and client sides,
        L{Connection.get_client_ca_list} returns a list containing those
        X509Names after the connection is set up.
        """
        secert = load_certificate(FILETYPE_PEM, server_cert_pem)
        clcert = load_certificate(FILETYPE_PEM, server_cert_pem)

        sedesc = secert.get_subject()
        cldesc = clcert.get_subject()

        def multiple_ca(ctx):
            L = [sedesc, cldesc]
            ctx.set_client_ca_list(L)
            return L
        self._check_client_ca_list(multiple_ca)


    def test_reset_ca_list(self):
        """
        If called multiple times, only the X509Names passed to the final call
        of L{Context.set_client_ca_list} are used to configure the CA names
        sent to the client.
        """
        cacert = load_certificate(FILETYPE_PEM, root_cert_pem)
        secert = load_certificate(FILETYPE_PEM, server_cert_pem)
        clcert = load_certificate(FILETYPE_PEM, server_cert_pem)

        cadesc = cacert.get_subject()
        sedesc = secert.get_subject()
        cldesc = clcert.get_subject()

        def changed_ca(ctx):
            ctx.set_client_ca_list([sedesc, cldesc])
            ctx.set_client_ca_list([cadesc])
            return [cadesc]
        self._check_client_ca_list(changed_ca)


    def test_mutated_ca_list(self):
        """
        If the list passed to L{Context.set_client_ca_list} is mutated
        afterwards, this does not affect the list of CA names sent to the
        client.
        """
        cacert = load_certificate(FILETYPE_PEM, root_cert_pem)
        secert = load_certificate(FILETYPE_PEM, server_cert_pem)

        cadesc = cacert.get_subject()
        sedesc = secert.get_subject()

        def mutated_ca(ctx):
            L = [cadesc]
            ctx.set_client_ca_list([cadesc])
            L.append(sedesc)
            return [cadesc]
        self._check_client_ca_list(mutated_ca)


    def test_add_client_ca_errors(self):
        """
        L{Context.add_client_ca} raises L{TypeError} if called with a non-X509
        object or with a number of arguments other than one.
        """
        ctx = Context(TLSv1_METHOD)
        cacert = load_certificate(FILETYPE_PEM, root_cert_pem)
        self.assertRaises(TypeError, ctx.add_client_ca)
        self.assertRaises(TypeError, ctx.add_client_ca, "spam")
        self.assertRaises(TypeError, ctx.add_client_ca, cacert, cacert)


    def test_one_add_client_ca(self):
        """
        A certificate's subject can be added as a CA to be sent to the client
        with L{Context.add_client_ca}.
        """
        cacert = load_certificate(FILETYPE_PEM, root_cert_pem)
        cadesc = cacert.get_subject()
        def single_ca(ctx):
            ctx.add_client_ca(cacert)
            return [cadesc]
        self._check_client_ca_list(single_ca)


    def test_multiple_add_client_ca(self):
        """
        Multiple CA names can be sent to the client by calling
        L{Context.add_client_ca} with multiple X509 objects.
        """
        cacert = load_certificate(FILETYPE_PEM, root_cert_pem)
        secert = load_certificate(FILETYPE_PEM, server_cert_pem)

        cadesc = cacert.get_subject()
        sedesc = secert.get_subject()

        def multiple_ca(ctx):
            ctx.add_client_ca(cacert)
            ctx.add_client_ca(secert)
            return [cadesc, sedesc]
        self._check_client_ca_list(multiple_ca)


    def test_set_and_add_client_ca(self):
        """
        A call to L{Context.set_client_ca_list} followed by a call to
        L{Context.add_client_ca} results in using the CA names from the first
        call and the CA name from the second call.
        """
        cacert = load_certificate(FILETYPE_PEM, root_cert_pem)
        secert = load_certificate(FILETYPE_PEM, server_cert_pem)
        clcert = load_certificate(FILETYPE_PEM, server_cert_pem)

        cadesc = cacert.get_subject()
        sedesc = secert.get_subject()
        cldesc = clcert.get_subject()

        def mixed_set_add_ca(ctx):
            ctx.set_client_ca_list([cadesc, sedesc])
            ctx.add_client_ca(clcert)
            return [cadesc, sedesc, cldesc]
        self._check_client_ca_list(mixed_set_add_ca)


    def test_set_after_add_client_ca(self):
        """
        A call to L{Context.set_client_ca_list} after a call to
        L{Context.add_client_ca} replaces the CA name specified by the former
        call with the names specified by the latter cal.
        """
        cacert = load_certificate(FILETYPE_PEM, root_cert_pem)
        secert = load_certificate(FILETYPE_PEM, server_cert_pem)
        clcert = load_certificate(FILETYPE_PEM, server_cert_pem)

        cadesc = cacert.get_subject()
        sedesc = secert.get_subject()

        def set_replaces_add_ca(ctx):
            ctx.add_client_ca(clcert)
            ctx.set_client_ca_list([cadesc])
            ctx.add_client_ca(secert)
            return [cadesc, sedesc]
        self._check_client_ca_list(set_replaces_add_ca)


class InfoConstantTests(TestCase):
    """
    Tests for assorted constants exposed for use in info callbacks.
    """
    def test_integers(self):
        """
        All of the info constants are integers.

        This is a very weak test.  It would be nice to have one that actually
        verifies that as certain info events happen, the value passed to the
        info callback matches up with the constant exposed by OpenSSL.SSL.
        """
        for const in [
            SSL_ST_CONNECT, SSL_ST_ACCEPT, SSL_ST_MASK, SSL_ST_INIT,
            SSL_ST_BEFORE, SSL_ST_OK, SSL_ST_RENEGOTIATE,
            SSL_CB_LOOP, SSL_CB_EXIT, SSL_CB_READ, SSL_CB_WRITE, SSL_CB_ALERT,
            SSL_CB_READ_ALERT, SSL_CB_WRITE_ALERT, SSL_CB_ACCEPT_LOOP,
            SSL_CB_ACCEPT_EXIT, SSL_CB_CONNECT_LOOP, SSL_CB_CONNECT_EXIT,
            SSL_CB_HANDSHAKE_START, SSL_CB_HANDSHAKE_DONE]:

            self.assertTrue(isinstance(const, int))


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = util
# Copyright (C) Jean-Paul Calderone
# Copyright (C) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Helpers for the OpenSSL test suite, largely copied from
U{Twisted<http://twistedmatrix.com/>}.
"""

import shutil
import os, os.path
from tempfile import mktemp
from unittest import TestCase
import sys

from OpenSSL.crypto import Error, _exception_from_error_queue

if sys.version_info < (3, 0):
    def b(s):
        return s
    bytes = str
else:
    def b(s):
        return s.encode("charmap")
    bytes = bytes


class TestCase(TestCase):
    """
    L{TestCase} adds useful testing functionality beyond what is available
    from the standard library L{unittest.TestCase}.
    """
    def tearDown(self):
        """
        Clean up any files or directories created using L{TestCase.mktemp}.
        Subclasses must invoke this method if they override it or the
        cleanup will not occur.
        """
        if False and self._temporaryFiles is not None:
            for temp in self._temporaryFiles:
                if os.path.isdir(temp):
                    shutil.rmtree(temp)
                elif os.path.exists(temp):
                    os.unlink(temp)
        try:
            _exception_from_error_queue()
        except Error:
            e = sys.exc_info()[1]
            if e.args != ([],):
                self.fail("Left over errors in OpenSSL error queue: " + repr(e))


    def failUnlessIn(self, containee, container, msg=None):
        """
        Fail the test if C{containee} is not found in C{container}.

        @param containee: the value that should be in C{container}
        @param container: a sequence type, or in the case of a mapping type,
                          will follow semantics of 'if key in dict.keys()'
        @param msg: if msg is None, then the failure message will be
                    '%r not in %r' % (first, second)
        """
        if containee not in container:
            raise self.failureException(msg or "%r not in %r"
                                        % (containee, container))
        return containee
    assertIn = failUnlessIn

    def failUnlessIdentical(self, first, second, msg=None):
        """
        Fail the test if C{first} is not C{second}.  This is an
        obect-identity-equality test, not an object equality
        (i.e. C{__eq__}) test.

        @param msg: if msg is None, then the failure message will be
        '%r is not %r' % (first, second)
        """
        if first is not second:
            raise self.failureException(msg or '%r is not %r' % (first, second))
        return first
    assertIdentical = failUnlessIdentical


    def failIfIdentical(self, first, second, msg=None):
        """
        Fail the test if C{first} is C{second}.  This is an
        obect-identity-equality test, not an object equality
        (i.e. C{__eq__}) test.

        @param msg: if msg is None, then the failure message will be
        '%r is %r' % (first, second)
        """
        if first is second:
            raise self.failureException(msg or '%r is %r' % (first, second))
        return first
    assertNotIdentical = failIfIdentical


    def failUnlessRaises(self, exception, f, *args, **kwargs):
        """
        Fail the test unless calling the function C{f} with the given
        C{args} and C{kwargs} raises C{exception}. The failure will report
        the traceback and call stack of the unexpected exception.

        @param exception: exception type that is to be expected
        @param f: the function to call

        @return: The raised exception instance, if it is of the given type.
        @raise self.failureException: Raised if the function call does
            not raise an exception or if it raises an exception of a
            different type.
        """
        try:
            result = f(*args, **kwargs)
        except exception:
            inst = sys.exc_info()[1]
            return inst
        except:
            raise self.failureException('%s raised instead of %s'
                                        % (sys.exc_info()[0],
                                           exception.__name__,
                                          ))
        else:
            raise self.failureException('%s not raised (%r returned)'
                                        % (exception.__name__, result))
    assertRaises = failUnlessRaises


    _temporaryFiles = None
    def mktemp(self):
        """
        Pathetic substitute for twisted.trial.unittest.TestCase.mktemp.
        """
        if self._temporaryFiles is None:
            self._temporaryFiles = []
        temp = mktemp(dir=".")
        self._temporaryFiles.append(temp)
        return temp


    # Python 2.3 compatibility.
    def assertTrue(self, *a, **kw):
        return self.failUnless(*a, **kw)


    def assertFalse(self, *a, **kw):
        return self.failIf(*a, **kw)


    # Other stuff
    def assertConsistentType(self, theType, name, *constructionArgs):
        """
        Perform various assertions about C{theType} to ensure that it is a
        well-defined type.  This is useful for extension types, where it's
        pretty easy to do something wacky.  If something about the type is
        unusual, an exception will be raised.

        @param theType: The type object about which to make assertions.
        @param name: A string giving the name of the type.
        @param constructionArgs: Positional arguments to use with C{theType} to
            create an instance of it.
        """
        self.assertEqual(theType.__name__, name)
        self.assertTrue(isinstance(theType, type))
        instance = theType(*constructionArgs)
        self.assertIdentical(type(instance), theType)

########NEW FILE########
__FILENAME__ = tsafe
from OpenSSL import SSL
_ssl = SSL
del SSL

import threading
_RLock = threading.RLock
del threading

class Connection:
    def __init__(self, *args):
        self._ssl_conn = apply(_ssl.Connection, args)
        self._lock = _RLock()

    for f in ('get_context', 'pending', 'send', 'write', 'recv', 'read',
              'renegotiate', 'bind', 'listen', 'connect', 'accept',
              'setblocking', 'fileno', 'shutdown', 'close', 'get_cipher_list',
              'getpeername', 'getsockname', 'getsockopt', 'setsockopt',
              'makefile', 'get_app_data', 'set_app_data', 'state_string',
              'sock_shutdown', 'get_peer_certificate', 'get_peer_cert_chain', 'want_read',
              'want_write', 'set_connect_state', 'set_accept_state',
              'connect_ex', 'sendall'):
        exec("""def %s(self, *args):
            self._lock.acquire()
            try:
                return self._ssl_conn.%s(*args)
            finally:
                self._lock.release()\n""" % (f, f))


########NEW FILE########
__FILENAME__ = version
# Copyright (C) AB Strakt
# Copyright (C) Jean-Paul Calderone
# See LICENSE for details.

"""
pyOpenSSL - A simple wrapper around the OpenSSL library
"""

__version__ = '0.13'

########NEW FILE########
__FILENAME__ = cert_print
#!/usr/bin/env python
import subprocess
import sys
#Print all certs in a file, openssl x509 only prints the first one 
#Uses the openssl x509 command, pretty hacky but it works 
def print_cert(inpath):
    output = ""
    i = 0

    with open(inpath) as f:
        buf = f.read()
        pattern = "-----BEGIN CERTIFICATE-----"
        index  = 0
        while True:
            index = buf.find(pattern, index)
            if (index==-1):
                break
            p = subprocess.Popen(["openssl", "x509", "-text"], \
                            stdout=subprocess.PIPE, stdin=subprocess.PIPE,\
                            stderr=subprocess.STDOUT)
            output += p.communicate(input=buf[index:])[0]
            index = index + len(pattern)
            i += 1
    print output 

if (len(sys.argv)<2):
    print "Usage: "+sys.argv[0]+" "+"cert_file"

print "Printing all certs from "+sys.argv[1]+":"
print_cert(sys.argv[1])

########NEW FILE########
__FILENAME__ = test_ssl_server
#!/usr/bin/env python
import socket
import ssl
import threading
def run_server(certfile, port):
    bindsock = socket.socket()
    bindsock.bind(('',port))
    bindsock.listen(1)


    sock, source = bindsock.accept()
    sslsock = ssl.wrap_socket(sock, certfile = certfile, server_side = True, ssl_version = ssl.PROTOCOL_SSLv23)
    #TODO: any recv we may or may not want
    #sslsock.recv()
    sslsock.close()
    bindsock.close()
    sock.close()
class ServerThread(threading.Thread):
    def __init__(self, certfile, port, event):
        threading.Thread.__init__(self)
        self.certfile = certfile
        self.port = port
        self.event = event
        self.bound = False
    def run(self):
        try :
            bindsock = socket.socket()
            bindsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            bindsock.bind(('',self.port))
            bindsock.listen(1)
            self.bound = True
            self.bindsock = bindsock
        except:
            # Signal we are done (the caller needs to check we bound correctly!
            self.event.set()
            return
        self.event.set()
        #Don't really care what happens from here out, if it fails it fails
        try:
            sock, source = bindsock.accept()
            self.sock = sock
            sslsock = ssl.wrap_socket(sock, certfile = self.certfile, server_side = True, ssl_version = ssl.PROTOCOL_SSLv23)
            self.sslsock = sslsock
            #TODO: any recv we may or may not want
            #sslsock.recv()
            sslsock.close()
            bindsock.close()
            sock.close()
        except:
            pass
    def close(self):
        try:
            self.bindsock.close()
        except:
            pass
        try:
            self.sock.close()
        except:
            pass
        try:
            self.sslsock.close()
        except:
            pass


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("usage: %s certfile port" % sys.argv[0])
        sys.exit()
    st = ServerThread(sys.argv[1], int(sys.argv[2]), threading.Event())
    st.run()

########NEW FILE########
