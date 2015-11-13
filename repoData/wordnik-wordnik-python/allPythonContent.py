__FILENAME__ = AccountApiTest
#!/usr/bin/env python

import sys
import unittest
import urllib2
import json

from BaseApiTest import BaseApiTest

sys.path = ['./'] + sys.path
from wordnik import *


class AccountApiTest(BaseApiTest):

    def setUp(self):
        super(AccountApiTest, self).setUp()
        self.authToken = self.accountApi.authenticate(self.username,
                                                      self.password).token

    def testAuthenticate(self):
        res = self.accountApi.authenticate(self.username, self.password)
        assert res, 'null authenticate result'
        assert res.token, 'invalid authentication token'
        assert res.userId != 0, 'userId was 0'
        assert res.userSignature, 'invalid userSignature'

    def testAuthenticatePost(self):
        res = self.accountApi.authenticatePost(self.username, self.password)
        assert res, 'null authenticate result'
        assert res.token, 'invalid authentication token'
        assert res.userId != 0, 'userId was 0'
        assert res.userSignature, 'invalid userSignature'

    def testGetWordListsForLoggedInUser(self):
        res = self.accountApi.getWordListsForLoggedInUser(self.authToken)
        assert res, 'null getWordListsForLoggedInUser result'
        assert len(res) != 0, 'number of lists shouldn\'t be 0'

    def testGetApiTokenStatus(self):
        res = self.accountApi.getApiTokenStatus()
        assert res, 'null getApiTokenStatus result'
        assert res.valid, 'token status not valid'
        assert res.remainingCalls != 0, 'remainingCalls shouldn\'t be 0'

    def testGetLoggedInUser(self):
        res = self.accountApi.getLoggedInUser(self.authToken)
        assert res, 'null getLoggedInUser result'
        assert res.id != 0, 'if shouldn\'t be 0'
        assert res.username == self.username, 'username was incorrect'
        assert res.status == 0, 'user status should be 0'
        assert res.email, 'email shouldn\'t be null'


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = BaseApiTest
#!/usr/bin/env python
"""Unit tests for Python Wordnik API client.

Requires you to set three environment varibales:
    API_KEY      your API key
    USER_NAME    the username of a user
    PASSWORD     the user's password

Run all tests:

    python BaseApiTest.py

"""

import sys
import os
import unittest

sys.path = ['./'] + sys.path
from wordnik import *


class BaseApiTest(unittest.TestCase):

    def setUp(self):
        self.apiUrl = 'http://api.wordnik.com/v4'
        self.apiKey = os.environ.get('API_KEY')
        self.username = os.environ.get('USER_NAME')
        self.password = os.environ.get('PASSWORD')

        client = swagger.ApiClient(self.apiKey, self.apiUrl)
        self.accountApi = AccountApi.AccountApi(client)
        self.wordApi = WordApi.WordApi(client)
        self.wordListApi = WordListApi.WordListApi(client)
        self.wordsApi = WordsApi.WordsApi(client)

if __name__ == "__main__":

    from AccountApiTest import AccountApiTest
    from WordApiTest import WordApiTest
    from WordListApiTest import WordListApiTest
    from WordsApiTest import WordsApiTest

    unittest.main()

########NEW FILE########
__FILENAME__ = WordApiTest
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import unittest
import urllib2
import json

from BaseApiTest import BaseApiTest

sys.path = ['./'] + sys.path
from wordnik import *


class WordApiTest(BaseApiTest):

    def testWordApis(self):
        response = urllib2.urlopen('http://api.wordnik.com/v4/word.json')
        doc = json.loads(response.read())
        assert len(doc['apis']) == 12, 'there should be 10 word apis'

    def testGetWord(self):
        res = self.wordApi.getWord('cat')
        assert res, 'null getWord result'
        assert res.word == 'cat', 'word should be "cat"'

    def testGetWordWithSuggestions(self):
        res = self.wordApi.getWord('cAt', includeSuggestions=True)
        assert res, 'null getWord result'
        assert res.word == 'cAt', 'word should be "cAt"'

    def testGetWordWithCanonicalForm(self):
        res = self.wordApi.getWord('cAt', useCanonical=True)
        assert res, 'null getWord result'
        assert res.word == 'cat', 'word should be "cAt"'

    def testGetDefinitions(self):
        res = self.wordApi.getDefinitions('cat', limit=10)
        assert res, 'null getDefinitions result'
        assert len(res) == 10, 'should have 10 definitions'

    def testGetDefinitionsWithSpacesInWord(self):
        res = self.wordApi.getDefinitions('bon vivant')
        assert res, 'null getDefinitions result'
        assert len(res) == 1, 'should have 1 definition'

    def testGetDefinitionsUtf8Word(self):
        res = self.wordApi.getDefinitions('élan', limit=10)
        assert res, 'null getDefinitions result'
        assert res[0].word == 'élan'.decode('utf8'), 'word should be élan'

    def testGetDefinitionsUnicodeWord(self):
        res = self.wordApi.getDefinitions(u"élan", limit=10)
        assert res, 'null getDefinitions result'
        assert res[0].word == 'élan'.decode('utf8'), 'word should be élan'

    def testGetExamples(self):
        res = self.wordApi.getExamples('cat', limit=5)
        assert res, 'null getExamples result'
        assert len(res.examples) == 5, 'should have 5 definitions'

    def testGetTopExample(self):
        res = self.wordApi.getTopExample('cat')
        assert res, 'null getTopExample result'
        assert res.word == 'cat', 'word should be "cat"'

    def testGetHyphenation(self):
        res = self.wordApi.getHyphenation('catalog', limit=1)
        assert res, 'null getHyphenation result'
        assert len(res) == 1, 'hypenation length should be 1'

    def testGetWordFrequency(self):
        res = self.wordApi.getWordFrequency('cat')
        assert res, 'null getWordFrequency result'
        assert res.totalCount != 0, 'total count should not be 0'

    def testGetPhrases(self):
        res = self.wordApi.getPhrases('money')
        assert res, 'null getPhrases result'
        assert len(res) != 0, 'getPhrases length should not be 0'

    def testGetRelatedWords(self):
        res = self.wordApi.getRelatedWords('cat')
        assert res, 'null getRelatedWords result'
        for related in res:
            assert len(related.words) <= 10, 'should have <= 10 related words'

    def testGetRelatedWordsWithUtf8(self):
        res = self.wordApi.getRelatedWords('Europe')
        assert res, 'null getRelatedWords result'
        for related in res:
            assert len(related.words) <= 10, 'should have <= 10 related words'

    def testGetAudio(self):
        res = self.wordApi.getAudio('cat', useCanonical=True, limit=2)
        assert res, 'null getAudio result'
        assert len(res) == 2, 'getAudio size should be 2'

    def testGetScrabbleScore(self):
        res = self.wordApi.getScrabbleScore('quixotry')
        assert res.value == 27, 'quixotry should have a Scrabble score of 27'

    def testGetEtymologies(self):
        res = self.wordApi.getEtymologies('butter')
        assert 'of Scythian origin' in res[0], 'etymology of "butter" should contain the phrase "of Scythian origin"'


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = WordListApiTest
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import unittest
import urllib2
import json
from pprint import pprint
from BaseApiTest import BaseApiTest

sys.path = ['./'] + sys.path
from wordnik import *


class WordListApiTest(BaseApiTest):

    def setUp(self):
        super(WordListApiTest, self).setUp()
        self.authToken = self.accountApi.authenticate(self.username,
                                                      self.password).token
        self.existingList = self.accountApi.getWordListsForLoggedInUser(self.authToken,
                                                                        limit=1)[0]

        from wordnik.models import WordList
        wordList = WordList.WordList()
        wordList.name = "my test list"
        wordList.type = "PUBLIC"
        wordList.description = "some words I want to play with"

    def testGetWordListByPermalink(self):
        res = self.wordListApi.getWordListByPermalink(self.existingList.permalink,
                                                      self.authToken)
        assert res, 'null getWordListByPermalink result'

    def testGetWordListByPermalink(self):
        res = self.wordListApi.getWordListByPermalink(self.existingList.permalink,
                                                      self.authToken)
        assert res, 'null getWordListByPermalink result'

    def testUpdateWordList(self):
        import time
        description = 'list updated at ' + str(time.time())
        self.existingList.description = description
        self.wordListApi.updateWordList(self.existingList.permalink,
                                        self.authToken, body=self.existingList)

        res = self.wordListApi.getWordListByPermalink(self.existingList.permalink,
                                                      self.authToken)

        assert res.description == description, 'did not update wordlist'

    def testAddWordsToWordList(self):
        from wordnik.models import StringValue
        wordsToAdd = []
        word1 = StringValue.StringValue()
        word1.word = "delicious"
        wordsToAdd.append(word1)
        word2 = StringValue.StringValue()
        word2.word = "tasty"
        wordsToAdd.append(word2)
        word3 = StringValue.StringValue()
        word3.word = "scrumptious"
        wordsToAdd.append(word3)
        word4 = StringValue.StringValue()
        word4.word = u"élan"
        wordsToAdd.append(word4)
        self.wordListApi.addWordsToWordList(self.existingList.permalink,
                                        self.authToken, body=wordsToAdd)

        res = self.wordListApi.getWordListWords(self.existingList.permalink,
                                                self.authToken)
        listSet = set([word.word for word in res])
        addedSet = set(["delicious", "tasty", "scrumptious", u"élan"])
        assert len(listSet.intersection(addedSet)) == 4, 'did not get added words'

    def testDeleteWordsFromList(self):
        from wordnik.models import StringValue
        wordsToRemove = []
        word1 = StringValue.StringValue()
        word1.word = "delicious"
        wordsToRemove.append(word1)
        word2 = StringValue.StringValue()
        word2.word = "tasty"
        wordsToRemove.append(word2)
        word3 = StringValue.StringValue()
        word3.word = "scrumptious"
        wordsToRemove.append(word3)
        word4 = StringValue.StringValue()
        word4.word = u"élan"
        wordsToRemove.append(word4)
        self.wordListApi.deleteWordsFromWordList(self.existingList.permalink,
                                                 self.authToken,
                                                 body=wordsToRemove)

        res = self.wordListApi.getWordListWords(self.existingList.permalink,
                                                self.authToken)
        listSet = set([word.word for word in res])
        addedSet = set(["delicious", "tasty", "scrumptious", u"élan", "élan"])
        assert len(listSet.intersection(addedSet)) == 0, 'did not get removed words'

    def testAddUnicodeWordsToWordList(self):
       from wordnik.models import StringValue
       wordsToAdd = []
       word1 = StringValue.StringValue()
       word1.word = u"délicieux"
       wordsToAdd.append(word1)
       word2 = StringValue.StringValue()
       word2.word = u"νόστιμος"
       wordsToAdd.append(word2)
       word3 = StringValue.StringValue()
       word3.word = u"великолепный"
       wordsToAdd.append(word3)
       self.wordListApi.addWordsToWordList(self.existingList.permalink,
                                       self.authToken, body=wordsToAdd)
 
       res = self.wordListApi.getWordListWords(self.existingList.permalink,
                                               self.authToken)
       listSet = set([word.word for word in res])
       addedSet = set([u"délicieux", u"νόστιμος", u"великолепный"])
       assert len(listSet.intersection(addedSet)) == 3, 'did not get added words'

    def testDeleteUnicodeWordsFromList(self):
       from wordnik.models import StringValue
       wordsToRemove = []
       word1 = StringValue.StringValue()
       word1.word = u"délicieux"
       wordsToRemove.append(word1)
       word2 = StringValue.StringValue()
       word2.word = u"νόστιμος"
       wordsToRemove.append(word2)
       word3 = StringValue.StringValue()
       word3.word = u"великолепный"
       wordsToRemove.append(word3)
       self.wordListApi.deleteWordsFromWordList(self.existingList.permalink,
                                                self.authToken,
                                                body=wordsToRemove)
 
       res = self.wordListApi.getWordListWords(self.existingList.permalink,
                                               self.authToken)
       listSet = set([word.word for word in res])
       addedSet = set([u"délicieux", u"νόστιμος", u"великолепный"])
       assert len(listSet.intersection(addedSet)) == 0, 'did not get removed words'

    def testAddUnicodeWordsToWordList(self):
        from wordnik.models import StringValue
        wordsToAdd = []
        word1 = StringValue.StringValue()
        word1.word = u"délicieux"
        wordsToAdd.append(word1)
        word2 = StringValue.StringValue()
        word2.word = u"νόστιμος"
        wordsToAdd.append(word2)
        word3 = StringValue.StringValue()
        word3.word = u"великолепный"
        wordsToAdd.append(word3)
        self.wordListApi.addWordsToWordList(self.existingList.permalink,
                                        self.authToken, body=wordsToAdd)

        res = self.wordListApi.getWordListWords(self.existingList.permalink,
                                                self.authToken)
        listSet = set([word.word for word in res])
        addedSet = set([u"délicieux", u"νόστιμος", u"великолепный"])
        assert len(listSet.intersection(addedSet)) == 3, 'did not get added words'

    def testDeleteUnicodeWordsFromList(self):
        from wordnik.models import StringValue
        wordsToRemove = []
        word1 = StringValue.StringValue()
        word1.word = u"délicieux"
        wordsToRemove.append(word1)
        word2 = StringValue.StringValue()
        word2.word = u"νόστιμος"
        wordsToRemove.append(word2)
        word3 = StringValue.StringValue()
        word3.word = u"великолепный"
        wordsToRemove.append(word3)
        self.wordListApi.deleteWordsFromWordList(self.existingList.permalink,
                                                 self.authToken,
                                                 body=wordsToRemove)

        res = self.wordListApi.getWordListWords(self.existingList.permalink,
                                                self.authToken)
        listSet = set([word.word for word in res])
        addedSet = set([u"délicieux", u"νόστιμος", u"великолепный"])
        assert len(listSet.intersection(addedSet)) == 0, 'did not get removed words'


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = WordsApiTest
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import unittest
import urllib2
import json

from BaseApiTest import BaseApiTest

sys.path = ['./'] + sys.path
from wordnik import *


class WordsApiTest(BaseApiTest):

    def testSearchWords(self):
        res = self.wordsApi.searchWords('tree')
        assert res, 'null search result'
        assert res.searchResults[0].word == 'tree', 'word should be "tree"'
        assert res.totalResults != 0, 'should not have 0 results'

    def testGetWordOfTheDay(self):
        res = self.wordsApi.getWordOfTheDay()
        assert res, 'null wordOfTheDay result'

    def testReverseDictionary(self):
        res = self.wordsApi.reverseDictionary("hairy")
        assert res, 'null reverseDictionary result'
        assert res.totalResults != 0, 'should not have 0 results'
        assert len(res.results) != 0, 'should not have 0 results'

    def testReverseDictionaryUtf8(self):
        res = self.wordsApi.reverseDictionary("élan")
        assert res, 'null reverseDictionary result'
        assert res.totalResults != 0, 'should not have 0 results'
        assert len(res.results) != 0, 'should not have 0 results'

    def testReverseDictionaryUnicode(self):
        res = self.wordsApi.reverseDictionary(u"élan")
        assert res, 'null reverseDictionary result'
        assert res.totalResults != 0, 'should not have 0 results'
        assert len(res.results) != 0, 'should not have 0 results'

    def testGetRandomWords(self):
        res = self.wordsApi.getRandomWords()
        assert res, 'null getRandomWords result'
        assert len(res) == 10, 'should get 10 random words'

    def testGetRandomWords(self):
        res = self.wordsApi.getRandomWords()
        assert res, 'null getRandomWord result'

    def testGetRandomWord(self):
        res = self.wordsApi.getRandomWords()
        assert res, 'null getRandomWord result'


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = AccountApi
#!/usr/bin/env python
"""
WordAPI.py
Copyright 2012 Wordnik, Inc.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

NOTE: This class is auto generated by the swagger code generator program. Do not edit the class manually.
"""
import sys
import os

from models import *


class AccountApi(object):

    def __init__(self, apiClient):
      self.apiClient = apiClient

    
    def authenticate(self, username, password, **kwargs):
        """Authenticates a User

        Args:
            username, str: A confirmed Wordnik username (required)
            password, str: The user's password (required)
            
        Returns: AuthenticationToken
        """

        allParams = ['username', 'password']

        params = locals()
        for (key, val) in params['kwargs'].iteritems():
            if key not in allParams:
                raise TypeError("Got an unexpected keyword argument '%s' to method authenticate" % key)
            params[key] = val
        del params['kwargs']

        resourcePath = '/account.{format}/authenticate/{username}'
        resourcePath = resourcePath.replace('{format}', 'json')
        method = 'GET'

        queryParams = {}
        headerParams = {}

        if ('password' in params):
            queryParams['password'] = self.apiClient.toPathValue(params['password'])
        if ('username' in params):
            replacement = str(self.apiClient.toPathValue(params['username']))
            resourcePath = resourcePath.replace('{' + 'username' + '}',
                                                replacement)
        postData = (params['body'] if 'body' in params else None)

        response = self.apiClient.callAPI(resourcePath, method, queryParams,
                                          postData, headerParams)

        if not response:
            return None

        responseObject = self.apiClient.deserialize(response, 'AuthenticationToken')
        return responseObject
        
        
    def authenticatePost(self, username, body, **kwargs):
        """Authenticates a user

        Args:
            username, str: A confirmed Wordnik username (required)
            body, str: The user's password (required)
            
        Returns: AuthenticationToken
        """

        allParams = ['username', 'body']

        params = locals()
        for (key, val) in params['kwargs'].iteritems():
            if key not in allParams:
                raise TypeError("Got an unexpected keyword argument '%s' to method authenticatePost" % key)
            params[key] = val
        del params['kwargs']

        resourcePath = '/account.{format}/authenticate/{username}'
        resourcePath = resourcePath.replace('{format}', 'json')
        method = 'POST'

        queryParams = {}
        headerParams = {}

        if ('username' in params):
            replacement = str(self.apiClient.toPathValue(params['username']))
            resourcePath = resourcePath.replace('{' + 'username' + '}',
                                                replacement)
        postData = (params['body'] if 'body' in params else None)

        response = self.apiClient.callAPI(resourcePath, method, queryParams,
                                          postData, headerParams)

        if not response:
            return None

        responseObject = self.apiClient.deserialize(response, 'AuthenticationToken')
        return responseObject
        
        
    def getWordListsForLoggedInUser(self, auth_token, **kwargs):
        """Fetches WordList objects for the logged-in user.

        Args:
            auth_token, str: auth_token of logged-in user (required)
            skip, int: Results to skip (optional)
            limit, int: Maximum number of results to return (optional)
            
        Returns: list[WordList]
        """

        allParams = ['auth_token', 'skip', 'limit']

        params = locals()
        for (key, val) in params['kwargs'].iteritems():
            if key not in allParams:
                raise TypeError("Got an unexpected keyword argument '%s' to method getWordListsForLoggedInUser" % key)
            params[key] = val
        del params['kwargs']

        resourcePath = '/account.{format}/wordLists'
        resourcePath = resourcePath.replace('{format}', 'json')
        method = 'GET'

        queryParams = {}
        headerParams = {}

        if ('skip' in params):
            queryParams['skip'] = self.apiClient.toPathValue(params['skip'])
        if ('limit' in params):
            queryParams['limit'] = self.apiClient.toPathValue(params['limit'])
        if ('auth_token' in params):
            headerParams['auth_token'] = params['auth_token']
        postData = (params['body'] if 'body' in params else None)

        response = self.apiClient.callAPI(resourcePath, method, queryParams,
                                          postData, headerParams)

        if not response:
            return None

        responseObject = self.apiClient.deserialize(response, 'list[WordList]')
        return responseObject
        
        
    def getApiTokenStatus(self, **kwargs):
        """Returns usage statistics for the API account.

        Args:
            api_key, str: Wordnik authentication token (optional)
            
        Returns: ApiTokenStatus
        """

        allParams = ['api_key']

        params = locals()
        for (key, val) in params['kwargs'].iteritems():
            if key not in allParams:
                raise TypeError("Got an unexpected keyword argument '%s' to method getApiTokenStatus" % key)
            params[key] = val
        del params['kwargs']

        resourcePath = '/account.{format}/apiTokenStatus'
        resourcePath = resourcePath.replace('{format}', 'json')
        method = 'GET'

        queryParams = {}
        headerParams = {}

        if ('api_key' in params):
            headerParams['api_key'] = params['api_key']
        postData = (params['body'] if 'body' in params else None)

        response = self.apiClient.callAPI(resourcePath, method, queryParams,
                                          postData, headerParams)

        if not response:
            return None

        responseObject = self.apiClient.deserialize(response, 'ApiTokenStatus')
        return responseObject
        
        
    def getLoggedInUser(self, auth_token, **kwargs):
        """Returns the logged-in User

        Args:
            auth_token, str: The auth token of the logged-in user, obtained by calling /account.{format}/authenticate/{username} (described above) (required)
            
        Returns: User
        """

        allParams = ['auth_token']

        params = locals()
        for (key, val) in params['kwargs'].iteritems():
            if key not in allParams:
                raise TypeError("Got an unexpected keyword argument '%s' to method getLoggedInUser" % key)
            params[key] = val
        del params['kwargs']

        resourcePath = '/account.{format}/user'
        resourcePath = resourcePath.replace('{format}', 'json')
        method = 'GET'

        queryParams = {}
        headerParams = {}

        if ('auth_token' in params):
            headerParams['auth_token'] = params['auth_token']
        postData = (params['body'] if 'body' in params else None)

        response = self.apiClient.callAPI(resourcePath, method, queryParams,
                                          postData, headerParams)

        if not response:
            return None

        responseObject = self.apiClient.deserialize(response, 'User')
        return responseObject
        
        
    



########NEW FILE########
__FILENAME__ = ApiTokenStatus
#!/usr/bin/env python
"""
Copyright 2012 Wordnik, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
class ApiTokenStatus:
    """NOTE: This class is auto generated by the swagger code generator program.
    Do not edit the class manually."""


    def __init__(self):
        self.swaggerTypes = {
            'valid': 'bool',
            'token': 'str',
            'resetsInMillis': 'long',
            'remainingCalls': 'long',
            'expiresInMillis': 'long',
            'totalRequests': 'long'

        }


        self.valid = None # bool
        self.token = None # str
        self.resetsInMillis = None # long
        self.remainingCalls = None # long
        self.expiresInMillis = None # long
        self.totalRequests = None # long
        

########NEW FILE########
__FILENAME__ = AudioFile
#!/usr/bin/env python
"""
Copyright 2012 Wordnik, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
class AudioFile:
    """NOTE: This class is auto generated by the swagger code generator program.
    Do not edit the class manually."""


    def __init__(self):
        self.swaggerTypes = {
            'attributionUrl': 'str',
            'commentCount': 'int',
            'voteCount': 'int',
            'fileUrl': 'str',
            'audioType': 'str',
            'id': 'long',
            'duration': 'float',
            'attributionText': 'str',
            'createdBy': 'str',
            'description': 'str',
            'createdAt': 'datetime',
            'voteWeightedAverage': 'float',
            'voteAverage': 'float',
            'word': 'str'

        }


        self.attributionUrl = None # str
        self.commentCount = None # int
        self.voteCount = None # int
        self.fileUrl = None # str
        self.audioType = None # str
        self.id = None # long
        self.duration = None # float
        self.attributionText = None # str
        self.createdBy = None # str
        self.description = None # str
        self.createdAt = None # datetime
        self.voteWeightedAverage = None # float
        self.voteAverage = None # float
        self.word = None # str
        

########NEW FILE########
__FILENAME__ = AuthenticationToken
#!/usr/bin/env python
"""
Copyright 2012 Wordnik, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
class AuthenticationToken:
    """NOTE: This class is auto generated by the swagger code generator program.
    Do not edit the class manually."""


    def __init__(self):
        self.swaggerTypes = {
            'token': 'str',
            'userId': 'long',
            'userSignature': 'str'

        }


        self.token = None # str
        self.userId = None # long
        self.userSignature = None # str
        

########NEW FILE########
__FILENAME__ = Bigram
#!/usr/bin/env python
"""
Copyright 2012 Wordnik, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
class Bigram:
    """NOTE: This class is auto generated by the swagger code generator program.
    Do not edit the class manually."""


    def __init__(self):
        self.swaggerTypes = {
            'count': 'long',
            'gram2': 'str',
            'gram1': 'str',
            'wlmi': 'float',
            'mi': 'float'

        }


        self.count = None # long
        self.gram2 = None # str
        self.gram1 = None # str
        self.wlmi = None # float
        self.mi = None # float
        

########NEW FILE########
__FILENAME__ = Citation
#!/usr/bin/env python
"""
Copyright 2012 Wordnik, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
class Citation:
    """NOTE: This class is auto generated by the swagger code generator program.
    Do not edit the class manually."""


    def __init__(self):
        self.swaggerTypes = {
            'cite': 'str',
            'source': 'str'

        }


        self.cite = None # str
        self.source = None # str
        

########NEW FILE########
__FILENAME__ = ContentProvider
#!/usr/bin/env python
"""
Copyright 2012 Wordnik, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
class ContentProvider:
    """NOTE: This class is auto generated by the swagger code generator program.
    Do not edit the class manually."""


    def __init__(self):
        self.swaggerTypes = {
            'id': 'int',
            'name': 'str'

        }


        self.id = None # int
        self.name = None # str
        

########NEW FILE########
__FILENAME__ = Definition
#!/usr/bin/env python
"""
Copyright 2012 Wordnik, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
class Definition:
    """NOTE: This class is auto generated by the swagger code generator program.
    Do not edit the class manually."""


    def __init__(self):
        self.swaggerTypes = {
            'extendedText': 'str',
            'text': 'str',
            'sourceDictionary': 'str',
            'citations': 'list[Citation]',
            'labels': 'list[Label]',
            'score': 'float',
            'exampleUses': 'list[ExampleUsage]',
            'attributionUrl': 'str',
            'seqString': 'str',
            'attributionText': 'str',
            'relatedWords': 'list[Related]',
            'sequence': 'str',
            'word': 'str',
            'notes': 'list[Note]',
            'textProns': 'list[TextPron]',
            'partOfSpeech': 'str'

        }


        self.extendedText = None # str
        self.text = None # str
        self.sourceDictionary = None # str
        self.citations = None # list[Citation]
        self.labels = None # list[Label]
        self.score = None # float
        self.exampleUses = None # list[ExampleUsage]
        self.attributionUrl = None # str
        self.seqString = None # str
        self.attributionText = None # str
        self.relatedWords = None # list[Related]
        self.sequence = None # str
        self.word = None # str
        self.notes = None # list[Note]
        self.textProns = None # list[TextPron]
        self.partOfSpeech = None # str
        

########NEW FILE########
__FILENAME__ = DefinitionSearchResults
#!/usr/bin/env python
"""
Copyright 2012 Wordnik, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
class DefinitionSearchResults:
    """NOTE: This class is auto generated by the swagger code generator program.
    Do not edit the class manually."""


    def __init__(self):
        self.swaggerTypes = {
            'results': 'list[Definition]',
            'totalResults': 'int'

        }


        self.results = None # list[Definition]
        self.totalResults = None # int
        

########NEW FILE########
__FILENAME__ = Example
#!/usr/bin/env python
"""
Copyright 2012 Wordnik, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
class Example:
    """NOTE: This class is auto generated by the swagger code generator program.
    Do not edit the class manually."""


    def __init__(self):
        self.swaggerTypes = {
            'id': 'long',
            'exampleId': 'long',
            'title': 'str',
            'text': 'str',
            'score': 'ScoredWord',
            'sentence': 'Sentence',
            'word': 'str',
            'provider': 'ContentProvider',
            'year': 'int',
            'rating': 'float',
            'documentId': 'long',
            'url': 'str'

        }


        self.id = None # long
        self.exampleId = None # long
        self.title = None # str
        self.text = None # str
        self.score = None # ScoredWord
        self.sentence = None # Sentence
        self.word = None # str
        self.provider = None # ContentProvider
        self.year = None # int
        self.rating = None # float
        self.documentId = None # long
        self.url = None # str
        

########NEW FILE########
__FILENAME__ = ExampleSearchResults
#!/usr/bin/env python
"""
Copyright 2012 Wordnik, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
class ExampleSearchResults:
    """NOTE: This class is auto generated by the swagger code generator program.
    Do not edit the class manually."""


    def __init__(self):
        self.swaggerTypes = {
            'facets': 'list[Facet]',
            'examples': 'list[Example]'

        }


        self.facets = None # list[Facet]
        self.examples = None # list[Example]
        

########NEW FILE########
__FILENAME__ = ExampleUsage
#!/usr/bin/env python
"""
Copyright 2012 Wordnik, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
class ExampleUsage:
    """NOTE: This class is auto generated by the swagger code generator program.
    Do not edit the class manually."""


    def __init__(self):
        self.swaggerTypes = {
            'text': 'str'

        }


        self.text = None # str
        

########NEW FILE########
__FILENAME__ = Facet
#!/usr/bin/env python
"""
Copyright 2012 Wordnik, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
class Facet:
    """NOTE: This class is auto generated by the swagger code generator program.
    Do not edit the class manually."""


    def __init__(self):
        self.swaggerTypes = {
            'facetValues': 'list[FacetValue]',
            'name': 'str'

        }


        self.facetValues = None # list[FacetValue]
        self.name = None # str
        

########NEW FILE########
__FILENAME__ = FacetValue
#!/usr/bin/env python
"""
Copyright 2012 Wordnik, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
class FacetValue:
    """NOTE: This class is auto generated by the swagger code generator program.
    Do not edit the class manually."""


    def __init__(self):
        self.swaggerTypes = {
            'count': 'long',
            'value': 'str'

        }


        self.count = None # long
        self.value = None # str
        

########NEW FILE########
__FILENAME__ = Frequency
#!/usr/bin/env python
"""
Copyright 2012 Wordnik, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
class Frequency:
    """NOTE: This class is auto generated by the swagger code generator program.
    Do not edit the class manually."""


    def __init__(self):
        self.swaggerTypes = {
            'count': 'long',
            'year': 'int'

        }


        self.count = None # long
        self.year = None # int
        

########NEW FILE########
__FILENAME__ = FrequencySummary
#!/usr/bin/env python
"""
Copyright 2012 Wordnik, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
class FrequencySummary:
    """NOTE: This class is auto generated by the swagger code generator program.
    Do not edit the class manually."""


    def __init__(self):
        self.swaggerTypes = {
            'unknownYearCount': 'int',
            'totalCount': 'long',
            'frequencyString': 'str',
            'word': 'str',
            'frequency': 'list[Frequency]'

        }


        self.unknownYearCount = None # int
        self.totalCount = None # long
        self.frequencyString = None # str
        self.word = None # str
        self.frequency = None # list[Frequency]
        

########NEW FILE########
__FILENAME__ = Label
#!/usr/bin/env python
"""
Copyright 2012 Wordnik, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
class Label:
    """NOTE: This class is auto generated by the swagger code generator program.
    Do not edit the class manually."""


    def __init__(self):
        self.swaggerTypes = {
            'text': 'str',
            'type': 'str'

        }


        self.text = None # str
        self.type = None # str
        

########NEW FILE########
__FILENAME__ = Note
#!/usr/bin/env python
"""
Copyright 2012 Wordnik, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
class Note:
    """NOTE: This class is auto generated by the swagger code generator program.
    Do not edit the class manually."""


    def __init__(self):
        self.swaggerTypes = {
            'noteType': 'str',
            'appliesTo': 'list[str]',
            'value': 'str',
            'pos': 'int'

        }


        self.noteType = None # str
        self.appliesTo = None # list[str]
        self.value = None # str
        self.pos = None # int
        

########NEW FILE########
__FILENAME__ = Related
#!/usr/bin/env python
"""
Copyright 2012 Wordnik, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
class Related:
    """NOTE: This class is auto generated by the swagger code generator program.
    Do not edit the class manually."""


    def __init__(self):
        self.swaggerTypes = {
            'label1': 'str',
            'relationshipType': 'str',
            'label2': 'str',
            'label3': 'str',
            'words': 'list[str]',
            'gram': 'str',
            'label4': 'str'

        }


        self.label1 = None # str
        self.relationshipType = None # str
        self.label2 = None # str
        self.label3 = None # str
        self.words = None # list[str]
        self.gram = None # str
        self.label4 = None # str
        

########NEW FILE########
__FILENAME__ = ScoredWord
#!/usr/bin/env python
"""
Copyright 2012 Wordnik, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
class ScoredWord:
    """NOTE: This class is auto generated by the swagger code generator program.
    Do not edit the class manually."""


    def __init__(self):
        self.swaggerTypes = {
            'position': 'int',
            'id': 'long',
            'docTermCount': 'int',
            'lemma': 'str',
            'wordType': 'str',
            'score': 'float',
            'sentenceId': 'long',
            'word': 'str',
            'stopword': 'bool',
            'baseWordScore': 'float',
            'partOfSpeech': 'str'

        }


        self.position = None # int
        self.id = None # long
        self.docTermCount = None # int
        self.lemma = None # str
        self.wordType = None # str
        self.score = None # float
        self.sentenceId = None # long
        self.word = None # str
        self.stopword = None # bool
        self.baseWordScore = None # float
        self.partOfSpeech = None # str
        

########NEW FILE########
__FILENAME__ = ScrabbleScoreResult
#!/usr/bin/env python
"""
Copyright 2012 Wordnik, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
class ScrabbleScoreResult:
    """NOTE: This class is auto generated by the swagger code generator program.
    Do not edit the class manually."""


    def __init__(self):
        self.swaggerTypes = {
            'value': 'int'

        }


        self.value = None # int
        

########NEW FILE########
__FILENAME__ = Sentence
#!/usr/bin/env python
"""
Copyright 2012 Wordnik, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
class Sentence:
    """NOTE: This class is auto generated by the swagger code generator program.
    Do not edit the class manually."""


    def __init__(self):
        self.swaggerTypes = {
            'hasScoredWords': 'bool',
            'id': 'long',
            'scoredWords': 'list[ScoredWord]',
            'display': 'str',
            'rating': 'int',
            'documentMetadataId': 'long'

        }


        self.hasScoredWords = None # bool
        self.id = None # long
        self.scoredWords = None # list[ScoredWord]
        self.display = None # str
        self.rating = None # int
        self.documentMetadataId = None # long
        

########NEW FILE########
__FILENAME__ = SimpleDefinition
#!/usr/bin/env python
"""
Copyright 2012 Wordnik, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
class SimpleDefinition:
    """NOTE: This class is auto generated by the swagger code generator program.
    Do not edit the class manually."""


    def __init__(self):
        self.swaggerTypes = {
            'text': 'str',
            'source': 'str',
            'note': 'str',
            'partOfSpeech': 'str'

        }


        self.text = None # str
        self.source = None # str
        self.note = None # str
        self.partOfSpeech = None # str
        

########NEW FILE########
__FILENAME__ = SimpleExample
#!/usr/bin/env python
"""
Copyright 2012 Wordnik, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
class SimpleExample:
    """NOTE: This class is auto generated by the swagger code generator program.
    Do not edit the class manually."""


    def __init__(self):
        self.swaggerTypes = {
            'id': 'long',
            'title': 'str',
            'text': 'str',
            'url': 'str'

        }


        self.id = None # long
        self.title = None # str
        self.text = None # str
        self.url = None # str
        

########NEW FILE########
__FILENAME__ = StringValue
#!/usr/bin/env python
"""
Copyright 2012 Wordnik, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
class StringValue:
    """NOTE: This class is auto generated by the swagger code generator program.
    Do not edit the class manually."""


    def __init__(self):
        self.swaggerTypes = {
            'word': 'str'

        }


        self.word = None # str
        

########NEW FILE########
__FILENAME__ = Syllable
#!/usr/bin/env python
"""
Copyright 2012 Wordnik, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
class Syllable:
    """NOTE: This class is auto generated by the swagger code generator program.
    Do not edit the class manually."""


    def __init__(self):
        self.swaggerTypes = {
            'text': 'str',
            'seq': 'int',
            'type': 'str'

        }


        self.text = None # str
        self.seq = None # int
        self.type = None # str
        

########NEW FILE########
__FILENAME__ = TextPron
#!/usr/bin/env python
"""
Copyright 2012 Wordnik, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
class TextPron:
    """NOTE: This class is auto generated by the swagger code generator program.
    Do not edit the class manually."""


    def __init__(self):
        self.swaggerTypes = {
            'raw': 'str',
            'seq': 'int',
            'rawType': 'str'

        }


        self.raw = None # str
        self.seq = None # int
        self.rawType = None # str
        

########NEW FILE########
__FILENAME__ = User
#!/usr/bin/env python
"""
Copyright 2012 Wordnik, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
class User:
    """NOTE: This class is auto generated by the swagger code generator program.
    Do not edit the class manually."""


    def __init__(self):
        self.swaggerTypes = {
            'id': 'long',
            'username': 'str',
            'email': 'str',
            'status': 'int',
            'faceBookId': 'str',
            'userName': 'str',
            'displayName': 'str',
            'password': 'str'

        }


        self.id = None # long
        self.username = None # str
        self.email = None # str
        self.status = None # int
        self.faceBookId = None # str
        self.userName = None # str
        self.displayName = None # str
        self.password = None # str
        

########NEW FILE########
__FILENAME__ = WordList
#!/usr/bin/env python
"""
Copyright 2012 Wordnik, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
class WordList:
    """NOTE: This class is auto generated by the swagger code generator program.
    Do not edit the class manually."""


    def __init__(self):
        self.swaggerTypes = {
            'id': 'long',
            'permalink': 'str',
            'name': 'str',
            'createdAt': 'datetime',
            'updatedAt': 'datetime',
            'lastActivityAt': 'datetime',
            'username': 'str',
            'userId': 'long',
            'description': 'str',
            'numberWordsInList': 'long',
            'type': 'str'

        }


        self.id = None # long
        self.permalink = None # str
        self.name = None # str
        self.createdAt = None # datetime
        self.updatedAt = None # datetime
        self.lastActivityAt = None # datetime
        self.username = None # str
        self.userId = None # long
        self.description = None # str
        self.numberWordsInList = None # long
        self.type = None # str
        

########NEW FILE########
__FILENAME__ = WordListWord
#!/usr/bin/env python
"""
Copyright 2012 Wordnik, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
class WordListWord:
    """NOTE: This class is auto generated by the swagger code generator program.
    Do not edit the class manually."""


    def __init__(self):
        self.swaggerTypes = {
            'id': 'long',
            'word': 'str',
            'username': 'str',
            'userId': 'long',
            'createdAt': 'datetime',
            'numberCommentsOnWord': 'long',
            'numberLists': 'long'

        }


        self.id = None # long
        self.word = None # str
        self.username = None # str
        self.userId = None # long
        self.createdAt = None # datetime
        self.numberCommentsOnWord = None # long
        self.numberLists = None # long
        

########NEW FILE########
__FILENAME__ = WordObject
#!/usr/bin/env python
"""
Copyright 2012 Wordnik, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
class WordObject:
    """NOTE: This class is auto generated by the swagger code generator program.
    Do not edit the class manually."""


    def __init__(self):
        self.swaggerTypes = {
            'id': 'long',
            'word': 'str',
            'originalWord': 'str',
            'suggestions': 'list[str]',
            'canonicalForm': 'str',
            'vulgar': 'str'

        }


        self.id = None # long
        self.word = None # str
        self.originalWord = None # str
        self.suggestions = None # list[str]
        self.canonicalForm = None # str
        self.vulgar = None # str
        

########NEW FILE########
__FILENAME__ = WordOfTheDay
#!/usr/bin/env python
"""
Copyright 2012 Wordnik, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
class WordOfTheDay:
    """NOTE: This class is auto generated by the swagger code generator program.
    Do not edit the class manually."""


    def __init__(self):
        self.swaggerTypes = {
            'id': 'long',
            'parentId': 'str',
            'category': 'str',
            'createdBy': 'str',
            'createdAt': 'datetime',
            'contentProvider': 'ContentProvider',
            'htmlExtra': 'str',
            'word': 'str',
            'definitions': 'list[SimpleDefinition]',
            'examples': 'list[SimpleExample]',
            'note': 'str',
            'publishDate': 'datetime'

        }


        self.id = None # long
        self.parentId = None # str
        self.category = None # str
        self.createdBy = None # str
        self.createdAt = None # datetime
        self.contentProvider = None # ContentProvider
        self.htmlExtra = None # str
        self.word = None # str
        self.definitions = None # list[SimpleDefinition]
        self.examples = None # list[SimpleExample]
        self.note = None # str
        self.publishDate = None # datetime
        

########NEW FILE########
__FILENAME__ = WordSearchResult
#!/usr/bin/env python
"""
Copyright 2012 Wordnik, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
class WordSearchResult:
    """NOTE: This class is auto generated by the swagger code generator program.
    Do not edit the class manually."""


    def __init__(self):
        self.swaggerTypes = {
            'count': 'long',
            'lexicality': 'float',
            'word': 'str'

        }


        self.count = None # long
        self.lexicality = None # float
        self.word = None # str
        

########NEW FILE########
__FILENAME__ = WordSearchResults
#!/usr/bin/env python
"""
Copyright 2012 Wordnik, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
class WordSearchResults:
    """NOTE: This class is auto generated by the swagger code generator program.
    Do not edit the class manually."""


    def __init__(self):
        self.swaggerTypes = {
            'searchResults': 'list[WordSearchResult]',
            'totalResults': 'int'

        }


        self.searchResults = None # list[WordSearchResult]
        self.totalResults = None # int
        

########NEW FILE########
__FILENAME__ = swagger
#!/usr/bin/env python
"""Wordnik.com's Swagger generic API client. This client handles the client-
server communication, and is invariant across implementations. Specifics of
the methods and models for each application are generated from the Swagger
templates."""

import sys
import os
import re
import urllib
import urllib2
import httplib
import json
import datetime

from models import *


class ApiClient:
    """Generic API client for Swagger client library builds"""

    def __init__(self, apiKey=None, apiServer=None):
        if apiKey == None:
            raise Exception('You must pass an apiKey when instantiating the '
                            'APIClient')
        self.apiKey = apiKey
        self.apiServer = apiServer
        self.cookie = None

    def callAPI(self, resourcePath, method, queryParams, postData,
                headerParams=None):

        url = self.apiServer + resourcePath
        headers = {}
        if headerParams:
            for param, value in headerParams.iteritems():
                headers[param] = value

        headers['Content-type'] = 'application/json'
        headers['api_key'] = self.apiKey

        if self.cookie:
            headers['Cookie'] = self.cookie

        data = None

        if method == 'GET':

            if queryParams:
                # Need to remove None values, these should not be sent
                sentQueryParams = {}
                for param, value in queryParams.items():
                    if value != None:
                        sentQueryParams[param] = value
                url = url + '?' + urllib.urlencode(sentQueryParams)

        elif method in ['POST', 'PUT', 'DELETE']:

            if postData:
                headers['Content-type'] = 'application/json'
                data = self.sanitizeForSerialization(postData)
                data = json.dumps(data)

        else:
            raise Exception('Method ' + method + ' is not recognized.')

        request = MethodRequest(method=method, url=url, headers=headers,
                                data=data)

        # Make the request
        response = urllib2.urlopen(request)
        if 'Set-Cookie' in response.headers:
            self.cookie = response.headers['Set-Cookie']
        string = response.read()

        try:
            data = json.loads(string)
        except ValueError:  # PUT requests don't return anything
            data = None

        return data

    def toPathValue(self, obj):
        """Convert a string or object to a path-friendly value
        Args:
            obj -- object or string value
        Returns:
            string -- quoted value
        """
        if type(obj) == list:
            return urllib.quote(','.join(obj))
        elif type(obj) == unicode:
            return urllib.quote(obj.encode('utf8'))
        else:
            return urllib.quote(str(obj))

    def sanitizeForSerialization(self, obj):
        """Dump an object into JSON for POSTing."""

        if not obj:
            return None
        elif type(obj) in [str, int, long, float, bool, unicode]:
            return obj
        elif type(obj) == unicode:
            return obj.encode('utf8')
        elif type(obj) == list:
            return [self.sanitizeForSerialization(subObj) for subObj in obj]
        elif type(obj) == datetime.datetime:
            return obj.isoformat()
        else:
            if type(obj) == dict:
                objDict = obj
            else:
                objDict = obj.__dict__
            return {key: self.sanitizeForSerialization(val)
                    for (key, val) in objDict.iteritems()
                    if key != 'swaggerTypes'}

        if type(postData) == list:
            # Could be a list of objects
            if type(postData[0]) in safeToDump:
                data = json.dumps(postData)
            else:
                data = json.dumps([datum.__dict__ for datum in postData])
        elif type(postData) not in safeToDump:
            data = json.dumps(postData.__dict__)

    def deserialize(self, obj, objClass):
        """Derialize a JSON string into an object.

        Args:
            obj -- string or object to be deserialized
            objClass -- class literal for deserialzied object, or string
                of class name
        Returns:
            object -- deserialized object"""

        # Have to accept objClass as string or actual type. Type could be a
        # native Python type, or one of the model classes.
        if type(objClass) == str:
            if 'list[' in objClass:
                match = re.match('list\[(.*)\]', objClass)
                subClass = match.group(1)
                return [self.deserialize(subObj, subClass) for subObj in obj]

            if (objClass in ['int', 'float', 'long', 'dict', 'list', 'str', 'bool', 'datetime']):
                objClass = eval(objClass)
            else:  # not a native type, must be model class
                objClass = eval(objClass + '.' + objClass)

        if objClass == str:
            return obj
        elif objClass in [int, long, float, dict, list, bool]:
            return objClass(obj)
        elif objClass == datetime:
            # Server will always return a time stamp in UTC, but with
            # trailing +0000 indicating no offset from UTC. So don't process
            # last 5 characters.
            return datetime.datetime.strptime(obj[:-5],
                                              "%Y-%m-%dT%H:%M:%S.%f")

        instance = objClass()

        for attr, attrType in instance.swaggerTypes.iteritems():
            if attr in obj:
                value = obj[attr]
                if attrType in ['str', 'int', 'long', 'float', 'bool']:
                    attrType = eval(attrType)
                    try:
                        value = attrType(value)
                    except UnicodeEncodeError:
                        value = unicode(value)
                    setattr(instance, attr, value)
                elif (attrType == 'datetime'):
                    setattr(instance, attr, datetime.datetime.strptime(value[:-5],
                                              "%Y-%m-%dT%H:%M:%S.%f"))
                elif 'list[' in attrType:
                    match = re.match('list\[(.*)\]', attrType)
                    subClass = match.group(1)
                    subValues = []
                    if not value:
                        setattr(instance, attr, None)
                    else:
                        for subValue in value:
                            subValues.append(self.deserialize(subValue,
                                                              subClass))
                    setattr(instance, attr, subValues)
                else:
                    setattr(instance, attr, self.deserialize(value,
                                                             objClass))

        return instance


class MethodRequest(urllib2.Request):

    def __init__(self, *args, **kwargs):
        """Construct a MethodRequest. Usage is the same as for
        `urllib2.Request` except it also takes an optional `method`
        keyword argument. If supplied, `method` will be used instead of
        the default."""

        if 'method' in kwargs:
            self.method = kwargs.pop('method')
        return urllib2.Request.__init__(self, *args, **kwargs)

    def get_method(self):
        return getattr(self, 'method', urllib2.Request.get_method(self))



########NEW FILE########
__FILENAME__ = WordApi
#!/usr/bin/env python
"""
WordAPI.py
Copyright 2012 Wordnik, Inc.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

NOTE: This class is auto generated by the swagger code generator program. Do not edit the class manually.
"""
import sys
import os

from models import *


class WordApi(object):

    def __init__(self, apiClient):
      self.apiClient = apiClient

    
    def getExamples(self, word, **kwargs):
        """Returns examples for a word

        Args:
            word, str: Word to return examples for (required)
            includeDuplicates, str: Show duplicate examples from different sources (optional)
            useCanonical, str: If true will try to return the correct word root ('cats' -&gt; 'cat'). If false returns exactly what was requested. (optional)
            skip, int: Results to skip (optional)
            limit, int: Maximum number of results to return (optional)
            
        Returns: ExampleSearchResults
        """

        allParams = ['word', 'includeDuplicates', 'useCanonical', 'skip', 'limit']

        params = locals()
        for (key, val) in params['kwargs'].iteritems():
            if key not in allParams:
                raise TypeError("Got an unexpected keyword argument '%s' to method getExamples" % key)
            params[key] = val
        del params['kwargs']

        resourcePath = '/word.{format}/{word}/examples'
        resourcePath = resourcePath.replace('{format}', 'json')
        method = 'GET'

        queryParams = {}
        headerParams = {}

        if ('includeDuplicates' in params):
            queryParams['includeDuplicates'] = self.apiClient.toPathValue(params['includeDuplicates'])
        if ('useCanonical' in params):
            queryParams['useCanonical'] = self.apiClient.toPathValue(params['useCanonical'])
        if ('skip' in params):
            queryParams['skip'] = self.apiClient.toPathValue(params['skip'])
        if ('limit' in params):
            queryParams['limit'] = self.apiClient.toPathValue(params['limit'])
        if ('word' in params):
            replacement = str(self.apiClient.toPathValue(params['word']))
            resourcePath = resourcePath.replace('{' + 'word' + '}',
                                                replacement)
        postData = (params['body'] if 'body' in params else None)

        response = self.apiClient.callAPI(resourcePath, method, queryParams,
                                          postData, headerParams)

        if not response:
            return None

        responseObject = self.apiClient.deserialize(response, 'ExampleSearchResults')
        return responseObject
        
        
    def getWord(self, word, **kwargs):
        """Given a word as a string, returns the WordObject that represents it

        Args:
            word, str: String value of WordObject to return (required)
            useCanonical, str: If true will try to return the correct word root ('cats' -&gt; 'cat'). If false returns exactly what was requested. (optional)
            includeSuggestions, str: Return suggestions (for correct spelling, case variants, etc.) (optional)
            
        Returns: WordObject
        """

        allParams = ['word', 'useCanonical', 'includeSuggestions']

        params = locals()
        for (key, val) in params['kwargs'].iteritems():
            if key not in allParams:
                raise TypeError("Got an unexpected keyword argument '%s' to method getWord" % key)
            params[key] = val
        del params['kwargs']

        resourcePath = '/word.{format}/{word}'
        resourcePath = resourcePath.replace('{format}', 'json')
        method = 'GET'

        queryParams = {}
        headerParams = {}

        if ('useCanonical' in params):
            queryParams['useCanonical'] = self.apiClient.toPathValue(params['useCanonical'])
        if ('includeSuggestions' in params):
            queryParams['includeSuggestions'] = self.apiClient.toPathValue(params['includeSuggestions'])
        if ('word' in params):
            replacement = str(self.apiClient.toPathValue(params['word']))
            resourcePath = resourcePath.replace('{' + 'word' + '}',
                                                replacement)
        postData = (params['body'] if 'body' in params else None)

        response = self.apiClient.callAPI(resourcePath, method, queryParams,
                                          postData, headerParams)

        if not response:
            return None

        responseObject = self.apiClient.deserialize(response, 'WordObject')
        return responseObject
        
        
    def getDefinitions(self, word, **kwargs):
        """Return definitions for a word

        Args:
            word, str: Word to return definitions for (required)
            partOfSpeech, str: CSV list of part-of-speech types (optional)
            sourceDictionaries, str: Source dictionary to return definitions from.  If 'all' is received, results are returned from all sources. If multiple values are received (e.g. 'century,wiktionary'), results are returned from the first specified dictionary that has definitions. If left blank, results are returned from the first dictionary that has definitions. By default, dictionaries are searched in this order: ahd, wiktionary, webster, century, wordnet (optional)
            limit, int: Maximum number of results to return (optional)
            includeRelated, str: Return related words with definitions (optional)
            useCanonical, str: If true will try to return the correct word root ('cats' -&gt; 'cat'). If false returns exactly what was requested. (optional)
            includeTags, str: Return a closed set of XML tags in response (optional)
            
        Returns: list[Definition]
        """

        allParams = ['word', 'partOfSpeech', 'sourceDictionaries', 'limit', 'includeRelated', 'useCanonical', 'includeTags']

        params = locals()
        for (key, val) in params['kwargs'].iteritems():
            if key not in allParams:
                raise TypeError("Got an unexpected keyword argument '%s' to method getDefinitions" % key)
            params[key] = val
        del params['kwargs']

        resourcePath = '/word.{format}/{word}/definitions'
        resourcePath = resourcePath.replace('{format}', 'json')
        method = 'GET'

        queryParams = {}
        headerParams = {}

        if ('limit' in params):
            queryParams['limit'] = self.apiClient.toPathValue(params['limit'])
        if ('partOfSpeech' in params):
            queryParams['partOfSpeech'] = self.apiClient.toPathValue(params['partOfSpeech'])
        if ('includeRelated' in params):
            queryParams['includeRelated'] = self.apiClient.toPathValue(params['includeRelated'])
        if ('sourceDictionaries' in params):
            queryParams['sourceDictionaries'] = self.apiClient.toPathValue(params['sourceDictionaries'])
        if ('useCanonical' in params):
            queryParams['useCanonical'] = self.apiClient.toPathValue(params['useCanonical'])
        if ('includeTags' in params):
            queryParams['includeTags'] = self.apiClient.toPathValue(params['includeTags'])
        if ('word' in params):
            replacement = self.apiClient.toPathValue(params['word']).encode('utf8')
            resourcePath = resourcePath.replace('{' + 'word' + '}',
                                                replacement)
        postData = (params['body'] if 'body' in params else None)

        response = self.apiClient.callAPI(resourcePath, method, queryParams,
                                          postData, headerParams)

        if not response:
            return None

        responseObject = self.apiClient.deserialize(response, 'list[Definition]')
        return responseObject
        
        
    def getTopExample(self, word, **kwargs):
        """Returns a top example for a word

        Args:
            word, str: Word to fetch examples for (required)
            useCanonical, str: If true will try to return the correct word root ('cats' -&gt; 'cat'). If false returns exactly what was requested. (optional)
            
        Returns: Example
        """

        allParams = ['word', 'useCanonical']

        params = locals()
        for (key, val) in params['kwargs'].iteritems():
            if key not in allParams:
                raise TypeError("Got an unexpected keyword argument '%s' to method getTopExample" % key)
            params[key] = val
        del params['kwargs']

        resourcePath = '/word.{format}/{word}/topExample'
        resourcePath = resourcePath.replace('{format}', 'json')
        method = 'GET'

        queryParams = {}
        headerParams = {}

        if ('useCanonical' in params):
            queryParams['useCanonical'] = self.apiClient.toPathValue(params['useCanonical'])
        if ('word' in params):
            replacement = str(self.apiClient.toPathValue(params['word']))
            resourcePath = resourcePath.replace('{' + 'word' + '}',
                                                replacement)
        postData = (params['body'] if 'body' in params else None)

        response = self.apiClient.callAPI(resourcePath, method, queryParams,
                                          postData, headerParams)

        if not response:
            return None

        responseObject = self.apiClient.deserialize(response, 'Example')
        return responseObject
        
        
    def getRelatedWords(self, word, **kwargs):
        """Given a word as a string, returns relationships from the Word Graph

        Args:
            word, str: Word to fetch relationships for (required)
            relationshipTypes, str: Limits the total results per type of relationship type (optional)
            useCanonical, str: If true will try to return the correct word root ('cats' -&gt; 'cat'). If false returns exactly what was requested. (optional)
            limitPerRelationshipType, int: Restrict to the supplied relatinship types (optional)
            
        Returns: list[Related]
        """

        allParams = ['word', 'relationshipTypes', 'useCanonical', 'limitPerRelationshipType']

        params = locals()
        for (key, val) in params['kwargs'].iteritems():
            if key not in allParams:
                raise TypeError("Got an unexpected keyword argument '%s' to method getRelatedWords" % key)
            params[key] = val
        del params['kwargs']

        resourcePath = '/word.{format}/{word}/relatedWords'
        resourcePath = resourcePath.replace('{format}', 'json')
        method = 'GET'

        queryParams = {}
        headerParams = {}

        if ('useCanonical' in params):
            queryParams['useCanonical'] = self.apiClient.toPathValue(params['useCanonical'])
        if ('relationshipTypes' in params):
            queryParams['relationshipTypes'] = self.apiClient.toPathValue(params['relationshipTypes'])
        if ('limitPerRelationshipType' in params):
            queryParams['limitPerRelationshipType'] = self.apiClient.toPathValue(params['limitPerRelationshipType'])
        if ('word' in params):
            replacement = str(self.apiClient.toPathValue(params['word']))
            resourcePath = resourcePath.replace('{' + 'word' + '}',
                                                replacement)
        postData = (params['body'] if 'body' in params else None)

        response = self.apiClient.callAPI(resourcePath, method, queryParams,
                                          postData, headerParams)

        if not response:
            return None

        responseObject = self.apiClient.deserialize(response, 'list[Related]')
        return responseObject
        
        
    def getTextPronunciations(self, word, **kwargs):
        """Returns text pronunciations for a given word

        Args:
            word, str: Word to get pronunciations for (required)
            sourceDictionary, str: Get from a single dictionary (optional)
            typeFormat, str: Text pronunciation type (optional)
            useCanonical, str: If true will try to return a correct word root ('cats' -&gt; 'cat'). If false returns exactly what was requested. (optional)
            limit, int: Maximum number of results to return (optional)
            
        Returns: list[TextPron]
        """

        allParams = ['word', 'sourceDictionary', 'typeFormat', 'useCanonical', 'limit']

        params = locals()
        for (key, val) in params['kwargs'].iteritems():
            if key not in allParams:
                raise TypeError("Got an unexpected keyword argument '%s' to method getTextPronunciations" % key)
            params[key] = val
        del params['kwargs']

        resourcePath = '/word.{format}/{word}/pronunciations'
        resourcePath = resourcePath.replace('{format}', 'json')
        method = 'GET'

        queryParams = {}
        headerParams = {}

        if ('useCanonical' in params):
            queryParams['useCanonical'] = self.apiClient.toPathValue(params['useCanonical'])
        if ('sourceDictionary' in params):
            queryParams['sourceDictionary'] = self.apiClient.toPathValue(params['sourceDictionary'])
        if ('typeFormat' in params):
            queryParams['typeFormat'] = self.apiClient.toPathValue(params['typeFormat'])
        if ('limit' in params):
            queryParams['limit'] = self.apiClient.toPathValue(params['limit'])
        if ('word' in params):
            replacement = str(self.apiClient.toPathValue(params['word']))
            resourcePath = resourcePath.replace('{' + 'word' + '}',
                                                replacement)
        postData = (params['body'] if 'body' in params else None)

        response = self.apiClient.callAPI(resourcePath, method, queryParams,
                                          postData, headerParams)

        if not response:
            return None

        responseObject = self.apiClient.deserialize(response, 'list[TextPron]')
        return responseObject
        
        
    def getHyphenation(self, word, **kwargs):
        """Returns syllable information for a word

        Args:
            word, str: Word to get syllables for (required)
            sourceDictionary, str: Get from a single dictionary. Valid options: ahd, century, wiktionary, webster, and wordnet. (optional)
            useCanonical, str: If true will try to return a correct word root ('cats' -&gt; 'cat'). If false returns exactly what was requested. (optional)
            limit, int: Maximum number of results to return (optional)
            
        Returns: list[Syllable]
        """

        allParams = ['word', 'sourceDictionary', 'useCanonical', 'limit']

        params = locals()
        for (key, val) in params['kwargs'].iteritems():
            if key not in allParams:
                raise TypeError("Got an unexpected keyword argument '%s' to method getHyphenation" % key)
            params[key] = val
        del params['kwargs']

        resourcePath = '/word.{format}/{word}/hyphenation'
        resourcePath = resourcePath.replace('{format}', 'json')
        method = 'GET'

        queryParams = {}
        headerParams = {}

        if ('useCanonical' in params):
            queryParams['useCanonical'] = self.apiClient.toPathValue(params['useCanonical'])
        if ('sourceDictionary' in params):
            queryParams['sourceDictionary'] = self.apiClient.toPathValue(params['sourceDictionary'])
        if ('limit' in params):
            queryParams['limit'] = self.apiClient.toPathValue(params['limit'])
        if ('word' in params):
            replacement = str(self.apiClient.toPathValue(params['word']))
            resourcePath = resourcePath.replace('{' + 'word' + '}',
                                                replacement)
        postData = (params['body'] if 'body' in params else None)

        response = self.apiClient.callAPI(resourcePath, method, queryParams,
                                          postData, headerParams)

        if not response:
            return None

        responseObject = self.apiClient.deserialize(response, 'list[Syllable]')
        return responseObject
        
        
    def getWordFrequency(self, word, **kwargs):
        """Returns word usage over time

        Args:
            word, str: Word to return (required)
            useCanonical, str: If true will try to return the correct word root ('cats' -&gt; 'cat'). If false returns exactly what was requested. (optional)
            startYear, int: Starting Year (optional)
            endYear, int: Ending Year (optional)
            
        Returns: FrequencySummary
        """

        allParams = ['word', 'useCanonical', 'startYear', 'endYear']

        params = locals()
        for (key, val) in params['kwargs'].iteritems():
            if key not in allParams:
                raise TypeError("Got an unexpected keyword argument '%s' to method getWordFrequency" % key)
            params[key] = val
        del params['kwargs']

        resourcePath = '/word.{format}/{word}/frequency'
        resourcePath = resourcePath.replace('{format}', 'json')
        method = 'GET'

        queryParams = {}
        headerParams = {}

        if ('useCanonical' in params):
            queryParams['useCanonical'] = self.apiClient.toPathValue(params['useCanonical'])
        if ('startYear' in params):
            queryParams['startYear'] = self.apiClient.toPathValue(params['startYear'])
        if ('endYear' in params):
            queryParams['endYear'] = self.apiClient.toPathValue(params['endYear'])
        if ('word' in params):
            replacement = str(self.apiClient.toPathValue(params['word']))
            resourcePath = resourcePath.replace('{' + 'word' + '}',
                                                replacement)
        postData = (params['body'] if 'body' in params else None)

        response = self.apiClient.callAPI(resourcePath, method, queryParams,
                                          postData, headerParams)

        if not response:
            return None

        responseObject = self.apiClient.deserialize(response, 'FrequencySummary')
        return responseObject
        
        
    def getPhrases(self, word, **kwargs):
        """Fetches bi-gram phrases for a word

        Args:
            word, str: Word to fetch phrases for (required)
            limit, int: Maximum number of results to return (optional)
            wlmi, int: Minimum WLMI for the phrase (optional)
            useCanonical, str: If true will try to return the correct word root ('cats' -&gt; 'cat'). If false returns exactly what was requested. (optional)
            
        Returns: list[Bigram]
        """

        allParams = ['word', 'limit', 'wlmi', 'useCanonical']

        params = locals()
        for (key, val) in params['kwargs'].iteritems():
            if key not in allParams:
                raise TypeError("Got an unexpected keyword argument '%s' to method getPhrases" % key)
            params[key] = val
        del params['kwargs']

        resourcePath = '/word.{format}/{word}/phrases'
        resourcePath = resourcePath.replace('{format}', 'json')
        method = 'GET'

        queryParams = {}
        headerParams = {}

        if ('limit' in params):
            queryParams['limit'] = self.apiClient.toPathValue(params['limit'])
        if ('wlmi' in params):
            queryParams['wlmi'] = self.apiClient.toPathValue(params['wlmi'])
        if ('useCanonical' in params):
            queryParams['useCanonical'] = self.apiClient.toPathValue(params['useCanonical'])
        if ('word' in params):
            replacement = str(self.apiClient.toPathValue(params['word']))
            resourcePath = resourcePath.replace('{' + 'word' + '}',
                                                replacement)
        postData = (params['body'] if 'body' in params else None)

        response = self.apiClient.callAPI(resourcePath, method, queryParams,
                                          postData, headerParams)

        if not response:
            return None

        responseObject = self.apiClient.deserialize(response, 'list[Bigram]')
        return responseObject
        
        
    def getEtymologies(self, word, **kwargs):
        """Fetches etymology data

        Args:
            word, str: Word to return (required)
            useCanonical, str: If true will try to return the correct word root ('cats' -&gt; 'cat'). If false returns exactly what was requested. (optional)
            
        Returns: list[str]
        """

        allParams = ['word', 'useCanonical']

        params = locals()
        for (key, val) in params['kwargs'].iteritems():
            if key not in allParams:
                raise TypeError("Got an unexpected keyword argument '%s' to method getEtymologies" % key)
            params[key] = val
        del params['kwargs']

        resourcePath = '/word.{format}/{word}/etymologies'
        resourcePath = resourcePath.replace('{format}', 'json')
        method = 'GET'

        queryParams = {}
        headerParams = {}

        if ('useCanonical' in params):
            queryParams['useCanonical'] = self.apiClient.toPathValue(params['useCanonical'])
        if ('word' in params):
            replacement = str(self.apiClient.toPathValue(params['word']))
            resourcePath = resourcePath.replace('{' + 'word' + '}',
                                                replacement)
        postData = (params['body'] if 'body' in params else None)

        response = self.apiClient.callAPI(resourcePath, method, queryParams,
                                          postData, headerParams)

        if not response:
            return None

        responseObject = self.apiClient.deserialize(response, 'list[str]')
        return responseObject
        
        
    def getAudio(self, word, **kwargs):
        """Fetches audio metadata for a word.

        Args:
            word, str: Word to get audio for. (required)
            useCanonical, str: Use the canonical form of the word (optional)
            limit, int: Maximum number of results to return (optional)
            
        Returns: list[AudioFile]
        """

        allParams = ['word', 'useCanonical', 'limit']

        params = locals()
        for (key, val) in params['kwargs'].iteritems():
            if key not in allParams:
                raise TypeError("Got an unexpected keyword argument '%s' to method getAudio" % key)
            params[key] = val
        del params['kwargs']

        resourcePath = '/word.{format}/{word}/audio'
        resourcePath = resourcePath.replace('{format}', 'json')
        method = 'GET'

        queryParams = {}
        headerParams = {}

        if ('useCanonical' in params):
            queryParams['useCanonical'] = self.apiClient.toPathValue(params['useCanonical'])
        if ('limit' in params):
            queryParams['limit'] = self.apiClient.toPathValue(params['limit'])
        if ('word' in params):
            replacement = str(self.apiClient.toPathValue(params['word']))
            resourcePath = resourcePath.replace('{' + 'word' + '}',
                                                replacement)
        postData = (params['body'] if 'body' in params else None)

        response = self.apiClient.callAPI(resourcePath, method, queryParams,
                                          postData, headerParams)

        if not response:
            return None

        responseObject = self.apiClient.deserialize(response, 'list[AudioFile]')
        return responseObject
        
        
    def getScrabbleScore(self, word, **kwargs):
        """Returns the Scrabble score for a word

        Args:
            word, str: Word to get scrabble score for. (required)
            
        Returns: ScrabbleScoreResult
        """

        allParams = ['word']

        params = locals()
        for (key, val) in params['kwargs'].iteritems():
            if key not in allParams:
                raise TypeError("Got an unexpected keyword argument '%s' to method getScrabbleScore" % key)
            params[key] = val
        del params['kwargs']

        resourcePath = '/word.{format}/{word}/scrabbleScore'
        resourcePath = resourcePath.replace('{format}', 'json')
        method = 'GET'

        queryParams = {}
        headerParams = {}

        if ('word' in params):
            replacement = str(self.apiClient.toPathValue(params['word']))
            resourcePath = resourcePath.replace('{' + 'word' + '}',
                                                replacement)
        postData = (params['body'] if 'body' in params else None)

        response = self.apiClient.callAPI(resourcePath, method, queryParams,
                                          postData, headerParams)

        if not response:
            return None

        responseObject = self.apiClient.deserialize(response, 'ScrabbleScoreResult')
        return responseObject
        
        
    



########NEW FILE########
__FILENAME__ = WordListApi
#!/usr/bin/env python
"""
WordAPI.py
Copyright 2012 Wordnik, Inc.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

NOTE: This class is auto generated by the swagger code generator program. Do not edit the class manually.
"""
import sys
import os

from models import *


class WordListApi(object):

    def __init__(self, apiClient):
      self.apiClient = apiClient

    
    def updateWordList(self, permalink, auth_token, **kwargs):
        """Updates an existing WordList

        Args:
            permalink, str: permalink of WordList to update (required)
            body, WordList: Updated WordList (optional)
            auth_token, str: The auth token of the logged-in user, obtained by calling /account.{format}/authenticate/{username} (described above) (required)
            
        Returns: 
        """

        allParams = ['permalink', 'body', 'auth_token']

        params = locals()
        for (key, val) in params['kwargs'].iteritems():
            if key not in allParams:
                raise TypeError("Got an unexpected keyword argument '%s' to method updateWordList" % key)
            params[key] = val
        del params['kwargs']

        resourcePath = '/wordList.{format}/{permalink}'
        resourcePath = resourcePath.replace('{format}', 'json')
        method = 'PUT'

        queryParams = {}
        headerParams = {}

        if ('auth_token' in params):
            headerParams['auth_token'] = params['auth_token']
        if ('permalink' in params):
            replacement = str(self.apiClient.toPathValue(params['permalink']))
            resourcePath = resourcePath.replace('{' + 'permalink' + '}',
                                                replacement)
        postData = (params['body'] if 'body' in params else None)

        response = self.apiClient.callAPI(resourcePath, method, queryParams,
                                          postData, headerParams)

        
        
    def deleteWordList(self, permalink, auth_token, **kwargs):
        """Deletes an existing WordList

        Args:
            permalink, str: ID of WordList to delete (required)
            auth_token, str: The auth token of the logged-in user, obtained by calling /account.{format}/authenticate/{username} (described above) (required)
            
        Returns: 
        """

        allParams = ['permalink', 'auth_token']

        params = locals()
        for (key, val) in params['kwargs'].iteritems():
            if key not in allParams:
                raise TypeError("Got an unexpected keyword argument '%s' to method deleteWordList" % key)
            params[key] = val
        del params['kwargs']

        resourcePath = '/wordList.{format}/{permalink}'
        resourcePath = resourcePath.replace('{format}', 'json')
        method = 'DELETE'

        queryParams = {}
        headerParams = {}

        if ('auth_token' in params):
            headerParams['auth_token'] = params['auth_token']
        if ('permalink' in params):
            replacement = str(self.apiClient.toPathValue(params['permalink']))
            resourcePath = resourcePath.replace('{' + 'permalink' + '}',
                                                replacement)
        postData = (params['body'] if 'body' in params else None)

        response = self.apiClient.callAPI(resourcePath, method, queryParams,
                                          postData, headerParams)

        
        
    def getWordListByPermalink(self, permalink, auth_token, **kwargs):
        """Fetches a WordList by ID

        Args:
            permalink, str: permalink of WordList to fetch (required)
            auth_token, str: The auth token of the logged-in user, obtained by calling /account.{format}/authenticate/{username} (described above) (required)
            
        Returns: WordList
        """

        allParams = ['permalink', 'auth_token']

        params = locals()
        for (key, val) in params['kwargs'].iteritems():
            if key not in allParams:
                raise TypeError("Got an unexpected keyword argument '%s' to method getWordListByPermalink" % key)
            params[key] = val
        del params['kwargs']

        resourcePath = '/wordList.{format}/{permalink}'
        resourcePath = resourcePath.replace('{format}', 'json')
        method = 'GET'

        queryParams = {}
        headerParams = {}

        if ('auth_token' in params):
            headerParams['auth_token'] = params['auth_token']
        if ('permalink' in params):
            replacement = str(self.apiClient.toPathValue(params['permalink']))
            resourcePath = resourcePath.replace('{' + 'permalink' + '}',
                                                replacement)
        postData = (params['body'] if 'body' in params else None)

        response = self.apiClient.callAPI(resourcePath, method, queryParams,
                                          postData, headerParams)

        if not response:
            return None

        responseObject = self.apiClient.deserialize(response, 'WordList')
        return responseObject
        
        
    def addWordsToWordList(self, permalink, auth_token, **kwargs):
        """Adds words to a WordList

        Args:
            permalink, str: permalink of WordList to user (required)
            body, list[StringValue]: Array of words to add to WordList (optional)
            auth_token, str: The auth token of the logged-in user, obtained by calling /account.{format}/authenticate/{username} (described above) (required)
            
        Returns: 
        """

        allParams = ['permalink', 'body', 'auth_token']

        params = locals()
        for (key, val) in params['kwargs'].iteritems():
            if key not in allParams:
                raise TypeError("Got an unexpected keyword argument '%s' to method addWordsToWordList" % key)
            params[key] = val
        del params['kwargs']

        resourcePath = '/wordList.{format}/{permalink}/words'
        resourcePath = resourcePath.replace('{format}', 'json')
        method = 'POST'

        queryParams = {}
        headerParams = {}

        if ('auth_token' in params):
            headerParams['auth_token'] = params['auth_token']
        if ('permalink' in params):
            replacement = str(self.apiClient.toPathValue(params['permalink']))
            resourcePath = resourcePath.replace('{' + 'permalink' + '}',
                                                replacement)
        postData = (params['body'] if 'body' in params else None)

        response = self.apiClient.callAPI(resourcePath, method, queryParams,
                                          postData, headerParams)

        
        
    def getWordListWords(self, permalink, auth_token, **kwargs):
        """Fetches words in a WordList

        Args:
            permalink, str: ID of WordList to use (required)
            auth_token, str: The auth token of the logged-in user, obtained by calling /account.{format}/authenticate/{username} (described above) (required)
            sortBy, str: Field to sort by (optional)
            sortOrder, str: Direction to sort (optional)
            skip, int: Results to skip (optional)
            limit, int: Maximum number of results to return (optional)
            
        Returns: list[WordListWord]
        """

        allParams = ['permalink', 'auth_token', 'sortBy', 'sortOrder', 'skip', 'limit']

        params = locals()
        for (key, val) in params['kwargs'].iteritems():
            if key not in allParams:
                raise TypeError("Got an unexpected keyword argument '%s' to method getWordListWords" % key)
            params[key] = val
        del params['kwargs']

        resourcePath = '/wordList.{format}/{permalink}/words'
        resourcePath = resourcePath.replace('{format}', 'json')
        method = 'GET'

        queryParams = {}
        headerParams = {}

        if ('sortBy' in params):
            queryParams['sortBy'] = self.apiClient.toPathValue(params['sortBy'])
        if ('sortOrder' in params):
            queryParams['sortOrder'] = self.apiClient.toPathValue(params['sortOrder'])
        if ('skip' in params):
            queryParams['skip'] = self.apiClient.toPathValue(params['skip'])
        if ('limit' in params):
            queryParams['limit'] = self.apiClient.toPathValue(params['limit'])
        if ('auth_token' in params):
            headerParams['auth_token'] = params['auth_token']
        if ('permalink' in params):
            replacement = str(self.apiClient.toPathValue(params['permalink']))
            resourcePath = resourcePath.replace('{' + 'permalink' + '}',
                                                replacement)
        postData = (params['body'] if 'body' in params else None)

        response = self.apiClient.callAPI(resourcePath, method, queryParams,
                                          postData, headerParams)

        if not response:
            return None

        responseObject = self.apiClient.deserialize(response, 'list[WordListWord]')
        return responseObject
        
        
    def deleteWordsFromWordList(self, permalink, auth_token, **kwargs):
        """Removes words from a WordList

        Args:
            permalink, str: permalink of WordList to use (required)
            body, list[StringValue]: Words to remove from WordList (optional)
            auth_token, str: The auth token of the logged-in user, obtained by calling /account.{format}/authenticate/{username} (described above) (required)
            
        Returns: 
        """

        allParams = ['permalink', 'body', 'auth_token']

        params = locals()
        for (key, val) in params['kwargs'].iteritems():
            if key not in allParams:
                raise TypeError("Got an unexpected keyword argument '%s' to method deleteWordsFromWordList" % key)
            params[key] = val
        del params['kwargs']

        resourcePath = '/wordList.{format}/{permalink}/deleteWords'
        resourcePath = resourcePath.replace('{format}', 'json')
        method = 'POST'

        queryParams = {}
        headerParams = {}

        if ('auth_token' in params):
            headerParams['auth_token'] = params['auth_token']
        if ('permalink' in params):
            replacement = str(self.apiClient.toPathValue(params['permalink']))
            resourcePath = resourcePath.replace('{' + 'permalink' + '}',
                                                replacement)
        postData = (params['body'] if 'body' in params else None)

        response = self.apiClient.callAPI(resourcePath, method, queryParams,
                                          postData, headerParams)

        
        
    



########NEW FILE########
__FILENAME__ = WordListsApi
#!/usr/bin/env python
"""
WordAPI.py
Copyright 2012 Wordnik, Inc.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

NOTE: This class is auto generated by the swagger code generator program. Do not edit the class manually.
"""
import sys
import os

from models import *


class WordListsApi(object):

    def __init__(self, apiClient):
      self.apiClient = apiClient

    
    def createWordList(self, auth_token, **kwargs):
        """Creates a WordList.

        Args:
            body, WordList: WordList to create (optional)
            auth_token, str: The auth token of the logged-in user, obtained by calling /account.{format}/authenticate/{username} (described above) (required)
            
        Returns: WordList
        """

        allParams = ['body', 'auth_token']

        params = locals()
        for (key, val) in params['kwargs'].iteritems():
            if key not in allParams:
                raise TypeError("Got an unexpected keyword argument '%s' to method createWordList" % key)
            params[key] = val
        del params['kwargs']

        resourcePath = '/wordLists.{format}'
        resourcePath = resourcePath.replace('{format}', 'json')
        method = 'POST'

        queryParams = {}
        headerParams = {}

        if ('auth_token' in params):
            headerParams['auth_token'] = params['auth_token']
        postData = (params['body'] if 'body' in params else None)

        response = self.apiClient.callAPI(resourcePath, method, queryParams,
                                          postData, headerParams)

        if not response:
            return None

        responseObject = self.apiClient.deserialize(response, 'WordList')
        return responseObject
        
        
    



########NEW FILE########
__FILENAME__ = WordsApi
#!/usr/bin/env python
"""
WordAPI.py
Copyright 2012 Wordnik, Inc.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

NOTE: This class is auto generated by the swagger code generator program. Do not edit the class manually.
"""
import sys
import os

from models import *


class WordsApi(object):

    def __init__(self, apiClient):
      self.apiClient = apiClient

    
    def searchWords(self, query, **kwargs):
        """Searches words

        Args:
            query, str: Search query (required)
            includePartOfSpeech, str: Only include these comma-delimited parts of speech (optional)
            excludePartOfSpeech, str: Exclude these comma-delimited parts of speech (optional)
            caseSensitive, str: Search case sensitive (optional)
            minCorpusCount, int: Minimum corpus frequency for terms (optional)
            maxCorpusCount, int: Maximum corpus frequency for terms (optional)
            minDictionaryCount, int: Minimum number of dictionary entries for words returned (optional)
            maxDictionaryCount, int: Maximum dictionary definition count (optional)
            minLength, int: Minimum word length (optional)
            maxLength, int: Maximum word length (optional)
            skip, int: Results to skip (optional)
            limit, int: Maximum number of results to return (optional)
            
        Returns: WordSearchResults
        """

        allParams = ['query', 'includePartOfSpeech', 'excludePartOfSpeech', 'caseSensitive', 'minCorpusCount', 'maxCorpusCount', 'minDictionaryCount', 'maxDictionaryCount', 'minLength', 'maxLength', 'skip', 'limit']

        params = locals()
        for (key, val) in params['kwargs'].iteritems():
            if key not in allParams:
                raise TypeError("Got an unexpected keyword argument '%s' to method searchWords" % key)
            params[key] = val
        del params['kwargs']

        resourcePath = '/words.{format}/search/{query}'
        resourcePath = resourcePath.replace('{format}', 'json')
        method = 'GET'

        queryParams = {}
        headerParams = {}

        if ('caseSensitive' in params):
            queryParams['caseSensitive'] = self.apiClient.toPathValue(params['caseSensitive'])
        if ('includePartOfSpeech' in params):
            queryParams['includePartOfSpeech'] = self.apiClient.toPathValue(params['includePartOfSpeech'])
        if ('excludePartOfSpeech' in params):
            queryParams['excludePartOfSpeech'] = self.apiClient.toPathValue(params['excludePartOfSpeech'])
        if ('minCorpusCount' in params):
            queryParams['minCorpusCount'] = self.apiClient.toPathValue(params['minCorpusCount'])
        if ('maxCorpusCount' in params):
            queryParams['maxCorpusCount'] = self.apiClient.toPathValue(params['maxCorpusCount'])
        if ('minDictionaryCount' in params):
            queryParams['minDictionaryCount'] = self.apiClient.toPathValue(params['minDictionaryCount'])
        if ('maxDictionaryCount' in params):
            queryParams['maxDictionaryCount'] = self.apiClient.toPathValue(params['maxDictionaryCount'])
        if ('minLength' in params):
            queryParams['minLength'] = self.apiClient.toPathValue(params['minLength'])
        if ('maxLength' in params):
            queryParams['maxLength'] = self.apiClient.toPathValue(params['maxLength'])
        if ('skip' in params):
            queryParams['skip'] = self.apiClient.toPathValue(params['skip'])
        if ('limit' in params):
            queryParams['limit'] = self.apiClient.toPathValue(params['limit'])
        if ('query' in params):
            replacement = str(self.apiClient.toPathValue(params['query']))
            resourcePath = resourcePath.replace('{' + 'query' + '}',
                                                replacement)
        postData = (params['body'] if 'body' in params else None)

        response = self.apiClient.callAPI(resourcePath, method, queryParams,
                                          postData, headerParams)

        if not response:
            return None

        responseObject = self.apiClient.deserialize(response, 'WordSearchResults')
        return responseObject
        
        
    def getWordOfTheDay(self, **kwargs):
        """Returns a specific WordOfTheDay

        Args:
            date, str: Fetches by date in yyyy-MM-dd (optional)
            
        Returns: WordOfTheDay
        """

        allParams = ['date']

        params = locals()
        for (key, val) in params['kwargs'].iteritems():
            if key not in allParams:
                raise TypeError("Got an unexpected keyword argument '%s' to method getWordOfTheDay" % key)
            params[key] = val
        del params['kwargs']

        resourcePath = '/words.{format}/wordOfTheDay'
        resourcePath = resourcePath.replace('{format}', 'json')
        method = 'GET'

        queryParams = {}
        headerParams = {}

        if ('date' in params):
            queryParams['date'] = self.apiClient.toPathValue(params['date'])
        postData = (params['body'] if 'body' in params else None)

        response = self.apiClient.callAPI(resourcePath, method, queryParams,
                                          postData, headerParams)

        if not response:
            return None

        responseObject = self.apiClient.deserialize(response, 'WordOfTheDay')
        return responseObject
        
        
    def reverseDictionary(self, query, **kwargs):
        """Reverse dictionary search

        Args:
            query, str: Search term (required)
            findSenseForWord, str: Restricts words and finds closest sense (optional)
            includeSourceDictionaries, str: Only include these comma-delimited source dictionaries (optional)
            excludeSourceDictionaries, str: Exclude these comma-delimited source dictionaries (optional)
            includePartOfSpeech, str: Only include these comma-delimited parts of speech (optional)
            excludePartOfSpeech, str: Exclude these comma-delimited parts of speech (optional)
            expandTerms, str: Expand terms (optional)
            sortBy, str: Attribute to sort by (optional)
            sortOrder, str: Sort direction (optional)
            minCorpusCount, int: Minimum corpus frequency for terms (optional)
            maxCorpusCount, int: Maximum corpus frequency for terms (optional)
            minLength, int: Minimum word length (optional)
            maxLength, int: Maximum word length (optional)
            includeTags, str: Return a closed set of XML tags in response (optional)
            skip, str: Results to skip (optional)
            limit, int: Maximum number of results to return (optional)
            
        Returns: DefinitionSearchResults
        """

        allParams = ['query', 'findSenseForWord', 'includeSourceDictionaries', 'excludeSourceDictionaries', 'includePartOfSpeech', 'excludePartOfSpeech', 'expandTerms', 'sortBy', 'sortOrder', 'minCorpusCount', 'maxCorpusCount', 'minLength', 'maxLength', 'includeTags', 'skip', 'limit']

        params = locals()
        for (key, val) in params['kwargs'].iteritems():
            if key not in allParams:
                raise TypeError("Got an unexpected keyword argument '%s' to method reverseDictionary" % key)
            params[key] = val
        del params['kwargs']

        resourcePath = '/words.{format}/reverseDictionary'
        resourcePath = resourcePath.replace('{format}', 'json')
        method = 'GET'

        queryParams = {}
        headerParams = {}

        if ('query' in params):
            queryParams['query'] = self.apiClient.toPathValue(params['query'])
        if ('findSenseForWord' in params):
            queryParams['findSenseForWord'] = self.apiClient.toPathValue(params['findSenseForWord'])
        if ('includeSourceDictionaries' in params):
            queryParams['includeSourceDictionaries'] = self.apiClient.toPathValue(params['includeSourceDictionaries'])
        if ('excludeSourceDictionaries' in params):
            queryParams['excludeSourceDictionaries'] = self.apiClient.toPathValue(params['excludeSourceDictionaries'])
        if ('includePartOfSpeech' in params):
            queryParams['includePartOfSpeech'] = self.apiClient.toPathValue(params['includePartOfSpeech'])
        if ('excludePartOfSpeech' in params):
            queryParams['excludePartOfSpeech'] = self.apiClient.toPathValue(params['excludePartOfSpeech'])
        if ('minCorpusCount' in params):
            queryParams['minCorpusCount'] = self.apiClient.toPathValue(params['minCorpusCount'])
        if ('maxCorpusCount' in params):
            queryParams['maxCorpusCount'] = self.apiClient.toPathValue(params['maxCorpusCount'])
        if ('minLength' in params):
            queryParams['minLength'] = self.apiClient.toPathValue(params['minLength'])
        if ('maxLength' in params):
            queryParams['maxLength'] = self.apiClient.toPathValue(params['maxLength'])
        if ('expandTerms' in params):
            queryParams['expandTerms'] = self.apiClient.toPathValue(params['expandTerms'])
        if ('includeTags' in params):
            queryParams['includeTags'] = self.apiClient.toPathValue(params['includeTags'])
        if ('sortBy' in params):
            queryParams['sortBy'] = self.apiClient.toPathValue(params['sortBy'])
        if ('sortOrder' in params):
            queryParams['sortOrder'] = self.apiClient.toPathValue(params['sortOrder'])
        if ('skip' in params):
            queryParams['skip'] = self.apiClient.toPathValue(params['skip'])
        if ('limit' in params):
            queryParams['limit'] = self.apiClient.toPathValue(params['limit'])
        postData = (params['body'] if 'body' in params else None)

        response = self.apiClient.callAPI(resourcePath, method, queryParams,
                                          postData, headerParams)

        if not response:
            return None

        responseObject = self.apiClient.deserialize(response, 'DefinitionSearchResults')
        return responseObject
        
        
    def getRandomWords(self, **kwargs):
        """Returns an array of random WordObjects

        Args:
            includePartOfSpeech, str: CSV part-of-speech values to include (optional)
            excludePartOfSpeech, str: CSV part-of-speech values to exclude (optional)
            sortBy, str: Attribute to sort by (optional)
            sortOrder, str: Sort direction (optional)
            hasDictionaryDef, str: Only return words with dictionary definitions (optional)
            minCorpusCount, int: Minimum corpus frequency for terms (optional)
            maxCorpusCount, int: Maximum corpus frequency for terms (optional)
            minDictionaryCount, int: Minimum dictionary count (optional)
            maxDictionaryCount, int: Maximum dictionary count (optional)
            minLength, int: Minimum word length (optional)
            maxLength, int: Maximum word length (optional)
            limit, int: Maximum number of results to return (optional)
            
        Returns: list[WordObject]
        """

        allParams = ['includePartOfSpeech', 'excludePartOfSpeech', 'sortBy', 'sortOrder', 'hasDictionaryDef', 'minCorpusCount', 'maxCorpusCount', 'minDictionaryCount', 'maxDictionaryCount', 'minLength', 'maxLength', 'limit']

        params = locals()
        for (key, val) in params['kwargs'].iteritems():
            if key not in allParams:
                raise TypeError("Got an unexpected keyword argument '%s' to method getRandomWords" % key)
            params[key] = val
        del params['kwargs']

        resourcePath = '/words.{format}/randomWords'
        resourcePath = resourcePath.replace('{format}', 'json')
        method = 'GET'

        queryParams = {}
        headerParams = {}

        if ('hasDictionaryDef' in params):
            queryParams['hasDictionaryDef'] = self.apiClient.toPathValue(params['hasDictionaryDef'])
        if ('includePartOfSpeech' in params):
            queryParams['includePartOfSpeech'] = self.apiClient.toPathValue(params['includePartOfSpeech'])
        if ('excludePartOfSpeech' in params):
            queryParams['excludePartOfSpeech'] = self.apiClient.toPathValue(params['excludePartOfSpeech'])
        if ('minCorpusCount' in params):
            queryParams['minCorpusCount'] = self.apiClient.toPathValue(params['minCorpusCount'])
        if ('maxCorpusCount' in params):
            queryParams['maxCorpusCount'] = self.apiClient.toPathValue(params['maxCorpusCount'])
        if ('minDictionaryCount' in params):
            queryParams['minDictionaryCount'] = self.apiClient.toPathValue(params['minDictionaryCount'])
        if ('maxDictionaryCount' in params):
            queryParams['maxDictionaryCount'] = self.apiClient.toPathValue(params['maxDictionaryCount'])
        if ('minLength' in params):
            queryParams['minLength'] = self.apiClient.toPathValue(params['minLength'])
        if ('maxLength' in params):
            queryParams['maxLength'] = self.apiClient.toPathValue(params['maxLength'])
        if ('sortBy' in params):
            queryParams['sortBy'] = self.apiClient.toPathValue(params['sortBy'])
        if ('sortOrder' in params):
            queryParams['sortOrder'] = self.apiClient.toPathValue(params['sortOrder'])
        if ('limit' in params):
            queryParams['limit'] = self.apiClient.toPathValue(params['limit'])
        postData = (params['body'] if 'body' in params else None)

        response = self.apiClient.callAPI(resourcePath, method, queryParams,
                                          postData, headerParams)

        if not response:
            return None

        responseObject = self.apiClient.deserialize(response, 'list[WordObject]')
        return responseObject
        
        
    def getRandomWord(self, **kwargs):
        """Returns a single random WordObject

        Args:
            includePartOfSpeech, str: CSV part-of-speech values to include (optional)
            excludePartOfSpeech, str: CSV part-of-speech values to exclude (optional)
            hasDictionaryDef, str: Only return words with dictionary definitions (optional)
            minCorpusCount, int: Minimum corpus frequency for terms (optional)
            maxCorpusCount, int: Maximum corpus frequency for terms (optional)
            minDictionaryCount, int: Minimum dictionary count (optional)
            maxDictionaryCount, int: Maximum dictionary count (optional)
            minLength, int: Minimum word length (optional)
            maxLength, int: Maximum word length (optional)
            
        Returns: WordObject
        """

        allParams = ['includePartOfSpeech', 'excludePartOfSpeech', 'hasDictionaryDef', 'minCorpusCount', 'maxCorpusCount', 'minDictionaryCount', 'maxDictionaryCount', 'minLength', 'maxLength']

        params = locals()
        for (key, val) in params['kwargs'].iteritems():
            if key not in allParams:
                raise TypeError("Got an unexpected keyword argument '%s' to method getRandomWord" % key)
            params[key] = val
        del params['kwargs']

        resourcePath = '/words.{format}/randomWord'
        resourcePath = resourcePath.replace('{format}', 'json')
        method = 'GET'

        queryParams = {}
        headerParams = {}

        if ('hasDictionaryDef' in params):
            queryParams['hasDictionaryDef'] = self.apiClient.toPathValue(params['hasDictionaryDef'])
        if ('includePartOfSpeech' in params):
            queryParams['includePartOfSpeech'] = self.apiClient.toPathValue(params['includePartOfSpeech'])
        if ('excludePartOfSpeech' in params):
            queryParams['excludePartOfSpeech'] = self.apiClient.toPathValue(params['excludePartOfSpeech'])
        if ('minCorpusCount' in params):
            queryParams['minCorpusCount'] = self.apiClient.toPathValue(params['minCorpusCount'])
        if ('maxCorpusCount' in params):
            queryParams['maxCorpusCount'] = self.apiClient.toPathValue(params['maxCorpusCount'])
        if ('minDictionaryCount' in params):
            queryParams['minDictionaryCount'] = self.apiClient.toPathValue(params['minDictionaryCount'])
        if ('maxDictionaryCount' in params):
            queryParams['maxDictionaryCount'] = self.apiClient.toPathValue(params['maxDictionaryCount'])
        if ('minLength' in params):
            queryParams['minLength'] = self.apiClient.toPathValue(params['minLength'])
        if ('maxLength' in params):
            queryParams['maxLength'] = self.apiClient.toPathValue(params['maxLength'])
        postData = (params['body'] if 'body' in params else None)

        response = self.apiClient.callAPI(resourcePath, method, queryParams,
                                          postData, headerParams)

        if not response:
            return None

        responseObject = self.apiClient.deserialize(response, 'WordObject')
        return responseObject
        
        
    



########NEW FILE########
