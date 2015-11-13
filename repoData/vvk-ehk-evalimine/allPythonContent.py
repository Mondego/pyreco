__FILENAME__ = cgilog
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import os
import evcommon
import evlog
import evlogdata

def get_loglines(prefix):
    to_alog = []
    to_elog = []

    to_alog.append(prefix + " REMOTE_ADDR: " + evlogdata.get_remote_ip())
    to_alog.append(prefix + " HTTP_USER_AGENT: " + evlogdata.get_user_agent())

    if evcommon.HTTP_CERT in os.environ:
        cert = os.environ[evcommon.HTTP_CERT]
        if len(cert) > 0:
            alog, elog = evlogdata.get_cert_data_log(cert, prefix)
            to_alog.append(alog)
            if elog:
                to_elog.append(elog)

    return to_alog, to_elog

def do_log(prefix):
    alog, elog = get_loglines(prefix)
    for el in alog:
        evlog.log(el)
    for el in elog:
        evlog.log_error(el)

def do_log_error(prefix):
    alog, elog = get_loglines(prefix)
    for el in alog:
        evlog.log_error(el)
    for el in elog:
        evlog.log_error(el)

# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = cgivalidator
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import evcommon
import formatutil
import election
import exception_msg

REASON_MISSING = 0
REASON_UNKNOWN = 1
REASON_NO_VALIDATOR = 2
REASON_NOT_SINGLE_VALUE = 3
REASON_NOT_VALID = 4
REASON_NOT_ZIP = 5
REASON_MISSING_ELEMENTS = 6
REASON_TOO_MANY_ELEMENTS = 7
REASON_NO_BALLOT = 8
REASON_ZIPBOMB = 9
REASON_BAD_SIGNATURE = 10

REASONS = {
        REASON_MISSING : "missing",
        REASON_UNKNOWN : "unknown",
        REASON_NO_VALIDATOR : "validator missing",
        REASON_NOT_SINGLE_VALUE : "multiple values",
        REASON_NOT_VALID : "invalid",
        REASON_NOT_ZIP : "badzip",
        REASON_MISSING_ELEMENTS : "missing elements",
        REASON_TOO_MANY_ELEMENTS : "too many elements",
        REASON_NO_BALLOT : "no ballot",
        REASON_ZIPBOMB : "zipbomb",
        REASON_BAD_SIGNATURE : "bad signature",
}

VALIDATORS = {
    evcommon.POST_EVOTE : formatutil.is_vote,
    evcommon.POST_PERSONAL_CODE: formatutil.is_isikukood,
    evcommon.POST_VOTERS_FILES_SHA256: formatutil.is_voters_file_sha256,
    evcommon.POST_SESS_ID: formatutil.is_session_id,
    evcommon.POST_PHONENO: formatutil.is_mobid_phoneno,
    evcommon.POST_MID_POLL: formatutil.is_mobid_poll
}

def is_bdoc_mimetype_file(zi):
    size = len("application/vnd.etsi.asic-e+zip")
    fn = (zi.filename == 'mimetype')
    fs = (zi.file_size == size)
    cs = (zi.compress_size == size)
    return (fn and fs and cs)


def is_bdoc_metainf_dir(zi):
    fn = (zi.filename == 'META-INF/')
    fs = (zi.file_size == 0)
    cs = (zi.compress_size == 0)
    return (fn and fs and cs)


def is_bdoc_manifest_file(zi):
    fn = (zi.filename == 'META-INF/manifest.xml')
    fs = (zi.file_size < 1024)
    cs = (zi.compress_size < 1024)
    return (fn and fs and cs)


def is_encrypted_vote(zi):
    fs = (zi.file_size == 256)
    cs = (zi.compress_size == 256)
    return (fs and cs)


def is_bdoc_signature_file(zi):
    fn = (zi.filename == 'META-INF/signatures0.xml')
    fs = (zi.file_size < 5500)
    cs = (zi.compress_size < 5500)
    return (fn and fs and cs)


ZIPFILE_VALIDATORS = {
    'mimetype' : is_bdoc_mimetype_file,
    'META-INF/' : is_bdoc_metainf_dir,
    'META-INF/manifest.xml' : is_bdoc_manifest_file,
    'META-INF/signatures0.xml' : is_bdoc_signature_file
}


def get_invalid_keys(form, required):
    invalid = []

    for key in required:
        if not form.has_key(key):
            invalid.append((key, REASON_MISSING))

    for key in form:

        values = form.getlist(key)
        extra = "%d, %s" % (len(values), values[:200])

        if not key in required:
            invalid.append((key, REASON_UNKNOWN, extra))
            continue

        if not VALIDATORS.has_key(key):
            invalid.append((key, REASON_NO_VALIDATOR, extra))
            continue

        if len(values) > 1:
            invalid.append((key, REASON_NOT_SINGLE_VALUE, extra))
            continue

        if not VALIDATORS[key](values[0]):
            invalid.append((key, REASON_NOT_VALID, extra))
            continue

    return invalid


HDR_1 = \
"""<asic:XAdESSignatures xmlns:asic="http://uri.etsi.org/02918/v1.2.1#" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:xades="http://uri.etsi.org/01903/v1.3.2#">
<ds:Signature Id="S0">
<ds:SignedInfo xmlns:asic="http://uri.etsi.org/02918/v1.2.1#" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" Id="S0-SignedInfo">
<ds:CanonicalizationMethod Algorithm="http://www.w3.org/2006/12/xml-c14n11">
</ds:CanonicalizationMethod>
<ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha224">
</ds:SignatureMethod>
"""

HDR_2 = \
"""</ds:X509Data></ds:KeyInfo>
<ds:Object Id="S0-object-xades"><xades:QualifyingProperties Id="S0-QualifyingProperties" Target="#S0"><xades:SignedProperties xmlns:asic="http://uri.etsi.org/02918/v1.2.1#" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" Id="S0-SignedProperties">
<xades:SignedSignatureProperties Id="S0-SignedSignatureProperties">
"""

HDR_3 = \
"""<xades:SigningCertificate>
<xades:Cert>
<xades:CertDigest>
<ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#sha224">
</ds:DigestMethod>
"""

HDR_4 = \
"""</xades:IssuerSerial>
</xades:Cert>
</xades:SigningCertificate>
<xades:SignaturePolicyIdentifier>
<xades:SignaturePolicyId>
<xades:SigPolicyId>
<xades:Identifier Qualifier="OIDAsURN">
urn:oid:1.3.6.1.4.1.10015.1000.3.2.1</xades:Identifier>
</xades:SigPolicyId>
<xades:SigPolicyHash>
<ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256">
</ds:DigestMethod>
<ds:DigestValue>3Tl1oILSvOAWomdI9VeWV6IA/32eSXRUri9kPEz1IVs=</ds:DigestValue>
</xades:SigPolicyHash>
<xades:SigPolicyQualifiers>
<xades:SigPolicyQualifier>
<xades:SPURI>
https://www.sk.ee/repository/bdoc-spec21.pdf</xades:SPURI>
</xades:SigPolicyQualifier>
</xades:SigPolicyQualifiers>
</xades:SignaturePolicyId>
</xades:SignaturePolicyIdentifier>
</xades:SignedSignatureProperties>
<xades:SignedDataObjectProperties>
"""

HDR_5 = \
"""
<ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#sha224">
</ds:DigestMethod>
"""

HDR_6 = \
"""</xades:SignedDataObjectProperties>
</xades:SignedProperties>
<xades:UnsignedProperties></xades:UnsignedProperties></xades:QualifyingProperties></ds:Object>
</ds:Signature>
</asic:XAdESSignatures>
"""


def check_prefix(inp, prefix):
    if inp.startswith(prefix):
        return len(prefix)
    return -1


def check_tag(inp, tag_start, tag_end, is_good):
    if not inp.startswith(tag_start):
        return -1

    end = inp.find(tag_end)
    if end == -1:
        return -1

    start = len(tag_start)
    if is_good(inp[start:end]):
        return end + len(tag_end)

    return -1


def check_dataobjects(inp, questions):
    start = 0
    lines = []
    ii = 0
    for el in questions:
        lines.append(\
                "<xades:DataObjectFormat ObjectReference=\"#S0-ref-%d\">\n" % ii)
        lines.append(\
                "<xades:MimeType>application/octet-stream</xades:MimeType>\n")
        lines.append("</xades:DataObjectFormat>\n")
        ii += 1

    for line in lines:
        ret = check_prefix(inp[start:], line)
        if ret == -1:
            return -1
        start = start + ret

    return start


def check_references(inp, questions):
    start = 0
    ref_count = 0
    common_start = "<ds:Reference"
    tag_end = "</ds:Reference>\n"
    taglist = []
    taglist.append(\
            "<ds:Reference Id=\"S0-ref-sp\" Type=\"http://uri.etsi.org/01903#SignedProperties\" URI=\"#S0-SignedProperties\">")
    ii = 0
    for el in questions:
        taglist.append("<ds:Reference Id=\"S0-ref-%d\" URI=\"/%s.evote\">" % (ii, el))
        ii += 1

    while inp[start:].startswith(common_start):
        for tag_start in taglist:
            ret = check_prefix(inp[start:], tag_start)
            if ret > -1:
                taglist.remove(tag_start)
                break
        if ret == -1:
            return -1
        start = start + ret

        ret = check_prefix(inp[start:], HDR_5)
        if ret == -1:
            return -1
        start = start + ret

        ret = check_tag(inp[start:], "<ds:DigestValue>", \
                "</ds:DigestValue>\n</ds:Reference>\n", formatutil.is_base64)
        if ret == -1:
            return -1
        start = start + ret

        ref_count = ref_count + 1

    if ref_count < 2:
        return -1

    return start

def is_well_formed_id_signature(sigdata, questions):

    tag_s_sigval = "</ds:SignedInfo><ds:SignatureValue Id=\"S0-SIG\">\n"
    tag_e_sigval = "</ds:SignatureValue>\n<ds:KeyInfo Id=\"S0-KeyInfo\">\n"
    tag_s_x509 = "<ds:X509Data><ds:X509Certificate>"
    tag_e_x509 = "</ds:X509Certificate>"
    tag_s_stime = "<xades:SigningTime>"
    tag_e_stime = "</xades:SigningTime>\n"
    tag_s_digval = "<ds:DigestValue>"
    tag_e_digval = "</ds:DigestValue>\n"
    tag_s_issuer = "</xades:CertDigest>\n<xades:IssuerSerial>\n" + \
            "<ds:X509IssuerName>"
    tag_e_issuer = "</ds:X509IssuerName>\n"
    tag_s_serial = "<ds:X509SerialNumber>"
    tag_e_serial = "</ds:X509SerialNumber>\n"

    item1 = {
            'validator' : check_prefix,
            'arguments' : {
                'prefix' : HDR_1
                }
            }
    item2 = {
            'validator' : check_references,
            'arguments' : {
                'questions' : questions
                }
            }
    item3 = {
            'validator' : check_tag,
            'arguments' : {
                'tag_start' : tag_s_sigval,
                'tag_end' : tag_e_sigval,
                'is_good' : formatutil.is_base64_lines
                }
            }
    item4 = {
            'validator' : check_tag,
            'arguments' : {
                'tag_start' : tag_s_x509,
                'tag_end' : tag_e_x509,
                'is_good' : formatutil.is_base64_lines
                }
            }
    item5 = {
            'validator' : check_prefix,
            'arguments' : {
                'prefix' : HDR_2
                }
            }
    item6 = {
            'validator' : check_tag,
            'arguments' : {
                'tag_start' : tag_s_stime,
                'tag_end' : tag_e_stime,
                'is_good' : formatutil.is_signing_time
                }
            }
    item7 = {
            'validator' : check_prefix,
            'arguments' : {
                'prefix' : HDR_3
                }
            }
    item8 = {
            'validator' : check_tag,
            'arguments' : {
                'tag_start' : tag_s_digval,
                'tag_end' : tag_e_digval,
                'is_good' : formatutil.is_base64
                }
            }
    item9 = {
            'validator' : check_tag,
            'arguments' : {
                'tag_start' : tag_s_issuer,
                'tag_end' : tag_e_issuer,
                'is_good' : formatutil.is_100utf8
                }
            }
    item10 = {
            'validator' : check_tag,
            'arguments' : {
                'tag_start' : tag_s_serial,
                'tag_end' : tag_e_serial,
                'is_good' : formatutil.is_number100
                }
            }
    item11 = {
            'validator' : check_prefix,
            'arguments' : {
                'prefix' : HDR_4
                }
            }

    item12 = {
            'validator' : check_dataobjects,
            'arguments' : {
                'questions' : questions
                }
            }

    item13 = {
            'validator' : check_prefix,
            'arguments' : {
                'prefix' : HDR_6
                }
            }


    stream = []
    stream.append(item1)
    stream.append(item2)
    stream.append(item3)
    stream.append(item4)
    stream.append(item5)
    stream.append(item6)
    stream.append(item7)
    stream.append(item8)
    stream.append(item9)
    stream.append(item10)
    stream.append(item11)
    stream.append(item12)
    stream.append(item13)

    start = 0
    for item in stream:
        validator = item['validator']
        ret = validator(sigdata[start:], **item['arguments'])
        if ret == -1:
            return False, sigdata[start:start+200]
        start = start + ret

    if start == len(sigdata):
        return True, ''

    return False, sigdata[start:start+200]


def is_well_formed_signature(sigfile, questions):

    hdr1 = sigfile.readline()
    if hdr1 == "<Signature/>":
        hdr2 = sigfile.readline()
        if hdr2 == "":
            return True, ''

    if hdr1 == "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n":
        return is_well_formed_id_signature(sigfile.read(), questions)

    return False, hdr1


def is_well_formed_vote_file(votefile, questions):

    import zipfile

    zipf = zipfile.ZipFile(votefile, "r")
    ziplist = zipf.infolist()

    if (len(ziplist) <= len(ZIPFILE_VALIDATORS)):
        return False, ('vote', REASON_MISSING_ELEMENTS)

    question_validators = {}
    for el in questions:
        question_validators["%s.evote" % el] = is_encrypted_vote

    if (len(ziplist) > ((len(ZIPFILE_VALIDATORS) + len(question_validators)))):
        return False, ('vote', REASON_TOO_MANY_ELEMENTS)

    real_questions = []
    for el in ziplist:
        if ZIPFILE_VALIDATORS.has_key(el.filename):
            if not ZIPFILE_VALIDATORS[el.filename](el):
                return False, (el.filename, REASON_NOT_VALID)

            data = zipf.open(el.filename).read(el.file_size + 1)
            if len(data) > el.file_size:
                return False, (el.filename, REASON_ZIPBOMB)

            continue

        if question_validators.has_key(el.filename):
            if not question_validators[el.filename](el):
                return False, (el.filename, REASON_NOT_VALID)
            real_questions.append(el.filename.split('.')[0])
            continue

        return False, (el.filename, REASON_UNKNOWN)

    if len(real_questions) == 0:
        return False, ('vote', REASON_NO_BALLOT)

    if zipf.testzip() != None:
        return False, ('vote', REASON_NOT_ZIP)

    res, extra = is_well_formed_signature(\
            zipf.open('META-INF/signatures0.xml'), real_questions)

    if not res:
        return False, ('vote', REASON_BAD_SIGNATURE, extra)

    return True, ()


def is_well_formed_vote(b64, questions):

    if not formatutil.is_vote(b64):
        return False, ('vote', REASON_NOT_VALID)

    import StringIO
    import base64

    votedata = base64.b64decode(b64)
    votefile = StringIO.StringIO(votedata)
    return is_well_formed_vote_file(votefile, questions)


def validate_vote(vote, questions):
    try:
        logline = ''
        res, why = is_well_formed_vote(vote, questions)
        if res:
            return True, logline

        if len(why) == 2:
            logline = 'Invalid vote: key - %s, reason - %s' % \
                    (why[0], REASONS[why[1]])
        elif len(why) == 3:
            logline = 'Invalid vote: key - %s, reason - %s, extra - %s' % \
                    (why[0], REASONS[why[1]], why[2][:200])
        else:
            logline = 'Invalid vote: internal error'

        return False, logline
    except:
        logline = 'Invalid vote: key - exception, reason - %s' % \
                exception_msg.trace()
        return False, logline


def validate_form(form, required):
    try:
        logline = ''
        invalid = get_invalid_keys(form, required)
        if len(invalid) <> 0:
            logline = 'Invalid form: '
            for el in invalid:
                if len(el) == 2:
                    logline = "%skey - %s, reason - %s;" % \
                            (logline, el[0], REASONS[el[1]])
                elif len(el) == 3:
                    logline = "%skey - %s, reason - %s, extra - %s" % \
                            (logline, el[0], REASONS[el[1]], el[2][:200])
                else:
                    logline = "%sinternal error" % logline
            return False, logline

        if evcommon.POST_EVOTE in required:
            return validate_vote(\
                    form.getvalue(evcommon.POST_EVOTE), \
                    election.Election().get_questions())

        return True, logline
    except:
        logline = 'Invalid form: key - exception, reason - %s' % \
                exception_msg.trace()
        return False, logline


def validate_sessionid(form):

    key = evcommon.POST_SESS_ID

    if not form.has_key(key):
        return False

    if not VALIDATORS.has_key(key):
        return False

    values = form.getlist(key)
    if len(values) > 1:
        return False

    if not VALIDATORS[key](values[0]):
        return False

    return True


if __name__ == '__main__':
    pass
#    print is_well_formed_vote_file(open('debug_vote.bdoc'), ['RH2018', 'EP2018'])


########NEW FILE########
__FILENAME__ = hes-cgi
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import cgi
import evcommon
import evlog
import hesdisp
import protocol
import sessionid
import cgivalidator
import cgilog
import election
import os

if not evcommon.testrun():
    os.umask(007)
    hesd = hesdisp.HESVoterDispatcher()
    form = cgi.FieldStorage()
    result = protocol.msg_error_technical()
    evlog.AppLog().set_app('HES')

    try:
        if form.has_key(evcommon.POST_EVOTE):
            req_params = [evcommon.POST_EVOTE, evcommon.POST_SESS_ID]

            if cgivalidator.validate_sessionid(form):
                sessionid.setsid(form.getvalue(evcommon.POST_SESS_ID))

            res, logline = cgivalidator.validate_form(form, req_params)
            if res:
                cgilog.do_log('vote/auth')
                result = hesd.hts_vote(form.getvalue(evcommon.POST_EVOTE))
            else:
                cgilog.do_log_error('vote/auth/err')
                evlog.log_error(logline)
        else:
            req_params = []
            res, logline = cgivalidator.validate_form(form, req_params)
            if res:
                cgilog.do_log('cand/auth')
                if election.Election().allow_new_voters():
                    result = hesd.get_candidate_list()
                else:
                    evlog.log_error('nonewvoters')
                    a, b = protocol.plain_error_election_off_after()
                    result = protocol.msg_error(a, b)
            else:
                cgilog.do_log_error('cand/auth/err')
                evlog.log_error(logline)
    except:
        evlog.log_exception()
        result = protocol.msg_error_technical()

    protocol.http_response(result)
    cgi.sys.exit(0)

# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = hes-verify-vote-cgi
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import cgi
import os
import urllib

import evcommon
import evmessage
import evstrings
import election
import formatutil
import protocol
import evlog
import evlogdata
import sessionid

os.umask(007)

APP = "hes-verify-vote.cgi"


def bad_parameters():
    protocol.http_response(evcommon.VERSION + "\n" + \
            evcommon.VERIFY_ERROR + "\n" + \
            evmessage.EvMessage().get_str("BAD_PARAMETERS", \
                evstrings.BAD_PARAMETERS))

def technical_error():
    protocol.http_response(evcommon.VERSION + "\n" + \
            evcommon.VERIFY_ERROR + "\n" + \
            evmessage.EvMessage().get_str("TECHNICAL_ERROR_VOTE_VERIFICATION", \
                evstrings.TECHNICAL_ERROR_VOTE_VERIFICATION))


def do_cgi():
    try:
        elec = election.Election()
        evlog.AppLog().set_app(APP)

        # Create a list of pairs from the form parameters. Don't use a dictionary
        # because that will overwrite recurring keys.
        form = cgi.FieldStorage()
        params = []
        for key in form:
            for value in form.getlist(key):
                params.append((key, value))

        # Only accept up to a single parameter
        if len(params) > 1:
            def keys(pairs):
                """Return a comma-separated list of the keys."""
                return ", ".join([pair[0] for pair in pairs])

            evlog.log_error("Too many query parameters: " + keys(params))
            bad_parameters()
            return

        # Only accept the POST_VERIFY_VOTE parameter.
        if len(params) and params[0][0] != evcommon.POST_VERIFY_VOTE:
            evlog.log_error("Unknown query parameter \"%s\"" % params[0][0])
            bad_parameters()
            return

        # Make sure the parameter is correctly formatted.
        if not formatutil.is_vote_verification_id(params[0][1]):
            # Don't write to disk; we don't know how large the value is
            evlog.log_error("Malformed vote ID")
            bad_parameters()
            return

        evlog.log("verif/auth REMOTE_ADDR: " + evlogdata.get_remote_ip())
        evlog.log("verif/auth VOTE-ID: " + params[0][1])

        params.append((evcommon.POST_SESS_ID, sessionid.voting()))

        url = "http://" + elec.get_hts_ip() + "/" + elec.get_hts_verify_path()
        conn = urllib.urlopen(url, urllib.urlencode(params))
        protocol.http_response(conn.read())
    except:
        evlog.log_exception()
        technical_error()

if not evcommon.testrun():
    do_cgi()
    cgi.sys.exit(0)
# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = hts-cgi
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import htsalldisp
import cgi
import evcommon
import protocol
import sessionid
import os

def bad_input():
    _msg = htsalldisp.bad_cgi_input()
    protocol.http_response(_msg)
    cgi.sys.exit(0)


if not evcommon.testrun():
    os.umask(007)
    form = cgi.FieldStorage()

    has_sha256 = form.has_key(evcommon.POST_VOTERS_FILES_SHA256)
    has_code = form.has_key(evcommon.POST_PERSONAL_CODE)
    has_vote = form.has_key(evcommon.POST_EVOTE)
    has_sess = form.has_key(evcommon.POST_SESS_ID)

    if (not has_sha256):
        bad_input()

    val_sha = form.getvalue(evcommon.POST_VOTERS_FILES_SHA256)

    if (not has_code) and (not has_vote):
        msg = htsalldisp.consistency(val_sha)
        protocol.http_response(msg)
        cgi.sys.exit(0)

    if (has_sess):
        sessionid.setsid(form.getvalue(evcommon.POST_SESS_ID))

    if has_code and has_vote:
        if (has_sess):
            val_code = form.getvalue(evcommon.POST_PERSONAL_CODE)
            val_vote = form.getvalue(evcommon.POST_EVOTE)
            msg = htsalldisp.store_vote(val_sha, val_code, val_vote)
            protocol.http_response(msg)
            cgi.sys.exit(0)
        else:
            bad_input()

    if has_code and (not has_vote):
        if (has_sess):
            val_code = form.getvalue(evcommon.POST_PERSONAL_CODE)
            msg = htsalldisp.check_repeat(val_sha, val_code)
            protocol.http_response(msg)
            cgi.sys.exit(0)
        else:
            bad_input()

    bad_input()


# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = hts-verify-vote-cgi
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import cgi
import os

import evcommon
import evmessage
import evstrings
import htsalldisp
import protocol
import sessionid
from evlog import AppLog

def bad_parameters():
    protocol.http_response(evcommon.VERSION + "\n" + \
            evcommon.VERIFY_ERROR + "\n" + \
            evmessage.EvMessage().get_str("BAD_PARAMETERS", \
                evstrings.BAD_PARAMETERS))
    cgi.sys.exit(0)

if not evcommon.testrun():

    os.umask(007)

    APP = "hts-verify-vote.cgi"
    AppLog().set_app(APP)

    form = cgi.FieldStorage()

    vote = None

    if form.has_key(evcommon.POST_SESS_ID):
        sessionid.setsid(form.getvalue(evcommon.POST_SESS_ID))

    if form.has_key(evcommon.POST_VERIFY_VOTE):
        values = form.getlist(evcommon.POST_VERIFY_VOTE)
        if len(values) == 1:
            vote = values[0]
        else:
            # Don't write the values to disk; we don't know how large they are
            AppLog().log_error("Too many parameter values")
            bad_parameters()

    protocol.http_response(htsalldisp.verify_vote(vote))
    cgi.sys.exit(0)

# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = mobid-cgi
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import cgi
import evcommon
import middisp
import protocol
import evlog
import sessionid
import cgivalidator
import cgilog
import election
import os

if not evcommon.testrun():
    os.umask(007)
    form = cgi.FieldStorage()
    result = protocol.msg_error_technical()
    mid = middisp.MIDDispatcher()
    evlog.AppLog().set_app('MID')

    try:
        has_sess = form.has_key(evcommon.POST_SESS_ID)
        has_poll = form.has_key(evcommon.POST_MID_POLL)
        if has_sess:
            if cgivalidator.validate_sessionid(form):
                sessionid.setsid(form.getvalue(evcommon.POST_SESS_ID))
            if has_poll:
                req_params = [evcommon.POST_MID_POLL, evcommon.POST_SESS_ID]
                res, logline = cgivalidator.validate_form(form, req_params)
                if res:
                    result = mid.poll()
                else:
                    evlog.log_error(logline)
            else:
                req_params = [evcommon.POST_EVOTE, evcommon.POST_SESS_ID]
                res, logline = cgivalidator.validate_form(form, req_params)
                if res:
                    cgilog.do_log("vote/auth")
                    result = mid.init_sign(form)
                else:
                    cgilog.do_log_error('vote/auth/err')
                    evlog.log_error(logline)
        else:
            req_params = [evcommon.POST_PHONENO]
            res, logline = cgivalidator.validate_form(form, req_params)
            if res:
                cgilog.do_log("cand/auth")
                phoneno = form.getvalue(evcommon.POST_PHONENO)
                evlog.log("PHONENO: " + phoneno)
                if election.Election().allow_new_voters():
                    result = mid.init_auth(phoneno)
                else:
                    evlog.log_error('nonewvoters')
                    a, b = protocol.plain_error_election_off_after()
                    result = protocol.msg_error(a, b)
            else:
                cgilog.do_log_error('cand/auth/err')
                evlog.log_error(logline)
    except:
        evlog.log_exception()
        result = protocol.msg_error_technical()

    protocol.http_response(result)
    cgi.sys.exit(0)

# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = apply_changes
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import sys
from election import Election
from election import ElectionState
import evlog
import ksum
import inputlists
import time
import uiutil
import evcommon


class BufferedLog:

    def __init__(self, log_file, app, elid):
        self.__logger = evlog.Logger(Election().get_server_str())
        self.__logger.set_logs(log_file)
        self.__buffer = []

    def log_error(self, msg):
        self.__buffer.append(msg)
        self.__logger.log_err(message=msg)

    def empty(self):
        return len(self.__buffer) == 0

    def output_errors(self):
        for elem in self.__buffer:
            sys.stderr.write(' %s\n' % elem)


def create_tokend_file(tokend, reg, elid):

    outf = None

    try:
        import hts
        hh = hts.HTS(elid)

        fn = 'tokend.'
        fn += time.strftime('%Y%m%d%H%M%S')

        out = ''

        for el in tokend:
            if hh.haaletanud(el):
                out += el
                out += '\t'
                out += '\t'.join(tokend[el])
                out += '\n'

        if len(out) != 0:
            out = elid + '\n' + out
            out = '1\n' + out
            filename = reg.path(['hts', 'output', fn])
            outf = file(filename, 'w')
            outf.write(out)
            outf.close()
            ksum.store(filename)
            outf = None

    finally:
        if (outf != None):
            outf.close()


def apply_changes(elid, voter_f):
    """Muudatuste rakendamine"""

    vl = None
    tokend = {}

    def check_state():
        if not ElectionState().can_apply_changes():
            sys.stderr.write('Selles hääletuse faasis (%s) pole võimalik '\
                'nimekirju uuendada\n' \
                % ElectionState().str())
            sys.exit(1)

    try:

        buflog = None

        if Election().is_hes():
            root = 'hes'
        elif Election().is_hts():
            root = 'hts'
        else:
            raise Exception('Vigane serveritüüp')

        buflog = BufferedLog(Election(). \
                get_path(evcommon.VOTER_LIST_LOG_FILE), \
                'APPLY-CHANGES', elid)

        check_state()
        reg = Election().get_sub_reg(elid)
        ed = inputlists.Districts()
        ed.load(root, reg)
        vl = inputlists.VotersList(root, reg, ed)
        vl.attach_elid(elid)
        vl.ignore_errors()
        evlog.AppLog().set_app('APPLY-CHANGES')
        vl.attach_logger(evlog.AppLog())

        print "Kontrollin valijate faili kontrollsummat"
        if not ksum.check(voter_f):
            raise Exception('Valijate faili kontrollsumma ei klapi\n')

        voters_file_sha256 = ksum.compute(voter_f)
        if Election().get_root_reg().check(\
            ['common', 'voters_file_hashes', voters_file_sha256]):
            raise Exception('Kontrollsummaga %s fail on juba laetud\n' \
                % voters_file_sha256)

        if not vl.check_format(voter_f, 'Kontrollin valijate nimekirja: '):
            print "Valijate nimekiri ei vasta vormingunõuetele"
            sys.exit(1)
        else:
            print 'Valijate nimekiri OK'

        vl.attach_logger(buflog)
        if not vl.check_muudatus( \
            'Kontrollin muudatuste kooskõlalisust: ', \
            ElectionState().election_on(), tokend):
            print "Sisend ei ole kooskõlas olemasoleva konfiguratsiooniga"
        else:
            print "Muudatuste kooskõlalisus OK"

        _apply = 1
        if not buflog.empty():
            print 'Muudatuste sisselaadimisel esines vigu'
            buflog.output_errors()
            _apply = uiutil.ask_yes_no(\
            'Kas rakendan kooskõlalised muudatused?')

        if not _apply:
            buflog.log_error('Muudatusi ei rakendatud')
            print 'Muudatusi ei rakendatud'
        else:
            if ElectionState().election_on() and root == 'hts':
                create_tokend_file(tokend, reg, elid)
            a_count, d_count = vl.create('Paigaldan valijaid: ')
            print 'Teostasin %d lisamist ja %d eemaldamist' \
                % (a_count, d_count)
            Election().copy_voters_file(elid, root, voter_f)
            print 'Muudatuste rakendamine lõppes edukalt'

    except SystemExit:
        sys.stderr.write('Viga muudatuste laadimisel\n')
        if buflog:
            buflog.output_errors()
        raise

    except Exception, ex:
        sys.stderr.write('Viga muudatuste laadimisel: ' + str(ex) + '\n')
        if buflog:
            buflog.output_errors()
        sys.exit(1)

    finally:
        if not vl == None:
            vl.close()


def usage():

    if (len(sys.argv) != 3):
        sys.stderr.write('Kasutamine: ' + sys.argv[0] + \
            ' <valimiste-id> <valijate-fail>\n')
        sys.exit(1)

    evcommon.checkfile(sys.argv[2])

if __name__ == '__main__':
    usage()
    apply_changes(sys.argv[1], sys.argv[2])

# vim:set ts=4 sw=4 expandtab et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = autocmd
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import os
import signal
import subprocess
import sys
import time

import election
import evcommon
import evreg

# Commands to automatically execute.
COMMAND_START = "start"
COMMAND_PREPARE_STOP = "prepare_stop"
COMMAND_STOP = "stop"

# Expected server states for the commands.
EXPECTED = {
        COMMAND_START:        election.ETAPP_ENNE_HAALETUST,
        COMMAND_PREPARE_STOP: election.ETAPP_HAALETUS,
        COMMAND_STOP:         election.ETAPP_HAALETUS,
    }

# The name of this module.
MODULE_AUTOCMD = "autocmd"

# The registry key for this module.
AUTOCMD_KEY = ["common", "autocmd"]

TIME_FORMAT = "%H:%M %d.%m.%Y"

# Registry location of the pid of a console to refresh when a command executes.
# It might make more sense for these to be in evui/evui.py, but we can't import
# evui from here, because it is a private module.
REFRESH_PID_KEY = ["common"]
REFRESH_PID_VALUE = "refresh.pid"

# Translated messages.
ERROR_SUBPROCESS = "Programmi väljakutsel esines viga: %s"
ERROR_SCHEDULE = "Automaatse sündmuse seadistamine ebaõnnestus!"

def stop_grace_period():
    """Get the configured time between COMMAND_PREPARE_STOP and COMMAND_STOP."""
    reg = evreg.Registry(root=evcommon.EVREG_CONFIG)
    try:
        return reg.read_integer_value(AUTOCMD_KEY, "grace").value
    except (IOError, LookupError):
        return None

def set_stop_grace_period(grace):
    """Configure the time between COMMAND_PREPARE_STOP and COMMAND_STOP."""
    reg = evreg.Registry(root=evcommon.EVREG_CONFIG)
    reg.ensure_key(AUTOCMD_KEY)
    reg.create_integer_value(AUTOCMD_KEY, "grace", grace)

def _job_value(cmd):
    return cmd + "_job"

def _time_value(cmd):
    return cmd + "_time"

def scheduled(cmd):
    reg = evreg.Registry(root=evcommon.EVREG_CONFIG)
    if not reg.check(AUTOCMD_KEY):
        return None
    try:
        job = reg.read_integer_value(AUTOCMD_KEY, _job_value(cmd)).value
        timestr = reg.read_string_value(AUTOCMD_KEY, _time_value(cmd)).value
    except (IOError, LookupError):
        return None
    return job, timestr

def _at(timestr, command):
    proc = subprocess.Popen(("at", timestr),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    _, err = proc.communicate(command)

    if proc.returncode != 0:
        print ERROR_SUBPROCESS % err
        return None

    for line in err.splitlines():
        if line.startswith("job "):
            _, job, _ = line.split(None, 2)
    return int(job)

def schedule(cmd, tstruct):
    if scheduled(cmd):
        raise Exception, "Command already scheduled"
    timestr = time.strftime(TIME_FORMAT, tstruct)
    job = _at(timestr, "python -m %s %i %s" % (MODULE_AUTOCMD, EXPECTED[cmd], cmd))
    if not job:
        print ERROR_SCHEDULE
        return

    reg = evreg.Registry(root=evcommon.EVREG_CONFIG)
    reg.ensure_key(AUTOCMD_KEY)
    reg.create_integer_value(AUTOCMD_KEY, _job_value(cmd), job)
    reg.create_string_value(AUTOCMD_KEY, _time_value(cmd), timestr)

def _atrm(job):
    try:
        subprocess.check_output(("atrm", str(job)), stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        print ERROR_SUBPROCESS % e.output

def _clean_reg(cmd):
    reg = evreg.Registry(root=evcommon.EVREG_CONFIG)
    try:
        reg.delete_value(AUTOCMD_KEY, _job_value(cmd))
    except OSError:
        pass
    try:
        reg.delete_value(AUTOCMD_KEY, _time_value(cmd))
    except OSError:
        pass

def unschedule(cmd, job):
    _atrm(job)
    _clean_reg(cmd)

def _execute_start():
    if election.ElectionState().get() == election.ETAPP_ENNE_HAALETUST:
        election.ElectionState().next()

def _execute_prepare_stop():
    import datetime

    if election.ElectionState().election_on():
        election.Election().refuse_new_voters()
        sched = scheduled(COMMAND_PREPARE_STOP)
        minutes = stop_grace_period()
        if not sched or not minutes:
            return
        _, time = sched

        dt = datetime.datetime.strptime(time, TIME_FORMAT)
        dt += datetime.timedelta(minutes=minutes)
        print "Scheduling command \"stop\" for %s" % dt
        schedule(COMMAND_STOP, dt.timetuple())

def _execute_stop():
    if election.ElectionState().election_on():
        election.ElectionState().next()

def _signal_ui():
    print "Signaling UI to refresh...",
    try:
        reg = evreg.Registry(root=evcommon.EVREG_CONFIG)
        pid = reg.read_integer_value(REFRESH_PID_KEY, REFRESH_PID_VALUE).value
    except IOError:
        print "No UI PID found."
    else:
        print "Found UI with PID %i" % pid
        os.kill(pid, signal.SIGUSR1)

def _main(expected, cmd):
    if election.ElectionState().get() == int(expected):
        print "Executing automatic command \"%s\"" % cmd
        if cmd == COMMAND_START:
            _execute_start()
        elif cmd == COMMAND_PREPARE_STOP:
            _execute_prepare_stop()
        elif cmd == COMMAND_STOP:
            _execute_stop()
        else:
            raise Exception, "Unknown command"
        _clean_reg(cmd)
        _signal_ui()
        print "Done."
    else:
        print "Unexpected state, nothing to do."

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print "Usage: %s <expected-state> <command>" % sys.argv[0]
        print "  Checks that the server is in state <expected-state> and then " \
                "executes the commands associated with <command>."
        print "  <expected-state> is a constant from election.py"
        print "  <command> is a constant from autocmd.py"
        sys.exit(1)
    _main(sys.argv[1], sys.argv[2])

# vim: set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = check_bdocconf
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import sys
import evcommon
import subprocess
import re
import bdocconfig
import os
import tempfile
import shutil

def check_bdoc_conf(conf_dir):

    tmpdir = None

    try:
        conf = bdocconfig.BDocConfig()
        conf.load(conf_dir)

        dirname = tempfile.mkdtemp()
        conf.save(dirname)

        cacerts1 = set()
        cadir = "%s/ca" % dirname
        for root, dirs, files in os.walk(cadir):
            for el in files:
                cacerts1.add(el)

        processed = subprocess.check_output(['c_rehash', cadir])
        lines = processed.split('\n')

        cacerts2 = set()
        for line in lines:
            m = re.match(r"(.*) => (.*)", line)
            if m:
                cacerts2.add(m.group(1))

        return cacerts1.difference(cacerts2)
    finally:
        if tmpdir:
            shutil.rmtree(tmpdir)


def usage():

    """
    Kontrollib BDoc konfiguratsiooni.
    """

    if (len(sys.argv) != 2):
        sys.stderr.write('Kasutamine: ' + sys.argv[0] + \
            ' <conf_dir>\n')
        sys.exit(1)

    evcommon.checkfile(sys.argv[1])


def main_function():
    try:
        usage()
        certs = check_bdoc_conf(sys.argv[1])

        if len(certs) == 0:
            print 'Konfiguratsiooni kontroll-laadimine õnnestus'
        else:
            print 'Probleemsed serdid: ', certs

    except SystemExit:
        sys.stderr.write('Konfiguratsiooni kontroll nurjus\n')
        sys.exit(1)
    except Exception, ex:
        sys.stderr.write('Konfiguratsiooni kontroll nurjus: %s\n' % str(ex))
        sys.exit(1)


if __name__ == '__main__':
    main_function()

# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = check_consistency
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import sys
import evcommon
import exception_msg
import hesdisp

def check_consistency():
    hes = hesdisp.HESDispatcher()
    res, msg = hes.hts_consistency_check()
    if res == evcommon.EVOTE_CONSISTENCY_YES:
        print 'HES ja HTS on kooskõlalised'
    elif res == evcommon.EVOTE_CONSISTENCY_NO:
        print 'HES ja HTS ei ole kooskõlalised'
    else:
        print 'Viga HES ja HTS kooskõlalisuse kontrollil (%s)' % msg

if __name__ == '__main__':
    #pylint: disable-msg=W0702
    try:
        check_consistency()
    except:
        sys.stderr.write('Viga HES ja HTS kooskõlalisuse kontrollil:' +
            exception_msg.trace() + '\n')
        sys.exit(1)

# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = check_inputlists
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import getopt
import sys
import inputlists
import evcommon


class BufferedLog:

    # pylint: disable-msg=R0903

    def __init__(self):
        pass

    def log_error(self, msg):
        # pylint: disable-msg=R0201
        # no error
        print msg


def usage():
    sys.stderr.write('Kasutamine: ' + sys.argv[0] + \
        ' -d <jaoskondade-fail> -c <valikute-fail> -v <valijate-fail>\n'\
        'NB! Failid ei ole BDOC failid, vaid tekstifailid.\n')

def check_inputlists(args):

    ed = None
    ch = None
    vl = None

    dist_f = None
    choices_f = None
    voters_f = None

    try:
        opts, args = getopt.getopt(args[1:], "d:c:v:h")
    except getopt.GetoptError, err:
        print str(err)
        usage()
        sys.exit(2)

    for option, value in opts:
        if option == "-v":
            voters_f = value
            evcommon.checkfile(voters_f)
        elif option == "-c":
            choices_f = value
            evcommon.checkfile(choices_f)
        elif option == "-d":
            dist_f = value
            evcommon.checkfile(dist_f)
        elif option == "-h":
            usage()
            sys.exit()
        else:
            assert False, "unhandled option"

    if (not dist_f) and (not choices_f) and (not voters_f):
        usage()
        sys.exit()

    blog = BufferedLog()

    if dist_f:
        ed = inputlists.Districts()
        ed.attach_logger(blog)
        if not ed.check_format(dist_f, 'Kontrollin jaoskondade nimekirja: '):
            print "Jaoskondade nimekiri ei vasta nõuetele"
        else:
            print "Jaoskondade nimekiri OK"

    if choices_f:
        ch = inputlists.ChoicesList(ed)
        ch.attach_logger(blog)
        if not ch.check_format(choices_f, 'Kontrollin valikute nimekirja: '):
            print "Valikute nimekiri ei vasta nõuetele"
        else:
            print "Valikute nimekiri OK"

    if voters_f:
        vl = inputlists.VotersList(None, None, ed)
        vl.attach_logger(blog)
        vl.ignore_errors()
        if not vl.check_format(voters_f, 'Kontrollin valijate nimekirja: '):
            print "Valijate nimekiri ei vasta nõuetele"
        else:
            print "Valijate nimekiri OK"


if __name__ == '__main__':
    check_inputlists(sys.argv)


# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = config_bdoc
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import sys
from election import Election
import evcommon
import bdocconfig
import subprocess

def set_bdoc_conf(conf_dir):
    conf = bdocconfig.BDocConfig()
    conf.load(conf_dir)
    conf.save(Election().get_bdoc_conf())
    subprocess.check_call(['c_rehash', Election().get_bdoc_ca()])

def usage():

    """
    Laeb BDoc spetsiifilisi konfiguratsioonifaile.
    Sertifikaatide jaoks bdoc.conf.
    """

    if (len(sys.argv) != 2):
        sys.stderr.write('Kasutamine: ' + sys.argv[0] + \
            ' <conf_dir>\n')
        sys.exit(1)

    evcommon.checkfile(sys.argv[1])


def main_function():
    try:
        usage()
        set_bdoc_conf(sys.argv[1])
        Election().config_bdoc_done()
        print "Sertifikaatide konfiguratsiooni laadimine oli edukas."
    except SystemExit:
        sys.stderr.write('Konfiguratsiooni laadimine nurjus\n')
        sys.exit(1)
    except Exception, ex:
        Election().config_bdoc_done(False)
        sys.stderr.write('Konfiguratsiooni laadimine nurjus: %s\n' % str(ex))
        sys.exit(1)


if __name__ == '__main__':
    main_function()

# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = config_common
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import os
import sys
import inputlists
import regrights
from election import Election
from election import ElectionState
from evlog import AppLog
import exception_msg
import evcommon
import ksum
import question

import bdocconfig
import bdocpython
import bdocpythonutils


def checkfile(filename):
    if not os.access(filename, os.F_OK):
        print 'Faili ' + filename + ' ei eksisteeri\n'
        return False
    if not os.access(filename, os.R_OK):
        print 'Faili ' + filename + ' ei saa lugeda\n'
        return False

    return True


class ConfCreator:

    def __init__(self):
        self.elid = None
        self._vl = None
        self._ed = None
        self._ch = None
        self.reg = None
        self.quest = None
        self.root = None
        self.voter_f = None

        self.conf = bdocconfig.BDocConfig()
        self.conf.load(Election().get_bdoc_conf())

    def __del__(self):
        if not self._vl == None:
            self._vl.close()

    def check_districts_file(self, jaosk_f):
        tmp_jaosk_f = None
        try:
            if not checkfile(jaosk_f):
                return False

            print 'Kontrollin jaoskondade faili volitusi'
            ret = regrights.kontrolli_volitusi(self.elid, jaosk_f, 'JAOSK', \
                self.conf)
            if not ret[0]:
                print 'Jaoskondade faili volituste '\
                    'kontroll andis negatiivse tulemuse'
                print ret[1]
                return False

            tmp_jaosk_f = bdocpythonutils.get_doc_content_file(jaosk_f)

            self._ed = inputlists.Districts()
            self._ed.attach_elid(self.elid)
            self._ed.attach_logger(AppLog())
            if not self._ed.check_format(tmp_jaosk_f, \
                'Kontrollin jaoskondade nimekirja: '):
                print "Jaoskondade nimekiri ei vasta nõuetele"
                return False
            print "Jaoskondade nimekiri OK"
            return True
        finally:
            if not tmp_jaosk_f == None:
                os.unlink(tmp_jaosk_f)

    def check_choices_file(self, valik_f):

        tmp_valik_f = None
        try:
            if not checkfile(valik_f):
                return False

            print 'Kontrollin valikutefaili volitusi'
            ret = regrights.kontrolli_volitusi(self.elid, valik_f, 'VALIK', \
                self.conf)
            if not ret[0]:
                print 'Valikute faili volituste kontroll '\
                    'andis negatiivse tulemuse'
                print ret[1]
                return False

            tmp_valik_f = bdocpythonutils.get_doc_content_file(valik_f)

            self._ch = self.quest.choices_list(self._ed)
            self._ch.attach_elid(self.elid)
            self._ch.attach_logger(AppLog())
            if not self._ch.check_format(tmp_valik_f, \
                'Kontrollin valikute nimekirja: '):
                print "Valikute nimekiri ei vasta nõuetele"
                return False
            print "Valikute nimekiri OK"
            return True
        finally:
            if not tmp_valik_f == None:
                os.unlink(tmp_valik_f)

    def check_voters_file(self):

    # HES & HTS

        if not checkfile(self.voter_f):
            return False

        print "Kontrollin valijate faili kontrollsummat"
        if not ksum.check(self.voter_f):
            print "Valijate faili kontrollsumma ei klapi"
            return False

        self._vl = inputlists.VotersList(self.root, self.reg, self._ed)
        self._vl.attach_elid(self.elid)
        self._vl.attach_logger(AppLog())
        if not self._vl.check_format(self.voter_f, \
            'Kontrollin valijate nimekirja: '):
            print "Valijate nimekiri ei vasta nõuetele"
            return False

        if not self._vl.algne:
            print "Valijate nimekirja tüüp ei ole 'algne'"
            return False

        print "Valijate nimekiri OK"
        return True

    def do_it(self):

        c_ring, c_dist = self._ed.create(self.root, self.reg)
        print 'Paigaldatud %d ringkonda ja %d jaoskonda' % (c_ring, c_dist)

        c_choice = self._ch.create(self.quest.choices_proxy())
        print 'Paigaldatud %d valikut' % c_choice

        if self.root == 'hes' or self.root == 'hts':
            c_add, c_del = self._vl.create('Paigaldan valijaid: ')
            print 'Valijad on paigaldatud. '\
                'Teostati %d lisamist ja %d eemaldamist'\
                % (c_add, c_del)
            Election().copy_voters_file(self.elid, self.root, self.voter_f)

        return True

    def prepare(self, confer_name, server_root):

        self.root = server_root

        if not ElectionState().can_load_conf():
            print 'Selles hääletuse faasis (%s) valimisinfot laadida ei saa'\
                % ElectionState().str()
            return False

        self.reg = Election().get_sub_reg(self.elid)
        AppLog().set_app(confer_name, self.elid)
        AppLog().log('Valimiste failide laadimine: ALGUS')
        self.quest = question.Question(self.elid, self.root, self.reg)
        self.quest.reset_data()

        print 'Valimised: ' + self.elid
        return True

    def success(self):
        Election().config_server_elid_done(self.elid)
        AppLog().log('Valimiste failide laadimine: LÕPP')
        print 'Valimiste failide laadimine oli edukas'

    def failure(self):
        self.quest.reset_data()
        Election().config_server_elid_done(self.elid, False)
        AppLog().log('Valimiste failide laadimine: LÕPP')
        print 'Valimiste failide laadimine ebaõnnestus'


def do_configure(apptype, elid, jaosk_f=None, voter_f=None, valik_f=None):

    def do_conf(cc):
        #pylint: disable-msg=W0702
        try:
            cc.elid = elid
            cc.voter_f = voter_f

            if not cc.prepare('CONFIGURATOR', apptype):
                return False

            if jaosk_f:
                if not cc.check_districts_file(jaosk_f):
                    return False

            if valik_f:
                if not cc.check_choices_file(valik_f):
                    return False

            if voter_f:
                if not cc.check_voters_file():
                    return False

            if not cc.do_it():
                return False
            return True

        except:
            print 'Viga valimiste failide laadimisel'
            print exception_msg.trace()
            return False

    bdocpython.initialize()

    try:
        my_cc = ConfCreator()
        if do_conf(my_cc):
            my_cc.success()
            return True
        else:
            my_cc.failure()
            return False
    finally:
        bdocpython.terminate()


def config_hts(elid, jaosk_f, voter_f, valik_f):
    return do_configure(evcommon.APPTYPE_HTS, elid, jaosk_f, voter_f, valik_f)


def config_hes(elid, jaosk_f, voter_f, valik_f):
    return do_configure(evcommon.APPTYPE_HES, elid, jaosk_f, voter_f, valik_f)


def config_hlr(elid, jaosk_f, valik_f):
    return do_configure(evcommon.APPTYPE_HLR, elid, jaosk_f, None, valik_f)


def usage_print():
    sys.stderr.write('Kasutamine: ' + sys.argv[0] + ' <parameetrid>\n')
    sys.stderr.write('\t' + evcommon.APPTYPE_HES + \
        ' <elid> <jaoskondade-fail> <valijate-fail> <valikute-fail>\n')
    sys.stderr.write('\t' + evcommon.APPTYPE_HTS + \
        ' <elid> <jaoskondade-fail> <valijate-fail> <valikute-fail>\n')
    sys.stderr.write('\t' + evcommon.APPTYPE_HLR + \
        ' <elid> <jaoskondade-fail> <valikute-fail>\n')
    sys.exit(1)


def usage():

    if (len(sys.argv) < 2):
        usage_print()

    if not sys.argv[1] in evcommon.APPTYPES:
        usage_print()

    if sys.argv[1] == evcommon.APPTYPE_HES or \
            sys.argv[1] == evcommon.APPTYPE_HTS:
        if (len(sys.argv) != 6):
            usage_print()
        else:
            evcommon.checkfile(sys.argv[3])
            evcommon.checkfile(sys.argv[4])
            evcommon.checkfile(sys.argv[5])

    if sys.argv[1] == evcommon.APPTYPE_HLR:
        if (len(sys.argv) != 5):
            usage_print()
        else:
            evcommon.checkfile(sys.argv[3])
            evcommon.checkfile(sys.argv[4])


def main_function():
    usage()
    res = False
    if sys.argv[1] == evcommon.APPTYPE_HES:
        res = config_hes(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])

    if sys.argv[1] == evcommon.APPTYPE_HTS:
        res = config_hts(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])

    if sys.argv[1] == evcommon.APPTYPE_HLR:
        res = config_hlr(sys.argv[2], sys.argv[3], sys.argv[4])

    return res

if __name__ == "__main__":
    main_function()

# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = config_hlr_input
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import os
import sys
import ksum
from election import Election

def check_file(ffile):
    return os.access(ffile, os.F_OK)


def usage():
    print "Kasutamine:"
    print "    %s <valimiste_id> <loendamisele_minevate_häälte_fail>" \
        % sys.argv[0]
    sys.exit(1)


def main_function():
    if len(sys.argv) != 3:
        usage()

    el_id = sys.argv[1]
    _if = sys.argv[2]


    if not ksum.check(_if, True):
        print "Kontrollsumma ei klapi"
        sys.exit(1)

    reg = Election().get_sub_reg(el_id)
    reg.ensure_key(['hlr', 'input'])
    dst = reg.path(['hlr', 'input', 'votes'])
    os.system("cp " + _if + " " + dst)
    ksum.store(dst)
    Election().config_hlr_input_elid_done(el_id)


if __name__ == '__main__':
    main_function()


# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = config_hsm
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import sys
import exception_msg
from election import Election

NOT_DEFINED_STR = "pole määratud"

#pylint: disable-msg=W0702


def get_hsm():

    try:
        hsm_token_name = Election().get_hsm_token_name()
    except:
        hsm_token_name = NOT_DEFINED_STR

    try:
        hsm_priv_key = Election().get_hsm_priv_key()
    except:
        hsm_priv_key = NOT_DEFINED_STR

    try:
        pkcs11_path = Election().get_pkcs11_path()
    except:
        pkcs11_path = NOT_DEFINED_STR

    print "Token'i nimi: %s" % hsm_token_name
    print "Privaatvõtme nimi: %s" % hsm_priv_key
    print "PKCS11 teegi asukoht: %s" % pkcs11_path


def set_hsm(token_name, priv_key, pkcs11_path):

    try:
        Election().set_hsm_token_name(token_name)
        Election().set_hsm_priv_key(priv_key)
        Election().set_pkcs11_path(pkcs11_path)
        Election().config_hsm_done()
    except:
        Election().config_hsm_done(False)
        sys.stderr.write("HSMi konfigureerimine nurjus: %s\n"
            % exception_msg.trace())
        sys.exit(1)


def usage():
    print 'Kasutamine: ' + sys.argv[0] + \
        ' get|(set <tokenname> <privkeylabel> <pkcs11 path>)'
    sys.exit(1)


def main_function():
    if (len(sys.argv) != 2) and (len(sys.argv) != 5):
        usage()

    if (len(sys.argv) == 2) and (sys.argv[1] != 'get'):
        usage()

    if (len(sys.argv) == 5) and (sys.argv[1] != 'set'):
        usage()

    cmd = sys.argv[1]

    if cmd == 'get' or cmd == 'set':
        if cmd == 'get':
            get_hsm()
        else:
            set_hsm(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        print 'Operatsioon ei ole teostatav'
        sys.exit(1)


if __name__ == '__main__':
    main_function()


# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = config_hth
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import sys
import exception_msg
from election import Election

NOT_DEFINED_STR = "pole määratud"


def usage():
    print 'Kasutamine: ' + sys.argv[0] + ' get|(set <hts> <htspath> <htsverifypath>)'
    sys.exit(1)


def execute(ip, path, verify):
    Election().set_hts_ip(ip)
    Election().set_hts_path(path)
    Election().set_hts_verify_path(verify)
    Election().config_hth_done()


#pylint: disable-msg=W0702

def main_function():
    if len(sys.argv) < 2:
        usage()

    if sys.argv[1] == 'get' or sys.argv[1] == 'set':

        if sys.argv[1] == 'get':
            try:
                hts_ip = Election().get_hts_ip()
            except:
                hts_ip = NOT_DEFINED_STR

            try:
                hts_path = Election().get_hts_path()
            except:
                hts_path = NOT_DEFINED_STR

            try:
                hts_verify = Election().get_hts_verify_path()
            except:
                hts_verify = NOT_DEFINED_STR

            print "HTS IP: %s" % hts_ip
            print "HTS path: %s" % hts_path
            print "HTS verification path: %s" % hts_verify
        else:
            try:
                if len(sys.argv) != 5:
                    usage()
                execute(sys.argv[2], sys.argv[3], sys.argv[4])
            except:
                Election().config_hth_done(False)
                sys.stderr.write("HTSi konfigureerimine nurjus: %s\n" \
                    % exception_msg.trace())
                sys.exit(1)
    else:
        print 'Operatsioon ei ole teostatav'
        sys.exit(1)


if __name__ == '__main__':
    main_function()


# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = election
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import os.path
import evreg
import time
import shutil
import ksum
import evcommon
import formatutil
import question
import protocol
import singleton

ELECTION_ID = 'electionid'

ETAPP_ENNE_HAALETUST = 1
ETAPP_HAALETUS = 2
ETAPP_TYHISTUS = 3
ETAPP_LUGEMINE = 4

G_STATES = {
        ETAPP_ENNE_HAALETUST: 'Seadistusperiood',
        ETAPP_HAALETUS: 'Hääletusperiood',
        ETAPP_TYHISTUS: 'Tühistusperiood',
        ETAPP_LUGEMINE: 'Lugemisperiood'}

HES_STATES = {
    ETAPP_ENNE_HAALETUST: ETAPP_HAALETUS,
    ETAPP_HAALETUS: ETAPP_LUGEMINE}

HTS_STATES = {
    ETAPP_ENNE_HAALETUST: ETAPP_HAALETUS,
    ETAPP_HAALETUS: ETAPP_TYHISTUS,
    ETAPP_TYHISTUS: ETAPP_LUGEMINE}

HLR_STATES = {
    ETAPP_ENNE_HAALETUST: ETAPP_LUGEMINE}


def create_registry():
    evreg.create_registry(evcommon.EVREG_CONFIG)


class ElectionState:

    __metaclass__ = singleton.SingletonType

    __reg = None

    def __init__(self):
        self.__reg = evreg.Registry(root=evcommon.EVREG_CONFIG)

    def _set(self, state):
        self.__reg.ensure_key(['common'])
        self.__reg.create_integer_value(['common'], 'state', state)

    def init(self):
        self._set(ETAPP_ENNE_HAALETUST)

    def has(self):
        return self.__reg.check(['common', 'state'])

    def get(self):
        if not self.has():
            self.init()
        return self.__reg.read_integer_value(['common'], 'state').value

    def str(self):
        _state = self.get()
        return G_STATES[_state]

    def election_on(self):
        return self.get() == ETAPP_HAALETUS

    def election_off_msg(self):
        if self.get() == ETAPP_ENNE_HAALETUST:
            return protocol.plain_error_election_off_before()
        return protocol.plain_error_election_off_after()

    def next(self):

        _oldstate = self.get()

        if _oldstate == ETAPP_LUGEMINE:
            return

        if Election().is_hes():
            _newstate = HES_STATES[_oldstate]
        elif Election().is_hts():
            _newstate = HTS_STATES[_oldstate]
        elif Election().is_hlr():
            _newstate = HLR_STATES[_oldstate]
        else:
            raise Exception('Puuduv serveritüüp')

        self._set(_newstate)

    def can_apply_changes(self):
        _state = self.get()
        return _state in [ETAPP_ENNE_HAALETUST, ETAPP_HAALETUS]

    def can_replace_candidates(self):
        _state = self.get()
        return _state in [ETAPP_ENNE_HAALETUST]

    def can_load_conf(self):
        _state = self.get()
        return _state in [ETAPP_ENNE_HAALETUST]


class Election:

    __metaclass__ = singleton.SingletonType

    reg = None

    def __init__(self):
        self.reg = evreg.Registry(root=evcommon.EVREG_CONFIG)

    def get_voters_files_sha256(self):
        if self.reg.check(['common', 'voters_files_sha256']):
            return \
                self.reg.read_string_value(\
                    ['common'], 'voters_files_sha256').value
        return ''

    def init_keys(self):
        self.reg.ensure_key(['common'])

    def is_hes(self):
        return self.reg.check(['common', 'hes'])

    def is_hts(self):
        return self.reg.check(['common', 'hts'])

    def is_hlr(self):
        return self.reg.check(['common', 'hlr'])

    def set_server_str(self, srvstr):
        if srvstr in evcommon.APPTYPES:
            self.reg.ensure_key(['common', srvstr])
        else:
            raise Exception('Vigane serveri tüüp')

    def get_server_str(self):
        if self.is_hes():
            return 'hes'
        elif self.is_hts():
            return 'hts'
        elif self.is_hlr():
            return 'hlr'
        else:
            raise Exception('Vigane serveri tüüp')

    def copy_voters_file(self, elid, server, voters_file):

        voters_files = 'voters_files'
        _r = self.get_sub_reg(elid, [server])
        _r.ensure_key([voters_files])

        time_str = time.strftime("%Y%m%d%H%M%S")
        copy_voters_file = _r.path([voters_files, time_str + '_' + \
            os.path.basename(voters_file)])
        shutil.copyfile(voters_file, copy_voters_file)

        voters_file_sha256 = ksum.compute(voters_file)
        voters_file_hashes = ['common', 'voters_file_hashes']
        self.reg.ensure_key(voters_file_hashes)
        self.reg.create_string_value(voters_file_hashes, voters_file_sha256, '')

        voters_files_sha256 = \
            ksum.compute_voters_files_sha256(self.reg.path(voters_file_hashes))
        self.reg.create_string_value(['common'], \
            'voters_files_sha256', voters_files_sha256)

    def get_bdoc_conf(self):
        return self.reg.path([evcommon.BDOC])

    def get_bdoc_ca(self):
        return self.reg.path([evcommon.BDOC, 'ca'])

    def get_hsm_token_name(self):
        return self.reg.read_string_value(['common', 'hsm'], 'tokenname').value

    def get_hsm_priv_key(self):
        return \
            self.reg.read_string_value(['common', 'hsm'], 'privkeylabel').value

    def get_pkcs11_path(self):
        return self.reg.read_string_value(['common', 'hsm'], 'pkcs11').value

    def set_hsm_token_name(self, val):
        self.reg.ensure_key(['common', 'hsm'])
        self.reg.create_string_value(['common', 'hsm'], 'tokenname', val)

    def set_hsm_priv_key(self, val):
        self.reg.ensure_key(['common', 'hsm'])
        self.reg.create_string_value(['common', 'hsm'], 'privkeylabel', val)

    def set_pkcs11_path(self, val):
        self.reg.ensure_key(['common', 'hsm'])
        self.reg.create_string_value(['common', 'hsm'], 'pkcs11', val)

    def get_path(self, afile):
        return self.reg.path(['common', afile])

    def get_hts_ip(self):
        return self.reg.read_ipaddr_value(['common'], 'htsip').value

    def set_hts_ip(self, ip):
        self.reg.ensure_key(['common'])
        self.reg.create_ipaddr_value(['common'], 'htsip', ip)

    def get_hts_path(self):
        return self.reg.read_string_value(['common'], 'htspath').value.rstrip()

    def set_hts_path(self, path):
        self.reg.ensure_key(['common'])
        self.reg.create_string_value(['common'], 'htspath', path)

    def get_hts_verify_path(self):
        return self.reg.read_string_value(['common'], 'htsverifypath').value.rstrip()

    def set_hts_verify_path(self, path):
        self.reg.ensure_key(['common'])
        self.reg.create_string_value(['common'], 'htsverifypath', path)

    def get_verification_time(self):
        return self.reg.read_integer_value(['common'], 'verification_time').value

    def set_verification_time(self, time):
        self.reg.ensure_key(['common'])
        self.reg.create_integer_value(['common'], 'verification_time', time)

    def get_verification_count(self):
        return self.reg.read_integer_value(['common'], 'verification_count').value

    def set_verification_count(self, count):
        self.reg.ensure_key(['common'])
        self.reg.create_integer_value(['common'], 'verification_count', count)

    def get_questions_obj(self, root):
        qlist = self.get_questions()
        ret = []
        for elem in qlist:
            quest = question.Question(elem, root, self.get_sub_reg(elem))
            ret.append(quest)
        return ret

    def get_questions(self):
        if self.reg.check(['questions']):
            return self.reg.list_keys(['questions'])
        return []

    def count_questions(self):
        return len(self.get_questions())

    def has_id(self, elid):
        return self.reg.check(['questions', elid])

    def get_sub_reg(self, elid, sub=['']): # pylint: disable=W0102
        if self.has_id(elid):
            return \
                evreg.Registry(root=self.reg.path(['questions', elid] + sub))
        raise \
            Exception('Ei ole lubatud valimiste identifikaator \"%s\"' % elid)

    def get_root_reg(self):
        return self.reg

    def delete_question(self, elid):
        self.reg.delete_key(['questions', elid])
        if self.count_questions() == 0:
            self.init_conf_done(False)

    def new_question(self, el_id, el_type, el_desc):
        if formatutil.is_valimiste_identifikaator(el_id):
            key = ['questions', el_id, 'common']
            self.reg.ensure_key(key)
            self.reg.create_string_value(key, ELECTION_ID, el_id)
            quest = question.Question(el_id, None, \
                evreg.Registry(root=self.reg.path(['questions', el_id])))
            g_common_keys = ['common/rights']
            quest.create_keys(g_common_keys)
            quest.set_type(int(el_type))
            quest.set_descr(el_desc)
            return quest
        else:
            raise Exception('Vigase formaadiga valimiste identifikaator')

    def restore_init_status(self):
        if self.is_hes():
            self.reg.truncate_value(['common'], evcommon.APPLICATION_LOG_FILE)
            self.reg.truncate_value(['common'], evcommon.ERROR_LOG_FILE)
            self.reg.truncate_value(['common'], evcommon.DEBUG_LOG_FILE)
            self.reg.ensure_no_key(['common', 'nonewvoters'])
        if self.is_hts():
            self.reg.truncate_value(['common'], evcommon.APPLICATION_LOG_FILE)
            self.reg.truncate_value(['common'], evcommon.ERROR_LOG_FILE)
            self.reg.truncate_value(['common'], evcommon.OCSP_LOG_FILE)
            self.reg.truncate_value(['common'], evcommon.STATUSREPORT_FILE)
            self.reg.delete_sub_keys(['verification'])
            for i in self.get_questions():
                quest = question.Question(i, 'hts', self.get_sub_reg(i))
                quest.truncate_log_file('1')
                quest.truncate_log_file('2')
                quest.truncate_log_file('3')
                quest.create_revlog()
                self.reg.delete_sub_keys(['questions', i, 'hts', 'votes'])
                self.reg.delete_sub_keys(['questions', i, 'hts', 'output'])
        if self.is_hlr():
            pass

    def get_election_type_str(self, el_id):
        return evcommon.G_TYPES[self.get_sub_reg(el_id)\
                .read_integer_value(['common'], 'type').value]

    def _do_flag(self, flag, do_set):
        if do_set:
            self.reg.ensure_key(flag)
        else:
            self.reg.ensure_no_key(flag)

    def is_config_bdoc_done(self):
        return self.reg.check(['common', evcommon.CONFIG_BDOC_DONE])

    def config_bdoc_done(self, done=True):
        self._do_flag(['common', evcommon.CONFIG_BDOC_DONE], done)

    def is_config_hth_done(self):
        return self.reg.check(['common', evcommon.CONFIG_HTH_DONE])

    def config_hth_done(self, done=True):
        self._do_flag(['common', evcommon.CONFIG_HTH_DONE], done)

    def is_init_conf_done(self):
        return self.reg.check(['common', evcommon.INIT_CONF_DONE])

    def init_conf_done(self, done=True):
        self._do_flag(['common', evcommon.INIT_CONF_DONE], done)

    def is_config_hsm_done(self):
        return self.reg.check(['common', evcommon.CONFIG_HSM_DONE])

    def config_hsm_done(self, done=True):
        self._do_flag(['common', evcommon.CONFIG_HSM_DONE], done)

    def is_config_hlr_input_done(self):
        for elid in self.get_questions():
            if not self.is_config_hlr_input_elid_done(elid):
                return False
        return True

    def is_config_hlr_input_elid_done(self, elid):
        return \
            self.reg.check(['questions', elid, 'common', \
                evcommon.CONFIG_HLR_INPUT_DONE])

    def config_hlr_input_elid_done(self, elid, done=True):
        self._do_flag(['questions', elid, 'common', \
            evcommon.CONFIG_HLR_INPUT_DONE], done)

    def is_config_server_done(self):
        for elid in self.get_questions():
            if not self.is_config_server_elid_done(elid):
                return False
        return True

    def is_config_server_elid_done(self, elid):
        return self.reg.check(['questions', elid, 'common', \
            evcommon.CONFIG_SERVER_DONE])

    def config_server_elid_done(self, elid, done=True):
        self._do_flag(['questions', elid, 'common', \
            evcommon.CONFIG_SERVER_DONE], done)

    def is_voters_list_disabled(self):
        return self.reg.check(['common', evcommon.VOTERS_LIST_IS_DISABLED])

    def is_hes_configured(self):
        return self.is_config_hth_done() and self.is_config_bdoc_done() and \
            self.is_config_server_done() and self.is_init_conf_done() and \
            self.is_config_mid_done()

    def is_hts_configured(self):
        return self.is_config_bdoc_done() and \
            self.is_config_server_done() and self.is_init_conf_done() and \
            self.is_config_verification_done()

    def is_hlr_configured(self):
        return self.is_config_bdoc_done() and \
            self.is_config_server_done() and self.is_config_hsm_done() and \
            self.is_init_conf_done()

    def toggle_check_voters_list(self, enable):
        self._do_flag(['common', evcommon.VOTERS_LIST_IS_DISABLED], \
            (not enable))

    def get_mid_url(self):
        return self.reg.read_string_value(['common', 'mid'], 'url').value

    def get_mid_name(self):
        return self.reg.read_string_value(['common', 'mid'], 'name').value

    def get_mid_messages(self):
        a_msg = self.reg.read_string_value(['common', 'mid'], 'auth_msg').value
        s_msg = self.reg.read_string_value(['common', 'mid'], 'sign_msg').value
        return a_msg, s_msg

    def set_mid_conf(self, url, name, auth_msg, sign_msg):
        try:
            self.reg.ensure_key(['common', 'mid'])
            self.reg.create_string_value(['common', 'mid'], 'url', url)
            self.reg.create_string_value(['common', 'mid'], 'name', name)
            self.reg.create_string_value(\
                                    ['common', 'mid'], 'auth_msg', auth_msg)
            self.reg.create_string_value(\
                                    ['common', 'mid'], 'sign_msg', sign_msg)
            self.config_mid_done()
        except:
            self.config_mid_done(False)
            raise

    def config_mid_done(self, done=True):
        self._do_flag(['common', evcommon.CONFIG_MID_DONE], done)

    def is_config_mid_done(self):
        return self.reg.check(['common', evcommon.CONFIG_MID_DONE])

    def can_vote(self, ik):
        questions = self.get_questions_obj('hes')
        for quest in questions:
            if quest.can_vote(ik):
                return True
        return False

    def refuse_new_voters(self):
        self.reg.ensure_key(['common', 'nonewvoters'])

    def restore_new_voters(self):
        self.reg.ensure_no_key(['common', 'nonewvoters'])

    def allow_new_voters(self):
        return not self.reg.check(['common', 'nonewvoters'])

    def is_config_verification_done(self):
        try:
            self.get_verification_time()
            self.get_verification_count()
            return True
        except (IOError, LookupError):
            return False


if __name__ == '__main__':
    pass


# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = evcommon
# log
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import sys

if sys.version_info[0] != 2 or sys.version_info[1] != 7:
    raise Exception(
        'Vajalik on pythoni versioon 2.7 (praegune versioon: %s.%s)' % (
            sys.version_info[0], sys.version_info[1]))


def testrun():
    return (None <> os.environ.get('IVOTE_TEST_RUN'))

VERSION = "1"

# Serverite tüübid
APPTYPE_HES = "hes"
APPTYPE_HTS = "hts"
APPTYPE_HLR = "hlr"
APPTYPES = [APPTYPE_HES, APPTYPE_HTS, APPTYPE_HLR]

# HTTP protokolli parameetrid

HTTP_POST = "POST"
# Kliendi autentimissertifikaat sessioonis
HTTP_CERT = 'SSL_CLIENT_CERT'
# Info kliendi platvormi kohta sessioonis
HTTP_AGENT = 'HTTP_USER_AGENT'

# hääletamine
POST_EVOTE = "vote"
# isikukoodi järgi hääletamise fakti kontroll
POST_PERSONAL_CODE = "ik"
# valijate nimekirjade failide kooskõlalisuse räsi
POST_VOTERS_FILES_SHA256 = "hash"
# sessiooniidentifikaator
POST_SESS_ID = "session"

# Mobiil-ID telefoni number
POST_PHONENO = "phone"

# Mobiil-ID sessioon
POST_MID_POLL = "poll"

# Verification protocol
POST_VERIFY_VOTE = "vote"

# VR <-> HES protokolli tagastusväärtused
# Samad koodid ka talletusprotokollis HES <-> HTS

# Positiivne vastuse lipp
EVOTE_OK = '0'
# Vea lipp
EVOTE_ERROR = '1'
# Kasutaja serdi vea lipp
EVOTE_CERT_ERROR = '2'
# Kasutaja pole valijate nimekirjas
EVOTE_VOTER_ERROR = '3'
# Mobiil-ID ei ole veel vastust andnud
EVOTE_POLL = '4'
# Mobiil-ID komponendi viga
EVOTE_MID_ERROR = '5'


# HES <-> HTS vaheliste protokollide väärtused

# EVOTE kooskõlalisuse protokolli tagastusväärtused
EVOTE_CONSISTENCY_NO = '3'
EVOTE_CONSISTENCY_YES = '2'
EVOTE_CONSISTENCY_ERROR = '1'

# EVOTE korduvhääletuse protokolli tagastusväärtused
EVOTE_REPEAT_NO = '3'
EVOTE_REPEAT_YES = '4'
EVOTE_REPEAT_NOT_CONSISTENT = '2'
EVOTE_REPEAT_ERROR = '1'

# Verification protocol return values
VERIFY_OK = '0'
VERIFY_ERROR = '1'

COMMON = "common"
BDOC = "common/bdoc"
MIDSPOOL = "midspool"

TYPE_RH = 0
TYPE_KOV = 1
TYPE_RK = 2
TYPE_EUROPARLAMENT = 3

G_TYPES = {
    TYPE_RH: 'Rahvahääletus',
    TYPE_KOV: 'Kohalikud omavalitsused',
    TYPE_RK: 'Riigikogu',
    TYPE_EUROPARLAMENT: 'Europarlament'}

# Logifailid
LOG1_FILE = "log1"
LOG2_FILE = "log2"
LOG3_FILE = "log3"
LOG4_FILE = "log4"
LOG5_FILE = "log5"
APPLICATION_LOG_FILE = "ivoting_app_log"
ERROR_LOG_FILE = "ivoting_err_log"
DEBUG_LOG_FILE = "ivoting_debug_log"
OCSP_LOG_FILE = "ivoting_ocsp_log"
VOTER_LIST_LOG_FILE = "valijate_nimekirjade_vigade_logi"
REVLOG_FILE = "tuhistamiste_ennistamiste_logi"
ELECTIONRESULT_ZIP_FILE = "haaletamistulemus.zip"
ELECTIONRESULT_FILE = "haaletamistulemus"
ELECTIONRESULT_SHA256_FILE = "haaletamistulemus.sha256"
ELECTIONRESULT_STAT_FILE = "haaletamistulemusjaosk"
ELECTIONRESULT_STAT_SHA256_FILE = "haaletamistulemusjaosk.sha256"
ELECTIONS_RESULT_FILE = "loendamisele_minevate_haalte_nimekiri"
ELECTIONS_RESULT_SHA256_FILE = "loendamisele_minevate_haalte_nimekiri.sha256"
ELECTORSLIST_FILE = "haaletanute_nimekiri"
ELECTORSLIST_SHA256_FILE = "haaletanute_nimekiri.sha256"
ELECTORSLIST_FILE_TMP = "haaletanute_nimekiri.tmp"
ELECTORSLIST_FILE_PDF = "haaletanute_nimekiri.pdf"
STATUSREPORT_FILE = "hts_vaheauditi_aruanne"
REVREPORT_FILE = "tuhistamiste_ennistamiste_aruanne"
REVREPORT_SHA256_FILE = "tuhistamiste_ennistamiste_aruanne.sha256"

LOG1_STR = "Vastuvõetud häälte logi (Log1)"
LOG2_STR = "Tühistatud häälte logi (Log2)"
LOG3_STR = "Lugemisele minevate häälte logi (Log3)"
LOG4_STR = "Kehtetute häälte logi (Log4)"
LOG5_STR = "Arvestatud häälte logi (Log5)"
APPLICATION_LOG_STR = "Rakenduse logi"
ERROR_LOG_STR = "Vigade logi"
DEBUG_LOG_STR = "Turvalogi"
OCSP_LOG_STR = "OCSP saadavuse logi"
VOTER_LIST_LOG_STR = "Valijate nimekirjade vigade logi"
REVLOG_STR = "Tühistamiste ja ennistamiste aruanne"
ELECTIONRESULT_ZIP_STR = "Hääletamistulemus (allkirjadega)"
ELECTIONRESULT_STR = "Hääletamistulemus (ringkondade kaupa)"
ELECTIONRESULT_STAT_STR = "Hääletamistulemus (jaoskondade kaupa)"
ELECTIONS_RESULT_STR = "Loendamisele minevate häälte nimekiri"
ELECTORSLIST_STR = "E-hääletanute nimekiri"
ELECTORSLIST_PDF_STR = "E-hääletanute nimekiri (PDF)"
STATUSREPORT_STR = "Vaheauditi aruanne"
REVREPORT_STR = "Tühistus-/ennistusavalduse impordi aruanne"

# konfigureerimist träkkivad lipud
INIT_CONF_DONE = "init_conf_done"
CONFIG_BDOC_DONE = "config_bdoc_done"
CONFIG_HTH_DONE = "config_hth_done"
CONFIG_MID_DONE = "config_mid_done"
CONFIG_SERVER_DONE = "config_server_done"
CONFIG_HSM_DONE = "config_hsm_done"
CONFIG_HLR_INPUT_DONE = "config_hlr_input_done"

VOTERS_LIST_IS_DISABLED = "voters_list_is_disabled"

# registri juurikas
import os

try:
    EVREG_CONFIG = os.environ['EVREG_CONFIG']
except KeyError:
    EVREG_CONFIG = '/var/evote/registry'

def burn_buff():
    return os.path.join(os.environ["HOME"], "burn_buff")

def checkfile(filename):
    if not os.access(filename, os.F_OK):
        sys.stderr.write('Faili ' + filename + ' ei eksisteeri\n')
        sys.exit(1)
    if not os.access(filename, os.R_OK):
        sys.stderr.write('Faili ' + filename + ' ei saa lugeda\n')
        sys.exit(1)


def touch_file(path):
    touch_f = file(path, 'w')
    touch_f.close()

def file_cmp(a, b, prefix): # pylint: disable=C0103
    if a == b:
        return 0

    if a == prefix:
        return -1

    if b == prefix:
        return 1

    ai = int(a.split('.')[2])
    bi = int(b.split('.')[2])
    return ai - bi

def access_cmp(a, b): # pylint: disable=C0103
    return file_cmp(a, b, 'access.log')

def error_cmp(a, b): # pylint: disable=C0103
    return file_cmp(a, b, 'error.log')

def get_apache_log_files():
    accesslog = []
    errorlog = []
    for filename in os.listdir('/var/log/apache2'):
        if filename.startswith('access.log'):
            accesslog.append(filename)
        if filename.startswith('error.log'):
            errorlog.append(filename)

    accesslog.sort(access_cmp)
    errorlog.sort(error_cmp)
    return accesslog, errorlog


# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = evlog
# log
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import os
import time
import fcntl
from operator import contains
import exception_msg
import ksum
import syslog
import singleton
import sessionid
import evcommon
import urllib

def log(msg):
    AppLog().log(msg)

def log_error(msg):
    AppLog().log_error(msg)

def log_exception():
    AppLog().log_exception()

def log_integrity(msg):
    AppLog().log_integrity(msg)

class RevLogFormat:

    def __init__(self):
        pass

    def keep(self):
        return True

    def message(self, args):

        newtime = time.localtime()
        if contains(args, 'testtime'):
            newtime = time.strptime(
                    args['testtime'],
                    "%Y%m%d%H%M%S")

        line = []
        line.append(args['tegevus'])
        line.append(args['isikukood'])
        line.append(args['nimi'])
        line.append(args['timestamp'])
        line.append(time.strftime("%Y%m%d%H%M%S", newtime))
        line.append(args['operaator'])
        line.append(args['pohjus'])
        logstring = "\t".join(line)
        return logstring


class EvLogFormat:

    def __init__(self):
        pass

    def keep(self):
        return True

    def logstring(self, **args):
        return self.message(args)

    def message(self, args):
        line = []
        # Üldvorming
        # aeg 14*14DIGIT
        if contains(args, 'timestamp'):
            line = [args['timestamp']]
        else:
            line = [time.strftime("%Y%m%d%H%M%S")]
        # Hääle räsi 28*28BASE64-CHAR
        if not contains(args, 'haal_rasi'):
            if contains(args, 'haal'):
                args['haal_rasi'] = ksum.votehash(args['haal'])
        line.append(args['haal_rasi'])

        # omavalitsuse-number 1*10DIGIT
        line.append(str(args['ringkond_omavalitsus']))
        # suhteline-ringkonna-number 1*10DIGIT
        line.append(str(args['ringkond']))
        if contains(args, 'jaoskond_omavalitsus'):
            # omavalitsuse-number 1*10DIGIT
            line.append(str(args['jaoskond_omavalitsus']))
        if contains(args, 'jaoskond'):
            # suhteline-valimisjaoskonna-number 1*10DIGIT
            line.append(str(args['jaoskond']))

        if args['tyyp'] in [0, 1, 2, 3]:
            #*1valija-andmed =
            #isikukood 11*11DIGIT
            line.append(str(args['isikukood']))
        if args['tyyp'] == 2:
            # pohjus 1*100UTF-8-CHAR
            line.append(args['pohjus'])
        if args['tyyp'] == 0:
            line.append(args['nimi'])
            line.append(args['reanumber'])
        logstring = "\t".join(line)

        return logstring


    # Currently we only check for personal code
    # this can be extended to check anything
    def matches(self, data, line, count):
        return (line.split("\t")[6][0:11] == data)


class AppLogFormat:

    def __init__(self, app = None):
        self.__app = app
        self.__elid = ''
        self.__pers_id = ''
        self.__sess = os.getpid()
        self.__psess = os.getppid()

    def set_elid(self, elid):
        self.__elid = elid

    def set_app(self, app):
        self.__app = app

    def set_person(self, person):
        self.__pers_id = person

    def keep(self):
        return False

    def message(self, args):
        logstring = "%s (%s:%d:%d:%s:%s:%s:%s): %s" % (
            time.strftime("%Y-%m-%d %H:%M:%S"),
            self.__app,
            self.__sess,
            self.__psess,
            sessionid.voting(),
            sessionid.apache(),
            self.__elid,
            self.__pers_id,
            args['message'])
        return logstring

class LogFile:

    __filename = None

    def __init__(self, filename):
        self.__filename = filename

    def write(self, message):
        if (self.__filename):
            _af = file(self.__filename, 'a')
            try:
                fcntl.lockf(_af, fcntl.LOCK_EX)
                _af.write(message)
                _af.flush()
            finally:
                _af.close()

    def line_count(self): # pylint: disable=R0201
        line_count = 0
        try:
            os.stat(self.__filename)
        except OSError:
            return line_count

        try:
            _rf = open(self.__filename, 'r')
            for _ in _rf:
                line_count += 1
            return line_count
        finally:
            if (_rf):
                _rf.close()


    def contains(self, data, form):

        res = False
        if not os.access(self.__filename, os.F_OK):
            return res

        _f = None
        try:
            _f = file(self.__filename, 'r')
            fcntl.lockf(_f, fcntl.LOCK_SH)
            ii = 0
            for line in _f:
                if form.matches(data, line, ii):
                    res = True
                    break
                ii = ii + 1

        finally:
            if _f:
                _f.close()

        return res



class Logger(object):

    def __init__(self, ident=None):
        self.__last_message = ''
        self._log = None
        self._form = None
        self.__ident = ident
        self.__fac = syslog.LOG_LOCAL0
        syslog.openlog(facility=self.__fac)

    def set_format(self, form):
        self._form = form

    def set_logs(self, path):
        self._log = LogFile(path)

    def last_message(self):
        return self.__last_message

    def _log_syslog(self, prio):
        if self.__ident:
            syslog.openlog(ident=self.__ident, facility=self.__fac)
            syslog.syslog(prio, self.__last_message)
            syslog.closelog()
        else:
            syslog.syslog(prio | self.__fac, self.__last_message)

    def _do_log(self, level, **args):
        self.__last_message = self._form.message(args)
        if not self._form.keep():
            self.__last_message = urllib.quote(self.__last_message, \
                    ' !"#&\'()*+,-./:;<=>?@\[\]_|\t]äöüõÄÖÜÕ')

        self.__last_message += "\n"
        self._log.write(self.__last_message)
        self._log_syslog(level)

    def log_info(self, **args):
        self._do_log(syslog.LOG_INFO, **args)

    def log_err(self, **args):
        self._do_log(syslog.LOG_ERR, **args)

    def log_debug(self, **args):
        self._do_log(syslog.LOG_DEBUG, **args)

    def lines_in_file(self):
        return self._log.line_count()

    def contains(self, data):
        return self._log.contains(data, self._form)



class AppLog(Logger):

    __metaclass__ = singleton.SingletonType

    def __init__(self):
        Logger.__init__(self)
        self._form = AppLogFormat()
        self.__log_i = LogFile(
                os.path.join(
                    evcommon.EVREG_CONFIG,
                    'common',
                    evcommon.APPLICATION_LOG_FILE))

        self.__log_e = LogFile(
                os.path.join(
                    evcommon.EVREG_CONFIG,
                    'common',
                    evcommon.ERROR_LOG_FILE))

        self.__log_d = LogFile(
                os.path.join(
                    evcommon.EVREG_CONFIG,
                    'common',
                    evcommon.DEBUG_LOG_FILE))

    def set_app(self, app, elid = None):
        #remove elid
        self._form.set_app(app)
        self._form.set_elid(elid)

    def set_person(self, person):
        self._form.set_person(person)

    def log(self, msg):
        #add elid
        self._log = self.__log_i
        self.log_info(message=msg)

    def log_error(self, msg):
        self._log = self.__log_e
        self.log_err(message=msg)

    def log_integrity(self, warns):
        msg = "FAILED: " + "; ".join(warns) if warns else "OK"
        self._log = self.__log_d
        self.log_debug(message=msg)

    def log_exception(self):
        self.log_error(exception_msg.trace())

# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = evlogdata
# log
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import os
import M2Crypto
import hashlib
import urllib
import exception_msg

def get_apache_env(key):
    if os.environ.has_key(key):
        return os.environ[key]
    return ''

def get_remote_ip():
    return get_apache_env('REMOTE_ADDR')

def get_user_agent():
    return urllib.quote_plus(get_apache_env('HTTP_USER_AGENT'))[:100]


def get_vote(name, data):
    return "VOTE=%s, SHA256=%s" % \
            (name, hashlib.sha256(data).digest().encode('hex'))


def get_cert_data_log(cert_pem, prefix = None, addlines = False):

    retval = ''

    isik = 'N/A'
    serial = 'N/A'
    certhash = 'N/A'
    org = 'N/A'
    exc = None

    my_cert_pem = cert_pem
    if addlines:
        bline = '-----BEGIN CERTIFICATE-----\n'
        eline = '\n-----END CERTIFICATE-----'
        my_cert_pem = bline + my_cert_pem + eline

    try:
        cert = M2Crypto.X509.load_cert_string(my_cert_pem)
        isik = cert.get_subject().serialNumber
        serial = cert.get_serial_number()
        certhash = hashlib.sha256(cert.as_der()).digest().encode('hex')
        org = cert.get_subject().O
    except:
        exc = exception_msg.trace()

    retval = "PC=%s, SERIAL=%s, HASH=%s, ORG=%s" % \
            (isik, serial, certhash, org)

    if exc:
        retval = retval + ", error occured"

    if prefix:
        retval = prefix + " " + retval

    return retval, exc

# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = evmessage
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import sys
import shutil
import ConfigParser
import evreg
import evcommon

import singleton

MSG_FILE = ['common', 'teated']

# Selle klassi ainus mõte on, et EV_ERRORS. abil saab lähtekoodis markeerida
# veakoode - siis on vajadusel mugav greppida neid.
class EvErrors:
    def __getattr__(self, attr):
        return attr

EV_ERRORS = EvErrors()

class EvMessage:
    """Message strings handling class, Singleton pattern
    """

    __metaclass__ = singleton.SingletonType

    def __init__(self):
        # Siin hoitakse mäppuvana koodid ja stringid.
        self.msg_strings = {}
        evreg.create_registry(evcommon.EVREG_CONFIG)
        self.reg = evreg.Registry(root=evcommon.EVREG_CONFIG)
        try:
            self._load_strings()
        except:
            pass

    def _load_strings(self):
        if self.reg.check(MSG_FILE):
            fn = self.reg.path(MSG_FILE)
            config = ConfigParser.ConfigParser()
            config.readfp(open(fn, 'r'))
            for i in config.sections():
                options = config.options(i)
                for j in options:
                    self.msg_strings[j] = config.get(i, j)

    def import_str_file(self, file_name):
        try:
            config = ConfigParser.ConfigParser()
            config.readfp(open(file_name, 'r'))
            shutil.copyfile(file_name, self.reg.path(MSG_FILE))
            self._load_strings()
        except: # pylint: disable=W0702
            exctype, value = sys.exc_info()[:2]
            print 'Teateid ei õnnestunud laadida: %s: \"%s\"' % \
                (exctype, value)
            return
        print 'Teated õnnestus laadida.'

    def get_str(self, key, default_msg):
        k = key.lower()
        if k in self.msg_strings:
            return self.msg_strings[k]
        return default_msg

    def print_all_strings(self):
        pairs = zip(self.msg_strings.keys(), self.msg_strings.values())
        print "USER STRINGS:\n"
        for j in pairs:
            print j

if __name__ == '__main__':
    EvMessage().print_all_strings()

# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = evreg
# Registry
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

"""
Module to implement filesystem based registry, where registry keys are
directories and registry values (with types) are stored in files.

Supported value types: string (UTF8), integer (int32) and IP
Address.

@var    STRING: string type
@var    STRING_STR: string prefix to identify string types in registry value
            files
@var    INTEGER: integer type
@var    INTEGER_STR: string prefix to identify integer types in registry value
            files
@var    IP_ADDR: IP address type
@var    IP_ADDR_STR: prefix to identify IP address types in registry value
            files
"""

import os
import fcntl

STRING = 1
INTEGER = 2
IP_ADDR = 3

STRING_STR = 'string:'
INTEGER_STR = 'integer:'
IP_ADDR_STR = 'ip_addr:'


def create_registry(path_to_registry):
    try:
        os.stat(path_to_registry)
    except OSError:
        os.makedirs(path_to_registry)


class Registry:
    """Registry handling class
    """

    def __init__(self, **args):
        """
        @type       root: string
        @keyword    root: root directory of registry
        """
        self.root = args['root']
        os.stat(self.root)

    def _dirname(self, key):
        return os.path.join(self.root, *key)

    def path(self, key=['']): # pylint: disable=W0102
        return self._dirname(key)

    def reset_key(self, key):
        self.ensure_no_key(key)
        self.create_key(key)

    def ensure_key(self, key):
        """Ensure there's key 'key' in the registry
        @type   key: string
        @param  key: key name
        Returns True if the key was created, False otherwise
        """
        if not self.check(key):
            self.create_key(key)
            return True
        return False

    def ensure_no_key(self, key):
        """Ensure there's no key 'key' in the registry
        @type   key: string
        @param  key: key name
        Returns True if the key existed, False otherwise
        """
        if self.check(key):
            self.delete_key(key)
            return True
        return False

    def create_key(self, key):
        """Create registry key

        @type   key: string
        @param  key: key name
        """
        os.makedirs(self._dirname(key))

    def delete_key(self, key=['']): # pylint: disable=W0102
        """Delete registry key

        @type   key: string
        @param  key: key name
        """

        self.delete_sub_keys(key)
        os.rmdir(self._dirname(key))

    def delete_sub_keys(self, key):
        """
        Delete subkeys of a registry key
        @type   key: string
        @param  key: key name
        """

        if not self.check(key):
            return

        dname = self._dirname(key)

        for name in os.listdir(dname):
            path = os.path.join(dname, name)
            if os.path.isdir(path):
                self.delete_key(key + [name])
            else:
                os.remove(path)

    def truncate_value(self, key, name):
        RegistryValue(self.root, key, name).truncate()

    def list_keys(self, sub=['']): # pylint: disable=W0102
        """List subkeys
        @type   sub: string
        @param  sub: subkey to list
        @return: list of subkeys
        """
        return os.listdir(self._dirname(sub))

    def check(self, key):
        """Check registry key

        @type   key: string
        @param  key: key name

        @return: False when key does not exist, True otherwise
        """
        try:
            os.stat(self._dirname(key))
        except OSError:
            return False
        return True

    def create_value(self, key, name, value, ttype=STRING):
        """Create registry value

        @type   key: string
        @param  key: key name
        @type   name: string
        @param  name: value name
        @type   value: string or integer
        @param  value: registry value
        @type   type: integer
        @param  type: value type

        @return: RegistryValue object
        """
        val = RegistryValue(self.root, key, name)
        val.create(value, ttype)
        return val

    def create_string_value(self, key, name, value):
        """L{CreateValue} wrapper for String values
        """
        return self.create_value(key, name, value, STRING)

    def create_integer_value(self, key, name, value):
        """L{CreateValue} wrapper for Integer values
        """
        return self.create_value(key, name, value, INTEGER)

    def create_ipaddr_value(self, key, name, value):
        """L{CreateValue} wrapper for IP addr values
        """
        return self.create_value(key, name, value, IP_ADDR)

    def read_value(self, key, name, ttype=None):
        """Read registry value

        @type   key: string
        @param  key: key name
        @type   name: string
        @param  name: value name
        @type   ttype: integer
        @param  ttype: value type

        @return: RegistryValue object
        """
        val = RegistryValue(self.root, key, name)
        val.read(ttype)
        return val

    def read_string_value(self, key, name):
        """L{ReadValue} wrapper for String values
        """
        return self.read_value(key, name, STRING)

    def read_integer_value(self, key, name):
        """L{ReadValue} wrapper for Integer values
        """
        return self.read_value(key, name, INTEGER)

    def read_ipaddr_value(self, key, name):
        """L{ReadValue} wrapper for IP Address values
        """
        return self.read_value(key, name, IP_ADDR)

    def delete_value(self, key, name):
        return RegistryValue(self.root, key, name).delete()


class RegistryValue:
    """Class to represent registry value

    @type   have_value: boolean
    @ivar   have_value: True, when RegistryValue have value assigned
    @type   root: string
    @ivar   root: root directory of regsitry
    @type   key: string
    @ivar   key: regsitry key name
    @type   name: string
    @ivar   name: value name
    @type   ttype: integer
    @ivar   ttype: value type
    @type   value: string or integer
    @ivar   value: value
    """

    def __init__(self, root, key, name):
        """

        @type   root: string
        @param  root: root directory of registry
        @type   key: string
        @param  key: registry key name
        @type   name: string
        @param  name: registry value name
        """
        self.root = root
        self.key = key
        self.name = name
        self.ttype = None
        self.value = None
        self.have_value = False

    def __repr__(self):
        if not self.have_value:
            raise LookupError("No value")
        return self.value

    def _filename(self):
        fp = [self.root] + self.key + [self.name]
        return os.path.join(*fp)

    def check(self):
        try:
            os.stat(self._filename())
        except OSError:
            return False
        return True

    def create(self, value, ttype):
        """Creates new registry value

        @type   value: string or integer
        @param  value: registry value
        @type   type: integer
        @param  type: value type
        """

        typestr = ''

        if ttype == STRING:
            typestr = STRING_STR
        elif ttype == INTEGER:
            typestr = INTEGER_STR
        elif ttype == IP_ADDR:
            typestr = IP_ADDR_STR
        else:
            raise TypeError("No valid type given")

        _wf = file(self._filename(), 'w')
        fcntl.lockf(_wf, fcntl.LOCK_EX)
        _wf.write('%s%s' % (typestr, value))
        _wf.close()
        self.ttype = ttype
        self.value = value
        self.have_value = True

    def read(self, ttype=None):
        """Read registry value

        Raises LookupError when values does not exist or TypeError when
        value type is not as requested type

        @type   type: integer
        @param  type: Value type (STRING, INTEGER, IP_ADDR) or None
                when type will automatically detected

        """
        _rf = file(self._filename(), 'r')
        fcntl.lockf(_rf, fcntl.LOCK_SH)
        val = _rf.read(-1)
        _rf.close()
        if val.find(STRING_STR, 0, len(STRING_STR)) == 0:
            if not ttype in [STRING, None]:
                raise TypeError("Type mismatch")
            self.value = val.replace(STRING_STR, '', 1)
            self.ttype = STRING

        elif val.find(INTEGER_STR, 0, len(INTEGER_STR)) == 0:
            if not ttype in [INTEGER, None]:
                raise TypeError("Type mismatch")
            self.value = int(val.replace(INTEGER_STR, '', 1))
            self.ttype = INTEGER

        elif val.find(IP_ADDR_STR, 0, len(IP_ADDR_STR)) == 0:
            if not ttype in [IP_ADDR, None]:
                raise TypeError("Type mismatch")
            self.value = str(val.replace(IP_ADDR_STR, '', 1))
            self.ttype = IP_ADDR

        else:
            raise LookupError("No value")

        self.have_value = True

    def delete(self):
        """Delete registry value
        """
        os.remove(self._filename())

    def truncate(self):
        if self.check():
            _wf = file(self._filename(), 'w')
            fcntl.lockf(_wf, fcntl.LOCK_EX)
            _wf.truncate()
            _wf.close()



# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = evstrings
# Log
# -*- coding: UTF8 -*-

# NB! This file is auto generated by script makemessages.py. Any changes
# made to it will be overwritten when the script next updates this file.

"""
Outcoming server error and message strings
"""

################################
# Verification protocol errors #
################################

# Error message shown when the query had too many or unknown parameters
BAD_PARAMETERS = \
    'Vigased sisendparameetrid'

# The verification vote ID has expired, reached it's maximum count or is otherwise invalid
INVALID_VOTE_ID = \
    'Seda hääle identifikaatorit ei saa kasutada hääle kontrollimiseks'

# Error message given for internal errors during vore verification
TECHNICAL_ERROR_VOTE_VERIFICATION = \
    'Tehniline viga hääle kontrollimisel'


# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = exception_msg
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import traceback
import sys


def trace():
    exctype, value, tb = sys.exc_info()[:3]
    msg = 'Unhandled [%s, \"%s\"]' % (exctype, value)
    errlst = traceback.extract_tb(tb)
    for el in errlst:
        msg += "[" + el[0] + "," + str(el[1]) + "," + el[2] + "]"
    del tb
    return msg

# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = formatutil
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import re

RE_ELID = re.compile('^\w{1,28}$')
RE_ISIKUKOOD = re.compile('^\d\d\d\d\d\d\d\d\d\d\d$')
RE_100UTF8 = re.compile('^.{1,100}$', re.UNICODE)
RE_100UTF8OPT = re.compile('^.{0,100}$', re.UNICODE)
RE_VERSIOON = re.compile('^\d{1,2}$')
RE_VALIK = re.compile('^\d{1,10}\.\d{1,11}$')
RE_NUMBER10 = re.compile(r'^\d{1,10}$')
RE_BASE64 = re.compile('^[a-zA-Z0-9+/=]+$')
RE_BASE64_LINES = re.compile('^[a-zA-Z0-9+/=\n]+$')
RE_HEX = re.compile('^[a-fA-F0-9]+$')
RE_LINENO = re.compile('^\d{0,11}$')
RE_PHONENO = re.compile(r'^\+(\d){7,15}$')
RE_SIGNING_TIME = re.compile('^[TZ0-9:-]+$')
RE_NUMBER100 = re.compile('^\d{1,100}$')

MAX_VOTE_BASE64_SIZE = 24000


# pylint: disable=C0103
def is_jaoskonna_number_kov_koodiga(p1, p2):
    if not is_jaoskonna_omavalitsuse_kood(p1):
        return False
    if not is_jaoskonna_number_kov_sees(p2):
        return False
    return True


def is_ringkonna_number_kov_koodiga(p1, p2):
    if not is_ringkonna_omavalitsuse_kood(p1):
        return False
    if not is_ringkonna_number_kov_sees(p2):
        return False
    return True


def is_jaoskonna_number_kov_sees(nr):
    return is_jaoskonna_number(nr)


def is_jaoskonna_omavalitsuse_kood(nr):
    return is_omavalitsuse_kood(nr)


def is_ringkonna_number_kov_sees(nr):
    return is_ringkonna_number(nr)


def is_ringkonna_omavalitsuse_kood(nr):
    return is_omavalitsuse_kood(nr)


def is_omavalitsuse_kood(nr):
    return _is_number10(nr)


def is_valimiste_identifikaator(elid):
    return RE_ELID.match(elid) <> None


def is_isikukood(code):
    return RE_ISIKUKOOD.match(code) <> None


def is_ringkonna_number(nr):
    return _is_number10(nr)


def is_jaoskonna_number(nr):
    return _is_number10(nr)


def is_100utf8(sstr):
    return RE_100UTF8.match(sstr) <> None


def is_100utf8optional(sstr):
    return RE_100UTF8OPT.match(sstr) <> None


def is_ringkonna_nimi(name):
    return is_100utf8(name)


def is_maakonna_nimi(name):
    return is_100utf8(name)


def is_jaoskonna_nimi(name):
    if not is_100utf8(name):
        return False

    parts = name.split(',')
    record_type = len(parts)
    if not (record_type in [2, 3, 4, 5]):
        return False
    return True


def is_versiooninumber(nr):
    return RE_VERSIOON.match(nr) <> None


def is_nimi(name):
    return is_100utf8(name)


def is_pohjus(sstr):
    return is_100utf8(sstr)


def is_valiku_kood(code):
    return RE_VALIK.match(code) <> None


def is_valiku_nimi(name):
    return is_100utf8(name)


def is_valimisnimekirja_nimi(name):
    return is_100utf8optional(name)


def is_rea_number_voi_tyhi(nr):
    return RE_LINENO.match(nr) <> None


def is_number100(nr):
    return RE_NUMBER100.match(nr) <> None


def _is_number10(nr):
    return RE_NUMBER10.match(nr) <> None


def is_signing_time(str_):
    return RE_SIGNING_TIME.match(str_) <> None


def is_base64(str_):
    return RE_BASE64.match(str_) <> None


def is_base64_lines(str_):
    return RE_BASE64_LINES.match(str_) <> None


def is_vote(str_):
    return (len(str_) < MAX_VOTE_BASE64_SIZE) and \
        (RE_BASE64_LINES.match(str_) <> None)


def is_mobid_poll(str_):
    return str_ == "true"


def is_mobid_phoneno(str_):
    return RE_PHONENO.match(str_) <> None


def is_voters_file_sha256(str_):
    return len(str_) == 64 and is_hex(str_)


def is_session_id(str_):
    return len(str_) == 20 and is_hex(str_)


def is_vote_verification_id(str_):
    return len(str_) == 40 and is_hex(str_)


def is_hex(str_):
    return RE_HEX.match(str_) <> None

# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = hts_state
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import sys
import exception_msg
import election
import htsdisp


def execute():
    _state = election.ElectionState().get()
    if _state == election.ETAPP_TYHISTUS:
        qlist = election.Election().get_questions()
        for el in qlist:
            print el
            htsdisp.start_revocation(el)
    elif _state == election.ETAPP_LUGEMINE:
        qlist = election.Election().get_questions()
        for el in qlist:
            print el
            htsdisp.start_tabulation(el)
    else:
        pass


def usage():
    sys.stderr.write('Kasutamine: %s\n' % sys.argv[0])
    sys.exit(1)


if __name__ == '__main__':

    if len(sys.argv) != 1:
        usage()

    try:
        execute()
    except: # pylint: disable=W0702
        sys.stderr.write(\
            'Viga etapivahetusel: ' + exception_msg.trace() + '\n')
        sys.exit(1)

# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = init_conf
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import sys
import election
import evcommon
import exception_msg

G_HES_KEYS = ['hes', 'hes/voters']
G_HTS_KEYS = ['hts', 'hts/output', 'hts/voters']
G_HLR_KEYS = ['hlr', 'hlr/input', 'hlr/output']


class ElectionCreator:

    def __init__(self):
        self.__quest = None

    def init_hes(self):
        self.__quest.create_keys(G_HES_KEYS)

    def init_hts(self):
        import htscommon

        election.Election().get_root_reg().ensure_key(\
                htscommon.get_verification_key())
        self.__quest.create_keys(G_HTS_KEYS)
        self.__quest.create_revlog()

    def init_hlr(self):
        self.__quest.create_keys(G_HLR_KEYS)

    def prepare(self, ex_elid, ex_type, ex_descr):
        election.create_registry()
        election.Election().init_keys()
        self.__quest = election.Election().new_question(\
                ex_elid, ex_type, ex_descr)

    def init_done(self): # pylint: disable=R0201
        election.ElectionState().init()
        election.Election().init_conf_done()


def usage():
    print "Kasutamine:"
    print "    %s <hes|hts|hlr> <election id> <election type> <description>" \
        % sys.argv[0]
    print "        - Algväärtustab vastava serveri olekupuu"
    sys.exit(1)


def execute(ex_elid, ex_type, ex_descr):

    creat = ElectionCreator()

    creat.prepare(ex_elid, ex_type, ex_descr)

    if election.Election().is_hes():
        creat.init_hes()
    elif election.Election().is_hts():
        creat.init_hts()
    elif election.Election().is_hlr():
        creat.init_hlr()
    else:
        raise Exception('Serveri tüüp määramata')

    creat.init_done()
    print 'Lõpetasin töö edukalt'


def main_function():
    if not len(sys.argv) == 4:
        usage()

    if not int(sys.argv[2]) in evcommon.G_TYPES:
        usage()

    try:
        execute(sys.argv[1], sys.argv[2], sys.argv[3])
    except: # pylint: disable=W0702
        sys.stderr.write('Viga initsialiseerimisel: ' +
            exception_msg.trace() + '\n')
        sys.exit(1)


if __name__ == '__main__':
    main_function()


# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = inputlists
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import sys
import os
import gdbm

import ticker
import formatutil
import evcommon

RINGKONNAD = 'districts_1'
DISTRICTS = 'districts_2'


def valiku_kood_key(arg):
    return int(arg.split('.')[1])


def valiku_kood_cmp(arg1, arg2):
    return arg1 - arg2


def input_list_error(name, lineno, etype, msg, line = None):
    lineno_txt = ''
    line_txt = ''

    if lineno != None:
        lineno_txt = ' LINENO(%d)' % lineno

    if line != None:
        line_txt = ' LINE(%s)' % line

    tmpl = '%(name)s %(error)s,%(lineno)s "%(msg)s"%(line)s'
    return tmpl % { 'name': name, 'error': etype, \
           'lineno': lineno_txt, 'msg': msg, 'line': line_txt  }

class InputList:

    def __init__(self):
        self.__ignore_errors = False
        self.__logard = None
        self.__tic = None
        self.__count = 0
        self.__elid = None
        self.__curline = None
        self.name = '<määramata>'

    def errother(self, msg):
        self._logit(
                input_list_error(
                    self.name, None,
                    'MUU VIGA', msg, self.__curline))

    def errform(self, msg):
        self._logit(
                input_list_error(
                    self.name, self.__count,
                    'FORMAAT', msg, self.__curline))

    def erruniq(self, msg):
        self._logit(
                input_list_error(
                    self.name, self.__count,
                    'UNIKAALSUS', msg, self.__curline))

    def errcons(self, msg):
        self._logit(
                input_list_error(
                    self.name, self.__count,
                    'KOOSKÕLA', msg, self.__curline))

    def attach_elid(self, elid):
        self.__elid = elid

    def ignore_errors(self):
        self.__ignore_errors = True

    def processed(self):
        return self.__count

    def dataline(self, line): # pylint: disable=W0613,R0201
        return False

    def attach_logger(self, logard):
        self.__logard = logard

    def _logit(self, err):
        #self.__elid
        #AppLog().log_error(err)
        if self.__logard:
            self.__logard.log_error(err)

    def current(self, line):
        self.__curline = None
        if line and len(line):
            self.__tic.tick(len(line))
            self.__curline = line.rstrip('\n')
            self.__count += 1
        return self.__curline

    def my_header(self, infile): # pylint: disable=W0613,R0201
        return True

    def _check_header(self, infile):

        retval = True
        line1 = self.current(infile.readline())
        if not line1 or not formatutil.is_versiooninumber(line1):
            self.errform('Versiooninumber')
            retval = False
        else:
            if evcommon.VERSION != line1:
                self.errcons('Versiooninumber pole %s' % evcommon.VERSION)
                retval = False

        line2 = self.current(infile.readline())
        if not line2 or not formatutil.is_valimiste_identifikaator(line2):
            self.errform('Valimiste identifikaator')
            retval = False
        else:
            if self.__elid != None:
                if self.__elid != line2:
                    self.errcons('Valimiste identifikaator pole %s'\
                        % self.__elid)
                    retval = False

        if not self.my_header(infile):
            retval = False

        return retval

    def checkuniq(self, line): # pylint: disable=W0613,R0201
        return False

    def _check_body(self, infile):
        retval = True

        while True:
            data = self.current(infile.readline())
            if data == None:
                break

            if self.dataline(data):
                if not self.checkuniq(data):
                    retval = False
            else:
                retval = False

            if ((not retval) and (not self.__ignore_errors)):
                return retval

        return retval

    def check_format(self, filename, msg=''):
        retval = True
        infile = None
        self.__tic = ticker.Ticker(os.stat(filename).st_size, msg)
        self.__count = 0
        self.__curline = None
        try:
            infile = open(filename, 'r')
            if not self._check_header(infile):
                retval = False
                if not self.__ignore_errors:
                    return retval
            if not self._check_body(infile):
                retval = False
            return retval
        finally:
            if not infile == None:
                infile.close()


class Districts(InputList):

    def __init__(self):
        InputList.__init__(self)
        self.name = 'Jaoskonnad/ringkonnad'
        self.district_list = {}
        self.__jsk = {}
        self.__ring = {}
        self.__ring_kov = {}

    def _check_ringkond(self, lst):
        key = '\t'.join(lst[1:3])
        value = lst[3]
        if key in self.__ring:
            self.erruniq('Lisatav ringkond olemas')
            return False
        self.__ring[key] = value
        self.__ring_kov[key] = set([])
        return True

    def _check_jaoskond(self, lst):
        key = '\t'.join(lst[1:5])
        value = (lst[5], lst[6])
        if key in self.district_list:
            self.erruniq('Lisatav valimisjaoskond ringkonnas olemas')
            return False

        # Eesti sisene jaoskonna kood on unikaalne
        key2 = '\t'.join(lst[1:3])
        if key2 in self.__jsk and not key2 == '0\t0':
            self.erruniq('Lisatav valimisjaoskond globaalselt olemas')
            return False

        ring_key = '\t'.join(lst[3:5])
        if not ring_key in self.__ring:
            self.errcons('Jaoskonda lisatakse olematusse ringkonda')
            return False

        self.__ring_kov[ring_key].add(lst[1])
        self.__jsk[key2] = 1
        self.district_list[key] = value
        return True

    def checkuniq(self, line):
        lst = line.split('\t')
        if lst[0] == 'ringkond':
            return self._check_ringkond(lst)
        return self._check_jaoskond(lst)

    def dataline(self, line):
        lst = line.split('\t')
        if lst[0] == 'ringkond':
            return self._dataline_ringkond(lst)

        elif lst[0] == 'valimisjaoskond':
            return self._dataline_jaoskond(lst)

        else:
            self.errform('Kirje tüüp')
            return False

    def _dataline_ringkond(self, lst):
        if len(lst) != 4:
            self.errform('Kirjete arv real')
            return False

        if not formatutil.is_ringkonna_number_kov_koodiga(lst[1], lst[2]):
            self.errform('Ringkonna number KOV koodiga')
            return False

        if not formatutil.is_ringkonna_nimi(lst[3]):
            self.errform('Ringkonna nimi')
            return False

        return True

    def _dataline_jaoskond(self, lst):
        if len(lst) != 7:
            self.errform('Kirjete arv real')
            return False

        if not formatutil.is_jaoskonna_number_kov_koodiga(\
                lst[1], lst[2]):
            self.errform('Valimisjaoskonna number KOV koodiga')
            return False

        if not formatutil.is_ringkonna_number_kov_koodiga(lst[3], lst[4]):
            self.errform('Ringkonna number KOV koodiga')
            return False

        if not formatutil.is_jaoskonna_nimi(lst[5]):
            self.errform('Valimisjaoskonna nimi')
            return False

        if not formatutil.is_maakonna_nimi(lst[6]):
            self.errform('Maakonna nimi')
            return False

        return True

    def create(self, root, reg):
        # Kustutame vanad ringkondade ja jaoskondade nimekirjad, kui on.
        if reg.check([root, RINGKONNAD]):
            reg.delete_value([root], RINGKONNAD)
        if reg.check([root, DISTRICTS]):
            reg.delete_value([root], DISTRICTS)

        c_ring = len(self.__ring)
        c_dist = len(self.district_list)

        r_value = ''
        for el in self.__ring:
            r_value += el + '\t' + self.__ring[el] + '\n'

        d_value = ''
        for el in self.district_list:
            d_value += el + '\t' + self.district_list[el][0] + '\t' + \
                self.district_list[el][1] + '\n'

        reg.ensure_key([root])
        reg.create_string_value([root], RINGKONNAD, r_value.strip())
        reg.create_string_value([root], DISTRICTS, d_value.strip())
        return c_ring, c_dist

    def load(self, root, reg):
        if not reg.check([root, DISTRICTS]):
            raise Exception('Ei leia valimisjaoskondade faili')

        if not reg.check([root, RINGKONNAD]):
            raise Exception('Ei leia valimisringkondade faili')

        d_data = reg.read_string_value([root], DISTRICTS).value
        r_data = reg.read_string_value([root], RINGKONNAD).value

        lines = d_data.split('\n')
        for line in lines:
            if line == '':
                continue
            lst = line.split('\t')
            self.district_list['\t'.join(lst[0:4])] = (lst[4], lst[5])

        lines = r_data.split('\n')
        for line in lines:
            if line == '':
                continue
            lst = line.split('\t')
            self.__ring['\t'.join(lst[0:2])] = lst[2]

    def has_ring(self, key):
        return ('\t'.join(key) in self.__ring)

    def has_dist(self, key):
        return ('\t'.join(key) in self.district_list)

    def is_kov_in_ring(self, key, kov):
        return kov in self.__ring_kov['\t'.join(key)]

    def district_name(self, ov_nber, s_rk_nber):
        key = [ov_nber, s_rk_nber]
        if not self.has_ring(key):
            raise Exception('Vigased andmed')
        return self.__ring['\t'.join(key)]


class ChoicesBase:

    def __init__(self, reg):
        self.reg = reg
        self.choices_key = None
        self.__sep = '_'

    def reset_choices(self):
        self.reg.reset_key(self.choices_key)

    def choice_name(self, v1, v2):
        return '%s%s%s' % (v1, self.__sep, v2)


class ChoicesHLR(ChoicesBase):

    _TEMPLATE = 'template'

    def __init__(self, reg):
        ChoicesBase.__init__(self, reg)
        self.choices_key = ['hlr', 'choices']

    def create_tree(self, chlist):

        def _distribute_by_districts():
            for _u in chlist:
                _tmp = chlist[_u].split('\t', 3)
                key = '_'.join((_tmp[3].split('\t')))
                if not key in choices_by_districts:
                    choices_by_districts[key] = []
                choices_by_districts[key].append(_tmp[0])

        choices_by_districts = {}
        _distribute_by_districts()
        alld = Districts()
        alld.load('hlr', self.reg)

        ticker_ = ticker.Ticker(len(alld.district_list),
                'Paigaldan valikuid: ')

        for dist in alld.district_list:
            d_lst = dist.split('\t')
            district = self.choice_name(d_lst[0], d_lst[1])
            ringkond = self.choice_name(d_lst[2], d_lst[3])
            if not ringkond in choices_by_districts:
                choices_by_districts[ringkond] = []
            self._create_district(d_lst[2], ringkond, district, choices_by_districts[ringkond])
            ticker_.tick()


    def _create_district(self, ringkond_code, ringkond, district, choices):
        ringkond_key = self.choices_key + [ringkond]
        district_key = self.choices_key + [ringkond, district]
        self.reg.ensure_key(ringkond_key)
        self.reg.ensure_key(district_key)
        self.reg.create_integer_value(district_key, ringkond_code + '.kehtetu', 0)
        for choice in choices:
            self.reg.create_integer_value(district_key, choice, 0)



class ChoicesHES(ChoicesBase):

    def __init__(self, reg):
        ChoicesBase.__init__(self, reg)
        self.choices_key = ['hes', 'choices']

    def district_choices_to_voter(self, voter, quest, distr_name):
        choi_list = self.district_choices(\
            voter['ringkond_omavalitsus'], voter['ringkond'])
        res = ''
        for elem in choi_list:
            res = res + \
                '\t'.join([quest, voter['ringkond'], distr_name, elem]) + '\n'
        return res

    def district_choices(self, v1, v2):
        sub = self.choice_name(v1, v2)
        return \
            self.reg.read_string_value(self.choices_key, sub).value.split('\n')

    def _add_choice(self, dist, choi, sorting_order):
        sub = self.choice_name(dist[0], dist[1])
        data = ''
        for el in sorting_order:
            data += el + '\t' + choi[el][0] + '\t' + choi[el][1] + '\n'
        self.reg.create_string_value(self.choices_key, sub, data.rstrip('\n'))

    def create_tree(self, chlist):

        def _distribute_by_districts():
            for _u in chlist:
                _tmp = chlist[_u].split('\t', 3)
                if not _tmp[3] in districts:
                    districts[_tmp[3]] = {}
                districts[_tmp[3]][_tmp[0]] = _tmp[1:3]

        districts = {}
        _distribute_by_districts()
        sorted_choices = []
        for el in districts:
            sorted_choices = districts[el].keys()
            sorted_choices.sort(valiku_kood_cmp, valiku_kood_key)
            self._add_choice(el.split('\t'), districts[el], sorted_choices)


class ChoicesHTS(ChoicesHES):

    def __init__(self, reg):
        ChoicesHES.__init__(self, reg)
        self.choices_key = ["hts", "choices"]


class ChoicesList(InputList):

    def __init__(self, jsk=None):
        InputList.__init__(self)
        self.name = 'Valikute nimekiri'
        self.uniq = {}
        self.jsk = jsk

    def checkuniq(self, line):
        lst = line.split('\t')
        key = lst[0]
        if key in self.uniq:
            self.erruniq('Lisatav valik juba olemas')
            return False
        self.uniq[key] = line
        return True

    def dataline(self, line):
        lst = line.split('\t')
        return self._dataline_form(lst) and self._dataline_cons(lst)

    def _dataline_form(self, lst):
        if not len(lst) == 5:
            self.errform('Kirjete arv real')
            return False

        if not formatutil.is_valiku_kood(lst[0]):
            self.errform('Valiku kood')
            return False

        if not formatutil.is_valiku_nimi(lst[1]):
            self.errform('Valiku nimi')
            return False

        if not formatutil.is_valimisnimekirja_nimi(lst[2]):
            self.errform('Valimisnimekirja nimi')
            return False

        if not formatutil.is_ringkonna_number_kov_koodiga(lst[3], lst[4]):
            self.errform('Ringkonna number KOV koodiga')
            return False

        return True

    def _dataline_cons(self, lst):
        if not (lst[0].split('.')[0] == lst[3]):
            self.errcons('Ringkonna KOV kood')
            return False

        if self.jsk:
            ring = [lst[3], lst[4]]
            if not self.jsk.has_ring(ring):
                self.errcons('Olematu ringkond')
                return False
            kov = lst[0].split('.')[0]
            if (not kov == '0') and (not self.jsk.is_kov_in_ring(ring, kov)):
                self.errcons('KOV vales ringkonnas')
                return False
        return True

    def create(self, adder, msg=''): # pylint: disable=W0613
        adder.reset_choices()
        c_choice = len(self.uniq)
        adder.create_tree(self.uniq)
        return c_choice

class VotersList(InputList):

    def __init__(self, root, reg, jsk=None):
        InputList.__init__(self)
        self.name = 'Valijate nimekiri'
        self.reg = reg
        self.__rdbi = {}
        self.__add = {}
        self.__del = {}
        self.algne = False
        self.voterskey = [root, 'voters']
        self.jsk = jsk

    def close(self):
        for el in self.__rdbi:
            self.__rdbi[el].close()
        self.__rdbi = {}

    def dataline(self, line):
        lst = line.split('\t')
        return self._dataline_form(lst) and self._dataline_cons(lst)

    def _dataline_form(self, lst): # pylint: disable=R0911
        if len(lst) != 9:
            self.errform('Kirjete arv real')
            return False

        if not formatutil.is_isikukood(lst[0]):
            self.errform('Isikukood')
            return False

        if not formatutil.is_nimi(lst[1]):
            self.errform('Valija nimi')
            return False

        if not lst[2] in ['lisamine', 'kustutamine']:
            self.errform('Kirje tüüp')
            return False

        if not formatutil.is_jaoskonna_number_kov_koodiga(\
                lst[3], lst[4]):
            self.errform('Valimisjaoskonna number KOV koodiga')
            return False

        if not formatutil.is_ringkonna_number_kov_koodiga(lst[5], lst[6]):
            self.errform('Ringkonna number KOV koodiga')
            return False

        if not formatutil.is_rea_number_voi_tyhi(lst[7]):
            self.errform('Rea number')
            return False

        return True

    def _dataline_cons(self, lst):
        if lst[2] == 'lisamine' and lst[8] != '':
            self.errcons('Lisamiskirjel on põhjus')
            return False

        if self.algne:
            if not lst[2] == 'lisamine':
                self.errcons('Algne nimekiri lubab vaid lisamisi')
                return False
        else:
            if lst[2] == 'kustutamine':
                pohjused = ['tokend', 'jaoskonna vahetus', 'muu', '']
                if not lst[8] in pohjused:
                    self.errcons('Põhjus ei ole ' + str(pohjused))
                    return False

        if self.jsk != None \
            and not self.jsk.has_dist([lst[3], lst[4], lst[5], lst[6]]):
            self.errcons('Olematu jaoskond')
            return False

        return True

    def checkuniq(self, line):
        lst = line.split('\t')
        if lst[2] == 'lisamine':
            if lst[0] in self.__add:
                self.errcons('Lisatav isik olemas')
                return False
            else:
                self.__add[lst[0]] = line
        else:
            if lst[0] in self.__del:
                self.errcons('Mitmekordne eemaldamine')
                return False
            else:
                self.__del[lst[0]] = line
        return True

    def my_header(self, infile):
        data = self.current(infile.readline())
        if data == 'algne':
            self.algne = True
        elif data == 'muudatused':
            self.algne = False
        else:
            self.errform('Faili tüüp')
            return False
        return True

    def __db(self, voter_id):
        if not voter_id[10] in self.__rdbi:
            self.__rdbi[voter_id[10]] = \
                gdbm.open(self._dbname(int(voter_id[10])), 'r')
        return self.__rdbi[voter_id[10]]

    def __has_voter(self, voter_id):
        # Siin kontrollime hääletajate nimekirja kontrollimise lippu.
        # Kui lipp on tõene, siis hääletajate nimekirja ei kontrolli ning
        # lubame kõigil hääletada, vajalik VVK'le süsteemi testimiseks/demomiseks

        from election import Election
        if (Election().is_voters_list_disabled()):
            return True

        try:
            db = self.__db(voter_id)
            return db.has_key(voter_id)
        except: # pylint: disable=W0702
            return False

    def has_voter(self, voter_id):
        if not formatutil.is_isikukood(voter_id):
            return False
        return self.__has_voter(voter_id)

    def __get_dummy_voter(self, voter_id):
        id_codes = ["00000000000", "00000000001", "00000000002", \
                "00000000003", "00000000004", "00000000005", \
                "00000000006", "00000000007", "00000000008", "00000000009"]
        id_code = voter_id
        for i in id_codes:
            db = self.__db(i)
            if len(db) == 0:
                continue
            else:
                id_code = db.keys()[0]
            voter = db[id_code].split('\t')
            ret = {
                'nimi': 'XXX YYY', # pylint: disable=W0511
                'jaoskond_omavalitsus': voter[3],
                'jaoskond': voter[4],
                'ringkond_omavalitsus': voter[5],
                'ringkond': voter[6],
                'reanumber': ''}
            return ret
        return None

    def __get_voter(self, voter_id):
        db = self.__db(voter_id)
        voter = db[voter_id].split('\t')
        if len(voter) == 7:
            voter.append('')
        ret = {
                'nimi': voter[1],
                'jaoskond_omavalitsus': voter[3],
                'jaoskond': voter[4],
                'ringkond_omavalitsus': voter[5],
                'ringkond': voter[6],
                'reanumber': voter[7]}
        return ret

    def get_voter(self, voter_id):
        # Siin kontrollime hääletajate nimekirja kontrollimise lippu.
        # Kui lipp on tõene, siis hääletajate nimekirja ei kontrolli ning
        # hääletaja saab olema esimeses leitud ringkonnast.

        from election import Election
        if (Election().is_voters_list_disabled()):
            return self.__get_dummy_voter(voter_id)
        return self.__get_voter(voter_id)

    def _dbname(self, iid):
        return self.reg.path(self.voterskey + ['gdmdb%d' % iid])

    def create(self, msg=''):

        dbi = {}
        try:
            self.close()
            self.reg.ensure_key(self.voterskey)
            for i in range(0, 10):
                dbi[str(i)] = gdbm.open(self._dbname(i), 'cf')

            c_add = len(self.__add)
            c_del = len(self.__del)

            _t = ticker.Ticker(c_add + c_del, msg)

            for el in self.__del:
                db = dbi[el[10]]
                del db[el]
                _t.tick()

            for el in self.__add:
                line = self.__add[el]
                db = dbi[el[10]]
                db[el] = line
                _t.tick()

            return c_add, c_del

        finally:
            print 'Sulgen baase'
            for el in dbi:
                dbi[el].close()
                print '.',
                sys.stdout.flush()
            print

    # Hetkel on tokend püsiv, s.t kui me lisame vaikeväärtusele midagi
    # (mida me ka teeme), siis on need muudatused ka järgmisel
    # vaikeväärtuse kasutusel alles.
    def check_muudatus(self, msg, el_on, tokend):
        """Kontrollib sisendandmete vastuolulisust valijate nimekirja
        muutmise korral. Andmed on vastuolulised järgmistel juhtudel:
        1. lisatav kasutaja on nimekirjas olemas
        2. kustutatavat kasutajat pole nimekirjas

        Kõik ebasobivad kirjed korjatakse self.__add ja self.__del
        listidest ära, sest kontroll tehakse lõpuni.
        """

        retval = True
        if self.algne:
            retval = False
            self.errother('Valijate nimekirja tüüp peab olema "muudatused"')

        _t = ticker.Ticker(len(self.__add) + len(self.__del), msg)

        tmp_del = self.__del.copy()
        tmp_add = self.__add.copy()

        for el in tmp_del:
            line = tmp_del[el]
            if not self.__has_voter(el):
                retval = False
                self.errother(
                    'Kustutatavat isikut %s pole valijate nimekirjas' % el)
                del self.__del[el]
            else:
                if el_on:
                    # hääletusperioodi ajal omab tähendust tõkend
                    _v = line.split('\t')
                    if _v[8] == 'tokend':
                        tokend[_v[0]] = [_v[1], _v[3], _v[4], _v[5], _v[6]]
            _t.tick()

        for el in tmp_add:
            line = tmp_add[el]
            if self.__has_voter(el) and not el in self.__del:
                retval = False
                self.errother(
                    'Lisatav isik %s on juba valijate nimekirjas' % el)
                del self.__add[el]

            _t.tick()

        return retval


if __name__ == '__main__':

    print 'No main'

# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = installer
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import sys
from election import Election
import config_common
import init_conf
import regrights
import tempfile
import shutil

import bdocconfig
import bdocpython
import bdocpythonutils

required = ["*.mobidurl", "*.mobidservice", "*.mobidauthmsg", \
        "*.mobidsignmsg", "*.hts", "*.verifytimeout", "*.verifymaxtries", \
        "*.elections"]

election_required= ["voters", "choices", "districts", "type", "description"]
election_optional= ["ALL", "VALIK", "JAOSK", "TYHIS"]

def add_right(rr, right, persons):
    for person in persons.split():
        rr.add(person, right)


def manage_rights(el, conf):
    rr = regrights.Rights(el)
    for right in ["TYHIS", "VALIK", "JAOSK"]:
        if conf.has_key(right):
            add_right(rr, right, conf[right])
    if conf.has_key("ALL"):
        add_right(rr, "TYHIS", conf["ALL"])
        add_right(rr, "VALIK", conf["ALL"])
        add_right(rr, "JAOSK", conf["ALL"])


def read_config(lines):
    tmp = {}
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            key, value = line.split(':', 1)
            if key in tmp:
                raise Exception('Error: Key (%s) already in config' % key)
            tmp[key] = value.strip()

    ret_gen = {}
    for key in required:
        if not key in tmp:
            raise Exception('Required key (%s) missing' % key)
        ret_gen[key] = tmp[key]
        del tmp[key]

    elections = ret_gen['*.elections'].split()

    ret_el = {}
    for el in elections:
        ret_el[el] = {}
        for key in election_required:
            elkey = "%s.%s" % (el, key)
            if not elkey in tmp:
                raise Exception('Required key (%s) missing' % elkey)
            ret_el[el][key] = tmp[elkey]
            del tmp[elkey]

        for key in election_optional:
            elkey = "%s.%s" % (el, key)
            if elkey in tmp:
                ret_el[el][key] = tmp[elkey]
                del tmp[elkey]

    if len(tmp.keys()) > 0:
        raise Exception('Unknown keys (%s)' % tmp.keys())

    return ret_gen, ret_el




class ElectionInstaller:


    def __init__(self):
        self.__dir = None
        self.__deldir = None
        self.__bdoc = None


    def __del__(self):
        if self.__deldir:
            shutil.rmtree(self.__deldir)


    def set_dir(self, ndir):
        if not ndir == None:
            self.__dir = ndir
        else:
            self.__dir = tempfile.mkdtemp()
            self.__deldir = self.__dir


    def process_bdoc(self, bdocfile):
        config = bdocconfig.BDocConfig()
        config.load(Election().get_bdoc_conf())
        self.__bdoc = bdocpythonutils.BDocContainer()
        self.__bdoc.load(bdocfile)
        profile = bdocpythonutils.ManifestProfile('TM', \
                'application/octet-stream')
        self.__bdoc.validate(profile)

        if len(self.__bdoc.signatures) != 1:
            return False, "BDoc sisaldab rohkem kui ühte allkirja"

        verifier = bdocpython.BDocVerifier()
        config.populate(verifier)

        for el in self.__bdoc.documents:
            verifier.setDocument(self.__bdoc.documents[el], el)

        _, sig_content = self.__bdoc.signatures.popitem()

        res = verifier.verifyTMOffline(sig_content)

        if res.result:
            return True, res.subject
        return False, res.error


    def print_contents(self):
        for el in self.__bdoc.documents:
            print el


    def extract(self):
        for el in self.__bdoc.documents:
            ff = open("%s/%s" % (self.__dir, el), "wb")
            ff.write(self.__bdoc.documents[el])
            ff.close()


    def setup(self):
        g_config = None
        e_config = None

        configfile = open("%s/config" % self.__dir, "r")
        g_config, e_config = read_config(configfile.readlines())
        configfile.close()

        if Election().is_hes():
            Election().set_hts_ip(g_config['*.hts'])
            Election().set_hts_path("/hts.cgi")
            Election().set_hts_verify_path("/hts-verify-vote.cgi")
            Election().config_hth_done()
            Election().set_mid_conf(
                    g_config["*.mobidurl"], \
                    g_config["*.mobidservice"], \
                    g_config["*.mobidauthmsg"], \
                    g_config["*.mobidsignmsg"])

            for el in e_config:
                init_conf.execute(el, e_config[el]['type'], \
                        e_config[el]['description'])

                manage_rights(el, e_config[el])
                config_common.config_hes(el, \
                        "%s/%s" % (self.__dir, e_config[el]['districts']), \
                        "%s/%s" % (self.__dir, e_config[el]['voters']), \
                        "%s/%s" % (self.__dir, e_config[el]['choices']))

        if Election().is_hts():
            Election().set_verification_time(g_config["*.verifytimeout"])
            Election().set_verification_count(g_config["*.verifymaxtries"])

            for el in e_config:
                init_conf.execute(el, e_config[el]['type'], \
                        e_config[el]['description'])

                manage_rights(el, e_config[el])
                config_common.config_hts(el, \
                        "%s/%s" % (self.__dir, e_config[el]['districts']), \
                        "%s/%s" % (self.__dir, e_config[el]['voters']), \
                        "%s/%s" % (self.__dir, e_config[el]['choices']))


        if Election().is_hlr():
            for el in e_config:
                init_conf.execute(el, e_config[el]['type'], \
                        e_config[el]['description'])

                manage_rights(el, e_config[el])
                config_common.config_hlr(el, \
                        "%s/%s" % (self.__dir, e_config[el]['districts']), \
                        "%s/%s" % (self.__dir, e_config[el]['choices']))



def usage():
    print "Invalid arguments"
    print "%s verify <bdoc>" % sys.argv[0]
    print "%s install <bdoc>" % sys.argv[0]
    sys.exit(1)


if __name__ == "__main__":

    bdocpython.initialize()
    if len(sys.argv) != 3:
        usage()

    typ = sys.argv[1]
    if not typ in ['install', 'verify']:
        usage()

    inst = ElectionInstaller()
    ret = 1

    if typ == 'verify':
        res, name = inst.process_bdoc(sys.argv[2])
        if res:
            ret = 0
            print 'Allkiri korrektne'
            inst.print_contents()
            print 'Allkirjastaja: %s' % name
    else:
        inst.set_dir(None)
        res, name = inst.process_bdoc(sys.argv[2])
        if res:
            inst.extract()
            inst.setup()
            ret = 0

    del inst
    bdocpython.terminate()
    sys.exit(ret)


# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = ksum
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import hashlib
import base64
import os
import sys


SHA256 = "sha256"
SHA1 = "sha1"


def filename(data_file, ext):
    return data_file + ext


def _has(ffile):
    return os.access(ffile, os.F_OK)


def _check_file(ffile):
    if not _has(ffile):
        raise Exception("Faili " + ffile + " ei eksisteeri")


def _read_sha256(ffile):
    _check_file(ffile)
    _rf = open(ffile, "r")
    try:
        return _rf.read()
    finally:
        _rf.close()


def compute_voters_files_sha256(voters_file_hashes_dir):
    file_list = os.listdir(voters_file_hashes_dir)
    file_list.sort()
    _s = hashlib.sha256()
    for i in file_list:
        _s.update(i)
    return _s.hexdigest()


def compute(ffile):
    _check_file(ffile)
    _rf = open(ffile, "r")
    try:
        _s = hashlib.sha256()
        for line in _rf:
            _s.update(line)
        return _s.hexdigest()
    finally:
        _rf.close()

def compute_sha1(ffile):
    with open(ffile, "r") as f:
        return base64.encodestring(hashlib.sha1(f.read()).hexdigest()).strip()
    return None


def store(data_file):
    checksum = compute(data_file)
    ksum_f = file("%s.%s" % (data_file, SHA256), "w")
    try:
        ksum_f.write(checksum)
    finally:
        ksum_f.close()


def check(data_file, strict = False):

    checksum_now = compute(data_file)
    checksum_file = None
    method = None

    fn = "%s.%s" % (data_file, SHA256)
    if _has(fn):
        with open(fn, "r") as f:
            checksum_file = f.read()
            method = SHA256

    fn = "%s.%s" % (data_file, SHA1)
    if (checksum_file == None) and _has(fn):
        with open(fn, "r") as f:
            checksum_file = f.read().strip()
            method = SHA1
            checksum_now = compute_sha1(data_file)

    if checksum_file:
        print "Kontrollsummafail olemas, kontrollin (%s)." % method
        return (checksum_now == checksum_file)

    if strict:
        return False

    print "Kontrollsummafail puudub, kuvan kontrollsumma (%s)." % SHA256
    print checksum_now
    return True


def votehash(vote):
    return base64.encodestring(hashlib.sha256(vote).digest()).strip()


def usage():
    print "Kasutamine:"
    print "    %s <store|check> <data_file>" % sys.argv[0]
    sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        usage()
    if sys.argv[1] != "store" and sys.argv[1] != "check":
        usage()

    if sys.argv[1] == "store":
        store(sys.argv[2])
    else:
        if not check(sys.argv[2]):
            print "Kontrollsumma ei klapi"
        else:
            print "Kontrollsumma klapib"

# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = makemessages
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import sys
import exception_msg

#groups
VERIFICATION_ERRORS = "VERIFICATION_ERRORS"

GROUPS = [VERIFICATION_ERRORS]

MSGSTRINGS_IN_FILE = 'evstrings.in'
MSGSTRINGS_FILE = 'evstrings.py'
TEATED_EXAMPLE_FILE = 'teated.example'


def create_msgstrings_py(strings):
    def write_lines(ffile, lines):
        keys = lines.keys()
        keys.sort()
        for i in keys:
            ffile.write("# %s\n%s = \\\n    '%s'\n\n" % \
                (lines[i][0], i, lines[i][1]))

    _wf = open(MSGSTRINGS_FILE, 'w')

    _wf.write('# Log\n')
    _wf.write('# -*- coding: UTF8 -*-\n\n')

    _wf.write('# NB! This file is auto generated by script %s. '\
        'Any changes\n' % sys.argv[0])
    _wf.write('# made to it will be overwritten when the script next '\
        'updates this file.\n\n')

    _wf.write('"""\n')
    _wf.write('Outcoming server error and message strings\n')
    _wf.write('"""\n\n')

    _wf.write('################################\n')
    _wf.write('# Verification protocol errors #\n')
    _wf.write('################################\n\n')
    write_lines(_wf, strings[VERIFICATION_ERRORS])

    _wf.write('\n# vim:set ts=4 sw=4 et fileencoding=utf8:\n')
    _wf.close()


def create_teated_example(strings):
    def write_lines(ffile, group, lines):
        ffile.write('\n\n[%s]\n\n' % group)
        keys = lines.keys()
        keys.sort()
        for i in keys:
            ffile.write("# %s\n%s=%s\n\n" % \
                (lines[i][0], i, lines[i][1]))

    _wf = open(TEATED_EXAMPLE_FILE, 'w')

    _wf.write('# Väljaminevad (vea)teated serveritest HES ja HTS.\n')
    _wf.write('# NB!\n')
    _wf.write('#\t* Teated peavad olema UTF-8 kodeeringus.\n')
    _wf.write('#\t* Võtmesõnu muuta ei tohi\n')
    _wf.write('#\t* Sümbolipaare "%s", mis asendatakse '\
        'dünaamilise tekstiga\n')
    _wf.write('#\t  võib teates ringi tõsta, kuid neid '\
        'ei tohi sealt välja \n')
    _wf.write('#\t  jätta ega juurde lisada.\n')
    _wf.write('\n')

    for group in GROUPS:
        write_lines(_wf, group, strings[group])

    _wf.write('\n# vim:set ts=4 sw=4 et fileencoding=utf8:\n')
    _wf.close()


def main_function():
    try:
        sstrings = {}
        for _g in GROUPS:
            sstrings[_g] = {}

        llines = []
        ff = open(MSGSTRINGS_IN_FILE, 'r')
        for ii in ff.readlines():
            line = ii.strip()
            if len(line) > 0:
                if line[0] == '#':
                    continue
                llines.append(line)
        ff.close()

        #jagame read gruppidesse
        ii = 3
        while ii < len(llines):
            ggroup = llines[ii - 3]
            comment = llines[ii - 2]
            key = llines[ii - 1]
            value = llines[ii]
            if ggroup in GROUPS:
                sstrings[ggroup][key] = (comment, value)
            else:
                raise Exception('Vigane grupp "%s", peab kuuluma "%s"' % \
                    (ggroup, str(GROUPS)))
            ii += 4

        create_msgstrings_py(sstrings)
        create_teated_example(sstrings)

    except: # pylint: disable=W0702
        print exception_msg.trace()
        sys.exit(1)

    sys.exit(0)


if __name__ == '__main__':
    main_function()


# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = monitoring
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

### depends on debian package python-psutil
import os, time, psutil, syslog

if __name__ == "__main__":
    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    ldavg = str(os.getloadavg())
    mem = psutil.phymem_usage().percent
    vmem = psutil.virtmem_usage().percent
    disk = psutil.disk_usage("/").percent
    disk_io = psutil.disk_io_counters(perdisk=True)
    net_io = psutil.network_io_counters(pernic=True)

    lines = []
    lines.append("%s: ldavg:%s mem:%s%% vmem:%s%% disk:%s%%" % \
            (ts, ldavg, mem, vmem, disk))

    for disk in disk_io:
        lines.append("%s: %s %s" % (ts, disk, str(disk_io[disk])))

    for nic in net_io:
        lines.append("%s: %s %s" % (ts, nic, str(net_io[nic])))

    for line in lines:
        syslog.syslog(line)

########NEW FILE########
__FILENAME__ = protocol
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import evcommon
from evmessage import EV_ERRORS

def http_response(content):
    print 'Content-Type: text/plain'
    print 'Content-Length: %d' % (len(content) + 1)
    print
    print content

def msg_ok(msg):
    return evcommon.VERSION + '\n' + evcommon.EVOTE_OK + '\n' + msg


def msg_repeat(cand, repeat):
    return msg_ok(cand + "\nkorduv\t" + repeat)


def msg_error(errcode, msg):
    return evcommon.VERSION + '\n' + errcode + '\n' + msg


def msg_error_technical():
    p1, p2 = plain_error_technical(evcommon.EVOTE_ERROR)
    return msg_error(p1, p2)


def msg_mobid_auth_init_ok(sesscode, challenge):
    return msg_ok(sesscode + '\t' + challenge)

def msg_mobid_sign_init_ok(challenge):
    return msg_ok(challenge)

def msg_mobid_poll():
    return msg_error(evcommon.EVOTE_POLL, '')


def plain_error_technical(code):
    return code, EV_ERRORS.TEHNILINE_VIGA


def plain_error_maintainance():
    return evcommon.EVOTE_ERROR, EV_ERRORS.HOOLDUS


def plain_error_election_off_before():
    return evcommon.EVOTE_ERROR, EV_ERRORS.HAALETUS_POLE_ALANUD


def plain_error_election_off_after():
    return evcommon.EVOTE_ERROR, EV_ERRORS.HAALETUS_ON_LOPPENUD

# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = question
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import inputlists
import evcommon

class Question:

    def __init__(self, elid, root, reg):
        self._elid = elid
        self._reg = reg
        self._root = root

    def qname(self):
        return self._elid

    def set_type(self, qtype):
        if not qtype in evcommon.G_TYPES:
            raise Exception('Vigane hääletustüüp')
        self._reg.ensure_key(['common'])
        self._reg.create_integer_value(['common'], 'type', qtype)

    def get_type(self):
        return self._reg.read_integer_value(['common'], 'type').value

    def set_descr(self, descr):
        self._reg.create_string_value(['common'], 'description', descr)

    def choices_list(self, ed):
        return inputlists.ChoicesList(ed)

    def choices_proxy(self):
        if self._root == 'hes':
            return inputlists.ChoicesHES(self._reg)
        elif self._root == 'hts':
            return inputlists.ChoicesHTS(self._reg)
        else:
            return inputlists.ChoicesHLR(self._reg)

    def get_voter(self, ik):
        vl = None
        try:
            vl = inputlists.VotersList(self._root, self._reg)
            if not vl.has_voter(ik):
                return None
            return vl.get_voter(ik)
        finally:
            if vl != None:
                vl.close()

    def reset_data(self):
        if self._reg.check([self._root, 'choices']):
            self._reg.reset_key([self._root, 'choices'])
        if self._reg.check([self._root, 'districts_1']):
            self._reg.delete_value([self._root], 'districts_1')
        if self._reg.check([self._root, 'districts_2']):
            self._reg.delete_value([self._root], 'districts_2')
        if self._reg.check([self._root, 'voters']):
            self._reg.reset_key([self._root, 'voters'])

    def create_keys(self, keys):
        for key in keys:
            if self._reg.check([key]):
                print 'Alamkataloog ' + key + ' on juba olemas. Jätan vahele'
            else:
                self._reg.create_key([key])
                print 'Loon alamkataloogi ' + key

    def create_revlog(self):
        self._reg.create_string_value(['common'], evcommon.REVLOG_FILE, "")
        self._reg.truncate_value(['common'], evcommon.REVLOG_FILE)
        filen = self._reg.path(['common', evcommon.REVLOG_FILE])
        header = evcommon.VERSION + '\n' + self._elid + '\n'
        out_f = file(filen, 'w')
        out_f.write(header)
        out_f.close()

    def truncate_log_file(self, lognr):
        logname = 'log%s' % lognr
        self._reg.create_string_value(['common'], logname, "")
        self._reg.truncate_value(['common'], logname)

    def can_vote(self, ik):
        return (self.get_voter(ik) != None)

    def choices_to_voter(self, voter):
        ed = inputlists.Districts()
        ed.load(self._root, self._reg)
        rk_nimi = \
            ed.district_name(voter['ringkond_omavalitsus'], voter['ringkond'])
        ch = self.choices_proxy()
        return ch.district_choices_to_voter(voter, self._elid, rk_nimi)

# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = regrights
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import sys
from election import Election
import formatutil
import bdocpython
import bdocpythonutils
import evlogdata

G_RIGHTS = ['TYHIS',
        'VALIK',
        'JAOSK']

G_DESCS = {'TYHIS': 'Tühistus- ja ennistusnimekirja allkirjastaja',
     'VALIK': 'Valikute nimekirja allkirjastaja',
     'JAOSK': 'Jaoskondade ja ringkondade nimekirja allkirjastaja'}

def get_personal_code(subj):
    return subj.partition('CN=')[2].split(',')[2].strip()

def _proper_right(right):
    """
    Kas volitus on meile sobiv?
    """
    return right in G_RIGHTS


class VoteLog:

    def __init__(self, bdocdata):
        self.alines = []
        self.elines = []
        self.bdoc = bdocpythonutils.BDocContainer()
        self.bdoc.load_bytes(bdocdata)
        self.bdoc.validateflex()

        _doc_count = len(self.bdoc.documents)
        if _doc_count == 0:
            raise Exception, "BDoc ei sisalda ühtegi andmefaili"

    def log_signingcert(self):
        if len(self.bdoc.signatures) != 1:
           raise Exception, "BDoc sisaldab rohkem kui ühte allkirja"

        _, sig_content = self.bdoc.signatures.popitem()

        start = '<ds:X509Certificate>'
        end = '</ds:X509Certificate>'
        cert = sig_content.partition(start)[2].partition(end)[0].strip()

        alog, elog = evlogdata.get_cert_data_log(cert, 'signingcert', True)
        self.alines.append(alog)

        if elog:
            self.elines.append(elog)

    def log_documents(self):
        for el in self.bdoc.documents:
            self.alines.append(evlogdata.get_vote(el, self.bdoc.documents[el]))


def analyze_signature_for_log(bdocdata):
    vl = VoteLog(bdocdata)
    vl.log_signingcert()
    return vl.alines, vl.elines


def analyze_vote_for_log(bdocdata):
    vl = VoteLog(bdocdata)
    vl.log_signingcert()
    vl.log_documents()
    return vl.alines, vl.elines


def analyze_vote(bdocdata, config):

    bdoc = bdocpythonutils.BDocContainer()
    bdoc.load_bytes(bdocdata)
    profile = bdocpythonutils.ManifestProfile('TM')
    bdoc.validate(profile)

    _doc_count = len(bdoc.documents)
    if _doc_count == 0:
        raise Exception, "BDoc ei sisalda ühtegi andmefaili"

    if len(bdoc.signatures) != 1:
        raise Exception, "BDoc sisaldab rohkem kui ühte allkirja"

    verifier = bdocpython.BDocVerifier()
    config.populate(verifier)

    for el in bdoc.documents:
        verifier.setDocument(bdoc.documents[el], el)

    _, sig_content = bdoc.signatures.popitem()
    return verifier.verifyTMOffline(sig_content)

def check_vote_hes_mobid(bdocdata, config):

    bdoc = bdocpythonutils.BDocContainer()
    bdoc.load_bytes(bdocdata)
    profile = bdocpythonutils.ManifestProfile('TM')
    bdoc.validate(profile)

    _doc_count = len(bdoc.documents)
    if _doc_count == 0:
        raise Exception, "BDoc ei sisalda ühtegi andmefaili"

    if len(bdoc.signatures) != 1:
        raise Exception, "BDoc sisaldab rohkem kui ühte allkirja"

    verifier = bdocpython.BDocVerifier()
    config.populate(verifier)

    for el in bdoc.documents:
        verifier.setDocument(bdoc.documents[el], el)

    _, sig_content = bdoc.signatures.popitem()
    return verifier.verifyTMOffline(sig_content)


def check_vote_hes(bdocdata, config):

    bdoc = bdocpythonutils.BDocContainer()
    bdoc.load_bytes(bdocdata)
    profile = bdocpythonutils.ManifestProfile('BES')
    bdoc.validate(profile)

    _doc_count = len(bdoc.documents)
    if _doc_count == 0:
        raise Exception, "BDoc ei sisalda ühtegi andmefaili"

    if len(bdoc.signatures) != 1:
        raise Exception, "BDoc sisaldab rohkem kui ühte allkirja"

    verifier = bdocpython.BDocVerifier()
    config.populate(verifier)

    for el in bdoc.documents:
        verifier.setDocument(bdoc.documents[el], el)

    _, sig_content = bdoc.signatures.popitem()
    return verifier.verifyBESOffline(sig_content)


def kontrolli_volitusi(elid, bdocfile, volitus, config):

    bdoc = bdocpythonutils.BDocContainer()
    bdoc.load(bdocfile)
    profile = bdocpythonutils.ManifestProfile('TM', 'application/octet-stream')
    bdoc.validate(profile)

    _doc_count = len(bdoc.documents)
    if _doc_count == 0:
        raise Exception, "BDoc ei sisalda ühtegi andmefaili"

    if _doc_count != 1:
        raise Exception, "BDoc sisaldab %d andmefaili" % _doc_count

    if len(bdoc.signatures) != 1:
        raise Exception, "BDoc sisaldab rohkem kui ühte allkirja"

    verifier = bdocpython.BDocVerifier()
    config.populate(verifier)

    doc_fn, doc_content = bdoc.documents.popitem()
    verifier.setDocument(doc_content, doc_fn)
    _signercode = None
    _, sig_content = bdoc.signatures.popitem()

    res = verifier.verifyTMOffline(sig_content)
    if res.result:
        _signercode = get_personal_code(res.subject)
    else:
        raise Exception, "Invalid signature %s" % res.error

    _rights = Rights(elid)
    if _rights.has(_signercode, volitus):
        return True, '', _signercode

    return False, \
        "Isikul koodiga %s puuduvad volitused " \
        "antud operatsiooni sooritamiseks" \
        % _signercode, _signercode


class Rights:

    def __init__(self, elid):
        self.reg = Election().get_sub_reg(elid, ['common', 'rights'])

    def descr(self, code):
        """
        Tagastab tegelase kohta käiva kirjelduse
        """
        if not formatutil.is_isikukood(code):
            raise Exception('Vigane isikukood')

        if self.reg.check([code, 'description']):
            return self.reg.read_string_value([code], 'description').value
        else:
            return 'Andmed puuduvad'

    def listall(self):
        """
        Tagastab kõik volitused
        """
        lst = self.reg.list_keys()

        ret = ''
        for ele in lst:
            ret = ret + '\n' + self.listuser(ele)
        return ret.strip()

    def _create_user(self, code):
        """     Loome kasutaja, kui teda veel pole
        """
        if not formatutil.is_isikukood(code):
            raise Exception('Vigane isikukood')

        self.reg.ensure_key([code, 'rights'])

    def add(self, code, right):
        """
        Lisab uue volituse
        """
        new_right = right.upper()
        if not _proper_right(new_right):
            raise Exception('Vigane volitus')

        self._create_user(code)

        if not self.has(code, new_right):
            self.reg.create_value([code, 'rights'], new_right, '')
            return True

        return False

    def adddesc(self, code, desc):
        """
        Lisab kasutajale kirjelduse
        """
        self._create_user(code)
        self.reg.create_value([code], 'description', desc)
        return True

    def remove(self, code, right):
        """
        Võtab kasutajalt volituse
        """

        if not formatutil.is_isikukood(code):
            raise Exception('Vigane isikukood')

        new_right = right.upper()
        if not _proper_right(new_right):
            raise Exception('Vigane volitus')

        if self.has(code, new_right):
            self.reg.delete_value([code, 'rights'], new_right)
            return True

        return False

    def remuser(self, code):
        """
        Eemaldab ühe kasutaja volituste failist
        """
        if not formatutil.is_isikukood(code):
            raise Exception('Vigane isikukood')

        return self.reg.ensure_no_key([code])

    def remall(self):
        """
        Eemaldab kõik volitused
        """
        self.reg.reset_key([''])
        return True

    def has(self, code, right):
        """
        Kas koodil on vastav volitus
        """

        if not formatutil.is_isikukood(code):
            raise Exception('Vigane isikukood')

        new_right = right.upper()
        if not _proper_right(new_right):
            raise Exception('Vigane volitus')

        if not self.reg.check([code, 'rights', new_right]):
            return False
        return True

    def listuser(self, code):
        """
        Ainult konkreetse kasutaja õigused
        """
        if not formatutil.is_isikukood(code):
            raise Exception('Vigane isikukood')

        ret = ''
        if self.reg.check([code]):
            ret = ret + code
            ret = ret + ' (' + self.descr(code) + ')'
            sub_list = self.reg.list_keys([code, 'rights'])
            if len(sub_list) > 0:
                for _s in sub_list:
                    ret = ret + '\n\t' + G_DESCS[_s]
            else:
                ret = ret + '\n\tVolitused puuduvad'
        return ret.strip()


def usage():
    print "Kasutamine:"
    print "    %s <valimiste-id> add <isikukood> <volitus>" % sys.argv[0]
    print "        - Annab isikukoodile volituse"
    print "    %s <valimiste-id> desc <isikukood> <kirjeldus>" % sys.argv[0]
    print "        - Annab isikukoodile kirjelduse"
    print "    %s <valimiste-id> rem <isikukood> <volitus>" % sys.argv[0]
    print "        - Võtab isikukoodilt volituse"
    print "    %s <valimiste-id> remuser <isikukood>" % sys.argv[0]
    print "        - Võtab isikukoodilt kõik volitused"
    print "    %s <valimiste-id> remall" % sys.argv[0]
    print "        - Eemaldab kõik volitused"
    print "    %s <valimiste-id> has <isikukood> <volitus>" % sys.argv[0]
    print "        - Küsib isikukoodi volituse olemasolu"
    print "    %s <valimiste-id> listuser <isikukood>" % sys.argv[0]
    print "        - Kuvab isikukoodi volitused"
    print "    %s <valimiste-id> listall" % sys.argv[0]
    print "        - Kuvab kõik volitused"
    print "Võimalikud volitused:"
    print "    " + G_RIGHTS[0] + " - " + G_DESCS[G_RIGHTS[0]]
    print "    " + G_RIGHTS[1] + " - " + G_DESCS[G_RIGHTS[1]]
    print "    " + G_RIGHTS[2] + " - " + G_DESCS[G_RIGHTS[2]]
    sys.exit(1)


def main_function():

    params_one = ['listall', 'remall']
    params_two = ['add', 'desc', 'rem', 'has']
    params_three = ['remuser', 'listuser']

    if len(sys.argv) < 3:
        usage()

    if not ((sys.argv[2] in params_one) or \
        (sys.argv[2] in params_two) or \
        (sys.argv[2] in params_three)):
        usage()

    if sys.argv[2] in params_two and len(sys.argv) < 5:
        usage()

    if sys.argv[2] in params_three and len(sys.argv) < 4:
        usage()

    try:

        _rights = Rights(sys.argv[1])

        if sys.argv[2] == 'add':
            res = _rights.add(sys.argv[3], sys.argv[4])
            if not res:
                print 'Isikul %s on juba volitus "%s"' % \
                    (sys.argv[3], G_DESCS[sys.argv[4]])
            else:
                print 'Volitus "%s" antud' % G_DESCS[sys.argv[4]]
        elif sys.argv[2] == 'desc':
            # kirjeldus võib koosneda mitmest sõnast
            name = " ".join(sys.argv[4:])
            res = _rights.adddesc(sys.argv[3], name)
            print "Kirjeldus lisatud"
        elif sys.argv[2] == 'rem':
            res = _rights.remove(sys.argv[3], sys.argv[4])
            if not res:
                print 'Isikul %s pole volitust %s' % \
                    (sys.argv[3], G_DESCS[sys.argv[4]])
            else:
                print "Volitus kustutatud"
        elif sys.argv[2] == 'remuser':
            res = _rights.remuser(sys.argv[3])
            if not res:
                print "Ei leia isikut %s" % sys.argv[3]
            else:
                print "Isik kustutatud"
        elif sys.argv[2] == 'has':
            res = _rights.has(sys.argv[3], sys.argv[4])
            if not res:
                print "On"
            else:
                print "Ei ole"
        elif sys.argv[2] == 'listuser':
            res = _rights.listuser(sys.argv[3])
            print res
        elif sys.argv[2] == 'listall':
            res = _rights.listall()
            print res
        elif sys.argv[2] == 'remall':
            res = _rights.remall()
            print "Kõik volitused kustutatud"
        else:
            usage()

    except Exception, ex: # pylint: disable=W0703
        print "Viga: %s" % ex
        sys.exit(1)


if __name__ == '__main__':
    main_function()

# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = replace_candidates
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import os
import sys
import shutil
import inputlists
import regrights
from election import Election
from election import ElectionState
from evlog import AppLog
import exception_msg
import evcommon
import question
import time

import bdocconfig
import bdocpython
import bdocpythonutils


class ChoicesReplace:


    def __init__(self):
        self.elid = None
        self._ed = None
        self._ch = None
        self.reg = None
        self.quest = None
        self.root = None
        self.backup_dir = None

        self.conf = bdocconfig.BDocConfig()
        self.conf.load(Election().get_bdoc_conf())


    def check_choices_file(self, valik_f):

        # HES & HLR
        tmp_valik_f = None
        try:

            print 'Kontrollin valikutefaili volitusi'
            ret = regrights.kontrolli_volitusi(self.elid, valik_f, 'VALIK', \
                self.conf)
            if not ret[0]:
                print 'Valikute faili volituste kontroll '\
                    'andis negatiivse tulemuse'
                print ret[1]
                return False

            tmp_valik_f = bdocpythonutils.get_doc_content_file(valik_f)

            self._ch = self.quest.choices_list(self._ed)
            self._ch.attach_elid(self.elid)
            self._ch.attach_logger(AppLog())
            if not self._ch.check_format(tmp_valik_f, \
                'Kontrollin valikute nimekirja: '):
                print "Valikute nimekiri ei vasta nõuetele"
                return False
            print "Valikute nimekiri OK"
            return True
        finally:
            if not tmp_valik_f == None:
                os.unlink(tmp_valik_f)

    def do_it(self):
        c_choice = self._ch.create(self.quest.choices_proxy())
        print 'Paigaldatud %d valikut' % c_choice
        return True

    def _backup_old_choices(self):
        src = os.path.join(self.reg.path(), self.root, 'choices')
        backup_t = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
        self.backup_dir = '/tmp/choices_%s' % backup_t
        if os.path.exists(src) and os.path.isdir(src):
            shutil.move(src, self.backup_dir)
        else:
            raise Exception('Valikute varundamine ebaõnnestus - ei leidnud '\
                                                        'kataloogi %s' % src)

    def _restore_old_choices(self):
        dst = os.path.join(self.reg.path(), self.root, 'choices')
        if os.path.exists(dst):
            shutil.rmtree(dst)

        if os.path.exists(self.backup_dir) and os.path.isdir(self.backup_dir):
            shutil.move(self.backup_dir, dst)
        else:
            raise Exception('Valikute taastamine ebaõnnestus')


    def _delete_old_choices(self):
        if self.backup_dir != None and os.path.exists(self.backup_dir) and \
                                                os.path.isdir(self.backup_dir):
            shutil.rmtree(self.backup_dir, True)


    def prepare(self, confer_name):

        if Election().is_hes():
            self.root = 'hes'
        elif Election().is_hlr():
            self.root = 'hlr'
        else:
            raise Exception('Vigane serveritüüp')

        if not ElectionState().can_replace_candidates():
            print 'Selles hääletuse faasis (%s) valikuid muuta ei saa'\
                % ElectionState().str()
            return False

        self.reg = Election().get_sub_reg(self.elid)
        AppLog().set_app(confer_name, self.elid)
        AppLog().log('Valikute nimekirja välja vahetamine: ALGUS')
        self.quest = question.Question(self.elid, self.root, self.reg)

        self._ed = inputlists.Districts()
        self._ed.load(self.root, self.reg)

        self._backup_old_choices()
        print 'Valimised: ' + self.elid
        return True

    def success(self):
        self._delete_old_choices()
        AppLog().log('Valikute nimekirja välja vahetamine: LÕPP')
        print 'Valikute nimekirja väljavahetamine oli edukas'

    def failure(self):
        self._restore_old_choices()
        AppLog().log('Valikute nimekirja välja vahetamine: LÕPP')
        print 'Valikute nimekirja väljavahetamine ebaõnnestus, '\
            'taastasin muudatuste eelse olukorra'


def replace_candidates(elid, valik_f):

    """Valikute nimekirja välja vahetamine"""

    def do_replace(cr):
        try:
            cr.elid = elid

            if not cr.prepare('REPLACE CHOICES'):
                return False

            if not cr.check_choices_file(valik_f):
                return False

            if not cr.do_it():
                return False
            return True

        except: # pylint: disable=W0702
            print 'Viga valikute nimekirja välja vahetamisel'
            print exception_msg.trace()
            return False


    bdocpython.initialize()
    try:
        my_cr = ChoicesReplace()
        if do_replace(my_cr):
            my_cr.success()
            return True
        else:
            my_cr.failure()
            return False
    finally:
        bdocpython.terminate()


def usage():

    if (len(sys.argv) != 3):
        sys.stderr.write('Kasutamine: ' + sys.argv[0] + \
            ' <valimiste-id> <valikute-fail>\n')
        sys.exit(1)

    evcommon.checkfile(sys.argv[2])

if __name__ == '__main__':
    usage()
    replace_candidates(sys.argv[1], sys.argv[2])

# vim:set ts=4 sw=4 expandtab et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = revocationlists
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import sys
import formatutil
import inputlists

class RevocationList(inputlists.InputList):

    def __init__(self):
        inputlists.InputList.__init__(self)
        self.name = 'Tühistus/ennistus'
        self.revoke = False
        self.rev_list = []
        self.__uniq = {}

    def checkuniq(self, line):
        lst = line.split('\t')
        key = lst[0]
        if key in self.__uniq:
            self.errcons('Mitmekordne tühistamine/ennistamine')
            return False
        self.__uniq[key] = '.'
        self.rev_list.append(lst)
        return True

    def dataline(self, line):
        lst = line.split('\t')
        if not len(lst) == 3:
            self.errform('Kirjete arv real')
            return False

        if not formatutil.is_isikukood(lst[0]):
            self.errform('Vigase vorminguga isikukood')
            return False

        if not formatutil.is_nimi(lst[1]):
            self.errform('Nimi')
            return False

        if not formatutil.is_pohjus(lst[2]):
            self.errform('Põhjus')
            return False

        return True

    def my_header(self, infile):
        data = self.current(infile.readline())
        if data == 'tühistus':
            self.revoke = True
        elif data == 'ennistus':
            self.revoke = False
        else:
            self.errform('Faili tüüp')
            return False
        return True


def main_function():
    rl = RevocationList()
    if not rl.check_format(sys.argv[1]):
        print "Nimekiri ei vasta formaadinõuetele"
        sys.exit(1)

    if rl.revoke:
        print 'Tegu on tühistusnimekirjaga'
    else:
        print 'Tegu on ennistusnimekirjaga'

    for el in rl.rev_list:
        print el

    print "Nimekiri OK"


if __name__ == '__main__':
    main_function()


# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = sessionid
# Session identification
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import os
import singleton

APACHE_UNIQUE_ID = "UNIQUE_ID"
COMMAND_LINE = "cmd"

class InternalSessionID:

    __metaclass__ = singleton.SingletonType

    __apache_id = None
    __session_id = None

    def __init__(self):
        self.reset()

    def reset(self):
        self.__apache_id = os.environ.get(APACHE_UNIQUE_ID)

        if not self.__apache_id:
            self.__apache_id = COMMAND_LINE

        self.__session_id = os.urandom(10).encode('hex')

    def setsid(self, uniq):
        if uniq:
            self.__session_id = uniq

    def voting(self):
        return self.__session_id

    def apache(self):
        return self.__apache_id


def apache():
    return InternalSessionID().apache()

def voting():
    return InternalSessionID().voting()

def setsid(sid):
    InternalSessionID().setsid(sid)

def reset():
    InternalSessionID().reset()


# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = show_voters_files_history
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import sys

from election import Election

def main_function():

    try:

        if Election().is_hes():
            server = 'hes'
        elif Election().is_hts():
            server = 'hts'
        else:
            raise Exception('Vigane serveri tüüp')

        election_ids = Election().get_questions()

        if len(election_ids) == 0:
            print "Valijanimekirju pole laaditud"
        else:
            election_ids.sort()
            for el_i in election_ids:
                print "%s" % el_i
                reg_i = Election().get_sub_reg(el_i, [server])
                if not reg_i.check(['voters_files']):
                    print "\tValijanimekirju pole laaditud"
                    continue

                file_list = reg_i.list_keys(['voters_files'])
                file_list.sort()
                if len(file_list) == 0:
                    print "\tValijanimekirju pole laaditud"
                else:
                    prefix_len = 8 + 1 + 14 + 1
                    j = 1
                    added_total = 0
                    for vf_i in file_list:
                        file_date = vf_i[0:4] + "." + vf_i[4:6] + \
                            "." + vf_i[6:8] + " " + vf_i[8:10] + \
                            ":" + vf_i[10:12] + ":" + vf_i[12:14]
                        file_name = vf_i[15:]
                        if len(file_name) > prefix_len:
                            file_name = file_name[prefix_len:]
                        print "\t%02d. %s - %s" % (j, file_date, file_name)
                        j += 1

                        # nimekirja kokkulugemine
                        _rf = file(reg_i.path(['voters_files', vf_i]), "r")
                        line = _rf.readline()      # päise 1. rida
                        line = _rf.readline()      # päise 2. rida
                        filetype = _rf.readline()  # päise 3. rida
                        added = 0
                        removed = 0
                        while 1:
                            line = _rf.readline()
                            if len(line) == 0:
                                break
                            fields = line.split("\t")
                            if fields[2] == "lisamine":
                                added += 1
                                added_total += 1
                            else:
                                removed += 1
                                added_total -= 1
                        print \
                            "\t    Faili tüüp: %s\n" % filetype.strip() + \
                            "\t    Lisamisi %d, " % added + \
                                  "eemaldamisi %d\n" % removed + \
                            "\t    Kokku peale laadimist: %d" % added_total

    except Exception, ex:
        print 'Viga valijanimekirjade uuenduste ajaloo kuvamisel: ' + str(ex)
        sys.exit(1)


if __name__ == '__main__':
    main_function()


# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = singleton
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

class SingletonType(type):

    def __call__(cls):
        if getattr(cls, '__instance__', None) is None:
            instance = cls.__new__(cls)
            instance.__init__()
            cls.__instance__ = instance
        return cls.__instance__


if __name__ == '__main__':
    pass

# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = ticker
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import sys

class Counter:

    def __init__(self, prefix='', formatstr=''):
        self._prefix = '\t' + prefix + ' %d '
        self._count = 0
        self._meter = 0
        self._level = 1000
        self._txt = self._prefix + formatstr
        self._clear = ''
        for _i in range(0, 80):
            self._clear += ' '

    def __do_output(self, *arglist):
        _args = (self._count,) + arglist
        self.__print_out(self._txt % _args)

    def __print_out(self, out):
        output = ''
        if (len(out) > 80):
            output = out[0:80] + '...'
        else:
            output = out

        sys.stdout.write('\r' + self._clear)
        sys.stdout.write('\r' + output)
        sys.stdout.flush()

    def start(self, txt):
        sys.stdout.write(txt + '\n')
        self.__print_out(self._prefix % self._count)

    def finish(self):
        sys.stdout.write('\r' + self._clear)
        sys.stdout.write('\n')

    def tick(self, amount=1, *arglist):
        self._count += amount
        self._meter += amount
        if (self._meter >= self._level):
            while self._meter >= self._level:
                self._meter -= self._level

            self.__do_output(*arglist)


class Ticker:
    # pylint: disable=R0903

    def __init__(self, all_, txt):
        self._txt = txt
        self._per = all_ / 100
        if self._per == 0:
            self._per = all_ + 1

        self._mod = 0
        self._out = 0

    def tick(self, amount=1):

        if self._out < 100:
            self._mod += amount
            if (self._mod >= self._per):
                while self._mod >= self._per:
                    self._mod = self._mod - self._per
                    self._out += 1
                if self._out > 100:
                    self._out = 100
                print '%s%d%%\r' % (self._txt, self._out),
                sys.stdout.flush()
                if self._out == 100:
                    print


def tickit(max_, msg):
    ticker = Ticker(max_, msg)

    for _ in range(max_):
        ticker.tick()


if __name__ == "__main__":
    tickit(1000000, 'Teade: ')

# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = repo
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2013 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import os
import sys
import subprocess


def usage():
    print 'Kasutamine:'
    print '    %s <repo> <deb directory> <i386|amd64>' % sys.argv[0]
    print 'Tulemus - <repo>.iso ja kataloogis <repo> debiani repositoorium'
    print 'HOIATUS: kustutab esimese sammuna kataloogi <repo>'
    sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 4:
        usage()

    if not sys.argv[3] in ['i386', 'amd64']:
        usage()

    repo = sys.argv[1].rstrip('/')
    debs = sys.argv[2]
    platform = sys.argv[3]
    binpath = 'dists/wheezy/evote/binary-%s' % platform
    fullrepo = '%s/%s' % (repo, binpath)

    print 'Kustutan vana repositooriumi (%s)' % repo
    subprocess.call('rm -rf %s' % repo, shell = True)

    print 'Loon uue kataloogistruktuuri (%s)' % fullrepo
    os.makedirs(fullrepo)

    print 'Kopeerin *.deb failid (%s %s)' % (debs, fullrepo)
    cmd = 'cp %s/*.deb %s' % (debs, fullrepo)
    subprocess.call(cmd, shell = True)

    print 'Lähtestan repositooriumi'
    out_f = open('%s/Packages.gz' % fullrepo, 'wb')
    p1 = subprocess.Popen(['dpkg-scanpackages', binpath, '/dev/null'], \
                                        stdout = subprocess.PIPE, cwd = repo)
    p2 = subprocess.Popen(['gzip', '-9c'], stdin = p1.stdout, stdout = out_f)
    p2.communicate()
    out_f.close()

    print 'Valmendan ketta'
    os.makedirs('%s/%s' % (repo, '.disk'))
    out_f = open('%s/%s/info' % (repo, '.disk'), 'wb')
    out_f.write('E-hääletamissüsteem')
    out_f.close()
    subprocess.call('genisoimage -input-charset utf8 -r -J -o %s.iso %s' % \
                                                    (repo, repo), shell = True)

# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = burner
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import subprocess
import stat
import time
import os.path
import shutil
import evcommon
import uiutil

BURN_PROGRAM = "growisofs"

DVD_MIN_SPEED = 1
DVD_MAX_SPEED = 256
DVD_DEF_SPEED = 4
DVD_SIZE = 4400000000                   # DVD 4,7 GB peaks olema siis 4,4GiB'i.

APACHE2_LOG_DIR = '/var/log/apache2'
SNAPSHOT_BACKUP_SCRIPT = '/usr/share/evote/evote_backup_snapshot'

class DiskBurner:
    """Klass, mis aitab DVD-plaate kirjutada.
    """

    def __init__(self, work_dir):
        self.work_dir = work_dir
        if os.path.isdir(work_dir):
            self.delete_files()
        os.mkdir(work_dir)

    def delete_files(self):
        if os.path.isdir(self.work_dir):
            shutil.rmtree(self.work_dir, True)
        return

    def _backup(self, src_dir):

        prompt = "Sisestage varukoopiate tegemiseks parool:"
        snapshot = subprocess.Popen(["sudo", "-p", prompt,
                        SNAPSHOT_BACKUP_SCRIPT, src_dir,
                        self.work_dir], stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT)
        # The pipe will be closed when the process dies.
        # Read it before wait, so we won't have deadlock by waiting on
        # process that's waiting on the output.
        # The stderr=STDOUT means that stderr is redirected into stdout.
        error = snapshot.stdout.read()
        snapshot.wait()
        if (snapshot.returncode != 0):
            print error
            return False

        return True

    def backup_dir(self, src_dir, apache=False):
        if not self._backup(src_dir):
            return False

        if apache and not self._backup(APACHE2_LOG_DIR):
            return False

        # Jagame jupid DVD'de kaupa kataloogidesse.

        chunks = os.listdir(self.work_dir)
        chunks.sort()

        dvd_count = 0
        current_size = 0
        current_dir = os.path.join(self.work_dir, "%d" % dvd_count)
        os.mkdir(current_dir)

        for chunk in chunks:
            chunk_path = os.path.join(self.work_dir, chunk)
            chunk_size = os.path.getsize(chunk_path)

            if current_size + chunk_size > DVD_SIZE:
                current_size = 0
                dvd_count += 1
                current_dir = os.path.join(self.work_dir, "%d" % dvd_count)
                os.mkdir(current_dir)
            current_size += chunk_size

            os.rename(chunk_path, os.path.join(current_dir, chunk))

        return True

    def burn(self):
        dvd_def_speed = DVD_DEF_SPEED
        dvd_count = 0
        dvd_dirs = os.listdir(self.work_dir)
        dvd_dirs_size = len(dvd_dirs)
        dvd_dirs.sort()

        for dvd_dir in dvd_dirs:
            dvd_count += 1

            if dvd_dirs_size > 1:
                print "Hakkame krijutama %d. DVD-d %d-st" % \
                        (dvd_count, dvd_dirs_size)

            if not uiutil.ask_yes_no(\
                    "Palun sisestage DVDR(W) meedia seadmesse. Jätkan"):
                print "DVD kirjutamine katkestati"
                return 1

            while True:
                dvd_speed = uiutil.ask_int(\
                        "Palun sisestage DVD kirjutamiskiirus", \
                        dvd_def_speed, DVD_MIN_SPEED, DVD_MAX_SPEED)
                dvd_def_speed = dvd_speed

                cmdline = '%s -speed=%d -Z /dev/dvd -q -r -J %s' % \
                        (BURN_PROGRAM, dvd_speed, \
                            os.path.join(self.work_dir, dvd_dir))

                print cmdline
                rc = subprocess.call(cmdline, shell=True)
                if rc == 0:
                    break
                print "Salvestamine nurjus veakoodiga %d" % rc
                if not uiutil.ask_yes_no("Kas proovite uuesti"):
                    print "DVD kirjutamine katkestati"
                    return 1
        return 0


class Restorer (DiskBurner):
    def __init__(self, work_dir):
        DiskBurner.__init__(self, work_dir)
        self.chunks = []

    def chunk_count(self):
        return len(self.chunks)

    def add_chunks(self, src_dir):
        count = 0
        for chunk in os.listdir(src_dir):
            if chunk.startswith("evote-registry"):
                print "Kopeerin faili '%s' ..." % chunk
                shutil.copy(os.path.join(src_dir, chunk), self.work_dir)
                subprocess.call('chmod ug+w %s' % \
                        os.path.join(self.work_dir, chunk), shell=True)
                self.chunks.append(os.path.join(self.work_dir, chunk))
                count += 1
        if (count == 0):
            print 'Kataloogis \'%s\' ei olnud ühtegi varukoopia faili' % \
                    src_dir

    def restore(self, reg_dir):
        if len(self.chunks) == 0:
            print('Pole ühtegi varukoopia faili. Loobun taastamisest')
            return

        self.chunks.sort()

        command = ['cat']
        command.extend(self.chunks)

        cat = subprocess.Popen(command, stdout=subprocess.PIPE, \
                stderr=subprocess.PIPE)
        tar = subprocess.Popen(['tar', '-xzp'], \
                stdin=cat.stdout, stderr=subprocess.PIPE,\
                cwd=self.work_dir)
        cat.wait()
        tar.wait()

        if (cat.returncode != 0):
            print cat.stderr.read()
            return False

        if (tar.returncode != 0):
            print tar.stderr.read()
            return False

        # Nüüd võime vana registri uue vastu vangerdada.
        os.rename(reg_dir, '%s-%s' % \
                (reg_dir, time.strftime("%Y%m%d%H%M%S")))
        os.rename(os.path.join(self.work_dir, 'registry'), reg_dir)

        return True


class FileListBurner(DiskBurner):

    def __init__(self, work_dir):
        DiskBurner.__init__(self, work_dir)
        self.application_log_exists = False
        self.error_log_exists = False
        self.debug_log_exists = False
        self.current_disk = None
        self.current_disk_name = ''
        self.session_dir_name = ''
        self.session_id = 'evote-%s' % time.strftime("%Y%m%d%-H%M%S")
        self.current_dvd_size = 0

    def _disk_name(self, election_id):
        self.current_disk_name = os.path.join(self.work_dir, '%d' % \
                self.current_disk)
        self.session_dir_name = os.path.join(self.current_disk_name, '%s' % \
                self.session_id)
        ret = os.path.join(self.session_dir_name, '%s' % election_id)
        if not os.path.isdir(ret):
            os.makedirs(ret)
        return ret

    def _new_disk(self, election_id):
        if self.current_disk == None:
            self.current_disk = 0
        else:
            self.current_disk += 1
        ret = self._disk_name(election_id)
        return ret

    def append_files(self, election_id, file_list):

        dir_name = ''
        if self.current_disk != None:
            dir_name = self._disk_name(election_id)
        else:
            dir_name = self._new_disk(election_id)

        for i in file_list:
            file_size = 0
            try:
                file_size = os.stat(i)[stat.ST_SIZE]
            except OSError:
                print "Faili '%s' ei eksisteeri" % i
                continue

            if file_size > DVD_SIZE:
                print "Fail '%s' on liiga suur, et DVD-le mahtuda" % i
                continue

            if file_size + self.current_dvd_size > DVD_SIZE:
                self.current_dvd_size = file_size
                dir_name = self._new_disk(election_id)

            tail = os.path.split(i)[1]

            if tail == evcommon.APPLICATION_LOG_FILE:
                if not self.application_log_exists:
                    shutil.copy(i, self.session_dir_name)
                    self.application_log_exists = True
            elif tail == evcommon.ERROR_LOG_FILE:
                if not self.error_log_exists:
                    shutil.copy(i, self.session_dir_name)
                    self.error_log_exists = True
            elif tail == evcommon.DEBUG_LOG_FILE:
                if not self.debug_log_exists:
                    shutil.copy(i, self.session_dir_name)
                    self.debug_log_exists = True
            else:
                shutil.copy(i, dir_name)

        return True


# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = evfiles
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import evcommon
from election import Election

class EvFileTable:

    def __init__(self):
        self.__files = []

    def add_file(self, ffile):
        if ffile:
            self.__files.append(ffile)

    def get_existing_files(self, usebinary):

        ret = {}

        for el in self.__files:
            if el.exists():
                if usebinary or not el.binary():
                    ret[el.name()] = el.path()

        return ret


IS_BINARY = True


class EvFile:

    def __init__(self, filename, uiname, regprefix, binary = False):
        self.__filename = filename
        self.__uiname = uiname
        self.__regprefix = regprefix
        self.__reg = Election().get_root_reg()
        self.__binary = binary

    def exists(self):
        return self.__reg.check(self.__regprefix + [self.__filename])

    def path(self):
        return self.__reg.path(self.__regprefix + [self.__filename])

    def name(self):
        return self.__uiname

    def binary(self):
        return self.__binary


def log1_file(elid):
    return EvFile(evcommon.LOG1_FILE, \
                    evcommon.LOG1_STR, ['questions', elid, 'common'])

def log2_file(elid):
    return EvFile(evcommon.LOG2_FILE, \
                    evcommon.LOG2_STR, ['questions', elid, 'common'])

def log3_file(elid):
    return EvFile(evcommon.LOG3_FILE, \
                    evcommon.LOG3_STR, ['questions', elid, 'common'])

def log4_file(elid):
    return EvFile(evcommon.LOG4_FILE, \
                    evcommon.LOG4_STR, ['questions', elid, 'common'])

def log5_file(elid):
    return EvFile(evcommon.LOG5_FILE, \
                    evcommon.LOG5_STR, ['questions', elid, 'common'])

def revlog_file(elid):
    return EvFile(evcommon.REVLOG_FILE, \
                    evcommon.REVLOG_STR, ['questions', elid, 'common'])

def application_log_file():
    return EvFile(evcommon.APPLICATION_LOG_FILE, \
                    evcommon.APPLICATION_LOG_STR, ['common'])

def error_log_file():
    return EvFile(evcommon.ERROR_LOG_FILE, \
                    evcommon.ERROR_LOG_STR, ['common'])

def integrity_log_file():
    return EvFile(evcommon.DEBUG_LOG_FILE, \
                    evcommon.DEBUG_LOG_STR, ['common'])

def ocsp_log_file():
    return EvFile(evcommon.OCSP_LOG_FILE, \
                    evcommon.OCSP_LOG_STR, ['common'])

def voter_list_log_file():
    return EvFile(evcommon.VOTER_LIST_LOG_FILE, \
                    evcommon.VOTER_LIST_LOG_STR, ['common'])

def elections_result_file(elid):
    return EvFile(evcommon.ELECTIONS_RESULT_FILE, \
                                        evcommon.ELECTIONS_RESULT_STR, \
                                        ['questions', elid, 'hts', 'output'])

def electorslist_file(elid):
    return EvFile(evcommon.ELECTORSLIST_FILE, evcommon.ELECTORSLIST_STR, \
                                        ['questions', elid, 'hts', 'output'])


def electorslist_file_pdf(elid):
    return EvFile(evcommon.ELECTORSLIST_FILE_PDF, \
            evcommon.ELECTORSLIST_PDF_STR, \
            ['questions', elid, 'hts', 'output'], IS_BINARY)


def revreport_file(elid):
    return EvFile(evcommon.REVREPORT_FILE, evcommon.REVREPORT_STR, \
                                        ['questions', elid, 'hts', 'output'])

def statusreport_file():
    return EvFile(evcommon.STATUSREPORT_FILE, \
                    evcommon.STATUSREPORT_STR, ['common'])

def electionresult_zip_file(elid):
    return EvFile(evcommon.ELECTIONRESULT_ZIP_FILE, \
                    evcommon.ELECTIONRESULT_ZIP_STR, \
                    ['questions', elid, 'hlr', 'output'], IS_BINARY)

def electionresult_file(elid):
    return EvFile(evcommon.ELECTIONRESULT_FILE, \
                                        evcommon.ELECTIONRESULT_STR, \
                                        ['questions', elid, 'hlr', 'output'])

def electionresultstat_file(elid):
    return EvFile(evcommon.ELECTIONRESULT_STAT_FILE, \
                                        evcommon.ELECTIONRESULT_STAT_STR, \
                                        ['questions', elid, 'hlr', 'output'])

def add_hts_files_to_table(elid, table):
    import os
    reg = Election().get_root_reg()
    if reg.check(['questions', elid, 'hts', 'output']):
        o_files = os.listdir(reg.path(['questions', elid, 'hts', 'output']))
        for of in o_files:
            if of.find("tokend.") == 0 and of.find(".sha256") == -1:
                table.add_file(EvFile(of, of, ['questions', elid, 'hts', 'output']))

# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = evui
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import os
import signal
import sys
import traceback
import uiutil
from election import Election
from election import ElectionState
import election
import evcommon
import evreg
import burner
import autocmd

import evfiles
import serviceutil

CHOICE_ADD_DESCRIPTION = "Anna isikule kirjeldus"
CHOICE_ADD_RIGHTS = "Anna isikule volitused"
CHOICE_AUDIT = "Audit"
CHOICE_BACK = "Tagasi (Ctrl+D)"
CHOICE_BACKUP = "Varunda olekupuu ja apache logid"
CHOICE_BROWSE_FILE = "Sirvi"
CHOICE_CHANGE_ELECTION_DESCRIPTION = "Muuda valimiste kirjeldust"
CHOICE_CHECK_CONFIGURE = "Vaata konfiguratsiooni hetkeseisu"
CHOICE_CHECK_CONSISTENCY = "Kontrolli HES ja HTS serverite kooskõlalisust"
CHOICE_CONFIGURE_COMMON = "Üldine konfiguratsioon"
CHOICE_CONFIGURE = "Konfigureeri"
CHOICE_COUNT_VOTES = "Loe hääled kokku"
CHOICE_CREATE_STATUS_REPORT = "Genereeri vaheauditi aruanne"
CHOICE_CREATE_STATUS_REPORT_NO_VERIFY = \
    "Genereeri vaheauditi aruanne hääli verifitseerimata"
CHOICE_DEL_ELECTION_ID = "Kustuta valimisidentifikaator"
CHOICE_DELETE_FILE_ALL = "Kustuta kõik failid"
CHOICE_DELETE_FILE = "Kustuta"
CHOICE_DIR_LIST = "Vaata kataloogi sisu"
CHOICE_DISABLE_VOTERS_LIST = "Keela hääletajate nimekirja kontroll"
CHOICE_ELECTION_ID = "Tegele valimistega"
CHOICE_ENABLE_VOTERS_LIST = "Luba hääletajate nimekirja kontroll"
CHOICE_EXIT = "Välju"
CHOICE_EXPORT_ALL = "Ekspordi kõik"
CHOICE_EXPORT_FILE_ALL = "Ekspordi kõik failid"
CHOICE_EXPORT_FILE = "Ekspordi"
CHOICE_GET_MID_CONF = "Vaata Mobiil-ID sätteid"
CHOICE_SET_MID_CONF = "Muuda Mobiil-ID sätteid"
CHOICE_GET_HES_HTS_CONF = "Vaata HTSi konfiguratsiooni"
CHOICE_GET_HSM_CONF = "Vaata HSMi konfiguratsiooni"
CHOICE_HES_CONF = "Lae HESi valimiste failid"
CHOICE_HLR_BACKUP = "Varunda olekupuu"
CHOICE_HLR_CONF = "Lae HLRi valimiste failid"
CHOICE_HTS_CONF = "Lae HTSi valimiste failid"
CHOICE_HTS_REVOKE = "Rakenda tühistus-/ennistusnimekirja"
CHOICE_IMPORT_VOTES = "Impordi hääled lugemiseks"
CHOICE_INSTALL = "Lae valimiste seaded paigaldusfailist"
CHOICE_LIST_ALL_RIGHTS = "Vaata kõiki volitusi"
CHOICE_LIST_USER_RIGHTS = "Vaata isiku volitusi"
CHOICE_LOAD_ELECTORS = "Lae valijate faili täiendused"
CHOICE_REPLACE_CANDIDATES = "Vaheta välja kandidaatide nimekiri"
CHOICE_LOAD_STRINGS = "Lae konfigureeritavad teated"
CHOICE_NEW_ELECTION_ID = "Loo uus valimisidentifikaator"
CHOICE_PRINT_FILE_ALL = "Prindi kõik failid"
CHOICE_PRINT_FILE = "Prindi"
CHOICE_REGRIGHTS = "Volitused"
CHOICE_REM_ALL_RIGHTS = "Kustuta kõik volitused"
CHOICE_REM_RIGHTS = "Kustuta isiku volitus"
CHOICE_REM_USER_RIGHTS = "Kustuta kõik isiku volitused"
CHOICE_RESTORE_FROM_BACKUP = "Taasta olekupuu varukoopiast"
CHOICE_RESTORE_INIT_STATUS = "Taasta algolek"
CHOICE_SET_HES_HTS_CONF = "Säti HTSi konfiguratsioon"
CHOICE_SET_HSM_CONF = "Initsialiseeri HSM"
CHOICE_START_COUNTING = "Alusta lugemisperioodi"
CHOICE_PRE_START_COUNTING_HES = "Nimekirjade väljastamise lõpetamine"
CHOICE_CANCEL_PRE_START_COUNTING_HES = "Nimekirjade väljastamise taastamine"
CHOICE_START_COUNTING_HES = "Lõpeta hääletusperiood"
CHOICE_START_ELECTION = "Alusta hääletusperioodi"
CHOICE_START_REVOCATION = "Alusta tühistusperioodi"
CHOICE_THE_END = "Lõpeta valimised"
CHOICE_BDOC_CONF = "Lae sertifikaatide konfiguratsioon"
CHOICE_VIEW_ELECTION_DESCRIPTION = "Vaata valimiste kirjeldust"
CHOICE_VIEW_STATUS_REPORT = "Vaata vaheauditi aruannet"
CHOICE_VOTERS_FILE_HISTORY = "Valijanimekirjade uuendamise ajalugu"
CHOICE_VERIFICATION_CONF = "Seadista kontrollitavus"
CHOICE_GET_VERIFICATION_CONF = "Vaata kontrollitavuse sätteid"
CHOICE_SCHEDULE_AUTOSTART = "Seadista hääletusperioodi automaatne algus"
CHOICE_UNSCHEDULE_AUTOSTART = "Kustuta hääletusperioodi automaatne algus"
CHOICE_SCHEDULE_AUTOSTOP = "Seadista hääletusperioodi automaatne lõpp"
CHOICE_UNSCHEDULE_AUTOSTOP = "Kustuta hääletusperioodi automaatne lõpp"
CHOICE_SCHEDULE_CONF = "Seadista automaatse lõpu kestvus"

# Konfi skriptid
SCRIPT_HTS_STATE = "hts_state.py"

# Prorgammid
PROGRAM_RM = "rm -rf"
PROGRAM_LESS = "less -fC"

# Faili actionid
ACTION_BROWSE_FILE = "Sirvi faili"
ACTION_PRINT_FILE = "Prindi fail(id)"
ACTION_EXPORT_FILE = "Ekspordi fail(id)"
ACTION_DELETE_FILE = "Kustuta fail(id)"

#Menüü pealkirjad
MENU_MAINMENU = "Peamenüü"

STR_YES = "yes"
#STR_NO =  "no"

# PID
MESSAGE_PID_EXISTS = "%s on juba olemas! Jätkamine võib lõhkuda olemasoleva operaatori menüü.\n" \
                     "Kas soovid jätkata" % autocmd.REFRESH_PID_VALUE

SHA256_KEYS = [ \
    evcommon.ELECTIONRESULT_STR, \
    evcommon.ELECTIONRESULT_STAT_STR, \
    evcommon.ELECTIONS_RESULT_STR, \
    evcommon.REVREPORT_STR, \
    evcommon.ELECTORSLIST_STR]

def file_action_to_str(action):

    ret = None

    if action == ACTION_BROWSE_FILE:
        return CHOICE_BROWSE_FILE
    elif action == ACTION_PRINT_FILE:
        return CHOICE_PRINT_FILE
    elif action == ACTION_EXPORT_FILE:
        return CHOICE_EXPORT_FILE
    elif action == ACTION_DELETE_FILE:
        return CHOICE_DELETE_FILE
    else:
        raise Exception('Defineerimata failioperatsioon')

    return ret


class MenuItemCommand:

    def __init__(self, name, action, args):
        self.__name = name
        self._action = action
        self.__args = args

    def get_str(self, idx):
        return " (%d) %s" % (idx, self.__name)

    def draw(self, idx):
        print " [%d] %s" % (idx, self.__name)

    def do_action(self, _):
        if self._action:
            if self.__args:
                self._action(self.__args)
            else:
                self._action()

class MenuItemSubMenu:

    def __init__(self):
        self.__name = None
        self.__cmd_list = []

    def create(self, name):
        self.__name = name
        self.__cmd_list = []

    def add_item(self, item, action = None, args = None):
        self.__cmd_list.append(MenuItemCommand(item, action, args))

    def draw(self, idx):
        print " [%d] %s" % (idx, self.__name)
        for k in range(len(self.__cmd_list)):
            print "\t", self.__cmd_list[k].get_str(k + 1)

    def do_action(self, cmd_string):

        if len(cmd_string) < 1:
            print "Palun tee ka alamvalik"
            return
        elif len(cmd_string) > 1:
            print "Vale valik"
            return

        idx = int(cmd_string[0]) - 1

        try:
            if idx not in range(len(self.__cmd_list)):
                print "Vale valik: %s" % cmd_string[0]
                return
        except ValueError:
            print "Vale valik: %s" % cmd_string[0]
            return

        self.__cmd_list[idx].do_action(cmd_string)

class EvUI:
    """
    Teksti moodis kasutajaliides HESi, HTSi ja HLRi tarbeks
    """

    def __init__(self):
        self.quit_flag = 0
        self.cmd_list = []
        self.__sub0 = MenuItemSubMenu()
        self.__sub1 = MenuItemSubMenu()
        self.__sub2 = MenuItemSubMenu()
        self.file_table = {}

        self.ui_update_function = None

        self.cur_elid = ""
        self.file_action = ""
        self.menu_caption = ""
        self.state = ElectionState().get()
        self.init_main_menu()

    def execute_command(self, val, cmd):
        self.cmd_list[val].do_action(cmd[1:])

    def items(self):
        return range(len(self.cmd_list))

    def add_item(self, name, action, args = None):
        self.cmd_list.append(MenuItemCommand(name, action, args))

    def add_sub(self, sub):
        self.cmd_list.append(sub)

    def clear_items(self):
        self.cmd_list = []

    def get_quit_flag(self):
        return self.quit_flag

    def init_main_menu(self):

        def create_sub0(sub):
            sub.create(CHOICE_ELECTION_ID)
            for el in Election().get_questions():
                sub.add_item("%s (%s)" % \
                    (el , Election().get_election_type_str(el)), \
                                        self.do_conf_election, el)

        def create_sub1_hes(sub):
            sub.create(CHOICE_CONFIGURE_COMMON)
            sub.add_item(CHOICE_BDOC_CONF, serviceutil.do_bdoc_conf_hes)
            sub.add_item(CHOICE_INSTALL, serviceutil.do_install)
            sub.add_item(CHOICE_SET_MID_CONF, serviceutil.do_set_mid_conf)
            sub.add_item(CHOICE_GET_MID_CONF, serviceutil.do_get_mid_conf)
            sub.add_item(CHOICE_SET_HES_HTS_CONF, serviceutil.do_set_hts_conf)
            sub.add_item(CHOICE_GET_HES_HTS_CONF, serviceutil.do_get_hts_conf)
            sub.add_item(CHOICE_VOTERS_FILE_HISTORY, \
                                            serviceutil.do_voters_file_history)

            if Election().is_config_hth_done():
                sub.add_item(CHOICE_CHECK_CONSISTENCY, \
                                            serviceutil.do_check_consistency)

            if self.state == election.ETAPP_ENNE_HAALETUST:
                if Election().is_voters_list_disabled():
                    sub.add_item(CHOICE_ENABLE_VOTERS_LIST, \
                                            serviceutil.do_enable_voters_list)
                else:
                    sub.add_item(CHOICE_DISABLE_VOTERS_LIST, \
                                            serviceutil.do_disable_voters_list)

            if Election().is_hes_configured():
                if self.state < election.ETAPP_HAALETUS:
                    if autocmd.scheduled(autocmd.COMMAND_START):
                        sub.add_item(CHOICE_UNSCHEDULE_AUTOSTART, \
                                            serviceutil.do_unschedule_autostart)
                    else:
                        sub.add_item(CHOICE_SCHEDULE_AUTOSTART, \
                                            serviceutil.do_schedule_autostart)

                if self.state == election.ETAPP_ENNE_HAALETUST:
                    sub.add_item(CHOICE_START_ELECTION, self.do_change_state)

                if self.state < election.ETAPP_LUGEMINE:
                    if autocmd.scheduled(autocmd.COMMAND_PREPARE_STOP) or \
                            autocmd.scheduled(autocmd.COMMAND_STOP):
                        sub.add_item(CHOICE_UNSCHEDULE_AUTOSTOP, \
                                            serviceutil.do_unschedule_autostop)
                    elif Election().allow_new_voters():
                        sub.add_item(CHOICE_SCHEDULE_AUTOSTOP, \
                                            serviceutil.do_schedule_autostop)

            if self.state == election.ETAPP_HAALETUS:
                if Election().allow_new_voters():
                    sub.add_item(CHOICE_PRE_START_COUNTING_HES, \
                                            serviceutil.do_pre_start_counting_hes)
                else:
                    sub.add_item(CHOICE_CANCEL_PRE_START_COUNTING_HES, \
                                            serviceutil.do_cancel_pre_start_counting_hes)
                sub.add_item(CHOICE_START_COUNTING_HES, self.do_change_state)

        def create_sub1_hts(sub):
            sub.create(CHOICE_CONFIGURE_COMMON)
            sub.add_item(CHOICE_BDOC_CONF, serviceutil.do_bdoc_conf)
            sub.add_item(CHOICE_INSTALL, serviceutil.do_install)
            sub.add_item(CHOICE_VOTERS_FILE_HISTORY, \
                                            serviceutil.do_voters_file_history)

            sub.add_item(CHOICE_VERIFICATION_CONF, \
                    serviceutil.do_verification_conf)
            sub.add_item(CHOICE_GET_VERIFICATION_CONF, \
                    serviceutil.do_get_verification_conf)

            if self.state == election.ETAPP_ENNE_HAALETUST:
                if Election().is_voters_list_disabled():
                    sub.add_item(CHOICE_ENABLE_VOTERS_LIST, \
                                            serviceutil.do_enable_voters_list)
                else:
                    sub.add_item(CHOICE_DISABLE_VOTERS_LIST, \
                                            serviceutil.do_disable_voters_list)

            if self.state == election.ETAPP_ENNE_HAALETUST and \
                Election().is_hts_configured():
                sub.add_item(CHOICE_START_ELECTION, self.do_change_state)

            if self.state == election.ETAPP_HAALETUS:
                sub.add_item(CHOICE_START_REVOCATION, self.do_change_state)

            if self.state == election.ETAPP_TYHISTUS:
                sub.add_item(CHOICE_START_COUNTING, self.do_change_state)

        def create_sub1_hlr(sub):
            sub.create(CHOICE_CONFIGURE_COMMON)
            sub.add_item(CHOICE_BDOC_CONF, serviceutil.do_bdoc_conf)
            sub.add_item(CHOICE_INSTALL, serviceutil.do_install)
            sub.add_item(CHOICE_SET_HSM_CONF, serviceutil.do_set_hsm_conf)
            sub.add_item(CHOICE_GET_HSM_CONF, serviceutil.do_get_hsm_conf)
            if self.state == election.ETAPP_ENNE_HAALETUST and \
                Election().is_hlr_configured():
                sub.add_item(CHOICE_START_COUNTING, self.do_change_state)

        def create_sub2_hts(sub):
            retval = False
            flag_1 = self.state > election.ETAPP_ENNE_HAALETUST
            flag_2 = evfiles.statusreport_file().exists()

            if flag_1 or flag_2:
                retval = True
                sub.create(CHOICE_AUDIT)

            if flag_1:
                sub.add_item(CHOICE_CREATE_STATUS_REPORT, \
                                        serviceutil.do_create_status_report)
                sub.add_item(CHOICE_CREATE_STATUS_REPORT_NO_VERIFY, \
                                serviceutil.do_create_status_report_no_verify)
            if flag_2:
                sub.add_item(CHOICE_VIEW_STATUS_REPORT, \
                                        serviceutil.do_view_status_report)
            return retval

        self.ui_update_function = self.init_main_menu
        self.menu_caption = MENU_MAINMENU
        self.cur_elid = ""
        self.clear_items()
        if self.state == election.ETAPP_ENNE_HAALETUST:
            self.add_item(CHOICE_NEW_ELECTION_ID, serviceutil.do_new_election)
            if Election().count_questions() > 0:
                self.add_item(CHOICE_DEL_ELECTION_ID, \
                                                serviceutil.do_del_election)

        if Election().count_questions() > 0:
            create_sub0(self.__sub0)
            self.add_sub(self.__sub0)

        if Election().is_hes():
            create_sub1_hes(self.__sub1)
            self.add_sub(self.__sub1)
            self.add_item(\
                        CHOICE_CHECK_CONFIGURE, serviceutil.do_check_configure)
            self.add_item(CHOICE_EXPORT_ALL, self.do_export_all)
            self.add_item(CHOICE_BACKUP, serviceutil.do_backup)
            self.add_item(CHOICE_RESTORE_FROM_BACKUP, serviceutil.do_restore)
            self.add_item(CHOICE_DIR_LIST, serviceutil.do_dir_list)

            if self.state == election.ETAPP_LUGEMINE:
                self.add_item(CHOICE_THE_END, self.do_the_end)

            if self.state == election.ETAPP_HAALETUS:
                self.add_item(CHOICE_RESTORE_INIT_STATUS, \
                                        serviceutil.do_restore_init_status)

            self.add_item(CHOICE_LOAD_STRINGS, \
                                        serviceutil.do_import_error_strings)

            self.add_item(CHOICE_EXIT, self.do_quit)

        elif Election().is_hts():
            create_sub1_hts(self.__sub1)
            self.add_sub(self.__sub1)
            self.add_item(\
                        CHOICE_CHECK_CONFIGURE, serviceutil.do_check_configure)
            if create_sub2_hts(self.__sub2):
                self.add_sub(self.__sub2)
            self.add_item(CHOICE_EXPORT_ALL, self.do_export_all)
            self.add_item(CHOICE_BACKUP, serviceutil.do_backup)
            self.add_item(CHOICE_RESTORE_FROM_BACKUP, serviceutil.do_restore)
            self.add_item(CHOICE_DIR_LIST, serviceutil.do_dir_list)

            if self.state == election.ETAPP_LUGEMINE:
                self.add_item(CHOICE_THE_END, self.do_the_end)

            if self.state == election.ETAPP_HAALETUS:
                self.add_item(CHOICE_RESTORE_INIT_STATUS, \
                                    serviceutil.do_restore_init_status)
            self.add_item(CHOICE_LOAD_STRINGS, \
                                        serviceutil.do_import_error_strings)
            self.add_item(CHOICE_EXIT, self.do_quit)

        elif Election().is_hlr():
            create_sub1_hlr(self.__sub1)
            self.add_sub(self.__sub1)
            self.add_item(\
                        CHOICE_CHECK_CONFIGURE, serviceutil.do_check_configure)
            self.add_item(CHOICE_EXPORT_ALL, self.do_export_all)
            self.add_item(CHOICE_HLR_BACKUP, serviceutil.do_backup)
            self.add_item(CHOICE_RESTORE_FROM_BACKUP, serviceutil.do_restore)
            self.add_item(CHOICE_DIR_LIST, serviceutil.do_dir_list)
            if self.state == election.ETAPP_LUGEMINE:
                self.add_item(CHOICE_THE_END, self.do_the_end)
            self.add_item(CHOICE_EXIT, self.do_quit)


    def init_election_menu(self):

        def create_sub1(sub):
            sub.create(CHOICE_CONFIGURE)
            sub.add_item(CHOICE_REGRIGHTS, self.init_reg_rights_menu)

            if Election().is_hes():
                if self.state == election.ETAPP_ENNE_HAALETUST and \
                    Election().is_config_bdoc_done():
                    sub.add_item(CHOICE_HES_CONF, \
                                        serviceutil.do_hes_conf, self.cur_elid)
                if self.state != election.ETAPP_LUGEMINE and \
                    Election().is_config_server_elid_done(self.cur_elid):
                    sub.add_item(CHOICE_LOAD_ELECTORS, \
                                serviceutil.do_load_electors, self.cur_elid)

                if self.state == election.ETAPP_ENNE_HAALETUST and \
                    Election().is_config_server_elid_done(self.cur_elid):
                    sub.add_item(CHOICE_REPLACE_CANDIDATES, \
                                serviceutil.do_replace_candidates, \
                                                                self.cur_elid)

            if Election().is_hts():
                sub.add_item(CHOICE_VIEW_ELECTION_DESCRIPTION, \
                        serviceutil.do_view_election_description, \
                                                            self.cur_elid)
                if self.state == election.ETAPP_ENNE_HAALETUST:
                    sub.add_item(CHOICE_CHANGE_ELECTION_DESCRIPTION, \
                        serviceutil.do_change_election_description, \
                                                                self.cur_elid)
                    if Election().is_config_bdoc_done():
                        sub.add_item(CHOICE_HTS_CONF, \
                                        serviceutil.do_hts_conf, self.cur_elid)
                if self.state != election.ETAPP_TYHISTUS and \
                    self.state != election.ETAPP_LUGEMINE and \
                    Election().is_config_server_elid_done(self.cur_elid):
                    sub.add_item(CHOICE_LOAD_ELECTORS, \
                                serviceutil.do_load_electors, self.cur_elid)

            if Election().is_hlr():
                if Election().is_config_bdoc_done():
                    sub.add_item(CHOICE_HLR_CONF, \
                                        serviceutil.do_hlr_conf, self.cur_elid)
                if Election().is_config_server_done():
                    sub.add_item(CHOICE_IMPORT_VOTES, \
                                    serviceutil.do_import_votes, self.cur_elid)

                if self.state == election.ETAPP_ENNE_HAALETUST and \
                    Election().is_config_server_elid_done(self.cur_elid):
                    sub.add_item(CHOICE_REPLACE_CANDIDATES, \
                                serviceutil.do_replace_candidates, \
                                                                self.cur_elid)


        self.ui_update_function = self.init_election_menu
        self.menu_caption = "%s->%s \"%s\" (%s)" % \
            (MENU_MAINMENU, CHOICE_ELECTION_ID, self.cur_elid, \
            Election().get_election_type_str(self.cur_elid))
        self.clear_items()

        create_sub1(self.__sub1)
        self.add_sub(self.__sub1)
        if Election().is_hes():
            self.add_item(CHOICE_BROWSE_FILE, self.do_browse)
            self.add_item(CHOICE_PRINT_FILE, self.do_print)
            self.add_item(CHOICE_EXPORT_FILE, self.do_export)
            self.add_item(CHOICE_DELETE_FILE, self.do_delete)
            self.add_item(CHOICE_BACK, self.init_main_menu)

        if Election().is_hts():
            if self.state == election.ETAPP_TYHISTUS:
                self.add_item(CHOICE_HTS_REVOKE, \
                                        serviceutil.do_revoke, self.cur_elid)
            self.add_item(CHOICE_BROWSE_FILE, self.do_browse)
            self.add_item(CHOICE_PRINT_FILE, self.do_print)
            self.add_item(CHOICE_EXPORT_FILE, self.do_export)
            self.add_item(CHOICE_DELETE_FILE, self.do_delete)
            self.add_item(CHOICE_BACK, self.init_main_menu)

        elif Election().is_hlr():
            if self.state == election.ETAPP_LUGEMINE and \
                Election().is_config_hlr_input_elid_done(self.cur_elid):
                self.add_item(CHOICE_COUNT_VOTES, \
                                    serviceutil.do_count_votes, self.cur_elid)
            self.add_item(CHOICE_BROWSE_FILE, self.do_browse)
            self.add_item(CHOICE_PRINT_FILE, self.do_print)
            self.add_item(CHOICE_EXPORT_FILE, self.do_export)
            self.add_item(CHOICE_DELETE_FILE, self.do_delete)
            self.add_item(CHOICE_BACK, self.init_main_menu)


    def init_file_menu(self):
        self.ui_update_function = self.init_file_menu
        self.menu_caption = "%s->%s \"%s\"->%s" % (MENU_MAINMENU, \
                                CHOICE_ELECTION_ID, self.cur_elid, \
                                file_action_to_str(self.file_action))
        self.clear_items()
        keys = self.file_table.keys()
        keys.sort()
        for key in keys:
            if self.file_action == ACTION_EXPORT_FILE or \
                self.file_action == ACTION_DELETE_FILE:
                self.add_item(key, self.do_file_action_one_wsha, key)
            else:
                self.add_item(key, self.do_file_action_one, key)

        if len(self.file_table) > 1:
            if self.file_action == ACTION_PRINT_FILE:
                self.add_item(CHOICE_PRINT_FILE_ALL, self.do_file_action_all)

            if self.file_action == ACTION_EXPORT_FILE:
                self.add_item(CHOICE_EXPORT_FILE_ALL, \
                                                self.do_file_action_all_wsha)

            if self.file_action == ACTION_DELETE_FILE:
                self.add_item(CHOICE_DELETE_FILE_ALL, \
                                                self.do_file_action_all_wsha)

        self.add_item(CHOICE_BACK, self.init_election_menu)

    def init_reg_rights_menu(self):
        self.ui_update_function = self.init_reg_rights_menu
        self.menu_caption = "%s->%s \"%s\"->%s" % (MENU_MAINMENU, \
            CHOICE_ELECTION_ID, self.cur_elid, CHOICE_REGRIGHTS)
        self.clear_items()
        self.add_item(CHOICE_ADD_RIGHTS, \
                                serviceutil.do_add_rights, self.cur_elid)
        self.add_item(CHOICE_ADD_DESCRIPTION, \
                            serviceutil.do_add_description, self.cur_elid)
        self.add_item(CHOICE_REM_RIGHTS, \
                                serviceutil.do_rem_rights, self.cur_elid)
        self.add_item(CHOICE_REM_USER_RIGHTS, \
                            serviceutil.do_rem_user_rights, self.cur_elid)
        self.add_item(CHOICE_REM_ALL_RIGHTS, \
                            serviceutil.do_rem_all_rights, self.cur_elid)
        self.add_item(CHOICE_LIST_USER_RIGHTS, \
                            serviceutil.do_list_user_rights, self.cur_elid)
        self.add_item(CHOICE_LIST_ALL_RIGHTS, \
                            serviceutil.do_list_all_rights, self.cur_elid)
        self.add_item(CHOICE_BACK, self.init_election_menu)

    def do_conf_election(self, args):
        self.cur_elid = args
        self.init_election_menu()

    def do_the_end(self):
        srv = Election().get_server_str()
        is_hlr = (srv == evcommon.APPTYPE_HLR)
        root_dir = Election().get_root_reg().root
        if uiutil.ask_yes_no("Kas oled kindel"):
            if uiutil.ask_yes_no(\
                "Valimiste lõpetamisega kustutatakse kogu " + \
                    "konfiguratsioon.\nKas jätkan"):
                print "Kustutan e-hääletuse faile. Palun oota.."
                # Kustutame kogu konfiguratsiooni ja ka olekupuu taastamise
                # käigus alles hoitud vanad olekupuud.
                cmd = "%s %s/* %s/../registry-*" % \
                                            (PROGRAM_RM, root_dir, root_dir)
                os.system(cmd)
                #HLRi korral ka vastav mälufailisüsteemi kraam.
                if is_hlr:
                    if "EVOTE_TMPDIR" in os.environ:
                        tmpdir = os.environ["EVOTE_TMPDIR"]
                        cmd = "%s %s/*" % (PROGRAM_RM, tmpdir)
                        os.system(cmd)
                # Initsialiseerime nüüd ka liidese.
                Election().set_server_str(srv)
                self.__init__()

    def do_quit(self):
        self.quit_flag = 1


    def draw(self):
        state_str = str(election.G_STATES[self.state])
        if self.state == 4 and Election().is_hes():
            state_str = "Hääletusperioodi lõpp"
        print "-----------------------------------------------------"
        print " %s\n Olek: %s" % (self.menu_caption, state_str)
        print "-----------------------------------------------------"

        for i in self.items():
            self.cmd_list[i].draw(i + 1)

    # Failidega seotud commandid
    def do_browse(self):
        self.file_action = ACTION_BROWSE_FILE
        self.init_file_menu()

    def do_print(self):
        self.file_action = ACTION_PRINT_FILE
        self.init_file_menu()

    def do_export(self):
        self.file_action = ACTION_EXPORT_FILE
        self.init_file_menu()

    def do_delete(self):
        self.file_action = ACTION_DELETE_FILE
        self.init_file_menu()

    def do_file_action_one(self, args = None):
        self.do_file_action([self.file_table[args]])

    def get_sha256_file(self, key):
        if key in SHA256_KEYS or key.find("tokend.") == 0:
            sha256_file = self.file_table[key] + ".sha256"
            if os.access(sha256_file, os.F_OK):
                return sha256_file
        return None

    def do_file_action_one_wsha(self, args = None):
        files = []
        files.append(self.file_table[args])
        sha256f = self.get_sha256_file(args)
        if sha256f:
            files.append(sha256f)
        self.do_file_action(files)

    def do_file_action_all(self):
        self.do_file_action(self.file_table.values())

    def do_file_action_all_wsha(self):
        files = []
        for el in self.file_table:
            files.append(self.file_table[el])
            sha256f = self.get_sha256_file(el)
            if sha256f:
                files.append(sha256f)
        self.do_file_action(files)

    def do_file_action(self, args):

        if len(args) < 1:
            return

        if self.file_action == ACTION_BROWSE_FILE:
            for el in args:
                cmd = "%s %s" % (PROGRAM_LESS, el)
                os.system(cmd)
        elif self.file_action == ACTION_PRINT_FILE:
            if len(args) > 1:
                print "Prindin failid.."
            else:
                print "Prindin faili.."
            uiutil.print_file_list(args)
        elif self.file_action == ACTION_EXPORT_FILE:
            cd_burner = burner.FileListBurner(evcommon.burn_buff())
            try:
                if len(args) > 1:
                    print "Ekspordin failid.."
                else:
                    print "Ekspordin faili.."
                print "Palun oota.."
                if cd_burner.append_files(self.cur_elid, args):
                    cd_burner.burn()
            finally:
                cd_burner.delete_files()
        elif self.file_action == ACTION_DELETE_FILE:
            if uiutil.ask_yes_no("Kas oled kindel"):
                if len(args) > 1:
                    print "Kustutan failid.."
                else:
                    print "Kustutan faili.."

                for el in args:
                    os.remove(el)
                self.init_file_menu()

    def do_export_all(self):
        """Kõigi valimiste väljund failid CDle
        """
        if Election().count_questions() < 1:
            print "Ei ole midagi eksportida"
            return
        cd_burner = burner.FileListBurner(evcommon.burn_buff())
        try:
            print "Ekspordime kõik. Palun oota.."
            for i in Election().get_questions():
                self.update_files(i)
                file_list = self.file_table.values()
                # Olukord, kus valimiste ID on, aga faile pole
                if len(file_list) == 0:
                    print "Ei ole midagi eksportida"
                    return

                # Kui on, siis ka vastav sha256 fail exporti
                for file_key in self.file_table.keys():
                    sha256f = self.get_sha256_file(file_key)
                    if sha256f:
                        file_list.append(sha256f)
                if not cd_burner.append_files(i, file_list):
                    return
            cd_burner.burn()
        finally:
            cd_burner.delete_files()

    def do_change_state(self):
        if not uiutil.ask_yes_no("Kas oled kindel"):
            return
        ElectionState().next()
        if Election().is_hts():
            cmd = SCRIPT_HTS_STATE
            os.system(cmd)

    def execute(self, cmd):
        if len(cmd) < 1:
            return
        try:
            val = int(cmd[0]) - 1
        except ValueError:
            print "Palun sisesta valiku number"
            return
        if val in self.items():
            try:
                self.execute_command(val, cmd)
            except KeyboardInterrupt:
                print "\nKatkestame tegevuse.."
            except EOFError:
                print "\nKatkestame tegevuse.."
            except Exception, what:
                traceback.print_exc(None, sys.stdout)
                print "Tegevus nurjus: %s" % what
        else:
            print "Tundmatu valik: %s" % cmd[0]

    def update(self):
        self.state = ElectionState().get()
        use_binary = True
        if self.file_action == ACTION_BROWSE_FILE:
            use_binary = False
        self.update_files(self.cur_elid, use_binary)
        if self.ui_update_function:
            self.ui_update_function()

    def update_files(self, elid, usebinary=True):
        """
        Siin hoiame up-to-date faili tabelit, mida saab
        sirvida/printida/exportida
        """
        self.file_table = {}  # string : path

        files = evfiles.EvFileTable()
        if Election().is_hes():
            files.add_file(evfiles.application_log_file())
            files.add_file(evfiles.error_log_file())
            files.add_file(evfiles.integrity_log_file())
            files.add_file(evfiles.voter_list_log_file())
        elif Election().is_hts():
            files.add_file(evfiles.log1_file(elid))
            files.add_file(evfiles.log2_file(elid))
            files.add_file(evfiles.log3_file(elid))
            files.add_file(evfiles.revlog_file(elid))
            files.add_file(evfiles.application_log_file())
            files.add_file(evfiles.error_log_file())
            files.add_file(evfiles.voter_list_log_file())
            files.add_file(evfiles.elections_result_file(elid))
            files.add_file(evfiles.electorslist_file(elid))
            files.add_file(evfiles.electorslist_file_pdf(elid))
            files.add_file(evfiles.revreport_file(elid))
            files.add_file(evfiles.statusreport_file())
            files.add_file(evfiles.ocsp_log_file())
            evfiles.add_hts_files_to_table(elid, files)
        elif Election().is_hlr():
            files.add_file(evfiles.log4_file(elid))
            files.add_file(evfiles.log5_file(elid))
            files.add_file(evfiles.application_log_file())
            files.add_file(evfiles.error_log_file())
            files.add_file(evfiles.electionresult_zip_file(elid))
            files.add_file(evfiles.electionresult_file(elid))
            files.add_file(evfiles.electionresultstat_file(elid))

        self.file_table = files.get_existing_files(usebinary)


class RefreshSignal(Exception):
    pass

def usr1_handler(signal, frame):
    """Handler for SIGUSR1 sent by the automatic election start script."""
    raise RefreshSignal

def write_pid():
    reg = evreg.Registry(root=evcommon.EVREG_CONFIG)
    reg.ensure_key(autocmd.REFRESH_PID_KEY)
    try:
        pid = reg.read_integer_value(autocmd.REFRESH_PID_KEY, \
                autocmd.REFRESH_PID_VALUE)
    except (IOError, LookupError):
        pid = None

    # If a PID exists and the user does not want to continue, return None.
    if pid and not uiutil.ask_yes_no(MESSAGE_PID_EXISTS, uiutil.ANSWER_NO):
        return None
    return reg.create_integer_value(autocmd.REFRESH_PID_KEY, \
            autocmd.REFRESH_PID_VALUE, os.getpid())

def main():
    # Ignoreerime SIGTSTP, st. Ctrl+Z, Ctrl+C ja Aborti
    signal.signal(signal.SIGTSTP, signal.SIG_IGN)
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGABRT, signal.SIG_IGN)
    signal.signal(signal.SIGUSR1, signal.SIG_IGN)

    pid = write_pid()
    if not pid:
        return

    evui = EvUI()
    uiutil.clrscr()

    prompt = "%sOperaator> " % Election().get_server_str()

    while not evui.get_quit_flag():
        try:
            signal.signal(signal.SIGUSR1, usr1_handler)
            evui.update()
            evui.draw()
            cmd = raw_input(prompt)
        except KeyboardInterrupt:
            # Siin püüame Ctrl+C kinni
            cmd = str(len(evui.cmd_list))
        except EOFError:
            print ""
            if evui.menu_caption == MENU_MAINMENU:
                continue
            else:
                cmd = str(len(evui.cmd_list))
        except RefreshSignal:
            print
            continue
        signal.signal(signal.SIGUSR1, signal.SIG_IGN)
        evui.execute(cmd.split())

    try:
        pid.delete()
    except OSError:
        pass # pid file has been deleted

    # Kustutame ka CD-lt importimisel tekitatud ajutised failid
    uiutil.del_tmp_files()
    print "Head aega!\n"


if __name__ == "__main__":
    main()

# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = serviceutil
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

from election import ElectionState
from election import Election
import os
import uiutil
import regrights
import burner
import evcommon
import autocmd

SCRIPT_CONFIG_HTH = "config_hth.py"
SCRIPT_CONFIG_HSM = "config_hsm.py"
SCRIPT_CHECK_CONSISTENCY = "check_consistency.py"
SCRIPT_VOTERS_FILE_HISTORY = "show_voters_files_history.py"
SCRIPT_REGRIGHTS = "regrights.py"
SCRIPT_HTS = "load_rev_files.py"
SCRIPT_INIT_CONF = "init_conf.py"
SCRIPT_CONFIG_SRV = "config_common.py"
SCRIPT_INSTALL_SRV = "installer.py"
SCRIPT_CONFIG_DIGIDOC = "config_bdoc.py"
SCRIPT_APPLY_CHANGES = "apply_changes.py"
SCRIPT_REPLACE_CANDIDATES = "replace_candidates.py"
SCRIPT_CONFIG_HLR_INPUT = "config_hlr_input.py"
SCRIPT_HTSALL = "htsalldisp.py"
SCRIPT_HLR = "hlr.py"

PROGRAM_LESS = "less -fC"
PROGRAM_LS = "ls -1Xla"

# pylint: disable-msg=W0702

def do_voters_file_history():
    cmd = '%s' % (SCRIPT_VOTERS_FILE_HISTORY)
    os.system(cmd)

def do_dir_list():
    dir_name = uiutil.ask_string("Sisesta kataloog")
    if os.path.isdir(dir_name):
        cmd = "%s %s | %s" % (PROGRAM_LS, dir_name, PROGRAM_LESS)
        os.system(cmd)
    else:
        print "\"%s\" ei ole kataloog" % dir_name

def do_import_error_strings():
    import evmessage
    evstrings_file = uiutil.ask_file_name("Sisesta teadete-faili asukoht")
    evm = evmessage.EvMessage()
    evm.import_str_file(evstrings_file)

def do_check_consistency():
    cmd = "%s" % SCRIPT_CHECK_CONSISTENCY
    os.system(cmd)

def do_get_mid_conf():

    try:
        url = Election().get_mid_url()
    except:
        url = uiutil.NOT_DEFINED_STR

    try:
        name = Election().get_mid_name()
    except:
        name = uiutil.NOT_DEFINED_STR

    try:
        auth_msg, sign_msg = Election().get_mid_messages()
    except:
        auth_msg = uiutil.NOT_DEFINED_STR
        sign_msg = uiutil.NOT_DEFINED_STR

    print "DigiDocService URL: %s" % url
    print "Teenuse nimi: %s" % name
    print "Teade autentimisel: %s" % auth_msg
    print "Teade signeerimisel: %s" % sign_msg

def do_set_mid_conf():

    try:
        def_url = Election().get_mid_url()
    except:
        def_url = 'https://www.openxades.org:8443/DigiDocService'

    try:
        def_name = Election().get_mid_name()
    except:
        def_name = 'Testimine'

    try:
        def_auth_msg, def_sign_msg = Election().get_mid_messages()
    except:
        def_auth_msg = 'E-hääletus, autentimine'
        def_sign_msg = 'E-hääletus, hääle allkirjastamine'

    url = uiutil.ask_string(\
                "Sisesta DigiDocService'i URL", None, None, def_url)

    name = uiutil.ask_string(\
                "Sisesta teenuse nimi", None, None, def_name)

    auth_msg = uiutil.ask_string(\
                "Sisesta sõnum autentimisel", None, None, def_auth_msg)

    sign_msg = uiutil.ask_string(\
                "Sisesta sõnum allkirjastamisel", None, None, def_sign_msg)

    Election().set_mid_conf(url, name, auth_msg, sign_msg)

def do_get_hsm_conf():
    cmd = "%s get" % SCRIPT_CONFIG_HSM
    os.system(cmd)

def do_set_hsm_conf():

    reg = Election().get_root_reg()

    if reg.check(['common', 'hsm', 'tokenname']):
        try:
            def_tokenname = \
                reg.read_string_value(['common', 'hsm'], 'tokenname').value
        except:
            def_tokenname = "evote"
    else:
        def_tokenname = "evote"

    token_name = uiutil.ask_string(\
                "Sisesta HSM'i partitsiooni nimi", None, None, def_tokenname)

    if reg.check(['common', 'hsm', 'privkeylabel']):
        try:
            def_privkeylabel = \
                reg.read_string_value(['common', 'hsm'], 'privkeylabel').value
        except:
            def_privkeylabel = "evote_key"
    else:
        def_privkeylabel = "evote_key"

    priv_key_label = uiutil.ask_string(\
                    "Sisesta privaatvõtme nimi", None, None, def_privkeylabel)

    if reg.check(['common', 'hsm', 'pkcs11']):
        try:
            def_pkcs11 = \
                reg.read_string_value(['common', 'hsm'], 'pkcs11').value
        except:
            def_pkcs11 = "/usr/lunasa/lib/libCryptoki2_64.so"
    else:
        def_pkcs11 = "/usr/lunasa/lib/libCryptoki2_64.so"

    pkcs11_path = uiutil.ask_file_name(\
                    "Sisesta PKCS11 teegi asukoht", def_pkcs11)

    cmd = "%s set %s %s %s" % \
                (SCRIPT_CONFIG_HSM, token_name, priv_key_label, pkcs11_path)
    os.system(cmd)

def do_set_hts_conf():

    reg = Election().get_root_reg()
    if reg.check(['common', 'htsip']):
        try:
            def_ip_port = reg.read_ipaddr_value(\
                                        ['common'], 'htsip').value.split(":")
            def_ip = def_ip_port[0]
            if len(def_ip_port) > 1:
                try:
                    def_port = int(def_ip_port[-1])
                except ValueError:
                    def_port = 80
            else:
                def_port = 80
        except:
            def_ip = None
            def_port = 80
    else:
        def_ip = None
        def_port = 80

    hts_ip = uiutil.ask_string("Sisesta HTSi IP aadress", None, None, def_ip)
    hts_port = uiutil.ask_int("Sisesta HTSi port", def_port, 0, 65535)

    try:
        def_url = Election().get_hts_path()
    except:
        def_url = "/hts.cgi"
    hts_url = uiutil.ask_string("Sisesta HTSi URL", None, None, def_url)

    try:
        def_verify = Election().get_hts_verify_path()
    except:
        def_verify = "/hts-verify-vote.cgi"
    hts_verify = uiutil.ask_string("Sisesta HTSi hääle kontrolli URL", \
            None, None, def_verify)

    cmd = "%s set %s:%d %s %s" % (SCRIPT_CONFIG_HTH, hts_ip, hts_port, \
            hts_url, hts_verify)
    os.system(cmd)

def do_get_hts_conf():
    cmd = "%s get" % SCRIPT_CONFIG_HTH
    os.system(cmd)


def do_add_rights(elid):
    ik = uiutil.ask_id_num()
    right_str_list = []
    if Election().is_hes() or Election().is_hlr():
        right = uiutil.ask_int("Võimalikud volitused:\n " + \
            "\t(1) %s\n" % regrights.G_DESCS["VALIK"] + \
            "\t(2) %s\n" % regrights.G_DESCS["JAOSK"] + \
            "\t(3) Kõik volitused\n" + \
            "Vali volitus:", 3, 1, 3)
        if right == 1:
            right_str_list.append("VALIK")
        elif right == 2:
            right_str_list.append("JAOSK")
        elif right == 3:
            right_str_list.append("VALIK")
            right_str_list.append("JAOSK")
    elif Election().is_hts():
        right = uiutil.ask_int("Võimalikud volitused:\n " + \
            "\t(1) %s\n" % regrights.G_DESCS["TYHIS"] + \
            "\t(2) %s\n" % regrights.G_DESCS["JAOSK"] + \
            "\t(3) %s\n" % regrights.G_DESCS["VALIK"] + \
            "\t(4) Kõik volitused\n" + \
            "Vali volitus:", 4, 1, 4)
        if right == 1:
            right_str_list.append("TYHIS")
        elif right == 2:
            right_str_list.append("JAOSK")
        elif right == 3:
            right_str_list.append("VALIK")
        elif right == 4:
            right_str_list.append("TYHIS")
            right_str_list.append("JAOSK")
            right_str_list.append("VALIK")

    for i in right_str_list:
        cmd = "%s %s add %s %s" % (SCRIPT_REGRIGHTS, elid, ik, i)
        os.system(cmd)

def do_add_description(elid):
    ik = uiutil.ask_id_num()
    desc = uiutil.ask_string("Sisesta kirjeldus")
    cmd = "%s %s desc %s %s" % (SCRIPT_REGRIGHTS, elid, ik, desc)
    os.system(cmd)

def do_rem_rights(elid):
    ik = uiutil.ask_id_num()
    right_str = ""
    if Election().is_hes() or Election().is_hlr():
        right = uiutil.ask_int("Võimalikud volitused:\n " + \
            "\t(1) Valikute nimekirja laadija\n" + \
            "\t(2) Valimisjaoskondade nimekirja laadija\n" + \
            "Vali volitus:", 1, 1, 2)
        if right == 1:
            right_str = "VALIK"
        elif right == 2:
            right_str = "JAOSK"
    elif Election().is_hts():
        right = uiutil.ask_int("Võimalikud volitused:\n " + \
                "\t(1) Tühistus- ja ennistusnimekirja laadija\n" +
                "\t(2) Valimisjaoskondade nimekirja laadija\n" + \
                "Vali volitus:", 1, 1, 2)
        if right == 1:
            right_str = "TYHIS"
        elif right == 2:
            right_str = "JAOSK"
    if not uiutil.ask_yes_no("Kas oled kindel"):
        return
    cmd = "%s %s rem %s %s" % (SCRIPT_REGRIGHTS, elid, ik, right_str)
    os.system(cmd)

def do_rem_user_rights(elid):
    ik = uiutil.ask_id_num()
    if not uiutil.ask_yes_no("Kas oled kindel"):
        return
    cmd = "%s %s remuser %s" % (SCRIPT_REGRIGHTS, elid, ik)
    os.system(cmd)

def do_rem_all_rights(elid):
    if not uiutil.ask_yes_no("Kas oled kindel"):
        return
    cmd = "%s %s remall" % (SCRIPT_REGRIGHTS, elid)
    os.system(cmd)

def do_list_user_rights(elid):
    ik = uiutil.ask_id_num()
    cmd = "%s %s listuser %s" % (SCRIPT_REGRIGHTS, elid, ik)
    os.system(cmd)

def do_list_all_rights(elid):
    cmd = "%s %s listall" % (SCRIPT_REGRIGHTS, elid)
    os.system(cmd)

def do_check_configure():

    # pylint: disable-msg=R0912

    print 'Laetud konfiguratsiooniandmed:'
    if Election().count_questions() != 0:
        print '\tValimisidentifikaator(id) - olemas'
    else:
        print '\tValimisidentifikaator(id) - puudu'

    for elid in Election().get_questions():
        if Election().is_hes():
            if Election().is_config_server_elid_done(elid):
                print '\t"%s" jaosk., valik., häälet. failid - olemas' % elid
            else:
                print '\t"%s" jaosk., valik., häälet. failid - puudu' % elid
        elif Election().is_hts():
            if Election().is_config_server_elid_done(elid):
                print '\t"%s" jaosk., häälet. failid - olemas' % elid
            else:
                print '\t"%s" jaosk., häälet. failid - puudu' % elid
        elif Election().is_hlr():
            if Election().is_config_server_elid_done(elid):
                print '\t"%s" jaosk., valik. failid - olemas' % elid
            else:
                print '\t"%s" jaosk., valik. failid - puudu' % elid

    if Election().is_config_bdoc_done():
        print '\tSertifikaadid - olemas'
    else:
        print '\tSertifikaadid - puudu'

    if Election().is_hes():
        if Election().is_config_hth_done():
            print '\tHTSi konfiguratsioon - olemas'
        else:
            print '\tHTSi konfiguratsioon - puudu'
        if Election().is_config_mid_done():
            print '\tMobiil-ID konfiguratsioon - olemas'
        else:
            print '\tMobiil-ID konfiguratsioon - puudu'

    if Election().is_hts():
        if Election().is_config_verification_done():
            print '\tKontrollitavuse konfiguratsioon - olemas'
        else:
            print '\tKontrollitavuse konfiguratsioon - puudu'

    if Election().is_hlr():
        if Election().is_config_hsm_done():
            print '\tHSMi konfiguratsioon - olemas'
        else:
            print '\tHSMi konfiguratsioon - puudu'
        for elid in Election().get_questions():
            if Election().is_config_hlr_input_elid_done(elid):
                print '\t"%s" imporditud häälte fail - olemas' % elid
            else:
                print '\t"%s" imporditud häälte fail - puudu' % elid

def do_pre_start_counting_hes():
    if not uiutil.ask_yes_no("Kas oled kindel"):
        return
    Election().refuse_new_voters()
    print 'Kandidaatide nimekirjade väljastamine peatatud'

def do_cancel_pre_start_counting_hes():
    if not uiutil.ask_yes_no("Kas oled kindel"):
        return
    Election().restore_new_voters()
    print 'Kandidaatide nimekirjade väljastamine taastatud'

def do_backup():
    """Varundame olekupuu DVD-le.
    """
    import time

    print "Varundame olekupuu. Palun oota.."
    s_time = time.time()
    cd_burner = burner.DiskBurner(evcommon.burn_buff())

    try:
        if cd_burner.backup_dir(Election().get_root_reg().root, \
                (Election().is_hes() or Election().is_hts())):

            print 'Varundamise ettevalmistamine kestis : %s' % \
                    time.strftime("%H:%M:%S", \
                    time.gmtime(long(time.time() - s_time)))
            cd_burner.burn()
    finally:
        cd_burner.delete_files()
        print '\nVarundamine kestis kokku: %s' % time.strftime("%H:%M:%S", \
                time.gmtime(long(time.time() - s_time)))

def do_revoke(elid):
    revokef = uiutil.ask_file_name_from_cd(\
            "Sisesta tühistus-/ennistusnimekirja-faili asukoht")
    cmd = "%s %s %s" % (SCRIPT_HTS, elid, revokef)
    os.system(cmd)

def do_new_election():
    elid = uiutil.ask_election_id(Election().get_questions())
    eltype = uiutil.ask_int("Võimalikud valimiste tüübid:\n " + \
            "\t(0) %s\n" % evcommon.G_TYPES[0] + \
            "\t(1) %s\n" % evcommon.G_TYPES[1] + \
            "\t(2) %s\n" % evcommon.G_TYPES[2] + \
            "\t(3) %s\n" % evcommon.G_TYPES[3] + \
            "Sisesta valimiste tüüp:", 0, 0, 3)

    if Election().is_hts():
        description = uiutil.ask_string("Sisesta valimiste kirjeldus", ".+", \
            "Valimiste kirjeldus peab sisaldama vähemalt ühte sümbolit")
    else:
        description = elid
    cmd = '%s %s %d "%s"' % (SCRIPT_INIT_CONF, elid, eltype, description)
    os.system(cmd)

def restart_apache():
    import subprocess

    prompt = "Palun sisestage veebiserveri taaskäivitamiseks parool: "
    retcode = subprocess.call(\
            ["sudo", "-p", prompt, "service", "apache2", "restart"])
    if retcode == 0:
        print "Veebiserver edukalt taaskäivitatud"
    elif retcode == 1:
        print "Probleem taaskäivitamisel, vale parool?"
    else:
        print "Probleem taaskäivitamisel, vea kood on ", retcode

def do_bdoc_conf_hes():
    if do_bdoc_conf():
        restart_apache()

def do_bdoc_conf():
    bdoc_conf = uiutil.ask_dir_name(\
        "Sisesta sertifikaatide konfiguratsioonipuu asukoht")
    cmd = "%s %s" % (SCRIPT_CONFIG_DIGIDOC, bdoc_conf)
    ret = os.system(cmd)
    if ret == 0:
        return True
    return False

def do_enable_voters_list():
    Election().toggle_check_voters_list(True)
    print "Hääletajate nimekirja kontroll lubatud\n"

def do_disable_voters_list():
    Election().toggle_check_voters_list(False)
    print "Hääletajate nimekirja kontroll keelatud\n"

def do_install():

    install_file = \
        uiutil.ask_file_name_from_cd("Sisesta paigaldusfaili asukoht")

    cmd = "%s verify %s" % (SCRIPT_INSTALL_SRV, install_file)
    ret = os.system(cmd)

    if not ret == 0:
        return

    if not uiutil.ask_yes_no("Kas paigaldame valimised?"):
        return

    cmd = "%s install %s" % (SCRIPT_INSTALL_SRV, install_file)
    os.system(cmd)

def do_hlr_conf(elid):
    station_file = \
        uiutil.ask_file_name_from_cd("Sisesta jaoskondade-faili asukoht")
    choices_file = \
        uiutil.ask_file_name_from_cd("Sisesta valikute-faili asukoht")
    cmd = "%s %s %s %s %s" % (SCRIPT_CONFIG_SRV, evcommon.APPTYPE_HLR, \
                            elid, station_file, choices_file)
    os.system(cmd)

def do_import_votes(elid):
    votes_file = \
            uiutil.ask_file_name_from_cd("Sisesta häälte-faili asukoht")
    cmd = "%s %s %s" % (SCRIPT_CONFIG_HLR_INPUT, elid, votes_file)
    os.system(cmd)

def do_hes_conf(elid):
    station_file = \
        uiutil.ask_file_name_from_cd("Sisesta jaoskondade-faili asukoht")
    choices_file = \
        uiutil.ask_file_name_from_cd("Sisesta valikute-faili asukoht")
    elector_file = \
        uiutil.ask_file_name_from_cd("Sisesta valijate-faili asukoht")
    cmd = "%s %s %s %s %s %s" % (SCRIPT_CONFIG_SRV, evcommon.APPTYPE_HES, \
            elid, station_file, elector_file, choices_file)
    os.system(cmd)

def do_hts_conf(elid):
    station_file = \
        uiutil.ask_file_name_from_cd("Sisesta jaoskondade-faili asukoht")
    choices_file = \
        uiutil.ask_file_name_from_cd("Sisesta valikute-faili asukoht")
    elector_file = \
        uiutil.ask_file_name_from_cd("Sisesta valijate-faili asukoht")
    cmd = "%s %s %s %s %s %s" % (SCRIPT_CONFIG_SRV, evcommon.APPTYPE_HTS, \
                            elid, station_file, elector_file, choices_file)
    os.system(cmd)

def do_load_electors(elid):
    elec_f = uiutil.ask_file_name_from_cd("Sisesta valijate-faili asukoht")
    cmd = "%s %s %s" % (SCRIPT_APPLY_CHANGES, elid, elec_f)
    os.system(cmd)

def do_replace_candidates(elid):
    if not uiutil.ask_yes_no("Kas oled kindel"):
        return
    if not uiutil.ask_yes_no("Valikute nimekirja väljavahetamisel " + \
            "kustutakse eelmine nimekiri.\nKas jätkan"):
        return
    elec_f = uiutil.ask_file_name_from_cd("Sisesta valikute-faili asukoht")
    cmd = "%s %s %s" % (SCRIPT_REPLACE_CANDIDATES, elid, elec_f)
    os.system(cmd)

def do_view_election_description(elid):
    el_reg = Election().get_sub_reg(elid)
    try:
        description = \
                el_reg.read_string_value(['common'], 'description').value
    except IOError:
        description = uiutil.NOT_DEFINED_STR
    except LookupError:
        description = uiutil.NOT_DEFINED_STR
    print "Valimiste %s kirjeldus: %s\n" % (elid, description)

def do_create_status_report():
    print "Palun oota, genereerin aruannet.."
    cmd = "%s status" % SCRIPT_HTSALL
    os.system(cmd)

def do_create_status_report_no_verify():

    # pylint: disable-msg=C0103

    print "Palun oota, genereerin aruannet..."
    cmd = "%s statusnoverify" % SCRIPT_HTSALL
    os.system(cmd)

def do_count_votes(elid):
    import evfiles
    import evlog

    log4 = evlog.Logger()
    log4.set_logs(evfiles.log4_file(elid).path())
    if log4.lines_in_file() > 3:
        print "Log4 fail ei ole tühi. Ei saa jätkata."
        return

    log5 = evlog.Logger()
    log5.set_logs(evfiles.log5_file(elid).path())
    if log5.lines_in_file() > 3:
        print "Log5 fail ei ole tühi. Ei saa jätkata."
        return

    if not uiutil.ask_yes_no("Kas oled kindel"):
        print "Katkestame häälte lugemise"
        return
    pin = uiutil.ask_password("Sisesta partitsiooni PIN: ", \
            "Sisestatud PIN oli tühi!")
    cmd = "%s %s %s" % (SCRIPT_HLR, elid, pin)
    os.system(cmd)

def do_del_election():
    elid = uiutil.ask_del_election_id(Election().get_questions())
    Election().delete_question(elid)

def do_restore_init_status():
    if not uiutil.ask_yes_no("Kas oled kindel"):
        return

    if not uiutil.ask_yes_no("Initsialiseerimisel kustutatakse " + \
        "antud hääled.\nKas jätkan"):
        return

    Election().restore_init_status()
    ElectionState().init()

def do_restore():
    """Taastame olekupuu varukoopiast.
    """

    if not uiutil.ask_yes_no("Kas oled kindel"):
        return
    if not uiutil.ask_yes_no("Olekupuu taastamisel varukoopiast " + \
            "kustutatakse vana olekupuu.\nKas jätkan"):
        return

    import time
    s_time = time.time()

    try:
        restorer = burner.Restorer(os.path.abspath(\
                os.path.join(evcommon.EVREG_CONFIG,\
                '..', 'restore-' + time.strftime("%Y%m%d%H%M%S"))))

        while 1:
            backup_dir = uiutil.ask_dir_name(\
                    "Sisesta kataloog, kus asuvad varukoopia failid")
            restorer.add_chunks(backup_dir)

            if not uiutil.ask_yes_no(\
                    "Kas soovid veel laadida varukoopia faile"):
                break

        if restorer.chunk_count() != 0:
            print "Taastame olekupuu varukoopiast. Palun oota.."
            restorer.restore(Election().get_root_reg().root)
        else:
            print 'Pole ühtegi varukoopia faili. Loobun taastamisest.'
    finally:
        print 'Kustutan ajutisi faile. Palun oota..'
        restorer.delete_files()

        if restorer.chunk_count() != 0:
            print '\nOlekupuu taastamine kestis: %s' % \
                    time.strftime("%H:%M:%S", \
                    time.gmtime(long(time.time() - s_time)))

def do_change_election_description(elid):
    description = uiutil.ask_string("Sisesta valimiste kirjeldus")
    el_reg = Election().get_sub_reg(elid)
    el_reg.create_string_value(['common'], 'description', description)

def do_view_status_report():
    import evfiles
    report_file = evfiles.statusreport_file().path()
    cmd = "%s %s" % (PROGRAM_LESS, report_file)
    os.system(cmd)

def do_verification_conf():
    try:
        def_time = Election().get_verification_time()
    except (IOError, LookupError):
        def_time = 30

    try:
        def_count = Election().get_verification_count()
    except (IOError, LookupError):
        def_count = 3

    verif_time = uiutil.ask_int("Sisesta taimaut hääle kontrollimiseks minutites", \
            def_time, 1)
    verif_count = uiutil.ask_int("Sisesta lubatud arv kordusi hääle kontrollimiseks", \
            def_count, 1)

    Election().set_verification_time(verif_time)
    Election().set_verification_count(verif_count)


def do_get_verification_conf():
    try:
        def_time = Election().get_verification_time()
    except (IOError, LookupError):
        def_time = "puudub"

    try:
        def_count = Election().get_verification_count()
    except (IOError, LookupError):
        def_count = "puudub"

    print "Taimaut hääle kontrollimiseks minutites: %s" % def_time
    print "Lubatud arv kordusi hääle kontrollimiseks: %s" % def_count

def do_schedule_autostart():
    time = uiutil.ask_time("Sisesta valimiste automaatse algusaja kuupäev ja kellaaeg")
    autocmd.schedule(autocmd.COMMAND_START, time)

def do_unschedule_autostart():
    job, time = autocmd.scheduled(autocmd.COMMAND_START)
    if uiutil.ask_yes_no("Kas soovid kustutada automaatse algusaja %s" % time, \
            uiutil.ANSWER_NO):
        autocmd.unschedule(autocmd.COMMAND_START, job)

def do_schedule_autostop():

    time = uiutil.ask_time("Sisesta nimekirjade väljastamise automaatse " \
            "lõpetamise kuupäev ja kellaaeg")

    def_grace = autocmd.stop_grace_period()
    if not def_grace:
        def_grace = 15

    grace_time = uiutil.ask_int("Sisesta ajavahemik nimekirjade väljastamise " \
            "automaatse lõpu\nja häälte vastuvõtmise automaatse lõpu vahel " \
            "minutites", def_grace, 1)
    autocmd.set_stop_grace_period(grace_time)

    autocmd.schedule(autocmd.COMMAND_PREPARE_STOP, time)

def do_unschedule_autostop():
    prepare = autocmd.scheduled(autocmd.COMMAND_PREPARE_STOP)
    stop = autocmd.scheduled(autocmd.COMMAND_STOP)
    time = prepare[1] if prepare else stop[1]
    if uiutil.ask_yes_no("Kas soovid kustutada automaatse lõpuaja %s" % time, \
            uiutil.ANSWER_NO):
        if prepare:
            autocmd.unschedule(autocmd.COMMAND_PREPARE_STOP, prepare[0])
        if stop:
            autocmd.unschedule(autocmd.COMMAND_STOP, stop[0])

# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = uiutil
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import re
import os
import time
import getpass
import shutil
# tab-completioni jaoks vajalikud moodulid
import curses.ascii
import struct
import fcntl
import termios
import glob
import sys
import tty

NOT_DEFINED_STR = "pole määratud"

PRINT_PROGRAM = "lpr"

ANSWER_YES = "jah"
ANSWER_NO = "ei"

TMPFILE_PREFIX = "evotetmp"


def print_file_list(file_list):
    if len(file_list) > 0:
        cmd = "%s %s" % (PRINT_PROGRAM, " ".join(file_list))
        os.system(cmd)
    return


def del_tmp_files():
    cmd = "rm -f /tmp/%s*" % TMPFILE_PREFIX
    os.system(cmd)


def clrscr():
    os.system("clear")


def ask_del_election_id(election_ids):
    """
    Küsib operaatorilt valimiste ID-d, mida kustutda.
    @return: valimiste identifikaator
    """
    do = 1
    while do:
        elid = ask_string(\
            "Sisestage kustutatav valimiste identifikaator", "^\w{1,28}$", \
                "Valimiste identifikaator peab olema 1..28 tähte/numbrit")
        if elid in election_ids:
            do = 0
        else:
            print 'Valimiste identifikaatorit "%s" ei ole' % elid
    return elid


def ask_election_id(election_ids):
    """
    Küsib operaatorilt valimiste ID-d. Duplikaatite kontrollime
    listilst election_ids
    @return: valimiste identifikaator
    """
    do = 1
    while do:
        elid = ask_string("Sisestage valimiste identifikaator", \
            "^\w{1,28}$", \
            "Valimiste identifikaator peab olema 1..28 tähte/numbrit")
        do = 0
        for i in range(len(election_ids)):
            if elid == election_ids[i]:
                print "Valimiste identifikaator pole unikaalne"
                do = 1
                break
    return elid


def ask_id_num():
    """
    Küsib operaatorilt isikukoodi.
    @return: isikukood
    """
    return ask_string("Sisesta isikukood", "^\d{11,11}$", \
        "Isikukood peab koosnema 11-st numbrist")


def ask_file_name(prefix, default=None):
    """
    Küsib operaatorilt faili nime.
    @return: faili nimi
    """
    while True:
        filename = ask_string(prefix, None, None, default)
        if not check_file(filename):
            print ("Faili %s ei eksisteeri või on tegu kataloogiga" % \
                    filename)
            continue
        break
    return filename


def ask_dir_name(prefix, default=None):
    """
    Küsib operaatorilt kataloogi nime.
    @return: kataloogi nimi
    """
    while True:
        dirname = ask_string(prefix, None, None, default)
        if not check_dir(dirname):
            print ("Kataloogi %s ei eksisteeri või on tegu failiga" % \
                    dirname)
            continue
        break
    return dirname


def ask_file_name_from_cd(prefix, default=None):
    """
    Küsib operaatorilt faili nime. Faili kopeeritakse /tmp/
    kataloogi spets prefikiga, et võimaldada CD vahetust dialoogi ajal.
    @return: faili nimi
    """
    while True:
        file_path = ask_string(prefix, None, None, default)
        if not check_file(file_path):
            print "Faili %s ei eksisteeri või on tegu katalooiga" % file_path
            continue
        file_name = os.path.split(file_path)[1]
        time_str = time.strftime("%Y%m%d%H%M%S")
        tmp_file = os.path.join("/", "tmp", "%s_%s_%s" % \
            (TMPFILE_PREFIX, time_str, file_name))
        print "Palun oota. Laen faili.."
        try:
            shutil.copyfile(file_path, tmp_file)
            if check_file(file_path + ".sha256"):
                shutil.copyfile(file_path + ".sha256", tmp_file + ".sha256")
            break
        except Exception, what:
            print "Viga! Faili ei õnnestu laadida: %s." % str(what)
    return tmp_file


def ask_yes_no(prefix, default=None):
    while 1:
        if default != None:
            yn = raw_input("%s (%s/%s) [%s]? " % \
                (prefix, ANSWER_YES, ANSWER_NO, default))
        else:
            yn = raw_input("%s (%s/%s)? " % \
                (prefix, ANSWER_YES, ANSWER_NO))
        yn = yn.strip().lower()
        if len(yn) > 0 and ANSWER_YES.find(yn) == 0:
            return 1
        if len(yn) > 0 and ANSWER_NO.find(yn) == 0:
            return 0
        if len(yn) == 0:
            if default == ANSWER_YES:
                return 1
            elif default == ANSWER_NO:
                return 0
        print "Palun vasta %s või %s!" % (ANSWER_YES, ANSWER_NO)


def check_file(path):
    return os.path.isfile(path)


def check_dir(path):
    return os.path.isdir(path)


def ask_int(prefix, default, minval=None, maxval=None):
    while 1:
        i = raw_input("%s [%d]: " % (prefix, default))
        i = i.strip()
        if len(i) == 0:
            return default
        try:
            retval = int(i)
        except ValueError:
            print "Palun sisesta täisarv"
            continue
        if minval != None and retval < minval:
            print "Palun sisesta täisarv, mis on võrdne või suurem " + \
                "kui %d" % minval
            continue
        if maxval != None and retval > maxval:
            print "Palun sisesta täisarv, mis on võrdne või väiksem " + \
                "kui %d" % maxval
            continue
        return retval

def ask_time(prefix, format="%d.%m.%Y %H:%M", default=None):
    while 1:
        if default == None:
            tstr = raw_input("%s: " % prefix)
        else:
            tstr = raw_input("%s [%s]: " % (prefix, time.strftime(format, default)))
        tstr = tstr.strip()
        if len(tstr) == 0 and default:
            return default
        try:
            return time.strptime(tstr, format)
        except ValueError as e:
            print "Palun sisesta kuupäev ja kellaaeg kujul %s" % format
            continue

def ask_string(prefix, pattern=None, err_text=None,
        default=None):
    """
    Küsib operaatorilt küsimuse prefix. Sisestatud vastus peab
    kattuma mustriga pattern, vastasel korral näidatakse
    veateksti err_text ja uuele ringile.
    @return: sisestatud string
    """
    while 1:
        if default == None:
            #in_str = raw_input("%s: " % prefix)
            in_str = _get_string("%s: " % prefix)
        else:
            #in_str = raw_input("%s [%s]: " % (prefix, default))
            in_str = _get_string("%s [%s]: " % (prefix, default))
        in_str = in_str.strip()
        if len(in_str) < 1:
            if default != None:
                in_str = default
            else:
                if err_text != None:
                    print err_text
                continue
        if (pattern != None):
            if not re.compile(pattern).match(in_str):
                print err_text
                continue
            else:
                return in_str
        else:
            return in_str


def ask_password(prefix, err_text):
    """
    Küsib operaatorilt parooli.
    @return: sisestatud string
    """
    while 1:
        in_str = getpass.getpass(prefix)
        in_str = in_str.strip()
        if len(in_str) < 1:
            print err_text
            continue
        else:
            return in_str


def _get_string(prefix):
    """
    Küsib stdio'st stringi. TAB klahv toimib autocomplete'na.
    @return sisestatud string
    """
    inp = ""

    sys.stdout.write(prefix)
    _to_new_line(prefix, inp)

    ch = _get_char()
    # Kuni sisestatakse "Enter"
    while ord(ch) != curses.ascii.CR:
        if ord(ch) == curses.ascii.EOT:
            # CTRL-D katkestab
            raise EOFError()
        if ord(ch) == curses.ascii.TAB:
            # TAB-completion
            comp = _complete(inp)
            if len(comp) == len(inp):
                # Autocomplete ei aita, pakume faile
                files = _possible(inp)
                if len(files) > 0:
                    print _display(files)
                    sys.stdout.write(prefix)
                    sys.stdout.write(inp)
                    _to_new_line(prefix, inp)
            else:
                # Autocomplete
                sys.stdout.write(comp[len(inp):])
                inp = inp + comp[len(inp):]
                _to_new_line(prefix, inp)
        elif ord(ch) == curses.ascii.DEL and len(inp) > 0:
            # Backspacega kustutamine
            if _del_char(prefix, inp):
                inp = inp[:-1]
        #elif curses.ascii.isascii(ch) and curses.ascii.isprint(ch):
        else:
            # Uue sümboli sisestamine
            sys.stdout.write(ch)
            inp = inp + ch
            _to_new_line(prefix, inp)
        ch = _get_char()

    # Reavahetus lõppu
    sys.stdout.write(chr(curses.ascii.LF))
    return inp


def _to_new_line(prefix, inp):
    """
    Kui sisestamisel satuti rea loppu, siis kursor uuele reale
    """
    _, _w = _term_size()
    # et saaks õige kuvatava tähtede arvu
    prefix_len = len(unicode(prefix, "utf8"))
    if (prefix_len + len(inp)) % _w == 0 and \
    prefix_len + len(inp) > 0:
        fd = sys.stdin.fileno()
        # vana seadistus
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            _go_down()
            for _ in range(0, _w):
                _go_left()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def _del_char(prefix, inp):
    """
    Kursor kas samm vasakule või rida ülespoole ja lõppu.
    Tagastab:
        False - midagi ei juhtunud
        True - kustutati symbol
    """
    _, _w = _term_size()
    # et saaks õige kuvatava tähtede arvu
    prefix_len = len(unicode(prefix, "utf8"))
    if (prefix_len + len(inp)) % _w == 0 and \
    prefix_len + len(inp) > 0:
        up_and_right = True
    elif len(inp) > 0:
        up_and_right = False
    else:
        return False

    fd = sys.stdin.fileno()
    # vana seadistus
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        if up_and_right:
            _go_up()
            for _ in range(0, _w):
                _go_right()
            sys.stdout.write(chr(curses.ascii.SP))
            _go_left()
            # Samm tagasi ja kirjutame üle, et kursor
            # saaks õigele kohale
            if len(inp) > 1:
                sys.stdout.write(inp[-2])
            else:
                sys.stdout.write(prefix[-1])
        else:
            _go_left()
            sys.stdout.write(chr(curses.ascii.SP))
            _go_left()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return True


def _go_left():
    sys.stdout.write(chr(27))
    sys.stdout.write(chr(91))
    sys.stdout.write(chr(68))


def _go_right():
    sys.stdout.write(chr(27))
    sys.stdout.write(chr(91))
    sys.stdout.write(chr(67))


def _go_up():
    sys.stdout.write(chr(27))
    sys.stdout.write(chr(91))
    sys.stdout.write(chr(65))


def _go_down():
    sys.stdout.write(chr(curses.ascii.LF))


def _get_char():
    """
    Küsib stdio'st üksiku sümboli seda ekraanile kuvamata
    """
    fd = sys.stdin.fileno()
    # vana seadistus
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
        #ch = os.read(fd, 1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch


def _complete(string):
    """
    Tagastab argumendina antud stringi, millele on appenditud
    võimalik completion. Kui completionit ei leidu, siis
    tagastatakse esialgne string
    """
    if len(string) == 0:
        return "/"
    if string[0] != "/":
        # abi ainult fullpathi leidmisel
        return string
    if '*' not in string:
        string += "*"

    _g = glob.glob(string)
    if len(_g) == 0:
        _s = string[:-1]
    elif len(_g) == 1:
        _s = _g[0]
        if os.path.isdir(_s) and _s[-1] != "/":
            _s += "/"
        if os.path.isfile(_s) and _s[-1] != " ":
            _s += " "
    else:
        chars_lst = zip(*_g)
        for i in range(0, len(chars_lst)):
            chars = chars_lst[i]
            if min(chars) != max(chars):
                j = i
                break
            else:
                j = min([len(_s) for _s in _g])
        _s = _g[0][:j]
    _s = os.path.expanduser(_s)
    return _s


def _possible(string):
    """
    Tagastab listi võimalikest failidest, mida järgnevalt valida.
    """
    if string[0] != '/':
        return []

    if '*' not in string:
        string += "*"

    _g = glob.glob(string)
    lst = []
    for file_name in _g:
        lst.append(file_name.split('/')[-1:][0])
    return lst


def _display(files):
    """
    Tagastab listis olevatest failidest moodustatud stringi, mis
    on kuvamiseks sobival kujul. Kirjed on sorteeritud ning
    arvestatakse terminaliakna suurust.
    """
    files.sort()
    max_len = 0
    for file_name in files:
        if len(file_name) > max_len:
            max_len = len(file_name)
    max_len = max_len + 2
    cols = _term_size()[1] / max_len
    rows = len(files) / cols
    if len(files) % cols != 0:
        rows = rows + 1

    table = "\n"
    for i in range(0, rows):
        for j in range(0, cols):
            idx = i + j * rows
            if idx < len(files):
                table = table + files[i + j * rows].ljust(max_len)
        table = table + '\n'
    return table[:-1]


def _term_size():
    """
    Tagastab tuple (height, width) terminaliakna mõõtmetest.
    """
    _h, _w = struct.unpack(\
        "hhhh", fcntl.ioctl(0, termios.TIOCGWINSZ, "\000" * 8))[0:2]
    return _h, _w



# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = birthday
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import time

def date_today():
    # tm_year, tm_mon, tm_mday, tm_hour, tm_min, tm_sec,
    # tm_wday, tm_yday, tm_isdst
    now = time.localtime()
    return [now[0], now[1], now[2]]


def date_birthday(ik):
    lst = []

    # aasta
    if ik[0] == '1' or ik[0] == '2':
        lst.append(int('18' + ik[1:3]))
    elif ik[0] == '3' or ik[0] == '4':
        lst.append(int('19' + ik[1:3]))
    else:
        lst.append(int('20' + ik[1:3]))
    # kuu
    lst.append(int(ik[3:5]))
    # p2ev
    lst.append(int(ik[5:7]))

    return lst


def is_18(ik):
    today = date_today()
    birthday = date_birthday(ik)

    if today[0] - birthday[0] > 18:
        return True
    if today[0] - birthday[0] < 18:
        return False

    # today[0] - birthday[0] == 18, v6rrelda kuup2evasid
    if today[1] > birthday[1]:
        return True
    if today[1] < birthday[1]:
        return False

    # today[1] == birthday[1], v6rrelda p2evasid
    if today[2] >= birthday[2]:
        return True

    # today[2] < birthday[2]. Isik pole veel t2naseks 18 saanud
    # (saab t2na v6i hiljem).
    return False


if __name__ == '__main__':
    print 'No main'

# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = DigiDocService_client
##################################################
# file: DigiDocService_client.py
#
# client stubs generated by "ZSI.generate.wsdl2python.WriteServiceModule"
#     /usr/bin/wsdl2py --complexType https://www.openxades.org:9443/?wsdl
#
##################################################

from DigiDocService_types import *
import urlparse, types
from ZSI.TCcompound import ComplexType, Struct
from ZSI import client
from ZSI.schema import GED, GTD
import ZSI
from ZSI.generate.pyclass import pyclass_type

# Locator
class DigiDocServiceLocator:
    DigiDocService_address = "https://www.openxades.org:9443/DigiDocService"
    def getDigiDocServiceAddress(self):
        return DigiDocServiceLocator.DigiDocService_address
    def getDigiDocService(self, url=None, **kw):
        return DigiDocServiceSOAP(url or DigiDocServiceLocator.DigiDocService_address, **kw)

# Methods
class DigiDocServiceSOAP:
    def __init__(self, url, **kw):
        kw.setdefault("readerclass", None)
        kw.setdefault("writerclass", None)
        # no resource properties
        self.binding = client.Binding(url=url, **kw)
        # no ws-addressing

    # op: StartSession
    def StartSession(self, request, **kw):
        if isinstance(request, StartSession) is False:
            raise TypeError, "%s incorrect request type" % (request.__class__)
        # no input wsaction
        self.binding.Send(None, None, request, soapaction="", encodingStyle="http://schemas.xmlsoap.org/soap/encoding/", **kw)
        # no output wsaction
        typecode = Struct(pname=None, ofwhat=StartSessionResponse.typecode.ofwhat, pyclass=StartSessionResponse.typecode.pyclass)
        response = self.binding.Receive(typecode)
        return response

    # op: CloseSession
    def CloseSession(self, request, **kw):
        if isinstance(request, CloseSession) is False:
            raise TypeError, "%s incorrect request type" % (request.__class__)
        # no input wsaction
        self.binding.Send(None, None, request, soapaction="", encodingStyle="http://schemas.xmlsoap.org/soap/encoding/", **kw)
        # no output wsaction
        typecode = Struct(pname=None, ofwhat=CloseSessionResponse.typecode.ofwhat, pyclass=CloseSessionResponse.typecode.pyclass)
        response = self.binding.Receive(typecode)
        return response

    # op: CreateSignedDoc
    def CreateSignedDoc(self, request, **kw):
        if isinstance(request, CreateSignedDoc) is False:
            raise TypeError, "%s incorrect request type" % (request.__class__)
        # no input wsaction
        self.binding.Send(None, None, request, soapaction="", encodingStyle="http://schemas.xmlsoap.org/soap/encoding/", **kw)
        # no output wsaction
        typecode = Struct(pname=None, ofwhat=CreateSignedDocResponse.typecode.ofwhat, pyclass=CreateSignedDocResponse.typecode.pyclass)
        response = self.binding.Receive(typecode)
        return response

    # op: AddDataFile
    def AddDataFile(self, request, **kw):
        if isinstance(request, AddDataFile) is False:
            raise TypeError, "%s incorrect request type" % (request.__class__)
        # no input wsaction
        self.binding.Send(None, None, request, soapaction="", encodingStyle="http://schemas.xmlsoap.org/soap/encoding/", **kw)
        # no output wsaction
        typecode = Struct(pname=None, ofwhat=AddDataFileResponse.typecode.ofwhat, pyclass=AddDataFileResponse.typecode.pyclass)
        response = self.binding.Receive(typecode)
        return response

    # op: RemoveDataFile
    def RemoveDataFile(self, request, **kw):
        if isinstance(request, RemoveDataFile) is False:
            raise TypeError, "%s incorrect request type" % (request.__class__)
        # no input wsaction
        self.binding.Send(None, None, request, soapaction="", encodingStyle="http://schemas.xmlsoap.org/soap/encoding/", **kw)
        # no output wsaction
        typecode = Struct(pname=None, ofwhat=RemoveDataFileResponse.typecode.ofwhat, pyclass=RemoveDataFileResponse.typecode.pyclass)
        response = self.binding.Receive(typecode)
        return response

    # op: GetSignedDoc
    def GetSignedDoc(self, request, **kw):
        if isinstance(request, GetSignedDoc) is False:
            raise TypeError, "%s incorrect request type" % (request.__class__)
        # no input wsaction
        self.binding.Send(None, None, request, soapaction="", encodingStyle="http://schemas.xmlsoap.org/soap/encoding/", **kw)
        # no output wsaction
        typecode = Struct(pname=None, ofwhat=GetSignedDocResponse.typecode.ofwhat, pyclass=GetSignedDocResponse.typecode.pyclass)
        response = self.binding.Receive(typecode)
        return response

    # op: GetSignedDocInfo
    def GetSignedDocInfo(self, request, **kw):
        if isinstance(request, GetSignedDocInfo) is False:
            raise TypeError, "%s incorrect request type" % (request.__class__)
        # no input wsaction
        self.binding.Send(None, None, request, soapaction="", encodingStyle="http://schemas.xmlsoap.org/soap/encoding/", **kw)
        # no output wsaction
        typecode = Struct(pname=None, ofwhat=GetSignedDocInfoResponse.typecode.ofwhat, pyclass=GetSignedDocInfoResponse.typecode.pyclass)
        response = self.binding.Receive(typecode)
        return response

    # op: GetDataFile
    def GetDataFile(self, request, **kw):
        if isinstance(request, GetDataFile) is False:
            raise TypeError, "%s incorrect request type" % (request.__class__)
        # no input wsaction
        self.binding.Send(None, None, request, soapaction="", encodingStyle="http://schemas.xmlsoap.org/soap/encoding/", **kw)
        # no output wsaction
        typecode = Struct(pname=None, ofwhat=GetDataFileResponse.typecode.ofwhat, pyclass=GetDataFileResponse.typecode.pyclass)
        response = self.binding.Receive(typecode)
        return response

    # op: GetSignersCertificate
    def GetSignersCertificate(self, request, **kw):
        if isinstance(request, GetSignersCertificate) is False:
            raise TypeError, "%s incorrect request type" % (request.__class__)
        # no input wsaction
        self.binding.Send(None, None, request, soapaction="", encodingStyle="http://schemas.xmlsoap.org/soap/encoding/", **kw)
        # no output wsaction
        typecode = Struct(pname=None, ofwhat=GetSignersCertificateResponse.typecode.ofwhat, pyclass=GetSignersCertificateResponse.typecode.pyclass)
        response = self.binding.Receive(typecode)
        return response

    # op: GetNotarysCertificate
    def GetNotarysCertificate(self, request, **kw):
        if isinstance(request, GetNotarysCertificate) is False:
            raise TypeError, "%s incorrect request type" % (request.__class__)
        # no input wsaction
        self.binding.Send(None, None, request, soapaction="", encodingStyle="http://schemas.xmlsoap.org/soap/encoding/", **kw)
        # no output wsaction
        typecode = Struct(pname=None, ofwhat=GetNotarysCertificateResponse.typecode.ofwhat, pyclass=GetNotarysCertificateResponse.typecode.pyclass)
        response = self.binding.Receive(typecode)
        return response

    # op: GetNotary
    def GetNotary(self, request, **kw):
        if isinstance(request, GetNotary) is False:
            raise TypeError, "%s incorrect request type" % (request.__class__)
        # no input wsaction
        self.binding.Send(None, None, request, soapaction="", encodingStyle="http://schemas.xmlsoap.org/soap/encoding/", **kw)
        # no output wsaction
        typecode = Struct(pname=None, ofwhat=GetNotaryResponse.typecode.ofwhat, pyclass=GetNotaryResponse.typecode.pyclass)
        response = self.binding.Receive(typecode)
        return response

    # op: GetTSACertificate
    def GetTSACertificate(self, request, **kw):
        if isinstance(request, GetTSACertificate) is False:
            raise TypeError, "%s incorrect request type" % (request.__class__)
        # no input wsaction
        self.binding.Send(None, None, request, soapaction="", encodingStyle="http://schemas.xmlsoap.org/soap/encoding/", **kw)
        # no output wsaction
        typecode = Struct(pname=None, ofwhat=GetTSACertificateResponse.typecode.ofwhat, pyclass=GetTSACertificateResponse.typecode.pyclass)
        response = self.binding.Receive(typecode)
        return response

    # op: GetTimestamp
    def GetTimestamp(self, request, **kw):
        if isinstance(request, GetTimestamp) is False:
            raise TypeError, "%s incorrect request type" % (request.__class__)
        # no input wsaction
        self.binding.Send(None, None, request, soapaction="", encodingStyle="http://schemas.xmlsoap.org/soap/encoding/", **kw)
        # no output wsaction
        typecode = Struct(pname=None, ofwhat=GetTimestampResponse.typecode.ofwhat, pyclass=GetTimestampResponse.typecode.pyclass)
        response = self.binding.Receive(typecode)
        return response

    # op: GetCRL
    def GetCRL(self, request, **kw):
        if isinstance(request, GetCRL) is False:
            raise TypeError, "%s incorrect request type" % (request.__class__)
        # no input wsaction
        self.binding.Send(None, None, request, soapaction="", encodingStyle="http://schemas.xmlsoap.org/soap/encoding/", **kw)
        # no output wsaction
        typecode = Struct(pname=None, ofwhat=GetCRLResponse.typecode.ofwhat, pyclass=GetCRLResponse.typecode.pyclass)
        response = self.binding.Receive(typecode)
        return response

    # op: GetSignatureModules
    def GetSignatureModules(self, request, **kw):
        if isinstance(request, GetSignatureModules) is False:
            raise TypeError, "%s incorrect request type" % (request.__class__)
        # no input wsaction
        self.binding.Send(None, None, request, soapaction="", encodingStyle="http://schemas.xmlsoap.org/soap/encoding/", **kw)
        # no output wsaction
        typecode = Struct(pname=None, ofwhat=GetSignatureModulesResponse.typecode.ofwhat, pyclass=GetSignatureModulesResponse.typecode.pyclass)
        response = self.binding.Receive(typecode)
        return response

    # op: PrepareSignature
    def PrepareSignature(self, request, **kw):
        if isinstance(request, PrepareSignature) is False:
            raise TypeError, "%s incorrect request type" % (request.__class__)
        # no input wsaction
        self.binding.Send(None, None, request, soapaction="", encodingStyle="http://schemas.xmlsoap.org/soap/encoding/", **kw)
        # no output wsaction
        typecode = Struct(pname=None, ofwhat=PrepareSignatureResponse.typecode.ofwhat, pyclass=PrepareSignatureResponse.typecode.pyclass)
        response = self.binding.Receive(typecode)
        return response

    # op: FinalizeSignature
    def FinalizeSignature(self, request, **kw):
        if isinstance(request, FinalizeSignature) is False:
            raise TypeError, "%s incorrect request type" % (request.__class__)
        # no input wsaction
        self.binding.Send(None, None, request, soapaction="", encodingStyle="http://schemas.xmlsoap.org/soap/encoding/", **kw)
        # no output wsaction
        typecode = Struct(pname=None, ofwhat=FinalizeSignatureResponse.typecode.ofwhat, pyclass=FinalizeSignatureResponse.typecode.pyclass)
        response = self.binding.Receive(typecode)
        return response

    # op: RemoveSignature
    def RemoveSignature(self, request, **kw):
        if isinstance(request, RemoveSignature) is False:
            raise TypeError, "%s incorrect request type" % (request.__class__)
        # no input wsaction
        self.binding.Send(None, None, request, soapaction="", encodingStyle="http://schemas.xmlsoap.org/soap/encoding/", **kw)
        # no output wsaction
        typecode = Struct(pname=None, ofwhat=RemoveSignatureResponse.typecode.ofwhat, pyclass=RemoveSignatureResponse.typecode.pyclass)
        response = self.binding.Receive(typecode)
        return response

    # op: GetVersion
    def GetVersion(self, request, **kw):
        if isinstance(request, GetVersion) is False:
            raise TypeError, "%s incorrect request type" % (request.__class__)
        # no input wsaction
        self.binding.Send(None, None, request, soapaction="", encodingStyle="http://schemas.xmlsoap.org/soap/encoding/", **kw)
        # no output wsaction
        typecode = Struct(pname=None, ofwhat=GetVersionResponse.typecode.ofwhat, pyclass=GetVersionResponse.typecode.pyclass)
        response = self.binding.Receive(typecode)
        return response

    # op: MobileSign
    def MobileSign(self, request, **kw):
        if isinstance(request, MobileSign) is False:
            raise TypeError, "%s incorrect request type" % (request.__class__)
        # no input wsaction
        self.binding.Send(None, None, request, soapaction="", encodingStyle="http://schemas.xmlsoap.org/soap/encoding/", **kw)
        # no output wsaction
        typecode = Struct(pname=None, ofwhat=MobileSignResponse.typecode.ofwhat, pyclass=MobileSignResponse.typecode.pyclass)
        response = self.binding.Receive(typecode)
        return response

    # op: GetStatusInfo
    def GetStatusInfo(self, request, **kw):
        if isinstance(request, GetStatusInfo) is False:
            raise TypeError, "%s incorrect request type" % (request.__class__)
        # no input wsaction
        self.binding.Send(None, None, request, soapaction="", encodingStyle="http://schemas.xmlsoap.org/soap/encoding/", **kw)
        # no output wsaction
        typecode = Struct(pname=None, ofwhat=GetStatusInfoResponse.typecode.ofwhat, pyclass=GetStatusInfoResponse.typecode.pyclass)
        response = self.binding.Receive(typecode)
        return response

    # op: MobileAuthenticate
    def MobileAuthenticate(self, request, **kw):
        if isinstance(request, MobileAuthenticate) is False:
            raise TypeError, "%s incorrect request type" % (request.__class__)
        # no input wsaction
        self.binding.Send(None, None, request, soapaction="", encodingStyle="http://schemas.xmlsoap.org/soap/encoding/", **kw)
        # no output wsaction
        typecode = Struct(pname=None, ofwhat=MobileAuthenticateResponse.typecode.ofwhat, pyclass=MobileAuthenticateResponse.typecode.pyclass)
        response = self.binding.Receive(typecode)
        return response

    # op: GetMobileAuthenticateStatus
    def GetMobileAuthenticateStatus(self, request, **kw):
        if isinstance(request, GetMobileAuthenticateStatus) is False:
            raise TypeError, "%s incorrect request type" % (request.__class__)
        # no input wsaction
        self.binding.Send(None, None, request, soapaction="", encodingStyle="http://schemas.xmlsoap.org/soap/encoding/", **kw)
        # no output wsaction
        typecode = Struct(pname=None, ofwhat=GetMobileAuthenticateStatusResponse.typecode.ofwhat, pyclass=GetMobileAuthenticateStatusResponse.typecode.pyclass)
        response = self.binding.Receive(typecode)
        return response

    # op: MobileCreateSignature
    def MobileCreateSignature(self, request, **kw):
        if isinstance(request, MobileCreateSignature) is False:
            raise TypeError, "%s incorrect request type" % (request.__class__)
        # no input wsaction
        self.binding.Send(None, None, request, soapaction="", encodingStyle="http://schemas.xmlsoap.org/soap/encoding/", **kw)
        # no output wsaction
        typecode = Struct(pname=None, ofwhat=MobileCreateSignatureResponse.typecode.ofwhat, pyclass=MobileCreateSignatureResponse.typecode.pyclass)
        response = self.binding.Receive(typecode)
        return response

    # op: GetMobileCreateSignatureStatus
    def GetMobileCreateSignatureStatus(self, request, **kw):
        if isinstance(request, GetMobileCreateSignatureStatus) is False:
            raise TypeError, "%s incorrect request type" % (request.__class__)
        # no input wsaction
        self.binding.Send(None, None, request, soapaction="", encodingStyle="http://schemas.xmlsoap.org/soap/encoding/", **kw)
        # no output wsaction
        typecode = Struct(pname=None, ofwhat=GetMobileCreateSignatureStatusResponse.typecode.ofwhat, pyclass=GetMobileCreateSignatureStatusResponse.typecode.pyclass)
        response = self.binding.Receive(typecode)
        return response

    # op: GetMobileCertificate
    def GetMobileCertificate(self, request, **kw):
        if isinstance(request, GetMobileCertificate) is False:
            raise TypeError, "%s incorrect request type" % (request.__class__)
        # no input wsaction
        self.binding.Send(None, None, request, soapaction="", encodingStyle="http://schemas.xmlsoap.org/soap/encoding/", **kw)
        # no output wsaction
        typecode = Struct(pname=None, ofwhat=GetMobileCertificateResponse.typecode.ofwhat, pyclass=GetMobileCertificateResponse.typecode.pyclass)
        response = self.binding.Receive(typecode)
        return response

    # op: CheckCertificate
    def CheckCertificate(self, request, **kw):
        if isinstance(request, CheckCertificate) is False:
            raise TypeError, "%s incorrect request type" % (request.__class__)
        # no input wsaction
        self.binding.Send(None, None, request, soapaction="", encodingStyle="http://schemas.xmlsoap.org/soap/encoding/", **kw)
        # no output wsaction
        typecode = Struct(pname=None, ofwhat=CheckCertificateResponse.typecode.ofwhat, pyclass=CheckCertificateResponse.typecode.pyclass)
        response = self.binding.Receive(typecode)
        return response

_StartSessionTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","StartSession"), ofwhat=[ZSI.TC.String(pname="SigningProfile", aname="_SigningProfile", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="SigDocXML", aname="_SigDocXML", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.Boolean(pname="bHoldSession", aname="_bHoldSession", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ns0.DataFileData_Def(pname="datafile", aname="_datafile", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class StartSession:
    typecode = _StartSessionTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        SigningProfile -- part SigningProfile
        SigDocXML -- part SigDocXML
        bHoldSession -- part bHoldSession
        datafile -- part datafile
        """
        self._SigningProfile =  kw.get("SigningProfile")
        self._SigDocXML =  kw.get("SigDocXML")
        self._bHoldSession =  kw.get("bHoldSession")
        self._datafile =  kw.get("datafile")
StartSession.typecode.pyclass = StartSession

_StartSessionResponseTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","StartSessionResponse"), ofwhat=[ZSI.TC.String(pname="Status", aname="_Status", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TCnumbers.Iint(pname="Sesscode", aname="_Sesscode", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ns0.SignedDocInfo_Def(pname="SignedDocInfo", aname="_SignedDocInfo", typed=False,
    encoded=None, minOccurs=0, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class StartSessionResponse:
    typecode = _StartSessionResponseTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Status -- part Status
        Sesscode -- part Sesscode
        SignedDocInfo -- part SignedDocInfo
        """
        self._Status =  kw.get("Status")
        self._Sesscode =  kw.get("Sesscode")
        self._SignedDocInfo =  kw.get("SignedDocInfo")
StartSessionResponse.typecode.pyclass = StartSessionResponse

_CloseSessionTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","CloseSession"), ofwhat=[ZSI.TCnumbers.Iint(pname="Sesscode", aname="_Sesscode", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class CloseSession:
    typecode = _CloseSessionTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Sesscode -- part Sesscode
        """
        self._Sesscode =  kw.get("Sesscode")
CloseSession.typecode.pyclass = CloseSession

_CloseSessionResponseTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","CloseSessionResponse"), ofwhat=[ZSI.TC.String(pname="Status", aname="_Status", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class CloseSessionResponse:
    typecode = _CloseSessionResponseTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Status -- part Status
        """
        self._Status =  kw.get("Status")
CloseSessionResponse.typecode.pyclass = CloseSessionResponse

_CreateSignedDocTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","CreateSignedDoc"), ofwhat=[ZSI.TCnumbers.Iint(pname="Sesscode", aname="_Sesscode", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="Format", aname="_Format", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="Version", aname="_Version", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class CreateSignedDoc:
    typecode = _CreateSignedDocTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Sesscode -- part Sesscode
        Format -- part Format
        Version -- part Version
        """
        self._Sesscode =  kw.get("Sesscode")
        self._Format =  kw.get("Format")
        self._Version =  kw.get("Version")
CreateSignedDoc.typecode.pyclass = CreateSignedDoc

_CreateSignedDocResponseTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","CreateSignedDocResponse"), ofwhat=[ZSI.TC.String(pname="Status", aname="_Status", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ns0.SignedDocInfo_Def(pname="SignedDocInfo", aname="_SignedDocInfo", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class CreateSignedDocResponse:
    typecode = _CreateSignedDocResponseTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Status -- part Status
        SignedDocInfo -- part SignedDocInfo
        """
        self._Status =  kw.get("Status")
        self._SignedDocInfo =  kw.get("SignedDocInfo")
CreateSignedDocResponse.typecode.pyclass = CreateSignedDocResponse

_AddDataFileTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","AddDataFile"), ofwhat=[ZSI.TCnumbers.Iint(pname="Sesscode", aname="_Sesscode", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="FileName", aname="_FileName", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="MimeType", aname="_MimeType", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="ContentType", aname="_ContentType", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TCnumbers.Iint(pname="Size", aname="_Size", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="DigestType", aname="_DigestType", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="DigestValue", aname="_DigestValue", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="Content", aname="_Content", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class AddDataFile:
    typecode = _AddDataFileTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Sesscode -- part Sesscode
        FileName -- part FileName
        MimeType -- part MimeType
        ContentType -- part ContentType
        Size -- part Size
        DigestType -- part DigestType
        DigestValue -- part DigestValue
        Content -- part Content
        """
        self._Sesscode =  kw.get("Sesscode")
        self._FileName =  kw.get("FileName")
        self._MimeType =  kw.get("MimeType")
        self._ContentType =  kw.get("ContentType")
        self._Size =  kw.get("Size")
        self._DigestType =  kw.get("DigestType")
        self._DigestValue =  kw.get("DigestValue")
        self._Content =  kw.get("Content")
AddDataFile.typecode.pyclass = AddDataFile

_AddDataFileResponseTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","AddDataFileResponse"), ofwhat=[ZSI.TC.String(pname="Status", aname="_Status", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ns0.SignedDocInfo_Def(pname="SignedDocInfo", aname="_SignedDocInfo", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class AddDataFileResponse:
    typecode = _AddDataFileResponseTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Status -- part Status
        SignedDocInfo -- part SignedDocInfo
        """
        self._Status =  kw.get("Status")
        self._SignedDocInfo =  kw.get("SignedDocInfo")
AddDataFileResponse.typecode.pyclass = AddDataFileResponse

_RemoveDataFileTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","RemoveDataFile"), ofwhat=[ZSI.TCnumbers.Iint(pname="Sesscode", aname="_Sesscode", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="DataFileId", aname="_DataFileId", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class RemoveDataFile:
    typecode = _RemoveDataFileTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Sesscode -- part Sesscode
        DataFileId -- part DataFileId
        """
        self._Sesscode =  kw.get("Sesscode")
        self._DataFileId =  kw.get("DataFileId")
RemoveDataFile.typecode.pyclass = RemoveDataFile

_RemoveDataFileResponseTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","RemoveDataFileResponse"), ofwhat=[ZSI.TC.String(pname="Status", aname="_Status", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ns0.SignedDocInfo_Def(pname="SignedDocInfo", aname="_SignedDocInfo", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class RemoveDataFileResponse:
    typecode = _RemoveDataFileResponseTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Status -- part Status
        SignedDocInfo -- part SignedDocInfo
        """
        self._Status =  kw.get("Status")
        self._SignedDocInfo =  kw.get("SignedDocInfo")
RemoveDataFileResponse.typecode.pyclass = RemoveDataFileResponse

_GetSignedDocTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","GetSignedDoc"), ofwhat=[ZSI.TCnumbers.Iint(pname="Sesscode", aname="_Sesscode", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class GetSignedDoc:
    typecode = _GetSignedDocTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Sesscode -- part Sesscode
        """
        self._Sesscode =  kw.get("Sesscode")
GetSignedDoc.typecode.pyclass = GetSignedDoc

_GetSignedDocResponseTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","GetSignedDocResponse"), ofwhat=[ZSI.TC.String(pname="Status", aname="_Status", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="SignedDocData", aname="_SignedDocData", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class GetSignedDocResponse:
    typecode = _GetSignedDocResponseTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Status -- part Status
        SignedDocData -- part SignedDocData
        """
        self._Status =  kw.get("Status")
        self._SignedDocData =  kw.get("SignedDocData")
GetSignedDocResponse.typecode.pyclass = GetSignedDocResponse

_GetSignedDocInfoTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","GetSignedDocInfo"), ofwhat=[ZSI.TCnumbers.Iint(pname="Sesscode", aname="_Sesscode", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class GetSignedDocInfo:
    typecode = _GetSignedDocInfoTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Sesscode -- part Sesscode
        """
        self._Sesscode =  kw.get("Sesscode")
GetSignedDocInfo.typecode.pyclass = GetSignedDocInfo

_GetSignedDocInfoResponseTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","GetSignedDocInfoResponse"), ofwhat=[ZSI.TC.String(pname="Status", aname="_Status", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ns0.SignedDocInfo_Def(pname="SignedDocInfo", aname="_SignedDocInfo", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class GetSignedDocInfoResponse:
    typecode = _GetSignedDocInfoResponseTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Status -- part Status
        SignedDocInfo -- part SignedDocInfo
        """
        self._Status =  kw.get("Status")
        self._SignedDocInfo =  kw.get("SignedDocInfo")
GetSignedDocInfoResponse.typecode.pyclass = GetSignedDocInfoResponse

_GetDataFileTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","GetDataFile"), ofwhat=[ZSI.TCnumbers.Iint(pname="Sesscode", aname="_Sesscode", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="DataFileId", aname="_DataFileId", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class GetDataFile:
    typecode = _GetDataFileTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Sesscode -- part Sesscode
        DataFileId -- part DataFileId
        """
        self._Sesscode =  kw.get("Sesscode")
        self._DataFileId =  kw.get("DataFileId")
GetDataFile.typecode.pyclass = GetDataFile

_GetDataFileResponseTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","GetDataFileResponse"), ofwhat=[ZSI.TC.String(pname="Status", aname="_Status", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ns0.DataFileData_Def(pname="DataFileData", aname="_DataFileData", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class GetDataFileResponse:
    typecode = _GetDataFileResponseTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Status -- part Status
        DataFileData -- part DataFileData
        """
        self._Status =  kw.get("Status")
        self._DataFileData =  kw.get("DataFileData")
GetDataFileResponse.typecode.pyclass = GetDataFileResponse

_GetSignersCertificateTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","GetSignersCertificate"), ofwhat=[ZSI.TCnumbers.Iint(pname="Sesscode", aname="_Sesscode", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="SignatureId", aname="_SignatureId", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class GetSignersCertificate:
    typecode = _GetSignersCertificateTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Sesscode -- part Sesscode
        SignatureId -- part SignatureId
        """
        self._Sesscode =  kw.get("Sesscode")
        self._SignatureId =  kw.get("SignatureId")
GetSignersCertificate.typecode.pyclass = GetSignersCertificate

_GetSignersCertificateResponseTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","GetSignersCertificateResponse"), ofwhat=[ZSI.TC.String(pname="Status", aname="_Status", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="CertificateData", aname="_CertificateData", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class GetSignersCertificateResponse:
    typecode = _GetSignersCertificateResponseTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Status -- part Status
        CertificateData -- part CertificateData
        """
        self._Status =  kw.get("Status")
        self._CertificateData =  kw.get("CertificateData")
GetSignersCertificateResponse.typecode.pyclass = GetSignersCertificateResponse

_GetNotarysCertificateTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","GetNotarysCertificate"), ofwhat=[ZSI.TCnumbers.Iint(pname="Sesscode", aname="_Sesscode", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="SignatureId", aname="_SignatureId", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class GetNotarysCertificate:
    typecode = _GetNotarysCertificateTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Sesscode -- part Sesscode
        SignatureId -- part SignatureId
        """
        self._Sesscode =  kw.get("Sesscode")
        self._SignatureId =  kw.get("SignatureId")
GetNotarysCertificate.typecode.pyclass = GetNotarysCertificate

_GetNotarysCertificateResponseTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","GetNotarysCertificateResponse"), ofwhat=[ZSI.TC.String(pname="Status", aname="_Status", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="CertificateData", aname="_CertificateData", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class GetNotarysCertificateResponse:
    typecode = _GetNotarysCertificateResponseTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Status -- part Status
        CertificateData -- part CertificateData
        """
        self._Status =  kw.get("Status")
        self._CertificateData =  kw.get("CertificateData")
GetNotarysCertificateResponse.typecode.pyclass = GetNotarysCertificateResponse

_GetNotaryTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","GetNotary"), ofwhat=[ZSI.TCnumbers.Iint(pname="Sesscode", aname="_Sesscode", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="SignatureId", aname="_SignatureId", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class GetNotary:
    typecode = _GetNotaryTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Sesscode -- part Sesscode
        SignatureId -- part SignatureId
        """
        self._Sesscode =  kw.get("Sesscode")
        self._SignatureId =  kw.get("SignatureId")
GetNotary.typecode.pyclass = GetNotary

_GetNotaryResponseTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","GetNotaryResponse"), ofwhat=[ZSI.TC.String(pname="Status", aname="_Status", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="OcspData", aname="_OcspData", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class GetNotaryResponse:
    typecode = _GetNotaryResponseTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Status -- part Status
        OcspData -- part OcspData
        """
        self._Status =  kw.get("Status")
        self._OcspData =  kw.get("OcspData")
GetNotaryResponse.typecode.pyclass = GetNotaryResponse

_GetTSACertificateTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","GetTSACertificate"), ofwhat=[ZSI.TCnumbers.Iint(pname="Sesscode", aname="_Sesscode", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="TimestampId", aname="_TimestampId", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class GetTSACertificate:
    typecode = _GetTSACertificateTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Sesscode -- part Sesscode
        TimestampId -- part TimestampId
        """
        self._Sesscode =  kw.get("Sesscode")
        self._TimestampId =  kw.get("TimestampId")
GetTSACertificate.typecode.pyclass = GetTSACertificate

_GetTSACertificateResponseTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","GetTSACertificateResponse"), ofwhat=[ZSI.TC.String(pname="Status", aname="_Status", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="CertificateData", aname="_CertificateData", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class GetTSACertificateResponse:
    typecode = _GetTSACertificateResponseTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Status -- part Status
        CertificateData -- part CertificateData
        """
        self._Status =  kw.get("Status")
        self._CertificateData =  kw.get("CertificateData")
GetTSACertificateResponse.typecode.pyclass = GetTSACertificateResponse

_GetTimestampTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","GetTimestamp"), ofwhat=[ZSI.TCnumbers.Iint(pname="Sesscode", aname="_Sesscode", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="TimestampId", aname="_TimestampId", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class GetTimestamp:
    typecode = _GetTimestampTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Sesscode -- part Sesscode
        TimestampId -- part TimestampId
        """
        self._Sesscode =  kw.get("Sesscode")
        self._TimestampId =  kw.get("TimestampId")
GetTimestamp.typecode.pyclass = GetTimestamp

_GetTimestampResponseTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","GetTimestampResponse"), ofwhat=[ZSI.TC.String(pname="Status", aname="_Status", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="TimestampData", aname="_TimestampData", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class GetTimestampResponse:
    typecode = _GetTimestampResponseTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Status -- part Status
        TimestampData -- part TimestampData
        """
        self._Status =  kw.get("Status")
        self._TimestampData =  kw.get("TimestampData")
GetTimestampResponse.typecode.pyclass = GetTimestampResponse

_GetCRLTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","GetCRL"), ofwhat=[ZSI.TCnumbers.Iint(pname="Sesscode", aname="_Sesscode", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="SignatureId", aname="_SignatureId", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class GetCRL:
    typecode = _GetCRLTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Sesscode -- part Sesscode
        SignatureId -- part SignatureId
        """
        self._Sesscode =  kw.get("Sesscode")
        self._SignatureId =  kw.get("SignatureId")
GetCRL.typecode.pyclass = GetCRL

_GetCRLResponseTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","GetCRLResponse"), ofwhat=[ZSI.TC.String(pname="Status", aname="_Status", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="CRLData", aname="_CRLData", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class GetCRLResponse:
    typecode = _GetCRLResponseTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Status -- part Status
        CRLData -- part CRLData
        """
        self._Status =  kw.get("Status")
        self._CRLData =  kw.get("CRLData")
GetCRLResponse.typecode.pyclass = GetCRLResponse

_GetSignatureModulesTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","GetSignatureModules"), ofwhat=[ZSI.TCnumbers.Iint(pname="Sesscode", aname="_Sesscode", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="Platform", aname="_Platform", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="Phase", aname="_Phase", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="Type", aname="_Type", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class GetSignatureModules:
    typecode = _GetSignatureModulesTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Sesscode -- part Sesscode
        Platform -- part Platform
        Phase -- part Phase
        Type -- part Type
        """
        self._Sesscode =  kw.get("Sesscode")
        self._Platform =  kw.get("Platform")
        self._Phase =  kw.get("Phase")
        self._Type =  kw.get("Type")
GetSignatureModules.typecode.pyclass = GetSignatureModules

_GetSignatureModulesResponseTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","GetSignatureModulesResponse"), ofwhat=[ZSI.TC.String(pname="Status", aname="_Status", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ns0.SignatureModulesArray_Def(pname="Modules", aname="_Modules", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class GetSignatureModulesResponse:
    typecode = _GetSignatureModulesResponseTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Status -- part Status
        Modules -- part Modules
        """
        self._Status =  kw.get("Status")
        self._Modules =  kw.get("Modules")
GetSignatureModulesResponse.typecode.pyclass = GetSignatureModulesResponse

_PrepareSignatureTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","PrepareSignature"), ofwhat=[ZSI.TCnumbers.Iint(pname="Sesscode", aname="_Sesscode", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="SignersCertificate", aname="_SignersCertificate", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="SignersTokenId", aname="_SignersTokenId", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="Role", aname="_Role", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="City", aname="_City", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="State", aname="_State", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="PostalCode", aname="_PostalCode", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="Country", aname="_Country", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="SigningProfile", aname="_SigningProfile", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class PrepareSignature:
    typecode = _PrepareSignatureTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Sesscode -- part Sesscode
        SignersCertificate -- part SignersCertificate
        SignersTokenId -- part SignersTokenId
        Role -- part Role
        City -- part City
        State -- part State
        PostalCode -- part PostalCode
        Country -- part Country
        SigningProfile -- part SigningProfile
        """
        self._Sesscode =  kw.get("Sesscode")
        self._SignersCertificate =  kw.get("SignersCertificate")
        self._SignersTokenId =  kw.get("SignersTokenId")
        self._Role =  kw.get("Role")
        self._City =  kw.get("City")
        self._State =  kw.get("State")
        self._PostalCode =  kw.get("PostalCode")
        self._Country =  kw.get("Country")
        self._SigningProfile =  kw.get("SigningProfile")
PrepareSignature.typecode.pyclass = PrepareSignature

_PrepareSignatureResponseTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","PrepareSignatureResponse"), ofwhat=[ZSI.TC.String(pname="Status", aname="_Status", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="SignatureId", aname="_SignatureId", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="SignedInfoDigest", aname="_SignedInfoDigest", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class PrepareSignatureResponse:
    typecode = _PrepareSignatureResponseTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Status -- part Status
        SignatureId -- part SignatureId
        SignedInfoDigest -- part SignedInfoDigest
        """
        self._Status =  kw.get("Status")
        self._SignatureId =  kw.get("SignatureId")
        self._SignedInfoDigest =  kw.get("SignedInfoDigest")
PrepareSignatureResponse.typecode.pyclass = PrepareSignatureResponse

_FinalizeSignatureTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","FinalizeSignature"), ofwhat=[ZSI.TCnumbers.Iint(pname="Sesscode", aname="_Sesscode", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="SignatureId", aname="_SignatureId", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="SignatureValue", aname="_SignatureValue", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class FinalizeSignature:
    typecode = _FinalizeSignatureTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Sesscode -- part Sesscode
        SignatureId -- part SignatureId
        SignatureValue -- part SignatureValue
        """
        self._Sesscode =  kw.get("Sesscode")
        self._SignatureId =  kw.get("SignatureId")
        self._SignatureValue =  kw.get("SignatureValue")
FinalizeSignature.typecode.pyclass = FinalizeSignature

_FinalizeSignatureResponseTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","FinalizeSignatureResponse"), ofwhat=[ZSI.TC.String(pname="Status", aname="_Status", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ns0.SignedDocInfo_Def(pname="SignedDocInfo", aname="_SignedDocInfo", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class FinalizeSignatureResponse:
    typecode = _FinalizeSignatureResponseTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Status -- part Status
        SignedDocInfo -- part SignedDocInfo
        """
        self._Status =  kw.get("Status")
        self._SignedDocInfo =  kw.get("SignedDocInfo")
FinalizeSignatureResponse.typecode.pyclass = FinalizeSignatureResponse

_RemoveSignatureTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","RemoveSignature"), ofwhat=[ZSI.TCnumbers.Iint(pname="Sesscode", aname="_Sesscode", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="SignatureId", aname="_SignatureId", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class RemoveSignature:
    typecode = _RemoveSignatureTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Sesscode -- part Sesscode
        SignatureId -- part SignatureId
        """
        self._Sesscode =  kw.get("Sesscode")
        self._SignatureId =  kw.get("SignatureId")
RemoveSignature.typecode.pyclass = RemoveSignature

_RemoveSignatureResponseTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","RemoveSignatureResponse"), ofwhat=[ZSI.TC.String(pname="Status", aname="_Status", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ns0.SignedDocInfo_Def(pname="SignedDocInfo", aname="_SignedDocInfo", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class RemoveSignatureResponse:
    typecode = _RemoveSignatureResponseTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Status -- part Status
        SignedDocInfo -- part SignedDocInfo
        """
        self._Status =  kw.get("Status")
        self._SignedDocInfo =  kw.get("SignedDocInfo")
RemoveSignatureResponse.typecode.pyclass = RemoveSignatureResponse

_GetVersionTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","GetVersion"), ofwhat=[], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class GetVersion:
    typecode = _GetVersionTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        """
GetVersion.typecode.pyclass = GetVersion

_GetVersionResponseTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","GetVersionResponse"), ofwhat=[ZSI.TC.String(pname="Name", aname="_Name", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="Version", aname="_Version", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="LibraryVersion", aname="_LibraryVersion", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class GetVersionResponse:
    typecode = _GetVersionResponseTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Name -- part Name
        Version -- part Version
        LibraryVersion -- part LibraryVersion
        """
        self._Name =  kw.get("Name")
        self._Version =  kw.get("Version")
        self._LibraryVersion =  kw.get("LibraryVersion")
GetVersionResponse.typecode.pyclass = GetVersionResponse

_MobileSignTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","MobileSign"), ofwhat=[ZSI.TCnumbers.Iint(pname="Sesscode", aname="_Sesscode", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="SignerIDCode", aname="_SignerIDCode", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="SignersCountry", aname="_SignersCountry", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="SignerPhoneNo", aname="_SignerPhoneNo", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="ServiceName", aname="_ServiceName", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="AdditionalDataToBeDisplayed", aname="_AdditionalDataToBeDisplayed", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="Language", aname="_Language", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="Role", aname="_Role", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="City", aname="_City", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="StateOrProvince", aname="_StateOrProvince", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="PostalCode", aname="_PostalCode", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="CountryName", aname="_CountryName", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="SigningProfile", aname="_SigningProfile", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="MessagingMode", aname="_MessagingMode", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TCnumbers.Iint(pname="AsyncConfiguration", aname="_AsyncConfiguration", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.Boolean(pname="ReturnDocInfo", aname="_ReturnDocInfo", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.Boolean(pname="ReturnDocData", aname="_ReturnDocData", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class MobileSign:
    typecode = _MobileSignTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Sesscode -- part Sesscode
        SignerIDCode -- part SignerIDCode
        SignersCountry -- part SignersCountry
        SignerPhoneNo -- part SignerPhoneNo
        ServiceName -- part ServiceName
        AdditionalDataToBeDisplayed -- part AdditionalDataToBeDisplayed
        Language -- part Language
        Role -- part Role
        City -- part City
        StateOrProvince -- part StateOrProvince
        PostalCode -- part PostalCode
        CountryName -- part CountryName
        SigningProfile -- part SigningProfile
        MessagingMode -- part MessagingMode
        AsyncConfiguration -- part AsyncConfiguration
        ReturnDocInfo -- part ReturnDocInfo
        ReturnDocData -- part ReturnDocData
        """
        self._Sesscode =  kw.get("Sesscode")
        self._SignerIDCode =  kw.get("SignerIDCode")
        self._SignersCountry =  kw.get("SignersCountry")
        self._SignerPhoneNo =  kw.get("SignerPhoneNo")
        self._ServiceName =  kw.get("ServiceName")
        self._AdditionalDataToBeDisplayed =  kw.get("AdditionalDataToBeDisplayed")
        self._Language =  kw.get("Language")
        self._Role =  kw.get("Role")
        self._City =  kw.get("City")
        self._StateOrProvince =  kw.get("StateOrProvince")
        self._PostalCode =  kw.get("PostalCode")
        self._CountryName =  kw.get("CountryName")
        self._SigningProfile =  kw.get("SigningProfile")
        self._MessagingMode =  kw.get("MessagingMode")
        self._AsyncConfiguration =  kw.get("AsyncConfiguration")
        self._ReturnDocInfo =  kw.get("ReturnDocInfo")
        self._ReturnDocData =  kw.get("ReturnDocData")
MobileSign.typecode.pyclass = MobileSign

_MobileSignResponseTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","MobileSignResponse"), ofwhat=[ZSI.TC.String(pname="Status", aname="_Status", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="StatusCode", aname="_StatusCode", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="ChallengeID", aname="_ChallengeID", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class MobileSignResponse:
    typecode = _MobileSignResponseTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Status -- part Status
        StatusCode -- part StatusCode
        ChallengeID -- part ChallengeID
        """
        self._Status =  kw.get("Status")
        self._StatusCode =  kw.get("StatusCode")
        self._ChallengeID =  kw.get("ChallengeID")
MobileSignResponse.typecode.pyclass = MobileSignResponse

_GetStatusInfoTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","GetStatusInfo"), ofwhat=[ZSI.TCnumbers.Iint(pname="Sesscode", aname="_Sesscode", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.Boolean(pname="ReturnDocInfo", aname="_ReturnDocInfo", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.Boolean(pname="WaitSignature", aname="_WaitSignature", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class GetStatusInfo:
    typecode = _GetStatusInfoTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Sesscode -- part Sesscode
        ReturnDocInfo -- part ReturnDocInfo
        WaitSignature -- part WaitSignature
        """
        self._Sesscode =  kw.get("Sesscode")
        self._ReturnDocInfo =  kw.get("ReturnDocInfo")
        self._WaitSignature =  kw.get("WaitSignature")
GetStatusInfo.typecode.pyclass = GetStatusInfo

_GetStatusInfoResponseTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","GetStatusInfoResponse"), ofwhat=[ZSI.TC.String(pname="Status", aname="_Status", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="StatusCode", aname="_StatusCode", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ns0.SignedDocInfo_Def(pname="SignedDocInfo", aname="_SignedDocInfo", typed=False,
    encoded=None, minOccurs=0, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class GetStatusInfoResponse:
    typecode = _GetStatusInfoResponseTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Status -- part Status
        StatusCode -- part StatusCode
        SignedDocInfo -- part SignedDocInfo
        """
        self._Status =  kw.get("Status")
        self._StatusCode =  kw.get("StatusCode")
        self._SignedDocInfo =  kw.get("SignedDocInfo")
GetStatusInfoResponse.typecode.pyclass = GetStatusInfoResponse

_MobileAuthenticateTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","MobileAuthenticate"), ofwhat=[ZSI.TC.String(pname="IDCode", aname="_IDCode", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="CountryCode", aname="_CountryCode", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="PhoneNo", aname="_PhoneNo", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="Language", aname="_Language", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="ServiceName", aname="_ServiceName", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="MessageToDisplay", aname="_MessageToDisplay", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="SPChallenge", aname="_SPChallenge", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="MessagingMode", aname="_MessagingMode", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TCnumbers.Iint(pname="AsyncConfiguration", aname="_AsyncConfiguration", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.Boolean(pname="ReturnCertData", aname="_ReturnCertData", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.Boolean(pname="ReturnRevocationData", aname="_ReturnRevocationData", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class MobileAuthenticate:
    typecode = _MobileAuthenticateTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        IDCode -- part IDCode
        CountryCode -- part CountryCode
        PhoneNo -- part PhoneNo
        Language -- part Language
        ServiceName -- part ServiceName
        MessageToDisplay -- part MessageToDisplay
        SPChallenge -- part SPChallenge
        MessagingMode -- part MessagingMode
        AsyncConfiguration -- part AsyncConfiguration
        ReturnCertData -- part ReturnCertData
        ReturnRevocationData -- part ReturnRevocationData
        """
        self._IDCode =  kw.get("IDCode")
        self._CountryCode =  kw.get("CountryCode")
        self._PhoneNo =  kw.get("PhoneNo")
        self._Language =  kw.get("Language")
        self._ServiceName =  kw.get("ServiceName")
        self._MessageToDisplay =  kw.get("MessageToDisplay")
        self._SPChallenge =  kw.get("SPChallenge")
        self._MessagingMode =  kw.get("MessagingMode")
        self._AsyncConfiguration =  kw.get("AsyncConfiguration")
        self._ReturnCertData =  kw.get("ReturnCertData")
        self._ReturnRevocationData =  kw.get("ReturnRevocationData")
MobileAuthenticate.typecode.pyclass = MobileAuthenticate

_MobileAuthenticateResponseTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","MobileAuthenticateResponse"), ofwhat=[ZSI.TCnumbers.Iint(pname="Sesscode", aname="_Sesscode", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="Status", aname="_Status", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="UserIDCode", aname="_UserIDCode", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="UserGivenname", aname="_UserGivenname", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="UserSurname", aname="_UserSurname", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="UserCountry", aname="_UserCountry", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="UserCN", aname="_UserCN", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="CertificateData", aname="_CertificateData", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="ChallengeID", aname="_ChallengeID", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="Challenge", aname="_Challenge", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="RevocationData", aname="_RevocationData", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class MobileAuthenticateResponse:
    typecode = _MobileAuthenticateResponseTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Sesscode -- part Sesscode
        Status -- part Status
        UserIDCode -- part UserIDCode
        UserGivenname -- part UserGivenname
        UserSurname -- part UserSurname
        UserCountry -- part UserCountry
        UserCN -- part UserCN
        CertificateData -- part CertificateData
        ChallengeID -- part ChallengeID
        Challenge -- part Challenge
        RevocationData -- part RevocationData
        """
        self._Sesscode =  kw.get("Sesscode")
        self._Status =  kw.get("Status")
        self._UserIDCode =  kw.get("UserIDCode")
        self._UserGivenname =  kw.get("UserGivenname")
        self._UserSurname =  kw.get("UserSurname")
        self._UserCountry =  kw.get("UserCountry")
        self._UserCN =  kw.get("UserCN")
        self._CertificateData =  kw.get("CertificateData")
        self._ChallengeID =  kw.get("ChallengeID")
        self._Challenge =  kw.get("Challenge")
        self._RevocationData =  kw.get("RevocationData")
MobileAuthenticateResponse.typecode.pyclass = MobileAuthenticateResponse

_GetMobileAuthenticateStatusTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","GetMobileAuthenticateStatus"), ofwhat=[ZSI.TCnumbers.Iint(pname="Sesscode", aname="_Sesscode", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.Boolean(pname="WaitSignature", aname="_WaitSignature", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class GetMobileAuthenticateStatus:
    typecode = _GetMobileAuthenticateStatusTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Sesscode -- part Sesscode
        WaitSignature -- part WaitSignature
        """
        self._Sesscode =  kw.get("Sesscode")
        self._WaitSignature =  kw.get("WaitSignature")
GetMobileAuthenticateStatus.typecode.pyclass = GetMobileAuthenticateStatus

_GetMobileAuthenticateStatusResponseTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","GetMobileAuthenticateStatusResponse"), ofwhat=[ZSI.TC.String(pname="Status", aname="_Status", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="Signature", aname="_Signature", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class GetMobileAuthenticateStatusResponse:
    typecode = _GetMobileAuthenticateStatusResponseTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Status -- part Status
        Signature -- part Signature
        """
        self._Status =  kw.get("Status")
        self._Signature =  kw.get("Signature")
GetMobileAuthenticateStatusResponse.typecode.pyclass = GetMobileAuthenticateStatusResponse

_MobileCreateSignatureTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","MobileCreateSignature"), ofwhat=[ZSI.TC.String(pname="IDCode", aname="_IDCode", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="SignersCountry", aname="_SignersCountry", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="PhoneNo", aname="_PhoneNo", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="Language", aname="_Language", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="ServiceName", aname="_ServiceName", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="MessageToDisplay", aname="_MessageToDisplay", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="Role", aname="_Role", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="City", aname="_City", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="StateOrProvince", aname="_StateOrProvince", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="PostalCode", aname="_PostalCode", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="CountryName", aname="_CountryName", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="SigningProfile", aname="_SigningProfile", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ns0.DataFileDigestList_Def(pname="DataFiles", aname="_DataFiles", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="Format", aname="_Format", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="Version", aname="_Version", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="SignatureID", aname="_SignatureID", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="MessagingMode", aname="_MessagingMode", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TCnumbers.Iint(pname="AsyncConfiguration", aname="_AsyncConfiguration", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class MobileCreateSignature:
    typecode = _MobileCreateSignatureTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        IDCode -- part IDCode
        SignersCountry -- part SignersCountry
        PhoneNo -- part PhoneNo
        Language -- part Language
        ServiceName -- part ServiceName
        MessageToDisplay -- part MessageToDisplay
        Role -- part Role
        City -- part City
        StateOrProvince -- part StateOrProvince
        PostalCode -- part PostalCode
        CountryName -- part CountryName
        SigningProfile -- part SigningProfile
        DataFiles -- part DataFiles
        Format -- part Format
        Version -- part Version
        SignatureID -- part SignatureID
        MessagingMode -- part MessagingMode
        AsyncConfiguration -- part AsyncConfiguration
        """
        self._IDCode =  kw.get("IDCode")
        self._SignersCountry =  kw.get("SignersCountry")
        self._PhoneNo =  kw.get("PhoneNo")
        self._Language =  kw.get("Language")
        self._ServiceName =  kw.get("ServiceName")
        self._MessageToDisplay =  kw.get("MessageToDisplay")
        self._Role =  kw.get("Role")
        self._City =  kw.get("City")
        self._StateOrProvince =  kw.get("StateOrProvince")
        self._PostalCode =  kw.get("PostalCode")
        self._CountryName =  kw.get("CountryName")
        self._SigningProfile =  kw.get("SigningProfile")
        self._DataFiles =  kw.get("DataFiles")
        self._Format =  kw.get("Format")
        self._Version =  kw.get("Version")
        self._SignatureID =  kw.get("SignatureID")
        self._MessagingMode =  kw.get("MessagingMode")
        self._AsyncConfiguration =  kw.get("AsyncConfiguration")
MobileCreateSignature.typecode.pyclass = MobileCreateSignature

_MobileCreateSignatureResponseTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","MobileCreateSignatureResponse"), ofwhat=[ZSI.TCnumbers.Iint(pname="Sesscode", aname="_Sesscode", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="ChallengeID", aname="_ChallengeID", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="Status", aname="_Status", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class MobileCreateSignatureResponse:
    typecode = _MobileCreateSignatureResponseTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Sesscode -- part Sesscode
        ChallengeID -- part ChallengeID
        Status -- part Status
        """
        self._Sesscode =  kw.get("Sesscode")
        self._ChallengeID =  kw.get("ChallengeID")
        self._Status =  kw.get("Status")
MobileCreateSignatureResponse.typecode.pyclass = MobileCreateSignatureResponse

_GetMobileCreateSignatureStatusTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","GetMobileCreateSignatureStatus"), ofwhat=[ZSI.TCnumbers.Iint(pname="Sesscode", aname="_Sesscode", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.Boolean(pname="WaitSignature", aname="_WaitSignature", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class GetMobileCreateSignatureStatus:
    typecode = _GetMobileCreateSignatureStatusTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Sesscode -- part Sesscode
        WaitSignature -- part WaitSignature
        """
        self._Sesscode =  kw.get("Sesscode")
        self._WaitSignature =  kw.get("WaitSignature")
GetMobileCreateSignatureStatus.typecode.pyclass = GetMobileCreateSignatureStatus

_GetMobileCreateSignatureStatusResponseTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","GetMobileCreateSignatureStatusResponse"), ofwhat=[ZSI.TCnumbers.Iint(pname="Sesscode", aname="_Sesscode", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="Status", aname="_Status", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="Signature", aname="_Signature", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class GetMobileCreateSignatureStatusResponse:
    typecode = _GetMobileCreateSignatureStatusResponseTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Sesscode -- part Sesscode
        Status -- part Status
        Signature -- part Signature
        """
        self._Sesscode =  kw.get("Sesscode")
        self._Status =  kw.get("Status")
        self._Signature =  kw.get("Signature")
GetMobileCreateSignatureStatusResponse.typecode.pyclass = GetMobileCreateSignatureStatusResponse

_GetMobileCertificateTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","GetMobileCertificate"), ofwhat=[ZSI.TC.String(pname="IDCode", aname="_IDCode", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="Country", aname="_Country", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="PhoneNo", aname="_PhoneNo", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="ReturnCertData", aname="_ReturnCertData", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class GetMobileCertificate:
    typecode = _GetMobileCertificateTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        IDCode -- part IDCode
        Country -- part Country
        PhoneNo -- part PhoneNo
        ReturnCertData -- part ReturnCertData
        """
        self._IDCode =  kw.get("IDCode")
        self._Country =  kw.get("Country")
        self._PhoneNo =  kw.get("PhoneNo")
        self._ReturnCertData =  kw.get("ReturnCertData")
GetMobileCertificate.typecode.pyclass = GetMobileCertificate

_GetMobileCertificateResponseTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","GetMobileCertificateResponse"), ofwhat=[ZSI.TC.String(pname="AuthCertStatus", aname="_AuthCertStatus", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="SignCertStatus", aname="_SignCertStatus", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="AuthCertData", aname="_AuthCertData", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="SignCertData", aname="_SignCertData", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class GetMobileCertificateResponse:
    typecode = _GetMobileCertificateResponseTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        AuthCertStatus -- part AuthCertStatus
        SignCertStatus -- part SignCertStatus
        AuthCertData -- part AuthCertData
        SignCertData -- part SignCertData
        """
        self._AuthCertStatus =  kw.get("AuthCertStatus")
        self._SignCertStatus =  kw.get("SignCertStatus")
        self._AuthCertData =  kw.get("AuthCertData")
        self._SignCertData =  kw.get("SignCertData")
GetMobileCertificateResponse.typecode.pyclass = GetMobileCertificateResponse

_CheckCertificateTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","CheckCertificate"), ofwhat=[ZSI.TC.String(pname="Certificate", aname="_Certificate", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.Boolean(pname="ReturnRevocationData", aname="_ReturnRevocationData", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class CheckCertificate:
    typecode = _CheckCertificateTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Certificate -- part Certificate
        ReturnRevocationData -- part ReturnRevocationData
        """
        self._Certificate =  kw.get("Certificate")
        self._ReturnRevocationData =  kw.get("ReturnRevocationData")
CheckCertificate.typecode.pyclass = CheckCertificate

_CheckCertificateResponseTypecode = Struct(pname=("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","CheckCertificateResponse"), ofwhat=[ZSI.TC.String(pname="Status", aname="_Status", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="UserIDCode", aname="_UserIDCode", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="UserGivenname", aname="_UserGivenname", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="UserSurname", aname="_UserSurname", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="UserCountry", aname="_UserCountry", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="UserOrganisation", aname="_UserOrganisation", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="UserCN", aname="_UserCN", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="IssuerCN", aname="_IssuerCN", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="KeyUsage", aname="_KeyUsage", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="EnhancedKeyUsage", aname="_EnhancedKeyUsage", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True), ZSI.TC.String(pname="RevocationData", aname="_RevocationData", typed=False, encoded=None, minOccurs=1, maxOccurs=1, nillable=True)], pyclass=None, encoded="http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl")
class CheckCertificateResponse:
    typecode = _CheckCertificateResponseTypecode
    __metaclass__ = pyclass_type
    def __init__(self, **kw):
        """Keyword parameters:
        Status -- part Status
        UserIDCode -- part UserIDCode
        UserGivenname -- part UserGivenname
        UserSurname -- part UserSurname
        UserCountry -- part UserCountry
        UserOrganisation -- part UserOrganisation
        UserCN -- part UserCN
        IssuerCN -- part IssuerCN
        KeyUsage -- part KeyUsage
        EnhancedKeyUsage -- part EnhancedKeyUsage
        RevocationData -- part RevocationData
        """
        self._Status =  kw.get("Status")
        self._UserIDCode =  kw.get("UserIDCode")
        self._UserGivenname =  kw.get("UserGivenname")
        self._UserSurname =  kw.get("UserSurname")
        self._UserCountry =  kw.get("UserCountry")
        self._UserOrganisation =  kw.get("UserOrganisation")
        self._UserCN =  kw.get("UserCN")
        self._IssuerCN =  kw.get("IssuerCN")
        self._KeyUsage =  kw.get("KeyUsage")
        self._EnhancedKeyUsage =  kw.get("EnhancedKeyUsage")
        self._RevocationData =  kw.get("RevocationData")
CheckCertificateResponse.typecode.pyclass = CheckCertificateResponse

########NEW FILE########
__FILENAME__ = DigiDocService_types
##################################################
# file: DigiDocService_types.py
#
# schema types generated by "ZSI.generate.wsdl2python.WriteServiceModule"
#    /usr/bin/wsdl2py --complexType https://www.openxades.org:9443/?wsdl
#
##################################################

import ZSI
import ZSI.TCcompound
from ZSI.schema import LocalElementDeclaration, ElementDeclaration, TypeDefinition, GTD, GED
from ZSI.generate.pyclass import pyclass_type

##############################
# targetNamespace
# http://www.sk.ee:8098/MSSP_GW/MSSP_GW.wsdl
##############################

class ns1:
    targetNamespace = "http://www.sk.ee:8098/MSSP_GW/MSSP_GW.wsdl"

# end class ns1 (tns: http://www.sk.ee:8098/MSSP_GW/MSSP_GW.wsdl)

##############################
# targetNamespace
# http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl
##############################

class ns0:
    targetNamespace = "http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl"

    class DataFileAttribute_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = "http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl"
        type = (schema, "DataFileAttribute")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = ns0.DataFileAttribute_Def.schema
            TClist = [ZSI.TC.String(pname="Name", aname="_Name", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), ZSI.TC.String(pname="Value", aname="_Value", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._Name = None
                    self._Value = None
                    return
            Holder.__name__ = "DataFileAttribute_Holder"
            self.pyclass = Holder

    class DataFileInfo_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = "http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl"
        type = (schema, "DataFileInfo")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = ns0.DataFileInfo_Def.schema
            TClist = [ZSI.TC.String(pname="Id", aname="_Id", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), ZSI.TC.String(pname="Filename", aname="_Filename", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), ZSI.TC.String(pname="MimeType", aname="_MimeType", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), ZSI.TC.String(pname="ContentType", aname="_ContentType", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), ZSI.TCnumbers.Iint(pname="Size", aname="_Size", minOccurs=1, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded")), ZSI.TC.String(pname="DigestType", aname="_DigestType", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), ZSI.TC.String(pname="DigestValue", aname="_DigestValue", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), GTD("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","DataFileAttribute",lazy=False)(pname="Attributes", aname="_Attributes", minOccurs=0, maxOccurs="unbounded", nillable=False, typed=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._Id = None
                    self._Filename = None
                    self._MimeType = None
                    self._ContentType = None
                    self._Size = None
                    self._DigestType = None
                    self._DigestValue = None
                    self._Attributes = []
                    return
            Holder.__name__ = "DataFileInfo_Holder"
            self.pyclass = Holder

    class SignerRole_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = "http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl"
        type = (schema, "SignerRole")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = ns0.SignerRole_Def.schema
            TClist = [ZSI.TCnumbers.Iint(pname="Certified", aname="_Certified", minOccurs=1, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded")), ZSI.TC.String(pname="Role", aname="_Role", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._Certified = None
                    self._Role = None
                    return
            Holder.__name__ = "SignerRole_Holder"
            self.pyclass = Holder

    class SignatureProductionPlace_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = "http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl"
        type = (schema, "SignatureProductionPlace")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = ns0.SignatureProductionPlace_Def.schema
            TClist = [ZSI.TC.String(pname="City", aname="_City", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), ZSI.TC.String(pname="StateOrProvince", aname="_StateOrProvince", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), ZSI.TC.String(pname="PostalCode", aname="_PostalCode", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), ZSI.TC.String(pname="CountryName", aname="_CountryName", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._City = None
                    self._StateOrProvince = None
                    self._PostalCode = None
                    self._CountryName = None
                    return
            Holder.__name__ = "SignatureProductionPlace_Holder"
            self.pyclass = Holder

    class CertificatePolicy_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = "http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl"
        type = (schema, "CertificatePolicy")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = ns0.CertificatePolicy_Def.schema
            TClist = [ZSI.TC.String(pname="OID", aname="_OID", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), ZSI.TC.String(pname="URL", aname="_URL", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), ZSI.TC.String(pname="Description", aname="_Description", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._OID = None
                    self._URL = None
                    self._Description = None
                    return
            Holder.__name__ = "CertificatePolicy_Holder"
            self.pyclass = Holder

    class CertificateInfo_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = "http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl"
        type = (schema, "CertificateInfo")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = ns0.CertificateInfo_Def.schema
            TClist = [ZSI.TC.String(pname="Issuer", aname="_Issuer", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), ZSI.TC.String(pname="Subject", aname="_Subject", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), ZSI.TCtimes.gDateTime(pname="ValidFrom", aname="_ValidFrom", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), ZSI.TCtimes.gDateTime(pname="ValidTo", aname="_ValidTo", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), ZSI.TC.String(pname="IssuerSerial", aname="_IssuerSerial", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), GTD("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","CertificatePolicy",lazy=False)(pname="Policies", aname="_Policies", minOccurs=0, maxOccurs="unbounded", nillable=False, typed=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._Issuer = None
                    self._Subject = None
                    self._ValidFrom = None
                    self._ValidTo = None
                    self._IssuerSerial = None
                    self._Policies = []
                    return
            Holder.__name__ = "CertificateInfo_Holder"
            self.pyclass = Holder

    class SignerInfo_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = "http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl"
        type = (schema, "SignerInfo")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = ns0.SignerInfo_Def.schema
            TClist = [ZSI.TC.String(pname="CommonName", aname="_CommonName", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), ZSI.TC.String(pname="IDCode", aname="_IDCode", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), GTD("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","CertificateInfo",lazy=False)(pname="Certificate", aname="_Certificate", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._CommonName = None
                    self._IDCode = None
                    self._Certificate = None
                    return
            Holder.__name__ = "SignerInfo_Holder"
            self.pyclass = Holder

    class ConfirmationInfo_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = "http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl"
        type = (schema, "ConfirmationInfo")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = ns0.ConfirmationInfo_Def.schema
            TClist = [ZSI.TC.String(pname="ResponderID", aname="_ResponderID", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), ZSI.TC.String(pname="ProducedAt", aname="_ProducedAt", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), GTD("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","CertificateInfo",lazy=False)(pname="ResponderCertificate", aname="_ResponderCertificate", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._ResponderID = None
                    self._ProducedAt = None
                    self._ResponderCertificate = None
                    return
            Holder.__name__ = "ConfirmationInfo_Holder"
            self.pyclass = Holder

    class TstInfo_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = "http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl"
        type = (schema, "TstInfo")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = ns0.TstInfo_Def.schema
            TClist = [ZSI.TC.String(pname="Id", aname="_Id", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), ZSI.TC.String(pname="Type", aname="_Type", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), ZSI.TC.String(pname="SerialNumber", aname="_SerialNumber", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), ZSI.TCtimes.gDateTime(pname="CreationTime", aname="_CreationTime", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), ZSI.TC.String(pname="Policy", aname="_Policy", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), ZSI.TC.String(pname="ErrorBound", aname="_ErrorBound", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), ZSI.TC.Boolean(pname="Ordered", aname="_Ordered", minOccurs=1, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded")), ZSI.TC.String(pname="TSA", aname="_TSA", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), GTD("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","CertificateInfo",lazy=False)(pname="Certificate", aname="_Certificate", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._Id = None
                    self._Type = None
                    self._SerialNumber = None
                    self._CreationTime = None
                    self._Policy = None
                    self._ErrorBound = None
                    self._Ordered = None
                    self._TSA = None
                    self._Certificate = None
                    return
            Holder.__name__ = "TstInfo_Holder"
            self.pyclass = Holder

    class RevokedInfo_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = "http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl"
        type = (schema, "RevokedInfo")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = ns0.RevokedInfo_Def.schema
            TClist = [ZSI.TCnumbers.IpositiveInteger(pname="Sequence", aname="_Sequence", minOccurs=1, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded")), ZSI.TC.String(pname="SerialNumber", aname="_SerialNumber", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), ZSI.TCtimes.gDateTime(pname="RevocationDate", aname="_RevocationDate", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._Sequence = None
                    self._SerialNumber = None
                    self._RevocationDate = None
                    return
            Holder.__name__ = "RevokedInfo_Holder"
            self.pyclass = Holder

    class CRLInfo_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = "http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl"
        type = (schema, "CRLInfo")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = ns0.CRLInfo_Def.schema
            TClist = [ZSI.TC.String(pname="Issuer", aname="_Issuer", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), ZSI.TCtimes.gDateTime(pname="LastUpdate", aname="_LastUpdate", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), ZSI.TCtimes.gDateTime(pname="NextUpdate", aname="_NextUpdate", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), GTD("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","RevokedInfo",lazy=False)(pname="Revocations", aname="_Revocations", minOccurs=0, maxOccurs="unbounded", nillable=False, typed=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._Issuer = None
                    self._LastUpdate = None
                    self._NextUpdate = None
                    self._Revocations = []
                    return
            Holder.__name__ = "CRLInfo_Holder"
            self.pyclass = Holder

    class Error_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = "http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl"
        type = (schema, "Error")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = ns0.Error_Def.schema
            TClist = [ZSI.TCnumbers.Iint(pname="Code", aname="_Code", minOccurs=1, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded")), ZSI.TC.String(pname="Category", aname="_Category", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), ZSI.TC.String(pname="Description", aname="_Description", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._Code = None
                    self._Category = None
                    self._Description = None
                    return
            Holder.__name__ = "Error_Holder"
            self.pyclass = Holder

    class SignatureInfo_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = "http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl"
        type = (schema, "SignatureInfo")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = ns0.SignatureInfo_Def.schema
            TClist = [ZSI.TC.String(pname="Id", aname="_Id", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), ZSI.TC.String(pname="Status", aname="_Status", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), GTD("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","Error",lazy=False)(pname="Error", aname="_Error", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), ZSI.TCtimes.gDateTime(pname="SigningTime", aname="_SigningTime", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), GTD("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","SignerRole",lazy=False)(pname="SignerRole", aname="_SignerRole", minOccurs=0, maxOccurs="unbounded", nillable=False, typed=False, encoded=kw.get("encoded")), GTD("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","SignatureProductionPlace",lazy=False)(pname="SignatureProductionPlace", aname="_SignatureProductionPlace", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), GTD("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","SignerInfo",lazy=False)(pname="Signer", aname="_Signer", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), GTD("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","ConfirmationInfo",lazy=False)(pname="Confirmation", aname="_Confirmation", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), GTD("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","TstInfo",lazy=False)(pname="Timestamps", aname="_Timestamps", minOccurs=0, maxOccurs="unbounded", nillable=False, typed=False, encoded=kw.get("encoded")), GTD("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","CRLInfo",lazy=False)(pname="CRLInfo", aname="_CRLInfo", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._Id = None
                    self._Status = None
                    self._Error = None
                    self._SigningTime = None
                    self._SignerRole = []
                    self._SignatureProductionPlace = None
                    self._Signer = None
                    self._Confirmation = None
                    self._Timestamps = []
                    self._CRLInfo = None
                    return
            Holder.__name__ = "SignatureInfo_Holder"
            self.pyclass = Holder

    class SignedDocInfo_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = "http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl"
        type = (schema, "SignedDocInfo")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = ns0.SignedDocInfo_Def.schema
            TClist = [ZSI.TC.String(pname="Format", aname="_Format", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), ZSI.TC.String(pname="Version", aname="_Version", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), GTD("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","DataFileInfo",lazy=False)(pname="DataFileInfo", aname="_DataFileInfo", minOccurs=0, maxOccurs="unbounded", nillable=False, typed=False, encoded=kw.get("encoded")), GTD("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","SignatureInfo",lazy=False)(pname="SignatureInfo", aname="_SignatureInfo", minOccurs=0, maxOccurs="unbounded", nillable=False, typed=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._Format = None
                    self._Version = None
                    self._DataFileInfo = []
                    self._SignatureInfo = []
                    return
            Holder.__name__ = "SignedDocInfo_Holder"
            self.pyclass = Holder

    class DataFileData_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = "http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl"
        type = (schema, "DataFileData")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = ns0.DataFileData_Def.schema
            TClist = [ZSI.TC.String(pname="Id", aname="_Id", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), ZSI.TC.String(pname="Filename", aname="_Filename", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), ZSI.TC.String(pname="MimeType", aname="_MimeType", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), ZSI.TC.String(pname="ContentType", aname="_ContentType", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), ZSI.TC.String(pname="DigestType", aname="_DigestType", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), ZSI.TC.String(pname="DigestValue", aname="_DigestValue", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), ZSI.TCnumbers.Iint(pname="Size", aname="_Size", minOccurs=1, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded")), GTD("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","DataFileAttribute",lazy=False)(pname="Attributes", aname="_Attributes", minOccurs=0, maxOccurs="unbounded", nillable=False, typed=False, encoded=kw.get("encoded")), ZSI.TC.String(pname="DfData", aname="_DfData", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._Id = None
                    self._Filename = None
                    self._MimeType = None
                    self._ContentType = None
                    self._DigestType = None
                    self._DigestValue = None
                    self._Size = None
                    self._Attributes = []
                    self._DfData = None
                    return
            Holder.__name__ = "DataFileData_Holder"
            self.pyclass = Holder

    class SignatureModule_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = "http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl"
        type = (schema, "SignatureModule")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = ns0.SignatureModule_Def.schema
            TClist = [ZSI.TC.String(pname="Name", aname="_Name", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), ZSI.TC.String(pname="Type", aname="_Type", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), ZSI.TC.String(pname="Location", aname="_Location", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), ZSI.TC.String(pname="ContentType", aname="_ContentType", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), ZSI.TC.String(pname="Content", aname="_Content", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._Name = None
                    self._Type = None
                    self._Location = None
                    self._ContentType = None
                    self._Content = None
                    return
            Holder.__name__ = "SignatureModule_Holder"
            self.pyclass = Holder

    class SignatureModulesArray_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = "http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl"
        type = (schema, "SignatureModulesArray")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = ns0.SignatureModulesArray_Def.schema
            TClist = [GTD("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","SignatureModule",lazy=False)(pname="Modules", aname="_Modules", minOccurs=0, maxOccurs="unbounded", nillable=False, typed=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._Modules = []
                    return
            Holder.__name__ = "SignatureModulesArray_Holder"
            self.pyclass = Holder

    class DataFileDigest_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = "http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl"
        type = (schema, "DataFileDigest")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = ns0.DataFileDigest_Def.schema
            TClist = [ZSI.TC.String(pname="Id", aname="_Id", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), ZSI.TC.String(pname="DigestType", aname="_DigestType", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded")), ZSI.TC.String(pname="DigestValue", aname="_DigestValue", minOccurs=0, maxOccurs=1, nillable=True, typed=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._Id = None
                    self._DigestType = None
                    self._DigestValue = None
                    return
            Holder.__name__ = "DataFileDigest_Holder"
            self.pyclass = Holder

    class DataFileDigestList_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = "http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl"
        type = (schema, "DataFileDigestList")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = ns0.DataFileDigestList_Def.schema
            TClist = [GTD("http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl","DataFileDigest",lazy=False)(pname="DataFileDigest", aname="_DataFileDigest", minOccurs=0, maxOccurs="unbounded", nillable=False, typed=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._DataFileDigest = []
                    return
            Holder.__name__ = "DataFileDigestList_Holder"
            self.pyclass = Holder

# end class ns0 (tns: http://www.sk.ee/DigiDocService/DigiDocService_2_3.wsdl)

########NEW FILE########
__FILENAME__ = hes
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import os
import httplib
import urllib
from election import Election
import evlog
import regrights
import evcommon
import evmessage
import bdocconfig
import bdocpython
import exception_msg
import sessionid

HEADERS = {
    'Content-type': 'application/x-www-form-urlencoded',
    'Accept': 'text/plain',
    'PID': os.getppid(),
    'User-agent': 'HES'}


class HESResult:

    def __init__(self, logit=None):
        self.user_code = evcommon.EVOTE_ERROR
        self.user_msg = evmessage.EV_ERRORS.TEHNILINE_VIGA
        self.log_msg = logit

    def pole_valija(self, ik):
        self.user_code = evcommon.EVOTE_VOTER_ERROR
        self.user_msg = evmessage.EV_ERRORS.POLE_VALIJA
        self.log_msg = \
            'Isikukood %s ei kuulu ühegi hääletuse valijate nimekirja' % ik

    def set_log_msg(self, msg):
        self.log_msg = msg


class VoteChecker:

    def __init__(self, decoded_vote, ik):
        self._decoded_vote = decoded_vote
        self._ik = ik
        self.error = HESResult()

    def check_vote(self, mobid):

        try:
            bdocpython.initialize()
            conf = bdocconfig.BDocConfig()
            conf.load(Election().get_bdoc_conf())

            alines = []
            elines = []
            if mobid:
                alines, elines = \
                        regrights.analyze_signature_for_log(self._decoded_vote)
            else:
                alines, elines = \
                        regrights.analyze_vote_for_log(self._decoded_vote)

            for el in alines:
                evlog.log(el)

            for el in elines:
                evlog.log_error(el)

            res = None
            if mobid:
                res = regrights.check_vote_hes_mobid(self._decoded_vote, conf)
            else:
                res = regrights.check_vote_hes(self._decoded_vote, conf)

            if not res.result:
                self.error.log_msg = res.error
                if self.error.user_msg == '':
                    self.error.user_msg = evmessage.EV_ERRORS.TEHNILINE_VIGA
                self.error.user_code = evcommon.EVOTE_ERROR

                if not res.cert_is_valid:
                    self.error.user_msg = evmessage.EV_ERRORS.SERTIFIKAAT_ON_AEGUNUD
                    self.error.user_code = evcommon.EVOTE_CERT_ERROR

                return False

            ik_ver = regrights.get_personal_code(res.subject)
            if self._ik != ik_ver:
                self.error.log_msg = \
                    'Autentija (%s) ja allkirjastaja (%s) erinevad' % \
                        (self._ik, ik_ver)
                self.error.user_msg = \
                    evmessage.EV_ERRORS.TEHNILINE_VIGA
                self.error.user_code = evcommon.EVOTE_ERROR
                return False

            return True

        except:
            self.error.user_msg = evmessage.EV_ERRORS.TEHNILINE_VIGA
            self.error.user_code = evcommon.EVOTE_ERROR
            self.error.log_msg = exception_msg.trace()

        finally:
            bdocpython.terminate()

        return False


class HTSConnector:

    def __init__(self, params):
        self._params = params
        self.error = HESResult()
        self.answer = []

    def work_strict(self):
        if self.work():
            if len(self.answer) == 3:
                return True
        return False

    def work(self):
        querystr = self._params.keys()
        encoded = urllib.urlencode(self._params)
        try:
            conn = httplib.HTTPConnection(Election().get_hts_ip())
            conn.request(evcommon.HTTP_POST, \
                Election().get_hts_path(), encoded, HEADERS)
            response = conn.getresponse()
            respstr = response.read()
            conn.close()

            if respstr.endswith('\n'):
                self.answer = respstr[:-1].split('\n')
            else:
                self.answer = respstr.split('\n')

        except Exception, ex:
            self.error.set_log_msg(\
                'Suhtlus HES ja HTS vahel ebaõnnestus: %s' % str(ex))
            return False

        #Teeme veateate valmis. Kui viga ei ole, siis teadet ei vaadata
        self.error.set_log_msg(\
            'Ebakorrektne vastus HTSilt. Saatsin (%s), sain (%s)' % \
                (querystr, self.answer))

        if len(self.answer) < 3:
            return False

        if evcommon.VERSION != self.answer[0]:
            return False

        if not self.answer[1] in ['0', '1', '2', '3', '4']:
            return False

        return True



class CandidateListExtractor:

    def __init__(self, ik, uid, pname):
        self._ik = ik
        self._list = []
        self._name_type = ''
        self._unique_id = uid
        self._pname = pname

    def compose_list(self):
        questions = Election().get_questions_obj('hes')
        for quest in questions:
            voter = quest.get_voter(self._ik)
            if voter == None:
                continue
            elid = quest.qname()
            self._name_type = \
                self._name_type + elid + ':' + str(quest.get_type()) + '\t'
            kandidaadid = quest.choices_to_voter(voter)
            evlog.log("Ringkond: %s-%s-%s-%s-%s" % \
                    (elid, voter['jaoskond_omavalitsus'], voter['jaoskond'], \
                    voter['ringkond_omavalitsus'], voter['ringkond']))
            self._list.append(kandidaadid)

    def has_list(self):
        return (len(self._list) > 0)

    def get_list(self):
        res = self._name_type + '\n'
        res = res + self._unique_id + '\n'
        res = res + self._pname + '\t' + self._ik + '\n'
        for el in self._list:
            res = res + el
        return res[:-1]

class HES:

    def __init__(self):
        evlog.AppLog().set_app('HES')

    def __return_error(self, hes_error):
        if hes_error.log_msg:
            evlog.log_error(hes_error.log_msg)
        return hes_error.user_code, hes_error.user_msg

    def get_candidate_list(self, valid_person):
        ik = valid_person[0]
        en = valid_person[1]
        pn = valid_person[2]
        evlog.AppLog().set_person(ik)
        evlog.log('Kandidaatide nimekiri: %s %s' % (en, pn))
        cld = CandidateListExtractor(
                ik, sessionid.voting(), "%s %s" % (en, pn))
        cld.compose_list()
        if cld.has_list():
            return evcommon.EVOTE_OK, cld.get_list()

        error = HESResult()
        error.pole_valija(ik)
        return self.__return_error(error)

    def hts_vote(self, valid_person, vote):
        ik = valid_person[0]
        en = valid_person[1]
        pn = valid_person[2]

        evlog.AppLog().set_person(ik)

        import base64
        decoded_vote = base64.decodestring(vote)

        evlog.log('Hääle talletamine: %s %s' % (en, pn))
        if not Election().can_vote(ik):
            error = HESResult()
            error.pole_valija(ik)
            return self.__return_error(error)

        inspector = VoteChecker(decoded_vote, ik)
        mobid = False
        if 'MOBILE_ID_CONTEXT' in os.environ:
            mobid = True

        if not inspector.check_vote(mobid):
            return self.__return_error(inspector.error)

        params = {}
        params[evcommon.POST_EVOTE] = vote
        params[evcommon.POST_PERSONAL_CODE] = ik
        params[evcommon.POST_VOTERS_FILES_SHA256] = \
            Election().get_voters_files_sha256()
        params[evcommon.POST_SESS_ID] = sessionid.voting()

        hts_connector = HTSConnector(params)
        if not hts_connector.work_strict():
            return self.__return_error(hts_connector.error)

        return hts_connector.answer[1], hts_connector.answer[2]

    def hts_repeat_check(self, valid_person):
        ik = valid_person[0]
        evlog.AppLog().set_person(ik)
        evlog.log('Korduvhääletuse kontroll')

        params = {}
        params[evcommon.POST_PERSONAL_CODE] = ik
        params[evcommon.POST_VOTERS_FILES_SHA256] = \
            Election().get_voters_files_sha256()
        params[evcommon.POST_SESS_ID] = sessionid.voting()

        hts_connector = HTSConnector(params)
        if not hts_connector.work():
            hts_connector.error.user_code = evcommon.EVOTE_REPEAT_ERROR
            return self.__return_error(hts_connector.error)

        retcode = hts_connector.answer[1]
        ans = '<br>'.join(hts_connector.answer[2:])
        return retcode, ans

    def hts_consistency_check(self):
        sha256 = Election().get_voters_files_sha256()
        if len(sha256) > 0:
            params = {evcommon.POST_VOTERS_FILES_SHA256: sha256}
            hts_connector = HTSConnector(params)
            if not hts_connector.work_strict():
                hts_connector.error.user_code = \
                    evcommon.EVOTE_CONSISTENCY_ERROR
                return self.__return_error(hts_connector.error)
            return hts_connector.answer[1], hts_connector.answer[2]
        else:
            error = HESResult()
            error.user_code = evcommon.EVOTE_CONSISTENCY_ERROR
            error.log_msg = 'POST_VOTERS_FILES_SHA256 parameeter oli (null)'
            return self.__return_error(error)


if __name__ == '__main__':

    print 'No main'


# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = hesdisp
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

"""
Häälteedastusserveri dispetsher (HESDispatch)

Hääleedastusserveri dispetsher on klass
läbi mille saab kasutada HES protokollis
määratud funktsionaalsust.

Kandidaatide nimekirja tõmbamine (VR <> HES <> HTS)
Hääle talletamisele saatmine (VR <> HES <> HTS)
HTS kooskõlalisuse kontroll (HES <> HTS)

Kogu VR suunast tulevasse infosse tuleb suhtuda kriitiliselt!
Ei saa eeldada, et kui kandidaatide nimekiri tõmmati,
siis on hääle talletamiseks kontrollid tehtud.

Kogu VR suunas minevasse infosse tuleb suhtuda kriitiliselt.
"""

import os
from election import Election
from election import ElectionState
import evlog
import evcommon
import evmessage
import protocol
import hes
import subprocess
import birthday

TASK_CAND = 'cand'
TASK_VOTE = 'vote'

STR_CAND = 'Kandidaatide nimekiri'
STR_VOTE = 'Hääle edastamine talletamiseks'

LOGSIG = {TASK_CAND : STR_CAND, TASK_VOTE : STR_VOTE}

def is_valid_id_cert():
    """Verifitseerib hääletaja sertifkaadi vastavust (ahelat) süsteemi
    laetud sertifikaatidega.

    @return True kui sertifikaat verifitseerub, vastasel korral False
    @throws Exception kui viga sertifikaadi lugemisel
    """

    proc = subprocess.Popen(\
        ['openssl', 'verify', '-CApath', Election().get_bdoc_ca()],\
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,\
        close_fds=True)

    proc.stdin.write(os.environ[evcommon.HTTP_CERT])
    proc.stdin.close()
    errlst = proc.stderr.readlines()
    reslst = proc.stdout.readlines()
    proc.stderr.close()
    proc.stdout.close()
    if len(errlst) > 0:
        err_data = ''
        if (len(os.environ[evcommon.HTTP_CERT]) > 0):
            err_data = os.environ[evcommon.HTTP_CERT][:100]
        raise Exception('Viga autentimissertifikaadi verifitseerimisel: '\
            '%s, INPUT: %s' % (errlst, err_data))

    if len(reslst) != 1 and reslst[0].strip()[-2:].upper() != "OK":
        return False, ''.join(reslst)
    return True, ''


def cert_info():
    """Tagastab autentimissertifikaadist kasutaja info.

    @returns sertifikaadile vastav ik, en, pn
    @throws Exception kui viga sertifikaadi lugemisel
    """
    # See tagastab kogu kraami utf8 kodeeringus

    proc = subprocess.Popen(\
        ['openssl', 'x509', '-subject', '-noout', \
        '-nameopt', 'sep_multiline', '-nameopt', 'utf8'], \
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,\
        close_fds=True)

    proc.stdin.write(os.environ[evcommon.HTTP_CERT])
    proc.stdin.close()
    errlst = proc.stderr.readlines()
    reslst = proc.stdout.readlines()
    proc.stderr.close()
    proc.stdout.close()

    if len(errlst) > 0:
        raise Exception(\
            'Viga autentimissertifikaadist info lugemisel: %s' % errlst)

    for el in reslst:
        tmp = el.strip().split('=')
        if len(tmp) != 2:
            raise Exception('Sobimatu autentimissertifikaat')

        if tmp[0] != 'CN':
            continue

        lst = tmp[1].split(',')
        if len(lst) != 3:
            raise Exception('Sobimatu autentimissertifikaat')

        # Kõik openssl'i poolt tagastatav info on juba õiges
        # kodeeringus
        pn = lst[0].strip()
        en = lst[1].strip()
        ik = lst[2].strip()

        return ik, en, pn


class CertAnalyzer:

    """
    Turvamees peab töötama nii get_candidate_list kui ka hts_vote ees,
    sest ei saa garanteerida, et kõik valijarakendused protokolli järgivad.
    Turvamehe errmsg peab sobima tavakasutajale saatmiseks.
    Exceptionid lendavad läbi ja logitakse kasutavas klassis
    """

    def __init__(self):
        self._ik = ''
        self._en = ''
        self._pn = ''
        self.errcode = evcommon.EVOTE_ERROR
        self.errmsg = ''
        self.logmsg = ''

    def work(self):

        valid, msg = is_valid_id_cert()
        if not valid:
            self.logmsg = msg
            self.errcode = evcommon.EVOTE_CERT_ERROR
            self.errmsg = evmessage.EV_ERRORS.EBASOBIV_SERTIFIKAAT
            return False

        self._ik, self._en, self._pn = cert_info()
        if not birthday.is_18(self._ik):
            self.errcode = evcommon.EVOTE_ERROR
            self.errmsg = evmessage.EV_ERRORS.POLE_18
            self.logmsg = self.errmsg
            return False

        return True

    def valid_person(self):
        return self._ik, self._en, self._pn


class HESVoterDispatcher:

    def __init__(self):
        self.__hes = hes.HES()
        self.__task = TASK_CAND

    def __return_exception(self):
        evlog.log_exception()
        r1, r2 = protocol.plain_error_technical(evcommon.EVOTE_ERROR)
        return self.__return_error(r1, r2)

    def __return_error(self, errcode, msg):
        evlog.log_error('Viga operatsioonil "%s", teade "%s"' %\
                (self.__task, msg))
        return protocol.msg_error(errcode, msg)

    def __get_candidate_list(self, valid_person):
        cand_ok, cand_msg = self.__hes.get_candidate_list(valid_person)

        if not cand_ok == evcommon.EVOTE_OK:
            return self.__return_error(cand_ok, cand_msg)

        korduv_ret, korduv_msg = self.__hes.hts_repeat_check(valid_person)

        if korduv_ret == evcommon.EVOTE_REPEAT_NO:
            evlog.log('Kandidaatide nimekiri väljastati A')
            return protocol.msg_ok(cand_msg)
        elif korduv_ret == evcommon.EVOTE_REPEAT_YES:
            evlog.log('Kandidaatide nimekiri väljastati B')
            return protocol.msg_repeat(cand_msg, korduv_msg)
        elif korduv_ret == evcommon.EVOTE_REPEAT_NOT_CONSISTENT:
            r1, r2 = protocol.plain_error_maintainance()
            return self.__return_error(r1, r2)
        else:
            return self.__return_error(evcommon.EVOTE_ERROR, korduv_msg)

    def __hts_vote(self, valid_person, vote, votebox):
        import vote_analyzer
        ik = valid_person[0]
        evlog.log_integrity(vote_analyzer.analyze(ik, vote, votebox))
        res_ok, res = self.__hes.hts_vote(valid_person, vote)
        if res_ok == evcommon.EVOTE_OK:
            return protocol.msg_ok(res)
        else:
            return self.__return_error(res_ok, res)

    def __proxy(self, vote = None, votebox = None):
        try:
            evlog.log(LOGSIG[self.__task] + ': ALGUS')
            if ElectionState().election_on():
                security = CertAnalyzer()
                if security.work():
                    if self.__task == TASK_CAND:
                        return \
                            self.__get_candidate_list(security.valid_person())
                    elif self.__task == TASK_VOTE:
                        return self.__hts_vote(\
                                    security.valid_person(), vote, votebox)
                    else:
                        r1, r2 = protocol.msg_error_technical()
                        return self.__return_error(r1, r2)
                else:
                    evlog.log_error('Viga: "%s"' % security.logmsg)
                    return \
                        self.__return_error(security.errcode, security.errmsg)
            else:
                r1, r2 = ElectionState().election_off_msg()
                return self.__return_error(r1, r2)
        except:
            return self.__return_exception()
        finally:
            evlog.log(LOGSIG[self.__task] + ': LõPP')

    def get_candidate_list(self):
        self.__task = TASK_CAND
        return self.__proxy()

    def hts_vote(self, vote, votebox = None):
        self.__task = TASK_VOTE
        return self.__proxy(vote, votebox)


class HESDispatcher:

    def __init__(self):
        self.__hes = hes.HES()

    def __return_exception(self, errcode):
        evlog.log_exception()
        return protocol.plain_error_technical(errcode)

    def hts_consistency_check(self):
        try:
            evlog.log('HES ja HTS kooskõlalisuse kontroll: ALGUS')
            return self.__hes.hts_consistency_check()
        except:
            return self.__return_exception(evcommon.EVOTE_CONSISTENCY_ERROR)
        finally:
            evlog.log('HTS kooskõlalisuse kontroll: LõPP')


if __name__ == '__main__':
    print 'No main'

# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = middisp
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import os
import binascii
import httplib
import base64
import StringIO

from DigiDocService_client import *
from DigiDocService_types import ns0 as ddstypes

from election import Election
from election import ElectionState
import evlog
import evlogdata
import sessionid
import evcommon
import protocol
import hesdisp

def get_mid_text(status):
    import evmessage

    if status == 'MID_NOT_READY':
        return evmessage.EV_ERRORS.MID_NOT_READY

    elif status == 'USER_CANCEL':
        return evmessage.EV_ERRORS.MID_USER_CANCEL

    elif status == 'PHONE_ABSENT':
        return evmessage.EV_ERRORS.MID_PHONE_ABSENT

    elif status == 'SENDING_ERROR':
        return evmessage.EV_ERRORS.MID_SENDING_ERROR

    elif status == 'SIM_ERROR':
        return evmessage.EV_ERRORS.MID_SIM_ERROR

    elif status == 'MID_ERROR_301':
        return evmessage.EV_ERRORS.MID_ERROR_301

    elif status in ['MID_ERROR_302', 'REVOKED', 'SUSPENDED']:
        return evmessage.EV_ERRORS.MID_ERROR_302

    elif status in ['MID_ERROR_303', 'NOT_ACTIVATED']:
        return evmessage.EV_ERRORS.MID_ERROR_303

    return evmessage.EV_ERRORS.MID_UNKNOWN_ERROR



def mobid_vote_data(b64vote):

    import bdocpythonutils

    bdocdata = base64.b64decode(b64vote)
    bdocfile = None

    try:
        bdocfile = StringIO.StringIO(bdocdata)
        bdoc = bdocpythonutils.BDocContainer()
        bdoc.load(bdocfile)
        bdoc.validateflex()
        _doc_count = len(bdoc.documents)
        if _doc_count == 0:
            raise Exception, "BDoc ei sisalda ühtegi andmefaili"
        ret = {}
        for el in bdoc.documents:
            evlog.log(evlogdata.get_vote(el, bdoc.documents[el]))
            ret[el] = bdoc.documents[el]

        return ret

    finally:
        if bdocfile != None:
            bdocfile.close()

def vote_with_signature(b64data, escaped_signature):
    import zipfile
    from xml.sax.saxutils import unescape

    sigfile = "META-INF/signatures0.xml"

    bdocdata = StringIO.StringIO(base64.b64decode(b64data))
    bdoczip = zipfile.ZipFile(bdocdata)

    # bdoczip already contains META-INF/signature0.xml, which we can't
    # delete/truncate, so we need to create a new zip and copy everything else
    # over.

    signedbdocdata = StringIO.StringIO()
    signedbdoczip = zipfile.ZipFile(signedbdocdata, "w")

    for entry in bdoczip.namelist():
        if entry != sigfile:
            signedbdoczip.writestr(entry, bdoczip.read(entry))
    signedbdoczip.writestr(sigfile, unescape(escaped_signature))

    signedbdoczip.close()
    bdoczip.close()
    return base64.b64encode(signedbdocdata.getvalue())

def challenge_ok(b64cert, mychal, ourchal, signature):

    import bdocpython
    if not signature:
        return False, 'DDS did not return signed challenge'

    bmychal = binascii.a2b_hex(mychal)
    bchal = binascii.a2b_hex(ourchal)

    if (bmychal != bchal[0:10]):
        return False, 'My challenge not present in our challenge'

    bcert = binascii.a2b_base64(b64cert)
    bsign = binascii.a2b_base64(signature)

    cv = bdocpython.ChallengeVerifier()
    cv.setCertificate(bcert)
    cv.setChallenge(bchal)
    cv.setSignature(bsign)
    res = cv.isChallengeOk()

    if not res:
        return False, cv.error

    return True, None



class MobileIDContext:

    phoneno = None
    lang = None
    challenge = None
    midsess = None
    origvote = None
    votefiles = {}
    __sessid = None
    __reg = None

    def __init__(self, sessid):
        if sessid == None:
            raise Exception('Puuduv sessiooniidentifikaator')
        self.__sessid = sessid
        self.__reg = Election().get_root_reg()
        self.lang = 'EST'

    def sessid(self):
        return self.__sessid

    def kill(self):
        self.__reg.ensure_no_key([evcommon.MIDSPOOL, self.__sessid])

    def set_phone(self, phone):
        self.phoneno = phone

    def set_origvote(self, hv):
        self.origvote = hv

    def get_origvote(self):
        self.origvote = self.__reg.read_value(\
                            [evcommon.MIDSPOOL, self.__sessid], \
                                                    'origvote').value
        return self.origvote

    def add_votefile(self, filename, data):
        self.votefiles[filename] = data

    def get_votefiles(self):
        for key in self.__reg.list_keys([evcommon.MIDSPOOL, self.__sessid, \
                'votefiles']):
            self.votefiles[key] = self.__reg.read_value(\
                    [evcommon.MIDSPOOL, self.__sessid, 'votefiles'], key).value
        return self.votefiles

    def generate_challenge(self):
        self.challenge = binascii.b2a_hex(os.urandom(10))

    def verify_challenge(self, signature):
        return challenge_ok(self.certificate(), self.mychallenge(), \
                            self.ourchallenge(), signature)

    def mychallenge(self):
        return self.__reg.read_value(\
                            [evcommon.MIDSPOOL, self.__sessid], \
                                    'mychallenge').value

    def ourchallenge(self):
        return self.__reg.read_value(\
                            [evcommon.MIDSPOOL, self.__sessid], \
                                    'ourchallenge').value

    def certificate(self):
        return self.__reg.read_value(\
                            [evcommon.MIDSPOOL, self.__sessid], \
                                    'cert').value

    def set_auth_succ(self):
        self.__reg.ensure_key([evcommon.MIDSPOOL, self.__sessid, 'authsucc'])

    def auth_succ(self):
        return self.__reg.check(\
                [evcommon.MIDSPOOL, self.__sessid, 'authsucc'])

    def save_post_auth(self, rsp):

        self.__reg.reset_key([evcommon.MIDSPOOL, self.__sessid])
        self.__reg.create_value([evcommon.MIDSPOOL, self.__sessid], \
                        'cert', rsp._CertificateData)

        self.__reg.create_value([evcommon.MIDSPOOL, self.__sessid], \
                        'phone', self.phoneno)

        self.__reg.create_value([evcommon.MIDSPOOL, self.__sessid], \
                        'midsess', rsp._Sesscode)

        self.__reg.create_value([evcommon.MIDSPOOL, self.__sessid], \
                        'mychallenge', self.challenge)

        self.__reg.create_value([evcommon.MIDSPOOL, self.__sessid], \
                        'ourchallenge', rsp._Challenge)

    def load_pre_sign(self):
        self.phoneno = self.__reg.read_value(\
                [evcommon.MIDSPOOL, self.__sessid], 'phone').value

    def save_post_sign(self, midsess):
        self.__reg.create_value([evcommon.MIDSPOOL, self.__sessid], \
                        'midsess', midsess)

        self.__reg.create_value([evcommon.MIDSPOOL, self.__sessid], \
                        'origvote', self.origvote)

        self.__reg.ensure_key([evcommon.MIDSPOOL, self.__sessid, 'votefiles'])
        for el in self.votefiles:
            self.__reg.create_value(\
                    [evcommon.MIDSPOOL, self.__sessid, 'votefiles'],\
                    el, self.votefiles[el])

    def load_pre_poll(self):
        self.midsess = int(self.__reg.read_value(\
                [evcommon.MIDSPOOL, self.__sessid], 'midsess').value)


class MobileIDService:

    url = None
    name = None
    auth_msg = None
    sign_msg = None
    srv = None
    dfs = {}

    def __init__(self):
        os.environ['MOBILE_ID_CONTEXT'] = '1'
        self.url = Election().get_mid_url()
        self.name = Election().get_mid_name()
        self.auth_msg, self.sign_msg = Election().get_mid_messages()
        loc = DigiDocServiceLocator()
        # self.fp = open('/tmp/debug.out', 'a')
        # kw = { 'tracefile': self.fp }
        kw = { }
        self.srv = loc.getDigiDocService(self.url, **kw)

    def add_file(self, name, data):
        self.dfs[name] = data

    def files(self):
        return len(self.dfs)

    def init_auth(self, ctx):
        request = MobileAuthenticate(\
                PhoneNo = ctx.phoneno, \
                Language = ctx.lang, \
                ServiceName = self.name, MessageToDisplay = self.auth_msg, \
                SPChallenge = ctx.challenge, \
                MessagingMode = 'asynchClientServer', ReturnCertData = True, \
                ReturnRevocationData = True)

        return self.srv.MobileAuthenticate(request)

    def init_sign(self, ctx):
        import hashlib

        datafiles = ddstypes.DataFileDigestList_Def("DataFiles")
        datafiles._DataFileDigest = []
        for el in self.dfs:
            digest = hashlib.sha256(self.dfs[el]).digest() # pylint: disable=E1101

            datafile = ddstypes.DataFileDigest_Def("DataFileDigest")
            datafile._Id = el
            datafile._DigestType = "sha256"
            datafile._DigestValue = base64.b64encode(digest)

            datafiles._DataFileDigest.append(datafile)

        req = MobileCreateSignature(\
                SignersCountry = "EE", \
                PhoneNo = ctx.phoneno, \
                Language = ctx.lang, \
                ServiceName = self.name, \
                MessageToDisplay = self.sign_msg, \
                DataFiles = datafiles, \
                Format = "BDOC", \
                Version = "2.1", \
                SignatureID = "S0", \
                MessagingMode = "asynchClientServer")
        rsp = self.srv.MobileCreateSignature(req)

        if rsp._Status != 'OK':
            return False, rsp._Status, None

        return True, rsp._Sesscode, rsp._ChallengeID

    def poll_auth(self, ctx):
        request = GetMobileAuthenticateStatus(\
                Sesscode = ctx.midsess, WaitSignature = False)
        return self.srv.GetMobileAuthenticateStatus(request)

    def poll_sign(self, ctx):
        req = GetMobileCreateSignatureStatus(\
                Sesscode = ctx.midsess, WaitSignature = False)
        rsp = self.srv.GetMobileCreateSignatureStatus(req)

        return rsp._Status, rsp._Signature


class MIDDispatcher:

    def __init__(self):
        evlog.AppLog().set_app('MID')
        self.__ctx = None

    def ctx(self):
        if not self.__ctx:
            self.__ctx = MobileIDContext(sessionid.voting())
        return self.__ctx

    def __return_exception(self):
        evlog.log_exception()
        r1, r2 = protocol.plain_error_technical(evcommon.EVOTE_MID_ERROR)
        return self.__return_error(r1, r2)

    def __return_error(self, errcode, msg):
        evlog.log_error('Teade Valija rakendusele: "%s"' % msg)
        if self.__ctx:
            self.__ctx.kill()
        return protocol.msg_error(errcode, msg)

    def __return_zsi_error(self, exc):

        fault = "%s" % exc

        evlog.log_error("Exception: %s" % fault)

        # 301 comes from MobileAuthenticate
        # 201 comes from GetMobileCertificate
        # both mean that the user is not MID client
        if fault.startswith('301') or fault.startswith('201'):
            return self.__return_error(evcommon.EVOTE_MID_ERROR, \
                                            get_mid_text('MID_ERROR_301'))

        elif fault.startswith('302'):
            return self.__return_error(evcommon.EVOTE_MID_ERROR, \
                                            get_mid_text('MID_ERROR_302'))

        elif fault.startswith('303'):
            return self.__return_error(evcommon.EVOTE_MID_ERROR, \
                                            get_mid_text('MID_ERROR_303'))

        return self.__return_error(evcommon.EVOTE_MID_ERROR, \
                                            get_mid_text('MID_UNKNOWN_ERROR'))

    def __return_mid_error(self, status):
        return self.__return_error(evcommon.EVOTE_MID_ERROR, \
                                            get_mid_text(status))


    def __return_badstatusline_error(self, exc):
        evlog.log_error('Vigane HTTP status-line: "%s"' % exc.line)
        return self.__return_mid_error('MID_UNKNOWN_ERROR')

    def init_sign(self, form):
        try:
            evlog.log('Signeerimispäring: ALGUS')
            if not self.ctx().auth_succ():
                raise Exception('Autentimata sessioon')

            self.ctx().load_pre_sign()
            service = MobileIDService()

            for el in form:
                if el == evcommon.POST_SESS_ID:
                    pass
                elif el == evcommon.POST_EVOTE:
                    b64 = form.getvalue(el)
                    votes = mobid_vote_data(b64)
                    for el in votes:
                        vote = votes[el]
                        service.add_file(el, vote)
                        self.ctx().add_votefile(el, vote)
                    self.ctx().set_origvote(b64)
                else:
                    raise Exception('Vigane päringuparameeter %s' % el)

            if service.files() < 1:
                raise Exception('Ei ole hääli, mida signeerida')

            r1, r2, r3 = service.init_sign(self.ctx())

            if r1:
                self.ctx().save_post_sign(r2)
                evlog.log('Signeerimispäring (%s)' % r2)
                return protocol.msg_mobid_sign_init_ok(r3)

            return self.__return_mid_error(r2)

        except httplib.BadStatusLine, exc:
            return self.__return_badstatusline_error(exc)
        except ZSI.FaultException, exc:
            return self.__return_zsi_error(exc)
        except:
            return self.__return_exception()
        finally:
            evlog.log('Signeerimispäring: LÕPP')


    def init_auth(self, phone):

        try:
            evlog.log("Autentimispäring: ALGUS %s" % (phone))
            if not ElectionState().election_on():
                r1, r2 = ElectionState().election_off_msg()
                evlog.log_error('Viga operatsioonil "cand", teade "%s"' % r2)
                return protocol.msg_error(r1, r2)

            self.ctx().set_phone(phone)
            self.ctx().generate_challenge()
            service = MobileIDService()

            rsp = service.init_auth(self.ctx())
            if rsp._Status == 'OK':
                rsp._CertificateData = rsp._CertificateData.strip()

                self.ctx().save_post_auth(rsp)

                alog, elog = evlogdata.get_cert_data_log(
                        rsp._CertificateData, 'cand/auth', True)

                evlog.log('Autentimispäring (%s, %s, %s, %s)' % \
                    (rsp._UserIDCode, rsp._UserGivenname, \
                    rsp._UserSurname, rsp._Challenge))

                evlog.log(alog)
                if elog:
                    evlog.log_error(elog)

                return protocol.msg_mobid_auth_init_ok(\
                    self.ctx().sessid(), rsp._ChallengeID)

            return self.__return_mid_error(rsp._Status)

        except httplib.BadStatusLine, exc:
            return self.__return_badstatusline_error(exc)
        except ZSI.FaultException, exc:
            return self.__return_zsi_error(exc)
        except:
            return self.__return_exception()
        finally:
            evlog.log('Autentimispäring: LÕPP')

    def __export_certificate(self):
        cert = '-----BEGIN CERTIFICATE-----\n' + \
            self.ctx().certificate() + '\n-----END CERTIFICATE-----\n'
        os.environ[evcommon.HTTP_CERT] = cert

    def __get_candidate_list(self):
        self.__export_certificate()
        hesd = hesdisp.HESVoterDispatcher()
        self.ctx().set_auth_succ()
        return hesd.get_candidate_list()

    def __hts_vote(self, signature):
        origvote = self.ctx().get_origvote()
        self.__export_certificate()
        self.ctx().kill()

        vote = vote_with_signature(origvote, signature)
        hesd = hesdisp.HESVoterDispatcher()
        return hesd.hts_vote(vote, origvote)

    def __poll_auth(self):
        service = MobileIDService()
        rsp = service.poll_auth(self.ctx())

        if rsp._Status == 'OUTSTANDING_TRANSACTION':
            return protocol.msg_mobid_poll()

        if rsp._Status == 'USER_AUTHENTICATED':
            evlog.log('Received USER_AUTHENTICATED from DDS')
            c1, c2 = self.ctx().verify_challenge(rsp._Signature)
            if not c1:
                evlog.log_error(c2)
                return self.__return_mid_error('Autentimine ebaõnnestus')

            return self.__get_candidate_list()

        return self.__return_mid_error(rsp._Status)

    def __poll_sign(self):
        service = MobileIDService()
        r1, r2 = service.poll_sign(self.ctx())

        if r1 == 'OUTSTANDING_TRANSACTION':
            return protocol.msg_mobid_poll()

        if r1 == 'SIGNATURE':
            evlog.log('Received SIGNATURE from DDS')
            return self.__hts_vote(r2)

        return self.__return_mid_error(r1)


    def poll(self):

        try:
            evlog.log('Poll: ALGUS')
            self.ctx().load_pre_poll()

            if self.ctx().auth_succ():
                return self.__poll_sign()
            return self.__poll_auth()

        except httplib.BadStatusLine, exc:
            return self.__return_badstatusline_error(exc)
        except ZSI.FaultException, exc:
            return self.__return_zsi_error(exc)
        except:
            return self.__return_exception()
        finally:
            evlog.log('Poll: LÕPP')


if __name__ == "__main__":
    pass

# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = vote_analyzer
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

def analyze(ik, vote, votebox):

    return []


########NEW FILE########
__FILENAME__ = hlr
#!/usr/bin/python2.7
# -*- encoding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import os
import sys
import subprocess
import base64
import time

from election import Election
import evlog
import evreg
import ksum
import evcommon

import inputlists
import formatutil

VOTING_ID_LENGTH = 28
DECRYPT_PROGRAM = "threaded_decrypt"
SIGN_PROGRAM = "sign_data"
CORRUPTED_VOTE = "xxx"

CERT_PATH = "/usr/lunasa/cert/vvk.der"
CERT = "vvk.der"

README_PATH = "/usr/share/doc/evote-hlr/README"
README = "README"


ENV_EVOTE_TMPDIR = "EVOTE_TMPDIR"

G_DECRYPT_ERRORS = {1: 'Dekrüpteerija sai vale arvu argumente',
    2: 'Häälte faili ei önnestunud lugemiseks avada',
    3: 'Dekrüptitud häälte faili ei õnnestunud kirjutamiseks avada',
    4: 'Häälte failis puudus versiooni number',
    5: 'Häälte failis puudus valimiste identifikaator',
    6: 'Viga sisendi lugemisel',
    7: 'Viga väljundi kirjutamisel',
    8: 'Häälte faili rida ei vastanud formaadile',
    9: 'Dekrüpteerija ebaõnnestus'}


G_SIGN_ERRORS = {1: 'Allkirjastaja sai vale arvu argumente',
    2: 'Tulemusfaili ei önnestunud lugemiseks avada',
    3: 'Allkirjafaili ei õnnestunud kirjutamiseks avada',
    4: 'Viga sisendi lugemisel',
    5: 'Viga väljundi kirjutamisel',
    6: 'Allkirjastaja ebaõnnestus'}


class DecodedVoteList(inputlists.InputList):

    def __init__(self, vote_handler, jsk=None):
        inputlists.InputList.__init__(self)
        self.name = 'Dekrüpteeritud häälte nimekiri'
        self.jsk = jsk
        self._vote_handler = vote_handler

    def checkuniq(self, line):
        return True

    def dataline(self, line):
        lst = line.split('\t')
        if not len(lst) == 6:
            self.errform('Kirjete arv real')
            return False
        if not formatutil.is_jaoskonna_number_kov_koodiga(lst[0], lst[1]):
            self.errform('Valimisjaoskonna number KOV koodiga')
            return False
        if not formatutil.is_ringkonna_number_kov_koodiga(lst[2], lst[3]):
            self.errform('Ringkonna number KOV koodiga')
            return False
        if not formatutil.is_base64(lst[4]):
            self.errform('Algne hääl')
            return False
        if not formatutil.is_base64(lst[5]):
            self.errform('Dekrüpteeritud hääl')
            return False
        if self.jsk:
            if not self.jsk.has_ring((lst[2], lst[3])):
                self.errcons('Olematu ringkond')
                return False
            if not self.jsk.has_stat((lst[2], lst[3]), (lst[0], lst[1])):
                self.errcons('Olematu jaoskond')
                return False

        if not self._vote_handler.handle_vote(lst, self.processed()):
            self.errcons('Viga hääle käitlemisel')
            return False

        return True


def ringkonnad_cmp(dist1, dist2):
    i1 = int(dist1[0])
    i2 = int(dist2[0])
    if (i1 != i2):
        return i1 - i2
    else:
        j1 = int(dist1[1])
        j2 = int(dist2[1])
        return j1 - j2
    return 0


def valikud_cmp(choi1, choi2):
    code1 = choi1.split('.')[1]
    code2 = choi2.split('.')[1]
    if (code1 == 'kehtetu') or (code2 == 'kehtetu'):
        if code1 == code2:
            return 0
        if code1 == 'kehtetu':
            return 1
        return -1
    return int(code1) - int(code2)


class ChoicesCounter:

    def __init__(self):
        self.__cdata = {}
        self.__ddata = {}
        self.__count = 0

    def add_vote(self, ring, stat, choice):
        self.__cdata[ring][stat][choice] += 1
        self.__ddata[ring][choice] += 1

    def _to_key(self, reg_key):
        lst = reg_key.split('_')
        return (lst[0], lst[1])

    def load(self, reg):
        for rk in reg.list_keys(['hlr', 'choices']):
            r_key = self._to_key(rk)
            self.__cdata[r_key] = {}
            if not r_key in self.__ddata:
                self.__ddata[r_key] = {}
            for stat in reg.list_keys(['hlr', 'choices', rk]):
                d_key = self._to_key(stat)
                self.__cdata[r_key][d_key] = {}
                for choi in reg.list_keys(['hlr', 'choices', rk, stat]):
                    self.__cdata[r_key][d_key][choi] = 0
                    if not choi in self.__ddata[r_key]:
                        self.__ddata[r_key][choi] = 0

    def has_ring(self, ring):
        return (ring in self.__cdata)

    def has_stat(self, ring, stat):
        return (stat in self.__cdata[ring])

    def has_choice(self, ring, stat, choice):
        return (choice in self.__cdata[ring][stat])

    def count(self):
        return self.__count

    def _sort(self, lst, cmp_method):
        keys = lst.keys()
        keys.sort(cmp_method)
        return keys

    def outputstat(self, out_f):
        self.__count = 0

        for rk in self._sort(self.__cdata, ringkonnad_cmp):
            for stat in self._sort(self.__cdata[rk], ringkonnad_cmp):
                for choice in self._sort(self.__cdata[rk][stat], valikud_cmp):
                    self.__count += self.__cdata[rk][stat][choice]
                    count_line = [stat[0], stat[1], rk[0], rk[1],
                        str(self.__cdata[rk][stat][choice]),
                        choice.split('.')[1]]
                    out_f.write("\t".join(count_line) + "\n")

    def outputdist(self, out_f):
        for rk in self._sort(self.__ddata, ringkonnad_cmp):
            for choice in self._sort(self.__ddata[rk], valikud_cmp):
                count_line = [rk[0], rk[1],
                    str(self.__ddata[rk][choice]),
                    choice.split('.')[1]]
                out_f.write("\t".join(count_line) + "\n")


def _sig(inf):
    return "%s.sig" % inf

class HLR:
    """
    Häältelugemisrakendus
    """

    def __init__(self, elid, tmpdir):

        self._elid = elid
        evlog.AppLog().set_app('HLR', self._elid)
        self._reg = Election().get_sub_reg(self._elid)
        self._log4 = evlog.Logger('log4')
        self._log5 = evlog.Logger('log5')
        self._log4.set_format(evlog.EvLogFormat())
        self._log5.set_format(evlog.EvLogFormat())
        self._log4.set_logs(self._reg.path(['common', 'log4']))
        self._log5.set_logs(self._reg.path(['common', 'log5']))

        tmpreg = evreg.Registry(root=tmpdir)
        tmpreg.ensure_key([])
        tmpreg.delete_sub_keys([])
        self.output_file = tmpreg.path(['decrypted_votes'])
        self.decrypt_prog = DECRYPT_PROGRAM
        self.sign_prog = SIGN_PROGRAM
        self.__cnt = ChoicesCounter()

    def __del__(self):
        try:
            os.remove(self.output_file)
        except:
            pass

    def _decrypt_votes(self, pin):

        input_file = self._reg.path(['hlr', 'input', 'votes'])
        token_name = Election().get_hsm_token_name()
        priv_key_label = Election().get_hsm_priv_key()
        pkcs11lib = Election().get_pkcs11_path()
        args = [input_file, self.output_file, \
            token_name, priv_key_label, pin, pkcs11lib]

        exit_code = 0

        try:
            exit_code = subprocess.call([self.decrypt_prog] + args)
        except OSError, oserr:
            errstr = "Häälte faili '%s' dekrüpteerimine nurjus: %s" % \
                (input_file, oserr)
            evlog.log_error(errstr)
            return False

        if exit_code == 0:
            return True

        if exit_code > 0:
            errstr2 = "Tundmatu viga"
            if exit_code in G_DECRYPT_ERRORS:
                errstr2 = G_DECRYPT_ERRORS[exit_code]

            errstr = \
                "Häälte faili '%s' dekrüpteerimine nurjus: %s (kood %d)" % \
                (input_file, errstr2, exit_code)
            evlog.log_error(errstr)
            return False

        errstr = "Häälte faili '%s' dekrüpteerimine nurjus (signaal %d)" % \
                (input_file, exit_code)
        evlog.log_error(errstr)
        return False


    def _sign_result(self, pin, input_file):

        token_name = Election().get_hsm_token_name()
        priv_key_label = Election().get_hsm_priv_key()
        pkcs11lib = Election().get_pkcs11_path()
        args = [input_file, _sig(input_file), \
            token_name, priv_key_label, pin, pkcs11lib]

        exit_code = 0

        try:
            exit_code = subprocess.call([self.sign_prog] + args)
        except OSError, oserr:
            errstr = "Tulemuste faili '%s' allkirjastamine nurjus: %s" % \
                (input_file, oserr)
            evlog.log_error(errstr)
            return False

        if exit_code == 0:
            return True

        if exit_code > 0:
            errstr2 = "Tundmatu viga"
            if exit_code in G_SIGN_ERRORS:
                errstr2 = G_SIGN_ERRORS[exit_code]

            errstr = \
                "Tulemuste faili '%s' allkirjastamine nurjus: %s (kood %d)" % \
                (input_file, errstr2, exit_code)
            evlog.log_error(errstr)
            return False

        errstr = "Tulemuste faili '%s' allkirjastamine nurjus (signaal %d)" % \
                (input_file, exit_code)
        evlog.log_error(errstr)
        return False

    def _sign_result_files(self, pin):
        f1 = self._reg.path(\
                ['hlr', 'output', evcommon.ELECTIONRESULT_FILE])
        f2 = self._reg.path(\
                ['hlr', 'output', evcommon.ELECTIONRESULT_STAT_FILE])

        ret1 = self._sign_result(pin, f1)
        ret2 = self._sign_result(pin, f2)

        if (ret1 and ret2):
            import zipfile
            zippath = self._reg.path(\
                ['hlr', 'output', evcommon.ELECTIONRESULT_ZIP_FILE])
            rzip = zipfile.ZipFile(zippath, "w")
            rzip.write(f1, evcommon.ELECTIONRESULT_FILE)
            rzip.write(_sig(f1), _sig(evcommon.ELECTIONRESULT_FILE))
            rzip.write(f2, evcommon.ELECTIONRESULT_STAT_FILE)
            rzip.write(_sig(f2), _sig(evcommon.ELECTIONRESULT_STAT_FILE))

            if os.path.isfile(CERT_PATH) and os.access(CERT_PATH, os.R_OK):
                rzip.write(CERT_PATH, CERT)

            if os.path.isfile(README_PATH) and os.access(README_PATH, os.R_OK):
                rzip.write(README_PATH, README)

            rzip.close()
            return True
        else:
            return False


    def _add_kehtetu(self, ringkond, district):
        self.__cnt.add_vote(ringkond, district, ringkond[0] + ".kehtetu")

    def _check_vote(self, ringkond, district, haal, line_nr):

        ret = True
        if haal == CORRUPTED_VOTE:
            errstr = "Häält (rida=%d) ei õnnestunud dekrüptida" % line_nr
            evlog.log_error(errstr)
            ret = False
        else:
            lst = haal.split('\n')
            if ((len(lst) != 4) or \
                (lst[0] != evcommon.VERSION) or \
                (lst[1] != self._elid) or \
                (lst[3] != "")):
                ret = False
            else:
                if not formatutil.is_valiku_kood(lst[2]):
                    ret = False
                elif lst[2].split(".")[0] != ringkond[0]:
                    ret = False

        if ret and self.__cnt.has_choice(ringkond, district, lst[2]):
            self.__cnt.add_vote(ringkond, district, lst[2])
        else:
            ret = False
            self._add_kehtetu(ringkond, district)

        return ret

    def handle_vote(self, votelst, line_nr):
        try:
            dist = (votelst[0], votelst[1])
            ring = (votelst[2], votelst[3])
            vote = base64.decodestring(votelst[5])
            if not self._check_vote(ring, dist, vote, line_nr):
                self._log4.log_info(
                        tyyp=4,
                        haal=base64.decodestring(votelst[4]),
                        ringkond_omavalitsus=votelst[2],
                        ringkond=votelst[3])
            else:
                self._log5.log_info(
                        tyyp=5,
                        haal=base64.decodestring(votelst[4]),
                        ringkond_omavalitsus=votelst[2],
                        ringkond=votelst[3])
            return True
        except:
            evlog.log_exception()
            return False

    def _count_votes(self):
        dvl = DecodedVoteList(self, self.__cnt)
        dvl.attach_logger(evlog.AppLog())
        dvl.attach_elid(self._elid)
        if not dvl.check_format(self.output_file, 'Loen hääli: '):
            evlog.log_error('Häälte lugemine ebaõnnestus')
            return False
        return True

    def _write_result(self):
        result_dist_fn = self._reg.path(\
                ['hlr', 'output', evcommon.ELECTIONRESULT_FILE])
        out_f = file(result_dist_fn, 'w')
        out_f.write(evcommon.VERSION + '\n' + self._elid + '\n')
        self.__cnt.outputdist(out_f)
        out_f.close()
        ksum.store(result_dist_fn)

        result_stat_fn = self._reg.path(\
                ['hlr', 'output', evcommon.ELECTIONRESULT_STAT_FILE])
        out_f = file(result_stat_fn, 'w')
        out_f.write(evcommon.VERSION + '\n' + self._elid + '\n')
        self.__cnt.outputstat(out_f)
        out_f.close()
        ksum.store(result_stat_fn)

        print "Hääled (%d) on loetud." % self.__cnt.count()

    def _check_logs(self):
        log_lines = 0
        log_lines = log_lines + self._log4.lines_in_file()
        log_lines = log_lines + self._log5.lines_in_file()
        # remove header
        log_lines = log_lines - 6
        if log_lines != self.__cnt.count():
            errstr = \
                "Log4 ja Log5 ridade arv (%d) "\
                    "ei klapi häälte arvuga (%d)" % \
                        (log_lines, self.__cnt.count())
            evlog.log_error(errstr)
            return False
        return True

    def _create_logs(self):
        with open(self._reg.path(['common','log4']),'w') as log4_f:
            log4_f.write(evcommon.VERSION + "\n")
            log4_f.write(self._elid + "\n")
            log4_f.write("4\n")
        with open(self._reg.path(['common','log5']),'w') as log5_f:
            log5_f.write(evcommon.VERSION + "\n")
            log5_f.write(self._elid + "\n")
            log5_f.write("5\n")
        return True

    def run(self, pin):
        try:
            self.__cnt.load(self._reg)
            if not self._decrypt_votes(pin):
                return False
            if not self._create_logs():
                return False
            if not self._count_votes():
                return False
            self._write_result()
            if not self._check_logs():
                return False
            if not self._sign_result_files(pin):
                return False
            return True
        except:
            evlog.log_exception()
            return False


def usage():
    print "Kasutamine:"
    print "    %s <valimiste-id> <PIN>" % sys.argv[0]
    sys.exit(1)


def main_function():
    if len(sys.argv) != 3:
        usage()

    start_time = time.time()

    # See on kataloom (mälufailisüsteem) kus vahetulemusi hoiame.
    if not ENV_EVOTE_TMPDIR in os.environ:
        print 'Keskkonnamuutuja %s seadmata\n' % (ENV_EVOTE_TMPDIR)
        sys.exit(1)

    _hlr = HLR(sys.argv[1], os.environ[ENV_EVOTE_TMPDIR])
    retval = _hlr.run(sys.argv[2])

    print time.strftime("\nAega kulus %H:%M:%S", \
            time.gmtime(long(time.time() - start_time)))

    if retval:
        print 'Häälte lugemine õnnestus'
        sys.exit(0)

    print 'Häälte lugemine ebaõnnestus'
    print 'Viimane viga: %s' % evlog.AppLog().last_message()
    sys.exit(1)


if __name__ == '__main__':
    main_function()

# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = hts
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import ksum
import ticker
import os
import htscommon
import base64
import inputlists
import fcntl
import evcommon
import htsbase
import evlog
import formatutil
import zipfile
import StringIO
import time
from operator import itemgetter


def _file2pdf(input_fn, output_fn):
    import subprocess

    error = False
    errstr = ''
    try:
        retcode = subprocess.call(\
            ["rst2pdf", "-s", "dejavu", input_fn, "-o", output_fn, "-v"])
        if retcode != 0:
            error = True
    except OSError, ose:
        error = True
        errstr += str(ose)

    if error:
        try:
            os.unlink(output_fn)
        except:
            pass

        raise Exception(retcode, errstr)



def jaoskonnad_cmp(jsk1, jsk2):
    list1 = jsk1.split('\t')
    list2 = jsk2.split('\t')
    for i in range(4):
        i1 = int(list1[i])
        i2 = int(list2[i])
        if (i1 != i2):
            return i1 - i2
    return 0

def reanumber_cmp(el1, el2):

    has_el1 = False
    has_el2 = False

    int_el1 = 0
    int_el2 = 0

    try:
        int_el1 = int(el1['reanumber'])
        has_el1 = True
    except:
        has_el1 = False

    try:
        int_el2 = int(el2['reanumber'])
        has_el2 = True
    except:
        has_el2 = False

    if has_el1:
        if has_el2:
            return int_el1 - int_el2
        else:
            return -1
    else:
        if has_el2:
            return 1
        else:
            return 0

    return 0


class HTS(htsbase.HTSBase):

    def __init__(self, elid):
        htsbase.HTSBase.__init__(self, elid)

    def _write_atomic(self, filename, data):
        tmp_name = filename + '.partial'
        try:
            _f = open(tmp_name, 'w')
            fcntl.lockf(_f, fcntl.LOCK_EX)
            _f.write(data)
            _f.flush()
            os.fsync(_f.fileno())
            _f.close()
            os.rename(tmp_name, filename)
        except Exception, (errno, errstr):
            evlog.log_error("Faili '%s' kirjutamine nurjus" % filename)
            raise Exception(errno, errstr)

    def talleta_haal(self, **args):
        haale_rasi = ksum.votehash(args['vote'])
        user_key = htscommon.get_user_key(args['signercode'])
        self._reg.ensure_key(user_key)
        voter = args['valija']
        vote_file = htscommon.valid_votefile_name(args['timestamp'])
        user_key.append(vote_file)
        filename = self._reg.path(user_key)

        frm = evlog.EvLogFormat()
        logline = frm.logstring(
            tyyp=0,
            haal_rasi=haale_rasi,
            timestamp=args['timestamp'],
            jaoskond=voter['jaoskond'],
            jaoskond_omavalitsus=voter['jaoskond_omavalitsus'],
            ringkond=voter['ringkond'],
            ringkond_omavalitsus=voter['ringkond_omavalitsus'],
            isikukood=args['signercode'],
            nimi=voter['nimi'],
            reanumber=voter['reanumber'])

        outdata = StringIO.StringIO()
        outzip = zipfile.ZipFile(outdata, 'w')
        outzip.writestr(htscommon.ZIP_BDOCFILE, args['signedvote'])
        outzip.writestr(htscommon.ZIP_LOGFILE, logline)
        outzip.close()
        self._write_atomic(filename, outdata.getvalue())


    def get_vote_for_result(self, logline, fname):
        res = None
        try:
            elems = logline.split('\t')
            code = elems[6]
            user_key = htscommon.get_user_key(code)
            fn = self._reg.path(user_key + [fname])
            bdoc = htsbase.get_vote(fn)
            if bdoc:
                haal = bdoc.documents["%s.evote" % self._elid]
                voter = htscommon.get_logline_voter(logline)
                b64haal = base64.b64encode(haal).strip()
                res = [voter['jaoskond_omavalitsus'], voter['jaoskond'], \
                    voter['ringkond_omavalitsus'], voter['ringkond'], b64haal]
        except:
            evlog.log_exception()

        return res


    def __write_masinloetav(self, jaoskonnad):

        # sortimine:
        # Kov-jsk numbriliselt -> hääletajad ridade kaupa

        ret = 0
        kov_jsk = jaoskonnad.keys()
        kov_jsk.sort(jaoskonnad_cmp)

        of = htscommon.LoggedFile(\
            self._reg.path(\
                ['hts', 'output', evcommon.ELECTORSLIST_FILE]))
        of.open('w')
        of.write(evcommon.VERSION + "\n")
        of.write(self._elid + "\n")

        for jsk in kov_jsk:
            if (len(jaoskonnad[jsk])):
                jaoskonnad[jsk].sort(reanumber_cmp)
                for voter in jaoskonnad[jsk]:
                    outline = '%s\t%s\t%s\t%s\t%s\n' % (
                                voter['jaoskond_omavalitsus'],
                                voter['jaoskond'],
                                voter['reanumber'],
                                voter['isikukood'],
                                voter['nimi'])
                    of.write(outline)
                    ret = ret + 1

        of.close()
        ksum.store(of.name())
        return ret

    def __write_inimloetav(self, jaoskonnad):

        # sortimine:
        #  Maakond -> Vald -> Kov-jsk numbriliselt -> hääletajad ridade kaupa

        ret = 0

        tmp_path = self._reg.path(\
                ['hts', 'output', evcommon.ELECTORSLIST_FILE_TMP])

        pdf_path = self._reg.path(\
                ['hts', 'output', evcommon.ELECTORSLIST_FILE_PDF])

        outfile = htscommon.LoggedFile(tmp_path)
        outfile.open('w')

        # ReStructuredText jalus leheküljenumbritega
        outfile.write(".. footer::\n\tLk ###Page###\n\n")

        description = ''
        try:
            description = \
                self._reg.read_string_value(['common'], 'description').value
        except:
            description = self._elid

        maakonnad = jaoskonnad.keys()
        import locale
        try:
            locale.setlocale(locale.LC_COLLATE, 'et_EE.UTF-8')
            maakonnad.sort(locale.strcoll)
        except:
            maakonnad.sort()

        dot_line = "---------------------------------------" + \
                   "--------------------------------------"
        for mk in maakonnad:
            vallad = jaoskonnad[mk].keys()
            vallad.sort(locale.strcoll)
            for vald in vallad:
                kov_jsk = jaoskonnad[mk][vald].keys()
                kov_jsk.sort(jaoskonnad_cmp)
                for jsk in kov_jsk:
                    outfile.write('E-hääletanute nimekiri\n\n')
                    outfile.write('%s\n\n' % description)
                    outfile.write('%s\n\n' % jaoskonnad[mk][vald][jsk][0])
                    outfile.write('| %s\n| %-15s%-16s%s\n| %s\n\n' % \
                        (dot_line, 'Nr val nimek', \
                        'Isikukood', 'Nimi', dot_line))

                    if (len(jaoskonnad[mk][vald][jsk][1])):
                        jaoskonnad[mk][vald][jsk][1].sort(reanumber_cmp)
                        for voter in jaoskonnad[mk][vald][jsk][1]:
                            outline = '| %-15s%-16s%s\n' % (
                                voter['reanumber'],
                                voter['isikukood'],
                                voter['nimi'])
                            outfile.write(outline)
                            ret = ret + 1
                    else:
                        outfile.write(\
                            '<<< Jaoskonnas pole ühtegi e-häält >>>\n')
                    outfile.write('\n.. raw:: pdf\n\n\tPageBreak\n\n')

        outfile.close()

        _file2pdf(tmp_path, pdf_path)
        return ret


    def __load_jaoskonnad(self, jsk, jsk_rev):
        dist = inputlists.Districts()
        dist.load(evcommon.APPTYPE_HTS, self._reg)
        # jaoskonnad = {
        #   'maakonna nimi': {
        #      'vald': {
        #         kov-jsk: ['jaoskonna string', [hääletajate list]]
        #       }
        #     }
        #   }
        #
        # jaoskonnad_rev viitab otse jaoskondadele

        for i in dist.district_list:

            split_district = dist.district_list[i][0].rsplit(',', 1)

            mk = dist.district_list[i][1]
            jsk_nr = '\t'.join(i.split('\t')[0:2])
            if jsk_nr == '0\t0':
                mk = 'ZZZ'

            if not  mk in jsk:
                jsk[mk] = {}

            vald = split_district[0]
            if mk == 'ZZZ':
                vald = 'ZZZ'

            if not vald in jsk[mk]:
                jsk[mk][vald] = {}

            if not i in jsk[mk][vald]:
                jsk[mk][vald][i] = [dist.district_list[i][0], []]
            else:
                self._errmsg = 'Viga andmestruktuurides (%s)' % jsk_nr
                raise Exception(self._errmsg)

            jsk_rev[i] = jsk[mk][vald][i][1]


    def get_log_lines(self, root, path):
        log_lines = []
        for vote_file in path:
            if htscommon.VALID_VOTE_PATTERN.match(vote_file):
                inzip = None
                lline = None
                try:
                    lname = root + '/' + vote_file
                    inzip = zipfile.ZipFile(lname, 'r')
                    lline = inzip.read(htscommon.ZIP_LOGFILE)
                except:
                    lline = None
                    evlog.log_error("Viga hääle käitlemisel: " + lname)
                    evlog.log_exception()

                if inzip:
                    inzip.close()

                if lline:
                    log_lines.append((lline, vote_file))

        return log_lines


    def tyhistusperioodi(self):

        vc_valid = 0
        vc_autor = 0

        jaoskonnad = {}
        jaoskonnad_rev = {}
        self.__load_jaoskonnad(jaoskonnad, jaoskonnad_rev)
        tic = ticker.Counter(\
            'Hääli:', '\tArvesse minevaid: %d\tKorduvaid: %d')
        tic.start('Koostan e-hääletanute nimekirja:')

        for path in os.walk(self._reg.path(['hts', 'votes'])):
            root = path[0]
            code = root.split('/').pop()

            if not formatutil.is_isikukood(code):
                continue

            log_lines = self.get_log_lines(root, path[2])

            if len(log_lines) > 0:
                log_lines.sort(key=itemgetter(0))
                latest = log_lines.pop()
                vc_autor += len(log_lines)
                vc_valid += 1

                voter = htscommon.get_logline_voter(latest[0])
                jaoskonnad_rev['%s\t%s\t%s\t%s' % (\
                    voter['jaoskond_omavalitsus'], \
                    voter['jaoskond'], voter['ringkond_omavalitsus'], \
                    voter['ringkond'])].append(voter)

            tic.tick(1, vc_valid, vc_autor)

        tic.finish()

        valijaid1 = self.__write_masinloetav(jaoskonnad_rev)
        valijaid2 = self.__write_inimloetav(jaoskonnad)
        if not (valijaid1 == valijaid2):
            self._errmsg = 'Viga nimekirjade koostamisel'
            raise Exception(self._errmsg)

        return vc_valid + vc_autor, vc_autor, valijaid1


    def lugemisperioodi(self):

        r_votes = 0
        v_votes = 0
        a_votes = 0
        b_votes = 0

        self._reg.ensure_no_key(\
            ['hts', 'output', evcommon.ELECTIONS_RESULT_FILE])

        vf = htscommon.LoggedFile(\
            self._reg.path(\
                ['hts', 'output', evcommon.ELECTIONS_RESULT_FILE]))
        vf.open('a')
        vf.write(evcommon.VERSION + "\n")
        vf.write(self._elid + "\n")

        l1_lines = []
        l2_lines = []
        l3_lines = []

        tic = ticker.Counter(\
            'Hääli:', '\tKehtivaid: %d\tAvalduse alusel tühistatuid: %d')
        tic.start('Koostan loendamisele minevate häälte nimekirja')

        nowstr = time.strftime("%Y%m%d%H%M%S")

        for path in os.walk(self._reg.path(['hts', 'votes'])):
            root = path[0]
            code = root.split('/').pop()

            if not formatutil.is_isikukood(code):
                continue

            log_lines = self.get_log_lines(root, path[2])

            if len(log_lines) > 0:
                log_lines.sort(key=itemgetter(0), reverse=True)
                new = None
                for lines in log_lines:
                    old = lines[0].rsplit('\t', 2)[0]
                    notime = old.split('\t', 1)[1]
                    fn = lines[1]
                    voteforres = self.get_vote_for_result(old, fn)
                    if voteforres:
                        l1_lines.append(old)
                        if new == None:
                            ur, reason, tim = self.is_user_revoked(code)
                            if ur:
                                l2_lines.append("%s\t%s\t%s" % (tim, notime, reason))
                                r_votes += 1
                            else:
                                vf.write('\t'.join(voteforres) + '\n')
                                v_votes += 1
                                l3_lines.append("%s\t%s" % (nowstr, notime))
                        else:
                            autor = new.split('\t')
                            l2_lines.append("%s\t%s\tkorduv e-hääl: %s" % \
                                    (autor[0], notime, autor[1]))
                            a_votes += 1
                        new = old
                    else:
                        b_votes += 1

                tic.tick(1, v_votes, r_votes)

        vf.close()
        ksum.store(vf.name())
        tic.finish()

        l1_lines.sort()
        self.save_log(l1_lines, '1')
        l2_lines.sort()
        self.save_log(l2_lines, '2')
        l3_lines.sort()
        self.save_log(l3_lines, '3')
        return v_votes, r_votes, a_votes, b_votes


    def load_revoke(self, input_list, operator):
        good_list = []
        bad_list = []
        for el in input_list:
            code = el[0]
            if not self.haaletanud(code):
                bad_list.append(el)
                evlog.log_error('Isik koodiga %s ei ole hääletanud' % code)
                continue

            revoked, reason, _ = self.is_user_revoked(code)
            if revoked:
                bad_list.append(el)
                evlog.log_error(\
                    'Kasutaja isikukoodiga %s hääl on juba tühistatud' % code)
            else:
                # vajalik lugemisele minevate häälte nimistu koostamiseks
                self.revoke_vote(el, operator)
                good_list.append(el)

        return good_list, bad_list


    def load_restore(self, input_list, operator):
        good_list = []
        bad_list = []
        for el in input_list:
            code = el[0]
            if not self.haaletanud(code):
                bad_list.append(el)
                evlog.log_error('Isik koodiga %s ei ole hääletanud' % code)
                continue

            revoked, reason, _ = self.is_user_revoked(code)
            if (not revoked):
                bad_list.append(el)
                evlog.log_error(\
                    'Isik koodiga %s ei ole oma häält tühistanud' % code)
                continue
            else:
                self.restore_vote(el, operator)
                good_list.append(el)

        return good_list, bad_list


if __name__ == '__main__':
    print "No main"

# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = htsall
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import bdocconfig
import bdocpython
import bdocpythonutils
from election import Election
import base64
import hts
import htsbase
import evstrings
import evcommon
from evmessage import EV_ERRORS
from evmessage import EvMessage
import evlog
import htsstatus
import htscommon
import formatutil
import question
import ksum
import time
import random
import os

def _generate_vote_id():
    return os.urandom(20).encode('hex')

def _delete_vote_id(vote_id):
    return Election().get_root_reg().ensure_no_key(\
            htscommon.get_verification_key(vote_id))

def _revoke_vote_id(voter_code):
    elec = Election()
    otps = set()
    for quest in elec.get_questions():
        reg = elec.get_sub_reg(quest)
        key = htscommon.get_user_key(voter_code)
        if reg.check(key + [htscommon.VOTE_VERIFICATION_ID_FILENAME]):
            otp = reg.read_string_value(key, \
                    htscommon.VOTE_VERIFICATION_ID_FILENAME)
            evlog.log("Found vote ID %s under question %s" % (otp, quest))
            otps.add(otp.value)
            otp.delete()

    if len(otps) > 1:
        evlog.log_error("The voter %s had multiple vote ID-s: %s" % \
                (voter_code, ", ".join(otps)))

    for otp in otps:
        evlog.log("Revoking vote ID %s" % otp)
        if not _delete_vote_id(otp):
            evlog.log_error("No such vote-ID: %s" % otp)

class HTSStoreException(Exception):
    def __init__(self, ret):
        self.ret = ret

class HTSStore:

    def __init__(self):
        self.user_msg = ''
        self.log_msg = ''
        self.signercode = None
        self.ocsp_time = None
        self.signed_vote = None
        self.bdoc = None
        self.questions = []
        self.actions = []

    def __check_incoming_vote(self, config):

        _doc_count = len(self.bdoc.documents)
        if _doc_count == 0:
            raise Exception, "BDoc ei sisalda ühtegi andmefaili"

        sigfiles = self.bdoc.signatures.keys()
        if len(sigfiles) != 1:
            raise Exception, "BDoc sisaldab rohkem kui ühte allkirja"

        verifier = bdocpython.BDocVerifier()
        config.populate(verifier)
        for el in self.bdoc.documents:
            verifier.setDocument(self.bdoc.documents[el], el)

        sig_fn = sigfiles[0]
        sig_content = self.bdoc.signatures[sig_fn]
        res = verifier.verifyInHTS(sig_content)
        if res.signature:
            self.bdoc.addTM(sig_fn, res.signature)
        return res


    def verify_vote(self, votedata):
        import regrights
        self.user_msg = EV_ERRORS.TEHNILINE_VIGA

        conf = bdocconfig.BDocConfig()
        conf.load(Election().get_bdoc_conf())

        self.bdoc = bdocpythonutils.BDocContainer()
        self.bdoc.load_bytes(votedata)
        self.bdoc.validateflex()
        res = self.__check_incoming_vote(conf)

        if not res.result:
            self.log_msg = res.error
            if self.user_msg == '':
                self.user_msg = EV_ERRORS.TEHNILINE_VIGA

            if not res.ocsp_is_good:
                self.user_msg = EV_ERRORS.SERTIFIKAAT_ON_TYHISTATUD_VOI_PEATATUD
                raise HTSStoreException, evcommon.EVOTE_CERT_ERROR

            raise HTSStoreException, evcommon.EVOTE_ERROR

        self.signercode = regrights.get_personal_code(res.subject)

        self.ocsp_time = res.ocsp_time
        self.signed_vote = self.bdoc.get_bytes()

    def extract_questions(self):

        self.log_msg = \
            "Allkirjastatud hääl '%s' ei vasta formaadinõuetele" % \
            self.signercode
        self.user_msg = EV_ERRORS.TEHNILINE_VIGA

        for dfn in self.bdoc.documents:
            quest = dfn.split('.')
            if len(quest) != 2:
                raise HTSStoreException, evcommon.EVOTE_ERROR

            if quest[1] != 'evote':
                raise HTSStoreException, evcommon.EVOTE_ERROR

            if not quest[0] in Election().get_questions():
                raise HTSStoreException, evcommon.EVOTE_ERROR

            vote = self.bdoc.documents[dfn]

            self.questions.append([quest[0], vote])

    def _count_votes(self, elid):
        user_key = htscommon.get_user_key(self.signercode)
        if Election().get_sub_reg(elid).check(user_key):
            keys = Election().get_sub_reg(elid).list_keys(user_key)
            try:
                keys.remove(htscommon.VOTE_VERIFICATION_ID_FILENAME)
            except ValueError:
                pass # No "otp" file
            return len(keys)
        return 0

    def create_actions(self):
        max_votes_per_voter = None
        if Election().get_root_reg().check(['common', 'max_votes_per_voter']):
            max_votes_per_voter = \
                Election().get_root_reg().read_integer_value(\
                    ['common'], 'max_votes_per_voter').value

        for el in self.questions:
            _hts = hts.HTS(el[0])
            voter = _hts.talletaja(self.signercode)
            dsc = ''
            try:
                dsc = Election().get_sub_reg(\
                    el[0]).read_string_value(['common'], 'description').value
            except:
                dsc = el[0]
            if voter == None:
                self.user_msg = EV_ERRORS.POLE_VALIJA
                self.log_msg = "Pole valija %s, %s"  % (self.signercode, dsc)
                raise HTSStoreException, evcommon.EVOTE_ERROR
            if max_votes_per_voter:
                if self._count_votes(el[0]) >= max_votes_per_voter:
                    self.user_msg = EV_ERRORS.TEHNILINE_VIGA

                    self.log_msg = self.user_msg
                    raise HTSStoreException, evcommon.EVOTE_ERROR

            self.actions.append([_hts, voter, el[1]])

    def revoke_vote_id(self):
        _revoke_vote_id(self.signercode)

    def __create_vote_key(self):
        reg = Election().get_root_reg()
        while True:
            vote_id = _generate_vote_id()
            key = htscommon.get_verification_key(vote_id)
            if not reg.check(key):
                reg.create_key(key)
                return vote_id

    def issue_vote_id(self):
        vote_id = self.__create_vote_key()
        rreg = Election().get_root_reg()
        key = htscommon.get_verification_key(vote_id)

        rreg.create_string_value(key, "voter", self.signercode)
        rreg.create_integer_value(key, "timestamp", int(time.time()))
        rreg.create_integer_value(key, "count", \
                Election().get_verification_count())

        # Store the election IDs and include a backreference in the
        # corresponding questions' subregistries.
        elids = ""
        for elid in [quest[0] for quest in self.questions]:
            elids += elid + "\t"

            sreg = Election().get_sub_reg(elid)
            skey = htscommon.get_user_key(self.signercode)
            sreg.ensure_key(skey)
            sreg.create_string_value(skey, \
                    htscommon.VOTE_VERIFICATION_ID_FILENAME, vote_id)

        rreg.create_string_value(key, "elids", elids)
        return vote_id

    def store_votes(self):

        for el in self.actions:
            el[0].talleta_haal(
                signercode=self.signercode,
                signedvote=self.signed_vote,
                vote=el[2],
                timestamp=self.ocsp_time,
                valija=el[1])

            if not el[0].haaletanud(self.signercode):
                self.user_msg = EV_ERRORS.TEHNILINE_VIGA
                self.log_msg = \
                    'Hääle talletamisjärgne kontroll andis '\
                    'vigase tulemuse (%s)' % self.signercode
                raise HTSStoreException, evcommon.EVOTE_ERROR


class HTSVerifyException(Exception):
    def __init__(self, ret):
        self.ret = ret

class HTSVerify:

    def __init__(self):
        self._rreg = Election().get_root_reg()
        self._vote_id = None
        self._voter_code = None

    def __revoke_vote_id(self):
        _revoke_vote_id(self._voter_code)

    def verify_id(self, vote_id):
        # check if valid vote ID
        if not formatutil.is_vote_verification_id(vote_id):
            # We don't know how large vote_id is, so don't write to disk
            evlog.log_error("Malformed vote ID")
            raise HTSVerifyException, evcommon.VERIFY_ERROR

        vote_id = vote_id.lower()
        otp_key = htscommon.get_verification_key(vote_id)

        # check if corresponding OTP exists
        if not self._rreg.check(otp_key):
            evlog.log_error("No such vote ID: %s" % vote_id)
            raise HTSVerifyException, evcommon.VERIFY_ERROR

        self._voter_code = self._rreg.read_string_value(\
                otp_key, "voter").value.rstrip()

        # check if timestamp is OK
        current = int(time.time())
        created = self._rreg.read_integer_value(otp_key, "timestamp").value
        timeout = Election().get_verification_time() * 60
        if created + timeout < current:
            evlog.log("Vote ID %s has expired" % vote_id)
            self.__revoke_vote_id()
            raise HTSVerifyException, evcommon.VERIFY_ERROR

        # check if count is OK
        count = self._rreg.read_integer_value(otp_key, "count").value
        if count <= 0:
            evlog.log_error("Vote ID %s count is zero, but had not been revoked")
            self.__revoke_vote_id()
            raise HTSVerifyException, evcommon.VERIFY_ERROR

        self._vote_id = vote_id

    def __load_bdoc(self, elid):
        voter_key = htscommon.get_user_key(self._voter_code)
        sreg = Election().get_sub_reg(elid)
        vote_files = []
        for vfile in sreg.list_keys(voter_key):
            if htscommon.VALID_VOTE_PATTERN.match(vfile):
                vote_files.append(vfile)

        vote_files.sort()
        latest = vote_files.pop()
        if latest:
            bdoc = htsbase.get_vote(sreg.path(voter_key + [latest]))

        if not bdoc:
            evlog.log_error("No valid BDOC found for voter %s using vote ID %s" % \
                    (self._voter_code, self._vote_id))
            raise HTSVerifyException, evcommon.VERIFY_ERROR

        return bdoc

    def __decrease_count(self):
        otp_key = htscommon.get_verification_key(self._vote_id)
        count = self._rreg.read_integer_value(otp_key, "count").value - 1
        if count > 0:
            self._rreg.create_integer_value(otp_key, "count", count)
        else:
            self.__revoke_vote_id()

    def get_response(self):
        import binascii

        # load a random BDOC from the ones available
        otp_key = htscommon.get_verification_key(self._vote_id)
        elids = self._rreg.read_string_value(otp_key, "elids")\
                .value.rstrip().split("\t")
        bdoc = self.__load_bdoc(random.choice(elids))
        evlog.log("Sending BDOC %s with vote ID %s for verification" %\
                (ksum.votehash(bdoc.get_bytes()), self._vote_id))

        # check consistency
        bdoc_set = set([doc.split(".")[0] for doc in bdoc.documents])
        elids_set = set(elids)
        if bdoc_set != elids_set:
            evlog.log_error("Votes in BDOC for vote ID %s are inconsistent " \
                    "with registry: %s, %s" % (self._vote_id, bdoc_set, elids_set))
            raise HTSVerifyException, evcommon.VERIFY_ERROR

        # create question objects
        questions = []
        for elid in elids:
            questions.append(question.Question(\
                    elid, "hts", Election().get_sub_reg(elid)))

        # start assembling the response
        ret = ""

        # append questions
        for quest in questions:
            ret += quest.qname() + ":" + str(quest.get_type()) + "\t"
        ret += "\n"

        # append election IDs and votes
        for votefile in bdoc.documents:
            elid = votefile.split(".")[0]
            ret += elid + "\t" + binascii.b2a_hex(bdoc.documents[votefile]) + "\n"
        ret += "\n"

        # append choices list
        for quest in questions:
            tv = quest.get_voter(self._voter_code)
            if tv:
                ret += quest.choices_to_voter(tv)
            else:
                evlog.log_error("Voter not found")

        self.__decrease_count()
        return ret

class HTSAll:

    def __init__(self):
        bdocpython.initialize()

    def __del__(self):
        bdocpython.terminate()

    def status(self, fo, verify):
        fo.write('HTS vaheauditi aruanne\n\n')
        if (not verify):
            fo.write('NB! Hääli ei verifitseeritud\n\n')
        fo.write('Käimasolevad hääletused:\n')
        for el in Election().get_questions():
            fo.write('\t%s\n' % el)

        fo.write('\nAnalüüs hääletuste kaupa:\n\n')
        for el in Election().get_questions():
            _h = htsstatus.HTSStatus(el)
            if verify:
                _h.status_verify()
            else:
                _h.status_noverify()
            _h.output(fo)
            fo.write('\n')

    def kooskolaline(self, voters_files_sha256):
        if Election().get_root_reg().check(['common', 'voters_files_sha256']):
            hts_voters_files_sha256 = \
                Election().get_root_reg().read_string_value(
                    ['common'], 'voters_files_sha256').value
        else:
            hts_voters_files_sha256 = ''
        if hts_voters_files_sha256 != voters_files_sha256:
            return False
        return True

    def haaletanud(self, ik):
        votes = []
        lst = Election().get_questions()
        for el in lst:
            _h = htsbase.HTSBase(el)
            if _h.haaletanud(ik):
                votes.append(\
                    Election().get_sub_reg(el).\
                        read_string_value(['common'], 'electionid').value)

        if len(votes) > 0:
            ret = ''
            for el in votes:
                ret += el
                ret += '\n'
            return True, ret.rstrip()

        return False, \
            'Isikukoodi %s kohta ei ole talletatud ühtegi häält' % ik

    def __haaletanud(self, ik):
        lst = Election().get_questions()
        for el in lst:
            _h = htsbase.HTSBase(el)
            if _h.haaletanud(ik):
                return True
        return False

    def __questions_with_valid_vote(self, ik):
        questions = []
        lst = Election().get_questions()
        for el in lst:
            _h = htsbase.HTSBase(el)
            if _h.haaletanud(ik):
                questions.append(el)
        return questions

    def __talleta(self, binvote):

        store = HTSStore()
        new_otp = False
        try:
            store.verify_vote(binvote)
            evlog.log('Hääle allkirjastaja: %s' % store.signercode)
            store.extract_questions()
            store.create_actions()
            store.revoke_vote_id()
            vote_id = store.issue_vote_id()
            new_otp = True
            store.store_votes()
        except HTSStoreException as e:
            evlog.log_error(store.log_msg)
            if new_otp:
                store.revoke_vote_id()
            return e.ret, store.user_msg

        evlog.log("Issued vote ID %s to %s for BDOC %s" % \
                (vote_id, store.signercode, ksum.votehash(store.signed_vote)))
        return evcommon.EVOTE_OK, vote_id

    def talleta_base64(self, data):

        try:
            decoded_vote = base64.decodestring(data)
            return self.__talleta(decoded_vote)
        except:
            evlog.log_exception()
            return evcommon.EVOTE_ERROR, EV_ERRORS.TEHNILINE_VIGA

    def verify(self, vote_id):
        verifier = HTSVerify()
        try:
            verifier.verify_id(vote_id)
        except HTSVerifyException as e:
            return e.ret, EvMessage().get_str(\
                    "INVALID_VOTE_ID", evstrings.INVALID_VOTE_ID)

        evlog.log("Verifying vote with ID %s" % vote_id)
        try:
            return evcommon.VERIFY_OK, verifier.get_response()
        except HTSVerifyException as e:
            return e.ret, EvMessage().get_str(\
                    "TECHNICAL_ERROR_VOTE_VERIFICATION", \
                    evstrings.TECHNICAL_ERROR_VOTE_VERIFICATION)


if __name__ == '__main__':

    print 'No main'

# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = htsalldisp
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import htsall
from election import ElectionState
from evlog import AppLog
import evreg
import sys
import evcommon
import evstrings
from evmessage import EvMessage
from evmessage import EV_ERRORS
import time


def __return_message(result, message):
    return evcommon.VERSION + '\n' + result + '\n' + message

def bad_cgi_input():
    ret = evcommon.EVOTE_ERROR
    msg = EV_ERRORS.TEHNILINE_VIGA
    AppLog().set_app('HTS-ALL')
    AppLog().log_error("Vigased sisendparameetrid")
    return __return_message(ret, msg)


def consistency(sha_in):
    _htsd = HTSAllDispatcher()
    ret = _htsd.kooskolaline(sha_in)
    return __return_message(ret, '')


def check_repeat(sha_in, code_in):
    _htsd = HTSAllDispatcher()
    ret = evcommon.EVOTE_REPEAT_ERROR
    msg = EV_ERRORS.TEHNILINE_VIGA

    AppLog().set_person(code_in)
    ret_cons = _htsd.kooskolaline(sha_in)

    if ret_cons == evcommon.EVOTE_CONSISTENCY_NO:
        ret = evcommon.EVOTE_REPEAT_NOT_CONSISTENT
        msg = EV_ERRORS.HOOLDUS
    elif ret_cons == evcommon.EVOTE_CONSISTENCY_YES:
        ok, ret_rep, msg_rep = _htsd.haaletanud(code_in)
        if ok:
            if ret_rep:
                ret = evcommon.EVOTE_REPEAT_YES
            else:
                ret = evcommon.EVOTE_REPEAT_NO
        msg = msg_rep

    return __return_message(ret, msg)


def store_vote(sha_in, code_in, vote_in):

    _htsd = HTSAllDispatcher()
    ret = evcommon.EVOTE_ERROR
    msg = EV_ERRORS.TEHNILINE_VIGA

    ret_cons = _htsd.kooskolaline(sha_in)
    if ret_cons == evcommon.EVOTE_CONSISTENCY_NO:
        ret = evcommon.EVOTE_ERROR
        msg = EV_ERRORS.HOOLDUS
    elif ret_cons == evcommon.EVOTE_CONSISTENCY_YES:
        AppLog().set_person(code_in)
        ret, msg = _htsd.talleta_base64(vote_in)
    else:
        ret = evcommon.EVOTE_ERROR
        msg = EV_ERRORS.TEHNILINE_VIGA
    return __return_message(ret, msg)

def verify_vote(vote_id):
    _htsd = HTSAllDispatcher()
    ret, msg = _htsd.verify(vote_id)
    return __return_message(ret, msg)

class HTSAllDispatcher:

    def __init__(self):
        AppLog().set_app('HTS-ALL')
        self.__all = htsall.HTSAll()

    def kooskolaline(self, voters_files_sha256):
        try:
            try:
                #AppLog().log('HES ja HTS kooskõlalisuse kontroll: ALGUS')
                if self.__all.kooskolaline(voters_files_sha256):
                    return evcommon.EVOTE_CONSISTENCY_YES
                else:
                    AppLog().log_error('HES ja HTS ei ole kooskõlalised')
                    return evcommon.EVOTE_CONSISTENCY_NO
            except:
                AppLog().log_exception()
                return evcommon.EVOTE_CONSISTENCY_ERROR
        finally:
            pass
            #AppLog().log('HES ja HTS kooskõlalisuse kontroll: LõPP')

    def haaletanud(self, ik):
        try:
            try:
                AppLog().log('Korduvhääletuse kontroll: ALGUS')
                if ElectionState().election_on():
                    ok, msg = self.__all.haaletanud(ik)
                    return True, ok, msg

                r1, msg = ElectionState().election_off_msg()
                AppLog().log_error(msg)
                return False, False, msg
            except:
                AppLog().log_exception()
                return False, False, EV_ERRORS.TEHNILINE_VIGA
        finally:
            AppLog().log('Korduvhääletuse kontroll: LõPP')

    def talleta_base64(self, data):
        try:
            try:
                AppLog().log('Hääle talletamine: ALGUS')
                if ElectionState().election_on():
                    return self.__all.talleta_base64(data)

                r1, msg = ElectionState().election_off_msg()
                AppLog().log_error(msg)
                return evcommon.EVOTE_ERROR, msg
            except:
                AppLog().log_exception()
                return evcommon.EVOTE_ERROR, EV_ERRORS.TEHNILINE_VIGA
        finally:
            AppLog().log('Hääle talletamine: LõPP')

    def status(self, fo, verify=True):
        p_time = "00:00:00"

        try:
            try:
                s_time = time.time()
                AppLog().log('Vaheauditi aruanne: ALGUS')
                self.__all.status(fo, verify)
                p_time = time.strftime("%H:%M:%S", \
                        time.gmtime(long(time.time() - s_time)))

                return 'Vaheauditi aruanne koostatud. Aega kulus %s.' % p_time
            except:
                AppLog().log_exception()
                return 'Tehniline viga vaheauditi aruande koostamisel'
        finally:
            AppLog().log('Vaheauditi aruanne (%s): LõPP' % p_time)


    def verify(self, vote_id):
        try:
            AppLog().log("Vote verification: START")
            if ElectionState().election_on():
                return self.__all.verify(vote_id)

            ret, msg = ElectionState().election_off_msg()
            AppLog().log_error(msg)
            return evcommon.VERIFY_ERROR, msg
        except:
            AppLog().log_exception()
            return evcommon.VERIFY_ERROR, EvMessage().get_str(\
                    "TECHNICAL_ERROR_VOTE_VERIFICATION", \
                    evstrings.TECHNICAL_ERROR_VOTE_VERIFICATION)
        finally:
            AppLog().log("Vote verification: END")


def talleta(base64_fail, htsd):
    try:
        _if = file(base64_fail, "rb")
        data = _if.read()
        return htsd.talleta_base64(data)
    finally:
        _if.close()


def usage():
    print "Kasutamine:"
    print "    %s haaletanud <isikukood>" % sys.argv[0]
    print \
        "        - kontrollib isikukoodi järgi, kas isik on juba hääletanud"
    print "    %s talleta <failinimi>" % sys.argv[0]
    print "        - talletab ddoc e-haale"
    print "    %s status" % sys.argv[0]
    print "        - kuvab infot e-hääletuste staatuse kohta"

    sys.exit(1)


def main_function():
    if len(sys.argv) < 2:
        usage()

    if not sys.argv[1] in \
        ['haaletanud', 'talleta', 'status', 'statusnoverify']:
        usage()

    if sys.argv[1] in ['haaletanud', 'talleta'] and len(sys.argv) < 3:
        usage()

    htsd = None

    try:
        htsd = HTSAllDispatcher()

        if sys.argv[1] == 'haaletanud':
            res, _ok, _msg = htsd.haaletanud(sys.argv[2])
            if not res:
                print 'Viga korduvhääletuse kontrollimisel'
            print _msg
            if _ok:
                sys.exit(0)
            sys.exit(1)
        elif sys.argv[1] == 'talleta':
            res, _msg = talleta(sys.argv[2], htsd)
            print _msg
            if res:
                sys.exit(0)
            sys.exit(1)
        elif sys.argv[1] == 'status':
            reg = evreg.Registry(root=evcommon.EVREG_CONFIG)
            status_file = reg.path(['common', evcommon.STATUSREPORT_FILE])
            _ff = file(status_file, 'w')
            try:
                res = htsd.status(_ff)
                _ff.write(res + "\n")
            finally:
                _ff.close()
        elif sys.argv[1] == 'statusnoverify':
            reg = evreg.Registry(root=evcommon.EVREG_CONFIG)
            status_file = reg.path(['common', evcommon.STATUSREPORT_FILE])
            _ff = file(status_file, 'w')
            try:
                res = htsd.status(_ff, False)
                _ff.write(res + "\n")
            finally:
                _ff.close()
        else:
            usage()

    except SystemExit:
        raise
    except Exception, _e:
        print _e
        sys.exit(1)
    except:
        sys.exit(1)

    finally:
        pass

    sys.exit(0)


if __name__ == '__main__':
    main_function()

# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = htsbase
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import evlog
import htscommon
import evcommon
from election import Election
import os
import inputlists
import bdocpythonutils
import zipfile
import time


def get_vote(zipfn):
    bdoc = None
    inzip = None
    try:
        try:
            inzip = zipfile.ZipFile(zipfn, 'r')
            bdocdata = inzip.read(htscommon.ZIP_BDOCFILE)
            bdoc = bdocpythonutils.BDocContainer()
            bdoc.load_bytes(bdocdata)
            profile = bdocpythonutils.ManifestProfile('TM')
            bdoc.validate(profile)
        except:
            bdoc = None
            evlog.log_exception()
    finally:
        if inzip:
            inzip.close()

    return bdoc


class HTSBase:

    def __init__(self, elid):
        self._elid = elid
        self._errmsg = None
        self._reg = Election().get_sub_reg(self._elid)

        self._revlog = evlog.Logger()
        self._revlog.set_format(evlog.RevLogFormat())
        self._revlog.set_logs(self._reg.path(['common', evcommon.REVLOG_FILE]))


    def haaletanud(self, isikukood):
        latest = self.get_latest_vote(isikukood)
        return latest <> None


    def get_revoked_path(self, pc):
        user_key = htscommon.get_user_key(pc)
        return self._reg.path(user_key + ['reason'])


    def get_latest_vote(self, pc):
        user_key = htscommon.get_user_key(pc)
        if self._reg.check(user_key):
            files = self._reg.list_keys(user_key)
            votes = []
            for el in files:
                if htscommon.VALID_VOTE_PATTERN.match(el):
                    votes.append(el)
            votes.sort()
            latest = votes.pop()
            if latest:
                return htscommon.get_votefile_time(latest)

        return None


    def restore_vote(self, revline, operator):
        timest = self.get_latest_vote(revline[0])
        os.unlink(self.get_revoked_path(revline[0]))
        self._revlog.log_info(
            tegevus='ennistamine',
            isikukood=revline[0],
            nimi=revline[1],
            timestamp=timest,
            operaator=operator,
            pohjus=revline[2])


    def revoke_vote(self, revline, operator):
        timest = self.get_latest_vote(revline[0])
        nowstr = time.strftime("%Y%m%d%H%M%S", time.localtime())
        self._reg.create_string_value(\
            htscommon.get_user_key(revline[0]), 'reason', \
            "%s\t%s" % (nowstr, revline[2]))

        self._revlog.log_info(
            tegevus='tühistamine',
            testtime=nowstr,
            isikukood=revline[0],
            nimi=revline[1],
            timestamp=timest,
            operaator=operator,
            pohjus=revline[2])


    def is_user_revoked(self, pc):
        user_key = htscommon.get_user_key(pc)
        if self._reg.check(user_key + ['reason']):
            line = self._reg.read_string_value(user_key, 'reason').value
            data = line.split('\t')
            return True, data[1], data[0]
        return False, '', ''


    def save_log(self, lines, log):
        fn = self._reg.path(['common', 'log%s' % log])
        lf = htscommon.LoggedFile(fn)
        lf.open('w')
        lf.write(evcommon.VERSION + "\n")
        lf.write(self._elid + "\n")
        lf.write("%s\n" % log)
        for el in lines:
            lf.write(el + '\n')
        lf.close()


    def save_revocation_report(self, report):
        fn = self._reg.path(['hts', 'output', evcommon.REVREPORT_FILE])
        outfile = htscommon.LoggedFile(fn)
        outfile.open('a')
        for el in report:
            outfile.write("\t".join(el) + "\n")

        outfile.close()


    def talletaja(self, ik):
        vl = None
        try:
            vl = inputlists.VotersList('hts', self._reg)
            if not vl.has_voter(ik):
                return None
            ret = vl.get_voter(ik)
            return ret
        finally:
            if vl != None:
                vl.close()
                vl = None



if __name__ == '__main__':
    print "No main"

# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = htscommon
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import fcntl
import re
import os

REVOKE_REASON_PATTERN = re.compile('^reason$')
VALID_VOTE_PATTERN = re.compile('^vote_.*_.*_.zip$', re.DOTALL)
PARTIAL_VOTE_PATTERN = re.compile('^vote_.*_.*_.zip.partial$', re.DOTALL)
VOTE_VERIFICATION_ID_FILENAME = "otp"

ZIP_BDOCFILE = "vote.bdoc"
ZIP_LOGFILE = "vote.log"

def get_verification_key(otp=None):
    key = ['verification', 'otps']
    if otp:
        key.append(otp)
    return key

def get_user_key(code):
    return ['hts', 'votes', code[7:11], code]

def get_votefile_time(filename):
    llist = filename.split('_')
    return llist[1]


def valid_votefile_name(timestamp):
    rnd = os.urandom(3).encode('hex')
    return '_'.join(['vote', timestamp, rnd,'.zip'])


def get_logline_voter(logline):
    voter = logline.split('\t')
    ret = {
        'timestamp': voter[0],
        'isikukood': voter[6],
        'nimi': '',
        'jaoskond_omavalitsus': voter[4],
        'jaoskond': voter[5],
        'ringkond_omavalitsus': voter[2],
        'ringkond': voter[3],
        'reanumber': ''}

    if len(voter) == 9:
        ret['nimi'] = voter[7]
        ret['reanumber'] = voter[8].rstrip()

    return ret


class LoggedFile:

    def __init__(self, filen):
        self.__filename = filen
        self.__file = None

    def name(self):
        return self.__filename

    def open(self, mode):
        self.__file = file(self.__filename, mode)
        fcntl.lockf(self.__file, fcntl.LOCK_EX)

    def write(self, writestr):
        self.__file.write(writestr)

    def close(self):
        self.__file.close()


if __name__ == '__main__':
    print "No main"

# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = htsdisp
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

from evlog import AppLog
import hts
import time

def start_revocation(elid):
    AppLog().set_app('HTS', elid)
    p_time = "00:00:00"

    try:
        try:
            s_time = time.time()
            AppLog().log('Üleminek tühistusperioodi: ALGUS')
            _hts = hts.HTS(elid)
            all_, rev, res = _hts.tyhistusperioodi()
            p_time = time.strftime("%H:%M:%S", \
                    time.gmtime(long(time.time() - s_time)))

            print '\tVastuvõetud häälte koguarv: %d' % all_
            print '\tTühistatud korduvate häälte arv: %d' % rev
            print '\tHääletanute nimekirja kantud kirjete arv: %d' % res
            print '\nAega kulus: %s' % p_time

        except:
            print 'Üleminek tühistusperioodi ebaõnnestus'
            AppLog().log_exception()
    finally:
        AppLog().log('Üleminek tühistusperioodi (%s): LÕPP' % p_time)


def start_tabulation(elid):
    AppLog().set_app('HTS', elid)
    p_time = "00:00:00"

    try:
        try:
            s_time = time.time()
            AppLog().log('Loendamisele minevate ' \
                    'häälte nimekirja koostamine: ALGUS')
            _hts = hts.HTS(elid)
            g_v, r_v, a_v, b_v = _hts.lugemisperioodi()
            p_time = time.strftime("%H:%M:%S", \
                    time.gmtime(long(time.time() - s_time)))
            print '\tLoendamisele minevate häälte arv: %d' % g_v
            print '\tAvalduse alusel tühistatud häälte arv: %d' % r_v
            print '\tKorduvate häälte arv: %d' % a_v
            if (b_v > 0):
                print '\tProbleemsete häälte arv: %d' % b_v
            print '\nAega kulus: %s' % p_time
        except:
            print 'Loendamisele minevate häälte nimekirja ' \
                'koostamine ebaõnnestus'
            AppLog().log_exception()
    finally:
        AppLog().log('Loendamisele minevate häälte nimekirja ' \
            'koostamine (%s): LÕPP' % p_time)


if __name__ == '__main__':
    pass

# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = htsstatus
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

from election import Election
import regrights
import ticker
import os
import htscommon
import htsbase
import formatutil
import zipfile

class StatusCounter:

    def __init__(self):
        self.c_ok = 0
        self.c_bad = 0
        self.c_msg = []

    def ok_c(self):
        return self.c_ok

    def bad_c(self):
        return self.c_bad

    def inc(self, cnt=1, msg=None, res=True):
        if (msg != None):
            self.c_msg.append(msg)
        if res:
            self.c_ok += cnt
        else:
            self.c_bad += cnt

    def print_msg(self, fo):
        for el in self.c_msg:
            fo.write('\t%s\n' % el)


class HTSStatusInfo:

    def __init__(self):
        self.v_votes = StatusCounter()
        self.a_votes = StatusCounter()
        self.r_votes = StatusCounter()
        self.n_votes = StatusCounter()

    def ok_count(self):
        return self.v_votes.ok_c() + self.a_votes.ok_c() + self.r_votes.ok_c()

    def bad_count(self):
        return \
            self.v_votes.bad_c() + self.a_votes.bad_c() + self.r_votes.bad_c()

    def valid_vote(self, cnt, msg, res):
        self.v_votes.inc(cnt, msg, res)

    def userrevoked_vote(self, cnt, msg, res):
        self.r_votes.inc(cnt, msg, res)

    def autorevoked_vote(self, cnt, msg, res):
        self.a_votes.inc(cnt, msg, res)

    def unknown_file(self, cnt, msg):
        self.n_votes.inc(cnt, msg)

    def status_output(self, fo):

        fo.write('\nTalletatud hääli %d:\n' % \
            (self.v_votes.ok_c() + self.v_votes.bad_c()))
        self.v_votes.print_msg(fo)
        fo.write('\tKorras hääli (%d), vigaseid hääli (%d)\n' % \
            (self.v_votes.ok_c(), self.v_votes.bad_c()))

        fo.write('\nAvalduse alusel tühistatud hääli %d:\n' % \
            (self.r_votes.ok_c() + self.r_votes.bad_c()))
        self.r_votes.print_msg(fo)
        fo.write('\tKorras hääli (%d), vigaseid hääli (%d)\n' % \
            (self.r_votes.ok_c(), self.r_votes.bad_c()))

        fo.write('\nTühistatud korduvaid hääli %d:\n' % \
            (self.a_votes.ok_c() + self.a_votes.bad_c()))
        self.a_votes.print_msg(fo)
        fo.write('\tKorras hääli (%d), vigaseid hääli (%d)\n' % \
            (self.a_votes.ok_c(), self.a_votes.bad_c()))

        if self.n_votes.ok_c() > 0:
            fo.write('\nVigu olekupuus %d:\n' % self.n_votes.ok_c())
            self.n_votes.print_msg(fo)


class HTSStatus(htsbase.HTSBase):

    def __init__(self, elid):
        htsbase.HTSBase.__init__(self, elid)
        self.__sti = HTSStatusInfo()

    def output(self, outstream):
        outstream.write('Hääletuse \"%s\" olekuanalüüs\n' % self._elid)
        self.__sti.status_output(outstream)

    def do_verify(self, root, vote_file, conf, code):
        res = False
        msg = 'VIGA:\t%s\tTundmatu viga' % code
        inzip = None
        try:
            try:

                lname = root + '/' + vote_file
                inzip = zipfile.ZipFile(lname, 'r')
                bdocdata = inzip.read(htscommon.ZIP_BDOCFILE)

                ver = regrights.analyze_vote(bdocdata, conf)
                if ver.result:
                    res = True
                    msg = 'OK:\t%s\t%s' % (code, ver.ocsp_time)
                else:
                    res = False
                    msg = 'VIGA:\t%s\t%s' % (code, ver.error)
            except Exception, e:
                res = False
                msg = 'Viga:\t%s\t%s' % (code, e)
            except:
                pass
        finally:
            if inzip:
                inzip.close()

        return res, msg


    def status_noverify(self):
        for path in os.walk(self._reg.path(['hts', 'votes'])):
            root = path[0]
            code = root.split('/').pop()

            if not formatutil.is_isikukood(code):
                continue

            user_revoked = False
            vc = 0
            for vote_file in path[2]:
                if htscommon.REVOKE_REASON_PATTERN.match(vote_file):
                    user_revoked = True
                if htscommon.VALID_VOTE_PATTERN.match(vote_file):
                    vc += 1

            if vc > 0:
                if not user_revoked:
                    self.__sti.valid_vote(1, None, True)
                else:
                    self.__sti.userrevoked_vote(1, None, True)
                self.__sti.autorevoked_vote(vc - 1, None, True)


    def status_verify(self):
        import bdocconfig

        tic = ticker.Counter('Hääli:', '\tKorras: %d\tVigaseid: %d')
        tic.start('Hääletuse \"%s\" olekuanalüüs' % self._elid)
        conf = bdocconfig.BDocConfig()
        conf.load(Election().get_bdoc_conf())

        for path in os.walk(self._reg.path(['hts', 'votes'])):
            root = path[0]
            code = root.split('/').pop()

            if not formatutil.is_isikukood(code):
                continue

            user_revoked = False

            valid_files = []
            for vote_file in path[2]:
                if htscommon.REVOKE_REASON_PATTERN.match(vote_file):
                    user_revoked = True
                    continue
                if htscommon.VOTE_VERIFICATION_ID_FILENAME == vote_file:
                    continue
                if htscommon.PARTIAL_VOTE_PATTERN.match(vote_file):
                    continue
                if not htscommon.VALID_VOTE_PATTERN.match(vote_file):
                    self.__sti.unknown_file(1, '\tTundmatu fail: ' + code + '/' + vote_file)
                    continue
                valid_files.append(vote_file)

            if len(valid_files) > 0:
                valid_files.sort()
                latest = valid_files.pop()
                res, msg = self.do_verify(root, latest, conf, code)
                if not user_revoked:
                    self.__sti.valid_vote(1, msg, res)
                else:
                    self.__sti.userrevoked_vote(1, msg, res)
                self.__sti.autorevoked_vote(len(valid_files), None, True)
            else:
                self.__sti.unknown_file(1, '\tHäälteta kaust: ' + code)

            tic.tick(1, self.__sti.ok_count(), self.__sti.bad_count())

        tic.finish()


if __name__ == '__main__':
    print "No main"

# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = load_rev_files
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import evlog
import sys
import time
import regrights
import os
import revocationlists
import hts
import election
import bdocconfig
import bdocpython
import bdocpythonutils


def restore_revoke(elid, rfile, operator):

    the_hts = hts.HTS(elid)
    rl = revocationlists.RevocationList()
    rl.attach_elid(elid)
    rl.attach_logger(evlog.AppLog())
    if not rl.check_format(rfile, 'Kontrollin tühistus-/ennistusnimekirja: '):
        errmsg = 'Vigase formaadiga tühistus-/ennistusnimekiri'
        raise Exception(errmsg)

    g_l = None
    b_l = None
    act = ''

    report = []

    newtime = time.localtime()
    if rl.revoke:
        act = 'tühistamine'
        evlog.log('Tühistusavalduse import')
        g_l, b_l = the_hts.load_revoke(rl.rev_list, operator)

        report.append(['------------------------------'])
        report.append(['TÜHISTAMINE (%s)' % \
                time.strftime("%Y%m%d%H%M%S", newtime)])
        report.append(['%d õnnestumist, %d ebaõnnestumist' % \
                (len(g_l), len(b_l))])
        report.append(['Operaator %s, fail %s ' % (operator, rfile)])

    else:
        act = 'ennistamine'
        evlog.log('Ennistusavalduse import')
        g_l, b_l = the_hts.load_restore(rl.rev_list, operator)

        report.append(['------------------------------'])
        report.append(['ENNISTAMINE (%s)' % \
                time.strftime("%Y%m%d%H%M%S", newtime)])
        report.append(['%d õnnestumist, %d ebaõnnestumist' % \
                (len(g_l), len(b_l))])
        report.append(['Operaator %s, fail %s ' % (operator, rfile)])


    for el in b_l:
        el.append(act + ' nurjus')
        report.append(el)

    for el in g_l:
        el.append(act + ' õnnestus')
        report.append(el)

    report.append(['------------------------------'])

    the_hts.save_revocation_report(report)
    return len(rl.rev_list), len(g_l), len(b_l)


def usage():
    print "Kasutamine:"
    print "    %s <valimiste-id> <failinimi>" % sys.argv[0]
    print "        - rakendab tühistus-/ennistusnimekirja"

    sys.exit(1)


if __name__ == '__main__':

    if len(sys.argv) < 3:
        usage()

    elid = sys.argv[1]
    infile = sys.argv[2]

    p_time = "00:00:00"
    evlog.AppLog().set_app('HTS', elid)

    tmp_f = None
    try:
        try:
            s_time = time.time()
            evlog.AppLog().log(\
                'Tühistus-/ennistusnimekirja laadimine: ALGUS')

            bdocpython.initialize()
            bconf = bdocconfig.BDocConfig()
            bconf.load(election.Election().get_bdoc_conf())
            result = regrights.kontrolli_volitusi(elid, infile, 'TYHIS', bconf)
            if not result[0]:
                errmsg = 'Tühistus-/ennistusnimekirja volituste ' \
                               'kontroll andis negatiivse tulemuse: '
                errmsg += result[1]
                raise Exception(errmsg)
            _signercode = result[2]

            tmp_f = bdocpythonutils.get_doc_content_file(infile)

            all_, res_a, res_u = restore_revoke(elid, tmp_f, _signercode)
            p_time = time.strftime("%H:%M:%S", \
                    time.gmtime(long(time.time() - s_time)))

            print 'Tühistamine/ennistamine'
            print '\tKirjeid kokku: %d' % all_
            print '\tEdukalt töödeldud kirjeid: %d' % res_a
            print '\tProbleemseid kirjeid: %d' % res_u
            print '\nAega kulus: %s' % p_time

        except:
            print 'Tühistus-/ennistusnimekirja laadimine ebaõnnestus'
            evlog.AppLog().log_exception()
            sys.exit(1)
    finally:
        if tmp_f != None:
            os.unlink(tmp_f)
        evlog.AppLog().log(\
            'Tühistus-/ennistusnimekirja laadimine (%s): LÕPP' % p_time)

    sys.exit(0)

# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = ocsp_checker
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import sys
import subprocess
from election import Election
import time
import bdocconfig
import evlog
import evcommon
import exception_msg

def check_ocsp():

    log = evlog.Logger()
    log.set_format(evlog.AppLogFormat('OCSPWD'))
    log.set_logs(Election().get_path(evcommon.OCSP_LOG_FILE))

    try:
        _conf = bdocconfig.BDocConfig()
        _conf.load(Election().get_bdoc_conf())
        _ocsp = _conf.get_ocsp_responders()

        for el in _ocsp:
            app = 'openssl ocsp -issuer "%s" -serial 123 -url "%s" -noverify' % \
                                                                (_ocsp[el], el)

            pp = subprocess.Popen(app, shell=True, stdin=subprocess.PIPE, \
                                        stdout=subprocess.PIPE, close_fds=True)
            is_ok = 0
            start = time.time()
            while 1:
                line = pp.stdout.readline()
                if line == '':
                    break
                if line.strip().find('This Update:') != -1:
                    is_ok = 1
            end = time.time()
            if is_ok:
                log.log_info(message='OCSP vastas %5.2f sekundiga' % (end - start))
            else:
                log.log_info(message='OCSP ei vasta')
    except:
        log.log_err(message=exception_msg.trace())


if __name__ == '__main__':
    try:
        check_ocsp()
    except:
        pass
    sys.exit(0)

# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = purge_otps
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import time
import election
from evlog import AppLog
import htscommon

def purge_otp(otp_key):
    elec = election.Election()
    reg = elec.get_root_reg()

    voter = reg.read_string_value(otp_key, "voter").value.rstrip()
    voter_key = htscommon.get_user_key(voter)
    elids = reg.read_string_value(otp_key, "elids").value.rstrip().split("\t")

    for elid in elids:
        sreg = elec.get_sub_reg(elid)
        if sreg.check(voter_key + [htscommon.VOTE_VERIFICATION_ID_FILENAME]):
            sreg.delete_value(voter_key, htscommon.VOTE_VERIFICATION_ID_FILENAME)
    reg.ensure_no_key(otp_key)

def purge_otps():
    runtime = int(time.time())
    AppLog().set_app("purgeotps.py")
    AppLog().log("Purging expired vote ID's as of %s: START" % \
            time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(runtime)))
    try:
        reg = election.Election().get_root_reg()
        timeout = election.Election().get_verification_time() * 60
        for otp in reg.list_keys(htscommon.get_verification_key()):
            otp_key = htscommon.get_verification_key(otp)
            created = reg.read_integer_value(otp_key, "timestamp").value
            if created + timeout < runtime:
                AppLog().log("Purging expired vote ID %s" % otp)
                purge_otp(otp_key)
    except:
        AppLog().log_exception()
    finally:
        AppLog().log("Purging expired vote ID's: DONE")


if __name__ == '__main__':
    if election.ElectionState().election_on():
        purge_otps()

# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = bdocconfig
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2013 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import os
import os.path
import xml.etree.ElementTree
import shutil

CONF_KNOWN_PARAMS = [ \
    'digest.uri']

CONF_NECESSARY_ELEMS = [ \
    'bdoc.conf',
    'ca',
    'ocsp',
    'schema',
    'schema/datatypes.dtd',
    'schema/XAdES.xsd',
    'schema/xmldsig-core-schema.xsd',
    'schema/XMLSchema.dtd']

class BDocConfig:

    def __init__(self):
        self.__root = None
        self.__ocsp = {}
        self.__param = {}

    def __del__(self):
        pass

    def _handle_ocsp(self, elems):
        for _el in elems:
            if len(_el) != 4:
                raise Exception, 'Invalid OCSP configuration'

            if (_el[0].tag != 'url') or (_el[1].tag != 'cert'):
                raise Exception, 'Invalid OCSP configuration - tag'

            if (_el[2].tag != 'skew') or (_el[3].tag != 'maxAge'):
                raise Exception, 'Invalid OCSP configuration - tag'

            if (not 'issuer' in _el.attrib) or (len(_el.attrib) != 1):
                raise Exception, 'Invalid OCSP configuration - issuer'

            _certf = os.path.join(self.__root, 'ocsp', _el[1].text)

            if not os.access(_certf, os.F_OK):
                raise Exception, 'Invalid OCSP configuration - cert %s' % _certf

            if not os.access(_certf, os.R_OK):
                raise Exception, 'Invalid OCSP configuration - cert'

            self.__ocsp[_el.attrib['issuer']] = {'url': _el[0].text, \
                                                'cert': _el[1].text, \
                                                'skew': long(_el[2].text), \
                                                'maxAge': long(_el[3].text)}

    def _handle_param(self, elems):
        for _el in elems:
            if (not 'name' in _el.attrib) or (len(_el.attrib) != 1):
                raise Exception, 'Invalid parameter configuration'

            if not _el.attrib['name'] in CONF_KNOWN_PARAMS:
                raise Exception, 'Invalid parameter configuration'

            self.__param[_el.attrib['name']] = _el.text


    def save(self, dirname):
        import stat
        if os.path.exists(dirname):
            shutil.rmtree(dirname)
        shutil.copytree(self.__root, dirname)
        fmode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP
        dmode = stat.S_IRWXU | stat.S_IRWXG
        os.chmod(dirname, dmode)
        for root, dirs, files in os.walk(dirname):
            for name in files:
                os.chmod(os.path.join(root, name), fmode)
            for name in dirs:
                os.chmod(os.path.join(root, name), dmode)


    def load(self, dirname):
        self.__root = dirname

        for _el in CONF_NECESSARY_ELEMS:
            _path = os.path.join(self.__root, _el)
            if not os.access(_path, os.F_OK):
                raise Exception, "Missing conf item \"%s\"" % _el

            if not os.access(_path, os.R_OK):
                raise Exception, "Missing conf item \"%s\"" % _el

        _tree = xml.etree.ElementTree.ElementTree()
        _tree.parse(os.path.join(self.__root, 'bdoc.conf'))

        _ocsp_elems = _tree.getiterator('ocsp')
        self._handle_ocsp(_ocsp_elems)

        _param_elems = _tree.getiterator('param')
        self._handle_param(_param_elems)


    def _ocsp_cert_path(self, el):
        return os.path.join(self.__root, 'ocsp', self.__ocsp[el]['cert'])

    def populate(self, ver):
        for el in self.__ocsp:
            ver.addOCSPConf(el, self.__ocsp[el]['url'], \
                self._ocsp_cert_path(el), \
                self.__ocsp[el]['skew'], self.__ocsp[el]['maxAge'])

        ver.setSchemaDir(os.path.join(self.__root, 'schema'))
        ver.setDigestURI(self.__param['digest.uri'])

        cadir = os.path.join(self.__root, 'ca')

        for el in os.listdir(cadir):
            ver.addCertToStore(os.path.join(cadir, el))

    def get_ocsp_responders(self):
        # NB! One URL gets into dict only once
        ret = {}
        for el in self.__ocsp:
            url = self.__ocsp[el]['url']
            path = self._ocsp_cert_path(el)
            ret[url] = path
        return ret




if __name__ == '__main__':
    pass

# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = bdocpythonutils
#!/usr/bin/python2.7
# -*- coding: UTF8 -*-

"""
Copyright: Eesti Vabariigi Valimiskomisjon
(Estonian National Electoral Committee), www.vvk.ee
Written in 2004-2014 by Cybernetica AS, www.cyber.ee

This work is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivs 3.0 Unported License.
To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc-nd/3.0/.
"""

import os
import zipfile
import exception_msg

REF_MIMETYPE = 'application/vnd.etsi.asic-e+zip'
REF_FILE_MANIFEST = 'META-INF/manifest.xml'
REF_FILE_MIMETYPE = 'mimetype'

REF_MANIFEST_TMPL_1 = '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>'
REF_MANIFEST_TMPL_2 = \
    '<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmln' \
    's:manifest:1.0">'
REF_MANIFEST_TMPL_3 = \
    '<manifest:file-entry manifest:full-path="/" manifest:media-type="applic' \
    'ation/vnd.etsi.asic-e+zip"/>'
REF_MANIFEST_TMPL_4 = '</manifest:manifest>'

REF_MANIFEST_LINES = [ \
    REF_MANIFEST_TMPL_1,
    REF_MANIFEST_TMPL_2,
    REF_MANIFEST_TMPL_3,
    REF_MANIFEST_TMPL_4]

# DigiDocService's manifest is formatted differently than qdigidocclient's and
# ours, so it needs a separate reference.
REF_MANIFEST_DDS_TMPL_1 = '<?xml version="1.0" encoding="utf-8"?>'
REF_MANIFEST_DDS_TMPL_3 = \
        '<manifest:file-entry manifest:media-type='\
        '"application/vnd.etsi.asic-e+zip" manifest:full-path="/" />'

REF_MANIFEST_DDS_LINES = [ \
    REF_MANIFEST_DDS_TMPL_1,
    REF_MANIFEST_TMPL_2,
    REF_MANIFEST_DDS_TMPL_3,
    REF_MANIFEST_TMPL_4]


class ManifestProfile:

    def __init__(self, sigtype, datatype = None):
        self.__sigtype = sigtype
        self.__datatype = "application/x-encrypted-vote"
        if datatype:
            self.__datatype = datatype

    def __del__(self):
        pass

    def is_signature(self, filename):
        return ((filename.count('signature') > 0) and
            (filename.startswith('META-INF/')))

    def file_entry(self, filename, dds = False, sigtype = None):
        mimetype = self.__datatype

        lst = ["<manifest:file-entry",
               " manifest:full-path=\"%s\"" % filename,
               " manifest:media-type=\"%s\"" % mimetype,
               "/>"]
        if dds:
            # DigiDocService has media-type and full-path swapped...
            lst[1], lst[2] = lst[2], lst[1]
            # ...and a space before the closing bracket.
            lst[3] = " " + lst[3]
        return "".join(lst)

    def sigtype(self):
        return self.__sigtype


class BDocContainer:

    def __init__(self):
        self.__bdoc = None
        self.__manifest = None
        self.documents = {}
        self.signatures = {}
        self.prof = 'BES'


    def __del__(self):
        if self.__bdoc:
            self.__bdoc.close()

    def count_data_files(self):
        return len(self.documents)

    def count_signatures(self):
        return len(self.signatures)

    def load(self, bdocfile):
        self.__bdoc = zipfile.ZipFile(bdocfile)
        if self.__bdoc.testzip() != None:
            raise Exception, 'Invalid zipfile'

    def load_bytes(self, data):
        import StringIO
        dfile = StringIO.StringIO(data)
        self.load(dfile)

    def get_bytes(self):
        import StringIO
        dfile = StringIO.StringIO()
        try:
            dfile = StringIO.StringIO()
            zip = zipfile.ZipFile(dfile, 'w')
            zip.writestr(REF_FILE_MIMETYPE, REF_MIMETYPE)
            for el in self.documents:
                zip.writestr(el, self.documents[el])

            for el in self.signatures:
                zip.writestr(el, self.signatures[el])

            zip.writestr(REF_FILE_MANIFEST, self.__manifest)
            zip.close()
            return dfile.getvalue()
        finally:
            dfile.close()


    def addTM(self, filename, signature):
        self.signatures[filename] = signature
        self.prof = 'TM'


    def _validate_mimetype(self, contents):

        if not REF_FILE_MIMETYPE in contents:
            return False

        del contents[REF_FILE_MIMETYPE]

        mimetype = self.__bdoc.read(REF_FILE_MIMETYPE)
        if REF_MIMETYPE == mimetype:
            return True
        return False

    def _acquire_manifest(self, contents):
        if not REF_FILE_MANIFEST in contents:
            return False

        del contents[REF_FILE_MANIFEST]
        self.__manifest = self.__bdoc.read(REF_FILE_MANIFEST)
        return True

    def validateflex(self):
        def is_dds_profile(idx):
            return idx == 2
        profile_b = ManifestProfile('BES')
        profile_t = ManifestProfile('TM')
        self.validateimpl([profile_b, profile_t, profile_t], is_dds_profile)

    def validate(self, profile):
        def is_dds_profile(idx):
            return idx == 1
        self.validateimpl([profile, profile], is_dds_profile)

    def validateimpl(self, profiles, is_dds_profile):
        _infos = self.__bdoc.infolist()
        _contents = {}
        for _el in _infos:
            _contents[_el.filename.encode("utf8")] = None

        if not self._validate_mimetype(_contents):
            raise Exception, 'Invalid or missing MIME type'

        if not self._acquire_manifest(_contents):
            raise Exception, 'Could not load manifest'

        _lst = self.__manifest.rstrip().split('\n')
        _lst = filter(None, map(str.strip, _lst))
        _len1 = len(_lst)
        _input_set = set(_lst)
        _len2 = len(_input_set)

        if _len1 != _len2:
            raise Exception, 'Invalid manifest: input contains equal lines'

        _reference_sets = []
        for _i in range(len(profiles)):
            if is_dds_profile(_i):
                _reference_sets.append(set(REF_MANIFEST_DDS_LINES))
            else:
                _reference_sets.append(set(REF_MANIFEST_LINES))

        for _el in _contents:
            if _el != 'META-INF/' and \
                    not profiles[0].is_signature(_el):
                for _i, _profile in enumerate(profiles):
                    _reference_sets[_i].add(_profile.file_entry(_el, is_dds_profile(_i)))

        _profile = None
        for _i, _reference_set in enumerate(_reference_sets):
            if _reference_set == _input_set:
                _profile = profiles[_i]
                break
        else:
            print _reference_sets
            print _input_set
            raise Exception, 'Invalid manifest: not equal to reference set'

        self.prof = _profile.sigtype()
        for _el in _contents:
            if (_el != 'META-INF/'):
                if _profile.is_signature(_el):
                    self.signatures[_el] = self.__bdoc.read(_el)
                else:
                    self.documents[_el] = self.__bdoc.read(_el)


def save_temporary(data):
    import fcntl
    import tempfile

    tmp_fd = None
    tmp_fn = None
    tmp_file = None
    try:
        tmp_fd, tmp_fn = tempfile.mkstemp()
        tmp_file = os.fdopen(tmp_fd, 'w')
        tmp_fd = None
        fcntl.lockf(tmp_file, fcntl.LOCK_EX)
        tmp_file.write(data)
        tmp_file.close()
        tmp_file = None
    finally:
        if tmp_fd:
            os.close(tmp_fd)
        if tmp_file:
            tmp_file.close()
    return tmp_fn


def get_doc_content_file(filename, datatype = 'application/octet-stream'):
    bdoc = BDocContainer()
    bdoc.load(filename)
    profile = ManifestProfile('TM', datatype)
    bdoc.validate(profile)

    if not len(bdoc.documents) == 1:
        raise Exception("Invalid document count in BDOC")

    doc_fn, doc_content = bdoc.documents.popitem()
    return save_temporary(doc_content)


if __name__ == '__main__':
    pass

# vim:set ts=4 sw=4 et fileencoding=utf8:

########NEW FILE########
__FILENAME__ = bdoctesttool
#!/usr/bin/python
# -*- coding: utf-8 -*-

import bdocconfig
import bdocpython
import bdocpythonutils
import os
import sys

etc = '../../etc'
conf_dir = '../../bdocconf'

method = sys.argv[1]
if len(sys.argv) == 3:
    contentType = 'application/octet-stream'
elif len(sys.argv) == 4:
    contentType = sys.argv[3]
else:
    print "bdoctool mode file [content-type]"
    exit(1)

print 'Expecting content type:', contentType

with file(sys.argv[2]) as f:
    zipbytes = f.read()

bdocpython.initialize()

config = bdocconfig.BDocConfig()

bdoc = bdocpythonutils.BDocContainer()
bdoc.load_bytes(zipbytes)
profile_type = 'TM' if method == 'tm' else 'BES'
bdoc.validate(bdocpythonutils.ManifestProfile(profile_type,
                                              datatype = contentType))

sigfiles = bdoc.signatures.keys()
if len(sigfiles) == 0:
    raise Exception, "BDoc ei sisalda ühtegi allkirja"

sigfiles = bdoc.signatures.keys()
if len(sigfiles) != 1:
    raise Exception, "BDoc sisaldab rohkem kui ühte allkirja"

config.load(conf_dir)

verifier = bdocpython.BDocVerifier()
config.populate(verifier)
verifier.setSchemaDir(etc + '/schema')
certDir = etc + '/certs'
for el in os.listdir(certDir):
    print 'Adding certificate:', el
    verifier.addCertToStore(os.path.join(certDir, el))

if method == 'online' or method == 'tm':
    #verifier.addOCSPConf(issuer, url, cert, skew, maxAge)
    pass

for el in bdoc.documents:
    verifier.setDocument(bdoc.documents[el], el)

sig_fn = sigfiles[0]
sig_content = bdoc.signatures[sig_fn]

if method == 'online':
    print "Verify method: verifyInHTS"
    res = verifier.verifyInHTS(sig_content)
elif method == 'tm':
    print "Verify method: verifyTMOffline"
    res = verifier.verifyTMOffline(sig_content)
else:
    print "Verify method: verifyBESOffline"
    res = verifier.verifyBESOffline(sig_content)

print 'Result:', res.result
print 'Subject:', res.subject
print 'OCSP:', res.ocsp_time
print 'Error:', res.error

if method == 'online':
    bdoc.addTM(sig_fn, res.signature)
    bytes = bdoc.get_bytes()
    outf = open('tmp.tm.bdoc', 'w')
    outf.write(bytes)
    outf.close()

print 'Cert is valid:', res.cert_is_valid
print 'OCSP is good:', res.ocsp_is_good


########NEW FILE########
