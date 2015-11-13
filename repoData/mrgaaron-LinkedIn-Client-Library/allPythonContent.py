__FILENAME__ = nlp
#! usr/bin/env python
import re, nltk

class TextualAnalyzer(object):
    def __init__(self, txt, source):
        self.sources = {}
        text = nltk.text.Text(txt)
        self.sources[source] = {}
        self.cfds = {}
        self.sources[source]['text'] = text
        self.sources[source]['collocations'] = text.collocations().split(';')
        self.sources[source]['freq_dist'] = text.vocab()
    
    def register(self, txt, source):
        if source not in self.sources.keys():
            text = nltk.text.Text(txt)
            self.sources[source] = {}
            self.sources[source]['text'] = text.tokens
            self.sources[source]['collocations'] = text.collocations().split(';')
            self.sources[source]['freq_dist'] = text.vocab()
        else:
            raise KeyError('Source already found in internal dictionary.  Please use a different source name.')
    
    def generate_cfd(self, srca, srcb):
        cdna = [(w, srca) for w in self.sources[srca]['text']]
        cdnb = [(w, srcb) for w in self.sources[srcb]['text']]
        cfdp = [cdnb + cdna]
        self.cfds[srca+ ', ' + srcb] = nltk.ConditionalFreqDist(cfdp)
    
    def tag(self, source, tagger=None):
        if not tagger:
            self.sources[source]['tagged'] = nltk.pos_tag(self.sources[source]['text'])
        else:
            self.sources[source]['tagged'] = tagger.tag(self.sources[source]['text'])
        
    def chunk(self, source, chunker=None):
        if not self.sources[source]['tagged']:
            self.tag(source)
        grammar = r"""
            NP: {<DT|PP>?<JJ.*>*<NN.*>}
                {<NNP>+}
            VP: {<JJ.*>?<RB>?<VB+><NN.*>*}
            """
        cp = nltk.RegexpParser(grammar)
        self.sources[source]['chunked'] = cp.parse(self.sources[source]['tagged'])

########NEW FILE########
__FILENAME__ = helpers
#! usr/bin/env python

def create_json(objs):
    assert type(objs) == type(dict()), 'Passed object must be a dict with keys "results" and "total"'
    json_skeleton = {'total': objs['total'], 'results': [], 'success': True}
    for obj in objs['results']:
        assert hasattr(obj, 'jsonify'), 'Passed objects must be convertible to json with a jsonify() method'
        json_skeleton['results'].append(obj.jsonify())
    return json_skeleton
########NEW FILE########
__FILENAME__ = lixml
from lxml import etree
import mappers
import re

class LinkedInXMLParser(object):
    def __init__(self, content):
        self.routing = {
            'network': self.__parse_network_updates,
            'person': self.__parse_personal_profile,
            'job-poster': self.__parse_personal_profile,
            'update-comments': self.__parse_update_comments,
            'connections': self.__parse_connections,
            'error': self.__parse_error,
            'position': self.__parse_position,
            'skill': self.__parse_skills,
            'education': self.__parse_education,
            'people': self.__parse_people_collection,
            'twitter-account': self.__parse_twitter_accounts,
            'member-url': self.__parse_member_url_resources
        }
        self.tree = etree.fromstring(content)
        self.root = self.tree.tag
        self.results = self.__forward_tree(self.tree, self.root)
    
    def __forward_tree(self, tree, root):
        results = self.routing[root](tree)
        return results
    
    def __parse_network_updates(self, tree):
        content = LinkedInNetworkUpdateParser(tree).results
        return content
    
    def __parse_personal_profile(self, tree):
        content = LinkedInProfileParser(tree).results
        return content
    
    def __parse_update_comments(self, tree):
        content = LinkedInNetworkCommentParser(tree).results
        return content
    
    def __parse_connections(self, tree):
        content = LinkedInConnectionsParser(tree).results
        return content
        
    def __parse_skills(self, tree):
        content = LinkedInSkillsParser(tree).results
        return content
    
    def __parse_error(self, tree):
        content = LinkedInErrorParser(tree).results
        return content
    
    def __parse_position(self, tree):
        content = LinkedInPositionParser(tree).results
        return content

    def __parse_education(self, tree):
        content = LinkedInEducationParser(tree).results
        return content
        
    def __parse_twitter_accounts(self, tree):
        content = LinkedInTwitterAccountParser(tree).results
        return content
        
    def __parse_member_url_resources(self, tree):
        content = LinkedInMemberUrlResourceParser(tree).results
        return content
    
    def __parse_people_collection(self, tree):
        ppl, n = tree.getchildren()
        result_count = int(n.text)
        content = []
        for p in ppl:
            rslts = LinkedInProfileParser(p).results
            content.append(rslts)
        return content
        
class LinkedInNetworkUpdateParser(LinkedInXMLParser):
    def __init__(self, content):
        self.xpath_collection = {
            'first-name': etree.XPath('update-content/person/first-name'),
            'profile-url': etree.XPath('update-content/person/site-standard-profile-request/url'),
            'last-name': etree.XPath('update-content/person/last-name'),
            'timestamp': etree.XPath('timestamp'),
            'updates': etree.XPath('updates'),
            'update': etree.XPath('updates/update'),
            'update-type': etree.XPath('update-type'),
            'update-key': etree.XPath('update-key'),
            #special paths for question/answer updates
            'qa-first-name': etree.XPath('update-content/question/author/first-name'), 
            'qa-last-name': etree.XPath('update-content/question/author/last-name'),   
            'qa-profile-url': etree.XPath('update-content/question/web-url'),
            'jobp-title': etree.XPath('update-content/job/position/title'),
            'jobp-company': etree.XPath('update-content/job/company/name'),
            'jobp-url': etree.XPath('update-content/job/site-job-request/url')
        }
        self.tree = content
        total = self.xpath_collection['updates'](self.tree)[0].attrib['total']
        self.results = self.__build_data(self.tree, total)
    
    def __build_data(self, tree, total):
        results = {}
        objs = []
        results['total'] = total
        updates = self.xpath_collection['update'](tree)
        for u in updates:
            types = self.xpath_collection['update-type'](u)[0].text
            if types == 'QSTN' or types == 'ANSW':
                data = self.__qa_data_builder(u)
            elif types == 'JOBP':
                data = self.__jobp_data_builder(u)
            else:
                data = self.__generic_data_builder(u)
            obj = self.__objectify(data, types, u)
            objs.append(obj)
        results['results'] = objs
        return results
    
    def __generic_data_builder(self, u):
        data = {}
        try:
            data['update_key'] = self.xpath_collection['update-key'](u)[0].text.strip()
        except IndexError:
            pass
        data['first_name'] = self.xpath_collection['first-name'](u)[0].text.strip()
        data['profile_url'] = self.xpath_collection['profile-url'](u)[0].text.strip()
        data['last_name'] = self.xpath_collection['last-name'](u)[0].text.strip()
        data['timestamp'] = self.xpath_collection['timestamp'](u)[0].text.strip()
        return data
        
    def __qa_data_builder(self, u):
        data = {}
        data['first_name'] = self.xpath_collection['qa-first-name'](u)[0].text.strip()
        try:
            data['profile_url'] = self.xpath_collection['qa-profile-url'](u)[0].text.strip()
        except IndexError: #the answers url is in a different spot, that's handled by the object
            pass
        data['last_name'] = self.xpath_collection['qa-last-name'](u)[0].text.strip()
        data['timestamp'] = self.xpath_collection['timestamp'](u)[0].text.strip()
        return data
    
    def __jobp_data_builder(self, u):
        data = {}
        data['job_title'] = self.xpath_collection['jobp-title'](u)[0].text.strip()
        data['job_company'] = self.xpath_collection['jobp-company'](u)[0].text.strip()
        data['profile_url'] = self.xpath_collection['jobp-url'](u)[0].text.strip()
        return data
    
    def __objectify(self, data, u_type, u):
        if u_type == 'STAT':
            obj = mappers.NetworkStatusUpdate(data, u)
        elif u_type == 'CONN':
            obj = mappers.NetworkConnectionUpdate(data, u)
        elif u_type == 'JGRP':
            obj = mappers.NetworkGroupUpdate(data, u)
        elif u_type == 'NCON':
            obj = mappers.NetworkNewConnectionUpdate(data, u)
        elif u_type == 'CCEM':
            obj = mappers.NetworkAddressBookUpdate(data, u)
        elif u_type == 'QSTN':
            obj = mappers.NetworkQuestionUpdate(data, u)
        elif u_type == 'ANSW':
            obj = mappers.NetworkAnswerUpdate(data, u)
        elif u_type == 'JOBP':
            obj = mappers.NetworkJobPostingUpdate(data, u)
        else:
            obj = mappers.NetworkUpdate(data, u)
        return obj
    
class LinkedInProfileParser(LinkedInXMLParser):
    def __init__(self, content):
        self.tree = content
        self.results = self.__build_data(self.tree)
    
    def __build_data(self, tree):
        results = []
        for p in tree.xpath('/person'):
            person = {}
            for item in p.getchildren():
                if item.tag == 'location':
                    person['location'] = item.getchildren()[0].text
                else:
                    person[re.sub(r'-', '_', item.tag)] = item.text
            obj = mappers.Profile(person, p)
            results.append(obj)
        
        # deal with hierarchical results in a somewhat kludgy way
        def fix(s):
            return re.sub(r'-', '_', s)
        def build_name(parent, item):
            s = ''
            p = item.getparent()
            while p != parent:
                s = fix(p.tag) + '_' + s
                p = p.getparent()
            s += fix(item.tag)
            return s
        if not results:
            person = {}
            for item in tree.iterdescendants():
                clean = item.text and item.text.strip()
                if clean:
                    name = build_name(tree, item)
                    if name in person:
                        value = person[name]
                        if type(value) != list:
                            person[name] = [value, clean]
                        else:
                            person[name].append(clean)
                    else:
                        person[name] = clean
            obj = mappers.Profile(person, tree)
            results.append(obj)
        if False: #not results: # the original, elegant but wrong way
            person = {}
            for item in tree.getchildren():
                person[re.sub(r'-', '_', item.tag)] = item.text
            obj = mappers.Profile(person, tree)
            results.append(obj)
        return results
    
class LinkedInNetworkCommentParser(LinkedInXMLParser):
    def __init__(self, content):
        self.tree = content
        self.comment_xpath = etree.XPath('update-comment')
        self.results = self.__build_data(self.tree)
    
    def __build_data(self, tree):
        if not tree.getchildren():
            return []
        else:
            objs = []
            for c in self.comment_xpath(tree):
                obj = mappers.NetworkUpdateComment(c)
                objs.append(obj)
            return objs
        
class LinkedInConnectionsParser(LinkedInXMLParser):
    def __init__(self, content):
        self.tree = content
        self.total = content.attrib['total']
        self.results = self.__build_data(self.tree)
    
    def __build_data(self, tree):
        results = {}
        results['results'] = []
        for p in tree.getchildren():
            parsed = LinkedInXMLParser(etree.tostring(p)).results[0]
            results['results'].append(parsed)
        results['total'] = self.total
        return results
    
class LinkedInErrorParser(LinkedInXMLParser):
    def __init__(self, content):
        self.tree = content
        self.xpath_collection = {
            'status': etree.XPath('status'),
            'timestamp': etree.XPath('timestamp'),
            'error-code': etree.XPath('error-code'),
            'message': etree.XPath('message')
        }
        self.results = self.__build_data(self.tree)
    
    def __build_data(self, tree):
        data = {}
        data['status'] = self.xpath_collection['status'](tree)[0].text.strip()
        data['timestamp'] = self.xpath_collection['timestamp'](tree)[0].text.strip()
        data['error_code'] = self.xpath_collection['error-code'](tree)[0].text.strip()
        data['message'] = self.xpath_collection['message'](tree)[0].text.strip()
        results = mappers.LinkedInError(data, tree)
        return results
    
class LinkedInPositionParser(LinkedInXMLParser):
    def __init__(self, content):
        self.tree = content
        self.xpath_collection = {
            'id': etree.XPath('id'),
            'title': etree.XPath('title'),
            'summary': etree.XPath('summary'),
            'start-date-year': etree.XPath('start-date/year'),
            'end-date-year': etree.XPath('end-date/year'),
            'start-date-month': etree.XPath('start-date/month'),
            'end-date-month': etree.XPath('end-date/month'),
            'is-current': etree.XPath('is-current'),
            'company-id': etree.XPath('company/id'),
            'company': etree.XPath('company/name')
        }
        self.results = self.__build_data(self.tree)
    
    def __build_data(self, tree):
        data = dict(
                [(re.sub('-','_',key),self.xpath_collection[key](tree)[0].text) for key in self.xpath_collection if len(self.xpath_collection[key](tree)) > 0]
                )
        results = mappers.Position(data, tree)
        return results

class LinkedInEducationParser(LinkedInXMLParser):
    def __init__(self, content):
        self.tree = content
        self.xpath_collection = {
            'id': etree.XPath('id'),
            'school-name': etree.XPath('school-name'),
            'field-of-study': etree.XPath('field-of-study'),
            'start-date': etree.XPath('start-date/year'),
            'end-date': etree.XPath('end-date/year'),
            'degree': etree.XPath('degree'),
            'activities': etree.XPath('activities')
        }
        self.results = self.__build_data(self.tree)
    
    def __build_data(self, tree):
        data = {}
        for n in tree.getchildren():
            if not n.getchildren():
                data[re.sub('-', '_', n.tag)] = n.text
            else:
                data[re.sub('-', '_', n.tag)] = n.getchildren()[0].text
        results = mappers.Education(data, tree)
        return results
        
        
class LinkedInTwitterAccountParser(LinkedInXMLParser):
    def __init__(self, content):
        self.tree = content
        self.xpath_collection = {
            'provider-account-id': etree.XPath('provider-account-id'),
            'provider-account-name': etree.XPath('provider-account-name'),
        }
        self.results = self.__build_data(self.tree)
    
    def __build_data(self, tree):
        data = dict(
                [(re.sub('-','_',key),self.xpath_collection[key](tree)[0].text) for key in self.xpath_collection if len(self.xpath_collection[key](tree)) > 0]
                )
        results = mappers.TwitterAccount(data, tree)
        return results
        
class LinkedInMemberUrlResourceParser(LinkedInXMLParser):
    def __init__(self, content):
        self.tree = content
        self.xpath_collection = {
            'url': etree.XPath('url'),
            'name': etree.XPath('name'),
        }
        self.results = self.__build_data(self.tree)
    
    def __build_data(self, tree):
        data = {}
        for n in tree.getchildren():
            if not n.getchildren():
                data[re.sub('-', '_', n.tag)] = n.text
            else:
                data[re.sub('-', '_', n.tag)] = n.getchildren()[0].text
        results = mappers.MemberUrlResource(data, tree)
        return results

class LinkedInSkillsParser(LinkedInXMLParser):
    def __init__(self, content):
        self.tree = content
        self.xpath_collection = {
            'id': etree.XPath('id'),
            'name': etree.XPath('skill/name'),
        }
        self.results = self.__build_data(self.tree)
    
    def __build_data(self, tree):
        data = {}
        for n in tree.getchildren():
            if not n.getchildren():
                data[re.sub('-', '_', n.tag)] = n.text
            else:
                data[re.sub('-', '_', n.tag)] = n.getchildren()[0].text
        results = mappers.Skills(data, tree)
        return results
        

########NEW FILE########
__FILENAME__ = mappers
from lxml import etree
import datetime, re
import lixml
    
class LinkedInData(object):
    def __init__(self, data, xml):
        self.xml = xml
        self.parse_data(data)
    
    def parse_data(self, data):
        for k in data.keys():
            self.__dict__[k] = data[k]
            
    def jsonify(self):
        json = {}
        for k in self.__dict__.keys():
            if type(self.__dict__[k]) == type(''):
                json[k] = self.__dict__[k]
        return json
        
    def xmlify(self):
        converted = [re.sub('_', '-', k) for k in self.__dict__.keys()]
        for d in self.xml.iter(tag=etree.Element):
            if d.tag in converted:
                try:
                    d.text = self.__dict__[re.sub('-', '_', d.tag)]
                except:
                    continue
        return etree.tostring(self.xml)
    
    def __str__(self):
        return self.update_content if hasattr(self, 'update_content') and self.update_content else '<No Content>'
    
class LinkedInError(LinkedInData):
    def __repr__(self):
        return '<LinkedIn Error code %s>'.encode('utf-8') % self.status
        
class NetworkUpdate(LinkedInData):
    def __init__(self, data, xml):
        self.xml = xml
        self.update_key = None
        self.parse_data(data)
        
    def jsonify(self):
        jsondict = {'first_name': self.first_name,
                    'last_name': self.last_name,
                    'update_content': self.update_content,
                    'timestamp': self.timestamp,
                    'update_key': self.update_key,
                    'profile_url': self.profile_url}
        return jsondict
    
class NetworkStatusUpdate(NetworkUpdate):
    def __init__(self, data, xml):
        self.status_xpath = etree.XPath('update-content/person/current-status')
        self.comment_xpath = etree.XPath('update-comments/update-comment')
        self.update_key = None
        self.xml = xml
        self.parse_data(data)
        self.update_content = self.status_xpath(xml)[0].text.strip()
        self.comments = []
        self.get_comments()
        
    def get_comments(self):
        for c in self.comment_xpath(self.xml):
            comment = NetworkUpdateComment(c)
            self.comments.append(comment)
        return

class NetworkConnectionUpdate(NetworkUpdate):
    def __init__(self, data, xml):
        self.xml = xml
        self.update_key = None
        self.parse_data(data)
        self.connection_target = etree.XPath('update-content/person/connections/person')
        self.targets = []
        self.get_targets()
        self.set_update_content(self.targets)
    
    def get_targets(self):
        for p in self.connection_target(self.xml):
            obj = lixml.LinkedInProfileParser(p).results
        self.targets = obj
    
    def set_update_content(self, targets):
        update_str = self.first_name + ' ' + self.last_name + ' is now connected with '
        if len(targets) == 1:
            update_str += targets[0].first_name + ' ' + targets[0].last_name
        else:
            for t in targets:
                update_str += t.first_name + ' ' + t.last_name + ', and '
        update_str = re.sub(', and $', '', update_str)
        self.update_content = update_str
        return

class NetworkNewConnectionUpdate(NetworkConnectionUpdate):
    def get_targets(self):
        self.connection_target = etree.XPath('update-content/person/')
        for p in self.connection_target(self.xml):
            obj = LinkedInProfileParser(p).results
        self.targets = obj
    
    def set_update_content(self, target):
        update_str = ' is now connected with you.'
        update_str = targets[0].first_name + ' ' + targets[0].last_name + update_str
        self.update_content = update_str
        return
    
class NetworkAddressBookUpdate(NetworkNewConnectionUpdate):
    def set_update_content(self, target):
        update_str = ' just joined LinkedIn.'
        update_str = self.targets[0].first_name + ' ' + self.targets[0].last_name + update_str
        self.update_content = update_str
        return

class NetworkGroupUpdate(NetworkUpdate):
    def __init__(self, data, xml):
        self.update_key = None
        self.xml = xml
        self.parse_data(data)
        self.group_target = etree.XPath('update-content/person/member-groups/member-group')
        self.group_name_target = etree.XPath('name')
        self.group_url_target = etree.XPath('site-group-request/url')
        self.targets = []
        self.get_targets()
        self.set_update_content(self.targets)
    
    def get_targets(self):
        for g in self.group_target(self.xml):
            target_dict = {}
            k = self.group_name_target(g)[0].text.strip()
            v = self.group_url_target(g)[0].text.strip()
            target_dict[k] = v
            self.targets.append(target_dict)
        return
    
    def set_update_content(self, targets):
        update_str = self.first_name + ' ' + self.last_name + ' joined '
        if len(targets) == 1:
            update_str += '<a href="'+targets[0].values()[0]+'">'+targets[0].keys()[0] + '</a>'
        else:
            for t in targets:
                update_str += '<a href="'+t.values()[0]+'">'+t.keys()[0] + '</a>, and '
        update_str = re.sub(', and $', '', update_str)
        self.update_content = update_str
        return
    
class NetworkQuestionUpdate(NetworkUpdate):
    def __init__(self, data, xml):
        self.xml = xml
        self.update_key = None
        self.parse_data(data)
        self.question_title_xpath = etree.XPath('update-content/question/title')
        self.set_update_content()
    
    def set_update_content(self):
        update_str = self.first_name + ' ' + self.last_name + ' asked a question: '
        qstn_text = self.question_title_xpath(self.xml)[0].text.strip()
        update_str += qstn_text
        self.update_content = update_str
        return
    
class NetworkAnswerUpdate(NetworkUpdate):
    def __init__(self, data, xml):
        self.update_key = None
        self.xml = xml
        self.parse_data(data)
        self.question_title_xpath = etree.XPath('update-content/question/title')
        self.answer_xpath = etree.XPath('update-content/question/answers/answer')
        self.get_answers()
        self.set_update_content()
    
    def get_answers(self):
        for a in self.answer_xpath(self.xml):
            self.profile_url = a.xpath('web-url')[0].text.strip()
            self.first_name = a.xpath('author/first-name')[0].text.strip()
            self.last_name = a.xpath('author/last-name')[0].text.strip()
    
    def set_update_content(self):
        update_str = self.first_name + ' ' + self.last_name + ' answered: '
        qstn_text = self.question_title_xpath(self.xml)[0].text.strip()
        update_str += qstn_text
        self.update_content = update_str
        return
    
class NetworkJobPostingUpdate(NetworkUpdate):
    def __init__(self, data, xml):
        self.xml = xml
        self.parse_data(data)
        self.set_update_content()
        self.poster = lixml.LinkedInXMLParser(xml.xpath('job-poster')[0])
    
    def set_update_content(self):
        update_str = self.poster.first_name + ' ' + self.poster.last_name + ' posted a job: ' + self.job_title
        self.update_content = update_str
        return

class NetworkUpdateComment(LinkedInData):
    def __init__(self, xml):
        self.xml = xml
        self.comment_xpath = etree.XPath('comment')
        self.person_xpath = etree.XPath('person')
        self.__content = lixml.LinkedInXMLParser(etree.tostring(self.person_xpath(xml)[0])).results[0]
        self.first_name = self.__content.first_name
        self.last_name = self.__content.last_name
        self.profile_url = self.__content.profile_url
        self.update_content = self.comment_xpath(xml)[0].text
        
    def jsonify(self):
        jsondict = {'first_name': self.first_name,
                    'last_name': self.last_name,
                    'update_content': self.update_content,
                    'profile_url': self.profile_url}
        return jsondict

class Profile(LinkedInData):
    def __init__(self, data, xml):
        self.profile_url = ''
        self.xml = xml
        self.parse_data(data)
        self.positions = []
        self.skills = []
        self.educations = []
        self.twitter_accounts = []
        self.member_url_resources = []
        if not self.profile_url:
            self.set_profile_url()
        self.get_location()
        self.get_positions()
        self.get_skills()
        self.get_educations()
        self.get_twitter_accounts()
        self.get_member_url_resources()
        
    def set_profile_url(self):
        try:
            profile_url_xpath = etree.XPath('site-standard-profile-request/url')
            self.profile_url = profile_url_xpath(self.xml)[0].text.strip()
        except:
            pass
            
    def get_location(self):
    	try:
            location_name_xpath = etree.XPath('location/name')
            self.location = location_name_xpath(self.xml)[0].text.strip()
            country_code_xpath = etree.XPath('location/country/code')
            self.country = country_code_xpath(self.xml)[0].text.strip()
        except:
            pass
        
    def get_positions(self):
        profile_position_xpath = etree.XPath('positions/position')
        pos = profile_position_xpath(self.xml)
        for p in pos:
            obj = lixml.LinkedInXMLParser(etree.tostring(p)).results
            self.positions.append(obj)
            
    def get_skills(self):
        
        profile_skills_xpath = etree.XPath('skills/skill')
        skills = profile_skills_xpath(self.xml)
        for s in skills:
            obj = lixml.LinkedInXMLParser(etree.tostring(s)).results
            self.skills.append(obj)
    
    def get_educations(self):
        profile_education_xpath = etree.XPath('educations/education')
        eds = profile_education_xpath(self.xml)
        for e in eds:
            obj = lixml.LinkedInXMLParser(etree.tostring(e)).results
            self.educations.append(obj)
            
    def get_twitter_accounts(self):
    	twitter_accounts_xpath = etree.XPath('twitter-accounts/twitter-account')
    	accounts = twitter_accounts_xpath(self.xml)
    	for account in accounts:
    		obj = lixml.LinkedInXMLParser(etree.tostring(account)).results
    		self.twitter_accounts.append(obj)
    		
    def get_member_url_resources(self):
    	url_resources_xpath = etree.XPath('member-url-resources/member-url')
    	urls = url_resources_xpath(self.xml)
    	for url in urls:
    		obj = lixml.LinkedInXMLParser(etree.tostring(url)).results
    		self.member_url_resources.append(obj)

    		
        
class Position(LinkedInData):
    pass

class Education(LinkedInData):
    pass
    
class TwitterAccount(LinkedInData):
    pass
  
class Skills(LinkedInData):
    pass
    
class MemberUrlResource(LinkedInData):
    pass
########NEW FILE########
