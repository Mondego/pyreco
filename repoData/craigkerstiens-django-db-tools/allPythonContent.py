__FILENAME__ = middleware
"""
Database read only mode middlware
"""
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
import os

class ReadOnlyMiddleware(object):
    """
    Two supported modes.
    
    Anonymous User mode - results in effect of all users being logged out
    Get Only mode - results in no posts being allowed. If your site requires 
    POSTs to update data then this should be sufficient.
    """
    def process_request(self, request):
        anon_mode =  os.environ.get('READ_ONLY_MODE', False)
        get_mode =  os.environ.get('GET_ONLY_MODE', False)

        if anon_mode:
            request.user = AnonymousUser()
        if get_mode:
            request.method = 'GET'        

########NEW FILE########
