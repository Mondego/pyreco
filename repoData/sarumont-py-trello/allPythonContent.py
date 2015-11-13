__FILENAME__ = test_trello
from trello import TrelloClient
import unittest
import os

class TrelloClientTestCase(unittest.TestCase):

	"""
	Tests for TrelloClient API. Note these test are in order to preserve dependencies, as an API
	integration cannot be tested independently.
	"""

	def setUp(self):
		self._trello = TrelloClient(os.environ['TRELLO_API_KEY'],
                                    token=os.environ['TRELLO_TOKEN'])

	def test01_list_boards(self):
		self.assertEquals(
				len(self._trello.list_boards()),
				int(os.environ['TRELLO_TEST_BOARD_COUNT']))

	def test10_board_attrs(self):
		boards = self._trello.list_boards()
		for b in boards:
			self.assertIsNotNone(b.id, msg="id not provided")
			self.assertIsNotNone(b.name, msg="name not provided")
			self.assertIsNotNone(b.description, msg="description not provided")
			self.assertIsNotNone(b.closed, msg="closed not provided")
			self.assertIsNotNone(b.url, msg="url not provided")

	def test20_board_all_lists(self):
		boards = self._trello.list_boards()
		for b in boards:
			try:
				b.all_lists()
			except Exception as e:
				self.fail("Caught Exception getting lists")

	def test21_board_open_lists(self):
		boards = self._trello.list_boards()
		for b in boards:
			try:
				b.open_lists()
			except Exception as e:
				self.fail("Caught Exception getting open lists")

	def test22_board_closed_lists(self):
		boards = self._trello.list_boards()
		for b in boards:
			try:
				b.closed_lists()
			except Exception as e:
				self.fail("Caught Exception getting closed lists")

	def test30_list_attrs(self):
		boards = self._trello.list_boards()
		for b in boards:
			for l in b.all_lists():
				self.assertIsNotNone(l.id, msg="id not provided")
				self.assertIsNotNone(l.name, msg="name not provided")
				self.assertIsNotNone(l.closed, msg="closed not provided")
			break # only need to test one board's lists

	def test40_list_cards(self):
		boards = self._trello.list_boards()
		for b in boards:
			for l in b.all_lists():
				for c in l.list_cards():
					self.assertIsNotNone(c.id, msg="id not provided")
					self.assertIsNotNone(c.name, msg="name not provided")
					self.assertIsNotNone(c.description, msg="description not provided")
					self.assertIsNotNone(c.closed, msg="closed not provided")
					self.assertIsNotNone(c.url, msg="url not provided")
				break
			break
		pass

	def test50_add_card(self):
		boards = self._trello.list_boards()
		board_id = None
		for b in boards:
			if b.name != os.environ['TRELLO_TEST_BOARD_NAME']:
				continue

			for l in b.open_lists():
				try:
					name = "Testing from Python - no desc"
					card = l.add_card(name)
				except Exception as e:
					print str(e)
					self.fail("Caught Exception adding card")

				self.assertIsNotNone(card, msg="card is None")
				self.assertIsNotNone(card.id, msg="id not provided")
				self.assertEquals(card.name, name)
				self.assertIsNotNone(card.closed, msg="closed not provided")
				self.assertIsNotNone(card.url, msg="url not provided")
				break
			break
		if not card:
			self.fail("No card created")

	def test51_add_card(self):
		boards = self._trello.list_boards()
		board_id = None
		for b in boards:
			if b.name != os.environ['TRELLO_TEST_BOARD_NAME']:
				continue

			for l in b.open_lists():
				try:
					name = "Testing from Python"
					description = "Description goes here"
					card = l.add_card(name, description)
				except Exception as e:
					print str(e)
					self.fail("Caught Exception adding card")

				self.assertIsNotNone(card, msg="card is None")
				self.assertIsNotNone(card.id, msg="id not provided")
				self.assertEquals(card.name, name)
				self.assertEquals(card.description, description)
				self.assertIsNotNone(card.closed, msg="closed not provided")
				self.assertIsNotNone(card.url, msg="url not provided")
				break
			break
		if not card:
			self.fail("No card created")

def suite():
	tests = ['test01_list_boards', 'test10_board_attrs', 'test20_add_card']
	return unittest.TestSuite(map(TrelloClientTestCase, tests))

if __name__ == "__main__":
	unittest.main()

########NEW FILE########
__FILENAME__ = util
import os
import urlparse

import oauth2 as oauth


def create_oauth_token():
    """
    Script to obtain an OAuth token from Trello.

    Must have TRELLO_API_KEY and TRELLO_API_SECRET set in your environment
    To set the token's expiration, set TRELLO_EXPIRATION as a string in your
    environment settings (eg. 'never'), otherwise it will default to 30 days.

    More info on token scope here:
        https://trello.com/docs/gettingstarted/#getting-a-token-from-a-user
    """
    request_token_url = 'https://trello.com/1/OAuthGetRequestToken'
    authorize_url = 'https://trello.com/1/OAuthAuthorizeToken'
    access_token_url = 'https://trello.com/1/OAuthGetAccessToken'

    expiration = os.environ.get('TRELLO_EXPIRATION', None)
    scope = os.environ.get('TRELLO_SCOPE', 'read,write')
    trello_key = os.environ['TRELLO_API_KEY']
    trello_secret = os.environ['TRELLO_API_SECRET']

    consumer = oauth.Consumer(trello_key, trello_secret)
    client = oauth.Client(consumer)

    # Step 1: Get a request token. This is a temporary token that is used for
    # having the user authorize an access token and to sign the request to obtain
    # said access token.

    resp, content = client.request(request_token_url, "GET")
    if resp['status'] != '200':
        raise Exception("Invalid response %s." % resp['status'])

    request_token = dict(urlparse.parse_qsl(content))

    print "Request Token:"
    print "    - oauth_token        = %s" % request_token['oauth_token']
    print "    - oauth_token_secret = %s" % request_token['oauth_token_secret']
    print

    # Step 2: Redirect to the provider. Since this is a CLI script we do not
    # redirect. In a web application you would redirect the user to the URL
    # below.

    print "Go to the following link in your browser:"
    print "{authorize_url}?oauth_token={oauth_token}&scope={scope}&expiration={expiration}".format(
        authorize_url=authorize_url,
        oauth_token=request_token['oauth_token'],
        expiration=expiration,
        scope=scope,
    )

    # After the user has granted access to you, the consumer, the provider will
    # redirect you to whatever URL you have told them to redirect to. You can
    # usually define this in the oauth_callback argument as well.
    accepted = 'n'
    while accepted.lower() == 'n':
        accepted = raw_input('Have you authorized me? (y/n) ')
    oauth_verifier = raw_input('What is the PIN? ')

    # Step 3: Once the consumer has redirected the user back to the oauth_callback
    # URL you can request the access token the user has approved. You use the
    # request token to sign this request. After this is done you throw away the
    # request token and use the access token returned. You should store this
    # access token somewhere safe, like a database, for future use.
    token = oauth.Token(request_token['oauth_token'],
                        request_token['oauth_token_secret'])
    token.set_verifier(oauth_verifier)
    client = oauth.Client(consumer, token)

    resp, content = client.request(access_token_url, "POST")
    access_token = dict(urlparse.parse_qsl(content))

    print "Access Token:"
    print "    - oauth_token        = %s" % access_token['oauth_token']
    print "    - oauth_token_secret = %s" % access_token['oauth_token_secret']
    print
    print "You may now access protected resources using the access tokens above."
    print

if __name__ == '__main__':
    create_oauth_token()

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

########NEW FILE########
