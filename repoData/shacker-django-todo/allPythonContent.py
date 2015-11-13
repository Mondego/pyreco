__FILENAME__ = admin
from django.contrib import admin
from todo.models import Item, User, List, Comment

class ItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'list', 'priority', 'due_date')
    list_filter = ('list',)
    ordering = ('priority',)
    search_fields = ('name',)


admin.site.register(List)
admin.site.register(Comment)
admin.site.register(Item,ItemAdmin)
########NEW FILE########
__FILENAME__ = forms
from django.db import models
from django import forms
from django.forms import ModelForm
from django.contrib.auth.models import User,Group
from todo.models import Item, List
import datetime

class AddListForm(ModelForm):    
    # The picklist showing allowable groups to which a new list can be added
    # determines which groups the user belongs to. This queries the form object
    # to derive that list.
    def __init__(self, user, *args, **kwargs):
        super(AddListForm, self).__init__(*args, **kwargs)
        self.fields['group'].queryset = Group.objects.filter(user=user)

    class Meta:
        model = List
        
 
        
class AddItemForm(ModelForm):
    
    # The picklist showing the users to which a new task can be assigned
    # must find other members of the groups the current list belongs to.
    def __init__(self, task_list, *args, **kwargs):
        super(AddItemForm, self).__init__(*args, **kwargs)
        # print dir(self.fields['list'])
        # print self.fields['list'].initial
        self.fields['assigned_to'].queryset = User.objects.filter(groups__in=[task_list.group])
            
    due_date = forms.DateField(
                    required=False,
                    widget=forms.DateTimeInput(attrs={'class':'due_date_picker'})
                    )
                    
    title = forms.CharField(
                    widget=forms.widgets.TextInput(attrs={'size':35})
                    ) 

    class Meta:
        model = Item
        


class EditItemForm(ModelForm):

    # The picklist showing the users to which a new task can be assigned
    # must find other members of the groups the current list belongs to.
    def __init__(self,  *args, **kwargs):
        super(EditItemForm, self).__init__(*args, **kwargs)
        self.fields['assigned_to'].queryset = User.objects.filter(groups__in=[self.instance.list.group])

    class Meta:
        model = Item
        exclude = ('created_date','created_by',)             
        

        
class AddExternalItemForm(ModelForm):
    """Form to allow users who are not part of the GTD system to file a ticket."""

    title = forms.CharField(
                    widget=forms.widgets.TextInput(attrs={'size':35})
                    ) 
    note = forms.CharField (
        widget=forms.widgets.Textarea(),
        help_text='Foo',
        )
    
    class Meta:
        model = Item
        exclude = ('list','created_date','due_date','created_by','assigned_to',)
        


class SearchForm(ModelForm):
    """Search."""

    q = forms.CharField(
                    widget=forms.widgets.TextInput(attrs={'size':35})
                    ) 



########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.forms.models import ModelForm
from django import forms
from django.contrib import admin
from django.contrib.auth.models import User,Group
import string, datetime
from django.template.defaultfilters import slugify


class List(models.Model):
    name = models.CharField(max_length=60)
    slug = models.SlugField(max_length=60,editable=False)
    # slug = models.SlugField(max_length=60)    
    group = models.ForeignKey(Group)
    
    def save(self, *args, **kwargs):
        if not self.id:
            self.slug = slugify(self.name)

        super(List, self).save(*args, **kwargs)

    

    def __unicode__(self):
        return self.name
        
    # Custom manager lets us do things like Item.completed_tasks.all()
    objects = models.Manager()
    
    def incomplete_tasks(self):
        # Count all incomplete tasks on the current list instance
        return Item.objects.filter(list=self,completed=0)
        
    class Meta:
        ordering = ["name"]        
        verbose_name_plural = "Lists"
        
        # Prevents (at the database level) creation of two lists with the same name in the same group
        unique_together = ("group", "slug")
        
        


        
class Item(models.Model):
    title = models.CharField(max_length=140)
    list = models.ForeignKey(List)
    created_date = models.DateField(auto_now=True, auto_now_add=True)
    due_date = models.DateField(blank=True,null=True,)
    completed = models.BooleanField()
    completed_date = models.DateField(blank=True,null=True)
    created_by = models.ForeignKey(User, related_name='created_by')
    assigned_to = models.ForeignKey(User, related_name='todo_assigned_to')
    note = models.TextField(blank=True,null=True)
    priority = models.PositiveIntegerField(max_length=3)
    
    # Model method: Has due date for an instance of this object passed?
    def overdue_status(self):
        "Returns whether the item's due date has passed or not."
        if datetime.date.today() > self.due_date :
            return 1

    def __unicode__(self):
        return self.title
        
    # Auto-set the item creation / completed date
    def save(self):
        # If Item is being marked complete, set the completed_date
        if self.completed :
            self.completed_date = datetime.datetime.now()
        super(Item, self).save()


    class Meta:
        ordering = ["priority"]        
        

class Comment(models.Model):    
    """
    Not using Django's built-in comments becase we want to be able to save 
    a comment and change task details at the same time. Rolling our own since it's easy.
    """
    author = models.ForeignKey(User)
    task = models.ForeignKey(Item)
    date = models.DateTimeField(default=datetime.datetime.now)
    body = models.TextField(blank=True)
    
    def __unicode__(self):        
        return '%s - %s' % (
                self.author, 
                self.date, 
                )        
########NEW FILE########
__FILENAME__ = settings
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings

STAFF_ONLY = getattr(settings, 'TODO_STAFF_ONLY', False)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import *
from django.contrib.auth import views as auth_views

urlpatterns = patterns('',
    url(r'^mine/$', 'todo.views.view_list',{'list_slug':'mine'},name="todo-mine"),
    url(r'^(?P<list_id>\d{1,4})/(?P<list_slug>[\w-]+)/delete$', 'todo.views.del_list',name="todo-del_list"),
    url(r'^task/(?P<task_id>\d{1,6})$', 'todo.views.view_task', name='todo-task_detail'),
    url(r'^(?P<list_id>\d{1,4})/(?P<list_slug>[\w-]+)$', 'todo.views.view_list', name='todo-incomplete_tasks'),
    url(r'^(?P<list_id>\d{1,4})/(?P<list_slug>[\w-]+)/completed$', 'todo.views.view_list', {'view_completed':1},name='todo-completed_tasks'),    
    url(r'^add_list/$', 'todo.views.add_list',name="todo-add_list"),
    url(r'^search/$', 'todo.views.search',name="todo-search"),    
    url(r'^$', 'todo.views.list_lists',name="todo-lists"),
    
    # View reorder_tasks is only called by JQuery for drag/drop task ordering
    url(r'^reorder_tasks/$', 'todo.views.reorder_tasks',name="todo-reorder_tasks"),
    
    url(r'^ticket/add/$', 'todo.views.external_add',name="todo-external-add"),    
    url(r'^recent/added/$', 'todo.views.view_list',{'list_slug':'recent-add'},name="todo-recently_added"),
    url(r'^recent/completed/$', 'todo.views.view_list',{'list_slug':'recent-complete'},name="todo-recently_completed"),    
)


########NEW FILE########
__FILENAME__ = views
from django import forms 
from django.shortcuts import render_to_response
from todo.models import Item, List, Comment
from todo.forms import AddListForm, AddItemForm, EditItemForm, AddExternalItemForm, SearchForm
from todo import settings
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.contrib import auth
from django.template import RequestContext
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django.contrib.sites.models import Site
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.contrib.auth.decorators import user_passes_test
from django.db import IntegrityError
from django.db.models import Q
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt

import datetime

# Need for links in email templates
current_site = Site.objects.get_current() 


def check_user_allowed(user):

    """
    test for user_passes_test decorator
    """
    if settings.STAFF_ONLY:
        return user.is_authenticated() and user.is_staff
    else:
        return user.is_authenticated()



@user_passes_test(check_user_allowed)
def list_lists(request):

    """
    Homepage view - list of lists a user can view, and ability to add a list.
    """
    
    # Make sure user belongs to at least one group.
    group_count = request.user.groups.all().count()
    if group_count == 0:
        messages.error(request, "You do not yet belong to any groups. Ask your administrator to add you to one.")                        
        

    # Only show lists to the user that belong to groups they are members of.
    # Superusers see all lists
    if request.user.is_superuser:
        list_list = List.objects.all().order_by('group','name')
    else:
        list_list = List.objects.filter(group__in=request.user.groups.all).order_by('group','name')
    
    # Count everything
    list_count = list_list.count()
    
    # Note admin users see all lists, so count shouldn't filter by just lists the admin belongs to
    if request.user.is_superuser :
        item_count = Item.objects.filter(completed=0).count()        
    else:
        item_count = Item.objects.filter(completed=0).filter(list__group__in=request.user.groups.all()).count()

    return render_to_response('todo/list_lists.html', locals(), context_instance=RequestContext(request))  
    

@user_passes_test(check_user_allowed)
def del_list(request,list_id,list_slug):

    """
    Delete an entire list. Danger Will Robinson! Only staff members should be allowed to access this view.
    """
    
    if request.user.is_staff:
        can_del = 1

    # Get this list's object (to derive list.name, list.id, etc.)
    list = get_object_or_404(List, slug=list_slug)

    # If delete confirmation is in the POST, delete all items in the list, then kill the list itself
    if request.method == 'POST':
        # Can the items
        del_items = Item.objects.filter(list=list.id)
        for del_item in del_items:
            del_item.delete()
        
        # Kill the list
        del_list = List.objects.get(id=list.id)
        del_list.delete()
        
        # A var to send to the template so we can show the right thing
        list_killed = 1

    else:
        item_count_done = Item.objects.filter(list=list.id,completed=1).count()
        item_count_undone = Item.objects.filter(list=list.id,completed=0).count()
        item_count_total = Item.objects.filter(list=list.id).count()    
    
    return render_to_response('todo/del_list.html', locals(), context_instance=RequestContext(request))


@user_passes_test(check_user_allowed)
def view_list(request,list_id=0,list_slug=None,view_completed=0):
    
    """
    Display and manage items in a task list
    """
    
    # Make sure the accessing user has permission to view this list.
    # Always authorize the "mine" view. Admins can view/edit all lists.

    if list_slug == "mine"  or list_slug == "recent-add" or list_slug == "recent-complete" :
        auth_ok =1
    else: 
        list = get_object_or_404(List, slug=list_slug)
        listid = list.id    
        
        # Check whether current user is a member of the group this list belongs to.
        if list.group in request.user.groups.all() or request.user.is_staff or list_slug == "mine" :
            auth_ok = 1   # User is authorized for this view
        else: # User does not belong to the group this list is attached to
            messages.error(request, "You do not have permission to view/edit this list.")                                    

        
    # First check for items in the mark_done POST array. If present, change
    # their status to complete.
    if request.POST.getlist('mark_done'):
        done_items = request.POST.getlist('mark_done')
        # Iterate through array of done items and update its representation in the model
        for thisitem in done_items:
            p = Item.objects.get(id=thisitem)
            p.completed = 1
            p.completed_date = datetime.datetime.now()
            p.save()
            messages.success(request, "Item \"%s\" marked complete." % p.title)                                             


    # Undo: Set completed items back to incomplete
    if request.POST.getlist('undo_completed_task'):
        undone_items = request.POST.getlist('undo_completed_task')
        for thisitem in undone_items:
            p = Item.objects.get(id=thisitem)
            p.completed = 0
            p.save()
            messages.success(request, "Previously completed task \"%s\" marked incomplete." % p.title)


    # And delete any requested items
    if request.POST.getlist('del_task'):
        deleted_items = request.POST.getlist('del_task')
        for thisitem in deleted_items:
            p = Item.objects.get(id=thisitem)
            p.delete()
            messages.success(request, "Item \"%s\" deleted." % p.title)         

    # And delete any *already completed* items
    if request.POST.getlist('del_completed_task'):
        deleted_items = request.POST.getlist('del_completed_task')
        for thisitem in deleted_items:
            p = Item.objects.get(id=thisitem)
            p.delete()
            messages.success(request, "Deleted previously completed item \"%s\"."  % p.title)                       


    thedate = datetime.datetime.now()
    created_date = "%s-%s-%s" % (thedate.year, thedate.month, thedate.day)


    # Get list of items with this list ID, or filter on items assigned to me, or recently added/completed
    if list_slug == "mine":
        task_list = Item.objects.filter(assigned_to=request.user, completed=0)
        completed_list = Item.objects.filter(assigned_to=request.user, completed=1)
        
    elif list_slug == "recent-add":
        # We'll assume this only includes uncompleted items to avoid confusion.
        # Only show items in lists that are in groups that the current user is also in.
        task_list = Item.objects.filter(list__group__in=(request.user.groups.all()),completed=0).order_by('-created_date')[:50]
        # completed_list = Item.objects.filter(assigned_to=request.user, completed=1)   
        
    elif list_slug == "recent-complete":
        # Only show items in lists that are in groups that the current user is also in.
        task_list = Item.objects.filter(list__group__in=request.user.groups.all(),completed=1).order_by('-completed_date')[:50]
        # completed_list = Item.objects.filter(assigned_to=request.user, completed=1)             


    else:
        task_list = Item.objects.filter(list=list.id, completed=0)
        completed_list = Item.objects.filter(list=list.id, completed=1)


    if request.POST.getlist('add_task') :
        form = AddItemForm(list, request.POST,initial={
        'assigned_to':request.user.id,
        'priority':999,
        })
        
        if form.is_valid():
            # Save task first so we have a db object to play with
            new_task = form.save()

            # Send email alert only if the Notify checkbox is checked AND the assignee is not the same as the submittor
            # Email subect and body format are handled by templates
            if "notify" in request.POST :
                if new_task.assigned_to != request.user :
                                        
                    # Send email
                    email_subject = render_to_string("todo/email/assigned_subject.txt", { 'task': new_task })                    
                    email_body = render_to_string("todo/email/assigned_body.txt", { 'task': new_task, 'site': current_site, })
                    try:
                        send_mail(email_subject, email_body, new_task.created_by.email, [new_task.assigned_to.email], fail_silently=False)
                    except:
                        messages.error(request, "Task saved but mail not sent. Contact your administrator.")
                        

            messages.success(request, "New task \"%s\" has been added." % new_task.title)                       
            
            return HttpResponseRedirect(request.path)

    else:
        if list_slug != "mine" and list_slug != "recent-add" and list_slug != "recent-complete" : # We don't allow adding a task on the "mine" view
            form = AddItemForm(list, initial={
                'assigned_to':request.user.id,
                'priority':999,
                } )

    if request.user.is_staff:
        can_del = 1

    return render_to_response('todo/view_list.html', locals(), context_instance=RequestContext(request))


@user_passes_test(check_user_allowed)
def view_task(request,task_id):

    """
    View task details. Allow task details to be edited.
    """

    task = get_object_or_404(Item, pk=task_id)
    comment_list = Comment.objects.filter(task=task_id)
        
    # Before doing anything, make sure the accessing user has permission to view this item.
    # Determine the group this task belongs to, and check whether current user is a member of that group.
    # Admins can edit all tasks.

    if task.list.group in request.user.groups.all() or request.user.is_staff:
        
        auth_ok = 1
        if request.POST:
             form = EditItemForm(request.POST,instance=task)

             if form.is_valid():
                 form.save()
                 
                 # Also save submitted comment, if non-empty
                 if request.POST['comment-body']:
                     c = Comment(
                         author=request.user, 
                         task=task,
                         body=request.POST['comment-body'],
                     )
                     c.save()
                    
                     # And email comment to all people who have participated in this thread.
                     email_subject = render_to_string("todo/email/assigned_subject.txt", { 'task': task })                    
                     email_body = render_to_string("todo/email/newcomment_body.txt", { 'task': task, 'body':request.POST['comment-body'], 'site': current_site, 'user':request.user })

                     # Get list of all thread participants - task creator plus everyone who has commented on it.
                     recip_list = []
                     recip_list.append(task.created_by.email)
                     commenters = Comment.objects.filter(task=task)
                     for c in commenters:
                         recip_list.append(c.author.email)
                     # Eliminate duplicate emails with the Python set() function
                     recip_list = set(recip_list)     
                     
                     # Send message
                     try:
                        send_mail(email_subject, email_body, task.created_by.email, recip_list, fail_silently=False)
                        messages.success(request, "Comment sent to thread participants.")                       
                        
                     except:
                        messages.error(request, "Comment saved but mail not sent. Contact your administrator.")
                    
                 
                 messages.success(request, "The task has been edited.")
                 
                 return HttpResponseRedirect(reverse('todo-incomplete_tasks', args=[task.list.id, task.list.slug]))
                 
        else:
            form = EditItemForm(instance=task)
            if task.due_date:
                thedate = task.due_date
            else:
                thedate = datetime.datetime.now()
            

    else:
        messages.info(request, "You do not have permission to view/edit this task.")
        

    return render_to_response('todo/view_task.html', locals(), context_instance=RequestContext(request))


@csrf_exempt
@user_passes_test(check_user_allowed)
def reorder_tasks(request):
    """
    Handle task re-ordering (priorities) from JQuery drag/drop in view_list.html
    """

    newtasklist = request.POST.getlist('tasktable[]')
    # First item in received list is always empty - remove it
    del newtasklist[0]
    
    # Items arrive in order, so all we need to do is increment up from one, saving
    # "i" as the new priority for the current object.
    i = 1
    for t in newtasklist:
        newitem = Item.objects.get(pk=t)
        newitem.priority = i
        newitem.save()
        i = i + 1
    
    # All views must return an httpresponse of some kind ... without this we get 
    # error 500s in the log even though things look peachy in the browser.    
    return HttpResponse(status=201)
        
    
@user_passes_test(check_user_allowed)
def external_add(request):
    """
    Allow users who don't have access to the rest of the ticket system to file a ticket in a specific list.
    This is useful if, for example, a core web team are in a group that can file todos for each other,
    but you also want students to be able to post trouble tickets to a list just for the sysadmin. This
    way we don't have to put all students into a group that gives them access to the whole ticket system.
    """
    if request.POST:
            form = AddExternalItemForm(request.POST)

            if form.is_valid():
                # Don't commit the save until we've added in the fields we need to set
                item = form.save(commit=False)
                item.list_id = 20 # Hate hard-coding in IDs like this.
                item.created_by = request.user
                item.assigned_to = User.objects.get(username='roy_baril')
                item.save()
                
                # Send email
                email_subject = render_to_string("todo/email/assigned_subject.txt", { 'task': item.title })                    
                email_body = render_to_string("todo/email/assigned_body.txt", { 'task': item, 'site': current_site, })
                try:
                    send_mail(email_subject, email_body, item.created_by.email, [item.assigned_to.email], fail_silently=False)
                except:
                    messages.error(request, "Task saved but mail not sent. Contact your administrator." )                    

                messages.success(request, "Your trouble ticket has been submitted. We'll get back to you soon." )                    
                
                return HttpResponseRedirect(reverse('intranet_home'))
            
        
    else:
        form = AddExternalItemForm()

    return render_to_response('todo/add_external_task.html', locals(), context_instance=RequestContext(request))



@user_passes_test(check_user_allowed)
def add_list(request):
    """
    Allow users to add a new todo list to the group they're in.
    """
    
    if request.POST:    
        form = AddListForm(request.user,request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "A new list has been added." )                                    
                return HttpResponseRedirect(request.path)
            except IntegrityError:
                messages.error(request, "There was a problem saving the new list. Most likely a list with the same name in the same group already exists." )
                
            
    else:
        form = AddListForm(request.user)
        
    return render_to_response('todo/add_list.html', locals(), context_instance=RequestContext(request))


  

@user_passes_test(check_user_allowed)
def search(request):
    """
    Search for tasks
    """

    if request.GET:    

        query_string = ''
        found_items = None
        if ('q' in request.GET) and request.GET['q'].strip():
            query_string = request.GET['q']

            found_items = Item.objects.filter(
                Q(title__icontains=query_string) |
                Q(note__icontains=query_string) 
            )
        else:

            # What if they selected the "completed" toggle but didn't type in a query string?
            # In that case we still need found_items in a queryset so it can be "excluded" below.
            found_items = Item.objects.all()    
        
        if request.GET['inc_complete'] == "0" :
            found_items = found_items.exclude(completed=True)
            
    else :
        query_string = None
        found_items = None

    return render_to_response('todo/search_results.html',
                          { 'query_string': query_string, 'found_items': found_items },
                          context_instance=RequestContext(request))


########NEW FILE########
