__FILENAME__ = add_a_cat
#!/usr/bin/python

# Copyright (C) 2013 Gerwin Sturm, FoldedSoft e.U.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Methods for Add a Cat to that service"""

__author__ = 'scarygami@gmail.com (Gerwin Sturm)'

from service import upload
from utils import base_url

import logging
import Image
import cStringIO
import random

__all__ = ["handle_item", "CONTACTS", "WELCOMES"]

"""Contacts that need to registered when the user connects to this service"""
CONTACTS = [
    {
        "acceptTypes": "image/*",
        "id": "add_a_cat",
        "displayName": "Add a Cat to that",
        "imageUrls": [base_url + "/images/cat.png"]
    }
]

"""Welcome message cards that are sent when the user first connects to this service"""
WELCOMES = [
    {
        "html": ("<article class=\"photo\">"
                 "  <img src=\"" + base_url + "/images/cat.png\" width=\"100%\" height=\"100%\">"
                 "  <div class=\"photo-overlay\"></div>"
                 "  <section>"
                 "    <p class=\"text-auto-size\">Welcome to Add a Cat!</p>"
                 "  </section>"
                 "</article>")
    }
]

_NUM_CATS = 6


def handle_item(item, notification, service, test):
    """Callback for Timeline updates."""

    if "userActions" in notification:
        for action in notification["userActions"]:
            if "type" in action and action["type"] == "SHARE":
                break
        else:
            # No SHARE action
            return
    else:
        # No SHARE action
        return

    if "recipients" in item:
        for rec in item["recipients"]:
            if rec["id"] == "add_a_cat":
                break
        else:
            # Item not meant for this service
            return
    else:
        # Item not meant for this service
        return

    imageId = None
    if "attachments" in item:
        for att in item["attachments"]:
            if att["contentType"].startswith("image/"):
                imageId = att["id"]
                break

    if imageId is None:
        logging.info("No suitable attachment")
        return

    attachment_metadata = service.timeline().attachments().get(
        itemId=item["id"], attachmentId=imageId).execute()
    content_url = attachment_metadata.get("contentUrl")
    resp, content = service._http.request(content_url)

    if resp.status != 200:
        logging.info("Couldn't fetch attachment")

    tempimg = cStringIO.StringIO(content)
    im = Image.open(tempimg)

    cat = random.randint(1, _NUM_CATS)
    cat_image = Image.open("res/cat%s.png" % cat)

    zoom = im.size[0] / 640

    cat_image.resize((cat_image.size[0] * zoom, cat_image.size[1] * zoom), Image.ANTIALIAS)

    x = random.randint(0, im.size[0] - cat_image.size[0])
    y = random.randint(0, im.size[1] - cat_image.size[1])

    im.paste(cat_image, (x, y), cat_image)

    f = cStringIO.StringIO()
    im.save(f, "JPEG")
    content = f.getvalue()
    f.close()

    new_item = {}
    new_item["menuItems"] = [{"action": "SHARE"}]

    result = upload.multipart_insert(new_item, content, "image/jpeg", service, test)
    logging.info(result)

########NEW FILE########
__FILENAME__ = check_in
#!/usr/bin/python

# Copyright (C) 2013 Gerwin Sturm, FoldedSoft e.U.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Methods for Check in service"""

from utils import JINJA
from utils import API_KEY
from utils import base_url
from utils import build_service_from_service

import json
import logging
import urllib2
import webapp2

from apiclient.errors import HttpError

__author__ = 'scarygami@gmail.com (Gerwin Sturm)'

__all__ = ["handle_item", "handle_location", "WELCOMES", "ROUTES"]


"""Welcome message cards that are sent when the user first connects to this service"""
WELCOMES = [
    {
        "html": ("<article class=\"photo\">"
                 "  <img src=\"glass://map?w=640&h=360&zoom=1\" width=\"100%\" height=\"100%\">"
                 "  <div class=\"photo-overlay\"></div>"
                 "  <section>"
                 "    <p class=\"text-auto-size\">Welcome to Check-in</p>"
                 "  </section>"
                 "</article>")
    }
]

_BUNDLE_ID = "checkin_service_123"
_ACTION_ID = "CHECKIN"


def handle_location(location, notification, service, test):
    """Callback for Location updates."""

    if not "longitude" in location or not "latitude" in location:
        # Incomplete location information
        return
    
    request_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    request_url += "?sensor=false&key=%s" % API_KEY
    request_url += "&location=%s,%s" % (location["latitude"], location["longitude"])
    request_url += "&radius=1000"
    request_url += "&types=food"

    try:
        places = json.load(urllib2.urlopen(request_url))
    except urllib2.URLError as e:
        # Couldn't retrieve results
        logging.info(e)
        return
        
    if not "results" in places or len(places["results"]) == 0:
        # No data retrieved
        if "status" in places:
            logging.info(places["status"])
        return

    # 1. retrieve current bundle cards and delete non-cover cards
    current_cards = service.timeline().list(bundleId=_BUNDLE_ID).execute()

    bundleCoverId = None
    if "items" in current_cards:
        for card in current_cards["items"]:
            if "isBundleCover" in card and card["isBundleCover"] == True:
                bundleCoverId = card["id"]
                break
               
        for card in current_cards["items"]:
            if bundleCoverId is None or card["id"] != bundleCoverId:
                # delete old cards
                service.timeline().delete(id=card["id"]).execute()
                
    # 2. create or update cover card
    map = "glass://map?w=640&h=360&"
    map += "marker=0;%s,%s" % (location["latitude"], location["longitude"])
    i = 1
    for place in places["results"]:
        map += "&marker=%s;%s,%s" % (i, place["geometry"]["location"]["lat"], place["geometry"]["location"]["lng"])
        i = i + 1
        if i > 10:
            break

    count = i - 1
    html = "<article class=\"photo\">"
    html += "<img src=\"%s\" width=\"100%%\" height=\"100%%\">" % map
    html += "<div class=\"photo-overlay\"></div>"
    html += "<footer><div>%s place%s nearby</div></footer>" % (count, "" if count == 1 else "s")
    html += "</article>"

    if bundleCoverId is None:
        body = {}
        body["html"] = html
        body["bundleId"] = _BUNDLE_ID
        body["isBundleCover"] = True
        result = service.timeline().insert(body=body).execute()
        logging.info(result)
    else:
        result = service.timeline().update(id=bundleCoverId, body={"html": html}).execute()
        logging.info(result)
    
    # 3. create up to 10 detailed cards
    i = 1
    
    checkinAction = {}
    checkinAction["action"] = "CUSTOM"
    checkinAction["id"] = _ACTION_ID
    actionValue = {}
    actionValue["state"] = "DEFAULT"
    actionValue["displayName"] = "Check-in"
    actionValue["iconUrl"] = base_url + "/glass/images/success.png"
    checkinAction["values"] = [actionValue]

    for place in places["results"]:
        body = {}
        map = "glass://map?w=330&h=240&"
        map += "marker=0;%s,%s" % (location["latitude"], location["longitude"])
        map += "&marker=1;%s,%s" % (place["geometry"]["location"]["lat"], place["geometry"]["location"]["lng"])
        html = "<article><figure>"
        
        if "name" in place:
            html += "<div style=\"margin-top: 40px;\"><p class=\"text-small align-center\">%s</p></div>" % place["name"]

        html += "</figure>"
        html += "<section><img src=\"%s\" width=\"330\" height=\"240\"></section></article>" % map
        
        body["html"] = html
        body["bundleId"] = _BUNDLE_ID
        body["isBundleCover"] = False
        body["location"] = {}
        body["location"]["latitude"] = place["geometry"]["location"]["lat"]
        body["location"]["longitude"] = place["geometry"]["location"]["lng"]
        body["sourceItemId"] = place["reference"]
        body["canonicalUrl"] = "%s/checkin/place/%s" % (base_url, place["reference"])
        
        body["menuItems"] = []
        body["menuItems"].append({"action": "NAVIGATE"})
        body["menuItems"].append(checkinAction)
        
        result = service.timeline().insert(body=body).execute()

        i = i + 1
        if i > 10:
            break    

    return

    
def handle_item(item, notification, service, test):
    """Callback for Timeline updates."""

    if "userActions" in notification:
        for action in notification["userActions"]:
            if "type" in action and "payload" in action and action["type"] == "CUSTOM" and action["payload"] == _ACTION_ID:
                break
        else:
            # No appropriate CUSTOM action
            return
    else:
        # No CUSTOM action
        return

    if not "canonicalUrl" in item:
        # No appropriate item
        return
            
    plus = build_service_from_service(service, "plus", "v1")

    body = {}
    body["type"] = "http://schemas.google.com/CheckInActivity"
    body["target"] = {}
    body["target"]["url"] = item["canonicalUrl"]
    
    try:
        result = plus.moments().insert(userId="me", collection="vault", body=body).execute()
        logging.info(result)
    except HttpError as e:
        logging.info(e)


class PlaceHandler(webapp2.RequestHandler):
    """Handler to create dummy pages from Google Places API result,
    so those pages can be added as App Activities"""

    def get(self, place_id):
    
        template = JINJA.get_template("demos/templates/place.html")
        request_url = "https://maps.googleapis.com/maps/api/place/details/json?reference=" + place_id + "&sensor=false&key=" + API_KEY

        try:
            result = json.load(urllib2.urlopen(request_url))
        except urllib2.URLError as e:
            logging.info(e)
            self.response.out.write(template.render({"chk_place": False, "chk_error": True, "error": "Couldn't access Places API"}))
            return

        if "result" in result:
            self.response.out.write(template.render({"chk_place": True, "place": result["result"]}))
        else:
            self.response.out.write(template.render({"chk_place": False, "chk_error": True, "error": result["status"]}))


ROUTES = [(r"/checkin/place/(.+)", PlaceHandler)]

########NEW FILE########
__FILENAME__ = friend_finder
#!/usr/bin/python

# Copyright (C) 2013 Gerwin Sturm, FoldedSoft e.U.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Methods for Friend finder service"""

__author__ = 'scarygami@gmail.com (Gerwin Sturm)'

__all__ = ["handle_location", "WELCOMES"]


"""Welcome message cards that are sent when the user first connects to this service"""
WELCOMES = [
    {
        "html": ("<article class=\"photo\">"
                 "  <img src=\"glass://map?w=640&h=360&zoom=1\" width=\"100%\" height=\"100%\">"
                 "  <div class=\"photo-overlay\"></div>"
                 "  <section>"
                 "    <p class=\"text-auto-size\">Welcome to Friend Finder</p>"
                 "  </section>"
                 "</article>")
    }
]


def handle_location(item, notification, service, test):
    """Callback for Location updates."""

    """
    Card layout for cover:
        <article class="photo">
            <img src="glass://map?w=640&h=360&marker=0;48.20887,16.3708&marker=1;48.20949,16.37143&marker=2;48.20903,16.36924&marker=3;48.20772,16.37036&marker=4;48.20753,16.36954" width="100%" height="100%">
            <div class="photo-overlay"></div>
            <footer><div>4 friends nearby</div></footer>
        </article>

    Card layout for detailed card:
        <article>
            <figure>
                <img src="https://lh3.googleusercontent.com/-khaIYLifQik/AAAAAAAAAAI/AAAAAAAA3bA/CWAtORun9is/photo.jpg?sz=240" width="240">
                <div><p class="text-small align-center">Gerwin Sturm</p></div>
            </figure>
            <section>
                <img src="glass://map?w=330&h=240&marker=0;48.20887,16.3708&marker=1;48.20949,16.37143" width="330" height="240">
            </section>
        </article>
    """

    # TODO: implement

    return

########NEW FILE########
__FILENAME__ = hodor
#!/usr/bin/python

# Copyright (C) 2013 Gerwin Sturm, FoldedSoft e.U.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Methods for Hodor service"""

__author__ = 'scarygami@gmail.com (Gerwin Sturm)'

from utils import base_url

import logging
import random

__all__ = ["handle_item", "CONTACTS", "WELCOMES"]

"""Contacts that need to registered when the user connects to this service"""
CONTACTS = [
    {
        "id": "hodor",
        "displayName": "Hodor",
        "imageUrls": [base_url + "/images/hodor.jpg"],
        "acceptCommands": [{
            "type": "POST_AN_UPDATE"
        }]
    }
]

"""
Welcome message cards that are sent when the user first connects
to this service
"""
WELCOMES = [
    {
        "html": ("<article class=\"photo\">"
                 "  <img src=\"" + base_url + "/images/hodor.jpg\""
                 "       width=\"100%\" height=\"100%\">"
                 "  <div class=\"photo-overlay\"></div>"
                 "  <section>"
                 "    <p class=\"text-auto-size\">Hodor!</p>"
                 "  </section>"
                 "</article>"),
        "menuItems": [{
            "action": "REPLY"
        }],
        "creator": {
            "id": "hodor"
        }
    }
]

"""
Possible responses to messages
"""
RESPONSES = [
    {
        "text": "Hodor!",
        "image": "hodor1.jpg"
    },
    {
        "text": "Hodor?",
        "image": "hodor2.jpg"
    },
    {
        "text": "Hodor...",
        "image": "hodor3.jpg"
    },
    {
        "text": "Hodor.",
        "image": "hodor4.jpg"
    },
]


def handle_item(item, notification, service, test):
    """Callback for Timeline updates."""

    if "userActions" in notification:
        for action in notification["userActions"]:
            if ("type" in action and
               (action["type"] == "LAUNCH" or action["type"] == "REPLY")):
                break
        else:
            # No SHARE action
            return
    else:
        # No SHARE action
        return

    if "recipients" in item:
        for rec in item["recipients"]:
            if rec["id"] == "hodor":
                break
        else:
            # Item not meant for this service
            return
    else:
        # Item not meant for this service
        return

    hodor = random.randint(0, len(RESPONSES) - 1)

    response = {
        "html": ("<article class=\"photo\">"
                 "  <img src=\"" + base_url + "/images/" + RESPONSES[hodor]["image"] + "\""
                 "       width=\"100%\" height=\"100%\">"
                 "  <div class=\"photo-overlay\"></div>"
                 "  <section>"
                 "    <p class=\"text-auto-size\">" + RESPONSES[hodor]["text"] + "</p>"
                 "  </section>"
                 "</article>"),
        "menuItems": [{
            "action": "REPLY"
        }],
        "creator": {
            "id": "hodor"
        }
    }

    if "inReplyTo" in item:
        result = service.timeline().update(id=item["inReplyTo"], body=response).execute()
    else:
        result = service.timeline().insert(body=response).execute()
    logging.info(result)

    # Delete reply card
    result = service.timeline().delete(id=item["id"]).execute()

########NEW FILE########
__FILENAME__ = instaglass
#!/usr/bin/python

# Copyright (C) 2013 Gerwin Sturm, FoldedSoft e.U.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Methods for Instaglass service"""

__author__ = 'scarygami@gmail.com (Gerwin Sturm)'

from service import upload
from utils import base_url

import logging
import Image
import ImageOps
import cStringIO

__all__ = ["handle_item", "CONTACTS", "WELCOMES"]

"""Contacts that need to registered when the user connects to this service"""
CONTACTS = [
    {
        "acceptTypes": "image/*",
        "id": "instaglass_sepia",
        "displayName": "Sepia",
        "imageUrls": [base_url + "/images/sepia.jpg"]
    }
]

"""Welcome message cards that are sent when the user first connects to this service"""
WELCOMES = [
    {
        "html": ("<article class=\"photo\">"
                 "  <img src=\"" + base_url + "/images/sepia.jpg\" width=\"100%\" height=\"100%\">"
                 "  <div class=\"photo-overlay\"></div>"
                 "  <section>"
                 "    <p class=\"text-auto-size\">Welcome to Instaglass!</p>"
                 "  </section>"
                 "</article>")
    }
]


def _make_linear_ramp(white):
    """ generate a palette in a format acceptable for `putpalette`, which
        expects [r,g,b,r,g,b,...]
    """
    ramp = []
    r, g, b = white
    for i in range(255):
        ramp.extend((r*i/255, g*i/255, b*i/255))
    return ramp


def _apply_sepia_filter(image):
    """ Apply a sepia-tone filter to the given PIL Image
        Based on code at: http://effbot.org/zone/pil-sepia.htm
    """
    # make sepia ramp (tweak color as necessary)
    sepia = _make_linear_ramp((255, 240, 192))

    # convert to grayscale
    orig_mode = image.mode
    if orig_mode != "L":
        image = image.convert("L")

    # apply contrast enhancement here, e.g.
    image = ImageOps.autocontrast(image)

    # apply sepia palette
    image.putpalette(sepia)

    # convert back to its original mode
    if orig_mode != "L":
        image = image.convert(orig_mode)

    return image


def handle_item(item, notification, service, test):
    """Callback for Timeline updates."""

    if "userActions" in notification:
        for action in notification["userActions"]:
            if "type" in action and action["type"] == "SHARE":
                break
        else:
            # No SHARE action
            return
    else:
        # No SHARE action
        return
    
    if "recipients" in item:
        for rec in item["recipients"]:
            if rec["id"] == "instaglass_sepia":
                break
        else:
            # Item not meant for this service
            return
    else:
        # Item not meant for this service
        return

    imageId = None
    if "attachments" in item:
        for att in item["attachments"]:
            if att["contentType"].startswith("image/"):
                imageId = att["id"]
                break

    if imageId is None:
        logging.info("No suitable attachment")
        return

    attachment_metadata = service.timeline().attachments().get(
        itemId=item["id"], attachmentId=imageId).execute()
    content_url = attachment_metadata.get("contentUrl")
    resp, content = service._http.request(content_url)

    if resp.status != 200:
        logging.info("Couldn't fetch attachment")

    tempimg = cStringIO.StringIO(content)
    im = Image.open(tempimg)
    new_im = _apply_sepia_filter(im)

    f = cStringIO.StringIO()
    new_im.save(f, "JPEG")
    content = f.getvalue()
    f.close()

    new_item = {}
    new_item["menuItems"] = [{"action": "SHARE"}]

    result = upload.multipart_insert(new_item, content, "image/jpeg", service, test)
    logging.info(result)

########NEW FILE########
__FILENAME__ = glass
#!/usr/bin/python

# Copyright (C) 2013 Gerwin Sturm, FoldedSoft e.U.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
RequestHandlers for Glass emulator

Renders the glass emulator and handles authentication and setting up
push notifications via the Channel API

"""

__author__ = 'scarygami@gmail.com (Gerwin Sturm)'

import utils

import httplib2
import json
import logging
import random
import string

from google.appengine.api import channel
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError


class GlassHandler(utils.BaseHandler):
    """Renders the Glass emulator"""

    def get(self):
        template = utils.JINJA.get_template("emulator/templates/glass.html")
        state = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))
        self.session["state"] = state
        self.session["credentials"] = None
        self.response.out.write(template.render(
            {
                "state": state,
                "client_id": utils.CLIENT_ID,
                "discovery_url": utils.discovery_url
            }
        ))


class GlassConnectHandler(utils.BaseHandler):
    """Handles connection requests coming from the emulator"""

    def post(self):
        """
        Exchange the one-time authorization code for a token and verify user.
        Return a channel token for push notifications on success
        """

        self.response.content_type = "application/json"

        state = self.request.get("state")
        gplus_id = self.request.get("gplus_id")
        code = self.request.body

        if state != self.session.get("state"):
            self.response.status = 401
            self.response.out.write(utils.createError(401, "Invalid state parameter"))
            return

        try:
            oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
            oauth_flow.redirect_uri = 'postmessage'
            credentials = oauth_flow.step2_exchange(code)
        except FlowExchangeError:
            self.response.status = 401
            self.response.out.write(utils.createError(401, "Failed to upgrade the authorization code."))
            return

        # Check that the access token is valid.
        access_token = credentials.access_token
        url = ("https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s" % access_token)
        h = httplib2.Http()
        result = json.loads(h.request(url, 'GET')[1])

        # If there was an error in the access token info, abort.
        if result.get("error") is not None:
            self.response.status = 500
            self.response.out.write(json.dumps(result.get("error")))
            return

        # Verify that the access token is used for the intended user.
        if result["user_id"] != gplus_id:
            self.response.status = 401
            self.response.out.write(utils.createError(401, "Token's user ID doesn't match given user ID."))
            return

        # Verify that the access token is valid for this app.
        if result['issued_to'] != utils.CLIENT_ID:
            self.response.status = 401
            self.response.out.write(utils.createError(401, "Token's client ID does not match the app's client ID"))
            return

        token = channel.create_channel(result["email"])

        self.session["credentials"] = credentials

        self.response.status = 200
        self.response.out.write(utils.createMessage({"token": token}))


class AttachmentHandler(utils.BaseHandler):
    """Retrieves an attachment using the current user's credentials"""

    def get(self, timelineId, attachmentId):
        credentials = self.session.get("credentials")
        if credentials is None:
            self.response.content_type = "application/json"
            self.response.status = 401
            self.response.out.write(utils.createError(401, "Invalid credentials."))
            return

        http = httplib2.Http()
        http = credentials.authorize(http)
        http.timeout = 60

        resp, content = http.request("%s/upload/mirror/v1/timeline/%s/attachments/%s" % (utils.base_url, timelineId, attachmentId))
        if resp.status == 200:
            self.response.content_type = resp["content-type"]
            self.response.out.write(content)
        else:
            self.response.content_type = "application/json"
            self.response.status = resp.status
            self.response.out.write(utils.createError(resp.status, "Unable to retrieve attachment."))


GLASS_ROUTES = [
    (r"/glass/attachment/(.*)/(.*)", AttachmentHandler),
    ("/glass/connect", GlassConnectHandler),
    ("/glass/", GlassHandler)
]

########NEW FILE########
__FILENAME__ = channel
"""Channel notifications support.

Classes and functions to support channel subscriptions and notifications
on those channels.

Notes:
  - This code is based on experimental APIs and is subject to change.
  - Notification does not do deduplication of notification ids, that's up to
    the receiver.
  - Storing the Channel between calls is up to the caller.


Example setting up a channel:

  # Create a new channel that gets notifications via webhook.
  channel = new_webhook_channel("https://example.com/my_web_hook")

  # Store the channel, keyed by 'channel.id'. Store it before calling the
  # watch method because notifications may start arriving before the watch
  # method returns.
  ...

  resp = service.objects().watchAll(
    bucket="some_bucket_id", body=channel.body()).execute()
  channel.update(resp)

  # Store the channel, keyed by 'channel.id'. Store it after being updated
  # since the resource_id value will now be correct, and that's needed to
  # stop a subscription.
  ...


An example Webhook implementation using webapp2. Note that webapp2 puts
headers in a case insensitive dictionary, as headers aren't guaranteed to
always be upper case.

  id = self.request.headers[X_GOOG_CHANNEL_ID]

  # Retrieve the channel by id.
  channel = ...

  # Parse notification from the headers, including validating the id.
  n = notification_from_headers(channel, self.request.headers)

  # Do app specific stuff with the notification here.
  if n.resource_state == 'sync':
    # Code to handle sync state.
  elif n.resource_state == 'exists':
    # Code to handle the exists state.
  elif n.resource_state == 'not_exists':
    # Code to handle the not exists state.


Example of unsubscribing.

  service.channels().stop(channel.body())
"""

import datetime
import uuid

from apiclient import errors
from oauth2client import util


# The unix time epoch starts at midnight 1970.
EPOCH = datetime.datetime.utcfromtimestamp(0)

# Map the names of the parameters in the JSON channel description to
# the parameter names we use in the Channel class.
CHANNEL_PARAMS = {
    'address': 'address',
    'id': 'id',
    'expiration': 'expiration',
    'params': 'params',
    'resourceId': 'resource_id',
    'resourceUri': 'resource_uri',
    'type': 'type',
    'token': 'token',
    }

X_GOOG_CHANNEL_ID     = 'X-GOOG-CHANNEL-ID'
X_GOOG_MESSAGE_NUMBER = 'X-GOOG-MESSAGE-NUMBER'
X_GOOG_RESOURCE_STATE = 'X-GOOG-RESOURCE-STATE'
X_GOOG_RESOURCE_URI   = 'X-GOOG-RESOURCE-URI'
X_GOOG_RESOURCE_ID    = 'X-GOOG-RESOURCE-ID'


def _upper_header_keys(headers):
  new_headers = {}
  for k, v in headers.iteritems():
    new_headers[k.upper()] = v
  return new_headers


class Notification(object):
  """A Notification from a Channel.

  Notifications are not usually constructed directly, but are returned
  from functions like notification_from_headers().

  Attributes:
    message_number: int, The unique id number of this notification.
    state: str, The state of the resource being monitored.
    uri: str, The address of the resource being monitored.
    resource_id: str, The unique identifier of the version of the resource at
      this event.
  """
  @util.positional(5)
  def __init__(self, message_number, state, resource_uri, resource_id):
    """Notification constructor.

    Args:
      message_number: int, The unique id number of this notification.
      state: str, The state of the resource being monitored. Can be one
        of "exists", "not_exists", or "sync".
      resource_uri: str, The address of the resource being monitored.
      resource_id: str, The identifier of the watched resource.
    """
    self.message_number = message_number
    self.state = state
    self.resource_uri = resource_uri
    self.resource_id = resource_id


class Channel(object):
  """A Channel for notifications.

  Usually not constructed directly, instead it is returned from helper
  functions like new_webhook_channel().

  Attributes:
    type: str, The type of delivery mechanism used by this channel. For
      example, 'web_hook'.
    id: str, A UUID for the channel.
    token: str, An arbitrary string associated with the channel that
      is delivered to the target address with each event delivered
      over this channel.
    address: str, The address of the receiving entity where events are
      delivered. Specific to the channel type.
    expiration: int, The time, in milliseconds from the epoch, when this
      channel will expire.
    params: dict, A dictionary of string to string, with additional parameters
      controlling delivery channel behavior.
    resource_id: str, An opaque id that identifies the resource that is
      being watched. Stable across different API versions.
    resource_uri: str, The canonicalized ID of the watched resource.
  """

  @util.positional(5)
  def __init__(self, type, id, token, address, expiration=None,
               params=None, resource_id="", resource_uri=""):
    """Create a new Channel.

    In user code, this Channel constructor will not typically be called
    manually since there are functions for creating channels for each specific
    type with a more customized set of arguments to pass.

    Args:
      type: str, The type of delivery mechanism used by this channel. For
        example, 'web_hook'.
      id: str, A UUID for the channel.
      token: str, An arbitrary string associated with the channel that
        is delivered to the target address with each event delivered
        over this channel.
      address: str,  The address of the receiving entity where events are
        delivered. Specific to the channel type.
      expiration: int, The time, in milliseconds from the epoch, when this
        channel will expire.
      params: dict, A dictionary of string to string, with additional parameters
        controlling delivery channel behavior.
      resource_id: str, An opaque id that identifies the resource that is
        being watched. Stable across different API versions.
      resource_uri: str, The canonicalized ID of the watched resource.
    """
    self.type = type
    self.id = id
    self.token = token
    self.address = address
    self.expiration = expiration
    self.params = params
    self.resource_id = resource_id
    self.resource_uri = resource_uri

  def body(self):
    """Build a body from the Channel.

    Constructs a dictionary that's appropriate for passing into watch()
    methods as the value of body argument.

    Returns:
      A dictionary representation of the channel.
    """
    result = {
        'id': self.id,
        'token': self.token,
        'type': self.type,
        'address': self.address
        }
    if self.params:
      result['params'] = self.params
    if self.resource_id:
      result['resourceId'] = self.resource_id
    if self.resource_uri:
      result['resourceUri'] = self.resource_uri
    if self.expiration:
      result['expiration'] = self.expiration

    return result

  def update(self, resp):
    """Update a channel with information from the response of watch().

    When a request is sent to watch() a resource, the response returned
    from the watch() request is a dictionary with updated channel information,
    such as the resource_id, which is needed when stopping a subscription.

    Args:
      resp: dict, The response from a watch() method.
    """
    for json_name, param_name in CHANNEL_PARAMS.iteritems():
      value = resp.get(json_name)
      if value is not None:
        setattr(self, param_name, value)


def notification_from_headers(channel, headers):
  """Parse a notification from the webhook request headers, validate
    the notification, and return a Notification object.

  Args:
    channel: Channel, The channel that the notification is associated with.
    headers: dict, A dictionary like object that contains the request headers
      from the webhook HTTP request.

  Returns:
    A Notification object.

  Raises:
    errors.InvalidNotificationError if the notification is invalid.
    ValueError if the X-GOOG-MESSAGE-NUMBER can't be converted to an int.
  """
  headers = _upper_header_keys(headers)
  channel_id = headers[X_GOOG_CHANNEL_ID]
  if channel.id != channel_id:
    raise errors.InvalidNotificationError(
        'Channel id mismatch: %s != %s' % (channel.id, channel_id))
  else:
    message_number = int(headers[X_GOOG_MESSAGE_NUMBER])
    state = headers[X_GOOG_RESOURCE_STATE]
    resource_uri = headers[X_GOOG_RESOURCE_URI]
    resource_id = headers[X_GOOG_RESOURCE_ID]
    return Notification(message_number, state, resource_uri, resource_id)


@util.positional(2)
def new_webhook_channel(url, token=None, expiration=None, params=None):
    """Create a new webhook Channel.

    Args:
      url: str, URL to post notifications to.
      token: str, An arbitrary string associated with the channel that
        is delivered to the target address with each notification delivered
        over this channel.
      expiration: datetime.datetime, A time in the future when the channel
        should expire. Can also be None if the subscription should use the
        default expiration. Note that different services may have different
        limits on how long a subscription lasts. Check the response from the
        watch() method to see the value the service has set for an expiration
        time.
      params: dict, Extra parameters to pass on channel creation. Currently
        not used for webhook channels.
    """
    expiration_ms = 0
    if expiration:
      delta = expiration - EPOCH
      expiration_ms = delta.microseconds/1000 + (
          delta.seconds + delta.days*24*3600)*1000
      if expiration_ms < 0:
        expiration_ms = 0

    return Channel('web_hook', str(uuid.uuid4()),
                   token, url, expiration=expiration_ms,
                   params=params)


########NEW FILE########
__FILENAME__ = discovery
# Copyright (C) 2010 Google Inc.
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

"""Client for discovery based APIs.

A client library for Google's discovery based APIs.
"""

__author__ = 'jcgregorio@google.com (Joe Gregorio)'
__all__ = [
    'build',
    'build_from_document',
    'fix_method_name',
    'key2param',
    ]


# Standard library imports
import copy
from email.mime.multipart import MIMEMultipart
from email.mime.nonmultipart import MIMENonMultipart
import keyword
import logging
import mimetypes
import os
import re
import urllib
import urlparse

try:
  from urlparse import parse_qsl
except ImportError:
  from cgi import parse_qsl

# Third-party imports
import httplib2
import mimeparse
import uritemplate

# Local imports
from apiclient.errors import HttpError
from apiclient.errors import InvalidJsonError
from apiclient.errors import MediaUploadSizeError
from apiclient.errors import UnacceptableMimeTypeError
from apiclient.errors import UnknownApiNameOrVersion
from apiclient.errors import UnknownFileType
from apiclient.http import HttpRequest
from apiclient.http import MediaFileUpload
from apiclient.http import MediaUpload
from apiclient.model import JsonModel
from apiclient.model import MediaModel
from apiclient.model import RawModel
from apiclient.schema import Schemas
from oauth2client.anyjson import simplejson
from oauth2client.util import _add_query_parameter
from oauth2client.util import positional


# The client library requires a version of httplib2 that supports RETRIES.
httplib2.RETRIES = 1

logger = logging.getLogger(__name__)

URITEMPLATE = re.compile('{[^}]*}')
VARNAME = re.compile('[a-zA-Z0-9_-]+')
DISCOVERY_URI = ('https://www.googleapis.com/discovery/v1/apis/'
                 '{api}/{apiVersion}/rest')
DEFAULT_METHOD_DOC = 'A description of how to use this function'
HTTP_PAYLOAD_METHODS = frozenset(['PUT', 'POST', 'PATCH'])
_MEDIA_SIZE_BIT_SHIFTS = {'KB': 10, 'MB': 20, 'GB': 30, 'TB': 40}
BODY_PARAMETER_DEFAULT_VALUE = {
    'description': 'The request body.',
    'type': 'object',
    'required': True,
}
MEDIA_BODY_PARAMETER_DEFAULT_VALUE = {
    'description': ('The filename of the media request body, or an instance '
                    'of a MediaUpload object.'),
    'type': 'string',
    'required': False,
}

# Parameters accepted by the stack, but not visible via discovery.
# TODO(dhermes): Remove 'userip' in 'v2'.
STACK_QUERY_PARAMETERS = frozenset(['trace', 'pp', 'userip', 'strict'])
STACK_QUERY_PARAMETER_DEFAULT_VALUE = {'type': 'string', 'location': 'query'}

# Library-specific reserved words beyond Python keywords.
RESERVED_WORDS = frozenset(['body'])


def fix_method_name(name):
  """Fix method names to avoid reserved word conflicts.

  Args:
    name: string, method name.

  Returns:
    The name with a '_' prefixed if the name is a reserved word.
  """
  if keyword.iskeyword(name) or name in RESERVED_WORDS:
    return name + '_'
  else:
    return name


def key2param(key):
  """Converts key names into parameter names.

  For example, converting "max-results" -> "max_results"

  Args:
    key: string, the method key name.

  Returns:
    A safe method name based on the key name.
  """
  result = []
  key = list(key)
  if not key[0].isalpha():
    result.append('x')
  for c in key:
    if c.isalnum():
      result.append(c)
    else:
      result.append('_')

  return ''.join(result)


@positional(2)
def build(serviceName,
          version,
          http=None,
          discoveryServiceUrl=DISCOVERY_URI,
          developerKey=None,
          model=None,
          requestBuilder=HttpRequest):
  """Construct a Resource for interacting with an API.

  Construct a Resource object for interacting with an API. The serviceName and
  version are the names from the Discovery service.

  Args:
    serviceName: string, name of the service.
    version: string, the version of the service.
    http: httplib2.Http, An instance of httplib2.Http or something that acts
      like it that HTTP requests will be made through.
    discoveryServiceUrl: string, a URI Template that points to the location of
      the discovery service. It should have two parameters {api} and
      {apiVersion} that when filled in produce an absolute URI to the discovery
      document for that service.
    developerKey: string, key obtained from
      https://code.google.com/apis/console.
    model: apiclient.Model, converts to and from the wire format.
    requestBuilder: apiclient.http.HttpRequest, encapsulator for an HTTP
      request.

  Returns:
    A Resource object with methods for interacting with the service.
  """
  params = {
      'api': serviceName,
      'apiVersion': version
      }

  if http is None:
    http = httplib2.Http()

  requested_url = uritemplate.expand(discoveryServiceUrl, params)

  # REMOTE_ADDR is defined by the CGI spec [RFC3875] as the environment
  # variable that contains the network address of the client sending the
  # request. If it exists then add that to the request for the discovery
  # document to avoid exceeding the quota on discovery requests.
  if 'REMOTE_ADDR' in os.environ:
    requested_url = _add_query_parameter(requested_url, 'userIp',
                                         os.environ['REMOTE_ADDR'])
  logger.info('URL being requested: %s' % requested_url)

  resp, content = http.request(requested_url)

  if resp.status == 404:
    raise UnknownApiNameOrVersion("name: %s  version: %s" % (serviceName,
                                                            version))
  if resp.status >= 400:
    raise HttpError(resp, content, uri=requested_url)

  try:
    service = simplejson.loads(content)
  except ValueError, e:
    logger.error('Failed to parse as JSON: ' + content)
    raise InvalidJsonError()

  return build_from_document(content, base=discoveryServiceUrl, http=http,
      developerKey=developerKey, model=model, requestBuilder=requestBuilder)


@positional(1)
def build_from_document(
    service,
    base=None,
    future=None,
    http=None,
    developerKey=None,
    model=None,
    requestBuilder=HttpRequest):
  """Create a Resource for interacting with an API.

  Same as `build()`, but constructs the Resource object from a discovery
  document that is it given, as opposed to retrieving one over HTTP.

  Args:
    service: string or object, the JSON discovery document describing the API.
      The value passed in may either be the JSON string or the deserialized
      JSON.
    base: string, base URI for all HTTP requests, usually the discovery URI.
      This parameter is no longer used as rootUrl and servicePath are included
      within the discovery document. (deprecated)
    future: string, discovery document with future capabilities (deprecated).
    http: httplib2.Http, An instance of httplib2.Http or something that acts
      like it that HTTP requests will be made through.
    developerKey: string, Key for controlling API usage, generated
      from the API Console.
    model: Model class instance that serializes and de-serializes requests and
      responses.
    requestBuilder: Takes an http request and packages it up to be executed.

  Returns:
    A Resource object with methods for interacting with the service.
  """

  # future is no longer used.
  future = {}

  if isinstance(service, basestring):
    service = simplejson.loads(service)
  base = urlparse.urljoin(service['rootUrl'], service['servicePath'])
  schema = Schemas(service)

  if model is None:
    features = service.get('features', [])
    model = JsonModel('dataWrapper' in features)
  return Resource(http=http, baseUrl=base, model=model,
                  developerKey=developerKey, requestBuilder=requestBuilder,
                  resourceDesc=service, rootDesc=service, schema=schema)


def _cast(value, schema_type):
  """Convert value to a string based on JSON Schema type.

  See http://tools.ietf.org/html/draft-zyp-json-schema-03 for more details on
  JSON Schema.

  Args:
    value: any, the value to convert
    schema_type: string, the type that value should be interpreted as

  Returns:
    A string representation of 'value' based on the schema_type.
  """
  if schema_type == 'string':
    if type(value) == type('') or type(value) == type(u''):
      return value
    else:
      return str(value)
  elif schema_type == 'integer':
    return str(int(value))
  elif schema_type == 'number':
    return str(float(value))
  elif schema_type == 'boolean':
    return str(bool(value)).lower()
  else:
    if type(value) == type('') or type(value) == type(u''):
      return value
    else:
      return str(value)


def _media_size_to_long(maxSize):
  """Convert a string media size, such as 10GB or 3TB into an integer.

  Args:
    maxSize: string, size as a string, such as 2MB or 7GB.

  Returns:
    The size as an integer value.
  """
  if len(maxSize) < 2:
    return 0L
  units = maxSize[-2:].upper()
  bit_shift = _MEDIA_SIZE_BIT_SHIFTS.get(units)
  if bit_shift is not None:
    return long(maxSize[:-2]) << bit_shift
  else:
    return long(maxSize)


def _media_path_url_from_info(root_desc, path_url):
  """Creates an absolute media path URL.

  Constructed using the API root URI and service path from the discovery
  document and the relative path for the API method.

  Args:
    root_desc: Dictionary; the entire original deserialized discovery document.
    path_url: String; the relative URL for the API method. Relative to the API
        root, which is specified in the discovery document.

  Returns:
    String; the absolute URI for media upload for the API method.
  """
  return '%(root)supload/%(service_path)s%(path)s' % {
      'root': root_desc['rootUrl'],
      'service_path': root_desc['servicePath'],
      'path': path_url,
  }


def _fix_up_parameters(method_desc, root_desc, http_method):
  """Updates parameters of an API method with values specific to this library.

  Specifically, adds whatever global parameters are specified by the API to the
  parameters for the individual method. Also adds parameters which don't
  appear in the discovery document, but are available to all discovery based
  APIs (these are listed in STACK_QUERY_PARAMETERS).

  SIDE EFFECTS: This updates the parameters dictionary object in the method
  description.

  Args:
    method_desc: Dictionary with metadata describing an API method. Value comes
        from the dictionary of methods stored in the 'methods' key in the
        deserialized discovery document.
    root_desc: Dictionary; the entire original deserialized discovery document.
    http_method: String; the HTTP method used to call the API method described
        in method_desc.

  Returns:
    The updated Dictionary stored in the 'parameters' key of the method
        description dictionary.
  """
  parameters = method_desc.setdefault('parameters', {})

  # Add in the parameters common to all methods.
  for name, description in root_desc.get('parameters', {}).iteritems():
    parameters[name] = description

  # Add in undocumented query parameters.
  for name in STACK_QUERY_PARAMETERS:
    parameters[name] = STACK_QUERY_PARAMETER_DEFAULT_VALUE.copy()

  # Add 'body' (our own reserved word) to parameters if the method supports
  # a request payload.
  if http_method in HTTP_PAYLOAD_METHODS and 'request' in method_desc:
    body = BODY_PARAMETER_DEFAULT_VALUE.copy()
    body.update(method_desc['request'])
    parameters['body'] = body

  return parameters


def _fix_up_media_upload(method_desc, root_desc, path_url, parameters):
  """Updates parameters of API by adding 'media_body' if supported by method.

  SIDE EFFECTS: If the method supports media upload and has a required body,
  sets body to be optional (required=False) instead. Also, if there is a
  'mediaUpload' in the method description, adds 'media_upload' key to
  parameters.

  Args:
    method_desc: Dictionary with metadata describing an API method. Value comes
        from the dictionary of methods stored in the 'methods' key in the
        deserialized discovery document.
    root_desc: Dictionary; the entire original deserialized discovery document.
    path_url: String; the relative URL for the API method. Relative to the API
        root, which is specified in the discovery document.
    parameters: A dictionary describing method parameters for method described
        in method_desc.

  Returns:
    Triple (accept, max_size, media_path_url) where:
      - accept is a list of strings representing what content types are
        accepted for media upload. Defaults to empty list if not in the
        discovery document.
      - max_size is a long representing the max size in bytes allowed for a
        media upload. Defaults to 0L if not in the discovery document.
      - media_path_url is a String; the absolute URI for media upload for the
        API method. Constructed using the API root URI and service path from
        the discovery document and the relative path for the API method. If
        media upload is not supported, this is None.
  """
  media_upload = method_desc.get('mediaUpload', {})
  accept = media_upload.get('accept', [])
  max_size = _media_size_to_long(media_upload.get('maxSize', ''))
  media_path_url = None

  if media_upload:
    media_path_url = _media_path_url_from_info(root_desc, path_url)
    parameters['media_body'] = MEDIA_BODY_PARAMETER_DEFAULT_VALUE.copy()
    if 'body' in parameters:
      parameters['body']['required'] = False

  return accept, max_size, media_path_url


def _fix_up_method_description(method_desc, root_desc):
  """Updates a method description in a discovery document.

  SIDE EFFECTS: Changes the parameters dictionary in the method description with
  extra parameters which are used locally.

  Args:
    method_desc: Dictionary with metadata describing an API method. Value comes
        from the dictionary of methods stored in the 'methods' key in the
        deserialized discovery document.
    root_desc: Dictionary; the entire original deserialized discovery document.

  Returns:
    Tuple (path_url, http_method, method_id, accept, max_size, media_path_url)
    where:
      - path_url is a String; the relative URL for the API method. Relative to
        the API root, which is specified in the discovery document.
      - http_method is a String; the HTTP method used to call the API method
        described in the method description.
      - method_id is a String; the name of the RPC method associated with the
        API method, and is in the method description in the 'id' key.
      - accept is a list of strings representing what content types are
        accepted for media upload. Defaults to empty list if not in the
        discovery document.
      - max_size is a long representing the max size in bytes allowed for a
        media upload. Defaults to 0L if not in the discovery document.
      - media_path_url is a String; the absolute URI for media upload for the
        API method. Constructed using the API root URI and service path from
        the discovery document and the relative path for the API method. If
        media upload is not supported, this is None.
  """
  path_url = method_desc['path']
  http_method = method_desc['httpMethod']
  method_id = method_desc['id']

  parameters = _fix_up_parameters(method_desc, root_desc, http_method)
  # Order is important. `_fix_up_media_upload` needs `method_desc` to have a
  # 'parameters' key and needs to know if there is a 'body' parameter because it
  # also sets a 'media_body' parameter.
  accept, max_size, media_path_url = _fix_up_media_upload(
      method_desc, root_desc, path_url, parameters)

  return path_url, http_method, method_id, accept, max_size, media_path_url


# TODO(dhermes): Convert this class to ResourceMethod and make it callable
class ResourceMethodParameters(object):
  """Represents the parameters associated with a method.

  Attributes:
    argmap: Map from method parameter name (string) to query parameter name
        (string).
    required_params: List of required parameters (represented by parameter
        name as string).
    repeated_params: List of repeated parameters (represented by parameter
        name as string).
    pattern_params: Map from method parameter name (string) to regular
        expression (as a string). If the pattern is set for a parameter, the
        value for that parameter must match the regular expression.
    query_params: List of parameters (represented by parameter name as string)
        that will be used in the query string.
    path_params: Set of parameters (represented by parameter name as string)
        that will be used in the base URL path.
    param_types: Map from method parameter name (string) to parameter type. Type
        can be any valid JSON schema type; valid values are 'any', 'array',
        'boolean', 'integer', 'number', 'object', or 'string'. Reference:
        http://tools.ietf.org/html/draft-zyp-json-schema-03#section-5.1
    enum_params: Map from method parameter name (string) to list of strings,
       where each list of strings is the list of acceptable enum values.
  """

  def __init__(self, method_desc):
    """Constructor for ResourceMethodParameters.

    Sets default values and defers to set_parameters to populate.

    Args:
      method_desc: Dictionary with metadata describing an API method. Value
          comes from the dictionary of methods stored in the 'methods' key in
          the deserialized discovery document.
    """
    self.argmap = {}
    self.required_params = []
    self.repeated_params = []
    self.pattern_params = {}
    self.query_params = []
    # TODO(dhermes): Change path_params to a list if the extra URITEMPLATE
    #                parsing is gotten rid of.
    self.path_params = set()
    self.param_types = {}
    self.enum_params = {}

    self.set_parameters(method_desc)

  def set_parameters(self, method_desc):
    """Populates maps and lists based on method description.

    Iterates through each parameter for the method and parses the values from
    the parameter dictionary.

    Args:
      method_desc: Dictionary with metadata describing an API method. Value
          comes from the dictionary of methods stored in the 'methods' key in
          the deserialized discovery document.
    """
    for arg, desc in method_desc.get('parameters', {}).iteritems():
      param = key2param(arg)
      self.argmap[param] = arg

      if desc.get('pattern'):
        self.pattern_params[param] = desc['pattern']
      if desc.get('enum'):
        self.enum_params[param] = desc['enum']
      if desc.get('required'):
        self.required_params.append(param)
      if desc.get('repeated'):
        self.repeated_params.append(param)
      if desc.get('location') == 'query':
        self.query_params.append(param)
      if desc.get('location') == 'path':
        self.path_params.add(param)
      self.param_types[param] = desc.get('type', 'string')

    # TODO(dhermes): Determine if this is still necessary. Discovery based APIs
    #                should have all path parameters already marked with
    #                'location: path'.
    for match in URITEMPLATE.finditer(method_desc['path']):
      for namematch in VARNAME.finditer(match.group(0)):
        name = key2param(namematch.group(0))
        self.path_params.add(name)
        if name in self.query_params:
          self.query_params.remove(name)


def createMethod(methodName, methodDesc, rootDesc, schema):
  """Creates a method for attaching to a Resource.

  Args:
    methodName: string, name of the method to use.
    methodDesc: object, fragment of deserialized discovery document that
      describes the method.
    rootDesc: object, the entire deserialized discovery document.
    schema: object, mapping of schema names to schema descriptions.
  """
  methodName = fix_method_name(methodName)
  (pathUrl, httpMethod, methodId, accept,
   maxSize, mediaPathUrl) = _fix_up_method_description(methodDesc, rootDesc)

  parameters = ResourceMethodParameters(methodDesc)

  def method(self, **kwargs):
    # Don't bother with doc string, it will be over-written by createMethod.

    for name in kwargs.iterkeys():
      if name not in parameters.argmap:
        raise TypeError('Got an unexpected keyword argument "%s"' % name)

    # Remove args that have a value of None.
    keys = kwargs.keys()
    for name in keys:
      if kwargs[name] is None:
        del kwargs[name]

    for name in parameters.required_params:
      if name not in kwargs:
        raise TypeError('Missing required parameter "%s"' % name)

    for name, regex in parameters.pattern_params.iteritems():
      if name in kwargs:
        if isinstance(kwargs[name], basestring):
          pvalues = [kwargs[name]]
        else:
          pvalues = kwargs[name]
        for pvalue in pvalues:
          if re.match(regex, pvalue) is None:
            raise TypeError(
                'Parameter "%s" value "%s" does not match the pattern "%s"' %
                (name, pvalue, regex))

    for name, enums in parameters.enum_params.iteritems():
      if name in kwargs:
        # We need to handle the case of a repeated enum
        # name differently, since we want to handle both
        # arg='value' and arg=['value1', 'value2']
        if (name in parameters.repeated_params and
            not isinstance(kwargs[name], basestring)):
          values = kwargs[name]
        else:
          values = [kwargs[name]]
        for value in values:
          if value not in enums:
            raise TypeError(
                'Parameter "%s" value "%s" is not an allowed value in "%s"' %
                (name, value, str(enums)))

    actual_query_params = {}
    actual_path_params = {}
    for key, value in kwargs.iteritems():
      to_type = parameters.param_types.get(key, 'string')
      # For repeated parameters we cast each member of the list.
      if key in parameters.repeated_params and type(value) == type([]):
        cast_value = [_cast(x, to_type) for x in value]
      else:
        cast_value = _cast(value, to_type)
      if key in parameters.query_params:
        actual_query_params[parameters.argmap[key]] = cast_value
      if key in parameters.path_params:
        actual_path_params[parameters.argmap[key]] = cast_value
    body_value = kwargs.get('body', None)
    media_filename = kwargs.get('media_body', None)

    if self._developerKey:
      actual_query_params['key'] = self._developerKey

    model = self._model
    if methodName.endswith('_media'):
      model = MediaModel()
    elif 'response' not in methodDesc:
      model = RawModel()

    headers = {}
    headers, params, query, body = model.request(headers,
        actual_path_params, actual_query_params, body_value)

    expanded_url = uritemplate.expand(pathUrl, params)
    url = urlparse.urljoin(self._baseUrl, expanded_url + query)

    resumable = None
    multipart_boundary = ''

    if media_filename:
      # Ensure we end up with a valid MediaUpload object.
      if isinstance(media_filename, basestring):
        (media_mime_type, encoding) = mimetypes.guess_type(media_filename)
        if media_mime_type is None:
          raise UnknownFileType(media_filename)
        if not mimeparse.best_match([media_mime_type], ','.join(accept)):
          raise UnacceptableMimeTypeError(media_mime_type)
        media_upload = MediaFileUpload(media_filename,
                                       mimetype=media_mime_type)
      elif isinstance(media_filename, MediaUpload):
        media_upload = media_filename
      else:
        raise TypeError('media_filename must be str or MediaUpload.')

      # Check the maxSize
      if maxSize > 0 and media_upload.size() > maxSize:
        raise MediaUploadSizeError("Media larger than: %s" % maxSize)

      # Use the media path uri for media uploads
      expanded_url = uritemplate.expand(mediaPathUrl, params)
      url = urlparse.urljoin(self._baseUrl, expanded_url + query)
      if media_upload.resumable():
        url = _add_query_parameter(url, 'uploadType', 'resumable')

      if media_upload.resumable():
        # This is all we need to do for resumable, if the body exists it gets
        # sent in the first request, otherwise an empty body is sent.
        resumable = media_upload
      else:
        # A non-resumable upload
        if body is None:
          # This is a simple media upload
          headers['content-type'] = media_upload.mimetype()
          body = media_upload.getbytes(0, media_upload.size())
          url = _add_query_parameter(url, 'uploadType', 'media')
        else:
          # This is a multipart/related upload.
          msgRoot = MIMEMultipart('related')
          # msgRoot should not write out it's own headers
          setattr(msgRoot, '_write_headers', lambda self: None)

          # attach the body as one part
          msg = MIMENonMultipart(*headers['content-type'].split('/'))
          msg.set_payload(body)
          msgRoot.attach(msg)

          # attach the media as the second part
          msg = MIMENonMultipart(*media_upload.mimetype().split('/'))
          msg['Content-Transfer-Encoding'] = 'binary'

          payload = media_upload.getbytes(0, media_upload.size())
          msg.set_payload(payload)
          msgRoot.attach(msg)
          body = msgRoot.as_string()

          multipart_boundary = msgRoot.get_boundary()
          headers['content-type'] = ('multipart/related; '
                                     'boundary="%s"') % multipart_boundary
          url = _add_query_parameter(url, 'uploadType', 'multipart')

    logger.info('URL being requested: %s' % url)
    return self._requestBuilder(self._http,
                                model.response,
                                url,
                                method=httpMethod,
                                body=body,
                                headers=headers,
                                methodId=methodId,
                                resumable=resumable)

  docs = [methodDesc.get('description', DEFAULT_METHOD_DOC), '\n\n']
  if len(parameters.argmap) > 0:
    docs.append('Args:\n')

  # Skip undocumented params and params common to all methods.
  skip_parameters = rootDesc.get('parameters', {}).keys()
  skip_parameters.extend(STACK_QUERY_PARAMETERS)

  all_args = parameters.argmap.keys()
  args_ordered = [key2param(s) for s in methodDesc.get('parameterOrder', [])]

  # Move body to the front of the line.
  if 'body' in all_args:
    args_ordered.append('body')

  for name in all_args:
    if name not in args_ordered:
      args_ordered.append(name)

  for arg in args_ordered:
    if arg in skip_parameters:
      continue

    repeated = ''
    if arg in parameters.repeated_params:
      repeated = ' (repeated)'
    required = ''
    if arg in parameters.required_params:
      required = ' (required)'
    paramdesc = methodDesc['parameters'][parameters.argmap[arg]]
    paramdoc = paramdesc.get('description', 'A parameter')
    if '$ref' in paramdesc:
      docs.append(
          ('  %s: object, %s%s%s\n    The object takes the'
          ' form of:\n\n%s\n\n') % (arg, paramdoc, required, repeated,
            schema.prettyPrintByName(paramdesc['$ref'])))
    else:
      paramtype = paramdesc.get('type', 'string')
      docs.append('  %s: %s, %s%s%s\n' % (arg, paramtype, paramdoc, required,
                                          repeated))
    enum = paramdesc.get('enum', [])
    enumDesc = paramdesc.get('enumDescriptions', [])
    if enum and enumDesc:
      docs.append('    Allowed values\n')
      for (name, desc) in zip(enum, enumDesc):
        docs.append('      %s - %s\n' % (name, desc))
  if 'response' in methodDesc:
    if methodName.endswith('_media'):
      docs.append('\nReturns:\n  The media object as a string.\n\n    ')
    else:
      docs.append('\nReturns:\n  An object of the form:\n\n    ')
      docs.append(schema.prettyPrintSchema(methodDesc['response']))

  setattr(method, '__doc__', ''.join(docs))
  return (methodName, method)


def createNextMethod(methodName):
  """Creates any _next methods for attaching to a Resource.

  The _next methods allow for easy iteration through list() responses.

  Args:
    methodName: string, name of the method to use.
  """
  methodName = fix_method_name(methodName)

  def methodNext(self, previous_request, previous_response):
    """Retrieves the next page of results.

Args:
  previous_request: The request for the previous page. (required)
  previous_response: The response from the request for the previous page. (required)

Returns:
  A request object that you can call 'execute()' on to request the next
  page. Returns None if there are no more items in the collection.
    """
    # Retrieve nextPageToken from previous_response
    # Use as pageToken in previous_request to create new request.

    if 'nextPageToken' not in previous_response:
      return None

    request = copy.copy(previous_request)

    pageToken = previous_response['nextPageToken']
    parsed = list(urlparse.urlparse(request.uri))
    q = parse_qsl(parsed[4])

    # Find and remove old 'pageToken' value from URI
    newq = [(key, value) for (key, value) in q if key != 'pageToken']
    newq.append(('pageToken', pageToken))
    parsed[4] = urllib.urlencode(newq)
    uri = urlparse.urlunparse(parsed)

    request.uri = uri

    logger.info('URL being requested: %s' % uri)

    return request

  return (methodName, methodNext)


class Resource(object):
  """A class for interacting with a resource."""

  def __init__(self, http, baseUrl, model, requestBuilder, developerKey,
               resourceDesc, rootDesc, schema):
    """Build a Resource from the API description.

    Args:
      http: httplib2.Http, Object to make http requests with.
      baseUrl: string, base URL for the API. All requests are relative to this
          URI.
      model: apiclient.Model, converts to and from the wire format.
      requestBuilder: class or callable that instantiates an
          apiclient.HttpRequest object.
      developerKey: string, key obtained from
          https://code.google.com/apis/console
      resourceDesc: object, section of deserialized discovery document that
          describes a resource. Note that the top level discovery document
          is considered a resource.
      rootDesc: object, the entire deserialized discovery document.
      schema: object, mapping of schema names to schema descriptions.
    """
    self._dynamic_attrs = []

    self._http = http
    self._baseUrl = baseUrl
    self._model = model
    self._developerKey = developerKey
    self._requestBuilder = requestBuilder
    self._resourceDesc = resourceDesc
    self._rootDesc = rootDesc
    self._schema = schema

    self._set_service_methods()

  def _set_dynamic_attr(self, attr_name, value):
    """Sets an instance attribute and tracks it in a list of dynamic attributes.

    Args:
      attr_name: string; The name of the attribute to be set
      value: The value being set on the object and tracked in the dynamic cache.
    """
    self._dynamic_attrs.append(attr_name)
    self.__dict__[attr_name] = value

  def __getstate__(self):
    """Trim the state down to something that can be pickled.

    Uses the fact that the instance variable _dynamic_attrs holds attrs that
    will be wiped and restored on pickle serialization.
    """
    state_dict = copy.copy(self.__dict__)
    for dynamic_attr in self._dynamic_attrs:
      del state_dict[dynamic_attr]
    del state_dict['_dynamic_attrs']
    return state_dict

  def __setstate__(self, state):
    """Reconstitute the state of the object from being pickled.

    Uses the fact that the instance variable _dynamic_attrs holds attrs that
    will be wiped and restored on pickle serialization.
    """
    self.__dict__.update(state)
    self._dynamic_attrs = []
    self._set_service_methods()

  def _set_service_methods(self):
    self._add_basic_methods(self._resourceDesc, self._rootDesc, self._schema)
    self._add_nested_resources(self._resourceDesc, self._rootDesc, self._schema)
    self._add_next_methods(self._resourceDesc, self._schema)

  def _add_basic_methods(self, resourceDesc, rootDesc, schema):
    # Add basic methods to Resource
    if 'methods' in resourceDesc:
      for methodName, methodDesc in resourceDesc['methods'].iteritems():
        fixedMethodName, method = createMethod(
            methodName, methodDesc, rootDesc, schema)
        self._set_dynamic_attr(fixedMethodName,
                               method.__get__(self, self.__class__))
        # Add in _media methods. The functionality of the attached method will
        # change when it sees that the method name ends in _media.
        if methodDesc.get('supportsMediaDownload', False):
          fixedMethodName, method = createMethod(
              methodName + '_media', methodDesc, rootDesc, schema)
          self._set_dynamic_attr(fixedMethodName,
                                 method.__get__(self, self.__class__))

  def _add_nested_resources(self, resourceDesc, rootDesc, schema):
    # Add in nested resources
    if 'resources' in resourceDesc:

      def createResourceMethod(methodName, methodDesc):
        """Create a method on the Resource to access a nested Resource.

        Args:
          methodName: string, name of the method to use.
          methodDesc: object, fragment of deserialized discovery document that
            describes the method.
        """
        methodName = fix_method_name(methodName)

        def methodResource(self):
          return Resource(http=self._http, baseUrl=self._baseUrl,
                          model=self._model, developerKey=self._developerKey,
                          requestBuilder=self._requestBuilder,
                          resourceDesc=methodDesc, rootDesc=rootDesc,
                          schema=schema)

        setattr(methodResource, '__doc__', 'A collection resource.')
        setattr(methodResource, '__is_resource__', True)

        return (methodName, methodResource)

      for methodName, methodDesc in resourceDesc['resources'].iteritems():
        fixedMethodName, method = createResourceMethod(methodName, methodDesc)
        self._set_dynamic_attr(fixedMethodName,
                               method.__get__(self, self.__class__))

  def _add_next_methods(self, resourceDesc, schema):
    # Add _next() methods
    # Look for response bodies in schema that contain nextPageToken, and methods
    # that take a pageToken parameter.
    if 'methods' in resourceDesc:
      for methodName, methodDesc in resourceDesc['methods'].iteritems():
        if 'response' in methodDesc:
          responseSchema = methodDesc['response']
          if '$ref' in responseSchema:
            responseSchema = schema.get(responseSchema['$ref'])
          hasNextPageToken = 'nextPageToken' in responseSchema.get('properties',
                                                                   {})
          hasPageToken = 'pageToken' in methodDesc.get('parameters', {})
          if hasNextPageToken and hasPageToken:
            fixedMethodName, method = createNextMethod(methodName + '_next')
            self._set_dynamic_attr(fixedMethodName,
                                   method.__get__(self, self.__class__))

########NEW FILE########
__FILENAME__ = errors
#!/usr/bin/python2.4
#
# Copyright (C) 2010 Google Inc.
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

"""Errors for the library.

All exceptions defined by the library
should be defined in this file.
"""

__author__ = 'jcgregorio@google.com (Joe Gregorio)'


from oauth2client import util
from oauth2client.anyjson import simplejson


class Error(Exception):
  """Base error for this module."""
  pass


class HttpError(Error):
  """HTTP data was invalid or unexpected."""

  @util.positional(3)
  def __init__(self, resp, content, uri=None):
    self.resp = resp
    self.content = content
    self.uri = uri

  def _get_reason(self):
    """Calculate the reason for the error from the response content."""
    reason = self.resp.reason
    try:
      data = simplejson.loads(self.content)
      reason = data['error']['message']
    except (ValueError, KeyError):
      pass
    if reason is None:
      reason = ''
    return reason

  def __repr__(self):
    if self.uri:
      return '<HttpError %s when requesting %s returned "%s">' % (
          self.resp.status, self.uri, self._get_reason().strip())
    else:
      return '<HttpError %s "%s">' % (self.resp.status, self._get_reason())

  __str__ = __repr__


class InvalidJsonError(Error):
  """The JSON returned could not be parsed."""
  pass


class UnknownFileType(Error):
  """File type unknown or unexpected."""
  pass


class UnknownLinkType(Error):
  """Link type unknown or unexpected."""
  pass


class UnknownApiNameOrVersion(Error):
  """No API with that name and version exists."""
  pass


class UnacceptableMimeTypeError(Error):
  """That is an unacceptable mimetype for this operation."""
  pass


class MediaUploadSizeError(Error):
  """Media is larger than the method can accept."""
  pass


class ResumableUploadError(HttpError):
  """Error occured during resumable upload."""
  pass


class InvalidChunkSizeError(Error):
  """The given chunksize is not valid."""
  pass

class InvalidNotificationError(Error):
  """The channel Notification is invalid."""
  pass

class BatchError(HttpError):
  """Error occured during batch operations."""

  @util.positional(2)
  def __init__(self, reason, resp=None, content=None):
    self.resp = resp
    self.content = content
    self.reason = reason

  def __repr__(self):
      return '<BatchError %s "%s">' % (self.resp.status, self.reason)

  __str__ = __repr__


class UnexpectedMethodError(Error):
  """Exception raised by RequestMockBuilder on unexpected calls."""

  @util.positional(1)
  def __init__(self, methodId=None):
    """Constructor for an UnexpectedMethodError."""
    super(UnexpectedMethodError, self).__init__(
        'Received unexpected call %s' % methodId)


class UnexpectedBodyError(Error):
  """Exception raised by RequestMockBuilder on unexpected bodies."""

  def __init__(self, expected, provided):
    """Constructor for an UnexpectedMethodError."""
    super(UnexpectedBodyError, self).__init__(
        'Expected: [%s] - Provided: [%s]' % (expected, provided))

########NEW FILE########
__FILENAME__ = http
# Copyright (C) 2012 Google Inc.
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

"""Classes to encapsulate a single HTTP request.

The classes implement a command pattern, with every
object supporting an execute() method that does the
actuall HTTP request.
"""

__author__ = 'jcgregorio@google.com (Joe Gregorio)'

import StringIO
import base64
import copy
import gzip
import httplib2
import logging
import mimeparse
import mimetypes
import os
import random
import sys
import time
import urllib
import urlparse
import uuid

from email.generator import Generator
from email.mime.multipart import MIMEMultipart
from email.mime.nonmultipart import MIMENonMultipart
from email.parser import FeedParser
from errors import BatchError
from errors import HttpError
from errors import InvalidChunkSizeError
from errors import ResumableUploadError
from errors import UnexpectedBodyError
from errors import UnexpectedMethodError
from model import JsonModel
from oauth2client import util
from oauth2client.anyjson import simplejson


DEFAULT_CHUNK_SIZE = 512*1024

MAX_URI_LENGTH = 2048


class MediaUploadProgress(object):
  """Status of a resumable upload."""

  def __init__(self, resumable_progress, total_size):
    """Constructor.

    Args:
      resumable_progress: int, bytes sent so far.
      total_size: int, total bytes in complete upload, or None if the total
        upload size isn't known ahead of time.
    """
    self.resumable_progress = resumable_progress
    self.total_size = total_size

  def progress(self):
    """Percent of upload completed, as a float.

    Returns:
      the percentage complete as a float, returning 0.0 if the total size of
      the upload is unknown.
    """
    if self.total_size is not None:
      return float(self.resumable_progress) / float(self.total_size)
    else:
      return 0.0


class MediaDownloadProgress(object):
  """Status of a resumable download."""

  def __init__(self, resumable_progress, total_size):
    """Constructor.

    Args:
      resumable_progress: int, bytes received so far.
      total_size: int, total bytes in complete download.
    """
    self.resumable_progress = resumable_progress
    self.total_size = total_size

  def progress(self):
    """Percent of download completed, as a float.

    Returns:
      the percentage complete as a float, returning 0.0 if the total size of
      the download is unknown.
    """
    if self.total_size is not None:
      return float(self.resumable_progress) / float(self.total_size)
    else:
      return 0.0


class MediaUpload(object):
  """Describes a media object to upload.

  Base class that defines the interface of MediaUpload subclasses.

  Note that subclasses of MediaUpload may allow you to control the chunksize
  when uploading a media object. It is important to keep the size of the chunk
  as large as possible to keep the upload efficient. Other factors may influence
  the size of the chunk you use, particularly if you are working in an
  environment where individual HTTP requests may have a hardcoded time limit,
  such as under certain classes of requests under Google App Engine.

  Streams are io.Base compatible objects that support seek(). Some MediaUpload
  subclasses support using streams directly to upload data. Support for
  streaming may be indicated by a MediaUpload sub-class and if appropriate for a
  platform that stream will be used for uploading the media object. The support
  for streaming is indicated by has_stream() returning True. The stream() method
  should return an io.Base object that supports seek(). On platforms where the
  underlying httplib module supports streaming, for example Python 2.6 and
  later, the stream will be passed into the http library which will result in
  less memory being used and possibly faster uploads.

  If you need to upload media that can't be uploaded using any of the existing
  MediaUpload sub-class then you can sub-class MediaUpload for your particular
  needs.
  """

  def chunksize(self):
    """Chunk size for resumable uploads.

    Returns:
      Chunk size in bytes.
    """
    raise NotImplementedError()

  def mimetype(self):
    """Mime type of the body.

    Returns:
      Mime type.
    """
    return 'application/octet-stream'

  def size(self):
    """Size of upload.

    Returns:
      Size of the body, or None of the size is unknown.
    """
    return None

  def resumable(self):
    """Whether this upload is resumable.

    Returns:
      True if resumable upload or False.
    """
    return False

  def getbytes(self, begin, end):
    """Get bytes from the media.

    Args:
      begin: int, offset from beginning of file.
      length: int, number of bytes to read, starting at begin.

    Returns:
      A string of bytes read. May be shorter than length if EOF was reached
      first.
    """
    raise NotImplementedError()

  def has_stream(self):
    """Does the underlying upload support a streaming interface.

    Streaming means it is an io.IOBase subclass that supports seek, i.e.
    seekable() returns True.

    Returns:
      True if the call to stream() will return an instance of a seekable io.Base
      subclass.
    """
    return False

  def stream(self):
    """A stream interface to the data being uploaded.

    Returns:
      The returned value is an io.IOBase subclass that supports seek, i.e.
      seekable() returns True.
    """
    raise NotImplementedError()

  @util.positional(1)
  def _to_json(self, strip=None):
    """Utility function for creating a JSON representation of a MediaUpload.

    Args:
      strip: array, An array of names of members to not include in the JSON.

    Returns:
       string, a JSON representation of this instance, suitable to pass to
       from_json().
    """
    t = type(self)
    d = copy.copy(self.__dict__)
    if strip is not None:
      for member in strip:
        del d[member]
    d['_class'] = t.__name__
    d['_module'] = t.__module__
    return simplejson.dumps(d)

  def to_json(self):
    """Create a JSON representation of an instance of MediaUpload.

    Returns:
       string, a JSON representation of this instance, suitable to pass to
       from_json().
    """
    return self._to_json()

  @classmethod
  def new_from_json(cls, s):
    """Utility class method to instantiate a MediaUpload subclass from a JSON
    representation produced by to_json().

    Args:
      s: string, JSON from to_json().

    Returns:
      An instance of the subclass of MediaUpload that was serialized with
      to_json().
    """
    data = simplejson.loads(s)
    # Find and call the right classmethod from_json() to restore the object.
    module = data['_module']
    m = __import__(module, fromlist=module.split('.')[:-1])
    kls = getattr(m, data['_class'])
    from_json = getattr(kls, 'from_json')
    return from_json(s)


class MediaIoBaseUpload(MediaUpload):
  """A MediaUpload for a io.Base objects.

  Note that the Python file object is compatible with io.Base and can be used
  with this class also.

    fh = io.BytesIO('...Some data to upload...')
    media = MediaIoBaseUpload(fh, mimetype='image/png',
      chunksize=1024*1024, resumable=True)
    farm.animals().insert(
        id='cow',
        name='cow.png',
        media_body=media).execute()

  Depending on the platform you are working on, you may pass -1 as the
  chunksize, which indicates that the entire file should be uploaded in a single
  request. If the underlying platform supports streams, such as Python 2.6 or
  later, then this can be very efficient as it avoids multiple connections, and
  also avoids loading the entire file into memory before sending it. Note that
  Google App Engine has a 5MB limit on request size, so you should never set
  your chunksize larger than 5MB, or to -1.
  """

  @util.positional(3)
  def __init__(self, fd, mimetype, chunksize=DEFAULT_CHUNK_SIZE,
      resumable=False):
    """Constructor.

    Args:
      fd: io.Base or file object, The source of the bytes to upload. MUST be
        opened in blocking mode, do not use streams opened in non-blocking mode.
        The given stream must be seekable, that is, it must be able to call
        seek() on fd.
      mimetype: string, Mime-type of the file.
      chunksize: int, File will be uploaded in chunks of this many bytes. Only
        used if resumable=True. Pass in a value of -1 if the file is to be
        uploaded as a single chunk. Note that Google App Engine has a 5MB limit
        on request size, so you should never set your chunksize larger than 5MB,
        or to -1.
      resumable: bool, True if this is a resumable upload. False means upload
        in a single request.
    """
    super(MediaIoBaseUpload, self).__init__()
    self._fd = fd
    self._mimetype = mimetype
    if not (chunksize == -1 or chunksize > 0):
      raise InvalidChunkSizeError()
    self._chunksize = chunksize
    self._resumable = resumable

    self._fd.seek(0, os.SEEK_END)
    self._size = self._fd.tell()

  def chunksize(self):
    """Chunk size for resumable uploads.

    Returns:
      Chunk size in bytes.
    """
    return self._chunksize

  def mimetype(self):
    """Mime type of the body.

    Returns:
      Mime type.
    """
    return self._mimetype

  def size(self):
    """Size of upload.

    Returns:
      Size of the body, or None of the size is unknown.
    """
    return self._size

  def resumable(self):
    """Whether this upload is resumable.

    Returns:
      True if resumable upload or False.
    """
    return self._resumable

  def getbytes(self, begin, length):
    """Get bytes from the media.

    Args:
      begin: int, offset from beginning of file.
      length: int, number of bytes to read, starting at begin.

    Returns:
      A string of bytes read. May be shorted than length if EOF was reached
      first.
    """
    self._fd.seek(begin)
    return self._fd.read(length)

  def has_stream(self):
    """Does the underlying upload support a streaming interface.

    Streaming means it is an io.IOBase subclass that supports seek, i.e.
    seekable() returns True.

    Returns:
      True if the call to stream() will return an instance of a seekable io.Base
      subclass.
    """
    return True

  def stream(self):
    """A stream interface to the data being uploaded.

    Returns:
      The returned value is an io.IOBase subclass that supports seek, i.e.
      seekable() returns True.
    """
    return self._fd

  def to_json(self):
    """This upload type is not serializable."""
    raise NotImplementedError('MediaIoBaseUpload is not serializable.')


class MediaFileUpload(MediaIoBaseUpload):
  """A MediaUpload for a file.

  Construct a MediaFileUpload and pass as the media_body parameter of the
  method. For example, if we had a service that allowed uploading images:


    media = MediaFileUpload('cow.png', mimetype='image/png',
      chunksize=1024*1024, resumable=True)
    farm.animals().insert(
        id='cow',
        name='cow.png',
        media_body=media).execute()

  Depending on the platform you are working on, you may pass -1 as the
  chunksize, which indicates that the entire file should be uploaded in a single
  request. If the underlying platform supports streams, such as Python 2.6 or
  later, then this can be very efficient as it avoids multiple connections, and
  also avoids loading the entire file into memory before sending it. Note that
  Google App Engine has a 5MB limit on request size, so you should never set
  your chunksize larger than 5MB, or to -1.
  """

  @util.positional(2)
  def __init__(self, filename, mimetype=None, chunksize=DEFAULT_CHUNK_SIZE,
               resumable=False):
    """Constructor.

    Args:
      filename: string, Name of the file.
      mimetype: string, Mime-type of the file. If None then a mime-type will be
        guessed from the file extension.
      chunksize: int, File will be uploaded in chunks of this many bytes. Only
        used if resumable=True. Pass in a value of -1 if the file is to be
        uploaded in a single chunk. Note that Google App Engine has a 5MB limit
        on request size, so you should never set your chunksize larger than 5MB,
        or to -1.
      resumable: bool, True if this is a resumable upload. False means upload
        in a single request.
    """
    self._filename = filename
    fd = open(self._filename, 'rb')
    if mimetype is None:
      (mimetype, encoding) = mimetypes.guess_type(filename)
    super(MediaFileUpload, self).__init__(fd, mimetype, chunksize=chunksize,
                                          resumable=resumable)

  def to_json(self):
    """Creating a JSON representation of an instance of MediaFileUpload.

    Returns:
       string, a JSON representation of this instance, suitable to pass to
       from_json().
    """
    return self._to_json(strip=['_fd'])

  @staticmethod
  def from_json(s):
    d = simplejson.loads(s)
    return MediaFileUpload(d['_filename'], mimetype=d['_mimetype'],
                           chunksize=d['_chunksize'], resumable=d['_resumable'])


class MediaInMemoryUpload(MediaIoBaseUpload):
  """MediaUpload for a chunk of bytes.

  DEPRECATED: Use MediaIoBaseUpload with either io.TextIOBase or StringIO for
  the stream.
  """

  @util.positional(2)
  def __init__(self, body, mimetype='application/octet-stream',
               chunksize=DEFAULT_CHUNK_SIZE, resumable=False):
    """Create a new MediaInMemoryUpload.

  DEPRECATED: Use MediaIoBaseUpload with either io.TextIOBase or StringIO for
  the stream.

  Args:
    body: string, Bytes of body content.
    mimetype: string, Mime-type of the file or default of
      'application/octet-stream'.
    chunksize: int, File will be uploaded in chunks of this many bytes. Only
      used if resumable=True.
    resumable: bool, True if this is a resumable upload. False means upload
      in a single request.
    """
    fd = StringIO.StringIO(body)
    super(MediaInMemoryUpload, self).__init__(fd, mimetype, chunksize=chunksize,
                                              resumable=resumable)


class MediaIoBaseDownload(object):
  """"Download media resources.

  Note that the Python file object is compatible with io.Base and can be used
  with this class also.


  Example:
    request = farms.animals().get_media(id='cow')
    fh = io.FileIO('cow.png', mode='wb')
    downloader = MediaIoBaseDownload(fh, request, chunksize=1024*1024)

    done = False
    while done is False:
      status, done = downloader.next_chunk()
      if status:
        print "Download %d%%." % int(status.progress() * 100)
    print "Download Complete!"
  """

  @util.positional(3)
  def __init__(self, fd, request, chunksize=DEFAULT_CHUNK_SIZE):
    """Constructor.

    Args:
      fd: io.Base or file object, The stream in which to write the downloaded
        bytes.
      request: apiclient.http.HttpRequest, the media request to perform in
        chunks.
      chunksize: int, File will be downloaded in chunks of this many bytes.
    """
    self._fd = fd
    self._request = request
    self._uri = request.uri
    self._chunksize = chunksize
    self._progress = 0
    self._total_size = None
    self._done = False

    # Stubs for testing.
    self._sleep = time.sleep
    self._rand = random.random

  @util.positional(1)
  def next_chunk(self, num_retries=0):
    """Get the next chunk of the download.

    Args:
      num_retries: Integer, number of times to retry 500's with randomized
            exponential backoff. If all retries fail, the raised HttpError
            represents the last request. If zero (default), we attempt the
            request only once.

    Returns:
      (status, done): (MediaDownloadStatus, boolean)
         The value of 'done' will be True when the media has been fully
         downloaded.

    Raises:
      apiclient.errors.HttpError if the response was not a 2xx.
      httplib2.HttpLib2Error if a transport error has occured.
    """
    headers = {
        'range': 'bytes=%d-%d' % (
            self._progress, self._progress + self._chunksize)
        }
    http = self._request.http

    for retry_num in xrange(num_retries + 1):
      if retry_num > 0:
        self._sleep(self._rand() * 2**retry_num)
        logging.warning(
            'Retry #%d for media download: GET %s, following status: %d'
            % (retry_num, self._uri, resp.status))

      resp, content = http.request(self._uri, headers=headers)
      if resp.status < 500:
        break

    if resp.status in [200, 206]:
      if 'content-location' in resp and resp['content-location'] != self._uri:
        self._uri = resp['content-location']
      self._progress += len(content)
      self._fd.write(content)

      if 'content-range' in resp:
        content_range = resp['content-range']
        length = content_range.rsplit('/', 1)[1]
        self._total_size = int(length)

      if self._progress == self._total_size:
        self._done = True
      return MediaDownloadProgress(self._progress, self._total_size), self._done
    else:
      raise HttpError(resp, content, uri=self._uri)


class _StreamSlice(object):
  """Truncated stream.

  Takes a stream and presents a stream that is a slice of the original stream.
  This is used when uploading media in chunks. In later versions of Python a
  stream can be passed to httplib in place of the string of data to send. The
  problem is that httplib just blindly reads to the end of the stream. This
  wrapper presents a virtual stream that only reads to the end of the chunk.
  """

  def __init__(self, stream, begin, chunksize):
    """Constructor.

    Args:
      stream: (io.Base, file object), the stream to wrap.
      begin: int, the seek position the chunk begins at.
      chunksize: int, the size of the chunk.
    """
    self._stream = stream
    self._begin = begin
    self._chunksize = chunksize
    self._stream.seek(begin)

  def read(self, n=-1):
    """Read n bytes.

    Args:
      n, int, the number of bytes to read.

    Returns:
      A string of length 'n', or less if EOF is reached.
    """
    # The data left available to read sits in [cur, end)
    cur = self._stream.tell()
    end = self._begin + self._chunksize
    if n == -1 or cur + n > end:
      n = end - cur
    return self._stream.read(n)


class HttpRequest(object):
  """Encapsulates a single HTTP request."""

  @util.positional(4)
  def __init__(self, http, postproc, uri,
               method='GET',
               body=None,
               headers=None,
               methodId=None,
               resumable=None):
    """Constructor for an HttpRequest.

    Args:
      http: httplib2.Http, the transport object to use to make a request
      postproc: callable, called on the HTTP response and content to transform
                it into a data object before returning, or raising an exception
                on an error.
      uri: string, the absolute URI to send the request to
      method: string, the HTTP method to use
      body: string, the request body of the HTTP request,
      headers: dict, the HTTP request headers
      methodId: string, a unique identifier for the API method being called.
      resumable: MediaUpload, None if this is not a resumbale request.
    """
    self.uri = uri
    self.method = method
    self.body = body
    self.headers = headers or {}
    self.methodId = methodId
    self.http = http
    self.postproc = postproc
    self.resumable = resumable
    self.response_callbacks = []
    self._in_error_state = False

    # Pull the multipart boundary out of the content-type header.
    major, minor, params = mimeparse.parse_mime_type(
        headers.get('content-type', 'application/json'))

    # The size of the non-media part of the request.
    self.body_size = len(self.body or '')

    # The resumable URI to send chunks to.
    self.resumable_uri = None

    # The bytes that have been uploaded.
    self.resumable_progress = 0

    # Stubs for testing.
    self._rand = random.random
    self._sleep = time.sleep

  @util.positional(1)
  def execute(self, http=None, num_retries=0):
    """Execute the request.

    Args:
      http: httplib2.Http, an http object to be used in place of the
            one the HttpRequest request object was constructed with.
      num_retries: Integer, number of times to retry 500's with randomized
            exponential backoff. If all retries fail, the raised HttpError
            represents the last request. If zero (default), we attempt the
            request only once.

    Returns:
      A deserialized object model of the response body as determined
      by the postproc.

    Raises:
      apiclient.errors.HttpError if the response was not a 2xx.
      httplib2.HttpLib2Error if a transport error has occured.
    """
    if http is None:
      http = self.http

    if self.resumable:
      body = None
      while body is None:
        _, body = self.next_chunk(http=http, num_retries=num_retries)
      return body

    # Non-resumable case.

    if 'content-length' not in self.headers:
      self.headers['content-length'] = str(self.body_size)
    # If the request URI is too long then turn it into a POST request.
    if len(self.uri) > MAX_URI_LENGTH and self.method == 'GET':
      self.method = 'POST'
      self.headers['x-http-method-override'] = 'GET'
      self.headers['content-type'] = 'application/x-www-form-urlencoded'
      parsed = urlparse.urlparse(self.uri)
      self.uri = urlparse.urlunparse(
          (parsed.scheme, parsed.netloc, parsed.path, parsed.params, None,
           None)
          )
      self.body = parsed.query
      self.headers['content-length'] = str(len(self.body))

    # Handle retries for server-side errors.
    for retry_num in xrange(num_retries + 1):
      if retry_num > 0:
        self._sleep(self._rand() * 2**retry_num)
        logging.warning('Retry #%d for request: %s %s, following status: %d'
                        % (retry_num, self.method, self.uri, resp.status))

      resp, content = http.request(str(self.uri), method=str(self.method),
                                   body=self.body, headers=self.headers)
      if resp.status < 500:
        break

    for callback in self.response_callbacks:
      callback(resp)
    if resp.status >= 300:
      raise HttpError(resp, content, uri=self.uri)
    return self.postproc(resp, content)

  @util.positional(2)
  def add_response_callback(self, cb):
    """add_response_headers_callback

    Args:
      cb: Callback to be called on receiving the response headers, of signature:

      def cb(resp):
        # Where resp is an instance of httplib2.Response
    """
    self.response_callbacks.append(cb)

  @util.positional(1)
  def next_chunk(self, http=None, num_retries=0):
    """Execute the next step of a resumable upload.

    Can only be used if the method being executed supports media uploads and
    the MediaUpload object passed in was flagged as using resumable upload.

    Example:

      media = MediaFileUpload('cow.png', mimetype='image/png',
                              chunksize=1000, resumable=True)
      request = farm.animals().insert(
          id='cow',
          name='cow.png',
          media_body=media)

      response = None
      while response is None:
        status, response = request.next_chunk()
        if status:
          print "Upload %d%% complete." % int(status.progress() * 100)


    Args:
      http: httplib2.Http, an http object to be used in place of the
            one the HttpRequest request object was constructed with.
      num_retries: Integer, number of times to retry 500's with randomized
            exponential backoff. If all retries fail, the raised HttpError
            represents the last request. If zero (default), we attempt the
            request only once.

    Returns:
      (status, body): (ResumableMediaStatus, object)
         The body will be None until the resumable media is fully uploaded.

    Raises:
      apiclient.errors.HttpError if the response was not a 2xx.
      httplib2.HttpLib2Error if a transport error has occured.
    """
    if http is None:
      http = self.http

    if self.resumable.size() is None:
      size = '*'
    else:
      size = str(self.resumable.size())

    if self.resumable_uri is None:
      start_headers = copy.copy(self.headers)
      start_headers['X-Upload-Content-Type'] = self.resumable.mimetype()
      if size != '*':
        start_headers['X-Upload-Content-Length'] = size
      start_headers['content-length'] = str(self.body_size)

      for retry_num in xrange(num_retries + 1):
        if retry_num > 0:
          self._sleep(self._rand() * 2**retry_num)
          logging.warning(
              'Retry #%d for resumable URI request: %s %s, following status: %d'
              % (retry_num, self.method, self.uri, resp.status))

        resp, content = http.request(self.uri, method=self.method,
                                     body=self.body,
                                     headers=start_headers)
        if resp.status < 500:
          break

      if resp.status == 200 and 'location' in resp:
        self.resumable_uri = resp['location']
      else:
        raise ResumableUploadError(resp, content)
    elif self._in_error_state:
      # If we are in an error state then query the server for current state of
      # the upload by sending an empty PUT and reading the 'range' header in
      # the response.
      headers = {
          'Content-Range': 'bytes */%s' % size,
          'content-length': '0'
          }
      resp, content = http.request(self.resumable_uri, 'PUT',
                                   headers=headers)
      status, body = self._process_response(resp, content)
      if body:
        # The upload was complete.
        return (status, body)

    # The httplib.request method can take streams for the body parameter, but
    # only in Python 2.6 or later. If a stream is available under those
    # conditions then use it as the body argument.
    if self.resumable.has_stream() and sys.version_info[1] >= 6:
      data = self.resumable.stream()
      if self.resumable.chunksize() == -1:
        data.seek(self.resumable_progress)
        chunk_end = self.resumable.size() - self.resumable_progress - 1
      else:
        # Doing chunking with a stream, so wrap a slice of the stream.
        data = _StreamSlice(data, self.resumable_progress,
                            self.resumable.chunksize())
        chunk_end = min(
            self.resumable_progress + self.resumable.chunksize() - 1,
            self.resumable.size() - 1)
    else:
      data = self.resumable.getbytes(
          self.resumable_progress, self.resumable.chunksize())

      # A short read implies that we are at EOF, so finish the upload.
      if len(data) < self.resumable.chunksize():
        size = str(self.resumable_progress + len(data))

      chunk_end = self.resumable_progress + len(data) - 1

    headers = {
        'Content-Range': 'bytes %d-%d/%s' % (
            self.resumable_progress, chunk_end, size),
        # Must set the content-length header here because httplib can't
        # calculate the size when working with _StreamSlice.
        'Content-Length': str(chunk_end - self.resumable_progress + 1)
        }

    for retry_num in xrange(num_retries + 1):
      if retry_num > 0:
        self._sleep(self._rand() * 2**retry_num)
        logging.warning(
            'Retry #%d for media upload: %s %s, following status: %d'
            % (retry_num, self.method, self.uri, resp.status))

      try:
        resp, content = http.request(self.resumable_uri, method='PUT',
                                     body=data,
                                     headers=headers)
      except:
        self._in_error_state = True
        raise
      if resp.status < 500:
        break

    return self._process_response(resp, content)

  def _process_response(self, resp, content):
    """Process the response from a single chunk upload.

    Args:
      resp: httplib2.Response, the response object.
      content: string, the content of the response.

    Returns:
      (status, body): (ResumableMediaStatus, object)
         The body will be None until the resumable media is fully uploaded.

    Raises:
      apiclient.errors.HttpError if the response was not a 2xx or a 308.
    """
    if resp.status in [200, 201]:
      self._in_error_state = False
      return None, self.postproc(resp, content)
    elif resp.status == 308:
      self._in_error_state = False
      # A "308 Resume Incomplete" indicates we are not done.
      self.resumable_progress = int(resp['range'].split('-')[1]) + 1
      if 'location' in resp:
        self.resumable_uri = resp['location']
    else:
      self._in_error_state = True
      raise HttpError(resp, content, uri=self.uri)

    return (MediaUploadProgress(self.resumable_progress, self.resumable.size()),
            None)

  def to_json(self):
    """Returns a JSON representation of the HttpRequest."""
    d = copy.copy(self.__dict__)
    if d['resumable'] is not None:
      d['resumable'] = self.resumable.to_json()
    del d['http']
    del d['postproc']
    del d['_sleep']
    del d['_rand']

    return simplejson.dumps(d)

  @staticmethod
  def from_json(s, http, postproc):
    """Returns an HttpRequest populated with info from a JSON object."""
    d = simplejson.loads(s)
    if d['resumable'] is not None:
      d['resumable'] = MediaUpload.new_from_json(d['resumable'])
    return HttpRequest(
        http,
        postproc,
        uri=d['uri'],
        method=d['method'],
        body=d['body'],
        headers=d['headers'],
        methodId=d['methodId'],
        resumable=d['resumable'])


class BatchHttpRequest(object):
  """Batches multiple HttpRequest objects into a single HTTP request.

  Example:
    from apiclient.http import BatchHttpRequest

    def list_animals(request_id, response, exception):
      \"\"\"Do something with the animals list response.\"\"\"
      if exception is not None:
        # Do something with the exception.
        pass
      else:
        # Do something with the response.
        pass

    def list_farmers(request_id, response, exception):
      \"\"\"Do something with the farmers list response.\"\"\"
      if exception is not None:
        # Do something with the exception.
        pass
      else:
        # Do something with the response.
        pass

    service = build('farm', 'v2')

    batch = BatchHttpRequest()

    batch.add(service.animals().list(), list_animals)
    batch.add(service.farmers().list(), list_farmers)
    batch.execute(http=http)
  """

  @util.positional(1)
  def __init__(self, callback=None, batch_uri=None):
    """Constructor for a BatchHttpRequest.

    Args:
      callback: callable, A callback to be called for each response, of the
        form callback(id, response, exception). The first parameter is the
        request id, and the second is the deserialized response object. The
        third is an apiclient.errors.HttpError exception object if an HTTP error
        occurred while processing the request, or None if no error occurred.
      batch_uri: string, URI to send batch requests to.
    """
    if batch_uri is None:
      batch_uri = 'https://www.googleapis.com/batch'
    self._batch_uri = batch_uri

    # Global callback to be called for each individual response in the batch.
    self._callback = callback

    # A map from id to request.
    self._requests = {}

    # A map from id to callback.
    self._callbacks = {}

    # List of request ids, in the order in which they were added.
    self._order = []

    # The last auto generated id.
    self._last_auto_id = 0

    # Unique ID on which to base the Content-ID headers.
    self._base_id = None

    # A map from request id to (httplib2.Response, content) response pairs
    self._responses = {}

    # A map of id(Credentials) that have been refreshed.
    self._refreshed_credentials = {}

  def _refresh_and_apply_credentials(self, request, http):
    """Refresh the credentials and apply to the request.

    Args:
      request: HttpRequest, the request.
      http: httplib2.Http, the global http object for the batch.
    """
    # For the credentials to refresh, but only once per refresh_token
    # If there is no http per the request then refresh the http passed in
    # via execute()
    creds = None
    if request.http is not None and hasattr(request.http.request,
        'credentials'):
      creds = request.http.request.credentials
    elif http is not None and hasattr(http.request, 'credentials'):
      creds = http.request.credentials
    if creds is not None:
      if id(creds) not in self._refreshed_credentials:
        creds.refresh(http)
        self._refreshed_credentials[id(creds)] = 1

    # Only apply the credentials if we are using the http object passed in,
    # otherwise apply() will get called during _serialize_request().
    if request.http is None or not hasattr(request.http.request,
        'credentials'):
      creds.apply(request.headers)

  def _id_to_header(self, id_):
    """Convert an id to a Content-ID header value.

    Args:
      id_: string, identifier of individual request.

    Returns:
      A Content-ID header with the id_ encoded into it. A UUID is prepended to
      the value because Content-ID headers are supposed to be universally
      unique.
    """
    if self._base_id is None:
      self._base_id = uuid.uuid4()

    return '<%s+%s>' % (self._base_id, urllib.quote(id_))

  def _header_to_id(self, header):
    """Convert a Content-ID header value to an id.

    Presumes the Content-ID header conforms to the format that _id_to_header()
    returns.

    Args:
      header: string, Content-ID header value.

    Returns:
      The extracted id value.

    Raises:
      BatchError if the header is not in the expected format.
    """
    if header[0] != '<' or header[-1] != '>':
      raise BatchError("Invalid value for Content-ID: %s" % header)
    if '+' not in header:
      raise BatchError("Invalid value for Content-ID: %s" % header)
    base, id_ = header[1:-1].rsplit('+', 1)

    return urllib.unquote(id_)

  def _serialize_request(self, request):
    """Convert an HttpRequest object into a string.

    Args:
      request: HttpRequest, the request to serialize.

    Returns:
      The request as a string in application/http format.
    """
    # Construct status line
    parsed = urlparse.urlparse(request.uri)
    request_line = urlparse.urlunparse(
        (None, None, parsed.path, parsed.params, parsed.query, None)
        )
    status_line = request.method + ' ' + request_line + ' HTTP/1.1\n'
    major, minor = request.headers.get('content-type', 'application/json').split('/')
    msg = MIMENonMultipart(major, minor)
    headers = request.headers.copy()

    if request.http is not None and hasattr(request.http.request,
        'credentials'):
      request.http.request.credentials.apply(headers)

    # MIMENonMultipart adds its own Content-Type header.
    if 'content-type' in headers:
      del headers['content-type']

    for key, value in headers.iteritems():
      msg[key] = value
    msg['Host'] = parsed.netloc
    msg.set_unixfrom(None)

    if request.body is not None:
      msg.set_payload(request.body)
      msg['content-length'] = str(len(request.body))

    # Serialize the mime message.
    fp = StringIO.StringIO()
    # maxheaderlen=0 means don't line wrap headers.
    g = Generator(fp, maxheaderlen=0)
    g.flatten(msg, unixfrom=False)
    body = fp.getvalue()

    # Strip off the \n\n that the MIME lib tacks onto the end of the payload.
    if request.body is None:
      body = body[:-2]

    return status_line.encode('utf-8') + body

  def _deserialize_response(self, payload):
    """Convert string into httplib2 response and content.

    Args:
      payload: string, headers and body as a string.

    Returns:
      A pair (resp, content), such as would be returned from httplib2.request.
    """
    # Strip off the status line
    status_line, payload = payload.split('\n', 1)
    protocol, status, reason = status_line.split(' ', 2)

    # Parse the rest of the response
    parser = FeedParser()
    parser.feed(payload)
    msg = parser.close()
    msg['status'] = status

    # Create httplib2.Response from the parsed headers.
    resp = httplib2.Response(msg)
    resp.reason = reason
    resp.version = int(protocol.split('/', 1)[1].replace('.', ''))

    content = payload.split('\r\n\r\n', 1)[1]

    return resp, content

  def _new_id(self):
    """Create a new id.

    Auto incrementing number that avoids conflicts with ids already used.

    Returns:
       string, a new unique id.
    """
    self._last_auto_id += 1
    while str(self._last_auto_id) in self._requests:
      self._last_auto_id += 1
    return str(self._last_auto_id)

  @util.positional(2)
  def add(self, request, callback=None, request_id=None):
    """Add a new request.

    Every callback added will be paired with a unique id, the request_id. That
    unique id will be passed back to the callback when the response comes back
    from the server. The default behavior is to have the library generate it's
    own unique id. If the caller passes in a request_id then they must ensure
    uniqueness for each request_id, and if they are not an exception is
    raised. Callers should either supply all request_ids or nevery supply a
    request id, to avoid such an error.

    Args:
      request: HttpRequest, Request to add to the batch.
      callback: callable, A callback to be called for this response, of the
        form callback(id, response, exception). The first parameter is the
        request id, and the second is the deserialized response object. The
        third is an apiclient.errors.HttpError exception object if an HTTP error
        occurred while processing the request, or None if no errors occurred.
      request_id: string, A unique id for the request. The id will be passed to
        the callback with the response.

    Returns:
      None

    Raises:
      BatchError if a media request is added to a batch.
      KeyError is the request_id is not unique.
    """
    if request_id is None:
      request_id = self._new_id()
    if request.resumable is not None:
      raise BatchError("Media requests cannot be used in a batch request.")
    if request_id in self._requests:
      raise KeyError("A request with this ID already exists: %s" % request_id)
    self._requests[request_id] = request
    self._callbacks[request_id] = callback
    self._order.append(request_id)

  def _execute(self, http, order, requests):
    """Serialize batch request, send to server, process response.

    Args:
      http: httplib2.Http, an http object to be used to make the request with.
      order: list, list of request ids in the order they were added to the
        batch.
      request: list, list of request objects to send.

    Raises:
      httplib2.HttpLib2Error if a transport error has occured.
      apiclient.errors.BatchError if the response is the wrong format.
    """
    message = MIMEMultipart('mixed')
    # Message should not write out it's own headers.
    setattr(message, '_write_headers', lambda self: None)

    # Add all the individual requests.
    for request_id in order:
      request = requests[request_id]

      msg = MIMENonMultipart('application', 'http')
      msg['Content-Transfer-Encoding'] = 'binary'
      msg['Content-ID'] = self._id_to_header(request_id)

      body = self._serialize_request(request)
      msg.set_payload(body)
      message.attach(msg)

    body = message.as_string()

    headers = {}
    headers['content-type'] = ('multipart/mixed; '
                               'boundary="%s"') % message.get_boundary()

    resp, content = http.request(self._batch_uri, method='POST', body=body,
                                 headers=headers)

    if resp.status >= 300:
      raise HttpError(resp, content, uri=self._batch_uri)

    # Now break out the individual responses and store each one.
    boundary, _ = content.split(None, 1)

    # Prepend with a content-type header so FeedParser can handle it.
    header = 'content-type: %s\r\n\r\n' % resp['content-type']
    for_parser = header + content

    parser = FeedParser()
    parser.feed(for_parser)
    mime_response = parser.close()

    if not mime_response.is_multipart():
      raise BatchError("Response not in multipart/mixed format.", resp=resp,
                       content=content)

    for part in mime_response.get_payload():
      request_id = self._header_to_id(part['Content-ID'])
      response, content = self._deserialize_response(part.get_payload())
      self._responses[request_id] = (response, content)

  @util.positional(1)
  def execute(self, http=None):
    """Execute all the requests as a single batched HTTP request.

    Args:
      http: httplib2.Http, an http object to be used in place of the one the
        HttpRequest request object was constructed with. If one isn't supplied
        then use a http object from the requests in this batch.

    Returns:
      None

    Raises:
      httplib2.HttpLib2Error if a transport error has occured.
      apiclient.errors.BatchError if the response is the wrong format.
    """

    # If http is not supplied use the first valid one given in the requests.
    if http is None:
      for request_id in self._order:
        request = self._requests[request_id]
        if request is not None:
          http = request.http
          break

    if http is None:
      raise ValueError("Missing a valid http object.")

    self._execute(http, self._order, self._requests)

    # Loop over all the requests and check for 401s. For each 401 request the
    # credentials should be refreshed and then sent again in a separate batch.
    redo_requests = {}
    redo_order = []

    for request_id in self._order:
      resp, content = self._responses[request_id]
      if resp['status'] == '401':
        redo_order.append(request_id)
        request = self._requests[request_id]
        self._refresh_and_apply_credentials(request, http)
        redo_requests[request_id] = request

    if redo_requests:
      self._execute(http, redo_order, redo_requests)

    # Now process all callbacks that are erroring, and raise an exception for
    # ones that return a non-2xx response? Or add extra parameter to callback
    # that contains an HttpError?

    for request_id in self._order:
      resp, content = self._responses[request_id]

      request = self._requests[request_id]
      callback = self._callbacks[request_id]

      response = None
      exception = None
      try:
        if resp.status >= 300:
          raise HttpError(resp, content, uri=request.uri)
        response = request.postproc(resp, content)
      except HttpError, e:
        exception = e

      if callback is not None:
        callback(request_id, response, exception)
      if self._callback is not None:
        self._callback(request_id, response, exception)


class HttpRequestMock(object):
  """Mock of HttpRequest.

  Do not construct directly, instead use RequestMockBuilder.
  """

  def __init__(self, resp, content, postproc):
    """Constructor for HttpRequestMock

    Args:
      resp: httplib2.Response, the response to emulate coming from the request
      content: string, the response body
      postproc: callable, the post processing function usually supplied by
                the model class. See model.JsonModel.response() as an example.
    """
    self.resp = resp
    self.content = content
    self.postproc = postproc
    if resp is None:
      self.resp = httplib2.Response({'status': 200, 'reason': 'OK'})
    if 'reason' in self.resp:
      self.resp.reason = self.resp['reason']

  def execute(self, http=None):
    """Execute the request.

    Same behavior as HttpRequest.execute(), but the response is
    mocked and not really from an HTTP request/response.
    """
    return self.postproc(self.resp, self.content)


class RequestMockBuilder(object):
  """A simple mock of HttpRequest

    Pass in a dictionary to the constructor that maps request methodIds to
    tuples of (httplib2.Response, content, opt_expected_body) that should be
    returned when that method is called. None may also be passed in for the
    httplib2.Response, in which case a 200 OK response will be generated.
    If an opt_expected_body (str or dict) is provided, it will be compared to
    the body and UnexpectedBodyError will be raised on inequality.

    Example:
      response = '{"data": {"id": "tag:google.c...'
      requestBuilder = RequestMockBuilder(
        {
          'plus.activities.get': (None, response),
        }
      )
      apiclient.discovery.build("plus", "v1", requestBuilder=requestBuilder)

    Methods that you do not supply a response for will return a
    200 OK with an empty string as the response content or raise an excpetion
    if check_unexpected is set to True. The methodId is taken from the rpcName
    in the discovery document.

    For more details see the project wiki.
  """

  def __init__(self, responses, check_unexpected=False):
    """Constructor for RequestMockBuilder

    The constructed object should be a callable object
    that can replace the class HttpResponse.

    responses - A dictionary that maps methodIds into tuples
                of (httplib2.Response, content). The methodId
                comes from the 'rpcName' field in the discovery
                document.
    check_unexpected - A boolean setting whether or not UnexpectedMethodError
                       should be raised on unsupplied method.
    """
    self.responses = responses
    self.check_unexpected = check_unexpected

  def __call__(self, http, postproc, uri, method='GET', body=None,
               headers=None, methodId=None, resumable=None):
    """Implements the callable interface that discovery.build() expects
    of requestBuilder, which is to build an object compatible with
    HttpRequest.execute(). See that method for the description of the
    parameters and the expected response.
    """
    if methodId in self.responses:
      response = self.responses[methodId]
      resp, content = response[:2]
      if len(response) > 2:
        # Test the body against the supplied expected_body.
        expected_body = response[2]
        if bool(expected_body) != bool(body):
          # Not expecting a body and provided one
          # or expecting a body and not provided one.
          raise UnexpectedBodyError(expected_body, body)
        if isinstance(expected_body, str):
          expected_body = simplejson.loads(expected_body)
        body = simplejson.loads(body)
        if body != expected_body:
          raise UnexpectedBodyError(expected_body, body)
      return HttpRequestMock(resp, content, postproc)
    elif self.check_unexpected:
      raise UnexpectedMethodError(methodId=methodId)
    else:
      model = JsonModel(False)
      return HttpRequestMock(None, '{}', model.response)


class HttpMock(object):
  """Mock of httplib2.Http"""

  def __init__(self, filename=None, headers=None):
    """
    Args:
      filename: string, absolute filename to read response from
      headers: dict, header to return with response
    """
    if headers is None:
      headers = {'status': '200 OK'}
    if filename:
      f = file(filename, 'r')
      self.data = f.read()
      f.close()
    else:
      self.data = None
    self.response_headers = headers
    self.headers = None
    self.uri = None
    self.method = None
    self.body = None
    self.headers = None


  def request(self, uri,
              method='GET',
              body=None,
              headers=None,
              redirections=1,
              connection_type=None):
    self.uri = uri
    self.method = method
    self.body = body
    self.headers = headers
    return httplib2.Response(self.response_headers), self.data


class HttpMockSequence(object):
  """Mock of httplib2.Http

  Mocks a sequence of calls to request returning different responses for each
  call. Create an instance initialized with the desired response headers
  and content and then use as if an httplib2.Http instance.

    http = HttpMockSequence([
      ({'status': '401'}, ''),
      ({'status': '200'}, '{"access_token":"1/3w","expires_in":3600}'),
      ({'status': '200'}, 'echo_request_headers'),
      ])
    resp, content = http.request("http://examples.com")

  There are special values you can pass in for content to trigger
  behavours that are helpful in testing.

  'echo_request_headers' means return the request headers in the response body
  'echo_request_headers_as_json' means return the request headers in
     the response body
  'echo_request_body' means return the request body in the response body
  'echo_request_uri' means return the request uri in the response body
  """

  def __init__(self, iterable):
    """
    Args:
      iterable: iterable, a sequence of pairs of (headers, body)
    """
    self._iterable = iterable
    self.follow_redirects = True

  def request(self, uri,
              method='GET',
              body=None,
              headers=None,
              redirections=1,
              connection_type=None):
    resp, content = self._iterable.pop(0)
    if content == 'echo_request_headers':
      content = headers
    elif content == 'echo_request_headers_as_json':
      content = simplejson.dumps(headers)
    elif content == 'echo_request_body':
      if hasattr(body, 'read'):
        content = body.read()
      else:
        content = body
    elif content == 'echo_request_uri':
      content = uri
    return httplib2.Response(resp), content


def set_user_agent(http, user_agent):
  """Set the user-agent on every request.

  Args:
     http - An instance of httplib2.Http
         or something that acts like it.
     user_agent: string, the value for the user-agent header.

  Returns:
     A modified instance of http that was passed in.

  Example:

    h = httplib2.Http()
    h = set_user_agent(h, "my-app-name/6.0")

  Most of the time the user-agent will be set doing auth, this is for the rare
  cases where you are accessing an unauthenticated endpoint.
  """
  request_orig = http.request

  # The closure that will replace 'httplib2.Http.request'.
  def new_request(uri, method='GET', body=None, headers=None,
                  redirections=httplib2.DEFAULT_MAX_REDIRECTS,
                  connection_type=None):
    """Modify the request headers to add the user-agent."""
    if headers is None:
      headers = {}
    if 'user-agent' in headers:
      headers['user-agent'] = user_agent + ' ' + headers['user-agent']
    else:
      headers['user-agent'] = user_agent
    resp, content = request_orig(uri, method, body, headers,
                        redirections, connection_type)
    return resp, content

  http.request = new_request
  return http


def tunnel_patch(http):
  """Tunnel PATCH requests over POST.
  Args:
     http - An instance of httplib2.Http
         or something that acts like it.

  Returns:
     A modified instance of http that was passed in.

  Example:

    h = httplib2.Http()
    h = tunnel_patch(h, "my-app-name/6.0")

  Useful if you are running on a platform that doesn't support PATCH.
  Apply this last if you are using OAuth 1.0, as changing the method
  will result in a different signature.
  """
  request_orig = http.request

  # The closure that will replace 'httplib2.Http.request'.
  def new_request(uri, method='GET', body=None, headers=None,
                  redirections=httplib2.DEFAULT_MAX_REDIRECTS,
                  connection_type=None):
    """Modify the request headers to add the user-agent."""
    if headers is None:
      headers = {}
    if method == 'PATCH':
      if 'oauth_token' in headers.get('authorization', ''):
        logging.warning(
            'OAuth 1.0 request made with Credentials after tunnel_patch.')
      headers['x-http-method-override'] = "PATCH"
      method = 'POST'
    resp, content = request_orig(uri, method, body, headers,
                        redirections, connection_type)
    return resp, content

  http.request = new_request
  return http

########NEW FILE########
__FILENAME__ = mimeparse
# Copyright (C) 2007 Joe Gregorio
#
# Licensed under the MIT License

"""MIME-Type Parser

This module provides basic functions for handling mime-types. It can handle
matching mime-types against a list of media-ranges. See section 14.1 of the
HTTP specification [RFC 2616] for a complete explanation.

   http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.1

Contents:
 - parse_mime_type():   Parses a mime-type into its component parts.
 - parse_media_range(): Media-ranges are mime-types with wild-cards and a 'q'
                          quality parameter.
 - quality():           Determines the quality ('q') of a mime-type when
                          compared against a list of media-ranges.
 - quality_parsed():    Just like quality() except the second parameter must be
                          pre-parsed.
 - best_match():        Choose the mime-type with the highest quality ('q')
                          from a list of candidates.
"""

__version__ = '0.1.3'
__author__ = 'Joe Gregorio'
__email__ = 'joe@bitworking.org'
__license__ = 'MIT License'
__credits__ = ''


def parse_mime_type(mime_type):
    """Parses a mime-type into its component parts.

    Carves up a mime-type and returns a tuple of the (type, subtype, params)
    where 'params' is a dictionary of all the parameters for the media range.
    For example, the media range 'application/xhtml;q=0.5' would get parsed
    into:

       ('application', 'xhtml', {'q', '0.5'})
       """
    parts = mime_type.split(';')
    params = dict([tuple([s.strip() for s in param.split('=', 1)])\
            for param in parts[1:]
                  ])
    full_type = parts[0].strip()
    # Java URLConnection class sends an Accept header that includes a
    # single '*'. Turn it into a legal wildcard.
    if full_type == '*':
        full_type = '*/*'
    (type, subtype) = full_type.split('/')

    return (type.strip(), subtype.strip(), params)


def parse_media_range(range):
    """Parse a media-range into its component parts.

    Carves up a media range and returns a tuple of the (type, subtype,
    params) where 'params' is a dictionary of all the parameters for the media
    range.  For example, the media range 'application/*;q=0.5' would get parsed
    into:

       ('application', '*', {'q', '0.5'})

    In addition this function also guarantees that there is a value for 'q'
    in the params dictionary, filling it in with a proper default if
    necessary.
    """
    (type, subtype, params) = parse_mime_type(range)
    if not params.has_key('q') or not params['q'] or \
            not float(params['q']) or float(params['q']) > 1\
            or float(params['q']) < 0:
        params['q'] = '1'

    return (type, subtype, params)


def fitness_and_quality_parsed(mime_type, parsed_ranges):
    """Find the best match for a mime-type amongst parsed media-ranges.

    Find the best match for a given mime-type against a list of media_ranges
    that have already been parsed by parse_media_range(). Returns a tuple of
    the fitness value and the value of the 'q' quality parameter of the best
    match, or (-1, 0) if no match was found. Just as for quality_parsed(),
    'parsed_ranges' must be a list of parsed media ranges.
    """
    best_fitness = -1
    best_fit_q = 0
    (target_type, target_subtype, target_params) =\
            parse_media_range(mime_type)
    for (type, subtype, params) in parsed_ranges:
        type_match = (type == target_type or\
                      type == '*' or\
                      target_type == '*')
        subtype_match = (subtype == target_subtype or\
                         subtype == '*' or\
                         target_subtype == '*')
        if type_match and subtype_match:
            param_matches = reduce(lambda x, y: x + y, [1 for (key, value) in \
                    target_params.iteritems() if key != 'q' and \
                    params.has_key(key) and value == params[key]], 0)
            fitness = (type == target_type) and 100 or 0
            fitness += (subtype == target_subtype) and 10 or 0
            fitness += param_matches
            if fitness > best_fitness:
                best_fitness = fitness
                best_fit_q = params['q']

    return best_fitness, float(best_fit_q)


def quality_parsed(mime_type, parsed_ranges):
    """Find the best match for a mime-type amongst parsed media-ranges.

    Find the best match for a given mime-type against a list of media_ranges
    that have already been parsed by parse_media_range(). Returns the 'q'
    quality parameter of the best match, 0 if no match was found. This function
    bahaves the same as quality() except that 'parsed_ranges' must be a list of
    parsed media ranges.
    """

    return fitness_and_quality_parsed(mime_type, parsed_ranges)[1]


def quality(mime_type, ranges):
    """Return the quality ('q') of a mime-type against a list of media-ranges.

    Returns the quality 'q' of a mime-type when compared against the
    media-ranges in ranges. For example:

    >>> quality('text/html','text/*;q=0.3, text/html;q=0.7,
                  text/html;level=1, text/html;level=2;q=0.4, */*;q=0.5')
    0.7

    """
    parsed_ranges = [parse_media_range(r) for r in ranges.split(',')]

    return quality_parsed(mime_type, parsed_ranges)


def best_match(supported, header):
    """Return mime-type with the highest quality ('q') from list of candidates.

    Takes a list of supported mime-types and finds the best match for all the
    media-ranges listed in header. The value of header must be a string that
    conforms to the format of the HTTP Accept: header. The value of 'supported'
    is a list of mime-types. The list of supported mime-types should be sorted
    in order of increasing desirability, in case of a situation where there is
    a tie.

    >>> best_match(['application/xbel+xml', 'text/xml'],
                   'text/*;q=0.5,*/*; q=0.1')
    'text/xml'
    """
    split_header = _filter_blank(header.split(','))
    parsed_header = [parse_media_range(r) for r in split_header]
    weighted_matches = []
    pos = 0
    for mime_type in supported:
        weighted_matches.append((fitness_and_quality_parsed(mime_type,
                                 parsed_header), pos, mime_type))
        pos += 1
    weighted_matches.sort()

    return weighted_matches[-1][0][1] and weighted_matches[-1][2] or ''


def _filter_blank(i):
    for s in i:
        if s.strip():
            yield s

########NEW FILE########
__FILENAME__ = model
#!/usr/bin/python2.4
#
# Copyright (C) 2010 Google Inc.
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

"""Model objects for requests and responses.

Each API may support one or more serializations, such
as JSON, Atom, etc. The model classes are responsible
for converting between the wire format and the Python
object representation.
"""

__author__ = 'jcgregorio@google.com (Joe Gregorio)'

import logging
import urllib

from apiclient import __version__
from errors import HttpError
from oauth2client.anyjson import simplejson


dump_request_response = False


def _abstract():
  raise NotImplementedError('You need to override this function')


class Model(object):
  """Model base class.

  All Model classes should implement this interface.
  The Model serializes and de-serializes between a wire
  format such as JSON and a Python object representation.
  """

  def request(self, headers, path_params, query_params, body_value):
    """Updates outgoing requests with a serialized body.

    Args:
      headers: dict, request headers
      path_params: dict, parameters that appear in the request path
      query_params: dict, parameters that appear in the query
      body_value: object, the request body as a Python object, which must be
                  serializable.
    Returns:
      A tuple of (headers, path_params, query, body)

      headers: dict, request headers
      path_params: dict, parameters that appear in the request path
      query: string, query part of the request URI
      body: string, the body serialized in the desired wire format.
    """
    _abstract()

  def response(self, resp, content):
    """Convert the response wire format into a Python object.

    Args:
      resp: httplib2.Response, the HTTP response headers and status
      content: string, the body of the HTTP response

    Returns:
      The body de-serialized as a Python object.

    Raises:
      apiclient.errors.HttpError if a non 2xx response is received.
    """
    _abstract()


class BaseModel(Model):
  """Base model class.

  Subclasses should provide implementations for the "serialize" and
  "deserialize" methods, as well as values for the following class attributes.

  Attributes:
    accept: The value to use for the HTTP Accept header.
    content_type: The value to use for the HTTP Content-type header.
    no_content_response: The value to return when deserializing a 204 "No
        Content" response.
    alt_param: The value to supply as the "alt" query parameter for requests.
  """

  accept = None
  content_type = None
  no_content_response = None
  alt_param = None

  def _log_request(self, headers, path_params, query, body):
    """Logs debugging information about the request if requested."""
    if dump_request_response:
      logging.info('--request-start--')
      logging.info('-headers-start-')
      for h, v in headers.iteritems():
        logging.info('%s: %s', h, v)
      logging.info('-headers-end-')
      logging.info('-path-parameters-start-')
      for h, v in path_params.iteritems():
        logging.info('%s: %s', h, v)
      logging.info('-path-parameters-end-')
      logging.info('body: %s', body)
      logging.info('query: %s', query)
      logging.info('--request-end--')

  def request(self, headers, path_params, query_params, body_value):
    """Updates outgoing requests with a serialized body.

    Args:
      headers: dict, request headers
      path_params: dict, parameters that appear in the request path
      query_params: dict, parameters that appear in the query
      body_value: object, the request body as a Python object, which must be
                  serializable by simplejson.
    Returns:
      A tuple of (headers, path_params, query, body)

      headers: dict, request headers
      path_params: dict, parameters that appear in the request path
      query: string, query part of the request URI
      body: string, the body serialized as JSON
    """
    query = self._build_query(query_params)
    headers['accept'] = self.accept
    headers['accept-encoding'] = 'gzip, deflate'
    if 'user-agent' in headers:
      headers['user-agent'] += ' '
    else:
      headers['user-agent'] = ''
    headers['user-agent'] += 'google-api-python-client/%s (gzip)' % __version__

    if body_value is not None:
      headers['content-type'] = self.content_type
      body_value = self.serialize(body_value)
    self._log_request(headers, path_params, query, body_value)
    return (headers, path_params, query, body_value)

  def _build_query(self, params):
    """Builds a query string.

    Args:
      params: dict, the query parameters

    Returns:
      The query parameters properly encoded into an HTTP URI query string.
    """
    if self.alt_param is not None:
      params.update({'alt': self.alt_param})
    astuples = []
    for key, value in params.iteritems():
      if type(value) == type([]):
        for x in value:
          x = x.encode('utf-8')
          astuples.append((key, x))
      else:
        if getattr(value, 'encode', False) and callable(value.encode):
          value = value.encode('utf-8')
        astuples.append((key, value))
    return '?' + urllib.urlencode(astuples)

  def _log_response(self, resp, content):
    """Logs debugging information about the response if requested."""
    if dump_request_response:
      logging.info('--response-start--')
      for h, v in resp.iteritems():
        logging.info('%s: %s', h, v)
      if content:
        logging.info(content)
      logging.info('--response-end--')

  def response(self, resp, content):
    """Convert the response wire format into a Python object.

    Args:
      resp: httplib2.Response, the HTTP response headers and status
      content: string, the body of the HTTP response

    Returns:
      The body de-serialized as a Python object.

    Raises:
      apiclient.errors.HttpError if a non 2xx response is received.
    """
    self._log_response(resp, content)
    # Error handling is TBD, for example, do we retry
    # for some operation/error combinations?
    if resp.status < 300:
      if resp.status == 204:
        # A 204: No Content response should be treated differently
        # to all the other success states
        return self.no_content_response
      return self.deserialize(content)
    else:
      logging.debug('Content from bad request was: %s' % content)
      raise HttpError(resp, content)

  def serialize(self, body_value):
    """Perform the actual Python object serialization.

    Args:
      body_value: object, the request body as a Python object.

    Returns:
      string, the body in serialized form.
    """
    _abstract()

  def deserialize(self, content):
    """Perform the actual deserialization from response string to Python
    object.

    Args:
      content: string, the body of the HTTP response

    Returns:
      The body de-serialized as a Python object.
    """
    _abstract()


class JsonModel(BaseModel):
  """Model class for JSON.

  Serializes and de-serializes between JSON and the Python
  object representation of HTTP request and response bodies.
  """
  accept = 'application/json'
  content_type = 'application/json'
  alt_param = 'json'

  def __init__(self, data_wrapper=False):
    """Construct a JsonModel.

    Args:
      data_wrapper: boolean, wrap requests and responses in a data wrapper
    """
    self._data_wrapper = data_wrapper

  def serialize(self, body_value):
    if (isinstance(body_value, dict) and 'data' not in body_value and
        self._data_wrapper):
      body_value = {'data': body_value}
    return simplejson.dumps(body_value)

  def deserialize(self, content):
    content = content.decode('utf-8')
    body = simplejson.loads(content)
    if self._data_wrapper and isinstance(body, dict) and 'data' in body:
      body = body['data']
    return body

  @property
  def no_content_response(self):
    return {}


class RawModel(JsonModel):
  """Model class for requests that don't return JSON.

  Serializes and de-serializes between JSON and the Python
  object representation of HTTP request, and returns the raw bytes
  of the response body.
  """
  accept = '*/*'
  content_type = 'application/json'
  alt_param = None

  def deserialize(self, content):
    return content

  @property
  def no_content_response(self):
    return ''


class MediaModel(JsonModel):
  """Model class for requests that return Media.

  Serializes and de-serializes between JSON and the Python
  object representation of HTTP request, and returns the raw bytes
  of the response body.
  """
  accept = '*/*'
  content_type = 'application/json'
  alt_param = 'media'

  def deserialize(self, content):
    return content

  @property
  def no_content_response(self):
    return ''


class ProtocolBufferModel(BaseModel):
  """Model class for protocol buffers.

  Serializes and de-serializes the binary protocol buffer sent in the HTTP
  request and response bodies.
  """
  accept = 'application/x-protobuf'
  content_type = 'application/x-protobuf'
  alt_param = 'proto'

  def __init__(self, protocol_buffer):
    """Constructs a ProtocolBufferModel.

    The serialzed protocol buffer returned in an HTTP response will be
    de-serialized using the given protocol buffer class.

    Args:
      protocol_buffer: The protocol buffer class used to de-serialize a
      response from the API.
    """
    self._protocol_buffer = protocol_buffer

  def serialize(self, body_value):
    return body_value.SerializeToString()

  def deserialize(self, content):
    return self._protocol_buffer.FromString(content)

  @property
  def no_content_response(self):
    return self._protocol_buffer()


def makepatch(original, modified):
  """Create a patch object.

  Some methods support PATCH, an efficient way to send updates to a resource.
  This method allows the easy construction of patch bodies by looking at the
  differences between a resource before and after it was modified.

  Args:
    original: object, the original deserialized resource
    modified: object, the modified deserialized resource
  Returns:
    An object that contains only the changes from original to modified, in a
    form suitable to pass to a PATCH method.

  Example usage:
    item = service.activities().get(postid=postid, userid=userid).execute()
    original = copy.deepcopy(item)
    item['object']['content'] = 'This is updated.'
    service.activities.patch(postid=postid, userid=userid,
      body=makepatch(original, item)).execute()
  """
  patch = {}
  for key, original_value in original.iteritems():
    modified_value = modified.get(key, None)
    if modified_value is None:
      # Use None to signal that the element is deleted
      patch[key] = None
    elif original_value != modified_value:
      if type(original_value) == type({}):
        # Recursively descend objects
        patch[key] = makepatch(original_value, modified_value)
      else:
        # In the case of simple types or arrays we just replace
        patch[key] = modified_value
    else:
      # Don't add anything to patch if there's no change
      pass
  for key in modified:
    if key not in original:
      patch[key] = modified[key]

  return patch

########NEW FILE########
__FILENAME__ = sample_tools
# Copyright (C) 2013 Google Inc.
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

"""Utilities for making samples.

Consolidates a lot of code commonly repeated in sample applications.
"""

__author__ = 'jcgregorio@google.com (Joe Gregorio)'
__all__ = ['init']


import argparse
import httplib2
import os

from apiclient import discovery
from oauth2client import client
from oauth2client import file
from oauth2client import tools


def init(argv, name, version, doc, filename, scope=None, parents=[]):
  """A common initialization routine for samples.

  Many of the sample applications do the same initialization, which has now
  been consolidated into this function. This function uses common idioms found
  in almost all the samples, i.e. for an API with name 'apiname', the
  credentials are stored in a file named apiname.dat, and the
  client_secrets.json file is stored in the same directory as the application
  main file.

  Args:
    argv: list of string, the command-line parameters of the application.
    name: string, name of the API.
    version: string, version of the API.
    doc: string, description of the application. Usually set to __doc__.
    file: string, filename of the application. Usually set to __file__.
    parents: list of argparse.ArgumentParser, additional command-line flags.
    scope: string, The OAuth scope used.

  Returns:
    A tuple of (service, flags), where service is the service object and flags
    is the parsed command-line flags.
  """
  if scope is None:
    scope = 'https://www.googleapis.com/auth/' + name

  # Parser command-line arguments.
  parent_parsers = [tools.argparser]
  parent_parsers.extend(parents)
  parser = argparse.ArgumentParser(
      description=doc,
      formatter_class=argparse.RawDescriptionHelpFormatter,
      parents=parent_parsers)
  flags = parser.parse_args(argv[1:])

  # Name of a file containing the OAuth 2.0 information for this
  # application, including client_id and client_secret, which are found
  # on the API Access tab on the Google APIs
  # Console <http://code.google.com/apis/console>.
  client_secrets = os.path.join(os.path.dirname(filename),
                                'client_secrets.json')

  # Set up a Flow object to be used if we need to authenticate.
  flow = client.flow_from_clientsecrets(client_secrets,
      scope=scope,
      message=tools.message_if_missing(client_secrets))

  # Prepare credentials, and authorize HTTP object with them.
  # If the credentials don't exist or are invalid run through the native client
  # flow. The Storage object will ensure that if successful the good
  # credentials will get written back to a file.
  storage = file.Storage(name + '.dat')
  credentials = storage.get()
  if credentials is None or credentials.invalid:
    credentials = tools.run_flow(flow, storage, flags)
  http = credentials.authorize(http = httplib2.Http())

  # Construct a service object via the discovery service.
  service = discovery.build(name, version, http=http)
  return (service, flags)

########NEW FILE########
__FILENAME__ = schema
# Copyright (C) 2010 Google Inc.
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

"""Schema processing for discovery based APIs

Schemas holds an APIs discovery schemas. It can return those schema as
deserialized JSON objects, or pretty print them as prototype objects that
conform to the schema.

For example, given the schema:

 schema = \"\"\"{
   "Foo": {
    "type": "object",
    "properties": {
     "etag": {
      "type": "string",
      "description": "ETag of the collection."
     },
     "kind": {
      "type": "string",
      "description": "Type of the collection ('calendar#acl').",
      "default": "calendar#acl"
     },
     "nextPageToken": {
      "type": "string",
      "description": "Token used to access the next
         page of this result. Omitted if no further results are available."
     }
    }
   }
 }\"\"\"

 s = Schemas(schema)
 print s.prettyPrintByName('Foo')

 Produces the following output:

  {
   "nextPageToken": "A String", # Token used to access the
       # next page of this result. Omitted if no further results are available.
   "kind": "A String", # Type of the collection ('calendar#acl').
   "etag": "A String", # ETag of the collection.
  },

The constructor takes a discovery document in which to look up named schema.
"""

# TODO(jcgregorio) support format, enum, minimum, maximum

__author__ = 'jcgregorio@google.com (Joe Gregorio)'

import copy

from oauth2client import util
from oauth2client.anyjson import simplejson


class Schemas(object):
  """Schemas for an API."""

  def __init__(self, discovery):
    """Constructor.

    Args:
      discovery: object, Deserialized discovery document from which we pull
        out the named schema.
    """
    self.schemas = discovery.get('schemas', {})

    # Cache of pretty printed schemas.
    self.pretty = {}

  @util.positional(2)
  def _prettyPrintByName(self, name, seen=None, dent=0):
    """Get pretty printed object prototype from the schema name.

    Args:
      name: string, Name of schema in the discovery document.
      seen: list of string, Names of schema already seen. Used to handle
        recursive definitions.

    Returns:
      string, A string that contains a prototype object with
        comments that conforms to the given schema.
    """
    if seen is None:
      seen = []

    if name in seen:
      # Do not fall into an infinite loop over recursive definitions.
      return '# Object with schema name: %s' % name
    seen.append(name)

    if name not in self.pretty:
      self.pretty[name] = _SchemaToStruct(self.schemas[name],
          seen, dent=dent).to_str(self._prettyPrintByName)

    seen.pop()

    return self.pretty[name]

  def prettyPrintByName(self, name):
    """Get pretty printed object prototype from the schema name.

    Args:
      name: string, Name of schema in the discovery document.

    Returns:
      string, A string that contains a prototype object with
        comments that conforms to the given schema.
    """
    # Return with trailing comma and newline removed.
    return self._prettyPrintByName(name, seen=[], dent=1)[:-2]

  @util.positional(2)
  def _prettyPrintSchema(self, schema, seen=None, dent=0):
    """Get pretty printed object prototype of schema.

    Args:
      schema: object, Parsed JSON schema.
      seen: list of string, Names of schema already seen. Used to handle
        recursive definitions.

    Returns:
      string, A string that contains a prototype object with
        comments that conforms to the given schema.
    """
    if seen is None:
      seen = []

    return _SchemaToStruct(schema, seen, dent=dent).to_str(self._prettyPrintByName)

  def prettyPrintSchema(self, schema):
    """Get pretty printed object prototype of schema.

    Args:
      schema: object, Parsed JSON schema.

    Returns:
      string, A string that contains a prototype object with
        comments that conforms to the given schema.
    """
    # Return with trailing comma and newline removed.
    return self._prettyPrintSchema(schema, dent=1)[:-2]

  def get(self, name):
    """Get deserialized JSON schema from the schema name.

    Args:
      name: string, Schema name.
    """
    return self.schemas[name]


class _SchemaToStruct(object):
  """Convert schema to a prototype object."""

  @util.positional(3)
  def __init__(self, schema, seen, dent=0):
    """Constructor.

    Args:
      schema: object, Parsed JSON schema.
      seen: list, List of names of schema already seen while parsing. Used to
        handle recursive definitions.
      dent: int, Initial indentation depth.
    """
    # The result of this parsing kept as list of strings.
    self.value = []

    # The final value of the parsing.
    self.string = None

    # The parsed JSON schema.
    self.schema = schema

    # Indentation level.
    self.dent = dent

    # Method that when called returns a prototype object for the schema with
    # the given name.
    self.from_cache = None

    # List of names of schema already seen while parsing.
    self.seen = seen

  def emit(self, text):
    """Add text as a line to the output.

    Args:
      text: string, Text to output.
    """
    self.value.extend(["  " * self.dent, text, '\n'])

  def emitBegin(self, text):
    """Add text to the output, but with no line terminator.

    Args:
      text: string, Text to output.
      """
    self.value.extend(["  " * self.dent, text])

  def emitEnd(self, text, comment):
    """Add text and comment to the output with line terminator.

    Args:
      text: string, Text to output.
      comment: string, Python comment.
    """
    if comment:
      divider = '\n' + '  ' * (self.dent + 2) + '# '
      lines = comment.splitlines()
      lines = [x.rstrip() for x in lines]
      comment = divider.join(lines)
      self.value.extend([text, ' # ', comment, '\n'])
    else:
      self.value.extend([text, '\n'])

  def indent(self):
    """Increase indentation level."""
    self.dent += 1

  def undent(self):
    """Decrease indentation level."""
    self.dent -= 1

  def _to_str_impl(self, schema):
    """Prototype object based on the schema, in Python code with comments.

    Args:
      schema: object, Parsed JSON schema file.

    Returns:
      Prototype object based on the schema, in Python code with comments.
    """
    stype = schema.get('type')
    if stype == 'object':
      self.emitEnd('{', schema.get('description', ''))
      self.indent()
      if 'properties' in schema:
        for pname, pschema in schema.get('properties', {}).iteritems():
          self.emitBegin('"%s": ' % pname)
          self._to_str_impl(pschema)
      elif 'additionalProperties' in schema:
        self.emitBegin('"a_key": ')
        self._to_str_impl(schema['additionalProperties'])
      self.undent()
      self.emit('},')
    elif '$ref' in schema:
      schemaName = schema['$ref']
      description = schema.get('description', '')
      s = self.from_cache(schemaName, seen=self.seen)
      parts = s.splitlines()
      self.emitEnd(parts[0], description)
      for line in parts[1:]:
        self.emit(line.rstrip())
    elif stype == 'boolean':
      value = schema.get('default', 'True or False')
      self.emitEnd('%s,' % str(value), schema.get('description', ''))
    elif stype == 'string':
      value = schema.get('default', 'A String')
      self.emitEnd('"%s",' % str(value), schema.get('description', ''))
    elif stype == 'integer':
      value = schema.get('default', '42')
      self.emitEnd('%s,' % str(value), schema.get('description', ''))
    elif stype == 'number':
      value = schema.get('default', '3.14')
      self.emitEnd('%s,' % str(value), schema.get('description', ''))
    elif stype == 'null':
      self.emitEnd('None,', schema.get('description', ''))
    elif stype == 'any':
      self.emitEnd('"",', schema.get('description', ''))
    elif stype == 'array':
      self.emitEnd('[', schema.get('description'))
      self.indent()
      self.emitBegin('')
      self._to_str_impl(schema['items'])
      self.undent()
      self.emit('],')
    else:
      self.emit('Unknown type! %s' % stype)
      self.emitEnd('', '')

    self.string = ''.join(self.value)
    return self.string

  def to_str(self, from_cache):
    """Prototype object based on the schema, in Python code with comments.

    Args:
      from_cache: callable(name, seen), Callable that retrieves an object
         prototype for a schema with the given name. Seen is a list of schema
         names already seen as we recursively descend the schema definition.

    Returns:
      Prototype object based on the schema, in Python code with comments.
      The lines of the code will all be properly indented.
    """
    self.from_cache = from_cache
    return self._to_str_impl(self.schema)

########NEW FILE########
__FILENAME__ = api_utils
# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

"""Util functions and classes for cloudstorage_api."""



__all__ = ['set_default_retry_params',
           'RetryParams',
          ]

import copy
import httplib
import logging
import math
import os
import threading
import time
import urllib


try:
  from google.appengine.api import app_identity
  from google.appengine.api import urlfetch
  from google.appengine.datastore import datastore_rpc
  from google.appengine.ext import ndb
  from google.appengine.ext.ndb import eventloop
  from google.appengine.ext.ndb import tasklets
  from google.appengine.ext.ndb import utils
  from google.appengine import runtime
  from google.appengine.runtime import apiproxy_errors
except ImportError:
  from google.appengine.api import app_identity
  from google.appengine.api import urlfetch
  from google.appengine.datastore import datastore_rpc
  from google.appengine import runtime
  from google.appengine.runtime import apiproxy_errors
  from google.appengine.ext import ndb
  from google.appengine.ext.ndb import eventloop
  from google.appengine.ext.ndb import tasklets
  from google.appengine.ext.ndb import utils


_RETRIABLE_EXCEPTIONS = (urlfetch.DownloadError,
                         apiproxy_errors.Error,
                         app_identity.InternalError,
                         app_identity.BackendDeadlineExceeded)

_thread_local_settings = threading.local()
_thread_local_settings.default_retry_params = None


def set_default_retry_params(retry_params):
  """Set a default RetryParams for current thread current request."""
  _thread_local_settings.default_retry_params = copy.copy(retry_params)


def _get_default_retry_params():
  """Get default RetryParams for current request and current thread.

  Returns:
    A new instance of the default RetryParams.
  """
  default = getattr(_thread_local_settings, 'default_retry_params', None)
  if default is None or not default.belong_to_current_request():
    return RetryParams()
  else:
    return copy.copy(default)


def _quote_filename(filename):
  """Quotes filename to use as a valid URI path.

  Args:
    filename: user provided filename. /bucket/filename.

  Returns:
    The filename properly quoted to use as URI's path component.
  """
  return urllib.quote(filename)


def _unquote_filename(filename):
  """Unquotes a valid URI path back to its filename.

  This is the opposite of _quote_filename.

  Args:
    filename: a quoted filename. /bucket/some%20filename.

  Returns:
    The filename unquoted.
  """
  return urllib.unquote(filename)


def _should_retry(resp):
  """Given a urlfetch response, decide whether to retry that request."""
  return (resp.status_code == httplib.REQUEST_TIMEOUT or
          (resp.status_code >= 500 and
           resp.status_code < 600))


class _RetryWrapper(object):
  """A wrapper that wraps retry logic around any tasklet."""

  def __init__(self,
               retry_params,
               retriable_exceptions=_RETRIABLE_EXCEPTIONS,
               should_retry=lambda r: False):
    """Init.

    Args:
      retry_params: an RetryParams instance.
      retriable_exceptions: a list of exception classes that are retriable.
      should_retry: a function that takes a result from the tasklet and returns
        a boolean. True if the result should be retried.
    """
    self.retry_params = retry_params
    self.retriable_exceptions = retriable_exceptions
    self.should_retry = should_retry

  @ndb.tasklet
  def run(self, tasklet, **kwds):
    """Run a tasklet with retry.

    The retry should be transparent to the caller: if no results
    are successful, the exception or result from the last retry is returned
    to the caller.

    Args:
      tasklet: the tasklet to run.
      **kwds: keywords arguments to run the tasklet.

    Raises:
      The exception from running the tasklet.

    Returns:
      The result from running the tasklet.
    """
    start_time = time.time()
    n = 1

    while True:
      e = None
      result = None
      got_result = False

      try:
        result = yield tasklet(**kwds)
        got_result = True
        if not self.should_retry(result):
          raise ndb.Return(result)
      except runtime.DeadlineExceededError:
        logging.debug(
            'Tasklet has exceeded request deadline after %s seconds total',
            time.time() - start_time)
        raise
      except self.retriable_exceptions as e:
        pass

      if n == 1:
        logging.debug('Tasklet is %r', tasklet)

      delay = self.retry_params.delay(n, start_time)

      if delay <= 0:
        logging.debug(
            'Tasklet failed after %s attempts and %s seconds in total',
            n, time.time() - start_time)
        if got_result:
          raise ndb.Return(result)
        elif e is not None:
          raise e
        else:
          assert False, 'Should never reach here.'

      if got_result:
        logging.debug(
            'Got result %r from tasklet.', result)
      else:
        logging.debug(
            'Got exception "%r" from tasklet.', e)
      logging.debug('Retry in %s seconds.', delay)
      n += 1
      yield tasklets.sleep(delay)


class RetryParams(object):
  """Retry configuration parameters."""

  _DEFAULT_USER_AGENT = 'App Engine Python GCS Client'

  @datastore_rpc._positional(1)
  def __init__(self,
               backoff_factor=2.0,
               initial_delay=0.1,
               max_delay=10.0,
               min_retries=3,
               max_retries=6,
               max_retry_period=30.0,
               urlfetch_timeout=None,
               save_access_token=False,
               _user_agent=None):
    """Init.

    This object is unique per request per thread.

    Library will retry according to this setting when App Engine Server
    can't call urlfetch, urlfetch timed out, or urlfetch got a 408 or
    500-600 response.

    Args:
      backoff_factor: exponential backoff multiplier.
      initial_delay: seconds to delay for the first retry.
      max_delay: max seconds to delay for every retry.
      min_retries: min number of times to retry. This value is automatically
        capped by max_retries.
      max_retries: max number of times to retry. Set this to 0 for no retry.
      max_retry_period: max total seconds spent on retry. Retry stops when
        this period passed AND min_retries has been attempted.
      urlfetch_timeout: timeout for urlfetch in seconds. Could be None,
        in which case the value will be chosen by urlfetch module.
      save_access_token: persist access token to datastore to avoid
        excessive usage of GetAccessToken API. Usually the token is cached
        in process and in memcache. In some cases, memcache isn't very
        reliable.
      _user_agent: The user agent string that you want to use in your requests.
    """
    self.backoff_factor = self._check('backoff_factor', backoff_factor)
    self.initial_delay = self._check('initial_delay', initial_delay)
    self.max_delay = self._check('max_delay', max_delay)
    self.max_retry_period = self._check('max_retry_period', max_retry_period)
    self.max_retries = self._check('max_retries', max_retries, True, int)
    self.min_retries = self._check('min_retries', min_retries, True, int)
    if self.min_retries > self.max_retries:
      self.min_retries = self.max_retries

    self.urlfetch_timeout = None
    if urlfetch_timeout is not None:
      self.urlfetch_timeout = self._check('urlfetch_timeout', urlfetch_timeout)
    self.save_access_token = self._check('save_access_token', save_access_token,
                                         True, bool)
    self._user_agent = _user_agent or self._DEFAULT_USER_AGENT

    self._request_id = os.getenv('REQUEST_LOG_ID')

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return False
    return self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not self.__eq__(other)

  @classmethod
  def _check(cls, name, val, can_be_zero=False, val_type=float):
    """Check init arguments.

    Args:
      name: name of the argument. For logging purpose.
      val: value. Value has to be non negative number.
      can_be_zero: whether value can be zero.
      val_type: Python type of the value.

    Returns:
      The value.

    Raises:
      ValueError: when invalid value is passed in.
      TypeError: when invalid value type is passed in.
    """
    valid_types = [val_type]
    if val_type is float:
      valid_types.append(int)

    if type(val) not in valid_types:
      raise TypeError(
          'Expect type %s for parameter %s' % (val_type.__name__, name))
    if val < 0:
      raise ValueError(
          'Value for parameter %s has to be greater than 0' % name)
    if not can_be_zero and val == 0:
      raise ValueError(
          'Value for parameter %s can not be 0' % name)
    return val

  def belong_to_current_request(self):
    return os.getenv('REQUEST_LOG_ID') == self._request_id

  def delay(self, n, start_time):
    """Calculate delay before the next retry.

    Args:
      n: the number of current attempt. The first attempt should be 1.
      start_time: the time when retry started in unix time.

    Returns:
      Number of seconds to wait before next retry. -1 if retry should give up.
    """
    if (n > self.max_retries or
        (n > self.min_retries and
         time.time() - start_time > self.max_retry_period)):
      return -1
    return min(
        math.pow(self.backoff_factor, n-1) * self.initial_delay,
        self.max_delay)


def _run_until_rpc():
  """Eagerly evaluate tasklets until it is blocking on some RPC.

  Usually ndb eventloop el isn't run until some code calls future.get_result().

  When an async tasklet is called, the tasklet wrapper evaluates the tasklet
  code into a generator, enqueues a callback _help_tasklet_along onto
  the el.current queue, and returns a future.

  _help_tasklet_along, when called by the el, will
  get one yielded value from the generator. If the value if another future,
  set up a callback _on_future_complete to invoke _help_tasklet_along
  when the dependent future fulfills. If the value if a RPC, set up a
  callback _on_rpc_complete to invoke _help_tasklet_along when the RPC fulfills.
  Thus _help_tasklet_along drills down
  the chain of futures until some future is blocked by RPC. El runs
  all callbacks and constantly check pending RPC status.
  """
  el = eventloop.get_event_loop()
  while el.current:
    el.run0()


def _eager_tasklet(tasklet):
  """Decorator to turn tasklet to run eagerly."""

  @utils.wrapping(tasklet)
  def eager_wrapper(*args, **kwds):
    fut = tasklet(*args, **kwds)
    _run_until_rpc()
    return fut

  return eager_wrapper

########NEW FILE########
__FILENAME__ = cloudstorage_api
# Copyright 2012 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

"""File Interface for Google Cloud Storage."""



from __future__ import with_statement



__all__ = ['delete',
           'listbucket',
           'open',
           'stat',
          ]

import logging
import StringIO
import urllib
import xml.etree.cElementTree as ET
from . import api_utils
from . import common
from . import errors
from . import storage_api



def open(filename,
         mode='r',
         content_type=None,
         options=None,
         read_buffer_size=storage_api.ReadBuffer.DEFAULT_BUFFER_SIZE,
         retry_params=None,
         _account_id=None):
  """Opens a Google Cloud Storage file and returns it as a File-like object.

  Args:
    filename: A Google Cloud Storage filename of form '/bucket/filename'.
    mode: 'r' for reading mode. 'w' for writing mode.
      In reading mode, the file must exist. In writing mode, a file will
      be created or be overrode.
    content_type: The MIME type of the file. str. Only valid in writing mode.
    options: A str->basestring dict to specify additional headers to pass to
      GCS e.g. {'x-goog-acl': 'private', 'x-goog-meta-foo': 'foo'}.
      Supported options are x-goog-acl, x-goog-meta-, cache-control,
      content-disposition, and content-encoding.
      Only valid in writing mode.
      See https://developers.google.com/storage/docs/reference-headers
      for details.
    read_buffer_size: The buffer size for read. Read keeps a buffer
      and prefetches another one. To minimize blocking for large files,
      always read by buffer size. To minimize number of RPC requests for
      small files, set a large buffer size. Max is 30MB.
    retry_params: An instance of api_utils.RetryParams for subsequent calls
      to GCS from this file handle. If None, the default one is used.
    _account_id: Internal-use only.

  Returns:
    A reading or writing buffer that supports File-like interface. Buffer
    must be closed after operations are done.

  Raises:
    errors.AuthorizationError: if authorization failed.
    errors.NotFoundError: if an object that's expected to exist doesn't.
    ValueError: invalid open mode or if content_type or options are specified
      in reading mode.
  """
  common.validate_file_path(filename)
  api = storage_api._get_storage_api(retry_params=retry_params,
                                     account_id=_account_id)
  filename = api_utils._quote_filename(filename)

  if mode == 'w':
    common.validate_options(options)
    return storage_api.StreamingBuffer(api, filename, content_type, options)
  elif mode == 'r':
    if content_type or options:
      raise ValueError('Options and content_type can only be specified '
                       'for writing mode.')
    return storage_api.ReadBuffer(api,
                                  filename,
                                  buffer_size=read_buffer_size)
  else:
    raise ValueError('Invalid mode %s.' % mode)


def delete(filename, retry_params=None, _account_id=None):
  """Delete a Google Cloud Storage file.

  Args:
    filename: A Google Cloud Storage filename of form '/bucket/filename'.
    retry_params: An api_utils.RetryParams for this call to GCS. If None,
      the default one is used.
    _account_id: Internal-use only.

  Raises:
    errors.NotFoundError: if the file doesn't exist prior to deletion.
  """
  api = storage_api._get_storage_api(retry_params=retry_params,
                                     account_id=_account_id)
  common.validate_file_path(filename)
  filename = api_utils._quote_filename(filename)
  status, resp_headers, content = api.delete_object(filename)
  errors.check_status(status, [204], filename, resp_headers=resp_headers,
                      body=content)


def stat(filename, retry_params=None, _account_id=None):
  """Get GCSFileStat of a Google Cloud storage file.

  Args:
    filename: A Google Cloud Storage filename of form '/bucket/filename'.
    retry_params: An api_utils.RetryParams for this call to GCS. If None,
      the default one is used.
    _account_id: Internal-use only.

  Returns:
    a GCSFileStat object containing info about this file.

  Raises:
    errors.AuthorizationError: if authorization failed.
    errors.NotFoundError: if an object that's expected to exist doesn't.
  """
  common.validate_file_path(filename)
  api = storage_api._get_storage_api(retry_params=retry_params,
                                     account_id=_account_id)
  status, headers, content = api.head_object(
      api_utils._quote_filename(filename))
  errors.check_status(status, [200], filename, resp_headers=headers,
                      body=content)
  file_stat = common.GCSFileStat(
      filename=filename,
      st_size=headers.get('content-length'),
      st_ctime=common.http_time_to_posix(headers.get('last-modified')),
      etag=headers.get('etag'),
      content_type=headers.get('content-type'),
      metadata=common.get_metadata(headers))

  return file_stat


def _copy2(src, dst, metadata=None, retry_params=None):
  """Copy the file content from src to dst.

  Internal use only!

  Args:
    src: /bucket/filename
    dst: /bucket/filename
    metadata: a dict of metadata for this copy. If None, old metadata is copied.
      For example, {'x-goog-meta-foo': 'bar'}.
    retry_params: An api_utils.RetryParams for this call to GCS. If None,
      the default one is used.

  Raises:
    errors.AuthorizationError: if authorization failed.
    errors.NotFoundError: if an object that's expected to exist doesn't.
  """
  common.validate_file_path(src)
  common.validate_file_path(dst)

  if metadata is None:
    metadata = {}
    copy_meta = 'COPY'
  else:
    copy_meta = 'REPLACE'
  metadata.update({'x-goog-copy-source': src,
                   'x-goog-metadata-directive': copy_meta})

  api = storage_api._get_storage_api(retry_params=retry_params)
  status, resp_headers, content = api.put_object(
      api_utils._quote_filename(dst), headers=metadata)
  errors.check_status(status, [200], src, metadata, resp_headers, body=content)


def listbucket(path_prefix, marker=None, prefix=None, max_keys=None,
               delimiter=None, retry_params=None, _account_id=None):
  """Returns a GCSFileStat iterator over a bucket.

  Optional arguments can limit the result to a subset of files under bucket.

  This function has two modes:
  1. List bucket mode: Lists all files in the bucket without any concept of
     hierarchy. GCS doesn't have real directory hierarchies.
  2. Directory emulation mode: If you specify the 'delimiter' argument,
     it is used as a path separator to emulate a hierarchy of directories.
     In this mode, the "path_prefix" argument should end in the delimiter
     specified (thus designates a logical directory). The logical directory's
     contents, both files and subdirectories, are listed. The names of
     subdirectories returned will end with the delimiter. So listbucket
     can be called with the subdirectory name to list the subdirectory's
     contents.

  Args:
    path_prefix: A Google Cloud Storage path of format "/bucket" or
      "/bucket/prefix". Only objects whose fullpath starts with the
      path_prefix will be returned.
    marker: Another path prefix. Only objects whose fullpath starts
      lexicographically after marker will be returned (exclusive).
    prefix: Deprecated. Use path_prefix.
    max_keys: The limit on the number of objects to return. int.
      For best performance, specify max_keys only if you know how many objects
      you want. Otherwise, this method requests large batches and handles
      pagination for you.
    delimiter: Use to turn on directory mode. str of one or multiple chars
      that your bucket uses as its directory separator.
    retry_params: An api_utils.RetryParams for this call to GCS. If None,
      the default one is used.
    _account_id: Internal-use only.

  Examples:
    For files "/bucket/a",
              "/bucket/bar/1"
              "/bucket/foo",
              "/bucket/foo/1", "/bucket/foo/2/1", "/bucket/foo/3/1",

    Regular mode:
    listbucket("/bucket/f", marker="/bucket/foo/1")
    will match "/bucket/foo/2/1", "/bucket/foo/3/1".

    Directory mode:
    listbucket("/bucket/", delimiter="/")
    will match "/bucket/a, "/bucket/bar/" "/bucket/foo", "/bucket/foo/".
    listbucket("/bucket/foo/", delimiter="/")
    will match "/bucket/foo/1", "/bucket/foo/2/", "/bucket/foo/3/"

  Returns:
    Regular mode:
    A GCSFileStat iterator over matched files ordered by filename.
    The iterator returns GCSFileStat objects. filename, etag, st_size,
    st_ctime, and is_dir are set.

    Directory emulation mode:
    A GCSFileStat iterator over matched files and directories ordered by
    name. The iterator returns GCSFileStat objects. For directories,
    only the filename and is_dir fields are set.

    The last name yielded can be used as next call's marker.
  """
  if prefix:
    common.validate_bucket_path(path_prefix)
    bucket = path_prefix
  else:
    bucket, prefix = common._process_path_prefix(path_prefix)

  if marker and marker.startswith(bucket):
    marker = marker[len(bucket) + 1:]

  api = storage_api._get_storage_api(retry_params=retry_params,
                                     account_id=_account_id)
  options = {}
  if marker:
    options['marker'] = marker
  if max_keys:
    options['max-keys'] = max_keys
  if prefix:
    options['prefix'] = prefix
  if delimiter:
    options['delimiter'] = delimiter

  return _Bucket(api, bucket, options)


class _Bucket(object):
  """A wrapper for a GCS bucket as the return value of listbucket."""

  def __init__(self, api, path, options):
    """Initialize.

    Args:
      api: storage_api instance.
      path: bucket path of form '/bucket'.
      options: a dict of listbucket options. Please see listbucket doc.
    """
    self._init(api, path, options)

  def _init(self, api, path, options):
    self._api = api
    self._path = path
    self._options = options.copy()
    self._get_bucket_fut = self._api.get_bucket_async(
        self._path + '?' + urllib.urlencode(self._options))
    self._last_yield = None
    self._new_max_keys = self._options.get('max-keys')

  def __getstate__(self):
    options = self._options
    if self._last_yield:
      options['marker'] = self._last_yield.filename[len(self._path) + 1:]
    if self._new_max_keys is not None:
      options['max-keys'] = self._new_max_keys
    return {'api': self._api,
            'path': self._path,
            'options': options}

  def __setstate__(self, state):
    self._init(state['api'], state['path'], state['options'])

  def __iter__(self):
    """Iter over the bucket.

    Yields:
      GCSFileStat: a GCSFileStat for an object in the bucket.
        They are ordered by GCSFileStat.filename.
    """
    total = 0
    max_keys = self._options.get('max-keys')

    while self._get_bucket_fut:
      status, resp_headers, content = self._get_bucket_fut.get_result()
      errors.check_status(status, [200], self._path, resp_headers=resp_headers,
                          body=content, extras=self._options)

      if self._should_get_another_batch(content):
        self._get_bucket_fut = self._api.get_bucket_async(
            self._path + '?' + urllib.urlencode(self._options))
      else:
        self._get_bucket_fut = None

      root = ET.fromstring(content)
      dirs = self._next_dir_gen(root)
      files = self._next_file_gen(root)
      next_file = files.next()
      next_dir = dirs.next()

      while ((max_keys is None or total < max_keys) and
             not (next_file is None and next_dir is None)):
        total += 1
        if next_file is None:
          self._last_yield = next_dir
          next_dir = dirs.next()
        elif next_dir is None:
          self._last_yield = next_file
          next_file = files.next()
        elif next_dir < next_file:
          self._last_yield = next_dir
          next_dir = dirs.next()
        elif next_file < next_dir:
          self._last_yield = next_file
          next_file = files.next()
        else:
          logging.error(
              'Should never reach. next file is %r. next dir is %r.',
              next_file, next_dir)
        if self._new_max_keys:
          self._new_max_keys -= 1
        yield self._last_yield

  def _next_file_gen(self, root):
    """Generator for next file element in the document.

    Args:
      root: root element of the XML tree.

    Yields:
      GCSFileStat for the next file.
    """
    for e in root.getiterator(common._T_CONTENTS):
      st_ctime, size, etag, key = None, None, None, None
      for child in e.getiterator('*'):
        if child.tag == common._T_LAST_MODIFIED:
          st_ctime = common.dt_str_to_posix(child.text)
        elif child.tag == common._T_ETAG:
          etag = child.text
        elif child.tag == common._T_SIZE:
          size = child.text
        elif child.tag == common._T_KEY:
          key = child.text
      yield common.GCSFileStat(self._path + '/' + key,
                               size, etag, st_ctime)
      e.clear()
    yield None

  def _next_dir_gen(self, root):
    """Generator for next directory element in the document.

    Args:
      root: root element in the XML tree.

    Yields:
      GCSFileStat for the next directory.
    """
    for e in root.getiterator(common._T_COMMON_PREFIXES):
      yield common.GCSFileStat(
          self._path + '/' + e.find(common._T_PREFIX).text,
          st_size=None, etag=None, st_ctime=None, is_dir=True)
      e.clear()
    yield None

  def _should_get_another_batch(self, content):
    """Whether to issue another GET bucket call.

    Args:
      content: response XML.

    Returns:
      True if should, also update self._options for the next request.
      False otherwise.
    """
    if ('max-keys' in self._options and
        self._options['max-keys'] <= common._MAX_GET_BUCKET_RESULT):
      return False

    elements = self._find_elements(
        content, set([common._T_IS_TRUNCATED,
                      common._T_NEXT_MARKER]))
    if elements.get(common._T_IS_TRUNCATED, 'false').lower() != 'true':
      return False

    next_marker = elements.get(common._T_NEXT_MARKER)
    if next_marker is None:
      self._options.pop('marker', None)
      return False
    self._options['marker'] = next_marker
    return True

  def _find_elements(self, result, elements):
    """Find interesting elements from XML.

    This function tries to only look for specified elements
    without parsing the entire XML. The specified elements is better
    located near the beginning.

    Args:
      result: response XML.
      elements: a set of interesting element tags.

    Returns:
      A dict from element tag to element value.
    """
    element_mapping = {}
    result = StringIO.StringIO(result)
    for _, e in ET.iterparse(result, events=('end',)):
      if not elements:
        break
      if e.tag in elements:
        element_mapping[e.tag] = e.text
        elements.remove(e.tag)
    return element_mapping

########NEW FILE########
__FILENAME__ = common
# Copyright 2012 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

"""Helpers shared by cloudstorage_stub and cloudstorage_api."""





__all__ = ['CS_XML_NS',
           'CSFileStat',
           'dt_str_to_posix',
           'local_api_url',
           'LOCAL_GCS_ENDPOINT',
           'local_run',
           'get_access_token',
           'get_metadata',
           'GCSFileStat',
           'http_time_to_posix',
           'memory_usage',
           'posix_time_to_http',
           'posix_to_dt_str',
           'set_access_token',
           'validate_options',
           'validate_bucket_name',
           'validate_bucket_path',
           'validate_file_path',
          ]


import calendar
import datetime
from email import utils as email_utils
import logging
import os
import re

try:
  from google.appengine.api import runtime
except ImportError:
  from google.appengine.api import runtime


_GCS_BUCKET_REGEX_BASE = r'[a-z0-9\.\-_]{3,63}'
_GCS_BUCKET_REGEX = re.compile(_GCS_BUCKET_REGEX_BASE + r'$')
_GCS_BUCKET_PATH_REGEX = re.compile(r'/' + _GCS_BUCKET_REGEX_BASE + r'$')
_GCS_PATH_PREFIX_REGEX = re.compile(r'/' + _GCS_BUCKET_REGEX_BASE + r'.*')
_GCS_FULLPATH_REGEX = re.compile(r'/' + _GCS_BUCKET_REGEX_BASE + r'/.*')
_GCS_METADATA = ['x-goog-meta-',
                 'content-disposition',
                 'cache-control',
                 'content-encoding']
_GCS_OPTIONS = _GCS_METADATA + ['x-goog-acl']
CS_XML_NS = 'http://doc.s3.amazonaws.com/2006-03-01'
LOCAL_GCS_ENDPOINT = '/_ah/gcs'
_access_token = ''


_MAX_GET_BUCKET_RESULT = 1000


def set_access_token(access_token):
  """Set the shared access token to authenticate with Google Cloud Storage.

  When set, the library will always attempt to communicate with the
  real Google Cloud Storage with this token even when running on dev appserver.
  Note the token could expire so it's up to you to renew it.

  When absent, the library will automatically request and refresh a token
  on appserver, or when on dev appserver, talk to a Google Cloud Storage
  stub.

  Args:
    access_token: you can get one by run 'gsutil -d ls' and copy the
      str after 'Bearer'.
  """
  global _access_token
  _access_token = access_token


def get_access_token():
  """Returns the shared access token."""
  return _access_token


class GCSFileStat(object):
  """Container for GCS file stat."""

  def __init__(self,
               filename,
               st_size,
               etag,
               st_ctime,
               content_type=None,
               metadata=None,
               is_dir=False):
    """Initialize.

    For files, the non optional arguments are always set.
    For directories, only filename and is_dir is set.

    Args:
      filename: a Google Cloud Storage filename of form '/bucket/filename'.
      st_size: file size in bytes. long compatible.
      etag: hex digest of the md5 hash of the file's content. str.
      st_ctime: posix file creation time. float compatible.
      content_type: content type. str.
      metadata: a str->str dict of user specified options when creating
        the file. Possible keys are x-goog-meta-, content-disposition,
        content-encoding, and cache-control.
      is_dir: True if this represents a directory. False if this is a real file.
    """
    self.filename = filename
    self.is_dir = is_dir
    self.st_size = None
    self.st_ctime = None
    self.etag = None
    self.content_type = content_type
    self.metadata = metadata

    if not is_dir:
      self.st_size = long(st_size)
      self.st_ctime = float(st_ctime)
      if etag[0] == '"' and etag[-1] == '"':
        etag = etag[1:-1]
      self.etag = etag

  def __repr__(self):
    if self.is_dir:
      return '(directory: %s)' % self.filename

    return (
        '(filename: %(filename)s, st_size: %(st_size)s, '
        'st_ctime: %(st_ctime)s, etag: %(etag)s, '
        'content_type: %(content_type)s, '
        'metadata: %(metadata)s)' %
        dict(filename=self.filename,
             st_size=self.st_size,
             st_ctime=self.st_ctime,
             etag=self.etag,
             content_type=self.content_type,
             metadata=self.metadata))

  def __cmp__(self, other):
    if not isinstance(other, self.__class__):
      raise ValueError('Argument to cmp must have the same type. '
                       'Expect %s, got %s', self.__class__.__name__,
                       other.__class__.__name__)
    if self.filename > other.filename:
      return 1
    elif self.filename < other.filename:
      return -1
    return 0

  def __hash__(self):
    if self.etag:
      return hash(self.etag)
    return hash(self.filename)


CSFileStat = GCSFileStat


def get_metadata(headers):
  """Get user defined options from HTTP response headers."""
  return dict((k, v) for k, v in headers.iteritems()
              if any(k.lower().startswith(valid) for valid in _GCS_METADATA))


def validate_bucket_name(name):
  """Validate a Google Storage bucket name.

  Args:
    name: a Google Storage bucket name with no prefix or suffix.

  Raises:
    ValueError: if name is invalid.
  """
  _validate_path(name)
  if not _GCS_BUCKET_REGEX.match(name):
    raise ValueError('Bucket should be 3-63 characters long using only a-z,'
                     '0-9, underscore, dash or dot but got %s' % name)


def validate_bucket_path(path):
  """Validate a Google Cloud Storage bucket path.

  Args:
    path: a Google Storage bucket path. It should have form '/bucket'.

  Raises:
    ValueError: if path is invalid.
  """
  _validate_path(path)
  if not _GCS_BUCKET_PATH_REGEX.match(path):
    raise ValueError('Bucket should have format /bucket '
                     'but got %s' % path)


def validate_file_path(path):
  """Validate a Google Cloud Storage file path.

  Args:
    path: a Google Storage file path. It should have form '/bucket/filename'.

  Raises:
    ValueError: if path is invalid.
  """
  _validate_path(path)
  if not _GCS_FULLPATH_REGEX.match(path):
    raise ValueError('Path should have format /bucket/filename '
                     'but got %s' % path)


def _process_path_prefix(path_prefix):
  """Validate and process a Google Cloud Stoarge path prefix.

  Args:
    path_prefix: a Google Cloud Storage path prefix of format '/bucket/prefix'
      or '/bucket/' or '/bucket'.

  Raises:
    ValueError: if path is invalid.

  Returns:
    a tuple of /bucket and prefix. prefix can be None.
  """
  _validate_path(path_prefix)
  if not _GCS_PATH_PREFIX_REGEX.match(path_prefix):
    raise ValueError('Path prefix should have format /bucket, /bucket/, '
                     'or /bucket/prefix but got %s.' % path_prefix)
  bucket_name_end = path_prefix.find('/', 1)
  bucket = path_prefix
  prefix = None
  if bucket_name_end != -1:
    bucket = path_prefix[:bucket_name_end]
    prefix = path_prefix[bucket_name_end + 1:] or None
  return bucket, prefix


def _validate_path(path):
  """Basic validation of Google Storage paths.

  Args:
    path: a Google Storage path. It should have form '/bucket/filename'
      or '/bucket'.

  Raises:
    ValueError: if path is invalid.
    TypeError: if path is not of type basestring.
  """
  if not path:
    raise ValueError('Path is empty')
  if not isinstance(path, basestring):
    raise TypeError('Path should be a string but is %s (%s).' %
                    (path.__class__, path))


def validate_options(options):
  """Validate Google Cloud Storage options.

  Args:
    options: a str->basestring dict of options to pass to Google Cloud Storage.

  Raises:
    ValueError: if option is not supported.
    TypeError: if option is not of type str or value of an option
      is not of type basestring.
  """
  if not options:
    return

  for k, v in options.iteritems():
    if not isinstance(k, str):
      raise TypeError('option %r should be a str.' % k)
    if not any(k.lower().startswith(valid) for valid in _GCS_OPTIONS):
      raise ValueError('option %s is not supported.' % k)
    if not isinstance(v, basestring):
      raise TypeError('value %r for option %s should be of type basestring.' %
                      (v, k))


def http_time_to_posix(http_time):
  """Convert HTTP time format to posix time.

  See http://www.w3.org/Protocols/rfc2616/rfc2616-sec3.html#sec3.3.1
  for http time format.

  Args:
    http_time: time in RFC 2616 format. e.g.
      "Mon, 20 Nov 1995 19:12:08 GMT".

  Returns:
    A float of secs from unix epoch.
  """
  if http_time is not None:
    return email_utils.mktime_tz(email_utils.parsedate_tz(http_time))


def posix_time_to_http(posix_time):
  """Convert posix time to HTML header time format.

  Args:
    posix_time: unix time.

  Returns:
    A datatime str in RFC 2616 format.
  """
  if posix_time:
    return email_utils.formatdate(posix_time, usegmt=True)


_DT_FORMAT = '%Y-%m-%dT%H:%M:%S'


def dt_str_to_posix(dt_str):
  """format str to posix.

  datetime str is of format %Y-%m-%dT%H:%M:%S.%fZ,
  e.g. 2013-04-12T00:22:27.978Z. According to ISO 8601, T is a separator
  between date and time when they are on the same line.
  Z indicates UTC (zero meridian).

  A pointer: http://www.cl.cam.ac.uk/~mgk25/iso-time.html

  This is used to parse LastModified node from GCS's GET bucket XML response.

  Args:
    dt_str: A datetime str.

  Returns:
    A float of secs from unix epoch. By posix definition, epoch is midnight
    1970/1/1 UTC.
  """
  parsable, _ = dt_str.split('.')
  dt = datetime.datetime.strptime(parsable, _DT_FORMAT)
  return calendar.timegm(dt.utctimetuple())


def posix_to_dt_str(posix):
  """Reverse of str_to_datetime.

  This is used by GCS stub to generate GET bucket XML response.

  Args:
    posix: A float of secs from unix epoch.

  Returns:
    A datetime str.
  """
  dt = datetime.datetime.utcfromtimestamp(posix)
  dt_str = dt.strftime(_DT_FORMAT)
  return dt_str + '.000Z'


def local_run():
  """Whether we should hit GCS dev appserver stub."""
  server_software = os.environ.get('SERVER_SOFTWARE')
  if server_software is None:
    return True
  if 'remote_api' in server_software:
    return False
  if server_software.startswith(('Development', 'testutil')):
    return True
  return False


def local_api_url():
  """Return URL for GCS emulation on dev appserver."""
  return 'http://%s%s' % (os.environ.get('HTTP_HOST'), LOCAL_GCS_ENDPOINT)


def memory_usage(method):
  """Log memory usage before and after a method."""
  def wrapper(*args, **kwargs):
    logging.info('Memory before method %s is %s.',
                 method.__name__, runtime.memory_usage().current())
    result = method(*args, **kwargs)
    logging.info('Memory after method %s is %s',
                 method.__name__, runtime.memory_usage().current())
    return result
  return wrapper


def _add_ns(tagname):
  return '{%(ns)s}%(tag)s' % {'ns': CS_XML_NS,
                              'tag': tagname}


_T_CONTENTS = _add_ns('Contents')
_T_LAST_MODIFIED = _add_ns('LastModified')
_T_ETAG = _add_ns('ETag')
_T_KEY = _add_ns('Key')
_T_SIZE = _add_ns('Size')
_T_PREFIX = _add_ns('Prefix')
_T_COMMON_PREFIXES = _add_ns('CommonPrefixes')
_T_NEXT_MARKER = _add_ns('NextMarker')
_T_IS_TRUNCATED = _add_ns('IsTruncated')

########NEW FILE########
__FILENAME__ = errors
# Copyright 2012 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

"""Google Cloud Storage specific Files API calls."""





__all__ = ['AuthorizationError',
           'check_status',
           'Error',
           'FatalError',
           'FileClosedError',
           'ForbiddenError',
           'InvalidRange',
           'NotFoundError',
           'ServerError',
           'TimeoutError',
           'TransientError',
          ]

import httplib


class Error(Exception):
  """Base error for all gcs operations.

  Error can happen on GAE side or GCS server side.
  For details on a particular GCS HTTP response code, see
  https://developers.google.com/storage/docs/reference-status#standardcodes
  """


class TransientError(Error):
  """TransientError could be retried."""


class TimeoutError(TransientError):
  """HTTP 408 timeout."""


class FatalError(Error):
  """FatalError shouldn't be retried."""


class FileClosedError(FatalError):
  """File is already closed.

  This can happen when the upload has finished but 'write' is called on
  a stale upload handle.
  """


class NotFoundError(FatalError):
  """HTTP 404 resource not found."""


class ForbiddenError(FatalError):
  """HTTP 403 Forbidden.

  While GCS replies with a 403 error for many reasons, the most common one
  is due to bucket permission not correctly setup for your app to access.
  """


class AuthorizationError(FatalError):
  """HTTP 401 authentication required.

  Unauthorized request has been received by GCS.

  This error is mostly handled by GCS client. GCS client will request
  a new access token and retry the request.
  """


class InvalidRange(FatalError):
  """HTTP 416 RequestRangeNotSatifiable."""


class ServerError(TransientError):
  """HTTP >= 500 server side error."""


def check_status(status, expected, path, headers=None,
                 resp_headers=None, body=None, extras=None):
  """Check HTTP response status is expected.

  Args:
    status: HTTP response status. int.
    expected: a list of expected statuses. A list of ints.
    path: filename or a path prefix.
    headers: HTTP request headers.
    resp_headers: HTTP response headers.
    body: HTTP response body.
    extras: extra info to be logged verbatim if error occurs.

  Raises:
    AuthorizationError: if authorization failed.
    NotFoundError: if an object that's expected to exist doesn't.
    TimeoutError: if HTTP request timed out.
    ServerError: if server experienced some errors.
    FatalError: if any other unexpected errors occurred.
  """
  if status in expected:
    return

  msg = ('Expect status %r from Google Storage. But got status %d.\n'
         'Path: %r.\n'
         'Request headers: %r.\n'
         'Response headers: %r.\n'
         'Body: %r.\n'
         'Extra info: %r.\n' %
         (expected, status, path, headers, resp_headers, body, extras))

  if status == httplib.UNAUTHORIZED:
    raise AuthorizationError(msg)
  elif status == httplib.FORBIDDEN:
    raise ForbiddenError(msg)
  elif status == httplib.NOT_FOUND:
    raise NotFoundError(msg)
  elif status == httplib.REQUEST_TIMEOUT:
    raise TimeoutError(msg)
  elif status == httplib.REQUESTED_RANGE_NOT_SATISFIABLE:
    raise InvalidRange(msg)
  elif (status == httplib.OK and 308 in expected and
        httplib.OK not in expected):
    raise FileClosedError(msg)
  elif status >= 500:
    raise ServerError(msg)
  else:
    raise FatalError(msg)

########NEW FILE########
__FILENAME__ = rest_api
# Copyright 2012 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

"""Base and helper classes for Google RESTful APIs."""





__all__ = ['add_sync_methods']

import random
import time

from . import api_utils

try:
  from google.appengine.api import app_identity
  from google.appengine.ext import ndb
except ImportError:
  from google.appengine.api import app_identity
  from google.appengine.ext import ndb



def _make_sync_method(name):
  """Helper to synthesize a synchronous method from an async method name.

  Used by the @add_sync_methods class decorator below.

  Args:
    name: The name of the synchronous method.

  Returns:
    A method (with first argument 'self') that retrieves and calls
    self.<name>, passing its own arguments, expects it to return a
    Future, and then waits for and returns that Future's result.
  """

  def sync_wrapper(self, *args, **kwds):
    method = getattr(self, name)
    future = method(*args, **kwds)
    return future.get_result()

  return sync_wrapper


def add_sync_methods(cls):
  """Class decorator to add synchronous methods corresponding to async methods.

  This modifies the class in place, adding additional methods to it.
  If a synchronous method of a given name already exists it is not
  replaced.

  Args:
    cls: A class.

  Returns:
    The same class, modified in place.
  """
  for name in cls.__dict__.keys():
    if name.endswith('_async'):
      sync_name = name[:-6]
      if not hasattr(cls, sync_name):
        setattr(cls, sync_name, _make_sync_method(name))
  return cls


class _AE_TokenStorage_(ndb.Model):
  """Entity to store app_identity tokens in memcache."""

  token = ndb.StringProperty()
  expires = ndb.FloatProperty()


@ndb.tasklet
def _make_token_async(scopes, service_account_id):
  """Get a fresh authentication token.

  Args:
    scopes: A list of scopes.
    service_account_id: Internal-use only.

  Raises:
    An ndb.Return with a tuple (token, expiration_time) where expiration_time is
    seconds since the epoch.
  """
  rpc = app_identity.create_rpc()
  app_identity.make_get_access_token_call(rpc, scopes, service_account_id)
  token, expires_at = yield rpc
  raise ndb.Return((token, expires_at))


class _RestApi(object):
  """Base class for REST-based API wrapper classes.

  This class manages authentication tokens and request retries.  All
  APIs are available as synchronous and async methods; synchronous
  methods are synthesized from async ones by the add_sync_methods()
  function in this module.

  WARNING: Do NOT directly use this api. It's an implementation detail
  and is subject to change at any release.
  """

  _TOKEN_EXPIRATION_HEADROOM = random.randint(60, 600)

  def __init__(self, scopes, service_account_id=None, token_maker=None,
               retry_params=None):
    """Constructor.

    Args:
      scopes: A scope or a list of scopes.
      service_account_id: Internal use only.
      token_maker: An asynchronous function of the form
        (scopes, service_account_id) -> (token, expires).
      retry_params: An instance of api_utils.RetryParams. If None, the
        default for current thread will be used.
    """

    if isinstance(scopes, basestring):
      scopes = [scopes]
    self.scopes = scopes
    self.service_account_id = service_account_id
    self.make_token_async = token_maker or _make_token_async
    if not retry_params:
      retry_params = api_utils._get_default_retry_params()
    self.retry_params = retry_params
    self.user_agent = {'User-Agent': retry_params._user_agent}

  def __getstate__(self):
    """Store state as part of serialization/pickling."""
    return {'scopes': self.scopes,
            'id': self.service_account_id,
            'a_maker': (None if self.make_token_async == _make_token_async
                        else self.make_token_async),
            'retry_params': self.retry_params}

  def __setstate__(self, state):
    """Restore state as part of deserialization/unpickling."""
    self.__init__(state['scopes'],
                  service_account_id=state['id'],
                  token_maker=state['a_maker'],
                  retry_params=state['retry_params'])

  @ndb.tasklet
  def do_request_async(self, url, method='GET', headers=None, payload=None,
                       deadline=None, callback=None):
    """Issue one HTTP request.

    It performs async retries using tasklets.

    Args:
      url: the url to fetch.
      method: the method in which to fetch.
      headers: the http headers.
      payload: the data to submit in the fetch.
      deadline: the deadline in which to make the call.
      callback: the call to make once completed.

    Yields:
      The async fetch of the url.
    """
    retry_wrapper = api_utils._RetryWrapper(
        self.retry_params,
        retriable_exceptions=api_utils._RETRIABLE_EXCEPTIONS,
        should_retry=api_utils._should_retry)
    resp = yield retry_wrapper.run(
        self.urlfetch_async,
        url=url,
        method=method,
        headers=headers,
        payload=payload,
        deadline=deadline,
        callback=callback,
        follow_redirects=False)
    raise ndb.Return((resp.status_code, resp.headers, resp.content))

  @ndb.tasklet
  def get_token_async(self, refresh=False):
    """Get an authentication token.

    The token is cached in memcache, keyed by the scopes argument.

    Args:
      refresh: If True, ignore a cached token; default False.

    Yields:
      An authentication token. This token is guaranteed to be non-expired.
    """
    key = '%s,%s' % (self.service_account_id, ','.join(self.scopes))
    ts = yield _AE_TokenStorage_.get_by_id_async(
        key, use_cache=True, use_memcache=True,
        use_datastore=self.retry_params.save_access_token)
    if refresh or ts is None or ts.expires < (
        time.time() + self._TOKEN_EXPIRATION_HEADROOM):
      token, expires_at = yield self.make_token_async(
          self.scopes, self.service_account_id)
      timeout = int(expires_at - time.time())
      ts = _AE_TokenStorage_(id=key, token=token, expires=expires_at)
      if timeout > 0:
        yield ts.put_async(memcache_timeout=timeout,
                           use_datastore=self.retry_params.save_access_token,
                           use_cache=True, use_memcache=True)
    raise ndb.Return(ts.token)

  @ndb.tasklet
  def urlfetch_async(self, url, method='GET', headers=None,
                     payload=None, deadline=None, callback=None,
                     follow_redirects=False):
    """Make an async urlfetch() call.

    This is an async wrapper around urlfetch(). It adds an authentication
    header.

    Args:
      url: the url to fetch.
      method: the method in which to fetch.
      headers: the http headers.
      payload: the data to submit in the fetch.
      deadline: the deadline in which to make the call.
      callback: the call to make once completed.
      follow_redirects: whether or not to follow redirects.

    Yields:
      This returns a Future despite not being decorated with @ndb.tasklet!
    """
    headers = {} if headers is None else dict(headers)
    headers.update(self.user_agent)
    self.token = yield self.get_token_async()
    headers['authorization'] = 'OAuth ' + self.token

    deadline = deadline or self.retry_params.urlfetch_timeout

    ctx = ndb.get_context()
    resp = yield ctx.urlfetch(
        url, payload=payload, method=method,
        headers=headers, follow_redirects=follow_redirects,
        deadline=deadline, callback=callback)
    raise ndb.Return(resp)


_RestApi = add_sync_methods(_RestApi)

########NEW FILE########
__FILENAME__ = storage_api
# Copyright 2012 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

"""Python wrappers for the Google Storage RESTful API."""





__all__ = ['ReadBuffer',
           'StreamingBuffer',
          ]

import collections
import os
import urlparse

from . import api_utils
from . import common
from . import errors
from . import rest_api

try:
  from google.appengine.api import urlfetch
  from google.appengine.ext import ndb
except ImportError:
  from google.appengine.api import urlfetch
  from google.appengine.ext import ndb



def _get_storage_api(retry_params, account_id=None):
  """Returns storage_api instance for API methods.

  Args:
    retry_params: An instance of api_utils.RetryParams. If none,
     thread's default will be used.
    account_id: Internal-use only.

  Returns:
    A storage_api instance to handle urlfetch work to GCS.
    On dev appserver, this instance by default will talk to a local stub
    unless common.ACCESS_TOKEN is set. That token will be used to talk
    to the real GCS.
  """


  api = _StorageApi(_StorageApi.full_control_scope,
                    service_account_id=account_id,
                    retry_params=retry_params)
  if common.local_run() and not common.get_access_token():
    api.api_url = common.local_api_url()
  if common.get_access_token():
    api.token = common.get_access_token()
  return api


class _StorageApi(rest_api._RestApi):
  """A simple wrapper for the Google Storage RESTful API.

  WARNING: Do NOT directly use this api. It's an implementation detail
  and is subject to change at any release.

  All async methods have similar args and returns.

  Args:
    path: The path to the Google Storage object or bucket, e.g.
      '/mybucket/myfile' or '/mybucket'.
    **kwd: Options for urlfetch. e.g.
      headers={'content-type': 'text/plain'}, payload='blah'.

  Returns:
    A ndb Future. When fulfilled, future.get_result() should return
    a tuple of (status, headers, content) that represents a HTTP response
    of Google Cloud Storage XML API.
  """

  api_url = 'https://storage.googleapis.com'
  read_only_scope = 'https://www.googleapis.com/auth/devstorage.read_only'
  read_write_scope = 'https://www.googleapis.com/auth/devstorage.read_write'
  full_control_scope = 'https://www.googleapis.com/auth/devstorage.full_control'

  def __getstate__(self):
    """Store state as part of serialization/pickling.

    Returns:
      A tuple (of dictionaries) with the state of this object
    """
    return (super(_StorageApi, self).__getstate__(), {'api_url': self.api_url})

  def __setstate__(self, state):
    """Restore state as part of deserialization/unpickling.

    Args:
      state: the tuple from a __getstate__ call
    """
    superstate, localstate = state
    super(_StorageApi, self).__setstate__(superstate)
    self.api_url = localstate['api_url']

  @api_utils._eager_tasklet
  @ndb.tasklet
  def do_request_async(self, url, method='GET', headers=None, payload=None,
                       deadline=None, callback=None):
    """Inherit docs.

    This method translates urlfetch exceptions to more service specific ones.
    """
    if headers is None:
      headers = {}
    if 'x-goog-api-version' not in headers:
      headers['x-goog-api-version'] = '2'
    headers['accept-encoding'] = 'gzip, *'
    try:
      resp_tuple = yield super(_StorageApi, self).do_request_async(
          url, method=method, headers=headers, payload=payload,
          deadline=deadline, callback=callback)
    except urlfetch.DownloadError, e:
      raise errors.TimeoutError(
          'Request to Google Cloud Storage timed out.', e)

    raise ndb.Return(resp_tuple)


  def post_object_async(self, path, **kwds):
    """POST to an object."""
    return self.do_request_async(self.api_url + path, 'POST', **kwds)

  def put_object_async(self, path, **kwds):
    """PUT an object."""
    return self.do_request_async(self.api_url + path, 'PUT', **kwds)

  def get_object_async(self, path, **kwds):
    """GET an object.

    Note: No payload argument is supported.
    """
    return self.do_request_async(self.api_url + path, 'GET', **kwds)

  def delete_object_async(self, path, **kwds):
    """DELETE an object.

    Note: No payload argument is supported.
    """
    return self.do_request_async(self.api_url + path, 'DELETE', **kwds)

  def head_object_async(self, path, **kwds):
    """HEAD an object.

    Depending on request headers, HEAD returns various object properties,
    e.g. Content-Length, Last-Modified, and ETag.

    Note: No payload argument is supported.
    """
    return self.do_request_async(self.api_url + path, 'HEAD', **kwds)

  def get_bucket_async(self, path, **kwds):
    """GET a bucket."""
    return self.do_request_async(self.api_url + path, 'GET', **kwds)


_StorageApi = rest_api.add_sync_methods(_StorageApi)


class ReadBuffer(object):
  """A class for reading Google storage files."""

  DEFAULT_BUFFER_SIZE = 1024 * 1024
  MAX_REQUEST_SIZE = 30 * DEFAULT_BUFFER_SIZE

  def __init__(self,
               api,
               path,
               buffer_size=DEFAULT_BUFFER_SIZE,
               max_request_size=MAX_REQUEST_SIZE):
    """Constructor.

    Args:
      api: A StorageApi instance.
      path: Quoted/escaped path to the object, e.g. /mybucket/myfile
      buffer_size: buffer size. The ReadBuffer keeps
        one buffer. But there may be a pending future that contains
        a second buffer. This size must be less than max_request_size.
      max_request_size: Max bytes to request in one urlfetch.
    """
    self._api = api
    self._path = path
    self.name = api_utils._unquote_filename(path)
    self.closed = False

    assert buffer_size <= max_request_size
    self._buffer_size = buffer_size
    self._max_request_size = max_request_size
    self._offset = 0
    self._buffer = _Buffer()
    self._etag = None

    self._request_next_buffer()

    status, headers, content = self._api.head_object(path)
    errors.check_status(status, [200], path, resp_headers=headers, body=content)
    self._file_size = long(headers['content-length'])
    self._check_etag(headers.get('etag'))
    if self._file_size == 0:
      self._buffer_future = None

  def __getstate__(self):
    """Store state as part of serialization/pickling.

    The contents of the read buffer are not stored, only the current offset for
    data read by the client. A new read buffer is established at unpickling.
    The head information for the object (file size and etag) are stored to
    reduce startup and ensure the file has not changed.

    Returns:
      A dictionary with the state of this object
    """
    return {'api': self._api,
            'path': self._path,
            'buffer_size': self._buffer_size,
            'request_size': self._max_request_size,
            'etag': self._etag,
            'size': self._file_size,
            'offset': self._offset,
            'closed': self.closed}

  def __setstate__(self, state):
    """Restore state as part of deserialization/unpickling.

    Args:
      state: the dictionary from a __getstate__ call

    Along with restoring the state, pre-fetch the next read buffer.
    """
    self._api = state['api']
    self._path = state['path']
    self.name = api_utils._unquote_filename(self._path)
    self._buffer_size = state['buffer_size']
    self._max_request_size = state['request_size']
    self._etag = state['etag']
    self._file_size = state['size']
    self._offset = state['offset']
    self._buffer = _Buffer()
    self.closed = state['closed']
    self._buffer_future = None
    if self._remaining() and not self.closed:
      self._request_next_buffer()

  def __iter__(self):
    """Iterator interface.

    Note the ReadBuffer container itself is the iterator. It's
    (quote PEP0234)
    'destructive: they consumes all the values and a second iterator
    cannot easily be created that iterates independently over the same values.
    You could open the file for the second time, or seek() to the beginning.'

    Returns:
      Self.
    """
    return self

  def next(self):
    line = self.readline()
    if not line:
      raise StopIteration()
    return line

  def readline(self, size=-1):
    """Read one line delimited by '\n' from the file.

    A trailing newline character is kept in the string. It may be absent when a
    file ends with an incomplete line. If the size argument is non-negative,
    it specifies the maximum string size (counting the newline) to return.
    A negative size is the same as unspecified. Empty string is returned
    only when EOF is encountered immediately.

    Args:
      size: Maximum number of bytes to read. If not specified, readline stops
        only on '\n' or EOF.

    Returns:
      The data read as a string.

    Raises:
      IOError: When this buffer is closed.
    """
    self._check_open()
    if size == 0 or not self._remaining():
      return ''

    data_list = []
    newline_offset = self._buffer.find_newline(size)
    while newline_offset < 0:
      data = self._buffer.read(size)
      size -= len(data)
      self._offset += len(data)
      data_list.append(data)
      if size == 0 or not self._remaining():
        return ''.join(data_list)
      self._buffer.reset(self._buffer_future.get_result())
      self._request_next_buffer()
      newline_offset = self._buffer.find_newline(size)

    data = self._buffer.read_to_offset(newline_offset + 1)
    self._offset += len(data)
    data_list.append(data)

    return ''.join(data_list)

  def read(self, size=-1):
    """Read data from RAW file.

    Args:
      size: Number of bytes to read as integer. Actual number of bytes
        read is always equal to size unless EOF is reached. If size is
        negative or unspecified, read the entire file.

    Returns:
      data read as str.

    Raises:
      IOError: When this buffer is closed.
    """
    self._check_open()
    if not self._remaining():
      return ''

    data_list = []
    while True:
      remaining = self._buffer.remaining()
      if size >= 0 and size < remaining:
        data_list.append(self._buffer.read(size))
        self._offset += size
        break
      else:
        size -= remaining
        self._offset += remaining
        data_list.append(self._buffer.read())

        if self._buffer_future is None:
          if size < 0 or size >= self._remaining():
            needs = self._remaining()
          else:
            needs = size
          data_list.extend(self._get_segments(self._offset, needs))
          self._offset += needs
          break

        if self._buffer_future:
          self._buffer.reset(self._buffer_future.get_result())
          self._buffer_future = None

    if self._buffer_future is None:
      self._request_next_buffer()
    return ''.join(data_list)

  def _remaining(self):
    return self._file_size - self._offset

  def _request_next_buffer(self):
    """Request next buffer.

    Requires self._offset and self._buffer are in consistent state
    """
    self._buffer_future = None
    next_offset = self._offset + self._buffer.remaining()
    if not hasattr(self, '_file_size') or next_offset != self._file_size:
      self._buffer_future = self._get_segment(next_offset,
                                              self._buffer_size)

  def _get_segments(self, start, request_size):
    """Get segments of the file from Google Storage as a list.

    A large request is broken into segments to avoid hitting urlfetch
    response size limit. Each segment is returned from a separate urlfetch.

    Args:
      start: start offset to request. Inclusive. Have to be within the
        range of the file.
      request_size: number of bytes to request.

    Returns:
      A list of file segments in order
    """
    if not request_size:
      return []

    end = start + request_size
    futures = []

    while request_size > self._max_request_size:
      futures.append(self._get_segment(start, self._max_request_size))
      request_size -= self._max_request_size
      start += self._max_request_size
    if start < end:
      futures.append(self._get_segment(start, end-start))
    return [fut.get_result() for fut in futures]

  @ndb.tasklet
  def _get_segment(self, start, request_size):
    """Get a segment of the file from Google Storage.

    Args:
      start: start offset of the segment. Inclusive. Have to be within the
        range of the file.
      request_size: number of bytes to request. Have to be small enough
        for a single urlfetch request. May go over the logical range of the
        file.

    Yields:
      a segment [start, start + request_size) of the file.

    Raises:
      ValueError: if the file has changed while reading.
    """
    end = start + request_size - 1
    content_range = '%d-%d' % (start, end)
    headers = {'Range': 'bytes=' + content_range}
    status, resp_headers, content = yield self._api.get_object_async(
        self._path, headers=headers)
    errors.check_status(status, [200, 206], self._path, headers, resp_headers,
                        body=content)
    self._check_etag(resp_headers.get('etag'))
    raise ndb.Return(content)

  def _check_etag(self, etag):
    """Check if etag is the same across requests to GCS.

    If self._etag is None, set it. If etag is set, check that the new
    etag equals the old one.

    In the __init__ method, we fire one HEAD and one GET request using
    ndb tasklet. One of them would return first and set the first value.

    Args:
      etag: etag from a GCS HTTP response. None if etag is not part of the
        response header. It could be None for example in the case of GCS
        composite file.

    Raises:
      ValueError: if two etags are not equal.
    """
    if etag is None:
      return
    elif self._etag is None:
      self._etag = etag
    elif self._etag != etag:
      raise ValueError('File on GCS has changed while reading.')

  def close(self):
    self.closed = True
    self._buffer = None
    self._buffer_future = None

  def __enter__(self):
    return self

  def __exit__(self, atype, value, traceback):
    self.close()
    return False

  def seek(self, offset, whence=os.SEEK_SET):
    """Set the file's current offset.

    Note if the new offset is out of bound, it is adjusted to either 0 or EOF.

    Args:
      offset: seek offset as number.
      whence: seek mode. Supported modes are os.SEEK_SET (absolute seek),
        os.SEEK_CUR (seek relative to the current position), and os.SEEK_END
        (seek relative to the end, offset should be negative).

    Raises:
      IOError: When this buffer is closed.
      ValueError: When whence is invalid.
    """
    self._check_open()

    self._buffer.reset()
    self._buffer_future = None

    if whence == os.SEEK_SET:
      self._offset = offset
    elif whence == os.SEEK_CUR:
      self._offset += offset
    elif whence == os.SEEK_END:
      self._offset = self._file_size + offset
    else:
      raise ValueError('Whence mode %s is invalid.' % str(whence))

    self._offset = min(self._offset, self._file_size)
    self._offset = max(self._offset, 0)
    if self._remaining():
      self._request_next_buffer()

  def tell(self):
    """Tell the file's current offset.

    Returns:
      current offset in reading this file.

    Raises:
      IOError: When this buffer is closed.
    """
    self._check_open()
    return self._offset

  def _check_open(self):
    if self.closed:
      raise IOError('Buffer is closed.')

  def seekable(self):
    return True

  def readable(self):
    return True

  def writable(self):
    return False


class _Buffer(object):
  """In memory buffer."""

  def __init__(self):
    self.reset()

  def reset(self, content='', offset=0):
    self._buffer = content
    self._offset = offset

  def read(self, size=-1):
    """Returns bytes from self._buffer and update related offsets.

    Args:
      size: number of bytes to read starting from current offset.
        Read the entire buffer if negative.

    Returns:
      Requested bytes from buffer.
    """
    if size < 0:
      offset = len(self._buffer)
    else:
      offset = self._offset + size
    return self.read_to_offset(offset)

  def read_to_offset(self, offset):
    """Returns bytes from self._buffer and update related offsets.

    Args:
      offset: read from current offset to this offset, exclusive.

    Returns:
      Requested bytes from buffer.
    """
    assert offset >= self._offset
    result = self._buffer[self._offset: offset]
    self._offset += len(result)
    return result

  def remaining(self):
    return len(self._buffer) - self._offset

  def find_newline(self, size=-1):
    """Search for newline char in buffer starting from current offset.

    Args:
      size: number of bytes to search. -1 means all.

    Returns:
      offset of newline char in buffer. -1 if doesn't exist.
    """
    if size < 0:
      return self._buffer.find('\n', self._offset)
    return self._buffer.find('\n', self._offset, self._offset + size)


class StreamingBuffer(object):
  """A class for creating large objects using the 'resumable' API.

  The API is a subset of the Python writable stream API sufficient to
  support writing zip files using the zipfile module.

  The exact sequence of calls and use of headers is documented at
  https://developers.google.com/storage/docs/developer-guide#unknownresumables
  """

  _blocksize = 256 * 1024

  _flushsize = 8 * _blocksize

  _maxrequestsize = 9 * 4 * _blocksize

  def __init__(self,
               api,
               path,
               content_type=None,
               gcs_headers=None):
    """Constructor.

    Args:
      api: A StorageApi instance.
      path: Quoted/escaped path to the object, e.g. /mybucket/myfile
      content_type: Optional content-type; Default value is
        delegate to Google Cloud Storage.
      gcs_headers: additional gs headers as a str->str dict, e.g
        {'x-goog-acl': 'private', 'x-goog-meta-foo': 'foo'}.
    Raises:
      IOError: When this location can not be found.
    """
    assert self._maxrequestsize > self._blocksize
    assert self._maxrequestsize % self._blocksize == 0
    assert self._maxrequestsize >= self._flushsize

    self._api = api
    self._path = path

    self.name = api_utils._unquote_filename(path)
    self.closed = False

    self._buffer = collections.deque()
    self._buffered = 0
    self._written = 0
    self._offset = 0

    headers = {'x-goog-resumable': 'start'}
    if content_type:
      headers['content-type'] = content_type
    if gcs_headers:
      headers.update(gcs_headers)
    status, resp_headers, content = self._api.post_object(path, headers=headers)
    errors.check_status(status, [201], path, headers, resp_headers,
                        body=content)
    loc = resp_headers.get('location')
    if not loc:
      raise IOError('No location header found in 201 response')
    parsed = urlparse.urlparse(loc)
    self._path_with_token = '%s?%s' % (self._path, parsed.query)

  def __getstate__(self):
    """Store state as part of serialization/pickling.

    The contents of the write buffer are stored. Writes to the underlying
    storage are required to be on block boundaries (_blocksize) except for the
    last write. In the worst case the pickled version of this object may be
    slightly larger than the blocksize.

    Returns:
      A dictionary with the state of this object

    """
    return {'api': self._api,
            'path': self._path,
            'path_token': self._path_with_token,
            'buffer': self._buffer,
            'buffered': self._buffered,
            'written': self._written,
            'offset': self._offset,
            'closed': self.closed}

  def __setstate__(self, state):
    """Restore state as part of deserialization/unpickling.

    Args:
      state: the dictionary from a __getstate__ call
    """
    self._api = state['api']
    self._path_with_token = state['path_token']
    self._buffer = state['buffer']
    self._buffered = state['buffered']
    self._written = state['written']
    self._offset = state['offset']
    self.closed = state['closed']
    self._path = state['path']
    self.name = api_utils._unquote_filename(self._path)

  def write(self, data):
    """Write some bytes.

    Args:
      data: data to write. str.

    Raises:
      TypeError: if data is not of type str.
    """
    self._check_open()
    if not isinstance(data, str):
      raise TypeError('Expected str but got %s.' % type(data))
    if not data:
      return
    self._buffer.append(data)
    self._buffered += len(data)
    self._offset += len(data)
    if self._buffered >= self._flushsize:
      self._flush()

  def flush(self):
    """Flush as much as possible to GCS.

    GCS *requires* that all writes except for the final one align on
    256KB boundaries. So the internal buffer may still have < 256KB bytes left
    after flush.
    """
    self._check_open()
    self._flush(finish=False)

  def tell(self):
    """Return the total number of bytes passed to write() so far.

    (There is no seek() method.)
    """
    return self._offset

  def close(self):
    """Flush the buffer and finalize the file.

    When this returns the new file is available for reading.
    """
    if not self.closed:
      self.closed = True
      self._flush(finish=True)
      self._buffer = None

  def __enter__(self):
    return self

  def __exit__(self, atype, value, traceback):
    self.close()
    return False

  def _flush(self, finish=False):
    """Internal API to flush.

    Buffer is flushed to GCS only when the total amount of buffered data is at
    least self._blocksize, or to flush the final (incomplete) block of
    the file with finish=True.
    """
    while ((finish and self._buffered >= 0) or
           (not finish and self._buffered >= self._blocksize)):
      tmp_buffer = []
      tmp_buffer_len = 0

      excess = 0
      while self._buffer:
        buf = self._buffer.popleft()
        size = len(buf)
        self._buffered -= size
        tmp_buffer.append(buf)
        tmp_buffer_len += size
        if tmp_buffer_len >= self._maxrequestsize:
          excess = tmp_buffer_len - self._maxrequestsize
          break
        if not finish and (
            tmp_buffer_len % self._blocksize + self._buffered <
            self._blocksize):
          excess = tmp_buffer_len % self._blocksize
          break

      if excess:
        over = tmp_buffer.pop()
        size = len(over)
        assert size >= excess
        tmp_buffer_len -= size
        head, tail = over[:-excess], over[-excess:]
        self._buffer.appendleft(tail)
        self._buffered += len(tail)
        if head:
          tmp_buffer.append(head)
          tmp_buffer_len += len(head)

      data = ''.join(tmp_buffer)
      file_len = '*'
      if finish and not self._buffered:
        file_len = self._written + len(data)
      self._send_data(data, self._written, file_len)
      self._written += len(data)
      if file_len != '*':
        break

  def _send_data(self, data, start_offset, file_len):
    """Send the block to the storage service.

    This is a utility method that does not modify self.

    Args:
      data: data to send in str.
      start_offset: start offset of the data in relation to the file.
      file_len: an int if this is the last data to append to the file.
        Otherwise '*'.
    """
    headers = {}
    end_offset = start_offset + len(data) - 1

    if data:
      headers['content-range'] = ('bytes %d-%d/%s' %
                                  (start_offset, end_offset, file_len))
    else:
      headers['content-range'] = ('bytes */%s' % file_len)

    status, response_headers, content = self._api.put_object(
        self._path_with_token, payload=data, headers=headers)
    if file_len == '*':
      expected = 308
    else:
      expected = 200
    errors.check_status(status, [expected], self._path, headers,
                        response_headers, content,
                        {'upload_path': self._path_with_token})

  def _get_offset_from_gcs(self):
    """Get the last offset that has been written to GCS.

    This is a utility method that does not modify self.

    Returns:
      an int of the last offset written to GCS by this upload, inclusive.
      -1 means nothing has been written.
    """
    headers = {'content-range': 'bytes */*'}
    status, response_headers, content = self._api.put_object(
        self._path_with_token, headers=headers)
    errors.check_status(status, [308], self._path, headers,
                        response_headers, content,
                        {'upload_path': self._path_with_token})
    val = response_headers.get('range')
    if val is None:
      return -1
    _, offset = val.rsplit('-', 1)
    return int(offset)

  def _force_close(self, file_length=None):
    """Close this buffer on file_length.

    Finalize this upload immediately on file_length.
    Contents that are still in memory will not be uploaded.

    This is a utility method that does not modify self.

    Args:
      file_length: file length. Must match what has been uploaded. If None,
        it will be queried from GCS.
    """
    if file_length is None:
      file_length = self._get_offset_from_gcs() + 1
    self._send_data('', 0, file_length)

  def _check_open(self):
    if self.closed:
      raise IOError('Buffer is closed.')

  def seekable(self):
    return False

  def readable(self):
    return False

  def writable(self):
    return True

########NEW FILE########
__FILENAME__ = test_utils
# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

"""Utils for testing."""


class MockUrlFetchResult(object):

  def __init__(self, status, headers, body):
    self.status_code = status
    self.headers = headers
    self.content = body
    self.content_was_truncated = False
    self.final_url = None

########NEW FILE########
__FILENAME__ = iri2uri
"""
iri2uri

Converts an IRI to a URI.

"""
__author__ = "Joe Gregorio (joe@bitworking.org)"
__copyright__ = "Copyright 2006, Joe Gregorio"
__contributors__ = []
__version__ = "1.0.0"
__license__ = "MIT"
__history__ = """
"""

import urlparse


# Convert an IRI to a URI following the rules in RFC 3987
#
# The characters we need to enocde and escape are defined in the spec:
#
# iprivate =  %xE000-F8FF / %xF0000-FFFFD / %x100000-10FFFD
# ucschar = %xA0-D7FF / %xF900-FDCF / %xFDF0-FFEF
#         / %x10000-1FFFD / %x20000-2FFFD / %x30000-3FFFD
#         / %x40000-4FFFD / %x50000-5FFFD / %x60000-6FFFD
#         / %x70000-7FFFD / %x80000-8FFFD / %x90000-9FFFD
#         / %xA0000-AFFFD / %xB0000-BFFFD / %xC0000-CFFFD
#         / %xD0000-DFFFD / %xE1000-EFFFD

escape_range = [
    (0xA0, 0xD7FF),
    (0xE000, 0xF8FF),
    (0xF900, 0xFDCF),
    (0xFDF0, 0xFFEF),
    (0x10000, 0x1FFFD),
    (0x20000, 0x2FFFD),
    (0x30000, 0x3FFFD),
    (0x40000, 0x4FFFD),
    (0x50000, 0x5FFFD),
    (0x60000, 0x6FFFD),
    (0x70000, 0x7FFFD),
    (0x80000, 0x8FFFD),
    (0x90000, 0x9FFFD),
    (0xA0000, 0xAFFFD),
    (0xB0000, 0xBFFFD),
    (0xC0000, 0xCFFFD),
    (0xD0000, 0xDFFFD),
    (0xE1000, 0xEFFFD),
    (0xF0000, 0xFFFFD),
    (0x100000, 0x10FFFD),
]

def encode(c):
    retval = c
    i = ord(c)
    for low, high in escape_range:
        if i < low:
            break
        if i >= low and i <= high:
            retval = "".join(["%%%2X" % ord(o) for o in c.encode('utf-8')])
            break
    return retval


def iri2uri(uri):
    """Convert an IRI to a URI. Note that IRIs must be
    passed in a unicode strings. That is, do not utf-8 encode
    the IRI before passing it into the function."""
    if isinstance(uri ,unicode):
        (scheme, authority, path, query, fragment) = urlparse.urlsplit(uri)
        authority = authority.encode('idna')
        # For each character in 'ucschar' or 'iprivate'
        #  1. encode as utf-8
        #  2. then %-encode each octet of that utf-8
        uri = urlparse.urlunsplit((scheme, authority, path, query, fragment))
        uri = "".join([encode(c) for c in uri])
    return uri

if __name__ == "__main__":
    import unittest

    class Test(unittest.TestCase):

        def test_uris(self):
            """Test that URIs are invariant under the transformation."""
            invariant = [
                u"ftp://ftp.is.co.za/rfc/rfc1808.txt",
                u"http://www.ietf.org/rfc/rfc2396.txt",
                u"ldap://[2001:db8::7]/c=GB?objectClass?one",
                u"mailto:John.Doe@example.com",
                u"news:comp.infosystems.www.servers.unix",
                u"tel:+1-816-555-1212",
                u"telnet://192.0.2.16:80/",
                u"urn:oasis:names:specification:docbook:dtd:xml:4.1.2" ]
            for uri in invariant:
                self.assertEqual(uri, iri2uri(uri))

        def test_iri(self):
            """ Test that the right type of escaping is done for each part of the URI."""
            self.assertEqual("http://xn--o3h.com/%E2%98%84", iri2uri(u"http://\N{COMET}.com/\N{COMET}"))
            self.assertEqual("http://bitworking.org/?fred=%E2%98%84", iri2uri(u"http://bitworking.org/?fred=\N{COMET}"))
            self.assertEqual("http://bitworking.org/#%E2%98%84", iri2uri(u"http://bitworking.org/#\N{COMET}"))
            self.assertEqual("#%E2%98%84", iri2uri(u"#\N{COMET}"))
            self.assertEqual("/fred?bar=%E2%98%9A#%E2%98%84", iri2uri(u"/fred?bar=\N{BLACK LEFT POINTING INDEX}#\N{COMET}"))
            self.assertEqual("/fred?bar=%E2%98%9A#%E2%98%84", iri2uri(iri2uri(u"/fred?bar=\N{BLACK LEFT POINTING INDEX}#\N{COMET}")))
            self.assertNotEqual("/fred?bar=%E2%98%9A#%E2%98%84", iri2uri(u"/fred?bar=\N{BLACK LEFT POINTING INDEX}#\N{COMET}".encode('utf-8')))

    unittest.main()



########NEW FILE########
__FILENAME__ = socks
"""SocksiPy - Python SOCKS module.
Version 1.00

Copyright 2006 Dan-Haim. All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.
3. Neither the name of Dan Haim nor the names of his contributors may be used
   to endorse or promote products derived from this software without specific
   prior written permission.

THIS SOFTWARE IS PROVIDED BY DAN HAIM "AS IS" AND ANY EXPRESS OR IMPLIED
WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
EVENT SHALL DAN HAIM OR HIS CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA
OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMANGE.


This module provides a standard socket-like interface for Python
for tunneling connections through SOCKS proxies.

"""

"""

Minor modifications made by Christopher Gilbert (http://motomastyle.com/)
for use in PyLoris (http://pyloris.sourceforge.net/)

Minor modifications made by Mario Vilas (http://breakingcode.wordpress.com/)
mainly to merge bug fixes found in Sourceforge

"""

import base64
import socket
import struct
import sys

if getattr(socket, 'socket', None) is None:
    raise ImportError('socket.socket missing, proxy support unusable')

PROXY_TYPE_SOCKS4 = 1
PROXY_TYPE_SOCKS5 = 2
PROXY_TYPE_HTTP = 3
PROXY_TYPE_HTTP_NO_TUNNEL = 4

_defaultproxy = None
_orgsocket = socket.socket

class ProxyError(Exception): pass
class GeneralProxyError(ProxyError): pass
class Socks5AuthError(ProxyError): pass
class Socks5Error(ProxyError): pass
class Socks4Error(ProxyError): pass
class HTTPError(ProxyError): pass

_generalerrors = ("success",
    "invalid data",
    "not connected",
    "not available",
    "bad proxy type",
    "bad input")

_socks5errors = ("succeeded",
    "general SOCKS server failure",
    "connection not allowed by ruleset",
    "Network unreachable",
    "Host unreachable",
    "Connection refused",
    "TTL expired",
    "Command not supported",
    "Address type not supported",
    "Unknown error")

_socks5autherrors = ("succeeded",
    "authentication is required",
    "all offered authentication methods were rejected",
    "unknown username or invalid password",
    "unknown error")

_socks4errors = ("request granted",
    "request rejected or failed",
    "request rejected because SOCKS server cannot connect to identd on the client",
    "request rejected because the client program and identd report different user-ids",
    "unknown error")

def setdefaultproxy(proxytype=None, addr=None, port=None, rdns=True, username=None, password=None):
    """setdefaultproxy(proxytype, addr[, port[, rdns[, username[, password]]]])
    Sets a default proxy which all further socksocket objects will use,
    unless explicitly changed.
    """
    global _defaultproxy
    _defaultproxy = (proxytype, addr, port, rdns, username, password)

def wrapmodule(module):
    """wrapmodule(module)
    Attempts to replace a module's socket library with a SOCKS socket. Must set
    a default proxy using setdefaultproxy(...) first.
    This will only work on modules that import socket directly into the namespace;
    most of the Python Standard Library falls into this category.
    """
    if _defaultproxy != None:
        module.socket.socket = socksocket
    else:
        raise GeneralProxyError((4, "no proxy specified"))

class socksocket(socket.socket):
    """socksocket([family[, type[, proto]]]) -> socket object
    Open a SOCKS enabled socket. The parameters are the same as
    those of the standard socket init. In order for SOCKS to work,
    you must specify family=AF_INET, type=SOCK_STREAM and proto=0.
    """

    def __init__(self, family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0, _sock=None):
        _orgsocket.__init__(self, family, type, proto, _sock)
        if _defaultproxy != None:
            self.__proxy = _defaultproxy
        else:
            self.__proxy = (None, None, None, None, None, None)
        self.__proxysockname = None
        self.__proxypeername = None
        self.__httptunnel = True

    def __recvall(self, count):
        """__recvall(count) -> data
        Receive EXACTLY the number of bytes requested from the socket.
        Blocks until the required number of bytes have been received.
        """
        data = self.recv(count)
        while len(data) < count:
            d = self.recv(count-len(data))
            if not d: raise GeneralProxyError((0, "connection closed unexpectedly"))
            data = data + d
        return data

    def sendall(self, content, *args):
        """ override socket.socket.sendall method to rewrite the header
        for non-tunneling proxies if needed
        """
        if not self.__httptunnel:
            content = self.__rewriteproxy(content)
        return super(socksocket, self).sendall(content, *args)

    def __rewriteproxy(self, header):
        """ rewrite HTTP request headers to support non-tunneling proxies
        (i.e. those which do not support the CONNECT method).
        This only works for HTTP (not HTTPS) since HTTPS requires tunneling.
        """
        host, endpt = None, None
        hdrs = header.split("\r\n")
        for hdr in hdrs:
            if hdr.lower().startswith("host:"):
                host = hdr
            elif hdr.lower().startswith("get") or hdr.lower().startswith("post"):
                endpt = hdr
        if host and endpt:
            hdrs.remove(host)
            hdrs.remove(endpt)
            host = host.split(" ")[1]
            endpt = endpt.split(" ")
            if (self.__proxy[4] != None and self.__proxy[5] != None):
                hdrs.insert(0, self.__getauthheader())
            hdrs.insert(0, "Host: %s" % host)
            hdrs.insert(0, "%s http://%s%s %s" % (endpt[0], host, endpt[1], endpt[2]))
        return "\r\n".join(hdrs)

    def __getauthheader(self):
        auth = self.__proxy[4] + ":" + self.__proxy[5]
        return "Proxy-Authorization: Basic " + base64.b64encode(auth)

    def setproxy(self, proxytype=None, addr=None, port=None, rdns=True, username=None, password=None):
        """setproxy(proxytype, addr[, port[, rdns[, username[, password]]]])
        Sets the proxy to be used.
        proxytype -    The type of the proxy to be used. Three types
                are supported: PROXY_TYPE_SOCKS4 (including socks4a),
                PROXY_TYPE_SOCKS5 and PROXY_TYPE_HTTP
        addr -        The address of the server (IP or DNS).
        port -        The port of the server. Defaults to 1080 for SOCKS
                servers and 8080 for HTTP proxy servers.
        rdns -        Should DNS queries be preformed on the remote side
                (rather than the local side). The default is True.
                Note: This has no effect with SOCKS4 servers.
        username -    Username to authenticate with to the server.
                The default is no authentication.
        password -    Password to authenticate with to the server.
                Only relevant when username is also provided.
        """
        self.__proxy = (proxytype, addr, port, rdns, username, password)

    def __negotiatesocks5(self, destaddr, destport):
        """__negotiatesocks5(self,destaddr,destport)
        Negotiates a connection through a SOCKS5 server.
        """
        # First we'll send the authentication packages we support.
        if (self.__proxy[4]!=None) and (self.__proxy[5]!=None):
            # The username/password details were supplied to the
            # setproxy method so we support the USERNAME/PASSWORD
            # authentication (in addition to the standard none).
            self.sendall(struct.pack('BBBB', 0x05, 0x02, 0x00, 0x02))
        else:
            # No username/password were entered, therefore we
            # only support connections with no authentication.
            self.sendall(struct.pack('BBB', 0x05, 0x01, 0x00))
        # We'll receive the server's response to determine which
        # method was selected
        chosenauth = self.__recvall(2)
        if chosenauth[0:1] != chr(0x05).encode():
            self.close()
            raise GeneralProxyError((1, _generalerrors[1]))
        # Check the chosen authentication method
        if chosenauth[1:2] == chr(0x00).encode():
            # No authentication is required
            pass
        elif chosenauth[1:2] == chr(0x02).encode():
            # Okay, we need to perform a basic username/password
            # authentication.
            self.sendall(chr(0x01).encode() + chr(len(self.__proxy[4])) + self.__proxy[4] + chr(len(self.__proxy[5])) + self.__proxy[5])
            authstat = self.__recvall(2)
            if authstat[0:1] != chr(0x01).encode():
                # Bad response
                self.close()
                raise GeneralProxyError((1, _generalerrors[1]))
            if authstat[1:2] != chr(0x00).encode():
                # Authentication failed
                self.close()
                raise Socks5AuthError((3, _socks5autherrors[3]))
            # Authentication succeeded
        else:
            # Reaching here is always bad
            self.close()
            if chosenauth[1] == chr(0xFF).encode():
                raise Socks5AuthError((2, _socks5autherrors[2]))
            else:
                raise GeneralProxyError((1, _generalerrors[1]))
        # Now we can request the actual connection
        req = struct.pack('BBB', 0x05, 0x01, 0x00)
        # If the given destination address is an IP address, we'll
        # use the IPv4 address request even if remote resolving was specified.
        try:
            ipaddr = socket.inet_aton(destaddr)
            req = req + chr(0x01).encode() + ipaddr
        except socket.error:
            # Well it's not an IP number,  so it's probably a DNS name.
            if self.__proxy[3]:
                # Resolve remotely
                ipaddr = None
                req = req + chr(0x03).encode() + chr(len(destaddr)).encode() + destaddr
            else:
                # Resolve locally
                ipaddr = socket.inet_aton(socket.gethostbyname(destaddr))
                req = req + chr(0x01).encode() + ipaddr
        req = req + struct.pack(">H", destport)
        self.sendall(req)
        # Get the response
        resp = self.__recvall(4)
        if resp[0:1] != chr(0x05).encode():
            self.close()
            raise GeneralProxyError((1, _generalerrors[1]))
        elif resp[1:2] != chr(0x00).encode():
            # Connection failed
            self.close()
            if ord(resp[1:2])<=8:
                raise Socks5Error((ord(resp[1:2]), _socks5errors[ord(resp[1:2])]))
            else:
                raise Socks5Error((9, _socks5errors[9]))
        # Get the bound address/port
        elif resp[3:4] == chr(0x01).encode():
            boundaddr = self.__recvall(4)
        elif resp[3:4] == chr(0x03).encode():
            resp = resp + self.recv(1)
            boundaddr = self.__recvall(ord(resp[4:5]))
        else:
            self.close()
            raise GeneralProxyError((1,_generalerrors[1]))
        boundport = struct.unpack(">H", self.__recvall(2))[0]
        self.__proxysockname = (boundaddr, boundport)
        if ipaddr != None:
            self.__proxypeername = (socket.inet_ntoa(ipaddr), destport)
        else:
            self.__proxypeername = (destaddr, destport)

    def getproxysockname(self):
        """getsockname() -> address info
        Returns the bound IP address and port number at the proxy.
        """
        return self.__proxysockname

    def getproxypeername(self):
        """getproxypeername() -> address info
        Returns the IP and port number of the proxy.
        """
        return _orgsocket.getpeername(self)

    def getpeername(self):
        """getpeername() -> address info
        Returns the IP address and port number of the destination
        machine (note: getproxypeername returns the proxy)
        """
        return self.__proxypeername

    def __negotiatesocks4(self,destaddr,destport):
        """__negotiatesocks4(self,destaddr,destport)
        Negotiates a connection through a SOCKS4 server.
        """
        # Check if the destination address provided is an IP address
        rmtrslv = False
        try:
            ipaddr = socket.inet_aton(destaddr)
        except socket.error:
            # It's a DNS name. Check where it should be resolved.
            if self.__proxy[3]:
                ipaddr = struct.pack("BBBB", 0x00, 0x00, 0x00, 0x01)
                rmtrslv = True
            else:
                ipaddr = socket.inet_aton(socket.gethostbyname(destaddr))
        # Construct the request packet
        req = struct.pack(">BBH", 0x04, 0x01, destport) + ipaddr
        # The username parameter is considered userid for SOCKS4
        if self.__proxy[4] != None:
            req = req + self.__proxy[4]
        req = req + chr(0x00).encode()
        # DNS name if remote resolving is required
        # NOTE: This is actually an extension to the SOCKS4 protocol
        # called SOCKS4A and may not be supported in all cases.
        if rmtrslv:
            req = req + destaddr + chr(0x00).encode()
        self.sendall(req)
        # Get the response from the server
        resp = self.__recvall(8)
        if resp[0:1] != chr(0x00).encode():
            # Bad data
            self.close()
            raise GeneralProxyError((1,_generalerrors[1]))
        if resp[1:2] != chr(0x5A).encode():
            # Server returned an error
            self.close()
            if ord(resp[1:2]) in (91, 92, 93):
                self.close()
                raise Socks4Error((ord(resp[1:2]), _socks4errors[ord(resp[1:2]) - 90]))
            else:
                raise Socks4Error((94, _socks4errors[4]))
        # Get the bound address/port
        self.__proxysockname = (socket.inet_ntoa(resp[4:]), struct.unpack(">H", resp[2:4])[0])
        if rmtrslv != None:
            self.__proxypeername = (socket.inet_ntoa(ipaddr), destport)
        else:
            self.__proxypeername = (destaddr, destport)

    def __negotiatehttp(self, destaddr, destport):
        """__negotiatehttp(self,destaddr,destport)
        Negotiates a connection through an HTTP server.
        """
        # If we need to resolve locally, we do this now
        if not self.__proxy[3]:
            addr = socket.gethostbyname(destaddr)
        else:
            addr = destaddr
        headers =  ["CONNECT ", addr, ":", str(destport), " HTTP/1.1\r\n"]
        headers += ["Host: ", destaddr, "\r\n"]
        if (self.__proxy[4] != None and self.__proxy[5] != None):
                headers += [self.__getauthheader(), "\r\n"]
        headers.append("\r\n")
        self.sendall("".join(headers).encode())
        # We read the response until we get the string "\r\n\r\n"
        resp = self.recv(1)
        while resp.find("\r\n\r\n".encode()) == -1:
            resp = resp + self.recv(1)
        # We just need the first line to check if the connection
        # was successful
        statusline = resp.splitlines()[0].split(" ".encode(), 2)
        if statusline[0] not in ("HTTP/1.0".encode(), "HTTP/1.1".encode()):
            self.close()
            raise GeneralProxyError((1, _generalerrors[1]))
        try:
            statuscode = int(statusline[1])
        except ValueError:
            self.close()
            raise GeneralProxyError((1, _generalerrors[1]))
        if statuscode != 200:
            self.close()
            raise HTTPError((statuscode, statusline[2]))
        self.__proxysockname = ("0.0.0.0", 0)
        self.__proxypeername = (addr, destport)

    def connect(self, destpair):
        """connect(self, despair)
        Connects to the specified destination through a proxy.
        destpar - A tuple of the IP/DNS address and the port number.
        (identical to socket's connect).
        To select the proxy server use setproxy().
        """
        # Do a minimal input check first
        if (not type(destpair) in (list,tuple)) or (len(destpair) < 2) or (not isinstance(destpair[0], basestring)) or (type(destpair[1]) != int):
            raise GeneralProxyError((5, _generalerrors[5]))
        if self.__proxy[0] == PROXY_TYPE_SOCKS5:
            if self.__proxy[2] != None:
                portnum = self.__proxy[2]
            else:
                portnum = 1080
            _orgsocket.connect(self, (self.__proxy[1], portnum))
            self.__negotiatesocks5(destpair[0], destpair[1])
        elif self.__proxy[0] == PROXY_TYPE_SOCKS4:
            if self.__proxy[2] != None:
                portnum = self.__proxy[2]
            else:
                portnum = 1080
            _orgsocket.connect(self,(self.__proxy[1], portnum))
            self.__negotiatesocks4(destpair[0], destpair[1])
        elif self.__proxy[0] == PROXY_TYPE_HTTP:
            if self.__proxy[2] != None:
                portnum = self.__proxy[2]
            else:
                portnum = 8080
            _orgsocket.connect(self,(self.__proxy[1], portnum))
            self.__negotiatehttp(destpair[0], destpair[1])
        elif self.__proxy[0] == PROXY_TYPE_HTTP_NO_TUNNEL:
            if self.__proxy[2] != None:
                portnum = self.__proxy[2]
            else:
                portnum = 8080
            _orgsocket.connect(self,(self.__proxy[1],portnum))
            if destpair[1] == 443:
                self.__negotiatehttp(destpair[0],destpair[1])
            else:
                self.__httptunnel = False
        elif self.__proxy[0] == None:
            _orgsocket.connect(self, (destpair[0], destpair[1]))
        else:
            raise GeneralProxyError((4, _generalerrors[4]))

########NEW FILE########
__FILENAME__ = anyjson
# Copyright (C) 2010 Google Inc.
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

"""Utility module to import a JSON module

Hides all the messy details of exactly where
we get a simplejson module from.
"""

__author__ = 'jcgregorio@google.com (Joe Gregorio)'


try: # pragma: no cover
  # Should work for Python2.6 and higher.
  import json as simplejson
except ImportError: # pragma: no cover
  try:
    import simplejson
  except ImportError:
    # Try to import from django, should work on App Engine
    from django.utils import simplejson

########NEW FILE########
__FILENAME__ = appengine
# Copyright (C) 2010 Google Inc.
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

"""Utilities for Google App Engine

Utilities for making it easier to use OAuth 2.0 on Google App Engine.
"""

__author__ = 'jcgregorio@google.com (Joe Gregorio)'

import base64
import cgi
import httplib2
import logging
import os
import pickle
import threading
import time

from google.appengine.api import app_identity
from google.appengine.api import memcache
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import login_required
from google.appengine.ext.webapp.util import run_wsgi_app
from oauth2client import GOOGLE_AUTH_URI
from oauth2client import GOOGLE_REVOKE_URI
from oauth2client import GOOGLE_TOKEN_URI
from oauth2client import clientsecrets
from oauth2client import util
from oauth2client import xsrfutil
from oauth2client.anyjson import simplejson
from oauth2client.client import AccessTokenRefreshError
from oauth2client.client import AssertionCredentials
from oauth2client.client import Credentials
from oauth2client.client import Flow
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.client import Storage

# TODO(dhermes): Resolve import issue.
# This is a temporary fix for a Google internal issue.
try:
  from google.appengine.ext import ndb
except ImportError:
  ndb = None


logger = logging.getLogger(__name__)

OAUTH2CLIENT_NAMESPACE = 'oauth2client#ns'

XSRF_MEMCACHE_ID = 'xsrf_secret_key'


def _safe_html(s):
  """Escape text to make it safe to display.

  Args:
    s: string, The text to escape.

  Returns:
    The escaped text as a string.
  """
  return cgi.escape(s, quote=1).replace("'", '&#39;')


class InvalidClientSecretsError(Exception):
  """The client_secrets.json file is malformed or missing required fields."""


class InvalidXsrfTokenError(Exception):
  """The XSRF token is invalid or expired."""


class SiteXsrfSecretKey(db.Model):
  """Storage for the sites XSRF secret key.

  There will only be one instance stored of this model, the one used for the
  site.
  """
  secret = db.StringProperty()

if ndb is not None:
  class SiteXsrfSecretKeyNDB(ndb.Model):
    """NDB Model for storage for the sites XSRF secret key.

    Since this model uses the same kind as SiteXsrfSecretKey, it can be used
    interchangeably. This simply provides an NDB model for interacting with the
    same data the DB model interacts with.

    There should only be one instance stored of this model, the one used for the
    site.
    """
    secret = ndb.StringProperty()

    @classmethod
    def _get_kind(cls):
      """Return the kind name for this class."""
      return 'SiteXsrfSecretKey'


def _generate_new_xsrf_secret_key():
  """Returns a random XSRF secret key.
  """
  return os.urandom(16).encode("hex")


def xsrf_secret_key():
  """Return the secret key for use for XSRF protection.

  If the Site entity does not have a secret key, this method will also create
  one and persist it.

  Returns:
    The secret key.
  """
  secret = memcache.get(XSRF_MEMCACHE_ID, namespace=OAUTH2CLIENT_NAMESPACE)
  if not secret:
    # Load the one and only instance of SiteXsrfSecretKey.
    model = SiteXsrfSecretKey.get_or_insert(key_name='site')
    if not model.secret:
      model.secret = _generate_new_xsrf_secret_key()
      model.put()
    secret = model.secret
    memcache.add(XSRF_MEMCACHE_ID, secret, namespace=OAUTH2CLIENT_NAMESPACE)

  return str(secret)


class AppAssertionCredentials(AssertionCredentials):
  """Credentials object for App Engine Assertion Grants

  This object will allow an App Engine application to identify itself to Google
  and other OAuth 2.0 servers that can verify assertions. It can be used for the
  purpose of accessing data stored under an account assigned to the App Engine
  application itself.

  This credential does not require a flow to instantiate because it represents
  a two legged flow, and therefore has all of the required information to
  generate and refresh its own access tokens.
  """

  @util.positional(2)
  def __init__(self, scope, **kwargs):
    """Constructor for AppAssertionCredentials

    Args:
      scope: string or iterable of strings, scope(s) of the credentials being
        requested.
    """
    self.scope = util.scopes_to_string(scope)

    # Assertion type is no longer used, but still in the parent class signature.
    super(AppAssertionCredentials, self).__init__(None)

  @classmethod
  def from_json(cls, json):
    data = simplejson.loads(json)
    return AppAssertionCredentials(data['scope'])

  def _refresh(self, http_request):
    """Refreshes the access_token.

    Since the underlying App Engine app_identity implementation does its own
    caching we can skip all the storage hoops and just to a refresh using the
    API.

    Args:
      http_request: callable, a callable that matches the method signature of
        httplib2.Http.request, used to make the refresh request.

    Raises:
      AccessTokenRefreshError: When the refresh fails.
    """
    try:
      scopes = self.scope.split()
      (token, _) = app_identity.get_access_token(scopes)
    except app_identity.Error, e:
      raise AccessTokenRefreshError(str(e))
    self.access_token = token


class FlowProperty(db.Property):
  """App Engine datastore Property for Flow.

  Utility property that allows easy storage and retrieval of an
  oauth2client.Flow"""

  # Tell what the user type is.
  data_type = Flow

  # For writing to datastore.
  def get_value_for_datastore(self, model_instance):
    flow = super(FlowProperty,
                 self).get_value_for_datastore(model_instance)
    return db.Blob(pickle.dumps(flow))

  # For reading from datastore.
  def make_value_from_datastore(self, value):
    if value is None:
      return None
    return pickle.loads(value)

  def validate(self, value):
    if value is not None and not isinstance(value, Flow):
      raise db.BadValueError('Property %s must be convertible '
                          'to a FlowThreeLegged instance (%s)' %
                          (self.name, value))
    return super(FlowProperty, self).validate(value)

  def empty(self, value):
    return not value


if ndb is not None:
  class FlowNDBProperty(ndb.PickleProperty):
    """App Engine NDB datastore Property for Flow.

    Serves the same purpose as the DB FlowProperty, but for NDB models. Since
    PickleProperty inherits from BlobProperty, the underlying representation of
    the data in the datastore will be the same as in the DB case.

    Utility property that allows easy storage and retrieval of an
    oauth2client.Flow
    """

    def _validate(self, value):
      """Validates a value as a proper Flow object.

      Args:
        value: A value to be set on the property.

      Raises:
        TypeError if the value is not an instance of Flow.
      """
      logger.info('validate: Got type %s', type(value))
      if value is not None and not isinstance(value, Flow):
        raise TypeError('Property %s must be convertible to a flow '
                        'instance; received: %s.' % (self._name, value))


class CredentialsProperty(db.Property):
  """App Engine datastore Property for Credentials.

  Utility property that allows easy storage and retrieval of
  oath2client.Credentials
  """

  # Tell what the user type is.
  data_type = Credentials

  # For writing to datastore.
  def get_value_for_datastore(self, model_instance):
    logger.info("get: Got type " + str(type(model_instance)))
    cred = super(CredentialsProperty,
                 self).get_value_for_datastore(model_instance)
    if cred is None:
      cred = ''
    else:
      cred = cred.to_json()
    return db.Blob(cred)

  # For reading from datastore.
  def make_value_from_datastore(self, value):
    logger.info("make: Got type " + str(type(value)))
    if value is None:
      return None
    if len(value) == 0:
      return None
    try:
      credentials = Credentials.new_from_json(value)
    except ValueError:
      credentials = None
    return credentials

  def validate(self, value):
    value = super(CredentialsProperty, self).validate(value)
    logger.info("validate: Got type " + str(type(value)))
    if value is not None and not isinstance(value, Credentials):
      raise db.BadValueError('Property %s must be convertible '
                          'to a Credentials instance (%s)' %
                            (self.name, value))
    #if value is not None and not isinstance(value, Credentials):
    #  return None
    return value


if ndb is not None:
  # TODO(dhermes): Turn this into a JsonProperty and overhaul the Credentials
  #                and subclass mechanics to use new_from_dict, to_dict,
  #                from_dict, etc.
  class CredentialsNDBProperty(ndb.BlobProperty):
    """App Engine NDB datastore Property for Credentials.

    Serves the same purpose as the DB CredentialsProperty, but for NDB models.
    Since CredentialsProperty stores data as a blob and this inherits from
    BlobProperty, the data in the datastore will be the same as in the DB case.

    Utility property that allows easy storage and retrieval of Credentials and
    subclasses.
    """
    def _validate(self, value):
      """Validates a value as a proper credentials object.

      Args:
        value: A value to be set on the property.

      Raises:
        TypeError if the value is not an instance of Credentials.
      """
      logger.info('validate: Got type %s', type(value))
      if value is not None and not isinstance(value, Credentials):
        raise TypeError('Property %s must be convertible to a credentials '
                        'instance; received: %s.' % (self._name, value))

    def _to_base_type(self, value):
      """Converts our validated value to a JSON serialized string.

      Args:
        value: A value to be set in the datastore.

      Returns:
        A JSON serialized version of the credential, else '' if value is None.
      """
      if value is None:
        return ''
      else:
        return value.to_json()

    def _from_base_type(self, value):
      """Converts our stored JSON string back to the desired type.

      Args:
        value: A value from the datastore to be converted to the desired type.

      Returns:
        A deserialized Credentials (or subclass) object, else None if the
            value can't be parsed.
      """
      if not value:
        return None
      try:
        # Uses the from_json method of the implied class of value
        credentials = Credentials.new_from_json(value)
      except ValueError:
        credentials = None
      return credentials


class StorageByKeyName(Storage):
  """Store and retrieve a credential to and from the App Engine datastore.

  This Storage helper presumes the Credentials have been stored as a
  CredentialsProperty or CredentialsNDBProperty on a datastore model class, and
  that entities are stored by key_name.
  """

  @util.positional(4)
  def __init__(self, model, key_name, property_name, cache=None, user=None):
    """Constructor for Storage.

    Args:
      model: db.Model or ndb.Model, model class
      key_name: string, key name for the entity that has the credentials
      property_name: string, name of the property that is a CredentialsProperty
        or CredentialsNDBProperty.
      cache: memcache, a write-through cache to put in front of the datastore.
        If the model you are using is an NDB model, using a cache will be
        redundant since the model uses an instance cache and memcache for you.
      user: users.User object, optional. Can be used to grab user ID as a
        key_name if no key name is specified.
    """
    if key_name is None:
      if user is None:
        raise ValueError('StorageByKeyName called with no key name or user.')
      key_name = user.user_id()

    self._model = model
    self._key_name = key_name
    self._property_name = property_name
    self._cache = cache

  def _is_ndb(self):
    """Determine whether the model of the instance is an NDB model.

    Returns:
      Boolean indicating whether or not the model is an NDB or DB model.
    """
    # issubclass will fail if one of the arguments is not a class, only need
    # worry about new-style classes since ndb and db models are new-style
    if isinstance(self._model, type):
      if ndb is not None and issubclass(self._model, ndb.Model):
        return True
      elif issubclass(self._model, db.Model):
        return False

    raise TypeError('Model class not an NDB or DB model: %s.' % (self._model,))

  def _get_entity(self):
    """Retrieve entity from datastore.

    Uses a different model method for db or ndb models.

    Returns:
      Instance of the model corresponding to the current storage object
          and stored using the key name of the storage object.
    """
    if self._is_ndb():
      return self._model.get_by_id(self._key_name)
    else:
      return self._model.get_by_key_name(self._key_name)

  def _delete_entity(self):
    """Delete entity from datastore.

    Attempts to delete using the key_name stored on the object, whether or not
    the given key is in the datastore.
    """
    if self._is_ndb():
      ndb.Key(self._model, self._key_name).delete()
    else:
      entity_key = db.Key.from_path(self._model.kind(), self._key_name)
      db.delete(entity_key)

  def locked_get(self):
    """Retrieve Credential from datastore.

    Returns:
      oauth2client.Credentials
    """
    credentials = None
    if self._cache:
      json = self._cache.get(self._key_name)
      if json:
        credentials = Credentials.new_from_json(json)
    if credentials is None:
      entity = self._get_entity()
      if entity is not None:
        credentials = getattr(entity, self._property_name)
        if self._cache:
          self._cache.set(self._key_name, credentials.to_json())

    if credentials and hasattr(credentials, 'set_store'):
      credentials.set_store(self)
    return credentials

  def locked_put(self, credentials):
    """Write a Credentials to the datastore.

    Args:
      credentials: Credentials, the credentials to store.
    """
    entity = self._model.get_or_insert(self._key_name)
    setattr(entity, self._property_name, credentials)
    entity.put()
    if self._cache:
      self._cache.set(self._key_name, credentials.to_json())

  def locked_delete(self):
    """Delete Credential from datastore."""

    if self._cache:
      self._cache.delete(self._key_name)

    self._delete_entity()


class CredentialsModel(db.Model):
  """Storage for OAuth 2.0 Credentials

  Storage of the model is keyed by the user.user_id().
  """
  credentials = CredentialsProperty()


if ndb is not None:
  class CredentialsNDBModel(ndb.Model):
    """NDB Model for storage of OAuth 2.0 Credentials

    Since this model uses the same kind as CredentialsModel and has a property
    which can serialize and deserialize Credentials correctly, it can be used
    interchangeably with a CredentialsModel to access, insert and delete the
    same entities. This simply provides an NDB model for interacting with the
    same data the DB model interacts with.

    Storage of the model is keyed by the user.user_id().
    """
    credentials = CredentialsNDBProperty()

    @classmethod
    def _get_kind(cls):
      """Return the kind name for this class."""
      return 'CredentialsModel'


def _build_state_value(request_handler, user):
  """Composes the value for the 'state' parameter.

  Packs the current request URI and an XSRF token into an opaque string that
  can be passed to the authentication server via the 'state' parameter.

  Args:
    request_handler: webapp.RequestHandler, The request.
    user: google.appengine.api.users.User, The current user.

  Returns:
    The state value as a string.
  """
  uri = request_handler.request.url
  token = xsrfutil.generate_token(xsrf_secret_key(), user.user_id(),
                                  action_id=str(uri))
  return  uri + ':' + token


def _parse_state_value(state, user):
  """Parse the value of the 'state' parameter.

  Parses the value and validates the XSRF token in the state parameter.

  Args:
    state: string, The value of the state parameter.
    user: google.appengine.api.users.User, The current user.

  Raises:
    InvalidXsrfTokenError: if the XSRF token is invalid.

  Returns:
    The redirect URI.
  """
  uri, token = state.rsplit(':', 1)
  if not xsrfutil.validate_token(xsrf_secret_key(), token, user.user_id(),
                                 action_id=uri):
    raise InvalidXsrfTokenError()

  return uri


class OAuth2Decorator(object):
  """Utility for making OAuth 2.0 easier.

  Instantiate and then use with oauth_required or oauth_aware
  as decorators on webapp.RequestHandler methods.

  Example:

    decorator = OAuth2Decorator(
        client_id='837...ent.com',
        client_secret='Qh...wwI',
        scope='https://www.googleapis.com/auth/plus')


    class MainHandler(webapp.RequestHandler):

      @decorator.oauth_required
      def get(self):
        http = decorator.http()
        # http is authorized with the user's Credentials and can be used
        # in API calls

  """

  def set_credentials(self, credentials):
    self._tls.credentials = credentials

  def get_credentials(self):
    """A thread local Credentials object.

    Returns:
      A client.Credentials object, or None if credentials hasn't been set in
      this thread yet, which may happen when calling has_credentials inside
      oauth_aware.
    """
    return getattr(self._tls, 'credentials', None)

  credentials = property(get_credentials, set_credentials)

  def set_flow(self, flow):
    self._tls.flow = flow

  def get_flow(self):
    """A thread local Flow object.

    Returns:
      A credentials.Flow object, or None if the flow hasn't been set in this
      thread yet, which happens in _create_flow() since Flows are created
      lazily.
    """
    return getattr(self._tls, 'flow', None)

  flow = property(get_flow, set_flow)


  @util.positional(4)
  def __init__(self, client_id, client_secret, scope,
               auth_uri=GOOGLE_AUTH_URI,
               token_uri=GOOGLE_TOKEN_URI,
               revoke_uri=GOOGLE_REVOKE_URI,
               user_agent=None,
               message=None,
               callback_path='/oauth2callback',
               token_response_param=None,
               _storage_class=StorageByKeyName,
               _credentials_class=CredentialsModel,
               _credentials_property_name='credentials',
               **kwargs):

    """Constructor for OAuth2Decorator

    Args:
      client_id: string, client identifier.
      client_secret: string client secret.
      scope: string or iterable of strings, scope(s) of the credentials being
        requested.
      auth_uri: string, URI for authorization endpoint. For convenience
        defaults to Google's endpoints but any OAuth 2.0 provider can be used.
      token_uri: string, URI for token endpoint. For convenience
        defaults to Google's endpoints but any OAuth 2.0 provider can be used.
      revoke_uri: string, URI for revoke endpoint. For convenience
        defaults to Google's endpoints but any OAuth 2.0 provider can be used.
      user_agent: string, User agent of your application, default to None.
      message: Message to display if there are problems with the OAuth 2.0
        configuration. The message may contain HTML and will be presented on the
        web interface for any method that uses the decorator.
      callback_path: string, The absolute path to use as the callback URI. Note
        that this must match up with the URI given when registering the
        application in the APIs Console.
      token_response_param: string. If provided, the full JSON response
        to the access token request will be encoded and included in this query
        parameter in the callback URI. This is useful with providers (e.g.
        wordpress.com) that include extra fields that the client may want.
      _storage_class: "Protected" keyword argument not typically provided to
        this constructor. A storage class to aid in storing a Credentials object
        for a user in the datastore. Defaults to StorageByKeyName.
      _credentials_class: "Protected" keyword argument not typically provided to
        this constructor. A db or ndb Model class to hold credentials. Defaults
        to CredentialsModel.
      _credentials_property_name: "Protected" keyword argument not typically
        provided to this constructor. A string indicating the name of the field
        on the _credentials_class where a Credentials object will be stored.
        Defaults to 'credentials'.
      **kwargs: dict, Keyword arguments are be passed along as kwargs to the
        OAuth2WebServerFlow constructor.
    """
    self._tls = threading.local()
    self.flow = None
    self.credentials = None
    self._client_id = client_id
    self._client_secret = client_secret
    self._scope = util.scopes_to_string(scope)
    self._auth_uri = auth_uri
    self._token_uri = token_uri
    self._revoke_uri = revoke_uri
    self._user_agent = user_agent
    self._kwargs = kwargs
    self._message = message
    self._in_error = False
    self._callback_path = callback_path
    self._token_response_param = token_response_param
    self._storage_class = _storage_class
    self._credentials_class = _credentials_class
    self._credentials_property_name = _credentials_property_name

  def _display_error_message(self, request_handler):
    request_handler.response.out.write('<html><body>')
    request_handler.response.out.write(_safe_html(self._message))
    request_handler.response.out.write('</body></html>')

  def oauth_required(self, method):
    """Decorator that starts the OAuth 2.0 dance.

    Starts the OAuth dance for the logged in user if they haven't already
    granted access for this application.

    Args:
      method: callable, to be decorated method of a webapp.RequestHandler
        instance.
    """

    def check_oauth(request_handler, *args, **kwargs):
      if self._in_error:
        self._display_error_message(request_handler)
        return

      user = users.get_current_user()
      # Don't use @login_decorator as this could be used in a POST request.
      if not user:
        request_handler.redirect(users.create_login_url(
            request_handler.request.uri))
        return

      self._create_flow(request_handler)

      # Store the request URI in 'state' so we can use it later
      self.flow.params['state'] = _build_state_value(request_handler, user)
      self.credentials = self._storage_class(
          self._credentials_class, None,
          self._credentials_property_name, user=user).get()

      if not self.has_credentials():
        return request_handler.redirect(self.authorize_url())
      try:
        resp = method(request_handler, *args, **kwargs)
      except AccessTokenRefreshError:
        return request_handler.redirect(self.authorize_url())
      finally:
        self.credentials = None
      return resp

    return check_oauth

  def _create_flow(self, request_handler):
    """Create the Flow object.

    The Flow is calculated lazily since we don't know where this app is
    running until it receives a request, at which point redirect_uri can be
    calculated and then the Flow object can be constructed.

    Args:
      request_handler: webapp.RequestHandler, the request handler.
    """
    if self.flow is None:
      redirect_uri = request_handler.request.relative_url(
          self._callback_path) # Usually /oauth2callback
      self.flow = OAuth2WebServerFlow(self._client_id, self._client_secret,
                                      self._scope, redirect_uri=redirect_uri,
                                      user_agent=self._user_agent,
                                      auth_uri=self._auth_uri,
                                      token_uri=self._token_uri,
                                      revoke_uri=self._revoke_uri,
                                      **self._kwargs)

  def oauth_aware(self, method):
    """Decorator that sets up for OAuth 2.0 dance, but doesn't do it.

    Does all the setup for the OAuth dance, but doesn't initiate it.
    This decorator is useful if you want to create a page that knows
    whether or not the user has granted access to this application.
    From within a method decorated with @oauth_aware the has_credentials()
    and authorize_url() methods can be called.

    Args:
      method: callable, to be decorated method of a webapp.RequestHandler
        instance.
    """

    def setup_oauth(request_handler, *args, **kwargs):
      if self._in_error:
        self._display_error_message(request_handler)
        return

      user = users.get_current_user()
      # Don't use @login_decorator as this could be used in a POST request.
      if not user:
        request_handler.redirect(users.create_login_url(
            request_handler.request.uri))
        return

      self._create_flow(request_handler)

      self.flow.params['state'] = _build_state_value(request_handler, user)
      self.credentials = self._storage_class(
          self._credentials_class, None,
          self._credentials_property_name, user=user).get()
      try:
        resp = method(request_handler, *args, **kwargs)
      finally:
        self.credentials = None
      return resp
    return setup_oauth


  def has_credentials(self):
    """True if for the logged in user there are valid access Credentials.

    Must only be called from with a webapp.RequestHandler subclassed method
    that had been decorated with either @oauth_required or @oauth_aware.
    """
    return self.credentials is not None and not self.credentials.invalid

  def authorize_url(self):
    """Returns the URL to start the OAuth dance.

    Must only be called from with a webapp.RequestHandler subclassed method
    that had been decorated with either @oauth_required or @oauth_aware.
    """
    url = self.flow.step1_get_authorize_url()
    return str(url)

  def http(self):
    """Returns an authorized http instance.

    Must only be called from within an @oauth_required decorated method, or
    from within an @oauth_aware decorated method where has_credentials()
    returns True.
    """
    return self.credentials.authorize(httplib2.Http())

  @property
  def callback_path(self):
    """The absolute path where the callback will occur.

    Note this is the absolute path, not the absolute URI, that will be
    calculated by the decorator at runtime. See callback_handler() for how this
    should be used.

    Returns:
      The callback path as a string.
    """
    return self._callback_path


  def callback_handler(self):
    """RequestHandler for the OAuth 2.0 redirect callback.

    Usage:
       app = webapp.WSGIApplication([
         ('/index', MyIndexHandler),
         ...,
         (decorator.callback_path, decorator.callback_handler())
       ])

    Returns:
      A webapp.RequestHandler that handles the redirect back from the
      server during the OAuth 2.0 dance.
    """
    decorator = self

    class OAuth2Handler(webapp.RequestHandler):
      """Handler for the redirect_uri of the OAuth 2.0 dance."""

      @login_required
      def get(self):
        error = self.request.get('error')
        if error:
          errormsg = self.request.get('error_description', error)
          self.response.out.write(
              'The authorization request failed: %s' % _safe_html(errormsg))
        else:
          user = users.get_current_user()
          decorator._create_flow(self)
          credentials = decorator.flow.step2_exchange(self.request.params)
          decorator._storage_class(
              decorator._credentials_class, None,
              decorator._credentials_property_name, user=user).put(credentials)
          redirect_uri = _parse_state_value(str(self.request.get('state')),
                                            user)

          if decorator._token_response_param and credentials.token_response:
            resp_json = simplejson.dumps(credentials.token_response)
            redirect_uri = util._add_query_parameter(
                redirect_uri, decorator._token_response_param, resp_json)

          self.redirect(redirect_uri)

    return OAuth2Handler

  def callback_application(self):
    """WSGI application for handling the OAuth 2.0 redirect callback.

    If you need finer grained control use `callback_handler` which returns just
    the webapp.RequestHandler.

    Returns:
      A webapp.WSGIApplication that handles the redirect back from the
      server during the OAuth 2.0 dance.
    """
    return webapp.WSGIApplication([
        (self.callback_path, self.callback_handler())
        ])


class OAuth2DecoratorFromClientSecrets(OAuth2Decorator):
  """An OAuth2Decorator that builds from a clientsecrets file.

  Uses a clientsecrets file as the source for all the information when
  constructing an OAuth2Decorator.

  Example:

    decorator = OAuth2DecoratorFromClientSecrets(
      os.path.join(os.path.dirname(__file__), 'client_secrets.json')
      scope='https://www.googleapis.com/auth/plus')


    class MainHandler(webapp.RequestHandler):

      @decorator.oauth_required
      def get(self):
        http = decorator.http()
        # http is authorized with the user's Credentials and can be used
        # in API calls
  """

  @util.positional(3)
  def __init__(self, filename, scope, message=None, cache=None):
    """Constructor

    Args:
      filename: string, File name of client secrets.
      scope: string or iterable of strings, scope(s) of the credentials being
        requested.
      message: string, A friendly string to display to the user if the
        clientsecrets file is missing or invalid. The message may contain HTML
        and will be presented on the web interface for any method that uses the
        decorator.
      cache: An optional cache service client that implements get() and set()
        methods. See clientsecrets.loadfile() for details.
    """
    client_type, client_info = clientsecrets.loadfile(filename, cache=cache)
    if client_type not in [
        clientsecrets.TYPE_WEB, clientsecrets.TYPE_INSTALLED]:
      raise InvalidClientSecretsError(
          'OAuth2Decorator doesn\'t support this OAuth 2.0 flow.')
    constructor_kwargs = {
      'auth_uri': client_info['auth_uri'],
      'token_uri': client_info['token_uri'],
      'message': message,
    }
    revoke_uri = client_info.get('revoke_uri')
    if revoke_uri is not None:
      constructor_kwargs['revoke_uri'] = revoke_uri
    super(OAuth2DecoratorFromClientSecrets, self).__init__(
        client_info['client_id'], client_info['client_secret'],
        scope, **constructor_kwargs)
    if message is not None:
      self._message = message
    else:
      self._message = 'Please configure your application for OAuth 2.0.'


@util.positional(2)
def oauth2decorator_from_clientsecrets(filename, scope,
                                       message=None, cache=None):
  """Creates an OAuth2Decorator populated from a clientsecrets file.

  Args:
    filename: string, File name of client secrets.
    scope: string or list of strings, scope(s) of the credentials being
      requested.
    message: string, A friendly string to display to the user if the
      clientsecrets file is missing or invalid. The message may contain HTML and
      will be presented on the web interface for any method that uses the
      decorator.
    cache: An optional cache service client that implements get() and set()
      methods. See clientsecrets.loadfile() for details.

  Returns: An OAuth2Decorator

  """
  return OAuth2DecoratorFromClientSecrets(filename, scope,
                                          message=message, cache=cache)

########NEW FILE########
__FILENAME__ = client
# Copyright (C) 2010 Google Inc.
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

"""An OAuth 2.0 client.

Tools for interacting with OAuth 2.0 protected resources.
"""

__author__ = 'jcgregorio@google.com (Joe Gregorio)'

import base64
import clientsecrets
import copy
import datetime
import httplib2
import logging
import os
import sys
import time
import urllib
import urlparse

from oauth2client import GOOGLE_AUTH_URI
from oauth2client import GOOGLE_REVOKE_URI
from oauth2client import GOOGLE_TOKEN_URI
from oauth2client import util
from oauth2client.anyjson import simplejson

HAS_OPENSSL = False
HAS_CRYPTO = False
try:
  from oauth2client import crypt
  HAS_CRYPTO = True
  if crypt.OpenSSLVerifier is not None:
    HAS_OPENSSL = True
except ImportError:
  pass

try:
  from urlparse import parse_qsl
except ImportError:
  from cgi import parse_qsl

logger = logging.getLogger(__name__)

# Expiry is stored in RFC3339 UTC format
EXPIRY_FORMAT = '%Y-%m-%dT%H:%M:%SZ'

# Which certs to use to validate id_tokens received.
ID_TOKEN_VERIFICATON_CERTS = 'https://www.googleapis.com/oauth2/v1/certs'

# Constant to use for the out of band OAuth 2.0 flow.
OOB_CALLBACK_URN = 'urn:ietf:wg:oauth:2.0:oob'

# Google Data client libraries may need to set this to [401, 403].
REFRESH_STATUS_CODES = [401]


class Error(Exception):
  """Base error for this module."""


class FlowExchangeError(Error):
  """Error trying to exchange an authorization grant for an access token."""


class AccessTokenRefreshError(Error):
  """Error trying to refresh an expired access token."""


class TokenRevokeError(Error):
  """Error trying to revoke a token."""


class UnknownClientSecretsFlowError(Error):
  """The client secrets file called for an unknown type of OAuth 2.0 flow. """


class AccessTokenCredentialsError(Error):
  """Having only the access_token means no refresh is possible."""


class VerifyJwtTokenError(Error):
  """Could on retrieve certificates for validation."""


class NonAsciiHeaderError(Error):
  """Header names and values must be ASCII strings."""


def _abstract():
  raise NotImplementedError('You need to override this function')


class MemoryCache(object):
  """httplib2 Cache implementation which only caches locally."""

  def __init__(self):
    self.cache = {}

  def get(self, key):
    return self.cache.get(key)

  def set(self, key, value):
    self.cache[key] = value

  def delete(self, key):
    self.cache.pop(key, None)


class Credentials(object):
  """Base class for all Credentials objects.

  Subclasses must define an authorize() method that applies the credentials to
  an HTTP transport.

  Subclasses must also specify a classmethod named 'from_json' that takes a JSON
  string as input and returns an instaniated Credentials object.
  """

  NON_SERIALIZED_MEMBERS = ['store']

  def authorize(self, http):
    """Take an httplib2.Http instance (or equivalent) and authorizes it.

    Authorizes it for the set of credentials, usually by replacing
    http.request() with a method that adds in the appropriate headers and then
    delegates to the original Http.request() method.

    Args:
      http: httplib2.Http, an http object to be used to make the refresh
        request.
    """
    _abstract()

  def refresh(self, http):
    """Forces a refresh of the access_token.

    Args:
      http: httplib2.Http, an http object to be used to make the refresh
        request.
    """
    _abstract()

  def revoke(self, http):
    """Revokes a refresh_token and makes the credentials void.

    Args:
      http: httplib2.Http, an http object to be used to make the revoke
        request.
    """
    _abstract()

  def apply(self, headers):
    """Add the authorization to the headers.

    Args:
      headers: dict, the headers to add the Authorization header to.
    """
    _abstract()

  def _to_json(self, strip):
    """Utility function that creates JSON repr. of a Credentials object.

    Args:
      strip: array, An array of names of members to not include in the JSON.

    Returns:
       string, a JSON representation of this instance, suitable to pass to
       from_json().
    """
    t = type(self)
    d = copy.copy(self.__dict__)
    for member in strip:
      if member in d:
        del d[member]
    if 'token_expiry' in d and isinstance(d['token_expiry'], datetime.datetime):
      d['token_expiry'] = d['token_expiry'].strftime(EXPIRY_FORMAT)
    # Add in information we will need later to reconsistitue this instance.
    d['_class'] = t.__name__
    d['_module'] = t.__module__
    return simplejson.dumps(d)

  def to_json(self):
    """Creating a JSON representation of an instance of Credentials.

    Returns:
       string, a JSON representation of this instance, suitable to pass to
       from_json().
    """
    return self._to_json(Credentials.NON_SERIALIZED_MEMBERS)

  @classmethod
  def new_from_json(cls, s):
    """Utility class method to instantiate a Credentials subclass from a JSON
    representation produced by to_json().

    Args:
      s: string, JSON from to_json().

    Returns:
      An instance of the subclass of Credentials that was serialized with
      to_json().
    """
    data = simplejson.loads(s)
    # Find and call the right classmethod from_json() to restore the object.
    module = data['_module']
    try:
      m = __import__(module)
    except ImportError:
      # In case there's an object from the old package structure, update it
      module = module.replace('.apiclient', '')
      m = __import__(module)

    m = __import__(module, fromlist=module.split('.')[:-1])
    kls = getattr(m, data['_class'])
    from_json = getattr(kls, 'from_json')
    return from_json(s)

  @classmethod
  def from_json(cls, s):
    """Instantiate a Credentials object from a JSON description of it.

    The JSON should have been produced by calling .to_json() on the object.

    Args:
      data: dict, A deserialized JSON object.

    Returns:
      An instance of a Credentials subclass.
    """
    return Credentials()


class Flow(object):
  """Base class for all Flow objects."""
  pass


class Storage(object):
  """Base class for all Storage objects.

  Store and retrieve a single credential. This class supports locking
  such that multiple processes and threads can operate on a single
  store.
  """

  def acquire_lock(self):
    """Acquires any lock necessary to access this Storage.

    This lock is not reentrant.
    """
    pass

  def release_lock(self):
    """Release the Storage lock.

    Trying to release a lock that isn't held will result in a
    RuntimeError.
    """
    pass

  def locked_get(self):
    """Retrieve credential.

    The Storage lock must be held when this is called.

    Returns:
      oauth2client.client.Credentials
    """
    _abstract()

  def locked_put(self, credentials):
    """Write a credential.

    The Storage lock must be held when this is called.

    Args:
      credentials: Credentials, the credentials to store.
    """
    _abstract()

  def locked_delete(self):
    """Delete a credential.

    The Storage lock must be held when this is called.
    """
    _abstract()

  def get(self):
    """Retrieve credential.

    The Storage lock must *not* be held when this is called.

    Returns:
      oauth2client.client.Credentials
    """
    self.acquire_lock()
    try:
      return self.locked_get()
    finally:
      self.release_lock()

  def put(self, credentials):
    """Write a credential.

    The Storage lock must be held when this is called.

    Args:
      credentials: Credentials, the credentials to store.
    """
    self.acquire_lock()
    try:
      self.locked_put(credentials)
    finally:
      self.release_lock()

  def delete(self):
    """Delete credential.

    Frees any resources associated with storing the credential.
    The Storage lock must *not* be held when this is called.

    Returns:
      None
    """
    self.acquire_lock()
    try:
      return self.locked_delete()
    finally:
      self.release_lock()


def clean_headers(headers):
  """Forces header keys and values to be strings, i.e not unicode.

  The httplib module just concats the header keys and values in a way that may
  make the message header a unicode string, which, if it then tries to
  contatenate to a binary request body may result in a unicode decode error.

  Args:
    headers: dict, A dictionary of headers.

  Returns:
    The same dictionary but with all the keys converted to strings.
  """
  clean = {}
  try:
    for k, v in headers.iteritems():
      clean[str(k)] = str(v)
  except UnicodeEncodeError:
    raise NonAsciiHeaderError(k + ': ' + v)
  return clean


def _update_query_params(uri, params):
  """Updates a URI with new query parameters.

  Args:
    uri: string, A valid URI, with potential existing query parameters.
    params: dict, A dictionary of query parameters.

  Returns:
    The same URI but with the new query parameters added.
  """
  parts = list(urlparse.urlparse(uri))
  query_params = dict(parse_qsl(parts[4])) # 4 is the index of the query part
  query_params.update(params)
  parts[4] = urllib.urlencode(query_params)
  return urlparse.urlunparse(parts)


class OAuth2Credentials(Credentials):
  """Credentials object for OAuth 2.0.

  Credentials can be applied to an httplib2.Http object using the authorize()
  method, which then adds the OAuth 2.0 access token to each request.

  OAuth2Credentials objects may be safely pickled and unpickled.
  """

  @util.positional(8)
  def __init__(self, access_token, client_id, client_secret, refresh_token,
               token_expiry, token_uri, user_agent, revoke_uri=None,
               id_token=None, token_response=None):
    """Create an instance of OAuth2Credentials.

    This constructor is not usually called by the user, instead
    OAuth2Credentials objects are instantiated by the OAuth2WebServerFlow.

    Args:
      access_token: string, access token.
      client_id: string, client identifier.
      client_secret: string, client secret.
      refresh_token: string, refresh token.
      token_expiry: datetime, when the access_token expires.
      token_uri: string, URI of token endpoint.
      user_agent: string, The HTTP User-Agent to provide for this application.
      revoke_uri: string, URI for revoke endpoint. Defaults to None; a token
        can't be revoked if this is None.
      id_token: object, The identity of the resource owner.
      token_response: dict, the decoded response to the token request. None
        if a token hasn't been requested yet. Stored because some providers
        (e.g. wordpress.com) include extra fields that clients may want.

    Notes:
      store: callable, A callable that when passed a Credential
        will store the credential back to where it came from.
        This is needed to store the latest access_token if it
        has expired and been refreshed.
    """
    self.access_token = access_token
    self.client_id = client_id
    self.client_secret = client_secret
    self.refresh_token = refresh_token
    self.store = None
    self.token_expiry = token_expiry
    self.token_uri = token_uri
    self.user_agent = user_agent
    self.revoke_uri = revoke_uri
    self.id_token = id_token
    self.token_response = token_response

    # True if the credentials have been revoked or expired and can't be
    # refreshed.
    self.invalid = False

  def authorize(self, http):
    """Authorize an httplib2.Http instance with these credentials.

    The modified http.request method will add authentication headers to each
    request and will refresh access_tokens when a 401 is received on a
    request. In addition the http.request method has a credentials property,
    http.request.credentials, which is the Credentials object that authorized
    it.

    Args:
       http: An instance of httplib2.Http
         or something that acts like it.

    Returns:
       A modified instance of http that was passed in.

    Example:

      h = httplib2.Http()
      h = credentials.authorize(h)

    You can't create a new OAuth subclass of httplib2.Authenication
    because it never gets passed the absolute URI, which is needed for
    signing. So instead we have to overload 'request' with a closure
    that adds in the Authorization header and then calls the original
    version of 'request()'.
    """
    request_orig = http.request

    # The closure that will replace 'httplib2.Http.request'.
    @util.positional(1)
    def new_request(uri, method='GET', body=None, headers=None,
                    redirections=httplib2.DEFAULT_MAX_REDIRECTS,
                    connection_type=None):
      if not self.access_token:
        logger.info('Attempting refresh to obtain initial access_token')
        self._refresh(request_orig)

      # Modify the request headers to add the appropriate
      # Authorization header.
      if headers is None:
        headers = {}
      self.apply(headers)

      if self.user_agent is not None:
        if 'user-agent' in headers:
          headers['user-agent'] = self.user_agent + ' ' + headers['user-agent']
        else:
          headers['user-agent'] = self.user_agent

      resp, content = request_orig(uri, method, body, clean_headers(headers),
                                   redirections, connection_type)

      if resp.status in REFRESH_STATUS_CODES:
        logger.info('Refreshing due to a %s' % str(resp.status))
        self._refresh(request_orig)
        self.apply(headers)
        return request_orig(uri, method, body, clean_headers(headers),
                            redirections, connection_type)
      else:
        return (resp, content)

    # Replace the request method with our own closure.
    http.request = new_request

    # Set credentials as a property of the request method.
    setattr(http.request, 'credentials', self)

    return http

  def refresh(self, http):
    """Forces a refresh of the access_token.

    Args:
      http: httplib2.Http, an http object to be used to make the refresh
        request.
    """
    self._refresh(http.request)

  def revoke(self, http):
    """Revokes a refresh_token and makes the credentials void.

    Args:
      http: httplib2.Http, an http object to be used to make the revoke
        request.
    """
    self._revoke(http.request)

  def apply(self, headers):
    """Add the authorization to the headers.

    Args:
      headers: dict, the headers to add the Authorization header to.
    """
    headers['Authorization'] = 'Bearer ' + self.access_token

  def to_json(self):
    return self._to_json(Credentials.NON_SERIALIZED_MEMBERS)

  @classmethod
  def from_json(cls, s):
    """Instantiate a Credentials object from a JSON description of it. The JSON
    should have been produced by calling .to_json() on the object.

    Args:
      data: dict, A deserialized JSON object.

    Returns:
      An instance of a Credentials subclass.
    """
    data = simplejson.loads(s)
    if 'token_expiry' in data and not isinstance(data['token_expiry'],
        datetime.datetime):
      try:
        data['token_expiry'] = datetime.datetime.strptime(
            data['token_expiry'], EXPIRY_FORMAT)
      except:
        data['token_expiry'] = None
    retval = cls(
        data['access_token'],
        data['client_id'],
        data['client_secret'],
        data['refresh_token'],
        data['token_expiry'],
        data['token_uri'],
        data['user_agent'],
        revoke_uri=data.get('revoke_uri', None),
        id_token=data.get('id_token', None),
        token_response=data.get('token_response', None))
    retval.invalid = data['invalid']
    return retval

  @property
  def access_token_expired(self):
    """True if the credential is expired or invalid.

    If the token_expiry isn't set, we assume the token doesn't expire.
    """
    if self.invalid:
      return True

    if not self.token_expiry:
      return False

    now = datetime.datetime.utcnow()
    if now >= self.token_expiry:
      logger.info('access_token is expired. Now: %s, token_expiry: %s',
                  now, self.token_expiry)
      return True
    return False

  def set_store(self, store):
    """Set the Storage for the credential.

    Args:
      store: Storage, an implementation of Stroage object.
        This is needed to store the latest access_token if it
        has expired and been refreshed. This implementation uses
        locking to check for updates before updating the
        access_token.
    """
    self.store = store

  def _updateFromCredential(self, other):
    """Update this Credential from another instance."""
    self.__dict__.update(other.__getstate__())

  def __getstate__(self):
    """Trim the state down to something that can be pickled."""
    d = copy.copy(self.__dict__)
    del d['store']
    return d

  def __setstate__(self, state):
    """Reconstitute the state of the object from being pickled."""
    self.__dict__.update(state)
    self.store = None

  def _generate_refresh_request_body(self):
    """Generate the body that will be used in the refresh request."""
    body = urllib.urlencode({
        'grant_type': 'refresh_token',
        'client_id': self.client_id,
        'client_secret': self.client_secret,
        'refresh_token': self.refresh_token,
        })
    return body

  def _generate_refresh_request_headers(self):
    """Generate the headers that will be used in the refresh request."""
    headers = {
        'content-type': 'application/x-www-form-urlencoded',
    }

    if self.user_agent is not None:
      headers['user-agent'] = self.user_agent

    return headers

  def _refresh(self, http_request):
    """Refreshes the access_token.

    This method first checks by reading the Storage object if available.
    If a refresh is still needed, it holds the Storage lock until the
    refresh is completed.

    Args:
      http_request: callable, a callable that matches the method signature of
        httplib2.Http.request, used to make the refresh request.

    Raises:
      AccessTokenRefreshError: When the refresh fails.
    """
    if not self.store:
      self._do_refresh_request(http_request)
    else:
      self.store.acquire_lock()
      try:
        new_cred = self.store.locked_get()
        if (new_cred and not new_cred.invalid and
            new_cred.access_token != self.access_token):
          logger.info('Updated access_token read from Storage')
          self._updateFromCredential(new_cred)
        else:
          self._do_refresh_request(http_request)
      finally:
        self.store.release_lock()

  def _do_refresh_request(self, http_request):
    """Refresh the access_token using the refresh_token.

    Args:
      http_request: callable, a callable that matches the method signature of
        httplib2.Http.request, used to make the refresh request.

    Raises:
      AccessTokenRefreshError: When the refresh fails.
    """
    body = self._generate_refresh_request_body()
    headers = self._generate_refresh_request_headers()

    logger.info('Refreshing access_token')
    resp, content = http_request(
        self.token_uri, method='POST', body=body, headers=headers)
    if resp.status == 200:
      # TODO(jcgregorio) Raise an error if loads fails?
      d = simplejson.loads(content)
      self.token_response = d
      self.access_token = d['access_token']
      self.refresh_token = d.get('refresh_token', self.refresh_token)
      if 'expires_in' in d:
        self.token_expiry = datetime.timedelta(
            seconds=int(d['expires_in'])) + datetime.datetime.utcnow()
      else:
        self.token_expiry = None
      if self.store:
        self.store.locked_put(self)
    else:
      # An {'error':...} response body means the token is expired or revoked,
      # so we flag the credentials as such.
      logger.info('Failed to retrieve access token: %s' % content)
      error_msg = 'Invalid response %s.' % resp['status']
      try:
        d = simplejson.loads(content)
        if 'error' in d:
          error_msg = d['error']
          self.invalid = True
          if self.store:
            self.store.locked_put(self)
      except StandardError:
        pass
      raise AccessTokenRefreshError(error_msg)

  def _revoke(self, http_request):
    """Revokes the refresh_token and deletes the store if available.

    Args:
      http_request: callable, a callable that matches the method signature of
        httplib2.Http.request, used to make the revoke request.
    """
    self._do_revoke(http_request, self.refresh_token)

  def _do_revoke(self, http_request, token):
    """Revokes the credentials and deletes the store if available.

    Args:
      http_request: callable, a callable that matches the method signature of
        httplib2.Http.request, used to make the refresh request.
      token: A string used as the token to be revoked. Can be either an
        access_token or refresh_token.

    Raises:
      TokenRevokeError: If the revoke request does not return with a 200 OK.
    """
    logger.info('Revoking token')
    query_params = {'token': token}
    token_revoke_uri = _update_query_params(self.revoke_uri, query_params)
    resp, content = http_request(token_revoke_uri)
    if resp.status == 200:
      self.invalid = True
    else:
      error_msg = 'Invalid response %s.' % resp.status
      try:
        d = simplejson.loads(content)
        if 'error' in d:
          error_msg = d['error']
      except StandardError:
        pass
      raise TokenRevokeError(error_msg)

    if self.store:
      self.store.delete()


class AccessTokenCredentials(OAuth2Credentials):
  """Credentials object for OAuth 2.0.

  Credentials can be applied to an httplib2.Http object using the
  authorize() method, which then signs each request from that object
  with the OAuth 2.0 access token. This set of credentials is for the
  use case where you have acquired an OAuth 2.0 access_token from
  another place such as a JavaScript client or another web
  application, and wish to use it from Python. Because only the
  access_token is present it can not be refreshed and will in time
  expire.

  AccessTokenCredentials objects may be safely pickled and unpickled.

  Usage:
    credentials = AccessTokenCredentials('<an access token>',
      'my-user-agent/1.0')
    http = httplib2.Http()
    http = credentials.authorize(http)

  Exceptions:
    AccessTokenCredentialsExpired: raised when the access_token expires or is
      revoked.
  """

  def __init__(self, access_token, user_agent, revoke_uri=None):
    """Create an instance of OAuth2Credentials

    This is one of the few types if Credentials that you should contrust,
    Credentials objects are usually instantiated by a Flow.

    Args:
      access_token: string, access token.
      user_agent: string, The HTTP User-Agent to provide for this application.
      revoke_uri: string, URI for revoke endpoint. Defaults to None; a token
        can't be revoked if this is None.
    """
    super(AccessTokenCredentials, self).__init__(
        access_token,
        None,
        None,
        None,
        None,
        None,
        user_agent,
        revoke_uri=revoke_uri)


  @classmethod
  def from_json(cls, s):
    data = simplejson.loads(s)
    retval = AccessTokenCredentials(
        data['access_token'],
        data['user_agent'])
    return retval

  def _refresh(self, http_request):
    raise AccessTokenCredentialsError(
        'The access_token is expired or invalid and can\'t be refreshed.')

  def _revoke(self, http_request):
    """Revokes the access_token and deletes the store if available.

    Args:
      http_request: callable, a callable that matches the method signature of
        httplib2.Http.request, used to make the revoke request.
    """
    self._do_revoke(http_request, self.access_token)


class AssertionCredentials(OAuth2Credentials):
  """Abstract Credentials object used for OAuth 2.0 assertion grants.

  This credential does not require a flow to instantiate because it
  represents a two legged flow, and therefore has all of the required
  information to generate and refresh its own access tokens. It must
  be subclassed to generate the appropriate assertion string.

  AssertionCredentials objects may be safely pickled and unpickled.
  """

  @util.positional(2)
  def __init__(self, assertion_type, user_agent=None,
               token_uri=GOOGLE_TOKEN_URI,
               revoke_uri=GOOGLE_REVOKE_URI,
               **unused_kwargs):
    """Constructor for AssertionFlowCredentials.

    Args:
      assertion_type: string, assertion type that will be declared to the auth
        server
      user_agent: string, The HTTP User-Agent to provide for this application.
      token_uri: string, URI for token endpoint. For convenience
        defaults to Google's endpoints but any OAuth 2.0 provider can be used.
      revoke_uri: string, URI for revoke endpoint.
    """
    super(AssertionCredentials, self).__init__(
        None,
        None,
        None,
        None,
        None,
        token_uri,
        user_agent,
        revoke_uri=revoke_uri)
    self.assertion_type = assertion_type

  def _generate_refresh_request_body(self):
    assertion = self._generate_assertion()

    body = urllib.urlencode({
        'assertion': assertion,
        'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
        })

    return body

  def _generate_assertion(self):
    """Generate the assertion string that will be used in the access token
    request.
    """
    _abstract()

  def _revoke(self, http_request):
    """Revokes the access_token and deletes the store if available.

    Args:
      http_request: callable, a callable that matches the method signature of
        httplib2.Http.request, used to make the revoke request.
    """
    self._do_revoke(http_request, self.access_token)


if HAS_CRYPTO:
  # PyOpenSSL and PyCrypto are not prerequisites for oauth2client, so if it is
  # missing then don't create the SignedJwtAssertionCredentials or the
  # verify_id_token() method.

  class SignedJwtAssertionCredentials(AssertionCredentials):
    """Credentials object used for OAuth 2.0 Signed JWT assertion grants.

    This credential does not require a flow to instantiate because it represents
    a two legged flow, and therefore has all of the required information to
    generate and refresh its own access tokens.

    SignedJwtAssertionCredentials requires either PyOpenSSL, or PyCrypto 2.6 or
    later. For App Engine you may also consider using AppAssertionCredentials.
    """

    MAX_TOKEN_LIFETIME_SECS = 3600 # 1 hour in seconds

    @util.positional(4)
    def __init__(self,
        service_account_name,
        private_key,
        scope,
        private_key_password='notasecret',
        user_agent=None,
        token_uri=GOOGLE_TOKEN_URI,
        revoke_uri=GOOGLE_REVOKE_URI,
        **kwargs):
      """Constructor for SignedJwtAssertionCredentials.

      Args:
        service_account_name: string, id for account, usually an email address.
        private_key: string, private key in PKCS12 or PEM format.
        scope: string or iterable of strings, scope(s) of the credentials being
          requested.
        private_key_password: string, password for private_key, unused if
          private_key is in PEM format.
        user_agent: string, HTTP User-Agent to provide for this application.
        token_uri: string, URI for token endpoint. For convenience
          defaults to Google's endpoints but any OAuth 2.0 provider can be used.
        revoke_uri: string, URI for revoke endpoint.
        kwargs: kwargs, Additional parameters to add to the JWT token, for
          example sub=joe@xample.org."""

      super(SignedJwtAssertionCredentials, self).__init__(
          None,
          user_agent=user_agent,
          token_uri=token_uri,
          revoke_uri=revoke_uri,
          )

      self.scope = util.scopes_to_string(scope)

      # Keep base64 encoded so it can be stored in JSON.
      self.private_key = base64.b64encode(private_key)

      self.private_key_password = private_key_password
      self.service_account_name = service_account_name
      self.kwargs = kwargs

    @classmethod
    def from_json(cls, s):
      data = simplejson.loads(s)
      retval = SignedJwtAssertionCredentials(
          data['service_account_name'],
          base64.b64decode(data['private_key']),
          data['scope'],
          private_key_password=data['private_key_password'],
          user_agent=data['user_agent'],
          token_uri=data['token_uri'],
          **data['kwargs']
          )
      retval.invalid = data['invalid']
      retval.access_token = data['access_token']
      return retval

    def _generate_assertion(self):
      """Generate the assertion that will be used in the request."""
      now = long(time.time())
      payload = {
          'aud': self.token_uri,
          'scope': self.scope,
          'iat': now,
          'exp': now + SignedJwtAssertionCredentials.MAX_TOKEN_LIFETIME_SECS,
          'iss': self.service_account_name
      }
      payload.update(self.kwargs)
      logger.debug(str(payload))

      private_key = base64.b64decode(self.private_key)
      return crypt.make_signed_jwt(crypt.Signer.from_string(
          private_key, self.private_key_password), payload)

  # Only used in verify_id_token(), which is always calling to the same URI
  # for the certs.
  _cached_http = httplib2.Http(MemoryCache())

  @util.positional(2)
  def verify_id_token(id_token, audience, http=None,
      cert_uri=ID_TOKEN_VERIFICATON_CERTS):
    """Verifies a signed JWT id_token.

    This function requires PyOpenSSL and because of that it does not work on
    App Engine.

    Args:
      id_token: string, A Signed JWT.
      audience: string, The audience 'aud' that the token should be for.
      http: httplib2.Http, instance to use to make the HTTP request. Callers
        should supply an instance that has caching enabled.
      cert_uri: string, URI of the certificates in JSON format to
        verify the JWT against.

    Returns:
      The deserialized JSON in the JWT.

    Raises:
      oauth2client.crypt.AppIdentityError if the JWT fails to verify.
    """
    if http is None:
      http = _cached_http

    resp, content = http.request(cert_uri)

    if resp.status == 200:
      certs = simplejson.loads(content)
      return crypt.verify_signed_jwt_with_certs(id_token, certs, audience)
    else:
      raise VerifyJwtTokenError('Status code: %d' % resp.status)


def _urlsafe_b64decode(b64string):
  # Guard against unicode strings, which base64 can't handle.
  b64string = b64string.encode('ascii')
  padded = b64string + '=' * (4 - len(b64string) % 4)
  return base64.urlsafe_b64decode(padded)


def _extract_id_token(id_token):
  """Extract the JSON payload from a JWT.

  Does the extraction w/o checking the signature.

  Args:
    id_token: string, OAuth 2.0 id_token.

  Returns:
    object, The deserialized JSON payload.
  """
  segments = id_token.split('.')

  if (len(segments) != 3):
    raise VerifyJwtTokenError(
      'Wrong number of segments in token: %s' % id_token)

  return simplejson.loads(_urlsafe_b64decode(segments[1]))


def _parse_exchange_token_response(content):
  """Parses response of an exchange token request.

  Most providers return JSON but some (e.g. Facebook) return a
  url-encoded string.

  Args:
    content: The body of a response

  Returns:
    Content as a dictionary object. Note that the dict could be empty,
    i.e. {}. That basically indicates a failure.
  """
  resp = {}
  try:
    resp = simplejson.loads(content)
  except StandardError:
    # different JSON libs raise different exceptions,
    # so we just do a catch-all here
    resp = dict(parse_qsl(content))

  # some providers respond with 'expires', others with 'expires_in'
  if resp and 'expires' in resp:
    resp['expires_in'] = resp.pop('expires')

  return resp


@util.positional(4)
def credentials_from_code(client_id, client_secret, scope, code,
                          redirect_uri='postmessage', http=None,
                          user_agent=None, token_uri=GOOGLE_TOKEN_URI,
                          auth_uri=GOOGLE_AUTH_URI,
                          revoke_uri=GOOGLE_REVOKE_URI):
  """Exchanges an authorization code for an OAuth2Credentials object.

  Args:
    client_id: string, client identifier.
    client_secret: string, client secret.
    scope: string or iterable of strings, scope(s) to request.
    code: string, An authroization code, most likely passed down from
      the client
    redirect_uri: string, this is generally set to 'postmessage' to match the
      redirect_uri that the client specified
    http: httplib2.Http, optional http instance to use to do the fetch
    token_uri: string, URI for token endpoint. For convenience
      defaults to Google's endpoints but any OAuth 2.0 provider can be used.
    auth_uri: string, URI for authorization endpoint. For convenience
      defaults to Google's endpoints but any OAuth 2.0 provider can be used.
    revoke_uri: string, URI for revoke endpoint. For convenience
      defaults to Google's endpoints but any OAuth 2.0 provider can be used.

  Returns:
    An OAuth2Credentials object.

  Raises:
    FlowExchangeError if the authorization code cannot be exchanged for an
     access token
  """
  flow = OAuth2WebServerFlow(client_id, client_secret, scope,
                             redirect_uri=redirect_uri, user_agent=user_agent,
                             auth_uri=auth_uri, token_uri=token_uri,
                             revoke_uri=revoke_uri)

  credentials = flow.step2_exchange(code, http=http)
  return credentials


@util.positional(3)
def credentials_from_clientsecrets_and_code(filename, scope, code,
                                            message = None,
                                            redirect_uri='postmessage',
                                            http=None,
                                            cache=None):
  """Returns OAuth2Credentials from a clientsecrets file and an auth code.

  Will create the right kind of Flow based on the contents of the clientsecrets
  file or will raise InvalidClientSecretsError for unknown types of Flows.

  Args:
    filename: string, File name of clientsecrets.
    scope: string or iterable of strings, scope(s) to request.
    code: string, An authorization code, most likely passed down from
      the client
    message: string, A friendly string to display to the user if the
      clientsecrets file is missing or invalid. If message is provided then
      sys.exit will be called in the case of an error. If message in not
      provided then clientsecrets.InvalidClientSecretsError will be raised.
    redirect_uri: string, this is generally set to 'postmessage' to match the
      redirect_uri that the client specified
    http: httplib2.Http, optional http instance to use to do the fetch
    cache: An optional cache service client that implements get() and set()
      methods. See clientsecrets.loadfile() for details.

  Returns:
    An OAuth2Credentials object.

  Raises:
    FlowExchangeError if the authorization code cannot be exchanged for an
     access token
    UnknownClientSecretsFlowError if the file describes an unknown kind of Flow.
    clientsecrets.InvalidClientSecretsError if the clientsecrets file is
      invalid.
  """
  flow = flow_from_clientsecrets(filename, scope, message=message, cache=cache,
                                 redirect_uri=redirect_uri)
  credentials = flow.step2_exchange(code, http=http)
  return credentials


class OAuth2WebServerFlow(Flow):
  """Does the Web Server Flow for OAuth 2.0.

  OAuth2WebServerFlow objects may be safely pickled and unpickled.
  """

  @util.positional(4)
  def __init__(self, client_id, client_secret, scope,
               redirect_uri=None,
               user_agent=None,
               auth_uri=GOOGLE_AUTH_URI,
               token_uri=GOOGLE_TOKEN_URI,
               revoke_uri=GOOGLE_REVOKE_URI,
               **kwargs):
    """Constructor for OAuth2WebServerFlow.

    The kwargs argument is used to set extra query parameters on the
    auth_uri. For example, the access_type and approval_prompt
    query parameters can be set via kwargs.

    Args:
      client_id: string, client identifier.
      client_secret: string client secret.
      scope: string or iterable of strings, scope(s) of the credentials being
        requested.
      redirect_uri: string, Either the string 'urn:ietf:wg:oauth:2.0:oob' for
        a non-web-based application, or a URI that handles the callback from
        the authorization server.
      user_agent: string, HTTP User-Agent to provide for this application.
      auth_uri: string, URI for authorization endpoint. For convenience
        defaults to Google's endpoints but any OAuth 2.0 provider can be used.
      token_uri: string, URI for token endpoint. For convenience
        defaults to Google's endpoints but any OAuth 2.0 provider can be used.
      revoke_uri: string, URI for revoke endpoint. For convenience
        defaults to Google's endpoints but any OAuth 2.0 provider can be used.
      **kwargs: dict, The keyword arguments are all optional and required
                        parameters for the OAuth calls.
    """
    self.client_id = client_id
    self.client_secret = client_secret
    self.scope = util.scopes_to_string(scope)
    self.redirect_uri = redirect_uri
    self.user_agent = user_agent
    self.auth_uri = auth_uri
    self.token_uri = token_uri
    self.revoke_uri = revoke_uri
    self.params = {
        'access_type': 'offline',
        'response_type': 'code',
    }
    self.params.update(kwargs)

  @util.positional(1)
  def step1_get_authorize_url(self, redirect_uri=None):
    """Returns a URI to redirect to the provider.

    Args:
      redirect_uri: string, Either the string 'urn:ietf:wg:oauth:2.0:oob' for
        a non-web-based application, or a URI that handles the callback from
        the authorization server. This parameter is deprecated, please move to
        passing the redirect_uri in via the constructor.

    Returns:
      A URI as a string to redirect the user to begin the authorization flow.
    """
    if redirect_uri is not None:
      logger.warning(('The redirect_uri parameter for'
          'OAuth2WebServerFlow.step1_get_authorize_url is deprecated. Please'
          'move to passing the redirect_uri in via the constructor.'))
      self.redirect_uri = redirect_uri

    if self.redirect_uri is None:
      raise ValueError('The value of redirect_uri must not be None.')

    query_params = {
        'client_id': self.client_id,
        'redirect_uri': self.redirect_uri,
        'scope': self.scope,
    }
    query_params.update(self.params)
    return _update_query_params(self.auth_uri, query_params)

  @util.positional(2)
  def step2_exchange(self, code, http=None):
    """Exhanges a code for OAuth2Credentials.

    Args:
      code: string or dict, either the code as a string, or a dictionary
        of the query parameters to the redirect_uri, which contains
        the code.
      http: httplib2.Http, optional http instance to use to do the fetch

    Returns:
      An OAuth2Credentials object that can be used to authorize requests.

    Raises:
      FlowExchangeError if a problem occured exchanging the code for a
      refresh_token.
    """

    if not (isinstance(code, str) or isinstance(code, unicode)):
      if 'code' not in code:
        if 'error' in code:
          error_msg = code['error']
        else:
          error_msg = 'No code was supplied in the query parameters.'
        raise FlowExchangeError(error_msg)
      else:
        code = code['code']

    body = urllib.urlencode({
        'grant_type': 'authorization_code',
        'client_id': self.client_id,
        'client_secret': self.client_secret,
        'code': code,
        'redirect_uri': self.redirect_uri,
        'scope': self.scope,
        })
    headers = {
        'content-type': 'application/x-www-form-urlencoded',
    }

    if self.user_agent is not None:
      headers['user-agent'] = self.user_agent

    if http is None:
      http = httplib2.Http()

    resp, content = http.request(self.token_uri, method='POST', body=body,
                                 headers=headers)
    d = _parse_exchange_token_response(content)
    if resp.status == 200 and 'access_token' in d:
      access_token = d['access_token']
      refresh_token = d.get('refresh_token', None)
      token_expiry = None
      if 'expires_in' in d:
        token_expiry = datetime.datetime.utcnow() + datetime.timedelta(
            seconds=int(d['expires_in']))

      if 'id_token' in d:
        d['id_token'] = _extract_id_token(d['id_token'])

      logger.info('Successfully retrieved access token')
      return OAuth2Credentials(access_token, self.client_id,
                               self.client_secret, refresh_token, token_expiry,
                               self.token_uri, self.user_agent,
                               revoke_uri=self.revoke_uri,
                               id_token=d.get('id_token', None),
                               token_response=d)
    else:
      logger.info('Failed to retrieve access token: %s' % content)
      if 'error' in d:
        # you never know what those providers got to say
        error_msg = unicode(d['error'])
      else:
        error_msg = 'Invalid response: %s.' % str(resp.status)
      raise FlowExchangeError(error_msg)


@util.positional(2)
def flow_from_clientsecrets(filename, scope, redirect_uri=None,
                            message=None, cache=None):
  """Create a Flow from a clientsecrets file.

  Will create the right kind of Flow based on the contents of the clientsecrets
  file or will raise InvalidClientSecretsError for unknown types of Flows.

  Args:
    filename: string, File name of client secrets.
    scope: string or iterable of strings, scope(s) to request.
    redirect_uri: string, Either the string 'urn:ietf:wg:oauth:2.0:oob' for
      a non-web-based application, or a URI that handles the callback from
      the authorization server.
    message: string, A friendly string to display to the user if the
      clientsecrets file is missing or invalid. If message is provided then
      sys.exit will be called in the case of an error. If message in not
      provided then clientsecrets.InvalidClientSecretsError will be raised.
    cache: An optional cache service client that implements get() and set()
      methods. See clientsecrets.loadfile() for details.

  Returns:
    A Flow object.

  Raises:
    UnknownClientSecretsFlowError if the file describes an unknown kind of Flow.
    clientsecrets.InvalidClientSecretsError if the clientsecrets file is
      invalid.
  """
  try:
    client_type, client_info = clientsecrets.loadfile(filename, cache=cache)
    if client_type in (clientsecrets.TYPE_WEB, clientsecrets.TYPE_INSTALLED):
      constructor_kwargs = {
          'redirect_uri': redirect_uri,
          'auth_uri': client_info['auth_uri'],
          'token_uri': client_info['token_uri'],
      }
      revoke_uri = client_info.get('revoke_uri')
      if revoke_uri is not None:
        constructor_kwargs['revoke_uri'] = revoke_uri
      return OAuth2WebServerFlow(
          client_info['client_id'], client_info['client_secret'],
          scope, **constructor_kwargs)

  except clientsecrets.InvalidClientSecretsError:
    if message:
      sys.exit(message)
    else:
      raise
  else:
    raise UnknownClientSecretsFlowError(
        'This OAuth 2.0 flow is unsupported: %r' % client_type)

########NEW FILE########
__FILENAME__ = clientsecrets
# Copyright (C) 2011 Google Inc.
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

"""Utilities for reading OAuth 2.0 client secret files.

A client_secrets.json file contains all the information needed to interact with
an OAuth 2.0 protected service.
"""

__author__ = 'jcgregorio@google.com (Joe Gregorio)'


from anyjson import simplejson

# Properties that make a client_secrets.json file valid.
TYPE_WEB = 'web'
TYPE_INSTALLED = 'installed'

VALID_CLIENT = {
    TYPE_WEB: {
        'required': [
            'client_id',
            'client_secret',
            'redirect_uris',
            'auth_uri',
            'token_uri',
        ],
        'string': [
            'client_id',
            'client_secret',
        ],
    },
    TYPE_INSTALLED: {
        'required': [
            'client_id',
            'client_secret',
            'redirect_uris',
            'auth_uri',
            'token_uri',
        ],
        'string': [
            'client_id',
            'client_secret',
        ],
    },
}


class Error(Exception):
  """Base error for this module."""
  pass


class InvalidClientSecretsError(Error):
  """Format of ClientSecrets file is invalid."""
  pass


def _validate_clientsecrets(obj):
  if obj is None or len(obj) != 1:
    raise InvalidClientSecretsError('Invalid file format.')
  client_type = obj.keys()[0]
  if client_type not in VALID_CLIENT.keys():
    raise InvalidClientSecretsError('Unknown client type: %s.' % client_type)
  client_info = obj[client_type]
  for prop_name in VALID_CLIENT[client_type]['required']:
    if prop_name not in client_info:
      raise InvalidClientSecretsError(
        'Missing property "%s" in a client type of "%s".' % (prop_name,
                                                           client_type))
  for prop_name in VALID_CLIENT[client_type]['string']:
    if client_info[prop_name].startswith('[['):
      raise InvalidClientSecretsError(
        'Property "%s" is not configured.' % prop_name)
  return client_type, client_info


def load(fp):
  obj = simplejson.load(fp)
  return _validate_clientsecrets(obj)


def loads(s):
  obj = simplejson.loads(s)
  return _validate_clientsecrets(obj)


def _loadfile(filename):
  try:
    fp = file(filename, 'r')
    try:
      obj = simplejson.load(fp)
    finally:
      fp.close()
  except IOError:
    raise InvalidClientSecretsError('File not found: "%s"' % filename)
  return _validate_clientsecrets(obj)


def loadfile(filename, cache=None):
  """Loading of client_secrets JSON file, optionally backed by a cache.

  Typical cache storage would be App Engine memcache service,
  but you can pass in any other cache client that implements
  these methods:
    - get(key, namespace=ns)
    - set(key, value, namespace=ns)

  Usage:
    # without caching
    client_type, client_info = loadfile('secrets.json')
    # using App Engine memcache service
    from google.appengine.api import memcache
    client_type, client_info = loadfile('secrets.json', cache=memcache)

  Args:
    filename: string, Path to a client_secrets.json file on a filesystem.
    cache: An optional cache service client that implements get() and set()
      methods. If not specified, the file is always being loaded from
      a filesystem.

  Raises:
    InvalidClientSecretsError: In case of a validation error or some
      I/O failure. Can happen only on cache miss.

  Returns:
    (client_type, client_info) tuple, as _loadfile() normally would.
    JSON contents is validated only during first load. Cache hits are not
    validated.
  """
  _SECRET_NAMESPACE = 'oauth2client:secrets#ns'

  if not cache:
    return _loadfile(filename)

  obj = cache.get(filename, namespace=_SECRET_NAMESPACE)
  if obj is None:
    client_type, client_info = _loadfile(filename)
    obj = {client_type: client_info}
    cache.set(filename, obj, namespace=_SECRET_NAMESPACE)

  return obj.iteritems().next()

########NEW FILE########
__FILENAME__ = crypt
#!/usr/bin/python2.4
# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 Google Inc.
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

import base64
import hashlib
import logging
import time

from anyjson import simplejson


CLOCK_SKEW_SECS = 300  # 5 minutes in seconds
AUTH_TOKEN_LIFETIME_SECS = 300  # 5 minutes in seconds
MAX_TOKEN_LIFETIME_SECS = 86400  # 1 day in seconds


logger = logging.getLogger(__name__)


class AppIdentityError(Exception):
  pass


try:
  from OpenSSL import crypto


  class OpenSSLVerifier(object):
    """Verifies the signature on a message."""

    def __init__(self, pubkey):
      """Constructor.

      Args:
        pubkey, OpenSSL.crypto.PKey, The public key to verify with.
      """
      self._pubkey = pubkey

    def verify(self, message, signature):
      """Verifies a message against a signature.

      Args:
        message: string, The message to verify.
        signature: string, The signature on the message.

      Returns:
        True if message was signed by the private key associated with the public
        key that this object was constructed with.
      """
      try:
        crypto.verify(self._pubkey, signature, message, 'sha256')
        return True
      except:
        return False

    @staticmethod
    def from_string(key_pem, is_x509_cert):
      """Construct a Verified instance from a string.

      Args:
        key_pem: string, public key in PEM format.
        is_x509_cert: bool, True if key_pem is an X509 cert, otherwise it is
          expected to be an RSA key in PEM format.

      Returns:
        Verifier instance.

      Raises:
        OpenSSL.crypto.Error if the key_pem can't be parsed.
      """
      if is_x509_cert:
        pubkey = crypto.load_certificate(crypto.FILETYPE_PEM, key_pem)
      else:
        pubkey = crypto.load_privatekey(crypto.FILETYPE_PEM, key_pem)
      return OpenSSLVerifier(pubkey)


  class OpenSSLSigner(object):
    """Signs messages with a private key."""

    def __init__(self, pkey):
      """Constructor.

      Args:
        pkey, OpenSSL.crypto.PKey (or equiv), The private key to sign with.
      """
      self._key = pkey

    def sign(self, message):
      """Signs a message.

      Args:
        message: string, Message to be signed.

      Returns:
        string, The signature of the message for the given key.
      """
      return crypto.sign(self._key, message, 'sha256')

    @staticmethod
    def from_string(key, password='notasecret'):
      """Construct a Signer instance from a string.

      Args:
        key: string, private key in PKCS12 or PEM format.
        password: string, password for the private key file.

      Returns:
        Signer instance.

      Raises:
        OpenSSL.crypto.Error if the key can't be parsed.
      """
      if key.startswith('-----BEGIN '):
        pkey = crypto.load_privatekey(crypto.FILETYPE_PEM, key)
      else:
        pkey = crypto.load_pkcs12(key, password).get_privatekey()
      return OpenSSLSigner(pkey)

except ImportError:
  OpenSSLVerifier = None
  OpenSSLSigner = None


try:
  from Crypto.PublicKey import RSA
  from Crypto.Hash import SHA256
  from Crypto.Signature import PKCS1_v1_5


  class PyCryptoVerifier(object):
    """Verifies the signature on a message."""

    def __init__(self, pubkey):
      """Constructor.

      Args:
        pubkey, OpenSSL.crypto.PKey (or equiv), The public key to verify with.
      """
      self._pubkey = pubkey

    def verify(self, message, signature):
      """Verifies a message against a signature.

      Args:
        message: string, The message to verify.
        signature: string, The signature on the message.

      Returns:
        True if message was signed by the private key associated with the public
        key that this object was constructed with.
      """
      try:
        return PKCS1_v1_5.new(self._pubkey).verify(
            SHA256.new(message), signature)
      except:
        return False

    @staticmethod
    def from_string(key_pem, is_x509_cert):
      """Construct a Verified instance from a string.

      Args:
        key_pem: string, public key in PEM format.
        is_x509_cert: bool, True if key_pem is an X509 cert, otherwise it is
          expected to be an RSA key in PEM format.

      Returns:
        Verifier instance.

      Raises:
        NotImplementedError if is_x509_cert is true.
      """
      if is_x509_cert:
        raise NotImplementedError(
            'X509 certs are not supported by the PyCrypto library. '
            'Try using PyOpenSSL if native code is an option.')
      else:
        pubkey = RSA.importKey(key_pem)
      return PyCryptoVerifier(pubkey)


  class PyCryptoSigner(object):
    """Signs messages with a private key."""

    def __init__(self, pkey):
      """Constructor.

      Args:
        pkey, OpenSSL.crypto.PKey (or equiv), The private key to sign with.
      """
      self._key = pkey

    def sign(self, message):
      """Signs a message.

      Args:
        message: string, Message to be signed.

      Returns:
        string, The signature of the message for the given key.
      """
      return PKCS1_v1_5.new(self._key).sign(SHA256.new(message))

    @staticmethod
    def from_string(key, password='notasecret'):
      """Construct a Signer instance from a string.

      Args:
        key: string, private key in PEM format.
        password: string, password for private key file. Unused for PEM files.

      Returns:
        Signer instance.

      Raises:
        NotImplementedError if they key isn't in PEM format.
      """
      if key.startswith('-----BEGIN '):
        pkey = RSA.importKey(key)
      else:
        raise NotImplementedError(
            'PKCS12 format is not supported by the PyCrpto library. '
            'Try converting to a "PEM" '
            '(openssl pkcs12 -in xxxxx.p12 -nodes -nocerts > privatekey.pem) '
            'or using PyOpenSSL if native code is an option.')
      return PyCryptoSigner(pkey)

except ImportError:
  PyCryptoVerifier = None
  PyCryptoSigner = None


if OpenSSLSigner:
  Signer = OpenSSLSigner
  Verifier = OpenSSLVerifier
elif PyCryptoSigner:
  Signer = PyCryptoSigner
  Verifier = PyCryptoVerifier
else:
  raise ImportError('No encryption library found. Please install either '
                    'PyOpenSSL, or PyCrypto 2.6 or later')


def _urlsafe_b64encode(raw_bytes):
  return base64.urlsafe_b64encode(raw_bytes).rstrip('=')


def _urlsafe_b64decode(b64string):
  # Guard against unicode strings, which base64 can't handle.
  b64string = b64string.encode('ascii')
  padded = b64string + '=' * (4 - len(b64string) % 4)
  return base64.urlsafe_b64decode(padded)


def _json_encode(data):
  return simplejson.dumps(data, separators = (',', ':'))


def make_signed_jwt(signer, payload):
  """Make a signed JWT.

  See http://self-issued.info/docs/draft-jones-json-web-token.html.

  Args:
    signer: crypt.Signer, Cryptographic signer.
    payload: dict, Dictionary of data to convert to JSON and then sign.

  Returns:
    string, The JWT for the payload.
  """
  header = {'typ': 'JWT', 'alg': 'RS256'}

  segments = [
          _urlsafe_b64encode(_json_encode(header)),
          _urlsafe_b64encode(_json_encode(payload)),
  ]
  signing_input = '.'.join(segments)

  signature = signer.sign(signing_input)
  segments.append(_urlsafe_b64encode(signature))

  logger.debug(str(segments))

  return '.'.join(segments)


def verify_signed_jwt_with_certs(jwt, certs, audience):
  """Verify a JWT against public certs.

  See http://self-issued.info/docs/draft-jones-json-web-token.html.

  Args:
    jwt: string, A JWT.
    certs: dict, Dictionary where values of public keys in PEM format.
    audience: string, The audience, 'aud', that this JWT should contain. If
      None then the JWT's 'aud' parameter is not verified.

  Returns:
    dict, The deserialized JSON payload in the JWT.

  Raises:
    AppIdentityError if any checks are failed.
  """
  segments = jwt.split('.')

  if (len(segments) != 3):
    raise AppIdentityError(
      'Wrong number of segments in token: %s' % jwt)
  signed = '%s.%s' % (segments[0], segments[1])

  signature = _urlsafe_b64decode(segments[2])

  # Parse token.
  json_body = _urlsafe_b64decode(segments[1])
  try:
    parsed = simplejson.loads(json_body)
  except:
    raise AppIdentityError('Can\'t parse token: %s' % json_body)

  # Check signature.
  verified = False
  for (keyname, pem) in certs.items():
    verifier = Verifier.from_string(pem, True)
    if (verifier.verify(signed, signature)):
      verified = True
      break
  if not verified:
    raise AppIdentityError('Invalid token signature: %s' % jwt)

  # Check creation timestamp.
  iat = parsed.get('iat')
  if iat is None:
    raise AppIdentityError('No iat field in token: %s' % json_body)
  earliest = iat - CLOCK_SKEW_SECS

  # Check expiration timestamp.
  now = long(time.time())
  exp = parsed.get('exp')
  if exp is None:
    raise AppIdentityError('No exp field in token: %s' % json_body)
  if exp >= now + MAX_TOKEN_LIFETIME_SECS:
    raise AppIdentityError(
      'exp field too far in future: %s' % json_body)
  latest = exp + CLOCK_SKEW_SECS

  if now < earliest:
    raise AppIdentityError('Token used too early, %d < %d: %s' %
      (now, earliest, json_body))
  if now > latest:
    raise AppIdentityError('Token used too late, %d > %d: %s' %
      (now, latest, json_body))

  # Check audience.
  if audience is not None:
    aud = parsed.get('aud')
    if aud is None:
      raise AppIdentityError('No aud field in token: %s' % json_body)
    if aud != audience:
      raise AppIdentityError('Wrong recipient, %s != %s: %s' %
          (aud, audience, json_body))

  return parsed

########NEW FILE########
__FILENAME__ = django_orm
# Copyright (C) 2010 Google Inc.
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

"""OAuth 2.0 utilities for Django.

Utilities for using OAuth 2.0 in conjunction with
the Django datastore.
"""

__author__ = 'jcgregorio@google.com (Joe Gregorio)'

import oauth2client
import base64
import pickle

from django.db import models
from oauth2client.client import Storage as BaseStorage

class CredentialsField(models.Field):

  __metaclass__ = models.SubfieldBase

  def __init__(self, *args, **kwargs):
    if 'null' not in kwargs:
      kwargs['null'] = True
    super(CredentialsField, self).__init__(*args, **kwargs)

  def get_internal_type(self):
    return "TextField"

  def to_python(self, value):
    if value is None:
      return None
    if isinstance(value, oauth2client.client.Credentials):
      return value
    return pickle.loads(base64.b64decode(value))

  def get_db_prep_value(self, value, connection, prepared=False):
    if value is None:
      return None
    return base64.b64encode(pickle.dumps(value))


class FlowField(models.Field):

  __metaclass__ = models.SubfieldBase

  def __init__(self, *args, **kwargs):
    if 'null' not in kwargs:
      kwargs['null'] = True
    super(FlowField, self).__init__(*args, **kwargs)

  def get_internal_type(self):
    return "TextField"

  def to_python(self, value):
    if value is None:
      return None
    if isinstance(value, oauth2client.client.Flow):
      return value
    return pickle.loads(base64.b64decode(value))

  def get_db_prep_value(self, value, connection, prepared=False):
    if value is None:
      return None
    return base64.b64encode(pickle.dumps(value))


class Storage(BaseStorage):
  """Store and retrieve a single credential to and from
  the datastore.

  This Storage helper presumes the Credentials
  have been stored as a CredenialsField
  on a db model class.
  """

  def __init__(self, model_class, key_name, key_value, property_name):
    """Constructor for Storage.

    Args:
      model: db.Model, model class
      key_name: string, key name for the entity that has the credentials
      key_value: string, key value for the entity that has the credentials
      property_name: string, name of the property that is an CredentialsProperty
    """
    self.model_class = model_class
    self.key_name = key_name
    self.key_value = key_value
    self.property_name = property_name

  def locked_get(self):
    """Retrieve Credential from datastore.

    Returns:
      oauth2client.Credentials
    """
    credential = None

    query = {self.key_name: self.key_value}
    entities = self.model_class.objects.filter(**query)
    if len(entities) > 0:
      credential = getattr(entities[0], self.property_name)
      if credential and hasattr(credential, 'set_store'):
        credential.set_store(self)
    return credential

  def locked_put(self, credentials):
    """Write a Credentials to the datastore.

    Args:
      credentials: Credentials, the credentials to store.
    """
    args = {self.key_name: self.key_value}
    entity = self.model_class(**args)
    setattr(entity, self.property_name, credentials)
    entity.save()

  def locked_delete(self):
    """Delete Credentials from the datastore."""

    query = {self.key_name: self.key_value}
    entities = self.model_class.objects.filter(**query).delete()

########NEW FILE########
__FILENAME__ = file
# Copyright (C) 2010 Google Inc.
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

"""Utilities for OAuth.

Utilities for making it easier to work with OAuth 2.0
credentials.
"""

__author__ = 'jcgregorio@google.com (Joe Gregorio)'

import os
import stat
import threading

from anyjson import simplejson
from client import Storage as BaseStorage
from client import Credentials


class CredentialsFileSymbolicLinkError(Exception):
  """Credentials files must not be symbolic links."""


class Storage(BaseStorage):
  """Store and retrieve a single credential to and from a file."""

  def __init__(self, filename):
    self._filename = filename
    self._lock = threading.Lock()

  def _validate_file(self):
    if os.path.islink(self._filename):
      raise CredentialsFileSymbolicLinkError(
          'File: %s is a symbolic link.' % self._filename)

  def acquire_lock(self):
    """Acquires any lock necessary to access this Storage.

    This lock is not reentrant."""
    self._lock.acquire()

  def release_lock(self):
    """Release the Storage lock.

    Trying to release a lock that isn't held will result in a
    RuntimeError.
    """
    self._lock.release()

  def locked_get(self):
    """Retrieve Credential from file.

    Returns:
      oauth2client.client.Credentials

    Raises:
      CredentialsFileSymbolicLinkError if the file is a symbolic link.
    """
    credentials = None
    self._validate_file()
    try:
      f = open(self._filename, 'rb')
      content = f.read()
      f.close()
    except IOError:
      return credentials

    try:
      credentials = Credentials.new_from_json(content)
      credentials.set_store(self)
    except ValueError:
      pass

    return credentials

  def _create_file_if_needed(self):
    """Create an empty file if necessary.

    This method will not initialize the file. Instead it implements a
    simple version of "touch" to ensure the file has been created.
    """
    if not os.path.exists(self._filename):
      old_umask = os.umask(0177)
      try:
        open(self._filename, 'a+b').close()
      finally:
        os.umask(old_umask)

  def locked_put(self, credentials):
    """Write Credentials to file.

    Args:
      credentials: Credentials, the credentials to store.

    Raises:
      CredentialsFileSymbolicLinkError if the file is a symbolic link.
    """

    self._create_file_if_needed()
    self._validate_file()
    f = open(self._filename, 'wb')
    f.write(credentials.to_json())
    f.close()

  def locked_delete(self):
    """Delete Credentials file.

    Args:
      credentials: Credentials, the credentials to store.
    """

    os.unlink(self._filename)

########NEW FILE########
__FILENAME__ = gce
# Copyright (C) 2012 Google Inc.
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

"""Utilities for Google Compute Engine

Utilities for making it easier to use OAuth 2.0 on Google Compute Engine.
"""

__author__ = 'jcgregorio@google.com (Joe Gregorio)'

import httplib2
import logging
import uritemplate

from oauth2client import util
from oauth2client.anyjson import simplejson
from oauth2client.client import AccessTokenRefreshError
from oauth2client.client import AssertionCredentials

logger = logging.getLogger(__name__)

# URI Template for the endpoint that returns access_tokens.
META = ('http://metadata.google.internal/0.1/meta-data/service-accounts/'
        'default/acquire{?scope}')


class AppAssertionCredentials(AssertionCredentials):
  """Credentials object for Compute Engine Assertion Grants

  This object will allow a Compute Engine instance to identify itself to
  Google and other OAuth 2.0 servers that can verify assertions. It can be used
  for the purpose of accessing data stored under an account assigned to the
  Compute Engine instance itself.

  This credential does not require a flow to instantiate because it represents
  a two legged flow, and therefore has all of the required information to
  generate and refresh its own access tokens.
  """

  @util.positional(2)
  def __init__(self, scope, **kwargs):
    """Constructor for AppAssertionCredentials

    Args:
      scope: string or iterable of strings, scope(s) of the credentials being
        requested.
    """
    self.scope = util.scopes_to_string(scope)

    # Assertion type is no longer used, but still in the parent class signature.
    super(AppAssertionCredentials, self).__init__(None)

  @classmethod
  def from_json(cls, json):
    data = simplejson.loads(json)
    return AppAssertionCredentials(data['scope'])

  def _refresh(self, http_request):
    """Refreshes the access_token.

    Skip all the storage hoops and just refresh using the API.

    Args:
      http_request: callable, a callable that matches the method signature of
        httplib2.Http.request, used to make the refresh request.

    Raises:
      AccessTokenRefreshError: When the refresh fails.
    """
    uri = uritemplate.expand(META, {'scope': self.scope})
    response, content = http_request(uri)
    if response.status == 200:
      try:
        d = simplejson.loads(content)
      except StandardError, e:
        raise AccessTokenRefreshError(str(e))
      self.access_token = d['accessToken']
    else:
      raise AccessTokenRefreshError(content)

########NEW FILE########
__FILENAME__ = keyring_storage
# Copyright (C) 2012 Google Inc.
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

"""A keyring based Storage.

A Storage for Credentials that uses the keyring module.
"""

__author__ = 'jcgregorio@google.com (Joe Gregorio)'

import keyring
import threading

from client import Storage as BaseStorage
from client import Credentials


class Storage(BaseStorage):
  """Store and retrieve a single credential to and from the keyring.

  To use this module you must have the keyring module installed. See
  <http://pypi.python.org/pypi/keyring/>. This is an optional module and is not
  installed with oauth2client by default because it does not work on all the
  platforms that oauth2client supports, such as Google App Engine.

  The keyring module <http://pypi.python.org/pypi/keyring/> is a cross-platform
  library for access the keyring capabilities of the local system. The user will
  be prompted for their keyring password when this module is used, and the
  manner in which the user is prompted will vary per platform.

  Usage:
    from oauth2client.keyring_storage import Storage

    s = Storage('name_of_application', 'user1')
    credentials = s.get()

  """

  def __init__(self, service_name, user_name):
    """Constructor.

    Args:
      service_name: string, The name of the service under which the credentials
        are stored.
      user_name: string, The name of the user to store credentials for.
    """
    self._service_name = service_name
    self._user_name = user_name
    self._lock = threading.Lock()

  def acquire_lock(self):
    """Acquires any lock necessary to access this Storage.

    This lock is not reentrant."""
    self._lock.acquire()

  def release_lock(self):
    """Release the Storage lock.

    Trying to release a lock that isn't held will result in a
    RuntimeError.
    """
    self._lock.release()

  def locked_get(self):
    """Retrieve Credential from file.

    Returns:
      oauth2client.client.Credentials
    """
    credentials = None
    content = keyring.get_password(self._service_name, self._user_name)

    if content is not None:
      try:
        credentials = Credentials.new_from_json(content)
        credentials.set_store(self)
      except ValueError:
        pass

    return credentials

  def locked_put(self, credentials):
    """Write Credentials to file.

    Args:
      credentials: Credentials, the credentials to store.
    """
    keyring.set_password(self._service_name, self._user_name,
                         credentials.to_json())

  def locked_delete(self):
    """Delete Credentials file.

    Args:
      credentials: Credentials, the credentials to store.
    """
    keyring.set_password(self._service_name, self._user_name, '')

########NEW FILE########
__FILENAME__ = locked_file
# Copyright 2011 Google Inc.
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

"""Locked file interface that should work on Unix and Windows pythons.

This module first tries to use fcntl locking to ensure serialized access
to a file, then falls back on a lock file if that is unavialable.

Usage:
    f = LockedFile('filename', 'r+b', 'rb')
    f.open_and_lock()
    if f.is_locked():
      print 'Acquired filename with r+b mode'
      f.file_handle().write('locked data')
    else:
      print 'Aquired filename with rb mode'
    f.unlock_and_close()
"""

__author__ = 'cache@google.com (David T McWherter)'

import errno
import logging
import os
import time

from oauth2client import util

logger = logging.getLogger(__name__)


class CredentialsFileSymbolicLinkError(Exception):
  """Credentials files must not be symbolic links."""


class AlreadyLockedException(Exception):
  """Trying to lock a file that has already been locked by the LockedFile."""
  pass


def validate_file(filename):
  if os.path.islink(filename):
    raise CredentialsFileSymbolicLinkError(
        'File: %s is a symbolic link.' % filename)

class _Opener(object):
  """Base class for different locking primitives."""

  def __init__(self, filename, mode, fallback_mode):
    """Create an Opener.

    Args:
      filename: string, The pathname of the file.
      mode: string, The preferred mode to access the file with.
      fallback_mode: string, The mode to use if locking fails.
    """
    self._locked = False
    self._filename = filename
    self._mode = mode
    self._fallback_mode = fallback_mode
    self._fh = None

  def is_locked(self):
    """Was the file locked."""
    return self._locked

  def file_handle(self):
    """The file handle to the file. Valid only after opened."""
    return self._fh

  def filename(self):
    """The filename that is being locked."""
    return self._filename

  def open_and_lock(self, timeout, delay):
    """Open the file and lock it.

    Args:
      timeout: float, How long to try to lock for.
      delay: float, How long to wait between retries.
    """
    pass

  def unlock_and_close(self):
    """Unlock and close the file."""
    pass


class _PosixOpener(_Opener):
  """Lock files using Posix advisory lock files."""

  def open_and_lock(self, timeout, delay):
    """Open the file and lock it.

    Tries to create a .lock file next to the file we're trying to open.

    Args:
      timeout: float, How long to try to lock for.
      delay: float, How long to wait between retries.

    Raises:
      AlreadyLockedException: if the lock is already acquired.
      IOError: if the open fails.
      CredentialsFileSymbolicLinkError if the file is a symbolic link.
    """
    if self._locked:
      raise AlreadyLockedException('File %s is already locked' %
                                   self._filename)
    self._locked = False

    validate_file(self._filename)
    try:
      self._fh = open(self._filename, self._mode)
    except IOError, e:
      # If we can't access with _mode, try _fallback_mode and don't lock.
      if e.errno == errno.EACCES:
        self._fh = open(self._filename, self._fallback_mode)
        return

    lock_filename = self._posix_lockfile(self._filename)
    start_time = time.time()
    while True:
      try:
        self._lock_fd = os.open(lock_filename,
                                os.O_CREAT|os.O_EXCL|os.O_RDWR)
        self._locked = True
        break

      except OSError, e:
        if e.errno != errno.EEXIST:
          raise
        if (time.time() - start_time) >= timeout:
          logger.warn('Could not acquire lock %s in %s seconds' % (
              lock_filename, timeout))
          # Close the file and open in fallback_mode.
          if self._fh:
            self._fh.close()
          self._fh = open(self._filename, self._fallback_mode)
          return
        time.sleep(delay)

  def unlock_and_close(self):
    """Unlock a file by removing the .lock file, and close the handle."""
    if self._locked:
      lock_filename = self._posix_lockfile(self._filename)
      os.close(self._lock_fd)
      os.unlink(lock_filename)
      self._locked = False
      self._lock_fd = None
    if self._fh:
      self._fh.close()

  def _posix_lockfile(self, filename):
    """The name of the lock file to use for posix locking."""
    return '%s.lock' % filename


try:
  import fcntl

  class _FcntlOpener(_Opener):
    """Open, lock, and unlock a file using fcntl.lockf."""

    def open_and_lock(self, timeout, delay):
      """Open the file and lock it.

      Args:
        timeout: float, How long to try to lock for.
        delay: float, How long to wait between retries

      Raises:
        AlreadyLockedException: if the lock is already acquired.
        IOError: if the open fails.
        CredentialsFileSymbolicLinkError if the file is a symbolic link.
      """
      if self._locked:
        raise AlreadyLockedException('File %s is already locked' %
                                     self._filename)
      start_time = time.time()

      validate_file(self._filename)
      try:
        self._fh = open(self._filename, self._mode)
      except IOError, e:
        # If we can't access with _mode, try _fallback_mode and don't lock.
        if e.errno == errno.EACCES:
          self._fh = open(self._filename, self._fallback_mode)
          return

      # We opened in _mode, try to lock the file.
      while True:
        try:
          fcntl.lockf(self._fh.fileno(), fcntl.LOCK_EX)
          self._locked = True
          return
        except IOError, e:
          # If not retrying, then just pass on the error.
          if timeout == 0:
            raise e
          if e.errno != errno.EACCES:
            raise e
          # We could not acquire the lock. Try again.
          if (time.time() - start_time) >= timeout:
            logger.warn('Could not lock %s in %s seconds' % (
                self._filename, timeout))
            if self._fh:
              self._fh.close()
            self._fh = open(self._filename, self._fallback_mode)
            return
          time.sleep(delay)

    def unlock_and_close(self):
      """Close and unlock the file using the fcntl.lockf primitive."""
      if self._locked:
        fcntl.lockf(self._fh.fileno(), fcntl.LOCK_UN)
      self._locked = False
      if self._fh:
        self._fh.close()
except ImportError:
  _FcntlOpener = None


try:
  import pywintypes
  import win32con
  import win32file

  class _Win32Opener(_Opener):
    """Open, lock, and unlock a file using windows primitives."""

    # Error #33:
    #  'The process cannot access the file because another process'
    FILE_IN_USE_ERROR = 33

    # Error #158:
    #  'The segment is already unlocked.'
    FILE_ALREADY_UNLOCKED_ERROR = 158

    def open_and_lock(self, timeout, delay):
      """Open the file and lock it.

      Args:
        timeout: float, How long to try to lock for.
        delay: float, How long to wait between retries

      Raises:
        AlreadyLockedException: if the lock is already acquired.
        IOError: if the open fails.
        CredentialsFileSymbolicLinkError if the file is a symbolic link.
      """
      if self._locked:
        raise AlreadyLockedException('File %s is already locked' %
                                     self._filename)
      start_time = time.time()

      validate_file(self._filename)
      try:
        self._fh = open(self._filename, self._mode)
      except IOError, e:
        # If we can't access with _mode, try _fallback_mode and don't lock.
        if e.errno == errno.EACCES:
          self._fh = open(self._filename, self._fallback_mode)
          return

      # We opened in _mode, try to lock the file.
      while True:
        try:
          hfile = win32file._get_osfhandle(self._fh.fileno())
          win32file.LockFileEx(
              hfile,
              (win32con.LOCKFILE_FAIL_IMMEDIATELY|
               win32con.LOCKFILE_EXCLUSIVE_LOCK), 0, -0x10000,
              pywintypes.OVERLAPPED())
          self._locked = True
          return
        except pywintypes.error, e:
          if timeout == 0:
            raise e

          # If the error is not that the file is already in use, raise.
          if e[0] != _Win32Opener.FILE_IN_USE_ERROR:
            raise

          # We could not acquire the lock. Try again.
          if (time.time() - start_time) >= timeout:
            logger.warn('Could not lock %s in %s seconds' % (
                self._filename, timeout))
            if self._fh:
              self._fh.close()
            self._fh = open(self._filename, self._fallback_mode)
            return
          time.sleep(delay)

    def unlock_and_close(self):
      """Close and unlock the file using the win32 primitive."""
      if self._locked:
        try:
          hfile = win32file._get_osfhandle(self._fh.fileno())
          win32file.UnlockFileEx(hfile, 0, -0x10000, pywintypes.OVERLAPPED())
        except pywintypes.error, e:
          if e[0] != _Win32Opener.FILE_ALREADY_UNLOCKED_ERROR:
            raise
      self._locked = False
      if self._fh:
        self._fh.close()
except ImportError:
  _Win32Opener = None


class LockedFile(object):
  """Represent a file that has exclusive access."""

  @util.positional(4)
  def __init__(self, filename, mode, fallback_mode, use_native_locking=True):
    """Construct a LockedFile.

    Args:
      filename: string, The path of the file to open.
      mode: string, The mode to try to open the file with.
      fallback_mode: string, The mode to use if locking fails.
      use_native_locking: bool, Whether or not fcntl/win32 locking is used.
    """
    opener = None
    if not opener and use_native_locking:
      if _Win32Opener:
        opener = _Win32Opener(filename, mode, fallback_mode)
      if _FcntlOpener:
        opener = _FcntlOpener(filename, mode, fallback_mode)

    if not opener:
      opener = _PosixOpener(filename, mode, fallback_mode)

    self._opener = opener

  def filename(self):
    """Return the filename we were constructed with."""
    return self._opener._filename

  def file_handle(self):
    """Return the file_handle to the opened file."""
    return self._opener.file_handle()

  def is_locked(self):
    """Return whether we successfully locked the file."""
    return self._opener.is_locked()

  def open_and_lock(self, timeout=0, delay=0.05):
    """Open the file, trying to lock it.

    Args:
      timeout: float, The number of seconds to try to acquire the lock.
      delay: float, The number of seconds to wait between retry attempts.

    Raises:
      AlreadyLockedException: if the lock is already acquired.
      IOError: if the open fails.
    """
    self._opener.open_and_lock(timeout, delay)

  def unlock_and_close(self):
    """Unlock and close a file."""
    self._opener.unlock_and_close()

########NEW FILE########
__FILENAME__ = multistore_file
# Copyright 2011 Google Inc.
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

"""Multi-credential file store with lock support.

This module implements a JSON credential store where multiple
credentials can be stored in one file. That file supports locking
both in a single process and across processes.

The credential themselves are keyed off of:
* client_id
* user_agent
* scope

The format of the stored data is like so:
{
  'file_version': 1,
  'data': [
    {
      'key': {
        'clientId': '<client id>',
        'userAgent': '<user agent>',
        'scope': '<scope>'
      },
      'credential': {
        # JSON serialized Credentials.
      }
    }
  ]
}
"""

__author__ = 'jbeda@google.com (Joe Beda)'

import base64
import errno
import logging
import os
import threading

from anyjson import simplejson
from oauth2client.client import Storage as BaseStorage
from oauth2client.client import Credentials
from oauth2client import util
from locked_file import LockedFile

logger = logging.getLogger(__name__)

# A dict from 'filename'->_MultiStore instances
_multistores = {}
_multistores_lock = threading.Lock()


class Error(Exception):
  """Base error for this module."""
  pass


class NewerCredentialStoreError(Error):
  """The credential store is a newer version that supported."""
  pass


@util.positional(4)
def get_credential_storage(filename, client_id, user_agent, scope,
                           warn_on_readonly=True):
  """Get a Storage instance for a credential.

  Args:
    filename: The JSON file storing a set of credentials
    client_id: The client_id for the credential
    user_agent: The user agent for the credential
    scope: string or iterable of strings, Scope(s) being requested
    warn_on_readonly: if True, log a warning if the store is readonly

  Returns:
    An object derived from client.Storage for getting/setting the
    credential.
  """
  # Recreate the legacy key with these specific parameters
  key = {'clientId': client_id, 'userAgent': user_agent,
         'scope': util.scopes_to_string(scope)}
  return get_credential_storage_custom_key(
      filename, key, warn_on_readonly=warn_on_readonly)


@util.positional(2)
def get_credential_storage_custom_string_key(
    filename, key_string, warn_on_readonly=True):
  """Get a Storage instance for a credential using a single string as a key.

  Allows you to provide a string as a custom key that will be used for
  credential storage and retrieval.

  Args:
    filename: The JSON file storing a set of credentials
    key_string: A string to use as the key for storing this credential.
    warn_on_readonly: if True, log a warning if the store is readonly

  Returns:
    An object derived from client.Storage for getting/setting the
    credential.
  """
  # Create a key dictionary that can be used
  key_dict = {'key': key_string}
  return get_credential_storage_custom_key(
      filename, key_dict, warn_on_readonly=warn_on_readonly)


@util.positional(2)
def get_credential_storage_custom_key(
    filename, key_dict, warn_on_readonly=True):
  """Get a Storage instance for a credential using a dictionary as a key.

  Allows you to provide a dictionary as a custom key that will be used for
  credential storage and retrieval.

  Args:
    filename: The JSON file storing a set of credentials
    key_dict: A dictionary to use as the key for storing this credential. There
      is no ordering of the keys in the dictionary. Logically equivalent
      dictionaries will produce equivalent storage keys.
    warn_on_readonly: if True, log a warning if the store is readonly

  Returns:
    An object derived from client.Storage for getting/setting the
    credential.
  """
  multistore = _get_multistore(filename, warn_on_readonly=warn_on_readonly)
  key = util.dict_to_tuple_key(key_dict)
  return multistore._get_storage(key)


@util.positional(1)
def get_all_credential_keys(filename, warn_on_readonly=True):
  """Gets all the registered credential keys in the given Multistore.

  Args:
    filename: The JSON file storing a set of credentials
    warn_on_readonly: if True, log a warning if the store is readonly

  Returns:
    A list of the credential keys present in the file.  They are returned as
    dictionaries that can be passed into get_credential_storage_custom_key to
    get the actual credentials.
  """
  multistore = _get_multistore(filename, warn_on_readonly=warn_on_readonly)
  multistore._lock()
  try:
    return multistore._get_all_credential_keys()
  finally:
    multistore._unlock()


@util.positional(1)
def _get_multistore(filename, warn_on_readonly=True):
  """A helper method to initialize the multistore with proper locking.

  Args:
    filename: The JSON file storing a set of credentials
    warn_on_readonly: if True, log a warning if the store is readonly

  Returns:
    A multistore object
  """
  filename = os.path.expanduser(filename)
  _multistores_lock.acquire()
  try:
    multistore = _multistores.setdefault(
        filename, _MultiStore(filename, warn_on_readonly=warn_on_readonly))
  finally:
    _multistores_lock.release()
  return multistore


class _MultiStore(object):
  """A file backed store for multiple credentials."""

  @util.positional(2)
  def __init__(self, filename, warn_on_readonly=True):
    """Initialize the class.

    This will create the file if necessary.
    """
    self._file = LockedFile(filename, 'r+b', 'rb')
    self._thread_lock = threading.Lock()
    self._read_only = False
    self._warn_on_readonly = warn_on_readonly

    self._create_file_if_needed()

    # Cache of deserialized store. This is only valid after the
    # _MultiStore is locked or _refresh_data_cache is called. This is
    # of the form of:
    #
    # ((key, value), (key, value)...) -> OAuth2Credential
    #
    # If this is None, then the store hasn't been read yet.
    self._data = None

  class _Storage(BaseStorage):
    """A Storage object that knows how to read/write a single credential."""

    def __init__(self, multistore, key):
      self._multistore = multistore
      self._key = key

    def acquire_lock(self):
      """Acquires any lock necessary to access this Storage.

      This lock is not reentrant.
      """
      self._multistore._lock()

    def release_lock(self):
      """Release the Storage lock.

      Trying to release a lock that isn't held will result in a
      RuntimeError.
      """
      self._multistore._unlock()

    def locked_get(self):
      """Retrieve credential.

      The Storage lock must be held when this is called.

      Returns:
        oauth2client.client.Credentials
      """
      credential = self._multistore._get_credential(self._key)
      if credential:
        credential.set_store(self)
      return credential

    def locked_put(self, credentials):
      """Write a credential.

      The Storage lock must be held when this is called.

      Args:
        credentials: Credentials, the credentials to store.
      """
      self._multistore._update_credential(self._key, credentials)

    def locked_delete(self):
      """Delete a credential.

      The Storage lock must be held when this is called.

      Args:
        credentials: Credentials, the credentials to store.
      """
      self._multistore._delete_credential(self._key)

  def _create_file_if_needed(self):
    """Create an empty file if necessary.

    This method will not initialize the file. Instead it implements a
    simple version of "touch" to ensure the file has been created.
    """
    if not os.path.exists(self._file.filename()):
      old_umask = os.umask(0177)
      try:
        open(self._file.filename(), 'a+b').close()
      finally:
        os.umask(old_umask)

  def _lock(self):
    """Lock the entire multistore."""
    self._thread_lock.acquire()
    self._file.open_and_lock()
    if not self._file.is_locked():
      self._read_only = True
      if self._warn_on_readonly:
        logger.warn('The credentials file (%s) is not writable. Opening in '
                    'read-only mode. Any refreshed credentials will only be '
                    'valid for this run.' % self._file.filename())
    if os.path.getsize(self._file.filename()) == 0:
      logger.debug('Initializing empty multistore file')
      # The multistore is empty so write out an empty file.
      self._data = {}
      self._write()
    elif not self._read_only or self._data is None:
      # Only refresh the data if we are read/write or we haven't
      # cached the data yet. If we are readonly, we assume is isn't
      # changing out from under us and that we only have to read it
      # once. This prevents us from whacking any new access keys that
      # we have cached in memory but were unable to write out.
      self._refresh_data_cache()

  def _unlock(self):
    """Release the lock on the multistore."""
    self._file.unlock_and_close()
    self._thread_lock.release()

  def _locked_json_read(self):
    """Get the raw content of the multistore file.

    The multistore must be locked when this is called.

    Returns:
      The contents of the multistore decoded as JSON.
    """
    assert self._thread_lock.locked()
    self._file.file_handle().seek(0)
    return simplejson.load(self._file.file_handle())

  def _locked_json_write(self, data):
    """Write a JSON serializable data structure to the multistore.

    The multistore must be locked when this is called.

    Args:
      data: The data to be serialized and written.
    """
    assert self._thread_lock.locked()
    if self._read_only:
      return
    self._file.file_handle().seek(0)
    simplejson.dump(data, self._file.file_handle(), sort_keys=True, indent=2)
    self._file.file_handle().truncate()

  def _refresh_data_cache(self):
    """Refresh the contents of the multistore.

    The multistore must be locked when this is called.

    Raises:
      NewerCredentialStoreError: Raised when a newer client has written the
        store.
    """
    self._data = {}
    try:
      raw_data = self._locked_json_read()
    except Exception:
      logger.warn('Credential data store could not be loaded. '
                  'Will ignore and overwrite.')
      return

    version = 0
    try:
      version = raw_data['file_version']
    except Exception:
      logger.warn('Missing version for credential data store. It may be '
                  'corrupt or an old version. Overwriting.')
    if version > 1:
      raise NewerCredentialStoreError(
          'Credential file has file_version of %d. '
          'Only file_version of 1 is supported.' % version)

    credentials = []
    try:
      credentials = raw_data['data']
    except (TypeError, KeyError):
      pass

    for cred_entry in credentials:
      try:
        (key, credential) = self._decode_credential_from_json(cred_entry)
        self._data[key] = credential
      except:
        # If something goes wrong loading a credential, just ignore it
        logger.info('Error decoding credential, skipping', exc_info=True)

  def _decode_credential_from_json(self, cred_entry):
    """Load a credential from our JSON serialization.

    Args:
      cred_entry: A dict entry from the data member of our format

    Returns:
      (key, cred) where the key is the key tuple and the cred is the
        OAuth2Credential object.
    """
    raw_key = cred_entry['key']
    key = util.dict_to_tuple_key(raw_key)
    credential = None
    credential = Credentials.new_from_json(simplejson.dumps(cred_entry['credential']))
    return (key, credential)

  def _write(self):
    """Write the cached data back out.

    The multistore must be locked.
    """
    raw_data = {'file_version': 1}
    raw_creds = []
    raw_data['data'] = raw_creds
    for (cred_key, cred) in self._data.items():
      raw_key = dict(cred_key)
      raw_cred = simplejson.loads(cred.to_json())
      raw_creds.append({'key': raw_key, 'credential': raw_cred})
    self._locked_json_write(raw_data)

  def _get_all_credential_keys(self):
    """Gets all the registered credential keys in the multistore.

    Returns:
      A list of dictionaries corresponding to all the keys currently registered
    """
    return [dict(key) for key in self._data.keys()]

  def _get_credential(self, key):
    """Get a credential from the multistore.

    The multistore must be locked.

    Args:
      key: The key used to retrieve the credential

    Returns:
      The credential specified or None if not present
    """
    return self._data.get(key, None)

  def _update_credential(self, key, cred):
    """Update a credential and write the multistore.

    This must be called when the multistore is locked.

    Args:
      key: The key used to retrieve the credential
      cred: The OAuth2Credential to update/set
    """
    self._data[key] = cred
    self._write()

  def _delete_credential(self, key):
    """Delete a credential and write the multistore.

    This must be called when the multistore is locked.

    Args:
      key: The key used to retrieve the credential
    """
    try:
      del self._data[key]
    except KeyError:
      pass
    self._write()

  def _get_storage(self, key):
    """Get a Storage object to get/set a credential.

    This Storage is a 'view' into the multistore.

    Args:
      key: The key used to retrieve the credential

    Returns:
      A Storage object that can be used to get/set this cred
    """
    return self._Storage(self, key)

########NEW FILE########
__FILENAME__ = old_run
# Copyright (C) 2013 Google Inc.
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

"""This module holds the old run() function which is deprecated, the
tools.run_flow() function should be used in its place."""


import logging
import socket
import sys
import webbrowser

import gflags

from oauth2client import client
from oauth2client import util
from tools import ClientRedirectHandler
from tools import ClientRedirectServer


FLAGS = gflags.FLAGS

gflags.DEFINE_boolean('auth_local_webserver', True,
                      ('Run a local web server to handle redirects during '
                       'OAuth authorization.'))

gflags.DEFINE_string('auth_host_name', 'localhost',
                     ('Host name to use when running a local web server to '
                      'handle redirects during OAuth authorization.'))

gflags.DEFINE_multi_int('auth_host_port', [8080, 8090],
                        ('Port to use when running a local web server to '
                         'handle redirects during OAuth authorization.'))


@util.positional(2)
def run(flow, storage, http=None):
  """Core code for a command-line application.

  The run() function is called from your application and runs through all
  the steps to obtain credentials. It takes a Flow argument and attempts to
  open an authorization server page in the user's default web browser. The
  server asks the user to grant your application access to the user's data.
  If the user grants access, the run() function returns new credentials. The
  new credentials are also stored in the Storage argument, which updates the
  file associated with the Storage object.

  It presumes it is run from a command-line application and supports the
  following flags:

    --auth_host_name: Host name to use when running a local web server
      to handle redirects during OAuth authorization.
      (default: 'localhost')

    --auth_host_port: Port to use when running a local web server to handle
    redirects during OAuth authorization.;
      repeat this option to specify a list of values
      (default: '[8080, 8090]')
      (an integer)

    --[no]auth_local_webserver: Run a local web server to handle redirects
      during OAuth authorization.
      (default: 'true')

  Since it uses flags make sure to initialize the gflags module before
  calling run().

  Args:
    flow: Flow, an OAuth 2.0 Flow to step through.
    storage: Storage, a Storage to store the credential in.
    http: An instance of httplib2.Http.request
         or something that acts like it.

  Returns:
    Credentials, the obtained credential.
  """
  logging.warning('This function, oauth2client.tools.run(), and the use of '
      'the gflags library are deprecated and will be removed in a future '
      'version of the library.')
  if FLAGS.auth_local_webserver:
    success = False
    port_number = 0
    for port in FLAGS.auth_host_port:
      port_number = port
      try:
        httpd = ClientRedirectServer((FLAGS.auth_host_name, port),
                                     ClientRedirectHandler)
      except socket.error, e:
        pass
      else:
        success = True
        break
    FLAGS.auth_local_webserver = success
    if not success:
      print 'Failed to start a local webserver listening on either port 8080'
      print 'or port 9090. Please check your firewall settings and locally'
      print 'running programs that may be blocking or using those ports.'
      print
      print 'Falling back to --noauth_local_webserver and continuing with',
      print 'authorization.'
      print

  if FLAGS.auth_local_webserver:
    oauth_callback = 'http://%s:%s/' % (FLAGS.auth_host_name, port_number)
  else:
    oauth_callback = client.OOB_CALLBACK_URN
  flow.redirect_uri = oauth_callback
  authorize_url = flow.step1_get_authorize_url()

  if FLAGS.auth_local_webserver:
    webbrowser.open(authorize_url, new=1, autoraise=True)
    print 'Your browser has been opened to visit:'
    print
    print '    ' + authorize_url
    print
    print 'If your browser is on a different machine then exit and re-run'
    print 'this application with the command-line parameter '
    print
    print '  --noauth_local_webserver'
    print
  else:
    print 'Go to the following link in your browser:'
    print
    print '    ' + authorize_url
    print

  code = None
  if FLAGS.auth_local_webserver:
    httpd.handle_request()
    if 'error' in httpd.query_params:
      sys.exit('Authentication request was rejected.')
    if 'code' in httpd.query_params:
      code = httpd.query_params['code']
    else:
      print 'Failed to find "code" in the query parameters of the redirect.'
      sys.exit('Try running with --noauth_local_webserver.')
  else:
    code = raw_input('Enter verification code: ').strip()

  try:
    credential = flow.step2_exchange(code, http=http)
  except client.FlowExchangeError, e:
    sys.exit('Authentication has failed: %s' % e)

  storage.put(credential)
  credential.set_store(storage)
  print 'Authentication successful.'

  return credential

########NEW FILE########
__FILENAME__ = tools
# Copyright (C) 2013 Google Inc.
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

"""Command-line tools for authenticating via OAuth 2.0

Do the OAuth 2.0 Web Server dance for a command line application. Stores the
generated credentials in a common file that is used by other example apps in
the same directory.
"""

__author__ = 'jcgregorio@google.com (Joe Gregorio)'
__all__ = ['argparser', 'run_flow', 'run', 'message_if_missing']


import BaseHTTPServer
import argparse
import httplib2
import logging
import os
import socket
import sys
import webbrowser

from oauth2client import client
from oauth2client import file
from oauth2client import util

try:
  from urlparse import parse_qsl
except ImportError:
  from cgi import parse_qsl

_CLIENT_SECRETS_MESSAGE = """WARNING: Please configure OAuth 2.0

To make this sample run you will need to populate the client_secrets.json file
found at:

   %s

with information from the APIs Console <https://code.google.com/apis/console>.

"""

# run_parser is an ArgumentParser that contains command-line options expected
# by tools.run(). Pass it in as part of the 'parents' argument to your own
# ArgumentParser.
argparser = argparse.ArgumentParser(add_help=False)
argparser.add_argument('--auth_host_name', default='localhost',
                        help='Hostname when running a local web server.')
argparser.add_argument('--noauth_local_webserver', action='store_true',
                        default=False, help='Do not run a local web server.')
argparser.add_argument('--auth_host_port', default=[8080, 8090], type=int,
                        nargs='*', help='Port web server should listen on.')
argparser.add_argument('--logging_level', default='ERROR',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR',
                                 'CRITICAL'],
                        help='Set the logging level of detail.')


class ClientRedirectServer(BaseHTTPServer.HTTPServer):
  """A server to handle OAuth 2.0 redirects back to localhost.

  Waits for a single request and parses the query parameters
  into query_params and then stops serving.
  """
  query_params = {}


class ClientRedirectHandler(BaseHTTPServer.BaseHTTPRequestHandler):
  """A handler for OAuth 2.0 redirects back to localhost.

  Waits for a single request and parses the query parameters
  into the servers query_params and then stops serving.
  """

  def do_GET(s):
    """Handle a GET request.

    Parses the query parameters and prints a message
    if the flow has completed. Note that we can't detect
    if an error occurred.
    """
    s.send_response(200)
    s.send_header("Content-type", "text/html")
    s.end_headers()
    query = s.path.split('?', 1)[-1]
    query = dict(parse_qsl(query))
    s.server.query_params = query
    s.wfile.write("<html><head><title>Authentication Status</title></head>")
    s.wfile.write("<body><p>The authentication flow has completed.</p>")
    s.wfile.write("</body></html>")

  def log_message(self, format, *args):
    """Do not log messages to stdout while running as command line program."""
    pass


@util.positional(3)
def run_flow(flow, storage, flags, http=None):
  """Core code for a command-line application.

  The run() function is called from your application and runs through all the
  steps to obtain credentials. It takes a Flow argument and attempts to open an
  authorization server page in the user's default web browser. The server asks
  the user to grant your application access to the user's data. If the user
  grants access, the run() function returns new credentials. The new credentials
  are also stored in the Storage argument, which updates the file associated
  with the Storage object.

  It presumes it is run from a command-line application and supports the
  following flags:

    --auth_host_name: Host name to use when running a local web server
      to handle redirects during OAuth authorization.
      (default: 'localhost')

    --auth_host_port: Port to use when running a local web server to handle
      redirects during OAuth authorization.;
      repeat this option to specify a list of values
      (default: '[8080, 8090]')
      (an integer)

    --[no]auth_local_webserver: Run a local web server to handle redirects
      during OAuth authorization.
      (default: 'true')

  The tools module defines an ArgumentParser the already contains the flag
  definitions that run() requires. You can pass that ArgumentParser to your
  ArgumentParser constructor:

    parser = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[tools.run_parser])
    flags = parser.parse_args(argv)

  Args:
    flow: Flow, an OAuth 2.0 Flow to step through.
    storage: Storage, a Storage to store the credential in.
    flags: argparse.ArgumentParser, the command-line flags.
    http: An instance of httplib2.Http.request
         or something that acts like it.

  Returns:
    Credentials, the obtained credential.
  """
  logging.getLogger().setLevel(getattr(logging, flags.logging_level))
  if not flags.noauth_local_webserver:
    success = False
    port_number = 0
    for port in flags.auth_host_port:
      port_number = port
      try:
        httpd = ClientRedirectServer((flags.auth_host_name, port),
                                     ClientRedirectHandler)
      except socket.error, e:
        pass
      else:
        success = True
        break
    flags.noauth_local_webserver = not success
    if not success:
      print 'Failed to start a local webserver listening on either port 8080'
      print 'or port 9090. Please check your firewall settings and locally'
      print 'running programs that may be blocking or using those ports.'
      print
      print 'Falling back to --noauth_local_webserver and continuing with',
      print 'authorization.'
      print

  if not flags.noauth_local_webserver:
    oauth_callback = 'http://%s:%s/' % (flags.auth_host_name, port_number)
  else:
    oauth_callback = client.OOB_CALLBACK_URN
  flow.redirect_uri = oauth_callback
  authorize_url = flow.step1_get_authorize_url()

  if not flags.noauth_local_webserver:
    webbrowser.open(authorize_url, new=1, autoraise=True)
    print 'Your browser has been opened to visit:'
    print
    print '    ' + authorize_url
    print
    print 'If your browser is on a different machine then exit and re-run this'
    print 'application with the command-line parameter '
    print
    print '  --noauth_local_webserver'
    print
  else:
    print 'Go to the following link in your browser:'
    print
    print '    ' + authorize_url
    print

  code = None
  if not flags.noauth_local_webserver:
    httpd.handle_request()
    if 'error' in httpd.query_params:
      sys.exit('Authentication request was rejected.')
    if 'code' in httpd.query_params:
      code = httpd.query_params['code']
    else:
      print 'Failed to find "code" in the query parameters of the redirect.'
      sys.exit('Try running with --noauth_local_webserver.')
  else:
    code = raw_input('Enter verification code: ').strip()

  try:
    credential = flow.step2_exchange(code, http=http)
  except client.FlowExchangeError, e:
    sys.exit('Authentication has failed: %s' % e)

  storage.put(credential)
  credential.set_store(storage)
  print 'Authentication successful.'

  return credential


def message_if_missing(filename):
  """Helpful message to display if the CLIENT_SECRETS file is missing."""

  return _CLIENT_SECRETS_MESSAGE % filename

try:
  from old_run import run
  from old_run import FLAGS
except ImportError:
  def run(*args, **kwargs):
    raise NotImplementedError(
        'The gflags library must be installed to use tools.run(). '
        'Please install gflags or preferrably switch to using '
        'tools.run_flow().')

########NEW FILE########
__FILENAME__ = util
#!/usr/bin/env python
#
# Copyright 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Common utility library."""

__author__ = ['rafek@google.com (Rafe Kaplan)',
              'guido@google.com (Guido van Rossum)',
]
__all__ = [
  'positional',
  'POSITIONAL_WARNING',
  'POSITIONAL_EXCEPTION',
  'POSITIONAL_IGNORE',
]

import inspect
import logging
import types
import urllib
import urlparse

try:
  from urlparse import parse_qsl
except ImportError:
  from cgi import parse_qsl

logger = logging.getLogger(__name__)

POSITIONAL_WARNING = 'WARNING'
POSITIONAL_EXCEPTION = 'EXCEPTION'
POSITIONAL_IGNORE = 'IGNORE'
POSITIONAL_SET = frozenset([POSITIONAL_WARNING, POSITIONAL_EXCEPTION,
                            POSITIONAL_IGNORE])

positional_parameters_enforcement = POSITIONAL_WARNING

def positional(max_positional_args):
  """A decorator to declare that only the first N arguments my be positional.

  This decorator makes it easy to support Python 3 style key-word only
  parameters. For example, in Python 3 it is possible to write:

    def fn(pos1, *, kwonly1=None, kwonly1=None):
      ...

  All named parameters after * must be a keyword:

    fn(10, 'kw1', 'kw2')  # Raises exception.
    fn(10, kwonly1='kw1')  # Ok.

  Example:
    To define a function like above, do:

      @positional(1)
      def fn(pos1, kwonly1=None, kwonly2=None):
        ...

    If no default value is provided to a keyword argument, it becomes a required
    keyword argument:

      @positional(0)
      def fn(required_kw):
        ...

    This must be called with the keyword parameter:

      fn()  # Raises exception.
      fn(10)  # Raises exception.
      fn(required_kw=10)  # Ok.

    When defining instance or class methods always remember to account for
    'self' and 'cls':

      class MyClass(object):

        @positional(2)
        def my_method(self, pos1, kwonly1=None):
          ...

        @classmethod
        @positional(2)
        def my_method(cls, pos1, kwonly1=None):
          ...

  The positional decorator behavior is controlled by
  util.positional_parameters_enforcement, which may be set to
  POSITIONAL_EXCEPTION, POSITIONAL_WARNING or POSITIONAL_IGNORE to raise an
  exception, log a warning, or do nothing, respectively, if a declaration is
  violated.

  Args:
    max_positional_arguments: Maximum number of positional arguments. All
      parameters after the this index must be keyword only.

  Returns:
    A decorator that prevents using arguments after max_positional_args from
    being used as positional parameters.

  Raises:
    TypeError if a key-word only argument is provided as a positional
    parameter, but only if util.positional_parameters_enforcement is set to
    POSITIONAL_EXCEPTION.
  """
  def positional_decorator(wrapped):
    def positional_wrapper(*args, **kwargs):
      if len(args) > max_positional_args:
        plural_s = ''
        if max_positional_args != 1:
          plural_s = 's'
        message = '%s() takes at most %d positional argument%s (%d given)' % (
            wrapped.__name__, max_positional_args, plural_s, len(args))
        if positional_parameters_enforcement == POSITIONAL_EXCEPTION:
          raise TypeError(message)
        elif positional_parameters_enforcement == POSITIONAL_WARNING:
          logger.warning(message)
        else: # IGNORE
          pass
      return wrapped(*args, **kwargs)
    return positional_wrapper

  if isinstance(max_positional_args, (int, long)):
    return positional_decorator
  else:
    args, _, _, defaults = inspect.getargspec(max_positional_args)
    return positional(len(args) - len(defaults))(max_positional_args)


def scopes_to_string(scopes):
  """Converts scope value to a string.

  If scopes is a string then it is simply passed through. If scopes is an
  iterable then a string is returned that is all the individual scopes
  concatenated with spaces.

  Args:
    scopes: string or iterable of strings, the scopes.

  Returns:
    The scopes formatted as a single string.
  """
  if isinstance(scopes, types.StringTypes):
    return scopes
  else:
    return ' '.join(scopes)


def dict_to_tuple_key(dictionary):
  """Converts a dictionary to a tuple that can be used as an immutable key.

  The resulting key is always sorted so that logically equivalent dictionaries
  always produce an identical tuple for a key.

  Args:
    dictionary: the dictionary to use as the key.

  Returns:
    A tuple representing the dictionary in it's naturally sorted ordering.
  """
  return tuple(sorted(dictionary.items()))


def _add_query_parameter(url, name, value):
  """Adds a query parameter to a url.

  Replaces the current value if it already exists in the URL.

  Args:
    url: string, url to add the query parameter to.
    name: string, query parameter name.
    value: string, query parameter value.

  Returns:
    Updated query parameter. Does not update the url if value is None.
  """
  if value is None:
    return url
  else:
    parsed = list(urlparse.urlparse(url))
    q = dict(parse_qsl(parsed[4]))
    q[name] = value
    parsed[4] = urllib.urlencode(q)
    return urlparse.urlunparse(parsed)

########NEW FILE########
__FILENAME__ = xsrfutil
#!/usr/bin/python2.5
#
# Copyright 2010 the Melange authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Helper methods for creating & verifying XSRF tokens."""

__authors__ = [
  '"Doug Coker" <dcoker@google.com>',
  '"Joe Gregorio" <jcgregorio@google.com>',
]


import base64
import hmac
import os  # for urandom
import time

from oauth2client import util


# Delimiter character
DELIMITER = ':'

# 1 hour in seconds
DEFAULT_TIMEOUT_SECS = 1*60*60

@util.positional(2)
def generate_token(key, user_id, action_id="", when=None):
  """Generates a URL-safe token for the given user, action, time tuple.

  Args:
    key: secret key to use.
    user_id: the user ID of the authenticated user.
    action_id: a string identifier of the action they requested
      authorization for.
    when: the time in seconds since the epoch at which the user was
      authorized for this action. If not set the current time is used.

  Returns:
    A string XSRF protection token.
  """
  when = when or int(time.time())
  digester = hmac.new(key)
  digester.update(str(user_id))
  digester.update(DELIMITER)
  digester.update(action_id)
  digester.update(DELIMITER)
  digester.update(str(when))
  digest = digester.digest()

  token = base64.urlsafe_b64encode('%s%s%d' % (digest,
                                               DELIMITER,
                                               when))
  return token


@util.positional(3)
def validate_token(key, token, user_id, action_id="", current_time=None):
  """Validates that the given token authorizes the user for the action.

  Tokens are invalid if the time of issue is too old or if the token
  does not match what generateToken outputs (i.e. the token was forged).

  Args:
    key: secret key to use.
    token: a string of the token generated by generateToken.
    user_id: the user ID of the authenticated user.
    action_id: a string identifier of the action they requested
      authorization for.

  Returns:
    A boolean - True if the user is authorized for the action, False
    otherwise.
  """
  if not token:
    return False
  try:
    decoded = base64.urlsafe_b64decode(str(token))
    token_time = long(decoded.split(DELIMITER)[-1])
  except (TypeError, ValueError):
    return False
  if current_time is None:
    current_time = time.time()
  # If the token is too old it's not valid.
  if current_time - token_time > DEFAULT_TIMEOUT_SECS:
    return False

  # The given token should match the generated one with the same time.
  expected_token = generate_token(key, user_id, action_id=action_id,
                                  when=token_time)
  if len(token) != len(expected_token):
    return False

  # Perform constant time comparison to avoid timing attacks
  different = 0
  for x, y in zip(token, expected_token):
    different |= ord(x) ^ ord(y)
  if different:
    return False

  return True

########NEW FILE########
__FILENAME__ = main
#!/usr/bin/python

# Copyright (C) 2013 Gerwin Sturm, FoldedSoft e.U.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""RequestHandlers for Glass emulator and Demo services"""

__author__ = 'scarygami@gmail.com (Gerwin Sturm)'

# Add the library location to the path
import sys
sys.path.insert(0, 'lib')

from utils import config
import webapp2

from service.auth import AUTH_ROUTES
from service.notify import NOTIFY_ROUTES
from service.service import SERVICE_ROUTES
from demos import DEMO_ROUTES

ROUTES = (AUTH_ROUTES + SERVICE_ROUTES + NOTIFY_ROUTES + DEMO_ROUTES)

# Remove the next two lines if you don't want to host a Glass emulator
from emulator.glass import GLASS_ROUTES
ROUTES = (ROUTES + GLASS_ROUTES)

app = webapp2.WSGIApplication(ROUTES, debug=True, config=config)

########NEW FILE########
__FILENAME__ = api
#!/usr/bin/python

# Copyright (C) 2013 Gerwin Sturm, FoldedSoft e.U.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
sys.path.insert(0, 'endpoints-proto-datastore')

import endpoints
from mirror_api import MirrorApi

ApiServer = endpoints.api_server([MirrorApi], restricted=False)

########NEW FILE########
__FILENAME__ = mirror_api
#!/usr/bin/python

# Copyright (C) 2013 Gerwin Sturm, FoldedSoft e.U.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Mirror API implemented using Google Cloud Endpoints."""

# Add the library location to the path
import sys
sys.path.insert(0, 'lib')

import cloudstorage as gcs
import endpoints
import json
import os
import logging
import sys
import urllib2

from google.appengine.api import app_identity
from google.appengine.api import channel
from google.appengine.ext import ndb
from protorpc import remote

from models import TimelineItem
from models import MenuAction
from models import UserAction
from models import Operation
from models import Contact
from models import Subscription
from models import Action
from models import ActionResponse
from models import Location
from models import AttachmentListRequest
from models import AttachmentRequest
from models import AttachmentResponse
from models import AttachmentList


_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SECRETS_PATH = os.path.join(_ROOT_DIR, "client_secrets.json")
_CLIENT_IDs = [endpoints.API_EXPLORER_CLIENT_ID]

my_default_retry_params = gcs.RetryParams(initial_delay=0.2,
                                          max_delay=5.0,
                                          backoff_factor=2,
                                          max_retry_period=15)

gcs.set_default_retry_params(my_default_retry_params)

bucket = "/" + os.environ.get("BUCKET_NAME", app_identity.get_default_gcs_bucket_name())

with open(_SECRETS_PATH, "r") as fh:
    _secrets = json.load(fh)["web"]
    _CLIENT_IDs.append(_secrets["client_id"])
    if "additional_client_ids" in _secrets:
        _CLIENT_IDs.extend(_secrets["additional_client_ids"])

API_DESCRIPTION = ("Mirror API implemented using Google Cloud "
                   "Endpoints for testing")


@endpoints.api(name="mirror", version="v1",
               description=API_DESCRIPTION,
               allowed_client_ids=_CLIENT_IDs,
               hostname=app_identity.get_application_id() + ".appspot.com")
class MirrorApi(remote.Service):
    """Class which defines the Mirror API v1."""

    @TimelineItem.query_method(query_fields=("maxResults", "pageToken", "bundleId", "includeDeleted", "pinnedOnly", "sourceItemId"),
                               user_required=True,
                               path="timeline", name="timeline.list")
    def timeline_list(self, query):
        """List timeline cards for the current user."""

        query = query.order(-TimelineItem.updated)
        query = query.filter(TimelineItem.user == endpoints.get_current_user())
        return query

    @TimelineItem.method(request_fields=("id",),
                         user_required=True,
                         path="timeline/{id}", http_method="GET",
                         name="timeline.get")
    def timeline_get(self, card):
        """Get card with ID for the current user"""

        if not card.from_datastore or card.user != endpoints.get_current_user():
            raise endpoints.NotFoundException("Card not found.")

        return card

    @TimelineItem.method(user_required=True, http_method="POST",
                         path="timeline", name="timeline.insert")
    def timeline_insert(self, card):
        """Insert a card for the current user."""

        if card.id is not None:
            raise endpoints.BadRequestException("ID is not allowed in request body.")

        if card.menuItems is not None:
            for menuItem in card.menuItems:
                if menuItem.action == MenuAction.CUSTOM:
                    if menuItem.id is None:
                        raise endpoints.BadRequestException("For custom actions id needs to be provided.")
                    if menuItem.values is None or len(menuItem.values) == 0:
                        raise endpoints.BadRequestException("For custom actions at least one value needs to be provided.")
                    for value in menuItem.values:
                        if value.displayName is None or value.iconUrl is None:
                            raise endpoints.BadRequestException("Each value needs to contain displayName and iconUrl.")

        card.isDeleted = False

        card.put()

        channel.send_message(card.user.email(), json.dumps({"id": card.id}))

        return card

    @TimelineItem.method(user_required=True, http_method="POST",
                         path="internal/timeline", name="internal.timeline.insert")
    def timeline_internal_insert(self, card):
        """Insert a card for the current user. Internal method for the Emulator to work.
        Not part of the actual Mirror API and shouldn't be used.
        """

        if card.id is not None:
            raise endpoints.BadRequestException("ID is not allowed in request body.")

        if card.menuItems is not None:
            for menuItem in card.menuItems:
                if menuItem.action == MenuAction.CUSTOM:
                    if menuItem.id is None:
                        raise endpoints.BadRequestException("For custom actions id needs to be provided.")
                    if menuItem.values is None or len(menuItem.values) == 0:
                        raise endpoints.BadRequestException("For custom actions at least one value needs to be provided.")
                    for value in menuItem.values:
                        if value.displayName is None or value.iconUrl is None:
                            raise endpoints.BadRequestException("Each value needs to contain displayName and iconUrl.")

        card.isDeleted = False

        card.put()

        return card

    @TimelineItem.method(user_required=True,
                         path="timeline/{id}", http_method="PUT",
                         name="timeline.update")
    def timeline_update(self, card):
        """Update card with ID for the current user"""

        if not card.from_datastore or card.user != endpoints.get_current_user():
            raise endpoints.NotFoundException("Card not found.")

        if card.isDeleted:
            raise endpoints.NotFoundException("Card has been deleted")

        card.put()

        channel.send_message(card.user.email(), json.dumps({"id": card.id}))

        return card

    @TimelineItem.method(user_required=True,
                         path="internal/timeline/{id}", http_method="PUT",
                         name="internal.timeline.update")
    def timeline_internal_update(self, card):
        """Update card with ID for the current user.  Internal method for the Emulator to work.
        Not part of the actual Mirror API and shouldn't be used.
        """

        if not card.from_datastore or card.user != endpoints.get_current_user():
            raise endpoints.NotFoundException("Card not found.")

        if card.isDeleted:
            raise endpoints.NotFoundException("Card has been deleted")

        card.put()

        channel.send_message(card.user.email(), json.dumps({"id": card.id}))

        return card

    @TimelineItem.method(request_fields=("id",),
                         response_fields=("id",),
                         user_required=True,
                         path="timeline/{id}", http_method="DELETE",
                         name="timeline.delete")
    def timeline_delete(self, card):
        """Remove an existing card for the current user.

        This will set all properties except the ID to None and set isDeleted to true
        """

        if not card.from_datastore or card.user != endpoints.get_current_user():
            raise endpoints.NotFoundException("Contact not found.")

        if card.isDeleted:
            raise endpoints.NotFoundException("Card has been deleted")

        # Delete attachments
        if card.attachments is not None:
            for att in card.attachments:
                try:
                    gcs.delete(bucket + "/" + att.id)
                except gcs.NotFoundError:
                    pass

        card.attachments = []
        card.bundleId = None
        card.canonicalUrl = None
        card.created = None
        card.creator = None
        card.displayTime = None
        card.html = None
        card.inReplyTo = None
        card.isBundleCover = None
        card.isPinned = None
        card.menuItems = []
        card.notification = None
        card.recipients = []
        card.sourceItemId = None
        card.speakableType = None
        card.speakableText = None
        card.text = None
        card.title = None
        card.updated = None
        card.isDeleted = True
        card.put()

        # Notify Glass emulator
        channel.send_message(card.user.email(), json.dumps({"id": card.id}))

        # Notify timeline DELETE subscriptions
        data = {}
        data["collection"] = "timeline"
        data["itemId"] = card.id
        operation = Operation.DELETE
        data["operation"] = operation.name

        header = {"Content-type": "application/json"}

        query = Subscription.query().filter(Subscription.user == endpoints.get_current_user())
        query = query.filter(Subscription.collection == "timeline")
        query = query.filter(Subscription.operation == operation)
        for subscription in query.fetch():
            data["userToken"] = subscription.userToken
            data["verifyToken"] = subscription.verifyToken

            req = urllib2.Request(subscription.callbackUrl, json.dumps(data), header)
            try:
                urllib2.urlopen(req)
            except:
                logging.error(sys.exc_info()[0])

        return card

    @Contact.query_method(user_required=True,
                          path="contacts", name="contacts.list")
    def contacts_list(self, query):
        """List all Contacts registered for the current user."""

        return query.filter(Contact.user == endpoints.get_current_user())

    @Contact.method(request_fields=("id",),
                    user_required=True,
                    path="contacts/{id}", http_method="GET",
                    name="contacts.get")
    def contacts_get(self, contact):
        """Get contact with ID for the current user"""

        if not contact.from_datastore or contact.user != endpoints.get_current_user():
            raise endpoints.NotFoundException("Contact not found.")

        return contact

    @Contact.method(user_required=True,
                    path="contacts", name="contacts.insert")
    def contacts_insert(self, contact):
        """Insert a new Contact for the current user."""

        if contact.id is None:
            raise endpoints.BadRequestException("ID needs to be provided.")
        if contact.displayName is None:
            raise endpoints.BadRequestException("displayName needs to be provided.")
        if contact.imageUrls is None or len(contact.imageUrls) == 0:
            raise endpoints.BadRequestException("At least one imageUrl needs to be provided.")

        if contact.from_datastore:
            return contact

        contact.put()
        return contact

    @Contact.method(request_fields=("id",),
                    response_fields=("id",),
                    user_required=True,
                    path="contacts/{id}", http_method="DELETE",
                    name="contacts.delete")
    def contacts_delete(self, contact):
        """Remove an existing Contact for the current user."""

        if not contact.from_datastore or contact.user != endpoints.get_current_user():
            raise endpoints.NotFoundException("Contact not found.")

        contact.key.delete()

        return contact

    @Contact.method(user_required=True,
                    path="contacts/{id}", http_method="PUT",
                    name="contacts.update")
    def contacts_update(self, contact):
        """Update Contact with ID for the current user"""

        if not contact.from_datastore or contact.user != endpoints.get_current_user():
            raise endpoints.NotFoundException("Card not found.")

        contact.put()
        return contact

    @Subscription.query_method(user_required=True,
                               path="subscriptions", name="subscriptions.list")
    def subscriptions_list(self, query):
        """List all Subscriptions registered for the current user."""

        return query.filter(Contact.user == endpoints.get_current_user())

    @Subscription.method(user_required=True, http_method="POST",
                         path="subscriptions", name="subscriptions.insert")
    def subscription_insert(self, subscription):
        """Insert a new subscription for the current user."""

        if subscription.id is not None:
            raise endpoints.BadRequestException("ID is not allowed in request body.")

        if subscription.operation is None or len(subscription.operation) == 0:
            subscription.operation = [Operation.UPDATE, Operation.INSERT, Operation.DELETE]

        subscription.put()
        return subscription

    @Subscription.method(request_fields=("id",),
                         response_fields=("id",),
                         user_required=True,
                         path="subscriptions/{id}", http_method="DELETE",
                         name="subscriptions.delete")
    def subscription_delete(self, subscription):
        """Remove an existing subscription for the current user."""

        if not subscription.from_datastore or subscription.user != endpoints.get_current_user():
            raise endpoints.NotFoundException("Card not found.")

        subscription.key.delete()

        return subscription

    @Location.query_method(user_required=True,
                           path="locations", name="locations.list")
    def locations_list(self, query):
        """List locations for the current user."""

        query = query.order(-Location.timestamp)
        return query.filter(TimelineItem.user == endpoints.get_current_user())

    @Location.method(request_fields=("id",),
                     user_required=True,
                     path="locations/{id}", http_method="GET",
                     name="locations.get")
    def locations_get(self, location):
        """Retrieve a single location for the current user.

        ID can be a specific location ID or "latest" to retrieve the
        latest known position of the user.
        """

        if not location.from_datastore or location.user != endpoints.get_current_user():
            raise endpoints.NotFoundException("Location not found.")

        return location

    @Location.method(user_required=True, http_method="POST",
                     path="internal/locations", name="internal.locations.insert")
    def locations_insert(self, location):
        """Insert a new location for the current user.

        Not part of the actual mirror API but used by the emulator.
        """

        if location.id is not None:
            raise endpoints.BadRequestException("ID is not allowed in request body.")

        location.put()

        # Notify location subscriptions

        data = {}
        data["collection"] = "locations"
        data["itemId"] = "latest"
        operation = Operation.UPDATE
        data["operation"] = operation.name

        header = {"Content-type": "application/json"}

        query = Subscription.query().filter(Subscription.user == endpoints.get_current_user())
        query = query.filter(Subscription.collection == "locations")
        query = query.filter(Subscription.operation == operation)
        for subscription in query.fetch():
            data["userToken"] = subscription.userToken
            data["verifyToken"] = subscription.verifyToken

            req = urllib2.Request(subscription.callbackUrl, json.dumps(data), header)
            try:
                urllib2.urlopen(req)
            except:
                logging.error(sys.exc_info()[0])

        return location

    @endpoints.method(AttachmentListRequest, AttachmentList,
                      path="timeline/{itemId}/attachments", http_method="GET",
                      name="timeline.attachments.list")
    def attachments_list(self, request):
        """Retrieve attachments for a timeline card"""

        current_user = endpoints.get_current_user()
        if current_user is None:
            raise endpoints.UnauthorizedException("Authentication required.")

        card = ndb.Key("TimelineItem", request.itemId).get()

        if card is None or card.user != current_user:
            raise endpoints.NotFoundException("Card not found.")

        attachments = []

        if card.attachments is not None:
            for att in card.attachments:
                attachments.append(AttachmentResponse(id=att.id,
                                                      contentType=att.contentType,
                                                      contentUrl=att.contentUrl,
                                                      isProcessingContent=att.isProcessingContent))

        return AttachmentList(items=attachments)

    @endpoints.method(AttachmentRequest, AttachmentResponse,
                      path="timeline/{itemId}/attachments/{attachmentId}", http_method="GET",
                      name="timeline.attachments.get")
    def attachments_get(self, request):
        """Retrieve metainfo for a single attachments for a timeline card"""

        current_user = endpoints.get_current_user()
        if current_user is None:
            raise endpoints.UnauthorizedException("Authentication required.")

        card = ndb.Key("TimelineItem", request.itemId).get()

        if card is None or card.user != current_user:
            raise endpoints.NotFoundException("Attachment not found.")

        if card.attachments is not None:
            for att in card.attachments:
                if att.id == request.attachmentId:
                    return AttachmentResponse(id=att.id,
                                              contentType=att.contentType,
                                              contentUrl=att.contentUrl,
                                              isProcessingContent=att.isProcessingContent)

        raise endpoints.NotFoundException("Attachment not found.")

    @endpoints.method(AttachmentRequest, AttachmentResponse,
                      path="timeline/{itemId}/attachments/{attachmentId}", http_method="DELETE",
                      name="timeline.attachments.delete")
    def attachments_delete(self, request):
        """Remove single attachment for a timeline card"""

        current_user = endpoints.get_current_user()
        if current_user is None:
            raise endpoints.UnauthorizedException("Authentication required.")

        card = ndb.Key("TimelineItem", request.itemId).get()

        if card is None or card.user != current_user:
            raise endpoints.NotFoundException("Attachment not found.")

        if card.attachments is not None:
            for att in card.attachments:
                if att.id == request.attachmentId:
                    # Delete attachment from blobstore
                    try:
                        gcs.delete(bucket + "/" + att.id)
                    except gcs.NotFoundError:
                        pass

                    # Remove attachment from timeline card
                    card.attachments.remove(att)
                    card.put()

                    return AttachmentResponse(id=att.id)

        raise endpoints.NotFoundException("Attachment not found.")

    @endpoints.method(Action, ActionResponse,
                      path="internal/actions", http_method="POST",
                      name="internal.actions.insert")
    def action_insert(self, action):
        """Perform an action on a timeline card for the current user.

        This isn't part of the actual Mirror API but necessary for the emulator
        to send actions to the subscribed services.

        Returns just a simple success message
        """

        current_user = endpoints.get_current_user()
        if current_user is None:
            raise endpoints.UnauthorizedException("Authentication required.")

        card = ndb.Key("TimelineItem", action.itemId).get()
        if card is None or card.user != current_user:
            raise endpoints.NotFoundException("Card not found.")

        data = None
        operation = None

        if action.action == UserAction.SHARE:
            operation = Operation.UPDATE
            data = {}
            data["collection"] = "timeline"
            data["itemId"] = action.itemId
            data["operation"] = operation.name
            data["userActions"] = [{"type": UserAction.SHARE.name}]

        if action.action == UserAction.REPLY or action.action == UserAction.REPLY_ALL:
            operation = Operation.INSERT
            data = {}
            data["collection"] = "timeline"
            data["itemId"] = action.itemId
            data["operation"] = operation.name
            data["userActions"] = [{"type": UserAction.REPLY.name}]

        if action.action == UserAction.DELETE:
            operation = Operation.DELETE
            data = {}
            data["collection"] = "timeline"
            data["itemId"] = action.itemId
            data["operation"] = operation.name
            data["userActions"] = [{"type": UserAction.DELETE.name}]

        if action.action == UserAction.CUSTOM:
            operation = Operation.UPDATE
            data = {}
            data["collection"] = "timeline"
            data["itemId"] = action.itemId
            data["operation"] = operation.name
            data["userActions"] = [{"type": UserAction.CUSTOM.name, "payload": action.value}]

        if action.action == UserAction.LAUNCH:
            operation = Operation.INSERT
            data = {}
            data["collection"] = "timeline"
            data["itemId"] = action.itemId
            data["operation"] = operation.name
            data["userActions"] = [{"type": UserAction.LAUNCH.name}]

        if data is not None and operation is not None:
            header = {"Content-type": "application/json"}

            query = Subscription.query().filter(Subscription.user == current_user)
            query = query.filter(Subscription.collection == "timeline")
            query = query.filter(Subscription.operation == operation)
            for subscription in query.fetch():
                data["userToken"] = subscription.userToken
                data["verifyToken"] = subscription.verifyToken

                req = urllib2.Request(subscription.callbackUrl, json.dumps(data), header)
                try:
                    urllib2.urlopen(req)
                except:
                    logging.error(sys.exc_info()[0])

        # Report back to Glass emulator
        channel.send_message(current_user.email(), json.dumps({"id": action.itemId}))

        return ActionResponse(success=True)

########NEW FILE########
__FILENAME__ = models
#!/usr/bin/python

# Copyright (C) 2013 Gerwin Sturm, FoldedSoft e.U.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Model definition for the Mirror API."""

import sys
sys.path.insert(1, 'endpoints-proto-datastore')

import endpoints

from google.appengine.ext import ndb
from google.appengine.ext.ndb import msgprop
from protorpc import messages
from protorpc import message_types

from endpoints_proto_datastore.ndb import EndpointsDateTimeProperty
from endpoints_proto_datastore.ndb import EndpointsModel
from endpoints_proto_datastore.ndb import EndpointsUserProperty
from endpoints_proto_datastore.ndb import EndpointsAliasProperty


class MenuAction(messages.Enum):
    REPLY = 1
    REPLY_ALL = 2
    DELETE = 3
    SHARE = 4
    READ_ALOUD = 5
    VOICE_CALL = 6
    NAVIGATE = 7
    TOGGLE_PINNED = 8
    CUSTOM = 9
    VIEW_WEBSITE = 10
    PLAY_VIDEO = 11


class MenuValue(EndpointsModel):

    class MenuValueState(messages.Enum):
        DEFAULT = 1
        PENDING = 2
        CONFIRMED = 3

    displayName = ndb.StringProperty(required=True)
    iconUrl = ndb.StringProperty(required=True)
    state = msgprop.EnumProperty(MenuValueState)


class MenuItem(EndpointsModel):
    action = msgprop.EnumProperty(MenuAction, required=True)
    id = ndb.StringProperty()
    payload = ndb.StringProperty()
    removeWhenSelected = ndb.BooleanProperty(default=False)
    values = ndb.LocalStructuredProperty(MenuValue, repeated=True)


class Location(EndpointsModel):
    """Model for location"""

    _latest = False

    _message_fields_schema = (
        "id",
        "timestamp",
        "latitude",
        "longitude",
        "accuracy",
        "displayName",
        "address"
    )

    user = EndpointsUserProperty(required=True, raise_unauthorized=True)
    timestamp = EndpointsDateTimeProperty(auto_now_add=True)
    latitude = ndb.FloatProperty()
    longitude = ndb.FloatProperty()
    accuracy = ndb.FloatProperty()
    displayName = ndb.StringProperty()
    address = ndb.StringProperty()

    def IdSet(self, value):
        if not isinstance(value, basestring):
            raise TypeError("ID must be a string.")

        if value == "latest":
            self._latest = True
            loc_query = Location.query().order(-Location.timestamp)
            loc_query = loc_query.filter(Location.user == self.user)
            loc = loc_query.get()
            if loc is not None:
                self.UpdateFromKey(loc.key)
            return

        if value.isdigit():
            self.UpdateFromKey(ndb.Key(Location, int(value)))

    @EndpointsAliasProperty(setter=IdSet, required=False)
    def id(self):
        if self._latest:
            return "latest"
        if self.key is not None:
            return str(self.key.integer_id())


class TimelineItem(EndpointsModel):
    """Model for timeline cards.

    Since the created property is auto_now_add=True, Cards will document when
    they were inserted immediately after being stored.
    """

    class Attachment(EndpointsModel):
        """Represents media content, such as a photo, that can be attached to a timeline item."""
        id = ndb.StringProperty()
        contentType = ndb.StringProperty()
        contentUrl = ndb.StringProperty()
        isProcessingContent = ndb.BooleanProperty(default=False)

    class TimelineContact(EndpointsModel):
        """A person or group that can be used as a creator or a contact."""

        class ContactType(messages.Enum):
            INDIVIDUAL = 1
            GROUP = 2

        acceptTypes = ndb.StringProperty(repeated=True)
        displayName = ndb.StringProperty()
        id = ndb.StringProperty(required=True)
        imageUrls = ndb.StringProperty(repeated=True)
        phoneNumber = ndb.StringProperty()
        source = ndb.StringProperty()
        type = msgprop.EnumProperty(ContactType)

    class Notification(EndpointsModel):

        level = ndb.StringProperty(default="DEFAULT")
        deliveryTime = EndpointsDateTimeProperty()

    _message_fields_schema = (
        "id",
        "attachments",
        "bundleId",
        "canonicalUrl",
        "created",
        "creator",
        "displayTime",
        "html",
        "inReplyTo",
        "isBundleCover",
        "isDeleted",
        "isPinned",
        "location",
        "menuItems",
        "notification",
        "pinScore",
        "recipients",
        "sourceItemId",
        "speakableText",
        "speakableType",
        "text",
        "title",
        "updated"
    )

    user = EndpointsUserProperty(required=True, raise_unauthorized=True)

    attachments = ndb.LocalStructuredProperty(Attachment, repeated=True)
    bundleId = ndb.StringProperty()
    canonicalUrl = ndb.StringProperty()
    created = EndpointsDateTimeProperty(auto_now_add=True)
    creator = ndb.LocalStructuredProperty(TimelineContact)
    displayTime = EndpointsDateTimeProperty()
    html = ndb.TextProperty()
    inReplyTo = ndb.IntegerProperty()
    isBundleCover = ndb.BooleanProperty()
    isDeleted = ndb.BooleanProperty()
    isPinned = ndb.BooleanProperty()
    location = ndb.LocalStructuredProperty(Location)
    menuItems = ndb.LocalStructuredProperty(MenuItem, repeated=True)
    notification = ndb.LocalStructuredProperty(Notification)
    pinScore = ndb.IntegerProperty()
    recipients = ndb.LocalStructuredProperty(TimelineContact, repeated=True)
    sourceItemId = ndb.StringProperty()
    speakableText = ndb.TextProperty()
    speakableType = ndb.TextProperty()
    text = ndb.StringProperty()
    title = ndb.StringProperty()
    updated = EndpointsDateTimeProperty(auto_now=True)

    def IncludeDeletedSet(self, value):
        """
        If value is true all timelineItems will be returned.
        Otherwise a filter for non-deleted items is necessary for the query.
        """
        if value is None or value is False:
            self._endpoints_query_info._AddFilter(TimelineItem.isDeleted == False)

    @EndpointsAliasProperty(setter=IncludeDeletedSet, property_type=messages.BooleanField, default=False)
    def includeDeleted(self):
        """
        includedDeleted is only used as parameter in query_methods
        so there should never be a reason to actually retrieve the value
        """
        return None

    def PinnedOnlySet(self, value):
        """
        If value is true only pinned timelineItems will be returned.
        Otherwise all timelineItems are returned.
        """
        if value is True:
            self._endpoints_query_info._AddFilter(TimelineItem.isPinned == True)

    @EndpointsAliasProperty(setter=PinnedOnlySet, property_type=messages.BooleanField, default=False)
    def pinnedOnly(self):
        """
        pinnedOnly is only used as parameter in query_methods
        so there should never be a reason to actually retrieve the value
        """
        return None

    def MaxResultsSet(self, value):
        """Setter to be used for default limit EndpointsAliasProperty.

        Simply sets the limit on the entity's query info object, and the query
        info object handles validation.

        Args:
          value: The limit value to be set.
        """
        self._endpoints_query_info.limit = value

    @EndpointsAliasProperty(setter=MaxResultsSet, property_type=messages.IntegerField, default=20)
    def maxResults(self):
        """Getter to be used for default limit EndpointsAliasProperty.

        Uses the ProtoRPC property_type IntegerField since a limit.

        Returns:
          The integer (or null) limit from the query info on the entity.
        """
        return self._endpoints_query_info.limit


class Contact(EndpointsModel):
    """A person or group that can be used as a creator or a contact."""

    class Command(EndpointsModel):

        class CommandType(messages.Enum):
            TAKE_A_NOTE = 1
            POST_AN_UPDATE = 2

        """A single menu command that is part of a Contact."""
        type = msgprop.EnumProperty(CommandType, required=True)

    class ContactType(messages.Enum):
        INDIVIDUAL = 1
        GROUP = 2

    _message_fields_schema = (
        "id",
        "acceptCommands",
        "acceptTypes",
        "displayName",
        "imageUrls",
        "phoneNumber",
        "priority",
        "source",
        "type"
    )

    user = EndpointsUserProperty(required=True, raise_unauthorized=True)

    acceptCommands = ndb.LocalStructuredProperty(Command, repeated=True)
    acceptTypes = ndb.StringProperty(repeated=True)
    displayName = ndb.StringProperty(required=True)
    imageUrls = ndb.StringProperty(repeated=True)
    phoneNumber = ndb.StringProperty()
    priority = ndb.IntegerProperty()
    source = ndb.StringProperty()
    speakableName = ndb.StringProperty()
    type = msgprop.EnumProperty(ContactType)

    def IdSet(self, value):
        if not isinstance(value, basestring):
            raise TypeError("ID must be a string.")

        self.UpdateFromKey(ndb.Key("User", self.user.email(), Contact, value))

    @EndpointsAliasProperty(setter=IdSet, required=True)
    def id(self):
        if self.key is not None:
            return self.key.pairs()[1][1]


class Operation(messages.Enum):
    UPDATE = 1
    INSERT = 2
    DELETE = 3


class Subscription(EndpointsModel):
    """Model for subscriptions"""

    _message_fields_schema = ("id", "collection", "userToken", "verifyToken", "operation", "callbackUrl")

    user = EndpointsUserProperty(required=True, raise_unauthorized=True)
    collection = ndb.StringProperty(required=True)
    userToken = ndb.StringProperty(required=True)
    verifyToken = ndb.StringProperty(required=True)
    operation = msgprop.EnumProperty(Operation, repeated=True)
    callbackUrl = ndb.StringProperty(required=True)


class UserAction(messages.Enum):
    """Represents an action taken by the user that triggers a notification."""
    REPLY = 1
    REPLY_ALL = 2
    DELETE = 3
    SHARE = 4
    PIN = 5
    UNPIN = 6
    LAUNCH = 7
    CUSTOM = 10


class Action(messages.Message):
    """ProtoRPC Message Class for actions performed on timeline cards

    Since those actions are directly forwarded to subscriptions they
    don't need to be saved to the data store, hence no EndpointsModel class
    """

    collection = messages.StringField(1, default="timeline")
    itemId = messages.IntegerField(2, required=True)
    action = messages.EnumField(UserAction, 3, required=True)
    value = messages.StringField(4)


class ActionResponse(messages.Message):
    """Simple response to actions send to the Mirror API"""
    success = messages.BooleanField(1, default=True)


AttachmentListRequest = endpoints.ResourceContainer(
    message_types.VoidMessage,
    itemId=messages.IntegerField(2, required=True))


AttachmentRequest = endpoints.ResourceContainer(
    message_types.VoidMessage,
    itemId=messages.IntegerField(2, required=True),
    attachmentId=messages.StringField(3, required=True))


class AttachmentResponse(messages.Message):
    id = messages.StringField(1)
    contentType = messages.StringField(2)
    contentUrl = messages.StringField(3)
    isProcessingContent = messages.BooleanField(4, default=False)


class AttachmentList(messages.Message):
    items = messages.MessageField(AttachmentResponse, 1, repeated=True)

########NEW FILE########
__FILENAME__ = upload
#!/usr/bin/python

# Copyright (C) 2013 Gerwin Sturm, FoldedSoft e.U.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Handle multipart and simple uploads to the API"""

__author__ = 'scarygami@gmail.com (Gerwin Sturm)'

# Add the library location to the path
import sys
sys.path.insert(0, 'lib')

import cloudstorage as gcs
import email
import httplib2
import json
import os
import utils
import uuid
import webapp2

from google.appengine.api import app_identity
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers

from apiclient.discovery import build
from apiclient.errors import HttpError
from oauth2client.client import AccessTokenCredentials

my_default_retry_params = gcs.RetryParams(initial_delay=0.2,
                                          max_delay=5.0,
                                          backoff_factor=2,
                                          max_retry_period=15)

gcs.set_default_retry_params(my_default_retry_params)

bucket = "/" + os.environ.get("BUCKET_NAME", app_identity.get_default_gcs_bucket_name())

class UploadHandler(webapp2.RequestHandler):

    _metainfo = None
    _content_type = None
    _content = None
    _token = None
    _service = None

    def dispatch(self):
        self._checkauth()
        self._decode()
        if self._token is None:
            self.abort(401)
        else:
            credentials = AccessTokenCredentials(self._token, "mirror-api-upload-handler/1.0")
            http = httplib2.Http()
            http = credentials.authorize(http)
            http.timeout = 60
            self._service = build("mirror", "v1", http=http, discoveryServiceUrl=utils.discovery_service_url)
            super(UploadHandler, self).dispatch()

    def _checkauth(self):
        if "Authorization" in self.request.headers:
            self._token = self.request.headers["Authorization"].split(" ")[1]

    def _decode(self):
        """Check for valid content types and decode data accordingly"""

        content_type = self.request.content_type
        if content_type == "multipart/related" or content_type == "multipart/mixed":
            # Attach content-type header to body so that email library can decode it correctly
            message = "Content-Type: " + self.request.headers["Content-Type"] + "\r\n"
            message += self.request.body

            msg = email.message_from_string(message)

            if not msg.is_multipart():
                return

            for payload in msg.get_payload():
                content_type = payload.get_content_type()
                if content_type.startswith("image/") or content_type.startswith("audio/") or content_type.startswith("video/"):
                    if self._content is None:
                        self._content_type = content_type
                        self._content = payload.get_payload(decode=True)
                elif content_type == "application/json":
                    if self._metainfo is None:
                        self._metainfo = json.loads(payload.get_payload())

            return

        if content_type.startswith("image/") or content_type.startswith("audio/") or content_type.startswith("video/"):
            self._content_type = content_type
            if "Content-Transfer-Encoding" in self.request.headers and self.request.headers["Content-Transfer-Encoding"].lower() == "base64":
                self._content = self.request.body.decode("base64")
            else:
                self._content = self.request.body


class InsertHandler(UploadHandler):

    def post(self):

        self.response.content_type = "application/json"

        if self._content is None:
            self.response.status = 400
            self.response.out.write(utils.createError(400, "Couldn't decode content or invalid content-type"))

        # 1) Insert new card using
        if self._metainfo is None:
            request = self._service.internal().timeline().insert(body={})
        else:
            request = self._service.internal().timeline().insert(body=self._metainfo)

        try:
            card = request.execute()
        except HttpError as e:
            self.response.status = e.resp.status
            self.response.out.write(e.content)
            return

        # 2) Insert data into cloud storage
        write_retry_params = gcs.RetryParams(backoff_factor=1.1)
        file_name = str(uuid.uuid4())
        gcs_file = gcs.open(bucket + "/" + file_name,
                        'w',
                        content_type=self._content_type,
                        retry_params=write_retry_params)
        gcs_file.write(self._content)
        gcs_file.close()

        # 3) Update card with attachment info
        if not "attachments" in card:
            card["attachments"] = []

        attachment = {
            "id": file_name,
            "contentType": self._content_type,
            "contentUrl": "%s/upload/mirror/v1/timeline/%s/attachments/%s" % (utils.base_url, card["id"], file_name),
            "isProcessing": False
        }

        card["attachments"].append(attachment)

        request = self._service.internal().timeline().update(id=card["id"], body=card)

        try:
            result = request.execute()
        except HttpError as e:
            self.response.status = e.resp.status
            self.response.out.write(e.content)
            return

        self.response.status = 200
        self.response.out.write(json.dumps(result))


class UpdateHandler(UploadHandler):

    def put(self, id):

        self.response.content_type = "application/json"

        if self._content is None:
            self.response.status = 400
            self.response.out.write(utils.createError(400, "Couldn't decode content or invalid content-type"))

        # Trying to access card to see if user is allowed to
        request = self._service.timeline().get(id=id)
        try:
            card = request.execute()
        except HttpError as e:
            self.response.status = e.resp.status
            self.response.out.write(e.content)
            return

        # 2) Insert data into cloud storage
        write_retry_params = gcs.RetryParams(backoff_factor=1.1)
        file_name = str(uuid.uuid4())
        gcs_file = gcs.open(bucket + "/" + file_name,
                        'w',
                        content_type=self._content_type,
                        retry_params=write_retry_params)
        gcs_file.write(self._content)
        gcs_file.close()

        # 3) Update card with attachment info and new metainfo
        if self._metainfo is None:
            new_card = {}
        else:
            new_card = self._metainfo

        if "attachments" in card:
            new_card["attachments"] = card["attachments"]
        else:
            new_card["attachments"] = []

        attachment = {
            "id": file_name,
            "contentType": self._content_type,
            "contentUrl": "%s/upload/mirror/v1/timeline/%s/attachments/%s" % (utils.base_url, card["id"], file_name),
            "isProcessing": False
        }

        new_card["attachments"].append(attachment)

        request = self._service.internal().timeline().update(id=card["id"], body=new_card)

        try:
            result = request.execute()
        except HttpError as e:
            self.response.status = e.resp.status
            self.response.out.write(e.content)
            return

        self.response.status = 200
        self.response.out.write(json.dumps(result))


class AttachmentInsertHandler(UploadHandler):

    def post(self, id):

        self.response.content_type = "application/json"

        if self._content is None:
            self.response.status = 400
            self.response.out.write(utils.createError(400, "Couldn't decode content or invalid content-type"))

        # Trying to access card to see if user is allowed to
        request = self._service.timeline().get(id=id)
        try:
            card = request.execute()
        except HttpError as e:
            self.response.status = e.resp.status
            self.response.out.write(e.content)
            return

        # 2) Insert data into cloud storage
        write_retry_params = gcs.RetryParams(backoff_factor=1.1)
        file_name = str(uuid.uuid4())
        gcs_file = gcs.open(bucket + "/" + file_name,
                        'w',
                        content_type=self._content_type,
                        retry_params=write_retry_params)
        gcs_file.write(self._content)
        gcs_file.close()

        # 3) Update card with attachment info
        if not "attachments" in card:
            card["attachments"] = []

        attachment = {
            "id": file_name,
            "contentType": self._content_type,
            "contentUrl": "%s/upload/mirror/v1/timeline/%s/attachments/%s" % (utils.base_url, card["id"], file_name),
            "isProcessing": False
        }

        card["attachments"].append(attachment)

        request = self._service.internal().timeline().update(id=card["id"], body=card)

        try:
            result = request.execute()
        except HttpError as e:
            self.response.status = e.resp.status
            self.response.out.write(e.content)
            return

        self.response.status = 200
        self.response.out.write(json.dumps(result))


class DownloadHandler(UploadHandler, blobstore_handlers.BlobstoreDownloadHandler):

    def get(self, id, attachment):

        # Trying to access card to see if user is allowed to
        request = self._service.timeline().get(id=id)
        try:
            request.execute()
        except HttpError as e:
            self.response.status = e.resp.status
            self.response.out.write(e.content)
            return

        blob_key = blobstore.create_gs_key("/gs" + bucket + "/" + attachment)
        self.send_blob(blob_key)


app = webapp2.WSGIApplication(
    [
        (r"/upload/mirror/v1/timeline/(.*)/attachments/(.*)", DownloadHandler),
        (r"/upload/mirror/v1/timeline/(.*)/attachments", AttachmentInsertHandler),
        (r"/upload/mirror/v1/timeline/(.*)", UpdateHandler),
        ("/upload/mirror/v1/timeline", InsertHandler)
    ],
    debug=True
)

########NEW FILE########
__FILENAME__ = auth
#!/usr/bin/python

# Copyright (C) 2013 Gerwin Sturm, FoldedSoft e.U.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""

RequestHandlers and helper functions for authentication

Handles all authentication and storing of credentials when a user signs up
for the demo services. Sets up Contacts and Subscriptions when the user
first connects. Also handles disconnection by removing all contacts and
subscriptions and deleting credentials when the user wants to disconnect.

"""

__author__ = 'scarygami@gmail.com (Gerwin Sturm)'

import utils
from demos import demo_services

import random
import string
import httplib2
import json
import logging

from apiclient.discovery import build
from apiclient.errors import HttpError
from apiclient.errors import UnknownApiNameOrVersion
from google.appengine.ext import ndb
from oauth2client.client import AccessTokenRefreshError
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
from oauth2client.appengine import StorageByKeyName


def get_credentials(gplus_id, test):
    """Retrieves credentials for the provided Google+ User ID from the Datastore"""
    if test is not None:
        storage = StorageByKeyName(utils.TestUser, gplus_id, "credentials")
    else:
        storage = StorageByKeyName(utils.User, gplus_id, "credentials")
    credentials = storage.get()
    return credentials


def store_credentials(gplus_id, test, credentials):
    """Stores credentials for the provide Google+ User ID to Datastore"""
    if test is not None:
        storage = StorageByKeyName(utils.TestUser, gplus_id, "credentials")
    else:
        storage = StorageByKeyName(utils.User, gplus_id, "credentials")
    storage.put(credentials)


def get_auth_service(gplus_id, test, api="mirror", version="v1"):
    """Creates a new authenticated API client using the stored credentials"""

    if test is not None and api == "mirror" and version == "v1":
        # Use internal API for mirror API in test mode
        discovery_service_url = utils.discovery_service_url
    else:
        # Use Google APIs in all other cases
        discovery_service_url = None

    credentials = get_credentials(gplus_id, test)
    if credentials is None:
        return None

    http = httplib2.Http()
    http = credentials.authorize(http)
    http.timeout = 60

    if discovery_service_url is None:
        service = build(api, version, http=http)
    else:
        service = build(api, version, http=http, discoveryServiceUrl=discovery_service_url)

    return service


def _disconnect(gplus_id, test):
    """Delete credentials in case of errors"""

    store_credentials(gplus_id, test, None)


class ConnectHandler(utils.BaseHandler):
    def post(self, test):
        """
        Exchange the one-time authorization code for a token and
        store the credentials for later access.

        Setup all contacts and subscriptions necessary for the hosted services.
        """

        self.response.content_type = "application/json"

        state = self.request.get("state")
        gplus_id = self.request.get("gplus_id")
        code = self.request.body

        if state != self.session.get("state"):
            self.response.status = 401
            self.response.out.write(utils.createError(401, "Invalid state parameter"))
            return

        try:
            oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
            oauth_flow.redirect_uri = 'postmessage'
            credentials = oauth_flow.step2_exchange(code)
        except FlowExchangeError:
            self.response.status = 401
            self.response.out.write(
                utils.createError(401, "Failed to upgrade the authorization code.")
            )
            return

        # Check that the access token is valid.
        access_token = credentials.access_token
        url = ("https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s" % access_token)
        h = httplib2.Http()
        result = json.loads(h.request(url, 'GET')[1])

        # If there was an error in the access token info, abort.
        if result.get("error") is not None:
            self.response.status = 500
            self.response.out.write(json.dumps(result.get("error")))
            return

        # Verify that the access token is used for the intended user.
        if result["user_id"] != gplus_id:
            self.response.status = 401
            self.response.out.write(
                utils.createError(401, "Token's user ID doesn't match given user ID.")
            )
            return

        # Verify that the access token is valid for this app.
        if result['issued_to'] != utils.CLIENT_ID:
            self.response.status = 401
            self.response.out.write(
                utils.createError(401, "Token's client ID does not match the app's client ID")
            )
            return

        # Store credentials associated with the User ID for later use
        self.session["gplus_id"] = gplus_id
        stored_credentials = get_credentials(gplus_id, test)
        new_user = False
        if stored_credentials is None:
            new_user = True
            store_credentials(gplus_id, test, credentials)

        # handle cases where credentials don't have a refresh token
        credentials = get_credentials(gplus_id, test)

        if credentials.refresh_token is None:
            _disconnect(gplus_id, test)
            self.response.status = 401
            self.response.out.write(
                utils.createError(401, "No Refresh token available, need to reauthenticate")
            )
            return

        # Create new authorized API clients for the Mirror API and Google+ API
        try:
            service = get_auth_service(gplus_id, test)
            plus_service = get_auth_service(gplus_id, test, "plus", "v1")
        except AccessTokenRefreshError:
            _disconnect(gplus_id, test)
            self.response.status = 401
            self.response.out.write(utils.createError(401, "Failed to refresh access token."))
            return
        except UnknownApiNameOrVersion:
            self.response.status = 500
            self.response.out.write(utils.createError(500, "Failed to initialize client library. Discovery document not found."))
            return
        except HttpError as e:
            self.response.status = 500
            self.response.out.write(utils.createError(500, "Failed to initialize client library. %s" % e))
            return

        # Fetch user information
        try:
            result = plus_service.people().get(userId="me", fields="displayName,image").execute()
        except AccessTokenRefreshError:
            _disconnect(gplus_id, test)
            self.response.status = 401
            self.response.out.write(utils.createError(401, "Failed to refresh access token."))
            return
        except HttpError as e:
            self.response.status = 500
            self.response.out.write(utils.createError(500, "Failed to execute request. %s" % e))
            return

        # Store some public user information for later user
        if test is not None:
            user = ndb.Key("TestUser", gplus_id).get()
        else:
            user = ndb.Key("User", gplus_id).get()
        user.displayName = result["displayName"]
        user.imageUrl = result["image"]["url"]
        user.put()

        # Fetch user friends and store for later user
        try:
            result = plus_service.people().list(userId="me", collection="visible", maxResults=100, orderBy="best", fields="items/id").execute()
        except AccessTokenRefreshError:
            _disconnect(gplus_id, test)
            self.response.status = 401
            self.response.out.write(utils.createError(401, "Failed to refresh access token."))
            return
        except HttpError as e:
            self.response.status = 500
            self.response.out.write(utils.createError(500, "Failed to execute request. %s" % e))
            return

        friends = []
        if "items" in result:
            for item in result["items"]:
                friends.append(item["id"])

        user.friends = friends
        user.put()

        # Delete all existing contacts, so only the currently implemented ones are available
        try:
            result = service.contacts().list().execute()
            if "items" in result:
                for contact in result["items"]:
                    del_result = service.contacts().delete(id=contact["id"]).execute()
        except AccessTokenRefreshError:
            _disconnect(gplus_id, test)
            self.response.status = 401
            self.response.out.write(utils.createError(401, "Failed to refresh access token."))
            return
        except HttpError as e:
            self.response.status = 500
            self.response.out.write(utils.createError(500, "Failed to execute request. %s" % e))
            return

        # Register contacts defined in the demo services
        contacts = []
        for demo_service in demo_services:
            if hasattr(demo_service, "CONTACTS"):
                contacts.extend(demo_service.CONTACTS)

        for contact in contacts:
            try:
                result = service.contacts().insert(body=contact).execute()
            except AccessTokenRefreshError:
                _disconnect(gplus_id, test)
                self.response.status = 401
                self.response.out.write(utils.createError(401, "Failed to refresh access token."))
                return
            except HttpError as e:
                self.response.status = 500
                self.response.out.write(utils.createError(500, "Failed to execute request. %s" % e))
                return

        """
        Re-register subscriptions to make sure all of them are available.
        Normally it would be best to use subscriptions.list first to check.
        For the purposes of this demo service all possible subscriptions are made.
        Normally you would only set-up subscriptions for the services you need.
        """

        # Delete all existing subscriptions
        try:
            result = service.subscriptions().list().execute()
            if "items" in result:
                for subscription in result["items"]:
                    del_result = service.subscriptions().delete(id=subscription["id"]).execute()
        except AccessTokenRefreshError:
            _disconnect(gplus_id, test)
            self.response.status = 401
            self.response.out.write(utils.createError(401, "Failed to refresh access token."))
            return
        except HttpError as e:
            self.response.status = 500
            self.response.out.write(utils.createError(500, "Failed to execute request. %s" % e))
            return

        # Generate random verifyToken and store it in User entity
        verifyToken = ''.join(random.choice(string.ascii_letters + string.digits) for x in range(32))
        user.verifyToken = verifyToken
        user.put()

        # Subscribe to all timeline inserts/updates/deletes
        body = {}
        body["collection"] = "timeline"
        body["userToken"] = gplus_id
        body["verifyToken"] = verifyToken
        body["callbackUrl"] = utils.base_url + ("" if test is None else "/test") + "/timeline_update"
        try:
            result = service.subscriptions().insert(body=body).execute()
        except AccessTokenRefreshError:
            _disconnect(gplus_id, test)
            self.response.status = 401
            self.response.out.write(utils.createError(401, "Failed to refresh access token."))
            return
        except HttpError as e:
            self.response.status = 500
            self.response.out.write(utils.createError(500, "Failed to execute request. %s" % e))
            return

        # Subscribe to all location updates
        body = {}
        body["collection"] = "locations"
        body["userToken"] = gplus_id
        body["verifyToken"] = verifyToken
        body["callbackUrl"] = utils.base_url + ("" if test is None else "/test") + "/locations_update"
        try:
            result = service.subscriptions().insert(body=body).execute()
        except AccessTokenRefreshError:
            _disconnect(gplus_id, test)
            self.response.status = 401
            self.response.out.write(utils.createError(401, "Failed to refresh access token."))
            return
        except HttpError as e:
            self.response.status = 500
            self.response.out.write(utils.createError(500, "Failed to execute request. %s" % e))
            return

        if not new_user:
            self.response.status = 200
            self.response.out.write(utils.createMessage("Current user is already connected."))
            return

        # Send welcome messages for new users
        welcomes = []
        for demo_service in demo_services:
            if hasattr(demo_service, "WELCOMES"):
                welcomes.extend(demo_service.WELCOMES)

        for welcome in welcomes:
            try:
                result = service.timeline().insert(body=welcome).execute()
            except AccessTokenRefreshError:
                _disconnect(gplus_id, test)
                self.response.status = 401
                self.response.out.write(utils.createError(401, "Failed to refresh access token."))
                return
            except HttpError as e:
                self.response.status = 500
                self.response.out.write(utils.createError(500, "Failed to execute request. %s" % e))
                return

        self.response.status = 200
        self.response.out.write(utils.createMessage("Successfully connected user."))


class DisconnectHandler(utils.BaseHandler):
    def post(self, test):
        """
        Remove contacts and subscriptions registered for the user.
        Revoke current user's token and reset their session.
        Delete User entity from Data store.
        """

        self.response.content_type = "application/json"

        gplus_id = self.session.get("gplus_id")

        # Only disconnect a connected user.
        credentials = get_credentials(gplus_id, test)
        if credentials is None:
            self.response.status = 401
            self.response.out.write(utils.createError(401, "Current user not connected."))
            return

        # Create a new authorized API client
        try:
            service = get_auth_service(gplus_id, test)
        except AccessTokenRefreshError:
            self.response.status = 500
            self.response.out.write(utils.createError(500, "Failed to refresh access token."))
            return
        except UnknownApiNameOrVersion:
            self.response.status = 500
            self.response.out.write(utils.createError(500, "Failed to initialize client library. Discovery document not found."))
            return
        except HttpError as e:
            self.response.status = 500
            self.response.out.write(utils.createError(500, "Failed to initialize client library. %s" % e))
            return

        # De-register contacts
        try:
            result = service.contacts().list().execute()
            if "items" in result:
                for contact in result["items"]:
                    del_result = service.contacts().delete(id=contact["id"]).execute()
        except AccessTokenRefreshError:
            self.response.status = 500
            self.response.out.write(utils.createError(500, "Failed to refresh access token."))
            return
        except HttpError as e:
            self.response.status = 500
            self.response.out.write(utils.createError(500, "Failed to execute request. %s" % e))
            return

        # De-register subscriptions
        try:
            result = service.subscriptions().list().execute()
            if "items" in result:
                for subscription in result["items"]:
                    del_result = service.subscriptions().delete(id=subscription["id"]).execute()
        except AccessTokenRefreshError:
            self.response.status = 500
            self.response.out.write(utils.createError(500, "Failed to refresh access token."))
            return
        except HttpError as e:
            self.response.status = 500
            self.response.out.write(utils.createError(500, "Failed to execute request. %s" % e))
            return

        # Execute HTTP GET request to revoke current token.
        access_token = credentials.access_token
        url = "https://accounts.google.com/o/oauth2/revoke?token=%s" % access_token
        h = httplib2.Http()
        try:
            result = h.request(url, "GET")[0]
            if result["status"] == "200":
                # Reset the user's session.
                self.response.status = 200
                self.response.out.write(utils.createMessage("Successfully disconnected user."))
            else:
                # For whatever reason, the given token was invalid.
                self.response.status = 400
                self.response.out.write(utils.createError(400, "Failed to revoke token for given user."))
        except HttpError as e:
            self.response.status = 500
            self.response.out.write(utils.createError(500, "Failed to execute request. %s" % e))
            return

        # Delete User entity from datastore
        if test is not None:
            ndb.Key("TestUser", gplus_id).delete()
        else:
            ndb.Key("User", gplus_id).delete()


AUTH_ROUTES = [
    (r"(/test)?/connect", ConnectHandler),
    (r"(/test)?/disconnect", DisconnectHandler)
]

########NEW FILE########
__FILENAME__ = notify
#!/usr/bin/python

# Copyright (C) 2013 Gerwin Sturm, FoldedSoft e.U.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Notification/subscription handler

Handles subscription post requests coming from the Mirror API and forwards
the requests to the relevant demo services.

"""

__author__ = 'scarygami@gmail.com (Gerwin Sturm)'

import utils
from demos import demo_services
from auth import get_auth_service

import json
import logging
from datetime import datetime
from google.appengine.ext import ndb


class TimelineNotifyHandler(utils.BaseHandler):
    """
    Handles all timeline notifications (updates, deletes, inserts)
    Forwards the information to implemented demo services
    """

    def post(self, test):
        """Callback for Timeline updates."""

        message = self.request.body
        data = json.loads(message)
        logging.info(data)

        self.response.status = 200

        gplus_id = data["userToken"]
        verifyToken = data["verifyToken"]
        if test is not None:
            user = ndb.Key("TestUser", gplus_id).get()
        else:
            user = ndb.Key("User", gplus_id).get()
        if user is None or user.verifyToken != verifyToken:
            logging.info("Wrong user")
            return

        if data["collection"] != "timeline":
            logging.info("Wrong collection")
            return

        service = get_auth_service(gplus_id, test)

        if service is None:
            logging.info("No valid credentials")
            return

        result = service.timeline().get(id=data["itemId"]).execute()
        logging.info(result)

        for demo_service in demo_services:
            if hasattr(demo_service, "handle_item"):
                demo_service.handle_item(result, data, service, test)


class LocationNotifyHandler(utils.BaseHandler):
    """
    Handles all location notifications
    Forwards the information to implemented demo services
    """

    def post(self, test):
        """Callback for Location updates."""

        message = self.request.body
        data = json.loads(message)

        self.response.status = 200

        gplus_id = data["userToken"]
        verifyToken = data["verifyToken"]
        if test is not None:
            user = ndb.Key("TestUser", gplus_id).get()
        else:
            user = ndb.Key("User", gplus_id).get()

        if user is None or user.verifyToken != verifyToken:
            logging.info("Wrong user")
            return

        if data["collection"] != "locations":
            logging.info("Wrong collection")
            return

        if data["operation"] != "UPDATE":
            logging.info("Wrong operation")
            return

        service = get_auth_service(gplus_id, test)

        if service is None:
            logging.info("No valid credentials")
            return

        result = service.locations().get(id=data["itemId"]).execute()
        logging.info(result)

        if "longitude" in result and "latitude" in result:
            user.longitude = result["longitude"]
            user.latitude = result["latitude"]
            user.locationUpdate = datetime.utcnow()
            user.put()

        for demo_service in demo_services:
            if hasattr(demo_service, "handle_location"):
                demo_service.handle_location(result, data, service, test)


NOTIFY_ROUTES = [
    (r"(/test)?/timeline_update", TimelineNotifyHandler),
    (r"(/test)?/locations_update", LocationNotifyHandler)
]

########NEW FILE########
__FILENAME__ = service
#!/usr/bin/python

# Copyright (C) 2013 Gerwin Sturm, FoldedSoft e.U.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""RequestHandlers for Web service"""

__author__ = 'scarygami@gmail.com (Gerwin Sturm)'

import utils
from auth import get_auth_service

import json
import logging
import random
import string


from oauth2client.client import AccessTokenRefreshError


class IndexHandler(utils.BaseHandler):
    """Renders the main page that is mainly used for authentication only so far"""

    def get(self, test):

        if test is None:
            scopes = ' '.join(utils.COMMON_SCOPES + utils.REAL_SCOPES)
        else:
            scopes = ' '.join(utils.COMMON_SCOPES + utils.TEST_SCOPES)

        request_visible_actions = ' '.join(utils.REQUEST_VISIBLE_ACTIONS)
        reconnect = (self.request.get("reconnect") == "true")
        template = utils.JINJA.get_template("service/templates/service.html")
        state = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))
        self.session["state"] = state
        self.response.out.write(template.render({"client_id": utils.CLIENT_ID, "state": state, "scopes": scopes, "actions": request_visible_actions, "reconnect": reconnect}))


class ListHandler(utils.BaseHandler):

    def get(self, test):
        """Retrieve timeline cards for the current user."""

        self.response.content_type = "application/json"

        gplus_id = self.session.get("gplus_id")
        service = get_auth_service(gplus_id, test)

        if service is None:
            self.response.status = 401
            self.response.out.write(utils.createError(401, "Current user not connected."))
            return
        try:
            # Retrieve timeline cards and return as reponse
            result = service.timeline().list().execute()
            self.response.status = 200
            self.response.out.write(json.dumps(result))
        except AccessTokenRefreshError:
            self.response.status = 500
            self.response.out.write(utils.createError(500, "Failed to refresh access token."))


class NewCardHandler(utils.BaseHandler):

    def post(self, test):
        """Create a new timeline card for the current user."""

        self.response.content_type = "application/json"

        gplus_id = self.session.get("gplus_id")
        service = get_auth_service(gplus_id, test)

        if service is None:
            self.response.status = 401
            self.response.out.write(utils.createError(401, "Current user not connected."))
            return

        message = self.request.body

        data = json.loads(message)

        body = {}
        body["text"] = data["text"]

        try:
            # Insert timeline card and return as reponse
            result = service.timeline().insert(body=body).execute()
            self.response.status = 200
            self.response.out.write(json.dumps(result))
        except AccessTokenRefreshError:
            self.response.status = 500
            self.response.out.write(utils.createError(500, "Failed to refresh access token."))


class AttachmentHandler(utils.BaseHandler):
    """Retrieves an attachment using the current user's credentials"""

    def get(self, test, timelineId, attachmentId):
        gplus_id = self.session.get("gplus_id")
        service = get_auth_service(gplus_id, test)
        if service is None:
            self.response.content_type = "application/json"
            self.response.status = 401
            self.response.out.write(utils.createError(401, "Invalid credentials."))
            return

        attachment_metadata = service.timeline().attachments().get(
            itemId=timelineId, attachmentId=attachmentId).execute()
        content_type = str(attachment_metadata.get("contentType"))
        content_url = attachment_metadata.get("contentUrl")
        resp, content = service._http.request(content_url)

        if resp.status == 200:
            self.response.content_type = content_type
            self.response.out.write(content)
        else:
            logging.info(resp)
            self.response.content_type = "application/json"
            self.response.status = resp.status
            self.response.out.write(utils.createError(resp.status, "Unable to retrieve attachment."))


SERVICE_ROUTES = [
    (r"(/test)?/attachment/(.*)/(.*)", AttachmentHandler),
    (r"(/test)?/", IndexHandler),
    (r"(/test)?/list", ListHandler),
    (r"(/test)?/new", NewCardHandler)
]

########NEW FILE########
__FILENAME__ = upload
#!/usr/bin/python

# Copyright (C) 2013 Gerwin Sturm, FoldedSoft e.U.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Helper functions to upload mediacontent to cards"""

__author__ = 'scarygami@gmail.com (Gerwin Sturm)'

from utils import base_url

import io
import json
import logging

from apiclient import errors
from apiclient.http import MediaIoBaseUpload

_BOUNDARY = "-----1234567890abc"


def _create_multipart_body(metadata, content, contentType):
    base64_data = content.encode("base64").replace("\n", "")
    multipart_body = "\r\n--" + _BOUNDARY + "\r\n"
    multipart_body += "Content-Type: application/json\r\n\r\n"
    multipart_body += json.dumps(metadata)
    multipart_body += "\r\n--" + _BOUNDARY + "\r\n"
    multipart_body += "Content-Type: " + contentType + "\r\n"
    multipart_body += "Content-Transfer-Encoding: base64\r\n\r\n"
    multipart_body += base64_data
    multipart_body += "\r\n\r\n--" + _BOUNDARY + "--"

    return multipart_body


def multipart_insert(metadata, content, contentType, service, test):

    if metadata is None:
        metadata = {}

    """Insert a new card with metainfo card and media."""
    if test is None:
        # Using the functionality of the API Client library to directly send multipart request
        media = MediaIoBaseUpload(io.BytesIO(content), contentType, resumable=True)
        try:
            return service.timeline().insert(body=metadata, media_body=media).execute()
        except errors.HttpError, error:
            logging.error("Multipart update error: %s" % error)
            return error

    # Constructing the multipart upload for test environement
    multipart_body = _create_multipart_body(metadata, content, contentType)

    headers = {}
    headers["Content-Type"] = "multipart/related; boundary=\"" + _BOUNDARY + "\""

    return service._http.request(base_url + "/upload/mirror/v1/timeline", method="POST", body=multipart_body, headers=headers)


def multipart_update(cardId, metadata, content, contentType, service, test):

    if metadata is None:
        metadata = {}

    """Update a card with metainfo and media."""
    if test is None:
        # Using the functionality of the API Client library to directly send multipart request
        media = MediaIoBaseUpload(io.BytesIO(content), contentType, resumable=True)
        try:
            return service.timeline().update(id=cardId, body=metadata, media_body=media).execute()
        except errors.HttpError, error:
            logging.error("Multipart update error: %s" % error)
            return error

    # Constructing the multipart upload for test environement
    multipart_body = _create_multipart_body(metadata, content, contentType)

    headers = {}
    headers["Content-Type"] = "multipart/related; boundary=\"" + _BOUNDARY + "\""

    return service._http.request("%s/upload/mirror/v1/timeline/%s" % (base_url, cardId), method="POST", body=multipart_body, headers=headers)


def media_insert(cardId, content, contentType, service, test):

    """Insert attachment to an existing card."""
    if test is None:
        # Using the functionality of the API Client library to directly send request
        media = MediaIoBaseUpload(io.BytesIO(content), contentType, resumable=True)
        try:
            return service.timeline().attachments().insert(id=cardId, media_body=media).execute()
        except errors.HttpError, error:
            logging.error("Attachment insert error: %s" % error)
            return error

    # Constructing the multipart upload for test environement
    multipart_body = _create_multipart_body({}, content, contentType)

    headers = {}
    headers["Content-Type"] = "multipart/related; boundary=\"" + _BOUNDARY + "\""

    return service._http.request("%s/upload/mirror/v1/timeline/%s/attachments" % (base_url, cardId), method="POST", body=multipart_body, headers=headers)

########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/python

# Copyright (C) 2013 Gerwin Sturm, FoldedSoft e.U.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Configuration options and helper functions for all services"""

__author__ = 'scarygami@gmail.com (Gerwin Sturm)'

import jinja2
import json
import os
import webapp2

from apiclient.discovery import build
from google.appengine.api.app_identity import get_application_id
from google.appengine.ext import ndb
from oauth2client.appengine import CredentialsNDBProperty
from webapp2_extras import sessions
from webapp2_extras.appengine import sessions_memcache

JINJA = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))

appname = get_application_id()
base_url = "https://" + appname + ".appspot.com"
discovery_url = base_url + "/_ah/api"
discovery_service_url = discovery_url + "/discovery/v1/apis/{api}/{apiVersion}/rest"

with open("client_secrets.json", "r") as fh:
    secrets = json.load(fh)["web"]
    CLIENT_ID = secrets["client_id"]
    SESSION_KEY = str(secrets["session_secret"])
    API_KEY = secrets["api_key"]

config = {}
config["webapp2_extras.sessions"] = {"secret_key": SESSION_KEY}

# Add any additional scopes that you might need for your service to access other Google APIs
COMMON_SCOPES = ["https://www.googleapis.com/auth/plus.login"]

# userinfo.email scope is required to work with Google Cloud Endpoints
TEST_SCOPES = ["https://www.googleapis.com/auth/userinfo.email"]

# Remove the location scope from here if you don't need it
REAL_SCOPES = [
    "https://www.googleapis.com/auth/glass.timeline",
    "https://www.googleapis.com/auth/glass.location"
]

# Requests for app activities during the Auth flow
REQUEST_VISIBLE_ACTIONS = [
    "http://schemas.google.com/CheckInActivity"
]


def createError(code, message):
    """Create a JSON string to be returned as error response to requests"""
    return json.dumps({"error": {"code": code, "message": message}})


def createMessage(message):
    """Create a JSON string to be returned as response to requests"""
    return json.dumps({"message": message})


class BaseHandler(webapp2.RequestHandler):
    """Base request handler to enable session storage for all handlers"""

    def dispatch(self):
        # Get a session store for this request.
        self.session_store = sessions.get_store(request=self.request)

        try:
            # Dispatch the request.
            webapp2.RequestHandler.dispatch(self)
        finally:
            # Save all sessions.
            self.session_store.save_sessions(self.response)

    @webapp2.cached_property
    def session(self):
        return self.session_store.get_session(name='mirror_session', factory=sessions_memcache.MemcacheSessionFactory)


def build_service_from_service(service, api, version):
    """Build a Google API service using another pre-authed service"""
    
    new_service = build(api, version, http=service._http)
    
    return new_service


class User(ndb.Model):
    """Datastore model to keep all relevant information about a user

    Properties:
        displayName     Name of the user as returned by the Google+ API
        imageUrl        Avatar image of the user as returned by the Google+ API
        verifyToken     Random token generated for each user to check validity of incoming notifications
        credentials     OAuth2 Access and refresh token to be used for requests against the Mirror API
        latitude        Latest recorded latitude of the user
        longitude       Latest recorded longitude of the user
        locationUpdate  DateTime at which the location of the user was last update
        friends         List of Google+ friends id, as returned by the Google+ API
    """

    displayName = ndb.StringProperty()
    imageUrl = ndb.StringProperty()
    verifyToken = ndb.StringProperty()
    credentials = CredentialsNDBProperty()
    latitude = ndb.FloatProperty()
    longitude = ndb.FloatProperty()
    locationUpdate = ndb.DateTimeProperty()
    friends = ndb.StringProperty(repeated=True)


class TestUser(User):

    _testUser = True

########NEW FILE########
