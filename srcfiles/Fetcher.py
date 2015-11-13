'''
@Author: Rohan Achar ra.rohan@gmail.com
'''
import socket, base64
try:
    from urllib2 import Request, urlopen, HTTPError, URLError
    from urlparse import urlparse, parse_qs
    import httplib
except ImportError:
    from urllib.request import Request, urlopen, HTTPError, URLError
    from urllib.parse import urlparse, parse_qs
    from http import client as httplib

from threading import *


class Fetcher:
    def __init__(self, config):
        self.config = config

    #url is assumed to be crawlable
    def FetchUrl(self, url, depth, urlManager, retry = 0):
        urlreq = Request(url, None, {"User-Agent" : self.config.UserAgentString})
        parsed = urlparse(url)
        if parsed.hostname in self.config.GetAuthenticationData():
            username, password = self.config.GetAuthenticationData()[parsed.hostname]
            base64string = base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
            urlreq.add_header("Authorization", "Basic %s" % base64string)
        try:
            urldata = urlopen(urlreq, timeout = self.config.UrlFetchTimeOut)
            try:

                size = int(urldata.info().getheaders("Content-Length")[0])
            except AttributeError:
                failobj = None
                sizestr = urldata.info().get("Content-Length", failobj)
                if sizestr:
                    size = int(sizestr)
                else:
                    size = -1
            except IndexError:
                size = -1

            return size < self.config.MaxPageSize and urldata.code > 199 and urldata.code < 300 and self.__ProcessUrlData(url, urldata.read(), depth, urlManager)
        except HTTPError:
            return False
        except URLError:
            return False
        except httplib.HTTPException:
            return False
        except socket.error:
            if (retry == self.config.MaxRetryDownloadOnFail):
                return False
            print ("Retrying " + url + " " + str(retry + 1) + " time")
            return self.FetchUrl(url, depth, urlManager, retry + 1)

    def __ProcessUrlData(self, url, htmlData, depth, urlManager):
        textData = self.config.GetTextData(htmlData, forUrl=url)
        links = []
        if (self.config.ExtractNextLinks(url, htmlData, links)):
            urlManager.AddOutput({"html": htmlData, "text": textData, "url": url})
            for link in links:
                urlManager.AddToFrontier(link, depth + 1)
            return True
        return False