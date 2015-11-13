__FILENAME__ = compilebot
from __future__ import unicode_literals, print_function
import ideone
import time
import praw
import re
import json
import urllib
import traceback

class Reply(object):

    """An object that represents a potential response to a comment.

    Replies are not tied to a specific recipient on at their inception,
    however once sent the recipient should be recorded.
    """

    def __init__(self, text):
        # Truncate text if it exceeds max character limit.
        if len(text) >= 10000:
            text = text[:9995] + '\n...'
        self.text = text
        self.recipient = None

    def send(self, *args, **kwargs):
        """An abstract method that sends the reply."""
        raise NotImplementedError

class CompiledReply(Reply):

    """Replies that contain details about evaluated code. These can be
    sent as replies to comments.
    """

    def __init__(self, text, compile_details):
        Reply.__init__(self, text)
        self.compile_details = compile_details
        self.parent_comment = None

    def send(self, comment):
        """Send a reply to a specific reddit comment or message."""
        self.parent_comment = comment
        self.recipient = comment.author
        try:
            comment.reply(self.text)
            log("Replied to {id}".format(id=comment.id))
        except praw.errors.RateLimitExceeded as e:
            log("Rate Limit exceeded. "
                "Sleeping for {time} seconds".format(time=e.sleep_time))
            # Wait and try again.
            time.sleep(e.sleep_time)
            self.send(comment)
        # Handle and log miscellaneous API exceptions
        except praw.errors.APIException as e:
            log("Exception on comment {id}, {error}".format(
                id=comment.id, error=e))

    def make_edit(self, comment, parent):
        """Edit one of the bot's existing comments."""
        self.parent_comment = parent
        self.recipient = parent.author
        comment.edit(self.text)
        log("Edited comment {}".format(comment.id))

    def detect_spam(self):
        """Scan a reply and return a list of potentially spammy attributes
        found in the comment's output.
        """
        output = self.compile_details['output']
        source = self.compile_details['source']
        errors = self.compile_details['stderr']

        spam_behaviors = {
            "Excessive line breaks": output.count('\n') > LINE_LIMIT,
            "Excessive character count": len(output) > CHAR_LIMIT,
            "Spam phrase detected": any([word.lower() in (source + output).lower()
                                         for word in SPAM_PHRASES]),
            "Illegal system call detected": "Permission denied" in errors
        }
        if any(spam_behaviors.values()):
            spam_triggers = [k for k, v in spam_behaviors.iteritems() if v]
            return spam_triggers
        return []

class MessageReply(Reply):

    """Replies that contain information that may be sent to a reddit user
    via private message.
    """

    def __init__(self, text, subject=''):
        Reply.__init__(self, text)
        self.subject = subject

    def send(self, comment):
        """Reply the author of a reddit comment by sending them a reply
        via private message.
        """
        self.recipient = comment.author
        r = comment.reddit_session
        # If no custom subject line is given, the default will be a label
        # that identifies the comment.
        if not self.subject:
            self.subject = "Comment {id}".format(id=comment.id)
        # Prepend message subject with username
        self.subject = "{} - {}".format(R_USERNAME, self.subject)
        r.send_message(self.recipient, self.subject, self.text)
        log("Message reply for comment {id} sent to {to}".format(
            id=comment.id, to=self.recipient))

def log(message, alert=False):
    """Log messages along with a timestamp in a log file. If the alert
    option is set to true, send a message to the admin's reddit inbox.
    """
    t = time.strftime('%y-%m-%d %H:%M:%S', time.localtime())
    message = "{}: {}\n".format(t, message)
    if LOG_FILE:
        with open(LOG_FILE, 'a') as f:
            f.write(message)
    else:
        print(message, end='')
    if alert and ADMIN:
        r = praw.Reddit(USER_AGENT)
        r.login(R_USERNAME, R_PASSWORD)
        admin_alert = message
        subject = "CompileBot Alert"
        r.send_message(ADMIN, subject, admin_alert)

def compile(source, lang, stdin=''):
    """Compile and evaluate source sode using the ideone API and return
    a dict containing the output details.

    Keyword arguments:
    source -- a string containing source code to be compiled and evaluated
    lang -- the programming language pertaining to the source code
    stdin -- optional "standard input" for the program

    >>> d = compile('print("Hello World")', 'python')
    >>> d['output']
    Hello World

    """
    lang = LANG_SHORTCUTS.get(lang.lower(), lang)
    # Login to ideone and create a submission
    i = ideone.Ideone(I_USERNAME, I_PASSWORD)
    sub = i.create_submission(source, language_name=lang, std_input=stdin)
    sub_link = sub['link']
    details = i.submission_details(sub_link)
    # The status of the submission indicates whether or not the source has
    # finished executing. A status of 0 indicates the submission is finished.
    while details['status'] != 0:
        details = i.submission_details(sub_link)
        time.sleep(3)
    details['link'] = sub_link
    return details

def code_block(text):
    """Create a markdown formatted code block containing the given text"""
    return ('\n' + text).replace('\n', '\n    ')

def get_banned(reddit):
    """Retrive list of banned users list from the moderator subreddit"""
    banned = {user.name.lower() for user in
                reddit.get_subreddit(SUBREDDIT).get_banned()}
    return banned

def send_modmail(subject, body, reddit):
    """Send a message to the bot moderators"""
    if SUBREDDIT:
        sub = reddit.get_subreddit(SUBREDDIT)
        reddit.send_message(sub, subject, body)
    else:
        log("Mod message not sent. No subreddit found in settings.")

def format_reply(details, opts):
    """Returns a reply that contains the output from a ideone submission's
    details along with optional additional information.
    """
    head, body, extra, = '', '', ''
    # Combine information that will go before the output.
    if '--source' in opts:
        head += 'Source:\n{}\n\n'.format(code_block(details['source']))
    if '--input' in opts:
    # Combine program output and runtime error output.
        head += 'Input:\n{}\n\n'.format(code_block(details['input']))
    output = details['output'] + details['stderr']
    # Truncate the output if it contains an excessive
    # amount of line breaks or if it is too long.
    if output.count('\n') > LINE_LIMIT:
        lines = output.split('\n')
        # If message contains an excessive amount of duplicate lines,
        # truncate to a small amount of lines to discourage spamming
        if len(set(lines)) < 5:
            lines_allowed = 2
        else:
            lines_allowed = 51
        output = '\n'.join(lines[:lines_allowed])
        output += "\n..."
    # Truncate the output if it is too long.
    if len(output) > 8000:
        output = output[:8000] + '\n    ...\n'
    body += 'Output:\n{}\n\n'.format(code_block(output))
    if details['cmpinfo']:
        body += 'Compiler Info:\n{}\n\n'.format(code_block(details['cmpinfo']))
    # Combine extra runtime information.
    if '--date' in opts:
        extra += "Date: {}\n\n".format(details['date'])
    if '--memory' in opts:
        extra += "Memory Usage: {} bytes\n\n".format(details['memory'])
    if '--time' in opts:
        extra += "Execution Time: {} seconds\n\n".format(details['time'])
    if '--version' in opts:
        extra += "Version: {}\n\n".format(details['langVersion'])
    # To ensure the reply is less than 10000 characters long, shorten
    # sections of the reply until they are of adequate length. Certain
    # sections with less priority will be shortened before others.
    total_len = 0
    for section in (FOOTER, body, head, extra):
        if len(section) + total_len > 9800:
            section = section[:9800 - total_len] + '\n...\n'
            total_len += len(section)
    reply_text = head + body + extra
    return reply_text

def parse_comment(body):
    """Parse a string that contains a username mention and code block
    and return the supplied arguments, source code and input.

    c_pattern is a regular expression that searches for the following:
        1. "+/u/" + the reddit username that is using the program
            (case insensitive).
        2. A string representing the programming language and arguments
            + a "\n".
        3. A markdown code block (one or more lines indented by 4 spaces or
            a tab) that represents the source code + a "\n".
        4. (Optional) "Input:" OR "Stdin:" + "\n".
        5. (Optional) A markdown code block that represents the
            program's input.
    """
    c_pattern = (
        r'\+/u/(?i)%s\s*(?P<args>.*)\n\s*'
        r'((?<=\n( {4}))|(?<=\n\t))'
        r'(?P<src>.*(\n((( {4}|\t).*\n)|\n)*(( {4}|\t).*))?)'
        r'(\n\s*((?i)Input|Stdin):?\s*\n\s*'
        r'((?<=\n( {4}))|(?<=\n\t))'
        r'(?P<in>.*(\n((( {4}|\t).*\n)|\n)*(( {4}|\t).*\n?))?))?'
    ) % R_USERNAME
    m = re.search(c_pattern, body)
    args, src, stdin = m.group('args'), m.group('src'), m.group('in') or ''
    # Remove the leading four spaces from every line.
    src = src.replace('\n    ', '\n')
    stdin = stdin.replace('\n    ', '\n')
    return args, src, stdin

def create_reply(comment):
    """Search comments for username mentions followed by code blocks
    and return a formatted reply containing the output of the executed
    block or a message with additional information.
    """
    try:
        args, src, stdin = parse_comment(comment.body)
    except AttributeError:
        preamble = ERROR_PREAMBLE.format(link=comment.permalink)
        postamble = ERROR_POSTAMBLE.format(link=comment.permalink)
        error_text = preamble + FORMAT_ERROR_TEXT + postamble
        log("Formatting error on comment {c.permalink}:\n\n{c.body}".format(
            c=comment))
        return MessageReply(error_text)
    # Seperate the language name from the rest of the supplied options.
    try:
        lang, opts = args.split(' -', 1)
        opts = ('-' + opts).split()
    except ValueError:
        # No additional opts found
        lang, opts = args, []
    lang = lang.strip()
    try:
        details = compile(src, lang, stdin=stdin)
        log("Compiled ideone submission {link} for comment {id}".format(
            link=details['link'], id=comment.id))
    except ideone.LanguageNotFoundError as e:
        preamble = ERROR_PREAMBLE.format(link=comment.permalink)
        postamble = ERROR_POSTAMBLE.format(link=comment.permalink)
        choices = ', '.join(e.similar_languages)
        error_text = LANG_ERROR_TEXT.format(lang=lang, choices=choices)
        error_text = preamble + error_text + postamble
        # TODO Add link to accepted languages to msg
        log("Language error on comment {id}".format(id=comment.id))
        return MessageReply(error_text)
    # The ideone submission result value indicaties the final state of
    # the program. If the program compiled and ran successfully the
    # result is 15. Other codes indicate various errors.
    result_code = details['result']
    # The user is alerted of any errors via message reply unless they
    # include an option to include errors in the reply.
    if result_code == 15 or '--include-errors' in opts:
        text = format_reply(details, opts)
        ideone_link = "http://ideone.com/{}".format(details['link'])
        url_pl = urllib.quote(comment.permalink)
        text += FOOTER.format(ide_link=ideone_link, perm_link=url_pl)
    else:
        log("Result error {code} detected in comment {id}".format(
            code=result_code, id=comment.id))
        preamble = ERROR_PREAMBLE.format(link=comment.permalink)
        postamble = ERROR_POSTAMBLE.format(link=comment.permalink)
        error_text = {
            11: COMPILE_ERROR_TEXT,
            12: RUNTIME_ERROR_TEXT,
            13: TIMEOUT_ERROR_TEXT,
            17: MEMORY_ERROR_TEXT,
            19: ILLEGAL_ERROR_TEXT,
            20: INTERNAL_ERROR_TEXT
        }.get(result_code, '')
        # Include any output from the submission in the reply.
        if details['cmpinfo']:
            error_text += "Compiler Output:\n\n{}\n\n".format(
                                code_block(details['cmpinfo']))
        if details['output']:
            error_text += "Output:\n\n{}\n\n".format(
                    code_block(details['cmpinfo']))
        if details['stderr']:
            error_text += "Error Output:\n\n{}\n\n".format(
                                code_block(details['stderr']))
        error_text = preamble + error_text + postamble
        return MessageReply(error_text)
    return CompiledReply(text, details)

def process_unread(new, r):
    """Parse a new comment or message for various options and ignore reply
    to as appropriate.
    """
    reply = None
    sender = new.author
    log("New {type} {id} from {sender}".format(
        type="mention" if new.was_comment else "message",
        id=new.id, sender=sender))
    if sender.name.lower() in BANNED_USERS:
        log("Ignoring banned user {user}".format(user=sender))
        return
    # Search for a user mention preceded by a '+' which is the signal
    # for CompileBot to create a reply for that comment.
    if (new.was_comment and
        re.search(r'(?i)\+/u/{}'.format(R_USERNAME), new.body)):
        reply = create_reply(new)
        if reply:
            reply.send(new)
    elif ((not new.was_comment) and
          re.match(r'(i?)\s*--help', new.body)):
        # Message a user the help text if comment is a message
        # containing "--help".
        reply = MessageReply(HELP_TEXT, subject='CompileBot Help')
        reply.send(new)
    elif ((not new.was_comment) and
          re.match(r'(i?)\s*--report', new.body) and SUBREDDIT):
        # Forward message to the moderators
        send_modmail("Report from {author}".format(author=new.author),
                     new.body, r)
        reply = MessageReply("Your message has been forwarded to the "
                             "moderators. Thank you.",
                             subject="CompileBot Report")
        reply.send(new)
    elif ((not new.was_comment) and
          re.match(r'(i?)\s*--recompile', new.body)):
        # Search for the recompile command followed by a comment id.
        # Example: 1tt4jt/post_title/ceb7czt
        # The comment id can optionally be prefixed by a url.
        # Example: reddit.com/r/sub/comments/1tt4jt/post_title/ceb7czt
        p = (r'(i?)--recompile\s*(?P<url>[^\s*]+)?'
             r'(?P<id>\b\w+/\w+/\w+\b)')
        m = re.search(p, new.body)
        try:
            id = m.group('id')
        except AttributeError:
            new.reply(RECOMPILE_ERROR_TEXT)
            return
        # Fetch the comment that will be recompiled.
        sub = r.get_submission(submission_id=id, comment_sort='best')
        original = sub.comments[0]
        log("Processing request to recompile {id} from {user}"
            "".format(id=original.id, user=new.author))
        # Ensure the author of the original comment matches the author
        # requesting the recompile to prevent one user sending a recompile
        # request on the behalf of another.
        if original.author == new.author:
            reply = create_reply(original)
            # Ensure the recompiled reply resulted in a valid comment
            # reply and not an error message reply.
            if isinstance(reply, CompiledReply):
                # Search for an existing comment reply from the bot.
                # If one is found, edit the existing comment instead
                # of creating a new one.
                #
                # Note: the .replies property only returns a limited
                # number of comments. If the reply is buried, it will
                # not be retrieved and a new one will be created
                for rp in original.replies:
                    if rp.author.name.lower() == R_USERNAME.lower():
                        footnote = ("\n\n**EDIT:** Recompile request "
                                    "by {}".format(new.author))
                        reply.text += footnote
                        reply.make_edit(rp, original)
                        break
                else:
                    # Reply to the original comment.
                    reply.send(original)
            else:
                # Send a message reply.
                reply.send(new)
        else:
            new.reply(RECOMPILE_AUTHOR_ERROR_TEXT)
            log("Attempt to reompile on behalf of another author "
                "detected. Request deined.")
    if reply and isinstance(reply, CompiledReply):
        spam = reply.detect_spam()
        if spam:
            text = ("Potential spam detected on comment {c.permalink} "
                    "by {c.author}: ".format(c=reply.parent_comment))
            text += ', '.join(spam)
            send_modmail("Potential spam detected", text, r)
            log(text)

def main():
    r = praw.Reddit(USER_AGENT)
    r.login(R_USERNAME, R_PASSWORD)
    if SUBREDDIT:
        global BANNED_USERS
        BANNED_USERS = get_banned(r)
    # Iterate though each new comment/message in the inbox and
    # process it appropriately.
    inbox = r.get_unread()
    for new in inbox:
        try:
            process_unread(new, r)
        except:
            tb = traceback.format_exc()
            # Notify admin of any errors
            log("Error processing comment {c.id}\n"
                "{traceback}".format(c=new, traceback=tb), alert=True)
        finally:
            new.mark_as_read()

# Settings
SETTINGS_FILE = 'settings.json'
# Fetch settings from json file
try:
    with open(SETTINGS_FILE, 'r') as f:
        SETTINGS = json.load(f)
except (OSError, IOError) as e:
    print("Please configure settings.json")
LOG_FILE = SETTINGS['log_file']
# Login credentials
I_USERNAME = SETTINGS['ideone_user']
I_PASSWORD = SETTINGS['ideone_pass']
R_USERNAME = SETTINGS['reddit_user']
R_PASSWORD = SETTINGS['reddit_pass']
USER_AGENT = SETTINGS['user_agent']
ADMIN = SETTINGS['admin_user']
SUBREDDIT = SETTINGS['subreddit']
LANG_SHORTCUTS = {k.lower(): v for k, v in SETTINGS['lang_shortcuts'].items()}
# A set of users that are banned. The banned users list is retrieved
# in the main session but not here because it requires a reddit login.
BANNED_USERS = set()
# Text
TEXT = SETTINGS['text']
FOOTER = TEXT['footer']
ERROR_PREAMBLE = TEXT['error_preamble']
ERROR_POSTAMBLE = TEXT['error_postamble']
HELP_TEXT = TEXT['help_text']
LANG_ERROR_TEXT = TEXT['language_error_text']
FORMAT_ERROR_TEXT = TEXT['format_error_text']
COMPILE_ERROR_TEXT = TEXT['compile_error_text']
RUNTIME_ERROR_TEXT = TEXT['runtime_error_text']
TIMEOUT_ERROR_TEXT = TEXT['timeout_error_text']
MEMORY_ERROR_TEXT = TEXT['memory_error_text']
ILLEGAL_ERROR_TEXT = TEXT['illegal_error_text']
INTERNAL_ERROR_TEXT =  TEXT['internal_error_text']
RECOMPILE_ERROR_TEXT = TEXT['recompile_error_text']
RECOMPILE_AUTHOR_ERROR_TEXT = TEXT['recompile_author_error_text']
# Spam Settings
LINE_LIMIT = SETTINGS["spam"]["line_limit"]
CHAR_LIMIT = SETTINGS["spam"]["char_limit"]
SPAM_PHRASES = SETTINGS["spam"]["spam_phrases"]

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = deploy
import time
import traceback
from requests import HTTPError
import compilebot as bot

SLEEP_TIME = 60

def main():
    try:
        bot.log("Initializing bot")
        while True:
            try:
                bot.main()
            except HTTPError as e:
                # HTTP Errors may indicate reddit is overloaded.
                # Sleep for some extra time. 
                bot.log(str(e) + " ")
                time.sleep(SLEEP_TIME*2)
            except Exception as e:
                bot.log("Error running bot.main: {error}".format(
                        error=e), alert=True)
            time.sleep(SLEEP_TIME)
    except KeyboardInterrupt:
        exit_msg = ''
    except Exception as e:
        tb = traceback.format_exc()
        exit_msg = "Depoyment error: {traceback}\n".format(traceback=tb)
        bot.log("{msg}Bot shutting down".format(msg=exit_msg), alert=True)
        
if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = run_all
# This script runs all of the suites from each unit test file.
# Run this file from the parent directory with the following command:
# python -m tests.run_all
from tests import *
import unittest    

def main():
    test_suites = [
        test_reply.test_suite(),
        test_compiler.test_suite()
    ]
    all_tests = unittest.TestSuite(test_suites)
    unittest.TextTestRunner().run(all_tests)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = test_compiler
from __future__ import unicode_literals, print_function
import unittest
import compilebot as cb

"""
Unit test cases for the compile function. Tests require an ideone login
credentials.

Run the following command from the parent directory in order to run only
this test module: python -m unittest tests.test_compiler
"""

cb.USER_AGENT = "compilebot unit tests run by {}".format(cb.R_USERNAME)
cb.LOG_FILE = "tests.log"

def test_suite():
    cases = [
        TestCompile
    ]
    alltests = [
        unittest.TestLoader().loadTestsFromTestCase(case) for case in cases
    ]
    return unittest.TestSuite(alltests)
    
    
class TestCompile(unittest.TestCase):


    def test_compile(self):
        expected_details = {
            'cmpinfo': '',
            'error': 'OK',
            'input': "Hello World",
            'langId': 116,
            'langName': "Python 3",
            'output': "Hello World\n",
            'public': True,
            'result': 15,
            'signal': 0,
            'source': "x = input()\nprint(x)",
            'status': 0,
            'stderr': "",
        }
        source = "x = input()\nprint(x)"
        lang = "python 3"
        stdin = "Hello World"
        details = cb.compile(source, lang, stdin)
        self.assertTrue(details['link'])
        self.assertDictContainsSubset(expected_details, details)

     
if __name__ == "__main__":
    unittest.main(exit=False)

########NEW FILE########
__FILENAME__ = test_reply
from __future__ import unicode_literals, print_function
import unittest
import random
import string 
from imp import reload
import compilebot as cb

"""
Unit test cases for functions, methods, and classes that format, create, 
and edit replies. All tests in this module shouldn't make any requests 
to reddit or ideone.

Run the following command from the parent directory in order to run only
this test module: python -m unittest tests.test_reply
"""

LOG_FILE = "tests.log" 
cb.LOG_FILE = LOG_FILE

def reddit_id(length=6):
    """Emulate a reddit id with a random string of letters and digits"""
    return ''.join(random.choice(string.ascii_lowercase + 
                   string.digits) for x in range(length))
    
def test_suite():
    cases = [
        TestParseComment, TestCreateReply, TestProcessUnread, TestDetectSpam
    ]
    alltests = [
        unittest.TestLoader().loadTestsFromTestCase(case) for case in cases
    ]
    return unittest.TestSuite(alltests)


class TestParseComment(unittest.TestCase):

    def setUp(self):
        self.user = cb.R_USERNAME

    def test_parser(self):
        body = ("This sentence should not be included. +/u/{user} python 3\n\n"
                "    print(\"Test\")\n\n"
                "This sentence should not be included.".format(user=self.user))
        args, source, stdin = cb.parse_comment(body)
        self.assertEqual(args, 'python 3')
        self.assertEqual(source, 'print(\"Test\")')
        self.assertEqual(stdin, '')
    
    def test_parse_args(self):
        body = ("+/u/{user} python 3 --time\n\n"
                "    \n        x = input()\n    print(\"x\")\n    \n\n\n"
                "Input: \n\n    5\n    6\n    7").format(user=self.user)
        args, source, stdin = cb.parse_comment(body)
        self.assertEqual(args, 'python 3 --time')
        self.assertEqual(source, '    x = input()\nprint(\"x\")\n')
        self.assertEqual(stdin, '5\n6\n7')
        
    def test_errors(self):
        # Should raise an attribute error when there an indented code
        # block is missing.
        body = ("+/u/{user} Java\n\n Source code missing"
                "\n\n".format(user=self.user))
        self.assertRaises(AttributeError, cb.parse_comment, (body))

class TestCreateReply(unittest.TestCase):
    
    # Simplified version of a PRAW comment for testing purposes.
    class Comment(object):
        def __init__(self, body):
            self.body = body
            self.id = reddit_id()
            self.permalink = ''
    
    def setUp(self):
        self.user = cb.R_USERNAME
    
    def test_create_reply(self):
        def compile(*args, **kwargs):
            return {
                'cmpinfo': "",
                'input': "",
                'langName': "Python",
                'output': "Test",
                'result': 15,
                'stderr': "",
                'link': ""
            }
        cb.compile = compile
        body = ("+/u/{user} python\n\n"
                "    print(\"Test\")\n\n".format(user=self.user))
        comment = self.Comment(body)
        reply = cb.create_reply(comment)
        self.assertIn("Output:\n\n    Test\n", reply.text)
        
    def test_bad_format(self):
        body = "+/u/{user} Formatted incorrectly".format(user=self.user)
        comment = self.Comment(body)
        reply = cb.create_reply(comment)
        self.assertIsInstance(reply, cb.MessageReply)
        self.assertIn(cb.FORMAT_ERROR_TEXT, reply.text)
        
    def test_missing_language(self):
        def compile(*args, **kwargs):
            raise cb.ideone.LanguageNotFoundError(error_msg, similar_langs)
        cb.compile = compile
        error_msg = "Language Error Message"
        similar_langs = ["FooBar", "BazzScript", "Z 1-X"]
        # When the compile function returns an LanguageNotFoundError,
        # compilebot should notify the user the possible languages they 
        # were looking for via message reply.
        body = "+/u/{user} Foo\n\n    print(\"Test\")\n\n".format(user=self.user)
        comment = self.Comment(body)
        reply = cb.create_reply(comment)
        self.assertIsInstance(reply, cb.MessageReply)
        self.assertTrue(all(lang in reply.text for lang in similar_langs))
        
    def test_result_errors(self):
        # Test each error code and ensure the user will be alerted of
        # errors via private message instead of in compiled replies.
        for error_code in [13, 17, 19, 20, 12]:
            def compile(*args, **kwargs):
                return {
                    'cmpinfo': "",
                    'input': "",
                    'langName': "Python",
                    'output': "Test",
                    'result': error_code,
                    'stderr': "Error message",
                    'link': ""
                }
            cb.compile = compile
            body = ("+/u/{user} python\n\n"
                    "    error\n\n".format(user=self.user))
            comment = self.Comment(body)
            reply = cb.create_reply(comment)
            self.assertIsInstance(reply, cb.MessageReply)
        body = ("+/u/{user} python --include-errors\n\n"
                "    error\n\n".format(user=self.user))
        comment = self.Comment(body)
        reply = cb.create_reply(comment)
        self.assertIsInstance(reply, cb.CompiledReply)
        
    def tearDown(self):
        reload(cb)
        cb.LOG_FILE = LOG_FILE

class TestProcessUnread(unittest.TestCase):
    
    # The following classes are meant to emulate various PRAW objects
    # They do not contain all of the same attributes if the original
    # PRAW class, but only the necessary ones needed for testing the
    # process_unread function.
    
    class Reddit(object):
        def __init__(self):
            self._sent_message = False
            self._message_recipient = ''
            self._message_subject = ''
            self._message_text = ''
            # Allows a custom comment to be assigned that is used to
            # verify if get_submission is working correctly.
            self._get_sub_comment = None
            
        def get_subreddit(*args, **kwargs):
            pass
            
        def send_message(self, recipient, subject, text, **kwargs):
            self._sent_message = True
            self._message_recipient = recipient
            self._message_subject = subject
            self._message_text = text
            
        def get_submission(self, *args, **kwargs):
            s = TestProcessUnread.Submission()
            if kwargs.get('submission_id') == self._get_sub_comment.permalink:
                s.comments.append(self._get_sub_comment)
            return s
    
    class Submission(object):
        def __init__(self):
            self.comments = []
            
    class Repliable(object):
        def __init__(self, author=None, body='', reddit_session=None, replies=[]):
            self.author = author or TestProcessUnread.Author()
            self.body = body
            self.replies = replies
            self.id = reddit_id()
            self.reddit_session = reddit_session
            self._replied_to = False
            self._reply_text = ''    
        
        def reply(self, text):
            self._replied_to = True
            self._reply_text = text
    
    class Author(object):
        def __init__(self, name=''):
            self.name = name
            
        def __eq__(self, other):
            return self.name == other.name
            
        def __ne__(self, other):
            return self.name != other.name
            
        def __str__(self):
            return self.name
            
    class Message(Repliable):
        def __init__(self, *args,  **kwargs):
            TestProcessUnread.Repliable.__init__(self, *args, **kwargs)
            self.was_comment = False
            
    class Comment(Repliable):
        def __init__(self, *args, **kwargs):
            TestProcessUnread.Repliable.__init__(self, *args, **kwargs)
            self.was_comment = True
            self.permalink = reddit_id() + '/test/' + self.id
            self._edited = False
            self._edit_text = ''
            
        def edit(self, text):
            self._edited = True
            self._edit_text = text
    
    def setUp(self):
        self.r = self.Reddit()
        self.user = cb.R_USERNAME
         
    def test_process_reply(self):
    
        def compile(*args, **kwargs):
            return {
                'cmpinfo': '', 'error': 'OK', 'input': "Hello World",
                'langId': 116, 'link': '', 'langName': "Python 3",
                'output': "Hello World\n", 'public': True, 'result': 15,
                'signal': 0, 'source': "x = input()\nprint(x)", 'status': 0,
                'stderr': "",
            }
        
        cb.compile = compile
        body = ("+/u/{user} python 3\n\n    x = input()\n    print(x)"
                "\n\n".format(user=self.user))
        new = self.Comment(body=body, reddit_session=self.r)
        cb.process_unread(new, self.r)
        self.assertTrue(new._replied_to)
        self.assertIn("Output:\n\n    Hello World", new._reply_text)
        
    def test_help_request(self):
        new = self.Message(body="--help", reddit_session=self.r)
        cb.process_unread(new, self.r)
        self.assertTrue(self.r._sent_message)
        self.assertIn(cb.HELP_TEXT, self.r._message_text)
        
    def test_banned_filter(self):
        cb.BANNED_USERS.add("Banned-User-01")
        new = self.Comment(author=self.Author(name="Banned-User-01"))
        cb.process_unread(new, self.r)
        self.assertFalse(new._replied_to)
        
    def test_recompile_request(self):
    
        def compile(*args, **kwargs):
            return {
                'cmpinfo': '', 'error': 'OK', 'input': "Hello World",
                'langId': 116, 'link': '', 'langName': "Python 3",
                'output': "Hello World\n", 'public': True, 'result': 15,
                'signal': 0, 'source': "x = input()\nprint(x)", 'status': 0,
                'stderr': "",
            }
        
        cb.compile = compile
        # Create the comment that will be recompiled.    
        body = ("+/u/{user} python 3\n\n    x = input()\n    print(x)"
                "\n\n".format(user=self.user))
        original = self.Comment(body=body, reddit_session=self.r)
        self.r._get_sub_comment = original
        # Message that makes the recompile request.
        body = "--recompile {link}".format(link=original.permalink)
        new = self.Message(body=body, reddit_session=self.r)
        cb.process_unread(new, self.r)
        self.assertTrue(original._replied_to)
        
    def test_recompile_edit(self):
        # Ensure that if there is an existing reply from a bot on a 
        # comment that is being recompiled, the existing reply is 
        # editing instead of making a new comment.
        def compile(*args, **kwargs):
            return {
                'cmpinfo': '', 'error': 'OK', 'input': "Hello World",
                'langId': 116, 'link': '', 'langName': "Python 3",
                'output': "Test\n", 'public': True, 'result': 15,
                'signal': 0, 'source': "print(\"Test\")", 'status': 0,
                'stderr': "",
            }
            
        cb.compile = compile
        existing_reply = self.Comment(author=self.Author(self.user))
        body = ("+/u/{user} python 3\n\n    print(\"test\")\n\n"
               "\n\n".format(user=self.user))
        
        replies = [existing_reply]
        original = self.Comment(body=body, reddit_session=self.r, 
                                replies=replies)
        self.r._get_sub_comment = original
        
        body = "--recompile {link}".format(link=original.permalink)
        new = self.Message(body=body, reddit_session=self.r)
        cb.process_unread(new, self.r)
        self.assertTrue(existing_reply._edited)
        self.assertIn("Output:\n\n    Test", existing_reply._edit_text)
        self.assertFalse(original._replied_to)
    
    def test_recompile_user_permissions(self):
        # Ensure users aren't allowed to make recompile requests of behalf
        # of other users.
        original = self.Comment(reddit_session=self.r, 
                                author=self.Author("Author-1"))
        self.r._get_sub_comment = original
        body = "--recompile {link}".format(link=original.permalink)
        new = self.Message(body=body, reddit_session=self.r, 
                           author=self.Author("Author-2"))
        cb.process_unread(new, self.r)
        self.assertFalse(original._replied_to)
        self.assertTrue(new._replied_to)
        
    def tearDown(self):
        reload(cb)
        cb.LOG_FILE = LOG_FILE
        
class TestDetectSpam(unittest.TestCase):
    
    class Comment(object):
        def __init__(self):
            self.author = ''
            self.permalink = ''
    
    def create_reply(self, spam):
        details = {
            'output': spam,
            'source': '',
            'stderr': ''
        }
        text = "Output:\n\n\n{}\n".format(spam)
        reply = cb.CompiledReply(text, details)
        reply.parent_comment = self.Comment()
        return reply
        
    def test_line_breaks(self):
        spam = "    \n" * (cb.LINE_LIMIT + 1)
        reply = self.create_reply(spam)
        self.assertIn("Excessive line breaks", reply.detect_spam())
        
    def test_char_limit(self):
        spam = "a" * (cb.CHAR_LIMIT + 1)
        reply = self.create_reply(spam)
        self.assertIn("Excessive character count", reply.detect_spam())
       
    def test_spam_phrases(self):
        spam = "Spam Phrase"
        cb.SPAM_PHRASES.append(spam)
        reply = self.create_reply(spam)
        self.assertIn("Spam phrase detected", reply.detect_spam())
        
    def test_permission_denied(self):
        spam = ""
        reply = self.create_reply(spam)
        reply.compile_details['stderr'] = "'rm -rf /*': Permission denied"
        self.assertIn("Illegal system call detected", reply.detect_spam())

     
if __name__ == "__main__":
    unittest.main(exit=False)

########NEW FILE########
