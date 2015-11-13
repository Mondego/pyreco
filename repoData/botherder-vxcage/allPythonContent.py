__FILENAME__ = api
#!/usr/bin/env python
# Copyright (c) 2012, Claudio "nex" Guarnieri
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# -*- coding: utf-8 -*-

import os
import argparse

from bottle import route, request, response, run
from bottle import HTTPError

from objects import File
from database import Database
from utils import jsonize, store_sample, get_sample_path

db = Database()

@route("/test", method="GET")
def test():
    return jsonize({"message" : "test"})

@route("/malware/add", method="POST")
def add_malware():
    tags = request.forms.get("tags")
    data = request.files.file
    info = File(file_path=store_sample(data.file.read()))

    db.add(obj=info, file_name=data.filename, tags=tags)

    return jsonize({"message" : "added"})

@route("/malware/get/<sha256>", method="GET")
def get_malware(sha256):
    path = get_sample_path(sha256)
    if not path:
        raise HTTPError(404, "File not found")

    response.content_length = os.path.getsize(path)
    response.content_type = "application/octet-stream; charset=UTF-8"
    data = open(path, "rb").read()

    return data

@route("/malware/find", method="POST")
def find_malware():
    def details(row):
        tags = []
        for tag in row.tag:
            tags.append(tag.tag)

        entry = {
            "id" : row.id,
            "file_name" : row.file_name,
            "file_type" : row.file_type,
            "file_size" : row.file_size,
            "md5" : row.md5,
            "sha1" : row.sha1,
            "sha256" : row.sha256,
            "sha512" : row.sha512,
            "crc32" : row.crc32,
            "ssdeep": row.ssdeep,
            "created_at": row.created_at.__str__(),
            "tags" : tags
        }

        return entry

    md5 = request.forms.get("md5")
    sha256 = request.forms.get("sha256")
    ssdeep = request.forms.get("ssdeep")
    tag = request.forms.get("tag")
    date = request.forms.get("date")

    if md5:
        row = db.find_md5(md5)
        if row:
            return jsonize(details(row))
        else:
            raise HTTPError(404, "File not found")
    elif sha256:
        row = db.find_sha256(sha256)
        if row:
            return jsonize(details(row))
        else:
            raise HTTPError(404, "File not found")
    else:
        if ssdeep:
            rows = db.find_ssdeep(ssdeep)
        elif tag:
            rows = db.find_tag(tag)
        elif date:
            rows = db.find_date(date)
        else:
            return HTTPError(400, "Invalid search term")

        if not rows:
            return HTTPError(404, "File not found")

        results = []
        for row in rows:
            entry = details(row)
            results.append(entry)

        return jsonize(results)

@route("/tags/list", method="GET")
def list_tags():
    rows = db.list_tags()

    results = []
    for row in rows:
        results.append(row.tag)

    return jsonize(results)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-H", "--host", help="Host to bind the API server on", default="localhost", action="store", required=False)
    parser.add_argument("-p", "--port", help="Port to bind the API server on", default=8080, action="store", required=False)
    args = parser.parse_args()

    run(host=args.host, port=args.port)

########NEW FILE########
__FILENAME__ = vxcage
#!/usr/bin/env python
# Copyright (c) 2012, Claudio "nex" Guarnieri
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# -*- coding: utf-8 -*-

import os
import sys
import getpass
import argparse

try:
    import requests
    from progressbar import *
    from prettytable import PrettyTable
except ImportError as e:
    sys.exit("ERROR: Missing dependency: %s" % e)

def color(text, color_code):
    return '\x1b[%dm%s\x1b[0m' % (color_code, text)

def cyan(text):
    return color(text, 36)

def bold(text):
    return color(text, 1)

def logo():
    print("")
    print(cyan("  `o   O o   O .oOo  .oOoO' .oOoO .oOo. "))
    print(cyan("   O   o  OoO  O     O   o  o   O OooO' "))
    print(cyan("   o  O   o o  o     o   O  O   o O     "))
    print(cyan("   `o'   O   O `OoO' `OoO'o `OoOo `OoO' "))
    print(cyan("                                O       "))
    print(cyan("                             OoO' ") + " by nex")
    print("")

def help():
    print("Available commands:")
    print("  " + bold("help") + "        Show this help")
    print("  " + bold("tags") + "        Retrieve list of tags")
    print("  " + bold("find") + "        Find a file by md5, sha256, ssdeep, tag or date")
    print("  " + bold("get") + "         Retrieve a file by sha256")
    print("  " + bold("add") + "         Upload a file to the server")

class VxCage(object):
    def __init__(self, host, port, ssl=False, auth=False):
        self.host = host
        self.port = port
        self.ssl = ssl
        self.auth = auth
        self.username = None
        self.password = None

    def authenticate(self):
        if self.auth:
            self.username = raw_input("Username: ")
            self.password = getpass.getpass("Password: ")

    def build_url(self, route):
        if self.ssl:
            url = "https://"
            self.port = 443
        else:
            url = "http://"
        
        url += "%s:%s%s" % (self.host, self.port, route)

        return url

    def check_errors(self, code):
        if code == 400:
            print("ERROR: Invalid request format")
            return True
        elif code == 500:
            print("ERROR: Unexpected error, check your server logs")
            return True
        else:
            return False

    def tags_list(self):
        req = requests.get(self.build_url("/tags/list"),
                           auth=(self.username, self.password),
                           verify=False)
        try:
            res = req.json()
        except:
            try:
                res = req.json
            except Exception as e:
                print("ERROR: Unable to parse results: {0}".format(e))
                return

        if self.check_errors(req.status_code):
            return

        table = PrettyTable(["tag"])
        table.align = "l"
        table.padding_width = 1

        for tag in res:
            table.add_row([tag])

        print(table)
        print("Total: %s" % len(res))

    def find_malware(self, term, value):
        term = term.lower()
        terms = ["md5", "sha256", "ssdeep", "tag", "date"]

        if not term in terms:
            print("ERROR: Invalid search term [%s]" % (", ".join(terms)))
            return

        payload = {term : value}
        req = requests.post(self.build_url("/malware/find"),
                            data=payload,
                            auth=(self.username, self.password),
                            verify=False)
        try:
            res = req.json()
        except:
            try:
                res = req.json
            except Exception as e:
                print("ERROR: Unable to parse results: {0}".format(e))
                return

        if req.status_code == 404:
            print("No file found matching your search")
            return
        if self.check_errors(req.status_code):
            return

        if isinstance(res, dict):
            for key, value in res.items():
                if key == "tags":
                    print("%s: %s" % (bold(key), ",".join(value)))
                else:
                    print("%s: %s" % (bold(key), value))
        else:
            table = PrettyTable(["md5",
                                 "sha256",
                                 "file_name",
                                 "file_type",
                                 "file_size",
                                 "tags"])
            table.align = "l"
            table.padding_width = 1

            for entry in res:
                table.add_row([entry["md5"],
                               entry["sha256"],
                               entry["file_name"],
                               entry["file_type"],
                               entry["file_size"],
                               ", ".join(entry["tags"])])

            print(table)
            print("Total: %d" % len(res))

    def get_malware(self, sha256, path):
        if not os.path.exists(path):
            print("ERROR: Folder does not exist at path %s" % path)
            return

        if not os.path.isdir(path):
            print("ERROR: The path specified is not a directory.")
            return

        req = requests.get(self.build_url("/malware/get/%s" % sha256),
                           auth=(self.username, self.password),
                           verify=False)

        if req.status_code == 404:
            print("File not found")
            return
        if self.check_errors(req.status_code):
            return

        size = int(req.headers["Content-Length"].strip())
        bytes = 0

        widgets = [
            "Download: ",
            Percentage(),
            " ",
            Bar(marker=":"),
            " ",
            ETA(),
            " ",
            FileTransferSpeed()
        ]
        progress = ProgressBar(widgets=widgets, maxval=size).start()

        destination = os.path.join(path, sha256)
        binary = open(destination, "wb")

        for buf in req.iter_content(1024):
            if buf:
                binary.write(buf)
                bytes += len(buf)
                progress.update(bytes)

        progress.finish()
        binary.close()

        print("File downloaded at path: %s" % destination)

    def add_malware(self, path, tags=None):
        if not os.path.exists(path):
            print("ERROR: File does not exist at path %s" % path)
            return

        files = {"file": (os.path.basename(path), open(path, "rb"))}
        payload = {"tags" : tags}

        req = requests.post(self.build_url("/malware/add"),
                            auth=(self.username, self.password),
                            verify=False,
                            files=files,
                            data=payload)

        if not self.check_errors(req.status_code):
            print("File uploaded successfully")

    def run(self):
        self.authenticate()

        while True:
            try:
                raw = raw_input(cyan("vxcage> "))
            except KeyboardInterrupt:
                print("")
                continue
            except EOFError:
                print("")
                break

            command = raw.strip().split(" ")

            if command[0] == "help":
                help()
            elif command[0] == "tags":
                self.tags_list()
            elif command[0] == "find":
                if len(command) == 3:
                    self.find_malware(command[1], command[2])
                else:
                    print("ERROR: Missing arguments (e.g. \"find <key> <value>\")")
            elif command[0] == "get":
                if len(command) == 3:
                    self.get_malware(command[1], command[2])
                else:
                    print("ERROR: Missing arguments (e.g. \"get <sha256> <path>\")")
            elif command[0] == "add":
                if len(command) == 2:
                    self.add_malware(command[1])
                elif len(command) == 3:
                    self.add_malware(command[1], command[2])
                else:
                    print("ERROR: Missing arguments (e.g. \"add <path> <comma separated tags>\")")
            elif command[0] == "quit" or command[0] == "exit":
                break

if __name__ == "__main__":
    logo()

    parser = argparse.ArgumentParser()
    parser.add_argument("-H", "--host", help="Host of VxCage server", default="localhost", action="store", required=False)
    parser.add_argument("-p", "--port", help="Port of VxCage server", default=8080, action="store", required=False)
    parser.add_argument("-s", "--ssl", help="Enable if the server is running over SSL", default=False, action="store_true", required=False)
    parser.add_argument("-a", "--auth", help="Enable if the server is prompting an HTTP authentication", default=False, action="store_true", required=False)
    args = parser.parse_args()

    vx = VxCage(host=args.host, port=args.port, ssl=args.ssl, auth=args.auth)
    vx.run()

########NEW FILE########
__FILENAME__ = database
# Copyright (c) 2012, Claudio "nex" Guarnieri
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Enum, Text, ForeignKey, Table, Index, and_
from sqlalchemy.orm import relationship, backref, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.pool import NullPool

from objects import File, Config
from datetime import datetime

Base = declarative_base()

association_table = Table('association', Base.metadata,
    Column('tag_id', Integer, ForeignKey('tag.id')),
    Column('malware_id', Integer, ForeignKey('malware.id'))
)

class Malware(Base):
    __tablename__ = "malware"

    id = Column(Integer(), primary_key=True)
    file_name = Column(String(255), nullable=True)
    file_size = Column(Integer(), nullable=False)
    file_type = Column(Text(), nullable=True)
    md5 = Column(String(32), nullable=False, index=True)
    crc32 = Column(String(8), nullable=False)
    sha1 = Column(String(40), nullable=False)
    sha256 = Column(String(64), nullable=False, index=True)
    sha512 = Column(String(128), nullable=False)
    ssdeep = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=False), default=datetime.now(), nullable=False)
    tag = relationship("Tag",
                       secondary=association_table,
                       backref="malware")
    __table_args__ = (Index("hash_index",
                            "md5",
                            "crc32",
                            "sha1",
                            "sha256",
                            "sha512",
                            unique=True), )

    def to_dict(self):
        row_dict = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            row_dict[column.name] = value

        return row_dict

    def __repr__(self):
        return "<Malware('%s','%s')>" % (self.id, self.md5)

    def __init__(self,
                 md5,
                 crc32,
                 sha1,
                 sha256,
                 sha512,
                 file_size,
                 file_type=None,
                 ssdeep=None,
                 file_name=None):
        self.md5 = md5
        self.sha1 = sha1
        self.crc32 = crc32
        self.sha256 = sha256
        self.sha512 = sha512
        self.file_size = file_size
        self.file_type = file_type
        self.ssdeep = ssdeep
        self.file_name = file_name

class Tag(Base):
    __tablename__ = "tag"

    id = Column(Integer(), primary_key=True)
    tag = Column(String(255), nullable=False, unique=True, index=True)

    def to_dict(self):
        row_dict = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            row_dict[column.name] = value

        return row_dict

    def __repr__(self):
        return "<Tag ('%s','%s'>" % (self.id, self.tag)

    def __init__(self, tag):
        self.tag = tag

class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class Database:

    __metaclass__ = Singleton

    def __init__(self):
        self.engine = create_engine(Config().api.database, poolclass=NullPool)
        self.engine.echo = False
        self.engine.pool_timeout = 60

        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def __del__(self):
        self.engine.dispose()

    def add(self, obj, file_name, tags=None):
        session = self.Session()

        if isinstance(obj, File):
            try:
                malware_entry = Malware(md5=obj.get_md5(),
                                        crc32=obj.get_crc32(),
                                        sha1=obj.get_sha1(),
                                        sha256=obj.get_sha256(),
                                        sha512=obj.get_sha512(),
                                        file_size=obj.get_size(),
                                        file_type=obj.get_type(),
                                        ssdeep=obj.get_ssdeep(),
                                        file_name=file_name)
                session.add(malware_entry)
                session.commit()
            except IntegrityError:
                session.rollback()
                malware_entry = session.query(Malware).filter(Malware.md5 == obj.get_md5()).first()
            except SQLAlchemyError:
                session.rollback()
                return False

        if tags:
            tags = tags.strip()
            if "," in tags:
                tags = tags.split(",")
            else:
                tags = tags.split(" ")

            for tag in tags:
                tag = tag.strip().lower()
                if tag == "":
                    continue

                try:
                    malware_entry.tag.append(Tag(tag))
                    session.commit()
                except IntegrityError as e:
                    session.rollback()
                    try:
                        malware_entry.tag.append(session.query(Tag).filter(Tag.tag==tag).first())
                        session.commit()
                    except SQLAlchemyError:
                        session.rollback()

        return True

    def find_md5(self, md5):
        session = self.Session()
        row = session.query(Malware).filter(Malware.md5 == md5).first()
        return row

    def find_sha256(self, sha256):
        session = self.Session()
        row = session.query(Malware).filter(Malware.sha256 == sha256).first()
        return row

    def find_tag(self, tag):
        session = self.Session()
        rows =  session.query(Malware).filter(Malware.tag.any(Tag.tag == tag.lower())).all()
        return rows

    def find_ssdeep(self, ssdeep):
        session = self.Session()
        rows = session.query(Malware).filter(Malware.ssdeep.like("%" + str(ssdeep) + "%")).all()
        return rows

    def find_date(self, date):
        session = self.Session()

        date_min = datetime.strptime(date, "%Y-%m-%d")
        date_max = date_min.replace(hour=23, minute=59, second=59)

        rows = session.query(Malware).filter(and_(Malware.created_at >= date_min, Malware.created_at <= date_max)).all()
        return rows

    def list_tags(self):
        session = self.Session()
        rows = session.query(Tag).all()
        return rows

########NEW FILE########
__FILENAME__ = objects
# Copyright (c) 2012, Claudio "nex" Guarnieri
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os
import hashlib
import binascii
import ConfigParser

try:
    import magic
except ImportError:
    pass

try:
    import pydeep
    HAVE_SSDEEP = True
except ImportError:
    HAVE_SSDEEP = False

class Dictionary(dict):
    def __getattr__(self, key):
        return self.get(key, None)

    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

class File:
    def __init__(self, file_path=None, file_data=None):
        self.file_path = file_path

        if file_path:
            self.file_data = open(self.file_path, "rb").read()
        else:
            self.file_data = file_data

    def get_name(self):
        file_name = os.path.basename(self.file_path)
        return file_name

    def get_data(self):
        return self.file_data

    def get_size(self):
        return os.path.getsize(self.file_path)

    def get_crc32(self):
        res = ''
        crc = binascii.crc32(self.file_data)
        for i in range(4):
            t = crc & 0xFF
            crc >>= 8
            res = '%02X%s' % (t, res)
        return res

    def get_md5(self):
        return hashlib.md5(self.file_data).hexdigest()

    def get_sha1(self):
        return hashlib.sha1(self.file_data).hexdigest()

    def get_sha256(self):
        return hashlib.sha256(self.file_data).hexdigest()

    def get_sha512(self):
        return hashlib.sha512(self.file_data).hexdigest()

    def get_ssdeep(self):
        if not HAVE_SSDEEP:
            return None

        try:
            return pydeep.hash_file(self.file_path)
        except Exception:
            return None

    def get_type(self):
        try:
            ms = magic.open(magic.MAGIC_NONE)
            ms.load()
            file_type = ms.buffer(self.file_data)
        except:
            try:
                file_type = magic.from_buffer(self.file_data)
            except:
                try:
                    import subprocess
                    file_process = subprocess.Popen(['file', '-b', self.file_path], stdout = subprocess.PIPE)
                    file_type = file_process.stdout.read().strip()
                except:
                    return None

        return file_type

class Config:
    def __init__(self, cfg="api.conf"):
        config = ConfigParser.ConfigParser()
        config.read(cfg)

        for section in config.sections():
            setattr(self, section, Dictionary())
            for name, raw_value in config.items(section):
                try:
                    value = config.getboolean(section, name)
                except ValueError:
                    try:
                        value = config.getint(section, name)
                    except ValueError:
                        value = config.get(section, name)

                setattr(getattr(self, section), name, value)

    def get(self, section):
        try:
            return getattr(self, section)
        except AttributeError as e:
            return None

########NEW FILE########
__FILENAME__ = utils
# Copyright (c) 2012, Claudio "nex" Guarnieri
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os
import json

from objects import File, Config

def jsonize(data):
    return json.dumps(data, sort_keys=False, indent=4)

def store_sample(data):
    sha256 = File(file_data=data).get_sha256()
    
    folder = os.path.join(Config().api.repository, sha256[0], sha256[1], sha256[2], sha256[3])
    if not os.path.exists(folder):
        os.makedirs(folder, 0750)

    file_path = os.path.join(folder, sha256)

    if not os.path.exists(file_path):
        sample = open(file_path, "wb")
        sample.write(data)
        sample.close()
    
    return file_path

def get_sample_path(sha256):
    path = os.path.join(Config().api.repository, sha256[0], sha256[1], sha256[2], sha256[3], sha256)
    if not os.path.exists(path):
        return None
    return path

########NEW FILE########
