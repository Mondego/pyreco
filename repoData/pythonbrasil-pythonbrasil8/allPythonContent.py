__FILENAME__ = accepted
#!/usr/bin/env python
# coding: utf-8

from pythonbrasil8.schedule.models import Session


approved_talks = [83, 92, 68, 102, 18, 62, 39, 99, 112, 2, 12, 81, 35, 42, 17, 97,
                  103, 126, 57, 58, 69, 71, 95, 24, 63, 108, 80, 38, 107, 9, 1,
                  123, 5, 31, 22, 73, 91, 124, 8, 34, 48, 120, 128, 113, 3, 79,
                  51, 19, 21, 26, 50, 114]

approved_tutorials = [78, 93, 59, 6, 86, 32, 105, 89, 60, 131, 132, 133]

for session in Session.objects.all():
    if session.id in approved_talks or session.id in approved_tutorials:
        session.status = u'accepted' # WTF?
    else:
        session.status = u'proposed'
    session.save()
    print session.type, session.status, session.id, session.title.encode('utf-8')

########NEW FILE########
__FILENAME__ = email_talk_confirmation
#!/usr/bin/env python
# coding: utf-8

import getpass
import smtplib
import sys
import time

from pythonbrasil8.schedule.models import Session


remetente = u'"Organização PythonBrasil[8]" <organizacao@python.org.br>'
msg = u'''Subject: Confirmação de palestra: "{PALESTRA}"
From: {REMETENTE}
To: {EMAIL}

Olá,

Parabéns! A palestra abaixo foi aprovada na PythonBrasil[8]:
    {PALESTRA}

Em breve enviaremos dia e horário da palestra.

Necessitamos da confirmação dessa palestra no evento - para isso, basta
responder a esse email com "sim" ou "não".

Lembramos que sua inscrição no evento será confirmada quando o pagamento for
efetuado (o valor promocional para palestrantes é de R$ 150,00).  Pedimos a
gentileza que verifique o estado de sua inscrição em:
    http://2012.pythonbrasil.org.br/dashboard/

Em caso de dúvidas, por favor, entre em contato com o time da organização do
evento através do email <organizacao@python.org.br>.

Até breve!

Atenciosamente,
  Organização PythonBrasil[8]
  http://2012.pythonbrasil.org.br
  http://twitter.com/PythonBrasil
  http://facebook.com/pythonbrasil8'''


class EmailConnection(object):
    def connect(self, smtp_host, smtp_port):
        self.connection = smtplib.SMTP(smtp_host, smtp_port)
        self.connection.ehlo()
        self.connection.starttls()
        self.connection.ehlo()

    def auth(self, username, password):
        self.connection.login(username, password)

    def send_mail(self, from_, to, message):
        return self.connection.sendmail(from_, to, message)

    def close(self):
        self.connection.close()


if __name__ == '__main__':
    smtp_host = 'smtp.gmail.com'
    smtp_port = 587
    #username = raw_input('Digite o username do email: ')
    username = 'organizacao@python.org.br'
    password = getpass.getpass('Digite a senha para <{}>: '.format(username))

    email_connection = EmailConnection()
    email_connection.connect(smtp_host, smtp_port)
    email_connection.auth(username, password)

    i = 0
    for session in Session.objects.filter(type='talk', status='accepted'):
        speakers = session.speakers.all()
        emails = [speaker.email for speaker in speakers]

        a_substituir = {u'EMAIL': u','.join(emails), u'REMETENTE': remetente,
                        u'PALESTRA': session.title}
        mensagem = msg
        for key, value in a_substituir.iteritems():
            mensagem = mensagem.replace(u'{' + key + u'}', value)
        mensagem = mensagem.encode('utf-8')

        i += 1
        sys.stdout.write(u'Enviando email {:02d} sobre "{}" para <{}> ...  '\
                         .format(i, session.title, emails).encode('utf-8'))
        response = email_connection.send_mail(remetente, emails, mensagem)
        print 'OK' if response == {} else response
        time.sleep(1)

    email_connection.close()

########NEW FILE########
__FILENAME__ = fabfile
# -*- coding: utf-8 -*-
import os

from fabric.api import cd, env, run

env.project_root = '/home/pythonbrasil/pythonbrasil8'
env.app_root = os.path.join(env.project_root, 'pythonbrasil8')
env.virtualenv = '/home/pythonbrasil/env'
env.hosts = ['2012.pythonbrasil.org.br']
env.user = 'pythonbrasil'


def update_app(tag):
    with cd(env.project_root):
        run("git pull origin %s" % tag)


def collect_static_files():
    with cd(env.project_root):
        run("DJANGO_SETTINGS_MODULE=pythonbrasil8.settings_local %(virtualenv)s/bin/python manage.py collectstatic -v 0 --noinput" % env)


def pip_install():
    run("%(virtualenv)s/bin/pip install -r %(project_root)s/requirements.txt" % env)


def start():
    with cd(env.project_root):
        run('DJANGO_SETTINGS_MODULE=pythonbrasil8.settings_local %(virtualenv)s/bin/gunicorn --access-logfile=gunicorn-access.log --error-logfile=gunicorn-error.log --pid=gunicorn.pid --bind=127.0.0.1:8080 --daemon --workers=3 pythonbrasil8.wsgi:application' % env)


def reload():
    run('kill -HUP `cat %(project_root)s/gunicorn.pid`' % env)


def stop():
    run('kill -KILL `cat %(project_root)s/gunicorn.pid`' % env)


def syncdb():
    with cd(env.project_root):
        run("DJANGO_SETTINGS_MODULE=pythonbrasil8.settings_local %(virtualenv)s/bin/python manage.py syncdb --noinput" % env)
        run("DJANGO_SETTINGS_MODULE=pythonbrasil8.settings_local %(virtualenv)s/bin/python manage.py migrate --noinput" % env)


def translate():
    with cd(env.app_root):
        run("%(virtualenv)s/bin/django-admin.py compilemessages" % env)


def loaddata():
    with cd(env.project_root):
        run("DJANGO_SETTINGS_MODULE=pythonbrasil8.settings_local %s/bin/python manage.py loaddata fixtures/initial_data.json" % env.virtualenv)


def limpar_pycs():
    with cd(env.project_root):
        run("find . -name \"*.pyc\" | xargs rm -f ")


def deploy(tag="master"):
    update_app(tag)
    pip_install()
    limpar_pycs()
    collect_static_files()
    translate()

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    if os.path.exists(os.path.join(os.path.dirname(__file__), 'pythonbrasil8', 'settings_local.py')):
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pythonbrasil8.settings_local")
    else:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pythonbrasil8.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = pagseguro_transaction
# coding: utf-8
import datetime

import requests
import xmltodict

from django.conf import settings

from pythonbrasil8.subscription import models


class PagSeguro(object):
    URL_TRANSACTIONS = 'https://ws.pagseguro.uol.com.br/v2/transactions'
    URL_TRANSACTION_DETAIL = \
            'https://ws.pagseguro.uol.com.br/v2/transactions/{}'

    def __init__(self, email, token):
        self.__parameters = {'email': email, 'token': token}

    def get_transactions(self, initial_date, final_date):
        '''Get all transactions in the interval

        If more than one page is needed, it automatically gets ALL the pages.
        `initial_date` and `final_date` should be in format
        `YYYY-MM-DDTHH:MM:SS`.
        PagSeguro's API documentation says it must be `YYYY-MM-DDTHH:MM:SS.sz`,
        where 's' is microseconds and 'z' is timezone, but it is not needed and
        it fails in some cases!
        '''
        page = 1
        max_results = 100
        finished = False
        parameters = {'initialDate': initial_date, 'finalDate': final_date,
                      'maxPageResults': max_results}
        parameters.update(self.__parameters)
        transactions = []
        while not finished:
            parameters['page'] = page
            response = requests.get(self.URL_TRANSACTIONS, params=parameters)
            data = xmltodict.parse(response.text.encode('iso-8859-1'))
            result = data['transactionSearchResult']
            if int(result['resultsInThisPage']) > 0:
                new_transactions = result['transactions']['transaction']
                if type(new_transactions) is not list:  # only one returned
                    new_transactions = [new_transactions]
                transactions.extend(new_transactions)
            total_pages = int(result['totalPages'])
            if page < total_pages:
                page += 1
            elif page == total_pages:
                finished = True
        return transactions

    def get_transaction(self, transaction_id):
        '''Given a transaction id, get its information'''
        url = self.URL_TRANSACTION_DETAIL.format(transaction_id)
        response = requests.get(url, params=self.__parameters)
        print response.status_code, response.text
        return xmltodict.parse(response.text.encode('iso-8859-1'))['transaction']

if __name__ == '__main__':
    email = settings.PAGSEGURO["email"]
    token = settings.PAGSEGURO["token"]
    ps = PagSeguro(email, token)

    def get_all_transactions():
        '''Get past transactions and save it to a CSV file

        PagSeguro only allow us to get 6-months-old transactions.
        '''

        # Get all desired transactions
        now = datetime.datetime.now()
        yesterday = now - datetime.timedelta(days=1)
        start = yesterday.strftime('%Y-%m-%dT%H:%M:%S-02:00')
        end = now.strftime('%Y-%m-%dT%H:%M:%S-02:00')
        whole_transactions = ps.get_transactions(start, end)

        paid = [t for t in whole_transactions
                if 'reference' in t
                and t['status'] in ('3', '4')
                and t['grossAmount'] in ('150.00', '250.00', '350.00')]
        for transaction in paid:
            subscription_id = transaction['reference']
            transactions = models.Transaction.objects.select_related('subscription').filter(
                subscription_id=subscription_id,
                price=float(transaction['grossAmount']),
            )
            update = None
            for transaction in transactions:
                if transaction.status == 'pending':
                    update = transaction
                elif transaction.status == 'done':
                    update = None
                    break
            if update:
                update.status = 'done'
                update.save()
                update.subscription.status = 'confirmed'
                update.subscription.save()
    get_all_transactions()

########NEW FILE########
__FILENAME__ = mail
# -*- coding: utf-8 -*-
import threading

from django.core import mail


class MailSender(object):

    def __init__(self, sender, receivers, subject, body):
        self.sender = sender
        self.receivers = receivers
        self.subject = subject
        self.body = body

    def send_mail(self):
        kw = {
            "subject": self.subject,
            "message": self.body,
            "recipient_list": self.receivers,
            "from_email": self.sender,
            "fail_silently": True,
        }
        self.t = threading.Thread(target=mail.send_mail, kwargs=kw)
        self.t.start()

    def wait(self, timeout=None):
        if timeout is None:
            self.t.join()
            return True
        self.t.join(timeout)
        return not self.t.isAlive()


def send(sender, receivers, subject, body):
    m = MailSender(sender, receivers, subject, body)
    m.send_mail()
    return m

########NEW FILE########
__FILENAME__ = middleware
# -*- coding: utf-8 -*-

from django.conf import settings


class CacheMiddleware(object):

    def process_response(self, request, response):
        if not hasattr(request, "user") or request.user.is_authenticated():
            response["Cache-Control"] = "no-cache"
            return response

        if not response.get("Cache-Control"):
            response["Cache-Control"] = "max-age=%d" % settings.PAGE_CACHE_MAXAGE

        if response.get("Vary") and "Cookie" in response["Vary"]:
            parts = response["Vary"].split(", ")
            parts.remove("Cookie")
            response["Vary"] = ", ".join(parts)

        return response

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-

########NEW FILE########
__FILENAME__ = menu
from django import template
from django.core.urlresolvers import reverse

register = template.Library()


@register.simple_tag
def is_active(current_path, urls):
    if current_path in (reverse(url) for url in urls.split()):
        return "active"
    return ""

########NEW FILE########
__FILENAME__ = setting
# coding: utf-8

from django.conf import settings
from django import template

register = template.Library()


class SettingNode(template.Node):
    def __init__(self, name, asvar):
        self.name = name

        self.asvar = asvar

    def render(self, context):
        if self.asvar:
            context[self.asvar] = getattr(settings, self.name)
            return ''

        else:
            return getattr(settings, self.name)


@register.tag
def setting(parser, token):
    bits = token.split_contents()
    viewname = bits[1]
    asvar = None
    if (viewname.startswith('"') and viewname.endswith('"')) or (viewname.startswith('\'') and viewname.endswith('\'')):
        viewname = viewname[1:-1]

    if len(bits) == 4:
        if bits[2] == 'as':
            asvar = bits[3]
        else:
            raise template.TemplateSyntaxError("usage: {% setting FOO as foo %} or {% setting FOO %}")
    elif len(bits) not in (2, 4):
        raise template.TemplateSyntaxError("usage: {% setting FOO as foo %} or {% setting FOO %}")
    return SettingNode(viewname, asvar)

########NEW FILE########
__FILENAME__ = mocks
# -*- coding: utf-8 -*-


class ResponseMock(dict):

    def __init__(self, *args, **kwargs):
        super(ResponseMock, self).__init__(*args, **kwargs)
        self['Content-Type'] = 'text/html'

    status_code = 200

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
from datetime import date
from django.views.generic import ListView
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required

#from mittun.sponsors.views import SponsorsView
from mittun.sponsors.models import Sponsor, Category, Job
from mittun.events.models import Event

from pythonbrasil8.news.models import Post


class CustomSponsorsView(ListView):

    template_name = "sponsors.html"
    model = Sponsor

    def get_context_data(self, **kwargs):
        context = super(CustomSponsorsView, self).get_context_data(**kwargs)
        context['sponsors_categories'] = Category.objects.all().order_by('priority')
        return context


class Home(ListView):
    model = Sponsor
    template_name = 'home.html'

    def sponsor_groups(self):
        groups = []
        sponsors = list(Sponsor.objects.select_related('category').all().order_by('category__priority', 'pk'))

        while sponsors:
            row = sponsors[:6]
            sponsors = sponsors[6:]
            groups.append(row)
        return groups

    def get_context_data(self, **kwargs):
        context = super(Home, self).get_context_data(**kwargs)
        context['sponsor_groups'] = self.sponsor_groups()
        context['event'] = Event.objects.all()[0]
        context['posts'] = Post.objects.filter(published_at__lte=date.today()).order_by('-published_at')[:5]
        return context


class AboutView(TemplateView):
    template_name = 'about.html'


class ScheduleView(TemplateView):
    template_name = 'schedule.html'


class VenueView(TemplateView):
    template_name = 'venue.html'


class SponsorsInfoView(TemplateView):
    template_name = 'sponsors_info.html'


class SponsorsJobsView(ListView):
    template_name = 'sponsors_jobs.html'
    model = Job
    context_object_name = 'jobs'


class LoginRequiredMixin(object):
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(LoginRequiredMixin, self).dispatch(*args, **kwargs)

########NEW FILE########
__FILENAME__ = admin
# -*- coding: utf-8 -*-
from django.contrib import admin

from pythonbrasil8.dashboard import models


class AccountProfileAdmin(admin.ModelAdmin):
    list_display = ["name", "user"]
    search_fields = ["name"]
    list_filter = ["type"]

admin.site.register(models.AccountProfile, AccountProfileAdmin)

########NEW FILE########
__FILENAME__ = choices
# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy


ATTENDANT_CHOICES = (
    ('Corporate', ugettext_lazy('Corporate')),
    ('Individual', ugettext_lazy('Individual')),
    ('Student', ugettext_lazy('Student')),
    ('APyB Associated', ugettext_lazy('APyB Associated'))
)

T_SHIRT_CHOICES = (
    (ugettext_lazy('Female'), (
            ('S', ugettext_lazy('S')),
            ('M', ugettext_lazy('M')),
            ('L', ugettext_lazy('L')),
        )
    ),
    (ugettext_lazy('Male'), (
            ('S', ugettext_lazy('S')),
            ('M', ugettext_lazy('M')),
            ('L', ugettext_lazy('L')),
            ('XL', ugettext_lazy('XL')),
            ('XXL', ugettext_lazy('XXL')),
        )
    )
)

GENDER_CHOICES = (
    ('female', ugettext_lazy('Female')),
    ('male', ugettext_lazy('Male')),
    ('other', ugettext_lazy('Other'))
)

AGE_CHOICES = (
    ('--9', ugettext_lazy('9 or less')),
    ('10-19', '10-19'),
    ('20-29', '20-29'),
    ('30-39', '30-39'),
    ('40-49', '40-49'),
    ('50-59', '50-59'),
    ('60-69', '60-69'),
    ('70-79', '70-79'),
    ('80-+', ugettext_lazy('80 or more')),
)

PROFESSION_CHOICES = (
    ('student', ugettext_lazy('Student')),
    ('trainee', ugettext_lazy('Trainee')),
    ('developer', ugettext_lazy('Developer')),
    ('software engineer', ugettext_lazy('Software engineer')),
    ('manager', ugettext_lazy('Manager')),
    ('sysadmin', ugettext_lazy('Sysadmin')),
    ('teacher', ugettext_lazy('Teacher')),
    ('researcher', ugettext_lazy('Researcher')),
    ('other', ugettext_lazy('Other')),
)

LOCALE_CHOICES = (
    ('AC', 'Acre'),
    ('AL', 'Alagoas'),
    ('AM', 'Amazonas'),
    ('AP', 'Amapá'),
    ('BA', 'Bahia'),
    ('CE', 'Ceará'),
    ('DF', 'Distrito Federal'),
    ('ES', 'Espírito Santo'),
    ('GO', 'Goiás'),
    ('MA', 'Maranhão'),
    ('MS', 'Mato Grosso do Sul'),
    ('MT', 'Mato Grosso'),
    ('MG', 'Minas Gerais'),
    ('PA', 'Pará'),
    ('PB', 'Paraíba'),
    ('PE', 'Pernambuco'),
    ('PI', 'Piauí'),
    ('PR', 'Paraná'),
    ('RJ', 'Rio de Janeiro'),
    ('RN', 'Rio Grande do Norte'),
    ('RO', 'Rondônia'),
    ('RR', 'Roraima'),
    ('RS', 'Rio Grande do Sul'),
    ('SC', 'Santa Catarina'),
    ('SE', 'Sergipe'),
    ('SP', 'São Paulo'),
    ('TO', 'Tocantins'),
    ('00', ugettext_lazy('Other country'))
)

########NEW FILE########
__FILENAME__ = forms
# -*- coding: utf-8 -*-
from django.forms import ModelForm, Textarea

from pythonbrasil8.dashboard.models import AccountProfile


class ProfileForm(ModelForm):

    class Meta:
        model = AccountProfile
        exclude = ('user', 'payement',)
        widgets = {
            'description': Textarea,
        }


class SpeakerProfileForm(ProfileForm):

    class Meta(ProfileForm.Meta):
        exclude = ('user', 'payement', 'type')

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Adding model 'AccountProfile'
        db.create_table('dashboard_accountprofile', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['auth.User'], unique=True)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('tshirt', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('locale', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('gender', self.gf('django.db.models.fields.CharField')(max_length=20, null=True, blank=True)),
            ('age', self.gf('django.db.models.fields.CharField')(max_length=20, null=True, blank=True)),
            ('profession', self.gf('django.db.models.fields.CharField')(max_length=50, null=True, blank=True)),
            ('institution', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('payement', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('dashboard', ['AccountProfile'])

    def backwards(self, orm):
        # Deleting model 'AccountProfile'
        db.delete_table('dashboard_accountprofile')

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 4, 28, 23, 48, 10, 524432)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 4, 28, 23, 48, 10, 524237)'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'dashboard.accountprofile': {
            'Meta': {'object_name': 'AccountProfile'},
            'age': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'gender': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'institution': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'locale': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'payement': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'profession': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'tshirt': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'})
        }
    }

    complete_apps = ['dashboard']

########NEW FILE########
__FILENAME__ = 0002_auto__add_field_accountprofile_name
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'AccountProfile.name'
        db.add_column('dashboard_accountprofile', 'name', self.gf('django.db.models.fields.CharField')(default=datetime.date(2012, 5, 5), max_length=20), keep_default=False)

    def backwards(self, orm):
        # Deleting field 'AccountProfile.name'
        db.delete_column('dashboard_accountprofile', 'name')

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 5, 5, 9, 40, 14, 278467)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 5, 5, 9, 40, 14, 278356)'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'dashboard.accountprofile': {
            'Meta': {'object_name': 'AccountProfile'},
            'age': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'gender': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'institution': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'locale': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'payement': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'profession': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'tshirt': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'})
        }
    }

    complete_apps = ['dashboard']

########NEW FILE########
__FILENAME__ = 0003_auto__add_field_accountprofile_twitter__add_field_accountprofile_publi
# encoding: utf-8
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'AccountProfile.twitter'
        db.add_column('dashboard_accountprofile', 'twitter', self.gf('django.db.models.fields.CharField')(max_length=15, null=True, blank=True), keep_default=False)

        # Adding field 'AccountProfile.public'
        db.add_column('dashboard_accountprofile', 'public', self.gf('django.db.models.fields.BooleanField')(default=True), keep_default=False)

    def backwards(self, orm):
        # Deleting field 'AccountProfile.twitter'
        db.delete_column('dashboard_accountprofile', 'twitter')

        # Deleting field 'AccountProfile.public'
        db.delete_column('dashboard_accountprofile', 'public')

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 6, 2, 14, 42, 9, 373109)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 6, 2, 14, 42, 9, 372985)'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'dashboard.accountprofile': {
            'Meta': {'object_name': 'AccountProfile'},
            'age': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'gender': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'institution': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'locale': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'payement': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'profession': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'tshirt': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'twitter': ('django.db.models.fields.CharField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'})
        }
    }

    complete_apps = ['dashboard']

########NEW FILE########
__FILENAME__ = 0004_auto__chg_field_accountprofile_description__chg_field_accountprofile_l
# encoding: utf-8
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'AccountProfile.description'
        db.alter_column('dashboard_accountprofile', 'description', self.gf('django.db.models.fields.CharField')(max_length=500))

        # Changing field 'AccountProfile.locale'
        db.alter_column('dashboard_accountprofile', 'locale', self.gf('django.db.models.fields.CharField')(default='RJ', max_length=255))

        # Changing field 'AccountProfile.gender'
        db.alter_column('dashboard_accountprofile', 'gender', self.gf('django.db.models.fields.CharField')(default='other', max_length=20))

    def backwards(self, orm):

        # Changing field 'AccountProfile.description'
        db.alter_column('dashboard_accountprofile', 'description', self.gf('django.db.models.fields.CharField')(max_length=20))

        # Changing field 'AccountProfile.locale'
        db.alter_column('dashboard_accountprofile', 'locale', self.gf('django.db.models.fields.CharField')(max_length=255, null=True))

        # Changing field 'AccountProfile.gender'
        db.alter_column('dashboard_accountprofile', 'gender', self.gf('django.db.models.fields.CharField')(max_length=20, null=True))

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 6, 5, 0, 28, 44, 902430)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 6, 5, 0, 28, 44, 902165)'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'dashboard.accountprofile': {
            'Meta': {'object_name': 'AccountProfile'},
            'age': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'gender': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'institution': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'locale': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'payement': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'profession': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'tshirt': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'twitter': ('django.db.models.fields.CharField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'})
        }
    }

    complete_apps = ['dashboard']

########NEW FILE########
__FILENAME__ = 0005_auto__add_field_accountprofile_country
# encoding: utf-8
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):
        db.add_column('dashboard_accountprofile', 'country', self.gf('django.db.models.fields.CharField')(max_length=50, null=True, blank=True), keep_default=False)

    def backwards(self, orm):
        db.delete_column('dashboard_accountprofile', 'country')

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 6, 24, 21, 51, 36, 253156)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 6, 24, 21, 51, 36, 253054)'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'dashboard.accountprofile': {
            'Meta': {'object_name': 'AccountProfile'},
            'age': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'country': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'gender': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'institution': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'locale': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'payement': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'profession': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'tshirt': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'twitter': ('django.db.models.fields.CharField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'})
        }
    }

    complete_apps = ['dashboard']

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
from django.contrib.auth.models import User
from django.db import models as django_models
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy

from pythonbrasil8.dashboard import choices
from pythonbrasil8.subscription import models
from registration.signals import user_activated


class CompleteSubscriptionException(Exception):
    pass


class AccountProfile(django_models.Model):
    user = django_models.OneToOneField(User)
    name = django_models.CharField(max_length=20, verbose_name=ugettext_lazy(u"Name"))
    description = django_models.CharField(max_length=500, verbose_name=ugettext_lazy(u"Short Bio"))
    type = django_models.CharField(max_length=50, choices=choices.ATTENDANT_CHOICES, verbose_name=ugettext_lazy(u"Registration type"))
    tshirt = django_models.CharField(max_length=50, choices=choices.T_SHIRT_CHOICES, verbose_name=ugettext_lazy(u"T-Shirt size"))
    locale = django_models.CharField(max_length=255, choices=choices.LOCALE_CHOICES, verbose_name=ugettext_lazy(u"State"))
    country = django_models.CharField(max_length=50, null=True, blank=True, verbose_name=ugettext_lazy(u"Country (if not Brazilian)"))
    gender = django_models.CharField(max_length=20, choices=choices.GENDER_CHOICES, verbose_name=ugettext_lazy(u"Gender"))
    age = django_models.CharField(max_length=20, null=True, blank=True, choices=choices.AGE_CHOICES, verbose_name=ugettext_lazy(u"Age"))
    profession = django_models.CharField(max_length=50, null=True, blank=True, choices=choices.PROFESSION_CHOICES, verbose_name=ugettext_lazy(u"Profession"))
    institution = django_models.CharField(max_length=100, null=True, blank=True, verbose_name=ugettext_lazy(u"Company / University / Institution"))
    payement = django_models.BooleanField(default=False)
    twitter = django_models.CharField(max_length=15, blank=True, null=True, verbose_name=ugettext_lazy(u"Twitter profile"))
    public = django_models.BooleanField(default=True, verbose_name=ugettext_lazy(u"Public profile (visible to everyone)?"))

    def has_talk_subscription(self):
        return self.user.subscription_set.filter(type="talk").exists()

    def talk_subscription(self):
        return self.user.subscription_set.filter(type="talk")[0]

    @property
    def transaction(self):
        subscription = None
        if self.has_talk_subscription():
            subscription = self.talk_subscription()
            if subscription.done():
                raise CompleteSubscriptionException("This subscription is complete.")
            qs = subscription.transaction_set.filter(
                price=models.PRICES[self.type],
                status="pending",
            )
            if qs:
                return qs[0]
        if not subscription:
            subscription = models.Subscription.objects.create(
                user=self.user,
                type="talk",
            )
        subscription.transaction_set.update(status="canceled")
        return models.Transaction.generate(subscription)


@receiver(user_activated)
def create_account_profile(user, request, *args, **kwargs):
    AccountProfile.objects.create(user=user)

########NEW FILE########
__FILENAME__ = test_account
from django.test import TestCase
from django.test.client import RequestFactory
from django.contrib.auth.models import User

from pythonbrasil8.dashboard.models import AccountProfile

from registration.signals import user_activated


class AccountTestCase(TestCase):

    def test_should_create_a_userprofile_when_user_is_activated(self):
        user = User.objects.create(username="ironman")
        request = RequestFactory().get("/")
        user_activated.send(sender=self.__class__, user=user, request=request)
        self.assertTrue(AccountProfile.objects.filter(user=user).exists())

########NEW FILE########
__FILENAME__ = test_admin
# -*- coding: utf-8 -*-
from django import test
from django.contrib import admin as django_admin

from pythonbrasil8.dashboard import admin, models


class AccountProfileAdminTestCase(test.TestCase):

    def test_AccountProfile_is_registered(self):
        self.assertIn(models.AccountProfile, django_admin.site._registry)

    def test_AccountProfile_is_registered_with_AccountProfileAdmin(self):
        self.assertIsInstance(
            django_admin.site._registry[models.AccountProfile],
            admin.AccountProfileAdmin,
        )

    def test_name_is_displayed(self):
        self.assertIn("name", admin.AccountProfileAdmin.list_display)

    def test_user_is_displayed(self):
        self.assertIn("user", admin.AccountProfileAdmin.list_display)

    def test_name_is_used_for_search(self):
        self.assertIn("name", admin.AccountProfileAdmin.search_fields)

    def test_type_is_used_for_filtering(self):
        self.assertIn("type", admin.AccountProfileAdmin.list_filter)

########NEW FILE########
__FILENAME__ = test_forms
# -*- coding: utf-8 -*-
from django import forms
from django.test import TestCase

from pythonbrasil8.dashboard.forms import ProfileForm, SpeakerProfileForm
from pythonbrasil8.dashboard.models import AccountProfile


class ProfileFormTestCase(TestCase):

    def test_model_should_be_AccountProfile(self):
        self.assertEqual(AccountProfile, ProfileForm._meta.model)

    def test_field_user_should_be_exclude(self):
        self.assertIn('user', ProfileForm._meta.exclude)

    def test_field_payement_should_be_exclude(self):
        self.assertIn('payement', ProfileForm._meta.exclude)

    def test_should_use_TextArea_widget_for_description(self):
        self.assertEqual(forms.Textarea, ProfileForm.Meta.widgets['description'])


class SpeakerProfileFormTestCase(TestCase):

    def test_should_inherit_from_ProfileForm(self):
        assert issubclass(SpeakerProfileForm, ProfileForm)

    def test_Meta_should_inherit_from_ProfileForm_meta(self):
        assert issubclass(SpeakerProfileForm.Meta, ProfileForm.Meta)

    def test_should_exclude_everything_that_ProfileForm_excludes(self):
        for f in ProfileForm._meta.exclude:
            self.assertIn(f, SpeakerProfileForm._meta.exclude)

    def test_should_exclude_type(self):
        self.assertIn("type", SpeakerProfileForm._meta.exclude)

########NEW FILE########
__FILENAME__ = test_models
# -*- coding: utf-8 -*-
from django.contrib.auth.models import User
from django.core import management
from django.db import models as django_models
from django.test import TestCase

from pythonbrasil8.dashboard.models import AccountProfile, CompleteSubscriptionException
from pythonbrasil8.subscription import models


class AccountProfileTestCase(TestCase):

    @classmethod
    def setUpClass(self):
        self.field_names = AccountProfile._meta.get_all_field_names()

    def test_should_have_user_field(self):
        self.assertIn('user', self.field_names)

    def test_user_field_should_be_one_to_one_field(self):
        field = AccountProfile._meta.get_field_by_name('user')[0]
        self.assertEqual(django_models.OneToOneField, field.__class__)

    def test_should_have_name(self):
        self.assertIn('name', self.field_names)

    def test_name_should_be_CharField(self):
        field = AccountProfile._meta.get_field_by_name('name')[0]
        self.assertIsInstance(field, django_models.CharField)

    def test_name_should_have_at_most_20_characters(self):
        field = AccountProfile._meta.get_field_by_name('name')[0]
        self.assertEqual(20, field.max_length)

    def test_name_should_have_verbose_name(self):
        field = AccountProfile._meta.get_field_by_name('name')[0]
        self.assertEqual(u"Name", field.verbose_name)

    def test_should_have_description_field(self):
        self.assertIn('description', self.field_names)

    def test_description_field_should_be_char_field(self):
        field = AccountProfile._meta.get_field_by_name('description')[0]
        self.assertEqual(django_models.CharField, field.__class__)

    def test_description_field_should_have_500_of_max_length(self):
        field = AccountProfile._meta.get_field_by_name('description')[0]
        self.assertEqual(500, field.max_length)

    def test_should_have_type_field(self):
        self.assertIn('type', self.field_names)

    def test_type_field_should_be_char_field(self):
        field = AccountProfile._meta.get_field_by_name('type')[0]
        self.assertEqual(django_models.CharField, field.__class__)

    def test_type_field_should_have_expected_choices(self):
        field = AccountProfile._meta.get_field_by_name('type')[0]
        self.assertIn(('Student', 'Student'), field.choices)
        self.assertIn(('APyB Associated', 'APyB Associated'), field.choices)
        self.assertIn(('Individual', 'Individual'), field.choices)

    def test_type_should_have_verbose_name(self):
        field = AccountProfile._meta.get_field_by_name('type')[0]
        self.assertEqual(u"Registration type", field.verbose_name)

    def test_should_have_tshirt_field(self):
        self.assertIn('tshirt', self.field_names)

    def test_tshirt_field_should_be_char_field(self):
        field = AccountProfile._meta.get_field_by_name('tshirt')[0]
        self.assertEqual(django_models.CharField, field.__class__)

    def test_tshirt_field_should_have_expected_choices(self):
        field = AccountProfile._meta.get_field_by_name('tshirt')[0]
        female_choices = (
            'Female', (
                ('S', 'S'),
                ('M', 'M'),
                ('L', 'L'),
            )
        )
        male_choices = (
            'Male', (
                ('S', 'S'),
                ('M', 'M'),
                ('L', 'L'),
                ('XL', 'XL'),
                ('XXL', 'XXL'),
            )
        )

        self.assertIn(female_choices, field.choices)
        self.assertIn(male_choices, field.choices)

    def test_tshirt_field_should_have_verbose_name(self):
        field = AccountProfile._meta.get_field_by_name('tshirt')[0]
        self.assertEqual(u"T-Shirt size", field.verbose_name)

    def test_should_have_locale_field(self):
        self.assertIn('locale', self.field_names)

    def test_locale_field_should_be_char_field(self):
        field = AccountProfile._meta.get_field_by_name('locale')[0]
        self.assertEqual(django_models.CharField, field.__class__)

    def test_locale_field_should_have_verbose_name(self):
        field = AccountProfile._meta.get_field_by_name('locale')[0]
        self.assertEqual(u"State", field.verbose_name)

    def test_locale_field_should_have_brazilian_states_choices(self):
        expected = (
            ('AC', 'Acre'),
            ('AL', 'Alagoas'),
            ('AM', 'Amazonas'),
            ('AP', 'Amapá'),
            ('BA', 'Bahia'),
            ('CE', 'Ceará'),
            ('DF', 'Distrito Federal'),
            ('ES', 'Espírito Santo'),
            ('GO', 'Goiás'),
            ('MA', 'Maranhão'),
            ('MS', 'Mato Grosso do Sul'),
            ('MT', 'Mato Grosso'),
            ('MG', 'Minas Gerais'),
            ('PA', 'Pará'),
            ('PB', 'Paraíba'),
            ('PE', 'Pernambuco'),
            ('PI', 'Piauí'),
            ('PR', 'Paraná'),
            ('RJ', 'Rio de Janeiro'),
            ('RN', 'Rio Grande do Norte'),
            ('RO', 'Rondônia'),
            ('RR', 'Roraima'),
            ('RS', 'Rio Grande do Sul'),
            ('SC', 'Santa Catarina'),
            ('SE', 'Sergipe'),
            ('SP', 'São Paulo'),
            ('TO', 'Tocantins'),
            ('00', 'Other country')
        )
        field = AccountProfile._meta.get_field_by_name('locale')[0]
        self.assertEqual(expected, field.choices)

    def test_should_have_country_field(self):
        self.assertIn('country', self.field_names)

    def test_gender_field_should_be_char_field(self):
        field = AccountProfile._meta.get_field_by_name('country')[0]
        self.assertEqual(django_models.CharField, field.__class__)

    def test_should_have_gender_field(self):
        self.assertIn('gender', self.field_names)

    def test_gender_field_should_be_char_field(self):
        field = AccountProfile._meta.get_field_by_name('gender')[0]
        self.assertEqual(django_models.CharField, field.__class__)

    def test_gender_field_should_have_expected_choices(self):
        field = AccountProfile._meta.get_field_by_name('gender')[0]
        self.assertIn(('female', 'Female'), field.choices)
        self.assertIn(('male', 'Male'), field.choices)
        self.assertIn(('other', 'Other'), field.choices)

    def test_gender_should_have_verbose_name(self):
        field = AccountProfile._meta.get_field_by_name('gender')[0]
        self.assertEqual(u"Gender", field.verbose_name)

    def test_should_have_age_field(self):
        self.assertIn('age', self.field_names)

    def test_age_field_should_be_char_field(self):
        field = AccountProfile._meta.get_field_by_name('age')[0]
        self.assertEqual(django_models.CharField, field.__class__)

    def test_age_field_should_have_expected_choices(self):
        field = AccountProfile._meta.get_field_by_name('age')[0]
        self.assertIn(('--9', '9 or less'), field.choices)
        self.assertIn(('10-19', '10-19'), field.choices)
        self.assertIn(('20-29', '20-29'), field.choices)
        self.assertIn(('30-39', '30-39'), field.choices)
        self.assertIn(('40-49', '40-49'), field.choices)
        self.assertIn(('50-59', '50-59'), field.choices)
        self.assertIn(('60-69', '60-69'), field.choices)
        self.assertIn(('70-79', '70-79'), field.choices)
        self.assertIn(('80-+', '80 or more'), field.choices)

    def test_age_field_should_be_optional(self):
        field = AccountProfile._meta.get_field_by_name('age')[0]
        self.assertTrue(field.null)
        self.assertTrue(field.blank)

    def test_age_should_have_a_verbose_name(self):
        field = AccountProfile._meta.get_field_by_name('age')[0]
        self.assertEqual(u"Age", field.verbose_name)

    def test_should_have_profession_field(self):
        self.assertIn('profession', self.field_names)

    def test_profession_field_should_be_char_field(self):
        field = AccountProfile._meta.get_field_by_name('profession')[0]
        self.assertEqual(django_models.CharField, field.__class__)

    def test_profession_field_should_have_expected_choices(self):
        field = AccountProfile._meta.get_field_by_name('profession')[0]
        self.assertIn(('student', 'Student'), field.choices)
        self.assertIn(('trainee', 'Trainee'), field.choices)
        self.assertIn(('developer', 'Developer'), field.choices)
        self.assertIn(('software engineer', 'Software engineer'), field.choices)
        self.assertIn(('manager', 'Manager'), field.choices)
        self.assertIn(('sysadmin', 'Sysadmin'), field.choices)
        self.assertIn(('teacher', 'Teacher'), field.choices)
        self.assertIn(('other', 'Other'), field.choices)

    def test_profession_field_should_be_optional(self):
        field = AccountProfile._meta.get_field_by_name('profession')[0]
        self.assertTrue(field.null)
        self.assertTrue(field.blank)

    def test_profession_should_have_a_verbose_name(self):
        field = AccountProfile._meta.get_field_by_name('profession')[0]
        self.assertEqual(u"Profession", field.verbose_name)

    def test_should_have_institution_field(self):
        self.assertIn('institution', self.field_names)

    def test_institution_field_should_be_char_field(self):
        field = AccountProfile._meta.get_field_by_name('institution')[0]
        self.assertEqual(django_models.CharField, field.__class__)

    def test_institution_field_should_be_optional(self):
        field = AccountProfile._meta.get_field_by_name('institution')[0]
        self.assertTrue(field.null)
        self.assertTrue(field.blank)

    def test_institution_field_should_have_verbose_name_company_university_institution(self):
        field = AccountProfile._meta.get_field_by_name('institution')[0]
        self.assertEquals('Company / University / Institution', field.verbose_name)

    def test_should_have_payement_field(self):
        self.assertIn('payement', self.field_names)

    def test_payement_field_should_be_char_field(self):
        field = AccountProfile._meta.get_field_by_name('payement')[0]
        self.assertEqual(django_models.BooleanField, field.__class__)

    def test_payement_field_should_have_default_False(self):
        field = AccountProfile._meta.get_field_by_name('payement')[0]
        self.assertFalse(field.default)

    def test_have_talk_subscription_should_be_false_when_use_hasnt_a_subscription(self):
        user = User.objects.create(username="tony")
        profile = AccountProfile.objects.create(user=user)
        self.assertFalse(profile.has_talk_subscription())

    def test_have_talk_subscription_shoud_be_true_when_user_has_a_subscription(self):
        user = User.objects.create(username="tony")
        profile = AccountProfile.objects.create(user=user)
        models.Subscription.objects.create(user=user, type="talk")
        self.assertTrue(profile.has_talk_subscription())

    def test_talk_subscription_shoud_be_returns_the_talk_subscription(self):
        user = User.objects.create(username="tony")
        profile = AccountProfile.objects.create(user=user)
        subscription = models.Subscription.objects.create(user=user, type="talk")
        self.assertEqual(subscription, profile.talk_subscription())

    def test_should_have_twitter_field(self):
        self.assertIn('twitter', self.field_names)

    def test_twitter_should_be_a_CharField(self):
        f = AccountProfile._meta.get_field_by_name('twitter')[0]
        self.assertIsInstance(f, django_models.CharField)

    def test_twitter_should_have_at_most_15_characters(self):
        f = AccountProfile._meta.get_field_by_name('twitter')[0]
        self.assertEqual(15, f.max_length)

    def test_twitter_should_accept_blank(self):
        f = AccountProfile._meta.get_field_by_name('twitter')[0]
        self.assertTrue(f.blank)

    def test_twitter_should_be_nullable(self):
        f = AccountProfile._meta.get_field_by_name('twitter')[0]
        self.assertTrue(f.null)

    def test_twitter_should_have_verbose_name(self):
        f = AccountProfile._meta.get_field_by_name('twitter')[0]
        self.assertEqual(u"Twitter profile", f.verbose_name)

    def test_should_have_field_for_public_displayable(self):
        self.assertIn('public', self.field_names)

    def test_public_should_be_a_BooleanField(self):
        f = AccountProfile._meta.get_field_by_name('public')[0]
        self.assertIsInstance(f, django_models.BooleanField)

    def test_public_should_be_true_by_default(self):
        f = AccountProfile._meta.get_field_by_name('public')[0]
        self.assertEqual(True, f.default)

    def test_public_should_have_verbose_name(self):
        f = AccountProfile._meta.get_field_by_name('public')[0]
        self.assertEqual(u"Public profile (visible to everyone)?", f.verbose_name)


class AccountProfileTransactionTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        management.call_command("loaddata", "profiles.json", verbosity=0)

    @classmethod
    def tearDownClass(cls):
        management.call_command("flush", interactive=False, verbosity=0)

    def setUp(self):
        self.user = User.objects.get(pk=1)

    def tearDown(self):
        if hasattr(self, "requests_original"):
            models.request = self.requests_original

    def _mock_requests(self, body, ok):
        self.requests_original = models.requests

        class ResponseMock(object):
            content = body

            def ok(self):
                return False

        def post(self, *args, **kwargs):
            return ResponseMock()

        models.requests.post = post

    def test_transaction_returns_a_new_transaction_if_the_profile_does_not_have_one(self):
        profile = self.user.get_profile()
        self._mock_requests("<code>xpto1234</code>", True)
        transaction = profile.transaction
        self.assertEqual(models.PRICES[profile.type], transaction.price)
        self.assertEqual("xpto1234", transaction.code)

    def test_transaction_raises_exception_if_the_user_has_a_done_subscription(self):
        subscription = models.Subscription.objects.create(
            user=self.user,
            type="talk",
            status="sponsor",
        )
        try:
            with self.assertRaises(CompleteSubscriptionException) as cm:
                self.user.get_profile().transaction
            exc = cm.exception
            self.assertEqual("This subscription is complete.", exc.args[0])
        finally:
            subscription.delete()

    def test_transaction_returns_the_already_created_transaction_if_it_matches_the_price(self):
        subscription = models.Subscription.objects.create(
            user=self.user,
            type="talk",
        )
        profile = self.user.get_profile()
        transaction = models.Transaction.objects.create(
            subscription=subscription,
            price=models.PRICES[profile.type],
            code="abcd123",
            status="pending",
        )
        try:
            got_transaction = profile.transaction
            self.assertEqual(transaction.pk, got_transaction.pk)
        finally:
            transaction.delete()
            subscription.delete()

    def test_transaction_generates_a_new_transaction_if_the_existing_transaction_does_not_match_price(self):
        self._mock_requests("<code>transaction321</code>", True)
        subscription = models.Subscription.objects.create(
            user=self.user,
            type="talk",
        )
        profile = self.user.get_profile()
        transaction = models.Transaction.objects.create(
            subscription=subscription,
            price=models.PRICES[profile.type] * 2,
            code="abcd123",
            status="pending",
        )
        try:
            got_transaction = profile.transaction
            self.assertNotEqual(transaction.pk, got_transaction.pk)
            self.assertEqual(transaction.subscription, got_transaction.subscription)
            self.assertEqual(models.PRICES[profile.type], got_transaction.price)
            self.assertEqual("transaction321", got_transaction.code)
            transaction = models.Transaction.objects.get(pk=transaction.pk)
            self.assertEqual("canceled", transaction.status)
        finally:
            transaction.delete()
            subscription.delete()

    def test_transaction_generates_a_new_transaction_if_the_existing_transaction_is_canceled(self):
        self._mock_requests("<code>transaction123</code>", True)
        subscription = models.Subscription.objects.create(
            user=self.user,
            type="talk",
        )
        profile = self.user.get_profile()
        transaction = models.Transaction.objects.create(
            subscription=subscription,
            price=models.PRICES[profile.type],
            code="abcd123",
            status="canceled",
        )
        try:
            got_transaction = profile.transaction
            self.assertNotEqual(transaction.pk, got_transaction.pk)
            self.assertEqual(transaction.subscription, got_transaction.subscription)
            self.assertEqual(models.PRICES[profile.type], got_transaction.price)
            self.assertEqual("transaction123", got_transaction.code)
        finally:
            transaction.delete()
            subscription.delete()

########NEW FILE########
__FILENAME__ = test_views
# -*- coding: utf-8 -*-
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.test.client import RequestFactory, Client
from django.views.generic import TemplateView
from django.views.generic.list import ListView

from pythonbrasil8.core.views import LoginRequiredMixin
from pythonbrasil8.dashboard.forms import ProfileForm, SpeakerProfileForm
from pythonbrasil8.dashboard.models import AccountProfile
from pythonbrasil8.dashboard.views import IndexView, ProfileView, SessionsView
from pythonbrasil8.schedule.models import Session, Track


class DashboardIndexTestCase(TestCase):

    def setUp(self):
        self.request = RequestFactory().get("/")
        self.request.user = User.objects.create_user(username="user", password='test')
        self.track = Track.objects.create(
            name=u"Beginners",
            description=u"Python for noobies",
        )
        self.session = Session.objects.create(
            title="Python for dummies",
            description="about python, universe and everything",
            type="talk",
            track=self.track,
        )
        self.session.speakers.add(self.request.user)

    def tearDown(self):
        self.session.delete()
        self.track.delete()

    def test_should_be_a_template_view(self):
        self.assertTrue(issubclass(IndexView, TemplateView))

    def test_shoud_use_a_dashboard_template(self):
        self.assertEqual('dashboard/index.html', IndexView.template_name)

    def test_should_redirects_if_user_is_not_logged_in(self):
        self.request.user.is_authenticated = lambda: False
        result = IndexView.as_view()(self.request)
        self.assertEqual(302, result.status_code)

    def test_should_have_200_status_code_when_user_is_logged_in(self):
        result = IndexView.as_view()(self.request)
        self.assertEqual(200, result.status_code)

    def test_should_have_sessions_on_context(self):
        result = IndexView.as_view()(self.request)
        self.assertIn('sessions', result.context_data)
        self.assertQuerysetEqual(result.context_data['sessions'], [u"Python for dummies", ], lambda s: s.title)

    def test_get_url_should_return_200(self):
        client = Client()
        client.login(username=self.request.user.username, password='test')
        response = client.get('/dashboard/')
        self.assertEqual(200, response.status_code)


class ProfileViewTestCase(TestCase):

    @classmethod
    def setUpClass(self):
        self.user = User.objects.create_user(username="user", password="test")
        self.account_profile = AccountProfile.objects.create(user=self.user)

    def setUp(self):
        self.request = RequestFactory().get("/")
        self.request.user = User.objects.get(id=self.user.id)
        self.response = ProfileView.as_view()(self.request, pk=self.account_profile.id)

    @classmethod
    def tearDownClass(self):
        self.account_profile.delete()

    def test_should_use_expected_template(self):
        self.assertTemplateUsed(self.response, 'dashboard/profile.html')

    def test_model_should_be_AccountProfile(self):
        self.assertEqual(AccountProfile, ProfileView.model)

    def test_form_should_be_ProfileForm_when_type_is_not_speaker(self):
        v = ProfileView()
        v.object = AccountProfile(type="Student")
        self.assertEqual(ProfileForm, v.get_form_class())

    def test_form_should_be_SpeakerProfileForm_when_type_is_speaker(self):
        v = ProfileView()
        v.object = AccountProfile(type="Speaker")
        self.assertEqual(SpeakerProfileForm, v.get_form_class())

    def test_should_redirects_if_user_is_not_logged_in(self):
        self.request.user.is_authenticated = lambda: False
        result = ProfileView.as_view()(self.request, pk=self.account_profile.id)
        self.assertEqual(302, result.status_code)

    def test_success_url_should_be_dashboard_index(self):
        self.assertEqual("/dashboard/", ProfileView.success_url)

    def test_should_have_200_status_code_when_user_is_logged_in(self):
        self.assertEqual(200, self.response.status_code)

    def test_update_account_user_with_success(self):
        data = {
            'user': self.user.id,
            'name': 'siminino',
            'description': 'simi test',
            'type': 'Student',
            'tshirt': 'M',
            'gender': 'male',
            'locale': 'AC',
        }

        request = RequestFactory().post('/', data)
        request.user = self.request.user
        response = ProfileView().dispatch(request)
        self.assertEqual(302, response.status_code)

        profile = AccountProfile.objects.get(id=self.account_profile.id)
        self.assertEqual('siminino', profile.name)
        self.assertEqual('simi test', profile.description)
        self.assertEqual('Student', profile.type)
        self.assertEqual('M', profile.tshirt)

    def test_get_url_should_return_200(self):
        client = Client()
        client.login(username=self.request.user.username, password='test')
        response = client.get('/dashboard/profile/')
        self.assertEqual(200, response.status_code)


class SessionsTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        call_command("loaddata", "sessions.json", verbosity=0)
        cls.factory = RequestFactory()

    @classmethod
    def tearDownClass(cls):
        call_command("flush", interactive=False, verbosity=0)

    def test_should_inherit_from_ListView(self):
        assert issubclass(SessionsView, ListView)

    def test_should_inherit_from_LoginRequiredMixin(self):
        assert issubclass(SessionsView, LoginRequiredMixin)

    def test_template_name_should_be_dashboard_slash_sessions(self):
        self.assertEqual(u"dashboard/sessions.html", SessionsView.template_name)

    def test_should_use_sessions_as_context_object_name(self):
        self.assertEqual(u"sessions", SessionsView.context_object_name)

    def test_queryset_should_return_sessions_of_the_request_user(self):
        expected = Session.objects.all()
        request = self.factory.get("/dashboard/sessions")
        request.user = User.objects.get(username="chico")
        v = SessionsView()
        v.request = request
        sessions = v.get_queryset()
        self.assertEqual([x.id for x in expected],
                         [x.id for x in sessions])

########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-
from django.conf.urls import patterns, url

from pythonbrasil8.dashboard.views import IndexView, ProfileView, SessionsView
from pythonbrasil8.subscription.views import SubscriptionView, TutorialSubscriptionView
from pythonbrasil8.schedule.views import DeleteSessionView, EditSessionView, FinishedProposalsView


urlpatterns = patterns('',
    url(r'^$', IndexView.as_view(), name='dashboard-index'),
    url(r'^subscription/talk/$', SubscriptionView.as_view(), name='talk-subscription'),
    url(r'^subscription/tutorials/$', TutorialSubscriptionView.as_view(), name='tutorials-subscription'),
    url(r'^profile/$', ProfileView.as_view(), name='edit-profile'),
    url(r'^proposals/$', SessionsView.as_view(), name='dashboard-sessions'),
    url(r'^proposals/propose/$', FinishedProposalsView.as_view(), name='session-subscribe'),
    url(r'^proposals/edit/(?P<id>\d+)', EditSessionView.as_view(), name='session-edit'),
    url(r'^proposals/delete/(?P<id>\d+)', DeleteSessionView.as_view(), name='session-delete'),
)

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
from django.contrib import messages
from django.utils.translation import ugettext
from django.views.generic import ListView, TemplateView, UpdateView

from pythonbrasil8.core.views import LoginRequiredMixin
from pythonbrasil8.dashboard.forms import ProfileForm, SpeakerProfileForm
from pythonbrasil8.dashboard.models import AccountProfile
from pythonbrasil8.schedule.models import Session


class DashBoardView(LoginRequiredMixin, TemplateView):
    pass


class ProfileView(LoginRequiredMixin, UpdateView):
    template_name = 'dashboard/profile.html'
    model = AccountProfile
    success_url = "/dashboard/"

    def get(self, *args, **kwargs):
        self.kwargs['pk'] = self.request.user.get_profile().id
        return super(ProfileView, self).get(*args, **kwargs)

    def post(self, *args, **kwargs):
        self.kwargs['pk'] = self.request.user.get_profile().id
        r = super(ProfileView, self).post(*args, **kwargs)
        if 300 < r.status_code < 400:
            messages.success(self.request, ugettext(u"Profile successfully updated."), fail_silently=True)
        return r

    def get_form_class(self):
        if self.object.type == "Speaker":
            return SpeakerProfileForm
        return ProfileForm


class IndexView(DashBoardView):
    template_name = 'dashboard/index.html'

    def get_context_data(self, *args, **kwargs):
        context = super(IndexView, self).get_context_data(*args, **kwargs)
        context['sessions'] = Session.objects.filter(speakers=self.request.user)
        return context


class SessionsView(LoginRequiredMixin, ListView):
    context_object_name = u"sessions"
    template_name = u"dashboard/sessions.html"

    def get_queryset(self):
        return Session.objects.filter(speakers=self.request.user)

########NEW FILE########
__FILENAME__ = admin
# -*- coding: utf-8 -*-
from django.contrib import admin
from pythonbrasil8.news.models import Post

admin.site.register(Post)

########NEW FILE########
__FILENAME__ = feed
# -*- coding: utf-8 -*-
from datetime import date

from django.core.urlresolvers import reverse
from django.contrib.markup.templatetags.markup import markdown
from django.contrib.syndication.views import Feed

from pythonbrasil8.news.models import Post


class NewsFeed(Feed):
    title = 'PythonBrasil[8] News'
    description = 'News from PythonBrasil[8]'
    link = '/news/feed/'

    def items(self):
        qs = Post.objects.filter(published_at__lte=date.today())
        return qs.order_by('-published_at')

    def item_description(self, item):
        return markdown(item.content)

    def item_title(self, item):
        return item.title

    def item_link(self, item):
        return reverse('news:post', kwargs={'post_slug': item.slug})

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Post'
        db.create_table('news_post', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title_en_us', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('title_pt_br', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('published_at', self.gf('django.db.models.fields.DateField')()),
            ('content_en_us', self.gf('django.db.models.fields.TextField')()),
            ('content_pt_br', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('slug', self.gf('django.db.models.fields.SlugField')(db_index=True, max_length=255, null=True, blank=True)),
            ('author', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
        ))
        db.send_create_signal('news', ['Post'])


    def backwards(self, orm):
        
        # Deleting model 'Post'
        db.delete_table('news_post')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 11, 3, 0, 40, 55, 405415)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 11, 3, 0, 40, 55, 405195)'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'news.post': {
            'Meta': {'object_name': 'Post'},
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'content_en_us': ('django.db.models.fields.TextField', [], {}),
            'content_pt_br': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'published_at': ('django.db.models.fields.DateField', [], {}),
            'slug': ('django.db.models.fields.SlugField', [], {'db_index': 'True', 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'title_en_us': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'title_pt_br': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['news']

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
from transmeta import TransMeta

from django.db import models
from django.contrib.auth.models import User
from django.template.defaultfilters import slugify
from django.utils.translation import ugettext_lazy as _

class Post(models.Model):
    __metaclass__ = TransMeta

    title = models.CharField(max_length=255, verbose_name=_(u'Title'))
    published_at = models.DateField(verbose_name=_(u'Published at'))
    content = models.TextField(verbose_name=_(u'Content'), help_text=_('Use markdown language'))
    slug = models.SlugField(max_length=255, verbose_name=_(u'Slug'), blank=True, null=True)
    author = models.ForeignKey(User, verbose_name=_(u'Author'))

    class Meta:
        translate = ('title', 'content')

    def __unicode__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.slug = slugify(self.title)
        super(Post, self).save(*args, **kwargs)

########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-
from django.conf.urls import patterns, url
from django.views.generic import TemplateView

from pythonbrasil8.news.feed import NewsFeed

urlpatterns = patterns('pythonbrasil8.news.views',
    url(r'^$', 'news_view', name='main'),
    url(r'^feed/$', NewsFeed(), name='feed'),
    url(r'^(?P<post_slug>[\w\d-]+)/$', 'post_view', name='post'),
)

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
from datetime import date
from django.shortcuts import get_object_or_404
from django.views.generic import ListView
from django.views.generic.simple import direct_to_template

from pythonbrasil8.news.models import Post

class NewsView(ListView):
    template_name = 'news.html'
    context_object_name = 'posts'

    def get_queryset(self, *args, **kwargs):
        return Post.objects.filter(published_at__lte=date.today()).order_by('-published_at')

news_view = NewsView.as_view()

def post_view(request, post_slug):
    post = get_object_or_404(Post, slug=post_slug)
    return direct_to_template(request, 'post.html', {'post': post})

########NEW FILE########
__FILENAME__ = admin
# -*- coding: utf-8 -*-
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from pythonbrasil8.schedule.models import Session, Track, ProposalVote


def coalesce(*args):
    for arg in args:
        if arg:
            return arg


class SessionAdmin(admin.ModelAdmin):
    list_display = ("title", "type", "speaker_names", "track", "status",)
    list_filter = ("type", "status",)

    def speaker_names(self, obj):
        speakers = [coalesce(s.accountprofile.name, s.username) for s in obj.speakers.all().order_by("username")]
        return ", ".join(speakers)

    speaker_names.short_description = _("Speakers")

admin.site.register(Session, SessionAdmin)

class TrackAdmin(admin.ModelAdmin):
    list_display = ("name",)

class ProposalVoteAdmin(admin.ModelAdmin):
    list_display = ("user", "session", "vote")

admin.site.register(Track, TrackAdmin)
admin.site.register(ProposalVote, ProposalVoteAdmin)

########NEW FILE########
__FILENAME__ = forms
from django.forms import ModelForm

from pythonbrasil8.schedule.models import Session


class SessionForm(ModelForm):
    class Meta:
        model = Session
        exclude = ("speakers", "status",)

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        db.create_table('schedule_session', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('description', self.gf('django.db.models.fields.TextField')()),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('tags', self.gf('django.db.models.fields.CharField')(max_length=255)),
        ))
        db.send_create_signal('schedule', ['Session'])

        db.create_table('schedule_session_speakers', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('session', models.ForeignKey(orm['schedule.session'], null=False)),
            ('user', models.ForeignKey(orm['auth.user'], null=False))
        ))
        db.create_unique('schedule_session_speakers', ['session_id', 'user_id'])

    def backwards(self, orm):
        db.delete_table('schedule_session')

        db.delete_table('schedule_session_speakers')

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 6, 17, 15, 17, 9, 870097)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 6, 17, 15, 17, 9, 869986)'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'schedule.session': {
            'Meta': {'object_name': 'Session'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'speakers': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False'}),
            'tags': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        }
    }

    complete_apps = ['schedule']

########NEW FILE########
__FILENAME__ = 0002_auto__add_track
# encoding: utf-8
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):
        db.create_table('schedule_track', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name_en_us', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('name_pt_br', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('description_en_us', self.gf('django.db.models.fields.CharField')(max_length=2000)),
            ('description_pt_br', self.gf('django.db.models.fields.CharField')(max_length=2000, null=True, blank=True)),
        ))
        db.send_create_signal('schedule', ['Track'])

    def backwards(self, orm):
        db.delete_table('schedule_track')

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 6, 17, 15, 17, 37, 807687)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 6, 17, 15, 17, 37, 807578)'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'schedule.session': {
            'Meta': {'object_name': 'Session'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'speakers': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False'}),
            'tags': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        },
        'schedule.track': {
            'Meta': {'object_name': 'Track'},
            'description_en_us': ('django.db.models.fields.CharField', [], {'max_length': '2000'}),
            'description_pt_br': ('django.db.models.fields.CharField', [], {'max_length': '2000', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name_en_us': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'name_pt_br': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['schedule']

########NEW FILE########
__FILENAME__ = 0003_auto__add_field_session_track
# encoding: utf-8
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):
        db.add_column('schedule_session', 'track', self.gf('django.db.models.fields.related.ForeignKey')(default=0, to=orm['schedule.Track']), keep_default=False)

    def backwards(self, orm):
        db.delete_column('schedule_session', 'track_id')

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 6, 17, 15, 35, 9, 582018)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 6, 17, 15, 35, 9, 581705)'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'schedule.session': {
            'Meta': {'object_name': 'Session'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'speakers': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False'}),
            'tags': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'track': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['schedule.Track']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        },
        'schedule.track': {
            'Meta': {'object_name': 'Track'},
            'description_en_us': ('django.db.models.fields.CharField', [], {'max_length': '2000'}),
            'description_pt_br': ('django.db.models.fields.CharField', [], {'max_length': '2000', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name_en_us': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'name_pt_br': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['schedule']

########NEW FILE########
__FILENAME__ = 0004_auto__add_field_session_language
# encoding: utf-8
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):
        db.add_column('schedule_session', 'language', self.gf('django.db.models.fields.CharField')(default='pt', max_length=2), keep_default=False)

    def backwards(self, orm):
        db.delete_column('schedule_session', 'language')

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 6, 23, 15, 47, 18, 228320)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 6, 23, 15, 47, 18, 228214)'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'schedule.session': {
            'Meta': {'object_name': 'Session'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'speakers': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False'}),
            'tags': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'track': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['schedule.Track']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        },
        'schedule.track': {
            'Meta': {'object_name': 'Track'},
            'description_en_us': ('django.db.models.fields.CharField', [], {'max_length': '2000'}),
            'description_pt_br': ('django.db.models.fields.CharField', [], {'max_length': '2000', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name_en_us': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'name_pt_br': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['schedule']

########NEW FILE########
__FILENAME__ = 0005_auto__del_field_session_tags
# encoding: utf-8
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):
        db.delete_column('schedule_session', 'tags')

    def backwards(self, orm):
        raise RuntimeError("Cannot reverse this migration. 'Session.tags' and its values cannot be restored.")

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 6, 24, 12, 36, 15, 309633)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 6, 24, 12, 36, 15, 309467)'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'schedule.session': {
            'Meta': {'object_name': 'Session'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'speakers': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'track': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['schedule.Track']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        },
        'schedule.track': {
            'Meta': {'object_name': 'Track'},
            'description_en_us': ('django.db.models.fields.CharField', [], {'max_length': '2000'}),
            'description_pt_br': ('django.db.models.fields.CharField', [], {'max_length': '2000', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name_en_us': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'name_pt_br': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['schedule']

########NEW FILE########
__FILENAME__ = 0006_auto__add_field_session_status
# encoding: utf-8
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):
        db.add_column('schedule_session', 'status', self.gf('django.db.models.fields.CharField')(default='proposed', max_length=10), keep_default=False)

    def backwards(self, orm):
        db.delete_column('schedule_session', 'status')

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 6, 24, 16, 51, 0, 66552)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 6, 24, 16, 51, 0, 66446)'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'schedule.session': {
            'Meta': {'object_name': 'Session'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'speakers': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'proposed'", 'max_length': '10'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'track': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['schedule.Track']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        },
        'schedule.track': {
            'Meta': {'object_name': 'Track'},
            'description_en_us': ('django.db.models.fields.CharField', [], {'max_length': '2000'}),
            'description_pt_br': ('django.db.models.fields.CharField', [], {'max_length': '2000', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name_en_us': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'name_pt_br': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['schedule']

########NEW FILE########
__FILENAME__ = 0007_auto__add_field_session_audience_level
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Session.audience_level'
        db.add_column('schedule_session', 'audience_level', self.gf('django.db.models.fields.CharField')(default='intermediate', max_length=12), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Session.audience_level'
        db.delete_column('schedule_session', 'audience_level')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 6, 24, 21, 51, 44, 549744)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 6, 24, 21, 51, 44, 549558)'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'schedule.session': {
            'Meta': {'object_name': 'Session'},
            'audience_level': ('django.db.models.fields.CharField', [], {'default': "'intermediate'", 'max_length': '12'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'speakers': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'proposed'", 'max_length': '10'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'track': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['schedule.Track']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        },
        'schedule.track': {
            'Meta': {'object_name': 'Track'},
            'description_en_us': ('django.db.models.fields.CharField', [], {'max_length': '2000'}),
            'description_pt_br': ('django.db.models.fields.CharField', [], {'max_length': '2000', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name_en_us': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'name_pt_br': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['schedule']

########NEW FILE########
__FILENAME__ = 0008_add_tracks
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models


class Migration(DataMigration):

    def forwards(self, orm):
        tracks = [
            ('Core & Interpreters', 'Core & Interpretadores',
             'The language, CPython, PyPy, Jython, IronPython, bindings, standard library, optimizations',
             'A linguagem, CPython, PyPy, Jython, IronPython, bindings, bibliotaca padrão, otimizações'),
            ('Games & Multimedia', 'Jogos & Multimídia',
             'Games, multimedia, image and video processing, interactivity, digital TV',
             'Jogos, multimídia, processamento de imagens e vídeo, interatividade, TV digital'),
            ('Embedded Systems & Mobile', 'Sistemas embarcados e móveis',
             'Microncontrollers, wireless sensor networks, mobile applications',
             'Microcontroladores, redes de sensores sem fio, aplicativos para celular'),
            ('GUI Programming', 'GUI',
             'GUI libraries, human-machine interface',
             'Bibliotecas GUI, interface homem-máquina '),
            ('Business', 'Negócios',
             'Entrepreneurship, innovation, success cases',
             'Empreendedorismo, inovação, casos de sucesso'),
            ('Databases', 'Banco de dados',
             'Databases, information retrieval, information systems',
             'Bancos de dados, recuperação de informação, sistemas de informação'),
            ('Science', 'Python na ciência',
             'Scientific computing, natural language processing, artificial intelligence, computer simulation',
             'Computação científica, processamento de linguagem natural, inteligência artificial, simulação computacional'),
            ('Python in society', 'Python na sociedade',
             'Communities, education, open data, government, art',
             'Comunidades, educação, dados abertos, governo, artes'),
            ('Web Frameworks', 'Frameworks Web',
             'Frameworks for Web development, libraries, applications',
             'Frameworks para desenvolvimento Web, bibliotecas, aplicações'),
            ('Cloud computing', 'Computação na nuvem',
             'Cloud computing, virtual machines, elasticity, infrastructure',
             'Computação na nuvem, máquinas virtuais, elasticidade, infraestrutura'),
            ('SysAdmin & DevOp', 'SysAdmin & DevOp',
             'Systems administration, infrastructure management',
             'Administração de sistemas, gerenciamento de infraestrutura'),
            ('Networks', 'Redes de computadores',
             'Distributed systems, network protocols, security',
             'Sistemas distribuídos, protocolos de rede, segurança'),
            ('Django', 'Django',
             'The framework, applications, libraries',
             'O framework, aplicações, bibliotecas'),
            ('Plone', 'Plone',
             'The framework, applications, libraries',
             'O framework, aplicações, bibliotecas'),
            ('Tools & methodology', 'Ferramentas e metodologias',
             'Good practices, design patterns, tests, documentation, packaging',
             'Boas práticas, design patterns, testes, documentação, empacotamento'),
            ('Other', 'Outra',
             'Does not fit in other options',
             'Não se encaixa nas demais opções'),
        ]
        for info in tracks:
            track = orm.Track(name_en_us=info[0], name_pt_br=info[1],
                              description_en_us=info[2],
                              description_pt_br=info[3])
            track.save()

    def backwards(self, orm):
        raise RuntimeError("Cannot reverse this migration.")

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 8, 22, 21, 50, 51, 913320)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 8, 22, 21, 50, 51, 913235)'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'schedule.session': {
            'Meta': {'object_name': 'Session'},
            'audience_level': ('django.db.models.fields.CharField', [], {'max_length': '12'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'speakers': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'proposed'", 'max_length': '10'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'track': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['schedule.Track']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        },
        'schedule.track': {
            'Meta': {'object_name': 'Track'},
            'description_en_us': ('django.db.models.fields.CharField', [], {'max_length': '2000'}),
            'description_pt_br': ('django.db.models.fields.CharField', [], {'max_length': '2000', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name_en_us': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'name_pt_br': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['schedule']

########NEW FILE########
__FILENAME__ = 0009_auto__add_field_session_slug__add_field_track_slug
# coding: utf-8

import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Adding field 'Session.slug'
        db.add_column('schedule_session', 'slug',
                self.gf('django.db.models.fields.SlugField')(default=None,
                    max_length=255, null=True, blank=True, db_index=True),
                keep_default=False)

        # Adding field 'Track.slug'
        db.add_column('schedule_track', 'slug',
                self.gf('django.db.models.fields.SlugField')(default=None,
                    max_length=255, null=True, blank=True, db_index=True),
                keep_default=False)


    def backwards(self, orm):

        # Deleting field 'Session.slug'
        db.delete_column('schedule_session', 'slug')

        # Deleting field 'Track.slug'
        db.delete_column('schedule_track', 'slug')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 10, 4, 8, 23, 17, 569737)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 10, 4, 8, 23, 17, 569648)'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'schedule.session': {
            'Meta': {'object_name': 'Session'},
            'audience_level': ('django.db.models.fields.CharField', [], {'max_length': '12'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'slug': ('django.db.models.fields.SlugField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'db_index': 'True'}),
            'speakers': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'proposed'", 'max_length': '10'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'track': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['schedule.Track']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        },
        'schedule.track': {
            'Meta': {'object_name': 'Track'},
            'description_en_us': ('django.db.models.fields.CharField', [], {'max_length': '2000'}),
            'description_pt_br': ('django.db.models.fields.CharField', [], {'max_length': '2000', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name_en_us': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'name_pt_br': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'db_index': 'True'})
        }
    }

    complete_apps = ['schedule']

########NEW FILE########
__FILENAME__ = 0010_slug
# -*- coding: utf-8 -*-
from django.template.defaultfilters import slugify
from south.v2 import DataMigration

class Migration(DataMigration):

    def forwards(self, orm):
        for track in orm.Track.objects.all():
            track.slug = slugify(track.name_en_us)
            track.save() # method save will automatically put slug
        for session in orm.Session.objects.all():
            session.slug = slugify(session.title)
            session.save() # method save will automatically put slug

    def backwards(self, orm):
        pass

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 10, 4, 8, 30, 40, 603325)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 10, 4, 8, 30, 40, 603240)'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'schedule.session': {
            'Meta': {'object_name': 'Session'},
            'audience_level': ('django.db.models.fields.CharField', [], {'max_length': '12'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'slug': ('django.db.models.fields.SlugField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'db_index': 'True', 'blank': 'True'}),
            'speakers': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'proposed'", 'max_length': '10'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'track': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['schedule.Track']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        },
        'schedule.track': {
            'Meta': {'object_name': 'Track'},
            'description_en_us': ('django.db.models.fields.CharField', [], {'max_length': '2000'}),
            'description_pt_br': ('django.db.models.fields.CharField', [], {'max_length': '2000', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name_en_us': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'name_pt_br': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'db_index': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['schedule']

########NEW FILE########
__FILENAME__ = 0011_auto__add_proposalvote
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'ProposalVote'
        db.create_table('schedule_proposalvote', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('session', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['schedule.Session'])),
            ('vote', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal('schedule', ['ProposalVote'])


    def backwards(self, orm):
        
        # Deleting model 'ProposalVote'
        db.delete_table('schedule_proposalvote')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 10, 12, 2, 31, 36, 762761)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 10, 12, 2, 31, 36, 762584)'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'schedule.proposalvote': {
            'Meta': {'object_name': 'ProposalVote'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'session': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['schedule.Session']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'vote': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'schedule.session': {
            'Meta': {'object_name': 'Session'},
            'audience_level': ('django.db.models.fields.CharField', [], {'max_length': '12'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'slug': ('django.db.models.fields.SlugField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'db_index': 'True', 'blank': 'True'}),
            'speakers': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'proposed'", 'max_length': '10'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'track': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['schedule.Track']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        },
        'schedule.track': {
            'Meta': {'object_name': 'Track'},
            'description_en_us': ('django.db.models.fields.CharField', [], {'max_length': '2000'}),
            'description_pt_br': ('django.db.models.fields.CharField', [], {'max_length': '2000', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name_en_us': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'name_pt_br': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'db_index': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['schedule']

########NEW FILE########
__FILENAME__ = 0012_auto__add_field_session_date
# encoding: utf-8
from south.db import db
from south.v2 import SchemaMigration

class Migration(SchemaMigration):

    def forwards(self, orm):
        db.add_column('schedule_session', 'date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True), keep_default=False)

    def backwards(self, orm):
        db.delete_column('schedule_session', 'date')

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 11, 13, 23, 45, 59, 987407)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 11, 13, 23, 45, 59, 987306)'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'schedule.proposalvote': {
            'Meta': {'object_name': 'ProposalVote'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'session': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['schedule.Session']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'vote': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'schedule.session': {
            'Meta': {'object_name': 'Session'},
            'audience_level': ('django.db.models.fields.CharField', [], {'max_length': '12'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'slug': ('django.db.models.fields.SlugField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'db_index': 'True', 'blank': 'True'}),
            'speakers': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'proposed'", 'max_length': '10'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'track': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['schedule.Track']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        },
        'schedule.track': {
            'Meta': {'object_name': 'Track'},
            'description_en_us': ('django.db.models.fields.CharField', [], {'max_length': '2000'}),
            'description_pt_br': ('django.db.models.fields.CharField', [], {'max_length': '2000', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name_en_us': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'name_pt_br': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'db_index': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['schedule']

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-

import transmeta
from django.contrib.auth import models as auth_models
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.template.defaultfilters import slugify


SESSION_TYPES = (
    ("talk", _("Talk")),
    ("tutorial", _("Tutorial"),),
    ("keynote", "Keynote"),
)

LANGUAGE_CHOICES = (
    ("pt", _("Portuguese")),
    ("en", _("English")),
    ("es", _("Spanish")),
)

SESSION_STATUSES = (
    (u"proposed", u"Proposed"),
    (u"accepted", u"Accepted"),
    (u"confirmed", u"Confirmed"),
    (u"canceled", u"Canceled"),
)

SESSION_LEVELS = (
    (u"beginner", _(u"Beginner")),
    (u"intermediate", _(u"Intermediate")),
    (u"advanced", _(u"Advanced")),
)


class Track(models.Model):
    __metaclass__ = transmeta.TransMeta

    name = models.CharField(max_length=255, verbose_name=_("Name"))
    slug = models.SlugField(max_length=255, default=None, null=True,
            blank=True)
    description = models.CharField(max_length=2000,
            verbose_name=_("Description"))

    class Meta:
        translate = ("name", "description")

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super(Track, self).save(*args, **kwargs)


class Session(models.Model):
    type = models.CharField(max_length=20, choices=SESSION_TYPES,
            verbose_name=_("Type"))
    track = models.ForeignKey(Track, verbose_name=_("Track"))
    audience_level = models.CharField(max_length=12, choices=SESSION_LEVELS,
            verbose_name=_("Audience level"))
    language = models.CharField(max_length=2, verbose_name=_("Language"),
            choices=LANGUAGE_CHOICES)
    title = models.CharField(max_length=255, verbose_name=_("Title"))
    slug = models.SlugField(max_length=255, default=None, null=True,
            blank=True)
    description = models.TextField(verbose_name=_("Description"))
    speakers = models.ManyToManyField(auth_models.User,
            verbose_name=_("Speakers"))
    status = models.CharField(max_length=10, choices=SESSION_STATUSES,
            default="proposed")
    date = models.DateTimeField(blank=True, null=True)

    def __unicode__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.slug = slugify(self.title)
        super(Session, self).save(*args, **kwargs)


class ProposalVote(models.Model):
    user = models.ForeignKey(auth_models.User)
    session = models.ForeignKey(Session)
    vote = models.IntegerField(default=0)

########NEW FILE########
__FILENAME__ = test_delete_session_view
# -*- coding: utf-8 -*-

from django import http
from django.contrib.auth import models as auth_models
from django.core import management
from django.test import TestCase
from pythonbrasil8.schedule import models, views


class DeleteSessionViewTestCase(TestCase):
    fixtures = ['sessions.json']

    def test_get_deletes_the_proposal(self):
        request = self.client.get("/dashboard/proposals/delete/1/")
        request.user = models.Session.objects.get(pk=1).speakers.get(username="chico")
        resp = views.DeleteSessionView().get(request, 1)
        self.assertIsInstance(resp, http.HttpResponseRedirect)
        self.assertEqual("/dashboard/proposals/", resp["Location"])
        with self.assertRaises(models.Session.DoesNotExist):
            models.Session.objects.get(pk=1)

    def test_get_return_404_if_the_user_is_not_speaker_in_the_talk(self):
        user, _ = auth_models.User.objects.get_or_create(username="aidimim")
        request = self.client.get("/dashboard/proposals/1/")
        request.user = user
        with self.assertRaises(http.Http404):
            views.DeleteSessionView().get(request, 1)

########NEW FILE########
__FILENAME__ = test_edit_session_view
# -*- coding: utf-8 -*-

from unittest import skip
from django import http
from django.contrib.auth import models as auth_models
from django.template import response
from django.test import client, TestCase

from pythonbrasil8.schedule import forms, models, views


class EditSessionTestCase(TestCase):
    fixtures = ['sessions.json']

    def test_should_use_SessionForm_as_form_class(self):
        self.assertEqual(forms.SessionForm, views.EditSessionView.form_class)

    def test_template_name_should_be_edit_session_html(self):
        self.assertEqual("schedule/edit-session.html",
                         views.EditSessionView.template_name)

    def test_get_render_the_template_with_the_session_in_context(self):
        instance = models.Session.objects.get(pk=1)
        request = self.client.get("/dashboard/proposals/1/")
        request.user = instance.speakers.get(username="chico")
        resp = views.EditSessionView().get(request, 1)
        self.assertIsInstance(resp, response.TemplateResponse)
        self.assertEqual(views.EditSessionView.template_name,
                         resp.template_name)
        self.assertIsInstance(resp.context_data["session"], models.Session)
        self.assertEqual(1, resp.context_data["session"].pk)

    def test_get_render_the_form_with_data_populated(self):
        instance = models.Session.objects.get(pk=1)
        request = self.client.get("/dashboard/proposals/1/")
        request.user = instance.speakers.get(username="chico")
        resp = views.EditSessionView().get(request, 1)
        form = resp.context_data["form"]
        self.assertIsInstance(form, views.EditSessionView.form_class)
        self.assertEqual(instance, form.instance)

    def test_get_return_404_if_the_user_is_not_speaker_in_the_talk(self):
        user, _ = auth_models.User.objects.get_or_create(username="aidimim")
        request = self.client.get("/dashboard/proposals/1/")
        request.user = user
        with self.assertRaises(http.Http404):
            views.EditSessionView().get(request, 1)

    def test_get_include_list_of_tracks_in_the_context(self):
        track = models.Track.objects.get(pk=1)
        request = self.client.get("/dashboard/proposals/1/")
        request.user = models.Session.objects.get(pk=1).speakers.get(username="chico")
        resp = views.EditSessionView().get(request, 1)
        self.assertEqual(track, list(resp.context_data["tracks"])[0])

    @skip('Proposals are closed')
    def test_post_updates_the_session(self):
        instance = models.Session.objects.get(pk=1)
        data = {
            "title": instance.title + " updated",
            "description": instance.description,
            "type": "talk",
            "audience_level": "intermediate",
            "tags": "some, tags",
            "track": instance.track.pk,
            "language": "en",
        }
        request = self.client.post("/dashboard/proposals/1/", data)
        request.user = instance.speakers.get(username="chico")
        resp = views.EditSessionView().post(request, 1)
        self.assertIsInstance(resp, http.HttpResponseRedirect)
        self.assertEqual("/dashboard/proposals/", resp["Location"])
        instance = models.Session.objects.get(pk=1)
        self.assertEqual(data["title"], instance.title)

    @skip('Proposals are closed')
    def test_post_renders_template_name_with_form_and_tracks_in_context(self):
        instance = models.Session.objects.get(pk=1)
        data = {
            "type": "talk",
            "audience_level": "advanced",
            "tags": "some, tags",
            "track": instance.track.pk,
            "language": "en",
        }
        request = self.client.post("/dashboard/proposals/1/", data)
        request.user = instance.speakers.get(username="chico")
        resp = views.EditSessionView().post(request, 1)
        self.assertIsInstance(resp, response.TemplateResponse)
        self.assertEqual(views.EditSessionView.template_name,
                         resp.template_name)
        self.assertEqual(instance.track, list(resp.context_data["tracks"])[0])
        form = resp.context_data["form"]
        self.assertIsInstance(form, views.EditSessionView.form_class)
        self.assertEqual(data["audience_level"], form.data["audience_level"])

    def test_get_render_the_template_with_extra_speakers_in_context(self):
        instance = models.Session.objects.get(pk=1)
        request = client.RequestFactory().get("/dashboard/proposals/2/")
        request.user = instance.speakers.get(username="chico")
        result = views.EditSessionView().get(request, 2)
        self.assertIn('extra_speakers', result.context_data)
        self.assertEqual(result.context_data["extra_speakers"][0].pk, 2)

########NEW FILE########
__FILENAME__ = test_finished_view
# -*- coding: utf-8 -*-
import unittest

from django.template import response
from django.test import client

from pythonbrasil8.schedule import views


class FinishedViewTestCase(unittest.TestCase):

    def test_template_name(self):
        self.assertEqual("schedule/finished_proposals.html",
                         views.FinishedProposalsView.template_name)

    def test_get(self):
        request = client.RequestFactory().get("/")
        resp = views.FinishedProposalsView().get(request)
        self.assertIsInstance(resp, response.TemplateResponse)
        self.assertEqual(views.FinishedProposalsView.template_name,
                         resp.template_name)

########NEW FILE########
__FILENAME__ = test_proposal_page
# coding: utf-8

from django.core import management
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.contrib.auth.models import User
from pythonbrasil8.schedule.models import Track, Session
from pythonbrasil8.dashboard.models import AccountProfile


class ProposalPageTestCase(TestCase):
    fixtures = ['sessions.json']

    def test_valid_track_but_inexistent_proposal_should_return_404(self):
        url = reverse('proposal-page', kwargs={'track_slug': 'newbiews',
                'proposal_slug': 'do-not-exist'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_correct_proposal_page_should_return_200(self):
        url = reverse('proposal-page', kwargs={'track_slug': 'newbies',
                'proposal_slug': 'how-to-learn-python'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_proposal_page_should_have_proposal_information(self):
        url = reverse('proposal-page', kwargs={'track_slug': 'newbies',
                'proposal_slug': 'how-to-learn-python'})
        response = self.client.get(url)
        self.assertEqual(response.context['proposal'],
                          Session.objects.get(pk=1))

    def test_proposal_page_should_have_status_of_proposal(self):
        url = reverse('proposal-page', kwargs={'track_slug': 'newbies',
                'proposal_slug': 'how-to-learn-python'})
        response = self.client.get(url)
        self.assertIn(u'Accepted', response.content.decode('utf-8'))

        url = reverse('proposal-page', kwargs={'track_slug': 'newbies',
                'proposal_slug': 'how-to-learn-django'})
        response = self.client.get(url)
        self.assertIn(u'Not accepted', response.content.decode('utf-8'))

        url = reverse('proposal-page', kwargs={'track_slug':
            'just-another-track',
                'proposal_slug': 'i-dont-know-6'})
        response = self.client.get(url)
        self.assertIn(u'Confirmed', response.content.decode('utf-8'))

    def test_proposal_page_should_have_speaker_info(self):
        url = reverse('proposal-page', kwargs={'track_slug': 'newbies',
                'proposal_slug': 'how-to-learn-python'})
        response = self.client.get(url)
        speaker = AccountProfile.objects.get(user=User.objects.get(pk=1))
        self.assertEqual(len(response.context['speakers']), 1)
        speaker_response = response.context['speakers'][0]
        self.assertEqual(speaker_response['name'], speaker.name)
        self.assertEqual(speaker_response['twitter'], speaker.twitter)
        self.assertEqual(speaker_response['institution'], speaker.institution)
        self.assertEqual(speaker_response['bio'], speaker.description)
        self.assertEqual(speaker_response['profession'], speaker.profession)

    def test_proposal_page_should_include_speaker_without_profile(self):
        url = reverse('proposal-page',
                kwargs={'track_slug': 'just-another-track',
                        'proposal_slug': 'how-to-learn-django'})
        response = self.client.get(url)
        speaker = user=User.objects.get(pk=2)
        self.assertEqual(len(response.context['speakers']), 2)
        speaker_response = response.context['speakers'][1]
        self.assertEqual(speaker_response['name'], speaker.username)
        self.assertEqual(speaker_response['twitter'], '')
        self.assertEqual(speaker_response['institution'], '')
        self.assertEqual(speaker_response['bio'], '')
        self.assertEqual(speaker_response['profession'], '')

########NEW FILE########
__FILENAME__ = test_session_admin
# -*- coding: utf-8 -*-

from django.contrib import admin as django_admin
from django.contrib.auth import models as auth_models
from django.core import management
from django.test import TestCase

from pythonbrasil8.dashboard import models as dashboard_models
from pythonbrasil8.schedule import admin, models


class SessionAdminTestCase(TestCase):

    def test_Session_should_be_registered(self):
        self.assertIn(models.Session, django_admin.site._registry)

    def test_Session_should_be_registered_with_SessionAdmin(self):
        self.assertIsInstance(django_admin.site._registry[models.Session],
                              admin.SessionAdmin)

    def test_should_display_the_title(self):
        self.assertIn("title", admin.SessionAdmin.list_display)

    def test_should_display_the_type(self):
        self.assertIn("type", admin.SessionAdmin.list_display)

    def test_should_display_speakers(self):
        self.assertIn("speaker_names", admin.SessionAdmin.list_display)

    def test_should_display_the_track(self):
        self.assertIn("track", admin.SessionAdmin.list_display)

    def test_should_display_the_status(self):
        self.assertIn("status", admin.SessionAdmin.list_display)

    def test_should_be_able_to_filter_by_type(self):
        self.assertIn("type", admin.SessionAdmin.list_filter)

    def test_should_be_able_to_filter_by_status(self):
        self.assertIn("status", admin.SessionAdmin.list_filter)

    def test_speaker_names_should_return_the_name_of_the_speakers(self):
        user1, _ = auth_models.User.objects.get_or_create(username="foo",
                                                          email="foo@bar.com")
        dashboard_models.AccountProfile.objects.create(user=user1)
        user2, _ = auth_models.User.objects.get_or_create(username="foo2",
                                                          email="foo2@bar.com")
        dashboard_models.AccountProfile.objects.create(user=user2)
        user3, _ = auth_models.User.objects.get_or_create(username="foo3",
                                                          email="foo3@bar.com")
        dashboard_models.AccountProfile.objects.create(user=user3,
                                                       name="Foo Bar")
        track, _ = models.Track.objects.get_or_create(name_en_us="Session test",
                                                      description_en_us="test")
        session = models.Session.objects.create(
            title=u"Admin test",
            description=u"desc",
            type=u"admin_test",
            status=u"proposed",
            language=u"pt",
            track=track,
        )
        session.speakers = [user1, user2, user3]
        session.save()
        adm = admin.SessionAdmin(session, None)
        self.assertEqual("foo, foo2, Foo Bar", adm.speaker_names(session))

    def test_speaker_names_should_have_short_description(self):
        self.assertEqual(u"Speakers",
                         admin.SessionAdmin.speaker_names.short_description)

########NEW FILE########
__FILENAME__ = test_session_form
# -*- coding: utf-8 -*-
from django.test import TestCase

from pythonbrasil8.schedule import forms, models


class SessionFormTestCase(TestCase):

    def test_model_should_be_Session(self):
        self.assertEqual(models.Session, forms.SessionForm._meta.model)

    def test_should_exclude_speakers_field(self):
        self.assertIn("speakers", forms.SessionForm._meta.exclude)

    def test_should_exclude_status_field(self):
        self.assertIn("status", forms.SessionForm._meta.exclude)

########NEW FILE########
__FILENAME__ = test_session_model
# -*- coding: utf-8 -*-
from django.test import TestCase
from django.db.models import CharField, ForeignKey, ManyToManyField

from pythonbrasil8.schedule.models import Session, Track


class SessionModelTestCase(TestCase):

    def test_should_have_title(self):
        self.assert_field_in("title", Session)

    def test_title_should_have_verbose_name(self):
        field = Session._meta.get_field_by_name("title")[0]
        self.assertEqual(u"Title", field.verbose_name)

    def test_should_have_description(self):
        self.assert_field_in("description", Session)

    def test_description_should_have_verbose_name(self):
        field = Session._meta.get_field_by_name("description")[0]
        self.assertEqual(u"Description", field.verbose_name)

    def test_should_have_speakers(self):
        self.assert_field_in("speakers", Session)

    def test_speakers_should_have_verbose_name(self):
        field = Session._meta.get_field_by_name("speakers")[0]
        self.assertEqual(u"Speakers", field.verbose_name)

    def test_should_have_type(self):
        self.assert_field_in("type", Session)

    def test_type_should_have_verbose_name(self):
        field = Session._meta.get_field_by_name("type")[0]
        self.assertEqual(u"Type", field.verbose_name)

    def test_should_have_audience_level(self):
        self.assert_field_in("audience_level", Session)

    def test_audience_level_should_have_choices(self):
        audience_level_field = Session._meta.get_field_by_name("audience_level")[0]
        choices = [choice[0] for choice in audience_level_field._choices]
        self.assertIn("beginner", choices)
        self.assertIn("intermediate", choices)
        self.assertIn("advanced", choices)

    def test_type_should_have_choices(self):
        type_field = Session._meta.get_field_by_name("type")[0]
        choices = [choice[0] for choice in type_field._choices]
        self.assertIn("talk", choices)
        self.assertIn("tutorial", choices)

    def test_speakers_shoudl_be_a_ManyToManyField(self):
        speakers_field = Session._meta.get_field_by_name("speakers")[0]
        self.assertIsInstance(speakers_field, ManyToManyField)

    def test_should_have_a_foreign_key_to_track(self):
        self.assert_field_in("track", Session)
        field = Session._meta.get_field_by_name("track")[0]
        self.assertIsInstance(field, ForeignKey)

    def test_track_fk_should_point_to_Track_model(self):
        field = Session._meta.get_field_by_name("track")[0]
        self.assertEqual(Track, field.related.parent_model)

    def test_track_should_have_a_verbose_name(self):
        field = Session._meta.get_field_by_name("track")[0]
        self.assertEqual(u"Track", field.verbose_name)

    def test_should_have_a_language_field(self):
        self.assert_field_in("language", Session)

    def test_language_should_be_a_CharField(self):
        field = Session._meta.get_field_by_name("language")[0]
        self.assertIsInstance(field, CharField)

    def test_language_should_have_at_most_2_characters(self):
        field = Session._meta.get_field_by_name("language")[0]
        self.assertEqual(2, field.max_length)

    def test_language_should_have_three_options_en_es_pt(self):
        expected = (
            ("pt", "Portuguese"),
            ("en", "English"),
            ("es", "Spanish"),
        )
        field = Session._meta.get_field_by_name("language")[0]
        self.assertEqual(expected, field.choices)

    def test_language_should_have_a_verbose_name(self):
        field = Session._meta.get_field_by_name("language")[0]
        self.assertEqual(u"Language", field.verbose_name)

    def test_should_have_status(self):
        self.assert_field_in("status", Session)

    def test_status_should_be_CharField(self):
        field = Session._meta.get_field_by_name("status")[0]
        self.assertIsInstance(field, CharField)

    def test_status_should_have_at_most_10_characters(self):
        field = Session._meta.get_field_by_name("status")[0]
        self.assertEqual(10, field.max_length)

    def test_status_should_have_choices(self):
        expected = (
            (u"proposed", u"Proposed"),
            (u"accepted", u"Accepted"),
            (u"confirmed", u"Confirmed"),
            (u"canceled", u"Canceled"),
        )
        field = Session._meta.get_field_by_name("status")[0]
        self.assertEqual(expected, field.choices)

    def test_status_should_be_proposed_by_default(self):
        field = Session._meta.get_field_by_name("status")[0]
        self.assertEqual("proposed", field.default)

    def assert_field_in(self, field_name, model):
        self.assertIn(field_name, model._meta.get_all_field_names())

########NEW FILE########
__FILENAME__ = test_session_view
# -*- coding: utf-8 -*-
from django import http, test
from django.contrib.auth import models as auth_models
from django.template.response import TemplateResponse
from django.test import client

from pythonbrasil8.schedule import forms, models, views


class SessionViewTestCase(test.TestCase):

    def setUp(self):
        self.request = client.RequestFactory().get("/")
        self.request.user = auth_models.User()

    def tearDown(self):
        models.Session.objects.filter(title="some title").delete()

    def test_should_returns_200_when_accessed_by_get(self):
        result = views.SubscribeView.as_view()(self.request)
        self.assertEqual(200, result.status_code)

    def test_should_be_use_a_expected_template(self):
        result = views.SubscribeView.as_view()(self.request)
        self.assertEqual(['schedule/subscribe.html'], result.template_name)

    def test_should_be_form_in_context(self):
        result = views.SubscribeView.as_view()(self.request)
        self.assertIn('form', result.context_data)
        self.assertIsInstance(result.context_data['form'], forms.SessionForm)

    def test_form_valid_saves_the_form_using_the_user_from_request(self):
        user, _ = auth_models.User.objects.get_or_create(username="foo", email="foo@bar.com")
        track, _ = models.Track.objects.get_or_create(name_en_us="Session test", description_en_us="test")
        data = {
            "title": "some title",
            "description": "some description",
            "type": "talk",
            "audience_level": "intermediate",
            "tags": "some, tags",
            "track": track.pk,
            "language": "pt",
            "status": "proposed",
        }
        form = forms.SessionForm(data)
        request = client.RequestFactory().post("/", data)
        request.user = user
        v = views.SubscribeView(request=request)
        v.form_valid(form)
        s = models.Session.objects.get(title="some title")
        self.assertEqual(user, s.speakers.all()[0])

    def test_should_create_a_session_with_the_post_data_getting_user_from_request(self):
        user, _ = auth_models.User.objects.get_or_create(username="foo", email="foo@bar.com")
        track, _  = models.Track.objects.get_or_create(name_en_us="Session test", description_en_us="test")
        data = {
            "title": "some title",
            "description": "some description",
            "type": "talk",
            "tags": "some, tags",
            "track": track.pk,
            "language": "pt",
            "status": "proposed",
            "audience_level": "intermediate"
        }
        request = client.RequestFactory().post("/", data)
        request.user = user
        result = views.SubscribeView.as_view()(request)
        self.assertEqual(302, result.status_code)
        session = models.Session.objects.get(title=data["title"])
        self.assertTrue(session.id)
        t = models.Session.objects.get(speakers=user)
        self.assertEqual(u"some title", t.title)

    def test_should_save_the_current_user_and_extra_speakers(self):
        user1, _ = auth_models.User.objects.get_or_create(username="foo", email="foo@bar.com")
        user2, _ = auth_models.User.objects.get_or_create(username="foo2", email="foo2@bar.com")
        track, _ = models.Track.objects.get_or_create(name_en_us="Session test", description_en_us="test")
        data = {
            "title": "some title",
            "description": "some description",
            "type": "talk",
            "tags": "some, tags",
            "track": track.pk,
            "language": "pt",
            "status": "proposed",
            "extra_speakers": "foo2@bar.com",
            "audience_level": "beginner"
        }
        request = client.RequestFactory().post("/", data)
        request.user = user1
        result = views.SubscribeView.as_view()(request)
        self.assertEqual(302, result.status_code)
        session = models.Session.objects.get(title=data["title"])
        self.assertTrue(session.id)
        t = models.Session.objects.get(speakers=user1)
        self.assertEqual(u"some title", t.title)
        self.assertEqual([user1, user2], list(t.speakers.all()))

    def test_should_keep_extra_speakers_in_the_context_if_the_form_validation_fails(self):
        user1, _ = auth_models.User.objects.get_or_create(username="foo", email="foo@bar.com")
        user2, _ = auth_models.User.objects.get_or_create(username="foo2", email="foo2@bar.com")
        data = {
            "title": "some title",
            "language": "pt",
            "extra_speakers": "foo2@bar.com",
        }
        request = client.RequestFactory().post("/", data)
        request.user = user1
        response = views.SubscribeView.as_view()(request)
        self.assertIsInstance(response, TemplateResponse)
        self.assertEqual(["foo2@bar.com"], response.context_data["extra_speakers"])

    def test_get_speakers_return_speakers_from_extra_speakers_parameter(self):
        user1, _ = auth_models.User.objects.get_or_create(username="foo", email="foo@bar.com")
        user2, _ = auth_models.User.objects.get_or_create(username="foo2", email="foo2@bar.com")
        user3, _ = auth_models.User.objects.get_or_create(username="foo3", email="foo3@bar.com")
        v = views.SubscribeView()
        v.request = client.RequestFactory().post("/", {})
        v.request.POST = http.QueryDict("extra_speakers=foo&extra_speakers=foo2&extra_speakers=foo3@bar.com")
        speakers = v.get_extra_speakers()
        self.assertEqual([user1, user2, user3], list(speakers))

    def test_get_speakers_return_speakers_from_extra_speakers_parameter_even_if_it_is_only_one(self):
        user1, _ = auth_models.User.objects.get_or_create(username="foo", email="foo@bar.com")
        user2, _ = auth_models.User.objects.get_or_create(username="foo2", email="foo2@bar.com")
        user3, _ = auth_models.User.objects.get_or_create(username="foo3", email="foo3@bar.com")
        v = views.SubscribeView()
        v.request = client.RequestFactory().post("/", {"extra_speakers": "foo2@bar.com"})
        speakers = v.get_extra_speakers()
        self.assertEqual([user2], list(speakers))

    def test_get_speakers_return_empty_list_if_extra_speakers_is_missing(self):
        v = views.SubscribeView()
        v.request = client.RequestFactory().post("/", {})
        speakers = v.get_extra_speakers()
        self.assertEqual([], list(speakers))

########NEW FILE########
__FILENAME__ = test_track_admin
# -*- coding: utf-8 -*-
import unittest

from django.contrib import admin as django_admin

from pythonbrasil8.schedule import admin, models


class TrackAdminTestCase(unittest.TestCase):

    def test_should_be_registered(self):
        self.assertIn(models.Track, django_admin.site._registry)

    def test_should_be_registered_with_the_TrackAdmin_class(self):
        self.assertIsInstance(django_admin.site._registry[models.Track],
                              admin.TrackAdmin)

    def test_should_display_the_name_of_the_track(self):
        self.assertIn("name", admin.TrackAdmin.list_display)

########NEW FILE########
__FILENAME__ = test_track_model
# -*- coding: utf-8 -*-
import unittest

import transmeta

from django.db import models as django_models

from pythonbrasil8.schedule import models


class TrackModelTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.fields = {}
        for name in models.Track._meta.get_all_field_names():
            cls.fields[name] = models.Track._meta.get_field_by_name(name)[0]

    def test_should_use_TransMeta_as_metaclass(self):
        self.assertIsInstance(models.Track, transmeta.TransMeta)

    def test_should_have_a_name_field(self):
        self.assertIn("name_en_us", self.fields)
        self.assertIn("name_pt_br", self.fields)

    def test_name_should_be_a_CharField(self):
        field = self.fields["name_en_us"]
        self.assertIsInstance(field, django_models.CharField)

    def test_name_should_have_at_most_255_characters(self):
        field = self.fields["name_en_us"]
        self.assertEqual(255, field.max_length)

    def test_should_translate_name(self):
        self.assertIn("name", models.Track._meta.translatable_fields)

    def test_should_have_a_description_field(self):
        self.assertIn("description_en_us", self.fields)
        self.assertIn("description_pt_br", self.fields)

    def test_description_should_be_a_CharField(self):
        field = self.fields["description_en_us"]
        self.assertIsInstance(field, django_models.CharField)

    def test_description_should_have_at_most_2000_characters(self):
        field = self.fields["description_en_us"]
        self.assertEqual(2000, field.max_length)

    def test_should_translate_description(self):
        self.assertIn("description", models.Track._meta.translatable_fields)

    def test_should_be_represented_by_its_name(self):
        t = models.Track(name_en_us=u"Django")
        self.assertEqual(u"Django", unicode(t))
        self.assertEqual(u"Django", str(t))

########NEW FILE########
__FILENAME__ = test_track_page
# coding: utf-8

from django.core import management
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.contrib.auth.models import User
from unittest import skip
from pythonbrasil8.schedule.models import Session


class NewTrackPage(TestCase):
    fixtures = ['sessions.json']

    def test_track_page_should_redirect_to_schedule_page(self):
        url = reverse('track-page', kwargs={'track_slug': 'newbies'})

        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        next_url = response.get('location', None)
        self.assertEqual(next_url, 'http://testserver' + reverse('schedule'))

        self.client.user = User.objects.create_user(username='user',
                                                    password='test')
        self.client.login(username='user', password='test')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        next_url = response.get('location', None)
        self.assertEqual(next_url, 'http://testserver' + reverse('schedule'))

@skip('Track should redirect to accepted proposals')
class TrackPageTestCase(TestCase):
    fixtures = ['sessions.json']

    def test_inexistent_track_should_return_404(self):
        url = reverse('track-page', kwargs={'track_slug': 'do-not-exist'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_track_page_should_list_all_proposals_to_that_track(self):
        url = reverse('track-page', kwargs={'track_slug': 'newbies'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        for proposal in Session.objects.filter(track=1):
            self.assertIn(proposal.title, content)
            self.assertIn(proposal.slug, content)

########NEW FILE########
__FILENAME__ = test_vote_page
# coding: utf-8

import json
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.test import TestCase
from unittest import skip
from pythonbrasil8.schedule.models import Track, Session, ProposalVote


class DisabledVotePage(TestCase):

    def test_vote_page_should_always_redirect_to_schedule_page(self):
        url = reverse('vote_page')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        next_url = response.get('location', None)
        self.assertEqual(next_url, 'http://testserver' + reverse('schedule'))

        self.client.user = User.objects.create_user(username='user',
                                                    password='test')
        self.client.login(username='user', password='test')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        next_url = response.get('location', None)
        self.assertEqual(next_url, 'http://testserver' + reverse('schedule'))


@skip('Voting is disabled')
class VotePage(TestCase):
    fixtures = ['sessions.json']

    def test_vote_page_should_redirect_user_that_is_not_logged_in(self):
        url = reverse('vote_page')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_vote_page_should_return_200_for_user_that_is_logged_in(self):
        url = reverse('vote_page')
        self.client.user = User.objects.create_user(username='user',
                                                    password='test')
        self.client.login(username='user', password='test')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_all_tracks_should_appear_on_vote_page(self):
        url = reverse('vote_page')
        self.client.user = User.objects.create_user(username='user',
                                                    password='test')
        self.client.login(username='user', password='test')
        response = self.client.get(url)
        content = response.content.decode('utf8')
        tracks = Track.objects.all()
        for track in tracks:
            self.assertIn(track.name, content)

    def test_only_proposed_sessions_should_appear_on_each_track(self):
        url = reverse('vote_page')
        self.client.user = User.objects.create_user(username='user',
                                                    password='test')
        self.client.login(username='user', password='test')
        response = self.client.get(url)
        content = response.content.decode('utf8')
        for session in Session.objects.filter(type='talk', status='proposed'):
            self.assertIn(session.title, content)
        for session in Session.objects.filter(type='talk').exclude(status='proposed'):
            self.assertNotIn(session.title, content)

    def test_tracks_should_appear_in_random_order(self):
        url = reverse('vote_page')
        self.client.user = User.objects.create_user(username='user',
                                                    password='test')
        self.client.login(username='user', password='test')

        tracks = []
        for i in range(50):
            response = self.client.get(url)
            tracks_and_sessions = response.context['tracks_and_sessions']
            tracks.append([track for track, sessions in tracks_and_sessions])

        diff_counter = 0
        for track in tracks[1:]:
            self.assertEqual(set(track), set(tracks[0]))
            if tracks[0] != track:
                diff_counter += 1

        self.assertTrue(diff_counter > 0)

    def test_only_talk_proposals_should_appear(self):
        url = reverse('vote_page')
        self.client.user = User.objects.create_user(username='user',
                                                    password='test')
        self.client.login(username='user', password='test')

        response = self.client.get(url)
        tracks_and_sessions = dict(response.context['tracks_and_sessions'])
        proposals = set()
        for tracks, sessions in tracks_and_sessions.items():
            proposals.update(sessions)
        talk_proposals = set(list(Session.objects.filter(type='talk', status='proposed')))
        self.assertEqual(talk_proposals, proposals)

    def test_sessions_should_appear_in_random_order_inside_a_track(self):
        url = reverse('vote_page')
        self.client.user = User.objects.create_user(username='user',
                                                    password='test')
        self.client.login(username='user', password='test')

        tracks_and_sessions = []
        for i in range(50):
            response = self.client.get(url)
            these_tracks = dict(response.context['tracks_and_sessions'])
            tracks_and_sessions.append(these_tracks)
        tracks = Track.objects.all()
        for track in tracks:
            diff_counter = 0
            first_request = tracks_and_sessions[0][track]
            for ts in tracks_and_sessions[1:]:
                self.assertEqual(set(ts[track]), set(first_request))
                if ts[track] != first_request:
                    diff_counter += 1
            self.assertTrue(diff_counter > 0)


@skip('Voting is disabled')
class ProposalVoteTest(TestCase):
    fixtures = ['sessions.json']

    def _login(self):
        self.client.user = User.objects.create_user(username='user',
                                                    password='test')
        self.client.login(username='user', password='test')

    def test_should_redirect_user_that_is_not_logged_in(self):
        url = reverse('proposal_vote', kwargs={'proposal_id': 1,
                                               'type_of_vote': 'up'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_should_only_allow_post_method(self):
        self._login()
        url = reverse('proposal_vote', kwargs={'proposal_id': 3,
                                               'type_of_vote': 'up'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)
        response = self.client.put(url)
        self.assertEqual(response.status_code, 405)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 405)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)

    def test_should_return_404_when_invalid_type_of_vote(self):
        self._login()
        url = reverse('proposal_vote', kwargs={'proposal_id': 1,
                                               'type_of_vote': 'python'})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 404)

    def test_should_return_404_when_invalid_proposal_id(self):
        self._login()
        url = reverse('proposal_vote', kwargs={'proposal_id': 9999999,
                                               'type_of_vote': 'up'})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 404)

    def test_should_return_404_if_trying_to_vote_for_a_tutorial(self):
        self._login()
        url = reverse('proposal_vote', kwargs={'proposal_id': 1,
                                               'type_of_vote': 'up'})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 404)

    def test_should_insert_one_row_if_vote_up(self):
        self._login()
        url = reverse('proposal_vote', kwargs={'proposal_id': 3,
                                               'type_of_vote': 'up'})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        session = Session.objects.get(pk=3)
        votes = ProposalVote.objects.filter(session=session, vote=1,
                                            user=self.client.user)
        self.assertEqual(votes.count(), 1)

        url = reverse('proposal_vote', kwargs={'proposal_id': 4,
                                               'type_of_vote': 'down'})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        session = Session.objects.get(pk=4)
        votes = ProposalVote.objects.filter(session=session, vote=-1,
                                            user=self.client.user)
        self.assertEqual(votes.count(), 1)

    def test_if_an_idiot_vote_more_than_once_for_the_same_talk_should_only_insert_one_row(self):
        self._login()
        url = reverse('proposal_vote', kwargs={'proposal_id': 3,
                                               'type_of_vote': 'up'})
        for i in range(5):
            self.client.post(url)
        session = Session.objects.get(pk=3)
        votes = ProposalVote.objects.filter(session=session, vote=1,
                                            user=self.client.user)
        self.assertEqual(votes.count(), 1)

        url = reverse('proposal_vote', kwargs={'proposal_id': 4,
                                               'type_of_vote': 'down'})
        for i in range(5):
            self.client.post(url)
        session = Session.objects.get(pk=4)
        votes = ProposalVote.objects.filter(session=session, vote=-1,
                                            user=self.client.user)
        self.assertEqual(votes.count(), 1)

    def test_neutral_votes_should_remove_record_for_that_user_and_talk(self):
        self._login()
        url = reverse('proposal_vote', kwargs={'proposal_id': 3,
                                               'type_of_vote': 'neutral'})
        self.client.post(url)
        session = Session.objects.get(pk=3)
        votes = ProposalVote.objects.filter(session=session,
                                            user=self.client.user)
        self.assertEqual(votes.count(), 0)

    def test_alternated_votes_should_record_only_the_last_one(self):
        self._login()
        types_of_vote = ('up', 'down', 'neutral')
        for type_1 in types_of_vote:
            for type_2 in types_of_vote:
                url = reverse('proposal_vote', kwargs={'proposal_id': 3,
                                                       'type_of_vote': type_1})
                self.client.post(url)
                url = reverse('proposal_vote', kwargs={'proposal_id': 3,
                                                       'type_of_vote': type_2})
                self.client.post(url)

                session = Session.objects.get(pk=3)
                votes = ProposalVote.objects.filter(session=session,
                                                    user=self.client.user)
                if type_2 == 'up':
                    self.assertEqual(votes.count(), 1)
                    self.assertEqual(votes[0].vote, 1)
                elif type_2 == 'down':
                    self.assertEqual(votes.count(), 1)
                    self.assertEqual(votes[0].vote, -1)
                if type_2 == 'neutral':
                    self.assertEqual(votes.count(), 0)

    def test_should_return_a_JSON_with_vote_information(self):
        self._login()
        url = reverse('proposal_vote', kwargs={'proposal_id': 3,
                                               'type_of_vote': 'neutral'})
        response = self.client.post(url)
        result = json.loads(response.content)
        self.assertEqual(result, {'proposal_id': 3, 'vote': 'neutral'})

        url = reverse('proposal_vote', kwargs={'proposal_id': 3,
                                               'type_of_vote': 'up'})
        response = self.client.post(url)
        result = json.loads(response.content)
        self.assertEqual(result, {'proposal_id': 3, 'vote': 'up'})

        url = reverse('proposal_vote', kwargs={'proposal_id': 3,
                                               'type_of_vote': 'down'})
        response = self.client.post(url)
        result = json.loads(response.content)
        self.assertEqual(result, {'proposal_id': 3, 'vote': 'down'})

    def test_should_load_past_votes(self):
        self._login()
        url = reverse('proposal_vote', kwargs={'proposal_id': 2,
                                               'type_of_vote': 'up'})
        self.client.post(url)

        url = reverse('proposal_vote', kwargs={'proposal_id': 3,
                                               'type_of_vote': 'neutral'})
        self.client.post(url)
        url = reverse('proposal_vote', kwargs={'proposal_id': 4,
                                               'type_of_vote': 'neutral'})
        self.client.post(url)

        url = reverse('proposal_vote', kwargs={'proposal_id': 6,
                                               'type_of_vote': 'down'})
        self.client.post(url)
        url = reverse('proposal_vote', kwargs={'proposal_id': 7,
                                               'type_of_vote': 'down'})
        self.client.post(url)
        url = reverse('proposal_vote', kwargs={'proposal_id': 8,
                                               'type_of_vote': 'down'})
        self.client.post(url)

        response = self.client.get(reverse('vote_page'))
        content = response.content.decode('utf-8')
        self.assertEqual(content.count('up_active.png'), 1)
        self.assertEqual(content.count('neutral_active.png'), 2)
        self.assertEqual(content.count('down_active.png'), 2)

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-

from django import http, shortcuts
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.template import response, RequestContext
from django.utils.translation import ugettext as _
from django.views.generic import CreateView, View

from pythonbrasil8.core.views import LoginRequiredMixin
from pythonbrasil8.schedule.forms import SessionForm
from pythonbrasil8.schedule.models import Session, Track


VOTE = {'up': 1, 'down': -1, 'neutral': 0}


class SubscribeView(LoginRequiredMixin, CreateView):
    form_class = SessionForm
    template_name = "schedule/subscribe.html"

    def get_success_url(self):
        return reverse("dashboard-index")

    def get_extra_speakers(self):
        es = self.request.POST.getlist("extra_speakers")
        return User.objects.filter(Q(username__in=es) | Q(email__in=es))

    def form_valid(self, form):
        r = super(SubscribeView, self).form_valid(form)
        spkrs = [self.request.user]
        spkrs.extend(self.get_extra_speakers())
        self.object.speakers = spkrs
        self.object.save()
        return r

    def get(self, request, *args, **kwargs):
        r = super(SubscribeView, self).get(request, *args, **kwargs)
        r.context_data["tracks"] = Track.objects.all()
        return r

    def post(self, request, *args, **kwargs):
        r = super(SubscribeView, self).post(request, *args, **kwargs)
        if isinstance(r, http.HttpResponseRedirect):
            messages.success(request, _("Session successfully submitted!"), fail_silently=True)
        else:
            r.context_data["extra_speakers"] = self.request.POST.getlist("extra_speakers")
        return r


class EditSessionView(LoginRequiredMixin, View):
    form_class = SessionForm
    template_name = "schedule/edit-session.html"

    def get(self, request, id):
        session = shortcuts.get_object_or_404(Session, pk=id, speakers=request.user)
        form = self.form_class(instance=session)
        extra_speakers = session.speakers.exclude(username=request.user.username)
        tracks = Track.objects.all()
        return response.TemplateResponse(request, self.template_name, {"session": session, "form": form, "tracks": tracks,
            "extra_speakers": extra_speakers})

    def post(self, request, id):
        session = shortcuts.get_object_or_404(Session, pk=id, speakers=request.user)
        form = self.form_class(request.POST, instance=session)
        if form.is_valid():
            form.save()
            messages.success(request, _("Session successfully updated!"), fail_silently=True)
            return http.HttpResponseRedirect(reverse("dashboard-sessions"))
        tracks = Track.objects.all()
        return response.TemplateResponse(request, self.template_name, {"session": session, "form": form, "tracks": tracks})


class DeleteSessionView(LoginRequiredMixin, View):

    def get(self, request, id):
        session = shortcuts.get_object_or_404(Session, pk=id, speakers=request.user)
        session.delete()
        messages.success(request, _("Session successfully deleted!"), fail_silently=True)
        return http.HttpResponseRedirect(reverse("dashboard-sessions"))


class FinishedProposalsView(LoginRequiredMixin, View):
    template_name = u"schedule/finished_proposals.html"

    def get(self, request):
        return response.TemplateResponse(request, self.template_name)


def schedule(request):
    '''Show accepted talk proposals'''
    tracks = Track.objects.all().order_by('name_en_us')
    tracks_and_sessions = {}
    for track in tracks:
        sessions = Session.objects.filter(track=track, type='talk',
                                          status__in=['accepted', 'confirmed'])
        tracks_and_sessions[track] = sessions
    data = {'tracks_and_sessions': tracks_and_sessions.items()}
    return shortcuts.render_to_response('schedule.html', data,
            context_instance=RequestContext(request))


def track_page(request, track_slug):
    return http.HttpResponseRedirect(reverse("schedule"))


def proposal_page(request, track_slug, proposal_slug):
    shortcuts.get_object_or_404(Track, slug=track_slug)
    proposal = shortcuts.get_object_or_404(Session, slug=proposal_slug)

    speakers = []
    for speaker in proposal.speakers.all():
        try:
            profile = speaker.get_profile()
            name = profile.name
            bio = profile.description
            twitter = profile.twitter
            institution = profile.institution
            profession = profile.profession
        except ObjectDoesNotExist:
            name = speaker.username
            twitter = ''
            bio = ''
            institution = ''
            profession = ''
        speakers.append({'name': name, 'twitter': twitter, 'bio': bio,
                         'institution': institution, 'profession': profession})
    data = {'proposal': proposal, 'speakers': speakers}
    return shortcuts.render_to_response('proposal.html', data,
            context_instance=RequestContext(request))


def vote_page(request):
    return http.HttpResponseRedirect(reverse("schedule"))

########NEW FILE########
__FILENAME__ = settings
# coding: utf-8
import os
# Django settings for pythonbrasil8 project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

PROJECT_DIR = os.path.dirname(__file__)

ADMINS = ()

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(PROJECT_DIR, 'pythonbrasil8.sqlite3'),
    }
}

TIME_ZONE = 'America/Sao_Paulo'
LANGUAGE_CODE = 'en-us'
LANGUAGES = (
    ('en-us', 'English'),
    ('pt-br', u'Português'),
)

SITE_ID = 1

USE_I18N = True
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = False

MEDIA_ROOT = os.path.join(PROJECT_DIR, 'media')
MEDIA_URL = '/media/'

STATIC_ROOT = os.path.join(PROJECT_DIR, 'static')
STATIC_URL = '/static/'
STATICFILES_DIRS = (
    os.path.join(PROJECT_DIR, 'static_files'),
)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
)

SECRET_KEY = 'i)=$2sz)alxoe0v9qtpur*_cmwyxuft!#w=#i3)=+4fvu1*)ex'

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.request',
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.contrib.messages.context_processors.messages',
)

PAGE_CACHE_MAXAGE = 120

MIDDLEWARE_CLASSES = (
    'pythonbrasil8.core.middleware.CacheMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'pythonbrasil8.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'pythonbrasil8.wsgi.application'

TEMPLATE_DIRS = (
    os.path.join(PROJECT_DIR, 'templates'),
)


TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

NOSE_ARGS = ['--quiet', "-sd", '--nologcapture']

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django.contrib.markup',
    'pythonbrasil8.core',
    'mittun.events',
    'mittun.sponsors',
    'django.contrib.admin',
    'django_nose',
    'compressor',
    'south',
    'registration',
    'pythonbrasil8.dashboard',
    'pythonbrasil8.schedule',
    'pythonbrasil8.subscription',
    'pythonbrasil8.news',
)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

#django-registration settings
ACCOUNT_ACTIVATION_DAYS = 7

LOGIN_REDIRECT_URL = '/dashboard/'

EMAIL_PORT = 25
EMAIL_USE_TLS = True
EMAIL_SENDER = 'organizacao@python.org.br'


AUTH_PROFILE_MODULE = 'dashboard.AccountProfile'

PAGSEGURO = {
    'email': 'ps@pythonbrasil.org.br',
    'charset': 'UTF-8',
    'token': 'radiogaga',
    'currency': 'BRL',
    'itemId1': '0001',
    'itemQuantity1': 1,
}

PAGSEGURO_BASE = 'https://ws.pagseguro.uol.com.br/v2'
PAGSEGURO_CHECKOUT = '%s/checkout' % PAGSEGURO_BASE
PAGSEGURO_TRANSACTIONS = '%s/transactions' % PAGSEGURO_BASE
PAGSEGURO_TRANSACTIONS_NOTIFICATIONS = '%s/notifications' % PAGSEGURO_TRANSACTIONS
PAGSEGURO_WEBCHECKOUT = 'https://pagseguro.uol.com.br/v2/checkout/payment.html?code='

COMPRESS_OFFLINE = False
COMPRESS_ENABLED = False

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from pythonbrasil8.subscription import models


def name(subscription):
    return subscription.user.get_profile().name
name.short_description = u"Name"


class SubscriptionAdmin(admin.ModelAdmin):
    search_fields = ("user__email", "user__username")
    list_display = (name, "status",)
    list_filter = ("status",)

admin.site.register(models.Subscription, SubscriptionAdmin)

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):
        db.create_table('subscription_subscription', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=25)),
        ))
        db.send_create_signal('subscription', ['Subscription'])

        db.create_table('subscription_transaction', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('subscription', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['subscription.Subscription'])),
            ('code', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('status', self.gf('django.db.models.fields.CharField')(max_length=25)),
            ('price', self.gf('django.db.models.fields.DecimalField')(max_digits=5, decimal_places=2)),
        ))
        db.send_create_signal('subscription', ['Transaction'])

    def backwards(self, orm):
        db.delete_table('subscription_subscription')
        db.delete_table('subscription_transaction')

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 6, 3, 18, 0, 6, 858734)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 6, 3, 18, 0, 6, 858541)'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'subscription.subscription': {
            'Meta': {'object_name': 'Subscription'},
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'subscription.transaction': {
            'Meta': {'object_name': 'Transaction'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'price': ('django.db.models.fields.DecimalField', [], {'max_digits': '5', 'decimal_places': '2'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'subscription': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['subscription.Subscription']"})
        }
    }

    complete_apps = ['subscription']

########NEW FILE########
__FILENAME__ = 0002_auto__add_field_subscription_status
# -*- coding: utf-8 -*-
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):
        db.add_column('subscription_subscription', 'status', self.gf('django.db.models.fields.CharField')(default='pending', max_length=20), keep_default=True)

    def backwards(self, orm):
        db.delete_column('subscription_subscription', 'status')

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 11, 11, 17, 57, 8, 469152)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 11, 11, 17, 57, 8, 469036)'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'subscription.subscription': {
            'Meta': {'object_name': 'Subscription'},
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'pending'", 'max_length': '20'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'subscription.transaction': {
            'Meta': {'object_name': 'Transaction'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'price': ('django.db.models.fields.DecimalField', [], {'max_digits': '5', 'decimal_places': '2'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'subscription': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['subscription.Subscription']"})
        }
    }

    complete_apps = ['subscription']

########NEW FILE########
__FILENAME__ = 0003_subscription_status
# -*- coding: utf-8 -*-
from south.v2 import DataMigration


class Migration(DataMigration):

    def forwards(self, orm):
        qs = orm.Subscription.objects.prefetch_related('transaction_set')
        qs.filter(transaction__status='done').exclude(transaction__price=0).update(status='confirmed')
        qs.filter(transaction__status='done', transaction__price=0).update(status='sponsor')

    def backwards(self, orm):
        raise RuntimeError("Irreversible migration.")

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 11, 11, 18, 6, 26, 33885)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 11, 11, 18, 6, 26, 33774)'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'subscription.subscription': {
            'Meta': {'object_name': 'Subscription'},
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'pending'", 'max_length': '20'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'subscription.transaction': {
            'Meta': {'object_name': 'Transaction'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'price': ('django.db.models.fields.DecimalField', [], {'max_digits': '5', 'decimal_places': '2'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'subscription': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['subscription.Subscription']"})
        }
    }

    complete_apps = ['subscription']

########NEW FILE########
__FILENAME__ = 0004_auto_add_field_tutorials
# -*- coding: utf-8 -*-
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        db.create_table('subscription_subscription_tutorials', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('subscription', models.ForeignKey(orm['subscription.subscription'], null=False)),
            ('session', models.ForeignKey(orm['schedule.session'], null=False))
        ))
        db.create_unique('subscription_subscription_tutorials', ['subscription_id', 'session_id'])

    def backwards(self, orm):
        db.delete_table('subscription_subscription_tutorials')

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 11, 13, 22, 23, 27, 915666)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 11, 13, 22, 23, 27, 915468)'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'schedule.session': {
            'Meta': {'object_name': 'Session'},
            'audience_level': ('django.db.models.fields.CharField', [], {'max_length': '12'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'slug': ('django.db.models.fields.SlugField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'db_index': 'True', 'blank': 'True'}),
            'speakers': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'proposed'", 'max_length': '10'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'track': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['schedule.Track']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        },
        'schedule.track': {
            'Meta': {'object_name': 'Track'},
            'description_en_us': ('django.db.models.fields.CharField', [], {'max_length': '2000'}),
            'description_pt_br': ('django.db.models.fields.CharField', [], {'max_length': '2000', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name_en_us': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'name_pt_br': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'db_index': 'True', 'blank': 'True'})
        },
        'subscription.subscription': {
            'Meta': {'object_name': 'Subscription'},
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'pending'", 'max_length': '20'}),
            'tutorials': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['schedule.Session']", 'symmetrical': 'False'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'subscription.transaction': {
            'Meta': {'object_name': 'Transaction'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'price': ('django.db.models.fields.DecimalField', [], {'max_digits': '5', 'decimal_places': '2'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'subscription': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['subscription.Subscription']"})
        }
    }

    complete_apps = ['subscription']

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
import requests

from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext
from lxml import etree

from pythonbrasil8.schedule.models import Session

PRICES = {
    "Student": 150,
    "APyB Associated": 150,
    "Speaker": 150,
    "Individual": 250,
    "Corporate": 350
}


class Subscription(models.Model):

    TYPE = (
        ("tutorial", "tutorial",),
        ("talk", "talk"),
    )

    STATUSES = (
        ("confirmed", "Confirmed"),
        ("canceled", "Canceled"),
        ("pending", "Pending"),
        ("sponsor", "Sponsor"),
    )

    date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User)
    type = models.CharField(max_length=25, choices=TYPE)
    status = models.CharField(max_length=20, choices=STATUSES, default="pending")
    tutorials = models.ManyToManyField(Session, blank=True)

    def done(self):
        return self.status == "confirmed" or self.status == "sponsor"


class Transaction(models.Model):
    subscription = models.ForeignKey("Subscription")
    code = models.CharField(max_length=50)
    status = models.CharField(max_length=25)
    price = models.DecimalField(max_digits=5, decimal_places=2)

    def get_checkout_url(self):
        return settings.PAGSEGURO_WEBCHECKOUT + self.code

    @staticmethod
    def generate(subscription):
        if subscription.type == "talk":
            return _generate_talk_transaction(subscription)
        return _generate_tutorial_transaction(subscription)


def _generate_transaction(subscription, price, description):
    headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
    payload = settings.PAGSEGURO
    payload["itemAmount1"] = "%.2f" % price
    payload["itemDescription1"] = description
    payload["reference"] = "%d" % subscription.pk
    response = requests.post(settings.PAGSEGURO_CHECKOUT, data=payload, headers=headers)
    if response.ok:
        dom = etree.fromstring(response.content)
        transaction_code = dom.xpath("//code")[0].text
        transaction = Transaction.objects.create(
            subscription=subscription,
            code=transaction_code,
            status="pending",
            price=price
        )
        return transaction
    return Transaction.objects.none()


def _generate_talk_transaction(subscription):
    profile = subscription.user.get_profile()
    price = PRICES[profile.type]
    description = ugettext(u"Payment of a %s Ticket in PythonBrasil[8] conference, 2012 edition") % ugettext(profile.type)
    return _generate_transaction(subscription, price, description)


def _generate_tutorial_transaction(subscription):
    tutorials = subscription.tutorials.all()
    if not tutorials:
        raise ValueError("No tutorials selected.")
    _prices = [35, 65, 90, 100]
    price = _prices[len(tutorials)-1]
    description = u"Payment of tutorials ticket in PythonBrasil[8] conference."
    return _generate_transaction(subscription, price, description)

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib import admin as django_admin
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.urlresolvers import reverse, NoReverseMatch
from django.db import models as django_models
from django.http import HttpResponseRedirect
from django.template import response
from django.test import TestCase
from django.test.client import RequestFactory

from pythonbrasil8.dashboard import models as dash_models
from pythonbrasil8.schedule import models as sched_models
from pythonbrasil8.subscription import admin, models, views
from pythonbrasil8.subscription.models import Subscription, Transaction, PRICES
from pythonbrasil8.subscription.views import SubscriptionView, NotificationView


class SubscriptionModelTestCase(TestCase):

    def setUp(self):
        self.user = User.objects.create(username="Wolverine")

    def test_name_url(self):
        try:
            reverse('talk-subscription')
        except NoReverseMatch:
            self.fail("Reversal of url named 'talk-subscription' failed with NoReverseMatch")

    def test_should_have_type(self):
        self.assert_field_in('type', Subscription)

    def test_type_should_be_CharField(self):
        type_field = Subscription._meta.get_field_by_name('type')[0]
        self.assertIsInstance(type_field, django_models.CharField)

    def test_type_should_have_choices(self):
        type_field = Subscription._meta.get_field_by_name('type')[0]
        choices = [choice[0] for choice in type_field._choices]
        self.assertIn('talk', choices)
        self.assertIn('tutorial', choices)

    def test_should_have_user(self):
        self.assert_field_in('user', Subscription)

    def test_user_should_be_a_foreign_key(self):
        user_field = Subscription._meta.get_field_by_name('user')[0]
        self.assertIsInstance(user_field, django_models.ForeignKey)
        self.assertEqual(User, user_field.related.parent_model)

    def test_should_have_date(self):
        self.assert_field_in('date', Subscription)

    def test_date_should_be_datetime_field(self):
        date_field = Subscription._meta.get_field_by_name('date')[0]
        self.assertIsInstance(date_field, django_models.DateTimeField)
        self.assertTrue(date_field.auto_now_add)

    def test_should_have_status(self):
        self.assert_field_in('status', Subscription)

    def test_status_should_be_CharField(self):
        status_field = Subscription._meta.get_field_by_name('status')[0]
        self.assertIsInstance(status_field, django_models.CharField)

    def test_status_should_have_at_most_20_characters(self):
        status_field = Subscription._meta.get_field_by_name('status')[0]
        self.assertEqual(20, status_field.max_length)

    def test_status_should_have_choices(self):
        status_field = Subscription._meta.get_field_by_name('status')[0]
        self.assertEqual(Subscription.STATUSES, status_field.choices)

    def test_status_should_be_pending_by_default(self):
        status_field = Subscription._meta.get_field_by_name('status')[0]
        self.assertEqual('pending', status_field.default)

    def test_should_have_tutorials(self):
        self.assert_field_in('tutorials', Subscription)

    def test_tutorials_should_be_ManyToManyField(self):
        tutorials_field = Subscription._meta.get_field_by_name('tutorials')[0]
        self.assertIsInstance(tutorials_field, django_models.ManyToManyField)

    def test_tutorials_should_point_to_subscription(self):
        tutorials_field = Subscription._meta.get_field_by_name('tutorials')[0]
        self.assertEqual(sched_models.Session, tutorials_field.related.parent_model)

    def test_tutorial_should_accept_blank(self):
        tutorials_field = Subscription._meta.get_field_by_name('tutorials')[0]
        self.assertTrue(tutorials_field.blank)

    def assert_field_in(self, field_name, model):
        self.assertIn(field_name, model._meta.get_all_field_names())


class TransactionModelTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        call_command("loaddata", "tutorials.json", verbosity=0)

    @classmethod
    def tearDownClass(cls):
        call_command("flush", interactive=False, verbosity=0)

    def setUp(self):
        self.user = User.objects.get(pk=1)
        self.request = RequestFactory().get("/", {})
        self.request.user = self.user

        self.requests_original = models.requests

        class ResponseMock(object):
            content = "<code>xpto123</code>"

            def ok(self):
                return True

        def post(self, *args, **kwargs):
            return ResponseMock()

        models.requests.post = post

    def tearDown(self):
        views.requests = self.requests_original
        Subscription.objects.all().delete()

    def test_should_have_code(self):
        self.assert_field_in('code', Transaction)

    def test_should_have_status(self):
        self.assert_field_in('status', Transaction)

    def test_should_have_subscription(self):
        self.assert_field_in('subscription', Transaction)

        subscription_field = Transaction._meta.get_field_by_name('subscription')[0]
        self.assertIsInstance(subscription_field, django_models.ForeignKey)
        self.assertEqual(Subscription, subscription_field.related.parent_model)

    def test_get_checkout_url(self):
        t = Transaction(code="123")
        expected_url = settings.PAGSEGURO_WEBCHECKOUT + "123"
        self.assertEqual(expected_url, t.get_checkout_url())

    def assert_field_in(self, field_name, model):
        self.assertIn(field_name, model._meta.get_all_field_names())

    def test_generate_talk_transaction(self):
        subscription = Subscription.objects.create(
            type='talk',
            user=self.user,
        )
        transaction = Transaction.generate(subscription)
        self.assertEqual(subscription, transaction.subscription)
        self.assertEqual("xpto123", transaction.code)

    def test_generate_tutorial_transaction(self):
        subscription = Subscription.objects.create(
            type="tutorial",
            user=self.user,
        )
        subscription.tutorials.add(sched_models.Session.objects.get(pk=1))
        transaction = Transaction.generate(subscription)
        self.assertEqual(subscription, transaction.subscription)
        self.assertEqual("xpto123", transaction.code)
        self.assertEqual(35, transaction.price)

    def test_generate_tutorial_transaction_raises_ValueError_when_no_tutorial_is_selected(self):
        subscription = Subscription.objects.create(
            type='tutorial',
            user=self.user,
        )
        with self.assertRaises(ValueError) as cm:
            Transaction.generate(subscription)
        exc = cm.exception
        self.assertEqual("No tutorials selected.", exc.args[0])


class SubscriptionViewTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        call_command("loaddata", "profiles.json", verbosity=0)

    @classmethod
    def tearDownClass(cls):
        call_command("flush", interactive=False, verbosity=0)

    def setUp(self):
        self.user = User.objects.get(pk=1)
        self.request = RequestFactory().get("/", {})
        self.request.user = self.user

        self.requests_original = views.requests

        class ResponseMock(object):
            content = "<code>xpto123</code>"

            def ok(self):
                return True

        def post(self, *args, **kwargs):
            return ResponseMock()

        views.requests.post = post

    def tearDown(self):
        views.requests = self.requests_original
        Subscription.objects.all().delete()

    def test_subscription_view_should_redirect_to_dashboard_if_it_fails_to_create_the_transaction(self):
        class ResponseMock(object):
            content = None

            @property
            def ok(self):
                return False

        requests_original = views.requests
        try:
            views.requests.post = lambda self, *args, **kwargs: ResponseMock()
            request = RequestFactory().get("/", {})
            request.user = User.objects.get(pk=1)
            v = SubscriptionView()
            v._notify_staff = lambda u: None
            response = v.dispatch(request)
            self.assertFalse(Subscription.objects.filter(user__pk=1).exists())
            self.assertEqual(302, response.status_code)
            self.assertEqual("/dashboard/", response["Location"])
        finally:
            views.requests = requests_original

    def test_subscription_view_should_create_a_subscription_for_the_current_user_and_redirect_to_payment_gateway(self):
        response = SubscriptionView.as_view()(self.request)
        self.assertTrue(Subscription.objects.filter(user=self.user).exists())
        self.assertEqual(302, response.status_code)
        expected_url = settings.PAGSEGURO_WEBCHECKOUT + "xpto123"
        self.assertEqual(expected_url, response["Location"])

    def test_subscription_view_should_create_a_subscription_for_the_user_type(self):
        SubscriptionView.as_view()(self.request)
        transaction = Transaction.objects.get(subscription__user=self.user)
        self.assertEqual(transaction.price, PRICES["Student"])

    def test_should_returns_error_when_user_is_not_logged(self):
        self.request.user.is_authenticated = lambda: False
        response = SubscriptionView.as_view()(self.request)
        self.assertEqual(302, response.status_code)
        self.assertIn('/accounts/login/', response.items()[1][1])

    def test_should_redirect_to_the_profile_url_if_the_user_does_not_have_a_profile(self):
        request = RequestFactory().get("/dashboard/subscription/talk/")
        request.user = User.objects.get(pk=2)
        response = SubscriptionView.as_view()(request)
        self.assertIsInstance(response, HttpResponseRedirect)
        base_url = reverse("edit-profile")
        expected_url = "%s?next=%s" % (base_url, request.path)
        self.assertEqual(expected_url, response["Location"])

    def test_should_redirect_to_the_profile_url_if_the_profile_does_not_contain_a_name(self):
        request = RequestFactory().get("/")
        request.user = User.objects.get(pk=3)
        response = SubscriptionView.as_view()(request)
        self.assertIsInstance(response, HttpResponseRedirect)
        base_url = reverse("edit-profile")
        expected_url = "%s?next=%s" % (base_url, request.path)
        self.assertEqual(expected_url, response["Location"])


class NotificationViewTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        call_command("loaddata", "profiles.json", verbosity=0)

    @classmethod
    def tearDownClass(cls):
        call_command("flush", interactive=False, verbosity=0)

    def setUp(self):
        self.user = User.objects.get(pk=1)
        self.requests_original = views.requests

        class ResponseMock(object):
            content = "<xml><status>3</status><reference>3</reference></xml>"

            def ok(self):
                return True

        def get(self, *args, **kwargs):
            return ResponseMock()

        views.requests.get = get

    def tearDown(self):
        views.requests = self.requests_original

    def test_name_url(self):
        try:
            reverse('notification')
        except NoReverseMatch:
            self.fail("Reversal of url named 'notification' failed with NoReverseMatch")

    def test_transaction_should_get_info_about_transaction(self):
        status, ref = NotificationView().transaction("code")
        self.assertEqual(3, status)
        self.assertEqual(3, ref)

    def test_transaction_done(self):
        subscription = Subscription.objects.create(
            user=self.user,
            type="talk",
            status="pending",
        )
        transaction = Transaction.objects.create(
            subscription=subscription,
            status="pending",
            code="xpto",
            price="123.54"
        )
        NotificationView().transaction_done(subscription.id)
        transaction = Transaction.objects.select_related("subscription").get(id=transaction.id)
        self.assertEqual("done", transaction.status)
        self.assertEqual("confirmed", transaction.subscription.status)

    def test_transaction_canceled(self):
        subscription = Subscription.objects.create(
            user=self.user,
            type="talk",
        )
        transaction = Transaction.objects.create(
            subscription=subscription,
            status="pending",
            code="xpto",
            price="115.84"
        )
        NotificationView().transaction_canceled(subscription.id)
        transaction = Transaction.objects.get(id=transaction.id)
        self.assertEqual("canceled", transaction.status)

    def test_methods_by_status(self):
        methods_by_status = NotificationView().methods_by_status
        self.assertEqual("transaction_done", methods_by_status[3].__name__)
        self.assertEqual("transaction_canceled", methods_by_status[7].__name__)

    def test_post(self):
        subscription = Subscription.objects.create(
            user=self.user,
            type="talk",
        )
        transaction = Transaction.objects.create(
            subscription=subscription,
            status="pending",
            code="xpto",
            price=123.45
        )
        notification_view = NotificationView()
        notification_view.transaction = (lambda code: (3, 1))
        request = RequestFactory().post("/", {"notificationCode": "123"})

        response = notification_view.post(request)

        transaction = Transaction.objects.get(id=transaction.id)
        self.assertEqual("done", transaction.status)
        self.assertEqual("OK", response.content)


class PricesTestCase(TestCase):

    def test_prices(self):
        expected = {
            'Student': 150,
            'APyB Associated': 150,
            'Speaker': 150,
            'Individual': 250,
            'Corporate': 350
        }
        self.assertEqual(expected, PRICES)


class SubscriptionAdminTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        call_command("loaddata", "profiles.json", verbosity=0)
        cls.factory = RequestFactory()

    @classmethod
    def tearDownClass(cls):
        call_command("flush", interactive=False, verbosity=0)

    def test_name(self):
        profile = dash_models.AccountProfile.objects.get(user=1)
        sub = models.Subscription(user=User.objects.get(pk=1))
        self.assertEqual(profile.name, admin.name(sub))

    def test_name_short_description(self):
        self.assertEqual(u"Name", admin.name.short_description)

    def test_name_function_is_in_list_display(self):
        self.assertIn(admin.name, admin.SubscriptionAdmin.list_display)

    def test_status_is_in_list_display(self):
        self.assertIn("status", admin.SubscriptionAdmin.list_display)

    def test_subscription_model_is_registered_with_subscription_admin(self):
        self.assertIn(models.Subscription, django_admin.site._registry)
        self.assertIsInstance(django_admin.site._registry[models.Subscription], admin.SubscriptionAdmin)

    def test_user__username_should_be_in_search_fields(self):
        self.assertIn("user__username", admin.SubscriptionAdmin.search_fields)

    def test_user__email_should_be_in_search_fields(self):
        self.assertIn("user__email", admin.SubscriptionAdmin.search_fields)


class TutorialSubscriptionViewTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        call_command("loaddata", "tutorials.json", verbosity=0)

    @classmethod
    def tearDownClass(cls):
        call_command("flush", interactive=False, verbosity=0)

    def setUp(self):
        self.user = User.objects.get(pk=1)
        self.request = RequestFactory().get("/", {})
        self.request.user = self.user

        self.requests_original = views.requests

        class ResponseMock(object):
            content = "<code>xpto123</code>"

            def ok(self):
                return True

        def post(self, *args, **kwargs):
            return ResponseMock()

        views.requests.post = post

    def tearDown(self):
        views.requests = self.requests_original
        Subscription.objects.all().delete()

    def test_get_renders_template(self):
        v = views.TutorialSubscriptionView()
        resp = v.get(self.request)
        self.assertIsInstance(resp, response.TemplateResponse)
        self.assertEqual("subscription/tutorials.html", resp.template_name)

    def test_get_should_include_accepted_tutorials_in_context_excluding_subscribed_tutorials(self):
        v = views.TutorialSubscriptionView()
        resp = v.get(self.request)
        tutorials = resp.context_data["tutorials"]
        expected = [
            views.TutorialSlot(
                tutorials=sched_models.Session.objects.filter(pk__in=[1, 5])
            ),
        ]
        self.assertEqual(len(expected), len(tutorials))
        for i, slot in enumerate(tutorials):
            self.assertEqual(list(expected[i].tutorials), list(slot.tutorials))
        self.assertFalse(resp.context_data["confirmed"])

    def test_get_should_include_subscripted_tutorials_in_context(self):
        v = views.TutorialSubscriptionView()
        resp = v.get(self.request)
        tutorials = resp.context_data["subscribed"]
        self.assertEqual(list(tutorials), [sched_models.Session.objects.get(pk=6)])

    def test_get_should_detect_if_the_user_already_have_talk_subscription(self):
        v = views.TutorialSubscriptionView()
        request = RequestFactory().get("/")
        request.user = User.objects.get(pk=2)
        resp = v.get(request)
        self.assertTrue(resp.context_data["confirmed"])

    def _prepare_post(self, user=3):
        data = {}
        tutorials = sched_models.Session.objects.filter(pk__in=[5, 7])
        for tutorial in tutorials:
            data[tutorial.date.strftime("tutorial-%Y%m%d%H%M%S")] = tutorial.pk
        request = RequestFactory().post("/", data)
        request.user = User.objects.get(pk=user)
        return tutorials, request

    def test_post_renders_template_with_information_about_the_transaction_and_the_subscription(self):
        tutorials, request = self._prepare_post()
        v = views.TutorialSubscriptionView()
        resp = v.post(request)
        subscription = Subscription.objects.get(user_id=3)
        transaction = subscription.transaction_set.get(price=65)
        self.assertIsInstance(resp, response.TemplateResponse)
        self.assertEqual("subscription/tutorials_success.html", resp.template_name)
        self.assertEqual(transaction, resp.context_data["transaction"])
        self.assertEqual(subscription, resp.context_data["subscription"])

    def test_post_creates_subscription_and_transaction(self):
        tutorials, request = self._prepare_post()
        v = views.TutorialSubscriptionView()
        v.post(request)
        subscription = Subscription.objects.get(user_id=3)
        self.assertEqual("tutorial", subscription.type)
        self.assertEqual("pending", subscription.status)
        self.assertEqual(list(tutorials), list(subscription.tutorials.all()))
        transaction = subscription.transaction_set.all()[0]
        self.assertEqual(65, transaction.price)
        self.assertEqual("xpto123", transaction.code)
        self.assertEqual("pending", transaction.status)

    def test_post_with_user_confirmed_for_the_conference(self):
        tutorials, request = self._prepare_post(user=2)
        v = views.TutorialSubscriptionView()
        resp = v.post(request)
        subscription = Subscription.objects.get(user_id=2, type="tutorial")
        self.assertEqual("subscription/tutorials_confirmed.html", resp.template_name)
        self.assertEqual(subscription, resp.context_data["subscription"])
        self.assertEqual("confirmed", subscription.status)
        self.assertFalse(subscription.transaction_set.exists())

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
import datetime
import re

import requests

from django.conf import settings
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse
from django.template import response
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from lxml import etree

from pythonbrasil8.core import mail
from pythonbrasil8.core.views import LoginRequiredMixin
from pythonbrasil8.dashboard.models import AccountProfile
from pythonbrasil8.schedule.models import Session
from pythonbrasil8.subscription.models import Subscription, Transaction


class SubscriptionView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        profile = AccountProfile.objects.filter(user=request.user)
        if not profile or not profile[0].name:
            msg = ugettext("In order to issue your registration to the conference, you need to complete your profile.")
            messages.error(request, msg, fail_silently=True)
            url = "%s?next=%s" % (reverse("edit-profile"), request.path)
            return HttpResponseRedirect(url)
        subscription = Subscription.objects.create(
            type='talk',
            user=request.user,
        )
        t = Transaction.generate(subscription)

        if not t:
            self._notify_staff(request.user)
            subscription.delete()
            url = "/dashboard/"
            messages.error(request, ugettext("Failed to generate a transaction within the payment gateway. Please contact the event staff to complete your registration."), fail_silently=True)
        else:
            url = settings.PAGSEGURO_WEBCHECKOUT + t.code
        return HttpResponseRedirect(url)

    def _notify_staff(self, user):
        msg = u"There was a failure in the communication with PagSeguro, the user %(email)s could not be registered."
        kw = {"email": user.email}
        body = msg % kw
        mail.send(settings.EMAIL_HOST_USER, ["organizers@python.org.br"], "PagSeguro Communication Failure", body)


class TutorialSubscriptionView(LoginRequiredMixin, View):

    def get(self, request):
        subscriptions = Subscription.objects.\
                filter(user=request.user, status="confirmed", type="tutorial").\
                prefetch_related("tutorials")
        subscribed = []
        if subscriptions:
            subscribed = subscriptions[0].tutorials.all()
        tutorials = Session.objects.\
                filter(type="tutorial", status__in=["accepted", "confirmed"]).\
                exclude(date__in=[t.date for t in subscribed]).\
                order_by("date")
        slots = []
        current_slot = None
        for tutorial in tutorials:
            if current_slot is None:
                current_slot = TutorialSlot([tutorial])
            elif tutorial.date == current_slot.date:
                current_slot.tutorials.append(tutorial)
            else:
                slots.append(current_slot)
                current_slot = TutorialSlot([tutorial])
        if current_slot:
            slots.append(current_slot)
        return response.TemplateResponse(
            request,
            "subscription/tutorials.html",
            context={
                "tutorials": slots,
                "subscribed": subscribed,
                "confirmed": request.user.subscription_set.filter(type="talk", status__in=("confirmed", "sponsor")).exists(),
            },
        )

    def post(self, request):
        tutorials = []
        regexp = re.compile(r"tutorial-(\d{14})")
        for k, v in request.POST.iteritems():
            m = regexp.match(k)
            if m:
                tutorial = Session.objects.get(
                    pk=v,
                    date=datetime.datetime.strptime(m.groups()[0], "%Y%m%d%H%M%S"),
                    type="tutorial",
                )
                tutorials.append(tutorial)
        status = "pending"
        if request.user.subscription_set.filter(type="talk", status__in=("confirmed", "sponsor")).exists():
            status = "confirmed"
        subscription = Subscription.objects.create(
            user=request.user,
            type="tutorial",
            status=status,
        )
        subscription.tutorials = tutorials
        subscription.save()
        if status == "confirmed":
            return response.TemplateResponse(
                request,
                "subscription/tutorials_confirmed.html",
                context={"subscription": subscription},
            )
        transaction = Transaction.generate(subscription)
        return response.TemplateResponse(
            request,
            "subscription/tutorials_success.html",
            context={
                "transaction": transaction,
                "subscription": subscription,
            },
        )


class TutorialSlot(object):

    def __init__(self, tutorials):
        self.date = tutorials[0].date
        self.tutorials = tutorials


class NotificationView(View):

    def __init__(self, *args, **kwargs):
        self.methods_by_status = {
            3: self.transaction_done,
            4: self.transaction_done,
            7: self.transaction_canceled,
        }
        return super(NotificationView, self).__init__(*args, **kwargs)

    def transaction(self, transaction_code):
        url_transacao = "%s/%s?email=%s&token=%s" % (settings.PAGSEGURO_TRANSACTIONS,
                                                     transaction_code,
                                                     settings.PAGSEGURO["email"],
                                                     settings.PAGSEGURO["token"])
        url_notificacao = "%s/%s?email=%s&token=%s" % (settings.PAGSEGURO_TRANSACTIONS_NOTIFICATIONS, transaction_code, settings.PAGSEGURO["email"], settings.PAGSEGURO["token"])

        response = requests.get(url_transacao)
        if not response.ok:
            response = requests.get(url_notificacao)
        if response.ok:
            dom = etree.fromstring(response.content)
            status_transacao = int(dom.xpath("//status")[0].text)
            referencia = int(dom.xpath("//reference")[0].text)
            return status_transacao, referencia
        return None, None

    def transaction_done(self, subscription_id):
        transaction = Transaction.objects.select_related('subscription').get(subscription_id=subscription_id)
        transaction.status = "done"
        transaction.save()
        transaction.subscription.status = 'confirmed'
        transaction.subscription.save()
        context = {"profile": AccountProfile.objects.get(user=transaction.subscription.user),
  }
        body = render_to_string("email_successful_registration.txt", context)
        subject = "PythonBrasil[8] - Registration Confirmation"
        mail.send(settings.EMAIL_SENDER,
                  [transaction.subscription.user.email],
                  subject,
                  body)

    def transaction_canceled(self, subscription_id):
        transaction = Transaction.objects.get(subscription_id=subscription_id)
        transaction.status = "canceled"
        transaction.save()
        context = {"profile": AccountProfile.objects.get(user=transaction.subscription.user)}
        body = render_to_string("email_unsuccessful_registration.txt", context)
        subject = "PythonBrasil[8] - Registration Unsuccessful "
        mail.send(settings.EMAIL_SENDER,
                  [transaction.subscription.user.email],
                  subject,
                  body)

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(NotificationView, self).dispatch(*args, **kwargs)

    def post(self, request):
        notification_code = request.POST.get("notificationCode")

        if notification_code:
            status, subscription_id = self.transaction(notification_code)
            method = self.methods_by_status.get(status)

            if method:
                method(subscription_id)

        return HttpResponse("OK")

########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-
from django.conf import settings
from django.conf.urls import patterns, url, include
from django.contrib import admin
from django.contrib.auth.views import password_reset, password_reset_confirm
from django.views.generic import TemplateView
from registration.forms import RegistrationForm

from pythonbrasil8.subscription.views import NotificationView

from core.views import (Home, AboutView, SponsorsInfoView, VenueView,
                        CustomSponsorsView, SponsorsJobsView)

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', Home.as_view(), name='home'),
    url(r'^sponsors/info/$', SponsorsInfoView.as_view(), name='sponsors-info'),
    url(r'^previous-editions/$', TemplateView.as_view(template_name="previous_editions.html"), name='previous-editions'),
    url(r'^badges/$', TemplateView.as_view(template_name="badges.html"), name='badges'),
    url(r'^register/$', TemplateView.as_view(template_name="register.html"), name='register'),
    url(r'^sponsors/$', CustomSponsorsView.as_view(), name='custom-sponsors'),
    url(r'^sponsors/jobs/$', SponsorsJobsView.as_view(), name='sponsors-jobs'),

    url(r'^schedule/$', 'pythonbrasil8.schedule.views.schedule', name='schedule'),
    url(r'^schedule/vote/?$', 'pythonbrasil8.schedule.views.vote_page',
        name='vote_page'),
    url(r'^schedule/(?P<track_slug>[^/]+)/?$',
        'pythonbrasil8.schedule.views.track_page', name='track-page'),
    url(r'^schedule/(?P<track_slug>[^/]+)/(?P<proposal_slug>.*)/?$',
        'pythonbrasil8.schedule.views.proposal_page', name='proposal-page'),

    url(r'about/$', AboutView.as_view(), name='about'),
    url(r'^venue/$', VenueView.as_view(), name='venue'),
    url(r'^media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),

    url(r'^notification/$', NotificationView.as_view(), name='notification'),

    url(r'^dashboard/', include('pythonbrasil8.dashboard.urls')),

    url(r'^accounts/login/$', 'django.contrib.auth.views.login', {'extra_context': {'registration_form': RegistrationForm()}}, name='auth_login'),
    url(r'^accounts/logout/$', 'django.contrib.auth.views.logout', {"next_page": "/"}, name='auth_logout'),
    url(r'^accounts/password/reset/$', password_reset, {'email_template_name': 'email_password_reset.txt', 'subject_template_name': 'email_password_reset_title.txt', 'template_name': 'password_reset.html'}, name='password_reset'),
    url(r'^accounts/password/reset/done/$', TemplateView.as_view(template_name="password_reset_sent.html"), name='password_reset_sent'),
    url(r'^accounts/password/reset/confirm/(?P<uidb36>[0-9A-Za-z]{1,13})-(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$', password_reset_confirm, {"template_name": "password_reset_confirm.html"}, name='password_reset_confirm'),
    url(r'^accounts/', include('registration.backends.default.urls')),

    url(r'^news/', include('pythonbrasil8.news.urls', namespace='news')),
    url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for pythonbrasil8 project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.

"""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pythonbrasil8.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
