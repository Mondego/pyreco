import json, os, shelve, sys, shutil, urllib
data = json.load(open("projects_meta_data.json", "r"))
Count = 0
shelveobj = shelve.open("persistent.shelve")
for repo in data:
    clone_url = repo["clone_url"].encode("utf-8")
    if not shelveobj.has_key(clone_url):
        #os.system("git clone --depth 1 " + repo["clone_url"])
        zip_url = clone_url[:-4] # remove .git
        zip_url += '/archive/master.zip' # change to zip-downloading url
        zipfile = clone_url[19:-4].replace('/', '-') + '.zip'
        urllib.urlretrieve(zip_url, 'github-projects/'+zipfile)

        Count +=1
        print ("DONE WITH " + str(Count) + "/" + str(len(data)))
        shelveobj[clone_url] = True
        shelveobj.sync()
