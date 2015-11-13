__FILENAME__ = automoderator
from datetime import datetime, timedelta
import logging, logging.config
from time import sleep, time

import HTMLParser
import praw
import re2 as re
import yaml
from requests.exceptions import HTTPError
from sqlalchemy.sql import and_
from sqlalchemy.orm.exc import NoResultFound

from models import cfg_file, path_to_cfg, session
from models import Log, StandardCondition, Subreddit

# global reddit session
r = None

class Condition(object):
    _defaults = {'reports': None,
                 'is_reply': None,
                 'ignore_blockquotes': False,
                 'priority': 0,
                 'action': None,
                 'comment': None,
                 'modmail': None,
                 'modmail_subject': 'AutoModerator notification',
                 'message': None,
                 'message_subject': 'AutoModerator notification',
                 'link_flair_text': '',
                 'link_flair_class': '',
                 'user_flair_text': '',
                 'user_flair_class': '',
                 'user_conditions': {},
                 'modifiers': []}

    _match_targets = ['link_id', 'user', 'title', 'domain', 'url', 'body',
                      'media_user', 'media_title', 'media_description',
                      'author_flair_text', 'author_flair_css_class',
                      'link_title', 'link_url']
    _match_modifiers = {'full-exact': u'^{0}$',
                        'full-text': ur'^\W*{0}\W*$',
                        'includes': u'{0}',
                        'includes-word': ur'(?:^|\W|\b){0}(?:$|\W|\b)',
                        'starts-with': u'^{0}',
                        'ends-with': u'{0}$'}
    _modifier_defaults = {'link_id': 'full-exact',
                          'user': 'full-exact',
                          'domain': 'full-exact',
                          'url': 'includes',
                          'media_user': 'full-exact',
                          'author_flair_text': 'full-exact',
                          'author_flair_css_class': 'full-exact',
                          'link_url': 'includes'}

    _standard_cache = {}
    _standard_rows = None

    @classmethod
    def update_standards(cls):
        standards = session.query(StandardCondition).all()
        if standards != cls._standard_rows:
            cls._standard_cache = {cond.name.lower(): yaml.safe_load(cond.yaml)
                                   for cond in standards}
            cls._standard_rows = standards
            return True
        return False

    @classmethod
    def get_standard_condition(cls, name):
        return cls._standard_cache.get(name.lower(), dict())

    @property
    def requests_required(self):
        # all things that will require an additional request
        reqs = sum(1 for i in
                    (self.action, self.user_conditions, self.comment,
                     self.modmail, self.message,
                     (self.user_flair_text or self.user_flair_class),
                     (self.link_flair_text or self.link_flair_class))
                    if i)
        # one extra request for distinguishing a comment
        if self.comment:
            reqs += 1

        return reqs

    def __init__(self, values):
        values = lowercase_keys_recursively(values)

        self.yaml = yaml.dump(values)

        # anything not defined in the "values" dict will be defaulted
        init = self._defaults.copy()

        # inherit from standard condition if they specified one
        if 'standard' in values:
            init.update(Condition.get_standard_condition(values['standard']))

        init.update(values)

        # convert the dict to attributes
        self.__dict__.update(init)

        # set match target/pattern definitions
        self.match_patterns = {}
        self.match_success = {}
        self.match_flags = {}
        match_fields = set()
        for key in [k for k in init
                    if k in self._match_targets or '+' in k]:
            if isinstance(self.modifiers, dict):
                modifiers = self.modifiers.get(key, [])
            else:
                modifiers = self.modifiers
            self.match_patterns[key] = self.get_pattern(key, modifiers)

            if 'inverse' in modifiers:
                self.match_success[key] = False
            else:
                self.match_success[key] = True

            # default match flags
            self.match_flags[key] = re.DOTALL|re.UNICODE
            if 'case-sensitive' not in modifiers:
                self.match_flags[key] |= re.IGNORECASE

            for field in key.split('+'):
                match_fields.add(field)
        
        # if type wasn't defined, set based on fields being matched against
        if not getattr(self, 'type', None):
            if (len(match_fields) > 0 and 
                all(f in ('title', 'domain', 'url',
                           'media_user', 'media_title', 'media_description')
                     for f in match_fields)):
                self.type = 'submission'
            else:
                self.type = 'both'


    def get_pattern(self, subject, modifiers):
        # cast to lists, so we're not splitting a single string
        if not isinstance(getattr(self, subject), list):
            setattr(self, subject, [getattr(self, subject)])
        if not isinstance(modifiers, list):
            modifiers = list(modifiers.split(' '))

        # cast all elements to strings in case of any numbers
        values = [unicode(val) for val in getattr(self, subject)]

        if 'regex' not in modifiers:
            values = [re.escape(val) for val in values]
        value_str = u'({0})'.format('|'.join(values))

        # check if they defined a match modifier
        for mod in self._match_modifiers:
            if mod in modifiers:
                match_mod = mod
                break
        else:
            # handle subdomains for domain checks
            if subject == 'domain':
                value_str = ur'(?:.*?\.)?' + value_str

            match_mod = self._modifier_defaults.get(subject, 'includes-word')

        return self._match_modifiers[match_mod].format(value_str)

    def check_item(self, item):
        """Checks an item against the condition.
        
        Returns True if the condition is satisfied, False otherwise.
        """
        # check number of reports if necessary
        if self.reports and item.num_reports < self.reports:
            return False

        # check whether it's a reply or top-level comment if necessary
        if self.is_reply is not None and self.is_reply != is_reply(item):
            return False

        html_parser = HTMLParser.HTMLParser()
        match = None
        approve_shadowbanned = False
        for subject in self.match_patterns:
            sources = set(subject.split('+'))
            for source in sources:
                approve_shadowbanned = False
                if source == 'user' and item.author:
                    string = item.author.name
                    # allow approving shadowbanned if it's a username match
                    approve_shadowbanned = True
                elif source == 'link_id':
                    # trim off the 't3_'
                    string = getattr(item, 'link_id', '')[3:]
                elif (source == 'body' and
                        isinstance(item, praw.objects.Submission)):
                    string = item.selftext
                elif (source == 'url' and
                        getattr(item, 'is_self', False)):
                    # get rid of the url value for self-posts
                    string = ''
                elif (source.startswith('media_') and
                        getattr(item, 'media', None)):
                    try:
                        if source == 'media_user':
                            string = item.media['oembed']['author_name']
                        elif source == 'media_title':
                            string = item.media['oembed']['title']
                        elif source == 'media_description':
                            string = item.media['oembed']['description']
                    except KeyError:
                        string = ''
                else:
                    string = getattr(item, source, '')

                if not string:
                    string = ''

                string = html_parser.unescape(string)

                # remove blockquotes if ignore_blockquotes is enabled
                if source == 'body' and self.ignore_blockquotes:
                    string = '\n'.join(line for line in string.splitlines()
                                        if not line.startswith('>') and
                                           len(line) > 0)

                match = re.search(self.match_patterns[subject],
                                  string,
                                  self.match_flags[subject])

                if match:
                    break

            if bool(match) != self.match_success[subject]:
                return False

        # check user conditions
        if not self.check_user_conditions(item):
            return False

        # matched, perform any actions
        # don't approve shadowbanned users' posts except in special cases
        if (self.action != 'approve' or
                not self.check_shadowbanned or
                not user_is_shadowbanned(item.author) or
                approve_shadowbanned):
            self.execute_actions(item, match)

        return True

    def check_user_conditions(self, item):
        """Checks an item's author against the defined requirements."""
        # if no user conditions are set, no need to check at all
        if not self.user_conditions:
            return True

        must_satisfy = self.user_conditions.get('must_satisfy', 'all')
        user = item.author

        for attr, compare in self.user_conditions.iteritems():
            if attr == 'must_satisfy':
                continue

            # extract the comparison operator
            operator = '='
            if not isinstance(compare, bool):
                operator_regex = '^(==?|<|>)'
                match = re.search(operator_regex, compare)
                if match:
                    operator = match.group(1)
                    compare = compare[len(operator):].strip()
                    if operator == '==':
                        operator = '='

            # convert rank to a numerical value
            if attr == 'rank':
                rank_values = {'user': 0, 'contributor': 1, 'moderator': 2}
                compare = rank_values[compare]

            if user:
                if attr == 'rank':
                    value = rank_values[get_user_rank(user, item.subreddit)]
                elif attr == 'account_age':
                    user_date = datetime.utcfromtimestamp(user.created_utc)
                    value = (datetime.utcnow() - user_date).days
                elif attr == 'combined_karma':
                    value = user.link_karma + user.comment_karma
                else:
                    value = getattr(user, attr, 0)
            else:
                value = 0
                
            if operator == '<':
                result = int(value) < int(compare)
            elif operator == '>':
                result = int(value) > int(compare)
            elif operator == '=':
                result = int(value) == int(compare)

            if result and must_satisfy == 'any':
                return True
            elif not result and must_satisfy == 'all':
                return False

        # if we reached this point, success depends on if this is any/all
        if must_satisfy == 'any' and not result:
            return False
        return True

    def execute_actions(self, item, match):
        """Performs the action(s) for the condition.
        
        Also sends any comment/messages (if set) and creates a log entry.
        """
        if self.action or self.comment or self.modmail or self.message:
            log_actions = [self.action]
        else:
            log_actions = []

        # perform the action
        if self.action == 'remove':
            item.remove(False)
        elif self.action == 'spam':
            item.remove(True)
        elif self.action == 'approve':
            item.approve()
        elif self.action == 'report':
            item.report()

        # set flairs
        if (isinstance(item, praw.objects.Submission) and 
                (self.link_flair_text or self.link_flair_class)):
            text = replace_placeholders(self.link_flair_text, item, match)
            css_class = replace_placeholders(self.link_flair_class, item, match)
            item.set_flair(text, css_class.lower())
            item.link_flair_text = text
            item.link_flair_css_class = css_class.lower()
            log_actions.append('link_flair')
        if (self.user_flair_text or self.user_flair_class):
            text = replace_placeholders(self.user_flair_text, item, match)
            css_class = replace_placeholders(self.user_flair_class, item, match)
            item.subreddit.set_flair(item.author, text, css_class.lower())
            item.author_flair_text = text
            item.author_flair_css_class = css_class.lower()
            log_actions.append('user_flair')

        if self.comment:
            comment = self.build_message(self.comment, item, match,
                                         disclaimer=True)
            if isinstance(item, praw.objects.Submission):
                response = item.add_comment(comment)
            elif isinstance(item, praw.objects.Comment):
                response = item.reply(comment)
            response.distinguish()

        if self.modmail:
            message = self.build_message(self.modmail, item, match,
                                         permalink=True)
            subject = replace_placeholders(self.modmail_subject, item, match)
            r.send_message('/r/'+item.subreddit.display_name, subject, message)

        if self.message and item.author:
            message = self.build_message(self.message, item, match,
                                         disclaimer=True, permalink=True)
            subject = replace_placeholders(self.message_subject, item, match)
            r.send_message(item.author.name, subject, message)

        log_entry = Log()
        log_entry.item_fullname = item.name
        log_entry.condition_yaml = self.yaml
        log_entry.datetime = datetime.utcnow()

        for entry in log_actions:
            log_entry.action = entry
            session.add(log_entry)

        session.commit()

        item_time = datetime.utcfromtimestamp(item.created_utc)
        logging.info('Matched {0}, actions: {1} (age: {2})'
                     .format(get_permalink(item).encode('ascii', 'ignore'),
                             log_actions,
                             datetime.utcnow() - item_time))

    def build_message(self, text, item, match,
                      disclaimer=False, permalink=False):
        """Builds a message/comment for the bot to post or send."""
        message = text
        if disclaimer:
            message = message+'\n\n'+cfg_file.get('reddit', 'disclaimer')
        if permalink and '{{permalink}}' not in message:
            message = '{{permalink}}\n\n'+message
        message = replace_placeholders(message, item, match)

        return message


def update_from_wiki(subreddit, requester):
    """Updates conditions from the subreddit's wiki."""
    global r
    username = cfg_file.get('reddit', 'username')

    try:
        page = subreddit.get_wiki_page(cfg_file.get('reddit', 'wiki_page_name'))
    except Exception:
        send_error_message(requester, subreddit.display_name,
            'The wiki page could not be accessed. Please ensure the page '
            'http://www.reddit.com/r/{0}/wiki/{1} exists and that {2} '
            'has the "wiki" mod permission to be able to access it.'
            .format(subreddit.display_name,
                    cfg_file.get('reddit', 'wiki_page_name'),
                    username))
        return False

    html_parser = HTMLParser.HTMLParser()
    page_content = html_parser.unescape(page.content_md)

    # check that all the conditions are valid yaml
    condition_defs = yaml.safe_load_all(page_content)
    condition_num = 1
    try:
        for cond_def in condition_defs:
            condition_num += 1
    except Exception as e:
        indented = ''
        for line in str(e).split('\n'):
            indented += '    {0}\n'.format(line)
        send_error_message(requester, subreddit.display_name,
            'Error when reading conditions from wiki - '
            'Syntax invalid in section #{0}:\n\n{1}'
            .format(condition_num, indented))
        return False

    # reload and actually process the conditions
    condition_defs = yaml.safe_load_all(page_content)
    condition_num = 1
    kept_sections = []
    for cond_def in condition_defs:
        # ignore any non-dict sections (can be used as comments, etc.)
        if not isinstance(cond_def, dict):
            continue

        cond_def = lowercase_keys_recursively(cond_def)

        try:
            check_condition_valid(cond_def)
        except ValueError as e:
            send_error_message(requester, subreddit.display_name,
                'Invalid condition in section #{0} - {1}'
                .format(condition_num, e))
            return False

        # create a condition for final checks
        condition = Condition(cond_def)

        # test to make sure that the final regex(es) are valid
        for pattern in condition.match_patterns.values():
            try:
                re.compile(pattern)
            except Exception as e:
                send_error_message(requester, subreddit.display_name,
                    'Generated an invalid regex from section #{0} - {1}'
                    .format(condition_num, e))
                return False

        condition_num += 1
        kept_sections.append(cond_def)

    # Update the subreddit, or add it if necessary
    try:
        db_subreddit = (session.query(Subreddit)
                       .filter(Subreddit.name == subreddit.display_name.lower())
                       .one())
    except NoResultFound:
        db_subreddit = Subreddit()
        db_subreddit.name = subreddit.display_name.lower()
        db_subreddit.last_submission = datetime.utcnow() - timedelta(days=1)
        db_subreddit.last_spam = datetime.utcnow() - timedelta(days=1)
        db_subreddit.last_comment = datetime.utcnow() - timedelta(days=1)
        session.add(db_subreddit)

    db_subreddit.conditions_yaml = page_content
    session.commit()

    r.send_message(requester,
                   '{0} conditions updated'.format(username),
                   "{0}'s conditions were successfully updated for /r/{1}"
                   .format(username, subreddit.display_name))
    return True


def lowercase_keys_recursively(subject):
    """Recursively lowercases all keys in a dict."""
    lowercased = dict()
    for key, val in subject.iteritems():
        if isinstance(val, dict):
            val = lowercase_keys_recursively(val)
        lowercased[key.lower()] = val

    return lowercased


def check_condition_valid(cond):
    """Checks if a condition defined on a wiki page is valid."""

    validate_values_not_empty(cond)

    if 'standard' in cond:
        if not Condition.get_standard_condition(cond['standard']):
            raise ValueError('Invalid standard condition: `{0}`'
                             .format(cond['standard']))
        cond.update(Condition.get_standard_condition(cond['standard']))

    validate_type(cond, 'user_conditions', dict)
    validate_keys(cond)
    validate_type(cond, 'is_reply', bool)
    validate_type(cond, 'ignore_blockquotes', bool)
    validate_type(cond, 'reports', int)
    validate_type(cond, 'priority', int)
    validate_type(cond, 'comment', basestring)
    validate_type(cond, 'modmail', basestring)
    validate_type(cond, 'modmail_subject', basestring)
    validate_type(cond, 'message', basestring)
    validate_type(cond, 'message_subject', basestring)

    validate_value_in(cond, 'action', ('approve', 'remove', 'spam', 'report'))
    validate_value_in(cond, 'type', ('submission', 'comment', 'both'))

    validate_modifiers(cond)

    # validate user conditions
    if 'user_conditions' in cond:
        user_conds = cond['user_conditions']
        operator_regex = '((==?|<|>) )?'
        oper_int_regex = '^'+operator_regex+'-?\d+$'
        oper_rank_regex = '^'+operator_regex+'(user|contributor|moderator)$'

        validate_regex(user_conds, 'account_age', oper_int_regex)
        validate_regex(user_conds, 'comment_karma', oper_int_regex)
        validate_regex(user_conds, 'link_karma', oper_int_regex)
        validate_regex(user_conds, 'combined_karma', oper_int_regex)
        validate_type(user_conds, 'is_gold', bool)
        validate_regex(user_conds, 'rank', oper_rank_regex)

        validate_value_in(user_conds, 'must_satisfy', ('any', 'all'))


def validate_values_not_empty(check):
    """Checks (recursively) that no values in the dict are empty."""
    for key, val in check.iteritems():
        if isinstance(val, dict):
            validate_values_not_empty(val)
        elif (val is None or
              (isinstance(val, (basestring, list)) and len(val) == 0)):
            raise ValueError('`{0}` set to an empty value'.format(key))


def validate_keys(check):
    """Checks if all the keys in the condition are valid."""
    # check top-level keys
    valid_keys = set(Condition._match_targets +
                     Condition._defaults.keys() + 
                     ['standard', 'type'])
    for key in check:
        if key in valid_keys:
            continue

        # multiple subjects
        if ('+' in key and
                all(t in Condition._match_targets
                     for t in key.split('+'))):
            continue

        raise ValueError('Invalid variable: `{0}`'.format(key))

    # check user_conditions keys
    if 'user_conditions' in check:
        valid_keys = set(['account_age', 'combined_karma', 'comment_karma',
                          'is_gold', 'link_karma', 'must_satisfy', 'rank'])
        for key in check['user_conditions']:
            if key not in valid_keys:
                raise ValueError('Invalid user_conditions variable: `{0}`'
                                 .format(key))

    # check modifiers keys
    if 'modifiers' in check and isinstance(check['modifiers'], dict):
        for key in check['modifiers']:
            if key not in check.keys():
                raise ValueError('Invalid modifiers variable: `{0}` - '
                                 'Check for typos and ensure all modifiers '
                                 'correspond to a defined match subject.'
                                 .format(key))


def validate_modifiers(check):
    """Checks that all modifier definitions in the condition are valid."""
    if 'modifiers' not in check:
        return

    match_types = Condition._match_modifiers.keys()
    valid_modifiers = set(match_types + ['case-sensitive', 'inverse', 'regex'])

    if isinstance(check['modifiers'], dict):
        to_validate = check['modifiers'].values()
    else:
        to_validate = list((check['modifiers'],))

    for mod_list in to_validate:
        # convert to a list if it's a string
        if not isinstance(mod_list, list):
            mod_list = mod_list.split(' ')

        # make sure all modifiers are valid choices
        for mod in mod_list:
            if mod not in valid_modifiers:
                raise ValueError('Invalid modifier: `{0}`'.format(mod))

        # check that they specified no more than one match type modifier
        if sum(1 for mod in mod_list if mod in match_types) > 1:
            raise ValueError('More than one match type modifier (`{0}`) '
                             'specified.'.format(', '.join(match_types)))


def validate_value_in(check, key, valid_vals):
    """Validates that a dict value is in a list of valid choices."""
    if key not in check:
        return

    if check[key] not in valid_vals:
        raise ValueError('Invalid {0}: {1}'.format(key, check[key]))


def validate_type(check, key, req_type):
    """Validates that a dict value is of the correct type."""
    if key not in check:
        return

    if req_type == int:
        try:
            int(str(check[key]))
        except ValueError:
            raise ValueError('{0} must be an integer'.format(key))
    else:
        if not isinstance(check[key], req_type):
            raise ValueError('{0} must be {1}'.format(key, req_type))


def validate_regex(check, key, pattern):
    """Validates that a dict value matches a regex."""
    if key not in check:
        return

    if not re.match(pattern, check[key]):
        raise ValueError('Invalid {0}: {1}'.format(key, check[key]))


def send_error_message(user, sr_name, error):
    """Sends an error message to the user if a wiki update failed."""
    global r
    r.send_message(user,
                   'Error updating from wiki in /r/{0}'.format(sr_name),
                   '### Error updating from [wiki configuration in /r/{0}]'
                   '(http://www.reddit.com/r/{0}/wiki/{1}):\n\n---\n\n'
                   '{2}\n\n---\n\n[View configuration documentation](https://'
                   'github.com/Deimos/AutoModerator/wiki/Wiki-Configuration)'
                   .format(sr_name,
                           cfg_file.get('reddit', 'wiki_page_name'),
                           error))


def process_messages():
    """Processes the bot's messages looking for invites/commands."""
    global r
    stop_time = int(cfg_file.get('reddit', 'last_message'))
    owner_username = cfg_file.get('reddit', 'owner_username')
    new_last_message = None
    update_srs = set()
    invite_srs = set()
    sleep_after = False

    logging.debug('Checking messages')

    try:
        for message in r.get_inbox():
            if int(message.created_utc) <= stop_time:
                break

            if message.was_comment:
                continue

            if not new_last_message:
                new_last_message = int(message.created_utc)

            # if it's a subreddit invite
            if (not message.author and
                    message.subject.startswith('invitation to moderate /r/')):
                invite_srs.add(message.subreddit.display_name.lower())
            elif message.body.strip().lower() == 'update':
                # handle if they put in something like '/r/' in the subject
                if '/' in message.subject:
                    sr_name = message.subject[message.subject.rindex('/')+1:]
                else:
                    sr_name = message.subject

                if (sr_name.lower(), message.author.name) in update_srs:
                    continue

                try:
                    subreddit = r.get_subreddit(sr_name)
                    if (message.author.name == owner_username or
                            message.author in subreddit.get_moderators()):
                        update_srs.add((sr_name.lower(), message.author.name))
                    else:
                        send_error_message(message.author, sr_name,
                            'You do not moderate /r/{0}'.format(sr_name))
                except HTTPError as e:
                    send_error_message(message.author, sr_name,
                        'Unable to access /r/{0}'.format(sr_name))
            elif (message.subject.strip().lower() == 'sleep' and
                  message.author.name == owner_username):
                sleep_after = True

        # accept subreddit invites
        for subreddit in invite_srs:
            try:
                # workaround for praw clearing mod sub list on accept
                mod_subs = r.user._mod_subs
                r.accept_moderator_invite(subreddit)
                r.user._mod_subs = mod_subs
                r.user._mod_subs[subreddit] = r.get_subreddit(subreddit)
                logging.info('Accepted mod invite in /r/{0}'
                             .format(subreddit))
            except praw.errors.InvalidInvite:
                pass

        # do requested updates from wiki pages
        updated_srs = []
        for subreddit, sender in update_srs:
            if update_from_wiki(r.get_subreddit(subreddit),
                                r.get_redditor(sender)):
                updated_srs.append(subreddit)
                logging.info('Updated from wiki in /r/{0}'.format(subreddit))
            else:
                logging.info('Error updating from wiki in /r/{0}'
                             .format(subreddit))

        if sleep_after:
            logging.info('Sleeping for 10 seconds')
            sleep(10)
            logging.info('Sleep ended, resuming')

    except Exception as e:
        logging.error('ERROR: {0}'.format(e))
        raise
    finally:
        # update cfg with new last_message value
        if new_last_message:
            cfg_file.set('reddit', 'last_message', str(new_last_message))
            cfg_file.write(open(path_to_cfg, 'w'))

    return updated_srs


def replace_placeholders(string, item, match):
    """Replaces placeholders in the string."""
    if isinstance(item, praw.objects.Comment):
        string = string.replace('{{body}}', item.body)
        string = string.replace('{{kind}}', 'comment')
    else:
        string = string.replace('{{body}}', item.selftext)
        string = string.replace('{{kind}}', 'submission')
    string = string.replace('{{domain}}', getattr(item, 'domain', ''))
    string = string.replace('{{permalink}}', get_permalink(item))
    string = string.replace('{{subreddit}}', item.subreddit.display_name)
    if isinstance(item, praw.objects.Comment):
        string = string.replace('{{title}}', item.link_title)
    else:
        string = string.replace('{{title}}', item.title)
    string = string.replace('{{url}}', getattr(item, 'url', ''))
    if item.author:
        string = string.replace('{{user}}', item.author.name)
    else:
        string = string.replace('{{user}}', '[deleted]')

    if getattr(item, 'media', None):
        oembed_mapping = {'{{media_user}}': 'author_name',
                          '{{media_title}}': 'title',
                          '{{media_description}}': 'description'}
        for placeholder, source in oembed_mapping.iteritems():
            if placeholder in string:
                try:
                    string = string.replace(placeholder,
                                            item.media['oembed'][source])
                except KeyError:
                    pass

    # replace any {{match_##}} with the corresponding match groups
    string = re.sub(r'\{\{match-(\d+)\}\}', r'\\\1', string)
    if match:
        string = match.expand(string)

    return string


def check_items(queue, items, stop_time, sr_dict, cond_dict):
    """Checks the items generator for any matching conditions."""
    item_count = 0
    start_time = time()
    last_updates = {}

    logging.debug('Checking {0} queue'.format(queue))

    bot_username = cfg_file.get('reddit', 'username')
    for item in items:
        # skip non-removed (reported) items when checking spam
        if queue == 'spam' and not item.banned_by:
            continue

        # never check the bot's own posts
        if item.author and item.author.name.lower() == bot_username.lower():
            continue

        item_time = datetime.utcfromtimestamp(item.created_utc)
        if (item_time < stop_time and
                (queue != 'submission' or not item.approved_by)):
            break

        sr_name = item.subreddit.display_name.lower()
        subreddit = sr_dict[sr_name]
        conditions = cond_dict[sr_name][queue]

        if (queue != 'report' and
                (queue != 'submission' or not item.approved_by) and
                sr_name not in last_updates):
            last_updates[sr_name] = item_time

        # don't need to check for shadowbanned unless we're in spam
        # and the subreddit doesn't exclude shadowbanned posts
        if queue == 'spam' and not subreddit.exclude_banned_modqueue:
            for condition in conditions:
                condition.check_shadowbanned = True
        else:
            for condition in conditions:
                condition.check_shadowbanned = False

        item_count += 1

        logging.debug('Checking item %s', get_permalink(item))

        try:
            # check removal conditions, stop checking if any matched
            if check_conditions(subreddit, item,
                                [c for c in conditions
                                 if c.action in ('remove', 'spam')],
                                stop_after_match=True):
                continue

            # check all other conditions
            check_conditions(subreddit, item,
                             [c for c in conditions
                              if c.action not in ('remove', 'spam')])
        except (praw.errors.ModeratorRequired,
                praw.errors.ModeratorOrScopeRequired,
                HTTPError) as e:
            if not isinstance(e, HTTPError) or e.response.status_code == 403:
                logging.error('Permissions error in /r/{0}'
                              .format(subreddit.name))
            raise
        except Exception as e:
            logging.error('ERROR: {0}'.format(e))

    # Update "last_" entries in db
    for sr in last_updates:
        setattr(sr_dict[sr], 'last_'+queue, last_updates[sr])
    session.commit()

    logging.debug('Checked {0} items in {1}'
                 .format(item_count, elapsed_since(start_time)))


def check_conditions(subreddit, item, conditions, stop_after_match=False):
    """Checks an item against a list of conditions.

    Returns True if any conditions matched, False otherwise.
    """
    bot_username = cfg_file.get('reddit', 'username')

    if isinstance(item, praw.objects.Submission):
        conditions = [c for c in conditions
                          if c.type in ('submission', 'both')]
    elif isinstance(item, praw.objects.Comment):
        conditions = [c for c in conditions
                          if c.type in ('comment', 'both')]

    # get what's already been performed out of the log
    performed_actions = set()
    performed_yaml = set()
    log_entries = (session.query(Log)
                          .filter(Log.item_fullname == item.name)
                          .all())
    for entry in log_entries:
        performed_actions.add(entry.action)
        performed_yaml.add(entry.condition_yaml)

    # sort the conditions by desc priority, and then by required requests
    conditions.sort(key=lambda c: c.requests_required)
    conditions.sort(key=lambda c: c.priority, reverse=True)

    any_matched = False
    for condition in conditions:
        # never remove anything if it's been approved by another mod
        if (condition.action in ('remove', 'spam') and
                item.approved_by and
                item.approved_by.name.lower() != bot_username.lower()):
            continue

        # don't bother checking condition if this action has already been done
        if condition.action in performed_actions:
                continue

        # don't send repeat messages for the same item
        if ((condition.comment or condition.modmail or condition.message) and
            condition.yaml in performed_yaml):
                continue

        # don't overwrite existing flair
        if ((condition.link_flair_text or condition.link_flair_class) and
                isinstance(item, praw.objects.Submission) and
                (item.link_flair_text or item.link_flair_css_class)):
            continue
        if ((condition.user_flair_text or condition.user_flair_class) and
                (item.author_flair_text or item.author_flair_css_class)):
            continue

        try:
            start_time = time()
            match = condition.check_item(item)
            if match:
                performed_actions.add(condition.action)
                performed_yaml.add(condition.yaml)

            logging.debug('{0}\n  Result {1} in {2}'
                          .format(condition.yaml,
                                  match,
                                  elapsed_since(start_time)))
        except (praw.errors.ModeratorRequired,
                praw.errors.ModeratorOrScopeRequired,
                HTTPError) as e:
            raise
        except Exception as e:
            logging.error('ERROR: {0}\n{1}'.format(e, condition.yaml))
            match = False

        any_matched = (any_matched or match)
        if stop_after_match and any_matched:
            break

    return any_matched


def filter_conditions(conditions, queue):
    """Filters a list of conditions based on the queue's needs."""
    if queue == 'spam':
        return [c for c in conditions
                if c.reports < 1 and
                   c.action != 'report']
    elif queue == 'report':
        return [c for c in conditions
                if c.action != 'report' and
                   (c.action != 'approve' or c.reports > 0)]
    elif queue == 'submission':
        return [c for c in conditions
                if c.type in ('both', 'submission') and
                   c.reports < 1 and
                   c.action != 'approve']
    elif queue == 'comment':
        return [c for c in conditions
                if c.type in ('both', 'comment') and
                   c.reports < 1 and
                   c.action != 'approve']


def get_user_rank(user, subreddit):
    """Returns the user's rank in the subreddit."""
    sr_name = subreddit.display_name.lower()

    # fetch mod/contrib lists if necessary
    cached = False
    if sr_name in get_user_rank.moderator_cache:
        cache_age = datetime.utcnow() - get_user_rank.cache_time[sr_name] 
        if cache_age < timedelta(hours=1):
            cached = True

    if not cached:
        get_user_rank.cache_time[sr_name] = datetime.utcnow()

        mod_list = set()
        for mod in subreddit.get_moderators():
            mod_list.add(mod.name)
        get_user_rank.moderator_cache[sr_name] = mod_list

        contrib_list = set()
        try:
            for contrib in subreddit.get_contributors():
                contrib_list.add(contrib.name)
        except HTTPError as e:
            if e.response.status_code != 404:
                raise
        get_user_rank.contributor_cache[sr_name] = contrib_list

    if user.name in get_user_rank.moderator_cache[sr_name]:
        return 'moderator'
    elif user.name in get_user_rank.contributor_cache[sr_name]:
        return 'contributor'
    else:
        return 'user'
get_user_rank.moderator_cache = {}
get_user_rank.contributor_cache = {}
get_user_rank.cache_time = {}


def user_is_shadowbanned(user):
    """Returns True if the user is shadowbanned."""
    global r

    try: # try to get user overview
        list(user.get_overview(limit=1))
    except HTTPError as e:
        # if that failed, they're probably shadowbanned
        if e.response.status_code == 404:
            return True
        else:
            raise

    return False


def get_permalink(item):
    """Returns the permalink for the item."""
    if isinstance(item, praw.objects.Submission):
        return item.permalink
    elif isinstance(item, praw.objects.Comment):
        permalink = ('http://www.reddit.com/r/{0}/comments/{1}/-/{2}'
                     .format(item.subreddit.display_name,
                             item.link_id.split('_')[1],
                             item.id))
        if is_reply(item):
            permalink += '?context=5'
        return permalink


def is_reply(item):
    """Returns True if the item is a reply (not a top-level comment)."""
    if not isinstance(item, praw.objects.Comment):
        return False

    if item.parent_id.startswith('t1_'):
        return True
    return False


def elapsed_since(start_time):
    """Returns a timedelta for how much time has passed since start_time."""
    elapsed = time() - start_time
    return timedelta(seconds=elapsed)


def build_multireddit_groups(subreddits):
    """Splits a subreddit list into groups if necessary (due to url length)."""
    multireddits = []
    current_multi = []
    current_len = 0
    for sub in subreddits:
        if current_len > 4700:
            multireddits.append(current_multi)
            current_multi = []
            current_len = 0
        current_multi.append(sub)
        current_len += len(sub) + 1
    multireddits.append(current_multi)

    return multireddits


def check_queues(queue_funcs, sr_dict, cond_dict):
    """Checks all the queues for new items to process."""
    global r

    for queue in queue_funcs:
        subreddits = [s for s in sr_dict if len(cond_dict[s][queue]) > 0]
        if len(subreddits) == 0:
            continue

        multireddits = build_multireddit_groups(subreddits)

        # fetch and process the items for each multireddit
        for multi in multireddits:
            if queue == 'report':
                limit = cfg_file.get('reddit', 'report_backlog_limit_hours')
                stop_time = datetime.utcnow() - timedelta(hours=int(limit))
            else:
                stop_time = max(getattr(sr, 'last_'+queue)
                                 for sr in sr_dict.values()
                                 if sr.name in multi)

            queue_subreddit = r.get_subreddit('+'.join(multi))
            if queue_subreddit:
                queue_func = getattr(queue_subreddit, queue_funcs[queue])
                items = queue_func(limit=None)
                check_items(queue, items, stop_time, sr_dict, cond_dict)


def update_conditions_for_sr(cond_dict, queues, subreddit):
    cond_dict[subreddit.name] = {}
    conditions = [Condition(d)
                  for d in yaml.safe_load_all(subreddit.conditions_yaml)
                  if isinstance(d, dict)]
    for queue in queues:
        cond_dict[subreddit.name][queue] = filter_conditions(conditions, queue)


def load_all_conditions(sr_dict, queues):
    cond_dict = {}
    for sr in sr_dict.values():
        update_conditions_for_sr(cond_dict, queues, sr)

    return cond_dict


def get_enabled_subreddits(reload_mod_subs=True):
    global r

    subreddits = (session.query(Subreddit)
                         .filter(Subreddit.enabled == True)
                         .all())

    if reload_mod_subs:
        r.user._mod_subs = None
        logging.info('Getting list of moderated subreddits')
        modded_subs = r.user.get_cached_moderated_reddits().keys()
    else:
        modded_subs = r.user._mod_subs.keys()

    # get rid of any subreddits the bot doesn't moderate
    sr_dict = {sr.name.lower(): sr
               for sr in subreddits
               if sr.name.lower() in modded_subs}

    return sr_dict


def main():
    global r
    logging.config.fileConfig(path_to_cfg)
    re.set_fallback_notification(re.FALLBACK_EXCEPTION)

    # which queues to check and the function to call
    queue_funcs = {'report': 'get_reports',
                   'spam': 'get_mod_queue',
                   'submission': 'get_new',
                   'comment': 'get_comments'}

    while True:
        try:
            r = praw.Reddit(user_agent=cfg_file.get('reddit', 'user_agent'))
            logging.info('Logging in as {0}'
                         .format(cfg_file.get('reddit', 'username')))
            r.login(cfg_file.get('reddit', 'username'),
                    cfg_file.get('reddit', 'password'))
            sr_dict = get_enabled_subreddits()
            Condition.update_standards()
            cond_dict = load_all_conditions(sr_dict, queue_funcs.keys())
            break
        except Exception as e:
            logging.error('ERROR: {0}'.format(e))

    reports_mins = int(cfg_file.get('reddit', 'reports_check_period_mins'))
    reports_check_period = timedelta(minutes=reports_mins)
    last_reports_check = time()

    while True:
        try:
            # if the standard conditions have changed, reinit all conditions
            if Condition.update_standards():
                logging.info('Updating standard conditions from database')
                cond_dict = load_all_conditions(sr_dict, queue_funcs.keys())

            # check reports if past checking period
            if elapsed_since(last_reports_check) > reports_check_period:
                last_reports_check = time()
                check_queues({'report': queue_funcs['report']},
                             sr_dict, cond_dict)
                             
            check_queues({q: queue_funcs[q]
                          for q in queue_funcs
                          if q != 'report'},
                         sr_dict, cond_dict)

            updated_srs = process_messages()
            if updated_srs:
                if any(sr not in sr_dict for sr in updated_srs):
                    sr_dict = get_enabled_subreddits(reload_mod_subs=True)
                else:
                    sr_dict = get_enabled_subreddits(reload_mod_subs=False)
                for sr in updated_srs:
                    update_conditions_for_sr(cond_dict,
                                             queue_funcs.keys(),
                                             sr_dict[sr])
        except (praw.errors.ModeratorRequired,
                praw.errors.ModeratorOrScopeRequired,
                HTTPError) as e:
            if not isinstance(e, HTTPError) or e.response.status_code == 403:
                logging.info('Re-initializing due to {0}'.format(e))
                sr_dict = get_enabled_subreddits()
        except KeyboardInterrupt:
            raise
        except Exception as e:
            logging.error('ERROR: {0}'.format(e))
            session.rollback()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = maintenance
"""Run occasionally via cron for maintenance tasks."""

from datetime import datetime, timedelta
import praw
from models import cfg_file, Log, session, Subreddit


def main():
    r = praw.Reddit(user_agent=cfg_file.get('reddit', 'user_agent'))
    r.login(cfg_file.get('reddit', 'username'),
            cfg_file.get('reddit', 'password'))

    # update exclude_banned_modqueue values for subreddits
    subreddits = (session.query(Subreddit)
                         .filter(Subreddit.enabled == True)
                         .all())
    for sr in subreddits:
        try:
            settings = r.get_subreddit(sr.name).get_settings()
            sr.exclude_banned_modqueue = settings['exclude_banned_modqueue']
        except Exception as e:
            sr.exclude_banned_modqueue = False

    session.commit()

    # delete old log entries
    log_retention_days = int(cfg_file.get('database', 'log_retention_days'))
    log_cutoff = datetime.utcnow() - timedelta(days=log_retention_days)
    deleted = session.query(Log).filter(Log.datetime < log_cutoff).delete()
    session.commit()
    print 'Deleted {0} log rows'.format(deleted)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = models
import sys, os
from ConfigParser import SafeConfigParser

from sqlalchemy import create_engine
from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base


cfg_file = SafeConfigParser()
path_to_cfg = os.path.abspath(os.path.dirname(sys.argv[0]))
path_to_cfg = os.path.join(path_to_cfg, 'automoderator.cfg')
cfg_file.read(path_to_cfg)

if cfg_file.get('database', 'system').lower() == 'sqlite':
    engine = create_engine(
        cfg_file.get('database', 'system')+':///'+\
        cfg_file.get('database', 'database'))
else:
    engine = create_engine(
        cfg_file.get('database', 'system')+'://'+\
        cfg_file.get('database', 'username')+':'+\
        cfg_file.get('database', 'password')+'@'+\
        cfg_file.get('database', 'host')+'/'+\
        cfg_file.get('database', 'database'))
Base = declarative_base()
Session = sessionmaker(bind=engine, expire_on_commit=False)
session = Session()


class Subreddit(Base):

    """Table containing the subreddits for the bot to monitor.

    name - The subreddit's name. "gaming", not "/r/gaming".
    enabled - Subreddit will not be checked if False
    conditions_yaml - YAML definition of the subreddit's conditions
    last_submission - The newest unfiltered submission the bot has seen
    last_spam - The newest filtered submission the bot has seen
    last_comment - The newest comment the bot has seen
    exclude_banned_modqueue - Should mirror the same setting's value on the
        subreddit. Used to determine if it's necessary to check whether
        submitters in the modqueue are shadowbanned or not.
    """

    __tablename__ = 'subreddits'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    enabled = Column(Boolean, nullable=False, default=True)
    conditions_yaml = Column(Text)
    last_submission = Column(DateTime, nullable=False)
    last_spam = Column(DateTime, nullable=False)
    last_comment = Column(DateTime, nullable=False)
    exclude_banned_modqueue = Column(Boolean, nullable=False, default=False)


class StandardCondition(Base):

    """Table containing standard conditions that can be included by subreddits.

    name - A name identifying the condition (used to include that condition)
    yaml - The YAML definition of the standard condition
    """

    __tablename__ = 'standard_conditions'

    name = Column(String(255), primary_key=True)
    yaml = Column(Text)


class Log(Base):
    """Table containing a log of the bot's actions."""

    __tablename__ = 'log'

    id = Column(Integer, primary_key=True)
    item_fullname = Column(String(255), nullable=False)
    action = Column(Enum('approve',
                         'remove',
                         'spam',
                         'report',
                         'link_flair',
                         'user_flair',
                         name='log_action'))
    condition_yaml = Column(Text)
    datetime = Column(DateTime)


########NEW FILE########
