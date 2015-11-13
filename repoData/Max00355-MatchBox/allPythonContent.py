__FILENAME__ = client
import urllib, time, os, getpass, thread, sys, hashlib

class MatchBoxClient:

    def __init__(self):
        self.url = raw_input("URL: ")
        self.username = raw_input("Username: ")
        self.password = getpass.getpass("Password: ")
        self.password = hashlib.sha1(self.password).hexdigest()
        self.files = {}
        self.verify_username_password()
        thread.start_new_thread(self.shell, ())
        self.main_loop()
    def main_loop(self):
        while True:
            try:
                time.sleep(1)
                this_dir = os.listdir(os.getcwd())
                that_dir = eval(urllib.urlopen(self.url+"/list/"+self.username+"/"+self.password).read())
                if str(this_dir) != str(that_dir):
                    for this in this_dir:
                        if this not in self.files and this != sys.argv[0]:
                            with open(this, 'rb') as md5file:
                                print "added", this
                                self.files[this] = hashlib.md5(md5file.read()).hexdigest()
                        if this not in that_dir and this != sys.argv[0]:
                            thread.start_new_thread(self.upload, (this,))
                    for that in that_dir:
                        if that not in this_dir:
                            thread.start_new_thread(self.download, (that,))
                    for file in self.files:
                        try:
                            with open(file, 'rb') as check_file:
                                check = hashlib.md5(check_file.read()).hexdigest()
                                if check != self.files[file]:
                                    print file, "changed"
                                    urllib.urlopen(self.url+"/delete/"+self.username+"/"+self.password+"/"+file)
                                    self.files[file] = check
                                    thread.start_new_thread(self.upload, (file,))
                        except IOError:
                            pass
            except IOError:
                print "It seems as though your server is down, please check it."
                time.sleep(60)
                        

    def upload(self, file):
        with open(file, 'rb') as upload:
            print "Uploading", file
            for letter in upload.readlines():
                line = []
                for x in letter:
                    line.append(str(ord(x)))
                urllib.urlopen(self.url+"/upload/"+self.username+"/"+self.password+"/"+file+"/"+' '.join(line))
        print "Done uploading", file

    def download(self, file):
        with open(file, 'wb') as download:
            print "Downloading", file
            download.write(urllib.urlopen(self.url+"/download/"+self.username+"/"+self.password+"/"+file).read())
        print "Done downloading", file

    def delete(self, file):
        os.remove(file)
        del self.files[file]
        urllib.urlopen(self.url+"/delete/"+self.username+"/"+self.password+"/"+file)

    def shell(self):
        while True:
            cmd = raw_input('> ')
            if cmd.startswith("rm"):
                cmd = cmd.split()
                if cmd[1] not in os.listdir(os.getcwd()):
                    print "File doesn't exist"
                elif cmd[1] == sys.argv[0]:
                    print "Don't delete MatchBox!"
                else:
                    thread.start_new_thread(self.delete, (cmd[1],))
            if cmd == "ls":
                print os.listdir(os.getcwd())
    def verify_username_password(self):
        if urllib.urlopen(self.url+"/list/"+self.username+"/"+self.password).read() == "Login Failed":
            print "Username or password not correct."
            exit()
        
if __name__ == "__main__":
    MatchBoxClient()

########NEW FILE########
__FILENAME__ = server
from flask import Flask
import os, hashlib

app = Flask(__name__)

users = {

'username':'password',

        }

@app.route("/delete/<username>/<password>/<file>")
def delete(username, password, file):
    if login(username, password) is False:
        return "Login Failed"
    else:
        os.remove("files/"+file)
        return "Success"

@app.route("/upload/<username>/<password>/<file>/<data>")
def upload(username, password, file, data):
    if login(username, password) is False:
        return "Login Failed"
    else:
        if file not in os.listdir("files"):
            with open("files/"+file, 'w') as file:
                pass
        upload = open("files/"+file, 'ab')
        data = data.split()
        for data in data:
            upload.write(chr(int(data)))
        upload.close()
        return "Success"

@app.route("/download/<username>/<password>/<file>")
def download(username, password, file):
    if login(username, password) is False:
        return "Login Failed"
    else:
        with open("files/"+file, 'rb') as file:
            return file.read()
        
@app.route("/list/<username>/<password>")
def list(username, password):
    if login(username, password) is False:
        return "Login Failed"
    else:
        return str(os.listdir("files"))

def login(username, password):
    if username not in users:
        return False
    elif hashlib.sha1(users[username]).hexdigest() == password:
        return True
    else:
        return False

if __name__ == "__main__":
    if "files" not in os.listdir(os.getcwd()):
        os.mkdir("files")
    app.run(host='0.0.0.0')

########NEW FILE########
