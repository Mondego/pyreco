__FILENAME__ = config
#!/usr/bin/python2.7
#
# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Configuration options for the application.

  OAuth 2.0 Client Settings:
    Visit the APIs Console (https://code.google.com/apis/console/) to create or
    obtain client details for a project.
    Authorized Redirect URIs for your client should include the hostname of your
    app with /admin/auth appended to the end.
    e.g. http://example.appspot.com/admin/auth

  XSRF Settings:
    This is used to generate a unique key for each user of the app.
    Replace this with a unique phrase or random set of characters.
    Keep this a secret.
"""

__author__ = 'pete.frisella@gmail.com (Pete Frisella)'

# OAuth 2.0 Client Settings
AUTH_CONFIG = {
    'OAUTH_CLIENT_ID': 'REPLACE THIS WITH YOUR CLIENT ID',
    'OAUTH_CLIENT_SECRET': 'REPLACE THIS WITH YOUR CLIENT SECRET',

    # E.g. Local Dev Env on port 8080: http://localhost:8080
    # E.g. Hosted on App Engine: https://your-application-id.appspot.com
    'OAUTH_REDIRECT_URI': '%s%s' % (
        'https://REPLACE_THIS_WITH_YOUR_APPLICATION_NAME.appspot.com OR http://localhost:8080',
        '/admin/auth')
}

# XSRF Settings
XSRF_KEY = 'REPLACE THIS WITH A SECRET PHRASE THAT SHOULD NOT BE SHARED'

########NEW FILE########
__FILENAME__ = admin
#!/usr/bin/python2.7
#
# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Handles all Admin requests to the Google Analytics Proxy.

These handlers are only available for actions performed by administrators. This
is configured in app.yaml. Addtional logic is provided by utility functions.

  AddUserHandler: Allows admins to view and grant users access to the app.
  QueryTaskWorker: Executes API Query tasks from the task queue
"""

__author__ = 'pete.frisella@gmail.com (Pete Frisella)'

from controllers import base
from controllers.util import co
from controllers.util import query_helper
from controllers.util import users_helper
import webapp2


class AddUserHandler(base.BaseHandler):
  """Handles viewing and adding users of the to the service."""

  def get(self):
    template_values = {
        'users': users_helper.ListUsers(),
        'invitations': users_helper.ListInvitations(),
        'activate_link': self.request.host_url + co.LINKS['owner_activate'],
        'LINKS': co.LINKS
    }
    self.RenderHtmlTemplate('users.html', template_values)

  def post(self):
    """Handles HTTP POSTS requests to add a user.

    Users can be added by email address only.
    """
    email = self.request.get('email')
    users_helper.AddInvitation(email)
    self.redirect(co.LINKS['admin_users'])


class QueryTaskWorker(base.BaseHandler):
  """Handles API Query requests and responses from the task queue."""

  def post(self):
    query_id = self.request.get('query_id')
    api_query = query_helper.GetApiQuery(query_id)
    query_helper.ExecuteApiQueryTask(api_query)


app = webapp2.WSGIApplication(
    [(co.LINKS['admin_users'], AddUserHandler),
     (co.LINKS['admin_runtask'], QueryTaskWorker)],
    debug=True)

########NEW FILE########
__FILENAME__ = base
#!/usr/bin/python2.7
#
# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""The base handlers used by public, owner, and admin handler scripts.

  BaseHandler: The base class for all other handlers to render content.
"""

__author__ = 'pete.frisella@gmail.com (Pete Frisella)'

import json
import os
import urllib

from controllers.util import co
from controllers.util import users_helper
import jinja2
import webapp2

from google.appengine.api import users

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(
        os.path.join(os.path.dirname(__file__), '..', 'templates')),
    autoescape=True)


class BaseHandler(webapp2.RequestHandler):
  """Base handler for generating responses for most types of requests."""

  def RenderHtmlTemplate(self, template_name, template_values=None):
    """Renders HTML using a template.

    Values that are common across most templates are automatically added and
    sent to the template.

    Args:
      template_name: The name of the template to render (e.g. 'admin.html')
      template_values: A dict of values to pass to the template.
    """
    if template_values is None:
      template_values = {}

    current_user = users.get_current_user()
    user_settings = None
    user_email = ''
    if current_user:
      user_settings = users_helper.GetGaSuperProxyUser(current_user.user_id())
      user_email = current_user.email()

    template_values.update({
        'user_settings': user_settings,
        'current_user_email': user_email,
        'is_admin': users.is_current_user_admin(),
        'logout_url': users.create_logout_url(co.LINKS['owner_index']),
        'LINKS': co.LINKS
    })
    self.response.headers['Content-Type'] = 'text/html; charset=UTF-8'
    self.response.headers['Content-Disposition'] = 'inline'
    self.response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    template = jinja_environment.get_template(template_name)
    self.response.write(template.render(template_values))

  def RenderCsv(self, csv_content, status=200):
    """Renders CSV content.

    Args:
      csv_content: The CSV content to output.
      status: The HTTP status code to send.
    """
    self.response.headers['Content-Type'] = 'text/csv; charset=UTF-8'
    self.response.headers['Content-Disposition'] = (
        'attachment; filename=query_response.csv')
    self.response.set_status(status)
    self.response.write(csv_content)

  def RenderHtml(self, html_content, status=200):
    """Renders HTML content.

    Args:
      html_content: The HTML content to output.
      status: The HTTP status code to send.
    """
    self.response.headers['Content-Type'] = 'text/html; charset=UTF-8'
    self.response.headers['Content-Disposition'] = 'inline'
    self.response.set_status(status)
    self.response.write(html_content)

  def RenderJson(self, json_response, status=200):
    """Renders JSON/Javascript content.

    If a callback parameter is included as part of the request then a
    Javascript function is output (JSONP support).

    Args:
      json_response: The JSON content to output.
      status: The HTTP status code to send.
    """
    self.response.set_status(status)
    self.response.headers['Content-Disposition'] = 'inline'
    if self.request.get('callback'):  # JSONP Support
      self.response.headers['Content-Type'] = (
          'application/javascript; charset=UTF-8')
      self.response.out.write('(%s)(%s);' %
                              (urllib.unquote(self.request.get('callback')),
                               json.dumps(json_response)))
    else:
      self.response.headers['Content-Type'] = 'application/json; charset=UTF-8'
      self.response.write(json.dumps(json_response))

  def RenderText(self, text, status=200):
    """Renders plain text content.

    Args:
      text: The plain text to output.
      status: The HTTP status code to send.
    """
    self.response.headers['Content-Type'] = 'text/plain; charset=UTF-8'
    self.response.headers['Content-Disposition'] = 'inline'
    self.response.set_status(status)
    self.response.write(text)

  def RenderTsv(self, tsv_content, status=200):
    """Renders TSV for Excel content.

    Args:
      tsv_content: The TSV for Excel content to output.
      status: The HTTP status code to send.
    """
    self.response.headers['Content-Type'] = ('application/vnd.ms-excel; '
                                             'charset=UTF-16LE')
    self.response.headers['Content-Disposition'] = (
        'attachment; filename=query_response.tsv')
    self.response.set_status(status)
    self.response.write(tsv_content)

########NEW FILE########
__FILENAME__ = owner
#!/usr/bin/python2.7
#
# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Handles all Owner requests to the Google Analytics superProxy.

  These handlers are available for actions performed by owners that can manage
  API Queries. This is configured in app.yaml. Additional logic is provided by
  utility functions.

  ActivateUserHandler: Activates new users.
  AdminHandler: Handles the admin home page for owners.
  AuthHandler: Handles OAuth 2.0 flow and storing auth tokens for the owner.
  ChangeQueryStatusHandler: Disables/enables public endpoints for queries.
  CreateQueryHandler: Handles creating new API Queries.
  DeleteQueryHandler: Deletes an API Query and related entities.
  DeleteQueryErrorsHandler: Deletes API query error responses.
  EditQueryHandler: Handles requests to edit an API Query.
  ManageQueryHandler: Provides the status and management operations for an
                      API Query.
  RunQueryHandler: Handles adhoc refresh requests from owners.
  ScheduleQueryHandler: Handles API Query scheduling.
"""

__author__ = 'pete.frisella@gmail.com (Pete Frisella)'

from controllers import base
from controllers.util import access_control
from controllers.util import analytics_auth_helper
from controllers.util import co
from controllers.util import query_helper
from controllers.util import schedule_helper
from controllers.util import template_helper
from controllers.util import users_helper
import webapp2

from google.appengine.api import users


class ActivateUserHandler(base.BaseHandler):
  """Handles the activation of a new user."""

  def get(self):
    """Handles user activations."""
    user = users.get_current_user()

    if users_helper.GetGaSuperProxyUser(user.user_id()):
      self.redirect(co.LINKS['owner_index'])
      return

    if not users_helper.GetInvitation(user.email().lower()):
      self.redirect(co.LINKS['public_index'])

    template_values = {
        'xsrf_token': access_control.GetXsrfToken()
    }
    self.RenderHtmlTemplate('activate.html', template_values)

  @access_control.ValidXsrfTokenRequired
  def post(self):
    """Activates and adds a user to the service."""
    users_helper.ActivateUser()
    self.redirect(co.LINKS['owner_index'])


class AdminHandler(base.BaseHandler):
  """Handler for the Admin panel to list all API Queries."""

  @access_control.ActiveGaSuperProxyUser
  def get(self):
    """Displays a list of API Queries.

    Only the user's API Queries are shown unless the user is an administrator.
    Administrators can also filter the list to only show queries they own.
    """
    query_filter = self.request.get('filter')

    if users.is_current_user_admin() and query_filter != 'owner':
      user = None
    else:
      user = users_helper.GetGaSuperProxyUser(
          users.get_current_user().user_id())

    api_queries = query_helper.ListApiQueries(user)
    hostname = self.request.host_url
    template_values = {
        'api_queries': template_helper.GetTemplateValuesForAdmin(api_queries,
                                                                 hostname),
        'query_error_limit': co.QUERY_ERROR_LIMIT,
        'revoke_token_url': '%s?revoke=true' % co.LINKS['owner_auth'],
        'oauth_url': analytics_auth_helper.OAUTH_URL
    }
    self.RenderHtmlTemplate('admin.html', template_values)


class AuthHandler(base.BaseHandler):
  """Handles OAuth 2.0 responses and requests."""

  @access_control.ActiveGaSuperProxyUser
  def get(self):
    template_values = analytics_auth_helper.OAuthHandler(self.request)
    self.RenderHtmlTemplate('auth.html', template_values)


class ChangeQueryStatusHandler(base.BaseHandler):
  """Handles requests to change the endpoint status of an API Query."""

  @access_control.OwnerRestricted
  @access_control.ValidXsrfTokenRequired
  @access_control.ActiveGaSuperProxyUser
  def post(self):
    """Change the public endpoint status of an API Query."""
    query_id = self.request.get('query_id')
    redirect = self.request.get('redirect', co.LINKS['owner_index'])

    api_query = query_helper.GetApiQuery(query_id)
    query_helper.SetPublicEndpointStatus(api_query)
    self.redirect(redirect)


class CreateQueryHandler(base.BaseHandler):
  """Handles the creation of API Queries.

    This handles 3 cases, testing a query, saving a new query, and saving and
    automatically scheduling a new query.
  """

  @access_control.ActiveGaSuperProxyUser
  def get(self):
    """Displays the create query form."""
    template_values = {
        'timezone': co.TIMEZONE,
        'xsrf_token': access_control.GetXsrfToken()
    }
    self.RenderHtmlTemplate('create.html', template_values)

  @access_control.ValidXsrfTokenRequired
  @access_control.ActiveGaSuperProxyUser
  def post(self):
    """Validates and tests/saves the API Query to the datastore.

    The owner can do any of the following from the create form:
    testing: It will render the create form and show test results.
    save: It will save the query to the datastore.
    save and schedule: It will save the query to the datastore and enable
                       scheduling for the query.
    """
    query_form_input = {
        'name': self.request.get('name'),
        'request': self.request.get('request'),
        'refresh_interval': self.request.get('refresh_interval')
    }

    query_form_input = query_helper.ValidateApiQuery(query_form_input)

    if not query_form_input:
      self.redirect(co.LINKS['owner_index'])

    api_query = query_helper.BuildApiQuery(**query_form_input)

    if self.request.get('test_query'):
      test_response = query_helper.FetchApiQueryResponse(api_query)

      template_values = {
          'test_response': test_response,
          'name': api_query.name,
          'request': api_query.request,
          'refresh_interval': api_query.refresh_interval,
          'timezone': co.TIMEZONE,
          'xsrf_token': access_control.GetXsrfToken()
      }

      self.RenderHtmlTemplate('create.html', template_values)
      return

    elif self.request.get('create_query'):
      query_helper.SaveApiQuery(api_query)

    elif self.request.get('create_run_query'):
      query_helper.ScheduleAndSaveApiQuery(api_query)

    api_query_links = template_helper.GetLinksForTemplate(
        api_query, self.request.host_url)
    self.redirect(api_query_links.get('manage_link', '/'))


class DeleteQueryHandler(base.BaseHandler):
  """Handles requests to delete an API Query."""

  @access_control.OwnerRestricted
  @access_control.ValidXsrfTokenRequired
  @access_control.ActiveGaSuperProxyUser
  def post(self):
    """Delete an API Query and any child API Query (Error) Responses."""
    query_id = self.request.get('query_id')
    redirect = self.request.get('redirect', co.LINKS['owner_index'])
    api_query = query_helper.GetApiQuery(query_id)

    query_helper.DeleteApiQuery(api_query)

    self.redirect(redirect)


class DeleteQueryErrorsHandler(base.BaseHandler):
  """Handles requests to delete API Query Error Responses."""

  @access_control.OwnerRestricted
  @access_control.ValidXsrfTokenRequired
  @access_control.ActiveGaSuperProxyUser
  def post(self):
    """Delete API query error responses."""
    query_id = self.request.get('query_id')
    redirect = self.request.get('redirect', co.LINKS['owner_index'])
    api_query = query_helper.GetApiQuery(query_id)

    query_helper.DeleteApiQueryErrors(api_query)
    schedule_helper.ScheduleApiQuery(api_query, randomize=True, countdown=0)
    self.redirect(redirect)


class EditQueryHandler(base.BaseHandler):
  """Handles requests to edit an API Query."""

  @access_control.ValidXsrfTokenRequired
  @access_control.ActiveGaSuperProxyUser
  def post(self):
    """Validates and tests/saves the API Query to the datastore.

    The owner can do any of the following from the edit form:
    testing: It will render the create form and show test results.
    save: It will save the query to the datastore.
    save and refresh: It will save the query, fetch the lastest data and then
      save both to the datastore.
    """
    query_id = self.request.get('query_id')
    api_query = query_helper.GetApiQuery(query_id)

    if not api_query:
      self.redirect(co.LINKS['owner_index'])

    query_form_input = {
        'name': self.request.get('name'),
        'request': self.request.get('request'),
        'refresh_interval': self.request.get('refresh_interval')
    }
    query_form_input = query_helper.ValidateApiQuery(query_form_input)

    hostname = self.request.host_url
    api_query_links = template_helper.GetLinksForTemplate(api_query, hostname)

    if not query_form_input:
      self.redirect(api_query_links.get('manage_link', '/'))

    api_query.name = query_form_input.get('name')
    api_query.request = query_form_input.get('request')
    api_query.refresh_interval = query_form_input.get('refresh_interval')

    if self.request.get('test_query'):
      test_response = query_helper.FetchApiQueryResponse(api_query)

      template_values = {
          'test_response': test_response,
          'api_query': template_helper.GetTemplateValuesForManage(api_query,
                                                                  hostname),
          'timezone': co.TIMEZONE,
          'xsrf_token': access_control.GetXsrfToken()
      }
      self.RenderHtmlTemplate('edit.html', template_values)
      return

    elif self.request.get('save_query'):
      query_helper.SaveApiQuery(api_query)
    elif self.request.get('save_query_refresh'):
      query_helper.SaveApiQuery(api_query)
      query_helper.RefreshApiQueryResponse(api_query)

    self.redirect(api_query_links.get('manage_link', '/'))


class ManageQueryHandler(base.BaseHandler):
  """Handles requests to view and manage API Queries."""

  @access_control.OwnerRestricted
  @access_control.ActiveGaSuperProxyUser
  def get(self):
    """Retrieves a query to be managed by the user."""
    query_id = self.request.get('query_id')
    api_query = query_helper.GetApiQuery(query_id)

    if api_query:
      hostname = self.request.host_url
      template_values = {
          'api_query': template_helper.GetTemplateValuesForManage(api_query,
                                                                  hostname),
          'timezone': co.TIMEZONE,
          'xsrf_token': access_control.GetXsrfToken()
      }

      if self.request.get('action') == 'edit':
        self.RenderHtmlTemplate('edit.html', template_values)
        return

      self.RenderHtmlTemplate('view.html', template_values)
      return

    self.redirect(co.LINKS['owner_index'])


class RunQueryHandler(base.BaseHandler):
  """Handles a single query execution request.

  This handles adhoc requests by owners to Refresh an API Query.
  """

  @access_control.OwnerRestricted
  @access_control.ValidXsrfTokenRequired
  @access_control.ActiveGaSuperProxyUser
  def post(self):
    """Refreshes the API Query Response."""
    query_id = self.request.get('query_id')
    api_query = query_helper.GetApiQuery(query_id)

    if api_query:
      query_helper.RefreshApiQueryResponse(api_query)
      api_query_links = template_helper.GetLinksForTemplate(
          api_query, self.request.host_url)
      self.redirect(api_query_links.get('manage_link', '/'))
      return

    self.redirect(co.LINKS['owner_index'])


class ScheduleQueryHandler(base.BaseHandler):
  """Handles the scheduling of API Queries. Starting and stopping."""

  @access_control.OwnerRestricted
  @access_control.ValidXsrfTokenRequired
  @access_control.ActiveGaSuperProxyUser
  def post(self):
    """Starts/Stops API Query Scheduling."""
    query_id = self.request.get('query_id')
    api_query = query_helper.GetApiQuery(query_id)

    if api_query:
      schedule_helper.SetApiQueryScheduleStatus(api_query)
      schedule_helper.ScheduleApiQuery(api_query, randomize=True, countdown=0)
      api_query_links = template_helper.GetLinksForTemplate(
          api_query, self.request.host_url)
      self.redirect(api_query_links.get('manage_link', '/'))
      return

    self.redirect(co.LINKS['owner_index'])


app = webapp2.WSGIApplication(
    [(co.LINKS['owner_index'], AdminHandler),
     (co.LINKS['query_manage'], ManageQueryHandler),
     (co.LINKS['query_edit'], EditQueryHandler),
     (co.LINKS['query_delete'], DeleteQueryHandler),
     (co.LINKS['query_delete_errors'], DeleteQueryErrorsHandler),
     (co.LINKS['query_create'], CreateQueryHandler),
     (co.LINKS['query_status_change'], ChangeQueryStatusHandler),
     (co.LINKS['query_run'], RunQueryHandler),
     (co.LINKS['query_schedule'], ScheduleQueryHandler),
     (co.LINKS['owner_auth'], AuthHandler),
     (co.LINKS['owner_activate'], ActivateUserHandler),
     (co.LINKS['owner_default'], AdminHandler)],
    debug=True)

########NEW FILE########
__FILENAME__ = public
#!/usr/bin/python2.7
#
# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Handles all public requests to the Google Analytics superProxy.

These handlers are for actions performed by external users that may or may not
be signed in. This is configured in app.yaml. Additional logic is provided by
utility functions.

  PublicQueryResponseHandler: Outputs the API response for the requested query.
  NotAuthorizedHandler: Handles unauthorized requests.
"""

__author__ = 'pete.frisella@gmail.com (Pete Frisella)'

from controllers import base
from controllers.transform import transformers
from controllers.util import co
from controllers.util import errors
from controllers.util import query_helper
import webapp2


class PublicQueryResponseHandler(base.BaseHandler):
  """Handles public requests for an API Query response.

  The handler retrieves the latest response for the requested API Query Id
  and format (if specified) and renders the response or an error message if
  a response was not found.
  """

  def get(self):
    """Renders the API Response in the format requested.

    Gets the public response and then uses the transformer to render the
    content. If there is an error then the error message will be rendered
    using the default response format.
    """
    query_id = self.request.get('id')
    response_format = str(self.request.get('format', co.DEFAULT_FORMAT))

    # The tqx parameter is required for Data Table Response requests. If it
    # exists then pass the value on to the Transform.
    tqx = self.request.get('tqx', None)

    transform = transformers.GetTransform(response_format, tqx)

    try:
      (content, status) = query_helper.GetPublicEndpointResponse(
          query_id, response_format, transform)
    except errors.GaSuperProxyHttpError, proxy_error:
      # For error responses use the transform of the default format.
      transform = transformers.GetTransform(co.DEFAULT_FORMAT)
      content = proxy_error.content
      status = proxy_error.status

    transform.Render(self, content, status)


class NotAuthorizedHandler(base.BaseHandler):
  """Handles unauthorized public requests to owner/admin pages."""

  def get(self):
    self.RenderHtmlTemplate('public.html')


app = webapp2.WSGIApplication(
    [(co.LINKS['public_query'], PublicQueryResponseHandler),
     (co.LINKS['public_default'], NotAuthorizedHandler)],
    debug=True)

########NEW FILE########
__FILENAME__ = transformers
#!/usr/bin/python2.7
#
# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utility module to Transform GA API responses to different formats.

  Transforms a JSON response from the Google Analytics Core Reporting API V3.
  Responses can be anonymized, transformed, and returned in a new format.
  For example: CSV, TSV, Data Table, etc.

  GetTransform: Returns a transform for the requested format.
  TransformJson: Transform and render a Core Reporting API response as JSON.
  TransformCsv: Transform and render a Core Reporting API response as CSV.
  TransformDataTableString: Transform and render a Core Reporting API response
      as a Data Table string.
  TransformDataTableResponse: Transform and render a Core Reporting API response
      as a Data Table response.
  TransformTsv: Transform and render a Core Reporting API response as TSV.
  RemoveKeys: Removes key/value pairs from a JSON response.
  GetDataTableSchema: Get a Data Table schema from Core Reporting API Response.
  GetDataTableRows: Get Data Table rows from Core Reporting API Response.
  GetDataTable: Returns a Data Table using the Gviz library
  GetColumnOrder: Converts API Response column headers to columns for Gviz.
"""

__author__ = 'pete.frisella@gmail.com (Pete Frisella)'

import cStringIO
import urllib

from libs.csv_writer import csv_writer
from libs.gviz_api import gviz_api

# The label to use for unknown data types.
UNKNOWN_LABEL = 'UNKNOWN'

# Maps the types used in a Core Reporting API response to Python types.
BUILTIN_DATA_TYPES = {
    'STRING': str,
    'INTEGER': int,
    'FLOAT': float,
    'CURRENCY': float,
    UNKNOWN_LABEL: str
}

# Maps the types used in a Core Reporting API response to JavaScript types.
JS_DATA_TYPES = {
    'STRING': 'string',
    'INTEGER': 'number',
    'FLOAT': 'number',
    'CURRENCY': 'number',
    UNKNOWN_LABEL: 'string'
}


# List of properties to remove from the response when Anonymized.
# Paths to sub-properties in a nested dict can be separated with a
# colon. e.g. 'query:ids' will remove ids property from parent property query.
PRIVATE_PROPERTIES = ('id', 'query:ids', 'selfLink', 'nextLink', 'profileInfo')


def GetTransform(response_format='json', tqx=None):
  """Returns a transform based on the requested format.

  Args:
    response_format: A string indicating the type of transform to get.
    tqx: string tqx is a standard parameter for the Chart Tools Datasource
      Protocol V0.6. If it exists then we must handle it. In this case it will
      get passed to the Data Table Response transform.

  Returns:
    A transform instance for the requested format type or a default transform
    instance if an invalid response format is requested.
  """
  if response_format == 'json':
    transform = TransformJson()
  elif response_format == 'csv':
    output = cStringIO.StringIO()
    writer = csv_writer.GetCsvStringPrinter(output)
    transform = TransformCsv(writer, output)
  elif response_format == 'data-table':
    transform = TransformDataTableString()
  elif response_format == 'data-table-response':
    transform = TransformDataTableResponse(tqx)
  elif response_format == 'tsv':
    output = cStringIO.StringIO()
    writer = csv_writer.GetTsvStringPrinter(output)
    transform = TransformTsv(writer, output)
  else:
    transform = TransformJson()

  return transform


class TransformJson(object):
  """A transform to render a Core Reporting API response as JSON."""

  def Transform(self, content):
    """Transforms a Core Reporting API Response to JSON.

    Although this method simply returns the original argument it is needed to
    maintain a consistent interface for all transforms.

    Args:
      content: A dict representing the Core Reporting API JSON response to
               transform.

    Returns:
      A dict, the original Core Reporting API Response.
    """
    return content

  def Render(self, webapp, content, status):
    """Renders a Core Reporting API response in JSON.

    Args:
      webapp: The webapp2 object to use to render the response.
      content: A dict representing the JSON content to render.
      status: An integer representing the HTTP status code to send.
    """
    webapp.RenderJson(content, status)


class TransformCsv(object):
  """A transform to render a Core Reporting API response as CSV."""

  def __init__(self, writer, output):
    """Initialize the CSV Transform.

    Args:
      writer: The CSV Writer object to use for the transform.
      output: The CStringIO object to write the transformed content to.
    """
    self.writer = writer
    self.output = output

  def Transform(self, content):
    """Transforms the columns and rows from the API JSON response to CSV.

    Args:
      content: A dict representing the Core Reporting API JSON response to
               transform.

    Returns:
      A string of either a CSV formatted response with a header or empty if no
      rows existed in the content to transform.

    Raises:
      AttributeError: Invalid JSON response content was provided.
    """
    csv_output = ''
    if content:
      column_headers = content.get('columnHeaders', [])
      rows = content.get('rows', [])

      if column_headers:
        self.writer.OutputHeaders(content)

      if rows:
        self.writer.OutputRows(content)

      csv_output = self.output.getvalue()
      self.output.close()

    return csv_output

  def Render(self, webapp, content, status):
    """Renders a Core Reporting API response as CSV.

    Args:
      webapp: The webapp2 object to use to render the response.
      content: A dict representing the JSON content to render.
      status: An integer representing the HTTP status code to send.
    """
    webapp.RenderCsv(content, status)


class TransformDataTableString(object):
  """A transform to render a Core Reporting API response as a Data Table."""

  def Transform(self, content):
    """Transforms a Core Reporting API response to a DataTable JSON String.

    DataTable
    https://developers.google.com/chart/interactive/docs/reference#DataTable

    JSON string -- If you are hosting the page that hosts the visualization that
    uses your data, you can generate a JSON string to pass into a DataTable
    constructor to populate it.
    From: https://developers.google.com/chart/interactive/docs/dev/gviz_api_lib

    Args:
      content: A dict representing the Core Reporting API JSON response to
               transform.

    Returns:
      None if no content is provided, an empty string if a Data Table isn't
      supported for the given content, or a Data Table as a JSON String.

    Raises:
      AttributeError: Invalid JSON response content was provided.
    """
    if not content:
      return None

    column_headers = content.get('columnHeaders')
    rows = content.get('rows')
    if column_headers and rows:
      data_table_schema = GetDataTableSchema(content)
      data_table_rows = GetDataTableRows(content)

      data_table_output = GetDataTable(data_table_schema, data_table_rows)

      if data_table_output:
        return data_table_output.ToJSon()
    return ''

  def Render(self, webapp, content, status):
    """Renders a Core Reporting API response as a Data Table String.

    Args:
      webapp: The webapp2 object to use to render the response.
      content: A dict representing the JSON content to render.
      status: An integer representing the HTTP status code to send.
    """
    webapp.RenderText(content, status)


class TransformDataTableResponse(object):
  """A transform to render a Core Reporting API response as a Data Table."""

  def __init__(self, tqx=None):
    """Initialize the Data Table Response Transform.

    Args:
      tqx: string A set of colon-delimited key/value pairs for standard or
        custom parameters. Pairs are separated by semicolons.
        (https://developers.google.com/chart/interactive/docs/dev/
          implementing_data_source#requestformat)
    """
    if tqx:
      tqx = urllib.unquote(tqx)
    self.tqx = tqx

  def Transform(self, content):
    """Transforms a Core Reporting API response to a DataTable JSON Response.

    DataTable
    https://developers.google.com/chart/interactive/docs/reference#DataTable

    JSON response -- If you do not host the page that hosts the visualization,
    and just want to act as a data source for external visualizations, you can
    create a complete JSON response string that can be returned in response to a
    data request.
    From: https://developers.google.com/chart/interactive/docs/dev/gviz_api_lib

    Args:
      content: A dict representing the Core Reporting API JSON response to
               transform.

    Returns:
      None if no content is provided, an empty string if a Data Table isn't
      supported for the given content, or a Data Table Response as JSON.

    Raises:
      AttributeError: Invalid JSON response content was provided.
    """
    if not content:
      return None

    column_headers = content.get('columnHeaders')
    rows = content.get('rows')
    if column_headers and rows:
      data_table_schema = GetDataTableSchema(content)
      data_table_rows = GetDataTableRows(content)
      data_table_output = GetDataTable(data_table_schema, data_table_rows)

      column_order = GetColumnOrder(column_headers)

      if data_table_output:
        req_id = 0
        # If tqx exists then handle at a minimum the reqId parameter
        if self.tqx:
          tqx_pairs = {}
          try:
            tqx_pairs = dict(pair.split(':') for pair in self.tqx.split(';'))
          except ValueError:
            # if the parse fails then just continue and use the empty dict
            pass
          req_id = tqx_pairs.get('reqId', 0)

        return data_table_output.ToJSonResponse(
            columns_order=column_order, req_id=req_id)
    return ''

  def Render(self, webapp, content, status):
    """Renders a Core Reporting API response as a Data Table Response.

    Args:
      webapp: The webapp2 object to use to render the response.
      content: A dict representing the JSON content to render.
      status: An integer representing the HTTP status code to send.
    """
    webapp.RenderText(content, status)


class TransformTsv(object):
  """A transform to render a Core Reporting API response as TSV."""

  def __init__(self, writer, output):
    """Initialize the TSV Transform.

    Args:
      writer: The CSV Writer object to use for the transform.
      output: The CStringIO object to write the transformed content to.
    """
    self.writer = writer
    self.output = output

  def Transform(self, content):
    """Transforms the columns and rows from the API JSON response to TSV.

    An Excel TSV is UTF-16 encoded.

    Args:
      content: A dict representing the Core Reporting API JSON response to
               transform.

    Returns:
      A UTF-16 encoded string representing an Excel TSV formatted response with
      a header or an empty string if no rows exist in the content.

    Raises:
      AttributeError: Invalid JSON response content was provided.
    """
    tsv_output = ''
    if content:
      column_headers = content.get('columnHeaders', [])
      rows = content.get('rows', [])

      if column_headers:
        self.writer.OutputHeaders(content)

      if rows:
        self.writer.OutputRows(content)

      out = self.output.getvalue()
      # Get UTF-8 output
      decoding = out.decode('UTF-8')
      # and re-encode to UTF-16 for Excel TSV
      tsv_output = decoding.encode('UTF-16')
      self.output.close()

    return tsv_output

  def Render(self, webapp, content, status):
    """Renders a Core Reporting API response as Excel TSV.

    Args:
      webapp: The webapp2 object to use to render the response.
      content: A dict representing the JSON content to render.
      status: An integer representing the HTTP status code to send.
    """
    webapp.RenderTsv(content, status)


def RemoveKeys(content, keys_to_remove=PRIVATE_PROPERTIES):
  """Removes key/value pairs from a JSON response.

  By default this will remove key/value pairs related to account information
  for a Google Analytics Core Reporting API JSON response.

  To remove keys, a path for each key to delete is created and stored in a list.
  Using this list of paths, the content is then traversed until each key is
  found and deleted from the content. For example, to traverse the content to
  find a single key, the key path is reversed and then each "node" in the path
  is popped off and fetched from the content. The traversal continues until
  all "nodes" have been fetched. Then a deletion is attempted.

  The reversal of the path is required because key paths are defined in order
  from ancestor to descendant and a pop operation returns the last item in a
  list. Since content traversal needs to go from ancestor to descendants,
  reversing the path before traversal will place the parent/ancestor at the
  end of the list, making it the first node/key to find in the content.

  Args:
    content: A dict representing the Core Reporting API JSON response to
             remove keys from.
    keys_to_remove: A tuple representing the keys to remove from the content.
                    The hiearchy/paths to child keys should be separated with a
                    colon. e.g. 'query:ids' will remove the child key, ids, from
                    parent key query.

  Returns:
    The given dict with the specified keys removed.
  """
  if content and keys_to_remove:
    for key_to_remove in keys_to_remove:

      # This gives a list that defines the hierarchy/path of the key to remove.
      key_hierarchy = key_to_remove.split(':')

      # Reverse the path to get the correct traversal order.
      key_hierarchy.reverse()
      key = key_hierarchy.pop()
      child_content = content

      # Traverse through hierarchy to find the key to delete.
      while key_hierarchy and child_content:
        child_content = child_content.get(key)
        key = key_hierarchy.pop()

      try:
        del child_content[key]
      except (KeyError, NameError, TypeError):
        # If the key doesn't exist then it's already "removed" so just continue
        # and move on to the next key for removal.
        pass
  return content


def GetDataTableSchema(content, data_types=None):
  """Builds and returns a Data Table schema from a Core Reporting API Response.

  Args:
    content: A dict representing the Core Reporting API JSON response to build
             a schmea from.
    data_types: A dict that maps the expected data types in the content to
                the equivalent JavaScript types. e.g.:
                {
                    'STRING': 'string',
                    'INTEGER': 'number'
                }
  Returns:
    A dict that contains column header and data type information that can be
    used for a Data Table schema/description. Returns None if there are no
    column headers in the Core Reporting API Response.

  Raises:
    AttributeError: Invalid JSON response content was provided.
  """
  if not content:
    return None

  if data_types is None:
    data_types = JS_DATA_TYPES

  column_headers = content.get('columnHeaders')
  schema = None

  if column_headers:
    schema = {}
    for header in column_headers:
      name = header.get('name', UNKNOWN_LABEL).encode('UTF-8')
      data_type = header.get('dataType', UNKNOWN_LABEL)
      data_type = data_types.get(data_type, data_types.get(UNKNOWN_LABEL))
      schema.update({
          name: (data_type, name),
      })
  return schema


def GetDataTableRows(content, data_types=None):
  """Builds and returns Data Table rows from a Core Reporting API Response.

  Args:
    content: A dict representing the Core Reporting API JSON response to build
             the rows from.

    data_types: A dict that maps the expected data types in the content to
                the equivalent Python types. e.g.:
                {
                    'STRING': str,
                    'INTEGER': int,
                    'FLOAT': float
                }

  Returns:
    A list where each item is a dict representing one row of data in a Data
    Table. Returns None if there are no column headers in the Core Reporting
    API response.
  """
  if not content:
    return None

  if data_types is None:
    data_types = BUILTIN_DATA_TYPES

  column_headers = content.get('columnHeaders')
  data_table = None

  if column_headers:
    data_table = []
    for data in content.get('rows', []):
      data_row = {}
      for index, data in enumerate(data):
        data_type = column_headers[index].get('dataType')
        convert_to = data_types.get(data_type, data_types.get(UNKNOWN_LABEL))
        if convert_to:
          data_row_value = convert_to(data)
        else:
          data_row_value = data.encode('UTF-8')
        data_row.update({
            column_headers[index].get('name', UNKNOWN_LABEL): data_row_value
        })
      data_table.append(data_row)
  return data_table


def GetDataTable(table_schema, table_rows):
  """Returns a Data Table using the Gviz library.

  DataTable:
  https://developers.google.com/chart/interactive/docs/reference#DataTable

  Data Source Python Library:
  https://developers.google.com/chart/interactive/docs/dev/gviz_api_lib

  Args:
    table_schema: A dict that contains column header and data type information
                  for a Data Table.
    table_rows: A list where each item in the list is a dict representing one
                row of data in a Data Table. It should match the schema defined
                by the provided table_schema argument.

  Returns:
    A gviz_api.DataTable object or None if Data Table isn't supported for
    the arguments provided.
  """
  if not table_schema or not table_rows:
    return None

  data_table_output = gviz_api.DataTable(table_schema)
  data_table_output.LoadData(table_rows)

  return data_table_output


def GetColumnOrder(column_headers):
  """Converts GA API columns headers into a column order tuple used by Gviz.

  Args:
    column_headers: A list of dicts that represent Column Headers. Equivalent
                    to the response from the GA API.
                    e.g.
                       [
                          {
                              "name": string,
                              "columnType": string,
                              "dataType": string
                          }
                       ]

  Returns:
    A tuple with column order that matches column headers in the original
    GA API response or None if there are no column headers.

  Raises:
    TypeError: An invalid list was provided.
  """
  column_order = None
  if column_headers:
    column_order = []
    for column in column_headers:
      column_order.append(column.get('name'))
    column_order = tuple(column_order)
  return column_order

########NEW FILE########
__FILENAME__ = access_control
#!/usr/bin/python2.7
#
# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utility module to validate XSRF tokens."""

__author__ = 'nickski15@gmail.com (Nick Mihailovski)'
__author__ = 'pete.frisella@gmail.com (Pete Frisella)'

import hashlib
import hmac

import config
from controllers.util import query_helper
from controllers.util import users_helper

import co

from google.appengine.api import users


def OwnerRestricted(original_request):
  """Requires that the user owns the entity being accessed or is an admin.

    If the request isn't made by the owner of the API Query or an admin then
    they will be redirected to the owner index page.

  Args:
    original_request: The restricted request being made.

  Returns:
    The wrapped request.
  """
  def Wrapper(self, *args, **kwargs):
    query_id = self.request.get('query_id')
    owner_has_access = UserOwnsApiQuery(query_id)
    if owner_has_access or users.is_current_user_admin():
      return original_request(self, *args, **kwargs)
    else:
      self.redirect(co.LINKS['owner_index'])
      return

  return Wrapper


def ActiveGaSuperProxyUser(original_request):
  """Requires that this is a valid user of the app.

    If the request isn't made by an active Google Analytics superProxy user then
    they will be redirected to the public index page.

  Args:
    original_request: The restricted request being made.

  Returns:
    The wrapped request.
  """
  def Wrapper(self, *args, **kwargs):
    user = users_helper.GetGaSuperProxyUser(users.get_current_user().user_id())
    if user or users.is_current_user_admin():
      return original_request(self, *args, **kwargs)
    else:
      self.redirect(co.LINKS['public_index'])
      return

  return Wrapper


def GetXsrfToken():
  """Generate a signed token unique to this user.

  Returns:
    An XSRF token unique to the user.
  """
  token = None
  user = users.get_current_user()
  if user:
    mac = hmac.new(config.XSRF_KEY, user.user_id(), hashlib.sha256)
    token = mac.hexdigest()
  return token


def ValidXsrfTokenRequired(original_handler):
  """Require a valid XSRF token in the environment, or error.

    If the request doesn't include a valid XSRF token then they will be
    redirected to the public index page.

  Args:
    original_handler: The handler that requires XSRF validation.

  Returns:
    The wrapped handler.
  """
  def Handler(self, *args, **kwargs):
    if self.request.get('xsrf_token') == GetXsrfToken():
      return original_handler(self, *args, **kwargs)
    else:
      self.redirect(co.LINKS['public_index'])
      return

  Handler.__name__ = original_handler.__name__
  return Handler


def UserOwnsApiQuery(query_id):
  """Check if the currently logged in user owns the API Query.

  Args:
    query_id: The id of the API query.

  Returns:
    A boolean to indicate whether the logged in user owns the API Query.
  """
  user = users.get_current_user()
  api_query = query_helper.GetApiQuery(query_id)

  if user and user.user_id() and api_query:
    return user.user_id() == api_query.user.key().name()
  return False

########NEW FILE########
__FILENAME__ = analytics_auth_helper
#!/usr/bin/python2.7
#
# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utility functions to handle authentication for Google Analytics API.

  AuthorizeApiQuery: Decorating function to add an access token to request URL.
  FetchAccessToken: Gets a new access token using a refresh token.
  FetchCredentials: Makes requests to Google Accounts API.
  GetAccessTokenForApiQuery: Requests an access token for a given refresh token.
  GetOAuthCredentials: Exchanges a auth code for tokens.
  OAuthHandler: Handles incoming requests from the Google Accounts API.
  RevokeAuthTokensForUser: Revokes and deletes a user's auth tokens.
  RevokeOAuthCredentials: Revokes a refresh token.
  SaveAuthTokensForUser: Obtains and saves auth tokens for a user.
"""

__author__ = 'pete.frisella@gmail.com (Pete Frisella)'

import copy
from datetime import datetime
import json
import urllib

import config
from controllers.util import users_helper

from google.appengine.api import urlfetch
from google.appengine.api import users


# Configure with your APIs Console Project
OAUTH_CLIENT_ID = config.AUTH_CONFIG['OAUTH_CLIENT_ID']
OAUTH_CLIENT_SECRET = config.AUTH_CONFIG['OAUTH_CLIENT_SECRET']
OAUTH_REDIRECT_URI = config.AUTH_CONFIG['OAUTH_REDIRECT_URI']

OAUTH_ENDPOINT = 'https://accounts.google.com/o/oauth2/auth'
OAUTH_TOKEN_ENDPOINT = 'https://accounts.google.com/o/oauth2/token'
OAUTH_REVOKE_ENDPOINT = 'https://accounts.google.com/o/oauth2/revoke?token='
OAUTH_SCOPE = 'https://www.googleapis.com/auth/analytics.readonly'
OAUTH_ACCESS_TYPE = 'offline'
ISSUED_AUTH_TOKENS_WEB_URL = (
    'https://www.google.com/accounts/IssuedAuthSubTokens')

OAUTH_PARAMS = urllib.urlencode({
    'response_type': 'code',
    'client_id': OAUTH_CLIENT_ID,
    'redirect_uri': OAUTH_REDIRECT_URI,
    'scope': OAUTH_SCOPE,
    'access_type': OAUTH_ACCESS_TYPE
})

OAUTH_URL = '%s?%s' % (OAUTH_ENDPOINT, OAUTH_PARAMS)

AUTH_MESSAGES = {
    'codeError': ('Unable to obtain credentials. Visit %s to revoke any '
                  'existing tokens for this App and retry.' %
                  ISSUED_AUTH_TOKENS_WEB_URL),
    'codeSuccess': 'Successfully connected to Google Analytics.',
    'revokeError': ('There was an error while attempting to disconnect from '
                    'Google Analytics. Visit <a href="%s">My Account</a> to '
                    'revoke any existing tokens for this App and retry.' %
                    ISSUED_AUTH_TOKENS_WEB_URL),
    'revokeSuccess': 'Successfully disconnected from Google Analytics.',
    'badRequest': ('Unable to obtain credentials for Google Analytics '
                   'connection visit <a href="%s">My Account</a> to revoke any '
                   'existing tokens for this App and retry.' %
                   ISSUED_AUTH_TOKENS_WEB_URL)
}


def AuthorizeApiQuery(fn):
  """Decorator to retrieve an access token and append it to an API Query URL.

  Args:
    fn: The original function being wrapped.

  Returns:
    An API Query entity with an access token appended to request URL.
  """
  def Wrapper(api_query):
    """Returns the original function with an authorized API Query."""
    access_token = GetAccessTokenForApiQuery(api_query)
    query = api_query.request
    if access_token:
      query = ('%s&access_token=%s&gasp=1' % (
          urllib.unquote(api_query.request), access_token))

    # Leave original API Query untouched by returning a copy with
    # a valid access_token appended to the API request URL.
    new_api_query = copy.copy(api_query)
    new_api_query.request = query

    return fn(new_api_query)
  return Wrapper


def FetchAccessToken(refresh_token):
  """Gets a new access token using a refresh token.

  Args:
    refresh_token: The refresh token to use.

  Returns:
    A valid access token or None if query was unsuccessful.
  """
  auth_params = {
      'refresh_token': refresh_token,
      'client_id': OAUTH_CLIENT_ID,
      'client_secret': OAUTH_CLIENT_SECRET,
      'grant_type': 'refresh_token'
  }

  return FetchCredentials(auth_params)


def FetchCredentials(auth_params):
  """General utility to make fetch requests to OAuth Service.

  Args:
    auth_params: The OAuth parameters to use for the request.

  Returns:
    A dict with the response status code and content.
  """
  auth_status = {
      'status_code': 400
  }

  auth_payload = urllib.urlencode(auth_params)

  try:
    response = urlfetch.fetch(url=OAUTH_TOKEN_ENDPOINT,
                              payload=auth_payload,
                              method=urlfetch.POST,
                              headers={
                                  'Content-Type':
                                  'application/x-www-form-urlencoded'
                              })

    response_content = json.loads(response.content)

    if response.status_code == 200:
      auth_status['status_code'] = 200

    auth_status['content'] = response_content

  except (ValueError, TypeError, AttributeError, urlfetch.Error), e:
    auth_status['content'] = str(e)

  return auth_status


def GetAccessTokenForApiQuery(api_query):
  """Attempts to retrieve a valid access token for an API Query.

  First retrieves the stored access token for the owner of the API Query, if
  available. Checks if token has expired and refreshes token if required (and
  saves it) before returning the token.

  Args:
    api_query: The API Query for which to retrieve an access token.

  Returns:
    A valid access token if available or None.
  """
  user_settings = users_helper.GetGaSuperProxyUser(api_query.user.key().name())
  if user_settings.ga_refresh_token and user_settings.ga_access_token:

    access_token = user_settings.ga_access_token

    # Check for expired access_token
    if datetime.utcnow() > user_settings.ga_token_expiry:
      response = FetchAccessToken(user_settings.ga_refresh_token)
      if (response.get('status_code') == 200 and response.get('content')
          and response.get('content').get('access_token')):
        access_token = response.get('content').get('access_token')
        expires_in = int(response.get('content').get('expires_in', 0))

        users_helper.SetUserCredentials(api_query.user.key().name(),
                                        user_settings.ga_refresh_token,
                                        access_token,
                                        expires_in)
    return access_token
  return None


def GetOAuthCredentials(code):
  """Retrieves credentials from OAuth 2.0 service.

  Args:
    code: The authorization code from the auth server

  Returns:
    A dict indicating whether auth flow was a success and the auth
    server response.
  """
  auth_params = {
      'code': code,
      'client_id': OAUTH_CLIENT_ID,
      'client_secret': OAUTH_CLIENT_SECRET,
      'redirect_uri': OAUTH_REDIRECT_URI,
      'grant_type': 'authorization_code'
  }

  return FetchCredentials(auth_params)


def OAuthHandler(request):
  """Handles OAuth Responses from Google Accounts.

  The function can handle code, revoke, and error requests.

  Args:
    request: The request object for the incoming request from Google Accounts.

  Returns:
    A dict containing messages that can be used to display to a user to indicate
    the outcome of the auth task.
  """

  # Request to exchange auth code for refresh/access token
  if request.get('code'):
    code_response = SaveAuthTokensForUser(request.get('code'))
    if code_response.get('success'):
      auth_values = {
          'status': 'success',
          'message': AUTH_MESSAGES['codeSuccess'],
      }
    else:
      auth_values = {
          'status': 'error',
          'message': AUTH_MESSAGES['codeError'],
          'message_detail': code_response.get('message')
      }

  # Request to revoke an issued refresh/access token
  elif request.get('revoke'):
    revoked = RevokeAuthTokensForUser()
    if revoked:
      auth_values = {
          'status': 'success',
          'message': AUTH_MESSAGES['revokeSuccess']
      }
    else:
      auth_values = {
          'status': 'error',
          'message': AUTH_MESSAGES['revokeError']
      }

  # Error returned from OAuth service
  elif request.get('error'):
    auth_values = {
        'status': 'error',
        'message': AUTH_MESSAGES['badRequest'],
        'message_detail': request.get('error')
    }
  else:
    auth_values = {
        'status': 'error',
        'message': 'There was an error connecting to Google Analytics.',
        'message_detail': AUTH_MESSAGES['badRequest']
    }

  return auth_values


def RevokeAuthTokensForUser():
  """Revokes a user's auth tokens and removes them from the datastore.

  Returns:
    A boolean indicating whether the revoke was successfully.
  """
  user = users_helper.GetGaSuperProxyUser(users.get_current_user().user_id())

  if user and user.ga_refresh_token:
    RevokeOAuthCredentials(user.ga_refresh_token)
    users_helper.SetUserCredentials(users.get_current_user().user_id())
    return True
  return False


def RevokeOAuthCredentials(token):
  """Revokes an OAuth token.

  Args:
    token: A refresh or access token

  Returns:
    True if token successfully revoked, False otherwise
  """
  if token:
    revoke_url = OAUTH_REVOKE_ENDPOINT + token

    try:
      response = urlfetch.fetch(url=revoke_url)

      if response.status_code == 200:
        return True
    except urlfetch.Error:
      return False
  return False


def SaveAuthTokensForUser(code):
  """Exchanges an auth code for tokens and saves it to the datastore for a user.

  Args:
    code: The auth code from Google Accounts to exchange for tokens.

  Returns:
    A dict indicating whether the user's auth settings were successfully
    saved to the datastore and any messages returned from the service.
  """
  response = {
      'success': False
  }
  auth_response = GetOAuthCredentials(code)
  response_content = auth_response.get('content')

  if (auth_response.get('status_code') == 200
      and response_content
      and response_content.get('refresh_token')):

    refresh_token = response_content.get('refresh_token')
    access_token = response_content.get('access_token')

    users_helper.SetUserCredentials(
        users.get_current_user().user_id(),
        refresh_token, access_token)
    response['success'] = True
  else:
    response['message'] = response_content

  return response

########NEW FILE########
__FILENAME__ = co
#!/usr/bin/python2.7
#
# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Application settings/constants for the Google Analytics superProxy."""

__author__ = 'pete.frisella@gmail.com (Pete Frisella)'

# Determines if account info is removed from responses.
# Set to True to remove Google Analytics account info from public responses.
# TODO(pfrisella): Move this into an Admin Web UI.
ANONYMIZE_RESPONSES = False

# Determines which timezone relative dates will be resolved to.
# North American timezones are supported and UTC.
# Acceptable values are (case-insensitive):
#   atlantic, atc, adt, eastern, est, edt, central, cst, cdt, mountain, mst,
#   mdt, pacific, pst, pdt, utc
# TODO(pfrisella): Move this into an Admin Web UI.
TIMEZONE = 'pacific'

# A list of all supported formats for responses.
# The key represents the query paramter value to use to request a format.
# For example &format=csv will return a CSV response.
# The label key/value is the friendly name for this format. It is displayed
# in the Web UI.
DEFAULT_FORMAT = 'json'
SUPPORTED_FORMATS = {
    'json': {
        'label': 'JSON'
    },
    'csv': {
        'label': 'CSV'
    },
    'data-table': {
        'label': 'DataTable (JSON String)'
    },
    'data-table-response': {
        'label': 'DataTable (JSON Response)'
    },
    'tsv': {
        'label': 'TSV for Excel'
    }
}


# Log API Response Errors
# It's not recommended to set this to False.
LOG_ERRORS = True

# Scheduling: Max number of errors until query scheduling is paused.
QUERY_ERROR_LIMIT = 10

# Scheduling: How many seconds until a query is considered abandoned. (i.e.
# there have been no requests for the data). Calculated as a multiple of the
# query's refresh interval.
ABANDONED_INTERVAL_MULTIPLE = 2

# Scheduling: Used to randomize start times for scheduled tasks to prevent
# multiple queries from all starting at the same time.
MAX_RANDOM_COUNTDOWN = 60  # seconds

# API Query Limitations (CreateForm)
MAX_NAME_LENGTH = 115   # characters
MAX_URL_LENGTH = 2000   # characters
MIN_INTERVAL = 15       # seconds
MAX_INTERVAL = 2505600  # seconds

# Sharding Key Names
REQUEST_COUNTER_KEY_TEMPLATE = 'request-count-{}'
REQUEST_TIMESTAMP_KEY_TEMPLATE = 'last-request-{}'

# General Error Messages
ERROR_INACTIVE_QUERY = 'inactiveQuery'
ERROR_INVALID_REQUEST = 'invalidRequest'
ERROR_INVALID_QUERY_ID = 'invalidQueryId'

ERROR_MESSAGES = {
    ERROR_INACTIVE_QUERY: ('The query is not yet available. Wait and try again '
                           'later.'),
    ERROR_INVALID_REQUEST: ('The query id is invalid or the API Query is '
                            'disabled.'),
    ERROR_INVALID_QUERY_ID: 'Invalid query id.'
}

DEFAULT_ERROR_MESSAGE = {
    'error': ERROR_INVALID_REQUEST,
    'code': 400,
    'message': ERROR_MESSAGES[ERROR_INVALID_REQUEST]
}

# All Links for Google Analytics superProxy
LINKS = {
    # Admin links
    'admin_users': '/admin/proxy/users',
    'admin_runtask': '/admin/proxy/runtask',

    # Owner links
    'owner_default': r'/admin.*',
    'owner_index': '/admin',
    'owner_auth': '/admin/auth',
    'owner_activate': '/admin/activate',
    'query_manage': '/admin/query/manage',
    'query_edit': '/admin/query/edit',
    'query_delete': '/admin/query/delete',
    'query_delete_errors': '/admin/query/errors/delete',
    'query_create': '/admin/query/create',
    'query_status_change': '/admin/query/status',
    'query_run': '/admin/query/run',
    'query_schedule': '/admin/query/schedule',

    # Public links
    'public_default': r'/.*',
    'public_index': '/',
    'public_query': '/query',

    # Static directories
    'css': '/static/gasuperproxy/css/',
    'js': '/static/gasuperproxy/js/'
}

########NEW FILE########
__FILENAME__ = date_helper
#!/usr/bin/python2.7
#
# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Handles timezone conversions for the Google Analytics superProxy.

Based on example from:
https://developers.google.com/appengine/docs/python/datastore/typesandpropertyclasses#datetime
"""

__author__ = 'pete.frisella@gmail.com (Pete Frisella)'

import datetime


def GetNATzinfo(tz='utc'):
  """Returns a timezone info object for the requested North American timezone.

  Args:
    tz: The requested timezone in North America.

  Returns:
    tzinfo object The tzinfo object for the requested timezone. If the timezone
    info is not available then None is returned.

  Raises:
    AttributeError: An invalid string was provided as an argument.
  """
  tzinfo = None
  tz = tz.lower()

  if tz == 'pst' or tz == 'pdt' or tz == 'pacific':
    tzinfo = NorthAmericanTzinfo(-8, 'PST', 'PDT')
  elif tz == 'mst' or tz == 'mdt' or tz == 'mountain':
    tzinfo = NorthAmericanTzinfo(-7, 'MST', 'MDT')
  elif tz == 'cst' or tz == 'cdt' or tz == 'central':
    tzinfo = NorthAmericanTzinfo(-6, 'CST', 'CDT')
  elif tz == 'est' or tz == 'edt' or tz == 'eastern':
    tzinfo = NorthAmericanTzinfo(-5, 'EST', 'EDT')
  elif tz == 'ast' or tz == 'adt' or tz == 'atlantic':
    tzinfo = NorthAmericanTzinfo(-4, 'AST', 'ADT')
  elif tz == 'utc':
    tzinfo = UtcTzinfo()

  return tzinfo


def ConvertDatetimeTimezone(date_to_convert, to_timezone):
  """Converts a datetime object's timzeone.

  Args:
    date_to_convert: The datetime object to convert the timezone.
    to_timezone: The timezone to convert the datetimt to.

  Returns:
    A datetime object set to the timezone requested. If the timezone isn't
    supported then None is returned.

  Raises:
    AttributeError: An invalid datetime object was provided.
  """
  tzinfo = GetNATzinfo(to_timezone)

  if tzinfo:
    new_date = date_to_convert.replace(tzinfo=UtcTzinfo())
    return new_date.astimezone(tzinfo)

  return None


class NorthAmericanTzinfo(datetime.tzinfo):
  """Implementation of North American timezones."""

  def __init__(self, hours, std_name, dst_name):
    """Initialize value for the North American timezone.

    Args:
      hours: integer Offset of local time from UTC in hours. E.g. -8 is Pacific.
      std_name: string Name of the timezone for standard time. E.g. PST.
      dst_name: string Name of the timezone for daylight savings time. E.g. PDT.
    """
    self.std_offset = datetime.timedelta(hours=hours)
    self.std_name = std_name
    self.dst_name = dst_name

  def utcoffset(self, dt):
    return self.std_offset + self.dst(dt)

  def _FirstSunday(self, dt):
    """First Sunday on or after dt."""
    return dt + datetime.timedelta(days=(6-dt.weekday()))

  def dst(self, dt):
    # 2 am on the second Sunday in March
    dst_start = self._FirstSunday(datetime.datetime(dt.year, 3, 8, 2))
    # 1 am on the first Sunday in November
    dst_end = self._FirstSunday(datetime.datetime(dt.year, 11, 1, 1))

    if dst_start <= dt.replace(tzinfo=None) < dst_end:
      return datetime.timedelta(hours=1)
    else:
      return datetime.timedelta(hours=0)

  def tzname(self, dt):
    if self.dst(dt) == datetime.timedelta(hours=0):
      return self.dst_name
    else:
      return self.std_name


class UtcTzinfo(datetime.tzinfo):
  """Implementation of UTC time."""

  def utcoffset(self, dt):
    return datetime.timedelta(0)

  def dst(self, dt):
    return datetime.timedelta(0)

  def tzname(self, dt):
    return 'UTC'

########NEW FILE########
__FILENAME__ = errors
#!/usr/bin/python2.7
#
# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Custom exceptions for the Google Analytics superProxy."""

__author__ = 'pete.frisella@gmail.com (Pete Frisella)'


class GaSuperProxyHttpError(Exception):
  """Exception for a proxy response with a non-200 HTTP status."""

  def __init__(self, content, status):
    """Initialize the error object.

    Args:
      content: A dict representing the error message response to display.
      status: An integer representing the HTTP status code of the error.
    """
    Exception.__init__(self)
    self.status = status
    self.content = content

  def __str__(self):
    """Returns the string representation of the error message content."""
    return repr(self.content)

########NEW FILE########
__FILENAME__ = models_helper
#!/usr/bin/python2.7
#
# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utility functions for DB Models.

  FormatTimedelta: Converts a time delta to nicely formatted string.
  GetApiQueryLastRequest: Get timestamp of last request for an API Query.
  GetApiQueryRequestCount: Get request count of API Query.
  GetLastRequestTimedelta: Get the time since last request for query.
  GetModifiedTimedelta: Get the time since last refresh of API Query.
  IsApiQueryAbandoned: Checks if an API Query is abandoned.
  IsErrorLimitReached: Checks if the API Query has reached the error limit.
"""

__author__ = 'pete.frisella@gmail.com (Pete Frisella)'

from datetime import datetime

from controllers.util import co
from controllers.util import request_counter_shard
from controllers.util import request_timestamp_shard

from google.appengine.api import memcache


def FormatTimedelta(time_delta):
  """Formats a time delta into a sentence.

  Args:
    time_delta: A Timedelta object to format.

  Returns:
    A string containing a nicely formatted time delta in the form of
    "HH hours, MM minutes, ss seconds ago".
  """
  seconds = int(time_delta.total_seconds())
  days, time_left = divmod(seconds, 86400)  # 86400: seconds in a day = 24*60*60
  hours, time_left = divmod(time_left, 3600)  # 3600: seconds in an hour = 60*60
  minutes, seconds = divmod(time_left, 60)  # 60: seconds in a minute

  pretty_label = '%ss ago' % seconds
  if days > 0:
    pretty_label = '%sd, %sh, %sm ago' % (days, hours, minutes)
  elif hours > 0:
    pretty_label = '%sh, %sm ago' % (hours, minutes)
  elif minutes > 0:
    pretty_label = '%sm, %ss ago' % (minutes, seconds)
  return pretty_label


def GetApiQueryLastRequest(query_id):
  """Returns the timestamp of the last request.

  Args:
    query_id: The ID of the Query for which to retrieve the last request time.

  Returns:
    A DateTime object specifying the time when the API Query was last
    requested using the external public endpoint.
  """
  if query_id:
    request_timestamp_key = co.REQUEST_TIMESTAMP_KEY_TEMPLATE.format(query_id)
    request_timestamp = memcache.get(request_timestamp_key)
    if not request_timestamp:
      request_timestamp = request_timestamp_shard.GetTimestamp(
          request_timestamp_key)
    return request_timestamp
  return None


def GetApiQueryRequestCount(query_id):
  """Returns the request count for an API Query.

  Args:
    query_id: The ID of the Query from which to retrieve the request count.

  Returns:
    An integer representing the number of times the API Query has been
    requested using the external public endpoint.
  """
  request_counter_key = co.REQUEST_COUNTER_KEY_TEMPLATE.format(query_id)
  request_count = memcache.get(request_counter_key)
  if not request_count:
    request_count = request_counter_shard.GetCount(request_counter_key)
  return request_count


def GetLastRequestTimedelta(api_query, from_time=None):
  """Returns how long since the API Query response was last requested.

  Args:
    api_query: The API Query from which to retrieve the last request timedelta.
    from_time: A DateTime object representing the start time to calculate the
               timedelta from.

  Returns:
    A string that describes how long since the API Query response was last
    requested in the form of "HH hours, MM minutes, ss seconds ago" or None
    if the API Query response has never been requested.
  """
  if not from_time:
    from_time = datetime.utcnow()

  if api_query.last_request:
    time_delta = from_time - api_query.last_request
    return FormatTimedelta(time_delta)
  return None


def GetModifiedTimedelta(api_query, from_time=None):
  """Returns how long since the API Query was updated.

  Args:
    api_query: The API Query from which to retrieve the modified timedelta.
    from_time: A DateTime object representing the start time to calculate the
               timedelta from.

  Returns:
    A string that describes how long since the API Query has been updated in
    the form of "HH hours, MM minutes, ss seconds ago" or None if the API Query
    has never been updated.
  """
  if not from_time:
    from_time = datetime.utcnow()

  api_query_response = api_query.api_query_responses.get()
  if api_query_response:
    time_delta = from_time - api_query_response.modified
    return FormatTimedelta(time_delta)
  return None


def IsApiQueryAbandoned(api_query):
  """Determines whether the API Query is considered abandoned.

  When an API Query response has not been requested for a period
  of time (configurable) then it is considered abandoned. Abandoned
  queries will not be scheduled for a refresh. This saves quota and resources.

  If any of the following 3 cases are true, then a query is considered to be
  abandoned:
  1) The timestamp of the last public request is greater than some multiple
     of the query's refresh interval. The multiple is a configurable value,
     defined as the constant ABANDONED_INTERVAL_MULTIPLE. For example, if the
     refresh interval of a query is 30 seconds, and the
     ABANDONED_INTERVAL_MULTIPLE is 2, and the last public request for the query
     is greater than 60 seconds ago, then the query is considered abandoned.

  If the query has never been publicly requested and there is no timestamp then
  the modified date of the query is used. The query is considered abandoned
  when:
  2) The timestamp of the last modified date of the query is greater than some
     multiple of the query's refresh interval. The multiple is a configurable
     value, defined as the constant ABANDONED_INTERVAL_MULTIPLE.

  If the query has never been publicly requested and there is no modified
  timestamp then the query is considered abandoned when:
  3) A stored API Query Response exists for the query.

  Args:
    api_query: THe API Query to check if abandonded.

  Returns:
    A boolean indicating if the query is considered abandoned.
  """
  # Case 1: Use the last requested timestamp.
  if api_query.last_request:
    last_request_age = int(
        (datetime.utcnow() - api_query.last_request).total_seconds())
    max_timedelta = co.ABANDONED_INTERVAL_MULTIPLE * api_query.refresh_interval
    return last_request_age > max_timedelta

  # Case 2: Use the last modified timestamp.
  elif api_query.modified:
    last_modified_age = int(
        (datetime.utcnow() - api_query.modified).total_seconds())
    max_timedelta = co.ABANDONED_INTERVAL_MULTIPLE * api_query.refresh_interval
    return last_modified_age > max_timedelta

  # Case 3: Check if there is a saved API Query Response.
  else:
    api_query_response = api_query.api_query_responses.get()
    if api_query_response:
      return True

  return False


def IsErrorLimitReached(api_query):
  """Returns a boolean to indicate if the API Query reached the error limit."""
  return (api_query.api_query_errors.count(
      limit=co.QUERY_ERROR_LIMIT) == co.QUERY_ERROR_LIMIT)

########NEW FILE########
__FILENAME__ = query_helper
#!/usr/bin/python2.7
#
# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utility functions to help ineteract with API Queries.

  ResolveDates: Converts placeholders to actual dates.
  BuildApiQuery: Creates an API Query for the user.
  DeleteApiQuery: Deletes an API Query and related entities.
  DeleteApiQueryErrors: Deletes API Query Errors.
  DeleteApiQueryResponses: Deletes API Query saved Responses.
  ExecuteApiQueryTask: Runs a task from the task queue.
  FetchApiQueryResponse: Makes a request to an API.
  GetApiQuery: Retrieves an API Query from the datastore.
  GetApiQueryResponseFromDb: Returns the response content from the datastore..
  GetApiQueryResponseFromMemcache: Retrieves an API query from memcache.
  GetPublicEndpointResponse: Returns public response for an API Query request.
  InsertApiQueryError: Saves an API Query Error response.
  ListApiQueries: Returns a list of API Queries.
  RefreshApiQueryResponse: Fetched and saves an updated response for a query
  SaveApiQuery: Saves an API Query for a user.
  SaveApiQueryResponse: Saves an API Query response for an API Query.
  ScheduleAndSaveApiQuery: Saves and API Query and schedules it.
  SetPublicEndpointStatus: Enables/Disables the public endpoint.
  UpdateApiQueryCounter: Increments the request counter for an API Query.
  UpdateApiQueryTimestamp: Updates the last request time for an API Query.
  ValidateApiQuery: Validates form input for creating an API Query.
"""

__author__ = 'pete.frisella@gmail.com (Pete Frisella)'

import copy
from datetime import datetime
from datetime import timedelta
import json
import re
import urllib

from controllers.transform import transformers
from controllers.util import analytics_auth_helper
from controllers.util import co
from controllers.util import date_helper
from controllers.util import errors
from controllers.util import request_counter_shard
from controllers.util import request_timestamp_shard
from controllers.util import schedule_helper
from controllers.util import users_helper

from models import db_models

from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.api import users
from google.appengine.ext import db


def ResolveDates(fn):
  """A decorator to resolve placeholder dates of an API Query request URL.

  Supports {today} and {Ndaysago} date formats.

  Args:
    fn: The original function being wrapped.

  Returns:
    An API Query entity with a new request URL where placeholder dates
    have been resolved to actual dates.
  """
  def Wrapper(api_query):
    """Returns an API Query with resolved placeholder dates in request URL."""
    query = urllib.unquote(api_query.request)
    start_search = re.search(r'start-date={(\d+)daysago}', query)
    end_search = re.search(r'end-date={(\d+)daysago}', query)

    if start_search:
      resolved_date = (datetime.utcnow() - timedelta(
          days=int(start_search.group(1))))
      resolved_date = FormatResolvedDate(resolved_date)
      query = query.replace(start_search.group(),
                            'start-date=%s' % resolved_date)

    if end_search:
      resolved_date = (datetime.utcnow() - timedelta(days=int(
          end_search.group(1))))
      resolved_date = FormatResolvedDate(resolved_date)
      query = query.replace(end_search.group(),
                            'end-date=%s' % resolved_date)

    if '{today}' in query:
      resolved_date = datetime.utcnow()
      resolved_date = FormatResolvedDate(resolved_date)
      query = query.replace('{today}', resolved_date)

    # Leave original API Query untouched by returning a copy w/resolved dates
    new_api_query = copy.copy(api_query)
    new_api_query.request = query

    return fn(new_api_query)
  return Wrapper


def FormatResolvedDate(date_to_format, timezone=co.TIMEZONE):
  """Formats a UTC date for the Google Analytics superProxy.

  Args:
    date_to_format: datetime The UTC date to format.
    timezone: string The timezone to use when formatting the date.
              E.g. 'pst', 'Eastern', 'cdt'.

  Returns:
    A string representing the resolved date for the specified timezone. The
    date format returned is yyyy-mm-dd. If the timezone specified does not
    exist then the original date will be used.
  """
  if timezone.lower() != 'utc':
    timezone_date = date_helper.ConvertDatetimeTimezone(
        date_to_format, timezone)
    if timezone_date:
      date_to_format = timezone_date

  return date_to_format.strftime('%Y-%m-%d')


def BuildApiQuery(name, request, refresh_interval, **kwargs):
  """Builds an API Query object for the current user.

  Args:
    name: The name of the API Query.
    request: The requet URL for the API Query.
    refresh_interval: An integer that specifies how often, in seconds, to
                      refresh the API Query when it is scheduled.
    **kwargs: Additional properties to set when building the query.

  Returns:
    An API Query object configured using the passed in parameters.
  """
  current_user = users_helper.GetGaSuperProxyUser(
      users.get_current_user().user_id())
  modified = datetime.utcnow()
  api_query = db_models.ApiQuery(name=name,
                                 request=request,
                                 refresh_interval=refresh_interval,
                                 user=current_user,
                                 modified=modified)

  for key in kwargs:
    if hasattr(api_query, key):
      setattr(api_query, key, kwargs[key])

  return api_query


def DeleteApiQuery(api_query):
  """Deletes an API Query including any related entities.

  Args:
    api_query: The API Query to delete.
  """
  if api_query:
    query_id = str(api_query.key())
    DeleteApiQueryErrors(api_query)
    DeleteApiQueryResponses(api_query)
    api_query.delete()
    memcache.delete_multi(['api_query'] + co.SUPPORTED_FORMATS.keys(),
                          key_prefix=query_id)

    request_counter_key = co.REQUEST_COUNTER_KEY_TEMPLATE.format(query_id)
    request_counter_shard.DeleteCounter(request_counter_key)

    request_timestamp_key = co.REQUEST_TIMESTAMP_KEY_TEMPLATE.format(query_id)
    request_timestamp_shard.DeleteTimestamp(request_timestamp_key)


def DeleteApiQueryErrors(api_query):
  """Deletes API Query Errors.

  Args:
    api_query: The API Query to delete errors for.
  """
  if api_query and api_query.api_query_errors:
    db.delete(api_query.api_query_errors)


def DeleteApiQueryResponses(api_query):
  """Deletes an API Query saved response.

  Args:
    api_query: The API Query for which to delete the response.
  """
  if api_query and api_query.api_query_responses:
    db.delete(api_query.api_query_responses)


def ExecuteApiQueryTask(api_query):
  """Executes a refresh of an API Query from the task queue.

    Attempts to fetch and update an API Query and will also log any errors.
    Schedules the API Query for next execution.

  Args:
    api_query: The API Query to refresh.

  Returns:
    A boolean. True if the API refresh was a success and False if the API
    Query is not valid or an error was logged.
  """
  if api_query:
    query_id = str(api_query.key())
    api_query.in_queue = False

    api_response_content = FetchApiQueryResponse(api_query)

    if not api_response_content or api_response_content.get('error'):
      InsertApiQueryError(api_query, api_response_content)

      if api_query.is_error_limit_reached:
        api_query.is_scheduled = False

      SaveApiQuery(api_query)

      # Since it failed, execute the query again unless the refresh interval of
      # query is less than the random countdown, then schedule it normally.
      if api_query.refresh_interval < co.MAX_RANDOM_COUNTDOWN:
        schedule_helper.ScheduleApiQuery(api_query)  # Run at normal interval.
      else:
        schedule_helper.ScheduleApiQuery(api_query, randomize=True, countdown=0)
      return False

    else:
      SaveApiQueryResponse(api_query, api_response_content)

      # Check that public  endpoint wasn't disabled after task added to queue.
      if api_query.is_active:
        memcache.set_multi({'api_query': api_query,
                            co.DEFAULT_FORMAT: api_response_content},
                           key_prefix=query_id,
                           time=api_query.refresh_interval)
        # Delete the transformed content in memcache since it will be updated
        # at the next request.
        delete_keys = set(co.SUPPORTED_FORMATS) - set([co.DEFAULT_FORMAT])
        memcache.delete_multi(list(delete_keys), key_prefix=query_id)

        SaveApiQuery(api_query)
        schedule_helper.ScheduleApiQuery(api_query)
        return True

      # Save the query state just in case the user disabled it
      # while it was in the task queue.
      SaveApiQuery(api_query)
  return False


@ResolveDates
@analytics_auth_helper.AuthorizeApiQuery
def FetchApiQueryResponse(api_query):
  try:
    response = urlfetch.fetch(url=api_query.request, deadline=60)
    response_content = json.loads(response.content)
  except (ValueError, TypeError, AttributeError, urlfetch.Error), e:
    return {'error': str(e)}

  return response_content


def GetApiQuery(query_id):
  """Retrieves an API Query entity.

  Args:
    query_id: the id of the entity

  Returns:
    The requested API Query entity or None if it doesn't exist.
  """
  try:
    return db_models.ApiQuery.get(query_id)
  except db.BadKeyError:
    return None


def GetApiQueryResponseFromDb(api_query):
  """Attempts to return an API Query response from the datastore.

  Args:
    api_query: The API Query for which the response is being requested.

  Returns:
    A dict with the HTTP status code and content for a public response.
    e.g. Valid Response: {'status': 200, 'content': A_JSON_RESPONSE}
    e.g. Error: {'status': 400, 'content': {'error': 'badRequest',
                                            'code': 400,
                                            'message': This is a bad request'}}
  """
  status = 400
  content = co.DEFAULT_ERROR_MESSAGE

  if api_query and api_query.is_active:
    try:
      query_response = api_query.api_query_responses.get()

      if query_response:
        status = 200
        content = query_response.content
      else:
        status = 400
        content = {
            'error': co.ERROR_INACTIVE_QUERY,
            'code': status,
            'message': co.ERROR_MESSAGES[co.ERROR_INACTIVE_QUERY]}
    except db.BadKeyError:
      status = 400
      content = {
          'error': co.ERROR_INVALID_QUERY_ID,
          'code': status,
          'message': co.ERROR_MESSAGES[co.ERROR_INVALID_QUERY_ID]}

  response = {
      'status': status,
      'content': content
  }

  return response


def GetApiQueryResponseFromMemcache(query_id, requested_format):
  """Attempts to return an API Query response from memcache.

  Args:
    query_id: The query id of the API Query to retrieve from memcache.
    requested_format: The format type requested for the response.

  Returns:
    A dict contatining the API Query, the response in the default format
    and requested format if available. None if there was no query found.
  """
  query_in_memcache = memcache.get_multi(
      ['api_query', co.DEFAULT_FORMAT, requested_format],
      key_prefix=query_id)

  if query_in_memcache:
    query = {
        'api_query': query_in_memcache.get('api_query'),
        'content': query_in_memcache.get(co.DEFAULT_FORMAT),
        'transformed_content': query_in_memcache.get(requested_format)
    }
    return query
  return None


def GetPublicEndpointResponse(
    query_id=None, requested_format=None, transform=None):
  """Returns the public response for an external user request.

  This handles all the steps required to get the latest successful API
  response for an API Query.
    1) Check Memcache, if found skip to #4.
    2) If not in memcache, check if the stored response is abandoned and needs
       to be refreshed.
    3) Retrieve response from datastore.
    4) Perform any transforms and return the formatted response to the user.

  Args:
    query_id: The query id to retrieve the response for.
    requested_format: The format type requested for the response.
    transform: The transform instance to use to transform the content to the
               requested format, if required.

  Returns:
    A tuple contatining the response content, and status code to
    render. e.g. (CONTENT, 200)
  """
  transformed_response_content = None
  schedule_query = False

  if not requested_format or requested_format not in co.SUPPORTED_FORMATS:
    requested_format = co.DEFAULT_FORMAT

  response = GetApiQueryResponseFromMemcache(query_id, requested_format)

  # 1. Check Memcache
  if response and response.get('api_query') and response.get('content'):
    api_query = response.get('api_query')
    response_content = response.get('content')
    transformed_response_content = response.get('transformed_content')
    response_status = 200
  else:
    api_query = GetApiQuery(query_id)

    # 2. Check if this is an abandoned query
    if (api_query is not None and api_query.is_active
        and not api_query.is_error_limit_reached
        and api_query.is_abandoned):
      RefreshApiQueryResponse(api_query)

    # 3. Retrieve response from datastore
    response = GetApiQueryResponseFromDb(api_query)
    response_content = response.get('content')
    response_status = response.get('status')

    # Flag to schedule query later on if there is a successful response.
    if api_query:
      schedule_query = not api_query.in_queue

  # 4. Return the formatted response.
  if response_status == 200:
    UpdateApiQueryCounter(query_id)
    UpdateApiQueryTimestamp(query_id)

    if co.ANONYMIZE_RESPONSES:
      response_content = transformers.RemoveKeys(response_content)

    if not transformed_response_content:
      try:
        transformed_response_content = transform.Transform(response_content)
      except (KeyError, TypeError, AttributeError):
        # If the transformation fails then return the original content.
        transformed_response_content = response_content

    memcache_keys = {
        'api_query': api_query,
        co.DEFAULT_FORMAT: response_content,
        requested_format: transformed_response_content
    }

    memcache.add_multi(memcache_keys,
                       key_prefix=query_id,
                       time=api_query.refresh_interval)

    # Attempt to schedule query if required.
    if schedule_query:
      schedule_helper.ScheduleApiQuery(api_query)

    response_content = transformed_response_content
  else:
    raise errors.GaSuperProxyHttpError(response_content, response_status)

  return (response_content, response_status)


def InsertApiQueryError(api_query, error):
  """Stores an API Error Response entity for an API Query.

  Args:
    api_query: The API Query for which the error occurred.
    error: The error that occurred.
  """
  if co.LOG_ERRORS:
    error = db_models.ApiErrorResponse(
        api_query=api_query,
        content=error,
        timestamp=datetime.utcnow())
    error.put()


def ListApiQueries(user=None, limit=1000):
  """Returns all queries that have been created.

  Args:
    user: The user to list API Queries for. None returns all queries.
    limit: The maximum number of queries to return.

  Returns:
    A list of queries.
  """
  if user:
    try:
      db_query = user.api_queries
      db_query.order('name')
      return db_query.run(limit=limit)
    except db.ReferencePropertyResolveError:
      return None
  else:
    api_query = db_models.ApiQuery.all()
    api_query.order('name')
    return api_query.run(limit=limit)
  return None


def RefreshApiQueryResponse(api_query):
  """Executes the API request and refreshes the response for an API Query.

  Args:
    api_query: The API Query to refresh the respone for.
  """
  if api_query:
    api_response = FetchApiQueryResponse(api_query)
    if not api_response or api_response.get('error'):
      InsertApiQueryError(api_query, api_response)
    else:
      SaveApiQueryResponse(api_query, api_response)

      # Clear memcache since this query response has changed.
      memcache.delete_multi(['api_query'] + co.SUPPORTED_FORMATS.keys(),
                            key_prefix=str(api_query.key()))


def SaveApiQuery(api_query, **kwargs):
  """Saves an API Query to the datastore.

  Args:
    api_query: The API Query to save.
    **kwargs: Additional properties to set for the API Query before saving.

  Returns:
    If successful the API Query that was saved or None if the save was
    unsuccessful.
  """

  if api_query:
    for key in kwargs:
      modified = datetime.utcnow()
      api_query.modified = modified
      if hasattr(api_query, key):
        setattr(api_query, key, kwargs[key])

    try:
      api_query.put()
      return api_query
    except db.TransactionFailedError:
      return None
  return None


def SaveApiQueryResponse(api_query, content):
  """Updates or creates a new API Query Response for an API Query.

  Args:
    api_query: The API Query for which the response will be added to
    content: The content of the API respone to add to the API Query.
  """
  db_response = api_query.api_query_responses.get()
  modified = datetime.utcnow()

  if db_response:
    db_response.content = content
    db_response.modified = modified
  else:
    db_response = db_models.ApiQueryResponse(api_query=api_query,
                                             content=content,
                                             modified=modified)
  db_response.put()


def ScheduleAndSaveApiQuery(api_query, **kwargs):
  """Schedules and saves an API Query.

  Args:
    api_query: The API Query to save and schedule.
    **kwargs: Additional properties to set for the API Query before saving.

  Returns:
    If successful the API Query that was saved or None if the save was
    unsuccessful.
  """
  if api_query:
    api_query.is_active = True
    api_query.is_scheduled = True
    saved = SaveApiQuery(api_query, **kwargs)
    if saved:
      schedule_helper.ScheduleApiQuery(api_query, randomize=True, countdown=0)
      return api_query

  return None


def SetPublicEndpointStatus(api_query, status=None):
  """Change the public endpoint status of an API Query.

  Args:
    api_query: The API Query to change
    status: The status to change the API Query to. If status=None then the
            status of the API Query will be toggled.

  Returns:
    True if status change was successful, False otherwise.
  """
  if api_query and status in (None, True, False):
    if not status:
      api_query.is_active = not api_query.is_active
    else:
      api_query.is_active = status

    if api_query.is_active is False:
      api_query.is_scheduled = False

    try:
      api_query.put()
      memcache.delete_multi(['api_query'] + co.SUPPORTED_FORMATS.keys(),
                            key_prefix=str(api_query.key()))
      return True
    except db.TransactionFailedError:
      return False
  return False


def UpdateApiQueryCounter(query_id):
  """Increment the request counter for the API Query."""
  request_counter_key = co.REQUEST_COUNTER_KEY_TEMPLATE.format(query_id)
  request_counter_shard.Increment(request_counter_key)


def UpdateApiQueryTimestamp(query_id):
  """Update the last request timestamp for an API Query."""
  request_timestamp_key = co.REQUEST_TIMESTAMP_KEY_TEMPLATE.format(query_id)
  request_timestamp_shard.Refresh(request_timestamp_key)


def ValidateApiQuery(request_input):
  """Validates API Query settings.

  Args:
    request_input: The incoming request object containing form input value.

  Returns:
    A dict containing the validated API Query values or None if the input
    was invalid.
    e.g. {'name': 'Query Name',
          'request': 'http://apirequest',
          'refresh_interval': 15
         }
  """
  if request_input:
    name = request_input.get('name')
    request = request_input.get('request')
    refresh_interval = request_input.get('refresh_interval')
    validated_request = None
    try:
      if not name or not request or not refresh_interval:
        return None

      if len(name) > co.MAX_NAME_LENGTH or len(name) <= 0:
        return None
      validated_request = {
          'name': name
      }

      if len(request) > co.MAX_URL_LENGTH or len(request) <= 0:
        return None
      validated_request['request'] = request

      if int(refresh_interval) not in range(co.MIN_INTERVAL, co.MAX_INTERVAL):
        return None
      validated_request['refresh_interval'] = int(refresh_interval)
    except (ValueError, TypeError):
      return None
    return validated_request

  return None

########NEW FILE########
__FILENAME__ = request_counter_shard
#!/usr/bin/python2.7
#
# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Handles the request counter for API Queries.

  Sharding is used to keep track of the number of requests for an API Query.

  Based on code from:
  https://developers.google.com/appengine/articles/sharding_counters
"""

__author__ = 'pete.frisella@gmail.com (Pete Frisella)'

import random

from google.appengine.api import memcache
from google.appengine.ext import ndb

SHARD_KEY_TEMPLATE = 'shard-{}-{:d}'


class GeneralCounterShardConfig(ndb.Model):
  """Tracks the number of shards for each named counter."""
  num_shards = ndb.IntegerProperty(default=20)

  @classmethod
  def AllKeys(cls, name):
    """Returns all possible keys for the counter name given the config.

    Args:
      name: The name of the counter.

    Returns:
      The full list of ndb.Key values corresponding to all the possible
      counter shards that could exist.
    """
    config = cls.get_or_insert(name)
    shard_key_strings = [SHARD_KEY_TEMPLATE.format(name, index)
                         for index in range(config.num_shards)]
    return [ndb.Key(GeneralCounterShard, shard_key_string)
            for shard_key_string in shard_key_strings]


class GeneralCounterShard(ndb.Model):
  """Shards for each named counter."""
  count = ndb.IntegerProperty(default=0)


def GetCount(name):
  """Retrieve the value for a given sharded counter.

  Args:
    name: The name of the counter.

  Returns:
    Integer; the cumulative count of all sharded counters for the given
    counter name.
  """
  total = memcache.get(name)
  if total is None:
    total = 0
    all_keys = GeneralCounterShardConfig.AllKeys(name)
    for counter in ndb.get_multi(all_keys):
      if counter is not None:
        total += counter.count
    memcache.add(name, total, 60)
  return total


def Increment(name):
  """Increment the value for a given sharded counter.

  Args:
    name: The name of the counter.
  """
  config = GeneralCounterShardConfig.get_or_insert(name)
  _Increment(name, config.num_shards)


@ndb.transactional
def _Increment(name, num_shards):
  """Transactional helper to increment the value for a given sharded counter.

  Also takes a number of shards to determine which shard will be used.

  Args:
    name: The name of the counter.
    num_shards: How many shards to use.
  """
  index = random.randint(0, num_shards - 1)
  shard_key_string = SHARD_KEY_TEMPLATE.format(name, index)
  counter = GeneralCounterShard.get_by_id(shard_key_string)
  if counter is None:
    counter = GeneralCounterShard(id=shard_key_string)
  counter.count += 1
  counter.put()
  # Memcache increment does nothing if the name is not a key in memcache
  memcache.incr(name)


@ndb.transactional
def IncreaseShards(name, num_shards):
  """Increase the number of shards for a given sharded counter.

  Will never decrease the number of shards.

  Args:
    name: The name of the counter.
    num_shards: How many shards to use.
  """
  config = GeneralCounterShardConfig.get_or_insert(name)
  if config.num_shards < num_shards:
    config.num_shards = num_shards
    config.put()


def DeleteCounter(name):
  """Delete a sharded counter.

  Args:
    name: The name of the counter to delete.
  """
  all_keys = GeneralCounterShardConfig.AllKeys(name)
  ndb.delete_multi(all_keys)
  memcache.delete(name)
  config_key = ndb.Key('GeneralCounterShardConfig', name)
  config_key.delete()

########NEW FILE########
__FILENAME__ = request_timestamp_shard
#!/usr/bin/python2.7
#
# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Handles the request timestamp for API Query requests.

  Sharding timestamps is used to handle when the last request was made for
  and API Query.

  Based on code from:
  https://developers.google.com/appengine/articles/sharding_counters
"""

__author__ = 'pete.frisella@gmail.com (Pete Frisella)'

from datetime import datetime
import random

from google.appengine.api import memcache
from google.appengine.ext import ndb

SHARD_KEY_TEMPLATE = 'shard-{}-{:d}'


class GeneralTimestampShardConfig(ndb.Model):
  """Tracks the number of shards for each named timestamp."""
  num_shards = ndb.IntegerProperty(default=20)

  @classmethod
  def AllKeys(cls, name):
    """Returns all possible keys for the timestamp name given the config.

    Args:
      name: The name of the timestamp.

    Returns:
      The full list of ndb.Key values corresponding to all the possible
      timestamp shards that could exist.
    """
    config = cls.get_or_insert(name)
    shard_key_strings = [SHARD_KEY_TEMPLATE.format(name, index)
                         for index in range(config.num_shards)]
    return [ndb.Key(GeneralTimestampShard, shard_key_string)
            for shard_key_string in shard_key_strings]


class GeneralTimestampShard(ndb.Model):
  """Shards for each named Timestamp."""
  timestamp = ndb.DateTimeProperty()


def GetTimestamp(name):
  """Retrieve the value for a given sharded timestamp.

  Args:
    name: The name of the timestamp.

  Returns:
    Integer; the cumulative count of all sharded Timestamps for the given
    Timestamp name.
  """
  latest_timestamp = memcache.get(name)
  if latest_timestamp is None:
    all_keys = GeneralTimestampShardConfig.AllKeys(name)
    for timestamp in ndb.get_multi(all_keys):
      if timestamp is not None and latest_timestamp is None:
        latest_timestamp = timestamp.timestamp
      elif timestamp is not None and timestamp.timestamp > latest_timestamp:
        latest_timestamp = timestamp.timestamp
    memcache.add(name, latest_timestamp, 60)
  return latest_timestamp


def Refresh(name):
  """Refresh the value for a given sharded timestamp.

  Args:
    name: The name of the timestamp.
  """
  config = GeneralTimestampShardConfig.get_or_insert(name)
  _Refresh(name, config.num_shards)


@ndb.transactional
def _Refresh(name, num_shards):
  """Transactional helper to refresh the value for a given sharded timestamp.

  Also takes a number of shards to determine which shard will be used.

  Args:
      name: The name of the timestamp.
      num_shards: How many shards to use.
  """
  index = random.randint(0, num_shards - 1)
  shard_key_string = SHARD_KEY_TEMPLATE.format(name, index)
  timestamp = GeneralTimestampShard.get_by_id(shard_key_string)
  if timestamp is None:
    timestamp = GeneralTimestampShard(id=shard_key_string)
  timestamp.timestamp = datetime.utcnow()
  timestamp.put()
  # Memcache replace does nothing if the name is not a key in memcache
  memcache.replace(name, timestamp.timestamp)


@ndb.transactional
def IncreaseShards(name, num_shards):
  """Increase the number of shards for a given sharded counter.

  Will never decrease the number of shards.

  Args:
    name: The name of the counter.
    num_shards: How many shards to use.
  """
  config = GeneralTimestampShardConfig.get_or_insert(name)
  if config.num_shards < num_shards:
    config.num_shards = num_shards
    config.put()


def DeleteTimestamp(name):
  """Delete a sharded timestamp.

  Args:
    name: The name of the timestamp to delete.
  """
  all_keys = GeneralTimestampShardConfig.AllKeys(name)
  ndb.delete_multi(all_keys)
  memcache.delete(name)
  config_key = ndb.Key('GeneralTimestampShardConfig', name)
  config_key.delete()

########NEW FILE########
__FILENAME__ = schedule_helper
#!/usr/bin/python2.7
#
# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utility functions to handle API Query scheduling.

  SetApiQueryScheduleStatus: Start and stop scheduling for an API Query.
  ScheduleApiQuery: Attempt to add an API Query to the task queue.
"""

__author__ = 'pete.frisella@gmail.com (Pete Frisella)'

import logging
import random

from controllers.util import co

from google.appengine.api import taskqueue


def SetApiQueryScheduleStatus(api_query, status=None):
  """Change the scheduling status of an API Query.

  Args:
    api_query: The API Query to change the scheduling status for.
    status: The status to change the API Query to. If status=None then the
            scheduling status of the API Query will be toggled.

  Returns:
    True if status change was successful, False otherwise.
  """
  if api_query:
    if status is None:
      api_query.is_scheduled = not api_query.is_scheduled
    elif status:
      api_query.is_scheduled = True
    else:
      api_query.is_scheduled = False

    api_query.put()
    return True
  return False


def ScheduleApiQuery(api_query, randomize=False, countdown=None):
  """Adds a task to refresh an API Query response.

  Args:
    api_query: the API Query entity to update
    randomize: A boolean to indicate whether to add a random amount of time to
               task countdown. Helpful to minimze occurrence of all tasks
               starting at the same time.
    countdown: How long to wait until executing the query
  """
  if (not api_query.in_queue
      and (api_query.is_scheduled and not api_query.is_abandoned
           and not api_query.is_error_limit_reached)):

    random_seconds = 0
    if randomize:
      random_seconds = random.randint(0, co.MAX_RANDOM_COUNTDOWN)

    if countdown is None:
      countdown = api_query.refresh_interval

    try:
      taskqueue.add(
          url=co.LINKS['admin_runtask'],
          countdown=countdown + random_seconds,
          params={
              'query_id': api_query.key(),
          })
      api_query.in_queue = True
      api_query.put()
    except taskqueue.Error as e:
      logging.error(
          'Error adding task to queue. API Query ID: {}. Error: {}'.format(
              api_query.key(), e))

########NEW FILE########
__FILENAME__ = template_helper
#!/usr/bin/python2.7
#
# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utility functions to help prepare template values for API Queries.

  GetContentForTemplate: Template value for API Query response content.
  GetErrorsForTemplate: Template value for API Query errors responses.
  GetFormatLinksForTemplate: Template value for API Query transform links.
  GetLinksForTemplate: Template values for API Query links.
  GetPropertiesForTemplate: Template values for API Query properties.
  GetTemplateValuesForAdmin: All template values required for the Admin page.
  GetTemplateValuesForManage: All template values required for the Manage page.
"""

__author__ = 'pete.frisella@gmail.com (Pete Frisella)'

from controllers.util import co


def GetContentForTemplate(api_query):
  """Prepares and returns the template value for an API Query response.

  Args:
    api_query: The API Query for which to prepare the response content template
               value.
  Returns:
    A dict containing the template value to use for the Response content.
  """
  content = {}
  if api_query:
    api_query_response = api_query.api_query_responses.get()
    if api_query_response:
      content['response_content'] = api_query_response.content

  return content


def GetErrorsForTemplate(api_query):
  """Prepares and returns the template values for API Query error responses.

  Args:
    api_query: The API Query for which to prepare the errors template values.
  Returns:
    A dict containing a list of template values to use for each API Query
    error responses.
  """
  errors = {}
  if api_query and api_query.api_query_errors:
    error_list = []
    for error in api_query.api_query_errors:
      error_list.append({
          'timestamp': error.timestamp,
          'content': error.content
      })

    errors['errors'] = error_list

  return errors


def GetFormatLinksForTemplate(api_query, hostname):
  """Prepares and returns template values for API Query format links.

  Args:
    api_query: The API Query for which to prepare the format links template
               values.
    hostname: The hostname to use for the format links.

  Returns:
    A dict containing the template value to use for the API Query format links.
  """
  query_id = api_query.key()
  format_links = {}
  format_links_list = {}

  for transform, config in co.SUPPORTED_FORMATS.items():
    format_links_list.update({
        config.get('label'): '%s%s?id=%s&format=%s' % (
            hostname, co.LINKS['public_query'], query_id, transform)
    })

  format_links['format_links'] = format_links_list

  return format_links


def GetLinksForTemplate(api_query, hostname):
  """Prepares and returns the template values for API Query links.

  Args:
    api_query: The API Query for which to prepare the links template values.
    hostname: The hostname to use for the links.

  Returns:
    A dict containing the template values to use for API Query links.
  """
  query_id = api_query.key()
  public_link = '%s%s?id=%s' % (hostname, co.LINKS['public_query'], query_id)
  manage_link = '%s?query_id=%s' % (co.LINKS['query_manage'], query_id)
  edit_link = '%s?query_id=%s&action=edit' % (
      co.LINKS['query_manage'], query_id)
  edit_post_link = '%s?query_id=%s' % (co.LINKS['query_edit'], query_id)
  delete_link = '%s?query_id=%s' % (co.LINKS['query_delete'], query_id)
  delete_errors_link = '%s?query_id=%s' % (
      co.LINKS['query_delete_errors'], query_id)
  status_change_link = '%s?query_id=%s' % (
      co.LINKS['query_status_change'], query_id)

  links = {
      'public_link': public_link,
      'manage_link': manage_link,
      'edit_link': edit_link,
      'edit_post_link': edit_post_link,
      'delete_link': delete_link,
      'delete_errors_link': delete_errors_link,
      'status_change_link': status_change_link
  }

  return links


def GetPropertiesForTemplate(api_query):
  """Prepares and returns the template value for a set of API Query properties.

  Args:
    api_query: The API Query for which to prepare the properties template
               values.
  Returns:
    A dict containing the template values to use for the API Query properties.
  """
  properties = {}
  if api_query:
    properties = {
        'id': str(api_query.key()),
        'name': api_query.name,
        'request': api_query.request,
        'user_email': api_query.user.email,
        'is_active': api_query.is_active,
        'is_scheduled': api_query.is_scheduled,
        'is_error_limit_reached': api_query.is_error_limit_reached,
        'in_queue': api_query.in_queue,
        'refresh_interval': api_query.refresh_interval,
        'modified_timedelta': api_query.modified_timedelta,
        'last_request_timedelta': api_query.last_request_timedelta,
        'request_count': api_query.request_count,
        'error_count': api_query.api_query_errors.count(
            limit=co.QUERY_ERROR_LIMIT)
    }

  return properties


def GetTemplateValuesForAdmin(api_queries, hostname):
  """Prepares and returns all the template values required for the Admin page.

  Args:
    api_queries: The list of queries for which to prepare template values.
    hostname: The hostname to use for links.

  Returns:
    A list of dicts that contain all the template values needed for each API
    Query that is listed on the Admin page.
  """
  template_values = []
  if api_queries:
    for api_query in api_queries:
      query_values = {}
      query_values.update(GetPropertiesForTemplate(api_query))
      query_values.update(GetLinksForTemplate(api_query, hostname))
      template_values.append(query_values)
  return template_values


def GetTemplateValuesForManage(api_query, hostname):
  """Prepares and returns all the template values required for the Manage page.

  Args:
    api_query: The API Query for which to prepare template values.
    hostname: The hostname to use for links.

  Returns:
    A dict that contains all the template values needed the API
    Query that is listed on the Manage page.
  """
  template_values = {}
  template_values.update(GetPropertiesForTemplate(api_query))
  template_values.update(GetLinksForTemplate(api_query, hostname))
  template_values.update(GetErrorsForTemplate(api_query))
  template_values.update(GetContentForTemplate(api_query))
  template_values.update(GetFormatLinksForTemplate(api_query, hostname))
  return template_values

########NEW FILE########
__FILENAME__ = users_helper
#!/usr/bin/python2.7
#
# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utility functions to handle user operations.

  AddInvitation: Adds an email to the user invite table.
  ActivateUser: Activates a user account so they can use the application.
  GetGaSuperProxyUser: Returns a user from the datastore.
  GetInvitation: Gets a user's invitation from the datastore.
  ListInvitations: Lists all invitations saved in the datastore.
  ListUsers: Lists all users saved in the datastore.
  SetUserCredentials: Saves auth tokens for a user.
"""

__author__ = 'pete.frisella@gmail.com (Pete Frisella)'

from datetime import datetime
from datetime import timedelta

from models import db_models

from google.appengine.api import users
from google.appengine.ext import db


def AddInvitation(email):
  """Create an invite for a user so that they can login.

  Args:
    email: the email of the user to invite/add.

  Returns:
    A boolean indicating whether the user was added or not.
  """
  if not GetInvitation(email):
    invitation = db_models.GaSuperProxyUserInvitation(
        email=email.lower(),
        issued=datetime.utcnow())
    invitation.put()
    return True
  return False


def ActivateUser():
  """Activates the current user if they have an outstanding invite.

  Returns:
    The user object for the activated user.
  """
  current_user = users.get_current_user()
  if current_user:
    invite = GetInvitation(current_user.email().lower())
    if invite:
      user = db_models.GaSuperProxyUser.get_or_insert(
          key_name=current_user.user_id(),
          email=current_user.email(),
          nickname=current_user.nickname())
      invite.delete()
      return user
  return None


def GetGaSuperProxyUser(user_id):
  """Retrieves a GaSuperProxyUser entity.

  Args:
    user_id: the user id of the entity

  Returns:
    The requested GaSuperProxyUser entity or None if it does not exist.
  """
  try:
    return db_models.GaSuperProxyUser.get_by_key_name(user_id)
  except db.BadKeyError:
    return None


def GetInvitation(email):
  """Retrieves a user invitation.

  Args:
    email: the email of the user

  Returns:
    The requested user invitation or None if it does not exist.
  """
  invitation = db_models.GaSuperProxyUserInvitation.all()
  invitation.filter('email = ', email)
  return invitation.get()


def ListInvitations(limit=1000):
  """Returns all outstanding user invitations.

  Args:
    limit: The maximum number of invitations to return.

  Returns:
    A list of invitations.
  """
  invitation = db_models.GaSuperProxyUserInvitation.all()
  return invitation.run(limit=limit)


def ListUsers(limit=1000):
  """Returns all users that have been added to the service.

  Args:
    limit: The maximum number of queries to return.

  Returns:
    A list of users.
  """
  user = db_models.GaSuperProxyUser.all()
  return user.run(limit=limit)


def SetUserCredentials(
    user_id, refresh_token=None, access_token=None, expires_in=3600):
  """Saves OAuth credentials for a user. Creates user if it does not exist.

  If only a user id is provided then credentials for a user will be cleared.

  Args:
    user_id: The id of the user to store credentials for.
    refresh_token: The refresh token to save for the user.
    access_token: The access token to save for the user.
    expires_in: How long the access token is valid for (seconds).
  """
  user = GetGaSuperProxyUser(user_id)
  token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)

  if user:
    user.ga_refresh_token = refresh_token
    user.ga_access_token = access_token
    user.ga_token_expiry = token_expiry
  else:
    user = db_models.GaSuperProxyUser(
        key_name=users.get_current_user().user_id(),
        email=users.get_current_user().email(),
        nickname=users.get_current_user().nickname(),
        ga_refresh_token=refresh_token,
        ga_access_token=access_token,
        ga_token_expiry=token_expiry)
  user.put()

########NEW FILE########
__FILENAME__ = csv_writer
#!/usr/bin/python2.5
# -*- coding: utf-8 -*-
#
# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utility to convert a Core Reporting API reponse into TSV.

This provides utitlites to both print TSV files to the standard output
as well as directly to a file. This logic handles all the utf-8 conversion.

  GetCsvStringPrinter: Returns an instantiated object to output to a string.
  GetTsvFilePrinter: Returns an instantiated object to output to files.
  GetTsvScreenPrinter: Returns an instantiated object to output to the screen.
  UnicodeWriter(): Utf-8 encodes output.
  ExportPrinter(): Converts the Core Reporting API response into tabular data.
"""

__author__ = 'nickski15@gmail.com (Nick Mihailovski)'


import codecs
import csv
import StringIO
import sys
import types


# A list of special characters that need to be escaped.
SPECIAL_CHARS = ('+', '-', '/', '*', '=')
# TODO(nm): Test leading numbers.


def GetCsvStringPrinter(f):
  """Returns a ExportPrinter object to output to string."""
  writer = UnicodeWriter(f)
  return ExportPrinter(writer)


def GetTsvFilePrinter(file_name):
  """Returns a ExportPrinter object to output to file_name.

  Args:
    file_name: string The name of the file to output to.

  Returns:
    The newly created ExportPrinter object.
  """
  my_handle = open(file_name)
  writer = UnicodeWriter(my_handle, dialect='excel-tab')
  return ExportPrinter(writer)


def GetTsvScreenPrinter():
  """Returns a ExportPrinter object to output to std.stdout."""
  writer = UnicodeWriter(sys.stdout, dialect='excel-tab')
  return ExportPrinter(writer)


def GetTsvStringPrinter(f):
  """Returns a ExportPrinter object to output to std.stdout."""
  writer = UnicodeWriter(f, dialect='excel-tab')
  return ExportPrinter(writer)


# Wrapper to output to utf-8. Taken mostly / directly from Python docs:
# http://docs.python.org/library/csv.html
class UnicodeWriter(object):
  """A CSV writer which uses the csv module to output csv compatible formats.

  Will write rows to CSV file "f", which is encoded in the given encoding.
  """

  def __init__(self, f, dialect=csv.excel, encoding='utf-8', **kwds):
    # Redirect output to a queue
    self.queue = StringIO.StringIO()
    self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
    self.stream = f
    self.encoder = codecs.getincrementalencoder(encoding)()

  def WriteRow(self, row):
    """Writes a row to the file."""
    self.writer.writerow([s.encode('utf-8') for s in row])
    # Fetch UTF-8 output from the queue ...
    data = self.queue.getvalue()
    data = data.decode('utf-8')
    # ... and reencode it into the target encoding
    data = self.encoder.encode(data)
    # write to the target stream
    self.stream.write(data)
    # empty queue
    self.queue.truncate(0)

  def WriteRows(self, rows):
    for row in rows:
      self.writerow(row)


class ExportPrinter(object):
  """Utility class to output a the data feed as tabular data."""

  def __init__(self, writer):
    """Initializes the class.

    Args:
      writer: Typically an instance of UnicodeWriter. The interface for this
          object provides two methods, WriteRow and WriteRow, which
          accepts a list or a list of lists respectively and process them as
          needed.
    """
    self.writer = writer

  def Output(self, results):
    """Outputs formatted rows of data retrieved from the Core Reporting API.

    This uses the writer object to output the data in the Core Reporting API.

    Args:
      results: The response from the Core Reporting API.
    """

    if not results.get('rows'):
      self.writer.WriteRow('No Results found')

    else:
      self.OutputProfileName(results)
      self.writer.WriteRow([])
      self.OutputContainsSampledData(results)
      self.writer.WriteRow([])
      self.OutputQueryInfo(results)
      self.writer.WriteRow([])

      self.OutputHeaders(results)
      self.OutputRows(results)

      self.writer.WriteRow([])
      self.OutputRowCounts(results)
      self.OutputTotalsForAllResults(results)

  def OutputProfileName(self, results):
    """Outputs the profile name along with the qurey."""
    profile_name = ''
    info = results.get('profileInfo')
    if info:
      profile_name = info.get('profileName')

    self.writer.WriteRow(['Report For Profile: ', profile_name])

  def OutputQueryInfo(self, results):
    """Outputs the query used."""
    self.writer.WriteRow(['These query parameters were used:'])

    query = results.get('query')
    for key, value in query.iteritems():
      if type(value) == types.ListType:
        value = ','.join(value)
      else:
        value = str(value)
      value = ExcelEscape(value)
      self.writer.WriteRow([key, value])

  def OutputContainsSampledData(self, results):
    """Outputs whether the resuls have been sampled."""

    sampled_text = 'do not'
    if results.get('containsSampledData'):
      sampled_text = 'do'

    row_text = 'These results %s contain sampled data.' % sampled_text
    self.writer.WriteRow([row_text])

  def OutputHeaders(self, results):
    """Outputs all the dimension and metric names in order."""

    row = []
    for header in results.get('columnHeaders'):
      row.append(header.get('name'))
    self.writer.WriteRow(row)

  def OutputRows(self, results):
    """Outputs all the rows in the table."""

    # Replace any first characters that have an = with '=
    for row in results.get('rows'):
      out_row = []
      for cell in row:
        cell = ExcelEscape(cell)
        out_row.append(cell)
      self.writer.WriteRow(out_row)

  def OutputRowCounts(self, results):
    """Outputs how many rows were returned vs rows that were matched."""

    items = str(results.get('itemsPerPage'))
    matched = str(results.get('totalResults'))

    output = [
        ['Rows Returned', items],
        ['Rows Matched', matched]
    ]
    self.writer.WriteRows(output)

  def OutputTotalsForAllResults(self, results):
    """Outputs the totals for all results matched by the query.

    This is not the sum of the values returned in the response.
    This will align the metric totals in the same columns as
    the headers are printed. The totals are stored as a dict, where the
    key is the metric name and the value is the total. To align these
    totals in the proper columns, a position index of the metric name
    and it's position in the table is first created. Then the totals
    are added by position to a row of empty strings.

    Args:
      results: The response from the Core Reporting API.
    """

    # Create the metric position index.
    metric_index = {}
    headers = results.get('columnHeaders')
    for index in range(0, len(headers)):
      header = headers[index]
      if header.get('columnType') == 'METRIC':
        metric_index[header.get('name')] = index

    # Create a row of empty strings the same length as the header.
    row = [''] * len(headers)

    # Use the position index to output the totals in the right columns.
    totals = results.get('totalsForAllResults')
    for metric_name, metric_total in totals.iteritems():
      index = metric_index[metric_name]
      row[index] = metric_total

    self.writer.WriteRows([['Totals For All Rows Matched'], row])


def ExcelEscape(input_value):
  """Escapes the first character of a string if it is special in Excel.

  Args:
    input_value: string The value to escape.

  Returns:
    A string that has the first character escaped if it is sepcial.
  """
  if input_value and input_value[0] in SPECIAL_CHARS:
    return "'" + input_value

  return input_value


########NEW FILE########
__FILENAME__ = gviz_api
#!/usr/bin/python
#
# Copyright (C) 2009 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Converts Python data into data for Google Visualization API clients.

This library can be used to create a google.visualization.DataTable usable by
visualizations built on the Google Visualization API. Output formats are raw
JSON, JSON response, JavaScript, CSV, and HTML table.

See http://code.google.com/apis/visualization/ for documentation on the
Google Visualization API.
"""

__author__ = "Amit Weinstein, Misha Seltzer, Jacob Baskin"

import cgi
import cStringIO
import csv
import datetime
try:
  import json
except ImportError:
  import simplejson as json
import types


class DataTableException(Exception):
  """The general exception object thrown by DataTable."""
  pass


class DataTableJSONEncoder(json.JSONEncoder):
  """JSON encoder that handles date/time/datetime objects correctly."""

  def __init__(self):
    json.JSONEncoder.__init__(self,
                              separators=(",", ":"),
                              ensure_ascii=False)

  def default(self, o):
    if isinstance(o, datetime.datetime):
      if o.microsecond == 0:
        # If the time doesn't have ms-resolution, leave it out to keep
        # things smaller.
        return "Date(%d,%d,%d,%d,%d,%d)" % (
            o.year, o.month - 1, o.day, o.hour, o.minute, o.second)
      else:
        return "Date(%d,%d,%d,%d,%d,%d,%d)" % (
            o.year, o.month - 1, o.day, o.hour, o.minute, o.second,
            o.microsecond / 1000)
    elif isinstance(o, datetime.date):
      return "Date(%d,%d,%d)" % (o.year, o.month - 1, o.day)
    elif isinstance(o, datetime.time):
      return [o.hour, o.minute, o.second]
    else:
      return super(DataTableJSONEncoder, self).default(o)


class DataTable(object):
  """Wraps the data to convert to a Google Visualization API DataTable.

  Create this object, populate it with data, then call one of the ToJS...
  methods to return a string representation of the data in the format described.

  You can clear all data from the object to reuse it, but you cannot clear
  individual cells, rows, or columns. You also cannot modify the table schema
  specified in the class constructor.

  You can add new data one or more rows at a time. All data added to an
  instantiated DataTable must conform to the schema passed in to __init__().

  You can reorder the columns in the output table, and also specify row sorting
  order by column. The default column order is according to the original
  table_description parameter. Default row sort order is ascending, by column
  1 values. For a dictionary, we sort the keys for order.

  The data and the table_description are closely tied, as described here:

  The table schema is defined in the class constructor's table_description
  parameter. The user defines each column using a tuple of
  (id[, type[, label[, custom_properties]]]). The default value for type is
  string, label is the same as ID if not specified, and custom properties is
  an empty dictionary if not specified.

  table_description is a dictionary or list, containing one or more column
  descriptor tuples, nested dictionaries, and lists. Each dictionary key, list
  element, or dictionary element must eventually be defined as
  a column description tuple. Here's an example of a dictionary where the key
  is a tuple, and the value is a list of two tuples:
    {('a', 'number'): [('b', 'number'), ('c', 'string')]}

  This flexibility in data entry enables you to build and manipulate your data
  in a Python structure that makes sense for your program.

  Add data to the table using the same nested design as the table's
  table_description, replacing column descriptor tuples with cell data, and
  each row is an element in the top level collection. This will be a bit
  clearer after you look at the following examples showing the
  table_description, matching data, and the resulting table:

  Columns as list of tuples [col1, col2, col3]
    table_description: [('a', 'number'), ('b', 'string')]
    AppendData( [[1, 'z'], [2, 'w'], [4, 'o'], [5, 'k']] )
    Table:
    a  b   <--- these are column ids/labels
    1  z
    2  w
    4  o
    5  k

  Dictionary of columns, where key is a column, and value is a list of
  columns  {col1: [col2, col3]}
    table_description: {('a', 'number'): [('b', 'number'), ('c', 'string')]}
    AppendData( data: {1: [2, 'z'], 3: [4, 'w']}
    Table:
    a  b  c
    1  2  z
    3  4  w

  Dictionary where key is a column, and the value is itself a dictionary of
  columns {col1: {col2, col3}}
    table_description: {('a', 'number'): {'b': 'number', 'c': 'string'}}
    AppendData( data: {1: {'b': 2, 'c': 'z'}, 3: {'b': 4, 'c': 'w'}}
    Table:
    a  b  c
    1  2  z
    3  4  w
  """

  def __init__(self, table_description, data=None, custom_properties=None):
    """Initialize the data table from a table schema and (optionally) data.

    See the class documentation for more information on table schema and data
    values.

    Args:
      table_description: A table schema, following one of the formats described
                         in TableDescriptionParser(). Schemas describe the
                         column names, data types, and labels. See
                         TableDescriptionParser() for acceptable formats.
      data: Optional. If given, fills the table with the given data. The data
            structure must be consistent with schema in table_description. See
            the class documentation for more information on acceptable data. You
            can add data later by calling AppendData().
      custom_properties: Optional. A dictionary from string to string that
                         goes into the table's custom properties. This can be
                         later changed by changing self.custom_properties.

    Raises:
      DataTableException: Raised if the data and the description did not match,
                          or did not use the supported formats.
    """
    self.__columns = self.TableDescriptionParser(table_description)
    self.__data = []
    self.custom_properties = {}
    if custom_properties is not None:
      self.custom_properties = custom_properties
    if data:
      self.LoadData(data)

  @staticmethod
  def CoerceValue(value, value_type):
    """Coerces a single value into the type expected for its column.

    Internal helper method.

    Args:
      value: The value which should be converted
      value_type: One of "string", "number", "boolean", "date", "datetime" or
                  "timeofday".

    Returns:
      An item of the Python type appropriate to the given value_type. Strings
      are also converted to Unicode using UTF-8 encoding if necessary.
      If a tuple is given, it should be in one of the following forms:
        - (value, formatted value)
        - (value, formatted value, custom properties)
      where the formatted value is a string, and custom properties is a
      dictionary of the custom properties for this cell.
      To specify custom properties without specifying formatted value, one can
      pass None as the formatted value.
      One can also have a null-valued cell with formatted value and/or custom
      properties by specifying None for the value.
      This method ignores the custom properties except for checking that it is a
      dictionary. The custom properties are handled in the ToJSon and ToJSCode
      methods.
      The real type of the given value is not strictly checked. For example,
      any type can be used for string - as we simply take its str( ) and for
      boolean value we just check "if value".
      Examples:
        CoerceValue(None, "string") returns None
        CoerceValue((5, "5$"), "number") returns (5, "5$")
        CoerceValue(100, "string") returns "100"
        CoerceValue(0, "boolean") returns False

    Raises:
      DataTableException: The value and type did not match in a not-recoverable
                          way, for example given value 'abc' for type 'number'.
    """
    if isinstance(value, tuple):
      # In case of a tuple, we run the same function on the value itself and
      # add the formatted value.
      if (len(value) not in [2, 3] or
          (len(value) == 3 and not isinstance(value[2], dict))):
        raise DataTableException("Wrong format for value and formatting - %s." %
                                 str(value))
      if not isinstance(value[1], types.StringTypes + (types.NoneType,)):
        raise DataTableException("Formatted value is not string, given %s." %
                                 type(value[1]))
      js_value = DataTable.CoerceValue(value[0], value_type)
      return (js_value,) + value[1:]

    t_value = type(value)
    if value is None:
      return value
    if value_type == "boolean":
      return bool(value)

    elif value_type == "number":
      if isinstance(value, (int, long, float)):
        return value
      raise DataTableException("Wrong type %s when expected number" % t_value)

    elif value_type == "string":
      if isinstance(value, unicode):
        return value
      else:
        return str(value).decode("utf-8")

    elif value_type == "date":
      if isinstance(value, datetime.datetime):
        return datetime.date(value.year, value.month, value.day)
      elif isinstance(value, datetime.date):
        return value
      else:
        raise DataTableException("Wrong type %s when expected date" % t_value)

    elif value_type == "timeofday":
      if isinstance(value, datetime.datetime):
        return datetime.time(value.hour, value.minute, value.second)
      elif isinstance(value, datetime.time):
        return value
      else:
        raise DataTableException("Wrong type %s when expected time" % t_value)

    elif value_type == "datetime":
      if isinstance(value, datetime.datetime):
        return value
      else:
        raise DataTableException("Wrong type %s when expected datetime" %
                                 t_value)
    # If we got here, it means the given value_type was not one of the
    # supported types.
    raise DataTableException("Unsupported type %s" % value_type)

  @staticmethod
  def EscapeForJSCode(encoder, value):
    if value is None:
      return "null"
    elif isinstance(value, datetime.datetime):
      if value.microsecond == 0:
        # If it's not ms-resolution, leave that out to save space.
        return "new Date(%d,%d,%d,%d,%d,%d)" % (value.year,
                                                value.month - 1,  # To match JS
                                                value.day,
                                                value.hour,
                                                value.minute,
                                                value.second)
      else:
        return "new Date(%d,%d,%d,%d,%d,%d,%d)" % (value.year,
                                                   value.month - 1,  # match JS
                                                   value.day,
                                                   value.hour,
                                                   value.minute,
                                                   value.second,
                                                   value.microsecond / 1000)
    elif isinstance(value, datetime.date):
      return "new Date(%d,%d,%d)" % (value.year, value.month - 1, value.day)
    else:
      return encoder.encode(value)

  @staticmethod
  def ToString(value):
    if value is None:
      return "(empty)"
    elif isinstance(value, (datetime.datetime,
                            datetime.date,
                            datetime.time)):
      return str(value)
    elif isinstance(value, unicode):
      return value
    elif isinstance(value, bool):
      return str(value).lower()
    else:
      return str(value).decode("utf-8")

  @staticmethod
  def ColumnTypeParser(description):
    """Parses a single column description. Internal helper method.

    Args:
      description: a column description in the possible formats:
       'id'
       ('id',)
       ('id', 'type')
       ('id', 'type', 'label')
       ('id', 'type', 'label', {'custom_prop1': 'custom_val1'})
    Returns:
      Dictionary with the following keys: id, label, type, and
      custom_properties where:
        - If label not given, it equals the id.
        - If type not given, string is used by default.
        - If custom properties are not given, an empty dictionary is used by
          default.

    Raises:
      DataTableException: The column description did not match the RE, or
          unsupported type was passed.
    """
    if not description:
      raise DataTableException("Description error: empty description given")

    if not isinstance(description, (types.StringTypes, tuple)):
      raise DataTableException("Description error: expected either string or "
                               "tuple, got %s." % type(description))

    if isinstance(description, types.StringTypes):
      description = (description,)

    # According to the tuple's length, we fill the keys
    # We verify everything is of type string
    for elem in description[:3]:
      if not isinstance(elem, types.StringTypes):
        raise DataTableException("Description error: expected tuple of "
                                 "strings, current element of type %s." %
                                 type(elem))
    desc_dict = {"id": description[0],
                 "label": description[0],
                 "type": "string",
                 "custom_properties": {}}
    if len(description) > 1:
      desc_dict["type"] = description[1].lower()
      if len(description) > 2:
        desc_dict["label"] = description[2]
        if len(description) > 3:
          if not isinstance(description[3], dict):
            raise DataTableException("Description error: expected custom "
                                     "properties of type dict, current element "
                                     "of type %s." % type(description[3]))
          desc_dict["custom_properties"] = description[3]
          if len(description) > 4:
            raise DataTableException("Description error: tuple of length > 4")
    if desc_dict["type"] not in ["string", "number", "boolean",
                                 "date", "datetime", "timeofday"]:
      raise DataTableException(
          "Description error: unsupported type '%s'" % desc_dict["type"])
    return desc_dict

  @staticmethod
  def TableDescriptionParser(table_description, depth=0):
    """Parses the table_description object for internal use.

    Parses the user-submitted table description into an internal format used
    by the Python DataTable class. Returns the flat list of parsed columns.

    Args:
      table_description: A description of the table which should comply
                         with one of the formats described below.
      depth: Optional. The depth of the first level in the current description.
             Used by recursive calls to this function.

    Returns:
      List of columns, where each column represented by a dictionary with the
      keys: id, label, type, depth, container which means the following:
      - id: the id of the column
      - name: The name of the column
      - type: The datatype of the elements in this column. Allowed types are
              described in ColumnTypeParser().
      - depth: The depth of this column in the table description
      - container: 'dict', 'iter' or 'scalar' for parsing the format easily.
      - custom_properties: The custom properties for this column.
      The returned description is flattened regardless of how it was given.

    Raises:
      DataTableException: Error in a column description or in the description
                          structure.

    Examples:
      A column description can be of the following forms:
       'id'
       ('id',)
       ('id', 'type')
       ('id', 'type', 'label')
       ('id', 'type', 'label', {'custom_prop1': 'custom_val1'})
       or as a dictionary:
       'id': 'type'
       'id': ('type',)
       'id': ('type', 'label')
       'id': ('type', 'label', {'custom_prop1': 'custom_val1'})
      If the type is not specified, we treat it as string.
      If no specific label is given, the label is simply the id.
      If no custom properties are given, we use an empty dictionary.

      input: [('a', 'date'), ('b', 'timeofday', 'b', {'foo': 'bar'})]
      output: [{'id': 'a', 'label': 'a', 'type': 'date',
                'depth': 0, 'container': 'iter', 'custom_properties': {}},
               {'id': 'b', 'label': 'b', 'type': 'timeofday',
                'depth': 0, 'container': 'iter',
                'custom_properties': {'foo': 'bar'}}]

      input: {'a': [('b', 'number'), ('c', 'string', 'column c')]}
      output: [{'id': 'a', 'label': 'a', 'type': 'string',
                'depth': 0, 'container': 'dict', 'custom_properties': {}},
               {'id': 'b', 'label': 'b', 'type': 'number',
                'depth': 1, 'container': 'iter', 'custom_properties': {}},
               {'id': 'c', 'label': 'column c', 'type': 'string',
                'depth': 1, 'container': 'iter', 'custom_properties': {}}]

      input:  {('a', 'number', 'column a'): { 'b': 'number', 'c': 'string'}}
      output: [{'id': 'a', 'label': 'column a', 'type': 'number',
                'depth': 0, 'container': 'dict', 'custom_properties': {}},
               {'id': 'b', 'label': 'b', 'type': 'number',
                'depth': 1, 'container': 'dict', 'custom_properties': {}},
               {'id': 'c', 'label': 'c', 'type': 'string',
                'depth': 1, 'container': 'dict', 'custom_properties': {}}]

      input: { ('w', 'string', 'word'): ('c', 'number', 'count') }
      output: [{'id': 'w', 'label': 'word', 'type': 'string',
                'depth': 0, 'container': 'dict', 'custom_properties': {}},
               {'id': 'c', 'label': 'count', 'type': 'number',
                'depth': 1, 'container': 'scalar', 'custom_properties': {}}]

      input: {'a': ('number', 'column a'), 'b': ('string', 'column b')}
      output: [{'id': 'a', 'label': 'column a', 'type': 'number', 'depth': 0,
               'container': 'dict', 'custom_properties': {}},
               {'id': 'b', 'label': 'column b', 'type': 'string', 'depth': 0,
               'container': 'dict', 'custom_properties': {}}

      NOTE: there might be ambiguity in the case of a dictionary representation
      of a single column. For example, the following description can be parsed
      in 2 different ways: {'a': ('b', 'c')} can be thought of a single column
      with the id 'a', of type 'b' and the label 'c', or as 2 columns: one named
      'a', and the other named 'b' of type 'c'. We choose the first option by
      default, and in case the second option is the right one, it is possible to
      make the key into a tuple (i.e. {('a',): ('b', 'c')}) or add more info
      into the tuple, thus making it look like this: {'a': ('b', 'c', 'b', {})}
      -- second 'b' is the label, and {} is the custom properties field.
    """
    # For the recursion step, we check for a scalar object (string or tuple)
    if isinstance(table_description, (types.StringTypes, tuple)):
      parsed_col = DataTable.ColumnTypeParser(table_description)
      parsed_col["depth"] = depth
      parsed_col["container"] = "scalar"
      return [parsed_col]

    # Since it is not scalar, table_description must be iterable.
    if not hasattr(table_description, "__iter__"):
      raise DataTableException("Expected an iterable object, got %s" %
                               type(table_description))
    if not isinstance(table_description, dict):
      # We expects a non-dictionary iterable item.
      columns = []
      for desc in table_description:
        parsed_col = DataTable.ColumnTypeParser(desc)
        parsed_col["depth"] = depth
        parsed_col["container"] = "iter"
        columns.append(parsed_col)
      if not columns:
        raise DataTableException("Description iterable objects should not"
                                 " be empty.")
      return columns
    # The other case is a dictionary
    if not table_description:
      raise DataTableException("Empty dictionaries are not allowed inside"
                               " description")

    # To differentiate between the two cases of more levels below or this is
    # the most inner dictionary, we consider the number of keys (more then one
    # key is indication for most inner dictionary) and the type of the key and
    # value in case of only 1 key (if the type of key is string and the type of
    # the value is a tuple of 0-3 items, we assume this is the most inner
    # dictionary).
    # NOTE: this way of differentiating might create ambiguity. See docs.
    if (len(table_description) != 1 or
        (isinstance(table_description.keys()[0], types.StringTypes) and
         isinstance(table_description.values()[0], tuple) and
         len(table_description.values()[0]) < 4)):
      # This is the most inner dictionary. Parsing types.
      columns = []
      # We sort the items, equivalent to sort the keys since they are unique
      for key, value in sorted(table_description.items()):
        # We parse the column type as (key, type) or (key, type, label) using
        # ColumnTypeParser.
        if isinstance(value, tuple):
          parsed_col = DataTable.ColumnTypeParser((key,) + value)
        else:
          parsed_col = DataTable.ColumnTypeParser((key, value))
        parsed_col["depth"] = depth
        parsed_col["container"] = "dict"
        columns.append(parsed_col)
      return columns
    # This is an outer dictionary, must have at most one key.
    parsed_col = DataTable.ColumnTypeParser(table_description.keys()[0])
    parsed_col["depth"] = depth
    parsed_col["container"] = "dict"
    return ([parsed_col] +
            DataTable.TableDescriptionParser(table_description.values()[0],
                                             depth=depth + 1))

  @property
  def columns(self):
    """Returns the parsed table description."""
    return self.__columns

  def NumberOfRows(self):
    """Returns the number of rows in the current data stored in the table."""
    return len(self.__data)

  def SetRowsCustomProperties(self, rows, custom_properties):
    """Sets the custom properties for given row(s).

    Can accept a single row or an iterable of rows.
    Sets the given custom properties for all specified rows.

    Args:
      rows: The row, or rows, to set the custom properties for.
      custom_properties: A string to string dictionary of custom properties to
      set for all rows.
    """
    if not hasattr(rows, "__iter__"):
      rows = [rows]
    for row in rows:
      self.__data[row] = (self.__data[row][0], custom_properties)

  def LoadData(self, data, custom_properties=None):
    """Loads new rows to the data table, clearing existing rows.

    May also set the custom_properties for the added rows. The given custom
    properties dictionary specifies the dictionary that will be used for *all*
    given rows.

    Args:
      data: The rows that the table will contain.
      custom_properties: A dictionary of string to string to set as the custom
                         properties for all rows.
    """
    self.__data = []
    self.AppendData(data, custom_properties)

  def AppendData(self, data, custom_properties=None):
    """Appends new data to the table.

    Data is appended in rows. Data must comply with
    the table schema passed in to __init__(). See CoerceValue() for a list
    of acceptable data types. See the class documentation for more information
    and examples of schema and data values.

    Args:
      data: The row to add to the table. The data must conform to the table
            description format.
      custom_properties: A dictionary of string to string, representing the
                         custom properties to add to all the rows.

    Raises:
      DataTableException: The data structure does not match the description.
    """
    # If the maximal depth is 0, we simply iterate over the data table
    # lines and insert them using _InnerAppendData. Otherwise, we simply
    # let the _InnerAppendData handle all the levels.
    if not self.__columns[-1]["depth"]:
      for row in data:
        self._InnerAppendData(({}, custom_properties), row, 0)
    else:
      self._InnerAppendData(({}, custom_properties), data, 0)

  def _InnerAppendData(self, prev_col_values, data, col_index):
    """Inner function to assist LoadData."""
    # We first check that col_index has not exceeded the columns size
    if col_index >= len(self.__columns):
      raise DataTableException("The data does not match description, too deep")

    # Dealing with the scalar case, the data is the last value.
    if self.__columns[col_index]["container"] == "scalar":
      prev_col_values[0][self.__columns[col_index]["id"]] = data
      self.__data.append(prev_col_values)
      return

    if self.__columns[col_index]["container"] == "iter":
      if not hasattr(data, "__iter__") or isinstance(data, dict):
        raise DataTableException("Expected iterable object, got %s" %
                                 type(data))
      # We only need to insert the rest of the columns
      # If there are less items than expected, we only add what there is.
      for value in data:
        if col_index >= len(self.__columns):
          raise DataTableException("Too many elements given in data")
        prev_col_values[0][self.__columns[col_index]["id"]] = value
        col_index += 1
      self.__data.append(prev_col_values)
      return

    # We know the current level is a dictionary, we verify the type.
    if not isinstance(data, dict):
      raise DataTableException("Expected dictionary at current level, got %s" %
                               type(data))
    # We check if this is the last level
    if self.__columns[col_index]["depth"] == self.__columns[-1]["depth"]:
      # We need to add the keys in the dictionary as they are
      for col in self.__columns[col_index:]:
        if col["id"] in data:
          prev_col_values[0][col["id"]] = data[col["id"]]
      self.__data.append(prev_col_values)
      return

    # We have a dictionary in an inner depth level.
    if not data.keys():
      # In case this is an empty dictionary, we add a record with the columns
      # filled only until this point.
      self.__data.append(prev_col_values)
    else:
      for key in sorted(data):
        col_values = dict(prev_col_values[0])
        col_values[self.__columns[col_index]["id"]] = key
        self._InnerAppendData((col_values, prev_col_values[1]),
                              data[key], col_index + 1)

  def _PreparedData(self, order_by=()):
    """Prepares the data for enumeration - sorting it by order_by.

    Args:
      order_by: Optional. Specifies the name of the column(s) to sort by, and
                (optionally) which direction to sort in. Default sort direction
                is asc. Following formats are accepted:
                "string_col_name"  -- For a single key in default (asc) order.
                ("string_col_name", "asc|desc") -- For a single key.
                [("col_1","asc|desc"), ("col_2","asc|desc")] -- For more than
                    one column, an array of tuples of (col_name, "asc|desc").

    Returns:
      The data sorted by the keys given.

    Raises:
      DataTableException: Sort direction not in 'asc' or 'desc'
    """
    if not order_by:
      return self.__data

    proper_sort_keys = []
    if isinstance(order_by, types.StringTypes) or (
        isinstance(order_by, tuple) and len(order_by) == 2 and
        order_by[1].lower() in ["asc", "desc"]):
      order_by = (order_by,)
    for key in order_by:
      if isinstance(key, types.StringTypes):
        proper_sort_keys.append((key, 1))
      elif (isinstance(key, (list, tuple)) and len(key) == 2 and
            key[1].lower() in ("asc", "desc")):
        proper_sort_keys.append((key[0], key[1].lower() == "asc" and 1 or -1))
      else:
        raise DataTableException("Expected tuple with second value: "
                                 "'asc' or 'desc'")

    def SortCmpFunc(row1, row2):
      """cmp function for sorted. Compares by keys and 'asc'/'desc' keywords."""
      for key, asc_mult in proper_sort_keys:
        cmp_result = asc_mult * cmp(row1[0].get(key), row2[0].get(key))
        if cmp_result:
          return cmp_result
      return 0

    return sorted(self.__data, cmp=SortCmpFunc)

  def ToJSCode(self, name, columns_order=None, order_by=()):
    """Writes the data table as a JS code string.

    This method writes a string of JS code that can be run to
    generate a DataTable with the specified data. Typically used for debugging
    only.

    Args:
      name: The name of the table. The name would be used as the DataTable's
            variable name in the created JS code.
      columns_order: Optional. Specifies the order of columns in the
                     output table. Specify a list of all column IDs in the order
                     in which you want the table created.
                     Note that you must list all column IDs in this parameter,
                     if you use it.
      order_by: Optional. Specifies the name of the column(s) to sort by.
                Passed as is to _PreparedData.

    Returns:
      A string of JS code that, when run, generates a DataTable with the given
      name and the data stored in the DataTable object.
      Example result:
        "var tab1 = new google.visualization.DataTable();
         tab1.addColumn("string", "a", "a");
         tab1.addColumn("number", "b", "b");
         tab1.addColumn("boolean", "c", "c");
         tab1.addRows(10);
         tab1.setCell(0, 0, "a");
         tab1.setCell(0, 1, 1, null, {"foo": "bar"});
         tab1.setCell(0, 2, true);
         ...
         tab1.setCell(9, 0, "c");
         tab1.setCell(9, 1, 3, "3$");
         tab1.setCell(9, 2, false);"

    Raises:
      DataTableException: The data does not match the type.
    """

    encoder = DataTableJSONEncoder()

    if columns_order is None:
      columns_order = [col["id"] for col in self.__columns]
    col_dict = dict([(col["id"], col) for col in self.__columns])

    # We first create the table with the given name
    jscode = "var %s = new google.visualization.DataTable();\n" % name
    if self.custom_properties:
      jscode += "%s.setTableProperties(%s);\n" % (
          name, encoder.encode(self.custom_properties))

    # We add the columns to the table
    for i, col in enumerate(columns_order):
      jscode += "%s.addColumn(%s, %s, %s);\n" % (
          name,
          encoder.encode(col_dict[col]["type"]),
          encoder.encode(col_dict[col]["label"]),
          encoder.encode(col_dict[col]["id"]))
      if col_dict[col]["custom_properties"]:
        jscode += "%s.setColumnProperties(%d, %s);\n" % (
            name, i, encoder.encode(col_dict[col]["custom_properties"]))
    jscode += "%s.addRows(%d);\n" % (name, len(self.__data))

    # We now go over the data and add each row
    for (i, (row, cp)) in enumerate(self._PreparedData(order_by)):
      # We add all the elements of this row by their order
      for (j, col) in enumerate(columns_order):
        if col not in row or row[col] is None:
          continue
        value = self.CoerceValue(row[col], col_dict[col]["type"])
        if isinstance(value, tuple):
          cell_cp = ""
          if len(value) == 3:
            cell_cp = ", %s" % encoder.encode(row[col][2])
          # We have a formatted value or custom property as well
          jscode += ("%s.setCell(%d, %d, %s, %s%s);\n" %
                     (name, i, j,
                      self.EscapeForJSCode(encoder, value[0]),
                      self.EscapeForJSCode(encoder, value[1]), cell_cp))
        else:
          jscode += "%s.setCell(%d, %d, %s);\n" % (
              name, i, j, self.EscapeForJSCode(encoder, value))
      if cp:
        jscode += "%s.setRowProperties(%d, %s);\n" % (
            name, i, encoder.encode(cp))
    return jscode

  def ToHtml(self, columns_order=None, order_by=()):
    """Writes the data table as an HTML table code string.

    Args:
      columns_order: Optional. Specifies the order of columns in the
                     output table. Specify a list of all column IDs in the order
                     in which you want the table created.
                     Note that you must list all column IDs in this parameter,
                     if you use it.
      order_by: Optional. Specifies the name of the column(s) to sort by.
                Passed as is to _PreparedData.

    Returns:
      An HTML table code string.
      Example result (the result is without the newlines):
       <html><body><table border="1">
        <thead><tr><th>a</th><th>b</th><th>c</th></tr></thead>
        <tbody>
         <tr><td>1</td><td>"z"</td><td>2</td></tr>
         <tr><td>"3$"</td><td>"w"</td><td></td></tr>
        </tbody>
       </table></body></html>

    Raises:
      DataTableException: The data does not match the type.
    """
    table_template = "<html><body><table border=\"1\">%s</table></body></html>"
    columns_template = "<thead><tr>%s</tr></thead>"
    rows_template = "<tbody>%s</tbody>"
    row_template = "<tr>%s</tr>"
    header_cell_template = "<th>%s</th>"
    cell_template = "<td>%s</td>"

    if columns_order is None:
      columns_order = [col["id"] for col in self.__columns]
    col_dict = dict([(col["id"], col) for col in self.__columns])

    columns_list = []
    for col in columns_order:
      columns_list.append(header_cell_template %
                          cgi.escape(col_dict[col]["label"]))
    columns_html = columns_template % "".join(columns_list)

    rows_list = []
    # We now go over the data and add each row
    for row, unused_cp in self._PreparedData(order_by):
      cells_list = []
      # We add all the elements of this row by their order
      for col in columns_order:
        # For empty string we want empty quotes ("").
        value = ""
        if col in row and row[col] is not None:
          value = self.CoerceValue(row[col], col_dict[col]["type"])
        if isinstance(value, tuple):
          # We have a formatted value and we're going to use it
          cells_list.append(cell_template % cgi.escape(self.ToString(value[1])))
        else:
          cells_list.append(cell_template % cgi.escape(self.ToString(value)))
      rows_list.append(row_template % "".join(cells_list))
    rows_html = rows_template % "".join(rows_list)

    return table_template % (columns_html + rows_html)

  def ToCsv(self, columns_order=None, order_by=(), separator=","):
    """Writes the data table as a CSV string.

    Output is encoded in UTF-8 because the Python "csv" module can't handle
    Unicode properly according to its documentation.

    Args:
      columns_order: Optional. Specifies the order of columns in the
                     output table. Specify a list of all column IDs in the order
                     in which you want the table created.
                     Note that you must list all column IDs in this parameter,
                     if you use it.
      order_by: Optional. Specifies the name of the column(s) to sort by.
                Passed as is to _PreparedData.
      separator: Optional. The separator to use between the values.

    Returns:
      A CSV string representing the table.
      Example result:
       'a','b','c'
       1,'z',2
       3,'w',''

    Raises:
      DataTableException: The data does not match the type.
    """

    csv_buffer = cStringIO.StringIO()
    writer = csv.writer(csv_buffer, delimiter=separator)

    if columns_order is None:
      columns_order = [col["id"] for col in self.__columns]
    col_dict = dict([(col["id"], col) for col in self.__columns])

    writer.writerow([col_dict[col]["label"].encode("utf-8")
                     for col in columns_order])

    # We now go over the data and add each row
    for row, unused_cp in self._PreparedData(order_by):
      cells_list = []
      # We add all the elements of this row by their order
      for col in columns_order:
        value = ""
        if col in row and row[col] is not None:
          value = self.CoerceValue(row[col], col_dict[col]["type"])
        if isinstance(value, tuple):
          # We have a formatted value. Using it only for date/time types.
          if col_dict[col]["type"] in ["date", "datetime", "timeofday"]:
            cells_list.append(self.ToString(value[1]).encode("utf-8"))
          else:
            cells_list.append(self.ToString(value[0]).encode("utf-8"))
        else:
          cells_list.append(self.ToString(value).encode("utf-8"))
      writer.writerow(cells_list)
    return csv_buffer.getvalue()

  def ToTsvExcel(self, columns_order=None, order_by=()):
    """Returns a file in tab-separated-format readable by MS Excel.

    Returns a file in UTF-16 little endian encoding, with tabs separating the
    values.

    Args:
      columns_order: Delegated to ToCsv.
      order_by: Delegated to ToCsv.

    Returns:
      A tab-separated little endian UTF16 file representing the table.
    """
    return (self.ToCsv(columns_order, order_by, separator="\t")
            .decode("utf-8").encode("UTF-16LE"))

  def _ToJSonObj(self, columns_order=None, order_by=()):
    """Returns an object suitable to be converted to JSON.

    Args:
      columns_order: Optional. A list of all column IDs in the order in which
                     you want them created in the output table. If specified,
                     all column IDs must be present.
      order_by: Optional. Specifies the name of the column(s) to sort by.
                Passed as is to _PreparedData().

    Returns:
      A dictionary object for use by ToJSon or ToJSonResponse.
    """
    if columns_order is None:
      columns_order = [col["id"] for col in self.__columns]
    col_dict = dict([(col["id"], col) for col in self.__columns])

    # Creating the column JSON objects
    col_objs = []
    for col_id in columns_order:
      col_obj = {"id": col_dict[col_id]["id"],
                 "label": col_dict[col_id]["label"],
                 "type": col_dict[col_id]["type"]}
      if col_dict[col_id]["custom_properties"]:
        col_obj["p"] = col_dict[col_id]["custom_properties"]
      col_objs.append(col_obj)

    # Creating the rows jsons
    row_objs = []
    for row, cp in self._PreparedData(order_by):
      cell_objs = []
      for col in columns_order:
        value = self.CoerceValue(row.get(col, None), col_dict[col]["type"])
        if value is None:
          cell_obj = None
        elif isinstance(value, tuple):
          cell_obj = {"v": value[0]}
          if len(value) > 1 and value[1] is not None:
            cell_obj["f"] = value[1]
          if len(value) == 3:
            cell_obj["p"] = value[2]
        else:
          cell_obj = {"v": value}
        cell_objs.append(cell_obj)
      row_obj = {"c": cell_objs}
      if cp:
        row_obj["p"] = cp
      row_objs.append(row_obj)

    json_obj = {"cols": col_objs, "rows": row_objs}
    if self.custom_properties:
      json_obj["p"] = self.custom_properties

    return json_obj

  def ToJSon(self, columns_order=None, order_by=()):
    """Returns a string that can be used in a JS DataTable constructor.

    This method writes a JSON string that can be passed directly into a Google
    Visualization API DataTable constructor. Use this output if you are
    hosting the visualization HTML on your site, and want to code the data
    table in Python. Pass this string into the
    google.visualization.DataTable constructor, e.g,:
      ... on my page that hosts my visualization ...
      google.setOnLoadCallback(drawTable);
      function drawTable() {
        var data = new google.visualization.DataTable(_my_JSon_string, 0.6);
        myTable.draw(data);
      }

    Args:
      columns_order: Optional. Specifies the order of columns in the
                     output table. Specify a list of all column IDs in the order
                     in which you want the table created.
                     Note that you must list all column IDs in this parameter,
                     if you use it.
      order_by: Optional. Specifies the name of the column(s) to sort by.
                Passed as is to _PreparedData().

    Returns:
      A JSon constructor string to generate a JS DataTable with the data
      stored in the DataTable object.
      Example result (the result is without the newlines):
       {cols: [{id:"a",label:"a",type:"number"},
               {id:"b",label:"b",type:"string"},
              {id:"c",label:"c",type:"number"}],
        rows: [{c:[{v:1},{v:"z"},{v:2}]}, c:{[{v:3,f:"3$"},{v:"w"},{v:null}]}],
        p:    {'foo': 'bar'}}

    Raises:
      DataTableException: The data does not match the type.
    """

    encoder = DataTableJSONEncoder()
    return encoder.encode(
        self._ToJSonObj(columns_order, order_by)).encode("utf-8")

  def ToJSonResponse(self, columns_order=None, order_by=(), req_id=0,
                     response_handler="google.visualization.Query.setResponse"):
    """Writes a table as a JSON response that can be returned as-is to a client.

    This method writes a JSON response to return to a client in response to a
    Google Visualization API query. This string can be processed by the calling
    page, and is used to deliver a data table to a visualization hosted on
    a different page.

    Args:
      columns_order: Optional. Passed straight to self.ToJSon().
      order_by: Optional. Passed straight to self.ToJSon().
      req_id: Optional. The response id, as retrieved by the request.
      response_handler: Optional. The response handler, as retrieved by the
          request.

    Returns:
      A JSON response string to be received by JS the visualization Query
      object. This response would be translated into a DataTable on the
      client side.
      Example result (newlines added for readability):
       google.visualization.Query.setResponse({
          'version':'0.6', 'reqId':'0', 'status':'OK',
          'table': {cols: [...], rows: [...]}});

    Note: The URL returning this string can be used as a data source by Google
          Visualization Gadgets or from JS code.
    """

    response_obj = {
        "version": "0.6",
        "reqId": str(req_id),
        "table": self._ToJSonObj(columns_order, order_by),
        "status": "ok"
    }
    encoder = DataTableJSONEncoder()
    return "%s(%s);" % (response_handler,
                        encoder.encode(response_obj).encode("utf-8"))

  def ToResponse(self, columns_order=None, order_by=(), tqx=""):
    """Writes the right response according to the request string passed in tqx.

    This method parses the tqx request string (format of which is defined in
    the documentation for implementing a data source of Google Visualization),
    and returns the right response according to the request.
    It parses out the "out" parameter of tqx, calls the relevant response
    (ToJSonResponse() for "json", ToCsv() for "csv", ToHtml() for "html",
    ToTsvExcel() for "tsv-excel") and passes the response function the rest of
    the relevant request keys.

    Args:
      columns_order: Optional. Passed as is to the relevant response function.
      order_by: Optional. Passed as is to the relevant response function.
      tqx: Optional. The request string as received by HTTP GET. Should be in
           the format "key1:value1;key2:value2...". All keys have a default
           value, so an empty string will just do the default (which is calling
           ToJSonResponse() with no extra parameters).

    Returns:
      A response string, as returned by the relevant response function.

    Raises:
      DataTableException: One of the parameters passed in tqx is not supported.
    """
    tqx_dict = {}
    if tqx:
      tqx_dict = dict(opt.split(":") for opt in tqx.split(";"))
    if tqx_dict.get("version", "0.6") != "0.6":
      raise DataTableException(
          "Version (%s) passed by request is not supported."
          % tqx_dict["version"])

    if tqx_dict.get("out", "json") == "json":
      response_handler = tqx_dict.get("responseHandler",
                                      "google.visualization.Query.setResponse")
      return self.ToJSonResponse(columns_order, order_by,
                                 req_id=tqx_dict.get("reqId", 0),
                                 response_handler=response_handler)
    elif tqx_dict["out"] == "html":
      return self.ToHtml(columns_order, order_by)
    elif tqx_dict["out"] == "csv":
      return self.ToCsv(columns_order, order_by)
    elif tqx_dict["out"] == "tsv-excel":
      return self.ToTsvExcel(columns_order, order_by)
    else:
      raise DataTableException(
          "'out' parameter: '%s' is not supported" % tqx_dict["out"])

########NEW FILE########
__FILENAME__ = gviz_api_test
#!/usr/bin/python
#
# Copyright (C) 2009 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for the gviz_api module."""

__author__ = "Amit Weinstein"

from datetime import date
from datetime import datetime
from datetime import time
try:
  import json
except ImportError:
  import simplejson as json
import unittest

from gviz_api import DataTable
from gviz_api import DataTableException


class DataTableTest(unittest.TestCase):

  def testCoerceValue(self):
    # We first check that given an unknown type it raises exception
    self.assertRaises(DataTableException,
                      DataTable.CoerceValue, 1, "no_such_type")

    # If we give a type which does not match the value, we expect it to fail
    self.assertRaises(DataTableException,
                      DataTable.CoerceValue, "a", "number")
    self.assertRaises(DataTableException,
                      DataTable.CoerceValue, "b", "timeofday")
    self.assertRaises(DataTableException,
                      DataTable.CoerceValue, 10, "date")

    # A tuple for value and formatted value should be of length 2
    self.assertRaises(DataTableException,
                      DataTable.CoerceValue, (5, "5$", "6$"), "string")

    # Some good examples from all the different types
    self.assertEqual(True, DataTable.CoerceValue(True, "boolean"))
    self.assertEqual(False, DataTable.CoerceValue(False, "boolean"))
    self.assertEqual(True, DataTable.CoerceValue(1, "boolean"))
    self.assertEqual(None, DataTable.CoerceValue(None, "boolean"))
    self.assertEqual((False, u"a"),
                     DataTable.CoerceValue((False, "a"), "boolean"))

    self.assertEqual(1, DataTable.CoerceValue(1, "number"))
    self.assertEqual(1., DataTable.CoerceValue(1., "number"))
    self.assertEqual(-5, DataTable.CoerceValue(-5, "number"))
    self.assertEqual(None, DataTable.CoerceValue(None, "number"))
    self.assertEqual((5, u"5$"),
                     DataTable.CoerceValue((5, "5$"), "number"))

    self.assertEqual("-5", DataTable.CoerceValue(-5, "string"))
    self.assertEqual("abc", DataTable.CoerceValue("abc", "string"))
    self.assertEqual(None, DataTable.CoerceValue(None, "string"))

    self.assertEqual(date(2010, 1, 2),
                     DataTable.CoerceValue(date(2010, 1, 2), "date"))
    self.assertEqual(date(2001, 2, 3),
                     DataTable.CoerceValue(datetime(2001, 2, 3, 4, 5, 6),
                                           "date"))
    self.assertEqual(None, DataTable.CoerceValue(None, "date"))

    self.assertEqual(time(10, 11, 12),
                     DataTable.CoerceValue(time(10, 11, 12), "timeofday"))
    self.assertEqual(time(3, 4, 5),
                     DataTable.CoerceValue(datetime(2010, 1, 2, 3, 4, 5),
                                           "timeofday"))
    self.assertEqual(None, DataTable.CoerceValue(None, "timeofday"))

    self.assertEqual(datetime(2001, 2, 3, 4, 5, 6, 555000),
                     DataTable.CoerceValue(datetime(2001, 2, 3, 4, 5, 6,
                                                    555000),
                                           "datetime"))
    self.assertEqual(None, DataTable.CoerceValue(None, "datetime"))
    self.assertEqual((None, "none"),
                     DataTable.CoerceValue((None, "none"), "string"))

  def testDifferentStrings(self):
    # Checking escaping of strings in JSON output
    the_strings = ["new\nline",
                   r"one\slash",
                   r"two\\slash",
                   u"unicode eng",
                   u"unicode \u05e2\u05d1\u05e8\u05d9\u05ea",
                   u"unicode \u05e2\u05d1\u05e8\u05d9\u05ea".encode("utf-8"),
                   u'"\u05e2\u05d1\\"\u05e8\u05d9\u05ea"']
    table = DataTable([("a", "string")],
                      [[x] for x in the_strings])

    json_obj = json.loads(table.ToJSon())
    for i, row in enumerate(json_obj["rows"]):
      utf8_str = the_strings[i]
      if isinstance(utf8_str, unicode):
        utf8_str = utf8_str.encode("utf-8")

      out_str = row["c"][0]["v"]
      self.assertEqual(out_str.encode("utf-8"), utf8_str)

  def testColumnTypeParser(self):
    # Checking several wrong formats
    self.assertRaises(DataTableException,
                      DataTable.ColumnTypeParser, 5)
    self.assertRaises(DataTableException,
                      DataTable.ColumnTypeParser, ("a", 5, "c"))
    self.assertRaises(DataTableException,
                      DataTable.ColumnTypeParser, ("a", "blah"))
    self.assertRaises(DataTableException,
                      DataTable.ColumnTypeParser, ("a", "number", "c", "d"))

    # Checking several legal formats
    self.assertEqual({"id": "abc", "label": "abc", "type": "string",
                      "custom_properties": {}},
                     DataTable.ColumnTypeParser("abc"))
    self.assertEqual({"id": "abc", "label": "abc", "type": "string",
                      "custom_properties": {}},
                     DataTable.ColumnTypeParser(("abc",)))
    self.assertEqual({"id": "abc", "label": "bcd", "type": "string",
                      "custom_properties": {}},
                     DataTable.ColumnTypeParser(("abc", "string", "bcd")))
    self.assertEqual({"id": "a", "label": "b", "type": "number",
                      "custom_properties": {}},
                     DataTable.ColumnTypeParser(("a", "number", "b")))
    self.assertEqual({"id": "a", "label": "a", "type": "number",
                      "custom_properties": {}},
                     DataTable.ColumnTypeParser(("a", "number")))
    self.assertEqual({"id": "i", "label": "l", "type": "string",
                      "custom_properties": {"key": "value"}},
                     DataTable.ColumnTypeParser(("i", "string", "l",
                                                 {"key": "value"})))

  def testTableDescriptionParser(self):
    # We expect it to fail with empty lists or dictionaries
    self.assertRaises(DataTableException,
                      DataTable.TableDescriptionParser, {})
    self.assertRaises(DataTableException,
                      DataTable.TableDescriptionParser, [])
    self.assertRaises(DataTableException,
                      DataTable.TableDescriptionParser, {"a": []})
    self.assertRaises(DataTableException,
                      DataTable.TableDescriptionParser, {"a": {"b": {}}})

    # We expect it to fail if we give a non-string at the lowest level
    self.assertRaises(DataTableException,
                      DataTable.TableDescriptionParser, {"a": 5})
    self.assertRaises(DataTableException,
                      DataTable.TableDescriptionParser, [("a", "number"), 6])

    # Some valid examples which mixes both dictionaries and lists
    self.assertEqual(
        [{"id": "a", "label": "a", "type": "date",
          "depth": 0, "container": "iter", "custom_properties": {}},
         {"id": "b", "label": "b", "type": "timeofday",
          "depth": 0, "container": "iter", "custom_properties": {}}],
        DataTable.TableDescriptionParser([("a", "date"), ("b", "timeofday")]))

    self.assertEqual(
        [{"id": "a", "label": "a", "type": "string",
          "depth": 0, "container": "dict", "custom_properties": {}},
         {"id": "b", "label": "b", "type": "number",
          "depth": 1, "container": "iter", "custom_properties": {}},
         {"id": "c", "label": "column c", "type": "string",
          "depth": 1, "container": "iter", "custom_properties": {}}],
        DataTable.TableDescriptionParser({"a": [("b", "number"),
                                                ("c", "string", "column c")]}))

    self.assertEqual(
        [{"id": "a", "label": "column a", "type": "number", "depth": 0,
          "container": "dict", "custom_properties": {}},
         {"id": "b", "label": "column b", "type": "string", "depth": 0,
          "container": "dict", "custom_properties": {}}],
        DataTable.TableDescriptionParser({"a": ("number", "column a"),
                                          "b": ("string", "column b")}))

    self.assertEqual(
        [{"id": "a", "label": "column a", "type": "number",
          "depth": 0, "container": "dict", "custom_properties": {}},
         {"id": "b", "label": "b", "type": "number",
          "depth": 1, "container": "dict", "custom_properties": {}},
         {"id": "c", "label": "c", "type": "string",
          "depth": 1, "container": "dict", "custom_properties": {}}],
        DataTable.TableDescriptionParser({("a", "number", "column a"):
                                          {"b": "number", "c": "string"}}))

    self.assertEqual(
        [{"id": "a", "label": "column a", "type": "number",
          "depth": 0, "container": "dict", "custom_properties": {}},
         {"id": "b", "label": "column b", "type": "string",
          "depth": 1, "container": "scalar", "custom_properties": {}}],
        DataTable.TableDescriptionParser({("a", "number", "column a"):
                                          ("b", "string", "column b")}))

    # Cases that might create ambiguity
    self.assertEqual(
        [{"id": "a", "label": "column a", "type": "number", "depth": 0,
          "container": "dict", "custom_properties": {}}],
        DataTable.TableDescriptionParser({"a": ("number", "column a")}))
    self.assertRaises(DataTableException, DataTable.TableDescriptionParser,
                      {"a": ("b", "number")})

    self.assertEqual(
        [{"id": "a", "label": "a", "type": "string", "depth": 0,
          "container": "dict", "custom_properties": {}},
         {"id": "b", "label": "b", "type": "number", "depth": 1,
          "container": "scalar", "custom_properties": {}}],
        DataTable.TableDescriptionParser({"a": ("b", "number", "b", {})}))

    self.assertEqual(
        [{"id": "a", "label": "a", "type": "string", "depth": 0,
          "container": "dict", "custom_properties": {}},
         {"id": "b", "label": "b", "type": "number", "depth": 1,
          "container": "scalar", "custom_properties": {}}],
        DataTable.TableDescriptionParser({("a",): ("b", "number")}))

  def testAppendData(self):
    # We check a few examples where the format of the data does not match the
    # description and hen a few valid examples. The test for the content itself
    # is done inside the ToJSCode and ToJSon functions.
    table = DataTable([("a", "number"), ("b", "string")])
    self.assertEqual(0, table.NumberOfRows())
    self.assertRaises(DataTableException,
                      table.AppendData, [[1, "a", True]])
    self.assertRaises(DataTableException,
                      table.AppendData, {1: ["a"], 2: ["b"]})
    self.assertEquals(None, table.AppendData([[1, "a"], [2, "b"]]))
    self.assertEqual(2, table.NumberOfRows())
    self.assertEquals(None, table.AppendData([[3, "c"], [4]]))
    self.assertEqual(4, table.NumberOfRows())

    table = DataTable({"a": "number", "b": "string"})
    self.assertEqual(0, table.NumberOfRows())
    self.assertRaises(DataTableException,
                      table.AppendData, [[1, "a"]])
    self.assertRaises(DataTableException,
                      table.AppendData, {5: {"b": "z"}})
    self.assertEquals(None, table.AppendData([{"a": 1, "b": "z"}]))
    self.assertEqual(1, table.NumberOfRows())

    table = DataTable({("a", "number"): [("b", "string")]})
    self.assertEqual(0, table.NumberOfRows())
    self.assertRaises(DataTableException,
                      table.AppendData, [[1, "a"]])
    self.assertRaises(DataTableException,
                      table.AppendData, {5: {"b": "z"}})
    self.assertEquals(None, table.AppendData({5: ["z"], 6: ["w"]}))
    self.assertEqual(2, table.NumberOfRows())

    table = DataTable({("a", "number"): {"b": "string", "c": "number"}})
    self.assertEqual(0, table.NumberOfRows())
    self.assertRaises(DataTableException,
                      table.AppendData, [[1, "a"]])
    self.assertRaises(DataTableException,
                      table.AppendData, {1: ["a", 2]})
    self.assertEquals(None, table.AppendData({5: {"b": "z", "c": 6},
                                              7: {"c": 8},
                                              9: {}}))
    self.assertEqual(3, table.NumberOfRows())

  def testToJSCode(self):
    table = DataTable([("a", "number", "A'"), "b\"", ("c", "timeofday")],
                      [[1],
                       [None, "z", time(1, 2, 3)],
                       [(2, "2$"), "w", time(2, 3, 4)]])
    self.assertEqual(3, table.NumberOfRows())
    self.assertEqual((u"var mytab = new google.visualization.DataTable();\n"
                      u"mytab.addColumn(\"number\", \"A'\", \"a\");\n"
                      u"mytab.addColumn(\"string\", \"b\\\"\", \"b\\\"\");\n"
                      u"mytab.addColumn(\"timeofday\", \"c\", \"c\");\n"
                      u"mytab.addRows(3);\n"
                      u"mytab.setCell(0, 0, 1);\n"
                      u"mytab.setCell(1, 1, \"z\");\n"
                      u"mytab.setCell(1, 2, [1,2,3]);\n"
                      u"mytab.setCell(2, 0, 2, \"2$\");\n"
                      u"mytab.setCell(2, 1, \"w\");\n"
                      u"mytab.setCell(2, 2, [2,3,4]);\n"),
                     table.ToJSCode("mytab"))

    table = DataTable({("a", "number"): {"b": "date", "c": "datetime"}},
                      {1: {},
                       2: {"b": date(1, 2, 3)},
                       3: {"c": datetime(1, 2, 3, 4, 5, 6, 555000)},
                       4: {"c": datetime(1, 2, 3, 4, 5, 6)}})
    self.assertEqual(4, table.NumberOfRows())
    self.assertEqual(("var mytab2 = new google.visualization.DataTable();\n"
                      'mytab2.addColumn("datetime", "c", "c");\n'
                      'mytab2.addColumn("date", "b", "b");\n'
                      'mytab2.addColumn("number", "a", "a");\n'
                      'mytab2.addRows(4);\n'
                      'mytab2.setCell(0, 2, 1);\n'
                      'mytab2.setCell(1, 1, new Date(1,1,3));\n'
                      'mytab2.setCell(1, 2, 2);\n'
                      'mytab2.setCell(2, 0, new Date(1,1,3,4,5,6,555));\n'
                      'mytab2.setCell(2, 2, 3);\n'
                      'mytab2.setCell(3, 0, new Date(1,1,3,4,5,6));\n'
                      'mytab2.setCell(3, 2, 4);\n'),
                     table.ToJSCode("mytab2", columns_order=["c", "b", "a"]))

  def testToJSon(self):
    json_obj = {"cols":
                [{"id": "a", "label": "A", "type": "number"},
                 {"id": "b", "label": "b", "type": "string"},
                 {"id": "c", "label": "c", "type": "boolean"}],
                "rows":
                [{"c": [{"v": 1}, None, None]},
                 {"c": [None, {"v": "z"}, {"v": True}]},
                 {"c": [None, {"v": u"\u05d0"}, None]},
                 {"c": [None, {"v": u"\u05d1"}, None]}]}

    table = DataTable([("a", "number", "A"), "b", ("c", "boolean")],
                      [[1],
                       [None, "z", True],
                       [None, u"\u05d0"],
                       [None, u"\u05d1".encode("utf-8")]])
    self.assertEqual(4, table.NumberOfRows())
    self.assertEqual(json.dumps(json_obj,
                                separators=(",", ":"),
                                ensure_ascii=False).encode("utf-8"),
                     table.ToJSon())
    table.AppendData([[-1, "w", False]])
    self.assertEqual(5, table.NumberOfRows())
    json_obj["rows"].append({"c": [{"v": -1}, {"v": "w"}, {"v": False}]})
    self.assertEqual(json.dumps(json_obj,
                                separators=(",", ":"),
                                ensure_ascii=False).encode("utf-8"),
                     table.ToJSon())

    json_obj = {"cols":
                [{"id": "t", "label": "T", "type": "timeofday"},
                 {"id": "d", "label": "d", "type": "date"},
                 {"id": "dt", "label": "dt", "type": "datetime"}],
                "rows":
                [{"c": [{"v": [1, 2, 3]}, {"v": "Date(1,1,3)"}, None]}]}
    table = DataTable({("d", "date"): [("t", "timeofday", "T"),
                                       ("dt", "datetime")]})
    table.LoadData({date(1, 2, 3): [time(1, 2, 3)]})
    self.assertEqual(1, table.NumberOfRows())
    self.assertEqual(json.dumps(json_obj, separators=(",", ":")),
                     table.ToJSon(columns_order=["t", "d", "dt"]))

    json_obj["rows"] = [
        {"c": [{"v": [2, 3, 4], "f": "time 2 3 4"},
               {"v": "Date(2,2,4)"},
               {"v": "Date(1,1,3,4,5,6,555)"}]},
        {"c": [None, {"v": "Date(3,3,5)"}, None]}]

    table.LoadData({date(2, 3, 4): [(time(2, 3, 4), "time 2 3 4"),
                                    datetime(1, 2, 3, 4, 5, 6, 555000)],
                    date(3, 4, 5): []})
    self.assertEqual(2, table.NumberOfRows())

    self.assertEqual(json.dumps(json_obj, separators=(",", ":")),
                     table.ToJSon(columns_order=["t", "d", "dt"]))

    json_obj = {
        "cols": [{"id": "a\"", "label": "a\"", "type": "string"},
                 {"id": "b", "label": "bb\"", "type": "number"}],
        "rows": [{"c": [{"v": "a1"}, {"v": 1}]},
                 {"c": [{"v": "a2"}, {"v": 2}]},
                 {"c": [{"v": "a3"}, {"v": 3}]}]}
    table = DataTable({"a\"": ("b", "number", "bb\"", {})},
                      {"a1": 1, "a2": 2, "a3": 3})
    self.assertEqual(3, table.NumberOfRows())
    self.assertEqual(json.dumps(json_obj, separators=(",", ":")),
                     table.ToJSon())

  def testCustomProperties(self):
    # The json of the initial data we load to the table.
    json_obj = {"cols": [{"id": "a",
                          "label": "A",
                          "type": "number",
                          "p": {"col_cp": "col_v"}},
                         {"id": "b", "label": "b", "type": "string"},
                         {"id": "c", "label": "c", "type": "boolean"}],
                "rows": [{"c": [{"v": 1},
                                None,
                                {"v": None,
                                 "p": {"null_cp": "null_v"}}],
                          "p": {"row_cp": "row_v"}},
                         {"c": [None,
                                {"v": "z", "p": {"cell_cp": "cell_v"}},
                                {"v": True}]},
                         {"c": [{"v": 3}, None, None],
                          "p": {"row_cp2": "row_v2"}}],
                "p": {"global_cp": "global_v"}}
    jscode = ("var mytab = new google.visualization.DataTable();\n"
              "mytab.setTableProperties({\"global_cp\":\"global_v\"});\n"
              "mytab.addColumn(\"number\", \"A\", \"a\");\n"
              "mytab.setColumnProperties(0, {\"col_cp\":\"col_v\"});\n"
              "mytab.addColumn(\"string\", \"b\", \"b\");\n"
              "mytab.addColumn(\"boolean\", \"c\", \"c\");\n"
              "mytab.addRows(3);\n"
              "mytab.setCell(0, 0, 1);\n"
              "mytab.setCell(0, 2, null, null, {\"null_cp\":\"null_v\"});\n"
              "mytab.setRowProperties(0, {\"row_cp\":\"row_v\"});\n"
              "mytab.setCell(1, 1, \"z\", null, {\"cell_cp\":\"cell_v\"});\n"
              "mytab.setCell(1, 2, true);\n"
              "mytab.setCell(2, 0, 3);\n"
              "mytab.setRowProperties(2, {\"row_cp2\":\"row_v2\"});\n")

    table = DataTable([("a", "number", "A", {"col_cp": "col_v"}), "b",
                       ("c", "boolean")],
                      custom_properties={"global_cp": "global_v"})
    table.AppendData([[1, None, (None, None, {"null_cp": "null_v"})]],
                     custom_properties={"row_cp": "row_v"})
    table.AppendData([[None, ("z", None, {"cell_cp": "cell_v"}), True], [3]])
    table.SetRowsCustomProperties(2, {"row_cp2": "row_v2"})
    self.assertEqual(json.dumps(json_obj, separators=(",", ":")),
                     table.ToJSon())
    self.assertEqual(jscode, table.ToJSCode("mytab"))

  def testToCsv(self):
    init_data_csv = "\r\n".join(["A,\"b\"\"\",c",
                                 "1,,",
                                 ",zz'top,true",
                                 ""])
    table = DataTable([("a", "number", "A"), "b\"", ("c", "boolean")],
                      [[(1, "$1")], [None, "zz'top", True]])
    self.assertEqual(init_data_csv, table.ToCsv())
    table.AppendData([[-1, "w", False]])
    init_data_csv = "%s%s\r\n" % (init_data_csv, "-1,w,false")
    self.assertEquals(init_data_csv, table.ToCsv())

    init_data_csv = "\r\n".join([
        "T,d,dt",
        "01:02:03,1901-02-03,",
        "\"time \"\"2 3 4\"\"\",1902-03-04,1901-02-03 04:05:06",
        ",1903-04-05,",
        ""])
    table = DataTable({("d", "date"): [("t", "timeofday", "T"),
                                       ("dt", "datetime")]})
    table.LoadData({date(1901, 2, 3): [time(1, 2, 3)],
                    date(1902, 3, 4): [(time(2, 3, 4), 'time "2 3 4"'),
                                       datetime(1901, 2, 3, 4, 5, 6)],
                    date(1903, 4, 5): []})
    self.assertEqual(init_data_csv, table.ToCsv(columns_order=["t", "d", "dt"]))

  def testToTsvExcel(self):
    table = DataTable({("d", "date"): [("t", "timeofday", "T"),
                                       ("dt", "datetime")]})
    table.LoadData({date(1901, 2, 3): [time(1, 2, 3)],
                    date(1902, 3, 4): [(time(2, 3, 4), 'time "2 3 4"'),
                                       datetime(1901, 2, 3, 4, 5, 6)],
                    date(1903, 4, 5): []})
    self.assertEqual(table.ToCsv().replace(",", "\t").encode("UTF-16LE"),
                     table.ToTsvExcel())

  def testToHtml(self):
    html_table_header = "<html><body><table border=\"1\">"
    html_table_footer = "</table></body></html>"
    init_data_html = html_table_header + (
        "<thead><tr>"
        "<th>A&lt;</th><th>b&gt;</th><th>c</th>"
        "</tr></thead>"
        "<tbody>"
        "<tr><td>$1</td><td></td><td></td></tr>"
        "<tr><td></td><td>&lt;z&gt;</td><td>true</td></tr>"
        "</tbody>") + html_table_footer
    table = DataTable([("a", "number", "A<"), "b>", ("c", "boolean")],
                      [[(1, "$1")], [None, "<z>", True]])
    self.assertEqual(init_data_html.replace("\n", ""), table.ToHtml())

    init_data_html = html_table_header + (
        "<thead><tr>"
        "<th>T</th><th>d</th><th>dt</th>"
        "</tr></thead>"
        "<tbody>"
        "<tr><td>01:02:03</td><td>0001-02-03</td><td></td></tr>"
        "<tr><td>time 2 3 4</td><td>0002-03-04</td>"
        "<td>0001-02-03 04:05:06</td></tr>"
        "<tr><td></td><td>0003-04-05</td><td></td></tr>"
        "</tbody>") + html_table_footer
    table = DataTable({("d", "date"): [("t", "timeofday", "T"),
                                       ("dt", "datetime")]})
    table.LoadData({date(1, 2, 3): [time(1, 2, 3)],
                    date(2, 3, 4): [(time(2, 3, 4), "time 2 3 4"),
                                    datetime(1, 2, 3, 4, 5, 6)],
                    date(3, 4, 5): []})
    self.assertEqual(init_data_html.replace("\n", ""),
                     table.ToHtml(columns_order=["t", "d", "dt"]))

  def testOrderBy(self):
    data = [("b", 3), ("a", 3), ("a", 2), ("b", 1)]
    description = ["col1", ("col2", "number", "Second Column")]
    table = DataTable(description, data)

    table_num_sorted = DataTable(description,
                                 sorted(data, key=lambda x: (x[1], x[0])))

    table_str_sorted = DataTable(description,
                                 sorted(data, key=lambda x: x[0]))

    table_diff_sorted = DataTable(description,
                                  sorted(sorted(data, key=lambda x: x[1]),
                                         key=lambda x: x[0], reverse=True))

    self.assertEqual(table_num_sorted.ToJSon(),
                     table.ToJSon(order_by=("col2", "col1")))
    self.assertEqual(table_num_sorted.ToJSCode("mytab"),
                     table.ToJSCode("mytab", order_by=("col2", "col1")))

    self.assertEqual(table_str_sorted.ToJSon(), table.ToJSon(order_by="col1"))
    self.assertEqual(table_str_sorted.ToJSCode("mytab"),
                     table.ToJSCode("mytab", order_by="col1"))

    self.assertEqual(table_diff_sorted.ToJSon(),
                     table.ToJSon(order_by=[("col1", "desc"), "col2"]))
    self.assertEqual(table_diff_sorted.ToJSCode("mytab"),
                     table.ToJSCode("mytab",
                                    order_by=[("col1", "desc"), "col2"]))

  def testToJSonResponse(self):
    description = ["col1", "col2", "col3"]
    data = [("1", "2", "3"), ("a", "b", "c"), ("One", "Two", "Three")]
    req_id = 4
    table = DataTable(description, data)

    start_str_default = r"google.visualization.Query.setResponse"
    start_str_handler = r"MyHandlerFunction"

    json_str = table.ToJSon().strip()

    json_response = table.ToJSonResponse(req_id=req_id)

    self.assertEquals(json_response.find(start_str_default + "("), 0)

    json_response_obj = json.loads(json_response[len(start_str_default) + 1:-2])
    self.assertEquals(json_response_obj["table"], json.loads(json_str))
    self.assertEquals(json_response_obj["version"], "0.6")
    self.assertEquals(json_response_obj["reqId"], str(req_id))
    self.assertEquals(json_response_obj["status"], "ok")

    json_response = table.ToJSonResponse(req_id=req_id,
                                         response_handler=start_str_handler)

    self.assertEquals(json_response.find(start_str_handler + "("), 0)
    json_response_obj = json.loads(json_response[len(start_str_handler) + 1:-2])
    self.assertEquals(json_response_obj["table"], json.loads(json_str))

  def testToResponse(self):
    description = ["col1", "col2", "col3"]
    data = [("1", "2", "3"), ("a", "b", "c"), ("One", "Two", "Three")]
    table = DataTable(description, data)

    self.assertEquals(table.ToResponse(), table.ToJSonResponse())
    self.assertEquals(table.ToResponse(tqx="out:csv"), table.ToCsv())
    self.assertEquals(table.ToResponse(tqx="out:html"), table.ToHtml())
    self.assertRaises(DataTableException, table.ToResponse, tqx="version:0.1")
    self.assertEquals(table.ToResponse(tqx="reqId:4;responseHandler:handle"),
                      table.ToJSonResponse(req_id=4, response_handler="handle"))
    self.assertEquals(table.ToResponse(tqx="out:csv;reqId:4"), table.ToCsv())
    self.assertEquals(table.ToResponse(order_by="col2"),
                      table.ToJSonResponse(order_by="col2"))
    self.assertEquals(table.ToResponse(tqx="out:html",
                                       columns_order=("col3", "col2", "col1")),
                      table.ToHtml(columns_order=("col3", "col2", "col1")))
    self.assertRaises(ValueError, table.ToResponse, tqx="SomeWrongTqxFormat")
    self.assertRaises(DataTableException, table.ToResponse, tqx="out:bad")


if __name__ == "__main__":
  unittest.main()

########NEW FILE########
__FILENAME__ = db_models
#!/usr/bin/python2.7
#
# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Models for the Google Analytics superProxy.

  JsonQueryProperty: Property to store API Responses.
  GaSuperProxyUser: Represents the users of the service.
  GaSuperProxyUserInvitation: Represents an user invited to the service.
  ApiQuery: Models the API Queries created by users.
  ApiQueryResponse: Represents a successful response from an API.
  ApiErrorResponse: Represents an error response from an API.
"""

__author__ = 'pete.frisella@gmail.com (Pete Frisella)'

import json

from controllers.util import models_helper

from google.appengine.ext import db


class JsonQueryProperty(db.Property):
  """Property to store/retrieve queries and responses in JSON format."""
  data_type = db.BlobProperty()

  # pylint: disable-msg=C6409
  def get_value_for_datastore(self, model_instance):
    value = super(JsonQueryProperty, self).get_value_for_datastore(
        model_instance)
    return db.Blob(json.dumps(value))

  def make_value_from_datastore(self, value):
    if value is None:
      return None
    value = json.loads(str(value))
    return super(JsonQueryProperty, self).make_value_from_datastore(value)


class GaSuperProxyUser(db.Model):
  """Models a GaSuperProxyUser and user settings."""
  email = db.StringProperty()
  nickname = db.StringProperty()
  ga_refresh_token = db.StringProperty()
  ga_access_token = db.StringProperty()
  ga_token_expiry = db.DateTimeProperty()


class GaSuperProxyUserInvitation(db.Model):
  """Models a user invited to use the service."""
  email = db.StringProperty()
  issued = db.DateTimeProperty()


class ApiQuery(db.Model):
  """Models an API Query."""
  user = db.ReferenceProperty(GaSuperProxyUser,
                              required=True,
                              collection_name='api_queries')
  name = db.StringProperty(required=True)
  request = JsonQueryProperty(required=True)
  refresh_interval = db.IntegerProperty(required=True, default=3600)
  in_queue = db.BooleanProperty(required=True, default=False)
  is_active = db.BooleanProperty(required=True, default=False)
  is_scheduled = db.BooleanProperty(required=True, default=False)
  modified = db.DateTimeProperty()

  @property
  def is_abandoned(self):
    """Determines whether the API Query is considered abandoned."""
    return models_helper.IsApiQueryAbandoned(self)

  @property
  def is_error_limit_reached(self):
    """Returns True if the API Query has hit error limits."""
    return models_helper.IsErrorLimitReached(self)

  @property
  def last_request(self):
    """Returns the timestamp of the last request."""
    return models_helper.GetApiQueryLastRequest(str(self.key()))

  @property
  def last_request_timedelta(self):
    """Returns how long since the API Query response was last requested."""
    return models_helper.GetLastRequestTimedelta(self)

  @property
  def modified_timedelta(self, from_time=None):
    """Returns how long since the API Query was updated."""
    return models_helper.GetModifiedTimedelta(self, from_time)

  @property
  def request_count(self):
    """Reuturns the request count for the API Query."""
    return models_helper.GetApiQueryRequestCount(str(self.key()))


class ApiQueryResponse(db.Model):
  """Models an API Response."""
  api_query = db.ReferenceProperty(ApiQuery,
                                   required=True,
                                   collection_name='api_query_responses')
  content = JsonQueryProperty(required=True)
  modified = db.DateTimeProperty(required=True)


class ApiErrorResponse(db.Model):
  """Models an API Query Error Response."""
  api_query = db.ReferenceProperty(ApiQuery,
                                   required=True,
                                   collection_name='api_query_errors')
  content = JsonQueryProperty(required=True)
  timestamp = db.DateTimeProperty(required=True)

########NEW FILE########
