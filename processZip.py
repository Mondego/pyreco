import zipfile

# get all filenames
zf = zipfile.ZipFile('github-projects/aio-libs-aiopg.zip', 'r');
# will get all file names in all directories recursively
filenames = zf.namelist()

for f in filenames:
	if f.endswith(‘.py’):

	# read a file
	zf.read(filename)

	# TODO: do whatever you need here