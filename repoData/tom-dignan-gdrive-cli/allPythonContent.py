__FILENAME__ = helper
"""
Helper methods for database
"""

import sqlite3
import os

def connect():
    home = os.getenv("HOME")

    #windows
    if home is None:
        home = os.getenv("HOMEPATH")

    dbpath = home + os.path.sep + ".gdrive-cli.db"
    return sqlite3.connect(dbpath)

def insert_file(metadata):
    """
    Inserts file metadata returned by gdrive.insert_file into the
    tbl_files table and tables related to it.

    Returns:
        id of the inserted data
    """

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO tbl_files (
            createdDate,
            description,
            downloadUrl,
            etag,
            fileExtension,
            fileSize,
            id,
            kind,
            lastViewedDate,
            md5Checksum,
            mimeType,
            modifiedByMeDate,
            modifiedDate,
            title
        ) VALUES (
           ?,?,?,?,?,?,?,?,?,?,?,?,?,?
        );
        """, (
            metadata["createdDate"],
            metadata["description"],
            metadata["downloadUrl"],
            metadata["etag"],
            metadata["fileExtension"],
            metadata["fileSize"],
            metadata["id"],
            metadata["kind"],
            metadata["lastViewedDate"],
            metadata["md5Checksum"],
            metadata["mimeType"],
            metadata["modifiedByMeDate"],
            metadata["modifiedDate"],
            metadata["title"],
            )
        );

    cursor.execute("""
        INSERT INTO tbl_labels (
            files_id,
            hidden,
            starred,
            trashed
        ) VALUES (
            ?,?,?,?
        );
        """, (
            metadata["id"],
            metadata["labels"]["hidden"],
            metadata["labels"]["starred"],
            metadata["labels"]["trashed"],
        )
    );

    for parent in metadata["parentsCollection"]:
        cursor.execute("""
            INSERT INTO tbl_parentsCollection (
                files_id,
                parent_id,
                parentLink
            ) VALUES (
                ?,?,?
            );
            """, (
                metadata["id"],
                parent["id"],
                parent["parentLink"],
            )
        );

    cursor.execute("""
        INSERT INTO tbl_userPermission (
            files_id,
            etag,
            kind,
            role,
            type
        ) VALUES (
            ?,?,?,?,?
        )
        """, (
            metadata["id"],
            metadata["userPermission"]["etag"],
            metadata["userPermission"]["kind"],
            metadata["userPermission"]["role"],
            metadata["userPermission"]["type"],
        )
    );


    conn.commit()
    cursor.close()

    return metadata["id"]


def rename_file(file_id, name):
    """
    Renames the file in the local sqlite database to reflect the remote change.
    Infers fileExtension from the filename.

    Returns:
        id of renamed file
    """
    conn = connect()
    cursor = conn.cursor()

    tokens = name.split(".")
    fileExtension = tokens[len(tokens) - 1]

    cursor.execute("""
        UPDATE tbl_files
        SET title = ?,  fileExtension = ?
        WHERE id = ?;
        """, (
            name,
            fileExtension,
            file_id
        ))

    conn.commit()
    cursor.close()

    return file_id

def update_file(metadata):
    """
    Updates file metadata returned by gdrive.update_file into the
    tbl_files table and tables related to it.

    Returns:
        id of the inserted data
    """

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE tbl_files
        SET createdDate = ?,
            description = ?, 
            downloadUrl = ?, 
            etag = ?, 
            fileExtension = ?, 
            fileSize = ?, 
            kind = ?, 
            lastViewedDate = ?, 
            md5Checksum = ?, 
            mimeType = ?, 
            modifiedBymeDate = ?, 
            modifiedDate = ?, 
            title = ?
        WHERE id = ?;
        """, (
            metadata["createdDate"],
            metadata["description"],
            metadata["downloadUrl"],
            metadata["etag"],
            metadata["fileExtension"],
            metadata["fileSize"],
            metadata["kind"],
            metadata["lastViewedDate"],
            metadata["md5Checksum"],
            metadata["mimeType"],
            metadata["modifiedByMeDate"],
            metadata["modifiedDate"],
            metadata["title"],
            metadata["id"],
        )
    );

    cursor.execute("""
        UPDATE tbl_labels
        SET hidden = ?,
            starred = ?,
            trashed = ?
        WHERE files_id = ?;
        """, (
            metadata["labels"]["hidden"],
            metadata["labels"]["starred"],
            metadata["labels"]["trashed"],
            metadata["id"],
        )
    );

    for parent in metadata["parentsCollection"]:
        cursor.execute("""
            UPDATE tbl_parentsCollection
            SET parent_id = ?,
                parentLink = ?
            WHERE files_id = ?
            """, (
                parent["id"],
                parent["parentLink"],
                metadata["id"],
            )
        );

    cursor.execute("""
        UPDATE tbl_userPermission 
        SET etag = ?,
            kind = ?,
            role = ?,
            type = ?
        WHERE files_id = ?;
        """, (
            metadata["userPermission"]["etag"],
            metadata["userPermission"]["kind"],
            metadata["userPermission"]["role"],
            metadata["userPermission"]["type"],
            metadata["id"],
        )
    );

    conn.commit()
    cursor.close()

    return metadata["id"]


def select_all_files():
    """
    Generates a basic listing of files in tbl_files
    """
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT title, id FROM tbl_files")
    files = cursor.fetchall()
    cursor.close()
    conn.commit()

    return files



def get_file_id_by_name(file_name):
    """
    Returns the id associated with 'file_name' 
    """
    file_name = file_name.strip()

    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM tbl_files WHERE title = ?; ",
        (file_name,))

    file_id = cursor.fetchone()

    cursor.close()
    conn.commit()

    return file_id[0]





########NEW FILE########
__FILENAME__ = schema
#!/usr/bin/env python

from helper import connect

def create_schema():
    conn = connect()
    cursor = conn.cursor()

    """
    tbl_files
        -> tbl_labels
        -> tbl_parentsCollection
        -> tbl_userPermission
    """
    cursor.execute("""
        CREATE TABLE tbl_files (
            createdDate TEXT,
            description TEXT,
            downloadUrl TEXT,
            etag TEXT,
            fileExtension TEXT,
            fileSize TEXT,
            id TEXT PRIMARY KEY,
            kind TEXT,
            lastViewedDate TEXT,
            md5Checksum TEXT,
            mimeType TEXT,
            modifiedByMeDate TEXT,
            modifiedDate TEXT,
            title TEXT
        );
        """)

    """
        tbl_labels
            <- tbl_files
    """
    cursor.execute("""
        CREATE TABLE tbl_labels (
            files_id TEXT,
            hidden INTEGER,
            starred INTEGER,
            trashed INTEGER,
            FOREIGN KEY (files_id) REFERENCES tbl_files(id)
            );
        """)

    """
        tbl_parentsCollection
            <- tbl_files
    """
    cursor.execute("""
        CREATE TABLE tbl_parentsCollection (
            files_id TEXT,
            parent_id TEXT,
            parentLink TEXT,
            FOREIGN KEY (files_id) REFERENCES tbl_files(id)
            );
        """)


    """
        tbl_userPermission
            <- tbl_files
    """
    cursor.execute("""
        CREATE TABLE tbl_userPermission (
            files_id TEXT,
            etag TEXT,
            kind TEXT,
            role TEXT,
            type TEXT,
            FOREIGN KEY (files_id) REFERENCES tbl_files(id)
            );
        """)

    conn.commit()
    cursor.close()

if __name__ == "__main__":
    import sys

    if len(sys.argv) == 2:
        print "creating database"
        create_schema()
        print "done"
    else:
        print "usage: ./schema.py create"



########NEW FILE########
__FILENAME__ = gdrive
from apiclient import errors
from apiclient.discovery import build
from apiclient.http import MediaFileUpload
import httplib2
import traceback
import os
"""
Google Drive python module. The code in this file is taken directly from
Google's API reference.

https://developers.google.com/drive/v1/reference/

ALL CODE IN THIS FILE IS A DERIVED WORK OF THE SDK EXAMPLE CODE.

Copyright 2012 Thomas Dignan <tom@tomdignan.com>

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

################################################################################
# Service Object (do this first)                                                                                             #
################################################################################

def build_service(credentials):
    """Build a Drive service object.

    Args:
        credentials: OAuth 2.0 credentials.

    Returns:
        Drive service object.
    """
    http = httplib2.Http()
    http = credentials.authorize(http)
    return build('drive', 'v1', http=http)

################################################################################
# Files: get                                                                                                                                     #
################################################################################

def print_file(service, file_id):
    """Print a file's metadata.

    Args:
        service: Drive API service instance.
        file_id: ID of the file to print metadata for.
    """
    try:
        file = service.files().get(id=file_id).execute()

        print 'Title: %s' % file['title']
        print 'Description: %s' % file['description']
        print 'MIME type: %s' % file['mimeType']
    except errors.HttpError, error:
        print 'An error occurred: %s' % error

def get_file_instance(service, file_id):
    """Print a file's metadata.

    Args:
        service: Drive API service instance.
        file_id: ID of the file to print metadata for.

    Returns:
        file instance or None
    """
    try:
        file = service.files().get(id=file_id).execute()
        return file
    except errors.HttpError, error:
        print 'An error occurred: %s' % error
        return None

def download_file_by_id(service, file_id):
    """
    Download file content by id
    """
    drive_file = get_file_instance(service, file_id)
    return download_file(service, drive_file)

def download_file(service, drive_file):
    """Download a file's content.

    Args:
        service: Drive API service instance.
        drive_file: Drive File instance.

    Returns:
        File's content if successful, None otherwise.
    """
    download_url = drive_file.get('downloadUrl')
    if download_url:
        resp, content = service._http.request(download_url)
        if resp.status == 200:
            #print 'Status: %s' % resp
            return content
        else:
            print 'An error occurred: %s' % resp
            return None
    else:
        # The file doesn't have any content stored on Drive.
        return None

################################################################################
# Files: insert                                                                                                                                #
################################################################################

def insert_file(service, title, description, parent_id, mime_type, filename):
    """Insert new file.

    Args:
        service: Drive API service instance.
        title: Title of the file to insert, including the extension.
        description: Description of the file to insert.
        parent_id: Parent folder's ID.
        mime_type: MIME type of the file to insert.
        filename: Filename of the file to insert.
    Returns:
        Inserted file metadata if successful, None otherwise.
    """
    if os.path.getsize(filename) > 5*2**20:
        media_body = MediaFileUpload(filename, mimetype=mime_type, chunksize=1024*1024, resumable=True)
    else:
        media_body = MediaFileUpload(filename, mimetype=mime_type)
    body = {
        'title': title,
        'description': description,
        'mimeType': mime_type
    }

    # Set the parent folder.
    if parent_id:
        body['parentsCollection'] = [{'id': parent_id}]


    try:
        file = service.files().insert(
                body=body,
                media_body=media_body).execute()

        # Uncomment the following line to print the File ID
        # print 'File ID: %s' % file['id']

        return file
    except errors.HttpError, error:
        print "TRACEBACK"
        print traceback.format_exc()
        print 'An error occured: %s' % error
        return None


################################################################################
# Files: patch                                                                                                                                #
################################################################################

def rename_file(service, file_id, new_title):
    """Rename a file.

    Args:
        service: Drive API service instance.
        file_id: ID of the file to rename.
        new_title: New title for the file.
    Returns:
        Updated file metadata if successful, None otherwise.
    """
    try:
        file = {'title': new_title}

        # Rename the file.
        updated_file = service.files().patch(
                id=file_id,
                body=file,
                fields='title').execute()

        return updated_file
    except errors.HttpError, error:
        print 'An error occurred: %s' % error
        return None

################################################################################
# Files: delete                                                                                                                                #
################################################################################

def delete_file_by_id(service, file_id):
    """Delete a file.

    Args:
        service: Drive API Service instance.
        file_id: ID of the file to delete.
    Returns:
        Success status message if successful, None otherwise.
    """
    try:
        delete_file = service.files().delete(
            id=file_id).execute()

        return file_id
    except errors.HttpError, error:
        print 'An error occurred: $s' % error
        return None
        


################################################################################
# Files: update                                                                                                                                #
################################################################################

def update_file(service, file_id, new_title, new_description, new_mime_type,
                                new_filename, new_revision):
    """Update an existing file's metadata and content.

    Args:
        service: Drive API service instance.
        file_id: ID of the file to update.
        new_title: New title for the file.
        new_description: New description for the file.
        new_mime_type: New MIME type for the file.
        new_filename: Filename of the new content to upload.
        new_revision: Whether or not to create a new revision for this file.
    Returns:
        Updated file metadata if successful, None otherwise.
    """
    try:
        # First retrieve the file from the API.
        file = service.files().get(id=file_id).execute()

        # File's new metadata.
        file['title'] = new_title
        file['description'] = new_description
        file['mimeType'] = new_mime_type

        # File's new content.
        if os.path.getsize(new_filename) > 5*2**20:
            media_body = MediaFileUpload(new_filename, mimetype=new_mime_type, chunksize=1024*1024, resumable=True)
        else:
            media_body = MediaFileUpload(new_filename, mimetype=new_mime_type, resumable=False)

        # Send the request to the API.
        updated_file = service.files().update(
                id=file_id,
                body=file,
                newRevision=new_revision,
                media_body=media_body).execute()
        return updated_file
    except errors.HttpError, error:
        print 'An error occurred: %s' % error
        return None

########NEW FILE########
__FILENAME__ = gdrive-cli
#!/usr/bin/env python
"""
Copyright 2012 Thomas Dignan <tom@tomdignan.com>

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

gdrive-cli.py command line google drive client.

Author: Tom Dignan <tom.dignan@gmail.com>
Date: Fri Apr 27 16:00:35 EDT 2012
Official Docs: https://developers.google.com/drive/
"""

import argparse
from oauth import simple_cli
from gdrive import gdrive
from os import getenv
import pickle
from db import helper as dbhelper
from db import schema as dbschema

def get_stored_credentials_path():
    home = getenv("HOME")

    # windows compat
    if home is None:
        home = getenv("HOMEPATH")

    return home + "/.gdrive_oauth"

def get_service_object():
    credentials = get_stored_credentials()
    return gdrive.build_service(credentials)

def store_credentials():
    credentials = simple_cli.authenticate()
    pickled_creds_path = get_stored_credentials_path()
    pickle.dump(credentials, open(pickled_creds_path, "wb"))

def authenticate():
    store_credentials()

def get_stored_credentials():
    pickled_creds_path = get_stored_credentials_path()
    return pickle.load(open(pickled_creds_path, "rb"))

def make_argparser():
    """
    ArgumentParser factory 
    """
    parser = argparse.ArgumentParser(description="gdrive-cli: google drive interface",
        epilog="Author: Tom Dignan <tom.dignan@gmail.com>")

    parser.add_argument("--init-database", help="must be run after install once to initialize the user local database", action="store_true")

    parser.add_argument("--authenticate", help="must be done before using other methods", action="store_true")

    parser.add_argument("--show", help="show file metadata", metavar="<file_id>")

#    parser.add_argument("--easy-upload", help="like insert, but easier", metavar=("<file_name>", "<mime_type"))

    parser.add_argument("--list", help="list application's files (uses local database)", action="store_true")

    parser.add_argument("--download", help="download file contents and print to stdout", metavar="<drive_file>")

    parser.add_argument("--insert", help="insert new file", nargs=5,
            metavar=("<title -- must include file ext>", "<description>", "<parent_id (if none, pass none)>", "<mime_type>", "<filename>"))

    parser.add_argument("--rename", help="rename a file", nargs=2,
            metavar=("<file_id>", "<new_title>"))

    parser.add_argument("--easy-rename", help="rename a file by name", nargs=2,
            metavar=("<original_name>", "<new_name>"))

    parser.add_argument("--update", help="update a file", nargs=6,
            metavar=("<file_id>", "<new_title>", "<new_description>", "<new_mime_type>",
                "<new_filename>", "<new_revision>"))

    return parser

def handle_args(args):
    if args.authenticate is True:
        handle_authenticate()
    elif args.list is True:
        handle_list()
    elif args.show is not None:
        handle_show(args.show)
    elif args.download is not None:
        handle_download(args.download)
    elif args.insert is not None:
        handle_insert(args.insert)
    elif args.rename is not None:
        handle_rename(args.rename)
    elif args.update is not None:
        handle_update(args.update)
    elif args.init_database is True:
        handle_init_database()
    elif args.easy_rename is not None:
        handle_easy_rename(args.easy_rename)

def handle_authenticate():
    authenticate()

def handle_show(file_id):
    service = get_service_object()
    gdrive.print_file(service, file_id)

def handle_download(file_id):
    service = get_service_object()
    download = gdrive.download_file_by_id(service, file_id)
    print download

def handle_insert(args):
    service = get_service_object()

    title = args[0]
    description = args[1]
    parent_id = args[2]

    if parent_id == "none":
        parent_id = None

    mime_type = args[3]
    filename = args[4]

    file = gdrive.insert_file(service, title, description, parent_id, mime_type,
            filename)

    id = dbhelper.insert_file(file)
    print "Inserted file ", id

def handle_list():
    files = dbhelper.select_all_files()
    print "filename\t\t\tid"
    for f in files:
        print "%(title)s\t\t%(id)s" % { "title" : f[0], "id" : f[1] }

def rename_file(file_id, new_name):
    service = get_service_object()
    gdrive.rename_file(service, file_id, new_name)
    dbhelper.rename_file(file_id, new_name)
    print "renamed %(file_id)s to %(new_name)s" % {"file_id" :
            file_id, "new_name" : new_name }

def handle_rename(args):
    file_id = args[0]
    new_name = args[1]
    rename_file(file_id, new_name)

def handle_easy_rename(args):
    service = get_service_object()
    old_name = args[0]
    new_name = args[1]
    
    old_id = dbhelper.get_file_id_by_name(old_name)

    if old_id is None:
        print "Unknown file: %s" % old_name
        return

    rename_file(old_id, new_name)

def handle_update(args):
    service = get_service_object()

    file_id = args[0]
    new_title = args[1]
    new_description = args[2]
    new_mime_type = args[3]
    new_filename = args[4]
    new_revision = args[5]

    if new_revision == "false":
        new_revision = False
    else:
        new_revision = True
        

    file = gdrive.update_file(service, file_id, new_title, new_description, new_mime_type, new_filename, new_revision)

    id = dbhelper.update_file(file)
    print "Updated file ", id

def handle_init_database():
    print "Creating database..."
    dbschema.create_schema()
    print "done."


if __name__ == "__main__":
    parser = make_argparser()
    args = parser.parse_args()
    handle_args(args)




########NEW FILE########
__FILENAME__ = simple_cli
""" Copyright 2012 Thomas Dignan <tom@tomdignan.com>

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""
import httplib2
from apiclient.discovery import build
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import run
from pprint import pprint
import os
import sys

home = os.getenv("HOME")

# windows
if home is None:
    home = os.getenv("HOMEPATH")

global_location = "/etc/gdrive-client"
local_location = home + "/.gdrive_client_secrets"
test_location = ".private/client_secrets.json"

if os.path.isfile(test_location):
    client_secrets_location = test_location
elif os.path.isfile(local_location):
    client_secrets_location = local_location
elif os.path.isfile(global_location):
    client_secrets_location = global_location
else:
    print "No client_secrets.json file was found! Exiting."
    sys.exit(1)

SCOPES = [
        'https://www.googleapis.com/auth/drive.file',
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/userinfo.profile',
]

def authenticate():
    """
    Authenticates and returns OAuth2 credentials.

    Warning, this launches a web browser! You will need to click.
    """
    storage_path = home + "/.gdrivefs.dat"
    storage = Storage(storage_path)
    flow = flow_from_clientsecrets(client_secrets_location, ' '.join(SCOPES))
    credentials = run(flow, storage)
    return credentials


########NEW FILE########
