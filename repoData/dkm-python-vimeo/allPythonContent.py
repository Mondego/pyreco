__FILENAME__ = vimeo-query
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2009 Marc Poulhiès
#
# Python module for Vimeo
#
# This is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Plopifier.  If not, see <http://www.gnu.org/licenses/>.


"""
This is an upload script for Vimeo using its v2 API
"""


import vimeo
import vimeo.config
import sys
import optparse
import pprint

def main(argv):
    parser = optparse.OptionParser(
        usage='Usage: %prog [options]',
        description="Simple Vimeo uploader")

    # auth/appli stuff
    parser.add_option('-k', '--key',
                      help="Consumer key")
    parser.add_option('-s', '--secret',
                      help="Consumer secret")
    parser.add_option('-t', '--access-token',
                      help="Access token")
    parser.add_option('-y', '--access-token-secret',
                      help="Access token secret")

    parser.add_option('--album', metavar="ALBUM_ID",
                      action="append",
                      help="Specify on which album other commands act."
                           +"Can be used more than once")
    parser.add_option('--group', metavar="GROUP_ID",
                      action="append",
                      help="Specify on which group other commands act."
                           +"Can be used more than once")
    parser.add_option('--channel', metavar="CHANNEL_ID",
                      action="append",
                      help="Specify on which channel other commands act."
                           +"Can be used more than once")
    parser.add_option('--video', metavar="VIDEO_ID",
                      action="append",
                      help="Specify on which video other command acts."
                           +"Can be used more than once")
    parser.add_option('--user', metavar="USER_ID",
                      action="append",
                      help="Specify on which user other command acts."
                           +"Can be used more than once")

    parser.add_option('--quota',
                      help="Get user quota", action="store_true", default=False)

    parser.add_option('--get-groups',
                      help="Get all public groups", action="store_true", default=False)
    parser.add_option('--get-group-files',
                      help="Get list of files for the GROUP_ID", 
                      action="store_true",
                      default=False)
    parser.add_option('--get-group-info',
                      help="Get information of the GROUP_ID", 
                      action="store_true",
                      default=False)
    parser.add_option('--get-group-members',
                      help="Get the members of the GROUP_ID", 
                      action="store_true",
                      default=False)
    parser.add_option('--get-group-video-comments',
                      help="Get a list of the comments for VIDEO_ID in GROUP_ID", 
                      action="store_true",
                      default=False)
    parser.add_option('--get_group_moderators',
                      help="Get a list of the group's moderators.",
                      action="store_true",
                      default=False)
    parser.add_option('--get-channels',
                      help="Get all public channels", action="store_true", default=False)
    parser.add_option('--get-channel-info',
                      help="Get info on channel CHANNEL_ID",
                      action="store_true")

    parser.add_option('--get-video-info',
                      help="Get info on video VIDEO_ID",
                      action="store_true")
    parser.add_option('--get-uploaded-videos',
                      help="Get a list of videos uploaded by a user.",
                      action="store_true")

    parser.add_option('--page', metavar="NUM",
                      help="Page number, when it makes sense...")
    parser.add_option('--per-page', metavar="NUM",
                      help="Per page number, when it makes sense...")
    parser.add_option('--sort', metavar="SORT_ID",
                      help="sort order, when it makes sense (accepted values depends on the query)...")
    parser.add_option('--get-channel-moderators',
                      help="Get moderators for channel CHANNEL_ID",
                      action="store_true")
    parser.add_option('--get-channel-subscribers',
                      help="Get subscribers for channel CHANNEL_ID",
                      action="store_true")
    parser.add_option('--get-channel-videos',
                      help="Get videos for channel CHANNEL_ID using the sort SORT_ID",
                      action="store_true")
    parser.add_option('--get-contacts',
                      help="Get all contacts for user USER_ID",
                      action="store_true")
    parser.add_option('--get-mutual-contacts',
                      help="Get the mutual contacts for USER_ID",
                      action="store_true")
    parser.add_option('--get-online-contacts',
                      help="Get the user's online contacts",
                      action="store_true")
    parser.add_option('--get-who-added-contacts',
                      help="Get the contacts who added USER_ID as a contact",
                      action="store_true")

    parser.add_option('--add-video',
                      help="Add the video VIDEO_ID to the album ALBUM_ID and channel" +
                           "CHANNEL_ID.",
                      action="store_true")

    parser.add_option('--remove-video', 
                      help="Remove the video ViDEO_ID from the album ALBUM_ID and channel" +
                           "CHANNEL_ID.",
                      action="store_true")

    parser.add_option('--set-album-description', metavar='DESCRIPTION',
                      help="Set the description for the album ALBUM_ID")

    parser.add_option('--set-channel-description', metavar='DESCRIPTION',
                      help="Set the description for the channel CHANNEL_ID")

    parser.add_option('--set-password', metavar='PASSWORD',
                      help="Set the password for the channel(s), album(s) and video(s) specified with --channel, --album and --video")
    

    (options, args) = parser.parse_args(argv[1:])

    def check_user():
        return options.user != None

    def check_channel():
        return options.channel != None

    def check_video():
        return options.video != None

    def check_group():
        return options.group != None
            
    def check_album():
        return options.album != None

    vconfig = vimeo.config.VimeoConfig(options)

    if not vconfig.has_option("appli", "consumer_key"):
        print "Missing consumer key"
        parser.print_help()
        sys.exit(-1)

    if not vconfig.has_option("appli", "consumer_secret"):
        print "Missing consumer secret"
        parser.print_help()
        sys.exit(-1)

    client = vimeo.VimeoClient(vconfig.get("appli", "consumer_key"),
                               vconfig.get("appli", "consumer_secret"),
                               token=vconfig.get("auth","token"),
                               token_secret=vconfig.get("auth", "token_secret"),
                               format="json")

    if options.quota:
        quota = client.vimeo_videos_upload_getQuota()['upload_space']['free']
        print "Your current quota is", int(quota)/(1024*1024), "MiB"

    elif options.get_channels:
        channels = client.vimeo_channels_getAll(page=options.page,
                                                sort=options.sort,
                                                per_page=options.per_page)
        if channels['perpage'] == "1":
            print "Name (%s):" % channels['channel']['id'], channels['channel']['name']
        else:
            for channel in channels["channel"]:
                print "Name (%s):" % channel['id'], channel['name']
    
    elif options.get_channel_info :
        if not check_channel():
            print "Missing channel"
            parser.print_help()
            sys.exit(-1)
        for chan in options.channel:
            info = client.vimeo_channels_getInfo(channel_id=chan)

            for text_item in ['name', 'description', 'created_on', 'modified_on', 'total_videos',
                              'total_subscribers', 'logo_url', 'badge_url', 'url', 'featured_description']:
                          
                it = info.get(text_item)
                if it:
                    print "%s:" %text_item, info.get(text_item)
            creator = info['creator']
            print "Creator: %s (%s)" %(creator['display_name'], creator['id'])
       
    elif options.get_video_info:
        if not check_video():
            print "Missing video"
            parser.print_help()
            sys.exit(-1)

        for vid in options.video:
            info = client.vimeo_videos_getInfo(video_id=vid)
            ## TODO pretty print results ?
            pprint.pprint(info)
    elif options.get_uploaded_videos:
        if not check_user():
            print "Missing user"
            parser.print_help()
            sys.exit(-1)

        for user in options.user:
            vids = client.vimeo_videos_getUploaded(user_id=user,
                                                   sort=options.sort,
                                                   page=options.page,
                                                   per_page=options.per_page)

            for vid in vids['video']:
                print "Video: %s (%s), uploaded %s" %(vid['title'], 
                                                      vid['id'], 
                                                      vid['upload_date'])

    elif options.get_channel_moderators:
        if not check_channel():
            print "Missing channel"
            parser.print_help()
            sys.exit(-1)

        for chan in options.channel:
            moderators = client.vimeo_channels_getModerators(channel_id=chan,
                                                             page=options.page,
                                                             per_page=options.per_page)

            if moderators['perpage'] == "1":
                print "Name: %s (%s)" %(moderators['user']['display_name'], moderators['user']['id'])
            else:
                for moderator in moderators['user']:
                    print "Name: %s (%s)" %(moderator['display_name'], moderator['id'])

    elif options.get_channel_subscribers:
        if not check_channel():
            print "Missing channel"
            parser.print_help()
            sys.exit(-1)

        for chan in options.channel:
            subs = client.vimeo_channels_getSubscribers(channel_id=chan,
                                                        page=options.page,
                                                        per_page=options.per_page)
            if subs['perpage'] == "1":
                print "Name: %s (%s)" %(subs['subscriber']['display_name'], subs['subscriber']['id'])
            else:
                for sub in subs['subscriber']:
                    print "Name: %s (%s)" %(sub['display_name'], sub['id'])

    elif options.get_channel_videos:
        if not check_channel():
            print "Missing channel"
            parser.print_help()
            sys.exit(-1)

        for chan in options.channel:
            vids = client.vimeo_channels_getVideos(channel_id=chan,
                                                   page=options.page,
                                                   per_page=options.per_page)

            ## Here, no need to check per-page, it always returns a list ?!
            for vid in vids['video']:
                print "Video: %s (%s), uploaded %s" %(vid['title'], 
                                                      vid['id'], 
                                                      vid['upload_date'])
    elif options.get_contacts:
        if not check_user():
            print "Missing user"
            parser.print_help()
            sys.exit(-1)

        for user in options.user:
            contacts = client.vimeo_contacts_getAll(user_id=user,
                                                    sort=options.sort,
                                                    page=options.page,
                                                    per_page=options.per_page)
            for contact in contacts['contact']:
                print "Contact: %s (%s)" %(contact['display_name'], contact['id'])

    elif options.add_video:
        if not check_video():
            print "Missing video"
            parser.print_help()
            sys.exit(-1)

        for vid in options.video:
            if options.album:
                for alb in options.album:
                    client.vimeo_albums_addVideo(album_id=alb,
                                                 video_id=vid)
            if options.channel:
                for chan in options.channel:
                    client.vimeo_channels_addVideo(channel_id=chan,
                                                   video_id=vid)
            if options.group:
                for chan in options.group:
                    client.vimeo_groups_addVideo(channel_id=chan,
                                                 video_id=vid)

###
### Folowing this line, the code has not been fixed yet.
###
    elif options.remove_video:
        if not check_video():
            print "Missing video"
            parser.print_help()
            sys.exit(-1)

        for vid in options.video:
            if options.album:
                for alb in options.album:
                    client.vimeo_albums_removeVideo(vid,
                                                alb)
            if options.channel:
                for chan in options.channel:
                    client.vimeo_channels_removeVideo(vid,
                                                      chan)
    elif options.get_groups:
        groups = client.vimeo_groups_getAll(page=options.page,
                                              sort=options.sort,
                                              per_page=options.per_page)
        for group in groups.findall("groups/group"):
            print "Name (%s):" %group.attrib['id'], group.find('name').text
    elif options.get_groups:
        if not check_group():
            print "Missing group"
            parser.print_help()
            sys.exit(-1)

        for group in option.group:
            groups = client.vimeo_groups_getFiles(group,
                                                  page=options.page,
                                                  per_page=options.per_page)
## FIXME: display the files !
#             for group in groups.findall("groups/group"):
#                 print "Name (%s):" %group.attrib['id'], group.find('name').text
    elif options.get_group_info:
        if not check_group():
            print "Missing group"
            parser.print_help()
            sys.exit(-1)

        for group in option.group:
            group_info = client.vimeo_groups_getInfo(group)
        ## FIXME: display the group info !
    elif options.get_group_members:
        if not check_group():
            print "Missing group"
            parser.print_help()
            sys.exit(-1)

        for group in option.group:
            group_members = client.vimeo_groups_getMembers(group,
                                                           options.page,
                                                           option.per_page,
                                                           option.sort)
        ## FIXME: display the group_members info !
        
    elif options.get_group_moderators:
        if not check_group():
            print "Missing group"
            parser.print_help()
            sys.exit(-1)

        for group in options.group:
            moderators = client.vimeo_groups_getModerators(group,
                                                           page=options.page,
                                                           per_page=options.per_page)
            for moderator in moderators.findall('moderators/user'):
                print "Name: %s (%s)" %(moderator.attrib['display_name'], moderator.attrib['id'])
    elif options.get_group_video_comments:
        if not check_group():
            print "Missing group"
            parser.print_help()
            sys.exit(-1)

        if not check_video():
            print "Missing video"
            parser.print_help()
            sys.exit(-1)

        for group in option.group:
            for video in options.video:
                comments = client.vimeo_groups_getVideoComments(group,
                                                                video,
                                                                page=options.page,
                                                                per_page=options.per_page)
                ##FIXME: display comments !

    elif options.set_album_description:
        if not check_album():
            print "Missing album"
            parser.print_help()
            sys.exit(-1)

        for alb in options.album:
            client.vimeo_albums_setDescription(options.set_album_description,
                                               alb)

    elif options.set_channel_description:
        if not check_channel():
            print "Missing channel"
            parser.print_help()
            sys.exit(-1)

        for chan in options.channel:
            client.vimeo_channels_setDescription(options.set_channel_description,
                                                 chan)
    elif options.set_password:
        if options.channel:
            for chan in options.channel:
                client.vimeo_channels_setPassword(options.set_password,
                                                  chan)
        if options.album:
            for alb in options.album:
                client.vimeo_albums_setPassword(options.set_password,
                                                   alb)
        if options.video:
            for vid in options.video:
                client.vimeo_videos_setPrivacy(privacy='password',
                                               password=options.set_password,
                                               video_id=vid)


if __name__ == '__main__':
    main(sys.argv)



########NEW FILE########
__FILENAME__ = vimeo-test
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2009 Marc Poulhiès
#
# Python module for Vimeo
#
# python-vimeo is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Plopifier is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Plopifier.  If not, see <http://www.gnu.org/licenses/>.


"""
This script contains various call to vimeo API
in order the check the correct behavior of python-vimeo.
"""

from vimeo import SimpleOAuthClient
import vimeo
import oauth.oauth as oauth
import sys
import optparse


def test_albums(client):
    video_ids = [xxx,yyy,zzz]
    user_id = uid

    client.vimeo_albums_addVideo(self, album_id, video_id)

    a1 = client.vimeo_albums_create(title, video_id)
    a2 = client.vimeo_albums_create(title, video_id, description=None)
    a3 = client.vimeo_albums_create(title, video_id, videos=videos_ids)
    
    client.vimeo_albums_delete(a2)
    client.vimeo_albums_delete(a3)

    client.vimeo_albums_getAll(uid)
    client.vimeo_albums_getAll(uid, sort="newest")
    client.vimeo_albums_getAll(uid, sort="oldest")
    client.vimeo_albums_getAll(uid, sort="alphabetical")

    client.vimeo_albums_getAll(uid, sort="newest", page=2)
    client.vimeo_albums_getAll(uid, sort="oldest", page=2)
    client.vimeo_albums_getAll(uid, sort="alphabetical", page=2)

    client.vimeo_albums_getAll(uid, sort="newest", per_page=35)
    client.vimeo_albums_getAll(uid, sort="oldest", per_page=35)
    client.vimeo_albums_getAll(uid, sort="alphabetical", per_page=35)

    client.vimeo_albums_getVideos(a1, full_response=None)
    client.vimeo_albums_getVideos(a1, full_response=True)

    client.vimeo_albums_removeVideo(a1)
    client.vimeo_albums_removeVideo(a1, video_ids[0])

    client.vimeo_albums_setDescription(a1, "toto toto")
    client.vimeo_albums_setPassword(a1, "abcd")
    client.vimeo_albums_setTitle(a1, "toto title")

def test_videos(client):
    user_ids=[xxx, yyy, zzz]
    video_ids=[xxx, yyy, zzz]
    client.vimeo_videos_addCast(user_ids[0], video_ids[0])

    client.vimeo_videos_addPhotos(photos_urls, video_id)
    client.vimeo_videos_addTags(tags, video_id)
    client.vimeo_videos_clearTags(video_id)
    client.vimeo_videos_delete(video_id)
    client.vimeo_videos_getAll(user_id,)
    client.vimeo_videos_getAppearsIn(user_id,)
    client.vimeo_videos_getByTag(tag, )
    client.vimeo_videos_getCast(video_id,)
    client.vimeo_videos_getContactsLiked(user_id,)
    client.vimeo_videos_getContactsUploaded(user_id, )
    client.vimeo_videos_getInfo(video_id)
    client.vimeo_videos_getLikes(user_id,)
    client.vimeo_videos_getSourceFileUrls(video_id)
    client.vimeo_videos_getSubscriptions(user_id,
    client.vimeo_videos_getThumbnailUrls(video_id)
    client.vimeo_videos_getUploaded(user_id,)
    client.vimeo_videos_removeCast(user_id, video_id)
    client.vimeo_videos_removeTag(tag_id, video_id)
    client.vimeo_videos_search(query, user_id=None,)
    client.vimeo_videos_setDescription(description, video_id)
    client.vimeo_videos_setLike(like, video_id)
    client.vimeo_videos_setPrivacy(privacy, video_id,)
    client.vimeo_videos_setTitle(title, video_id)
    client.vimeo_videos_comments_addComment(comment_text, video_id,)
    client.vimeo_videos_comments_deleteComment(comment_id, video_id)
    client.vimeo_videos_comments_editComment(comment_id,)
    client.vimeo_videos_comments_getList(video_id,)
    client.vimeo_videos_embed_getPresets(page=None, per_page=None)
    client.vimeo_videos_embed_setPreset(preset_id,)


def test_upload(client):
                                             
#     client.vimeo_videos_upload_checkTicket(ticket_id)
#     client.vimeo_videos_upload_confirm(ticket_id,
#     client.vimeo_videos_upload_getTicket(self)
#     client.vimeo_videos_upload_verifyManifest(json_manifest, ticket_id, xml_manifest)



def main(argv):
    parser = optparse.OptionParser(
        usage='Usage: %prog [options]',
        description="Simple Vimeo uploader")
    parser.add_option('-k', '--key',
                      help="Consumer key")
    parser.add_option('-s', '--secret',
                      help="Consumer secret")
    parser.add_option('-t', '--access-token',
                      help="Access token")
    parser.add_option('-y', '--access-token-secret',
                      help="Access token secret")


    (options, args) = parser.parse_args(argv[1:])
    
    if None in (options.key, options.secret):
        print "Missing key or secret"
        sys.exit(-1)

    if None in (options.access_token, options.access_token_secret):
        client = SimpleOAuthClient(options.key, options.secret)
        client.get_request_token()
        print client.get_authorize_token_url()
        verifier = sys.stdin.readline().strip()
        print "Using ", verifier, " as verifier"
        print "Token is:", client.get_access_token(verifier)
    else:
        client = SimpleOAuthClient(options.key, options.secret,
                                   token=options.access_token,
                                   token_secret=options.access_token_secret)

#     print "getQuota"
#     client.vimeo_videos_upload_getQuota()

#     # print "test null"
#     # client.vimeo_test_null()
    
#     # print "test login"
#     # client.vimeo_test_login()

#     print "test echo"
#     client.vimeo_test_echo({'tata':'prout', 'prout':'caca'})

#     print "albums getAll"
#     client.vimeo_albums_getAll('1443699')
    
#     print "channels getAll"
#     client.vimeo_channels_getAll()

    # oauth_request = oauth.OAuthRequest.from_token_and_callback(token=token, 
    #                                                            http_url=client.authorization_url)
    # response = client.authorize_token(oauth_request)
    # print response

    # oauth_request = oauth.OAuthRequest.from_consumer_and_token(consumer, 
    #                                                            token=token, 
    #                                                            http_method='GET', 
    #                                                            http_url=RESOURCE_URL, 
    #                                                            parameters=parameters)
    # oauth_request.sign_request(signature_method_hmac_sha1, consumer, token)

if __name__ == '__main__':
    main(sys.argv)
    ##print vimeo.user_videos('dkm')



########NEW FILE########
__FILENAME__ = vimeo-upload
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2009 Marc Poulhiès
#
# Python module for Vimeo
#
# Plopifier is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Plopifier is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Plopifier.  If not, see <http://www.gnu.org/licenses/>.


"""
This script can be used to upload a video to Vimeo
It is using the 'advanced API', which is in the process
of being obsoleted by the API v2.
"""

import sys
import os
import optparse
import time
import vimeo

def main(argv):
    parser = optparse.OptionParser(
        usage='Usage: %prog [options]',
        description="Simple Vimeo uploader")

    # video_file = api_key = api_secret = authtok = title = None
    # tags=""

    parser.add_option('-f', '--video-file',
                      help="Video file to upload", metavar="video-file")
    parser.add_option('-k', '--vimeo-apikey', metavar='api-key',
                      help='set the "api_key" for vimeo')
    parser.add_option('-s', '--vimeo-secret', metavar='api-secret',
                      help='set the "secret" for vimeo')
    parser.add_option('-t', '--vimeo-authtoken', metavar='authtok',
                      help='set the "auth_token" for vimeo')
    parser.add_option('-n', '--video-title', metavar='title',
                      help='set the video title')
    parser.add_option('-g', '--video-tags', metavar='tags',
                      default="",
                      help='set the video tags as a coma separated list')

    (options, args) = parser.parse_args(argv[1:])

    if not options.video_file:
        parser.error("Missing video-file argument")

    if not (options.vimeo_apikey and options.vimeo_secret and options.vimeo_authtoken):
        parser.error("Missing vimeo credentials")

    v = vimeo.Vimeo(options.vimeo_apikey,
                    options.vimeo_secret,
                    options.vimeo_authtoken)
    v.set_userid()
    v.do_upload(options.video_file, options.video_title,
                tags=options.video_tags.split(','))

    while len(v.vimeo_bug_queue) > 0:
        v.process_bug_queue()
        time.sleep(1)

if __name__ == '__main__':
    main(sys.argv)

########NEW FILE########
__FILENAME__ = vimeo-uploadv2
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2009 Marc Poulhiès
#
# Python module for Vimeo
#
# This is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Plopifier.  If not, see <http://www.gnu.org/licenses/>.


"""
This is an upload script for Vimeo using its v2 API
"""


import vimeo
import vimeo.config
import vimeo.convenience

import sys,time
import optparse

## use a sleep to wait a few secs for vimeo servers to be synced.
## sometimes, going too fast
sleep_workaround = True

def main(argv):
    parser = optparse.OptionParser(
        usage='Usage: %prog [options]',
        description="Simple Vimeo uploader")

    # auth/appli stuff
    parser.add_option('-k', '--key',
                      help="Consumer key")
    parser.add_option('-s', '--secret',
                      help="Consumer secret")
    parser.add_option('-t', '--access-token',
                      help="Access token")
    parser.add_option('-y', '--access-token-secret',
                      help="Access token secret")
    # file upload stuff
    parser.add_option('-f', '--file',
                      help="Video file to upload")
    parser.add_option('--title',
                      help="Set the video title")
    parser.add_option('--description',
                      help="Set the video description")
    parser.add_option('--privacy',
                      help="Set the video privacy (anybody; nobody; contacts; users:u1,u2; password:pwd; disable)")
    parser.add_option('--tags',
                      help="Set the video tags (comma separated)")

    (options, args) = parser.parse_args(argv[1:])

    vconfig = vimeo.config.VimeoConfig(options)

    if not vconfig.has_option("appli", "consumer_key"):
        print "Missing consumer key"
        parser.print_help()
        sys.exit(-1)

    if not vconfig.has_option("appli", "consumer_secret"):
        print "Missing consumer secret"
        parser.print_help()
        sys.exit(-1)

    if not options.file :
        print "Missing file to upload!"
        parser.print_help()
        sys.exit(-1)

    if not (vconfig.has_option("auth", "token") and vconfig.has_option("auth", "token_secret")):
        client = vimeo.VimeoClient(key=vconfig.get("appli", "consumer_key"),
                                   secret=vconfig.get("appli", "consumer_secret"))
        client.get_request_token()
        print client.get_authorization_url(permission="write")
        verifier = sys.stdin.readline().strip()
        print "Using", verifier, "as verifier"
        print client.get_access_token(verifier)
    else:
        client = vimeo.VimeoClient(key=vconfig.get("appli", "consumer_key"),
                                   secret=vconfig.get("appli", "consumer_secret"),
                                   token=vconfig.get("auth","token"),
                                   token_secret=vconfig.get("auth", "token_secret"),
                                   format="json")

    quota = client.vimeo_videos_upload_getQuota()
    print "Your current quota is", int(quota['upload_space']['free'])/(1024*1024), "MiB"

    t = client.vimeo_videos_upload_getTicket()
    vup = vimeo.convenience.VimeoUploader(client, t, quota=quota)
    vup.upload(options.file)
    vid = vup.complete()['video_id']
    print vid
    # do we need to wait a bit for vimeo servers ?
    if sleep_workaround and (options.title or options.description or options.tags or options.privacy):
        time.sleep(5)

    if options.title:
        client.vimeo_videos_setTitle(video_id=vid, title=options.title)

    if options.description :
        client.vimeo_videos_setDescription(video_id=vid, description=options.description)

    if options.tags:
        client.vimeo_videos_addTags(video_id=vid, tags=options.tags)

    if options.privacy :
        pusers = None
        ppwd = None
        ppriv = options.privacy
        if options.privacy.startswith("users"):
            pusers = options.privacy.split(":")[1]
            ppriv = "users"
        if options.privacy.startswith("password"):
            ppwd = options.privacy.split(":")[1]
            ppriv = "password"

        client.vimeo_videos_setPrivacy(privacy=ppriv, video_id=vid, users=pusers, password=ppwd)

if __name__ == '__main__':
    main(sys.argv)



########NEW FILE########
__FILENAME__ = config
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2009 Marc Poulhiès
#
# Python module for Vimeo
# originaly part of 'plopifier'
#
# Plopifier is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Plopifier is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Plopifier.  If not, see <http://www.gnu.org/licenses/>.

import ConfigParser
import os

DEFAULT_CONFIG="~/.python-vimeo.rc"

class VimeoConfig(ConfigParser.ConfigParser):
    def __init__(self, options=None):
        ConfigParser.ConfigParser.__init__(self)

        try:
            self.read(os.path.expanduser(DEFAULT_CONFIG))
        except IOError,e:
            # most probably the file does not exist
            if os.path.exists(os.path.expanduser(DEFAULT_CONFIG)):
                # looks like it's something else
                raise e
            # if not, simply ignore the error, config is empty

        if not options :
            return

        try :
            self.add_section("appli")
        except:
            pass

        try:
            self.add_section("auth")
        except:
            pass

        if options.key:
            self.set("appli", "consumer_key", options.key)

        if options.secret:
            self.set("appli", "consumer_secret", options.secret)

        if options.access_token:
            self.set("auth", "token", options.access_token)

        if options.access_token_secret:
            self.set("auth", "token_secret", options.access_token_secret)

########NEW FILE########
__FILENAME__ = convenience

# Copyright 2010 Julian Berman
# The MIT License
#
# Copyright (c) 2010
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
Module providing convenience classes and methods for some basic API procedures.

In general, this module is more rigid than the base module, in that it relies
on some current API behavior (e.g. hard-coding some parameters in the Uploader
class) where the base module chooses to remain ambigous. While this module
shouldn't completely break either until Vimeo seriously changes their API, keep
in mind that if something in this module doesn't work, it still might work the
"conventional" way using just the base module.
"""
from os.path import getsize
from urllib import urlencode

import urllib2
import oauth2
import requests

from . import VimeoClient, VimeoError, API_REST_URL


class VimeoUploader(object):
    """
    A convenience uploader class to be used alongside a client.

    The ticket is assumed to be a dict-like object, which means that if you
    aren't using a JSON client the ticket will need to be converted first.
    """
    def __init__(self, vimeo_client, ticket, **kwargs):
        self.vimeo_client = vimeo_client
        self.endpoint = ticket["endpoint"]
        self.ticket_id = ticket["id"]
        self.max_file_size = ticket["max_file_size"]
        self.chunk_id = 0

        self.user = getattr(vimeo_client, "user", None)

        quota = kwargs.pop("quota", {})
        self.has_sd_quota = bool(quota.get("sd_quota", None))
        self.has_hd_quota = bool(quota.get("hd_quota", None))
        self.upload_space = quota.get("upload_space", {})

    def _check_file_size(self, file_size):
        if file_size > self.upload_space.get("free", file_size):
            raise VimeoError("Not enough free space to upload the file.")
        elif file_size > self.max_file_size:
            raise VimeoError("File is larger than the maximum allowed size.")

    def _post_to_endpoint(self, open_file, **kwargs):
        params = {"chunk_id" : self.chunk_id,
                  "ticket_id" : self.ticket_id}

        headers = kwargs.get("headers",
                             dict(self.vimeo_client._CLIENT_HEADERS))

        request = oauth2.Request.from_consumer_and_token(
                                          consumer=self.vimeo_client.consumer,
                                          token=self.vimeo_client.token,
                                          http_method="POST",
                                          http_url=self.endpoint,
                                          parameters=params)

        request.sign_request(self.vimeo_client.signature_method,
                             self.vimeo_client.consumer,
                             self.vimeo_client.token)

        files = {"file_data" : open_file}
        return requests.post(
            self.endpoint, data=request, files=files, headers=headers)


    def upload(self, file_path, chunk=False, chunk_size=2*1024*1024,
               chunk_complete_hook=None):
        """
        Performs the steps of an upload. Checks file size and can handle
        splitting into chunks.
        """

        file_size = getsize(file_path)
        self._check_file_size(file_size)

        ## FIXME something is missing
        if chunk:
            self.chunk_id += 1
        else:
            self._post_to_endpoint(open(file_path))


        return self.vimeo_client.vimeo_videos_upload_verifyChunks(
                                                ticket_id=self.ticket_id)

    def complete(self):
        """
        Finish an upload.
        """
        return self.vimeo_client.vimeo_videos_upload_complete(
                                                ticket_id=self.ticket_id)


########NEW FILE########
__FILENAME__ = curl
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2009 Marc Poulhiès
#
# Python module for Vimeo
# originaly part of 'plopifier'
#
# This is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Plopifier.  If not, see <http://www.gnu.org/licenses/>.


import pycurl
import xml.etree.ElementTree as ET

USER_AGENT = 'python-vimeo http://github.com/dkm/python-vimeo'
TURNING_BAR='|/-\\'

class CurlyRestException(Exception):
    def __init__(self, code, msg, full):
        Exception.__init__(self)
        self.code = code
        self.msg = msg
        self.full = full

    def __str__(self):
        return "Error code: %s, message: %s\nFull message: %s" % (self.code, 
                                                                  self.msg, 
                                                                  self.full)
class CurlyRequest:
    """
    A CurlyRequest object is used to send HTTP requests.
    It's a simple wrapper around basic curl methods.
    In particular, it can upload files and display a progress bar.
    """
    def __init__(self, pbarsize=19):
        self.buf = None
        self.pbar_size = pbarsize
        self.pidx = 0

    def do_rest_call(self, url):
        """
        Send a simple GET request and interpret the answer as a REST reply.
        """

        res = self.do_request(url)
        try:
            t = ET.fromstring(res)

            if t.attrib['stat'] == 'fail':
                err_code = t.find('err').attrib['code']
                err_msg = t.find('err').attrib['msg']
                raise CurlyRestException(err_code, err_msg, ET.tostring(t))
            return t
        except Exception,e:
            print "Error with:", res
            raise e

    def _body_callback(self, buf):
        self.buf += buf
        return len(buf)

    def do_request(self, url):
        """
        Send a simple GET request
        """

        self.buf = ""
        curl = pycurl.Curl()
        curl.setopt(pycurl.USERAGENT, USER_AGENT)
        curl.setopt(curl.URL, url)
        curl.setopt(curl.WRITEFUNCTION, self._body_callback)
        curl.perform()
        curl.close()
        p = self.buf
        self.buf = ""
        return p
    
    def _upload_progress(self, download_t, download_d, upload_t, upload_d):
        # this is only for upload progress bar
	if upload_t == 0:
            return 0

        self.pidx = (self.pidx + 1) % len(TURNING_BAR)

        done = int(self.pbar_size * upload_d / upload_t)

        if done != self.pbar_size:
            pstr = '#'*done  +'>' + ' '*(self.pbar_size - done - 1)
        else:
            pstr = '#'*done

        print "\r%s[%s]  " %(TURNING_BAR[self.pidx], pstr),
        return 0
        
    def do_post_call(self, url, args, use_progress=False, progress_callback=None):
        """
        Send a simple POST request
        """
        if progress_callback:
            my_cb = progress_callback
        else:
            my_cb = self._upload_progress

        c = pycurl.Curl()
        c.setopt(c.POST, 1)
        c.setopt(c.URL, url)
        c.setopt(c.HTTPPOST, args)
        c.setopt(c.WRITEFUNCTION, self._body_callback)
        #c.setopt(c.VERBOSE, 1)
        self.buf = ""

        c.setopt(c.NOPROGRESS, 0)
        
        if use_progress:
            c.setopt(c.PROGRESSFUNCTION, my_cb)

        c.perform()
        c.close()
        res = self.buf
        self.buf = ""
        return res

########NEW FILE########
