"""Relevant result:write"""
from django.http import HttpResponse
from authomatic import Authomatic
from authomatic.adapters import DjangoAdapter
from config import CONFIG

authomatic = Authomatic(CONFIG, 'a super secret random string')

def login(request, provider_name):
    response = HttpResponse()
   result = authomatic.login(DjangoAdapter(request, response), provider_name)
if result:
        Response.
