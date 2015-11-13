__FILENAME__ = cleaver
import re
from exception import UnparseableNameException
from names import SUFFIX_RE, DEGREE_RE, PersonName, PoliticianName, RunningMatesNames, \
    OrganizationName
from nicknames import NICKNAMES


class BaseNameCleaver(object):
    def __init__(self, string):
        self.name = string
        self.orig_str = string

    def cannot_parse(self, safe, e=None):
        if safe:
            return self.orig_str
        else:
            # uncomment for debugging
            #if e:
            #   print e
            raise UnparseableNameException(u"Couldn't parse name: {0}".format(self.name))

    def get_object_class(self):
        return self.object_class()


class IndividualNameCleaver(BaseNameCleaver):
    object_class = PersonName

    def __init__(self, string):
        super(IndividualNameCleaver, self).__init__(string)

    def parse(self, safe=False):
        if not self.orig_str:
            return ''

        if not ' ' in self.name:
            self.name = self.get_object_class().new_from_tokens(self.name)
            return self.name.case_name_parts()
        else:
            try:
                self.name = self.pre_process(self.name)

                name, honorific, suffix, nick = self.separate_affixes(self.name)

                if honorific and not honorific.endswith('.'):
                    honorific += '.'

                name = self.reverse_last_first(name)
                self.name = self.convert_name_to_obj(name, nick, honorific, suffix)
            except Exception, e:
                return self.cannot_parse(safe, e)
            finally:
                if (isinstance(self.name, self.object_class) and self.name.last):
                    return self.name.case_name_parts()
                else:
                    return self.cannot_parse(safe)

    def pre_process(self, name):
        # strip any spaces padding parenthetical phrases
        name = re.sub('\(\s*([^)]+)\s*\)', '(\1)', name)

        # get rid of trailing '& mrs'
        name = re.sub(' (?i)\& mrs\.?$', '', name)

        return name

    def separate_affixes(self, name):

        name, suffix = self.extract_suffix(name)

        name, honorific = self.extract_matching_portion(r'\b(?P<honorific>[dm][rs]s?[,.]?)(?=(\b|\s))+', name)

        if suffix:
            suffix = suffix.replace('.', '')

        name, junk = self.extract_matching_portion(r'(?P<junk_numbers>\b\d{2,}(?=(\b|\s))+)', name)
        name, nick = self.extract_matching_portion(r'("[^"]+")', name)

        # strip trailing non alphanumeric characters
        name = re.sub(r'[^a-zA-Z0-9]$', '', name)

        return name, honorific, suffix, nick

    def extract_matching_portion(self, pattern, name):
        m = re.finditer(pattern, name, flags=re.IGNORECASE)

        matched_portion = None
        match_strings = []

        for match in m:
            matched_piece = match.group()
            match_strings.append(matched_piece)
            name = re.sub('\s?{0}'.format(matched_piece), '', name)

        if len(match_strings):
            matched_portion = ' '.join(match_strings)

        return name, matched_portion

    def extract_suffix(self, name):
        """
        Returns a tuple of (name, suffix), or (name, None) if no suffix could be found.
        As the method name indicates, the name is returned without the suffix.

        Suffixes deemed to be degrees are discarded.
        """
        # don't extract suffixes if we can't reasonably suspect we have enough parts to the name for there to be one
        if len(name.strip().split()) > 2:
            name, suffix = self.extract_matching_portion(r'\b(?P<suffix>{})(?=\b|\s|\Z|\W)'.format(SUFFIX_RE), name)
            suffix, degree = self.extract_matching_portion(DEGREE_RE, suffix or '')
            return name, suffix or None

        return name, None

    def reverse_last_first(self, name):
        """ Takes a name that is in [last, first] format and returns it in a hopefully [first last] order.
            Also extracts the suffix and puts it back on the end, in case it's embedded somewhere in the middle.
        """
        # make sure we don't put a suffix in the middle, as in "Smith, Tom II"
        name, suffix = self.extract_suffix(name)

        split = re.split(', ?', name)

        # make sure that the comma is not just preceding a suffix, such as "Jr",
        # by checking that we have at least 2 name parts and the last doesn't match
        # our suffix regex
        if len(split) >= 2:
            split.reverse()

        if suffix:
            split.append(suffix)

        return ' '.join(split)

    def convert_name_to_obj(self, name, nick, honorific, suffix):
        name = ' '.join([x.strip() for x in [name, nick, suffix, honorific] if x])

        return self.get_object_class().new_from_tokens(*[x for x in re.split('\s+', name)], **{'allow_quoted_nicknames': True})

    @classmethod
    def name_processing_failed(cls, subject_name):
        return subject_name and (isinstance(subject_name, RunningMatesNames) or not subject_name.last)

    @classmethod
    def compare(cls, name1, name2):
        score = 0

        # score last name
        if name1.last == name2.last:
            score += 1
        else:
            return 0

        # score first name
        if name1.first and name2.first and name1.first == name2.first:
            score += 1
        elif name1.first and name2.first:
            for name_set in NICKNAMES:
                if set(name_set).issuperset([name1.first, name2.first]):
                    score += 0.6
                    break

            if name1.first == name2.middle and name2.first == name1.middle:
                score += 0.8
            else:
                try:
                    # this was failing in cases where an odd organization name was in the mix
                    if name1.first[0] == name2.first[0]:
                        score += 0.1
                except:
                    return 0

        # score middle name
        if name1.middle and name2.middle:
            # we only want to count the middle name for much if we've already
            # got a match on first and last, to avoid getting high scores for
            # names which only match on last and middle
            if score > 1.1:
                if name1.middle == name2.middle:
                    score += 1
                elif name1.middle[0] == name2.middle[0]:
                    score += .5
                else:
                    score -= 1.5

            else:
                score += .2

        return score


class PoliticianNameCleaver(IndividualNameCleaver):
    object_class = PoliticianName

    def __init__(self, string):
        super(PoliticianNameCleaver, self).__init__(string)

    def parse(self, safe=False):
        if not self.orig_str:
            return ''

        if not ' ' in self.name:
            self.name = self.get_object_class().new_from_tokens(self.name)
            return self.name.case_name_parts()
        else:
            try:
                self.strip_party()
                self.name = self.convert_name_to_obj(self.name)  # important for "last, first", and also running mates
            except Exception, e:
                return self.cannot_parse(safe, e)
            finally:
                if ((isinstance(self.name, self.object_class) and self.name.last) or isinstance(self.name, RunningMatesNames)):
                    return self.name.case_name_parts()
                else:
                    return self.cannot_parse(safe)

    def strip_party(self):
        if '(' in self.name:
            self.name = re.sub(r'\s*\([^)]+\)\s*$', '', self.name)

    def convert_name_to_obj(self, name):
        if '&' in name or '/' in name:
            return self.convert_running_mates_names_to_obj(name)
        else:
            return self.convert_regular_name_to_obj(name)

    def convert_regular_name_to_obj(self, name):
        name = self.reverse_last_first(name)
        return self.get_object_class().new_from_tokens(*[x for x in re.split('\s+', name) if x])

    def convert_running_mates_names_to_obj(self, name):
        return RunningMatesNames(*[self.convert_name_to_obj(x) for x in re.split(' [&/] ', name)])


class OrganizationNameCleaver(BaseNameCleaver):
    object_class = OrganizationName

    def __init__(self, string):
        super(OrganizationNameCleaver, self).__init__(string)

    def parse(self, safe=False):
        if not self.orig_str:
            return ''

        try:
            self.name = self.name.strip()

            self.name = self.get_object_class().new(self.name)
        except Exception, e:
            return self.cannot_parse(safe, e)
        finally:
            if isinstance(self.name, self.object_class):
                return self.name.case_name_parts()
            else:
                return self.cannot_parse(safe)

    def convert_name_to_obj(self):
        self.name = self.get_object_class().new(self.name)

    @classmethod
    def name_processing_failed(cls, subject_name):
        return not isinstance(subject_name, cls.object_class)

    @classmethod
    def compare(cls, match, subject):
        """
            Accepts two OrganizationName objects and returns an arbitrary,
            numerical score based upon how well the names match.
        """
        if match.expand().lower() == subject.expand().lower():
            return 4
        elif match.kernel().lower() == subject.kernel().lower():
            return 3
        # law and lobbying firms in CRP data typically list only the first two partners
        # before 'et al'
        elif ',' in subject.expand():  # we may have a list of partners
            if subject.crp_style_firm_name() == str(match).lower():
                return 3
        else:
            return 2

########NEW FILE########
__FILENAME__ = exception

class UnparseableNameException(Exception):
    pass

########NEW FILE########
__FILENAME__ = names
import re

DEGREE_RE = 'j\.?d\.?|m\.?d\.?|ph\.?d\.?'
SUFFIX_RE = '([js]r\.?|%s|[IVX]{2,})' % DEGREE_RE

class Name(object):
    scottish_re = r'(?i)\b(?P<mc>ma?c)(?!hin)(?P<first_letter>\w)\w+'

    def primary_name_parts(self):
        raise NotImplementedError("Subclasses of Name must implement primary_name_parts.")

    def non_empty_primary_name_parts(self):
        return ' '.join([ x for x in self.primary_name_parts() if x ])

    def is_mixed_case(self):
        return re.search(r'[A-Z][a-z]', self.non_empty_primary_name_parts())

    def uppercase_the_scots(self, name_portion):
        matches = re.search(self.scottish_re, name_portion)

        if matches:
            mc = matches.group('mc')
            first_letter = matches.group('first_letter')
            return re.sub(mc + first_letter, mc.title() + first_letter.upper(), name_portion)
        else:
            return name_portion

    def fix_case_for_possessives(self, name):
        return re.sub(r"(\w+)'S\b", "\\1's", name)


class OrganizationName(Name):
    abbreviations = {
        'acad': 'Academy',
        'assns': 'Associations',
        'assn': 'Association',
        'cmte': 'Committee',
        'cltn': 'Coalition',
        'inst': 'Institute',
        'corp': 'Corporation',
        'co': 'Company',
        'fedn' : 'Federation',
        'fed': 'Federal',
        'fzco': 'Company',
        'usa': 'USA',
        'us': 'United States',
        'dept': 'Department',
        'assoc': 'Associates',
        'natl': 'National',
        'nat\'l': 'National',
        'intl': 'International',
        'inc': 'Incorporated',
        'llc': 'LLC',
        'llp': 'LLP',
        'lp': 'LP',
        'plc': 'PLC',
        'ltd': 'Limited',
        'univ': 'University',
        'colls': 'Colleges',
        'coll': 'College',
        'amer': 'American',
        'ed': 'Educational',
    }
    filler_words = 'The And Of In For Group'.split()

    name = None

    #suffix = None

    def new(self, name):
        self.name = name
        return self

    def case_name_parts(self):
        if not self.is_mixed_case():
            self.name = self.name.title()
            self.name = self.uppercase_the_scots(self.name)

            if re.match(r'(?i)^\w*PAC$', self.name):
                self.name = self.name.upper() # if there's only one word that ends in PAC, make the whole thing uppercase
            else:
                self.name = re.sub(r'(?i)\bpac\b', 'PAC', self.name) # otherwise just uppercase the PAC part

            self.name = self.uppercase_the_scots(self.name)
            self.name = self.fix_case_for_possessives(self.name)

        return self

    def primary_name_parts(self):
        return [ self.without_extra_phrases() ]

    def __unicode__(self):
        return unicode(self.name)

    def __str__(self):
        return unicode(self.name).encode('utf-8')

    def without_extra_phrases(self):
        """Removes parenthethical and dashed phrases"""
        # the last parenthesis is optional, because sometimes they are truncated
        name = re.sub(r'\s*\([^)]*\)?\s*$', '', self.name)
        name = re.sub(r'(?i)\s* formerly.*$', '', name)
        name = re.sub(r'(?i)\s*and its affiliates$', '', name)
        name = re.sub(r'\bet al\b', '', name)
        
        # in some datasets, the name of an organization is followed by a hyphen and an abbreviated name, or a specific
        # department or geographic subdivision; we want to remove this extraneous stuff without breaking names like
        # Wal-Mart or Williams-Sonoma

        # if there's a hyphen at least four characters in, proceed
        if "-" in name:
            hyphen_parts = name.rsplit("-", 1)
            # if the part after the hyphen is shorter than the part before,
            # AND isn't either a number (often occurs in Union names) or a single letter (e.g., Tech-X),
            # AND the hyphen is preceded by either whitespace or at least four characters,
            # discard the hyphen and whatever follows
            if len(hyphen_parts[1]) < len(hyphen_parts[0]) and re.search(r'(\w{4,}|\s+)$', hyphen_parts[0]) and not re.match(r'^([a-zA-Z]|[0-9]+)$', hyphen_parts[1]):
                name = hyphen_parts[0].strip()

        return name

    def without_punctuation(self):
        name = re.sub(r'/', ' ', self.without_extra_phrases())
        return re.sub(r'[,.*:;+]*', '', name)

    def expand(self):
        return ' '.join(self.abbreviations.get(w.lower(), w) for w in self.without_punctuation().split())

    def kernel(self):
        """ The 'kernel' is an attempt to get at just the most pithy words in the name """
        stop_words = [ y.lower() for y in self.abbreviations.values() + self.filler_words ]
        kernel = ' '.join([ x for x in self.expand().split() if x.lower() not in stop_words ])

        # this is a hack to get around the fact that this is the only two-word phrase we want to block
        # amongst our stop words. if we end up with more, we may need a better way to do this
        kernel = re.sub(r'\s*United States', '', kernel)

        return kernel

    def crp_style_firm_name(self, with_et_al=True):
        if with_et_al:
            return ', '.join(self.kernel().split()[0:2] + ['et al'])
        else:
            return ', '.join(self.kernel().split()[0:2])


class PersonName(Name):
    honorific = None
    first = None
    middle = None
    last = None
    suffix = None
    nick = None

    family_name_prefixes = ('de', 'di', 'du', 'la', 'van', 'von')
    allowed_honorifics = ['mrs', 'mrs.']

    def new(self, first, last, **kwargs):
        self.first = first.strip()
        self.last = last.strip()

        self.set_and_clean_option('middle', kwargs)
        self.set_and_clean_option('suffix', kwargs)
        self.set_and_clean_option('honorific', kwargs)
        self.set_and_clean_option('nick', kwargs)

        return self

    def set_and_clean_option(self, optname, kwargs):
        optval = kwargs.get(optname)

        if optval:
            optval = optval.strip()
            setattr(self, optname, optval)

    def new_from_tokens(self, *args, **kwargs):
        """
            Takes in a name that has been split by spaces.
            Names which are in [last, first] format need to be preprocessed.
            The nickname must be in double quotes to be recognized as such.

            This can take name parts in in these orders:
            first, middle, last, nick, suffix, honorific
            first, middle, last, nick, suffix
            first, middle, last, suffix, honorific
            first, middle, last, honorific
            first, middle, last, suffix
            first, middle, last, nick
            first, last, honorific
            first, last, suffix
            first, last, nick
            first, middle, last
            first, last
            last
        """

        if kwargs.get('allow_quoted_nicknames'):
            args = [ x.strip() for x in args if not re.match(r'^[(]', x) ]
        else:
            args = [ x.strip() for x in args if not re.match(r'^[("]', x) ]

        if len(args) > 2:
            self.detect_and_fix_two_part_surname(args)

        # set defaults
        self.first = ''
        self.last = ''

        # the final few tokens should always be detectable, otherwise a last name
        if len(args):
            if self.is_an_honorific(args[-1]):
                self.honorific = args.pop()
                if not self.honorific[-1] == '.':
                    self.honorific += '.'
            if self.is_a_suffix(args[-1]):
                self.suffix = args.pop()
                if re.match(r'[js]r(?!\.)', self.suffix, re.IGNORECASE):
                    self.suffix += '.'
            if self.is_a_nickname(args[-1]):
                self.nick = args.pop()
            self.last = args.pop()

        num_remaining_parts = len(args)

        if num_remaining_parts == 3:
            # if we've still got this many parts, we'll consider what's left as first name
            # plus multi-part middle name
            self.first = args[0]
            self.middle = ' '.join(args[1:3])

        elif num_remaining_parts == 2:
            self.first, self.middle = args
            if len(self.middle) == 1:
                self.middle += '.'

        elif num_remaining_parts == 1:
            self.first = ' '.join(args)

        if self.first and len(self.first) == 1:
            self.first += '.'

        return self

    def is_a_suffix(self, name_part):
        return re.match(r'^%s$' % SUFFIX_RE, name_part, re.IGNORECASE)

    def is_an_honorific(self, name_part):
        return re.match(r'^\s*[dm][rs]s?[.,]?\s*$', name_part, re.IGNORECASE)

    def is_a_nickname(self, name_part):
        """
        Nicknames, in our data, often come wrapped in parentheses or the like. This detects those.
        """
        return re.match(r'^["(].*[")]$', name_part)

    def detect_and_fix_two_part_surname(self, args):
        """
        This detects common family name prefixes and joins them to the last name,
        so names like "De Kuyper" don't end up with "De" as a middle name.
        """
        i = 0
        while i < len(args) - 1:
            if args[i].lower() in self.family_name_prefixes:
                args[i] = ' '.join(args[i:i+2])
                del(args[i+1])
                break
            else:
                i += 1

    def __unicode__(self):
        return unicode(self.name_str())

    def __str__(self):
        return unicode(self.name_str()).encode('utf-8')

    def name_str(self):
        return ' '.join([x.strip() for x in [
            self.honorific if self.honorific and self.honorific.lower() in self.allowed_honorifics else None,
            self.first,
            self.middle,
            self.nick,
            self.last + (',' if self.suffix else ''),
            self.suffix
        ] if x])

    def case_name_parts(self):
        """
        Convert all the parts of the name to the proper case... carefully!
        """
        if not self.is_mixed_case():
            self.honorific = self.honorific.title() if self.honorific else None
            self.nick = self.nick.title() if self.nick else None

            if self.first:
                self.first = self.first.title()
                self.first = self.capitalize_and_punctuate_initials(self.first)

            if self.last:
                self.last = self.last.title()
                self.last = self.uppercase_the_scots(self.last)

            self.middle = self.middle.title() if self.middle else None

            if self.suffix:
                # Title case Jr/Sr, but uppercase roman numerals
                if re.match(r'(?i).*[js]r', self.suffix):
                    self.suffix = self.suffix.title()
                else:
                    self.suffix = self.suffix.upper()

        return self

    def is_only_initials(self, name_part):
        """
        Let's assume we have a name like "B.J." if the name is two to three
        characters and consonants only.
        """
        return re.match(r'(?i)[^aeiouy]{2,3}$', name_part)

    def capitalize_and_punctuate_initials(self, name_part):
        if self.is_only_initials(name_part):
            if '.' not in name_part:
                return ''.join([ '{0}.'.format(x.upper()) for x in name_part])
            else:
                return name_part
        else:
            return name_part

    def primary_name_parts(self, include_middle=False):
        if include_middle:
            return [ self.first, self.middle, self.last ]
        else:
            return [ self.first, self.last ]

    def as_dict(self):
        return { 'first': self.first, 'middle': self.middle, 'last': self.last, 'honorific': self.honorific, 'suffix': self.suffix }

    def __repr__(self):
        return self.as_dict()


class PoliticalMetadata(object):
    party = None
    state = None

    def plus_metadata(self, party, state):
        self.party = party
        self.state = state

        return self

    def __str__(self):
        if self.party or self.state:
            party_state = u"-".join([ x for x in [self.party, self.state] if x ]) # because presidential candidates are listed without a state
            return unicode(u"{0} ({1})".format(unicode(self.name_str()), party_state)).encode('utf-8')
        else:
            return unicode(self.name_str()).encode('utf-8')


class PoliticianName(PoliticalMetadata, PersonName):
    pass


class RunningMatesNames(PoliticalMetadata):

    def __init__(self, mate1, mate2):
        self.mate1 = mate1
        self.mate2 = mate2

    def name_str(self):
        return u' & '.join([unicode(self.mate1), unicode(self.mate2)])

    def __repr__(self):
        return self.__str__()

    def mates(self):
        return [ self.mate1, self.mate2 ]

    def is_mixed_case(self):
        for mate in self.mates():
            if mate.is_mixed_case():
                return True

        return False

    def case_name_parts(self):
        for mate in self.mates():
            mate.case_name_parts()

        return self



########NEW FILE########
__FILENAME__ = nicknames
# List of names which can be equated with each other
# Do not put names that cannot be considered equivalent
# in the same tuple, even if they have the same nickname.
# For instance, John and Jacob could both be shortened to
# Jack, but unless you want John and Jacob to be stand-ins
# for each other, they should not be together.
NICKNAMES = (
    ('Abigail', 'Abby'),
    ('Allan', 'Allen', 'Alan', 'Al'),
    ('Allison', 'Alison', 'Ali', 'Aly', 'Allie'),
    ('Andre', u'Andr\00e9'),
    ('Andrew', 'Andy', 'Drew'),
    ('Antonio', 'Anthony', 'Tony', 'Anton'),
    ('Barbara', 'Barb'),
    ('Benjamin', 'Ben'),
    ('Bernard', 'Bernie'),
    ('Calvin', 'Cal'),
    ('Charles', 'Chas', 'Chuck', 'Chucky', 'Charlie'),
    ('Christine', 'Christina', 'Chris'),
    ('Christopher', 'Chris'),
    ('Daniel', 'Dan', 'Danny'),
    ('David', 'Dave'),
    ('Dennis', 'Denny'),
    ('Donald', 'Don', 'Donny'),
    ('Douglas', 'Doug'),
    ('Edward', 'Ed', 'Eddie'),
    ('Elizabeth', 'Liz', 'Lizbet', 'Lizbeth', 'Beth', 'Lizzie'),
    ('Francis', 'Frank', 'Frankie'),
    ('Fredrick', 'Frederick', 'Fred', 'Freddy'),
    ('Gerard', 'Gerry', 'Jerry'),
    ('Gerald', 'Gerry', 'Jerry'),
    ('Gregory', 'Greg'),
    ('Harris', 'Harry', 'Harrison'),
    ('Henry', 'Hank'),
    ('Herbert', 'Herb'),
    ('Howard', 'Howie'),
    ('James', 'Jim', 'Jimmy'),
    ('Jerome', 'Jerry'),
    ('John', 'Jon', 'Johnny', 'Jack'),
    ('Joseph', 'Joe'),
    ('Judith', 'Judy'),
    ('Johnathan', 'John'),
    ('Jonathan', 'Jon'),
    ('Katherine', 'Kathy', 'Katie'),
    ('Catherine', 'Cathy', 'Kathy'),
    ('Kathleen', 'Kathy'),
    ('Kenneth', 'Ken', 'Kenny'),
    ('Lawrence', 'Laurence', 'Larry'),
    ('Lewis', 'Louis', 'Lou'),
    ('Matthew', 'Matt'),
    ('Margaret', 'Marge', 'Margie', 'Maggie', 'Meg'),
    ('Martin', 'Marty'),
    ('Melvin', 'Melvyn' ,'Mel'),
    ('Mervyn', 'Merv'),
    ('Michael', 'Mike'),
    ('Mitchell', 'Mitch'),
    ('Nicholas', 'Nick'),
    ('Patricia', 'Pat', 'Patty', 'Pati'),
    ('Patrick', 'Pat'),
    ('Peter', 'Pete'),
    ('Philip', 'Phillip', 'Phil'),
    ('Randall', 'Randy'),
    ('Richard', 'Rick', 'Dick', 'Rich'),
    ('Robert', 'Rob', 'Robby', 'Bobby', 'Bob'),
    ('Steven', 'Stephen', 'Steve'),
    ('Stephanie', 'Steph'),
    ('Stewart', 'Stuart', 'Stu'),
    ('Theodore', 'Ted', 'Teddy'),
    ('Terrance', 'Terry'),
    ('Thomas', 'Tom', 'Thom', 'Tommy'),
    ('Vernon', 'Vern'),
    ('William', 'Bill', 'Billy', 'Will', 'Willy'),
    ('Willis', 'Will'),
)

########NEW FILE########
__FILENAME__ = test_name_cleaver
from cleaver import PoliticianNameCleaver, OrganizationNameCleaver, \
        IndividualNameCleaver, UnparseableNameException

try:
    import unittest2 as unittest
except ImportError:
    import unittest


class TestPoliticianNameCleaver(unittest.TestCase):

    def test_case_converts_in_non_mixed_case_names_only(self):
        self.assertEqual('Antonio dAlesio', str(PoliticianNameCleaver('Antonio dAlesio').parse()))

    def test_upper_case_scot_with_party(self):
        self.assertEqual('Emory MacDonald', str(PoliticianNameCleaver('MACDONALD, EMORY (R)').parse()))

    def test_last_first_mixed_case_scot_with_party(self):
        self.assertEqual('Emory MacDonald', str(PoliticianNameCleaver('MacDonald, Emory (R)').parse()))

    def test_first_last_mixed_case_with_party(self):
        self.assertEqual('Nancy Pelosi', str(PoliticianNameCleaver('Nancy Pelosi (D)').parse()))

    def test_not_everything_is_a_scot(self):
        self.assertEqual('Adam Mack', str(PoliticianNameCleaver('ADAM MACK').parse()))
        self.assertEqual('Don Womackey', str(PoliticianNameCleaver('DON WOMACKEY').parse()))

    def test_last_first(self):
        self.assertEqual('Albert Gore', str(PoliticianNameCleaver('Gore, Albert').parse()))

    def test_pile_it_on(self):
        self.assertEqual('Milton Elmer McCullough, Jr.', str(PoliticianNameCleaver('Milton Elmer "Mac" McCullough, Jr (3)').parse()))

    def test_pile_it_on_two(self):
        self.assertEqual('William Steve Southerland, II', str(PoliticianNameCleaver('William Steve Southerland  II (R)').parse()))

    def test_pile_it_on_three(self):
        self.assertEqual('Edward Thomas O\'Donnell, Jr.', str(PoliticianNameCleaver('Edward Thomas O\'Donnell, Jr (D)').parse()))

    def test_standardize_running_mate_names(self):
        self.assertEqual('John Kasich & Mary Taylor', str(PoliticianNameCleaver('Kasich, John & Taylor, Mary').parse()))

    def test_standardize_running_mate_names_with_slash(self):
        self.assertEqual('Mitt Romney & Paul D. Ryan', str(PoliticianNameCleaver('ROMNEY, MITT / RYAN, PAUL D.').parse()))

    def test_we_dont_need_no_steeenking_nicknames(self):
        self.assertEqual('Robert M. McDonnell', str(PoliticianNameCleaver('McDonnell, Robert M (Bob)').parse()))
        self.assertEqual('John J. Duncan, Jr.', str(PoliticianNameCleaver('John J (Jimmy) Duncan Jr (R)').parse()))
        self.assertEqual('Christopher Bond', str(PoliticianNameCleaver('Christopher "Kit" Bond').parse()))

        self.assertEqual('"Kit"', IndividualNameCleaver('Christopher "Kit" Bond').parse().nick)

    def test_capitalize_roman_numeral_suffixes(self):
        self.assertEqual('Ken Cuccinelli, II', str(PoliticianNameCleaver('KEN CUCCINELLI II').parse()))
        self.assertEqual('Ken Cuccinelli, II', str(PoliticianNameCleaver('CUCCINELLI II, KEN').parse()))
        self.assertEqual('Ken T. Cuccinelli, II', str(PoliticianNameCleaver('CUCCINELLI II, KEN T').parse()))
        self.assertEqual('Ken T. Cuccinelli, II', str(PoliticianNameCleaver('CUCCINELLI, KEN T II').parse()))
        self.assertEqual('Ken Cuccinelli, IV', str(PoliticianNameCleaver('CUCCINELLI IV, KEN').parse()))
        self.assertEqual('Ken Cuccinelli, IX', str(PoliticianNameCleaver('CUCCINELLI IX, KEN').parse()))

    def test_name_with_two_part_last_name(self):
        self.assertEqual('La Mere', PoliticianNameCleaver('Albert J La Mere').parse().last)
        self.assertEqual('Di Souza', PoliticianNameCleaver('Dinesh Di Souza').parse().last)

    def test_deals_with_last_names_that_look_like_two_part_but_are_not(self):
        name = PoliticianNameCleaver('Quoc Van (D)').parse()
        self.assertEqual('Quoc', name.first)
        self.assertEqual('Van', name.last)

    def test_doesnt_misinterpret_roman_numeral_characters_in_last_name_as_suffix(self):
        self.assertEqual('Vickers', PoliticianNameCleaver('Audrey C Vickers').parse().last)

    def test_multiple_middle_names(self):
        self.assertEqual('Swift Eagle', PoliticianNameCleaver('Alexander Swift Eagle Justice').parse().middle)

    def test_edgar_de_lisle_ross(self):
        name = PoliticianNameCleaver('Edgar de L\'Isle Ross (R)').parse()
        self.assertEqual('Edgar', name.first)
        self.assertEqual('de L\'Isle', name.middle)
        self.assertEqual('Ross', name.last)
        self.assertEqual(None, name.suffix)

    def test_with_metadata(self):
        self.assertEqual('Charles Schumer (D-NY)', str(PoliticianNameCleaver('Charles Schumer').parse().plus_metadata('D', 'NY')))
        self.assertEqual('Barack Obama (D)', str(PoliticianNameCleaver('Barack Obama').parse().plus_metadata('D', '')))
        self.assertEqual('Charles Schumer (NY)', str(PoliticianNameCleaver('Charles Schumer').parse().plus_metadata('', 'NY')))
        self.assertEqual('Jerry Leon Carroll', str(PoliticianNameCleaver('Jerry Leon Carroll').parse().plus_metadata('', '')))  # only this one guy is missing both at the moment

    def test_running_mates_with_metadata(self):
        self.assertEqual('Ted Strickland & Lee Fischer (D-OH)', str(PoliticianNameCleaver('STRICKLAND, TED & FISCHER, LEE').parse().plus_metadata('D', 'OH')))

    def test_names_with_weird_parenthetical_stuff(self):
        self.assertEqual('Lynn Swann', str(PoliticianNameCleaver('SWANN, LYNN (COMMITTEE 1)').parse()))

    def test_handles_empty_names(self):
        self.assertEqual('', str(PoliticianNameCleaver('').parse()))

    def test_capitalize_irish_names(self):
        self.assertEqual('Sean O\'Leary', str(PoliticianNameCleaver('SEAN O\'LEARY').parse()))

    def test_primary_name_parts(self):
        self.assertEqual(['Robert', 'Geoff', 'Smith'], PoliticianNameCleaver('Smith, Robert Geoff').parse().primary_name_parts(include_middle=True))
        self.assertEqual(['Robert', 'Smith'], PoliticianNameCleaver('Smith, Robert Geoff').parse().primary_name_parts())

    def test_van_is_valid_first_name(self):
        self.assertEqual(['Van', 'Morrison'], PoliticianNameCleaver('Van Morrison').parse().primary_name_parts())

    def test_alternate_running_mates_format(self):
        self.assertEqual('Obama/Biden 2012', str(PoliticianNameCleaver('2012, Obama/Biden').parse()))

    def test_alternate_punctuation(self):
        self.assertEqual('Charles W. Boustany, Jr.', str(PoliticianNameCleaver('Charles W. Boustany Jr.').parse()))


class TestOrganizationNameCleaver(unittest.TestCase):

    def test_capitalize_pac(self):
        self.assertEqual('Nancy Pelosi Leadership PAC', str(OrganizationNameCleaver('NANCY PELOSI LEADERSHIP PAC').parse()))

    def test_make_single_word_names_ending_in_pac_all_uppercase(self):
        self.assertEqual('ECEPAC', str(OrganizationNameCleaver('ECEPAC').parse()))

    def test_names_starting_with_PAC(self):
        self.assertEqual('PAC For Engineers', str(OrganizationNameCleaver('PAC FOR ENGINEERS').parse()))
        self.assertEqual('PAC 102', str(OrganizationNameCleaver('PAC 102').parse()))

    def test_doesnt_bother_names_containing_string_pac(self):
        self.assertEqual('Pacific Trust', str(OrganizationNameCleaver('PACIFIC TRUST').parse()))

    def test_capitalize_scottish_names(self):
        self.assertEqual('McDonnell Douglas', str(OrganizationNameCleaver('MCDONNELL DOUGLAS').parse()))
        self.assertEqual('MacDonnell Douglas', str(OrganizationNameCleaver('MACDONNELL DOUGLAS').parse()))

    def test_dont_capitalize_just_anything_starting_with_mac(self):
        self.assertEqual('Machinists/Aerospace Workers Union', str(OrganizationNameCleaver('MACHINISTS/AEROSPACE WORKERS UNION').parse()))

    def test_expand(self):
        self.assertEqual('Raytheon Corporation', OrganizationNameCleaver('Raytheon Corp.').parse().expand())
        self.assertEqual('Massachusetts Institute of Technology', OrganizationNameCleaver('Massachusetts Inst. of Technology').parse().expand())

    def test_expand_with_two_tokens_to_expand(self):
        self.assertEqual('Merck & Company Incorporated', OrganizationNameCleaver('Merck & Co., Inc.').parse().expand())

    def test_dont_strip_after_hyphens_too_soon_in_a_name(self):
        self.assertEqual('US-Russia Business Council', OrganizationNameCleaver('US-Russia Business Council').parse().kernel())
        self.assertEqual('Wal-Mart Stores', OrganizationNameCleaver('Wal-Mart Stores, Inc.').parse().kernel())

        # these were new after the hyphen rewrite
        self.assertEqual('Coca-Cola Company', OrganizationNameCleaver('Coca-Cola Co').parse().expand()) # used to return 'Coca'
        self.assertEqual('Rolls-Royce PLC', OrganizationNameCleaver('Rolls-Royce PLC').parse().expand()) # used to return 'Rolls'

    def test_drop_postname_hyphen_phrases(self):
        self.assertEqual('Lawyers For Better Government', OrganizationNameCleaver('LAWYERS FOR BETTER GOVERNMENT-ILLINOIS').parse().without_extra_phrases())
        self.assertEqual('Jobs Opportunity And Freedom Political Action Committee', OrganizationNameCleaver('JOBS OPPORTUNITY AND FREEDOM POLITICAL ACTION COMMITTEE - JOFPAC').parse().without_extra_phrases())

    def test_kernel(self):
        """
        Intended to get only the unique/meaningful words out of a name
        """
        self.assertEqual('Massachusetts Technology', OrganizationNameCleaver('Massachusetts Inst. of Technology').parse().kernel())
        self.assertEqual('Massachusetts Technology', OrganizationNameCleaver('Massachusetts Institute of Technology').parse().kernel())

        self.assertEqual('Walsh', OrganizationNameCleaver('The Walsh Group').parse().kernel())

        self.assertEqual('Health Net', OrganizationNameCleaver('Health Net Inc').parse().kernel())
        self.assertEqual('Health Net', OrganizationNameCleaver('Health Net, Inc.').parse().kernel())

        self.assertEqual('Distilled Spirits Council', OrganizationNameCleaver('Distilled Spirits Council of the U.S., Inc.').parse().kernel())

    def test_handles_empty_names(self):
        self.assertEqual('', str(OrganizationNameCleaver('').parse()))


class TestIndividualNameCleaver(unittest.TestCase):
    cleaver = IndividualNameCleaver

    def cleave_to_str(self, name_input):
        return str(self.cleaver(name_input).parse())

    def test_allow_names_to_have_only_last_name(self):
        self.assertEqual('Lee', self.cleave_to_str('LEE'))

    def test_all_kinds_of_crazy(self):
        self.assertEqual('Stanford Z. Rothschild', self.cleave_to_str('ROTHSCHILD 212, STANFORD Z MR'))

    def test_jr_and_the_like_end_up_at_the_end(self):
        self.assertEqual('Frederick A. "Tripp" Baird, III', self.cleave_to_str('Baird, Frederick A "Tripp" III'))

    def test_nicknames_suffixes_and_honorifics(self):
        self.assertEqual('Frederick A. "Tripp" Baird, III', self.cleave_to_str('Baird, Frederick A "Tripp" III Mr'))
        self.assertEqual('Frederick A. "Tripp" Baird, III', self.cleave_to_str('Baird, Mr Frederick A "Tripp" III'))

    def test_throw_out_mr(self):
        self.assertEqual('T. Boone Pickens', self.cleave_to_str('Mr T Boone Pickens'))
        self.assertEqual('T. Boone Pickens', self.cleave_to_str('Mr. T Boone Pickens'))
        self.assertEqual('T. Boone Pickens', self.cleave_to_str('Pickens, T Boone Mr'))
        self.assertEqual('John L. Nau', self.cleave_to_str(' MR JOHN L NAU,'))

    def test_keep_the_mrs(self):
        self.assertEqual('Mrs. T. Boone Pickens', self.cleave_to_str('Mrs T Boone Pickens'))
        self.assertEqual('Mrs. T. Boone Pickens', self.cleave_to_str('Mrs. T Boone Pickens'))
        self.assertEqual('Mrs. Stanford Z. Rothschild', self.cleave_to_str('ROTHSCHILD 212, STANFORD Z MRS'))

    def test_mrs_walton(self):
        self.assertEqual('Mrs. Jim Walton', self.cleave_to_str('WALTON, JIM MRS'))

    def test_capitalize_roman_numeral_suffixes(self):
        self.assertEqual('Ken Cuccinelli, II', self.cleave_to_str('KEN CUCCINELLI II'))
        self.assertEqual('Ken Cuccinelli, II', self.cleave_to_str('CUCCINELLI II, KEN'))
        self.assertEqual('Ken Cuccinelli, IV', self.cleave_to_str('CUCCINELLI IV, KEN'))
        self.assertEqual('Ken Cuccinelli, IX', self.cleave_to_str('CUCCINELLI IX, KEN'))

    def test_capitalize_scottish_last_names(self):
        self.assertEqual('Ronald McDonald', self.cleave_to_str('RONALD MCDONALD'))
        self.assertEqual('Old MacDonald', self.cleave_to_str('OLD MACDONALD'))

    def test_capitalizes_and_punctuates_initials(self):
        self.assertEqual('B.L. Schwartz', self.cleave_to_str('SCHWARTZ, BL'))

    def test_capitalizes_initials_but_not_honorifics(self):
        self.assertEqual('John Koza', self.cleave_to_str('KOZA, DR JOHN'))

    def test_doesnt_overzealously_detect_doctors(self):
        self.assertEqual('Drew Maloney', self.cleave_to_str('Maloney, Drew'))

    def test_unfazed_by_weird_cop_cont_parenthetical_phrases(self):
        self.assertEqual('Jacqueline A. Schmitz', self.cleave_to_str('SCHMITZ (COP CONT ), JACQUELINE A'))
        self.assertEqual('Hannah Mellman', self.cleave_to_str('MELLMAN (CONT\'D), HANNAH (CONT\'D)'))
        self.assertEqual('Tod Preston', self.cleave_to_str('PRESTON (C O P CONT\'D ), TOD'))

    def test_mr_and_mrs(self):
        self.assertEqual('Kenneth L. Lay', self.cleave_to_str('LAY, KENNETH L MR & MRS'))

    def test_primary_name_parts(self):
        self.assertEqual(['Robert', 'Geoff', 'Smith'], self.cleaver('Smith, Robert Geoff').parse().primary_name_parts(include_middle=True))
        self.assertEqual(['Robert', 'Smith'], self.cleaver('Smith, Robert Geoff').parse().primary_name_parts())

    def test_initialed_first_name(self):
        self.assertEqual('C. Richard Bonebrake', self.cleave_to_str('C. RICHARD BONEBRAKE'))

    def test_degree_gets_thrown_out(self):
        self.assertEqual('C. Richard Bonebrake', self.cleave_to_str('C. RICHARD BONEBRAKE, M.D.'))
        self.assertEqual('John W. Noble, Jr.', self.cleave_to_str('NOBLE JR., JOHN W. MD'))
        self.assertEqual('John W. Noble, Jr.', self.cleave_to_str('NOBLE JR., JOHN W. PHD MD'))
        self.assertEqual('Barney Dinosaur', self.cleave_to_str('DINOSAUR, BARNEY J.D.'))

    def test_two_part_names_skip_suffix_check(self):
        self.assertEqual('Vi Simpson', self.cleave_to_str('SIMPSON, VI'))
        self.assertEqual('J.R. Reskovac', self.cleave_to_str('RESKOVAC, JR'))

    def test_honorific_and_suffix_both_at_end(self):
        self.assertEqual('Paul De Cleva, Sr.', self.cleave_to_str('DE CLEVA, PAUL MR SR'))
        self.assertEqual('Bill Marriott, Jr.', self.cleave_to_str('MARRIOTT, BILL MR JR'))

    def test_considers_double_initial_a_first_name(self):
        self.assertEqual('C.W. Bill Young', self.cleave_to_str('C.W. Bill Young'))

        self.assertEqual('C.A. "Dutch" Ruppersberger', self.cleave_to_str('C.A. "Dutch" Ruppersberger'))

        dutch = IndividualNameCleaver('C.A. "Dutch" Ruppersberger').parse()
        self.assertEqual('"Dutch"', dutch.nick)
        self.assertIsNone(dutch.middle)
        self.assertEqual('C.A.', dutch.first)


class TestCapitalization(unittest.TestCase):

    def test_overrides_dumb_python_titlecasing_for_apostrophes(self):
        self.assertEqual('Phoenix Women\'s Health Center', str(OrganizationNameCleaver('PHOENIX WOMEN\'S HEALTH CENTER').parse()))


class TestOrganizationNameCleaverForIndustries(unittest.TestCase):

    def test_capitalizes_letter_after_slash(self):
        self.assertEqual('Health Services/Hmos', str(OrganizationNameCleaver('HEALTH SERVICES/HMOS').parse()))
        self.assertEqual('Lawyers/Law Firms', str(OrganizationNameCleaver('LAWYERS/LAW FIRMS').parse()))

    def test_capitalizes_letter_after_hyphen(self):
        self.assertEqual('Non-Profit Institutions', str(OrganizationNameCleaver('NON-PROFIT INSTITUTIONS').parse()))
        self.assertEqual('Pro-Israel', str(OrganizationNameCleaver('PRO-ISRAEL').parse()))


class TestUnicode(unittest.TestCase):

    def test_individual(self):
        self.assertEqual(u'Tobias F\u00fcnke'.encode('utf-8'),
                str(IndividualNameCleaver(u'F\u00fcnke, Tobias').parse()))

    def test_politician(self):
        self.assertEqual(u'Tobias F\u00fcnke'.encode('utf-8'),
                str(PoliticianNameCleaver(u'F\u00fcnke, Tobias').parse()))

    def test_politician_plus_metadata(self):
        self.assertEqual(u'Tobias F\u00fcnke (D-CA)'.encode('utf-8'),
                str(PoliticianNameCleaver(u'F\u00fcnke, Tobias').parse().plus_metadata('D', 'CA')))

    def test_politician_running_mates(self):
        self.assertEqual(u'Tobias F\u00fcnke & Lindsay F\u00fcnke'.encode('utf-8'),
                str(PoliticianNameCleaver(u'F\u00fcnke, Tobias & F\u00fcnke, Lindsay').parse()))

    def test_running_mates_with_metadata(self):
        self.assertEqual(u'Ted Strickland & Le\u00e9 Fischer (D-OH)'.encode('utf-8'),
                str(PoliticianNameCleaver(u'STRICKLAND, TED & FISCHER, LE\u00c9').parse().plus_metadata('D', 'OH')))

    def test_organization(self):
        self.assertEqual(u'\u00C6tna, Inc.'.encode('utf-8'),
                str(OrganizationNameCleaver(u'\u00C6tna, Inc.').parse()))


class TestErrors(unittest.TestCase):

    def test_unparseable_politician_name(self):
        with self.assertRaises(UnparseableNameException):
            PoliticianNameCleaver("mr & mrs").parse()

    def test_unparseable_individual_name(self):
        with self.assertRaises(UnparseableNameException):
            IndividualNameCleaver("mr & mrs").parse()

    # this ought to have a test, but I'm not sure how to break this one.
    #def test_unparseable_organization_name(self):
    #    with self.assertRaises(UnparseableNameException):
    #        OrganizationNameCleaver("####!!!").parse()

    def test_parse_safe__individual(self):
        pass
        #with self.assertRaises(UnparseableNameException):
        #    IndividualNameCleaver("BARDEN PHD J D, R CHRISTOPHER").parse()

        #self.assertEqual('BARDEN PHD J D, R CHRISTOPHER', str(IndividualNameCleaver('BARDEN PHD J D, R CHRISTOPHER').parse(safe=True)))

        #with self.assertRaises(UnparseableNameException):
        #    IndividualNameCleaver("gobbledy blah bloop!!!.p,.lcrg%%% #$<").parse()

        #self.assertEqual('gobbledy blah bloop!!!.p,.lcrg%%% #$<', str(IndividualNameCleaver('gobbledy blah bloop!!!.p,.lcrg%%% #$<').parse(safe=True)))

    def test_parse_safe__politician(self):
        pass
        #with self.assertRaises(UnparseableNameException):
        #    PoliticianNameCleaver("BARDEN PHD J D, R CHRISTOPHER").parse()

        #self.assertEqual('BARDEN PHD J D, R CHRISTOPHER', str(PoliticianNameCleaver('BARDEN PHD J D, R CHRISTOPHER').parse(safe=True)))

        #with self.assertRaises(UnparseableNameException):
        #    PoliticianNameCleaver("gobbledy gook bah bah bloop!!!.p,.lcrg%%% #$<").parse()

        #self.assertEqual('gobbledy gook bah bah bloop!!!.p,.lcrg%%% #$<', str(PoliticianNameCleaver('gobbledy gook bah bah bloop!!!.p,.lcrg%%% #$<').parse(safe=True)))

    def test_parse_safe__organization(self):
        self.assertEqual('', OrganizationNameCleaver(None).parse(safe=True))

########NEW FILE########
