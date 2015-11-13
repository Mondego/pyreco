__FILENAME__ = config
__author__ = 'gsibble'

COINBASE_ENDPOINT = 'https://coinbase.com/api/v1'

COINBASE_AUTH_URI = 'https://www.coinbase.com/oauth/authorize'
COINBASE_TOKEN_URI = 'https://www.coinbase.com/oauth/token'


TEMP_CREDENTIALS = '''
{"_module": "oauth2client.client", "token_expiry": "2013-03-24T02:37:50Z", "access_token": "2a02d1fc82b1c42d4ea94d6866b5a232b53a3a50ad4ee899ead9afa6144c2ca3", "token_uri": "https://www.coinbase.com/oauth/token", "invalid": false, "token_response": {"access_token": "2a02d1fc82b1c42d4ea94d6866b5a232b53a3a50ad4ee899ead9afa6144c2ca3", "token_type": "bearer", "expires_in": 7200, "refresh_token": "ffec0153da773468c8cb418d07ced54c13ca8deceae813c9be0b90d25e7c3d71", "scope": "all"}, "client_id": "2df06cb383f4ffffac20e257244708c78a1150d128f37d420f11fdc069a914fc", "id_token": null, "client_secret": "7caedd79052d7e29aa0f2700980247e499ce85381e70e4a44de0c08f25bded8a", "revoke_uri": "https://accounts.google.com/o/oauth2/revoke", "_class": "OAuth2Credentials", "refresh_token": "ffec0153da773468c8cb418d07ced54c13ca8deceae813c9be0b90d25e7c3d71", "user_agent": null}'''
########NEW FILE########
__FILENAME__ = amount
__author__ = 'gsibble'

class CoinbaseAmount(float):

    def __new__(self, amount, currency):
        return float.__new__(self, amount)

    def __init__(self, amount, currency):
        super(CoinbaseAmount, self).__init__()
        self.currency = currency

########NEW FILE########
__FILENAME__ = button
__author__ = 'mhluongo'

class CoinbasePaymentButton(object):

    def __init__(self, *args, **kwargs):
        for key, value in kwargs.iteritems():
            setattr(self, key, value)


########NEW FILE########
__FILENAME__ = contact
__author__ = 'gsibble'

class CoinbaseContact(object):

    def __init__(self, contact_id=None, name=None, email=None):
        self.id = contact_id
        self.name = name
        self.email = email
########NEW FILE########
__FILENAME__ = error
__author__ = 'kroberts'



class CoinbaseError(object):

    def __init__(self, errorList):
        self.error = errorList

########NEW FILE########
__FILENAME__ = transaction
__author__ = 'gsibble'

from amount import CoinbaseAmount
from contact import CoinbaseContact

class CoinbaseTransaction(object):

    def __init__(self, transaction):

        self.transaction_id = transaction['id']
        self.created_at = transaction['created_at']
        self.notes = transaction['notes']

        transaction_amount = transaction['amount']['amount']
        transaction_currency = transaction['amount']['currency']

        self.amount = CoinbaseAmount(transaction_amount, transaction_currency)

        self.status = transaction['status']
        self.request = transaction['request']


        #Sender Information
        if 'sender' in transaction:
            sender_id = transaction['sender'].get('id', None)
            sender_name = transaction['sender'].get('name', None)
            sender_email = transaction['sender'].get('email', None)

            self.sender = CoinbaseContact(contact_id=sender_id,
                                          name=sender_name,
                                          email=sender_email)

        else:
            #TODO:  Not sure what key would go here
            pass

        #Recipient Info
        if 'recipient' in transaction:
            recipient_id = transaction['recipient'].get('id', None)
            recipient_name = transaction['recipient'].get('name', None)
            recipient_email = transaction['recipient'].get('email', None)

            self.recipient = CoinbaseContact(contact_id=recipient_id,
                                          name=recipient_name,
                                          email=recipient_email)
            self.recipient_address = None
            self.recipient_type = 'CoinBase'

        elif 'recipient_address' in transaction:
            self.recipient = None
            self.recipient_address = transaction['recipient_address']
            self.recipient_type = 'Bitcoin'

    def refresh(self):
        pass
        #TODO:  Refresh the transaction

    def cancel(self):
        pass
        #TODO:  Cancel the transaction if possible

    def complete(self):
        pass
        #TODO:  Approve the transaction if possible

    def resend(self):
        pass
        #TODO:  Resend the transaction email if possible


########NEW FILE########
__FILENAME__ = transfer
__author__ = 'pmb6tz'

from amount import CoinbaseAmount

class CoinbaseTransfer(object):

    def __init__(self, transfer):
        self.type = transfer['type']
        self.code = transfer['code']
        self.created_at = transfer['created_at']

        fees_coinbase_cents = transfer['fees']['coinbase']['cents']
        fees_coinbase_currency_iso = transfer['fees']['coinbase']['currency_iso']
        self.fees_coinbase = CoinbaseAmount(fees_coinbase_cents, fees_coinbase_currency_iso)

        fees_bank_cents = transfer['fees']['bank']['cents']
        fees_bank_currency_iso = transfer['fees']['bank']['currency_iso']
        self.fees_bank = CoinbaseAmount(fees_bank_cents, fees_bank_currency_iso)

        self.payout_date = transfer['payout_date']
        self.transaction_id = transfer.get('transaction_id','')
        self.status = transfer['status']

        btc_amount = transfer['btc']['amount']
        btc_currency = transfer['btc']['currency']
        self.btc_amount = CoinbaseAmount(btc_amount, btc_currency)

        subtotal_amount = transfer['subtotal']['amount']
        subtotal_currency = transfer['subtotal']['currency']
        self.subtotal_amount = CoinbaseAmount(subtotal_amount, subtotal_currency)

        total_amount = transfer['total']['amount']
        total_currency = transfer['total']['currency']
        self.total_amount = CoinbaseAmount(total_amount, total_currency)

        self.description = transfer.get('description','')

    def refresh(self):
        pass
        #TODO:  Refresh the transfer

    def cancel(self):
        pass
        #TODO:  Cancel the transfer if possible

    def complete(self):
        pass
        #TODO:  Approve the transfer if possible

    def resend(self):
        pass
        #TODO:  Resend the transfer email if possible
########NEW FILE########
__FILENAME__ = user
__author__ = 'gsibble'

class CoinbaseUser(object):

    def __init__(self,
                 user_id,
                 name,
                 email,
                 time_zone,
                 native_currency,
                 balance,
                 buy_level,
                 sell_level,
                 buy_limit,
                 sell_limit):

        self.id = user_id
        self.name = name
        self.email = email
        self.time_zone = time_zone
        self.native_currency = native_currency
        self.balance = balance
        self.buy_level = buy_level
        self.sell_level = sell_level
        self.buy_limit = buy_limit
        self.sell_limit = sell_limit
########NEW FILE########
__FILENAME__ = tests
__author__ = 'gsibble'

import sure
from sure import it, this, those, these
import unittest
from httpretty import HTTPretty, httprettified

from coinbase import CoinbaseAccount
from models import CoinbaseAmount

TEMP_CREDENTIALS = '''{"_module": "oauth2client.client", "token_expiry": "2014-03-31T23:27:40Z", "access_token": "c15a9f84e471db9b0b8fb94f3cb83f08867b4e00cb823f49ead771e928af5c79", "token_uri": "https://www.coinbase.com/oauth/token", "invalid": false, "token_response": {"access_token": "c15a9f84e471db9b0b8fb94f3cb83f08867b4e00cb823f49ead771e928af5c79", "token_type": "bearer", "expires_in": 7200, "refresh_token": "90cb2424ddc39f6668da41a7b46dfd5a729ac9030e19e05fd95bb1880ad07e65", "scope": "all"}, "client_id": "2df06cb383f4ffffac20e257244708c78a1150d128f37d420f11fdc069a914fc", "id_token": null, "client_secret": "7caedd79052d7e29aa0f2700980247e499ce85381e70e4a44de0c08f25bded8a", "revoke_uri": "https://accounts.google.com/o/oauth2/revoke", "_class": "OAuth2Credentials", "refresh_token": "90cb2424ddc39f6668da41a7b46dfd5a729ac9030e19e05fd95bb1880ad07e65", "user_agent": null}'''

class CoinBaseAmountTests(unittest.TestCase):

    def setUp(self):
        self.cb_amount = CoinbaseAmount(1, 'BTC')

    def test_cb_amount_class(self):
        this(self.cb_amount).should.equal(1)
        this(self.cb_amount.currency).should.equal('BTC')

class CoinBaseAPIKeyTests(unittest.TestCase):

    def setUp(self):
        self.account = CoinbaseAccount(api_key='f64223978e5fd99d07cded069db2189a38c17142fee35625f6ab3635585f61ab')

    @httprettified
    def test_api_key_balance(self):

        HTTPretty.register_uri(HTTPretty.GET, "https://coinbase.com/api/v1/account/balance",
                           body='''{"amount":"1.00000000","currency":"BTC"}''',
                           content_type='text/json')

        this(self.account.balance).should.equal(1.0)

class CoinBaseLibraryTests(unittest.TestCase):

    def setUp(self):
        self.account = CoinbaseAccount(oauth2_credentials=TEMP_CREDENTIALS)

    @httprettified
    def test_retrieve_balance(self):

        HTTPretty.register_uri(HTTPretty.GET, "https://coinbase.com/api/v1/account/balance",
                               body='''{"amount":"0.00000000","currency":"BTC"}''',
                               content_type='text/json')

        this(self.account.balance).should.equal(0.0)
        this(self.account.balance.currency).should.equal('BTC')

        #TODO:  Switch to decimals
        #this(self.account.balance).should.equal(CoinbaseAmount('0.00000000', 'USD'))
        #this(self.account.balance.currency).should.equal(CoinbaseAmount('0.00000000', 'USD').currency)

    @httprettified
    def test_receive_addresses(self):

        HTTPretty.register_uri(HTTPretty.GET, "https://coinbase.com/api/v1/account/receive_address",
                               body='''{"address" : "1DX9ECEF3FbGUtzzoQhDT8CG3nLUEA2FJt"}''',
                               content_type='text/json')

        this(self.account.receive_address).should.equal(u'1DX9ECEF3FbGUtzzoQhDT8CG3nLUEA2FJt')

    @httprettified
    def test_contacts(self):
        HTTPretty.register_uri(HTTPretty.GET, "https://coinbase.com/api/v1/contacts",
                               body='''{"contacts":[{"contact":{"email":"brian@coinbase.com"}}],"total_count":1,"num_pages":1,"current_page":1}''',
                               content_type='text/json')

        this(self.account.contacts).should.equal([{u'email': u'brian@coinbase.com'}])

    @httprettified
    def test_buy_price_1(self):
        HTTPretty.register_uri(HTTPretty.GET, "https://coinbase.com/api/v1/prices/buy?qty=1",
                               body='''{"amount":"63.31","currency":"USD"}''',
                               content_type='text/json')

        buy_price_1 = self.account.buy_price(1)
        this(buy_price_1).should.be.an(float)
        this(buy_price_1).should.be.lower_than(100)
        this(buy_price_1.currency).should.equal('USD')

    @httprettified
    def test_buy_price_2(self):

        HTTPretty.register_uri(HTTPretty.GET, "https://coinbase.com/api/v1/prices/buy?qty=10",
                               body='''{"amount":"633.25","currency":"USD"}''',
                               content_type='text/json')

        buy_price_10 = self.account.buy_price(10)
        this(buy_price_10).should.be.greater_than(100)

    @httprettified
    def test_sell_price(self):

        HTTPretty.register_uri(HTTPretty.GET, "https://coinbase.com/api/v1/prices/sell?qty=1",
                               body='''{"amount":"63.31","currency":"USD"}''',
                               content_type='text/json')

        sell_price_1 = self.account.sell_price(1)
        this(sell_price_1).should.be.an(float)
        this(sell_price_1).should.be.lower_than(100)
        this(sell_price_1.currency).should.equal('USD')

    @httprettified
    def test_sell_price_10(self):
        HTTPretty.register_uri(HTTPretty.GET, "https://coinbase.com/api/v1/prices/sell?qty=1",
                               body='''{"amount":"630.31","currency":"USD"}''',
                               content_type='text/json')

        sell_price_10 = self.account.sell_price(10)
        this(sell_price_10).should.be.greater_than(100)

    @httprettified
    def test_request_bitcoin(self):

        HTTPretty.register_uri(HTTPretty.POST, "https://coinbase.com/api/v1/transactions/request_money",
                               body='''{"success":true,"transaction":{"id":"514e4c37802e1bf69100000e","created_at":"2013-03-23T17:43:35-07:00","hsh":null,"notes":"Testing","amount":{"amount":"1.00000000","currency":"BTC"},"request":true,"status":"pending","sender":{"id":"514e4c1c802e1bef9800001e","email":"george@atlasr.com","name":"george@atlasr.com"},"recipient":{"id":"509e01ca12838e0200000212","email":"gsibble@gmail.com","name":"gsibble@gmail.com"}}}''',
                               content_type='text/json')

        new_request = self.account.request('george@atlasr.com', 1, 'Testing')

        this(new_request.amount).should.equal(1)
        this(new_request.request).should.equal(True)
        this(new_request.sender.email).should.equal('george@atlasr.com')
        this(new_request.recipient.email).should.equal('gsibble@gmail.com')
        this(new_request.notes).should.equal('Testing')

    @httprettified
    def test_send_bitcoin(self):

        HTTPretty.register_uri(HTTPretty.POST, "https://coinbase.com/api/v1/transactions/send_money",
                               body='''{"success":true,"transaction":{"id":"5158b227802669269c000009","created_at":"2013-03-31T15:01:11-07:00","hsh":null,"notes":"","amount":{"amount":"-0.10000000","currency":"BTC"},"request":false,"status":"pending","sender":{"id":"509e01ca12838e0200000212","email":"gsibble@gmail.com","name":"gsibble@gmail.com"},"recipient_address":"15yHmnB5vY68sXpAU9pR71rnyPAGLLWeRP"}}    ''',
                               content_type='text/json')

        new_transaction_with_btc_address = self.account.send('15yHmnB5vY68sXpAU9pR71rnyPAGLLWeRP', amount=0.1)

        this(new_transaction_with_btc_address.amount).should.equal(-0.1)
        this(new_transaction_with_btc_address.request).should.equal(False)
        this(new_transaction_with_btc_address.sender.email).should.equal('gsibble@gmail.com')
        this(new_transaction_with_btc_address.recipient).should.equal(None)
        this(new_transaction_with_btc_address.recipient_address).should.equal('15yHmnB5vY68sXpAU9pR71rnyPAGLLWeRP')

        HTTPretty.register_uri(HTTPretty.POST, "https://coinbase.com/api/v1/transactions/send_money",
                               body='''{"success":true,"transaction":{"id":"5158b2920b974ea4cb000003","created_at":"2013-03-31T15:02:58-07:00","hsh":null,"notes":"","amount":{"amount":"-0.10000000","currency":"BTC"},"request":false,"status":"pending","sender":{"id":"509e01ca12838e0200000212","email":"gsibble@gmail.com","name":"gsibble@gmail.com"},"recipient":{"id":"4efec8d7bedd320001000003","email":"brian@coinbase.com","name":"Brian Armstrong"},"recipient_address":"brian@coinbase.com"}}
''',
                               content_type='text/json')

        new_transaction_with_email = self.account.send('brian@coinbase.com', amount=0.1)

        this(new_transaction_with_email.recipient.email).should.equal('brian@coinbase.com')

    @httprettified
    def test_transaction_list(self):

        HTTPretty.register_uri(HTTPretty.GET, "https://coinbase.com/api/v1/transactions",
                               body='''{"current_user":{"id":"509e01ca12838e0200000212","email":"gsibble@gmail.com","name":"gsibble@gmail.com"},"balance":{"amount":"0.00000000","currency":"BTC"},"total_count":4,"num_pages":1,"current_page":1,"transactions":[{"transaction":{"id":"514e4c37802e1bf69100000e","created_at":"2013-03-23T17:43:35-07:00","hsh":null,"notes":"Testing","amount":{"amount":"1.00000000","currency":"BTC"},"request":true,"status":"pending","sender":{"id":"514e4c1c802e1bef9800001e","email":"george@atlasr.com","name":"george@atlasr.com"},"recipient":{"id":"509e01ca12838e0200000212","email":"gsibble@gmail.com","name":"gsibble@gmail.com"}}},{"transaction":{"id":"514e4c1c802e1bef98000020","created_at":"2013-03-23T17:43:08-07:00","hsh":null,"notes":"Testing","amount":{"amount":"1.00000000","currency":"BTC"},"request":true,"status":"pending","sender":{"id":"514e4c1c802e1bef9800001e","email":"george@atlasr.com","name":"george@atlasr.com"},"recipient":{"id":"509e01ca12838e0200000212","email":"gsibble@gmail.com","name":"gsibble@gmail.com"}}},{"transaction":{"id":"514b9fb1b8377ee36500000d","created_at":"2013-03-21T17:02:57-07:00","hsh":"42dd65a18dbea0779f32021663e60b1fab8ee0f859db7172a078d4528e01c6c8","notes":"You gave me this a while ago. It's turning into a fair amount of cash and thought you might want it back :) Building something on your API this weekend. Take care!","amount":{"amount":"-1.00000000","currency":"BTC"},"request":false,"status":"complete","sender":{"id":"509e01ca12838e0200000212","email":"gsibble@gmail.com","name":"gsibble@gmail.com"},"recipient":{"id":"4efec8d7bedd320001000003","email":"brian@coinbase.com","name":"Brian Armstrong"},"recipient_address":"brian@coinbase.com"}},{"transaction":{"id":"509e01cb12838e0200000224","created_at":"2012-11-09T23:27:07-08:00","hsh":"ac9b0ffbe36dbe12c5ca047a5bdf9cadca3c9b89b74751dff83b3ac863ccc0b3","notes":"","amount":{"amount":"1.00000000","currency":"BTC"},"request":false,"status":"complete","sender":{"id":"4efec8d7bedd320001000003","email":"brian@coinbase.com","name":"Brian Armstrong"},"recipient":{"id":"509e01ca12838e0200000212","email":"gsibble@gmail.com","name":"gsibble@gmail.com"},"recipient_address":"gsibble@gmail.com"}}]}''',
                           content_type='text/json')

        transaction_list = self.account.transactions()

        this(transaction_list).should.be.an(list)

    @httprettified
    def test_getting_transaction(self):

        HTTPretty.register_uri(HTTPretty.GET, "https://coinbase.com/api/v1/transactions/5158b227802669269c000009",
                               body='''{"transaction":{"id":"5158b227802669269c000009","created_at":"2013-03-31T15:01:11-07:00","hsh":"223a404485c39173ab41f343439e59b53a5d6cba94a02501fc6c67eeca0d9d9e","notes":"","amount":{"amount":"-0.10000000","currency":"BTC"},"request":false,"status":"pending","sender":{"id":"509e01ca12838e0200000212","email":"gsibble@gmail.com","name":"gsibble@gmail.com"},"recipient_address":"15yHmnB5vY68sXpAU9pR71rnyPAGLLWeRP"}}''',
                               content_type='text/json')

        transaction = self.account.get_transaction('5158b227802669269c000009')

        this(transaction.status).should.equal('pending')
        this(transaction.amount).should.equal(-0.1)

    @httprettified
    def test_getting_user_details(self):

        HTTPretty.register_uri(HTTPretty.GET, "https://coinbase.com/api/v1/users",
                               body='''{"users":[{"user":{"id":"509f01da12837e0201100212","name":"New User","email":"gsibble@gmail.com","time_zone":"Pacific Time (US & Canada)","native_currency":"USD","buy_level":1,"sell_level":1,"balance":{"amount":"1225.86084181","currency":"BTC"},"buy_limit":{"amount":"10.00000000","currency":"BTC"},"sell_limit":{"amount":"50.00000000","currency":"BTC"}}}]}''',
                               content_type='text/json')

        user = self.account.get_user_details()

        this(user.id).should.equal("509f01da12837e0201100212")
        this(user.balance).should.equal(1225.86084181)

    @httprettified
    def test_creating_a_button(self):

        HTTPretty.register_uri(HTTPretty.POST, "https://coinbase.com/api/v1/buttons",
                               body='''{"button": {"style": "buy_now_large", "code": "b123456783q812e381cd9d39a5783277", "name": "Test Button", "info_url": null, "text": "Pay With Bitcoin", "price": {"cents": 2000, "currency_iso": "USD"}, "include_email": false, "custom": "", "cancel_url": null, "auto_redirect": false, "success_url": null, "variable_price": false, "include_address": false, "callback_url": null, "type": "buy_now", "choose_price": false, "description": ""}, "success": true}''',
                               content_type='text/json')

        button = self.account.create_button('Test Button', '20.00', 'USD')

        this(button.code).should.equal('b123456783q812e381cd9d39a5783277')
        this(button.name).should.equal('Test Button')
        this(button.price['cents']).should.equal(2000)

########NEW FILE########
__FILENAME__ = example
__author__ = 'gsibble'

from coinbase import CoinbaseAccount
import oauth2client

#Use oAuth2client web flow to get JSON credentials (see coinbase_oauth2 example)
TEMP_CREDENTIALS = '''{"_module": "oauth2client.client", "token_expiry": "2013-03-31T22:48:20Z", "access_token": "c15a9f84e471db9b0b8fb94f3cb83f08867b4e00cb823f49ead771e928af5c79", "token_uri": "https://www.coinbase.com/oauth/token", "invalid": false, "token_response": {"access_token": "c15a9f84e471db9b0b8fb94f3cb83f08867b4e00cb823f49ead771e928af5c79", "token_type": "bearer", "expires_in": 7200, "refresh_token": "90cb2424ddc39f6668da41a7b46dfd5a729ac9030e19e05fd95bb1880ad07e65", "scope": "all"}, "client_id": "2df06cb383f4ffffac20e257244708c78a1150d128f37d420f11fdc069a914fc", "id_token": null, "client_secret": "7caedd79052d7e29aa0f2700980247e499ce85381e70e4a44de0c08f25bded8a", "revoke_uri": "https://accounts.google.com/o/oauth2/revoke", "_class": "OAuth2Credentials", "refresh_token": "90cb2424ddc39f6668da41a7b46dfd5a729ac9030e19e05fd95bb1880ad07e65", "user_agent": null}'''


def do_coinbase_stuff(account):
    print 'The current value of 1 BTC in USD is: $' + str(account.sell_price())
    print 'The current value of 10 BTC in USD is: $' + str(account.sell_price(qty=10))
    print 'You can buy 1 bitcoin for ' + str(account.buy_price()) + ' USD'
    print 'Your balance is ' + str(account.balance) + ' BTC'
    print 'That means your account value in USD is $' + str(account.sell_price(qty=account.balance))

    print 'Your receive address is ' + str(account.receive_address)
    print 'You have the following people in your address book:'
    print [contact['email'] for contact in account.contacts]

    print 'Would you like to try moving some Bitcoin around?'
    response = raw_input("Type YES if so: ")

    if response == 'YES':
        print "Awesome!  Let's do it.  First, let's have you make a request to someone for some BTC."
        request_btc_from_email = raw_input("What email address would you like to request BTC from: ")
        amount_to_request = raw_input("How much BTC would you like to request: ")
        print 'Setting up request to ' + request_btc_from_email
        request_transaction = account.request(from_email=request_btc_from_email,
                                              amount=amount_to_request,
                                              notes='Test request')
        print "We successfully created a request for " + request_transaction.sender.email + " to send you " + str(
            request_transaction.amount) + " " + request_transaction.amount.currency

        print "Now would you like to send some bitcoin? Plese note this will really send BTC from your account."
        send_response = raw_input("Type YES if so: ")

        if send_response == 'YES':
            print "Awesome!  Let's do that!"
            send_btc_to = raw_input("Please enter a Bitcoin address to send money to: ")
            amount_to_send = raw_input("How much BTC would you like to send: ")
            send_transaction = account.send(to_address=send_btc_to,
                                            amount=amount_to_send,
                                            notes='Test send')

            print "We successfully sent " + str(
                send_transaction.amount) + " " + send_transaction.amount.currency + " to " + send_transaction.recipient_address

            print "Your new balance is " + str(account.balance)

    transactions = account.transactions(count=30)

    print "Here are your last " + str(len(transactions)) + " transactions:"

    for index, transaction in enumerate(transactions):

        if transaction.amount > 0:
            print str(index) + ": " + str(transaction.amount) + " " + transaction.amount.currency + " to your Coinbase wallet."
        else:
            print str(index) + ": " + str(transaction.amount) + " " + transaction.amount.currency + " out to a " + transaction.recipient_type + " address"


if __name__ == '__main__':
    account = CoinbaseAccount(oauth2_credentials=TEMP_CREDENTIALS)
    do_coinbase_stuff(account=account)
########NEW FILE########
