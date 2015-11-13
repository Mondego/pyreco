__FILENAME__ = deactivate
#!/usr/bin/env python
"""The final rename and clear step for canceling an account.

If the account has a balance or is involved in active tips,
this script will report the problem and abort without making any update.

If the first eight digits of the account's API key are not given or do not match,
this script will report the problem and abort without making any update.

Usage:

    [gittip] $ heroku config -s -a gittip | foreman run -e /dev/stdin ./env/bin/python ./bin/deactivate.py "username" [first-eight-of-api-key]

"""
from __future__ import print_function

import sys

from gittip import wireup
from gittip.models.participant import Participant


username = sys.argv[1] # will fail with KeyError if missing
if len(sys.argv) < 3:
    first_eight = "unknown!"
else:
    first_eight = sys.argv[2]

db = wireup.db(wireup.env())


# Ensure that balance and tips have been dealt with.
# ==================================================

target = Participant.from_username(username)

INCOMING = """
        SELECT count(*)
          FROM current_tips
         WHERE tippee = %s
           AND amount > 0
"""

FIELDS = """
        SELECT username, username_lower, api_key, claimed_time
          FROM participants
         WHERE username = %s
"""

incoming = db.one(INCOMING, (username,))
fields = db.one(FIELDS, (username,))

print("Current balance ", target.balance)
print("Incoming tip count ", incoming)
print(fields)

assert target.balance == 0
assert incoming == 0
if fields.api_key == None:
    assert first_eight == "None"
else:
    assert fields.api_key[0:8] == first_eight


# Archive the participant record.
# ===============================

deactivated_name = "deactivated-" + username
print("Renaming " + username + " to " + deactivated_name)

RENAME = """
        UPDATE participants
           SET claimed_time = null
             , session_token = null
             , username = %s
             , username_lower = %s
         WHERE username = %s
"""

print(RENAME % (deactivated_name, deactivated_name.lower(), username))

db.run(RENAME, (deactivated_name, deactivated_name.lower(), username))

print("All done.")

########NEW FILE########
__FILENAME__ = final-gift
#!/usr/bin/env python
"""Distribute a balance as a final gift. This addresses part of #54.

Usage:

    [gittip] $ heroku config -s -a gittip | foreman run -e /dev/stdin ./env/bin/python ./bin/final-gift.py "username" [first-eight-of-api-key]

"""
from __future__ import print_function

import sys
from decimal import ROUND_DOWN, Decimal as D

from gittip import wireup
from gittip.models.participant import Participant
from gittip.exceptions import NegativeBalance

db = wireup.db(wireup.env())

username = sys.argv[1] # will fail with KeyError if missing
tipper = Participant.from_username(username)
if len(sys.argv) < 3:
    first_eight = "unknown!"
else:
    first_eight = sys.argv[2]

# Ensure user is legit
FIELDS = """
        SELECT username, username_lower, api_key, claimed_time
          FROM participants
         WHERE username = %s
"""

fields = db.one(FIELDS, (username,))
print(fields)

if fields.api_key == None:
    assert first_eight == "None"
else:
    assert fields.api_key[0:8] == first_eight

print("Distributing {} from {}.".format(tipper.balance, tipper.username))
if tipper.balance == 0:
    raise SystemExit

claimed_tips, claimed_total, unclaimed_tips, unclaimed_total = tipper.get_giving_for_profile()
transfers = []
distributed = D('0.00')

for tip in claimed_tips:
    if tip.amount == 0:
        continue
    rate = tip.amount / claimed_total
    pro_rated = (tipper.balance * rate).quantize(D('0.01'), ROUND_DOWN)
    distributed += pro_rated
    print( tipper.username.ljust(12)
         , tip.tippee.ljust(18)
         , str(tip.amount).rjust(6)
         , str(rate).ljust(32)
         , pro_rated
          )
    transfers.append([tip.tippee, pro_rated])

diff = tipper.balance - distributed
if diff != 0:
    print("Adjusting for rounding error of {}. Giving it to {}.".format(diff, transfers[0][0]))
    transfers[0][1] += diff  # Give it to the highest receiver.

with db.get_cursor() as cursor:
    for tippee, amount in transfers:
        assert amount > 0
        balance = cursor.one("""
            UPDATE participants
               SET balance = balance - %s
             WHERE username = %s
         RETURNING balance
        """, (amount, tipper.username))
        if balance < 0:
            raise NegativeBalance
        cursor.run( "UPDATE participants SET balance=balance + %s WHERE username=%s"
                  , (amount, tippee)
                   )
        cursor.run( "INSERT INTO transfers (tipper, tippee, amount) VALUES (%s, %s, %s)"
                  , (tipper.username, tippee, amount)
                   )

########NEW FILE########
__FILENAME__ = masspay
#!/usr/bin/env python
"""This is a script for managing MassPay each week.

Most of our payouts are handled by Balanced, but they're limited to people in
the U.S. We need to payout to people outside the U.S. (#126), and while we work
on a long-term solution, we are using PayPal. However, we've grown past the
point that PayPal's Instant Transfer feature is workable. This script is for
interfacing with PayPal's MassPay feature.

This script provides for:

  1. Computing an input CSV by hitting the Gittip database directly.
  2. Computing two output CSVs (one to upload to PayPal, the second to use for POSTing
      the exchanges back to Gittip)
  3. POSTing the exchanges back to Gittip via the HTTP API.

The idea is that you run steps 1 and 2, then run through the MassPay UI on the
PayPal website using the appropriate CSV from step 2, then run step 3.

"""
from __future__ import absolute_import, division, print_function, unicode_literals

import csv
import datetime
import getpass
import os
import sys
from decimal import Decimal as D, ROUND_HALF_UP

import requests
from httplib import IncompleteRead


os.chdir('../masspay')
ts = datetime.datetime.now().strftime('%Y-%m-%d')
INPUT_CSV = '{}.input.csv'.format(ts)
PAYPAL_CSV = '{}.output.paypal.csv'.format(ts)
GITTIP_CSV = '{}.output.gittip.csv'.format(ts)


def round_(d):
    return d.quantize(D('0.01'), rounding=ROUND_HALF_UP)

def print_rule(w=80):
    print("-" * w)


class Payee(object):
    username = None
    email = None
    gross = None
    gross_perc = None
    fee = None
    net = None
    additional_note = ""

    def __init__(self, rec):
        self.username, self.email, fee_cap, amount = rec
        self.gross = D(amount)
        self.fee = D(0)
        self.fee_cap = D(fee_cap)
        self.net = self.gross

    def assess_fee(self):

        # In order to avoid slowly leaking escrow, we need to be careful about
        # how we compute the fee. It's complicated, but it goes something like
        # this:
        #
        #   1. We want to pass PayPal's fees through to each payee.
        #
        #   2. With MassPay there is no option to have the receiver pay the fee,
        #       as there is with Instant Transfer.
        #
        #   3. We have to subtract the fee before uploading the spreadsheet
        #       to PayPal.
        #
        #   4. If we upload 15.24, PayPal upcharges to 15.54.
        #
        #   6. If we upload 15.25, PayPal upcharges to 15.56.
        #
        #   7. They only accept whole cents. We can't upload 15.245.
        #
        #   8. What if we want to hit 15.55?
        #
        #   9. We can't.
        #
        #  10. Our solution is to leave a penny behind in Gittip for
        #       affected payees.
        #
        #  11. BUT ... if we upload 1.25, PayPal upcharges to 1.28. Think about
        #       it.
        #
        # See also: https://github.com/gittip/www.gittip.com/issues/1673
        #           https://github.com/gittip/www.gittip.com/issues/2029
        #           https://github.com/gittip/www.gittip.com/issues/2198
        #           https://github.com/gittip/www.gittip.com/pull/2209
        #           https://github.com/gittip/www.gittip.com/issues/2296

        target = net = self.gross
        while 1:
            net -= D('0.01')
            fee = round_(net * D('0.02'))
            fee = min(fee, self.fee_cap)
            gross = net + fee
            if gross <= target:
                break
        self.gross = gross
        self.net = net
        self.fee = fee

        remainder = target - gross
        if remainder > 0:
            n = "{:.2} remaining due to PayPal rounding limitation.".format(remainder)
            self.additional_note = n

        return fee


def compute_input_csv():
    from gittip import wireup
    db = wireup.db(wireup.env())
    participants = db.all("""

        SELECT participants.*::participants
          FROM participants
         WHERE paypal_email IS NOT null
           AND balance > 0
      ORDER BY balance DESC

    """)
    writer = csv.writer(open(INPUT_CSV, 'w+'))
    print_rule(88)
    headers = "username", "email", "fee cap", "balance", "tips", "amount"
    print("{:<24}{:<32} {:^7} {:^7} {:^7} {:^7}".format(*headers))
    print_rule(88)
    total_gross = 0
    for participant in participants:
        tips, total = participant.get_tips_and_total(for_payday=False)
        amount = participant.balance - total
        if amount < 0.50:
            # Minimum payout of 50 cents. I think that otherwise PayPal upcharges to a penny.
            # See https://github.com/gittip/www.gittip.com/issues/1958.
            continue
        total_gross += amount
        print("{:<24}{:<32} {:>7} {:>7} {:>7} {:>7}".format( participant.username
                                                           , participant.paypal_email
                                                           , participant.paypal_fee_cap
                                                           , participant.balance
                                                           , total
                                                           , amount
                                                            ))
        row = (participant.username, participant.paypal_email, participant.paypal_fee_cap, amount)
        writer.writerow(row)
    print(" "*80, "-"*7)
    print("{:>88}".format(total_gross))


def compute_output_csvs():
    payees = [Payee(rec) for rec in csv.reader(open(INPUT_CSV))]
    payees.sort(key=lambda o: o.gross, reverse=True)

    total_fees = sum([payee.assess_fee() for payee in payees])  # side-effective!
    total_net = sum([p.net for p in payees])
    total_gross = sum([p.gross for p in payees])
    assert total_fees + total_net == total_gross

    paypal_csv = csv.writer(open(PAYPAL_CSV, 'w+'))
    gittip_csv = csv.writer(open(GITTIP_CSV, 'w+'))
    print_rule()
    print("{:<24}{:<32} {:^7} {:^7} {:^7}".format("username", "email", "gross", "fee", "net"))
    print_rule()
    for payee in payees:
        paypal_csv.writerow((payee.email, payee.net, "usd"))
        gittip_csv.writerow(( payee.username
                            , payee.email
                            , payee.gross
                            , payee.fee
                            , payee.net
                            , payee.additional_note
                             ))
        print("{username:<24}{email:<32} {gross:>7} {fee:>7} {net:>7}".format(**payee.__dict__))

    print(" "*56, "-"*23)
    print("{:>64} {:>7} {:>7}".format(total_gross, total_fees, total_net))


def post_back_to_gittip():

    try:
        gittip_api_key = os.environ['GITTIP_API_KEY']
    except KeyError:
        gittip_api_key = getpass.getpass("Gittip API key: ")

    try:
        gittip_base_url = os.environ['GITTIP_BASE_URL']
    except KeyError:
        gittip_base_url = 'https://www.gittip.com'

    for username, email, gross, fee, net, additional_note in csv.reader(open(GITTIP_CSV)):
        url = '{}/{}/history/record-an-exchange'.format(gittip_base_url, username)
        note = 'PayPal MassPay to {}.'.format(email)
        if additional_note:
            note += " " + additional_note
        print(note)

        data = {'amount': '-' + net, 'fee': fee, 'note': note}
        try:
            response = requests.post(url, auth=(gittip_api_key, ''), data=data)
        except IncompleteRead:
            print('IncompleteRead, proceeding (but double-check!)')
        else:
            if response.status_code != 200:
                if response.status_code == 404:
                    print('Got 404, is your API key good? {}'.format(gittip_api_key))
                else:
                    print('... resulted in a {} response:'.format(response.status_code))
                    print(response.text)
                raise SystemExit


def run_report():
    """Print a report to help Determine how much escrow we should store in PayPal.
    """
    totals = []
    max_masspay = max_weekly_growth = D(0)
    for filename in os.listdir('.'):
        if not filename.endswith('.input.csv'):
            continue

        datestamp = filename.split('.')[0]

        totals.append(D(0))
        for rec in csv.reader(open(filename)):
            amount = rec[-1]
            totals[-1] += D(amount)

        max_masspay = max(max_masspay, totals[-1])
        if len(totals) == 1:
            print("{} {:8}".format(datestamp, totals[-1]))
        else:
            weekly_growth = totals[-1] / totals[-2]
            max_weekly_growth = max(max_weekly_growth, weekly_growth)
            print("{} {:8} {:4.1f}".format(datestamp, totals[-1], weekly_growth))

    print()
    print("Max Withdrawal:    ${:9,.2f}".format(max_masspay))
    print("Max Weekly Growth:  {:8.1f}".format(max_weekly_growth))
    print("5x Current:        ${:9,.2f}".format(5 * totals[-1]))


def main():
    if not sys.argv[1:]:
        print("Looking for files for {} ...".format(ts))
        for filename in (INPUT_CSV, PAYPAL_CSV, GITTIP_CSV):
            print("  [{}] {}".format('x' if os.path.exists(filename) else ' ', filename))
        print("Rerun with one of these options:")
        print("  -i - hits db to generate input CSV (needs envvars via heroku + honcho)")
        print("  -o - computes output CSVs (doesn't need anything but input CSV)")
        print("  -p - posts back to Gittip (prompts for API key)")
    elif '-i' in sys.argv:
        compute_input_csv()
    elif '-o' in sys.argv:
        compute_output_csvs()
    elif '-p' in sys.argv:
        post_back_to_gittip()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print()

########NEW FILE########
__FILENAME__ = snapper
#!/usr/bin/env python
"""This is a command line utility for managing Gittip backups.

Running this script gets you a `snapper> ` prompt with commands to take backups
and load them locally. Backups are managed as *.psql files in ../backups/, and
they're loaded into a local gittip-bak database. Type 'help' or '?' at the
prompt for help.

"""
from __future__ import absolute_import, division, print_function, unicode_literals

import cmd
import os
import subprocess


class Snapper(cmd.Cmd):

    prompt = 'snapper> '
    root = '../backups'
    dbname = 'gittip-bak'

    def do_EOF(self, line):
        raise KeyboardInterrupt

    def do_quit(self, line):
        raise SystemExit
    do_exit = do_quit

    def do_new(self, line):
        """Take a new backup.
        """
        subprocess.call('./backup.sh')
    do_n = do_new

    def do_list(self, line):
        """List available backups.
        """
        filenames = self.get_filenames()
        for i, filename in enumerate(filenames):
            print('{:>2} {}'.format(i, filename[:-len('.psql')]))
    do_l = do_list

    def get_filenames(self):
        return sorted([f for f in os.listdir(self.root) if f.endswith('.psql')])

    def do_load(self, line):
        """Load a backup based on its number per `list`..
        """
        try:
            i = int(line)
            filename = self.get_filenames()[i]
        except (ValueError, KeyError):
            print('\x1b[31;1mBad backup number!\x1b[0m')
            print('\x1b[32;1mPick one of these:\x1b[0m')
            self.do_list('')
        else:
            if subprocess.call(['dropdb', self.dbname]) == 0:
                if subprocess.call(['createdb', self.dbname]) == 0:
                    subprocess.call( 'psql {} < {}/{}'.format(self.dbname, self.root, filename)
                                   , shell=True
                                    )


if __name__ == '__main__':
    try:
        Snapper().cmdloop()
    except KeyboardInterrupt:
        print()

########NEW FILE########
__FILENAME__ = untip
#!/usr/bin/env python
"""Zero out tips to a given user. This is a workaround for #1469.

Usage:

    [gittip] $ heroku config -s -a gittip | foreman run -e /dev/stdin ./env/bin/python ./scripts/untip.py "username"

"""
from __future__ import print_function

import sys

from gittip import wireup


tippee = sys.argv[1] # will fail with KeyError if missing

db = wireup.db(wireup.env())

tips = db.all("""

    SELECT amount
         , ( SELECT participants.*::participants
               FROM participants
              WHERE username=tipper
            ) AS tipper
         , ( SELECT participants.*::participants
               FROM participants
              WHERE username=tippee
            ) AS tippee
      FROM current_tips
     WHERE tippee = %s
       AND amount > 0
  ORDER BY amount DESC

""", (tippee,))


for tip in tips:
    print( tip.tipper.username.ljust(12)
         , tip.tippee.username.ljust(12)
         , str(tip.amount).rjust(6)
          )
    tip.tipper.set_tip_to(tip.tippee.username, '0.00')

########NEW FILE########
__FILENAME__ = update-user-info
#!/usr/bin/env python
"""This is a one-off script to update user_info for #1936.

This could be generalized for #900.

"""
from __future__ import absolute_import, division, print_function, unicode_literals
import os
import time
import sys

import requests
from gittip import wireup
from requests_oauthlib import OAuth1

db = wireup.db(wireup.env())

def update_twitter():
    oauth = OAuth1( os.environ['TWITTER_CONSUMER_KEY']
                , os.environ['TWITTER_CONSUMER_SECRET']
                , os.environ['TWITTER_ACCESS_TOKEN']
                , os.environ['TWITTER_ACCESS_TOKEN_SECRET']
                )
    elsewhere = db.all("SELECT user_id FROM ELSEWHERE WHERE platform='twitter' ORDER BY id;")
    url = "https://api.twitter.com/1.1/users/lookup.json"

    while elsewhere:
        batch = elsewhere[:100]
        elsewhere = elsewhere[100:]
        user_ids = ','.join([str(user_id) for user_id in batch])

        response = requests.post(url, data={'user_id': user_ids}, auth=oauth)


        # Log the rate-limit.
        # ===================

        nremaining = int(response.headers['X-RATE-LIMIT-REMAINING'])
        reset = int(response.headers['X-RATE-LIMIT-RESET'])
        print(nremaining, reset, time.time())


        if response.status_code != 200:

            # Who knows what happened?
            # ========================
            # Supposedly we shouldn't hit 429, at least.

            print(response.status_code, response.text)

        else:

            # Update!
            # =======

            users = response.json()

            with db.get_cursor() as c:

                for user_info in users:

                    # flatten per upsert method in gittip/elsewhere/__init__.py
                    for k, v in user_info.items():
                        user_info[k] = unicode(v)

                    user_id = user_info['id']

                    c.one("""
                        UPDATE elsewhere
                        SET user_info=%s
                        WHERE user_id=%s
                        AND platform='twitter'
                        RETURNING id
                    """, (user_info, user_id))

                    print("updated {} ({})".format(user_info['screen_name'], user_id))

                # find deleted users
                existing = set(u['id'] for u in users)
                deleted = existing - set(batch)

                for user_id in deleted:

                    c.one("""
                        UPDATE elsewhere
                        SET user_info=NULL
                        WHERE user_id=%s
                        AND platform='twitter'
                        RETURNING id
                    """, (user_id,))

                    print("orphan found: {}".format(user_id))


        # Stay under our rate limit.
        # =========================
        # We get 180 per 15 minutes for the users/lookup endpoint, per:
        #
        #   https://dev.twitter.com/docs/rate-limiting/1.1/limits

        sleep_for = 5
        if nremaining == 0:
            sleep_for = reset - time.time()
            sleep_for += 10  # Account for potential clock skew between us and Twitter.
        time.sleep(sleep_for)

def update_github():
    elsewhere = db.all("SELECT user_id FROM ELSEWHERE WHERE platform='github' ORDER BY id;")
    url = "https://api.github.com/user/%s"
    client_id = os.environ.get('GITHUB_CLIENT_ID')
    client_secret = os.environ.get('GITHUB_CLIENT_SECRET')

    for user_id in elsewhere:
        response = requests.get(url % user_id, params={
            'client_id': client_id,
            'client_secret': client_secret
        })

        # Log the rate-limit.
        # ===================

        nremaining = int(response.headers['X-RATELIMIT-REMAINING'])
        reset = int(response.headers['X-RATELIMIT-RESET'])
        # https://developer.github.com/v3/#rate-limiting
        now = time.time()
        print(nremaining, reset, now, reset-now, end=' ')

        status = response.status_code

        if status == 200:

            user_info = response.json()

            # flatten per upsert method in gittip/elsewhere/__init__.py
            for k, v in user_info.items():
                user_info[k] = unicode(v)

            assert user_id == user_info['id']

            db.one("""
                UPDATE elsewhere
                SET user_info=%s
                WHERE user_id=%s
                AND platform='github'
                RETURNING id
            """, (user_info, user_id))

            print("updated {} ({})".format(user_info['login'], user_id))

        elif status == 404:

            db.one("""
                UPDATE elsewhere
                SET user_info=NULL
                WHERE user_id=%s
                AND platform='github'
                RETURNING id
            """, (user_id,))

            print("orphan found: {}".format(user_id))
        else:
            # some other problem
            print(response.status_code, response.text)

        sleep_for = 0.5
        if nremaining == 0:
            sleep_for = reset - time.time()
            sleep_for += 10  # Account for potential clock skew between us and them
        time.sleep(sleep_for)

if __name__ == "__main__":
    if len(sys.argv) == 1:
        platform = raw_input("twitter or github?: ")
    else:
        platform = sys.argv[1]

    if platform == 'twitter':
        update_twitter()
    elif platform == 'github':
        update_github()

########NEW FILE########
__FILENAME__ = configure-aspen
from __future__ import division

import os
import sys
import threading
import time
import traceback

import gittip
import gittip.wireup
from gittip import canonize
from gittip.security import authentication, csrf, x_frame_options
from gittip.utils import cache_static, timer


from aspen import log_dammit


# Wireup Algorithm
# ================

version_file = os.path.join(website.www_root, 'version.txt')
website.version = open(version_file).read().strip()


website.renderer_default = "jinja2"

website.renderer_factories['jinja2'].Renderer.global_context = {
    'range': range,
    'unicode': unicode,
    'enumerate': enumerate,
    'len': len,
    'float': float,
    'type': type,
    'str': str
}


env = website.env = gittip.wireup.env()
gittip.wireup.canonical(env)
website.db = gittip.wireup.db(env)
website.mail = gittip.wireup.mail(env)
gittip.wireup.billing(env)
gittip.wireup.username_restrictions(website)
gittip.wireup.nanswers(env)
gittip.wireup.other_stuff(website, env)
gittip.wireup.accounts_elsewhere(website, env)
tell_sentry = gittip.wireup.make_sentry_teller(website)

# The homepage wants expensive queries. Let's periodically select into an
# intermediate table.

UPDATE_HOMEPAGE_EVERY = env.update_homepage_every
def update_homepage_queries():
    from gittip import utils
    while 1:
        try:
            utils.update_global_stats(website)
            utils.update_homepage_queries_once(website.db)
            website.db.self_check()
        except:
            exception = sys.exc_info()[0]
            tell_sentry(exception)
            tb = traceback.format_exc().strip()
            log_dammit(tb)
        time.sleep(UPDATE_HOMEPAGE_EVERY)

if UPDATE_HOMEPAGE_EVERY > 0:
    homepage_updater = threading.Thread(target=update_homepage_queries)
    homepage_updater.daemon = True
    homepage_updater.start()
else:
    from gittip import utils
    utils.update_global_stats(website)


# Server Algorithm
# ================

def up_minthreads(website):
    # https://github.com/gittip/www.gittip.com/issues/1098
    # Discovered the following API by inspecting in pdb and browsing source.
    # This requires network_engine.bind to have already been called.
    request_queue = website.network_engine.cheroot_server.requests
    request_queue.min = website.min_threads


def setup_busy_threads_logging(website):
    # https://github.com/gittip/www.gittip.com/issues/1572
    log_every = website.log_busy_threads_every
    if log_every == 0:
        return

    pool = website.network_engine.cheroot_server.requests
    def log_busy_threads():
        time.sleep(0.5)  # without this we get a single log message where all threads are busy
        while 1:

            # Use pool.min and not pool.max because of the semantics of these
            # inside of Cheroot. (Max is a hard limit used only when pool.grow
            # is called, and it's never called except when the pool starts up,
            # when it's called with pool.min.)

            nbusy_threads = pool.min - pool.idle
            print("sample#aspen.busy_threads={}".format(nbusy_threads))
            time.sleep(log_every)

    thread = threading.Thread(target=log_busy_threads)
    thread.daemon = True
    thread.start()


website.server_algorithm.insert_before('start', up_minthreads)
website.server_algorithm.insert_before('start', setup_busy_threads_logging)


# Website Algorithm
# =================

def add_stuff_to_context(request):
    request.context['username'] = None

def scab_body_onto_response(response):

    # This is a workaround for a Cheroot bug, where the connection is closed
    # too early if there is no body:
    #
    # https://bitbucket.org/cherrypy/cheroot/issue/1/fail-if-passed-zero-bytes
    #
    # This Cheroot bug is manifesting because of a change in Aspen's behavior
    # with the algorithm.py refactor in 0.27+: Aspen no longer sets a body for
    # 302s as it used to. This means that all redirects are breaking
    # intermittently (sometimes the client seems not to care that the
    # connection is closed too early, so I guess there's some timing
    # involved?), which is affecting a number of parts of Gittip, notably
    # around logging in (#1859).

    if not response.body:
        response.body = '*sigh*'


algorithm = website.algorithm
algorithm.functions = [ timer.start
                      , algorithm['parse_environ_into_request']
                      , algorithm['tack_website_onto_request']
                      , algorithm['raise_200_for_OPTIONS']

                      , canonize
                      , authentication.inbound
                      , csrf.inbound
                      , add_stuff_to_context

                      , algorithm['dispatch_request_to_filesystem']
                      , algorithm['apply_typecasters_to_path']

                      , cache_static.inbound

                      , algorithm['get_response_for_socket']
                      , algorithm['get_resource_for_request']
                      , algorithm['get_response_for_resource']

                      , tell_sentry
                      , algorithm['get_response_for_exception']

                      , gittip.outbound
                      , authentication.outbound
                      , csrf.outbound
                      , cache_static.outbound
                      , x_frame_options

                      , algorithm['log_traceback_for_5xx']
                      , algorithm['delegate_error_to_simplate']
                      , tell_sentry
                      , algorithm['log_traceback_for_exception']
                      , algorithm['log_result_of_request']

                      , scab_body_onto_response
                      , timer.end
                      , tell_sentry
                       ]

########NEW FILE########
__FILENAME__ = autolib
#!/usr/bin/env python
"""Generate *.rst files to mirror *.py files in a Python library.

This script is conceptually similar to the sphinx-apidoc script bundled with
Sphinx:

    http://sphinx-doc.org/man/sphinx-apidoc.html

We produce different *.rst output, however.

"""
from __future__ import print_function, unicode_literals
import os


w = lambda f, s, *a, **kw: print(s.format(*a, **kw), file=f)


def rst_for_module(toc_path):
    """Given a toc_path, write rst and return a file object.
    """

    f = open(toc_path + '.rst', 'w+')

    heading = ":mod:`{}`".format(os.path.basename(toc_path))
    dotted = toc_path.replace('/', '.')

    w(f, heading)
    w(f, "=" * len(heading))
    w(f, ".. automodule:: {}", dotted)

    return f


def rst_for_package(root, dirs, files):
    """Given ../mylib/path/to/package and lists of dir/file names, write rst.
    """

    doc_path = root[3:]
    if not os.path.isdir(doc_path):
        os.mkdir(doc_path)


    # Start a rst doc for this package.
    # =================================

    f = rst_for_module(doc_path)


    # Add a table of contents.
    # ========================

    w(f, ".. toctree::")

    def toc(doc_path, name):
        parent = os.path.dirname(doc_path)
        toc_path = os.path.join(doc_path[len(parent):].lstrip('/'), name)
        if toc_path.endswith('.py'):
            toc_path = toc_path[:-len('.py')]
        w(f, "    {}", toc_path)
        return os.path.join(parent, toc_path)

    for name in sorted(dirs + files):
        if name in dirs:
            toc(doc_path, name)
        else:
            if not name.endswith('.py'): continue
            if name == '__init__.py': continue

            toc_path = toc(doc_path, name)


            # Write a rst file for each module.
            # =================================

            rst_for_module(toc_path)


def main():
    library_root = os.environ['AUTOLIB_LIBRARY_ROOT']
    for root, dirs, files in os.walk(library_root):
        rst_for_package(root, dirs, files)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Gittip documentation build configuration file, created by
# sphinx-quickstart on Thu Aug  8 23:20:15 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.doctest', 'sphinx.ext.intersphinx', 'sphinx.ext.coverage', 'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Gittip'
copyright = u'2013, Gittip, LLC'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '-'
# The full version, including alpha/beta/rc tags.
release = '-'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


# -- Generate RST files -------------------------------------------------------

# We do this in here instead of in the Makefile so that RTD picks this up.
os.environ['AUTOLIB_LIBRARY_ROOT'] = '../gittip'
os.system("./autolib.py")


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'Gittipdoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Gittip.tex', u'Gittip Documentation',
   u'Gittip, LLC', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'gittip', u'Gittip Documentation',
     [u'Gittip, LLC'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'Gittip', u'Gittip Documentation',
   u'Gittip, LLC', 'Gittip', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#texinfo_no_detailmenu = False


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/': None}

autodoc_default_flags = ['members', 'member-order: bysource']

import mock

MOCK_MODULES = ['scipy', 'scipy.sparse']
for mod_name in MOCK_MODULES:
    sys.modules[mod_name] = mock.Mock()

########NEW FILE########
__FILENAME__ = payday
"""This is Gittip's payday algorithm. I would appreciate feedback on it.

The payday algorithm is designed to be crash-resistant and parallelizable, but
it's not eventually consistent in the strict sense (iinm) because consistency
is always apodeictically knowable.

Exchanges (moving money between Gittip and the outside world) and transfers
(moving money amongst Gittip users) happen within an isolated event called
payday. This event has duration (it's not punctiliar). It is started
transactionally, and it ends transactionally, and inside of it, exchanges and
transfers happen transactionally (though the link between our db and our
processor's db could be tightened up; see #213). Exchanges immediately affect
the participant's balance, but transfers accrue against a "pending" column in
the database. Once the payday event has completed successfully, it ends with
the pending column being applied to the balance column and reset to NULL in a
single transaction.

"""
from __future__ import unicode_literals

import sys
from decimal import Decimal, ROUND_UP

import balanced
import stripe
import aspen.utils
from aspen import log
from aspen.utils import typecheck
from gittip.models.participant import Participant
from gittip.exceptions import NegativeBalance
from psycopg2 import IntegrityError


# Set fees and minimums.
# ======================
# Balanced has a $0.50 minimum. We go even higher to avoid onerous
# per-transaction fees. See:
# https://github.com/gittip/www.gittip.com/issues/167 XXX I should maybe
# compute this using *ahem* math.

FEE_CHARGE = ( Decimal("0.30")   # $0.30
             , Decimal("0.029")  #  2.9%
              )
FEE_CREDIT = Decimal("0.00")    # Balanced doesn't actually charge us for this,
                                # because we were in the door early enough.

MINIMUM_CHARGE = Decimal("9.41")
MINIMUM_CREDIT = Decimal("10.00")


def upcharge(amount):
    """Given an amount, return a higher amount and the difference.
    """
    typecheck(amount, Decimal)
    charge_amount = (amount + FEE_CHARGE[0]) / (1 - FEE_CHARGE[1])
    charge_amount = charge_amount.quantize(FEE_CHARGE[0], rounding=ROUND_UP)
    return charge_amount, charge_amount - amount

def skim_credit(amount):
    """Given an amount, return a lower amount and the difference.
    """
    typecheck(amount, Decimal)
    return amount - FEE_CREDIT, FEE_CREDIT

assert upcharge(MINIMUM_CHARGE) == (Decimal('10.00'), Decimal('0.59'))


def is_whitelisted(participant):
    """Given a dict, return bool, possibly logging.

    We only perform credit card charges and bank deposits for whitelisted
    participants. We don't even include is_suspicious participants in the
    initial SELECT, so we should never see one here.

    """
    assert participant.is_suspicious is not True, participant.username
    if participant.is_suspicious is None:
        log("UNREVIEWED: %s" % participant.username)
        return False
    return True


class NoPayday(Exception):
    def __str__(self):
        return "No payday found where one was expected."


LOOP_PAYIN, LOOP_PACHINKO, LOOP_PAYOUT = range(3)


class Payday(object):
    """Represent an abstract event during which money is moved.

    On Payday, we want to use a participant's Gittip balance to settle their
    tips due (pulling in more money via credit card as needed), but we only
    want to use their balance at the start of Payday. Balance changes should be
    atomic globally per-Payday.

    """

    def __init__(self, db):
        """Takes a postgres.Postgres instance.
        """
        self.db = db


    def genparticipants(self, ts_start, loop):
        """Generator to yield participants with extra info.

        The extra info varies depending on which loop we're in: tips/total for
        payin and payout, takes for pachinko.

        """
        teams_only = (loop == LOOP_PACHINKO)
        for participant in self.get_participants(ts_start, teams_only):
            if loop == LOOP_PAYIN:
                extra = participant.get_tips_and_total(for_payday=ts_start)
            elif loop == LOOP_PACHINKO:
                extra = participant.get_takes(for_payday=ts_start)
            elif loop == LOOP_PAYOUT:

                # On the payout loop we want to use the total obligations they
                # have for next week, and if we pass a non-False for_payday to
                # get_tips_and_total then we only get unfulfilled tips from
                # prior to that timestamp, which is none of them by definition
                # at this point since we just recently finished payin.

                extra = participant.get_tips_and_total()
            else:
                raise Exception  # sanity check
            yield(participant, extra)


    def run(self):
        """This is the starting point for payday.

        This method runs every Thursday. It is structured such that it can be
        run again safely (with a newly-instantiated Payday object) if it
        crashes.

        """
        self.db.self_check()

        _start = aspen.utils.utcnow()
        log("Greetings, program! It's PAYDAY!!!!")
        ts_start = self.start()
        self.zero_out_pending(ts_start)

        self.payin(ts_start, self.genparticipants(ts_start, loop=LOOP_PAYIN))
        self.move_pending_to_balance_for_teams()
        self.pachinko(ts_start, self.genparticipants(ts_start, loop=LOOP_PACHINKO))
        self.clear_pending_to_balance()
        self.payout(ts_start, self.genparticipants(ts_start, loop=LOOP_PAYOUT))
        self.set_nactive(ts_start)

        self.end()

        self.db.self_check()

        _end = aspen.utils.utcnow()
        _delta = _end - _start
        fmt_past = "Script ran for {age} (%s)." % _delta

        # XXX For some reason newer versions of aspen use old string
        # formatting, so if/when we upgrade this will break. Why do we do that
        # in aspen, anyway?

        log(aspen.utils.to_age(_start, fmt_past=fmt_past))


    def start(self):
        """Try to start a new Payday.

        If there is a Payday that hasn't finished yet, then the UNIQUE
        constraint on ts_end will kick in and notify us of that. In that case
        we load the existing Payday and work on it some more. We use the start
        time of the current Payday to synchronize our work.

        """
        try:
            ts_start = self.db.one("INSERT INTO paydays DEFAULT VALUES "
                                   "RETURNING ts_start")
            log("Starting a new payday.")
        except IntegrityError:  # Collision, we have a Payday already.
            ts_start = self.db.one("""

                SELECT ts_start
                  FROM paydays
                 WHERE ts_end='1970-01-01T00:00:00+00'::timestamptz

            """)
            log("Picking up with an existing payday.")

        log("Payday started at %s." % ts_start)
        return ts_start


    def zero_out_pending(self, ts_start):
        """Given a timestamp, zero out the pending column.

        We keep track of balance changes as a result of Payday in the pending
        column, and then move them over to the balance column in one big
        transaction at the end of Payday.

        """
        START_PENDING = """\

            UPDATE participants
               SET pending=0.00
             WHERE pending IS NULL
               AND claimed_time < %s

        """
        self.db.run(START_PENDING, (ts_start,))
        log("Zeroed out the pending column.")
        return None


    def get_participants(self, ts_start, teams_only=False):
        """Given a timestamp, return a list of participants dicts.
        """
        PARTICIPANTS = """\
            SELECT participants.*::participants
              FROM participants
             WHERE claimed_time IS NOT NULL
               AND claimed_time < %s
               AND is_suspicious IS NOT true
               {}
          ORDER BY claimed_time ASC
        """.format(teams_only and "AND number = 'plural'" or '')
        participants = self.db.all(PARTICIPANTS, (ts_start,))
        log("Fetched participants.")
        return participants


    def payin(self, ts_start, participants):
        """Given a datetime and an iterator, do the payin side of Payday.
        """
        i = 0
        log("Starting payin loop.")
        for i, (participant, (tips, total)) in enumerate(participants, start=1):
            if i % 100 == 0:
                log("Payin done for %d participants." % i)
            self.charge_and_or_transfer(ts_start, participant, tips, total)
        log("Did payin for %d participants." % i)


    def pachinko(self, ts_start, participants):
        i = 0
        for i, (participant, takes) in enumerate(participants, start=1):
            if i % 100 == 0:
                log("Pachinko done for %d participants." % i)

            available = participant.balance
            log("Pachinko out from %s with $%s." % ( participant.username
                                                   , available
                                                    ))

            def tip(tippee, amount):
                tip = {}
                tip['tipper'] = participant.username
                tip['tippee'] = tippee
                tip['amount'] = amount
                tip['claimed_time'] = ts_start
                self.tip( participant
                        , tip
                        , ts_start
                        , pachinko=True
                         )

            for take in takes:
                amount = min(take['amount'], available)
                available -= amount
                tip(take['member'], amount)
                if available == 0:
                    break

        log("Did pachinko for %d participants." % i)


    def payout(self, ts_start, participants):
        """Given a datetime and an iterator, do the payout side of Payday.
        """
        i = 0
        log("Starting payout loop.")
        for i, (participant, (tips, total)) in enumerate(participants, start=1):
            if i % 100 == 0:
                log("Payout done for %d participants." % i)
            self.ach_credit(ts_start, participant, tips, total)
        log("Did payout for %d participants." % i)


    def charge_and_or_transfer(self, ts_start, participant, tips, total):
        """Given one participant record, pay their day.

        Charge each participants' credit card if needed before transfering
        money between Gittip accounts.

        """
        short = total - participant.balance
        if short > 0:

            # The participant's Gittip account is short the amount needed to
            # fund all their tips. Let's try pulling in money from their credit
            # card. If their credit card fails we'll forge ahead, in case they
            # have a positive Gittip balance already that can be used to fund
            # at least *some* tips. The charge method will have set
            # last_bill_result to a non-empty string if the card did fail.

            self.charge(participant, short)

        nsuccessful_tips = 0
        for tip in tips:
            result = self.tip(participant, tip, ts_start)
            if result >= 0:
                nsuccessful_tips += result
            else:
                break

        self.mark_participant(nsuccessful_tips)


    def move_pending_to_balance_for_teams(self):
        """Transfer pending into balance for teams.

        We do this because debit_participant operates against balance, not
        pending. This is because credit card charges go directly into balance
        on the first (payin) loop.

        """
        self.db.run("""\

            UPDATE participants
               SET balance = (balance + pending)
                 , pending = 0
             WHERE pending IS NOT NULL
               AND number='plural'

        """)
        # "Moved" instead of "cleared" because we don't also set to null.
        log("Moved pending to balance for teams. Ready for pachinko.")


    def clear_pending_to_balance(self):
        """Transfer pending into balance, setting pending to NULL.

        Any users that were created while the payin loop was running will have
        pending NULL (the default). If we try to add that to balance we'll get
        a NULL (0.0 + NULL = NULL), and balance has a NOT NULL constraint.
        Hence the where clause. See:

            https://github.com/gittip/www.gittip.com/issues/170

        """

        self.db.run("""\

            UPDATE participants
               SET balance = (balance + pending)
                 , pending = NULL
             WHERE pending IS NOT NULL

        """)
        # "Cleared" instead of "moved because we also set to null.
        log("Cleared pending to balance. Ready for payouts.")


    def set_nactive(self, ts_start):
        self.db.run("""\

            UPDATE paydays
               SET nactive=(
                    SELECT count(DISTINCT foo.*) FROM (
                        SELECT tipper FROM transfers WHERE "timestamp" >= %(ts_start)s
                            UNION
                        SELECT tippee FROM transfers WHERE "timestamp" >= %(ts_start)s
                    ) AS foo
                )
             WHERE ts_end='1970-01-01T00:00:00+00'::timestamptz

        """, {'ts_start': ts_start})

    def end(self):
        self.db.one("""\

            UPDATE paydays
               SET ts_end=now()
             WHERE ts_end='1970-01-01T00:00:00+00'::timestamptz
         RETURNING id

        """, default=NoPayday)


    # Move money between Gittip participants.
    # =======================================

    def tip(self, participant, tip, ts_start, pachinko=False):
        """Given dict, dict, and datetime, log and return int.

        Return values:

            | 0 if no valid tip available or tip has not been claimed
            | 1 if tip is valid
            | -1 if transfer fails and we cannot continue

        """
        msg = "$%s from %s to %s%s."
        msg %= ( tip['amount']
               , participant.username
               , tip['tippee']
               , " (pachinko)" if pachinko else ""
                )

        if tip['amount'] == 0:

            # The tips table contains a record for every time you click a tip
            # button. So if you click $0.25 then $3.00 then $0.00, that
            # generates three entries. We are looking at the last entry here,
            # and it's zero.

            return 0

        claimed_time = tip['claimed_time']
        if claimed_time is None or claimed_time > ts_start:

            # Gittip is opt-in. We're only going to collect money on a person's
            # behalf if they opted-in by claiming their account before the
            # start of this payday.

            log("SKIPPED: %s" % msg)
            return 0

        if not self.transfer(participant.username, tip['tippee'], \
                                             tip['amount'], pachinko=pachinko):

            # The transfer failed due to a lack of funds for the participant.
            # Don't try any further transfers.

            log("FAILURE: %s" % msg)
            return -1

        log("SUCCESS: %s" % msg)
        return 1


    def transfer(self, tipper, tippee, amount, pachinko=False):
        """Given two unicodes, a Decimal, and a boolean, return a boolean.

        If the tipper doesn't have enough in their Gittip account then we
        return False. Otherwise we decrement tipper's balance and increment
        tippee's *pending* balance by amount.

        """
        typecheck( tipper, unicode
                 , tippee, unicode
                 , amount, Decimal
                 , pachinko, bool
                  )
        with self.db.get_cursor() as cursor:

            try:
                self.debit_participant(cursor, tipper, amount)
            except NegativeBalance:
                return False

            self.credit_participant(cursor, tippee, amount)
            self.record_transfer(cursor, tipper, tippee, amount, pachinko)
            if pachinko:
                self.mark_pachinko(cursor, amount)
            else:
                self.mark_transfer(cursor, amount)

            return True


    def debit_participant(self, cursor, participant, amount):
        """Decrement the tipper's balance.
        """

        DECREMENT = """\

           UPDATE participants
              SET balance = (balance - %(amount)s)
            WHERE username = %(participant)s
              AND balance >= %(amount)s
        RETURNING pending

        """
        args = dict(amount=amount, participant=participant)
        r = cursor.one(DECREMENT, args, default=False)
        if r is False:
            raise NegativeBalance
        assert r is not None, (amount, participant)  # sanity check


    def credit_participant(self, cursor, participant, amount):
        """Increment the tippee's *pending* balance.

        The pending balance will clear to the balance proper when Payday is
        done.

        """

        INCREMENT = """\

           UPDATE participants
              SET pending=(pending + %s)
            WHERE username=%s
              AND pending IS NOT NULL
        RETURNING pending

        """
        cursor.execute(INCREMENT, (amount, participant))
        rec = cursor.fetchone()
        assert rec is not None, (participant, amount)  # sanity check


    # Move money between Gittip and the outside world.
    # ================================================

    def charge(self, participant, amount):
        """Given dict and Decimal, return None.

        This is the only place where we actually charge credit cards. Amount
        should be the nominal amount. We'll compute Gittip's fee below this
        function and add it to amount to end up with charge_amount.

        """
        typecheck(participant, Participant, amount, Decimal)

        username = participant.username
        balanced_customer_href = participant.balanced_customer_href
        stripe_customer_id = participant.stripe_customer_id

        typecheck( username, unicode
                 , balanced_customer_href, (unicode, None)
                 , stripe_customer_id, (unicode, None)
                  )


        # Perform some last-minute checks.
        # ================================

        if balanced_customer_href is None and stripe_customer_id is None:
            self.mark_missing_funding()
            return      # Participant has no funding source.

        if not is_whitelisted(participant):
            return      # Participant not trusted.


        # Go to Balanced or Stripe.
        # =========================

        if balanced_customer_href is not None:
            things = self.charge_on_balanced( username
                                            , balanced_customer_href
                                            , amount
                                             )
            charge_amount, fee, error = things
        else:
            assert stripe_customer_id is not None
            things = self.charge_on_stripe( username
                                          , stripe_customer_id
                                          , amount
                                           )
            charge_amount, fee, error = things

        amount = charge_amount - fee  # account for possible rounding under
                                      # charge_on_*

        self.record_charge( amount
                          , charge_amount
                          , fee
                          , error
                          , username
                           )


    def ach_credit(self, ts_start, participant, tips, total):

        # Compute the amount to credit them.
        # ==================================
        # Leave money in Gittip to cover their obligations next week (as these
        # currently stand). Also reduce the amount by our service fee.

        balance = participant.balance
        assert balance is not None, balance # sanity check
        amount = balance - total

        # Do some last-minute checks.
        # ===========================

        if amount <= 0:
            return      # Participant not owed anything.

        if amount < MINIMUM_CREDIT:
            also_log = ""
            if total > 0:
                also_log = " ($%s balance - $%s in obligations)"
                also_log %= (balance, total)
            log("Minimum payout is $%s. %s is only due $%s%s."
               % (MINIMUM_CREDIT, participant.username, amount, also_log))
            return      # Participant owed too little.

        if not is_whitelisted(participant):
            return      # Participant not trusted.


        # Do final calculations.
        # ======================

        credit_amount, fee = skim_credit(amount)
        cents = credit_amount * 100

        if total > 0:
            also_log = "$%s balance - $%s in obligations"
            also_log %= (balance, total)
        else:
            also_log = "$%s" % amount
        msg = "Crediting %s %d cents (%s - $%s fee = $%s) on Balanced ... "
        msg %= (participant.username, cents, also_log, fee, credit_amount)


        # Try to dance with Balanced.
        # ===========================

        try:
            balanced_customer_href = participant.balanced_customer_href
            if balanced_customer_href is None:
                log("%s has no balanced_customer_href."
                    % participant.username)
                return  # not in Balanced

            customer = balanced.Customer.fetch(balanced_customer_href)
            customer.bank_accounts.one()\
                                  .credit(amount=cents,
                                          description=participant.username)

            log(msg + "succeeded.")
            error = ""
        except balanced.exc.HTTPError as err:
            error = err.message.message
        except:
            error = repr(sys.exc_info()[1])

        if error:
            log(msg + "failed: %s" % error)

        self.record_credit(credit_amount, fee, error, participant.username)


    def charge_on_balanced(self, username, balanced_customer_href, amount):
        """We have a purported balanced_customer_href. Try to use it.
        """
        typecheck( username, unicode
                 , balanced_customer_href, unicode
                 , amount, Decimal
                  )

        cents, msg, charge_amount, fee = self._prep_hit(amount)
        msg = msg % (username, "Balanced")

        try:
            customer = balanced.Customer.fetch(balanced_customer_href)
            customer.cards.one().debit(amount=cents, description=username)
            log(msg + "succeeded.")
            error = ""
        except balanced.exc.HTTPError as err:
            error = err.message.message
        except:
            error = repr(sys.exc_info()[1])

        if error:
            log(msg + "failed: %s" % error)

        return charge_amount, fee, error


    def charge_on_stripe(self, username, stripe_customer_id, amount):
        """We have a purported stripe_customer_id. Try to use it.
        """
        typecheck( username, unicode
                 , stripe_customer_id, unicode
                 , amount, Decimal
                  )

        cents, msg, charge_amount, fee = self._prep_hit(amount)
        msg = msg % (username, "Stripe")

        try:
            stripe.Charge.create( customer=stripe_customer_id
                                , amount=cents
                                , description=username
                                , currency="USD"
                                 )
            log(msg + "succeeded.")
            error = ""
        except stripe.StripeError, err:
            error = err.message
            log(msg + "failed: %s" % error)

        return charge_amount, fee, error


    def _prep_hit(self, unrounded):
        """Takes an amount in dollars. Returns cents, etc.

        cents       This is passed to the payment processor charge API. This is
                    the value that is actually charged to the participant. It's
                    an int.
        msg         A log message with a couple %s to be filled in by the
                    caller.
        upcharged   Decimal dollar equivalent to `cents'.
        fee         Decimal dollar amount of the fee portion of `upcharged'.

        The latter two end up in the db in a couple places via record_charge.

        """
        also_log = ''
        rounded = unrounded
        if unrounded < MINIMUM_CHARGE:
            rounded = MINIMUM_CHARGE  # per github/#167
            also_log = ' [rounded up from $%s]' % unrounded

        upcharged, fee = upcharge(rounded)
        cents = int(upcharged * 100)

        msg = "Charging %%s %d cents ($%s%s + $%s fee = $%s) on %%s ... "
        msg %= cents, rounded, also_log, fee, upcharged

        return cents, msg, upcharged, fee


    # Record-keeping.
    # ===============

    def record_charge(self, amount, charge_amount, fee, error, username):
        """Given a Bunch of Stuff, return None.

        This function takes the result of an API call to a payment processor
        and records the result in our db. If the power goes out at this point
        then Postgres will be out of sync with the payment processor. We'll
        have to resolve that manually be reviewing the transaction log at the
        processor and modifying Postgres accordingly.

        For Balanced, this could be automated by generating an ID locally and
        commiting that to the db and then passing that through in the meta
        field.* Then syncing would be a case of simply::

            for payment in unresolved_payments:
                payment_in_balanced = balanced.Transaction.query.filter(
                  **{'meta.unique_id': 'value'}).one()
                payment.transaction_uri = payment_in_balanced.uri

        * https://www.balancedpayments.com/docs/meta

        """

        with self.db.get_cursor() as cursor:

            if error:
                last_bill_result = error
                amount = Decimal('0.00')
                self.mark_charge_failed(cursor)
            else:
                last_bill_result = ''
                EXCHANGE = """\

                        INSERT INTO exchanges
                               (amount, fee, participant)
                        VALUES (%s, %s, %s)

                """
                cursor.execute(EXCHANGE, (amount, fee, username))
                self.mark_charge_success(cursor, charge_amount, fee)


            # Update the participant's balance.
            # =================================
            # Credit card charges go immediately to balance, not to pending.

            RESULT = """\

            UPDATE participants
               SET last_bill_result=%s
                 , balance=(balance + %s)
             WHERE username=%s

            """
            cursor.execute(RESULT, (last_bill_result, amount, username))


    def record_credit(self, amount, fee, error, username):
        """Given a Bunch of Stuff, return None.

        Records in the exchanges table for credits have these characteristics:

            amount  It's negative, representing an outflow from Gittip to you.
                    This is oppositive of charges, where amount is positive.
                    The sign is how we differentiate the two in, e.g., the
                    history page.

            fee     It's positive, just like with charges.

        """
        credit = -amount  # From Gittip's POV this is money flowing out of the
                          # system.

        with self.db.get_cursor() as cursor:

            if error:
                last_ach_result = error
                credit = fee = Decimal('0.00')  # ensures balance won't change
                self.mark_ach_failed(cursor)
            else:
                last_ach_result = ''
                EXCHANGE = """\

                        INSERT INTO exchanges
                               (amount, fee, participant)
                        VALUES (%s, %s, %s)

                """
                cursor.execute(EXCHANGE, (credit, fee, username))
                self.mark_ach_success(cursor, amount, fee)


            # Update the participant's balance.
            # =================================

            RESULT = """\

            UPDATE participants
               SET last_ach_result=%s
                 , balance=(balance + %s)
             WHERE username=%s
         RETURNING balance

            """
            balance = cursor.one(RESULT, ( last_ach_result
                                         , credit - fee     # -10.00 - 0.30 = -10.30
                                         , username
                                          ))
            if balance < 0:
                raise NegativeBalance


    def record_transfer(self, cursor, tipper, tippee, amount, as_team_member=False):
        cursor.run("""\

          INSERT INTO transfers
                      (tipper, tippee, amount, as_team_member)
               VALUES (%s, %s, %s, %s)

        """, (tipper, tippee, amount, as_team_member))


    def mark_missing_funding(self):
        self.db.one("""\

            UPDATE paydays
               SET ncc_missing = ncc_missing + 1
             WHERE ts_end='1970-01-01T00:00:00+00'::timestamptz
         RETURNING id

        """, default=NoPayday)


    def mark_charge_failed(self, cursor):
        STATS = """\

            UPDATE paydays
               SET ncc_failing = ncc_failing + 1
             WHERE ts_end='1970-01-01T00:00:00+00'::timestamptz
         RETURNING id

        """
        cursor.execute(STATS)
        assert cursor.fetchone() is not None

    def mark_charge_success(self, cursor, amount, fee):
        STATS = """\

            UPDATE paydays
               SET ncharges = ncharges + 1
                 , charge_volume = charge_volume + %s
                 , charge_fees_volume = charge_fees_volume + %s
             WHERE ts_end='1970-01-01T00:00:00+00'::timestamptz
         RETURNING id

        """
        cursor.execute(STATS, (amount, fee))
        assert cursor.fetchone() is not None


    def mark_ach_failed(self, cursor):
        cursor.one("""\

            UPDATE paydays
               SET nach_failing = nach_failing + 1
             WHERE ts_end='1970-01-01T00:00:00+00'::timestamptz
         RETURNING id

        """, default=NoPayday)

    def mark_ach_success(self, cursor, amount, fee):
        cursor.one("""\

            UPDATE paydays
               SET nachs = nachs + 1
                 , ach_volume = ach_volume + %s
                 , ach_fees_volume = ach_fees_volume + %s
             WHERE ts_end='1970-01-01T00:00:00+00'::timestamptz
         RETURNING id

        """, (-amount, fee), default=NoPayday)


    def mark_transfer(self, cursor, amount):
        cursor.one("""\

            UPDATE paydays
               SET ntransfers = ntransfers + 1
                 , transfer_volume = transfer_volume + %s
             WHERE ts_end='1970-01-01T00:00:00+00'::timestamptz
         RETURNING id

        """, (amount,), default=NoPayday)


    def mark_pachinko(self, cursor, amount):
        cursor.one("""\

            UPDATE paydays
               SET npachinko = npachinko + 1
                 , pachinko_volume = pachinko_volume + %s
             WHERE ts_end='1970-01-01T00:00:00+00'::timestamptz
         RETURNING id

        """, (amount,), default=NoPayday)


    def mark_participant(self, nsuccessful_tips):
        self.db.one("""\

            UPDATE paydays
               SET nparticipants = nparticipants + 1
                 , ntippers = ntippers + %s
                 , ntips = ntips + %s
             WHERE ts_end='1970-01-01T00:00:00+00'::timestamptz
         RETURNING id

        """, ( 1 if nsuccessful_tips > 0 else 0
             , nsuccessful_tips  # XXX bug?
              ), default=NoPayday)

########NEW FILE########
__FILENAME__ = steady_state
# -*- coding: utf-8 -*-
#
# Written in 2013 by Roy Liu <carsomyr@gmail.com>
#
# To the extent possible under law, the author(s) have dedicated all copyright
# and related and neighboring rights to this software to the public domain
# worldwide. This software is distributed without any warranty.
#
# You should have received a copy of the CC0 Public Domain Dedication along with
# this software. If not, see
# <http://creativecommons.org/publicdomain/zero/1.0/>.

"""A library for computing the payday steady state. It owes its existence to the knotty problem of determining payouts
under situations where funds contain funds themselves, and when the payout graph contains cycles.
"""

__author__ = "Roy Liu <carsomyr@gmail.com>"

import sys
from scipy.sparse import csr_matrix
from scipy.sparse import eye
from scipy.sparse import issparse
from scipy.sparse import lil_matrix

class SteadyState:
    """Contains core functionality for computing the steady state payouts.
    """

    def __init__(self):
        """Default constructor.
        """

    @staticmethod
    def converge(payouts, epsilon = 1e-10, max_rounds = 100):
        """Computes the the payday steady state by iteratively building a geometric sum of the payout matrix. TODO: Use
        a sparse solver to compute the exact answer.

        Args:
            n_rounds: The number of payout rounds to run.

        Returns:
            Converges to the steady state.
        """
        if not issparse(payouts):
            raise ValueError("Please provide a sparse matrix")

        (n_rows, n_cols) = payouts.shape

        if n_rows != n_cols:
            raise ValueError("The payout matrix must be square")

        payouts_d = lil_matrix((n_rows, n_cols))
        payouts_d.setdiag(payouts.diagonal())
        payouts_d = payouts_d.tocsr()

        payouts_without_d = payouts.copy()
        payouts_without_d.setdiag([0] * n_rows)
        payouts_without_d = payouts_without_d.tocsr()

        payouts = payouts.tocsr()

        acc1 = csr_matrix((n_rows, n_cols))
        acc2 = eye(n_rows, n_cols)

        for _ in range(max_rounds):
            acc1 = acc1 + acc2
            acc2 = acc2 * payouts_without_d

            if acc2.sum() < epsilon:
                break

        if acc2.sum() >= epsilon:
            raise RuntimeError("The payout matrix failed to converge")

        return acc1 * payouts_d + acc2

def main():
    """The main method body.
    """
    payouts = lil_matrix((5, 5))
    payouts[0, 0:5] = [0, .8, .2,  0, 0]
    payouts[1, 0:5] = [0,  1,  0,  0, 0]
    payouts[2, 0:5] = [0, .9,  0, .1, 0]
    payouts[3, 0:5] = [0,  0,  0,  1, 0]
    payouts[4, 0:5] = [.1, .5, .2, .2, 0]

    initial = lil_matrix((1, 5))
    initial[0, 0:5] = [100, 0, 100, 0, 100]

    print(payouts.todense())
    print(initial.todense())
    print(initial * SteadyState.converge(payouts).todense())

#

if __name__ == "__main__":
    sys.exit(main())

########NEW FILE########
__FILENAME__ = cli
"""This is installed as `payday`.
"""
from gittip import wireup


def payday():

    # Wire things up.
    # ===============
    # Manually override max db connections so that we only have one connection.
    # Our db access is serialized right now anyway, and with only one
    # connection it's easier to trust changes to statement_timeout. The point
    # here is that we want to turn off statement_timeout for payday.

    env = wireup.env()
    env.database_maxconn = 1
    db = wireup.db(env)
    db.run("SET statement_timeout = 0")

    wireup.billing(env)
    wireup.nanswers(env)


    # Lazily import the billing module.
    # =================================
    # This dodges a problem where db in billing is None if we import it from
    # gittip before calling wireup.billing.

    from gittip.billing.payday import Payday

    try:
        Payday(db).run()
    except KeyboardInterrupt:
        pass
    except:
        import aspen
        import traceback
        aspen.log(traceback.format_exc())

########NEW FILE########
__FILENAME__ = bitbucket
from __future__ import absolute_import, division, print_function, unicode_literals

from gittip.elsewhere import PlatformOAuth1
from gittip.elsewhere._extractors import any_key, key, not_available
from gittip.elsewhere._paginators import keys_paginator


class Bitbucket(PlatformOAuth1):

    # Platform attributes
    name = 'bitbucket'
    display_name = 'Bitbucket'
    account_url = 'https://bitbucket.org/{user_name}'

    # Auth attributes
    auth_url = 'https://bitbucket.org/api/1.0'
    authorize_path = '/oauth/authenticate'

    # API attributes
    api_format = 'json'
    api_paginator = keys_paginator(prev='previous')
    api_url = 'https://bitbucket.org/api'
    api_user_info_path = '/1.0/users/{user_name}'
    api_user_self_info_path = '/1.0/user'
    api_team_members_path = '/2.0/teams/{user_name}/members'

    # User info extractors
    x_user_info = key('user')
    x_user_id = not_available  # No immutable id. :-/
    x_user_name = key('username')
    x_display_name = key('display_name')
    x_email = not_available
    x_avatar_url = any_key('avatar', ('links', 'avatar', 'href'))
    x_is_team = key('is_team')

########NEW FILE########
__FILENAME__ = bountysource
from __future__ import absolute_import, division, print_function, unicode_literals

from binascii import hexlify
import hashlib
import os
from time import time
from urllib import urlencode
from urlparse import parse_qs, urlparse

import requests

from aspen import Response
from gittip.elsewhere import Platform
from gittip.elsewhere._extractors import key, not_available


class Bountysource(Platform):

    # Platform attributes
    name = 'bountysource'
    display_name = 'Bountysource'
    account_url = '{platform_data.auth_url}/people/{user_id}'

    # API attributes
    api_format = 'json'
    api_user_info_path = '/users/{user_id}'
    api_user_self_info_path = '/user'

    # User info extractors
    x_user_id = key('id')
    x_user_name = not_available
    x_display_name = key('display_name')
    x_email = key('email')
    x_avatar_url = key('image_url')

    def get_auth_session(self, token=None):
        sess = requests.Session()
        sess.auth = BountysourceAuth(token)
        return sess

    def get_auth_url(self, user):
        query_id = hexlify(os.urandom(10))
        time_now = int(time())
        raw = '%s.%s.%s' % (user.participant.id, time_now, self.api_secret)
        h = hashlib.md5(raw).hexdigest()
        token = '%s.%s.%s' % (user.participant.id, time_now, h)
        params = dict(
            redirect_url=self.callback_url+'?query_id='+query_id,
            external_access_token=token
        )
        url = self.auth_url+'/auth/gittip/confirm?'+urlencode(params)
        return url, query_id, ''

    def get_query_id(self, querystring):
        token = querystring['access_token']
        i = token.rfind('.')
        data, data_hash = token[:i], token[i+1:]
        if data_hash != hashlib.md5(data+'.'+self.api_secret).hexdigest():
            raise Response(400, 'Invalid hash in access_token')
        return querystring['query_id']

    def get_user_self_info(self, sess):
        querystring = urlparse(sess._callback_url).query
        info = {k: v[0] if len(v) == 1 else v
                for k, v in parse_qs(querystring).items()}
        info.pop('access_token')
        info.pop('query_id')
        return self.extract_user_info(info)

    def handle_auth_callback(self, url, query_id, unused_arg):
        sess = self.get_auth_session(token=query_id)
        sess._callback_url=url
        return sess


class BountysourceAuth(object):

    def __init__(self, token=None):
        self.token = token

    def __call__(self, req):
        if self.token:
            req.params['access_token'] = self.token

########NEW FILE########
__FILENAME__ = github
from __future__ import absolute_import, division, print_function, unicode_literals

from gittip.elsewhere import PlatformOAuth2
from gittip.elsewhere._extractors import key
from gittip.elsewhere._paginators import header_links_paginator


class GitHub(PlatformOAuth2):

    # Platform attributes
    name = 'github'
    display_name = 'GitHub'
    account_url = 'https://github.com/{user_name}'
    allows_team_connect = True

    # Auth attributes
    auth_url = 'https://github.com/login/oauth'
    oauth_email_scope = 'user:email'
    oauth_default_scope = ['read:org']

    # API attributes
    api_format = 'json'
    api_paginator = header_links_paginator()
    api_url = 'https://api.github.com'
    api_user_info_path = '/users/{user_name}'
    api_user_self_info_path = '/user'
    api_team_members_path = '/orgs/{user_name}/public_members'
    ratelimit_headers_prefix = 'x-ratelimit-'

    # User info extractors
    x_user_id = key('id')
    x_user_name = key('login')
    x_display_name = key('name')
    x_email = key('email')
    x_gravatar_id = key('gravatar_id')
    x_avatar_url = key('avatar_url')
    x_is_team = key('type', clean=lambda t: t.lower() == 'organization')

    def is_team_admin(self, team_name, sess):
        user_teams = self.api_parser(self.api_get('/user/teams', sess=sess))
        return any(team.get('organization', {}).get('login') == team_name and
                   team.get('permission') == 'admin'
                   for team in user_teams)

########NEW FILE########
__FILENAME__ = openstreetmap
from __future__ import absolute_import, division, print_function, unicode_literals

from gittip.elsewhere import PlatformOAuth1
from gittip.elsewhere._extractors import not_available, xpath


class OpenStreetMap(PlatformOAuth1):

    # Platform attributes
    name = 'openstreetmap'
    display_name = 'OpenStreetMap'
    account_url = 'http://www.openstreetmap.org/user/{user_name}'

    # API attributes
    api_format = 'xml'
    api_user_info_path = '/user/{user_id}'
    api_user_self_info_path = '/user/details'

    # User info extractors
    x_user_id = xpath('./user', attr='id')
    x_user_name = xpath('./user', attr='display_name')
    x_display_name = x_user_name
    x_email = not_available
    x_avatar_url = xpath('./user/img', attr='href')

########NEW FILE########
__FILENAME__ = twitter
from __future__ import absolute_import, division, print_function, unicode_literals

from gittip.elsewhere import PlatformOAuth1
from gittip.elsewhere._extractors import key, not_available


class Twitter(PlatformOAuth1):

    # Platform attributes
    name = 'twitter'
    display_name = 'Twitter'
    account_url = 'https://twitter.com/{user_name}'

    # Auth attributes
    auth_url = 'https://api.twitter.com'

    # API attributes
    api_format = 'json'
    api_url = 'https://api.twitter.com/1.1'
    api_user_info_path = '/users/show.json?screen_name={user_name}'
    api_user_self_info_path = '/account/verify_credentials.json'
    ratelimit_headers_prefix = 'x-rate-limit-'

    # User info extractors
    x_user_id = key('id')
    x_user_name = key('screen_name')
    x_display_name = key('name')
    x_email = not_available
    x_avatar_url = key('profile_image_url_https',
                       clean=lambda v: v.replace('_normal.', '.'))

########NEW FILE########
__FILENAME__ = venmo
from __future__ import absolute_import, division, print_function, unicode_literals

from gittip.elsewhere import PlatformOAuth2
from gittip.elsewhere._extractors import key


class Venmo(PlatformOAuth2):

    # Platform attributes
    name = 'venmo'
    display_name = 'Venmo'
    account_url = 'https://venmo.com/{user_name}'

    # PlatformOAuth2 attributes
    auth_url = 'https://api.venmo.com/v1/oauth'
    oauth_email_scope = 'access_email'
    oauth_payment_scope = 'make_payments'
    oauth_default_scope = ['access_profile']

    # API attributes
    api_format = 'json'
    api_url = 'https://api.venmo.com/v1'
    api_user_info_path = '/users/{user_id}'
    api_user_self_info_path = '/me'

    # User info extractors
    x_user_info = key('data', clean=lambda d: d.pop('user', d))
    x_user_id = key('id')
    x_user_name = key('username')
    x_display_name = key('display_name')
    x_email = key('email')
    x_avatar_url = key('profile_picture_url')

########NEW FILE########
__FILENAME__ = _extractors
"""Helper functions to extract data from API responses
"""
from __future__ import unicode_literals

import json
from operator import getitem
import xml.etree.ElementTree as ET

from aspen import log


def _getitemchain(o, *keys):
    return reduce(getitem, keys, o)


def _popitemchain(obj, *keys):
    objs = [obj]
    for key in keys[:-1]:
        objs.append(objs[-1][key])
    r = objs[-1].pop(keys[-1])
    for o, k in reversed(list(zip(objs[:-1], keys[:-1]))):
        if len(o[k]) != 0:
            break
        o.pop(k)
    return r


def any_key(*keys, **kw):
    clean = kw.pop('clean', lambda a: a)
    def f(self, info, *default):
        for key in keys:
            chain = isinstance(key, basestring) and (key,) or key
            try:
                v = _getitemchain(info, *chain)
            except (KeyError, TypeError):
                continue
            if v:
                v = clean(v)
            if not v:
                continue
            _popitemchain(info, *chain)
            return v
        if default:
            return default[0]
        msg = 'Unable to find any of the keys %s in %s API response:\n%s'
        msg %= keys, self.name, json.dumps(info, indent=4)
        log(msg)
        raise KeyError(msg)
    return f


def key(k, clean=lambda a: a):
    def f(self, info, *default):
        try:
            v = info.pop(k, *default)
        except KeyError:
            msg = 'Unable to find key "%s" in %s API response:\n%s'
            log(msg % (k, self.name, json.dumps(info, indent=4)))
            raise
        if v:
            v = clean(v)
        if not v and not default:
            msg = 'Key "%s" has an empty value in %s API response:\n%s'
            msg %= (k, self.name, json.dumps(info, indent=4))
            log(msg)
            raise ValueError(msg)
        return v
    return f


def not_available(self, info, default):
    return default


def xpath(path, attr=None, clean=lambda a: a):
    def f(self, info, *default):
        try:
            l = info.findall(path)
            if len(l) > 1:
                msg = 'The xpath "%s" matches more than one element in %s API response:\n%s'
                msg %= (path, self.name, ET.tostring(info))
                log(msg)
                raise ValueError(msg)
            v = l[0].get(attr) if attr else l[0]
        except IndexError:
            if default:
                return default[0]
            msg = 'Unable to find xpath "%s" in %s API response:\n%s'
            msg %= (path, self.name, ET.tostring(info))
            log(msg)
            raise IndexError(msg)
        except KeyError:
            if default:
                return default[0]
            msg = 'The element has no "%s" attribute in %s API response:\n%s'
            msg %= (attr, self.name, ET.tostring(info))
            log(msg)
            raise KeyError(msg)
        if v:
            v = clean(v)
        if not v and not default:
            msg = 'The xpath "%s" points to an empty value in %s API response:\n%s'
            msg %= (path, self.name, ET.tostring(info))
            log(msg)
            raise ValueError(msg)
        return v
    return f

########NEW FILE########
__FILENAME__ = _paginators
"""Helper functions to handle pagination of API responses
"""
from __future__ import unicode_literals


def _relativize_urls(base, urls):
    i = len(base)
    r = {}
    for link_key, url in urls.items():
        if not url.startswith(base):
            raise ValueError('"%s" is not a prefix of "%s"' % (base, url))
        r[link_key] = url[i:]
    return r


links_keys = set('prev next first last'.split())


def header_links_paginator():
    def f(self, response, parsed):
        links = {k: v['url'] for k, v in response.links.items() if k in links_keys}
        total_count = -1 if links else len(parsed)
        return parsed, total_count, _relativize_urls(self.api_url, links)
    return f


def keys_paginator(**kw):
    page_key = kw.get('page', 'values')
    total_count_key = kw.get('total_count', 'size')
    links_keys_map = tuple((k, kw.get(k, k)) for k in links_keys)
    def f(self, response, parsed):
        page = parsed[page_key]
        links = {k: parsed[k2] for k, k2 in links_keys_map if parsed.get(k2)}
        total_count = parsed.get(total_count_key, -1) if links else len(page)
        return page, total_count, _relativize_urls(self.api_url, links)
    return f

########NEW FILE########
__FILENAME__ = exceptions
"""
This module contains exceptions shared across application code.
"""

from __future__ import print_function, unicode_literals


class ProblemChangingUsername(Exception):
    def __str__(self):
        return self.msg.format(self.args[0])

class UsernameIsEmpty(ProblemChangingUsername):
    msg = "You need to provide a username!"

class UsernameTooLong(ProblemChangingUsername):
    msg = "The username '{}' is too long."

class UsernameContainsInvalidCharacters(ProblemChangingUsername):
    msg = "The username '{}' contains invalid characters."

class UsernameIsRestricted(ProblemChangingUsername):
    msg = "The username '{}' is restricted."

class UsernameAlreadyTaken(ProblemChangingUsername):
    msg = "The username '{}' is already taken."


class ProblemChangingNumber(Exception):
    def __str__(self):
        return self.msg

class HasBigTips(ProblemChangingNumber):
    msg = "You receive tips too large for an individual. Please contact support@gittip.com."


class TooGreedy(Exception): pass
class NoSelfTipping(Exception): pass
class NoTippee(Exception): pass
class BadAmount(Exception): pass


class NegativeBalance(Exception):
    def __str__(self):
        return "Negative balance not allowed in this context."

########NEW FILE########
__FILENAME__ = account_elsewhere
from __future__ import absolute_import, division, print_function, unicode_literals

import json
from postgres.orm import Model
from psycopg2 import IntegrityError
from urlparse import urlsplit, urlunsplit
import xml.etree.ElementTree as ET
import xmltodict

from aspen import Response
from gittip.exceptions import ProblemChangingUsername
from gittip.utils.username import reserve_a_random_username


class UnknownAccountElsewhere(Exception): pass


class AccountElsewhere(Model):

    typname = "elsewhere_with_participant"

    def __init__(self, *args, **kwargs):
        super(AccountElsewhere, self).__init__(*args, **kwargs)
        self.platform_data = getattr(self.platforms, self.platform)


    # Constructors
    # ============

    @classmethod
    def from_user_id(cls, platform, user_id):
        """Return an existing AccountElsewhere based on platform and user_id.
        """
        return cls._from_thing('user_id', platform, user_id)

    @classmethod
    def from_user_name(cls, platform, user_name):
        """Return an existing AccountElsewhere based on platform and user_name.
        """
        return cls._from_thing('user_name', platform, user_name)

    @classmethod
    def _from_thing(cls, thing, platform, value):
        assert thing in ('user_id', 'user_name')
        exception = UnknownAccountElsewhere(thing, platform, value)
        return cls.db.one("""

            SELECT elsewhere.*::elsewhere_with_participant
              FROM elsewhere
             WHERE platform = %s
               AND {} = %s

        """.format(thing), (platform, value), default=exception)

    @classmethod
    def get_many(cls, platform, user_infos):
        accounts = cls.db.all("""\

            SELECT elsewhere.*::elsewhere_with_participant
              FROM elsewhere
             WHERE platform = %s
               AND user_id = any(%s)

        """, (platform, [i.user_id for i in user_infos]))
        found_user_ids = set(a.user_id for a in accounts)
        for i in user_infos:
            if i.user_id not in found_user_ids:
                accounts.append(cls.upsert(i))
        return accounts

    @classmethod
    def upsert(cls, i):
        """Insert or update a user's info.
        """

        # Clean up avatar_url
        if i.avatar_url:
            scheme, netloc, path, query, fragment = urlsplit(i.avatar_url)
            fragment = ''
            if netloc.endswith('githubusercontent.com') or \
               netloc.endswith('gravatar.com'):
                query = 's=128'
            i.avatar_url = urlunsplit((scheme, netloc, path, query, fragment))

        # Serialize extra_info
        if isinstance(i.extra_info, ET.Element):
            i.extra_info = xmltodict.parse(ET.tostring(i.extra_info))
        i.extra_info = json.dumps(i.extra_info)

        cols, vals = zip(*i.__dict__.items())
        cols = ', '.join(cols)
        placeholders = ', '.join(['%s']*len(vals))

        try:
            # Try to insert the account
            # We do this with a transaction so that if the insert fails, the
            # participant we reserved for them is rolled back as well.
            with cls.db.get_cursor() as cursor:
                username = reserve_a_random_username(cursor)
                cursor.execute("""
                    INSERT INTO elsewhere
                                (participant, {0})
                         VALUES (%s, {1})
                """.format(cols, placeholders), (username,)+vals)
                # Propagate elsewhere.is_team to participants.number
                if i.is_team:
                    cursor.execute("""
                        UPDATE participants
                           SET number = 'plural'::participant_number
                         WHERE username = %s
                    """, (username,))
        except IntegrityError:
            # The account is already in the DB, update it instead
            username = cls.db.one("""
                UPDATE elsewhere
                   SET ({0}) = ({1})
                 WHERE platform=%s AND user_id=%s
             RETURNING participant
            """.format(cols, placeholders), vals+(i.platform, i.user_id))
            if not username:
                raise

        # Return account after propagating avatar_url to participant
        account = AccountElsewhere.from_user_id(i.platform, i.user_id)
        account.participant.update_avatar()
        return account


    # Random Stuff
    # ============

    @property
    def html_url(self):
        return self.platform_data.account_url.format(
            user_id=self.user_id,
            user_name=self.user_name,
            platform_data=self.platform_data
        )

    def opt_in(self, desired_username):
        """Given a desired username, return a User object.
        """
        from gittip.security.user import User
        self.set_is_locked(False)
        user = User.from_username(self.participant.username)
        user.sign_in()
        assert not user.ANON, self.participant  # sanity check
        if self.participant.is_claimed:
            newly_claimed = False
        else:
            newly_claimed = True
            user.participant.set_as_claimed()
            try:
                user.participant.change_username(desired_username)
            except ProblemChangingUsername:
                pass
        return user, newly_claimed

    def save_token(self, token, refresh_token=None, expires=None):
        """Saves the given access token in the database.
        """
        self.db.run("""
            UPDATE elsewhere
               SET (access_token, refresh_token, expires) = (%s, %s, %s)
             WHERE id=%s
        """, (token, refresh_token, expires, self.id))
        self.set_attributes( access_token=token
                           , refresh_token=refresh_token
                           , expires=expires
                           )

    def set_is_locked(self, is_locked):
        self.db.run( 'UPDATE elsewhere SET is_locked=%s WHERE id=%s'
                   , (is_locked, self.id)
                   )
        self.set_attributes(is_locked=is_locked)


def get_account_elsewhere(request):
    path = request.line.uri.path
    platform = getattr(request.website.platforms, path['platform'], None)
    if platform is None:
        raise Response(404)
    user_name = path['user_name']
    try:
        account = AccountElsewhere.from_user_name(platform.name, user_name)
    except UnknownAccountElsewhere:
        account = AccountElsewhere.upsert(platform.get_user_info(user_name))
    return platform, account

########NEW FILE########
__FILENAME__ = community
import re

from postgres.orm import Model


name_pattern = re.compile(r'^[A-Za-z0-9,._ -]+$')

def slugize(slug):
    """Convert a string to a string for an URL.
    """
    assert name_pattern.match(slug) is not None
    slug = slug.lower()
    for c in (' ', ',', '.', '_'):
        slug = slug.replace(c, '-')
    while '--' in slug:
        slug = slug.replace('--', '-')
    slug = slug.strip('-')
    return slug


def slug_to_name(db, slug):
    """Given a slug like ``python``, return a name like ``Python``.

    :database: One SELECT, one row

    """
    SQL = "SELECT name FROM community_summary WHERE slug=%s"
    return db.one(SQL, (slug,))


def get_list_for(db, username):
    """Return a listing of communities.

    :database: One SELECT, multiple rows

    """
    if username is None:
        member_test = "false"
        sort_order = 'DESC'
        params = ()
    else:
        member_test = "bool_or(participant = %s)"
        sort_order = 'ASC'
        params = (username,)

    return db.all("""

        SELECT max(name) AS name
             , slug
             , count(*) AS nmembers
             , {} AS is_member
          FROM current_communities
      GROUP BY slug
      ORDER BY nmembers {}, slug

    """.format(member_test, sort_order), params)


class Community(Model):
    """Model a community on Gittip.
    """

    typname = "community_summary"

    def check_membership(self, participant):
        return self.db.one("""

        SELECT * FROM current_communities WHERE slug=%s AND participant=%s

        """, (self.slug, participant.username)) is not None

########NEW FILE########
__FILENAME__ = email_address_with_confirmation
from postgres.orm import Model


class EmailAddressWithConfirmation(Model):

    typname = "email_address_with_confirmation"

########NEW FILE########
__FILENAME__ = participant
"""*Participant* is the name Gittip gives to people and groups that are known
to Gittip. We've got a ``participants`` table in the database, and a
:py:class:`Participant` class that we define here. We distinguish several kinds
of participant, based on certain properties.

 - *Stub* participants
 - *Organizations* are plural participants
 - *Teams* are plural participants with members

"""
from __future__ import print_function, unicode_literals

import datetime
from decimal import Decimal
import uuid

from aspen.utils import typecheck
from postgres.orm import Model
from psycopg2 import IntegrityError
import pytz

import gittip
from gittip import NotSane
from gittip.exceptions import (
    HasBigTips,
    UsernameIsEmpty,
    UsernameTooLong,
    UsernameContainsInvalidCharacters,
    UsernameIsRestricted,
    UsernameAlreadyTaken,
    NoSelfTipping,
    NoTippee,
    BadAmount,
)

from gittip.models import add_event
from gittip.models._mixin_team import MixinTeam
from gittip.models.account_elsewhere import AccountElsewhere
from gittip.utils.username import gen_random_usernames, reserve_a_random_username
from gittip import billing
from gittip.utils import is_card_expiring


ASCII_ALLOWED_IN_USERNAME = set("0123456789"
                                "abcdefghijklmnopqrstuvwxyz"
                                "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                                ".,-_:@ ")
# We use | in Sentry logging, so don't make that allowable. :-)

NANSWERS_THRESHOLD = 0  # configured in wireup.py

NOTIFIED_ABOUT_EXPIRATION = b'notifiedAboutExpiration'

class Participant(Model, MixinTeam):
    """Represent a Gittip participant.
    """

    typname = 'participants'

    def __eq__(self, other):
        if not isinstance(other, Participant):
            return False
        return self.username == other.username

    def __ne__(self, other):
        if not isinstance(other, Participant):
            return False
        return self.username != other.username


    # Constructors
    # ============

    @classmethod
    def with_random_username(cls):
        """Return a new participant with a random username.
        """
        with cls.db.get_cursor() as cursor:
            username = reserve_a_random_username(cursor)
        return cls.from_username(username)

    @classmethod
    def from_id(cls, id):
        """Return an existing participant based on id.
        """
        return cls._from_thing("id", id)

    @classmethod
    def from_username(cls, username):
        """Return an existing participant based on username.
        """
        return cls._from_thing("username_lower", username.lower())

    @classmethod
    def from_session_token(cls, token):
        """Return an existing participant based on session token.
        """
        participant = cls._from_thing("session_token", token)
        if participant and participant.session_expires < pytz.utc.localize(datetime.datetime.utcnow()):
            participant = None

        return participant

    @classmethod
    def from_api_key(cls, api_key):
        """Return an existing participant based on API key.
        """
        return cls._from_thing("api_key", api_key)

    @classmethod
    def _from_thing(cls, thing, value):
        assert thing in ("id", "username_lower", "session_token", "api_key")
        return cls.db.one("""

            SELECT participants.*::participants
              FROM participants
             WHERE {}=%s

        """.format(thing), (value,))


    # Session Management
    # ==================

    def start_new_session(self):
        """Set ``session_token`` in the database to a new uuid.

        :database: One UPDATE, one row

        """
        self._update_session_token(uuid.uuid4().hex)

    def end_session(self):
        """Set ``session_token`` in the database to ``NULL``.

        :database: One UPDATE, one row

        """
        self._update_session_token(None)

    def _update_session_token(self, new_token):
        self.db.run( "UPDATE participants SET session_token=%s "
                     "WHERE id=%s AND is_suspicious IS NOT true"
                   , (new_token, self.id,)
                    )
        self.set_attributes(session_token=new_token)

    def set_session_expires(self, expires):
        """Set session_expires in the database.

        :param float expires: A UNIX timestamp, which XXX we assume is UTC?
        :database: One UPDATE, one row

        """
        session_expires = datetime.datetime.fromtimestamp(expires) \
                                                      .replace(tzinfo=pytz.utc)
        self.db.run( "UPDATE participants SET session_expires=%s "
                     "WHERE id=%s AND is_suspicious IS NOT true"
                   , (session_expires, self.id,)
                    )
        self.set_attributes(session_expires=session_expires)


    # Claimed-ness
    # ============

    @property
    def is_claimed(self):
        return self.claimed_time is not None


    # Number
    # ======

    @property
    def IS_SINGULAR(self):
        return self.number == 'singular'

    @property
    def IS_PLURAL(self):
        return self.number == 'plural'

    def update_number(self, number):
        assert number in ('singular', 'plural')
        if number == 'singular':
            nbigtips = self.db.one("""\
                SELECT count(*) FROM current_tips WHERE tippee=%s AND amount > %s
            """, (self.username, gittip.MAX_TIP_SINGULAR))
            if nbigtips > 0:
                raise HasBigTips
        self.db.run( "UPDATE participants SET number=%s WHERE id=%s"
                   , (number, self.id)
                    )
        self.set_attributes(number=number)


    # Statement
    # =========

    def update_statement(self, statement):
        self.db.run("UPDATE participants SET statement=%s WHERE id=%s", (statement, self.id))
        self.set_attributes(statement=statement)


    # API Key
    # =======

    def recreate_api_key(self):
        api_key = str(uuid.uuid4())
        SQL = "UPDATE participants SET api_key=%s WHERE username=%s"
        with self.db.get_cursor() as c:
            add_event(c, 'participant', dict(action='set', id=self.id, values=dict(api_key=api_key)))
            c.run(SQL, (api_key, self.username))
        return api_key


    # Claiming
    # ========
    # An unclaimed Participant is a stub that's created when someone pledges to
    # give to an AccountElsewhere that's not been connected on Gittip yet.

    def resolve_unclaimed(self):
        """Given a username, return an URL path.
        """
        rec = self.db.one( "SELECT platform, user_name "
                           "FROM elsewhere "
                           "WHERE participant = %s"
                           , (self.username,)
                            )
        if rec is None:
            return
        return '/on/%s/%s/' % (rec.platform, rec.user_name)

    def set_as_claimed(self):
        with self.db.get_cursor() as c:
            add_event(c, 'participant', dict(id=self.id, action='claim'))
            claimed_time = c.one("""\

                UPDATE participants
                   SET claimed_time=CURRENT_TIMESTAMP
                 WHERE username=%s
                   AND claimed_time IS NULL
             RETURNING claimed_time

            """, (self.username,))
            self.set_attributes(claimed_time=claimed_time)



    # Random Junk
    # ===========

    def get_teams(self):
        """Return a list of teams this user is a member of.
        """
        return self.db.all("""

            SELECT team AS name
                 , ( SELECT count(*)
                       FROM current_takes
                      WHERE team=x.team
                    ) AS nmembers
              FROM current_takes x
             WHERE member=%s;

        """, (self.username,))

    @property
    def accepts_tips(self):
        return (self.goal is None) or (self.goal >= 0)


    def insert_into_communities(self, is_member, name, slug):
        username = self.username
        self.db.run("""

            INSERT INTO communities
                        (ctime, name, slug, participant, is_member)
                 VALUES ( COALESCE (( SELECT ctime
                                        FROM communities
                                       WHERE (participant=%s AND slug=%s)
                                       LIMIT 1
                                      ), CURRENT_TIMESTAMP)
                        , %s, %s, %s, %s
                         )
              RETURNING ( SELECT count(*) = 0
                            FROM communities
                           WHERE participant=%s
                         )
                     AS first_time_community

        """, (username, slug, name, slug, username, is_member, username))


    def change_username(self, suggested):
        """Raise Response or return None.

        Usernames are limited to alphanumeric characters, plus ".,-_:@ ",
        and can only be 32 characters long.

        """
        # TODO: reconsider allowing unicode usernames
        suggested = suggested.strip()

        if not suggested:
            raise UsernameIsEmpty(suggested)

        if len(suggested) > 32:
            raise UsernameTooLong(suggested)

        if set(suggested) - ASCII_ALLOWED_IN_USERNAME:
            raise UsernameContainsInvalidCharacters(suggested)

        lowercased = suggested.lower()

        if lowercased in gittip.RESTRICTED_USERNAMES:
            raise UsernameIsRestricted(suggested)

        if suggested != self.username:
            try:
                # Will raise IntegrityError if the desired username is taken.
                with self.db.get_cursor(back_as=tuple) as c:
                    add_event(c, 'participant', dict(id=self.id, action='set', values=dict(username=suggested)))
                    actual = c.one( "UPDATE participants "
                                    "SET username=%s, username_lower=%s "
                                    "WHERE username=%s "
                                    "RETURNING username, username_lower"
                                   , (suggested, lowercased, self.username)
                                   )
            except IntegrityError:
                raise UsernameAlreadyTaken(suggested)

            assert (suggested, lowercased) == actual # sanity check
            self.set_attributes(username=suggested, username_lower=lowercased)

        return suggested

    def update_avatar(self):
        avatar_url = self.db.run("""
            UPDATE participants p
               SET avatar_url = (
                       SELECT avatar_url
                         FROM elsewhere
                        WHERE participant = p.username
                     ORDER BY platform = 'github' DESC,
                              avatar_url LIKE '%%gravatar.com%%' DESC
                        LIMIT 1
                   )
             WHERE p.username = %s
         RETURNING avatar_url
        """, (self.username,))
        self.set_attributes(avatar_url=avatar_url)

    def update_email(self, email, confirmed=False):
        with self.db.get_cursor() as c:
            add_event(c, 'participant', dict(id=self.id, action='set', values=dict(current_email=email)))
            c.one("UPDATE participants SET email = ROW(%s, %s) WHERE username=%s RETURNING id"
                 , (email, confirmed, self.username)
                  )
        self.set_attributes(email=(email, confirmed))

    def update_goal(self, goal):
        typecheck(goal, (Decimal, None))
        with self.db.get_cursor() as c:
            tmp = goal if goal is None else unicode(goal)
            add_event(c, 'participant', dict(id=self.id, action='set', values=dict(goal=tmp)))
            c.one( "UPDATE participants SET goal=%s WHERE username=%s RETURNING id"
                 , (goal, self.username)
                  )
        self.set_attributes(goal=goal)


    def set_tip_to(self, tippee, amount):
        """Given participant id and amount as str, return a tuple.

        We INSERT instead of UPDATE, so that we have history to explore. The
        COALESCE function returns the first of its arguments that is not NULL.
        The effect here is to stamp all tips with the timestamp of the first
        tip from this user to that. I believe this is used to determine the
        order of transfers during payday.

        The tuple returned is the amount as a Decimal and a boolean indicating
        whether this is the first time this tipper has tipped (we want to track
        that as part of our conversion funnel).

        """

        if self.username == tippee:
            raise NoSelfTipping

        tippee = Participant.from_username(tippee)
        if tippee is None:
            raise NoTippee

        amount = Decimal(amount)  # May raise InvalidOperation
        max_tip = gittip.MAX_TIP_PLURAL if tippee.IS_PLURAL else gittip.MAX_TIP_SINGULAR
        if (amount < gittip.MIN_TIP) or (amount > max_tip):
            raise BadAmount

        NEW_TIP = """\

            INSERT INTO tips
                        (ctime, tipper, tippee, amount)
                 VALUES ( COALESCE (( SELECT ctime
                                        FROM tips
                                       WHERE (tipper=%s AND tippee=%s)
                                       LIMIT 1
                                      ), CURRENT_TIMESTAMP)
                        , %s, %s, %s
                         )
              RETURNING ( SELECT count(*) = 0 FROM tips WHERE tipper=%s )
                     AS first_time_tipper

        """
        args = (self.username, tippee.username, self.username, tippee.username, amount, \
                                                                                     self.username)
        first_time_tipper = self.db.one(NEW_TIP, args)
        return amount, first_time_tipper


    def get_tip_to(self, tippee):
        """Given two user ids, return a Decimal.
        """
        return self.db.one("""\

            SELECT amount
              FROM tips
             WHERE tipper=%s
               AND tippee=%s
          ORDER BY mtime DESC
             LIMIT 1

        """, (self.username, tippee), default=Decimal('0.00'))


    def get_dollars_receiving(self):
        """Return a Decimal.
        """
        return self.db.one("""\

            SELECT sum(amount)
              FROM ( SELECT DISTINCT ON (tipper)
                            amount
                          , tipper
                       FROM tips
                       JOIN participants p ON p.username = tipper
                      WHERE tippee=%s
                        AND last_bill_result = ''
                        AND is_suspicious IS NOT true
                   ORDER BY tipper
                          , mtime DESC
                    ) AS foo

        """, (self.username,), default=Decimal('0.00'))


    def get_dollars_giving(self):
        """Return a Decimal.
        """
        return self.db.one("""\

            SELECT sum(amount)
              FROM ( SELECT DISTINCT ON (tippee)
                            amount
                          , tippee
                       FROM tips
                       JOIN participants p ON p.username = tippee
                      WHERE tipper=%s
                        AND is_suspicious IS NOT true
                        AND claimed_time IS NOT NULL
                   ORDER BY tippee
                          , mtime DESC
                    ) AS foo

        """, (self.username,), default=Decimal('0.00'))


    def get_number_of_backers(self):
        """Given a unicode, return an int.
        """
        return self.db.one("""\

            SELECT count(amount)
              FROM ( SELECT DISTINCT ON (tipper)
                            amount
                          , tipper
                       FROM tips
                       JOIN participants p ON p.username = tipper
                      WHERE tippee=%s
                        AND last_bill_result = ''
                        AND is_suspicious IS NOT true
                   ORDER BY tipper
                          , mtime DESC
                    ) AS foo
             WHERE amount > 0

        """, (self.username,), default=0)


    def get_tip_distribution(self):
        """
            Returns a data structure in the form of::

                [
                    [TIPAMOUNT1, TIPAMOUNT2...TIPAMOUNTN],
                    total_number_patrons_giving_to_me,
                    total_amount_received
                ]

            where each TIPAMOUNTN is in the form::

                [
                    amount,
                    number_of_tippers_for_this_amount,
                    total_amount_given_at_this_amount,
                    proportion_of_tips_at_this_amount,
                    proportion_of_total_amount_at_this_amount
                ]

        """
        SQL = """

            SELECT amount
                 , count(amount) AS ncontributing
              FROM ( SELECT DISTINCT ON (tipper)
                            amount
                          , tipper
                       FROM tips
                       JOIN participants p ON p.username = tipper
                      WHERE tippee=%s
                        AND last_bill_result = ''
                        AND is_suspicious IS NOT true
                   ORDER BY tipper
                          , mtime DESC
                    ) AS foo
             WHERE amount > 0
          GROUP BY amount
          ORDER BY amount

        """

        tip_amounts = []

        npatrons = 0.0  # float to trigger float division
        contributed = Decimal('0.00')
        for rec in self.db.all(SQL, (self.username,)):
            tip_amounts.append([ rec.amount
                               , rec.ncontributing
                               , rec.amount * rec.ncontributing
                                ])
            contributed += tip_amounts[-1][2]
            npatrons += rec.ncontributing

        for row in tip_amounts:
            row.append((row[1] / npatrons) if npatrons > 0 else 0)
            row.append((row[2] / contributed) if contributed > 0 else 0)

        return tip_amounts, npatrons, contributed


    def get_giving_for_profile(self):
        """Given a participant id and a date, return a list and a Decimal.

        This function is used to populate a participant's page for their own
        viewing pleasure.

        """

        TIPS = """\

            SELECT * FROM (
                SELECT DISTINCT ON (tippee)
                       amount
                     , tippee
                     , t.ctime
                     , p.claimed_time
                     , p.username_lower
                     , p.number
                  FROM tips t
                  JOIN participants p ON p.username = t.tippee
                 WHERE tipper = %s
                   AND p.is_suspicious IS NOT true
                   AND p.claimed_time IS NOT NULL
              ORDER BY tippee
                     , t.mtime DESC
            ) AS foo
            ORDER BY amount DESC
                   , username_lower

        """
        tips = self.db.all(TIPS, (self.username,))

        UNCLAIMED_TIPS = """\

            SELECT * FROM (
                SELECT DISTINCT ON (tippee)
                       amount
                     , tippee
                     , t.ctime
                     , p.claimed_time
                     , e.platform
                     , e.user_name
                  FROM tips t
                  JOIN participants p ON p.username = t.tippee
                  JOIN elsewhere e ON e.participant = t.tippee
                 WHERE tipper = %s
                   AND p.is_suspicious IS NOT true
                   AND p.claimed_time IS NULL
              ORDER BY tippee
                     , t.mtime DESC
            ) AS foo
            ORDER BY amount DESC
                   , lower(user_name)

        """
        unclaimed_tips = self.db.all(UNCLAIMED_TIPS, (self.username,))


        # Compute the total.
        # ==================
        # For payday we only want to process payments to tippees who have
        # themselves opted into Gittip. For the tipper's profile page we want
        # to show the total amount they've pledged (so they're not surprised
        # when someone *does* start accepting tips and all of a sudden they're
        # hit with bigger charges.

        total = sum([t.amount for t in tips])
        if not total:
            # If tips is an empty list, total is int 0. We want a Decimal.
            total = Decimal('0.00')

        unclaimed_total = sum([t.amount for t in unclaimed_tips])
        if not unclaimed_total:
            unclaimed_total = Decimal('0.00')

        return tips, total, unclaimed_tips, unclaimed_total


    def get_tips_and_total(self, for_payday=False):
        """Given a participant id and a date, return a list and a Decimal.

        This function is used by the payday function. If for_payday is not
        False it must be a date object. Originally we also used this function
        to populate the profile page, but our requirements there changed while,
        oddly, our requirements in payday *also* changed to match the old
        requirements of the profile page. So this function keeps the for_payday
        parameter after all.

        """

        if for_payday:

            # For payday we want the oldest relationship to be paid first.
            order_by = "ctime ASC"


            # This is where it gets crash-proof.
            # ==================================
            # We need to account for the fact that we may have crashed during
            # Payday and we're re-running that function. We only want to select
            # tips that existed before Payday started, but haven't been
            # processed as part of this Payday yet.
            #
            # It's a bug if the paydays subselect returns > 1 rows.
            #
            # XXX If we crash during Payday and we rerun it after a timezone
            # change, will we get burned? How?

            ts_filter = """\

                   AND mtime < %s
                   AND ( SELECT id
                           FROM transfers
                          WHERE tipper=t.tipper
                            AND tippee=t.tippee
                            AND timestamp >= %s
                        ) IS NULL

            """
            args = (self.username, for_payday, for_payday)
        else:
            order_by = "amount DESC"
            ts_filter = ""
            args = (self.username,)

        TIPS = """\

            SELECT * FROM (
                SELECT DISTINCT ON (tippee)
                       amount
                     , tippee
                     , t.ctime
                     , p.claimed_time
                  FROM tips t
                  JOIN participants p ON p.username = t.tippee
                 WHERE tipper = %%s
                   AND p.is_suspicious IS NOT true
                   %s
              ORDER BY tippee
                     , t.mtime DESC
            ) AS foo
            ORDER BY %s
                   , tippee

        """ % (ts_filter, order_by)  # XXX, No injections here, right?!
        tips = self.db.all(TIPS, args, back_as=dict)


        # Compute the total.
        # ==================
        # For payday we only want to process payments to tippees who have
        # themselves opted into Gittip. For the tipper's profile page we want
        # to show the total amount they've pledged (so they're not surprised
        # when someone *does* start accepting tips and all of a sudden they're
        # hit with bigger charges.

        if for_payday:
            to_total = [t for t in tips if t['claimed_time'] is not None]
        else:
            to_total = tips
        total = sum([t['amount'] for t in to_total], Decimal('0.00'))

        return tips, total


    def get_og_title(self):
        out = self.username
        receiving = self.get_dollars_receiving()
        giving = self.get_dollars_giving()
        if (giving > receiving) and not self.anonymous_giving:
            out += " gives $%.2f/wk" % giving
        elif receiving > 0 and not self.anonymous_receiving:
            out += " receives $%.2f/wk" % receiving
        else:
            out += " is"
        return out + " on Gittip"


    def get_age_in_seconds(self):
        out = -1
        if self.claimed_time is not None:
            now = datetime.datetime.now(self.claimed_time.tzinfo)
            out = (now - self.claimed_time).total_seconds()
        return out


    def get_accounts_elsewhere(self):
        """Return a dict of AccountElsewhere instances.
        """
        accounts = self.db.all("""

            SELECT elsewhere.*::elsewhere_with_participant
              FROM elsewhere
             WHERE participant=%s

        """, (self.username,))
        accounts_dict = {account.platform: account for account in accounts}
        return accounts_dict


    def take_over(self, account, have_confirmation=False):
        """Given an AccountElsewhere or a tuple (platform_name, user_id),
        associate an elsewhere account.

        Returns None or raises NeedConfirmation.

        This method associates an account on another platform (GitHub, Twitter,
        etc.) with the given Gittip participant. Every account elsewhere has an
        associated Gittip participant account, even if its only a stub
        participant (it allows us to track pledges to that account should they
        ever decide to join Gittip).

        In certain circumstances, we want to present the user with a
        confirmation before proceeding to transfer the account elsewhere to
        the new Gittip account; NeedConfirmation is the signal to request
        confirmation. If it was the last account elsewhere connected to the old
        Gittip account, then we absorb the old Gittip account into the new one,
        effectively archiving the old account.

        Here's what absorbing means:

            - consolidated tips to and fro are set up for the new participant

                Amounts are summed, so if alice tips bob $1 and carl $1, and
                then bob absorbs carl, then alice tips bob $2(!) and carl $0.

                And if bob tips alice $1 and carl tips alice $1, and then bob
                absorbs carl, then bob tips alice $2(!) and carl tips alice $0.

                The ctime of each new consolidated tip is the older of the two
                tips that are being consolidated.

                If alice tips bob $1, and alice absorbs bob, then alice tips
                bob $0.

                If alice tips bob $1, and bob absorbs alice, then alice tips
                bob $0.

            - all tips to and from the other participant are set to zero
            - the absorbed username is released for reuse
            - the absorption is recorded in an absorptions table

        This is done in one transaction.
        """

        if isinstance(account, AccountElsewhere):
            platform, user_id = account.platform, account.user_id
        else:
            platform, user_id = account

        CREATE_TEMP_TABLE_FOR_UNIQUE_TIPS = """

        CREATE TEMP TABLE __temp_unique_tips ON COMMIT drop AS

            -- Get all the latest tips from everyone to everyone.

            SELECT DISTINCT ON (tipper, tippee)
                   ctime, tipper, tippee, amount
              FROM tips
          ORDER BY tipper, tippee, mtime DESC;

        """

        CONSOLIDATE_TIPS_RECEIVING = """

            -- Create a new set of tips, one for each current tip *to* either
            -- the dead or the live account. If a user was tipping both the
            -- dead and the live account, then we create one new combined tip
            -- to the live account (via the GROUP BY and sum()).

            INSERT INTO tips (ctime, tipper, tippee, amount)

                 SELECT min(ctime), tipper, %(live)s AS tippee, sum(amount)

                   FROM __temp_unique_tips

                  WHERE (tippee = %(dead)s OR tippee = %(live)s)
                        -- Include tips *to* either the dead or live account.

                AND NOT (tipper = %(dead)s OR tipper = %(live)s)
                        -- Don't include tips *from* the dead or live account,
                        -- lest we convert cross-tipping to self-tipping.

                    AND amount > 0
                        -- Don't include zeroed out tips, so we avoid a no-op
                        -- zero tip entry.

               GROUP BY tipper

        """

        CONSOLIDATE_TIPS_GIVING = """

            -- Create a new set of tips, one for each current tip *from* either
            -- the dead or the live account. If both the dead and the live
            -- account were tipping a given user, then we create one new
            -- combined tip from the live account (via the GROUP BY and sum()).

            INSERT INTO tips (ctime, tipper, tippee, amount)

                 SELECT min(ctime), %(live)s AS tipper, tippee, sum(amount)

                   FROM __temp_unique_tips

                  WHERE (tipper = %(dead)s OR tipper = %(live)s)
                        -- Include tips *from* either the dead or live account.

                AND NOT (tippee = %(dead)s OR tippee = %(live)s)
                        -- Don't include tips *to* the dead or live account,
                        -- lest we convert cross-tipping to self-tipping.

                    AND amount > 0
                        -- Don't include zeroed out tips, so we avoid a no-op
                        -- zero tip entry.

               GROUP BY tippee

        """

        ZERO_OUT_OLD_TIPS_RECEIVING = """

            INSERT INTO tips (ctime, tipper, tippee, amount)

                SELECT ctime, tipper, tippee, 0 AS amount
                  FROM __temp_unique_tips
                 WHERE tippee=%s AND amount > 0

        """

        ZERO_OUT_OLD_TIPS_GIVING = """

            INSERT INTO tips (ctime, tipper, tippee, amount)

                SELECT ctime, tipper, tippee, 0 AS amount
                  FROM __temp_unique_tips
                 WHERE tipper=%s AND amount > 0

        """

        with self.db.get_cursor() as cursor:

            # Load the existing connection.
            # =============================
            # Every account elsewhere has at least a stub participant account
            # on Gittip.

            rec = cursor.one("""

                SELECT participant
                     , claimed_time IS NULL AS is_stub
                     , is_team
                  FROM elsewhere
                  JOIN participants ON participant=participants.username
                 WHERE elsewhere.platform=%s AND elsewhere.user_id=%s

            """, (platform, user_id), default=NotSane)

            other_username = rec.participant

            if self.username == other_username:
                # this is a no op - trying to take over itself
                return


            # Make sure we have user confirmation if needed.
            # ==============================================
            # We need confirmation in whatever combination of the following
            # three cases:
            #
            #   - the other participant is not a stub; we are taking the
            #       account elsewhere away from another viable Gittip
            #       participant
            #
            #   - the other participant has no other accounts elsewhere; taking
            #       away the account elsewhere will leave the other Gittip
            #       participant without any means of logging in, and it will be
            #       archived and its tips absorbed by us
            #
            #   - we already have an account elsewhere connected from the given
            #       platform, and it will be handed off to a new stub
            #       participant

            # other_is_a_real_participant
            other_is_a_real_participant = not rec.is_stub

            # this_is_others_last_account_elsewhere
            nelsewhere = cursor.one( "SELECT count(*) FROM elsewhere "
                                     "WHERE participant=%s"
                                   , (other_username,)
                                    )
            assert nelsewhere > 0           # sanity check
            this_is_others_last_account_elsewhere = (nelsewhere == 1)

            # we_already_have_that_kind_of_account
            nparticipants = cursor.one( "SELECT count(*) FROM elsewhere "
                                        "WHERE participant=%s AND platform=%s"
                                      , (self.username, platform)
                                       )
            assert nparticipants in (0, 1)  # sanity check
            we_already_have_that_kind_of_account = nparticipants == 1

            if rec.is_team and we_already_have_that_kind_of_account:
                if len(self.get_accounts_elsewhere()) == 1:
                    raise TeamCantBeOnlyAuth

            need_confirmation = NeedConfirmation( other_is_a_real_participant
                                                , this_is_others_last_account_elsewhere
                                                , we_already_have_that_kind_of_account
                                                 )
            if need_confirmation and not have_confirmation:
                raise need_confirmation


            # We have user confirmation. Proceed.
            # ===================================
            # There is a race condition here. The last person to call this will
            # win. XXX: I'm not sure what will happen to the DB and UI for the
            # loser.


            # Move any old account out of the way.
            # ====================================

            if we_already_have_that_kind_of_account:
                new_stub_username = reserve_a_random_username(cursor)
                cursor.run( "UPDATE elsewhere SET participant=%s "
                            "WHERE platform=%s AND participant=%s"
                          , (new_stub_username, platform, self.username)
                           )


            # Do the deal.
            # ============
            # If other_is_not_a_stub, then other will have the account
            # elsewhere taken away from them with this call. If there are other
            # browsing sessions open from that account, they will stay open
            # until they expire (XXX Is that okay?)

            cursor.run( "UPDATE elsewhere SET participant=%s "
                        "WHERE platform=%s AND user_id=%s"
                      , (self.username, platform, user_id)
                       )


            # Fold the old participant into the new as appropriate.
            # =====================================================
            # We want to do this whether or not other is a stub participant.

            if this_is_others_last_account_elsewhere:

                # Take over tips.
                # ===============

                x, y = self.username, other_username
                cursor.run(CREATE_TEMP_TABLE_FOR_UNIQUE_TIPS)
                cursor.run(CONSOLIDATE_TIPS_RECEIVING, dict(live=x, dead=y))
                cursor.run(CONSOLIDATE_TIPS_GIVING, dict(live=x, dead=y))
                cursor.run(ZERO_OUT_OLD_TIPS_RECEIVING, (other_username,))
                cursor.run(ZERO_OUT_OLD_TIPS_GIVING, (other_username,))


                # Archive the old participant.
                # ============================
                # We always give them a new, random username. We sign out
                # the old participant.

                for archive_username in gen_random_usernames():
                    try:
                        username = cursor.one("""

                            UPDATE participants
                               SET username=%s
                                 , username_lower=%s
                                 , session_token=NULL
                                 , session_expires=now()
                             WHERE username=%s
                         RETURNING username

                        """, ( archive_username
                             , archive_username.lower()
                             , other_username
                              ), default=NotSane)
                    except IntegrityError:
                        continue  # archive_username is already taken;
                                  # extremely unlikely, but ...
                                  # XXX But can the UPDATE fail in other ways?
                    else:
                        assert username == archive_username
                        break


                # Record the absorption.
                # ======================
                # This is for preservation of history.

                cursor.run( "INSERT INTO absorptions "
                            "(absorbed_was, absorbed_by, archived_as) "
                            "VALUES (%s, %s, %s)"
                          , ( other_username
                            , self.username
                            , archive_username
                             )
                           )

        self.update_avatar()

    def delete_elsewhere(self, platform, user_id):
        """Deletes account elsewhere unless the user would not be able
        to log in anymore.
        """
        user_id = unicode(user_id)
        with self.db.get_cursor() as c:
            accounts = c.all("""
                SELECT platform, user_id
                  FROM elsewhere
                 WHERE participant=%s
                   AND platform IN %s
                   AND NOT is_team
            """, (self.username, AccountElsewhere.signin_platforms_names))
            assert len(accounts) > 0
            if len(accounts) == 1 and accounts[0] == (platform, user_id):
                raise LastElsewhere()
            c.one("""
                DELETE FROM elsewhere
                WHERE participant=%s
                AND platform=%s
                AND user_id=%s
                RETURNING participant
            """, (self.username, platform, user_id), default=NonexistingElsewhere)
            add_event(c, 'participant', dict(id=self.id, action='disconnect', values=dict(platform=platform, user_id=user_id)))
        self.update_avatar()

    def credit_card_expiring(self, request, response):
        card_expiring = False

        if NOTIFIED_ABOUT_EXPIRATION in request.headers.cookie:
            cookie = request.headers.cookie[NOTIFIED_ABOUT_EXPIRATION]
            if cookie.value == self.session_token:
                return False

        if self.balanced_customer_href:
            card = billing.BalancedCard(self.balanced_customer_href)
        else:
            card = billing.StripeCard(self.stripe_customer_id)

        expiration_year = card['expiration_year']
        expiration_month= card['expiration_month']
        if expiration_year and expiration_month:
            card_expiring = is_card_expiring(int(expiration_year), int(expiration_month))

        response.headers.cookie[NOTIFIED_ABOUT_EXPIRATION] = self.session_token
        return card_expiring


class NeedConfirmation(Exception):
    """Represent the case where we need user confirmation during a merge.

    This is used in the workflow for merging one participant into another.

    """

    def __init__(self, a, b, c):
        self.other_is_a_real_participant = a
        self.this_is_others_last_account_elsewhere = b
        self.we_already_have_that_kind_of_account = c
        self._all = (a, b, c)

    def __repr__(self):
        return "<NeedConfirmation: %r %r %r>" % self._all
    __str__ = __repr__

    def __eq__(self, other):
        return self._all == other._all

    def __ne__(self, other):
        return not self.__eq__(other)

    def __nonzero__(self):
        # bool(need_confirmation)
        A, B, C = self._all
        return A or C

class LastElsewhere(Exception): pass

class NonexistingElsewhere(Exception): pass

class TeamCantBeOnlyAuth(Exception): pass

########NEW FILE########
__FILENAME__ = _mixin_team
"""Teams on Gittip are plural participants with members.
"""
from decimal import Decimal

from aspen.utils import typecheck


class MemberLimitReached(Exception): pass


class MixinTeam(object):
    """This class provides methods for working with a Participant as a Team.

    :param Participant participant: the underlying :py:class:`~gittip.participant.Participant` object for this team

    """

    # XXX These were all written with the ORM and need to be converted.

    def __init__(self, participant):
        self.participant = participant

    def show_as_team(self, user):
        """Return a boolean, whether to show this participant as a team.
        """
        if not self.IS_PLURAL:
            return False
        if user.ADMIN:
            return True
        if not self.get_takes():
            if self == user.participant:
                return True
            return False
        return True

    def add_member(self, member):
        """Add a member to this team.
        """
        assert self.IS_PLURAL
        if len(self.get_takes()) == 149:
            raise MemberLimitReached
        self.__set_take_for(member, Decimal('0.01'), self)

    def remove_member(self, member):
        """Remove a member from this team.
        """
        assert self.IS_PLURAL
        self.__set_take_for(member, Decimal('0.00'), self)

    def member_of(self, team):
        """Given a Participant object, return a boolean.
        """
        assert team.IS_PLURAL
        for take in team.get_takes():
            if take['member'] == self.username:
                return True
        return False

    def get_take_last_week_for(self, member):
        """What did the user actually take most recently? Used in throttling.
        """
        assert self.IS_PLURAL
        membername = member.username if hasattr(member, 'username') \
                                                        else member['username']
        return self.db.one("""

            SELECT amount
              FROM transfers
             WHERE tipper=%s AND tippee=%s
               AND timestamp >
                (SELECT ts_start FROM paydays ORDER BY ts_start DESC LIMIT 1)
          ORDER BY timestamp DESC LIMIT 1

        """, (self.username, membername), default=Decimal('0.00'))

    def get_take_for(self, member):
        """Return a Decimal representation of the take for this member, or 0.
        """
        assert self.IS_PLURAL
        return self.db.one( "SELECT amount FROM current_takes "
                            "WHERE member=%s AND team=%s"
                          , (member.username, self.username)
                          , default=Decimal('0.00')
                           )

    def compute_max_this_week(self, last_week):
        """2x last week's take, but at least a dollar.
        """
        return max(last_week * Decimal('2'), Decimal('1.00'))

    def set_take_for(self, member, take, recorder):
        """Sets member's take from the team pool.
        """
        assert self.IS_PLURAL

        # lazy import to avoid circular import
        from gittip.security.user import User
        from gittip.models.participant import Participant

        typecheck( member, Participant
                 , take, Decimal
                 , recorder, (Participant, User)
                  )

        last_week = self.get_take_last_week_for(member)
        max_this_week = self.compute_max_this_week(last_week)
        if take > max_this_week:
            take = max_this_week

        self.__set_take_for(member, take, recorder)
        return take

    def __set_take_for(self, member, amount, recorder):
        assert self.IS_PLURAL
        # XXX Factored out for testing purposes only! :O Use .set_take_for.
        self.db.run("""

            INSERT INTO takes (ctime, member, team, amount, recorder)
             VALUES ( COALESCE (( SELECT ctime
                                    FROM takes
                                   WHERE member=%s
                                     AND team=%s
                                   LIMIT 1
                                 ), CURRENT_TIMESTAMP)
                    , %s
                    , %s
                    , %s
                    , %s
                     )

        """, (member.username, self.username, member.username, self.username, \
                                                      amount, recorder.username))

    def get_takes(self, for_payday=False):
        """Return a list of member takes for a team.

        This is implemented parallel to Participant.get_tips_and_total. See
        over there for an explanation of for_payday.

        """
        assert self.IS_PLURAL

        args = dict(team=self.username)

        if for_payday:
            args['ts_start'] = for_payday

            # Get the takes for this team, as they were before ts_start,
            # filtering out the ones we've already transferred (in case payday
            # is interrupted and restarted).

            TAKES = """\

                SELECT * FROM (
                     SELECT DISTINCT ON (member) t.*
                       FROM takes t
                       JOIN participants p ON p.username = member
                      WHERE team=%(team)s
                        AND mtime < %(ts_start)s
                        AND p.is_suspicious IS NOT true
                        AND ( SELECT id
                                FROM transfers
                               WHERE tipper=t.team
                                 AND tippee=t.member
                                 AND as_team_member IS true
                                 AND timestamp >= %(ts_start)s
                             ) IS NULL
                   ORDER BY member, mtime DESC
                ) AS foo
                ORDER BY ctime DESC

            """
        else:
            TAKES = """\

                SELECT member, amount, ctime, mtime
                  FROM current_takes
                 WHERE team=%(team)s
              ORDER BY ctime DESC

            """

        return self.db.all(TAKES, args, back_as=dict)

    def get_team_take(self):
        """Return a single take for a team, the team itself's take.
        """
        assert self.IS_PLURAL
        TAKE = "SELECT sum(amount) FROM current_takes WHERE team=%s"
        total_take = self.db.one(TAKE, (self.username,), default=0)
        team_take = max(self.get_dollars_receiving() - total_take, 0)
        membership = { "ctime": None
                     , "mtime": None
                     , "member": self.username
                     , "amount": team_take
                      }
        return membership

    def get_members(self, current_participant):
        """Return a list of member dicts.
        """
        assert self.IS_PLURAL
        takes = self.get_takes()
        takes.append(self.get_team_take())
        budget = balance = self.get_dollars_receiving()
        members = []
        for take in takes:
            member = {}
            member['username'] = take['member']
            member['take'] = take['amount']

            member['removal_allowed'] = current_participant == self
            member['editing_allowed'] = False
            member['is_current_user'] = False
            if current_participant is not None:
                if member['username'] == current_participant.username:
                    member['is_current_user'] = True
                    if take['ctime'] is not None:
                        # current user, but not the team itself
                        member['editing_allowed']= True

            member['last_week'] = last_week = self.get_take_last_week_for(member)
            member['max_this_week'] = self.compute_max_this_week(last_week)
            amount = min(take['amount'], balance)
            balance -= amount
            member['balance'] = balance
            member['percentage'] = (amount / budget) if budget > 0 else 0
            members.append(member)
        return members

########NEW FILE########
__FILENAME__ = authentication
"""Defines website authentication helpers.
"""
import rfc822
import time

import gittip
from aspen import Response
from gittip.security import csrf
from gittip.security.user import User

BEGINNING_OF_EPOCH = rfc822.formatdate(0)
TIMEOUT = 60 * 60 * 24 * 7

def inbound(request):
    """Authenticate from a cookie or an API key in basic auth.
    """
    user = None
    if request.line.uri.startswith('/assets/'):
        pass
    elif 'Authorization' in request.headers:
        header = request.headers['authorization']
        if header.startswith('Basic '):
            creds = header[len('Basic '):].decode('base64')
            token, ignored = creds.split(':')
            user = User.from_api_key(token)

            # We don't require CSRF if they basically authenticated.
            csrf_token = csrf._get_new_csrf_key()
            request.headers.cookie['csrf_token'] = csrf_token
            request.headers['X-CSRF-TOKEN'] = csrf_token
            if 'Referer' not in request.headers:
                request.headers['Referer'] = \
                                        'https://%s/' % csrf._get_host(request)
    elif 'session' in request.headers.cookie:
        token = request.headers.cookie['session'].value
        user = User.from_session_token(token)

    request.context['user'] = user or User()

def outbound(request, response):
    if request.line.uri.startswith('/assets/'): return

    response.headers['Expires'] = BEGINNING_OF_EPOCH # don't cache

    user = request.context.get('user') or User()
    if not isinstance(user, User):
        raise Response(500, "If you define 'user' in a simplate it has to "
                            "be a User instance.")

    if not user.ANON:
        response.headers.cookie['session'] = user.participant.session_token
        expires = time.time() + TIMEOUT
        user.keep_signed_in_until(expires)

        cookie = response.headers.cookie['session']
        cookie['path'] = '/'
        cookie['expires'] = rfc822.formatdate(expires)
        cookie['httponly'] = 'Yes, please.'
        if gittip.canonical_scheme == 'https':
            cookie['secure'] = 'Yes, please.'

########NEW FILE########
__FILENAME__ = crypto
"""
Django's standard crypto functions and utilities.
"""
from __future__ import unicode_literals

import hmac
import struct
import hashlib
import binascii
import operator
import time
from functools import reduce

# Use the system PRNG if possible
import random
try:
    random = random.SystemRandom()
    using_sysrandom = True
except NotImplementedError:
    import warnings
    warnings.warn('A secure pseudo-random number generator is not available '
                  'on your system. Falling back to Mersenne Twister.')
    using_sysrandom = False

#from django.conf import settings
SECRET_KEY = ""
import string
pool = string.digits + string.letters + string.punctuation
UNSECURE_RANDOM_STRING = b"".join([random.choice(pool) for i in range(64)])


# I get wet.

#from django.utils.functional import Promise
class Promise(object):
    """
    This is just a base class for the proxy class created in
    the closure of the lazy function. It can be used to recognize
    promises in code.
    """
    pass

#from django.utils.encoding import smart_str
def smart_str(s, encoding='utf-8', strings_only=False, errors='strict'):
    """
    Returns a bytestring version of 's', encoded as specified in 'encoding'.

    If strings_only is True, don't convert (some) non-string-like objects.
    """
    if strings_only and (s is None or isinstance(s, int)):
        return s
    if isinstance(s, Promise):
        return unicode(s).encode(encoding, errors)
    elif not isinstance(s, basestring):
        try:
            return str(s)
        except UnicodeEncodeError:
            if isinstance(s, Exception):
                # An Exception subclass containing non-ASCII data that doesn't
                # know how to print itself properly. We shouldn't raise a
                # further exception.
                return ' '.join([smart_str(arg, encoding, strings_only,
                        errors) for arg in s])
            return unicode(s).encode(encoding, errors)
    elif isinstance(s, unicode):
        return s.encode(encoding, errors)
    elif s and encoding != 'utf-8':
        return s.decode('utf-8', errors).encode(encoding, errors)
    else:
        return s


_trans_5c = b"".join([chr(x ^ 0x5C) for x in xrange(256)])
_trans_36 = b"".join([chr(x ^ 0x36) for x in xrange(256)])


def salted_hmac(key_salt, value, secret=None):
    """
    Returns the HMAC-SHA1 of 'value', using a key generated from key_salt and a
    secret (which defaults to settings.SECRET_KEY).

    A different key_salt should be passed in for every application of HMAC.
    """
    if secret is None:
        raise NotImplementedError
        #secret = settings.SECRET_KEY

    # We need to generate a derived key from our base key.  We can do this by
    # passing the key_salt and our base key through a pseudo-random function and
    # SHA1 works nicely.
    key = hashlib.sha1((key_salt + secret).encode('utf-8')).digest()

    # If len(key_salt + secret) > sha_constructor().block_size, the above
    # line is redundant and could be replaced by key = key_salt + secret, since
    # the hmac module does the same thing for keys longer than the block size.
    # However, we need to ensure that we *always* do this.
    return hmac.new(key, msg=value, digestmod=hashlib.sha1)


def get_random_string(length=12,
                      allowed_chars='abcdefghijklmnopqrstuvwxyz'
                                    'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'):
    """
    Returns a securely generated random string.

    The default length of 12 with the a-z, A-Z, 0-9 character set returns
    a 71-bit value. log_2((26+26+10)^12) =~ 71 bits
    """
    if not using_sysrandom:
        # This is ugly, and a hack, but it makes things better than
        # the alternative of predictability. This re-seeds the PRNG
        # using a value that is hard for an attacker to predict, every
        # time a random string is required. This may change the
        # properties of the chosen random sequence slightly, but this
        # is better than absolute predictability.
        random.seed(
            hashlib.sha256(
                "%s%s%s" % (
                    random.getstate(),
                    time.time(),
                    UNSECURE_RANDOM_STRING)
                ).digest())
    return ''.join([random.choice(allowed_chars) for i in range(length)])


def constant_time_compare(val1, val2):
    """
    Returns True if the two strings are equal, False otherwise.

    The time taken is independent of the number of characters that match.
    """
    if len(val1) != len(val2):
        return False
    result = 0
    for x, y in zip(val1, val2):
        result |= ord(x) ^ ord(y)
    return result == 0


def _bin_to_long(x):
    """
    Convert a binary string into a long integer

    This is a clever optimization for fast xor vector math
    """
    return long(x.encode('hex'), 16)


def _long_to_bin(x, hex_format_string):
    """
    Convert a long integer into a binary string.
    hex_format_string is like "%020x" for padding 10 characters.
    """
    return binascii.unhexlify((hex_format_string % x).encode('ascii'))


def _fast_hmac(key, msg, digest):
    """
    A trimmed down version of Python's HMAC implementation
    """
    dig1, dig2 = digest(), digest()
    key = smart_str(key)
    if len(key) > dig1.block_size:
        key = digest(key).digest()
    key += chr(0) * (dig1.block_size - len(key))
    dig1.update(key.translate(_trans_36))
    dig1.update(msg)
    dig2.update(key.translate(_trans_5c))
    dig2.update(dig1.digest())
    return dig2


def pbkdf2(password, salt, iterations, dklen=0, digest=None):
    """
    Implements PBKDF2 as defined in RFC 2898, section 5.2

    HMAC+SHA256 is used as the default pseudo random function.

    Right now 10,000 iterations is the recommended default which takes
    100ms on a 2.2Ghz Core 2 Duo.  This is probably the bare minimum
    for security given 1000 iterations was recommended in 2001. This
    code is very well optimized for CPython and is only four times
    slower than openssl's implementation.
    """
    assert iterations > 0
    if not digest:
        digest = hashlib.sha256
    password = smart_str(password)
    salt = smart_str(salt)
    hlen = digest().digest_size
    if not dklen:
        dklen = hlen
    if dklen > (2 ** 32 - 1) * hlen:
        raise OverflowError('dklen too big')
    l = -(-dklen // hlen)
    r = dklen - (l - 1) * hlen

    hex_format_string = "%%0%ix" % (hlen * 2)

    def F(i):
        def U():
            u = salt + struct.pack(b'>I', i)
            for j in xrange(int(iterations)):
                u = _fast_hmac(password, u, digest).digest()
                yield _bin_to_long(u)
        return _long_to_bin(reduce(operator.xor, U()), hex_format_string)

    T = [F(x) for x in range(1, l + 1)]
    return b''.join(T[:-1]) + T[-1][:r]

########NEW FILE########
__FILENAME__ = csrf
"""Cross Site Request Forgery middleware, borrowed from Django.

See also:

    https://github.com/django/django/blob/master/django/middleware/csrf.py
    https://docs.djangoproject.com/en/dev/ref/contrib/csrf/
    https://github.com/gittip/www.gittip.com/issues/88

"""
import rfc822
import re
import time
import urlparse
from aspen import log_dammit


#from django.utils.cache import patch_vary_headers
cc_delim_re = re.compile(r'\s*,\s*')
def patch_vary_headers(response, newheaders):
    """
    Adds (or updates) the "Vary" header in the given HttpResponse object.
    newheaders is a list of header names that should be in "Vary". Existing
    headers in "Vary" aren't removed.
    """
    # Note that we need to keep the original order intact, because cache
    # implementations may rely on the order of the Vary contents in, say,
    # computing an MD5 hash.
    if 'Vary' in response.headers:
        vary_headers = cc_delim_re.split(response.headers['Vary'])
    else:
        vary_headers = []
    # Use .lower() here so we treat headers as case-insensitive.
    existing_headers = set([header.lower() for header in vary_headers])
    additional_headers = [newheader for newheader in newheaders
                          if newheader.lower() not in existing_headers]
    response.headers['Vary'] = ', '.join(vary_headers + additional_headers)


#from django.utils.http import same_origin
def same_origin(url1, url2):
    """
    Checks if two URLs are 'same-origin'
    """
    p1, p2 = urlparse.urlparse(url1), urlparse.urlparse(url2)
    return (p1.scheme, p1.hostname, p1.port) == (p2.scheme, p2.hostname, p2.port)


from aspen import Response
from crypto import constant_time_compare, get_random_string

REASON_NO_REFERER = "Referer checking failed - no Referer."
REASON_BAD_REFERER = "Referer checking failed - %s does not match %s."
REASON_NO_CSRF_COOKIE = "CSRF cookie not set."
REASON_BAD_TOKEN = "CSRF token missing or incorrect."

TOKEN_LENGTH = 32
TIMEOUT = 60 * 60 * 24 * 7


def _get_new_csrf_key():
    return get_random_string(TOKEN_LENGTH)


def _sanitize_token(token):
    # Allow only alphanum, and ensure we return a 'str' for the sake
    # of the post processing middleware.
    if len(token) > TOKEN_LENGTH:
        return _get_new_csrf_key()
    token = re.sub('[^a-zA-Z0-9]+', '', str(token.decode('ascii', 'ignore')))
    if token == "":
        # In case the cookie has been truncated to nothing at some point.
        return _get_new_csrf_key()
    return token

def _is_secure(request):
    import gittip
    return gittip.canonical_scheme == 'https'

def _get_host(request):
    """Returns the HTTP host using the request headers.
    """
    return request.headers.get('X-Forwarded-Host', request.headers['Host'])



def inbound(request):
    """Given a Request object, reject it if it's a forgery.
    """
    if request.line.uri.startswith('/assets/'): return

    try:
        csrf_token = request.headers.cookie.get('csrf_token')
        csrf_token = '' if csrf_token is None else csrf_token.value
        csrf_token = _sanitize_token(csrf_token)
    except KeyError:
        csrf_token = _get_new_csrf_key()

    request.context['csrf_token'] = csrf_token

    # Assume that anything not defined as 'safe' by RC2616 needs protection
    if request.line.method not in ('GET', 'HEAD', 'OPTIONS', 'TRACE'):

        if _is_secure(request):
            # Suppose user visits http://example.com/
            # An active network attacker (man-in-the-middle, MITM) sends a
            # POST form that targets https://example.com/detonate-bomb/ and
            # submits it via JavaScript.
            #
            # The attacker will need to provide a CSRF cookie and token, but
            # that's no problem for a MITM and the session-independent
            # nonce we're using. So the MITM can circumvent the CSRF
            # protection. This is true for any HTTP connection, but anyone
            # using HTTPS expects better! For this reason, for
            # https://example.com/ we need additional protection that treats
            # http://example.com/ as completely untrusted. Under HTTPS,
            # Barth et al. found that the Referer header is missing for
            # same-domain requests in only about 0.2% of cases or less, so
            # we can use strict Referer checking.
            referer = request.headers.get('Referer')
            if referer is None:
                raise Response(403, REASON_NO_REFERER)

            good_referer = 'https://%s/' % _get_host(request)
            if not same_origin(referer, good_referer):
                reason = REASON_BAD_REFERER % (referer, good_referer)
                log_dammit(reason)
                raise Response(403, reason)

        if csrf_token is None:
            raise Response(403, REASON_NO_CSRF_COOKIE)

        # Check non-cookie token for match.
        request_csrf_token = ""
        if request.line.method == "POST":
            request_csrf_token = request.body.get('csrf_token', '')

        if request_csrf_token == "":
            # Fall back to X-CSRF-TOKEN, to make things easier for AJAX,
            # and possible for PUT/DELETE.
            request_csrf_token = request.headers.get('X-CSRF-TOKEN', '')

        if not constant_time_compare(request_csrf_token, csrf_token):
            raise Response(403, REASON_BAD_TOKEN)


def outbound(request, response):
    """Store the latest CSRF token as a cookie.
    """
    csrf_token = request.context.get('csrf_token')
    if csrf_token:
        response.headers.cookie['csrf_token'] = csrf_token
        cookie = response.headers.cookie['csrf_token']
        cookie['path'] = '/'
        cookie['expires'] = rfc822.formatdate(time.time() + TIMEOUT)

        # Content varies with the CSRF cookie, so set the Vary header.
        patch_vary_headers(response, ('Cookie',))

########NEW FILE########
__FILENAME__ = user
from gittip.models.participant import Participant

class User(object):
    """Represent a user of our website.
    """

    participant = None


    # Constructors
    # ============

    @classmethod
    def from_session_token(cls, token):
        """Find a participant based on token and return a User.
        """
        self = cls()
        self.participant = Participant.from_session_token(token)
        return self

    @classmethod
    def from_api_key(cls, api_key):
        """Find a participant based on token and return a User.
        """
        self = cls()
        self.participant = Participant.from_api_key(api_key)
        return self

    @classmethod
    def from_username(cls, username):
        """Find a participant based on username and return a User.
        """
        self = cls()
        self.participant = Participant.from_username(username)
        return self

    def __str__(self):
        if self.participant is None:
            out = '<Anonymous>'
        else:
            out = '<User: %s>' % self.participant.username
        return out
    __repr__ = __str__


    # Authentication Helpers
    # ======================

    def sign_in(self):
        """Start a new session for the user.
        """
        self.participant.start_new_session()

    def keep_signed_in_until(self, expires):
        """Extend the user's current session.

        :param float expires: A UNIX timestamp (XXX timezone?)

        """
        self.participant.set_session_expires(expires)

    def sign_out(self):
        """End the user's current session.
        """
        self.participant.end_session()
        self.participant = None


    # Roles
    # =====

    @property
    def ADMIN(self):
        return not self.ANON and self.participant.is_admin

    @property
    def ANON(self):
        return self.participant is None or self.participant.is_suspicious is True
        # Append "is True" here because otherwise Python will return the result
        # of evaluating the right side of the or expression, which can be None.

    def get_highest_role(self, owner):
        """Return a string representing the highest role this user has.

        :param string owner: the username of the owner of the resource we're
            concerned with, or None

        """
        def is_owner():
            if self.participant is not None:
                if owner is not None:
                    if self.participant.username == owner:
                        return True
            return False

        if self.ADMIN:
            return 'admin'
        elif is_owner():
            return 'owner'
        elif not self.ANON:
            return 'authenticated'
        else:
            return 'anonymous'

########NEW FILE########
__FILENAME__ = balanced
from __future__ import absolute_import, division, print_function, unicode_literals

import balanced

from gittip.testing import Harness


class BalancedHarness(Harness):

    @classmethod
    def setUpClass(cls):
        super(BalancedHarness, cls).setUpClass()
        cls.balanced_api_key = balanced.APIKey().save().secret
        balanced.configure(cls.balanced_api_key)
        mp = balanced.Marketplace.my_marketplace
        if not mp:
            mp = balanced.Marketplace().save()
        cls.balanced_marketplace = mp


    def setUp(self):
        Harness.setUp(self)
        self.alice = self.make_participant('alice', elsewhere='github')

        self.balanced_customer_href = unicode(balanced.Customer().save().href)
        self.card_href = unicode(balanced.Card(
            number='4111111111111111',
            expiration_month=10,
            expiration_year=2020,
            address={
                'line1': "123 Main Street",
                'state': 'Confusion',
                'postal_code': '90210',
            },
            # gittip stores some of the address data in the meta fields,
            # continue using them to support backwards compatibility
            meta={
                'address_2': 'Box 2',
                'city_town': '',
                'region': 'Confusion',
            }
        ).save().href) # XXX Why don't we actually associate this with the customer? See XXX in
                       # test_billing_payday.TestPaydayChargeOnBalanced.
        self.bank_account_href = unicode(balanced.BankAccount(
            name='Homer Jay',
            account_number='112233a',
            routing_number='121042882',
        ).save().href)

########NEW FILE########
__FILENAME__ = elsewhere
# -*- coding: utf-8 -*-

"""
Examples of data returned by the APIs of the elsewhere platforms.

They are wrapped in lambdas to prevent tests from persistently modifying the
data.
"""

import xml.etree.ElementTree as ET

bitbucket = lambda: {
    "repositories": [
        {
            "scm": "hg",
            "has_wiki": True,
            "last_updated": "2012-03-16T23:36:38.019",
            "no_forks": None,
            "created_on": "2012-03-16T23:34:46.740",
            "owner": "whit537",
            "logo": "https://d3oaxc4q5k2d6q.cloudfront.net/m/6fac1fb24100/img/language-avatars/default_16.png",
            "email_mailinglist": "",
            "is_mq": False,
            "size": 142818,
            "read_only": False,
            "fork_of": {
                "scm": "hg",
                "has_wiki": True,
                "last_updated": "2014-02-01T03:41:46.920",
                "no_forks": None,
                "created_on": "2010-07-17T16:12:34.381",
                "owner": "jaraco",
                "logo": "https://d3oaxc4q5k2d6q.cloudfront.net/m/6fac1fb24100/img/language-avatars/python_16.png",
                "email_mailinglist": "",
                "is_mq": False,
                "size": 316601,
                "read_only": False,
                "creator": None,
                "state": "available",
                "utc_created_on": "2010-07-17 14:12:34+00:00",
                "website": "",
                "description": "Inspried by jezdez.setuptools_hg, and building on that work, hgtools provides tools for developing with mercurial and setuptools/distribute (specifically a file-finder plugin and automatic repo tag versioning).\r\n\r\nThe underlying library is designed to be extensible for other applications to build other functionality that depends on mercurial, whether using the 'hg' command or the mercurial libraries directly.",
                "has_issues": True,
                "is_fork": True,
                "slug": "hgtools",
                "is_private": False,
                "name": "hgtools",
                "language": "python",
                "utc_last_updated": "2014-02-01 02:41:46+00:00",
                "email_writers": True,
                "no_public_forks": False,
                "resource_uri": "/1.0/repositories/jaraco/hgtools"
            },
            "mq_of": {
                "scm": "hg",
                "has_wiki": True,
                "last_updated": "2014-02-01T03:41:46.920",
                "no_forks": None,
                "created_on": "2010-07-17T16:12:34.381",
                "owner": "jaraco",
                "logo": "https://d3oaxc4q5k2d6q.cloudfront.net/m/6fac1fb24100/img/language-avatars/python_16.png",
                "email_mailinglist": "",
                "is_mq": False,
                "size": 316601,
                "read_only": False,
                "creator": None,
                "state": "available",
                "utc_created_on": "2010-07-17 14:12:34+00:00",
                "website": "",
                "description": "Inspried by jezdez.setuptools_hg, and building on that work, hgtools provides tools for developing with mercurial and setuptools/distribute (specifically a file-finder plugin and automatic repo tag versioning).\r\n\r\nThe underlying library is designed to be extensible for other applications to build other functionality that depends on mercurial, whether using the 'hg' command or the mercurial libraries directly.",
                "has_issues": True,
                "is_fork": True,
                "slug": "hgtools",
                "is_private": False,
                "name": "hgtools",
                "language": "python",
                "utc_last_updated": "2014-02-01 02:41:46+00:00",
                "email_writers": True,
                "no_public_forks": False,
                "resource_uri": "/1.0/repositories/jaraco/hgtools"
            },
            "state": "available",
            "utc_created_on": "2012-03-16 22:34:46+00:00",
            "website": None,
            "description": "I'm forking to fix another bug case in issue #7.",
            "has_issues": True,
            "is_fork": True,
            "slug": "hgtools",
            "is_private": False,
            "name": "hgtools",
            "language": "",
            "utc_last_updated": "2012-03-16 22:36:38+00:00",
            "email_writers": True,
            "no_public_forks": False,
            "creator": None,
            "resource_uri": "/1.0/repositories/whit537/hgtools"
        }
    ],
    "user": {
        "username": "whit537",
        "first_name": "Chad",
        "last_name": "Whitacre",
        "display_name": "Chad Whitacre",
        "is_team": False,
        "avatar": "https://secure.gravatar.com/avatar/5698bc43665106a28833ef61c8a9f67f?d=https%3A%2F%2Fd3oaxc4q5k2d6q.cloudfront.net%2Fm%2F6fac1fb24100%2Fimg%2Fdefault_avatar%2F32%2Fuser_blue.png&s=32",
        "resource_uri": "/1.0/users/whit537"
    }
}

bountysource = lambda: {
    "bio": "Code alchemist at Bountysource.",
    "twitter_account": {
        "uid": 313084547,
        "followers": None,
        "following": None,
        "image_url": "https://cloudinary-a.akamaihd.net/bountysource/image/twitter_name/d_noaoqqwxegvmulwus0un.png,c_pad,w_100,h_100/corytheboyd.png",
        "login": "corytheboyd",
        "id": 2105
    },
    "display_name": "corytheboyd",
    "url": "",
    "type": "Person",
    "created_at": "2012-09-14T03:28:07Z",
    "slug": "6-corytheboyd",
    "facebook_account": {
        "uid": 589244295,
        "followers": 0,
        "following": 0,
        "image_url": "https://cloudinary-a.akamaihd.net/bountysource/image/facebook/d_noaoqqwxegvmulwus0un.png,c_pad,w_100,h_100/corytheboyd.jpg",
        "login": "corytheboyd",
        "id": 2103
    },
    "gittip_account": {
        "uid": 17306,
        "followers": 0,
        "following": 0,
        "image_url": "https://cloudinary-a.akamaihd.net/bountysource/image/gravatar/d_noaoqqwxegvmulwus0un.png,c_pad,w_100,h_100/bdeaea505d059ccf23d8de5714ae7f73",
        "login": "corytheboyd",
        "id": 2067
    },
    "large_image_url": "https://cloudinary-a.akamaihd.net/bountysource/image/twitter_name/d_noaoqqwxegvmulwus0un.png,c_pad,w_400,h_400/corytheboyd.png",
    "frontend_path": "/users/6-corytheboyd",
    "image_url": "https://cloudinary-a.akamaihd.net/bountysource/image/twitter_name/d_noaoqqwxegvmulwus0un.png,c_pad,w_100,h_100/corytheboyd.png",
    "location": "San Francisco, CA",
    "medium_image_url": "https://cloudinary-a.akamaihd.net/bountysource/image/twitter_name/d_noaoqqwxegvmulwus0un.png,c_pad,w_200,h_200/corytheboyd.png",
    "frontend_url": "https://www.bountysource.com/users/6-corytheboyd",
    "github_account": {
        "uid": 692632,
        "followers": 11,
        "following": 4,
        "image_url": "https://cloudinary-a.akamaihd.net/bountysource/image/gravatar/d_noaoqqwxegvmulwus0un.png,c_pad,w_100,h_100/bdeaea505d059ccf23d8de5714ae7f73",
        "login": "corytheboyd",
        "id": 89,
        "permissions": [
            "public_repo"
        ]
    },
    "company": "Bountysource",
    "id": 6,
    "public_email": "cory@bountysource.com"
}

github = lambda: {
    "bio": "",
    "updated_at": "2013-01-14T13:43:23Z",
    "gravatar_id": "fb054b407a6461e417ee6b6ae084da37",
    "hireable": False,
    "id": 134455,
    "followers_url": "https://api.github.com/users/whit537/followers",
    "following_url": "https://api.github.com/users/whit537/following",
    "blog": "http://whit537.org/",
    "followers": 90,
    "location": "Pittsburgh, PA",
    "type": "User",
    "email": "chad@zetaweb.com",
    "public_repos": 25,
    "events_url": "https://api.github.com/users/whit537/events{/privacy}",
    "company": "Gittip",
    "gists_url": "https://api.github.com/users/whit537/gists{/gist_id}",
    "html_url": "https://github.com/whit537",
    "subscriptions_url": "https://api.github.com/users/whit537/subscriptions",
    "received_events_url": "https://api.github.com/users/whit537/received_events",
    "starred_url": "https://api.github.com/users/whit537/starred{/owner}{/repo}",
    "public_gists": 29,
    "name": "Chad Whitacre",
    "organizations_url": "https://api.github.com/users/whit537/orgs",
    "url": "https://api.github.com/users/whit537",
    "created_at": "2009-10-03T02:47:57Z",
    "avatar_url": "https://secure.gravatar.com/avatar/fb054b407a6461e417ee6b6ae084da37?d=https://a248.e.akamai.net/assets.github.com%2Fimages%2Fgravatars%2Fgravatar-user-420.png",
    "repos_url": "https://api.github.com/users/whit537/repos",
    "following": 15,
    "login": "whit537"
}

openstreetmap = lambda: ET.fromstring("""
 <!-- copied from http://wiki.openstreetmap.org/wiki/API_v0.6 -->
 <osm version="0.6" generator="OpenStreetMap server">
   <user id="12023" display_name="jbpbis" account_created="2007-08-16T01:35:56Z">
     <description></description>
     <contributor-terms agreed="false"/>
     <img href="http://www.gravatar.com/avatar/c8c86cd15f60ecca66ce2b10cb6b9a00.jpg?s=256&amp;d=http%3A%2F%2Fwww.openstreetmap.org%2Fassets%2Fusers%2Fimages%2Flarge-39c3a9dc4e778311af6b70ddcf447b58.png"/>
     <roles>
     </roles>
     <changesets count="1"/>
     <traces count="0"/>
     <blocks>
       <received count="0" active="0"/>
     </blocks>
   </user>
 </osm>
""")

twitter = lambda: {
    "lang": "en",
    "utc_offset": 3600,
    "statuses_count": 1339,
    "follow_request_sent": None,
    "friends_count": 81,
    "profile_use_background_image": True,
    "contributors_enabled": False,
    "profile_link_color": "0084B4",
    "profile_image_url": "http://pbs.twimg.com/profile_images/3502698593/36a503f65df33aea1a59faea77a57e73_normal.png",
    "time_zone": "Paris",
    "notifications": None,
    "is_translator": False,
    "favourites_count": 81,
    "profile_background_image_url_https": "https://abs.twimg.com/images/themes/theme1/bg.png",
    "profile_background_color": "C0DEED",
    "id": 23608307,
    "profile_background_image_url": "http://abs.twimg.com/images/themes/theme1/bg.png",
    "description": "#Freelance computer programmer from France. In English: #FreeSoftware and #BasicIncome. In French: #LogicielLibre, #RevenuDeBase and #Démocratie/#TirageAuSort.",
    "is_translation_enabled": False,
    "default_profile": True,
    "profile_background_tile": False,
    "verified": False,
    "screen_name": "Changaco",
    "entities": {
        "url": {
            "urls": [
                {
                    "url": "http://t.co/2VUhacI9SG",
                    "indices": [
                        0,
                        22
                    ],
                    "expanded_url": "http://changaco.oy.lc/",
                    "display_url": "changaco.oy.lc"
                }
            ]
        },
        "description": {
            "urls": []
        }
    },
    "url": "http://t.co/2VUhacI9SG",
    "profile_image_url_https": "https://pbs.twimg.com/profile_images/3502698593/36a503f65df33aea1a59faea77a57e73_normal.png",
    "profile_sidebar_fill_color": "DDEEF6",
    "location": "France",
    "name": "Changaco",
    "geo_enabled": False,
    "profile_text_color": "333333",
    "followers_count": 94,
    "profile_sidebar_border_color": "C0DEED",
    "id_str": "23608307",
    "default_profile_image": False,
    "following": None,
    "protected": False,
    "created_at": "Tue Mar 10 15:58:07 +0000 2009",
    "listed_count": 7
}

venmo = lambda: {
    "about": "No Short Bio",
    "date_joined": "2013-09-11T19:57:53",
    "display_name": "Thomas Boyt",
    "email": None,
    "first_name": "Thomas",
    "friends_count": 30,
    "id": "1242868517699584789",
    "is_friend": False,
    "last_name": "Boyt",
    "phone": None,
    "profile_picture_url": "https://s3.amazonaws.com/venmo/no-image.gif",
    "username": "thomas-boyt"
}

########NEW FILE########
__FILENAME__ = cache_static
"""
Handles caching of static resources.
"""
import os
from calendar import timegm
from email.utils import parsedate
from wsgiref.handlers import format_date_time

from aspen import Response


def version_is_available(request):
    """Return a boolean, whether we have the version they asked for.
    """
    path = request.line.uri.path
    version = request.website.version
    return path['version'] == version if 'version' in path else True


def version_is_dash(request):
    """Return a boolean, whether the version they asked for is -.
    """
    return request.line.uri.path.get('version') == '-'


def get_last_modified(fs_path):
    """Get the last modified time, as int, of the file pointed to by fs_path.
    """
    return int(os.path.getctime(fs_path))


def inbound(request):
    """Try to serve a 304 for resources under assets/.
    """
    uri = request.line.uri

    if not uri.startswith('/assets/'):

        # Only apply to the assets/ directory.

        return request

    if version_is_dash(request):

        # Special-case a version of '-' to never 304/404 here.

        return request

    if not version_is_available(request):

        # Don't serve one version of a file as if it were another.

        raise Response(404)

    ims = request.headers.get('If-Modified-Since')
    if not ims:

        # This client doesn't care about when the file was modified.

        return request

    if request.fs.endswith('.spt'):

        # This is a requests for a dynamic resource. Perhaps in the future
        # we'll delegate to such resources to compute a sensible Last-Modified
        # or E-Tag, but for now we punt. This is okay, because we expect to
        # put our dynamic assets behind a CDN in production.

        return request


    try:
        ims = timegm(parsedate(ims))
    except:

        # Malformed If-Modified-Since header. Proceed with the request.

        return request

    last_modified = get_last_modified(request.fs)
    if ims < last_modified:

        # The file has been modified since. Serve the whole thing.

        return request


    # Huzzah!
    # =======
    # We can serve a 304! :D

    response = Response(304)
    response.headers['Last-Modified'] = format_date_time(last_modified)
    response.headers['Cache-Control'] = 'no-cache'
    raise response


def outbound(request, response, website):
    """Set caching headers for resources under assets/.
    """
    uri = request.line.uri
    
    if not uri.startswith('/assets/'):
        return response

    if response.code != 200:
        return response

    if website.cache_static:

        # https://developers.google.com/speed/docs/best-practices/caching
        response.headers['Cache-Control'] = 'public'
        response.headers['Vary'] = 'accept-encoding'

        # all assets are versioned, so it's fine to cache them

        response.headers['Expires'] = 'Sun, 17 Jan 2038 19:14:07 GMT'
        last_modified = get_last_modified(request.fs)
        response.headers['Last-Modified'] = format_date_time(last_modified)

########NEW FILE########
__FILENAME__ = fake_data
from faker import Factory
from gittip import wireup, MAX_TIP_SINGULAR, MIN_TIP
from gittip.elsewhere import PLATFORMS
from gittip.models.participant import Participant

import datetime
import decimal
import random
import string


faker = Factory.create()


def _fake_thing(db, tablename, **kw):
    column_names = []
    column_value_placeholders = []
    column_values = []

    for k,v in kw.items():
        column_names.append(k)
        column_value_placeholders.append("%s")
        column_values.append(v)

    column_names = ", ".join(column_names)
    column_value_placeholders = ", ".join(column_value_placeholders)

    db.run( "INSERT INTO {} ({}) VALUES ({})"
            .format(tablename, column_names, column_value_placeholders)
          , column_values
           )
    return kw


def fake_text_id(size=6, chars=string.ascii_lowercase + string.digits):
    """Create a random text id.
    """
    return ''.join(random.choice(chars) for x in range(size))


def fake_balance(max_amount=100):
    """Return a random amount between 0 and max_amount.
    """
    return random.random() * max_amount


def fake_int_id(nmax=2 ** 31 -1):
    """Create a random int id.
    """
    return random.randint(0, nmax)


def fake_sentence(start=1, stop=100):
    """Create a sentence of random length.
    """
    return faker.sentence(random.randrange(start,stop))


def fake_participant(db, number="singular", is_admin=False):
    """Create a fake User.
    """
    username = faker.first_name() + fake_text_id(3)
    _fake_thing( db
               , "participants"
               , id=fake_int_id()
               , username=username
               , username_lower=username.lower()
               , statement=fake_sentence()
               , ctime=faker.date_time_this_year()
               , is_admin=is_admin
               , balance=fake_balance()
               , anonymous_giving=(random.randrange(5) == 0)
               , anonymous_receiving=(random.randrange(5) == 0)
               , goal=fake_balance()
               , balanced_customer_href=faker.uri()
               , last_ach_result=''
               , is_suspicious=False
               , last_bill_result=''  # Needed to not be suspicious
               , claimed_time=faker.date_time_this_year()
               , number=number
                )
    #Call participant constructor to perform other DB initialization
    return Participant.from_username(username)



def fake_tip_amount():
    amount = ((decimal.Decimal(random.random()) * (MAX_TIP_SINGULAR - MIN_TIP))
            + MIN_TIP)

    decimal_amount = decimal.Decimal(amount).quantize(decimal.Decimal('.01'))

    return decimal_amount


def fake_tip(db, tipper, tippee):
    """Create a fake tip.
    """
    return _fake_thing( db
               , "tips"
               , id=fake_int_id()
               , ctime=faker.date_time_this_year()
               , mtime=faker.date_time_this_month()
               , tipper=tipper.username
               , tippee=tippee.username
               , amount=fake_tip_amount()
                )


def fake_elsewhere(db, participant, platform):
    """Create a fake elsewhere.
    """
    _fake_thing( db
               , "elsewhere"
               , id=fake_int_id()
               , platform=platform
               , user_id=fake_text_id()
               , user_name=participant.username
               , is_locked=False
               , participant=participant.username
               , extra_info=None
                )


def fake_transfer(db, tipper, tippee):
        return _fake_thing( db
               , "transfers"
               , id=fake_int_id()
               , timestamp=faker.date_time_this_year()
               , tipper=tipper.username
               , tippee=tippee.username
               , amount=fake_tip_amount()
                )


def populate_db(db, num_participants=100, num_tips=200, num_teams=5, num_transfers=5000):
    """Populate DB with fake data.
    """
    #Make the participants
    participants = []
    for i in xrange(num_participants):
        participants.append(fake_participant(db))

    #Make the "Elsewhere's"
    for p in participants:
        #All participants get between 1 and 3 elsewheres
        num_elsewheres = random.randint(1, 3)
        for platform_name in random.sample(PLATFORMS, num_elsewheres):
            fake_elsewhere(db, p, platform_name)

    #Make teams
    for i in xrange(num_teams):
        t = fake_participant(db, number="plural")
        #Add 1 to 3 members to the team
        members = random.sample(participants, random.randint(1, 3))
        for p in members:
            t.add_member(p)

    #Make the tips
    tips = []
    for i in xrange(num_tips):
        tipper, tippee = random.sample(participants, 2)
        tips.append(fake_tip(db, tipper, tippee))


    #Make the transfers
    transfers = []
    for i in xrange(num_transfers):
        tipper, tippee = random.sample(participants, 2)
        transfers.append(fake_transfer(db, tipper, tippee))


    #Make some paydays
    #First determine the boundaries - min and max date
    min_date = min(min(x['ctime'] for x in tips), \
                   min(x['timestamp'] for x in transfers))
    max_date = max(max(x['ctime'] for x in tips), \
                   max(x['timestamp'] for x in transfers))
    #iterate through min_date, max_date one week at a time
    date = min_date
    while date < max_date:
        end_date = date + datetime.timedelta(days=7)
        week_tips = filter(lambda x: date <= x['ctime'] <= end_date, tips)
        week_transfers = filter(lambda x: date <= x['timestamp'] <= end_date, transfers)
        week_participants = filter(lambda x: x.ctime.replace(tzinfo=None) <= end_date, participants)
        actives=set()
        tippers=set()
        for xfers in week_tips, week_transfers:
            actives.update(x['tipper'] for x in xfers)
            actives.update(x['tippee'] for x in xfers)
            tippers.update(x['tipper'] for x in xfers)
        payday = {
            'id': fake_int_id(),
            'ts_start': date,
            'ts_end': end_date,
            'ntips': len(week_tips),
            'ntransfers': len(week_transfers),
            'nparticipants': len(week_participants),
            'ntippers': len(tippers),
            'nactive': len(actives),
            'transfer_volume': sum(x['amount'] for x in week_transfers)
        }
        #Make ach_volume and charge_volume between 0 and 10% of transfer volume
        def rand_part():
            return decimal.Decimal(random.random()* 0.1)
        payday['ach_volume']   = -1 * payday['transfer_volume'] * rand_part()
        payday['charge_volume'] = payday['transfer_volume'] * rand_part()
        _fake_thing(db, "paydays", **payday)
        date = end_date



def main():
    populate_db(wireup.db(wireup.env()))

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = query_cache
import sys
import threading
import time
import traceback


# Define a query cache.
# ==========================

class FormattingError(StandardError):
    """Represent a problem with a format callable.
    """


class Entry(object):
    """An entry in a QueryCache.
    """

    timestamp = None    # The timestamp of the last query run [datetime.datetime]
    lock = None         # Access control for this record [threading.Lock]
    exc = None          # Any exception in query or formatting [Exception]

    def __init__(self, timestamp=0, lock=None, result=None):
        """Populate with dummy data or an actual db entry.
        """
        self.timestamp = timestamp
        self.lock = lock or threading.Lock()
        self.result = result


class QueryCache(object):
    """Implement a caching SQL post-processor.

    Instances of this object are callables that take two or more arguments. The
    first argument is a callback function; subsequent arguments are strings of
    SQL. The callback function will be given one result set per SQL query, and
    in the same order. These result sets are lists of dictionaries. The
    callback function may return any Python data type; this is the query
    result, post-processed for your application.

    The results of the callback are cached for <self.threshold> seconds
    (default: 5), keyed to the given SQL queries. NB: the cache is *not* keyed
    to the callback function, so cache entries with different callbacks will
    collide when operating on identical SQL queries. In this case cache entries
    can be differentiated by adding comments to the SQL statements.

    This so-called micro-caching helps greatly when under load, while keeping
    pages more or less fresh. For relatively static page elements like
    navigation, the time could certainly be extended. But even for page
    elements which are supposed to seem completely dynamic -- different for
    each page load -- you can profitably use this object with a low cache
    setting (1 or 2 seconds): the page will appear dynamic to any given user,
    but 100 requests in the same second will only result in one database call.

    This object also features a pruning thread, which removes stale cache
    entries on a more relaxed schedule (default: 60 seconds). It keeps the
    cache clean without interfering too much with actual usage.

    If the actual database call or the formatting callback raise an Exception,
    then that is cached as well, and will be raised on further calls until the
    cache expires as usual.

    And yes, Virginia, QueryCache is thread-safe (as long as you don't invoke
    the same instance again within your formatting callback).

    """

    db = None               # PostgresManager object
    cache = None            # the query cache [dictionary]
    locks = None            # access controls for self.cache [Locks]
    threshold = 5           # maximum life of a cache entry [seconds as int]
    threshold_prune = 60    # time between pruning runs [seconds as int]


    def __init__(self, db, threshold=5, threshold_prune=60):
        """
        """
        self.db = db
        self.threshold = threshold
        self.threshold_prune = threshold_prune
        self.cache = {}

        class Locks:
            checkin = threading.Lock()
            checkout = threading.Lock()
        self.locks = Locks()

        self.pruner = threading.Thread(target=self.prune)
        self.pruner.setDaemon(True)
        self.pruner.start()


    def one(self, query, params, process=None):
        return self._do_query(self.db.one, query, params, process)

    def all(self, query, params, process=None):
        if process is None:
            process = lambda g: list(g)
        return self._do_query(self.db.all, query, params, process)

    def _do_query(self, fetchfunc, query, params, process):
        """Given a function, a SQL string, a tuple, and a function, return ???.
        """

        # Compute a cache key.
        # ====================

        key = (query, params)


        # Check out an entry.
        # ===================
        # Each entry has its own lock, and "checking out" an entry means
        # acquiring that lock. If a queryset isn't yet in our cache, we first
        # "check in" a new dummy entry for it (and prevent other threads from
        # adding the same query), which will be populated presently.

        #thread_id = threading.currentThread().getName()[-1:] # for debugging
        #call_id = ''.join([random.choice(string.letters) for i in range(5)])

        self.locks.checkout.acquire()
        try:  # critical section
            if key in self.cache:

                # Retrieve an already cached query.
                # =================================
                # The cached entry may be a dummy. The best way to guarantee we
                # will catch this case is to simply refresh our entry after we
                # acquire its lock.

                entry = self.cache[key]
                entry.lock.acquire()
                entry = self.cache[key]

            else:

                # Add a new entry to our cache.
                # =============================

                dummy = Entry()
                dummy.lock.acquire()
                self.locks.checkin.acquire()
                try:  # critical section
                    if key in self.cache:
                        # Someone beat us to it. XXX: can this actually happen?
                        entry = self.cache[key]
                    else:
                        self.cache[key] = dummy
                        entry = dummy
                finally:
                    self.locks.checkin.release()

        finally:
            self.locks.checkout.release() # Now that we've checked out our
                                          # queryset, other threads are free to
                                          # check out other queries.


        # Process the query.
        # ==================

        try:  # critical section

            # Decide whether it's a hit or miss.
            # ==================================

            if time.time() - entry.timestamp < self.threshold:  # cache hit
                if entry.exc is not None:
                    raise entry.exc
                return entry.result

            else:                                               # cache miss
                try:                    # XXX uses postgres.py api, not dbapi2!
                    entry.result = fetchfunc(query, params)
                    if process is not None:
                        entry.result = process(entry.result)
                    entry.exc = None
                except:
                    entry.result = None
                    entry.exc = ( FormattingError(traceback.format_exc())
                                , sys.exc_info()[2]
                                 )


            # Check the queryset back in.
            # ===========================

            self.locks.checkin.acquire()
            try:  # critical section
                entry.timestamp = time.time()
                self.cache[key] = entry
                if entry.exc is not None:
                    raise entry.exc[0]
                else:
                    return entry.result
            finally:
                self.locks.checkin.release()

        finally:
            entry.lock.release()


    def prune(self):
        """Periodically remove any stale queries in our cache.
        """

        last = 0  # timestamp of last pruning run

        while 1:

            if time.time() < last + self.threshold_prune:
                # Not time to prune yet.
                time.sleep(0.2)
                continue

            self.locks.checkout.acquire()
            try:  # critical section

                for key, entry in tuple(self.cache.items()):

                    # Check out the entry.
                    # ====================
                    # If the entry is currently in use, skip it.

                    available = entry.lock.acquire(False)
                    if not available:
                        continue


                    # Remove the entry if it is too old.
                    # ==================================

                    try:  # critical section
                        if time.time() - entry.timestamp > self.threshold_prune:
                            del self.cache[key]
                    finally:
                        entry.lock.release()

            finally:
                self.locks.checkout.release()

            last = time.time()

########NEW FILE########
__FILENAME__ = timer
import time

def start():
    return {'start_time': time.time()}

def end(start_time, website):
    if website.log_metrics:
        print("count#requests=1")
        response_time = time.time() - start_time
        print("measure#response_time={}ms".format(response_time * 1000))

########NEW FILE########
__FILENAME__ = username
from psycopg2 import IntegrityError
import random

def gen_random_usernames():
    """Yield up to 100 random 12-hex-digit unicodes.

    We raise :py:exc:`StopIteration` after 100 usernames as a safety
    precaution.

    """
    seatbelt = 0
    while 1:
        yield hex(int(random.random() * 16**12))[2:].zfill(12).decode('ASCII')
        seatbelt += 1
        if seatbelt > 100:
            raise StopIteration


def reserve_a_random_username(txn):
    """Reserve a random username.

    :param txn: a :py:class:`psycopg2.cursor` managed as a :py:mod:`postgres`
        transaction
    :database: one ``INSERT`` on average
    :returns: a 12-hex-digit unicode
    :raises: :py:class:`StopIteration` if no acceptable username is found
        within 100 attempts

    The returned value is guaranteed to have been reserved in the database.

    """
    for username in gen_random_usernames():
        try:
            txn.execute( "INSERT INTO participants (username, username_lower) "
                         "VALUES (%s, %s)"
                       , (username, username.lower())
                        )
        except IntegrityError:  # Collision, try again with another value.
            pass
        else:
            break

    return username

########NEW FILE########
__FILENAME__ = wireup
"""Wireup
"""
from __future__ import absolute_import, division, print_function, unicode_literals
import os

import aspen
import balanced
import gittip
import raven
import stripe
import mandrill
from environment import Environment, is_yesish
from gittip.elsewhere import PlatformRegistry
from gittip.elsewhere.bitbucket import Bitbucket
from gittip.elsewhere.bountysource import Bountysource
from gittip.elsewhere.github import GitHub
from gittip.elsewhere.openstreetmap import OpenStreetMap
from gittip.elsewhere.twitter import Twitter
from gittip.elsewhere.venmo import Venmo
from gittip.models.account_elsewhere import AccountElsewhere
from gittip.models.community import Community
from gittip.models.participant import Participant
from gittip.models.email_address_with_confirmation import EmailAddressWithConfirmation
from gittip.models import GittipDB


def canonical(env):
    gittip.canonical_scheme = env.canonical_scheme
    gittip.canonical_host = env.canonical_host


def db(env):
    dburl = env.database_url
    maxconn = env.database_maxconn
    db = GittipDB(dburl, maxconn=maxconn)

    db.register_model(Community)
    db.register_model(AccountElsewhere)
    db.register_model(Participant)
    db.register_model(EmailAddressWithConfirmation)

    return db

def mail(env):
    mandrill_client = mandrill.Mandrill(env.mandrill_key)

    return mandrill_client

def billing(env):
    stripe.api_key = env.stripe_secret_api_key
    stripe.publishable_api_key = env.stripe_publishable_api_key
    balanced.configure(env.balanced_api_secret)


def username_restrictions(website):
    if not hasattr(gittip, 'RESTRICTED_USERNAMES'):
        gittip.RESTRICTED_USERNAMES = os.listdir(website.www_root)


def make_sentry_teller(website):
    if not website.sentry_dsn:
        aspen.log_dammit("Won't log to Sentry (SENTRY_DSN is empty).")
        def noop(exception, request=None):
            pass
        return noop

    sentry = raven.Client(website.sentry_dsn)

    def tell_sentry(exception, request=None):

        # Decide if we care.
        # ==================

        if isinstance(exception, aspen.Response):

            if exception.code < 500:

                # Only log server errors to Sentry. For responses < 500 we use
                # stream-/line-based access logging. See discussion on:

                # https://github.com/gittip/www.gittip.com/pull/1560.

                return


        # Find a user.
        # ============
        # | is disallowed in usernames, so we can use it here to indicate
        # situations in which we can't get a username.

        request_context = getattr(request, 'context', None)
        user = {}
        user_id = 'n/a'
        if request_context is None:
            username = '| no context'
        else:
            user = request.context.get('user', None)
            if user is None:
                username = '| no user'
            else:
                is_anon = getattr(user, 'ANON', None)
                if is_anon is None:
                    username = '| no ANON'
                elif is_anon:
                    username = '| anonymous'
                else:
                    participant = getattr(user, 'participant', None)
                    if participant is None:
                        username = '| no participant'
                    else:
                        username = getattr(user.participant, 'username', None)
                        if username is None:
                            username = '| no username'
                        else:
                            user_id = user.participant.id
                            username = username.encode('utf8')
                            user = { 'id': user_id
                                   , 'is_admin': user.participant.is_admin
                                   , 'is_suspicious': user.participant.is_suspicious
                                   , 'claimed_time': user.participant.claimed_time.isoformat()
                                   , 'url': 'https://www.gittip.com/{}/'.format(username)
                                    }


        # Fire off a Sentry call.
        # =======================

        tags = { 'username': username
               , 'user_id': user_id
                }
        extra = { 'filepath': getattr(request, 'fs', None)
                , 'request': str(request).splitlines()
                , 'user': user
                 }
        result = sentry.captureException(tags=tags, extra=extra)


        # Emit a reference string to stdout.
        # ==================================

        ident = sentry.get_ident(result)
        aspen.log_dammit('Exception reference: ' + ident)

    return tell_sentry


def nanswers(env):
    from gittip.models import participant
    participant.NANSWERS_THRESHOLD = env.nanswers_threshold


class BadEnvironment(SystemExit):
    pass


def accounts_elsewhere(website, env):

    twitter = Twitter(
        website.asset_url,
        env.twitter_consumer_key,
        env.twitter_consumer_secret,
        env.twitter_callback,
    )
    github = GitHub(
        website.asset_url,
        env.github_client_id,
        env.github_client_secret,
        env.github_callback,
    )
    bitbucket = Bitbucket(
        website.asset_url,
        env.bitbucket_consumer_key,
        env.bitbucket_consumer_secret,
        env.bitbucket_callback,
    )
    openstreetmap = OpenStreetMap(
        website.asset_url,
        env.openstreetmap_consumer_key,
        env.openstreetmap_consumer_secret,
        env.openstreetmap_callback,
        env.openstreetmap_api_url,
        env.openstreetmap_auth_url,
    )
    bountysource = Bountysource(
        website.asset_url,
        None,
        env.bountysource_api_secret,
        env.bountysource_callback,
        env.bountysource_api_host,
        env.bountysource_www_host,
    )
    venmo = Venmo(
        website.asset_url,
        env.venmo_client_id,
        env.venmo_client_secret,
        env.venmo_callback,
    )

    signin_platforms = [twitter, github, bitbucket, openstreetmap]
    website.signin_platforms = PlatformRegistry(signin_platforms)
    AccountElsewhere.signin_platforms_names = tuple(p.name for p in signin_platforms)

    # For displaying "Connected Accounts"
    website.social_profiles = [twitter, github, bitbucket, openstreetmap, bountysource]

    all_platforms = signin_platforms + [bountysource, venmo]
    website.platforms = AccountElsewhere.platforms = PlatformRegistry(all_platforms)


def other_stuff(website, env):
    website.asset_url = env.gittip_asset_url.replace('%version', website.version)
    website.cache_static = env.gittip_cache_static
    website.compress_assets = env.gittip_compress_assets

    website.segment_key = env.segment_key
    website.sentry_dsn = env.sentry_dsn

    website.min_threads = env.min_threads
    website.log_busy_threads_every = env.log_busy_threads_every
    website.log_metrics = env.log_metrics


def env():
    env = Environment(
        DATABASE_URL                    = unicode,
        CANONICAL_HOST                  = unicode,
        CANONICAL_SCHEME                = unicode,
        MIN_THREADS                     = int,
        DATABASE_MAXCONN                = int,
        GITTIP_ASSET_URL                = unicode,
        GITTIP_CACHE_STATIC             = is_yesish,
        GITTIP_COMPRESS_ASSETS          = is_yesish,
        STRIPE_SECRET_API_KEY           = unicode,
        STRIPE_PUBLISHABLE_API_KEY      = unicode,
        BALANCED_API_SECRET             = unicode,
        #DEBUG                           = unicode,
        GITHUB_CLIENT_ID                = unicode,
        GITHUB_CLIENT_SECRET            = unicode,
        GITHUB_CALLBACK                 = unicode,
        BITBUCKET_CONSUMER_KEY          = unicode,
        BITBUCKET_CONSUMER_SECRET       = unicode,
        BITBUCKET_CALLBACK              = unicode,
        TWITTER_CONSUMER_KEY            = unicode,
        TWITTER_CONSUMER_SECRET         = unicode,
        TWITTER_CALLBACK                = unicode,
        BOUNTYSOURCE_API_SECRET         = unicode,
        BOUNTYSOURCE_CALLBACK           = unicode,
        BOUNTYSOURCE_API_HOST           = unicode,
        BOUNTYSOURCE_WWW_HOST           = unicode,
        VENMO_CLIENT_ID                 = unicode,
        VENMO_CLIENT_SECRET             = unicode,
        VENMO_CALLBACK                  = unicode,
        OPENSTREETMAP_CONSUMER_KEY      = unicode,
        OPENSTREETMAP_CONSUMER_SECRET   = unicode,
        OPENSTREETMAP_CALLBACK          = unicode,
        OPENSTREETMAP_API_URL           = unicode,
        OPENSTREETMAP_AUTH_URL          = unicode,
        NANSWERS_THRESHOLD              = int,
        UPDATE_HOMEPAGE_EVERY           = int,
        SEGMENT_KEY                     = unicode,
        SENTRY_DSN                      = unicode,
        LOG_BUSY_THREADS_EVERY          = int,
        LOG_METRICS                     = is_yesish,
        MANDRILL_KEY                    = unicode,
    )


    # Error Checking
    # ==============

    if env.malformed:
        these = len(env.malformed) != 1 and 'these' or 'this'
        plural = len(env.malformed) != 1 and 's' or ''
        aspen.log_dammit("=" * 42)
        aspen.log_dammit( "Oh no! Gittip.com couldn't understand %s " % these
                        , "environment variable%s:" % plural
                         )
        aspen.log_dammit(" ")
        for key, err in env.malformed:
            aspen.log_dammit("  {} ({})".format(key, err))
        aspen.log_dammit(" ")
        aspen.log_dammit("See ./default_local.env for hints.")

        aspen.log_dammit("=" * 42)
        keys = ', '.join([key for key in env.malformed])
        raise BadEnvironment("Malformed envvar{}: {}.".format(plural, keys))

    if env.missing:
        these = len(env.missing) != 1 and 'these' or 'this'
        plural = len(env.missing) != 1 and 's' or ''
        aspen.log_dammit("=" * 42)
        aspen.log_dammit( "Oh no! Gittip.com needs %s missing " % these
                        , "environment variable%s:" % plural
                         )
        aspen.log_dammit(" ")
        for key in env.missing:
            aspen.log_dammit("  " + key)
        aspen.log_dammit(" ")
        aspen.log_dammit( "(Sorry, we must've started looking for "
                        , "%s since you last updated Gittip!)" % these
                         )
        aspen.log_dammit(" ")
        aspen.log_dammit("Running Gittip locally? Edit ./local.env.")
        aspen.log_dammit("Running the test suite? Edit ./tests/env.")
        aspen.log_dammit(" ")
        aspen.log_dammit("See ./default_local.env for hints.")

        aspen.log_dammit("=" * 42)
        keys = ', '.join([key for key in env.missing])
        raise BadEnvironment("Missing envvar{}: {}.".format(plural, keys))

    return env

########NEW FILE########
__FILENAME__ = gittip
#!/usr/bin/env python
"""\
Gittip
~~~~~~

A personal funding platform.

Dependencies:
- Python 2.7
- Postgresql 9.2

To run:
$ gittip.py

This will also initialize a local environment on the first run.
"""

import os
import sys
import shutil
from subprocess import check_call, check_output, STDOUT, CalledProcessError


is_win = sys.platform.startswith('win')
bin_dir = 'Scripts' if is_win else 'bin'
ext = '.exe' if is_win else ''

default_port = 8537
vendor_path = 'vendor'
env_path = 'env'
requirements_installed_path = os.path.join(env_path, '.requirements_installed')
bin_path = os.path.join(env_path, bin_dir)
default_config_path = 'default_local.env'
config_path = 'local.env'
virtualenv_path = os.path.join(vendor_path, 'virtualenv-1.9.1.py')
pip_path = os.path.join(bin_path, 'pip' + ext)
swaddle_path = os.path.join(bin_path, 'swaddle' + ext)
aspen_path = os.path.join(bin_path, 'aspen' + ext)


def main():
    # TODO: Handle command-line arguments to override default config values
    #  e.g. the address and port to serve on, whether to run tests, etc

    try:
        bootstrap_environment()
    except CalledProcessError as ex:
        print ex.output
    except EnvironmentError as ex:
        print 'Error:', ex
        return 1

    run_server()


def bootstrap_environment():
    ensure_dependencies()
    init_config()
    init_virtualenv()
    install_requirements()


def ensure_dependencies():
    if not shell('python', '--version', capture=True).startswith('Python 2.7'):
        raise EnvironmentError('Python 2.7 is required.')

    try:
        shell('pg_config' + ext, capture=True)
    except OSError as e:
        if e.errno != os.errno.ENOENT:
            raise
        raise EnvironmentError('Postgresql is required. (Make sure pg_config is on your PATH.)')


def init_config():
    if os.path.exists(config_path):
        return

    print 'Creating a %s file...' % config_path
    shutil.copyfile(default_config_path, config_path)


def init_virtualenv():
    if os.path.exists(env_path):
        return

    print 'Initializing virtualenv at %s...' % env_path

    shell('python', virtualenv_path,
          '--unzip-setuptools',
          '--prompt="[gittip] "',
          '--never-download',
          '--extra-search-dir=' + vendor_path,
          '--distribute',
          env_path)


def install_requirements():
    # TODO: Detect when requirements.txt changes instead of checking for a file
    if os.path.exists(requirements_installed_path):
        return

    print 'Installing requirements...'

    shell(pip_path, 'install', '-r', 'requirements.txt')
    shell(pip_path, 'install', os.path.join(vendor_path, 'nose-1.1.2.tar.gz'))
    shell(pip_path, 'install', '-e', '.')

    open(requirements_installed_path, 'w').close()


def run_server():
    # TODO: Wait for Aspen to quit before exiting
    shell(swaddle_path, config_path, aspen_path)


def shell(*args, **kwargs):
    if kwargs.pop('capture', None):
        return check_output(args, stderr=STDOUT, **kwargs)
    return check_call(args, **kwargs)


if __name__ == '__main__':
    sys.exit(main())

########NEW FILE########
__FILENAME__ = test_anonymous_json
from __future__ import print_function, unicode_literals

from aspen import json
from gittip.testing import Harness


class Tests(Harness):

    def setUp(self):
        Harness.setUp(self)
        self.make_participant('alice')

    def hit_anonymous(self, method='GET', expected_code=200, **kw):
        response = self.client.hit(method, "/alice/anonymous.json", auth_as='alice', **kw)
        if response.code != expected_code:
            print(response.body)
        return response


    def test_participant_can_get_their_anonymity_settings(self):
        response = self.hit_anonymous('GET')
        actual = json.loads(response.body)
        assert actual == {'giving': False, 'receiving': False}

    def test_participant_can_toggle_anonymous_giving(self):
        response = self.hit_anonymous('POST', data={'toggle': 'giving'})
        actual = json.loads(response.body)
        assert actual['giving'] is True

    def test_participant_can_toggle_anonymous_receiving(self):
        response = self.hit_anonymous('POST', data={'toggle': 'receiving'})
        actual = json.loads(response.body)
        assert actual['receiving'] is True

    def test_participant_can_toggle_anonymous_giving_back(self):
        response = self.hit_anonymous('POST', data={'toggle': 'giving'})
        response = self.hit_anonymous('POST', data={'toggle': 'giving'})
        actual = json.loads(response.body)['giving']
        assert actual is False

    def test_participant_can_toggle_anonymous_receiving_back(self):
        response = self.hit_anonymous('POST', data={'toggle': 'receiving'})
        response = self.hit_anonymous('POST', data={'toggle': 'receiving'})
        actual = json.loads(response.body)['receiving']
        assert actual is False

########NEW FILE########
__FILENAME__ = test_billing
from __future__ import absolute_import, division, print_function, unicode_literals

import balanced
import mock

from gittip import billing
from gittip.security import authentication
from gittip.testing import Harness
from gittip.testing.balanced import BalancedHarness
from gittip.models.participant import Participant


class TestBalancedCard(BalancedHarness):

    def test_balanced_card_basically_works(self):
        balanced.Card.fetch(self.card_href) \
                     .associate_to_customer(self.balanced_customer_href)

        expected = {
            'id': self.balanced_customer_href,
            'last_four': 'xxxxxxxxxxxx1111',
            'last4': 'xxxxxxxxxxxx1111',
            'expiration_month': 10,
            'expiration_year': 2020,
            'address_1': '123 Main Street',
            'address_2': 'Box 2',
            'state': 'Confusion',
            'zip': '90210',
        }
        card = billing.BalancedCard(self.balanced_customer_href)
        actual = dict([(name, card[name]) for name in expected])
        assert actual == expected

    def test_credit_card_page_shows_card_missing(self):
        expected = 'Your credit card is <em id="status">missing'
        actual = self.client.GET('/credit-card.html', auth_as='alice').body.decode('utf8')
        assert expected in actual

    def test_credit_card_page_loads_when_there_is_a_card(self):
        self.db.run( "UPDATE participants SET balanced_customer_href=%s WHERE username='alice'"
                   , (self.balanced_customer_href,)
                    )
        billing.associate( self.db
                         , 'credit card'
                         , 'alice'
                         , self.balanced_customer_href
                         , self.card_href
                          )

        expected = 'Your credit card is <em id="status">working'
        actual = self.client.GET('/credit-card.html', auth_as='alice').body.decode('utf8')
        assert expected in actual

    def test_credit_card_page_loads_when_there_is_an_account_but_no_card(self):
        self.db.run( "UPDATE participants "
                     "SET balanced_customer_href=%s, last_bill_result='NoResultFound()'"
                     "WHERE username='alice'"
                   , (self.balanced_customer_href,)
                    )

        expected = 'Your credit card is <em id="status">failing'
        actual = self.client.GET('/credit-card.html', auth_as='alice').body.decode('utf8')
        assert expected in actual

    @mock.patch('balanced.Customer')
    def test_balanced_card_gives_class_name_instead_of_KeyError(self, ba):
        card = mock.Mock()

        balanced_account = ba.fetch.return_value
        balanced_account.href = self.balanced_customer_href
        balanced_account.cards = mock.Mock()
        balanced_account.cards.filter.return_value.all.return_value = [card]

        card = billing.BalancedCard(self.balanced_customer_href)

        expected = mock.Mock.__name__
        actual = card['nothing'].__class__.__name__

        assert actual == expected

    def test_balanced_works_with_old_urls(self):
        # gittip will have a combination of old style from v1
        # and new urls from v1.1
        balanced.Card.fetch(self.card_href).associate_to_customer(
            self.balanced_customer_href
        )
        # do not actually do this in any real system
        # but construct the url using the id from the
        # customer and marketplace on the new api
        # to match the format of that of the old one
        url_user = '/v1/marketplaces/{}/accounts/{}'.format(
            self.balanced_marketplace.id,
            self.balanced_customer_href.split('/customers/')[1])

        card = billing.BalancedCard(url_user)

        assert card._thing.href == self.card_href


class TestStripeCard(Harness):

    @mock.patch('stripe.Customer')
    def test_stripe_card_basically_works(self, sc):
        active_card = {}
        active_card['last4'] = '1234'
        active_card['exp_month'] = 10
        active_card['exp_year'] = 2020
        active_card['address_line1'] = "123 Main Street"
        active_card['address_line2'] = "Box 2"
        active_card['address_state'] = "Confusion"
        active_card['address_zip'] = "90210"

        stripe_customer = sc.retrieve.return_value
        stripe_customer.id = 'deadbeef'
        stripe_customer.get = {'active_card': active_card}.get

        expected = {
            'id': 'deadbeef',
            'last4': '************1234',
            'expiration_month': 10,
            'expiration_year': 2020,
            'address_1': '123 Main Street',
            'address_2': 'Box 2',
            'state': 'Confusion',
            'zip': '90210'
        }
        card = billing.StripeCard('deadbeef')
        actual = dict([(name, card[name]) for name in expected])
        assert actual == expected

    @mock.patch('stripe.Customer')
    def test_stripe_card_gives_empty_string_instead_of_KeyError(self, sc):
        stripe_customer = sc.retrieve.return_value
        stripe_customer.id = 'deadbeef'
        stripe_customer.get = {'active_card': {}}.get

        expected = ''
        actual = billing.StripeCard('deadbeef')['nothing']
        assert actual == expected


class TestBalancedBankAccount(BalancedHarness):

    def test_balanced_bank_account(self):
        balanced.BankAccount.fetch(self.bank_account_href)\
                            .associate_to_customer(self.balanced_customer_href)

        ba_account = billing.BalancedBankAccount(self.balanced_customer_href)

        assert ba_account.is_setup

        with self.assertRaises(KeyError):
            ba_account.__getitem__('invalid')

        actual = ba_account['customer_href']
        expected = self.balanced_customer_href
        assert actual == expected

    def test_balanced_bank_account_not_setup(self):
        bank_account = billing.BalancedBankAccount(None)
        assert not bank_account.is_setup
        assert not bank_account['id']

    def test_balanced_bank_has_an_account_number(self):
        balanced.BankAccount.fetch(self.bank_account_href)\
                            .associate_to_customer(self.balanced_customer_href)

        bank_account = billing.BalancedBankAccount(self.balanced_customer_href)
        assert bank_account['account_number'] == 'xxx233a'


class TestBillingAssociate(BalancedHarness):

    def test_associate_valid_card(self):
        billing.associate(self.db, u"credit card", 'alice', None, self.card_href)

        user = authentication.User.from_username('alice')
        customer = balanced.Customer.fetch(user.participant.balanced_customer_href)
        cards = customer.cards.all()
        assert len(cards) == 1
        assert cards[0].href == self.card_href

    def test_associate_invalid_card(self): #, find):

        billing.associate( self.db
                         , u"credit card"
                         , 'alice'
                         , self.balanced_customer_href
                         , '/cards/CC123123123123',  # invalid href
                          )
        user = authentication.User.from_username('alice')
        # participant in db should be updated to reflect the error message of
        # last update
        assert user.participant.last_bill_result == '404 Client Error: NOT FOUND'

    def test_associate_bank_account_valid(self):

        billing.associate( self.db
                         , u"bank account"
                         , 'alice'
                         , self.balanced_customer_href
                         , self.bank_account_href
                          )

        #args, _ = find.call_args

        customer = balanced.Customer.fetch(self.balanced_customer_href)
        bank_accounts = customer.bank_accounts.all()
        assert len(bank_accounts) == 1
        assert bank_accounts[0].href == self.bank_account_href


        user = authentication.User.from_username('alice')

        # participant in db should be updated
        assert user.participant.last_ach_result == ''

    def test_associate_bank_account_invalid(self):

        billing.associate( self.db
                         , u"bank account"
                         , 'alice'
                         , self.balanced_customer_href
                         , '/bank_accounts/BA123123123123123123' # invalid href
                          )

        # participant in db should be updated
        alice = Participant.from_username('alice')
        assert alice.last_ach_result == '404 Client Error: NOT FOUND'


class TestBillingClear(BalancedHarness):

    def test_clear(self):

        balanced.Card.fetch(self.card_href)\
                     .associate_to_customer(self.balanced_customer_href)

        MURKY = """\

            UPDATE participants
               SET balanced_customer_href='not null'
                 , last_bill_result='ooga booga'
             WHERE username=%s

        """
        self.db.run(MURKY, ('alice',))

        billing.clear(self.db, u"credit card", 'alice', self.balanced_customer_href)

        customer = balanced.Customer.fetch(self.balanced_customer_href)
        cards = customer.cards.all()
        assert len(cards) == 0

        user = authentication.User.from_username('alice')
        assert not user.participant.last_bill_result
        assert user.participant.balanced_customer_href

    def test_clear_bank_account(self):
        balanced.BankAccount.fetch(self.bank_account_href)\
                            .associate_to_customer(self.balanced_customer_href)

        MURKY = """\

            UPDATE participants
               SET balanced_customer_href='not null'
                 , last_ach_result='ooga booga'
             WHERE username=%s

        """
        self.db.run(MURKY, ('alice',))

        billing.clear(self.db, u"bank account", 'alice', self.balanced_customer_href)

        customer = balanced.Customer.fetch(self.balanced_customer_href)
        bank_accounts = customer.bank_accounts.all()
        assert len(bank_accounts) == 0

        user = authentication.User.from_username('alice')
        assert not user.participant.last_ach_result
        assert user.participant.balanced_customer_href


class TestBillingStoreError(BalancedHarness):

    def test_store_error_stores_bill_error(self):
        billing.store_error(self.db, u"credit card", "alice", "cheese is yummy")
        rec = self.db.one("select * from participants where "
                            "username='alice'")
        expected = "cheese is yummy"
        actual = rec.last_bill_result
        assert actual == expected

    def test_store_error_stores_ach_error(self):
        for message in ['cheese is yummy', 'cheese smells like my vibrams']:
            billing.store_error(self.db, u"bank account", 'alice', message)
            rec = self.db.one("select * from participants "
                                "where username='alice'")
            assert rec.last_ach_result == message

########NEW FILE########
__FILENAME__ = test_billing_payday
from __future__ import absolute_import, division, print_function, unicode_literals

from decimal import Decimal as D
from datetime import datetime, timedelta

import balanced
import mock
import pytest
from psycopg2 import IntegrityError

from aspen.utils import typecheck, utcnow
from gittip import billing
from gittip.billing.payday import Payday, skim_credit, LOOP_PACHINKO
from gittip.exceptions import NegativeBalance
from gittip.models.participant import Participant
from gittip.testing import Harness
from gittip.testing.balanced import BalancedHarness


class PaydayHarness(BalancedHarness):

    def setUp(self):
        BalancedHarness.setUp(self)
        self.payday = Payday(self.db)

    def fetch_payday(self):
        return self.db.one("SELECT * FROM paydays", back_as=dict)


class TestPaydayCharge(PaydayHarness):
    STRIPE_CUSTOMER_ID = 'cus_deadbeef'

    def get_numbers(self):
        """Return a list of 11 ints:

            nachs
            nach_failing
            nactive
            ncc_failing
            ncc_missing
            ncharges
            npachinko
            nparticipants
            ntippers
            ntips
            ntransfers

        """
        payday = self.fetch_payday()
        keys = [key for key in sorted(payday) if key.startswith('n')]
        return [payday[key] for key in keys]

    def test_charge_without_cc_details_returns_None(self):
        self.payday.start()
        actual = self.payday.charge(self.alice, D('1.00'))
        assert actual is None

    def test_charge_without_cc_marked_as_failure(self):
        self.payday.start()
        self.payday.charge(self.alice, D('1.00'))
        actual = self.get_numbers()
        assert actual == [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0]

    @mock.patch('gittip.billing.payday.Payday.charge_on_balanced')
    def test_charge_failure_returns_None(self, cob):
        cob.return_value = (D('10.00'), D('0.68'), 'FAILED')
        bob = self.make_participant('bob', last_bill_result="failure",
                                    balanced_customer_href=self.balanced_customer_href,
                                    stripe_customer_id=self.STRIPE_CUSTOMER_ID,
                                    is_suspicious=False)

        self.payday.start()
        actual = self.payday.charge(bob, D('1.00'))
        assert actual is None

    @mock.patch('gittip.billing.payday.Payday.charge_on_balanced')
    def test_charge_success_returns_None(self, charge_on_balanced):
        charge_on_balanced.return_value = (D('10.00'), D('0.68'), "")
        bob = self.make_participant('bob', last_bill_result="failure",
                                    balanced_customer_href=self.balanced_customer_href,
                                    stripe_customer_id=self.STRIPE_CUSTOMER_ID,
                                    is_suspicious=False)

        self.payday.start()
        actual = self.payday.charge(bob, D('1.00'))
        assert actual is None

    @mock.patch('gittip.billing.payday.Payday.charge_on_balanced')
    def test_charge_success_updates_participant(self, cob):
        cob.return_value = (D('10.00'), D('0.68'), "")
        bob = self.make_participant('bob', last_bill_result="failure",
                                    balanced_customer_href=self.balanced_customer_href,
                                    is_suspicious=False)
        self.payday.start()
        self.payday.charge(bob, D('1.00'))

        bob = Participant.from_username('bob')
        expected = {'balance': D('9.32'), 'last_bill_result': ''}
        actual = {'balance': bob.balance,
                  'last_bill_result': bob.last_bill_result}
        assert actual == expected

    @mock.patch('gittip.billing.payday.Payday.charge_on_balanced')
    def test_payday_moves_money(self, charge_on_balanced):
        charge_on_balanced.return_value = (D('10.00'), D('0.68'), "")
        day_ago = utcnow() - timedelta(days=1)
        bob = self.make_participant('bob', claimed_time=day_ago,
                                    last_bill_result='',
                                    is_suspicious=False)
        carl = self.make_participant('carl', claimed_time=day_ago,
                                     balanced_customer_href=self.balanced_customer_href,
                                     last_bill_result='',
                                     is_suspicious=False)
        carl.set_tip_to('bob', '6.00')  # under $10!
        self.payday.run()

        bob = Participant.from_username('bob')
        carl = Participant.from_username('carl')

        assert bob.balance == D('6.00')
        assert carl.balance == D('3.32')

    @mock.patch('gittip.billing.payday.Payday.charge_on_balanced')
    def test_payday_doesnt_move_money_from_a_suspicious_account(self, charge_on_balanced):
        charge_on_balanced.return_value = (D('10.00'), D('0.68'), "")
        day_ago = utcnow() - timedelta(days=1)
        bob = self.make_participant('bob', claimed_time=day_ago,
                                    last_bill_result='',
                                    is_suspicious=False)
        carl = self.make_participant('carl', claimed_time=day_ago,
                                     balanced_customer_href=self.balanced_customer_href,
                                     last_bill_result='',
                                     is_suspicious=True)
        carl.set_tip_to('bob', '6.00')  # under $10!
        self.payday.run()

        bob = Participant.from_username('bob')
        carl = Participant.from_username('carl')

        assert bob.balance == D('0.00')
        assert carl.balance == D('0.00')

    @mock.patch('gittip.billing.payday.Payday.charge_on_balanced')
    def test_payday_doesnt_move_money_to_a_suspicious_account(self, charge_on_balanced):
        charge_on_balanced.return_value = (D('10.00'), D('0.68'), "")
        day_ago = utcnow() - timedelta(days=1)
        bob = self.make_participant('bob', claimed_time=day_ago,
                                    last_bill_result='',
                                    is_suspicious=True)
        carl = self.make_participant('carl', claimed_time=day_ago,
                                     balanced_customer_href=self.balanced_customer_href,
                                     last_bill_result='',
                                     is_suspicious=False)
        carl.set_tip_to('bob', '6.00')  # under $10!
        self.payday.run()

        bob = Participant.from_username('bob')
        carl = Participant.from_username('carl')

        assert bob.balance == D('0.00')
        assert carl.balance == D('0.00')

    def test_payday_moves_money_with_balanced(self):
        day_ago = utcnow() - timedelta(days=1)
        paying_customer = balanced.Customer().save()
        balanced.Card.fetch(self.card_href)\
                     .associate_to_customer(paying_customer)
        balanced.BankAccount.fetch(self.bank_account_href)\
                            .associate_to_customer(self.balanced_customer_href)
        bob = self.make_participant('bob', claimed_time=day_ago,
                                    balanced_customer_href=self.balanced_customer_href,
                                    last_bill_result='',
                                    is_suspicious=False)
        carl = self.make_participant('carl', claimed_time=day_ago,
                                     balanced_customer_href=paying_customer.href,
                                     last_bill_result='',
                                     is_suspicious=False)
        carl.set_tip_to('bob', '15.00')
        self.payday.run()

        bob = Participant.from_username('bob')
        carl = Participant.from_username('carl')

        assert bob.balance == D('0.00')
        assert carl.balance == D('0.00')

        bob_customer = balanced.Customer.fetch(bob.balanced_customer_href)
        carl_customer = balanced.Customer.fetch(carl.balanced_customer_href)

        bob_credits = bob_customer.credits.all()
        assert len(bob_credits) == 1
        assert bob_credits[0].amount == 1500
        assert bob_credits[0].description == 'bob'

        carl_debits = carl_customer.debits.all()
        assert len(carl_debits) == 1
        assert carl_debits[0].amount == 1576  # base amount + fee
        assert carl_debits[0].description == 'carl'


class TestPaydayChargeOnBalanced(PaydayHarness):

    def setUp(self):
        PaydayHarness.setUp(self)


    def test_charge_on_balanced(self):

        # XXX Why can't we do this in BalancedHarness.setUp? Understand VCR!
        balanced_customer_href = unicode(balanced.Customer().save().href)
        balanced.Card.fetch(self.card_href) \
                     .associate_to_customer(balanced_customer_href)

        actual = self.payday.charge_on_balanced( 'whatever username'
                                               , balanced_customer_href
                                               , D('10.00') # $10.00 USD
                                                )
        assert actual == (D('10.61'), D('0.61'), '')

    def test_charge_on_balanced_small_amount(self):

        # XXX Why can't we do this in BalancedHarness.setUp? Understand VCR!
        balanced_customer_href = unicode(balanced.Customer().save().href)
        balanced.Card.fetch(self.card_href) \
                     .associate_to_customer(balanced_customer_href)

        actual = self.payday.charge_on_balanced( 'whatever username'
                                               , balanced_customer_href
                                               , D('0.06')  # $0.06 USD
                                                )
        assert actual == (D('10.00'), D('0.59'), '')

    def test_charge_on_balanced_failure(self):
        customer_with_bad_card = unicode(balanced.Customer().save().href)
        card = balanced.Card(
            number='4444444444444448',
            expiration_year=2020,
            expiration_month=12
        ).save()
        card.associate_to_customer(customer_with_bad_card)

        actual = self.payday.charge_on_balanced( 'whatever username'
                                               , customer_with_bad_card
                                               , D('10.00')
                                                )
        assert actual == (D('10.61'), D('0.61'), '402 Client Error: PAYMENT REQUIRED')

    def test_charge_on_balanced_handles_MultipleFoundError(self):
        card = balanced.Card(
            number='4242424242424242',
            expiration_year=2020,
            expiration_month=12
        ).save()
        card.associate_to_customer(self.balanced_customer_href)

        card = balanced.Card(
            number='4242424242424242',
            expiration_year=2030,
            expiration_month=12
        ).save()
        card.associate_to_customer(self.balanced_customer_href)

        actual = self.payday.charge_on_balanced( 'whatever username'
                                               , self.balanced_customer_href
                                               , D('10.00')
                                                )
        assert actual == (D('10.61'), D('0.61'), 'MultipleResultsFound()')

    def test_charge_on_balanced_handles_NotFoundError(self):
        customer_with_no_card = unicode(balanced.Customer().save().href)
        actual = self.payday.charge_on_balanced( 'whatever username'
                                               , customer_with_no_card
                                               , D('10.00')
                                                )
        assert actual == (D('10.61'), D('0.61'), 'NoResultFound()')


class TestBillingCharges(PaydayHarness):
    BALANCED_CUSTOMER_HREF = '/customers/CU123123123'
    BALANCED_TOKEN = u'/cards/CU123123123'

    STRIPE_CUSTOMER_ID = u'cus_deadbeef'

    def test_mark_missing_funding(self):
        self.payday.start()
        before = self.fetch_payday()
        missing_count = before['ncc_missing']

        self.payday.mark_missing_funding()

        after = self.fetch_payday()
        assert after['ncc_missing'] == missing_count + 1

    def test_mark_charge_failed(self):
        self.payday.start()
        before = self.fetch_payday()
        fail_count = before['ncc_failing']

        with self.db.get_cursor() as cursor:
            self.payday.mark_charge_failed(cursor)

        after = self.fetch_payday()
        assert after['ncc_failing'] == fail_count + 1

    def test_mark_charge_success(self):
        self.payday.start()
        charge_amount, fee = 4, 2

        with self.db.get_cursor() as cursor:
            self.payday.mark_charge_success(cursor, charge_amount, fee)

        # verify paydays
        actual = self.fetch_payday()
        assert actual['ncharges'] == 1

    @mock.patch('stripe.Charge')
    def test_charge_on_stripe(self, ba):
        amount_to_charge = D('10.00')  # $10.00 USD
        expected_fee = D('0.61')
        charge_amount, fee, msg = self.payday.charge_on_stripe(
            self.alice.username, self.STRIPE_CUSTOMER_ID, amount_to_charge)

        assert charge_amount == amount_to_charge + fee
        assert fee == expected_fee
        assert ba.find.called_with(self.STRIPE_CUSTOMER_ID)
        customer = ba.find.return_value
        assert customer.debit.called_with( int(charge_amount * 100)
                                         , self.alice.username
                                          )


class TestPrepHit(PaydayHarness):

    ## XXX Consider turning _prep_hit in to a class method
    #@classmethod
    #def setUpClass(cls):
    #    PaydayHarness.setUpClass()
    #    cls.payday = Payday(mock.Mock())  # Mock out the DB connection

    def prep(self, amount):
        """Given a dollar amount as a string, return a 3-tuple.

        The return tuple is like the one returned from _prep_hit, but with the
        second value, a log message, removed.

        """
        typecheck(amount, unicode)
        out = list(self.payday._prep_hit(D(amount)))
        out = [out[0]] + out[2:]
        return tuple(out)

    def test_prep_hit_basically_works(self):
        actual = self.payday._prep_hit(D('20.00'))
        expected = (2091,
                    u'Charging %s 2091 cents ($20.00 + $0.91 fee = $20.91) on %s ' u'... ',
                    D('20.91'), D('0.91'))
        assert actual == expected

    def test_prep_hit_full_in_rounded_case(self):
        actual = self.payday._prep_hit(D('5.00'))
        expected = (1000,
                    u'Charging %s 1000 cents ($9.41 [rounded up from $5.00] + ' u'$0.59 fee = $10.00) on %s ... ',
                    D('10.00'), D('0.59'))
        assert actual == expected

    def test_prep_hit_at_ten_dollars(self):
        actual = self.prep(u'10.00')
        expected = (1061, D('10.61'), D('0.61'))
        assert actual == expected

    def test_prep_hit_at_forty_cents(self):
        actual = self.prep(u'0.40')
        expected = (1000, D('10.00'), D('0.59'))
        assert actual == expected

    def test_prep_hit_at_fifty_cents(self):
        actual = self.prep(u'0.50')
        expected = (1000, D('10.00'), D('0.59'))
        assert actual == expected

    def test_prep_hit_at_sixty_cents(self):
        actual = self.prep(u'0.60')
        expected = (1000, D('10.00'), D('0.59'))
        assert actual == expected

    def test_prep_hit_at_eighty_cents(self):
        actual = self.prep(u'0.80')
        expected = (1000, D('10.00'), D('0.59'))
        assert actual == expected

    def test_prep_hit_at_nine_fifteen(self):
        actual = self.prep(u'9.15')
        expected = (1000, D('10.00'), D('0.59'))
        assert actual == expected

    def test_prep_hit_at_nine_forty(self):
        actual = self.prep(u'9.40')
        expected = (1000, D('10.00'), D('0.59'))
        assert actual == expected

    def test_prep_hit_at_nine_forty_one(self):
        actual = self.prep(u'9.41')
        expected = (1000, D('10.00'), D('0.59'))
        assert actual == expected

    def test_prep_hit_at_nine_forty_two(self):
        actual = self.prep(u'9.42')
        expected = (1002, D('10.02'), D('0.60'))
        assert actual == expected


class TestBillingPayday(PaydayHarness):
    BALANCED_CUSTOMER_HREF = '/customers/CU123123123'

    def test_move_pending_to_balance_for_teams_does_so(self):
        self.make_participant('A', number='plural', balance=2, pending=3)
        self.payday.move_pending_to_balance_for_teams()
        actual = self.db.one("SELECT balance FROM participants WHERE username='A'")
        assert actual == 5

    def test_move_pending_to_balance_for_teams_ignores_new_teams(self):
        # See https://github.com/gittip/www.gittip.com/issues/1684
        self.make_participant('A', number='plural', balance=0, pending=None)
        self.payday.move_pending_to_balance_for_teams()
        actual = self.db.one("SELECT balance FROM participants WHERE username='A'")
        assert actual == 0

    @mock.patch('gittip.models.participant.Participant.get_tips_and_total')
    def test_charge_and_or_transfer_no_tips(self, get_tips_and_total):
        self.db.run("""

            UPDATE participants
               SET balance=1
                 , balanced_customer_href=%s
                 , is_suspicious=False
             WHERE username='alice'

        """, (self.BALANCED_CUSTOMER_HREF,))

        amount = D('1.00')

        ts_start = self.payday.start()

        tips, total = [], amount

        initial_payday = self.fetch_payday()
        self.payday.charge_and_or_transfer(ts_start, self.alice, tips, total)
        resulting_payday = self.fetch_payday()

        assert initial_payday['ntippers'] == resulting_payday['ntippers']
        assert initial_payday['ntips'] == resulting_payday['ntips']
        assert initial_payday['nparticipants'] + 1 == resulting_payday['nparticipants']

    @mock.patch('gittip.models.participant.Participant.get_tips_and_total')
    @mock.patch('gittip.billing.payday.Payday.tip')
    def test_charge_and_or_transfer(self, tip, get_tips_and_total):
        self.db.run("""

            UPDATE participants
               SET balance=1
                 , balanced_customer_href=%s
                 , is_suspicious=False
             WHERE username='alice'

        """, (self.BALANCED_CUSTOMER_HREF,))

        ts_start = self.payday.start()
        now = datetime.utcnow()
        amount = D('1.00')
        like_a_tip = {'amount': amount, 'tippee': 'mjallday', 'ctime': now,
                      'claimed_time': now}

        # success, success, claimed, failure
        tips = [like_a_tip, like_a_tip, like_a_tip, like_a_tip]
        total = amount

        ts_start = datetime.utcnow()

        return_values = [1, 1, 0, -1]
        return_values.reverse()

        def tip_return_values(*_):
            return return_values.pop()

        tip.side_effect = tip_return_values

        initial_payday = self.fetch_payday()
        self.payday.charge_and_or_transfer(ts_start, self.alice, tips, total)
        resulting_payday = self.fetch_payday()

        assert initial_payday['ntippers'] + 1 == resulting_payday['ntippers']
        assert initial_payday['ntips'] + 2 == resulting_payday['ntips']
        assert initial_payday['nparticipants'] + 1 == resulting_payday['nparticipants']

    @mock.patch('gittip.models.participant.Participant.get_tips_and_total')
    @mock.patch('gittip.billing.payday.Payday.charge')
    def test_charge_and_or_transfer_short(self, charge, get_tips_and_total):
        self.db.run("""

            UPDATE participants
               SET balance=1
                 , balanced_customer_href=%s
                 , is_suspicious=False
             WHERE username='alice'

        """, (self.BALANCED_CUSTOMER_HREF,))

        now = datetime.utcnow()
        amount = D('1.00')
        like_a_tip = {'amount': amount, 'tippee': 'mjallday', 'ctime': now,
                      'claimed_time': now}

        # success, success, claimed, failure
        tips = [like_a_tip, like_a_tip, like_a_tip, like_a_tip]
        get_tips_and_total.return_value = tips, amount

        ts_start = datetime.utcnow()

        # In real-life we wouldn't be able to catch an error as the charge
        # method will swallow any errors and return false. We don't handle this
        # return value within charge_and_or_transfer but instead continue on
        # trying to use the remaining credit in the user's account to payout as
        # many tips as possible.
        #
        # Here we're hacking the system and throwing the exception so execution
        # stops since we're only testing this part of the method. That smells
        # like we need to refactor.

        charge.side_effect = Exception()
        with self.assertRaises(Exception):
            billing.charge_and_or_transfer(ts_start, self.alice)
        assert charge.called_with(self.alice.username,
                                  self.BALANCED_CUSTOMER_HREF,
                                  amount)

    @mock.patch('gittip.billing.payday.Payday.transfer')
    @mock.patch('gittip.billing.payday.log')
    def test_tip(self, log, transfer):
        self.db.run("""

            UPDATE participants
               SET balance=1
                 , balanced_customer_href=%s
                 , is_suspicious=False
             WHERE username='alice'

        """, (self.BALANCED_CUSTOMER_HREF,))
        amount = D('1.00')
        invalid_amount = D('0.00')
        tip = { 'amount': amount
              , 'tippee': self.alice.username
              , 'claimed_time': utcnow()
               }
        ts_start = utcnow()

        result = self.payday.tip(self.alice, tip, ts_start)
        assert result == 1
        result = transfer.called_with(self.alice.username, tip['tippee'],
                                      tip['amount'])
        assert result

        assert log.called_with('SUCCESS: $1 from mjallday to alice.')

        # XXX: Should these tests be broken down to a separate class with the
        # common setup factored in to a setUp method.

        # XXX: We should have constants to compare the values to
        # invalid amount
        tip['amount'] = invalid_amount
        result = self.payday.tip(self.alice, tip, ts_start)
        assert result == 0

        tip['amount'] = amount

        # XXX: We should have constants to compare the values to
        # not claimed
        tip['claimed_time'] = None
        result = self.payday.tip(self.alice, tip, ts_start)
        assert result == 0

        # XXX: We should have constants to compare the values to
        # claimed after payday
        tip['claimed_time'] = utcnow()
        result = self.payday.tip(self.alice, tip, ts_start)
        assert result == 0

        ts_start = utcnow()

        # XXX: We should have constants to compare the values to
        # transfer failed
        transfer.return_value = False
        result = self.payday.tip(self.alice, tip, ts_start)
        assert result == -1

    @mock.patch('gittip.billing.payday.log')
    def test_start_zero_out_and_get_participants(self, log):
        self.make_participant('bob', balance=10, claimed_time=None,
                              pending=1,
                              balanced_customer_href=self.BALANCED_CUSTOMER_HREF)
        self.make_participant('carl', balance=10, claimed_time=utcnow(),
                              pending=1,
                              balanced_customer_href=self.BALANCED_CUSTOMER_HREF)
        self.db.run("""

            UPDATE participants
               SET balance=0
                 , claimed_time=null
                 , pending=null
                 , balanced_customer_href=%s
             WHERE username='alice'

        """, (self.BALANCED_CUSTOMER_HREF,))

        ts_start = self.payday.start()

        self.payday.zero_out_pending(ts_start)
        participants = self.payday.get_participants(ts_start)

        expected_logging_call_args = [
            ('Starting a new payday.'),
            ('Payday started at {}.'.format(ts_start)),
            ('Zeroed out the pending column.'),
            ('Fetched participants.'),
        ]
        expected_logging_call_args.reverse()
        for args, _ in log.call_args_list:
            assert args[0] == expected_logging_call_args.pop()

        log.reset_mock()

        # run a second time, we should see it pick up the existing payday
        second_ts_start = self.payday.start()
        self.payday.zero_out_pending(second_ts_start)
        second_participants = self.payday.get_participants(second_ts_start)

        assert ts_start == second_ts_start
        participants = list(participants)
        second_participants = list(second_participants)

        # carl is the only valid participant as he has a claimed time
        assert len(participants) == 1
        assert participants == second_participants

        expected_logging_call_args = [
            ('Picking up with an existing payday.'),
            ('Payday started at {}.'.format(second_ts_start)),
            ('Zeroed out the pending column.'),
            ('Fetched participants.')]
        expected_logging_call_args.reverse()
        for args, _ in log.call_args_list:
            assert args[0] == expected_logging_call_args.pop()

    @mock.patch('gittip.billing.payday.log')
    def test_end(self, log):
        self.payday.start()
        self.payday.end()
        assert log.called_with('Finished payday.')

        # finishing the payday will set the ts_end date on this payday record
        # to now, so this will not return any result
        result = self.db.one("SELECT count(*) FROM paydays "
                             "WHERE ts_end > '1970-01-01'")
        assert result == 1

    @mock.patch('gittip.billing.payday.log')
    @mock.patch('gittip.billing.payday.Payday.start')
    @mock.patch('gittip.billing.payday.Payday.payin')
    @mock.patch('gittip.billing.payday.Payday.end')
    def test_payday(self, end, payin, init, log):
        ts_start = utcnow()
        init.return_value = (ts_start,)
        greeting = 'Greetings, program! It\'s PAYDAY!!!!'

        self.payday.run()

        assert log.called_with(greeting)
        assert init.call_count
        assert payin.called_with(init.return_value)
        assert end.call_count


class TestBillingTransfer(PaydayHarness):
    def setUp(self):
        PaydayHarness.setUp(self)
        self.payday.start()
        self.tipper = self.make_participant('lgtest')
        #self.balanced_customer_href = '/v1/marketplaces/M123/accounts/A123'

    def test_transfer(self):
        amount = D('1.00')
        sender = self.make_participant('test_transfer_sender', pending=0,
                                       balance=1)
        recipient = self.make_participant('test_transfer_recipient', pending=0,
                                          balance=1)

        result = self.payday.transfer( sender.username
                                     , recipient.username
                                     , amount
                                      )
        assert result == True

        # no balance remaining for a second transfer
        result = self.payday.transfer( sender.username
                                     , recipient.username
                                     , amount
                                      )
        assert result == False

    def test_debit_participant(self):
        amount = D('1.00')
        subject = self.make_participant('test_debit_participant', pending=0,
                                        balance=1)

        initial_amount = subject.balance

        with self.db.get_cursor() as cursor:
            self.payday.debit_participant(cursor, subject.username, amount)

        subject = Participant.from_username('test_debit_participant')

        expected = initial_amount - amount
        actual = subject.balance
        assert actual == expected

        # this will fail because not enough balance
        with self.db.get_cursor() as cursor:
            with self.assertRaises(NegativeBalance):
                self.payday.debit_participant(cursor, subject.username, amount)

    def test_skim_credit(self):
        actual = skim_credit(D('10.00'))
        assert actual == (D('10.00'), D('0.00'))

    def test_credit_participant(self):
        amount = D('1.00')
        subject = self.make_participant('test_credit_participant', pending=0,
                                        balance=1)

        initial_amount = subject.pending

        with self.db.get_cursor() as cursor:
            self.payday.credit_participant(cursor, subject.username, amount)

        subject = Participant.from_username('test_credit_participant') # reload

        expected = initial_amount + amount
        actual = subject.pending
        assert actual == expected

    def test_record_transfer(self):
        amount = D('1.00')
        subjects = ['jim', 'kate', 'bob']

        for subject in subjects:
            self.make_participant(subject, balance=1, pending=0)

        with self.db.get_cursor() as cursor:
            # Tip 'jim' twice
            for recipient in ['jim'] + subjects:
                self.payday.record_transfer( cursor
                                           , self.tipper.username
                                           , recipient
                                           , amount
                                            )

        for subject in subjects:
            # 'jim' is tipped twice
            expected = amount * 2 if subject == 'jim' else amount
            actual = self.db.one( "SELECT sum(amount) FROM transfers "
                                  "WHERE tippee=%s"
                                , (subject,)
                                 )
            assert actual == expected

    def test_record_transfer_invalid_participant(self):
        amount = D('1.00')

        with self.db.get_cursor() as cursor:
            with self.assertRaises(IntegrityError):
                self.payday.record_transfer( cursor
                                           , 'idontexist'
                                           , 'nori'
                                           , amount
                                            )

    def test_mark_transfer(self):
        amount = D('1.00')

        # Forces a load with current state in dict
        before_transfer = self.fetch_payday()

        with self.db.get_cursor() as cursor:
            self.payday.mark_transfer(cursor, amount)

        # Forces a load with current state in dict
        after_transfer = self.fetch_payday()

        expected = before_transfer['ntransfers'] + 1
        actual = after_transfer['ntransfers']
        assert actual == expected

        expected = before_transfer['transfer_volume'] + amount
        actual = after_transfer['transfer_volume']
        assert actual == expected

    def test_record_credit_updates_balance(self):
        self.payday.record_credit( amount=D("-1.00")
                                 , fee=D("0.41")
                                 , error=""
                                 , username="alice"
                                  )
        alice = Participant.from_username('alice')
        assert alice.balance == D("0.59")

    def test_record_credit_fails_if_negative_balance(self):
        pytest.raises( NegativeBalance
                     , self.payday.record_credit
                     , amount=D("10.00")
                     , fee=D("0.41")
                     , error=""
                     , username="alice"
                      )

    def test_record_credit_doesnt_update_balance_if_error(self):
        self.payday.record_credit( amount=D("-1.00")
                                 , fee=D("0.41")
                                 , error="SOME ERROR"
                                 , username="alice"
                                  )
        alice = Participant.from_username('alice')
        assert alice.balance == D("0.00")


class TestPachinko(Harness):

    def setUp(self):
        Harness.setUp(self)
        self.payday = Payday(self.db)

    def test_get_participants_gets_participants(self):
        a_team = self.make_participant('a_team', claimed_time='now', number='plural', balance=20)
        a_team.add_member(self.make_participant('alice', claimed_time='now'))
        a_team.add_member(self.make_participant('bob', claimed_time='now'))

        ts_start = self.payday.start()

        actual = [p.username for p in self.payday.get_participants(ts_start)]
        expected = ['a_team', 'alice', 'bob']
        assert actual == expected

    def test_pachinko_pachinkos(self):
        a_team = self.make_participant('a_team', claimed_time='now', number='plural', balance=20, \
                                                                                         pending=0)
        a_team.add_member(self.make_participant('alice', claimed_time='now', balance=0, pending=0))
        a_team.add_member(self.make_participant('bob', claimed_time='now', balance=0, pending=0))

        ts_start = self.payday.start()

        participants = self.payday.genparticipants(ts_start, LOOP_PACHINKO)
        self.payday.pachinko(ts_start, participants)

        assert Participant.from_username('alice').pending == D('0.01')
        assert Participant.from_username('bob').pending == D('0.01')

    def test_pachinko_sees_current_take(self):
        a_team = self.make_participant('a_team', claimed_time='now', number='plural', balance=20, \
                                                                                         pending=0)
        alice = self.make_participant('alice', claimed_time='now', balance=0, pending=0)
        a_team.add_member(alice)
        a_team.set_take_for(alice, D('1.00'), alice)

        ts_start = self.payday.start()

        participants = self.payday.genparticipants(ts_start, LOOP_PACHINKO)
        self.payday.pachinko(ts_start, participants)

        assert Participant.from_username('alice').pending == D('1.00')

    def test_pachinko_ignores_take_set_after_payday_starts(self):
        a_team = self.make_participant('a_team', claimed_time='now', number='plural', balance=20, \
                                                                                         pending=0)
        alice = self.make_participant('alice', claimed_time='now', balance=0, pending=0)
        a_team.add_member(alice)
        a_team.set_take_for(alice, D('0.33'), alice)

        ts_start = self.payday.start()
        a_team.set_take_for(alice, D('1.00'), alice)

        participants = self.payday.genparticipants(ts_start, LOOP_PACHINKO)
        self.payday.pachinko(ts_start, participants)

        assert Participant.from_username('alice').pending == D('0.33')

    def test_pachinko_ignores_take_thats_already_been_processed(self):
        a_team = self.make_participant('a_team', claimed_time='now', number='plural', balance=20, \
                                                                                         pending=0)
        alice = self.make_participant('alice', claimed_time='now', balance=0, pending=0)
        a_team.add_member(alice)
        a_team.set_take_for(alice, D('0.33'), alice)

        ts_start = self.payday.start()
        a_team.set_take_for(alice, D('1.00'), alice)

        for i in range(4):
            participants = self.payday.genparticipants(ts_start, LOOP_PACHINKO)
            self.payday.pachinko(ts_start, participants)

        assert Participant.from_username('alice').pending == D('0.33')

########NEW FILE########
__FILENAME__ = test_bitcoin_json
from __future__ import print_function, unicode_literals

import json

from gittip.testing import Harness


class Tests(Harness):
    def change_bitcoin_address(self, address, user='alice', should_fail=True):
        self.make_participant('alice')
        if should_fail:
            response = self.client.PxST("/alice/bitcoin.json",
                               {'bitcoin_address': address,},
                                auth_as=user
            )
        else:
            response = self.client.POST("/alice/bitcoin.json",
                               {'bitcoin_address': address,},
                                auth_as=user
            )
        return response

    def test_participant_can_change_their_address(self):
        response = self.change_bitcoin_address(
            '17NdbrSGoUotzeGCcMMCqnFkEvLymoou9j', should_fail=False)
        actual = json.loads(response.body)['bitcoin_address']
        assert actual == '17NdbrSGoUotzeGCcMMCqnFkEvLymoou9j', actual

    def test_anonymous_gets_404(self):
        response = self.change_bitcoin_address(
            '17NdbrSGoUotzeGCcMMCqnFkEvLymoou9j', user=None)
        assert response.code == 404, response.code

    def test_invalid_is_400(self):
        response = self.change_bitcoin_address('12345')
        assert response.code == 400, response.code

########NEW FILE########
__FILENAME__ = test_charts_json
from __future__ import absolute_import, division, print_function, unicode_literals

import datetime
import json

from gittip.billing.payday import Payday
from gittip.testing import Harness

def today():
    return datetime.datetime.utcnow().date().strftime('%Y-%m-%d')

class Tests(Harness):

    def make_participants_and_tips(self):
        alice = self.make_participant('alice', balance=10, claimed_time='now')
        bob = self.make_participant('bob', balance=10, claimed_time='now')
        self.make_participant('carl', claimed_time='now')
        self.db.run("""
            INSERT INTO EXCHANGES
                (amount, fee, participant) VALUES
                (10.00, 0.00, 'alice'),
                (10.00, 0.00, 'bob')
        """)
        self.make_participant('notactive', claimed_time='now')

        alice.set_tip_to('carl', '1.00')
        bob.set_tip_to('carl', '2.00')

        return alice, bob

    def run_payday(self):
        Payday(self.db).run()


    def test_no_payday_returns_empty_list(self):
        self.make_participants_and_tips()
        assert json.loads(self.client.GET('/carl/charts.json').body) == []

    def test_zeroth_payday_is_ignored(self):
        self.make_participants_and_tips()
        self.run_payday()   # zeroeth
        assert json.loads(self.client.GET('/carl/charts.json').body) == []

    def test_first_payday_comes_through(self):
        alice, bob = self.make_participants_and_tips()
        self.run_payday()   # zeroeth, ignored
        self.run_payday()   # first

        expected = [ { "date": today()
                     , "npatrons": 2
                     , "receipts": 3.00
                      }
                    ]
        actual = json.loads(self.client.GET('/carl/charts.json').body)

        assert actual == expected

    def test_second_payday_comes_through(self):
        alice, bob = self.make_participants_and_tips()
        self.run_payday()   # zeroth, ignored
        self.run_payday()   # first

        alice.set_tip_to('carl', '5.00')
        bob.set_tip_to('carl', '0.00')

        self.run_payday()   # second

        expected = [ { "date": today()
                     , "npatrons": 1 # most recent first
                     , "receipts": 5.00
                      }
                   , { "date": today()
                     , "npatrons": 2
                     , "receipts": 3.00
                      }
                    ]
        actual = json.loads(self.client.GET('/carl/charts.json').body)

        assert actual == expected

    def test_sandwiched_tipless_payday_comes_through(self):
        alice, bob = self.make_participants_and_tips()
        self.run_payday()   # zeroth, ignored
        self.run_payday()   # first

        # Oops! Sorry, Carl. :-(
        alice.set_tip_to('carl', '0.00')
        bob.set_tip_to('carl', '0.00')
        self.run_payday()   # second

        # Bouncing back ...
        alice.set_tip_to('carl', '5.00')
        self.run_payday()   # third

        expected = [ { "date": today()
                     , "npatrons": 1 # most recent first
                     , "receipts": 5.00
                      }
                   , { "date": today()
                     , "npatrons": 0
                     , "receipts": 0.00
                      }
                   , { "date": today()
                     , "npatrons": 2
                     , "receipts": 3.00
                      }
                    ]
        actual = json.loads(self.client.GET('/carl/charts.json').body)

        assert actual == expected

    def test_out_of_band_transfer_gets_included_with_prior_payday(self):
        alice, bob = self.make_participants_and_tips()
        self.run_payday()   # zeroth, ignored
        self.run_payday()   # first
        self.run_payday()   # second

        # Do an out-of-band transfer.
        self.db.run("UPDATE participants SET balance=balance - 4 WHERE username='alice'")
        self.db.run("UPDATE participants SET balance=balance + 4 WHERE username='carl'")
        self.db.run("INSERT INTO transfers (tipper, tippee, amount) VALUES ('alice', 'carl', 4)")

        self.run_payday()   # third

        expected = [ { "date": today()
                     , "npatrons": 2 # most recent first
                     , "receipts": 3.00
                      }
                   , { "date": today()
                     , "npatrons": 3  # Since this is rare, don't worry that we double-count alice.
                     , "receipts": 7.00
                      }
                   , { "date": today()
                     , "npatrons": 2
                     , "receipts": 3.00
                      }
                    ]
        actual = json.loads(self.client.GET('/carl/charts.json').body)

        assert actual == expected

    def test_never_received_gives_empty_array(self):
        alice, bob = self.make_participants_and_tips()
        self.run_payday()   # zeroeth, ignored
        self.run_payday()   # first
        self.run_payday()   # second
        self.run_payday()   # third

        expected = []
        actual = json.loads(self.client.GET('/alice/charts.json').body)

        assert actual == expected

    def test_transfer_volume(self):
        self.make_participants_and_tips()
        self.run_payday()
        self.run_payday()

        expected = { "date": today()
                   , "weekly_gifts": 3.0
                   , "charges": 0.0
                   , "withdrawals": 0.0
                   , "active_users": 3
                   , "total_users": 4
                   , "total_gifts": 6.0
                    }
        actual = json.loads(self.client.GET('/about/charts.json').body)[0]

        assert actual == expected

########NEW FILE########
__FILENAME__ = test_communities
from __future__ import absolute_import, division, print_function, unicode_literals

from gittip.testing import Harness


class Tests(Harness):

    def setUp(self):
        Harness.setUp(self)

        # Alice joins a community.
        self.alice = self.make_participant("alice", claimed_time='now', last_bill_result='')
        self.client.POST( '/for/communities.json'
                        , {'name': 'something', 'is_member': 'true'}
                        , auth_as='alice'
                         )

    def test_community_member_shows_up_on_community_listing(self):
        html = self.client.GET('/for/something/', want='response.body')
        assert html.count('alice') == 2  # entry in New Participants

    def test_givers_show_up_on_community_page(self):

        # Alice tips bob.
        self.make_participant("bob", claimed_time='now')
        self.alice.set_tip_to('bob', '1.00')

        html = self.client.GET('/for/something/', want='response.body')
        assert html.count('alice') == 4  # entries in both New Participants and Givers
        assert 'bob' not in html

    def test_givers_dont_show_up_if_they_give_zero(self):

        # Alice tips bob.
        self.make_participant("bob", claimed_time='now')
        self.alice.set_tip_to('bob', '1.00')
        self.alice.set_tip_to('bob', '0.00')

        html = self.client.GET('/for/something/', want='response.body')
        assert html.count('alice') == 2  # entry in New Participants only
        assert 'bob' not in html

    def test_receivers_show_up_on_community_page(self):

        # Bob tips alice.
        bob = self.make_participant("bob", claimed_time='now', last_bill_result='')
        bob.set_tip_to('alice', '1.00')

        html = self.client.GET('/for/something/', want='response.body')
        assert html.count('alice') == 4  # entries in both New Participants and Receivers
        assert 'bob' not in html

    def test_receivers_dont_show_up_if_they_receive_zero(self):

        # Bob tips alice.
        bob = self.make_participant("bob", claimed_time='now', last_bill_result='')
        bob.set_tip_to('alice', '1.00')
        bob.set_tip_to('alice', '0.00')  # zero out bob's tip

        html = self.client.GET('/for/something/', want='response.body')
        assert html.count('alice') == 2  # entry in New Participants only
        assert 'bob' not in html

    def test_community_listing_works_for_pristine_community(self):
        html = self.client.GET('/for/pristine/', want='response.body')
        assert 'first one here' in html

########NEW FILE########
__FILENAME__ = test_communities_json
from __future__ import unicode_literals

import json

from aspen.utils import utcnow
from gittip.testing import Harness

class TestCommunitiesJson(Harness):

    def test_post_name_pattern_none_returns_400(self):
        response = self.client.PxST('/for/communities.json', {'name': 'BadName!'})
        assert response.code == 400

    def test_post_is_member_not_bool_returns_400(self):
        response = self.client.PxST( '/for/communities.json'
                                   , {'name': 'Good Name', 'is_member': 'no'}
                                    )
        assert response.code == 400

    def test_post_can_join_community(self):
        self.make_participant("alice", claimed_time=utcnow())

        response = self.client.GET('/for/communities.json', auth_as='alice')
        assert len(json.loads(response.body)['communities']) == 0

        response = self.client.POST( '/for/communities.json'
                                   , {'name': 'Test', 'is_member': 'true'}
                                   , auth_as='alice'
                                    )

        communities = json.loads(response.body)['communities']
        assert len(communities) == 1

        actual = communities[0]['name']
        assert actual == 'Test'

    def test_post_can_leave_community(self):
        self.make_participant("alice", claimed_time=utcnow())

        response = self.client.POST( '/for/communities.json'
                                   , {'name': 'Test', 'is_member': 'true'}
                                   , auth_as='alice'
                                    )

        response = self.client.POST( '/for/communities.json'
                                   , {'name': 'Test', 'is_member': 'false'}
                                   , auth_as='alice'
                                    )

        response = self.client.GET('/for/communities.json', auth_as='alice')

        assert len(json.loads(response.body)['communities']) == 0

    def test_get_can_get_communities_for_user(self):
        self.make_participant("alice", claimed_time=utcnow())
        response = self.client.GET('/for/communities.json', auth_as='alice')
        assert len(json.loads(response.body)['communities']) == 0

    def test_get_can_get_communities_when_anon(self):
        response = self.client.GET('/for/communities.json')

        assert response.code == 200
        assert len(json.loads(response.body)['communities']) == 0

########NEW FILE########
__FILENAME__ = test_delete_elsewhere_json
from __future__ import absolute_import, division, print_function, unicode_literals

import json

from gittip.testing import Harness


class Tests(Harness):

    def test_delete_nonexistent(self):
        self.make_participant('alice', claimed_time='now', elsewhere='twitter')
        response = self.client.PxST('/alice/delete-elsewhere.json', {'platform': 'twitter', 'user_id': 'nonexistent'}, auth_as='alice')
        assert response.code == 400
        assert "not exist" in response.body

    def test_delete_last(self):
        platform, user_id = 'twitter', '1'
        self.make_elsewhere(platform, user_id, 'alice').opt_in('alice')
        data = dict(platform=platform, user_id=user_id)
        response = self.client.PxST('/alice/delete-elsewhere.json', data, auth_as='alice')
        assert response.code == 400
        assert "last login" in response.body

    def test_delete_last_login(self):
        platform, user_id = 'twitter', '1'
        alice, _ = self.make_elsewhere(platform, user_id, 'alice').opt_in('alice')
        self.make_elsewhere('venmo', '1', 'alice')
        alice.participant.take_over(('venmo', '1'))
        data = dict(platform=platform, user_id=user_id)
        response = self.client.PxST('/alice/delete-elsewhere.json', data, auth_as='alice')
        assert response.code == 400
        assert "last login" in response.body

    def test_delete_200(self):
        platform, user_id = 'twitter', '1'
        alice, _ = self.make_elsewhere(platform, user_id, 'alice').opt_in('alice')
        self.make_elsewhere('github', '1', 'alice')
        alice.participant.take_over(('github', '1'))
        data = dict(platform=platform, user_id=user_id)
        response = self.client.POST('/alice/delete-elsewhere.json', data, auth_as='alice')
        assert response.code == 200
        msg = json.loads(response.body)['msg']
        assert "OK" in msg

########NEW FILE########
__FILENAME__ = test_elsewhere
from __future__ import absolute_import, division, print_function, unicode_literals

from gittip.elsewhere import UserInfo
from gittip.models.account_elsewhere import AccountElsewhere
from gittip.testing import Harness
import gittip.testing.elsewhere as user_info_examples


class Tests(Harness):

    def test_associate_csrf(self):
        response = self.client.GxT('/on/github/associate?state=49b7c66246c7')
        assert response.code == 400

    def test_extract_user_info(self):
        for platform in self.platforms:
            user_info = getattr(user_info_examples, platform.name)()
            r = platform.extract_user_info(user_info)
            assert isinstance(r, UserInfo)
            assert r.user_id is not None
            assert len(r.user_id) > 0

    def test_opt_in_can_change_username(self):
        account = self.make_elsewhere('twitter', 1, 'alice')
        expected = 'bob'
        actual = account.opt_in('bob')[0].participant.username
        assert actual == expected

    def test_opt_in_doesnt_have_to_change_username(self):
        self.make_participant('bob')
        account = self.make_elsewhere('twitter', 1, 'alice')
        expected = account.participant.username # A random one.
        actual = account.opt_in('bob')[0].participant.username
        assert actual == expected

    def test_redirect_csrf(self):
        response = self.client.GxT('/on/github/redirect')
        assert response.code == 405

    def test_redirects(self, *classes):
        self.make_participant('alice')
        data = dict(action='opt-in', then='/', user_name='')
        for platform in self.platforms:
            platform.get_auth_url = lambda *a, **kw: ('', '', '')
            response = self.client.PxST('/on/%s/redirect' % platform.name,
                                        data, auth_as='alice')
            assert response.code == 302

    def test_upsert(self):
        for platform in self.platforms:
            user_info = getattr(user_info_examples, platform.name)()
            account = AccountElsewhere.upsert(platform.extract_user_info(user_info))
            assert isinstance(account, AccountElsewhere)

    def test_user_pages(self):
        for platform in self.platforms:
            alice = UserInfo( platform=platform.name
                            , user_id='0'
                            , user_name='alice'
                            , is_team=False
                            )
            platform.get_user_info = lambda *a: alice
            response = self.client.GET('/on/%s/alice/' % platform.name)
            assert response.code == 200
            assert 'has not joined' in response.body.decode('utf8')

########NEW FILE########
__FILENAME__ = test_elsewhere_public_json
from __future__ import print_function, unicode_literals

import json
#import datetime

#import pytz
from gittip.testing import Harness


class Tests(Harness):

    def test_returns_json_if_not_opted_in(self, *classes):
        for platform in self.platforms:
            self.make_elsewhere(platform.name, 1, 'alice')
            response = self.client.GET('/on/%s/alice/public.json' % platform.name)

            assert response.code == 200

            data = json.loads(response.body)
            assert data['on'] == platform.name

    def test_redirect_if_opted_in(self, *classes):
        self.make_participant('alice')
        for platform in self.platforms:
            account = self.make_elsewhere(platform.name, 1, 'alice')
            account.opt_in('alice')

            response = self.client.GxT('/on/%s/alice/public.json' % platform.name)

            assert response.code == 302

########NEW FILE########
__FILENAME__ = test_email_json
from __future__ import unicode_literals

import json

from gittip.testing import Harness

class TestMembernameJson(Harness):

    def change_email_address(self, address, user='alice', should_fail=True):
        self.make_participant("alice")

        if should_fail:
            response = self.client.PxST("/alice/email.json"
                , {'email': address,}
                , auth_as=user
            )
        else:
            response = self.client.POST("/alice/email.json"
                , {'email': address,}
                , auth_as=user
            )
        return response

    def test_participant_can_change_email(self):
        response = self.change_email_address('alice@gittip.com', should_fail=False)
        actual = json.loads(response.body)['email']
        assert actual == 'alice@gittip.com', actual

    def test_post_anon_returns_404(self):
        response = self.change_email_address('anon@gittip.com', user=None)
        assert response.code == 404, response.code

    def test_post_with_no_at_symbol_is_400(self):
        response = self.change_email_address('gittip.com')
        assert response.code == 400, response.code

    def test_post_with_no_period_symbol_is_400(self):
        response = self.change_email_address('test@gittip')
        assert response.code == 400, response.code

########NEW FILE########
__FILENAME__ = test_fake_data
from __future__ import print_function, unicode_literals

from gittip.utils import fake_data
from gittip.testing import Harness


class TestFakeData(Harness):
    """
    Ensure the fake_data script doesn't throw any exceptions
    """

    def test_fake_data(self):
        num_participants = 5
        num_tips = 5
        num_teams = 1
        num_transfers = 5
        fake_data.populate_db(self.db, num_participants, num_tips, num_teams, num_transfers)
        tips = self.db.all("SELECT * FROM tips")
        participants = self.db.all("SELECT * FROM participants")
        transfers = self.db.all("SELECT * FROM transfers")
        assert len(tips) == num_tips
        assert len(participants) == num_participants + num_teams
        assert len(transfers) == num_transfers

########NEW FILE########
__FILENAME__ = test_goal_json
from __future__ import print_function, unicode_literals

import json
from decimal import Decimal

from gittip.testing import Harness
from gittip.models.participant import Participant


class Tests(Harness):

    def make_alice(self):
        return self.make_participant('alice', claimed_time='now')

    def change_goal(self, goal, goal_custom="", username="alice", expecting_error=False):
        if isinstance(username, Participant):
            username = username.username
        elif username == 'alice':
            self.make_alice()

        method = self.client.POST if not expecting_error else self.client.PxST
        response = method( "/alice/goal.json"
                         , {'goal': goal, 'goal_custom': goal_custom}
                         , auth_as=username
                          )
        return response


    def test_participant_can_set_their_goal_to_null(self):
        response = self.change_goal("null")
        actual = json.loads(response.body)['goal']
        assert actual == None

    def test_participant_can_set_their_goal_to_zero(self):
        response = self.change_goal("0")
        actual = json.loads(response.body)['goal']
        assert actual == "0.00"

    def test_participant_can_set_their_goal_to_a_custom_amount(self):
        response = self.change_goal("custom", "100.00")
        actual = json.loads(response.body)['goal']
        assert actual == "100.00"

    def test_custom_amounts_can_include_comma(self):
        response = self.change_goal("custom", "1,100.00")
        actual = json.loads(response.body)['goal']
        assert actual == "1,100.00"

    def test_wonky_custom_amounts_are_standardized(self):
        response = self.change_goal("custom", ",100,100.00000")
        actual = json.loads(response.body)['goal']
        assert actual == "100,100.00"

    def test_anonymous_gets_404(self):
        response = self.change_goal("100.00", username=None, expecting_error=True)
        assert response.code == 404, response.code

    def test_invalid_is_400(self):
        response = self.change_goal("cheese", expecting_error=True)
        assert response.code == 400, response.code

    def test_invalid_custom_amount_is_400(self):
        response = self.change_goal("custom", "cheese", expecting_error=True)
        assert response.code == 400, response.code


    # Exercise the event logging for goal changes.

    def test_last_goal_is_stored_in_participants_table(self):
        alice = self.make_alice()
        self.change_goal("custom", "100", alice)
        self.change_goal("custom", "200", alice)
        self.change_goal("custom", "300", alice)
        self.change_goal("null", "", alice)
        self.change_goal("custom", "400", alice)
        actual = self.db.one("SELECT goal FROM participants")
        assert actual == Decimal("400.00")

    def test_all_goals_are_stored_in_events_table(self):
        alice = self.make_alice()
        self.change_goal("custom", "100", alice)
        self.change_goal("custom", "200", alice)
        self.change_goal("custom", "300", alice)
        self.change_goal("null", "", alice)
        self.change_goal("custom", "400", alice)
        actual = self.db.all("SELECT (payload->'values'->>'goal')::int AS goal "
                             "FROM events ORDER BY ts DESC")
        assert actual == [400, None, 300, 200, 100, None]

########NEW FILE########
__FILENAME__ = test_hooks
from __future__ import absolute_import, division, print_function, unicode_literals

from gittip import wireup
from gittip.testing import Harness
from gittip.models.participant import Participant
from environment import Environment


class Tests(Harness):

    def setUp(self):
        Harness.setUp(self)

        # Grab configuration from the environment, storing for later.
        env = wireup.env()
        self.environ = env.environ

        # Change env, doesn't change self.environ.
        env.canonical_scheme = 'https'
        env.canonical_host = 'www.gittip.com'

        wireup.canonical(env)

    def tearDown(self):
        Harness.tearDown(self)
        reset = Environment(CANONICAL_SCHEME=unicode, CANONICAL_HOST=unicode, environ=self.environ)
        wireup.canonical(reset)


    def test_canonize_canonizes(self):
        response = self.client.GxT( "/"
                                  , HTTP_HOST='www.gittip.com'
                                  , HTTP_X_FORWARDED_PROTO='http'
                                   )
        assert response.code == 302
        assert response.headers['Location'] == 'https://www.gittip.com/'


    def test_session_cookie_set_in_auth_response(self):
        self.make_participant('alice')

        # Make a normal authenticated request.
        normal = self.client.GET( "/"
                                , auth_as='alice'
                                , HTTP_X_FORWARDED_PROTO='https'
                                , HTTP_HOST='www.gittip.com'
                                 )
        alice = Participant.from_username('alice')
        assert normal.headers.cookie['session'].value == alice.session_token


    def test_session_cookie_isnt_overwritten_by_canonizer(self):
        # https://github.com/gittip/www.gittip.com/issues/940

        self.make_participant('alice')

        # Make a request that canonizer will redirect.
        redirect = self.client.GET( "/"
                                  , auth_as='alice'
                                  , HTTP_X_FORWARDED_PROTO='http'
                                  , HTTP_HOST='www.gittip.com'
                                  , raise_immediately=False
                                   )
        assert redirect.code == 302
        assert 'session' not in redirect.headers.cookie

        # This is bad, because it means that the user will be signed out of
        # https://www.gittip.com/ if they make a request for
        # http://www.gittip.com/.


    def test_session_cookie_is_secure_if_it_should_be(self):
        # https://github.com/gittip/www.gittip.com/issues/940
        response = self.client.GET( "/"
                                  , auth_as=self.make_participant('alice').username
                                  , HTTP_X_FORWARDED_PROTO='https'
                                  , HTTP_HOST='www.gittip.com'
                                   )
        assert response.code == 200
        assert '; secure' in response.headers.cookie['session'].output()

########NEW FILE########
__FILENAME__ = test_is_suspicious
from __future__ import print_function, unicode_literals

from gittip.testing import Harness
from gittip.models.participant import Participant


class TestIsSuspicious(Harness):
    def setUp(self):
        Harness.setUp(self)
        self.bar = self.make_participant('bar', is_admin=True)

    def toggle_is_suspicious(self):
        self.client.GET('/foo/toggle-is-suspicious.json', auth_as='bar')

    def test_that_is_suspicious_defaults_to_None(self):
        foo = self.make_participant('foo', claimed_time='now')
        actual = foo.is_suspicious
        assert actual == None

    def test_toggling_NULL_gives_true(self):
        self.make_participant('foo', claimed_time='now')
        self.toggle_is_suspicious()
        actual = Participant.from_username('foo').is_suspicious
        assert actual == True

    def test_toggling_true_gives_false(self):
        self.make_participant('foo', is_suspicious=True, claimed_time='now')
        self.toggle_is_suspicious()
        actual = Participant.from_username('foo').is_suspicious
        assert actual == False

    def test_toggling_false_gives_true(self):
        self.make_participant('foo', is_suspicious=False, claimed_time='now')
        self.toggle_is_suspicious()
        actual = Participant.from_username('foo').is_suspicious
        assert actual == True

    def test_toggling_adds_event(self):
        foo = self.make_participant('foo', is_suspicious=False, claimed_time='now')
        self.toggle_is_suspicious()

        actual = self.db.one("""\
                SELECT type, payload
                FROM events
                WHERE CAST(payload->>'id' AS INTEGER) = %s
                  AND (payload->'values'->'is_suspicious')::text != 'null'
                ORDER BY ts DESC""",
                (foo.id,))
        assert actual == ('participant', dict(id=foo.id,
            recorder=dict(id=self.bar.id, username=self.bar.username), action='set',
            values=dict(is_suspicious=True)))

########NEW FILE########
__FILENAME__ = test_lookup_json
from __future__ import unicode_literals

import json

from aspen.utils import utcnow
from gittip.testing import Harness

class TestLookupJson(Harness):

    def test_get_without_query_querystring_returns_400(self):
        response = self.client.GET('/lookup.json')
        assert response.code == 400

    def test_get_non_existent_user(self):
        response = self.client.GET('/lookup.json?query={}'.format('alice'))
        data = json.loads(response.body)

        assert len(data) == 1
        assert data[0]['id'] == -1

    def test_get_existing_user(self):
        self.make_participant("alice", claimed_time=utcnow())

        response = self.client.GET('/lookup.json?query={}'.format('alice'))
        data = json.loads(response.body)

        assert len(data) == 1
        assert data[0]['id'] != -1

########NEW FILE########
__FILENAME__ = test_membername_json
from __future__ import unicode_literals

import pytest
from aspen import json
from aspen.utils import utcnow
from gittip.testing import Harness

class TestMembernameJson(Harness):

    def setUp(self):
        Harness.setUp(self)
        self.make_participant("team", claimed_time=utcnow(), number='plural')
        self.make_participant("alice", claimed_time=utcnow())

    def test_post_team_is_not_team_returns_404(self):
        response = self.client.PxST('/alice/members/team.json', auth_as='alice')
        assert response.code == 404

    def test_post_participant_doesnt_exist_returns_404(self):
        response = self.client.PxST('/team/members/bob.json', auth_as='team')
        assert response.code == 404

    def test_post_user_is_not_member_or_team_returns_403(self):
        self.make_participant("bob", claimed_time=utcnow(), number='plural')
        response = self.client.POST('/team/members/alice.json', {'take': '0.01'}, auth_as='team')
        assert response.code == 200

        response = self.client.POST('/team/members/bob.json', {'take': '0.01'}, auth_as='team')
        assert response.code == 200

        response = self.client.PxST('/team/members/alice.json', auth_as='bob')
        assert response.code == 403

    def test_post_take_is_not_decimal_returns_400(self):
        response = self.client.PxST('/team/members/alice.json', {'take': 'bad'}, auth_as='team')
        assert response.code == 400

    def test_post_member_equals_team_returns_400(self):
        response = self.client.PxST('/team/members/team.json', {'take': '0.01'}, auth_as='team')
        assert response.code == 400

    def test_post_take_is_not_zero_or_penny_returns_400(self):
        response = self.client.PxST('/team/members/alice.json', {'take': '0.02'}, auth_as='team')
        assert response.code == 400

    def test_post_zero_take_on_non_member_raises_Exception(self):
        pytest.raises( Exception
                     , self.client.PxST
                     , '/team/members/alice.json'
                     , {'take': '0.00'}
                     , auth_as='team'
                      )

    def test_post_can_add_member_to_team(self):
        response = self.client.POST('/team/members/alice.json', {'take': '0.01'}, auth_as='team')
        data = json.loads(response.body)
        assert len(data) == 2

        for rec in data:
            assert rec['username'] in ('team', 'alice'), rec['username']

    def test_post_can_remove_member_from_team(self):
        response = self.client.POST('/team/members/alice.json', {'take': '0.01'}, auth_as='team')

        data = json.loads(response.body)
        assert len(data) == 2

        for rec in data:
            assert rec['username'] in ('team', 'alice'), rec['username']

        response = self.client.POST('/team/members/alice.json', {'take': '0.00'}, auth_as='team')

        data = json.loads(response.body)
        assert len(data) == 1
        assert data[0]['username'] == 'team'

    def test_post_non_team_member_adds_member_returns_403(self):
        self.make_participant("bob", claimed_time=utcnow())

        response = self.client.POST('/team/members/alice.json', {'take': '0.01'}, auth_as='team')
        assert response.code == 200

        response = self.client.PxST('/team/members/bob.json', {'take': '0.01'}, auth_as='alice')
        assert response.code == 403

    def test_get_team_when_team_equals_member(self):
        response = self.client.GET('/team/members/team.json', auth_as='team')
        data = json.loads(response.body)
        assert response.code == 200
        assert data['username'] == 'team'
        assert data['take'] == '0.00'

    def test_get_team_member_returns_null_when_non_member(self):
        response = self.client.GET('/team/members/alice.json', auth_as='team')
        assert response.code == 200
        assert response.body == 'null'

    def test_get_team_members_returns_take_when_member(self):
        response = self.client.POST('/team/members/alice.json', {'take': '0.01'}, auth_as='team')
        assert response.code == 200

        response = self.client.GET('/team/members/alice.json', auth_as='team')
        data = json.loads(response.body)

        assert response.code == 200
        assert data['username'] == 'alice'
        assert data['take'] == '0.01'

########NEW FILE########
__FILENAME__ = test_pages
from __future__ import print_function, unicode_literals

from gittip.testing import Harness
from gittip.utils import update_homepage_queries_once


class TestPages(Harness):

    def test_homepage(self):
        actual = self.client.GET('/').body
        expected = "Sustainable Crowdfunding"
        assert expected in actual

    def test_homepage_with_anonymous_giver(self):
        self.make_participant('bob', elsewhere='twitter', claimed_time='now')
        alice = self.make_participant('alice', anonymous_giving=True, last_bill_result='',
                                      elsewhere='twitter', claimed_time='now')
        alice.set_tip_to('bob', 1)
        update_homepage_queries_once(self.db)

        actual = self.client.GET('/').body
        expected = "Anonymous"
        assert expected in actual

    def test_homepage_with_anonymous_receiver(self):
        self.make_participant('bob', anonymous_receiving=True, last_bill_result='',
                              elsewhere='twitter', claimed_time='now')
        alice = self.make_participant('alice', last_bill_result='', claimed_time='now')
        alice.set_tip_to('bob', 1)
        update_homepage_queries_once(self.db)

        actual = self.client.GET('/').body
        expected = "Anonymous"
        assert expected in actual

    def test_profile(self):
        self.make_participant('cheese', claimed_time='now')
        expected = "I'm grateful for gifts"
        actual = self.client.GET('/cheese/').body.decode('utf8') # deal with cent sign
        assert expected in actual

    def test_widget(self):
        self.make_participant('cheese', claimed_time='now')
        expected = "javascript: window.open"
        actual = self.client.GET('/cheese/widget.html').body
        assert expected in actual

    def test_bank_account(self):
        expected = "add<br> or change your bank account"
        actual = self.client.GET('/bank-account.html').body
        assert expected in actual

    def test_credit_card(self):
        expected = "add<br> or change your credit card"
        actual = self.client.GET('/credit-card.html').body
        assert expected in actual

    def test_github_associate(self):
        assert self.client.GxT('/on/github/associate').code == 400

    def test_twitter_associate(self):
        assert self.client.GxT('/on/twitter/associate').code == 400

    def test_about(self):
        expected = "small weekly cash gifts"
        actual = self.client.GET('/about/').body
        assert expected in actual

    def test_about_stats(self):
        expected = "have joined Gittip"
        actual = self.client.GET('/about/stats.html').body
        assert expected in actual

    def test_about_charts(self):
        expected = "Money transferred"
        actual = self.client.GET('/about/charts.html').body
        assert expected in actual

    def test_404(self):
        response = self.client.GET('/about/four-oh-four.html', raise_immediately=False)
        assert "Page Not Found" in response.body
        assert "{%" not in response.body

    def test_bank_account_complete(self):
        assert self.client.GxT('/bank-account-complete.html').code == 404

    def test_for_contributors_redirects_to_building_gittip(self):
        assert self.client.GxT('/for/contributors/').headers['Location'] == \
                                                                      'http://building.gittip.com/'

    def test_mission_statement_also_redirects(self):
        assert self.client.GxT('/for/contributors/mission-statement.html').code == 302

    def test_bank_account_json(self):
        assert self.client.GxT('/bank-account.json').code == 404

    def test_credit_card_json(self):
        assert self.client.GxT('/credit-card.json').code == 404

    def test_anonymous_sign_out_redirects(self):
        response = self.client.PxST('/sign-out.html')
        assert response.code == 302
        assert response.headers['Location'] == '/'

    def test_receipts_signed_in(self):
        self.make_participant('alice', claimed_time='now')
        self.db.run("INSERT INTO exchanges (id, participant, amount, fee) "
                    "VALUES(100,'alice',1,0.1)")
        request = self.client.GET("/alice/receipts/100.html", auth_as="alice")
        assert request.code == 200

########NEW FILE########
__FILENAME__ = test_participant
from __future__ import print_function, unicode_literals

import datetime
import random
from decimal import Decimal

import pytz
import pytest
from aspen.utils import utcnow
from gittip import NotSane
from gittip.exceptions import (
    HasBigTips,
    UsernameIsEmpty,
    UsernameTooLong,
    UsernameAlreadyTaken,
    UsernameContainsInvalidCharacters,
    UsernameIsRestricted,
    NoSelfTipping,
    NoTippee,
    BadAmount,
)
from gittip.models.participant import (
    LastElsewhere, NeedConfirmation, NonexistingElsewhere, Participant
)
from gittip.testing import Harness


# TODO: Test that accounts elsewhere are not considered claimed by default


class TestNeedConfirmation(Harness):
    def test_need_confirmation1(self):
        assert not NeedConfirmation(False, False, False)

    def test_need_confirmation2(self):
        assert NeedConfirmation(False, False, True)

    def test_need_confirmation3(self):
        assert not NeedConfirmation(False, True, False)

    def test_need_confirmation4(self):
        assert NeedConfirmation(False, True, True)

    def test_need_confirmation5(self):
        assert NeedConfirmation(True, False, False)

    def test_need_confirmation6(self):
        assert NeedConfirmation(True, False, True)

    def test_need_confirmation7(self):
        assert NeedConfirmation(True, True, False)

    def test_need_confirmation8(self):
        assert NeedConfirmation(True, True, True)


class TestAbsorptions(Harness):
    # TODO: These tests should probably be moved to absorptions tests
    def setUp(self):
        Harness.setUp(self)
        now = utcnow()
        hour_ago = now - datetime.timedelta(hours=1)
        for username in ['alice', 'bob', 'carl']:
            self.make_participant( username
                                 , claimed_time=hour_ago
                                 , last_bill_result=''
                                  )
        deadbeef = self.make_elsewhere('twitter', '1', 'deadbeef')
        self.deadbeef_original_username = deadbeef.participant.username

        Participant.from_username('carl').set_tip_to('bob', '1.00')
        Participant.from_username('alice').set_tip_to(self.deadbeef_original_username, '1.00')
        Participant.from_username('bob').take_over(deadbeef, have_confirmation=True)

    def test_participant_can_be_instantiated(self):
        expected = Participant
        actual = Participant.from_username('alice').__class__
        assert actual is expected

    def test_bob_has_two_dollars_in_tips(self):
        expected = Decimal('2.00')
        actual = Participant.from_username('bob').get_dollars_receiving()
        assert actual == expected

    def test_alice_gives_to_bob_now(self):
        expected = Decimal('1.00')
        actual = Participant.from_username('alice').get_tip_to('bob')
        assert actual == expected

    def test_deadbeef_is_archived(self):
        actual = self.db.one( "SELECT count(*) FROM absorptions "
                              "WHERE absorbed_by='bob' AND absorbed_was=%s"
                            , (self.deadbeef_original_username,)
                             )
        expected = 1
        assert actual == expected

    def test_alice_doesnt_gives_to_deadbeef_anymore(self):
        expected = Decimal('0.00')
        actual = Participant.from_username('alice').get_tip_to(self.deadbeef_original_username)
        assert actual == expected

    def test_alice_doesnt_give_to_whatever_deadbeef_was_archived_as_either(self):
        expected = Decimal('0.00')
        alice = Participant.from_username('alice')
        actual = alice.get_tip_to(self.deadbeef_original_username)
        assert actual == expected

    def test_there_is_no_more_deadbeef(self):
        actual = Participant.from_username('deadbeef')
        assert actual is None


class TestTakeOver(Harness):

    def test_cross_tip_doesnt_become_self_tip(self):
        alice = self.make_elsewhere('twitter', 1, 'alice')
        bob   = self.make_elsewhere('twitter', 2, 'bob')
        alice_participant = alice.opt_in('alice')[0].participant
        bob_participant = bob.opt_in('bob')[0].participant
        alice_participant.set_tip_to('bob', '1.00')
        bob_participant.take_over(alice, have_confirmation=True)
        self.db.self_check()

    def test_zero_cross_tip_doesnt_become_self_tip(self):
        alice = self.make_elsewhere('twitter', 1, 'alice')
        bob   = self.make_elsewhere('twitter', 2, 'bob')
        alice_participant = alice.opt_in('alice')[0].participant
        bob_participant = bob.opt_in('bob')[0].participant
        alice_participant.set_tip_to('bob', '1.00')
        alice_participant.set_tip_to('bob', '0.00')
        bob_participant.take_over(alice, have_confirmation=True)
        self.db.self_check()

    def test_do_not_take_over_zero_tips_giving(self):
        alice = self.make_elsewhere('twitter', 1, 'alice')
        self.make_elsewhere('twitter', 2, 'bob').opt_in('bob')
        carl  = self.make_elsewhere('twitter', 3, 'carl')
        alice_participant = alice.opt_in('alice')[0].participant
        carl_participant = carl.opt_in('carl')[0].participant
        carl_participant.set_tip_to('bob', '1.00')
        carl_participant.set_tip_to('bob', '0.00')
        alice_participant.take_over(carl, have_confirmation=True)
        ntips = self.db.one("select count(*) from tips")
        assert 2 == ntips
        self.db.self_check()

    def test_do_not_take_over_zero_tips_receiving(self):
        alice = self.make_elsewhere('twitter', 1, 'alice')
        bob   = self.make_elsewhere('twitter', 2, 'bob')
        carl  = self.make_elsewhere('twitter', 3, 'carl')
        alice_participant = alice.opt_in('alice')[0].participant
        bob_participant   = bob.opt_in('bob')[0].participant
        carl.opt_in('carl')
        bob_participant.set_tip_to('carl', '1.00')
        bob_participant.set_tip_to('carl', '0.00')
        alice_participant.take_over(carl, have_confirmation=True)
        ntips = self.db.one("select count(*) from tips")
        assert 2 == ntips
        self.db.self_check()

    def test_idempotent(self):
        alice = self.make_elsewhere('twitter', 1, 'alice')
        bob   = self.make_elsewhere('github', 2, 'bob')
        alice_participant = alice.opt_in('alice')[0].participant
        alice_participant.take_over(bob, have_confirmation=True)
        alice_participant.take_over(bob, have_confirmation=True)
        self.db.self_check()


class TestParticipant(Harness):
    def setUp(self):
        Harness.setUp(self)
        now = utcnow()
        for username in ['alice', 'bob', 'carl']:
            self.make_participant(username, claimed_time=now, elsewhere='twitter')

    def test_bob_is_singular(self):
        expected = True
        actual = Participant.from_username('bob').IS_SINGULAR
        assert actual == expected

    def test_john_is_plural(self):
        expected = True
        self.make_participant('john', number='plural')
        actual = Participant.from_username('john').IS_PLURAL
        assert actual == expected

    def test_can_change_email(self):
        Participant.from_username('alice').update_email('alice@gittip.com')
        expected = 'alice@gittip.com'
        actual = Participant.from_username('alice').email.address
        assert actual == expected

    def test_can_confirm_email(self):
        Participant.from_username('alice').update_email('alice@gittip.com', True)
        actual = Participant.from_username('alice').email.confirmed
        assert actual == True

    def test_cant_take_over_claimed_participant_without_confirmation(self):
        bob_twitter = self.make_elsewhere('twitter', '2', 'bob')
        with self.assertRaises(NeedConfirmation):
            Participant.from_username('alice').take_over(bob_twitter)

    def test_taking_over_yourself_sets_all_to_zero(self):
        bob_twitter = self.make_elsewhere('twitter', '2', 'bob')
        Participant.from_username('alice').set_tip_to('bob', '1.00')
        Participant.from_username('alice').take_over(bob_twitter, have_confirmation=True)
        expected = Decimal('0.00')
        actual = Participant.from_username('alice').get_dollars_giving()
        assert actual == expected

    def test_alice_ends_up_tipping_bob_two_dollars(self):
        carl_twitter = self.make_elsewhere('twitter', '3', 'carl')
        Participant.from_username('alice').set_tip_to('bob', '1.00')
        Participant.from_username('alice').set_tip_to('carl', '1.00')
        Participant.from_username('bob').take_over(carl_twitter, have_confirmation=True)
        expected = Decimal('2.00')
        actual = Participant.from_username('alice').get_tip_to('bob')
        assert actual == expected

    def test_bob_ends_up_tipping_alice_two_dollars(self):
        carl_twitter = self.make_elsewhere('twitter', '3', 'carl')
        Participant.from_username('bob').set_tip_to('alice', '1.00')
        Participant.from_username('carl').set_tip_to('alice', '1.00')
        Participant.from_username('bob').take_over(carl_twitter, have_confirmation=True)
        expected = Decimal('2.00')
        actual = Participant.from_username('bob').get_tip_to('alice')
        assert actual == expected

    def test_ctime_comes_from_the_older_tip(self):
        carl_twitter = self.make_elsewhere('twitter', '3', 'carl')
        Participant.from_username('alice').set_tip_to('bob', '1.00')
        Participant.from_username('alice').set_tip_to('carl', '1.00')
        Participant.from_username('bob').take_over(carl_twitter, have_confirmation=True)

        tips = self.db.all("SELECT * FROM tips")
        first, second = tips[0], tips[1]

        # sanity checks (these don't count :)
        assert len(tips) == 4
        assert first.tipper, first.tippee == ('alice', 'bob')
        assert second.tipper, second.tippee == ('alice', 'carl')

        expected = first.ctime
        actual = self.db.one("SELECT ctime FROM tips ORDER BY ctime LIMIT 1")
        assert actual == expected

    def test_connecting_unknown_account_fails(self):
        with self.assertRaises(NotSane):
            Participant.from_username('bob').take_over(('github', 'jim'))

    def test_delete_elsewhere_last(self):
        alice = Participant.from_username('alice')
        with pytest.raises(LastElsewhere):
            alice.delete_elsewhere('twitter', 1)

    def test_delete_elsewhere_last_signin(self):
        alice = Participant.from_username('alice')
        self.make_elsewhere('bountysource', alice.id, 'alice')
        with pytest.raises(LastElsewhere):
            alice.delete_elsewhere('twitter', 1)

    def test_delete_elsewhere_nonsignin(self):
        g = self.make_elsewhere('bountysource', 1, 'alice')
        alice = Participant.from_username('alice')
        alice.take_over(g)
        accounts = alice.get_accounts_elsewhere()
        assert accounts['twitter'] and accounts['bountysource']
        alice.delete_elsewhere('bountysource', 1)
        accounts = alice.get_accounts_elsewhere()
        assert accounts['twitter'] and accounts.get('bountysource') is None

    def test_delete_elsewhere_nonexisting(self):
        alice = Participant.from_username('alice')
        with pytest.raises(NonexistingElsewhere):
            alice.delete_elsewhere('github', 1)

    def test_delete_elsewhere(self):
        g = self.make_elsewhere('github', 1, 'alice')
        alice = Participant.from_username('alice')
        alice.take_over(g)
        # test preconditions
        accounts = alice.get_accounts_elsewhere()
        assert accounts['twitter'] and accounts['github']
        # do the thing
        alice.delete_elsewhere('twitter', 1)
        # unit test
        accounts = alice.get_accounts_elsewhere()
        assert accounts.get('twitter') is None and accounts['github']




class Tests(Harness):

    def random_restricted_username(self):
        """helper method to chooses a restricted username for testing """
        from gittip import RESTRICTED_USERNAMES
        random_item = random.choice(RESTRICTED_USERNAMES)
        while random_item.startswith('%'):
            random_item = random.choice(RESTRICTED_USERNAMES)
        return random_item

    def setUp(self):
        Harness.setUp(self)
        self.participant = self.make_participant('user1')  # Our protagonist


    def test_claiming_participant(self):
        now = datetime.datetime.now(pytz.utc)
        self.participant.set_as_claimed()
        actual = self.participant.claimed_time - now
        expected = datetime.timedelta(seconds=0.1)
        assert actual < expected

    def test_changing_username_successfully(self):
        self.participant.change_username('user2')
        actual = Participant.from_username('user2')
        assert self.participant == actual

    def test_changing_username_to_nothing(self):
        with self.assertRaises(UsernameIsEmpty):
            self.participant.change_username('')

    def test_changing_username_to_all_spaces(self):
        with self.assertRaises(UsernameIsEmpty):
            self.participant.change_username('    ')

    def test_changing_username_strips_spaces(self):
        self.participant.change_username('  aaa  ')
        actual = Participant.from_username('aaa')
        assert self.participant == actual

    def test_changing_username_returns_the_new_username(self):
        returned = self.participant.change_username('  foo bar baz  ')
        assert returned == 'foo bar baz', returned

    def test_changing_username_to_too_long(self):
        with self.assertRaises(UsernameTooLong):
            self.participant.change_username('123456789012345678901234567890123')

    def test_changing_username_to_already_taken(self):
        self.make_participant('user2')
        with self.assertRaises(UsernameAlreadyTaken):
            self.participant.change_username('user2')

    def test_changing_username_to_already_taken_is_case_insensitive(self):
        self.make_participant('UsEr2')
        with self.assertRaises(UsernameAlreadyTaken):
            self.participant.change_username('uSeR2')

    def test_changing_username_to_invalid_characters(self):
        with self.assertRaises(UsernameContainsInvalidCharacters):
            self.participant.change_username(u"\u2603") # Snowman

    def test_changing_username_to_restricted_name(self):
        with self.assertRaises(UsernameIsRestricted):
            self.participant.change_username(self.random_restricted_username())

    def test_getting_tips_actually_made(self):
        expected = Decimal('1.00')
        self.make_participant('user2')
        self.participant.set_tip_to('user2', expected)
        actual = self.participant.get_tip_to('user2')
        assert actual == expected

    def test_getting_tips_not_made(self):
        expected = Decimal('0.00')
        self.make_participant('user2')
        actual = self.participant.get_tip_to('user2')
        assert actual == expected


    # id

    def test_participant_gets_a_long_id(self):
        actual = type(self.make_participant('alice').id)
        assert actual == long


    # number

    def test_cant_go_singular_with_big_tips(self):
        alice = self.make_participant('alice', last_bill_result='')
        bob = self.make_participant('bob', number='plural')
        carl = self.make_participant('carl')
        carl.set_tip_to('bob', '100.00')
        alice.set_tip_to('bob', '1000.00')
        pytest.raises(HasBigTips, bob.update_number, 'singular')

    def test_can_go_singular_without_big_tips(self):
        alice = self.make_participant('alice', last_bill_result='')
        bob = self.make_participant('bob', number='plural')
        alice.set_tip_to('bob', '100.00')
        bob.update_number('singular')
        assert Participant.from_username('bob').number == 'singular'

    def test_can_go_plural(self):
        alice = self.make_participant('alice', last_bill_result='')
        bob = self.make_participant('bob')
        alice.set_tip_to('bob', '100.00')
        bob.update_number('plural')
        assert Participant.from_username('bob').number == 'plural'


    # set_tip_to - stt

    def test_stt_sets_tip_to(self):
        alice = self.make_participant('alice', last_bill_result='')
        self.make_participant('bob')
        alice.set_tip_to('bob', '1.00')

        actual = alice.get_tip_to('bob')
        assert actual == Decimal('1.00')

    def test_stt_returns_a_Decimal_and_a_boolean(self):
        alice = self.make_participant('alice', last_bill_result='')
        self.make_participant('bob')
        actual = alice.set_tip_to('bob', '1.00')
        assert actual == (Decimal('1.00'), True)

    def test_stt_returns_False_for_second_time_tipper(self):
        alice = self.make_participant('alice', last_bill_result='')
        self.make_participant('bob')
        alice.set_tip_to('bob', '1.00')
        actual = alice.set_tip_to('bob', '2.00')
        assert actual == (Decimal('2.00'), False)

    def test_stt_doesnt_allow_self_tipping(self):
        alice = self.make_participant('alice', last_bill_result='')
        self.assertRaises(NoSelfTipping, alice.set_tip_to, 'alice', '10.00')

    def test_stt_doesnt_allow_just_any_ole_amount(self):
        alice = self.make_participant('alice', last_bill_result='')
        self.make_participant('bob')
        self.assertRaises(BadAmount, alice.set_tip_to, 'bob', '1000.00')

    def test_stt_allows_higher_tip_to_plural_receiver(self):
        alice = self.make_participant('alice', last_bill_result='')
        self.make_participant('bob', number='plural')
        actual = alice.set_tip_to('bob', '1000.00')
        assert actual == (Decimal('1000.00'), True)

    def test_stt_still_caps_tips_to_plural_receivers(self):
        alice = self.make_participant('alice', last_bill_result='')
        self.make_participant('bob', number='plural')
        self.assertRaises(BadAmount, alice.set_tip_to, 'bob', '1000.01')

    def test_stt_fails_to_tip_unknown_people(self):
        alice = self.make_participant('alice', last_bill_result='')
        self.assertRaises(NoTippee, alice.set_tip_to, 'bob', '1.00')


    # get_dollars_receiving - gdr

    def test_gdr_only_sees_latest_tip(self):
        alice = self.make_participant('alice', last_bill_result='')
        bob = self.make_participant('bob')
        alice.set_tip_to('bob', '12.00')
        alice.set_tip_to('bob', '3.00')

        expected = Decimal('3.00')
        actual = bob.get_dollars_receiving()
        assert actual == expected


    def test_gdr_includes_tips_from_accounts_with_a_working_card(self):
        alice = self.make_participant('alice', last_bill_result='')
        bob = self.make_participant('bob')
        alice.set_tip_to('bob', '3.00')

        expected = Decimal('3.00')
        actual = bob.get_dollars_receiving()
        assert actual == expected

    def test_gdr_ignores_tips_from_accounts_with_no_card_on_file(self):
        alice = self.make_participant('alice', last_bill_result=None)
        bob = self.make_participant('bob')
        alice.set_tip_to('bob', '3.00')

        expected = Decimal('0.00')
        actual = bob.get_dollars_receiving()
        assert actual == expected

    def test_gdr_ignores_tips_from_accounts_with_a_failing_card_on_file(self):
        alice = self.make_participant('alice', last_bill_result="Fail!")
        bob = self.make_participant('bob')
        alice.set_tip_to('bob', '3.00')

        expected = Decimal('0.00')
        actual = bob.get_dollars_receiving()
        assert actual == expected


    def test_gdr_includes_tips_from_whitelisted_accounts(self):
        alice = self.make_participant( 'alice'
                                     , last_bill_result=''
                                     , is_suspicious=False
                                      )
        bob = self.make_participant('bob')
        alice.set_tip_to('bob', '3.00')

        expected = Decimal('3.00')
        actual = bob.get_dollars_receiving()
        assert actual == expected

    def test_gdr_includes_tips_from_unreviewed_accounts(self):
        alice = self.make_participant( 'alice'
                                     , last_bill_result=''
                                     , is_suspicious=None
                                      )
        bob = self.make_participant('bob')
        alice.set_tip_to('bob', '3.00')

        expected = Decimal('3.00')
        actual = bob.get_dollars_receiving()
        assert actual == expected

    def test_gdr_ignores_tips_from_blacklisted_accounts(self):
        alice = self.make_participant( 'alice'
                                     , last_bill_result=''
                                     , is_suspicious=True
                                      )
        bob = self.make_participant('bob')
        alice.set_tip_to('bob', '3.00')

        expected = Decimal('0.00')
        actual = bob.get_dollars_receiving()
        assert actual == expected


    # get_number_of_backers - gnob

    def test_gnob_gets_number_of_backers(self):
        alice = self.make_participant('alice', last_bill_result='')
        bob = self.make_participant('bob', last_bill_result='')
        clancy = self.make_participant('clancy')

        alice.set_tip_to('clancy', '3.00')
        bob.set_tip_to('clancy', '1.00')

        actual = clancy.get_number_of_backers()
        assert actual == 2


    def test_gnob_includes_backers_with_a_working_card_on_file(self):
        alice = self.make_participant('alice', last_bill_result='')
        bob = self.make_participant('bob')
        alice.set_tip_to('bob', '3.00')

        actual = bob.get_number_of_backers()
        assert actual == 1

    def test_gnob_ignores_backers_with_no_card_on_file(self):
        alice = self.make_participant('alice', last_bill_result=None)
        bob = self.make_participant('bob')
        alice.set_tip_to('bob', '3.00')

        actual = bob.get_number_of_backers()
        assert actual == 0

    def test_gnob_ignores_backers_with_a_failing_card_on_file(self):
        alice = self.make_participant('alice', last_bill_result="Fail!")
        bob = self.make_participant('bob')
        alice.set_tip_to('bob', '3.00')

        actual = bob.get_number_of_backers()
        assert actual == 0


    def test_gnob_includes_whitelisted_backers(self):
        alice = self.make_participant( 'alice'
                                     , last_bill_result=''
                                     , is_suspicious=False
                                      )
        bob = self.make_participant('bob')
        alice.set_tip_to('bob', '3.00')

        actual = bob.get_number_of_backers()
        assert actual == 1

    def test_gnob_includes_unreviewed_backers(self):
        alice = self.make_participant( 'alice'
                                     , last_bill_result=''
                                     , is_suspicious=None
                                      )
        bob = self.make_participant('bob')
        alice.set_tip_to('bob', '3.00')

        actual = bob.get_number_of_backers()
        assert actual == 1

    def test_gnob_ignores_blacklisted_backers(self):
        alice = self.make_participant( 'alice'
                                     , last_bill_result=''
                                     , is_suspicious=True
                                      )
        bob = self.make_participant('bob')
        alice.set_tip_to('bob', '3.00')

        actual = bob.get_number_of_backers()
        assert actual == 0


    def test_gnob_ignores_backers_where_tip_is_zero(self):
        alice = self.make_participant('alice', last_bill_result='')
        bob = self.make_participant('bob')
        alice.set_tip_to('bob', '0.00')

        actual = bob.get_number_of_backers()
        assert actual == 0

    def test_gnob_looks_at_latest_tip_only(self):
        alice = self.make_participant('alice', last_bill_result='')
        bob = self.make_participant('bob')

        alice.set_tip_to('bob', '1.00')
        alice.set_tip_to('bob', '12.00')
        alice.set_tip_to('bob', '3.00')
        alice.set_tip_to('bob', '6.00')
        alice.set_tip_to('bob', '0.00')

        actual = bob.get_number_of_backers()
        assert actual == 0


    # get_age_in_seconds - gais

    def test_gais_gets_age_in_seconds(self):
        now = datetime.datetime.now(pytz.utc)
        alice = self.make_participant('alice', claimed_time=now)
        actual = alice.get_age_in_seconds()
        assert 0 < actual < 1

    def test_gais_returns_negative_one_if_None(self):
        alice = self.make_participant('alice', claimed_time=None)
        actual = alice.get_age_in_seconds()
        assert actual == -1


    # resolve_unclaimed - ru

    def test_ru_returns_None_for_orphaned_participant(self):
        resolved = self.make_participant('alice').resolve_unclaimed()
        assert resolved is None, resolved

    def test_ru_returns_bitbucket_url_for_stub_from_bitbucket(self):
        unclaimed = self.make_elsewhere('bitbucket', '1234', 'alice')
        stub = Participant.from_username(unclaimed.participant.username)
        actual = stub.resolve_unclaimed()
        assert actual == "/on/bitbucket/alice/"

    def test_ru_returns_github_url_for_stub_from_github(self):
        unclaimed = self.make_elsewhere('github', '1234', 'alice')
        stub = Participant.from_username(unclaimed.participant.username)
        actual = stub.resolve_unclaimed()
        assert actual == "/on/github/alice/"

    def test_ru_returns_twitter_url_for_stub_from_twitter(self):
        unclaimed = self.make_elsewhere('twitter', '1234', 'alice')
        stub = Participant.from_username(unclaimed.participant.username)
        actual = stub.resolve_unclaimed()
        assert actual == "/on/twitter/alice/"

    def test_ru_returns_openstreetmap_url_for_stub_from_openstreetmap(self):
        unclaimed = self.make_elsewhere('openstreetmap', '1', 'alice')
        stub = Participant.from_username(unclaimed.participant.username)
        actual = stub.resolve_unclaimed()
        assert actual == "/on/openstreetmap/alice/"


    # participant session

    def test_no_participant_from_expired_session(self):
        self.participant.start_new_session()
        token = self.participant.session_token

        # Session has expired long time ago
        self.participant.set_session_expires(0)
        actual = Participant.from_session_token(token)

        assert actual is None

########NEW FILE########
__FILENAME__ = test_public_json
from __future__ import print_function, unicode_literals

import json
import datetime

import pytz
from gittip.testing import Harness


class Tests(Harness):

    def make_participant(self, *a, **kw):
        kw['claimed_time'] = datetime.datetime.now(pytz.utc)
        return Harness.make_participant(self, *a, **kw)

    def test_on_key_gives_gittip(self):
        self.make_participant('alice', last_bill_result='')
        data = json.loads(self.client.GET('/alice/public.json').body)

        assert data['on'] == 'gittip'

    def test_anonymous_gets_receiving(self):
        alice = self.make_participant('alice', last_bill_result='')
        self.make_participant('bob')

        alice.set_tip_to('bob', '1.00')

        data = json.loads(self.client.GET('/bob/public.json').body)

        assert data['receiving'] == '1.00'

    def test_anonymous_does_not_get_my_tip(self):
        alice = self.make_participant('alice', last_bill_result='')
        self.make_participant('bob')

        alice.set_tip_to('bob', '1.00')

        data = json.loads(self.client.GET('/bob/public.json').body)

        assert data.has_key('my_tip') == False

    def test_anonymous_gets_giving(self):
        alice = self.make_participant('alice', last_bill_result='')
        self.make_participant('bob')

        alice.set_tip_to('bob', '1.00')

        data = json.loads(self.client.GET('/alice/public.json').body)

        assert data['giving'] == '1.00'

    def test_anonymous_gets_null_giving_if_user_anonymous(self):
        alice = self.make_participant( 'alice'
                                     , last_bill_result=''
                                     , anonymous_giving=True
                                     )
        self.make_participant('bob')
        alice.set_tip_to('bob', '1.00')
        data = json.loads(self.client.GET('/alice/public.json').body)

        assert data['giving'] == None

    def test_anonymous_gets_null_receiving_if_user_anonymous(self):
        alice = self.make_participant( 'alice'
                                     , last_bill_result=''
                                     , anonymous_receiving=True
                                     )
        self.make_participant('bob')
        alice.set_tip_to('bob', '1.00')
        data = json.loads(self.client.GET('/alice/public.json').body)

        assert data['receiving'] == None

    def test_anonymous_does_not_get_goal_if_user_regifts(self):
        self.make_participant('alice', last_bill_result='', goal=0)
        data = json.loads(self.client.GET('/alice/public.json').body)
        assert data.has_key('goal') == False

    def test_anonymous_gets_null_goal_if_user_has_no_goal(self):
        self.make_participant('alice', last_bill_result='')
        data = json.loads(self.client.GET('/alice/public.json').body)
        assert data['goal'] == None

    def test_anonymous_gets_user_goal_if_set(self):
        self.make_participant('alice', last_bill_result='', goal=1)
        data = json.loads(self.client.GET('/alice/public.json').body)
        assert data['goal'] == '1.00'

    def test_authenticated_user_gets_their_tip(self):
        alice = self.make_participant('alice', last_bill_result='')
        self.make_participant('bob')

        alice.set_tip_to('bob', '1.00')

        raw = self.client.GET('/bob/public.json', auth_as='alice').body

        data = json.loads(raw)

        assert data['receiving'] == '1.00'
        assert data['my_tip'] == '1.00'

    def test_authenticated_user_doesnt_get_other_peoples_tips(self):
        alice = self.make_participant('alice', last_bill_result='')
        bob = self.make_participant('bob', last_bill_result='')
        carl = self.make_participant('carl', last_bill_result='')
        self.make_participant('dana')

        alice.set_tip_to('dana', '1.00')
        bob.set_tip_to('dana', '3.00')
        carl.set_tip_to('dana', '12.00')

        raw = self.client.GET('/dana/public.json', auth_as='alice').body

        data = json.loads(raw)

        assert data['receiving'] == '16.00'
        assert data['my_tip'] == '1.00'

    def test_authenticated_user_gets_zero_if_they_dont_tip(self):
        self.make_participant('alice', last_bill_result='')
        bob = self.make_participant('bob', last_bill_result='')
        self.make_participant('carl')

        bob.set_tip_to('carl', '3.00')

        raw = self.client.GET('/carl/public.json', auth_as='alice').body

        data = json.loads(raw)

        assert data['receiving'] == '3.00'
        assert data['my_tip'] == '0.00'

    def test_authenticated_user_gets_self_for_self(self):
        alice = self.make_participant('alice', last_bill_result='')
        self.make_participant('bob')

        alice.set_tip_to('bob', '3.00')

        raw = self.client.GET('/bob/public.json', auth_as='bob').body

        data = json.loads(raw)

        assert data['receiving'] == '3.00'
        assert data['my_tip'] == 'self'

########NEW FILE########
__FILENAME__ = test_record_an_exchange
from __future__ import unicode_literals
from decimal import Decimal

from aspen.utils import utcnow
from gittip.testing import Harness


class TestRecordAnExchange(Harness):

    # fixture
    # =======

    def record_an_exchange(self, amount, fee, note, make_participants=True):
        if make_participants:
            now = utcnow()
            self.make_participant('alice', claimed_time=now, is_admin=True)
            self.make_participant('bob', claimed_time=now)
        return self.client.PxST( '/bob/history/record-an-exchange'
                               , {'amount': amount, 'fee': fee, 'note': note}
                               , auth_as='alice'
                                )

    # tests
    # =====

    def test_success_is_302(self):
        actual = self.record_an_exchange('10', '0', 'foo').code
        assert actual == 302

    def test_non_admin_is_404(self):
        self.make_participant('alice', claimed_time=utcnow())
        self.make_participant('bob', claimed_time=utcnow())
        actual = self.record_an_exchange('10', '0', 'foo', False).code
        assert actual == 404

    def test_non_post_is_405(self):
        self.make_participant('alice', claimed_time=utcnow(), is_admin=True)
        self.make_participant('bob', claimed_time=utcnow())
        actual = self.client.GxT( '/bob/history/record-an-exchange'
                                , auth_as='alice'
                                 ).code
        assert actual == 405

    def test_bad_amount_is_400(self):
        actual = self.record_an_exchange('cheese', '0', 'foo').code
        assert actual == 400

    def test_bad_fee_is_400(self):
        actual = self.record_an_exchange('10', 'cheese', 'foo').code
        assert actual == 400

    def test_no_note_is_400(self):
        actual = self.record_an_exchange('10', '0', '').code
        assert actual == 400

    def test_whitespace_note_is_400(self):
        actual = self.record_an_exchange('10', '0', '    ').code
        assert actual == 400

    def test_dropping_balance_below_zero_is_allowed_in_this_context(self):
        self.record_an_exchange('-10', '0', 'noted')
        actual = self.db.one("SELECT balance FROM participants WHERE username='bob'")
        assert actual == Decimal('-10.00')

    def test_success_records_exchange(self):
        self.record_an_exchange('10', '0.50', 'noted')
        expected = { "amount": Decimal('10.00')
                   , "fee": Decimal('0.50')
                   , "participant": "bob"
                   , "recorder": "alice"
                   , "note": "noted"
                    }
        SQL = "SELECT amount, fee, participant, recorder, note " \
              "FROM exchanges"
        actual = self.db.one(SQL, back_as=dict)
        assert actual == expected

    def test_success_updates_balance(self):
        self.record_an_exchange('10', '0', 'noted')
        expected = Decimal('10.00')
        SQL = "SELECT balance FROM participants WHERE username='bob'"
        actual = self.db.one(SQL)
        assert actual == expected

    def test_withdrawals_work(self):
        self.make_participant('alice', claimed_time=utcnow(), is_admin=True)
        self.make_participant('bob', claimed_time=utcnow(), balance=20)
        self.record_an_exchange('-7', '0', 'noted', False)
        expected = Decimal('13.00')
        SQL = "SELECT balance FROM participants WHERE username='bob'"
        actual = self.db.one(SQL)
        assert actual == expected

    def test_withdrawals_take_fee_out_of_balance(self):
        self.make_participant('alice', claimed_time=utcnow(), is_admin=True)
        self.make_participant('bob', claimed_time=utcnow(), balance=20)
        self.record_an_exchange('-7', '1.13', 'noted', False)
        SQL = "SELECT balance FROM participants WHERE username='bob'"
        assert self.db.one(SQL) == Decimal('11.87')

########NEW FILE########
__FILENAME__ = test_statement_json
from __future__ import print_function, unicode_literals

import json

from gittip.testing import Harness


class Tests(Harness):

    def change_statement(self, statement, number='singular', auth_as='alice',
            expecting_error=False):
        self.make_participant('alice')

        method = self.client.POST if not expecting_error else self.client.PxST
        response = method( "/alice/statement.json"
                         , {'statement': statement, 'number': number}
                         , auth_as=auth_as
                          )
        return response

    def test_participant_can_change_their_statement(self):
        response = self.change_statement('being awesome.')
        actual = json.loads(response.body)['statement']
        assert actual == 'being awesome.'

    def test_participant_can_change_their_number(self):
        response = self.change_statement('', 'plural')
        actual = json.loads(response.body)['number']
        assert actual == 'plural'

    def test_anonymous_gets_404(self):
        response = self.change_statement( 'being awesome.'
                                        , 'singular'
                                        , auth_as=None
                                        , expecting_error=True
                                         )
        assert response.code == 404, response.code

    def test_invalid_is_400(self):
        response = self.change_statement('', 'none', expecting_error=True)
        assert response.code == 400, response.code

########NEW FILE########
__FILENAME__ = test_stats
from __future__ import print_function, unicode_literals

import datetime
from decimal import Decimal
import json

from mock import patch

from gittip import wireup
from gittip.billing.payday import Payday
from gittip.models.participant import Participant
from gittip.testing import Harness


class TestCommaize(Harness):
    # XXX This really ought to be in helper methods test file
    def setUp(self):
        Harness.setUp(self)
        simplate = self.client.load_resource(b'/about/stats.html')
        self.commaize = simplate.pages[0]['commaize']

    def test_commaize_commaizes(self):
        actual = self.commaize(1000.0)
        assert actual == "1,000"

    def test_commaize_commaizes_and_obeys_decimal_places(self):
        actual = self.commaize(1000, 4)
        assert actual == "1,000.0000"


class TestChartOfReceiving(Harness):
    def setUp(self):
        Harness.setUp(self)
        for participant in ['alice', 'bob']:
            self.make_participant(participant, last_bill_result='')

    def test_get_tip_distribution_handles_a_tip(self):
        Participant.from_username('alice').set_tip_to('bob', '3.00')
        expected = ([[Decimal('3.00'), 1, Decimal('3.00'), 1.0, Decimal('1')]],
                    1.0, Decimal('3.00'))
        actual = Participant.from_username('bob').get_tip_distribution()
        assert actual == expected

    def test_get_tip_distribution_handles_no_tips(self):
        expected = ([], 0.0, Decimal('0.00'))
        actual = Participant.from_username('alice').get_tip_distribution()
        assert actual == expected

    def test_get_tip_distribution_handles_multiple_tips(self):
        self.make_participant('carl', last_bill_result='')
        Participant.from_username('alice').set_tip_to('bob', '1.00')
        Participant.from_username('carl').set_tip_to('bob', '3.00')
        expected = ([
            [Decimal('1.00'), 1L, Decimal('1.00'), 0.5, Decimal('0.25')],
            [Decimal('3.00'), 1L, Decimal('3.00'), 0.5, Decimal('0.75')]
        ], 2.0, Decimal('4.00'))
        actual = Participant.from_username('bob').get_tip_distribution()
        assert actual == expected

    def test_get_tip_distribution_handles_big_tips(self):
        bob = Participant.from_username('bob')
        bob.update_number('plural')
        self.make_participant('carl', last_bill_result='')
        Participant.from_username('alice').set_tip_to('bob', '200.00')
        Participant.from_username('carl').set_tip_to('bob', '300.00')
        expected = ([
            [Decimal('200.00'), 1L, Decimal('200.00'), 0.5, Decimal('0.4')],
            [Decimal('300.00'), 1L, Decimal('300.00'), 0.5, Decimal('0.6')]
        ], 2.0, Decimal('500.00'))
        actual = bob.get_tip_distribution()
        assert actual == expected

    def test_get_tip_distribution_ignores_bad_cc(self):
        self.make_participant('bad_cc', last_bill_result='Failure!')
        Participant.from_username('alice').set_tip_to('bob', '1.00')
        Participant.from_username('bad_cc').set_tip_to('bob', '3.00')
        expected = ([[Decimal('1.00'), 1L, Decimal('1.00'), 1, Decimal('1')]],
                    1.0, Decimal('1.00'))
        actual = Participant.from_username('bob').get_tip_distribution()
        assert actual == expected

    def test_get_tip_distribution_ignores_missing_cc(self):
        self.make_participant('missing_cc', last_bill_result=None)
        Participant.from_username('alice').set_tip_to('bob', '1.00')
        Participant.from_username('missing_cc').set_tip_to('bob', '3.00')
        expected = ([[Decimal('1.00'), 1L, Decimal('1.00'), 1, Decimal('1')]],
                    1.0, Decimal('1.00'))
        actual = Participant.from_username('bob').get_tip_distribution()
        assert actual == expected

class TestJson(Harness):

    def test_200(self):
        response = self.client.GET('/about/stats.json')
        assert response.code == 200
        body = json.loads(response.body)
        assert len(body) > 0

class TestRenderingStatsPage(Harness):
    def get_stats_page(self):
        return self.client.GET('/about/stats.html').body

    def test_stats_description_accurate_during_payday_run(self):
        """Test that stats page takes running payday into account.

        This test was originally written to expose the fix required for
        https://github.com/gittip/www.gittip.com/issues/92.
        """

        # Hydrating a website requires a functioning datetime module.
        self.client.hydrate_website()

        a_thursday = datetime.datetime(2012, 8, 9, 11, 00, 01)
        with patch.object(datetime, 'datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = a_thursday

            env = wireup.env()
            wireup.billing(env)
            payday = Payday(self.db)
            payday.start()

            body = self.get_stats_page()
            assert "is changing hands <b>right now!</b>" in body, body
            payday.end()

    def test_stats_description_accurate_outside_of_payday(self):
        """Test stats page outside of the payday running"""

        # Hydrating a website requires a functioning datetime module.
        self.client.hydrate_website()

        a_monday = datetime.datetime(2012, 8, 6, 11, 00, 01)
        with patch.object(datetime, 'datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = a_monday

            payday = Payday(self.db)
            payday.start()

            body = self.get_stats_page()
            assert "is ready for <b>this Thursday</b>" in body, body
            payday.end()

########NEW FILE########
__FILENAME__ = test_take
from __future__ import unicode_literals

from decimal import Decimal as D

from gittip.testing import Harness


default_team_name = 'Team'


class Tests(Harness):

    def make_team(self, name=default_team_name):
        team = self.make_participant(name, number='plural')

        warbucks = self.make_participant( 'Daddy Warbucks'
                                        , last_bill_result=''
                                         )
        warbucks.set_tip_to(name, '100')

        return team

    def make_participant(self, username, *arg, **kw):
        take_last_week = kw.pop('take_last_week', '40')
        team_name = kw.pop('team_name', default_team_name)
        participant = Harness.make_participant(self, username, **kw)
        if username == 'alice':
            self.db.run("INSERT INTO paydays DEFAULT VALUES")
            self.db.run( "INSERT INTO transfers "
                           "(timestamp, tipper, tippee, amount) "
                           "VALUES (now(), %s, 'alice', %s)"
                         , (team_name, take_last_week,)
                          )
        return participant

    def test_we_can_make_a_team(self):
        team = self.make_team()
        assert team.IS_PLURAL

    def test_random_schmoe_is_not_member_of_team(self):
        team = self.make_team()
        schmoe = self.make_participant('schmoe')
        assert not schmoe.member_of(team)

    def test_team_member_is_team_member(self):
        team = self.make_team()
        alice = self.make_participant('alice')
        team.add_member(alice)
        assert alice.member_of(team)

    def test_cant_grow_tip_a_lot(self):
        team = self.make_team()
        alice = self.make_participant('alice')
        team._MixinTeam__set_take_for(alice, D('40.00'), team)
        assert team.set_take_for(alice, D('100.00'), alice) == 80

    def test_take_can_double(self):
        team = self.make_team()
        alice = self.make_participant('alice')
        team._MixinTeam__set_take_for(alice, D('40.00'), team)
        team.set_take_for(alice, D('80.00'), alice)
        assert team.get_take_for(alice) == 80

    def test_take_can_double_but_not_a_penny_more(self):
        team = self.make_team()
        alice = self.make_participant('alice')
        team._MixinTeam__set_take_for(alice, D('40.00'), team)
        actual = team.set_take_for(alice, D('80.01'), alice)
        assert actual == 80

    def test_increase_is_based_on_actual_take_last_week(self):
        team = self.make_team()
        alice = self.make_participant('alice', take_last_week='20.00')
        team._MixinTeam__set_take_for(alice, D('35.00'), team)
        assert team.set_take_for(alice, D('42.00'), alice) == 40

    def test_if_last_week_is_less_than_a_dollar_can_increase_to_a_dollar(self):
        team = self.make_team()
        alice = self.make_participant('alice', take_last_week='0.01')
        team.add_member(alice)
        actual = team.set_take_for(alice, D('42.00'), team)
        assert actual == 1

    def test_get_members(self):
        team = self.make_team()
        alice = self.make_participant('alice')
        team.add_member(alice)
        team.set_take_for(alice, D('42.00'), team)
        members = team.get_members(alice)
        assert len(members) == 2
        assert members[0]['username'] == 'alice'
        assert members[0]['take'] == 42
        assert members[0]['balance'] == 58

########NEW FILE########
__FILENAME__ = test_teams
from __future__ import unicode_literals

from gittip.testing import Harness
from gittip.security.user import User


class Tests(Harness):

    def setUp(self):
        Harness.setUp(self)
        self.team = self.make_participant('A-Team', number='plural')

    def test_is_team(self):
        expeted = True
        actual = self.team.IS_PLURAL
        assert actual == expeted

    def test_show_as_team_to_admin(self):
        self.make_participant('alice', is_admin=True)
        user = User.from_username('alice')
        assert self.team.show_as_team(user)

    def test_show_as_team_to_team_member(self):
        self.make_participant('alice')
        self.team.add_member(self.make_participant('bob'))
        user = User.from_username('bob')
        assert self.team.show_as_team(user)

    def test_show_as_team_to_non_team_member(self):
        self.make_participant('alice')
        self.team.add_member(self.make_participant('bob'))
        user = User.from_username('alice')
        assert self.team.show_as_team(user)

    def test_show_as_team_to_anon(self):
        self.make_participant('alice')
        self.team.add_member(self.make_participant('bob'))
        assert self.team.show_as_team(User())

    def test_dont_show_individuals_as_team(self):
        alice = self.make_participant('alice', number='singular')
        assert not alice.show_as_team(User())

    def test_dont_show_plural_no_members_as_team_to_anon(self):
        group = self.make_participant('Group', number='plural')
        assert not group.show_as_team(User())

    def test_dont_show_plural_no_members_as_team_to_auth(self):
        group = self.make_participant('Group', number='plural')
        self.make_participant('alice')
        assert not group.show_as_team(User.from_username('alice'))

    def test_show_plural_no_members_as_team_to_self(self):
        group = self.make_participant('Group', number='plural')
        assert group.show_as_team(User.from_username('Group'))

    def test_show_plural_no_members_as_team_to_admin(self):
        group = self.make_participant('Group', number='plural')
        self.make_participant('Admin', is_admin=True)
        assert group.show_as_team(User.from_username('Admin'))


    def test_can_add_members(self):
        alice = self.make_participant('alice')
        expected = True
        self.team.add_member(alice)
        actual = alice.member_of(self.team)
        assert actual == expected

    def test_get_teams_for_member(self):
        alice = self.make_participant('alice')
        bob = self.make_participant('bob')
        team = self.make_participant('B-Team', number='plural')
        self.team.add_member(alice)
        team.add_member(bob)
        expected = 1
        actual = alice.get_teams().pop().nmembers
        assert actual == expected

########NEW FILE########
__FILENAME__ = test_tips_json
from __future__ import print_function, unicode_literals

import datetime
import json

import pytz

from gittip.testing import Harness


class TestTipsJson(Harness):

    def also_prune_variant(self, also_prune, tippees=1):

        now = datetime.datetime.now(pytz.utc)
        self.make_participant("test_tippee1", claimed_time=now)
        self.make_participant("test_tippee2", claimed_time=now)
        self.make_participant("test_tipper", claimed_time=now)

        data = [
            {'username': 'test_tippee1', 'platform': 'gittip', 'amount': '1.00'},
            {'username': 'test_tippee2', 'platform': 'gittip', 'amount': '2.00'}
        ]

        response = self.client.POST( '/test_tipper/tips.json'
                                   , body=json.dumps(data)
                                   , content_type='application/json'
                                   , auth_as='test_tipper'
                                    )

        assert response.code == 200
        assert len(json.loads(response.body)) == 2

        response = self.client.POST( '/test_tipper/tips.json?also_prune=' + also_prune
                                   , body=json.dumps([{ 'username': 'test_tippee2'
                                                      , 'platform': 'gittip'
                                                      , 'amount': '1.00'
                                                       }])
                                   , content_type='application/json'
                                   , auth_as='test_tipper'
                                    )

        assert response.code == 200

        response = self.client.GET('/test_tipper/tips.json', auth_as='test_tipper')
        assert response.code == 200
        assert len(json.loads(response.body)) == tippees

    def test_get_response(self):
        now = datetime.datetime.now(pytz.utc)
        self.make_participant("test_tipper", claimed_time=now)

        response = self.client.GET('/test_tipper/tips.json', auth_as='test_tipper')

        assert response.code == 200
        assert len(json.loads(response.body)) == 0 # empty array

    def test_get_response_with_tips(self):
        now = datetime.datetime.now(pytz.utc)
        self.make_participant("test_tippee1", claimed_time=now)
        self.make_participant("test_tipper", claimed_time=now)

        response = self.client.POST( '/test_tippee1/tip.json'
                                   , {'amount': '1.00'}
                                   , auth_as='test_tipper'
                                    )

        assert response.code == 200
        assert json.loads(response.body)['amount'] == '1.00'

        response = self.client.GET('/test_tipper/tips.json', auth_as='test_tipper')
        data = json.loads(response.body)[0]

        assert response.code == 200
        assert data['username'] == 'test_tippee1'
        assert data['amount'] == '1.00'

    def test_post_bad_platform(self):
        now = datetime.datetime.now(pytz.utc)
        self.make_participant("test_tippee1", claimed_time=now)
        self.make_participant("test_tipper", claimed_time=now)

        response = self.client.POST( '/test_tipper/tips.json'
                                   , body=json.dumps([{ 'username': 'test_tippee1'
                                                 , 'platform': 'badname'
                                                 , 'amount': '1.00'
                                                  }])
                                   , auth_as='test_tipper'
                                   , content_type='application/json'
                                    )

        assert response.code == 200

        resp = json.loads(response.body)

        for tip in resp:
            assert 'error' in tip

    def test_also_prune_as_1(self):
        self.also_prune_variant('1')

    def test_also_prune_as_true(self):
        self.also_prune_variant('true')

    def test_also_prune_as_yes(self):
        self.also_prune_variant('yes')

    def test_also_prune_as_0(self):
        self.also_prune_variant('0', 2)

########NEW FILE########
__FILENAME__ = test_tip_json
from __future__ import print_function, unicode_literals

import datetime
import json

import pytz

from gittip.testing import Harness


class TestTipJson(Harness):

    def test_get_amount_and_total_back_from_api(self):
        "Test that we get correct amounts and totals back on POSTs to tip.json"

        # First, create some test data
        # We need accounts
        now = datetime.datetime.now(pytz.utc)
        self.make_participant("test_tippee1", claimed_time=now)
        self.make_participant("test_tippee2", claimed_time=now)
        self.make_participant("test_tipper")

        # Then, add a $1.50 and $3.00 tip
        response1 = self.client.POST( "/test_tippee1/tip.json"
                                    , {'amount': "1.00"}
                                    , auth_as='test_tipper'
                                     )

        response2 = self.client.POST( "/test_tippee2/tip.json"
                                    , {'amount': "3.00"}
                                    , auth_as='test_tipper'
                                     )

        # Confirm we get back the right amounts.
        first_data = json.loads(response1.body)
        second_data = json.loads(response2.body)
        assert first_data['amount'] == "1.00"
        assert first_data['total_giving'] == "1.00"
        assert second_data['amount'] == "3.00"
        assert second_data['total_giving'] == "4.00"

    def test_set_tip_out_of_range(self):
        now = datetime.datetime.now(pytz.utc)
        self.make_participant("alice", claimed_time=now)
        self.make_participant("bob", claimed_time=now)

        response = self.client.PxST( "/alice/tip.json"
                                   , {'amount': "110.00"}
                                   , auth_as='bob'
                                    )
        assert "bad amount" in response.body
        assert response.code == 400

        response = self.client.PxST( "/alice/tip.json"
                                   , {'amount': "-1.00"}
                                   , auth_as='bob'
                                    )
        assert "bad amount" in response.body
        assert response.code == 400

########NEW FILE########
__FILENAME__ = test_user
from __future__ import print_function, unicode_literals

from gittip.security.user import User
from gittip.testing import Harness


class TestUser(Harness):

    def test_anonymous_user_is_anonymous(self):
        user = User()
        assert user.ANON

    def test_anonymous_user_is_not_admin(self):
        user = User()
        assert not user.ADMIN

    def test_known_user_is_known(self):
        self.make_participant('alice')
        alice = User.from_username('alice')
        assert not alice.ANON

    def test_username_is_case_insensitive(self):
        self.make_participant('AlIcE')
        actual = User.from_username('aLiCe').participant.username_lower
        assert actual == 'alice'

    def test_known_user_is_not_admin(self):
        self.make_participant('alice')
        alice = User.from_username('alice')
        assert not alice.ADMIN

    def test_admin_user_is_admin(self):
        self.make_participant('alice', is_admin=True)
        alice = User.from_username('alice')
        assert alice.ADMIN


    # ANON

    def test_unreviewed_user_is_not_ANON(self):
        self.make_participant('alice', is_suspicious=None)
        alice = User.from_username('alice')
        assert alice.ANON is False

    def test_whitelisted_user_is_not_ANON(self):
        self.make_participant('alice', is_suspicious=False)
        alice = User.from_username('alice')
        assert alice.ANON is False

    def test_blacklisted_user_is_ANON(self):
        self.make_participant('alice', is_suspicious=True)
        alice = User.from_username('alice')
        assert alice.ANON is True


    # session token

    def test_user_from_bad_session_token_is_anonymous(self):
        user = User.from_session_token('deadbeef')
        assert user.ANON

    def test_user_from_None_session_token_is_anonymous(self):
        self.make_participant('alice')
        self.make_participant('bob')
        user = User.from_session_token(None)
        assert user.ANON

    def test_user_can_be_loaded_from_session_token(self):
        self.make_participant('alice')
        user = User.from_username('alice')
        user.sign_in()
        token = user.participant.session_token
        actual = User.from_session_token(token).participant.username
        assert actual == 'alice'


    # key token

    def test_user_from_bad_api_key_is_anonymous(self):
        user = User.from_api_key('deadbeef')
        assert user.ANON

    def test_user_from_None_api_key_is_anonymous(self):
        self.make_participant('alice')
        self.make_participant('bob')
        user = User.from_api_key(None)
        assert user.ANON

    def test_user_can_be_loaded_from_api_key(self):
        alice = self.make_participant('alice')
        api_key = alice.recreate_api_key()
        actual = User.from_api_key(api_key).participant.username
        assert actual == 'alice'


    def test_user_from_bad_id_is_anonymous(self):
        user = User.from_username('deadbeef')
        assert user.ANON

    def test_suspicious_user_from_username_is_anonymous(self):
        self.make_participant('alice', is_suspicious=True)
        user = User.from_username('alice')
        assert user.ANON

    def test_signed_out_user_is_anonymous(self):
        self.make_participant('alice')
        alice = User.from_username('alice')
        assert not alice.ANON
        alice.sign_out()
        assert alice.ANON

########NEW FILE########
__FILENAME__ = test_username_json
from __future__ import print_function, unicode_literals

import json

from gittip.testing import Harness


class Tests(Harness):

    def change_username(self, new_username, auth_as='alice', weird=False):
        if auth_as:
            self.make_participant(auth_as)

        if weird:
            post, args = self.client.PxST, {}
        else:
            post, args = self.client.POST, {'raise_immediately': False}

        r = post('/alice/username.json', {'username': new_username},
                                         auth_as=auth_as, **args)
        return r.code, r.body if weird else json.loads(r.body)

    def test_participant_can_change_their_username(self):
        code, body = self.change_username("bob")
        assert code == 200
        assert body['username'] == "bob"

    def test_anonymous_gets_404(self):
        code, body = self.change_username("bob", auth_as=None, weird=True)
        assert code == 404

    def test_empty(self):
        code, body = self.change_username('      ')
        assert code == 400
        assert body['error_message_long'] == "You need to provide a username!"

    def test_invalid(self):
        code, body = self.change_username("§".encode('utf8'))
        assert code == 400
        assert body['error_message_long'] == "The username '§' contains invalid characters."

    def test_restricted_username(self):
        code, body = self.change_username("assets")
        assert code == 400
        assert body['error_message_long'] == "The username 'assets' is restricted."

    def test_unavailable(self):
        self.make_participant("bob")
        code, body = self.change_username("bob")
        assert code == 400
        assert body['error_message_long'] == "The username 'bob' is already taken."

    def test_too_long(self):
        username = "I am way too long, and you know it, and the American people know it."
        code, body = self.change_username(username)
        assert code == 400
        assert body['error_message_long'] == "The username '%s' is too long." % username

########NEW FILE########
__FILENAME__ = test_utils
from __future__ import absolute_import, division, print_function, unicode_literals

from aspen.http.response import Response
from gittip import utils
from gittip.testing import Harness
from datetime import datetime
from datetime import timedelta

class Tests(Harness):

    def test_get_participant_gets_participant(self):
        expected = self.make_participant('alice', claimed_time='now')
        request = self.client.GET( '/alice/'
                                 , return_after='dispatch_request_to_filesystem'
                                 , want='request'
                                  )
        actual = utils.get_participant(request, restrict=False)
        assert actual == expected

    def test_get_participant_canonicalizes(self):
        self.make_participant('alice', claimed_time='now')
        request = self.client.GET( '/Alice/'
                                 , return_after='dispatch_request_to_filesystem'
                                 , want='request'
                                  )

        with self.assertRaises(Response) as cm:
            utils.get_participant(request, restrict=False)
        actual = cm.exception.code

        assert actual == 302

    def test_dict_to_querystring_converts_dict_to_querystring(self):
        expected = "?foo=bar"
        actual = utils.dict_to_querystring({"foo": ["bar"]})
        assert actual == expected

    def test_dict_to_querystring_converts_empty_dict_to_querystring(self):
        expected = ""
        actual = utils.dict_to_querystring({})
        assert actual == expected

    def test_linkify_linkifies_url_with_www(self):
        expected = '<a href="http://www.example.com" target="_blank">http://www.example.com</a>'
        actual = utils.linkify('http://www.example.com')
        assert actual == expected

    def test_linkify_linkifies_url_without_www(self):
        expected = '<a href="http://example.com" target="_blank">http://example.com</a>'
        actual = utils.linkify('http://example.com')
        assert actual == expected

    def test_linkify_linkifies_url_with_uppercase_letters(self):
        expected = '<a href="Http://Www.Example.Com" target="_blank">Http://Www.Example.Com</a>'
        actual = utils.linkify('Http://Www.Example.Com')
        assert actual == expected

    def test_linkify_works_without_protocol(self):
        expected = '<a href="http://www.example.com" target="_blank">www.example.com</a>'
        actual = utils.linkify('www.example.com')
        assert actual == expected

    def test_short_difference_is_expiring(self):
        expiring = datetime.utcnow() + timedelta(days = 1)
        expiring = utils.is_card_expiring(expiring.year, expiring.month)
        assert expiring

    def test_long_difference_not_expiring(self):
        expiring = datetime.utcnow() + timedelta(days = 100)
        expiring = utils.is_card_expiring(expiring.year, expiring.month)
        assert not expiring

########NEW FILE########
__FILENAME__ = virtualenv-1.9.1
#!/usr/bin/env python
"""Create a "virtual" Python installation
"""

# If you change the version here, change it in setup.py
# and docs/conf.py as well.
__version__ = "1.9.1"  # following best practices
virtualenv_version = __version__  # legacy, again

import base64
import sys
import os
import codecs
import optparse
import re
import shutil
import logging
import tempfile
import zlib
import errno
import glob
import distutils.sysconfig
from distutils.util import strtobool
import struct
import subprocess

if sys.version_info < (2, 5):
    print('ERROR: %s' % sys.exc_info()[1])
    print('ERROR: this script requires Python 2.5 or greater.')
    sys.exit(101)

try:
    set
except NameError:
    from sets import Set as set
try:
    basestring
except NameError:
    basestring = str

try:
    import ConfigParser
except ImportError:
    import configparser as ConfigParser

join = os.path.join
py_version = 'python%s.%s' % (sys.version_info[0], sys.version_info[1])

is_jython = sys.platform.startswith('java')
is_pypy = hasattr(sys, 'pypy_version_info')
is_win = (sys.platform == 'win32')
is_cygwin = (sys.platform == 'cygwin')
is_darwin = (sys.platform == 'darwin')
abiflags = getattr(sys, 'abiflags', '')

user_dir = os.path.expanduser('~')
if is_win:
    default_storage_dir = os.path.join(user_dir, 'virtualenv')
else:
    default_storage_dir = os.path.join(user_dir, '.virtualenv')
default_config_file = os.path.join(default_storage_dir, 'virtualenv.ini')

if is_pypy:
    expected_exe = 'pypy'
elif is_jython:
    expected_exe = 'jython'
else:
    expected_exe = 'python'


REQUIRED_MODULES = ['os', 'posix', 'posixpath', 'nt', 'ntpath', 'genericpath',
                    'fnmatch', 'locale', 'encodings', 'codecs',
                    'stat', 'UserDict', 'readline', 'copy_reg', 'types',
                    're', 'sre', 'sre_parse', 'sre_constants', 'sre_compile',
                    'zlib']

REQUIRED_FILES = ['lib-dynload', 'config']

majver, minver = sys.version_info[:2]
if majver == 2:
    if minver >= 6:
        REQUIRED_MODULES.extend(['warnings', 'linecache', '_abcoll', 'abc'])
    if minver >= 7:
        REQUIRED_MODULES.extend(['_weakrefset'])
    if minver <= 3:
        REQUIRED_MODULES.extend(['sets', '__future__'])
elif majver == 3:
    # Some extra modules are needed for Python 3, but different ones
    # for different versions.
    REQUIRED_MODULES.extend(['_abcoll', 'warnings', 'linecache', 'abc', 'io',
                             '_weakrefset', 'copyreg', 'tempfile', 'random',
                             '__future__', 'collections', 'keyword', 'tarfile',
                             'shutil', 'struct', 'copy', 'tokenize', 'token',
                             'functools', 'heapq', 'bisect', 'weakref',
                             'reprlib'])
    if minver >= 2:
        REQUIRED_FILES[-1] = 'config-%s' % majver
    if minver == 3:
        import sysconfig
        platdir = sysconfig.get_config_var('PLATDIR')
        REQUIRED_FILES.append(platdir)
        # The whole list of 3.3 modules is reproduced below - the current
        # uncommented ones are required for 3.3 as of now, but more may be
        # added as 3.3 development continues.
        REQUIRED_MODULES.extend([
            #"aifc",
            #"antigravity",
            #"argparse",
            #"ast",
            #"asynchat",
            #"asyncore",
            "base64",
            #"bdb",
            #"binhex",
            #"bisect",
            #"calendar",
            #"cgi",
            #"cgitb",
            #"chunk",
            #"cmd",
            #"codeop",
            #"code",
            #"colorsys",
            #"_compat_pickle",
            #"compileall",
            #"concurrent",
            #"configparser",
            #"contextlib",
            #"cProfile",
            #"crypt",
            #"csv",
            #"ctypes",
            #"curses",
            #"datetime",
            #"dbm",
            #"decimal",
            #"difflib",
            #"dis",
            #"doctest",
            #"dummy_threading",
            "_dummy_thread",
            #"email",
            #"filecmp",
            #"fileinput",
            #"formatter",
            #"fractions",
            #"ftplib",
            #"functools",
            #"getopt",
            #"getpass",
            #"gettext",
            #"glob",
            #"gzip",
            "hashlib",
            #"heapq",
            "hmac",
            #"html",
            #"http",
            #"idlelib",
            #"imaplib",
            #"imghdr",
            "imp",
            "importlib",
            #"inspect",
            #"json",
            #"lib2to3",
            #"logging",
            #"macpath",
            #"macurl2path",
            #"mailbox",
            #"mailcap",
            #"_markupbase",
            #"mimetypes",
            #"modulefinder",
            #"multiprocessing",
            #"netrc",
            #"nntplib",
            #"nturl2path",
            #"numbers",
            #"opcode",
            #"optparse",
            #"os2emxpath",
            #"pdb",
            #"pickle",
            #"pickletools",
            #"pipes",
            #"pkgutil",
            #"platform",
            #"plat-linux2",
            #"plistlib",
            #"poplib",
            #"pprint",
            #"profile",
            #"pstats",
            #"pty",
            #"pyclbr",
            #"py_compile",
            #"pydoc_data",
            #"pydoc",
            #"_pyio",
            #"queue",
            #"quopri",
            #"reprlib",
            "rlcompleter",
            #"runpy",
            #"sched",
            #"shelve",
            #"shlex",
            #"smtpd",
            #"smtplib",
            #"sndhdr",
            #"socket",
            #"socketserver",
            #"sqlite3",
            #"ssl",
            #"stringprep",
            #"string",
            #"_strptime",
            #"subprocess",
            #"sunau",
            #"symbol",
            #"symtable",
            #"sysconfig",
            #"tabnanny",
            #"telnetlib",
            #"test",
            #"textwrap",
            #"this",
            #"_threading_local",
            #"threading",
            #"timeit",
            #"tkinter",
            #"tokenize",
            #"token",
            #"traceback",
            #"trace",
            #"tty",
            #"turtledemo",
            #"turtle",
            #"unittest",
            #"urllib",
            #"uuid",
            #"uu",
            #"wave",
            #"weakref",
            #"webbrowser",
            #"wsgiref",
            #"xdrlib",
            #"xml",
            #"xmlrpc",
            #"zipfile",
        ])

if is_pypy:
    # these are needed to correctly display the exceptions that may happen
    # during the bootstrap
    REQUIRED_MODULES.extend(['traceback', 'linecache'])

class Logger(object):

    """
    Logging object for use in command-line script.  Allows ranges of
    levels, to avoid some redundancy of displayed information.
    """

    DEBUG = logging.DEBUG
    INFO = logging.INFO
    NOTIFY = (logging.INFO+logging.WARN)/2
    WARN = WARNING = logging.WARN
    ERROR = logging.ERROR
    FATAL = logging.FATAL

    LEVELS = [DEBUG, INFO, NOTIFY, WARN, ERROR, FATAL]

    def __init__(self, consumers):
        self.consumers = consumers
        self.indent = 0
        self.in_progress = None
        self.in_progress_hanging = False

    def debug(self, msg, *args, **kw):
        self.log(self.DEBUG, msg, *args, **kw)
    def info(self, msg, *args, **kw):
        self.log(self.INFO, msg, *args, **kw)
    def notify(self, msg, *args, **kw):
        self.log(self.NOTIFY, msg, *args, **kw)
    def warn(self, msg, *args, **kw):
        self.log(self.WARN, msg, *args, **kw)
    def error(self, msg, *args, **kw):
        self.log(self.ERROR, msg, *args, **kw)
    def fatal(self, msg, *args, **kw):
        self.log(self.FATAL, msg, *args, **kw)
    def log(self, level, msg, *args, **kw):
        if args:
            if kw:
                raise TypeError(
                    "You may give positional or keyword arguments, not both")
        args = args or kw
        rendered = None
        for consumer_level, consumer in self.consumers:
            if self.level_matches(level, consumer_level):
                if (self.in_progress_hanging
                    and consumer in (sys.stdout, sys.stderr)):
                    self.in_progress_hanging = False
                    sys.stdout.write('\n')
                    sys.stdout.flush()
                if rendered is None:
                    if args:
                        rendered = msg % args
                    else:
                        rendered = msg
                    rendered = ' '*self.indent + rendered
                if hasattr(consumer, 'write'):
                    consumer.write(rendered+'\n')
                else:
                    consumer(rendered)

    def start_progress(self, msg):
        assert not self.in_progress, (
            "Tried to start_progress(%r) while in_progress %r"
            % (msg, self.in_progress))
        if self.level_matches(self.NOTIFY, self._stdout_level()):
            sys.stdout.write(msg)
            sys.stdout.flush()
            self.in_progress_hanging = True
        else:
            self.in_progress_hanging = False
        self.in_progress = msg

    def end_progress(self, msg='done.'):
        assert self.in_progress, (
            "Tried to end_progress without start_progress")
        if self.stdout_level_matches(self.NOTIFY):
            if not self.in_progress_hanging:
                # Some message has been printed out since start_progress
                sys.stdout.write('...' + self.in_progress + msg + '\n')
                sys.stdout.flush()
            else:
                sys.stdout.write(msg + '\n')
                sys.stdout.flush()
        self.in_progress = None
        self.in_progress_hanging = False

    def show_progress(self):
        """If we are in a progress scope, and no log messages have been
        shown, write out another '.'"""
        if self.in_progress_hanging:
            sys.stdout.write('.')
            sys.stdout.flush()

    def stdout_level_matches(self, level):
        """Returns true if a message at this level will go to stdout"""
        return self.level_matches(level, self._stdout_level())

    def _stdout_level(self):
        """Returns the level that stdout runs at"""
        for level, consumer in self.consumers:
            if consumer is sys.stdout:
                return level
        return self.FATAL

    def level_matches(self, level, consumer_level):
        """
        >>> l = Logger([])
        >>> l.level_matches(3, 4)
        False
        >>> l.level_matches(3, 2)
        True
        >>> l.level_matches(slice(None, 3), 3)
        False
        >>> l.level_matches(slice(None, 3), 2)
        True
        >>> l.level_matches(slice(1, 3), 1)
        True
        >>> l.level_matches(slice(2, 3), 1)
        False
        """
        if isinstance(level, slice):
            start, stop = level.start, level.stop
            if start is not None and start > consumer_level:
                return False
            if stop is not None and stop <= consumer_level:
                return False
            return True
        else:
            return level >= consumer_level

    #@classmethod
    def level_for_integer(cls, level):
        levels = cls.LEVELS
        if level < 0:
            return levels[0]
        if level >= len(levels):
            return levels[-1]
        return levels[level]

    level_for_integer = classmethod(level_for_integer)

# create a silent logger just to prevent this from being undefined
# will be overridden with requested verbosity main() is called.
logger = Logger([(Logger.LEVELS[-1], sys.stdout)])

def mkdir(path):
    if not os.path.exists(path):
        logger.info('Creating %s', path)
        os.makedirs(path)
    else:
        logger.info('Directory %s already exists', path)

def copyfileordir(src, dest):
    if os.path.isdir(src):
        shutil.copytree(src, dest, True)
    else:
        shutil.copy2(src, dest)

def copyfile(src, dest, symlink=True):
    if not os.path.exists(src):
        # Some bad symlink in the src
        logger.warn('Cannot find file %s (bad symlink)', src)
        return
    if os.path.exists(dest):
        logger.debug('File %s already exists', dest)
        return
    if not os.path.exists(os.path.dirname(dest)):
        logger.info('Creating parent directories for %s' % os.path.dirname(dest))
        os.makedirs(os.path.dirname(dest))
    if not os.path.islink(src):
        srcpath = os.path.abspath(src)
    else:
        srcpath = os.readlink(src)
    if symlink and hasattr(os, 'symlink') and not is_win:
        logger.info('Symlinking %s', dest)
        try:
            os.symlink(srcpath, dest)
        except (OSError, NotImplementedError):
            logger.info('Symlinking failed, copying to %s', dest)
            copyfileordir(src, dest)
    else:
        logger.info('Copying to %s', dest)
        copyfileordir(src, dest)

def writefile(dest, content, overwrite=True):
    if not os.path.exists(dest):
        logger.info('Writing %s', dest)
        f = open(dest, 'wb')
        f.write(content.encode('utf-8'))
        f.close()
        return
    else:
        f = open(dest, 'rb')
        c = f.read()
        f.close()
        if c != content.encode("utf-8"):
            if not overwrite:
                logger.notify('File %s exists with different content; not overwriting', dest)
                return
            logger.notify('Overwriting %s with new content', dest)
            f = open(dest, 'wb')
            f.write(content.encode('utf-8'))
            f.close()
        else:
            logger.info('Content %s already in place', dest)

def rmtree(dir):
    if os.path.exists(dir):
        logger.notify('Deleting tree %s', dir)
        shutil.rmtree(dir)
    else:
        logger.info('Do not need to delete %s; already gone', dir)

def make_exe(fn):
    if hasattr(os, 'chmod'):
        oldmode = os.stat(fn).st_mode & 0xFFF # 0o7777
        newmode = (oldmode | 0x16D) & 0xFFF # 0o555, 0o7777
        os.chmod(fn, newmode)
        logger.info('Changed mode of %s to %s', fn, oct(newmode))

def _find_file(filename, dirs):
    for dir in reversed(dirs):
        files = glob.glob(os.path.join(dir, filename))
        if files and os.path.isfile(files[0]):
            return True, files[0]
    return False, filename

def _install_req(py_executable, unzip=False, distribute=False,
                 search_dirs=None, never_download=False):

    if search_dirs is None:
        search_dirs = file_search_dirs()

    if not distribute:
        egg_path = 'setuptools-*-py%s.egg' % sys.version[:3]
        found, egg_path = _find_file(egg_path, search_dirs)
        project_name = 'setuptools'
        bootstrap_script = EZ_SETUP_PY
        tgz_path = None
    else:
        # Look for a distribute egg (these are not distributed by default,
        # but can be made available by the user)
        egg_path = 'distribute-*-py%s.egg' % sys.version[:3]
        found, egg_path = _find_file(egg_path, search_dirs)
        project_name = 'distribute'
        if found:
            tgz_path = None
            bootstrap_script = DISTRIBUTE_FROM_EGG_PY
        else:
            # Fall back to sdist
            # NB: egg_path is not None iff tgz_path is None
            # iff bootstrap_script is a generic setup script accepting
            # the standard arguments.
            egg_path = None
            tgz_path = 'distribute-*.tar.gz'
            found, tgz_path = _find_file(tgz_path, search_dirs)
            bootstrap_script = DISTRIBUTE_SETUP_PY

    if is_jython and os._name == 'nt':
        # Jython's .bat sys.executable can't handle a command line
        # argument with newlines
        fd, ez_setup = tempfile.mkstemp('.py')
        os.write(fd, bootstrap_script)
        os.close(fd)
        cmd = [py_executable, ez_setup]
    else:
        cmd = [py_executable, '-c', bootstrap_script]
    if unzip and egg_path:
        cmd.append('--always-unzip')
    env = {}
    remove_from_env = ['__PYVENV_LAUNCHER__']
    if logger.stdout_level_matches(logger.DEBUG) and egg_path:
        cmd.append('-v')

    old_chdir = os.getcwd()
    if egg_path is not None and os.path.exists(egg_path):
        logger.info('Using existing %s egg: %s' % (project_name, egg_path))
        cmd.append(egg_path)
        if os.environ.get('PYTHONPATH'):
            env['PYTHONPATH'] = egg_path + os.path.pathsep + os.environ['PYTHONPATH']
        else:
            env['PYTHONPATH'] = egg_path
    elif tgz_path is not None and os.path.exists(tgz_path):
        # Found a tgz source dist, let's chdir
        logger.info('Using existing %s egg: %s' % (project_name, tgz_path))
        os.chdir(os.path.dirname(tgz_path))
        # in this case, we want to be sure that PYTHONPATH is unset (not
        # just empty, really unset), else CPython tries to import the
        # site.py that it's in virtualenv_support
        remove_from_env.append('PYTHONPATH')
    elif never_download:
        logger.fatal("Can't find any local distributions of %s to install "
                     "and --never-download is set.  Either re-run virtualenv "
                     "without the --never-download option, or place a %s "
                     "distribution (%s) in one of these "
                     "locations: %r" % (project_name, project_name,
                                        egg_path or tgz_path,
                                        search_dirs))
        sys.exit(1)
    elif egg_path:
        logger.info('No %s egg found; downloading' % project_name)
        cmd.extend(['--always-copy', '-U', project_name])
    else:
        logger.info('No %s tgz found; downloading' % project_name)
    logger.start_progress('Installing %s...' % project_name)
    logger.indent += 2
    cwd = None
    if project_name == 'distribute':
        env['DONT_PATCH_SETUPTOOLS'] = 'true'

    def _filter_ez_setup(line):
        return filter_ez_setup(line, project_name)

    if not os.access(os.getcwd(), os.W_OK):
        cwd = tempfile.mkdtemp()
        if tgz_path is not None and os.path.exists(tgz_path):
            # the current working dir is hostile, let's copy the
            # tarball to a temp dir
            target = os.path.join(cwd, os.path.split(tgz_path)[-1])
            shutil.copy(tgz_path, target)
    try:
        call_subprocess(cmd, show_stdout=False,
                        filter_stdout=_filter_ez_setup,
                        extra_env=env,
                        remove_from_env=remove_from_env,
                        cwd=cwd)
    finally:
        logger.indent -= 2
        logger.end_progress()
        if cwd is not None:
            shutil.rmtree(cwd)
        if os.getcwd() != old_chdir:
            os.chdir(old_chdir)
        if is_jython and os._name == 'nt':
            os.remove(ez_setup)

def file_search_dirs():
    here = os.path.dirname(os.path.abspath(__file__))
    dirs = ['.', here,
            join(here, 'virtualenv_support')]
    if os.path.splitext(os.path.dirname(__file__))[0] != 'virtualenv':
        # Probably some boot script; just in case virtualenv is installed...
        try:
            import virtualenv
        except ImportError:
            pass
        else:
            dirs.append(os.path.join(os.path.dirname(virtualenv.__file__), 'virtualenv_support'))
    return [d for d in dirs if os.path.isdir(d)]

def install_setuptools(py_executable, unzip=False,
                       search_dirs=None, never_download=False):
    _install_req(py_executable, unzip,
                 search_dirs=search_dirs, never_download=never_download)

def install_distribute(py_executable, unzip=False,
                       search_dirs=None, never_download=False):
    _install_req(py_executable, unzip, distribute=True,
                 search_dirs=search_dirs, never_download=never_download)

_pip_re = re.compile(r'^pip-.*(zip|tar.gz|tar.bz2|tgz|tbz)$', re.I)
def install_pip(py_executable, search_dirs=None, never_download=False):
    if search_dirs is None:
        search_dirs = file_search_dirs()

    filenames = []
    for dir in search_dirs:
        filenames.extend([join(dir, fn) for fn in os.listdir(dir)
                          if _pip_re.search(fn)])
    filenames = [(os.path.basename(filename).lower(), i, filename) for i, filename in enumerate(filenames)]
    filenames.sort()
    filenames = [filename for basename, i, filename in filenames]
    if not filenames:
        filename = 'pip'
    else:
        filename = filenames[-1]
    easy_install_script = 'easy_install'
    if is_win:
        easy_install_script = 'easy_install-script.py'
    # There's two subtle issues here when invoking easy_install.
    # 1. On unix-like systems the easy_install script can *only* be executed
    #    directly if its full filesystem path is no longer than 78 characters.
    # 2. A work around to [1] is to use the `python path/to/easy_install foo`
    #    pattern, but that breaks if the path contains non-ASCII characters, as
    #    you can't put the file encoding declaration before the shebang line.
    # The solution is to use Python's -x flag to skip the first line of the
    # script (and any ASCII decoding errors that may have occurred in that line)
    cmd = [py_executable, '-x', join(os.path.dirname(py_executable), easy_install_script), filename]
    # jython and pypy don't yet support -x
    if is_jython or is_pypy:
        cmd.remove('-x')
    if filename == 'pip':
        if never_download:
            logger.fatal("Can't find any local distributions of pip to install "
                         "and --never-download is set.  Either re-run virtualenv "
                         "without the --never-download option, or place a pip "
                         "source distribution (zip/tar.gz/tar.bz2) in one of these "
                         "locations: %r" % search_dirs)
            sys.exit(1)
        logger.info('Installing pip from network...')
    else:
        logger.info('Installing existing %s distribution: %s' % (
                os.path.basename(filename), filename))
    logger.start_progress('Installing pip...')
    logger.indent += 2
    def _filter_setup(line):
        return filter_ez_setup(line, 'pip')
    try:
        call_subprocess(cmd, show_stdout=False,
                        filter_stdout=_filter_setup)
    finally:
        logger.indent -= 2
        logger.end_progress()

def filter_ez_setup(line, project_name='setuptools'):
    if not line.strip():
        return Logger.DEBUG
    if project_name == 'distribute':
        for prefix in ('Extracting', 'Now working', 'Installing', 'Before',
                       'Scanning', 'Setuptools', 'Egg', 'Already',
                       'running', 'writing', 'reading', 'installing',
                       'creating', 'copying', 'byte-compiling', 'removing',
                       'Processing'):
            if line.startswith(prefix):
                return Logger.DEBUG
        return Logger.DEBUG
    for prefix in ['Reading ', 'Best match', 'Processing setuptools',
                   'Copying setuptools', 'Adding setuptools',
                   'Installing ', 'Installed ']:
        if line.startswith(prefix):
            return Logger.DEBUG
    return Logger.INFO


class UpdatingDefaultsHelpFormatter(optparse.IndentedHelpFormatter):
    """
    Custom help formatter for use in ConfigOptionParser that updates
    the defaults before expanding them, allowing them to show up correctly
    in the help listing
    """
    def expand_default(self, option):
        if self.parser is not None:
            self.parser.update_defaults(self.parser.defaults)
        return optparse.IndentedHelpFormatter.expand_default(self, option)


class ConfigOptionParser(optparse.OptionParser):
    """
    Custom option parser which updates its defaults by by checking the
    configuration files and environmental variables
    """
    def __init__(self, *args, **kwargs):
        self.config = ConfigParser.RawConfigParser()
        self.files = self.get_config_files()
        self.config.read(self.files)
        optparse.OptionParser.__init__(self, *args, **kwargs)

    def get_config_files(self):
        config_file = os.environ.get('VIRTUALENV_CONFIG_FILE', False)
        if config_file and os.path.exists(config_file):
            return [config_file]
        return [default_config_file]

    def update_defaults(self, defaults):
        """
        Updates the given defaults with values from the config files and
        the environ. Does a little special handling for certain types of
        options (lists).
        """
        # Then go and look for the other sources of configuration:
        config = {}
        # 1. config files
        config.update(dict(self.get_config_section('virtualenv')))
        # 2. environmental variables
        config.update(dict(self.get_environ_vars()))
        # Then set the options with those values
        for key, val in config.items():
            key = key.replace('_', '-')
            if not key.startswith('--'):
                key = '--%s' % key  # only prefer long opts
            option = self.get_option(key)
            if option is not None:
                # ignore empty values
                if not val:
                    continue
                # handle multiline configs
                if option.action == 'append':
                    val = val.split()
                else:
                    option.nargs = 1
                if option.action == 'store_false':
                    val = not strtobool(val)
                elif option.action in ('store_true', 'count'):
                    val = strtobool(val)
                try:
                    val = option.convert_value(key, val)
                except optparse.OptionValueError:
                    e = sys.exc_info()[1]
                    print("An error occured during configuration: %s" % e)
                    sys.exit(3)
                defaults[option.dest] = val
        return defaults

    def get_config_section(self, name):
        """
        Get a section of a configuration
        """
        if self.config.has_section(name):
            return self.config.items(name)
        return []

    def get_environ_vars(self, prefix='VIRTUALENV_'):
        """
        Returns a generator with all environmental vars with prefix VIRTUALENV
        """
        for key, val in os.environ.items():
            if key.startswith(prefix):
                yield (key.replace(prefix, '').lower(), val)

    def get_default_values(self):
        """
        Overridding to make updating the defaults after instantiation of
        the option parser possible, update_defaults() does the dirty work.
        """
        if not self.process_default_values:
            # Old, pre-Optik 1.5 behaviour.
            return optparse.Values(self.defaults)

        defaults = self.update_defaults(self.defaults.copy())  # ours
        for option in self._get_all_options():
            default = defaults.get(option.dest)
            if isinstance(default, basestring):
                opt_str = option.get_opt_string()
                defaults[option.dest] = option.check_value(opt_str, default)
        return optparse.Values(defaults)


def main():
    parser = ConfigOptionParser(
        version=virtualenv_version,
        usage="%prog [OPTIONS] DEST_DIR",
        formatter=UpdatingDefaultsHelpFormatter())

    parser.add_option(
        '-v', '--verbose',
        action='count',
        dest='verbose',
        default=0,
        help="Increase verbosity")

    parser.add_option(
        '-q', '--quiet',
        action='count',
        dest='quiet',
        default=0,
        help='Decrease verbosity')

    parser.add_option(
        '-p', '--python',
        dest='python',
        metavar='PYTHON_EXE',
        help='The Python interpreter to use, e.g., --python=python2.5 will use the python2.5 '
        'interpreter to create the new environment.  The default is the interpreter that '
        'virtualenv was installed with (%s)' % sys.executable)

    parser.add_option(
        '--clear',
        dest='clear',
        action='store_true',
        help="Clear out the non-root install and start from scratch")

    parser.set_defaults(system_site_packages=False)
    parser.add_option(
        '--no-site-packages',
        dest='system_site_packages',
        action='store_false',
        help="Don't give access to the global site-packages dir to the "
             "virtual environment (default)")

    parser.add_option(
        '--system-site-packages',
        dest='system_site_packages',
        action='store_true',
        help="Give access to the global site-packages dir to the "
             "virtual environment")

    parser.add_option(
        '--unzip-setuptools',
        dest='unzip_setuptools',
        action='store_true',
        help="Unzip Setuptools or Distribute when installing it")

    parser.add_option(
        '--relocatable',
        dest='relocatable',
        action='store_true',
        help='Make an EXISTING virtualenv environment relocatable.  '
        'This fixes up scripts and makes all .pth files relative')

    parser.add_option(
        '--distribute', '--use-distribute',  # the second option is for legacy reasons here. Hi Kenneth!
        dest='use_distribute',
        action='store_true',
        help='Use Distribute instead of Setuptools. Set environ variable '
        'VIRTUALENV_DISTRIBUTE to make it the default ')

    parser.add_option(
        '--no-setuptools',
        dest='no_setuptools',
        action='store_true',
        help='Do not install distribute/setuptools (or pip) '
        'in the new virtualenv.')

    parser.add_option(
        '--no-pip',
        dest='no_pip',
        action='store_true',
        help='Do not install pip in the new virtualenv.')

    parser.add_option(
        '--setuptools',
        dest='use_distribute',
        action='store_false',
        help='Use Setuptools instead of Distribute.  Set environ variable '
        'VIRTUALENV_SETUPTOOLS to make it the default ')

    # Set this to True to use distribute by default, even in Python 2.
    parser.set_defaults(use_distribute=False)

    default_search_dirs = file_search_dirs()
    parser.add_option(
        '--extra-search-dir',
        dest="search_dirs",
        action="append",
        default=default_search_dirs,
        help="Directory to look for setuptools/distribute/pip distributions in. "
        "You can add any number of additional --extra-search-dir paths.")

    parser.add_option(
        '--never-download',
        dest="never_download",
        action="store_true",
        help="Never download anything from the network.  Instead, virtualenv will fail "
        "if local distributions of setuptools/distribute/pip are not present.")

    parser.add_option(
        '--prompt',
        dest='prompt',
        help='Provides an alternative prompt prefix for this environment')

    if 'extend_parser' in globals():
        extend_parser(parser)

    options, args = parser.parse_args()

    global logger

    if 'adjust_options' in globals():
        adjust_options(options, args)

    verbosity = options.verbose - options.quiet
    logger = Logger([(Logger.level_for_integer(2 - verbosity), sys.stdout)])

    if options.python and not os.environ.get('VIRTUALENV_INTERPRETER_RUNNING'):
        env = os.environ.copy()
        interpreter = resolve_interpreter(options.python)
        if interpreter == sys.executable:
            logger.warn('Already using interpreter %s' % interpreter)
        else:
            logger.notify('Running virtualenv with interpreter %s' % interpreter)
            env['VIRTUALENV_INTERPRETER_RUNNING'] = 'true'
            file = __file__
            if file.endswith('.pyc'):
                file = file[:-1]
            popen = subprocess.Popen([interpreter, file] + sys.argv[1:], env=env)
            raise SystemExit(popen.wait())

    # Force --distribute on Python 3, since setuptools is not available.
    if majver > 2:
        options.use_distribute = True

    if os.environ.get('PYTHONDONTWRITEBYTECODE') and not options.use_distribute:
        print(
            "The PYTHONDONTWRITEBYTECODE environment variable is "
            "not compatible with setuptools. Either use --distribute "
            "or unset PYTHONDONTWRITEBYTECODE.")
        sys.exit(2)
    if not args:
        print('You must provide a DEST_DIR')
        parser.print_help()
        sys.exit(2)
    if len(args) > 1:
        print('There must be only one argument: DEST_DIR (you gave %s)' % (
            ' '.join(args)))
        parser.print_help()
        sys.exit(2)

    home_dir = args[0]

    if os.environ.get('WORKING_ENV'):
        logger.fatal('ERROR: you cannot run virtualenv while in a workingenv')
        logger.fatal('Please deactivate your workingenv, then re-run this script')
        sys.exit(3)

    if 'PYTHONHOME' in os.environ:
        logger.warn('PYTHONHOME is set.  You *must* activate the virtualenv before using it')
        del os.environ['PYTHONHOME']

    if options.relocatable:
        make_environment_relocatable(home_dir)
        return

    create_environment(home_dir,
                       site_packages=options.system_site_packages,
                       clear=options.clear,
                       unzip_setuptools=options.unzip_setuptools,
                       use_distribute=options.use_distribute,
                       prompt=options.prompt,
                       search_dirs=options.search_dirs,
                       never_download=options.never_download,
                       no_setuptools=options.no_setuptools,
                       no_pip=options.no_pip)
    if 'after_install' in globals():
        after_install(options, home_dir)

def call_subprocess(cmd, show_stdout=True,
                    filter_stdout=None, cwd=None,
                    raise_on_returncode=True, extra_env=None,
                    remove_from_env=None):
    cmd_parts = []
    for part in cmd:
        if len(part) > 45:
            part = part[:20]+"..."+part[-20:]
        if ' ' in part or '\n' in part or '"' in part or "'" in part:
            part = '"%s"' % part.replace('"', '\\"')
        if hasattr(part, 'decode'):
            try:
                part = part.decode(sys.getdefaultencoding())
            except UnicodeDecodeError:
                part = part.decode(sys.getfilesystemencoding())
        cmd_parts.append(part)
    cmd_desc = ' '.join(cmd_parts)
    if show_stdout:
        stdout = None
    else:
        stdout = subprocess.PIPE
    logger.debug("Running command %s" % cmd_desc)
    if extra_env or remove_from_env:
        env = os.environ.copy()
        if extra_env:
            env.update(extra_env)
        if remove_from_env:
            for varname in remove_from_env:
                env.pop(varname, None)
    else:
        env = None
    try:
        proc = subprocess.Popen(
            cmd, stderr=subprocess.STDOUT, stdin=None, stdout=stdout,
            cwd=cwd, env=env)
    except Exception:
        e = sys.exc_info()[1]
        logger.fatal(
            "Error %s while executing command %s" % (e, cmd_desc))
        raise
    all_output = []
    if stdout is not None:
        stdout = proc.stdout
        encoding = sys.getdefaultencoding()
        fs_encoding = sys.getfilesystemencoding()
        while 1:
            line = stdout.readline()
            try:
                line = line.decode(encoding)
            except UnicodeDecodeError:
                line = line.decode(fs_encoding)
            if not line:
                break
            line = line.rstrip()
            all_output.append(line)
            if filter_stdout:
                level = filter_stdout(line)
                if isinstance(level, tuple):
                    level, line = level
                logger.log(level, line)
                if not logger.stdout_level_matches(level):
                    logger.show_progress()
            else:
                logger.info(line)
    else:
        proc.communicate()
    proc.wait()
    if proc.returncode:
        if raise_on_returncode:
            if all_output:
                logger.notify('Complete output from command %s:' % cmd_desc)
                logger.notify('\n'.join(all_output) + '\n----------------------------------------')
            raise OSError(
                "Command %s failed with error code %s"
                % (cmd_desc, proc.returncode))
        else:
            logger.warn(
                "Command %s had error code %s"
                % (cmd_desc, proc.returncode))


def create_environment(home_dir, site_packages=False, clear=False,
                       unzip_setuptools=False, use_distribute=False,
                       prompt=None, search_dirs=None, never_download=False,
                       no_setuptools=False, no_pip=False):
    """
    Creates a new environment in ``home_dir``.

    If ``site_packages`` is true, then the global ``site-packages/``
    directory will be on the path.

    If ``clear`` is true (default False) then the environment will
    first be cleared.
    """
    home_dir, lib_dir, inc_dir, bin_dir = path_locations(home_dir)

    py_executable = os.path.abspath(install_python(
        home_dir, lib_dir, inc_dir, bin_dir,
        site_packages=site_packages, clear=clear))

    install_distutils(home_dir)

    if not no_setuptools:
        if use_distribute:
            install_distribute(py_executable, unzip=unzip_setuptools,
                               search_dirs=search_dirs, never_download=never_download)
        else:
            install_setuptools(py_executable, unzip=unzip_setuptools,
                               search_dirs=search_dirs, never_download=never_download)

        if not no_pip:
            install_pip(py_executable, search_dirs=search_dirs, never_download=never_download)

    install_activate(home_dir, bin_dir, prompt)

def is_executable_file(fpath):
    return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

def path_locations(home_dir):
    """Return the path locations for the environment (where libraries are,
    where scripts go, etc)"""
    # XXX: We'd use distutils.sysconfig.get_python_inc/lib but its
    # prefix arg is broken: http://bugs.python.org/issue3386
    if is_win:
        # Windows has lots of problems with executables with spaces in
        # the name; this function will remove them (using the ~1
        # format):
        mkdir(home_dir)
        if ' ' in home_dir:
            import ctypes
            GetShortPathName = ctypes.windll.kernel32.GetShortPathNameW
            size = max(len(home_dir)+1, 256)
            buf = ctypes.create_unicode_buffer(size)
            try:
                u = unicode
            except NameError:
                u = str
            ret = GetShortPathName(u(home_dir), buf, size)
            if not ret:
                print('Error: the path "%s" has a space in it' % home_dir)
                print('We could not determine the short pathname for it.')
                print('Exiting.')
                sys.exit(3)
            home_dir = str(buf.value)
        lib_dir = join(home_dir, 'Lib')
        inc_dir = join(home_dir, 'Include')
        bin_dir = join(home_dir, 'Scripts')
    if is_jython:
        lib_dir = join(home_dir, 'Lib')
        inc_dir = join(home_dir, 'Include')
        bin_dir = join(home_dir, 'bin')
    elif is_pypy:
        lib_dir = home_dir
        inc_dir = join(home_dir, 'include')
        bin_dir = join(home_dir, 'bin')
    elif not is_win:
        lib_dir = join(home_dir, 'lib', py_version)
        multiarch_exec = '/usr/bin/multiarch-platform'
        if is_executable_file(multiarch_exec):
            # In Mageia (2) and Mandriva distros the include dir must be like:
            # virtualenv/include/multiarch-x86_64-linux/python2.7
            # instead of being virtualenv/include/python2.7
            p = subprocess.Popen(multiarch_exec, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = p.communicate()
            # stdout.strip is needed to remove newline character
            inc_dir = join(home_dir, 'include', stdout.strip(), py_version + abiflags)
        else:
            inc_dir = join(home_dir, 'include', py_version + abiflags)
        bin_dir = join(home_dir, 'bin')
    return home_dir, lib_dir, inc_dir, bin_dir


def change_prefix(filename, dst_prefix):
    prefixes = [sys.prefix]

    if is_darwin:
        prefixes.extend((
            os.path.join("/Library/Python", sys.version[:3], "site-packages"),
            os.path.join(sys.prefix, "Extras", "lib", "python"),
            os.path.join("~", "Library", "Python", sys.version[:3], "site-packages"),
            # Python 2.6 no-frameworks
            os.path.join("~", ".local", "lib","python", sys.version[:3], "site-packages"),
            # System Python 2.7 on OSX Mountain Lion
            os.path.join("~", "Library", "Python", sys.version[:3], "lib", "python", "site-packages")))

    if hasattr(sys, 'real_prefix'):
        prefixes.append(sys.real_prefix)
    if hasattr(sys, 'base_prefix'):
        prefixes.append(sys.base_prefix)
    prefixes = list(map(os.path.expanduser, prefixes))
    prefixes = list(map(os.path.abspath, prefixes))
    # Check longer prefixes first so we don't split in the middle of a filename
    prefixes = sorted(prefixes, key=len, reverse=True)
    filename = os.path.abspath(filename)
    for src_prefix in prefixes:
        if filename.startswith(src_prefix):
            _, relpath = filename.split(src_prefix, 1)
            if src_prefix != os.sep: # sys.prefix == "/"
                assert relpath[0] == os.sep
                relpath = relpath[1:]
            return join(dst_prefix, relpath)
    assert False, "Filename %s does not start with any of these prefixes: %s" % \
        (filename, prefixes)

def copy_required_modules(dst_prefix):
    import imp
    # If we are running under -p, we need to remove the current
    # directory from sys.path temporarily here, so that we
    # definitely get the modules from the site directory of
    # the interpreter we are running under, not the one
    # virtualenv.py is installed under (which might lead to py2/py3
    # incompatibility issues)
    _prev_sys_path = sys.path
    if os.environ.get('VIRTUALENV_INTERPRETER_RUNNING'):
        sys.path = sys.path[1:]
    try:
        for modname in REQUIRED_MODULES:
            if modname in sys.builtin_module_names:
                logger.info("Ignoring built-in bootstrap module: %s" % modname)
                continue
            try:
                f, filename, _ = imp.find_module(modname)
            except ImportError:
                logger.info("Cannot import bootstrap module: %s" % modname)
            else:
                if f is not None:
                    f.close()
                # special-case custom readline.so on OS X, but not for pypy:
                if modname == 'readline' and sys.platform == 'darwin' and not (
                        is_pypy or filename.endswith(join('lib-dynload', 'readline.so'))):
                    dst_filename = join(dst_prefix, 'lib', 'python%s' % sys.version[:3], 'readline.so')
                else:
                    dst_filename = change_prefix(filename, dst_prefix)
                copyfile(filename, dst_filename)
                if filename.endswith('.pyc'):
                    pyfile = filename[:-1]
                    if os.path.exists(pyfile):
                        copyfile(pyfile, dst_filename[:-1])
    finally:
        sys.path = _prev_sys_path


def subst_path(prefix_path, prefix, home_dir):
    prefix_path = os.path.normpath(prefix_path)
    prefix = os.path.normpath(prefix)
    home_dir = os.path.normpath(home_dir)
    if not prefix_path.startswith(prefix):
        logger.warn('Path not in prefix %r %r', prefix_path, prefix)
        return
    return prefix_path.replace(prefix, home_dir, 1)


def install_python(home_dir, lib_dir, inc_dir, bin_dir, site_packages, clear):
    """Install just the base environment, no distutils patches etc"""
    if sys.executable.startswith(bin_dir):
        print('Please use the *system* python to run this script')
        return

    if clear:
        rmtree(lib_dir)
        ## FIXME: why not delete it?
        ## Maybe it should delete everything with #!/path/to/venv/python in it
        logger.notify('Not deleting %s', bin_dir)

    if hasattr(sys, 'real_prefix'):
        logger.notify('Using real prefix %r' % sys.real_prefix)
        prefix = sys.real_prefix
    elif hasattr(sys, 'base_prefix'):
        logger.notify('Using base prefix %r' % sys.base_prefix)
        prefix = sys.base_prefix
    else:
        prefix = sys.prefix
    mkdir(lib_dir)
    fix_lib64(lib_dir)
    stdlib_dirs = [os.path.dirname(os.__file__)]
    if is_win:
        stdlib_dirs.append(join(os.path.dirname(stdlib_dirs[0]), 'DLLs'))
    elif is_darwin:
        stdlib_dirs.append(join(stdlib_dirs[0], 'site-packages'))
    if hasattr(os, 'symlink'):
        logger.info('Symlinking Python bootstrap modules')
    else:
        logger.info('Copying Python bootstrap modules')
    logger.indent += 2
    try:
        # copy required files...
        for stdlib_dir in stdlib_dirs:
            if not os.path.isdir(stdlib_dir):
                continue
            for fn in os.listdir(stdlib_dir):
                bn = os.path.splitext(fn)[0]
                if fn != 'site-packages' and bn in REQUIRED_FILES:
                    copyfile(join(stdlib_dir, fn), join(lib_dir, fn))
        # ...and modules
        copy_required_modules(home_dir)
    finally:
        logger.indent -= 2
    mkdir(join(lib_dir, 'site-packages'))
    import site
    site_filename = site.__file__
    if site_filename.endswith('.pyc'):
        site_filename = site_filename[:-1]
    elif site_filename.endswith('$py.class'):
        site_filename = site_filename.replace('$py.class', '.py')
    site_filename_dst = change_prefix(site_filename, home_dir)
    site_dir = os.path.dirname(site_filename_dst)
    writefile(site_filename_dst, SITE_PY)
    writefile(join(site_dir, 'orig-prefix.txt'), prefix)
    site_packages_filename = join(site_dir, 'no-global-site-packages.txt')
    if not site_packages:
        writefile(site_packages_filename, '')

    if is_pypy or is_win:
        stdinc_dir = join(prefix, 'include')
    else:
        stdinc_dir = join(prefix, 'include', py_version + abiflags)
    if os.path.exists(stdinc_dir):
        copyfile(stdinc_dir, inc_dir)
    else:
        logger.debug('No include dir %s' % stdinc_dir)

    platinc_dir = distutils.sysconfig.get_python_inc(plat_specific=1)
    if platinc_dir != stdinc_dir:
        platinc_dest = distutils.sysconfig.get_python_inc(
            plat_specific=1, prefix=home_dir)
        if platinc_dir == platinc_dest:
            # Do platinc_dest manually due to a CPython bug;
            # not http://bugs.python.org/issue3386 but a close cousin
            platinc_dest = subst_path(platinc_dir, prefix, home_dir)
        if platinc_dest:
            # PyPy's stdinc_dir and prefix are relative to the original binary
            # (traversing virtualenvs), whereas the platinc_dir is relative to
            # the inner virtualenv and ignores the prefix argument.
            # This seems more evolved than designed.
            copyfile(platinc_dir, platinc_dest)

    # pypy never uses exec_prefix, just ignore it
    if sys.exec_prefix != prefix and not is_pypy:
        if is_win:
            exec_dir = join(sys.exec_prefix, 'lib')
        elif is_jython:
            exec_dir = join(sys.exec_prefix, 'Lib')
        else:
            exec_dir = join(sys.exec_prefix, 'lib', py_version)
        for fn in os.listdir(exec_dir):
            copyfile(join(exec_dir, fn), join(lib_dir, fn))

    if is_jython:
        # Jython has either jython-dev.jar and javalib/ dir, or just
        # jython.jar
        for name in 'jython-dev.jar', 'javalib', 'jython.jar':
            src = join(prefix, name)
            if os.path.exists(src):
                copyfile(src, join(home_dir, name))
        # XXX: registry should always exist after Jython 2.5rc1
        src = join(prefix, 'registry')
        if os.path.exists(src):
            copyfile(src, join(home_dir, 'registry'), symlink=False)
        copyfile(join(prefix, 'cachedir'), join(home_dir, 'cachedir'),
                 symlink=False)

    mkdir(bin_dir)
    py_executable = join(bin_dir, os.path.basename(sys.executable))
    if 'Python.framework' in prefix:
        # OS X framework builds cause validation to break
        # https://github.com/pypa/virtualenv/issues/322
        if os.environ.get('__PYVENV_LAUNCHER__'):
          os.unsetenv('__PYVENV_LAUNCHER__')
        if re.search(r'/Python(?:-32|-64)*$', py_executable):
            # The name of the python executable is not quite what
            # we want, rename it.
            py_executable = os.path.join(
                    os.path.dirname(py_executable), 'python')

    logger.notify('New %s executable in %s', expected_exe, py_executable)
    pcbuild_dir = os.path.dirname(sys.executable)
    pyd_pth = os.path.join(lib_dir, 'site-packages', 'virtualenv_builddir_pyd.pth')
    if is_win and os.path.exists(os.path.join(pcbuild_dir, 'build.bat')):
        logger.notify('Detected python running from build directory %s', pcbuild_dir)
        logger.notify('Writing .pth file linking to build directory for *.pyd files')
        writefile(pyd_pth, pcbuild_dir)
    else:
        pcbuild_dir = None
        if os.path.exists(pyd_pth):
            logger.info('Deleting %s (not Windows env or not build directory python)' % pyd_pth)
            os.unlink(pyd_pth)

    if sys.executable != py_executable:
        ## FIXME: could I just hard link?
        executable = sys.executable
        shutil.copyfile(executable, py_executable)
        make_exe(py_executable)
        if is_win or is_cygwin:
            pythonw = os.path.join(os.path.dirname(sys.executable), 'pythonw.exe')
            if os.path.exists(pythonw):
                logger.info('Also created pythonw.exe')
                shutil.copyfile(pythonw, os.path.join(os.path.dirname(py_executable), 'pythonw.exe'))
            python_d = os.path.join(os.path.dirname(sys.executable), 'python_d.exe')
            python_d_dest = os.path.join(os.path.dirname(py_executable), 'python_d.exe')
            if os.path.exists(python_d):
                logger.info('Also created python_d.exe')
                shutil.copyfile(python_d, python_d_dest)
            elif os.path.exists(python_d_dest):
                logger.info('Removed python_d.exe as it is no longer at the source')
                os.unlink(python_d_dest)
            # we need to copy the DLL to enforce that windows will load the correct one.
            # may not exist if we are cygwin.
            py_executable_dll = 'python%s%s.dll' % (
                sys.version_info[0], sys.version_info[1])
            py_executable_dll_d = 'python%s%s_d.dll' % (
                sys.version_info[0], sys.version_info[1])
            pythondll = os.path.join(os.path.dirname(sys.executable), py_executable_dll)
            pythondll_d = os.path.join(os.path.dirname(sys.executable), py_executable_dll_d)
            pythondll_d_dest = os.path.join(os.path.dirname(py_executable), py_executable_dll_d)
            if os.path.exists(pythondll):
                logger.info('Also created %s' % py_executable_dll)
                shutil.copyfile(pythondll, os.path.join(os.path.dirname(py_executable), py_executable_dll))
            if os.path.exists(pythondll_d):
                logger.info('Also created %s' % py_executable_dll_d)
                shutil.copyfile(pythondll_d, pythondll_d_dest)
            elif os.path.exists(pythondll_d_dest):
                logger.info('Removed %s as the source does not exist' % pythondll_d_dest)
                os.unlink(pythondll_d_dest)
        if is_pypy:
            # make a symlink python --> pypy-c
            python_executable = os.path.join(os.path.dirname(py_executable), 'python')
            if sys.platform in ('win32', 'cygwin'):
                python_executable += '.exe'
            logger.info('Also created executable %s' % python_executable)
            copyfile(py_executable, python_executable)

            if is_win:
                for name in 'libexpat.dll', 'libpypy.dll', 'libpypy-c.dll', 'libeay32.dll', 'ssleay32.dll', 'sqlite.dll':
                    src = join(prefix, name)
                    if os.path.exists(src):
                        copyfile(src, join(bin_dir, name))

    if os.path.splitext(os.path.basename(py_executable))[0] != expected_exe:
        secondary_exe = os.path.join(os.path.dirname(py_executable),
                                     expected_exe)
        py_executable_ext = os.path.splitext(py_executable)[1]
        if py_executable_ext == '.exe':
            # python2.4 gives an extension of '.4' :P
            secondary_exe += py_executable_ext
        if os.path.exists(secondary_exe):
            logger.warn('Not overwriting existing %s script %s (you must use %s)'
                        % (expected_exe, secondary_exe, py_executable))
        else:
            logger.notify('Also creating executable in %s' % secondary_exe)
            shutil.copyfile(sys.executable, secondary_exe)
            make_exe(secondary_exe)

    if '.framework' in prefix:
        if 'Python.framework' in prefix:
            logger.debug('MacOSX Python framework detected')
            # Make sure we use the the embedded interpreter inside
            # the framework, even if sys.executable points to
            # the stub executable in ${sys.prefix}/bin
            # See http://groups.google.com/group/python-virtualenv/
            #                              browse_thread/thread/17cab2f85da75951
            original_python = os.path.join(
                prefix, 'Resources/Python.app/Contents/MacOS/Python')
        if 'EPD' in prefix:
            logger.debug('EPD framework detected')
            original_python = os.path.join(prefix, 'bin/python')
        shutil.copy(original_python, py_executable)

        # Copy the framework's dylib into the virtual
        # environment
        virtual_lib = os.path.join(home_dir, '.Python')

        if os.path.exists(virtual_lib):
            os.unlink(virtual_lib)
        copyfile(
            os.path.join(prefix, 'Python'),
            virtual_lib)

        # And then change the install_name of the copied python executable
        try:
            mach_o_change(py_executable,
                          os.path.join(prefix, 'Python'),
                          '@executable_path/../.Python')
        except:
            e = sys.exc_info()[1]
            logger.warn("Could not call mach_o_change: %s. "
                        "Trying to call install_name_tool instead." % e)
            try:
                call_subprocess(
                    ["install_name_tool", "-change",
                     os.path.join(prefix, 'Python'),
                     '@executable_path/../.Python',
                     py_executable])
            except:
                logger.fatal("Could not call install_name_tool -- you must "
                             "have Apple's development tools installed")
                raise

    if not is_win:
        # Ensure that 'python', 'pythonX' and 'pythonX.Y' all exist
        py_exe_version_major = 'python%s' % sys.version_info[0]
        py_exe_version_major_minor = 'python%s.%s' % (
            sys.version_info[0], sys.version_info[1])
        py_exe_no_version = 'python'
        required_symlinks = [ py_exe_no_version, py_exe_version_major,
                         py_exe_version_major_minor ]

        py_executable_base = os.path.basename(py_executable)

        if py_executable_base in required_symlinks:
            # Don't try to symlink to yourself.
            required_symlinks.remove(py_executable_base)

        for pth in required_symlinks:
            full_pth = join(bin_dir, pth)
            if os.path.exists(full_pth):
                os.unlink(full_pth)
            os.symlink(py_executable_base, full_pth)

    if is_win and ' ' in py_executable:
        # There's a bug with subprocess on Windows when using a first
        # argument that has a space in it.  Instead we have to quote
        # the value:
        py_executable = '"%s"' % py_executable
    # NOTE: keep this check as one line, cmd.exe doesn't cope with line breaks
    cmd = [py_executable, '-c', 'import sys;out=sys.stdout;'
        'getattr(out, "buffer", out).write(sys.prefix.encode("utf-8"))']
    logger.info('Testing executable with %s %s "%s"' % tuple(cmd))
    try:
        proc = subprocess.Popen(cmd,
                            stdout=subprocess.PIPE)
        proc_stdout, proc_stderr = proc.communicate()
    except OSError:
        e = sys.exc_info()[1]
        if e.errno == errno.EACCES:
            logger.fatal('ERROR: The executable %s could not be run: %s' % (py_executable, e))
            sys.exit(100)
        else:
            raise e

    proc_stdout = proc_stdout.strip().decode("utf-8")
    proc_stdout = os.path.normcase(os.path.abspath(proc_stdout))
    norm_home_dir = os.path.normcase(os.path.abspath(home_dir))
    if hasattr(norm_home_dir, 'decode'):
        norm_home_dir = norm_home_dir.decode(sys.getfilesystemencoding())
    if proc_stdout != norm_home_dir:
        logger.fatal(
            'ERROR: The executable %s is not functioning' % py_executable)
        logger.fatal(
            'ERROR: It thinks sys.prefix is %r (should be %r)'
            % (proc_stdout, norm_home_dir))
        logger.fatal(
            'ERROR: virtualenv is not compatible with this system or executable')
        if is_win:
            logger.fatal(
                'Note: some Windows users have reported this error when they '
                'installed Python for "Only this user" or have multiple '
                'versions of Python installed. Copying the appropriate '
                'PythonXX.dll to the virtualenv Scripts/ directory may fix '
                'this problem.')
        sys.exit(100)
    else:
        logger.info('Got sys.prefix result: %r' % proc_stdout)

    pydistutils = os.path.expanduser('~/.pydistutils.cfg')
    if os.path.exists(pydistutils):
        logger.notify('Please make sure you remove any previous custom paths from '
                      'your %s file.' % pydistutils)
    ## FIXME: really this should be calculated earlier

    fix_local_scheme(home_dir)

    if site_packages:
        if os.path.exists(site_packages_filename):
            logger.info('Deleting %s' % site_packages_filename)
            os.unlink(site_packages_filename)

    return py_executable


def install_activate(home_dir, bin_dir, prompt=None):
    home_dir = os.path.abspath(home_dir)
    if is_win or is_jython and os._name == 'nt':
        files = {
            'activate.bat': ACTIVATE_BAT,
            'deactivate.bat': DEACTIVATE_BAT,
            'activate.ps1': ACTIVATE_PS,
        }

        # MSYS needs paths of the form /c/path/to/file
        drive, tail = os.path.splitdrive(home_dir.replace(os.sep, '/'))
        home_dir_msys = (drive and "/%s%s" or "%s%s") % (drive[:1], tail)

        # Run-time conditional enables (basic) Cygwin compatibility
        home_dir_sh = ("""$(if [ "$OSTYPE" "==" "cygwin" ]; then cygpath -u '%s'; else echo '%s'; fi;)""" %
                       (home_dir, home_dir_msys))
        files['activate'] = ACTIVATE_SH.replace('__VIRTUAL_ENV__', home_dir_sh)

    else:
        files = {'activate': ACTIVATE_SH}

        # suppling activate.fish in addition to, not instead of, the
        # bash script support.
        files['activate.fish'] = ACTIVATE_FISH

        # same for csh/tcsh support...
        files['activate.csh'] = ACTIVATE_CSH

    files['activate_this.py'] = ACTIVATE_THIS
    if hasattr(home_dir, 'decode'):
        home_dir = home_dir.decode(sys.getfilesystemencoding())
    vname = os.path.basename(home_dir)
    for name, content in files.items():
        content = content.replace('__VIRTUAL_PROMPT__', prompt or '')
        content = content.replace('__VIRTUAL_WINPROMPT__', prompt or '(%s)' % vname)
        content = content.replace('__VIRTUAL_ENV__', home_dir)
        content = content.replace('__VIRTUAL_NAME__', vname)
        content = content.replace('__BIN_NAME__', os.path.basename(bin_dir))
        writefile(os.path.join(bin_dir, name), content)

def install_distutils(home_dir):
    distutils_path = change_prefix(distutils.__path__[0], home_dir)
    mkdir(distutils_path)
    ## FIXME: maybe this prefix setting should only be put in place if
    ## there's a local distutils.cfg with a prefix setting?
    home_dir = os.path.abspath(home_dir)
    ## FIXME: this is breaking things, removing for now:
    #distutils_cfg = DISTUTILS_CFG + "\n[install]\nprefix=%s\n" % home_dir
    writefile(os.path.join(distutils_path, '__init__.py'), DISTUTILS_INIT)
    writefile(os.path.join(distutils_path, 'distutils.cfg'), DISTUTILS_CFG, overwrite=False)

def fix_local_scheme(home_dir):
    """
    Platforms that use the "posix_local" install scheme (like Ubuntu with
    Python 2.7) need to be given an additional "local" location, sigh.
    """
    try:
        import sysconfig
    except ImportError:
        pass
    else:
        if sysconfig._get_default_scheme() == 'posix_local':
            local_path = os.path.join(home_dir, 'local')
            if not os.path.exists(local_path):
                os.mkdir(local_path)
                for subdir_name in os.listdir(home_dir):
                    if subdir_name == 'local':
                        continue
                    os.symlink(os.path.abspath(os.path.join(home_dir, subdir_name)), \
                                                            os.path.join(local_path, subdir_name))

def fix_lib64(lib_dir):
    """
    Some platforms (particularly Gentoo on x64) put things in lib64/pythonX.Y
    instead of lib/pythonX.Y.  If this is such a platform we'll just create a
    symlink so lib64 points to lib
    """
    if [p for p in distutils.sysconfig.get_config_vars().values()
        if isinstance(p, basestring) and 'lib64' in p]:
        logger.debug('This system uses lib64; symlinking lib64 to lib')
        assert os.path.basename(lib_dir) == 'python%s' % sys.version[:3], (
            "Unexpected python lib dir: %r" % lib_dir)
        lib_parent = os.path.dirname(lib_dir)
        top_level = os.path.dirname(lib_parent)
        lib_dir = os.path.join(top_level, 'lib')
        lib64_link = os.path.join(top_level, 'lib64')
        assert os.path.basename(lib_parent) == 'lib', (
            "Unexpected parent dir: %r" % lib_parent)
        if os.path.lexists(lib64_link):
            return
        os.symlink('lib', lib64_link)

def resolve_interpreter(exe):
    """
    If the executable given isn't an absolute path, search $PATH for the interpreter
    """
    if os.path.abspath(exe) != exe:
        paths = os.environ.get('PATH', '').split(os.pathsep)
        for path in paths:
            if os.path.exists(os.path.join(path, exe)):
                exe = os.path.join(path, exe)
                break
    if not os.path.exists(exe):
        logger.fatal('The executable %s (from --python=%s) does not exist' % (exe, exe))
        raise SystemExit(3)
    if not is_executable(exe):
        logger.fatal('The executable %s (from --python=%s) is not executable' % (exe, exe))
        raise SystemExit(3)
    return exe

def is_executable(exe):
    """Checks a file is executable"""
    return os.access(exe, os.X_OK)

############################################################
## Relocating the environment:

def make_environment_relocatable(home_dir):
    """
    Makes the already-existing environment use relative paths, and takes out
    the #!-based environment selection in scripts.
    """
    home_dir, lib_dir, inc_dir, bin_dir = path_locations(home_dir)
    activate_this = os.path.join(bin_dir, 'activate_this.py')
    if not os.path.exists(activate_this):
        logger.fatal(
            'The environment doesn\'t have a file %s -- please re-run virtualenv '
            'on this environment to update it' % activate_this)
    fixup_scripts(home_dir)
    fixup_pth_and_egg_link(home_dir)
    ## FIXME: need to fix up distutils.cfg

OK_ABS_SCRIPTS = ['python', 'python%s' % sys.version[:3],
                  'activate', 'activate.bat', 'activate_this.py']

def fixup_scripts(home_dir):
    # This is what we expect at the top of scripts:
    shebang = '#!%s/bin/python' % os.path.normcase(os.path.abspath(home_dir))
    # This is what we'll put:
    new_shebang = '#!/usr/bin/env python%s' % sys.version[:3]
    if is_win:
        bin_suffix = 'Scripts'
    else:
        bin_suffix = 'bin'
    bin_dir = os.path.join(home_dir, bin_suffix)
    home_dir, lib_dir, inc_dir, bin_dir = path_locations(home_dir)
    for filename in os.listdir(bin_dir):
        filename = os.path.join(bin_dir, filename)
        if not os.path.isfile(filename):
            # ignore subdirs, e.g. .svn ones.
            continue
        f = open(filename, 'rb')
        try:
            try:
                lines = f.read().decode('utf-8').splitlines()
            except UnicodeDecodeError:
                # This is probably a binary program instead
                # of a script, so just ignore it.
                continue
        finally:
            f.close()
        if not lines:
            logger.warn('Script %s is an empty file' % filename)
            continue
        if not lines[0].strip().startswith(shebang):
            if os.path.basename(filename) in OK_ABS_SCRIPTS:
                logger.debug('Cannot make script %s relative' % filename)
            elif lines[0].strip() == new_shebang:
                logger.info('Script %s has already been made relative' % filename)
            else:
                logger.warn('Script %s cannot be made relative (it\'s not a normal script that starts with %s)'
                            % (filename, shebang))
            continue
        logger.notify('Making script %s relative' % filename)
        script = relative_script([new_shebang] + lines[1:])
        f = open(filename, 'wb')
        f.write('\n'.join(script).encode('utf-8'))
        f.close()

def relative_script(lines):
    "Return a script that'll work in a relocatable environment."
    activate = "import os; activate_this=os.path.join(os.path.dirname(os.path.realpath(__file__)), 'activate_this.py'); execfile(activate_this, dict(__file__=activate_this)); del os, activate_this"
    # Find the last future statement in the script. If we insert the activation
    # line before a future statement, Python will raise a SyntaxError.
    activate_at = None
    for idx, line in reversed(list(enumerate(lines))):
        if line.split()[:3] == ['from', '__future__', 'import']:
            activate_at = idx + 1
            break
    if activate_at is None:
        # Activate after the shebang.
        activate_at = 1
    return lines[:activate_at] + ['', activate, ''] + lines[activate_at:]

def fixup_pth_and_egg_link(home_dir, sys_path=None):
    """Makes .pth and .egg-link files use relative paths"""
    home_dir = os.path.normcase(os.path.abspath(home_dir))
    if sys_path is None:
        sys_path = sys.path
    for path in sys_path:
        if not path:
            path = '.'
        if not os.path.isdir(path):
            continue
        path = os.path.normcase(os.path.abspath(path))
        if not path.startswith(home_dir):
            logger.debug('Skipping system (non-environment) directory %s' % path)
            continue
        for filename in os.listdir(path):
            filename = os.path.join(path, filename)
            if filename.endswith('.pth'):
                if not os.access(filename, os.W_OK):
                    logger.warn('Cannot write .pth file %s, skipping' % filename)
                else:
                    fixup_pth_file(filename)
            if filename.endswith('.egg-link'):
                if not os.access(filename, os.W_OK):
                    logger.warn('Cannot write .egg-link file %s, skipping' % filename)
                else:
                    fixup_egg_link(filename)

def fixup_pth_file(filename):
    lines = []
    prev_lines = []
    f = open(filename)
    prev_lines = f.readlines()
    f.close()
    for line in prev_lines:
        line = line.strip()
        if (not line or line.startswith('#') or line.startswith('import ')
            or os.path.abspath(line) != line):
            lines.append(line)
        else:
            new_value = make_relative_path(filename, line)
            if line != new_value:
                logger.debug('Rewriting path %s as %s (in %s)' % (line, new_value, filename))
            lines.append(new_value)
    if lines == prev_lines:
        logger.info('No changes to .pth file %s' % filename)
        return
    logger.notify('Making paths in .pth file %s relative' % filename)
    f = open(filename, 'w')
    f.write('\n'.join(lines) + '\n')
    f.close()

def fixup_egg_link(filename):
    f = open(filename)
    link = f.readline().strip()
    f.close()
    if os.path.abspath(link) != link:
        logger.debug('Link in %s already relative' % filename)
        return
    new_link = make_relative_path(filename, link)
    logger.notify('Rewriting link %s in %s as %s' % (link, filename, new_link))
    f = open(filename, 'w')
    f.write(new_link)
    f.close()

def make_relative_path(source, dest, dest_is_directory=True):
    """
    Make a filename relative, where the filename is dest, and it is
    being referred to from the filename source.

        >>> make_relative_path('/usr/share/something/a-file.pth',
        ...                    '/usr/share/another-place/src/Directory')
        '../another-place/src/Directory'
        >>> make_relative_path('/usr/share/something/a-file.pth',
        ...                    '/home/user/src/Directory')
        '../../../home/user/src/Directory'
        >>> make_relative_path('/usr/share/a-file.pth', '/usr/share/')
        './'
    """
    source = os.path.dirname(source)
    if not dest_is_directory:
        dest_filename = os.path.basename(dest)
        dest = os.path.dirname(dest)
    dest = os.path.normpath(os.path.abspath(dest))
    source = os.path.normpath(os.path.abspath(source))
    dest_parts = dest.strip(os.path.sep).split(os.path.sep)
    source_parts = source.strip(os.path.sep).split(os.path.sep)
    while dest_parts and source_parts and dest_parts[0] == source_parts[0]:
        dest_parts.pop(0)
        source_parts.pop(0)
    full_parts = ['..']*len(source_parts) + dest_parts
    if not dest_is_directory:
        full_parts.append(dest_filename)
    if not full_parts:
        # Special case for the current directory (otherwise it'd be '')
        return './'
    return os.path.sep.join(full_parts)



############################################################
## Bootstrap script creation:

def create_bootstrap_script(extra_text, python_version=''):
    """
    Creates a bootstrap script, which is like this script but with
    extend_parser, adjust_options, and after_install hooks.

    This returns a string that (written to disk of course) can be used
    as a bootstrap script with your own customizations.  The script
    will be the standard virtualenv.py script, with your extra text
    added (your extra text should be Python code).

    If you include these functions, they will be called:

    ``extend_parser(optparse_parser)``:
        You can add or remove options from the parser here.

    ``adjust_options(options, args)``:
        You can change options here, or change the args (if you accept
        different kinds of arguments, be sure you modify ``args`` so it is
        only ``[DEST_DIR]``).

    ``after_install(options, home_dir)``:

        After everything is installed, this function is called.  This
        is probably the function you are most likely to use.  An
        example would be::

            def after_install(options, home_dir):
                subprocess.call([join(home_dir, 'bin', 'easy_install'),
                                 'MyPackage'])
                subprocess.call([join(home_dir, 'bin', 'my-package-script'),
                                 'setup', home_dir])

        This example immediately installs a package, and runs a setup
        script from that package.

    If you provide something like ``python_version='2.5'`` then the
    script will start with ``#!/usr/bin/env python2.5`` instead of
    ``#!/usr/bin/env python``.  You can use this when the script must
    be run with a particular Python version.
    """
    filename = __file__
    if filename.endswith('.pyc'):
        filename = filename[:-1]
    f = codecs.open(filename, 'r', encoding='utf-8')
    content = f.read()
    f.close()
    py_exe = 'python%s' % python_version
    content = (('#!/usr/bin/env %s\n' % py_exe)
               + '## WARNING: This file is generated\n'
               + content)
    return content.replace('##EXT' 'END##', extra_text)

##EXTEND##

def convert(s):
    b = base64.b64decode(s.encode('ascii'))
    return zlib.decompress(b).decode('utf-8')

##file site.py
SITE_PY = convert("""
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
UM3ckC/Q8aP8VLy+mjYY5MxOtAdgjULwf2RtvCc=
""")

##file ez_setup.py
EZ_SETUP_PY = convert("""
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
qL7+C1AkCcw=
""")

##file distribute_from_egg.py
DISTRIBUTE_FROM_EGG_PY = convert("""
eJw9j8tqAzEMRfcG/4MgmxQyptkGusonZBmGoGTUGYFfWPKE6dfXTkM3gqt7rh47OKP3NMF3SQFW
LlrRU1zhybpAxoKBlIqcrNnBdRjQP3GTocYfzmNrrCPQPN9iwzpxSQfQhWBi0cL3qtRtYIG/4Mv0
KApY5hooqrOGQ05FQTaxptF9Fnx16Rq0XofjaE1XGXVxHIWK7j8P8EY/rHndLqQ1a0pe3COFgHFy
hLLdWkDbi/DeEpCjNb3u/zccT2Ob8gtnwVyI
""")

##file distribute_setup.py
DISTRIBUTE_SETUP_PY = convert("""
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
""")

##file activate.sh
ACTIVATE_SH = convert("""
eJytVVFvokAQfudXTLEPtTlLeo9tvMSmJpq02hSvl7u2wRUG2QR2DSxSe7n/frOACEVNLlceRHa+
nfl25pvZDswCnoDPQ4QoTRQsENIEPci4CsBMZBq7CAsuLOYqvmYKTTj3YxnBgiXBudGBjUzBZUJI
BXEqgCvweIyuCjeG4eF2F5x14bcB9KQiQQWrjSddI1/oQIx6SYYeoFjzWIoIhYI1izlbhJjkKO7D
M/QEmKfO9O7WeRo/zr4P7pyHwWxkwitcgwpQ5Ej96OX+PmiFwLeVjFUOrNYKaq1Nud3nR2n8nI2m
k9H0friPTGVsUdptaxGrTEfpNVFEskxpXtUkkCkl1UNF9cgLBkx48J4EXyALuBtAwNYIjF5kcmUU
abMKmMq1ULoiRbgsDEkTSsKSGFCJ6Z8vY/2xYiSacmtyAfCDdCNTVZoVF8vSTQOoEwSnOrngBkws
MYGMBMg8/bMBLSYKS7pYEXP0PqT+ZmBT0Xuy+Pplj5yn4aM9nk72JD8/Wi+Gr98sD9eWSMOwkapD
BbUv91XSvmyVkICt2tmXR4tWmrcUCsjWOpw87YidEC8i0gdTSOFhouJUNxR+4NYBG0MftoCTD9F7
2rTtxG3oPwY1b2HncYwhrlmj6Wq924xtGDWqfdNxap+OYxplEurnMVo9RWks+rH8qKEtx7kZT5zJ
4H7oOFclrN6uFe+d+nW2aIUsSgs/42EIPuOhXq+jEo3S6tX6w2ilNkDnIpHCWdEQhFgwj9pkk7FN
l/y5eQvRSIQ5+TrL05lewxWpt/Lbhes5cJF3mLET1MGhcKCF+40tNWnUulxrpojwDo2sObdje3Bz
N3QeHqf3D7OjEXMVV8LN3ZlvuzoWHqiUcNKHtwNd0IbvPGKYYM31nPKCgkUILw3KL+Y8l7aO1ArS
Ad37nIU0fCj5NE5gQCuC5sOSu+UdI2NeXg/lFkQIlFpdWVaWZRfvqGiirC9o6liJ9FXGYrSY9mI1
D/Ncozgn13vJvsznr7DnkJWXsyMH7e42ljdJ+aqNDF1bFnKWFLdj31xtaJYK6EXFgqmV/ymD/ROG
+n8O9H8f5vsGOWXsL1+1k3g=
""")

##file activate.fish
ACTIVATE_FISH = convert("""
eJyVVWFv2jAQ/c6vuBoqQVWC9nVSNVGVCaS2VC2rNLWVZZILWAs2s52wVvvxsyEJDrjbmgpK7PP5
3bt3d22YLbmGlGcIq1wbmCPkGhPYcLMEEsGciwGLDS+YwSjlekngLFVyBe73GXSXxqw/DwbuTS8x
yyKpFr1WG15lDjETQhpQuQBuIOEKY5O9tlppLqxHKSDByjVAPwEy+mXtCq5MzjIUBTCRgEKTKwFG
gpBqxTLYXgN2myspVigMaYF92tZSowGZJf4mFExxNs9Qb614CgZtmH0BpEOn11f0cXI/+za8pnfD
2ZjA1sg9zlV/8QvcMhxbNu0QwgYokn/d+n02nt6Opzcjcnx1vXcIoN74O4ymWQXmHURfJw9jenc/
vbmb0enj6P5+cuVhqlKm3S0u2XRtRbA2QQAhV7VhBF0rsgUX9Ur1rBUXJgVSy8O751k8mzY5OrKH
RW3eaQhYGTr8hrXO59ALhxQ83mCsDLAid3T72CCSdJhaFE+fXgicXAARUiR2WeVO37gH3oYHzFKo
9k7CaPZ1UeNwH1tWuXA4uFKYYcEa8vaKqXl7q1UpygMPhFLvlVKyNzsSM3S2km7UBOl4xweUXk5u
6e3wZmQ9leY1XE/Ili670tr9g/5POBBpGIJXCCF79L1siarl/dbESa8mD8PL61GpzqpzuMS7tqeB
1YkALrRBloBMbR9yLcVx7frQAgUqR7NZIuzkEu110gbNit1enNs82Rx5utq7Z3prU78HFRgulqNC
OTwbqJa9vkJFclQgZSjbKeBgSsUtCtt9D8OwAbIVJuewQdfvQRaoFE9wd1TmCuRG7OgJ1bVXGHc7
z5WDL/WW36v2oi37CyVBak61+yPBA9C1qqGxzKQqZ0oPuocU9hpud0PIp8sDHkXR1HKkNlzjuUWA
a0enFUyzOWZA4yXGP+ZMI3Tdt2OuqU/SO4q64526cPE0A7ZyW2PMbWZiZ5HamIZ2RcCKLXhcDl2b
vXL+eccQoRzem80mekPDEiyiWK4GWqZmwxQOmPM0eIfgp1P9cqrBsewR2p/DPMtt+pfcYM+Ls2uh
hALufTAdmGl8B1H3VPd2af8fQAc4PgqjlIBL9cGQqNpXaAwe3LrtVn8AkZTUxg==
""")

##file activate.csh
ACTIVATE_CSH = convert("""
eJx9VG1P2zAQ/u5fcYQKNgTNPtN1WxlIQ4KCUEGaxuQ6yYVYSuzKdhqVX7+zk3bpy5YPUXL3PPfc
ne98DLNCWshliVDV1kGCUFvMoJGugMjq2qQIiVSxSJ1cCofD1BYRnOVGV0CfZ0N2DD91DalQSjsw
tQLpIJMGU1euvPe7QeJlkKzgWixlhnAt4aoUVsLnLBiy5NtbJWQ5THX1ZciYKKWwkOFaE04dUm6D
r/zh7pq/3D7Nnid3/HEy+wFHY/gEJydg0aFaQrBFgz1c5DG1IhTs+UZgsBC2GMFBlaeH+8dZXwcW
VPvCjXdlAvCfQsE7al0+07XjZvrSCUevR5dnkVeKlFYZmUztG4BdzL2u9KyLVabTU0bdfg7a0hgs
cSmUg6UwUiQl2iHrcbcVGNvPCiLOe7+cRwG13z9qRGgx2z6DHjfm/Op2yqeT+xvOLzs0PTKHDz2V
tkckFHoQfQRXoGJAj9el0FyJCmEMhzgMS4sB7KPOE2ExoLcSieYwDvR+cP8cg11gKkVJc2wRcm1g
QhYFlXiTaTfO2ki0fQoiFM4tLuO4aZrhOzqR4dIPcWx17hphMBY+Srwh7RTyN83XOWkcSPh1Pg/k
TXX/jbJTbMtUmcxZ+/bbqOsy82suFQg/BhdSOTRhMNBHlUarCpU7JzBhmkKmRejKOQzayQe6MWoa
n1wqWmuh6LZAaHxcdeqIlVLhIBJdO9/kbl0It2oEXQj+eGjJOuvOIR/YGRqvFhttUB2XTvLXYN2H
37CBdbW2W7j2r2+VsCn0doVWcFG1/4y1VwBjfwAyoZhD
""")

##file activate.bat
ACTIVATE_BAT = convert("""
eJx9UdEKgjAUfW6wfxjiIH+hEDKUFHSKLCMI7kNOEkIf9P9pTJ3OLJ/03HPPPed4Es9XS9qqwqgT
PbGKKOdXL4aAFS7A4gvAwgijuiKlqOpGlATS2NeMLE+TjJM9RkQ+SmqAXLrBo1LLIeLdiWlD6jZt
r7VNubWkndkXaxg5GO3UaOOKS6drO3luDDiO5my3iA0YAKGzPRV1ack8cOdhysI0CYzIPzjSiH5X
0QcvC8Lfaj0emsVKYF2rhL5L3fCkVjV76kShi59NHwDniAHzkgDgqBcwOgTMx+gDQQqXCw==
""")

##file deactivate.bat
DEACTIVATE_BAT = convert("""
eJxzSE3OyFfIT0vj4ipOLVEI8wwKCXX0iXf1C7Pl4spMU0hJTcvMS01RiPf3cYmHyQYE+fsGhCho
cCkAAUibEkTEVhWLMlUlLk6QGixStlyaeCyJDPHw9/Pw93VFsQguim4ZXAJoIUw5DhX47XUM8UCx
EchHtwsohN1bILUgw61c/Vy4AJYPYm4=
""")

##file activate.ps1
ACTIVATE_PS = convert("""
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
QastYw==
""")

##file distutils-init.py
DISTUTILS_INIT = convert("""
eJytV1uL4zYUfvevOE0ottuMW9q3gVDa3aUMXXbLMlDKMBiNrSTqOJKRlMxkf33PkXyRbGe7Dw2E
UXTu37lpxLFV2oIyifAncxmOL0xLIfcG+gv80x9VW6maw7o/CANSWWBwFtqeWMPlGY6qPjV8A0bB
C4eKSTgZ5LRgFeyErMEeOBhbN+Ipgeizhjtnhkn7DdyjuNLPoCS0l/ayQTG0djwZC08cLXozeMss
aG5EzQ0IScpnWtHSTXuxByV/QCmxE7y+eS0uxWeoheaVVfqSJHiU7Mhhi6gULbOHorshkrEnKxpT
0n3A8Y8SMpuwZx6aoix3ouFlmW8gHRSkeSJ2g7hU+kiHLDaQw3bmRDaTGfTnty7gPm0FHbIBg9U9
oh1kZzAFLaue2R6htPCtAda2nGlDSUJ4PZBgCJBGVcwKTAMz/vJiLD+Oin5Z5QlvDPdulC6EsiyE
NFzb7McNTKJzbJqzphx92VKRFY1idenzmq3K0emRcbWBD0ryqc4NZGmKOOOX9Pz5x+/l27tP797c
f/z0d+4NruGNai8uAM0bfsYaw8itFk8ny41jsfpyO+BWlpqfhcG4yxLdi/0tQqoT4a8Vby382mt8
p7XSo7aWGdPBc+b6utaBmCQ7rQKQoWtAuthQCiold2KfJIPTT8xwg9blPumc+YDZC/wYGdAyHpJk
vUbHbHWAp5No6pK/WhhLEWrFjUwtPEv1Agf8YmnsuXUQYkeZoHm8ogP16gt2uHoxcEMdf2C6pmbw
hUMsWGhanboh4IzzmsIpWs134jVPqD/c74bZHdY69UKKSn/+KfVhxLgUlToemayLMYQOqfEC61bh
cbhwaqoGUzIyZRFHPmau5juaWqwRn3mpWmoEA5nhzS5gog/5jbcFQqOZvmBasZtwYlG93k5GEiyw
buHhMWLjDarEGpMGB2LFs5nIJkhp/nUmZneFaRth++lieJtHepIvKgx6PJqIlD9X2j6pG1i9x3pZ
5bHuCPFiirGHeO7McvoXkz786GaKVzC9DSpnOxJdc4xm6NSVq7lNEnKdVlnpu9BNYoKX2Iq3wvgh
gGEUM66kK6j4NiyoneuPLSwaCWDxczgaolEWpiMyDVDb7dNuLAbriL8ig8mmeju31oNvQdpnvEPC
1vAXbWacGRVrGt/uXN/gU0CDDwgooKRrHfTBb1/s9lYZ8ZqOBU0yLvpuP6+K9hLFsvIjeNhBi0KL
MlOuWRn3FRwx5oHXjl0YImUx0+gLzjGchrgzca026ETmYJzPD+IpuKzNi8AFn048Thd63OdD86M6
84zE8yQm0VqXdbbgvub2pKVnS76icBGdeTHHXTKspUmr4NYo/furFLKiMdQzFjHJNcdAnMhltBJK
0/IKX3DVFqvPJ2dLE7bDBkH0l/PJ29074+F0CsGYOxsb7U3myTUncYfXqnLLfa6sJybX4g+hmcjO
kMRBfA1JellfRRKJcyRpxdS4rIl6FdmQCWjo/o9Qz7yKffoP4JHjOvABcRn4CZIT2RH4jnxmfpVG
qgLaAvQBNfuO6X0/Ux02nb4FKx3vgP+XnkX0QW9pLy/NsXgdN24dD3LxO2Nwil7Zlc1dqtP3d7/h
kzp1/+7hGBuY4pk0XD/0Ao/oTe/XGrfyM773aB7iUhgkpy+dwAMalxMP0DrBcsVw/6p25+/hobP9
GBknrWExDhLJ1bwt1NcCNblaFbMKCyvmX0PeRaQ=
""")

##file distutils.cfg
DISTUTILS_CFG = convert("""
eJxNj00KwkAMhfc9xYNuxe4Ft57AjYiUtDO1wXSmNJnK3N5pdSEEAu8nH6lxHVlRhtDHMPATA4uH
xJ4EFmGbvfJiicSHFRzUSISMY6hq3GLCRLnIvSTnEefN0FIjw5tF0Hkk9Q5dRunBsVoyFi24aaLg
9FDOlL0FPGluf4QjcInLlxd6f6rqkgPu/5nHLg0cXCscXoozRrP51DRT3j9QNl99AP53T2Q=
""")

##file activate_this.py
ACTIVATE_THIS = convert("""
eJyNU01v2zAMvetXEB4K21jmDOstQA4dMGCHbeihlyEIDMWmG62yJEiKE//7kXKdpN2KzYBt8euR
fKSyLPs8wiEo8wh4wqZTGou4V6Hm0wJa1cSiTkJdr8+GsoTRHuCotBayiWqQEYGtMCgfD1KjGYBe
5a3p0cRKiAe2NtLADikftnDco0ko/SFEVgEZ8aRC5GLux7i3BpSJ6J1H+i7A2CjiHq9z7JRZuuQq
siwTIvpxJYCeuWaBpwZdhB+yxy/eWz+ZvVSU8C4E9FFZkyxFsvCT/ZzL8gcz9aXVE14Yyp2M+2W0
y7n5mp0qN+avKXvbsyyzUqjeWR8hjGE+2iCE1W1tQ82hsCZN9UzlJr+/e/iab8WfqsmPI6pWeUPd
FrMsd4H/55poeO9n54COhUs+sZNEzNtg/wanpjpuqHJaxs76HtZryI/K3H7KJ/KDIhqcbJ7kI4ar
XL+sMgXnX0D+Te2Iy5xdP8yueSlQB/x/ED2BTAtyE3K4SYUN6AMNfbO63f4lBW3bUJPbTL+mjSxS
PyRfJkZRgj+VbFv+EzHFi5pKwUEepa4JslMnwkowSRCXI+m5XvEOvtuBrxHdhLalG0JofYBok6qj
YdN2dEngUlbC4PG60M1WEN0piu7Nq7on0mgyyUw3iV1etLo6r/81biWdQ9MWHFaePWZYaq+nmp+t
s3az+sj7eA0jfgPfeoN1
""")

MH_MAGIC = 0xfeedface
MH_CIGAM = 0xcefaedfe
MH_MAGIC_64 = 0xfeedfacf
MH_CIGAM_64 = 0xcffaedfe
FAT_MAGIC = 0xcafebabe
BIG_ENDIAN = '>'
LITTLE_ENDIAN = '<'
LC_LOAD_DYLIB = 0xc
maxint = majver == 3 and getattr(sys, 'maxsize') or getattr(sys, 'maxint')


class fileview(object):
    """
    A proxy for file-like objects that exposes a given view of a file.
    Modified from macholib.
    """

    def __init__(self, fileobj, start=0, size=maxint):
        if isinstance(fileobj, fileview):
            self._fileobj = fileobj._fileobj
        else:
            self._fileobj = fileobj
        self._start = start
        self._end = start + size
        self._pos = 0

    def __repr__(self):
        return '<fileview [%d, %d] %r>' % (
            self._start, self._end, self._fileobj)

    def tell(self):
        return self._pos

    def _checkwindow(self, seekto, op):
        if not (self._start <= seekto <= self._end):
            raise IOError("%s to offset %d is outside window [%d, %d]" % (
                op, seekto, self._start, self._end))

    def seek(self, offset, whence=0):
        seekto = offset
        if whence == os.SEEK_SET:
            seekto += self._start
        elif whence == os.SEEK_CUR:
            seekto += self._start + self._pos
        elif whence == os.SEEK_END:
            seekto += self._end
        else:
            raise IOError("Invalid whence argument to seek: %r" % (whence,))
        self._checkwindow(seekto, 'seek')
        self._fileobj.seek(seekto)
        self._pos = seekto - self._start

    def write(self, bytes):
        here = self._start + self._pos
        self._checkwindow(here, 'write')
        self._checkwindow(here + len(bytes), 'write')
        self._fileobj.seek(here, os.SEEK_SET)
        self._fileobj.write(bytes)
        self._pos += len(bytes)

    def read(self, size=maxint):
        assert size >= 0
        here = self._start + self._pos
        self._checkwindow(here, 'read')
        size = min(size, self._end - here)
        self._fileobj.seek(here, os.SEEK_SET)
        bytes = self._fileobj.read(size)
        self._pos += len(bytes)
        return bytes


def read_data(file, endian, num=1):
    """
    Read a given number of 32-bits unsigned integers from the given file
    with the given endianness.
    """
    res = struct.unpack(endian + 'L' * num, file.read(num * 4))
    if len(res) == 1:
        return res[0]
    return res


def mach_o_change(path, what, value):
    """
    Replace a given name (what) in any LC_LOAD_DYLIB command found in
    the given binary with a new name (value), provided it's shorter.
    """

    def do_macho(file, bits, endian):
        # Read Mach-O header (the magic number is assumed read by the caller)
        cputype, cpusubtype, filetype, ncmds, sizeofcmds, flags = read_data(file, endian, 6)
        # 64-bits header has one more field.
        if bits == 64:
            read_data(file, endian)
        # The header is followed by ncmds commands
        for n in range(ncmds):
            where = file.tell()
            # Read command header
            cmd, cmdsize = read_data(file, endian, 2)
            if cmd == LC_LOAD_DYLIB:
                # The first data field in LC_LOAD_DYLIB commands is the
                # offset of the name, starting from the beginning of the
                # command.
                name_offset = read_data(file, endian)
                file.seek(where + name_offset, os.SEEK_SET)
                # Read the NUL terminated string
                load = file.read(cmdsize - name_offset).decode()
                load = load[:load.index('\0')]
                # If the string is what is being replaced, overwrite it.
                if load == what:
                    file.seek(where + name_offset, os.SEEK_SET)
                    file.write(value.encode() + '\0'.encode())
            # Seek to the next command
            file.seek(where + cmdsize, os.SEEK_SET)

    def do_file(file, offset=0, size=maxint):
        file = fileview(file, offset, size)
        # Read magic number
        magic = read_data(file, BIG_ENDIAN)
        if magic == FAT_MAGIC:
            # Fat binaries contain nfat_arch Mach-O binaries
            nfat_arch = read_data(file, BIG_ENDIAN)
            for n in range(nfat_arch):
                # Read arch header
                cputype, cpusubtype, offset, size, align = read_data(file, BIG_ENDIAN, 5)
                do_file(file, offset, size)
        elif magic == MH_MAGIC:
            do_macho(file, 32, BIG_ENDIAN)
        elif magic == MH_CIGAM:
            do_macho(file, 32, LITTLE_ENDIAN)
        elif magic == MH_MAGIC_64:
            do_macho(file, 64, BIG_ENDIAN)
        elif magic == MH_CIGAM_64:
            do_macho(file, 64, LITTLE_ENDIAN)

    assert(len(what) >= len(value))
    do_file(open(path, 'r+b'))


if __name__ == '__main__':
    main()

## TODO:
## Copy python.exe.manifest
## Monkeypatch distutils.sysconfig

########NEW FILE########
