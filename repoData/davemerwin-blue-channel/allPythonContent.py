__FILENAME__ = admin
from django.contrib import admin
from bluechannel.blog.models import Post

class PostAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title',)}
    save_on_top = True
    list_display = ('title', 'status', 'summary', 'author', 'updated_at')
    list_filter = ('status', 'author', 'category',)
    search_fields = ('title', 'main_content', 'summary')

admin.site.register(Post, PostAdmin)
########NEW FILE########
__FILENAME__ = models
from datetime import datetime
from tagging.fields import TagField
from django.db import models
from django.contrib.auth.models import User
from bluechannel.media.models import Media
from bluechannel.categories.models import Category
from django.utils.translation import ugettext_lazy as _

# Published Event Manager
class PublishedPostManager(models.Manager):
    def get_query_set(self):
        return super(PublishedPostManager, self).get_query_set().filter(status='publish')

class Post(models.Model):
    """
    The post model for blogs
    """
    ENTRY_STATUS = (
        ('draft', 'Draft'),
        ('remove', 'Remove'),
        ('publish', 'Publish')
    )
    title = models.CharField(max_length=200)
    slug = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=ENTRY_STATUS)
    main_content = models.TextField(blank=True)
    category = models.ForeignKey(Category, blank=True, null=True)
    media = models.ManyToManyField(Media, blank=True)
    summary = models.TextField(blank=True)
    publish = models.DateTimeField(_('publish'), default=datetime.now)
    created_at = models.DateTimeField(_('created at'), default=datetime.now)
    updated_at = models.DateTimeField(_('updated at'))
    author = models.ForeignKey(User)
    similar_entries = models.ManyToManyField('self', blank=True, related_name='similar')
    enable_comments = models.BooleanField(default=False)
    close_comments = models.BooleanField(default=False)
    tags = TagField()
    
    objects = models.Manager() # The default manager.
    published_objects = PublishedPostManager() # Only published posts

    def save(self, force_insert=False, force_update=False):
        self.updated_at = datetime.now()
        super(Post, self).save(force_insert, force_update)

    def __unicode__(self):
        return self.title
        
    def get_absolute_url(self):
        return "/blog/%s/%s/" % (self.created_at.strftime("%Y/%b/%d").lower(), self.slug)
        
    def get_month(self):
        return "/blog/%s/" % (self.created_at.strftime("%Y/%b").lower())
        
    class Meta:
        verbose_name = ('Post')
        verbose_name_plural = ('Posts')
        

########NEW FILE########
__FILENAME__ = blog_tags
from django import template
from bluechannel.blog.models import Post

register = template.Library()

@register.inclusion_tag('itags/blog_recent_list.html')
def recent_entries_list():
    """Recent Blog Entries"""
    recent_list = Post.objects.order_by('-created_at')[:5]
    return {'recent_list': recent_list}
    
@register.inclusion_tag('itags/blog_archive_list.html')
def show_archive_blog():
    archive_list = Post.objects.all()
    return {'archive_list': archive_list}

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from bluechannel.blog.models import Post

list_dict = {
    'queryset': Post.objects.filter(status='publish'),
    'date_field': 'created_at',
    'paginate_by': 25,
}

latest_dict = {
    'queryset': Post.objects.filter(status='publish'),
    'date_field': 'created_at',
}

detail_dict = {
    'queryset': Post.objects.filter(status='publish'),
    'date_field': 'created_at',
}

urlpatterns = patterns('django.views.generic.date_based',
   url(r'^(?P<year>\d{4})/(?P<month>[a-z]{3})/(?P<day>\w{1,2})/(?P<slug>[-\w]+)/$', 'object_detail', detail_dict, name="detail"),
   url(r'^(?P<year>\d{4})/(?P<month>[a-z]{3})/(?P<day>\w{1,2})/$', 'archive_day',   list_dict, name="day-archive"),
   url(r'^(?P<year>\d{4})/(?P<month>[a-z]{3})/$', 'archive_month', list_dict, name="month-archive"),
   url(r'^(?P<year>\d{4})/$', 'archive_year',  list_dict, name="year-archive"),
   url(r'^$', 'archive_index', latest_dict, name="latest"),
)

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from bluechannel.categories.models import Category

class CategoryAdmin(admin.ModelAdmin):
    pass

admin.site.register(Category, CategoryAdmin)
########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.
class Category(models.Model):
    name = models.CharField(max_length=100)
    desription = models.TextField(blank=True)
    parent = models.ForeignKey('self', blank=True, null=True, related_name='child')
    slug = models.CharField(max_length=100)
    
    def __unicode__(self):
        return self.name
        
    class Meta:
        verbose_name = ('Category')
        verbose_name_plural = ('Categories')

    def get_absolute_url(self):
        parents = self.get_all_parents()
        return '/%s/' % ('/'.join([p.slug for p in parents]))
        
    def get_all_parents(self):
        "Gets all parents going up the parent tree until a page with no parent, including itself."
        parents = []
        category = self
        while True:
            parents.insert(0, page)
            category = category.parent
            if not category:
                break
        return parents

    def get_children(self):
        "Gets children of current category, no grandchildren."
        return Category.objects.filter(parent=self.id)

    def get_all_siblings(self):
        "Gets siblings of current category only, no children of siblings."
        return Category.objects.filter(parent=self.category)
        #return "/%i/" % (self.slug)
########NEW FILE########
__FILENAME__ = category_tags
from django import template
from bluechannel.categories.models import Category

register = template.Library()
    
@register.inclusion_tag('itags/category_list.html')
def show_categories():
    category_list = Category.objects.all()
    return {'category_list': category_list}
########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from bluechannel.customers.models import Customer

class CustomerAdmin(admin.ModelAdmin):
    list_display = ('user', 'approved', 'created_at','updated_at',)
    list_filter = ('approved',)
    pass

admin.site.register(Customer, CustomerAdmin)
########NEW FILE########
__FILENAME__ = models
from django.forms import ModelForm
from django.db import models
from django.contrib.auth.models import User
from bluechannel.media.models import Media
from django.utils.translation import ugettext_lazy as _
from datetime import datetime

# Create your models here.
class Customer(models.Model):
    user = models.ForeignKey(User, unique=True)
    approved = models.BooleanField(default=False)
    organization = models.CharField(blank=True, max_length=255)
    phone = models.CharField(max_length=15)
    mobile = models.CharField(blank=True, max_length=15)
    fax = models.CharField(blank=True, max_length=15)
    address_1 = models.CharField(max_length=255)
    address_2 = models.CharField(blank=True, max_length=100)
    city = models.CharField(max_length=200)
    state = models.CharField(max_length=100)
    postal_code = models.IntegerField()
    created_at = models.DateTimeField(_('created at'), default=datetime.now)
    updated_at = models.DateTimeField(_('updated at'), blank=True)

    def get_absolute_url(self):
        return ('profiles_profile_detail', (), { 'username': self.user.username })
    get_absolute_url = models.permalink(get_absolute_url)
    
    def save(self, force_insert=False, force_update=False):
        self.updated_at = datetime.now()
        super(Customer, self).save(force_insert, force_update)
    
    def __str__(self):
        return self.user.username
        
class CustomerForm(ModelForm):
    class Meta:
        model = Customer
        exclude=('user', 'approved', 'created_at', 'updated_at',)
        

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^$', 'customers.views.subscribe', name='subscribe'),
)

########NEW FILE########
__FILENAME__ = views
from django.forms import ModelForm
from django.shortcuts import render_to_response
from bluechannel.customers.models import CustomerForm
from django.template import Context, Template, RequestContext
from django.http import Http404, HttpResponseRedirect
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

# see docs for how to grab the template view. Pretty straight forward

def subscribe(request):
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.user = request.user
            customer.save()
            
            # Send an email to teh admin letting them know that a person registered
            subject = render_to_string('subscribe/email_subject.txt',)
            message = render_to_string('subscribe/email.txt', {
                    'user': request.user,
                })
            recipients = ['dave.merwin@gmail.com']
            # recipients = ['johnsonlm@wou.edu']
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipients)
            
            return HttpResponseRedirect('/thanks/')
    else:
        form = CustomerForm()
        
    return render_to_response('subscribe/customer.html', {'form':form}, context_instance=RequestContext(request))

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from bluechannel.demo.models import Step, Demo

class StepAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    save_on_top = True
    pass

admin.site.register(Step, StepAdmin)

class DemoAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    save_on_top = True
    pass

admin.site.register(Demo, DemoAdmin)
########NEW FILE########
__FILENAME__ = models
from datetime import datetime
from tagging.fields import TagField
from django.db import models
from django.contrib.auth.models import User
from bluechannel.page.models import Page

# Create your models here.
class Step(models.Model):
    """Individual Piece of the Demo"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    page = models.ForeignKey(Page)
    order = models.IntegerField(blank=True, null=True)
    slug = models.CharField(max_length=100)
    
    def __unicode__(self):
        return self.name
        
    def get_absolute_url(self):
        return "/%s/" % self.slug
    
class Demo(models.Model):
    """The Complete Demo"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    steps = models.ManyToManyField(Step)
    slug = models.CharField(max_length=100)
    
    def __unicode__(self):
        return self.name
        
    def get_absolute_url(self):
        return "/%s/" % self.slug

# class ModuleOrder(models.Model):
#    """(ModuleOrder description)"""
########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
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
__FILENAME__ = admin
from django.contrib import admin
from bluechannel.media.models import Type, Media


class TypeAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    save_on_top = True

admin.site.register(Type, TypeAdmin)

class MediaAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    save_on_top = True
    list_filter = ('media_type',)
    list_display = ('name', 'media_type', 'title_text', 'author',)

admin.site.register(Media, MediaAdmin)
########NEW FILE########
__FILENAME__ = models
from datetime import datetime
from django.db import models
from tagging.fields import TagField
from django.utils.translation import ugettext_lazy as _

class Type(models.Model):
    name = models.CharField(max_length=200)
    slug = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(_('created at'), default=datetime.now)
    updated_at = models.DateTimeField(_('updated at'))

    class Meta:
        verbose_name_plural = ('Type')

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return "/media-type/%i/" % (self.slug)
        
    def save(self, force_insert=False, force_update=False):
        self.updated_at = datetime.now()
        super(Type, self).save(force_insert, force_update)
        

class Media(models.Model):
    name = models.CharField(max_length=250)
    slug = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    media_type = models.ForeignKey(Type, blank=True, null=True)
    media_file = models.FileField(upload_to='%Y/%m/%d/', max_length=255, blank=True)
    media_embed = models.TextField(blank=True, help_text="Place your EMBED code here from YouTube, Flickr or others.")
    title_text = models.CharField(blank=True, max_length=100)
    alt_text = models.CharField(blank=True, max_length=100)
    caption = models.CharField(blank=True, max_length=200)
    author = models.CharField(blank=True, max_length=100)
    liscense_type = models.CharField(blank=True, max_length=100)
    liscense_url = models.URLField(blank=True, verify_exists=True)
    created_at = models.DateTimeField(_('created at'), default=datetime.now)
    updated_at = models.DateTimeField(_('updated at'))
    display = models.BooleanField(default=True)
    tags = TagField()
    
    class Meta:
        verbose_name_plural = ('Media')

    def __unicode__(self):
        return self.name

    def save(self, force_insert=False, force_update=False):
        self.updated_at = datetime.now()
        super(Media, self).save(force_insert, force_update)
    
    def get_absolute_url(self):
        return self.get_media_file_url()
        
    def _save_FIELD_file(self, field, filename, raw_contents, save=True):
        original_upload_to = field.upload_to
        field.upload_to = '%s/%s' % (self.media_type, field.upload_to)
        super(Media, self)._save_FIELD_file(field, filename, raw_contents, save)
        field.upload_to = original_upload_to
########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = admin
from django import forms
from django.contrib import admin
from bluechannel.page.models import Highlight, Type, Event, Template, Page

class HighlightAdmin(admin.ModelAdmin):
    save_on_top = True
    pass

admin.site.register(Highlight, HighlightAdmin)

class TypeAdmin(admin.ModelAdmin):
    save_on_top = True
    pass
    
admin.site.register(Type, TypeAdmin)

class EventAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    save_on_top = True
    list_display = ('name','event_start_date')
    search_fields = ('name','description')
    pass

admin.site.register(Event, EventAdmin)

class TemplateAdmin(admin.ModelAdmin):
    save_on_top = True
    list_display = ('name', 'description')

admin.site.register(Template, TemplateAdmin)

class TemplateModelChoiceField(forms.ModelChoiceField):
    """Based on ModelChoiceField, but using a radio button widget"""
    widget = forms.RadioSelect

class PageAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title',)}
    save_on_top = True
    list_display = ('title', 'page_title', 'page_type', 'status', 'summary', 'author', 'updated_at', 'in_nav', 'parent')
    list_filter = ('status', 'in_nav', 'page_type')
    search_fields = ('title', 'page_title', 'summary', 'main_content')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "template":
            kwargs['form_class'] = TemplateModelChoiceField
            return db_field.formfield(**kwargs)
        return super(PageAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

admin.site.register(Page, PageAdmin)

########NEW FILE########
__FILENAME__ = models
from datetime import datetime
from tagging.fields import TagField
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from bluechannel.media.models import Media

STATUS = (
    ('draft', 'Draft'),
    ('remove', 'Remove'),
    ('publish', 'Publish')
)

class Highlight(models.Model):
    """
    A piece of content that is included via Page.
    """
    name = models.CharField(max_length=200)
    content = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS)
    created_at = models.DateTimeField(_('created at'), default=datetime.now)
    updated_at = models.DateTimeField(_('updated at'), blank=True)
    tags = TagField()
    
    def __unicode__(self):
        return self.name
    
    class Meta:
        verbose_name = ('Highlight')
        verbose_name_plural = ('Highlights')
    
    def save(self, force_insert=False, force_update=False):
        self.updated_at = datetime.now()
        super(Highlight, self).save(force_insert, force_update)
        
class Type(models.Model):
    """
    What Type it?
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(_('created at'), default=datetime.now)
    updated_at = models.DateTimeField(_('updated at'), blank=True)
    
    class Meta:
        verbose_name = ('Type')
        verbose_name_plural = ('Type')
    
    def __str__(self):
        return self.name
        
    def save(self, force_insert=False, force_update=False):
        self.updated_at = datetime.now()
        super(Type, self).save(force_insert, force_update)
        
class Event(models.Model):
    """The events module"""
    name = models.CharField(blank=True, max_length=200)
    event_start_date = models.DateField(blank=True)
    event_start_time = models.TimeField(blank=True)
    event_end_date = models.DateField(blank=True)
    event_end_time = models.TimeField(blank=True)
    description = models.TextField('Content', blank=True)
    summary = models.TextField(blank=True)
    created_at = models.DateTimeField(_('created at'), default=datetime.now)
    updated_at = models.DateTimeField(_('updated at'), blank=True)
    slug = models.CharField(max_length=100)
    tags = TagField()
    enable_comments = models.BooleanField(default=True)
    
    def __unicode__(self):
        return self.name
        
    def save(self, force_insert=False, force_update=False):
        self.updated_at = datetime.now()
        super(Event, self).save(force_insert, force_update)

class Template(models.Model):
    """A template model with sample template image"""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='template_images', max_length=200, blank=True)

    def __unicode__(self):
        return self.name

# Published Page Manager
class PublishedPageManager(models.Manager):
    def get_query_set(self):
        return super(PublishedPageManager, self).get_query_set().filter(status='publish')

class Page(models.Model):
    """
    The central Page model.  This correlates directly with the URL such that
    the URL `/about/` would be Page.objects.get(slug='about').  Pages can be
    nested heirarchically.
    """

    title = models.CharField(max_length=200)
    page_title = models.CharField(blank=True, max_length=200, help_text=("Use the Page Title if you want the Title of the page to be different than the Title. For Example... Title: About. Page Title: About Our Company."))
    slug = models.CharField(max_length=100)
    template = models.ForeignKey(Template, blank=True, null=True)
    page_type = models.ForeignKey(Type)
    parent = models.ForeignKey('self', blank=True, null=True, related_name='child')
    status = models.CharField(max_length=20, choices=STATUS)
    main_content = models.TextField(blank=True)
    summary = models.TextField(blank=True)
    hilight = models.ManyToManyField(Highlight, blank=True, related_name='hilight')
    event = models.ManyToManyField(Event, blank=True)
    media = models.ManyToManyField(Media, blank=True)
    created_at = models.DateTimeField(_('created at'), default=datetime.now)
    updated_at = models.DateTimeField(_('updated at'), blank=True)
    author = models.ForeignKey(User)
    similar_pages = models.ManyToManyField('self', blank=True, related_name='similar')
    enable_comments = models.BooleanField(default=False)
    order = models.IntegerField(blank=True, null=True)
    in_nav = models.BooleanField(default=False, help_text=("Does this page represent a top level link for the site? Do you want it avalable from the Nav Bar?"))
    is_home = models.BooleanField(default=False, blank=True, help_text=("Is this the site's homepage?"))
    in_site_map = models.BooleanField(default=True)
    has_next = models.BooleanField(default=False, help_text=("Does this page have a next page?"))
    tags = TagField()
    objects = models.Manager() # The default manager.
    published_objects = PublishedPageManager() # Only published pages

    def save(self, force_insert=False, force_update=False):
        self.updated_at = datetime.now()
        super(Page, self).save(force_insert, force_update)

    def __unicode__(self):
        return self.title

    def get_absolute_url(self):
        parents = self.get_all_parents()
        return '/%s/' % ('/'.join([p.slug for p in parents]))

    def get_all_parents(self):
        "Gets all parents going up the parent tree until a page with no parent, including itself."
        parents = []
        page = self
        while True:
            parents.insert(0, page)
            page = page.parent
            if not page:
                break
        return parents

    def get_children(self):
        "Gets children of current page, no grandchildren."
        return Page.published_objects.filter(parent=self.id)

    def get_all_siblings(self):
        "Gets siblings of current page only, no children of siblings."
        return Page.published_objects.filter(parent=self.parent)
        #return "/%i/" % (self.slug)

########NEW FILE########
__FILENAME__ = page_tags
from django import template
from bluechannel.page.models import Page, Highlight

register = template.Library()

@register.tag
def get_breadcrumb(parser, token):
	"""
	Get all parents of a given page going up the parent chain.	If given a
	context variable, this will put the list of pages in that variable, 
	otherwise they'll be placed in a context variable named `breadcrumb`.
	
	Template::
	
		{% get_breadcrumb for page_object_name [as varname] %}
		
	Example with no variable::
	
		{% get_breadcrumb for page %}
		{% for page in breadcrumb %}
			# ...
		{% endfor %}
	
	Example with variable
	
		{% get_breadcrumb for object as page_list %}
		{% for page in page_list %}
			# ...
		{% endfor %}
	
	"""
	bits = token.contents.split()
	len_bits = len(bits)
	if len_bits not in (3, 5):
		raise template.TemplateSyntaxError('%s tag requires either two or four arguments') % bits[0]
	if bits[1] != 'for':
		raise template.TemplateSyntaxError("First argument to %s tag must be 'for'") % bits[0]
	if len_bits > 3 and bits[3] != 'as':
		raise template.TemplateSyntaxError("Third argument to %s tag must be 'as'") % bits[0]

	page_obj_name = bits[2]
	context_var = 'breadcrumb'
	if len_bits == 5:
		context_var = bits[4]
	
	return BreadcrumbNode(page_obj_name, context_var)

class BreadcrumbNode(template.Node):
	def __init__(self, page_obj_name, context_var):
		self.page_obj_name = template.Variable(page_obj_name)
		self.context_var = context_var
	
	def render(self, context):
		try:
			page = self.page_obj_name.resolve(context)
		except template.VariableDoesNotExist:
			return ''
		
		page_list = page.get_all_parents()
		context[self.context_var] = page_list
		return ''

		from bluechannel.highlight.models import *
		from bluechannel.event.models import *
		from bluechannel.asset.models import *
		from django import template

		register = template.Library()

@register.inclusion_tag('itags/page_list.html')
def show_page_list():
	"""
	For creating a nav list
	"""
	page_list = Page.objects.filter(in_nav=1).order_by('order')
	return {'page_list': page_list}
	
@register.inclusion_tag('itags/about_blurb.html')
def about_blurb():
	"""
	For creating a nav list
	"""
	about_blub = Highlight.objects.filter(tags='about-blurb')
	return {'about_blurb': about_blurb}
	
@register.inclusion_tag('itags/page_list_accessible.html')
def show_page_list_accessible():
	"""
	For creating a nav list
	"""
	page_list = Page.objects.filter(in_nav=1).order_by('order')
	return {'page_list': page_list}

@register.inclusion_tag('itags/random_testimonial.html')
def show_random_testimonial():
	"""
	For generating a single piece of content from content tagged testimonial
	"""
	random_testimonial = Highlight.objects.filter(tags='testimonial')
	if random_testimonial != '':
		return {'random_testimonial': random_testimonial}
	else:
		return 'Nothing Here'

@register.inclusion_tag('itags/home_detail.html')
def show_home_detail():
	"""
	For generating a single piece of content from pages
	"""
	home_detail = Page.objects.filter(is_home=1)
    
	if home_detail != '':
	    return {'home_detail': home_detail}
	else:
	    return ''

@register.inclusion_tag('itags/events_list.html')
def show_events_list():
	"""
	For showing pages tagged with events
	"""
	events_list = Page.objects.filter(tags='events').order_by('-created')
	return {'events_list': events_list}
	
@register.inclusion_tag('itags/blog_list.html')
def show_blog_list():
	"""
	For showing pages tagged with events
	"""
	blog_list = Page.objects.filter(page_type=3).order_by('-created')[:4]
	return {'blog_list': blog_list}

@register.inclusion_tag('itags/news_list.html')
def show_news_list():
	"""
	For showing pages tagged with events
	"""
	news_list = Page.objects.filter(tags='news').order_by('-created')
	return {'news_list': news_list}
	
@register.inclusion_tag('itags/did_you_know.html')
def get_did_you_know():
	"""
	For showing content tagged with dyk (did you know)
	"""
	did_you_know = Highlight.objects.filter(tags='dyk').order_by('?')
	if did_you_know != '':
		return {'did_you_know': did_you_know}
	else:
		return ''

@register.inclusion_tag('itags/sub_menu.html')
def get_submenu():
	"""
	Show Siblings of the current page and all children
	"""	
	siblings = Page.get_all_siblings()
	#children = Page.objects.filter(parent=self.id)
	return {'siblings': siblings}
########NEW FILE########
__FILENAME__ = urls_event
from django.conf.urls.defaults import *
from django.views.generic.list_detail import object_detail, object_list
from bluechannel.page.models import Event

event_dict = {
    'queryset': Event.objects.order_by('name'),
    'paginate_by': 25,
}

event_detail = {
    'queryset': Event.objects.all(),
}

urlpatterns = patterns('',
    
    # For the events
    (r'(?P<slug>[-\w]+)/$', object_detail, dict(event_detail, slug_field='slug')),
    (r'^$', object_list, event_dict),

)
########NEW FILE########
__FILENAME__ = views
from django.db import models
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.views.generic.list_detail import object_list, object_detail

Page = models.get_model('page', 'page')

# see docs for how to grab the template view. Pretty straight forward

def page_list(request): #For now lists ALL pages
    page_list = Page.objects.all()
    return object_list(request, queryset=page_list) # the name is the class to generic view to return with the query set
    
def published_page(request, slug):
    slug_field=slug
    published_page = Page.objects.filter(status='Publish')
    return object_detail(request, slug=slug_field, queryset=published_page)

def detail(request, slug):
    page = get_object_or_404(Page, slug=slug)
    template = page.template or 'page/page_detail.html'
    return render_to_response(
        template,
        {'object': page},
        context_instance=RequestContext(request)
    )
    
def home(request):
    try:
        home = Page.published_objects.get(is_home=True)
    except Page.DoesNotExist:
        home = None
    
    return render_to_response(
        'page/homepage.html',
        {'home': home,},
        context_instance=RequestContext(request)
    )

########NEW FILE########
__FILENAME__ = settings
import os

PROJECT_PATH = os.path.abspath(os.path.dirname(__file__))

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'sqlite3'     # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = '%s/db' % PROJECT_PATH   # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
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

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(PROJECT_PATH, 'media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/zippitydoodah/'

# Make this unique, and don't share it with anybody.
# SECRET_KEY = ''

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

ROOT_URLCONF = 'bluechannel.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.comments',
    'django.contrib.formtools',
    'django.contrib.humanize',
    'django.contrib.markup',
    'django.contrib.redirects',
    'django.contrib.sitemaps',
    'django.contrib.syndication',
    
    # External Apps
    # From Blue Channel http://github.com/davemerwin/blue-channel/tree/master
    'bluechannel.media',
    'bluechannel.customers',
    'bluechannel.page',
    'bluechannel.blog',
    'bluechannel.demo',
    'bluechannel.categories',
    
    
    #External Apps
    'tagging',
)


# For local development setting overrides
try:
    from local_settings import *
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = urls
from django.conf import settings
from django.conf.urls.defaults import *

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^bluechannel/', include('bluechannel.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^admin/(.*)', admin.site.root),
)

if settings.DEBUG:
    urlpatterns += patterns('', 
        (r'^media/(.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),
    )

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from account.models import Account, OtherServiceInfo

admin.site.register(Account)
admin.site.register(OtherServiceInfo)

########NEW FILE########
__FILENAME__ = context_processors
def openid(request):
    return {'openid': request.openid}
########NEW FILE########
__FILENAME__ = forms

import re

from django import forms
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.translation import ugettext_lazy as _, ugettext
from django.utils.encoding import smart_unicode

from core.utils import get_send_mail
send_mail = get_send_mail()

from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User

from emailconfirmation.models import EmailAddress
# from friends.models import JoinInvitation
from account.models import Account

from timezones.forms import TimeZoneField

alnum_re = re.compile(r'^\w+$')

class LoginForm(forms.Form):

    username = forms.CharField(label=_("Username"), max_length=30, widget=forms.TextInput())
    password = forms.CharField(label=_("Password"), widget=forms.PasswordInput(render_value=False))
    remember = forms.BooleanField(label=_("Remember Me"), help_text=_("If checked you will stay logged in for 3 weeks"), required=False)

    user = None

    def clean(self):
        if self._errors:
            return
        user = authenticate(username=self.cleaned_data["username"], password=self.cleaned_data["password"])
        if user:
            if user.is_active:
                self.user = user
            else:
                raise forms.ValdidationError(_("This account is currently inactive."))
        else:
            raise forms.ValidationError(_("The username and/or password you specified are not correct."))
        return self.cleaned_data

    def login(self, request):
        if self.is_valid():
            login(request, self.user)
            request.user.message_set.create(message=ugettext(u"Successfully logged in as %(username)s.") % {'username': self.user.username})
            if self.cleaned_data['remember']:
                request.session.set_expiry(60 * 60 * 24 * 7 * 3)
            else:
                request.session.set_expiry(0)
            return True
        return False


class SignupForm(forms.Form):

    username = forms.CharField(label=_("Username"), max_length=30, widget=forms.TextInput())
    password1 = forms.CharField(label=_("Password"), widget=forms.PasswordInput(render_value=False))
    password2 = forms.CharField(label=_("Password (again)"), widget=forms.PasswordInput(render_value=False))
    email = forms.EmailField(label=_("Email (optional)"), required=False, widget=forms.TextInput())
    confirmation_key = forms.CharField(max_length=40, required=False, widget=forms.HiddenInput())

    def clean_username(self):
        if not alnum_re.search(self.cleaned_data["username"]):
            raise forms.ValidationError(_("Usernames can only contain letters, numbers and underscores."))
        try:
            user = User.objects.get(username__iexact=self.cleaned_data["username"])
        except User.DoesNotExist:
            return self.cleaned_data["username"]
        raise forms.ValidationError(_("This username is already taken. Please choose another."))

    def clean(self):
        if "password1" in self.cleaned_data and "password2" in self.cleaned_data:
            if self.cleaned_data["password1"] != self.cleaned_data["password2"]:
                raise forms.ValidationError(_("You must type the same password each time."))
        return self.cleaned_data

    def save(self):
        username = self.cleaned_data["username"]
        email = self.cleaned_data["email"]
        password = self.cleaned_data["password1"]
        if self.cleaned_data["confirmation_key"]:
            try:
                join_invitation = JoinInvitation.objects.get(confirmation_key = self.cleaned_data["confirmation_key"])
                confirmed = True
            except JoinInvitation.DoesNotExist:
                confirmed = False
        else:
            confirmed = False

        # @@@ clean up some of the repetition below -- DRY!

        if confirmed:
            if email == join_invitation.contact.email:
                new_user = User.objects.create_user(username, email, password)
                join_invitation.accept(new_user) # should go before creation of EmailAddress below
                new_user.message_set.create(message=ugettext(u"Your email address has already been verified"))
                # already verified so can just create
                EmailAddress(user=new_user, email=email, verified=True, primary=True).save()
            else:
                new_user = User.objects.create_user(username, "", password)
                join_invitation.accept(new_user) # should go before creation of EmailAddress below
                if email:
                    new_user.message_set.create(message=ugettext(u"Confirmation email sent to %(email)s") % {'email': email})
                    EmailAddress.objects.add_email(new_user, email)
            return username, password # required for authenticate()
        else:
            new_user = User.objects.create_user(username, "", password)
            if email:
                new_user.message_set.create(message=ugettext(u"Confirmation email sent to %(email)s") % {'email': email})
                EmailAddress.objects.add_email(new_user, email)
            return username, password # required for authenticate()


class UserForm(forms.Form):

    def __init__(self, user=None, *args, **kwargs):
        self.user = user
        super(UserForm, self).__init__(*args, **kwargs)

class AccountForm(UserForm):

    def __init__(self, *args, **kwargs):
        super(AccountForm, self).__init__(*args, **kwargs)
        try:
            self.account = Account.objects.get(user=self.user)
        except Account.DoesNotExist:
            self.account = Account(user=self.user)


class AddEmailForm(UserForm):

    email = forms.EmailField(label=_("Email"), required=True, widget=forms.TextInput(attrs={'size':'30'}))

    def clean_email(self):
        try:
            EmailAddress.objects.get(user=self.user, email=self.cleaned_data["email"])
        except EmailAddress.DoesNotExist:
            return self.cleaned_data["email"]
        raise forms.ValidationError(_("This email address already associated with this account."))

    def save(self):
        self.user.message_set.create(message=ugettext(u"Confirmation email sent to %(email)s") % {'email': self.cleaned_data["email"]})
        return EmailAddress.objects.add_email(self.user, self.cleaned_data["email"])


class ChangePasswordForm(UserForm):

    oldpassword = forms.CharField(label=_("Current Password"), widget=forms.PasswordInput(render_value=False))
    password1 = forms.CharField(label=_("New Password"), widget=forms.PasswordInput(render_value=False))
    password2 = forms.CharField(label=_("New Password (again)"), widget=forms.PasswordInput(render_value=False))

    def clean_oldpassword(self):
        if not self.user.check_password(self.cleaned_data.get("oldpassword")):
            raise forms.ValidationError(_("Please type your current password."))
        return self.cleaned_data["oldpassword"]

    def clean_password2(self):
        if "password1" in self.cleaned_data and "password2" in self.cleaned_data:
            if self.cleaned_data["password1"] != self.cleaned_data["password2"]:
                raise forms.ValidationError(_("You must type the same password each time."))
        return self.cleaned_data["password2"]

    def save(self):
        self.user.set_password(self.cleaned_data['password1'])
        self.user.save()
        self.user.message_set.create(message=ugettext(u"Password successfully changed."))


class ResetPasswordForm(forms.Form):

    email = forms.EmailField(label=_("Email"), required=True, widget=forms.TextInput(attrs={'size':'30'}))

    def clean_email(self):
        if EmailAddress.objects.filter(email__iexact=self.cleaned_data["email"], verified=True).count() == 0:
            raise forms.ValidationError(_("Email address not verified for any user account"))
        return self.cleaned_data["email"]

    def save(self):
        for user in User.objects.filter(email__iexact=self.cleaned_data["email"]):
            new_password = User.objects.make_random_password()
            user.set_password(new_password)
            user.save()
            subject = _("Password reset")
            message = render_to_string("account/password_reset_message.txt", {
                "user": user,
                "new_password": new_password,
            })
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], priority="high")
        return self.cleaned_data["email"]

class ChangeTimezoneForm(AccountForm):

    timezone = TimeZoneField(label=_("Timezone"), required=True)

    def __init__(self, *args, **kwargs):
        super(ChangeTimezoneForm, self).__init__(*args, **kwargs)
        self.initial.update({"timezone": self.account.timezone})

    def save(self):
        self.account.timezone = self.cleaned_data["timezone"]
        self.account.save()
        self.user.message_set.create(message=ugettext(u"Timezone successfully updated."))

class ChangeLanguageForm(AccountForm):

    language = forms.ChoiceField(label=_("Language"), required=True, choices=settings.LANGUAGES)

    def __init__(self, *args, **kwargs):
        super(ChangeLanguageForm, self).__init__(*args, **kwargs)
        self.initial.update({"language": self.account.language})

    def save(self):
        self.account.language = self.cleaned_data["language"]
        self.account.save()
        self.user.message_set.create(message=ugettext(u"Language successfully updated."))


# @@@ these should somehow be moved out of account or at least out of this module

from account.models import OtherServiceInfo, other_service, update_other_services

class TwitterForm(UserForm):
    username = forms.CharField(label=_("Username"), required=True)
    password = forms.CharField(label=_("Password"), required=True,
                               widget=forms.PasswordInput(render_value=False))

    def __init__(self, *args, **kwargs):
        super(TwitterForm, self).__init__(*args, **kwargs)
        self.initial.update({"username": other_service(self.user, "twitter_user")})

    def save(self):
        from zwitschern.utils import get_twitter_password
        update_other_services(self.user,
            twitter_user = self.cleaned_data['username'],
            twitter_password = get_twitter_password(settings.SECRET_KEY, self.cleaned_data['password']),
        )
        self.user.message_set.create(message=ugettext(u"Successfully authenticated."))

class PownceForm(UserForm):
    usernamep = forms.CharField(label=_("Username"), required=True)
    passwordp = forms.CharField(label=_("Password"), required=True,
                               widget=forms.PasswordInput(render_value=False))
                               
    def __init__(self, *args, **kwargs):
        super(PownceForm, self).__init__(*args, **kwargs)
        self.initial.update({"usernamep": other_service(self.user, "pownce_user")})
        
    def save(self):
        from zwitschern.pownce_utils import get_pownce_password
        update_other_service(self.user,
            pownce_user = self.cleaned_data['usernamep'],
            pownce_password = get_pownce_password(settings.SECRET_KEY, self.cleaned_data['passwordp']),
        )
        self.user.message_set.create(message=ugettext(u"Successfully authenticated."))

########NEW FILE########
__FILENAME__ = create_accounts_from_profiles
from django.core.management.base import NoArgsCommand, CommandError
from django.contrib.auth.models import User
from django.conf import settings
from account.models import Account, OtherServiceInfo

class Command(NoArgsCommand):
    help = 'Create an account object for users which do not have one and copy over info from profile.'
    
    def handle_noargs(self, **options):
        try:
            from profiles.models import Profile
        except ImportError:
            raise CommandError("The profile app could not be imported.")
        
        for user in User.objects.all():
            profile = Profile.objects.get(user=user)
            account, created = Account.objects.get_or_create(user=user)
            
            if created:
                account.timezone = profile.timezone
                account.language = account.language
                account.save()
                print "created account for %s" % user
            
            if profile.blogrss:
                info, created = OtherServiceInfo.objects.get_or_create(user=user, key="blogrss")
                info.value = profile.blogrss
                info.save()
                print "copied over blogrss for %s" % user
            if profile.twitter_user:
                info, created = OtherServiceInfo.objects.get_or_create(user=user, key="twitter_user")
                info.value = profile.twitter_user
                info.save()
                print "copied over twitter_user for %s" % user
            if profile.twitter_password:
                info, created = OtherServiceInfo.objects.get_or_create(user=user, key="twitter_password")
                info.value = profile.twitter_password
                info.save()
                print "copied over twitter_password for %s" % user
            if profile.pownce_user:
                info, created = OtherServiceInfo.objects.get_or_create(user=user, key="pownce_user")
                info.value = profile.pownce_user
                info.save()
                print "copied over pownce_user for %s" % user
            if profile.pownce_password:
                info, created = OtherServiceInfo.objects.get_or_create(user=user, key="pownce_password")
                info.value = profile.pownce_password
                info.save()
                print "copied over pownce_password for %s" % user

########NEW FILE########
__FILENAME__ = middleware
from django.utils.cache import patch_vary_headers
from django.utils import translation
from account.models import Account

class LocaleMiddleware(object):
    """
    This is a very simple middleware that parses a request
    and decides what translation object to install in the current
    thread context depending on the user's account. This allows pages
    to be dynamically translated to the language the user desires
    (if the language is available, of course). 
    """

    def get_language_for_user(self, request):
        if request.user.is_authenticated():
            try:
                account = Account.objects.get(user=request.user)
                return account.language
            except (Account.DoesNotExist, Account.MultipleObjectsReturned):
                pass
        return translation.get_language_from_request(request)

    def process_request(self, request):
        translation.activate(self.get_language_for_user(request))
        request.LANGUAGE_CODE = translation.get_language()

    def process_response(self, request, response):
        patch_vary_headers(response, ('Accept-Language',))
        response['Content-Language'] = translation.get_language()
        translation.deactivate()
        return response

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.utils.translation import ugettext_lazy as _

from timezones.fields import TimeZoneField

class Account(models.Model):
    
    user = models.ForeignKey(User, unique=True, verbose_name=_('user'))
    
    timezone = TimeZoneField(_('timezone'))
    language = models.CharField(_('language'), max_length=10, choices=settings.LANGUAGES, default=settings.LANGUAGE_CODE)
    
    def __unicode__(self):
        return self.user.username


class OtherServiceInfo(models.Model):
    
    # eg blogrss, twitter_user, twitter_password, pownce_user, pownce_password
    
    user = models.ForeignKey(User, verbose_name=_('user'))
    key = models.CharField(_('Other Service Info Key'), max_length=50)
    value = models.TextField(_('Other Service Info Value'))
    
    class Meta:
        unique_together = [('user', 'key')]
    
    def __unicode__(self):
        return u"%s for %s" % (self.key, self.user)

def other_service(user, key, default_value=""):
    """
    retrieve the other service info for given key for the given user.
    
    return default_value ("") if no value.
    """
    try:
        value = OtherServiceInfo.objects.get(user=user, key=key).value
    except OtherServiceInfo.DoesNotExist:
        value = default_value
    return value

def update_other_services(user, **kwargs):
    """
    update the other service info for the given user using the given keyword args.
    
    e.g. update_other_services(user, twitter_user=..., twitter_password=...)
    """
    for key, value in kwargs.items():
        info, created = OtherServiceInfo.objects.get_or_create(user=user, key=key)
        info.value = value
        info.save()

def create_account(sender, instance=None, **kwargs):
    if instance is None:
        return
    account, created = Account.objects.get_or_create(user=instance)

post_save.connect(create_account, sender=User)

########NEW FILE########
__FILENAME__ = openid_urls
from django.conf.urls.defaults import *
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django_openidauth.regviews import register

def if_not_user_url(request):
    return HttpResponseRedirect(reverse('acct_login'))

def restrict_signup(func):
    def _inner(request, *args, **kwargs):
        if not request.openid:
            return HttpResponseRedirect(reverse('acct_login'))
        return register(request, *args, **kwargs)
    return _inner

urlpatterns = patterns('',
    url(r'^signup/$', restrict_signup(register), {
        'success_url': '/account/email/',
        'template_name': 'openid/signup.html',
        'already_registered_url': '/openid/associations/',
    }, name="openid_signup"),
    url(r'^login/$', 'django_openidconsumer.views.begin', {
        'sreg': 'email,nickname',
        'redirect_to': '/openid/complete/',
        'if_not_user_url': if_not_user_url,
    }, name="openid_login"),
    url(r'^complete/$', 'django_openidauth.views.complete', {
        'on_login_ok_url'    : '/',
        'on_login_failed_url': '/openid/signup/'
    }, name="openid_complete"),
    url(r'^logout/$', 'django_openidconsumer.views.signout', name="openid_logout"),
    url(r'^associations/$', 'django_openidauth.views.associations', {
        'template_name': 'openid/associations.html',
    }, name="openid_assoc"),
)
########NEW FILE########
__FILENAME__ = openid_tags
from django import template
from django_openidauth.models import UserOpenID
from django.utils.safestring import mark_safe

try:
    any
except NameError:
    def any(seq):
        for x in seq:
            if x:
                return True
        return False

register = template.Library()

def openid_icon(openid, user):
    oid = u'%s' % openid
    matches = [u.openid == oid for u in UserOpenID.objects.filter(user=user)]
    if any(matches):
        return mark_safe(u'<img src="/site_media/openid-icon.png" alt="Logged in with OpenID" />')
    else:
        return u''
register.simple_tag(openid_icon)

########NEW FILE########
__FILENAME__ = other_service_tags
import re

from django import template
from account.models import other_service

register = template.Library()

class OtherServiceNode(template.Node):
    def __init__(self, user, key, asvar):
        self.user = user
        self.key = key
        self.asvar = asvar
    
    def render(self, context):
        user = self.user.resolve(context)
        key = self.key
        value = other_service(user, key)
                    
        if self.asvar:
            context[self.asvar] = value
            return ''
        else:
            return value


@register.tag(name='other_service')
def other_service_tag(parser, token):
    bits = token.split_contents()
    if len(bits) == 3: # {% other_service user key %}
        user = parser.compile_filter(bits[1])
        key = bits[2]
        asvar = None
    elif len(bits) == 5: # {% other_service user key as var %}
        if bits[3] != "as":
            raise template.TemplateSyntaxError("3rd argument to %s should be 'as'" % bits[0])
        user = parser.compile_filter(bits[1])
        key = bits[2]
        asvar = bits[4]
    else:
        raise template.TemplateSyntaxError("wrong number of arguments to %s" % bits[0])
    
    return OtherServiceNode(user, key, asvar)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from account.forms import *

urlpatterns = patterns('',
    url(r'^email/$', 'account.views.email', name="acct_email"),
    url(r'^signup/$', 'account.views.signup', name="acct_signup"),
    url(r'^login/$', 'account.views.login', name="acct_login"),
    url(r'^password_change/$', 'account.views.password_change', name="acct_passwd"),
    url(r'^password_reset/$', 'account.views.password_reset', name="acct_passwd_reset"),
    url(r'^timezone/$', 'account.views.timezone_change', name="acct_timezone_change"),
    url(r'^other_services/$', 'account.views.other_services', name="acct_other_services"),
    url(r'^language/$', 'account.views.language_change', name="acct_language_change"),
    url(r'^logout/$', 'django.contrib.auth.views.logout', {"template_name": "account/logout.html"}, name="acct_logout"),
    
    url(r'^confirm_email/(\w+)/$', 'emailconfirmation.views.confirm_email', name="acct_confirm_email"),

    # ajax validation
    (r'^validate/$', 'ajax_validation.views.validate', {'form_class': SignupForm}, 'signup_form_validate'),
)

########NEW FILE########
__FILENAME__ = views

from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect
from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login
from django.template import RequestContext
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required

from forms import SignupForm, AddEmailForm, LoginForm, ChangePasswordForm, ResetPasswordForm, ChangeTimezoneForm, ChangeLanguageForm, TwitterForm, PownceForm
from emailconfirmation.models import EmailAddress, EmailConfirmation

def login(request, form_class=LoginForm, template_name="account/login.html"):
    redirect_to = request.REQUEST.get("next", reverse("what_next"))
    if request.method == "POST":
        form = form_class(request.POST)
        if form.login(request):
            return HttpResponseRedirect(redirect_to)
    else:
        form = form_class()
    return render_to_response(template_name, {
        "form": form,
    }, context_instance=RequestContext(request))

def signup(request, form_class=SignupForm,
        template_name="account/signup.html", success_url=None):
    if success_url is None:
        success_url = reverse("what_next")
    if request.method == "POST":
        form = form_class(request.POST)
        if form.is_valid():
            username, password = form.save()
            user = authenticate(username=username, password=password)
            auth_login(request, user)
            request.user.message_set.create(message=_("Successfully logged in as %(username)s.") % {'username': user.username})
            return HttpResponseRedirect(success_url)
    else:
        form = form_class()
    return render_to_response(template_name, {
        "form": form,
    }, context_instance=RequestContext(request))

def email(request, form_class=AddEmailForm,
        template_name="account/email.html"):
    if request.method == "POST" and request.user.is_authenticated():
        if request.POST["action"] == "add":
            add_email_form = form_class(request.user, request.POST)
            if add_email_form.is_valid():
                add_email_form.save()
                add_email_form = form_class() # @@@
        else:
            add_email_form = form_class()
            if request.POST["action"] == "send":
                email = request.POST["email"]
                try:
                    email_address = EmailAddress.objects.get(user=request.user, email=email)
                    request.user.message_set.create(message="Confirmation email sent to %s" % email)
                    EmailConfirmation.objects.send_confirmation(email_address)
                except EmailAddress.DoesNotExist:
                    pass
            elif request.POST["action"] == "remove":
                email = request.POST["email"]
                try:
                    email_address = EmailAddress.objects.get(user=request.user, email=email)
                    email_address.delete()
                    request.user.message_set.create(message="Removed email address %s" % email)
                except EmailAddress.DoesNotExist:
                    pass
            elif request.POST["action"] == "primary":
                email = request.POST["email"]
                email_address = EmailAddress.objects.get(user=request.user, email=email)
                email_address.set_as_primary()
    else:
        add_email_form = form_class()
    return render_to_response(template_name, {
        "add_email_form": add_email_form,
    }, context_instance=RequestContext(request))
email = login_required(email)

def password_change(request, form_class=ChangePasswordForm,
        template_name="account/password_change.html"):
    if request.method == "POST":
        password_change_form = form_class(request.user, request.POST)
        if password_change_form.is_valid():
            password_change_form.save()
            password_change_form = form_class(request.user)
    else:
        password_change_form = form_class(request.user)
    return render_to_response(template_name, {
        "password_change_form": password_change_form,
    }, context_instance=RequestContext(request))
password_change = login_required(password_change)

def password_reset(request, form_class=ResetPasswordForm,
        template_name="account/password_reset.html",
        template_name_done="account/password_reset_done.html"):
    if request.method == "POST":
        password_reset_form = form_class(request.POST)
        if password_reset_form.is_valid():
            email = password_reset_form.save()
            return render_to_response(template_name_done, {
                "email": email,
            }, context_instance=RequestContext(request))
    else:
        password_reset_form = form_class()
    
    return render_to_response(template_name, {
        "password_reset_form": password_reset_form,
    }, context_instance=RequestContext(request))

def timezone_change(request, form_class=ChangeTimezoneForm,
        template_name="account/timezone_change.html"):
    if request.method == "POST":
        form = form_class(request.user, request.POST)
        if form.is_valid():
            form.save()
    else:
        form = form_class(request.user)
    return render_to_response(template_name, {
        "form": form,
    }, context_instance=RequestContext(request))
timezone_change = login_required(timezone_change)

def language_change(request, form_class=ChangeLanguageForm,
        template_name="account/language_change.html"):
    if request.method == "POST":
        form = form_class(request.user, request.POST)
        if form.is_valid():
            form.save()
            next = request.META.get('HTTP_REFERER', None)
            return HttpResponseRedirect(next)
    else:
        form = form_class(request.user)
    return render_to_response(template_name, {
        "form": form,
    }, context_instance=RequestContext(request))
language_change = login_required(language_change)

def other_services(request, template_name="account/other_services.html"):
    from zwitschern.utils import twitter_verify_credentials
    from zwitschern.pownce_utils import pownce_verify_credentials
    twitter_form = TwitterForm(request.user)
    pownce_form = PownceForm(request.user)
    twitter_authorized = False
    pownce_authorized = False
    if request.method == "POST":
        twitter_form = TwitterForm(request.user, request.POST)

        if request.POST['actionType'] == 'saveTwitter':
            if twitter_form.is_valid():
                from zwitschern.utils import twitter_account_raw
                twitter_account = twitter_account_raw(request.POST['username'], request.POST['password'])
                twitter_authorized = twitter_verify_credentials(twitter_account)
                if not twitter_authorized:
                    request.user.message_set.create(message="Twitter authentication failed")
                else:
                    twitter_form.save()
                
        if request.POST['actionType'] == 'savePownce':
            pownce_form = PownceForm(request.user, request.POST)     
            if pownce_form.is_valid():
                from zwitschern.pownce_utils import pownce_account_raw
                pownce_account = pownce_account_raw(request.POST['usernamep'], request.POST['passwordp'])
                pownce_authorized = pownce_verify_credentials(pownce_account)
                if not pownce_authorized:
                    request.user.message_set.create(message="Pownce authentication failed")
                else:
                    pownce_form.save()
    else:
        from zwitschern.utils import twitter_account_for_user
        from zwitschern.pownce_utils import pownce_account_for_user
        twitter_account = twitter_account_for_user(request.user)
        pownce_account  = pownce_account_for_user(request.user)
        twitter_authorized = twitter_verify_credentials(twitter_account)
        pownce_authorized = pownce_verify_credentials(pownce_account)
        twitter_form = TwitterForm(request.user)
        pownce_form = PownceForm(request.user)
    return render_to_response(template_name, {
        "twitter_form": twitter_form,
        "twitter_authorized": twitter_authorized,
        "pownce_form": pownce_form,
        "pownce_authorized":pownce_authorized,
    }, context_instance=RequestContext(request))
other_services = login_required(other_services)

########NEW FILE########
__FILENAME__ = context_processors
from django.conf import settings
from zwitschern.models import Tweet 
from tribes.models import Tribe 
from django.contrib.auth.models import User 
from bookmarks.models import Bookmark
from blog.models import Post
from core.utils import inbox_count_sources

def contact_email(request):
    return {'contact_email': getattr(settings, 'CONTACT_EMAIL', '')}

def site_name(request):
    return {'site_name': getattr(settings, 'SITE_NAME', '')}

def footer(request): 
    return {
        'latest_tweets': Tweet.objects.all().order_by('-sent')[:5], 
        'latest_tribes': Tribe.objects.all().order_by('-created')[:5], 
        'latest_users': User.objects.all().order_by('-date_joined')[:9], 
        'latest_bookmarks': Bookmark.objects.all().order_by('-added')[:5],
        'latest_blogs': Post.objects.filter(status=2).order_by('-publish')[:5],
    }

def combined_inbox_count(request):
    """
    A context processor that uses other context processors defined in
    setting.COMBINED_INBOX_COUNT_SOURCES to return the combined number from
    arbitrary counter sources.
    """
    count = 0
    for func in inbox_count_sources():
        counts = func(request)
        if counts:
            for value in counts.itervalues():
                try:
                    count = count + int(value)
                except (TypeError, ValueError):
                    pass
    return {'combined_inbox_count': count,}

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = captureas_tag
from django import template

register = template.Library()

@register.tag(name='captureas')
def do_captureas(parser, token):
    try:
        tag_name, args = token.contents.split(None, 1)
    except ValueError:
        raise template.TemplateSyntaxError("'captureas' node requires a variable name.")
    nodelist = parser.parse(('endcaptureas',))
    parser.delete_first_token()
    return CaptureasNode(nodelist, args)

class CaptureasNode(template.Node):
    def __init__(self, nodelist, varname):
        self.nodelist = nodelist
        self.varname = varname

    def render(self, context):
        output = self.nodelist.render(context)
        context[self.varname] = output
        return ''

########NEW FILE########
__FILENAME__ = comments_tag
from django import template

register = template.Library()

def comments(context, obj):
    return {
        'object': obj, 
        'request': context['request'],
        'user': context['user'],
    }

register.inclusion_tag('threadedcomments/comments.html', takes_context=True)(comments)
########NEW FILE########
__FILENAME__ = in_filter
from django import template

register = template.Library()

# http://www.djangosnippets.org/snippets/379/

@register.filter
def in_list(value, arg):
    """
    Tests if value is in arg.
    """
    return value in arg

########NEW FILE########
__FILENAME__ = shorttimesince_tag
from django.template import Library
register = Library()

import datetime
import time

from django.utils.tzinfo import LocalTimezone
from django.utils.translation import ungettext, ugettext

def calculate_shorttimesince(d, now=None):
    """
    like django's built in timesince but abbreviates units
    """
    chunks = (
      (60 * 60 * 24 * 365, lambda n: ungettext('yr', 'yr', n)),
      (60 * 60 * 24 * 30, lambda n: ungettext('mn', 'mn', n)),
      (60 * 60 * 24 * 7, lambda n : ungettext('wk', 'wk', n)),
      (60 * 60 * 24, lambda n : ungettext('d', 'd', n)),
      (60 * 60, lambda n: ungettext('hr', 'hr', n)),
      (60, lambda n: ungettext('min', 'min', n))
    )
    # Convert datetime.date to datetime.datetime for comparison
    if d.__class__ is not datetime.datetime:
        d = datetime.datetime(d.year, d.month, d.day)
    if now:
        t = now.timetuple()
    else:
        t = time.localtime()
    if d.tzinfo:
        tz = LocalTimezone(d)
    else:
        tz = None
    now = datetime.datetime(t[0], t[1], t[2], t[3], t[4], t[5], tzinfo=tz)

    # ignore microsecond part of 'd' since we removed it from 'now'
    delta = now - (d - datetime.timedelta(0, 0, d.microsecond))
    since = delta.days * 24 * 60 * 60 + delta.seconds
    if since <= 0:
        # d is in the future compared to now, stop processing.
        return u'0' + ugettext('min')
    for i, (seconds, name) in enumerate(chunks):
        count = since // seconds
        if count != 0:
            break
    s = ugettext('%(number)d%(type)s') % {'number': count, 'type': name(count)}
    if i + 1 < len(chunks):
        # Now get the second item
        seconds2, name2 = chunks[i + 1]
        count2 = (since - (seconds * count)) // seconds2
        if count2 != 0:
            s += ugettext(', %(number)d%(type)s') % {'number': count2, 'type': name2(count2)}
    return s
    
def shorttimesince(value, arg=None):
    """Formats a date as the time since that date (i.e. "4 days, 6 hours")."""
    from django.utils.timesince import timesince
    if not value:
        return u''
    if arg:
        return calculate_shorttimesince(arg, value)
    return calculate_shorttimesince(value)
shorttimesince.is_safe = False

register.filter(shorttimesince)

########NEW FILE########
__FILENAME__ = svn_app_version
from django import template
from django.conf import settings
from django.core.cache import cache
from django.utils.encoding import smart_str
from os.path import abspath
from os.path import dirname as dn
from django.utils.version import get_svn_revision
from django.db.models.loading import get_app
register = template.Library()


@register.simple_tag
def svn_app_version(appname=None, fail_silently=bool(not settings.DEBUG)):
    """
    foo.app {% svn_app_version "foo.app" %}
    project {% svn_app_version %}
    """
    cname = 'svn_app_version'
    if appname: cname += '.' + appname
    version = cache.get(cname)
    if not version:
        if not appname:
            ## RED_FLAG: hard coded relative root!
            version = get_svn_revision(dn(dn(dn(abspath(__file__)))))
        elif appname == 'django':
            version = get_svn_revision()
        elif appname not in settings.INSTALLED_APPS:
            version = 'SVN-None'
        else:
            try:
                module = get_app(appname)
            except:
                if not fail_silently: raise
                version = 'SVN-Error'
            else:
                version = get_svn_revision(dn(abspath(module.__file__)))
        cache.set(cname, version, 60*60*24*30)
    return version

def get_all_versions(fail_silently=bool(not settings.DEBUG)):
    # this cannot be done on load as there would be circular and parital imports
    try:
        allnames = ['', 'django'] + settings.INSTALLED_APPS
        res = [ (app, smart_str(svn_app_version(app, fail_silently)))
                    for app in allnames ]
    except:
        if fail_silently: return []
        raise
    return res

########NEW FILE########
__FILENAME__ = var_tag
from django import template

register = template.Library()

class VarNode(template.Node):
    def __init__(self, var_name, var_to_resolve):
        self.var_name = var_name
        self.var_to_resolve = var_to_resolve
    def get_context(self, top_context):
        for context in top_context.dicts:
            if self.var_name in context:
                return context
        return top_context
    def render(self, context):
        try:
            resolved_var = template.resolve_variable(self.var_to_resolve,
                                                     context)
            self.get_context(context)[self.var_name] = resolved_var
        except template.VariableDoesNotExist:
            self.get_context(context)[self.var_name] = ''
        return ''


@register.tag
def var(parser, token):
    '''
    {% var foo = expression %}
    {% var foo = Model.foo_set.count %}
    {% var foo = foo|restructuredtext %}
    {{ foo }} {{ foo|escape }}
    '''

    args = token.split_contents()
    if len(args) != 4 or args[2] != '=':
        raise template.TemplateSyntaxError(
            "'%s' statement requires the form {% %s foo = bar %}." % (
                args[0], args[0]))
    return VarNode(args[1], args[3])

########NEW FILE########
__FILENAME__ = utils
from django.conf import settings

_inbox_count_sources = None

def inbox_count_sources():
    global _inbox_count_sources
    if _inbox_count_sources is None:
        sources = []
        for path in settings.COMBINED_INBOX_COUNT_SOURCES:
            i = path.rfind('.')
            module, attr = path[:i], path[i+1:]
            try:
                mod = __import__(module, {}, {}, [attr])
            except ImportError, e:
                raise ImproperlyConfigured('Error importing request processor module %s: "%s"' % (module, e))
            try:
                func = getattr(mod, attr)
            except AttributeError:
                raise ImproperlyConfigured('Module "%s" does not define a "%s" callable request processor' % (module, attr))
            sources.append(func)
        _inbox_count_sources = tuple(sources)
    return _inbox_count_sources


def get_send_mail():
    """
    A function to return a send_mail function suitable for use in the app. It
    deals with incompatibilities between signatures.
    """
    # favour django-mailer but fall back to django.core.mail
    if "mailer" in settings.INSTALLED_APPS:
        from mailer import send_mail
    else:
        from django.core.mail import send_mail as _send_mail
        def send_mail(*args, **kwargs):
            del kwargs["priority"]
            return _send_mail(*args, **kwargs)
    return send_mail

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from emailconfirmation.models import EmailAddress, EmailConfirmation

admin.site.register(EmailAddress)
admin.site.register(EmailConfirmation)

########NEW FILE########
__FILENAME__ = models
from datetime import datetime, timedelta
from random import random
import sha

from django.conf import settings
from django.db import models, IntegrityError
from django.template.loader import render_to_string
from django.core.urlresolvers import reverse
from django.contrib.sites.models import Site
from django.contrib.auth.models import User

from emailconfirmation.utils import get_send_mail
send_mail = get_send_mail()

# this code based in-part on django-registration

class EmailAddressManager(models.Manager):
    
    def add_email(self, user, email):
        try:
            email_address = self.create(user=user, email=email)
            EmailConfirmation.objects.send_confirmation(email_address)
            return email_address
        except IntegrityError:
            return None
    
    def get_primary(self, user):
        try:
            return self.get(user=user, primary=True)
        except EmailAddress.DoesNotExist:
            return None
    
    def get_users_for(self, email):
        """
        returns a list of users with the given email.
        """
        # this is a list rather than a generator because we probably want to do a len() on it right away
        return [address.user for address in EmailAddress.objects.filter(verified=True, email=email)]
    

class EmailAddress(models.Model):
    
    user = models.ForeignKey(User)
    email = models.EmailField()
    verified = models.BooleanField(default=False)
    primary = models.BooleanField(default=False)
    
    objects = EmailAddressManager()
    
    def set_as_primary(self, conditional=False):
        old_primary = EmailAddress.objects.get_primary(self.user)
        if old_primary:
            if conditional:
                return False
            old_primary.primary = False
            old_primary.save()
        self.primary = True
        self.save()
        self.user.email = self.email
        self.user.save()
        return True
    
    def __unicode__(self):
        return u"%s (%s)" % (self.email, self.user)
    
    class Meta:
        unique_together = (
            ("user", "email"),
        )


class EmailConfirmationManager(models.Manager):
    
    def confirm_email(self, confirmation_key):
        try:
            confirmation = self.get(confirmation_key=confirmation_key)
        except self.model.DoesNotExist:
            return None
        if not confirmation.key_expired():
            email_address = confirmation.email_address
            email_address.verified = True
            email_address.set_as_primary(conditional=True)
            email_address.save()
            return email_address
    
    def send_confirmation(self, email_address):
        salt = sha.new(str(random())).hexdigest()[:5]
        confirmation_key = sha.new(salt + email_address.email).hexdigest()
        current_site = Site.objects.get_current()
        activate_url = u"http://%s%s" % (
            unicode(current_site.domain),
            reverse("emailconfirmation.views.confirm_email", args=(confirmation_key,))
        )
        context = {
            "user": email_address.user,
            "activate_url": activate_url,
            "current_site": current_site,
            "confirmation_key": confirmation_key,
        }
        subject = render_to_string("emailconfirmation/email_confirmation_subject.txt", context)
        message = render_to_string("emailconfirmation/email_confirmation_message.txt", context)
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email_address.email], priority="high")
        
        return self.create(email_address=email_address, sent=datetime.now(), confirmation_key=confirmation_key)
    
    def delete_expired_confirmations(self):
        for confirmation in self.all():
            if confirmation.key_expired():
                confirmation.delete()

class EmailConfirmation(models.Model):
    
    email_address = models.ForeignKey(EmailAddress)
    sent = models.DateTimeField()
    confirmation_key = models.CharField(max_length=40)
    
    objects = EmailConfirmationManager()
    
    def key_expired(self):
        expiration_date = self.sent + timedelta(days=settings.EMAIL_CONFIRMATION_DAYS)
        return expiration_date <= datetime.now()
    key_expired.boolean = True
    
    def __unicode__(self):
        return u"confirmation for %s" % self.email_address

########NEW FILE########
__FILENAME__ = utils

from django.conf import settings

def get_send_mail():
    """
    A function to return a send_mail function suitable for use in the app. It
    deals with incompatibilities between signatures.
    """
    # favour django-mailer but fall back to django.core.mail
    if "mailer" in settings.INSTALLED_APPS:
        from mailer import send_mail
    else:
        from django.core.mail import send_mail as _send_mail
        def send_mail(*args, **kwargs):
            del kwargs["priority"]
            return _send_mail(*args, **kwargs)
    return send_mail
########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render_to_response
from django.template import RequestContext

from emailconfirmation.models import EmailConfirmation

def confirm_email(request, confirmation_key):
    confirmation_key = confirmation_key.lower()
    email_address = EmailConfirmation.objects.confirm_email(confirmation_key)
    return render_to_response("emailconfirmation/confirm_email.html", {
        "email_address": email_address,
    }, context_instance=RequestContext(request))
########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from notification.models import NoticeType, NoticeSetting, Notice, ObservedItem

class NoticeTypeAdmin(admin.ModelAdmin):
    list_display = ('label', 'display', 'description', 'default')

class NoticeSettingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'notice_type', 'medium', 'send')

class NoticeAdmin(admin.ModelAdmin):
    list_display = ('message', 'user', 'notice_type', 'added', 'unseen', 'archived')


admin.site.register(NoticeType, NoticeTypeAdmin)
admin.site.register(NoticeSetting, NoticeSettingAdmin)
admin.site.register(Notice, NoticeAdmin)
admin.site.register(ObservedItem)

########NEW FILE########
__FILENAME__ = context_processors
from notification.models import Notice

def notification(request):
    if request.user.is_authenticated():
        return {'notice_unseen_count': Notice.objects.unseen_count_for(request.user),}
    else:
        return {}

########NEW FILE########
__FILENAME__ = decorators
from django.utils.translation import ugettext as _
from django.http import HttpResponse
from django.contrib.auth import authenticate, login
from django.conf import settings

def simple_basic_auth_callback(request, user, *args, **kwargs):
    """
    Simple callback to automatically login the given user after a successful
    basic authentication.
    """
    login(request, user)
    request.user = user

def basic_auth_required(realm=None, test_func=None, callback_func=None):
    """
    This decorator should be used with views that need simple authentication
    against Django's authentication framework.
    
    The ``realm`` string is shown during the basic auth query.
    
    It takes a ``test_func`` argument that is used to validate the given
    credentials and return the decorated function if successful.
    
    If unsuccessful the decorator will try to authenticate and checks if the
    user has the ``is_active`` field set to True.
    
    In case of a successful authentication  the ``callback_func`` will be
    called by passing the ``request`` and the ``user`` object. After that the
    actual view function will be called.
    
    If all of the above fails a "Authorization Required" message will be shown.
    """
    if realm is None:
        realm = getattr(settings, 'HTTP_AUTHENTICATION_REALM', _('Restricted Access'))
    if test_func is None:
        test_func = lambda u: u.is_authenticated()

    def decorator(view_func):
        def basic_auth(request, *args, **kwargs):
            # Just return the original view because already logged in
            if test_func(request.user):
                return view_func(request, *args, **kwargs)

            # Not logged in, look if login credentials are provided
            if 'HTTP_AUTHORIZATION' in request.META:        
                auth_method, auth = request.META['HTTP_AUTHORIZATION'].split(' ',1)
                if 'basic' == auth_method.lower():
                    auth = auth.strip().decode('base64')
                    username, password = auth.split(':',1)
                    user = authenticate(username=username, password=password)
                    if user is not None:
                        if user.is_active:
                            if callback_func is not None and callable(callback_func):
                                callback_func(request, user, *args, **kwargs)
                            return view_func(request, *args, **kwargs)

            response =  HttpResponse(_('Authorization Required'), mimetype="text/plain")
            response.status_code = 401
            response['WWW-Authenticate'] = 'Basic realm="%s"' % realm
            return response
        return basic_auth
    return decorator

########NEW FILE########
__FILENAME__ = engine

import time
import logging

try:
    import cPickle as pickle
except ImportError:
    import pickle

from django.conf import settings
from django.contrib.auth.models import User

from lockfile import FileLock, AlreadyLocked, LockTimeout

from notification.models import NoticeQueueBatch
from notification import models as notification

# lock timeout value. how long to wait for the lock to become available.
# default behavior is to never wait for the lock to be available.
LOCK_WAIT_TIMEOUT = getattr(settings, "NOTIFICATION_LOCK_WAIT_TIMEOUT", -1)

def send_all():
    lock = FileLock("send_notices")

    logging.debug("acquiring lock...")
    try:
        lock.acquire(LOCK_WAIT_TIMEOUT)
    except AlreadyLocked:
        logging.debug("lock already in place. quitting.")
        return
    except LockTimeout:
        logging.debug("waiting for the lock timed out. quitting.")
        return
    logging.debug("acquired.")

    batches, sent = 0, 0
    start_time = time.time()

    try:
        for queued_batch in NoticeQueueBatch.objects.all():
            notices = pickle.loads(str(queued_batch.pickled_data).decode("base64"))
            for user, label, extra_context, on_site in notices:
                user = User.objects.get(pk=user)
                logging.info("emitting notice to %s" % user)
                # call this once per user to be atomic and allow for logging to
                # accurately show how long each takes.
                notification.send_now([user], label, extra_context, on_site)
                sent += 1
            queued_batch.delete()
            batches += 1
    finally:
        logging.debug("releasing lock...")
        lock.release()
        logging.debug("released.")
    
    logging.info("")
    logging.info("%s batches, %s sent" % (batches, sent,))
    logging.info("done in %.2f seconds" % (time.time() - start_time))

########NEW FILE########
__FILENAME__ = feeds
from atomformat import Feed
from datetime import datetime

from django.core.urlresolvers import reverse
from django.conf import settings
from django.contrib.sites.models import Site
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import linebreaks, escape, striptags
from django.utils.translation import ugettext_lazy as _

from notification.models import Notice

ITEMS_PER_FEED = getattr(settings, 'ITEMS_PER_FEED', 20)

class BaseNoticeFeed(Feed):
    def item_id(self, notification):
        return "http://%s%s" % (
            Site.objects.get_current().domain,
            notification.get_absolute_url(),
        )
    
    def item_title(self, notification):
        return striptags(notification.message)
    
    def item_updated(self, notification):
        return notification.added
    
    def item_published(self, notification):
        return notification.added
    
    def item_content(self, notification):
        return {"type" : "html", }, linebreaks(escape(notification.message))
    
    def item_links(self, notification):
        return [{"href" : self.item_id(notification)}]
    
    def item_authors(self, notification):
        return [{"name" : notification.user.username}]

class NoticeUserFeed(BaseNoticeFeed):
    def get_object(self, params):
        return get_object_or_404(User, username=params[0].lower())

    def feed_id(self, user):
        return "http://%s%s" % (
                Site.objects.get_current().domain,
                reverse('notification_feed_for_user'),
            )

    def feed_title(self, user):
        return _('Notices Feed')

    def feed_updated(self, user):
        qs = Notice.objects.filter(user=user)
        # We return an arbitrary date if there are no results, because there
        # must be a feed_updated field as per the Atom specifications, however
        # there is no real data to go by, and an arbitrary date can be static.
        if qs.count() == 0:
            return datetime(year=2008, month=7, day=1)
        return qs.latest('added').added

    def feed_links(self, user):
        complete_url = "http://%s%s" % (
                Site.objects.get_current().domain,
                reverse('notification_notices'),
            )
        return ({'href': complete_url},)

    def items(self, user):
        return Notice.objects.notices_for(user).order_by("-added")[:ITEMS_PER_FEED]

########NEW FILE########
__FILENAME__ = lockfile

"""
lockfile.py - Platform-independent advisory file locks.

Requires Python 2.5 unless you apply 2.4.diff
Locking is done on a per-thread basis instead of a per-process basis.

Usage:

>>> lock = FileLock(_testfile())
>>> try:
...     lock.acquire()
... except AlreadyLocked:
...     print _testfile(), 'is locked already.'
... except LockFailed:
...     print _testfile(), 'can\\'t be locked.'
... else:
...     print 'got lock'
got lock
>>> print lock.is_locked()
True
>>> lock.release()

>>> lock = FileLock(_testfile())
>>> print lock.is_locked()
False
>>> with lock:
...    print lock.is_locked()
True
>>> print lock.is_locked()
False
>>> # It is okay to lock twice from the same thread...
>>> with lock:
...     lock.acquire()
...
>>> # Though no counter is kept, so you can't unlock multiple times...
>>> print lock.is_locked()
False

Exceptions:

    Error - base class for other exceptions
        LockError - base class for all locking exceptions
            AlreadyLocked - Another thread or process already holds the lock
            LockFailed - Lock failed for some other reason
        UnlockError - base class for all unlocking exceptions
            AlreadyUnlocked - File was not locked.
            NotMyLock - File was locked but not by the current thread/process

To do:
    * Write more test cases
      - verify that all lines of code are executed
    * Describe on-disk file structures in the documentation.
"""

from __future__ import division, with_statement

import socket
import os
import threading
import time
import errno
import thread

class Error(Exception):
    """
    Base class for other exceptions.

    >>> try:
    ...   raise Error
    ... except Exception:
    ...   pass
    """
    pass

class LockError(Error):
    """
    Base class for error arising from attempts to acquire the lock.

    >>> try:
    ...   raise LockError
    ... except Error:
    ...   pass
    """
    pass

class LockTimeout(LockError):
    """Raised when lock creation fails within a user-defined period of time.

    >>> try:
    ...   raise LockTimeout
    ... except LockError:
    ...   pass
    """
    pass

class AlreadyLocked(LockError):
    """Some other thread/process is locking the file.

    >>> try:
    ...   raise AlreadyLocked
    ... except LockError:
    ...   pass
    """
    pass

class LockFailed(LockError):
    """Lock file creation failed for some other reason.

    >>> try:
    ...   raise LockFailed
    ... except LockError:
    ...   pass
    """
    pass

class UnlockError(Error):
    """
    Base class for errors arising from attempts to release the lock.

    >>> try:
    ...   raise UnlockError
    ... except Error:
    ...   pass
    """
    pass

class NotLocked(UnlockError):
    """Raised when an attempt is made to unlock an unlocked file.

    >>> try:
    ...   raise NotLocked
    ... except UnlockError:
    ...   pass
    """
    pass

class NotMyLock(UnlockError):
    """Raised when an attempt is made to unlock a file someone else locked.

    >>> try:
    ...   raise NotMyLock
    ... except UnlockError:
    ...   pass
    """
    pass

class LockBase:
    """Base class for platform-specific lock classes."""
    def __init__(self, path, threaded=True):
        """
        >>> lock = LockBase(_testfile())
        """
        self.path = path
        self.lock_file = os.path.abspath(path) + ".lock"
        self.hostname = socket.gethostname()
        self.pid = os.getpid()
        if threaded:
            tname = "%x-" % thread.get_ident()
        else:
            tname = ""
        dirname = os.path.dirname(self.lock_file)
        self.unique_name = os.path.join(dirname,
                                        "%s.%s%s" % (self.hostname,
                                                     tname,
                                                     self.pid))

    def acquire(self, timeout=None):
        """
        Acquire the lock.

        * If timeout is omitted (or None), wait forever trying to lock the
          file.

        * If timeout > 0, try to acquire the lock for that many seconds.  If
          the lock period expires and the file is still locked, raise
          LockTimeout.

        * If timeout <= 0, raise AlreadyLocked immediately if the file is
          already locked.

        >>> # As simple as it gets.
        >>> lock = FileLock(_testfile())
        >>> lock.acquire()
        >>> lock.release()

        >>> # No timeout test
        >>> e1, e2 = threading.Event(), threading.Event()
        >>> t = _in_thread(_lock_wait_unlock, e1, e2)
        >>> e1.wait()         # wait for thread t to acquire lock
        >>> lock2 = FileLock(_testfile())
        >>> lock2.is_locked()
        True
        >>> lock2.i_am_locking()
        False
        >>> try:
        ...   lock2.acquire(timeout=-1)
        ... except AlreadyLocked:
        ...   pass
        ... except Exception, e:
        ...   print 'unexpected exception', repr(e)
        ... else:
        ...   print 'thread', threading.currentThread().getName(),
        ...   print 'erroneously locked an already locked file.'
        ...   lock2.release()
        ...
        >>> e2.set()          # tell thread t to release lock
        >>> t.join()

        >>> # Timeout test
        >>> e1, e2 = threading.Event(), threading.Event()
        >>> t = _in_thread(_lock_wait_unlock, e1, e2)
        >>> e1.wait() # wait for thread t to acquire filelock
        >>> lock2 = FileLock(_testfile())
        >>> lock2.is_locked()
        True
        >>> try:
        ...   lock2.acquire(timeout=0.1)
        ... except LockTimeout:
        ...   pass
        ... except Exception, e:
        ...   print 'unexpected exception', repr(e)
        ... else:
        ...   lock2.release()
        ...   print 'thread', threading.currentThread().getName(),
        ...   print 'erroneously locked an already locked file.'
        ...
        >>> e2.set()
        >>> t.join()
        """
        pass

    def release(self):
        """
        Release the lock.

        If the file is not locked, raise NotLocked.
        >>> lock = FileLock(_testfile())
        >>> lock.acquire()
        >>> lock.release()
        >>> lock.is_locked()
        False
        >>> lock.i_am_locking()
        False
        >>> try:
        ...   lock.release()
        ... except NotLocked:
        ...   pass
        ... except NotMyLock:
        ...   print 'unexpected exception', NotMyLock
        ... except Exception, e:
        ...   print 'unexpected exception', repr(e)
        ... else:
        ...   print 'erroneously unlocked file'

        >>> e1, e2 = threading.Event(), threading.Event()
        >>> t = _in_thread(_lock_wait_unlock, e1, e2)
        >>> e1.wait()
        >>> lock2 = FileLock(_testfile())
        >>> lock2.is_locked()
        True
        >>> lock2.i_am_locking()
        False
        >>> try:
        ...   lock2.release()
        ... except NotMyLock:
        ...   pass
        ... except Exception, e:
        ...   print 'unexpected exception', repr(e)
        ... else:
        ...   print 'erroneously unlocked a file locked by another thread.'
        ...
        >>> e2.set()
        >>> t.join()
        """
        pass

    def is_locked(self):
        """
        Tell whether or not the file is locked.
        >>> lock = FileLock(_testfile())
        >>> lock.acquire()
        >>> lock.is_locked()
        True
        >>> lock.release()
        >>> lock.is_locked()
        False
        """
        pass

    def i_am_locking(self):
        """Return True if this object is locking the file.

        >>> lock1 = FileLock(_testfile(), threaded=False)
        >>> lock1.acquire()
        >>> lock2 = FileLock(_testfile())
        >>> lock1.i_am_locking()
        True
        >>> lock2.i_am_locking()
        False
	>>> try:
	...   lock2.acquire(timeout=2)
	... except LockTimeout:
        ...   lock2.break_lock()
        ...   lock2.is_locked()
        ...   lock1.is_locked()
        ...   lock2.acquire()
        ... else:
        ...   print 'expected LockTimeout...'
        ...
        False
        False
        >>> lock1.i_am_locking()
        False
        >>> lock2.i_am_locking()
        True
        >>> lock2.release()
        """
        pass

    def break_lock(self):
        """Remove a lock.  Useful if a locking thread failed to unlock.

        >>> lock = FileLock(_testfile())
        >>> lock.acquire()
        >>> lock2 = FileLock(_testfile())
        >>> lock2.is_locked()
        True
        >>> lock2.break_lock()
        >>> lock2.is_locked()
        False
        >>> try:
        ...   lock.release()
        ... except NotLocked:
        ...   pass
        ... except Exception, e:
        ...   print 'unexpected exception', repr(e)
        ... else:
        ...   print 'break lock failed'
        """
        pass

    def __enter__(self):
        """Context manager support.

        >>> lock = FileLock(_testfile())
        >>> with lock:
        ...   lock.is_locked()
        ...
        True
        >>> lock.is_locked()
        False
        """
        self.acquire()
        return self

    def __exit__(self, *_exc):
        """Context manager support.

        >>> 'tested in __enter__'
        'tested in __enter__'
        """
        self.release()

class LinkFileLock(LockBase):
    """Lock access to a file using atomic property of link(2)."""

    def acquire(self, timeout=None):
        """
        >>> d = _testfile()
        >>> os.mkdir(d)
        >>> os.chmod(d, 0444)
        >>> try:
        ...   lock = LinkFileLock(os.path.join(d, 'test'))
        ...   try:
        ...     lock.acquire()
        ...   except LockFailed:
        ...     pass
        ...   else:
        ...     lock.release()
        ...     print 'erroneously locked', os.path.join(d, 'test')
        ... finally:
        ...   os.chmod(d, 0664)
        ...   os.rmdir(d)
        """
        try:
            open(self.unique_name, "wb").close()
        except IOError:
            raise LockFailed

        end_time = time.time()
        if timeout is not None and timeout > 0:
            end_time += timeout

        while True:
            # Try and create a hard link to it.
            try:
                os.link(self.unique_name, self.lock_file)
            except OSError:
                # Link creation failed.  Maybe we've double-locked?
                nlinks = os.stat(self.unique_name).st_nlink
                if nlinks == 2:
                    # The original link plus the one I created == 2.  We're
                    # good to go.
                    return
                else:
                    # Otherwise the lock creation failed.
                    if timeout is not None and time.time() > end_time:
                        os.unlink(self.unique_name)
                        if timeout > 0:
                            raise LockTimeout
                        else:
                            raise AlreadyLocked
                    time.sleep(timeout is not None and timeout/10 or 0.1)
            else:
                # Link creation succeeded.  We're good to go.
                return

    def release(self):
        if not self.is_locked():
            raise NotLocked
        elif not os.path.exists(self.unique_name):
            raise NotMyLock
        os.unlink(self.unique_name)
        os.unlink(self.lock_file)

    def is_locked(self):
        return os.path.exists(self.lock_file)

    def i_am_locking(self):
        return (self.is_locked() and
                os.path.exists(self.unique_name) and
                os.stat(self.unique_name).st_nlink == 2)

    def break_lock(self):
        if os.path.exists(self.lock_file):
            os.unlink(self.lock_file)

class MkdirFileLock(LockBase):
    """Lock file by creating a directory."""
    def __init__(self, path, threaded=True):
        """
        >>> lock = MkdirFileLock(_testfile())
        """
        LockBase.__init__(self, path)
        if threaded:
            tname = "%x-" % thread.get_ident()
        else:
            tname = ""
        # Lock file itself is a directory.  Place the unique file name into
        # it.
        self.unique_name  = os.path.join(self.lock_file,
                                         "%s.%s%s" % (self.hostname,
                                                      tname,
                                                      self.pid))

    def acquire(self, timeout=None):
        end_time = time.time()
        if timeout is not None and timeout > 0:
            end_time += timeout

        if timeout is None:
            wait = 0.1
        else:
            wait = max(0, timeout / 10)

        while True:
            try:
                os.mkdir(self.lock_file)
            except OSError, err:
                if err.errno == errno.EEXIST:
                    # Already locked.
                    if os.path.exists(self.unique_name):
                        # Already locked by me.
                        return
                    if timeout is not None and time.time() > end_time:
                        if timeout > 0:
                            raise LockTimeout
                        else:
                            # Someone else has the lock.
                            raise AlreadyLocked
                    time.sleep(wait)
                else:
                    # Couldn't create the lock for some other reason
                    raise LockFailed
            else:
                open(self.unique_name, "wb").close()
                return

    def release(self):
        if not self.is_locked():
            raise NotLocked
        elif not os.path.exists(self.unique_name):
            raise NotMyLock
        os.unlink(self.unique_name)
        os.rmdir(self.lock_file)

    def is_locked(self):
        return os.path.exists(self.lock_file)

    def i_am_locking(self):
        return (self.is_locked() and
                os.path.exists(self.unique_name))

    def break_lock(self):
        if os.path.exists(self.lock_file):
            for name in os.listdir(self.lock_file):
                os.unlink(os.path.join(self.lock_file, name))
            os.rmdir(self.lock_file)

class SQLiteFileLock(LockBase):
    "Demonstration of using same SQL-based locking."

    import tempfile
    _fd, testdb = tempfile.mkstemp()
    os.close(_fd)
    os.unlink(testdb)
    del _fd, tempfile

    def __init__(self, path, threaded=True):
        LockBase.__init__(self, path, threaded)
        self.lock_file = unicode(self.lock_file)
        self.unique_name = unicode(self.unique_name)

        import sqlite3
        self.connection = sqlite3.connect(SQLiteFileLock.testdb)
        
        c = self.connection.cursor()
        try:
            c.execute("create table locks"
                      "("
                      "   lock_file varchar(32),"
                      "   unique_name varchar(32)"
                      ")")
        except sqlite3.OperationalError:
            pass
        else:
            self.connection.commit()
            import atexit
            atexit.register(os.unlink, SQLiteFileLock.testdb)

    def acquire(self, timeout=None):
        end_time = time.time()
        if timeout is not None and timeout > 0:
            end_time += timeout

        if timeout is None:
            wait = 0.1
        elif timeout <= 0:
            wait = 0
        else:
            wait = timeout / 10

        cursor = self.connection.cursor()

        while True:
            if not self.is_locked():
                # Not locked.  Try to lock it.
                cursor.execute("insert into locks"
                               "  (lock_file, unique_name)"
                               "  values"
                               "  (?, ?)",
                               (self.lock_file, self.unique_name))
                self.connection.commit()

                # Check to see if we are the only lock holder.
                cursor.execute("select * from locks"
                               "  where unique_name = ?",
                               (self.unique_name,))
                rows = cursor.fetchall()
                if len(rows) > 1:
                    # Nope.  Someone else got there.  Remove our lock.
                    cursor.execute("delete from locks"
                                   "  where unique_name = ?",
                                   (self.unique_name,))
                    self.connection.commit()
                else:
                    # Yup.  We're done, so go home.
                    return
            else:
                # Check to see if we are the only lock holder.
                cursor.execute("select * from locks"
                               "  where unique_name = ?",
                               (self.unique_name,))
                rows = cursor.fetchall()
                if len(rows) == 1:
                    # We're the locker, so go home.
                    return
                    
            # Maybe we should wait a bit longer.
            if timeout is not None and time.time() > end_time:
                if timeout > 0:
                    # No more waiting.
                    raise LockTimeout
                else:
                    # Someone else has the lock and we are impatient..
                    raise AlreadyLocked

            # Well, okay.  We'll give it a bit longer.
            time.sleep(wait)

    def release(self):
        if not self.is_locked():
            raise NotLocked
        if not self.i_am_locking():
            raise NotMyLock, ("locker:", self._who_is_locking(),
                              "me:", self.unique_name)
        cursor = self.connection.cursor()
        cursor.execute("delete from locks"
                       "  where unique_name = ?",
                       (self.unique_name,))
        self.connection.commit()

    def _who_is_locking(self):
        cursor = self.connection.cursor()
        cursor.execute("select unique_name from locks"
                       "  where lock_file = ?",
                       (self.lock_file,))
        return cursor.fetchone()[0]
        
    def is_locked(self):
        cursor = self.connection.cursor()
        cursor.execute("select * from locks"
                       "  where lock_file = ?",
                       (self.lock_file,))
        rows = cursor.fetchall()
        return not not rows

    def i_am_locking(self):
        cursor = self.connection.cursor()
        cursor.execute("select * from locks"
                       "  where lock_file = ?"
                       "    and unique_name = ?",
                       (self.lock_file, self.unique_name))
        return not not cursor.fetchall()

    def break_lock(self):
        cursor = self.connection.cursor()
        cursor.execute("delete from locks"
                       "  where lock_file = ?",
                       (self.lock_file,))
        self.connection.commit()

if hasattr(os, "link"):
    FileLock = LinkFileLock
else:
    FileLock = MkdirFileLock

def _in_thread(func, *args, **kwargs):
    """Execute func(*args, **kwargs) after dt seconds.

    Helper for docttests.
    """
    def _f():
        func(*args, **kwargs)
    t = threading.Thread(target=_f, name='/*/*')
    t.start()
    return t

def _testfile():
    """Return platform-appropriate lock file name.

    Helper for doctests.
    """
    import tempfile
    return os.path.join(tempfile.gettempdir(), 'trash-%s' % os.getpid())

def _lock_wait_unlock(event1, event2):
    """Lock from another thread.

    Helper for doctests.
    """
    lock = FileLock(_testfile())
    with lock:
        event1.set()  # we're in,
        event2.wait() # wait for boss's permission to leave

def _test():
    global FileLock

    import doctest
    import sys

    def test_object(c):
        nfailed = ntests = 0
        for (obj, recurse) in ((c, True),
                               (LockBase, True),
                               (sys.modules["__main__"], False)):
            tests = doctest.DocTestFinder(recurse=recurse).find(obj)
            runner = doctest.DocTestRunner(verbose="-v" in sys.argv)
            tests.sort(key = lambda test: test.name)
            for test in tests:
                f, t = runner.run(test)
                nfailed += f
                ntests += t
        print FileLock.__name__, "tests:", ntests, "failed:", nfailed
        return nfailed, ntests

    nfailed = ntests = 0

    if hasattr(os, "link"):
        FileLock = LinkFileLock
        f, t = test_object(FileLock)
        nfailed += f
        ntests += t

    if hasattr(os, "mkdir"):
        FileLock = MkdirFileLock
        f, t = test_object(FileLock)
        nfailed += f
        ntests += t

    try:
        import sqlite3
    except ImportError:
        print "SQLite3 is unavailable - not testing SQLiteFileLock."
    else:
        print "Testing SQLiteFileLock with sqlite", sqlite3.sqlite_version,
        print "& pysqlite", sqlite3.version
        FileLock = SQLiteFileLock
        f, t = test_object(FileLock)
        nfailed += f
        ntests += t

    print "total tests:", ntests, "total failed:", nfailed

if __name__ == "__main__":
    _test()

########NEW FILE########
__FILENAME__ = emit_notices

import logging

from django.core.management.base import NoArgsCommand

from notification.engine import send_all

class Command(NoArgsCommand):
    help = "Emit queued notices."
    
    def handle_noargs(self, **options):
        logging.basicConfig(level=logging.DEBUG, format="%(message)s")
        logging.info("-" * 72)
        send_all()
    
########NEW FILE########
__FILENAME__ = models
import datetime

try:
    import cPickle as pickle
except ImportError:
    import pickle

from django.db import models
from django.db.models.query import QuerySet
from django.conf import settings
from django.core.urlresolvers import reverse
from django.template import Context
from django.template.loader import render_to_string

from django.core.exceptions import ImproperlyConfigured

from django.contrib.sites.models import Site
from django.contrib.auth.models import User
from django.contrib.auth.models import AnonymousUser

from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic

from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext, get_language, activate

# favour django-mailer but fall back to django.core.mail
try:
    from mailer import send_mail
except ImportError:
    from django.core.mail import send_mail

QUEUE_ALL = getattr(settings, "NOTIFICATION_QUEUE_ALL", False)

class LanguageStoreNotAvailable(Exception):
    pass

class NoticeType(models.Model):

    label = models.CharField(_('label'), max_length=40)
    display = models.CharField(_('display'), max_length=50)
    description = models.CharField(_('description'), max_length=100)

    # by default only on for media with sensitivity less than or equal to this number
    default = models.IntegerField(_('default'))

    def __unicode__(self):
        return self.label

    class Meta:
        verbose_name = _("notice type")
        verbose_name_plural = _("notice types")


# if this gets updated, the create() method below needs to be as well...
NOTICE_MEDIA = (
    ("1", _("Email")),
)

# how spam-sensitive is the medium
NOTICE_MEDIA_DEFAULTS = {
    "1": 2 # email
}

class NoticeSetting(models.Model):
    """
    Indicates, for a given user, whether to send notifications
    of a given type to a given medium.
    """

    user = models.ForeignKey(User, verbose_name=_('user'))
    notice_type = models.ForeignKey(NoticeType, verbose_name=_('notice type'))
    medium = models.CharField(_('medium'), max_length=1, choices=NOTICE_MEDIA)
    send = models.BooleanField(_('send'))

    class Meta:
        verbose_name = _("notice setting")
        verbose_name_plural = _("notice settings")
        unique_together = ("user", "notice_type", "medium")

def get_notification_setting(user, notice_type, medium):
    try:
        return NoticeSetting.objects.get(user=user, notice_type=notice_type, medium=medium)
    except NoticeSetting.DoesNotExist:
        default = (NOTICE_MEDIA_DEFAULTS[medium] <= notice_type.default)
        setting = NoticeSetting(user=user, notice_type=notice_type, medium=medium, send=default)
        setting.save()
        return setting

def should_send(user, notice_type, medium):
    return get_notification_setting(user, notice_type, medium).send


class NoticeManager(models.Manager):

    def notices_for(self, user, archived=False, unseen=None, on_site=None):
        """
        returns Notice objects for the given user.

        If archived=False, it only include notices not archived.
        If archived=True, it returns all notices for that user.

        If unseen=None, it includes all notices.
        If unseen=True, return only unseen notices.
        If unseen=False, return only seen notices.
        """
        if archived:
            qs = self.filter(user=user)
        else:
            qs = self.filter(user=user, archived=archived)
        if unseen is not None:
            qs = qs.filter(unseen=unseen)
        if on_site is not None:
            qs = qs.filter(on_site=on_site)
        return qs

    def unseen_count_for(self, user):
        """
        returns the number of unseen notices for the given user but does not
        mark them seen
        """
        return self.filter(user=user, unseen=True).count()

class Notice(models.Model):

    user = models.ForeignKey(User, verbose_name=_('user'))
    message = models.TextField(_('message'))
    notice_type = models.ForeignKey(NoticeType, verbose_name=_('notice type'))
    added = models.DateTimeField(_('added'), default=datetime.datetime.now)
    unseen = models.BooleanField(_('unseen'), default=True)
    archived = models.BooleanField(_('archived'), default=False)
    on_site = models.BooleanField(_('on site'))

    objects = NoticeManager()

    def __unicode__(self):
        return self.message

    def archive(self):
        self.archived = True
        self.save()

    def is_unseen(self):
        """
        returns value of self.unseen but also changes it to false.

        Use this in a template to mark an unseen notice differently the first
        time it is shown.
        """
        unseen = self.unseen
        if unseen:
            self.unseen = False
            self.save()
        return unseen

    class Meta:
        ordering = ["-added"]
        verbose_name = _("notice")
        verbose_name_plural = _("notices")

    @models.permalink
    def get_absolute_url(self):
        return ("notification_notice", [str(self.pk)])

class NoticeQueueBatch(models.Model):
    """
    A queued notice.
    Denormalized data for a notice.
    """
    pickled_data = models.TextField()

def create_notice_type(label, display, description, default=2):
    """
    Creates a new NoticeType.

    This is intended to be used by other apps as a post_syncdb manangement step.
    """
    try:
        notice_type = NoticeType.objects.get(label=label)
        updated = False
        if display != notice_type.display:
            notice_type.display = display
            updated = True
        if description != notice_type.description:
            notice_type.description = description
            updated = True
        if default != notice_type.default:
            notice_type.default = default
            updated = True
        if updated:
            notice_type.save()
            print "Updated %s NoticeType" % label
    except NoticeType.DoesNotExist:
        NoticeType(label=label, display=display, description=description, default=default).save()
        print "Created %s NoticeType" % label

def get_notification_language(user):
    """
    Returns site-specific notification language for this user. Raises
    LanguageStoreNotAvailable if this site does not use translated
    notifications.
    """
    if getattr(settings, 'NOTIFICATION_LANGUAGE_MODULE', False):
        try:
            app_label, model_name = settings.NOTIFICATION_LANGUAGE_MODULE.split('.')
            model = models.get_model(app_label, model_name)
            language_model = model._default_manager.get(user__id__exact=user.id)
            if hasattr(language_model, 'language'):
                return language_model.language
        except (ImportError, ImproperlyConfigured, model.DoesNotExist):
            raise LanguageStoreNotAvailable
    raise LanguageStoreNotAvailable

def get_formatted_messages(formats, label, context):
    """
    Returns a dictionary with the format identifier as the key. The values are
    are fully rendered templates with the given context.
    """
    format_templates = {}
    for format in formats:
        # conditionally turn off autoescaping for .txt extensions in format
        if format.endswith(".txt"):
            context.autoescape = False
        format_templates[format] = render_to_string((
            'notification/%s/%s' % (label, format),
            'notification/%s' % format), context_instance=context)
    return format_templates

def send_now(users, label, extra_context=None, on_site=True):
    """
    Creates a new notice.

    This is intended to be how other apps create new notices.

    notification.send(user, 'friends_invite_sent', {
        'spam': 'eggs',
        'foo': 'bar',
    )
    
    You can pass in on_site=False to prevent the notice emitted from being
    displayed on the site.
    """
    if extra_context is None:
        extra_context = {}
    
    notice_type = NoticeType.objects.get(label=label)

    current_site = Site.objects.get_current()
    notices_url = u"http://%s%s" % (
        unicode(current_site),
        reverse("notification_notices"),
    )

    current_language = get_language()

    formats = (
        'short.txt',
        'full.txt',
        'notice.html',
        'full.html',
    ) # TODO make formats configurable

    for user in users:
        recipients = []
        # get user language for user from language store defined in
        # NOTIFICATION_LANGUAGE_MODULE setting
        try:
            language = get_notification_language(user)
        except LanguageStoreNotAvailable:
            language = None

        if language is not None:
            # activate the user's language
            activate(language)

        # update context with user specific translations
        context = Context({
            "user": user,
            "notice": ugettext(notice_type.display),
            "notices_url": notices_url,
            "current_site": current_site,
        })
        context.update(extra_context)

        # get prerendered format messages
        messages = get_formatted_messages(formats, label, context)

        # Strip newlines from subject
        subject = ''.join(render_to_string('notification/email_subject.txt', {
            'message': messages['short.txt'],
        }, context).splitlines())

        body = render_to_string('notification/email_body.txt', {
            'message': messages['full.txt'],
        }, context)

        notice = Notice.objects.create(user=user, message=messages['notice.html'],
            notice_type=notice_type, on_site=on_site)
        if should_send(user, notice_type, "1") and user.email: # Email
            recipients.append(user.email)
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, recipients)

    # reset environment to original language
    activate(current_language)

def send(*args, **kwargs):
    """
    A basic interface around both queue and send_now. This honors a global
    flag NOTIFICATION_QUEUE_ALL that helps determine whether all calls should
    be queued or not. A per call ``queue`` or ``now`` keyword argument can be
    used to always override the default global behavior.
    """
    queue_flag = kwargs.pop("queue", False)
    now_flag = kwargs.pop("now", False)
    assert not (queue_flag and now_flag), "'queue' and 'now' cannot both be True."
    if queue_flag:
        return queue(*args, **kwargs)
    elif now_flag:
        return send_now(*args, **kwargs)
    else:
        if QUEUE_ALL:
            return queue(*args, **kwargs)
        else:
            return send_now(*args, **kwargs)
        
def queue(users, label, extra_context=None, on_site=True):
    """
    Queue the notification in NoticeQueueBatch. This allows for large amounts
    of user notifications to be deferred to a seperate process running outside
    the webserver.
    """
    if extra_context is None:
        extra_context = {}
    if isinstance(users, QuerySet):
        users = [row["pk"] for row in users.values("pk")]
    else:
        users = [user.pk for user in users]
    notices = []
    for user in users:
        notices.append((user, label, extra_context, on_site))
    NoticeQueueBatch(pickled_data=pickle.dumps(notices).encode("base64")).save()

class ObservedItemManager(models.Manager):

    def all_for(self, observed, signal):
        """
        Returns all ObservedItems for an observed object,
        to be sent when a signal is emited.
        """
        content_type = ContentType.objects.get_for_model(observed)
        observed_items = self.filter(content_type=content_type, object_id=observed.id, signal=signal)
        return observed_items

    def get_for(self, observed, observer, signal):
        content_type = ContentType.objects.get_for_model(observed)
        observed_item = self.get(content_type=content_type, object_id=observed.id, user=observer, signal=signal)
        return observed_item


class ObservedItem(models.Model):

    user = models.ForeignKey(User, verbose_name=_('user'))

    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    observed_object = generic.GenericForeignKey('content_type', 'object_id')

    notice_type = models.ForeignKey(NoticeType, verbose_name=_('notice type'))

    added = models.DateTimeField(_('added'), default=datetime.datetime.now)

    # the signal that will be listened to send the notice
    signal = models.TextField(verbose_name=_('signal'))

    objects = ObservedItemManager()

    class Meta:
        ordering = ['-added']
        verbose_name = _('observed item')
        verbose_name_plural = _('observed items')

    def send_notice(self):
        send([self.user], self.notice_type.label,
             {'observed': self.observed_object})


def observe(observed, observer, notice_type_label, signal='post_save'):
    """
    Create a new ObservedItem.

    To be used by applications to register a user as an observer for some object.
    """
    notice_type = NoticeType.objects.get(label=notice_type_label)
    observed_item = ObservedItem(user=observer, observed_object=observed,
                                 notice_type=notice_type, signal=signal)
    observed_item.save()
    return observed_item

def stop_observing(observed, observer, signal='post_save'):
    """
    Remove an observed item.
    """
    observed_item = ObservedItem.objects.get_for(observed, observer, signal)
    observed_item.delete()

def send_observation_notices_for(observed, signal='post_save'):
    """
    Send a notice for each registered user about an observed object.
    """
    observed_items = ObservedItem.objects.all_for(observed, signal)
    for observed_item in observed_items:
        observed_item.send_notice()
    return observed_items

def is_observing(observed, observer, signal='post_save'):
    if isinstance(observer, AnonymousUser):
        return False
    try:
        observed_items = ObservedItem.objects.get_for(observed, observer, signal)
        return True
    except ObservedItem.DoesNotExist:
        return False
    except ObservedItem.MultipleObjectsReturned:
        return True

def handle_observations(sender, instance, *args, **kw):
    send_observation_notices_for(instance)

########NEW FILE########
__FILENAME__ = captureas_tag
from django import template

register = template.Library()

@register.tag(name='captureas')
def do_captureas(parser, token):
    try:
        tag_name, args = token.contents.split(None, 1)
    except ValueError:
        raise template.TemplateSyntaxError("'captureas' node requires a variable name.")
    nodelist = parser.parse(('endcaptureas',))
    parser.delete_first_token()
    return CaptureasNode(nodelist, args)

class CaptureasNode(template.Node):
    def __init__(self, nodelist, varname):
        self.nodelist = nodelist
        self.varname = varname

    def render(self, context):
        output = self.nodelist.render(context)
        context[self.varname] = output
        return ''

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

# @@@ from atom import Feed

from notification.views import notices, mark_all_seen, feed_for_user, single

urlpatterns = patterns('',
    url(r'^$', notices, name="notification_notices"),
    url(r'^(\d+)/$', single, name="notification_notice"),
    url(r'^feed/$', feed_for_user, name="notification_feed_for_user"),
    url(r'^mark_all_seen/$', mark_all_seen, name="notification_mark_all_seen"),
)

########NEW FILE########
__FILENAME__ = views
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect, Http404
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.contrib.syndication.views import feed

from notification.models import *
from notification.decorators import basic_auth_required, simple_basic_auth_callback
from notification.feeds import NoticeUserFeed

@basic_auth_required(realm='Notices Feed', callback_func=simple_basic_auth_callback)
def feed_for_user(request):
    url = "feed/%s" % request.user.username
    return feed(request, url, {
        "feed": NoticeUserFeed,
    })

@login_required
def notices(request):
    notice_types = NoticeType.objects.all()
    notices = Notice.objects.notices_for(request.user, on_site=True)
    settings_table = []
    for notice_type in NoticeType.objects.all():
        settings_row = []
        for medium_id, medium_display in NOTICE_MEDIA:
            form_label = "%s_%s" % (notice_type.label, medium_id)
            setting = get_notification_setting(request.user, notice_type, medium_id)
            if request.method == "POST":
                if request.POST.get(form_label) == "on":
                    setting.send = True
                else:
                    setting.send = False
                setting.save()
            settings_row.append((form_label, setting.send))
        settings_table.append({"notice_type": notice_type, "cells": settings_row})
    
    notice_settings = {
        "column_headers": [medium_display for medium_id, medium_display in NOTICE_MEDIA],
        "rows": settings_table,
    }
    
    return render_to_response("notification/notices.html", {
        "notices": notices,
        "notice_types": notice_types,
        "notice_settings": notice_settings,
    }, context_instance=RequestContext(request))

@login_required
def single(request, id):
    notice = get_object_or_404(Notice, id=id)
    if request.user == notice.user:
        return render_to_response("notification/single.html", {
            "notice": notice,
        }, context_instance=RequestContext(request))
    raise Http404

@login_required
def archive(request, noticeid=None, next_page=None):
    if noticeid:
        try:
            notice = Notice.objects.get(id=noticeid)
            if request.user == notice.user or request.user.is_superuser:
                notice.archive()
            else:   # you can archive other users' notices
                    # only if you are superuser.
                return HttpResponseRedirect(next_page)
        except Notice.DoesNotExist:
            return HttpResponseRedirect(next_page)
    return HttpResponseRedirect(next_page)

@login_required
def delete(request, noticeid=None, next_page=None):
    if noticeid:
        try:
            notice = Notice.objects.get(id=noticeid)
            if request.user == notice.user or request.user.is_superuser:
                notice.delete()
            else:   # you can delete other users' notices
                    # only if you are superuser.
                return HttpResponseRedirect(next_page)
        except Notice.DoesNotExist:
            return HttpResponseRedirect(next_page)
    return HttpResponseRedirect(next_page)

@login_required
def mark_all_seen(request):
    for notice in Notice.objects.notices_for(request.user, unseen=True):
        notice.unseen = False
        notice.save()
    return HttpResponseRedirect(reverse("notification_notices"))
    
########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from profiles.models import Profile

admin.site.register(Profile)

########NEW FILE########
__FILENAME__ = 001_add_timezone

from django_evolution.mutations import *
from django.db import models
from django.conf import settings

MUTATIONS = [
    AddField('Profile', 'timezone', models.CharField, initial=settings.TIME_ZONE, max_length=100)
]

########NEW FILE########
__FILENAME__ = 002_add_language
from django_evolution.mutations import *
from django.db import models
from django.conf import settings

MUTATIONS = [
    AddField('Profile', 'language', models.CharField, initial=settings.LANGUAGE_CODE, max_length=10)
]

########NEW FILE########
__FILENAME__ = forms
from django.conf import settings
from django import forms

from profiles.models import Profile

try:
    from notification import models as notification
except ImportError:
    notification = None

class ProfileForm(forms.ModelForm):
    
    class Meta:
        model = Profile
        exclude = ('user', 'blogrss', 'timezone', 'language',
            'twitter_user', 'twitter_password', 'pownce_user', 'pownce_password')

########NEW FILE########
__FILENAME__ = cache_profile_feeds
from django.core.management.base import NoArgsCommand
from feedutil.templatetags.feedutil import pull_feed
from account.models import OtherServiceInfo
from django.conf import settings

class Command(NoArgsCommand):
    help = 'For each blogrss url, cache the feed.'
    
    def handle_noargs(self, **options):
        for info in OtherServiceInfo.objects.filter(key="blogrss"):
            try:
                pull_feed(info.value)
            except:
                if settings.DEBUG: raise

########NEW FILE########
__FILENAME__ = create_profiles_for_users
from django.core.management.base import NoArgsCommand
from profiles.models import Profile
from django.contrib.auth.models import User
from django.conf import settings

class Command(NoArgsCommand):
    help = 'Create a profile object for users which do not have one.'

    def handle_noargs(self, **options):
        for usr in User.objects.all():
            profile, is_new = Profile.objects.get_or_create(user=usr)
            if is_new: profile.save()

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.utils.translation import ugettext_lazy as _

from timezones.fields import TimeZoneField

class Profile(models.Model):

    user = models.ForeignKey(User, unique=True, verbose_name=_('user'))
    name = models.CharField(_('name'), max_length=200, null=True, blank=True)
    about = models.TextField(_('about'), null=True, blank=True)
    location = models.CharField(_('location'), max_length=40, null=True, blank=True)
    website = models.URLField(_('website'), null=True, blank=True, verify_exists=False)
    
    # @@@ the following are all deprecated -  see account/models.py
    blogrss = models.URLField(_('blog rss/atom'), null=True, blank=True, verify_exists=False)
    timezone = TimeZoneField(_('timezone'))
    twitter_user = models.CharField(_('Twitter Username'), max_length=50, blank=True)
    twitter_password = models.CharField(_('Twitter Password'), max_length=50, blank=True)
    pownce_user = models.CharField(_('Pownce Username'), max_length=50, blank=True)
    pownce_password = models.CharField(_('Pownce Password'), max_length=50, blank=True)
    language = models.CharField(_('language'), max_length=10, choices=settings.LANGUAGES, default=settings.LANGUAGE_CODE)

    def __unicode__(self):
        return self.user.username

    def get_absolute_url(self):
        return ('profile_detail', None, {'username': self.user.username})
    get_absolute_url = models.permalink(get_absolute_url)

    class Meta:
        verbose_name = _('profile')
        verbose_name_plural = _('profiles')

def create_profile(sender, instance=None, **kwargs):
    if instance is None:
        return
    profile, created = Profile.objects.get_or_create(user=instance)

post_save.connect(create_profile, sender=User)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^$', 'profiles.views.profiles', name='profile_list'),
    url(r'^(?P<username>[\w]+)/$', 'profiles.views.profile', name='profile_detail'),
    url(r'^username_autocomplete/$', 'profiles.views.username_autocomplete', name='profile_username_autocomplete'),
)

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.contrib.auth.models import User
from django.http import HttpResponse, HttpResponseForbidden

from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext

#from friends.forms import InviteFriendForm
#from friends.models import FriendshipInvitation, Friendship
#from photos.models import Photos

#from zwitschern.models import Following

from profiles.models import Profile
from profiles.forms import ProfileForm

#from gravatar.templatetags.gravatar import gravatar

try:
    from notification import models as notification
except ImportError:
    notification = None

def profiles(request, template_name="profiles/profiles.html"):
    return render_to_response(template_name, {
        "users": User.objects.all().order_by("-date_joined"),
    }, context_instance=RequestContext(request))

def profile(request, username, template_name="profiles/profile.html"):
    other_user = get_object_or_404(User, username=username)
    if request.user.is_authenticated():
        # is_friend = Friendship.objects.are_friends(request.user, other_user)
        # is_following = Following.objects.is_following(request.user, other_user)
        # other_friends = Friendship.objects.friends_for_user(other_user)
        if request.user == other_user:
            is_me = True
        else:
            is_me = False
    else:
        other_friends = []
        is_friend = False
        is_me = False
        is_following = False
    
    if request.user.is_authenticated() and request.method == "POST" and not is_me:
        
        # @@@ some of this should go in zwitschern itself
        
        if request.POST["action"] == "follow":
            Following.objects.follow(request.user, other_user)
            is_following = True
            request.user.message_set.create(message=_("You are now following %(other_user)s") % {'other_user': other_user})
            if notification:
                notification.send([other_user], "tweet_follow", {"user": request.user})
        elif request.POST["action"] == "unfollow":
            Following.objects.unfollow(request.user, other_user)
            is_following = False
            request.user.message_set.create(message=_("You have stopped following %(other_user)s") % {'other_user': other_user})
    
    """if is_friend:
        invite_form = None
        previous_invitations_to = None
        previous_invitations_from = None
    else:
        if request.user.is_authenticated() and request.method == "POST":
            if request.POST["action"] == "invite":
                invite_form = InviteFriendForm(request.user, request.POST)
                if invite_form.is_valid():
                    invite_form.save()
            else:
                invite_form = InviteFriendForm(request.user, {
                    'to_user': username,
                    'message': ugettext("Let's be friends!"),
                })
                if request.POST["action"] == "accept": # @@@ perhaps the form should just post to friends and be redirected here
                    invitation_id = request.POST["invitation"]
                    try:
                        invitation = FriendshipInvitation.objects.get(id=invitation_id)
                        if invitation.to_user == request.user:
                            invitation.accept()
                            request.user.message_set.create(message=_("You have accepted the friendship request from %(from_user)s") % {'from_user': invitation.from_user})
                            is_friend = True
                            other_friends = Friendship.objects.friends_for_user(other_user)
                    except FriendshipInvitation.DoesNotExist:
                        pass
        else:
            invite_form = InviteFriendForm(request.user, {
                'to_user': username,
                'message': ugettext("Let's be friends!"),
            })
    previous_invitations_to = FriendshipInvitation.objects.filter(to_user=other_user, from_user=request.user)
    previous_invitations_from = FriendshipInvitation.objects.filter(to_user=request.user, from_user=other_user)"""
    
    if is_me:
        if request.method == "POST":
            if request.POST["action"] == "update":
                profile_form = ProfileForm(request.POST, instance=other_user.get_profile())
                if profile_form.is_valid():
                    profile = profile_form.save(commit=False)
                    profile.user = other_user
                    profile.save()
            else:
                profile_form = ProfileForm(instance=other_user.get_profile())
        else:
            profile_form = ProfileForm(instance=other_user.get_profile())
    else:
        profile_form = None

    return render_to_response(template_name, {
        "profile_form": profile_form,
        "is_me": is_me,
        #"is_friend": is_friend,
        #"is_following": is_following,
        "other_user": other_user,
        #"other_friends": other_friends,
        #"invite_form": invite_form,
        #"previous_invitations_to": previous_invitations_to,
        #"previous_invitations_from": previous_invitations_from,
    }, context_instance=RequestContext(request))

def username_autocomplete(request):
    if request.user.is_authenticated():
        q = request.GET.get("q")
        friends = Friendship.objects.friends_for_user(request.user)
        content = []
        for friendship in friends:
            if friendship["friend"].username.lower().startswith(q):
                try:
                    profile = friendship["friend"].get_profile()
                    entry = "%s,,%s,,%s" % (
                        gravatar(friendship["friend"], 40),
                        friendship["friend"].username,
                        profile.location
                    )
                except Profile.DoesNotExist:
                    pass
                content.append(entry)
        response = HttpResponse("\n".join(content))
    else:
        response = HttpResponseForbidden()
    setattr(response, "djangologging.suppress_output", True)
    return response
########NEW FILE########
__FILENAME__ = reference
'''
Reference tzinfo implementations from the Python docs.
Used for testing against as they are only correct for the years
1987 to 2006. Do not use these for real code.
'''

from datetime import tzinfo, timedelta, datetime
from pytz import utc, UTC, HOUR, ZERO

# A class building tzinfo objects for fixed-offset time zones.
# Note that FixedOffset(0, "UTC") is a different way to build a
# UTC tzinfo object.

class FixedOffset(tzinfo):
    """Fixed offset in minutes east from UTC."""

    def __init__(self, offset, name):
        self.__offset = timedelta(minutes = offset)
        self.__name = name

    def utcoffset(self, dt):
        return self.__offset

    def tzname(self, dt):
        return self.__name

    def dst(self, dt):
        return ZERO

# A class capturing the platform's idea of local time.

import time as _time

STDOFFSET = timedelta(seconds = -_time.timezone)
if _time.daylight:
    DSTOFFSET = timedelta(seconds = -_time.altzone)
else:
    DSTOFFSET = STDOFFSET

DSTDIFF = DSTOFFSET - STDOFFSET

class LocalTimezone(tzinfo):

    def utcoffset(self, dt):
        if self._isdst(dt):
            return DSTOFFSET
        else:
            return STDOFFSET

    def dst(self, dt):
        if self._isdst(dt):
            return DSTDIFF
        else:
            return ZERO

    def tzname(self, dt):
        return _time.tzname[self._isdst(dt)]

    def _isdst(self, dt):
        tt = (dt.year, dt.month, dt.day,
              dt.hour, dt.minute, dt.second,
              dt.weekday(), 0, -1)
        stamp = _time.mktime(tt)
        tt = _time.localtime(stamp)
        return tt.tm_isdst > 0

Local = LocalTimezone()

# A complete implementation of current DST rules for major US time zones.

def first_sunday_on_or_after(dt):
    days_to_go = 6 - dt.weekday()
    if days_to_go:
        dt += timedelta(days_to_go)
    return dt

# In the US, DST starts at 2am (standard time) on the first Sunday in April.
DSTSTART = datetime(1, 4, 1, 2)
# and ends at 2am (DST time; 1am standard time) on the last Sunday of Oct.
# which is the first Sunday on or after Oct 25.
DSTEND = datetime(1, 10, 25, 1)

class USTimeZone(tzinfo):

    def __init__(self, hours, reprname, stdname, dstname):
        self.stdoffset = timedelta(hours=hours)
        self.reprname = reprname
        self.stdname = stdname
        self.dstname = dstname

    def __repr__(self):
        return self.reprname

    def tzname(self, dt):
        if self.dst(dt):
            return self.dstname
        else:
            return self.stdname

    def utcoffset(self, dt):
        return self.stdoffset + self.dst(dt)

    def dst(self, dt):
        if dt is None or dt.tzinfo is None:
            # An exception may be sensible here, in one or both cases.
            # It depends on how you want to treat them.  The default
            # fromutc() implementation (called by the default astimezone()
            # implementation) passes a datetime with dt.tzinfo is self.
            return ZERO
        assert dt.tzinfo is self

        # Find first Sunday in April & the last in October.
        start = first_sunday_on_or_after(DSTSTART.replace(year=dt.year))
        end = first_sunday_on_or_after(DSTEND.replace(year=dt.year))

        # Can't compare naive to aware objects, so strip the timezone from
        # dt first.
        if start <= dt.replace(tzinfo=None) < end:
            return HOUR
        else:
            return ZERO

Eastern  = USTimeZone(-5, "Eastern",  "EST", "EDT")
Central  = USTimeZone(-6, "Central",  "CST", "CDT")
Mountain = USTimeZone(-7, "Mountain", "MST", "MDT")
Pacific  = USTimeZone(-8, "Pacific",  "PST", "PDT")


########NEW FILE########
__FILENAME__ = test_docs
# -*- coding: ascii -*-

import unittest, os, os.path, sys
from doctest import DocTestSuite

# We test the documentation this way instead of using DocFileSuite so
# we can run the tests under Python 2.3
def test_README():
    pass

this_dir = os.path.dirname(__file__)
locs = [
    os.path.join(this_dir, os.pardir, 'README.txt'),
    os.path.join(this_dir, os.pardir, os.pardir, 'README.txt'),
    ]
for loc in locs:
    if os.path.exists(loc):
        test_README.__doc__ = open(loc).read()
        break
if test_README.__doc__ is None:
    raise RuntimeError('README.txt not found')


def test_suite():
    "For the Z3 test runner"
    return DocTestSuite()


if __name__ == '__main__':
    sys.path.insert(0, os.path.abspath(os.path.join(
        this_dir, os.pardir, os.pardir
        )))
    unittest.main(defaultTest='test_suite')



########NEW FILE########
__FILENAME__ = test_tzinfo
# -*- coding: ascii -*-

import sys, os, os.path
import unittest, doctest
import cPickle as pickle
from datetime import datetime, tzinfo, timedelta

if __name__ == '__main__':
    # Only munge path if invoked as a script. Testrunners should have setup
    # the paths already
    sys.path.insert(0, os.path.abspath(os.path.join(os.pardir, os.pardir)))

import pytz
from pytz import reference

# I test for expected version to ensure the correct version of pytz is
# actually being tested.
EXPECTED_VERSION='2008i'

fmt = '%Y-%m-%d %H:%M:%S %Z%z'

NOTIME = timedelta(0)

# GMT is a tzinfo.StaticTzInfo--the class we primarily want to test--while
# UTC is reference implementation.  They both have the same timezone meaning.
UTC = pytz.timezone('UTC')
GMT = pytz.timezone('GMT')

class BasicTest(unittest.TestCase):

    def testVersion(self):
        # Ensuring the correct version of pytz has been loaded
        self.failUnlessEqual(EXPECTED_VERSION, pytz.__version__,
                'Incorrect pytz version loaded. Import path is stuffed '
                'or this test needs updating. (Wanted %s, got %s)'
                % (EXPECTED_VERSION, pytz.__version__)
                )

    def testGMT(self):
        now = datetime.now(tz=GMT)
        self.failUnless(now.utcoffset() == NOTIME)
        self.failUnless(now.dst() == NOTIME)
        self.failUnless(now.timetuple() == now.utctimetuple())
        self.failUnless(now==now.replace(tzinfo=UTC))

    def testReferenceUTC(self):
        now = datetime.now(tz=UTC)
        self.failUnless(now.utcoffset() == NOTIME)
        self.failUnless(now.dst() == NOTIME)
        self.failUnless(now.timetuple() == now.utctimetuple())


class PicklingTest(unittest.TestCase):

    def _roundtrip_tzinfo(self, tz):
        p = pickle.dumps(tz)
        unpickled_tz = pickle.loads(p)
        self.failUnless(tz is unpickled_tz, '%s did not roundtrip' % tz.zone)

    def _roundtrip_datetime(self, dt):
        # Ensure that the tzinfo attached to a datetime instance
        # is identical to the one returned. This is important for
        # DST timezones, as some state is stored in the tzinfo.
        tz = dt.tzinfo
        p = pickle.dumps(dt)
        unpickled_dt = pickle.loads(p)
        unpickled_tz = unpickled_dt.tzinfo
        self.failUnless(tz is unpickled_tz, '%s did not roundtrip' % tz.zone)

    def testDst(self):
        tz = pytz.timezone('Europe/Amsterdam')
        dt = datetime(2004, 2, 1, 0, 0, 0)

        for localized_tz in tz._tzinfos.values():
            self._roundtrip_tzinfo(localized_tz)
            self._roundtrip_datetime(dt.replace(tzinfo=localized_tz))

    def testRoundtrip(self):
        dt = datetime(2004, 2, 1, 0, 0, 0)
        for zone in pytz.all_timezones:
            tz = pytz.timezone(zone)
            self._roundtrip_tzinfo(tz)

    def testDatabaseFixes(self):
        # Hack the pickle to make it refer to a timezone abbreviation
        # that does not match anything. The unpickler should be able
        # to repair this case
        tz = pytz.timezone('Australia/Melbourne')
        p = pickle.dumps(tz)
        tzname = tz._tzname
        hacked_p = p.replace(tzname, '???')
        self.failIfEqual(p, hacked_p)
        unpickled_tz = pickle.loads(hacked_p)
        self.failUnless(tz is unpickled_tz)

        # Simulate a database correction. In this case, the incorrect
        # data will continue to be used.
        p = pickle.dumps(tz)
        new_utcoffset = tz._utcoffset.seconds + 42
        hacked_p = p.replace(str(tz._utcoffset.seconds), str(new_utcoffset))
        self.failIfEqual(p, hacked_p)
        unpickled_tz = pickle.loads(hacked_p)
        self.failUnlessEqual(unpickled_tz._utcoffset.seconds, new_utcoffset)
        self.failUnless(tz is not unpickled_tz)

    def testOldPickles(self):
        # Ensure that applications serializing pytz instances as pickles
        # have no troubles upgrading to a new pytz release. These pickles
        # where created with pytz2006j
        east1 = pickle.loads(
                "cpytz\n_p\np1\n(S'US/Eastern'\np2\nI-18000\n"
                "I0\nS'EST'\np3\ntRp4\n."
                )
        east2 = pytz.timezone('US/Eastern')
        self.failUnless(east1 is east2)

        # Confirm changes in name munging between 2006j and 2007c cause
        # no problems.
        pap1 = pickle.loads(
                "cpytz\n_p\np1\n(S'America/Port_minus_au_minus_Prince'"
                "\np2\nI-17340\nI0\nS'PPMT'\np3\ntRp4\n."
                )
        pap2 = pytz.timezone('America/Port-au-Prince')
        self.failUnless(pap1 is pap2)

        gmt1 = pickle.loads("cpytz\n_p\np1\n(S'Etc/GMT_plus_10'\np2\ntRp3\n.")
        gmt2 = pytz.timezone('Etc/GMT+10')
        self.failUnless(gmt1 is gmt2)


class USEasternDSTStartTestCase(unittest.TestCase):
    tzinfo = pytz.timezone('US/Eastern')

    # 24 hours before DST changeover
    transition_time = datetime(2002, 4, 7, 7, 0, 0, tzinfo=UTC)

    # Increase for 'flexible' DST transitions due to 1 minute granularity
    # of Python's datetime library
    instant = timedelta(seconds=1)

    # before transition
    before = {
        'tzname': 'EST',
        'utcoffset': timedelta(hours = -5),
        'dst': timedelta(hours = 0),
        }

    # after transition
    after = {
        'tzname': 'EDT',
        'utcoffset': timedelta(hours = -4),
        'dst': timedelta(hours = 1),
        }

    def _test_tzname(self, utc_dt, wanted):
        tzname = wanted['tzname']
        dt = utc_dt.astimezone(self.tzinfo)
        self.failUnlessEqual(dt.tzname(), tzname,
            'Expected %s as tzname for %s. Got %s' % (
                tzname, str(utc_dt), dt.tzname()
                )
            )

    def _test_utcoffset(self, utc_dt, wanted):
        utcoffset = wanted['utcoffset']
        dt = utc_dt.astimezone(self.tzinfo)
        self.failUnlessEqual(
                dt.utcoffset(), wanted['utcoffset'],
                'Expected %s as utcoffset for %s. Got %s' % (
                    utcoffset, utc_dt, dt.utcoffset()
                    )
                )

    def _test_dst(self, utc_dt, wanted):
        dst = wanted['dst']
        dt = utc_dt.astimezone(self.tzinfo)
        self.failUnlessEqual(dt.dst(),dst,
            'Expected %s as dst for %s. Got %s' % (
                dst, utc_dt, dt.dst()
                )
            )

    def test_arithmetic(self):
        utc_dt = self.transition_time

        for days in range(-420, 720, 20):
            delta = timedelta(days=days)

            # Make sure we can get back where we started
            dt = utc_dt.astimezone(self.tzinfo)
            dt2 = dt + delta
            dt2 = dt2 - delta
            self.failUnlessEqual(dt, dt2)

            # Make sure arithmetic crossing DST boundaries ends
            # up in the correct timezone after normalization
            self.failUnlessEqual(
                    (utc_dt + delta).astimezone(self.tzinfo).strftime(fmt),
                    self.tzinfo.normalize(dt + delta).strftime(fmt),
                    'Incorrect result for delta==%d days.  Wanted %r. Got %r'%(
                        days,
                        (utc_dt + delta).astimezone(self.tzinfo).strftime(fmt),
                        self.tzinfo.normalize(dt + delta).strftime(fmt),
                        )
                    )

    def _test_all(self, utc_dt, wanted):
        self._test_utcoffset(utc_dt, wanted)
        self._test_tzname(utc_dt, wanted)
        self._test_dst(utc_dt, wanted)

    def testDayBefore(self):
        self._test_all(
                self.transition_time - timedelta(days=1), self.before
                )

    def testTwoHoursBefore(self):
        self._test_all(
                self.transition_time - timedelta(hours=2), self.before
                )

    def testHourBefore(self):
        self._test_all(
                self.transition_time - timedelta(hours=1), self.before
                )

    def testInstantBefore(self):
        self._test_all(
                self.transition_time - self.instant, self.before
                )

    def testTransition(self):
        self._test_all(
                self.transition_time, self.after
                )

    def testInstantAfter(self):
        self._test_all(
                self.transition_time + self.instant, self.after
                )

    def testHourAfter(self):
        self._test_all(
                self.transition_time + timedelta(hours=1), self.after
                )

    def testTwoHoursAfter(self):
        self._test_all(
                self.transition_time + timedelta(hours=1), self.after
                )

    def testDayAfter(self):
        self._test_all(
                self.transition_time + timedelta(days=1), self.after
                )


class USEasternDSTEndTestCase(USEasternDSTStartTestCase):
    tzinfo = pytz.timezone('US/Eastern')
    transition_time = datetime(2002, 10, 27, 6, 0, 0, tzinfo=UTC)
    before = {
        'tzname': 'EDT',
        'utcoffset': timedelta(hours = -4),
        'dst': timedelta(hours = 1),
        }
    after = {
        'tzname': 'EST',
        'utcoffset': timedelta(hours = -5),
        'dst': timedelta(hours = 0),
        }


class USEasternEPTStartTestCase(USEasternDSTStartTestCase):
    transition_time = datetime(1945, 8, 14, 23, 0, 0, tzinfo=UTC)
    before = {
        'tzname': 'EWT',
        'utcoffset': timedelta(hours = -4),
        'dst': timedelta(hours = 1),
        }
    after = {
        'tzname': 'EPT',
        'utcoffset': timedelta(hours = -4),
        'dst': timedelta(hours = 1),
        }


class USEasternEPTEndTestCase(USEasternDSTStartTestCase):
    transition_time = datetime(1945, 9, 30, 6, 0, 0, tzinfo=UTC)
    before = {
        'tzname': 'EPT',
        'utcoffset': timedelta(hours = -4),
        'dst': timedelta(hours = 1),
        }
    after = {
        'tzname': 'EST',
        'utcoffset': timedelta(hours = -5),
        'dst': timedelta(hours = 0),
        }


class WarsawWMTEndTestCase(USEasternDSTStartTestCase):
    # In 1915, Warsaw changed from Warsaw to Central European time.
    # This involved the clocks being set backwards, causing a end-of-DST
    # like situation without DST being involved.
    tzinfo = pytz.timezone('Europe/Warsaw')
    transition_time = datetime(1915, 8, 4, 22, 36, 0, tzinfo=UTC)
    before = {
        'tzname': 'WMT',
        'utcoffset': timedelta(hours=1, minutes=24),
        'dst': timedelta(0),
        }
    after = {
        'tzname': 'CET',
        'utcoffset': timedelta(hours=1),
        'dst': timedelta(0),
        }


class VilniusWMTEndTestCase(USEasternDSTStartTestCase):
    # At the end of 1916, Vilnius changed timezones putting its clock
    # forward by 11 minutes 35 seconds. Neither timezone was in DST mode.
    tzinfo = pytz.timezone('Europe/Vilnius')
    instant = timedelta(seconds=31)
    transition_time = datetime(1916, 12, 31, 22, 36, 00, tzinfo=UTC)
    before = {
        'tzname': 'WMT',
        'utcoffset': timedelta(hours=1, minutes=24),
        'dst': timedelta(0),
        }
    after = {
        'tzname': 'KMT',
        'utcoffset': timedelta(hours=1, minutes=36), # Really 1:35:36
        'dst': timedelta(0),
        }


class ReferenceUSEasternDSTStartTestCase(USEasternDSTStartTestCase):
    tzinfo = reference.Eastern
    def test_arithmetic(self):
        # Reference implementation cannot handle this
        pass


class ReferenceUSEasternDSTEndTestCase(USEasternDSTEndTestCase):
    tzinfo = reference.Eastern

    def testHourBefore(self):
        # Python's datetime library has a bug, where the hour before
        # a daylight savings transition is one hour out. For example,
        # at the end of US/Eastern daylight savings time, 01:00 EST
        # occurs twice (once at 05:00 UTC and once at 06:00 UTC),
        # whereas the first should actually be 01:00 EDT.
        # Note that this bug is by design - by accepting this ambiguity
        # for one hour one hour per year, an is_dst flag on datetime.time
        # became unnecessary.
        self._test_all(
                self.transition_time - timedelta(hours=1), self.after
                )

    def testInstantBefore(self):
        self._test_all(
                self.transition_time - timedelta(seconds=1), self.after
                )

    def test_arithmetic(self):
        # Reference implementation cannot handle this
        pass


class LocalTestCase(unittest.TestCase):
    def testLocalize(self):
        loc_tz = pytz.timezone('Europe/Amsterdam')

        loc_time = loc_tz.localize(datetime(1930, 5, 10, 0, 0, 0))
        # Actually +00:19:32, but Python datetime rounds this
        self.failUnlessEqual(loc_time.strftime('%Z%z'), 'AMT+0020')

        loc_time = loc_tz.localize(datetime(1930, 5, 20, 0, 0, 0))
        # Actually +00:19:32, but Python datetime rounds this
        self.failUnlessEqual(loc_time.strftime('%Z%z'), 'NST+0120')

        loc_time = loc_tz.localize(datetime(1940, 5, 10, 0, 0, 0))
        self.failUnlessEqual(loc_time.strftime('%Z%z'), 'NET+0020')

        loc_time = loc_tz.localize(datetime(1940, 5, 20, 0, 0, 0))
        self.failUnlessEqual(loc_time.strftime('%Z%z'), 'CEST+0200')

        loc_time = loc_tz.localize(datetime(2004, 2, 1, 0, 0, 0))
        self.failUnlessEqual(loc_time.strftime('%Z%z'), 'CET+0100')

        loc_time = loc_tz.localize(datetime(2004, 4, 1, 0, 0, 0))
        self.failUnlessEqual(loc_time.strftime('%Z%z'), 'CEST+0200')

        tz = pytz.timezone('Europe/Amsterdam')
        loc_time = loc_tz.localize(datetime(1943, 3, 29, 1, 59, 59))
        self.failUnlessEqual(loc_time.strftime('%Z%z'), 'CET+0100')


        # Switch to US
        loc_tz = pytz.timezone('US/Eastern')

        # End of DST ambiguity check
        loc_time = loc_tz.localize(datetime(1918, 10, 27, 1, 59, 59), is_dst=1)
        self.failUnlessEqual(loc_time.strftime('%Z%z'), 'EDT-0400')

        loc_time = loc_tz.localize(datetime(1918, 10, 27, 1, 59, 59), is_dst=0)
        self.failUnlessEqual(loc_time.strftime('%Z%z'), 'EST-0500')

        self.failUnlessRaises(pytz.AmbiguousTimeError,
            loc_tz.localize, datetime(1918, 10, 27, 1, 59, 59), is_dst=None
            )

        # Start of DST non-existent times
        loc_time = loc_tz.localize(datetime(1918, 3, 31, 2, 0, 0), is_dst=0)
        self.failUnlessEqual(loc_time.strftime('%Z%z'), 'EST-0500')

        loc_time = loc_tz.localize(datetime(1918, 3, 31, 2, 0, 0), is_dst=1)
        self.failUnlessEqual(loc_time.strftime('%Z%z'), 'EDT-0400')

        self.failUnlessRaises(pytz.NonExistentTimeError,
            loc_tz.localize, datetime(1918, 3, 31, 2, 0, 0), is_dst=None
            )

        # Weird changes - war time and peace time both is_dst==True

        loc_time = loc_tz.localize(datetime(1942, 2, 9, 3, 0, 0))
        self.failUnlessEqual(loc_time.strftime('%Z%z'), 'EWT-0400')

        loc_time = loc_tz.localize(datetime(1945, 8, 14, 19, 0, 0))
        self.failUnlessEqual(loc_time.strftime('%Z%z'), 'EPT-0400')

        loc_time = loc_tz.localize(datetime(1945, 9, 30, 1, 0, 0), is_dst=1)
        self.failUnlessEqual(loc_time.strftime('%Z%z'), 'EPT-0400')

        loc_time = loc_tz.localize(datetime(1945, 9, 30, 1, 0, 0), is_dst=0)
        self.failUnlessEqual(loc_time.strftime('%Z%z'), 'EST-0500')

    def testNormalize(self):
        tz = pytz.timezone('US/Eastern')
        dt = datetime(2004, 4, 4, 7, 0, 0, tzinfo=UTC).astimezone(tz)
        dt2 = dt - timedelta(minutes=10)
        self.failUnlessEqual(
                dt2.strftime('%Y-%m-%d %H:%M:%S %Z%z'),
                '2004-04-04 02:50:00 EDT-0400'
                )

        dt2 = tz.normalize(dt2)
        self.failUnlessEqual(
                dt2.strftime('%Y-%m-%d %H:%M:%S %Z%z'),
                '2004-04-04 01:50:00 EST-0500'
                )

    def testPartialMinuteOffsets(self):
        # utcoffset in Amsterdam was not a whole minute until 1937
        # However, we fudge this by rounding them, as the Python
        # datetime library 
        tz = pytz.timezone('Europe/Amsterdam')
        utc_dt = datetime(1914, 1, 1, 13, 40, 28, tzinfo=UTC) # correct
        utc_dt = utc_dt.replace(second=0) # But we need to fudge it
        loc_dt = utc_dt.astimezone(tz)
        self.failUnlessEqual(
                loc_dt.strftime('%Y-%m-%d %H:%M:%S %Z%z'),
                '1914-01-01 14:00:00 AMT+0020'
                )

        # And get back...
        utc_dt = loc_dt.astimezone(UTC)
        self.failUnlessEqual(
                utc_dt.strftime('%Y-%m-%d %H:%M:%S %Z%z'),
                '1914-01-01 13:40:00 UTC+0000'
                )

    def no_testCreateLocaltime(self):
        # It would be nice if this worked, but it doesn't.
        tz = pytz.timezone('Europe/Amsterdam')
        dt = datetime(2004, 10, 31, 2, 0, 0, tzinfo=tz)
        self.failUnlessEqual(
                dt.strftime(fmt),
                '2004-10-31 02:00:00 CET+0100'
                )

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite('pytz'))
    suite.addTest(doctest.DocTestSuite('pytz.tzinfo'))
    import test_tzinfo
    suite.addTest(unittest.defaultTestLoader.loadTestsFromModule(test_tzinfo))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')


########NEW FILE########
__FILENAME__ = tzfile
#!/usr/bin/env python
'''
$Id: tzfile.py,v 1.8 2004/06/03 00:15:24 zenzen Exp $
'''

from cStringIO import StringIO
from datetime import datetime, timedelta
from struct import unpack, calcsize

from pytz.tzinfo import StaticTzInfo, DstTzInfo, memorized_ttinfo
from pytz.tzinfo import memorized_datetime, memorized_timedelta


def build_tzinfo(zone, fp):
    head_fmt = '>4s 16x 6l'
    head_size = calcsize(head_fmt)
    (magic,ttisgmtcnt,ttisstdcnt,leapcnt,
     timecnt,typecnt,charcnt) =  unpack(head_fmt, fp.read(head_size))
    
    # Make sure it is a tzinfo(5) file
    assert magic == 'TZif'

    # Read out the transition times, localtime indices and ttinfo structures.
    data_fmt = '>%(timecnt)dl %(timecnt)dB %(ttinfo)s %(charcnt)ds' % dict(
        timecnt=timecnt, ttinfo='lBB'*typecnt, charcnt=charcnt)
    data_size = calcsize(data_fmt)
    data = unpack(data_fmt, fp.read(data_size))

    # make sure we unpacked the right number of values
    assert len(data) == 2 * timecnt + 3 * typecnt + 1
    transitions = [memorized_datetime(trans)
                   for trans in data[:timecnt]]
    lindexes = list(data[timecnt:2 * timecnt])
    ttinfo_raw = data[2 * timecnt:-1]
    tznames_raw = data[-1]
    del data

    # Process ttinfo into separate structs
    ttinfo = []
    tznames = {}
    i = 0
    while i < len(ttinfo_raw):
        # have we looked up this timezone name yet?
        tzname_offset = ttinfo_raw[i+2]
        if tzname_offset not in tznames:
            nul = tznames_raw.find('\0', tzname_offset)
            if nul < 0:
                nul = len(tznames_raw)
            tznames[tzname_offset] = tznames_raw[tzname_offset:nul]
        ttinfo.append((ttinfo_raw[i],
                       bool(ttinfo_raw[i+1]),
                       tznames[tzname_offset]))
        i += 3

    # Now build the timezone object
    if len(transitions) == 0:
        ttinfo[0][0], ttinfo[0][2]
        cls = type(zone, (StaticTzInfo,), dict(
            zone=zone,
            _utcoffset=memorized_timedelta(ttinfo[0][0]),
            _tzname=ttinfo[0][2]))
    else:
        # Early dates use the first standard time ttinfo
        i = 0
        while ttinfo[i][1]:
            i += 1
        if ttinfo[i] == ttinfo[lindexes[0]]:
            transitions[0] = datetime.min
        else:
            transitions.insert(0, datetime.min)
            lindexes.insert(0, i)

        # calculate transition info
        transition_info = []
        for i in range(len(transitions)):
            inf = ttinfo[lindexes[i]]
            utcoffset = inf[0]
            if not inf[1]:
                dst = 0
            else:
                for j in range(i-1, -1, -1):
                    prev_inf = ttinfo[lindexes[j]]
                    if not prev_inf[1]:
                        break
                dst = inf[0] - prev_inf[0] # dst offset
            tzname = inf[2]

            # Round utcoffset and dst to the nearest minute or the
            # datetime library will complain. Conversions to these timezones
            # might be up to plus or minus 30 seconds out, but it is
            # the best we can do.
            utcoffset = int((utcoffset + 30) / 60) * 60
            dst = int((dst + 30) / 60) * 60
            transition_info.append(memorized_ttinfo(utcoffset, dst, tzname))

        cls = type(zone, (DstTzInfo,), dict(
            zone=zone,
            _utc_transition_times=transitions,
            _transition_info=transition_info))

    return cls()

if __name__ == '__main__':
    import os.path
    from pprint import pprint
    base = os.path.join(os.path.dirname(__file__), 'zoneinfo')
    tz = build_tzinfo('Australia/Melbourne',
                      open(os.path.join(base,'Australia','Melbourne'), 'rb'))
    tz = build_tzinfo('US/Eastern',
                      open(os.path.join(base,'US','Eastern'), 'rb'))
    pprint(tz._utc_transition_times)
    #print tz.asPython(4)
    #print tz.transitions_mapping

########NEW FILE########
__FILENAME__ = tzinfo
'''Base classes and helpers for building zone specific tzinfo classes'''

from datetime import datetime, timedelta, tzinfo
from bisect import bisect_right
try:
    set
except NameError:
    from sets import Set as set

import pytz

__all__ = []

_timedelta_cache = {}
def memorized_timedelta(seconds):
    '''Create only one instance of each distinct timedelta'''
    try:
        return _timedelta_cache[seconds]
    except KeyError:
        delta = timedelta(seconds=seconds)
        _timedelta_cache[seconds] = delta
        return delta

_epoch = datetime.utcfromtimestamp(0)
_datetime_cache = {0: _epoch}
def memorized_datetime(seconds):
    '''Create only one instance of each distinct datetime'''
    try:
        return _datetime_cache[seconds]
    except KeyError:
        # NB. We can't just do datetime.utcfromtimestamp(seconds) as this
        # fails with negative values under Windows (Bug #90096)
        dt = _epoch + timedelta(seconds=seconds)
        _datetime_cache[seconds] = dt
        return dt

_ttinfo_cache = {}
def memorized_ttinfo(*args):
    '''Create only one instance of each distinct tuple'''
    try:
        return _ttinfo_cache[args]
    except KeyError:
        ttinfo = (
                memorized_timedelta(args[0]),
                memorized_timedelta(args[1]),
                args[2]
                )
        _ttinfo_cache[args] = ttinfo
        return ttinfo

_notime = memorized_timedelta(0)

def _to_seconds(td):
    '''Convert a timedelta to seconds'''
    return td.seconds + td.days * 24 * 60 * 60


class BaseTzInfo(tzinfo):
    # Overridden in subclass
    _utcoffset = None
    _tzname = None
    zone = None

    def __str__(self):
        return self.zone


class StaticTzInfo(BaseTzInfo):
    '''A timezone that has a constant offset from UTC

    These timezones are rare, as most regions have changed their
    offset from UTC at some point in their history
    '''
    def fromutc(self, dt):
        '''See datetime.tzinfo.fromutc'''
        return (dt + self._utcoffset).replace(tzinfo=self)
    
    def utcoffset(self,dt):
        '''See datetime.tzinfo.utcoffset'''
        return self._utcoffset

    def dst(self,dt):
        '''See datetime.tzinfo.dst'''
        return _notime

    def tzname(self,dt):
        '''See datetime.tzinfo.tzname'''
        return self._tzname

    def localize(self, dt, is_dst=False):
        '''Convert naive time to local time'''
        if dt.tzinfo is not None:
            raise ValueError, 'Not naive datetime (tzinfo is already set)'
        return dt.replace(tzinfo=self)

    def normalize(self, dt, is_dst=False):
        '''Correct the timezone information on the given datetime'''
        if dt.tzinfo is None:
            raise ValueError, 'Naive time - no tzinfo set'
        return dt.replace(tzinfo=self)

    def __repr__(self):
        return '<StaticTzInfo %r>' % (self.zone,)

    def __reduce__(self):
        # Special pickle to zone remains a singleton and to cope with
        # database changes. 
        return pytz._p, (self.zone,)


class DstTzInfo(BaseTzInfo):
    '''A timezone that has a variable offset from UTC
   
    The offset might change if daylight savings time comes into effect,
    or at a point in history when the region decides to change their 
    timezone definition. 

    '''
    # Overridden in subclass
    _utc_transition_times = None # Sorted list of DST transition times in UTC
    _transition_info = None # [(utcoffset, dstoffset, tzname)] corresponding
                            # to _utc_transition_times entries
    zone = None

    # Set in __init__
    _tzinfos = None
    _dst = None # DST offset

    def __init__(self, _inf=None, _tzinfos=None):
        if _inf:
            self._tzinfos = _tzinfos
            self._utcoffset, self._dst, self._tzname = _inf
        else:
            _tzinfos = {}
            self._tzinfos = _tzinfos
            self._utcoffset, self._dst, self._tzname = self._transition_info[0]
            _tzinfos[self._transition_info[0]] = self
            for inf in self._transition_info[1:]:
                if not _tzinfos.has_key(inf):
                    _tzinfos[inf] = self.__class__(inf, _tzinfos)

    def fromutc(self, dt):
        '''See datetime.tzinfo.fromutc'''
        dt = dt.replace(tzinfo=None)
        idx = max(0, bisect_right(self._utc_transition_times, dt) - 1)
        inf = self._transition_info[idx]
        return (dt + inf[0]).replace(tzinfo=self._tzinfos[inf])

    def normalize(self, dt):
        '''Correct the timezone information on the given datetime

        If date arithmetic crosses DST boundaries, the tzinfo
        is not magically adjusted. This method normalizes the
        tzinfo to the correct one.

        To test, first we need to do some setup

        >>> from pytz import timezone
        >>> utc = timezone('UTC')
        >>> eastern = timezone('US/Eastern')
        >>> fmt = '%Y-%m-%d %H:%M:%S %Z (%z)'

        We next create a datetime right on an end-of-DST transition point,
        the instant when the wallclocks are wound back one hour.

        >>> utc_dt = datetime(2002, 10, 27, 6, 0, 0, tzinfo=utc)
        >>> loc_dt = utc_dt.astimezone(eastern)
        >>> loc_dt.strftime(fmt)
        '2002-10-27 01:00:00 EST (-0500)'

        Now, if we subtract a few minutes from it, note that the timezone
        information has not changed.

        >>> before = loc_dt - timedelta(minutes=10)
        >>> before.strftime(fmt)
        '2002-10-27 00:50:00 EST (-0500)'

        But we can fix that by calling the normalize method

        >>> before = eastern.normalize(before)
        >>> before.strftime(fmt)
        '2002-10-27 01:50:00 EDT (-0400)'

        '''
        if dt.tzinfo is None:
            raise ValueError, 'Naive time - no tzinfo set'

        # Convert dt in localtime to UTC
        offset = dt.tzinfo._utcoffset
        dt = dt.replace(tzinfo=None)
        dt = dt - offset
        # convert it back, and return it
        return self.fromutc(dt)

    def localize(self, dt, is_dst=False):
        '''Convert naive time to local time.
        
        This method should be used to construct localtimes, rather
        than passing a tzinfo argument to a datetime constructor.

        is_dst is used to determine the correct timezone in the ambigous
        period at the end of daylight savings time.
        
        >>> from pytz import timezone
        >>> fmt = '%Y-%m-%d %H:%M:%S %Z (%z)'
        >>> amdam = timezone('Europe/Amsterdam')
        >>> dt  = datetime(2004, 10, 31, 2, 0, 0)
        >>> loc_dt1 = amdam.localize(dt, is_dst=True)
        >>> loc_dt2 = amdam.localize(dt, is_dst=False)
        >>> loc_dt1.strftime(fmt)
        '2004-10-31 02:00:00 CEST (+0200)'
        >>> loc_dt2.strftime(fmt)
        '2004-10-31 02:00:00 CET (+0100)'
        >>> str(loc_dt2 - loc_dt1)
        '1:00:00'

        Use is_dst=None to raise an AmbiguousTimeError for ambiguous
        times at the end of daylight savings

        >>> loc_dt1 = amdam.localize(dt, is_dst=None)
        Traceback (most recent call last):
            [...]
        AmbiguousTimeError: 2004-10-31 02:00:00

        is_dst defaults to False
        
        >>> amdam.localize(dt) == amdam.localize(dt, False)
        True

        is_dst is also used to determine the correct timezone in the
        wallclock times jumped over at the start of daylight savings time.

        >>> pacific = timezone('US/Pacific')
        >>> dt = datetime(2008, 3, 9, 2, 0, 0)
        >>> ploc_dt1 = pacific.localize(dt, is_dst=True)
        >>> ploc_dt2 = pacific.localize(dt, is_dst=False)
        >>> ploc_dt1.strftime(fmt)
        '2008-03-09 02:00:00 PDT (-0700)'
        >>> ploc_dt2.strftime(fmt)
        '2008-03-09 02:00:00 PST (-0800)'
        >>> str(ploc_dt2 - ploc_dt1)
        '1:00:00'

        Use is_dst=None to raise a NonExistentTimeError for these skipped
        times.

        >>> loc_dt1 = pacific.localize(dt, is_dst=None)
        Traceback (most recent call last):
            [...]
        NonExistentTimeError: 2008-03-09 02:00:00
        '''
        if dt.tzinfo is not None:
            raise ValueError, 'Not naive datetime (tzinfo is already set)'

        # Find the possibly correct timezones. We probably just have one,
        # but we might end up with two if we are in the end-of-DST
        # transition period. Or possibly more in some particularly confused
        # location...
        possible_loc_dt = set()
        for tzinfo in self._tzinfos.values():
            loc_dt = tzinfo.normalize(dt.replace(tzinfo=tzinfo))
            if loc_dt.replace(tzinfo=None) == dt:
                possible_loc_dt.add(loc_dt)

        if len(possible_loc_dt) == 1:
            return possible_loc_dt.pop()

        # If there are no possibly correct timezones, we are attempting
        # to convert a time that never happened - the time period jumped
        # during the start-of-DST transition period.
        if len(possible_loc_dt) == 0:
            # If we refuse to guess, raise an exception.
            if is_dst is None:
                raise NonExistentTimeError(dt)

            # If we are forcing the pre-DST side of the DST transition, we
            # obtain the correct timezone by winding the clock forward a few
            # hours.
            elif is_dst:
                return self.localize(
                    dt + timedelta(hours=6), is_dst=True) - timedelta(hours=6)

            # If we are forcing the post-DST side of the DST transition, we
            # obtain the correct timezone by winding the clock back.
            else:
                return self.localize(
                    dt - timedelta(hours=6), is_dst=False) + timedelta(hours=6)


        # If we get this far, we have multiple possible timezones - this
        # is an ambiguous case occuring during the end-of-DST transition.

        # If told to be strict, raise an exception since we have an
        # ambiguous case
        if is_dst is None:
            raise AmbiguousTimeError(dt)

        # Filter out the possiblilities that don't match the requested
        # is_dst
        filtered_possible_loc_dt = [
            p for p in possible_loc_dt
                if bool(p.tzinfo._dst) == is_dst
            ]

        # Hopefully we only have one possibility left. Return it.
        if len(filtered_possible_loc_dt) == 1:
            return filtered_possible_loc_dt[0]

        if len(filtered_possible_loc_dt) == 0:
            filtered_possible_loc_dt = list(possible_loc_dt)

        # If we get this far, we have in a wierd timezone transition
        # where the clocks have been wound back but is_dst is the same
        # in both (eg. Europe/Warsaw 1915 when they switched to CET).
        # At this point, we just have to guess unless we allow more
        # hints to be passed in (such as the UTC offset or abbreviation),
        # but that is just getting silly.
        #
        # Choose the earliest (by UTC) applicable timezone.
        def mycmp(a,b):
            return cmp(
                    a.replace(tzinfo=None) - a.tzinfo._utcoffset,
                    b.replace(tzinfo=None) - b.tzinfo._utcoffset,
                    )
        filtered_possible_loc_dt.sort(mycmp)
        return filtered_possible_loc_dt[0]
        
    def utcoffset(self, dt):
        '''See datetime.tzinfo.utcoffset'''
        return self._utcoffset

    def dst(self, dt):
        '''See datetime.tzinfo.dst'''
        return self._dst

    def tzname(self, dt):
        '''See datetime.tzinfo.tzname'''
        return self._tzname

    def __repr__(self):
        if self._dst:
            dst = 'DST'
        else:
            dst = 'STD'
        if self._utcoffset > _notime:
            return '<DstTzInfo %r %s+%s %s>' % (
                    self.zone, self._tzname, self._utcoffset, dst
                )
        else:
            return '<DstTzInfo %r %s%s %s>' % (
                    self.zone, self._tzname, self._utcoffset, dst
                )

    def __reduce__(self):
        # Special pickle to zone remains a singleton and to cope with
        # database changes.
        return pytz._p, (
                self.zone,
                _to_seconds(self._utcoffset),
                _to_seconds(self._dst),
                self._tzname
                )


class InvalidTimeError(Exception):
    '''Base class for invalid time exceptions.'''


class AmbiguousTimeError(InvalidTimeError):
    '''Exception raised when attempting to create an ambiguous wallclock time.

    At the end of a DST transition period, a particular wallclock time will
    occur twice (once before the clocks are set back, once after). Both
    possibilities may be correct, unless further information is supplied.

    See DstTzInfo.normalize() for more info
    '''


class NonExistentTimeError(InvalidTimeError):
    '''Exception raised when attempting to create a wallclock time that
    cannot exist.

    At the start of a DST transition period, the wallclock time jumps forward.
    The instants jumped over never occur.
    '''


def unpickler(zone, utcoffset=None, dstoffset=None, tzname=None):
    """Factory function for unpickling pytz tzinfo instances.
    
    This is shared for both StaticTzInfo and DstTzInfo instances, because
    database changes could cause a zones implementation to switch between
    these two base classes and we can't break pickles on a pytz version
    upgrade.
    """
    # Raises a KeyError if zone no longer exists, which should never happen
    # and would be a bug.
    tz = pytz.timezone(zone)

    # A StaticTzInfo - just return it
    if utcoffset is None:
        return tz

    # This pickle was created from a DstTzInfo. We need to
    # determine which of the list of tzinfo instances for this zone
    # to use in order to restore the state of any datetime instances using
    # it correctly.
    utcoffset = memorized_timedelta(utcoffset)
    dstoffset = memorized_timedelta(dstoffset)
    try:
        return tz._tzinfos[(utcoffset, dstoffset, tzname)]
    except KeyError:
        # The particular state requested in this timezone no longer exists.
        # This indicates a corrupt pickle, or the timezone database has been
        # corrected violently enough to make this particular
        # (utcoffset,dstoffset) no longer exist in the zone, or the
        # abbreviation has been changed.
        pass

    # See if we can find an entry differing only by tzname. Abbreviations
    # get changed from the initial guess by the database maintainers to
    # match reality when this information is discovered.
    for localized_tz in tz._tzinfos.values():
        if (localized_tz._utcoffset == utcoffset
                and localized_tz._dst == dstoffset):
            return localized_tz

    # This (utcoffset, dstoffset) information has been removed from the
    # zone. Add it back. This might occur when the database maintainers have
    # corrected incorrect information. datetime instances using this
    # incorrect information will continue to do so, exactly as they were
    # before being pickled. This is purely an overly paranoid safety net - I
    # doubt this will ever been needed in real life.
    inf = (utcoffset, dstoffset, tzname)
    tz._tzinfos[inf] = tz.__class__(inf, tz._tzinfos)
    return tz._tzinfos[inf]


########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from registration.models import RegistrationProfile


class RegistrationAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'activation_key_expired')
    search_fields = ('user__username', 'user__first_name')


admin.site.register(RegistrationProfile, RegistrationAdmin)

########NEW FILE########
__FILENAME__ = delete_expired_users
"""
A script which removes expired/inactive user accounts from the
database.

This is intended to be run as a cron job; for example, to have it run
at midnight each Sunday, you could add lines like the following to
your crontab::

    DJANGO_SETTINGS_MODULE=yoursite.settings
    0 0 * * sun python /path/to/registration/bin/delete_expired_users.py

See the method ``delete_expired_users`` of the ``RegistrationManager``
class in ``registration/models.py`` for further documentation.

"""

if __name__ == '__main__':
    from registration.models import RegistrationProfile
    RegistrationProfile.objects.delete_expired_users()

########NEW FILE########
__FILENAME__ = forms
"""
Forms and validation code for user registration.

"""


from django import forms
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User

from registration.models import RegistrationProfile


# I put this on all required fields, because it's easier to pick up
# on them with CSS or JavaScript if they have a class of "required"
# in the HTML. Your mileage may vary. If/when Django ticket #3515
# lands in trunk, this will no longer be necessary.
attrs_dict = { 'class': 'required' }


class RegistrationForm(forms.Form):
    """
    Form for registering a new user account.
    
    Validates that the requested username is not already in use, and
    requires the password to be entered twice to catch typos.
    
    Subclasses should feel free to add any additional validation they
    need, but should either preserve the base ``save()`` or implement
    a ``save()`` which accepts the ``profile_callback`` keyword
    argument and passes it through to
    ``RegistrationProfile.objects.create_inactive_user()``.
    
    """
    username = forms.RegexField(regex=r'^\w+$',
                                max_length=30,
                                widget=forms.TextInput(attrs=attrs_dict),
                                label=_(u'username'))
    email = forms.EmailField(widget=forms.TextInput(attrs=dict(attrs_dict,
                                                               maxlength=75)),
                             label=_(u'email address'))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs=attrs_dict, render_value=False),
                                label=_(u'password'))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs=attrs_dict, render_value=False),
                                label=_(u'password (again)'))
    
    def clean_username(self):
        """
        Validate that the username is alphanumeric and is not already
        in use.
        
        """
        try:
            user = User.objects.get(username__iexact=self.cleaned_data['username'])
        except User.DoesNotExist:
            return self.cleaned_data['username']
        raise forms.ValidationError(_(u'This username is already taken. Please choose another.'))

    def clean(self):
        """
        Verifiy that the values entered into the two password fields
        match. Note that an error here will end up in
        ``non_field_errors()`` because it doesn't apply to a single
        field.
        
        """
        if 'password1' in self.cleaned_data and 'password2' in self.cleaned_data:
            if self.cleaned_data['password1'] != self.cleaned_data['password2']:
                raise forms.ValidationError(_(u'You must type the same password each time'))
        return self.cleaned_data
    
    def save(self, profile_callback=None):
        """
        Create the new ``User`` and ``RegistrationProfile``, and
        returns the ``User``.
        
        This is essentially a light wrapper around
        ``RegistrationProfile.objects.create_inactive_user()``,
        feeding it the form data and a profile callback (see the
        documentation on ``create_inactive_user()`` for details) if
        supplied.
        
        """
        new_user = RegistrationProfile.objects.create_inactive_user(username=self.cleaned_data['username'],
                                                                    password=self.cleaned_data['password1'],
                                                                    email=self.cleaned_data['email'],
                                                                    profile_callback=profile_callback)
        return new_user


class RegistrationFormTermsOfService(RegistrationForm):
    """
    Subclass of ``RegistrationForm`` which adds a required checkbox
    for agreeing to a site's Terms of Service.
    
    """
    tos = forms.BooleanField(widget=forms.CheckboxInput(attrs=attrs_dict),
                             label=_(u'I have read and agree to the Terms of Service'))
    
    def clean_tos(self):
        """
        Validate that the user accepted the Terms of Service.
        
        """
        if self.cleaned_data.get('tos', False):
            return self.cleaned_data['tos']
        raise forms.ValidationError(_(u'You must agree to the terms to register'))


class RegistrationFormUniqueEmail(RegistrationForm):
    """
    Subclass of ``RegistrationForm`` which enforces uniqueness of
    email addresses.
    
    """
    def clean_email(self):
        """
        Validate that the supplied email address is unique for the
        site.
        
        """
        if User.objects.filter(email__iexact=self.cleaned_data['email']):
            raise forms.ValidationError(_(u'This email address is already in use. Please supply a different email address.'))
        return self.cleaned_data['email']


class RegistrationFormNoFreeEmail(RegistrationForm):
    """
    Subclass of ``RegistrationForm`` which disallows registration with
    email addresses from popular free webmail services; moderately
    useful for preventing automated spam registrations.
    
    To change the list of banned domains, subclass this form and
    override the attribute ``bad_domains``.
    
    """
    bad_domains = ['aim.com', 'aol.com', 'email.com', 'gmail.com',
                   'googlemail.com', 'hotmail.com', 'hushmail.com',
                   'msn.com', 'mail.ru', 'mailinator.com', 'live.com']
    
    def clean_email(self):
        """
        Check the supplied email address against a list of known free
        webmail domains.
        
        """
        email_domain = self.cleaned_data['email'].split('@')[1]
        if email_domain in self.bad_domains:
            raise forms.ValidationError(_(u'Registration using free email addresses is prohibited. Please supply a different email address.'))
        return self.cleaned_data['email']

########NEW FILE########
__FILENAME__ = cleanupregistration
"""
A management command which deletes expired accounts (e.g.,
accounts which signed up but never activated) from the database.

Calls ``RegistrationProfile.objects.delete_expired_users()``, which
contains the actual logic for determining which accounts are deleted.

"""

from django.core.management.base import NoArgsCommand
from django.core.management.base import CommandError

from registration.models import RegistrationProfile


class Command(NoArgsCommand):
    help = "Delete expired user registrations from the database"

    def handle_noargs(self, **options):
        RegistrationProfile.objects.delete_expired_users()

########NEW FILE########
__FILENAME__ = models
import datetime
import random
import re
import sha

from django.conf import settings
from django.db import models
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from django.contrib.sites.models import Site


SHA1_RE = re.compile('^[a-f0-9]{40}$')


class RegistrationManager(models.Manager):
    """
    Custom manager for the ``RegistrationProfile`` model.
    
    The methods defined here provide shortcuts for account creation
    and activation (including generation and emailing of activation
    keys), and for cleaning out expired inactive accounts.
    
    """
    def activate_user(self, activation_key):
        """
        Validate an activation key and activate the corresponding
        ``User`` if valid.
        
        If the key is valid and has not expired, return the ``User``
        after activating.
        
        If the key is not valid or has expired, return ``False``.
        
        If the key is valid but the ``User`` is already active,
        return ``False``.
        
        To prevent reactivation of an account which has been
        deactivated by site administrators, the activation key is
        reset to the string ``ALREADY_ACTIVATED`` after successful
        activation.
        
        """
        # Make sure the key we're trying conforms to the pattern of a
        # SHA1 hash; if it doesn't, no point trying to look it up in
        # the database.
        if SHA1_RE.search(activation_key):
            try:
                profile = self.get(activation_key=activation_key)
            except self.model.DoesNotExist:
                return False
            if not profile.activation_key_expired():
                user = profile.user
                user.is_active = True
                user.save()
                profile.activation_key = "ALREADY_ACTIVATED"
                profile.save()
                return user
        return False
    
    def create_inactive_user(self, username, password, email,
                             send_email=True, profile_callback=None):
        """
        Create a new, inactive ``User``, generates a
        ``RegistrationProfile`` and email its activation key to the
        ``User``, returning the new ``User``.
        
        To disable the email, call with ``send_email=False``.
        
        To enable creation of a custom user profile along with the
        ``User`` (e.g., the model specified in the
        ``AUTH_PROFILE_MODULE`` setting), define a function which
        knows how to create and save an instance of that model with
        appropriate default values, and pass it as the keyword
        argument ``profile_callback``. This function should accept one
        keyword argument:

        ``user``
            The ``User`` to relate the profile to.
        
        """
        new_user = User.objects.create_user(username, email, password)
        new_user.is_active = False
        new_user.save()
        
        registration_profile = self.create_profile(new_user)
        
        if profile_callback is not None:
            profile_callback(user=new_user)
        
        if send_email:
            from django.core.mail import send_mail
            current_site = Site.objects.get_current()
            
            subject = render_to_string('registration/activation_email_subject.txt',
                                       { 'site': current_site })
            # Email subject *must not* contain newlines
            subject = ''.join(subject.splitlines())
            
            message = render_to_string('registration/activation_email.txt',
                                       { 'activation_key': registration_profile.activation_key,
                                         'expiration_days': settings.ACCOUNT_ACTIVATION_DAYS,
                                         'site': current_site })
            
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [new_user.email])
        return new_user
    
    def create_profile(self, user):
        """
        Create a ``RegistrationProfile`` for a given
        ``User``, and return the ``RegistrationProfile``.
        
        The activation key for the ``RegistrationProfile`` will be a
        SHA1 hash, generated from a combination of the ``User``'s
        username and a random salt.
        
        """
        salt = sha.new(str(random.random())).hexdigest()[:5]
        activation_key = sha.new(salt+user.username).hexdigest()
        return self.create(user=user,
                           activation_key=activation_key)
        
    def delete_expired_users(self):
        """
        Remove expired instances of ``RegistrationProfile`` and their
        associated ``User``s.
        
        Accounts to be deleted are identified by searching for
        instances of ``RegistrationProfile`` with expired activation
        keys, and then checking to see if their associated ``User``
        instances have the field ``is_active`` set to ``False``; any
        ``User`` who is both inactive and has an expired activation
        key will be deleted.
        
        It is recommended that this method be executed regularly as
        part of your routine site maintenance; this application
        provides a custom management command which will call this
        method, accessible as ``manage.py cleanupregistration``.
        
        Regularly clearing out accounts which have never been
        activated serves two useful purposes:
        
        1. It alleviates the ocasional need to reset a
           ``RegistrationProfile`` and/or re-send an activation email
           when a user does not receive or does not act upon the
           initial activation email; since the account will be
           deleted, the user will be able to simply re-register and
           receive a new activation key.
        
        2. It prevents the possibility of a malicious user registering
           one or more accounts and never activating them (thus
           denying the use of those usernames to anyone else); since
           those accounts will be deleted, the usernames will become
           available for use again.
        
        If you have a troublesome ``User`` and wish to disable their
        account while keeping it in the database, simply delete the
        associated ``RegistrationProfile``; an inactive ``User`` which
        does not have an associated ``RegistrationProfile`` will not
        be deleted.
        
        """
        for profile in self.all():
            if profile.activation_key_expired():
                user = profile.user
                if not user.is_active:
                    user.delete()


class RegistrationProfile(models.Model):
    """
    A simple profile which stores an activation key for use during
    user account registration.
    
    Generally, you will not want to interact directly with instances
    of this model; the provided manager includes methods
    for creating and activating new accounts, as well as for cleaning
    out accounts which have never been activated.
    
    While it is possible to use this model as the value of the
    ``AUTH_PROFILE_MODULE`` setting, it's not recommended that you do
    so. This model's sole purpose is to store data temporarily during
    account registration and activation, and a mechanism for
    automatically creating an instance of a site-specific profile
    model is provided via the ``create_inactive_user`` on
    ``RegistrationManager``.
    
    """
    user = models.ForeignKey(User, unique=True, verbose_name=_('user'))
    activation_key = models.CharField(_('activation key'), max_length=40)
    
    objects = RegistrationManager()
    
    class Meta:
        verbose_name = _('registration profile')
        verbose_name_plural = _('registration profiles')
    
    def __unicode__(self):
        return u"Registration information for %s" % self.user
    
    def activation_key_expired(self):
        """
        Determine whether this ``RegistrationProfile``'s activation
        key has expired, returning a boolean -- ``True`` if the key
        has expired.
        
        Key expiration is determined by a two-step process:
        
        1. If the user has already activated, the key will have been
           reset to the string ``ALREADY_ACTIVATED``. Re-activating is
           not permitted, and so this method returns ``True`` in this
           case.

        2. Otherwise, the date the user signed up is incremented by
           the number of days specified in the setting
           ``ACCOUNT_ACTIVATION_DAYS`` (which should be the number of
           days after signup during which a user is allowed to
           activate their account); if the result is less than or
           equal to the current date, the key has expired and this
           method returns ``True``.
        
        """
        expiration_date = datetime.timedelta(days=settings.ACCOUNT_ACTIVATION_DAYS)
        return self.activation_key == "ALREADY_ACTIVATED" or \
               (self.user.date_joined + expiration_date <= datetime.datetime.now())
    activation_key_expired.boolean = True

########NEW FILE########
__FILENAME__ = urls
"""
URLConf for Django user registration and authentication.

Recommended usage is a call to ``include()`` in your project's root
URLConf to include this URLConf for any URL beginning with
``/accounts/``.

"""


from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template
from django.contrib.auth import views as auth_views

from registration.views import activate
from registration.views import register


urlpatterns = patterns('',
                       # Activation keys get matched by \w+ instead of the more specific
                       # [a-fA-F0-9]{40} because a bad activation key should still get to the view;
                       # that way it can return a sensible "invalid key" message instead of a
                       # confusing 404.
                       url(r'^activate/(?P<activation_key>\w+)/$',
                           activate,
                           name='registration_activate'),
                       url(r'^login/$',
                           auth_views.login,
                           {'template_name': 'registration/login.html'},
                           name='auth_login'),
                       url(r'^logout/$',
                           auth_views.logout,
                           {'template_name': 'registration/logout.html'},
                           name='auth_logout'),
                       url(r'^password/change/$',
                           auth_views.password_change,
                           name='auth_password_change'),
                       url(r'^password/change/done/$',
                           auth_views.password_change_done,
                           name='auth_password_change_done'),
                       url(r'^password/reset/$',
                           auth_views.password_reset,
                           name='auth_password_reset'),
                       url(r'^password/reset/confirm/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$',
                           auth_views.password_reset_confirm,
                           name='auth_password_reset_confirm'),
                       url(r'^password/reset/complete/$',
                           auth_views.password_reset_complete,
                           name='auth_password_reset_complete'),
                       url(r'^password/reset/done/$',
                           auth_views.password_reset_done,
                           name='auth_password_reset_done'),
                       url(r'^register/$',
                           register,
                           name='registration_register'),
                       url(r'^register/complete/$',
                           direct_to_template,
                           {'template': 'registration/registration_complete.html'},
                           name='registration_complete'),
                       )

########NEW FILE########
__FILENAME__ = views
"""
Views which allow users to create and activate accounts.

"""


from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext

from registration.forms import RegistrationForm
from registration.models import RegistrationProfile


def activate(request, activation_key,
             template_name='registration/activate.html',
             extra_context=None):
    """
    Activate a ``User``'s account from an activation key, if their key
    is valid and hasn't expired.
    
    By default, use the template ``registration/activate.html``; to
    change this, pass the name of a template as the keyword argument
    ``template_name``.
    
    **Required arguments**
    
    ``activation_key``
       The activation key to validate and use for activating the
       ``User``.
    
    **Optional arguments**
       
    ``extra_context``
        A dictionary of variables to add to the template context. Any
        callable object in this dictionary will be called to produce
        the end result which appears in the context.
    
    ``template_name``
        A custom template to use.
    
    **Context:**
    
    ``account``
        The ``User`` object corresponding to the account, if the
        activation was successful. ``False`` if the activation was not
        successful.
    
    ``expiration_days``
        The number of days for which activation keys stay valid after
        registration.
    
    Any extra variables supplied in the ``extra_context`` argument
    (see above).
    
    **Template:**
    
    registration/activate.html or ``template_name`` keyword argument.
    
    """
    activation_key = activation_key.lower() # Normalize before trying anything with it.
    account = RegistrationProfile.objects.activate_user(activation_key)
    if extra_context is None:
        extra_context = {}
    context = RequestContext(request)
    for key, value in extra_context.items():
        context[key] = callable(value) and value() or value
    return render_to_response(template_name,
                              { 'account': account,
                                'expiration_days': settings.ACCOUNT_ACTIVATION_DAYS },
                              context_instance=context)


def register(request, success_url=None,
             form_class=RegistrationForm, profile_callback=None,
             template_name='registration/registration_form.html',
             extra_context=None):
    """
    Allow a new user to register an account.
    
    Following successful registration, issue a redirect; by default,
    this will be whatever URL corresponds to the named URL pattern
    ``registration_complete``, which will be
    ``/accounts/register/complete/`` if using the included URLConf. To
    change this, point that named pattern at another URL, or pass your
    preferred URL as the keyword argument ``success_url``.
    
    By default, ``registration.forms.RegistrationForm`` will be used
    as the registration form; to change this, pass a different form
    class as the ``form_class`` keyword argument. The form class you
    specify must have a method ``save`` which will create and return
    the new ``User``, and that method must accept the keyword argument
    ``profile_callback`` (see below).
    
    To enable creation of a site-specific user profile object for the
    new user, pass a function which will create the profile object as
    the keyword argument ``profile_callback``. See
    ``RegistrationManager.create_inactive_user`` in the file
    ``models.py`` for details on how to write this function.
    
    By default, use the template
    ``registration/registration_form.html``; to change this, pass the
    name of a template as the keyword argument ``template_name``.
    
    **Required arguments**
    
    None.
    
    **Optional arguments**
    
    ``form_class``
        The form class to use for registration.
    
    ``extra_context``
        A dictionary of variables to add to the template context. Any
        callable object in this dictionary will be called to produce
        the end result which appears in the context.
    
    ``profile_callback``
        A function which will be used to create a site-specific
        profile instance for the new ``User``.
    
    ``success_url``
        The URL to redirect to on successful registration.
    
    ``template_name``
        A custom template to use.
    
    **Context:**
    
    ``form``
        The registration form.
    
    Any extra variables supplied in the ``extra_context`` argument
    (see above).
    
    **Template:**
    
    registration/registration_form.html or ``template_name`` keyword
    argument.
    
    """
    if request.method == 'POST':
        form = form_class(data=request.POST, files=request.FILES)
        if form.is_valid():
            new_user = form.save(profile_callback=profile_callback)
            # success_url needs to be dynamically generated here; setting a
            # a default value using reverse() will cause circular-import
            # problems with the default URLConf for this application, which
            # imports this file.
            return HttpResponseRedirect(success_url or reverse('registration_complete'))
    else:
        form = form_class()
    
    if extra_context is None:
        extra_context = {}
    context = RequestContext(request)
    for key, value in extra_context.items():
        context[key] = callable(value) and value() or value
    return render_to_response(template_name,
                              { 'form': form },
                              context_instance=context)

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from tagging.models import Tag, TaggedItem

admin.site.register(TaggedItem)
admin.site.register(Tag)

########NEW FILE########
__FILENAME__ = fields
"""
A custom Model Field for tagging.
"""
from django.db.models import signals
from django.db.models.fields import CharField
from django.utils.translation import ugettext_lazy as _

from tagging import settings
from tagging.models import Tag
from tagging.utils import edit_string_for_tags

class TagField(CharField):
    """
    A "special" character field that actually works as a relationship to tags
    "under the hood". This exposes a space-separated string of tags, but does
    the splitting/reordering/etc. under the hood.
    """
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = kwargs.get('max_length', 255)
        kwargs['blank'] = kwargs.get('blank', True)
        super(TagField, self).__init__(*args, **kwargs)

    def contribute_to_class(self, cls, name):
        super(TagField, self).contribute_to_class(cls, name)

        # Make this object the descriptor for field access.
        setattr(cls, self.name, self)

        # Save tags back to the database post-save
        signals.post_save.connect(self._save, cls, True)

    def __get__(self, instance, owner=None):
        """
        Tag getter. Returns an instance's tags if accessed on an instance, and
        all of a model's tags if called on a class. That is, this model::

           class Link(models.Model):
               ...
               tags = TagField()

        Lets you do both of these::

           >>> l = Link.objects.get(...)
           >>> l.tags
           'tag1 tag2 tag3'

           >>> Link.tags
           'tag1 tag2 tag3 tag4'

        """
        # Handle access on the model (i.e. Link.tags)
        if instance is None:
            return edit_string_for_tags(Tag.objects.usage_for_model(owner))

        tags = self._get_instance_tag_cache(instance)
        if tags is None:
            if instance.pk is None:
                self._set_instance_tag_cache(instance, '')
            else:
                self._set_instance_tag_cache(
                    instance, edit_string_for_tags(Tag.objects.get_for_object(instance)))
        return self._get_instance_tag_cache(instance)

    def __set__(self, instance, value):
        """
        Set an object's tags.
        """
        if instance is None:
            raise AttributeError(_('%s can only be set on instances.') % self.name)
        if settings.FORCE_LOWERCASE_TAGS and value is not None:
            value = value.lower()
        self._set_instance_tag_cache(instance, value)

    def _save(self, **kwargs): #signal, sender, instance):
        """
        Save tags back to the database
        """
        tags = self._get_instance_tag_cache(kwargs['instance'])
        if tags is not None:
            Tag.objects.update_tags(kwargs['instance'], tags)

    def __delete__(self, instance):
        """
        Clear all of an object's tags.
        """
        self._set_instance_tag_cache(instance, '')

    def _get_instance_tag_cache(self, instance):
        """
        Helper: get an instance's tag cache.
        """
        return getattr(instance, '_%s_cache' % self.attname, None)

    def _set_instance_tag_cache(self, instance, tags):
        """
        Helper: set an instance's tag cache.
        """
        setattr(instance, '_%s_cache' % self.attname, tags)

    def get_internal_type(self):
        return 'CharField'

    def formfield(self, **kwargs):
        from tagging import forms
        defaults = {'form_class': forms.TagField}
        defaults.update(kwargs)
        return super(TagField, self).formfield(**defaults)

########NEW FILE########
__FILENAME__ = forms
"""
Tagging components for Django's ``newforms`` form library.
"""
from django import forms
from django.utils.translation import ugettext as _

from tagging import settings
from tagging.models import Tag
from tagging.validators import is_tag, is_tag_list
from tagging.utils import parse_tag_input

class AdminTagForm(forms.ModelForm):
    class Meta:
        model = Tag
    
    def clean_name(self):
        value = self.cleaned_data["name"]
        return is_tag(value)
        

class TagField(forms.CharField):
    """
    A ``CharField`` which validates that its input is a valid list of
    tag names.
    """
    def clean(self, value):
        value = super(TagField, self).clean(value)
        if value == u'':
            return value
        return is_tag_list(value)

########NEW FILE########
__FILENAME__ = generic
from django.contrib.contenttypes.models import ContentType

def fetch_content_objects(tagged_items, select_related_for=None):
    """
    Retrieves ``ContentType`` and content objects for the given list of
    ``TaggedItems``, grouping the retrieval of content objects by model
    type to reduce the number of queries executed.

    This results in ``number_of_content_types + 1`` queries rather than
    the ``number_of_tagged_items * 2`` queries you'd get by iterating
    over the list and accessing each item's ``object`` attribute.

    A ``select_related_for`` argument can be used to specify a list of
    of model names (corresponding to the ``model`` field of a
    ``ContentType``) for which ``select_related`` should be used when
    retrieving model instances.
    """
    if select_related_for is None: select_related_for = []

    # Group content object pks by their content type pks
    objects = {}
    for item in tagged_items:
        objects.setdefault(item.content_type_id, []).append(item.object_id)

    # Retrieve content types and content objects in bulk
    content_types = ContentType._default_manager.in_bulk(objects.keys())
    for content_type_pk, object_pks in objects.iteritems():
        model = content_types[content_type_pk].model_class()
        if content_types[content_type_pk].model in select_related_for:
            objects[content_type_pk] = model._default_manager.select_related().in_bulk(object_pks)
        else:
            objects[content_type_pk] = model._default_manager.in_bulk(object_pks)

    # Set content types and content objects in the appropriate cache
    # attributes, so accessing the 'content_type' and 'object'
    # attributes on each tagged item won't result in further database
    # hits.
    for item in tagged_items:
        item._object_cache = objects[item.content_type_id][item.object_id]
        item._content_type_cache = content_types[item.content_type_id]

########NEW FILE########
__FILENAME__ = managers
"""
Custom managers for Django models registered with the tagging
application.
"""
from django.contrib.contenttypes.models import ContentType
from django.db import models

from tagging.models import Tag, TaggedItem

class ModelTagManager(models.Manager):
    """
    A manager for retrieving tags for a particular model.
    """
    def get_query_set(self):
        ctype = ContentType.objects.get_for_model(self.model)
        return Tag.objects.filter(
            items__content_type__pk=ctype.pk).distinct()

    def cloud(self, *args, **kwargs):
        return Tag.objects.cloud_for_model(self.model, *args, **kwargs)

    def related(self, tags, *args, **kwargs):
        return Tag.objects.related_for_model(tags, self.model, *args, **kwargs)

    def usage(self, *args, **kwargs):
        return Tag.objects.usage_for_model(self.model, *arg, **kwargs)

class ModelTaggedItemManager(models.Manager):
    """
    A manager for retrieving model instances based on their tags.
    """
    def related_to(self, obj, queryset=None, num=None):
        if queryset is None:
            return TaggedItem.objects.get_related(obj, self.model, num=num)
        else:
            return TaggedItem.objects.get_related(obj, queryset, num=num)

    def with_all(self, tags, queryset=None):
        if queryset is None:
            return TaggedItem.objects.get_by_model(self.model, tags)
        else:
            return TaggedItem.objects.get_by_model(queryset, tags)

    def with_any(self, tags, queryset=None):
        if queryset is None:
            return TaggedItem.objects.get_union_by_model(self.model, tags)
        else:
            return TaggedItem.objects.get_union_by_model(queryset, tags)

class TagDescriptor(object):
    """
    A descriptor which provides access to a ``ModelTagManager`` for
    model classes and simple retrieval, updating and deletion of tags
    for model instances.
    """
    def __get__(self, instance, owner):
        if not instance:
            tag_manager = ModelTagManager()
            tag_manager.model = owner
            return tag_manager
        else:
            return Tag.objects.get_for_object(instance)

    def __set__(self, instance, value):
        Tag.objects.update_tags(instance, value)

    def __delete__(self, instance):
        Tag.objects.update_tags(instance, None)

########NEW FILE########
__FILENAME__ = models
"""
Models and managers for generic tagging.
"""
# Python 2.3 compatibility
try:
    set
except NameError:
    from sets import Set as set

from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import connection, models
from django.db.models.query import QuerySet
from django.utils.translation import ugettext_lazy as _

from tagging import settings
from tagging.utils import calculate_cloud, get_tag_list, get_queryset_and_model, parse_tag_input
from tagging.utils import LOGARITHMIC

qn = connection.ops.quote_name

try:
    from django.db.models.query import parse_lookup
except ImportError:
    parse_lookup = None

############
# Managers #
############

class TagManager(models.Manager):
    def update_tags(self, obj, tag_names):
        """
        Update tags associated with an object.
        """
        ctype = ContentType.objects.get_for_model(obj)
        current_tags = list(self.filter(items__content_type__pk=ctype.pk,
                                        items__object_id=obj.pk))
        updated_tag_names = parse_tag_input(tag_names)
        if settings.FORCE_LOWERCASE_TAGS:
            updated_tag_names = [t.lower() for t in updated_tag_names]

        # Remove tags which no longer apply
        tags_for_removal = [tag for tag in current_tags \
                            if tag.name not in updated_tag_names]
        if len(tags_for_removal):
            TaggedItem._default_manager.filter(content_type__pk=ctype.pk,
                                               object_id=obj.pk,
                                               tag__in=tags_for_removal).delete()
        # Add new tags
        current_tag_names = [tag.name for tag in current_tags]
        for tag_name in updated_tag_names:
            if tag_name not in current_tag_names:
                tag, created = self.get_or_create(name=tag_name)
                TaggedItem._default_manager.create(tag=tag, object=obj)

    def add_tag(self, obj, tag_name):
        """
        Associates the given object with a tag.
        """
        tag_names = parse_tag_input(tag_name)
        if not len(tag_names):
            raise AttributeError(_('No tags were given: "%s".') % tag_name)
        if len(tag_names) > 1:
            raise AttributeError(_('Multiple tags were given: "%s".') % tag_name)
        tag_name = tag_names[0]
        if settings.FORCE_LOWERCASE_TAGS:
            tag_name = tag_name.lower()
        tag, created = self.get_or_create(name=tag_name)
        ctype = ContentType.objects.get_for_model(obj)
        TaggedItem._default_manager.get_or_create(
            tag=tag, content_type=ctype, object_id=obj.pk)

    def get_for_object(self, obj):
        """
        Create a queryset matching all tags associated with the given
        object.
        """
        ctype = ContentType.objects.get_for_model(obj)
        return self.filter(items__content_type__pk=ctype.pk,
                           items__object_id=obj.pk)

    def _get_usage(self, model, counts=False, min_count=None, extra_joins=None, extra_criteria=None, params=None):
        """
        Perform the custom SQL query for ``usage_for_model`` and
        ``usage_for_queryset``.
        """
        if min_count is not None: counts = True

        model_table = qn(model._meta.db_table)
        model_pk = '%s.%s' % (model_table, qn(model._meta.pk.column))
        query = """
        SELECT DISTINCT %(tag)s.id, %(tag)s.name%(count_sql)s
        FROM
            %(tag)s
            INNER JOIN %(tagged_item)s
                ON %(tag)s.id = %(tagged_item)s.tag_id
            INNER JOIN %(model)s
                ON %(tagged_item)s.object_id = %(model_pk)s
            %%s
        WHERE %(tagged_item)s.content_type_id = %(content_type_id)s
            %%s
        GROUP BY %(tag)s.id, %(tag)s.name
        %%s
        ORDER BY %(tag)s.name ASC""" % {
            'tag': qn(self.model._meta.db_table),
            'count_sql': counts and (', COUNT(%s)' % model_pk) or '',
            'tagged_item': qn(TaggedItem._meta.db_table),
            'model': model_table,
            'model_pk': model_pk,
            'content_type_id': ContentType.objects.get_for_model(model).pk,
        }

        min_count_sql = ''
        if min_count is not None:
            min_count_sql = 'HAVING COUNT(%s) >= %%s' % model_pk
            params.append(min_count)

        cursor = connection.cursor()
        cursor.execute(query % (extra_joins, extra_criteria, min_count_sql), params)
        tags = []
        for row in cursor.fetchall():
            t = self.model(*row[:2])
            if counts:
                t.count = row[2]
            tags.append(t)
        return tags

    def usage_for_model(self, model, counts=False, min_count=None, filters=None):
        """
        Obtain a list of tags associated with instances of the given
        Model class.

        If ``counts`` is True, a ``count`` attribute will be added to
        each tag, indicating how many times it has been used against
        the Model class in question.

        If ``min_count`` is given, only tags which have a ``count``
        greater than or equal to ``min_count`` will be returned.
        Passing a value for ``min_count`` implies ``counts=True``.

        To limit the tags (and counts, if specified) returned to those
        used by a subset of the Model's instances, pass a dictionary
        of field lookups to be applied to the given Model as the
        ``filters`` argument.
        """
        if filters is None: filters = {}

        if not parse_lookup:
            # post-queryset-refactor (hand off to usage_for_queryset)
            queryset = model._default_manager.filter()
            for f in filters.items():
                queryset.query.add_filter(f)
            usage = self.usage_for_queryset(queryset, counts, min_count)
        else:
            # pre-queryset-refactor
            extra_joins = ''
            extra_criteria = ''
            params = []
            if len(filters) > 0:
                joins, where, params = parse_lookup(filters.items(), model._meta)
                extra_joins = ' '.join(['%s %s AS %s ON %s' % (join_type, table, alias, condition)
                                        for (alias, (table, join_type, condition)) in joins.items()])
                extra_criteria = 'AND %s' % (' AND '.join(where))
            usage = self._get_usage(model, counts, min_count, extra_joins, extra_criteria, params)

        return usage

    def usage_for_queryset(self, queryset, counts=False, min_count=None):
        """
        Obtain a list of tags associated with instances of a model
        contained in the given queryset.

        If ``counts`` is True, a ``count`` attribute will be added to
        each tag, indicating how many times it has been used against
        the Model class in question.

        If ``min_count`` is given, only tags which have a ``count``
        greater than or equal to ``min_count`` will be returned.
        Passing a value for ``min_count`` implies ``counts=True``.
        """
        if parse_lookup:
            raise AttributeError("'TagManager.usage_for_queryset' is not compatible with pre-queryset-refactor versions of Django.")

        extra_joins = ' '.join(queryset.query.get_from_clause()[0][1:])
        where, params = queryset.query.where.as_sql()
        if where:
            extra_criteria = 'AND %s' % where
        else:
            extra_criteria = ''
        return self._get_usage(queryset.model, counts, min_count, extra_joins, extra_criteria, params)

    def related_for_model(self, tags, model, counts=False, min_count=None):
        """
        Obtain a list of tags related to a given list of tags - that
        is, other tags used by items which have all the given tags.

        If ``counts`` is True, a ``count`` attribute will be added to
        each tag, indicating the number of items which have it in
        addition to the given list of tags.

        If ``min_count`` is given, only tags which have a ``count``
        greater than or equal to ``min_count`` will be returned.
        Passing a value for ``min_count`` implies ``counts=True``.
        """
        if min_count is not None: counts = True
        tags = get_tag_list(tags)
        tag_count = len(tags)
        tagged_item_table = qn(TaggedItem._meta.db_table)
        query = """
        SELECT %(tag)s.id, %(tag)s.name%(count_sql)s
        FROM %(tagged_item)s INNER JOIN %(tag)s ON %(tagged_item)s.tag_id = %(tag)s.id
        WHERE %(tagged_item)s.content_type_id = %(content_type_id)s
          AND %(tagged_item)s.object_id IN
          (
              SELECT %(tagged_item)s.object_id
              FROM %(tagged_item)s, %(tag)s
              WHERE %(tagged_item)s.content_type_id = %(content_type_id)s
                AND %(tag)s.id = %(tagged_item)s.tag_id
                AND %(tag)s.id IN (%(tag_id_placeholders)s)
              GROUP BY %(tagged_item)s.object_id
              HAVING COUNT(%(tagged_item)s.object_id) = %(tag_count)s
          )
          AND %(tag)s.id NOT IN (%(tag_id_placeholders)s)
        GROUP BY %(tag)s.id, %(tag)s.name
        %(min_count_sql)s
        ORDER BY %(tag)s.name ASC""" % {
            'tag': qn(self.model._meta.db_table),
            'count_sql': counts and ', COUNT(%s.object_id)' % tagged_item_table or '',
            'tagged_item': tagged_item_table,
            'content_type_id': ContentType.objects.get_for_model(model).pk,
            'tag_id_placeholders': ','.join(['%s'] * tag_count),
            'tag_count': tag_count,
            'min_count_sql': min_count is not None and ('HAVING COUNT(%s.object_id) >= %%s' % tagged_item_table) or '',
        }

        params = [tag.pk for tag in tags] * 2
        if min_count is not None:
            params.append(min_count)

        cursor = connection.cursor()
        cursor.execute(query, params)
        related = []
        for row in cursor.fetchall():
            tag = self.model(*row[:2])
            if counts is True:
                tag.count = row[2]
            related.append(tag)
        return related

    def cloud_for_model(self, model, steps=4, distribution=LOGARITHMIC,
                        filters=None, min_count=None):
        """
        Obtain a list of tags associated with instances of the given
        Model, giving each tag a ``count`` attribute indicating how
        many times it has been used and a ``font_size`` attribute for
        use in displaying a tag cloud.

        ``steps`` defines the range of font sizes - ``font_size`` will
        be an integer between 1 and ``steps`` (inclusive).

        ``distribution`` defines the type of font size distribution
        algorithm which will be used - logarithmic or linear. It must
        be either ``tagging.utils.LOGARITHMIC`` or
        ``tagging.utils.LINEAR``.

        To limit the tags displayed in the cloud to those associated
        with a subset of the Model's instances, pass a dictionary of
        field lookups to be applied to the given Model as the
        ``filters`` argument.

        To limit the tags displayed in the cloud to those with a
        ``count`` greater than or equal to ``min_count``, pass a value
        for the ``min_count`` argument.
        """
        tags = list(self.usage_for_model(model, counts=True, filters=filters,
                                         min_count=min_count))
        return calculate_cloud(tags, steps, distribution)

class TaggedItemManager(models.Manager):
    """
    FIXME There's currently no way to get the ``GROUP BY`` and ``HAVING``
          SQL clauses required by many of this manager's methods into
          Django's ORM.

          For now, we manually execute a query to retrieve the PKs of
          objects we're interested in, then use the ORM's ``__in``
          lookup to return a ``QuerySet``.

          Once the queryset-refactor branch lands in trunk, this can be
          tidied up significantly.
    """
    def get_by_model(self, queryset_or_model, tags):
        """
        Create a ``QuerySet`` containing instances of the specified
        model associated with a given tag or list of tags.
        """
        tags = get_tag_list(tags)
        tag_count = len(tags)
        if tag_count == 0:
            # No existing tags were given
            queryset, model = get_queryset_and_model(queryset_or_model)
            return model._default_manager.none()
        elif tag_count == 1:
            # Optimisation for single tag - fall through to the simpler
            # query below.
            tag = tags[0]
        else:
            return self.get_intersection_by_model(queryset_or_model, tags)

        queryset, model = get_queryset_and_model(queryset_or_model)
        content_type = ContentType.objects.get_for_model(model)
        opts = self.model._meta
        tagged_item_table = qn(opts.db_table)
        return queryset.extra(
            tables=[opts.db_table],
            where=[
                '%s.content_type_id = %%s' % tagged_item_table,
                '%s.tag_id = %%s' % tagged_item_table,
                '%s.%s = %s.object_id' % (qn(model._meta.db_table),
                                          qn(model._meta.pk.column),
                                          tagged_item_table)
            ],
            params=[content_type.pk, tag.pk],
        )

    def get_intersection_by_model(self, queryset_or_model, tags):
        """
        Create a ``QuerySet`` containing instances of the specified
        model associated with *all* of the given list of tags.
        """
        tags = get_tag_list(tags)
        tag_count = len(tags)
        queryset, model = get_queryset_and_model(queryset_or_model)

        if not tag_count:
            return model._default_manager.none()

        model_table = qn(model._meta.db_table)
        # This query selects the ids of all objects which have all the
        # given tags.
        query = """
        SELECT %(model_pk)s
        FROM %(model)s, %(tagged_item)s
        WHERE %(tagged_item)s.content_type_id = %(content_type_id)s
          AND %(tagged_item)s.tag_id IN (%(tag_id_placeholders)s)
          AND %(model_pk)s = %(tagged_item)s.object_id
        GROUP BY %(model_pk)s
        HAVING COUNT(%(model_pk)s) = %(tag_count)s""" % {
            'model_pk': '%s.%s' % (model_table, qn(model._meta.pk.column)),
            'model': model_table,
            'tagged_item': qn(self.model._meta.db_table),
            'content_type_id': ContentType.objects.get_for_model(model).pk,
            'tag_id_placeholders': ','.join(['%s'] * tag_count),
            'tag_count': tag_count,
        }

        cursor = connection.cursor()
        cursor.execute(query, [tag.pk for tag in tags])
        object_ids = [row[0] for row in cursor.fetchall()]
        if len(object_ids) > 0:
            return queryset.filter(pk__in=object_ids)
        else:
            return model._default_manager.none()

    def get_union_by_model(self, queryset_or_model, tags):
        """
        Create a ``QuerySet`` containing instances of the specified
        model associated with *any* of the given list of tags.
        """
        tags = get_tag_list(tags)
        tag_count = len(tags)
        queryset, model = get_queryset_and_model(queryset_or_model)

        if not tag_count:
            return model._default_manager.none()

        model_table = qn(model._meta.db_table)
        # This query selects the ids of all objects which have any of
        # the given tags.
        query = """
        SELECT %(model_pk)s
        FROM %(model)s, %(tagged_item)s
        WHERE %(tagged_item)s.content_type_id = %(content_type_id)s
          AND %(tagged_item)s.tag_id IN (%(tag_id_placeholders)s)
          AND %(model_pk)s = %(tagged_item)s.object_id
        GROUP BY %(model_pk)s""" % {
            'model_pk': '%s.%s' % (model_table, qn(model._meta.pk.column)),
            'model': model_table,
            'tagged_item': qn(self.model._meta.db_table),
            'content_type_id': ContentType.objects.get_for_model(model).pk,
            'tag_id_placeholders': ','.join(['%s'] * tag_count),
        }

        cursor = connection.cursor()
        cursor.execute(query, [tag.pk for tag in tags])
        object_ids = [row[0] for row in cursor.fetchall()]
        if len(object_ids) > 0:
            return queryset.filter(pk__in=object_ids)
        else:
            return model._default_manager.none()

    def get_related(self, obj, queryset_or_model, num=None):
        """
        Retrieve a list of instances of the specified model which share
        tags with the model instance ``obj``, ordered by the number of
        shared tags in descending order.

        If ``num`` is given, a maximum of ``num`` instances will be
        returned.
        """
        queryset, model = get_queryset_and_model(queryset_or_model)
        model_table = qn(model._meta.db_table)
        content_type = ContentType.objects.get_for_model(obj)
        related_content_type = ContentType.objects.get_for_model(model)
        query = """
        SELECT %(model_pk)s, COUNT(related_tagged_item.object_id) AS %(count)s
        FROM %(model)s, %(tagged_item)s, %(tag)s, %(tagged_item)s related_tagged_item
        WHERE %(tagged_item)s.object_id = %%s
          AND %(tagged_item)s.content_type_id = %(content_type_id)s
          AND %(tag)s.id = %(tagged_item)s.tag_id
          AND related_tagged_item.content_type_id = %(related_content_type_id)s
          AND related_tagged_item.tag_id = %(tagged_item)s.tag_id
          AND %(model_pk)s = related_tagged_item.object_id"""
        if content_type.pk == related_content_type.pk:
            # Exclude the given instance itself if determining related
            # instances for the same model.
            query += """
          AND related_tagged_item.object_id != %(tagged_item)s.object_id"""
        query += """
        GROUP BY %(model_pk)s
        ORDER BY %(count)s DESC
        %(limit_offset)s"""
        query = query % {
            'model_pk': '%s.%s' % (model_table, qn(model._meta.pk.column)),
            'count': qn('count'),
            'model': model_table,
            'tagged_item': qn(self.model._meta.db_table),
            'tag': qn(self.model._meta.get_field('tag').rel.to._meta.db_table),
            'content_type_id': content_type.pk,
            'related_content_type_id': related_content_type.pk,
            'limit_offset': num is not None and connection.ops.limit_offset_sql(num) or '',
        }

        cursor = connection.cursor()
        cursor.execute(query, [obj.pk])
        object_ids = [row[0] for row in cursor.fetchall()]
        if len(object_ids) > 0:
            # Use in_bulk here instead of an id__in lookup, because id__in would
            # clobber the ordering.
            object_dict = queryset.in_bulk(object_ids)
            return [object_dict[object_id] for object_id in object_ids \
                    if object_id in object_dict]
        else:
            return []

##########
# Models #
##########

class Tag(models.Model):
    """
    A tag.
    """
    name = models.CharField(_('name'), max_length=50, unique=True, db_index=True)

    objects = TagManager()

    class Meta:
        ordering = ('name',)
        verbose_name = _('tag')
        verbose_name_plural = _('tags')

    def __unicode__(self):
        return self.name

class TaggedItem(models.Model):
    """
    Holds the relationship between a tag and the item being tagged.
    """
    tag          = models.ForeignKey(Tag, verbose_name=_('tag'), related_name='items')
    content_type = models.ForeignKey(ContentType, verbose_name=_('content type'))
    object_id    = models.PositiveIntegerField(_('object id'), db_index=True)
    object       = generic.GenericForeignKey('content_type', 'object_id')

    objects = TaggedItemManager()

    class Meta:
        # Enforce unique tag association per object
        unique_together = (('tag', 'content_type', 'object_id'),)
        verbose_name = _('tagged item')
        verbose_name_plural = _('tagged items')

    def __unicode__(self):
        return u'%s [%s]' % (self.object, self.tag)

########NEW FILE########
__FILENAME__ = settings
"""
Convenience module for access of custom tagging application settings,
which enforces default settings when the main settings module does not
contain the appropriate settings.
"""
from django.conf import settings

# The maximum length of a tag's name.
MAX_TAG_LENGTH = getattr(settings, 'MAX_TAG_LENGTH', 50)

# Whether to force all tags to lowercase before they are saved to the
# database.
FORCE_LOWERCASE_TAGS = getattr(settings, 'FORCE_LOWERCASE_TAGS', False)

########NEW FILE########
__FILENAME__ = tagging_tags
from django.db.models import get_model
from django.template import Library, Node, TemplateSyntaxError, Variable, resolve_variable
from django.utils.translation import ugettext as _

from tagging.models import Tag, TaggedItem
from tagging.utils import LINEAR, LOGARITHMIC

register = Library()

class TagsForModelNode(Node):
    def __init__(self, model, context_var, counts):
        self.model = model
        self.context_var = context_var
        self.counts = counts

    def render(self, context):
        model = get_model(*self.model.split('.'))
        if model is None:
            raise TemplateSyntaxError(_('tags_for_model tag was given an invalid model: %s') % self.model)
        context[self.context_var] = Tag.objects.usage_for_model(model, counts=self.counts)
        return ''

class TagCloudForModelNode(Node):
    def __init__(self, model, context_var, **kwargs):
        self.model = model
        self.context_var = context_var
        self.kwargs = kwargs

    def render(self, context):
        model = get_model(*self.model.split('.'))
        if model is None:
            raise TemplateSyntaxError(_('tag_cloud_for_model tag was given an invalid model: %s') % self.model)
        context[self.context_var] = \
            Tag.objects.cloud_for_model(model, **self.kwargs)
        return ''

class TagsForObjectNode(Node):
    def __init__(self, obj, context_var):
        self.obj = Variable(obj)
        self.context_var = context_var

    def render(self, context):
        context[self.context_var] = \
            Tag.objects.get_for_object(self.obj.resolve(context))
        return ''

class TaggedObjectsNode(Node):
    def __init__(self, tag, model, context_var):
        self.tag = Variable(tag)
        self.context_var = context_var
        self.model = model

    def render(self, context):
        model = get_model(*self.model.split('.'))
        if model is None:
            raise TemplateSyntaxError(_('tagged_objects tag was given an invalid model: %s') % self.model)
        context[self.context_var] = \
            TaggedItem.objects.get_by_model(model, self.tag.resolve(context))
        return ''

def do_tags_for_model(parser, token):
    """
    Retrieves a list of ``Tag`` objects associated with a given model
    and stores them in a context variable.

    Usage::

       {% tags_for_model [model] as [varname] %}

    The model is specified in ``[appname].[modelname]`` format.

    Extended usage::

       {% tags_for_model [model] as [varname] with counts %}

    If specified - by providing extra ``with counts`` arguments - adds
    a ``count`` attribute to each tag containing the number of
    instances of the given model which have been tagged with it.

    Examples::

       {% tags_for_model products.Widget as widget_tags %}
       {% tags_for_model products.Widget as widget_tags with counts %}

    """
    bits = token.contents.split()
    len_bits = len(bits)
    if len_bits not in (4, 6):
        raise TemplateSyntaxError(_('%s tag requires either three or five arguments') % bits[0])
    if bits[2] != 'as':
        raise TemplateSyntaxError(_("second argument to %s tag must be 'as'") % bits[0])
    if len_bits == 6:
        if bits[4] != 'with':
            raise TemplateSyntaxError(_("if given, fourth argument to %s tag must be 'with'") % bits[0])
        if bits[5] != 'counts':
            raise TemplateSyntaxError(_("if given, fifth argument to %s tag must be 'counts'") % bits[0])
    if len_bits == 4:
        return TagsForModelNode(bits[1], bits[3], counts=False)
    else:
        return TagsForModelNode(bits[1], bits[3], counts=True)

def do_tag_cloud_for_model(parser, token):
    """
    Retrieves a list of ``Tag`` objects for a given model, with tag
    cloud attributes set, and stores them in a context variable.

    Usage::

       {% tag_cloud_for_model [model] as [varname] %}

    The model is specified in ``[appname].[modelname]`` format.

    Extended usage::

       {% tag_cloud_for_model [model] as [varname] with [options] %}

    Extra options can be provided after an optional ``with`` argument,
    with each option being specified in ``[name]=[value]`` format. Valid
    extra options are:

       ``steps``
          Integer. Defines the range of font sizes.

       ``min_count``
          Integer. Defines the minimum number of times a tag must have
          been used to appear in the cloud.

       ``distribution``
          One of ``linear`` or ``log``. Defines the font-size
          distribution algorithm to use when generating the tag cloud.

    Examples::

       {% tag_cloud_for_model products.Widget as widget_tags %}
       {% tag_cloud_for_model products.Widget as widget_tags with steps=9 min_count=3 distribution=log %}

    """
    bits = token.contents.split()
    len_bits = len(bits)
    if len_bits != 4 and len_bits not in range(6, 9):
        raise TemplateSyntaxError(_('%s tag requires either three or between five and seven arguments') % bits[0])
    if bits[2] != 'as':
        raise TemplateSyntaxError(_("second argument to %s tag must be 'as'") % bits[0])
    kwargs = {}
    if len_bits > 5:
        if bits[4] != 'with':
            raise TemplateSyntaxError(_("if given, fourth argument to %s tag must be 'with'") % bits[0])
        for i in range(5, len_bits):
            try:
                name, value = bits[i].split('=')
                if name == 'steps' or name == 'min_count':
                    try:
                        kwargs[str(name)] = int(value)
                    except ValueError:
                        raise TemplateSyntaxError(_("%(tag)s tag's '%(option)s' option was not a valid integer: '%(value)s'") % {
                            'tag': bits[0],
                            'option': name,
                            'value': value,
                        })
                elif name == 'distribution':
                    if value in ['linear', 'log']:
                        kwargs[str(name)] = {'linear': LINEAR, 'log': LOGARITHMIC}[value]
                    else:
                        raise TemplateSyntaxError(_("%(tag)s tag's '%(option)s' option was not a valid choice: '%(value)s'") % {
                            'tag': bits[0],
                            'option': name,
                            'value': value,
                        })
                else:
                    raise TemplateSyntaxError(_("%(tag)s tag was given an invalid option: '%(option)s'") % {
                        'tag': bits[0],
                        'option': name,
                    })
            except ValueError:
                raise TemplateSyntaxError(_("%(tag)s tag was given a badly formatted option: '%(option)s'") % {
                    'tag': bits[0],
                    'option': bits[i],
                })
    return TagCloudForModelNode(bits[1], bits[3], **kwargs)

def do_tags_for_object(parser, token):
    """
    Retrieves a list of ``Tag`` objects associated with an object and
    stores them in a context variable.

    Usage::

       {% tags_for_object [object] as [varname] %}

    Example::

        {% tags_for_object foo_object as tag_list %}
    """
    bits = token.contents.split()
    if len(bits) != 4:
        raise TemplateSyntaxError(_('%s tag requires exactly three arguments') % bits[0])
    if bits[2] != 'as':
        raise TemplateSyntaxError(_("second argument to %s tag must be 'as'") % bits[0])
    return TagsForObjectNode(bits[1], bits[3])

def do_tagged_objects(parser, token):
    """
    Retrieves a list of instances of a given model which are tagged with
    a given ``Tag`` and stores them in a context variable.

    Usage::

       {% tagged_objects [tag] in [model] as [varname] %}

    The model is specified in ``[appname].[modelname]`` format.

    The tag must be an instance of a ``Tag``, not the name of a tag.

    Example::

        {% tagged_objects comedy_tag in tv.Show as comedies %}

    """
    bits = token.contents.split()
    if len(bits) != 6:
        raise TemplateSyntaxError(_('%s tag requires exactly five arguments') % bits[0])
    if bits[2] != 'in':
        raise TemplateSyntaxError(_("second argument to %s tag must be 'in'") % bits[0])
    if bits[4] != 'as':
        raise TemplateSyntaxError(_("fourth argument to %s tag must be 'as'") % bits[0])
    return TaggedObjectsNode(bits[1], bits[3], bits[5])

register.tag('tags_for_model', do_tags_for_model)
register.tag('tag_cloud_for_model', do_tag_cloud_for_model)
register.tag('tags_for_object', do_tags_for_object)
register.tag('tagged_objects', do_tagged_objects)

########NEW FILE########
__FILENAME__ = models
from django.db import models

from tagging.fields import TagField

class Perch(models.Model):
    size = models.IntegerField()
    smelly = models.BooleanField(default=True)

class Parrot(models.Model):
    state = models.CharField(max_length=50)
    perch = models.ForeignKey(Perch, null=True)

    def __unicode__(self):
        return self.state

    class Meta:
        ordering = ['state']

class Link(models.Model):
    name = models.CharField(max_length=50)

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ['name']

class Article(models.Model):
    name = models.CharField(max_length=50)

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ['name']

class FormTest(models.Model):
    tags = TagField('Test', help_text='Test')

########NEW FILE########
__FILENAME__ = settings
import os
DIRNAME = os.path.dirname(__file__)

DEFAULT_CHARSET = 'utf-8'

DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = os.path.join(DIRNAME, 'tagging_test.db')

#DATABASE_ENGINE = 'mysql'
#DATABASE_NAME = 'tagging_test'
#DATABASE_USER = 'root'
#DATABASE_PASSWORD = ''
#DATABASE_HOST = 'localhost'
#DATABASE_PORT = '3306'

#DATABASE_ENGINE = 'postgresql_psycopg2'
#DATABASE_NAME = 'tagging_test'
#DATABASE_USER = 'postgres'
#DATABASE_PASSWORD = ''
#DATABASE_HOST = 'localhost'
#DATABASE_PORT = '5432'

INSTALLED_APPS = (
    'django.contrib.contenttypes',
    'tagging',
    'tagging.tests',
)

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
tests = r"""
>>> import os
>>> from django import newforms as forms
>>> from tagging.forms import TagField
>>> from tagging import settings
>>> from tagging.models import Tag, TaggedItem
>>> from tagging.tests.models import Article, Link, Perch, Parrot, FormTest
>>> from tagging.utils import calculate_cloud, get_tag_list, get_tag, parse_tag_input
>>> from tagging.utils import LINEAR
>>> from tagging.validators import is_tag_list, is_tag

#############
# Utilities #
#############

# Tag input ###################################################################

# Simple space-delimited tags
>>> parse_tag_input('one')
[u'one']
>>> parse_tag_input('one two')
[u'one', u'two']
>>> parse_tag_input('one two three')
[u'one', u'three', u'two']
>>> parse_tag_input('one one two two')
[u'one', u'two']

# Comma-delimited multiple words - an unquoted comma in the input will trigger
# this.
>>> parse_tag_input(',one')
[u'one']
>>> parse_tag_input(',one two')
[u'one two']
>>> parse_tag_input(',one two three')
[u'one two three']
>>> parse_tag_input('a-one, a-two and a-three')
[u'a-one', u'a-two and a-three']

# Double-quoted multiple words - a completed quote will trigger this.
# Unclosed quotes are ignored.
>>> parse_tag_input('"one')
[u'one']
>>> parse_tag_input('"one two')
[u'one', u'two']
>>> parse_tag_input('"one two three')
[u'one', u'three', u'two']
>>> parse_tag_input('"one two"')
[u'one two']
>>> parse_tag_input('a-one "a-two and a-three"')
[u'a-one', u'a-two and a-three']

# No loose commas - split on spaces
>>> parse_tag_input('one two "thr,ee"')
[u'one', u'thr,ee', u'two']

# Loose commas - split on commas
>>> parse_tag_input('"one", two three')
[u'one', u'two three']

# Double quotes can contain commas
>>> parse_tag_input('a-one "a-two, and a-three"')
[u'a-one', u'a-two, and a-three']
>>> parse_tag_input('"two", one, one, two, "one"')
[u'one', u'two']

# Bad users! Naughty users!
>>> parse_tag_input(None)
[]
>>> parse_tag_input('')
[]
>>> parse_tag_input('"')
[]
>>> parse_tag_input('""')
[]
>>> parse_tag_input('"' * 7)
[]
>>> parse_tag_input(',,,,,,')
[]
>>> parse_tag_input('",",",",",",","')
[u',']
>>> parse_tag_input('a-one "a-two" and "a-three')
[u'a-one', u'a-three', u'a-two', u'and']

# Normalised Tag list input ###################################################
>>> cheese = Tag.objects.create(name='cheese')
>>> toast = Tag.objects.create(name='toast')
>>> get_tag_list(cheese)
[<Tag: cheese>]
>>> get_tag_list('cheese toast')
[<Tag: cheese>, <Tag: toast>]
>>> get_tag_list('cheese,toast')
[<Tag: cheese>, <Tag: toast>]
>>> get_tag_list([])
[]
>>> get_tag_list(['cheese', 'toast'])
[<Tag: cheese>, <Tag: toast>]
>>> get_tag_list([cheese.id, toast.id])
[<Tag: cheese>, <Tag: toast>]
>>> get_tag_list(['cheese', 'toast', 'ŠĐĆŽćžšđ'])
[<Tag: cheese>, <Tag: toast>]
>>> get_tag_list([cheese, toast])
[<Tag: cheese>, <Tag: toast>]
>>> get_tag_list((cheese, toast))
(<Tag: cheese>, <Tag: toast>)
>>> get_tag_list(Tag.objects.filter(name__in=['cheese', 'toast']))
[<Tag: cheese>, <Tag: toast>]
>>> get_tag_list(['cheese', toast])
Traceback (most recent call last):
    ...
ValueError: If a list or tuple of tags is provided, they must all be tag names, Tag objects or Tag ids.
>>> get_tag_list(29)
Traceback (most recent call last):
    ...
ValueError: The tag input given was invalid.

# Normalised Tag input
>>> get_tag(cheese)
<Tag: cheese>
>>> get_tag('cheese')
<Tag: cheese>
>>> get_tag(cheese.id)
<Tag: cheese>
>>> get_tag('mouse')

# Tag clouds ##################################################################
>>> tags = []
>>> for line in open(os.path.join(os.path.dirname(__file__), 'tags.txt')).readlines():
...     name, count = line.rstrip().split()
...     tag = Tag(name=name)
...     tag.count = int(count)
...     tags.append(tag)

>>> sizes = {}
>>> for tag in calculate_cloud(tags, steps=5):
...     sizes[tag.font_size] = sizes.get(tag.font_size, 0) + 1

# This isn't a pre-calculated test, just making sure it's consistent
>>> sizes
{1: 48, 2: 30, 3: 19, 4: 15, 5: 10}

>>> sizes = {}
>>> for tag in calculate_cloud(tags, steps=5, distribution=LINEAR):
...     sizes[tag.font_size] = sizes.get(tag.font_size, 0) + 1

# This isn't a pre-calculated test, just making sure it's consistent
>>> sizes
{1: 97, 2: 12, 3: 7, 4: 2, 5: 4}

>>> calculate_cloud(tags, steps=5, distribution='cheese')
Traceback (most recent call last):
    ...
ValueError: Invalid distribution algorithm specified: cheese.

# Validators ##################################################################

>>> is_tag_list('foo qwertyuiopasdfghjklzxcvbnmqwertyuiopasdfghjklzxcvbn bar', {})
Traceback (most recent call last):
    ...
ValidationError: [u'Each tag may be no more than 50 characters long.']

>>> is_tag('"test"', {})
>>> is_tag(',test', {})
>>> is_tag('f o o', {})
Traceback (most recent call last):
    ...
ValidationError: [u'Multiple tags were given.']
>>> is_tag_list('foo qwertyuiopasdfghjklzxcvbnmqwertyuiopasdfghjklzxcvbn bar', {})
Traceback (most recent call last):
    ...
ValidationError: [u'Each tag may be no more than 50 characters long.']

###########
# Tagging #
###########

# Basic tagging ###############################################################

>>> dead = Parrot.objects.create(state='dead')
>>> Tag.objects.update_tags(dead, 'foo,bar,"ter"')
>>> Tag.objects.get_for_object(dead)
[<Tag: bar>, <Tag: foo>, <Tag: ter>]
>>> Tag.objects.update_tags(dead, '"foo" bar "baz"')
>>> Tag.objects.get_for_object(dead)
[<Tag: bar>, <Tag: baz>, <Tag: foo>]
>>> Tag.objects.add_tag(dead, 'foo')
>>> Tag.objects.get_for_object(dead)
[<Tag: bar>, <Tag: baz>, <Tag: foo>]
>>> Tag.objects.add_tag(dead, 'zip')
>>> Tag.objects.get_for_object(dead)
[<Tag: bar>, <Tag: baz>, <Tag: foo>, <Tag: zip>]
>>> Tag.objects.add_tag(dead, '    ')
Traceback (most recent call last):
    ...
AttributeError: No tags were given: "    ".
>>> Tag.objects.add_tag(dead, 'one two')
Traceback (most recent call last):
    ...
AttributeError: Multiple tags were given: "one two".

# Note that doctest in Python 2.4 (and maybe 2.5?) doesn't support non-ascii
# characters in output, so we're displaying the repr() here.
>>> Tag.objects.update_tags(dead, 'ŠĐĆŽćžšđ')
>>> repr(Tag.objects.get_for_object(dead))
'[<Tag: \xc5\xa0\xc4\x90\xc4\x86\xc5\xbd\xc4\x87\xc5\xbe\xc5\xa1\xc4\x91>]'

>>> Tag.objects.update_tags(dead, None)
>>> Tag.objects.get_for_object(dead)
[]

# Using a model's TagField
>>> f1 = FormTest.objects.create(tags=u'test3 test2 test1')
>>> Tag.objects.get_for_object(f1)
[<Tag: test1>, <Tag: test2>, <Tag: test3>]
>>> f1.tags = u'test4'
>>> f1.save()
>>> Tag.objects.get_for_object(f1)
[<Tag: test4>]
>>> f1.tags = ''
>>> f1.save()
>>> Tag.objects.get_for_object(f1)
[]

# Forcing tags to lowercase
>>> settings.FORCE_LOWERCASE_TAGS = True
>>> Tag.objects.update_tags(dead, 'foO bAr Ter')
>>> Tag.objects.get_for_object(dead)
[<Tag: bar>, <Tag: foo>, <Tag: ter>]
>>> Tag.objects.update_tags(dead, 'foO bAr baZ')
>>> Tag.objects.get_for_object(dead)
[<Tag: bar>, <Tag: baz>, <Tag: foo>]
>>> Tag.objects.add_tag(dead, 'FOO')
>>> Tag.objects.get_for_object(dead)
[<Tag: bar>, <Tag: baz>, <Tag: foo>]
>>> Tag.objects.add_tag(dead, 'Zip')
>>> Tag.objects.get_for_object(dead)
[<Tag: bar>, <Tag: baz>, <Tag: foo>, <Tag: zip>]
>>> Tag.objects.update_tags(dead, None)
>>> f1.tags = u'TEST5'
>>> f1.save()
>>> Tag.objects.get_for_object(f1)
[<Tag: test5>]
>>> f1.tags
u'test5'

# Retrieving tags by Model ####################################################

>>> Tag.objects.usage_for_model(Parrot)
[]
>>> parrot_details = (
...     ('pining for the fjords', 9, True,  'foo bar'),
...     ('passed on',             6, False, 'bar baz ter'),
...     ('no more',               4, True,  'foo ter'),
...     ('late',                  2, False, 'bar ter'),
... )

>>> for state, perch_size, perch_smelly, tags in parrot_details:
...     perch = Perch.objects.create(size=perch_size, smelly=perch_smelly)
...     parrot = Parrot.objects.create(state=state, perch=perch)
...     Tag.objects.update_tags(parrot, tags)

>>> [(tag.name, tag.count) for tag in Tag.objects.usage_for_model(Parrot, counts=True)]
[(u'bar', 3), (u'baz', 1), (u'foo', 2), (u'ter', 3)]
>>> [(tag.name, tag.count) for tag in Tag.objects.usage_for_model(Parrot, min_count=2)]
[(u'bar', 3), (u'foo', 2), (u'ter', 3)]

# Limiting results to a subset of the model
>>> [(tag.name, tag.count) for tag in Tag.objects.usage_for_model(Parrot, counts=True, filters=dict(state='no more'))]
[(u'foo', 1), (u'ter', 1)]
>>> [(tag.name, tag.count) for tag in Tag.objects.usage_for_model(Parrot, counts=True, filters=dict(state__startswith='p'))]
[(u'bar', 2), (u'baz', 1), (u'foo', 1), (u'ter', 1)]
>>> [(tag.name, tag.count) for tag in Tag.objects.usage_for_model(Parrot, counts=True, filters=dict(perch__size__gt=4))]
[(u'bar', 2), (u'baz', 1), (u'foo', 1), (u'ter', 1)]
>>> [(tag.name, tag.count) for tag in Tag.objects.usage_for_model(Parrot, counts=True, filters=dict(perch__smelly=True))]
[(u'bar', 1), (u'foo', 2), (u'ter', 1)]
>>> [(tag.name, tag.count) for tag in Tag.objects.usage_for_model(Parrot, min_count=2, filters=dict(perch__smelly=True))]
[(u'foo', 2)]
>>> [(tag.name, hasattr(tag, 'counts')) for tag in Tag.objects.usage_for_model(Parrot, filters=dict(perch__size__gt=4))]
[(u'bar', False), (u'baz', False), (u'foo', False), (u'ter', False)]
>>> [(tag.name, hasattr(tag, 'counts')) for tag in Tag.objects.usage_for_model(Parrot, filters=dict(perch__size__gt=99))]
[]

# Related tags
>>> [(tag.name, tag.count) for tag in Tag.objects.related_for_model(Tag.objects.filter(name__in=['bar']), Parrot, counts=True)]
[(u'baz', 1), (u'foo', 1), (u'ter', 2)]
>>> [(tag.name, tag.count) for tag in Tag.objects.related_for_model(Tag.objects.filter(name__in=['bar']), Parrot, min_count=2)]
[(u'ter', 2)]
>>> [tag.name for tag in Tag.objects.related_for_model(Tag.objects.filter(name__in=['bar']), Parrot, counts=False)]
[u'baz', u'foo', u'ter']
>>> [(tag.name, tag.count) for tag in Tag.objects.related_for_model(Tag.objects.filter(name__in=['bar', 'ter']), Parrot, counts=True)]
[(u'baz', 1)]
>>> [(tag.name, tag.count) for tag in Tag.objects.related_for_model(Tag.objects.filter(name__in=['bar', 'ter', 'baz']), Parrot, counts=True)]
[]

# Once again, with feeling (strings)
>>> [(tag.name, tag.count) for tag in Tag.objects.related_for_model('bar', Parrot, counts=True)]
[(u'baz', 1), (u'foo', 1), (u'ter', 2)]
>>> [(tag.name, tag.count) for tag in Tag.objects.related_for_model('bar', Parrot, min_count=2)]
[(u'ter', 2)]
>>> [tag.name for tag in Tag.objects.related_for_model('bar', Parrot, counts=False)]
[u'baz', u'foo', u'ter']
>>> [(tag.name, tag.count) for tag in Tag.objects.related_for_model(['bar', 'ter'], Parrot, counts=True)]
[(u'baz', 1)]
>>> [(tag.name, tag.count) for tag in Tag.objects.related_for_model(['bar', 'ter', 'baz'], Parrot, counts=True)]
[]

# Retrieving tagged objects by Model ##########################################

>>> foo = Tag.objects.get(name='foo')
>>> bar = Tag.objects.get(name='bar')
>>> baz = Tag.objects.get(name='baz')
>>> ter = Tag.objects.get(name='ter')
>>> TaggedItem.objects.get_by_model(Parrot, foo)
[<Parrot: no more>, <Parrot: pining for the fjords>]
>>> TaggedItem.objects.get_by_model(Parrot, bar)
[<Parrot: late>, <Parrot: passed on>, <Parrot: pining for the fjords>]

# Intersections are supported
>>> TaggedItem.objects.get_by_model(Parrot, [foo, baz])
[]
>>> TaggedItem.objects.get_by_model(Parrot, [foo, bar])
[<Parrot: pining for the fjords>]
>>> TaggedItem.objects.get_by_model(Parrot, [bar, ter])
[<Parrot: late>, <Parrot: passed on>]

# Issue 114 - Intersection with non-existant tags
>>> TaggedItem.objects.get_intersection_by_model(Parrot, [])
[]

# You can also pass Tag QuerySets
>>> TaggedItem.objects.get_by_model(Parrot, Tag.objects.filter(name__in=['foo', 'baz']))
[]
>>> TaggedItem.objects.get_by_model(Parrot, Tag.objects.filter(name__in=['foo', 'bar']))
[<Parrot: pining for the fjords>]
>>> TaggedItem.objects.get_by_model(Parrot, Tag.objects.filter(name__in=['bar', 'ter']))
[<Parrot: late>, <Parrot: passed on>]

# You can also pass strings and lists of strings
>>> TaggedItem.objects.get_by_model(Parrot, 'foo baz')
[]
>>> TaggedItem.objects.get_by_model(Parrot, 'foo bar')
[<Parrot: pining for the fjords>]
>>> TaggedItem.objects.get_by_model(Parrot, 'bar ter')
[<Parrot: late>, <Parrot: passed on>]
>>> TaggedItem.objects.get_by_model(Parrot, ['foo', 'baz'])
[]
>>> TaggedItem.objects.get_by_model(Parrot, ['foo', 'bar'])
[<Parrot: pining for the fjords>]
>>> TaggedItem.objects.get_by_model(Parrot, ['bar', 'ter'])
[<Parrot: late>, <Parrot: passed on>]

# Issue 50 - Get by non-existent tag
>>> TaggedItem.objects.get_by_model(Parrot, 'argatrons')
[]

# Unions
>>> TaggedItem.objects.get_union_by_model(Parrot, ['foo', 'ter'])
[<Parrot: late>, <Parrot: no more>, <Parrot: passed on>, <Parrot: pining for the fjords>]
>>> TaggedItem.objects.get_union_by_model(Parrot, ['bar', 'baz'])
[<Parrot: late>, <Parrot: passed on>, <Parrot: pining for the fjords>]

# Issue 114 - Union with non-existant tags
>>> TaggedItem.objects.get_union_by_model(Parrot, [])
[]

# Retrieving related objects by Model #########################################

# Related instances of the same Model
>>> l1 = Link.objects.create(name='link 1')
>>> Tag.objects.update_tags(l1, 'tag1 tag2 tag3 tag4 tag5')
>>> l2 = Link.objects.create(name='link 2')
>>> Tag.objects.update_tags(l2, 'tag1 tag2 tag3')
>>> l3 = Link.objects.create(name='link 3')
>>> Tag.objects.update_tags(l3, 'tag1')
>>> l4 = Link.objects.create(name='link 4')
>>> TaggedItem.objects.get_related(l1, Link)
[<Link: link 2>, <Link: link 3>]
>>> TaggedItem.objects.get_related(l1, Link, num=1)
[<Link: link 2>]
>>> TaggedItem.objects.get_related(l4, Link)
[]

# Limit related items
>>> TaggedItem.objects.get_related(l1, Link.objects.exclude(name='link 3'))
[<Link: link 2>]

# Related instance of a different Model
>>> a1 = Article.objects.create(name='article 1')
>>> Tag.objects.update_tags(a1, 'tag1 tag2 tag3 tag4')
>>> TaggedItem.objects.get_related(a1, Link)
[<Link: link 1>, <Link: link 2>, <Link: link 3>]
>>> Tag.objects.update_tags(a1, 'tag6')
>>> TaggedItem.objects.get_related(a1, Link)
[]

################
# Model Fields #
################

# TagField ####################################################################

# Ensure that automatically created forms use TagField
>>> class TestForm(forms.ModelForm):
...     class Meta:
...         model = FormTest
>>> form = TestForm()
>>> form.fields['tags'].__class__.__name__
'TagField'

# Recreating string representaions of tag lists ###############################
>>> plain = Tag.objects.create(name='plain')
>>> spaces = Tag.objects.create(name='spa ces')
>>> comma = Tag.objects.create(name='com,ma')

>>> from tagging.utils import edit_string_for_tags
>>> edit_string_for_tags([plain])
u'plain'
>>> edit_string_for_tags([plain, spaces])
u'plain, spa ces'
>>> edit_string_for_tags([plain, spaces, comma])
u'plain, spa ces, "com,ma"'
>>> edit_string_for_tags([plain, comma])
u'plain "com,ma"'
>>> edit_string_for_tags([comma, spaces])
u'"com,ma", spa ces'

###############
# Form Fields #
###############

>>> t = TagField()
>>> t.clean('foo')
u'foo'
>>> t.clean('foo bar baz')
u'foo bar baz'
>>> t.clean('foo,bar,baz')
u'foo,bar,baz'
>>> t.clean('foo, bar, baz')
u'foo, bar, baz'
>>> t.clean('foo qwertyuiopasdfghjklzxcvbnmqwertyuiopasdfghjklzxcvb bar')
u'foo qwertyuiopasdfghjklzxcvbnmqwertyuiopasdfghjklzxcvb bar'
>>> t.clean('foo qwertyuiopasdfghjklzxcvbnmqwertyuiopasdfghjklzxcvbn bar')
Traceback (most recent call last):
    ...
ValidationError: [u'Each tag may be no more than 50 characters long.']
"""

tests_pre_qsrf = tests + r"""
# Limiting results to a queryset
>>> Tag.objects.usage_for_queryset(Parrot.objects.filter())
Traceback (most recent call last):
    ...
AttributeError: 'TagManager.usage_for_queryset' is not compatible with pre-queryset-refactor versions of Django.
"""

tests_post_qsrf = tests + r"""
>>> from django.db.models import Q

# Limiting results to a queryset
>>> [(tag.name, tag.count) for tag in Tag.objects.usage_for_queryset(Parrot.objects.filter(state='no more'), counts=True)]
[(u'foo', 1), (u'ter', 1)]
>>> [(tag.name, tag.count) for tag in Tag.objects.usage_for_queryset(Parrot.objects.filter(state__startswith='p'), counts=True)]
[(u'bar', 2), (u'baz', 1), (u'foo', 1), (u'ter', 1)]
>>> [(tag.name, tag.count) for tag in Tag.objects.usage_for_queryset(Parrot.objects.filter(perch__size__gt=4), counts=True)]
[(u'bar', 2), (u'baz', 1), (u'foo', 1), (u'ter', 1)]
>>> [(tag.name, tag.count) for tag in Tag.objects.usage_for_queryset(Parrot.objects.filter(perch__smelly=True), counts=True)]
[(u'bar', 1), (u'foo', 2), (u'ter', 1)]
>>> [(tag.name, tag.count) for tag in Tag.objects.usage_for_queryset(Parrot.objects.filter(perch__smelly=True), min_count=2)]
[(u'foo', 2)]
>>> [(tag.name, hasattr(tag, 'counts')) for tag in Tag.objects.usage_for_queryset(Parrot.objects.filter(perch__size__gt=4))]
[(u'bar', False), (u'baz', False), (u'foo', False), (u'ter', False)]
>>> [(tag.name, hasattr(tag, 'counts')) for tag in Tag.objects.usage_for_queryset(Parrot.objects.filter(perch__size__gt=99))]
[]
>>> [(tag.name, tag.count) for tag in Tag.objects.usage_for_queryset(Parrot.objects.filter(Q(perch__size__gt=6) | Q(state__startswith='l')), counts=True)]
[(u'bar', 2), (u'foo', 1), (u'ter', 1)]
>>> [(tag.name, tag.count) for tag in Tag.objects.usage_for_queryset(Parrot.objects.filter(Q(perch__size__gt=6) | Q(state__startswith='l')), min_count=2)]
[(u'bar', 2)]
>>> [(tag.name, hasattr(tag, 'counts')) for tag in Tag.objects.usage_for_queryset(Parrot.objects.filter(Q(perch__size__gt=6) | Q(state__startswith='l')))]
[(u'bar', False), (u'foo', False), (u'ter', False)]
>>> [(tag.name, tag.count) for tag in Tag.objects.usage_for_queryset(Parrot.objects.exclude(state='passed on'), counts=True)]
[(u'bar', 2), (u'foo', 2), (u'ter', 2)]
>>> [(tag.name, tag.count) for tag in Tag.objects.usage_for_queryset(Parrot.objects.exclude(state__startswith='p'), min_count=2)]
[(u'ter', 2)]
>>> [(tag.name, tag.count) for tag in Tag.objects.usage_for_queryset(Parrot.objects.exclude(Q(perch__size__gt=6) | Q(perch__smelly=False)), counts=True)]
[(u'foo', 1), (u'ter', 1)]
>>> [(tag.name, tag.count) for tag in Tag.objects.usage_for_queryset(Parrot.objects.exclude(perch__smelly=True).filter(state__startswith='l'), counts=True)]
[(u'bar', 1), (u'ter', 1)]
"""

try:
    from django.db.models.query import parse_lookup
except ImportError:
    __test__ = {'post-qsrf': tests_post_qsrf}
else:
    __test__ = {'pre-qsrf': tests_pre_qsrf}

########NEW FILE########
__FILENAME__ = utils
"""
Tagging utilities - from user tag input parsing to tag cloud
calculation.
"""
import math
import types

from django.db.models.query import QuerySet
from django.utils.encoding import force_unicode
from django.utils.translation import ugettext as _

# Python 2.3 compatibility
try:
    set
except NameError:
    from sets import Set as set

def parse_tag_input(input):
    """
    Parses tag input, with multiple word input being activated and
    delineated by commas and double quotes. Quotes take precedence, so
    they may contain commas.

    Returns a sorted list of unique tag names.
    """
    if not input:
        return []

    input = force_unicode(input)

    # Special case - if there are no commas or double quotes in the
    # input, we don't *do* a recall... I mean, we know we only need to
    # split on spaces.
    if u',' not in input and u'"' not in input:
        words = list(set(split_strip(input, u' ')))
        words.sort()
        return words

    words = []
    buffer = []
    # Defer splitting of non-quoted sections until we know if there are
    # any unquoted commas.
    to_be_split = []
    saw_loose_comma = False
    open_quote = False
    i = iter(input)
    try:
        while 1:
            c = i.next()
            if c == u'"':
                if buffer:
                    to_be_split.append(u''.join(buffer))
                    buffer = []
                # Find the matching quote
                open_quote = True
                c = i.next()
                while c != u'"':
                    buffer.append(c)
                    c = i.next()
                if buffer:
                    word = u''.join(buffer).strip()
                    if word:
                        words.append(word)
                    buffer = []
                open_quote = False
            else:
                if not saw_loose_comma and c == u',':
                    saw_loose_comma = True
                buffer.append(c)
    except StopIteration:
        # If we were parsing an open quote which was never closed treat
        # the buffer as unquoted.
        if buffer:
            if open_quote and u',' in buffer:
                saw_loose_comma = True
            to_be_split.append(u''.join(buffer))
    if to_be_split:
        if saw_loose_comma:
            delimiter = u','
        else:
            delimiter = u' '
        for chunk in to_be_split:
            words.extend(split_strip(chunk, delimiter))
    words = list(set(words))
    words.sort()
    return words

def split_strip(input, delimiter=u','):
    """
    Splits ``input`` on ``delimiter``, stripping each resulting string
    and returning a list of non-empty strings.
    """
    if not input:
        return []

    words = [w.strip() for w in input.split(delimiter)]
    return [w for w in words if w]

def edit_string_for_tags(tags):
    """
    Given list of ``Tag`` instances, creates a string representation of
    the list suitable for editing by the user, such that submitting the
    given string representation back without changing it will give the
    same list of tags.

    Tag names which contain commas will be double quoted.

    If any tag name which isn't being quoted contains whitespace, the
    resulting string of tag names will be comma-delimited, otherwise
    it will be space-delimited.
    """
    names = []
    use_commas = False
    for tag in tags:
        name = tag.name
        if u',' in name:
            names.append('"%s"' % name)
            continue
        elif u' ' in name:
            if not use_commas:
                use_commas = True
        names.append(name)
    if use_commas:
        glue = u', '
    else:
        glue = u' '
    return glue.join(names)

def get_queryset_and_model(queryset_or_model):
    """
    Given a ``QuerySet`` or a ``Model``, returns a two-tuple of
    (queryset, model).

    If a ``Model`` is given, the ``QuerySet`` returned will be created
    using its default manager.
    """
    try:
        return queryset_or_model, queryset_or_model.model
    except AttributeError:
        return queryset_or_model._default_manager.all(), queryset_or_model

def get_tag_list(tags):
    """
    Utility function for accepting tag input in a flexible manner.

    If a ``Tag`` object is given, it will be returned in a list as
    its single occupant.

    If given, the tag names in the following will be used to create a
    ``Tag`` ``QuerySet``:

       * A string, which may contain multiple tag names.
       * A list or tuple of strings corresponding to tag names.
       * A list or tuple of integers corresponding to tag ids.

    If given, the following will be returned as-is:

       * A list or tuple of ``Tag`` objects.
       * A ``Tag`` ``QuerySet``.

    """
    from tagging.models import Tag
    if isinstance(tags, Tag):
        return [tags]
    elif isinstance(tags, QuerySet) and tags.model is Tag:
        return tags
    elif isinstance(tags, types.StringTypes):
        return Tag.objects.filter(name__in=parse_tag_input(tags))
    elif isinstance(tags, (types.ListType, types.TupleType)):
        if len(tags) == 0:
            return tags
        contents = set()
        for item in tags:
            if isinstance(item, types.StringTypes):
                contents.add('string')
            elif isinstance(item, Tag):
                contents.add('tag')
            elif isinstance(item, (types.IntType, types.LongType)):
                contents.add('int')
        if len(contents) == 1:
            if 'string' in contents:
                return Tag.objects.filter(name__in=[force_unicode(tag) \
                                                    for tag in tags])
            elif 'tag' in contents:
                return tags
            elif 'int' in contents:
                return Tag.objects.filter(id__in=tags)
        else:
            raise ValueError(_('If a list or tuple of tags is provided, they must all be tag names, Tag objects or Tag ids.'))
    else:
        raise ValueError(_('The tag input given was invalid.'))

def get_tag(tag):
    """
    Utility function for accepting single tag input in a flexible
    manner.

    If a ``Tag`` object is given it will be returned as-is; if a
    string or integer are given, they will be used to lookup the
    appropriate ``Tag``.

    If no matching tag can be found, ``None`` will be returned.
    """
    from tagging.models import Tag
    if isinstance(tag, Tag):
        return tag

    try:
        if isinstance(tag, types.StringTypes):
            return Tag.objects.get(name=tag)
        elif isinstance(tag, (types.IntType, types.LongType)):
            return Tag.objects.get(id=tag)
    except Tag.DoesNotExist:
        pass

    return None

# Font size distribution algorithms
LOGARITHMIC, LINEAR = 1, 2

def _calculate_thresholds(min_weight, max_weight, steps):
    delta = (max_weight - min_weight) / float(steps)
    return [min_weight + i * delta for i in range(1, steps + 1)]

def _calculate_tag_weight(weight, max_weight, distribution):
    """
    Logarithmic tag weight calculation is based on code from the
    `Tag Cloud`_ plugin for Mephisto, by Sven Fuchs.

    .. _`Tag Cloud`: http://www.artweb-design.de/projects/mephisto-plugin-tag-cloud
    """
    if distribution == LINEAR or max_weight == 1:
        return weight
    elif distribution == LOGARITHMIC:
        return math.log(weight) * max_weight / math.log(max_weight)
    raise ValueError(_('Invalid distribution algorithm specified: %s.') % distribution)

def calculate_cloud(tags, steps=4, distribution=LOGARITHMIC):
    """
    Add a ``font_size`` attribute to each tag according to the
    frequency of its use, as indicated by its ``count``
    attribute.

    ``steps`` defines the range of font sizes - ``font_size`` will
    be an integer between 1 and ``steps`` (inclusive).

    ``distribution`` defines the type of font size distribution
    algorithm which will be used - logarithmic or linear. It must be
    one of ``tagging.utils.LOGARITHMIC`` or ``tagging.utils.LINEAR``.
    """
    if len(tags) > 0:
        counts = [tag.count for tag in tags]
        min_weight = float(min(counts))
        max_weight = float(max(counts))
        thresholds = _calculate_thresholds(min_weight, max_weight, steps)
        for tag in tags:
            font_set = False
            tag_weight = _calculate_tag_weight(tag.count, max_weight, distribution)
            for i in range(steps):
                if not font_set and tag_weight <= thresholds[i]:
                    tag.font_size = i + 1
                    font_set = True
    return tags

########NEW FILE########
__FILENAME__ = validators
"""
Oldforms validators for tagging related fields - these are still
required for basic ``django.contrib.admin`` application field validation
until the ``newforms-admin`` branch lands in trunk.
"""
from django import forms
from django.utils.translation import ugettext as _

from tagging import settings
from tagging.utils import parse_tag_input

def is_tag_list(value):
    """
    Validates that ``value`` is a valid list of tags.
    """
    for tag_name in parse_tag_input(value):
        if len(tag_name) > settings.MAX_TAG_LENGTH:
            raise forms.ValidationError(
                _('Each tag may be no more than %s characters long.') % settings.MAX_TAG_LENGTH)
    return value

def is_tag(value):
    """
    Validates that ``value`` is a valid tag.
    """
    tag_names = parse_tag_input(value)
    if len(tag_names) > 1:
        raise ValidationError(_('Multiple tags were given.'))
    elif len(tag_names[0]) > settings.MAX_TAG_LENGTH:
        raise forms.ValidationError(
            _('A tag may be no more than %s characters long.') % settings.MAX_TAG_LENGTH)
    return value

########NEW FILE########
__FILENAME__ = views
"""
Tagging related views.
"""
from django.http import Http404
from django.utils.translation import ugettext as _
from django.views.generic.list_detail import object_list

from tagging.models import Tag, TaggedItem
from tagging.utils import get_tag, get_queryset_and_model

def tagged_object_list(request, queryset_or_model=None, tag=None,
        related_tags=False, related_tag_counts=True, **kwargs):
    """
    A thin wrapper around
    ``django.views.generic.list_detail.object_list`` which creates a
    ``QuerySet`` containing instances of the given queryset or model
    tagged with the given tag.

    In addition to the context variables set up by ``object_list``, a
    ``tag`` context variable will contain the ``Tag`` instance for the
    tag.

    If ``related_tags`` is ``True``, a ``related_tags`` context variable
    will contain tags related to the given tag for the given model.
    Additionally, if ``related_tag_counts`` is ``True``, each related
    tag will have a ``count`` attribute indicating the number of items
    which have it in addition to the given tag.
    """
    if queryset_or_model is None:
        try:
            queryset_or_model = kwargs.pop('queryset_or_model')
        except KeyError:
            raise AttributeError(_('tagged_object_list must be called with a queryset or a model.'))

    if tag is None:
        try:
            tag = kwargs.pop('tag')
        except KeyError:
            raise AttributeError(_('tagged_object_list must be called with a tag.'))

    tag_instance = get_tag(tag)
    if tag_instance is None:
        raise Http404(_('No Tag found matching "%s".') % tag)
    queryset = TaggedItem.objects.get_by_model(queryset_or_model, tag_instance)
    if not kwargs.has_key('extra_context'):
        kwargs['extra_context'] = {}
    kwargs['extra_context']['tag'] = tag_instance
    if related_tags:
        kwargs['extra_context']['related_tags'] = \
            Tag.objects.related_for_model(tag_instance, queryset_or_model,
                                          counts=related_tag_counts)
    return object_list(request, queryset, **kwargs)

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from threadedcomments.models import ThreadedComment, FreeThreadedComment

class ThreadedCommentAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {'fields': ('content_type', 'object_id')}),
        (_('Parent'), {'fields' : ('parent',)}),
        (_('Content'), {'fields': ('user', 'comment')}),
        (_('Meta'), {'fields': ('is_public', 'date_submitted', 'date_modified', 'date_approved', 'is_approved', 'ip_address')}),
    )
    list_display = ('user', 'date_submitted', 'content_type', 'get_content_object', 'parent', '__unicode__')
    list_filter = ('date_submitted',)
    date_hierarchy = 'date_submitted'
    search_fields = ('comment', 'user__username')

class FreeThreadedCommentAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {'fields': ('content_type', 'object_id')}),
        (_('Parent'), {'fields' : ('parent',)}),
        (_('Content'), {'fields': ('name', 'website', 'email', 'comment')}),
        (_('Meta'), {'fields': ('date_submitted', 'date_modified', 'date_approved', 'is_public', 'ip_address', 'is_approved')}),
    )
    list_display = ('name', 'date_submitted', 'content_type', 'get_content_object', 'parent', '__unicode__')
    list_filter = ('date_submitted',)
    date_hierarchy = 'date_submitted'
    search_fields = ('comment', 'name', 'email', 'website')


admin.site.register(ThreadedComment, ThreadedCommentAdmin)
admin.site.register(FreeThreadedComment, FreeThreadedCommentAdmin)

########NEW FILE########
__FILENAME__ = forms
from django import forms
from threadedcomments.models import DEFAULT_MAX_COMMENT_LENGTH
from threadedcomments.models import FreeThreadedComment, ThreadedComment
from django.utils.translation import ugettext_lazy as _

class ThreadedCommentForm(forms.ModelForm):
    """
    Form which can be used to validate data for a new ThreadedComment.
    It consists of just two fields: ``comment``, and ``markup``.
    
    The ``comment`` field is the only one which is required.
    """

    comment = forms.CharField(
        label = _('comment'),
        max_length = DEFAULT_MAX_COMMENT_LENGTH,
        widget = forms.Textarea
    )

    class Meta:
        model = ThreadedComment
        fields = ('comment', 'markup')

class FreeThreadedCommentForm(forms.ModelForm):
    """
    Form which can be used to validate data for a new FreeThreadedComment.
    It consists of just a few fields: ``comment``, ``name``, ``website``,
    ``email``, and ``markup``.
    
    The fields ``comment``, and ``name`` are the only ones which are required.
    """

    comment = forms.CharField(
        label = _('comment'),
        max_length = DEFAULT_MAX_COMMENT_LENGTH,
        widget = forms.Textarea
    )

    class Meta:
        model = FreeThreadedComment
        fields = ('comment', 'name', 'website', 'email', 'markup')
########NEW FILE########
__FILENAME__ = migratecomments
from django.core.management.base import BaseCommand
from django.contrib.comments.models import Comment, FreeComment
from threadedcomments.models import ThreadedComment, FreeThreadedComment

class Command(BaseCommand):
    help = "Migrates Django's built-in django.contrib.comments data to threadedcomments data"
    
    output_transaction = True
    
    def handle(self, *args, **options):
        """
        Converts all legacy ``Comment`` and ``FreeComment`` objects into 
        ``ThreadedComment`` and ``FreeThreadedComment`` objects, respectively.
        """
        self.handle_free_comments()
        self.handle_comments()
    
    def handle_free_comments(self):
        """
        Converts all legacy ``FreeComment`` objects into ``FreeThreadedComment``
        objects.
        """
        comments = FreeComment.objects.all()
        for c in comments:
            new = FreeThreadedComment(
                content_type = c.content_type,
                object_id = c.object_id,
                comment = c.comment,
                name = c.person_name,
                website = '',
                email = '',
                date_submitted = c.submit_date,
                date_modified = c.submit_date,
                date_approved = c.submit_date,
                is_public = c.is_public,
                ip_address = c.ip_address,
                is_approved = c.approved
            )
            new.save()
    
    def handle_comments(self):
        """
        Converts all legacy ``Comment`` objects into ``ThreadedComment`` objects.
        """
        comments = Comment.objects.all()
        for c in comments:
            new = ThreadedComment(
                content_type = c.content_type,
                object_id = c.object_id,
                comment = c.comment,
                user = c.user,
                date_submitted = c.submit_date,
                date_modified = c.submit_date,
                date_approved = c.submit_date,
                is_public = c.is_public,
                ip_address = c.ip_address,
                is_approved = not c.is_removed
            )
            new.save()
########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.contrib.auth.models import User
from datetime import datetime
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.utils.encoding import force_unicode

DEFAULT_MAX_COMMENT_LENGTH = getattr(settings, 'DEFAULT_MAX_COMMENT_LENGTH', 1000)
DEFAULT_MAX_COMMENT_DEPTH = getattr(settings, 'DEFAULT_MAX_COMMENT_DEPTH', 8)

MARKDOWN = 1
TEXTILE = 2
REST = 3
#HTML = 4
PLAINTEXT = 5
MARKUP_CHOICES = (
    (MARKDOWN, _("markdown")),
    (TEXTILE, _("textile")),
    (REST, _("restructuredtext")),
#    (HTML, _("html")),
    (PLAINTEXT, _("plaintext")),
)

DEFAULT_MARKUP = getattr(settings, 'DEFAULT_MARKUP', PLAINTEXT)

def dfs(node, all_nodes, depth):
    """
    Performs a recursive depth-first search starting at ``node``.  This function
    also annotates an attribute, ``depth``, which is an integer that represents
    how deeply nested this node is away from the original object.
    """
    node.depth = depth
    to_return = [node,]
    for subnode in all_nodes:
        if subnode.parent and subnode.parent.id == node.id:
            to_return.extend(dfs(subnode, all_nodes, depth+1))
    return to_return

class ThreadedCommentManager(models.Manager):
    """
    A ``Manager`` which will be attached to each comment model.  It helps to facilitate
    the retrieval of comments in tree form and also has utility methods for
    creating and retrieving objects related to a specific content object.
    """
    def get_tree(self, content_object, root=None):
        """
        Runs a depth-first search on all comments related to the given content_object.
        This depth-first search adds a ``depth`` attribute to the comment which
        signifies how how deeply nested the comment is away from the original object.
        
        If root is specified, it will start the tree from that comment's ID.
        
        Ideally, one would use this ``depth`` attribute in the display of the comment to
        offset that comment by some specified length.
        
        The following is a (VERY) simple example of how the depth property might be used in a template:
        
            {% for comment in comment_tree %}
                <p style="margin-left: {{ comment.depth }}em">{{ comment.comment }}</p>
            {% endfor %}
        """
        content_type = ContentType.objects.get_for_model(content_object)
        children = list(self.get_query_set().filter(
            content_type = content_type,
            object_id = getattr(content_object, 'pk', getattr(content_object, 'id')),
        ).select_related().order_by('date_submitted'))
        to_return = []
        if root:
            if isinstance(root, int):
                root_id = root
            else:
                root_id = root.id
            to_return = [c for c in children if c.id == root_id]
            if to_return:
                to_return[0].depth = 0
                for child in children:
                    if child.parent_id == root_id:
                        to_return.extend(dfs(child, children, 1))
        else:
            for child in children:
                if not child.parent:
                    to_return.extend(dfs(child, children, 0))
        return to_return

    def _generate_object_kwarg_dict(self, content_object, **kwargs):
        """
        Generates the most comment keyword arguments for a given ``content_object``.
        """
        kwargs['content_type'] = ContentType.objects.get_for_model(content_object)
        kwargs['object_id'] = getattr(content_object, 'pk', getattr(content_object, 'id'))
        return kwargs

    def create_for_object(self, content_object, **kwargs):
        """
        A simple wrapper around ``create`` for a given ``content_object``.
        """
        return self.create(**self._generate_object_kwarg_dict(content_object, **kwargs))
    
    def get_or_create_for_object(self, content_object, **kwargs):
        """
        A simple wrapper around ``get_or_create`` for a given ``content_object``.
        """
        return self.get_or_create(**self._generate_object_kwarg_dict(content_object, **kwargs))
    
    def get_for_object(self, content_object, **kwargs):
        """
        A simple wrapper around ``get`` for a given ``content_object``.
        """
        return self.get(**self._generate_object_kwarg_dict(content_object, **kwargs))

    def all_for_object(self, content_object, **kwargs):
        """
        Prepopulates a QuerySet with all comments related to the given ``content_object``.
        """
        return self.filter(**self._generate_object_kwarg_dict(content_object, **kwargs))

class PublicThreadedCommentManager(ThreadedCommentManager):
    """
    A ``Manager`` which borrows all of the same methods from ``ThreadedCommentManager``,
    but which also restricts the queryset to only the published methods 
    (in other words, ``is_public = True``).
    """
    def get_query_set(self):
        return super(ThreadedCommentManager, self).get_query_set().filter(
            Q(is_public = True) | Q(is_approved = True)
        )

class ThreadedComment(models.Model):
    """
    A threaded comment which must be associated with an instance of 
    ``django.contrib.auth.models.User``.  It is given its hierarchy by
    a nullable relationship back on itself named ``parent``.
    
    This ``ThreadedComment`` supports several kinds of markup languages,
    including Textile, Markdown, and ReST.
    
    It also includes two Managers: ``objects``, which is the same as the normal
    ``objects`` Manager with a few added utility functions (see above), and
    ``public``, which has those same utility functions but limits the QuerySet to
    only those values which are designated as public (``is_public=True``).
    """
    # Generic Foreign Key Fields
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField(_('object ID'))
    content_object = generic.GenericForeignKey()
    
    # Hierarchy Field
    parent = models.ForeignKey('self', null=True, blank=True, default=None, related_name='children')
    
    # User Field
    user = models.ForeignKey(User)
    
    # Date Fields
    date_submitted = models.DateTimeField(_('date/time submitted'), default = datetime.now)
    date_modified = models.DateTimeField(_('date/time modified'), default = datetime.now)
    date_approved = models.DateTimeField(_('date/time approved'), default=None, null=True, blank=True)
    
    # Meat n' Potatoes
    comment = models.TextField(_('comment'))
    markup = models.IntegerField(choices=MARKUP_CHOICES, default=DEFAULT_MARKUP, null=True, blank=True)
    
    # Status Fields
    is_public = models.BooleanField(_('is public'), default = True)
    is_approved = models.BooleanField(_('is approved'), default = False)
    
    # Extra Field
    ip_address = models.IPAddressField(_('IP address'), null=True, blank=True)
    
    objects = ThreadedCommentManager()
    public = PublicThreadedCommentManager()
    
    def __unicode__(self):
        if len(self.comment) > 50:
            return self.comment[:50] + "..."
        return self.comment[:50]
    
    def save(self, **kwargs):
        if not self.markup:
            self.markup = DEFAULT_MARKUP
        self.date_modified = datetime.now()
        if not self.date_approved and self.is_approved:
            self.date_approved = datetime.now()
        super(ThreadedComment, self).save(**kwargs)
    
    def get_content_object(self):
        """
        Wrapper around the GenericForeignKey due to compatibility reasons
        and due to ``list_display`` limitations.
        """
        return self.content_object
    
    def get_base_data(self, show_dates=True):
        """
        Outputs a Python dictionary representing the most useful bits of
        information about this particular object instance.
        
        This is mostly useful for testing purposes, as the output from the
        serializer changes from run to run.  However, this may end up being
        useful for JSON and/or XML data exchange going forward and as the
        serializer system is changed.
        """
        markup = "plaintext"
        for markup_choice in MARKUP_CHOICES:
            if self.markup == markup_choice[0]:
                markup = markup_choice[1]
                break
        to_return = {
            'content_object' : self.content_object,
            'parent' : self.parent,
            'user' : self.user,
            'comment' : self.comment,
            'is_public' : self.is_public,
            'is_approved' : self.is_approved,
            'ip_address' : self.ip_address,
            'markup' : force_unicode(markup),
        }
        if show_dates:
            to_return['date_submitted'] = self.date_submitted
            to_return['date_modified'] = self.date_modified
            to_return['date_approved'] = self.date_approved
        return to_return
    
    class Meta:
        ordering = ('-date_submitted',)
        verbose_name = _("Threaded Comment")
        verbose_name_plural = _("Threaded Comments")
        get_latest_by = "date_submitted"

    
class FreeThreadedComment(models.Model):
    """
    A threaded comment which need not be associated with an instance of 
    ``django.contrib.auth.models.User``.  Instead, it requires minimally a name,
    and maximally a name, website, and e-mail address.  It is given its hierarchy
    by a nullable relationship back on itself named ``parent``.
    
    This ``FreeThreadedComment`` supports several kinds of markup languages,
    including Textile, Markdown, and ReST.
    
    It also includes two Managers: ``objects``, which is the same as the normal
    ``objects`` Manager with a few added utility functions (see above), and
    ``public``, which has those same utility functions but limits the QuerySet to
    only those values which are designated as public (``is_public=True``).
    """
    # Generic Foreign Key Fields
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField(_('object ID'))
    content_object = generic.GenericForeignKey()
    
    # Hierarchy Field
    parent = models.ForeignKey('self', null = True, blank=True, default = None, related_name='children')
    
    # User-Replacement Fields
    name = models.CharField(_('name'), max_length = 128)
    website = models.URLField(_('site'), blank = True)
    email = models.EmailField(_('e-mail address'), blank = True)
    
    # Date Fields
    date_submitted = models.DateTimeField(_('date/time submitted'), default = datetime.now)
    date_modified = models.DateTimeField(_('date/time modified'), default = datetime.now)
    date_approved = models.DateTimeField(_('date/time approved'), default=None, null=True, blank=True)
    
    # Meat n' Potatoes
    comment = models.TextField(_('comment'))
    markup = models.IntegerField(choices=MARKUP_CHOICES, default=DEFAULT_MARKUP, null=True, blank=True)
    
    # Status Fields
    is_public = models.BooleanField(_('is public'), default = True)
    is_approved = models.BooleanField(_('is approved'), default = False)
    
    # Extra Field
    ip_address = models.IPAddressField(_('IP address'), null=True, blank=True)
    
    objects = ThreadedCommentManager()
    public = PublicThreadedCommentManager()
    
    def __unicode__(self):
        if len(self.comment) > 50:
            return self.comment[:50] + "..."
        return self.comment[:50]
    
    def save(self, **kwargs):
        if not self.markup:
            self.markup = DEFAULT_MARKUP
        self.date_modified = datetime.now()
        if not self.date_approved and self.is_approved:
            self.date_approved = datetime.now()
        super(FreeThreadedComment, self).save()
    
    def get_content_object(self, **kwargs):
        """
        Wrapper around the GenericForeignKey due to compatibility reasons
        and due to ``list_display`` limitations.
        """
        return self.content_object
    
    def get_base_data(self, show_dates=True):
        """
        Outputs a Python dictionary representing the most useful bits of
        information about this particular object instance.
        
        This is mostly useful for testing purposes, as the output from the
        serializer changes from run to run.  However, this may end up being
        useful for JSON and/or XML data exchange going forward and as the
        serializer system is changed.
        """
        markup = "plaintext"
        for markup_choice in MARKUP_CHOICES:
            if self.markup == markup_choice[0]:
                markup = markup_choice[1]
                break
        to_return = {
            'content_object' : self.content_object,
            'parent' : self.parent,
            'name' : self.name,
            'website' : self.website,
            'email' : self.email,
            'comment' : self.comment,
            'is_public' : self.is_public,
            'is_approved' : self.is_approved,
            'ip_address' : self.ip_address,
            'markup' : force_unicode(markup),
        }
        if show_dates:
            to_return['date_submitted'] = self.date_submitted
            to_return['date_modified'] = self.date_modified
            to_return['date_approved'] = self.date_approved
        return to_return
    
    class Meta:
        ordering = ('-date_submitted',)
        verbose_name = _("Free Threaded Comment")
        verbose_name_plural = _("Free Threaded Comments")
        get_latest_by = "date_submitted"


class TestModel(models.Model):
    """
    This model is simply used by this application's test suite as a model to 
    which to attach comments.
    """
    name = models.CharField(max_length=5)
    is_public = models.BooleanField(default=True)
    date = models.DateTimeField(default=datetime.now)

########NEW FILE########
__FILENAME__ = moderation
from django.db.models import signals
from threadedcomments.models import ThreadedComment, FreeThreadedComment, MARKUP_CHOICES
from threadedcomments.models import DEFAULT_MAX_COMMENT_LENGTH, DEFAULT_MAX_COMMENT_DEPTH
from comment_utils import moderation

MARKUP_CHOICES_IDS = [c[0] for c in MARKUP_CHOICES]


class CommentModerator(moderation.CommentModerator):
    max_comment_length = DEFAULT_MAX_COMMENT_LENGTH
    allowed_markup = MARKUP_CHOICES_IDS
    max_depth = DEFAULT_MAX_COMMENT_DEPTH

    def _is_past_max_depth(self, comment):
        i = 1
        c = comment.parent
        while c != None:
            c = c.parent
            i = i + 1
            if i > self.max_depth:
                return True
        return False

    def allow(self, comment, content_object):
        if self._is_past_max_depth(comment):
            return False
        if comment.markup not in self.allowed_markup:
            return False
        return super(CommentModerator, self).allow(comment, content_object)

    def moderate(self, comment, content_object):
        if len(comment.comment) > self.max_comment_length:
            return True
        return super(CommentModerator, self).moderate(comment, content_object)

class Moderator(moderation.Moderator):
    def connect(self):
        for model in (ThreadedComment, FreeThreadedComment):
            signals.pre_save.connect(self.pre_save_moderation, sender=model)
            signals.post_save.connect(self.post_save_moderation, sender=model)
    
    ## THE FOLLOWING ARE HACKS UNTIL django-comment-utils GETS UPDATED SIGNALS ####
    def pre_save_moderation(self, sender=None, instance=None, **kwargs):
        return super(Moderator, self).pre_save_moderation(sender, instance)

    def post_save_moderation(self, sender=None, instance=None, **kwargs):
        return super(Moderator, self).post_save_moderation(sender, instance)


# Instantiate the ``Moderator`` so that other modules can import and 
# begin to register with it.

moderator = Moderator()
########NEW FILE########
__FILENAME__ = gravatar
from django import template
from django.conf import settings
from django.template.defaultfilters import stringfilter
from django.utils.encoding import smart_str
from django.utils.safestring import mark_safe
import md5
import urllib

GRAVATAR_MAX_RATING = getattr(settings, 'GRAVATAR_MAX_RATING', 'R')
GRAVATAR_DEFAULT_IMG = getattr(settings, 'GRAVATAR_DEFAULT_IMG', 'img:blank')
GRAVATAR_SIZE = getattr(settings, 'GRAVATAR_SIZE', 80)

GRAVATAR_URL = u'http://www.gravatar.com/avatar.php?gravatar_id=%(hash)s&rating=%(rating)s&size=%(size)s&default=%(default)s'

def get_gravatar_url(parser, token):
    """
    Generates a gravatar image URL based on the given parameters.
        
    Format is as follows (The square brackets indicate that those arguments are 
    optional.)::
    
        {% get_gravatar_url for myemailvar [rating "R" size 80 default img:blank as gravatar_url] %}
    
    Rating, size, and default may be either literal values or template variables.
    The template tag will attempt to resolve variables first, and on resolution
    failure it will use the literal value.
    
    If ``as`` is not specified, the URL will be output to the template in place.
    
    For all other arguments that are not specified, the appropriate default 
    settings attribute will be used instead.
    """
    words = token.contents.split()
    tagname = words.pop(0)
    if len(words) < 2:
        raise template.TemplateSyntaxError, "%r tag: At least one argument should be provided." % tagname
    if words.pop(0) != "for":
        raise template.TemplateSyntaxError, "%r tag: Syntax is {% get_gravatar_url for myemailvar rating "R" size 80 default img:blank as gravatar_url %}, where everything after myemailvar is optional."
    email = words.pop(0)
    if len(words) % 2 != 0:
        raise template.TemplateSyntaxError, "%r tag: Imbalanced number of arguments." % tagname
    args = {
        'email': email,
        'rating': GRAVATAR_MAX_RATING,
        'size': GRAVATAR_SIZE,
        'default': GRAVATAR_DEFAULT_IMG,
    }
    for name, value in zip(words[::2], words[1::2]):
        name = name.lower()
        if name not in ('rating', 'size', 'default', 'as'):
            raise template.TemplateSyntaxError, "%r tag: Invalid argument %r." % tagname, name
        args[smart_str(name)] = value
    return GravatarUrlNode(**args)

class GravatarUrlNode(template.Node):
    def __init__(self, email=None, rating=GRAVATAR_MAX_RATING, size=GRAVATAR_SIZE, 
        default=GRAVATAR_DEFAULT_IMG, **other_kwargs):
        self.email = template.Variable(email)
        self.rating = template.Variable(rating)
        try:
            self.size = template.Variable(size)
        except:
            self.size = size
        self.default = template.Variable(default)
        self.other_kwargs = other_kwargs

    def render(self, context):
        # Try to resolve the variables.  If they are not resolve-able, then use
        # the provided name itself.
        try:
            email = self.email.resolve(context)
        except template.VariableDoesNotExist:
            email = self.email.var
        try:
            rating = self.rating.resolve(context)
        except template.VariableDoesNotExist:
            rating = self.rating.var
        try:
            size = self.size.resolve(context)
        except template.VariableDoesNotExist:
            size = self.size.var
        except AttributeError:
            size = self.size
        try:
            default = self.default.resolve(context)
        except template.VariableDoesNotExist:
            default = self.default.var
        
        gravatargs = {
            'hash': md5.new(email).hexdigest(),
            'rating': rating,
            'size': size,
            'default': urllib.quote_plus(default),
        }
        url = GRAVATAR_URL % gravatargs
        if 'as' in self.other_kwargs:
            context[self.other_kwargs['as']] = mark_safe(url)
            return ''
        return url

def gravatar(email):
    """
    Takes an e-mail address and returns a gravatar image URL, using properties
    from the django settings file.
    """
    hashed_email = md5.new(email).hexdigest()
    return mark_safe(GRAVATAR_URL % {
        'hash': hashed_email,
        'rating': GRAVATAR_MAX_RATING, 
        'size': GRAVATAR_SIZE,
        'default': urllib.quote_plus(GRAVATAR_DEFAULT_IMG),
    })
gravatar = stringfilter(gravatar)


register = template.Library()
register.filter('gravatar', gravatar)
register.tag('get_gravatar_url', get_gravatar_url)

########NEW FILE########
__FILENAME__ = threadedcommentstags
import re
from django import template
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe
from threadedcomments.models import ThreadedComment, FreeThreadedComment
from threadedcomments.forms import ThreadedCommentForm, FreeThreadedCommentForm

# Regular expressions for getting rid of newlines and witespace
inbetween = re.compile('>[ \r\n]+<')
newlines = re.compile('\r|\n')

def get_contenttype_kwargs(content_object):
    """
    Gets the basic kwargs necessary for almost all of the following tags.
    """
    kwargs = {
        'content_type' : ContentType.objects.get_for_model(content_object).id,
        'object_id' : getattr(content_object, 'pk', getattr(content_object, 'id')),
    }
    return kwargs

def get_comment_url(content_object, parent=None):
    """
    Given an object and an optional parent, this tag gets the URL to POST to for the
    creation of new ``ThreadedComment`` objects.
    """
    kwargs = get_contenttype_kwargs(content_object)
    if parent:
        if not isinstance(parent, ThreadedComment):
            raise template.TemplateSyntaxError, "get_comment_url requires its parent object to be of type ThreadedComment"
        kwargs.update({'parent_id' : getattr(parent, 'pk', getattr(parent, 'id'))})
        return reverse('tc_comment_parent', kwargs=kwargs)
    else:
        return reverse('tc_comment', kwargs=kwargs)

def get_comment_url_ajax(content_object, parent=None, ajax_type='json'):
    """
    Given an object and an optional parent, this tag gets the URL to POST to for the
    creation of new ``ThreadedComment`` objects.  It returns the latest created object
    in the AJAX form of the user's choosing (json or xml).
    """
    kwargs = get_contenttype_kwargs(content_object)
    kwargs.update({'ajax' : ajax_type})
    if parent:
        if not isinstance(parent, ThreadedComment):
            raise template.TemplateSyntaxError, "get_comment_url_ajax requires its parent object to be of type ThreadedComment"
        kwargs.update({'parent_id' : getattr(parent, 'pk', getattr(parent, 'id'))})
        return reverse('tc_comment_parent_ajax', kwargs=kwargs)
    else:
        return reverse('tc_comment_ajax', kwargs=kwargs)

def get_comment_url_json(content_object, parent=None):
    """
    Wraps ``get_comment_url_ajax`` with ``ajax_type='json'``
    """
    try:
        return get_comment_url_ajax(content_object, parent, ajax_type="json")
    except template.TemplateSyntaxError:
        raise template.TemplateSyntaxError, "get_comment_url_json requires its parent object to be of type ThreadedComment"
    return ''

def get_comment_url_xml(content_object, parent=None):
    """
    Wraps ``get_comment_url_ajax`` with ``ajax_type='xml'``
    """
    try:
        return get_comment_url_ajax(content_object, parent, ajax_type="xml")
    except template.TemplateSyntaxError:
        raise template.TemplateSyntaxError, "get_comment_url_xml requires its parent object to be of type ThreadedComment"
    return ''

def get_free_comment_url(content_object, parent=None):
    """
    Given an object and an optional parent, this tag gets the URL to POST to for the
    creation of new ``FreeThreadedComment`` objects.
    """
    kwargs = get_contenttype_kwargs(content_object)
    if parent:
        if not isinstance(parent, FreeThreadedComment):
            raise template.TemplateSyntaxError, "get_free_comment_url requires its parent object to be of type FreeThreadedComment"
        kwargs.update({'parent_id' : getattr(parent, 'pk', getattr(parent, 'id'))})
        return reverse('tc_free_comment_parent', kwargs=kwargs)
    else:
        return reverse('tc_free_comment', kwargs=kwargs)

def get_free_comment_url_ajax(content_object, parent=None, ajax_type='json'):
    """
    Given an object and an optional parent, this tag gets the URL to POST to for the
    creation of new ``FreeThreadedComment`` objects.  It returns the latest created object
    in the AJAX form of the user's choosing (json or xml).
    """
    kwargs = get_contenttype_kwargs(content_object)
    kwargs.update({'ajax' : ajax_type})
    if parent:
        if not isinstance(parent, FreeThreadedComment):
            raise template.TemplateSyntaxError, "get_free_comment_url_ajax requires its parent object to be of type FreeThreadedComment"
        kwargs.update({'parent_id' : getattr(parent, 'pk', getattr(parent, 'id'))})
        return reverse('tc_free_comment_parent_ajax', kwargs=kwargs)
    else:
        return reverse('tc_free_comment_ajax', kwargs=kwargs)

def get_free_comment_url_json(content_object, parent=None):
    """
    Wraps ``get_free_comment_url_ajax`` with ``ajax_type='json'``
    """
    try:
        return get_free_comment_url_ajax(content_object, parent, ajax_type="json")
    except template.TemplateSyntaxError:
        raise template.TemplateSyntaxError, "get_free_comment_url_json requires its parent object to be of type FreeThreadedComment"
    return ''

def get_free_comment_url_xml(content_object, parent=None):
    """
    Wraps ``get_free_comment_url_ajax`` with ``ajax_type='xml'``
    """
    try:
        return get_free_comment_url_ajax(content_object, parent, ajax_type="xml")
    except template.TemplateSyntaxError:
        raise template.TemplateSyntaxError, "get_free_comment_url_xml requires its parent object to be of type FreeThreadedComment"
    return ''

def auto_transform_markup(comment):
    """
    Given a comment (``ThreadedComment`` or ``FreeThreadedComment``), this tag
    looks up the markup type of the comment and formats the output accordingly.
    
    It can also output the formatted content to a context variable, if a context name is
    specified.
    """
    try:
        from django.utils.html import escape
        from threadedcomments.models import MARKDOWN, TEXTILE, REST, PLAINTEXT
        if comment.markup == MARKDOWN:
            from django.contrib.markup.templatetags.markup import markdown
            return markdown(comment.comment)
        elif comment.markup == TEXTILE:
            from django.contrib.markup.templatetags.markup import textile
            return textile(comment.comment)
        elif comment.markup == REST:
            from django.contrib.markup.templatetags.markup import restructuredtext
            return restructuredtext(comment.comment)
#        elif comment.markup == HTML:
#            return mark_safe(force_unicode(comment.comment))
        elif comment.markup == PLAINTEXT:
            return escape(comment.comment)
    except ImportError:
        # Not marking safe, in case tag fails and users input malicious code.
        return force_unicode(comment.comment)

def do_auto_transform_markup(parser, token):
    try:
        split = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag must be of format {%% %r COMMENT %%} or of format {%% %r COMMENT as CONTEXT_VARIABLE %%}" % (token.contents.split()[0], token.contents.split()[0], token.contents.split()[0])
    if len(split) == 2:
        return AutoTransformMarkupNode(split[1])
    elif len(split) == 4:
        return AutoTransformMarkupNode(split[1], context_name=split[3])
    else:
        raise template.TemplateSyntaxError, "Invalid number of arguments for tag %r" % split[0]

class AutoTransformMarkupNode(template.Node):
    def __init__(self, comment, context_name=None):
        self.comment = template.Variable(comment)
        self.context_name = context_name
    def render(self, context):
        comment = self.comment.resolve(context)
        if self.context_name:
            context[self.context_name] = auto_transform_markup(comment)
            return ''
        else:
            return auto_transform_markup(comment)

def do_get_threaded_comment_tree(parser, token):
    """
    Gets a tree (list of objects ordered by preorder tree traversal, and with an
    additional ``depth`` integer attribute annotated onto each ``ThreadedComment``.
    """
    error_string = "%r tag must be of format {%% get_threaded_comment_tree for OBJECT [TREE_ROOT] as CONTEXT_VARIABLE %%}" % token.contents.split()[0]
    try:
        split = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError(error_string)
    if len(split) == 5:
        return CommentTreeNode(split[2], split[4], split[3])
    elif len(split) == 6:
        return CommentTreeNode(split[2], split[5], split[3])
    else:
        raise template.TemplateSyntaxError(error_string)

def do_get_free_threaded_comment_tree(parser, token):
    """
    Gets a tree (list of objects ordered by traversing tree in preorder, and with an
    additional ``depth`` integer attribute annotated onto each ``FreeThreadedComment.``
    """
    error_string = "%r tag must be of format {%% get_free_threaded_comment_tree for OBJECT [TREE_ROOT] as CONTEXT_VARIABLE %%}" % token.contents.split()[0]
    try:
        split = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError(error_string)
    if len(split) == 5:
        return FreeCommentTreeNode(split[2], split[4], split[3])
    elif len(split) == 6:
        return FreeCommentTreeNode(split[2], split[5], split[3])
    else:
        raise template.TemplateSyntaxError(error_string)

class CommentTreeNode(template.Node):
    def __init__(self, content_object, context_name, tree_root):
        self.content_object = template.Variable(content_object)
        self.tree_root = template.Variable(tree_root)
        self.tree_root_str = tree_root
        self.context_name = context_name
    def render(self, context):
        content_object = self.content_object.resolve(context)
        try:
            tree_root = self.tree_root.resolve(context)
        except template.VariableDoesNotExist:
            if self.tree_root_str == 'as':
                tree_root = None
            else:
                try:
                    tree_root = int(self.tree_root_str)
                except ValueError:
                    tree_root = self.tree_root_str
        context[self.context_name] = ThreadedComment.public.get_tree(content_object, root=tree_root)
        return ''

class FreeCommentTreeNode(template.Node):
    def __init__(self, content_object, context_name, tree_root):
        self.content_object = template.Variable(content_object)
        self.tree_root = template.Variable(tree_root)
        self.tree_root_str = tree_root
        self.context_name = context_name
    def render(self, context):
        content_object = self.content_object.resolve(context)
        try:
            tree_root = self.tree_root.resolve(context)
        except template.VariableDoesNotExist:
            if self.tree_root_str == 'as':
                tree_root = None
            else:
                try:
                    tree_root = int(self.tree_root_str)
                except ValueError:
                    tree_root = self.tree_root_str
        context[self.context_name] = FreeThreadedComment.public.get_tree(content_object, root=tree_root)
        return ''

def do_get_comment_count(parser, token):
    """
    Gets a count of how many ThreadedComment objects are attached to the given
    object.
    """
    error_message = "%r tag must be of format {%% %r for OBJECT as CONTEXT_VARIABLE %%}" % (token.contents.split()[0], token.contents.split()[0])
    try:
        split = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, error_message
    if split[1] != 'for' or split[3] != 'as':
        raise template.TemplateSyntaxError, error_message
    return ThreadedCommentCountNode(split[2], split[4])

class ThreadedCommentCountNode(template.Node):
    def __init__(self, content_object, context_name):
        self.content_object = template.Variable(content_object)
        self.context_name = context_name
    def render(self, context):
        content_object = self.content_object.resolve(context)
        context[self.context_name] = ThreadedComment.public.all_for_object(content_object).count()
        return ''
        
def do_get_free_comment_count(parser, token):
    """
    Gets a count of how many FreeThreadedComment objects are attached to the 
    given object.
    """
    error_message = "%r tag must be of format {%% %r for OBJECT as CONTEXT_VARIABLE %%}" % (token.contents.split()[0], token.contents.split()[0])
    try:
        split = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, error_message
    if split[1] != 'for' or split[3] != 'as':
        raise template.TemplateSyntaxError, error_message
    return FreeThreadedCommentCountNode(split[2], split[4])

class FreeThreadedCommentCountNode(template.Node):
    def __init__(self, content_object, context_name):
        self.content_object = template.Variable(content_object)
        self.context_name = context_name
    def render(self, context):
        content_object = self.content_object.resolve(context)
        context[self.context_name] = FreeThreadedComment.public.all_for_object(content_object).count()
        return ''

def oneline(value):
    """
    Takes some HTML and gets rid of newlines and spaces between tags, rendering
    the result all on one line.
    """
    try:
        return mark_safe(newlines.sub('', inbetween.sub('><', value)))
    except:
        return value

def do_get_threaded_comment_form(parser, token):
    """
    Gets a FreeThreadedCommentForm and inserts it into the context.
    """
    error_message = "%r tag must be of format {%% %r as CONTEXT_VARIABLE %%}" % (token.contents.split()[0], token.contents.split()[0])
    try:
        split = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, error_message
    if split[1] != 'as':
        raise template.TemplateSyntaxError, error_message
    if len(split) != 3:
        raise template.TemplateSyntaxError, error_message
    if "free" in split[0]:
        is_free = True
    else:
        is_free = False
    return ThreadedCommentFormNode(split[2], free=is_free)

class ThreadedCommentFormNode(template.Node):
    def __init__(self, context_name, free=False):
        self.context_name = context_name
        self.free = free
    def render(self, context):
        if self.free:
            form = FreeThreadedCommentForm()
        else:
            form = ThreadedCommentForm()
        context[self.context_name] = form
        return ''

def do_get_latest_comments(parser, token):
    """
    Gets the latest comments by date_submitted.
    """
    error_message = "%r tag must be of format {%% %r NUM_TO_GET as CONTEXT_VARIABLE %%}" % (token.contents.split()[0], token.contents.split()[0])
    try:
        split = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, error_message
    if len(split) != 4:
        raise template.TemplateSyntaxError, error_message
    if split[2] != 'as':
        raise template.TemplateSyntaxError, error_message
    if "free" in split[0]:
        is_free = True
    else:
        is_free = False
    return LatestCommentsNode(split[1], split[3], free=is_free)

class LatestCommentsNode(template.Node):
    def __init__(self, num, context_name, free=False):
        self.num = num
        self.context_name = context_name
        self.free = free
    def render(self, context):
        if self.free:
            comments = FreeThreadedComment.objects.order_by('-date_submitted')[:self.num]
        else:
            comments = ThreadedComment.objects.order_by('-date_submitted')[:self.num]
        context[self.context_name] = comments
        return ''

def do_get_user_comments(parser, token):
    """
    Gets all comments submitted by a particular user.
    """
    error_message = "%r tag must be of format {%% %r for OBJECT as CONTEXT_VARIABLE %%}" % (token.contents.split()[0], token.contents.split()[0])
    try:
        split = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, error_message
    if len(split) != 5:
        raise template.TemplateSyntaxError, error_message
    return UserCommentsNode(split[2], split[4])

class UserCommentsNode(template.Node):
    def __init__(self, user, context_name):
        self.user = template.Variable(user)
        self.context_name = context_name
    def render(self, context):
        user = self.user.resolve(context)
        context[self.context_name] = user.threadedcomment_set.all()
        return ''

def do_get_user_comment_count(parser, token):
    """
    Gets the count of all comments submitted by a particular user.
    """
    error_message = "%r tag must be of format {%% %r for OBJECT as CONTEXT_VARIABLE %%}" % (token.contents.split()[0], token.contents.split()[0])
    try:
        split = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, error_message
    if len(split) != 5:
        raise template.TemplateSyntaxError, error_message
    return UserCommentCountNode(split[2], split[4])

class UserCommentCountNode(template.Node):
    def __init__(self, user, context_name):
        self.user = template.Variable(user)
        self.context_name = context_name
    def render(self, context):
        user = self.user.resolve(context)
        context[self.context_name] = user.threadedcomment_set.all().count()
        return ''

register = template.Library()
register.simple_tag(get_comment_url)
register.simple_tag(get_comment_url_json)
register.simple_tag(get_comment_url_xml)
register.simple_tag(get_free_comment_url)
register.simple_tag(get_free_comment_url_json)
register.simple_tag(get_free_comment_url_xml)

register.filter('oneline', oneline)

register.tag('auto_transform_markup', do_auto_transform_markup)
register.tag('get_threaded_comment_tree', do_get_threaded_comment_tree)
register.tag('get_free_threaded_comment_tree', do_get_free_threaded_comment_tree)
register.tag('get_comment_count', do_get_comment_count)
register.tag('get_free_comment_count', do_get_free_comment_count)
register.tag('get_free_threaded_comment_form', do_get_threaded_comment_form)
register.tag('get_threaded_comment_form', do_get_threaded_comment_form)
register.tag('get_latest_comments', do_get_latest_comments)
register.tag('get_latest_free_comments', do_get_latest_comments)
register.tag('get_user_comments', do_get_user_comments)
register.tag('get_user_comment_count', do_get_user_comment_count)
########NEW FILE########
__FILENAME__ = tests
"""
##################################
### Model and Moderation Tests ###
##################################
>>> import datetime
>>> from threadedcomments.models import FreeThreadedComment, ThreadedComment, TestModel
>>> from threadedcomments.models import MARKDOWN, TEXTILE, REST, PLAINTEXT
>>> from django.contrib.auth.models import User
>>> from django.contrib.contenttypes.models import ContentType
>>> from threadedcomments.moderation import moderator, CommentModerator
>>> from django.core import mail

>>> topic = TestModel.objects.create(name = "Test")
>>> user = User.objects.create_user('user', 'floguy@gmail.com', password='password')
>>> user2 = User.objects.create_user('user2', 'floguy@gmail.com', password='password')

  #######################
  ### ThreadedComment ###
  #######################

>>> comment1 = ThreadedComment.objects.create_for_object(
...     topic, user = user, ip_address = '127.0.0.1',
...     comment = 'This is fun!  This is very fun!',
... )
>>> comment2 = ThreadedComment.objects.create_for_object(
...     topic, user = user, ip_address = '127.0.0.1',
...     comment = 'This is stupid!  I hate it!',
... )
>>> comment3 = ThreadedComment.objects.create_for_object(
...     topic, user = user, ip_address = '127.0.0.1', parent = comment2,
...     comment = 'I agree, the first comment was wrong and you are right!',
... )
>>> comment4 = ThreadedComment.objects.create_for_object(
...     topic, user = user, ip_address = '127.0.0.1',
...     comment = 'What are we talking about?',
... )
>>> comment5 = ThreadedComment.objects.create_for_object(
...     topic, user = user, ip_address = '127.0.0.1', parent = comment3,
...     comment = "I'm a fanboy!",
... )
>>> comment6 = ThreadedComment.objects.create_for_object(
...     topic, user = user, ip_address = '127.0.0.1', parent = comment1,
...     comment = "What are you talking about?",
... )

>>> class Moderator1(CommentModerator):
...     enable_field = 'is_public'
...     auto_close_field = 'date'
...     close_after = 15
>>> moderator.register(TestModel, Moderator1)

>>> comment7 = ThreadedComment.objects.create_for_object(
...     topic, user = user, ip_address = '127.0.0.1',
...     comment = "Post moderator addition.  Does it still work?",
... )

>>> topic.is_public = False
>>> topic.save()

>>> comment8 = ThreadedComment.objects.create_for_object(
...     topic, user = user, ip_address = '127.0.0.1', parent = comment7,
...     comment = "This should not appear, due to enable_field",
... )

>>> moderator.unregister(TestModel)

>>> comment9 = ThreadedComment.objects.create_for_object(
...     topic, user = user, ip_address = '127.0.0.1',
...     comment = "This should appear again, due to unregistration",
... )

>>> len(mail.outbox)
0

>>> class Moderator2(CommentModerator):
...     enable_field = 'is_public'
...     auto_close_field = 'date'
...     close_after = 15
...     akismet = False
...     email_notification = True
>>> moderator.register(TestModel, Moderator2)

>>> comment10 = ThreadedComment.objects.create_for_object(
...     topic, user = user, ip_address = '127.0.0.1',
...     comment = "This should not appear again, due to registration with a new manager.",
... )

>>> topic.is_public = True
>>> topic.save()

>>> comment11 = ThreadedComment.objects.create_for_object(
...     topic, user = user, ip_address = '127.0.0.1', parent = comment1,
...     comment = "This should appear again.",
... )

>>> len(mail.outbox)
1
>>> mail.outbox = []

>>> topic.date = topic.date - datetime.timedelta(days = 20)
>>> topic.save()

>>> comment12 = ThreadedComment.objects.create_for_object(
...     topic, user = user, ip_address = '127.0.0.1', parent = comment7,
...     comment = "This shouldn't appear, due to close_after=15.",
... )

>>> topic.date = topic.date + datetime.timedelta(days = 20)
>>> topic.save()

>>> moderator.unregister(TestModel)

>>> class Moderator3(CommentModerator):
...     max_comment_length = 10
>>> moderator.register(TestModel, Moderator3)

>>> comment13 = ThreadedComment.objects.create_for_object(
...     topic, user = user, ip_address = '127.0.0.1', parent = comment7,
...     comment = "This shouldn't appear because it has more than 10 chars.",
... )

>>> comment14 = ThreadedComment.objects.create_for_object(
...     topic, user = user, ip_address = '127.0.0.1', parent = comment7,
...     comment = "<10chars",
... )

>>> moderator.unregister(TestModel)
>>> class Moderator4(CommentModerator):
...     allowed_markup = [REST,]
>>> moderator.register(TestModel, Moderator4)

>>> comment15 = ThreadedComment.objects.create_for_object(
...     topic, user = user, ip_address = '127.0.0.1', parent = comment7,
...     comment = "INVALID Markup.  Should not show up.", markup=TEXTILE
... )

>>> comment16 = ThreadedComment.objects.create_for_object(
...     topic, user = user, ip_address = '127.0.0.1', parent = comment7,
...     comment = "VALID Markup.  Should show up.", markup=REST
... )

>>> moderator.unregister(TestModel)

>>> tree = ThreadedComment.public.get_tree(topic)
>>> for comment in tree:
...     print "%s %s" % ("    " * comment.depth, comment.comment)
 This is fun!  This is very fun!
     What are you talking about?
     This should appear again.
 This is stupid!  I hate it!
     I agree, the first comment was wrong and you are right!
         I'm a fanboy!
 What are we talking about?
 Post moderator addition.  Does it still work?
     <10chars
     VALID Markup.  Should show up.
 This should appear again, due to unregistration

>>> tree = ThreadedComment.objects.get_tree(topic)
>>> for comment in tree:
...     print "%s %s" % ("    " * comment.depth, comment.comment)
 This is fun!  This is very fun!
     What are you talking about?
     This should appear again.
 This is stupid!  I hate it!
     I agree, the first comment was wrong and you are right!
         I'm a fanboy!
 What are we talking about?
 Post moderator addition.  Does it still work?
     This shouldn't appear because it has more than 10 chars.
     <10chars
     VALID Markup.  Should show up.
 This should appear again, due to unregistration

>>> tree = ThreadedComment.objects.get_tree(topic, root=comment2)
>>> for comment in tree:
...     print "%s %s" % ("    " * comment.depth, comment.comment)
 This is stupid!  I hate it!
     I agree, the first comment was wrong and you are right!
         I'm a fanboy!

>>> tree = ThreadedComment.objects.get_tree(topic, root=comment2.id)
>>> for comment in tree:
...     print "%s %s" % ("    " * comment.depth, comment.comment)
 This is stupid!  I hate it!
     I agree, the first comment was wrong and you are right!
         I'm a fanboy!
>>>

  ###########################
  ### FreeThreadedComment ###
  ###########################

>>> fcomment1 = FreeThreadedComment.objects.create_for_object(
...     topic, name = "Eric", ip_address = '127.0.0.1',
...     comment = 'This is fun!  This is very fun!',
... )
>>> fcomment2 = FreeThreadedComment.objects.create_for_object(
...     topic, name = "Eric", ip_address = '127.0.0.1',
...     comment = 'This is stupid!  I hate it!',
... )
>>> fcomment3 = FreeThreadedComment.objects.create_for_object(
...     topic, name = "Eric", ip_address = '127.0.0.1', parent = fcomment2,
...     comment = 'I agree, the first comment was wrong and you are right!',
... )
>>> fcomment4 = FreeThreadedComment.objects.create_for_object(
...     topic, name = "Eric", ip_address = '127.0.0.1', 
...     website="http://www.eflorenzano.com/", email="floguy@gmail.com",
...     comment = 'What are we talking about?',
... )
>>> fcomment5 = FreeThreadedComment.objects.create_for_object(
...     topic, name = "Eric", ip_address = '127.0.0.1', parent = fcomment3,
...     comment = "I'm a fanboy!",
... )
>>> fcomment6 = FreeThreadedComment.objects.create_for_object(
...     topic, name = "Eric", ip_address = '127.0.0.1', parent = fcomment1,
...     comment = "What are you talking about?",
... )

>>> moderator.register(TestModel, Moderator1)

>>> fcomment7 = FreeThreadedComment.objects.create_for_object(
...     topic, name = "Eric", ip_address = '127.0.0.1',
...     comment = "Post moderator addition.  Does it still work?",
... )

>>> topic.is_public = False
>>> topic.save()

>>> fcomment8 = FreeThreadedComment.objects.create_for_object(
...     topic, name = "Eric", ip_address = '127.0.0.1', parent = fcomment7,
...     comment = "This should not appear, due to enable_field",
... )

>>> moderator.unregister(TestModel)

>>> fcomment9 = FreeThreadedComment.objects.create_for_object(
...     topic, name = "Eric", ip_address = '127.0.0.1',
...     comment = "This should appear again, due to unregistration",
... )

>>> len(mail.outbox)
0

>>> moderator.register(TestModel, Moderator2)

>>> fcomment10 = FreeThreadedComment.objects.create_for_object(
...     topic, name = "Eric", ip_address = '127.0.0.1',
...     comment = "This should not appear again, due to registration with a new manager.",
... )

>>> topic.is_public = True
>>> topic.save()

>>> fcomment11 = FreeThreadedComment.objects.create_for_object(
...     topic, name = "Eric", ip_address = '127.0.0.1', parent = fcomment1,
...     comment = "This should appear again.",
... )

>>> len(mail.outbox)
1
>>> mail.outbox = []

>>> topic.date = topic.date - datetime.timedelta(days = 20)
>>> topic.save()

>>> fcomment12 = FreeThreadedComment.objects.create_for_object(
...     topic, name = "Eric", ip_address = '127.0.0.1', parent = fcomment7,
...     comment = "This shouldn't appear, due to close_after=15.",
... )

>>> topic.date = topic.date + datetime.timedelta(days = 20)
>>> topic.save()

>>> moderator.unregister(TestModel)
>>> moderator.register(TestModel, Moderator3)

>>> fcomment13 = FreeThreadedComment.objects.create_for_object(
...     topic, name = "Eric", ip_address = '127.0.0.1', parent = fcomment7,
...     comment = "This shouldn't appear because it has more than 10 chars.",
... )

>>> fcomment14 = FreeThreadedComment.objects.create_for_object(
...     topic, name = "Eric", ip_address = '127.0.0.1', parent = fcomment7,
...     comment = "<10chars",
... )

>>> moderator.unregister(TestModel)
>>> class Moderator5(CommentModerator):
...     allowed_markup = [REST,]
...     max_depth = 3
>>> moderator.register(TestModel, Moderator5)

>>> fcomment15 = FreeThreadedComment.objects.create_for_object(
...     topic, name = "Eric", ip_address = '127.0.0.1', parent = fcomment7,
...     comment = "INVALID Markup.  Should not show up.", markup=TEXTILE
... )

>>> fcomment16 = FreeThreadedComment.objects.create_for_object(
...     topic, name = "Eric", ip_address = '127.0.0.1', parent = None,
...     comment = "VALID Markup.  Should show up.", markup=REST
... )

>>> fcomment17 = FreeThreadedComment.objects.create_for_object(
...     topic, name = "Eric", ip_address = '127.0.0.1', parent = fcomment16,
...     comment = "Building Depth...Should Show Up.", markup=REST
... )

>>> fcomment18 = FreeThreadedComment.objects.create_for_object(
...     topic, name = "Eric", ip_address = '127.0.0.1', parent = fcomment17,
...     comment = "More Depth...Should Show Up.", markup=REST
... )

>>> fcomment19 = FreeThreadedComment.objects.create_for_object(
...     topic, name = "Eric", ip_address = '127.0.0.1', parent = fcomment18,
...     comment = "Too Deep..Should NOT Show UP", markup=REST
... )

>>> moderator.unregister(TestModel)

>>> tree = FreeThreadedComment.public.get_tree(topic)
>>> for comment in tree:
...     print "%s %s" % ("    " * comment.depth, comment.comment)
 This is fun!  This is very fun!
     What are you talking about?
     This should appear again.
 This is stupid!  I hate it!
     I agree, the first comment was wrong and you are right!
         I'm a fanboy!
 What are we talking about?
 Post moderator addition.  Does it still work?
     <10chars
 This should appear again, due to unregistration
 VALID Markup.  Should show up.
     Building Depth...Should Show Up.
         More Depth...Should Show Up.

>>> tree = FreeThreadedComment.objects.get_tree(topic)
>>> for comment in tree:
...     print "%s %s" % ("    " * comment.depth, comment.comment)
 This is fun!  This is very fun!
     What are you talking about?
     This should appear again.
 This is stupid!  I hate it!
     I agree, the first comment was wrong and you are right!
         I'm a fanboy!
 What are we talking about?
 Post moderator addition.  Does it still work?
     This shouldn't appear because it has more than 10 chars.
     <10chars
 This should appear again, due to unregistration
 VALID Markup.  Should show up.
     Building Depth...Should Show Up.
         More Depth...Should Show Up.

>>> tree = FreeThreadedComment.objects.get_tree(topic, root=comment2)
>>> for comment in tree:
...     print "%s %s" % ("    " * comment.depth, comment.comment)
 This is stupid!  I hate it!
     I agree, the first comment was wrong and you are right!
         I'm a fanboy!

>>> tree = FreeThreadedComment.objects.get_tree(topic, root=comment2.id)
>>> for comment in tree:
...     print "%s %s" % ("    " * comment.depth, comment.comment)
 This is stupid!  I hate it!
     I agree, the first comment was wrong and you are right!
         I'm a fanboy!
>>>

############################
### Views and URLs Tests ###
############################
>>> from django.core.urlresolvers import reverse
>>> from django.test.client import Client
>>> from django.utils.simplejson import loads
>>> from xml.dom.minidom import parseString

>>> topic = TestModel.objects.create(name = "Test2")
>>> old_topic = topic
>>> content_type = ContentType.objects.get_for_model(topic)
>>>
  #######################################
  ### FreeThreadedComments URLs Tests ###
  #######################################
>>> c = Client()

>>> url = reverse('tc_free_comment', 
...     kwargs={'content_type': content_type.id, 'object_id' : topic.id}
... )
>>> response = c.post(url, {'comment' : 'test1', 'name' : 'eric', 'website' : 'http://www.eflorenzano.com/', 'email' : 'floguy@gmail.com', 'next' : '/'})
>>> FreeThreadedComment.objects.latest('date_submitted').get_base_data(show_dates=False)
{'website': u'http://www.eflorenzano.com/', 'comment': u'test1', 'name': u'eric', 'parent': None, 'markup': u'plaintext', 'content_object': <TestModel: TestModel object>, 'is_public': True, 'ip_address': None, 'email': u'floguy@gmail.com', 'is_approved': False}

# Testing Preview
>>> response = c.post(url, {'comment' : 'test1', 'name' : 'eric', 'website' : 'http://www.eflorenzano.com/', 'email' : 'floguy@gmail.com', 'next' : '/', 'preview' : 'True'})
>>> len(response.content) > 0
True

# Testing Edit
>>> latest = FreeThreadedComment.objects.latest('date_submitted')
>>> url = reverse('tc_free_comment_edit', kwargs={'edit_id' : latest.pk})
>>> response = c.post(url, {'comment' : 'test1_edited', 'name' : 'eric', 'website' : 'http://www.eflorenzano.com/', 'email' : 'floguy@gmail.com', 'next' : '/'})
>>> FreeThreadedComment.objects.latest('date_submitted').get_base_data(show_dates=False)
{'website': u'http://www.eflorenzano.com/', 'comment': u'test1_edited', 'name': u'eric', 'parent': None, 'markup': u'plaintext', 'content_object': <TestModel: TestModel object>, 'is_public': True, 'ip_address': None, 'email': u'floguy@gmail.com', 'is_approved': False}
>>> latest.save()

# Testing Edit With Preview
>>> response = c.post(url, {'comment' : 'test1_edited', 'name' : 'eric', 'website' : 'http://www.eflorenzano.com/', 'email' : 'floguy@gmail.com', 'next' : '/', 'preview' : 'True'})
>>> FreeThreadedComment.objects.latest('date_submitted').get_base_data(show_dates=False)
{'website': u'http://www.eflorenzano.com/', 'comment': u'test1', 'name': u'eric', 'parent': None, 'markup': u'plaintext', 'content_object': <TestModel: TestModel object>, 'is_public': True, 'ip_address': None, 'email': u'floguy@gmail.com', 'is_approved': False}
>>> len(response.content) > 0
True

>>> url = reverse('tc_free_comment_ajax', 
...     kwargs={'content_type': content_type.id, 'object_id' : topic.id,
...         'ajax' : 'json'}
... )
>>> response = c.post(url, {'comment' : 'test2', 'name' : 'eric', 'website' : 'http://www.eflorenzano.com/', 'email' : 'floguy@gmail.com'})
>>> tmp = loads(response.content)
>>> FreeThreadedComment.objects.latest('date_submitted').get_base_data(show_dates=False)
{'website': u'http://www.eflorenzano.com/', 'comment': u'test2', 'name': u'eric', 'parent': None, 'markup': u'plaintext', 'content_object': <TestModel: TestModel object>, 'is_public': True, 'ip_address': None, 'email': u'floguy@gmail.com', 'is_approved': False}

# Testing Edit AJAX JSON
>>> latest = FreeThreadedComment.objects.latest('date_submitted')
>>> url = reverse('tc_free_comment_edit_ajax', 
...     kwargs={'edit_id': latest.pk, 'ajax' : 'json'})
>>> response = c.post(url, {'comment' : 'test2_edited', 'name' : 'eric', 'website' : 'http://www.eflorenzano.com/', 'email' : 'floguy@gmail.com'})
>>> tmp = loads(response.content)
>>> FreeThreadedComment.objects.latest('date_submitted').get_base_data(show_dates=False)
{'website': u'http://www.eflorenzano.com/', 'comment': u'test2_edited', 'name': u'eric', 'parent': None, 'markup': u'plaintext', 'content_object': <TestModel: TestModel object>, 'is_public': True, 'ip_address': None, 'email': u'floguy@gmail.com', 'is_approved': False}
>>> latest.save()

# Testing Edit AJAX XML
>>> url = reverse('tc_free_comment_edit_ajax', 
...     kwargs={'edit_id': latest.pk, 'ajax' : 'xml'})
>>> response = c.post(url, {'comment' : 'test2_edited', 'name' : 'eric', 'website' : 'http://www.eflorenzano.com/', 'email' : 'floguy@gmail.com'})
>>> tmp = parseString(response.content)
>>> FreeThreadedComment.objects.latest('date_submitted').get_base_data(show_dates=False)
{'website': u'http://www.eflorenzano.com/', 'comment': u'test2_edited', 'name': u'eric', 'parent': None, 'markup': u'plaintext', 'content_object': <TestModel: TestModel object>, 'is_public': True, 'ip_address': None, 'email': u'floguy@gmail.com', 'is_approved': False}
>>> latest.save()

>>> url = reverse('tc_free_comment_ajax', 
...     kwargs={'content_type': content_type.id, 'object_id' : topic.id,
...         'ajax' : 'xml'}
... )
>>> response = c.post(url, {'comment' : 'test3', 'name' : 'eric', 'website' : 'http://www.eflorenzano.com/', 'email' : 'floguy@gmail.com', 'next' : '/'})
>>> tmp = parseString(response.content)
>>> FreeThreadedComment.objects.latest('date_submitted').get_base_data(show_dates=False)
{'website': u'http://www.eflorenzano.com/', 'comment': u'test3', 'name': u'eric', 'parent': None, 'markup': u'plaintext', 'content_object': <TestModel: TestModel object>, 'is_public': True, 'ip_address': None, 'email': u'floguy@gmail.com', 'is_approved': False}

>>> parent = FreeThreadedComment.objects.latest('date_submitted')

>>> url = reverse('tc_free_comment_parent', 
...     kwargs={'content_type': content_type.id, 'object_id' : topic.id, 
...         'parent_id' : parent.id}
... )
>>> response = c.post(url, {'comment' : 'test4', 'name' : 'eric', 'website' : 'http://www.eflorenzano.com/', 'email' : 'floguy@gmail.com', 'next' : '/'})
>>> FreeThreadedComment.objects.latest('date_submitted').get_base_data(show_dates=False)
{'website': u'http://www.eflorenzano.com/', 'comment': u'test4', 'name': u'eric', 'parent': <FreeThreadedComment: test3>, 'markup': u'plaintext', 'content_object': <TestModel: TestModel object>, 'is_public': True, 'ip_address': None, 'email': u'floguy@gmail.com', 'is_approved': False}

>>> url = reverse('tc_free_comment_parent_ajax', 
...     kwargs={'content_type': content_type.id, 'object_id' : topic.id, 
...         'parent_id' : parent.id, 'ajax' : 'json'}
... )
>>> response = c.post(url, {'comment' : 'test5', 'name' : 'eric', 'website' : 'http://www.eflorenzano.com/', 'email' : 'floguy@gmail.com'})
>>> tmp = loads(response.content)
>>> FreeThreadedComment.objects.latest('date_submitted').get_base_data(show_dates=False)
{'website': u'http://www.eflorenzano.com/', 'comment': u'test5', 'name': u'eric', 'parent': <FreeThreadedComment: test3>, 'markup': u'plaintext', 'content_object': <TestModel: TestModel object>, 'is_public': True, 'ip_address': None, 'email': u'floguy@gmail.com', 'is_approved': False}

>>> url = reverse('tc_free_comment_parent_ajax',
...     kwargs={'content_type': content_type.id, 'object_id' : topic.id, 
...         'parent_id' : parent.id, 'ajax' : 'xml'}
... )
>>> response = c.post(url, {'comment' : 'test6', 'name' : 'eric', 'website' : 'http://www.eflorenzano.com/', 'email' : 'floguy@gmail.com'})
>>> tmp = parseString(response.content)
>>> FreeThreadedComment.objects.latest('date_submitted').get_base_data(show_dates=False)
{'website': u'http://www.eflorenzano.com/', 'comment': u'test6', 'name': u'eric', 'parent': <FreeThreadedComment: test3>, 'markup': u'plaintext', 'content_object': <TestModel: TestModel object>, 'is_public': True, 'ip_address': None, 'email': u'floguy@gmail.com', 'is_approved': False}

  ###################################
  ### ThreadedComments URLs Tests ###
  ###################################
>>> u = User.objects.create_user('testuser', 'testuser@gmail.com', password='password')
>>> u.is_active = True
>>> u.save()
>>> c.login(username='testuser', password='password')
True

>>> url = reverse('tc_comment', 
...     kwargs={'content_type': content_type.id, 'object_id' : topic.id}
... )
>>> response = c.post(url, {'comment' : 'test7', 'next' : '/'})
>>> ThreadedComment.objects.latest('date_submitted').get_base_data(show_dates=False)
{'comment': u'test7', 'is_approved': False, 'parent': None, 'markup': u'plaintext', 'content_object': <TestModel: TestModel object>, 'user': <User: testuser>, 'is_public': True, 'ip_address': None}

# Testing Preview
>>> response = c.post(url, {'comment' : 'test7', 'next' : '/', 'preview' : 'True'})
>>> len(response.content) > 0
True

# Testing Edit
>>> latest = ThreadedComment.objects.latest('date_submitted')
>>> url = reverse('tc_comment_edit', kwargs={'edit_id' : latest.pk})
>>> response = c.post(url, {'comment' : 'test7_edited', 'next' : '/'})
>>> ThreadedComment.objects.latest('date_submitted').get_base_data(show_dates=False)
{'comment': u'test7_edited', 'is_approved': False, 'parent': None, 'markup': u'plaintext', 'content_object': <TestModel: TestModel object>, 'user': <User: testuser>, 'is_public': True, 'ip_address': None}
>>> latest.save()

# Testing Edit With Preview
>>> response = c.post(url, {'comment' : 'test7_edited', 'next' : '/', 'preview' : 'True'})
>>> len(response.content) > 0
True
>>> ThreadedComment.objects.latest('date_submitted').get_base_data(show_dates=False)
{'comment': u'test7', 'is_approved': False, 'parent': None, 'markup': u'plaintext', 'content_object': <TestModel: TestModel object>, 'user': <User: testuser>, 'is_public': True, 'ip_address': None}

>>> url = reverse('tc_comment_ajax', 
...     kwargs={'content_type': content_type.id, 'object_id' : topic.id,
...         'ajax' : 'json'}
... )
>>> response = c.post(url, {'comment' : 'test8'})
>>> tmp = loads(response.content)
>>> ThreadedComment.objects.latest('date_submitted').get_base_data(show_dates=False)
{'comment': u'test8', 'is_approved': False, 'parent': None, 'markup': u'plaintext', 'content_object': <TestModel: TestModel object>, 'user': <User: testuser>, 'is_public': True, 'ip_address': None}

# Testing Edit AJAX JSON
>>> latest = ThreadedComment.objects.latest('date_submitted')
>>> url = reverse('tc_comment_edit_ajax', kwargs={'edit_id': latest.pk, 'ajax' : 'json'})
>>> response = c.post(url, {'comment' : 'test8_edited'})
>>> tmp = loads(response.content)
>>> ThreadedComment.objects.latest('date_submitted').get_base_data(show_dates=False)
{'comment': u'test8_edited', 'is_approved': False, 'parent': None, 'markup': u'plaintext', 'content_object': <TestModel: TestModel object>, 'user': <User: testuser>, 'is_public': True, 'ip_address': None}
>>> latest.save()

# Testing Edit AJAX XML
>>> url = reverse('tc_comment_edit_ajax', kwargs={'edit_id': latest.pk, 'ajax' : 'xml'})
>>> response = c.post(url, {'comment' : 'test8_edited'})
>>> tmp = parseString(response.content)
>>> ThreadedComment.objects.latest('date_submitted').get_base_data(show_dates=False)
{'comment': u'test8_edited', 'is_approved': False, 'parent': None, 'markup': u'plaintext', 'content_object': <TestModel: TestModel object>, 'user': <User: testuser>, 'is_public': True, 'ip_address': None}
>>> latest.save()

>>> url = reverse('tc_comment_ajax', 
...     kwargs={'content_type': content_type.id, 'object_id' : topic.id,
...         'ajax' : 'xml'}
... )
>>> response = c.post(url, {'comment' : 'test9'})
>>> tmp = parseString(response.content)
>>> ThreadedComment.objects.latest('date_submitted').get_base_data(show_dates=False)
{'comment': u'test9', 'is_approved': False, 'parent': None, 'markup': u'plaintext', 'content_object': <TestModel: TestModel object>, 'user': <User: testuser>, 'is_public': True, 'ip_address': None}

>>> parent = ThreadedComment.objects.latest('date_submitted')

>>> url = reverse('tc_comment_parent', 
...     kwargs={'content_type': content_type.id, 'object_id' : topic.id, 
...         'parent_id' : parent.id}
... )
>>> response = c.post(url, {'comment' : 'test10', 'next' : '/'})
>>> ThreadedComment.objects.latest('date_submitted').get_base_data(show_dates=False)
{'comment': u'test10', 'is_approved': False, 'parent': <ThreadedComment: test9>, 'markup': u'plaintext', 'content_object': <TestModel: TestModel object>, 'user': <User: testuser>, 'is_public': True, 'ip_address': None}

>>> url = reverse('tc_comment_parent_ajax', 
...     kwargs={'content_type': content_type.id, 'object_id' : topic.id, 
...         'parent_id' : parent.id, 'ajax' : 'json'}
... )
>>> response = c.post(url, {'comment' : 'test11'})
>>> tmp = loads(response.content)
>>> ThreadedComment.objects.latest('date_submitted').get_base_data(show_dates=False)
{'comment': u'test11', 'is_approved': False, 'parent': <ThreadedComment: test9>, 'markup': u'plaintext', 'content_object': <TestModel: TestModel object>, 'user': <User: testuser>, 'is_public': True, 'ip_address': None}

>>> url = reverse('tc_comment_parent_ajax', 
...     kwargs={'content_type': content_type.id, 'object_id' : topic.id, 
...         'parent_id' : parent.id, 'ajax' : 'xml'}
... )
>>> response = c.post(url, {'comment' : 'test12'})
>>> tmp = parseString(response.content)
>>> ThreadedComment.objects.latest('date_submitted').get_base_data(show_dates=False)
{'comment': u'test12', 'is_approved': False, 'parent': <ThreadedComment: test9>, 'markup': u'plaintext', 'content_object': <TestModel: TestModel object>, 'user': <User: testuser>, 'is_public': True, 'ip_address': None}
>>>

######################
### DELETION Tests ###
######################

  ###########################
  ### FreeThreadedComment ###
  ###########################
>>> latest = FreeThreadedComment.objects.latest('date_submitted')
>>> latest_id = latest.pk

>>> non_used_user = User.objects.create_user('user999', 'floguy2@gmail.com', password='password2')
>>> latest.user = non_used_user
>>> latest.save()

>>> url = reverse('tc_free_comment_delete',
...     kwargs={'object_id':latest_id})
>>> response = c.post(url, {'next' : '/'})
>>> response['Location'].split('?')[-1] == 'next=/freecomment/%d/delete/' % latest_id
True

>>> u.is_superuser = True
>>> u.save()

>>> response = c.post(url, {'next' : '/'})
>>> response['Location']
'http://testserver/'
>>> FreeThreadedComment.objects.get(id=latest_id)
Traceback (most recent call last):
...
DoesNotExist: FreeThreadedComment matching query does not exist.
>>> latest.save()

>>> response = c.get(url, {'next' : '/'})
>>> len(response.content) > 0
True

>>> FreeThreadedComment.objects.get(id=latest_id) != None
True

>>> u.is_superuser = False
>>> u.save()

  #######################
  ### ThreadedComment ###
  #######################
>>> latest = ThreadedComment.objects.latest('date_submitted')
>>> latest_id = latest.pk

>>> latest.user = non_used_user
>>> latest.save()

>>> url = reverse('tc_comment_delete',
...     kwargs={'object_id':latest_id})
>>> response = c.post(url, {'next' : '/'})
>>> response['Location'].split('?')[-1]
'next=/comment/18/delete/'

>>> u.is_superuser = True
>>> u.save()

>>> response = c.post(url, {'next' : '/'})
>>> response['Location']
'http://testserver/'
>>> ThreadedComment.objects.get(id=latest_id)
Traceback (most recent call last):
...
DoesNotExist: ThreadedComment matching query does not exist.
>>> latest.save()

>>> response = c.get(url, {'next' : '/'})
>>> len(response.content) > 0
True

>>> ThreadedComment.objects.get(id=latest_id) != None
True

#########################
### Templatetag Tests ###
#########################
>>> from django.template import Context, Template
>>> from threadedcomments.templatetags import threadedcommentstags as tags

>>> topic = TestModel.objects.create(name = "Test3")
>>> c = Context({'topic' : topic, 'old_topic' : old_topic, 'parent' : comment9})

>>> Template('{% load threadedcommentstags %}{% get_comment_url topic %}').render(c)
u'/comment/10/3/'
>>> Template('{% load threadedcommentstags %}{% get_comment_url topic parent %}').render(c)
u'/comment/10/3/8/'
>>> Template('{% load threadedcommentstags %}{% get_comment_url_json topic %}').render(c)
u'/comment/10/3/json/'
>>> Template('{% load threadedcommentstags %}{% get_comment_url_xml topic %}').render(c)
u'/comment/10/3/xml/'
>>> Template('{% load threadedcommentstags %}{% get_comment_url_json topic parent %}').render(c)
u'/comment/10/3/8/json/'
>>> Template('{% load threadedcommentstags %}{% get_comment_url_xml topic parent %}').render(c)
u'/comment/10/3/8/xml/'

>>> Template('{% load threadedcommentstags %}{% get_comment_count for old_topic as count %}{{ count }}').render(c)
u'6'

>>> Template('{% load threadedcommentstags %}{% get_latest_comments 2 as comments %}{{ comments }}').render(c)
u'[&lt;ThreadedComment: test12&gt;, &lt;ThreadedComment: test11&gt;]'

>>> Template('{% load threadedcommentstags %}{% get_threaded_comment_form as form %}{{ form }}').render(c)
u'<tr><th><label for="id_comment">comment:</label></th><td><textarea id="id_comment" rows="10" cols="40" name="comment"></textarea></td></tr>\\n<tr><th><label for="id_markup">Markup:</label></th><td><select name="markup" id="id_markup">\\n<option value="">---------</option>\\n<option value="1">markdown</option>\\n<option value="2">textile</option>\\n<option value="3">restructuredtext</option>\\n<option value="5" selected="selected">plaintext</option>\\n</select></td></tr>'

>>> c = Context({'topic' : topic, 'old_topic' : old_topic, 'parent' : FreeThreadedComment.objects.latest('date_submitted')})
>>> Template('{% load threadedcommentstags %}{% get_free_comment_url topic %}').render(c)
u'/freecomment/10/3/'
>>> Template('{% load threadedcommentstags %}{% get_free_comment_url topic parent %}').render(c)
u'/freecomment/10/3/20/'
>>> Template('{% load threadedcommentstags %}{% get_free_comment_url_json topic %}').render(c)
u'/freecomment/10/3/json/'
>>> Template('{% load threadedcommentstags %}{% get_free_comment_url_xml topic %}').render(c)
u'/freecomment/10/3/xml/'
>>> Template('{% load threadedcommentstags %}{% get_free_comment_url_json topic parent %}').render(c)
u'/freecomment/10/3/20/json/'
>>> Template('{% load threadedcommentstags %}{% get_free_comment_url_xml topic parent %}').render(c)
u'/freecomment/10/3/20/xml/'

>>> Template('{% load threadedcommentstags %}{% get_free_comment_count for old_topic as count %}{{ count }}').render(c)
u'6'

>>> Template('{% load threadedcommentstags %}{% get_latest_free_comments 2 as comments %}{{ comments }}').render(c)
u'[&lt;FreeThreadedComment: test6&gt;, &lt;FreeThreadedComment: test5&gt;]'

>>> Template('{% load threadedcommentstags %}{% get_free_threaded_comment_form as form %}{{ form }}').render(c)
u'<tr><th><label for="id_name">Name:</label></th><td><input id="id_name" type="text" name="name" maxlength="128" /></td></tr>\\n<tr><th><label for="id_website">Site:</label></th><td><input id="id_website" type="text" name="website" maxlength="200" /></td></tr>\\n<tr><th><label for="id_email">E-mail address:</label></th><td><input id="id_email" type="text" name="email" maxlength="75" /></td></tr>\\n<tr><th><label for="id_comment">comment:</label></th><td><textarea id="id_comment" rows="10" cols="40" name="comment"></textarea></td></tr>\\n<tr><th><label for="id_markup">Markup:</label></th><td><select name="markup" id="id_markup">\\n<option value="">---------</option>\\n<option value="1">markdown</option>\\n<option value="2">textile</option>\\n<option value="3">restructuredtext</option>\\n<option value="5" selected="selected">plaintext</option>\\n</select></td></tr>'

>>> c = Context({'topic' : old_topic, 'parent' : FreeThreadedComment.objects.latest('date_submitted'), 'user':user})
>>> Template('{% load threadedcommentstags %}{% get_free_threaded_comment_tree for topic as tree %}[{% for item in tree %}({{ item.depth }}){{ item.comment }},{% endfor %}]').render(c)
u'[(0)test1,(0)test2,(0)test3,(1)test4,(1)test5,(1)test6,]'

>>> Template('{% load threadedcommentstags %}{% get_free_threaded_comment_tree for topic 17 as tree %}[{% for item in tree %}({{ item.depth }}){{ item.comment }},{% endfor %}]').render(c)
u'[(0)test3,(1)test4,(1)test5,(1)test6,]'

>>> Template('{% load threadedcommentstags %}{% get_threaded_comment_tree for topic as tree %}[{% for item in tree %}({{ item.depth }}){{ item.comment }},{% endfor %}]').render(c)
u'[(0)test7,(0)test8,(0)test9,(1)test10,(1)test11,(1)test12,]'

>>> Template('{% load threadedcommentstags %}{% get_threaded_comment_tree for topic 15 as tree %}[{% for item in tree %}({{ item.depth }}){{ item.comment }},{% endfor %}]').render(c)
u'[(0)test9,(1)test10,(1)test11,(1)test12,]'

>>> Template('{% load threadedcommentstags %}{% get_user_comments for user as comments %}{{ comments }}').render(c)
u'[&lt;ThreadedComment: VALID Markup.  Should show up.&gt;, &lt;ThreadedComment: &lt;10chars&gt;, &lt;ThreadedComment: This shouldn&#39;t appear because it has more than 10 ...&gt;, &lt;ThreadedComment: This should appear again.&gt;, &lt;ThreadedComment: This should appear again, due to unregistration&gt;, &lt;ThreadedComment: Post moderator addition.  Does it still work?&gt;, &lt;ThreadedComment: What are you talking about?&gt;, &lt;ThreadedComment: I&#39;m a fanboy!&gt;, &lt;ThreadedComment: What are we talking about?&gt;, &lt;ThreadedComment: I agree, the first comment was wrong and you are r...&gt;, &lt;ThreadedComment: This is stupid!  I hate it!&gt;, &lt;ThreadedComment: This is fun!  This is very fun!&gt;]'

>>> Template('{% load threadedcommentstags %}{% get_user_comment_count for user as comment_count %}{{ comment_count }}').render(c)
u'12'

>>> markdown_txt = '''
... A First Level Header
... ====================
... 
... A Second Level Header
... ---------------------
... 
... Now is the time for all good men to come to
... the aid of their country. This is just a
... regular paragraph.
... 
... The quick brown fox jumped over the lazy
... dog's back.
... 
... ### Header 3
... 
... > This is a blockquote.
... > 
... > This is the second paragraph in the blockquote.
... >
... > ## This is an H2 in a blockquote
... '''

>>> comment_markdown = ThreadedComment.objects.create_for_object(
...     old_topic, user = user, ip_address = '127.0.0.1', markup = MARKDOWN,
...     comment = markdown_txt,
... )

>>> c = Context({'comment' : comment_markdown})
>>> Template("{% load threadedcommentstags %}{% auto_transform_markup comment %}").render(c).replace('\\n', '')
u"<h1>...

>>> textile_txt = '''
... h2{color:green}. This is a title
... 
... h3. This is a subhead
... 
... p{color:red}. This is some text of dubious character. Isn't the use of "quotes" just lazy ... writing -- and theft of 'intellectual property' besides? I think the time has come to see a block quote.
... 
... bq[fr]. This is a block quote. I'll admit it's not the most exciting block quote ever devised.
... 
... Simple list:
... 
... #{color:blue} one
... # two
... # three
... 
... Multi-level list:
... 
... # one
... ## aye
... ## bee
... ## see
... # two
... ## x
... ## y
... # three
... 
... Mixed list:
... 
... * Point one
... * Point two
... ## Step 1
... ## Step 2
... ## Step 3
... * Point three
... ** Sub point 1
... ** Sub point 2
... 
... 
... Well, that went well. How about we insert an <a href="/" title="watch out">old-fashioned ... hypertext link</a>? Will the quote marks in the tags get messed up? No!
... 
... "This is a link (optional title)":http://www.textism.com
... 
... table{border:1px solid black}.
... |_. this|_. is|_. a|_. header|
... <{background:gray}. |\2. this is|{background:red;width:200px}. a|^<>{height:200px}. row|
... |this|<>{padding:10px}. is|^. another|(bob#bob). row|
... 
... An image:
... 
... !/common/textist.gif(optional alt text)!
... 
... # Librarians rule
... # Yes they do
... # But you knew that
... 
... Some more text of dubious character. Here is a noisome string of CAPITAL letters. Here is ... something we want to _emphasize_. 
... That was a linebreak. And something to indicate *strength*. Of course I could use <em>my ... own HTML tags</em> if I <strong>felt</strong> like it.
... 
... h3. Coding
... 
... This <code>is some code, "isn't it"</code>. Watch those quote marks! Now for some preformatted text:
... 
... <pre>
... <code>
... 	$text = str_replace("<p>%::%</p>","",$text);
... 	$text = str_replace("%::%</p>","",$text);
... 	$text = str_replace("%::%","",$text);
... 
... </code>
... </pre>
... 
... This isn't code.
... 
... 
... So you see, my friends:
... 
... * The time is now
... * The time is not later
... * The time is not yesterday
... * We must act
... '''

>>> comment_textile = ThreadedComment.objects.create_for_object(
...     old_topic, user = user, ip_address = '127.0.0.1', markup = TEXTILE,
...     comment = textile_txt,
... )
>>> c = Context({'comment' : comment_textile})
>>> Template("{% load threadedcommentstags %}{% auto_transform_markup comment %}").render(c)
u'<h2 style="color:green;">This is a title</h2>\\n\\n<h3>This is a subhead</h3>\\n\\n<p style="color:red;">This is some text of dubious character. Isn&#8217;t the use of &#8220;quotes&#8221; just lazy&#8230; writing&#8212;and theft of &#8216;intellectual property&#8217; besides? I think the time has come to see a block quote.</p>\\n\\n<blockquote lang="fr">\\n<p>This is a block quote. I&#8217;ll admit it&#8217;s not the most exciting block quote ever devised.</p>\\n</blockquote>\\n\\n<p>Simple list:</p>\\n\\n<ol>\\n<li style="color:blue;">one</li>\\n<li>two</li>\\n<li>three</li>\\n</ol>\\n\\n<p>Multi-level list:</p>\\n\\n<ol>\\n<li>one\\n<ol>\\n<li>aye</li>\\n<li>bee</li>\\n<li>see</li>\\n</ol>\\n</li>\\n<li>two\\n<ol>\\n<li>x</li>\\n<li>y</li>\\n</ol>\\n</li>\\n<li>three</li>\\n</ol>\\n\\n<p>Mixed list:</p>\\n\\n<ul>\\n<li>Point one</li>\\n<li>Point two<br />\\n## Step 1<br />\\n## Step 2<br />\\n## Step 3</li>\\n<li>Point three\\n<ul>\\n<li>Sub point 1</li>\\n<li>Sub point 2</li>\\n</ul>\\n</li>\\n</ul>\\n\\n<p>Well, that went well. How about we insert an <a href="/" title="watch out">old-fashioned&#8230; hypertext link</a>? Will the quote marks in the tags get messed up? No!</p>\\n\\n<p><a href="http://www.textism.com" title="optional title">This is a link</a></p>\\n\\n<table style="border:1px solid black;">\\n<tr>\\n<th>this</th>\\n<th>is</th>\\n<th>a</th>\\n<th>header</th>\\n</tr>\\n<tr style="background:gray;" align="left">\\n<td>\\x02. this is</td>\\n<td style="background:red;width:200px;">a</td>\\n<td style="height:200px;" align="justify" valign="top">row</td>\\n</tr>\\n<tr>\\n<td>this</td>\\n<td style="padding:10px;" align="justify">is</td>\\n<td valign="top">another</td>\\n<td class="bob" id="bob">row</td>\\n</tr>\\n</table>\\n\\n<p>An image:</p>\\n\\n<p><img src="/common/textist.gif" title="optional alt text" alt="optional alt text" /></p>\\n\\n<ol>\\n<li>Librarians rule</li>\\n<li>Yes they do</li>\\n<li>But you knew that</li>\\n</ol>\\n\\n<p>Some more text of dubious character. Here is a noisome string of <span class="caps">CAPITAL</span> letters. Here is&#8230; something we want to <em>emphasize</em>. <br />\\nThat was a linebreak. And something to indicate <strong>strength</strong>. Of course I could use <em>my&#8230; own <span class="caps">HTML</span> tags</em> if I <strong>felt</strong> like it.</p>\\n\\n<h3>Coding</h3>\\n\\n<p>This <code>is some code, &#8220;isn&#8217;t it&#8221;</code>. Watch those quote marks! Now for some preformatted text:</p>\\n\\n<pre>\\n<code>\\n    $text = str_replace("<p>%::%</p>","",$text);\\n    $text = str_replace("%::%</p>","",$text);\\n    $text = str_replace("%::%","",$text);\\n\\n</code>\\n</pre>\\n\\n<p>This isn&#8217;t code.</p>\\n\\n<p>So you see, my friends:</p>\\n\\n<ul>\\n<li>The time is now</li>\\n<li>The time is not later</li>\\n<li>The time is not yesterday</li>\\n<li>We must act</li>\\n</ul>'


>>> rest_txt = '''
... FooBar Header
... =============
... reStructuredText is **nice**. It has its own webpage_.
... 
... A table:
... 
... =====  =====  ======
...    Inputs     Output
... ------------  ------
...   A      B    A or B
... =====  =====  ======
... False  False  False
... True   False  True
... False  True   True
... True   True   True
... =====  =====  ======
... 
... RST TracLinks
... -------------
... 
... See also ticket `#42`::.
... 
... .. _webpage: http://docutils.sourceforge.net/rst.html
... '''

>>> comment_rest = ThreadedComment.objects.create_for_object(
...     old_topic, user = user, ip_address = '127.0.0.1', markup = REST,
...     comment = rest_txt,
... )
>>> c = Context({'comment' : comment_rest})
>>> Template("{% load threadedcommentstags %}{% auto_transform_markup comment %}").render(c)
u'<p>reStructuredText is...

>>> comment_plaintext = ThreadedComment.objects.create_for_object(
...     old_topic, user = user, ip_address = '127.0.0.1', markup = PLAINTEXT,
...     comment = '<b>This is Funny</b>',
... )
>>> c = Context({'comment' : comment_plaintext})
>>> Template("{% load threadedcommentstags %}{% auto_transform_markup comment %}").render(c)
u'&lt;b&gt;This is Funny&lt;/b&gt;'

>>> comment_plaintext = ThreadedComment.objects.create_for_object(
...     old_topic, user = user, ip_address = '127.0.0.1', markup = PLAINTEXT,
...     comment = '<b>This is Funny</b>',
... )
>>> c = Context({'comment' : comment_plaintext})
>>> Template("{% load threadedcommentstags %}{% auto_transform_markup comment as abc %}{{ abc }}").render(c)
u'&lt;b&gt;This is Funny&lt;/b&gt;'
>>>

##################################
### Gravatar Templatetag Tests ###
##################################
>>> c = Context({'email' : "floguy@gmail.com", 'rating' : "G", 'size' : 30, 'default': 'img:blank'})
>>> Template('{% load gravatar %}{% get_gravatar_url for email %}').render(c)
u'http://www.gravatar.com/avatar.php?gravatar_id=04d6b8e8d3c68899ac88eb8623392150&rating=R&size=80&default=http%3A%2F%2Fsite.gravatar.com%2Fimages%2Fcommon%2Ftop%2Flogo.gif'

>>> Template('{% load gravatar %}{% get_gravatar_url for email as var %}Var: {{ var }}').render(c)
u'Var: http://www.gravatar.com/avatar.php?gravatar_id=04d6b8e8d3c68899ac88eb8623392150&rating=R&size=80&default=http%3A%2F%2Fsite.gravatar.com%2Fimages%2Fcommon%2Ftop%2Flogo.gif'

>>> Template('{% load gravatar %}{% get_gravatar_url for email size 30 rating "G" default img:blank as var %}Var: {{ var }}').render(c)
u'Var: http://www.gravatar.com/avatar.php?gravatar_id=04d6b8e8d3c68899ac88eb8623392150&rating=G&size=30&default=img%3Ablank'

>>> Template('{% load gravatar %}{% get_gravatar_url for email size size rating rating default default as var %}Var: {{ var }}').render(c)
u'Var: http://www.gravatar.com/avatar.php?gravatar_id=04d6b8e8d3c68899ac88eb8623392150&rating=G&size=30&default=img%3Ablank'

>>> Template('{% load gravatar %}{{ email|gravatar }}').render(c)
u'http://www.gravatar.com/avatar.php?gravatar_id=04d6b8e8d3c68899ac88eb8623392150&rating=R&size=80&default=http%3A%2F%2Fsite.gravatar.com%2Fimages%2Fcommon%2Ftop%2Flogo.gif'

"""
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url
from threadedcomments.models import FreeThreadedComment
import views

free = {'model' : FreeThreadedComment}

urlpatterns = patterns('',
    ### Comments ###
    url(r'^comment/(?P<content_type>\d+)/(?P<object_id>\d+)/$', views.comment, name="tc_comment"),
    url(r'^comment/(?P<content_type>\d+)/(?P<object_id>\d+)/(?P<parent_id>\d+)/$', views.comment, name="tc_comment_parent"),
    url(r'^comment/(?P<object_id>\d+)/delete/$', views.comment_delete, name="tc_comment_delete"),
    url(r'^comment/(?P<edit_id>\d+)/edit/$', views.comment, name="tc_comment_edit"),
    
    ### Comments (AJAX) ###
    url(r'^comment/(?P<content_type>\d+)/(?P<object_id>\d+)/(?P<ajax>json|xml)/$', views.comment, name="tc_comment_ajax"),
    url(r'^comment/(?P<content_type>\d+)/(?P<object_id>\d+)/(?P<parent_id>\d+)/(?P<ajax>json|xml)/$', views.comment, name="tc_comment_parent_ajax"),
    url(r'^comment/(?P<edit_id>\d+)/edit/(?P<ajax>json|xml)/$', views.comment, name="tc_comment_edit_ajax"),

    ### Free Comments ###
    url(r'^freecomment/(?P<content_type>\d+)/(?P<object_id>\d+)/$', views.free_comment, name="tc_free_comment"),
    url(r'^freecomment/(?P<content_type>\d+)/(?P<object_id>\d+)/(?P<parent_id>\d+)/$', views.free_comment, name="tc_free_comment_parent"),
    url(r'^freecomment/(?P<object_id>\d+)/delete/$', views.comment_delete, free, name="tc_free_comment_delete"),
    url(r'^freecomment/(?P<edit_id>\d+)/edit/$', views.free_comment, name="tc_free_comment_edit"),

    ### Free Comments (AJAX) ###
    url(r'^freecomment/(?P<content_type>\d+)/(?P<object_id>\d+)/(?P<ajax>json|xml)/$', views.free_comment, name="tc_free_comment_ajax"),
    url(r'^freecomment/(?P<content_type>\d+)/(?P<object_id>\d+)/(?P<parent_id>\d+)/(?P<ajax>json|xml)/$', views.free_comment, name="tc_free_comment_parent_ajax"),
    url(r'^freecomment/(?P<edit_id>\d+)/edit/(?P<ajax>json|xml)/$', views.free_comment, name="tc_free_comment_edit_ajax"),
)
########NEW FILE########
__FILENAME__ = utils
from django.core.serializers import serialize
from django.http import HttpResponse
from django.utils import simplejson
from django.utils.functional import Promise
from django.utils.encoding import force_unicode 

class LazyEncoder(simplejson.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Promise):
            return force_unicode(obj)
        return obj

class JSONResponse(HttpResponse):
    """
    A simple subclass of ``HttpResponse`` which makes serializing to JSON easy.
    """
    def __init__(self, object, is_iterable = True):
        if is_iterable:
            content = serialize('json', object)
        else:
            content = simplejson.dumps(object, cls=LazyEncoder)
        super(JSONResponse, self).__init__(content, mimetype='application/json')

class XMLResponse(HttpResponse):
    """
    A simple subclass of ``HttpResponse`` which makes serializing to XML easy.
    """
    def __init__(self, object, is_iterable = True):
        if is_iterable:
            content = serialize('xml', object)
        else:
            content = object
        super(XMLResponse, self).__init__(content, mimetype='application/xml')
########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponseRedirect, Http404
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext, Context, Template
from django.utils.http import urlquote
from django.conf import settings
from forms import FreeThreadedCommentForm, ThreadedCommentForm
from models import ThreadedComment, FreeThreadedComment, DEFAULT_MAX_COMMENT_LENGTH
from utils import JSONResponse, XMLResponse

def _adjust_max_comment_length(form, field_name='comment'):
    """
    Sets the maximum comment length to that default specified in the settings.
    """
    form.base_fields['comment'].max_length = DEFAULT_MAX_COMMENT_LENGTH

def _get_next(request):
    """
    The part that's the least straightforward about views in this module is how they 
    determine their redirects after they have finished computation.

    In short, they will try and determine the next place to go in the following order:

    1. If there is a variable named ``next`` in the *POST* parameters, the view will
    redirect to that variable's value.
    2. If there is a variable named ``next`` in the *GET* parameters, the view will
    redirect to that variable's value.
    3. If Django can determine the previous page from the HTTP headers, the view will
    redirect to that previous page.
    4. Otherwise, the view raise a 404 Not Found.
    """
    next = request.POST.get('next', request.GET.get('next', request.META.get('HTTP_REFERER', None)))
    if not next or next == request.path:
        raise Http404 # No next url was supplied in GET or POST.
    return next

def _preview(request, context_processors, extra_context, form_class=ThreadedCommentForm):
    """
    Returns a preview of the comment so that the user may decide if he or she wants to
    edit it before submitting it permanently.
    """
    _adjust_max_comment_length(form_class)
    form = form_class(request.POST or None)
    context = {
        'next' : _get_next(request),
        'form' : form,
    }
    if form.is_valid():
        new_comment = form.save(commit=False)
        context['comment'] = new_comment
    else:
        context['comment'] = None
    return render_to_response(
        'threadedcomments/preview_comment.html',
        extra_context, 
        context_instance = RequestContext(request, context, context_processors)
    )

def free_comment(request, content_type=None, object_id=None, edit_id=None, parent_id=None, add_messages=False, ajax=False, model=FreeThreadedComment, form_class=FreeThreadedCommentForm, context_processors=[], extra_context={}):
    """
    Receives POST data and either creates a new ``ThreadedComment`` or 
    ``FreeThreadedComment``, or edits an old one based upon the specified parameters.

    If there is a 'preview' key in the POST request, a preview will be forced and the
    comment will not be saved until a 'preview' key is no longer in the POST request.
    
    If it is an *AJAX* request (either XML or JSON), it will return a serialized
    version of the last created ``ThreadedComment`` and there will be no redirect.
    
    If invalid POST data is submitted, this will go to the comment preview page
    where the comment may be edited until it does not contain errors.
    """
    if not edit_id and not (content_type and object_id):
        raise Http404 # Must specify either content_type and object_id or edit_id
    if "preview" in request.POST:
        return _preview(request, context_processors, extra_context, form_class=form_class)
    if edit_id:
        instance = get_object_or_404(model, id=edit_id)
    else:
        instance = None
    _adjust_max_comment_length(form_class)
    form = form_class(request.POST, instance=instance)
    if form.is_valid():
        new_comment = form.save(commit=False)
        if not edit_id:
            new_comment.ip_address = request.META.get('REMOTE_ADDR', None)
            new_comment.content_type = get_object_or_404(ContentType, id = int(content_type))
            new_comment.object_id = int(object_id)
        if model == ThreadedComment:
            new_comment.user = request.user
        if parent_id:
            new_comment.parent = get_object_or_404(model, id = int(parent_id))
        new_comment.save()
        if model == ThreadedComment:
            if add_messages:
                request.user.message_set.create(message="Your message has been posted successfully.")
        else:
            request.session['successful_data'] = {
                'name' : form.cleaned_data['name'],
                'website' : form.cleaned_data['website'],
                'email' : form.cleaned_data['email'],
            }
        if ajax == 'json':
            return JSONResponse([new_comment,])
        elif ajax == 'xml':
            return XMLResponse([new_comment,])
        else:
            return HttpResponseRedirect(_get_next(request))
    elif ajax=="json":
        return JSONResponse({'errors' : form.errors}, is_iterable=False)
    elif ajax=="xml":
        template_str = """
<errorlist>
    {% for error,name in errors %}
    <field name="{{ name }}">
        {% for suberror in error %}<error>{{ suberror }}</error>{% endfor %}
    </field>
    {% endfor %}
</errorlist>
        """
        response_str = Template(template_str).render(Context({'errors' : zip(form.errors.values(), form.errors.keys())}))
        return XMLResponse(response_str, is_iterable=False)
    else:
        return _preview(request, context_processors, extra_context, form_class=form_class)
      
def comment(*args, **kwargs):
    """
    Thin wrapper around free_comment which adds login_required status and also assigns
    the ``model`` to be ``ThreadedComment``.
    """
    kwargs['model'] = ThreadedComment
    kwargs['form_class'] = ThreadedCommentForm
    return free_comment(*args, **kwargs)
# Require login to be required, as request.user must exist and be valid.
comment = login_required(comment)

def can_delete_comment(comment, user):
    """
    Default callback function to determine wether the given user has the
    ability to delete the given comment.
    """
    if user.is_staff or user.is_superuser:
        return True
    if hasattr(comment, 'user') and comment.user == user:
        return True
    return False

def comment_delete(request, object_id, model=ThreadedComment, extra_context = {}, context_processors = [], permission_callback=can_delete_comment):
    """
    Deletes the specified comment, which can be either a ``FreeThreadedComment`` or a
    ``ThreadedComment``.  If it is a POST request, then the comment will be deleted
    outright, however, if it is a GET request, a confirmation page will be shown.
    """
    tc = get_object_or_404(model, id=int(object_id))
    if not permission_callback(tc, request.user):
        login_url = settings.LOGIN_URL
        current_url = urlquote(request.get_full_path())
        return HttpResponseRedirect("%s?next=%s" % (login_url, current_url))
    if request.method == "POST":
        tc.delete()
        return HttpResponseRedirect(_get_next(request))
    else:
        if model == ThreadedComment:
            is_free_threaded_comment = False
            is_threaded_comment = True
        else:
            is_free_threaded_comment = True
            is_threaded_comment = False
        return render_to_response(
            'threadedcomments/confirm_delete.html',
            extra_context, 
            context_instance = RequestContext(
                request, 
                {
                    'comment' : tc, 
                    'is_free_threaded_comment' : is_free_threaded_comment,
                    'is_threaded_comment' : is_threaded_comment,
                    'next' : _get_next(request),
                },
                context_processors
            )
        )
########NEW FILE########
__FILENAME__ = decorators

import pytz

from django.utils.encoding import smart_str
from django.conf import settings

default_tz = pytz.timezone(getattr(settings, "TIME_ZONE", "UTC"))

def localdatetime(field_name):
    def get_datetime(instance):
        return getattr(instance, field_name)
    def set_datetime(instance, value):
        return setattr(instance, field_name, value)
        
    def make_local_property(get_tz):
        def get_local(instance):
            tz = get_tz(instance)
            if not hasattr(tz, "localize"):
                tz = pytz.timezone(smart_str(tz))
            dt = get_datetime(instance)
            if dt.tzinfo is None:
                dt = default_tz.localize(dt)
            return dt.astimezone(tz)
        def set_local(instance, dt):
            if dt.tzinfo is None:
                tz = get_tz(instance)
                if not hasattr(tz, "localize"):
                    tz = pytz.timezone(smart_str(tz))
                dt = tz.localize(dt)
            dt = dt.astimezone(default_tz)
            return set_datetime(instance, dt)
        return property(get_local, set_local)
    return make_local_property

########NEW FILE########
__FILENAME__ = fields

from django.db import models
from django.conf import settings
from django.utils.encoding import smart_unicode, smart_str
from django.db.models import signals

from timezones import forms

import pytz

MAX_TIMEZONE_LENGTH = getattr(settings, "MAX_TIMEZONE_LENGTH", 100)
default_tz = pytz.timezone(getattr(settings, "TIME_ZONE", "UTC"))


assert(reduce(lambda x, y: x and (len(y) <= MAX_TIMEZONE_LENGTH),
              forms.TIMEZONE_CHOICES, True),
       "timezones.fields.TimeZoneField MAX_TIMEZONE_LENGTH is too small")

class TimeZoneField(models.CharField):
    def __init__(self, *args, **kwargs):
        defaults = {"max_length": MAX_TIMEZONE_LENGTH,
                    "default": settings.TIME_ZONE,
                    "choices": forms.TIMEZONE_CHOICES}
        defaults.update(kwargs)
        return super(TimeZoneField, self).__init__(*args, **defaults)
        
    def to_python(self, value):
        value = super(TimeZoneField, self).to_python(value)
        if value is None:
            return None # null=True
        return pytz.timezone(value)
        
    def get_db_prep_save(self, value):
        # Casts timezone into string format for entry into database.
        if value is not None:
            value = smart_unicode(value)
        return super(TimeZoneField, self).get_db_prep_save(value)

    def flatten_data(self, follow, obj=None):
        value = self._get_val_from_obj(obj)
        if value is None:
            value = ""
        return {self.attname: smart_unicode(value)}

    def formfield(self, **kwargs):
        defaults = {"form_class": forms.TimeZoneField}
        defaults.update(kwargs)
        return super(TimeZoneField, self).formfield(**defaults)

class LocalizedDateTimeField(models.DateTimeField):
    """
    A model field that provides automatic localized timezone support.
    timezone can be a timezone string, a callable (returning a timezone string),
    or a queryset keyword relation for the model, or a pytz.timezone()
    result.
    """
    def __init__(self, verbose_name=None, name=None, timezone=None, **kwargs):
        if isinstance(timezone, basestring):
            timezone = smart_str(timezone)
        if timezone in pytz.all_timezones_set:
            self.timezone = pytz.timezone(timezone)
        else:
            self.timezone = timezone
        super(LocalizedDateTimeField, self).__init__(verbose_name, name, **kwargs)
        
    def formfield(self, **kwargs):
        defaults = {"form_class": forms.LocalizedDateTimeField}
        if (not isinstance(self.timezone, basestring) and str(self.timezone) in pytz.all_timezones_set):
            defaults["timezone"] = str(self.timezone)
        defaults.update(kwargs)
        return super(LocalizedDateTimeField, self).formfield(**defaults)
        
    def get_db_prep_save(self, value):
        "Returns field's value prepared for saving into a database."
        ## convert to settings.TIME_ZONE
        if value is not None:
            if value.tzinfo is None:
                value = default_tz.localize(value)
            else:
                value = value.astimezone(default_tz)
        return super(LocalizedDateTimeField, self).get_db_prep_save(value)
        
    def get_db_prep_lookup(self, lookup_type, value):
        "Returns field's value prepared for database lookup."
        ## convert to settings.TIME_ZONE
        if value.tzinfo is None:
            value = default_tz.localize(value)
        else:
            value = value.astimezone(default_tz)
        return super(LocalizedDateTimeField, self).get_db_prep_lookup(lookup_type, value)

def prep_localized_datetime(sender, **kwargs):
    for field in sender._meta.fields:
        if not isinstance(field, LocalizedDateTimeField) or field.timezone is None:
            continue
        dt_field_name = "_datetimezone_%s" % field.attname
        def get_dtz_field(instance):
            return getattr(instance, dt_field_name)
        def set_dtz_field(instance, dt):
            if dt.tzinfo is None:
                dt = default_tz.localize(dt)
            time_zone = field.timezone
            if isinstance(field.timezone, basestring):
                tz_name = instance._default_manager.filter(
                    pk=model_instance._get_pk_val()
                ).values_list(field.timezone)[0][0]
                try:
                    time_zone = pytz.timezone(tz_name)
                except:
                    time_zone = default_tz
                if time_zone is None:
                    # lookup failed
                    time_zone = default_tz
                    #raise pytz.UnknownTimeZoneError(
                    #    "Time zone %r from relation %r was not found"
                    #    % (tz_name, field.timezone)
                    #)
            elif callable(time_zone):
                tz_name = time_zone()
                if isinstance(tz_name, basestring):
                    try:
                        time_zone = pytz.timezone(tz_name)
                    except:
                        time_zone = default_tz
                else:
                    time_zone = tz_name
                if time_zone is None:
                    # lookup failed
                    time_zone = default_tz
                    #raise pytz.UnknownTimeZoneError(
                    #    "Time zone %r from callable %r was not found"
                    #    % (tz_name, field.timezone)
                    #)
            setattr(instance, dt_field_name, dt.astimezone(time_zone))
        setattr(sender, field.attname, property(get_dtz_field, set_dtz_field))

## RED_FLAG: need to add a check at manage.py validation time that
##           time_zone value is a valid query keyword (if it is one)
signals.class_prepared.connect(prep_localized_datetime)

########NEW FILE########
__FILENAME__ = forms

import pytz

from django.conf import settings
from django import forms

from timezones.utils import adjust_datetime_to_timezone

TIMEZONE_CHOICES = tuple(zip(pytz.all_timezones, pytz.all_timezones))

class TimeZoneField(forms.ChoiceField):
    def __init__(self, choices=None,  max_length=None, min_length=None,
                 *args, **kwargs):
        self.max_length, self.min_length = max_length, min_length
        if choices is not None:
            kwargs["choices"] = choices
        else:
            kwargs["choices"] = TIMEZONE_CHOICES
        super(TimeZoneField, self).__init__(*args, **kwargs)

    def clean(self, value):
        value = super(TimeZoneField, self).clean(value)
        return pytz.timezone(value)

class LocalizedDateTimeField(forms.DateTimeField):
    """
    Converts the datetime from the user timezone to settings.TIME_ZONE.
    """
    def __init__(self, timezone=None, *args, **kwargs):
        super(LocalizedDateTimeField, self).__init__(*args, **kwargs)
        self.timezone = timezone or settings.TIME_ZONE
        
    def clean(self, value):
        value = super(LocalizedDateTimeField, self).clean(value)
        return adjust_datetime_to_timezone(value, from_tz=self.timezone)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = timezone_filters

from django.template import Node
from django.template import Library

from timezones.utils import localtime_for_timezone

register = Library()

def localtime(value, timezone):
    return localtime_for_timezone(value, timezone)
register.filter("localtime", localtime)


########NEW FILE########
__FILENAME__ = tests

__test__ = {"API_TESTS": r"""
>>> from django.conf import settings
>>> ORIGINAL_TIME_ZONE = settings.TIME_ZONE
>>> settings.TIME_ZONE = "UTC"

>>> from timezones import forms

# the default case where no timezone is given explicitly.
# uses settings.TIME_ZONE.
>>> f = forms.LocalizedDateTimeField()
>>> f.clean("2008-05-30 14:30:00")
datetime.datetime(2008, 5, 30, 14, 30, tzinfo=<UTC>)

# specify a timezone explicity. this may come from a UserProfile for example.
>>> f = forms.LocalizedDateTimeField(timezone="America/Denver")
>>> f.clean("2008-05-30 14:30:00")
datetime.datetime(2008, 5, 30, 20, 30, tzinfo=<UTC>)

>>> f = forms.TimeZoneField()
>>> f.clean('US/Eastern')
<DstTzInfo 'US/Eastern' EST-1 day, 19:00:00 STD>

>>> settings.TIME_ZONE = ORIGINAL_TIME_ZONE
""",
"DECORATOR_TESTS": r"""
>>> from timezones import decorators
>>> from datetime import *
>>> class Foo(object):
...     datetime = datetime(2008, 6, 20, 23, 58, 17)
...     @decorators.localdatetime('datetime')
...     def localdatetime(self):
...         return 'Australia/Lindeman'
...
>>> foo = Foo()
>>> foo.datetime
datetime.datetime(2008, 6, 20, 23, 58, 17)
>>> foo.localdatetime
datetime.datetime(2008, 6, 21, 9, 58, 17, tzinfo=<DstTzInfo 'Australia/Lindeman' EST+10:00:00 STD>)
>>> foo.localdatetime = datetime(2008, 6, 12, 23, 50, 0)
>>> foo.datetime
datetime.datetime(2008, 6, 12, 13, 50, tzinfo=<UTC>)
>>> foo.localdatetime
datetime.datetime(2008, 6, 12, 23, 50, tzinfo=<DstTzInfo 'Australia/Lindeman' EST+10:00:00 STD>)
"""}

########NEW FILE########
__FILENAME__ = utils

import pytz

from django.conf import settings
from django.utils.encoding import smart_str

def localtime_for_timezone(value, timezone):
    """
    Given a ``datetime.datetime`` object in UTC and a timezone represented as
    a string, return the localized time for the timezone.
    """
    return adjust_datetime_to_timezone(value, settings.TIME_ZONE, timezone)

def adjust_datetime_to_timezone(value, from_tz, to_tz=None):
    """
    Given a ``datetime`` object adjust it according to the from_tz timezone
    string into the to_tz timezone string.
    """
    if to_tz is None:
        to_tz = settings.TIME_ZONE
    if value.tzinfo is None:
        if not hasattr(from_tz, "localize"):
            from_tz = pytz.timezone(smart_str(from_tz))
        value = from_tz.localize(value)
    return value.astimezone(pytz.timezone(smart_str(to_tz)))

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from voting.models import Vote

admin.site.register(Vote)

########NEW FILE########
__FILENAME__ = managers
from django.conf import settings
from django.db import connection, models
from django.contrib.contenttypes.models import ContentType

qn = connection.ops.quote_name

class VoteManager(models.Manager):
    def get_score(self, obj):
        """
        Get a dictionary containing the total score for ``obj`` and
        the number of votes it's received.
        """
        query = """
        SELECT SUM(vote), COUNT(vote)
        FROM %s
        WHERE content_type_id = %%s
          AND object_id = %%s""" % qn(self.model._meta.db_table)
        ctype = ContentType.objects.get_for_model(obj)
        cursor = connection.cursor()
        cursor.execute(query, [ctype.id, obj._get_pk_val()])
        result = cursor.fetchall()[0]
        # MySQL returns floats and longs respectively for these
        # results, so we need to convert them to ints explicitly.
        return {
            'score': result[0] and int(result[0]) or 0,
            'num_votes': int(result[1]),
        }

    def get_scores_in_bulk(self, objects):
        """
        Get a dictionary mapping object ids to total score and number
        of votes for each object.
        """
        vote_dict = {}
        if len(objects) > 0:
            query = """
            SELECT object_id, SUM(vote), COUNT(vote)
            FROM %s
            WHERE content_type_id = %%s
              AND object_id IN (%s)
            GROUP BY object_id""" % (
                qn(self.model._meta.db_table),
                ','.join(['%s'] * len(objects))
            )
            ctype = ContentType.objects.get_for_model(objects[0])
            cursor = connection.cursor()
            cursor.execute(query, [ctype.id] + [obj._get_pk_val() \
                                                for obj in objects])
            results = cursor.fetchall()
            vote_dict = dict([(int(object_id), {
                              'score': int(score),
                              'num_votes': int(num_votes),
                          }) for object_id, score, num_votes in results])
        return vote_dict

    def record_vote(self, obj, user, vote):
        """
        Record a user's vote on a given object. Only allows a given user
        to vote once, though that vote may be changed.

        A zero vote indicates that any existing vote should be removed.
        """
        if vote not in (+1, 0, -1):
            raise ValueError('Invalid vote (must be +1/0/-1)')
        ctype = ContentType.objects.get_for_model(obj)
        try:
            v = self.get(user=user, content_type=ctype,
                         object_id=obj._get_pk_val())
            if vote == 0:
                v.delete()
            else:
                v.vote = vote
                v.save()
        except models.ObjectDoesNotExist:
            if vote != 0:
                self.create(user=user, content_type=ctype,
                            object_id=obj._get_pk_val(), vote=vote)

    def get_top(self, Model, limit=10, reversed=False):
        """
        Get the top N scored objects for a given model.

        Yields (object, score) tuples.
        """
        ctype = ContentType.objects.get_for_model(Model)
        query = """
        SELECT object_id, SUM(vote) as %s
        FROM %s
        WHERE content_type_id = %%s
        GROUP BY object_id""" % (
            qn('score'),
            qn(self.model._meta.db_table),
        )

        # MySQL has issues with re-using the aggregate function in the
        # HAVING clause, so we alias the score and use this alias for
        # its benefit.
        if settings.DATABASE_ENGINE == 'mysql':
            having_score = qn('score')
        else:
            having_score = 'SUM(vote)'
        if reversed:
            having_sql = ' HAVING %(having_score)s < 0 ORDER BY %(having_score)s ASC %(limit_offset)s'
        else:
            having_sql = ' HAVING %(having_score)s > 0 ORDER BY %(having_score)s DESC %(limit_offset)s'
        query += having_sql % {
            'having_score': having_score,
            'limit_offset': connection.ops.limit_offset_sql(limit),
        }

        cursor = connection.cursor()
        cursor.execute(query, [ctype.id])
        results = cursor.fetchall()

        # Use in_bulk() to avoid O(limit) db hits.
        objects = Model.objects.in_bulk([id for id, score in results])

        # Yield each object, score pair. Because of the lazy nature of generic
        # relations, missing objects are silently ignored.
        for id, score in results:
            if id in objects:
                yield objects[id], int(score)

    def get_bottom(self, Model, limit=10):
        """
        Get the bottom (i.e. most negative) N scored objects for a given
        model.

        Yields (object, score) tuples.
        """
        return self.get_top(Model, limit, True)

    def get_for_user(self, obj, user):
        """
        Get the vote made on the given object by the given user, or
        ``None`` if no matching vote exists.
        """
        if not user.is_authenticated():
            return None
        ctype = ContentType.objects.get_for_model(obj)
        try:
            vote = self.get(content_type=ctype, object_id=obj._get_pk_val(),
                            user=user)
        except models.ObjectDoesNotExist:
            vote = None
        return vote

    def get_for_user_in_bulk(self, objects, user):
        """
        Get a dictionary mapping object ids to votes made by the given
        user on the corresponding objects.
        """
        vote_dict = {}
        if len(objects) > 0:
            ctype = ContentType.objects.get_for_model(objects[0])
            votes = list(self.filter(content_type__pk=ctype.id,
                                     object_id__in=[obj._get_pk_val() \
                                                    for obj in objects],
                                     user__pk=user.id))
            vote_dict = dict([(vote.object_id, vote) for vote in votes])
        return vote_dict

########NEW FILE########
__FILENAME__ = models
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from django.db import models

from voting.managers import VoteManager

SCORES = (
    (u'+1', +1),
    (u'-1', -1),
)

class Vote(models.Model):
    """
    A vote on an object by a User.
    """
    user         = models.ForeignKey(User)
    content_type = models.ForeignKey(ContentType)
    object_id    = models.PositiveIntegerField()
    object       = generic.GenericForeignKey('content_type', 'object_id')
    vote         = models.SmallIntegerField(choices=SCORES)

    objects = VoteManager()

    class Meta:
        db_table = 'votes'
        # One vote per user per object
        unique_together = (('user', 'content_type', 'object_id'),)

    def __unicode__(self):
        return u'%s: %s on %s' % (self.user, self.vote, self.object)

    def is_upvote(self):
        return self.vote == 1

    def is_downvote(self):
        return self.vote == -1

########NEW FILE########
__FILENAME__ = voting_tags
from django import template
from django.utils.html import escape

from voting.models import Vote

register = template.Library()

# Tags

class ScoreForObjectNode(template.Node):
    def __init__(self, object, context_var):
        self.object = object
        self.context_var = context_var

    def render(self, context):
        try:
            object = template.resolve_variable(self.object, context)
        except template.VariableDoesNotExist:
            return ''
        context[self.context_var] = Vote.objects.get_score(object)
        return ''

class ScoresForObjectsNode(template.Node):
    def __init__(self, objects, context_var):
        self.objects = objects
        self.context_var = context_var

    def render(self, context):
        try:
            objects = template.resolve_variable(self.objects, context)
        except template.VariableDoesNotExist:
            return ''
        context[self.context_var] = Vote.objects.get_scores_in_bulk(objects)
        return ''

class VoteByUserNode(template.Node):
    def __init__(self, user, object, context_var):
        self.user = user
        self.object = object
        self.context_var = context_var

    def render(self, context):
        try:
            user = template.resolve_variable(self.user, context)
            object = template.resolve_variable(self.object, context)
        except template.VariableDoesNotExist:
            return ''
        context[self.context_var] = Vote.objects.get_for_user(object, user)
        return ''

class VotesByUserNode(template.Node):
    def __init__(self, user, objects, context_var):
        self.user = user
        self.objects = objects
        self.context_var = context_var

    def render(self, context):
        try:
            user = template.resolve_variable(self.user, context)
            objects = template.resolve_variable(self.objects, context)
        except template.VariableDoesNotExist:
            return ''
        context[self.context_var] = Vote.objects.get_for_user_in_bulk(objects, user)
        return ''

class DictEntryForItemNode(template.Node):
    def __init__(self, item, dictionary, context_var):
        self.item = item
        self.dictionary = dictionary
        self.context_var = context_var

    def render(self, context):
        try:
            dictionary = template.resolve_variable(self.dictionary, context)
            item = template.resolve_variable(self.item, context)
        except template.VariableDoesNotExist:
            return ''
        context[self.context_var] = dictionary.get(item.id, None)
        return ''

def do_score_for_object(parser, token):
    """
    Retrieves the total score for an object and the number of votes
    it's received and stores them in a context variable which has
    ``score`` and ``num_votes`` properties.

    Example usage::

        {% score_for_object widget as score %}

        {{ score.score }}point{{ score.score|pluralize }}
        after {{ score.num_votes }} vote{{ score.num_votes|pluralize }}
    """
    bits = token.contents.split()
    if len(bits) != 4:
        raise template.TemplateSyntaxError("'%s' tag takes exactly three arguments" % bits[0])
    if bits[2] != 'as':
        raise template.TemplateSyntaxError("second argument to '%s' tag must be 'as'" % bits[0])
    return ScoreForObjectNode(bits[1], bits[3])

def do_scores_for_objects(parser, token):
    """
    Retrieves the total scores for a list of objects and the number of
    votes they have received and stores them in a context variable.

    Example usage::

        {% scores_for_objects widget_list as score_dict %}
    """
    bits = token.contents.split()
    if len(bits) != 4:
        raise template.TemplateSyntaxError("'%s' tag takes exactly three arguments" % bits[0])
    if bits[2] != 'as':
        raise template.TemplateSyntaxError("second argument to '%s' tag must be 'as'" % bits[0])
    return ScoresForObjectsNode(bits[1], bits[3])

def do_vote_by_user(parser, token):
    """
    Retrieves the ``Vote`` cast by a user on a particular object and
    stores it in a context variable. If the user has not voted, the
    context variable will be ``None``.

    Example usage::

        {% vote_by_user user on widget as vote %}
    """
    bits = token.contents.split()
    if len(bits) != 6:
        raise template.TemplateSyntaxError("'%s' tag takes exactly five arguments" % bits[0])
    if bits[2] != 'on':
        raise template.TemplateSyntaxError("second argument to '%s' tag must be 'on'" % bits[0])
    if bits[4] != 'as':
        raise template.TemplateSyntaxError("fourth argument to '%s' tag must be 'as'" % bits[0])
    return VoteByUserNode(bits[1], bits[3], bits[5])

def do_votes_by_user(parser, token):
    """
    Retrieves the votes cast by a user on a list of objects as a
    dictionary keyed with object ids and stores it in a context
    variable.

    Example usage::

        {% votes_by_user user on widget_list as vote_dict %}
    """
    bits = token.contents.split()
    if len(bits) != 6:
        raise template.TemplateSyntaxError("'%s' tag takes exactly four arguments" % bits[0])
    if bits[2] != 'on':
        raise template.TemplateSyntaxError("second argument to '%s' tag must be 'on'" % bits[0])
    if bits[4] != 'as':
        raise template.TemplateSyntaxError("fourth argument to '%s' tag must be 'as'" % bits[0])
    return VotesByUserNode(bits[1], bits[3], bits[5])

def do_dict_entry_for_item(parser, token):
    """
    Given an object and a dictionary keyed with object ids - as
    returned by the ``votes_by_user`` and ``scores_for_objects``
    template tags - retrieves the value for the given object and
    stores it in a context variable, storing ``None`` if no value
    exists for the given object.

    Example usage::

        {% dict_entry_for_item widget from vote_dict as vote %}
    """
    bits = token.contents.split()
    if len(bits) != 6:
        raise template.TemplateSyntaxError("'%s' tag takes exactly five arguments" % bits[0])
    if bits[2] != 'from':
        raise template.TemplateSyntaxError("second argument to '%s' tag must be 'from'" % bits[0])
    if bits[4] != 'as':
        raise template.TemplateSyntaxError("fourth argument to '%s' tag must be 'as'" % bits[0])
    return DictEntryForItemNode(bits[1], bits[3], bits[5])

register.tag('score_for_object', do_score_for_object)
register.tag('scores_for_objects', do_scores_for_objects)
register.tag('vote_by_user', do_vote_by_user)
register.tag('votes_by_user', do_votes_by_user)
register.tag('dict_entry_for_item', do_dict_entry_for_item)

# Simple Tags

def confirm_vote_message(object_description, vote_direction):
    """
    Creates an appropriate message asking the user to confirm the given vote
    for the given object description.

    Example usage::

        {% confirm_vote_message widget.title direction %}
    """
    if vote_direction == 'clear':
        message = 'Confirm clearing your vote for <strong>%s</strong>.'
    else:
        message = 'Confirm <strong>%s</strong> vote for <strong>%%s</strong>.' % vote_direction
    return message % (escape(object_description),)

register.simple_tag(confirm_vote_message)

# Filters

def vote_display(vote, arg=None):
    """
    Given a string mapping values for up and down votes, returns one
    of the strings according to the given ``Vote``:

    =========  =====================  =============
    Vote type   Argument               Outputs
    =========  =====================  =============
    ``+1``     ``"Bodacious,Bogus"``  ``Bodacious``
    ``-1``     ``"Bodacious,Bogus"``  ``Bogus``
    =========  =====================  =============

    If no string mapping is given, "Up" and "Down" will be used.

    Example usage::

        {{ vote|vote_display:"Bodacious,Bogus" }}
    """
    if arg is None:
        arg = 'Up,Down'
    bits = arg.split(',')
    if len(bits) != 2:
        return vote.vote # Invalid arg
    up, down = bits
    if vote.vote == 1:
        return up
    return down

register.filter(vote_display)
########NEW FILE########
__FILENAME__ = models
from django.db import models

class Item(models.Model):
    name = models.CharField(maxlength=50)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
########NEW FILE########
__FILENAME__ = runtests
import os, sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'voting.tests.settings'

from django.test.simple import run_tests

failures = run_tests(None, verbosity=9)
if failures:
    sys.exit(failures)

########NEW FILE########
__FILENAME__ = settings
import os
DIRNAME = os.path.dirname(__file__)

DEFAULT_CHARSET = 'utf-8'

DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = os.path.join(DIRNAME, 'database.db')

#DATABASE_ENGINE = 'mysql'
#DATABASE_NAME = 'tagging_test'
#DATABASE_USER = 'root'
#DATABASE_PASSWORD = ''
#DATABASE_HOST = 'localhost'
#DATABASE_PORT = '3306'

#DATABASE_ENGINE = 'postgresql_psycopg2'
#DATABASE_NAME = 'tagging_test'
#DATABASE_USER = 'postgres'
#DATABASE_PASSWORD = ''
#DATABASE_HOST = 'localhost'
#DATABASE_PORT = '5432'

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'voting',
    'voting.tests',
)
########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
r"""
>>> from django.contrib.auth.models import User
>>> from voting.models import Vote
>>> from voting.tests.models import Item

##########
# Voting #
##########

# Basic voting ###############################################################

>>> i1 = Item.objects.create(name='test1')
>>> users = []
>>> for username in ['u1', 'u2', 'u3', 'u4']:
...     users.append(User.objects.create_user(username, '%s@test.com' % username, 'test'))
>>> Vote.objects.get_score(i1)
{'score': 0, 'num_votes': 0}
>>> Vote.objects.record_vote(i1, users[0], +1)
>>> Vote.objects.get_score(i1)
{'score': 1, 'num_votes': 1}
>>> Vote.objects.record_vote(i1, users[0], -1)
>>> Vote.objects.get_score(i1)
{'score': -1, 'num_votes': 1}
>>> Vote.objects.record_vote(i1, users[0], 0)
>>> Vote.objects.get_score(i1)
{'score': 0, 'num_votes': 0}
>>> for user in users:
...     Vote.objects.record_vote(i1, user, +1)
>>> Vote.objects.get_score(i1)
{'score': 4, 'num_votes': 4}
>>> for user in users[:2]:
...     Vote.objects.record_vote(i1, user, 0)
>>> Vote.objects.get_score(i1)
{'score': 2, 'num_votes': 2}
>>> for user in users[:2]:
...     Vote.objects.record_vote(i1, user, -1)
>>> Vote.objects.get_score(i1)
{'score': 0, 'num_votes': 4}

>>> Vote.objects.record_vote(i1, user, -2)
Traceback (most recent call last):
    ...
ValueError: Invalid vote (must be +1/0/-1)

# Retrieval of votes #########################################################

>>> i2 = Item.objects.create(name='test2')
>>> i3 = Item.objects.create(name='test3')
>>> i4 = Item.objects.create(name='test4')
>>> Vote.objects.record_vote(i2, users[0], +1)
>>> Vote.objects.record_vote(i3, users[0], -1)
>>> Vote.objects.record_vote(i4, users[0], 0)
>>> vote = Vote.objects.get_for_user(i2, users[0])
>>> (vote.vote, vote.is_upvote(), vote.is_downvote())
(1, True, False)
>>> vote = Vote.objects.get_for_user(i3, users[0])
>>> (vote.vote, vote.is_upvote(), vote.is_downvote())
(-1, False, True)
>>> Vote.objects.get_for_user(i4, users[0]) is None
True

# In bulk
>>> votes = Vote.objects.get_for_user_in_bulk([i1, i2, i3, i4], users[0])
>>> [(id, vote.vote) for id, vote in votes.items()]
[(1, -1), (2, 1), (3, -1)]
>>> Vote.objects.get_for_user_in_bulk([], users[0])
{}

>>> for user in users[1:]:
...     Vote.objects.record_vote(i2, user, +1)
...     Vote.objects.record_vote(i3, user, +1)
...     Vote.objects.record_vote(i4, user, +1)
>>> list(Vote.objects.get_top(Item))
[(<Item: test2>, 4), (<Item: test4>, 3), (<Item: test3>, 2)]
>>> for user in users[1:]:
...     Vote.objects.record_vote(i2, user, -1)
...     Vote.objects.record_vote(i3, user, -1)
...     Vote.objects.record_vote(i4, user, -1)
>>> list(Vote.objects.get_bottom(Item))
[(<Item: test3>, -4), (<Item: test4>, -3), (<Item: test2>, -2)]

>>> Vote.objects.get_scores_in_bulk([i1, i2, i3, i4])
{1: {'score': 0, 'num_votes': 4}, 2: {'score': -2, 'num_votes': 4}, 3: {'score': -4, 'num_votes': 4}, 4: {'score': -3, 'num_votes': 3}}
>>> Vote.objects.get_scores_in_bulk([])
{}
"""

########NEW FILE########
__FILENAME__ = views
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.contrib.auth.views import redirect_to_login
from django.template import loader, RequestContext
from django.utils import simplejson

from voting.models import Vote

VOTE_DIRECTIONS = (('up', 1), ('down', -1), ('clear', 0))

def vote_on_object(request, model, direction, post_vote_redirect=None,
        object_id=None, slug=None, slug_field=None, template_name=None,
        template_loader=loader, extra_context=None, context_processors=None,
        template_object_name='object', allow_xmlhttprequest=False):
    """
    Generic object vote function.

    The given template will be used to confirm the vote if this view is
    fetched using GET; vote registration will only be performed if this
    view is POSTed.

    If ``allow_xmlhttprequest`` is ``True`` and an XMLHttpRequest is
    detected by examining the ``HTTP_X_REQUESTED_WITH`` header, the
    ``xmlhttp_vote_on_object`` view will be used to process the
    request - this makes it trivial to implement voting via
    XMLHttpRequest with a fallback for users who don't have JavaScript
    enabled.

    Templates:``<app_label>/<model_name>_confirm_vote.html``
    Context:
        object
            The object being voted on.
        direction
            The type of vote which will be registered for the object.
    """
    if (allow_xmlhttprequest and
        request.META.has_key('HTTP_X_REQUESTED_WITH') and
        request.META['HTTP_X_REQUESTED_WITH'] == 'XMLHttpRequest'):
        return xmlhttprequest_vote_on_object(request, model, direction,
                                             object_id=object_id, slug=slug,
                                             slug_field=slug_field)

    if extra_context is None: extra_context = {}
    if not request.user.is_authenticated():
        return redirect_to_login(request.path)

    try:
        vote = dict(VOTE_DIRECTIONS)[direction]
    except KeyError:
        raise AttributeError('\'%s\' is not a valid vote type.' % vote_type)

    # Look up the object to be voted on
    lookup_kwargs = {}
    if object_id:
        lookup_kwargs['%s__exact' % model._meta.pk.name] = object_id
    elif slug and slug_field:
        lookup_kwargs['%s__exact' % slug_field] = slug
    else:
        raise AttributeError('Generic vote view must be called with either object_id slug/slug_field.')
    try:
        obj = model._default_manager.get(**lookup_kwargs)
    except ObjectDoesNotExist:
        raise Http404, 'No %s found for %s.' % (model._meta.app_label, lookup_kwargs)

    if request.method == 'POST':
        if post_vote_redirect is not None:
            next = post_vote_redirect
        elif request.REQUEST.has_key('next'):
            next = request.REQUEST['next']
        elif hasattr(obj, 'get_absolute_url'):
            if callable(getattr(obj, 'get_absolute_url')):
                next = obj.get_absolute_url()
            else:
                next = obj.get_absolute_url
        else:
            raise AttributeError('Generic vote view must be called with either post_vote_redirect, a "next" parameter in the request, or the object being voted on must define a get_absolute_url method or property.')
        Vote.objects.record_vote(obj, request.user, vote)
        return HttpResponseRedirect(next)
    else:
        if not template_name:
            template_name = '%s/%s_confirm_vote.html' % (model._meta.app_label, model._meta.object_name.lower())
        t = template_loader.get_template(template_name)
        c = RequestContext(request, {
            template_object_name: obj,
            'direction': direction,
        }, context_processors)
        for key, value in extra_context.items():
            if callable(value):
                c[key] = value()
            else:
                c[key] = value
        response = HttpResponse(t.render(c))
        return response

def json_error_response(error_message, *args, **kwargs):
    return HttpResponse(simplejson.dumps(dict(success=False,
                                              error_message=error_message)))

def xmlhttprequest_vote_on_object(request, model, direction,
    object_id=None, slug=None, slug_field=None):
    """
    Generic object vote function for use via XMLHttpRequest.

    Properties of the resulting JSON object:
        success
            ``true`` if the vote was successfully processed, ``false``
            otherwise.
        score
            The object's updated score and number of votes if the vote
            was successfully processed.
        error_message
            Contains an error message if the vote was not successfully
            processed.
    """
    if request.method == 'GET':
        return json_error_response('XMLHttpRequest votes can only be made using POST.')
    if not request.user.is_authenticated():
        return json_error_response('Not authenticated.')

    try:
        vote = dict(VOTE_DIRECTIONS)[direction]
    except KeyError:
        return json_error_response('\'%s\' is not a valid vote type.' % direction)

    # Look up the object to be voted on
    lookup_kwargs = {}
    if object_id:
        lookup_kwargs['%s__exact' % model._meta.pk.name] = object_id
    elif slug and slug_field:
        lookup_kwargs['%s__exact' % slug_field] = slug
    else:
        return json_error_response('Generic XMLHttpRequest vote view must be called with either object_id or slug/slug_field.')
    try:
        obj = model._default_manager.get(**lookup_kwargs)
    except ObjectDoesNotExist:
        return json_error_response('No %s found for %s.' % (model._meta.verbose_name, lookup_kwargs))

    # Vote and respond
    Vote.objects.record_vote(obj, request.user, vote)
    return HttpResponse(simplejson.dumps({'success': True,
                                          'score': Vote.objects.get_score(obj)}))

########NEW FILE########
