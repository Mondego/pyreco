__FILENAME__ = main
import time

from zxcvbn.matching import omnimatch
from zxcvbn.scoring import minimum_entropy_match_sequence


def password_strength(password, user_inputs=[]):
    start = time.time()
    matches = omnimatch(password, user_inputs)
    result = minimum_entropy_match_sequence(password, matches)
    result['calc_time'] = time.time() - start
    return result

########NEW FILE########
__FILENAME__ = matching
from itertools import groupby
import pkg_resources
import re

try:
    import simplejson as json
    json # silences pyflakes :<
except ImportError:
    import json


GRAPHS = {}
DICTIONARY_MATCHERS = []


def translate(string, chr_map):
    out = ''
    for char in string:
        out += chr_map[char] if char in chr_map else char
    return out

#-------------------------------------------------------------------------------
# dictionary match (common passwords, english, last names, etc) ----------------
#-------------------------------------------------------------------------------

def dictionary_match(password, ranked_dict):
    result = []
    length = len(password)

    pw_lower = password.lower()

    for i in xrange(0, length):
        for j in xrange(i, length):
            word = pw_lower[i:j+1]
            if word in ranked_dict:
                rank = ranked_dict[word]
                result.append( {'pattern':'dictionary',
                                'i' : i,
                                'j' : j,
                                'token' : password[i:j+1],
                                'matched_word' : word,
                                'rank': rank,
                               })
    return result


def _build_dict_matcher(dict_name, ranked_dict):
    def func(password):
        matches = dictionary_match(password, ranked_dict)
        for match in matches:
            match['dictionary_name'] = dict_name
        return matches
    return func


def _build_ranked_dict(unranked_list):
    result = {}
    i = 1
    for word in unranked_list:
        result[word] = i
        i += 1
    return result


def _load_frequency_lists():
    data = pkg_resources.resource_string(__name__, 'generated/frequency_lists.json')
    dicts = json.loads(data)
    for name, wordlist in dicts.items():
        DICTIONARY_MATCHERS.append(_build_dict_matcher(name, _build_ranked_dict(wordlist)))


def _load_adjacency_graphs():
    global GRAPHS
    data = pkg_resources.resource_string(__name__, 'generated/adjacency_graphs.json')
    GRAPHS = json.loads(data)


# on qwerty, 'g' has degree 6, being adjacent to 'ftyhbv'. '\' has degree 1.
# this calculates the average over all keys.
def _calc_average_degree(graph):
    average = 0.0
    for neighbors in graph.values():
        average += len([n for n in neighbors if n is not None])

    average /= len(graph)
    return average


_load_frequency_lists()
_load_adjacency_graphs()

KEYBOARD_AVERAGE_DEGREE = _calc_average_degree(GRAPHS[u'qwerty'])

# slightly different for keypad/mac keypad, but close enough
KEYPAD_AVERAGE_DEGREE = _calc_average_degree(GRAPHS[u'keypad'])

KEYBOARD_STARTING_POSITIONS = len(GRAPHS[u'qwerty'])
KEYPAD_STARTING_POSITIONS = len(GRAPHS[u'keypad'])


#-------------------------------------------------------------------------------
# dictionary match with common l33t substitutions ------------------------------
#-------------------------------------------------------------------------------

L33T_TABLE = {
  'a': ['4', '@'],
  'b': ['8'],
  'c': ['(', '{', '[', '<'],
  'e': ['3'],
  'g': ['6', '9'],
  'i': ['1', '!', '|'],
  'l': ['1', '|', '7'],
  'o': ['0'],
  's': ['$', '5'],
  't': ['+', '7'],
  'x': ['%'],
  'z': ['2'],
}

# makes a pruned copy of L33T_TABLE that only includes password's possible substitutions
def relevant_l33t_subtable(password):
    password_chars = set(password)

    filtered = {}
    for letter, subs in L33T_TABLE.items():
        relevent_subs = [sub for sub in subs if sub in password_chars]
        if len(relevent_subs) > 0:
            filtered[letter] = relevent_subs
    return filtered

# returns the list of possible 1337 replacement dictionaries for a given password

def enumerate_l33t_subs(table):
    subs = [[]]

    def dedup(subs):
        deduped = []
        members = set()
        for sub in subs:
            key = str(sorted(sub))
            if key not in members:
                deduped.append(sub)
        return deduped

    keys = table.keys()
    while len(keys) > 0:
        first_key = keys[0]
        rest_keys = keys[1:]
        next_subs = []
        for l33t_chr in table[first_key]:
            for sub in subs:
                dup_l33t_index = -1
                for i in range(0, len(sub)):
                    if sub[i][0] == l33t_chr:
                        dup_l33t_index = i
                        break
                if dup_l33t_index == -1:
                    sub_extension = list(sub)
                    sub_extension.append((l33t_chr, first_key))
                    next_subs.append(sub_extension)
                else:
                    sub_alternative = list(sub)
                    sub_alternative.pop(dup_l33t_index)
                    sub_alternative.append((l33t_chr, first_key))
                    next_subs.append(sub)
                    next_subs.append(sub_alternative)
        subs = dedup(next_subs)
        keys = rest_keys
    return map(dict, subs)


def l33t_match(password):
    matches = []

    for sub in enumerate_l33t_subs(relevant_l33t_subtable(password)):
        if len(sub) == 0:
            break
        subbed_password = translate(password, sub)
        for matcher in DICTIONARY_MATCHERS:
            for match in matcher(subbed_password):
                token = password[match['i']:match['j'] + 1]
                if token.lower() == match['matched_word']:
                    continue
                match_sub = {}
                for subbed_chr, char in sub.items():
                    if token.find(subbed_chr) != -1:
                        match_sub[subbed_chr] = char
                match['l33t'] = True
                match['token'] = token
                match['sub'] = match_sub
                match['sub_display'] = ', '.join([("%s -> %s" % (k, v)) for k, v in match_sub.items()])
                matches.append(match)
    return matches

# ------------------------------------------------------------------------------
# spatial match (qwerty/dvorak/keypad) -----------------------------------------
# ------------------------------------------------------------------------------

def spatial_match(password):
    matches = []
    for graph_name, graph in GRAPHS.items():
        matches.extend(spatial_match_helper(password, graph, graph_name))
    return matches


def spatial_match_helper(password, graph, graph_name):
    result = []
    i = 0
    while i < len(password) - 1:
        j = i + 1
        last_direction = None
        turns = 0
        shifted_count = 0
        while True:
            prev_char = password[j-1]
            found = False
            found_direction = -1
            cur_direction = -1
            adjacents = graph[prev_char] if prev_char in graph else []
            # consider growing pattern by one character if j hasn't gone over the edge.
            if j < len(password):
                cur_char = password[j]
                for adj in adjacents:
                    cur_direction += 1
                    if adj and adj.find(cur_char) != -1:
                        found = True
                        found_direction = cur_direction
                        if adj.find(cur_char) == 1:
                            # index 1 in the adjacency means the key is shifted, 0 means unshifted: A vs a, % vs 5, etc.
                            # for example, 'q' is adjacent to the entry '2@'. @ is shifted w/ index 1, 2 is unshifted.
                            shifted_count += 1
                        if last_direction != found_direction:
                            # adding a turn is correct even in the initial case when last_direction is null:
                            # every spatial pattern starts with a turn.
                            turns += 1
                            last_direction = found_direction
                        break
            # if the current pattern continued, extend j and try to grow again
            if found:
                j += 1
            # otherwise push the pattern discovered so far, if any...
            else:
                if j - i > 2: # don't consider length 1 or 2 chains.
                    result.append({
                        'pattern': 'spatial',
                        'i': i,
                        'j': j-1,
                        'token': password[i:j],
                        'graph': graph_name,
                        'turns': turns,
                        'shifted_count': shifted_count,
                    })
                # ...and then start a new search for the rest of the password.
                i = j
                break
    return result

#-------------------------------------------------------------------------------
# repeats (aaa) and sequences (abcdef) -----------------------------------------
#-------------------------------------------------------------------------------

def repeat_match(password):
    result = []
    repeats = groupby(password)
    i = 0
    for char, group in repeats:
        length = len(list(group))
        if length > 2:
            j = i + length - 1
            result.append({
                'pattern': 'repeat',
                'i': i,
                'j': j,
                'token': password[i:j+1],
                'repeated_char': char,
            })
        i += length
    return result


SEQUENCES = {
    'lower': 'abcdefghijklmnopqrstuvwxyz',
    'upper': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
   'digits': '01234567890',
}


def sequence_match(password):
    result = []
    i = 0
    while i < len(password):
        j = i + 1
        seq = None           # either lower, upper, or digits
        seq_name = None
        seq_direction = None # 1 for ascending seq abcd, -1 for dcba
        for seq_candidate_name, seq_candidate in SEQUENCES.items():
            i_n = seq_candidate.find(password[i])
            j_n = seq_candidate.find(password[j]) if j < len(password) else -1

            if i_n > -1 and j_n > -1:
                direction = j_n - i_n
                if direction in [1, -1]:
                    seq = seq_candidate
                    seq_name = seq_candidate_name
                    seq_direction = direction
                    break
        if seq:
            while True:
                if j <  len(password):
                    prev_char, cur_char = password[j-1], password[j]
                    prev_n, cur_n = seq_candidate.find(prev_char), seq_candidate.find(cur_char)
                if j == len(password) or cur_n - prev_n != seq_direction:
                    if j - i > 2: # don't consider length 1 or 2 chains.
                        result.append({
                            'pattern': 'sequence',
                            'i': i,
                            'j': j-1,
                            'token': password[i:j],
                            'sequence_name': seq_name,
                            'sequence_space': len(seq),
                            'ascending': seq_direction    == 1,
                        })
                    break
                else:
                    j += 1
        i = j
    return result

#-------------------------------------------------------------------------------
# digits, years, dates ---------------------------------------------------------
#-------------------------------------------------------------------------------

def match_all(password, pattern_name, regex):
    out = []
    for match in regex.finditer(password):
        i = match.start()
        j = match.end()
        out.append({
            'pattern' : pattern_name,
            'i' : i,
            'j' : j,
            'token' : password[i:j+1]
        })
    return out


DIGITS_MATCH = re.compile(r'\d{3,}')
def digits_match(password):
    return match_all(password, 'digits', DIGITS_MATCH)


YEAR_MATCH = re.compile(r'19\d\d|200\d|201\d')
def year_match(password):
    return match_all(password, 'year', YEAR_MATCH)


def date_match(password):
    l = date_without_sep_match(password)
    l.extend(date_sep_match(password))
    return l


DATE_WITHOUT_SEP_MATCH = re.compile(r'\d{4,8}')
def date_without_sep_match(password):
    date_matches = []
    for digit_match in DATE_WITHOUT_SEP_MATCH.finditer(password):
        i, j = digit_match.start(), digit_match.end()
        token = password[i:j+1]
        end = len(token)
        candidates_round_1 = [] # parse year alternatives
        if len(token) <= 6:
            # 2-digit year prefix
            candidates_round_1.append({
                'daymonth': token[2:],
                'year': token[0:2],
                'i': i,
                'j': j,
            })

            # 2-digit year suffix
            candidates_round_1.append({
                'daymonth': token[0:end-2],
                'year': token[end-2:],
                'i': i,
                'j': j,
            })
        if len(token) >= 6:
            # 4-digit year prefix
            candidates_round_1.append({
                'daymonth': token[4:],
                'year': token[0:4],
                'i': i,
                'j': j,
            })
            # 4-digit year suffix
            candidates_round_1.append({
                'daymonth': token[0:end-4],
                'year': token[end-4:],
                'i': i,
                'j': j,
            })
        candidates_round_2 = [] # parse day/month alternatives
        for candidate in candidates_round_1:
            if len(candidate['daymonth']) == 2: # ex. 1 1 97
                candidates_round_2.append({
                    'day': candidate['daymonth'][0],
                    'month': candidate['daymonth'][1],
                    'year': candidate['year'],
                    'i': candidate['i'],
                    'j': candidate['j'],
                })
            elif len(candidate['daymonth']) == 3: # ex. 11 1 97 or 1 11 97
                candidates_round_2.append({
                    'day': candidate['daymonth'][0:2],
                    'month': candidate['daymonth'][2],
                    'year': candidate['year'],
                    'i': candidate['i'],
                    'j': candidate['j'],
                })
                candidates_round_2.append({
                    'day': candidate['daymonth'][0],
                    'month': candidate['daymonth'][1:3],
                    'year': candidate['year'],
                    'i': candidate['i'],
                    'j': candidate['j'],
                })
            elif len(candidate['daymonth']) == 4: # ex. 11 11 97
                candidates_round_2.append({
                    'day': candidate['daymonth'][0:2],
                    'month': candidate['daymonth'][2:4],
                    'year': candidate['year'],
                    'i': candidate['i'],
                    'j': candidate['j'],
                })
        # final loop: reject invalid dates
        for candidate in candidates_round_2:
            try:
                day = int(candidate['day'])
                month = int(candidate['month'])
                year = int(candidate['year'])
            except ValueError:
                continue
            valid, (day, month, year) = check_date(day, month, year)
            if not valid:
                continue
            date_matches.append( {
                'pattern': 'date',
                'i': candidate['i'],
                'j': candidate['j'],
                'token': password[i:j+1],
                'separator': '',
                'day': day,
                'month': month,
                'year': year,
            })
    return date_matches


DATE_RX_YEAR_SUFFIX = re.compile(r"(\d{1,2})(\s|-|/|\\|_|\.)(\d{1,2})\2(19\d{2}|200\d|201\d|\d{2})")
#DATE_RX_YEAR_SUFFIX = "(\d{1,2})(\s|-|/|\\|_|\.)"
DATE_RX_YEAR_PREFIX = re.compile(r"(19\d{2}|200\d|201\d|\d{2})(\s|-|/|\\|_|\.)(\d{1,2})\2(\d{1,2})")


def date_sep_match(password):
    matches = []
    for match in DATE_RX_YEAR_SUFFIX.finditer(password):
        day, month, year = tuple(int(match.group(x)) for x in [1, 3, 4])
        matches.append( {
            'day' : day,
            'month' : month,
            'year' : year,
            'sep' : match.group(2),
            'i' : match.start(),
            'j' : match.end()
        })
    for match in DATE_RX_YEAR_PREFIX.finditer(password):
        day, month, year = tuple(int(match.group(x)) for x in [4, 3, 1])
        matches.append( {
            'day' : day,
            'month' : month,
            'year' : year,
            'sep' : match.group(2),
            'i' : match.start(),
            'j' : match.end()
        })
    out = []
    for match in matches:
        valid, (day, month, year) = check_date(match['day'], match['month'], match['year'])
        if not valid:
            continue
        out.append({
            'pattern': 'date',
            'i': match['i'],
            'j': match['j']-1,
            'token': password[match['i']:match['j']],
            'separator': match['sep'],
            'day': day,
            'month': month,
            'year': year,
        })
    return out


def check_date(day, month, year):
    if 12 <= month <= 31 and day <= 12: # tolerate both day-month and month-day order
        day, month = month, day

    if day > 31 or month > 12:
        return (False, (0, 0, 0))

    if not (1900 <= year <= 2019):
        return (False, (0, 0, 0))

    return (True, (day, month, year))


MATCHERS = list(DICTIONARY_MATCHERS)
MATCHERS.extend([
    l33t_match,
    digits_match, year_match, date_match,
    repeat_match, sequence_match,
    spatial_match
])


def omnimatch(password, user_inputs=[]):
    ranked_user_inputs_dict = {}
    for i, user_input in enumerate(user_inputs):
    	ranked_user_inputs_dict[user_input.lower()] = i+1
    user_input_matcher = _build_dict_matcher('user_inputs', ranked_user_inputs_dict)
    matches = user_input_matcher(password)
    for matcher in MATCHERS:
        matches.extend(matcher(password))
    matches.sort(key=lambda x : (x['i'], x['j']))
    return matches

########NEW FILE########
__FILENAME__ = scoring
import math
import re

from zxcvbn.matching import (KEYBOARD_STARTING_POSITIONS, KEYBOARD_AVERAGE_DEGREE,
                             KEYPAD_STARTING_POSITIONS, KEYPAD_AVERAGE_DEGREE)

def binom(n, k):
    """
    Returns binomial coefficient (n choose k).
    """
    # http://blog.plover.com/math/choose.html
    if k > n:
        return 0
    if k == 0:
        return 1
    result = 1
    for denom in range(1, k + 1):
        result *= n
        result /= denom
        n -= 1
    return result


def lg(n):
    """
    Returns logarithm of n in base 2.
    """
    return math.log(n, 2)

# ------------------------------------------------------------------------------
# minimum entropy search -------------------------------------------------------
# ------------------------------------------------------------------------------
#
# takes a list of overlapping matches, returns the non-overlapping sublist with
# minimum entropy. O(nm) dp alg for length-n password with m candidate matches.
# ------------------------------------------------------------------------------
def get(a, i):
    if i < 0 or i >= len(a):
        return 0
    return a[i]


def minimum_entropy_match_sequence(password, matches):
    """
    Returns minimum entropy

    Takes a list of overlapping matches, returns the non-overlapping sublist with
    minimum entropy. O(nm) dp alg for length-n password with m candidate matches.
    """
    bruteforce_cardinality = calc_bruteforce_cardinality(password) # e.g. 26 for lowercase
    up_to_k = [0] * len(password) # minimum entropy up to k.
    # for the optimal sequence of matches up to k, holds the final match (match['j'] == k). null means the sequence ends
    # without a brute-force character.
    backpointers = []
    for k in range(0, len(password)):
        # starting scenario to try and beat: adding a brute-force character to the minimum entropy sequence at k-1.
        up_to_k[k] = get(up_to_k, k-1) + lg(bruteforce_cardinality)
        backpointers.append(None)
        for match in matches:
            if match['j'] != k:
                continue
            i, j = match['i'], match['j']
            # see if best entropy up to i-1 + entropy of this match is less than the current minimum at j.
            up_to = get(up_to_k, i-1)
            candidate_entropy = up_to + calc_entropy(match)
            if candidate_entropy < up_to_k[j]:
                #print "New minimum: using " + str(match)
                #print "Entropy: " + str(candidate_entropy)
                up_to_k[j] = candidate_entropy
                backpointers[j] = match

    # walk backwards and decode the best sequence
    match_sequence = []
    k = len(password) - 1
    while k >= 0:
        match = backpointers[k]
        if match:
            match_sequence.append(match)
            k = match['i'] - 1
        else:
            k -= 1
    match_sequence.reverse()

    # fill in the blanks between pattern matches with bruteforce "matches"
    # that way the match sequence fully covers the password: match1.j == match2.i - 1 for every adjacent match1, match2.
    def make_bruteforce_match(i, j):
        return {
            'pattern': 'bruteforce',
            'i': i,
            'j': j,
            'token': password[i:j+1],
            'entropy': lg(math.pow(bruteforce_cardinality, j - i + 1)),
            'cardinality': bruteforce_cardinality,
        }
    k = 0
    match_sequence_copy = []
    for match in match_sequence:
        i, j = match['i'], match['j']
        if i - k > 0:
            match_sequence_copy.append(make_bruteforce_match(k, i - 1))
        k = j + 1
        match_sequence_copy.append(match)

    if k < len(password):
        match_sequence_copy.append(make_bruteforce_match(k, len(password) - 1))
    match_sequence = match_sequence_copy

    min_entropy = 0 if len(password) == 0 else up_to_k[len(password) - 1] # corner case is for an empty password ''
    crack_time = entropy_to_crack_time(min_entropy)

    # final result object
    return {
        'password': password,
        'entropy': round_to_x_digits(min_entropy, 3),
        'match_sequence': match_sequence,
        'crack_time': round_to_x_digits(crack_time, 3),
        'crack_time_display': display_time(crack_time),
        'score': crack_time_to_score(crack_time),
    }


def round_to_x_digits(number, digits):
    """
    Returns 'number' rounded to 'digits' digits.
    """
    return round(number * math.pow(10, digits)) / math.pow(10, digits)

# ------------------------------------------------------------------------------
# threat model -- stolen hash catastrophe scenario -----------------------------
# ------------------------------------------------------------------------------
#
# assumes:
# * passwords are stored as salted hashes, different random salt per user.
#   (making rainbow attacks infeasable.)
# * hashes and salts were stolen. attacker is guessing passwords at max rate.
# * attacker has several CPUs at their disposal.
# ------------------------------------------------------------------------------

# for a hash function like bcrypt/scrypt/PBKDF2, 10ms per guess is a safe lower bound.
# (usually a guess would take longer -- this assumes fast hardware and a small work factor.)
# adjust for your site accordingly if you use another hash function, possibly by
# several orders of magnitude!
SINGLE_GUESS = .010
NUM_ATTACKERS = 100 # number of cores guessing in parallel.

SECONDS_PER_GUESS = SINGLE_GUESS / NUM_ATTACKERS


def entropy_to_crack_time(entropy):
    return (0.5 * math.pow(2, entropy)) * SECONDS_PER_GUESS # average, not total


def crack_time_to_score(seconds):
    if seconds < math.pow(10, 2):
        return 0
    if seconds < math.pow(10, 4):
        return 1
    if seconds < math.pow(10, 6):
        return 2
    if seconds < math.pow(10, 8):
        return 3
    return 4

# ------------------------------------------------------------------------------
# entropy calcs -- one function per match pattern ------------------------------
# ------------------------------------------------------------------------------

def calc_entropy(match):
    if 'entropy' in match: return match['entropy']

    if match['pattern'] == 'repeat':
        entropy_func = repeat_entropy
    elif match['pattern'] == 'sequence':
        entropy_func = sequence_entropy
    elif match['pattern'] == 'digits':
        entropy_func = digits_entropy
    elif match['pattern'] == 'year':
        entropy_func = year_entropy
    elif match['pattern'] == 'date':
        entropy_func = date_entropy
    elif match['pattern'] == 'spatial':
        entropy_func = spatial_entropy
    elif match['pattern'] == 'dictionary':
        entropy_func = dictionary_entropy
    match['entropy'] = entropy_func(match)
    return match['entropy']


def repeat_entropy(match):
    cardinality = calc_bruteforce_cardinality(match['token'])
    return lg(cardinality * len(match['token']))


def sequence_entropy(match):
    first_chr = match['token'][0]
    if first_chr in ['a', '1']:
        base_entropy = 1
    else:
        if first_chr.isdigit():
            base_entropy = lg(10) # digits
        elif first_chr.isalpha():
            base_entropy = lg(26) # lower
        else:
            base_entropy = lg(26) + 1 # extra bit for uppercase
    if not match['ascending']:
        base_entropy += 1 # extra bit for descending instead of ascending
    return base_entropy + lg(len(match['token']))


def digits_entropy(match):
    return lg(math.pow(10, len(match['token'])))


NUM_YEARS = 119 # years match against 1900 - 2019
NUM_MONTHS = 12
NUM_DAYS = 31


def year_entropy(match):
    return lg(NUM_YEARS)


def date_entropy(match):
    if match['year'] < 100:
        entropy = lg(NUM_DAYS * NUM_MONTHS * 100) # two-digit year
    else:
        entropy = lg(NUM_DAYS * NUM_MONTHS * NUM_YEARS) # four-digit year

    if match['separator']:
        entropy += 2 # add two bits for separator selection [/,-,.,etc]
    return entropy


def spatial_entropy(match):
    if match['graph'] in ['qwerty', 'dvorak']:
        s = KEYBOARD_STARTING_POSITIONS
        d = KEYBOARD_AVERAGE_DEGREE
    else:
        s = KEYPAD_STARTING_POSITIONS
        d = KEYPAD_AVERAGE_DEGREE
    possibilities = 0
    L = len(match['token'])
    t = match['turns']
    # estimate the number of possible patterns w/ length L or less with t turns or less.
    for i in range(2, L + 1):
        possible_turns = min(t, i - 1)
        for j in range(1, possible_turns+1):
            x =  binom(i - 1, j - 1) * s * math.pow(d, j)
            possibilities += x
    entropy = lg(possibilities)
    # add extra entropy for shifted keys. (% instead of 5, A instead of a.)
    # math is similar to extra entropy from uppercase letters in dictionary matches.
    if 'shifted_count' in match:
        S = match['shifted_count']
        U = L - S # unshifted count
        possibilities = sum(binom(S + U, i) for i in xrange(0, min(S, U) + 1))
        entropy += lg(possibilities)
    return entropy


def dictionary_entropy(match):
    match['base_entropy'] = lg(match['rank']) # keep these as properties for display purposes
    match['uppercase_entropy'] = extra_uppercase_entropy(match)
    match['l33t_entropy'] = extra_l33t_entropy(match)
    ret = match['base_entropy'] + match['uppercase_entropy'] + match['l33t_entropy']
    return ret


START_UPPER = re.compile('^[A-Z][^A-Z]+$')
END_UPPER = re.compile('^[^A-Z]+[A-Z]$')
ALL_UPPER = re.compile('^[A-Z]+$')


def extra_uppercase_entropy(match):
    word = match['token']
    if word.islower():
        return 0
    # a capitalized word is the most common capitalization scheme,
    # so it only doubles the search space (uncapitalized + capitalized): 1 extra bit of entropy.
    # allcaps and end-capitalized are common enough too, underestimate as 1 extra bit to be safe.
    for regex in [START_UPPER, END_UPPER, ALL_UPPER]:
        if regex.match(word):
            return 1
    # Otherwise calculate the number of ways to capitalize U+L uppercase+lowercase letters with U uppercase letters or
    # less. Or, if there's more uppercase than lower (for e.g. PASSwORD), the number of ways to lowercase U+L letters
    # with L lowercase letters or less.
    upp_len = len([x for x in word if x.isupper()])
    low_len = len([x for x in word if x.islower()])
    possibilities = sum(binom(upp_len + low_len, i) for i in range(0, min(upp_len, low_len) + 1))
    return lg(possibilities)


def extra_l33t_entropy(match):
    if 'l33t' not in match or not match['l33t']:
        return 0
    possibilities = 0
    for subbed, unsubbed in match['sub'].items():
        sub_len = len([x for x in match['token'] if x == subbed])
        unsub_len = len([x for x in match['token'] if x == unsubbed])
        possibilities += sum(binom(unsub_len + sub_len, i) for i in range(0, min(unsub_len, sub_len) + 1))
    # corner: return 1 bit for single-letter subs, like 4pple -> apple, instead of 0.
    if possibilities <= 1:
        return 1
    return lg(possibilities)

# utilities --------------------------------------------------------------------

def calc_bruteforce_cardinality(password):
    lower, upper, digits, symbols = 0, 0, 0, 0
    for char in password:
        if char.islower():
            lower = 26
        elif char.isdigit():
            digits = 10
        elif char.isupper():
            upper = 26
        else:
            symbols = 33
    cardinality = lower + digits + upper + symbols
    return cardinality


def display_time(seconds):
    minute = 60
    hour = minute * 60
    day = hour * 24
    month = day * 31
    year = month * 12
    century = year * 100
    if seconds < minute:
        return 'instant'
    elif seconds < hour:
        return str(1 + math.ceil(seconds / minute)) + " minutes"
    elif seconds < day:
        return str(1 + math.ceil(seconds / hour)) + " hours"
    elif seconds < month:
        return str(1 + math.ceil(seconds / day)) + " days"
    elif seconds < year:
        return str(1 + math.ceil(seconds / month)) + " months"
    elif seconds < century:
        return str(1 + math.ceil(seconds / year)) + " years"
    else:
        return 'centuries'

########NEW FILE########
__FILENAME__ = build_frequency_lists
from __future__ import with_statement
import os
import time
import codecs
try:
    import simplejson as json
    json
except ImportError:
    import json

import urllib2

SLEEP_TIME = 20 # seconds

def get_ranked_english():
    '''
    wikitionary has a list of ~40k English words, ranked by frequency of occurance in TV and movie transcripts.
    more details at:
    http://en.wiktionary.org/wiki/Wiktionary:Frequency_lists/TV/2006/explanation

    the list is separated into pages of 1000 or 2000 terms each.
    * the first 10k words are separated into pages of 1000 terms each.
    * the remainder is separated into pages of 2000 terms each:
    '''
    URL_TMPL = 'http://en.wiktionary.org/wiki/Wiktionary:Frequency_lists/TV/2006/%s'
    urls = []
    for i in xrange(10):
        freq_range = "%d-%d" % (i * 1000 + 1, (i+1) * 1000)
        urls.append(URL_TMPL % freq_range)

    for i in xrange(0,15):
        freq_range = "%d-%d" % (10000 + 2 * i * 1000 + 1, 10000 + (2 * i + 2) * 1000)
        urls.append(URL_TMPL % freq_range)

    urls.append(URL_TMPL % '40001-41284')

    ranked_terms = [] # ordered by rank, in decreasing frequency.
    for url in urls:
        html, is_cached = wiki_download(url)
        if not is_cached:
            time.sleep(SLEEP_TIME)
        new_terms = parse_wiki_terms(html)
        ranked_terms.extend(new_terms)

    return ranked_terms

def wiki_download(url):
    '''
    scrape friendly: sleep 20 seconds between each request, cache each result.
    '''
    DOWNLOAD_TMPL = '../data/tv_and_movie_freqlist%s.html'
    freq_range = url[url.rindex('/')+1:]

    tmp_path = DOWNLOAD_TMPL % freq_range
    if os.path.exists(tmp_path):
        print 'cached.......', url
        with codecs.open(tmp_path, 'r', 'utf8') as f:
            return f.read(), True
    with codecs.open(tmp_path, 'w', 'utf8') as f:
        print 'downloading...', url
        req = urllib2.Request(url, headers={
                'User-Agent': 'zxcvbn'
                })
        response = urllib2.urlopen(req)
        result = response.read().decode('utf8')
        f.write(result)
        return result, False

def parse_wiki_terms(doc):
    '''who needs an html parser. fragile hax, but checks the result at the end'''
    results = []
    last3 = ['', '', '']
    header = True
    for line in doc.split('\n'):
        last3.pop(0)
        last3.append(line.strip())
        if all(s.startswith('<td>') and not s == '<td></td>' for s in last3):
            if header:
                header = False
                continue
            last3 = [s.replace('<td>', '').replace('</td>', '').strip() for s in last3]
            rank, term, count = last3
            rank = int(rank.split()[0])
            term = term.replace('</a>', '')
            term = term[term.index('>')+1:].lower()
            results.append(term)
    assert len(results) in [1000, 2000, 1284] # early docs have 1k entries, later have 2k, last doc has 1284
    return results

def get_ranked_census_names():
    '''
    takes name lists from the the 2000 us census, prepares as a json array in order of frequency (most common names first).

    more info:
    http://www.census.gov/genealogy/www/data/2000surnames/index.html

    files in data are downloaded copies of:
    http://www.census.gov/genealogy/names/dist.all.last
    http://www.census.gov/genealogy/names/dist.male.first
    http://www.census.gov/genealogy/names/dist.female.first
    '''
    FILE_TMPL = '../data/us_census_2000_%s.txt'
    SURNAME_CUTOFF_PERCENTILE = 85 # ie7 can't handle huge lists. cut surname list off at a certain percentile.
    lists = []
    for list_name in ['surnames', 'male_first', 'female_first']:
        path = FILE_TMPL % list_name
        lst = []
        for line in codecs.open(path, 'r', 'utf8'):
            if line.strip():
                if list_name == 'surnames' and float(line.split()[2]) > SURNAME_CUTOFF_PERCENTILE:
                    break
                name = line.split()[0].lower()
                lst.append(name)
        lists.append(lst)
    return lists

def get_ranked_common_passwords():
    lst = []
    for line in codecs.open('../data/common_passwords.txt', 'r', 'utf8'):
        if line.strip():
            lst.append(line.strip())
    return lst

def to_ranked_dict(lst):
    return dict((word, i) for i, word in enumerate(lst))

def filter_short(terms):
    '''
    only keep if brute-force possibilities are greater than this word's rank in the dictionary
    '''
    return [term for i, term in enumerate(terms) if 26**(len(term)) > i]

def filter_dup(lst, lists):
    '''
    filters lst to only include terms that don't have lower rank in another list
    '''
    max_rank = len(lst) + 1
    dct = to_ranked_dict(lst)
    dicts = [to_ranked_dict(l) for l in lists]
    return [word for word in lst if all(dct[word] < dct2.get(word, max_rank) for dct2 in dicts)]

def filter_ascii(lst):
    '''
    removes words with accent chars etc.
    (most accented words in the english lookup exist in the same table unaccented.)
    '''
    return [word for word in lst if all(ord(c) < 128 for c in word)]

def main():
    english = get_ranked_english()
    surnames, male_names, female_names = get_ranked_census_names()
    passwords = get_ranked_common_passwords()

    [english,
     surnames, male_names, female_names,
     passwords] = [filter_ascii(filter_short(lst)) for lst in (english,
                                                               surnames, male_names, female_names,
                                                               passwords)]

    # make dictionaries disjoint so that d1 & d2 == set() for any two dictionaries
    all_dicts = set(tuple(l) for l in [english, surnames, male_names, female_names, passwords])
    passwords    = filter_dup(passwords,    all_dicts - set([tuple(passwords)]))
    male_names   = filter_dup(male_names,   all_dicts - set([tuple(male_names)]))
    female_names = filter_dup(female_names, all_dicts - set([tuple(female_names)]))
    surnames     = filter_dup(surnames,     all_dicts - set([tuple(surnames)]))
    english      = filter_dup(english,      all_dicts - set([tuple(english)]))

    with open('../generated/frequency_lists.json', 'w') as f: # words are all ascii at this point
        lsts = locals()
        out = {}
        for lst_name in 'passwords male_names female_names surnames english'.split():
            lst = lsts[lst_name]
            out[lst_name] = lst
        json.dump(out, f)

    print '\nall done! totals:\n'
    print 'passwords....', len(passwords)
    print 'male.........', len(male_names)
    print 'female.......', len(female_names)
    print 'surnames.....', len(surnames)
    print 'english......', len(english)
    print

if __name__ == '__main__':
    if os.path.basename(os.getcwd()) != 'scripts':
        print 'run this from the scripts directory'
        exit(1)
    main()

########NEW FILE########
__FILENAME__ = build_keyboard_adjacency_graph
from __future__ import with_statement
try:
    import simplejson as json
    json # silence pyflakes
except ImportError:
    import json

qwerty = r'''
`~ 1! 2@ 3# 4$ 5% 6^ 7& 8* 9( 0) -_ =+
    qQ wW eE rR tT yY uU iI oO pP [{ ]} \|
     aA sS dD fF gG hH jJ kK lL ;: '"
      zZ xX cC vV bB nN mM ,< .> /?
'''

dvorak = r'''
`~ 1! 2@ 3# 4$ 5% 6^ 7& 8* 9( 0) [{ ]}
    '" ,< .> pP yY fF gG cC rR lL /? =+ \|
     aA oO eE uU iI dD hH tT nN sS -_
      ;: qQ jJ kK xX bB mM wW vV zZ
'''

keypad = r'''
  / * -
7 8 9 +
4 5 6
1 2 3
  0 .
'''

mac_keypad = r'''
  = / *
7 8 9 -
4 5 6 +
1 2 3
  0 .
'''

def get_slanted_adjacent_coords(x, y):
    '''
    returns the six adjacent coordinates on a standard keyboard, where each row is slanted to the right from the last.
    adjacencies are clockwise, starting with key to the left, then two keys above, then right key, then two keys below.
    (that is, only near-diagonal keys are adjacent, so g's coordinate is adjacent to those of t,y,b,v, but not those of r,u,n,c.)
    '''
    return [(x-1, y), (x, y-1), (x+1, y-1), (x+1, y), (x, y+1), (x-1, y+1)]

def get_aligned_adjacent_coords(x, y):
    '''
    returns the nine clockwise adjacent coordinates on a keypad, where each row is vertically aligned.
    '''
    return [(x-1, y), (x-1, y-1), (x, y-1), (x+1, y-1), (x+1, y), (x+1, y+1), (x, y+1), (x-1, y+1)]

def build_graph(layout_str, slanted):
    '''
    builds an adjacency graph as a dictionary: {character: [adjacent_characters]}.
    adjacent characters occur in a clockwise order.
    for example:
    * on qwerty layout, 'g' maps to ['fF', 'tT', 'yY', 'hH', 'bB', 'vV']
    * on keypad layout, '7' maps to [None, None, None, '=', '8', '5', '4', None]
    '''
    position_table = {} # maps from tuple (x,y) -> characters at that position.
    tokens = layout_str.split()
    token_size = len(tokens[0])
    x_unit = token_size + 1 # x position unit length is token length plus 1 for the following whitespace.
    adjacency_func = get_slanted_adjacent_coords if slanted else get_aligned_adjacent_coords
    assert all(len(token) == token_size for token in tokens), 'token length mismatch:\n ' + layout_str
    for y, line in enumerate(layout_str.split('\n')):
        slant = y - 1 if slanted else 0 # the way i illustrated keys above, each qwerty row is indented one space in from the last
        for token in line.split():
            x, remainder = divmod(line.index(token) - slant, x_unit)
            assert remainder == 0, 'unexpected x offset for %s in:\n%s' % (token, layout_str)
            position_table[(x,y)] = token

    adjacency_graph = {}
    for (x,y), chars in position_table.iteritems():
        for char in chars:
            adjacency_graph[char] = []
            for coord in adjacency_func(x, y):
                # position in the list indicates direction (for qwerty, 0 is left, 1 is top, 2 is top right, ...)
                # for edge chars like 1 or m, insert None as a placeholder when needed so that each character in the graph has a same-length adjacency list.
                adjacency_graph[char].append(position_table.get(coord, None))
    return adjacency_graph

if __name__ == '__main__':
    with open('../generated/adjacency_graphs.json', 'w') as f:
        out = {}
        for graph_name, args in [('qwerty', (qwerty, True)),
                                 ('dvorak', (dvorak, True)),
                                 ('keypad', (keypad, False)),
                                 ('mac_keypad', (mac_keypad, False))]:
            graph = build_graph(*args)
            out[graph_name] = graph
        json.dump(out, f)

########NEW FILE########
