__FILENAME__ = fabfile
from fabric.api import run, env, cd, prefix
from xichuangzhu import config


def deploy():
    env.host_string = config.HOST_STRING
    with cd('/var/www/xichuangzhu'):
        run('git pull')
        run('bower install --allow-root')
        with prefix('source venv/bin/activate'):
            run('pip install -r requirements.txt')
        run('sudo supervisorctl restart xcz')


def restart():
    env.host_string = config.HOST_STRING
    run('sudo supervisorctl restart xcz')
########NEW FILE########
__FILENAME__ = manage
# coding: utf-8
from flask.ext.script import Manager
from flask.ext.migrate import Migrate, MigrateCommand
from fabric.api import run as fabrun, env
from xichuangzhu import app
from xichuangzhu.models import db

manager = Manager(app)

migrate = Migrate(app, db)
manager.add_command('db', MigrateCommand)


@manager.command
def run():
    """启动app"""
    app.run(debug=True)


@manager.command
def syncdb():
    """根据model创建数据库tables"""
    db.create_all()


@manager.command
def backdb():
    """将数据库中的表结构和数据提取为sql文件"""
    env.host_string = "localhost"
    fabrun("mysqldump -uroot -p xcz > /var/www/xichuangzhu/xcz.sql")


@manager.command
def test():
    pass


if __name__ == "__main__":
    manager.run()
########NEW FILE########
__FILENAME__ = env
from __future__ import with_statement
from alembic import context
from sqlalchemy import engine_from_config, pool
from logging.config import fileConfig

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
from flask import current_app
config.set_main_option('sqlalchemy.url', current_app.config.get('SQLALCHEMY_DATABASE_URI'))
target_metadata = current_app.extensions['migrate'].db.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url)

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    engine = engine_from_config(
                config.get_section(config.config_ini_section),
                prefix='sqlalchemy.',
                poolclass=pool.NullPool)

    connection = engine.connect()
    context.configure(
                connection=connection,
                target_metadata=target_metadata
                )

    try:
        with context.begin_transaction():
            context.run_migrations()
    finally:
        connection.close()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()


########NEW FILE########
__FILENAME__ = base
import unittest
import xichuangzhu as xcz

class TestBase(unittest.TestCase):

    def setUp(self):
        xcz.app.config['TESTING'] = True
        self.app = xcz.app.test_client()

    def test_a(self):
        assert True

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()
########NEW FILE########
__FILENAME__ = test_author
from .base import TestBase

class TestAuthor(TestBase):
	def test_aa():
		pass


    
########NEW FILE########
__FILENAME__ = test_dynasty

########NEW FILE########
__FILENAME__ = test_sign

########NEW FILE########
__FILENAME__ = test_site

########NEW FILE########
__FILENAME__ = test_topic

########NEW FILE########
__FILENAME__ = test_user

########NEW FILE########
__FILENAME__ = test_work

########NEW FILE########
__FILENAME__ = test_work_image

########NEW FILE########
__FILENAME__ = test_work_review

########NEW FILE########
__FILENAME__ = config_sample
# coding: utf-8

# set False in production
DEBUG = True

# Such as "root@12.34.56.78"
HOST_STRING = ""

# site domain
SITE_DOMAIN = "http://localhost:5000"
IMAGE_SERVER_URL = "http://localhost"

# image upload path
UPLOADS_DEFAULT_DEST = "/var/www/xcz_uploads"
UPLOADS_DEFAULT_URL = "%s/xcz_uploads/" % IMAGE_SERVER_URL

# app config
SECRET_KEY = ""
PERMANENT_SESSION_LIFETIME = 3600 * 24 * 7
SESSION_COOKIE_NAME = 'xcz_session'

# db config
DB_HOST = ""
DB_USER = ""
DB_PASSWORD = ""
DB_NAME = "xcz"
SQLALCHEMY_DATABASE_URI = "mysql://%s:%s@%s/%s" % (DB_USER, DB_PASSWORD, DB_HOST, DB_NAME)

# smtp config
MAIL_SERVER = ''
MAIL_PORT = 25
MAIL_USE_TLS = False
MAIL_USE_SSL = False
MAIL_DEBUG = DEBUG
MAIL_USERNAME = ''
MAIL_PASSWORD = ''
MAIL_DEFAULT_SENDER = ''
MAIL_MAX_EMAILS = None
MAIL_ADMIN_ADDR = ''

# Flask debug toolbar
DEBUG_TB_INTERCEPT_REDIRECTS = False

# douban oauth2 config
DOUBAN_CLIENT_ID = '0cf909cba46ce67526eb1d62ed46b35f'
DOUBAN_SECRET = '4c87a8ef33e6c6be'
DOUBAN_REDIRECT_URI = '%s/account/signin' % SITE_DOMAIN
DOUBAN_LOGIN_URL = "https://www.douban.com/service/auth2/auth?client_id=%s&redirect_uri=%s&response_type=code" % (
    DOUBAN_CLIENT_ID, DOUBAN_REDIRECT_URI)

# aliyun oss config
OSS_HOST = 'oss.aliyuncs.com'
OSS_KEY = ''
OSS_SECRET = ''
OSS_URL = ''
########NEW FILE########
__FILENAME__ = account
# coding: utf-8
import requests
import hashlib
from flask import render_template, request, redirect, url_for, Blueprint, flash, abort, g
from .. import config
from ..models import db, User
from ..utils import signin_user, signout_user
from ..forms import SignupForm, SettingsForm
from ..roles import NewUserRole, BanUserRole, UserRole
from ..permissions import require_visitor, new_user_permission
from ..mails import signup_mail

bp = Blueprint('account', __name__)


@bp.route('/signin')
@require_visitor
def signin():
    """通过豆瓣OAuth登陆"""
    # get current authed user id
    code = request.args.get('code')
    if not code:
        abort(500)
    url = "https://www.douban.com/service/auth2/token"
    data = {
        'client_id': config.DOUBAN_CLIENT_ID,
        'client_secret': config.DOUBAN_SECRET,
        'redirect_uri': config.DOUBAN_REDIRECT_URI,
        'grant_type': 'authorization_code',
        'code': code
    }
    res = requests.post(url, data=data).json()
    user_id = int(res['douban_user_id'])

    user = User.query.get(user_id)
    if user:
        if user.role == BanUserRole:
            flash('账户已被禁用')
            return redirect(url_for('site.index'))
        if user.role == NewUserRole:
            flash('账户尚未激活，请登陆邮箱激活账户')
        signin_user(user, True)
        return redirect(url_for('site.index'))
    return redirect(url_for('.signup', user_id=user_id))


@bp.route('/signup/<int:user_id>', methods=['GET', 'POST'])
@require_visitor
def signup(user_id):
    """发送激活邮件"""
    # Get user info from douban
    url = "https://api.douban.com/v2/user/%d" % user_id
    user_info = requests.get(url).json()
    form = SignupForm()
    if form.validate_on_submit():
        to_addr = form.email.data
        user = User(id=user_id, name=user_info['name'], abbr=user_info['uid'],
                    signature=user_info['signature'], email=to_addr)
        # 如果存在大图，则使用大图
        if user_info['large_avatar'] != "http://img3.douban.com/icon/user_large.jpg":
            user.avatar = user_info['large_avatar']
        else:
            user.avatar = user_info['avatar']
        db.session.add(user)
        db.session.commit()
        signin_user(user, True)

        # send activate email
        try:
            signup_mail(user)
        except:
            flash('邮件发送失败，请稍后尝试')
        else:
            flash('激活邮件已发送到你的邮箱，请查收')
        return redirect(url_for('site.index'))
    return render_template('account/signup.html', user_info=user_info, form=form)


@bp.route('/activate/<int:user_id>/<token>')
def activate(user_id, token):
    """激活用户"""
    user = User.query.get_or_404(user_id)
    if token == hashlib.sha1(user.name).hexdigest():
        user.role = UserRole
        db.session.add(user)
        db.session.commit()
        signin_user(user, True)
        flash('账号激活成功！')
        return redirect(url_for('site.index'))
    flash('无效的激活链接')
    return redirect(url_for('site.index'))


@bp.route('/signout')
def signout():
    """登出"""
    signout_user()
    return redirect(url_for('site.index'))


@bp.route('/settings', methods=['GET', 'POST'])
@new_user_permission
def settings():
    """个人设置"""
    form = SettingsForm(signature=g.user.signature)
    if form.validate_on_submit():
        g.user.signature = form.signature.data
        db.session.add(g.user)
        db.session.commit()
        flash('设置已保存')
        return redirect(url_for('.settings'))
    return render_template('account/settings.html', form=form)


@bp.route('/resend_activate_mail')
@new_user_permission
def resend_activate_mail():
    if g.user_role != NewUserRole:
        abort(403)
    try:
        signup_mail(g.user)
    except:
        flash('邮件发送失败，请稍后尝试')
    else:
        flash('激活邮件已发送到你的邮箱，请查收')
    return redirect(url_for('.settings'))
########NEW FILE########
__FILENAME__ = admin
# coding: utf-8
from flask import render_template, Blueprint, request
from ..models import Work, Author, Dynasty, WorkType
from ..permissions import admin_permission

bp = Blueprint('admin', __name__)


@bp.route('/authors', defaults={'page': 1})
@bp.route('/authors/<int:page>', methods=['GET', 'POST'])
@admin_permission
def authors(page):
    """管理文学家"""
    paginator = Author.query.paginate(page, 30)
    return render_template('admin/authors.html', paginator=paginator)


@bp.route('/works', defaults={'page': 1})
@bp.route('/works/page/<int:page>', methods=['GET', 'POST'])
@admin_permission
def works(page):
    """管理作品"""
    paginator = Work.query.paginate(page, 15)
    return render_template('admin/works.html', paginator=paginator)


@bp.route('/highlight_works', defaults={'page': 1})
@bp.route('/highlight_works/page/<int:page>', methods=['GET', 'POST'])
@admin_permission
def highlight_works(page):
    """全部加精作品"""
    work_type = request.args.get('type', 'all')
    dynasty_abbr = request.args.get('dynasty', 'all')
    works = Work.query.filter(Work.highlight == True)
    if work_type != 'all':
        works = works.filter(Work.type.has(WorkType.en == work_type))
    if dynasty_abbr != 'all':
        works = works.filter(Work.author.has(Author.dynasty.has(Dynasty.abbr == dynasty_abbr)))
    paginator = works.paginate(page, 15)
    work_types = WorkType.query
    dynasties = Dynasty.query.order_by(Dynasty.start_year.asc())
    return render_template('admin/highlight_works.html', paginator=paginator, work_type=work_type,
                           dynasty_abbr=dynasty_abbr, work_types=work_types, dynasties=dynasties)

########NEW FILE########
__FILENAME__ = author
# coding: utf-8
from flask import render_template, request, redirect, url_for, Blueprint
from ..models import db, Author, AuthorQuote, Work, WorkType, CollectWork, Dynasty
from ..permissions import admin_permission
from ..forms import AuthorForm, AuthorQuoteForm

bp = Blueprint('author', __name__)


@bp.route('/<author_abbr>')
def view(author_abbr):
    """文学家主页"""
    author = Author.query.filter(Author.abbr == author_abbr).first_or_404()
    quote_id = request.args.get('q')
    quote = AuthorQuote.query.get(quote_id) if quote_id else author.random_quote
    stmt = db.session.query(Work.type_id, db.func.count(Work.type_id).label('type_num')).filter(
        Work.author_id == author.id).group_by(Work.type_id).subquery()
    work_types = db.session.query(WorkType, stmt.c.type_num) \
        .join(stmt, WorkType.id == stmt.c.type_id)
    return render_template('author/author.html', author=author, quote=quote, work_types=work_types)


@bp.route('/')
def authors():
    """全部文学家"""
    # 仅获取包含至少1个文学家的朝代
    dynasties = Dynasty.query.filter(Dynasty.authors.any()).order_by(Dynasty.start_year.asc())
    # get the authors who's works are latest collected by user
    stmt = db.session.query(Author.id, CollectWork.create_time).join(Work).join(
        CollectWork).group_by(Author.id).having(
        db.func.max(CollectWork.create_time)).subquery()
    hot_authors = Author.query.join(stmt, Author.id == stmt.c.id).order_by(
        stmt.c.create_time.desc()).limit(8)
    return render_template('author/authors.html', dynasties=dynasties, hot_authors=hot_authors)


@bp.route('/add', methods=['GET', 'POST'])
@admin_permission
def add():
    """添加文学家"""
    form = AuthorForm()
    form.dynasty_id.choices = [(d.id, d.name) for d in Dynasty.query.order_by(Dynasty.start_year)]
    if form.validate_on_submit():
        author = Author(**form.data)
        db.session.add(author)
        db.session.commit()
        return redirect(url_for('.view', author_abbr=author.abbr))
    return render_template('author/add.html', form=form)


@bp.route('/<int:author_id>/edit', methods=['GET', 'POST'])
@admin_permission
def edit(author_id):
    """编辑文学家"""
    author = Author.query.get_or_404(author_id)
    form = AuthorForm(obj=author)
    form.dynasty_id.choices = [(d.id, d.name) for d in Dynasty.query.order_by(Dynasty.start_year)]
    if form.validate_on_submit():
        form.populate_obj(author)
        db.session.add(author)
        db.session.commit()
        return redirect(url_for('.view', author_abbr=author.abbr))
    return render_template('author/edit.html', author=author, form=form)


@bp.route('/<int:author_id>/admin_quotes', methods=['GET', 'POST'])
@admin_permission
def admin_quotes(author_id):
    """管理文学家的名言"""
    author = Author.query.get_or_404(author_id)
    form = AuthorQuoteForm(author_id=author_id)
    if form.validate_on_submit():
        quote = AuthorQuote(**form.data)
        db.session.add(quote)
        db.session.commit()
        return redirect(url_for('.admin_quotes', author_id=author_id))
    return render_template('author/admin_quotes.html', author=author, form=form)


@bp.route('/quote/<int:quote_id>/delete')
@admin_permission
def delete_quote(quote_id):
    """删除名言"""
    quote = AuthorQuote.query.get_or_404(quote_id)
    db.session.delete(quote)
    db.session.commit()
    return redirect(url_for('.admin_quotes', author_id=quote.author_id))


@bp.route('/quote/<int:quote_id>/edit', methods=['GET', 'POST'])
@admin_permission
def edit_quote(quote_id):
    """编辑名言"""
    quote = AuthorQuote.query.get_or_404(quote_id)
    form = AuthorQuoteForm(obj=quote)
    if form.validate_on_submit():
        form.populate_obj(quote)
        db.session.add(quote)
        db.session.commit()
        return redirect(url_for('.admin_quotes', author_id=quote.author_id))
    return render_template('author/edit_quote.html', quote=quote, form=form)
########NEW FILE########
__FILENAME__ = dynasty
# coding: utf-8
from flask import render_template, redirect, url_for, Blueprint
from ..models import db, Dynasty
from ..forms import DynastyForm
from ..permissions import admin_permission

bp = Blueprint('dynasty', __name__)


@bp.route('/<dynasty_abbr>')
def view(dynasty_abbr):
    """朝代"""
    dynasties = Dynasty.query.order_by(Dynasty.start_year.asc())
    dynasty = Dynasty.query.filter(Dynasty.abbr == dynasty_abbr).first_or_404()
    authors = dynasty.authors.order_by(db.func.rand()).limit(5)
    return render_template('dynasty/dynasty.html', dynasty=dynasty, authors=authors,
                           dynasties=dynasties)


@bp.route('/add', methods=['GET', 'POST'])
@admin_permission
def add():
    """添加朝代"""
    form = DynastyForm()
    if form.validate_on_submit():
        dynasty = Dynasty(**form.data)
        db.session.add(dynasty)
        db.session.commit()
        return redirect(url_for('.view', dynasty_abbr=dynasty.abbr))
    return render_template('dynasty/add.html', form=form)


@bp.route('/<int:dynasty_id>/edit', methods=['GET', 'POST'])
@admin_permission
def edit(dynasty_id):
    """编辑朝代"""
    dynasty = Dynasty.query.get_or_404(dynasty_id)
    form = DynastyForm(obj=dynasty)
    if form.validate_on_submit():
        form.populate_obj(dynasty)
        db.session.add(dynasty)
        db.session.commit()
        return redirect(url_for('.view', dynasty_abbr=dynasty.abbr))
    return render_template('dynasty/edit.html', dynasty=dynasty, form=form)
########NEW FILE########
__FILENAME__ = site
# coding: utf-8
from flask import render_template, Blueprint
from ..models import db, Work, WorkImage, WorkReview, Author, Dynasty

bp = Blueprint('site', __name__)


@bp.route('/')
def index():
    """首页"""
    works = Work.query.order_by(db.func.rand()).limit(4)
    work_images = WorkImage.query.order_by(WorkImage.create_time.desc()).limit(18)
    work_reviews = WorkReview.query.filter(WorkReview.is_publish == True).order_by(
        WorkReview.create_time.desc()).limit(4)
    authors = Author.query.order_by(db.func.rand()).limit(5)
    dynasties = Dynasty.query.order_by(Dynasty.start_year.asc())
    return render_template('site/index.html', works=works, work_images=work_images,
                           work_reviews=work_reviews, authors=authors, dynasties=dynasties)


@bp.route('/works', methods=['POST'])
def works():
    """生成首页需要的作品json数据"""
    works = Work.query.order_by(db.func.rand()).limit(4)
    return render_template('macro/index_works.html', works=works)


@bp.route('/about')
def about():
    """关于页"""
    return render_template('site/about.html')
########NEW FILE########
__FILENAME__ = topic
# coding: utf-8
from flask import render_template, redirect, url_for, session, abort, Blueprint, g
from ..models import db, Topic, TopicComment
from ..forms import TopicForm, TopicCommentForm
from ..permissions import user_permission, TopicOwnerPermission


bp = Blueprint('topic', __name__)


@bp.route('/<int:topic_id>', methods=['POST', 'GET'])
def view(topic_id):
    """话题"""
    form = TopicCommentForm()
    topic = Topic.query.get_or_404(topic_id)
    topic.click_num += 1
    db.session.add(topic)
    db.session.commit()
    if form.validate_on_submit():
        if not user_permission.check():
            return user_permission.deny()
        comment = TopicComment(user_id=g.user.id, topic_id=topic_id, **form.data)
        db.session.add(comment)
        db.session.commit()
        return redirect(url_for('.view', topic_id=topic_id) + "#" + str(comment.id))
    return render_template('topic/topic.html', topic=topic, form=form)


@bp.route('/topics', defaults={'page': 1})
@bp.route('/topics/page/<int:page>')
def topics(page):
    """全部话题"""
    paginator = Topic.query.order_by(Topic.create_time.desc()).paginate(page, 10)
    return render_template('topic/topics.html', paginator=paginator)


@bp.route('/add', methods=['POST', 'GET'])
@user_permission
def add():
    """添加话题"""
    form = TopicForm()
    if form.validate_on_submit():
        topic = Topic(user_id=g.user.id, **form.data)
        db.session.add(topic)
        db.session.commit()
        return redirect(url_for('.view', topic_id=topic.id))
    return render_template('topic/add.html', form=form)


@bp.route('/<int:topic_id>/edit', methods=['POST', 'GET'])
@user_permission
def edit(topic_id):
    """编辑话题"""
    topic = Topic.query.get_or_404(topic_id)
    permission = TopicOwnerPermission(topic_id)
    if not permission.check():
        return permission.deny()
    form = TopicForm(obj=topic)
    if form.validate_on_submit():
        form.populate_obj(topic)
        db.session.add(topic)
        db.session.commit()
        return redirect(url_for('.view', topic_id=topic_id))
    return render_template('topic/edit.html', topic=topic, form=form)


@bp.route('/<int:topic_id>/delete')
@user_permission
def delete(topic_id):
    """删除话题"""
    topic = Topic.query.get_or_404(topic_id)
    permission = TopicOwnerPermission(topic_id)
    if not permission.check():
        return permission.deny()
    db.session.delete(topic)
    db.session.commit()
    return redirect(url_for('.topics'))
########NEW FILE########
__FILENAME__ = user
# coding: utf-8
from __future__ import division
from flask import render_template, Blueprint, g
from ..models import User, CollectWork, CollectWorkImage, Work, WorkImage, WorkReview
from ..utils import check_is_me
from ..permissions import user_permission

bp = Blueprint('user', __name__)


@bp.route('/<user_abbr>')
def view(user_abbr):
    """用户主页"""
    user = User.query.filter(User.abbr == user_abbr).first_or_404()
    query = user.work_reviews
    if not check_is_me(user.id):
        query = query.filter(WorkReview.is_publish == True)
    work_reviews = query.limit(3)
    work_reviews_num = query.count()
    topics = user.topics.limit(3)
    work_images = user.work_images.limit(16)
    return render_template('user/user.html', user=user, work_reviews=work_reviews,
                           work_reviews_num=work_reviews_num, topics=topics,
                           work_images=work_images)


@bp.route('/<user_abbr>/work_reviews', defaults={'page': 1})
@bp.route('/<user_abbr>/work_reviews/page/<int:page>')
def work_reviews(user_abbr, page):
    """用户的作品点评"""
    user = User.query.filter(User.abbr == user_abbr).first_or_404()
    work_reviews = user.work_reviews
    if not check_is_me(user.id):
        work_reviews = work_reviews.filter(WorkReview.is_publish == True)
    paginator = work_reviews.paginate(page, 10)
    return render_template('user/work_reviews.html', user=user, paginator=paginator)


@bp.route('/<user_abbr>/topics', defaults={'page': 1})
@bp.route('/<user_abbr>/topics/page/<int:page>')
def topics(user_abbr, page):
    """用户发表的话题"""
    user = User.query.filter(User.abbr == user_abbr).first_or_404()
    paginator = user.topics.paginate(page, 10)
    return render_template('user/topics.html', user=user, paginator=paginator)


@bp.route('/<user_abbr>/work_images', defaults={'page': 1})
@bp.route('/<user_abbr>/work_images/page/<int:page>')
def work_images(user_abbr, page):
    """用户上传的作品图片"""
    user = User.query.filter(User.abbr == user_abbr).first_or_404()
    paginator = user.work_images.paginate(page, 16)
    return render_template('user/work_images.html', user=user, paginator=paginator)


@bp.route('/collects')
@user_permission
def collects():
    """用户收藏页"""
    collect_works = Work.query.join(CollectWork).filter(CollectWork.user_id == g.user.id).order_by(
        CollectWork.create_time.desc()).limit(6)
    collect_work_images = WorkImage.query.join(CollectWorkImage).filter(
        CollectWorkImage.user_id == g.user.id).order_by(
        CollectWorkImage.create_time.desc()).limit(9)
    return render_template('user/collects.html', user=g.user, collect_works=collect_works,
                           collect_work_images=collect_work_images)


@bp.route('/collect_works', defaults={'page': 1})
@bp.route('/collect_works/page/<int:page>')
@user_permission
def collect_works(page):
    """用户收藏的文学作品"""
    paginator = Work.query.join(CollectWork).filter(
        CollectWork.user_id == g.user.id).order_by(
        CollectWork.create_time.desc()).paginate(page, 10)
    return render_template('user/collect_works.html', paginator=paginator)


@bp.route('/collect_work_images', defaults={'page': 1})
@bp.route('/collect_work_images/page/<int:page>')
@user_permission
def collect_work_images(page):
    """用户收藏的图片"""
    paginator = WorkImage.query.join(CollectWorkImage).filter(
        CollectWorkImage.user_id == g.user.id).order_by(
        CollectWorkImage.create_time.desc()).paginate(page, 12)
    return render_template('user/collect_work_images.html', paginator=paginator)
########NEW FILE########
__FILENAME__ = work
# coding: utf-8
from __future__ import division
from flask import render_template, request, redirect, url_for, json, Blueprint, abort, g, flash
from ..models import db, Work, WorkType, WorkTag, WorkImage, WorkReview, Tag, Dynasty, Author, \
    User, CollectWork, CollectWorkImage, WorkReviewComment
from ..utils import check_is_me
from ..permissions import user_permission, admin_permission, WorkImageOwnerPermission, \
    WorkReviewOwnerPermission
from ..forms import WorkImageForm, WorkReviewCommentForm, WorkReviewForm, WorkForm
from ..utils import random_filename, save_to_oss
from ..uploadsets import workimages

bp = Blueprint('work', __name__)


@bp.route('/<int:work_id>')
def view(work_id):
    """文学作品"""
    work = Work.query.get_or_404(work_id)
    query = work.reviews.filter(WorkReview.is_publish == True)
    reviews = query.limit(4)
    reviews_num = query.count()
    images = work.images.limit(16)
    other_works = Work.query.filter(Work.author_id == work.author_id).filter(
        Work.id != work_id).limit(5)
    collectors = User.query.join(CollectWork).join(Work).filter(Work.id == work_id).limit(4)
    return render_template('work/work.html', work=work, reviews=reviews, reviews_num=reviews_num,
                           images=images, collectors=collectors, other_works=other_works)


@bp.route('/<int:work_id>/collect', methods=['GET'])
@user_permission
def collect(work_id):
    """收藏作品"""
    collect = CollectWork(user_id=g.user.id, work_id=work_id)
    db.session.add(collect)
    db.session.commit()
    return redirect(url_for('.view', work_id=work_id))


@bp.route('/<int:work_id>/discollect')
@user_permission
def discollect(work_id):
    """取消收藏文学作品"""
    db.session.query(CollectWork).filter(CollectWork.user_id == g.user.id).filter(
        CollectWork.work_id == work_id).delete()
    db.session.commit()
    return redirect(url_for('.view', work_id=work_id))


@bp.route('/', defaults={'page': 1})
@bp.route('/page/<int:page>')
def works(page):
    """全部文学作品"""
    work_type = request.args.get('type', 'all')
    dynasty_abbr = request.args.get('dynasty', 'all')
    works = Work.query
    if work_type != 'all':
        works = works.filter(Work.type.has(WorkType.en == work_type))
    if dynasty_abbr != 'all':
        works = works.filter(Work.author.has(Author.dynasty.has(Dynasty.abbr == dynasty_abbr)))
    paginator = works.paginate(page, 10)
    work_types = WorkType.query
    dynasties = Dynasty.query.order_by(Dynasty.start_year.asc())
    return render_template('work/works.html', paginator=paginator, work_type=work_type,
                           dynasty_abbr=dynasty_abbr, work_types=work_types, dynasties=dynasties)


@bp.route('/tags')
def tags():
    """作品标签页"""
    tags = Tag.query
    return render_template('work/tags.html', tags=tags)


@bp.route('/tag/<int:tag_id>', defaults={'page': 1})
@bp.route('/tag/<int:tag_id>/page/<int:page>')
def tag(tag_id, page):
    """作品标签"""
    tag = Tag.query.get_or_404(tag_id)
    paginator = Work.query.filter(Work.tags.any(WorkTag.tag_id == tag_id)).paginate(page, 12)
    return render_template('work/tag.html', tag=tag, paginator=paginator)


@bp.route('/add', methods=['GET', 'POST'])
@admin_permission
def add():
    """添加作品"""
    form = WorkForm(author_id=request.args.get('author_id', None))
    form.author_id.choices = [(a.id, '〔%s〕%s' % (a.dynasty.name, a.name)) for a in Author.query]
    form.type_id.choices = [(t.id, t.cn) for t in WorkType.query]
    if form.validate_on_submit():
        work = Work(**form.data)
        db.session.add(work)
        db.session.commit()
        return redirect(url_for('.view', work_id=work.id))
    return render_template('work/add.html', form=form)


@bp.route('/<int:work_id>/edit', methods=['GET', 'POST'])
@admin_permission
def edit(work_id):
    """编辑作品"""
    work = Work.query.get_or_404(work_id)
    form = WorkForm(obj=work)
    form.author_id.choices = [(a.id, '〔%s〕%s' % (a.dynasty.name, a.name)) for a in Author.query]
    form.type_id.choices = [(t.id, t.cn) for t in WorkType.query]
    if form.validate_on_submit():
        form.populate_obj(work)
        db.session.add(work)
        db.session.commit()
        return redirect(url_for('.view', work_id=work_id))
    return render_template('work/edit.html', work=work, form=form)


@bp.route('/<int:work_id>/highlight')
@admin_permission
def highlight(work_id):
    """加精作品"""
    work = Work.query.get_or_404(work_id)
    work.highlight = True
    db.session.add(work)
    db.session.commit()
    return redirect(url_for('.view', work_id=work_id))


@bp.route('/<int:work_id>/shade')
@admin_permission
def shade(work_id):
    """取消加精"""
    work = Work.query.get_or_404(work_id)
    work.highlight = False
    db.session.add(work)
    db.session.commit()
    return redirect(url_for('.view', work_id=work_id))


@bp.route('/<int:work_id>/reviews', defaults={'page': 1})
@bp.route('/<int:work_id>/reviews/page/<int:page>')
def reviews(work_id, page):
    """作品点评"""
    work = Work.query.get_or_404(work_id)
    paginator = work.reviews.filter(WorkReview.is_publish == True).order_by(
        WorkReview.create_time.desc()).paginate(page, 10)
    return render_template('work/reviews.html', work=work, paginator=paginator)


@bp.route('/<int:work_id>/images', defaults={'page': 1})
@bp.route('/<int:work_id>/images/page/<int:page>')
def images(work_id, page):
    """作品图片"""
    work = Work.query.get_or_404(work_id)
    paginator = work.images.order_by(WorkImage.create_time.desc()).paginate(page, 16)
    return render_template('work/images.html', work=work, paginator=paginator)


@bp.route('/search_authors', methods=['POST'])
@admin_permission
def search_authors():
    """根据关键字返回json格式的作者信息"""
    author_name = request.form.get('author_name', '')
    authors = Author.query.filter(Author.name.like('%%%s%%' % author_name))
    dict_authors = []
    for a in authors:
        dict_authors.append({'id': a.id, 'dynasty': a.dynasty.name, 'name': a.name})
    return json.dumps(dict_authors)


@bp.route('/image/<int:work_image_id>', methods=['GET'])
def image(work_image_id):
    """作品的单个相关图片"""
    work_image = WorkImage.query.get_or_404(work_image_id)
    return render_template('work/image.html', work_image=work_image)


@bp.route('/<int:work_id>/add_image', methods=['GET', 'POST'])
@user_permission
def add_image(work_id):
    """添加作品图片"""
    work = Work.query.get_or_404(work_id)
    form = WorkImageForm()
    if form.validate_on_submit():
        # Save image to local and oss
        filename = workimages.save(request.files['image'], name=random_filename() + ".")
        try:
            save_to_oss(filename, workimages)
        except IOError:
            flash('图片上传失败，请稍后尝试')
            return redirect(url_for('.add_image', work_id=work_id))
        else:
            work_image = WorkImage(work_id=work_id, user_id=g.user.id, filename=filename)
            db.session.add(work_image)
            db.session.commit()
            return redirect(url_for('.image', work_image_id=work_image.id))
    return render_template('work/add_image.html', work=work, form=form)


@bp.route('/image/<int:work_image_id>/edit', methods=['GET', 'POST'])
@user_permission
def edit_image(work_image_id):
    """编辑作品图片"""
    work_image = WorkImage.query.get_or_404(work_image_id)
    permission = WorkImageOwnerPermission(work_image_id)
    if not permission.check():
        return permission.deny()
    form = WorkImageForm()
    if form.validate_on_submit():
        filename = workimages.save(request.files['image'], name=random_filename() + ".")
        try:
            save_to_oss(filename, workimages)
        except IOError:
            flash('图片上传失败，请稍后尝试')
            return redirect(url_for('.edit_image', work_image_id=work_image_id))
        else:
            work_image.filename = filename
            db.session.add(work_image)
            db.session.commit()
            return redirect(url_for('.image', work_image_id=work_image_id))
    return render_template('work/edit_image.html', work_image=work_image, form=form)


@bp.route('/image/<int:work_image_id>/delete', methods=['GET'])
@user_permission
def delete_image(work_image_id):
    """删除作品图片"""
    work_image = WorkImage.query.get_or_404(work_image_id)
    permission = WorkImageOwnerPermission(work_image_id)
    if not permission.check():
        return permission.deny()
    db.session.delete(work_image)
    db.session.commit()
    return redirect(url_for('.view', work_id=work_image.work_id))


@bp.route('/image/<int:work_image_id>/collect', methods=['GET'])
@user_permission
def collect_image(work_image_id):
    """收藏作品图片"""
    collect = CollectWorkImage(user_id=g.user.id, work_image_id=work_image_id)
    db.session.add(collect)
    db.session.commit()
    return redirect(url_for('.image', work_image_id=work_image_id))


@bp.route('/image/<int:work_image_id>/discollect')
@user_permission
def discollect_image(work_image_id):
    """取消收藏作品图片"""
    db.session.query(CollectWorkImage).filter(CollectWorkImage.user_id == g.user.id).filter(
        CollectWorkImage.work_image_id == work_image_id).delete()
    db.session.commit()
    return redirect(url_for('.image', work_image_id=work_image_id))


@bp.route('/all_images', defaults={'page': 1})
@bp.route('/all_images/page/<int:page>')
def all_images(page):
    """所有作品图片"""
    paginator = WorkImage.query.paginate(page, 12)
    return render_template('work/all_images.html', paginator=paginator)


@bp.route('/review/<int:review_id>', methods=['GET', 'POST'])
def review(review_id):
    """作品点评"""
    form = WorkReviewCommentForm()
    review = WorkReview.query.get_or_404(review_id)
    # others cannot see draft
    if not review.is_publish and not check_is_me(review.user_id):
        abort(404)
    review.click_num += 1
    db.session.add(review)
    db.session.commit()
    if form.validate_on_submit():
        comment = WorkReviewComment(review_id=review_id, user_id=g.user.id, **form.data)
        db.session.add(comment)
        db.session.commit()
        return redirect(url_for('.review', review_id=review_id) + "#" + str(comment.id))
    return render_template('work/review.html', review=review, form=form)


@bp.route('/all_reviews', defaults={'page': 1})
@bp.route('/all_reviews/page/<int:page>')
def all_reviews(page):
    """最新作品点评"""
    paginator = WorkReview.query.filter(WorkReview.is_publish == True).order_by(
        WorkReview.create_time.desc()).paginate(page, 10)
    stmt = db.session.query(WorkReview.user_id, db.func.count(WorkReview.user_id).label(
        'reviews_num')).group_by(WorkReview.user_id).subquery()
    hot_reviewers = db.session.query(User).join(stmt, User.id == stmt.c.user_id).order_by(
        stmt.c.reviews_num)
    return render_template('work/all_reviews.html', paginator=paginator,
                           hot_reviewers=hot_reviewers)


@bp.route('/<int:work_id>/add_review', methods=['GET', 'POST'])
@user_permission
def add_review(work_id):
    """添加作品点评"""
    work = Work.query.get_or_404(work_id)
    form = WorkReviewForm()
    if form.validate_on_submit():
        is_publish = True if 'publish' in request.form else False
        review = WorkReview(user_id=g.user.id, work_id=work_id, is_publish=is_publish,
                            **form.data)
        db.session.add(review)
        db.session.commit()
        return redirect(url_for('.review', review_id=review.id))
    return render_template('work/add_review.html', work=work, form=form)


@bp.route('/review/<int:review_id>/edit', methods=['GET', 'POST'])
@user_permission
def edit_review(review_id):
    """编辑作品点评"""
    review = WorkReview.query.get_or_404(review_id)
    permission = WorkReviewOwnerPermission(review_id)
    if not permission.check():
        return permission.deny()
    form = WorkReviewForm(obj=review)
    if form.validate_on_submit():
        form.populate_obj(review)
        review.is_publish = True if 'publish' in request.form else False
        db.session.add(review)
        db.session.commit()
        return redirect(url_for('.review', review_id=review_id))
    return render_template('work/edit_review.html', review=review, form=form)


@bp.route('/review/<int:review_id>/delete')
@user_permission
def delete_review(review_id):
    """删除作品点评"""
    review = WorkReview.query.get_or_404(review_id)
    permission = WorkReviewOwnerPermission(review_id)
    if not permission.check():
        return permission.deny()
    db.session.delete(review)
    db.session.commit()
    return redirect(url_for('.view', work_id=review.work_id))
########NEW FILE########
__FILENAME__ = filters
# coding: utf-8
import datetime
import re
import markdown2
from werkzeug.utils import escape
from flask import g
from models import CollectWork, CollectWorkImage


def timesince(value):
    """Friendly time gap"""
    now = datetime.datetime.now()
    delta = now - value
    if delta.days > 365:
        return '%d年前' % (delta.days / 365)
    if delta.days > 30:
        return '%d个月前' % (delta.days / 30)
    if delta.days > 0:
        return '%d天前' % delta.days
    if delta.seconds > 3600:
        return '%d小时前' % (delta.seconds / 3600)
    if delta.seconds > 60:
        return '%d分钟前' % (delta.seconds / 60)
    return '刚刚'


def clean_work(content):
    """截取作品内容时，去除其中一些不需要的元素"""
    c = re.sub(r'<([^<]+)>', '', content)
    c = c.replace('%', '')
    c = c.replace('（一）', "")
    c = c.replace('(一)', "")
    return c


def markdown_work(content):
    """将作品内容格式化为HTML标签
    Add comment -> Split ci -> Generate paragraph
    """
    c = re.sub(r'<([^<^b]+)>', r"<sup title='\1'></sup>", content)
    c = c.replace('%', "&nbsp;&nbsp;&nbsp;&nbsp;")
    c = markdown2.markdown(c)
    return c


def format_year(year):
    """将数字表示的年转换成中文"""
    return str(year).replace('-', '前') + "年"


def format_text(text):
    """将文本进行HTML转义，然后将换行符替换为div"""
    return escape(text).replace('\n', "<div class='text-gap'></div>")


def is_work_collected(work):
    """判断当前用户是否收藏此作品"""
    return g.user and CollectWork.query.filter(CollectWork.work_id == work.id).filter(
        CollectWork.user_id == g.user.id).count() > 0


def is_work_image_collected(work_image):
    """判断当前用户是否收藏此作品图片"""
    return g.user and CollectWorkImage.query.filter(CollectWorkImage.user_id == g.user.id).filter(
        CollectWorkImage.work_image_id == work_image.id).count() > 0
########NEW FILE########
__FILENAME__ = account
# coding: utf-8
from flask_wtf import Form
from wtforms import TextField, TextAreaField
from wtforms.validators import DataRequired, Email
from ..models import User


class SignupForm(Form):
    """Form for send email"""
    email = TextField('邮箱', [DataRequired(message="邮箱不能为空"), Email(message="无效的邮箱")],
                      description='你常用的邮箱')

    def validate_email(self, field):
        if User.query.filter(User.email == field.data).count() > 0:
            raise ValueError('邮箱已被使用')


class SettingsForm(Form):
    """Form for personal settings"""
    signature = TextAreaField('签名', [])
########NEW FILE########
__FILENAME__ = admin
# coding: utf-8
from flask_wtf import Form
from wtforms import TextField, TextAreaField, SelectField, IntegerField, HiddenField
from wtforms.validators import DataRequired


class WorkForm(Form):
    """Form for add & edit work"""
    title = TextField('标题', [DataRequired('标题不能为空')])
    type_id = SelectField('类别', [DataRequired("类别不能为空")], coerce=int)
    layout = SelectField('布局', [DataRequired('布局不能为空')],
                         choices=[('center', '居中'), ('indent', '段落缩进')])
    author_id = SelectField('作者', [DataRequired('作者不能为空')], coerce=int)
    foreword = TextAreaField('序')
    intro = TextAreaField('题解')
    content = TextAreaField('内容', [DataRequired('内容不能为空')])


class AuthorForm(Form):
    """Form for add & edit author"""
    name = TextField('姓名', [DataRequired('姓名不能为空')])
    abbr = TextField('拼音', [DataRequired('拼音不能为空')])
    dynasty_id = SelectField('朝代', [DataRequired('朝代不能为空')], coerce=int)
    birth_year = TextField('生年', [DataRequired('生年不能为空')])
    death_year = TextField('卒年')
    intro = TextAreaField('简介', [DataRequired('简介不能为空')])


class AuthorQuoteForm(Form):
    """Form for add & edit author quote"""
    quote = TextField('引语', [DataRequired('引语不能为空')])
    work_id = IntegerField('出处', [DataRequired('出处不能为空')])
    author_id = HiddenField('作者', [DataRequired('作者不能为空')])


class DynastyForm(Form):
    """Form for add & edit dynasty"""
    name = TextField('朝代', [DataRequired('朝代不能为空')])
    abbr = TextField('拼音', [DataRequired('拼音不能为空')])
    intro = TextAreaField('简介', [DataRequired('简介不能为空')])
    start_year = IntegerField('起始年', [DataRequired('起始年不能为空')])
    end_year = IntegerField('结束年', [DataRequired('结束年不能为空')])
########NEW FILE########
__FILENAME__ = forum
# coding: utf-8
from flask_wtf import Form
from wtforms import TextField, TextAreaField, HiddenField
from wtforms.validators import DataRequired, Email
from flask_wtf.file import FileField, FileAllowed, FileRequired


class TopicForm(Form):
    """Form for add and edit topic"""
    title = TextField('标题', [DataRequired(message="标题不能为空")])
    content = TextAreaField('内容', [DataRequired(message="内容不能为空")])


class TopicCommentForm(Form):
    """Form for add comment to topic"""
    content = TextAreaField('回复', [DataRequired(message="回复不能为空")])
########NEW FILE########
__FILENAME__ = work
# coding: utf-8
from flask_wtf import Form
from wtforms import TextField, TextAreaField
from wtforms.validators import DataRequired
from flask_wtf.file import FileField, FileAllowed, FileRequired
from ..uploadsets import workimages


class WorkReviewForm(Form):
    """Form for add and edit work review"""
    title = TextField('标题', [DataRequired("标题不能为空")])
    content = TextAreaField('内容', [DataRequired("内容不能为空")])


class WorkReviewCommentForm(Form):
    """Form for add comment to work review"""
    content = TextAreaField('回复', [DataRequired("回复不能为空")])


class WorkImageForm(Form):
    """Form for add and edit work image"""
    image = FileField('作品', [FileRequired('作品图片不能为空'),
                             FileAllowed(workimages, '不支持的图片格式')])
########NEW FILE########
__FILENAME__ = mails
# coding: utf-8
import hashlib
from flask import render_template, url_for
from flask_mail import Message, Mail
from . import config

mail = Mail()


def signup_mail(user):
    """Send signup email"""
    token = hashlib.sha1(user.name).hexdigest()
    url = config.SITE_DOMAIN + url_for('.activate', user_id=user.id, token=token)
    msg = Message("欢迎来到西窗烛", recipients=[user.email])
    msg.html = render_template('email/signup.html', url=url)
    mail.send(msg)
########NEW FILE########
__FILENAME__ = author
# coding: utf-8
from ._base import db


class Author(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)
    abbr = db.Column(db.String(50), unique=True)
    intro = db.Column(db.Text())
    birth_year = db.Column(db.String(20))
    death_year = db.Column(db.String(20))

    dynasty_id = db.Column(db.Integer, db.ForeignKey('dynasty.id'))
    dynasty = db.relationship('Dynasty', backref=db.backref('authors', lazy='dynamic',
                                                            order_by="asc(Author.birth_year)"))

    def __repr__(self):
        return '<Author %s>' % self.name

    @property
    def random_quote(self):
        """Get a random quote of the author
        为了防止每次访问此属性时都得到不同的结果，
        在第一次查询后将结果缓存起来，以便后续使用
        """
        if not hasattr(self, '_random_quote'):
            self._random_quote = AuthorQuote.query.filter(
                AuthorQuote.author_id == self.id).order_by(db.func.rand()).first()
        return self._random_quote


class AuthorQuote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quote = db.Column(db.Text())

    author_id = db.Column(db.Integer, db.ForeignKey('author.id'))
    author = db.relationship('Author', backref=db.backref('quotes', lazy='dynamic'))

    work_id = db.Column(db.Integer, db.ForeignKey('work.id'))
    work = db.relationship('Work', backref=db.backref('quotes', lazy='dynamic'))

    def __repr__(self):
        return '<AuthorQuote %s>' % self.quote
########NEW FILE########
__FILENAME__ = collect
# coding: utf-8
import datetime
from ._base import db


class CollectWork(db.Model):
    create_time = db.Column(db.DateTime, default=datetime.datetime.now)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    user = db.relationship('User', backref=db.backref('collect_works', lazy='dynamic'))

    work_id = db.Column(db.Integer, db.ForeignKey('work.id'), primary_key=True)
    work = db.relationship('Work',
                           backref=db.backref('collectors', lazy='dynamic', cascade='delete'))

    def __repr__(self):
        return '<User %d collect Work %d>' % (self.user_id, self.work_id)


class CollectWorkImage(db.Model):
    create_time = db.Column(db.DateTime, default=datetime.datetime.now)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    user = db.relationship('User', backref=db.backref('collect_work_images', lazy='dynamic'))

    work_image_id = db.Column(db.Integer, db.ForeignKey('work_image.id'), primary_key=True)
    work_image = db.relationship('WorkImage',
                                 backref=db.backref('collectors', lazy='dynamic', cascade='delete'))

    def __repr__(self):
        return '<User %d collect WorkImage %d>' % (self.user_id, self.work_image_id)
########NEW FILE########
__FILENAME__ = dynasty
# coding: utf-8
from ._base import db


class Dynasty(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    abbr = db.Column(db.String(50), unique=True)
    intro = db.Column(db.Text())
    start_year = db.Column(db.Integer)
    end_year = db.Column(db.Integer)

    def __repr__(self):
        return '<Dynasty %s>' % self.name
########NEW FILE########
__FILENAME__ = topic
# coding: utf-8
import datetime
from ._base import db


class Topic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    content = db.Column(db.Text)
    click_num = db.Column(db.Integer, default=0)
    create_time = db.Column(db.DateTime, default=datetime.datetime.now)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref=db.backref('topics', lazy='dynamic',
                                                      order_by="desc(Topic.create_time)"))

    def __repr__(self):
        return '<Topic %s>' % self.title


class TopicComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text)
    create_time = db.Column(db.DateTime, default=datetime.datetime.now)
    
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'), primary_key=True)
    topic = db.relationship('Topic', backref=db.backref('comments', lazy='dynamic',
                                                        order_by="asc(TopicComment.create_time)"))

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    user = db.relationship('User', backref=db.backref('topic_comments', lazy='dynamic',
                                                      order_by="desc(TopicComment.create_time)"))

    def __repr__(self):
        return '<TopicComment %s>' % self.content
########NEW FILE########
__FILENAME__ = user
# coding: utf-8
import datetime
from ._base import db
from ..roles import NewUserRole


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)
    role = db.Column(db.Integer, default=NewUserRole)
    abbr = db.Column(db.String(50))
    email = db.Column(db.String(50))
    avatar = db.Column(db.String(200))
    signature = db.Column(db.Text)
    check_inform_time = db.Column(db.DateTime, default=datetime.datetime.now)
    create_time = db.Column(db.DateTime, default=datetime.datetime.now)

    def __repr__(self):
        return '<User %s>' % self.name
########NEW FILE########
__FILENAME__ = work
# coding: utf-8
import datetime
from flask import current_app
from ._base import db


class Work(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(50))
    foreword = db.Column(db.Text())
    content = db.Column(db.Text())
    intro = db.Column(db.Text())
    layout = db.Column(db.String(10))
    highlight = db.Column(db.Boolean, default=False)
    create_time = db.Column(db.DateTime)

    author_id = db.Column(db.Integer, db.ForeignKey('author.id'))
    author = db.relationship('Author', backref=db.backref('works', lazy='dynamic'))

    type_id = db.Column(db.Integer, db.ForeignKey('work_type.id'))
    type = db.relationship('WorkType', backref=db.backref('works', lazy='dynamic'))

    def __repr__(self):
        return '<Work %s>' % self.title


class WorkType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    en = db.Column(db.String(50))
    cn = db.Column(db.String(50))

    def __repr__(self):
        return '<WorkType %s>' % self.cn


class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(50))
    desc = db.Column(db.String(200))
    icon = db.Column(db.String(200))


class WorkTag(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    work_id = db.Column(db.Integer, db.ForeignKey('work.id'), primary_key=True)
    work = db.relationship('Work', backref=db.backref('tags'))

    tag_id = db.Column(db.Integer, db.ForeignKey('tag.id'), primary_key=True)
    tag = db.relationship('Tag', backref=db.backref('works'))

    def __repr__(self):
        return '<WorkTag %s>' % self.tag


class WorkImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200))
    create_time = db.Column(db.DateTime, default=datetime.datetime.now)

    work_id = db.Column(db.Integer, db.ForeignKey('work.id'))
    work = db.relationship('Work', backref=db.backref('images', lazy='dynamic'))

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref=db.backref('work_images', lazy='dynamic',
                                                      order_by="desc(WorkImage.create_time)"))

    @property
    def url(self):
        return current_app.config['OSS_URL'] + self.filename

    def __repr__(self):
        return '<WorkImage %s>' % self.filename


class WorkReview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    content = db.Column(db.Text)
    is_publish = db.Column(db.Boolean)
    click_num = db.Column(db.Integer, default=0)
    create_time = db.Column(db.DateTime, default=datetime.datetime.now)

    work_id = db.Column(db.Integer, db.ForeignKey('work.id'))
    work = db.relationship('Work', backref=db.backref('reviews', lazy='dynamic',
                                                      order_by="desc(WorkReview.create_time)"))

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref=db.backref('work_reviews', lazy='dynamic',
                                                      order_by="desc(WorkReview.create_time)"))

    def __repr__(self):
        return '<WorkReview %s>' % self.title


class WorkReviewComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text)
    create_time = db.Column(db.DateTime, default=datetime.datetime.now)

    review_id = db.Column(db.Integer, db.ForeignKey('work_review.id'), primary_key=True)
    review = db.relationship('WorkReview',
                             backref=db.backref('comments', lazy='dynamic',
                                                order_by="desc(WorkReviewComment.create_time)"))

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    user = db.relationship('User',
                           backref=db.backref('work_review_comments', lazy='dynamic',
                                              order_by="desc(WorkReviewComment.create_time)"))

    def __repr__(self):
        return '<WorkReviewComment %s>' % self.content
########NEW FILE########
__FILENAME__ = _base
from flask.ext.sqlalchemy import SQLAlchemy

db = SQLAlchemy()
########NEW FILE########
__FILENAME__ = permissions
# coding: utf-8
from flask import request, g
from functools import wraps
from flask import abort, redirect, url_for, flash
from .models import Topic, WorkReview, WorkImage
import roles


def require_visitor(func):
    """Check if no user login"""
    @wraps(func)
    def decorator(*args, **kwargs):
        if g.user_role != roles.VisitorRole:
            return redirect(url_for('site.index'))
        return func(*args, **kwargs)
    return decorator


class Permission(object):
    def __init__(self, role, extra=True, super_extra=True):
        self.role = role
        self.extra = extra
        self.super_extra = super_extra

    def __call__(self, func):
        @wraps(func)
        def decorator(*args, **kwargs):
            if not self.check():
                return self.deny()
            return func(*args, **kwargs)
        return decorator

    def check(self):
        """判断是否满足权限条件"""
        if g.user_role < self.role:
            return False
        elif g.user_role == self.role:
            return self.extra
        return self.super_extra

    def deny(self, next_url=""):
        """针对不同的role进行不同的处理"""
        if g.user_role == roles.VisitorRole:
            flash('此操作需要登录账户')
            return redirect(url_for('site.index'))
        elif g.user_role == roles.NewUserRole:
            flash('请登录邮箱激活账户')
            return redirect(request.referrer or url_for('site.index'))
        abort(403)


new_user_permission = Permission(roles.NewUserRole)
user_permission = Permission(roles.UserRole)
admin_permission = Permission(roles.AdminRole)
super_admin_permission = Permission(roles.SuperAdminRole)


class TopicOwnerPermission(Permission):
    def __init__(self, topic_id):
        own = g.user and Topic.query.filter(Topic.id == topic_id).filter(
            Topic.user_id == g.user.id).count() > 0
        Permission.__init__(self, roles.UserRole, own)


class WorkReviewOwnerPermission(Permission):
    def __init__(self, review_id):
        own = g.user and WorkReview.query.filter(WorkReview.id == review_id).filter(
            WorkReview.user_id == g.user.id).count() > 0
        Permission.__init__(self, roles.UserRole, own)


class WorkImageOwnerPermission(Permission):
    def __init__(self, image_id):
        own = g.user and WorkImage.query.filter(WorkImage.id == image_id).filter(
            WorkImage.user_id == g.user.id).count() > 0
        Permission.__init__(self, roles.UserRole, own)
########NEW FILE########
__FILENAME__ = roles
# Roles
SuperAdminRole = 5
AdminRole = 4
UserRole = 3
NewUserRole = 2
BanUserRole = 1
VisitorRole = 0
########NEW FILE########
__FILENAME__ = uploadsets
# coding: utf-8
from flask.ext.uploads import UploadSet, IMAGES

# UploadSets
workimages = UploadSet('workimages', IMAGES)
########NEW FILE########
__FILENAME__ = utils
# coding: utf-8
import datetime
import uuid
from oss.oss_api import OssAPI
from flask import session, g
from . import config, roles
from .models import User


# count the time diff by timedelta, return a user-friendly format
def time_diff(time):
    """Friendly time gap"""
    now = datetime.datetime.now()
    delta = now - time
    if delta.days > 365:
        return '%d年前' % (delta.days / 365)
    if delta.days > 30:
        return '%d个月前' % (delta.days / 30)
    if delta.days > 0:
        return '%d天前' % delta.days
    if delta.seconds > 3600:
        return '%d小时前' % (delta.seconds / 3600)
    if delta.seconds > 60:
        return '%d分钟前' % (delta.seconds / 60)
    return '刚刚'


def check_is_me(user_id):
    """判断此user是否为当前在线的user"""
    return g.user and g.user.id == user_id


def signin_user(user, permenent):
    """Sign in user"""
    session.permanent = permenent
    session['user_id'] = user.id


def signout_user():
    """Sign out user"""
    session.pop('user_id', None)


def get_current_user():
    """获取当前user，同时进行session有效性的检测"""
    if not 'user_id' in session:
        return None
    user = User.query.filter(User.id == session['user_id']).first()
    if not user:
        signout_user()
        return None
    return user


def get_current_user_role():
    """获取当前用户的角色，若无有效用户，则返回VisitorRole"""
    if not g.user:
        return roles.VisitorRole
    return g.user.role


def random_filename():
    """生成伪随机文件名"""
    return str(uuid.uuid4())


def save_to_oss(filename, uploadset):
    """将文件保存到OSS上，若保存失败，则抛出IO异常"""
    oss = OssAPI(config.OSS_HOST, config.OSS_KEY, config.OSS_SECRET)
    res = oss.put_object_from_file("xichuangzhu", filename, uploadset.config.destination + '/' + filename)
    status = res.status
    if status != 200:
        raise IOError

########NEW FILE########
