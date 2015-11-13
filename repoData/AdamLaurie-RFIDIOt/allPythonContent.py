__FILENAME__ = bruteforce
#!/usr/bin/python

#  bruteforce.py - try random numbers to login to sector 0
# 
#  Adam Laurie <adam@algroup.co.uk>
#  http://rfidiot.org/
# 
#  This code is copyright (c) Adam Laurie, 2006, All rights reserved.
#  For non-commercial use only, the following terms apply - for all other
#  uses, please contact the author:
#
#    This code is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#


import rfidiot
import random
import sys
import os

try:
        card= rfidiot.card
except:
	print "Couldn't open reader!"
        os._exit(True)

args= rfidiot.args
help= rfidiot.help

card.info('bruteforce v0.1i')
card.select()
print 'Card ID: ' + card.uid

finished = 0
tries = 0
print ' Tries: %s\r' % tries,
sys.stdout.flush()           

while not finished:

	tries += 1
	if tries % 10 == 0:
		print ' Tries: %s\r' % tries,
		sys.stdout.flush()           

	if len(args) == 1:
		key= args[0]
		if len(key) != 12:
			print '  Static Key must be 12 HEX characters!'
			os._exit(True)
		print 'Trying static key: ' + key
	else:
		key = '%012x' % random.getrandbits(48)

	for type in ['AA', 'BB']:
		card.select()
		if card.login(0,type,key):
			print '\nlogin succeeded after %d tries!' % tries
			print 'key: ' + type + ' ' + key
			finished = 1
			break	
		elif card.errorcode != 'X' and card.errorcode != '6982' and card.errorcode != '6200':
			print '\nerror!'
			print 'key: ' + type +  ' ' + key
			print 'error code: ' + card.errorcode
			finished = 1
			break
	if finished:
		break
os._exit(False)

########NEW FILE########
__FILENAME__ = cardselect
#!/usr/bin/python


#  cardselect.py - select card and display ID
# 
#  Adam Laurie <adam@algroup.co.uk>
#  http://rfidiot.org/
# 
#  This code is copyright (c) Adam Laurie, 2006, All rights reserved.
#  For non-commercial use only, the following terms apply - for all other
#  uses, please contact the author:
#
#    This code is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#


import rfidiot
import sys
import os

try:
        card= rfidiot.card
except:
	print "Couldn't open reader!"
        os._exit(True)

args= rfidiot.args

card.info('cardselect v0.1m')
# force card type if specified
if len(args) == 1:
	card.settagtype(args[0])
else:
	card.settagtype(card.ALL)

if card.select():
	print '    Card ID: ' + card.uid
	if card.readertype == card.READER_PCSC:
		print '    ATR: ' + card.pcsc_atr
else:
	if card.errorcode:
		print '    '+card.ISO7816ErrorCodes[card.errorcode]
	else:
		print '    No card present'
		os._exit(True)
os._exit(False)

########NEW FILE########
__FILENAME__ = ChAP
#! /usr/bin/env python
"""
Script that tries to select the EMV Payment Systems Directory on all inserted cards.

Copyright 2008 RFIDIOt
Author: Adam Laurie, mailto:adam@algroup.co.uk
	http://rfidiot.org/ChAP.py

This file is based on an example program from scard-python.
  Originally Copyright 2001-2007 gemalto
  Author: Jean-Daniel Aussel, mailto:jean-daniel.aussel@gemalto.com

scard-python is free software; you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation; either version 2.1 of the License, or
(at your option) any later version.

scard-python is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with scard-python; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
"""

from smartcard.CardType import AnyCardType
from smartcard.CardRequest import CardRequest
from smartcard.CardConnection import CardConnection
from smartcard.CardConnectionObserver import ConsoleCardConnectionObserver
from smartcard.Exceptions import CardRequestTimeoutException

import getopt
import sys
from operator import *

# local imports
from rfidiot.iso3166 import ISO3166CountryCodes

# default global options
BruteforcePrimitives= False
BruteforceFiles= False
BruteforceAID= False
BruteforceEMV= False
OutputFiles= False
Debug= False
Protocol= CardConnection.T0_protocol
RawOutput= False
Verbose= False

# Global VARs for data interchange
Cdol1= ''
Cdol2= ''
CurrentAID= ''

# known AIDs
# please mail new AIDs to aid@rfidiot.org
KNOWN_AIDS= 	[
		['VISA',0xa0,0x00,0x00,0x00,0x03],
		['VISA Debit/Credit',0xa0,0x00,0x00,0x00,0x03,0x10,0x10],
		['VISA Credit',0xa0,0x00,0x00,0x00,0x03,0x10,0x10,0x01],
		['VISA Debit',0xa0,0x00,0x00,0x00,0x03,0x10,0x10,0x02],
		['VISA Electron',0xa0,0x00,0x00,0x00,0x03,0x20,0x10],
		['VISA Interlink',0xa0,0x00,0x00,0x00,0x03,0x30,0x10],
		['VISA Plus',0xa0,0x00,0x00,0x00,0x03,0x80,0x10],
		['VISA ATM',0xa0,0x00,0x00,0x00,0x03,0x99,0x99,0x10],
		['MASTERCARD',0xa0,0x00,0x00,0x00,0x04,0x10,0x10],
		['Maestro',0xa0,0x00,0x00,0x00,0x04,0x30,0x60],
		['Maestro UK',0xa0,0x00,0x00,0x00,0x05,0x00,0x01],
		['Maestro TEST',0xb0,0x12,0x34,0x56,0x78],
		['Self Service',0xa0,0x00,0x00,0x00,0x24,0x01],
		['American Express',0xa0,0x00,0x00,0x00,0x25],
		['ExpressPay',0xa0,0x00,0x00,0x00,0x25,0x01,0x07,0x01],
		['Link',0xa0,0x00,0x00,0x00,0x29,0x10,0x10],
	     	['Alias AID',0xa0,0x00,0x00,0x00,0x29,0x10,0x10],
	    	]

# Master Data File for PSE
DF_PSE = [0x31, 0x50, 0x41, 0x59, 0x2E, 0x53, 0x59, 0x53, 0x2E, 0x44, 0x44, 0x46, 0x30, 0x31]

# define the apdus used in this script
AAC= 0
TC= 0x40
ARQC= 0x80
GENERATE_AC= [0x80,0xae]
GET_CHALLENGE= [0x00,0x84,0x00]
GET_DATA = [0x80, 0xca]
GET_PROCESSING_OPTIONS = [0x80,0xa8,0x00,0x00,0x02,0x83,0x00,0x00]
GET_RESPONSE = [0x00, 0xC0, 0x00, 0x00 ]
READ_RECORD = [0x00, 0xb2]
SELECT = [0x00, 0xA4, 0x04, 0x00]
UNBLOCK_PIN= [0x84,0x24,0x00,0x00,0x00]
VERIFY= [0x00,0x20,0x00,0x80]

#BRUTE_AID= [0xa0,0x00,0x00,0x00]
BRUTE_AID= []

# define tags for response
BINARY= 0
TEXT= 1
BER_TLV= 2
NUMERIC= 3
MIXED= 4
TEMPLATE= 0
ITEM= 1
VALUE= 2
SFI= 0x88
CDOL1= 0x8c
CDOL2= 0x8d
TAGS= 	{	
	0x4f:['Application Identifier (AID)',BINARY,ITEM],
	0x50:['Application Label',TEXT,ITEM],
	0x57:['Track 2 Equivalent Data',BINARY,ITEM],
	0x5a:['Application Primary Account Number (PAN)',NUMERIC,ITEM],
	0x6f:['File Control Information (FCI) Template',BINARY,TEMPLATE],
	0x70:['Record Template',BINARY,TEMPLATE],
	0x77:['Response Message Template Format 2',BINARY,ITEM],
	0x80:['Response Message Template Format 1',BINARY,ITEM],
	0x82:['Application Interchange Profile',BINARY,ITEM],
	0x83:['Command Template',BER_TLV,ITEM],
	0x84:['DF Name',MIXED,ITEM],
	0x86:['Issuer Script Command',BER_TLV,ITEM],
	0x87:['Application Priority Indicator',BER_TLV,ITEM],
	0x88:['Short File Identifier',BINARY,ITEM],
	0x8a:['Authorisation Response Code',BINARY,VALUE],
	0x8c:['Card Risk Management Data Object List 1 (CDOL1)',BINARY,TEMPLATE],
	0x8d:['Card Risk Management Data Object List 2 (CDOL2)',BINARY,TEMPLATE],
	0x8e:['Cardholder Verification Method (CVM) List',BINARY,ITEM],
	0x8f:['Certification Authority Public Key Index',BINARY,ITEM],
	0x93:['Signed Static Application Data',BINARY,ITEM],
	0x94:['Application File Locator',BINARY,ITEM],
	0x95:['Terminal Verification Results',BINARY,VALUE],
	0x97:['Transaction Certificate Data Object List (TDOL)',BER_TLV,ITEM],
	0x9c:['Transaction Type',BINARY,VALUE],
	0x9d:['Directory Definition File',BINARY,ITEM],
	0xa5:['Proprietary Information',BINARY,TEMPLATE],
	0x5f20:['Cardholder Name',TEXT,ITEM],
	0x5f24:['Application Expiration Date YYMMDD',NUMERIC,ITEM],
	0x5f25:['Application Effective Date YYMMDD',NUMERIC,ITEM],
	0x5f28:['Issuer Country Code',NUMERIC,ITEM],
	0x5f2a:['Transaction Currency Code',BINARY,VALUE],
	0x5f2d:['Language Preference',TEXT,ITEM],
	0x5f30:['Service Code',NUMERIC,ITEM],
	0x5f34:['Application Primary Account Number (PAN) Sequence Number',NUMERIC,ITEM],
	0x5f50:['Issuer URL',TEXT,ITEM],
	0x92:['Issuer Public Key Remainder',BINARY,ITEM],
	0x9a:['Transaction Date',BINARY,VALUE],
	0x9f02:['Amount, Authorised (Numeric)',BINARY,VALUE],
	0x9f03:['Amount, Other (Numeric)',BINARY,VALUE],
	0x9f04:['Amount, Other (Binary)',BINARY,VALUE],
	0x9f05:['Application Discretionary Data',BINARY,ITEM],
	0x9f07:['Application Usage Control',BINARY,ITEM],
	0x9f08:['Application Version Number',BINARY,ITEM],
	0x9f0d:['Issuer Action Code - Default',BINARY,ITEM],
	0x9f0e:['Issuer Action Code - Denial',BINARY,ITEM],
	0x9f0f:['Issuer Action Code - Online',BINARY,ITEM],
	0x9f11:['Issuer Code Table Index',BINARY,ITEM],
	0x9f12:['Application Preferred Name',TEXT,ITEM],
	0x9f1a:['Terminal Country Code',BINARY,VALUE],
	0x9f1f:['Track 1 Discretionary Data',TEXT,ITEM],
	0x9f20:['Track 2 Discretionary Data',TEXT,ITEM],
	0x9f26:['Application Cryptogram',BINARY,ITEM],
	0x9f32:['Issuer Public Key Exponent',BINARY,ITEM],
	0x9f36:['Application Transaction Counter',BINARY,ITEM],
	0x9f37:['Unpredictable Number',BINARY,VALUE],
	0x9f38:['Processing Options Data Object List (PDOL)',BINARY,TEMPLATE],
	0x9f42:['Application Currency Code',NUMERIC,ITEM],
	0x9f44:['Application Currency Exponent',NUMERIC,ITEM],
	0x9f4a:['Static Data Authentication Tag List',BINARY,ITEM],
	0x9f4d:['Log Entry',BINARY,ITEM],
	0x9f66:['Card Production Life Cycle',BINARY,ITEM],
	0xbf0c:['File Control Information (FCI) Issuer Discretionary Data',BER_TLV,TEMPLATE],
	}

#// conflicting item - need to check
#// 0x9f38:['Processing Optional Data Object List',BINARY,ITEM],

# define BER-TLV masks

TLV_CLASS_MASK= {	
		0x00:'Universal class',
		0x40:'Application class',
		0x80:'Context-specific class',
		0xc0:'Private class',
		}

# if TLV_TAG_NUMBER_MASK bits are set, refer to next byte(s) for tag number
# otherwise it's b1-5
TLV_TAG_NUMBER_MASK= 0x1f

# if TLV_DATA_MASK bit is set it's a 'Constructed data object'
# otherwise, 'Primitive data object'
TLV_DATA_MASK= 	0x20
TLV_DATA_TYPE= ['Primitive data object','Constructed data object']

# if TLV_TAG_MASK is set another tag byte follows
TLV_TAG_MASK= 0x80
TLV_LENGTH_MASK= 0x80


# define AIP mask
AIP_MASK= {
	  0x01:'CDA Supported (Combined Dynamic Data Authentication / Application Cryptogram Generation)',
	  0x02:'RFU',
	  0x04:'Issuer authentication is supported',
	  0x08:'Terminal risk management is to be performed',
	  0x10:'Cardholder verification is supported',
	  0x20:'DDA supported (Dynamic Data Authentication)',
	  0x40:'SDA supported (Static Data Authentiction)',
	  0x80:'RFU'
	  }

# define dummy transaction values (see TAGS for tag names)
# for generate_ac
TRANS_VAL= {
	   0x9f02:[0x00,0x00,0x00,0x00,0x00,0x01],
	   0x9f03:[0x00,0x00,0x00,0x00,0x00,0x00],
	   0x9f1a:[0x08,0x26],
	   0x95:[0x00,0x00,0x00,0x00,0x00],
	   0x5f2a:[0x08,0x26],
	   0x9a:[0x08,0x04,0x01],
	   0x9c:[0x01],
	   0x9f37:[0xba,0xdf,0x00,0x0d]
	   }
	
# define SW1 return values
SW1_RESPONSE_BYTES= 0x61
SW1_WRONG_LENGTH= 0x6c
SW12_OK= [0x90,0x00]
SW12_NOT_SUPORTED= [0x6a,0x81]
SW12_NOT_FOUND= [0x6a,0x82]
SW12_COND_NOT_SAT= [0x69,0x85]		# conditions of use not satisfied 
PIN_BLOCKED= [0x69,0x83]
PIN_BLOCKED2= [0x69,0x84]
PIN_WRONG= 0x63

# some human readable error messages
ERRORS= {
	'6700':"Not known",
	'6985':"Conditions of use not satisfied or Command not supported",
	'6984':"PIN Try Limit exceeded"
	}

# define GET_DATA primitive tags
PIN_TRY_COUNTER= [0x9f,0x17]
ATC= [0x9f,0x36]
LAST_ATC= [0x9f,0x13]
LOG_FORMAT= [0x9f, 0x4f]

# define TAGs after BER-TVL decoding
BER_TLV_AIP= 0x02
BER_TLV_AFL= 0x14 

def printhelp():
	print '\nChAP.py - Chip And PIN in Python'
	print 'Ver 0.1c\n'
	print 'usage:\n\n ChAP.py [options] [PIN]'
	print
	print 'If the optional numeric PIN argument is given, the PIN will be verified (note that this' 
	print 'updates the PIN Try Counter and may result in the card being PIN blocked).'
	print '\nOptions:\n'
	print '\t-a\t\tBruteforce AIDs'
	print '\t-A\t\tPrint list of known AIDs'
	print '\t-d\t\tDebug - Show PC/SC APDU data'
	print '\t-e\t\tBruteforce EMV AIDs'
	print '\t-f\t\tBruteforce files'
	print '\t-h\t\tPrint detailed help message'
	print '\t-o\t\tOutput to files ([AID]-FILExxRECORDxx.HEX)'
	print '\t-p\t\tBruteforce primitives'
	print '\t-r\t\tRaw output - do not interpret EMV data'
	print '\t-t\t\tUse T1 protocol (default is T0)'
	print '\t-v\t\tVerbose on'
        print

def hexprint(data):
	index= 0

	while index < len(data):
		print '%02x' % data[index],
		index += 1
	print

def get_tag(data,req):
	"return a tag's data if present"

	index= 0

	# walk the tag chain to ensure no false positives
	while index < len(data):
		try:
			# try 1-byte tags
			tag= data[index]	
			TAGS[tag]
			taglen= 1
		except:
			try:
				# try 2-byte tags
				tag= data[index] * 256 + data[index+1]
				TAGS[tag]
				taglen= 2
			except:
				# tag not found
				index += 1
				continue
		if tag == req:
			itemlength= data[index + taglen]
			index += taglen + 1
			return True, itemlength, data[index:index + itemlength]
		else:
			index += taglen + 1
	return False,0,''

def isbinary(data):
	index= 0

	while index < len(data):
		if data[index] < 0x20 or data[index] > 0x7e:
			return True
		index += 1
	return False

def decode_pse(data):
	"decode the main PSE select response"

	index= 0
	indent= ''

	if OutputFiles:
		file= open('%s-PSE.HEX' % CurrentAID,'w')
		for n in range(len(data)):
			file.write('%02X' % data[n])
		file.flush()
		file.close()

		
	if RawOutput:
		hexprint(data)
		textprint(data)
		return

	while index < len(data):
		try:
			tag= data[index]
			TAGS[tag]
			taglen= 1
		except:
			try:
				tag= data[index] * 256 + data[index+1]
				TAGS[tag]
				taglen= 2
			except:
				print indent + '  Unrecognised TAG:', 
				hexprint(data[index:])
				return
		print indent + '  %0x:' % tag, TAGS[tag][0],
		if TAGS[tag][2] == VALUE:
			itemlength= 1
			offset= 0
		else:
			itemlength= data[index + taglen]
			offset= 1
		print '(%d bytes):' % itemlength,
		# store CDOLs for later use
		if tag == CDOL1:
			Cdol1= data[index + taglen:index + taglen + itemlength + 1]
		if tag == CDOL2:
			Cdol2= data[index + taglen:index + taglen + itemlength + 1]
		out= ''
		mixedout= []
		while itemlength > 0:
			if TAGS[tag][1] == BER_TLV:
				print 'skipping BER-TLV object!'
				return
				#decode_ber_tlv_field(data[index + taglen + offset:])
			if TAGS[tag][1] == BINARY or TAGS[tag][1] == VALUE:
					if TAGS[tag][2] != TEMPLATE or Verbose:
						print '%02x' % data[index + taglen + offset],
			else: 
				if TAGS[tag][1] == NUMERIC:
					out += '%02x' % data[index + taglen + offset]
				else:
					if TAGS[tag][1] == TEXT:
						out += "%c" % data[index + taglen + offset]
					if TAGS[tag][1] == MIXED:
						mixedout.append(data[index + taglen + offset])
			itemlength -= 1
			offset += 1
		if TAGS[tag][1] == MIXED:
			if isbinary(mixedout):
				hexprint(mixedout)
			else:
				textprint(mixedout)
		if TAGS[tag][1] == BINARY:
			print
		if TAGS[tag][1] == TEXT or TAGS[tag][1] == NUMERIC:
			print out,
			if tag == 0x9f42 or tag == 0x5f28:
				print '(' + ISO3166CountryCodes['%03d' % int(out)] + ')'
			else:
				print
		if TAGS[tag][2] == ITEM:
			index += data[index + taglen] + taglen + 1
		else:
			index += taglen + 1
#			if TAGS[tag][2] != VALUE:
#				indent += '   ' 
	indent= ''

def textprint(data):
	index= 0
	out= ''

	while index < len(data):
		if data[index] >= 0x20 and data[index] < 0x7f:
			out += chr(data[index])
		else:
			out += '.'
		index += 1
	print out

def bruteforce_primitives():
	for x in range(256):
		for y in range(256):
			status, length, response= get_primitive([x,y])
			if status:
				print 'Primitive %02x%02x: ' % (x,y)
				if response:
					hexprint(response)
					textprint(response)

def get_primitive(tag):
	# get primitive data object - return status, length, data
	le= 0x00
	apdu = GET_DATA + tag + [le]
	response, sw1, sw2 = send_apdu(apdu)
	if response[0:2] == tag:
		length= response[2]
		return True, length, response[3:]
	else:
		return False, 0, ''

def check_return(sw1,sw2):
	if [sw1,sw2] == SW12_OK:
		return True
	return False

def send_apdu(apdu):
	# send apdu and get additional data if required 
	response, sw1, sw2 = cardservice.connection.transmit( apdu, Protocol )
	if sw1 == SW1_WRONG_LENGTH:
		# command used wrong length. retry with correct length.
		apdu= apdu[:len(apdu) - 1] + [sw2]
		return send_apdu(apdu)
	if sw1 == SW1_RESPONSE_BYTES:
		# response bytes available.
		apdu = GET_RESPONSE + [sw2]
		response, sw1, sw2 = cardservice.connection.transmit( apdu, Protocol )
	return response, sw1, sw2

def select_aid(aid):
	# select an AID and return True/False plus additional data
	apdu = SELECT + [len(aid)] + aid + [0x00]
	response, sw1, sw2= send_apdu(apdu)
	if check_return(sw1,sw2):
		if Verbose:
			decode_pse(response)
		return True, response, sw1, sw2
	else:
		return False, [], sw1,sw2

def bruteforce_aids(aid):
	#brute force two digits of AID
	print 'Bruteforcing AIDs'
	y= z= 0
	if BruteforceEMV:
		brute_range= [0xa0]
	else:
		brute_range= range(256)
	for x in brute_range:
		for y in range(256):
			for z in range(256):
				#aidb= aid + [x]
				aidb= [x,y,0x00,0x00,z]
				if Verbose:
					print '\r  %02x %02x %02x %02x %02x' % (x,y,0x00,0x00,z),
				status, response, sw1, sw2= select_aid(aidb)
				if [sw1,sw2] != SW12_NOT_FOUND:
					print '\r  Found AID:',
					hexprint(aidb)
					if status:
						decode_pse(response)
					else:
						print 'SW1 SW2: %02x %02x' % (sw1,sw2)

def read_record(sfi,record):
	# read a specific record from a file
	p1= record
	p2= (sfi << 3) + 4
	le= 0x00
	apdu= READ_RECORD + [p1,p2,le]
	response, sw1, sw2= send_apdu(apdu)
	if check_return(sw1,sw2):
		return True, response
	else:
		return False, ''

def bruteforce_files():
	# now try and brute force records
	print '  Checking for files:'
	for y in range(1,31):
		for x in range(1,256):
			ret, response= read_record(y,x)
			if ret:
				print "  Record %02x, File %02x: length %d" % (x,y,len(response))
				if Verbose:
					hexprint(response)
					textprint(response)
				decode_pse(response)

def get_processing_options():
	apdu= GET_PROCESSING_OPTIONS
	response, sw1, sw2= send_apdu(apdu)
	if check_return(sw1,sw2):
		return True, response
	else:
		return False, "%02x%02x" % (sw1,sw2)

def decode_processing_options(data):
	# extract and decode AIP (Application Interchange Profile)
	# and AFL (Application File Locator)
	if data[0] == 0x80:
		# data is in response format 1
		# first two bytes after length byte are AIP
		decode_aip(data[2:])
		# remaining data is AFL
		x= 4
		while x < len(data):
			sfi, start, end, offline= decode_afl(data[x:x+4])
			print '    SFI %02X: starting record %02X, ending record %02X; %02X offline data authentication records' % (sfi,start,end,offline)
			x += 4
			decode_file(sfi,start,end)
	if data[0] == 0x77:
		# data is in response format 2 (BER-TLV)
		x= 2
		while x < len(data):
			tag, fieldlen, value= decode_ber_tlv_item(data[x:])
			print '-- Value: ', hexprint(value)
			if tag == BER_TLV_AIP:
				decode_aip(value)
			if tag == BER_TLV_AFL:
				sfi, start, end, offline= decode_afl(value)
				print '    SFI %02X: starting record %02X, ending record %02X; %02X offline data authentication records' % (sfi,start,end,offline)
				decode_file(sfi,start,end)
			x += fieldlen

def decode_file(sfi,start,end):
	for y in range(start,end + 1):
		ret, response= read_record(sfi,y)
		if ret:
			if OutputFiles:
				file= open('%s-FILE%02XRECORD%02X.HEX' % (CurrentAID,sfi,y),'w')
				for n in range(len(response)):
					file.write('%02X' % response[n])
				file.flush()
				file.close()
			print '      record %02X: ' % y,
			decode_pse(response)
		else:
			print 'Read error!'


def decode_aip(data):
	# byte 1 of AIP is bit masked, byte 2 is RFU
	for x in AIP_MASK.keys():
		if data[0] & x:
			print '    ' + AIP_MASK[x]

def decode_afl(data):
	print '-- deccode_afl data: ', hexprint(data)
	sfi= int(data[0] >> 3)
	start= int(data[1])
	end= int(data[2])
	offline= int(data[3])
	return sfi, start, end, offline

def decode_ber_tlv_field(data):
	x= 0
	while x < len(data):
		tag, fieldlen, value= decode_ber_tlv_item(data[x:])
		print 'Tag %04X: ' % tag,
		hexprint(value)
		x += fieldlen

def decode_ber_tlv_item(data):
	# return tag, total length of data processed and value for BER-TLV object
	tag= data[0] & TLV_TAG_NUMBER_MASK
	i= 1
	if tag == TLV_TAG_NUMBER_MASK:
		tag= ''
		while data[i] & TLV_TAG_MASK:
			# another tag byte follows
			tag.append(xor(data[i],TLV_TAG_MASK))
			i += 1
		tag.append(data[i])
		i += 1
	if data[i] & TLV_LENGTH_MASK:
		# this byte tells us the number of subsequent bytes that describe the length
		lenlen= xor(data[i],TLV_LENGTH_MASK)
		i += 1
		length= int(data[i])
		z= 1
		while z < lenlen:
			i += 1
			z += 1
			length= length << 8
			length += int(data[i]) 
		i += 1
	else:
		length= int(data[i])
		i += 1
	return tag, i + length, data[i:i+length]

def get_challenge(bytes):
	lc= bytes
	le= 0x00
	apdu= GET_CHALLENGE + [lc,le]
	response, sw1, sw2= send_apdu(apdu)
	if check_return(sw1,sw2):
		print 'Random number: ',
		hexprint(response)
	#print 'GET CHAL: %02x%02x %d' % (sw1,sw2,len(response))

def verify_pin(pin):
	# construct offline PIN block and verify (plaintext)
	print 'Verifying PIN:',pin
	control= 0x02
	pinlen= len(pin)
	block= []
	block.append((control << 4) + pinlen)
	x= 0
	while x < len(pin):
		leftnibble= int(pin[x])
		try:
			rightnibble= int(pin[x + 1])	
		except:
			# pad to even length
			rightnibble= 0x0f
		block.append((leftnibble << 4) + rightnibble)
		x += 2
	while(len(block) < 8):
		block.append(0xff)
	lc= len(block)
	apdu= VERIFY + [lc] + block
	response, sw1, sw2= send_apdu(apdu)
	if check_return(sw1,sw2):
		print 'PIN verified'
		return True
	else:
		if [sw1,sw2] == PIN_BLOCKED or [sw1,sw2] == PIN_BLOCKED2:
			print 'PIN blocked!'
		else:
			if sw1 == PIN_WRONG:
				print 'wrong PIN - %d tries left' % (int(sw2) & 0x0f)
			if [sw1,sw2] == SW12_NOT_SUPORTED:
				print 'Function not supported'
			else:
				print 'command failed!', 
				hexprint([sw1,sw2])
	return False

def update_pin_try_counter(tries):
	# try to set Pin Try Counter by sending Card Status Update
	if tries > 0x0f:
		return False, 'PTC max value exceeded'
	csu= []
	csu.append(tries)
	csu.append(0x10)
	csu.append(0x00)
	csu.append(0x00)
	tag= 0x91 # Issuer Authentication Data
	lc= len(csu) + 1

def generate_ac(type):
	# generate an application Cryptogram
	if type == TC:
		# populate data with CDOL1
		print 
	apdu= GENERATE_AC + [lc,type] + data + [le]
	le= 0x00
	response, sw1, sw2= send_apdu(apdu)
	if check_return(sw1,sw2):
		print 'AC generated!'
		return True
	else:
		hexprint([sw1,sw2])
	

# main loop
aidlist= KNOWN_AIDS

try:
	# 'args' will be set to remaining arguments (if any)
	opts, args  = getopt.getopt(sys.argv[1:],'aAdefoprtv')
	for o, a in opts:
		if o == '-a':
			BruteforceAID= True
		if o == '-A':
			print
			for x in range(len(aidlist)):
				print '% 20s: ' % aidlist[x][0],
				hexprint(aidlist[x][1:])
			print
			sys.exit(False)	
		if o == '-d':
			Debug= True
		if o == '-e':
			BruteforceAID= True
			BruteforceEMV= True
		if o == '-f':
			BruteforceFiles= True
		if o == '-o':
			OutputFiles= True
		if o == '-p':
			BruteforcePrimitives= True
		if o == '-r':
			RawOutput= True
		if o == '-t':
			Protocol= CardConnection.T1_protocol
		if o == '-v':
			Verbose= True

except getopt.GetoptError:
	# -h will cause an exception as it doesn't exist!
	printhelp()
	sys.exit(True)

PIN= ''
if args:
	if not args[0].isdigit():
		print 'Invalid PIN', args[0]
		sys.exit(True)
	else:
		PIN= args[0]

try:
	# request any card type
	cardtype = AnyCardType()
	# request card insertion
	print 'insert a card within 10s'
	cardrequest = CardRequest( timeout=10, cardType=cardtype )
	cardservice = cardrequest.waitforcard()

	# attach the console tracer
	if Debug:
		observer=ConsoleCardConnectionObserver()
    		cardservice.connection.addObserver( observer )

	# connect to the card
	cardservice.connection.connect(Protocol)

	#get_challenge(0)

	# try to select PSE
	apdu = SELECT + [len(DF_PSE)] + DF_PSE
	response, sw1, sw2 = send_apdu( apdu )

	if check_return(sw1,sw2):
		# there is a PSE
		print 'PSE found!'
		decode_pse(response)
		if BruteforcePrimitives:
			# brute force primitives
			print 'Brute forcing primitives'
			bruteforce_primitives()
		if BruteforceFiles:
			print 'Brute forcing files'
			bruteforce_files()
		status, length, psd= get_tag(response,SFI)
		if not status:
			print 'No PSD found!'
		else:
			print '  Checking for records:',
			if BruteforcePrimitives:
				psd= range(31)
				print '(bruteforce all files)'
			else:
				print
			for x in range(256):
				for y in psd:
					p1= x
					p2= (y << 3) + 4
					le= 0x00
					apdu= READ_RECORD + [p1] + [p2,le]
					response, sw1, sw2 = cardservice.connection.transmit( apdu )
					if sw1 == 0x6c:
						print "  Record %02x, File %02x: length %d" % (x,y,sw2)
						le= sw2
						apdu= READ_RECORD + [p1] + [p2,le]
						response, sw1, sw2 = cardservice.connection.transmit( apdu )
						print "  ",
						aid= ''
						if Verbose:
							hexprint(response)
							textprint(response)
						i= 0
						while i < len(response):
							# extract the AID
							if response[i] == 0x4f and aid == '':
								aidlen= response[i + 1]
								aid= response[i + 2:i + 2 + aidlen]
							i += 1
						print '   AID found:',
						hexprint(aid)
						aidlist.append(['PSD Entry']+aid)
	if BruteforceAID:
		bruteforce_aids(BRUTE_AID)
	if aidlist:
		# now try dumping the AID records
		current= 0
		while current < len(aidlist):
			if Verbose:
				print 'Trying AID: %s -' % aidlist[current][0],
				hexprint(aidlist[current][1:])
			selected, response, sw1, sw2= select_aid(aidlist[current][1:])
			if selected:
				CurrentAID= ''
				for n in range(len(aidlist[current][1:])):
					CurrentAID += '%02X' % aidlist[current][1:][n]
				if Verbose:
					print '  Selected: ',
					hexprint(response)
					textprint(response)
				else:
					print '  Found AID: %s -' % aidlist[current][0],
					hexprint(aidlist[current][1:])
				decode_pse(response)
				if BruteforcePrimitives:
					# brute force primitives
					print 'Brute forcing primitives'
					bruteforce_primitives()
				if BruteforceFiles:
					print 'Brute forcing files'
					bruteforce_files()
				ret, response= get_processing_options()
				if ret:
					print '  Processing Options:',
					decode_pse(response)						
					decode_processing_options(response)
				else:
					print '  Could not get processing options:', response, ERRORS[response]
				ret, length, pins= get_primitive(PIN_TRY_COUNTER)
				if ret:
					ptc= int(pins[0])
					print '  PIN tries left:', ptc
					#if ptc == 0:
					#	print 'unblocking PIN'
					#	update_pin_try_counter(3)
					#	ret, sw1, sw2= send_apdu(UNBLOCK_PIN)
					#	hexprint([sw1,sw2])
				if PIN:
					if verify_pin(PIN):
						sys.exit(False)
					else:
						sys.exit(True)
				ret, length, atc= get_primitive(ATC)
				if ret:
					atcval= (atc[0] << 8) + atc[1]
					print '  Application Transaction Counter:', atcval
				ret, length, latc= get_primitive(LAST_ATC)
				if ret:
					latcval= (latc[0] << 8) + latc[1]
					print '  Last ATC:', latcval
				ret, length, logf= get_primitive(LOG_FORMAT)
				if ret:
					print 'Log Format: ',
					hexprint(logf)
				current += 1
			else:
				if Verbose:
					print '  Not found: %02x %02x' % (sw1,sw2)
				current += 1
	else:
		print 'no PSE: %02x %02x' % (sw1,sw2)

except CardRequestTimeoutException:
	print 'time-out: no card inserted during last 10s'

if 'win32'==sys.platform:
	print 'press Enter to continue'
	sys.stdin.read(1)

########NEW FILE########
__FILENAME__ = copytag
#!/usr/bin/python

#  copytag.py - read all sectors from a standard tag and write them back 
#               to a blank
# 
#  Adam Laurie <adam@algroup.co.uk>
#  http://rfidiot.org/
# 
#  This code is copyright (c) Adam Laurie, 2006, All rights reserved.
#  For non-commercial use only, the following terms apply - for all other
#  uses, please contact the author:
#
#    This code is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#


import rfidiot
import sys
import os
import string

try:
        card= rfidiot.card
except:
	print "Couldn't open reader!"
        os._exit(True)

card.info('copytag v0.1d')
card.select()
print '\nID: ' + card.uid
print '  Reading:'

buffer= []

card.select()
for x in range(98):
	if card.readblock(x):
		print '    Block %02x: %s\r' % (x , card.data),
		sys.stdout.flush()
		buffer.append(card.data)		
	else:
		if x == 0:
			print 'Read error: ', card.ISO7816ErrorCodes[card.errorcode]
		break

if x > 0:
	print '\nRead %d blocks' % x
	raw_input('Remove source tag and hit <CR> to continue...')
	targettype= card.tagtype	
	while 42:
		card.waitfortag('Waiting for blank tag...')
		print 'ID: ' + card.uid
		if card.tagtype != targettype:
			raw_input('Invalid tag type! Hit <CR> to continue...')
			continue
		if not card.readblock(0):
			raw_input('Tag not readable! Hit <CR> to continue...')
			continue
		if len(card.data) != len(buffer[0]):
			print 'Wrong blocksize! (%d / %d)' % (len(buffer[0]),len(card.data)),
			raw_input(' Hit <CR> to continue...')
			continue
		if string.upper(raw_input('*** Warning! Data will be overwritten! Continue (y/n)?')) == 'Y':
			break
		else:
			os._exit(False)
	print '  Writing:'
	for n in range(x):
		print '    Block %02x: %s\r' % (n , buffer[n]),
		sys.stdout.flush()
		if not card.writeblock(n, buffer[n]):
			print '\nWrite failed!'
	print '\n  Verifying:'
	for n in range(x):
		print '    Block %02x: %s' % (n , buffer[n]),
		if not card.readblock(n) or card.data != buffer[n]:
			print '\nVerify failed!'
			os._exit(True)
		print ' OK\r',
		sys.stdout.flush()
	print
	os._exit(False)
else:
	print 'No data!'
	os._exit(True)

########NEW FILE########
__FILENAME__ = demotag
#!/usr/bin/python

#  demotag.py - test IAIK TUG DemoTag`
# 
#  Adam Laurie <adam@algroup.co.uk>
#  http://rfidiot.org/
# 
#  This code is copyright (c) Adam Laurie, 2006, All rights reserved.
#  For non-commercial use only, the following terms apply - for all other
#  uses, please contact the author:
#
#    This code is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#

import rfidiot
import sys
import os

try:
        card= rfidiot.card
except:
	print "Couldn't open reader!"
        os._exit(False)

args= rfidiot.args

print 'Setting ID to: ' + args[0]
print card.demotag(card.DT_SET_UID,card.ToBinary(args[0]))

########NEW FILE########
__FILENAME__ = eeprom
#!/usr/bin/python

#  eeprom.py - display reader's eeprom settings
# 
#  Adam Laurie <adam@algroup.co.uk>
#  http://rfidiot.org/
# 
#  This code is copyright (c) Adam Laurie, 2006, All rights reserved.
#  For non-commercial use only, the following terms apply - for all other
#  uses, please contact the author:
#
#    This code is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#


import rfidiot
import sys
import os

try:
        card= rfidiot.card
except:
	print "Couldn't open reader!"
        os._exit(True)

card.info('eeprom v0.1e')
print 'Station:\t' + card.station()
print 'Protocol:\t' + card.PCON()
print 'Protocol2:\t' + card.PCON2()
print 'Protocol3:\t' + card.PCON3()

address= 0
while address < 0xf0:
	print 'address %02x:\t%s' % (address,card.readEEPROM(address))
	address += 1

########NEW FILE########
__FILENAME__ = fdxbnum
#!/usr/bin/python

#  fdxbnum.py - generate / decode FDX-B EM4x05 compliant IDs
# 
#  Adam Laurie <adam@algroup.co.uk>
#  http://rfidiot.org/
# 
#  This code is copyright (c) Adam Laurie, 2006, All rights reserved.
#  For non-commercial use only, the following terms apply - for all other
#  uses, please contact the author:
#
#    This code is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#


import rfidiot
import sys
import os
import string

try:
	card= rfidiot.card
except:
	os._exit(True)

args= rfidiot.args
help= rfidiot.help

card.info('fdxbnum v0.1f')

precoded= False

if not help and (len(args) == 1 or len(args) == 2):
	print "Decode: "
	if len(args[0]) == 16:
        	card.FDXBIDPrint(args[0])
	else:
		card.FDXBIDPrint(args[0][1:])
	if len(args) == 2:
		if args[1] == 'WRITE':
			precoded= True
		else:
			print 'Unrecognised option: ' + args[1]
			os._exit(True)
	else:
		os._exit(False)

if not help and (len(args) >= 3 or precoded):
	if precoded:
		id= args[0]
	else:
		print "Encode: ",
		id= card.FDXBIDEncode(args[0],args[1],args[2])
		print id
	out= card.FDXBID128Bit(id)
	print 'binary is',out
	if (len(args) == 4 and args[3] == 'WRITE') or precoded:
       		while True:
			# Q5 must be forced into Q5 mode to be sure of detection so try that first 
			if card.readertype == card.READER_ACG:
				card.settagtype(card.Q5)
			card.select()
			if card.readertype == card.READER_ACG:
				if not card.tagtype == card.Q5:
					card.settagtype(card.ALL)
               		card.waitfortag('Waiting for blank tag...')
               		print '  Tag ID: ' + card.data
			if card.tagtype == card.Q5 or card.tagtype == card.HITAG2:
               			x= string.upper(raw_input('  *** Warning! This will overwrite TAG! Proceed (y/n)? '))
               			if x == 'N':
                       			os._exit(False)
               			if x == 'Y':
                       			break
			else:
				x= raw_input('  Incompatible TAG! Hit <RETURN> to retry...')
		writetag= True
		print
	else:
		writetag= False
	# now turn it all back to 4 byte hex blocks for writing
	outbin= ''
	outhex= ['','','','','']
	# control block for Q5:
	# carrier 32 (2 * 15 + 2)
	# rf/? (don't care) - set to 00
	# data inverted
	# biphase
	# maxblock 4
	print '  Q5 Control Block:  ',
	q5control= '6000F0E8'
	print q5control
	for x in range(0,len(out),8):
		outbin += chr(int(out[x:x + 8],2))
	for x in range(0,len(outbin),4):
		print '    Q5 Data Block %02d:' % (x / 4 + 1),
		outhex[x / 4 + 1]= card.ToHex(outbin[x:x+4])
		print outhex[x / 4 + 1]
	# control block for Hitag2
	# Public Mode B
	# default password
	print
	print '  Hitag2 Control Block:  ',
	h2control= card.HITAG2_PUBLIC_B + card.HITAG2_TRANSPORT_TAG
	print h2control
	for x in range(1,5,1):
		print '    Hitag2 Data Block %02d:' % (x + 3),
		print outhex[x]
	if writetag == True:
		print 
		print '  Writing to tag type: ' + card.LFXTags[card.tagtype]
		if card.tagtype == card.Q5:
			outhex[0]= q5control
			offset= 0
		if card.tagtype == card.HITAG2:
			outhex[0]= h2control
			offset= 3
			if card.readertype == card.READER_ACG:	
				card.login('','',card.HITAG2_TRANSPORT_RWD)
		for x in range(4 + offset,-1 + offset,-1):
			print "    Writing block %02x:" % x,
        		if not card.writeblock(x,outhex[x - offset]):
				# we expect a Q5 to fail after writing the control block as it re-reads
				# it before trying to verify the write and switches mode so is now no longer in Q5 mode
				if x == offset:
					print '    Control:  ' + outhex[x - offset]
					print
					print '  Done!'
					# now check for FDX-B ID
               				card.settagtype(card.EM4x05)
					card.select()
					print '  Card ID: ' + card.data
				else:
                			print 'Write failed!'
					if card.readertype == card.READER_FROSCH:
						print card.FROSCH_Errors[card.errorcode]
                			os._exit(True)
			else:
				# hitag2 don't change mode until the next time they're selected so write
				# confirmation of control block should be ok
				if x == offset:
					print '    Control:  ' + outhex[x - offset]
					print
					print '  Done!'
					# now check for FDX-B ID
					card.reset()
               				card.settagtype(card.EM4x05)
					card.select()
					print '  Card ID: ' + card.data
				else:
					print outhex[x - offset]
		if card.readertype == card.READER_ACG:	
               		card.settagtype(card.ALL)
	os._exit(False)
print sys.argv[0] + ' - generate / decode FDX-B EM4x05 compliant IDs'
print 'Usage: ' + sys.argv[0] + ' [OPTIONS] <ID> [WRITE] | <APPID> <COUNTRY CODE> <NATIONAL ID> [WRITE]'
print
print '\tIf a single 16 HEX digit ID is provided, it will be decoded according to the FDX-B standard.'
print '\tAlternatively, specifying a 4 HEX digit Application ID, 3 or 4 digit decimal country code'
print '\t(normally based on ISO-3166 country codes or ICAR.ORG manufacturer codes, range 0 - 4095)'
print '\tand a decimal National ID Number will generate a 16 HEX digit ID.'
print '\tNote: Application ID 8000 is \'Animal\', and 0000 is non-Animal.'
print '\tMaximum value for country code is 999 according to the standard, but 4 digits will work.'
print '\tMaximum value for National ID is 274877906943.'
print
print '\tIf the WRITE option is specified, a Q5 or Hitag2 will be programmed to emulate FDX-B.'
print
os._exit(True)

########NEW FILE########
__FILENAME__ = formatmifare1kvalue
#!/usr/bin/python

#  formatmifare1kvalue.py - format value blocks on a mifare standard tag
# 
#  Adam Laurie <adam@algroup.co.uk>
#  http://rfidiot.org/
# 
#  This code is copyright (c) Adam Laurie, 2006, All rights reserved.
#  For non-commercial use only, the following terms apply - for all other
#  uses, please contact the author:
#
#    This code is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#


import rfidiot
import sys
import string
import os

try:
        card= rfidiot.card
except:
	print "Couldn't open reader!"
        os._exit(True)

card.info('formatmifare1k v0.1c')
card.select()
print 'Card ID: ' + card.data
while True:
	x= string.upper(raw_input('\n*** Warning! This will overwrite all data blocks! Proceed (y/n)? '))
	if x == 'N':
		os._exit(False)
	if x == 'Y':
		break

sector = 1
while sector < 0x10:
        for type in ['AA', 'BB', 'FF']:
                card.select()
		print ' sector %02x: Keytype: %s' % (sector, type),
                if card.login(sector,type,''):
			for block in range(3):
                		print '\n  block %02x: ' % ((sector * 4) + block),
				data= '00000000'
                        	print 'Value: ' + data,
				if card.writevalueblock((sector * 4) + block,data):
					print ' OK'
                		elif card.errorcode:
                        		print 'error code: ' + card.errorcode
		elif type == 'FF':
				print 'login failed'
               	print '\r',
                sys.stdout.flush()           
        sector += 1
	print
print

########NEW FILE########
__FILENAME__ = froschtest
#!/usr/bin/python

#  froschtest.py - test frosch HTRM112 reader`
# 
#  Adam Laurie <adam@algroup.co.uk>
#  http://rfidiot.org/
# 
#  This code is copyright (c) Adam Laurie, 2006, All rights reserved.
#  For non-commercial use only, the following terms apply - for all other
#  uses, please contact the author:
#
#    This code is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#

import rfidiot
import sys
import os

try:
        card= rfidiot.card
except:
	print "Couldn't open reader!"
        os._exit(True)

card.info('froschtest v0.1d')
print 
print 'Trying Hitag1: ',
if card.frosch(card.FR_HT1_Get_Snr,''):
	print card.data[:len(card.data) -2]
	if not card.select():
		print 'Select failed: ',
		print card.FROSCH_Errors[card.errorcode]
	else:
		for x in range(0,8):
			if card.readblock(x):
				print '\tBlock %02d: %s' % (x,card.data)
			else:
				print '\tBlock %0d read failed: ' % x,
				print card.FROSCH_Errors[card.errorcode]
else:
	print card.FROSCH_Errors[card.errorcode]

print 'Trying Hitag2: ',
if card.frosch(card.FR_HT2_Get_Snr_PWD,''):
	print card.data[:len(card.data) -2]
	if not card.select():
		print 'Select failed: ',
		print card.FROSCH_Errors[card.errorcode]
	else:
		for x in range(0,8):
			if card.readblock(x):
				print '\tBlock %02d: %s' % (x,card.data)
			else:
				print '\tBlock %0d read failed' % x,
				print card.FROSCH_Errors[card.errorcode]
else:
	print card.FROSCH_Errors[card.errorcode]

print 'Trying Hitag2 Public A (Unique / Miro): ',
if card.frosch(card.FR_HT2_Read_Miro,''):
	print card.data
else:
	print card.FROSCH_Errors[card.errorcode]

print 'Trying Hitag2 Public B (FDX-B): ',
if card.frosch(card.FR_HT2_Read_PublicB,''):
	print 'Raw: ' + card.data,
	print 'ID: ' + card.FDXBID128BitDecode(card.ToBinaryString(card.ToBinary(card.data)))
	card.FDXBIDPrint(card.FDXBID128BitDecode(card.ToBinaryString(card.ToBinary(card.data))))
else:
	print card.FROSCH_Errors[card.errorcode]
os._exit(False)

########NEW FILE########
__FILENAME__ = hidprox
#!/usr/bin/python


#  hidprox.py - show HID Prox card type and site/id code
# 
#  Adam Laurie <adam@algroup.co.uk>
#  http://rfidiot.org/
# 
#  This code is copyright (c) Adam Laurie, 2009, All rights reserved.
#  For non-commercial use only, the following terms apply - for all other
#  uses, please contact the author:
#
#    This code is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#


import sys
import os
import string
import rfidiot

try:
        card= rfidiot.card
except:
	print "Couldn't open reader!"
        os._exit(True)

card.info('hidprox v0.1f')

if not card.readersubtype == card.READER_OMNIKEY:
	print 'Reader type not supported!', card.ReaderSubType, card.READER_OMNIKEY
	os._exit(True)

try:
	card.select()
	prox= card.pcsc_atr[:6]
	type= card.HID_PROX_TYPES[prox]
	print '  Card type:', type
except:
	if not card.pcsc_atr:
		print 'No card detected!'
	else:
		print 'Unrecognised card type! ATR:', card.pcsc_atr
	os._exit(True)

# H10301 - 26 bit (FAC + CN)
if prox == card.HID_PROX_H10301:
	fc= card.pcsc_atr[7:10]
	cn= card.pcsc_atr[11:16]
	octal= '%o' % int(card.pcsc_atr[7:16])

# H10301 - 26 bit (FAC + CN) (ATR in HEX)
if prox == card.HID_PROX_H10301_H:
	binary= card.ToBinaryString(card.pcsc_atr[6:].decode('hex'))
	# strip leading zeros and parity
	binary= binary[7:]
	binary= binary[:-1]
	fc= int(binary[:8],2)
	cn= int(binary[8:],2)
	octal= '%o' % int(card.pcsc_atr[6:],16)

# H10302 - 37 bit (CN)
if prox == card.HID_PROX_H10302:
	fc= 'n/a'
	cn= card.pcsc_atr[6:18]
	octal= '%o' % int(card.pcsc_atr[6:18])

# H10302 - 37 bit (CN) (ATR in HEX)
if prox == card.HID_PROX_H10302_H:
	fc= 'n/a'
	binary= card.ToBinaryString(card.pcsc_atr[6:].decode('hex'))
	# strip leading zeros and parity
	binary= binary[8:]
	binary= binary[:-1]
	cn= int(binary,2)
	octal= '%o' % int(card.pcsc_atr[6:],16)

# H10304 - 37 bit (FAC + CN)
if prox == card.HID_PROX_H10304:
	fc= card.pcsc_atr[7:12]
	cn= card.pcsc_atr[12:18]
	octal= '%o' % int(card.pcsc_atr[7:18])

# H10320 - 32 bit clock/data card
if prox == card.HID_PROX_H10320:
	fc= 'n/a'
	cn= card.pcsc_atr[6:14]
	octal= '%o' % int(card.pcsc_atr[6:14])

# Corp 1000 - 35 bit (CIC + CN)	
if prox == card.HID_PROX_CORP1K:
	fc= card.pcsc_atr[6:10]
	cn= card.pcsc_atr[10:18]
	octal= '%o' % int(card.pcsc_atr[6:18])

print
print '    Facility Code:', fc
print '      Card Number:', cn
print '            Octal:', octal
print
os._exit(False)

########NEW FILE########
__FILENAME__ = hitag2brute
#!/usr/bin/python


#  hitag2brute.py - Brute Force hitag2 password
# 
#  Adam Laurie <adam@algroup.co.uk>
#  http://rfidiot.org/
# 
#  This code is copyright (c) Adam Laurie, 2008, All rights reserved.
#  For non-commercial use only, the following terms apply - for all other
#  uses, please contact the author:
#
#    This code is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#


import rfidiot
import sys
import os
import time

try:
        card= rfidiot.card
except:
	print "Couldn't open reader!"
        os._exit(True)

args= rfidiot.args

card.info('hitag2brute v0.1c')

pwd= 0x00

# start at specified PWD
if len(args) == 1:
	pwd= int(args[0],16)

card.settagtype(card.ALL)

if card.select():
	print 'Bruteforcing tag:', card.uid
else:
	print 'No tag found!'
	os._exit(True)

while 42:
	PWD= '%08X' % pwd
	if card.h2login(PWD):
		print 'Password is %s' % PWD
		os._exit(False)
	else:
		if not pwd % 16:
			print PWD + '                        \r',
	if not card.select():
		print 'No tag found! Last try: %s\r' % PWD,
	else:
		pwd= pwd + 1
	sys.stdout.flush()
	if pwd == 0xffffffff:
		os._exit(True)
os._exit(False)

########NEW FILE########
__FILENAME__ = hitag2reset
#!/usr/bin/python

#  hitag2reset.py - hitag2 tags need love too...
# 
#  Adam Laurie <adam@algroup.co.uk>
#  http://rfidiot.org/
# 
#  This code is copyright (c) Adam Laurie, 2006, All rights reserved.
#  For non-commercial use only, the following terms apply - for all other
#  uses, please contact the author:
#
#    This code is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#


import rfidiot
import sys
import os
import string

try:
        card= rfidiot.card
except:
	print "Couldn't open reader!"
        os._exit(True)

args= rfidiot.args
help= rfidiot.help

card.info('hitag2reset v0.1e')

# standard config block
#CFB='06' + card.HITAG2_TRANSPORT_TAG
CFB=card.HITAG2_PASSWORD + card.HITAG2_TRANSPORT_TAG
BLK1= card.HITAG2_TRANSPORT_RWD

if len(args) == 0 or len(args) > 2 or help:
	print sys.argv[0] + ' - return a Hitag2 tag to life'
	print 'Usage: ' + sys.argv[0] + ' <CONTROL> [<OLD PASSWD> <NEW PASSWD>]'
	print
	print 'If the optional PASSWD fields are specified, the password will be set,'
	print 'otherwise factory password \'%s\' will be used' % card.HITAG2_TRANSPORT_RWD
	os._exit(True)

if args[0] == 'CONTROL':
       	while True:
               	print
#		if card.frosch(card.FR_HT2_Read_PublicB):
#              		print '  Card ID: ' + card.data
               	x= string.upper(raw_input('  *** Warning! This will overwrite TAG! Place card and proceed (y/n)? '))
               	if x == 'N':
               		os._exit(False)
       		if x == 'Y':
			break
	print 'Writing...'
	logins= 0
	if (card.h2publicselect()):
		print 'Hitag2 ID: ' + card.data
	else:
		print 'No TAG, or incompatible hardware!'
		os._exit(True)
	if not card.writeblock(3,CFB):
		print card.FROSCH_Errors[card.errorcode]
		print 'Block 3 write failed!'
		os._exit(True)
	else:
		# set new passord if specified
		if len(args) > 1:
			BLK1= args[1]
		#if not card.writeblock(1,B1) or not card.writeblock(2,B2):
		if not card.writeblock(1,BLK1):
			print 'Block 1 write failed!'
			print card.FROSCH_Errors[card.errorcode]
			os._exit(True)	 	
	card.settagtype(card.ALL)
	print 'Done!'
       	if card.select():
       		print '  Card ID: ' + card.uid
os._exit(False)

########NEW FILE########
__FILENAME__ = isotype
#!/usr/bin/python


#  isotype.py - determine ISO tag type
# 
#  Adam Laurie <adam@algroup.co.uk>
#  http://rfidiot.org/
# 
#  This code is copyright (c) Adam Laurie, 2006, All rights reserved.
#  For non-commercial use only, the following terms apply - for all other
#  uses, please contact the author:
#
#    This code is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#


import sys
import os
import string
import rfidiot

try:
        card= rfidiot.card
except:
	print "Couldn't open reader!"
        os._exit(True)


card.info('isotype v0.1m')

typed= 0
if card.readertype == card.READER_ACG:
	for command, cardtype in card.ISOTags.iteritems():
		if not card.settagtype(command):
			print 'Could not test for card type: ' + cardtype
			continue
		if card.select():
			print '     ID: ' + card.uid
			print "       Tag is " + cardtype
			typed= True
			if command == card.ISO15693:
				print '         Manufacturer:',
				try:
					print card.ISO7816Manufacturer[card.uid[2:4]]
				except:
					print 'Unknown (%s)' % card.uid[2:4]

	for command, cardtype in card.ISOTagsA.iteritems():
		if not card.settagtype(command):
			print 'Could not reset reader to ' + cardtype + '!'
			os._exit(True)
if card.readertype == card.READER_PCSC:
	if card.select():
		print '     ID: ' + card.uid
		print "       Tag is " + card.tagtype
		if string.find(card.tagtype,"ISO 15693") >= 0:
			print '         Manufacturer:',
			try:
				print card.ISO7816Manufacturer[card.uid[2:4]]
			except:
				print 'Unknown (%s)' % card.uid[2:4]
		typed= True
		print
		print
		if not card.readersubtype == card.READER_ACS:
			card.PCSCPrintATR(card.pcsc_atr)
	else:
		print card.ISO7816ErrorCodes[card.errorcode]
		os._exit(True)
if card.readertype == card.READER_LIBNFC:
	if card.select('A'):
		print '     ID: ' + card.uid
		if card.atr:
			print '     ATS: ' + card.atr
		print "       Tag is ISO 14443A"
		typed= True
	if card.select('B'):
		print '   PUPI: ' + card.pupi
		print "       Tag is ISO 14443B"
		typed= True
if not typed:
	print "Could not determine type"
	os._exit(True)

os._exit(False)

########NEW FILE########
__FILENAME__ = jcopmifare
#!/usr/bin/python


#  jcopmifare.py - test program for mifare emulation on JCOP
#  
#  This program can be used to test READ/WRITE functionality of the built-in
#  mifare emulation on mifare enabled JCOP cards.
#  The mifare access applet jcop_mifare_access.cap must be loaded onto the card first.
# 
#  Adam Laurie <adam@algroup.co.uk>
#  http://rfidiot.org/
# 
#  This code is copyright (c) Adam Laurie, 2006, All rights reserved.
#  For non-commercial use only, the following terms apply - for all other
#  uses, please contact the author:
#
#    This code is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
# history
#	15/11/08 - ver 0.1a - first cut, seems to work. :)
#	13/01/09 - ver 0.1b - add RANDOM UID mode

import rfidiot
import sys
import os

try:
        card= rfidiot.card
except:
	print "Couldn't open reader!"
        os._exit(True)

args= rfidiot.args
Help= rfidiot.help

# fixed values required by JCOP applet
CLA= '00'
INS= 'MIFARE_ACCESS'
P1= '03'
WRITE= '01'
READ= '02'
RANDOM= '03'
MIFARE_AID= 'DC4420060606'

card.info('jcopmifare v0.1e')

if Help or len(args) < 2:
	print '\nUsage:\n\n\t%s [OPTIONS] <READ|WRITE|RANDOM> <MIFARE_PWD> [SECTOR] [HEX DATA]' % sys.argv[0]
	print
	print '\tMIFARE_PWD should be the HEX 8 BYTE MifarePWD produced by mifarekeys.py, or the'
	print '\tRANDOM_UID secret key.'
	print
	print '\tSECTOR number must be specified for READ and WRITE operations. Note that not all'
	print '\tsectors are WRITEable.'
	print
	print '\tRANDOM will set card into RANDOM_UID mode. All future selects will return a random'
	print '\tUID instead of the one stored in sector 0. This behaviour cannot be reversed.'
	print
	print '\tHEX DATA must be 16 BYTES worth of HEX for WRITE operations.' 
	print
	print '\t(default NXP transport keys are both FFFFFFFFFFFF, so MifarePWD is 0B54570745FE3AE7)'
	print '\t(sector 0 default is A0A1A2A3A4A5, so MifarePWD is 0FB3BBC7099ED432)'
	print
	print '\tExample:'
	print
	print '\t\t./jcopmifare.py WRITE 0B54570745FE3AE7 1 12345678123456781234567812345678'
	print
	print
	print '\tNote that jcop_mifare_access.cap or native Mifare emulation must be active on the card.'
	print
	os._exit(True)

def mifare_read(key,sector):
	cla= CLA
	ins= INS
	p1= P1
	p2= READ
	data= key + '%02X' % int(sector)
	lc= '%02X' % (len(data) / 2)
	le= '10'

	if card.send_apdu('','','','',cla,ins,p1,p2,lc,data,le):
		return True, card.data
	return False, card.errorcode

def mifare_write(key,sector,sectordata):
	cla= CLA
	ins= INS
	p1= P1
	p2= WRITE
	data= key + sectordata + '%02X' % int(sector)
	lc= '%02X' % (len(data) / 2)
	
	if card.send_apdu('','','','',cla,ins,p1,p2,lc,data,''):
		return True, card.data
	return False, card.errorcode

def mifare_random(key):
	cla= CLA
	ins= INS
	p1= P1
	p2= RANDOM
	data= key
	lc= '%02X' % (len(data) / 2)
	
	if card.send_apdu('','','','',cla,ins,p1,p2,lc,data,''):
		return True, card.data
	return False, card.errorcode

def select_mifare_app():
        "select mifare application (AID: DC4420060606)"
        ins= 'SELECT_FILE'
        p1= '04'
        p2= '0C'
        data= MIFARE_AID
	lc= '%02X' % (len(data) / 2)
        card.send_apdu('','','','','',ins,p1,p2,lc,data,'')
        if card.errorcode == card.ISO_OK:
                return True
        else:
                return False

def error_exit(message,error):
	print '  %s, error number: %s' % (message,error),
	try:
		print card.ISO7816ErrorCodes[error]
	except:
		print
	os._exit(True)

if card.select():
	print '    Card ID: ' + card.uid
	if card.readertype == card.READER_PCSC:
		print '    ATR: ' + card.pcsc_atr
else:
	print '    No card present'

# high speed select required for ACG
if not card.hsselect('08'):
        print '    Could not select card for APDU processing'
        os._exit(True)

if not select_mifare_app():
	print '  Could not select mifare applet!'
	os._exit(True)

if args[0] == 'READ':
	stat, data= mifare_read(args[1],args[2])
	if not stat:
		error_exit('Read failed', data)
	else:
		print 'Data: ', data
		os._exit(False)

if args[0] == 'WRITE':
	stat, data= mifare_write(args[1],args[2],args[3])
	if not stat:
		error_exit('Write failed', data)
	else:
		print 'Write completed'
		os._exit(False)

if args[0] == 'RANDOM':
	stat, data= mifare_random(args[1])
	if not stat:
		error_exit('Random_UID mode failed', data)
	else:
		print 'Random_UID set'
		os._exit(False)



print "Unrecognised command:", args[0]
os._exit(True)

########NEW FILE########
__FILENAME__ = jcopsetatrhist
#!/usr/bin/python


#  jcopsetatrhist.py - set ATR History bytes on JCOP cards
#  
#  The applet jcop_set_atr_hist.cap must be loaded onto the card first,
#  and it must be installed as "default selectable" (priv mode 0x04).
# 
#  Adam Laurie <adam@algroup.co.uk>
#  http://rfidiot.org/
# 
#  This code is copyright (c) Adam Laurie, 2008, All rights reserved.
#  For non-commercial use only, the following terms apply - for all other
#  uses, please contact the author:
#
#    This code is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#

import rfidiot
import sys
import os
import string

try:
        card= rfidiot.card
except:
        os._exit(True)

args= rfidiot.args
Help= rfidiot.help

# fixed values required by JCOP applet
CLA= '80'
P1= '00'
P2= '00'
JCOP_ATR_AID= 'DC4420060607'

if Help or len(args) < 2:
	print '\nUsage:\n\n\t%s [OPTIONS] \'SET\' <HEX DATA>' % sys.argv[0]
	print
	print '\tHEX DATA is up to 15 BYTES of ASCII HEX.' 
	print
	print '\tExample:'
	print
	print '\t./jcopsetatrhist.py SET 0064041101013180009000'
	print
	os._exit(True)

def jcop_set_atr_hist(bytes):
	cla= CLA
	ins= 'ATR_HIST'
	p1= P1
	p2= P2
	data= '%02X' % (len(bytes) / 2) + bytes
	lc= '%02X' % (len(data) / 2)
	if card.send_apdu('','','','',cla,ins,p1,p2,lc,data,''):
		return True, card.data
	return False, card.errorcode

def select_atrhist_app():
        "select atr_hist application (AID: DC4420060607)"
        ins= 'SELECT_FILE'
        p1= '04'
        p2= '0C'
        data= JCOP_ATR_AID
	lc= '%02X' % (len(data) / 2)
        card.send_apdu('','','','','',ins,p1,p2,lc,data,'')
        if card.errorcode == card.ISO_OK:
                return True
        else:
                return False

def error_exit(message,error):
	print '  %s, error number: %s' % (message,error),
	try:
		print card.ISO7816ErrorCodes[error]
	except:
		print
	os._exit(True)

card.info('jcopsetatrhist v0.1c')

if card.select():
	print '    Card ID: ' + card.uid
	if card.readertype == card.READER_PCSC:
		print '    ATR: ' + card.pcsc_atr
else:
	print '    No card present'
	os._exit(True)

# high speed select required for ACG
if not card.hsselect('08'):
        print '    Could not select card for APDU processing'
        os._exit(True)

if not select_atrhist_app():
	print
	print "  Can't select atrhist applet!"
	print '  Please load jcop_set_atr_hist.cap onto JCOP card.'
	print '  (Use command: gpshell java/jcop_set_atr_hist.gpsh)'
	print
	os._exit(True)
		
if args[0] == 'SET':
	stat, data= jcop_set_atr_hist(args[1])
	if not stat:
		error_exit('Set hist bytes failed', data)
	else:
		print
		print '  ATR History Bytes (ATS) set to', args[1]
		print 
		print '  *** Remove card from reader and replace to finalise!'
		print
		print '  You can now delete jcop_set_atr_hist.cap from the JCOP card.'
		print '  (Use command: gpshell java/jcop_delete_atr_hist.gpsh)'
		print
		os._exit(False)
else:
	print "Unrecognised command:", args[0]
	os._exit(True)

########NEW FILE########
__FILENAME__ = jcoptool
#!/usr/bin/python


#  jcoptool.py - JCOP card toolkit
#  
#  Adam Laurie <adam@algroup.co.uk>
#  http://rfidiot.org/
# 
#  This code is copyright (c) Adam Laurie, 2009, All rights reserved.
#  For non-commercial use only, the following terms apply - for all other
#  uses, please contact the author:
#
#    This code is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#

import rfidiot
import sys
import os
import string
from Crypto.Cipher import DES3
from Crypto.Cipher import DES
from pyasn1.codec.ber import decoder

try:
        card= rfidiot.card
except:
	print "Couldn't open reader!"
        os._exit(True)

args= rfidiot.args
Help= rfidiot.help

# fixed values required by JCOP applet
CLA= '80'
P1= '00'
P2= '00'

templates=	{
	   	'66':'Card Data',
	   	'73':'Card Recognition Data',
	   	}

tags=	{
	'06':'OID',
	'60':'Application tag 0 - Card Management Type and Version',
	'63':'Application tag 3 - Card Identification Scheme',
	'64':'Application tag 4 - Secure Channel Protocol of the Issuer Security Domain and its implementation options',
	'65':'Application tag 5 - Card configuration details',
	'66':'Application tag 6 - Card / chip details',
	'67':'Application tag 7 - Issuer Security Domain\'s Trust Point certificate information',
	'68':'Application tag 8 - Issuer Security Domain certificate information',
	}

registry_tags= 	{
		'4F':'AID',
		'9F70':'Life Cycle State',
		'C5':'Privileges',
		'C4':'Application\'s Executable Load File AID',
		'CE':'Executable Lod File Version Number',
		'84':'First or only ExecutableModule AID',
		'CC':'Associated Security Domain\'s AID',
		}

card_status=	{
		'80':'Issuer Security Domain',
		'40':'Applications and Supplementary Security Domains',
		'20':'Executable Load Files',
		'10':'Executable Load Files and their Executable Modules',
		}

# life cycle state must be masked as bits 4-7 (bit numbering starting at 1) are application specific
application_life_cycle_states= 	{
				'01':'LOADED',
				'03':'INSTALLED',
				'07':'SELECTABLE',
				'83':'LOCKED',
				'87':'LOCKED',
				}

executable_life_cycle_states= 	{
				'01':'LOADED',
				}

security_domain_life_cycle_states= 	{
					'03':'INSTALLED',
					'07':'SELECTABLE',
					'0F':'PERSONALIZED',
					'83':'LOCKED',
					'87':'LOCKED',
					'8B':'LOCKED',
					'8F':'LOCKED',
					}
					

card_life_cycle_states=	{
			'01':'OP_READY',
			'07':'INITIALIZED',
			'0F':'SECURED',
			'7F':'CARD_LOCKED',
			'FF':'TERMINATED',
			}

targets= 	{
		'00':'Unknown',
		'01':'SmartMX',
		'03':'sm412',
		}

fuse_state=	{
		'00':'Not Fused',
		'01':'Fused',
		}

manufacturers= 	{
		'PH':'Philips Semiconductors',
		'NX':'NXP',
		}

privilege_byte_1=	{
			'80':'Security Domain',
			'C0':'DAP Verification',
			'A0':'Delegated Management',
			'10':'Card Lock',
			'08':'Card Terminate',
			'04':'Card Reset',
			'02':'CVM Management',
			'C1':'Mandated DAP Verification',
			}

def decode_jcop_identify(data, padding):
	fabkey= data[0:2]
	patch_id= data[2:4]
	target= data[4:6]
	mask_id= data[6:8]
	custom_mask= data[8:16]
	mask_name= data[16:28]
	fuse= data[28:30]
	rom_info= data[30:42]

	manufacturer= card.ToBinary(mask_name[0:4])
	manufacture_year= card.ToBinary(mask_name[4:6])
	manufacture_week= card.ToBinary(mask_name[6:10])
	manufacture_mask= ord(card.ToBinary(mask_name[10:12])) - 64
	

	print padding + 'FABKEY ID:       %s' % fabkey
	print padding + 'PATCH ID:        %s' % patch_id
	print padding + 'TARGET ID:       %s' % target + ' (' + targets[target] + ')'
	print padding + 'MASK ID:         %s' % mask_id + ' (Mask %s)' % int(mask_id,16)
	print padding + 'CUSTOM MASK:     %s' % custom_mask + ' (%s)' % card.ReadablePrint(card.ToBinary(custom_mask))
	print padding + 'MASK NAME:       %s' % card.ToBinary(mask_name)
	print padding + 'FUSE STATE:      %s' % fuse + ' (' + fuse_state[fuse] + ')'
	print padding + 'ROM INFO:        %s' % rom_info + ' (Checksum)'
	print padding + 'COMBO NAME:      %s-m%s.%s.%s-%s' % (targets[target], mask_id, fabkey, patch_id, card.ToBinary(mask_name))
	print padding + 'MANUFACTURER:    %s' % manufacturers[manufacturer]
	print padding + 'PRODUCED:        Year %s, Week %s, Build %d' % (manufacture_year, manufacture_week, manufacture_mask)

def decode_jcop_lifecycle(data, padding):
	ic_fab= data[0:4]
	ic_type= data[4:8]
	os_id= data[8:12]
	os_release_date= data[12:16]
	os_release_level= data[16:20]
	ic_fab_date= data[20:24]
	ic_serial= data[24:32]
	ic_batch= data[32:36]
	ic_mod_fab= data[36:40]
	ic_mod_pack_date= data[40:44]
	icc_man= data[44:48]
	ic_embed_date= data[48:52]
	ic_pre_perso= data[52:56]
	ic_pre_perso_date= data[56:60]
	ic_pre_perso_equip= data[60:68]
	ic_perso= data[68:72]
	ic_perso_date= data[72:76]
	ic_perso_equip= data[76:84]
	
	print
	print padding + 'IC Fabricator                       %s' % ic_fab
	print padding + 'IC Type                             %s' % ic_type
	print padding + 'OS ID                               %s' % os_id
	print padding + 'OS Release Date                     %s' % os_release_date
	print padding + 'OS Release Level                    %s' % os_release_level
	print padding + 'IC Fabrication Date                 Year %s Day %s' % (ic_fab_date[0], ic_fab_date[1:4])
	print padding + 'IC Serial Number                    %s' % ic_serial
	print padding + 'IC Batch Number                     %s' % ic_batch
	print padding + 'IC Module Fabricator                %s' % ic_mod_fab
	print padding + 'IC Module Packaging Date            Year %s Day %s' % (ic_mod_pack_date[0], ic_mod_pack_date[1:4])
	print padding + 'ICC Manufacturer                    %s' % icc_man
	print padding + 'IC Embedding Date                   Year %s Day %s' % (ic_embed_date[0], ic_embed_date[1:4])
	print padding + 'IC Pre-Personalizer                 %s' % ic_pre_perso
	print padding + 'IC Pre-Personalization Date         %s' % ic_pre_perso_date
	print padding + 'IC Pre-Personalization Equipment    %s' % ic_pre_perso_equip
	print padding + 'IC Personalizer                     %s' % ic_perso
	print padding + 'IC Personalization Date             Year %s Day %s' % (ic_perso_date[0], ic_perso_date[1:4])
	print padding + 'IC Personalization Equipment        %s' % ic_perso_equip

def decode_privileges(data):
	print '(',
	multiple= False
	try:
		for mask in privilege_byte_1.keys():
			if (int(data[0:2],16) & int(mask,16)) == int(mask,16):
				if multiple:
					print '/',
				print privilege_byte_1[mask],
				multiple= True
	except:
		print ')',
		return
	print ')',

# check privilege byte 0 to see if we're a security domain
def check_security_domain(data):
	length= int(data[2:4],16) * 2
	i= 4
	while i < length + 4:
		for item in registry_tags.keys():
			if data[i:i+len(item)] == item:
				itemlength= int(data[i+len(item):i+len(item)+2],16) * 2
				if item == card.GP_REG_PRIV:
					itemdata= data[i+len(item)+2:i+len(item)+2+itemlength]
					if (int(itemdata[0:2],16) & 0x80) == 0x80:
						return True
				i += itemlength + len(item) + 2
	return False

def decode_gp_registry_data(data, padding, filter):
	if not data[0:2] == card.GP_REG_DATA:
		return False, ''
	states= application_life_cycle_states
	if filter == card.GP_FILTER_ISD:
		states= card_life_cycle_states
	if filter == card.GP_FILTER_ASSD:
		states= application_life_cycle_states					
	if filter == card.GP_FILTER_ELF:
		states= executable_life_cycle_states
	# check if this is a security domain (not set up right, so disabled!)
	#if check_security_domain(data):
	#	states= security_domain_life_cycle_states
	length= int(data[2:4],16) * 2
	i= 4
	while i < length + 4:
		decoded= False
		for item in registry_tags.keys():
			if data[i:i+len(item)] == item:
				if not item == card.GP_REG_AID:
					print ' ',
				itemlength= int(data[i+len(item):i+len(item)+2],16) * 2
				itemdata= data[i+len(item)+2:i+len(item)+2+itemlength]
				print padding, registry_tags[item]+':', itemdata,
				if item == card.GP_REG_LCS:
					if filter == card.GP_FILTER_ASSD:
						# mask out application specific bits
						itemdata= '%02x' % (int(itemdata,16) & 0x87)
					print '( '+states[itemdata]+' )',
				if item == card.GP_REG_PRIV:
					decode_privileges(itemdata)
				decoded=  True
				i += itemlength + len(item) + 2
				print
		if not decoded:
			return False
	return True
	
card.info('jcoptool v0.1d')
if Help or len(args) < 1:
	print '\nUsage:\n\n\t%s [OPTIONS] <COMMAND> [ARGS] [ENC Key] [MAC Key] [KEK Key]' % sys.argv[0]
	print
	print '\tWhere COMMAND/ARGS are one of the following combinations:'
	print
	print "\tINFO\t\t\tDisplay useful info about the JCOP card and it's contents."
	print
	print '\tDES keys ENC MAC and KEK are always the final 3 arguments, and should be in HEX.'
	print '\tIf not specified, the default \'404142434445464748494A4B4C4D4E4F\' will be used.'
	print
	os._exit(True)

command= args[0]

if card.select():
	print
	print '    Card ID: ' + card.uid
	if card.readertype == card.READER_PCSC:
		print '    ATS: %s (%s)' % (card.pcsc_ats,card.ReadablePrint(card.ToBinary(card.pcsc_ats)))
else:
	print '    No RFID card present'
	print
	#os._exit(True)

#print '    ATR: ' + card.pcsc_atr
#print

# high speed select required for ACG
if not card.hsselect('08'):
	print '    Could not select RFID card for APDU processing'
	#os._exit(True)

print
print '    JCOP Identity Data:',
# send pseudo file select command for JCOP IDENTIFY
card.iso_7816_select_file(card.AID_JCOP_IDENTIFY,'04','00')
if card.errorcode == '6A82' and len(card.data) > 0:
	print card.data
	print
	decode_jcop_identify(card.data,'      ')
else:
	print '      Device does not support JCOP IDENTIFY!'

# card life cycle data
# high speed select required for ACG
if not card.hsselect('08'):
	print '    Could not select RFID card for APDU processing'
print
print '    Life Cycle data:',
if not card.gp_get_data('9F7F'):
	print " Failed - ", card.ISO7816ErrorCodes[card.errorcode]
else:
	print card.data
	if card.data[0:4] == '9F7F':
		decode_jcop_lifecycle(card.data[6:],'      ')

# select JCOP Card Manager
# high speed select required for ACG
if not card.hsselect('08'):
	print '    Could not select RFID card for APDU processing'
if not card.iso_7816_select_file(card.AID_CARD_MANAGER,'04','00'):
	print
	print "  Can't select Card Manager!",
	card.iso_7816_fail(card.errorcode)

if command == 'INFO':
	# high speed select required for ACG
	if not card.hsselect('08'):
		print '    Could not select RFID card for APDU processing'
	# get Card Recognition Data
	if not card.gp_get_data('0066'):
		print
		print "  Can't get Card Recognition Data!",
		card.iso_7816_fail(card.errorcode)
	pointer= 0
	item= card.data[pointer:pointer+2]
	if item != '66':
		print 'Unrecognised template:', item
		os._exit(True)
	pointer += 2
	item= card.data[pointer:pointer+2]
	length= int(item,16)

	print
	print '    Card Data length:',length
	pointer += 2
	item= card.data[pointer:pointer+2]
	if item != '73':
		print 'Unrecognised template:', item
		os._exit(True)
	pointer += 2
	item= card.data[pointer:pointer+2]
	length= int(item,16)
	print '      Card Recognition Data length:',length
	pointer += 2
	while pointer < len(card.data):
		item= card.data[pointer:pointer+2]
		try:
			print '        '+tags[item]+':',
			pointer += 2
			length= int(card.data[pointer:pointer + 2],16)
			pointer += 2
			if tags[item] == 'OID':
				decodedOID, dummy= decoder.decode(card.ToBinary(item+('%02x' % length)+card.data[pointer:pointer + length * 2]))
				print decodedOID.prettyPrint()
			else:
				if(card.data[pointer:pointer + 2]) == '06':
					decodedOID, dummy= decoder.decode(card.ToBinary(card.data[pointer:pointer + length * 2]))
					print
					print '          OID:', decodedOID.prettyPrint()
				else:
					print card.data[pointer:pointer + length * 2]
			pointer += length * 2
		except:
			print 'Unrecognised tag', item
			os._exit(True)
	# set up DES keys for encryption operations
	if len(args) > 1:
		enc_key= args[1]
		if len(args) > 2:
			mac_key= args[2]
	else:
		enc_key= card.GP_ENC_KEY
		mac_key= card.GP_MAC_KEY

if command == 'INSTALL':
	if len(args) > 2:
		enc_key= args[2]
		if len(args) > 3:
			mac_key= args[3]
	else:
		enc_key= card.GP_ENC_KEY
		mac_key= card.GP_MAC_KEY

if command == 'INFO' or command == 'INSTALL':
	# authenticate to card
	# initialise secure channel
	print
	print '      *** Warning'
	print '      *** Repeated authentication failures may permanently disable device'
	print
	x= string.upper(raw_input('      Attempt to authenticate (y/n)? '))
	if not x == 'Y':
		os._exit(True)

	# high speed select required for ACG
	if not card.hsselect('08'):
		print '    Could not select RFID card for APDU processing'
	host_challenge= card.GetRandom(8)
	if not card.gp_initialize_update(host_challenge):
		print 'Can\'t Initialise Update!'
		card.iso_7816_fail(card.errorcode)	
	card_key_diversification, card_key_info, card_sc_sequence_counter,card_challenge,card_cryptogram= card.gp_initialize_update_response_scp02(card.data)


	secure_channel_protocol= card_key_info[2:4]

	if secure_channel_protocol == card.GP_SCP02:
		# create ENC session key by encrypting derivation data with ENC key
		session_pad= '000000000000000000000000'
		derivation_data= '0182' + card_sc_sequence_counter + session_pad
		# create encryption object with ENC key
		e_enc= DES3.new(card.ToBinary(enc_key),DES3.MODE_CBC,card.DES_IV)
		enc_s_key= e_enc.encrypt(card.ToBinary(derivation_data))
		# data for cryptograms
		card_cryptogram_source= host_challenge + card_sc_sequence_counter + card_challenge
		host_cryptogram_source= card_sc_sequence_counter + card_challenge + host_challenge
		# check card cryptogram 
		check_cryptogram= string.upper(card.ToHex(card.DES3MAC(card.ToBinary(card_cryptogram_source), enc_s_key, '')))
		if not check_cryptogram == card_cryptogram:
			print 'Key mismatch!'
			print 'Card Cryptogram:      ', card_cryptogram
			print 'Calculated Cryptogram:', check_cryptogram
			os._exit(True)

		# cryptogram checks out, so we can use session key
		# create encryption object with ENC Session key
		s_enc= DES3.new(enc_s_key,DES3.MODE_CBC,card.DES_IV)

		# authenticate to card
		host_cryptogram= card.DES3MAC(card.ToBinary(host_cryptogram_source), enc_s_key, '')
		# create encryption object with MAC key
		e_enc= DES3.new(card.ToBinary(mac_key),DES3.MODE_CBC,card.DES_IV)
		# create C-MAC session key
		derivation_data= '0101' + card_sc_sequence_counter + session_pad
		cmac_s_key= e_enc.encrypt(card.ToBinary(derivation_data))
		if not card.gp_external_authenticate(host_cryptogram,cmac_s_key):
			print 'Card Authentication failed!'
			card.iso_7816_fail(card.errorcode)	
	else:
		print 'Unsupported Secure Channel Protocol:', secure_channel_protocol
		os._exit(True)


print '      Authentication succeeded'	
# get card status (list card contents)
# high speed select required for ACG
#if not card.hsselect('08'):
#		print '    Could not select RFID card for APDU processing'
print
print '    Card contents:'
for filter in '80','40','20','10':
	if not card.gp_get_status(filter,'02',''):
		if not card.errorcode == '6A88':
			print
			print "  Can't get Card Status!",
			card.iso_7816_fail(card.errorcode)
	print
	print '     ', card_status[filter]+':'
	if card.errorcode == '6A88':
		print '        None!'
	else:
		if not decode_gp_registry_data(card.data,'       ',filter):
			print '  Can\'t decode Registry!'
			print card.data
			os._exit(True)
os._exit(False)

########NEW FILE########
__FILENAME__ = lfxtype
#!/usr/bin/python


#  lfxtype.py - select card and display tag type
# 
#  Adam Laurie <adam@algroup.co.uk>
#  http://rfidiot.org/
# 
#  This code is copyright (c) Adam Laurie, 2006, All rights reserved.
#  For non-commercial use only, the following terms apply - for all other
#  uses, please contact the author:
#
#    This code is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#


import rfidiot
import sys
import os

try:
        card= rfidiot.card
except:
	print "Couldn't open reader!"
        os._exit(True)


card.info('lfxtype v0.1j')
card.select()
ID= card.uid
if ID:
	print 'Card ID: ' + ID
	print 'Tag type: ' + card.LFXTags[card.tagtype]
	if card.tagtype == card.EM4x02:
		print '  Unique ID: ' + card.EMToUnique(ID)
		card.settagtype(card.Q5)
		card.select()
		if card.uid:
			print '  *** This is a Q5 tag in EM4x02 emulation mode ***'
	os._exit(False)
else:
	print 'No TAG present!'
	os._exit(True)

########NEW FILE########
__FILENAME__ = loginall
#!/usr/bin/python

#  loginall.py - attempt to login to each sector with transport keys
# 
#  Adam Laurie <adam@algroup.co.uk>
#  http://rfidiot.org/
# 
#  This code is copyright (c) Adam Laurie, 2006, All rights reserved.
#  For non-commercial use only, the following terms apply - for all other
#  uses, please contact the author:
#
#    This code is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#


import rfidiot

try:
        card= rfidiot.card
except:
	print "Couldn't open reader!"
        os._exit(True)

card.info('loginall v0.1h')

card.select()
print '\ncard id: ' + card.uid

block = 0

while block < 16:
	for X in [ 'AA', 'BB', 'FF' ]:
		card.select()
		print '%02x %s: ' % (block, X),
		if card.login(block, X, ''):
			print "success!"
		elif card.errorcode:
			print "error: " + card.errorcode
		else:
			print "failed"
	block += 1
os._exit(False)

########NEW FILE########
__FILENAME__ = mifarekeys
#!/usr/bin/python


#  mifarekeys.py - calculate 3DES key for Mifare access on JCOP cards
#  as per Philips Application Note AN02105
#  http://www.nxp.com/acrobat_download/other/identification/067512.pdf
# 
#  Adam Laurie <adam@algroup.co.uk>
#  http://rfidiot.org/
# 
#  This code is copyright (c) Adam Laurie, 2008, All rights reserved.
#  For non-commercial use only, the following terms apply - for all other
#  uses, please contact the author:
#
#    This code is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
# 22/07/08 - version 1.0 - Mifare to 3DES key mapping working, but not final MifarePWD
# 23/07/08 - version 1.1 - Fix 3DES ciphering FTW!
# 24/07/08 - version 1.2 - Add some usage text

import sys
from Crypto.Cipher import DES3
from Crypto.Cipher import DES

def HexArray(data):
	# first check array is all hex digits
	try:
		int(data,16)
	except:
		return False, []
	# check array is 4 hex digit pairs
	if len(data) != 12:
		return False, []
	# now break into array of hex pairs
	out= []
	for x in range(0,len(data),2):
		out.append(data[x:x+2])
	return True, out

### main ###
print('mifarekeys v0.1b')

if len(sys.argv) != 3:
	print
	print "Usage:"
	print "\t%s <KeyA> <KeyB>" % sys.argv[0]
	print
	print "\tCreate MifarePWD for access to Mifare protected memory on Dual Interface IC"
	print "\t(JCOP) cards. Output is DKeyA, DKeyB and MifarePWD. DKeyA and DKeyB are used as"
	print "\tthe DES3 keys to generate MifarePWD with an IV of (binary) '00000000', a"
	print "\tChallenge of (also binary) '00000000', and a key of DKeyA+DKeyB+DKeyA."
	print
	print "\tExample:"
	print
	print "\tUsing KeyA of A0A1A2A3A4A5 and KeyB of B0B1B2B3B4B5 should give the result:"
	print
	print "\t\tDKeyA:        40424446484A7E00"
	print "\t\tDKeyB:        007E60626466686A"
	print
  	print "\t\tMifarePWD:    8C7F46D76CE01266"
	print
	sys.exit(True)

# break keyA and keyB into 2 digit hex arrays
ret, keyA= HexArray(sys.argv[1])
if not ret:
	print "Invalid HEX string:", sys.argv[1]
	sys.exit(True)
ret, keyB= HexArray(sys.argv[2])
if not ret:
	print "Invalid HEX string:", sys.argv[2]
	sys.exit(True)

# now expand 48 bit Mifare keys to 64 bits for DES by adding 2 bytes
# one is all zeros and the other is derived from the 48 Mifare key bits

### KeyA ###
# first left shift 1 to create a 0 trailing bit (masked to keep it a single byte)
newkeyA= ''
for n in range(6):
	newkeyA += "%02X" % ((int(keyA[n],16) << 1) & 0xff)
# now create byte 6 from bit 7 of original bytes 0-5, shifted to the correct bit position
newkeyAbyte6= 0x00
for n in range(6):
	newkeyAbyte6 |= ((int(keyA[n],16) >> n + 1) & pow(2,7 - (n + 1)))
newkeyA += "%02X" % newkeyAbyte6
# and finally add a 0x00 to the end
newkeyA += '00'
print
print "  DKeyA:       ", newkeyA

### KeyB ###
# now do keyB, which is basically the same but starting at byte 2 and prepending new bytes
newkeyB= '00'
# now create byte 1 from bit 7 of original bytes 0-5, shifted to the correct bit position, which is
# the reverse of byte6 in KeyA
newkeyBbyte1= 0x00
for n in range(6):
	newkeyBbyte1 |= ((int(keyB[n],16) >> 7 - (n + 1)) & pow(2,n + 1))
newkeyB += "%02X" % newkeyBbyte1
# left shift 1 to create a 0 trailing bit (masked to keep it a single byte)
for n in range(6):
	newkeyB += "%02X" % ((int(keyB[n],16) << 1) & 0xff)
print "  DKeyB:       ", newkeyB

# now create triple-DES key
deskeyABA= ''
# build key MSB first
for n in range(len(newkeyA+newkeyB+newkeyA)-2,-2,-2):
	deskeyABA += chr(int((newkeyA+newkeyB+newkeyA)[n:n + 2],16))
des3= DES3.new(deskeyABA,DES.MODE_CBC,'\0\0\0\0\0\0\0\0')
mifarePWD= des3.encrypt('\0\0\0\0\0\0\0\0')
# reverse LSB/MSB for final output
mifarePWDout= ''
for n in range(len(mifarePWD)-1,-1,-1):
	mifarePWDout += "%02X" % int(ord(mifarePWD[n]))
print
print "  MifarePWD:   ", mifarePWDout
print

########NEW FILE########
__FILENAME__ = mrpkey
#!/usr/bin/python


#  mrpkey.py - calculate 3DES key for Machine Readable Passport
# 
#  Adam Laurie <adam@algroup.co.uk>
#  http://rfidiot.org/
# 
#  This code is copyright (c) Adam Laurie, 2006, 2007, All rights reserved.
#  For non-commercial use only, the following terms apply - for all other
#  uses, please contact the author:
#
#    This code is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#

STRIP_INDEX=True
DEBUG= False
Filetype= ''
DocumentType= '?'
Fields= ()
FieldNames= ()
FieldLengths= ()
FieldKeys= ()

# this needs fixing - MAX should be able to go up to size supported by device
MAXCHUNK= 118

import rfidiot
import sys
import os
import commands
from Crypto.Hash import SHA
from Crypto.Cipher import DES3
from Crypto.Cipher import DES
import string
from operator import *
import StringIO
from Tkinter import *
import PIL.Image as Image
import PIL.ImageTk as ImageTk

# Machine Readable Document types
DOC_UNDEF= {
	   '?':'Undefined',
	   }

DOC_ID= {
	'I<':'ID Card',
	'IR':'ID Card',
	}

DOC_PASS=  {
	   'P<':'Passport',
	   'PM':'Passport',
	   'PA':'Passport',
	   'PV':'Passport',
	   }

DOCUMENT_TYPE= {}

# TEST data
TEST_MRZ= 'L898902C<3UTO6908061F9406236ZE184226B<<<<<14'
TEST_rnd_ifd= '781723860C06C226'
TEST_rnd_icc= '4608F91988702212'
TEST_Kifd= '0B795240CB7049B01C19B33E32804F0B'
TEST_respdata= '46B9342A41396CD7386BF5803104D7CEDC122B9132139BAF2EEDC94EE178534F2F2D235D074D7449'
MRZ_WEIGHT= [7,3,1]
APDU_OK= '9000'
APDU_BAC= '6982'

# Data Groups and Elements
EF_COM= '60'
EF_DG1= '61'
EF_DG2= '75'
EF_DG3= '63'
EF_DG4= '76'
EF_DG5= '65'
EF_DG6= '66'
EF_DG7= '67'
EF_DG8= '68'
EF_DG9= '69'
EF_DG10= '6a'
EF_DG11= '6b'
EF_DG12= '6c'
EF_DG13= '6d'
EF_DG14= '6e'
EF_DG15= '6f'
EF_DG16= '70'
EF_SOD= '77'
EF_TAGS= '5c'

# Data Group Names
TAG_NAME= {EF_COM:'EF.COM Data Group Presence Map',\
	   EF_DG1:'EF.DG1 Data Recorded in MRZ',\
	   EF_DG2:'EF.DG2 Encoded Identification Features - FACE',\
	   EF_DG3:'EF.DG3 Encoded Identification Features - FINGER(s)',\
	   EF_DG4:'EF.DG4 Encoded Identification Features - IRIS(s)',\
	   EF_DG5:'EF.DG5 Displayed Identification Feature(s) - PORTRAIT',\
	   EF_DG6:'EF.DG6 Reserved for future use',\
	   EF_DG7:'EF.DG7 Displayed Identification Features - SIGNATURE or USUAL MARK',\
	   EF_DG8:'EF.DG8 Encoded Security Features - DATA FEATURE(s)',\
	   EF_DG9:'EF.DG9 Encoded Security Features - STRUCTURE FEATURE(s)',\
	   EF_DG10:'EF.DG10 Encoded Security Features - SUBSTANCE FEATURE(s)',\
	   EF_DG11:'EF.DG11 Additional Personal Detail(s)',\
	   EF_DG12:'EF.DG12 Additional Document Detail(s)',\
	   EF_DG13:'EF.DG13 Optional Detail(s)',\
	   EF_DG14:'EF.DG14 Reserved for Future Use',\
	   EF_DG15:'EF.DG15 Active Authentication Public Key Info',\
	   EF_DG16:'EF.DG16 Person(s) to Notify',\
	   EF_SOD:'EF.SOD Document Security Object',\
	   EF_TAGS:'Tag List'}

# Data Group Passport Application Long FID
TAG_FID=  {EF_COM:'011E',\
	   EF_DG1:'0101',\
	   EF_DG2:'0102',\
	   EF_DG3:'0103',\
	   EF_DG4:'0104',\
	   EF_DG5:'0105',\
	   EF_DG6:'0106',\
	   EF_DG7:'0107',\
	   EF_DG8:'0108',\
	   EF_DG9:'0109',\
	   EF_DG10:'010A',\
	   EF_DG11:'010B',\
	   EF_DG12:'010C',\
	   EF_DG13:'010D',\
	   EF_DG14:'010E',\
	   EF_DG15:'010F',\
	   EF_DG16:'0110',\
	   EF_SOD:'011D'}

# Filesystem paths
tempfiles= '/tmp/'
filespath= ''

# Data Group filenames for local storage
TAG_FILE= {EF_COM:'EF_COM.BIN',\
	   EF_DG1:'EF_DG1.BIN',\
	   EF_DG2:'EF_DG2.BIN',\
	   EF_DG3:'EF_DG3.BIN',\
	   EF_DG4:'EF_DG4.BIN',\
	   EF_DG5:'EF_DG5.BIN',\
	   EF_DG6:'EF_DG6.BIN',\
	   EF_DG7:'EF_DG7.BIN',\
	   EF_DG8:'EF_DG8.BIN',\
	   EF_DG9:'EF_DG9.BIN',\
	   EF_DG10:'EF_DG10.BIN',\
	   EF_DG11:'EF_DG11.BIN',\
	   EF_DG12:'EF_DG12.BIN',\
	   EF_DG13:'EF_DG13.BIN',\
	   EF_DG14:'EF_DG14.BIN',\
	   EF_DG15:'EF_DG15.BIN',\
	   EF_DG16:'EF_DG16.BIN',\
	   EF_SOD:'EF_SOD.BIN'}

# Flags filenames for local storage
NOBAC_FILE='NOBAC'

# Data Group 1 Elements
DG1_ELEMENTS= {EF_DG1:'EF.DG1',\
	       '5f01':'LDS Version number with format aabb, where aa defines the version of the LDS and bb defines the update level',\
	       '5f36':'Unicode Version number with format aabbcc, where aa defines the Major version, bb defines the Minor version and cc defines the release level',\
	       '5c':'Tag list. List of all Data Groups present.'}
# Data Group 2 Elements
BDB= '5f2e'
BDB1= '7f2e'
FAC= '46414300'
DG2_ELEMENTS= {EF_DG2:'EF.DG2',\
	       '7f61':'Biometric Information Group Template',\
	       '02':'Integer - Number of instances of this type of biometric',\
	       '7f60':'1st Biometric Information Template',\
	       'a1':'Biometric Header Template (BHT)',\
	       '80':'ICAO header version [01 00] (Optional) - Version of the CBEFF patron header format',\
	       '81':'Biometric type (Optional)',\
	       '82':'Biometric feature (Optional for DG2, mandatory for DG3, DG4.)',\
	       '83':'Creation date and time (Optional)',\
	       '84':'Validity period (from through) (Optional)',\
	       '86':'Creator of the biometric reference data (PID) (Optional)',\
	       '87':'Format owner (Mandatory)',\
	       '88':'Format type (Mandatory)',\
	       BDB:'Biometric data (encoded according to Format Owner) also called the biometric data block (BDB).',\
	       BDB1:'Biometric data (encoded according to Format Owner) also called the biometric data block (BDB).',\
	       '7f60':'2nd Biometric Information Template',\
	       FAC:'Format Identifier ASCII FAC\0'}
# Data Group 2 field types
TEMPLATE= 0
SUB= 1
DG2_TYPE= {EF_DG2:TEMPLATE,\
	     '7f61':TEMPLATE,\
	     '02':SUB,\
	     '7f60':TEMPLATE,\
	     'a1':TEMPLATE,\
	     '80':SUB,\
	     '81':SUB,\
	     '82':SUB,\
	     '83':SUB,\
	     '84':SUB,\
	     '86':SUB,\
	     '87':SUB,\
	     '88':SUB,\
	     '5f2e':TEMPLATE,\
	     '7f2e':TEMPLATE,\
	     '7f60':TEMPLATE}

# ISO 19794_5 (Biometric identifiers)
ISO19794_5_GENDER= { '00':'Unpecified',\
		     '01':'Male',\
		     '02':'Female',\
		     '03':'Unknown',\
		     'ff':'Other'}

ISO19794_5_EYECOLOUR= { '00':'Unspecified',\
			'01':'Black',\
			'02':'Blue',\
			'03':'Brown',\
			'04':'Grey',\
			'05':'Green',\
			'06':'Multi',\
			'07':'Pink',\
			'08':'Other'}

ISO19794_5_HAIRCOLOUR= { '00':'Unspecified',\
			 '01':'Bald',\
			 '02':'Black',\
			 '03':'Blonde',\
			 '04':'Brown',\
			 '05':'Grey',\
			 '06':'White',\
			 '07':'Red',\
			 '08':'Green',\
			 '09':'Blue',\
			 'ff':'Other'}	

ISO19794_5_FEATURE= {0x01:'Specified',\
		     0x02:'Glasses',\
		     0x04:'Moustache',\
		     0x08:'Beard',\
		     0x10:'Teeth Visible',\
		     0x20:'Blink',\
		     0x40:'Mouth Open',\
		     0x80:'Left Eyepatch',\
		     0x100:'Right Eyepatch',\
		     0x200:'Dark Glasses',\
		     0x400:'Distorted'}

ISO19794_5_EXPRESSION= {'0000':'Unspecified',\
			'0001':'Neutral',\
		  	'0002':'Smile Closed',\
		  	'0003':'Smile Open',\
		  	'0004':'Raised Eyebrow',\
		  	'0005':'Looking Away',\
		  	'0006':'Squinting',\
		  	'0007':'Frowning'}

ISO19794_5_IMG_TYPE= {'00':'Unspecified (Front)',\
		      '01':'Basic',\
		      '02':'Full Front',\
		      '03':'Token Front',\
		      '04':'Other'}

ISO19794_5_IMG_DTYPE= {'00':'JPEG',\
		       '01':'JPEG 2000'}

ISO19794_5_IMG_FTYPE= {'00':'JPG',\
		       '01':'JP2'}

ISO19794_5_IMG_CSPACE= {'00':'Unspecified',\
			'01':'RGB24',\
			'02':'YUV422',\
			'03':'GREY8BIT',\
			'04':'Other'}

ISO19794_5_IMG_SOURCE= {'00':'Unspecified',\
			'01':'Static Unspecified',\
			'02':'Static Digital',\
			'03':'Static Scan',\
			'04':'Video Unknown',\
			'05':'Video Analogue',\
			'06':'Video Digital',\
			'07':'Unknown'}

ISO19794_5_IMG_QUALITY= {'00':'Unspecified'}

DG7_ELEMENTS= {EF_DG7:'EF.DG7',\
	       '5f43':'Displayed signature or mark',\
	       '02':'Integer - Number of instances of this type of displayed image'}

# display options
# standard document
MRZ_FIELD_NAMES= ('Document code','Issuing State or Organisation','Name','Passport Number','Check Digit','Nationality','Date of Birth','Check Digit','Sex','Date of Expiry','Check Digit','Personal Number or other optional elements','Check Digit','Composite Check Digit')
MRZ_FIELD_LENGTHS= (2,3,39,9,1,3,6,1,1,6,1,14,1,1)
MRZ_FIELD_DISPLAY= (0,3,1,2,5,6,8,9,11)
MRZ_FIELD_KEYS= (44,57,65)
# id card
MRZ_FIELD_NAMES_ID= ('Document code','Issuing State or Organisation','Document Number','Check Digit','Personal Number or other optional elements','Check Digit','Date of Birth','Check Digit','Sex','Date of Expiry','Check Digit','Nationality','Check Digit','Name')
MRZ_FIELD_LENGTHS_ID= (2,3,9,1,14,1,6,1,1,6,1,14,1,30)
MRZ_FIELD_DISPLAY_ID= (0,2,1,13,11,6,8,9,4)
MRZ_FIELD_KEYS_ID= (5,30,38)

# Global Send Sequence Counter
SSC= ''

# Global bruteforce vars
num= []
map= []
brnum= 0

def mrzspaces(data, fill):
	out= ''
	for x in range(len(data)):
		if data[x] == '<':
			out += fill
		else:
			out += data[x]
	return out

Displayed= False
Display_DG7= False
def drawfeatures(face,features):
	global Displayed
	global Style

	face.delete("feature")
	if Displayed:
		Displayed= False;
		return
	for item in features:
		x= int(item[4:8],16)
		y= int(item[8:12],16)
		if Style == 'Arrow':
			face.create_line(0,0,x,y,fill="Red",arrow="last",width=2,tags="feature")
		if Style == 'Cross':
			face.create_line(x-6,y-6,x+6,y+6,fill="Red",width=2, tags="feature")
			face.create_line(x-6,y+6,x+6,y-6,fill="Red",width=2, tags= "feature")
		if Style == 'Target':
			face.create_line(x,y-15,x,y+15,fill="Red",width=3, tags="feature")
			face.create_line(x-15,y,x+15,y,fill="Red",width=3, tags="feature")
			face.create_oval(x-6,y-6,x+6,y+6,fill="Red",tags="feature")
		if Style == 'Circle':
			face.create_oval(x-6,y-6,x+6,y+6,fill="Red", tags="feature")
		Displayed= True

def changestyle(style,face,features):
	global Style
	global Displayed

	Style= style
	if Displayed:
		Displayed= False
		drawfeatures(face,features)

def secure_select_file(keyenc, keymac,file):
	"secure select file"
	global SSC

	cla= '0c'
	ins= passport.ISOAPDU['SELECT_FILE']
	p1= '02'
	p2= '0c'
	command= passport.PADBlock(passport.ToBinary(cla + ins + p1 + p2))
	data= passport.PADBlock(passport.ToBinary(file))
	tdes= DES3.new(keyenc,DES.MODE_CBC,passport.DES_IV)
	encdata= tdes.encrypt(data)
	if DEBUG:
		print 'Encrypted data: ',
		passport.HexPrint(encdata)
	do87= passport.ToBinary(passport.DO87) + encdata
	m= command + do87
	if DEBUG:
		print 'DO87: ',
		passport.HexPrint(m)
	SSC= passport.SSCIncrement(SSC)
	n= SSC + m
	cc= passport.DESMAC(n,keymac,'')
	if DEBUG:
		print 'CC: ',
		passport.HexPrint(cc)
	do8e= passport.ToBinary(passport.DO8E) + cc
	if DEBUG:
		print 'DO8E: ',
		passport.HexPrint(do8e)
	lc= "%02x" % (len(do87) + len(do8e))
	le= '00'
	data= passport.ToHex(do87 + do8e)
	if DEBUG:
		print
		print 'Protected APDU: ',
		print cla+ins+p1+p2+lc+data+le
	ins= 'SELECT_FILE'
	if passport.send_apdu('','','','',cla,ins,p1,p2,lc,data,le):
		out= passport.data
	if DEBUG:
		print 'Secure Select:',
	if passport.errorcode == APDU_OK:
		if DEBUG:
			print 'OK'
		check_cc(keymac,out)
		return True, out
	else:
		return False, passport.errorcode

def secure_read_binary(keymac,bytes,offset):
	"secure read binary data"
	global SSC

	cla= '0c'
	ins= passport.ISOAPDU['READ_BINARY']
	hexoffset= '%04x' % offset
	p1= hexoffset[0:2]
	p2= hexoffset[2:4]
	le= '%02x' % bytes
	command= passport.PADBlock(passport.ToBinary(cla + ins + p1 + p2))
	do97= passport.ToBinary(passport.DO97 + le)
	m= command + do97 
	SSC= passport.SSCIncrement(SSC)
	n= SSC + m
	cc= passport.DESMAC(n,keymac,'')
	do8e= passport.ToBinary(passport.DO8E) + cc
	lc= "%02x" % (len(do97) + len(do8e))
	le= '00'
	data= passport.ToHex(do97 + do8e)
	if DEBUG:
		print
		print 'Protected APDU: ',
		print cla+ins+p1+p2+lc+data+le
	ins= 'READ_BINARY'
	if passport.send_apdu('','','','',cla,ins,p1,p2,lc,data,le):
		out= passport.data
	if DEBUG:
		print 'Secure Read Binary (%02d bytes): ' % bytes,
	if passport.errorcode == APDU_OK:
		if DEBUG:
			print 'OK:', out
		check_cc(keymac,out)
		return True, out
	else:
		return False, passport.errorcode 

def calculate_check_digit(data):
	"calculate ICAO 9303 check digit"
	cd= n= 0
	for d in data:
		if 'A' <= d <= 'Z':
			value = ord(d)-55
		elif d == '<':
			value = 0
		else:
			value = int(d)
		cd += value * MRZ_WEIGHT[n % 3]
		n += 1
	return '%s' % (cd % 10)

def check_cc(key,rapdu):
	"Check Cryptographic Checksum"
	global SSC

	SSC= passport.SSCIncrement(SSC)
	k= SSC
	length= 0
	# check if DO87 present
	if rapdu[0:2] == "87":
		length= 4 + int(rapdu[2:4],16) * 2
		k += passport.ToBinary(rapdu[:length])
	# check if DO99 present
	if rapdu[length:length + 2] == "99":
		length2= 4 + int(rapdu[length + 2:length + 4],16) * 2
		k += passport.ToBinary(rapdu[length:length + length2])
	
	if DEBUG:
		print 'K: ',
		passport.HexPrint(k)
	cc= passport.DESMAC(k,key,'')
	if DEBUG:
		print 'CC: ',
		print passport.ToHex(cc),
	if cc ==  passport.ToBinary(rapdu[len(rapdu) - len(cc) *2:]):
		if DEBUG:
        		print '(verified)'
		return True
	else:
        	print 'Cryptographic Checksum failed!'
        	print 'Expected CC: ',
        	passport.HexPrint(cc)
        	print 'Received CC: ',
        	print rapdu[len(rapdu) - len(cc) * 2:]
		os._exit(True)

def decode_ef_com(data):
	TAG_PAD= '80'

	# set up array for Data Groups to be read
	ef_groups= []

	"display contents of EF.COM"
	hexdata= passport.ToHex(data)
	# skip header
	pos= 2
	# EF.COM length
	print 'Length: ', asn1datalength(hexdata[pos:])
	pos += asn1fieldlength(hexdata[pos:])
	while pos < len(hexdata):
		# end of data
		if hexdata[pos:pos+2] == TAG_PAD:
			return
		# LDS & Unicode Versions
		decoded= False
		for length in 2,4:
                       	if DG1_ELEMENTS.has_key(hexdata[pos:pos + length]):
				decoded= True
				print '  tag:',hexdata[pos:pos + length],'('+DG1_ELEMENTS[hexdata[pos:pos+length]]+')'
				# decode tag list (stored objects)
				if hexdata[pos:pos+length] == EF_TAGS:
					pos += 2
					print '    length: ',
					length= asn1datalength(hexdata[pos:])
					print length
					pos += asn1fieldlength(hexdata[pos:])
					for n in range(length):
						print '      Data Group: ',
						print hexdata[pos:pos+2] + ' (' + TAG_NAME[hexdata[pos:pos+2]] + ')'
						ef_groups.append(hexdata[pos:pos+2])
						pos += 2
				else:
					pos += length
					fieldlength= asn1datalength(hexdata[pos:])
					print '    length:',fieldlength
					pos += asn1fieldlength(hexdata[pos:])
					print '    data:',hexdata[pos:pos+fieldlength*2]
					pos += fieldlength*2
		if not decoded:
			print 'Unrecognised element:', hexdata[pos:pos+4]
			os._exit(True)
	return ef_groups

def read_file(file):
	if not passport.iso_7816_select_file(file,passport.ISO_7816_SELECT_BY_EF,'0C'):
		return False, ''
	readlen= 4
	offset= 4
	if not passport.iso_7816_read_binary(readlen,0):
		return False, ''
	data= passport.data
	# get file length
	tag= data[:2]
	datalen= asn1datalength(data[2:])
	print 'File Length:', datalen
	# deduct length field and header from what we've already read
	readlen= datalen - (3 - asn1fieldlength(data[2:]) / 2)
	print 'Remaining data length:', readlen
	# read remaining bytes
	while readlen > 0:
		if readlen > MAXCHUNK:
			toread= MAXCHUNK
		else:
			toread= readlen
		if not passport.iso_7816_read_binary(toread,offset):
			return False, ''
		data+=passport.data
		offset += toread
		readlen -= toread
		print 'Reading: %05d\r' % readlen,
		sys.stdout.flush()
	print
	return True, data.decode('hex')

def asn1fieldlength(data):
	#return length of number field according to asn.1 rules (doubled as we normally care about the hex version)
	if int(data[:2],16) <= 0x7f:
		return 2
	if int(data[:2],16) == 0x81:
		return 4
	if int(data[:2],16) == 0x82:
		return 6

def asn1datalength(data):
	#return actual length represented by asn.1 field
	if int(data[:2],16) <= 0x7f:
		return int(data[:2],16)
	if int(data[:2],16) == 0x81:
		return  int(data[2:4],16)
	if int(data[:2],16) == 0x82:
		return int(data[2:6],16)

def secure_read_file(keyenc,keymac,file):
#	MAXCHUNK= int(passport.ISO_FRAMESIZE[passport.framesize])

	status, rapdu= secure_select_file(keyenc,keymac,file)
	if not status:
		return False, rapdu
	# secure read file header (header byte plus up to 3 bytes of field length)
	readlen= 4
	offset= 4
	status, rapdu= secure_read_binary(keymac,readlen,0)
	if not status:
		return False, rapdu
	do87= rapdu[6:22]
	if DEBUG:
		print 'DO87: ' + do87
		print 'Decrypted DO87: ',
	tdes=  DES3.new(keyenc,DES.MODE_CBC,passport.DES_IV)
	decdo87= tdes.decrypt(passport.ToBinary(do87))[:readlen]
	if DEBUG:
		passport.HexPrint(decdo87)

	# get file length
	do87hex= passport.ToHex(decdo87)
	tag= do87hex[:2]
	datalen= asn1datalength(do87hex[2:])
	print 'File Length:', datalen
	# deduct length field and header from what we've already read
	readlen= datalen - (3 - asn1fieldlength(do87hex[2:]) / 2)
	print 'Remaining data length:', readlen
	# secure read remaining bytes
	while readlen > 0:
		if readlen > MAXCHUNK:
			toread= MAXCHUNK
		else:
			toread= readlen
		status, rapdu= secure_read_binary(keymac,toread,offset)
		if not status:
			return rapdu
		do87= rapdu[6:(toread + (8 - toread % 8)) * 2 + 6]
		tdes=  DES3.new(keyenc,DES.MODE_CBC,passport.DES_IV)
		decdo87 += tdes.decrypt(passport.ToBinary(do87))[:toread]
		offset += toread
		readlen -= toread
		print 'Reading: %05d\r' % readlen,
		sys.stdout.flush()
	print
	return True, decdo87

def decode_ef_dg1(data):
	global DocumentType
	global DOCUMENT_TYPE
	global Fields
	global FieldNames
	global FieldLengths
	global FieldKeys

	length= int(passport.ToHex(data[4]),16)
	print 'Data Length: ',
	print length
	pointer= 5
	out= ''
	while pointer < len(data):
		if data[pointer] == chr(0x80):
			break
		out += '%s' % chr(int(passport.ToHex(data[pointer]),16))
		pointer += 1
	print '  Decoded Data: ' + out
	DocumentType= out[0:2]
	if DOC_ID.has_key(DocumentType):
		print '    Document type: %s' % DOC_ID[DocumentType]
		DOCUMENT_TYPE= DOC_ID
		Fields= MRZ_FIELD_DISPLAY_ID
		FieldNames= MRZ_FIELD_NAMES_ID
		FieldLengths= MRZ_FIELD_LENGTHS_ID
		FieldKeys= MRZ_FIELD_KEYS_ID
	else:
		print '    Document type: %s' % DOC_PASS[DocumentType]
		DOCUMENT_TYPE= DOC_PASS
		Fields= MRZ_FIELD_DISPLAY
		FieldNames= MRZ_FIELD_NAMES
		FieldLengths= MRZ_FIELD_LENGTHS
		FieldKeys= MRZ_FIELD_KEYS
	pointer= 0
	for n in range(len(FieldNames)):
		print '    ' + FieldNames[n] + ': ',
		print out[pointer:pointer + FieldLengths[n]]
		pointer += FieldLengths[n]
	return(out)

def decode_ef_dg2(data):
	global Filetype
	img_features= []

	datahex= passport.ToHex(data)
	position= 0
	end= len(datahex)
	while position < end:
		decoded= False
		# check for presence of tags
		for length in 4,2:
			if DG2_ELEMENTS.has_key(datahex[position:position + length]):
				decoded= True
				tag= datahex[position:position + length]
				print '  Tag:', tag, '('+DG2_ELEMENTS[tag]+')'
				# don't skip TEMPLATE fields as they contain sub-fields
				# except BDB which is a special case (CBEFF formatted) so for now
				# just try and extract the image which is 65 bytes in
				if DG2_TYPE[tag] == TEMPLATE:
					position += length
					fieldlength= asn1datalength(datahex[position:])
					print '     length:', fieldlength
					if tag == BDB or tag == BDB1:
						# process CBEFF block
						position += asn1fieldlength(datahex[position:])
						# FACE header
						length= len(FAC)
						tag= datahex[position:position + length]
						if not tag == FAC:
							print 'Missing FAC in CBEFF block: %s' % tag
							os._exit(True)
						position += length
						# FACE version
						print '    FACE version: %s' % passport.ToBinary(datahex[position:position + 6])
						position += 8
						# Image length
						print '      Record Length: %d' % int(datahex[position:position + 8],16)
						imagelength= int(datahex[position:position + 8],16)
						position += 8
						# Number of Images
						images= int(datahex[position:position + 4],16)
						print '      Number of Images: %d' % images
						position += 4
						# Facial Image block
						print '      Block Length: %d' % int(datahex[position:position + 8],16)
						position += 8
						features= int(datahex[position:position + 4],16)
						print '      Number of Features: %d' % features
						position += 4
						print '      Gender: %s' % ISO19794_5_GENDER[datahex[position:position + 2]]
						position += 2
						print '      Eye Colour: %s' % ISO19794_5_EYECOLOUR[datahex[position:position + 2]]
						position += 2
						print '      Hair Colour: %s' % ISO19794_5_HAIRCOLOUR[datahex[position:position + 2]]
						position += 2
						mask= int(datahex[position:position + 6],16)
						print '      Feature Mask: %s' % datahex[position:position + 6]
						position += 6
						if features:
							print '      Features:'
							for m, d in ISO19794_5_FEATURE.items():
								if and_(mask,m):
									print '        : %s' % d
						print '      Expression: %s' % ISO19794_5_EXPRESSION[datahex[position:position + 4]]
						position += 4
						print '      Pose Angle: %s' % datahex[position:position + 6]
						position += 6
						print '      Pose Angle Uncertainty: %s' % datahex[position:position + 6]
						position += 6
						while features > 0:
							print '      Feature block: %s' % datahex[position:position + 16]
							img_features.append(datahex[position:position + 16])
							features -= 1
							position += 16
						print '      Image Type: %s' % ISO19794_5_IMG_TYPE[datahex[position:position + 2]]
						position += 2
						print '      Image Data Type: %s' % ISO19794_5_IMG_DTYPE[datahex[position:position + 2]]
						Filetype= ISO19794_5_IMG_FTYPE[datahex[position:position + 2]]
						position += 2
						print '      Image Width: %d' % int(datahex[position:position + 4],16)
						position += 4
						print '      Image Height: %d' % int(datahex[position:position + 4],16)
						position += 4
						print '      Image Colour Space: %s' % ISO19794_5_IMG_CSPACE[datahex[position:position + 2]]
						position += 2
						print '      Image Source Type: %s' % ISO19794_5_IMG_SOURCE[datahex[position:position + 2]]
                                                position += 2
						print '      Image Device Type: %s' % datahex[position:position + 6]
                                                position += 6
						print '      Image Quality: %s' % ISO19794_5_IMG_QUALITY[datahex[position:position + 2]]
						position += 2
						img= open(tempfiles+'EF_DG2.' + Filetype,'wb+')
						img.write(data[position / 2:position + imagelength])
						img.flush()
						img.close()
						print '     JPEG image stored in %sEF_DG2.%s' % (tempfiles,Filetype)
						position += imagelength * 2
					else:
						position += asn1fieldlength(datahex[position:])
				else:
					position += length
					fieldlength= asn1datalength(datahex[position:])
					print '     length:', fieldlength
					position += asn1fieldlength(datahex[position:])
					print '     data:', datahex[position:position + fieldlength * 2]
					position += fieldlength * 2
		if not decoded:
			print 'Unrecognised element:', datahex[position:position + 4]
			os._exit(True)
	return img_features	

def decode_ef_dg7(data):
	global Filetype
	global Display_DG7
	datahex= passport.ToHex(data)
	position= 0
	end= len(datahex)
	while position < end:
		decoded= False
		# check for presence of tags
		for length in 4,2:
			if DG7_ELEMENTS.has_key(datahex[position:position + length]):
				decoded= True
				tag= datahex[position:position + length]
				print '  Tag:', tag, '('+DG7_ELEMENTS[tag]+')'
				position += length
				fieldlength= asn1datalength(datahex[position:])
				print '     length:', fieldlength
				if tag == '67':
					position += asn1fieldlength(datahex[position:])
				elif tag == '02':
					position += asn1fieldlength(datahex[position:])
					print '     content: %i instance(s)' % int(datahex[position:position + fieldlength * 2], 16)
					# note that for now we don't support decoding several instances...
					position += fieldlength * 2
				elif tag == '5f43':
					position += asn1fieldlength(datahex[position:])
					img= open(tempfiles+'EF_DG7.' + Filetype,'wb+')
					img.write(data[position / 2:position + fieldlength])
					img.flush()
					img.close()
					print '     JPEG image stored in %sEF_DG7.%s' % (tempfiles,Filetype)
					Display_DG7= True
					position += fieldlength * 2
		if not decoded:
			print 'Unrecognised element:', datahex[position:position + 4]
			os._exit(True)
	return

def jmrtd_create_file(file,length):
	"create JMRTD file"
	ins= 'CREATE_FILE'
	p1= '00'
	p2= '00'
	le= '06' # length is always 6
	data= "6304" + "%04x" % length + file
	if passport.send_apdu('','','','','',ins,p1,p2,le,data,''):
		return
	if passport.errorcode == '6D00':
		# could be a vonJeek card
		print "create file failed - assuming vonJeek emulator"
		return
	passport.iso_7816_fail(passport.errorcode)

def jmrtd_select_file(file):
	"select JMRTD file"
	ins= 'SELECT_FILE'
	p1= '00'
	p2= '00'
	data= "02" + file
	if passport.send_apdu('','','','','',ins,p1,p2,'',data,''):
		return
	if passport.errorcode == '6982':
		# try vonJeek
		print "selecting vonJeek file"
		ins= 'VONJEEK_SELECT_FILE'
		cla= '10'
		if passport.send_apdu('','','','',cla,ins,p1,p2,'',data,''):
			return
	passport.iso_7816_fail(passport.errorcode)

def jmrtd_write_file(file,data):
	"write data to JMRTD file"
	jmrtd_select_file(file)
	offset= 0
	towrite= len(data)
	while towrite:
		if towrite > MAXCHUNK:
			chunk= MAXCHUNK
		else:
			chunk= towrite
		print "\rwriting %d bytes       " % towrite,
		sys.stdout.flush()
		jmrtd_update_binary(offset,data[offset:offset + chunk])
		offset += chunk
		towrite -= chunk
	print

def jmrtd_update_binary(offset,data):
	"write a chunk of data to an offset within the currently selected JMRTD file"
	hexoff= "%04x" % offset
	ins= 'UPDATE_BINARY'
	p1= hexoff[0:2]
	p2= hexoff[2:4]
	lc= "%02x" % len(data)
	data= passport.ToHex(data)
	if passport.send_apdu('','','','','',ins,p1,p2,lc,data,''):
		return
	if passport.errorcode == '6D00':
		# vonJeek
		print "(vonJeek)",
		ins= 'VONJEEK_UPDATE_BINARY'
		cla= '10'
		if passport.send_apdu('','','','',cla,ins,p1,p2,lc,data,''):
			return
	passport.iso_7816_fail(passport.errorcode)

def jmrtd_personalise(documentnumber,dob,expiry):
	"set the secret key for JMRTD document"
	ins= 'PUT_DATA'
	p1= '00'
	p2= '62'
	data= '621B04' + "%02x" % len(documentnumber) + passport.ToHex(documentnumber) + '04' + "%02x" % len(dob) + passport.ToHex(dob) + '04' + "%02X" % len(expiry) + passport.ToHex(expiry)
	lc= "%02X" % (len(data) / 2)
	if passport.send_apdu('','','','','',ins,p1,p2,lc,data,''):
		return 
	if passport.errorcode == '6D00':
		# vonJeek
		cla= '10'
		ins= 'VONJEEK_SET_MRZ'
		data= passport.ToHex(documentnumber) +  passport.ToHex(calculate_check_digit(documentnumber)) + passport.ToHex(dob) + passport.ToHex(calculate_check_digit(dob)) + passport.ToHex(expiry) + passport.ToHex(calculate_check_digit(expiry))
		lc= "%02X" % (len(data) / 2)
		if passport.send_apdu('','','','',cla,ins,p1,p2,lc,data,''):
			# see if we need to set BAC or not, hacky way for now...
			if os.access(filespath+NOBAC_FILE,os.F_OK):
				BAC=False
			else:
				BAC=True
			if BAC:
				vonjeek_setBAC()
			else:
				vonjeek_unsetBAC()
			return
	passport.iso_7816_fail(passport.errorcode)

def vonjeek_setBAC():
	"enable BAC on vonjeek emulator card"
	# Setting BAC works only on recent vonJeek emulators, older have only BAC anyway
	print "Forcing BAC mode to ENABLED"
	if passport.send_apdu('','','','','10','VONJEEK_SET_BAC','00','01','00','',''):
		return
	else:
		print "ERROR Could not enable BAC, make sure you are using a recent vonJeek emulator"
		os._exit(True)

def vonjeek_unsetBAC():
	"disable BAC on vonjeek emulator card"
	print "Forcing BAC mode to DISABLED"
	if passport.send_apdu('','','','','10','VONJEEK_SET_BAC','00','00','00','',''):
		return
	else:
		print "ERROR Could not disable BAC, make sure you are using a recent vonJeek emulator"
		os._exit(True)

def jmrtd_lock():
	"set the JMRTD to Read Only"
	ins= 'PUT_DATA'
	p1= 'de'
	p2= 'ad'
	lc= '00'
	if passport.send_apdu('','','','','',ins,p1,p2,lc,'',''):
		return
	passport.iso_7816_fail(passport.errorcode)

def bruteno(init):
	global num
	global map
	global brnum
	global width

	if init:
		# set up brute force and return number of iterations required
		width= 0
		for x in range(len(init)):
			if init[x] == '?':
				width += 1
				num.append(0)
				map.append(True)
			else:
				num.append(init[x])
				map.append(False)
		return pow(10, width)
	else:
		out= ''
		bruted= False
		for x in range(len(num)):
			if map[x]:
				if bruted:
					continue
				else:
					bruted= True
					out += '%0*d' % (width, brnum)
					brnum += 1
			else:
				out += num[x]
		return out

try:
        passport= rfidiot.card
except:
        os._exit(True)

args= rfidiot.args
Help= rfidiot.help
Nogui= rfidiot.nogui
DEBUG= rfidiot.rfidiotglobals.Debug

myver= 'mrpkey v0.1u'
passport.info(myver)

TEST= False
FILES= False
bruteforce= False
bruteforceno= False
bruteforcereset= False
Jmrtd= False
JmrtdLock= False
MRZ=True
BAC=True
SETBAC=False
UNSETBAC=False

def help():
	print
	print 'Usage:'
	print '\t' + sys.argv[0] + ' [OPTIONS] <MRZ (Lower)|PLAIN|CHECK|[PATH]> [WRITE|WRITELOCK|SLOWBRUTE]'
	print
	print '\tSpecify the Lower MRZ as a quoted string or the word TEST to use sample data.'
	print '\tLower MRZ can be full line or shortened to the essentials: chars 1-9;14-19;22-27'
	print '\tSpecify the word PLAIN if the passport doesn\'t have BAC (shorthand for dummy MRZ)'
	print '\tSpecify the word CHECK to check if the device is a passport.'
	print '\tSpecify a PATH to use files that were previously read from a passport.'
	print '\tSpecify the option WRITE after a PATH to initialise a JMRTD or vonJeek emulator \'blank\'.'
	print '\tSpecify the option WRITELOCK after a PATH to initialise a JMRTD emulator \'blank\' and set to Read Only.'
	print '\tSpecify the option WRITE/WRITELOCK after a MRZ or PLAIN to clone a passport to a JMRTD or vonJeek emulator.'
	print '\tSpecify the option SETBAC   to enable  BAC on a (already configured) vonJeek emulator card.'
	print '\tSpecify the option UNSETBAC to disable BAC on a (already configured) vonJeek emulator card.'
	print '\tSpecify \'?\' for check digits if not known and they will be calculated.'
	print '\tSpecify \'?\' in the passport number field for bruteforce of that portion.'
	print '\tNote: only one contiguous portion of the field may be bruteforced.'
	print '\tSpecify the option SLOWBRUTE after MRZ to force reset between attempts (required on some new passports)'
	print '\tPadding character \'<\' should be used for unknown fields.'
	print
        os._exit(True)

if len(args) == 0 or Help:
	help()

arg0= args[0].upper()

if not(len(arg0) == 44 or len(arg0) == 21 or arg0 == 'TEST' or arg0 == 'CHECK' or arg0 == 'PLAIN' or arg0 == 'SETBAC' or arg0 == 'UNSETBAC' or os.access(args[0],os.F_OK)) or len(args) > 2:
	help()

if len(args) == 2:
        arg1= args[1].upper()
        if not (arg1 == 'WRITE' or arg1 == 'WRITELOCK' or arg1 == 'SLOWBRUTE'):
                help()

print

# check if we are reading from files
if os.access(args[0],os.F_OK):
	FILES= True
	filespath= args[0]
	if not filespath[len(filespath) - 1] == '/':
		filespath += '/'
	try:
		passfile= open(filespath + 'EF_COM.BIN','rb')
	except:
		print "Can't open %s" % (filespath + 'EF_COM.BIN')
		os._exit(True)
	data= passfile.read()
	eflist= decode_ef_com(data)
	raw_efcom= data
	passfile.close()

if arg0 == 'PLAIN' or len(arg0) == 44 or len(arg0) == 21 or FILES:
	if len(args) == 2:
		if arg1 == "WRITE":
			Jmrtd= True
		if arg1 == "WRITELOCK":
			Jmrtd= True
			JmrtdLock= True

if len(args) == 2 and arg1 == "SLOWBRUTE":
        bruteforcereset = True

if arg0 == 'TEST':
	TEST= True

if arg0 == 'SETBAC':
	MRZ=False
	SETBAC= True

if arg0 == 'UNSETBAC':
	MRZ=False
	UNSETBAC= True

if arg0 == 'CHECK':
	while not passport.hsselect('08', 'A') and not passport.hsselect('08', 'B'):
		print 'Waiting for passport... (%s)' % passport.errorcode
	if passport.iso_7816_select_file(passport.AID_MRTD,passport.ISO_7816_SELECT_BY_NAME,'0C'):
		print 'Device is a Machine Readable Document'
		os._exit(False)
	else:
		print 'Device may NOT be a Machine Readable Document'
		passport.iso_7816_fail(passport.errorcode)
		os._exit(True)

if arg0 == 'PLAIN':
	MRZ=False

if TEST:
	passport.MRPmrzl(TEST_MRZ)
	print 'Test MRZ: ' + TEST_MRZ
if not TEST and not FILES and MRZ:
	key=arg0
	# expands short MRZ version if needed
	if len(key) == 21:
		key= key[0:9] + 'XXXX' + key[9:15] + 'XX' + key[15:21] + 'XXXXXXXXXXXXXXXXX'
	passport.MRPmrzl(key)

if not FILES and not TEST:
	# set communication speed
	# 01 = 106 kBaud
	# 02 = 212 kBaud
	# 04 = 414 kBaud
	# 08 = 818 kBaud
	while 42:
                cardtype='A'
                if passport.hsselect('08', cardtype):
                        break
                cardtype='B'
                if passport.hsselect('08', cardtype):
                        break
		print 'Waiting for passport... (%s)' % passport.errorcode
	print 'Device set to %s transfers' % passport.ISO_SPEED[passport.speed]
	print 'Device supports %s Byte transfers' % passport.ISO_FRAMESIZE[passport.framesize]
	print
	print 'Select Passport Application (AID): ',
	if passport.iso_7816_select_file(passport.AID_MRTD,passport.ISO_7816_SELECT_BY_NAME,'0C'):
		print 'OK'
	else:
		passport.iso_7816_fail(passport.errorcode)
	print 'Select Master File: ',
	if passport.iso_7816_select_file(TAG_FID[EF_COM],passport.ISO_7816_SELECT_BY_EF,'0C'):
		# try forcing BAC by reading a file
		status, data= read_file(TAG_FID[EF_DG1])
		if not status and passport.errorcode == APDU_BAC:
			BAC=True
		else:
			print 'No Basic Access Control!'
			print passport.errorcode
			BAC=False
if BAC:
	print 'Basic Acces Control Enforced!'

if SETBAC:
	vonjeek_setBAC()
	os._exit(True)

if UNSETBAC:
	vonjeek_unsetBAC()
	os._exit(True)

if BAC and not MRZ:
	print 'Please provide a MRZ!'
	os._exit(True)

if not FILES and BAC:
	print 'Passport number: ' + passport.MRPnumber
	if passport.MRPnumber.find('?') >= 0:
		bruteforce= True
		bruteforceno= True
		# initialise bruteforce for number
		iterations= bruteno(passport.MRPnumber)
		print 'Bruteforcing Passport Number (%d iterations)' % iterations
	else:
		iterations= 1
	print 'Nationality: ' + passport.MRPnationality
	print 'Date Of Birth: ' + passport.MRPdob
	print 'Sex: ' + passport.MRPsex
	print 'Expiry: ' + passport.MRPexpiry
	print 'Optional: ' + passport.MRPoptional

	# loop until successful login breaks us out or we've tried all possibilities
	while iterations:
		iterations -= 1
		if bruteforceno:
			passport.MRPnumber= bruteno('')
		# always calculate check digits (makes bruteforcing easier)
		passport.MRPnumbercd= calculate_check_digit(passport.MRPnumber)
		passport.MRPdobcd= calculate_check_digit(passport.MRPdob)
		passport.MRPexpirycd= calculate_check_digit(passport.MRPexpiry)
		passport.MRPoptionalcd= calculate_check_digit(passport.MRPoptional)
		passport.MRPcompsoitecd= calculate_check_digit(passport.MRPnumber + passport.MRPnumbercd + passport.MRPdob + passport.MRPdobcd + passport.MRPexpiry + passport.MRPexpirycd + passport.MRPoptional + passport.MRPoptionalcd)

		kmrz= passport.MRPnumber + passport.MRPnumbercd + passport.MRPdob + passport.MRPdobcd + passport.MRPexpiry + passport.MRPexpirycd

		print
		print 'Generate local keys:'
		print
		if not TEST:
			print 'Supplied MRZ:  ' + arg0
			print 'Corrected MRZ: ' + passport.MRPnumber + passport.MRPnumbercd + passport.MRPnationality + passport.MRPdob + passport.MRPdobcd + passport.MRPsex + passport.MRPexpiry + passport.MRPexpirycd + passport.MRPoptional + passport.MRPoptionalcd+passport.MRPcompsoitecd
		print 'Key MRZ Info (kmrz): ' + kmrz
		print
		kseedhash= SHA.new(kmrz)
		kseed= kseedhash.digest()[:16]
		if DEBUG:
			print 'Kseed (SHA1 hash digest of kmrz): ' + kseedhash.hexdigest()[:32]

		# calculate Kenc & Kmac
		Kenc= passport.DESKey(kseed,passport.KENC,16)
		if DEBUG:
			print 'Kenc: ',
			passport.HexPrint(Kenc)
		Kmac= passport.DESKey(kseed,passport.KMAC,16)
		if DEBUG:
			print 'Kmac: ',
			passport.HexPrint(Kmac)
			print

		if TEST:
			rnd_ifd= TEST_rnd_ifd
			rnd_icc= TEST_rnd_icc
			Kifd= TEST_Kifd
		else:
			if DEBUG:
				print 'Get Challenge from Passport (rnd_icc): ',
			if passport.iso_7816_get_challenge(8):
				rnd_icc= passport.data
			else:
				passport.iso_7816_fail(passport.errorcode)	
			if DEBUG:
				passport.HexPrint(rnd_icc)
			rnd_ifd= passport.GetRandom(8)
			Kifd= passport.GetRandom(16)

		if DEBUG or TEST:
			print 'Generate local random Challenge (rnd_ifd): ' + rnd_ifd
			print 'Generate local random Challenge (Kifd): ' + Kifd
			print

		S= passport.ToBinary(rnd_ifd + rnd_icc + Kifd)

		if DEBUG or TEST:
			print 'S: ',
			passport.HexPrint(S)

		if DEBUG or TEST:
			print 'Kenc: ',
			passport.HexPrint(Kenc)


		tdes= DES3.new(Kenc,DES.MODE_CBC,passport.DES_IV)
		Eifd= tdes.encrypt(S)
		if DEBUG or TEST:
			print 'Eifd: ',
			passport.HexPrint(Eifd)
			print 'Kmac: ',
			passport.HexPrint(Kmac)
		Mifd= passport.DESMAC(Eifd,Kmac,'')
		if DEBUG or TEST:
			print 'Mifd: ',
			passport.HexPrint(Mifd)

		cmd_data= Eifd + Mifd
		if DEBUG or TEST:
			print 'cmd_data: ',
			passport.HexPrint(cmd_data)
			print

		if TEST:
			respdata= TEST_respdata
		else:
			print 'Authenticating: ',
			if passport.iso_7816_external_authenticate(passport.ToHex(cmd_data),Kmac):
				respdata= passport.data
			else:
				# failures allowed if we're brute forcing
				if brnum:
					respdata= ''
				else:
					passport.iso_7816_fail(passport.errorcode)
		if DEBUG or TEST:
			print 'Auth Response: ' + respdata
		resp= respdata[:64]
		respmac= respdata[64:80]
		if DEBUG or TEST:
			print 'Auth message: ' + resp
			print 'Auth MAC: ' + respmac + ' (verified)'
		decresp= passport.ToHex(tdes.decrypt(passport.ToBinary(resp)))
		if DEBUG or TEST:
			print 'Decrypted Auth Response: ' + decresp
			print 'Decrypted rnd_icc: ' + decresp[:16]
		recifd= decresp[16:32]
		if DEBUG or TEST:
			print 'Decrypted rnd_ifd: ' + recifd,
		# check returned rnd_ifd matches our challenge
		if not passport.ToBinary(recifd) == passport.ToBinary(rnd_ifd):
			print 'Challenge failed!'
			print 'Expected rnd_ifd: ', rnd_ifd
			print 'Received rnd_ifd: ', recifd
			if not bruteforce or iterations == 0:
				os._exit(True)
                        if bruteforcereset:
                                while not passport.hsselect('08', cardtype):
                                        print 'Waiting for passport... (%s)' % passport.errorcode
                                passport.iso_7816_select_file(passport.AID_MRTD,passport.ISO_7816_SELECT_BY_NAME,'0C')
		else:
			if DEBUG or TEST:
				print '(verified)'
			# challenge succeeded, so break
			break

	kicc= decresp[32:64] 
	if DEBUG or TEST:
		print 'Decrypted Kicc: ' + kicc

	# generate session keys
	print
	print 'Generate session keys: '
	print
	kseedhex= "%032x" % xor(int(Kifd,16),int(kicc,16))
	kseed= passport.ToBinary(kseedhex)
	print 'Kifd XOR Kicc (kseed): ',
	passport.HexPrint(kseed)
	KSenc= passport.DESKey(kseed,passport.KENC,16)
	print 'Session Key ENC: ',
	passport.HexPrint(KSenc)
	KSmac= passport.DESKey(kseed,passport.KMAC,16)
	print 'Session Key MAC: ',
	passport.HexPrint(KSmac)

	print
	# calculate Send Sequence Counter
	print 'Calculate Send Sequence Counter: '
	print
	SSC= passport.ToBinary(rnd_icc[8:16] + rnd_ifd[8:16])
	print 'SSC: ',
	passport.HexPrint(SSC)

	# secure select master file
	if TEST:
		KSmac= passport.ToBinary('F1CB1F1FB5ADF208806B89DC579DC1F8')
		rapdu= '990290008E08FA855A5D4C50A8ED9000'
		# ran out of steam on testing here! 
		os._exit(False)
	else:
		status, data= secure_read_file(KSenc,KSmac,TAG_FID[EF_COM])
		if not status:
			passport.iso_7816_fail(data)	

	# secure read file header
	#if TEST:
	#	KSmac= passport.ToBinary('F1CB1F1FB5ADF208806B89DC579DC1F8')
	#	rapdu= '8709019FF0EC34F9922651990290008E08AD55CC17140B2DED9000'
	#else:
	#	readlen= 4
	#	rapdu= secure_read_binary(KSmac,readlen,0)

	print 'EF.COM: ',
	if DEBUG:
		passport.HexPrint(data)
	eflist= decode_ef_com(data)
	raw_efcom= data
	efcom= open(tempfiles+TAG_FILE[EF_COM],'wb+')
	efcom.write(data)
	efcom.flush()
	efcom.close()
	print 'EF.COM stored in', tempfiles+TAG_FILE[EF_COM]

if not FILES and not BAC:
	status, data= read_file(TAG_FID[EF_COM])
	if not status:
		passport.iso_7816_fail(passport.errorcode)

	print 'EF.COM: ',
	if DEBUG:
		passport.HexPrint(data)
	eflist= decode_ef_com(data)
	raw_efcom= data
	bacfile= open(tempfiles+NOBAC_FILE,'wb+')
	bacfile.close()
	efcom= open(tempfiles+TAG_FILE[EF_COM],'wb+')
	efcom.write(data)
	efcom.flush()
	efcom.close()
	print 'EF.COM stored in', tempfiles+TAG_FILE[EF_COM]

# get SOD
#print
#print 'Select EF.SOD: ',
#data= secure_read_file(KSenc,KSmac,TAG_FID[EF_SOD])
#if DEBUG:
#	passport.HexPrint(data)
#sod= open(tempfiles+TAG_FILE[EF_SOD],'w+')
#sod.write(data)
#sod.flush()
#sod.close()
#print 'EF.SOD stored in', tempfiles+TAG_FILE[EF_SOD]

# Add Security Object and Main Directory to list for reading
eflist.insert(0,EF_SOD)
eflist.insert(0,EF_COM)
# now get everything else
for tag in eflist:
	print 'Reading:', TAG_NAME[tag]
	if not FILES:
		if BAC:
			status, data= secure_read_file(KSenc,KSmac,TAG_FID[tag])
		else:
			status, data= read_file(TAG_FID[tag])
		if not status:
			print "skipping (%s)" % passport.ISO7816ErrorCodes[data] 
			continue
	else:
		try:
			passfile= open(filespath+TAG_FILE[tag],'rb')
		except:
			print "*** Warning! Can't open %s" % filespath+TAG_FILE[tag]
			continue
		data= passfile.read()
	
	if DEBUG:
		passport.HexPrint(data)
	outfile= open(tempfiles+TAG_FILE[tag],'wb+')
	outfile.write(data)
	outfile.flush()
	outfile.close()
	print '  Stored in', tempfiles+TAG_FILE[tag]
	# special cases
	if tag == EF_SOD:
		# extract DER file (should be at offset 4 - if not, use sod.py to find it in EF_SOD.BIN
		# temporary evil hack until I have time to decode EF.SOD properly
		outfile= open(tempfiles+"EF_SOD.TMP",'wb+')
		outfile.write(data[4:])
		outfile.flush()
		outfile.close()
		exitstatus= os.system("openssl pkcs7 -text -print_certs -in %sEF_SOD.TMP -inform DER" % tempfiles)
		if not exitstatus:
			exitstatus= os.system("openssl pkcs7 -in %sEF_SOD.TMP -out %sEF_SOD.PEM -inform DER" % (tempfiles,tempfiles))
			exitstatus= os.system("openssl pkcs7 -text -print_certs -in %sEF_SOD.PEM" % tempfiles)
			print 
			print 'Certificate stored in %sEF_SOD.PEM' % tempfiles
	if tag == EF_DG1:
		mrz= decode_ef_dg1(data)
	if tag == EF_DG2:
		dg2_features= decode_ef_dg2(data)
	if tag == EF_DG7:
		decode_ef_dg7(data)

#initialise app if we are going to WRITE JMRTD
if Jmrtd:
	if not FILES:
		filespath=tempfiles
		print
		raw_input('Please replace passport with a JMRTD or vonJeek emulator card and press ENTER when ready...')
	if (not passport.hsselect('08', 'A') and not passport.hsselect('08', 'B')) or not passport.iso_7816_select_file(passport.AID_MRTD,passport.ISO_7816_SELECT_BY_NAME,'0C'):
		print "Couldn't select JMRTD!"
		os._exit(True)
	print "Initialising JMRTD or vonJeek..."
	if STRIP_INDEX:
		print 'Stripping AA & EAC files'
		print 'old EF.COM: '+raw_efcom.encode('hex')
		# DG.COM tag & length
		total_length= ord(raw_efcom[1])
		new_total_length= ord(raw_efcom[1])
		i= 2
		tmp= ''
		while i-2 < total_length-1:
			# next tag
			tag= raw_efcom[i]
			tmp+= raw_efcom[i]
			# not sure how to distinguish 2-byte tags...
			if raw_efcom[i]==chr(0x5F) or  raw_efcom[i]==chr(0x7F):
				i+= 1
				tag+= raw_efcom[i]
				tmp+= raw_efcom[i]
			i+= 1
			length= ord(raw_efcom[i])
			i+= 1
			if tag=='5C'.decode('hex'):
				# Keeping only known files in the tag index
				oldindex=raw_efcom[i:i+length]
				clearDGs=[chr(0x61), chr(0x75), chr(0x67), chr(0x6b), chr(0x6c), chr(0x6d), chr(0x63)]
				newindex=''.join(filter(lambda x: x in clearDGs, list(oldindex)))
				newlength=len(newindex)
				tmp+= chr(newlength)+newindex
				i+= newlength
				# Fixing total length:
				new_total_length= total_length-(length-newlength)
			else:
				tmp+= chr(length)+raw_efcom[i:i+length]
			i+= length
		raw_efcom= raw_efcom[0]+chr(new_total_length)+tmp
		print 'new EF.COM: '+raw_efcom.encode('hex')
		eflist= decode_ef_com(raw_efcom)
		eflist.insert(0,EF_SOD)
		eflist.insert(0,EF_COM)
	for tag in eflist:
		print 'Reading:', TAG_NAME[tag]
		if tag == EF_COM and STRIP_INDEX:
			data= raw_efcom
		else:
			try:
				passfile= open(filespath+TAG_FILE[tag],'rb')
			except:
				print "*** Warning! Can't open %s" % filespath+TAG_FILE[tag]
				continue
			data= passfile.read()
		print "Creating JMRTD", TAG_NAME[tag], "Length", len(data)
		jmrtd_create_file(TAG_FID[tag],len(data))
		print "Writing JMRTD", TAG_NAME[tag]
		jmrtd_write_file(TAG_FID[tag],data)
	# set private key
	# second line of MRZ is second half of decoded mrz from DG1
	passport.MRPmrzl(mrz[len(mrz) / 2:])
	print "Setting 3DES key"
	jmrtd_personalise(mrz[FieldKeys[0]:FieldKeys[0]+9],mrz[FieldKeys[1]:FieldKeys[1]+6],mrz[FieldKeys[2]:FieldKeys[2]+6])
	print "JMRTD/vonJeek 3DES key set to: " + mrz[FieldKeys[0]:FieldKeys[0]+9] + mrz[FieldKeys[1]:FieldKeys[1]+6] + mrz[FieldKeys[2]:FieldKeys[2]+6]
if JmrtdLock:
	jmrtd_lock()

# image read is nasty hacky bodge to see if image display without interpreting the headers
# start of image location may change - look for JPEG header bytes 'FF D8 FF E0'
# german is JP2 format, not JPG - look for '00 00 00 0C 6A 50'
# in /tmp/EF_DG2.BIN

def do_command(func, *args, **kw):
	def _wrapper(*wargs):
		return func(*(wargs + args), **kw)
	return _wrapper

# display data and image in gui window
Style= 'Arrow'
if not Nogui:
	root = Tk()

	font= 'fixed 22'
	fonta= 'fixed 22'

	frame = Frame(root, colormap="new", visual='truecolor').grid()
	root.title('%s (RFIDIOt v%s)' % (myver,passport.VERSION))
	if Filetype == "JP2":
		# nasty hack to deal with JPEG 2000 until PIL support comes along
		exitstatus= os.system("convert %sJP2 %sJPG" % (tempfiles+'EF_DG2.',tempfiles+'EF_DG2.'))
		print "      (converted %sJP2 to %sJPG for display)" % (tempfiles+'EF_DG2.',tempfiles+'EF_DG2.')
		if exitstatus:
			print 'Could not convert JPEG 2000 image (%d) - please install ImageMagick' % exitstatus
			os._exit(True)
		elif Display_DG7:
			os.system("convert %sJP2 %sJPG" % (tempfiles+'EF_DG7.',tempfiles+'EF_DG7.'))
			print "      (converted %sJP2 to %sJPG for display)" % (tempfiles+'EF_DG7.',tempfiles+'EF_DG7.')
		Filetype= 'JPG'
	imagedata = ImageTk.PhotoImage(file=tempfiles + 'EF_DG2.' + Filetype)
	canvas= Canvas(frame, height= imagedata.height(), width= imagedata.width())
	canvas.grid(row= 3, sticky= NW, rowspan= 20)
	canvasimage= canvas.create_image(0,0,image=imagedata, anchor=NW)
	featurebutton= Checkbutton(frame, text="Show Features", command=do_command(drawfeatures,canvas,dg2_features))
	featurebutton.grid(row= 1, column=0, sticky= W, rowspan= 1)
	featurestyle= Radiobutton(frame, text="Arrow",command=do_command(changestyle,"Arrow",canvas,dg2_features))
	featurestyle.grid(row= 1, column=0, rowspan= 1)
	featurestyle.select()
	featurestyle2= Radiobutton(frame, text="Cross",command=do_command(changestyle,"Cross",canvas,dg2_features))
	featurestyle2.grid(row= 2, column=0, rowspan= 1)
	featurestyle2.deselect()
	featurestyle3= Radiobutton(frame, text="Circle ",command=do_command(changestyle,"Circle",canvas,dg2_features))
	featurestyle3.grid(row= 1, column=0, rowspan= 1, sticky= E)
	featurestyle3.deselect()
	featurestyle4= Radiobutton(frame, text="Target",command=do_command(changestyle,"Target",canvas,dg2_features))
	featurestyle4.grid(row= 2, column=0, rowspan= 1, sticky= E)
	featurestyle4.deselect()
	quitbutton= Button(frame, text="Quit", command=root.quit)
	quitbutton.grid(row= 1, column=3, sticky= NE, rowspan= 2)
	Label(frame, text='Type').grid(row= 1, sticky= W, column= 1)
	Label(frame, text=DOCUMENT_TYPE[DocumentType], font= font).grid(row= 2, sticky= W, column= 1)
	row= 3
	for item in Fields:
		Label(frame, text=FieldNames[item]).grid(row= row, sticky= W, column= 1)
		row += 1
		mrzoffset= 0
		for x in range(item):
			mrzoffset += FieldLengths[x]
		if FieldNames[item] == "Issuing State or Organisation" or FieldNames[item] == "Nationality":
			Label(frame, text= mrzspaces(mrz[mrzoffset:mrzoffset + FieldLengths[item]],' ') + '  ' + passport.ISO3166CountryCodesAlpha[mrzspaces(mrz[mrzoffset:mrzoffset + FieldLengths[item]],'')], font= font).grid(row= row, sticky= W, column= 1)
		else:
			Label(frame, text=mrzspaces(mrz[mrzoffset:mrzoffset + FieldLengths[item]],' '), font= font).grid(row= row, sticky= W, column= 1)
		row += 1
	Label(frame, text='  ' + mrz[:len(mrz) / 2], font= fonta, justify= 'left').grid(row= row, sticky= W, columnspan= 4)
	row += 1
	Label(frame, text='  ' + mrz[len(mrz) / 2:], font= fonta, justify= 'left').grid(row= row, sticky= W, columnspan= 4)
	row += 1
	if Display_DG7:
		im = Image.open(tempfiles + 'EF_DG7.' + Filetype)
		width, height = im.size
		im=im.resize((300, 300 * height / width))
		pic=ImageTk.PhotoImage(im)
		width, height = im.size
		signcanvas= Canvas(frame, height= height, width= width)
		signcanvas.create_image(0,0,image=pic, anchor=NW)
		signcanvas.grid(row= row, sticky= NW, columnspan=4)
	row += 1
	Label(frame, text='http://rfidiot.org').grid(row= row, sticky= W, column= 1)
	root.mainloop()
passport.shutdown()
os._exit(False)

########NEW FILE########
__FILENAME__ = multiselect
#!/usr/bin/python


#  multiselect.py - continuously select card and display ID
# 
#  Adam Laurie <adam@algroup.co.uk>
#  http://rfidiot.org/
# 
#  This code is copyright (c) Adam Laurie, 2006, All rights reserved.
#  For non-commercial use only, the following terms apply - for all other
#  uses, please contact the author:
#
#    This code is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#


import rfidiot
import sys
import os
import time
import string

try:
        card= rfidiot.card
except:
        os._exit(True)

args= rfidiot.args

card.info('multiselect v0.1n')

# force card type if specified
if len(args) == 1:
        if not card.settagtype(args[0]):
		print 'Could not set tag type'
		os._exit(True)
else:
        card.settagtype(card.ALL)

while 42:
	if card.select('A') or card.select('B'):
		print '    Tag ID: ' + card.uid,
		if (card.readertype == card.READER_ACG and string.find(card.readername,"LFX") == 0):
			print "    Tag Type:" + card.LFXTags[card.tagtype]
		else:
			print
	else:
		print '    No card present\r',
		sys.stdout.flush()

########NEW FILE########
__FILENAME__ = nfcid
#!/usr/bin/python

#
# NFC ID.py - Python code for Identifying NFC cards
# version 0.1
# Nick von Dadelszen (nick@lateralsecurity.com)
# Lateral Security (www.lateralsecurity.com)

#
# This code is copyright (c) Lateral Security, 2011, All rights reserved.
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
#   You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

#import RFIDIOtconfig
import sys
import os
import pyandroid
import datetime

Verbose= True
Quiet= True

aidlist= 	[
		['MASTERCARD',		'a0000000041010'],
		['MASTERCARD',		'a0000000049999'],
		['VISA',		'a000000003'],
		['VISA Debit/Credit',	'a0000000031010'],
		['VISA Credit',		'a000000003101001'],
		['VISA Debit',		'a000000003101002'],
		['VISA Electron',	'a0000000032010'],
		['VISA V Pay',		'a0000000032020'],
		['VISA Interlink',	'a0000000033010'],
		['VISA Plus',		'a0000000038010'],
		['VISA ATM',		'a000000003999910'],
		['Maestro',		'a0000000043060'],
		['Maestro UK',		'a0000000050001'],
		['Maestro TEST',	'b012345678'],
		['Self Service',	'a00000002401'],
		['American Express',	'a000000025'],
		['ExpressPay',		'a000000025010701'],
		['Link',		'a0000000291010'],
	    ['Alias AID',		'a0000000291010'],
		['Cirrus',		'a0000000046000'],
		['Snapper Card',		'D4100000030001'],		
		['Passport',		'A0000002471001'],		
	    	]


n = pyandroid.Android()

while(42):
	uid = n.select()
	print 'GMT Timestamp: ' + str(datetime.datetime.now())

	if not Quiet:
		print '\nID: ' + uid
		print '  Data:'

	current = 0
	cc_data = False

	while current < len(aidlist):
		if Verbose:
			print 'Trying AID: '+ aidlist[current][0]  + ':' + aidlist[current][1]
		apdu = '00A4040007' + aidlist[current][1]
		r = n.sendAPDU(apdu)
		#print r
		#print r[-4:]	
		if not r[-4:] == '9000':
			apdu = apdu + '00'
			r = n.sendAPDU(apdu)
			#print r
			#print r[-4:]

		if r[-4:] == '9000':
			#print card.data + card.errorcode
			uid = uid[:-1]
			n.sendResults("Card found-UID: " + uid + "-Card type: " + aidlist[current][0])
			break
			
		current += 1	

	if not Quiet:			
		print 'Ending now ...'
	n.deconfigure()
	print 


########NEW FILE########
__FILENAME__ = pn532emulate
#!/usr/bin/python

#  pn532emulate.py - switch NXP PN532 reader chip into TAG emulation mode
# 
#  Adam Laurie <adam@algroup.co.uk>
#  http://rfidiot.org/
# 
#  This code is copyright (c) Adam Laurie, 2009, All rights reserved.
#  For non-commercial use only, the following terms apply - for all other
#  uses, please contact the author:
#
#    This code is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#



import rfidiot
from rfidiot.pn532 import *
import sys
import os

try:
        card= rfidiot.card
except:
        os._exit(True)

args= rfidiot.args
help= rfidiot.help

card.info('pn532emulate v0.1d')

if help or len(args) < 6: 
	print sys.argv[0] + ' - Switch NXP PN532 chip into emulation mode'
	print
	print 'Usage: ' + sys.argv[0] + ' <MODE> <SENS_RES> <NFCID1t> <SEL_RES> <NFCID2t> <PAD> <SYSTEM_CODE> <NFCID3t> [General Bytes] [Historical Bytes]'
	print
	print '  The NXP PN532 chip inside some readers (such as ACS/Tikitag) are capable of emulating the following tags:'
	print
	print '    ISO-14443-3'
	print '    ISO-14443-4'
	print '    Mifare'
	print '    FeliCa'
	print
	print '  Arguments should be specified as follows:'
	print
	print '    MODE (BitField, last 3 bits only):'
	print '        -----000 - Any'
	print '        -----001 - Passive only'
	print '        -----010 - DEP only'
	print '        -----100 - PICC only'
	print
	print '    SENS_RES:'
	print '        2 Bytes, LSB first, as defined in ISO 14443-3.'
	print
	print '    NFCID1t:'
	print "        UID Last 6 HEX digits ('08' will be prepended)."
	print
	print '    SEL_RES:'
	print '        1 Byte, as defined in ISO14443-4.'
	print
	print '    NFCID2t:'
	print "        8 Bytes target NFC ID2. Must start with '01fe'."
	print
	print '    PAD:'
	print '        8 Bytes.'
	print
	print '    SYSTEM_CODE:'
	print '        2 Bytes, returned in the POL_RES frame if the 4th byte of the incoming POL_REQ'
	print '        command frame is 0x01.'
	print 
	print '    NFCID3t:'
	print '        10 Bytes, used in the ATR_RES in case of ATR_REQ received from the initiator.'
	print
	print '    General Bytes:'
	print '        Optional, Max 47 Bytes, to be used in the ATR_RES.'
	print
	print '    Historical Bytes:'
	print '        Optional, Max 48 Bytes, to be used in the ATS when in ISO/IEC 14443-4 PICC'
	print '        emulation mode.'
	print 
	print '  Example:'
	print
	print '    ' + sys.argv[0] + ' 00 0800 dc4420 60 01fea2a3a4a5a6a7c0c1c2c3c4c5c6c7ffff aa998877665544332211 00 52464944494f7420504e353332'
	print
	print '    In ISO/IEC 14443-4 PICC emulation mode, the emulator will wait for initiator, then wait for an APDU,'
	print "    to which it will reply '9000' and exit."
	print
	os._exit(True)

if not card.readersubtype == card.READER_ACS:
	print '  Reader type not supported!'
	os._exit(True)

# switch off auto-polling (for ACS v1 firmware only) (doesn't seem to help anyway!)
#if not card.acs_send_apdu(card.PCSC_APDU['ACS_DISABLE_AUTO_POLL']):
#	print '  Could not disable auto-polling'
#	os._exit(True)

if card.acs_send_apdu(PN532_APDU['GET_PN532_FIRMWARE']):
        print '  NXP PN532 Firmware:'
	pn532_print_firmware(card.data)

if card.acs_send_apdu(PN532_APDU['GET_GENERAL_STATUS']):
	pn532_print_status(card.data)

mode= [args[0]]
sens_res= [args[1]]
uid= [args[2]]
sel_res= [args[3]]
felica= [args[4]]
nfcid=  [args[5]]
try:
	lengt= ['%02x' % (len(args[6]) / 2)]
	gt= [args[6]]
except:
	lengt= ['00']
	gt= ['']
try:
	lentk= ['%02x' % (len(args[7]) / 2)]
	tk= [args[7]]
except:
	lentk= ['00']
	tk= ['']

print '  Waiting for activation...'
card.acs_send_apdu(card.PCSC_APDU['ACS_LED_RED'])
status= card.acs_send_apdu(PN532_APDU['TG_INIT_AS_TARGET']+mode+sens_res+uid+sel_res+felica+nfcid+lengt+gt+lentk+tk)
if not status or not card.data[:4] == 'D58D':
		print 'Target Init failed:', card.errorcode
		os._exit(True)
mode= int(card.data[4:6],16)
baudrate= mode & 0x70
print '  Emulator activated:'
print '         UID: 08%s' % uid[0]
print '    Baudrate:', PN532_BAUDRATES[baudrate]
print '        Mode:',
if mode & 0x08:
	print 'ISO/IEC 14443-4 PICC'
if mode & 0x04:
	print 'DEP'
framing= mode & 0x03
print '     Framing:', PN532_FRAMING[framing]
print '   Initiator:', card.data[6:]
print

print '  Waiting for APDU...'
status= card.acs_send_apdu(PN532_APDU['TG_GET_DATA'])
if not status or not card.data[:4] == 'D587':
		print 'Target Get Data failed:', card.errorcode
		print 'Data:',card.data
		os._exit(True)
errorcode= int(card.data[4:6],16)
if not errorcode == 0x00:
	print 'Error:',PN532_ERRORS[errorcode]
	os._exit(True)
print '<<', card.data[6:]

print '>>', card.ISO_OK
status= card.acs_send_apdu(PN532_APDU['TG_SET_DATA']+[card.ISO_OK])
if not status:
	os._exit(True)
else:
	os._exit(False)

########NEW FILE########
__FILENAME__ = pn532mitm
#!/usr/bin/python

#  pn532mitm.py - NXP PN532 Man-In-The_Middle - log conversations between TAG and external reader
# 
#  Adam Laurie <adam@algroup.co.uk>
#  http://rfidiot.org/
# 
#  This code is copyright (c) Adam Laurie, 2009, All rights reserved.
#  For non-commercial use only, the following terms apply - for all other
#  uses, please contact the author:
#
#    This code is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#


import rfidiot
from rfidiot.pn532 import *
import sys
import os
import string
import socket
import time
import random
import operator

# try to connect to remote host. if that fails, alternately listen and connect.
def connect_to(host,port,type):
	peer= socket.socket()
	random.seed()
	first= True
	while 42:
		peer.settimeout(random.randint(1,10))	
		print '  Paging %s %s                    \r' % (host, port),
		sys.stdout.flush()
		time.sleep(1)
		if peer.connect_ex((host,port)) == 0:
			print '  Connected to %s port %d                  ' % (host,port)
			send_data(peer,type)
			data= recv_data(peer)
			connection= peer
			break
		try:
			print '  Listening for REMOTE on port %s              \r' % port,
			sys.stdout.flush()
			if first:
				peer.bind(('0.0.0.0',port))
				peer.listen(1)
				first= False
			conn, addr= peer.accept()
			if conn:
				print '  Connected to %s port %d                  ' % (addr[0],addr[1])
				data= recv_data(conn)
				send_data(conn,type)
				connection= conn
				break
		except socket.timeout:
			pass
		except Exception, exc:
			print 'Could not open local socket:                    '
			print exc
			os._exit(True)
	if data == type:
		print '  Handshake failed - both ends are set to', type
		time.sleep(1)
		connection.close()
		os._exit(True)
	print '  Remote is', data
	print
	return connection

# send data with 3 digit length and 2 digit CRC
def send_data(host, data):
	lrc= 0
	length= '%03x' % (len(data) + 2)
	for x in length + data:
		lrc= operator.xor(lrc,ord(x))
	host.send(length)
	host.send(data)
	host.send('%02x' % lrc)

# receive data of specified length and check CRC
def recv_data(host):
	out= ''
	while len(out) < 3:
		out += host.recv(3 - len(out))
	length= int(out,16)
	lrc= 0
	for x in out:
		lrc= operator.xor(lrc,ord(x))
	out= ''
	while len(out) < length:
		out += host.recv(length - len(out))
	for x in out[:-2]:
		lrc= operator.xor(lrc,ord(x))
	if not lrc == int(out[-2:],16):
		print '  Remote socket CRC failed!'
		host.close()
		os._exit(True)
	return out[:-2]

try:
        card= rfidiot.card
except:
        os._exit(True)

args= rfidiot.args
help= rfidiot.help

card.info('pn532mitm v0.1e')

if help or len(args) < 1: 
	print sys.argv[0] + ' - NXP PN532 Man-In-The-Middle'
	print
	print '\tUsage: ' + sys.argv[0] + " <EMULATOR|REMOTE> [LOG FILE] ['QUIET']"
	print
	print '\t  Default PCSC reader will be the READER. Specify reader number to use as an EMULATOR as'
	print '\t  the <EMULATOR> argument.'
	print
	print "\t  To utilise a REMOTE device, use a string in the form 'emulator:HOST:PORT' or 'reader:HOST:PORT'."
	print
	print '\t  COMMANDS and RESPONSES will be relayed between the READER and the EMULATOR, and relayed'
	print '\t  traffic will be displayed (and logged if [LOG FILE] is specified).'
	print
	print "\t  If the 'QUIET' option is specified, traffic log will not be displayed on screen."
	print 
	print '\t  Logging is in the format:'
	print
	print '\t    << DATA...        - HEX APDU received by EMULATOR and relayed to READER'
	print '\t    >> DATA... SW1SW2 - HEX response and STATUS received by READER and relayed to EMULATOR' 
	print
	print '\t  Examples:'
	print
	print '\t    Use device no. 2 as the READER and device no. 3 as the EMULATOR:'
	print
	print '\t      ' + sys.argv[0] + ' -r 2 3'
	print
	print '\t    Use device no. 2 as the EMULATOR and remote system on 192.168.1.3 port 5000 as the READER:'
	print
	print '\t      ' + sys.argv[0] + ' -r 2 reader:192.168.1.3:5000'
	print
	os._exit(True)

logging= False
if len(args) > 1:
	try:
		logfile= open(args[1],'r')
		x= string.upper(raw_input('  *** Warning! File already exists! Overwrite (y/n)? '))
		if not x == 'Y':
			os._exit(True)
		logfile.close()
	except:
		pass
	try:
		logfile= open(args[1],'w')
		logging= True
	except:
		print "  Couldn't create logfile:", args[1]
		os._exit(True)

try:
	if args[2] == 'QUIET':
		quiet= True
except:
	quiet= False

if len(args) < 1:
	print 'No EMULATOR or REMOTE specified'
	os._exit(True)

# check if we are using a REMOTE system
remote= ''
remote_type= ''
if string.find(args[0],'emulator:') == 0:
	remote= args[0][9:]
	em_remote= True
	remote_type= 'EMULATOR'
else:
	em_remote= False
if string.find(args[0],'reader:') == 0:
	remote= args[0][7:]
	rd_remote= True
	remote_type= 'READER'
	emulator= card
else:
	rd_remote= False


if remote:
	host= remote[:string.find(remote,':')]
	port= int(remote[string.find(remote,':') + 1:])
	connection= connect_to(host, port, remote_type)
else:
	try:
		readernum= int(args[0])
		emulator= rfidiot.RFIDIOt.rfidiot(readernum,card.readertype,'','','','','','')
		print '  Emulator:',
		emulator.info('')
		if not emulator.readersubtype == card.READER_ACS:
			print "EMULATOR is not an ACS"
			os._exit(True)
	except:
		print "Couldn't initialise EMULATOR on reader", args[0]
		os._exit(True) 

# always check at least one device locally
if not card.readersubtype == card.READER_ACS:
	print "READER is not an ACS"
	if remote:
		connection.close()
	os._exit(True)

if card.acs_send_apdu(PN532_APDU['GET_PN532_FIRMWARE']):
	if remote:
		send_data(connection,card.data)
		print '  Local NXP PN532 Firmware:'
	else:
		print '  Reader NXP PN532 Firmware:'
	if not card.data[:4] == PN532_OK:
		print '  Bad data from PN532:', card.data
		if remote:
			connection.close()
		os._exit(True)
	else:
		pn532_print_firmware(card.data)

if remote:
	data= recv_data(connection)
	print '  Remote NXP PN532 Firmware:'
else:
	if emulator.acs_send_apdu(PN532_APDU['GET_PN532_FIRMWARE']):
		data= card.data
	emulator.acs_send_apdu(card.PCSC_APDU['ACS_LED_ORANGE'])
	print '  Emulator NXP PN532 Firmware:'

if not data[:4] == PN532_OK:
	print '  Bad data from PN532:', data
	if remote:
		connection.close()
	os._exit(True)
else:
	pn532_print_firmware(data)

if not remote or remote_type == 'EMULATOR':
	card.waitfortag('  Waiting for source TAG...')
	full_uid= card.uid
	sens_res= [card.sens_res]
	sel_res= [card.sel_res]
if remote:
	if remote_type == 'READER':
		print '  Waiting for remote TAG...'
		connection.settimeout(None)
		full_uid= recv_data(connection)
		sens_res= [recv_data(connection)]
		sel_res= [recv_data(connection)]
	else:
		send_data(connection,card.uid)
		send_data(connection,card.sens_res)
		send_data(connection,card.sel_res)
		
mode= ['00']
print '         UID:', full_uid
uid= [full_uid[2:]]
print '    sens_res:', sens_res[0]
print '     sel_res:', sel_res[0]
print
felica= ['01fea2a3a4a5a6a7c0c1c2c3c4c5c6c7ffff']
nfcid=  ['aa998877665544332211']
try:
	lengt= ['%02x' % (len(args[6]) / 2)]
	gt= [args[6]]
except:
	lengt= ['00']
	gt= ['']
try:
	lentk= ['%02x' % (len(args[7]) / 2)]
	tk= [args[7]]
except:
	lentk= ['00']
	tk= ['']

if not remote or remote_type == 'EMULATOR':
	if card.acs_send_apdu(PN532_APDU['GET_GENERAL_STATUS']):
		data= card.data
if remote:
	if remote_type == 'EMULATOR':
		send_data(connection,data)
	else:
		data= recv_data(connection)

tags= pn532_print_status(data)
if tags > 1:
	print '  Too many TAGS to EMULATE!'
	if remote:
		connection.close()
	os._exit(True)

#emulator.acs_send_apdu(emulator.PCSC_APDU['ACS_SET_PARAMETERS']+['14'])

if not remote or remote_type == 'READER':
	print '  Waiting for EMULATOR activation...'
	status= emulator.acs_send_apdu(PN532_APDU['TG_INIT_AS_TARGET']+mode+sens_res+uid+sel_res+felica+nfcid+lengt+gt+lentk+tk)
	if not status or not emulator.data[:4] == 'D58D':
		print 'Target Init failed:', emulator.errorcode, emulator.ISO7816ErrorCodes[emulator.errorcode]
		if remote:
			connection.close()
		os._exit(True)
	data= emulator.data
if remote:
	if remote_type == 'READER':
		send_data(connection,data)
	else:
		print '  Waiting for remote EMULATOR activation...'
		connection.settimeout(None)
		data= recv_data(connection)

mode= int(data[4:6],16)
baudrate= mode & 0x70
print '  Emulator activated:'
print '         UID: 08%s' % uid[0]
print '    Baudrate:', PN532_BAUDRATES[baudrate]
print '        Mode:',
if mode & 0x08:
	print 'ISO/IEC 14443-4 PICC'
if mode & 0x04:
	print 'DEP'
framing= mode & 0x03
print '     Framing:', PN532_FRAMING[framing]
initiator= data[6:]
print '   Initiator:', initiator
print

print '  Waiting for APDU...'
started= False
try:
	while 42:
		# wait for emulator to receive a command
		if not remote or remote_type == 'READER':
			status= emulator.acs_send_apdu(PN532_APDU['TG_GET_DATA'])
			data= emulator.data
			#if not status or not emulator.data[:4] == 'D587':
			if not status:
				print 'Target Get Data failed:', emulator.errorcode, emulator.ISO7816ErrorCodes[emulator.errorcode]
				print 'Data:', emulator.data
				if remote:
					connection.close()
				os._exit(True)
		if remote:
			if remote_type == 'READER':
				send_data(connection,data)
			else:
				connection.settimeout(None)
				data= recv_data(connection)
		errorcode= int(data[4:6],16)
		if not errorcode == 0x00:
			if remote:
				connection.close()
			if errorcode == 0x29:
				if logging:
					logfile.close()
				print '  Session ended: EMULATOR released by Initiator'
				if not remote or remote_type == 'READER':
					emulator.acs_send_apdu(card.PCSC_APDU['ACS_LED_GREEN'])
				os._exit(False)
			print 'Error:',PN532_ERRORS[errorcode]
			os._exit(True)
		if not quiet:
			print '<<', data[6:]
		else:
			if not started:
				print '  Logging started...'
				started= True
		if logging:
			logfile.write('<< %s\n' % data[6:])
			logfile.flush()
		# relay command to tag
		if not remote or remote_type == 'EMULATOR':
			status= card.acs_send_direct_apdu(data[6:])
			data= card.data
			errorcode= card.errorcode
		if remote:
			if remote_type == 'EMULATOR':
				send_data(connection,data)
				send_data(connection,errorcode)
			else:
				data= recv_data(connection)
				errorcode= recv_data(connection)
		if not quiet:
			print '>>', data, errorcode
		if logging:
			logfile.write('>> %s %s\n' % (data,errorcode))
			logfile.flush
		# relay tag's response back via emulator
		if not remote or remote_type == 'READER':
			status= emulator.acs_send_apdu(PN532_APDU['TG_SET_DATA']+[data]+[errorcode])
except:
		if logging:
			logfile.close()
		print '  Session ended with possible errors'
		if remote:
			connection.close()
		if not remote or remote_type == 'READER':
			emulator.acs_send_apdu(card.PCSC_APDU['ACS_LED_GREEN'])
		os._exit(True)

########NEW FILE########
__FILENAME__ = q5reset
#!/usr/bin/python

#  q5reset.py - plooking too hard on your Q5? this should sort it out.
# 
#  Adam Laurie <adam@algroup.co.uk>
#  http://rfidiot.org/
# 
#  This code is copyright (c) Adam Laurie, 2006, All rights reserved.
#  For non-commercial use only, the following terms apply - for all other
#  uses, please contact the author:
#
#    This code is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#


import rfidiot
import sys
import os
import string

try:
	card= rfidiot.card
except:
	print "Couldn't open reader!"
	os._exit(True)

args= rfidiot.args
help= rfidiot.help

card.info('q5reset v0.1g')

# standard config block
CFB='e601f004'
B1='ff801bc2'
B2='52500006'

if help or len(args) == 0 or len(args) > 2:
	print sys.argv[0] + ' - sooth and heal a sorely mistreated Q5 tag'
	print 'Usage: ' + sys.argv[0] + ' [OPTIONS] <CONTROL> [ID]'
	print
	print '\tIf the optional 8 HEX-digit ID argument is specified, the' 
	print '\tQ5 tag will be programmed to that ID. Otherwise, only the' 
	print '\tcontrol block will be written. If the literal \'ID\' is used'
	print '\tthen a default ID will be programmed.'
	print
	print '\tNote that not all Q5 chips allow programming of their ID!'
	print
	os._exit(True)

if args[0] == 'CONTROL':
       	card.settagtype(card.ALL)
       	while True:
               	print
               	card.select()
               	print '  Card ID: ' + card.uid
               	x= string.upper(raw_input('  *** Warning! This will overwrite TAG! Place defective card and proceed (y/n)? '))
               	if x == 'N':
               		os._exit(False)
       		if x == 'Y':
			break
	print 'Writing...'
       	card.settagtype(card.Q5)
	card.select()
	if not card.writeblock(0,CFB):
		print 'Write failed!'
		os._exit(True)
	else:
		if len(args) > 1:
			if not args[1] == 'ID':
				out= card.Unique64Bit(card.HexToQ5(args[1] + '00'))
				B1= '%08x' % int(out[:32],2)
				B2= '%08x' % int(out[32:64],2)
			if not card.writeblock(1,B1) or not card.writeblock(2,B2):
				print 'Write failed!'
				os._exit(True)	 	
	print 'Done!'
       	card.select()
       	print '  Card ID: ' + card.data
	card.settagtype(card.ALL)
os._exit(False)

########NEW FILE########
__FILENAME__ = readlfx
#!/usr/bin/python

#  readlfx.py - read all sectors from a LFX reader
# 
#  Adam Laurie <adam@algroup.co.uk>
#  http://rfidiot.org/
# 
#  This code is copyright (c) Adam Laurie, 2006, All rights reserved.
#  For non-commercial use only, the following terms apply - for all other
#  uses, please contact the author:
#
#    This code is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#

# usage: readlfx [KEY]
#
#        specifiy KEY for protected tags. If not specified, TRANSPORT key will be tried.

import rfidiot
import sys
import os

try:
        card= rfidiot.card
except:
	print "Couldn't open reader!"
        os._exit(True)

args= rfidiot.args
help= rfidiot.help

Q5Mod= { '000':'Manchester',\
	 '001':'PSK 1',\
	 '010':'PSK 2',\
	 '011':'PSK 3',\
	 '100':'FSK 1 (a = 0)',\
	 '101':'FSK 2 (a = 0)',\
	 '110':'Biphase',\
	 '111':'NRZ / direct'}

card.info('readlfx v0.1m')

# force card type if specified
if len(args) > 0:
	print 'Setting tag type:', args[0]
	card.settagtype(args[0])
else:
	card.settagtype(card.ALL)
card.select()
ID= card.uid
print 'Card ID: ' + ID
print 'Tag type: ' + card.LFXTags[card.tagtype]

# set key if specified
if len(args) > 1:
	key= args[1]
else:
	key= ''

# Login to Hitag2
if card.tagtype == card.HITAG2 and card.readertype == card.READER_ACG:
	if not key:
		key= card.HITAG2_TRANSPORT_RWD
	print ' Logging in with key: ' + key
	if not card.login('','',key):
		print 'Login failed!'
		os._exit(True)

# Interpret EM4x05 ID structure
if card.tagtype == card.EM4x05:
	card.FDXBIDPrint(ID)

# Q5 cards can emulate other cards, so check if this one responds as Q5
if card.tagtype == card.EM4x02 or card.tagtype == card.Q5 or card.tagtype ==  card.EM4x05:
	print '  Checking for Q5'
	card.settagtype(card.Q5)
	card.select()
	Q5ID= card.uid
	if card.tagtype == card.Q5:
		print '    Q5 ID: ' + Q5ID
		print
		card.readblock(0)
		print '    Config Block: ',
		print card.ToHex(card.binary)
		print '    Config Binary: ',
		configbin= card.ToBinaryString(card.binary)
		print configbin
		print '          Reserved: ' + configbin[:12]
		print '       Page Select: ' + configbin[12]
		print '        Fast Write: ' + configbin[13]
		print '  Data Bit Rate n5: ' + configbin[14]
		print '  Data Bit Rate n4: ' + configbin[15]
		print '  Data Bit Rate n3: ' + configbin[16]
		print '  Data Bit Rate n2: ' + configbin[17]
		print '  Data Bit Rate n1: ' + configbin[18]
		print '  Data Bit Rate n0: ' + configbin[19]
		print ' (Field Clocks/Bit: %d)' % (2 * int(configbin[14:20],2) + 2)
		print '           Use AOR: ' + configbin[20]
		print '           Use PWD: ' + configbin[21]
		print '  PSK Carrier Freq: ' + configbin[22] + configbin[23]
		print '  Inverse data out: ' + configbin[24]
		print '        Modulation: ' + configbin[25] + configbin[26] + configbin[27] + " (%s)" % Q5Mod[configbin[25] + configbin[26] + configbin[27]]
		print '          Maxblock: ' + configbin[28] + configbin[29] + configbin[30] + " (%d)" % int (configbin[28] + configbin[29] + configbin[30],2)
		print '        Terminator: ' + configbin[31]
		print
		# Emulated ID is contained in 'traceability data'
		print '    Traceability Data 1: ',
		card.readblock(1)
		td1= card.binary
# to test a hardwired number, uncomment following line (and td2 below)
#		td1= chr(0xff) + chr(0x98) + chr(0xa6) + chr(0x4a)
		print card.ToHex(td1)
		print '    Traceability Data 2: ',
		card.readblock(2)
		td2= card.binary
# don't forget to set column parity!
#		td2= chr(0x98) + chr(0xf8) + chr(0xc8) + chr(0x06)
		print card.ToHex(td2)
		print '    Traceability Binary: ',
		tdbin= card.ToBinaryString(td1 + td2)
		print tdbin
		# traceability is broken into 4 bit chunks with even parity
		print
		print '      Header:',
		print tdbin[:9]
		print '                    Parity (even)'
		print '      D00-D03: ' + tdbin[9:13] + ' ' + tdbin[13]
		print '      D10-D13: ' + tdbin[14:18] + ' ' + tdbin[18]
		print '      D20-D23: ' + tdbin[19:23] + ' ' + tdbin[23]
		print '      D30-D33: ' + tdbin[24:28] + ' ' + tdbin[28]
		print '      D40-D43: ' + tdbin[29:33] + ' ' + tdbin[33]
		print '      D50-D53: ' + tdbin[34:38] + ' ' + tdbin[38]
		print '      D60-D63: ' + tdbin[39:43] + ' ' + tdbin[43]
		print '      D70-D73: ' + tdbin[44:48] + ' ' + tdbin[48]
		print '      D80-D83: ' + tdbin[49:53] + ' ' + tdbin[53]
		print '      D90-D93: ' + tdbin[54:58] + ' ' + tdbin[58]
		print '               ' + tdbin[59:63] + ' ' + tdbin[63] + ' Column Parity & Stop Bit'
		# reconstruct data bytes
		d0= chr(int(tdbin[9:13] + tdbin[14:18],2))
		d1= chr(int(tdbin[19:23] + tdbin[24:28],2))
		d2= chr(int(tdbin[29:33] + tdbin[34:38],2))
		d3= chr(int(tdbin[39:43] + tdbin[44:48],2))
		d4= chr(int(tdbin[49:53] + tdbin[54:58],2))
		print
		print '      Reconstructed data D00-D93 (UNIQUE ID): ',
		card.HexPrint(d0 + d1 + d2 + d3 + d4)
		# set ID to Q5ID so block reading works
		ID= Q5ID
		print
	else:
		print '    Native - UNIQUE ID: ' + card.EMToUnique(ID)

sector = 0
while sector < card.LFXTagBlocks[card.tagtype]:
        print ' sector %02x: ' % sector,
	if card.readblock(sector):
		print card.data
	else:
		print 'Read error: ' + card.errorcode
        sector += 1
print

# set reader back to all cards
card.settagtype(card.ALL)
card.select()
print
os._exit(False)

########NEW FILE########
__FILENAME__ = readmifare1k
#!/usr/bin/python

#  readmifare1k.py - read all sectors from a mifare standard tag
# 
#  Adam Laurie <adam@algroup.co.uk>
#  http://rfidiot.org/
# 
#  This code is copyright (c) Adam Laurie, 2006, All rights reserved.
#  For non-commercial use only, the following terms apply - for all other
#  uses, please contact the author:
#
#    This code is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#


import rfidiot
import sys
import os

try:
        card= rfidiot.card
except:
	print "Couldn't open reader!"
        os._exit(True)

card.info('readmifare1k v0.1j')
card.select()
print 'Card ID: ' + card.uid

blocksread= 0
blockslocked= 0
lockedblocks= []

for type in ['AA', 'BB', 'FF']:
	card.select()
	if card.login(0,type,''):
		if card.readMIFAREblock(0):
			card.MIFAREmfb(card.MIFAREdata)
		else:
			print 'Read error: %s %s' % (card.errorcode , card.ISO7816ErrorCodes[card.errorcode])
			os._exit(True)
		print "\nMIFARE data (keytype %s):" % type
		print "\tSerial number:\t\t%s\n\tCheck byte:\t\t%s\n\tManufacturer data:\t%s" % (card.MIFAREserialnumber, card.MIFAREcheckbyte, card.MIFAREmanufacturerdata)
print

sector = 1
while sector < 16:
	locked= True
        for type in ['AA', 'BB', 'FF']:
                print ' sector %02x: Keytype: %s' % (sector,type),
                card.select()
                if card.login(sector * 4,type,''):
			locked= False
			blocksread += 1
			print 'Login OK. Data:'
			print
			print ' ',
			for block in range(4):
				# card.login(sector,type,'')
				if card.readMIFAREblock((sector * 4) + block):
					print card.MIFAREdata,
		                	sys.stdout.flush()           
				else:
					print 'Read error: %s %s' % (card.errorcode , card.ISO7816ErrorCodes[card.errorcode])
					os._exit(True)
			print
			card.MIFAREkb(card.MIFAREdata)
			print "  Access Block User Data Byte: " + card.MIFAREaccessconditionsuserbyte
			print
			print "\tKey A (non-readable):\t%s\n\tKey B:\t\t\t%s\n\tAccess conditions:\t%s" % (card.MIFAREkeyA, card.MIFAREkeyB, card.MIFAREaccessconditions)
			print "\t\tMIFAREC1:\t%s\n\t\tMIFAREC2:\t%s\n\t\tMIFAREC3:\t%s" % (hex(card.MIFAREC1)[2:], hex(card.MIFAREC2)[2:], hex(card.MIFAREC3)[2:])
			print "\t\tMIFAREblock0AC: " + card.MIFAREblock0AC
			print "\t\t\t" + card.MIFAREACDB[card.MIFAREblock0AC]
			print "\t\tMIFAREblock1AC: " + card.MIFAREblock1AC
			print "\t\t\t" + card.MIFAREACDB[card.MIFAREblock1AC]
			print "\t\tMIFAREblock2AC: " + card.MIFAREblock2AC
			print "\t\t\t" + card.MIFAREACDB[card.MIFAREblock2AC]
			print "\t\tMIFAREblock3AC: " + card.MIFAREblock3AC
			print "\t\t\t" + card.MIFAREACKB[card.MIFAREblock3AC]
			print
			continue
		elif card.errorcode != '':
			print 'Login Error: %s %s' % (card.errorcode , card.ISO7816ErrorCodes[card.errorcode])
		elif type == 'FF':
			print 'Login failed'
                print '\r',
		sys.stdout.flush()
	if locked:
		blockslocked += 1
		lockedblocks.append(sector)
        sector += 1
print
print '  Total blocks read: %d' % blocksread
print '  Total blocks locked: %d' % blockslocked
if lockedblocks > 0:
	print '  Locked block numbers:', lockedblocks
os._exit(False)

########NEW FILE########
__FILENAME__ = readmifaresimple
#!/usr/bin/python

#  readmifaresimple.py - read all sectors from a mifare tag
# 
#  Adam Laurie <adam@algroup.co.uk>
#  http://rfidiot.org/
# 
#  This code is copyright (c) Adam Laurie, 2006, All rights reserved.
#  For non-commercial use only, the following terms apply - for all other
#  uses, please contact the author:
#
#    This code is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#

import sys
import os
import rfidiot
import time
import string

try:
	card= rfidiot.card
except:
	print "Couldn't open reader!"
	os._exit(False)

args= rfidiot.args
help= rfidiot.help

blocksread= 0
blockslocked= 0
lockedblocks= []
DEFAULT_KEY= 'FFFFFFFFFFFF'
KEYS= ['FFFFFFFFFFFF','A0A1A2A3A4A5','B0B1B2B3B4B5','000000000000','ABCDEF012345','4D3A99C351DD','1A982C7E459A','D3F7D3F7D3F7','AABBCCDDEEFF']
KEYTYPES=['AA','BB','FF']
DEFAULT_KEYTYPE= 'AA'
BLOCKS_PER_SECT= 4
START_BLOCK= 0
END_BLOCK= 63
CloneData= []
RESET_DATA=    '00000000000000000000000000000000'
RESET_TRAILER= 'FFFFFFFFFFFFFF078069FFFFFFFFFFFF'

if help or len(args) > 6:
        print sys.argv[0] + ' - read mifare tags'
        print 'Usage: ' + sys.argv[0] + ' [START BLOCK] [END BLOCK] [KEY] [KEYTYPE] [COPY|RESET]'
        print
        print '\tRead Mifare sector numbers [START BLOCK] to [END BLOCK], using' 
        print '\t[KEY] to authenticate. Keys can be truncated to \'AA\' for transport' 
        print '\tkey \'A0A1A2A3A4A5\', \'BB\' for transport key \'B0B1B2B3B4B5\' or \'FF\''
        print '\tfor transport key \'FFFFFFFFFFFF\'.' 
	print 
        print '\tSTART BLOCK defaults to 0 and END BLOCK to 63. If not specified, KEY'
	print '\tdefaults to \'FFFFFFFFFFFF\', and KEYTYPE defaults to \'AA\'. All known' 	
	print '\talternative keys are tried in the event of a login failure.'
	print 
	print '\tIf the option \'RESET\' is specified, the card will be programmed to'
	print '\tfactory defaults after reading.'
	print
	print '\tIf the option \'COPY\' is specified, a card will be programmed with'
	print '\twith the data blocks read (note that block 0 cannot normally be written)'
	print
        os._exit(True)

card.info('readmifaresimple v0.1h')

if not card.select():
	card.waitfortag('waiting for Mifare TAG...')

# set options

reset= False
copy= False

try:
	if args[4] == 'RESET':
		reset= True
except:
	pass

try:
	if args[4] == 'COPY':
		copy= True
except:
	pass

if copy:
	try:
		otherkey= args[5]
	except:
		pass

try:
	keytype= string.upper(args[3])
	KEYTYPES.remove(keytype)
	trykeytype= [keytype] + KEYTYPES
except:
	keytype= DEFAULT_KEYTYPE
	trykeytype= KEYTYPES

try:
	key= string.upper(args[2])
	trykey= [key] + KEYS
except:
	key= DEFAULT_KEY
	trykey= KEYS

try:
	endblock= int(args[1])
except:
	endblock= END_BLOCK

try:
	startblock= int(args[0])
except:
	startblock= 0

if not reset:
	print '  Card ID:', card.uid
	print
	print '    Reading from %02d to %02d, key %s (%s)\n' % (startblock, endblock, key, keytype)

# see if key is an abbreviation
# if so, only need to set keytype and login will use transport keys
for d in ['AA','BB','FF']:
	if key == d:
		keytype= key
		key= ''

if len(key) > 12:
	print 'Invalid key: ', key
	os._exit(True)

block= startblock
while block <= endblock and not reset:
	locked= True
        print '    Block %03i:' % block,
	# ACG requires a login only to the base 'sector', so block number must be divided
	# by BLOCKS_PER_SECT
	if card.readertype == card.READER_ACG:
		loginblock= block / BLOCKS_PER_SECT
	else:
		loginblock= block
	loggedin= False
	for y in trykey:
		if loggedin:
			break
		for x in trykeytype:
			if card.login(loginblock,x,y):
				loggedin= True
				goodkey= y
				goodkeytype= x
				break
			else:
				# clear the error
				card.select()

	if loggedin:
		print 'OK (%s %s) Data:' % (goodkey,goodkeytype),
		locked= False
		if card.readMIFAREblock(block):
			blocksread += 1
			print card.MIFAREdata,
			print card.ReadablePrint(card.ToBinary(card.MIFAREdata))
			CloneData += [card.MIFAREdata]
		else:
			print 'Read error: %s %s' % (card.errorcode , card.ISO7816ErrorCodes[card.errorcode])
	else:
		print 'Login error: %s %s' % (card.errorcode , card.ISO7816ErrorCodes[card.errorcode])
		locked= True
		blockslocked += 1
		lockedblocks.append(block)
		# ACG requires re-select to clear error condition after failed login
		if card.readertype == card.READER_ACG:
			card.select()
        block +=  1

if not reset:
	print
	print '  Total blocks read: %d' % blocksread
	print '  Total blocks locked: %d' % blockslocked
	if blockslocked > 0:
		print '  Locked block numbers:', lockedblocks
	print

if not reset and not copy:
	os._exit(False)

raw_input('Place tag to be written and hit <ENTER> to proceed')

while True:
	print
	card.select()
	print '  Card ID: ' + card.uid
	print
	if not reset:
		if keytype == 'AA':
			print '  KeyA will be set to', key + ', KeyB will be set to %s' % otherkey
		else:
			print '  KeyA will be set to %s,' % otherkey, 'KeyB will be set to', key 
	else:
		print '  KeyA will be set to FFFFFFFFFFFF, KeyB will be set to FFFFFFFFFFFF'
	print
	x= string.upper(raw_input('  *** Warning! This will overwrite TAG! Proceed (y/n) or <ENTER> to select new TAG? '))
	if x == 'N':
		os._exit(False)
	if x == 'Y':
		print
		break

block= startblock
outblock= 0
while block <= endblock:
	# block 0 is not writeable
	if block == 0:
		block += 1
		outblock += 1
		continue
        print '    Block %03i: ' % block,
	# ACG requires a login only to the base 'sector', so block number must be divided
	# by BLOCKS_PER_SECT
	if card.readertype == card.READER_ACG:
		loginblock= block / BLOCKS_PER_SECT
	else:
		loginblock= block
	loggedin= False
	if not reset:
		# assume we're writing to a factory blank, so try default keys first
		trykey= KEYS + [key]
		trykeytype= ['AA','BB']
	for y in trykey:
		if loggedin:
			break
		for x in trykeytype:
			if card.login(loginblock,x,y):
				loggedin= True
				goodkey= y
				goodkeytype= x
				break
			else:
				# clear the error
				card.select()

	if loggedin:
		if (block + 1) % 4:
			if reset:
				blockdata= RESET_DATA
			else:
				blockdata= CloneData[outblock]
		else:
			if reset:
				blockdata= RESET_TRAILER 
			else:
				if keytype == 'BB':
					# only ACL is useful from original data
					blockdata= RESET_TRAILER[:12] + CloneData[outblock][12:20] + key
				else:
					# ACL plus KeyB
					blockdata= key + CloneData[outblock][12:20] + otherkey
		print 'OK (%s %s), writing: %s' % (goodkey,goodkeytype,blockdata),
		if card.writeblock(block,blockdata):
			print 'OK'
		else:
			print 'Write error: %s %s' % (card.errorcode , card.ISO7816ErrorCodes[card.errorcode])
	else:
		print 'Login error: %s %s' % (card.errorcode , card.ISO7816ErrorCodes[card.errorcode])
		# ACG requires re-select to clear error condition after failed login
		if card.readertype == card.READER_ACG:
			card.select()
        block +=  1
	outblock += 1
os._exit(False)

########NEW FILE########
__FILENAME__ = readmifareultra
#!/usr/bin/python

#  readmifareultra.py - read all sectors from a Ultralight tag
# 
#  Keith Howell <kch@kch.net>
#    built on the code by:
#  Adam Laurie <adam@algroup.co.uk>
#  http://rfidiot.org/
# 
#  This code is copyright (c) Adam Laurie, 2006, All rights reserved.
#  For non-commercial use only, the following terms apply - for all other
#  uses, please contact the author:
#
#    This code is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#


import rfidiot
import sys
import os

try:
        card= rfidiot.card
except:
	print "Couldn't open reader!"
        os._exit(True)

help= rfidiot.help

if help:
        print sys.argv[0] + ' - read mifare ultralight tags'
        print 'Usage: ' + sys.argv[0]
        print
	os._exit(True)

card.info('readmifareultra v0.1b')
card.waitfortag('Waiting for Mifare Ultralight...')

blocks=16

print '\n  ID: ' + card.uid
print 'Type: ' + card.tagtype

card.select()
# pull header block information from the tag
if card.readblock(0):
	sn0=card.data[0:2]
	sn1=card.data[2:4]
	sn2=card.data[4:6]
	bcc0=card.data[6:8]
else:
	print 'read error: %s' % card.errorcode

if card.readblock(1):
	sn3=card.data[0:2]
	sn4=card.data[2:4]
	sn5=card.data[4:6]
	sn6=card.data[6:8]
else:
	print 'read error: %s' % card.errorcode

if card.readblock(2):
	bcc1=card.data[0:2]
	internal=card.data[2:4]
	lock0=card.data[4:6]
	lock1=card.data[6:8]
else:
	print 'read error: %s' % card.errorcode

if card.readblock(3):
	otp0=card.data[0:2]
	otp1=card.data[2:4]
	otp2=card.data[4:6]
	otp3=card.data[6:8]
else:
	print 'read error: %s' % card.errorcode

# convert lock bytes to binary for later use
lbits0=card.ToBinaryString(card.ToBinary(lock0))
lbits1=card.ToBinaryString(card.ToBinary(lock1))
lbits=lbits1 + lbits0

y=0
plock=''
for x in range(15,-1,-1):
	plock = lbits[y:y+1] + plock
	y += 1

# show status of the OTP area on the tag
print 'OTP area is',
if int(plock[3:4]) == 1:
	print 'locked and',
else:
	print 'unlocked and',
if int(plock[0:1]) == 1:
	print 'cannot be changed'
else:
	print 'can be changed'

print 'If locked, blocks 4 through 9',
if int(plock[1:2]) == 1:
	print 'cannot be unlocked'
else:
	print 'can be unlocked'

print 'If locked, blocks 0a through 0f',
if int(plock[2:3]) == 1:
	print 'cannot be unlocked'
else:
	print 'can be unlocked'

print '\nTag Data:'
# DATA0 byte starts on page/block 4
for x in range(blocks):
	print '    Block %02x:' % x,
	if card.readblock(x):
		print card.data[:8],
		print card.ReadablePrint(card.ToBinary(card.data[:8])),
		if x > 2:
			if int(plock[x:x+1]) == 1:
				print '  locked'
			else:
				print '  unlocked'
		else:
			print '  -'
	else:
		print 'read error: %s' % card.errorcode
print

if x > 0:
	os._exit(False)
else:
	os._exit(True)

########NEW FILE########
__FILENAME__ = readtag
#!/usr/bin/python

#  readtag.py - read all sectors from a standard tag
# 
#  Adam Laurie <adam@algroup.co.uk>
#  http://rfidiot.org/
# 
#  This code is copyright (c) Adam Laurie, 2006, All rights reserved.
#  For non-commercial use only, the following terms apply - for all other
#  uses, please contact the author:
#
#    This code is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#


import rfidiot
import sys
import os

try:
        card= rfidiot.card
except:
	print "Couldn't open reader!"
        os._exit(True)

card.info('readtag v0.1f')
card.select()
print '\nID: ' + card.uid
print '  Data:'

card.select()
for x in range(255):
	print '    Block %02x:' % x,
	if card.readblock(x):
		print card.data,
		print card.ReadablePrint(card.ToBinary(card.data))
	else:
		print 'read error: %s, %s' % (card.errorcode, card.ISO7816ErrorCodes[card.errorcode])

print '\n    Total blocks: ',
print x
if x > 0:
	os._exit(False)
else:
	os._exit(True)

########NEW FILE########
__FILENAME__ = iso3166
# -*- coding: iso-8859-15 -*-
# ISO-3166 alpha country codes - ver 1
ISO3166CountryCodesAlpha= { "ABW":"Aruba",\
			 "AFG":"Afghanistan",\
			 "AGO":"Angola",\
			 "AIA":"Anguilla",\
			 "ALA":"Åland Islands",\
			 "ALB":"Albania",\
			 "AND":"Andorra",\
			 "ANT":"Netherlands Antilles",\
			 "ARE":"United Arab Emirates",\
			 "ARG":"Argentina",\
			 "ARM":"Armenia",\
			 "ASM":"American Samoa",\
			 "ATA":"Antarctica",\
			 "ATF":"French Southern Territories",\
			 "ATG":"Antigua and Barbuda",\
			 "AUS":"Australia",\
			 "AUT":"Austria",\
			 "AZE":"Azerbaijan",\
			 "BDI":"Burundi",\
			 "BDR":"Bundesdruckerei",\
			 "BEL":"Belgium",\
			 "BEN":"Benin",\
			 "BFA":"Burkina Faso",\
			 "BGD":"Bangladesh",\
			 "BGR":"Bulgaria",\
			 "BHR":"Bahrain",\
			 "BHS":"Bahamas",\
			 "BIH":"Bosnia and Herzegovina",\
			 "BLR":"Belarus",\
			 "BLZ":"Belize",\
			 "BMU":"Bermuda",\
			 "BOL":"Bolivia",\
			 "BRA":"Brazil",\
			 "BRB":"Barbados",\
			 "BRN":"Brunei Darussalam",\
			 "BTN":"Bhutan",\
			 "BVT":"Bouvet Island",\
			 "BWA":"Botswana",\
			 "CAF":"Central African Republic",\
			 "CAN":"Canada",\
			 "CCK":"Cocos (Keeling) Islands",\
			 "CHE":"Switzerland",\
			 "CHL":"Chile",\
			 "CHN":"China",\
			 "CIV":"Côte d'Ivoire",\
			 "CMR":"Cameroon",\
			 "COD":"Congo, the Democratic Republic of the",\
			 "COG":"Congo",\
			 "COK":"Cook Islands",\
			 "COL":"Colombia",\
			 "COM":"Comoros",\
			 "CPV":"Cape Verde",\
			 "CRI":"Costa Rica",\
			 "CUB":"Cuba",\
			 "CXR":"Christmas Island",\
			 "CYM":"Cayman Islands",\
			 "CYP":"Cyprus",\
			 "CZE":"Czech Republic",\
			 "DEU":"Germany",\
			 # for brain-damaged german passports
			 "D":"Germany",\
			 "DJI":"Djibouti",\
			 "DMA":"Dominica",\
			 "DNK":"Denmark",\
			 "DOM":"Dominican Republic",\
			 "DZA":"Algeria",\
			 "ECU":"Ecuador",\
			 "EGY":"Egypt",\
			 "ERI":"Eritrea",\
			 "ESH":"Western Sahara",\
			 "ESP":"Spain",\
			 "EST":"Estonia",\
			 "ETH":"Ethiopia",\
			 "FIN":"Finland",\
			 "FJI":"Fiji",\
			 "FLK":"Falkland Islands (Malvinas)",\
			 "FRA":"France",\
			 "FRO":"Faroe Islands",\
			 "FSM":"Micronesia, Federated States of",\
			 "GAB":"Gabon",\
			 "GBR":"United Kingdom",\
			 "GEO":"Georgia",\
			 "GGY":"Guernsey",\
			 "GHA":"Ghana",\
			 "GIB":"Gibraltar",\
			 "GIN":"Guinea",\
			 "GLP":"Guadeloupe",\
			 "GMB":"Gambia",\
			 "GNB":"Guinea-Bissau",\
			 "GNQ":"Equatorial Guinea",\
			 "GRC":"Greece",\
			 "GRD":"Grenada",\
			 "GRL":"Greenland",\
			 "GTM":"Guatemala",\
			 "GUF":"French Guiana",\
			 "GUM":"Guam",\
			 "GUY":"Guyana",\
			 "HKG":"Hong Kong",\
			 "HMD":"Heard Island and McDonald Islands",\
			 "HND":"Honduras",\
			 "HRV":"Croatia",\
			 "HTI":"Haiti",\
			 "HUN":"Hungary",\
			 "IDN":"Indonesia",\
			 "IMN":"Isle of Man",\
			 "IND":"India",\
			 "IOT":"British Indian Ocean Territory",\
			 "IRL":"Ireland",\
			 "IRN":"Iran, Islamic Republic of",\
			 "IRQ":"Iraq",\
			 "ISL":"Iceland",\
			 "ISR":"Israel",\
			 "ITA":"Italy",\
			 "JAM":"Jamaica",\
			 "JEY":"Jersey",\
			 "JOR":"Jordan",\
			 "JPN":"Japan",\
			 "KAZ":"Kazakhstan",\
			 "KEN":"Kenya",\
			 "KGZ":"Kyrgyzstan",\
			 "KHM":"Cambodia",\
			 "KIR":"Kiribati",\
			 "KNA":"Saint Kitts and Nevis",\
			 "KOR":"Korea, Republic of",\
			 "KWT":"Kuwait",\
			 "LAO":"Lao People's Democratic Republic",\
			 "LBN":"Lebanon",\
			 "LBR":"Liberia",\
			 "LBY":"Libyan Arab Jamahiriya",\
			 "LCA":"Saint Lucia",\
			 "LIE":"Liechtenstein",\
			 "LKA":"Sri Lanka",\
			 "LSO":"Lesotho",\
			 "LTU":"Lithuania",\
			 "LUX":"Luxembourg",\
			 "LVA":"Latvia",\
			 "MAC":"Macao",\
			 "MAR":"Morocco",\
			 "MCO":"Monaco",\
			 "MDA":"Moldova, Republic of",\
			 "MDG":"Madagascar",\
			 "MDV":"Maldives",\
			 "MEX":"Mexico",\
			 "MHL":"Marshall Islands",\
			 "MKD":"Macedonia, the former Yugoslav Republic of",\
			 "MLI":"Mali",\
			 "MLT":"Malta",\
			 "MMR":"Myanmar",\
			 "MNE":"Montenegro",\
			 "MNG":"Mongolia",\
			 "MNP":"Northern Mariana Islands",\
			 "MOZ":"Mozambique",\
			 "MRT":"Mauritania",\
			 "MSR":"Montserrat",\
			 "MTQ":"Martinique",\
			 "MUS":"Mauritius",\
			 "MWI":"Malawi",\
			 "MYS":"Malaysia",\
			 "MYT":"Mayotte",\
			 "NAM":"Namibia",\
			 "NCL":"New Caledonia",\
			 "NER":"Niger",\
			 "NFK":"Norfolk Island",\
			 "NGA":"Nigeria",\
			 "NIC":"Nicaragua",\
			 "NIU":"Niue",\
			 "NLD":"Netherlands",\
			 "NOR":"Norway",\
			 "NPL":"Nepal",\
			 "NRU":"Nauru",\
			 "NZL":"New Zealand",\
			 "OMN":"Oman",\
			 "PAK":"Pakistan",\
			 "PAN":"Panama",\
			 "PCN":"Pitcairn",\
			 "PER":"Peru",\
			 "PHL":"Philippines",\
			 "PLW":"Palau",\
			 "PNG":"Papua New Guinea",\
			 "POL":"Poland",\
			 "PRI":"Puerto Rico",\
			 "PRK":"Korea, Democratic People's Republic of",\
			 "PRT":"Portugal",\
			 "PRY":"Paraguay",\
			 "PSE":"Palestinian Territory, Occupied",\
			 "PYF":"French Polynesia",\
			 "QAT":"Qatar",\
			 "REU":"Réunion",\
			 "ROU":"Romania",\
			 "RUS":"Russian Federation",\
			 "RWA":"Rwanda",\
			 "SAU":"Saudi Arabia",\
			 "SDN":"Sudan",\
			 "SEN":"Senegal",\
			 "SGP":"Singapore",\
			 "SGS":"South Georgia and the South Sandwich Islands",\
			 "SHN":"Saint Helena",\
			 "SJM":"Svalbard and Jan Mayen",\
			 "SLB":"Solomon Islands",\
			 "SLE":"Sierra Leone",\
			 "SLV":"El Salvador",\
			 "SMR":"San Marino",\
			 "SOM":"Somalia",\
			 "SPM":"Saint Pierre and Miquelon",\
			 "SRB":"Serbia",\
			 "STP":"Sao Tome and Principe",\
			 "SUR":"Suriname",\
			 "SVK":"Slovakia",\
			 "SVN":"Slovenia",\
			 "SWE":"Sweden",\
			 "SWZ":"Swaziland",\
			 "SYC":"Seychelles",\
			 "SYR":"Syrian Arab Republic",\
			 "TCA":"Turks and Caicos Islands",\
			 "TCD":"Chad",\
			 "TGO":"Togo",\
			 "THA":"Thailand",\
			 "TJK":"Tajikistan",\
			 "TKL":"Tokelau",\
			 "TKM":"Turkmenistan",\
			 "TLS":"Timor-Leste",\
			 "TON":"Tonga",\
			 "TTO":"Trinidad and Tobago",\
			 "TUN":"Tunisia",\
			 "TUR":"Turkey",\
			 "TUV":"Tuvalu",\
			 "TWN":"Taiwan, Province of China",\
			 "TZA":"Tanzania, United Republic of",\
			 "UGA":"Uganda",\
			 "UKR":"Ukraine",\
			 "UMI":"United States Minor Outlying Islands",\
			 "URY":"Uruguay",\
			 "USA":"United States",\
			 "UTO":"Utopia",\
			 "UZB":"Uzbekistan",\
			 "VAT":"Holy See (Vatican City State)",\
			 "VCT":"Saint Vincent and the Grenadines",\
			 "VEN":"Venezuela",\
			 "VGB":"Virgin Islands, British",\
			 "VIR":"Virgin Islands, U.S.",\
			 "VNM":"Viet Nam",\
			 "VUT":"Vanuatu",\
			 "WLF":"Wallis and Futuna",\
			 "WSM":"Samoa",\
			 "YEM":"Yemen",\
			 "ZAF":"South Africa",\
			 "ZMB":"Zambia",\
			 "ZWE":"Zimbabwe",\
			 "UNO":"United Nations Organization",\
			 "UNA":"United Nations specialized agency official",\
			 "XXA":"Stateless",\
			 "XXB":"Refugee",\
			 "XXC":"Refugee (non-convention)",\
			 "XXX":"Unspecified / Unknown",\
			}

# combined ISO-3166 country and icar.org manufacturer codes
ISO3166CountryCodes= {'004':'Afghanistan',\
		      '248':'Åland Islands',\
		      '008':'Albania',\
		      '012':'Algeria',\
		      '016':'American Samoa',\
		      '020':'Andorra',\
		      '024':'Angola',\
		      '660':'Anguilla',\
		      '010':'Antarctica',\
		      '028':'Antigua and Barbuda',\
		      '032':'Argentina',\
		      '051':'Armenia',\
		      '533':'Aruba',\
		      '036':'Australia',\
		      '040':'Austria',\
		      '031':'Azerbaijan',\
		      '044':'Bahamas',\
		      '048':'Bahrain',\
		      '050':'Bangladesh',\
		      '052':'Barbados',\
		      '112':'Belarus',\
		      '056':'Belgium',\
		      '084':'Belize',\
		      '204':'Benin',\
		      '060':'Bermuda',\
		      '064':'Bhutan',\
		      '068':'Bolivia',\
		      '070':'Bosnia and Herzegovina',\
		      '072':'Botswana',\
		      '074':'Bouvet Island',\
		      '076':'Brazil',\
		      '086':'British Indian Ocean Territory',\
		      '096':'Brunei Darussalam',\
		      '100':'Bulgaria',\
		      '854':'Burkina Faso',\
		      '108':'Burundi',\
		      '116':'Cambodia',\
		      '120':'Cameroon',\
		      '124':'Canada',\
		      '132':'Cape Verde',\
		      '136':'Cayman Islands',\
		      '140':'Central African Republic',\
		      '148':'Chad',\
		      '152':'Chile',\
		      '156':'China',\
		      '162':'Christmas Island',\
		      '166':'Cocos (Keeling) Islands',\
		      '170':'Colombia',\
		      '174':'Comoros',\
		      '178':'Congo',\
		      '180':'Congo, the Democratic Republic of the',\
		      '184':'Cook Islands',\
		      '188':'Costa Rica',\
		      '384':'Côte d\'Ivoire',\
		      '191':'Croatia',\
		      '192':'Cuba',\
		      '196':'Cyprus',\
		      '203':'Czech Republic',\
		      '208':'Denmark',\
		      '262':'Djibouti',\
		      '212':'Dominica',\
		      '214':'Dominican Republic',\
		      '218':'Ecuador',\
		      '818':'Egypt',\
		      '222':'El Salvador',\
		      '226':'Equatorial Guinea',\
		      '232':'Eritrea',\
		      '233':'Estonia',\
		      '231':'Ethiopia',\
		      '238':'Falkland Islands (Malvinas)',\
		      '234':'Faroe Islands',\
		      '242':'Fiji',\
		      '246':'Finland',\
		      '250':'France',\
		      '254':'French Guiana',\
		      '258':'French Polynesia',\
		      '260':'French Southern Territories',\
		      '266':'Gabon',\
		      '270':'Gambia',\
		      '268':'Georgia',\
		      '276':'Germany',\
		      '288':'Ghana',\
		      '292':'Gibraltar',\
		      '300':'Greece',\
		      '304':'Greenland',\
		      '308':'Grenada',\
		      '312':'Guadeloupe',\
		      '316':'Guam',\
		      '320':'Guatemala',\
		      '831':'Guernsey',\
		      '324':'Guinea',\
		      '624':'Guinea-Bissau',\
		      '328':'Guyana',\
		      '332':'Haiti',\
		      '334':'Heard Island and McDonald Islands',\
		      '336':'Holy See (Vatican City State)',\
		      '340':'Honduras',\
		      '344':'Hong Kong',\
		      '348':'Hungary',\
		      '352':'Iceland',\
		      '356':'India',\
		      '360':'Indonesia',\
		      '364':'Iran, Islamic Republic of',\
		      '368':'Iraq',\
		      '372':'Ireland',\
		      '833':'Isle of Man',\
		      '376':'Israel',\
		      '380':'Italy',\
		      '388':'Jamaica',\
		      '392':'Japan',\
		      '832':'Jersey',\
		      '400':'Jordan',\
		      '398':'Kazakhstan',\
		      '404':'Kenya',\
		      '296':'Kiribati',\
		      '408':'Korea, Democratic People\'s Republic of',\
		      '410':'Korea, Republic of',\
		      '414':'Kuwait',\
		      '417':'Kyrgyzstan',\
		      '418':'Lao People\'s Democratic Republic',\
		      '428':'Latvia',\
		      '422':'Lebanon',\
		      '426':'Lesotho',\
		      '430':'Liberia',\
		      '434':'Libyan Arab Jamahiriya',\
		      '438':'Liechtenstein',\
		      '440':'Lithuania',\
		      '442':'Luxembourg',\
		      '446':'Macao',\
		      '807':'Macedonia, the former Yugoslav Republic of',\
		      '450':'Madagascar',\
		      '454':'Malawi',\
		      '458':'Malaysia',\
		      '462':'Maldives',\
		      '466':'Mali',\
		      '470':'Malta',\
		      '584':'Marshall Islands',\
		      '474':'Martinique',\
		      '478':'Mauritania',\
		      '480':'Mauritius',\
		      '175':'Mayotte',\
		      '484':'Mexico',\
		      '583':'Micronesia, Federated States of',\
		      '498':'Moldova, Republic of',\
		      '492':'Monaco',\
		      '496':'Mongolia',\
		      '499':'Montenegro',\
		      '500':'Montserrat',\
		      '504':'Morocco',\
		      '508':'Mozambique',\
		      '104':'Myanmar',\
		      '516':'Namibia',\
		      '520':'Nauru',\
		      '524':'Nepal',\
		      '528':'Netherlands',\
		      '530':'Netherlands Antilles',\
		      '540':'New Caledonia',\
		      '554':'New Zealand',\
		      '558':'Nicaragua',\
		      '562':'Niger',\
		      '566':'Nigeria',\
		      '570':'Niue',\
		      '574':'Norfolk Island',\
		      '580':'Northern Mariana Islands',\
		      '578':'Norway',\
		      '512':'Oman',\
		      '586':'Pakistan',\
		      '585':'Palau',\
		      '275':'Palestinian Territory, Occupied',\
		      '591':'Panama',\
		      '598':'Papua New Guinea',\
		      '600':'Paraguay',\
		      '604':'Peru',\
		      '608':'Philippines',\
		      '612':'Pitcairn',\
		      '616':'Poland',\
		      '620':'Portugal',\
		      '630':'Puerto Rico',\
		      '634':'Qatar',\
		      '638':'Réunion',\
		      '642':'Romania',\
		      '643':'Russian Federation',\
		      '646':'Rwanda',\
		      '654':'Saint Helena',\
		      '659':'Saint Kitts and Nevis',\
		      '662':'Saint Lucia',\
		      '666':'Saint Pierre and Miquelon',\
		      '670':'Saint Vincent and the Grenadines',\
		      '882':'Samoa',\
		      '674':'San Marino',\
		      '678':'Sao Tome and Principe',\
		      '682':'Saudi Arabia',\
		      '686':'Senegal',\
		      '688':'Serbia',\
		      '690':'Seychelles',\
		      '694':'Sierra Leone',\
		      '702':'Singapore',\
		      '703':'Slovakia',\
		      '705':'Slovenia',\
		      '090':'Solomon Islands',\
		      '706':'Somalia Somalia',\
		      '710':'South Africa',\
		      '239':'South Georgia and the South Sandwich Islands',\
		      '724':'Spain',\
		      '144':'Sri Lanka',\
		      '736':'Sudan',\
		      '740':'Suriname',\
		      '744':'Svalbard and Jan Mayen',\
		      '748':'Swaziland',\
		      '752':'Sweden',\
		      '756':'Switzerland',\
		      '760':'Syrian Arab Republic',\
		      '158':'Taiwan, Province of China',\
		      '762':'Tajikistan',\
		      '834':'Tanzania, United Republic of',\
		      '764':'Thailand',\
		      '626':'Timor-Leste',\
		      '768':'Togo',\
		      '772':'Tokelau',\
		      '776':'Tonga',\
		      '780':'Trinidad and Tobago',\
		      '788':'Tunisia',\
		      '792':'Turkey',\
		      '795':'Turkmenistan',\
		      '796':'Turks and Caicos Islands',\
		      '798':'Tuvalu',\
		      '800':'Uganda',\
		      '804':'Ukraine',\
		      '784':'United Arab Emirates',\
		      '826':'United Kingdom',\
		      '840':'United States',\
		      '581':'United States Minor Outlying Islands',\
		      '858':'Uruguay',\
		      '860':'Uzbekistan',\
		      '548':'Vanuatu',\
		      '862':'Venezuela',\
		      '704':'Viet Nam',\
		      '092':'Virgin Islands, British',\
		      '850':'Virgin Islands, U.S.',\
		      '876':'Wallis and Futuna',\
		      '732':'Western Sahara',\
		      '887':'Yemen',\
		      '894':'Zambia',\
		      '716':'Zimbabwe',\
		      '985':'MANUF: Destron Fearing / Digital Angel Corporation',\
		      '984':'MANUF: Nedap',\
		      '983':'MANUF: Texas Instruments',\
		      '982':'MANUF: Allflex',\
		      '981':'MANUF: Datamars',\
		      '980':'MANUF: AGRIDENT BV',\
		      '979':'MANUF: Earlsmere I.D.',\
		      '978':'MANUF: IER SA',\
		      '977':'MANUF: Avid',\
		      '976':'MANUF: Gemplus',\
		      '975':'MANUF: Sokymat',\
		      '974':'MANUF: Impro',\
		      '973':'MANUF: Fujihira',\
		      '972':'MANUF: Planet ID',\
		      '971':'MANUF: Alfa Laval Agri',\
		      '970':'MANUF: Amphenol',\
		      '969':'MANUF: Caisley',\
		      '968':'MANUF: AEG',\
		      '967':'MANUF: Rfdynamics',\
		      '966':'MANUF: PetCode',\
		      '965':'MANUF: 4D Technology Co. Ltd.',\
		      '964':'MANUF: Rumitag S.L.',\
		      '963':'MANUF: Korth Eletro Mecanica LTDA',\
		      '962':'MANUF: DigiTag A/S',\
		      '961':'MANUF: Mannings I.A.I.D.',\
		      '960':'MANUF: Chevillot',\
		      '959':'MANUF: Global ID Technologies',\
		      '958':'MANUF: Pet ID',\
		      '957':'MANUF: Innoceramics',\
		      '956':'MANUF: Trovan Ltd.',\
		      '955':'MANUF: Reseaumatique',\
		      '954':'MANUF: Ryeflex',\
		      '953':'MANUF: Cromasa',\
		      '952':'MANUF: JECTA',\
		      '951':'MANUF: Leader Products Pty Ltd',\
		      '950':'MANUF: SPLICE do Brasil Telecomunicacoes e Eletronica S.A.',\
		      '949':'MANUF: Y-Tex Corporation',\
		      '948':'MANUF: H. Hauptner und Richard Herberholz GmbH & Co. KG',\
		      '947':'MANUF: BELCAM. ID',\
		      '946':'MANUF: Advanced Ceramics Limited',\
		      '945':'MANUF: Business Inception Identification B.V.',\
		      '944':'MANUF: Net & Telligent SA',\
		      '943':'MANUF: E-Mark Technologie & Development',\
		      '942':'MANUF: Zee Tags',\
		      '941':'MANUF: Felixcan S.L.',\
		      '940':'MANUF: Shearwell Data Ltd.',\
		      '939':'MANUF: RealTrace',\
		      '938':'MANUF: INSVET',\
		      '937':'MANUF: ID & Traceback Systems AS',\
		      '936':'MANUF: CROVET, S.L.',\
		      '935':'MANUF: VeriLogik, Inc.',\
		      '900':'MANUF: Shared (see http://www.icar.org/manufacturer_codes.htm)',\
		      '1022':'UNREGISTERED MANUF: VeriChip Corporation'}

########NEW FILE########
__FILENAME__ = pn532
#!/usr/bin/python

#  pn532.py - NXP PN532 definitions for restricted functions
# 
#  Adam Laurie <adam@algroup.co.uk>
#  http://rfidiot.org/
# 
#  This code is copyright (c) Adam Laurie, 2009, All rights reserved.
#  For non-commercial use only, the following terms apply - for all other
#  uses, please contact the author:
#
#    This code is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#


PN532_APDU=		{
			'GET_GENERAL_STATUS' : ['d4','04'],
			'GET_PN532_FIRMWARE' : ['d4','02'],
			'IN_ATR' : ['d4','50'],
			'IN_AUTO_POLL' : ['d4','60'],
			'IN_COMMUNICATE_THRU' : ['d4','42'],
			'IN_DATA_EXCHANGE' : ['d4','40'],
			'IN_LIST_PASSIVE_TARGET' : ['d4','4a'],
			'IN_SELECT' : ['d4','54'],
			'TG_GET_DATA' : ['d4','86'],
			'TG_INIT_AS_TARGET' : ['d4','8c'],
			'TG_SET_DATA' : ['d4','8e'],
			}

PN532_FUNCTIONS=	{
			0x01 : 'ISO/IEC 14443 Type A',
			0x02 : 'ISO/IEC 14443 Type B',
			0x04 : 'ISO/IEC 18092',
			}

PN532_OK= 'D503'

PN532_BAUDRATES= 	{
			0x00 : '106 kbps',
			0x01 : '212 kbps',
			0x02 : '424 kbps',
			0x10 : '212 kbps',
			0x20 : '424 kbps',
			}

PN532_FRAMING= 		{
			0x00 : 'Mifare',
			0x01 : 'Active mode',
			0x02 : 'FeliCa',
			}

PN532_TARGETS=		{
			'00' : 'Generic passive 106kbps (ISO/IEC1443-4A,mifare,DEP)',
			'10' : 'mifare card',
			}

PN532_MODULATION=	{
			0x00 : 'Mifare, ISO/IEC 14443-3 Type A/B, ISO/IEC 18092 passive 106 kbps',
			0x01 : 'ISO/IEC 18092 active',
			0x02 : 'Innovision Jewel',
			0x10 : 'FeliCa, ISO/IEC 18092 passive 212/424 kbps',
			}

PN532_ERRORS=		{
			0x00 : 'No Error',
			0x01 : 'Time Out',
			0x02 : 'CRC Error',
			0x03 : 'Parity Error',
			0x04 : 'Erroneous Bit Count during Aticollision/Select (ISO 14443-3/ISO 18092 106kbps)',
			0x05 : 'Mifare Framing Error',
			0x06 : 'Abnormal Bit Collision during Bitwise Anticollision (106 kbps)',
			0x07 : 'Communication Buffer Size Insufficient',
			0x09 : 'RF Buffer Overflow (Register CIU_ERROR BufferOvfl)',
			0x0a : 'Active Communication RF Timeout',
			0x0b : 'RF Protocol Error',
			0x0d : 'Antenna Overheat',
			0x0e : 'Internal Buffer Overflow',
			0x10 : 'Invalid Parameter',
			0x12 : 'DEP protocol - initiator command not supported',
			0x13 : 'DEP protocol - data format out of spec',
			0x14 : 'Mifare authentication error',
			0x23 : 'ISO/IEC 14443-3 UID check byte wrong',
			0x25 : 'DEP protocol - invalid device state',
			0x26 : 'Operation not allowed in this configuration',
			0x27 : 'Command out of context',
			0x29 : 'Target released by Initiator',
			0x2a : 'ID mismatch - card has been exchanged',
			0x2b : 'Activated card missing',
			0x2c : 'NFCID3 mismatch',
			0x2d : 'Over-current event detected',
			0x2e : 'NAD missing in DEP frame',
			}

PN532_RF=	{
		0x00 : 'Not present',
		0x01 : 'Present',
		}

# pn532 functions

# print pn532 firmware details
def pn532_print_firmware(data):
	if not data[:4] == PN532_OK:
		print '  Bad data from PN532:', data
	else:
		print '       IC:', data[4:6]
		print '      Rev: %d.%d' %  (int(data[6:8],16),int(data[8:10]))
		print '  Support:',
		support= int(data[10:12],16)
		spacing= ''
		for n in PN532_FUNCTIONS.keys():
			if support & n:
				print spacing + PN532_FUNCTIONS[n]
				spacing= '           '
		print

# print pn532 antenna status and return number of tags in field
def pn532_print_status(data):
	print '  Reader PN532 Status:'
	print '      Last error:', PN532_ERRORS[int(data[4:6])]
	print '     External RF:', PN532_RF[int(data[6:8],16)]
	tags= int(data[8:10],16)
	print '    TAGS present:', tags
	for n in range(tags):
		print '    Tag number %d:' % (n + 1)
		print '      Logical number:', data[10 + n * 2:12 + n * 2]
		print '         RX Baudrate:', PN532_BAUDRATES[int(data[12 + n * 2:14 + n * 2],16)]
		print '         TX Baudrate:', PN532_BAUDRATES[int(data[14 + n * 2:16 + n * 2],16)]
		print '          Modulation:', PN532_MODULATION[int(data[16 + n * 2:18 + n * 2],16)]
		print '      SAM Status:', data[18 + n * 2:20 + n * 2]
	print
	return tags

########NEW FILE########
__FILENAME__ = pyandroid
#!/usr/bin/python

#
# pyandroid.py - Python code for working with Android NFC reader
# version 0.1
# Nick von Dadelszen (nick@lateralsecurity.com)
# Lateral Security (www.lateralsecurity.com)

#
# This code is copyright (c) Lateral Security, 2011, All rights reserved.
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
#   You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import binascii
import logging
import time
import readline
import socket
import rfidiotglobals

# listening port
PORT = 4444

class Android(object):
	VERSION = "0.1"
	s = None
	c = None
	
	def __init__(self):
		if rfidiotglobals.Debug:
			self.initLog()
		if rfidiotglobals.Debug:
			self.log.debug("pyandroid starting")
		self.configure()
	
	def __del__(self):
		self.deconfigure()
	
	def deconfigure(self):
		if rfidiotglobals.Debug:
			self.log.debug("pyandroid: deconfiguring")
		if self.c is not None:
				self.c.send("close\n")

	def initLog(self, level=logging.DEBUG):
#	def initLog(self, level=logging.INFO):
		self.log = logging.getLogger("pyandroid")
		self.log.setLevel(level)
		sh = logging.StreamHandler()
		sh.setLevel(level)
		f = logging.Formatter("%(asctime)s: %(levelname)s - %(message)s")
		sh.setFormatter(f)
		self.log.addHandler(sh)

	def configure(self):
		if rfidiotglobals.Debug:
			self.log.debug("pyandroid: Setting up listening port")
		if self.s is not None:
			self.s.close()
		try:
			self.s = socket.socket()         # Create a socket object
			self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			self.s.bind(("0.0.0.0", PORT))	# Bind to the port
			self.s.listen(5) 				# Listen for connections
		except Exception as e:
			print 'pyandroid: Could not open port: %s' % PORT
			print e
		
	def reset(self):
		if rfidiotglobals.Debug:
			self.log.debug("pyandroid: Resetting connections")
		if self.c is not None:
			self.c.send("close\n")
			self.c.close()
		if self.s is not None:
			self.s.close()
		self.configure()	
	
	def select(self):
		if rfidiotglobals.Debug:
			self.log.debug("pyandroid in select statement")
		print 'Waiting for connection from Android device ....'
		self.c, addr = self.s.accept()     # Establish connection with client.
		if rfidiotglobals.Debug:
			self.log.debug("pyandroid: Got connection from " + addr[0])
		print "Got connection from ", addr
		# Get UID
		self.c.send('getUID\n')
		uid = self.c.recv(1024)		
		return uid
	
	def sendAPDU(self, apdu):
		if rfidiotglobals.Debug:	
			self.log.debug("Sending APDU: " + apdu)
		self.c.send(apdu + '\n')
		response = self.c.recv(1024)
		response = response[:-1]
		
		if rfidiotglobals.Debug:
			self.log.debug('APDU r =' + response)
		return response

        def sendResults(self, result):
                if rfidiotglobals.Debug:
                        self.log.debug("Sending results: " + results)
                self.c.send('r:' + result + '\n')
                response = self.c.recv(1024)
                response = response[:-1]

                if rfidiotglobals.Debug:
                        self.log.debug('Response r =' + response)
                return response

if __name__ == "__main__":
	n = Android()
	uid = n.select()
	if uid:
		print 'UID: ' + uid
	print

	cont = True
	while cont:
		apdu = raw_input("enter the apdu to send now, send \'close\' to finish :")
		if apdu == 'close':
			cont = False
		else:
			r = n.sendAPDU(apdu)
			print r

	print 'Ending now ...'
	n.deconfigure()

########NEW FILE########
__FILENAME__ = pynfc
#!/usr/bin/python

#
# pynfc.py - Python wrapper for libnfc
# version 0.2 (should work with libnfc 1.2.1 and 1.3.0)
# version 0.2a - tweaked by rfidiot for libnfc 1.6.0-rc1 october 2012
# Nick von Dadelszen (nick@lateralsecurity.com)
# Lateral Security (www.lateralsecurity.com)

#  Thanks to metlstorm for python help :)
#
# This code is copyright (c) Nick von Dadelszen, 2009, All rights reserved.
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
#   You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import ctypes
import ctypes.util
import binascii
import logging
import time
import readline
import string
import rfidiotglobals

# nfc_property enumeration
NP_TIMEOUT_COMMAND		= 0x00
NP_TIMEOUT_ATR			= 0x01
NP_TIMEOUT_COM			= 0x02
NP_HANDLE_CRC			= 0x03
NP_HANDLE_PARITY		= 0x04
NP_ACTIVATE_FIELD		= 0x05
NP_ACTIVATE_CRYPTO1		= 0x06
NP_INFINITE_SELECT		= 0x07
NP_ACCEPT_INVALID_FRAMES	= 0x08
NP_ACCEPT_MULTIPLE_FRAMES	= 0x09
NP_AUTO_ISO14443_4		= 0x0a
NP_EASY_FRAMING			= 0x0b
NP_FORCE_ISO14443_A		= 0x0c
NP_FORCE_ISO14443_B		= 0x0d
NP_FORCE_SPEED_106		= 0x0e

# NFC modulation type enumeration
NMT_ISO14443A		= 0x01
NMT_JEWEL		= 0x02
NMT_ISO14443B		= 0x03
NMT_ISO14443BI		= 0x04
NMT_ISO14443B2SR	= 0x05
NMT_ISO14443B2CT	= 0x06
NMT_FELICA		= 0x07
NMT_DEP			= 0x08

# NFC baud rate enumeration
NBR_UNDEFINED		= 0x00
NBR_106			= 0x01
NBR_212			= 0x02
NBR_424			= 0x03
NBR_847			= 0x04

#NFC D.E.P. (Data Exchange Protocol) active/passive mode
NDM_UNDEFINED		= 0x00
NDM_PASSIVE		= 0x01
NDM_ACTIVE		= 0x02

# Mifare commands
MC_AUTH_A 		= 0x60
MC_AUTH_B 		= 0x61
MC_READ 		= 0x30
MC_WRITE 		= 0xA0
MC_TRANSFER 		= 0xB0
MC_DECREMENT 		= 0xC0
MC_INCREMENT 		= 0xC1
MC_STORE 		= 0xC2

# PN53x specific errors */
ETIMEOUT        	= 0x01
ECRC            	= 0x02
EPARITY         	= 0x03
EBITCOUNT       	= 0x04
EFRAMING        	= 0x05
EBITCOLL        	= 0x06
ESMALLBUF       	= 0x07
EBUFOVF         	= 0x09
ERFTIMEOUT      	= 0x0a
ERFPROTO        	= 0x0b
EOVHEAT         	= 0x0d
EINBUFOVF       	= 0x0e
EINVPARAM       	= 0x10
EDEPUNKCMD      	= 0x12
EINVRXFRAM      	= 0x13
EMFAUTH         	= 0x14
ENSECNOTSUPP    	= 0x18    # PN533 only
EBCC            	= 0x23
EDEPINVSTATE    	= 0x25
EOPNOTALL       	= 0x26
ECMD            	= 0x27
ETGREL          	= 0x29
ECID            	= 0x2a
ECDISCARDED     	= 0x2b
ENFCID3         	= 0x2c
EOVCURRENT      	= 0x2d
ENAD            	= 0x2e

MAX_FRAME_LEN 		= 264
MAX_DEVICES 		= 16
BUFSIZ 			= 8192
MAX_TARGET_COUNT 	= 1

DEVICE_NAME_LENGTH	= 256
DEVICE_PORT_LENGTH	= 64
NFC_CONNSTRING_LENGTH	= 1024

class NFC_ISO14443A_INFO(ctypes.Structure):
	_pack_ = 1
	_fields_ = [('abtAtqa', ctypes.c_ubyte * 2),
		    ('btSak', ctypes.c_ubyte),
		    ('uiUidLen', ctypes.c_size_t),
		    ('abtUid', ctypes.c_ubyte * 10),
		    ('uiAtsLen', ctypes.c_size_t),
		    ('abtAts', ctypes.c_ubyte * 254)]

class NFC_FELICA_INFO(ctypes.Structure):
	_pack_ = 1
	_fields_ = [('szLen', ctypes.c_size_t),
		    ('btResCode', ctypes.c_ubyte),
		    ('abtId', ctypes.c_ubyte * 8),
		    ('abtPad', ctypes.c_ubyte * 8),
		    ('abtSysCode', ctypes.c_ubyte * 2)]

class NFC_ISO14443B_INFO(ctypes.Structure):
	_pack_ = 1
	_fields_ = [('abtPupi', ctypes.c_ubyte * 4),
		    ('abtApplicationData', ctypes.c_ubyte * 4),
		    ('abtProtocolInfo', ctypes.c_ubyte * 3),
		    ('ui8CardIdentifier', ctypes.c_ubyte)]

class NFC_ISO14443BI_INFO(ctypes.Structure):
	_pack_ = 1
	_fields_ = [('abtDIV', ctypes.c_ubyte * 4),
		    ('btVerLog', ctypes.c_ubyte),
		    ('btConfig', ctypes.c_ubyte),
		    ('szAtrLen', ctypes.c_size_t),
		    ('abtAtr', ctypes.c_ubyte * 33)]

class NFC_ISO14443B2SR_INFO(ctypes.Structure):
	_pack_ = 1
	_fields_ = [('abtUID', ctypes.c_ubyte * 8)]


class NFC_ISO14443B2CT_INFO(ctypes.Structure):
	_pack_ = 1
	_fields_ = [('abtUID', ctypes.c_ubyte * 4),
		    ('btProdCode', ctypes.c_ubyte),
		    ('btFabCode', ctypes.c_ubyte)]

class NFC_JEWEL_INFO(ctypes.Structure):
	_pack_ = 1
	_fields_ = [('btSensRes', ctypes.c_ubyte * 2),
		    ('btId', ctypes.c_ubyte * 4)]

class NFC_DEP_INFO(ctypes.Structure):
	_pack_ = 1
	_fields_ = [('abtNFCID3', ctypes.c_ubyte * 10),
		    ('btDID', ctypes.c_ubyte),
		    ('btBS', ctypes.c_ubyte),
		    ('btBR', ctypes.c_ubyte),
		    ('btTO', ctypes.c_ubyte),
		    ('btPP', ctypes.c_ubyte),
		    ('abtGB', ctypes.c_ubyte * 48),
		    ('szGB', ctypes.c_size_t),
		    ('ndm', ctypes.c_ubyte)]

class NFC_TARGET_INFO(ctypes.Union):
	_pack_ = 1
	_fields_ = [('nai', NFC_ISO14443A_INFO),
		    ('nfi', NFC_FELICA_INFO),
		    ('nbi', NFC_ISO14443B_INFO),
		    ('nii', NFC_ISO14443BI_INFO),
		    ('nsi', NFC_ISO14443B2SR_INFO),
		    ('nci', NFC_ISO14443B2CT_INFO),
		    ('nji', NFC_JEWEL_INFO),
		    ('ndi', NFC_DEP_INFO)]

class NFC_CONNSTRING(ctypes.Structure):
	_pack_ = 1
	_fields_ = [('connstring', ctypes.c_ubyte * NFC_CONNSTRING_LENGTH)]

class NFC_MODULATION(ctypes.Structure):
	_pack_ = 1
	_fields_ = [('nmt', ctypes.c_uint),
		    ('nbr', ctypes.c_uint)]

class NFC_TARGET(ctypes.Structure):
	_pack_ = 1
	_fields_ = [('nti', NFC_TARGET_INFO),
		    ('nm', NFC_MODULATION)]

#class NFC_DEVICE(ctypes.Structure):
#	_fields_ = [('driver', ctypes.pointer(NFC_DRIVER),
#		    ('driver_data', ctypes.c_void_p),
#		    ('chip_data', ctypes.c_void_p),
#		    ('name', ctypes.c_ubyte * DEVICE_NAME_LENGTH),
#		    ('nfc_connstring', ctypes.c_ubyte * NFC_CONNSTRING_LENGTH),
#		    ('bCrc', ctypes.c_bool),
#		    ('bPar', ctypes.c_bool),
#		    ('bEasyFraming', ctypes.c_bool),
#		    ('bAutoIso14443_4', ctypes.c_bool),
#		    ('btSupportByte', ctypes.c_ubyte).
#		    ('last_error', ctypes.c_byte)]

#class NFC_DEVICE_DESC_T(ctypes.Structure):
#	_fields_ = [('acDevice',ctypes.c_char * BUFSIZ),
#		    ('pcDriver',ctypes.c_char_p),
#		    ('pcPort',ctypes.c_char_p),
#		    ('uiSpeed',ctypes.c_ulong),
#		    ('uiBusIndex',ctypes.c_ulong)]

#NFC_DEVICE_LIST = NFC_DEVICE_DESC_T * MAX_DEVICES
NFC_DEVICE_LIST = NFC_CONNSTRING * MAX_DEVICES

class ISO14443A(object):
	def __init__(self, ti):
		self.uid = "".join(["%02X" % x for x in ti.abtUid[:ti.uiUidLen]])
		if ti.uiAtsLen:
			self.atr = "".join(["%02X" % x for x in ti.abtAts[:ti.uiAtsLen]])
		else:
			self.atr = ""
	
	def __str__(self):
		rv = "ISO14443A(uid='%s', atr='%s')" % (self.uid, self.atr)
		return rv

class ISO14443B(object):
	def __init__(self, ti):
		self.pupi = "".join(["%02X" % x for x in ti.abtPupi[:4]])
		self.uid = self.pupi # for sake of compatibility with apps written for typeA
		self.atr = ""        # idem
	def __str__(self):
		rv = "ISO14443B(pupi='%s')" % (self.pupi)
		return rv

class NFC(object):
	def __init__(self, nfcreader):
		self.LIB = ctypes.util.find_library('nfc')
		#self.LIB = "/usr/local/lib/libnfc.so"
		#self.LIB = "/usr/local/lib/libnfc_26102009.so.0.0.0"
		#self.LIB = "./libnfc_nvd.so.0.0.0"
		#self.LIB = "./libnfc_26102009.so.0.0.0"		
		#self.LIB = "/data/RFID/libnfc/libnfc-svn-1.3.0/src/lib/.libs/libnfc.so"		
		self.device = None
		self.context = ctypes.POINTER(ctypes.c_int)()
		self.poweredUp = False

		self.initLog()
		self.LIBNFC_VER= self.initlibnfc()
		if rfidiotglobals.Debug:
			self.log.debug("libnfc %s" % self.LIBNFC_VER)
		self.configure(nfcreader)
	
	def __del__(self):
		self.deconfigure()

	def initLog(self, level=logging.DEBUG):
#	def initLog(self, level=logging.INFO):
		self.log = logging.getLogger("pynfc")
		self.log.setLevel(level)
		sh = logging.StreamHandler()
		sh.setLevel(level)
		f = logging.Formatter("%(asctime)s: %(levelname)s - %(message)s")
		sh.setFormatter(f)
		self.log.addHandler(sh)

	def initlibnfc(self):
		if rfidiotglobals.Debug:
			self.log.debug("Loading %s" % self.LIB)
		self.libnfc = ctypes.CDLL(self.LIB)
		self.libnfc.nfc_version.restype = ctypes.c_char_p
		self.libnfc.nfc_device_get_name.restype = ctypes.c_char_p
		self.libnfc.nfc_device_get_name.argtypes = [ctypes.c_void_p]
		self.libnfc.nfc_open.restype = ctypes.c_void_p
		self.libnfc.nfc_initiator_init.argtypes = [ctypes.c_void_p]
		self.libnfc.nfc_device_set_property_bool.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_bool];
		self.libnfc.nfc_close.argtypes = [ctypes.c_void_p]
		self.libnfc.nfc_initiator_list_passive_targets.argtypes = [ctypes.c_void_p, ctypes.Structure, ctypes.c_void_p, ctypes.c_size_t]
		self.libnfc.nfc_initiator_transceive_bytes.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint32]
		self.libnfc.nfc_init(ctypes.byref(self.context))
		return self.libnfc.nfc_version()

	def listreaders(self, target):
		devices = NFC_DEVICE_LIST()
		nfc_num_devices = ctypes.c_size_t()
		nfc_num_devices= self.libnfc.nfc_list_devices(self.context,ctypes.byref(devices),MAX_DEVICES)
		if target != None:
			if target > nfc_num_devices - 1:
				print 'Reader number %d not found!' % target
				return None
			return devices[target]
		print 'LibNFC ver' , self.libnfc.nfc_version(), 'devices (%d):' % nfc_num_devices
		if nfc_num_devices == 0:
			print '\t', 'no supported devices!'
			return
		for i in range(nfc_num_devices):
			if devices[i]:
				dev = self.libnfc.nfc_open(self.context, ctypes.byref(devices[i]))
				devname= self.libnfc.nfc_device_get_name(dev)
				print '    No: %d\t\t%s' % (i,devname)
				self.libnfc.nfc_close(dev)
				#print '    No: %d\t\t%s (%s)' % (i,devname,devices[i].acDevice)
				#print '    \t\t\t\tDriver:',devices[i].pcDriver
				#if devices[i].pcPort != None:
				#	print '    \t\t\t\tPort:', devices[i].pcPort
				#	print '    \t\t\t\tSpeed:', devices[i].uiSpeed


	def configure(self, nfcreader):
		if rfidiotglobals.Debug:
			self.log.debug("NFC Readers:")
			self.listreaders(None)
			self.log.debug("Connecting to NFC reader number: %s" % repr(nfcreader)) # nfcreader may be none
		if nfcreader != None:
			target=  self.listreaders(nfcreader)
		else:
			target= None 
		if target:
			target= ctypes.byref(target)
		self.device = self.libnfc.nfc_open(self.context, target)
		self.LIBNFC_READER= self.libnfc.nfc_device_get_name(self.device)
		if rfidiotglobals.Debug:
			if self.device == None:
				self.log.error("Error opening NFC reader")
			else:
				self.log.debug("Opened NFC reader " + self.LIBNFC_READER)	
			self.log.debug("Initing NFC reader")
		self.libnfc.nfc_initiator_init(self.device)		
		if rfidiotglobals.Debug:
			self.log.debug("Configuring NFC reader")

  		# Drop the field for a while
		self.libnfc.nfc_device_set_property_bool(self.device,NP_ACTIVATE_FIELD,False);
  	
  		# Let the reader only try once to find a tag
  		self.libnfc.nfc_device_set_property_bool(self.device,NP_INFINITE_SELECT,False);
  		self.libnfc.nfc_device_set_property_bool(self.device,NP_HANDLE_CRC,True);
		self.libnfc.nfc_device_set_property_bool(self.device,NP_HANDLE_PARITY,True);
		self.libnfc.nfc_device_set_property_bool(self.device,NP_ACCEPT_INVALID_FRAMES, True);
  		# Enable field so more power consuming cards can power themselves up
  		self.libnfc.nfc_device_set_property_bool(self.device,NP_ACTIVATE_FIELD,True);

		
	def deconfigure(self):
		if self.device != None:
			if rfidiotglobals.Debug:
				self.log.debug("Deconfiguring NFC reader")
			#self.powerOff()
			self.libnfc.nfc_close(self.device)
			self.libnfc.nfc_exit(self.context)
			if rfidiotglobals.Debug:
				self.log.debug("Disconnected NFC reader")
			self.device = None
			self.context = ctypes.POINTER(ctypes.c_int)()
	
	def powerOn(self):
		self.libnfc.nfc_device_set_property_bool(self.device, NP_ACTIVATE_FIELD, True)
		if rfidiotglobals.Debug:
			self.log.debug("Powered up field")
		self.poweredUp = True
	
	def powerOff(self):
		self.libnfc.nfc_device_set_property_bool(self.device, NP_ACTIVATE_FIELD, False)
		if rfidiotglobals.Debug:
			self.log.debug("Powered down field")
		self.poweredUp = False
	
	def selectISO14443A(self):
		"""Detect and initialise an ISO14443A card, returns an ISO14443A() object."""
		if rfidiotglobals.Debug:
			self.log.debug("Polling for ISO14443A cards")
		#r = self.libnfc.nfc_initiator_select_tag(self.device, IM_ISO14443A_106, None, None, ctypes.byref(ti))
		#r = self.libnfc.nfc_initiator_init(self.device)
		#if RFIDIOtconfig.debug:
		#	self.log.debug('card Select r: ' + str(r))
		#if r == None or r < 0:
		#	if RFIDIOtconfig.debug:
		#		self.log.error("No cards found, trying again")
		#	time.sleep(1)
		#	result = self.readISO14443A()
		#	return result
		#else:
		#	if RFIDIOtconfig.debug:
		#		self.log.debug("Card found")
		self.powerOff()
		self.powerOn()
		nm= NFC_MODULATION()
		target= (NFC_TARGET * MAX_TARGET_COUNT) ()
		nm.nmt = NMT_ISO14443A
		nm.nbr = NBR_106
		if self.libnfc.nfc_initiator_list_passive_targets(self.device, nm, ctypes.byref(target), MAX_TARGET_COUNT):
			return ISO14443A(target[0].nti.nai)
		return None

	def selectISO14443B(self):
		"""Detect and initialise an ISO14443B card, returns an ISO14443B() object."""
		if rfidiotglobals.Debug:
			self.log.debug("Polling for ISO14443B cards")
		self.powerOff()
		self.powerOn()
		nm= NFC_MODULATION()
		target= (NFC_TARGET * MAX_TARGET_COUNT) ()
		nm.nmt = NMT_ISO14443B
		nm.nbr = NBR_106
		if self.libnfc.nfc_initiator_list_passive_targets(self.device, nm, ctypes.byref(target), MAX_TARGET_COUNT):
			return ISO14443B(target[0].nti.nbi)
		return None

	# set Mifare specific parameters
	def configMifare(self):
		self.libnfc.nfc_device_set_property_bool(self.device, NP_AUTO_ISO14443_4, False)
		self.libnfc.nfc_device_set_property_bool(self.device, NP_EASY_FRAMING, True)
		self.selectISO14443A()

	def sendAPDU(self, apdu):
		apdu= "".join([x for x in apdu])
		txData = []		
		for i in range(0, len(apdu), 2):
			txData.append(int(apdu[i:i+2], 16))
	
		txAPDU = ctypes.c_ubyte * len(txData)
		tx = txAPDU(*txData)

		rxAPDU = ctypes.c_ubyte * MAX_FRAME_LEN
		rx = rxAPDU()
	
		if rfidiotglobals.Debug:	
			self.log.debug("Sending %d byte APDU: %s" % (len(tx),"".join(["%02x" % x for x in tx])))
		rxlen = self.libnfc.nfc_initiator_transceive_bytes(self.device, ctypes.byref(tx), ctypes.c_size_t(len(tx)), ctypes.byref(rx), ctypes.c_size_t(len(rx)), -1)
		if rfidiotglobals.Debug:
			self.log.debug('APDU rxlen = ' + str(rxlen))
		if rxlen < 0:
			if rfidiotglobals.Debug:
				self.log.error("Error sending/receiving APDU")
			return False, rxlen
		else:
			rxAPDU = "".join(["%02x" % x for x in rx[:rxlen]])
			if rfidiotglobals.Debug:
				self.log.debug("Received %d byte APDU: %s" % (rxlen, rxAPDU))
			return True, string.upper(rxAPDU)

if __name__ == "__main__":
	n = NFC()
	n.powerOn()
	c = n.readISO14443A()
	print 'UID: ' + c.uid
	print 'ATR: ' + c.atr

	cont = True
	while cont:
		apdu = raw_input("enter the apdu to send now:")
		if apdu == 'exit':
			cont = False
		else:
			r = n.sendAPDU(apdu)
			print r

	print 'Ending now ...'
	n.deconfigure()

########NEW FILE########
__FILENAME__ = RFIDIOt
#  RFIDIOt.py - RFID IO tools for python
# -*- coding: iso-8859-15 -*-
# 
#  Adam Laurie <adam@algroup.co.uk>
#  http://rfidiot.org/
# 
#  This code is copyright (c) Adam Laurie, 2006,7,8,9 All rights reserved.
#  For non-commercial use only, the following terms apply - for all other
#  uses, please contact the author:
#
#    This code is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#

# use Psyco compiler to speed things up if available
try:
	import psyco
	psyco.profile(0.01)
        psyco.full()
except ImportError:
        pass

import os
import sys
import random
import string
import time
from Crypto.Hash import SHA
from Crypto.Cipher import DES3
from Crypto.Cipher import DES
from operator import *
import pynfc
import signal
import socket
import pyandroid

try:
	import smartcard, smartcard.CardRequest
	IOCTL_SMARTCARD_VENDOR_IFD_EXCHANGE = smartcard.scard.SCARD_CTL_CODE(1)
except:
	print '*** Warning - no pyscard installed or pcscd not running'

try:
	from pynfc import get_version
	print
	print '*** Warning - pynfc mismatch!'
	print "*** This is Mike Auty's pynfc which is not what RFIDIOt is expecting!"
except:
	pass

MASK_CCITT = 0x1021 # CRC-CCITT mask (ISO 3309, used in X25, HDLC)
MASK_11785 = 0x8408
MASK_CRC16 = 0xA001 # CRC16 mask (used in ARC files)


class rfidiot:
	DEBUG= False
	readertype= None
	readersubtype= None
	NoInit= False
	NFCReader= None
	pcsc_atr= None
	"RFIDIOt - RFID I/O tools - http://rfidiot.org"
	# local imports
	from iso3166 import ISO3166CountryCodesAlpha
	from iso3166 import ISO3166CountryCodes
	#
	# open reader port
	#
	def __init__(self,readernum,reader,port,baud,to,debug,noinit,nfcreader):
		self.readertype= reader
		self.readersubtype= reader
		readernum= int(readernum)
		self.DEBUG= debug
		self.NoInit= noinit
		self.NFCReader= nfcreader
		if not self.NoInit:
			if self.readertype == self.READER_PCSC:
				try:
					self.pcsc_protocol= smartcard.scard.SCARD_PROTOCOL_T1
				except:
					print 'Could not find PCSC daemon, try with option -n if you don\'t have a reader'
					os._exit(True)
				# select the reader specified
				try:
					self.pcsc= smartcard.System.readers()
				except:
					print 'Could not find PCSC daemon, try with option -n if you don\'t have a reader'
					os._exit(True)
				if readernum >= len(self.pcsc):
					print 'There is no such reader #%i, PCSC sees only %i reader(s)' % (readernum, len(self.pcsc))
					os._exit(True)
				try:
					self.readername= self.pcsc[readernum].name
					self.pcsc_connection= self.pcsc[readernum].createConnection()
					# debug option will show APDU traffic
					if self.DEBUG:
						from smartcard.CardConnectionObserver import ConsoleCardConnectionObserver
						observer=ConsoleCardConnectionObserver()
						self.pcsc_connection.addObserver( observer )
				except:
					print 'Could not create connection to %s' % self.readername
					os._exit(True)
				# determine PCSC subtype
				if string.find(self.readername,'OMNIKEY') == 0:
					self.readersubtype= self.READER_OMNIKEY
				else:
					if string.find(self.readername,'SDI010') == 0:
						self.readersubtype= self.READER_SCM
					else:
						if string.find(self.readername,'ACS ACR122U PICC') == 0:
							self.readersubtype= self.READER_ACS
							self.pcsc_protocol= smartcard.scard.SCARD_PROTOCOL_T1
							self.hcard = None
						elif string.find(self.readername,'ACS') == 0:
							self.readersubtype= self.READER_ACS
							self.pcsc_protocol= smartcard.scard.SCARD_PROTOCOL_T0
							self.hcard = None
						else:
							# default to Omnikey for now
							self.readersubtype= self.READER_OMNIKEY
				if self.DEBUG:
					print 'Reader Subtype:',self.readersubtype
				# create a connection
				try:
					self.pcsc_connection.connect()
					if self.DEBUG:
						print 'pcsc_connection successful'
				except:
					# card may be something like a HID PROX which only returns ATR and does not allow connect
					hresult, hcontext = smartcard.scard.SCardEstablishContext( smartcard.scard.SCARD_SCOPE_USER )
					if hresult != 0:
						raise error, 'Failed to establish context: ' + smartcard.scard.SCardGetErrorMessage(hresult)
					hresult, readers = smartcard.scard.SCardListReaders( hcontext, [] )
					readerstates= [ (readers[readernum], smartcard.scard.SCARD_STATE_UNAWARE ) ]
					hresult, newstates = smartcard.scard.SCardGetStatusChange( hcontext, 0, readerstates )
					if self.readersubtype == self.READER_ACS and self.pcsc_protocol == smartcard.scard.SCARD_PROTOCOL_T1:
						# SCARD_SHARE_SHARED if there is a PICC otherwise SCARD_SHARE_DIRECT
						hresult, hcard, dwActiveProtocol = smartcard.scard.SCardConnect(
							hcontext, readers[readernum], smartcard.scard.SCARD_SHARE_DIRECT, smartcard.scard.SCARD_PROTOCOL_T0 )
						self.hcard = hcard
						# Let's test if we can really use SCardControl, e.g. by sending a get_firmware_version APDU
						apdu = [ 0xFF, 0x00, 0x48, 0x00, 0x00 ]
						hresult, response = smartcard.scard.SCardControl( self.hcard, IOCTL_SMARTCARD_VENDOR_IFD_EXCHANGE, apdu )
						if hresult != smartcard.scard.SCARD_S_SUCCESS:
							print 'Failed to control: ' + smartcard.scard.SCardGetErrorMessage(hresult)
							if hresult == smartcard.scard.SCARD_E_NOT_TRANSACTED:
								print 'Did you set DRIVER_OPTION_CCID_EXCHANGE_AUTHORIZED in ifdDriverOptions in libccid_Info.plist?'
							os._exit(True)
					self.pcsc_atr= self.ListToHex(newstates[0][2])
					pass
				if self.readersubtype == self.READER_ACS:
					self.acs_set_retry(to)
			#libnfc device
			elif self.readertype == self.READER_LIBNFC:
				self.nfc = pynfc.NFC(self.NFCReader)
				self.readername = self.nfc.LIBNFC_READER
			#Andoid reader
			elif self.readertype == self.READER_ANDROID:
				self.android = pyandroid.Android()
				self.readername = "Android"
			elif self.readertype == self.READER_NONE:
				self.readername = 'none'
			else:	
				# frosch always starts at 9600 baud - need to add code to test for selected rate and
				# switch if required. 
				try:
					import serial
					self.ser = serial.Serial(port, baud, timeout=to)
					self.ser.readline()
					self.ser.flushInput()
					self.ser.flushOutput()
				except:
					print 'Could not open serial port %s' % port
					os._exit(True)
	#
	# variables
	#
	# VERSION: RFIDIOt.py version number
	# errorcode: 1 letter errorcode returned by the reader
	#
	# MIFAREdata: ASCII HEX representation of data block after successful read
	# MIFAREbinary: data block converted back to binary
	# MIFAREBLOCKLEN: constant ASCII HEX block length
	# MIFAREVALUELEN: constant ASCII HEX value length
	# MIFAREserialnumber: Unique ID (UID) of card
	# MIFAREkeyA: KEYA from key block (will always be 000000000000)
	# MIFAREkeyB: KEYB from key block
	# MIFAREaccessconditions: access conditions field from Key Block
	# MIFAREC1: Access conditions bitfield C1
	# MIFAREC2: Access conditions bitfield C2
	# MIFAREC3: Access conditions bitfield C3
	# MIFAREblock0AC: Block 0 Access Conditions
	# MIFAREblock1AC: Block 1 Access Conditions
	# MIFAREblock2AC: Block 2 Access Conditions
	# MIFAREblock3AC: Block 3 Access Conditions
	# MIFAREACKB: Human readable Key Block Access Conditions
	# MIFAREACDB: Human readable Data Block Access ConditionsA
	#
	# MRPmrzu: Machine Readable Passport - Machine Readable Zone - Upper
	# MRPmrzl Machine Readable Passport - Machine Readable Zone - Lower
	VERSION= '1.0h'
	# Reader types
	READER_ACG= 0x01
	READER_FROSCH= 0x02
	READER_DEMOTAG= 0x03
	READER_PCSC= 0x04
	READER_OMNIKEY= 0x05
	READER_SCM= 0x06
	READER_ACS= 0x07
	READER_LIBNFC = 0x08
	READER_NONE = 0x09
	READER_ANDROID = 0x10
	# TAG related globals
	errorcode= ''
	binary= ''
	data= ''
	sel_res= ''
	sens_res= ''
	tagtype= ''
	speed= ''
	framesize= ''
	uid= ''
	MIFAREdata=''
	MIFAREbinary=''
	MIFAREBLOCKLEN=32
	MIFAREVALUELEN=8
	MIFAREserialnumber= ''
	MIFAREcheckbyte= ''
	MIFAREmanufacturerdata= ''
	MIFAREkeyA= ''
	MIFAREkeyB= ''
	MIFAREaccessconditions= ''
	MIFAREaccessconditionsuserbyte= ' '
	MIFAREC1= 0
	MIFAREC2= 0
	MIFAREC3= 0
	MIFAREblock0AC= ''
	MIFAREblock1AC= ''
	MIFAREblock2AC= ''
	MIFAREblock3AC= ''
	# PCSC uses 'External Authentication', whereby keys are stored in the reader and then presented to the card. They only need
	# to be set up once per session, so login will store them in a global dictionary.
	# PCSC_Keys= { key : keynum } where keynum is 0 - 31 as per OmniKey docs
	PCSC_Keys= {}
	# Static Globals
	MIFAREACKB= {'000':'Write KeyA: KEYA, Read Access bits: KEYA, Write Access bits: NONE, Read KeyB: KEYA, Write KeyB: KEYA (KEYB readable)',\
		     '010':'Write KeyA: NONE, Read Access bits: KEYA, Write Access bits: NONE, Read KeyB: KEYA, Write KeyB: NONE (KEYB readable)',\
		     '100':'Write KeyA: KEYB, Read Access bits: KEYA/B, Write Access bits: NONE, Read KeyB: NONE, Write KeyB: KEYB',\
		     '110':'Write KeyA: NONE, Read Access bits: KEYA/B, Write Access bits: NONE, Read KeyB: NONE, Write KeyB: NONE',\
		     '001':'Write KeyA: KEYA, Read Access bits: KEYA, Write Access bits: KEYA, Read KeyB: KEYA, Write KeyB: KEYA (KEYB readable, transport configuration)',\
		     '011':'Write KeyA: KEYB, Read Access bits: KEYA/B, Write Access bits: KEYB, Read KeyB: NONE, Write KeyB: KEYB',\
		     '101':'Write KeyA: NONE, Read Access bits: KEYA/B, Write Access bits: KEYB, Read KeyB: NONE, Write KeyB: NONE',\
		     '111':'Write KeyA: NONE, Read Access bits: KEYA/B, Write Access bits: NONE, Read KeyB: NONE, Write KeyB: NONE'}
	MIFAREACDB= {'000':'Read: KEYA/B, Write: KEYA/B, Increment: KEYA/B, Decrement/Transfer/Restore: KEYA/B (transport configuration)',\
		     '010':'Read: KEYA/B, Write: NONE, Increment: NONE, Decrement/Transfer/Restore: NONE',\
		     '100':'Read: KEYA/B, Write: KEYB, Increment: NONE, Decrement/Transfer/Restore: NONE',\
		     '110':'Read: KEYA/B, Write: KEYB, Increment: KEYB, Decrement/Transfer/Restore: KEYA/B',\
		     '001':'Read: KEYA/B, Write: NONE, Increment: NONE, Decrement/Transfer/Restore: KEYA/B',\
		     '011':'Read: KEYB, Write: KEYB, Increment: NONE, Decrement/Transfer/Restore: NONE',\
		     '101':'Read: KEYB, Write: NONE, Increment: NONE, Decrement/Transfer/Restore: NONE',\
		     '111':'Read: NONE, Write: NONE, Increment: NONE, Decrement/Transfer/Restore: NONE'}
	LFXTags= {'U':'EM 4x02 (Unique)',\
		  'Z':'EM 4x05 (ISO FDX-B)',\
		  'T':'EM 4x50',\
		  'h':'Hitag 1 / Hitag S',\
		  'H':'Hitag 2',\
		  'Q':'Q5',\
		  'R':'TI-RFID Systems',\
		  'N':'No TAG present!'}
	# number of data blocks for each tag type (including block 0)
	LFXTagBlocks= {'U':0,\
		  'Z':0,\
		  'T':34,\
		  'h':64,\
		  'H':8,\
		  'Q':8,\
		  'R':18,\
		  'N':0}
	ALL= 'all'
	EM4x02= 'U'
	EM4x05= 'Z'
	Q5= 'Q'
	HITAG1= 'h'
	HITAG2= 'H'
	HITAG2_TRANSPORT_RWD='4D494B52'
	HITAG2_TRANSPORT_TAG='AA4854'
	HITAG2_TRANSPORT_HIGH='4F4E'
	HITAG2_PUBLIC_A= '02'
	HITAG2_PUBLIC_B= '00'
	HITAG2_PUBLIC_C= '04'
	HITAG2_PASSWORD= '06'
	HITAG2_CRYPTO= '0e'
	ACG_FAIL= 'N'
	# Mifare transort keys
	MIFARE_TK= { 'AA' : 'A0A1A2A3A4A5',\
		     'BB' : 'B0B1B2B3B4B5',\
		     'FF' : 'FFFFFFFFFFFF'}
	ISOTags= {'a':'ISO 14443 Type A  ',\
		  'b':'ISO 14443 Type B  ',\
		  'd':'ICODE UID         ',\
		  'e':'ICODE EPC         ',\
		  'i':'ICODE             ',\
		  's':'SR176             ',\
		  'v':'ISO 15693         '}
	ISOTagsA= {'t':'All Supported Tags'}
	ISO15693= 'v'
	# Manufacturer codes (Listed in ISO/IEC 7816-6)
	ISO7816Manufacturer= { '00':'Not Specified',\
			       '01':'Motorola',\
			       '02':'ST Microelectronics',\
			       '03':'Hitachi, Ltd',\
			       '04':'Philips Semiconductors (NXP)',\
			       '05':'Infineon Technologies AG',\
			       '06':'Cylinc',\
			       '07':'Texas Instrument',\
			       '08':'Fujitsu Limited',\
			       '09':'Matsushita Electronics Corporation',\
			       '0a':'NEC',\
			       '0b':'Oki Electric Industry Co. Ltd',\
			       '0c':'Toshiba Corp.',\
			       '0d':'Mitsubishi Electric Corp.',\
			       '0e':'Samsung Electronics Co. Ltd',\
			       '0f':'Hyundai Electronics Industries Co. Ltd',\
			       '10':'LG-Semiconductors Co. Ltd',\
			       '12':'HID Corporation',\
			       '16':'EM Microelectronic-Marin SA',
			       }
	ISOAPDU=  {'ERASE BINARY':'0E',
		   'VERIFY':'20',
		   # Global Platform
		   'INITIALIZE_UPDATE':'50',
		   # GP end
                   'MANAGE_CHANNEL':'70',
                   'EXTERNAL_AUTHENTICATE':'82',
                   'GET_CHALLENGE':'84',
                   'INTERNAL_AUTHENTICATE':'88',
                   'SELECT_FILE':'A4',
                   #vonjeek start
                   'VONJEEK_SELECT_FILE':'A5',
                   'VONJEEK_UPDATE_BINARY':'A6',
                   'VONJEEK_SET_MRZ':'A7',
		   'VONJEEK_SET_BAC':'A8',
		   'VONJEEK_SET_DATASET':'AA',
                   #vonjeek end
		   # special for JCOP
		   'MIFARE_ACCESS':'AA',
		   'ATR_HIST':'AB',
		   'SET_RANDOM_UID':'AC',
		   # JCOP end
                   'READ_BINARY':'B0',
                   'READ_RECORD(S)':'B2',
                   'GET_RESPONSE':'C0',
                   'ENVELOPE':'C2',
                   'GET_DATA':'CA',
                   'WRITE_BINARY':'D0',
                   'WRITE_RECORD':'D2',
                   'UPDATE_BINARY':'D6',
                   'PUT_DATA':'DA',
                   'UPDATE_DATA':'DC',
		   'CREATE_FILE':'E0',
                   'APPEND_RECORD':'E2',
		   # Global Platform
		   'GET_STATUS':'F2',
		   # GP end
		   'READ_BALANCE':'4C',
		   'INIT_LOAD': '40',
		   'LOAD_CMD':'42',
		   'WRITE_MEMORY':'7A',
		   'READ_MEMORY':'78',
		   }
	# some control parameters
	ISO_7816_SELECT_BY_NAME= '04'
	ISO_7816_SELECT_BY_EF= '02'
	ISO_7816_OPTION_FIRST_OR_ONLY= '00'
	ISO_7816_OPTION_NEXT_OCCURRENCE= '02'

	# well known AIDs
	AID_CARD_MANAGER= 'A000000003000000'
	AID_MRTD= 'A0000002471001'
	AID_JAVA_LANG= 'A0000000620001'
	AID_JAVACARD_FRAMEWORK= 'A0000000620101'
	AID_JAVACARD_SECURITY= 'A0000000620102'
	AID_JAVARCARDX_CRYPTO= 'A0000000620201'
	AID_FIPS_140_2= 'A000000167413001'
	AID_JAVACARD_BIOMETRY= 'A0000001320001'
	AID_SECURITY_DOMAIN= 'A0000000035350'
	AID_PKCS_15= 'A000000063'
	AID_JCOP_IDENTIFY= 'A000000167413000FF'
	AID_GSD_MANAGER= 'A000000476A110'
	AIDS= {
		AID_CARD_MANAGER:'Card Manager',
		AID_MRTD:'Machine Readable Travel Document',
		AID_JAVA_LANG:'java.lang',
		AID_JAVACARD_FRAMEWORK:'javacard.framework',
		AID_JAVACARD_SECURITY:'javacard.security',
		AID_JAVARCARDX_CRYPTO:'javacardx.crypto',
		AID_FIPS_140_2:'FIPS 140-2',
		AID_JAVACARD_BIOMETRY:'org.javacardforum.javacard.biometry',
		AID_SECURITY_DOMAIN:'Security Domain',
		AID_PKCS_15:'PKCS15',
		AID_JCOP_IDENTIFY:'JCOP Identify',
		AID_GSD_MANAGER:'GSD Manager',
	}


	# Global Platform
	CLA_GLOBAL_PLATFORM= '80'
	GP_MAC_KEY= '404142434445464748494A4B4C4D4E4F'
	GP_ENC_KEY= '404142434445464748494A4B4C4D4E4F'
	GP_KEK_KEY= '404142434445464748494A4B4C4D4E4F'
	GP_NO_ENCRYPTION= '00'
	GP_C_MAC= '01'
	GP_C_MAC_DECRYPTION= '02'
	GP_SCP02= '02'
	GP_REG_DATA= 'E3'
	GP_REG_AID= '4F'
	GP_REG_LCS= '9F70'
	GP_REG_PRIV= 'C5'
	GP_FILTER_ISD= '80'
	GP_FILTER_ASSD= '40'
	GP_FILTER_ELF= '20'

	ISO_OK= '9000'
	ISO_SECURE= '6982'
	ISO_NOINFO= '6200'

	ISO_SPEED= {'00':'106kBaud',\
		    '02':'212kBaud',\
		    '04':'424kBaud',\
		    '08':'848kBaud'}
	ISO_FRAMESIZE= { '00':'16',\
			 '01':'24',\
			 '02':'32',\
			 '03':'40',\
			 '04':'48',\
			 '05':'64',\
			 '06':'96',\
			 '07':'128',\
			 '08':'256'}
	ISO7816ErrorCodes=  {
			    '61':'SW2 indicates the number of response bytes still available',
			    '6200':'No information given',
			    '6281':'Part of returned data may be corrupted',
			    '6282':'End of file/record reached before reading Le bytes',
			    '6283':'Selected file invalidated',
			    '6284':'FCI not formatted according to ISO7816-4 section 5.1.5',
			    '6300':'No information given',
			    '6301':'ACR: PN532 does not respond',
			    '6327':'ACR: Contacless Response invalid checksum',
			    '637F':'ACR: PN532 invalid Contactless Command',
			    '6381':'File filled up by the last write',
			    '6382':'Card Key not supported',
			    '6383':'Reader Key not supported',
			    '6384':'Plain transmission not supported',
			    '6385':'Secured Transmission not supported',
			    '6386':'Volatile memory not available',
			    '6387':'Non Volatile memory not available',
			    '6388':'Key number not valid',
			    '6389':'Key length is not correct',
			    '63C':'Counter provided by X (valued from 0 to 15) (exact meaning depending on the command)',
			    '64':'State of non-volatile memory unchanged (SW2=00, other values are RFU)',
			    '6400':'Card Execution error',
			    '6500':'No information given',
			    '6581':'Memory failure',
			    '66':'Reserved for security-related issues (not defined in this part of ISO/IEC 7816)',
			    '6700':'Wrong length',
			    '6800':'No information given',
			    '6881':'Logical channel not supported',
			    '6882':'Secure messaging not supported',
			    '6900':'No information given',
			    '6981':'Command incompatible with file structure',
			    '6982':'Security status not satisfied',
			    '6983':'Authentication method blocked',
			    '6984':'Referenced data invalidated',
			    '6985':'Conditions of use not satisfied',
			    '6986':'Command not allowed (no current EF)',
			    '6987':'Expected SM data objects missing',
			    '6988':'SM data objects incorrect',
			    '6A00':'No information given',
			    '6A80':'Incorrect parameters in the data field',
			    '6A81':'Function not supported',
			    '6A82':'File not found',
			    '6A83':'Record not found',
			    '6A84':'Not enough memory space in the file',
			    '6A85':'Lc inconsistent with TLV structure',
			    '6A86':'Incorrect parameters P1-P2',
			    '6A87':'Lc inconsistent with P1-P2',
			    '6A88':'Referenced data not found',
			    '6B00':'Wrong parameter(s) P1-P2',
			    '6C':'Wrong length Le: SW2 indicates the exact length',
			    '6D00':'Instruction code not supported or invalid',
			    '6E00':'Class not supported',
			    '6F00':'No precise diagnosis',
			    '9000':'No further qualification',
			    'ABCD':'RFIDIOt: Reader does not support this command',
			    'F':'Read error or Security status not satisfied',
			    'FFFB':'Mifare (JCOP) Block Out Of Range',
			    'FFFF':'Unspecified Mifare (JCOP) Error',
			    'N':'No precise diagnosis',
			    'PC00':'No TAG present!',
			    'PC01':'PCSC Communications Error',
			    'PN00': 'PN531 Communications Error',
			    'R':'Block out of range',
			    'X':'Authentication failed',
			    }
	DES_IV='\0\0\0\0\0\0\0\0'
	DES_PAD= [chr(0x80),chr(0),chr(0),chr(0),chr(0),chr(0),chr(0),chr(0)]
	DES_PAD_HEX= '8000000000000000'
	KENC= '\0\0\0\1'
	KMAC= '\0\0\0\2'
	DO87= '870901'
	DO8E= '8E08'
	DO97= '9701'
	DO99= '99029000'
	#
	# frosch command set
	#
	#
	# Reader Key Init Mode (update internal secret key)
	FR_RWD_Key_Init_Mode= chr(0x4B)
	# Reader Key Init Mode Reset (exit key init mode)
	FR_RWD_KI_Reset= chr(0x52)
	# READER Key Init Mode Read EEPROM
	FR_RWD_KI_Read_EE_Data= chr(0x58)
	# Reader Stop
	FR_RWD_Stop_Cmd= chr(0xA6)
	# Reader Reset
	FR_RWD_HF_Reset= chr(0x68)
	# Reader Version
	FR_RWD_Get_Version= chr(0x56)
	# Hitag1 Get Serial Number
	FR_HT1_Get_Snr= chr(0x47)
	# Hitag1 Get Serial Number & set tag into Advanced Protocol Mode
	FR_HT1_Get_Snr_Adv= chr(0xA2)
	# Hitag1 Select Last Seen
	FR_HT1_Select_Last= chr(0x53)
	# Hitag1 Select Serial Number
	FR_HT1_Select_Snr= chr(0x53)
	# Hitag1 Read Page
	FR_HT1_Read_Page= chr(0x50)
	# Hitag2 Get Serial Number (password mode)
	FR_HT2_Get_Snr_PWD= chr(0x80) + chr(0x00)
	# Hitag2 Get Serial Number Reset (to reset for normal access when in public modes)
	FR_HT2_Get_Snr_Reset= chr(0x80)
	# Hitag2 Halt Selected
	FR_HT2_Halt_Selected= chr(0x81)
	# Hitag2 read page
	FR_HT2_Read_Page= chr(0x82)
	# Hitag2 Read Miro (Unique / Public Mode A)
	FR_HT2_Read_Miro= chr(0x4d)
	# Hitag2 Read Public B (FDX-B)
	FR_HT2_Read_PublicB= chr(0x9e)
	# Hitag2 Write Page
	FR_HT2_Write_Page= chr(0x84)
	#
	# frosch errors
	#
	FROSCH_Errors= { '00':'No Error',\
			 '02':'Error',\
			 '07':'No Error',\
			 'eb':'Antenna Overload',\
			 'f1':'EEPROM Read Protected',\
			 'f2':'EEPROM Write Protected',\
			 'f3':'EEPROM Wrong - Old Data',\
			 'f4':'EEPROM Error',\
			 'f5':'CryptoBlock not INIT',\
			 'f6':'Acknowledgement Error',\
			 'f9':'Authentication Error',\
			 'fa':'Incorrect Password TAG',\
			 'fb':'Incorrect Password RWD',\
			 'fc':'Timeout',\
			 'fd':'No TAG present!',\
			 'ff':'Serial port fail or wrong mode'}
	# 
	# frosch constants
	#
	FR_BAUD_RATE= {   9600:chr(0x01),\
		   	 14400:chr(0x02),\
		   	 19200:chr(0x03),\
		   	 38400:chr(0x04),\
		   	 57600:chr(0x05),\
		  	115200:chr(0x06)}
	FR_NO_ERROR= chr(0x00)
	FR_PLAIN= chr(0x00)
	FR_CRYPTO= chr(0x01)
	FR_TIMEOUT= 'fc'
	FR_COMMAND_MODE= 0x00
	FR_KEY_INIT_MODE= 0x01
	#
	# frosch statics
	#
	FR_BCC_Mode= FR_COMMAND_MODE
	#
	# DemoTag command set
	#
	DT_SET_UID= 'u'
	#
	# DemoTag Errors
	#
	DT_ERROR= '?'
	#
	# PCSC APDUs
	#
	# these are basically standard APDUs but with fields filled in and using OmniKey terminology
	# should really unify them all, but for now...
	# COMMAND : [Class, Ins, P1, P2, DATA, LEN]
	PCSC_APDU= {
		    'ACS_14443_A' : ['d4','40','01'],
		    'ACS_14443_B' : ['d4','42','02'],
		    'ACS_14443_0' : ['d5','86','80', '05'],
		    'ACS_DISABLE_AUTO_POLL' : ['ff','00','51','3f','00'],
		    'ACS_DIRECT_TRANSMIT' : ['ff','00','00','00'],
		    'ACS_GET_SAM_SERIAL' : ['80','14','00','00','08'],
		    'ACS_GET_SAM_ID' : ['80','14','04','00','06'],
		    'ACS_GET_READER_FIRMWARE' : ['ff','00','48','00','00'],
		    'ACS_GET_RESPONSE' : ['ff','c0','00','00'],
		    'ACS_GET_STATUS' : ['d4','04'],
		    'ACS_IN_LIST_PASSIVE_TARGET' : ['d4','4a'],
		    'ACS_LED_GREEN' : ['ff','00','40','0e','04','00','00','00','00'],
		    'ACS_LED_ORANGE' : ['ff','00','40','0f','04','00','00','00','00'],
		    'ACS_LED_RED' : ['ff','00','40','0d','04','00','00','00','00'],
		    'ACS_MIFARE_LOGIN' : ['d4','40','01'],
		    'ACS_READ_MIFARE' : ['d4','40','01','30'],
		    'ACS_POLL_MIFARE' : ['d4','4a','01','00'],
		    'ACS_POWER_OFF' : ['d4','32','01','00'],
		    'ACS_POWER_ON' : ['d4','32','01','01'],
		    'ACS_RATS_14443_4_OFF' : ['d4','12','24'],
		    'ACS_RATS_14443_4_ON' : ['d4','12','34'],
		    'ACS_SET_PARAMETERS' : ['d4','12'],
		    'ACS_SET_RETRY' : ['d4','32','05','00','00','00'],
		    'AUTHENTICATE' : ['ff', ISOAPDU['INTERNAL_AUTHENTICATE']],
		    'GUID' : ['ff', ISOAPDU['GET_DATA'], '00', '00', '00'],
		    'ACS_GET_ATS' : ['ff', ISOAPDU['GET_DATA'], '01', '00', '00'],
		    'LOAD_KEY' : ['ff',  ISOAPDU['EXTERNAL_AUTHENTICATE']],
		    'READ_BLOCK' : ['ff', ISOAPDU['READ_BINARY']],
		    'UPDATE_BLOCK' : ['ff', ISOAPDU['UPDATE_BINARY']],
		    'VERIFY' : ['ff', ISOAPDU['VERIFY']],
		    'WRITE_BLOCK' : ['ff', ISOAPDU['WRITE_BINARY']],
		    }
	# PCSC Errors
	PCSC_NO_CARD= 'PC00'
	PCSC_COMMS_ERROR= 'PC01'
	PCSC_VOLATILE= '00'
	PCSC_NON_VOLATILE= '20'
	# PCSC Contactless Storage Cards
	PCSC_CSC= '804F'
	# PCSC Workgroup RID
	PCSC_RID= 'A000000306'
	# PCSC Storage Standard Byte
	PCSC_SS= { '00':'No information given',\
		   '01':'ISO 14443 A, part 1',\
		   '02':'ISO 14443 A, part 2',\
		   '03':'ISO 14443 A, part 3',\
		   '04':'RFU',\
		   '05':'ISO 14443 B, part 1',\
		   '06':'ISO 14443 B, part 2',\
		   '07':'ISO 14443 B, part 3',\
		   '08':'RFU',\
		   '09':'ISO 15693, part 1',\
                   '0A':'ISO 15693, part 2',\
                   '0B':'ISO 15693, part 3',\
                   '0C':'ISO 15693, part 4',\
		   '0D':'Contact (7816-10) I2 C',\
		   '0E':'Contact (7816-10) Extended I2 C',\
		   '0F':'Contact (7816-10) 2WBP',\
		   '10':'Contact (7816-10) 3WBP',\
		   'FF':'RFU'}
	# PCSC card names
	PCSC_NAME= { '0000':'No name given',\
		     '0001':'Mifare Standard 1K',\
		     '0002':'Mifare Standard 4K',\
		     '0003':'Mifare Ultra light',\
		     '0004':'SLE55R_XXXX',\
		     '0006':'SR176',\
		     '0007':'SRI X4K',\
		     '0008':'AT88RF020',\
		     '0009':'AT88SC0204CRF',\
		     '000A':'AT88SC0808CRF',\
		     '000B':'AT88SC1616CRF',\
		     '000C':'AT88SC3216CRF',\
		     '000D':'AT88SC6416CRF',\
		     '000E':'SRF55V10P',\
		     '000F':'SRF55V02P',\
		     '0010':'SRF55V10S',\
		     '0011':'SRF55V02S',\
		     '0012':'TAG_IT',\
		     '0013':'LRI512',\
		     '0014':'ICODESLI',\
		     '0015':'TEMPSENS',\
		     '0016':'I.CODE1',\
		     '0017':'PicoPass 2K',\
		     '0018':'PicoPass 2KS',\
		     '0019':'PicoPass 16K',\
		     '001A':'PicoPass 16Ks',\
		     '001B':'PicoPass 16K(8x2)',\
		     '001C':'PicoPass 16KS(8x2)',\
		     '001D':'PicoPass 32KS(16+16)',\
		     '001E':'PicoPass 32KS(16+8x2)',\
		     '001F':'PicoPass 32KS(8x2+16)',\
		     '0020':'PicoPass 32KS(8x2+8x2)',\
		     '0021':'LRI64',\
		     '0022':'I.CODE UID',\
		     '0023':'I.CODE EPC',\
		     '0024':'LRI12',\
		     '0025':'LRI128',\
		     '0026':'Mifare Mini',\
		     '0027':'my-d move (SLE 66R01P)',\
		     '0028':'my-d NFC (SLE 66RxxP)',\
		     '0029':'my-d proximity 2 (SLE 66RxxS)',\
		     '002A':'my-d proximity enhanced (SLE 55RxxE)',\
		     '002B':'my-d light (SRF 55V01P)',\
		     '002C':'PJM Stack Tag (SRF 66V10ST)',\
		     '002D':'PJM Item Tag (SRF 66V10IT)',\
		     '002E':'PJM Light (SRF 66V01ST)',\
		     '002F':'Jewel Tag',\
		     '0030':'Topaz NFC Tag',\
		     '0031':'AT88SC0104CRF',\
		     '0032':'AT88SC0404CRF',\
		     '0033':'AT88RF01C',\
		     '0034':'AT88RF04C',\
		     '0035':'i-Code SL2',\
		     '0036':'MIFARE Plus SL1_2K',\
		     '0037':'MIFARE Plus SL1_4K',\
		     '0038':'MIFARE Plus SL2_2K',\
		     '0039':'MIFARE Plus SL2_4K',\
		     '003A':'MIFARE Ultralight C',\
		     '003B':'FeliCa',\
		     '003C':'Melexis Sensor Tag (MLX90129)',\
		     '003D':'MIFARE Ultralight EV1',\
		     }
	# ACS Constants
	ACS_TAG_FOUND= 'D54B'
	ACS_DATA_OK= 'D541'
	ACS_NO_SAM= '3B00'
	ACS_TAG_MIFARE_ULTRA= 'MIFARE Ultralight'
	ACS_TAG_MIFARE_1K= 'MIFARE 1K'
	ACS_TAG_MIFARE_MINI= 'MIFARE MINI'
	ACS_TAG_MIFARE_4K= 'MIFARE 4K'
	ACS_TAG_MIFARE_DESFIRE= 'MIFARE DESFIRE'
	ACS_TAG_JCOP30= 'JCOP30'
	ACS_TAG_JCOP40= 'JCOP40'
	ACS_TAG_MIFARE_OYSTER= 'London Transport Oyster'
	ACS_TAG_GEMPLUS_MPCOS= 'Gemplus MPCOS'

	ACS_TAG_TYPES=	{
			'00':ACS_TAG_MIFARE_ULTRA,
			'08':ACS_TAG_MIFARE_1K,
			'09':ACS_TAG_MIFARE_MINI,
			'18':ACS_TAG_MIFARE_4K,
			'20':ACS_TAG_MIFARE_DESFIRE,
			'28':ACS_TAG_JCOP30,
			'38':ACS_TAG_JCOP40,
			'88':ACS_TAG_MIFARE_OYSTER,
			'98':ACS_TAG_GEMPLUS_MPCOS,
			}
	# HID constants
	HID_PROX_H10301_H= '3B0500'
	HID_PROX_H10301= '3B0601'
	HID_PROX_H10302= '3B0702'
	HID_PROX_H10302_H= '3B0600'
	HID_PROX_H10304= '3B0704'
	HID_PROX_H10320= '3B0514'
	HID_PROX_CORP1K= '3B0764'
	HID_PROX_TYPES=	{
			HID_PROX_H10301_H:'HID Prox H10301 - 26 bit (FAC + CN)',
			HID_PROX_H10301:'HID Prox H10301 - 26 bit (FAC + CN)',
			HID_PROX_H10302:'HID Prox H10302 - 37 bit (CN)',
			HID_PROX_H10302_H:'HID Prox H10302 - 37 bit (CN)',
			HID_PROX_H10304:'HID Prox H10304 - 37 bit (FAC + CN)',
			HID_PROX_H10320:'HID Prox H10320 - 32 bit clock/data card',
			HID_PROX_CORP1K:'HID Prox Corp 1000 - 35 bit (CIC + CN)',
			}
	#
	# local/informational functions
	#
	def info(self,caller):
		if len(caller) > 0:
			print caller + ' (using RFIDIOt v' + self.VERSION + ')'
		if not self.NoInit:
			self.reset()
			self.version()
			if len(caller) > 0:
				print '  Reader:',
			if self.readertype == self.READER_ACG:
				print 'ACG ' + self.readername,
				print ' (serial no: ' + self.id() + ')'
			if self.readertype == self.READER_FROSCH:
				print 'Frosch ' + self.ToBinary(self.data[:16]) + ' / ' + self.ToBinary(self.data[16:32]),
				print ' (serial no: ' + self.data[32:54] + ')'
			if self.readertype == self.READER_PCSC:
				print 'PCSC ' + self.readername
				if self.readersubtype == self.READER_ACS and self.pcsc_protocol == smartcard.scard.SCARD_PROTOCOL_T0:
					# get ATR to see if we have a SAM
					self.select()
					if not self.pcsc_atr[:4] == self.ACS_NO_SAM:
						if self.acs_get_firmware_revision():
							print '          (Firmware: %s, ' % self.ToBinary(self.data),
						else:
							print "\ncan't get firmware revision!"
							os._exit(True)
						if self.acs_get_sam_serial():
							print 'SAM Serial: %s, ' % self.data,
						else:
							print "\ncan't get SAM Serial Number!"
							os._exit(True)
						if self.acs_get_sam_id():
							print 'SAM ID: %s)' % self.ToBinary(self.data)
						else:
							print "\ncan't get SAM Serial Number!"
							os._exit(True)
				elif self.readersubtype == self.READER_ACS and self.pcsc_protocol == smartcard.scard.SCARD_PROTOCOL_T1:
					if self.acs_get_firmware_revision():
						print '          (Firmware: %s)' % self.ToBinary(self.data)
					else:
						print "\ncan't get firmware revision!"
						os._exit(True)
			if self.readertype == self.READER_LIBNFC:			
				print 'LibNFC', self.readername
			if self.readertype == self.READER_ANDROID:			
				print 'Android Reader'
			print
	#
	# reader functions
	#
        def reset(self):
		if self.readertype == self.READER_ACG:
			# send a select to stop just in case it's in multi-select mode
			self.ser.write('s')
			self.ser.readline()
			self.ser.flushInput()
			self.ser.flushOutput()
			# now send a reset and read response
			self.ser.write('x')
			self.ser.readline()
			# now send a select and read remaining lines
			self.ser.write('s')
			self.ser.readline()
			self.ser.flushInput()
			self.ser.flushOutput()
			return True
		if self.readertype == self.READER_FROSCH:
			if self.frosch(self.FR_RWD_HF_Reset,''):
				return True
			else:
				print self.FROSCH_Errors[self.errorcode]
				os._exit(True)
		if self.readertype == self.READER_PCSC:
			if self.readersubtype == self.READER_ACS:
				self.acs_power_off()			
				self.acs_power_on()			
			self.data= 'A PCSC Reader (need to add reset function!)'
		if self.readertype == self.READER_LIBNFC:
			self.nfc.powerOff()
			self.nfc.powerOn()
		if self.readertype == self.READER_ANDROID:
			self.android.reset()
			
	def version(self):
		if self.readertype == self.READER_ACG:
			self.ser.write('v')
			try:
				self.data= self.ser.readline()[:-2]
				self.readername= self.data
			except:
				print '\nReader not responding - check baud rate'
				os._exit(True)
			# check for garbage data (wrong baud rate)
			if not self.data or self.data[0] < ' ' or self.data[0] > '~':
				print '\nGarbage received from reader - check baud rate'
				os._exit(True)
			return True
		if self.readertype == self.READER_FROSCH:
			if self.frosch(self.FR_RWD_Get_Version,''):
				return True
			else:
				print self.FROSCH_Errors[self.errorcode]
				os._exit(True)
		if self.readertype == self.READER_ANDROID:
			print 'Android version: ', self.android.VERSION
	def id(self):
		return self.readEEPROM(0)[:2] + self.readEEPROM(1)[:2] + self.readEEPROM(2)[:2] + self.readEEPROM(3)[:2]
	def station(self):
		return self.readEEPROM(0x0a)[:2]
	def PCON(self):
		return self.readEEPROM(0x0b)[:2]
	def PCON2(self):
		return self.readEEPROM(0x13)[:2]
	def PCON3(self):
		return self.readEEPROM(0x1b)[:2]
	def BAUD(self):
		return self.readEEPROM(0x0c)[:2]
	def CGT(self):
		return self.readEEPROM(0x0d)[:2]
	def opmode(self):
		return self.readEEPROM(0x0e)[:2]
	def SST(self):
		return self.readEEPROM(0x0f)[:2]
	def ROT(self):
		return self.readEEPROM(0x14)[:2]
	def RRT(self):
		return self.readEEPROM(0x15)[:2]
	def AFI(self):
		return self.readEEPROM(0x16)[:2]
	def STOa(self):
		return self.readEEPROM(0x17)[:2]
	def STOb(self):
		return self.readEEPROM(0x18)[:2]
	def STOs(self):
		return self.readEEPROM(0x19)[:2]
	def readEEPROM(self,byte):
		self.ser.write('rp%02x' % byte)
		return self.ser.readline()[:2]
	def writeEEPROM(self,byte,value):
		self.ser.write('wp%02x%02x' % (byte,value))
		self.errorcode= self.ser.readline()[:-2]
		if eval(self.errorcode) == value:
			return True
		return False
	def settagtype(self,type):
		if self.readertype == self.READER_ACG:
			# ACG HF reader uses 't' for 'all', LF uses 'a'
			if type == self.ALL:
				if string.find(self.readername,'LFX') == 0:
					type= 'a'
				else:
					type= 't'
			self.ser.write('o' + type)
			self.errorcode= self.ser.readline()[:-2]
			if self.errorcode == 'O' + string.upper(type):
				self.tagtype= type
				return True
		if self.readertype == self.READER_FROSCH:
			if type == self.EM4x02:
				return self.frosch(self.FR_HT2_Read_Miro,'')			
			if type == self.EM4x05:
				return self.frosch(self.FR_HT2_Read_PublicB,'')
		return False
	#
	# card functions
	#
	def pcsc_listreaders(self):
		n= 0
		print 'PCSC devices:'
		#for reader in self.pcsc.listReader():
		for reader in self.pcsc:
			print '    No: %d\t\t%s' % (n,reader)
			n += 1
	def libnfc_listreaders(self):
		self.nfc.listreaders(self.NFCReader)
	def waitfortag(self,message):
		if message:
			print message,
			sys.stdout.flush()
		# we need a way to interrupt infinite loop
		if self.readersubtype == self.READER_OMNIKEY or self.readersubtype == self.READER_SCM:
			wait=True
			while wait:
				try:
					self.pcsc_connection.connect()
					self.select()
					wait=False
				except:
					sys.stdin.flush()
					time.sleep(0.5)
		else:
			while not self.select():
				# do nothing
				time.sleep(0.1)
		return True
	def select(self, cardtype='A'):
		if self.DEBUG:
			print 'in select'
		self.uid= ''
		# return True or False and set tag type and data
		if self.readertype == self.READER_ACG:
			if self.DEBUG:
				print 'selecting card using ACG'
			self.ser.write('s')
			self.data= self.ser.readline()[:-2]
			self.tagtype= self.data[:1]
			if self.tagtype == self.ACG_FAIL:
				self.errorcode= self.PCSC_NO_CARD
				return False
			# strip leading tag type from LFX response
			if self.readername.find("LFX") == 0:
				self.uid= self.data[1:]
			else:
				self.uid= self.data
			return True
		if self.readertype == self.READER_FROSCH:
			if self.DEBUG:
				print 'selecting card using FROSCH'
			if self.frosch(self.FR_HT2_Get_Snr_PWD,''):
				# select returns an extra byte on the serial number, so strip it
				self.data= self.data[:len(self.data) - 2]
				self.tagtype= self.HITAG2
				self.uid= self.data
				return True
			if self.frosch(self.FR_HT1_Get_Snr,''):
				# select returns an extra byte on the serial number, so strip it
				# and preserve for after select command
				serialno= self.data[:len(self.data) - 2]
				if self.frosch(self.FR_HT1_Select_Last,''):
					self.tagtype= self.HITAG1
					self.data= self.uid= serialno
					return True
			return False
		if self.readertype == self.READER_PCSC:
			if self.DEBUG:
				print 'selecting card using PCSC'
			try:
				# start a new connection in case TAG has been switched
				self.pcsc_connection.disconnect()
				self.pcsc_connection.connect()
				time.sleep(0.6)	
				self.pcsc_atr= self.ListToHex(self.pcsc_connection.getATR())
				atslen= 2 * int(self.pcsc_atr[3],16)
				self.pcsc_ats= self.pcsc_atr[8:8 + atslen]
				if self.readersubtype == self.READER_ACS:
					self.acs_select_tag()
				else:
					self.pcsc_send_apdu(self.PCSC_APDU['GUID'])
			except smartcard.Exceptions.NoCardException:
				self.errorcode= self.PCSC_NO_CARD
				return False
			except:
				self.errorcode= self.PCSC_COMMS_ERROR
				return False
			if self.errorcode == self.ISO_OK:
				self.uid= self.data
				if not self.readersubtype == self.READER_ACS:
					self.tagtype= self.PCSCGetTagType(self.pcsc_atr)
				# pcsc returns ISO15693 tags LSByte first, so reverse
				if string.find(self.tagtype,'ISO 15693') >= 0:
					self.data= self.uid= self.HexByteReverse(self.data)
				return True
			else:
				return False
		if self.readertype == self.READER_LIBNFC:
			try:
				if self.DEBUG:
					print 'selecting card using LIBNFC'
				if cardtype == 'A':
					result = self.nfc.selectISO14443A()
					if result:
						self.atr = result.atr
						self.uid = result.uid
						if self.DEBUG:
							print 'UID: ' + self.uid
						return True
					else:
						if self.DEBUG:
							print 'Error selecting card'
						return False
				else:
					if cardtype == 'B':
						result = self.nfc.selectISO14443B()
						if result:
							self.pupi = result.pupi
							self.atr = result.atr
							self.uid = result.uid
							if self.DEBUG:
								print 'PUPI: ' + self.pupi
							return True
						else:
							if self.DEBUG:
								print 'Error selecting card'
							return False
					else:
						if self.DEBUG:
							print 'Error: Unknown card type specified: %s' % cardtype
						return False
			except ValueError:
				self.errorcode = 'Error selecting card using LIBNFC' + e
		
		if self.readertype == self.READER_ANDROID:
			try:
				if self.DEBUG:
					print 'Reading card using Android'
				uid = self.android.select()
				if uid:
					self.uid = uid
					if self.DEBUG:
						print '\tUID: ' + self.uid
					return True
				else:
					if self.DEBUG:
						print 'Error selecting card'
					return False
			except ValueError:
				self.errorcode = 'Error reading card using Android' + e
		return False
	def h2publicselect(self):
		"select Hitag2 from Public Mode A/B/C"
		if self.readertype == self.READER_FROSCH:
			if (self.frosch(self.FR_HT2_Get_Snr_Reset,self.FR_PLAIN + 'M')):
				self.tagtype= self.HITAG2
				self.data= self.data[:8]
				return True
		return False
	def h2login(self,password):
		"login to hitag2 in password mode"
		if not self.readertype == self.READER_ACG:
			print 'Reader type not supported for hitag2login!'
			return False
		self.ser.write('l'+password)
		ret= self.ser.readline()[:-2]
		if ret == self.ACG_FAIL:
			self.errorcode= ret
			return False
		return True
	def hsselect(self,speed,cardtype='A'):
		if self.readertype == self.READER_PCSC or self.readertype == self.READER_LIBNFC or self.READER_ANDROID:
			# low level takes care of this, so normal select only
			if self.select(cardtype):
				#fixme - find true speed/framesize
				self.speed= '04'
				self.framesize= '08'
				return True
			else:
				return False
		"high speed select - 106 (speed= 01), 212 (speed= 02), 424 (speed= 04) or 848 (speed= 08) kBaud"
		self.ser.write('h'+speed)
		ret= self.ser.readline()[:-2]
		if ret == self.ACG_FAIL:
			self.errorcode= ret
			return False
		sizebaud= ret[-2:]
		self.speed= '%02d' % int(sizebaud[-1:])
		self.framesize= '%02d' % int(sizebaud[:-1])
		self.data= ret[:-2]
		return True
	# ACS specific commands
	#
	# note there are 2 different types of ACS command:
	#   
	#    standard APDU for reader - acs_send_reader_apdu
	#    pseudo APDU for contact or contactless card - acs_send_apdu
	#	
	# contact and contacless commands are wrapped and passed to the NXP PN532 for processing
	def acs_send_apdu(self,apdu):
		"ACS send APDU to contacless card"
		myapdu= self.HexArraysToArray(apdu)
		# determine if this is for direct transmission to the card
		if myapdu[0] == 'd4':
			# build pseudo command for ACS contactless interface
			lc= '%02x' % len(myapdu)
			apduout= self.HexArrayToList(self.PCSC_APDU['ACS_DIRECT_TRANSMIT']+[lc]+myapdu)
		else:
			if  myapdu[0] == 'ff' or myapdu[0] == '80':
				apduout= self.HexArrayToList(myapdu)
			else:
				# build pseudo command for ACS 14443-A
				lc= '%02x' % (len(myapdu) + len(self.PCSC_APDU['ACS_14443_A']))
				apduout= self.HexArrayToList(self.PCSC_APDU['ACS_DIRECT_TRANSMIT']+[lc]+self.PCSC_APDU['ACS_14443_A']+myapdu)
		result, sw1, sw2= self.acs_transmit_apdu(apduout)
		self.errorcode= '%02X%02X' % (sw1,sw2)
		if self.errorcode == self.ISO_OK:
			self.data= self.ListToHex(result)
			if not myapdu[0] == 'ff' and not myapdu[0] == '80' and not myapdu[0] == 'd4':
				# this is a 14443-A command, so needs further processing
				# last 4 data bytes is status of wrapped command
				if self.data[-4:] == self.ISO_OK and len(self.data) > 6:
					# strip first 6 hex characters (ACS specific)
					self.data= self.data[6:]
					# strip last 4 to remove errorcode
					self.data= self.data[:-4]
					return True
				else:
					self.errorcode= self.data[-4:]
					# strip ACS status and errorcode in case there is some data expected despite error
					self.data= self.data[6:-4]
					return False
			return True
		self.data= ''
		return False
	def acs_transmit_apdu(self,apdu):
		"ACS send APDU and retrieve additional DATA if required"
		if self.hcard is None:
			result, sw1, sw2= self.pcsc_connection.transmit(apdu,protocol= self.pcsc_protocol)
			if sw1 == 0x61:
				# response bytes waiting
				apduout= self.HexArrayToList(self.PCSC_APDU['ACS_GET_RESPONSE']+[('%02x' % sw2)])
				result, sw1, sw2= self.pcsc_connection.transmit(apduout,protocol= self.pcsc_protocol)
			return result, sw1, sw2
		else:
			hresult, response = smartcard.scard.SCardControl( self.hcard, IOCTL_SMARTCARD_VENDOR_IFD_EXCHANGE, apdu )
			if hresult != smartcard.scard.SCARD_S_SUCCESS:
				return '',0x63,0x00
				#print 'Failed to control: ' + smartcard.scard.SCardGetErrorMessage(hresult)
				#os._exit(True)
			# evil hacky bodge as ACS returns only one byte for this APDU (ACS_DISABLE_AUTO_POLL)
			# and we ignore failure of we're running on firmware V1 as it doesn't support this command
			if apdu == [0xff,0x00,0x51,0x3f,0x00]:
				#print 'here!!!'
				if response == [0x3f] or self.hcard is not None:
					return '',0x90,0x00
				else:
					return '',0x63,0x00
			result = response[:-2]
			sw1 = response[-2]
			sw2 = response[-1]
			return result, sw1, sw2

	def acs_send_reader_apdu(self,apdu):
		"ACS send APDU to reader"
		myapdu= self.HexArraysToArray(apdu)
		apduout= self.HexArrayToList(myapdu)
		result, sw1, sw2= self.acs_transmit_apdu(apduout)
		self.data= self.ListToHex(result)
		self.errorcode= '%02X%02X' % (sw1,sw2)
		return True
	def acs_send_direct_apdu(self,apdu):
		"ACS send APDU direct to TAG"
		myapdu= self.HexArraysToArray(apdu)
		# build pseudo command for ACS 14443-A via NXP PN532
		lc= '%02x' % (len(myapdu) + len(self.PCSC_APDU['ACS_14443_A']))
		apduout= self.HexArrayToList(self.PCSC_APDU['ACS_DIRECT_TRANSMIT']+[lc]+self.PCSC_APDU['ACS_14443_A']+myapdu)		
		result, sw1, sw2= self.acs_transmit_apdu(apduout)
		self.errorcode= '%02X%02X' % (sw1,sw2)
		if self.errorcode == self.ISO_OK:
			self.data= self.ListToHex(result)
			# strip direct wrapper response and header to get TAG response and DATA
			if self.data[-4:] == self.ISO_OK and len(self.data) > 6:
				self.data= self.data[6:]
				self.data= self.data[:-4]
				return True
			else:
				self.errorcode= self.data[-4:]
				# strip ACS status and errorcode in case there is some data expected despite error
				self.data= self.data[6:-4]
				return False
			return True
		else:
			self.data= ''
			return False	
	def acs_rats(self,control):
		"ACS RATS on/off"
		if control:
			return self.acs_send_apdu(self.PCSC_APDU['ACS_RATS_14443_4_ON'])
		else:
			return self.acs_send_apdu(self.PCSC_APDU['ACS_RATS_14443_4_OFF'])
	def acs_mifare_login(self,block,key,keytype):
		"ACS Mifare Login"
		if keytype == 'BB':
			keytype= '61'
		else:
		   keytype= '60'
		loginblock= '%02x' % block
		if self.tagtype == self.ACS_TAG_MIFARE_1K or self.tagtype == self.ACS_TAG_MIFARE_4K:
			status= self.acs_send_apdu(self.PCSC_APDU['ACS_MIFARE_LOGIN']+[keytype]+[loginblock]+[key]+[self.uid])
		else:
			self.errorcode= self.ISO_NOINFO
			return False
		if not status or not self.data[:4] == self.ACS_DATA_OK or not self.data[4:6] == '00':
			self.errorcode= self.ISO_NOINFO
			return False
		self.errorcode= self.ISO_OK
		return True
	def acs_read_block(self,block):
		"ACS READ Block"
		readblock= '%02x' % block
		read= False
		if self.tagtype == self.ACS_TAG_MIFARE_ULTRA or self.tagtype == self.ACS_TAG_MIFARE_1K or self.tagtype == self.ACS_TAG_MIFARE_4K:
			status= self.acs_send_apdu(self.PCSC_APDU['ACS_READ_MIFARE']+[readblock])
			read= True
		if read:
			if not status or len(self.data) < 8 or not self.data[:4] == self.ACS_DATA_OK:
				self.errorcode= self.ISO_NOINFO
				return False
			# MIFARE ultralight returns 4 blocks although only asking for one, so truncate
			if self.tagtype == self.ACS_TAG_MIFARE_ULTRA:
				self.data= self.data[6:14]
			else:
				self.data= self.data[6:]
			self.errorcode= self.ISO_OK
			return True
		print "Can't read %s blocks" % self.ACS_TAG_TYPES[self.tagtype]
		os._exit(True)
	def acs_get_sam_serial(self):
		"ACS get SAM serial"
		return self.acs_send_apdu(self.PCSC_APDU['ACS_GET_SAM_SERIAL'])
	def acs_get_sam_id(self):
		"ACS get SAM id"
		return self.acs_send_apdu(self.PCSC_APDU['ACS_GET_SAM_ID'])
	def acs_set_retry(self,time):
		"ACS set retry"
		# 'time' currently ignored due to lack of documentation - hard wired to '1'
		return self.acs_send_apdu(self.PCSC_APDU['ACS_SET_RETRY'])
	def acs_select_tag(self):
		"ACS select TAG"
		# power antenna off and on to reset ISO14443-4 tags
		self.reset()
		self.acs_send_apdu(self.PCSC_APDU['ACS_POLL_MIFARE'])
		if not self.data[:4] == self.ACS_TAG_FOUND:
			# this shouldn't happen as the command should return number of tags to be 0 instead
			return False
		tags= int(self.data[4:6])
		if tags == 0:
			self.errorcode= self.PCSC_NO_CARD
			return False
		target= self.data[6:8]
		self.sens_res= self.data[8:12]
		self.sel_res= self.data[12:14]
		length= int(self.data[14:16])
		if length == 0:
			self.errorcode= self.PCSC_NO_CARD
			return False
		uid= self.data[16:16+length*2]
		try:
			self.tagtype= self.ACS_TAG_TYPES[self.sel_res]
		except:
			print 'unrecognised TAG type:', self.sel_res
			print 'full ACS return:', self.data
			self.tagtype= 'Unrecognised'
		self.data= uid
		return True
	def acs_get_firmware_revision(self):
		"ACS Get Firmware Revision"
                self.acs_send_reader_apdu(self.PCSC_APDU['ACS_GET_READER_FIRMWARE'])
		# 'special' APDU that doesn't return in the usual way. sw1,sw2 contains some of the data
		if len(self.data) > 0:
	                self.data += self.errorcode
			self.errorcode= self.ISO_OK
			return True
		self.data= ''
		self.errorcode= self.ISO_NOINFO
		return False
	def acs_power_on(self):
		"ACS Antenna Power On"
		return self.acs_send_apdu(self.PCSC_APDU['ACS_POWER_ON'])
	def acs_power_off(self):
		"ACS Antenna Power Off"
		return self.acs_send_apdu(self.PCSC_APDU['ACS_POWER_OFF'])
	# libNFC specific commands
	def libnfc_mifare_login(self,block,key,keytype):
		"libNFC Mifare Login"
		self.nfc.configMifare()
		if keytype == 'BB':
			keytype= '%02x' % pynfc.MC_AUTH_B
		else:
		   keytype= '%02x' % pynfc.MC_AUTH_A
		loginblock= '%02x' % block
		#if self.tagtype == self.ACS_TAG_MIFARE_1K or self.tagtype == self.ACS_TAG_MIFARE_4K:
		ret, self.errorcode= self.nfc.sendAPDU([keytype]+[loginblock]+[key]+[self.uid])
		if not ret:
			self.errorcode= self.ISO_SECURE
			return False
		self.errorcode= self.ISO_OK
		return True
	def libnfc_mifare_read_block(self, block):
		apdu= []
		apdu += '%02X' % pynfc.MC_READ # mifare read
		hexblock= '%02x' % block
		apdu.append(hexblock)
		ret, dat= self.nfc.sendAPDU(apdu)
		if not ret:
			self.errorcode= dat
			return False
		self.data= dat
		self.errorcode= self.ISO_OK
		return True
	# Global Platform specific commands
	def gp_external_authenticate(self,host_cryptogram,mac_key):
		"Global Platform external authenticate"
		cla=  '84'
		ins= 'EXTERNAL_AUTHENTICATE'
		p1= '00' # security level 0 - plaintext
		#p1= '01' # security level 1 - C-MAC
		p2= '00'
		data= self.ToHex(host_cryptogram)
		lc= '10' # needs to include MAC that will be added after mac generation
		mac= self.ToHex(self.DESMAC(self.ToBinary(cla+'82'+p1+p2+lc+data),mac_key,''))
		data += mac
		return self.send_apdu('','','','',cla,ins,p1,p2,lc,data,'')
	def gp_generate_session_key_01(self,hostchallenge,cardchallenge):
		"Global Platform generate session key from host and card challenges (SCP01)"
		derivation= cardchallenge[8:16]
		derivation += hostchallenge[0:8]
		derivation += cardchallenge[0:8]
		derivation += hostchallenge[8:16]
		return(derivation)
	def gp_get_data(self,object):
		"Global Platform get data"
		cla= self.CLA_GLOBAL_PLATFORM
		ins= 'GET_DATA'
		p1= object[0:2]
		p2= object[2:4]
		le= '00'
        	return self.send_apdu('','','','',cla,ins,p1,p2,'','',le)
	def gp_get_status(self,subset,control,aid):
		"Global Platform get status"
		cla= self.CLA_GLOBAL_PLATFORM
		ins= 'GET_STATUS'
		p1= subset
		p2= control
		data= '4F00' + aid
		lc= '%02x' % (len(data) / 2)
		le= '00'
		return self.send_apdu('','','','',cla,ins,p1,p2,lc,data,le)
	def gp_initialize_update(self,challenge):
		"Global Platform initialize update"
		cla= self.CLA_GLOBAL_PLATFORM
		ins= 'INITIALIZE_UPDATE'
		p1= '00'
		p2= '00'
		data= challenge
		lc= '%02x' % (len(data) / 2)
		le= '00'
		return self.send_apdu('','','','',cla,ins,p1,p2,lc,data,le)
	def gp_initialize_update_response_scp02(self,data):
		"return broken down Initialize Update response (SCP02) - Key Diversification (10), Key Info (2), Sequence Counter (2), Card Challenge (6), Card Cryptogram (8)"
		return data[0:20],data[20:24],data[24:28],data[28:40],data[40:56]
	# ISO 7816 commands
	def iso_7816_external_authenticate(self,response,key):
	        "7816 external authenticate"
        	ins= 'EXTERNAL_AUTHENTICATE'
        	lc= le= '%02x' % (len(response) / 2)
        	if self.send_apdu('','','','','',ins,'','',lc,response,le):
                	if self.MACVerify(self.data,key):
                        	return True
		return False
	def iso_7816_fail(self,code):
		"print 7816 failure code and exit"
		if code == self.ACG_FAIL:
			print "Application not implemented!"
			os._exit(True)
		print "Failed - reason code " + code + " (" + self.ISO7816ErrorCodes[code] + ")"
		print
		os._exit(True)
	def iso_7816_get_challenge(self,length):
        	"get random challenge - challenge will be in .data"
        	ins= 'GET_CHALLENGE'
        	le= '%02x' % length
        	if self.DEBUG:
                	print "DEBUG: requesting %d byte challenge" % length
        	return self.send_apdu('','','','','',ins,'','','','',le)
	def iso_7816_read_binary(self,bytes,offset):
		"7816 read binary - data read will be in .data"
	        ins= 'READ_BINARY'
        	hexoffset= '%04x' % offset
        	p1= hexoffset[0:2]
        	p2= hexoffset[2:4]
        	le= '%02x' % bytes
        	return self.send_apdu('','','','','',ins,p1,p2,'','',le)
	def iso_7816_select_file(self,file,control,options):
        	"7816 select file"
        	ins= 'SELECT_FILE'
        	lc= '%02x' % (len(file) / 2)
		p1= control
		p2= options
		data= file
        	return self.send_apdu('','','','','',ins,p1,p2,lc,data,'')
	def pcsc_send_apdu(self,apdu):
		# build and transmit PCSC apdu (list as appropriate, e.g. [cla,ins,p1,p2,lc,data,le...])
		apdustring= ''
		if self.readersubtype == self.READER_ACS:
			return self.acs_send_apdu(apdu)
			
		if self.readertype == self.READER_ANDROID:
			result = self.android.sendAPDU(apdu)
			self.data = result[0:-4]
			self.errorcode = result[len(result)-4:len(result)]
			if self.errorcode == self.ISO_OK:
				return True
			return False
		# apdu is a list which may contain long fields such as 'data', so first concatonate into
		# one long string, then break up into 2 char hex fields
		for d in apdu:
			apdustring += d
		apduout= self.HexToList(apdustring)
		result, sw1, sw2= self.pcsc_connection.transmit(apduout,protocol= self.pcsc_protocol)
		self.errorcode= '%02X%02X' % (sw1,sw2)
		self.data= self.ListToHex(result)
		# SCM readers need a little time to get over the excertion
#		if self.readersubtype == self.READER_SCM:
#			time.sleep(.1)
		if self.errorcode == self.ISO_OK:
			return True
		return False
	def send_apdu(self,option,pcb,cid,nad,cla,ins,p1,p2,lc,data,le):
		"send iso-7816-4 apdu"
		if not option:
			option= '1f'
			#option= '00'
		if not pcb:
			pcb= '02'
		if not cla:
			cla= '00'
		if not p1:
			p1= '00'
		if not p2:
			p2= '00'
		try:
			ins= self.ISOAPDU[ins]
		except:
			pass
		if self.readertype == self.READER_PCSC:
			return self.pcsc_send_apdu(cla+ins+p1+p2+lc+data+le)
		if self.readertype == self.READER_LIBNFC:
			if self.DEBUG:
				print 'In send_apdu - for libnfc:', cla+ins+p1+p2+lc+data+le
			ret, result = self.nfc.sendAPDU(cla+ins+p1+p2+lc+data+le)
			self.data = result[0:-4]
			self.errorcode = result[len(result)-4:len(result)]
			if not ret or self.errorcode != self.ISO_OK:
				return False
			return True
		if self.readertype == self.READER_ANDROID:
			result = self.android.sendAPDU(cla+ins+p1+p2+lc+data+le)
			self.data = result[0:-4]
			self.errorcode = result[len(result)-4:len(result)]
			if self.errorcode == self.ISO_OK:
				return True
			return False
			dlength= 5
		command= pcb+cla+ins+p1+p2+lc+data+le
		dlength += len(data) / 2
		dlength += len(lc) / 2
		dlength += len(le) / 2
		if self.DEBUG:
			print 'sending: ' + 't' + '%02x' % dlength + option + command
		self.ser.write('t' + '%02x' % dlength + option + command)
		# need check for 'le' length as well
		ret= self.ser.readline()[:-2] 
		if self.DEBUG:
			print 'received:',ret
		self.errorcode= ret[len(ret) - 4:len(ret)]
		# copy data if more than just an error code (JCOP sometimes returns an error with data)
		if len(ret) > 8:
			self.data= ret[4:len(ret) - 4]
		else:
			self.data= ''
		if self.errorcode == self.ISO_OK:
			return True
		return False	
#		return ret[4:len(ret) - 4]
#		if not len(ret) / 2 == int(ret[0:2],16) + 1:
#			return False
#		return ret[4:int(le,16) * 2 + 4]
	def login_iclass(self,page,keynum):
		"login to an iclass page with a key stored on the reader"
		if not self.readersubtype == self.READER_OMNIKEY:
			self.errorcode= 'ABCD'
			return False
		ins= 'EXTERNAL_AUTHENTICATE'
		p1= '00'
		p2= '%02x' % keynum
		lc= '08'
		data= '0000000000000000'
		if not self.send_apdu('','','','','80',ins,p1,p2,lc,data,''):
			return False
		return True			
	def login(self,sector,keytype,key):
		"login to specified sector - returns True if successful, False if failed. If failure is due to an error, 'errorcode' will be set." 
		keytype= string.upper(keytype)
		if keytype == 'A':
			keytype= 'AA'
		if keytype == 'B':
			keytype= 'BB'
		# use transport key if none specified
		if not key:
			key= self.MIFARE_TK[keytype]
		if self.readertype == self.READER_ACG:
			if keytype == 'FF':
				keytype= 'AA'
			if not sector == '':
				if self.DEBUG:
					print 'sending:', 'l' + ('%02x' % sector) + keytype + key
				self.ser.write('l' + ('%02x' % sector) + keytype + key)
			else:
				if self.DEBUG:
					print 'sending:','l' + keytype + key
				self.ser.write('l' + keytype + key)
			if key == '':
				self.ser.write('\r')
			self.errorcode= self.ser.readline()[0]
			if self.DEBUG:
				print 'received:', self.errorcode
			if self.errorcode == 'L':
				self.errorcode= ''
				return True
			return False
		if self.readertype == self.READER_FROSCH:
			return self.frosch(self.FR_HTS_TagAuthent,'')
		if self.readertype == self.READER_LIBNFC:
			return self.libnfc_mifare_login(sector,key,keytype)
		if self.readertype == self.READER_PCSC:
			if self.readersubtype == self.READER_ACS:
				return self.acs_mifare_login(sector,key,keytype)
			# PCSC requires key to be loaded to reader, then login with key
			if not self.PCSC_Keys.has_key(key):
				# send key to reader and store in global PCSC_KEYS if not already sent
				apdu= []
				apdu += self.PCSC_APDU['LOAD_KEY']
				if self.readersubtype == self.READER_OMNIKEY:	
					keynum= len(self.PCSC_Keys)
					apdu += self.PCSC_NON_VOLATILE # load key to non-volatile reader memory
				else:
					apdu += self.PCSC_VOLATILE # load key to volatile reader memory
					keynum= len(self.PCSC_Keys) + 96 # SCM Mifare keys live at hex 60+
				if keytype == 'BB':
					keynumoffset= 1
				else:
					keynumoffset= 0
				apdu.append('%02x' % (keynum + keynumoffset)) # p2 - key number
				apdu.append('%02x' % (len(key) / 2)) # lc
				apdu.append(key) # data
				if not self.pcsc_send_apdu(apdu):
					return False
				if self.readersubtype == self.READER_OMNIKEY:
					# readers with non-volatile memory only need the key once
					self.PCSC_Keys[key]= keynum
			else:
				#use stored key if already sent	
				keynum= self.PCSC_Keys[key]
			# now try to authenticate
			return self.authenticate(sector,keytype, keynum)
	def authenticate(self,sector,keytype, keynum):
			keytype= string.upper(keytype)
			apdu= []
			apdu += self.PCSC_APDU['AUTHENTICATE']
			block= '%04x' % sector
			apdu.append(block[0:2]) # p1 sector msb
			apdu.append(block[2:4]) # p1 sector lsb
			if keytype == 'AA' or keytype == 'FF':
				apdu.append('60') # keytype
			elif keytype == 'BB':
				apdu.append('61') # keytype
			else:
				apdu.append(keytype)
			apdu.append('%02x' % keynum) # key number
			ret= self.pcsc_send_apdu(apdu)
			if ret == False:
				# let PCSC get over it!
				time.sleep(0.5)
			return ret
	def verify(self,keytype,key):
		keytype= string.upper(keytype)
		apdu= []
		apdu += self.PCSC_APDU['VERIFY']
		if keytype == 'AA' or keytype == 'FF':
			apdu.append('60') # keytype
		elif keytype == 'BB':
			apdu.append('61') # keytype
		apdu.append('00')
		apdu.append('%02x' % (len(key) / 2))
		apdu.append(key)
		ret= self.pcsc_send_apdu(apdu)
		if ret == False:
			# let PCSC get over it!
			time.sleep(0.5)
		return ret
	def readblock(self,block):
		if self.readertype == self.READER_FROSCH:
			if self.tagtype == self.HITAG1:
				return(self.frosch(self.FR_HT1_Read_Page,self.FR_PLAIN + chr(block))) 	
			if self.tagtype == self.HITAG2:
				return(self.frosch(self.FR_HT2_Read_Page,chr(block))) 	
		if self.readertype == self.READER_ACG:
			self.ser.write('r%02x' % block)
			self.data= self.ser.readline()[:-2]
			self.binary= ''
			if len(self.data) == 1:
				self.errorcode= self.data
				self.data= ''
				return False
			count= 0
			while count * 2 < len(self.data):
				self.binary += chr(int(self.data[count * 2:(count * 2) + 2],16))
				count += 1
			return True	
		if self.readertype == self.READER_LIBNFC:
			print "not implemented!"
			return False
			apdu += self.PCSC_APDU['READ_BLOCK']
			apdu= []
			apdu += '%02X' % pynfc.MC_READ # mifare read
			hexblock= '%04x' % block
			apdu.append(hexblock)
			ret, self.errorcode= self.nfc.sendAPDU(apdu)
			if not ret:
				return False
			self.errorcode= self.ISO_OK
			return True
		if self.readertype == self.READER_PCSC:
			if self.readersubtype == self.READER_ACS:
				return self.acs_read_block(block)
			apdu= []
			apdu += self.PCSC_APDU['READ_BLOCK']
			hexblock= '%04x' % block
			apdu.append(hexblock[0:2]) # p1
			apdu.append(hexblock[2:4]) # p2
			# try reading with block length of 1 to provoke size error
			apdu.append('01') # le
			ret= self.pcsc_send_apdu(apdu)
			# if failure is due to wrong block size, use block size returned by card instead
			if self.errorcode.upper()[0:2] == '6C':
				apdu[-1]= self.errorcode[2:4]
				return self.pcsc_send_apdu(apdu)
			else:
				return ret
	def readMIFAREblock(self,block):
		if self.readertype == self.READER_LIBNFC:
			if self.libnfc_mifare_read_block(block):
				self.MIFAREdata= self.data
			else:
				return False
		elif self.readblock(block):
			self.MIFAREdata= self.data
		else:
			return False
		count= 0
		while count * 2 < len(self.MIFAREdata):
			self.MIFAREbinary += chr(int(self.MIFAREdata[count * 2:(count * 2) + 2],16))
			count += 1
		return True
	def readvalueblock(self,block):
		self.ser.write('rv%02x' % block)
		self.MIFAREdata= self.ser.readline()[:-2]
		if len(self.MIFAREdata) != self.MIFAREVALUELEN:
			self.errorcode= self.MIFAREdata
			self.MIFAREdata= ''
			return False
		count= 0
		while count * 2 < len(self.MIFAREdata):
			self.MIFAREbinary += chr(int(self.MIFAREdata[count * 2:(count * 2) + 2],16))
			count += 1
		return True
	def writeblock(self,block,data):
		if self.readertype == self.READER_FROSCH:
			#if self.tagtype == self.HITAG1:
			#	return(self.frosch(self.FR_HT1_Read_Page,self.FR_PLAIN + chr(block))) 	
			if self.tagtype == self.HITAG2:
				return(self.frosch(self.FR_HT2_Write_Page,chr(block) + self.ToBinary(data))) 	
		if self.readertype == self.READER_ACG:
			self.ser.write('w%02x%s' % (block,data))
			x= self.ser.readline()[:-2]
			if x == string.upper(data):
				self.errorcode= ''
				return True
			self.errorcode= x
			return False
		if self.readertype == self.READER_PCSC:
			apdu= []
			apdu += self.PCSC_APDU['UPDATE_BLOCK']
			hexblock= '%04x' % block
			apdu.append(hexblock[0:2]) # p1
			apdu.append(hexblock[2:4]) # p2
			apdu.append('%02x' % (len(data) / 2)) # le
			apdu.append(data)
			return self.pcsc_send_apdu(apdu)
	def writevalueblock(self,block,data):
		self.ser.write('wv%02x%s' % (block,data))
                x= self.ser.readline()[:-2]
                if x == string.upper(data):
                        self.errorcode= ''
                        return True
                self.errorcode= x
                return False
	def frosch(self,command,data):
		"send frosch commands with check digit"
		command += data
		commandlen= len(command)
		bcc= self.frosch_bcc_out(command,commandlen + 1)
		# send length + command + checkdigit
		if self.DEBUG:
			print 'Sending: ', 
			self.HexPrint(chr(commandlen + 1) + command + chr(bcc))
		self.ser.write(chr(commandlen + 1) + command + chr(bcc))
		ret= ''
		# perform a blocking read - returned byte is number of chars still to read
		ret += self.ser.read(1)
		# if read times out, reset may be required for normal read mode
		if len(ret) == 0:
			if command == self.FR_HT2_Read_PublicB or command == self.FR_HT2_Read_Miro:
				self.frosch(self.FR_RWD_Stop_Cmd,'')
			self.errorcode= self.FR_TIMEOUT
			return False
		# now read the rest
		ret += self.ser.read(ord(ret[0]))
		if self.DEBUG:
			print 'ret: %d ' % len(ret),
			self.HexPrint(ret)
		# check integrity of return
		bcc= self.frosch_bcc_in(ret,0)
		if not bcc == ord(ret[len(ret) - 1]):
			# may be reporting an error with wrong BCC set
			if ret[0] == chr(0x02) and not ret[1] == chr(0x00):
				self.data= ''
				self.errorcode= self.ToHex(ret[1])
				return False
			print 'Frosch error! Checksum error:',
			self.HexPrint(ret)
			print 'Expected BCC: %02x' % bcc
			os._exit(True)
		status= ret[1]
		if status == self.FR_NO_ERROR:
			self.errorcode= ''
			# for consistency with ACG, data is converted to printable hex before return
			self.data= self.ToHex(ret[2:len(ret) - 1])
			return True
		else :
			self.errorcode= self.ToHex(status)
			self.data= ''
			if self.DEBUG:
				print "Frosch error:", int(self.errorcode,16) - 256
			# reader may need resetting to normal read mode
			if command == self.FR_HT2_Read_PublicB or command == self.FR_HT2_Read_Miro:
				self.frosch(self.FR_RWD_Stop_Cmd,'')
			return False
	def frosch_bcc(self,data,seed):
		bcc= seed
		if self.FR_BCC_Mode == self.FR_COMMAND_MODE:
			for x in range(len(data)):
				bcc= xor(bcc,ord(data[x]))
		else:
			for x in range(len(data)):
				bcc += ord(data[x])
			bcc= int(bcc & 0xff)
		return bcc	
	def frosch_bcc_in(self,data,seed):
		return self.frosch_bcc(data[:len(data) - 1],seed)
	def frosch_bcc_out(self,data,seed):
		return self.frosch_bcc(data,seed)
	def frosch_key_init_mode(self,passwd):
		"enter key init mode"
		status= self.frosch(self.FR_RWD_Key_Init_Mode,self.ToBinary(passwd))
		# frosch BCC calculation mode changes once we enter key init mode
		if status:
			self.FR_BCC_Mode= self.FR_KEY_INIT_MODE
		return status
	def frosch_read_ee_data(self,item):
		"read RWD EEPROM"
		# item defines which personalization data is to be read
		# 0x00 ... Password
		# 0x01 ... Key A
		# 0x02 ... Key B
		# 0x03 ... Logdata 0A
		# 0x04 ... Logdata 0B
		# 0x05 ... Logdata 1A
		# 0x06 ... Logdata 1B
		return self.frosch(self.FR_RWD_KI_Read_EE_Data,self.ToBinary(item))
	def demotag(self,command,data):
		"send DemoTag commands"
		if self.ser.write(command + data):
                	x= self.ser.readline()[:-2]
			if x == self.DT_ERROR:
				self.errorcode= x
				return False
			self.data= x
			return True
		return False
	#
	# data manipulation
	#
	def GetRandom(self,size):
        	data= ''
        	for x in range(size):
                	data += '%02x' % int(random.uniform(0,0xff))
        	return data
	def Parity(self,data,parity):
		# return parity bit to make odd or even as required
		myparity= 0
		for x in range(len(data)):
			myparity += int(data[x],2)
		myparity %= 2
		return xor(myparity,parity)
	def Unique64Bit(self,data):
		"convert binary ID to Unique formatted 64 bit data block"
		# standard header == 9 bits of '1'
		out= '111111111'
		# break output into 4 bit chunks and add parity
		colparity= [0,0,0,0]
		for x in range(0,len(data),4):
			parity= 0
			chunk= data[x:x+4]
			for y in range(4):
				parity += int(chunk[y],2)
				colparity[y] += int(chunk[y],2)
			out += chunk + '%s' % (int(parity) % 2)
		# add column parity
		for x in range(4):
			out += '%s' % (int(colparity[x]) % 2)
		# add stop bit
		out += '0'
		return out
	def UniqueToEM(self,data):
		"convert Unique ID to raw EM4x02 ID"
		# swap words
		tmp= ''
		for x in range(5):
			tmp += data[x * 2 + 1] + data[x * 2]
		# reverse bits
		return self.ToBinaryString(self.ToBinary(tmp))[::-1]
	def EMToUnique(self,data):
		"convert raw EM4x02 ID to Unique"
		return self.ToHex(self.BitReverse(self.ToBinary(data)))
	def HexToQ5(self,data):
		"conver human readable HEX to Q5 ID"
		return self.ToBinaryString(self.ToBinary(data))
	def crcccitt(self,data):
		crcvalue= 0x0000
		for x in range(len(data)):
			crcvalue= self.crc(crcvalue,data[x],MASK_CCITT)
		return crcvalue
	def crc(self, crc, data, mask=MASK_CRC16):
		for char in data:
			c = ord(char)
			c = c << 8
		for j in xrange(8):
			if (crc ^ c) & 0x8000:
				crc = (crc << 1) ^ mask
			else:
				crc = crc << 1
			c = c << 1
		return crc & 0xffff
	def crc16(self,data):
		crcValue=0x0000
		crc16tab = (0x0000, 0xC0C1, 0xC181, 0x0140, 0xC301, 0x03C0, 0x0280,
		0xC241, 0xC601, 0x06C0, 0x0780, 0xC741, 0x0500, 0xC5C1, 0xC481,
		0x0440, 0xCC01, 0x0CC0, 0x0D80, 0xCD41, 0x0F00, 0xCFC1, 0xCE81,
		0x0E40, 0x0A00, 0xCAC1, 0xCB81, 0x0B40, 0xC901, 0x09C0, 0x0880,
		0xC841, 0xD801, 0x18C0, 0x1980, 0xD941, 0x1B00, 0xDBC1, 0xDA81,
		0x1A40, 0x1E00, 0xDEC1, 0xDF81, 0x1F40, 0xDD01, 0x1DC0, 0x1C80,
		0xDC41, 0x1400, 0xD4C1, 0xD581, 0x1540, 0xD701, 0x17C0, 0x1680,
		0xD641, 0xD201, 0x12C0, 0x1380, 0xD341, 0x1100, 0xD1C1, 0xD081,
		0x1040, 0xF001, 0x30C0, 0x3180, 0xF141, 0x3300, 0xF3C1, 0xF281,
		0x3240, 0x3600, 0xF6C1, 0xF781, 0x3740, 0xF501, 0x35C0, 0x3480,
		0xF441, 0x3C00, 0xFCC1, 0xFD81, 0x3D40, 0xFF01, 0x3FC0, 0x3E80,
		0xFE41, 0xFA01, 0x3AC0, 0x3B80, 0xFB41, 0x3900, 0xF9C1, 0xF881,
		0x3840, 0x2800, 0xE8C1, 0xE981, 0x2940, 0xEB01, 0x2BC0, 0x2A80,
		0xEA41, 0xEE01, 0x2EC0, 0x2F80, 0xEF41, 0x2D00, 0xEDC1, 0xEC81,
		0x2C40, 0xE401, 0x24C0, 0x2580, 0xE541, 0x2700, 0xE7C1, 0xE681,
		0x2640, 0x2200, 0xE2C1, 0xE381, 0x2340, 0xE101, 0x21C0, 0x2080,
		0xE041, 0xA001, 0x60C0, 0x6180, 0xA141, 0x6300, 0xA3C1, 0xA281,
		0x6240, 0x6600, 0xA6C1, 0xA781, 0x6740, 0xA501, 0x65C0, 0x6480,
		0xA441, 0x6C00, 0xACC1, 0xAD81, 0x6D40, 0xAF01, 0x6FC0, 0x6E80,
		0xAE41, 0xAA01, 0x6AC0, 0x6B80, 0xAB41, 0x6900, 0xA9C1, 0xA881,
		0x6840, 0x7800, 0xB8C1, 0xB981, 0x7940, 0xBB01, 0x7BC0, 0x7A80,
		0xBA41, 0xBE01, 0x7EC0, 0x7F80, 0xBF41, 0x7D00, 0xBDC1, 0xBC81,
		0x7C40, 0xB401, 0x74C0, 0x7580, 0xB541, 0x7700, 0xB7C1, 0xB681,
		0x7640, 0x7200, 0xB2C1, 0xB381, 0x7340, 0xB101, 0x71C0, 0x7080,
		0xB041, 0x5000, 0x90C1, 0x9181, 0x5140, 0x9301, 0x53C0, 0x5280,
		0x9241, 0x9601, 0x56C0, 0x5780, 0x9741, 0x5500, 0x95C1, 0x9481,
		0x5440, 0x9C01, 0x5CC0, 0x5D80, 0x9D41, 0x5F00, 0x9FC1, 0x9E81,
		0x5E40, 0x5A00, 0x9AC1, 0x9B81, 0x5B40, 0x9901, 0x59C0, 0x5880,
		0x9841, 0x8801, 0x48C0, 0x4980, 0x8941, 0x4B00, 0x8BC1, 0x8A81,
		0x4A40, 0x4E00, 0x8EC1, 0x8F81, 0x4F40, 0x8D01, 0x4DC0, 0x4C80,
		0x8C41, 0x4400, 0x84C1, 0x8581, 0x4540, 0x8701, 0x47C0, 0x4680,
		0x8641, 0x8201, 0x42C0, 0x4380, 0x8341, 0x4100, 0x81C1, 0x8081,
		0x4040)
		for ch in data:
			tmp=crcValue^(ord(ch))
			crcValue=(crcValue>> 8)^crc16tab[(tmp & 0xff)]
		return crcValue
	def MIFAREmfb(self,data):
		"Set variables from standard MIFARE manufacturer block (block 0 sector 0)"
		self.MIFAREserialnumber= data[0:8]
		self.MIFAREcheckbyte= data[8:10]
		self.MIFAREmanufacturerdata= data[10:32]
	def MIFAREkb(self,data):
		"Set variables from standard MIFARE key block (trailing sector)"
		self.MIFAREkeyA= data[0:12]
		self.MIFAREaccessconditions= data[12:18]
		self.MIFAREaccessconditionsuserbyte= data[18:20]
		self.MIFAREC1= int(data[14:16],16) >> 4
		self.MIFAREC2= int(data[16:18],16) & 0x0f
		self.MIFAREC3= (int(data[16:18],16) & 0xf0) >> 4
		self.MIFAREblock0AC= str(self.MIFAREC1 & 0x01) + str(self.MIFAREC2 & 0x01) + str(self.MIFAREC3 & 0x01)
		self.MIFAREblock1AC= str((self.MIFAREC1 & 0x02) >> 1) + str((self.MIFAREC2 & 0x02) >> 1) + str((self.MIFAREC3 & 0x02) >> 1)
		self.MIFAREblock2AC= str((self.MIFAREC1 & 0x04) >> 2) + str((self.MIFAREC2 & 0x04) >> 2) + str((self.MIFAREC3 & 0x04) >> 2)
		self.MIFAREblock3AC= str((self.MIFAREC1 & 0x08) >> 3) + str((self.MIFAREC2 & 0x08) >> 3) + str((self.MIFAREC3 & 0x08) >> 3)
		self.MIFAREkeyB= data[20:32]
	def MIFAREvb(self,data):
		"Set variables from standard MIFARE value block"
		self.MIFAREvalue= data[0:4]
		self.MIFAREvalueinv= data[4:8]
		self.MIFAREvalue2= data[8:12]
		self.MIFAREaddr= data[12]
		self.MIFAREaddrinv= data[13]
		self.MIFAREaddr2= data[14]
		self.MIFAREaddrinv2= data[15]
	def MRPmrzl(self,data):
		"Set variables from Machine Readable Zone (Lower)"
		self.MRPnumber= data[0:9]
		self.MRPnumbercd= data[9]
		self.MRPnationality= data[10:13]
		self.MRPdob= data[13:19]
		self.MRPdobcd= data[19]
		self.MRPsex= data[20]
		self.MRPexpiry= data[21:27]
		self.MRPexpirycd= data[27]
		self.MRPoptional= data[28:42]
		self.MRPoptionalcd= data[42]
		self.MRPcompsoitecd= data[43]
	def BitReverse(self,data):
		"Reverse bits - MSB to LSB"
		output= ''
		for y in range(len(data)):
			outchr= ''
			for x in range(8):
				outchr += str(ord(data[y]) >> x & 1)
			output += str(chr(int(outchr,2)))
		return output
	def HexReverse(self,data):
		"Reverse HEX characters"
		output= ''
		for y in reversed(range(len(data))):
			output += data[y]
		return output
	def HexBitReverse(self,data):
		"Convert HEX to Binary then bit reverse and convert back"
		return self.ToHex(self.BitReverse(self.ToBinary(data)))
	def HexByteReverse(self,data):
		"Reverse order of Hex pairs"
		output= ''
		y= len(data) - 2
		while y >= 0:
			output += data[y:y+2]
			y -= 2
		return output
	def NibbleReverse(self,data):
		"Reverse Nibbles"
		output= ''
		for y in range(len(data)):
			leftnibble= ''
			rightnibble= ''
			for x in range(4):
				leftnibble += str(ord(data[y]) >> x & 1)
			for x in range(4,8):
				rightnibble += str(ord(data[y]) >> x & 1)
			output += str(chr(int(rightnibble + leftnibble,2)))
		return output
	def HexNibbleReverse(self,data):
		"Convert HEX to Binary then reverse nibbles and convert back"
		return self.ToHex(self.NibbleReverse(self.ToBinary(data)))
	def ToHex(self,data):
		"convert binary data to hex printable"
        	string= ''
        	for x in range(len(data)):
                	string += '%02x' % ord(data[x])
		return string
	def HexPrint(self,data):
        	print self.ToHex(data)
	def ReadablePrint(self,data):
		out= ''
		for x in range(len(data)):
			if data[x] >= ' ' and data[x] <= '~':
				out += data[x]
			else:
				out += '.'
		return out
	def ListToHex(self,data):
		string= ''
		for d in data:
			string += '%02X' % d
		return string
	def HexArrayToString(self,array):
		# translate array of strings to single string
		out= ''
		for n in array:
			out += n
		return out
	def HexArraysToArray(self,array):
		# translate an array of strings to an array of 2 character strings
		temp= self.HexArrayToString(array)
		out= []
		n= 0
		while n < len(temp):
			out.append(temp[n:n+2])
			n += 2
		return out
	def HexArrayToList(self,array):
		# translate array of 2 char HEX to int list
		# first make sure we're dealing with a single array
		source= self.HexArraysToArray(array)
		out= []
		for n in source:
			out.append(int(n,16))
		return out
	def HexToList(self,string):
		# translate string of 2 char HEX to int list
		n= 0
		out= []
		while n < len(string):
			out.append(int(string[n:n+2],16))
			n += 2
		return out
	def ToBinary(self,string):
		"convert hex string to binary characters"
        	output= ''
        	x= 0
        	while x < len(string):
                	output += chr(int(string[x:x + 2],16))
                	x += 2
        	return output
	def BinaryPrint(self,data):
		"print binary representation"
		print self.ToBinaryString(data)
	def ToBinaryString(self,data):
		"convert binary data to printable binary ('01101011')"
		output= ''
		string= self.ToHex(data)
		for x in range(0,len(string),2):
			for y in range(7,-1,-1):
				output += '%s' % (int(string[x:x+2],16) >> y & 1)
		return output
	def BinaryToManchester(self,data):
		"convert binary string to manchester encoded string"
		output= ''
		for bit in data:
			if bit == '0':
				output += '01'
			else:
				output += '10'
		return output
	def DESParity(self,data):
        	adjusted= ''
        	for x in range(len(data)):
                	y= ord(data[x]) & 0xfe
                	parity= 0
                	for z in range(8):
                        	parity += y >>  z & 1
                	adjusted += chr(y + (not parity % 2))
        	return adjusted
	def DESKey(self,seed,type,length):
		d= seed + type	
		kencsha= SHA.new(d)
		k= kencsha.digest()
		kp= self.DESParity(k)
		return(kp[:length])
	def PADBlock(self,block):
		"add DES padding to data block"
		# call with null string to return an 8 byte padding block
		# call with an unknown sized block to return the block padded to a multiple of 8 bytes
        	for x in range(8 - (len(block) % 8)):
                	block += self.DES_PAD[x]
		return block
	def DES3MAC(self,message,key,ssc):
		"iso 9797-1 Algorithm 3 (Full DES3)"
		tdes= DES3.new(key,DES3.MODE_ECB,self.DES_IV)
		if(ssc):
			mac= tdes.encrypt(self.ToBinary(ssc))
		else:
			mac= self.DES_IV
		message += self.PADBlock('')
		for y in range(len(message) / 8):
			current= message[y * 8:(y * 8) + 8]
			left= ''
			right= ''
			for x in range(len(mac)):
				left += '%02x' % ord(mac[x])
				right += '%02x' % ord(current[x])
			machex= '%016x' % xor(int(left,16),int(right,16))
			mac= tdes.encrypt(self.ToBinary(machex))
		# iso 9797-1 says we should do the next two steps for "Output Transform 3"
		# but they're obviously redundant for DES3 with only one key, so I don't bother!
		#mac= tdes.decrypt(mac)
		#mac= tdes.encrypt(mac)
		return mac
	def DESMAC(self,message,key,ssc):
		"iso 9797-1 Algorithm 3 (Retail MAC)"
		# DES for all blocks
		# DES3 for last block
	        tdesa= DES.new(key[0:8],DES.MODE_ECB,self.DES_IV)
        	tdesb= DES.new(key[8:16],DES.MODE_ECB,self.DES_IV)
        	if(ssc):
                	mac= tdesa.encrypt(self.ToBinary(ssc))
        	else:
                	mac= self.DES_IV
		message += self.PADBlock('')
        	for y in range(len(message) / 8):
                	current= message[y * 8:(y * 8) + 8]
                	left= right= ''
                	for x in range(len(mac)):
                        	left += '%02x' % ord(mac[x])
                        	right += '%02x' % ord(current[x])
                	machex= '%016x' % xor(int(left,16),int(right,16))
                	mac= tdesa.encrypt(self.ToBinary(machex))
        	mac= tdesb.decrypt(mac)
        	return tdesa.encrypt(mac)
	def MACVerify(self,message,key):
		mess= self.ToBinary(message[:len(message)- 16])
		mac= self.DESMAC(mess,key,'')
		if not mac == self.ToBinary(message[len(message) -16:]):
			print 'MAC Error!'
			print 'Expected MAC: ', message[len(message) -16:]
			print 'Actual MAC:   ',
			self.HexPrint(mac)
			return(False)
		return(True)
	def SSCIncrement(self,ssc):
		out= int(self.ToHex(ssc),16) + 1
		return self.ToBinary("%016x" % out)
	def TRANSITIDEncode(self,data):
		"Encode TRANSIT ID"
		# start sentinel
		out= '0000000000000000'
		# UID
		out += self.ToBinaryString(self.ToBinary(data))
		# LRC
		lrc= self.TRANSITLRC(out[16:48])
		out += self.ToBinaryString(chr(lrc))
		# end sentinel
		out += self.ToBinaryString(chr(0xf2))
		return out
	def TRANSITID(self,data):
		"Decode TRANSIT ID"
		# check for start sentinel
		if(data[0:16] != '0000000000000000'):
			print 'Start sentinel not found! (0000000000000000)'
			return 0
		# check for end sentinel
		if(int(data[56:],2) != 0xf2):
			print 'End sentinel not found! (11110010)'
			return 0
		lrc= self.TRANSITLRC(data[16:48])
		if(lrc != int(data[48:56],2)):
			print 'LRC mismatch: %02X should be %02X!' % (int(data[48:56],2),lrc)
			return 0
		out= '%08X' % int(data[16:48],2)
		return out
	def TRANSITIDPrint(self,data):
		out= self.TRANSITID(data)
		if(out != 0):
			print 'UID:', out
		else:
			print 'Invalid ID!'
	def TRANSITLRC(self,data):
		"Calculate TRANSIT LRC"
		i= 0
		lrc= 0x00
		# rolling XOR
                while(i < 4):
                        lrc ^= (int(data[(i) * 8:(i+1) * 8],2)) & 0xff
                        i += 1
		# final byte XOR
                lrc ^= 0x5a & 0xff
		return lrc
	def FDXBID(self,data):
		"Decode FDX-B ID"
        	out= self.HexReverse(data)
        	hexout= self.ToHex(self.NibbleReverse(self.ToBinary(out)))
		# Application ID
        	self.FDXBAPP= hexout[:4]
		# Country Code
        	ccode= hexout[4:7]
        	self.FDXBCCODE= int(ccode,16) >> 2
		# Human Readable CCODE
		if "%d" % self.FDXBCCODE in self.ISO3166CountryCodes:
			self.FDXBCCODEHR= self.ISO3166CountryCodes["%d" % self.FDXBCCODE]
		else:
			self.FDXBCCODEHR= 'Undefined - see http://www.icar.org/manufacturer_codes.htm'
		# National ID
        	natid= hexout[6:16]
        	self.FDXBNID= int(natid,16) &0x3fffffffff
	def FDXBIDEncode(self,appid,ccode,natid):
		"Encode FDX-B ID"
		hexccode= "%03x" % (int(ccode,10) << 2)
		glue = int(hexccode[-1:],16) & 0xc
		hexccode = hexccode[:-1]
		hexid= "%010x" % int(natid,10)
		glue = glue | (int(hexid[:1],16) & 0x3)
		hexglue = "%01x" % glue
		hexid = hexid[1:]
		rawid= appid + hexccode + hexglue + hexid
		nibbleid= self.NibbleReverse(self.ToBinary(rawid))
		hexout= self.HexReverse(self.ToHex(nibbleid))
		return hexout 
	def FDXBIDPrint(self,data):
		self.FDXBID(data)
        	print 'Application Identifier: ', self.FDXBAPP
        	print 'Country Code: ',
        	print self.FDXBCCODE,
        	print  "(" + self.FDXBCCODEHR + ")"
        	print 'National ID: ',
        	print self.FDXBNID
	def FDXBID128Bit(self,data):
		"generate raw 128 bit FDX-B data from FDX-B ID"
		idbin= self.ToBinaryString(self.ToBinary(data))
		# construct FDX-B encoded blocks
		out= ''
		# header is ten zeros and a '1'
		header= '00000000001'
		out += header
		# break id into 8 bit chunks with a trailing '1' on each
		for x in range(0,len(idbin),8):
			out += idbin[x:x+8] + '1'
		# add 16 CRC-CCITT error detection bits
		crc= '%04x' % self.crcccitt(self.ToBinary(data))
		crcbin= self.ToBinaryString(self.ToBinary(crc))
		# crc is transmitted LSB first with trailing '1's
		out += crcbin[0:8] + '1'
		out += crcbin[8:16] + '1'
		# add 3 sets of trailer bits (RFU)
		trailer= '000000001'
		for x in range(3):
			out += trailer
		return out
	def FDXBID128BitDecode(self,data):
		"convert raw 128 bit FDX-B data to FDX-B ID"
		#strip off header
		y= data[11:]
		#strip off trailing '1' from the first 8 9-bit groups
		out= ''
		for x in range(0,72,9):
			out += y[x:x+8]
		# ignore the rest - CRC etc.
		return '%016x' % int(out,2)	
	def PCSCGetTagType(self,atr):
		"get currently selected tag type from atr"
		if atr[8:12] == self.PCSC_CSC:
			ss= atr[24:26]
			return self.PCSC_SS[ss]
		else:
			return 'SMARTCARD'
	def PCSCPrintATR(self,data):
		"print breakdown of HEX ATR"
		print '    ATR:', data
		if data[0:2].upper() == '3B':
			print '         3B  Initial Header' 
		else:
			print 'ATR not recognised!'
			return False
		if data[2] == '8':
			print '           8  No TA1, TB1, TC1 only TD1 is following'
		histlen= int(data[3],16)
		print '            %s  %d bytes historical data follow' % (data[3] , histlen)
		if data[4] == '8':
			print '             8  No TA2, TB2, TC2 only TD2 is following'
		if data[5] == '0':
			print '              0  T = 0'
		if data[6] == '0':
			print '               0  No TA3, TB3, TC3, TD3 following'
		if data[7] == '1':
			print '                1  T = 1'
		if data[8:12] == self.PCSC_CSC:
			print '                 Detected STORAGECARD'
			print '     Historical:', data[8:-2]
			print '                 80  Status indicator may be present (COMPACT-TLV object)'
			print '                   4F  Application Identifier presence indicator'
			applen= int(data[12:14],16)
			print '                     %s  %d bytes follow' % (data[12:14] , applen) 
			print '                 RID:  %s ' % data[14:24],
			if data[14:24].upper() == self.PCSC_RID:
				print 'PC/SC Workgroup'
			else:
				print 'Unknown RID'
			pixlen= applen - 5
			print '                           PIX:  %s' % data[24:24 + pixlen * 2]
			ss= data[24:26]
			print '                            SS:  %s  %s' % (ss , self.PCSC_SS[ss]),
			# if card is ISO15693 print manufacturer name
			if 9 <= int(ss,16) <= 12:
				try:
					print '(%s)' % self.ISO7816Manufacturer[self.uid[2:4]]
				except:
					print '(Uknown Manufacturer)'
			else:
				print
			print '                            Name:  %s  %s' % (data[26:30] , self.PCSC_NAME[data[26:30]])
			print '                                 RFU:  %s' % data[30:-2]
			spaces= histlen * 2
		else:
			print '                 Detected SMARTCARD'
			print '            ATS:',self.pcsc_ats,'-',
			print self.ReadablePrint(self.ToBinary(self.pcsc_ats))
			# if ats starts with '00', '10' or '8X' it is an ISO-7816-4 card
			atsbyte= self.pcsc_ats[0:2]
			if atsbyte == '00' or atsbyte == '10' or self.pcsc_ats[0] == '8':
				print '       Category: %s  Format according to ISO/IEC 7816-4' % atsbyte
			else:
				print '       Category: %s  Proprietary format' % atsbyte
			spaces= len(self.pcsc_ats)
		space= ''
		for x in range(spaces):
			space += ' '
			
		print space + '   Checksum TCK: ' + data[-2:],
		# calculate checksum excluding Initial Header and TCK
		tck= 0
		x= 2
		while x < len(data) - 2:
			tck= xor(tck,int(data[x:x+2],16))
			x += 2
		if int(data[-2:],16) == tck:
			print '(OK)'
			return True
		else:
			print '(Checksum error: %02x)' % tck
			return False

	def shutdown(self):
		if self.readertype == self.READER_LIBNFC:
			self.nfc.powerOff()
			self.nfc.deconfigure()
		os._exit(False)

########NEW FILE########
__FILENAME__ = rfidiotglobals
Debug=False

########NEW FILE########
__FILENAME__ = rfidiot-cli
#!/usr/bin/python


#  rfidiot-cli.py - CLI for rfidiot
# 
#  Adam Laurie <adam@algroup.co.uk>
#  http://rfidiot.org/
# 
#  This code is copyright (c) Adam Laurie, 2012, All rights reserved.
#  For non-commercial use only, the following terms apply - for all other
#  uses, please contact the author:
#
#    This code is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#


#
# This program is intended to illustrate RFIDIOt's capabilities. It is deliberately
# written in a style that is easy to understand rather then one that is elegant
# or efficient. Everything is done in longhand so that individual functions can 
# be easily understood and extracted.
#
# On the other hand, due to it's completely open structure, it can be a powerful 
# tool when commands are combined, and it's easy to create shell scripts that 
# perform one-off tasks that are not worth writing an entire program for.


import rfidiot
import sys
import time

args= rfidiot.args
help= rfidiot.help

if help or len(sys.argv) == 1:
	print
	print 'Usage: %s [OPTIONS] <COMMAND> [ARG(s)] ... [<COMMAND> [ARG(s)] ... ]' % sys.argv[0]
	print
	print '  Commands:'
	print
	print '     AID <AID|"ALL"|"ANY">                            Select ISO 7816 AID'
	print '     AIDS                                             List well known AIDs'
	print '     APDU <CLA> <INS> <P1> <P2> <LC> <DATA> <LE>      Send raw ISO 7816 APDU (use "" for empty elements)'
	print '     CHANGE <MESSAGE>                                 Print message and wait for TAG to change'
	print '     FILE <"A|H"> <ASCII|HEX>                         Select ISO 7816 FILE'
	print '     HSS <SPEED>                                      High Speed Select TAG. SPEED values are:'
	print '                                                        1 == 106 kBaud'
	print '                                                        2 == 212 kBaud'
	print '                                                        4 == 424 kBaud'
	print '                                                        8 == 848 kBaud'
	print '     IDENTIFY                                         Show TAG type'
	print '     MF <COMMAND> [<ARGS> ... ]                       Mifare commands:'
	print '        AUTH <"A|B"> <BLOCK>                            Authenticate with KEY A or B (future authentications'
	print '                                                        are automated)'
	print '        CLONE <HEX KEY>                                 Duplicate a Mifare TAG (KEY is KEY A of BLANK)'
	print '        DUMP <START> <END>                              Show data blocks'
	print '        KEY <"A|B"> <HEX KEY>                           Set Mifare KEY A or B'
	print '        READ <START> <END> <FILE>                       Read data blocks and save as FILE'
	print '        WIPE                                            Set Mifare TAG to all 00'
	print '        WRITE <START> <FILE>                            Write data blocks from FILE (note that KEY A will'
	print '                                                        be inserted from previously set value and KEY B'
	print '                                                        will also be inserted if set, overriding FILE value)'
	print '     PROMPT <MESSAGE>                                 Print message and wait for Y/N answer (exit if N)'
	print '     SCRIPT <FILE>                                    Read commands from FILE (see script.txt for example)'   
	print '     SELECT                                           Select TAG'
	print '     WAIT <MESSAGE>                                   Print message and wait for TAG'
	print
	print '  Commands will be executed sequentially and must be combined as appropriate.'
	print '  Block numbers must be specified in HEX.'
	print
	print '  Examples:'
	print
	print '     Select TAG, set Mifare KEY A to "FFFFFFFFFFFF" and authenticate against sector 0:'
	print
	print '       rfidiot-cli.py select mf key a FFFFFFFFFFFF mf auth a 0'
	print
	print '     Write Mifare data to new TAG, changing Key A to 112233445566 (writing block 0 is allowed to fail):'
	print
	print '       rfidiot-cli.py select mf key a FFFFFFFFFFFF mf auth a 0 mf key a 112233445566 mf write 0 mifare.dat'
	print
	print '     Clone a Mifare TAG to a new blank:'
	print
	print '       rfidiot-cli.py select mf key a 112233445566 mf auth a 0 mf clone FFFFFFFFFFFF'
	exit(True)

try:
        card= rfidiot.card
except:
	print "Couldn't open reader!"
        exit(True)

print
card.info('rfidiot-cli v0.1')

# globals
Mifare_Key= None
Mifare_KeyType= None
Mifare_KeyA= None
Mifare_KeyB= None

# main loop
args.reverse()
while args:
	command= args.pop().upper()
	if command == 'AID':
		arg= args.pop().upper()
		if arg == 'ANY' or arg == 'ALL':
			aids= card.AIDS.keys()
		else:
			aids= [arg]
		while aids:
			aid= aids.pop()
			print
			print '  Selecting AID: %s' % aid,
			try:
				print '(%s)' % card.AIDS[aid],
			except:
				pass
			print
			print
			if card.iso_7816_select_file(aid,card.ISO_7816_SELECT_BY_NAME,'0C'):
				print '    OK'
				if arg == 'ANY':
					break
			else:
				print '    Failed: '+card.ISO7816ErrorCodes[card.errorcode]
		continue
	if command == 'AIDS':
		print
		print '  AIDs:'
		print
		for aid in card.AIDS.iteritems():
			print '    % 24s: %s' % (aid[0], aid[1])
		print
		continue
	if command == 'APDU':
		cla= args.pop().upper()
		ins= args.pop().upper()
		p1= args.pop().upper()
		p2= args.pop().upper()
		lc= args.pop().upper()
		data= args.pop().upper()
		le= args.pop().upper()
		print
		print '  Sending APDU:', cla+ins+p1+p2+lc+data+le
		print
		if card.send_apdu('','','','',cla,ins,p1,p2,lc,data,le):
			print '    OK'
			print '    Data:', card.data
		else:
			print '    Failed: '+card.ISO7816ErrorCodes[card.errorcode]
		continue
	if command == 'CHANGE':
		message= args.pop()
		print
		current= card.uid
		card.waitfortag(message)
		while card.uid == current or card.uid == '':
			card.waitfortag('')
		print
		continue
	if command == 'FILE':
		mode= args.pop().upper()
		if mode == 'A':
			isofile= args.pop().encode('hex')
		elif mode == 'H':
			isofile= args.pop().upper()
		else:
			print 'Invalid FILE mode:', args.pop().upper()
			exit(True)
		print
		print '  Selecting ISO File:', isofile
		print
		if card.iso_7816_select_file(isofile,card.ISO_7816_SELECT_BY_NAME,'00'):
			print '    OK'
		else:
			print '    Failed: '+card.ISO7816ErrorCodes[card.errorcode]
		continue
	if command == 'HSS':
		speed= '%02X' % int(args.pop())
		print
		print '  High Speed Selecting (%s)' % card.ISO_SPEED[speed]
		print
		if card.hsselect(speed):
			print '    Tag ID: ' + card.uid
		else:
			if card.errorcode:
				print '    '+card.ISO7816ErrorCodes[card.errorcode]
			else:
				print '    No card present'
		continue
	if command == 'IDENTIFY':
		print
		print '  Identiying TAG'
		print
		if card.select():
			print '    Tag ID:', card.uid, '   Tag Type:',
			if (card.readertype == card.READER_ACG and card.readername.find('LFX') == 0):
				print card.LFXTags[card.tagtype]
			else:
				print card.tagtype
			if card.readertype == card.READER_PCSC:
				if card.tagtype.find('ISO 15693') >= 0:
					print
					print '         Manufacturer:',
					try:
						print card.ISO7816Manufacturer[card.uid[2:4]]
					except:
						print 'Unknown (%s)' % card.uid[2:4]
				if not card.readersubtype == card.READER_ACS:
					print
					card.PCSCPrintATR(card.pcsc_atr)
		else:
			print '    No card present',
		continue
	if command == 'MF':
		print
		mfcommand= args.pop().upper()
		if mfcommand == 'AUTH':
			keytype= args.pop().upper()
			sector= int(args.pop(),16)
			print '  Authenticating to sector %02X with Mifare Key' % sector,
			Mifare_KeyType= keytype
			if keytype == 'A':
				Mifare_Key= Mifare_KeyA
				print 'A (%s)' % Mifare_Key
			elif keytype == 'B':
				Mifare_Key= Mifare_KeyB
				print 'B (%s)' % Mifare_Key
			else:
				print 'failed! Invalid keytype:', keytype
				exit(True)
			print
			if card.login(sector, Mifare_KeyType, Mifare_Key):
				print '    OK'
			else:
				print '    Failed: '+card.ISO7816ErrorCodes[card.errorcode]
			continue
		if mfcommand == 'CLONE':
			print '  Cloning Mifare TAG',
			if not Mifare_KeyA:
				print 'failed! KEY A not set!'
				exit(True)
			if not Mifare_KeyType or not Mifare_Key:
				print 'failed! No authentication performed!'
				exit(True)
			print
			print
			print '    Key A will be set to:', Mifare_KeyA
			print
			blank_key= args.pop()
			start= 0
			end= 0x3F
			data= ''
			sector= start
			print '    Reading...'
			while sector <= end:
				if card.login(sector, Mifare_KeyType, Mifare_Key) and card.readMIFAREblock(sector):
					data += card.MIFAREdata.decode('hex')
				else:
					print '    Failed: '+card.ISO7816ErrorCodes[card.errorcode]
				sector += 1
			print
			print '      OK'
			print
			# wait for tag to change (same UID is OK)
			card.waitfortag('    Replace TAG with TARGET')
			while card.select():
				pass
			time.sleep(.5)
			while not card.select():
				pass
			time.sleep(.5)
			print
			print
			print '    Writing...'
			sector= start
			p= 0
			while sector <= end:
				block= data[p:p + 16].encode('hex')
				if not (sector + 1) % 4:
					# trailing block must contain keys, so reconstruct
					block= Mifare_KeyA + block[12:]
				if not (card.login(sector, 'A', blank_key) and card.writeblock(sector, block)):
					if sector == 0:
						print '      Sector 0 write failed'
						card.select()
					else:
						print '      Failed: '+card.ISO7816ErrorCodes[card.errorcode]
						exit(True)
				sector += 1
				p += 16
			print
			print '      OK'
			continue
		if mfcommand == 'DUMP':
			start= int(args.pop(),16)
			end= int(args.pop(),16)
			print '  Dumping data blocks %02X to %02X:' % (start, end),
			if not Mifare_KeyType or not Mifare_Key:
				print 'failed! No authentication performed!'
				exit(True)
			print
			print
			sector= start
			while sector <= end:
				if card.login(sector, Mifare_KeyType, Mifare_Key) and card.readMIFAREblock(sector):
					print '    %02X: %s %s' % (sector, card.MIFAREdata, card.ReadablePrint(card.MIFAREdata.decode('hex')))
				else:
					print '    Failed: '+card.ISO7816ErrorCodes[card.errorcode]
				sector += 1
			continue
		if mfcommand == 'KEY':
			print '  Setting Mifare Key',
			keytype= args.pop().upper()
			if keytype == 'A':
				Mifare_KeyA= args.pop().upper()
				print 'A:', Mifare_KeyA
			elif keytype == 'B':
				Mifare_KeyB= args.pop().upper()
				print 'B:', Mifare_KeyB
			else:
				print 'failed! Invalid keytype:', keytype
				exit(True)
			continue
		if mfcommand == 'READ':
			start= int(args.pop(),16)
			end= int(args.pop(),16)
			filename= args.pop()
			print '  Reading data blocks %02X to %02X and saving as %s:' % (start, end, filename),
			outfile= open(filename, "wb")
			if not outfile:
				print "failed! Couldn't open output file!"
				exit(True)
			if not Mifare_KeyType or not Mifare_Key:
				print 'failed! No authentication performed!'
				exit(True)
			print
			print
			sector= start
			while sector <= end:
				if card.login(sector, Mifare_KeyType, Mifare_Key) and card.readMIFAREblock(sector):
					outfile.write(card.MIFAREdata.decode('hex'))
				else:
					print '    Failed: '+card.ISO7816ErrorCodes[card.errorcode]
				sector += 1
			outfile.close()
			print '    OK'
			continue
		if mfcommand == 'WIPE':
			print '  Wiping Mifare TAG',
			if not Mifare_KeyA:
				print 'failed! KEY A not set!'
				exit(True)
			if not Mifare_KeyB:
				print 'failed! KEY B not set!'
				exit(True)
			if not Mifare_KeyType or not Mifare_Key:
				print 'failed! No authentication performed!'
				exit(True)
			print
			print
			print '    Key A will be set to:', Mifare_KeyA
			print '    Key B will be set to:', Mifare_KeyB
			print
			start= 1
			end= 0x3F
			sector= start
			perms= 'FF078069'
			while sector <= end:
				if not (sector + 1) % 4:
					# trailing block must contain keys, so reconstruct
					block= Mifare_KeyA + perms + Mifare_KeyB
				else:
					block= '00' * 16
				if not (card.login(sector, Mifare_KeyType, Mifare_Key) and card.writeblock(sector, block)):
					print '    Failed: '+card.ISO7816ErrorCodes[card.errorcode]
					exit(True)
				sector += 1
			print '    OK'
			continue
		if mfcommand == 'WRITE':
			start= int(args.pop(),16)
			filename= args.pop()
			infile= open(filename,"rb")
			data= infile.read()
			infile.close()
			print '  Writing data from file', filename,
			if len(data) % 16:
				print 'failed! File length is not divisible by Mifare block length (16)!'
				exit(True)
			if not Mifare_KeyA:
				print 'failed! KEY A not set!'
				exit(True)
			if not Mifare_KeyType or not Mifare_Key:
				print 'failed! No authentication performed!'
				exit(True)
			end= start + len(data) / 16 - 1
			print 'to blocks %02X to %02X' % (start, end)
			print
			print '    Key A will be set to:', Mifare_KeyA
			if Mifare_KeyB:
				print '    Key B will be set to:', Mifare_KeyB
			else:
				print '    Key B will be set as per file'
			print
			sector= start
			p= 0
			while sector <= end:
				block= data[p:p + 16].encode('hex')
				if not (sector + 1) % 4:
					# trailing block must contain keys, so reconstruct
					if Mifare_KeyB:
						block= Mifare_KeyA + block[12:20] + Mifare_KeyB
					else:
						block= Mifare_KeyA + block[12:]
				if not (card.login(sector, Mifare_KeyType, Mifare_Key) and card.writeblock(sector, block)):
					if sector == 0:
						print '    Sector 0 write failed'
						card.select()
					else:
						print '    Failed: '+card.ISO7816ErrorCodes[card.errorcode]
						exit(True)
				sector += 1
				p += 16
			print '    OK'
			continue
		print '  Invalid MF command:', mfcommand
		exit(True)
	if command == 'PROMPT':
		message= args.pop()
		print
		x= raw_input(message).upper()
		if x == 'N':
			exit(False)
		continue
	if command == 'SCRIPT':
		filename= args.pop()
		infile= open(filename,"rb")
		print
		print '  Reading commands from', filename
		if not infile:
			print "failed! Can't open file!"
			exit(True)
		script= []
		while 42:
			line= infile.readline()
			if line == '':
				break
			line= line.strip()
			if line == '':
				continue
			quoted= False
			for arg in line.split(' '):
				# skip comments
				if arg[0] == '#':
					break
				# quoted sections
				if arg[0] == '"' or arg[0] == "'":
					quoted= True
					quote= ''
					arg= arg[1:]
				if quoted:
					if arg[-1] == '"' or arg[-1] == "'":
						quote += ' ' + arg[:-1]
						quoted= False
						script.append(quote)
					else:
						quote += ' ' + arg
				else:
					script.append(arg)
		infile.close()
		script.reverse()
		args += script
		continue
	if command == 'SELECT':
		print
		print '  Selecting TAG'
		print
		if card.select():
			print '    Tag ID: ' + card.uid
			if card.readertype == card.READER_PCSC:
				print '    ATR: ' + card.pcsc_atr
		else:
			if card.errorcode:
				print '    Failed:  '+card.ISO7816ErrorCodes[card.errorcode]
			else:
				print '    No card present'
		continue
	if command == 'WAIT':
		message= args.pop()
		print
		current= card.uid
		card.waitfortag(message)
		print
		continue
	print
	print 'Unrecognised command:', command
	exit(True)
print
exit(False)

########NEW FILE########
__FILENAME__ = send_apdu
#!/usr/bin/python

#
# send_apdu.py - Python code for Sending raw APDU commands
# version 0.1
# Nick von Dadelszen (nick@lateralsecurity.com)
# Lateral Security (www.lateralsecurity.com)

#
# This code is copyright (c) Lateral Security, 2011, All rights reserved.
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
#   You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import rfidiot
import sys
import os

try:
        card= rfidiot.card
except:
	print "Couldn't open reader!"
        os._exit(True)

card.info('send_apdu v0.1a')
card.select()
print '\nID: ' + card.uid
print '  Data:'

cont = True
while cont:
	apdu = raw_input("enter the apdu to send now, send \'close\' to finish :")
	if apdu == 'close':
		cont = False
	else:
		r = card.pcsc_send_apdu(apdu)
		print card.data + card.errorcode
				
print 'Ending now ...'


########NEW FILE########
__FILENAME__ = sod
#!/usr/bin/python


#  sod.py - try to find X509 data in EF.SOD
# 
#  Adam Laurie <adam@algroup.co.uk>
#  http://rfidiot.org/
# 
#  This code is copyright (c) Adam Laurie, 2007, All rights reserved.
#  For non-commercial use only, the following terms apply - for all other
#  uses, please contact the author:
#
#    This code is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
import commands
import sys
import os

x= 0
if len(sys.argv) > 1:
	sod= open(sys.argv[1],"r")
else:
	sod= open("/tmp/EF_SOD.BIN","r")
data= sod.read()
while x < len(data):
	out= open("/tmp/SOD","w")
	out.write(data[x:])
	out.flush()
	out.close()
	(exitstatus, outtext) = commands.getstatusoutput("openssl pkcs7 -text -print_certs -in /tmp/SOD -inform DER")
	if not exitstatus and len(outtext) > 0:
		print 'PKCS7 certificate found at offset %d:' % x
		print
		print outtext
		os._exit(False)
	x += 1
os._exit(True)

########NEW FILE########
__FILENAME__ = transit
#!/usr/bin/python

#  transit.py - generate / decode FDI Matalec Transit 500 and Transit 999 UIDs
# 
#  Adam Laurie <adam@algroup.co.uk>
#  http://rfidiot.org/
# 
#  This code is copyright (c) Adam Laurie, 2009, All rights reserved.
#  For non-commercial use only, the following terms apply - for all other
#  uses, please contact the author:
#
#    This code is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#


import rfidiot
import sys
import os
import string

try:
	card= rfidiot.card
except:
	print "Couldn't open reader!"
	os._exit(True)

args= rfidiot.args
help= rfidiot.help

card.info('transit v0.1b')

precoded= False

if not help and len(args) > 0 and len(args[0]) == 64:
	print "\nDecode: ",
       	card.TRANSITIDPrint(args[0])
	if len(args) == 2:
		if args[1] == 'WRITE':
			precoded= True
		else:
			print 'Unrecognised option: ' + args[1]
			os._exit(True)
	else:
		print
		os._exit(False)

if not help and ((len(args) > 0 and len(args[0]) == 8) or precoded):
	if precoded:
		out= args[0]
	else:
		print "\nEncode: ",
		out= card.TRANSITIDEncode(args[0])
	print out
	if (len(args) == 2 and args[1] == 'WRITE') or precoded:
       		while True:
			# Q5 must be forced into Q5 mode to be sure of detection so try that first 
			if card.readertype == card.READER_ACG:
				card.settagtype(card.Q5)
			card.select()
			if card.readertype == card.READER_ACG:
				if not card.tagtype == card.Q5:
					card.settagtype(card.ALL)
               		card.waitfortag('Waiting for blank tag...')
               		print '  Tag ID: ' + card.data
			if card.tagtype == card.Q5:
               			x= string.upper(raw_input('  *** Warning! This will overwrite TAG! Proceed (y/n)? '))
               			if x == 'N':
                       			os._exit(False)
               			if x == 'Y':
                       			break
			else:
				x= raw_input('  Incompatible TAG! Hit <RETURN> to retry...')
		writetag= True
		print
	else:
		writetag= False
	# now turn it all back to 4 byte hex blocks for writing
	outbin= ''
	outhex= ['','','','','']
	# control block for Q5:
	# carrier 32 (2 * 15 + 2)
	# rf/? (don't care) - set to 00
	# data not inverted
	# manchester
	# maxblock 2
	print '  Q5 Control Block:  ',
	q5control= '6000F004'
	print q5control
	for x in range(0,len(out),8):
		outbin += chr(int(out[x:x + 8],2))
	for x in range(0,len(outbin),4):
		print '    Q5 Data Block %02d:' % (x / 4 + 1),
		outhex[x / 4 + 1]= card.ToHex(outbin[x:x+4])
		print outhex[x / 4 + 1]
	if writetag == True:
		print 
		outhex[0]= q5control
		for x in range(2,-1,-1):
			if(x != 0):
				print "    Writing block %02x:" % x,
        		if not card.writeblock(x,outhex[x]):
				# we expect a Q5 to fail after writing the control block as it re-reads
				# it before trying to verify the write and switches mode so is now no longer in Q5 mode
				if x == 0:
					print '             Control: ' + outhex[x]
					print
					print '  Done!'
				else:
                			print 'Write failed!'
                			os._exit(True)
			else:
				print outhex[x]
		if card.readertype == card.READER_ACG:	
               		card.settagtype(card.ALL)
	print
	os._exit(False)
print
print sys.argv[0] + ' - Q5 encode / decode TRANSIT compliant IDs'
print '\nUsage: ' + sys.argv[0] + ' [OPTIONS] <UID> [WRITE]'
print
print '\tIf a single 64 Bit BINARY UID is provided, it will be decoded according to the TRANSIT standard.'
print '\tAlternatively, specifying a 8 HEX digit UID will encode the 64 Bit BINARY with LRC and sentinels.'
print
print '\tIf the WRITE option is specified, a Q5 will be programmed to emulate a TRANSIT tag.'
print
os._exit(True)

########NEW FILE########
__FILENAME__ = unique
#!/usr/bin/python

#  unique.py -  generate EM4x02 and/or UNIQUE compliant IDs
#       these can then be written to a Q5 tag to emulate EM4x02
#       by transmitting data blocks 1 & 2 (MAXBLOCK == 2),
#       or Hitag2 in Public Mode A with data stored in blocks
#       4 and 5.
# 
#  Adam Laurie <adam@algroup.co.uk>
#  http://rfidiot.org/
# 
#  This code is copyright (c) Adam Laurie, 2006, All rights reserved.
#  For non-commercial use only, the following terms apply - for all other
#  uses, please contact the author:
#
#    This code is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#


import rfidiot
import sys
import os
import string
import time

try:
	card= rfidiot.card
except:
	print "Couldn't open reader!"
	os._exit(True)

args= rfidiot.args
help= rfidiot.help

card.info('unique v0.1l')

# Q5 config block
Q5CFB='e601f004'
# Hitag2 config block
H2CFB= card.HITAG2_PUBLIC_A + card.HITAG2_TRANSPORT_TAG

if len(args) < 1 or len(args) > 3 or help:
    print
    print sys.argv[0] + ' - generate EM4x02 and/or UNIQUE compliant ID data blocks'
    print '\nUsage: ' + sys.argv[0] + ' [OPTIONS] <TYPE> <ID> [\"WRITE\"]'
    print '       ' + sys.argv[0] + ' [OPTIONS] <\"CLONE\">'
    print
    print '\t10 digit HEX ID will be translated to valid data for blocks 1 & 2'
    print '\tfor a Q5 tag running in EM4x02 emulation mode, and blocks 4 & 5 for'
    print '\ta Hitag2, where TYPE is U for UNIQUE code and E for EM4x02. For '
    print '\tguidance, standard emulation control blocks (0 & 3 respectively)'
    print '\twill also be displayed.' 
    print 
    print '\tIf the optional WRITE argument is specified, programming a Q5 or'
    print '\tHitag2 tag will be initiated.'
    print
    print '\tIf the single word CLONE is specified, the reader will scan for'
    print '\ta Unique tag and then wait for a suitable blank to be presented'
    print '\tfor writing. No prompting will take place before the target is'
    print '\toverwritten.'
    os._exit(True)


if len(args) == 1 and string.upper(args[0]) == "CLONE":
	type= 'UNIQUE'
	clone= True
	card.settagtype(card.EM4x02)
	card.waitfortag('Waiting for Unique tag...')
	id= card.uid
	idbin= card.UniqueToEM(card.HexReverse(id))
else:
	clone= False
	if len(args[1]) != 10:
		print 'ID must be 10 HEX digits!'
		os._exit(True)
	id= args[1]

if args[0] == 'E':
    type= 'EM4x02'
    idbin= card.UniqueToEM(card.HexReverse(id))
else:
    if args[0] == 'U':
        type= 'UNIQUE'
        idbin= card.ToBinaryString(card.ToBinary(id))
    else:
	if not clone:
        	print 'Unknown TYPE: ' + args[0]
        	os._exit(True)


out= card.Unique64Bit(idbin)
manchester= card.BinaryToManchester(out)
db1= '%08x' % int(out[:32],2)
db2= '%08x' % int(out[32:64],2)
print
print '  ' + type + ' ID: ' + id
print '  Q5 ID: ' + '%08x' % int(idbin[:32],2)
if type ==  'EM4x02':
    print '  UNIQUE ID: ' + '%10x' % int(idbin,2)
else:
    print '  EM4x02 ID: ' + ('%10x' % int(card.UniqueToEM(id),2))[::-1]
print '  Binary traceablility data: ' + out
print '  Manchester Encoded:        ' + manchester
print
print '  Q5 Config Block (0): ' + Q5CFB
print '  Data Block 1: ' + db1
print '  Data Block 2: ' + db2
print
print '  Hitag2 Config Block (3): ' + H2CFB 
print '  Data Block 4: ' + db1
print '  Data Block 5: ' + db2

if (len(args) == 3 and string.upper(args[2]) == 'WRITE') or clone:
	# check for Q5 first`
	if card.readertype == card.READER_ACG:
		card.settagtype(card.Q5)
		if not card.select():
                	card.settagtype(card.ALL)
        while not (card.tagtype == card.Q5 or card.tagtype == card.HITAG2):
        	card.waitfortag('Waiting for blank tag (Q5 or Hitag2)...')
        	print 'Tag ID: ' + card.uid
	if not clone:
      		x= string.upper(raw_input('  *** Warning! This will overwrite TAG! Proceed (y/n)? '))
       		if x != 'Y':
        	       	os._exit(False)
	# allow blank to settle
	time.sleep(2)
	print 'Writing...'
	if card.tagtype == card.Q5:
        	if not card.writeblock(0,Q5CFB) or not card.writeblock(1,db1) or not card.writeblock(2,db2):
            		print 'Write failed!'
            		os._exit(True)
	if card.tagtype == card.HITAG2:
        	if card.readertype == card.READER_ACG:
            		card.login('','',card.HITAG2_TRANSPORT_RWD)
        	if not card.writeblock(3,H2CFB) or not card.writeblock(4,db1) or not card.writeblock(5,db2):
            		print 'Write failed!'
            		os._exit(True)
	card.settagtype(card.EM4x02)
	card.select()
	print 'Card ID: ' + card.uid
	print '  Unique ID: ' + card.EMToUnique(card.uid)
	print 'Done!'
	card.settagtype(card.ALL)
os._exit(False)

########NEW FILE########
__FILENAME__ = writelfx
#!/usr/bin/python

#  writelfx.py - read and then write all sectors from a LFX reader
# 
#  Adam Laurie <adam@algroup.co.uk>
#  http://rfidiot.org/
# 
#  This code is copyright (c) Adam Laurie, 2009, All rights reserved.
#  For non-commercial use only, the following terms apply - for all other
#  uses, please contact the author:
#
#    This code is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#

import rfidiot
import sys
import os

try:
        card= rfidiot.card
except:
	print "Couldn't open reader!"
        os._exit(True)

args= rfidiot.args
help= rfidiot.help

Q5Mod= { '000':'Manchester',\
	 '001':'PSK 1',\
	 '010':'PSK 2',\
	 '011':'PSK 3',\
	 '100':'FSK 1 (a = 0)',\
	 '101':'FSK 2 (a = 0)',\
	 '110':'Biphase',\
	 '111':'NRZ / direct'}

card.info('writelfx v0.1c')

# force card type if specified
if len(args) > 0:
	print 'Setting tag type:', args[0]
	card.settagtype(args[0])
else:
	card.settagtype(card.ALL)
card.select()
ID= card.uid
print 'Card ID: ' + ID
print 'Tag type: ' + card.LFXTags[card.tagtype]

# set key if specified
if len(args) > 1:
	key= args[1]
else:
	key= ''

# Login to Hitag2
if card.tagtype == card.HITAG2 and card.readertype == card.READER_ACG:
	if not key:
		key= card.HITAG2_TRANSPORT_RWD
	print ' Logging in with key: ' + key
	if not card.login('','',key):
		print 'Login failed!'
		os._exit(True)

# Interpret EM4x05 ID structure
if card.tagtype == card.EM4x05:
	card.FDXBIDPrint(ID)

# Q5 cards can emulate other cards, so check if this one responds as Q5
if card.tagtype == card.EM4x02 or card.tagtype == card.Q5 or card.tagtype ==  card.EM4x05:
	print '  Checking for Q5'
	card.settagtype(card.Q5)
	card.select()
	Q5ID= card.uid
	if card.tagtype == card.Q5:
		print '    Q5 ID: ' + Q5ID
		print
		card.readblock(0)
		print '    Config Block: ',
		print card.ToHex(card.binary)
		print '    Config Binary: ',
		configbin= card.ToBinaryString(card.binary)
		print configbin
		print '          Reserved: ' + configbin[:12]
		print '       Page Select: ' + configbin[12]
		print '        Fast Write: ' + configbin[13]
		print '  Data Bit Rate n5: ' + configbin[14]
		print '  Data Bit Rate n4: ' + configbin[15]
		print '  Data Bit Rate n3: ' + configbin[16]
		print '  Data Bit Rate n2: ' + configbin[17]
		print '  Data Bit Rate n1: ' + configbin[18]
		print '  Data Bit Rate n0: ' + configbin[19]
		print ' (Field Clocks/Bit: %d)' % (2 * int(configbin[14:20],2) + 2)
		print '           Use AOR: ' + configbin[20]
		print '           Use PWD: ' + configbin[21]
		print '  PSK Carrier Freq: ' + configbin[22] + configbin[23]
		print '  Inverse data out: ' + configbin[24]
		print '        Modulation: ' + configbin[25] + configbin[26] + configbin[27] + " (%s)" % Q5Mod[configbin[25] + configbin[26] + configbin[27]]
		print '          Maxblock: ' + configbin[28] + configbin[29] + configbin[30] + " (%d)" % int (configbin[28] + configbin[29] + configbin[30],2)
		print '        Terminator: ' + configbin[31]
		print
		# Emulated ID is contained in 'traceability data'
		print '    Traceability Data 1: ',
		card.readblock(1)
		td1= card.binary
# to test a hardwired number, uncomment following line (and td2 below)
#		td1= chr(0xff) + chr(0x98) + chr(0xa6) + chr(0x4a)
		print card.ToHex(td1)
		print '    Traceability Data 2: ',
		card.readblock(2)
		td2= card.binary
# don't forget to set column parity!
#		td2= chr(0x98) + chr(0xf8) + chr(0xc8) + chr(0x06)
		print card.ToHex(td2)
		print '    Traceability Binary: ',
		tdbin= card.ToBinaryString(td1 + td2)
		print tdbin
		# traceability is broken into 4 bit chunks with even parity
		print
		print '      Header:',
		print tdbin[:9]
		print '                    Parity (even)'
		print '      D00-D03: ' + tdbin[9:13] + ' ' + tdbin[13]
		print '      D10-D13: ' + tdbin[14:18] + ' ' + tdbin[18]
		print '      D20-D23: ' + tdbin[19:23] + ' ' + tdbin[23]
		print '      D30-D33: ' + tdbin[24:28] + ' ' + tdbin[28]
		print '      D40-D43: ' + tdbin[29:33] + ' ' + tdbin[33]
		print '      D50-D53: ' + tdbin[34:38] + ' ' + tdbin[38]
		print '      D60-D63: ' + tdbin[39:43] + ' ' + tdbin[43]
		print '      D70-D73: ' + tdbin[44:48] + ' ' + tdbin[48]
		print '      D80-D83: ' + tdbin[49:53] + ' ' + tdbin[53]
		print '      D90-D93: ' + tdbin[54:58] + ' ' + tdbin[58]
		print '               ' + tdbin[59:63] + ' ' + tdbin[63] + ' Column Parity & Stop Bit'
		# reconstruct data bytes
		d0= chr(int(tdbin[9:13] + tdbin[14:18],2))
		d1= chr(int(tdbin[19:23] + tdbin[24:28],2))
		d2= chr(int(tdbin[29:33] + tdbin[34:38],2))
		d3= chr(int(tdbin[39:43] + tdbin[44:48],2))
		d4= chr(int(tdbin[49:53] + tdbin[54:58],2))
		print
		print '      Reconstructed data D00-D93 (UNIQUE ID): ',
		card.HexPrint(d0 + d1 + d2 + d3 + d4)
		# set ID to Q5ID so block reading works
		ID= Q5ID
		print
	else:
		print '    Native - UNIQUE ID: ' + card.EMToUnique(ID)

sector = 0
print
print ' Writing...'
print
while sector < card.LFXTagBlocks[card.tagtype]:
        print ' sector %02x: ' % sector,
	if card.readblock(sector):
		print card.data,
		if not card.writeblock(sector,card.data):
			print 'Write failed'
		else:
			print 'OK'
	else:
		print 'Read error: ' + card.errorcode
        sector += 1
print

# set reader back to all cards
card.settagtype(card.ALL)
card.select()
print
os._exit(False)


########NEW FILE########
__FILENAME__ = writemifare1k
#!/usr/bin/python

#  writemifare1k.py - write all blocks on a mifare standard tag
# 
#  Adam Laurie <adam@algroup.co.uk>
#  http://rfidiot.org/
# 
#  This code is copyright (c) Adam Laurie, 2006, All rights reserved.
#  For non-commercial use only, the following terms apply - for all other
#  uses, please contact the author:
#
#    This code is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#


import rfidiot
import sys
import random
import string
import os

try:
        card= rfidiot.card
except:
	print "Couldn't open reader!"
        os._exit(True)

args= rfidiot.args
help= rfidiot.help

card.info('writemifare1k v0.1f')
card.select()
print 'Card ID: ' + card.uid
while True:
	x= string.upper(raw_input('\n*** Warning! This will overwrite all data blocks! Proceed (y/n)? '))
	if x == 'N':
		os._exit(False)
	if x == 'Y':
		break

sector = 1
while sector < 0x10:
        for type in ['AA', 'BB', 'FF']:
                card.select()
		print ' sector %02x: Keytype: %s' % (sector, type),
                if card.login(sector,type,'FFFFFFFFFFFF'):
			for block in range(3):
                		print '\n  block %02x: ' % ((sector * 4) + block),
				if len(args) == 1:
					data= args[0]
				else:
					data = '%032x' % random.getrandbits(128)
                        	print 'Data: ' + data,
				if card.writeblock((sector * 4) + block,data):
					print ' OK'
                		elif card.errorcode:
                        		print 'error %s %s' % (card.errorcode , card.ISO7816ErrorCodes[card.errorcode])
		elif type == 'FF':
				print 'login failed'
               	print '\r',
                sys.stdout.flush()           
        sector += 1
	print
print
os._exit(False)

########NEW FILE########
