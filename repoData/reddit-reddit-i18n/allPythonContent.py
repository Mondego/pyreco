__FILENAME__ = gendata
#!/usr/bin/env python
import collections
import gettext
import json
import os
import cPickle as pickle
import subprocess
import sys


Completion = collections.namedtuple('Completion',
        'lang_code lang_name lines_done total_lines words_done total_words')


def completion_info(pofile, lang_info=None):
    '''Given a path to a pofile, return a tuple of:
    (number of strings with translations, total number of strings)
    
    '''
    cmd = "msgattrib  %s --no-obsolete --no-wrap %s | grep '^msgid' | wc"
    translated = subprocess.check_output(cmd % ("--translated", pofile), shell=True)
    untranslated = subprocess.check_output(cmd % ("--untranslated", pofile), shell=True)
    # `wc` returns three values: line count, word count, character count
    # The lines printed by msgattrib are of the form:
    #     msgid "some string"
    # Subtract the line count from the word count so as not to be counting the
    # `msgid` words.
    translated = [int(x) for x in translated.split()]
    translated_lines = translated[0]
    translated_words = translated[1] - translated_lines
    untranslated = [int(x) for x in untranslated.split()]
    untranslated_lines = untranslated[0]
    untranslated_words = untranslated[1] - untranslated_lines
    if lang_info is None:
        lang_info = get_lang_info(pofile)
    return Completion(lang_info['language'], lang_info['display-name-en'],
                      translated_lines, translated_lines + untranslated_lines,
                      translated_words, translated_words + untranslated_words)


def csv_summary(pofile):
    return ",".join(str(x) for x in completion_info(pofile))


def completion_percent(completion):
    return 100.0 * completion.lines_done / completion.total_lines


def get_lang_info(pofile):
    lang_dir = os.path.dirname(os.path.dirname(pofile))
    lang = os.path.basename(lang_dir)
    directory = os.path.dirname(lang_dir)
    print '%s %s' % (directory, lang)
    translator = gettext.translation("r2", directory, [lang])
    return translator.info()


def build_data(datafilename, verbose=False):
    '''Create an r2.data file for a given language. r2.data is JSON formatted
    metadata about the translation, with the display name, english name,
    info on number of translated/untranslated strings, and whether
    or not the language is currently enabled
    
    '''
    prefix = datafilename[:-4]
    pofile = prefix + "po"
    lang_info = get_lang_info(pofile)
    info = completion_info(pofile)
    if verbose:
        print "%s: appears %i%% complete" % (info.lang, completion_percent(info))
    
    en_name = lang_info['display-name-en']
    if not en_name:
        raise ValueError("display-name-en not set for " + info.lang)
    disp_name = lang_info['display-name']
    if not disp_name:
        raise ValueError("display-name not set for " + info.lang)
    
    data = {'en_name': en_name,
            'name': disp_name,
            'num_completed': info.lines_done or 0,
            'num_total': info.total_lines or 1,
            '_is_enabled': lang_info.get("enabled", True),
            }
    with open(datafilename, "w") as datafile:
        json.dump(data, datafile)


if __name__ == '__main__':
    verbose = '-v' in sys.argv
    if '--csv' in sys.argv:
        if '--header' in sys.argv:
            print ','.join(Completion._fields)
        else:
            print csv_summary(sys.argv[-1])
    else:
        build_data(sys.argv[-1], verbose=verbose)

########NEW FILE########
__FILENAME__ = send_trophy
#!/usr/bin/python
import datetime
import logging
import sqlite3
import sys
import time

try:
    from r2.models import admintools
except ImportError:
    print >> sys.stderr, "Unable to import admintools"

import transifex
import transifex.history
import transifex.pm


TROPHY_EVENTS = ('project_resource_translated',)
TABLES = {'messages': '(user text, lang_uid text, date text)'}


def uid_from_lang(lang):
    # This intentionally chokes if lang is None.
    # lang of None is an indicator that transifex.history isn't
    # properly figuring out the languages from the timeline HTML
    return lang.replace(" ", "_").replace("(", "").replace(")", "").lower()


def iter_trophy_events(filename):
    # Put "Event" in the local namespace so the scary eval() works
    Event = transifex.history.Event
    with open(filename) as events:
        # super scary eval. input file should be trusted
        for event in events:
            event = eval(event)
            if event.kind in TROPHY_EVENTS:
                yield event


def get_cursor(config):
    db_path = config.get('local', 'db')
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    # TABLES is a trusted source
    for table in TABLES:
        try:
            cursor.execute('select count(*) from ' + table)
        except sqlite3.OperationalError:
            cursor.execute('create table ' + table + ' ' + TABLES[table])
    return cursor


SEEN_SQL = "SELECT * from messages WHERE user = ? AND lang_uid = ?"
INSERT_SQL = "INSERT INTO messages VALUES (?, ?, ?)"
def seen(cursor, user, lang_uid, date_txt):
    existing = cursor.execute(SEEN_SQL, (user, lang_uid)).fetchall()
    if not existing:
        cursor.execute(INSERT_SQL, (user, lang_uid, date_txt))
    return existing


def do_trophies(cursor, config, tx_session, filename):
    # Ensure that admintools import succeeded
    assert admintools
    project = config.get('site', 'project')
    trophy_url = config.get('site', 'remote') + '/projects/p/' + project
    for event in iter_trophy_events(filename):
        logging.info("Checking event %s", (event,))
        date_txt = datetime.date.today().isoformat()
        lang_uid = uid_from_lang(event.lang)
        if seen(cursor, event.user, lang_uid, date_txt):
            logging.info("User %s already has been sent trophy PM for %s",
                         event.user, lang_uid)
            continue
        logging.info("Sending Transifex PM with trophy link")
        description = '%s -- %s' % (event.lang, date_txt)
        claim_url = admintools.create_award_claim_code(lang_uid, 'i18n',
                                                       description, trophy_url)
        fmt_info = {'user': event.user, 'lang': event.lang, 'url': claim_url}
        subject = config.get('award', 'subject') % fmt_info
        body = config.get('award', 'message') % fmt_info

        transifex.pm.post_message(config, tx_session, event.user, subject,
                                  body)
        time.sleep(0.5)


def main(args):
    logging.basicConfig(level=logging.DEBUG)
    config = transifex.config_from_filepath(args[1])
    infile = args[2]
    cursor = get_cursor(config)
    tx_session = transifex.create_transifex_session(config)
    do_trophies(cursor, config, tx_session, infile)


if __name__ == '__main__':
    main(sys.argv)


########NEW FILE########
__FILENAME__ = history
#!/usr/bin/python
import collections
import logging
import os
import sys
import time
import transifex

from BeautifulSoup import BeautifulSoup
import requests 

PROJECT_PATH = 'projects/p/%(project)s'
TIMELINE = 'timeline/'


VERBOSE = True


Event = collections.namedtuple('Event', 'kind lang user when')


def dump_events(config, session, outfile, start_at=1, end_at=None):
    with open(outfile, 'w') as write_to:
        for event in iter_timeline(config, session, start_at=start_at, end_at=end_at):
            write_to.write(repr(event))
            write_to.write('\n')


def get_cookie():
    return {'cookie': os.environ['TXCOOKIE']}


def get_timeline_page(config, session, project='reddit', pagenum=1):
    site = config.get('site', 'remote')
    path = '/'.join([site, PROJECT_PATH, TIMELINE]) % {'project': project}
    params = {'page': pagenum}
    logging.info("Getting: %s?page=%s", path, pagenum)
    response = session.get(path, params=params)
    if response.ok:
        return BeautifulSoup(response.content)
    else:
        raise StandardError('Something went wrong', response)


def iter_timeline(config, session, start_at=1, end_at=None, sleep=2):
    page = start_at
    while True:
        soup = get_timeline_page(config, session, pagenum=page)
        table = soup.find('tbody')
        if not table:
            break
        for item in iter_table(table):
            yield item
        logging.info("Latest item: %r", (item,))
        if end_at is not None and page >= end_at:
            break
        page += 1
        time.sleep(sleep)


def iter_table(table):
    rows = table.findAll('tr')
    for row in rows:
        event = decompose_row(row)
        if event:
            yield event


def decompose_row(row):
    action_type = get_type(row)
    user = get_user(row)
    when = get_when(row)
    lang = get_lang(row)
    return Event(action_type, lang, user, when)


def get_type(row):
    span = row.findAll('td')[0].find('span')
    return _attrs(span)['title']


def get_user(row):
    td = row.findAll('td')[1]
    assert 'timelineuser' in _attrs(td)['class']
    return td.text.strip()


def get_when(row):
    td = row.findAll('td')[2]
    assert 'timelinewhen' in _attrs(td)['class']
    return td.text


def get_lang(row):
    td = row.findAll('td')[3]
    text = td.text.strip()
    if text.startswith('A translation for'):
        text = text.split()
        start = len('A translation for'.split())
        end = text.index('was')
        return u' '.join(text[start:end])
    elif 'submitted a ' in text and ' translation ' in text:
        text = text.partition('submitted a ')[2]
        text = text.partition(' translation')[0]
        return text
    else:
        hrefs = td.findAll('a')
        for href in hrefs:
            if '/language/' in _attrs(href)['href']:
                lang = href.text
                return lang[:-len(' language translation')]
    return None


def _attrs(soup):
    return dict(soup.attrs)


def main(args):
    logging.basicConfig(level=logging.DEBUG)
    configpath = args[1]
    assert args[2] == '--page'
    page = int(args[3])
    outfile = args[4]
    assert outfile
    config = transifex.config_from_filepath(configpath)
    session = transifex.create_transifex_session(config)
    dump_events(config, session, outfile, end_at=page)


if __name__ == '__main__':
    main(sys.argv)


########NEW FILE########
__FILENAME__ = pm
#!/usr/bin/python
import logging
import os
import sys

import requests 

import transifex

MESSAGE_SEND_PATH = '/messages/compose/'


def post_message(config, session, recipient, subject, message):
    path = config.get('site', 'remote') + MESSAGE_SEND_PATH
    headers =  {'Referer': path}
    csrf = session.cookies['csrftoken']
    params = {'body': message,
              'csrfmiddlewaretoken': csrf,
              'recipient': recipient,
              'send_message': 'Send ',
              'subject': subject}
    logging.info("POSTing to: %s", path)
    logging.info("subject: %(subject)s\nrecipient: %(recipient)s" % params)
    logging.debug("body: %(body)s" % params)

    response = session.post(path, data=params, headers=headers)
    logging.info(response)
    if not response.ok:
        raise StandardError("Something went wrong", response)
    else:
        return response


def main(args):
    logging.basicConfig(level=logging.DEBUG)
    cmd, configpath, user, subject, body = sys.argv
    config = transifex.config_from_filepath(configpath)
    session = transifex.create_transifex_session(config)
    import time; time.sleep(1)
    post_message(config, session, user, subject, body)


if __name__ == '__main__':
    main(sys.argv)

########NEW FILE########
__FILENAME__ = revert_display_name
#!/usr/bin/env python
'''Temporary script to revert the "Display-Name" and
"Display-Name-en" metadata that the transifex client
strips out when running "tx pull".

'''
import fileinput
import os
import subprocess
import sys

COMMAND = "git show HEAD:%s | grep -i display-name"
def get_display_name(filename):
    lines = subprocess.check_output(COMMAND % filename, shell=True)
    return lines


def has_display_name(filename):
    with open(filename) as f:
        contents = f.read().lower()
        return '\n"display-name' in contents


def write_display_name_lines(filename, lines):
    written = False
    if has_display_name(filename):
        print "%s already has Display-Name lines" % filename
        return
    for line in fileinput.input(filename, inplace=1, backup=".dn.bak"):
        if not written and line.startswith('"Content-Transfer-Encoding'):
            for l in lines:
                sys.stdout.write(l)
            written = True
        sys.stdout.write(line)


def handle_lang(lang_path, po_file="r2.po"):
    filename = os.path.join(lang_path, po_file)
    lines = get_display_name(filename)
    write_display_name_lines(filename, lines)


if __name__ == "__main__":
    handle_lang(sys.argv[1])

########NEW FILE########
