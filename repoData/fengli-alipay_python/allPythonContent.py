__FILENAME__ = urls
# These URLs are normally mapped to /admin/urls.py. This URLs file is
# provided as a convenience to those who want to deploy these URLs elsewhere.
# This file is also used to provide a reliable view deployment for test purposes.

from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^login/$', 'django.contrib.auth.views.login'),
    (r'^logout/$', 'django.contrib.auth.views.logout'),
    (r'^password_change/$', 'django.contrib.auth.views.password_change'),
    (r'^password_change/done/$', 'django.contrib.auth.views.password_change_done'),
    (r'^password_reset/$', 'django.contrib.auth.views.password_reset'),
    (r'^password_reset/done/$', 'django.contrib.auth.views.password_reset_done'),
    (r'^reset/(?P<uidb36>[0-9A-Za-z]{1,13})-(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$', 'django.contrib.auth.views.password_reset_confirm'),
    (r'^reset/done/$', 'django.contrib.auth.views.password_reset_complete'),
)


########NEW FILE########
__FILENAME__ = alipay
# -*- coding: utf-8 -*-
'''
Created on 2011-4-21
支付宝接口
@author: Yefe
'''
import types
from urllib import urlencode, urlopen
from hashcompat import md5_constructor as md5
from config import settings

def smart_str(s, encoding='utf-8', strings_only=False, errors='strict'):
    """
    Returns a bytestring version of 's', encoded as specified in 'encoding'.

    If strings_only is True, don't convert (some) non-string-like objects.
    """
    if strings_only and isinstance(s, (types.NoneType, int)):
        return s
    if not isinstance(s, basestring):
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

# 网关地址
_GATEWAY = 'https://mapi.alipay.com/gateway.do?'


# 对数组排序并除去数组中的空值和签名参数
# 返回数组和链接串
def params_filter(params):
    ks = params.keys()
    ks.sort()
    newparams = {}
    prestr = ''
    for k in ks:
        v = params[k]
        k = smart_str(k, settings.ALIPAY_INPUT_CHARSET)
        if k not in ('sign','sign_type') and v != '':
            newparams[k] = smart_str(v, settings.ALIPAY_INPUT_CHARSET)
            prestr += '%s=%s&' % (k, newparams[k])
    prestr = prestr[:-1]
    return newparams, prestr


# 生成签名结果
def build_mysign(prestr, key, sign_type = 'MD5'):
    if sign_type == 'MD5':
        return md5(prestr + key).hexdigest()
    return ''


# 即时到账交易接口
def create_direct_pay_by_user(tn, subject, body, total_fee):
    params = {}
    params['service']       = 'create_direct_pay_by_user'
    params['payment_type']  = '1'
    
    # 获取配置文件
    params['partner']           = settings.ALIPAY_PARTNER
    params['seller_email']      = settings.ALIPAY_SELLER_EMAIL
    params['return_url']        = settings.ALIPAY_RETURN_URL
    params['notify_url']        = settings.ALIPAY_NOTIFY_URL
    params['_input_charset']    = settings.ALIPAY_INPUT_CHARSET
    params['show_url']          = settings.ALIPAY_SHOW_URL
    
    # 从订单数据中动态获取到的必填参数
    params['out_trade_no']  = tn        # 请与贵网站订单系统中的唯一订单号匹配
    params['subject']       = subject   # 订单名称，显示在支付宝收银台里的“商品名称”里，显示在支付宝的交易管理的“商品名称”的列表里。
    params['body']          = body      # 订单描述、订单详细、订单备注，显示在支付宝收银台里的“商品描述”里
    params['total_fee']     = total_fee # 订单总金额，显示在支付宝收银台里的“应付总额”里
    
    # 扩展功能参数——网银提前
    params['paymethod'] = 'directPay'   # 默认支付方式，四个值可选：bankPay(网银); cartoon(卡通); directPay(余额); CASH(网点支付)
    params['defaultbank'] = ''          # 默认网银代号，代号列表见http://club.alipay.com/read.php?tid=8681379
    
    # 扩展功能参数——防钓鱼
    params['anti_phishing_key'] = ''
    params['exter_invoke_ip'] = ''
    
    # 扩展功能参数——自定义参数
    params['buyer_email'] = ''
    params['extra_common_param'] = ''
    
    # 扩展功能参数——分润
    params['royalty_type'] = ''
    params['royalty_parameters'] = ''
    
    params,prestr = params_filter(params)
    
    params['sign'] = build_mysign(prestr, settings.ALIPAY_KEY, settings.ALIPAY_SIGN_TYPE)
    params['sign_type'] = settings.ALIPAY_SIGN_TYPE
    
    return _GATEWAY + urlencode(params)


# 纯担保交易接口
def create_partner_trade_by_buyer (tn, subject, body, price):
    params = {}
    # 基本参数
    params['service']       = 'create_partner_trade_by_buyer'
    params['partner']           = settings.ALIPAY_PARTNER
    params['_input_charset']    = settings.ALIPAY_INPUT_CHARSET
    params['notify_url']        = settings.ALIPAY_NOTIFY_URL
    params['return_url']        = settings.ALIPAY_RETURN_URL

    # 业务参数
    params['out_trade_no']  = tn        # 请与贵网站订单系统中的唯一订单号匹配
    params['subject']       = subject   # 订单名称，显示在支付宝收银台里的“商品名称”里，显示在支付宝的交易管理的“商品名称”的列表里。
    params['payment_type']  = '1'
    params['logistics_type'] = 'POST'   # 第一组物流类型
    params['logistics_fee'] = '0.00'
    params['logistics_payment'] = 'BUYER_PAY'
    params['price'] = price             # 订单总金额，显示在支付宝收银台里的“应付总额”里
    params['quantity'] = 1              # 商品的数量
    params['seller_email']      = settings.ALIPAY_SELLER_EMAIL
    params['body']          = body      # 订单描述、订单详细、订单备注，显示在支付宝收银台里的“商品描述”里
    params['show_url'] = settings.ALIPAY_SHOW_URL
    
    params,prestr = params_filter(params)
    
    params['sign'] = build_mysign(prestr, settings.ALIPAY_KEY, settings.ALIPAY_SIGN_TYPE)
    params['sign_type'] = settings.ALIPAY_SIGN_TYPE
    
    return _GATEWAY + urlencode(params)

# 确认发货接口
def send_goods_confirm_by_platform (tn):
    params = {}

    # 基本参数
    params['service']       = 'send_goods_confirm_by_platform'
    params['partner']           = settings.ALIPAY_PARTNER
    params['_input_charset']    = settings.ALIPAY_INPUT_CHARSET

    # 业务参数
    params['trade_no']  = tn
    params['logistics_name'] = u'银河列车'   # 物流公司名称
    params['transport_type'] = u'POST'
    
    params,prestr = params_filter(params)
    
    params['sign'] = build_mysign(prestr, settings.ALIPAY_KEY, settings.ALIPAY_SIGN_TYPE)
    params['sign_type'] = settings.ALIPAY_SIGN_TYPE
    
    return _GATEWAY + urlencode(params)

def notify_verify(post):
    # 初级验证--签名
    _,prestr = params_filter(post)
    mysign = build_mysign(prestr, settings.ALIPAY_KEY, settings.ALIPAY_SIGN_TYPE)
    if mysign != post.get('sign'):
        return False
    
    # 二级验证--查询支付宝服务器此条信息是否有效
    params = {}
    params['partner'] = settings.ALIPAY_PARTNER
    params['notify_id'] = post.get('notify_id')
    if settings.ALIPAY_TRANSPORT == 'https':
        params['service'] = 'notify_verify'
        gateway = 'https://mapi.alipay.com/gateway.do'
    else:
        gateway = 'http://notify.alipay.com/trade/notify_query.do'
    veryfy_result = urlopen(gateway, urlencode(params)).read()
    if veryfy_result.lower().strip() == 'true':
        return True
    return False


########NEW FILE########
__FILENAME__ = config
#-*- coding:utf-8 -*-

class settings:
  # 安全检验码，以数字和字母组成的32位字符
  ALIPAY_KEY = ''

  ALIPAY_INPUT_CHARSET = 'utf-8'

  # 合作身份者ID，以2088开头的16位纯数字
  ALIPAY_PARTNER = ''

  # 签约支付宝账号或卖家支付宝帐户
  ALIPAY_SELLER_EMAIL = ''

  ALIPAY_SIGN_TYPE = 'MD5'

  # 付完款后跳转的页面（同步通知） 要用 http://格式的完整路径，不允许加?id=123这类自定义参数
  ALIPAY_RETURN_URL=''

  # 交易过程中服务器异步通知的页面 要用 http://格式的完整路径，不允许加?id=123这类自定义参数
  ALIPAY_NOTIFY_URL=''

  ALIPAY_SHOW_URL=''

  # 访问模式,根据自己的服务器是否支持ssl访问，若支持请选择https；若不支持请选择http
  ALIPAY_TRANSPORT='https'

########NEW FILE########
__FILENAME__ = hashcompat
"""
The md5 and sha modules are deprecated since Python 2.5, replaced by the
hashlib module containing both hash algorithms. Here, we provide a common
interface to the md5 and sha constructors, preferring the hashlib module when
available.
"""

try:
    import hashlib
    md5_constructor = hashlib.md5
    md5_hmac = md5_constructor
    sha_constructor = hashlib.sha1
    sha_hmac = sha_constructor
except ImportError:
    import md5
    md5_constructor = md5.new
    md5_hmac = md5
    import sha
    sha_constructor = sha.new
    sha_hmac = sha

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/python
from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = models
#-*- coding:utf-8 -*-

from django.db import models
from django.contrib.auth.models import User
from django.contrib import admin
import datetime

ACCOUNT_TYPE={'free':u'免费账户','bronze':u'付费订阅(bronze)','silver':u'付费订阅(silver)','gold':u'付费订阅(gold)'}

class Bill (models.Model):
  user = models.OneToOneField (User)
  account_type = models.CharField (max_length=20, default='free', null=True)
  upgrade_type = models.CharField (max_length=20, default='free', null=True)

  # It'll be one of the 4 status ('WAIT_BUYER_PAY', 'WAIT_SELLER_SEND_GOODS',
  # 'WAIT_BUYER_CONFIRM_GOODS', 'TRADE_FINISHED', 'TRADE_CLOSED'), the inital
  # status will be 'INIT'.
  trade_status = models.CharField (max_length=50, default='INIT', null=True)
  start_date = models.DateTimeField (default=datetime.datetime(1900,1,1))
  expire_date = models.DateTimeField (default=datetime.datetime(1900,1,1))

  def __unicode__ (self):
    return self.user.username+" "+self.account_type
admin.site.register (Bill)

########NEW FILE########
__FILENAME__ = urls
#!/usr/bin/python

from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template

urlpatterns = patterns('',
    url(r'^upgrade/(?P<acc_type>\w+)/$', view = 'payment.views.upgrade_account', name="payment_upgrade_account"),
    url(r'^$', direct_to_template, {'template':'payment/plans.html'},name="payment_upgrade_plans"),
    url(r'^success/$', direct_to_template, {'template':'payment/success.html'}, name="payment_success"),
    url(r'^error/$', direct_to_template, {'template':'payment/error.html'}, name="payment_error"),
    url(r'^return_url$', view = 'payment.views.return_url_handler', name="payment_return_url"),
    url(r'^notify_url$', view = 'payment.views.notify_url_handler', name="payment_notify_url"),
)

########NEW FILE########
__FILENAME__ = views
#-*- coding:utf-8 -*-

from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from alipay.alipay import *
from payment.models import Bill
from settings import LOGGING_PAYMENT
import datetime
import logging
import urllib

logger1 =logging.getLogger(__name__)
logger1.setLevel(logging.INFO)
logger1.addHandler (logging.FileHandler(LOGGING_PAYMENT))

def upgrade_bill (bill, valide_days):
  """
  Upgrade bill BILL valide for VALIDE_DAYS from today. And update
  bill account_type.
  """
  bill.account_type = bill.upgrade_type
  start_date = datetime.datetime.now()
  expire_date=start_date+datetime.timedelta(days=valide_days)
  bill.start_date=start_date
  bill.expire_date=expire_date
  bill.save()

@login_required
def upgrade_account (request, acc_type):
  """
  Request for upgrade account to acc_type. Redirect to alipay
  payment web page due to ACC_TYPE.
  """
  user = request.user
  bill = None
  try: bill = user.bill
  except: bill = Bill (user=user)
  bill.upgrade_type = acc_type
  bill.save()
  tn = bill.pk
  if acc_type == "bronze":
    url=create_partner_trade_by_buyer (tn, u'ikindle杂志订阅(4份)',
                                       u'订阅杂志到你的Kindle， 2.99x6个月', '0.01')
    return HttpResponseRedirect (url)
  elif acc_type == "silver":
    url=create_partner_trade_by_buyer (tn, u'ikindle杂志订阅(6份)',
                                       u'订阅杂志到你的Kindle，3.99x6个月', '0.01')
    return HttpResponseRedirect (url)
  elif acc_type == "gold":
    url=create_partner_trade_by_buyer (tn, u'ikindle杂志订阅(无限制)',
                                       u'订阅杂志到你的Kindle，5.99x6个月', '0.01')
    return HttpResponseRedirect (url)
  else:
    return HttpResponseRedirect (reverse ('payment_error'))

from django.views.decorators.csrf import csrf_exempt
@csrf_exempt
def notify_url_handler (request):
  """
  Handler for notify_url for asynchronous updating billing information.
  Logging the information.
  """
  logger1.info ('>>notify url handler start...')
  if request.method == 'POST':
    if notify_verify (request.POST):
      logger1.info ('pass verification...')
      tn = request.POST.get('out_trade_no')
      logger1.info('Change the status of bill %s'%tn)
      bill = Bill.objects.get (pk=tn)
      trade_status = request.POST.get('trade_status')
      logger1.info('the status of bill %s changed to %s'% (tn,trade_status))
      bill.trade_status = trade_status
      bill.save ()
      trade_no=request.POST.get('trade_no')
      if trade_status == 'WAIT_SELLER_SEND_GOODS':
        logger1.info ('It is WAIT_SELLER_SEND_GOODS, so upgrade bill')
        upgrade_bill (bill, 6*30+7)
        url = send_goods_confirm_by_platform (trade_no)
        logger1.info('send goods confirmation. %s'%url)        
        req=urllib.urlopen (url)
        return HttpResponse("success")
      else:
        logger1.info ('##info: Status of %s' % trade_status)
        return HttpResponse ("success")
  return HttpResponse ("fail")

def return_url_handler (request):
  """
  Handler for synchronous updating billing information.
  """
  logger1.info('>> return url handler start')
  if notify_verify (request.GET):
    tn = request.GET.get('out_trade_no')
    trade_no = request.GET.get('trade_no')
    logger1.info('Change the status of bill %s'%tn)
    bill = Bill.objects.get (pk=tn)
    trade_status = request.GET.get('trade_status')
    logger1.info('the status changed to %s'%trade_status)
    bill.trade_status = trade_status
    upgrade_bill (bill, 30*6+7)
    url=send_goods_confirm_by_platform (trade_no)
    req=urllib.urlopen (url)
    logger1.info('send goods confirmation. %s'%url)
    return HttpResponseRedirect (reverse ('payment_success'))
  return HttpResponseRedirect (reverse ('payment_error'))

########NEW FILE########
__FILENAME__ = settings
# Django settings for alipay_python project.
import os

CUR_DIR = os.path.dirname(__file__)
ROOT_PATH = os.path.dirname (CUR_DIR)

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': os.path.join (CUR_DIR, 'db/sqlite3.db'),                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '4@whpmcqsh=o_jn9m-_ysg)-d-qd80pacsd1q-ihhe(89!!i(('

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'alipay_python.urls'

TEMPLATE_DIRS = (
    os.path.join (ROOT_PATH, "alipay_python/templates")  
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'payment',
    'accounts',
)

LOGGING_PAYMENT = 'payment.log'

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
import settings

from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    (r'^', include('alipay_python.payment.urls')),
    # (r'^media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT }),
    (r'^admin/', include(admin.site.urls)),
    (r'^accounts/', include('alipay_python.accounts.urls')),                       
)

########NEW FILE########
