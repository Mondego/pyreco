__FILENAME__ = avivore
#!/usr/bin/env python

import time
from twitter import *
import re
import sys
import os
import locale
import sqlite3 as lite

"""
Here are the various settings we'll want to use for the application.
"""
TwitterSearchTerms = [ "ip server", "blackberry pin", "bb pin", "text me", "call me", "new number",
                        "new phone", "phone me", "ip address" ]
TwitterSearchInterval = 8 # You'll want to set this to ten seconds or higher.

"""
Twitter-related functions.
"""
def TwitterSearch(string):
    try:
        TwitSearch = Twitter(domain="search.twitter.com")
        TwitterRetr = TwitSearch.search(q=string)
        output = TwitterRetr['results']
    except:
        output = 1 # If this bombs out, we have the option of at least spitting out a result.
    return output

def TwitterReadTweet(string):
    FindNum = re.compile(r'(\d{3}[-\.\s]??\d{3}[-\.\s]??\d{4}|\(\d{3}\)\s*\d{3}[-\.\s]??\d{4}|\d{3}[-\.\s]??\d{4})')
    result = FindNum.findall(string)
    if result == []: # If we don't find phone numbers, we'll move on.
        FindBBPIN = re.compile(r'\b[a-fA-F0-9]{8}\b') # Let's find a Blackberry PIN!
        result = FindBBPIN.findall(string)
        if result == []: # No BB pin? Let's try for an IP address.
            FindIPAddr = re.compile(r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b')
            result = FindIPAddr.findall(string)
            if result == []: # Guess we have nothing.
                return 0, 0
            else:
                return 3, result[0]
        else:
            return 2, result[0]
    else: # By default we look for phone numbers, so if we find that it has a result, we'll try and verify it.
        result = ValidNumber(result) # This is kind of a placeholder for later on. Kind of redundant I know.
        if result == 0:
            return 0, result
        else:
            return 1, result

def ValidNumber(num): # This will filter out non-NANP numbers. It's not fool-proof but good enough.
    string = re.sub("[^0-9]", "", str(num))
    if int(string[:1]) == 0 or len(string) != 10:
        string = 0
    return string

"""
Various functions for this application.
"""
def Main():
    LastAction = time.time() # Sets the initial time to start our scan. It's not used however.
    Stored = []
    while 1:
        for x in TwitterSearchTerms:
            TwitData = TwitterSearch(x)
            if TwitData is None: # With the defaults, it's unlikely that this message will come up.
                message = "Nothing found for \"" + x + "\". Waiting " + str(TwitterSearchInterval) + " seconds to try again."
                Output(message)
            else:
                for y in TwitterSearch(x):
                    z = y['id'], y['created_at'], y['from_user'], y['text']
                    result = TwitterReadTweet(z[3])
                    if result[0] == 0:
                        pass
                    else: # If something is found, then we'll process the tweet
                        Stored = Stored, int(z[0])
                        string = result[0], z[2], result[1], z[0], z[3] # result value, time, result itself, tweet ID, tweet itself
                        message = ProcessTweet(string)
                        Output(message)
            time.sleep(TwitterSearchInterval) # This will pause the script 

def Output(string):
    # Default text output for the console.
    if string == 0:
        pass
    else:
        print "[" + str(round(time.time(),0))[:-2] + "]", string # This is sort of lame but whatever.

def ProcessTweet(string): 
    # This is just to write the tweet to the DB and then to output it in a friendly manner.
    # I guess it can be cleaned up but it works.
    if DBDupCheck(string[3]) == 0:
        DBWriteValue(time.time(), string[0], string[1], string[2], string[3], string[4])
        if string[0] == 1: # Phone numbers
            return "Type: phone, User: " + string[1] + ", Number: " + str(ValidNumber(string[2])) + \
                    ", TweetID: " + str(string[3])

        elif string[0] == 2: # Blackberry PIN
            return "Type: bbpin, User: " + string[1] + ", PIN: " + string[2] + ", TweetID: " + str(string[3])
        elif string[0] == 3: # IP addresses
            return "Type: ipadr, User: " + string[1] + ", IP: " + string[2] + ", TweetID: " + str(string[3])
    else:
        return 0

def DBDupCheck(value):
    # The nice thing about using the SQL DB is that I can just have it make a query to make a duplicate check.
    # This can likely be done better but it's "good enough" for now.
    string = "SELECT * FROM Data WHERE TID IS \'" + str(int(value)) + "\'"
    con = lite.connect(DBPath)
    cur = con.cursor()
    cur.execute(string)
    if cur.fetchone() != None: # We should only have to pull one.
        output = 1
    else:
        output = 0
    return output

def DBWriteValue(Time, Type, User, Value, TweetID, Message):
    # Just a simple function to write the results to the database.
    con = lite.connect(DBPath)
    qstring = "INSERT INTO Data VALUES(?, ?, ?, ?, ?, ?)"
    with con:
        cur = con.cursor()
        cur.execute(qstring, ( unicode(Time), unicode(Type), unicode(User), unicode(Value), unicode(TweetID), unicode(Message) ) )
        lid = cur.lastrowid

def InitDatabase(status, filename):
    if os.path.isfile(filename):
        Output("Using existing database to store results.")
        DBCon = lite.connect(filename)
        DBCur = DBCon.cursor()
        DBCur.execute("SELECT Count(*) FROM Data")
        Output(str(DBCur.fetchone()[0]) + " entries in this database so far.")
	'''
        # Removed the items below due to a bug. It's not needed really.
        DBCur.execute("SELECT * FROM Data ORDER BY TimeRecv ASC LIMIT 1")
        print DBCur.fetchone()[0]
        DatabaseFirstWrite = float(DBCur.fetchone()[0]) + 2
        Output("Database first written to " + str(DataBaseFirstWrite))
        '''
    else: # If the database doesn't exist, we'll create it.
        if status == 1: # If we desire to save the database, it will output this message.
            Output("Creating a new database to store data!")
        # Eventually I'll set this up to just delete the DB at close should it be chosen as an option.
        DBCon = lite.connect(filename)
        DBCur = DBCon.cursor()
        DBCur.execute("CREATE TABLE Data (TimeRecv int, Type int, User text, Value text, TID int, Message text)")

def SoftwareInitMsg(version):
    print ""
    print "  Avivore", version
    print "  A Twitter-based tool for finding personal data."
    print ""
    print "  Licensed under the LGPL and created by Colin Keigher"
    print "  http://github.com/ColinKeigher"
    print "--------------------------------------------------------"
    print ""

def SoftwareExit(type, message):
    print ""
    print message

"""
Here we go!
"""
if __name__ == "__main__":
    # This stuff will be customisable eventually.
    DBPath = "avivore.db"
    SoftwareInitMsg("1.0.1")
    InitDatabase(0, DBPath)
    try:
        Main()
    except KeyboardInterrupt:
        SoftwareExit(0, "Exiting the application.")
    except:
        Main()
        raise

########NEW FILE########
