__FILENAME__ = tests
'''
Created on 9 Nov 2012

@author: plish
'''

import unittest
import uuid

from trolly.client import Client
from trolly.organisation import Organisation
from trolly.board import Board
from trolly.list import List
from trolly.card import Card
from trolly.checklist import Checklist
from trolly.member import Member
from trolly import ResourceUnavailable


api_key = ''
user_auth_token = ''

organisation = ''
board_id = ''
list_id = ''
card_id = ''
checklist_id = ''
member_id = ''


class TrelloTests( unittest.TestCase ):

    def setUp( self ):
        self.client = Client( api_key, user_auth_token )
        self.org = Organisation( self.client, organisation )
        self.board = Board( self.client, board_id )
        self.list = List( self.client, list_id )
        self.card = Card( self.client, card_id )
        self.checklist = Checklist( self.client, checklist_id )
        self.member = Member( self.client, member_id )


    def tearDown( self ):
        pass


    def test_org_01_getBoardInfo( self ):
        result = self.org.getOrganisationInformation()
        self.assertIsNotNone( result, 'JSON was empty' )


    def test_org_02_getBoards( self ):
        for board in self.org.getBoards():
            self.assertIsNotNone( board.id, msg = "ID has not been provided" )
            self.assertIsNotNone( board.name, msg = "Name has not been provided" )


    def test_org_03_getMembers( self ):
        for member in self.org.getMembers():
            self.assertIsNotNone( member.id, msg = "ID has not been provided" )
            self.assertIsNotNone( member.name, msg = "Name has not been provided" )


    def test_org_04_updateOrganisation( self ):
        description = str( uuid.uuid1() )
        new_organisation = self.org.updateOrganisation( { 'desc': description } )
        new_description = new_organisation.getOrganisationInformation()['desc']

        self.assertEqual( description, new_description, msg = "Descriptions don't match. Update Organisation didn't work!" )


    def test_boa_01_getBoardInformation( self ):
        result = self.board.getBoardInformation()
        self.assertIsNotNone( result, 'JSON was empty' )


    def test_boa_02_getLists( self ):
        for lis in self.board.getLists():
            self.assertIsNotNone( lis.id, msg = "ID has not been provided" )
            self.assertIsNotNone( lis.name, msg = "Name has not been provided" )


    def test_boa_03_getCards( self ):
        for card in self.board.getCards():
            self.assertIsNotNone( card.id, msg = "ID has not been provided" )
            self.assertIsNotNone( card.name, msg = "Name has not been provided" )


    def test_boa_04_getCard( self ):
        card = self.board.getCard( card_id )
        self.assertIsNotNone( card.id, msg = "ID has not been provided" )
        self.assertIsNotNone( card.name, msg = "Name has not been provided" )


    def test_boa_05_getMembers( self ):
        for member in self.board.getMembers():
            self.assertIsNotNone( member.id, msg = "ID has not been provided" )
            self.assertIsNotNone( member.name, msg = "Name has not been provided" )


    def test_boa_06_getOrganisation( self ):
        organisation = self.board.getOrganisation()
        self.assertIsNotNone( organisation.id, msg = "ID has not been provided" )
        self.assertIsNotNone( organisation.name, msg = "Name has not been provided" )


    def test_boa_07_updateBoard( self ):
        description = str( uuid.uuid1() )
        new_board = self.board.updateBoard( { 'desc': description } )
        new_description = new_board.getBoardInformation()['desc']

        self.assertEqual( description, new_description, msg = "Descriptions don't match. Update Board didn't work!" )


    def test_boa_08_addList( self ):
        name = str( uuid.uuid1() )
        new_list = self.board.addList( { 'name': name } )
        new_list_name = new_list.name

        self.assertEqual( name, new_list_name, msg = "Names don't match. Add list didn't work!" )


    def test_lis_01_getListInformation( self ):
        result = self.list.getListInformation()
        self.assertIsNotNone( result, 'JSON was empty' )


    def test_lis_02_getBoard( self ):
        board = self.list.getBoard()
        self.assertIsNotNone( board.id, msg = "ID has not been provided" )
        self.assertIsNotNone( board.name, msg = "Name has not been provided" )


    def test_lis_03_getCards( self ):
        for card in self.list.getCards():
            self.assertIsNotNone( card.id, msg = "ID has not been provided" )
            self.assertIsNotNone( card.name, msg = "Name has not been provided" )


    def test_lis_04_updateList( self ):
        name = str( uuid.uuid1() )
        new_list = self.list.updateList( { 'name': name } )
        new_list_name = new_list.name

        self.assertEqual( name, new_list_name, msg = "Names don't match. Update list didn't work!" )


    def test_lis_05_addCard( self ):
        name = str( uuid.uuid1() )
        new_card = self.list.addCard( { 'name': name } )
        new_card_name = new_card.name

        self.assertEqual( name, new_card_name, msg = "Names don't match. Add card didn't work!" )


    def test_car_01_getCardInformation( self ):
        result = self.card.getCardInformation()
        self.assertIsNotNone( result, 'JSON was empty' )


    def test_car_02_getBoard( self ):
        board = self.card.getBoard()
        self.assertIsNotNone( board.id, msg = "ID has not been provided" )
        self.assertIsNotNone( board.name, msg = "Name has not been provided" )


    def test_car_03_getList( self ):
        lis = self.card.getList()
        self.assertIsNotNone( lis.id, msg = "ID has not been provided" )
        self.assertIsNotNone( lis.name, msg = "Name has not been provided" )


    def test_car_04_getChecklists( self ):
        for checklist in self.card.getChecklists():
            self.assertIsNotNone( checklist.id, msg = "ID has not been provided" )
            self.assertIsNotNone( checklist.name, msg = "Name has not been provided" )


    def test_car_05_getMembers( self ):
        for member in self.card.getMembers():
            self.assertIsNotNone( member.id, msg = "ID has not been provided" )
            self.assertIsNotNone( member.name, msg = "Name has not been provided" )


    def test_car_06_updateCard( self ):
        description = str( uuid.uuid1() )
        new_card = self.card.updateCard( { 'desc': description } )
        new_description = new_card.getCardInformation()['desc']

        self.assertEqual( description, new_description, msg = "Descriptions don't match. Update Card didn't work!" )


    def test_car_07_addComments( self ):
        comment = str( uuid.uuid1() )
        result = self.card.addComments( comment )
        new_comment = result['data']['text']

        self.assertEqual( comment, new_comment, msg = "Comments don't match. Add comment didn't work!" )


    def test_car_08_addAttachment( self ):
        f = open( 'test/test.txt', 'r' ).read()
        result = self.card.addAttachment( 'text.txt', f )
        self.assertIsNotNone( result, "Got nothing back, doesn't look like it worked!" )


    def test_car_09_addChecklists( self ):
        name = str( uuid.uuid1() )
        new_checklist = self.card.addChecklists( { 'name': name } )
        new_checklist_name = new_checklist.name

        self.assertEqual( name, new_checklist_name, "Names don't match. Add Checklist failed!" )


    def test_car_10_addLabels( self ):

        try:
            label_colour = 'green'
            result = self.card.addLabels( { 'value': label_colour } )

            found_label = False

            for label in result:
                if label['color'] == label_colour:
                    found_label = True

            self.assertTrue( found_label, "Label wasn't added!" )

        except ResourceUnavailable:
            # Label already added
            pass


    def test_car_11_addMember( self ):

        try:
            result = self.card.addMember( member_id )

            found_member = False

            for member in result:
                if member.id == member_id:
                    found_member = True

            self.assertTrue( found_member, "Member wasn't added to card!" )

        except ResourceUnavailable:
            # Member is already on the card
            pass


    def test_car_12_removeMember( self ):

        try:
            result = self.card.removeMember( member_id )

            self.assertIsNotNone( result, "JSON failure! Nothing was returned" )

            for member in result:
                self.assertNotEqual( member['id'], member_id, "Member was not removed!" )

        except ResourceUnavailable:
            # Member isn't attached to card
            pass


    def test_che_01_getChecklistInformation( self ):
        result = self.checklist.getChecklistInformation()
        self.assertIsNotNone( result, 'JSON was empty' )


    def test_che_02_getItems( self ):
        result = self.checklist.getItems()
        self.assertIsNotNone( result, 'JSON was empty' )


    def test_che_03_updateChecklist( self ):
        name = str( uuid.uuid1() )
        new_checklist = self.checklist.updateChecklist( name )
        new_name = new_checklist.name

        self.assertEqual( name, new_name, msg = "Names don't match. Update didn't work!" )


    def test_che_04_addItem( self ):
        name = str( uuid.uuid1() )
        result = self.checklist.addItem( {'name': name } )
        new_item_name = result[ len( result ) - 1 ]['name']

        self.assertEqual( name, new_item_name, "Names don't match! Add item failed" )


    def test_che_05_removeItem( self ):
        items = self.checklist.getItems()

        if len( items ) > 0:
            item_id = items[0]['id']

            result = self.checklist.removeItem( item_id )
            self.assertIsNotNone( result, "JSON was empty!" )


    def test_mem_01_getMemberInformation( self ):
        result = self.member.getMemberInformation()
        self.assertIsNotNone( result, 'JSON was empty' )


    def test_mem_02_getBoards( self ):
        for board in self.member.getBoards():
            self.assertIsNotNone( board.id, msg = "ID has not been provided" )
            self.assertIsNotNone( board.name, msg = "Name has not been provided" )


    def test_mem_03_getCards( self ):
        for cards in self.member.getCards():
            self.assertIsNotNone( cards.id, msg = "ID has not been provided" )
            self.assertIsNotNone( cards.name, msg = "Name has not been provided" )



if __name__ == '__main__':

    unittest.main()


########NEW FILE########
__FILENAME__ = authorise
'''
Created on 8 Nov 2012

@author: plish
'''

from trolly.client import Client


class Authorise( Client ):
    """
    Class for helping get user auth token.
    """

    def __init__( self, api_key ):
        super( Authorise, self ).__init__( api_key )


    def getAuthorisationUrl( self, application_name, token_expire = '1day' ):
        """
        Returns a URL that needs to be opened in a browser to retrieve an
        access token.
        """
        query_params = {
                'name': application_name,
                'expiration': token_expire,
                'response_type': 'token',
                'scope': 'read,write'
            }

        authorisation_url = self.buildUri(
                path = '/authorize',
                query_params = self.addAuthorisation(query_params)
            )

        print 'Please go to the following URL and get the user authorisation token:\n', authorisation_url
        return authorisation_url


if __name__ == "__main__":

    import sys

    option = ''

    try:
        option = sys.argv[1]
        api_key = sys.argv[2]
        application_name = sys.argv[3]

        if len( sys.argv ) >= 5:
            token_expires = sys.argv[4]

        else:
            token_expires = '1day'

    except:
        pass

    if option in ( '-h', '--h', '-help' ):
        print '\n%s \n\t%s \n\t%s \n\t%s\n\n' % (
                'Use the -a option to get the authorisation URL.',
                'First argument API key.',
                'Second Argument application name',
                'Third argument token expires (optional, default is 1day)'
            )

    elif option == '-a':
        authorise = Authorise( api_key )
        authorise.getAuthorisationUrl( application_name, token_expires )

    else:
        print "Try running from a terminal using --h for help"












########NEW FILE########
__FILENAME__ = board
'''
Created on 8 Nov 2012

@author: plish
'''

from trolly.trelloobject import TrelloObject


class Board( TrelloObject ):
    """
    Class representing a Trello Board
    """

    def __init__( self, trello_client, board_id, name = '' ):

        super( Board, self ).__init__( trello_client )

        self.id = board_id
        self.name = name

        self.base_uri = '/boards/' + self.id


    def getBoardInformation( self, query_params = {} ):
        """
        Get all information for this board. Returns a dictionary of values.
        """
        return self.fetchJson(
                uri_path = '/boards/' + self.id,
                query_params = query_params
            )


    def getLists( self ):
        """
        Get the lists attached to this board. Returns a list of List objects.
        """
        lists = self.getListsJson( self.base_uri )

        lists_list = []
        for list_json in lists:
            lists_list.append( self.createList( list_json ) )

        return lists_list


    def getCards( self ):
        """
        Get the cards for this board. Returns a list of Card objects.
        """
        cards = self.getCardsJson( self.base_uri )

        cards_list = []
        for card_json in cards:
            cards_list.append( self.createCard( card_json ) )

        return cards_list


    def getCard( self, card_id ):
        """
        Get a Card for a given card id. Returns a Card object.
        """
        card_json = self.fetchJson(
                uri_path = self.base_uri + '/cards/' + card_id
            )

        return self.createCard( card_json )


    def getMembers( self ):
        """
        Get Members attached to this board. Returns a list of Member objects.
        """
        members = self.getMembersJson( self.base_uri )

        members_list = []
        for member_json in members:
            members_list.append( self.createMember( member_json ) )

        return members_list


    def getOrganisation( self ):
        """
        Get the Organisation for this board. Returns Organisation object.
        """
        organisation_json = self.getOrganisationsJson( self.base_uri )

        return self.createOrganisation( organisation_json )


    def updateBoard( self, query_params = {} ):
        """
        Update this board's information. Returns a new board.
        """
        board_json = self.fetchJson(
                uri_path = self.base_uri,
                http_method = 'PUT',
                query_params = query_params
            )

        return self.createBoard( board_json )


    def addList( self, query_params = {} ):
        """
        Create a list for a board. Returns a new List object.
        """
        list_json = self.fetchJson(
                uri_path = self.base_uri + '/lists',
                http_method = 'POST',
                query_params = query_params
            )

        return self.createList( list_json )


    def addMemberById( self, member_id, membership_type = 'normal' ):
        """
        Add a member to the board using the id. Membership type can be
        normal or admin. Returns JSON of all members if successful or raises an
        Unauthorised exception if not.
        """
        return self.fetchJson(
                uri_path = self.base_uri + '/members/%s' % ( member_id ),
                http_method = 'PUT',
                query_params = {
                    'type': membership_type
                }
            )


    def addMember( self, email, fullname, membership_type = 'normal' ):
        """
        Add a member to the board. Membership type can be normal or admin.
        Returns JSON of all members if successful or raises an Unauthorised
        exception if not.
        """
        return self.fetchJson(
                uri_path = self.base_uri + '/members',
                http_method = 'PUT',
                query_params = {
                    'email': email,
                    'fullName': fullname,
                    'type': membership_type
                }
            )


    def removeMember( self, member_id ):
        """
        Remove a member from the organisation.Returns JSON of all members if
        successful or raises an Unauthorised exception if not.
        """
        return self.fetchJson(
                uri_path = self.base_uri + '/members/%s' % ( member_id ),
                http_method = 'DELETE'
            )

########NEW FILE########
__FILENAME__ = card
'''
Created on 8 Nov 2012

@author: plish
'''

import mimetypes

from trolly.trelloobject import TrelloObject


class Card( TrelloObject ):
    """
    Class representing a Trello Card
    """

    def __init__( self, trello_client, card_id, name = '' ):

        super( Card, self ).__init__( trello_client )

        self.id = card_id
        self.name = name

        self.base_uri = '/cards/' + self.id


    def getCardInformation( self, query_params = {} ):
        """
        Get information for this card. Returns a dictionary of values.
        """
        return self.fetchJson(
                uri_path = self.base_uri,
                query_params = query_params
            )


    def getBoard( self ):
        """
        Get board information for this card. Returns a Board object.
        """
        board_json = self.getBoardJson( self.base_uri )
        return self.createBoard( board_json )


    def getList( self ):
        """
        Get list information for this card. Returns a List object.
        """
        list_json = self.getListJson( self.base_uri )

        return self.createList( list_json )


    def getChecklists( self ):
        """
        Get the checklists for this card. Returns a list of Checklist objects.
        """
        checklists = self.getChecklistsJson( self.base_uri )

        checklists_list = []
        for checklist_json in checklists:
            checklists_list.append( self.createChecklist( checklist_json ) )

        return checklists_list


    def getMembers( self ):
        """
        Get all members attached to this card. Returns a list of Member objects.
        """
        members = self.getMembersJson( self.base_uri )

        members_list = []
        for member_json  in members:
            members_list.append( self.createMember( member_json ) )

        return members_list


    def updateCard( self, query_params = {} ):
        """
        Update information for this card. Returns a new Card object.
        """
        card_json = self.fetchJson(
                uri_path = self.base_uri,
                http_method = 'PUT',
                query_params = query_params
            )

        return self.createCard( card_json )


    def addComments( self, comment_text ):
        """
        Adds a comment to this card by the current user.
        """
        return self.fetchJson(
                uri_path = self.base_uri + '/actions/comments',
                http_method = 'POST',
                query_params = { 'text': comment_text }
            )


    def addAttachment( self, filename, open_file ):
        """
        Adds an attachement to this card.
        """
        fields = {
                'api_key': self.client.api_key,
                'token': self.client.user_auth_token
            }

        content_type, body = self.encodeMultipartFormdata(
                fields = fields,
                filename = filename,
                file_values = open_file
            )

        return self.fetchJson(
                uri_path = self.base_uri + '/attachments',
                http_method = 'POST',
                body = body,
                headers = { 'Content-Type': content_type },
            )



    def addChecklists( self, query_params = {} ):
        """
        Add a checklist to this card. Returns a Checklist object.
        """
        checklist_json = self.fetchJson(
                uri_path = self.base_uri + '/checklists',
                http_method = 'POST',
                query_params = query_params
            )

        return self.createChecklist( checklist_json )


    def addLabels( self, query_params = {} ):
        """
        Add a label to this card.
        """
        return self.fetchJson(
                uri_path = self.base_uri + '/labels',
                http_method = 'POST',
                query_params = query_params
            )


    def addMember( self, member_id ):
        """
        Add a member to this card. Returns a list of Member objects.
        """
        members = self.fetchJson(
                uri_path = self.base_uri + '/members',
                http_method = 'POST',
                query_params = { 'value': member_id }
            )

        members_list = []
        for member_json in members:
            members_list.append( self.createMember( member_json ) )

        return members_list


    def removeMember( self, member_id ):
        """
        Remove a member from this card.
        """
        return self.fetchJson(
                uri_path = self.base_uri + '/members/' + member_id,
                http_method = 'DELETE'
            )


    def encodeMultipartFormdata( self, fields, filename, file_values ):
        """
        Encodes data to updload a file to Trello.
        Fields is a dictionary of api_key and token. Filename is the name of the
        file and file_values is the open(file).read() string.
        """
        boundary = '----------Trello_Boundary_$'
        crlf = '\r\n'

        data = []

        for key in fields:
            data.append( '--' + boundary )
            data.append( 'Content-Disposition: form-data; name="%s"' % key )
            data.append( '' )
            data.append( fields[key] )

        data.append( '--' + boundary )
        data.append( 'Content-Disposition: form-data; name="file"; filename="%s"' % ( filename ) )
        data.append( 'Content-Type: %s' % self.getContentType( filename ) )
        data.append( '' )
        data.append( file_values )

        data.append( '--' + boundary + '--' )
        data.append( '' )

        # Try and avoid the damn unicode errors
        data = [ str( segment ) for segment in data ]

        body = crlf.join( data )
        content_type = 'multipart/form-data; boundary=%s' % boundary

        return content_type, body


    def getContentType( self, filename ):
        return mimetypes.guess_type( filename )[0] or 'application/octet-stream'






########NEW FILE########
__FILENAME__ = checklist
'''
Created on 13 Nov 2012

@author: plish
'''

from trolly.trelloobject import TrelloObject


class Checklist( TrelloObject ):
    """
    Class representing a Trello Checklist
    """
    def __init__( self, trello_client, checklist_id, name = '' ):
        super( Checklist, self ).__init__( trello_client )

        self.id = checklist_id
        self.name = name

        self.base_uri = '/checklists/' + self.id


    def getChecklistInformation( self, query_params = {} ):
        """
        Get all information for this Checklist. Returns a dictionary of values.
        """
        return self.fetchJson(
                uri_path = self.base_uri,
                query_params = query_params
            )


    def getItems( self, query_params = {} ):
        """
        Get all the items for this checklist. Returns a list of dictionaries.
        Each dictionary has the values for an item.
        """
        return self.fetchJson(
                uri_path = self.base_uri + '/checkItems',
                query_params = query_params
            )


    def updateChecklist( self, name ):
        """
        Update the current checklist. Returns a new Checklist object.
        """
        checklist_json = self.fetchJson(
                uri_path = self.base_uri,
                http_method = 'PUT',
                query_params = { 'name': name }
            )

        return self.createChecklist( checklist_json )


    def addItem( self, query_params = {} ):
        """
        Add an item to this checklist. Returns a dictionary of values of new item.
        """
        return self.fetchJson(
                uri_path = self.base_uri + '/checkItems',
                http_method = 'POST',
                query_params = query_params
            )


    def removeItem( self, item_id ):
        """
        Deletes an item from this checklist.
        """
        return self.fetchJson(
                uri_path = self.base_uri + '/checkItems/' + item_id,
                http_method = 'DELETE'
            )

########NEW FILE########
__FILENAME__ = client
'''
Created on 8 Nov 2012

@author: plish
'''

import json
from httplib2 import Http
try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode

from trolly.organisation import Organisation
from trolly.board import Board
from trolly.list import List
from trolly.card import Card
from trolly.checklist import Checklist
from trolly.member import Member

from trolly import Unauthorised, ResourceUnavailable


class Client( object ):
    """
    A class that has all the logic for communicating with Trello and returning
    information to the user
    """

    def __init__( self, api_key, user_auth_token = None ):
        """
        Takes the API key and User Auth Token, which are needed for all Trello
        API calls to allow access to requested information
        """
        self.api_key = api_key
        self.user_auth_token = user_auth_token

        self.client = Http()


    def addAuthorisation( self, query_params ):
        """
        Adds the API key and user auth token to the query parameters
        """
        query_params['key'] = self.api_key

        if self.user_auth_token:
            query_params['token'] = self.user_auth_token

        return query_params


    def cleanPath( self, path ):
        """
        Ensure the path has a preceeding /
        """
        if path[0] != '/':
            path = '/' + path
        return path


    def checkErrors( self, uri, response ):
        """
        Check HTTP reponse for known errors
        """
        if response.status == 401:
            raise Unauthorised( uri, response )

        if response.status != 200:
            raise ResourceUnavailable( uri, response )


    def buildUri( self, path, query_params ):
        """
        Build the URI for the API call.
        """
        url = 'https://api.trello.com/1' + self.cleanPath( path )
        url += '?' + urlencode( query_params )

        return url


    def fetchJson( self, uri_path, http_method = 'GET', query_params = {}, body = None, headers = {} ):
        """
        Make a call to Trello API and capture JSON response. Raises an error
        when it fails.
        """
        query_params = self.addAuthorisation( query_params )
        uri = self.buildUri( uri_path, query_params )

        if ( http_method in ( "POST", "PUT", "DELETE" ) and not
             headers.has_key( 'Content-Type' ) ):

            headers['Content-Type'] = 'application/json'

        headers['Accept'] = 'application/json'
        response, content = self.client.request(
                uri = uri,
                method = http_method,
                body = body,
                headers = headers
            )

        self.checkErrors( uri, response )

        return json.loads( content.decode() )


    def createOrganisation( self, organisation_json ):
        """
        Create an Organisation object from a JSON object
        """
        return Organisation(
                trello_client = self,
                organisation_id = organisation_json['id'].encode('utf-8'),
                name = organisation_json['name'].encode( 'utf-8' )
            )


    def createBoard( self, board_json ):
        """
        Create Board object from a JSON object
        """
        return Board(
                trello_client = self,
                board_id = board_json['id'].encode('utf-8'),
                name = board_json['name'].encode( 'utf-8' )
            )


    def createList( self, list_json ):
        """
        Create List object from JSON object
        """
        return List(
                trello_client = self,
                list_id = list_json['id'].encode('utf-8'),
                name = list_json['name'].encode( 'utf-8' )
            )


    def createCard( self, card_json ):
        """
        Create a Card object from JSON object
        """
        return Card(
                trello_client = self,
                card_id = card_json['id'].encode('utf-8'),
                name = card_json['name'].encode( 'utf-8' )
            )


    def createChecklist( self, checklist_json ):
        """
        Create a Checklist object from JSON object
        """
        return Checklist(
                trello_client = self,
                checklist_id = checklist_json['id'].encode('utf-8'),
                name = checklist_json['name'].encode( 'utf-8' )
            )


    def createMember( self, member_json ):
        """
        Create a Member object from JSON object
        """
        return Member(
                trello_client = self,
                member_id = member_json['id'].encode('utf-8'),
                name = member_json['fullName'].encode( 'utf-8' )
            )


########NEW FILE########
__FILENAME__ = list
'''
Created on 8 Nov 2012

@author: plish
'''

from trolly.trelloobject import TrelloObject


class List( TrelloObject ):
    """
    Class representing a Trello List
    """

    def __init__( self, trello_client, list_id, name = '' ):
        super( List, self ).__init__( trello_client )

        self.id = list_id
        self.name = name

        self.base_uri = '/lists/' + self.id


    def getListInformation( self, query_params = {} ):
        """
        Get information for this list. Returns a dictionary of values.
        """
        return self.fetchJson(
                uri_path = self.base_uri,
                query_params = query_params
            )


    def getBoard( self ):
        """
        Get the board that this list belongs to. Returns a Board object.
        """
        board_json = self.getBoardJson( self.base_uri )

        return self.createBoard( board_json )


    def getCards( self ):
        """
        Get cards for this list. Returns a list of Card objects
        """
        cards = self.getCardsJson( self.base_uri )

        cards_list = []
        for card_json in cards:
            cards_list.append( self.createCard( card_json ) )

        return cards_list


    def updateList( self, query_params = {} ):
        """
        Update information for this list. Returns a new List object.
        """
        list_json = self.fetchJson(
                uri_path = self.base_uri,
                http_method = 'PUT',
                query_params = query_params
            )

        return self.createList( list_json )


    def addCard( self, query_params = {} ):
        """
        Create a card for this list. Returns a Card object.
        """
        card_json = self.fetchJson(
                uri_path = self.base_uri + '/cards',
                http_method = 'POST',
                query_params = query_params
            )

        return self.createCard( card_json )










########NEW FILE########
__FILENAME__ = member
'''
Created on 9 Nov 2012

@author: plish
'''

from trolly.trelloobject import TrelloObject


class Member( TrelloObject ):
    """
    Class representing a Trello Member
    """

    def __init__( self, trello_client, member_id, name = '' ):

        super( Member, self ).__init__( trello_client )
        self.id = member_id
        self.name = name

        self.base_uri = '/members/' + self.id


    def getMemberInformation( self, query_params = {} ):
        """
        Get Information for a memeber. Returns a dictionary of values.
        """
        return self.fetchJson(
                uri_path = self.base_uri,
                query_params = query_params
            )


    def getBoards( self ):
        """
        Get all boards this member is attached to. Returns a list of Board objects.
        """
        boards = self.getBoardsJson( self.base_uri )

        boards_list = []
        for board_json in boards:
            boards_list.append( self.createBoard( board_json ) )

        return boards_list


    def getCards( self ):
        """
        Get all cards this member is attached to. Return a list of Card objects.
        """
        cards = self.getCardsJson( self.base_uri )

        cards_list = []
        for card_json in cards:
            cards_list.append( self.createCard( card_json ) )

        return cards_list

########NEW FILE########
__FILENAME__ = organisation
'''
Created on 14 Nov 2012

@author: plish
'''

from trolly.trelloobject import TrelloObject


class Organisation( TrelloObject ):

    def __init__( self, trello_client, organisation_id, name = '' ):
        super( Organisation, self ).__init__( trello_client )

        self.id = organisation_id
        self.name = name

        self.base_uri = '/organizations/' + self.id


    def getOrganisationInformation( self, query_params = {} ):
        """
        Get information fot this organisation. Returns a dictionary of values.
        """
        return self.fetchJson(
                uri_path = self.base_uri,
                query_params = query_params
            )


    def getBoards( self ):
        """
        Get all the boards for this organisation. Returns a list of Board s.
        """
        boards = self.getBoardsJson( self.base_uri )

        boards_list = []
        for board_json in boards:
            boards_list.append( self.createBoard( board_json ) )

        return boards_list


    def getMembers( self ):
        """
        Get all members attached to this organisation. Returns a list of
        Member objects
        """
        members = self.getMembersJson( self.base_uri )

        members_list = []
        for member_json in members:
            members_list.append( self.createMember( member_json ) )

        return members_list


    def updateOrganisation( self, query_params = {} ):
        """
        Update this organisations information. Returns a new organisation object.
        """
        organisation_json = self.fetchJson(
                uri_path = self.base_uri,
                http_method = 'PUT',
                query_params = query_params
            )

        return self.createOrganisation( organisation_json )


    def removeMember( self, member_id ):
        """
        Remove a member from the organisation.Returns JSON of all members if
        successful or raises an Unauthorised exception if not.
        """
        return self.fetchJson(
                uri_path = self.base_uri + '/members/%s' % ( member_id ),
                http_method = 'DELETE'
            )


    def addMemberById( self, member_id, membership_type = 'normal' ):
        """
        Add a member to the board using the id. Membership type can be
        normal or admin. Returns JSON of all members if successful or raises an
        Unauthorised exception if not.
        """
        return self.fetchJson(
                uri_path = self.base_uri + '/members/%s' % ( member_id ),
                http_method = 'PUT',
                query_params = {
                    'type': membership_type
                }
            )


    def addMember( self, email, fullname, membership_type = 'normal' ):
        """
        Add a member to the board. Membership type can be normal or admin.
        Returns JSON of all members if successful or raises an Unauthorised
        exception if not.
        """
        return self.fetchJson(
                uri_path = self.base_uri + '/members',
                http_method = 'PUT',
                query_params = {
                    'email': email,
                    'fullName': fullname,
                    'type': membership_type
                }
            )

########NEW FILE########
__FILENAME__ = trelloobject
'''
Created on 9 Nov 2012

@author: plish
'''

class TrelloObject( object ):
    """
    This class is a base object that should be used by all trello objects;
    Board, List, Card, etc. It contains methods needed and used by all those
    objects and masks the client calls as methods belonging to the object.
    """

    def __init__( self, trello_client ):
        """
        A Trello client, Oauth of HTTP client is required for each object.
        """
        super( TrelloObject, self ).__init__()

        self.client = trello_client


    def fetchJson( self, uri_path, http_method = 'GET', query_params = {}, body = None, headers = {} ):

        return self.client.fetchJson( 
                uri_path = uri_path,
                http_method = http_method,
                query_params = query_params,
                body = body,
                headers = headers,
            )


    def getOrganisationsJson( self, base_uri ):
        return self.fetchJson( base_uri + '/organization' )


    def getBoardsJson( self, base_uri ):
        return self.fetchJson( base_uri + '/boards' )


    def getBoardJson( self, base_uri ):
        return self.fetchJson( base_uri + '/board' )


    def getListsJson( self, base_uri ):
        return self.fetchJson( base_uri + '/lists' )


    def getListJson( self, base_uri ):
        return self.fetchJson( base_uri + '/list' )


    def getCardsJson( self, base_uri ):
        return self.fetchJson( base_uri + '/cards' )


    def getChecklistsJson( self, base_uri ):
        return self.fetchJson( base_uri + '/checklists' )


    def getMembersJson( self, base_uri ):
        return self.fetchJson( base_uri + '/members' )


    def createOrganisation( self, oranisation_json, **kwargs ):
        return self.client.createOrganisation( oranisation_json, **kwargs )


    def createBoard( self, board_json, **kwargs ):
        return self.client.createBoard( board_json, **kwargs )


    def createList( self, list_json, **kwargs ):
        return self.client.createList( list_json, **kwargs )


    def createCard( self, card_json, **kwargs ):
        return self.client.createCard( card_json, **kwargs )


    def createChecklist( self, checklist_json, **kwargs ):
        return self.client.createChecklist( checklist_json, **kwargs )


    def createMember( self, member_json, **kwargs ):
        return self.client.createMember( member_json, **kwargs )

########NEW FILE########
