__FILENAME__ = admin
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from longerusername.forms import UserCreationForm, UserChangeForm

class LongerUserNameUserAdmin(UserAdmin):
    add_form = UserCreationForm
    form = UserChangeForm

admin.site.unregister(User)
admin.site.register(User, LongerUserNameUserAdmin)

########NEW FILE########
__FILENAME__ = forms
from django.utils.translation import ugettext as _
from django.core.validators import MaxLengthValidator
from django.contrib.auth import forms as auth_forms
from django import forms

from longerusername import MAX_USERNAME_LENGTH

def update_username_field(field):
    field.widget.attrs['maxlength'] = MAX_USERNAME_LENGTH()
    field.max_length = MAX_USERNAME_LENGTH()
    field.help_text = _("Required, %s characters or fewer. Only letters, "
                        "numbers, and characters such as @.+_- are "
                        "allowed." % MAX_USERNAME_LENGTH())

    # we need to find the MaxLengthValidator and change its
    # limit_value otherwise the auth forms will fail validation
    for v in field.validators:
        if isinstance(v, MaxLengthValidator):
            v.limit_value = MAX_USERNAME_LENGTH()

class UserCreationForm(auth_forms.UserCreationForm):
    def __init__(self, *args, **kwargs):
        super(UserCreationForm, self).__init__(*args, **kwargs)
        update_username_field(self.fields['username'])

class UserChangeForm(auth_forms.UserChangeForm):
    def __init__(self, *args, **kwargs):
        super(UserChangeForm, self).__init__(*args, **kwargs)
        update_username_field(self.fields['username'])

class AuthenticationForm(auth_forms.AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super(AuthenticationForm, self).__init__(*args, **kwargs)
        update_username_field(self.fields['username'])

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
from south.db import db
from south.v2 import SchemaMigration
from django.db import models
from longerusername import MAX_USERNAME_LENGTH

class Migration(SchemaMigration):

    def forwards(self, orm):
        # Changing field 'User.username'
        db.alter_column('auth_user', 'username', models.CharField(max_length=MAX_USERNAME_LENGTH()))


    def backwards(self, orm):

        # Changing field 'User.username'
        db.alter_column('auth_user', 'username', models.CharField(max_length=35))


    models = {
        
    }

    complete_apps = ['django_monkeypatches']

########NEW FILE########
__FILENAME__ = models
import django
from django.core.validators import MaxLengthValidator
from django.utils.translation import ugettext as _
from django.db.models.signals import class_prepared
from django.conf import settings
from longerusername import MAX_USERNAME_LENGTH

def longer_username_signal(sender, *args, **kwargs):
    if (sender.__name__ == "User" and
        sender.__module__ == "django.contrib.auth.models"):
        patch_user_model(sender)
class_prepared.connect(longer_username_signal)

def patch_user_model(model):
    field = model._meta.get_field("username")

    field.max_length = MAX_USERNAME_LENGTH()
    field.help_text = _("Required, %s characters or fewer. Only letters, "
                        "numbers, and @, ., +, -, or _ "
                        "characters." % MAX_USERNAME_LENGTH())

    # patch model field validator because validator doesn't change if we change
    # max_length
    for v in field.validators:
        if isinstance(v, MaxLengthValidator):
            v.limit_value = MAX_USERNAME_LENGTH()

from django.contrib.auth.models import User

# https://github.com/GoodCloud/django-longer-username/issues/1
# django 1.3.X loads User model before class_prepared signal is connected
# so we patch model after it's prepared

# check if User model is patched
if User._meta.get_field("username").max_length != MAX_USERNAME_LENGTH():
    patch_user_model(User)
########NEW FILE########
__FILENAME__ = tests
from django.contrib.auth.models import User
from django.test import TestCase

class LongerUsernameTests(TestCase):
    """
    Unit tests for longerusername app
    """
    def setUp(self):
        """
        creates a user with a terribly long username
        """
        long_username = ''.join([str(i) for i  in range(100)])
        self.user = User.objects.create_user('test' + long_username, 'test@test.com', 'testpassword')
    def testUserCreation(self):
        """
        tests that self.user was successfully saved, and can be retrieved
        """
        self.assertNotEqual(self.user,None)
        User.objects.get(id=self.user.id) # returns DoesNotExist error if the user wasn't created
########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
