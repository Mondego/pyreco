__FILENAME__ = admin
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#

from werkzeug.contrib.securecookie  import SecureCookie

from catonmat.views.utils           import display_template
from catonmat.config                import config

import hashlib

# ----------------------------------------------------------------------------

REQUIRE_IP   = 1
REQUIRE_CRED = 2

def require_admin(req_what=[REQUIRE_IP, REQUIRE_CRED]):
    def _require_admin(f):        
        def __require_admin(request, *args, **kw):
            if not req_what:
                raise ValueError, "Forgot to specify req_what in %s" % f.__name__
            if REQUIRE_IP in req_what:
                if not allowed_ip(request):
                    return display_template('admin/access_denied',
                             message='your ip %s was not in the allowed ip list' % str(request.remote_addr))
            if REQUIRE_CRED in req_what:
                if not admin_cred_match(request):
                    return display_template('admin/access_denied',
                             message='admin credentials don\'t match')
            return f(request, *args, **kw)
        return __require_admin
    return _require_admin

def unserialize_secure_cookie(request):
    if not request.cookies.get('admin'):
        return dict()
    return SecureCookie.unserialize(request.cookies.get('admin'), secret_key=config.secure_key)

def admin_cred_match(request):
    d = unserialize_secure_cookie(request)
    return admin_cred_match_prim(d.get('admin_user'), d.get('admin_hash'))

def admin_cred_match_prim(user, hash):
    return user == get_admin_user() and hash == get_admin_hash() 

def get_admin_user():
    return open(config.admin_hash_file).readline().strip().split(':')[0]

def get_admin_hash():
    return open(config.admin_hash_file).readline().strip().split(':')[1]

def allowed_ip(request):
    return request.remote_addr in get_allowed_ips()

def get_allowed_ips():
    return [l.strip() for l in open(config.ips_file, 'r')]

def logged_in(request):
    return admin_cred_match(request)

def hash_password(password):
    md5 = hashlib.md5()
    md5.update(password)
    md5.update(config.secure_key)
    return md5.hexdigest()

def mk_secure_cookie(Dict):
    return SecureCookie(Dict, secret_key=config.secure_key)


########NEW FILE########
__FILENAME__ = application
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#

from werkzeug             import Request, redirect
from werkzeug.exceptions  import HTTPException, NotFound
from werkzeug             import SharedDataMiddleware

from catonmat.database    import session
from catonmat.views.utils import get_view
from catonmat.errorlog    import log_404, log_exception
from catonmat.urls        import predefined_urls, find_url_map, find_redirect
from catonmat.config      import config

from os import path

# ----------------------------------------------------------------------------

def handle_request(view, *values, **kw_values):
    handler = get_view(view)
    return handler(*values, **kw_values)


@Request.application
def application(request):
    try:
        adapter = predefined_urls.bind_to_environ(request.environ)
        endpoint, values = adapter.match()
        return handle_request(endpoint, request, **values)
    except NotFound:
        redir = find_redirect(request.path)
        if redir:
            return redirect(redir.new_path, code=redir.code)

        #print "Request path: " + request.path
        if request.path[-1] != '/':
            return redirect(request.path + '/', code=301)

        url_map = find_url_map(request.path)
        if url_map:
            return handle_request('pages.main', request, url_map)

        # Log this request in the 404 log and display not found page
        log_404(request)
        return handle_request('not_found.main', request)
    except:
        log_exception(request)
        return handle_request('exception.main', request)
    finally:
        session.remove()

application = SharedDataMiddleware(application,
    { '/static': path.join(path.dirname(__file__), 'static') }
)

if config.use_profiler:
    from repoze.profile.profiler import AccumulatingProfileMiddleware
    application = AccumulatingProfileMiddleware(
                    application,
                    log_filename='/tmp/repoze-catonmat.txt',
                    cachegrind_filename='/tmp/repoze-catonmat-cachegrind',
                    discard_first_request=True,
                    flush_at_shutdown=True,
                    path='/__profile__'
                  )


########NEW FILE########
__FILENAME__ = cache
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#

from catonmat.config            import config

import memcache

# ----------------------------------------------------------------------------

mc = memcache.Client(['127.0.0.1:11211'])


def cache(key, duration=0):
    def _cache(function):
        def __cache(*args, **kw):
            if not config.use_cache:
                return function(*args, **kw)

            value = cache_get(key)
            if value is not None:
                return value

            value = function(*args, **kw)
            cache_set(key, value, duration)
            return value
        return __cache
    return _cache


def cache_get(key):
    return mc.get(str(key))


def cache_set(key, value, duration=0):
    mc.set(str(key), value, duration)


def cache_del(key):
    mc.delete(str(key))


class MemcachedNone(object):
    pass

def from_cache_or_compute(computef, key, duration, *args, **kw):
    if not config.use_cache:
        return computef(*args, **kw)

    cached_data = cache_get(key)
    if isinstance(cached_data, MemcachedNone):
        return None
    if cached_data is not None:
        return cached_data
    
    # if data is not cached, compute, cache and return it
    cached_data = computef(*args, **kw)
    if cached_data is None:
        cache_set(key, MemcachedNone(), duration)
    else:
        cache_set(key, cached_data, duration)
    return cached_data


########NEW FILE########
__FILENAME__ = comments
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#

from werkzeug               import redirect, Response
from werkzeug.exceptions    import BadRequest

from catonmat.config        import config
from catonmat.cache         import cache_del
from catonmat.models        import Page, Comment, Visitor
from catonmat.database      import session
from catonmat.views.utils   import get_template

from StringIO               import StringIO
from urlparse               import urlparse
from collections            import defaultdict

import re
import simplejson as json

from comment_spamlist import spamlist_names, spamlist_urls, spamlist_emails, spamlist_comments

# ----------------------------------------------------------------------------

email_rx   = re.compile(r'^.+@.+\..+$')
twitter_rx = re.compile(r'^[a-zA-Z0-9_]+$')
lynx_re  = re.compile(r'Lynx|Links', re.I)

def lynx_browser(request):
    browser = request.headers.get('User-Agent')
    if browser:
        if lynx_re.match(browser):
            return True
    return False


class CommentError(Exception):
    pass


def validate_comment(request, preview=False):
    def validate_name(name):
        if not name:
            raise CommentError, "You forgot to specify your name!"
        if len(name) > 64:
            raise CommentError, "Your name is too long. Maximum length is 64 characters."

    def validate_email(email):
        if email:
            if len(email) > 128:
                raise CommentError, "Your e-mail is too long. Maximum length is 128 characters."
            if not email_rx.match(email):
                raise CommentError, "Sorry, your e-mail address is not valid!"

    def validate_comment_txt(comment):
        if not comment:
            raise CommentError, "You left the comment empty!"

    def validate_twitter(twitter):
        if twitter:
            if len(twitter) > 128:
                raise CommentError, "Your Twitter name is too long. Maximum length is 128 characters."
            if not twitter_rx.match(twitter):
                raise CommentError, "Your Twitter name is incorrect! It can consist only of letters, numbers and the underscore symbol."

    def validate_website(website):
        if website:
            if len(website) > 256:
                raise CommentError, "Your website address is too long. Maximum length is 256 characters."
            if '.' not in website:
                raise CommentError, "Your website address is invalid!"

            url = urlparse(website)
            if url.scheme:
                if url.scheme not in ('http', 'https', 'ftp'):
                    raise CommentError, "The only allowed website schemes are http://, https:// and ftp://"

    def validate_page_id(page_id):
        number_of_pages = session.query(Page).filter_by(page_id=page_id).count()
        if number_of_pages != 1:
            raise CommentError, "Something went wrong, the page you were commenting on was not found..."

    def validate_parent_id(parent_id):
        if parent_id:
            comments = session.query(Comment).filter_by(comment_id=parent_id).count()
            if comments != 1:
                raise CommentError, "Something went wrong, the comment you were responding to was not found..."

    def validate_captcha(name, captcha):
        if name[0] != captcha:
            raise CommentError, 'Please type "' + name[0] + '" in the box below'

    def validate_spam_comment(name, email, url, comment):
        msg = """My anti-spam system says your comment looks spammy. I can't post it. If you're a real person and your comment is real, can you please email it to me at <a href="mailto:peter@catonmat.net">peter@catonmat.net</a>? I'll post your comment then and tune my anti-spam system not to match comments like these in the future. Thanks!"""

        for r in spamlist_names:
            if r.search(name):
                raise CommentError, msg

        for r in spamlist_emails:
            if r.search(email):
                raise CommentError, msg

        for r in spamlist_urls:
            if r.search(url):
                raise CommentError, msg

        for r in spamlist_comments:
            if r.search(comment):
                raise CommentError, msg

        msg2 = "I am sorry, please don't end your comment with a link. It's a common spam pattern I am seeing on my blog. Please add at least a dot at the end of the comment to avoid it being matched by this spam filter. Thanks!"

        if re.search("</a>$", comment):
            raise CommentError, msg2

        if re.search("</a></strong>$", comment):
            raise CommentError, msg2

    validate_page_id(request.form['page_id'])
    validate_parent_id(request.form['parent_id'])
    validate_name(request.form['name'].strip())
    validate_email(request.form['email'].strip())
    validate_twitter(request.form['twitter'].replace('@', '').strip())
    validate_website(request.form['website'].strip())
    validate_comment_txt(request.form['comment'].strip())
    validate_spam_comment(request.form['name'].strip(), request.form['email'].strip(), request.form['website'].strip(), request.form['comment'].strip())

    if not lynx_browser(request) and not preview:
        validate_captcha(request.form['name'].strip(), request.form['commentc'].strip())


def json_response(**data):
    return json.dumps(data)


# TODO: @json_response
def preview_comment(request):
    if request.method == "POST":
        try:
            validate_comment(request, preview=True)
        except CommentError, e:
            return Response(json_response(status='error', message=e.message)
                 ,   mimetype='application/json')

        return Response(
                json_response(status='success',
                    comment=get_template('comment').
                            get_def('individual_comment').
                            render(comment=new_comment(request),
                    preview=True))
        , mimetype='application/json')


def add_comment(request):
    if request.method == "POST":
        try:
            validate_comment(request)
        except CommentError, e:
            return Response ( json_response(status='error', message=e.message)
                    , mimetype='application/json')

        comment = new_comment(request)
        comment.save()

        invalidate_page_cache(request.form['page_id'])

        return Response(
                json_response(status='success',
                    comment=get_template('comment').
                            get_def('individual_comment').
                            render(comment=comment))
        , mimetype='application/json')


def invalidate_page_cache(page_id):
    if config.use_cache:
        page = session.query(Page).filter_by(page_id=page_id).first()
        cache_del('individual_page_%s' % page.request_path)


def get_comment(id):
    return session.query(Comment).filter_by(comment_id=id).first()


def new_comment(request):
    return Comment(
        page_id   = request.form['page_id'],
        parent_id = request.form['parent_id'],
        name      = request.form['name']   .strip(),
        comment   = request.form['comment'].strip(),
        email     = request.form['email']  .strip(),
        twitter   = request.form['twitter'].replace('@', '').strip(),
        website   = request.form['website'].strip(),
        visitor   = Visitor(request)
    )


def thread(comments):
    """
    Given a list of comments, threads them (creates a data structure
    that can be recursively iterated to output them in a threaded form).

    For example, for data:     it creates this tree:
    comment_id parent_id       root
    5          NULL            `-5
    6          5               | `-6
    7          5               | |`-8
    8          6               | `-7
    9          NULL            `-9 
    10         9               | `-10
    11         9               | |`-12
    12         10              | | `-13
    13         12              | `-11
    14         NULL            `-14

    and that tree is represented as the following data structure:
    {
      'root': [5, 9, 14],
      '5':    [6, 7],
      '6':    [8],
      '7':    [],        # actually keys with empty values are not present, i just added
      '8':    [],        # them here so that i can understand it better myself
      '9':    [10, 11],
      '10':   [12],
      '11':   [],
      '12':   [13],
      '13':   [],
      '14':   []
    }

    This data structure is actually the adjacency list representation of a graph.

    """
    
    ret = {'root': []}
    for comment in comments:
        if not comment.parent_id:
            ret['root'].append(comment)
        else:
            if comment.parent_id not in ret:
                ret[comment.parent_id] = []
            ret[comment.parent_id].append(comment)
    return ret


def linear(comments):
    """
    Given a list of comments, returns them in linear order (to display them as
    a simple list and not as a threaded tree.
    """

    return {'root': comments}


########NEW FILE########
__FILENAME__ = comment_spamlist
import re

r = re.compile

spamlist_names = [
    r('classifieds', re.I),
    r('wireless alarm', re.I),
    r('alarm kit', re.I),
    r('lasik ', re.I),
    r('jordan lls', re.I),
    r('touchscreen ', re.I),
    r('credit card', re.I),
    r('austin home', re.I),
    r('noah theme', re.I),
    r('cash loan', re.I),
    r('cash.*loan', re.I),
    r('advance loan', re.I),
    r('payday loan', re.I),
    r('silver price', re.I),
    r('ed hardy', re.I),
    r('florida.*fishing', re.I),
    r('fishing.*florida', re.I),
    r('real estate', re.I),
    r('free dating', re.I),
    r('dating site', re.I),
    r('dating website', re.I),
    r('countertop', re.I),
    r('solar panel', re.I),
    r('dentists', re.I),
    r('.+dentist', re.I),
    r('dental clinic', re.I),
    r('clinical ', re.I),
    r('locksmith in', re.I),
    r('buy.*online', re.I),
    r('coupons', re.I),
    r('discount.*coupon', re.I),
    r('self diagnosis', re.I),
    r('handicapped vans', re.I),
    r('hotel finder', re.I),
    r('cheap hotel', re.I),
    r('cheap business', re.I),
    r('lawsuit', re.I),
    r('horoscope', re.I),
    r('garmin.*forerunner', re.I),
    r('replica purses', re.I),
    r('cheap.*insurance', re.I),
    r('mobile.*review', re.I),
    r('.+app?artment', re.I),
    r('refurbished.+', re.I),
    r('water damage', re.I),
    r('fire damage', re.I),
    r('.+ seo', re.I),
    r('light bulb', re.I),
    r('.+ tour', re.I),
    r('surgery', re.I),
    r('.+ restoration', re.I),
    r('cleaning service', re.I),
    r('cleaning compan', re.I),
    r('house clean', re.I),
    r('vibrator', re.I),
    r('male.+pills', re.I),
    r('seo .+', re.I),
    r('.+ lawyer', re.I),
    r('flat stomach', re.I),
    r('weight loss', re.I),
    r('angle grinder', re.I),
    r('janetcmr', re.I),
    r('steamfast sf-407', re.I),
    r('du ventre', re.I),
    r('iphone', re.I),
    r('antivirus', re.I),
    r('mortgage', re.I),
    r('windows.*key', re.I),
    r('office.*key', re.I),
    r('louis.*vuitton', re.I),
    r('land for sale', re.I),
    r('suspension training', re.I),
    r('artificial turf', re.I),
    r('make money', re.I),
    r('money online', re.I),
    r('beauty business', re.I),
    r('cheap.+ticket', re.I),
    r('hair loss', re.I),
    r('fasciitis', re.I),
    r('abuse', re.I),
    r('finance professional', re.I),
    r('slot machine', re.I),
    r('addiction', re.I),
    r('fall in love', re.I),
    r('classified ads', re.I),
    r('^seo$', re.I),
    r('rapidement', re.I),
    r('gratuitement', re.I),
    r('transpiration', re.I),
    r('maigrir', re.I),
    r('mobile.+app', re.I),
    r('^cash$', re.I),
    r('habitat restore', re.I),
    r('android developer', re.I),
    r('web.*software', re.I),
    r('laptops', re.I),
    r(' advertising', re.I),
    r('voisine', re.I),
    r('cartomancie', re.I),
    r(' amour', re.I),
    r('crash course', re.I),
    r('hospital', re.I),
    r('poop bag', re.I),
    r('internet marketing', re.I),
    r('project management', re.I),
    r(' services', re.I),
    r('nauka angielskiego', re.I),
    r('^loans?$', re.I),
    r('jobs? in ', re.I),
    r('bipolar test', re.I),
    r('mincir', re.I),
    r('adopting ', re.I),
    r('travail', re.I),
    r('custom.*builder', re.I),
    r('air condition', re.I),
    r('klima servisi', re.I),
    r('last minute', re.I),
    r('zeiterfassung', re.I),
    r('spraytan', re.I),
    r(' girls', re.I),
    r('mold ', re.I),
    r('remediation', re.I),
    r('barbecue', re.I),
    r('new jersey', re.I),
    r('minivan', re.I),
    r('handicap', re.I),
    r('used ', re.I),
    r('magic mesh', re.I),
    r('forex', re.I),
    r('iit exam', re.I),
    r('garagedoor', re.I),
    r('garage door', re.I),
    r('swing set', re.I),
    r('designer cloth', re.I),
    r('it health', re.I),
    r('healthcare', re.I),
    r('fiance visa', re.I),
    r('for sale', re.I),
    r('linoleum', re.I),
    r('essay editor', re.I),
    r('professional.*editor', re.I),
    r('tailor.*shirt', re.I),
    r('divorce attorney', re.I),
    r(' dating', re.I),
    r('dating ', re.I),
    r('^dating$', re.I),
    r('financing', re.I),
    r('restaurant ', re.I),
    r('adoption', re.I),
    r('adoptive', re.I),
    r('article submission', re.I),
    r('ultrasound ', re.I),
    r('hypnoteraphy', re.I),
    r('mobile signal', re.I),
    r('signal booster', re.I),
    r('party suppl', re.I),
    r('vergleich', re.I),
    r('buy ', re.I),
    r('twitter ', re.I),
    r('football pick', re.I),
    r('net branch', re.I),
    r('tax attorney', re.I),
    r('ugg boot', re.I),
    r('uggboot', re.I),
    r('nurse qualification', re.I),
    r('car transport', re.I),
    r('prank call', re.I),
    r('web design', re.I),
    r('scuba diving', re.I),
    r('spas in', re.I),
    r('thailand ', re.I),
    r('retirement', re.I),
    r('scratchcard', re.I),
    r('scratch card', re.I),
    r('satchel handbag', re.I),
    r('leather ', re.I),
    r('for women', re.I),
    r('for woman', re.I),
    r(' vacation', re.I),
    r('vacation ', re.I),
    r('video poker', re.I),
    r('couch surf', re.I),
    r(' knives', re.I),
    r('family vacation', re.I),
    r('family issues', re.I),
    r('fake.*watch', re.I),
    r('flex duct', re.I),
    r('house paint', re.I),
    r('article directory', re.I),
    r('viagra', re.I),
    r(' attorney', re.I),
    r('attorney ', re.I),
    r('^attorney$', re.I),
    r('chinese herb', re.I),
    r('fertality', re.I),
    r(' earring', re.I),
    r('^earring$', re.I),
    r('law enforcement', re.I),
    r('training online', re.I),
    r(' online', re.I),
    r(' massage', re.I),
    r('massage ', re.I),
    r('^massage$', re.I),
    r('hair removal', re.I),
    r('chanel bag', re.I),
    r('chanel ', re.I),
    r('trench coat', re.I),
    r('credit report', re.I),
    r('stem cell', re.I),
    r('personal statement', re.I),
    r('ultra sound', re.I),
    r('resume writing', re.I),
    r('glass pool', re.I),
    r('moncler.*jacket', re.I),
    r('button triplet', re.I),
    r('love music', re.I),
    r('muscle building', re.I),
    r('cheap jordans', re.I),
    r('astrologie', re.I),
    r('natural vitamin', re.I),
    r('vitamins? supplement', re.I),
    r('^cheap ', re.I),
    r('celik raf', re.I),
    r('jerseys', re.I),
    r('fabric blinds', re.I),
    r('wedding dress', re.I),
    r('bingoonline', re.I),
    r('spyware removal', re.I),
    r('income plan', re.I),
    r(' workout', re.I),
    r(' printing', re.I),
    r('bankruptcy', re.I),
    r('music video', re.I),
    r('wind shield', re.I),
    r('auto transport', re.I),
    r('sunglasses', re.I),
    r('business card', re.I),
    r('colon cleanse', re.I),
    r(' cleanse', re.I),
    r('herbal product', re.I),
    r('^webhosting$', re.I),
    r('hosting review', re.I),
    r('telefonsex', re.I),
    r('natural health', re.I),
    r('health product', re.I),
    r('couples counsel', re.I),
    r(' hotels? ', re.I),
    r('^hotels? ', re.I),
    r('driving instructor', re.I),
    r('halloween ', re.I),
    r('justin bieber', re.I),
    r('car insurance', re.I),
    r(' insurance', re.I),
    r('ex boyfriend', re.I),
    r('hemorrhoid', re.I),
    r('penny auction', re.I),
    r('free sms', re.I),
    r('love sms', re.I),
    r('funny sms', re.I),
    r('birthday sms', re.I),
    r('floor sanding', re.I),
    r('tongue piercing', re.I),
    r('^psychologist$', re.I),
    r('bin cabinet', re.I),
    r('bin shelving', re.I),
    r('droid accesor', re.I),
    r('wholesale', re.I),
    r('lingerie', re.I),
    r('assignment help', re.I),
    r('wedding', re.I),
    r('domain price', re.I),
    r('belly fat', re.I),
    r(' symptoms', re.I),
    r('research paper', re.I),
    r(' betting', re.I),
    r(' facts', re.I),
    r('nike.*sale', re.I),
    r('cigarette ', re.I),
    r('cigars ', re.I),
    r('affiliate program', re.I),
    r('cosmetology', re.I),
    r('personal trainer', re.I),
    r('commercial cleaning', re.I),
    r('cholesterol', re.I),
    r('^funny ', re.I),
    r('coach bag', re.I),
    r('brand bag', re.I),
    r('^bags$', re.I),
    r('timberland', re.I),
    r(' boots', re.I),
    r('baby contest', re.I),
    r('flirten', re.I),
    r('fashion ', re.I),
    r(' glasses', re.I),
    r('eyeglass', re.I),
    r('grow taller', re.I),
    r('nursing shoe', re.I),
    r('hair extension', re.I),
    r('flatter stomach', re.I),
    r('love quote', re.I),
    r('menopause', re.I),
    r('driving lesson', re.I),
    r('article director', re.I),
    r('^oakley$', re.I),
    r('bag wholesale', re.I),
    r('wholesale', re.I),
    r('bottom shoes', re.I),
    r('sexy.*costume', re.I),
    r('dog obedience', re.I),
    r('gorilla safari', re.I),
    r('weightloss', re.I),
    r('internet wiki', re.I),
    r('du sommeil', re.I),
    r('barcode', re.I),
    r(' software', re.I),
    r('energy efficient', re.I),
    r(' rental', re.I),
    r('virtual assistant', re.I),
    r('eczema', re.I),
    r('spinal surgeon', re.I),
    r('in kentucky', re.I),
    r('thesis writing', re.I),
    r('accessories for', re.I),
    r('trophies and medals', re.I),
    r('piercing tools', re.I),
    r('driving school', re.I),
    r('share trading', re.I),
    r('energy solution', re.I),
    r('cash advance', re.I),
    r('ivc filter', re.I),
    r(' translation', re.I),
    r('axle cover', re.I),
    r('swing seat', re.I),
    r('grout cleaner', re.I),
    r('^debt ', re.I),
    r(' tutorial', re.I),
    r('artificial grass', re.I),
    r('mens? tuxedo', re.I),
    r('for m[ae]n', re.I),
    r('youtube ', re.I),
    r('business loan', re.I),
    r(' loan', re.I),
    r('landscape design', re.I),
    r('dog fence', re.I),
    r('pizza oven', re.I),
    r('^p90$', re.I),
    r('golden root', re.I),
    r('gain height', re.I),
    r('skin care', re.I),
    r('dry climate', re.I),
    r('medical billing', re.I),
    r('energy solution', re.I),
    r('web  design', re.I),
    r('flv player', re.I),
    r('cyprus compan', re.I),
    r('video chat', re.I),
    r('free chat', re.I),
    r('^ugg ', re.I),
    r('wood floor', re.I),
    r('personal growth', re.I),
    r('bumper sticker', re.I),
    r('canvas print', re.I),
    r('office coordinator', re.I),
    r('wood pellet', re.I),
    r('sungate energy', re.I),
    r(' watches$', re.I),
    r('webcam chat', re.I),
    r('web chat', re.I),
    r('american single', re.I),
    r('communication degree', re.I),
    r('water softener', re.I),
    r('cna training', re.I),
    r(' tutor$', re.I),
    r('mobile phone', re.I),
    r('miami roofing', re.I),
    r('christmas forum', re.I),
    r('savings account', re.I),
    r('retail management', re.I),
    r('management system', re.I),
    r('retail traffic', re.I),
    r('traffic counting', re.I),
    r('data recovery', re.I),
    r('^freelance ', re.I),
    r('voucher', re.I),
    r('discount code', re.I),
    r('electric fence', re.I),
    r('in dubai', re.I),
    r('for rent', re.I),
    r('uggs sale', re.I),
    r('free.*test', re.I),
    r('vending machine', re.I),
    r('essay writing', re.I),
    r('logo design', re.I),
    r('design contest', re.I),
    r('penis', re.I),
    r('online pharmacy', re.I),
    r('credit bureau', re.I),
    r('online homework', re.I),
    r('homework help', re.I),
    r('online assignment', re.I),
    r('emergency food', re.I),
    r('jobs? from home', re.I),
    r('part time job', re.I),
    r('legal steroid', re.I),
    r('los angeles', re.I),
    r('public record', re.I),
    r('social media', re.I),
    r('wrinkle cream', re.I),
    r('diet pill', re.I),
    r('make a website', re.I),
    r('ovulation kit', re.I),
    r(' recipes$', re.I),
    r('arcade game', re.I),
    r('side effect', re.I),
    r('bulk sms', re.I),
    r('oil price', re.I),
    r('hiv aids', re.I),
    r('pci compliance', re.I),
    r('treatment of', re.I),
    r('suzuki motorcycle', re.I),
    r('medical face mask', re.I),
    r('^medical ', re.I),
    r(' escorts$', re.I),
    r('photo contest', re.I),
    r('oil painting', re.I),
    r('stock tip', re.I),
]

spamlist_emails = [
    r('cancer', re.I),
    r('angelmike', re.I),
]

spamlist_urls = [
    r('cancer', re.I),
    r('du-?ventre', re.I),
    r('xrumer.+service', re.I),
    r('cheap-', re.I),
    r('discount.*coupon', re.I),
    r('wedding', re.I),
    r('abuse', re.I),
    r('addiction', re.I),
    r('android-developer.in', re.I),
    r('android-app', re.I),
    r('itunes.apple.com', re.I),
    r('telefon-sex', re.I),
    r('longchamp', re.I),
    r('slotmachine', re.I),
    r('gambling', re.I),
    r('deals.co', re.I),
    r('tripploans.com', re.I),
    r('kredit.com', re.I),
    r('phonecharger', re.I),
    r('footballpicks', re.I),
    r('divorceattorney', re.I),
    r('asiadate', re.I),
    r('freemoney', re.I),
    r('vacation-network', re.I),
    r('casino', re.I),
    r('moncler', re.I),
    r('astrologie', re.I),
    r('flowers.info', re.I),
    r('www.flowers', re.I),
    r('y8games', re.I),
]

spamlist_comments = [
    r('cash loan', re.I),
    r('payday loan', re.I),
    r('>loan<', re.I),
    r('tripploans.com', re.I),
    r('natural remed(y|ies)', re.I),
    r('acid reflux', re.I),
    r('unlock iphone', re.I),
    r('real estate', re.I),
    r('live sport', re.I),
    r('fasciitis exercise', re.I),
    r('foreclosure', re.I),
    r('house cleaning', re.I),
    r('quotes about life', re.I),
    r('creatine supplement', re.I),
    r('outlook time tracking', re.I),
    r('bukmacherskie', re.I),
    r('shoes outlet', re.I),
    r('cheap hotel', re.I),
    r('saint laurent', re.I),
    r('vacation network', re.I),
    r('cheap.*shoes', re.I),
    r('cheap.*air.*max', re.I),
    r('nike-outlet', re.I),
    r('discount.*shoes', re.I),
    r('nauka angiel', re.I),
    r('credit score', re.I),
    r('boat loan', re.I),
    r('car loan', re.I),
    r('house loan', re.I),
    r('apartment loan', re.I),
    r('dental insurance', re.I),
    r('cheap.*insurance', re.I),
    r('auto insurance', re.I),
    r('car insurance', re.I),
    r('rwanda safaris', re.I),
    r('free iphone', re.I),
    r('iphone deal', re.I),
    r('drudge report', re.I),
    r('hurricane.com', re.I),
    r('slot machine', re.I),
    r('printable coupon', re.I),
    r('tax attorney', re.I),
    r('>last minute', re.I),
    r('laptisor.*vanzare', re.I),
    r('>.*?dentist<', re.I),
    r('>.*?accomodation<', re.I),
    r('>debit card<', re.I),
    r('>credit card<', re.I),
    r('thyroid symptoms', re.I),
    r('angina symptoms', re.I),
    r('morning sickness', re.I),
    r('sickness remed(y|ies)', re.I),
    r('ex-?boyfriend', re.I),
    r('ex-?girlfriend', re.I),
    r('induce labor', re.I),
    r('knee pain', re.I),
    r('pain running', re.I),
    r('penisforstoring', re.I),
    r('>water colors', re.I),
    r('>mortgage ', re.I),
    r('>pandora ', re.I),
    r('term papers?<', re.I),
    r('finance<', re.I),
    r('buy.*toaster', re.I),
    r('football picks<', re.I),
    r('finance degrees?<', re.I),
    r('air.jordan', re.I),
    r('grout strain', re.I),
    r('acne treatment', re.I),
    r('zeanballonline.com', re.I),
    r('louis vuitton', re.I),
    r('home furniture', re.I),
    r('dog trainer', re.I),
    r('xanax abuse', re.I),
    r('toronto limo', re.I),
]


########NEW FILE########
__FILENAME__ = config
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#

# copied MakoDict from catonmat.views.utils because I couldn't get rid
# of circular references. Also renamed it to MakoDictz for great justice.

class MakoDictz(object):
    """
    Given a dict d, MakoDict makes its keys accessible via dot.
    It also returns None if the key doesn't exist.
    >>> d = DotDict({'apple': 5, 'peach': { 'kiwi': 9 } })
    >>> d.apple
    5
    >>> d.peach.kiwi
    9
    >>> d.coco
    None
    """
    def __init__(self, d, exclude=None):
        if exclude is None:
            exclude = []

        for k, v in d.items():
            if isinstance(v, dict) and k not in exclude:
                v = MakoDict(v)
            self.__dict__[k] = v

    def __getitem__(self, k):
        return self.__dict__[k]

    def __getattr__(self, name):
        return None

    def __setattr__(self, name, value):
        self.__dict__[name] = value

    def __setitem__(self, name, value):
        self.__dict__[name] = value


config = MakoDictz({
    'database_uri':     'mysql://catonmat@localhost/catonmat?charset=utf8',
    'database_echo':    False,
    'posts_per_page':   5,
    'use_cache':        True,
    'download_path':    '/home/pkrumins/catonmat/downloads',
    'rss_items':        20,
    'mako_modules':     '/home/pkrumins/catonmat/mako_modules',
    'ips_file':         '/home/pkrumins/catonmat/admin_ips.txt',
    'admin_hash_file':  '/home/pkrumins/catonmat/admin_hash.txt',
    'secure_key':       'key'
})


########NEW FILE########
__FILENAME__ = database
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#

from sqlalchemy.orm  import mapper, sessionmaker, scoped_session
from sqlalchemy      import (
    MetaData,
    Table,    Column,   ForeignKey,
    String,   Text,     Integer,        DateTime,   Boolean,    LargeBinary,
    create_engine
)

from catonmat.config import config

# ----------------------------------------------------------------------------

metadata = MetaData()
engine = create_engine(
    config['database_uri'],
    echo=config['database_echo'],
    pool_recycle=3600
)

Session = sessionmaker(bind=engine, autoflush=True, autocommit=False)
session = scoped_session(Session)

pages_table = Table('pages', metadata,
    Column('page_id',       Integer,    primary_key=True),
    Column('title',         String(256)),
    Column('created',       DateTime),
    Column('last_update',   DateTime),
    Column('content',       Text),
    Column('excerpt',       Text),      # goes in <meta description="...">
    Column('category_id',   Integer,    ForeignKey('categories.category_id')),
    Column('views',         Integer),   # should factor out to pagemeta_table
    Column('status',        String(64)),# should factor out to pagemeta_table
    mysql_charset='utf8'
)

pagemeta_table = Table('page_meta', metadata,
    Column('meta_id',       Integer,     primary_key=True),
    Column('page_id',       Integer,     ForeignKey('pages.page_id')),
    Column('meta_key',      String(128)),
    Column('meta_val',      LargeBinary),
    mysql_charset='utf8'
)

revisions_table = Table('revisions', metadata,
    Column('revision_id',   Integer,    primary_key=True),
    Column('page_id',       Integer,    ForeignKey('pages.page_id')),
    Column('timestamp',     DateTime),
    Column('change_note',   Text),
    Column('title',         String(256)),
    Column('content',       Text),
    Column('excerpt',       Text),
    mysql_charset='utf8'
)

comments_table = Table('comments', metadata,
    Column('comment_id',    Integer,    primary_key=True),
    Column('parent_id',     Integer),
    Column('page_id',       Integer,    ForeignKey('pages.page_id')),
    Column('visitor_id',    Integer,    ForeignKey('visitors.visitor_id')),
    Column('timestamp',     DateTime),
    Column('name',          String(64)),
    Column('email',         String(128)),
    Column('gravatar_md5',  String(32)),
    Column('twitter',       String(128)),
    Column('website',       String(256)),
    Column('comment',       Text),
    mysql_charset='utf8'
)

categories_table = Table('categories', metadata,
    Column('category_id',   Integer,     primary_key=True),
    Column('name',          String(128)),
    Column('seo_name',      String(128), unique=True),
    Column('description',   Text),
    Column('count',         Integer),    # number of pages in this category
)

tags_table = Table('tags', metadata,
    Column('tag_id',        Integer,     primary_key=True),
    Column('name',          String(128)),
    Column('seo_name',      String(128), unique=True),
    Column('description',   Text),
    Column('count',         Integer),    # number of pages tagged
)

page_tags_table = Table('page_tags', metadata,
    Column('page_id',       Integer,    ForeignKey('pages.page_id')),
    Column('tag_id',        Integer,    ForeignKey('tags.tag_id'))
)

urlmaps_table = Table('url_maps', metadata,
    Column('url_map_id',    Integer,     primary_key=True),
    Column('request_path',  String(256), unique=True),
    Column('page_id',       Integer,     ForeignKey('pages.page_id')),
    mysql_charset='utf8'
)

redirects_table = Table('redirects', metadata,
    Column('redirect_id',   Integer,     primary_key=True),
    Column('old_path',      String(256), unique=True),
    Column('new_path',      String(256)),
    Column('code',          Integer),
    mysql_charset='utf8'
)

fourofour_table = Table('404', metadata,
    Column('404_id',        Integer,    primary_key=True),
    Column('request_path',  Text),
    Column('date',          DateTime),
    Column('visitor_id',    Integer,    ForeignKey('visitors.visitor_id')),
    mysql_charset='utf8'
)

exceptions_table = Table('exceptions', metadata,
    Column('exception_id',   Integer,    primary_key=True),
    Column('request_path',   Text),
    Column('args',           Text),
    Column('form',           Text),
    Column('exception_type', Text),
    Column('traceback',      Text),
    Column('last_error',     Text),
    Column('date',           DateTime),
    Column('visitor_id',     Integer,    ForeignKey('visitors.visitor_id')),
    mysql_charset='utf8'
)

blogpages_table = Table('blog_pages', metadata,
    Column('blog_page_id',  Integer,    primary_key=True),
    Column('page_id',       Integer,    ForeignKey('pages.page_id')),
    Column('publish_date',  DateTime),
    Column('visible',       Boolean),
    mysql_charset='utf8'
)

visitors_table = Table('visitors', metadata,
    Column('visitor_id',    Integer,    primary_key=True),
    Column('ip',            String(39)),
    Column('host',          String(256)),
    Column('headers',       Text),
    Column('timestamp',     DateTime),
    mysql_charset='utf8'
)

rss_table = Table('rss', metadata,
    Column('rss_id',        Integer,    primary_key=True),
    Column('page_id',       Integer,    ForeignKey('pages.page_id')),
    Column('publish_date',  DateTime),
    Column('visible',       Boolean),
    mysql_charset='utf8'
)

downloads_table = Table('downloads', metadata,
    Column('download_id',   Integer,    primary_key=True),
    Column('title',         String(128)),
    Column('filename',      String(128)),
    Column('mimetype',      String(64)),
    Column('timestamp',     DateTime),
    Column('downloads',     Integer),
    mysql_charset='utf8'
)

download_stats_table = Table('download_stats', metadata,
    Column('stat_id',       Integer,    primary_key=True),
    Column('download_id',   Integer,    ForeignKey('downloads.download_id')),
    Column('ip',            String(39)),
    Column('timestamp',     DateTime),
    mysql_charset='utf8'
)

feedback_table = Table('feedback', metadata,
    Column('feedback_id',   Integer,    primary_key=True),
    Column('visitor_id',    Integer,    ForeignKey('visitors.visitor_id')),
    Column('name',          String(64)),
    Column('email',         String(128)),
    Column('website',       String(256)),
    Column('subject',       Text),
    Column('message',       Text),
    Column('timestamp',     DateTime),
    mysql_charset='utf8'
)

article_series_table = Table('article_series', metadata,
    Column('series_id',     Integer,    primary_key=True),
    Column('name',          String(128)),
    Column('seo_name',      String(128)),
    Column('description',   Text),
    Column('count',         Integer),
    mysql_charset='utf8'
)

pages_to_series_table = Table('pages_to_series', metadata,
    Column('page_id',       Integer,    ForeignKey('pages.page_id')),
    Column('series_id',     Integer,    ForeignKey('article_series.series_id')),
    Column('order',         Integer),
)

search_history_table = Table('search_history', metadata,
    Column('search_id',     Integer,    primary_key=True),
    Column('query',         Text),
    Column('timestamp',     DateTime),
    Column('visitor_id',    Integer,    ForeignKey('visitors.visitor_id')),
    mysql_charset='utf8'
)

news_table = Table('news', metadata,
    Column('news_id',       Integer,    primary_key=True),
    Column('title',         String(128)),
    Column('seo_title',     String(128)),
    Column('timestamp',     DateTime),
    Column('content',       Text),
    mysql_charset='utf8'
)

text_ads_table = Table('text_ads', metadata,
    Column('ad_id',         Integer,    primary_key=True),
    Column('page_id',       Integer,    ForeignKey('pages.page_id')),
    Column('title',         String(128)),
    Column('html',          Text),
    Column('expires',       DateTime),
    Column('priority',      Integer),
    mysql_charset='utf8'
)

paypal_payments_table = Table('paypal_payments', metadata,
    Column('payment_id',        Integer,    primary_key=True),
    Column('product_type',      String(128)), # my custom type
    Column('status',            String(64)),  # my custom status
    Column('transaction_id',    String(128)), # txn_id         paypal field
    Column('transaction_type',  String(128)), # txn_type       paypal field
    Column('payment_status',    String(64)),  # payment_status paypal field
    Column('mc_gross',          String(16)),  # mc_gross       paypal field
    Column('mc_fee',            String(16)),  # mc_fee         paypal field
    Column('first_name',        String(128)), # first_name     paypal field
    Column('last_name',         String(128)), # last_name      paypal field
    Column('payer_email',       String(256)), # payer_email    paypal field
    Column('system_date',       DateTime),    # system date i received POST request from paypal
    Column('payment_date',      String(128)), # payment_date field in paypal field
    Column('ipn_message',       Text),
    Column('comments',          Text),
    Column('visitor_id',        Integer,    ForeignKey('visitors.visitor_id'))
)


########NEW FILE########
__FILENAME__ = errorlog
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#

from catonmat.models    import FouroFour, Exception
from StringIO           import StringIO

import traceback
import sys

# ----------------------------------------------------------------------------

def log_404(request):
    if request.path.find("/c/") != 0: # don't log comment url 404s
        FouroFour(request).save()


def str_traceback(exc_type, exc_value, tb):
    buffer = StringIO()
    traceback.print_exception(exc_type, exc_value, tb, file=buffer)
    return buffer.getvalue()


def log_exception(request):
    exc_type, exc_value, tb = sys.exc_info()
    str_tb = str_traceback(exc_type, exc_value, tb)
    Exception(request, str(exc_type), str(exc_value), str_tb).save()


########NEW FILE########
__FILENAME__ = models
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#

from sqlalchemy.orm            import dynamic_loader, relation, mapper, backref
from sqlalchemy.orm.interfaces import AttributeExtension

from catonmat.database      import (
    pages_table,     revisions_table, urlmaps_table,    fourofour_table,
    blogpages_table, comments_table,  categories_table, tags_table,
    page_tags_table, visitors_table,  rss_table,        pagemeta_table,
    downloads_table, redirects_table, feedback_table,   exceptions_table,
    download_stats_table, article_series_table, pages_to_series_table,
    search_history_table, news_table, text_ads_table,   paypal_payments_table,
    session
)

from urlparse               import urlparse
from datetime               import datetime

import re
import hashlib
import simplejson as json

# ----------------------------------------------------------------------------

# Copied back from catonmat.views.utils due to circular references
def number_to_us(num):
    return (','.join(re.findall(r'\d{1,3}', str(num)[::-1])))[::-1]


class ModelBase(object):
    def save(self):
        session.add(self)
        session.commit()


class Page(ModelBase):
    def __init__(self, title, content=None, excerpt=None, created=None, last_update=None, category_id=None, views=0):
        self.title = title
        self.content = content
        self.excerpt = excerpt
        self.created = created
        self.last_update = last_update
        self.category_id = category_id
        self.views = views
        
        if self.created is None:
            self.created = datetime.utcnow()
        if self.last_update is None:
            self.last_update = datetime.utcnow()

    @property
    def parsed_content(self):
        from catonmat.parser import parse_page
        return parse_page(self.content)

    def parsed_content_with_ad(self, ad_icon, ad_noicon):
        from catonmat.parser import parse_page_with_ad
        return parse_page_with_ad(self.content, ad_icon, ad_noicon)

    @property
    def plain_text(self):
        from catonmat.parser import plain_text_page
        return plain_text_page(self.content)

    @property
    def publish_time(self):
        if self.blog_page:
            return self.blog_page.publish_date.strftime("%B %d, %Y")
        return self.created.strftime("%B %d, %Y")

    @property
    def comment_count(self):
        return session.query(Comment).filter_by(page_id=self.page_id).count()

    def get_meta(self, meta_key):
        meta = self.meta.filter_by(meta_key=meta_key).first()
        if meta:
            return meta.meta_val
        return ''

    def set_meta(self, meta_key, meta_val):
        meta = self.meta.filter_by(meta_key=meta_key).first()
        if not meta:
            meta = PageMeta(self, meta_key, meta_val)
            self.meta.append(meta)
        else:
            meta.meta_val = meta_val
        self.save()

    def delete_meta(self, meta_key):
        meta = self.meta.filter_by(meta_key=meta_key).first()
        if meta:
            self.meta.remove(meta)
            self.save()

    def _get_request_path(self):
        if self.url_map:
            return self.url_map.request_path
        return ''

    def _set_request_path(self, path):
        if path:
            if self.url_map:
                self.url_map.request_path = path
            else:
                self.url_map = UrlMap(path, self.page_id)
        else: # no path - delete the url_map
            if self.url_map:
                session.delete(self.url_map)
        self.save()

    request_path = property(_get_request_path, _set_request_path)

    @property
    def us_views(self):
        return number_to_us(self.views)

    def delete_tag(self, tag_name):
        tag = session.query(Tag).filter_by(name=tag_name).first()
        if tag in self.tags:
            self.tags.remove(tag)
            self.save()
            if tag.count == 1:
                session.delete(tag)
            else:
                tag.count = Tag.count - 1
            session.commit()

    def add_tag(self, tag):
        real_tag = tag
        t = session.query(Tag).filter_by(seo_name=tag.seo_name).first()
        if t:
            real_tag = t
            real_tag.count = Tag.count + 1
        else:
            real_tag.count = 1
        self.tags.append(real_tag)
        self.save()

    def add_comment(self, comment):
        self.comments.append(comment)

    def __repr__(self):
        return '<Page: %s>' % self.title


class PageMeta(ModelBase):
    def __init__(self, page, meta_key, meta_val):
        self.page  = page
        self.meta_key = meta_key
        self.meta_val = meta_val

    def __repr__(self):
        return '<PageMeta(%s) for Page(%s)' % (self.meta_key, self.page.title)


class Revision(ModelBase):
    def __init__(self, page, change_note, timestamp=None):
        self.page = page
        self.change_note = change_note
        self.timestamp = timestamp

        self.title = page.title
        self.content = page.content
        self.excerpt = page.excerpt

        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

    def __repr__(self):
        return '<Revision of Page(%s)>' % self.page.title


class Comment(ModelBase):
    def __init__(self, page_id, name, comment, visitor, parent_id=None, email=None, twitter=None, website=None, timestamp=None):
        self.page_id = page_id
        self.parent_id = parent_id
        self.name = name
        self.comment = comment
        self.email = email
        self.gravatar_md5 = ""
        self.twitter = twitter
        self.website = website
        self.visitor = visitor
        self.timestamp = timestamp

        if website:
            url = urlparse(website)
            if not url.scheme:
                self.website = 'http://' + website

        if parent_id == '':
            self.parent_id = None
        if email:
            self.gravatar_md5 = hashlib.md5(email).hexdigest()
        if timestamp is None:
            self.timestamp = datetime.utcnow()

    @property
    def parsed_comment(self):
        from catonmat.parser import parse_comment
        return parse_comment(self.comment)

    @property
    def publish_time(self):
        return self.timestamp.strftime("%B %d, %Y, %H:%M")

    def __repr__(self):
        return '<Comment(%d) on Page(%s)>' % (self.comment_id, self.page.title)


class Category(ModelBase):
    def __init__(self, name, seo_name, description=None, count=0):
        self.name = name
        self.seo_name = seo_name
        self.description = description
        self.count = count

    @property
    def blog_pages(self): # TODO: Don't know to make it via dynamic_loader
       return session. \
                query(Page). \
                join(BlogPage). \
                filter(Page.category_id==self.category_id)

    def __repr__(self):
        return '<Category %s>' % self.name


class Tag(ModelBase):
    def __init__(self, name, seo_name, description=None, count=0):
        self.name = name
        self.seo_name = seo_name
        self.description = description
        self.count = count

    @property
    def blog_pages(self): # TODO: Don't know to make it via dynamic_loader
       return session. \
                query(Page). \
                join(BlogPage). \
                join(
                  (page_tags_table, Page.page_id == page_tags_table.c.page_id),
                  (Tag,             Tag.tag_id   == page_tags_table.c.tag_id)
                ). \
                filter(Tag.tag_id==self.tag_id)

    def __repr__(self):
        return '<Tag %s>' % self.name


class UrlMap(ModelBase):
    def __init__(self, request_path, page_id):
        self.request_path = request_path
        self.page_id  = page_id

    def __repr__(self):
        return '<UrlMap from %s to Page(%s)>' % (self.request_path, self.page.title)


class Redirect(ModelBase):
    def __init__(self, old_path, new_path, code=301):
        self.old_path = old_path
        self.new_path = new_path
        self.code     = code

    def __repr__(self):
        return '<Redirect from %s to %s (%d)>' % (self.old_path, self.new_path, self.code)


class FouroFour(ModelBase):
    def __init__(self, request):
        self.request_path = request.path
        self.visitor = Visitor(request)
        self.date = datetime.utcnow()

    def __repr__(self):
        return '<404 of %s>' % self.request_path


class Exception(ModelBase):
    def __init__(self, request, exception_type, last_error, traceback):
        self.request_path = request.path
        if request.args:
            self.args = json.dumps(request.args)
        if request.form:
            self.form = json.dumps(request.form)
        self.exception_type = exception_type
        self.last_error = last_error
        self.traceback = traceback
        self.visitor = Visitor(request)
        self.date = datetime.utcnow()

    def __repr__(self):
        return '<Exception: %s>' % self.last_error


class BlogPage(ModelBase):
    def __init__(self, page, publish_date=None, visible=True):
        self.page = page
        self.publish_date = publish_date
        self.visible = visible

        if publish_date is None:
            self.publish_date = date.utcnow()

    def __repr__(self):
        return '<Blog Page of Page(%s)>' % page.title


class Visitor(ModelBase):
    def __init__(self, request):
        self.ip = request.remote_addr
        self.headers = str(request.headers).strip()
        self.host = None
        self.timestamp = datetime.utcnow()

    def __repr__(self):
        return '<Visitor from %s>' % self.ip


class Rss(ModelBase):
    def __init__(self, page, publish_date, visible=True):
        self.page = page
        self.publish_date = publish_date
        self.visible = visible

    def __repr__(self):
        return '<RSS for Page(%s)>' % page.title


class Download(ModelBase):
    def __init__(self, title, filename, mimetype=None, downloads=0, timestamp=None):
        self.title = title
        self.filename = filename
        self.mimetype = mimetype
        self.downloads = downloads
        self.timestamp = timestamp
        if timestamp is None:
            self.timestamp = datetime.utcnow()

    def another_download(self, request):
        self.downloads = Download.downloads + 1 # this creates an update statement
        download_stat = DownloadStats(self, request.remote_addr)
        self.save()
        download_stat.save()

    @property
    def us_downloads(self):
        return number_to_us(self.downloads)

    def __repr__(self):
        return '<Download %s>' % self.filename


class DownloadStats(ModelBase):
    def __init__(self, download, ip, timestamp=None):
        self.download = download
        self.ip = ip
        if timestamp is None:
            self.timestamp = datetime.utcnow()

    def __repr__(self):
        return '<DownloadStat of %s>' % self.download.filename


class Feedback(ModelBase):
    def __init__(self, visitor, name, email, subject, message, website=None):
        self.visitor = visitor
        self.name = name
        self.email = email
        self.subject = subject
        self.message = message
        self.website = website
        self.timestamp = datetime.utcnow()

    def __repr__(self):
        return '<Feedback from %s>' % self.name


class ArticleSeries(ModelBase):
    def __init__(self, name, seo_name, description):
        self.name = name
        self.seo_name = seo_name
        self.description = description

    def __repr__(self):
        return '<Article Series %s>' % self.name


class SearchHistory(ModelBase):
    def __init__(self, query, request):
        self.query = query
        self.visitor = Visitor(request)
        self.timestamp = datetime.utcnow()

    def __repr__(self):
        return '<Search for %s>' % self.query


class News(ModelBase):
    def __init__(self, title, seo_title, content, timestamp=None):
        self.title = title
        self.seo_title = seo_title
        self.content = content
        self.timestamp = timestamp
        if timestamp is None:
            self.timestamp = datetime.utcnow()

    @property
    def parsed_content(self):
        from catonmat.parser import parse_page
        return parse_page(self.content)

    @property
    def publish_time(self):
        return self.timestamp.strftime("%B %d, %Y")

    def __repr__(self):
        return '<News %s>' % self.title


class TextAds(ModelBase):
    def __init__(self, page, title, html, expires=None):
        self.page  = page
        self.title = title
        self.html  = html
        self.expires = expires

    def __repr__(self):
        return '<Text Ad %s>' % self.title


class PayPalPayments(ModelBase):
    def __init__(self, product_type, request):
        self.product_type = product_type
        self.transaction_id = request.form['txn_id']
        self.payment_status = request.form['payment_status']

        try:
            self.transaction_type = request.form['txn_type']
        except KeyError:
            self.transaction_type = 'none'

        try:
            self.mc_gross = request.form['mc_gross']
        except KeyError:
            try:
                self.mc_gross = request.form['mc_gross_1']
            except KeyError:
                try:
                    self.mc_gross = request.form['mc_gross1']
                except KeyError:
                    self.mc_gross = 0
        try:
            self.mc_fee = request.form['mc_fee']
        except KeyError:
            self.mc_fee = 0
        self.first_name = request.form['first_name']
        self.last_name = request.form['last_name']
        self.payer_email = request.form['payer_email']
        self.system_date = datetime.utcnow()
        self.payment_date = request.form['payment_date']
        self.status = 'new'
        self.ipn_message = json.dumps(request.form.to_dict())
        self.visitor = Visitor(request)

    def extract(self, prop):
        return json.loads(self.ipn_message)[prop]

    def __repr__(self):
        return '<Paypal Payment from %s>' % self.extract('payer_email')


class PageCategoryExtension(AttributeExtension):
    def set(self, state, value, oldvalue, initiator):
        if value != oldvalue:
            page = state.obj()
            if page.status != 'draft':
                oldvalue.count = Category.count - 1
                value.count = Category.count + 1
        return value

mapper(Page, pages_table, properties={
    'revisions': dynamic_loader(
                    Revision,
                    backref='page',
                    order_by=revisions_table.c.revision_id.desc()
    ),
    'comments': dynamic_loader(
                    Comment,
                    backref='page',
                    order_by=comments_table.c.comment_id.asc()
    ),
    'category': relation(Category, extension=PageCategoryExtension()),
    'tags':     relation(
                    Tag,
                    secondary=page_tags_table,
                    order_by=tags_table.c.seo_name,
                    cascade='all, delete'
    ),
    'meta':     dynamic_loader(
                    PageMeta,
                    backref='page',
                    order_by=pagemeta_table.c.meta_id,
                    cascade='all, delete, delete-orphan'
    ),
    'text_ads':  dynamic_loader(
                    TextAds,
                    order_by=[text_ads_table.c.priority, text_ads_table.c.ad_id]
    ),
    'url_map':   relation(UrlMap, uselist=False),
    'blog_page': relation(BlogPage, uselist=False),
    'rss_page':  relation(Rss, uselist=False)
})
mapper(PageMeta, pagemeta_table)
mapper(Revision, revisions_table)
mapper(Comment,  comments_table, properties={
    'visitor': relation(Visitor, uselist=False)
})
mapper(Category, categories_table)
mapper(Tag,      tags_table, properties={
    'pages': dynamic_loader(Page, secondary=page_tags_table)
})
mapper(UrlMap, urlmaps_table, properties={
    'page': relation(Page, uselist=False)
})
mapper(Redirect, redirects_table)
mapper(FouroFour, fourofour_table, properties={
    'visitor': relation(
                 Visitor,
                 uselist=False,
                 cascade='all, delete',
                 single_parent=True
    )
})
mapper(Exception, exceptions_table, properties={
    'visitor': relation(Visitor, uselist=False)
})
mapper(BlogPage, blogpages_table, properties={
    'page': relation(Page, uselist=False)
})
mapper(Rss, rss_table, properties={
    'page': relation(Page)
})
mapper(Visitor, visitors_table)
mapper(Download, downloads_table, properties={
    'stats': dynamic_loader(
                DownloadStats,
                backref='download',
                order_by=download_stats_table.c.stat_id.asc()
    )
})
mapper(DownloadStats, download_stats_table)
mapper(Feedback, feedback_table, properties={
    'visitor': relation(Visitor, uselist=False)
})
mapper(ArticleSeries, article_series_table, properties={
    'pages': relation(
                Page,
                secondary=pages_to_series_table,
                order_by=pages_to_series_table.c.order.asc(),
                backref=backref('series', uselist=False)
    )
})
mapper(SearchHistory, search_history_table, properties={
    'visitor': relation(Visitor, uselist=False)
})
mapper(News, news_table)
mapper(TextAds, text_ads_table, properties={
    'page': relation(Page, uselist=False)
})
mapper(PayPalPayments, paypal_payments_table, properties={
    'visitor': relation(Visitor, uselist=False)
})


########NEW FILE########
__FILENAME__ = commentparser
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#

from catonmat.parser.util   import (
    get_lexer, extract_tag_name, document_lexer,
    DocumentNode, ParagraphNode, TextNode, CommentNode, InlineTagNode,
    SelfClosingTagNode, BlockTagNode, LiteralNode,
)

from catonmat.parser.grammar import gdocument
from catonmat.parser.filter  import filter_tree

from StringIO               import StringIO
from urlparse               import urlparse

import re

# ----------------------------------------------------------------------------

ALLOWED_COMMENT_TAGS = [
    'a', 'b', 'strong', 'i', 'em', 'q', 'blockquote', 'code', 'pre', 'sub',
    'sup',
    'div', 'span'
]
ALLOWED_COMMENT_URL_SCHEMES = [ 'http', 'https', 'ftp' ]

href_re = re.compile(r"""href="([^"]+)"|href='([^']+)'""")
class_re = re.compile(r'class="([^"]+)"')

def build_parse_tree(token_stream):
    return gdocument(token_stream)

def allowed_tag(tag):
    return tag in ALLOWED_COMMENT_TAGS

def normalize_href(href):
    url = urlparse(href)
    check_scheme = True
    if not url.scheme:
        href = 'http://' + href
        check_scheme = False
    if check_scheme:
        if url.scheme not in ALLOWED_COMMENT_URL_SCHEMES:
            return None
    return href

def handle_a_tag(node, writable):
    match = href_re.search(node.value)
    if match:
        href = match.group(1) or match.group(2)
        href = normalize_href(href)
        if href:
            writable.write("""<a href="%s">""" % href)
            return
    writable.write("<a>")

def should_traverse_children(tag):
    return allowed_tag(tag)

def extract_class(tag):
    match = class_re.search(tag)
    if match:
        return match.group(1)
    return None

def handle_tag(node, tag, writable):
    if tag == 'a':
        handle_a_tag(node, writable)
    elif tag == 'div':
        if extract_class(node.value) == 'highlight':
            writable.write('<div class="highlight">')
        else:
            writable.write('<div>')
    elif tag == 'span':
        klass = extract_class(node.value)
        if klass:
            writable.write('<span class="%s">' % klass)
        else:
            writable.write('<span>')
    else:
        writable.write("<%s>" % tag)

def handle_disallowed_tag(node, tag, writable):
    writable.write("&lt;%s&gt;" % tag)
    build_html(node, writable)

def handle_tag_node(node, tag, writable):
    if allowed_tag(tag):
        handle_tag(node, tag, writable)
    else:
        handle_disallowed_tag(node, tag, writable)

def build_html(parse_tree, writable):
    for node in parse_tree:
        traverse_children = True
        if isinstance(node, ParagraphNode):
            writable.write("<p>")
        elif isinstance(node, TextNode):
            writable.write(node.value)
        elif isinstance(node, InlineTagNode) or \
                isinstance(node, BlockTagNode):
            tag = extract_tag_name(node.value)
            handle_tag_node(node, tag, writable)
            traverse_children = should_traverse_children(tag)
        elif isinstance(node, SelfClosingTagNode):
            tag = extract_tag_name(node.value)
            if tag == 'br':
                writable.write("<br>\n")

        if traverse_children:
            build_html(node, writable)

            if isinstance(node, ParagraphNode):
                writable.write("</p>\n")
            elif isinstance(node, InlineTagNode):
                tag = extract_tag_name(node.value)
                writable.write("</%s>" % tag)
            elif isinstance(node, BlockTagNode):
                tag = extract_tag_name(node.value)
                writable.write("</%s>\n" % tag)

def parse_comment(text):
    from catonmat.parser.lexer   import CommentLexer
    # TODO: this method is 1:1 as pageparser.py:parsepage(),
    #       merge them!
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    token_stream = get_lexer(text, CommentLexer)

    # first stage tree contains the full parse tree, including empty nodes
    # such as <p>       </p> and <p>   <br>   </p>.
    first_stage_tree = build_parse_tree(token_stream)

    # second stage tree clears up the empty text elements
    second_stage_tree = filter_tree(first_stage_tree)

    buffer = StringIO()
    build_html(second_stage_tree, buffer)
    return buffer.getvalue()


########NEW FILE########
__FILENAME__ = filter
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#

from catonmat.parser.util   import (
    extract_tag_name,
    ParagraphNode, TextNode, SelfClosingTagNode
)

# ----------------------------------------------------------------------------

def empty_text(text):
    return text.isspace()

def empty_pred(node):
    if isinstance(node, TextNode):
        return empty_text(node.value)
    elif isinstance(node, SelfClosingTagNode):
        return extract_tag_name(node.value) == 'br'
    return False

def empty_paragraph(p):
    """ A paragraph is empty if it contains only empty text nodes and <br>s """
    return all(empty_pred(pnode) for pnode in p)

def empty_node(node):
    if isinstance(node, ParagraphNode):
        return empty_paragraph(node)
    return False

def filter_tree(tree):
    tree.children = [filter_tree(child_node) for child_node in \
            tree.children if not empty_node(child_node)]
    return tree


########NEW FILE########
__FILENAME__ = grammar
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#

from catonmat.parser.util   import (
    DocumentNode, ParagraphNode, TextNode, CommentNode, InlineTagNode,
    SelfClosingTagNode, BlockTagNode, LiteralNode,
    accept_token, extract_tag_name, skip_token,
    DONT_P, RESPECT_BR
)

from pygments.token         import Token

# ----------------------------------------------------------------------------

def gdocument(token_stream):
    root = DocumentNode()
    while True:
        if accept_token(token_stream, Token.Par):
            skip_token(token_stream)
        elif accept_token(token_stream, Token.Br):
            skip_token(token_stream)
        elif accept_token(token_stream, Token.Literal):
            root.append(LiteralNode(token_stream.value))
        elif accept_token(token_stream, Token.Comment):
            root.append(CommentNode(token_stream.value))
        elif accept_token(token_stream, Token.Text):
            p = gparagraph(token_stream)
            root.append(p)
        elif accept_token(token_stream, Token.Tag.SelfClosingTag):
            p = gparagraph(token_stream)
            root.append(p)
        elif accept_token(token_stream, Token.Tag.InlineTag):
            p = gparagraph(token_stream)
            root.append(p)
        elif accept_token(token_stream, Token.Tag.BlockTag):
            block = gblock(token_stream)
            root.append(block)
        else:
            return root

def gparagraph(token_stream):
    p = ParagraphNode()
    while True:
        if accept_token(token_stream, Token.Par):
            skip_token(token_stream)
            return p
        elif accept_token(token_stream, Token.Br):
            p.append(gbr(token_stream))
        elif accept_token(token_stream, Token.Literal):
            p.append(LiteralNode(token_stream.value))
        elif accept_token(token_stream, Token.Comment):
            p.append(CommentNode(token_stream.value))
        elif accept_token(token_stream, Token.Text):
            p.append(TextNode(token_stream.value))
        elif accept_token(token_stream, Token.Tag.SelfClosingTag):
            p.append(SelfClosingTagNode(token_stream.value))
        elif accept_token(token_stream, Token.Tag.InlineTag):
            inline_tag = ginline_tag(token_stream)
            p.append(inline_tag)
        elif accept_token(token_stream, Token.Tag.BlockTag):
            return p
        else:
            return p

def gbr(token_stream):
    skip_token(token_stream)
    br = SelfClosingTagNode("<br>")
    if accept_token(token_stream, Token.Tag.BlockTag):
        return None
    if accept_token(token_stream, Token.Tag.Close):
        return None
    return br

def ginline_tag(token_stream):
    inline_tag = InlineTagNode(token_stream.value)
    while True:
        if accept_token(token_stream, Token.Tag.Close): # assume correctly nested and closed tags
            skip_token(token_stream)
            return inline_tag
        elif accept_token(token_stream, Token.Par):
            skip_token(token_stream)
        elif accept_token(token_stream, Token.Br):
            inline_tag.append(gbr(token_stream))
        elif accept_token(token_stream, Token.Literal):
            inline_tag.append(LiteralNode(token_stream.value))
        elif accept_token(token_stream, Token.Comment):
            inline_tag.append(CommentNode(token_stream.value))
        elif accept_token(token_stream, Token.Text):
            inline_tag.append(TextNode(token_stream.value))
        elif accept_token(token_stream, Token.Tag.SelfClosingTag):
            inline_tag.append(SelfClosingTagNode(token_stream.value))
        elif accept_token(token_stream, Token.Tag.InlineTag):
            nested_inline_tag = ginline_tag(token_stream)
            inline_tag.append(nested_inline_tag)
        elif accept_token(token_stream, Token.Tag.BlockTag):
            return inline_tag
        else:
            return inline_tag

def block_try_p(tag_name, token_stream, node_type, nonterminal=None):
    if tag_name in DONT_P:
        if nonterminal:
            return nonterminal(token_stream)
        return node_type(token_stream.value)
    else:
        return gparagraph(token_stream)

def gblock(token_stream):
    block = BlockTagNode(token_stream.value)
    tag_name = extract_tag_name(block.value)
    while True:
        if accept_token(token_stream, Token.Tag.Close): #assume correctly nested and closed tags
            skip_token(token_stream)
            return block
        elif accept_token(token_stream, Token.Par):
            skip_token(token_stream)
        elif accept_token(token_stream, Token.Br):
            if tag_name in RESPECT_BR:
                block.append(SelfClosingTagNode('<br>'))
            skip_token(token_stream)
        elif accept_token(token_stream, Token.Literal):
            block.append(LiteralNode(token_stream.value))
        elif accept_token(token_stream, Token.Comment):
            block.append(CommentNode(token_stream.value))
        elif accept_token(token_stream, Token.Text):
            block.append(block_try_p(tag_name, token_stream, TextNode))
        elif accept_token(token_stream, Token.Tag.SelfClosingTag):
            block.append(block_try_p(tag_name, token_stream, SelfClosingTagNode))
        elif accept_token(token_stream, Token.Tag.InlineTag):
            block.append(block_try_p(tag_name, token_stream, InlineTagNode, ginline_tag))
        elif accept_token(token_stream, Token.Tag.BlockTag):
            nested_block = gblock(token_stream)
            block.append(nested_block)
        else:
            return block


########NEW FILE########
__FILENAME__ = lexer
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#

from pygments               import highlight
from pygments.util          import ClassNotFound
from pygments.token         import Token
from pygments.lexer         import RegexLexer
from pygments.lexers        import get_lexer_by_name
from pygments.formatters    import HtmlFormatter

from catonmat.parser.util   import tag_type_by_name, get_lexer
from catonmat.models        import Download
from catonmat.database      import session

import re

# ----------------------------------------------------------------------------

class MyHtmlFormatter(HtmlFormatter):
    def __init__(self, other):
        self._xyzzy_other = other
        HtmlFormatter.__init__(self)

    def _wrap_pre(self, inner):
        yield 0, '<pre %s>' % self._xyzzy_other
        for tup in inner:
            yield tup
        yield 0, '</pre>'

# TODO: rewrite everything

class DocumentLexer(RegexLexer):
    def open_tag_handler_yielder(lexer, tag_name, full_tag):
        tag_type = tag_type_by_name(tag_name)
        return 0, tag_type, full_tag

    def open_tag_handler(lexer, match):
        tag_name = match.group(1)
        yield lexer.open_tag_handler_yielder(tag_name, match.group(0))

    def pure_pre_token_stream(lexer, pre_text, other=''):
        yield_items = [
            (Token.Tag.BlockTag, "<pre %s>" % other),
            (Token.Text, pre_text.replace('<', '&lt;')),
            (Token.Tag.Close, "</pre>")
        ]
        return yield_items

    def pure_pre_handler(lexer, match):
        for token, value in lexer.pure_pre_token_stream(match.group(1)):
            yield 0, token, value

    def html_pre_handler2(lexer, pre_text, other=''):
        yield 0, Token.Tag.BlockTag, "<pre %s>" % other
        yield 0, Token.Text, pre_text
        yield 0, Token.Tag.Close, "</pre>"

    def html_pre_handler(lexer, match):
        for v in lexer.html_pre_handler2(match.group(1)):
            yield v

    def lang_pre_handler2(lexer, lang, code, other=''):
        try:
            lang_lexer = get_lexer_by_name(lang, stripall=True)
            if other:
                html_formatter = MyHtmlFormatter(other)
            else:
                html_formatter = HtmlFormatter()
            token_stream = get_lexer(highlight(code, lang_lexer, html_formatter), PreLexer)
        except ClassNotFound:
            token_stream = lexer.pure_pre_token_stream(code)
        for token, value in token_stream:
            yield 0, token, value

    def lang_pre_handler(lexer, match):
        lang, code = match.groups()
        for v in lexer.lang_pre_handler2(lang, code):
            yield v

    def download_error(lexer, download_id):
        yield_items = [
            (Token.Text, "Oops, download with id %s wasn't found. " % download_id),
            (Token.Text, "Please let me know about this error via the "),
            (Token.Tag.InlineTag, '<a href="/feedback/">'),
            (Token.Text, "feedback"),
            (Token.Tag.Close, "</a>"),
            (Token.Text, " form! Thanks!")
        ]
        return yield_items

    def download_handler(lexer, match):
        download_id = match.group(1)
        download = session.query(Download).filter_by(download_id=download_id).first()
        if not download:
            token_stream = lexer.download_error(download_id)
        else:
            token_stream = [
                (Token.Tag.InlineTag,
                    '<a href="/download/%s" title="Download &quot;%s&quot;">' % \
                                        (download.filename, download.title)),
                (Token.Text, download.title),
                (Token.Tag.Close, "</a>")
            ]
        for token, value in token_stream:
            yield 0, token, value

    def download_hits_handler(lexer, match):
        download_id = match.group(1)
        download = session.query(Download).filter_by(download_id=download_id).first()
        if not download:
            token_stream = lexer.download_error(download_id)
        else:
            token_stream = [(Token.Text, download.downloads)]
        for token, value in token_stream:
            yield 0, token, value

    def download_nohits_handler(lexer, match):
        for v in lexer.download_handler(match):
            yield v

    def open_tag(lexer, _):
        yield 0, Token.Text, '&lt;'

    def pre_handler(lexer, match):
        args = match.group(1).strip().split(' ')
        body = match.group(2)

        lang = None

        for arg in args:
            match = re.match('lang="(.+?)"', arg)
            if match:
                lang = match.group(1)

        if lang:
            args.remove('lang="%s"' % lang)
            other = ' '.join(args)
            for v in lexer.lang_pre_handler2(lang, body, other):
                yield v
            return

        if 'html' in args:
            args.remove('html')
            other = ' '.join(args)
            for v in lexer.html_pre_handler2(body, other):
                yield v
            return

        other = ' '.join(args)
        for v, t in lexer.pure_pre_token_stream(body, other):
            yield 0, v, t

    def audio_handler(lexer, match):
        url = match.group(1)
        yield 0, Token.Text, "[audio:%s]" % url

    flags = re.IGNORECASE | re.DOTALL
    tokens = {
        'root': [
            (r'\n\n+',                         Token.Par),
            (r'\n',                            Token.Br),
            (r'[^[<\n]+',                      Token.Text),
            (r'\[download#(\d+)#nohits\]',     download_nohits_handler),
            (r'\[download#(\d+)#hits\]',       download_hits_handler),
            (r'\[download#(\d+)\]',            download_handler),
            (r'\[audio:(.+?)\]',               audio_handler),
            (r'<!--.*?-->',                    Token.Comment),
            (r'<pre>(.+?)</pre>',              pure_pre_handler),
            (r'<pre(.+?)>(.+?)</pre>',         pre_handler),
            (r'<([a-zA-Z0-9]+).*?>',           open_tag_handler),
            (r'</[^>]+>',                      Token.Tag.Close),
            (r'<',                             open_tag),
            (r'\[',                            Token.Text)
        ],
    }

class PreLexer(DocumentLexer):
    def pure_pre_token_stream(lexer, pre_text, other=''):
        yield_items = [
            (Token.Tag.BlockTag, "<pre %s>" % other),
            (Token.Text, pre_text),
            (Token.Tag.Close, "</pre>")
        ]
        return yield_items

from catonmat.parser.commentparser import ALLOWED_COMMENT_TAGS
allowed_open_tag_re = re.compile('|'.join('<(%s)>|<(%s)\W+.*?>' % (tag, tag) for tag in ALLOWED_COMMENT_TAGS))
allowed_close_tag_re = re.compile('|'.join('</(%s)>' % tag for tag in ALLOWED_COMMENT_TAGS))

class CommentLexer(DocumentLexer):
    def comment_open_tag_handler(lexer, match):
        tag_name = [t for t in match.groups() if t][0]
        yield lexer.open_tag_handler_yielder(tag_name, match.group(0))

    tokens = {
        'root': [
            (r'\n\n+',                Token.Par),
            (r'\n',                   Token.Br),
            (r'[^<\n]+',              Token.Text),
            (r'<pre>(.+?)</pre>',     DocumentLexer.pure_pre_handler),
            (r'<pre lang="(.+?)">(.+?)</pre>', DocumentLexer.lang_pre_handler),
            (allowed_open_tag_re,     comment_open_tag_handler),
            (allowed_close_tag_re,    Token.Tag.Close),
            (r'<',                    DocumentLexer.open_tag)
        ],
    }


########NEW FILE########
__FILENAME__ = pageparser
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#

from catonmat.parser.util    import (
    get_lexer, extract_tag_name, document_lexer,
    DocumentNode, ParagraphNode, TextNode, CommentNode, InlineTagNode,
    SelfClosingTagNode, BlockTagNode, LiteralNode,
)

from catonmat.parser.lexer   import DocumentLexer
from catonmat.parser.grammar import gdocument
from catonmat.parser.filter  import filter_tree

from StringIO                import StringIO

# ----------------------------------------------------------------------------

def build_parse_tree(token_stream):
    return gdocument(token_stream)

def build_html(tree, writable):
    for node in tree:
        if isinstance(node, ParagraphNode):
            writable.write("<p>")
        elif isinstance(node, TextNode):
            writable.write(node.value)
        elif isinstance(node, LiteralNode):
            writable.write(node.value)
        elif isinstance(node, CommentNode):
            writable.write(node.value)
        elif isinstance(node, InlineTagNode):
            writable.write(node.value)
        elif isinstance(node, BlockTagNode):
            writable.write(node.value)
        elif isinstance(node, SelfClosingTagNode):
            tag = extract_tag_name(node.value)
            if tag == 'br':
                writable.write("<br>\n")
            else:
                writable.write(node.value)

        build_html(node, writable)

        if isinstance(node, ParagraphNode):
            writable.write("</p>\n")
        elif isinstance(node, InlineTagNode):
            tag = extract_tag_name(node.value)
            writable.write("</%s>" % tag)
        elif isinstance(node, BlockTagNode):
            tag = extract_tag_name(node.value)
            writable.write("</%s>\n" % tag)

def build_plain_text(tree, writable):
    for node in tree:
        if isinstance(node, TextNode):
            writable.write(node.value)
        elif isinstance(node, ParagraphNode):
            writable.write(' ')
        elif isinstance(node, SelfClosingTagNode):
            tag = extract_tag_name(node.value)
            if tag == 'br':
                writable.write(' ')

        build_plain_text(node, writable)

def parse_page(text):
    tree = get_tree(text)
    return build(build_html, tree)

def plain_text_page(text):
    tree = get_tree(text)
    plain_text = build(build_plain_text, tree).strip()
    return plain_text

def get_tree(text):
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    token_stream = get_lexer(text, DocumentLexer)

    # first stage tree contains the full parse tree, including empty nodes
    # such as <p>       </p> and <p>   <br>   </p>.
    first_stage_tree = build_parse_tree(token_stream)

    # second stage tree clears up the empty text elements
    second_stage_tree = filter_tree(first_stage_tree)

    return second_stage_tree

def build(build_fn, tree):
    buffer = StringIO()
    build_fn(tree, buffer)
    return buffer.getvalue()

def parse_page_with_ad(text, ad_icon, ad_noicon):
    tree = get_tree(text)
    insert_ad(tree, ad_icon, ad_noicon)
    return build(build_html, tree)

def insert_ad(tree, ad_icon, ad_noicon):
    try: # has post icon?
        img = tree.children[0].children[0]
        if isinstance(img, SelfClosingTagNode):
            if img.value.find('post-icon'):
                adblock  = BlockTagNode('<div style="margin-bottom: 10px">')
                adblock.children.append(tree.children[0].children[0])
                float_ad = BlockTagNode('<div style="float: right; margin-right:20px">')
                float_ad.children.append(LiteralNode(ad_icon))
                clear = BlockTagNode('<div class="clear">')
                adblock.children.append(float_ad)
                adblock.children.append(clear)
                del tree.children[0].children[0]
                tree.children.insert(0, adblock)
        else:
            googlead = BlockTagNode('<div style="margin-bottom: 10px; text-align:center">')
            googlead.children.append(LiteralNode(ad_noicon))
            tree.children.insert(0, googlead)
    except:
        pass


########NEW FILE########
__FILENAME__ = util
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#

from pygments           import lex
from pygments.token     import Token

import re

# ----------------------------------------------------------------------------

SELF_CLOSING_TAGS = frozenset(['img', 'br', 'hr', 'input'])
INLINE_TAGS = frozenset([
    'a',      'abbr', 'acronym', 'b',        'bdo',   'big',  'cite',
    'code',   'dfn',  'em',      'font',     'i',     'kbd',  'label',
    'q',      's',    'samp',    'select',   'small', 'span', 'strike',
    'strong', 'sub',  'sup',     'textarea', 'tt',    'u',    'var'
])
DONT_P = frozenset(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'li', 'pre'])
RESPECT_BR = frozenset(['li'])

def tag_type_by_name(tag_name):
    tag_name = tag_name.lower()
    if tag_name in SELF_CLOSING_TAGS:
        return Token.Tag.SelfClosingTag
    elif tag_name in INLINE_TAGS:
        return Token.Tag.InlineTag
    else:
        return Token.Tag.BlockTag

def extract_tag_name(value):
    matches = re.match(r'<([a-zA-Z0-9]+)', value)
    if matches:
        return matches.group(1)
    raise ValueError("Tag '%s' didn't match regex" % value)

class TokenGenerator(object):
    """
    Given a generator from Pygments, this wrapper adds peek() method to look
    into the future, and adds several other convenience properties.
    """
    NONE = object()

    def __init__(self, generator):
        self.generator = generator
        self.peeked_value = self.NONE

    def peek(self):
        """ Peek for the next value in the generator """
        if self.peeked_value is self.NONE:
            # May throw StopIteration if we try to peek beyond last element
            self.peeked_value = self.generator.next()
            return self.peeked_value
        return self.peeked_value

    def _xyzzy(self, method, index):
        try:
            return method()[index]
        except StopIteration:
            return None

    @property
    def token(self):
        """ Get just the token in the generator """
        return self._xyzzy(self.next, 0)

    @property
    def value(self):
        """ Get just the value in the generator """
        return self._xyzzy(self.next, 1)

    @property
    def peek_token(self):
        """ Peek just the token in the generator """
        return self._xyzzy(self.peek, 0)

    @property
    def peek_value(self):
        """ Peek just the value in the generator """
        return self._xyzzy(self.peek, 1)

    def __iter__(self):
        while True:
            yield self.next()

    def next(self):
        if self.peeked_value is not self.NONE:
            peeked_value, self.peeked_value = self.peeked_value, self.NONE
            return peeked_value
        else:
            return self.generator.next()

def GeneratorWithoutLast(generator):
    """
    Pygments has a nasty property that it adds a new-line at the end of the
    parsed token list. This generator wrapper drops the last token in the stream.
    """
    last = generator.next()
    for val in generator:
        yield last
        last = val

def get_lexer(text, lexer):
    return TokenGenerator(GeneratorWithoutLast(lex(text, lexer())))

def document_lexer(text, lexer):
    return get_lexer(text, lexer)

class Node(object):
    def __init__(self, value=None):
        self.value = value
        self.parent = None
        self.children = []

    def append(self, node):
        if node:
            node.parent = self
            self.children.append(node)

    def __iter__(self):
        for child in self.children:
            yield child

    def __repr__(self):
        return "<Node(%s)>" % self.__class__.__name__

class DocumentNode(Node):
    pass

class ParagraphNode(Node):
    pass

class TextNode(Node):
    pass

class LiteralNode(Node):
    pass

class CommentNode(Node):
    pass

class InlineTagNode(Node):
    pass

class SelfClosingTagNode(Node):
    pass

class BlockTagNode(Node):
    pass

def accept_token(token_stream, token):
    return token_stream.peek_token == token

def skip_token(token_stream):
    token_stream.next()

def walk(root, indent=0):
    for node in root:
        if indent:
            print " "*(4*indent), node, node.value
        else:
            print node, node.value
        walk(node, indent+1)


########NEW FILE########
__FILENAME__ = payments
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#

from werkzeug import Response
from catonmat.models import PayPalPayments

def awk_book(request):
    PayPalPayments('awk_book', request).save()
    return Response('ok')

def awk_book_995(request):
    PayPalPayments('awk_book_995', request).save()
    return Response('ok')

def awk_book_shantanu(request):
    PayPalPayments('awk_book_shantanu', request).save()
    return Response('ok')

def sed_book(request):
    PayPalPayments('sed_book', request).save()
    return Response('ok')

def sed_book_shantanu(request):
    PayPalPayments('sed_book_shantanu', request).save()
    return Response('ok')

def perl_book(request):
    PayPalPayments('perl_book', request).save()
    return Response('ok')


########NEW FILE########
__FILENAME__ = quotelist
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website. See this post for more info:
# http://www.catonmat.net/blog/50-ideas-for-the-new-catonmat-website/
#
# Code is licensed under GNU GPL license.
#

class Quote(object):
    def __init__(self, quote, author):
        self.quote = quote
        self.author = author

    def __repr__(self):
        return "<quote by %s>" % self.author

# TODO:
# http://stackoverflow.com/questions/58640/great-programming-quotes

quotes = (
    Quote("Person who say it cannot be done should not interrupt person doing it.", "Chinese Proverb"),
    Quote("Being an expert in XML is like being an expert in comma-separated values.", "Terence Parr"),
    Quote("The error message is God.", "mjd"),
    Quote("If you lie to the compiler, it will get its revenge.", "Henry Spencer"), 
    Quote("Trying to outsmart a compiler defeats much of the purpose of using one.", "Kernighan & Plauger"), 
    Quote("It's hard enough to find an error in your code when you're looking for it; it's even harder when you've assumed your code is error-free.", "Steve McConnell"), 
    Quote("If builders built buildings the way programmers wrote programs, then the first woodpecker that came along would destroy civilisation.", "Gerald Weinberg"), 
    Quote("Programming can be fun, so can cryptography; however they should not be combined.", "Kreitzberg and Shneiderman"), 
    Quote("Once a new technology starts rolling, if you're not part of the steamroller, you're part of the road.", "Stewart Brand"), 
    Quote("The truth does not change according to our ability to stomach it.", "Flannery O'Connor"), 
    Quote("Let us change our traditional attitude to the construction of programs. Instead of imagining that our main task is to instruct a computer what to to, let us concentrate rather on explaining to human beings what we want a computer to do.", "Donald Knuth"), 
    Quote("Beware of bugs in the above code; I have only proved it correct, not tried it.", "Donald Knuth"), 
    Quote("Computers are good at following instructions, but not at reading your mind.", "Donald Knuth"), 
    Quote("The designer of a new system must not only be the implementor and the first large-scale user; the designer should also write the first user manual.", "Donald Knuth"), 
    Quote("Any inaccuracies in this index may be explained by the fact that it has been sorted with the help of a computer.", "Donald Knuth"), 
    Quote("TeX has found at least one bug in every Pascal compiler it's been run on, I think, and at least two in every C compiler.", "Donald Knuth"), 
    Quote("The process of preparing programs for a digital computer is especially attractive, not only because it can be economically and scientifically rewarding, but also because it can be an aesthetic experience much like composing poetry or music.", "Donald Knuth"), 
    Quote("You're bound to be unhappy if you optimize everything.", "Donald Knuth"), 
    Quote("These machines have no common sense; they have not yet learned to 'think,' and they do exactly as they are told, no more and no less. This fact is the hardest concept to grasp when one first tries to use a computer.", "Donald Knuth"), 
    Quote("We should forget about small efficiencies, say about 97% of the time: premature optimization is the root of all evil.", "Donald Knuth"), 
    Quote("Good code is its own best documentation. As you're about to add a comment, ask yourself, 'How can I improve the code so that this comment isn't needed?' Improve the code and then document it to make it even clearer.", "Steve McConnell"), 
    Quote("The trouble with the world is that the stupid are cocksure and the intelligent are full of doubt.", "Bertrand Russell"), 
    Quote("A charlatan makes obscure what is clear; a thinker makes clear what is obscure.", "Hugh Kingsmill"), 
    Quote("Unformed people delight in the gaudy and in novelty. Cooked people delight in the ordinary.", "Erik Naggum"), 
    Quote("An organisation that treats its programmers as morons will soon have programmers that are willing and able to act like morons only.", "Bjarne Stroustrup"), 
    Quote("Measuring programming progress by lines of code is like measuring aircraft building progress by weight.", "Bill Gates"), 
    Quote("The first 90% of the code accounts for the first 90% of the development time. The remaining 10% of the code accounts for the other 90% of the development time.", "Tom Cargill"), 
    Quote("Before software can be reusable it first has to be usable.", "Ralph Johnson"), 
    Quote("Programmers are in a race with the Universe to create bigger and better idiot-proof programs, while the Universe is trying to create bigger and better idiots. So far the Universe is winning.", "Anon"), 
    Quote("Two things are infinite: the universe and human stupidity; and I'm not sure about the universe.", "Albert Einstein"), 
    Quote("Just because the standard provides a cliff in front of you, you are not necessarily required to jump off it.", "Norman Diamond"), 
    Quote("But in our enthusiasm, we could not resist a radical overhaul of the system, in which all of its major weaknesses have been exposed, analyzed, and replaced with new weaknesses.", "Bruce Leverett"), 
    Quote("The best performance improvement is the transition from the nonworking state to the working state ", "John Ousterhout"), 
    Quote("Real computer scientists despise the idea of actual hardware. Hardware has limitations, software doesn't. It's a real shame that Turing machines are so poor at I/O.", "Anon"), 
    Quote("There are only two industries that refer to their customers as 'users'.", "Edward Tufte"), 
    Quote("Debugging a Direct3D application can be challenging.", "Microsoft's Direct3D Immediate Mode overview."), 
    Quote("There are two ways to write error-free programs; only the third works.", "Alan J. Perlis"), 
    Quote("To many managers, getting rid of the arrogant, undisciplined, over-paid, technology-obsessed, improperly-dressed programmers would appear to be a significant added benefit.", "Bjarne Stroustrup"), 
    Quote("I did say something along the lines of 'C makes it easy to shoot yourself in the foot; C++ makes it harder, but when you do, it blows your whole leg off.' ", "Bjarne Stroustrup"), 
    Quote("I have always wished that my computer would be as easy to use as my telephone. My wish has come true. I no longer know how to use my telephone.", "Bjarne Stroustrup"), 
    Quote("The most important single aspect of software development is to be clear about what you are trying to build.", "Bjarne Stroustrup"), 
    Quote("If you think your management doesn't know what it's doing or that your organisation turns out low-quality software crap that embarrasses you, then leave.", "Edward Yourdon"), 
    Quote("Most of you are familiar with the virtues of a programmer. There are three, of course: laziness, impatience, and hubris.", "Larry Wall"), 
    Quote("It has been said that the great scientific disciplines are examples of giants standing on the shoulders of other giants. It has also been said that the software industry is an example of midgets standing on the toes of other midgets.", "Alan Cooper"), 
    Quote("The road to wisdom? Well its plain and simple to express: Err and err and err again,	but less and less and less.", "Piet Hein"), 
    Quote("There are perhaps 5% of the population that simply *can't* think. There are another 5% who *can*, and *do*. The remaining 90% *can* think, but *don't*.", "R. A. Heinlein"), 
    Quote("Lord, give us the wisdom to utter words that are gentle and tender, for tomorrow we may have to eat them.", "Sen. Morris Udall"), 
    Quote("Do not worry about your difficulties in mathematics, I assure you that mine are greater.", "Einstein"), 
    Quote("Computers are useless. They can only give you answers.", "Pablo Picasso"), 
    Quote("Theory is when you know something, but it doesn't work. Practice is when something works, but you don't know why. Programmers combine theory and practice: Nothing works and they don't know why.", "unknown"), 
    Quote("I really hate this damned machine. I wish that they would sell it. It never does quite what I want. But only what I tell it.", "A Programmer's Lament"), 
    Quote("UNIX is simple. It just takes a genius to understand its simplicity.", "Dennis Ritchie"), 
    Quote("When someone says, 'I want a programming language in which I need only say what I want done,' give him a lollipop.", "Alan Perlis"), 
    Quote("For every complex problem there is an answer that is clear, simple, and wrong.", "H L Mencken"), 
    Quote("One of the main causes of the fall of the Roman Empire was that, lacking zero, they had no way to indicate successful termination of their C programs.", "Robert Firth"), 
    Quote("Haste is of the devil. Slowness is of God.", "H L Mencken"), 
    Quote("If the code and the comments disagree, then both are probably wrong.", "Norm Schryer"), 
    Quote("Good programmers use their brains, but good guidelines save us having to think out every case.", "Francis Glassborow"), 
    Quote("Never ascribe to malice that which is adequately explained by incompetence ", "Napoleon Bonaparte"), 
    Quote("Sufficiently advanced incompetence is indistinguishable from malice.", "unknown"), 
    Quote("And the users exclaimed with a laugh and a taunt: 'It's just what we asked for but not what we want.' ", "unknown"), 
    Quote("Some problems are so complex that you have to be highly intelligent and well informed just to be undecided about them.", "Laurence J. Peter"), 
    Quote("The Six Phases of a Project: Enthusiasm, Disillusionment, Panic, Search for the Guilty, Punishment of the Innocent, Praise for non-participants.", "unknown"), 
    Quote("Those who cannot remember the past are condemned to repeat it.", "George Santayana"), 
    Quote("Fashion is something barbarous, for it produces innovation without reason and imitation without benefit.", "George Santayana"), 
    Quote("For a sucessful technology, honesty must take precedence over public relations for nature cannot be fooled.", "Richard Feynman"), 
    Quote("The inside of a computer is as dumb as hell but it goes like mad! ", "Richard Feynman"), 
    Quote("A most important, but also most elusive, aspect of any tool is its influence on the habits of those who train themselves in its use. If the tool is a programming language this influence is, whether we like it or not, an influence on our thinking habits.", "Edsger Dijkstra"), 
    Quote("To iterate is human, to recurse divine.", "L. Peter Deutsch"), 
    Quote("There's no sense being exact about something if you don't even know what you're talking about.", "John von Neumann"), 
    Quote("Anyone who considers arithmetical methods of producing random numbers is, of course, in a state of sin.", "John von Neumann"), 
    Quote("There are two ways of constructing a software design. One way is to make it so simple that there are obviously no deficiencies. And the other way is to make it so complicated that there are no obvious deficiencies.", "C.A.R. Hoare"), 
    Quote("The cost of adding a feature isn't just the time it takes to code it. The cost also includes the addition of an obstacle to future expansion. The trick is to pick the features that don't fight each other.", "John Carmack"), 
    Quote("You can't have great software without a great team, and most software teams behave like dysfunctional families.", "Jim McCarthy"), 
    Quote("Even if you're on the right track, you'll get run over if you just sit there.", "Will Rogers"), 
    Quote("That's the thing about people who think they hate computers. What they really hate is lousy programmers.", "Larry Niven"), 
    Quote("That's the thing about people who think they hate computers. What they really hate is lousy programmers.", "Jerry Pournelle"), 
    Quote("Trying to get into the details seems to be a religious issue -- nearly everybody is convinced that every style but their own is ugly and unreadable. Leave out the 'but their own' and they're probably right...", "Jerry Coffin on indentation"), 
    Quote("When you start off by telling those who disagree with you that they are not merely in error but in sin, how much of a dialogue do you expect?", "Thomas Sowell"), 
    Quote("Einstein argued that there must be simplified explanations of nature, because God is not capricious or arbitrary. No such faith comforts the software engineer.", "Fred Brooks, Jr."), 
    Quote("Incompetents invariably make trouble for people other than themselves.", "Larry McMurtry"), 
    Quote("A notation is important for what it leaves out.", "Joseph Stoy"), 
    Quote("As we said in the preface to the first edition, C 'wears well as one's experience with it grows.' With a decade more experience, we still feel that way.", "Brian Kernighan and Dennis Ritchie"), 
    Quote("A mathematician is a machine for turning coffee into theorems.", "Paul Erdos"), 
    Quote("PHP is a minor evil perpetrated and created by incompetent amateurs, whereas Perl is a great and insidious evil, perpetrated by skilled but perverted professionals.", "Jon Ribbens"), 
    Quote("Simplicity is prerequisite for reliability.", "Edsger W.Dijkstra"), 
    Quote("I've finally learned what 'upward compatible' means. It means we get to keep all our old mistakes.", "Dennie van Tassel"), 
    Quote("Exceptions relieve the programmer of tedious writing boilerplate code -- without removing the semantics of said code -- and they allow the programmer to arrange the code so that error handling code is more separate from the main program logic.", "Herb Sutter"), 
    Quote("It is difficult to get a man to understand something when his salary depends on his not understanding it.", "Upton Sinclair"), 
    Quote("Some people, when confronted with a problem, think 'I know, I'll use regular expressions.' Now they have two problems.", "Jamie Zawinski"), 
    Quote("The behavior of any bureaucratic organization can best be understood by assuming that it is controlled by a secret cabal of its enemies.", "Robert Conquest's Second Law of Politics"), 
    Quote("Power is the ability to control things, moral authority is the ability to change things ", "Jim Wallis"), 
    Quote("The open secrets of good design practice include the importance of knowing what to keep whole, what to combine, what to separate, and what to throw away.", "Kevlin Henny"), 
    Quote("Rules of Optimization: Rule 1: Don't do it. Rule 2 (for experts only): Don't do it yet.", "M.A. Jackson"), 
    Quote("More computing sins are committed in the name of efficiency (without necessarily achieving it) than for any other single reason - including blind stupidity.", "W.A. Wulf"), 
    Quote("The best is the enemy of the good.", "Voltaire"), 
    Quote("There's a fine line between being on the leading edge and being in the lunatic fringe.", "Frank Armstrong"), 
    Quote("The pessimist complains about the wind; the optimist expects it to change; the realist adjusts the sails.", "William Arthur Ward"), 
    Quote("Good judgement comes from experience, and experience comes from bad judgement.", "Fred Brooks"), 
    Quote("Plan to throw one away, you will anyhow.", "Fred Brooks"), 
    Quote("If you plan to throw one away, you will throw away two.", "Craig Zerouni"), 
    Quote("Learning is not compulsory. Neither is survival.", "W. Edwards Deming"), 
    Quote("C++ tries to guard against Murphy, not Machiavelli.", "Damian Conway"), 
    Quote("I have always found that plans are useless, but planning is indispensable.", "Dwight Eisenhower"), 
    Quote("We are tied down to a language which makes up in obscurity what it lacks in style.", "Tom Stoppard"), 
    Quote("They always say time changes things, but you actually have to change them yourself.", "Andy Warhol"), 
    Quote("We only acknowledge small faults in order to make it appear that we are free from great ones.", "La Rochefoucauld"), 
    Quote("Most software today is very much like an Egyptian pyramid with millions of bricks piled on top of each other, with no structural integrity, but just done by brute force and thousands of slaves.", "Alan Kay"), 
    Quote("We all agree on the necessity of compromise. We just can't agree on when it's necessary to compromise.", "Larry Wall"), 
    Quote("Perl is another example of filling a tiny, short-term need, and then being a real problem in the longer term.", "Alan Kay"), 
    Quote("The competent programmer is fully aware of the strictly limited size of his own skull; therefore he approaches the programming task in full humility, and among other things he avoids clever tricks like the plague.", "Edsger Dijkstra"), 
    Quote("It is practically impossible to teach good programming style to students that have had prior exposure to Basic; as potential programmers they are mentally mutilated beyond hope of regeneration.", "Edsger Dijkstra"), 
    Quote("We are apt to shut our eyes against a painful truth.... For my part, I am willing to know the whole truth; to know the worst; and to provide for it.", "Patrick Henry"), 
    Quote("A non-virtual function says, you have to do this and you must do it this way. A virtual function says you have to do this, but you don't have to do it this way. That's their fundamental difference.", "Scott Meyers"), 
    Quote("Comparing to another activity is useful if it helps you formulate questions, it's dangerous when you use it to justify answers.", "Martin Fowler"), 
    Quote("Correctness is clearly the prime quality. If a system does not do what it is supposed to do, then everything else about it matters little.", "Bertrand Meyer"), 
    Quote("An API that isn't comprehensible isn't usable.", "James Gosling"), 
    Quote("Style distinguishes excellence from accomplishment.", "James Coplien"), 
    Quote("You know you've achieved perfection in design, not when you have nothing more to add, but when you have nothing more to take away.", "Antoine de Saint-Exupery, Wind, Sand and Stars"), 
    Quote("It always takes longer than you expect, even when you take into account Hofstadter's Law.", "Hofstadter's Law"), 
    Quote("The ability to simplify means to eliminate the unnecessary so that the necessary may speak.", "Hans Hoffmann"), 
    Quote("Simplicity carried to the extreme becomes elegance.", "Jon Franklin"), 
    Quote("Simplicity is the ultimate sophistication.", "Leonardo da Vinci"), 
    Quote("It's so easy to become mesmerized by the immediacy of a result that you don't question its validity.", "Naomi Karten"), 
    Quote("Every program has (at least) two purposes: the one for which it was written, and another for which it wasn't.", "Alan J. Perlis"), 
    Quote("Elegance is not optional ", "Richard O'Keefe"), 
    Quote("The most amazing achievement of the computer software industry is its continuing cancellation of the steady and staggering gains made by the computer hardware industry.", "Henry Petroski"), 
    Quote("Technology is dominated by two types of people: Those who understand what they do not manage. Those who manage what they do not understand.", "Putt's Law"), 
    Quote("Copy and paste is a design error ", "David Parnas"), 
    Quote("There is not now, nor has there ever been, nor will there ever be, any programming language in which it is the least bit difficult to write bad code.", "Flon's Law"), 
    Quote("Any code of your own that you haven't looked at for six or more months might as well have been written by someone else.", "Eagleson's law"), 
    Quote("If you can't be a good example, then you'll just have to be a horrible warning.", "Catherine Aird"), 
    Quote("Alas, to wear the mantle of Galileo it is not enough that you be persecuted by an unkind establishment, you must also be right.", "Bob Park"), 
    Quote("Any fool can use a computer. Many do.", "Ted Nelson"), 
    Quote("Say what you will about the Ten Commandments, you must always come back to the pleasant fact that there are only ten of them.", "H. L. Mencken"), 
    Quote("Incorrect documentation is often worse than no documentation.", "Bertrand Meyer"), 
    Quote("Debugging is twice as hard as writing the code in the first place. Therefore, if you write the code as cleverly as possible, you are, by definition, not smart enough to debug it.", "Brian W. Kernighan"), 
    Quote("If the lessons of history teach us anything it is that nobody learns the lessons that history teaches us.", "unknown"), 
    Quote("The primary duty of an exception handler is to get the error out of the lap of the programmer and into the surprised face of the user. Provided you keep this cardinal rule in mind, you can't go far wrong.", "Verity Stob"), 
    Quote("If you want a product with certain characteristics, you must ensure that the team has those characteristics before the product's development.", "Jim and Michele McCarthy"), 
    Quote("Organizations which design systems are constrained to produce designs which are copies of the communication structures of these organizations. (For example, if you have four groups working on a compiler, you'll get a 4-pass compiler)", "Damien Conway (Conway's Law)"), 
    Quote("It's not at all important to get it right the first time. It's vitally important to get it right the last time.", "Andrew Hunt and David Thomas")
)


########NEW FILE########
__FILENAME__ = search
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#

from catonmat.thirdparty.sphinxapi          import SphinxClient

# ----------------------------------------------------------------------------

class SearchError(Exception):
    pass


def search(query, index):
    sc = SphinxClient()
    sc.SetServer('localhost', 9312)
    result = sc.Query(query, index)
    if not result:
        raise SearchError(sc.GetLastError())
    return result


########NEW FILE########
__FILENAME__ = similarity
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#

from catonmat.config            import config
from catonmat.cache             import cache
from catonmat.models            import Page, BlogPage, session, page_tags_table

from collections                import defaultdict

# ----------------------------------------------------------------------------

def jaccard_metric(s1, s2):
    return (len(s1.intersection(s2)) + 0.0)/len(s1.union(s2))


def simple_metric(s1, s2):
    return len(s1.intersection(s2))


def related_posts(post, n=10):
    posts_tags = get_posts_tags()
    this_post_tags = set(posts_tags[post.page_id])
    similarity = []
    for page_id in posts_tags:
        if page_id == post.page_id:
            continue
        score = jaccard_metric(this_post_tags, set(posts_tags[page_id]))
        similarity.append([page_id, score])
    top = sorted(similarity, key=lambda (page_id, score): score, reverse=True)
    for_in = []
    found = 0
    for page_id, score in top:
        if score == 0: break
        if session.query(BlogPage).filter_by(page_id=page_id).count() == 0:
            continue
        for_in.append(page_id)
        found = found + 1
        if found == n:
            break
    ret = []
    if for_in:
        pages = session.query(Page).join(BlogPage).filter(Page.page_id.in_(for_in)).all()
        d = dict([p.page_id, p] for p in pages)
        return [d[id] for id in for_in]
    return []


@cache('posts_tags')
def get_posts_tags():
    posts_tags = session.query(page_tags_table).all()
    ret = defaultdict(list)
    for page_id, tag_id in posts_tags:
        ret[page_id].append(tag_id)
    return ret


########NEW FILE########
__FILENAME__ = statistics
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# Code is licensed under MIT license.
#

from catonmat.database          import session
from catonmat.models            import Page, Download, BlogPage

from sqlalchemy                 import func
from calendar                   import month_name as MONTH


# ----------------------------------------------------------------------------

def get_most_popular_pages(count=10):
    return session. \
             query(Page). \
             join(BlogPage). \
             order_by(Page.views.desc()). \
             limit(count). \
             all()


def get_most_downloads(count=10):
    return session. \
             query(Download). \
             order_by(Download.downloads.desc()). \
             limit(count). \
             all()


def get_recent_pages(count=10):
    return session. \
             query(Page). \
             join(BlogPage). \
             order_by(BlogPage.publish_date.desc()). \
             limit(count). \
             all()


def get_post_archive():
    fy = func.year
    fm = func.month
    bp = BlogPage.publish_date
    ymc = session. \
             query(fy(bp), fm(bp), func.count()). \
             group_by(fy(bp), fm(bp)). \
             order_by(fy(bp).desc()). \
             order_by(fm(bp).desc()). \
             all()
    for y, m, c in ymc:
        yield y, m, MONTH[m], c


########NEW FILE########
__FILENAME__ = sphinxapi
#
# $Id: sphinxapi.py 2055 2009-11-06 23:09:58Z shodan $
#
# Python version of Sphinx searchd client (Python API)
#
# Copyright (c) 2006-2008, Andrew Aksyonoff
# Copyright (c) 2006, Mike Osadnik
# All rights reserved
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License. You should have
# received a copy of the GPL license along with this program; if you
# did not, you can find it at http://www.gnu.org/
#

import sys
import select
import socket
import re
from struct import *


# known searchd commands
SEARCHD_COMMAND_SEARCH	= 0
SEARCHD_COMMAND_EXCERPT	= 1
SEARCHD_COMMAND_UPDATE	= 2
SEARCHD_COMMAND_KEYWORDS= 3
SEARCHD_COMMAND_PERSIST	= 4

# current client-side command implementation versions
VER_COMMAND_SEARCH		= 0x116
VER_COMMAND_EXCERPT		= 0x100
VER_COMMAND_UPDATE		= 0x101
VER_COMMAND_KEYWORDS	= 0x100

# known searchd status codes
SEARCHD_OK				= 0
SEARCHD_ERROR			= 1
SEARCHD_RETRY			= 2
SEARCHD_WARNING			= 3

# known match modes
SPH_MATCH_ALL			= 0
SPH_MATCH_ANY			= 1
SPH_MATCH_PHRASE		= 2
SPH_MATCH_BOOLEAN		= 3
SPH_MATCH_EXTENDED		= 4
SPH_MATCH_FULLSCAN		= 5
SPH_MATCH_EXTENDED2		= 6

# known ranking modes (extended2 mode only)
SPH_RANK_PROXIMITY_BM25	= 0 # default mode, phrase proximity major factor and BM25 minor one
SPH_RANK_BM25			= 1 # statistical mode, BM25 ranking only (faster but worse quality)
SPH_RANK_NONE			= 2 # no ranking, all matches get a weight of 1
SPH_RANK_WORDCOUNT		= 3 # simple word-count weighting, rank is a weighted sum of per-field keyword occurence counts

# known sort modes
SPH_SORT_RELEVANCE		= 0
SPH_SORT_ATTR_DESC		= 1
SPH_SORT_ATTR_ASC		= 2
SPH_SORT_TIME_SEGMENTS	= 3
SPH_SORT_EXTENDED		= 4
SPH_SORT_EXPR			= 5

# known filter types
SPH_FILTER_VALUES		= 0
SPH_FILTER_RANGE		= 1
SPH_FILTER_FLOATRANGE	= 2

# known attribute types
SPH_ATTR_NONE			= 0
SPH_ATTR_INTEGER		= 1
SPH_ATTR_TIMESTAMP		= 2
SPH_ATTR_ORDINAL		= 3
SPH_ATTR_BOOL			= 4
SPH_ATTR_FLOAT			= 5
SPH_ATTR_BIGINT			= 6
SPH_ATTR_MULTI			= 0X40000000L

SPH_ATTR_TYPES = (SPH_ATTR_NONE,
				  SPH_ATTR_INTEGER,
				  SPH_ATTR_TIMESTAMP,
				  SPH_ATTR_ORDINAL,
				  SPH_ATTR_BOOL,
				  SPH_ATTR_FLOAT,
				  SPH_ATTR_BIGINT,
				  SPH_ATTR_MULTI)

# known grouping functions
SPH_GROUPBY_DAY	 		= 0
SPH_GROUPBY_WEEK		= 1
SPH_GROUPBY_MONTH		= 2
SPH_GROUPBY_YEAR		= 3
SPH_GROUPBY_ATTR		= 4
SPH_GROUPBY_ATTRPAIR	= 5


class SphinxClient:
	def __init__ (self):
		"""
		Create a new client object, and fill defaults.
		"""
		self._host			= 'localhost'					# searchd host (default is "localhost")
		self._port			= 9312							# searchd port (default is 9312)
		self._path			= None							# searchd unix-domain socket path
		self._socket		= None
		self._offset		= 0								# how much records to seek from result-set start (default is 0)
		self._limit			= 20							# how much records to return from result-set starting at offset (default is 20)
		self._mode			= SPH_MATCH_ALL					# query matching mode (default is SPH_MATCH_ALL)
		self._weights		= []							# per-field weights (default is 1 for all fields)
		self._sort			= SPH_SORT_RELEVANCE			# match sorting mode (default is SPH_SORT_RELEVANCE)
		self._sortby		= ''							# attribute to sort by (defualt is "")
		self._min_id		= 0								# min ID to match (default is 0)
		self._max_id		= 0								# max ID to match (default is UINT_MAX)
		self._filters		= []							# search filters
		self._groupby		= ''							# group-by attribute name
		self._groupfunc		= SPH_GROUPBY_DAY				# group-by function (to pre-process group-by attribute value with)
		self._groupsort		= '@group desc'					# group-by sorting clause (to sort groups in result set with)
		self._groupdistinct	= ''							# group-by count-distinct attribute
		self._maxmatches	= 1000							# max matches to retrieve
		self._cutoff		= 0								# cutoff to stop searching at
		self._retrycount	= 0								# distributed retry count
		self._retrydelay	= 0								# distributed retry delay
		self._anchor		= {}							# geographical anchor point
		self._indexweights	= {}							# per-index weights
		self._ranker		= SPH_RANK_PROXIMITY_BM25		# ranking mode
		self._maxquerytime	= 0								# max query time, milliseconds (default is 0, do not limit)
		self._fieldweights	= {}							# per-field-name weights
		self._overrides		= {}							# per-query attribute values overrides
		self._select		= '*'							# select-list (attributes or expressions, with optional aliases)
		
		self._error			= ''							# last error message
		self._warning		= ''							# last warning message
		self._reqs			= []							# requests array for multi-query

	def __del__ (self):
		if self._socket:
			self._socket.close()


	def GetLastError (self):
		"""
		Get last error message (string).
		"""
		return self._error


	def GetLastWarning (self):
		"""
		Get last warning message (string).
		"""
		return self._warning


	def SetServer (self, host, port = None):
		"""
		Set searchd server host and port.
		"""
		assert(isinstance(host, str))
		if host.startswith('/'):
			self._path = host
			return
		elif host.startswith('unix://'):
			self._path = host[7:]
			return
		assert(isinstance(port, int))
		self._host = host
		self._port = port
		self._path = None

					
	def _Connect (self):
		"""
		INTERNAL METHOD, DO NOT CALL. Connects to searchd server.
		"""
		if self._socket:
			# we have a socket, but is it still alive?
			sr, sw, _ = select.select ( [self._socket], [self._socket], [], 0 )

			# this is how alive socket should look
			if len(sr)==0 and len(sw)==1:
				return self._socket

			# oops, looks like it was closed, lets reopen
			self._socket.close()
			self._socket = None

		try:
			if self._path:
				af = socket.AF_UNIX
				addr = self._path
				desc = self._path
			else:
				af = socket.AF_INET
				addr = ( self._host, self._port )
				desc = '%s;%s' % addr
			sock = socket.socket ( af, socket.SOCK_STREAM )
			sock.connect ( addr )
		except socket.error, msg:
			if sock:
				sock.close()
			self._error = 'connection to %s failed (%s)' % ( desc, msg )
			return

		v = unpack('>L', sock.recv(4))
		if v<1:
			sock.close()
			self._error = 'expected searchd protocol version, got %s' % v
			return

		# all ok, send my version
		sock.send(pack('>L', 1))
		return sock


	def _GetResponse (self, sock, client_ver):
		"""
		INTERNAL METHOD, DO NOT CALL. Gets and checks response packet from searchd server.
		"""
		(status, ver, length) = unpack('>2HL', sock.recv(8))
		response = ''
		left = length
		while left>0:
			chunk = sock.recv(left)
			if chunk:
				response += chunk
				left -= len(chunk)
			else:
				break

		if not self._socket:
			sock.close()

		# check response
		read = len(response)
		if not response or read!=length:
			if length:
				self._error = 'failed to read searchd response (status=%s, ver=%s, len=%s, read=%s)' \
					% (status, ver, length, read)
			else:
				self._error = 'received zero-sized searchd response'
			return None

		# check status
		if status==SEARCHD_WARNING:
			wend = 4 + unpack ( '>L', response[0:4] )[0]
			self._warning = response[4:wend]
			return response[wend:]

		if status==SEARCHD_ERROR:
			self._error = 'searchd error: '+response[4:]
			return None

		if status==SEARCHD_RETRY:
			self._error = 'temporary searchd error: '+response[4:]
			return None

		if status!=SEARCHD_OK:
			self._error = 'unknown status code %d' % status
			return None

		# check version
		if ver<client_ver:
			self._warning = 'searchd command v.%d.%d older than client\'s v.%d.%d, some options might not work' \
				% (ver>>8, ver&0xff, client_ver>>8, client_ver&0xff)

		return response


	def SetLimits (self, offset, limit, maxmatches=0, cutoff=0):
		"""
		Set offset and count into result set, and optionally set max-matches and cutoff limits.
		"""
		assert ( type(offset) in [int,long] and 0<=offset<16777216 )
		assert ( type(limit) in [int,long] and 0<limit<16777216 )
		assert(maxmatches>=0)
		self._offset = offset
		self._limit = limit
		if maxmatches>0:
			self._maxmatches = maxmatches
		if cutoff>=0:
			self._cutoff = cutoff


	def SetMaxQueryTime (self, maxquerytime):
		"""
		Set maximum query time, in milliseconds, per-index. 0 means 'do not limit'.
		"""
		assert(isinstance(maxquerytime,int) and maxquerytime>0)
		self._maxquerytime = maxquerytime


	def SetMatchMode (self, mode):
		"""
		Set matching mode.
		"""
		assert(mode in [SPH_MATCH_ALL, SPH_MATCH_ANY, SPH_MATCH_PHRASE, SPH_MATCH_BOOLEAN, SPH_MATCH_EXTENDED, SPH_MATCH_FULLSCAN, SPH_MATCH_EXTENDED2])
		self._mode = mode


	def SetRankingMode (self, ranker):
		"""
		Set ranking mode.
		"""
		assert(ranker in [SPH_RANK_PROXIMITY_BM25, SPH_RANK_BM25, SPH_RANK_NONE, SPH_RANK_WORDCOUNT])
		self._ranker = ranker


	def SetSortMode ( self, mode, clause='' ):
		"""
		Set sorting mode.
		"""
		assert ( mode in [SPH_SORT_RELEVANCE, SPH_SORT_ATTR_DESC, SPH_SORT_ATTR_ASC, SPH_SORT_TIME_SEGMENTS, SPH_SORT_EXTENDED, SPH_SORT_EXPR] )
		assert ( isinstance ( clause, str ) )
		self._sort = mode
		self._sortby = clause


	def SetWeights (self, weights): 
		"""
		Set per-field weights.
		WARNING, DEPRECATED; do not use it! use SetFieldWeights() instead
		"""
		assert(isinstance(weights, list))
		for w in weights:
			assert(isinstance(w, int))
		self._weights = weights


	def SetFieldWeights (self, weights):
		"""
		Bind per-field weights by name; expects (name,field_weight) dictionary as argument.
		"""
		assert(isinstance(weights,dict))
		for key,val in weights.items():
			assert(isinstance(key,str))
			assert(isinstance(val,int))
		self._fieldweights = weights


	def SetIndexWeights (self, weights):
		"""
		Bind per-index weights by name; expects (name,index_weight) dictionary as argument.
		"""
		assert(isinstance(weights,dict))
		for key,val in weights.items():
			assert(isinstance(key,str))
			assert(isinstance(val,int))
		self._indexweights = weights


	def SetIDRange (self, minid, maxid):
		"""
		Set IDs range to match.
		Only match records if document ID is beetwen $min and $max (inclusive).
		"""
		assert(isinstance(minid, (int, long)))
		assert(isinstance(maxid, (int, long)))
		assert(minid<=maxid)
		self._min_id = minid
		self._max_id = maxid


	def SetFilter ( self, attribute, values, exclude=0 ):
		"""
		Set values set filter.
		Only match records where 'attribute' value is in given 'values' set.
		"""
		assert(isinstance(attribute, str))
		assert iter(values)

		for value in values:
			assert(isinstance(value, int))

		self._filters.append ( { 'type':SPH_FILTER_VALUES, 'attr':attribute, 'exclude':exclude, 'values':values } )


	def SetFilterRange (self, attribute, min_, max_, exclude=0 ):
		"""
		Set range filter.
		Only match records if 'attribute' value is beetwen 'min_' and 'max_' (inclusive).
		"""
		assert(isinstance(attribute, str))
		assert(isinstance(min_, int))
		assert(isinstance(max_, int))
		assert(min_<=max_)

		self._filters.append ( { 'type':SPH_FILTER_RANGE, 'attr':attribute, 'exclude':exclude, 'min':min_, 'max':max_ } )


	def SetFilterFloatRange (self, attribute, min_, max_, exclude=0 ):
		assert(isinstance(attribute,str))
		assert(isinstance(min_,float))
		assert(isinstance(max_,float))
		assert(min_ <= max_)
		self._filters.append ( {'type':SPH_FILTER_FLOATRANGE, 'attr':attribute, 'exclude':exclude, 'min':min_, 'max':max_} ) 


	def SetGeoAnchor (self, attrlat, attrlong, latitude, longitude):
		assert(isinstance(attrlat,str))
		assert(isinstance(attrlong,str))
		assert(isinstance(latitude,float))
		assert(isinstance(longitude,float))
		self._anchor['attrlat'] = attrlat
		self._anchor['attrlong'] = attrlong
		self._anchor['lat'] = latitude
		self._anchor['long'] = longitude


	def SetGroupBy ( self, attribute, func, groupsort='@group desc' ):
		"""
		Set grouping attribute and function.
		"""
		assert(isinstance(attribute, str))
		assert(func in [SPH_GROUPBY_DAY, SPH_GROUPBY_WEEK, SPH_GROUPBY_MONTH, SPH_GROUPBY_YEAR, SPH_GROUPBY_ATTR, SPH_GROUPBY_ATTRPAIR] )
		assert(isinstance(groupsort, str))

		self._groupby = attribute
		self._groupfunc = func
		self._groupsort = groupsort


	def SetGroupDistinct (self, attribute):
		assert(isinstance(attribute,str))
		self._groupdistinct = attribute


	def SetRetries (self, count, delay=0):
		assert(isinstance(count,int) and count>=0)
		assert(isinstance(delay,int) and delay>=0)
		self._retrycount = count
		self._retrydelay = delay


	def SetOverride (self, name, type, values):
		assert(isinstance(name, str))
		assert(type in SPH_ATTR_TYPES)
		assert(isinstance(values, dict))

		self._overrides[name] = {'name': name, 'type': type, 'values': values}

	def SetSelect (self, select):
		assert(isinstance(select, str))
		self._select = select


	def ResetOverrides (self):
		self._overrides = {}


	def ResetFilters (self):
		"""
		Clear all filters (for multi-queries).
		"""
		self._filters = []
		self._anchor = {}


	def ResetGroupBy (self):
		"""
		Clear groupby settings (for multi-queries).
		"""
		self._groupby = ''
		self._groupfunc = SPH_GROUPBY_DAY
		self._groupsort = '@group desc'
		self._groupdistinct = ''


	def Query (self, query, index='*', comment=''):
		"""
		Connect to searchd server and run given search query.
		Returns None on failure; result set hash on success (see documentation for details).
		"""
		assert(len(self._reqs)==0)
		self.AddQuery(query,index,comment)
		results = self.RunQueries()

		if not results or len(results)==0:
			return None
		self._error = results[0]['error']
		self._warning = results[0]['warning']
		if results[0]['status'] == SEARCHD_ERROR:
			return None
		return results[0]


	def AddQuery (self, query, index='*', comment=''):
		"""
		Add query to batch.
		"""
		# build request
		req = [pack('>5L', self._offset, self._limit, self._mode, self._ranker, self._sort)]
		req.append(pack('>L', len(self._sortby)))
		req.append(self._sortby)

		if isinstance(query,unicode):
			query = query.encode('utf-8')
		assert(isinstance(query,str))

		req.append(pack('>L', len(query)))
		req.append(query)

		req.append(pack('>L', len(self._weights)))
		for w in self._weights:
			req.append(pack('>L', w))
		req.append(pack('>L', len(index)))
		req.append(index)
		req.append(pack('>L',1)) # id64 range marker
		req.append(pack('>Q', self._min_id))
		req.append(pack('>Q', self._max_id))
		
		# filters
		req.append ( pack ( '>L', len(self._filters) ) )
		for f in self._filters:
			req.append ( pack ( '>L', len(f['attr'])) + f['attr'])
			filtertype = f['type']
			req.append ( pack ( '>L', filtertype))
			if filtertype == SPH_FILTER_VALUES:
				req.append ( pack ('>L', len(f['values'])))
				for val in f['values']:
					req.append ( pack ('>q', val))
			elif filtertype == SPH_FILTER_RANGE:
				req.append ( pack ('>2q', f['min'], f['max']))
			elif filtertype == SPH_FILTER_FLOATRANGE:
				req.append ( pack ('>2f', f['min'], f['max']))
			req.append ( pack ( '>L', f['exclude'] ) )

		# group-by, max-matches, group-sort
		req.append ( pack ( '>2L', self._groupfunc, len(self._groupby) ) )
		req.append ( self._groupby )
		req.append ( pack ( '>2L', self._maxmatches, len(self._groupsort) ) )
		req.append ( self._groupsort )
		req.append ( pack ( '>LLL', self._cutoff, self._retrycount, self._retrydelay)) 
		req.append ( pack ( '>L', len(self._groupdistinct)))
		req.append ( self._groupdistinct)

		# anchor point
		if len(self._anchor) == 0:
			req.append ( pack ('>L', 0))
		else:
			attrlat, attrlong = self._anchor['attrlat'], self._anchor['attrlong']
			latitude, longitude = self._anchor['lat'], self._anchor['long']
			req.append ( pack ('>L', 1))
			req.append ( pack ('>L', len(attrlat)) + attrlat)
			req.append ( pack ('>L', len(attrlong)) + attrlong)
			req.append ( pack ('>f', latitude) + pack ('>f', longitude))

		# per-index weights
		req.append ( pack ('>L',len(self._indexweights)))
		for indx,weight in self._indexweights.items():
			req.append ( pack ('>L',len(indx)) + indx + pack ('>L',weight))

		# max query time
		req.append ( pack ('>L', self._maxquerytime) ) 

		# per-field weights
		req.append ( pack ('>L',len(self._fieldweights) ) )
		for field,weight in self._fieldweights.items():
			req.append ( pack ('>L',len(field)) + field + pack ('>L',weight) )

		# comment
		req.append ( pack('>L',len(comment)) + comment )

		# attribute overrides
		req.append ( pack('>L', len(self._overrides)) )
		for v in self._overrides.values():
			req.extend ( ( pack('>L', len(v['name'])), v['name'] ) )
			req.append ( pack('>LL', v['type'], len(v['values'])) )
			for id, value in v['values'].iteritems():
				req.append ( pack('>Q', id) )
				if v['type'] == SPH_ATTR_FLOAT:
					req.append ( pack('>f', value) )
				elif v['type'] == SPH_ATTR_BIGINT:
					req.append ( pack('>q', value) )
				else:
					req.append ( pack('>l', value) )

		# select-list
		req.append ( pack('>L', len(self._select)) )
		req.append ( self._select )

		# send query, get response
		req = ''.join(req)

		self._reqs.append(req)
		return


	def RunQueries (self):
		"""
		Run queries batch.
		Returns None on network IO failure; or an array of result set hashes on success.
		"""
		if len(self._reqs)==0:
			self._error = 'no queries defined, issue AddQuery() first'
			return None

		sock = self._Connect()
		if not sock:
			return None

		req = ''.join(self._reqs)
		length = len(req)+4
		req = pack('>HHLL', SEARCHD_COMMAND_SEARCH, VER_COMMAND_SEARCH, length, len(self._reqs))+req
		sock.send(req)

		response = self._GetResponse(sock, VER_COMMAND_SEARCH)
		if not response:
			return None

		nreqs = len(self._reqs)

		# parse response
		max_ = len(response)
		p = 0

		results = []
		for i in range(0,nreqs,1):
			result = {}
			results.append(result)

			result['error'] = ''
			result['warning'] = ''
			status = unpack('>L', response[p:p+4])[0]
			p += 4
			result['status'] = status
			if status != SEARCHD_OK:
				length = unpack('>L', response[p:p+4])[0]
				p += 4
				message = response[p:p+length]
				p += length

				if status == SEARCHD_WARNING:
					result['warning'] = message
				else:
					result['error'] = message
					continue

			# read schema
			fields = []
			attrs = []

			nfields = unpack('>L', response[p:p+4])[0]
			p += 4
			while nfields>0 and p<max_:
				nfields -= 1
				length = unpack('>L', response[p:p+4])[0]
				p += 4
				fields.append(response[p:p+length])
				p += length

			result['fields'] = fields

			nattrs = unpack('>L', response[p:p+4])[0]
			p += 4
			while nattrs>0 and p<max_:
				nattrs -= 1
				length = unpack('>L', response[p:p+4])[0]
				p += 4
				attr = response[p:p+length]
				p += length
				type_ = unpack('>L', response[p:p+4])[0]
				p += 4
				attrs.append([attr,type_])

			result['attrs'] = attrs

			# read match count
			count = unpack('>L', response[p:p+4])[0]
			p += 4
			id64 = unpack('>L', response[p:p+4])[0]
			p += 4
		
			# read matches
			result['matches'] = []
			while count>0 and p<max_:
				count -= 1
				if id64:
					doc, weight = unpack('>QL', response[p:p+12])
					p += 12
				else:
					doc, weight = unpack('>2L', response[p:p+8])
					p += 8

				match = { 'id':doc, 'weight':weight, 'attrs':{} }
				for i in range(len(attrs)):
					if attrs[i][1] == SPH_ATTR_FLOAT:
						match['attrs'][attrs[i][0]] = unpack('>f', response[p:p+4])[0]
					elif attrs[i][1] == SPH_ATTR_BIGINT:
						match['attrs'][attrs[i][0]] = unpack('>q', response[p:p+8])[0]
						p += 4
					elif attrs[i][1] == (SPH_ATTR_MULTI | SPH_ATTR_INTEGER):
						match['attrs'][attrs[i][0]] = []
						nvals = unpack('>L', response[p:p+4])[0]
						p += 4
						for n in range(0,nvals,1):
							match['attrs'][attrs[i][0]].append(unpack('>L', response[p:p+4])[0])
							p += 4
						p -= 4
					else:
						match['attrs'][attrs[i][0]] = unpack('>L', response[p:p+4])[0]
					p += 4

				result['matches'].append ( match )

			result['total'], result['total_found'], result['time'], words = unpack('>4L', response[p:p+16])

			result['time'] = '%.3f' % (result['time']/1000.0)
			p += 16

			result['words'] = []
			while words>0:
				words -= 1
				length = unpack('>L', response[p:p+4])[0]
				p += 4
				word = response[p:p+length]
				p += length
				docs, hits = unpack('>2L', response[p:p+8])
				p += 8

				result['words'].append({'word':word, 'docs':docs, 'hits':hits})
		
		self._reqs = []
		return results
	

	def BuildExcerpts (self, docs, index, words, opts=None):
		"""
		Connect to searchd server and generate exceprts from given documents.
		"""
		if not opts:
			opts = {}
		if isinstance(words,unicode):
			words = words.encode('utf-8')

		assert(isinstance(docs, list))
		assert(isinstance(index, str))
		assert(isinstance(words, str))
		assert(isinstance(opts, dict))

		sock = self._Connect()

		if not sock:
			return None

		# fixup options
		opts.setdefault('before_match', '<b>')
		opts.setdefault('after_match', '</b>')
		opts.setdefault('chunk_separator', ' ... ')
		opts.setdefault('limit', 256)
		opts.setdefault('around', 5)

		# build request
		# v.1.0 req

		flags = 1 # (remove spaces)
		if opts.get('exact_phrase'):	flags |= 2
		if opts.get('single_passage'):	flags |= 4
		if opts.get('use_boundaries'):	flags |= 8
		if opts.get('weight_order'):	flags |= 16
		
		# mode=0, flags
		req = [pack('>2L', 0, flags)]

		# req index
		req.append(pack('>L', len(index)))
		req.append(index)

		# req words
		req.append(pack('>L', len(words)))
		req.append(words)

		# options
		req.append(pack('>L', len(opts['before_match'])))
		req.append(opts['before_match'])

		req.append(pack('>L', len(opts['after_match'])))
		req.append(opts['after_match'])

		req.append(pack('>L', len(opts['chunk_separator'])))
		req.append(opts['chunk_separator'])

		req.append(pack('>L', int(opts['limit'])))
		req.append(pack('>L', int(opts['around'])))

		# documents
		req.append(pack('>L', len(docs)))
		for doc in docs:
			if isinstance(doc,unicode):
				doc = doc.encode('utf-8')
			assert(isinstance(doc, str))
			req.append(pack('>L', len(doc)))
			req.append(doc)

		req = ''.join(req)

		# send query, get response
		length = len(req)

		# add header
		req = pack('>2HL', SEARCHD_COMMAND_EXCERPT, VER_COMMAND_EXCERPT, length)+req
		wrote = sock.send(req)

		response = self._GetResponse(sock, VER_COMMAND_EXCERPT )
		if not response:
			return []

		# parse response
		pos = 0
		res = []
		rlen = len(response)

		for i in range(len(docs)):
			length = unpack('>L', response[pos:pos+4])[0]
			pos += 4

			if pos+length > rlen:
				self._error = 'incomplete reply'
				return []

			res.append(response[pos:pos+length])
			pos += length

		return res


	def UpdateAttributes ( self, index, attrs, values ):
		"""
		Update given attribute values on given documents in given indexes.
		Returns amount of updated documents (0 or more) on success, or -1 on failure.

		'attrs' must be a list of strings.
		'values' must be a dict with int key (document ID) and list of int values (new attribute values).

		Example:
			res = cl.UpdateAttributes ( 'test1', [ 'group_id', 'date_added' ], { 2:[123,1000000000], 4:[456,1234567890] } )
		"""
		assert ( isinstance ( index, str ) )
		assert ( isinstance ( attrs, list ) )
		assert ( isinstance ( values, dict ) )
		for attr in attrs:
			assert ( isinstance ( attr, str ) )
		for docid, entry in values.items():
			assert ( isinstance ( docid, int ) )
			assert ( isinstance ( entry, list ) )
			assert ( len(attrs)==len(entry) )
			for val in entry:
				assert ( isinstance ( val, int ) )

		# build request
		req = [ pack('>L',len(index)), index ]

		req.append ( pack('>L',len(attrs)) )
		for attr in attrs:
			req.append ( pack('>L',len(attr)) + attr )

		req.append ( pack('>L',len(values)) )
		for docid, entry in values.items():
			req.append ( pack('>Q',docid) )
			for val in entry:
				req.append ( pack('>L',val) )

		# connect, send query, get response
		sock = self._Connect()
		if not sock:
			return None

		req = ''.join(req)
		length = len(req)
		req = pack ( '>2HL', SEARCHD_COMMAND_UPDATE, VER_COMMAND_UPDATE, length ) + req
		wrote = sock.send ( req )

		response = self._GetResponse ( sock, VER_COMMAND_UPDATE )
		if not response:
			return -1

		# parse response
		updated = unpack ( '>L', response[0:4] )[0]
		return updated


	def BuildKeywords ( self, query, index, hits ):
		"""
		Connect to searchd server, and generate keywords list for a given query.
		Returns None on failure, or a list of keywords on success.
		"""
		assert ( isinstance ( query, str ) )
		assert ( isinstance ( index, str ) )
		assert ( isinstance ( hits, int ) )

		# build request
		req = [ pack ( '>L', len(query) ) + query ]
		req.append ( pack ( '>L', len(index) ) + index )
		req.append ( pack ( '>L', hits ) )

		# connect, send query, get response
		sock = self._Connect()
		if not sock:
			return None

		req = ''.join(req)
		length = len(req)
		req = pack ( '>2HL', SEARCHD_COMMAND_KEYWORDS, VER_COMMAND_KEYWORDS, length ) + req
		wrote = sock.send ( req )

		response = self._GetResponse ( sock, VER_COMMAND_KEYWORDS )
		if not response:
			return None

		# parse response
		res = []

		nwords = unpack ( '>L', response[0:4] )[0]
		p = 4
		max_ = len(response)

		while nwords>0 and p<max_:
			nwords -= 1

			length = unpack ( '>L', response[p:p+4] )[0]
			p += 4
			tokenized = response[p:p+length]
			p += length

			length = unpack ( '>L', response[p:p+4] )[0]
			p += 4
			normalized = response[p:p+length]
			p += length

			entry = { 'tokenized':tokenized, 'normalized':normalized }
			if hits:
				entry['docs'], entry['hits'] = unpack ( '>2L', response[p:p+8] )
				p += 8

			res.append ( entry )

		if nwords>0 or p>max_:
			self._error = 'incomplete reply'
			return None

		return res

	### persistent connections

	def Open(self):
		if self._socket:
			self._error = 'already connected'
			return
		
		server = self._Connect()
		if not server:
			return

		# command, command version = 0, body length = 4, body = 1
		request = pack ( '>hhII', SEARCHD_COMMAND_PERSIST, 0, 4, 1 )
		server.send ( request )
		
		self._socket = server

	def Close(self):
		if not self._socket:
			self._error = 'not connected'
			return
		self._socket.close()
		self._socket = None
	
	def EscapeString(self, string):
		return re.sub(r"([=\(\)|\-!@~\"&/\\\^\$\=])", r"\\\1", string)

#
# $Id: sphinxapi.py 2055 2009-11-06 23:09:58Z shodan $
#

########NEW FILE########
__FILENAME__ = urls
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under MIT license.
#

from catonmat.views.utils   import MakoDict
from catonmat.cache         import from_cache_or_compute
from catonmat.models        import UrlMap, Redirect
from catonmat.database      import session

from werkzeug.routing       import Map, Rule as RuleBase, Submount

import re

# ----------------------------------------------------------------------------

def agreed_path(request_path):
    request_path = request_path.rstrip('/')
    request_path = re.sub('//+', '/', request_path)
    return request_path


def find_redirect(request_path):
    request_path = agreed_path(request_path)
    cache_key = 'redirect_%s' % request_path
    return from_cache_or_compute(find_redirect_compute, cache_key, 3600, request_path)


def find_redirect_compute(request_path):
    return session.query(Redirect).filter_by(old_path=request_path).first()


def find_url_map(request_path):
    request_path = agreed_path(request_path)
    cache_key = 'not_found_%s' % request_path
    return from_cache_or_compute(find_url_map_compute, cache_key, 3600, request_path)


def find_url_map_compute(request_path):
    url_map = session.query(UrlMap).filter_by(request_path=request_path).first()
    if not url_map:
        return None
    return {
      'url_map_id':   url_map.url_map_id,
      'request_path': url_map.request_path,
      'page_id':      url_map.page_id
    }


class Rule(RuleBase):
    def __gt__(self, endpoint):
        self.endpoint = endpoint
        return self


predefined_urls = Map([
    # Main page
    Rule('/')                          > 'index.main',

    # Pagination
    Rule('/page')                      > 'index.page_list',
    Rule('/pages')                     > 'index.page_list',
    Rule('/page/<int:page_nr>')        > 'index.page',

    # Search
    Rule('/search')                    > 'search.main',

    # Atom feed
    Rule('/feed')                      > 'rss.atom_feed',
    Rule('/feed/atom')                 > 'rss.atom_feed',
    Rule('/feed/rss')                  > 'rss.atom_feed',

    # Blog is alias for Main page right now
    Rule('/blog')                      > 'index.main',

    # Mobile pages
    Rule('/mobile/<path:url>')         > 'mobile.main',

    # Feedback
    Rule('/feedback')                  > 'feedback.main',

    # Sitemap
    Rule('/sitemap')                   > 'sitemap.main',

    # Article Series
    Rule('/series')                    > 'series.main',
    Rule('/series/<seo_name>')         > 'series.single',

    # Categories
    Rule('/category/<seo_name>')       > 'categories.main',
    Rule('/category')                  > 'categories.list',
    Rule('/categories')                > 'categories.list',

    # Tags
    Rule('/tag/<seo_name>')            > 'tags.main',
    Rule('/tag')                       > 'tags.list',
    Rule('/tags')                      > 'tags.list',

    # Article archive
    Rule('/archive')                        > 'archive.main',
    Rule('/archive/<int:year>')             > 'archive.year',
    Rule('/archive/<int:year>/<int:month>') > 'archive.year_month',

    # Programming quotes
    Rule('/quotes')                    > 'quotes.main',

    # Downloads
    Rule('/download/<filename>')       > 'downloads.main',
    Rule('/downloads')                 > 'downloads.all',
    Rule('/blog/wp-content/plugins/wp-downloadMonitor/user_uploads/<filename>') > 'downloads.old_wp_download',
    Rule('/wp-content/plugins/wp-downloadMonitor/user_uploads/<filename>') > 'downloads.old_wp_download',

    # Add and preview comments via AJAX
    Rule('/_services/comment_preview') > 'catonmat.comments.preview_comment',
    Rule('/_services/comment_add')     > 'catonmat.comments.add_comment',

    # Short URL for comments
    Rule('/c/<int:comment_id>')        > 'c.main',

    # Short URL for pages
    Rule('/p/<int:page_id>')           > 'p.main',

    # News
    Rule('/news')                      > 'news.main',

    # Payments
    Rule('/payments/awk_book')         > 'catonmat.payments.awk_book',
    Rule('/payments/awk_book_995')     > 'catonmat.payments.awk_book_995',
    Rule('/payments/awk_book_shantanu') > 'catonmat.payments.awk_book_shantanu',
    Rule('/payments/sed_book')         > 'catonmat.payments.sed_book',
    Rule('/payments/sed_book_shantanu') > 'catonmat.payments.sed_book_shantanu',
    Rule('/payments/perl_book')         > 'catonmat.payments.perl_book',

    # Admin
    Submount('/admin', [
        Rule('/')                      > 'admin.index.main',
        Rule('/login')                 > 'admin.login.main',
        Rule('/pages')                 > 'admin.pages.main',
        Rule('/edit_page/<page_id>')   > 'admin.edit_page.main',
        Rule('/new_page')              > 'admin.new_page.main',
        Rule('/categories')            > 'admin.categories.main',
        Rule('/fof')                   > 'admin.fof.main',
        Rule('/exceptions')            > 'admin.exceptions.main',
    ])
],
strict_slashes=False)


########NEW FILE########
__FILENAME__ = categories
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#

from catonmat.admin             import require_admin
from catonmat.models            import session, Category
from catonmat.views.utils       import display_plain_template

# ----------------------------------------------------------------------------

@require_admin()
def main(request):
    cats = session.query(Category).all()
    return display_plain_template('admin/categories', cats=cats)


########NEW FILE########
__FILENAME__ = edit_page
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#

from werkzeug                   import redirect

from catonmat.models            import session, Page, Category, Revision, Tag, Rss, BlogPage
from catonmat.admin             import require_admin
from catonmat.views.utils       import display_plain_template, MakoDict
from catonmat.views.pages       import default_page_template_data, display_page
from catonmat.cache             import cache_del
from catonmat.config            import config

from datetime                   import datetime

# ----------------------------------------------------------------------------

@require_admin()
def main(request, page_id):
    if request.method == "GET":
        page = session.query(Page).filter_by(page_id=page_id).first()
        cats = session.query(Category).all()
        return display_plain_template('admin/edit_page', page=page, cats=cats)

    if 'submit' in request.form:
        return edit_page_submit(request, page_id)
    elif 'publish' in request.form:
        return publish_page(request, page_id)
    elif 'preview' in request.form:
        return edit_page_preview(request, page_id)


def edit_page_submit(request, page_id):
    page = session.query(Page).filter_by(page_id=page_id).first()
    page_cat = session.query(Category).filter_by(category_id=request.form['cat_id']).first()

    page.title        = request.form['title']
    page.content      = request.form['content']
    page.excerpt      = request.form['excerpt']
    page.request_path = request.form['request_path']
    page.category     = page_cat
    page.last_update  = datetime.utcnow()

    if page.status == 'draft':
        page.set_meta('draft_tags', request.form['tags'])
    else:
        new_tags = set(tag_list(request.form['tags']))
        old_tags = set([t.name for t in page.tags])

        removed_tags = old_tags-new_tags
        if removed_tags:
            for tag in removed_tags:
                page.delete_tag(tag)

        new_tags = new_tags-old_tags
        if new_tags:
            for tag in new_tags:
                seo_name = tag.replace(' ', '-')
                page.add_tag(Tag(tag, seo_name))

    page.save()
    if config.use_cache:
        cache_del('posts_tags')
        if page.request_path:
            cache_del('individual_page_%s' % page.request_path)

    change_note = request.form['change_note'].strip()
    if change_note:
        Revision(page, change_note).save()

    cats = session.query(Category).all()
    return display_plain_template('admin/edit_page', page=page, cats=cats)


def tag_list(tag_str):
    if not tag_str:
        return []
    return [t.strip() for t in tag_str.split(',')]


def edit_page_preview(request, page_id):
    session.autoflush = False

    page = session.query(Page).filter_by(page_id=page_id).first()
    page_cat = session.query(Category).filter_by(category_id=request.form['cat_id']).first()

    page.title = request.form['title']
    page.content = request.form['content']
    page.excerpt = request.form['excerpt']
    page.category = page_cat

    map = MakoDict({
            'page':         page,
            'request_path': page.request_path
    })
    return display_page(default_page_template_data(request, map))


def publish_page(request, page_id):
    page = session.query(Page).filter_by(page_id=page_id).first()
    status = request.form['status']

    if status == 'page':
        page.status = 'page'
        page.save()
    elif status == 'post':
        page.category.count = Category.count + 1
        page.status = 'post'
        publish_date = datetime.strptime(request.form['publish_date'], '%Y-%m-%d %H:%M:%S')
        Rss(page, publish_date).save()
        BlogPage(page, publish_date).save()
        page.save()

    if status == 'page' or status == 'post':
        if config.use_cache:
            cache_del('individual_page_%s' % page.request_path)
            cache_del('page_list')
            cache_del('index_page_1')
            cache_del('posts_tags')
            if status == 'post':
                cache_del('atom_feed')
            # TODO: optimize cache invalidation method, and invalidate tags and categories

        draft_tags = page.get_meta('draft_tags')
        if draft_tags:
            tags = tag_list(draft_tags)
            for tag in tags:
                seo_name = tag.replace(' ', '-')
                page.add_tag(Tag(tag, seo_name))
        page.delete_meta('draft_tags')

    return redirect('/admin/edit_page/%d' % page.page_id)


########NEW FILE########
__FILENAME__ = exceptions
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#

from catonmat.admin             import require_admin
from catonmat.models            import session, Exception
from catonmat.views.utils       import display_plain_template

# ----------------------------------------------------------------------------

@require_admin()
def main(request):
    exc = session.query(Exception).order_by(Exception.date.desc()).all()
    return display_plain_template('admin/exceptions', exc=exc)


########NEW FILE########
__FILENAME__ = fof
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#

from catonmat.admin             import require_admin
from catonmat.models            import session, FouroFour
from catonmat.views.utils       import display_plain_template

# ----------------------------------------------------------------------------

@require_admin()
def main(request):
    fof = session.query(FouroFour).order_by(FouroFour.date.desc()).all()
    return display_plain_template('admin/404', fof=fof)


########NEW FILE########
__FILENAME__ = index
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#

from catonmat.admin             import require_admin, logged_in, REQUIRE_IP
from catonmat.views.utils       import display_plain_template

# ----------------------------------------------------------------------------

@require_admin([REQUIRE_IP])
def main(request):
    if not logged_in(request):
        return display_plain_template('admin/login')
    return display_plain_template('admin/index')


########NEW FILE########
__FILENAME__ = login
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#

from werkzeug                   import redirect

from catonmat.views.utils       import display_plain_template
from catonmat.admin             import (
    require_admin, REQUIRE_IP, hash_password, admin_cred_match_prim,
    mk_secure_cookie
)

# ----------------------------------------------------------------------------

@require_admin([REQUIRE_IP])
def main(request):
    if request.method != "POST":
        return display_plain_template('admin/login', message="Not a POST request")
    
    user = request.form.get('a')
    hash = hash_password(request.form.get('b'))
    if admin_cred_match_prim(user, hash):
        cookie = {
            'admin_user': user,
            'admin_hash': hash
        }
        response = redirect('/admin')
        response.set_cookie('admin', mk_secure_cookie(cookie).serialize(), httponly=True)
        return response

    return display_plain_template('admin/login', message="Password incorrect")


########NEW FILE########
__FILENAME__ = new_page
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#

from werkzeug                   import redirect

from catonmat.models            import session, Page, Category
from catonmat.admin             import require_admin
from catonmat.views.utils       import display_plain_template

# ----------------------------------------------------------------------------

@require_admin()
def main(request):
    if request.method == "GET":
        cats = session.query(Category).all()
        return display_plain_template('admin/new_page', cats=cats)
    if 'submit' in request.form:
        page = new_page(request)
        return redirect('/admin/edit_page/%d' % page.page_id)


def new_page(request):
    page = Page(
             request.form['title'],
             request.form['content'],
             request.form['excerpt'],
             category_id=request.form['cat_id'])
    page.status = 'draft'
    page.request_path = request.form['request_path']

    draft_tags = request.form['tags'].strip()
    if draft_tags:
        page.set_meta('draft_tags', draft_tags)

    page.save()

    return page


########NEW FILE########
__FILENAME__ = pages
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#

from catonmat.models            import session, Page
from catonmat.admin             import require_admin
from catonmat.views.utils       import display_plain_template

# ----------------------------------------------------------------------------

@require_admin()
def main(request):
    query = session.query(Page)

    if request.args.get('unpublished') is not None:
        query = query.filter_by(status='draft')
    elif request.args.get('posts') is not None:
        query = query.filter_by(status='post')
    elif request.args.get('pages') is not None:
        query = query.filter_by(status='page')

    all_pages = query.order_by(Page.page_id).all()
    return display_plain_template('admin/pages', pages=all_pages)


########NEW FILE########
__FILENAME__ = archive
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#

from sqlalchemy                     import func
from werkzeug.exceptions            import NotFound
from calendar                       import month_name as MONTH

from catonmat.models                import Page, BlogPage
from catonmat.database              import session
from catonmat.views.utils           import (
    cached_template_response, render_template, number_to_us
)

# ----------------------------------------------------------------------------

def main(request):
    sorted_by = request.args.get('sorted_by', 'date')
    return cached_template_response(
             compute_main,
             'archive_%s' % sorted_by,
             3600,
             sorted_by)


def compute_main(sorted_by):
    if sorted_by == 'views':
        sort_f = Page.views.desc
    elif sorted_by == 'date':
        sort_f = BlogPage.publish_date.desc
    pages = session. \
              query(Page). \
              join(BlogPage). \
              order_by(sort_f()). \
              all()
    return render_template('archive',
        pages=pages,
        sorted_by=sorted_by,
        number_to_us=number_to_us)


def year(request, year):
    return cached_template_response(
             compute_year,
             'archive_year_%d' % year,
             3600,
             year)


def compute_year(year):
    pages = session. \
              query(Page). \
              join(BlogPage). \
              filter('year(blog_pages.publish_date) = %d' % year). \
              order_by(BlogPage.publish_date.desc()). \
              all()
    return render_template('archive_year',
             pages=pages,
             year=year,
             number_to_us=number_to_us)


def year_month(request, year, month):
    return cached_template_response(
             compute_year_month,
             'archive_year_month_%d_%d' % (year, month),
             3600,
             year,
             month)


def compute_year_month(year, month):
    filter_str = 'year(blog_pages.publish_date) = %d and ' \
                 'month(blog_pages.publish_date) = %d' % (year, month)
    pages = session. \
              query(Page). \
              join(BlogPage). \
              filter(filter_str). \
              order_by(BlogPage.publish_date.desc()). \
              all()
    return render_template('archive_year_month',
             pages=pages,
             year=year,
             nmonth=month,
             month=MONTH[month],
             number_to_us=number_to_us)


########NEW FILE########
__FILENAME__ = c
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#
# This file handles /c/<comment_id> short comment URLS.

from werkzeug               import redirect
from werkzeug.exceptions    import NotFound

from sqlalchemy             import join

from catonmat.cache         import cache_del
from catonmat.models        import Comment, Page, UrlMap
from catonmat.database      import session
from catonmat.views.utils   import get_template, display_template

from catonmat.comments      import (
    validate_comment,       new_comment, thread, CommentError,
    invalidate_page_cache,  lynx_browser
)

# ----------------------------------------------------------------------------

# TODO: add caching

def main(request, comment_id):
    if request.method == "POST":
        return handle_comment_post(request, comment_id)
    return handle_comment_get(request, comment_id)


def handle_comment_get(request, comment_id):
    if request.args.get('reply') is not None:
        return comment_reply(request, comment_id)
    return comment_tree(request, comment_id)


def default_comment_template_data(request, comment_id):
    mixergy = session. \
                query(Comment, Page, UrlMap). \
                join(Page, UrlMap). \
                filter(Comment.comment_id==comment_id). \
                first()

    if not mixergy:
        # TODO: "The requested comment was not found, here are a few latest coments"
        #       "Here are latest posts, here are most commented posts..."
        raise NotFound()

    comment, page, urlmap = mixergy

    template_data = {
        'page':                 page,
        'page_path':            urlmap.request_path,
        'comment_submit_path':  '/c/%d?reply' % comment_id,
        'comment_parent_id':    comment_id,
        'comment':              comment,
        'form':                 request.form,
        'lynx':                 lynx_browser(request)
    }
    return template_data


def comment_reply(request, comment_id):
    template_data = default_comment_template_data(request, comment_id)
    template_data['reply'] = True
    return display_page(template_data)


def comment_tree(request, comment_id):
    template_data = default_comment_template_data(request, comment_id)
    template_data['reply'] = False

    # TODO: optimize comment selection
    comments = thread(template_data['page'].comments.all())
    template_data['comments'] = comments

    return display_page(template_data)


def handle_comment_post(request, comment_id):
    if request.form.get('submit') is not None:
        return handle_comment_submit(request, comment_id)
    else:
        return handle_comment_preview(request, comment_id)


def comment_error(request, comment_id, error):
    template_data = default_comment_template_data(request, comment_id)
    template_data['comment_error'] = error
    template_data['reply'] = True

    return display_page(template_data)


def handle_comment_submit(request, comment_id):
    try:
        validate_comment(request)
    except CommentError, e:
        return comment_error(request, comment_id, e.message)

    comment = new_comment(request)
    comment.save()

    invalidate_page_cache(request.form['page_id'])

    return redirect('/c/%d' % comment.comment_id)


def handle_comment_preview(request, comment_id):
    try:
        validate_comment(request, preview=True)
    except CommentError, e:
        return comment_error(request, comment_id, e.message)

    comment = new_comment(request)
    comment_preview = (get_template('comment').
                         get_def('individual_comment').
                         render(comment=comment, preview=True))

    template_data = default_comment_template_data(request, comment_id)
    template_data['comment_preview'] = comment_preview
    template_data['reply'] = True

    return display_page(template_data)


def display_page(template_data):
    return display_template("comment_page", **template_data)


########NEW FILE########
__FILENAME__ = categories
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#

from werkzeug.exceptions            import NotFound
from catonmat.models                import Category, BlogPage
from catonmat.database              import session
from catonmat.views.utils           import (
    cached_template_response, render_template, number_to_us
)

# ----------------------------------------------------------------------------

def main(request, seo_name):
    return cached_template_response(
             compute_main,
             'category_page_%s' % seo_name,
             3600,
             request,
             seo_name)

def compute_main(request, seo_name):
    category = session.query(Category).filter_by(seo_name=seo_name).first() 
    if not category:
        raise NotFound()

    pages = category.blog_pages.order_by(BlogPage.publish_date.desc()).all()

    return render_template('category', category=category, pages=pages,
             number_to_us=number_to_us)


def list(request):
    return cached_template_response(
             compute_list,
             'category_list',
             3600,
             request)


def compute_list(request):
    return render_template('category_list')


########NEW FILE########
__FILENAME__ = downloads
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#
# This file handles /p/<page_id> short page URLS.

from werkzeug               import Response, redirect, wrap_file
from werkzeug.exceptions    import NotFound

from catonmat.config        import config
from catonmat.models        import Download
from catonmat.database      import session

from catonmat.views.utils           import (
    cached_template_response, render_template, number_to_us
)

# ----------------------------------------------------------------------------

def main(request, filename):
    download = session.query(Download).filter_by(filename=filename).first() 
    if not download:
        # TODO: 'download you were looking for was not found, check out these downloads...'
        raise NotFound()

    try:
        file = open("%s/%s" % (config['download_path'], filename))
    except IOError:
        # TODO: 'the file was not found, check this out'
        raise NotFound()

    download.another_download(request)
    return Response(wrap_file(request.environ, file), mimetype=download.mimetype,
            direct_passthrough=True)


def old_wp_download(request, filename):
    return redirect('/download/%s' % filename, code=301)

def all(request):
    return cached_template_response(
             compute_all,
             'downloads',
             3600)

def compute_all():
    downloads = session. \
      query(Download). \
      order_by(Download.timestamp.desc()). \
      all()
    return render_template('downloads',
        downloads=downloads,
        number_to_us=number_to_us)


########NEW FILE########
__FILENAME__ = exception
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#

from werkzeug                           import Response

from pygments               import highlight
from pygments.lexers        import get_lexer_by_name
from pygments.formatters    import HtmlFormatter
from pygments.lexers.agile  import PythonTracebackLexer

from catonmat.views.utils               import render_template
from catonmat.errorlog                  import str_traceback

import sys

# ----------------------------------------------------------------------------

def main(request):
    exc_type, exc_value, tb = sys.exc_info()
    str_tb = str_traceback(exc_type, exc_value, tb)

    highlighted_str_tb = highlight(str_tb, PythonTracebackLexer(), HtmlFormatter())

    template = render_template('exception',
                 exception_type=exc_type.__name__,
                 exception_message=str(exc_value),
                 traceback=highlighted_str_tb)
    return Response(template, mimetype='text/html', status=500)


########NEW FILE########
__FILENAME__ = feedback
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#

from werkzeug                   import url_unquote_plus

from catonmat.views.utils       import display_template
from catonmat.models            import Feedback, Visitor

from urlparse                   import urlparse

import re

# ----------------------------------------------------------------------------

def main(request):
    if request.method == "POST":
        return handle_feedback_post(request)
    return handle_feedback_get(request)


class FeedbackError(Exception):
    pass


email_rx = re.compile(r'^.+@.+\..+$')
lynx_re  = re.compile(r'Lynx|Links', re.I)

def lynx_browser(request):
    browser = request.headers.get('User-Agent')
    if browser:
        if lynx_re.match(browser):
            return True
    return False


def validate_feedback(request):
    def validate_name(name):
        if not name:
            raise FeedbackError, "You forgot to specify your name!"
        if len(name) > 64:
            raise FeedbackError, "Your name is too long. Maximum length is 64 characters."

    def validate_email(email):
        if not email:
            raise FeedbackError, "You forgot to specify your e-mail!"
        if len(email) > 128:
            raise FeedbackError, "Your e-mail is too long. Maximum length is 128 characters."
        if not email_rx.match(email):
            raise FeedbackError, "Sorry, your e-mail address is not valid!"

    def validate_website(website):
        if website:
            if len(website) > 256:
                raise FeedbackError, "Your website address is too long. Maximum length is 256 characters."
            if '.' not in website:
                raise FeedbackError, "Your website address is invalid!"

            url = urlparse(website)
            if url.scheme:
                if url.scheme not in ('http', 'https', 'ftp'):
                    raise FeedbackError, "The only allowed website schemes are http://, https:// and ftp://"

    def validate_subject(subject):
        if not subject:
            raise FeedbackError, "You didn't write the subject of the message!"

    def validate_message(message):
        if not message:
            raise FeedbackError, "You didn't type the message!"

    def validate_captcha(name, captcha):
        if name[0] != captcha:
            raise FeedbackError, 'Please type "' + name[0] + '" in the box below.'

    validate_name(request.form['name'].strip())
    validate_email(request.form['email'].strip())
    validate_website(request.form['website'].strip())
    validate_subject(request.form['subject'].strip())
    validate_message(request.form['message'].strip())

    # pass through Lynx users (I have several loyal blog readers that use Lynx only)
    if not lynx_browser(request):
        validate_captcha(request.form['name'].strip(), request.form['feedbackc'].strip())


def handle_feedback_post(request):
    thank_you = False
    lynx = lynx_browser(request)
    try:
        validate_feedback(request)
        Feedback(
          Visitor(request),
          request.form['name'].strip(), 
          request.form['email'].strip(),
          request.form['subject'].strip(),
          request.form['message'].strip(),
          request.form['website'].strip()
        ).save()
        thank_you = True
    except FeedbackError, e:
        return display_template("feedback", form=request.form, error=e.message, lynx=lynx)

    if thank_you:
        form = dict()
    else:
        form = request.form
    return display_template("feedback", form=form, thank_you=thank_you, lynx=lynx)


def handle_feedback_get(request):
    form = dict()
    if request.args.get('subject'):
        form['subject'] = request.args.get('subject')
    return display_template("feedback", form=form, lynx=lynx_browser(request))


########NEW FILE########
__FILENAME__ = index
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#

from werkzeug.exceptions        import NotFound

from catonmat.views.utils       import MakoDict, cached_template_response, render_template
from catonmat.database          import session
from catonmat.models            import Page, BlogPage, UrlMap
from catonmat.config            import config
from catonmat.cache             import cache

from math                       import ceil

# ----------------------------------------------------------------------------

class Pagination(object):
    def __init__(self, current_page, total_pages, items_per_page):
        self.current_page = current_page
        self.total_pages = total_pages
        self.items_per_page = items_per_page

    @property
    def physical_pages(self):
        return int(ceil(self.total_pages/(self.items_per_page + 0.0)))


def main(request):
    return handle_page()


def page(request, page_nr):
    blogpages = total_blogpages()
    last_page = int(ceil(blogpages/(config.posts_per_page + 0.0)))

    if page_nr <= 0 or page_nr > last_page:
        # TODO: display nice error that page is out of range,
        #       and point the user to latest posts, other interesting stuff.
        raise NotFound()

    return handle_page(page_nr)


def page_list(request):
    blogpages = total_blogpages()
    return cached_template_response(
             compute_page_list,
             'page_list',
             3600)


def compute_page_list():
    posts = session. \
              query(Page). \
              join(BlogPage). \
              order_by(BlogPage.publish_date.desc()). \
              filter(BlogPage.visible==True). \
              all()
    return render_template(
             'page_list',
             posts=posts,
             pagination=Pagination(1, total_blogpages(), config.posts_per_page))


def handle_page(page_nr=1):
    return cached_template_response(
             compute_handle_page,
             'index_page_%s' % page_nr,
             3600,
             page_nr)


def compute_handle_page(page_nr=1):
    mixergy = get_mixergy(page_nr)

    page_array = []
    for page, urlmap in mixergy:
        page_array.append(
            mako_page(page, urlmap.request_path)
        )

    template_data = {
        'page_array': page_array,
        'pagination': Pagination(page_nr, total_blogpages(), config.posts_per_page)
    }
    if page_nr == 1:
        template_data['front_page'] = True
    else:
        template_data['front_page'] = False
    return render_template("index", **template_data)


@cache('total_blogpages')
def total_blogpages():
    return session. \
             query(BlogPage). \
             filter(BlogPage.visible==True). \
             count()


def get_mixergy(page=1):
    # TODO: narrow down the query
    return session. \
             query(Page, UrlMap). \
             join(BlogPage, UrlMap). \
             order_by(BlogPage.publish_date.desc()). \
             filter(BlogPage.visible==True). \
             limit(config.posts_per_page). \
             offset((page-1)*config.posts_per_page). \
             all() 


def default_display_options():
    return {
        'display_category':      True,
        'display_comment_count': True,
        'display_publish_time':  True,
        'display_tags':          False,
        'display_comments':      False,
        'display_comment_url':   True,
        'display_views':         True,
        'display_short_url':     False,
        'display_series_after':  False,
        'after_comments_ad':     False,
    }

    
def mako_page(page, request_path):
    return MakoDict({
        'page_data':        {
            'page':      page,
            'page_path': request_path
        },
        'comment_data':     {
            'comment_count': page.comment_count,
        },
        'display_options': default_display_options()
    })


########NEW FILE########
__FILENAME__ = mobile
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#

from catonmat.views.utils   import display_template

# ----------------------------------------------------------------------------

def main(request, url):
    fixed_url = "/" + url
    return display_template("mobile_page", page_url=fixed_url)


########NEW FILE########
__FILENAME__ = news
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#

from werkzeug.exceptions            import NotFound

from catonmat.models                import News, session
from catonmat.views.utils           import cached_template_response, render_template

# ----------------------------------------------------------------------------

def main(request):
    return cached_template_response(
             compute_main,
             'news',
             3600)

def compute_main():
    news = session.query(News).order_by(News.timestamp.desc()).all()
    return render_template('news', news=news)


########NEW FILE########
__FILENAME__ = not_found
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#

from werkzeug                           import Response
from catonmat.views.utils               import render_template

# ----------------------------------------------------------------------------

def main(request):
    template = render_template('404', path=request.path)
    return Response(template, mimetype='text/html', status=404)


########NEW FILE########
__FILENAME__ = p
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#
# This file handles /p/<page_id> short page URLS.

from werkzeug               import redirect
from werkzeug.exceptions    import NotFound

from catonmat.models        import UrlMap
from catonmat.database      import session

# ----------------------------------------------------------------------------

def main(request, page_id):
    return redirect(find_url(page_id), code=301)


def find_url(page_id):
    map = session. \
            query(UrlMap). \
            filter_by(page_id=page_id). \
            first()

    if not map:
        # TODO: 'page you were looking for was not found, perhaps you want to see ...'
        raise NotFound()

    return map.request_path


########NEW FILE########
__FILENAME__ = pages
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#

from sqlalchemy             import or_
from werkzeug.exceptions    import NotFound
from werkzeug               import redirect

from catonmat.database      import session, engine
from catonmat.models        import Page, UrlMap, TextAds
from catonmat.cache         import cache_del
from catonmat.config        import config
from catonmat.similarity    import related_posts
from catonmat.views.utils   import (
    MakoDict, cached_template_response, render_template, display_template,
    get_template
)
from catonmat.comments      import (
    validate_comment, new_comment, thread, linear, CommentError, lynx_browser
)

from datetime               import datetime
import re

# ----------------------------------------------------------------------------

def main(request, map):
    if request.method == "POST":
        return handle_page_post(request, map)
    return handle_page_get(request, map)


def handle_page_post(request, map):
    # Currently POST can only originate from a comment being submitted.
    map = session.query(UrlMap).filter_by(url_map_id=map['url_map_id']).first()
    if request.form.get('submit') is not None:
        return handle_comment_submit(request, map)

    if request.form.get('preview') is not None:
        return handle_comment_preview(request, map)

    raise NotFound()


def handle_comment_submit(request, map):
    try:
        validate_comment(request)
    except CommentError, e:
        return page_with_comment_error(request, map, e.message)

    # TODO: merge this, c.py and comments.py together,
    #       otherwise same code is spread over 3 files
    comment = new_comment(request)
    comment.save()

    if config.use_cache:
        cache_del('individual_page_%s' % map.request_path)
    
    return redirect('/c/%d' % comment.comment_id)


def handle_comment_preview(request, map):
    try:
        validate_comment(request, preview=True)
    except CommentError, e:
        return page_with_comment_error(request, map, e.message)

    comment = new_comment(request)
    comment_preview = (get_template('comment').
                         get_def('individual_comment').
                         render(comment=comment, preview=True))

    template_data = default_page_template_data(request, map)
    template_data['comment_data']['comment_preview'] = comment_preview

    return display_page(**template_data)


def page_with_comment_error(request, map, error):
    template_data = default_page_template_data(request, map)
    template_data['comment_data']['comment_error'] = error

    return display_page(**template_data)


def default_page_template_data(request, map):
    plain_old_comments = map.page.comments.all()
    if request.args.get('linear') is not None:
        comment_mode = 'linear'
        comments = linear(plain_old_comments)
    else:
        comment_mode = 'threaded'
        comments = thread(plain_old_comments)

    return {
        'display_options': MakoDict(default_display_options()),
        'page_data':       MakoDict({
            'page':                 map.page,
            'page_path':            map.request_path
        }),
        'comment_data':    MakoDict({
            'comment_count':        len(plain_old_comments),
            'comments':             comments,
            'comment_submit_path':  map.request_path,
            'comment_mode':         comment_mode,
            'form':                 request.form,
        }, ['comments', 'form']),
        'tags_data':       MakoDict({
            'tags':                 map.page.tags
        }),
        'related_posts':   related_posts(map.page),
        'lynx': lynx_browser(request)
    }


def default_display_options():
    return {
        'display_category':      True,
        'display_comment_count': True,
        'display_publish_time':  True,
        'display_comments':      True,
        'display_comment_url':   True,
        'display_tags':          True,
        'display_views':         True,
        'display_short_url':     True,
        'display_series_after':  True,
        'display_related_posts': True,
        'display_social':        True,
        'display_bsa':           True,
        'after_comments_ad':     True,
    }

no_adsense_ids = [6, 88, 3, 8, 18, 15, 139, 141, 153, 158]
stackvm_ids = [226, 231, 245, 257, 268, 269, 259, 273, 276, 278, 303, 310, 318, 324, 349, 346, 401]
mobile_rx = re.compile('/mobile/')

def handle_page_get(request, map):
    engine.execute("UPDATE pages SET views=views+1 WHERE page_id=%d" % map['page_id'])

    stackvm_post = False
    if map['page_id'] in stackvm_ids: # stackvm post ids
        stackvm_post = True

    if stackvm_post:
        su = request.args.get('signup')
        if su in ['ok', 'failed']:
            return compute_stackvm_get_page(request, map)

    referer = request.headers.get('Referer', 'None')
    mobile = False
    if mobile_rx.search(referer):
        mobile = True

    cache_id = 'individual_page_%s' % map['request_path']
    if mobile:
        cache_id = 'individual_mobile_page_%s' % map['request_path']

    return cached_template_response(
             compute_handle_page_get,
             cache_id,
             3600,
             request,
             map)


def compute_handle_page_get(request, map):
    map = session.query(UrlMap).filter_by(url_map_id=map['url_map_id']).first()
    template_data = default_page_template_data(request, map)
    text_ads = map.page.text_ads.filter(
                 or_(TextAds.expires==None, TextAds.expires<=datetime.utcnow())
               ).all()

    adsense = True
    if map.page_id in no_adsense_ids:
        adsense = False

    stackvm = False
    if map.page_id in stackvm_ids:
        stackvm=True

    referer = request.headers.get('Referer', 'None')
    mobile = False
    if mobile_rx.search(referer):
        mobile = True

    return render_template("page",
            text_ads=text_ads,
            stackvm=stackvm,
            adsense=adsense,
            mobile=mobile,
            **template_data)


def compute_stackvm_get_page(request, map):
    map = session.query(UrlMap).filter_by(url_map_id=map['url_map_id']).first()
    template_data = default_page_template_data(request, map)
    text_ads = map.page.text_ads.filter(
                 or_(TextAds.expires==None, TextAds.expires<=datetime.utcnow())
               ).all()

    referer = request.headers.get('Referer', 'None')
    mobile = False
    if mobile_rx.search(referer):
        mobile = True

    return display_page(
            text_ads=text_ads,
            mobile=mobile,
            stackvm=True,
            stackvm_signup=request.args.get('signup'),
            stackvm_signup_error=request.args.get('error'),
            **template_data
    )


def display_page(**template_data):
    return display_template("page", **template_data)


########NEW FILE########
__FILENAME__ = rss
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#

from werkzeug                       import Response, redirect
from werkzeug.contrib.atom          import AtomFeed

from catonmat.config                import config
from catonmat.cache                 import cache
from catonmat.database              import session
from catonmat.models                import Page, Rss

import re

# ----------------------------------------------------------------------------

feedburner_re = re.compile(r'feedburner|feedvalidator', re.I)

def feedburner_bot(request):
    ua = request.headers.get('User-Agent')
    if ua and feedburner_re.search(ua):
        return True
    return False

def atom_feed(request):
    if feedburner_bot(request):
        feed = compute_atom_feed(request)
        return Response(feed, mimetype='application/atom+xml')
    return redirect('http://feeds.feedburner.com/catonmat', code=302)

peteris = {
    'name':  'Peteris Krumins',
    'uri':   'http://www.catonmat.net/about',
    'email': 'peter@catonmat.net'
}

catonmat_title    = "good coders code, great reuse"
catonmat_subtitle = "Peteris Krumins' blog about programming, hacking, software reuse, software ideas, computer security, google and technology."

@cache('atom_feed')
def compute_atom_feed(request):
    feed = AtomFeed(
             title     = catonmat_title,
             subtitle  = catonmat_subtitle,
             feed_url  = 'http://www.catonmat.net/feed',
             url       = 'http://www.catonmat.net',
             author    = peteris,
             icon      = 'http://www.catonmat.net/favicon.ico',
             generator = ('catonmat blog', 'http://www.catonmat.net', 'v1.0')
           )

             # TODO: logo='http://www.catonmat.net/)

    pages = session. \
              query(Page). \
              join(Rss). \
              order_by(Rss.publish_date.desc()). \
              limit(config.rss_items). \
              all()

    for page in pages:
        feed.add(title        = page.title,
                 content      = page.parsed_content,
                 content_type = 'html',
                 author       = peteris,
                 url          = 'http://www.catonmat.net' + page.request_path,
                 id           = page.page_id,
                 updated      = page.last_update,
                 published    = page.rss_page.publish_date)

    return feed.to_string()


########NEW FILE########
__FILENAME__ = search
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#

from werkzeug.exceptions        import NotFound

from catonmat.models            import (
    Page, ArticleSeries, Comment, Tag, Category, SearchHistory, session
)
from catonmat.search            import search, SearchError
from catonmat.views.utils       import display_template, MakoDict
from catonmat.errorlog          import log_exception

# ----------------------------------------------------------------------------

def main(request):
    query = request.args.get('q')
    if not query:
        # TODO: display latest/top search queries instead of raising NotFound
        return display_template('search_empty')

    SearchHistory(query, request).save()

    try:
        page_results    = search(query, 'pages')
        as_results      = search(query, 'article_series')
        comment_results = search(query, 'comments')
        tag_results     = search(query, 'tags')
        cat_results     = search(query, 'categories')
    except SearchError, e:
        log_exception(request)
        return display_template('search_failed', query=query, error=e.message)

    pages    = get_pages(page_results)
    article_series = get_as(as_results)
    comments = get_comments(comment_results)
    tags     = get_tags(tag_results)
    cats     = get_cats(cat_results)

    return display_template('search',
             query=query,
             page_results=MakoDict(page_results),
             pages=pages,
             as_results=MakoDict(as_results),
             article_series=article_series,
             comment_results=MakoDict(comment_results),
             comments=comments,
             tag_results=MakoDict(tag_results),
             tags=tags,
             cat_results=MakoDict(cat_results),
             cats=cats)


# TODO: abstract this code.
def get_pages(page_results):
    page_ids = extract_ids(page_results['matches'])
    if not page_ids:
        return []
    pages = session. \
              query(Page). \
              filter(Page.page_id.in_(page_ids)). \
              all()
    d = dict([p.page_id, p] for p in pages)
    return [d[id] for id in page_ids]


def get_as(as_results):
    as_ids = extract_ids(as_results['matches'])
    if not as_ids:
        return []
    article_series = session. \
                       query(ArticleSeries). \
                       filter(ArticleSeries.series_id.in_(as_ids)). \
                       all()
    d = dict([a.series_id, a] for a in article_series)
    return [d[id] for id in as_ids]


def get_comments(comment_results):
    comment_ids = extract_ids(comment_results['matches'])
    if not comment_ids:
        return []
    comments = session. \
                 query(Comment). \
                 filter(Comment.comment_id.in_(comment_ids)). \
                 all()
    d = dict([c.comment_id, c] for c in comments)
    return [d[id] for id in comment_ids]


def get_tags(tag_results):
    tag_ids = extract_ids(tag_results['matches'])
    if not tag_ids:
        return []
    tags = session. \
             query(Tag). \
             filter(Tag.tag_id.in_(tag_ids)). \
             all()
    d = dict([t.tag_id, t] for t in tags)
    return [d[id] for id in tag_ids]


def get_cats(cat_results):
    cat_ids = extract_ids(cat_results['matches'])
    if not cat_ids:
        return []
    cats = session. \
             query(Category). \
             filter(Category.category_id.in_(cat_ids)). \
             all()
    d = dict([c.category_id, c] for c in cats)
    return [d[id] for id in cat_ids]


def extract_ids(matches):
    return [m['id'] for m in matches]


########NEW FILE########
__FILENAME__ = series
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#

from werkzeug                   import redirect
from werkzeug.exceptions        import NotFound

from catonmat.models            import ArticleSeries, session
from catonmat.views.utils       import (
    render_template, cached_template_response, number_to_us
)

# ----------------------------------------------------------------------------

def main(request):
    if request.method == "POST":
        return handle_series_post(request)
    return handle_series_get(request)


def handle_series_post(request):
    return redirect(request.form['navigate'])


def handle_series_get(request):
    """ list all series """
    return list(request)


def list(request):
    return cached_template_response(
             compute_list,
             'series', 
             3600)


def compute_list():
    series = session. \
               query(ArticleSeries). \
               order_by(ArticleSeries.name.asc()). \
               all()
    return render_template('series_list', series=series)



def single(request, seo_name):
    """ list articles in single series """
    return cached_template_response(
             compute_single,
             'series_%s' % seo_name,
             3600,
             seo_name)


def compute_single(seo_name):
    series = session.query(ArticleSeries).filter_by(seo_name=seo_name).first()
    if not series:
        # TODO: better not-found message
        raise NotFound
    return render_template('series', series=series, number_to_us=number_to_us)


########NEW FILE########
__FILENAME__ = sitemap
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#

from catonmat.models            import ArticleSeries, session
from catonmat.views.utils       import (
    MakoDict, cached_template_response, render_template
)

# ----------------------------------------------------------------------------

# TODO: make this dynamic

PAGES_D = [
    { 'path': '/projects', 'name': 'Projects', 'title': "Peteris Krumins' projects" },
    { 'path': '/sitemap',  'name': 'Sitemap',  'title': "Catonmat sitemap" },
    { 'path': '/feedback', 'name': 'Feedback', 'title': "Contact Peteris Krumins" }
]

PAGES = [ MakoDict(d) for d in PAGES_D ]

def main(request):
    return cached_template_response(compute_sitemap, 'sitemap', 3600)


def compute_sitemap():
    series = session.query(ArticleSeries).order_by(ArticleSeries.name).all()
    return render_template('sitemap', pages=PAGES, series=series)


########NEW FILE########
__FILENAME__ = tags
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#

from werkzeug.exceptions            import NotFound

from catonmat.models                import Tag, BlogPage
from catonmat.database              import page_tags_table, session
from catonmat.views.utils           import (
    cached_template_response, render_template, number_to_us
)

# ----------------------------------------------------------------------------

def main(request, seo_name):
    return cached_template_response(
             compute_main,
             'tag_page_%s' % seo_name,
             3600,
             request,
             seo_name)


def compute_main(request, seo_name):
    # TODO: perhaps this query is not necessary
    tag = session.query(Tag).filter_by(seo_name=seo_name).first()
    if not tag:
        raise NotFound()

    pages = tag.blog_pages.order_by(BlogPage.publish_date.desc()).all()

    return render_template('tag', tag=tag, pages=pages, number_to_us=number_to_us)


def list(request):
    return cached_template_response(
             compute_list,
             'tag_list',
             3600,
             request)


def compute_list(request):
    tags = session.query(Tag).order_by(Tag.name).all()
    return render_template('tag_list', tags=tags)


########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#

from werkzeug               import import_string, Response

from mako.template          import Template
from mako.lookup            import TemplateLookup

from catonmat.config        import config
from catonmat.cache         import from_cache_or_compute
from catonmat.quotes        import get_random_quote

import re

# ----------------------------------------------------------------------------

class MakoDict(object):
    """
    Given a dict d, MakoDict makes its keys accessible via dot.
    It also returns None if the key doesn't exist.
    >>> d = DotDict({'apple': 5, 'peach': { 'kiwi': 9 } })
    >>> d.apple
    5
    >>> d.peach.kiwi
    9
    >>> d.coco
    None
    """
    def __init__(self, d, exclude=None):
        if exclude is None:
            exclude = []

        for k, v in d.items():
            if isinstance(v, dict) and k not in exclude:
                v = MakoDict(v)
            self.__dict__[k] = v

    def __getitem__(self, k):
        return self.__dict__[k]

    def __getattr__(self, name):
        if name.startswith('__'):
            return object.__getattr__(self, name)
        return None

    def __setattr__(self, name, value):
        self.__dict__[name] = value

    def __setitem__(self, name, value):
        self.__dict__[name] = value


def number_to_us(num):
    return (','.join(re.findall(r'\d{1,3}', str(num)[::-1])))[::-1]


mako_lookup = TemplateLookup(
    directories=['catonmat/templates'],
    module_directory=config.mako_modules,
    output_encoding='utf-8'
)

def template_response(rendered_template):
    return Response(
        rendered_template,
        mimetype='text/html'
    )


def cached_template_response(computef, cache_key, duration, *args, **kw):
    return template_response(from_cache_or_compute(computef, cache_key, duration, *args, **kw))


def display_template(template, **template_args):
    rendered_template = render_template(template, **template_args)
    return template_response(rendered_template)


def display_plain_template(template, **template_args):
    rendered_template = render_plain_template(template, **template_args);
    return template_response(rendered_template)


def render_template(template_name, **template_args):
    quote = get_random_quote()
    top_pages = get_most_popular_pages()
    top_downloads = get_most_downloads()
    recent_pages = get_recent_pages()
    categories = session.query(Category).order_by(Category.name.asc()).all()
    post_archive = get_post_archive()
    return render_plain_template(
             template_name, 
             quote=quote,
             top_pages=top_pages,
             top_downloads=top_downloads,
             recent_pages = recent_pages,
             categories = categories,
             post_archive = post_archive,
             **template_args)


def render_plain_template(template_name, **template_args):
    template = get_template(template_name)
    return template.render(**template_args)


def get_template(name):
    file = name + ".tmpl.html"
    template = mako_lookup.get_template(file)
    return template


def get_view(endpoint):
  try:
    return import_string('catonmat.views.' + endpoint)
  except (ImportError, AttributeError):
    try:
      return import_string(endpoint)
    except (ImportError, AttributeError):
      raise RuntimeError('Could not locate view for %r' % endpoint)


from catonmat.models        import Category, session
from catonmat.statistics    import (
    get_most_popular_pages, get_most_downloads, get_recent_pages, get_post_archive
)


########NEW FILE########
__FILENAME__ = catonmat_fcgi
#!/home/pkrumins/catonmat/bin/python
#

from flup.server.fcgi import WSGIServer
from catonmat.application import application

WSGIServer(application).run()


########NEW FILE########
__FILENAME__ = processor
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#

import sys
sys.path.append('.')

import smtplib, time, urllib, urllib2, socket, subprocess
import simplejson as json
from datetime import datetime
from email import encoders
from email.message import Message
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from unidecode import unidecode

from catonmat.models import PayPalPayments, session

PayPalSandbox = False

MailServer = "localhost"
MailFrom = "Peteris Krumins <peter@catonmat.net>"

PayPalUrl = "www.sandbox.paypal.com" if PayPalSandbox else "www.paypal.com"

EmailTemplatePath = "/home/pkrumins/catonmat/payments"
AwkBookPath = "/home/pkrumins/lvm0/Workstation/catonmat/books/awk-one-liners-explained"
SedBookPath = "/home/pkrumins/lvm0/Workstation/catonmat/books/sed-one-liners-explained"
PerlBookPath = "/home/pkrumins/lvm0/Workstation/catonmat/books/perl-one-liners-explained"
LatexLogPath = "/home/pkrumins/catonmat/payments/latex.log"

def template_replace(text, hash):
    for x in hash:
        text = text.replace("!%s!" % x, hash[x])
    return text

def awk_book_template(infile, outfile, payment):
    fd = open("%s/%s" % (AwkBookPath, infile))
    data = fd.read()
    fd.close()

    email = payment.payer_email.replace("_", "\\_")

    if payment.product_type in ['awk_book', 'awk_book_995']:
        bgcontents = "Prepared exclusively for !NAME! !SURNAME! (!EMAIL!)"
    elif payment.product_type == 'awk_book_shantanu':
        bgcontents = "Prepared exclusively for !NAME! !SURNAME! (!EMAIL!) from Shantanu N Kulkarni's Awk class"
    else:
        print "Unknown product_type %s" % payment.product_type

    bgcontents = template_replace(bgcontents, {
        "NAME" : payment.first_name,
        "SURNAME" : payment.last_name,
        "EMAIL" : email
    })

    data = template_replace(data, {
        "NAME" : payment.first_name,
        "SURNAME" : payment.last_name,
        "EMAIL" : email,
        "BGCONTENTS" : bgcontents
    })

    fd = open("%s/%s" % (AwkBookPath, outfile), 'w+')
    fd.write(data.encode('utf-8'))
    fd.close()


def awk_book(payment):
    print "Preparing Awk Book..."
    subject = Products['awk_book']['subject']
    attachment = "%s/%s" % (AwkBookPath, Products['awk_book']['file'])
    attachment_name = Products['awk_book']['attachment_name']
    
    fd = open(EmailTemplatePath + '/thanks-awk-book.txt')
    body = fd.read()
    fd.close()

    email_body = template_replace(body, {
        "NAME": payment.first_name,
        "SURNAME": payment.last_name
    })

    awk_book_template('awkbook_template.tex', 'awkbook.tex', payment)
    awk_book_template('intro_template.tex', 'intro.tex', payment)
    awk_book_template('chapter2_template.tex', 'chapter2.tex', payment)
    awk_book_template('chapter3_template.tex', 'chapter3.tex', payment)
    awk_book_template('chapter4_template.tex', 'chapter4.tex', payment)

    print "Spawning Latex..."
    latex_log = open(LatexLogPath, 'a+')
    latex = subprocess.Popen("pdflatex awkbook.tex", stdout=latex_log, stderr=latex_log, cwd=AwkBookPath, shell=True)
    latex.wait()

    print "Spawning makeindex..."
    makeindex = subprocess.Popen("makeindex awkbook", stdout=latex_log, stderr=latex_log, cwd=AwkBookPath, shell=True)
    makeindex.wait()

    print "Spawning Latex 2nd time..."
    latex = subprocess.Popen("pdflatex awkbook.tex", stdout=latex_log, stderr=latex_log, cwd=AwkBookPath, shell=True)
    latex.wait()

    print "Spawning Latex 3nd time..."
    latex = subprocess.Popen("pdflatex awkbook.tex", stdout=latex_log, stderr=latex_log, cwd=AwkBookPath, shell=True)
    latex.wait()
    latex_log.close()

    print "Sending the Awk book to %s %s (%s)." % (unidecode(payment.first_name), unidecode(payment.last_name), payment.payer_email)
    send_mail(payment.payer_email, MailFrom, Products['awk_book']['subject'], email_body, attachment, attachment_name)

def sed_book_template(infile, outfile, payment):
    fd = open("%s/%s" % (SedBookPath, infile))
    data = fd.read()
    fd.close()

    email = payment.payer_email.replace("_", "\\_")

    data = template_replace(data, {
        "NAME" : payment.first_name,
        "SURNAME" : payment.last_name,
        "EMAIL" : email
    })

    fd = open("%s/%s" % (SedBookPath, outfile), 'w+')
    fd.write(data.encode('utf-8'))
    fd.close()

def sed_book(payment):
    print "Preparing Sed Book..."
    subject = Products['sed_book']['subject']
    attachment = "%s/%s" % (SedBookPath, Products['sed_book']['file'])
    attachment_name = Products['sed_book']['attachment_name']
    
    fd = open(EmailTemplatePath + '/thanks-sed-book.txt')
    body = fd.read()
    fd.close()

    email_body = template_replace(body, {
        "NAME": payment.first_name,
        "SURNAME": payment.last_name
    })

    sed_book_template('sedbook_template.tex', 'sedbook.tex', payment)
    sed_book_template('chapter1_template.tex', 'chapter1.tex', payment)
    sed_book_template('chapter4_template.tex', 'chapter4.tex', payment)
    sed_book_template('chapter6_template.tex', 'chapter6.tex', payment)

    print "Spawning Latex..."
    latex_log = open(LatexLogPath, 'a+')
    latex = subprocess.Popen("pdflatex sedbook.tex", stdout=latex_log, stderr=latex_log, cwd=SedBookPath, shell=True)
    latex.wait()

    print "Spawning makeindex..."
    makeindex = subprocess.Popen("makeindex sedbook", stdout=latex_log, stderr=latex_log, cwd=SedBookPath, shell=True)
    makeindex.wait()

    print "Spawning Latex 2nd time..."
    latex = subprocess.Popen("pdflatex sedbook.tex", stdout=latex_log, stderr=latex_log, cwd=SedBookPath, shell=True)
    latex.wait()

    print "Spawning Latex 3nd time..."
    latex = subprocess.Popen("pdflatex sedbook.tex", stdout=latex_log, stderr=latex_log, cwd=SedBookPath, shell=True)
    latex.wait()
    latex_log.close()

    print "Sending the Sed book to %s %s (%s)." % (unidecode(payment.first_name), unidecode(payment.last_name), payment.payer_email)
    send_mail(payment.payer_email, MailFrom, Products['sed_book']['subject'], email_body, attachment, attachment_name)

def perl_book_template(infile, outfile, payment):
    fd = open("%s/%s" % (PerlBookPath, infile))
    data = fd.read()
    fd.close()

    email = payment.payer_email.replace("_", "\\_")

    data = template_replace(data, {
        "NAME" : payment.first_name,
        "SURNAME" : payment.last_name,
        "EMAIL" : email
    })

    fd = open("%s/%s" % (PerlBookPath, outfile), 'w+')
    fd.write(data.encode('utf-8'))
    fd.close()

def perl_book(payment):
    print "Preparing Perl Book..."
    subject = Products['perl_book']['subject']
    attachment = "%s/%s" % (PerlBookPath, Products['perl_book']['file'])
    attachment_name = Products['perl_book']['attachment_name']
    
    fd = open(EmailTemplatePath + '/thanks-perl-book.txt')
    body = fd.read()
    fd.close()

    email_body = template_replace(body, {
        "NAME": payment.first_name,
        "SURNAME": payment.last_name
    })

    perl_book_template('perlbook_template.tex', 'perlbook.tex', payment)
    perl_book_template('chapter6_template.tex', 'chapter6.tex', payment)
    perl_book_template('chapter7_template.tex', 'chapter7.tex', payment)

    print "Spawning Latex..."
    latex_log = open(LatexLogPath, 'a+')
    latex = subprocess.Popen("pdflatex perlbook.tex", stdout=latex_log, stderr=latex_log, cwd=PerlBookPath, shell=True)
    latex.wait()

    print "Spawning makeindex..."
    makeindex = subprocess.Popen("makeindex perlbook", stdout=latex_log, stderr=latex_log, cwd=PerlBookPath, shell=True)
    makeindex.wait()

    print "Spawning Latex 2nd time..."
    latex = subprocess.Popen("pdflatex perlbook.tex", stdout=latex_log, stderr=latex_log, cwd=PerlBookPath, shell=True)
    latex.wait()

    print "Spawning Latex 3nd time..."
    latex = subprocess.Popen("pdflatex perlbook.tex", stdout=latex_log, stderr=latex_log, cwd=PerlBookPath, shell=True)
    latex.wait()
    latex_log.close()

    print "Sending the Perl book to %s %s (%s)." % (unidecode(payment.first_name), unidecode(payment.last_name), payment.payer_email)
    send_mail(payment.payer_email, MailFrom, Products['perl_book']['subject'], email_body, attachment, attachment_name)



Products = {
    'awk_book': {
        'subject' : 'Your Awk One-Liners Explained E-Book!',
        'file' : 'awkbook.pdf',
        'attachment_name' : 'awk-one-liners-explained.pdf',
        'price' : '5.95',
        'email_body' : 'thanks-awk-book.txt',
        'handler' : awk_book
    },
    'awk_book_995': {
        'subject' : 'Your Awk One-Liners Explained E-Book!',
        'file' : 'awkbook.pdf',
        'attachment_name' : 'awk-one-liners-explained.pdf',
        'price' : '9.95',
        'email_body' : 'thanks-awk-book.txt',
        'handler' : awk_book
    },
    'awk_book_shantanu' : {
        'subject' : 'Your Awk One-Liners Explained E-Book!',
        'file' : 'awkbook.pdf',
        'attachment_name' : 'awk-one-liners-explained.pdf',
        'price' : '2.50',
        'email_body' : 'thanks-awk-book.txt',
        'handler' : awk_book
    },
    'sed_book': {
        'subject' : 'Your Sed One-Liners Explained E-Book!',
        'file' : 'sedbook.pdf',
        'attachment_name' : 'sed-one-liners-explained.pdf',
        'price' : '9.95',
        'email_body' : 'thanks-sed-book.txt',
        'handler' : sed_book
    },
    'sed_book_shantanu': {
        'subject' : 'Your Sed One-Liners Explained E-Book!',
        'file' : 'sedbook.pdf',
        'attachment_name' : 'sed-one-liners-explained.pdf',
        'price' : '2.50',
        'email_body' : 'thanks-sed-book.txt',
        'handler' : sed_book
    },
    'perl_book': {
        'subject' : 'Your Perl One-Liners Explained E-Book!',
        'file' : 'perlbook.pdf',
        'attachment_name' : 'perl-one-liners-explained.pdf',
        'price' : '9.95',
        'email_body' : 'thanks-perl-book.txt',
        'handler' : perl_book
    },
}


def send_mail(mail_to, mail_from, subject, body, attachment, attachment_name):
    TO = [mail_to]

    mail = MIMEMultipart()
    mail['Subject'] = subject
    mail['From'] = mail_from
    mail['To'] = ','.join(TO)

    mailbody = MIMEText(body.encode('utf8'), 'plain')
    mail.attach(mailbody)

    fp = open(attachment, 'rb')
    attachment = MIMEBase('application', 'pdf')
    attachment.set_payload(fp.read())
    attachment.add_header('Content-Disposition', 'attachment', filename=attachment_name)
    fp.close()
    encoders.encode_base64(attachment)
    mail.attach(attachment)

    server = smtplib.SMTP(MailServer)
    server.sendmail(mail_from, TO, mail.as_string())
    server.quit()


def payment_already_completed(payment):
    payments = session.query(PayPalPayments) \
        .filter_by(transaction_id=payment.transaction_id) \
        .all()

    for existing_payment in payments:
        if existing_payment.transaction_id == payment.transaction_id:
            if existing_payment.status == 'completed':
                return True
    return False


def valid_paypal_payment(payment):
    PayPalPostUrl = "http://%s/cgi-bin/webscr" % PayPalUrl
    try:
        post_data = json.loads(payment.ipn_message)
        post_data['cmd'] = '_notify-validate'
        post_data = dict([k, v.encode('utf-8')] for k, v in post_data.items())
        response = urllib2.urlopen(PayPalPostUrl, urllib.urlencode(post_data))
        return response.read() == 'VERIFIED'
    except (urllib2.HTTPError, urllib2.URLError), e:
        print "Error POST'ing to PayPal: %s" % str(e)
    except (socket.error, socket.sslerror), e:
        print "Socket error: %s" % str(e)
    except socket.timeout, e:
        print "Socket timeout: %s" % str(e)


def completed_paypal_payment(payment):
    return payment.payment_status == 'Completed'


def correct_price(payment):
    return payment.mc_gross >= Products[payment.product_type]['price']


def handle_new_payments():
    new_payments = session.query(PayPalPayments) \
        .filter_by(status='new') \
        .order_by(PayPalPayments.payment_id) \
        .all()

    for payment in new_payments:
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        print "[%s] Processing new payment (id: %s, trx_id: %s) for %s from %s." % (now, payment.payment_id, payment.transaction_id, payment.product_type, payment.payer_email)
        if payment_already_completed(payment):
            print "Payment (id: %s, trx_id: %s) has already been completed." % (payment.payment_id, payment.transaction_id)
            payment.status = 'already_completed'
            session.commit()
            continue

        if payment.product_type not in Products:
            print "Unknown product type %s for payment (id: %s, trx_id: %s)" % (payment.product_type, payment.payment_id, payment.transaction_id)
            payment.status = 'unknown_product'
            session.commit()
            continue

        if not valid_paypal_payment(payment):
            print "Payment (id: %s, trx_id: %s) is invalid." % (payment.payment_id, payment.transaction_id)
            payment.status = 'invalid'
            session.commit()
            continue

        if not completed_paypal_payment(payment):
            print "Payment (id: %s, trx_id: %s) has PayPal status %s (not 'Completed')." % (payment.payment_id, payment.transaction_id, payment.payment_status)
            payment.status = 'not_paypal_completed'
            session.commit()
            continue

        if not correct_price(payment):
            print "Payment (id: %s, trx_id: %s) has wrong price (has: %s, should be: %s)." % (payment.payment_id, payment.transaction_id, payment.mc_gross, Products[payment.product_type]['price'])
            payment.status = 'wrong_price'
            session.commit()
            continue

        Products[payment.product_type]['handler'](payment)
        payment.status = 'completed'
        session.commit()


def handle_free_payments():
    new_payments = session.query(PayPalPayments) \
        .filter_by(status='free') \
        .order_by(PayPalPayments.payment_id) \
        .all()

    for payment in new_payments:
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        print "[%s] Processing free payment (id: %s, trx_id: %s) for %s from %s." % (now, payment.payment_id, payment.transaction_id, payment.product_type, payment.payer_email)
        Products[payment.product_type]['handler'](payment)
        payment.status = 'completed_free'
        session.commit()


if __name__ == "__main__":
    while True:
        handle_new_payments()
        handle_free_payments()
        session.commit()
        time.sleep(30)


########NEW FILE########
__FILENAME__ = email_sender
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#

import sys
sys.path.append('.')

import smtplib, time, urllib, urllib2, socket, subprocess
import simplejson as json
from datetime import datetime
from email import encoders
from email.message import Message
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from unidecode import unidecode

MailServer = "localhost"
MailFrom = "Peteris Krumins <peter@catonmat.net>"
Subject = "I have written my second e-book: Sed One-Liners Explained!"

def template_replace(text, hash):
    for x in hash:
        text = text.replace("!%s!" % x, hash[x])
    return text


def send_mail(mail_to, mail_from, subject, body):
    TO = [mail_to]

    mail = MIMEText(body, 'plain', 'utf8')
    mail['Subject'] = subject
    mail['From'] = mail_from
    mail['To'] = ','.join(TO)

    server = smtplib.SMTP(MailServer)
    server.sendmail(mail_from, TO, mail.as_string())
    server.quit()


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) < 2:
        print "Usage: script.py emails_file template_file"
        sys.exit(1)

    emails_file, template_file = args

    fh = open(emails_file)
    emails = fh.read()
    fh.close()

    fh = open(template_file)
    template = fh.read()
    fh.close()
    template = template.encode('utf8')

    emails = [e for e in emails.split('\n') if e]
    total = len(emails)
    sent = 0
    for e in emails:
        name, surname, email = e.split('\t')
        etemplate = template_replace(template, {
            "NAME" : name,
            "SURNAME" : surname
        })
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        print "[%s] [%d/%d] Sending email to %s %s (%s)." % (now, sent+1, total, unidecode(name), unidecode(surname), email)
        send_mail(email, MailFrom, Subject, etemplate)
        sent = sent + 1
        time.sleep(10)


########NEW FILE########
__FILENAME__ = init_database
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# This script creates all the new catonmat.net database tables.
#
# Code is licensed under GNU GPL license.
#

import sys
sys.path.append('/home/pkrumins/catonmat')

from catonmat.database import metadata, engine

def init_database():
    metadata.create_all(engine)

print "Initing catonmat database."
init_database()
print "Done initing."


########NEW FILE########
__FILENAME__ = ping_services
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# This program pings several blog services to notify them that blog has updated.
#
# Code is licensed under GNU GPL license.
#

import sys
import socket
from xmlrpclib import Server, Error

socket.setdefaulttimeout(5)

services = [
    [ 'FeedBurner', 'http://ping.feedburner.google.com/' ],
    [ 'Google', 'http://blogsearch.google.com/ping/RPC2' ],
    [ 'Weblogs.com', 'http://rpc.weblogs.com/RPC2' ],
    [ 'Moreover', 'http://api.moreover.com/RPC2' ],
    [ 'Syndic8', 'http://ping.syndic8.com/xmlrpc.php'  ],
    [ 'BlogRolling', 'http://rpc.blogrolling.com/pinger/' ],
    [ 'NewsGator', 'http://services.newsgator.com/ngws/xmlrpcping.aspx' ],
    [ 'Blog People', 'http://www.blogpeople.net/servlet/weblogUpdates' ],
    [ 'FeedSky', 'http://www.feedsky.com/api/RPC2' ],
    [ 'Yandex', 'http://ping.blogs.yandex.ru/RPC2' ]
]

default_blog_title  = 'good coders code, great reuse'
default_blog_url    = 'http://www.catonmat.net'
default_blog_fb_url = 'http://feeds.feedburner.com/catonmat'

# ---------------------------------------------------------------------------

def ping_services(blog_title, blog_url, blog_fb_url):
    for service in services:
        ping_service(service, blog_title, blog_url, blog_fb_url)

def ping_service(service, blog_title, blog_url, blog_fb_url):
    service_name, service_url = service
    if service_name == 'FeedBurner': # feedburner is an exception
        blog_url = blog_fb_url
    try:
        print "Pinging %s." % service_name
        rpc = Server(service_url)
        response = rpc.weblogUpdates.ping(blog_title, blog_url)
        if response['flerror']:
            print "Failed pinging %s. Error: %s" % (service_name, response['message'])
        else:
            print "Successfully pinged %s. Response: %s" % (service_name, response['message'])
    except socket.timeout:
        print "Failed pinging %s. Error: socket timed out"
    except Error, e:
        print "Failed pinging %s. Error: %s" % (service_name, str(e))

def main():
    args = sys.argv[1:]
    if len(args) != 0 and len(args) != 3:
        print >>sys.stderr, """Usage: %s "blog title" BLOG_URL FEEDBURNER_URL"""
        sys.exit(1)
    if len(args) == 0:
        print "Using default blog data for blog %s" % default_blog_title
        blog_title  = default_blog_title
        blog_url    = default_blog_url
        blog_fb_url = default_blog_fb_url
    if len(args) == 3:
        blog_title, blog_url, blog_fb_url = args
    
    ping_services(blog_title, blog_url, blog_fb_url)

if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = pygments_css_style
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# This program imports a wordpress database into the new catonmat database
#
# Code is licensed under GNU GPL license.
#

import sys
from pygments.formatters import HtmlFormatter
from pygments.util       import ClassNotFound

def print_style(name):
    try:
        print HtmlFormatter(style=name).get_style_defs('.highlight')
    except ClassNotFound:
        print "Style %s not found!" % name
        sys.exit(1)

def main():
    args = sys.argv[1:]
    if not args:
        print "Usage: %s <style name>" % sys.argv[0]
        sys.exit(1)
    style_name = args[0]
    print_style(style_name)

if __name__ == "__main__":
    main()


########NEW FILE########
__FILENAME__ = spamtest
import sys
sys.path.append('.')

from catonmat.models import Comment
from catonmat.database import session
from catonmat.comment_spamlist import spamlist_names, spamlist_urls, spamlist_emails, spamlist_comments

comments = session.query(Comment).all()

for c in comments:
    for r in spamlist_names:
        if r.search(c.name):
            print "Comment %d matches name %s" % (c.comment_id, c.name.encode('utf8'))

    for r in spamlist_emails:
        if r.search(c.email):
            print "Comment %d matches email %s" % (c.comment_id, c.email)

    for r in spamlist_urls:
        if r.search(c.website):
            print "Comment %d matches website %s" % (c.comment_id, c.website)

    for r in spamlist_comments:
        if r.search(c.comment):
            print "Comment %d matches comment %s..." % (c.comment_id, c.comment[0:50])

########NEW FILE########
__FILENAME__ = wordpress_to_catonmat
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# This program imports a wordpress database into the new catonmat database
#
# Code is licensed under GNU GPL license.
#

import sys
sys.path.append('/home/pkrumins/catonmat')

from sqlalchemy         import MetaData, create_engine
from sqlalchemy         import Table
from sqlalchemy.orm     import sessionmaker

from catonmat.views.utils import MakoDict
from catonmat.models    import (
    Page, Tag, Category, Comment, Visitor, UrlMap, BlogPage, Rss, Download, Revision
)

from mimetypes          import guess_type
from collections        import defaultdict
from urlparse           import urlparse
from datetime           import timedelta

import re

# ----------------------------------------------------------------------------

engine = create_engine('mysql://root@localhost/catonmat_wordpress?charset=utf8')
metadata = MetaData(bind=engine)
Session = sessionmaker(bind=engine)
session = Session()

wp_pages_table = Table('wp_posts', metadata, autoload=True)
wp_tags_table = Table('wp_tags', metadata, autoload=True)
wp_post2tag_table = Table('wp_post2tag', metadata, autoload=True)
wp_comments_table = Table('wp_comments', metadata, autoload=True)
wp_categories_table = Table('wp_categories', metadata, autoload=True)
wp_post2cat_table = Table('wp_post2cat', metadata, autoload=True)
wp_postmeta_table = Table('wp_postmeta', metadata, autoload=True)
wp_downloads_table = Table('wp_DLM_DOWNLOADS', metadata, autoload=True)

def enumerate1(iterable):
    for a, b in enumerate(iterable):
        yield a+1, b

def flush_write(str):
    sys.stdout.write(str)
    sys.stdout.flush()

def wordpress_to_catonmat():
    wp_pages = get_wp_pages()
    wp_tags_dict = get_wp_tags()
    wp_comments_dict = get_wp_comments()
    wp_categories_dict = get_wp_categories()
    wp_downloads = get_wp_downloads()

    import_categories(wp_categories_dict)
    import_downloads(wp_downloads)
    import_pages(wp_pages, wp_tags_dict, wp_comments_dict, wp_categories_dict)

def import_downloads(wp_downloads):
    def get_mimetype(filename):
        plaintext_mimes = "awk php phps vb vbs pl pm perl conf py python c cpp".split()
        try:
            ext = filename.split('.')[1]
            if ext in plaintext_mimes:
                return 'text/plain'
        except (IndexError, KeyError):
            pass
        return guess_type(filename)[0]

    flush_write("Importing downloads. ")
    for wp_download in wp_downloads:
        filename = re.sub(r'.*/', '', wp_download.filename)
        mimetype = get_mimetype(filename)
        cm_download = Download(wp_download.title, filename, \
                        mimetype, wp_download.hits, \
                        wp_download.postDate)
        cm_download.download_id = wp_download.id
        cm_download.save()
    flush_write("Done.\n")

def import_categories(wp_categories_dict):
    flush_write("Importing categories. ")
    for wp_cat in wp_categories_dict.values():
        cm_cat = Category(wp_cat.cat_name, wp_cat.category_nicename, wp_cat.category_description)
        wp_cat.cm_cat = cm_cat
        cm_cat.save()
    flush_write("Done.\n")

def import_pages(wp_pages, wp_tags_dict, wp_comments_dict, wp_categories_dict):
    def print_status(npk):
        if npk % 10 == 0: flush_write("(%d)" % npk)
        else:             flush_write('.')

    skip_paths = ['/sitemap', '/feedback', '/post-archive'] 
    skip_titles_re = re.compile('continuity')

    flush_write("Importing pages, comments, tags, urlmaps, blogpages and rss.\n")
    for npk, wp_page in enumerate1(wp_pages):
        print_status(npk)

        if skip_titles_re.search(wp_page.post_title):
            continue

        parsed = urlparse(wp_page.guid)
        path = parsed.path.rstrip('/')
        if path:
            if path in skip_paths:
                continue

        post_date=wp_page.post_date
        if post_date:
            post_date = post_date-timedelta(hours=3)            # 3 hr diff in my wp config
        post_modified=wp_page.post_modified
        if post_modified:
            post_modified = post_modified-timedelta(hours=3)    # same
        cm_page = Page(wp_page.post_title, wp_page.post_content, wp_page.post_excerpt, 
                       post_date, post_modified)
        if wp_page.post_status == 'draft':
            cm_page.status = 'draft'
        elif wp_page.post_status == 'publish':
            if wp_page.post_type == 'page':
                cm_page.status = 'page'
            elif wp_page.post_type == 'post':
                cm_page.status = 'post'
        import_page_views(wp_page, cm_page)
        import_page_tags(wp_page, cm_page, wp_tags_dict)
        import_page_category(wp_page, cm_page, wp_categories_dict)
        Revision(cm_page, 'first import').save()
        cm_page.save() # to generate cm_page.page_id
        import_page_comments(wp_page, cm_page.page_id, wp_comments_dict)
        generate_urlmap(wp_page, cm_page.page_id)
        insert_blogpage(wp_page, cm_page)
        insert_rss(wp_page, cm_page)
    flush_write("Done.\n")

def import_page_views(wp_page, cm_page):
    views = session. \
              query(wp_postmeta_table). \
              filter(wp_postmeta_table.c.post_id==wp_page.ID). \
              filter(wp_postmeta_table.c.meta_key=='views'). \
              first()
    if views:
        cm_page.views = views.meta_value
    else:
        cm_page.views = 0

def import_page_tags(wp_page, cm_page, wp_tags_dict):
    wp_tags = get_page_tags(wp_page, wp_tags_dict)
    for wp_tag in wp_tags:
        tag_seo_name = wp_tag
        tag_name = wp_tag.replace('-', ' ')
        cm_page.add_tag(Tag(tag_name, tag_seo_name))

def import_page_category(wp_page, cm_page, wp_categories_dict):
    wp_cat = get_page_category(wp_page)
    cm_page.category = wp_categories_dict[wp_cat].cm_cat
    if wp_page.post_type == 'post' and wp_page.post_status == 'publish':
        cm_page.category.count += 1

def import_page_comments(wp_page, cm_page_id, wp_comments_dict):
    for comment in wp_comments_dict[wp_page.ID]:
        # fake request
        request = MakoDict({
                    'remote_addr': comment.comment_author_IP,
                    'headers': '' })
        visitor = Visitor(request)
        visitor.timestamp = comment.comment_date
        Comment(cm_page_id, comment.comment_author,
                comment.comment_content,
                visitor,
                email=comment.comment_author_email,
                website=comment.comment_author_url,
                timestamp=comment.comment_date).save()

def generate_urlmap(wp_page, cm_page_id):
    parsed = urlparse(wp_page.guid)
    path = parsed.path.rstrip('/')
    if path:
        UrlMap(parsed.path.rstrip('/'), cm_page_id).save()
    elif wp_page.ID==2: # 2nd post for some reason doesn't have a path in my db
        UrlMap('/about', cm_page_id).save()
    
def insert_blogpage(wp_page, cm_page):
    if wp_page.post_type == 'post' and wp_page.post_status == 'publish':
        BlogPage(cm_page, cm_page.created).save()

def insert_rss(wp_page, cm_page):
    if wp_page.post_type == 'post' and wp_page.post_status == 'publish':
        Rss(cm_page, cm_page.created).save()

def get_wp_pages():
    flush_write("Getting wordpress pages. ")
    pages = session. \
              query(wp_pages_table). \
              filter(wp_pages_table.c.post_type.in_(['page', 'post'])). \
              order_by(wp_pages_table.c.ID.asc()). \
              all()
    flush_write("Got %d wordpress pages.\n" % len(pages))
    return pages

def get_wp_tags():
    flush_write("Getting wordpress tags. ")
    all_tags = session.query(wp_tags_table).all()
    wp_tags_dict = dict([t.tag_ID, t.tag] for t in all_tags)
    flush_write("Got %d wordpress tags.\n" % len(wp_tags_dict))
    return wp_tags_dict

def get_wp_comments():
    flush_write("Getting wordpress comments. ")
    all_comments = session.query(wp_comments_table). \
                     filter(wp_comments_table.c.comment_type==''). \
                     filter(wp_comments_table.c.comment_approved=='1'). \
                     order_by(wp_comments_table.c.comment_ID.asc()). \
                     all()
    wp_comments_dict = defaultdict(list)
    for comment in all_comments:
        wp_comments_dict[comment.comment_post_ID].append(comment)
    flush_write("Got %d wordpress comments.\n" % len(all_comments))
    return wp_comments_dict

def get_wp_categories():
    flush_write("Getting wordpress categories. ")
    all_categories = session.query(wp_categories_table). \
                       filter(wp_categories_table.c.category_count>0). \
                       all()
    wp_cat_dict = dict([c.cat_ID, c] for c in all_categories)
    flush_write("Got %d wordpress categories.\n" % len(wp_cat_dict))
    return wp_cat_dict

def get_wp_downloads():
    flush_write("Getting wordpress downloads. ")
    wp_downloads = session.query(wp_downloads_table). \
                    order_by(wp_downloads_table.c.id).all()
    flush_write("Got %d wordpress downloads.\n" % len(wp_downloads))
    return wp_downloads

def get_page_tags(page, wp_tags):
    tags = session. \
             query(wp_post2tag_table). \
             filter(wp_post2tag_table.c.post_id==page.ID). \
             all()
    ids = [tag.tag_id for tag in tags]
    return [wp_tags[id] for id in ids]

def get_page_category(page):
    cats = session. \
             query(wp_post2cat_table). \
             filter(wp_post2cat_table.c.post_id==page.ID). \
             first()
    return cats.category_id

if __name__ == "__main__":
    wordpress_to_catonmat()


########NEW FILE########
__FILENAME__ = start-server
#!/usr/bin/python
#

import sys
from werkzeug import run_simple
from catonmat.application import application

port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
run_simple('0.0.0.0', port, application,
    use_debugger=True, use_reloader=True)


########NEW FILE########
__FILENAME__ = page_comment_tests
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#

from BeautifulSoup import BeautifulSoup as BS
import os

# ---------------------------------------------------------------------------

def slurp_file(filename):
    return file(filename).read()

def simplify_bs(bs):
    ret = []
    for item in bs:
        if isinstance(item, basestring):
            item = item.strip()
            if item:
                ret.append(item.replace('\r', '').replace('\n', ''))
        else:
            ret.append([item.name, simplify_bs(item.contents)])
    return ret

def equal_bs(bs1, bs2):
    return bs1 == bs2

def run_parser_tests(path_to_files, parser):
    success = True
    test_files = os.listdir(path_to_files)
    input_files = sorted(f for f in test_files if f.endswith('.input'))
    for input_file in input_files:
        input_file_path = os.path.join(path_to_files, input_file)
        output_file_path = input_file_path.replace('.input', '.output')

        input = slurp_file(input_file_path)
        
        parsed_input = parser(input)
        expected_output = slurp_file(output_file_path)

        input_bs =  BS(parsed_input)
        output_bs = BS(expected_output)

        simplified_input_bs = simplify_bs(input_bs)
        simplified_output_bs = simplify_bs(output_bs)

        status = equal_bs(simplified_input_bs, simplified_output_bs)

        if status:
            print "Success: %s." % input_file
        else:
            print "Failed: %s." % input_file
            print "Expected:", simplified_output_bs
            print "Got_____:", simplified_input_bs
            success = False
    return success



########NEW FILE########
__FILENAME__ = test-comment-parser
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#

import sys
sys.path.append('/home/pkrumins/catonmat')

from tests.page_comment_tests import run_parser_tests
from catonmat.parser import parse_comment

# ---------------------------------------------------------------------------

PATH = '/home/pkrumins/catonmat/tests/comment-parser'

def run_tests():
    success = run_parser_tests(PATH, parse_comment)
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    run_tests()


########NEW FILE########
__FILENAME__ = test-page-parser
#!/usr/bin/python
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# The new catonmat.net website.
#
# Code is licensed under GNU GPL license.
#

import sys
sys.path.append('/home/pkrumins/catonmat')

from tests.page_comment_tests import run_parser_tests
from catonmat.parser import parse_page

# ---------------------------------------------------------------------------

PATH = '/home/pkrumins/catonmat/tests/page-parser'

def run_tests():
    success = run_parser_tests(PATH, parse_page)
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    run_tests()


########NEW FILE########
