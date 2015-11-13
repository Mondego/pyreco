__FILENAME__ = config
# coding: utf-8

import os

_CURRENT_PATH = os.path.dirname(__file__)
_DB_SQLITE_PATH = os.path.join(_CURRENT_PATH, 'feather.sqlite')

_DBUSER = "yetone" # 数据库用户名
_DBPASS = "123" # 数据库密码
_DBHOST = "localhost" # 数据库服务器
_DBNAME = "feather" # 数据库名称

PER_PAGE = 15 # 每页显示主题数目
RE_PER_PAGE = 25 # 每页显示主题回复数目
DEFAULT_TIMEZONE = "Asia/Shanghai" # 默认时区

#_COMM_NAME = "Feather" # 社区名称

class Config(object):
	SECRET_KEY = 'your secret key'
	DEBUG = False
	TESTING = False
	SQLALCHEMY_DATABASE_URI = 'sqlite:///%s' % _DB_SQLITE_PATH
	CACHE_TYPE = 'memcached'


class ProConfig(Config):
	SQLALCHEMY_DATABASE_URI = 'mysql://%s:%s@%s/%s' % (_DBUSER, _DBPASS, _DBHOST, _DBNAME)

class DevConfig(Config):
	DEBUG = True

class TestConfig(Config):
	TESTING = True

########NEW FILE########
__FILENAME__ = databases
# coding: utf-8
import time
from feather.extensions import db

# databases
favorites = db.Table('favorites',
		db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
		db.Column('topic_id', db.Integer, db.ForeignKey('topic.id'))
		)

votes = db.Table('votes',
		db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
		db.Column('topic_id', db.Integer, db.ForeignKey('topic.id'))
		)

thanks = db.Table('thanks',
		db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
		db.Column('reply_id', db.Integer, db.ForeignKey('reply.id'))
		)

reads = db.Table('reads',
		db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
		db.Column('topic_id', db.Integer, db.ForeignKey('topic.id'))
)

class Bill(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
	topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'))
	reply_id = db.Column(db.Integer, db.ForeignKey('reply.id'))
	user_id = db.Column(db.Integer)
	time = db.Column(db.Integer)
	balance = db.Column(db.Integer)
	type = db.Column(db.Integer)
	date = db.Column(db.Integer)

	def __init__(self, author, time, balance, type, date, topic=None, reply=None, user_id=None):
		self.author = author
		self.topic = topic
		self.reply = reply
		self.user_id = user_id
		self.time = time
		self.balance = balance
		self.type = type
		self.date = date

	def __repr__(self):
		return '<Bill %r>' % (self.id)

class Bank(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	time = db.Column(db.Integer)

	def __init__(self,time):
		self.time = time

	def __repr__(self):
		return '<Bank %r>' % (self.time)

class City(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(50), unique=True)
	site = db.Column(db.String(50), unique=True)
	description = db.Column(db.Text)
	users = db.relationship('User', backref='city', lazy='dynamic')

	def __init__(self, name):
		self.name = name
		self.site = name
		self.description = u''

	def __repr__(self):
		return '<City %r>' % (self.name)


class User(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(50), unique=True)
	email = db.Column(db.String(120), unique=True)
	password = db.Column(db.String(120))
	time = db.Column(db.Integer)
	timeswitch = db.Column(db.Integer)
	topswitch = db.Column(db.Integer)
	emailswitch = db.Column(db.Integer)
	timetop = db.Column(db.Integer)
	usercenter = db.Column(db.String(50), unique=True)
	status = db.Column(db.Integer)
	steam_id = db.Column(db.Integer)
	description = db.Column(db.Text)
	website = db.Column(db.Text)
	date = db.Column(db.Integer)
	tab_id = db.Column(db.Integer)
	topics = db.relationship('Topic', backref='author', lazy='dynamic')
	replys = db.relationship('Reply', backref='author', lazy='dynamic')
	bills = db.relationship('Bill', backref='author', lazy='dynamic')
	notifications = db.relationship('Notify', backref='author', lazy='dynamic')
	favorites = db.relationship('Topic', secondary=favorites,
			backref=db.backref('followers', lazy='dynamic'))
	votes = db.relationship('Topic', secondary=votes,
			backref=db.backref('voters', lazy='dynamic'))
	thanks = db.relationship('Reply', secondary=thanks,
			backref=db.backref('thankers', lazy='dynamic'))
	city_id = db.Column(db.Integer, db.ForeignKey('city.id'))
	reads = db.relationship('Topic', secondary=reads,
			backref=db.backref('readers', lazy='dynamic'))

	def __init__(self, name, email, password, time, date):
		self.name = name
		self.email = email
		self.password = password
		self.time = time
		self.timeswitch = 1
		self.timetop = 1
		self.topswitch = 1
		self.emailswitch = 1
		self.usercenter = name
		self.status = 1
		self.steam_id = 1
		self.description = u''
		self.website = u''
		self.date = date
		self.tab_id = -1
	

	def get_gravatar_url(self, size=80):
		return 'http://www.gravatar.com/avatar/%s?d=identicon&s=%d' % \
				(md5(self.email.strip().lower().encode('utf-8')).hexdigest(), size)


	def __repr__(self):
		return '<User %r>' % (self.name)


class Nodeclass(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(50), unique=True)
	description = db.Column(db.Text)
	nodes = db.relationship('Node', backref='nodeclass', lazy='dynamic')
	topics = db.relationship('Topic', backref='nodeclass', lazy='dynamic')
	status = db.Column(db.Integer)

	def __init__(self, name):
		self.name = name
		self.description = u''
		self.status = 1

	def __repr__(self):
		return '<Nodeclass %r>' % self.name


class Node(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(50), unique=True)
	site = db.Column(db.String(50), unique=True)
	description = db.Column(db.Text)
	header = db.Column(db.Text)
	description_origin = db.Column(db.Text)
	header_origin = db.Column(db.Text)
	nodeclass_id = db.Column(db.Integer, db.ForeignKey('nodeclass.id'))
	topics = db.relationship('Topic', backref='node', lazy='dynamic')
	status = db.Column(db.Integer)
	date = db.Column(db.Integer)
	style = db.Column(db.Text)

	def __init__(self, name, site, description, description_origin, nodeclass, style=None):
		self.name = name
		self.site = site
		self.description = description
		self.description_origin = description_origin
		self.header = u''
		self.header_origin = u''
		self.status = 1
		self.date = int(time.time())
		self.nodeclass = nodeclass

	def __repr__(self):
		return '<Node %r>' % self.name


class Topic(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
	notify = db.relationship('Notify', backref='topic', lazy='dynamic', uselist=False)
	title = db.Column(db.String(80))
	text = db.Column(db.Text)
	text_origin = db.Column(db.Text)
	replys = db.relationship('Reply', backref='topic', lazy='dynamic')
	bills = db.relationship('Bill', backref='topic', uselist=False, lazy='dynamic')
	node_id = db.Column(db.Integer, db.ForeignKey('node.id'))
	nodeclass_id = db.Column(db.Integer, db.ForeignKey('nodeclass.id'))
	vote = db.Column(db.Integer)
	report = db.Column(db.Integer)
	date = db.Column(db.Integer)
	last_reply_date = db.Column(db.Integer)
	reply_count = db.Column(db.Integer)

	def __init__(self, author, title, text, text_origin, node, reply_count, report=0):
		self.author = author
		self.title = title
		self.text = text
		self.text_origin = text_origin
		self.node = node
		self.nodeclass = node.nodeclass
		self.vote = 0
		self.report = report
		self.date = int(time.time())
		self.last_reply_date = int(time.time())
		self.reply_count = reply_count

	def get_reply_count(self):
		return len(self.replys.all()) if self.replys else 0

	def __repr__(self):
		return '<Topic %r>' % self.title


class Reply(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'))
	author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
	notify = db.relationship('Notify', backref='reply', lazy='dynamic')
	text = db.Column(db.Text)
	text_origin = db.Column(db.Text)
	bills = db.relationship('Bill', backref='reply', uselist=False, lazy='dynamic')
	date = db.Column(db.Integer)
	number = db.Column(db.Integer)
	type = db.Column(db.Integer)

	def __init__(self, topic, author, text, text_origin, number=1, type=0):
		self.topic = topic
		self.author = author
		self.text = text
		self.text_origin = text_origin
		self.date = int(time.time())
		self.number = number
		self.type = type

	def __repr__(self):
		return '<Reply %r>' % self.text

class Notify(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
	status = db.Column(db.Integer)
	topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'))
	reply_id = db.Column(db.Integer, db.ForeignKey('reply.id'))
	type = db.Column(db.Integer)
	date = db.Column(db.Integer)

	def __init__(self, author, topic, reply, type):
		self.author = author
		self.status = 1
		self.topic = topic
		self.reply = reply
		self.type = type
		self.date = int(time.time())

	def __repr__(self):
		return '<Notify %r>' % self.id


########NEW FILE########
__FILENAME__ = extensions
# coding: utf-8

from flask_sqlalchemy import SQLAlchemy
from flaskext.cache import Cache

db = SQLAlchemy()
cache = Cache()

########NEW FILE########
__FILENAME__ = helpers
# coding: utf-8
import re
from feather.databases import User, Topic, Reply
import markdown
import functools

markdown = functools.partial(markdown.markdown,
                             safe_mode=False,
                             output_format="html")


_emoji_list = [
    "-1", "0", "1", "109", "2", "3", "4", "5", "6", "7", "8", "8ball", "9",
    "a", "ab", "airplane", "alien", "ambulance", "angel", "anger", "angry",
    "apple", "aquarius", "aries", "arrow_backward", "arrow_down",
    "arrow_forward", "arrow_left", "arrow_lower_left", "arrow_lower_right",
    "arrow_right", "arrow_up", "arrow_upper_left", "arrow_upper_right",
    "art", "astonished", "atm", "b", "baby", "baby_chick", "baby_symbol",
    "balloon", "bamboo", "bank", "barber", "baseball", "basketball", "bath",
    "bear", "beer", "beers", "beginner", "bell", "bento", "bike", "bikini",
    "bird", "birthday", "black_square", "blue_car", "blue_heart", "blush",
    "boar", "boat", "bomb", "book", "boot", "bouquet", "bow", "bowtie",
    "boy", "bread", "briefcase", "broken_heart", "bug", "bulb",
    "bullettrain_front", "bullettrain_side", "bus", "busstop", "cactus",
    "cake", "calling", "camel", "camera", "cancer", "capricorn", "car",
    "cat", "cd", "chart", "checkered_flag", "cherry_blossom", "chicken",
    "christmas_tree", "church", "cinema", "city_sunrise", "city_sunset",
    "clap", "clapper", "clock1", "clock10", "clock11", "clock12", "clock2",
    "clock3", "clock4", "clock5", "clock6", "clock7", "clock8", "clock9",
    "closed_umbrella", "cloud", "clubs", "cn", "cocktail", "coffee",
    "cold_sweat", "computer", "confounded", "congratulations",
    "construction", "construction_worker", "convenience_store", "cool",
    "cop", "copyright", "couple", "couple_with_heart", "couplekiss", "cow",
    "crossed_flags", "crown", "cry", "cupid", "currency_exchange", "curry",
    "cyclone", "dancer", "dancers", "dango", "dart", "dash", "de",
    "department_store", "diamonds", "disappointed", "dog", "dolls",
    "dolphin", "dress", "dvd", "ear", "ear_of_rice", "egg", "eggplant",
    "egplant", "eight_pointed_black_star", "eight_spoked_asterisk",
    "elephant", "email", "es", "european_castle", "exclamation", "eyes",
    "factory", "fallen_leaf", "fast_forward", "fax", "fearful", "feelsgood",
    "feet", "ferris_wheel", "finnadie", "fire", "fire_engine", "fireworks",
    "fish", "fist", "flags", "flushed", "football", "fork_and_knife",
    "fountain", "four_leaf_clover", "fr", "fries", "frog", "fuelpump", "gb",
    "gem", "gemini", "ghost", "gift", "gift_heart", "girl", "goberserk",
    "godmode", "golf", "green_heart", "grey_exclamation", "grey_question",
    "grin", "guardsman", "guitar", "gun", "haircut", "hamburger", "hammer",
    "hamster", "hand", "handbag", "hankey", "hash", "headphones", "heart",
    "heart_decoration", "heart_eyes", "heartbeat", "heartpulse", "hearts",
    "hibiscus", "high_heel", "horse", "hospital", "hotel", "hotsprings",
    "house", "hurtrealbad", "icecream", "id", "ideograph_advantage", "imp",
    "information_desk_person", "iphone", "it", "jack_o_lantern",
    "japanese_castle", "joy", "jp", "key", "kimono", "kiss", "kissing_face",
    "kissing_heart", "koala", "koko", "kr", "leaves", "leo", "libra", "lips",
    "lipstick", "lock", "loop", "loudspeaker", "love_hotel", "mag",
    "mahjong", "mailbox", "man", "man_with_gua_pi_mao", "man_with_turban",
    "maple_leaf", "mask", "massage", "mega", "memo", "mens", "metal",
    "metro", "microphone", "minidisc", "mobile_phone_off", "moneybag",
    "monkey", "monkey_face", "moon", "mortar_board", "mount_fuji", "mouse",
    "movie_camera", "muscle", "musical_note", "nail_care", "necktie", "new",
    "no_good", "no_smoking", "nose", "notes", "o", "o2", "ocean", "octocat",
    "octopus", "oden", "office", "ok", "ok_hand", "ok_woman", "older_man",
    "older_woman", "open_hands", "ophiuchus", "palm_tree", "parking",
    "part_alternation_mark", "pencil", "penguin", "pensive", "persevere",
    "person_with_blond_hair", "phone", "pig", "pill", "pisces", "plus1",
    "point_down", "point_left", "point_right", "point_up", "point_up_2",
    "police_car", "poop", "post_office", "postbox", "pray", "princess",
    "punch", "purple_heart", "question", "rabbit", "racehorse", "radio",
    "rage", "rage1", "rage2", "rage3", "rage4", "rainbow", "raised_hands",
    "ramen", "red_car", "red_circle", "registered", "relaxed", "relieved",
    "restroom", "rewind", "ribbon", "rice", "rice_ball", "rice_cracker",
    "rice_scene", "ring", "rocket", "roller_coaster", "rose", "ru", "runner",
    "sa", "sagittarius", "sailboat", "sake", "sandal", "santa", "satellite",
    "satisfied", "saxophone", "school", "school_satchel", "scissors",
    "scorpius", "scream", "seat", "secret", "shaved_ice", "sheep", "shell",
    "ship", "shipit", "shirt", "shit", "shoe", "signal_strength",
    "six_pointed_star", "ski", "skull", "sleepy", "slot_machine", "smile",
    "smiley", "smirk", "smoking", "snake", "snowman", "sob", "soccer",
    "space_invader", "spades", "spaghetti", "sparkler", "sparkles",
    "speaker", "speedboat", "squirrel", "star", "star2", "stars", "station",
    "statue_of_liberty", "stew", "strawberry", "sunflower", "sunny",
    "sunrise", "sunrise_over_mountains", "surfer", "sushi", "suspect",
    "sweat", "sweat_drops", "swimmer", "syringe", "tada", "tangerine",
    "taurus", "taxi", "tea", "telephone", "tennis", "tent", "thumbsdown",
    "thumbsup", "ticket", "tiger", "tm", "toilet", "tokyo_tower", "tomato",
    "tongue", "top", "tophat", "traffic_light", "train", "trident",
    "trollface", "trophy", "tropical_fish", "truck", "trumpet", "tshirt",
    "tulip", "tv", "u5272", "u55b6", "u6307", "u6708", "u6709", "u6e80",
    "u7121", "u7533", "u7a7a", "umbrella", "unamused", "underage", "unlock",
    "up", "us", "v", "vhs", "vibration_mode", "virgo", "vs", "walking",
    "warning", "watermelon", "wave", "wc", "wedding", "whale", "wheelchair",
    "white_square", "wind_chime", "wink", "wink2", "wolf", "woman",
    "womans_hat", "womens", "x", "yellow_heart", "zap", "zzz", "+1"
]


def _emoji(text):
    pattern = re.compile(':([a-z0-9\+\-_]+):')

    def make_emoji(m):
        name = m.group(1)
        if name not in _emoji_list:
            return ':%s:' % name
        tpl = ('<img class="emoji" title="%(name)s" alt="%(name)s" height="20"'
				' width="20" src="http://l.ruby-china.org/assets/emojis/%(name)s.png" align="top">')
        return tpl % {'name': name}

    text = pattern.sub(make_emoji, text)
    return text

def textformat(text):
	text = re.sub(ur'<a.+?href="(.+?)".*?>(.+?)<\/a>',ur'<a href="\1" target="_blank">\2</a>',text)
	text = re.sub(ur'<(http(s|):\/\/[\w.]+\/?\S*)>',ur'<a href="\1" target="_blank">\1</a>',text)
	topic_url = ur'http:\/\/(www\.|)feather\.im\/topic\/?(\S*)'
	for match in re.finditer(topic_url, text):
		url = match.group(0)
		topic_id = match.group(2)
		topic = Topic.query.get(topic_id)
		if topic is None:
			continue
		else:
			topic_title = topic.title
		aurl = '<a href="%s" target="_blank">/%s</a>' % (url, topic_title)
		text = text.replace(url, aurl)
	regex_url = r'(^|\s)http(s|):\/\/([\w.]+\/?)\S*'
	for match in re.finditer(regex_url, text):
		url = match.group(0)
		aurl = '<a href="%s" target="_blank">%s</a>' % (url, url)
		text = text.replace(url, aurl)
	number = ur'#(\d+)楼\s'
	for match in re.finditer(number, text):
		url = match.group(1)
		number = match.group(0)
		tonumber = int(url) - 1
		nurl = '<a id=lou onclick="toReply(%s);" href="#;" style="color: #376B43;">#<span id=nu>%s</span>楼 </a>' % (url, url)
		text = text.replace(number, nurl)
	text = _emoji(text)
	return text

def mention(text):
	usernames = []
	if text.find('@') == -1:
		begin = -1
		usernames = usernames
	elif text.find(' ') != -1:
		begin = text.find('@') + 1
		if text.find('\n') != -1:
			end = text.find(' ') < text.find('\n') and text.find(' ') or text.find('\n')
		else:
			end = len(text)
	elif text.find('\n') != -1:
		begin = text.find('@') + 1
		end = text.find('\n')
	else:
		begin = text.find('@') +1
		end = len(text)
	if begin != -1:
		value = text[begin:end]
		n = len(value)
		for i in range(0,n):
			rv = User.query.filter_by(name=value).first()
			if not rv:
				value = list(value)
				value.pop()
				value = ''.join(value)
				if value == '' and '@' in text[text.find('@') + 1:]:
					usernames = 'error'
			else:
				text = text[text.find('@') + len(value):]
				usernames = usernames + [value]
				break
	return usernames

def mentions(text):
	usernames = []
	if text.find('@') == -1:
		begin = -1
		usernames = usernames
	elif text.find(' ') != -1:
		begin = text.find('@') + 1
		if text.find('\n') != -1:
			end = text.find(' ') < text.find('\n') and text.find(' ') or text.find('\n')
		else:
			end = len(text)
	elif text.find('\n') != -1:
		begin = text.find('@') + 1
		end = text.find('\n')
	else:
		begin = text.find('@') +1
		end = len(text)
	if begin != -1:
		value = text[begin:end]
		n = len(value)
		for i in range(0,n):
			rv = User.query.filter_by(name=value).first()
			if not rv:
				value = list(value)
				value.pop()
				value = ''.join(value)
				if value == '' and '@' in text[text.find('@') + 1:]:
					text = text[text.find('@') + 1:]
					while True:
						a = mention(text)
						if a == []:
							break
						i = 0
						while a == 'error':
							text = text[text.find('@') + 1:]
							a = mention(text)
							i += 1
							if i == 6:
								break
						if a == 'error':
							a = []
						usernames = usernames + a
						text = text[text.find('@') + 1:]
			else:
				text = text[text.find('@') + len(value):]
				usernames = usernames + [value]
				while True:
					a = mention(text)
					if a == []:
						break
					i = 0
					while a == 'error':
						text = text[text.find('@') + 1:]
						a = mention(text)
						i += 1
						if i == 6:
							break
					if a == 'error':
						a = []
					usernames = usernames + a
					text = text[text.find('@') + 1:]
				break
	return usernames



def mentionfilter(text):
	content = text.replace('\n','')
	usernames = list(set(mentions(content)))
	for username in usernames:
		url = '<a class=at_user href="/member/%s" target="_blank">%s</a>' % (username, username)
		text = text.replace(username, url)
	return text

########NEW FILE########
__FILENAME__ = account
# coding: utf-8
import time
from flask import Module, request, session, g, redirect, url_for, \
		abort, render_template, flash
from werkzeug import check_password_hash, generate_password_hash
from feather.extensions import db, cache
from feather import config
from feather.databases import Bill, Bank, City, User, Topic, Notify, Reply

account = Module(__name__)

def get_user_id(username):
	rv = User.query.filter_by(name=username).first()
	return rv.id if rv else None

def get_user_id_from_email(email):
	rv = User.query.filter_by(email=email).first()
	return rv.id if rv else None

@cache.cached(60 * 60, key_prefix='topusers')
def get_top_users():
	rv = User.query.filter_by(topswitch=1).order_by(User.time.desc()).limit(26).all()
	return rv

@cache.cached(60 * 5, key_prefix='users')
def get_users():
	rv = User.query.order_by(User.id.asc()).all()
	return rv

@account.route('/users')
def users():
	users = get_users()
	return render_template('users.html',users=users)


@account.route('/member/<username>', defaults={'page': 1})
@account.route('/member/<username>/page/<int:page>')
def usercenter(username, page):
	user = User.query.filter_by(name=username).first()
	page_obj = user.topics.filter(Topic.report == 0).order_by(Topic.last_reply_date.desc()).paginate(page, per_page=config.PER_PAGE)
	page_url = lambda page: url_for("account.usercenter", username=username, page=page)
	topiccount = user.topics.filter(Topic.report==0).count()
	replycount = user.replys.filter(Reply.type==0).count()
	return render_template('usercenter.html', user=user, topiccount=topiccount, replycount=replycount, page_obj=page_obj, page_url=page_url)


@account.route('/setting/account', methods=['GET', 'POST'])
def setting():
	if not g.user:
		return redirect(url_for('topic.tab_view'))
	user = g.user
	if request.method == 'POST':
		user.name = request.form['user[name]']
		user.email = request.form['user[email]']
		user.website = request.form['user[website]']
		user.description = request.form['user[description]']
		user.timeswitch = request.form['user[timeswitch]']
		user.topswitch = request.form['user[topswitch]']
		user.emailswitch = request.form['user[emailswitch]']
		city = City.query.filter_by(name=request.form['user[city]']).first()
		if not city:
			city = City(name=request.form['user[city]'])
			db.session.add(city)
			db.session.commit()
		city = City.query.filter_by(name=request.form['user[city]']).first()
		user.city = city
		db.session.commit()
		flash(u'修改成功！')
		return redirect(url_for('account.setting'))
	return render_template('setting.html',user=g.user)


@account.route('/notification', defaults={'page': 1})
@account.route('/notification/page/<int:page>')
def notify(page):
	g.notify = 0
	if g.notify_read:
		page_obj = g.notify_read.paginate(page, per_page=config.RE_PER_PAGE)
	else:
		page_obj = []
	page_url = lambda page: url_for("account.notify", page=page)
	notifications = Notify.query.filter_by(author=g.user).all()
	for notification in notifications:
		notification.status = 0
		db.session.commit()
	return render_template('notifications.html', page_obj=page_obj, page_url=page_url, unreads=g.notify_unread, un=g.un)


@account.route('/notifacations/del/<int:notify_id>', defaults={'page': 1})
@account.route('/notifacations/del/<int:notify_id>?page=<int:page>')
def del_notifacations(notify_id, page):
	notify = Notify.query.get(notify_id)
	db.session.delete(notify)
	db.session.commit()
	return redirect(url_for('account.notify', page=page))

@account.route('/top')
def top():
	users = get_top_users()
	return render_template('top.html',users=users)



@account.route('/favorites', defaults={'page': 1})
@account.route('/favorites/page/<int:page>')
def favorites(page):
	if not session.get('user_id'):
		abort(401)
	topics = User.query.get(session['user_id']).favorites
	n = len(topics)
	PER_PAGE = config.PER_PAGE
	if n < PER_PAGE:
		pages = 1
	else:
		pages = n / PER_PAGE
		if n % PER_PAGE != 0:
			pages += 1
	return render_template('favorites.html',topics=topics[(page-1)*PER_PAGE:(page-1)*PER_PAGE+PER_PAGE],pages=pages,page=page)



@account.route('/times', defaults={'page': 1})
@account.route('/times/page/<int:page>')
def times(page):
	if not session.get('user_id'):
		abort(401)
	page_obj = Bill.query.filter_by(author=g.user).order_by(Bill.date.desc()).paginate(page, per_page=config.RE_PER_PAGE)
	page_url = lambda page: url_for("account.times", page=page)
	return render_template('times.html', page_obj=page_obj, page_url=page_url)



@account.route('/login', methods=['GET', 'POST'])
def login():
	if session.get('user_id'):
		return redirect(url_for('topic.tab_view'))
	error = None
	if request.method == 'POST':
		if '@' in request.form['username']:
			user = User.query.filter_by(email=request.form['username']).first()
			if user is None:
				error = u'用户名错误！'
			elif not check_password_hash(user.password,request.form['password']):
				error = u'密码错误！'
			else:
				flash(u'登录成功！')
				session['user_id'] = user.id
				return redirect(url_for('topic.tab_view'))
		else:
			user = User.query.filter_by(name=request.form['username']).first()
			if user is None:
				error = u'用户名错误！'
			elif not check_password_hash(user.password,request.form['password']):
				error = u'密码错误！'
			else:
				flash(u'登录成功！')
				session['user_id'] = user.id
				session.permanent = True
				return redirect(url_for('topic.tab_view'))
	return render_template('login.html', error=error)


@account.route('/register', defaults={'invitername': u''}, methods=['GET', 'POST'])
@account.route('/register/~<invitername>', methods=['GET', 'POST'])
def register(invitername):
	if g.user:
		return redirect(url_for('topic.tab_view'))
	error = None
	if request.method == 'POST':
		if not request.form['username']:
			error = u'你需要输入一个用户名哦！'
		elif not request.form['email'] or \
				'@' not in request.form['email']:
			error = u'你需要输入一个有效的邮箱地址！'
		elif not request.form['password']:
			error = u'你需要输入一个密码哦！'
		elif request.form['password'] != request.form['password2']:
			error = u'你输入的两次密码不一样哦！'
		elif get_user_id(request.form['username']) is not None:
			error = u'此用户名已存在哦！'
		elif get_user_id_from_email(request.form['email']) is not None:
			error = u'此邮箱已存在哦！'
		else:
			if invitername:
				user = User(name=request.form['username'], email=request.form['email'], password=generate_password_hash(request.form['password']), time=2160, date=int(time.time()))
			else:
				user = User(name=request.form['username'], email=request.form['email'], password=generate_password_hash(request.form['password']), time=2100, date=int(time.time()))
			db.session.add(user)
			db.session.commit()
			if Bank.query.all() == []:
				b = Bank(time=2100000)
				db.session.add(b)
				db.session.commit()
			bank = Bank.query.get(1)
			user = User.query.filter_by(name=request.form['username']).first()
			if invitername:
				giver = User.query.filter_by(name=invitername).first()
				bank.time -= 2220
				giver.time += 60
				bill = Bill(author=user,time=2160,type=7,balance=user.time,date=int(time.time()),user_id=giver.id)
				bill2 = Bill(author=giver,time=60,type=8,balance=giver.time,date=int(time.time()),user_id=user.id)
				db.session.add(bill2)
			else:
				bank.time -= 2100
				bill = Bill(author=user,time=2100,type=1,balance=user.time,date=int(time.time()))
			db.session.add(bill)
			db.session.commit()
			flash(u'你已经成功注册！现在马上登录吧！')
			return redirect(url_for('account.login'))
	return render_template('register.html', error=error, invitername=invitername)




@account.route('/logout', methods=['GET', 'POST'])
def logout():
	if g.user is not None:
		session.pop('user_id', None)
		session.permanent = False
		flash(u'你已经成功登出！')
	return redirect(url_for('topic.tab_view'))




########NEW FILE########
__FILENAME__ = blog
# coding: utf-8
import time
from flask import Module, request, session, g, redirect, url_for, \
		abort, render_template, flash, jsonify
from flask_sqlalchemy import Pagination
from feather import config
from feather.extensions import db, cache
from feather.helpers import mentions, mentionfilter
from feather.databases import Bill, Bank, User, Nodeclass, Node, \
		Topic, Reply, Notify


blog = Module(__name__)

@blog.route('/blog', defaults={'page': 1})
@blog.route('/blog/page/<int:page>')
def index(page):
	page_obj = Topic.query.filter_by(report=3).order_by(Topic.date.desc()).paginate(page, per_page=config.PER_PAGE)
	page_url = lambda page: url_for("blog.index", page=page)
	return render_template('blog.html', page_obj=page_obj, page_url=page_url)

@blog.route('/blog/add', methods=['GET', 'POST'])
def blog_add():
	node = Node.query.filter_by(name=u'爱情').first()
	if session.get('user_id') != 1:
		return redirect(url_for('topic.index'))
	if request.method == 'POST':
		topic = Topic(author=g.user, title=request.form['title'], text=request.form['text'], text_origin=request.form['text'], reply_count=0, node=node, report=3)
		db.session.add(topic)
		db.session.commit()
		return redirect(url_for('blog.blog_view', topic_id=topic.id))
	return render_template('blog_add.html', node=node)

@blog.route('/blog/<int:topic_id>')
def blog_view(topic_id):
	topic = Topic.query.get(topic_id)
	return render_template('blog_view.html', topic=topic)

@blog.route('/blog/edit/<int:topic_id>', methods=['GET', 'POST'])
def blog_edit(topic_id):
	if session['user_id'] != 1:
		return redirect(url_for('topic.index'))
	topic = Topic.query.get(topic_id)
	if request.method == 'POST':
		topic.title = request.form['title']
		topic.text = request.form['text']
		db.session.commit()
		return redirect(url_for('blog.blog_view', topic_id=topic_id))
	return render_template('blog_edit.html', topic=topic)


@blog.route('/blog/<int:topic_id>/reply', methods=['POST'])
def blog_reply(topic_id):
	topic = Topic.query.get(topic_id)
	reply = Reply(topic=topic, author=g.user, text=request.form['reply[content]'], text_origin=request.form['reply[content]'], type=2)
	db.session.add(reply)
	db.session.commit()
	return redirect(url_for('blog.blog_view', topic_id=topic_id))

########NEW FILE########
__FILENAME__ = city
# coding: utf-8
from flask import Module, render_template
from feather.extensions import db
from feather.databases import City, User

city = Module(__name__)

@city.route('/city/<citysite>')
def city_view(citysite):
	city = City.query.filter_by(site=citysite).first()
	users = city.users.order_by(User.id.asc()).all()
	return render_template('city_view.html',city=city,users=users)


########NEW FILE########
__FILENAME__ = love
# coding: utf-8
import time
from flask import Module, request, session, g, redirect, url_for, \
		abort, render_template, flash, jsonify
from flask_sqlalchemy import Pagination
from feather import config
from feather.extensions import db, cache
from feather.helpers import mentions, mentionfilter
from feather.databases import Bill, Bank, User, Nodeclass, Node, \
		Topic, Reply, Notify


love = Module(__name__)

@love.route('/love', defaults={'page': 1})
@love.route('/love/page/<int:page>')
def index(page):
	if not session.get('user_id'):
		return redirect(url_for('account.login'))
	if session.get('user_id') != 1 and session.get('user_id') != 2:
		return redirect(url_for('topic.index'))
	page_obj = Topic.query.filter_by(report=2).order_by(Topic.date.desc()).paginate(page, per_page=config.PER_PAGE)
	page_url = lambda page: url_for("love.index", page=page)
	return render_template('love.html', page_obj=page_obj, page_url=page_url)

@love.route('/love/add', methods=['GET', 'POST'])
def love_add():
	node = Node.query.filter_by(name=u'爱情').first()
	if not session.get('user_id'):
		return redirect(url_for('account.login'))
	if session.get('user_id') != 1 and session.get('user_id') != 2:
		return redirect(url_for('topic.index'))
	if request.method == 'POST':
		topic = Topic(author=g.user, title=request.form['title'], text=request.form['text'], text_origin=request.form['text'], reply_count=0, node=node, report=2)
		db.session.add(topic)
		db.session.commit()
		return redirect(url_for('love.love_view', topic_id=topic.id))
	return render_template('love_add.html', node=node)

@love.route('/love/<int:topic_id>')
def love_view(topic_id):
	topic = Topic.query.get(topic_id)
	return render_template('love_view.html', topic=topic)

@love.route('/love/edit/<int:topic_id>', methods=['GET', 'POST'])
def love_edit(topic_id):
	if session['user_id'] != 1 and session['user_id'] != 2:
		return redirect(url_for('topic.index'))
	topic = Topic.query.get(topic_id)
	if request.method == 'POST':
		topic.title = request.form['title']
		topic.text = request.form['text']
		db.session.commit()
		return redirect(url_for('love.love_view', topic_id=topic_id))
	return render_template('love_edit.html', topic=topic)

@love.route('/love/<int:topic_id>/reply', methods=['POST'])
def love_reply(topic_id):
	topic = Topic.query.get(topic_id)
	reply = Reply(topic=topic, author=g.user, text=request.form['reply[content]'], text_origin=request.form['reply[content]'], type=1)
	db.session.add(reply)
	db.session.commit()
	return redirect(url_for('love.love_view', topic_id=topic_id))

########NEW FILE########
__FILENAME__ = node
# coding: utf-8
from flask import Module, request, session, g, redirect, url_for, \
		abort, render_template, flash
from feather import config
from feather.helpers import textformat, markdown
from feather.extensions import db
from feather.databases import Nodeclass, Node, Topic

node = Module(__name__)


def get_node(nodesite):
	rv = Node.query.filter_by(site=nodesite).first()
	return rv

def get_topicscount(node):
	return node.topics.count()

@node.route('/add/node', methods=['GET', 'POST'])
def node_add():
	if session['user_id'] != 1:
		abort(401)
	if request.method == 'POST':
		if session['user_id'] != 1:
			abort(401)
		nodeclass = Nodeclass.query.filter_by(name=request.form['nodeclass']).first()
		if not nodeclass:
			nodeclass = Nodeclass(request.form['nodeclass'])
			db.session.add(nodeclass)
			db.session.commit()
		nodeclass = Nodeclass.query.filter_by(name=request.form['nodeclass']).first()
		if request.form['nodename'] == '' or request.form['nodesite'] == '' or request.form['nodeclass'] == '':
			error = u'请填写完整信息！'
			return render_template('node_add.html', error=error)
		elif Node.query.filter_by(name=request.form['nodename']).first() is not None:
			error = u'节点名称已存在！'
			return render_template('node_add.html', error=error)
		elif Node.query.filter_by(site=request.form['nodesite']).first() is not None:
			error = u'节点地址已存在！'
			return render_template('node_add.html', error=error)
		else:
			description = textformat(request.form['description'])
			description = markdown(description)
			node = Node(name=request.form['nodename'], site=request.form['nodesite'], description=description, description_origin=request.form['description'], nodeclass=nodeclass)
			db.session.add(node)
			db.session.commit()
			flash(u'添加成功！')
			return redirect(url_for('topic.tab_view'))
	return render_template('node_add.html')

@node.route('/node/<nodesite>/edit', methods=['GET', 'POST'])
def node_edit(nodesite):
	if session['user_id'] != 1:
		abort(401)
	node = Node.query.filter_by(site=nodesite).first()
	if request.method == 'POST':
		if request.form['nodename'] == '' or request.form['nodesite'] == '' or request.form['nodeclass'] == '':
			error = u'请填写完整信息！'
			return render_template('node_edit.html', node=node, error=error)
		elif request.form['nodename'] != node.name and Node.query.filter_by(name=request.form['nodename']).first() is not None:
			error = u'节点名称已存在！'
			return render_template('node_edit.html', node=node, error=error)
		elif request.form['nodesite'] != node.site and Node.query.filter_by(site=request.form['nodesite']).first() is not None:
			error = u'节点地址已存在！'
			return render_template('node_edit.html', node=node, error=error)
		else:
			nodeclass = Nodeclass.query.filter_by(name=request.form['nodeclass']).first()
			if not nodeclass:
				nodeclass = Nodeclass(request.form['nodeclass'])
				db.session.add(nodeclass)
				db.session.commit()
			nodeclass = Nodeclass.query.filter_by(name=request.form['nodeclass']).first()
			description = textformat(request.form['description'])
			description = markdown(description)
			header = markdown(request.form['header'])
			node.name = request.form['nodename']
			node.site = request.form['nodesite']
			node.description = description
			node.header = header
			node.description_origin = request.form['description']
			node.header_origin = request.form['header']
			node.style = request.form['style']
			node.nodeclass = nodeclass
			db.session.commit()
			flash(u'节点修改成功！')
			return redirect(url_for('node.index', nodesite=nodesite))
	return render_template('node_edit.html',node=node)

@node.route('/node/<nodesite>', defaults={'page': 1})
@node.route('/node/<nodesite>/page/<int:page>')
def index(nodesite,page):
	node = get_node(nodesite)
	topicscount = get_topicscount(node)
	page_obj = Topic.query.filter_by(node=node).filter_by(report=0).order_by(Topic.last_reply_date.desc()).paginate(page, per_page=config.PER_PAGE)
	page_url = lambda page: url_for("node.index", nodesite=nodesite, page=page)
	return render_template('node_index.html', page_obj=page_obj, page_url=page_url, node=node, topicscount=topicscount)



########NEW FILE########
__FILENAME__ = reply
# coding: utf-8
import time
from flask import Module, request, session, g, redirect, url_for, \
		abort, render_template, flash
from feather import config
from feather.extensions import db
from feather.helpers import mentions, mentionfilter, textformat, markdown
from feather.databases import Bill, User, Topic, Reply, Notify

reply = Module(__name__)


@reply.route('/topic/<int:topic_id>/reply',methods=['POST'])
def add_reply(topic_id):
	if not session.get('user_id'):
		abort(401)
	if g.user.time < 5:
		g.error = u'抱歉，您的时间不足5分钟！'
		return redirect(url_for('topic.topic_view', topic_id=topic_id) + "#replyend")
	if request.form['reply[content]'] == '':
		g.error = u'抱歉，您的时间不足5分钟！'
		return redirect(url_for('topic.topic_view', topic_id=topic_id) + "#replyend")
	topic = Topic.query.get(topic_id)
	if topic.replys is not None:
		numbered = len(topic.replys.all())
	else:
		numbered = 0
	page_obj = topic.replys.paginate(1, per_page=config.RE_PER_PAGE)
	if page_obj.pages == 0:
		page = 1
	elif len(topic.replys.all()) % config.RE_PER_PAGE == 0:
		page = page_obj.pages + 1
	else:
		page = page_obj.pages
	if '@' in request.form['reply[content]']:
		reply_content = mentionfilter(request.form['reply[content]'])
	else:
		reply_content = request.form['reply[content]']
	reply_content = textformat(reply_content)
	reply_content = markdown(reply_content)
	reply = Reply(topic=topic, author=g.user, text=reply_content, text_origin=request.form['reply[content]'], number=numbered + 1)
	g.user.time -= 5
	topic.author.time += 5
	topic.last_reply_date = int(time.time())
	topic.reply_count += 1
	for reader in topic.readers:
		topic.readers.remove(reader)
	db.session.add(reply)
	db.session.commit()
	t = int(time.time())
	if session['user_id'] != topic.author.id:
		bill = Bill(author=g.user,time=5,type=3,date=t,reply=reply,user_id=topic.author.id,balance=g.user.time)
		bill2 = Bill(author=topic.author,time=5,type=5,date=t,reply=reply,user_id=g.user.id,balance=topic.author.time)
		db.session.add(bill)
		db.session.add(bill2)
		db.session.commit()
		notify = Notify(author=topic.author, topic=topic, reply=reply, type=1)
		db.session.add(notify)
		db.session.commit()
	if '@' in request.form['reply[content]']:
		content = request.form['reply[content]'].replace('\n','')
		usernames = list(set(mentions(content)))
		for username in usernames:
			author = User.query.filter_by(name=username).first()
			if author.id != topic.author.id and author.id != g.user.id:
				notify = Notify(author, topic, reply=reply, type=2)
				db.session.add(notify)
				db.session.commit()
	return redirect(url_for('topic.topic_view', topic_id=topic_id, page=page) + "#replyend")


@reply.route('/del/reply<int:reply_id>')
def del_reply(reply_id):
	reply = Reply.query.get(reply_id)
	reply.topic.reply_count -= 1
	db.session.delete(reply)
	db.session.commit()
	flash(u'成功删除一条评论！')
	return redirect(url_for('topic.topic_view', topic_id=reply.topic.id) + '#replys')



@reply.route('/reply/<int:reply_id>/edit<int:page>', methods=['GET', 'POST'])
def reply_edit(reply_id, page):
	reply = Reply.query.get(reply_id)
	if session.get('user_id') == reply.author.id or session.get('user_id') == 1:
		if request.method == 'POST':
			if not session.get('user_id'):
				abort(401)
			if '@' in request.form['reply[content]']:
				reply_content = mentionfilter(request.form['reply[content]'])
			else:
				reply_content = request.form['reply[content]']
			reply_content = textformat(reply_content)
			reply_content = markdown(reply_content)
			reply = Reply.query.get(reply_id)
			reply.text = reply_content
			reply.text_origin = request.form['reply[content]']
			db.session.commit()
			return redirect(url_for('topic.topic_view', topic_id=reply.topic.id, page=page) + '#replys')
		return render_template('reply_edit.html', reply=reply, topic=reply.topic, page=page)
	else:
		abort(401)


@reply.route('/reply/<int:reply_id>/thank')
def thank(reply_id):
	if not session.get('user_id'):
		abort(401)
	reply = Reply.query.get(reply_id)
	user = g.user
	if reply in user.thanks:
		return redirect(url_for('topic.topic_view', topic_id=reply.topic.id) + '#reply-' + str(reply_id))
	else:
		author = reply.author
		user.thanks += [reply]
		user.time -= 10
		author.time += 10
		db.session.commit()
		t = int(time.time())
		bill = Bill(author=g.user,time=10,type=4,date=t,reply=reply,user_id=reply.author.id,balance=g.user.time)
		bill2 = Bill(author=reply.author,time=10,type=6,date=t,reply=reply,user_id=g.user.id,balance=reply.author.time)
		db.session.add(bill)
		db.session.add(bill2)
		db.session.commit()
		return redirect(url_for('topic.topic_view', topic_id=reply.topic.id) + '#reply-' + str(reply_id))


########NEW FILE########
__FILENAME__ = timesystem
# coding: utf-8
from flask import Module, abort, render_template, url_for
from feather import config
from feather.extensions import db, cache
from feather.databases import Bill, Bank
from sqlalchemy import or_

timesystem = Module(__name__)

@timesystem.route('/bank', defaults={'page': 1})
@timesystem.route('/bank/page/<int:page>')
@cache.cached(60 * 5)
def bank(page):
	bank = Bank.query.get(1)
	if not bank:
		abort(401)
	page_obj = Bill.query.filter(or_(Bill.type == 1, Bill.type == 2, Bill.type == 7, Bill.type == 8)).order_by(Bill.date.desc()).paginate(page, per_page=config.RE_PER_PAGE)
	page_url = lambda page: url_for("timesystem.bank", page=page)
	return render_template('bank.html', bank=bank, page_obj=page_obj, page_url=page_url)


########NEW FILE########
__FILENAME__ = topic
# coding: utf-8
import time
from flask import Module, request, session, g, redirect, url_for, \
		abort, render_template, flash, jsonify
from flask_sqlalchemy import Pagination
from feather import config
from feather.extensions import db, cache
from feather.helpers import mentions, mentionfilter, textformat, markdown
from feather.databases import Bill, Bank, User, Nodeclass, Node, \
		Topic, Reply, Notify


topic = Module(__name__)


@cache.cached(60 * 60, key_prefix='liketopics/%d')
def get_liketopics(topicid):
	topic = Topic.query.get(topicid)
	liketopics = []
	i = 0
	for n in Topic.query.filter(Topic.report == 0).all():
		if i == 6:
			break
		if liketopic(topic.title,n.title) == 0:
			liketopics += [n]
			i += 1
			continue
		elif liketopic(topic.title,n.title) == 1:
			liketopics += [n]
			i += 1
			continue
		elif liketopic(topic.title,n.title) == 2:
			liketopics += [n]
			i += 1
			continue
	return liketopics

@cache.cached(60 * 15, key_prefix='sitestatus')
def get_sitestatus():
	usercount = User.query.count()
	topiccount = Topic.query.filter(Topic.report == 0).count()
	replycount = Reply.query.filter(Reply.type == 0).count()
	rv = (usercount, topiccount, replycount)
	return rv

@cache.cached(1200, key_prefix='hottopics')
def get_hottopics():
	nowtime = int(time.time())
	agotime = nowtime - 24*60*60
	rv = Topic.query.filter(Topic.report == 0).filter(Topic.date <= nowtime).filter(Topic.date >= agotime).order_by(Topic.reply_count.desc()).limit(10).all()
	return rv

def get_nodeclass(tabname):
	return Nodeclass.query.filter_by(name=tabname).first()

@cache.cached(60 * 60, key_prefix='includes/%s')
def get_includes(tabname):
	nodeclass = get_nodeclass(tabname)
	return nodeclass.nodes.all() if nodeclass is not None else None


def liketopic(a,b):
	import difflib
	return len(filter(lambda i: i.startswith('+'), difflib.ndiff(a,b)))

class Getdate:
	def __init__(self, time):
		self.time = time
	def year(self):
		return int(time.strftime('%Y', time.localtime(self.time)))
	def month(self):
		return int(time.strftime('%m', time.localtime(self.time)))
	def day(self):
		return int(time.strftime('%d', time.localtime(self.time)))


@topic.route('/<tabname>', defaults={'page': 1})
@topic.route('/index', defaults={'page': 1, 'tabname': 'All'})
@topic.route('/page/<int:page>', defaults={'tabname': 'All'})
@topic.route('/<tabname>/page/<int:page>')
def index(page, tabname):
	(usercount, topiccount, replycount) = get_sitestatus()
	hottopics = get_hottopics()
	nodeclasses = Nodeclass.query.all()
	nodeclass = get_nodeclass(tabname)
	includenodes = get_includes(tabname)
	if tabname == 'All':
		page_obj = Topic.query.filter_by(report=0).order_by(Topic.last_reply_date.desc()).paginate(page, per_page=config.PER_PAGE)
		page_url = lambda page: url_for("topic.index", page=page, tabname='All')
	elif nodeclass is None:
		tabname = 'Geek'
		nodeclass = get_nodeclass(tabname)
		includenodes = get_includes(tabname)
		page_obj = Topic.query.filter_by(report=0).filter_by(nodeclass=nodeclass).order_by(Topic.last_reply_date.desc()).paginate(page, per_page=config.PER_PAGE)
		page_url = lambda page: url_for("topic.index", page=page, tabname='Geek')
	else:
		page_obj = Topic.query.filter_by(report=0).filter_by(nodeclass=nodeclass).order_by(Topic.last_reply_date.desc()).paginate(page, per_page=config.PER_PAGE)
		page_url = lambda page: url_for("topic.index", page=page, tabname=nodeclass.name)
	return render_template('index.html', page_obj=page_obj, page_url=page_url, nodeclasses=nodeclasses, nodeclass=nodeclass, usercount=usercount, topiccount=topiccount, replycount=replycount, hottopics=hottopics, tabname=tabname, includenodes=includenodes)

@topic.route('/', defaults={'tabname': 'index'})
@topic.route('/tab/<tabname>')
def tab_view(tabname):
	if not session.get('user_id'):
		if tabname == 'index':
			return redirect(url_for('topic.index', tabname='All'))
		else:
			return redirect(url_for('topic.index', tabname=tabname))
	if tabname == 'index' and session.get('user_id'):
		if g.user.tab_id == 0:
			return redirect(url_for('topic.index', tabname='All'))
		elif g.user.tab_id != -1:
			nodeclass = Nodeclass.query.get(g.user.tab_id)
			return redirect(url_for('topic.index', tabname=nodeclass.name))
		else:
			return redirect(url_for('topic.index', tabname='Geek'))
	else:
		nodeclass = Nodeclass.query.filter_by(name=tabname).first()
		if nodeclass is not None and session.get('user_id'):
			g.user.tab_id = nodeclass.id
			db.session.commit()
			return redirect(url_for('topic.index', tabname=tabname))
		elif tabname == 'all' or tabname == 'All':
			g.user.tab_id = 0
			db.session.commit()
			return redirect(url_for('topic.index', tabname='All'))

@topic.route('/add/<nodesite>', methods=['GET', 'POST'])
def topic_add(nodesite):
	if not session.get('user_id'):
		return redirect(url_for('account.login'))
	node = Node.query.filter_by(site=nodesite).first()
	if request.method == 'POST':
		if g.user.time < 20:
			flash(u'时间不足20分钟！')
			return redirect(url_for('topic.index'))
		node = Node.query.filter_by(site=nodesite).first()
		if request.form['title'] == '':
			g.error = u'请输入主题标题！'
			render_template('topic_add.html', node=node)
		elif request.form['text'] == '':
			g.error = u'请输入主题内容！'
			render_template('topic_add.html', node=node)
		else:
			if '@' in request.form['text']:
				text = mentionfilter(request.form['text'])
			else:
				text = request.form['text']
			text = textformat(text)
			text = markdown(text)
			topic = Topic(author=g.user, title=request.form['title'], text=text, text_origin=request.form['text'], node=node, reply_count=0)
			bank = Bank.query.get(1)
			g.user.time -= 20
			bank.time +=20
			db.session.add(topic)
			db.session.commit()
			bill = Bill(author=g.user,time=20,type=2,date=int(time.time()),topic=topic,balance=g.user.time)
			db.session.add(bill)
			db.session.commit()
			flash(u'发布成功！')
			if '@' in request.form['title']:
				title = request.form['title'].replace('\n','')
				usernames = list(set(mentions(title)))
				for username in usernames:
					author = User.query.filter_by(name=username).first()
					if author.id != g.user.id:
						notify = Notify(author, topic, reply=None, type=3)
						db.session.add(notify)
						db.session.commit()
			if '@' in request.form['text']:
				text = request.form['text'].replace('\n','')
				usernames = list(set(mentions(text)))
				for username in usernames:
					author = User.query.filter_by(name=username).first()
					if author.id != g.user.id:
						notify = Notify(author, topic, reply=None, type=3)
						db.session.add(notify)
						db.session.commit()
			return redirect(url_for('topic.topic_view', topic_id=topic.id))
	return render_template('topic_add.html', node=node)


@topic.route('/del/<int:topic_id>')
def del_topic(topic_id):
	topic = Topic.query.get(topic_id)
	replys = topic.replys.all()
	if replys:
		for reply in replys:
			db.session.delete(reply)
	db.session.delete(topic)
	db.session.commit()
	flash(u'成功删除一条记录！')
	return redirect(url_for('topic.index'))


@topic.route('/topic/<int:topic_id>/edit', methods=['GET', 'POST'])
def topic_edit(topic_id):
	topic = Topic.query.get(topic_id)
	if session.get('user_id') == topic.author.id or session.get('user_id') == 1:
		if request.method == 'POST':
			if request.form['title'] == '':
				g.error = u'请输入主题标题！'
				render_template('topic_edit.html', topic=topic)
			elif request.form['text'] == '':
				g.error = u'请输入主题内容！'
				render_template('topic_edit.html', topic=topic)
			else:
				if '@' in request.form['text']:
					text = mentionfilter(request.form['text'])
				else:
					text = request.form['text']
				text = textformat(text)
				text = markdown(text)
				topic.title = request.form['title']
				topic.text = text
				topic.text_origin = request.form['text']
				topic.date = int(time.time())
				db.session.commit()
				flash(u'修改成功！')
				return redirect(url_for('topic.topic_view',topic_id=topic_id))
		return render_template('topic_edit.html', topic=topic)
	else:
		abort(401)


@topic.route('/topic/<int:topic_id>', defaults={'page': 1})
@topic.route('/topic/<int:topic_id>/page/<int:page>')
def topic_view(topic_id, page):
	topic = Topic.query.get(topic_id)
	liketopics = get_liketopics(topic.id)
	page_obj = topic.replys.order_by(Reply.date.asc()).paginate(page, per_page=config.RE_PER_PAGE)
	page_url = lambda page: url_for("topic.topic_view", topic_id=topic_id, page=page)
	if g.user:
		if topic not in g.user.reads:
			g.user.reads += [topic]
			db.session.commit()
	return render_template('topic_view.html', topic=topic, liketopics=liketopics, page_obj=page_obj, page_url=page_url, page=page)



@topic.route('/topic/<int:topic_id>/fav', defaults={'page': 1})
def fav(topic_id, page):
	if not session.get('user_id'):
		abort(401)
	topic = Topic.query.get(topic_id)
	user = g.user
	if topic in user.favorites:
		flash(u'抱歉，暂不支持这个功能 T-T')
		return redirect(url_for('account.favorites', page=page))
	else:
		user.favorites += [topic]
		db.session.commit()
		return redirect(url_for('topic.topic_view', topic_id=topic.id) + "#topic")

@topic.route('/topic/<int:topic_id>/vote')
def vote(topic_id):
	if not session.get('user_id'):
		abort(401)
	topic = Topic.query.get(topic_id)
	user = g.user
	if topic in user.votes:
		return redirect(url_for('topic.topic_view', topic_id=topic.id) + "#;")
	else:
		user.votes += [topic]
		topic.vote += 1
		if topic.vote >= 10:
			topic.report = 1
		db.session.commit()
		flash(u'已举报，谢谢参与社区建设。')
		return redirect(url_for('topic.topic_view', topic_id=topic.id) + "#;")


@topic.route('/trash', defaults={'page': 1})
@topic.route('/trash/page/<int:page>')
def trash(page):
	page_obj = Topic.query.filter_by(report=1).order_by(Topic.last_reply_date.desc()).paginate(page, per_page=config.PER_PAGE)
	page_url = lambda page: url_for("topic.trash", page=page)
	return render_template('trash.html', page_obj=page_obj, page_url=page_url)

@topic.route('/allusers')
def allusers():
	users = User.query.all()
	return jsonify(names=[x.name for x in users])

@topic.route('/about')
def about():
	return render_template('about.html')

########NEW FILE########
__FILENAME__ = run
# coding: utf-8
from flaskext.script import Manager, Server, prompt_bool
from feather import app, db

manager = Manager(app)
server = Server(host='0.0.0.0', port=8888)
manager.add_command("runserver", server)

@manager.command
def createall():
	db.create_all()

@manager.command
def dropall():
	if prompt_bool(u"警告：你将要删除全部的数据！你确定否？"):
		db.drop_all()

if __name__ == "__main__":
	manager.run()

########NEW FILE########
