__FILENAME__ = checkout-jdk
#!/bin/sh
''''exec "$(dirname "$0")"/ImageJ.sh --jython "$0" "$@" # (call again with fiji)'''

import os
import sys

if len(sys.argv) < 2:
	print 'Need a path to the JDK'
	sys.exit(1)

jdk = sys.argv[1]

if not os.path.isdir(os.path.join(jdk, '.git')):
        print 'Initializing ', jdk
	if os.system('git submodule init ' + jdk) \
			or os.system('git submodule update ' + jdk):
		print 'Could not check out ', jdk
		sys.exit(1)
else:
	print 'Updating ', jdk
	if os.system('cd ' + jdk  \
			+ ' && git pull origin master'):
		print 'Could not update ', jdk
		sys.exit(1)

########NEW FILE########
__FILENAME__ = commit-plugin
#!/bin/sh
''''exec "$(dirname "$0")"/ImageJ.sh --jython "$0" "$@" # (call again with fiji)'''

import os
import sys

from compat import execute

# TODO: allow other cwds than fiji/
# TODO: use JGit

if len(sys.argv) < 2:
	print 'Usage:', sys.argv[0], 'src-plugins/<path>...'
	sys.exit(1)

list = list()
third_parties = dict()
for file in sys.argv[1:]:
	if file.startswith('staged-plugins/'):
		if file.endswith('.jar'):
			file = file[15:]
			list.append(file)
			third_parties[file] = file
		else:
			print 'Will not add non-jar staged plugin'
		continue
	if not file.startswith('src-plugins/'):
		print 'Will not add plugin outside src-plugins:', file
		continue
	if file.find('_') < 0:
		print 'This is not a plugin:', file
		continue
	if not os.path.isdir(file) and not file.endswith('.java'):
		print 'Will not add non-Java file:', file
		continue
	list.append(file[12:])

# read .gitignore

ignored = dict()
f = open('.gitignore', 'r')
line_number = 0
for line in f.readlines():
	ignored[line] = line_number
	line_number += 1
f.close()

# read Fakefile

f = open('Fakefile', 'r')
fakefile = f.readlines()
f.close()
faked_plugins = dict()
last_plugin_line = -1
last_jar_plugin_line = -1
last_3rd_party_plugin_line = -1
for i in range(0, len(fakefile)):
	if fakefile[i].startswith('PLUGIN_TARGETS='):
		while i < len(fakefile) and fakefile[i] != "\n":
			if fakefile[i].endswith(".class \\\n"):
				last_plugin_line = i
				faked_plugins[fakefile[i]] = i
			elif fakefile[i].endswith(".jar \\\n"):
				last_jar_plugin_line = i
				faked_plugins[fakefile[i]] = i
			i += 1
	elif fakefile[i].startswith('THIRD_PARTY_PLUGINS='):
		while i < len(fakefile) and fakefile[i] != "\n":
			if fakefile[i].endswith(".jar \\\n"):
				last_3rd_party_plugin_line = i
				faked_plugins[fakefile[i]] = i
			i += 1

# remove all .class files in the given directory

def remove_class_files(dir):
	for item in os.listdir(dir):
		path = dir + '/' + item
		if item.endswith('.class'):
			os.remove(path)
		elif os.path.isdir(path):
			remove_class_files(path)

# add the plugin to .gitignore, Fakefile, and the file itself

def add_plugin(plugin):
	if plugin.endswith('.java'):
		target = 'plugins/' + plugin[0:len(plugin) - 5] + '.class'
	elif plugin in third_parties:
		target = 'plugins/' + plugin
	else:
		if plugin.endswith('/'):
			plugin = plugin[0:len(plugin) - 1]
		remove_class_files('src-plugins/' + plugin)
		target = 'plugins/' + plugin + '.jar'

	ignore_line = '/' + target + "\n"
	if not ignore_line in ignored:
		f = open('.gitignore', 'a')
		f.write(ignore_line)
		f.close()
		ignored[target] = -1
		execute('git add .gitignore')

	plugin_line = "\t" + target + " \\\n"
	global last_plugin_line, last_jar_plugin_line, faked_plugins
	global last_3rd_party_plugin_line
	if not plugin_line in faked_plugins:
		if plugin.endswith('.java'):
			if last_jar_plugin_line > last_plugin_line:
				last_jar_plugin_line += 1
			if last_3rd_party_plugin_line > last_plugin_line:
				last_3rd_party_plugin_line += 1
			last_plugin_line += 1
			fakefile.insert(last_plugin_line, plugin_line)
		elif plugin in third_parties:
			if last_plugin_line > last_3rd_party_plugin_line:
				last_plugin_line += 1
			if last_jar_plugin_line > last_3rd_party_plugin_line:
				last_jar_plugin_line += 1
			last_3rd_party_plugin_line += 1
			fakefile.insert(last_3rd_party_plugin_line, plugin_line)
		else:
			if last_plugin_line > last_jar_plugin_line:
				last_plugin_line += 1
			if last_3rd_party_plugin_line > last_jar_plugin_line:
				last_3rd_party_plugin_line += 1
			last_jar_plugin_line += 1
			fakefile.insert(last_jar_plugin_line, plugin_line)

		f = open ('Fakefile', 'w')
		f.write(''.join(fakefile))
		f.close()
		execute('git add Fakefile')

	if plugin in third_parties:
		file = 'staged-plugins/' + plugin
		third_party = 'third-party '
	else:
		file = 'src-plugins/' + plugin
		third_party = ''
	if execute('git ls-files ' + file) == '':
		action = 'Add'
	else:
		action = 'Modify'
	execute('git add ' + file)
	f = open('.msg', 'w')
	if plugin.endswith('.java'):
		plugin = plugin[0:len(plugin) - 5]
	elif plugin.endswith('.jar'):
		plugin = plugin[0:len(plugin) - 4]
	configfile = 'staged-plugins/' + plugin + '.config'
	if os.path.exists(configfile):
		execute('git add ' + configfile)
	name = plugin.replace('/', '>').replace('_', ' ')
	f.write(action + ' the ' + third_party + 'plugin "' + name + '"')
	f.close() 
	execute('git commit -s -F .msg')
	os.remove('.msg')

for plugin in list:
	print 'Adding', plugin
	add_plugin(plugin)

########NEW FILE########
__FILENAME__ = compat
import os

# Jython does not support removedirs and symlink.
# Warning: this implementation is not space-safe!
if not 'JavaPOSIX' in dir(os):
	def removedirs(dir):
		os.removedirs(dir)
else:
	def removedirs(dir):
		os.system('rm -rf ' + dir)
if 'symlink' in dir(os):
	def symlink(src, dest):
		os.symlink(src, dest)
else:
	def symlink(src, dest):
		os.system("ln -s '" + src + "' '" + dest + "'")
if 'chmod' in dir(os):
	def chmod(path, mode):
		os.chmod(path, mode)
else:
	def chmod(path, mode):
		os.system('chmod ' + ('%o' % mode) + ' ' + path)

if os.name == 'java':
	from compat_jython import execute
else:
	def execute(cmd):
		proc = os.popen(cmd)
		return "\n".join(proc.readlines())

########NEW FILE########
__FILENAME__ = compat_jython
import os

# Jython does not support removedirs and symlink.
# Warning: this implementation is not space-safe!
if 'removedirs' in dir(os):
	def removedirs(dir):
		os.removedirs(dir)
else:
	def removedirs(dir):
		os.system('rm -rf ' + dir)
if 'symlink' in dir(os):
	def symlink(src, dest):
		os.symlink(src, dest)
else:
	def symlink(src, dest):
		os.system("ln -s '" + src + "' '" + dest + "'")
if 'chmod' in dir(os):
	def chmod(path, mode):
		os.chmod(path, mode)
else:
	def chmod(path, mode):
		os.system('chmod ' + ('%o' % mode) + ' ' + path)
try:
	from java.lang import Runtime
	from java.io import BufferedReader, InputStreamReader

	def execute(cmd):
		runtime = Runtime.getRuntime()
		p = runtime.exec(cmd)
		p.outputStream.close()
		result = ""
		reader = BufferedReader(InputStreamReader(p.inputStream))
		errorReader = BufferedReader(InputStreamReader(p.errorStream))
		while True:
			if p.errorStream.available() > 0:
				print errorReader.readLine()
			line=reader.readLine()
			if line == None:
				break
			result+=line + "\n"
		while True:
			line = errorReader.readLine()
			if line == None:
				break
			print line
		p.waitFor()
		if p.exitValue() != 0:
			print result
			raise RuntimeError, 'execution failure'
		return result
except:
	def execute(cmd):
		proc = os.popen(cmd)
		return "\n".join(proc.readlines())

########NEW FILE########
__FILENAME__ = generate-download-arrow
from ij import IJ
from ij.gui import ShapeRoi
from java.awt import Color, Polygon
from java.awt.geom import PathIterator

w = int(36)
h = int(42)
lineWidth = 2
arrowWidth = 16

image = IJ.createImage('Download arrow', 'rgb', w, h, 1)
ip = image.getProcessor()
ip.setLineWidth(lineWidth)
ip.setColor(Color(0x65a4e3))
roi = ShapeRoi([PathIterator.SEG_MOVETO, 0, 0,
	PathIterator.SEG_LINETO, w, 0,
	PathIterator.SEG_LINETO, w, w,
	PathIterator.SEG_LINETO, 0, w,
	PathIterator.SEG_CLOSE])
lw = lineWidth
roi = roi.not(ShapeRoi([PathIterator.SEG_MOVETO, lw, lw,
	PathIterator.SEG_LINETO, w - lw, lw,
	PathIterator.SEG_LINETO, w - lw, w - lw,
	PathIterator.SEG_LINETO, lw, w - lw,
	PathIterator.SEG_CLOSE]))
x1 = (w - arrowWidth) / 2
x2 = (w + arrowWidth) / 2
y1 = w * 2 / 3
roi = roi.or(ShapeRoi([PathIterator.SEG_MOVETO, x1, 0,
	PathIterator.SEG_LINETO, x1, y1,
	PathIterator.SEG_LINETO, 0, y1,
	PathIterator.SEG_LINETO, w / 2 - 1, h,
	PathIterator.SEG_LINETO, w / 2, h,
	PathIterator.SEG_LINETO, w - 1, y1,
	PathIterator.SEG_LINETO, x2, y1,
	PathIterator.SEG_LINETO, x2, 0,
	PathIterator.SEG_CLOSE]))
ip.fill(roi)
IJ.saveAs(image, "PNG", "resources/download-arrow.png")

########NEW FILE########
__FILENAME__ = generate-fiji-images
#!/bin/sh
''''exec "$(dirname "$0")"/ImageJ.sh --jython "$0" "$@" # (call again with fiji)'''

import sys

# .svg
from org.apache.batik.bridge \
	import BridgeContext, DocumentLoader, GVTBuilder, \
		UserAgent, UserAgentAdapter
from org.apache.batik.gvt.renderer import StaticRenderer
from org.w3c.dom import Document, Element

from java.awt import Rectangle
from java.awt.geom import AffineTransform
from java.awt.image import BufferedImage

# .ico
from net.sf.image4j.codec.ico import ICOEncoder

# .icns
from iconsupport.icns import IcnsCodec, IconSuite
from java.io import File, FileOutputStream

# .png
from javax.imageio import ImageIO

# .tif
from ij import ImagePlus
from ij.io import FileSaver

input = 'images/fiji-logo-1.0.svg'
ico = 'images/fiji.ico'
icns = 'Contents/Resources/Fiji.icns'

# load .svg

user_agent = UserAgentAdapter()
loader = DocumentLoader(user_agent)
context = BridgeContext(user_agent, loader)
user_agent.setBridgeContext(context)
document = loader.loadDocument(File(input).toURI().toString())
root = document.getRootElement()
svg_x = root.getX().getBaseVal().getValue()
svg_y = root.getY().getBaseVal().getValue()
svg_width = root.getWidth().getBaseVal().getValue()
svg_height = root.getHeight().getBaseVal().getValue()

def generate_image(width, height):
	renderer = StaticRenderer()
	renderer.setTree(GVTBuilder().build(context, document))
	transform = AffineTransform()
	transform.translate(-svg_x, -svg_y)
	transform.scale(width / svg_width, height / svg_height)
	renderer.setTransform(transform)
	renderer.updateOffScreen(width, height)
	renderer.repaint(Rectangle(0, 0, width, height))
	return renderer.getOffScreen()

# make .ico

def make_ico(ico):
	list = []
	for width in [ 256, 48, 32, 24, 16 ]:
		list.append(generate_image(width, width))
	ICOEncoder.write(list, File(ico))

# make .icns

def make_icns(icns):
	icons = IconSuite()
	icons.setSmallIcon(generate_image(16, 16))
	icons.setLargeIcon(generate_image(32, 32))
	icons.setHugeIcon(generate_image(48, 48))
	icons.setThumbnailIcon(generate_image(128, 128))
	codec = IcnsCodec()
	out = FileOutputStream(icns)
	codec.encode(icons, out)
	out.close()

def make_tiff(width, height, file):
	image = generate_image(width, height)
	FileSaver(ImagePlus("", image)).saveAsTiff(file)

def make_image(width, height, file, type):
	image = generate_image(width, height)
	ImageIO.write(image, type, File(file))

def extract_dimensions(filename):
	dot = filename.rfind('.')
	if dot < 0:
		dot = len(filename)
	x = filename.rfind('x', 0, dot)
	if x < 0:
		raise 'No dimensions found: ' + filename
	minus = filename.rfind('-', 0, x)
	if minus < 0:
		raise 'No dimensions found: ' + filename
	return [int(filename[minus + 1:x]), int(filename[x + 1:dot])]

if len(sys.argv) > 1:
	for file in sys.argv[1:]:
		if file.endswith('.ico'):
			make_ico(file)
		elif file.endswith('.icns'):
			make_icns(file)
		elif file.endswith('.png'):
			[width, height] = extract_dimensions(file)
			make_image(width, height, file, 'png')
		elif file.endswith('.jpg') or file.endswith('.jpeg'):
			[width, height] = extract_dimensions(file)
			make_image(width, height, file, 'jpg')
		elif file.endswith('.tiff') or file.endswith('.tif'):
			[width, height] = extract_dimensions(file)
			make_tiff(width, height, file)
		else:
			print 'Ignoring unknown file type:', file
else:
	make_ico('images/fiji.ico')
	make_icns('Contents/Resources/Fiji.icns')

########NEW FILE########
__FILENAME__ = generate-finder-background
from ij import IJ, ImagePlus
from ij.gui import Toolbar, Roi
from ij.process import Blitter
from java.awt import Color, Font, Polygon, Rectangle

w = 472
h = 354
xOffset = 59
yOffset = 120
radius = 20
arrowThickness = 14
fontName = 'Arial'
upperFontSize = 18
lowerFontSize = 10

image = IJ.createImage("MacOSX background picture", "rgb", w, h, 1)

# background
Toolbar.setForegroundColor(Color(0x5886ea))
Toolbar.setBackgroundColor(Color(0x3464c9))
IJ.run(image, "Radial Gradient", "")

# rounded rectangle
# correct for MacOSX bug: do the rounded rectangle in another image
image2 = image
image = IJ.createImage("MacOSX background picture", "rgb", w, h, 1)
image.setRoi(Roi(xOffset, yOffset, w - 2 * xOffset, h - 2 * yOffset))
IJ.run(image, "Make rectangular selection rounded", "radius=" + str(radius))
Toolbar.setForegroundColor(Color(0x435a96))
Toolbar.setBackgroundColor(Color(0x294482))
IJ.run(image, "Radial Gradient", "")
ip = image.getProcessor()
ip.setColor(0x0071bc)
ip.setLineWidth(2)
image.getRoi().drawPixels(ip)
Roi.setPasteMode(Blitter.COPY_TRANSPARENT)
#grow = image.getRoi().getClass().getSuperclass().getDeclaredMethod('growConstrained', [Integer.TYPE, Integer.TYPE])
#grow.setAccessible(True)
#grow.invoke(image.getRoi(), [1, 1])
image.copy(True)
image = image2
image.paste()
image.killRoi()
ip = image.getProcessor()

# arrow
ip.setColor(0x123558)
arrowLength = int(arrowThickness * 2.5)
arrowWidth = arrowThickness * 2
x1 = (w - arrowLength) / 2
x2 = x1 + arrowLength
x3 = x2 - arrowThickness
y1 = (h - arrowThickness) / 2
y2 = y1 + arrowThickness
y3 = (h - arrowWidth) / 2
y4 = y3 + arrowWidth
y5 = h / 2
polygon = Polygon(
	[x1, x1, x3, x3, x2, x3, x3],
	[y1, y2, y2, y4, y5, y3, y1], 7)
ip.fillPolygon(polygon)

# upper text
# work around an ImageJ bug: anti-aliased text is always black
ip.setAntialiasedText(True)
ip.invert()

ip.setJustification(ip.CENTER_JUSTIFY)
ip.setFont(Font(fontName, Font.BOLD, upperFontSize))
ip.drawString('Fiji is just ImageJ - batteries included',
	int(w / 2), int((yOffset + upperFontSize) / 2))
ip.setFont(Font(fontName, Font.BOLD, lowerFontSize))
ip.drawString('To install, drag Fiji to your Applications folder',
	int(w / 2), h - yOffset + lowerFontSize * 2)
ip.drawString('If you cannot write to the Applications folder,',
	int(w / 2), h - yOffset + lowerFontSize * 4)
ip.drawString('drag Fiji to another folder, e.g. onto your Desktop',
	int(w / 2), h - yOffset + lowerFontSize * 5)
ip.invert()

IJ.saveAs(image, "jpeg", "resources/install-fiji.jpg")

########NEW FILE########
__FILENAME__ = iconv
#!/bin/sh
''''exec "$(dirname "$0")"/ImageJ.sh --jython "$0" "$@" # (call again with fiji)'''

from java.io import File, FileInputStream, FileOutputStream
from java.nio import ByteBuffer
from java.nio.charset import Charset
import sys

if sys.argv[1] == '-f':
	decoder = Charset.forName(sys.argv[2]).newDecoder()
	sys.argv[1:] = sys.argv[3:]
elif sys.argv[1] == '-l':
	for name in Charset.availableCharsets().keySet():
		print name
	sys.exit(0)
else:
	decoder = Charset.forName("ISO-8859-1").newDecoder()
encoder = Charset.forName("UTF-8").newEncoder()

def iconv(file):
	print 'Converting', file
	f = File(file)
	if not f.exists():
		print file, 'does not exist'
		sys.exit(1)
	buffer = ByteBuffer.allocate(f.length() * 2)
	input = FileInputStream(f)
	input.getChannel().read(buffer)
	buffer.limit(buffer.position())
	buffer.position(0)
	if buffer.limit() != f.length():
		print file, 'could not be read completely'
		sys.exit(1)
	input.close()
	buffer = encoder.encode(decoder.decode(buffer))
	buffer.position(0)
	output = FileOutputStream(file + '.cnv')
	if output.getChannel().write(buffer) != buffer.limit():
		print file, 'could not be reencoded'
		sys.exit(1)
	output.close()
	f.delete()
	File(file + '.cnv').renameTo(f)

for file in sys.argv[1:]:
	iconv(file)

########NEW FILE########
__FILENAME__ = make-7z
#!/bin/sh
''''exec "$(dirname "$0")"/ImageJ.sh --jython "$0" "$@" # (call again with fiji)'''

import sys
from compat import execute

if len(sys.argv) < 3:
	print 'Usage: ', sys.argv[0], ' <archive> <folder>'
	exit(1)

archive = sys.argv[1]
folder = sys.argv[2]

print 'Making', archive, 'from', folder

if not archive.endswith('.7z'):
	archive = archive + '.7z'

execute('7z a -m0=lzma -mx=9 -md=64M ' + archive + ' ' + folder)
execute('chmod a+r ' + archive)

########NEW FILE########
__FILENAME__ = make-app
#!/bin/sh
''''exec "$(dirname "$0")"/ImageJ.sh --jython "$0" "$@" # (call again with fiji)'''

import os
import shutil
import sys
from compat import chmod, execute
from java.io import File

if len(sys.argv) < 3:
	print 'Usage: ' + sys.argv[0] + ' <platform> <host-platform>'
	exit(1)

platform = sys.argv[1].replace('app-', '')
host_platform = sys.argv[2]

all_platforms = ['linux32', 'linux64', 'win32', 'win64', 'macosx']

if platform == 'nojre':
	copy_jre = False
	platform = 'all'
else:
	copy_jre = True


def removedirs(dir):
	if not isinstance(dir, File):
		dir = File(dir)
	list = dir.listFiles()
	if list is None:
		return
	for file in list:
		if file.isDirectory():
			removedirs(file)
		elif file.isFile():
			file.delete();
	dir.delete()

def make_app():
	print 'Making app'
	if os.path.isdir('Fiji.app'):
		removedirs('Fiji.app')
	os.makedirs('Fiji.app/images')
	shutil.copy('images/icon.png', 'Fiji.app/images/')
	for d in ['plugins', 'macros', 'jars', 'retro', 'luts', \
			'scripts']:
		shutil.copytree(d, 'Fiji.app/' + d)
	if os.path.isdir('samples'):
		shutil.copytree('samples', 'Fiji.app/samples')
	if os.path.isdir('Fiji.app/jars/jython2.2.1/cachedir'):
		removedirs('Fiji.app/jars/jython2.2.1/cachedir')
	if os.path.isdir('Fiji.app/jars/cachedir'):
		removedirs('Fiji.app/jars/cachedir')

def get_java_platform(platform):
	if platform == 'linux64':
		platform = 'linux-amd64'
	elif platform == 'macosx':
		platform = 'macosx-java3d'
	return platform

def find_java_tree(platform):
	java = 'java/' + platform
	revision = execute('git rev-parse HEAD:' + java)
	if platform == 'macosx-java3d':
		return [revision.replace('\n', ''), platform]
	tree = execute('git --git-dir=' + java + '/.git ls-tree ' + revision)
	return [tree[12:52] + ':jre',
		platform + '/' + tree[53:].replace('\n', '') + '/jre']

def copy_java(platform):
	if platform == 'linux32':
		platform = 'linux'
	java_platform = get_java_platform(platform)
	java_tree = find_java_tree(java_platform)
	os.system('git --git-dir=java/' + java_platform + '/.git ' \
		+ 'archive --prefix=Fiji.app/java/' + java_tree[1] + '/ ' \
			+ java_tree[0] + ' | ' \
			+ 'tar xf -')

def copy_platform_specific_files(platform):
	if copy_jre:
		print 'Copying Java files for', platform
		copy_java(platform)

	print 'Copying platform-specific files for', platform, \
		'(host platform=' + host_platform + ')'
	if platform == 'macosx':
		macos='Fiji.app/Contents/MacOS/'
		os.makedirs(macos)
		shutil.copy('Contents/MacOS/ImageJ-macosx', macos + 'ImageJ-macosx')
		shutil.copy('Contents/MacOS/ImageJ-tiger', macos)
		chmod(macos + 'ImageJ-macosx', 0755)
		chmod(macos + 'ImageJ-tiger', 0755)
		shutil.copy('Contents/Info.plist', 'Fiji.app/Contents/')
		images='Fiji.app/Contents/Resources/'
		os.makedirs(images)
		shutil.copy('Contents/Resources/Fiji.icns', images)
	else:
		if platform.startswith('win'):
			exe = ".exe"
		else:
			exe = ''

		binary = 'ImageJ-' + platform + exe
		shutil.copy(binary, 'Fiji.app/' + binary)
		chmod('Fiji.app/' + binary, 0755)

make_app()
execute('bin/download-launchers.sh snapshot')
if platform == 'all':
	for p in all_platforms:
		copy_platform_specific_files(p)
else:
	copy_platform_specific_files(platform)

########NEW FILE########
__FILENAME__ = make-dmg
#!/bin/sh
''''exec "$(dirname "$0")"/ImageJ.sh --jython "$0" "$@" # (call again with fiji)'''

import os
import re

from compat import symlink, execute

dmg='fiji-macosx.dmg'
app='Fiji.app'

def hdiutil(cmd):
	print cmd
	os.system('hdiutil ' + cmd)
def get_disk_id(dmg):
	match=re.match('.*/dev/([^ ]*)[^/]*Apple_HFS.*', execute('hdid ' + dmg),
		re.MULTILINE | re.DOTALL)
	if match != None:
		return match.group(1)
	return None
def get_folder(dmg):
	match=re.match('.*Apple_HFS\s*([^\n]*).*', execute('hdid ' + dmg),
		re.MULTILINE | re.DOTALL)
	if match != None:
		return match.group(1)
	return None
def eject(dmg):
	disk_id=get_disk_id(dmg)
	print "disk_id: ", disk_id
	hdiutil('eject ' + disk_id)

# create temporary disk image and format, ejecting when done
hdiutil('create ' + dmg + ' -srcfolder ' + app \
	+ ' -fs HFS+ -format UDRW -volname Fiji -ov')
folder=get_folder(dmg)
print "folder: ", folder
os.system('cp resources/install-fiji.jpg "' + folder + '"/.background.jpg')
symlink('/Applications', folder + '/Applications')
execute('perl bin/generate-finder-dsstore.perl')
# to edit the background image/icon positions: raw_input('Press Enter...')
eject(dmg)

os.rename(dmg, dmg + '.tmp')
hdiutil('convert ' + dmg + '.tmp -format UDZO -o ' + dmg)
eject(dmg)
os.remove(dmg + '.tmp')

########NEW FILE########
__FILENAME__ = make-tar
#!/bin/sh
''''exec "$(dirname "$0")"/ImageJ.sh --jython "$0" "$@" # (call again with fiji)'''

import sys
from compat import execute

if len(sys.argv) < 3:
	print 'Usage: ', sys.argv[0], ' <tarfile> <folder>'
	exit(1)

tarfile = sys.argv[1]
folder = sys.argv[2]

print 'Making', tarfile, 'from', folder

if tarfile.endswith('.bz2'):
	packer = 'bzip2 -9 -f'
	tarfile = tarfile[:len(tarfile) - 4]
elif tarfile.endswith('.gz'):
	packer = 'gzip -9 -f'
	tarfile = tarfile[:len(tarfile) - 3]
else:
	packer = ''

execute('tar cvf ' + tarfile + ' ' + folder)

if packer != '':
	execute(packer + ' ' + tarfile)

########NEW FILE########
__FILENAME__ = make-zip
#!/bin/sh
''''exec "$(dirname "$0")"/ImageJ.sh --jython "$0" "$@" # (call again with fiji)'''

import os
import sys
from compat import execute

if len(sys.argv) < 3:
	print 'Usage: ', sys.argv[0], ' <zipfile> <folder>'
	exit(1)

zipfile = sys.argv[1]
folder = sys.argv[2]

verbose = False

print 'Making', zipfile, 'from', folder

if os.name == 'java':
	from java.io import FileOutputStream
	from java.util.zip import ZipOutputStream, ZipEntry

	def add_folder(zip, folder):
		for file in os.listdir(folder):
			file = folder + '/' + file
			if os.path.isdir(file):
				add_folder(zip, file)
			elif os.path.isfile(file):
				if verbose:
					print file
				entry = ZipEntry(file)
				zip.putNextEntry(entry)
				f = open(file, "rb")
				zip.write(f.read())
				f.close()
				zip.closeEntry()

	output = FileOutputStream(zipfile)
	zip = ZipOutputStream(output)
	add_folder(zip, folder)
	zip.close()
else:
	execute('zip -9r ' + zipfile + ' ' + folder)

########NEW FILE########
__FILENAME__ = pdf-concat
#!/bin/sh
''''exec "$(dirname "$0")"/ImageJ.sh --jython "$0" "$@" # (call again with fiji)'''

from com.itextpdf.text import Document
from com.itextpdf.text.pdf import PdfReader, PdfCopy, SimpleBookmark
from java.io import FileOutputStream
from java.util import ArrayList
import sys

# This Python file is a straight translation of the Concatenate example

if len(sys.argv) < 3:
	print 'Usage:', sys.argv[0], 'source(s).pdf...', 'target.pdf'
	sys.exit(1)

copy = None
all_bookmarks = ArrayList()
page_offset = 0

for file in sys.argv[1:len(sys.argv) - 1]:
	reader = PdfReader(file)
	reader.consolidateNamedDestinations()
	bookmarks = SimpleBookmark.getBookmark(reader)
	if bookmarks != None:
		if page_offset != 0:
			SimpleBookmark.shiftPageNumbers(bookmarks, \
				page_offset, None)
		all_bookmarks.add(bookmarks)

	page_count = reader.getNumberOfPages()
	page_offset += page_offset

	if copy == None:
		document = Document(reader.getPageSizeWithRotation(1))
		output = FileOutputStream(sys.argv[len(sys.argv) - 1])
		copy = PdfCopy(document, output)
		document.open()

	print "Adding", page_count, "pages from", file

	for k in range(0, page_count):
		copy.addPage(copy.getImportedPage(reader, k + 1))

	if reader.getAcroForm() != None:
		copy.copyAcroForm(reader)

if not all_bookmarks.isEmpty():
	copy.setOutlines(all_bookmarks)

if document != None:
	document.close()

########NEW FILE########
__FILENAME__ = pdf-extract-images
#!/bin/sh
''''exec "$(dirname "$0")"/ImageJ.sh --jython "$0" "$@" # (call again with fiji)'''

from org.jpedal import PdfDecoder
from ij import ImageJ, ImagePlus
import sys

if len(sys.argv) != 2:
	print 'Usage:', sys.argv[0], 'source.pdf'
	sys.exit(1)

ij = None

decoder = PdfDecoder(False)
decoder.setExtractionMode(PdfDecoder.RAWIMAGES | PdfDecoder.FINALIMAGES)
decoder.openPdfFile(sys.argv[1])

for page in range(0, decoder.getPageCount()):
	decoder.decodePage(page + 1)
	images = decoder.getPdfImageData()
	image_count = images.getImageCount()
	for i in range(0, image_count):
		name = images.getImageName(i)
		image = decoder.getObjectStore().loadStoredImage('R' + name)
		if ij == None:
			ij = ImageJ()
			ij.exitWhenQuitting(True)
		ImagePlus(name, image).show()
	decoder.flushObjectValues(True)
decoder.closePdfFile()

########NEW FILE########
__FILENAME__ = pdf-rotate
#!/bin/sh
''''exec "$(dirname "$0")"/ImageJ.sh --jython "$0" "$@" # (call again with fiji)'''

from com.itextpdf.text.pdf import PdfReader, PdfName, PdfNumber, PdfStamper
from java.io import FileOutputStream
import sys

if len(sys.argv) != 3:
	print 'Usage:', sys.argv[0], 'source.pdf', 'target.pdf'
	sys.exit(1)

reader = PdfReader(sys.argv[1])
for k in range(0, reader.getNumberOfPages()):
	reader.getPageN(k + 1).put(PdfName.ROTATE, PdfNumber(90))
	print "rotated", k

stamper = PdfStamper(reader, FileOutputStream(sys.argv[2]))
stamper.close()

########NEW FILE########
__FILENAME__ = plugin-documentation-list
#!/bin/sh
''''exec "$(dirname "$0")"/ImageJ.sh --jython "$0" "$@" # (call again with fiji)'''

from xml.dom.minidom import parseString
import re
from elementtidy import TidyHTMLTreeBuilder
import urllib
import elementtree.ElementTree as ET
import urlparse
import posixpath


# -------------------------------
#       PUBLIC ATTRIBUTES
# -------------------------------

# regular expression to find a maintainer
MAINTAINER_TAG = 'Maintainer'
# URL to the wiki
WIKI_URL = 'http://fiji.sc'
# URL to the plugin list
PLUGIN_LIST_URL = WIKI_URL + '/wiki/index.php/Template:PluginList';


# -------------------------------
#       PRIVATE ATTRIBUTES
# -------------------------------

# Xhtml tag
__XHTML = "{http://www.w3.org/1999/xhtml}"
# Rex rule to find header tags in html
__HEADER_REGEXP = re.compile('h(?P<hlevel>\d)')

# -------------------------------
#       PUBLIC FUNCTIONS
# -------------------------------


def findMaintainer(tree):    
    for table in tree.findall(".//"+__XHTML+"table"):
        table_class = table.get("class")
        if table_class != "infobox": continue
        for tr in table.getiterator():
            for child in tr:
                text = child.text
                if text is None: continue
                if MAINTAINER_TAG.lower() in text.lower():
                    # the parent (tel) of this child has a "maintainer" text in it
                    plugin_name = tree.find(".//"+__XHTML+"h1").text
                    td = tr.find(__XHTML+'td')
                    if (td.text is None) or (td.text.strip() is None):
                        # Check if we have a maintainer in the shape of a link or somthing else
                        if len(td) == 0:
                            # It has no children, so it is empty
                            return None
                        else:
                            # Find the first subelement which text is not empty
                            for sub_td in td:
                                if not ( (sub_td.text is None) or (sub_td.text.strip() is None) ):
                                    return sub_td.text.strip()
                            return 'Could not parse mainainer name.'
                    else:
                        # We have a maintainer entered as plain text in the td tag
                        return td.text.strip()
                
def prettyPrint(element):
    txt = ET.tostring(element)
    print parseString(txt).toprettyxml()


def getPluginListHTMLpage():
    """Returns the raw html of the wiki age that collect plugin hierarchy."""
    plugin_list_page_tree = TidyHTMLTreeBuilder.parse(urllib.urlopen(PLUGIN_LIST_URL))
    return plugin_list_page_tree
    

def getPluginListTree():
    """Returns the ElementTree of the plugin hierarchy, as it is on the plugin
    list wiki page."""
    
    plugin_list_page_tree = getPluginListHTMLpage();
    # Get the body-content div
    body = plugin_list_page_tree.find( __XHTML+'body')
    body_content = body.find(__XHTML+"div[@id='globalWrapper']/"+
                             __XHTML+"div[@id='column-content']/"+
                             __XHTML+"div[@id='content']/"+
                             __XHTML+"div[@id='bodyContent']/")
    # Get rid of the toc
    body_elements = body_content[6:] 
    # Build the tree recursively
    root = ET.Element('plugin_hierarchy')
    root.append( __createChildElement("toplevel", 1, body_elements) )
    return root
    
def getPackageTree():
    """Returns the ElementTree of the packages that can be found in the plugin
    hierarchy, as it is on the plugin list wiki page."""
    plugin_list_page_tree = getPluginListHTMLpage();
    # Get the body-content div
    body = plugin_list_page_tree.find( __XHTML+'body')
    body_content = body.find(__XHTML+"div[@id='globalWrapper']/"+
                             __XHTML+"div[@id='column-content']/"+
                             __XHTML+"div[@id='content']/"+
                             __XHTML+"div[@id='bodyContent']/")
    # Get rid of the toc
    body_elements = body_content[6:] 
    # Build the tree 
    root = ET.Element('package_list')
    for element in body_content.getiterator():
        
        # Plugins are in HTML unordered list
        if not __XHTML+'ul' in element.tag:
            continue
        
        for li_child in element:
            
            # Each plugin is listed in a html list item
            if not __XHTML+'li' in li_child.tag: continue
            
            # For this, we depend strongly on html markups chosen by the
            # script that has generated this page
            a_el = li_child.find(__XHTML+'a')
            if a_el is None: continue
            plugin_package = li_child.find(__XHTML+'b')
            if plugin_package is not None:
                plugin_package = plugin_package.find(__XHTML+'a')
                if plugin_package is not None:
                    package_attrib = __parseAElement(plugin_package)
                    # Check if we did not already parsed this one
                    if root.find("package[@name='" + package_attrib['name'] + "']") is None:
                        new_element = ET.SubElement(root, 'package')
                        new_element.attrib = package_attrib
    
    return root


def createBlamePage():
    
    # Build blame list
    plugin_without_documentation_page = []
    plugin_without_maintainer = []
    package_without_documentation_page = []
    package_without_maintainer = []

    plugintree = getPluginListTree()
    plugin_els = plugintree.findall('.//plugin')
    for el in plugin_els:
        plugin_str =  '* [[' + el.attrib['name'] + ']]'
        if el.attrib['has_page'] == 'no':
            plugin_without_documentation_page.append(plugin_str)
        else:
            html = getPluginHTMLpage(el)
            mtnr = findMaintainer(html)            
            if mtnr is None:
                plugin_without_maintainer.append(plugin_str)

                
    packagetree = getPackageTree()
    package_els = packagetree.findall('.//package')
    for el in package_els:
        package_str =  '* [[' + el.attrib['name'] + ']]'
        if el.attrib['has_page'] == 'no':
            package_without_documentation_page.append(package_str)
        else:
            html = getPluginHTMLpage(el)
            mtnr = findMaintainer(html)
            if mtnr is None:
                package_without_maintainer.append(package_str)
    
    # Output blame list
    headers = [
        "== Plugins without documentation page ==",
        "== Plugins without maintainer ==",
        "== Packages without a documentation page ==",
        "== Packages without maintainer =="    ]
    lists = [
        plugin_without_documentation_page ,
        plugin_without_maintainer ,
        package_without_documentation_page, 
        package_without_maintainer     ]
    spacer = 2*'\n'
    
    for i in range(len(headers)):
        print spacer
        print headers[i]
        print spacer
        for line in lists[i]:
            print line
    
def createMaintainerPage():
    """Get the maintainer for each plugin and package, and generate a list of
    maintained item per maintainer."""
    
    # Build maintainer dicts
    plugin_maintainer_dict = {}
    package_maintainer_dict = {}
    
    plugintree = getPluginListTree()
    plugin_els = plugintree.findall('.//plugin')
    for el in plugin_els:
        plugin_str =  '* [[' + el.attrib['name'] + ']]'
        if el.attrib['has_page'] == 'no':
            continue
        else:
            html = getPluginHTMLpage(el)
            mtnr = findMaintainer(html)            
            if mtnr is not None:
                mtnr = __cleanString(mtnr)
                if plugin_maintainer_dict.has_key(mtnr):
                    plugin_maintainer_dict[mtnr].append(plugin_str)
                else:
                    plugin_maintainer_dict[mtnr] = [ plugin_str ]
                    
                
    packagetree = getPackageTree()
    package_els = packagetree.findall('.//package')
    for el in package_els:
        package_str =  '* [[' + el.attrib['name'] + ']]'
        if el.attrib['has_page'] == 'no':
            continue
        else:
            html = getPluginHTMLpage(el)
            mtnr = findMaintainer(html)
            if mtnr is not None:
                mtnr = __cleanString(mtnr)
                if package_maintainer_dict.has_key(mtnr):
                    package_maintainer_dict[mtnr].append(package_str)
                else:
                    package_maintainer_dict[mtnr] = [ package_str ]

    # Output maintainer dict
    maintainers = plugin_maintainer_dict.keys() + package_maintainer_dict.keys()
    maintainers = __unique(maintainers)
    
    wiki_page = '';
    wiki_page = wiki_page  + '{{ #switch:{{{maintainer|}}}' + 2*'\n'
    
    for maintainer in maintainers:
        wiki_page = wiki_page  + '| ' + maintainer + ' = \n'
        
        wiki_page = wiki_page  + '\n=== Plugins ===' + 2*'\n'
        plugins = plugin_maintainer_dict.get(maintainer,[])
        for plugin in plugins:
            wiki_page = wiki_page + plugin + '\n'

        wiki_page = wiki_page  + '\n=== Packages ===' + 2*'\n'
        packages = package_maintainer_dict.get(maintainer,[])
        for package in packages:
            wiki_page = wiki_page + package + '\n'
            
        wiki_page = wiki_page  + 2*'\n'
        
    wiki_page = wiki_page + '}}' + 2*'\n'
    wiki_page = wiki_page + '<noinclude>' + 2*'\n' \
                + '__NOTOC__' + 2*'\n' \
                + 'This template automatically generate a paragraph containing ' \
                + 'the list of plugins and packages maintained by a maintainer, as ' \
                + 'stated in the wiki. It is automatically generated from a python ' \
                + 'script in the Fiji development repository, that can be seen ' \
                + '[http:////fiji.sc/cgi-bin/gitweb.cgi?p=fiji.git;a=blob;f=scripts/plugin-documentation-list.py;hb=HEAD here]' \
                + '.\n\nSyntax is the ' \
                + 'following:' + 2*'\n' \
                + '<pre>\n' \
                + '== Plugins and Packages maintained by Mark Longair ==\n' \
                + '{{ Maintainers | maintainer = Mark Longair }} \n' \
                + '</pre>\n' \
                + '\n' \
                + '== Plugins and Packages maintained by Mark Longair ==\n' \
                + '{{ Maintainers | maintainer = Mark Longair }}\n' \
                + '<' + '\\' + 'noinclude>'
    
    print wiki_page
    

def getPluginHTMLpage(element):
    """Returns the raw html from the wiki page of the plugin referenced by
    this element."""
    rel_link = element.attrib['link']
    url = __join(WIKI_URL,rel_link)
    plugin_page = TidyHTMLTreeBuilder.parse(urllib.urlopen(url))
    return plugin_page

# -------------------------------
#       PRIVATE FUNCTIONS
# -------------------------------

def __unique(li):
    """Return a list made of the unique item of the given list.
    Not order preserving"""
    keys = {}
    for e in li:
        keys[e] = 1
    return keys.keys()

def __cleanString(input_str):
    """Used to remove parenthesis and their content from maintainer strinfgs."""
    new_str = re.sub('\(.*?\)', '', input_str)
    new_str = new_str.replace('(','')
    new_str = new_str.replace(')','')
    return new_str.strip()

def __join(base,url):
    join = urlparse.urljoin(base,url)
    url = urlparse.urlparse(join)
    path = posixpath.normpath(url[2])
    return urlparse.urlunparse(
        (url.scheme,url.netloc,path,url.params,url.query,url.fragment)
        )


def __parseAElement(alement):
    """Parse a Element made from a html link in the shape of
    <a href="link" class="new" title="TransformJ">TransformJ_</a> """    
    attrib = {}
    attrib['name'] = alement.attrib.get('title')
    attrib['link'] = alement.attrib['href']
    if alement.attrib.get('class') == 'new':
        attrib['has_page'] = 'no'
    else:
        attrib['has_page'] = 'yes'
    return attrib
    


def __createChildElement(current_name, current_hlevel, body_elements):
    
    # Create element for this section    
    current_element = ET.Element("h"+str(current_hlevel))
    current_element.attrib['name']=current_name
    
    # Go trough each element of this list

    while len(body_elements) > 0:
        
        # Pop the first element out
        element = body_elements.pop(0)
        
        m = __HEADER_REGEXP.search(element.tag)
        if m is not None:
            
            # Case 1: is a header 
            hlevel = int(m.group('hlevel'))        
            if hlevel > current_hlevel:
                # The found header has a hierrachy level strictly deeper than
                # the one we are currently parsing (e.g h3 > h2). As a
                # consequence, a new element should be made out of the found
                # header content. This element is going to be child of the
                # current element
                new_name = element[1].text
                #new_body_elements = body_elements [ index + 1 : ]
                new_element = __createChildElement(new_name, hlevel, body_elements)
                current_element.append(new_element)
                
            else:
                # The found header has a hierachy level equal or superior than the
                # one we are currently parsing (e.g h2 <= h2). As a consequence,
                # we are done parsing this one and the current element should
                # be returned.
                # But before, we have to put back this poped-out element for
                # the parent process
                body_elements.insert(0,element)
                return current_element


        # Case 2: look for plugin items
        # Plugins are in HTML unordered list
        if not __XHTML+'ul' in element.tag:
            continue
        
        for li_child in element:
            
            # Each plugin is listed in a html list item
            if not __XHTML+'li' in li_child.tag: continue
                        
            # For this, we depend strongly on html markups chosen by the
            # script that has generated this page
            plugin_attrib = {}
            a_el = li_child.find(__XHTML+'a')
            if a_el is None: continue
            plugin_attrib = __parseAElement(a_el)
            plugin_attrib['type'] = li_child.find(__XHTML+'i').text
            plugin_attrib['file'] = li_child.find(__XHTML+'tt').text
            plugin_package = li_child.find(__XHTML+'b')
            if plugin_package is not None:
                plugin_package = plugin_package.find(__XHTML+'a')
                if plugin_package is not None:
                    plugin_package = __parseAElement(plugin_package)
                    plugin_attrib['package'] = plugin_package['name']
                    
            # Attach attributes to current element
            plugin_element = ET.SubElement(current_element, 'plugin')
            plugin_element.attrib = plugin_attrib
    
    # Done parsing all elements
    return current_element


# -------------------------------
#       MAIN
# -------------------------------

#createBlamePage()

createMaintainerPage()


########NEW FILE########
__FILENAME__ = plugin-list-parser
#!/bin/sh
''''exec "$(dirname "$0")"/ImageJ.sh --headless --jython "$0" "$@" # (call again with fiji)'''

from fiji import User_Plugins
from ij import IJ
from java.io import File
from java.util import LinkedHashMap
import os, stat, types
import zipfile
import sys


"""
This script parses the plugins folder content, and tries to build a list
of Fiji plugins from it, formatted to be pasted in MediaWiki. Optionally,
it can upload the changes right away. Or compare to the current version on
the Wiki.

It fetches information on menu item position and files called by
letting fiji.User_Plugins parse the jars.

J.Y. Tinevez - 2009, J. Schindelin - 2010,2012
"""

def walktree(top = ".", depthfirst = True):
    """Walk the directory tree, starting from top. Credit to Noah Spurrier and Doug Fort."""
    import os, stat, types
    names = os.listdir(top)
    names.sort()
    if not depthfirst:
        yield top, names
    for name in names:
        try:
            st = os.lstat(os.path.join(top, name))
        except os.error:
            continue
        if stat.S_ISDIR(st.st_mode):
            for (newtop, children) in walktree (os.path.join(top, name), depthfirst):
                yield newtop, children
    if depthfirst:
        yield top, names

def splitLast(string, separator, emptyLeft = None):
    """ Splits the string into two parts at the last location of the separator."""
    offset = string.rfind(separator)
    if offset < 0:
        return [emptyLeft, string]
    return string[:offset], string[offset + 1:]

def getTree(menuPath):
    """Get the tree (a list) for a given menuPath (e.g. File>New)"""
    global allElements, root
    if menuPath.endswith('>'):
        menuPath = menuPath[:-1]
    if menuPath in allElements:
        result = allElements[menuPath]
    else:
        result = []
        parentMenuPath, dummy = splitLast(menuPath, '>', '')
        parentTree = getTree(parentMenuPath)
        parentTree.append([menuPath, result])
        allElements.put(menuPath, result)
    return result

def appendPlugin(menuPath, name, class_name, package_name, type, path = None):
    tree = getTree(menuPath)
    if path != None and path.startswith(PLUGINS_FOLDER):
        path = path[len(PLUGINS_FOLDER):]
    tree.append({'name': name, 'path': path, 'class': class_name, 'package': package_name, 'type': type})

def appendJar(jarfile_path, type):
    """Analyze the content of a plugins.config embeded in a jar, and get the
    location of its indexed compenents."""
    for line in User_Plugins(False).getJarPluginList(File(jarfile_path), 'Plugins'):
        if line[1] == '-':
            continue
        packageName, className = splitLast(line[2], '.')
        appendPlugin(line[0], line[1], className, packageName, type, jarfile_path)

def createPluginsTree(ij_folder):
    plugins_location = os.path.join(ij_folder, PLUGINS_FOLDER)

    for top, names in walktree(plugins_location):
        for name in names:
            # Get filename and type
            split_filename = os.path.splitext(name)
            file_extension = split_filename[1]
            file_name = split_filename[0]
            type = PLUGINS_TYPE.get(file_extension)

            if type == None or file_name.find('$') >= 0: # Folders or gremlins
                continue
            elif type == PLUGINS_TYPE.get(JAR_EXTENSION):
                appendJar(os.path.join(plugins_location, name), type)
            elif file_name.find('_') >= 0: # Plain plugin
                menuPath = top[top.find(PLUGINS_FOLDER) + len(PLUGINS_FOLDER) + 1:].replace('/', '>')
                if menuPath == '':
                    menuPath = 'Plugins'
                elif menuPath.startswith('Scripts>'):
                    menuPath = menuPath[8:]
                else:
                    menuPath = 'Plugins>' + menuPath
                menuItemLabel = name[:-len(file_extension)].replace('_', ' ')
                appendPlugin(menuPath, menuItemLabel, name, None, type, name)

def treeToString(tree, level=1):
    global firstNode
    result = ''

    tree.sort()

    # first handle the commands
    for element in tree:
        if type(element) is dict:
            # if it is a dict, it describes one menu entry
            if element['class'] == None:
                element['class'] = '#'
            if element['package'] != None:
                element['class'] = element['package'] +"." + element['class']
                element['package'] = None
            plugin_line = '* ' + '[[' + element['name'] + ']]' + ' - file ' + "<tt>" + element['class'] + "</tt>"
            plugin_line += "  -- ''" + element['type'] + "''"
            result += plugin_line + '\n'

    # then handle the submenus
    for element in tree:
        if type(element) is list:
            # submenu: a list of the form [title, tree]
            # Echo section title
            if firstNode:
                firstNode = False
            else:
                result += (4-level)*'\n'
            title_tag = (1+level)*'='
            title_string = title_tag + ' ' + element[0].replace('>', ' > ') + ' ' + title_tag + '\n'
            result += title_string + '\n' + treeToString(element[1], level + 1)
    return result

def pluginsTreeToString():
    global firstNode
    firstNode = True
    return treeToString(allElements.get(''))



# -------------------------------
#       MAIN
# -------------------------------

# Define dictionaries
JAR_EXTENSION = '.jar'
PLUGINS_TYPE = {JAR_EXTENSION:'java jar file',
                '.class':'java class file',
                '.txt':'macro',
                '.ijm':'macro',
                '.bsh':'beanshell script',
                '.js':'javascript script',
                '.rb':'jruby script',
                '.py':'jython script',
                '.clj':'clojure script'}
# Folder names
PLUGINS_FOLDER = 'plugins'
PLUGINS_MENU_NAME = 'Plugins'

URL = 'http://fiji.sc/wiki/index.php'
PAGE = 'Template:PluginList'

allElements = LinkedHashMap()
allElements[''] = []

uploadToWiki = False
compareToWiki = False
color = '--color=none'
if len(sys.argv) > 1 and sys.argv[1] == '--upload-to-wiki':
    uploadToWiki = True
    sys.argv = sys.argv[:1] + sys.argv[2:]
elif len(sys.argv) > 1 and sys.argv[1] == '--compare-to-wiki':
    compareToWiki = True
    sys.argv = sys.argv[:1] + sys.argv[2:]
    if len(sys.argv) > 1 and sys.argv[1] == '--color':
        color = '--color'
        sys.argv = sys.argv[:1] + sys.argv[2:]

if len(sys.argv) < 2:
    ij_folder = os.path.curdir
else:
    ij_folder = sys.argv[1]

# Create the tree
createPluginsTree(ij_folder)

# Output it
result = pluginsTreeToString()
if uploadToWiki or compareToWiki:
    from fiji import MediaWikiClient

    client = MediaWikiClient(URL)
    wiki = client.sendRequest(['title', PAGE, 'action', 'edit'], None)
    begin = wiki.find('<textarea')
    begin = wiki.find('>', begin) + 1
    end = wiki.find('</textarea>', begin)
    wiki = wiki[begin:end].replace('&lt;', '<')
    if wiki != result:
        if compareToWiki:
            from fiji import SimpleExecuter
            from java.io import File, FileWriter
            file1 = File.createTempFile('PluginList', '.wiki')
            writer1 = FileWriter(file1)
            writer1.write(wiki)
            writer1.close()
            file2 = File.createTempFile('PluginList', '.wiki')
            writer2 = FileWriter(file2)
            writer2.write(result)
            writer2.close()
            diff = SimpleExecuter(['git', 'diff', color, '--ignore-space-at-eol', '--patience', '--no-index', '--src-prefix=wiki/', '--dst-prefix=local/', file1.getAbsolutePath(), file2.getAbsolutePath()])
            file1.delete()
            file2.delete()
            print diff.getOutput()
        else:
            # get username and password
            user = None
            password = None
            from os import getenv, path
            home = getenv('HOME')
            if home != None and path.exists(home + '/.netrc'):
                host = URL
                if host.startswith('http://'):
                    host = host[7:]
                elif host.startswith('https://'):
                    host = host[8:]
                slash = host.find('/')
                if slash > 0:
                    host = host[:slash]
    
                found = False
                f = open(home + '/.netrc')
                for line in f.readlines():
                    line = line.strip()
                    if line == 'machine ' + host:
                        found = True
                    elif found == False:
                        continue
                    elif line.startswith('login '):
                        user = line[6:]
                    elif line.startswith('password '):
                        password = line[9:]
                    elif line.startswith('machine '):
                        break
                f.close()
    
            if not client.isLoggedIn():
                if user != None and password != None:
                    client.logIn(user, password)
                    response = client.uploadPage(PAGE, result, 'Updated by plugin-list-parser')
                    if client.isLoggedIn():
                        client.logOut()
                    if not response:
                        print 'There was a problem with uploading', PAGE
                        if IJ.getInstance() == None:
                            sys.exit(1)
                else:
                    print 'No .netrc entry for', URL
                    if IJ.getInstance() == None:
                        sys.exit(1)
else:
    print result

########NEW FILE########
__FILENAME__ = prepare-wiki-screenshot
#!/bin/sh
''''exec "$(dirname "$0")"/ImageJ.sh --jython "$0" "$@" # (call again with fiji)'''

from ij import IJ, ImageJ

label = 'Fiji Is Just ImageJ'

if IJ.getInstance() == None:
	# called from the command line
	from sys import argv

	if len(argv) > 1:
		file = argv[1]
	else:
		file = "Stitching-overview.jpg"
	if len(argv) > 2:
		label = argv[2]
	ImageJ()
	screenshot = IJ.openImage(file)
	print "Opened", file, screenshot
else:
	screenshot = IJ.getImage()
	label = IJ.getString('Label:', label)

from fiji import Prettify_Wiki_Screenshot

plugin = Prettify_Wiki_Screenshot()
plugin.label = label
plugin.run(screenshot.getProcessor())

########NEW FILE########
__FILENAME__ = screenshot
#!/bin/sh
''''exec "$(dirname "$0")"/ImageJ.sh --jython "$0" "$@" # (call again with fiji)'''

import sys
from ij import IJ, ImageJ

if len(sys.argv) < 2:
	print 'Need an output file'
	sys.exit(1)

window = ImageJ()
window.hide()
IJ.run("Capture Screen ")
IJ.save(sys.argv[1])
sys.exit(0)

########NEW FILE########
__FILENAME__ = synchronize-db.xml.gz
#!/bin/sh
''''exec "$(dirname "$0")"/ImageJ.sh --jython "$0" "$@" # (call again with fiji)'''

from os import listdir, mkdir, remove, rmdir, system
from os.path import isdir
from re import compile
from sys import argv, exit
from sys.stderr import write
from tempfile import mktemp

from fiji.updater.logic import Checksummer, PluginCollection, \
	XMLFileReader, XMLFileWriter
from fiji.updater.util import StderrProgress, Util
from java.io import FileInputStream, FileOutputStream
from java.lang.System import getProperty
from java.util.zip import GZIPInputStream, GZIPOutputStream

dbPath = getProperty('ij.dir') + '/db.xml.gz'
plugins = PluginCollection()
XMLFileReader(plugins).read(None, GZIPInputStream(FileInputStream(dbPath)))

def addPreviousVersion(plugin, checksum, timestamp):
	p = plugins.getPlugin(plugin)
	if p != None:
		if not p.hasPreviousVersion(checksum):
			p.addPreviousVersion(checksum, timestamp)

prefix = '/var/www/update/'
pattern = compile('^(.*)-([0-9]{14})$')

def addPreviousVersions(path):
	write('Adding ' + path + '...\r')
	if isdir(prefix + path):
		names = listdir(prefix + path)
		names.sort()
		for name in names:
			if path != '':
				name = path + '/' + name
			addPreviousVersions(name)
	else:
		match = pattern.match(path)
		if match == None:
			return
		plugin = plugins.getPlugin(match.group(1))
		if plugin == None:
			print 'Ignoring', match.group(1)
			return
		checksum = Util.getDigest(match.group(1), prefix + path)
		timestamp = long(match.group(2))
		if not plugin.hasPreviousVersion(checksum):
			plugin.addPreviousVersion(checksum, timestamp)

addPreviousVersions('')

writer = XMLFileWriter(plugins)
writer.validate()
writer.write(GZIPOutputStream(FileOutputStream(dbPath)))

########NEW FILE########
__FILENAME__ = which-jar-has-plugin
#!/bin/sh
''''exec "$(dirname "$0")"/ImageJ.sh --jython "$0" "$@" # (call again with fiji)'''


from java.io import File

from java.lang import System

import sys

from zipfile import ZipFile

if len(sys.argv) < 2:
	print 'Usage:', sys.argv[0], '<name>...'
	sys.exit(1)

jars = System.getProperty("java.class.path").split(File.pathSeparator)

for name in sys.argv[1:]:
	key = '"' + name + '"'
	for jar in jars:
		try:
			config = ZipFile(jar, 'r').read('plugins.config')
			if config.find(key) > 0:
				print jar, 'contains', key
		except:
			pass # do nothing

########NEW FILE########
__FILENAME__ = wiki-monitor
#!/bin/sh
''''exec "$(dirname "$0")"/ImageJ.sh --jython --headless --mem=64m "$0" "$@" # (call again with fiji)'''

# This script allows you to monitor a Wiki conveniently, by looking at the
# Special:RecentChanges page, and comparing it with the version it found
# last time.
#
# Call the script with the URL of the Wiki's index.php as only argument. If
# the Wiki requires you to log in to see the recent changes, you can add the
# credentials to your $HOME/.netrc. The cached recent changes will be stored
# in the file ".recent-changes.<host>" in your current working directory.

from codecs import open
from sys import argv, exit
from re import search

if len(argv) != 2:
	print 'Usage:', argv[0], '<URL>'
	exit(1)

url = argv[1]

# get username and password
user = None
password = None
from os import getenv, path
home = getenv('HOME')
if home != None and path.exists(home + '/.netrc'):
	host = url
	if host.startswith('http://'):
		host = host[7:]
	elif host.startswith('https://'):
		host = host[8:]
	slash = host.find('/')
	if slash > 0:
		host = host[:slash]

	found = False
	f = open(home + '/.netrc')
	for line in f.readlines():
		line = line.strip()
		if line == 'machine ' + host:
			found = True
		elif found == False:
			continue
		elif line.startswith('login '):
			user = line[6:]
		elif line.startswith('password '):
			password = line[9:]
		elif line.startswith('machine '):
			break
	f.close()

from java.io import File

jssecacerts = File('jssecacerts')
if jssecacerts.exists():
	from java.lang import System

	System.setProperty('javax.net.ssl.trustStore', jssecacerts.getAbsolutePath())

from fiji import MediaWikiClient

client = MediaWikiClient(url)
if user != None and password != None and not client.isLoggedIn():
	client.logIn(user, password)
response = client.sendRequest(['title', 'Special:RecentChanges', 'hidebots', '0'], None)
if client.isLoggedIn():
	client.logOut()

def parse_time(string):
	m = search('\\d\\d:\\d\\d', string)
	if m is None:
		return '<notime>'
	return m.group(0)

result = ''
for line in response.split('\n'):
	i = line.find('<h4>')
	if line.find('<div') > 0 and line.find('mainContent') > 0:
		result = ''
	elif line.find('</div') > 0 and line.find('mainContent') > 0:
		break
	elif i >= 0:
		line = line[i + 4:]
		if line.endswith('</h4>'):
			line = line[:-5]
		if len(result) > 0:
			result += '\n'
		result += line + '\n'
	elif line.find('<li>') >= 0 or line.find('<li class=') >= 0:
		title = '<unknown>'
		time = '<sometime>'
		i = line.find('mw-userlink')
		if i > 0:
			start = line.find('>', i) + 1
			end = line.find('<', start)
			author = line[start:end]
			end = line.rfind('</a>', 0, i)
			start = line.rfind('>', 0, end) + 1
			title = line[start:end]
			start = line.find(';', end) + 1
			if start > 0:
				if line[start:].startswith('&#32;'):
					start += 5
				if line[start] == ' ':
					start += 1
				time = parse_time(line[start:])
		else:
			i = line.find('>Talk</a>')
			if i > 0:
				end = line.rfind('</a>', 0, i)
				start = line.rfind('>', 0, end) + 1
				author = line[start:end]
				end = line.rfind('; ', 0, start)
				time = parse_time(line[end + 2:])
				end = line.rfind('</a>', 0, end)
				start = line.rfind('">', 0, end) + 2
				title = line[start:end]
			else:
				author = '<unknown>'
		i = line.find('uploaded "<a href=')
		if i > 0:
			start = line.find('>', i) + 1
			end = line.find('<', start)
			title = ' -> ' + line[start:end]
		i = line.find('uploaded a new version of "')
		if i > 0:
			start = line.find('>', i) + 1
			end = line.find('<', start)
			title = ' ->> ' + line[start:end]
		result += '\t' + time + ' ' + title + ' (' + author + ')\n'

firstLine = 'From ' + url + '/Special:RecentChanges?hidebots=0\n'
from java.lang import System
backup = '.recent-changes.' + host
if path.exists(backup):
	f = open(backup, 'r', 'utf-8')
	firstline = f.readline().strip()
	secondline = f.readline().strip()
	f.close()
	lines = result.split('\n')
	if len(lines) > 0 and lines[0] == firstline:
		if len(lines) > 1 and lines[1].strip() == secondline:
			firstline = None
		else:
			firstline = secondline
	if firstline != None:
		for line in lines:
			if line.strip() == firstline:
				break
			else:
				if firstLine != None:
					System.out.println(firstLine)
					firstLine = None
				System.out.println(line)
else:
	System.out.println(firstLine)
	System.out.println(result)

f = open(backup, 'w', 'utf-8')
f.write(result)
f.close()

########NEW FILE########
__FILENAME__ = chess_
from time import sleep

w = 40
h = 40

def setColor(color):
	IJ.run('Colors...', 'foreground=' + color)

def square(i, j, currentX, currentY):
	IJ.runMacro('makeRectangle(' + str(w * i) + ', '
		+ str(h * j) + ', '
		+  str(w) + ', ' + str(h) + ');')
	if i == currentX and j == currentY:
		color = 'orange'
	elif (i + j) & 1 == 1:
		color = 'black'
	else:
		color = 'white'
	setColor(color)
	IJ.run('Fill')

Pawn = [18,4,11,6,9,10,10,14,15,16,6,30,
	33,30,24,16,28,14,29,10,26,5]

Pawn = [18,15,14,17,14,19,16,21,11,34,24,34,20,20,21,18,20,17]

Rook = [2,5,2,10,6,10,6,16,2,35,36,35,32,
	16,32,9,35,9,35,3,29,3,29,6,27,
	9,23,9,23,3,15,3,15,9,9,9,8,6,8,4]

Knight = [6,10,17,7,21,2,24,3,23,7,27,12,30,
	21,30,29,31,34,14,33,19,27,18,20,
	17,17,12,18,10,16,6,15,4,13]

Bishop = [17,3,15,5,17,6,13,8,12,12,13,14,
	15,16,11,34,8,34,8,36,28,36,28,33,
	25,34,21,16,23,13,22,8,18,6,19,4]

Queen = [20,5,21,3,20,1,18,3,18,5,14,5,15,
	7,14,11,18,11,13,31,13,33,25,33,25,
	31,20,11,24,11,23,7,24,5,21,5]

King = [17,2,19,2,19,4,21,4,21,6,19,6,19,8,
	22,8,22,12,19,12,19,15,23,17,24,22,
	23,27,20,30,20,31,23,31,23,32,14,31,
	13,30,17,30,14,27,13,22,15,17,16,15,
	16,12,13,12,13,8,16,8,16,6,14,6]

def path(i, j, array):
	macro = 'makePolygon('
	for k in range(0, len(array), 2):
		if k > 0:
			macro = macro + ', '
		macro = macro + str(i * w + array[k]) + ', ' + str(j * h + array[k + 1])
	macro += ');'
	IJ.runMacro(macro)

def parseCoord(coord):
	return (int(ord(coord[0]) - ord('a')),
		9 - int(coord[1]) - 1)

def draw(i, j, array, color):
	if color == "white":
		antiColor = "black"
	else:
		antiColor = "white"
	path(i, j, array)
	setColor(color)
	IJ.run("Fill")
	setColor(antiColor)
	IJ.run("Draw")
	IJ.run("Select None")

def drawCoord(coord, array, color):
	(i, j) = parseCoord(coord)
	draw(i, j, array, color)

def erase():
	i = WindowManager.getImageCount()
	while i > 0:
		WindowManager.getImage(WindowManager.getNthImageID(i)).close()
		i = i - 1

erase()

IJ.runMacro('newImage("Chess", "RGB", ' + str(w * 8) + ', '
	+ str(h * 8) + ', 1);')

def initial_field():
	return [ 'Rb', 'Nb', 'Bb', 'Qb', 'Kb', 'Bb', 'Nb', 'Rb',
		'Pb', 'Pb', 'Pb', 'Pb', 'Pb', 'Pb', 'Pb', 'Pb',
		'', '', '', '', '', '', '', '',
		'', '', '', '', '', '', '', '',
		'', '', '', '', '', '', '', '',
		'', '', '', '', '', '', '', '',
		'Pw', 'Pw', 'Pw', 'Pw', 'Pw', 'Pw', 'Pw', 'Pw',
		'Rw', 'Nw', 'Bw', 'Qw', 'Kw', 'Bw', 'Nw', 'Rw']

def get_array(name):
	if name == 'P':
		return Pawn
	elif name == 'R':
		return Rook
	elif name == 'N':
		return Knight
	elif name == 'B':
		return Bishop
	elif name == 'Q':
		return Queen
	elif name == 'K':
		return King

def draw_one(i, j, field, selectedX, selectedY):
	square(i, j, selectedX, selectedY)
	f = field[i + j * 8]
	if f != '':
		array = get_array(f[0])
		if f[1] == 'b':
			color = 'black'
		else:
			color = 'white'
		draw(i, j, array, color)

def draw_field(field, selectedX, selectedY):
	for j in range(0, 8):
		for i in range(0, 8):
			draw_one(i, j, field, selectedX, selectedY)

IJ.setTool(Toolbar.HAND)
field = initial_field()
currentX = -1
currentY = -1
draw_field(field, currentX, currentY)
canvas = WindowManager.getCurrentImage().getCanvas()
clicked = 0

while True:
	p = canvas.getCursorLoc()
	x = int(p.x / w)
	y = int(p.y / h)
	newClicked = canvas.getModifiers() & 16
	if clicked and not newClicked:
		if currentX >= 0:
			if x != currentX or y != currentY:
				oldOffset = currentX + 8 * currentY
				field[x + 8 * y] = field[oldOffset]
				field[oldOffset] = ''
			draw_one(currentX, currentY, field, -1, -1)
			draw_one(x, y, field, -1, -1)
			currentX = currentY = -1
		else:
			draw_one(x, y, field, x, y)
			currentX = x
			currentY = y
	clicked = newClicked
	sleep(0.1)

########NEW FILE########
__FILENAME__ = Command_Launcher_Python
from java.awt import Color
from java.awt.event import TextListener
import ij

#commands = [c for c in ij.Menus.getCommands().keySet()]
# Above, equivalent list as below:
commands = ij.Menus.getCommands().keySet().toArray()
gd = ij.gui.GenericDialog('Command Launcher')
gd.addStringField('Command: ', '');
prompt = gd.getStringFields().get(0)
prompt.setForeground(Color.red)

class TypeListener(TextListener):
	def textValueChanged(self, tvc):
		if prompt.getText() in commands:
			prompt.setForeground(Color.black)
			return
		prompt.setForeground(Color.red)
		# or loop:
		#for c in commands:
		#	if c == text:
		#		prompt.setForeground(Color.black)
		#		return
		#
		#prompt.setForeground(Color.red)

prompt.addTextListener(TypeListener())
gd.showDialog()
if not gd.wasCanceled(): ij.IJ.doCommand(gd.getNextString())

# This python version does not encapsulate the values of the variables, so they are all global when defined outside the class definition.
# In contrast, the lisp 'let' definitions encapsulates them in full
# As an advantage, each python script executes within its own namespace, whereas clojure scripts run all within a unique static interpreter.

########NEW FILE########
__FILENAME__ = Cover_Maker
# Cover Maker was written by PAvel Tomancak with minor help of
# Albert Cardona & Johannes Schindelin (Pop & Mom)

from ij import IJ
from ij.io import FileSaver
from math import sqrt, pow
import os
from os import path
import sys
import re
import random
from fiji.scripting import Weaver
from fiji.util.gui import GenericDialogPlus
from mpicbg.ij.integral import Scale
from java.awt.event import ActionListener, TextListener
from loci.formats.gui import BufferedImageReader
import zipfile
import zlib

def CropInputImage(ip, width, height):
	temp = int(ip.width/width)
	newwidth = temp * width
	temp = int(ip.height/height)
	newheight = temp * height

	roi = Roi(0,0,newwidth,newheight)
	ip.setRoi(roi)
	ip = ip.crop()
	return ip.crop()

#split template image into tiles
def SplitImage(ip, width, height):
	stack = ImageStack(width, height)

	for x in range(0,ip.width,width):
		for y in range(0,ip.height,height):
			roi = Roi(x,y,width,height)
			ip.setRoi(roi)
			ip2 = ip.crop()
			stack.addSlice(None, ip2)
	return stack

# inlines Java code doing the main comparison calculations
def Inline(arrays):
	return Weaver.inline(
		"""
		int[] pixelst = (int[])arrays.get(0);
		int[] pixelsd = (int[])arrays.get(1);
		double sum = 0;
		for (int i=0; i<pixelst.length; i++) {
			int t = pixelst[i];
			int d = pixelsd[i];
			int red = ((t >> 16)&0xff) - ((d >> 16)&0xff);
			int green = ((t >> 8)&0xff) - ((d >> 8)&0xff);
			int blue = (t&0xff) - (d&0xff);
			//sum += Math.sqrt(red * red + green * green + blue * blue);
			sum += red * red + green * green + blue * blue;
		}
		return sum;
		""",
		{"arrays" : arrays})

#compare all tiles to all downsampled database images of the same size
#iterate through template slices
def CreateCover(ip, width, height, dbpath):
	# split input image into appropriate tiles
	stackt = SplitImage(ip, width, height)
	impt = ImagePlus("template", stackt)
	nSlicestmp = impt.getNSlices()

	# open the preprocessed database
	print dbpath
	impd = IJ.openImage(dbpath)
	stackd = impd.getImageStack()
	nSlicesdb = impd.getNSlices()

	#associate index with image names
	imageNames = impd.getProperty('Info')
	imageList = imageNames.split(';')

	# set up preview output
	outputip = ColorProcessor(ip.width, ip.height)
	outputimp = ImagePlus("output", outputip)
	outputimp.show()

	cols = ip.width/width
	rows = ip.height/height

	print str(cols) + "," + str(rows)

	x = 0
	y = 0

	arrays = [None, None] # a list of two elements
	cruncher = Inline(arrays)
	tileNames = {}
	tileIndex = {}
	placed = {}
	used = {}

	while len(placed) < nSlicestmp:
		randomTileIndex = random.randint(1, nSlicestmp)
		if randomTileIndex in placed:
			continue
		# transform to row adn column coordinate
		if randomTileIndex%rows == 0:
			y = rows-1
			x = (randomTileIndex/rows)-1
		else:
			y = (randomTileIndex%rows)-1
			x = int(randomTileIndex/rows)

		pixelst = stackt.getPixels(randomTileIndex)
		minimum = Float.MAX_VALUE
		#iterate through database images
		j = 1
		indexOfBestMatch = 0
		arrays[0] = pixelst
		while j < nSlicesdb:
			if j in used:
				j +=1
				continue
			arrays[1] = stackd.getPixels(j)
			diff = cruncher.call()
			if diff < minimum:
				minimum = diff
				indexOfBestMatch = j
			j += 1
		ip = stackd.getProcessor(indexOfBestMatch)
		outputip.copyBits(ip, x*width, y*height, 0)
		used[indexOfBestMatch] = 1
		tileNames[randomTileIndex] = imageList[indexOfBestMatch-1]
		tileIndex[randomTileIndex] = indexOfBestMatch-1
		outputimp.draw()
		placed[randomTileIndex] = 1

	return tileNames, tileIndex, cols, rows

def ScaleImageToSize(ip, width, height):
	"""Scale image to a specific size using Stephans scaler"""
	smaller = ip.scale( width, height );
	return smaller

def SaveCoverFromFs(tiles, newwidth, newheight, cols, rows):

	tilewidth = int(newwidth/cols)
	tileheight = int(newheight/rows)

	newwidth = int(newwidth/tilewidth) * tilewidth
	newheight = int(newheight/tileheight) * tileheight

	hiresoutip = ColorProcessor(newwidth, newheight)
	hiresout = ImagePlus("hi res output", hiresoutip)
	hiresout.show()

	x = 0
	y = -1

	plane = []

	# scale the images
	for i in sorted(tiles.iterkeys()):
		if y < rows-1:
			y += 1
		else:
			y = 0
			x += 1
		imp = IJ.openImage(str(tiles[i]))
		scale = Scale(imp.getProcessor())
		ipscaled = ScaleImageToSize(scale, tilewidth, tileheight)
		hiresoutip.copyBits(ipscaled, x*tilewidth, y*tileheight, 0)
		hiresout.draw()


def SaveCoverFromZip(tileIndex, newwidth, newheight, cols, rows, originalspath):
	baseDir = re.sub(r'\/originals.zip', "", originalspath)

	#print baseDir

	zf = zipfile.ZipFile(originalspath, mode='r')

	tilewidth = int(newwidth/cols)
	tileheight = int(newheight/rows)

	newwidth = int(newwidth/tilewidth) * tilewidth
	newheight = int(newheight/tileheight) * tileheight

	hiresoutip = ColorProcessor(newwidth, newheight)
	hiresout = ImagePlus("hi res output", hiresoutip)
	hiresout.show()

	x = 0
	y = -1

	plane = []

	# scale the images
	for i in sorted(tileIndex.iterkeys()):
		if y < rows-1:
			y += 1
		else:
			y = 0
			x += 1
		#bi = bir.openImage(tileIndex[i]);
		#ip = ColorProcessor(bi)
		image = zf.read(str(tileIndex[i]) + ".jpeg")
		#IJ.log("Placing image :" + str(tileIndex[i]) + ".jpeg")
		my_file = open(baseDir + 'temporary.jpeg','w')
		my_file.write(image)
		my_file.close()
		imp = IJ.openImage(baseDir + "/temporary.jpeg")
		ip = imp.getProcessor()
		scale = Scale(ip)
		ipscaled = ScaleImageToSize(scale, tilewidth, tileheight)
		hiresoutip.copyBits(ipscaled, x*tilewidth, y*tileheight, 0)
		hiresout.draw()

class ResolutionListener(TextListener):
	def __init__(self, resField, widthPixels, heightPixels, widthInches, heightInches):
		self.resField = resField
		self.widthPixels = widthPixels
		self.heightPixels = heightPixels
		self.widthInches = widthInches
		self.heightInches = heightInches
	def textValueChanged(self, e):
		source = e.getSource()
		if source == self.resField:
			dpi = float(source.getText())
			width = float(self.widthInches.getText())
			height = float(self.heightInches.getText())
			self.widthPixels.setText(str(int(width * dpi)))
			self.heightPixels.setText(str(int(height * dpi)))
		elif source == self.widthInches:
			dpi = float(self.resField.getText())
			widthInches = float(source.getText())
			heightInches = widthInches/ratio
			self.heightInches.setText(str(heightInches))
			self.widthPixels.setText(str(int(float(self.widthInches.getText()) * dpi)))
			self.heightPixels.setText(str(int(float(self.heightInches.getText()) * dpi)))

def Dialog(imp):
	dpi = 300
	# a4 width in inches
	defaultWidth = 11.69
	defaultHeight = defaultWidth/ratio
	defaultAspectRatio = 1.41

	if imp:
		gd = GenericDialogPlus("Cover Maker")
		gd.addMessage("Input Options")
		gd.addFileField("Select image database", "", 20)
		gd.addMessage("Cover Maker Options")
		gd.addNumericField("tile width", 12, 0)
		gd.addNumericField("tile height", 9, 0)

		gd.showDialog()

		if gd.wasCanceled():
			print "User canceled dialog!"
			return
		databasepath = gd.getNextString()
		tilewidth = gd.getNextNumber()
		tileheight = gd.getNextNumber()

		return databasepath, imp.getWidth(), imp.getHeight(), int(tilewidth), int(tileheight)
	else:
		IJ.showMessage( "You should have at least one image open." )

def SaveDialog(imp):
	dpi = 300
	# a4 width in inches
	defaultWidth = 11.69
	defaultHeight = defaultWidth/ratio
	defaultAspectRatio = 1.41

	if imp:
		gd = GenericDialogPlus("Cover Maker")
		gd.addMessage("Saving options")
		gd.addNumericField("resolution (dpi)", dpi, 0)
		gd.addNumericField("width (pixels)", defaultWidth*dpi, 0)
		gd.addNumericField("height (pixels)", defaultHeight*dpi, 0)
		gd.addNumericField("width (inches)", defaultWidth, 2)
		gd.addNumericField("height (inches)", defaultHeight, 2)
		gd.addFileField("Select Originals database", "", 20)

		fields = gd.getNumericFields()

		resField = fields.get(0)
		widthPixels = fields.get(1)
		heightPixels = fields.get(2)
		widthInches = fields.get(3)
		heightInches = fields.get(4)

		# resolution and size listener
		textListener = ResolutionListener(resField, widthPixels, heightPixels, widthInches, heightInches)
		resField.addTextListener(textListener)
		widthInches.addTextListener(textListener)
		heightInches.addTextListener(textListener)

		gd.showDialog()

		if gd.wasCanceled():
			print "User canceled dialog!"
			return

		newres = gd.getNextNumber()
		newwidth = gd.getNextNumber()
		newheight = gd.getNextNumber()
		originalspath = gd.getNextString()

		return int(newwidth), int(newheight), newres, originalspath
	else:
		IJ.showMessage( "You should have at least one image open." )

# main body of the program
imp = IJ.getImage()
ratio = float(imp.getWidth()) / float(imp.getHeight())

#get options
(dbpath, width, height, tilewidth, tileheight) = Dialog(imp)

# run program
ip = CropInputImage(imp.getProcessor(), tilewidth, tileheight)
tileName, tileIndex, cols, rows = CreateCover(ip, tilewidth, tileheight, dbpath)

# save output
newwidth, newheight, res, originalspath = SaveDialog(imp)
if originalspath:
	SaveCoverFromZip(tileIndex, newwidth, newheight, cols, rows, originalspath)
else:
	SaveCoverFromFs(tileName, newwidth, newheight, cols, rows)

########NEW FILE########
__FILENAME__ = Prepare_Cover_Maker_Database
from ij import IJ
from ij.io import FileSaver
from mpicbg.ij.integral import Scale
import os
import sys
from os import path, walk
from loci.formats import ImageReader
from loci.formats import ImageWriter
from fiji.util.gui import GenericDialogPlus
from java.awt.event import TextListener
import zipfile
import zlib

def ScaleImageToSize(ip, width, height):
	"""Scale image to a specific size using Stephans scaler"""
	smaller = ip.scale( width, height )
	return smaller

def SaveToZip(zf, ip, baseDir, counter):
	fs = FileSaver(ip)
	fs.setJpegQuality(75)
	fs.saveAsJpeg(baseDir + "/tmp.jpeg")
	zipName = str(counter) + ".jpeg"
	zf.write(baseDir + "/tmp.jpeg", arcname=zipName)
	os.remove(baseDir + "/tmp.jpeg")

def DirList(baseDir):
	r = ImageReader()
	imgStats = {}
	for root, dirs, files in os.walk(str(baseDir)):
		for f1 in files:
			if f1.endswith(".jpg") or f1.endswith(".jpe") or f1.endswith(".jpeg"):
				id = root + "/" +  f1
				r.setId(id)
				if r is None:
					print "Couldn\'t open image from file:", id
					continue
				w = r.getSizeX()
				h = r.getSizeY()
				imgStats[str(w) + "_" + str(h)] = imgStats.get(str(w) + "_" + str(h), 0)+1
				IJ.log("Found image: " + str(id))
				#counter += 1
	r.close()
	#print summary
	summary = ''
	for k, v in imgStats.iteritems():
		dim = k.split("_")
		ratio = float(dim[0])/float(dim[1])
		IJ.log("Found " + str(v) + " images of dimension " + str(dim[0]) + "x" + str(dim[1]) + " apect ratio " + str(round(ratio, 2)))
		summary = summary + "\nFound " + str(v) + " images of dimension " + str(dim[0]) + "x" + str(dim[1]) + " apect ratio " + str(round(ratio, 2))
	return summary

def PrepareDatabase(minw, maxw, baseDir, aspectRatio, majorWidth, majorHeight):
	outputpath = baseDir + "/" + str(majorWidth) + "_" + str(majorHeight) + "_orig.tif"
	#initialize stacks and labels
	stackScaled = []
	stackOrig = ImageStack(majorWidth, majorHeight)
	imageNames = []
	for i in range(minw, maxw+1):
		stackScaled.append(ImageStack(i, int(round(i/aspectRatio, 0))))
		imageNames.append('')

	counter = 0

	# initialize zip file for originals
	zf = zipfile.ZipFile(baseDir + "/originals.zip", mode='w', compression=zipfile.ZIP_DEFLATED, allowZip64=1)
	zf.writestr('from_string.txt', 'hello')
	zf.close()
	zf = zipfile.ZipFile(baseDir + "/originals.zip", mode='a', compression=zipfile.ZIP_DEFLATED, allowZip64=1)

	for root, dirs, files in os.walk(str(baseDir)):
		for f1 in files:
			if f1.endswith(".jpg") or f1.endswith(".jpe") or f1.endswith(".jpeg"):
				id = root + "/" +  f1
				IJ.redirectErrorMessages()
				IJ.redirectErrorMessages(1)
				imp = IJ.openImage(id)
				if imp is None:
					print "Couldn\'t open image from file:", id
					continue
				# skip non RGBimages
				if imp.getProcessor().getNChannels() != 3:
					print "Converting non RGB image:", id
					if imp.getStackSize() > 1:
						StackConverter(imp).convertToRGB()
					else:
						ImageConverter(imp).convertToRGB()
				#skip images with different aspect ratio
				width = imp.getWidth()
				height = imp.getHeight()
				ratio = round(float(width)/float(height), 2) # this makes the ratio filering approximate, minor variations in image dimensions will be ignored
				if ratio != aspectRatio:
					IJ.log("Skipping image of size: " + str(width) + "," + str(height))
					continue
				# now scale the image within a given range
				scale = Scale(imp.getProcessor())
				IJ.log("Scaling image " + str(counter) + " " + str(id))
				for i in range(minw, maxw+1):
					stackScaled[i-minw].addSlice(None, ScaleImageToSize(scale, i, int(round(i/aspectRatio, 0))))
					imageNames[i-minw] += str(id) + ";"
				# save the originals to a temp directory
				scaledOrig = ImagePlus(None, ScaleImageToSize(scale, majorWidth, majorHeight))
				SaveToZip(zf, scaledOrig, baseDir, counter)
				counter += 1
	zf.close()
	# save the stacks
	for i in range(minw, maxw+1):
		impScaled = ImagePlus(str(minw) + "_" + str(int(round(i/aspectRatio, 0))), stackScaled[i-minw])
		impScaled.show()
		#print imageNames
		impScaled.setProperty('Info', imageNames[i-minw][:-1])
		fs = FileSaver(impScaled)
		filepath = baseDir + "/" + str(i) + "_" + str(int(round(i/aspectRatio, 0))) + ".tif"
		IJ.log("Saving output stack" + str(filepath))
		fs.saveAsTiffStack(filepath)
		#IJ.save(impScaled, filepath);
		IJ.log("Done")



def DialogAnalyze():
	dpi = 300
	defaultAspectRatio = 1.41

	gd = GenericDialogPlus("Cover Maker")
	gd.addMessage("Prepare Image database")
	gd.addDirectoryField("Select base directory containing images", "", 20)

	gd.showDialog()

	if gd.wasCanceled():
		print "User canceled dialog!"
		return
	imageBaseDir = gd.getNextString()

	return imageBaseDir

class RatioToDim(TextListener):
	def __init__(self, aspRatio, minw, maxw, minh, maxh):
		self.aspRatio = aspRatio
		self.minw = minw
		self.maxw = maxw
		self.minh = minh
		self.maxh = maxh
	def textValueChanged(self, e):
		source = e.getSource()
		if source == self.aspRatio:
			#print "bla " + str(self.minw.getText)# + " " + str(float(source.getText()))
			self.minh.setText(str(int(round(float(self.minw.getText())/float(source.getText())))))
			self.maxh.setText(str(int(round(float(self.maxw.getText())/float(source.getText())))))
		elif source == self.minw:
			self.minh.setText(str(int(round(float(source.getText())/float(self.aspRatio.getText()), 0))))
		elif source == self.maxw:
			self.maxh.setText(str(int(round(float(source.getText())/float(self.aspRatio.getText()), 0))))

def DialogGenerate(imageBaseDir, summary):
	dpi = 300
	defaultAspectRatio = 1.33
	defaultTileWidth = 15
	defaultOriginalWidth = 150
	defaultOriginalHeight = 113
	defaultTileHeight = round(defaultTileWidth/defaultAspectRatio)

	gd = GenericDialogPlus("Cover Maker")
	gd.addMessage("Prepare Image database")
	gd.addDirectoryField("Select base directory containing images", imageBaseDir, 20)
	gd.addMessage(summary)
	gd.addNumericField("Aspect ratio", defaultAspectRatio, 2)
	gd.addNumericField("Original width", defaultOriginalWidth, 0)
	gd.addNumericField("Original height", defaultOriginalHeight, 0)
	gd.addNumericField("minimal tile width", defaultTileWidth, 0)
	gd.addNumericField("maximal tile width", defaultTileWidth, 0)
	gd.addNumericField("minimal tile height", defaultTileHeight, 0)
	gd.addNumericField("maximal tile height", defaultTileHeight, 0)

	fields = gd.getNumericFields()

	aspRatio = fields.get(0)
	minw = fields.get(3)
	maxw = fields.get(4)
	minh = fields.get(5)
	maxh = fields.get(6)

	# resolution and size listener
	textListener = RatioToDim(aspRatio, minw, maxw, minh, maxh)
	aspRatio.addTextListener(textListener)
	minw.addTextListener(textListener)
	maxw.addTextListener(textListener)

	gd.showDialog()

	if gd.wasCanceled():
		print "User canceled dialog!"
		return
	imageBaseDir = gd.getNextString()
	aspectRatio = gd.getNextNumber()
	majorWidth = gd.getNextNumber()
	majorHeight = gd.getNextNumber()
	mintilewidth = gd.getNextNumber()
	maxtilewidth = gd.getNextNumber()

	return int(mintilewidth), int(maxtilewidth), imageBaseDir, float(aspectRatio), int(majorWidth), int(majorHeight)

imageBaseDir = ''
summary = ''

#imageBaseDir = DialogAnalyze()
#summary = DirList(imageBaseDir)
(minw, maxw, imageBaseDir, aspectRatio, majorWidth, majorHeight) = DialogGenerate(imageBaseDir, summary)
PrepareDatabase(minw, maxw, imageBaseDir, aspectRatio, majorWidth, majorHeight)

########NEW FILE########
__FILENAME__ = Delayed_Snapshot
# Take a snapshot after a delay specified in a dialog
# 
# The plugin has to fork, which is done by:
# 1 - declaring a function to do the work, 'snasphot'
# 2 - invoking the function via thread.start_new_thread,
#     which runs it in a separate thread.


import thread
import time

def snapshot(delay):
   time.sleep(delay)
   IJ.doCommand('Capture Screen')

gd = GenericDialog('Delay')
gd.addSlider('Delay (secs.): ', 0, 20, 5)
gd.showDialog()

if not gd.wasCanceled():
	# the 'extra' comma signals tuple, a kind of list in python.
	thread.start_new_thread(snapshot, (int(gd.getNextNumber()),))

########NEW FILE########
__FILENAME__ = Edit_LUT_As_Text
import jarray
from java.awt import Font, Menu, MenuItem
from java.awt.event import ActionListener
from java.awt.image import IndexColorModel

# Call this script to show the current Lookup Table in an editor.
# The user can edit it, and call Lookup Table>Set Lookup Table after editing
# the numbers.

def editLUTAsText():
	image = WindowManager.getCurrentImage()
	if image == None:
		IJ.error('Need an image')
		return
	ip = image.getProcessor()
	cm = ip.getCurrentColorModel()
	if not hasattr(cm, 'getMapSize'):
		IJ.error('Need an 8-bit color image')
		return

	size = cm.getMapSize()
	if size > 256:
		IJ.error('Need an 8-bit color image')
		return
	reds = jarray.zeros(size, 'b')
	greens = jarray.zeros(size, 'b')
	blues = jarray.zeros(size, 'b')
	cm.getReds(reds)
	cm.getGreens(greens)
	cm.getBlues(blues)

	def color(array, index):
		value = array[index]
		if value < 0:
			value += 256
		return '% 4d' % value

	text = ''
	for i in range(0, size):
		text = text + color(reds, i) + ' ' + color(greens, i) + ' ' \
			+ color(blues, i) + "\n"

	editor = Editor(25, 80, 12, Editor.MONOSPACED | Editor.MENU_BAR)
	editor.create('Lookup Table', text)

	def string2byte(string):
		value = int(string)
		if value > 127:
			value -= 256
		if value < -128:
			value = 128
		return value

	class SetLookupTable(ActionListener):
		def actionPerformed(self, event):
			text = editor.getText()
			i = 0
			for line in text.split("\n"):
				colors = line.split()
				if len(colors) < 3:
					continue
				reds[i] = string2byte(colors[0])
				greens[i] = string2byte(colors[1])
				blues[i] = string2byte(colors[2])
				i += 1
			cm = IndexColorModel(8, 256, reds, greens, blues)
			ip.setColorModel(cm)
			image.updateAndRepaintWindow()

	menuItem = MenuItem('Set Lookup Table')
	menuItem.addActionListener(SetLookupTable())

	menu = Menu('Lookup Table')
	menu.add(menuItem)

	menuBar = editor.getMenuBar()
	for i in range(menuBar.getMenuCount() - 1, -1, -1):
		label = menuBar.getMenu(i).getLabel()
		if label == 'Macros' or label == 'Debug':
			menuBar.remove(i)
	menuBar.add(menu)

editLUTAsText()

########NEW FILE########
__FILENAME__ = Find_Dimension_of_Raw_Image
# This script serves two purposes:
#
# - to demonstrate that an AWT Listener can be written in Jython, and
#
# - to find the width of an image you know is uncompressed, but do not know
#   the dimensions.
#
# To use it, open the raw image with File>Import>Raw... choosing a width and
# height that should roughly be the correct one.  Then start this script,
# which will open a dialog box with a slider, with which you can interactively
# test new widths -- the pixels in the image window will be updated accordingly.

from ij.gui import GenericDialog

from java.awt.event import AdjustmentListener

from java.lang import Math, System

image = WindowManager.getCurrentImage()
ip = image.getProcessor()
pixelsCopy = ip.getPixelsCopy()
pixels = ip.getPixels()
width = ip.getWidth()
height = ip.getHeight()

minWidth = int(Math.sqrt(len(pixels) / 16))
maxWidth = minWidth * 16

class Listener(AdjustmentListener):
	def adjustmentValueChanged(self, event):
		value = event.getSource().getValue()
		rowstride = min(width, value)
		for j in range(0, min(height, int(width * height / value))):
			System.arraycopy(pixelsCopy, j * value,
				pixels, j * width, rowstride)
		image.updateAndDraw()

gd = GenericDialog("Width")
gd.addSlider("width", minWidth, maxWidth, ip.getHeight())
gd.getSliders().get(0).addAdjustmentListener(Listener())
gd.showDialog()
if gd.wasCanceled():
	pixels[0:width * height] = pixelsCopy
	image.updateAndDraw()

########NEW FILE########
__FILENAME__ = list_all_threads
from jarray import zeros
from java.lang import *

def findRootThreadGroup():
	tg = Thread.currentThread().getThreadGroup()
	root_tg = tg.getParent()
	root_tg = tg
	parent = root_tg.getParent()
	while None != parent:
		root_tg = parent
		parent = parent.getParent()
	return root_tg

def listGroup(list, group):
	threads = zeros(group.activeCount(), Thread)
	group.enumerate(threads, 0)
	groups = zeros(group.activeGroupCount(), ThreadGroup)
	group.enumerate(groups, 0)
	for t in threads:
		if None is not t: list.append(t.getName())
	for g in groups:
		if None is not g: listGroup(list, g)

def listThreadNames():
	list = []
	listGroup(list, findRootThreadGroup())
	return list

IJ.log("Threads:")
i = 1
for thread in listThreadNames():
	IJ.log(str(i) + ": " + thread)
	i += 1


########NEW FILE########
__FILENAME__ = extract_stack_under_arealist
# Albert Cardona 2009-11-16 for Nitai Steinberg
#
# Select an AreaList in a TrakEM2 project and then run this script.
#

from ij import IJ, ImageStack, ImagePlus
from ij.gui import ShapeRoi
from ij.process import ByteProcessor, ShortProcessor
from ini.trakem2.display import Display, AreaList, Patch
from java.awt import Color

def extract_stack_under_arealist():
	# Check that a Display is open
	display = Display.getFront()
	if display is None:
		IJ.log("Open a TrakEM2 Display first!")
		return
	# Check that an AreaList is selected and active:
	ali = display.getActive()
	if ali is None or not isinstance(ali, AreaList):
		IJ.log("Please select an AreaList first!")
		return

	# Get the range of layers to which ali paints:
	ls = display.getLayerSet()
	ifirst = ls.indexOf(ali.getFirstLayer())
	ilast = ls.indexOf(ali.getLastLayer())
	layers = display.getLayerSet().getLayers().subList(ifirst, ilast +1)

	# Create a stack with the dimensions of ali
	bounds = ali.getBoundingBox()
	stack = ImageStack(bounds.width, bounds.height)

	# Using 16-bit. To change to 8-bit, use GRAY8 and ByteProcessor in the two lines below:
	type = ImagePlus.GRAY16
	ref_ip = ShortProcessor(bounds.width, bounds.height)

	for layer in layers:
		area = ali.getArea(layer)
		z = layer.getZ()
		ip = ref_ip.createProcessor(bounds.width, bounds.height)
		if area is None:
			stack.addSlice(str(z), bp)
			continue

		# Create a ROI from the area of ali at layer:
		aff = ali.getAffineTransformCopy()
		aff.translate(-bounds.x, -bounds.y)
		roi = ShapeRoi(area.createTransformedArea(aff))

		# Create a cropped snapshot of the images at layer under ali:
		flat = Patch.makeFlatImage(type, layer, bounds, 1.0, layer.getDisplayables(Patch), Color.black)
		b = roi.getBounds()
		flat.setRoi(roi)
		ip.insert(flat.crop(), b.x, b.y)

		# Clear the outside of ROI (ShapeRoi is a non-rectangular ROI type)
		bimp = ImagePlus("", ip)
		bimp.setRoi(roi)
		ip.setValue(0)
		ip.setBackgroundValue(0)
		IJ.run(bimp, "Clear Outside", "")

		# Accumulate slices
		stack.addSlice(str(z), ip)

	imp = ImagePlus("AreaList stack", stack)
	imp.setCalibration(ls.getCalibrationCopy())
	imp.show()


# Execute:
extract_stack_under_arealist()

########NEW FILE########
__FILENAME__ = Homogenize_Ball_Radius
############## Ball Size Homogenize
# Set a specific radius to all individual spheres
# of all Ball objects of the displayed TrakEM2 project.

gd = GenericDialog("Ball Radius")
gd.addNumericField( "radius :", 40, 2 )
gd.showDialog()
if not gd.wasCanceled() :
	calibrated_radius = gd.getNextNumber()  # in microns, nm, whatever

	display = Display.getFront()
	layerset = display.getLayerSet()
	cal = layerset.getCalibration()
	# bring radius to pixels
	new_radius = calibrated_radius / cal.pixelWidth

	for ballOb in layerset.getZDisplayables(Ball):
		for i in range(ballOb.getCount()):
			ballOb.setRadius(i, new_radius)
			ballOb.repaint(True, None)
##############
########NEW FILE########
__FILENAME__ = Measure_AreaLists
# Albert Cardona 20081204 14:55
# 
# An example script for TrakEM2 to measure the areas of each AreaList at each
# layer, and also the mean intensity values of the images under such areas.
#
# Works by creating a ShapeRoi ouf of the area of the java.awt.geom.Area that
# an AreaList has for a given Layer.
#
# Reports in an ImageJ Results Table.
# 
# There are two measure functions:
# 1 - measure: uses ImageJ's measurement settings and options
# 2 - measureCustom: directly creates a ResultsTable with each AreaList name,
# id, layer index, layer Z, area in the layer and mean in the layer.
#
# The declaration and invocation of the first "measure" function are commented
# out with triple quotes.
# 
# Built as requested by Jean-Yves Tinevez on 20081204 on fiji-devel mailing list
# 

from java.awt.geom import AffineTransform

"""
def measure(layerset):
  # Obtain a list of all AreaLists:
  alis = layerset.getZDisplayables(AreaList)
  # The loader
  loader = layerset.getProject().getLoader()

  for ali in alis:
    affine = ali.getAffineTransformCopy()
    box = ali.getBoundingBox()
    for layer in layerset.getLayers():
      # The java.awt.geom.Area object for the AreaList 'ali'
      # at the given Layer 'layer':
      area = ali.getArea(layer)
      if area:
        # Bring the area to world coordinates,
        # and then local to its own data:
        tr = AffineTransform()
        tr.translate(-box.x, -box.y)
        tr.concatenate(affine)
        area = area.createTransformedArea(tr)
        # Create a snapshot of the images under the area:
        imp = loader.getFlatImage(layer, box, 1, 0xffffffff,
              ImagePlus.GRAY8, Patch, False)
        # Set the area as a roi
        imp.setRoi(ShapeRoi(area))
        # Perform measurement according to ImageJ's measurement options:
	# (Calibrated)
        IJ.run(imp, "Measure", "")

display = Display.getFront()
if display is not None:
  # Obtain the LayerSet of the current Display canvas:
  layerset = Display.getFront().getLayer().getParent()
  # Measure!
  measure(layerset)
else:
  IJ.showMessage("Open a TrakEM2 display first!")
"""


# As an alternative, create your own ResultsTable:
def measureCustom(layerset):
  # Obtain a list of all AreaLists:
  alis = layerset.getZDisplayables(AreaList)
  # The loader
  loader = layerset.getProject().getLoader()
  # The ResultsTable
  table = Utils.createResultsTable("AreaLists", ["id", "layer", "Z", "area", "mean"])
  # The LayerSet's Calibration (units in microns, etc)
  calibration = layerset.getCalibrationCopy()
  # The measurement options as a bit mask:
  moptions = Measurements.AREA | Measurements.MEAN
  
  for ali in alis:
    affine = ali.getAffineTransformCopy()
    box = ali.getBoundingBox()
    index = 0
    for layer in layerset.getLayers():
      index += 1 # layer index starts at 1, so sum before
      # The java.awt.geom.Area object for the AreaList 'ali'
      # at the given Layer 'layer':
      area = ali.getArea(layer)
      if area:
        # Bring the area to world coordinates,
        # and then local to its own data:
        tr = AffineTransform()
        tr.translate(-box.x, -box.y)
        tr.concatenate(affine)
        area = area.createTransformedArea(tr)
        # Create a snapshot of the images under the area:
        imp = loader.getFlatImage(layer, box, 1, 0xffffffff,
              ImagePlus.GRAY8, Patch, False)
        # Set the area as a roi
        imp.setRoi(ShapeRoi(area))
        # Perform measurements (uncalibrated)
	# (To get the calibration, call layerset.getCalibrationCopy())
        stats = ByteStatistics(imp.getProcessor(), moptions, calibration)
	table.incrementCounter()
	table.addLabel("Name", ali.getTitle())
	table.addValue(0, ali.getId())
	table.addValue(1, index) # the layer index
	table.addValue(2, layer.getZ()) 
	table.addValue(3, stats.area)
	table.addValue(4, stats.mean)
    # Update and show the table
    table.show("AreaLists")


# Get the front display, if any:
display = Display.getFront()

if display is not None:
  # Obtain the LayerSet of the current Display canvas:
  layerset = Display.getFront().getLayer().getParent()
  # Measure!
  measureCustom(display.getFront().getLayer().getParent())
else:
  IJ.showMessage("Open a TrakEM2 display first!")


########NEW FILE########
__FILENAME__ = T2_Select_All
# Example script to select all 2D objects of the current layer
# in a trakem project whose display window is at the front.

display = Display.getFront()

if display is None:
	IJ.showMessage("No TrakEM2 displays are open.")
else:
	layer = display.getLayer()
	sel = display.getSelection()
	# Add all displayables of the layer to the selection of the front display:
	for d in layer.getDisplayables():
		sel.add(d)

########NEW FILE########
__FILENAME__ = T2_set_all_transforms_to_identity
display = Display.getFront()
if display is None:
	IJ.showMessage("No TrakEM displays are open.")
else:
	layer_set = display.getLayer().getParent()
	for la in layer_set.getLayers():
		for d in la.getDisplayables():
			d.getAffineTransform().setToIdentity()

########NEW FILE########
__FILENAME__ = Correct_3D_drift
# Robert Bryson-Richardson and Albert Cardona 2010-10-08 at Estoril, Portugal
# EMBO Developmental Imaging course by Gabriel Martins
#
# Register time frames (stacks) to each other using Stitching_3D library
# to compute translations only, in all 3 spatial axes.
# Operates on a virtual stack.
# 23/1/13 -
# added user dialog to make use of virtual stack an option

from ij import VirtualStack, IJ, CompositeImage, ImageStack
from ij.process import ColorProcessor
from ij.io import DirectoryChooser
from ij.gui import YesNoCancelDialog
from mpicbg.imglib.image import ImagePlusAdapter
from mpicbg.imglib.algorithm.fft import PhaseCorrelation
from javax.vecmath import Point3i
from java.io import File, FilenameFilter

# imp stands for ij.ImagePlus instance

def compute_stitch(imp1, imp2):
  """ Compute a Point3i that expressed the translation of imp2 relative to imp1."""
  phc = PhaseCorrelation(ImagePlusAdapter.wrap(imp1), ImagePlusAdapter.wrap(imp2), 5, True)
  phc.process()
  return Point3i(phc.getShift().getPosition())

def extract_frame(imp, frame, channel):
  """ From a VirtualStack that is a hyperstack, contained in imp,
  extract the timepoint frame as an ImageStack, and return it.
  It will do so only for the given channel. """
  stack = imp.getStack() # multi-time point virtual stack
  vs = ImageStack(imp.width, imp.height, None)
  for s in range(1, imp.getNSlices()+1):
    i = imp.getStackIndex(channel, s, frame)
    vs.addSlice(str(s), stack.getProcessor(i))
  return vs

def compute_frame_translations(imp, channel):
  """ imp contains a hyper virtual stack, and we want to compute
  the X,Y,Z translation between every time point in it
  using the given preferred channel. """
  t1_vs = extract_frame(imp, 1, channel)
  shifts = []
  # store the first shift: between t1 and t2
  shifts.append(Point3i(0, 0, 0))
  # append the rest:
  IJ.showProgress(0)
  i = 1
  for t in range(2, imp.getNFrames()+1):
    t2_vs = extract_frame(imp, t, channel)
    shift = compute_stitch(ImagePlus("1", t1_vs), ImagePlus("2", t2_vs))
    shifts.append(shift)
    t1_vs = t2_vs
    IJ.showProgress(i / float(imp.getNFrames()))
    i += 1
  IJ.showProgress(1)
  return shifts

def concatenate_shifts(shifts):
  """ Take the shifts, which are relative to the previous shift,
  and sum them up so that all of them are relative to the first."""
  # the first shift is 0,0,0
  for i in range(2, len(shifts)): # we start at the third
    s0 = shifts[i-1]
    s1 = shifts[i]
    s1.x += s0.x
    s1.y += s0.y
    s1.z += s0.z
  return shifts

def compute_min_max(shifts):
  """ Find out the top left up corner, and the right bottom down corner,
  namely the bounds of the new virtual stack to create.
  Expects absolute shifts. """
  minx = Integer.MAX_VALUE
  miny = Integer.MAX_VALUE
  minz = Integer.MAX_VALUE
  maxx = -Integer.MAX_VALUE
  maxy = -Integer.MAX_VALUE
  maxz = -Integer.MAX_VALUE
  for shift in shifts:
    minx = min(minx, shift.x)
    miny = min(miny, shift.y)
    minz = min(minz, shift.z)
    maxx = max(maxx, shift.x)
    maxy = max(maxy, shift.y)
    maxz = max(maxz, shift.z)
  
  return minx, miny, minz, maxx, maxy, maxz

def zero_pad(num, digits):
  """ for 34, 4 --> '0034' """
  str_num = str(num)
  while (len(str_num) < digits):
    str_num = '0' + str_num
  return str_num

def create_registered_hyperstack(imp, channel, target_folder, virtual):
  """ Takes the imp, determines the x,y,z drift for each pair of time points, using the preferred given channel,
  and outputs as a hyperstack."""
  shifts = compute_frame_translations(imp, channel)
  # Make shifts relative to 0,0,0 of the original imp:
  shifts = concatenate_shifts(shifts)
  print "shifts concatenated:"
  for s in shifts:
    print s.x, s.y, s.z
  # Compute bounds of the new volume,
  # which accounts for all translations:
  minx, miny, minz, maxx, maxy, maxz = compute_min_max(shifts)
  # Make shifts relative to new canvas dimensions
  # so that the min values become 0,0,0
  for shift in shifts:
    shift.x -= minx
    shift.y -= miny
    shift.z -= minz
  print "shifts relative to new dimensions:"
  for s in shifts:
    print s.x, s.y, s.z
  # new canvas dimensions:
  width = imp.width + maxx - minx
  height = maxy - miny + imp.height
  slices = maxz - minz + imp.getNSlices()

  print "New dimensions:", width, height, slices
  # Prepare empty slice to pad in Z when necessary
  empty = imp.getProcessor().createProcessor(width, height)

  # if it's RGB, fill the empty slice with blackness
  if isinstance(empty, ColorProcessor):
    empty.setValue(0)
    empty.fill()
  # Write all slices to files:
  stack = imp.getStack()

  if virtual is False:
  	registeredstack = ImageStack(width, height, imp.getProcessor().getColorModel())
  names = []
  for frame in range(1, imp.getNFrames()+1):
    shift = shifts[frame-1]
    fr = "t" + zero_pad(frame, len(str(imp.getNFrames())))
    # Pad with empty slices before reaching the first slice
    for s in range(shift.z):
      ss = "_z" + zero_pad(s + 1, len(str(slices))) # slices start at 1
      for ch in range(1, imp.getNChannels()+1):
        name = fr + ss + "_c" + zero_pad(ch, len(str(imp.getNChannels()))) +".tif"
        names.append(name)

        if virtual is True:
          currentslice = ImagePlus("", empty)
          currentslice.setCalibration(imp.getCalibration().copy())
          currentslice.setProperty("Info", imp.getProperty("Info"))
          FileSaver(currentslice).saveAsTiff(target_folder + "/" + name)
        else:
          empty = imp.getProcessor().createProcessor(width, height)
          registeredstack.addSlice(str(name), empty)
    # Add all proper slices
    stack = imp.getStack()
    for s in range(1, imp.getNSlices()+1):
      ss = "_z" + zero_pad(s + shift.z, len(str(slices)))
      for ch in range(1, imp.getNChannels()+1):
         ip = stack.getProcessor(imp.getStackIndex(ch, s, frame))
         ip2 = ip.createProcessor(width, height) # potentially larger
         ip2.insert(ip, shift.x, shift.y)
         name = fr + ss + "_c" + zero_pad(ch, len(str(imp.getNChannels()))) +".tif"
         names.append(name)

         if virtual is True:
           currentslice = ImagePlus("", ip2)
           currentslice.setCalibration(imp.getCalibration().copy())
           currentslice.setProperty("Info", imp.getProperty("Info"));
           FileSaver(currentslice).saveAsTiff(target_folder + "/" + name)
         else:
           registeredstack.addSlice(str(name), ip2)

    # Pad the end
    for s in range(shift.z + imp.getNSlices(), slices):
      ss = "_z" + zero_pad(s + 1, len(str(slices)))
      for ch in range(1, imp.getNChannels()+1):
        name = fr + ss + "_c" + zero_pad(ch, len(str(imp.getNChannels()))) +".tif"
        names.append(name)

        if virtual is True:
          currentslice = ImagePlus("", empty)
          currentslice.setCalibration(imp.getCalibration().copy())
          currentslice.setProperty("Info", imp.getProperty("Info"))
          FileSaver(currentslice).saveAsTiff(target_folder + "/" + name)
        else:
          registeredstack.addSlice(str(name), empty)

  if virtual is True:
      # Create virtual hyper stack with the result
      registeredstack = VirtualStack(width, height, None, target_folder)
      for name in names:
        registeredstack.addSlice(name)
      registeredstack_imp = ImagePlus("registered time points", registeredstack)
      registeredstack_imp.setDimensions(imp.getNChannels(), len(names) / (imp.getNChannels() * imp.getNFrames()), imp.getNFrames())
      registeredstack_imp.setCalibration(imp.getCalibration().copy())
      registeredstack_imp.setOpenAsHyperStack(True)

  else:
    registeredstack_imp = ImagePlus("registered time points", registeredstack)
    registeredstack_imp.setCalibration(imp.getCalibration().copy())
    registeredstack_imp.setProperty("Info", imp.getProperty("Info"))
    registeredstack_imp.setDimensions(imp.getNChannels(), len(names) / (imp.getNChannels() * imp.getNFrames()), imp.getNFrames())
    registeredstack_imp.setOpenAsHyperStack(True)
    if 1 == registeredstack_imp.getNChannels():
      return registeredstack_imp
  IJ.log("\nHyperstack dimensions: time frames:" + str(registeredstack_imp.getNFrames()) + ", slices: " + str(registeredstack_imp.getNSlices()) + ", channels: " + str(registeredstack_imp.getNChannels()))

  # Else, as composite
  mode = CompositeImage.COLOR;
  if isinstance(imp, CompositeImage):
    mode = imp.getMode()
  else:
    return registeredstack_imp
  return CompositeImage(registeredstack_imp, mode)

class Filter(FilenameFilter):
  def accept(self, folder, name):
    return not File(folder.getAbsolutePath() + "/" + name).isHidden()

def validate(target_folder):
  f = File(target_folder)
  if len(File(target_folder).list(Filter())) > 0:
    yn = YesNoCancelDialog(IJ.getInstance(), "Warning!", "Target folder is not empty! May overwrite files! Continue?")
    if yn.yesPressed():
      return True
    else:
      return False
  return True

def getOptions(imp):
  gd = GenericDialog("Correct 3D Drift Options")
  channels = []
  for ch in range(1, imp.getNChannels()+1 ):
    channels.append(str(ch))
  gd.addMessage("Select a channel to be used for the registration.")
  gd.addChoice("     channel:", channels, channels[0])
  gd.addCheckbox("Use virtualstack?", False)
  gd.addMessage("This will store the registered hyperstack as an image sequence and\nshould be used if free RAM is less than 2X the size of the hyperstack. ")
  gd.showDialog()
  if gd.wasCanceled():
    return
  channel = gd.getNextChoiceIndex() + 1  # zero-based
  virtual = gd.getNextBoolean()
  return channel, virtual

#Need function to get colors for each channel. Loop channels extracting color model and then apply to registered

def run():
  imp = IJ.getImage()
  if imp is None:
    return
  if not imp.isHyperStack():
    print "Not a hyper stack!"
    return
  if 1 == imp.getNFrames():
    print "There is only one time frame!"
    return
  if 1 == imp.getNSlices():
    print "To register slices of a stack, use 'Register Virtual Stack Slices'"
    return

  options = getOptions(imp)
  if options is not None:
    channel, virtual = options
    print "channel="+str(channel)+" virtual="+str(virtual)
  if virtual is True:
    dc = DirectoryChooser("Choose target folder to save image sequence")
    target_folder = dc.getDirectory()
    if target_folder is None:
      return # user canceled the dialog
    if not validate(target_folder):
      return
  else:
    target_folder = None 

  registered_imp= create_registered_hyperstack(imp, channel, target_folder, virtual)
  if virtual is True:
    if 1 == imp.getNChannels():
      ip=imp.getProcessor()
      ip2=registered_imp.getProcessor()
      ip2.setColorModel(ip.getCurrentColorModel())
      registered_imp.show()
    else:
    	registered_imp.copyLuts(imp)
    	registered_imp.show()
  else:
    if 1 ==imp.getNChannels():
    	registered_imp.show()
    else:
    	registered_imp.copyLuts(imp)
    	registered_imp.show()
  
  registered_imp.show()

run()
########NEW FILE########
__FILENAME__ = Record_Desktop
# Take a snapshot of the desktop every X miliseconds,
# and then make a stack out of it.
# Limited by RAM for speed, this plugin is intended
# for short recordings.

import thread
import time

from java.awt import Robot, Rectangle

def run(title):
	gd = GenericDialog('Record Desktop')
	gd.addNumericField('Max. frames:', 50, 0)
	gd.addNumericField('Milisecond interval:', 300, 0)
	gd.addSlider('Start in (seconds):', 0, 20, 5)
	gd.showDialog()
	if gd.wasCanceled():
		return
	n_frames = int(gd.getNextNumber())
	interval = gd.getNextNumber() / 1000.0 # in seconds
	delay = int(gd.getNextNumber())
	
	snaps = []

	try:
		while delay > 0:
			IJ.showStatus('Starting in ' + str(delay) + 's.')
			time.sleep(1) # one second
			delay -= 1
		IJ.showStatus('')
		System.out.println("Starting...")
		# start capturing
		robot = Robot()
		box = Rectangle(IJ.getScreenSize())
		start = System.currentTimeMillis() / 1000.0 # in seconds
		last = start
		intervals = []
		real_interval = 0
		# Initial shot
		snaps.append(robot.createScreenCapture(box))
		while len(snaps) < n_frames and last - start < n_frames * interval:
			now = System.currentTimeMillis() / 1000.0 # in seconds
			real_interval = now - last
			if real_interval >= interval:
				last = now
				snaps.append(robot.createScreenCapture(box))
				intervals.append(real_interval)
			else:
				time.sleep(interval / 5) # time in seconds
		# Create stack
		System.out.println("End")
		awt = snaps[0]
		stack = ImageStack(awt.getWidth(None), awt.getHeight(None), None)
		t = 0
		for snap,real_interval in zip(snaps,intervals):
			stack.addSlice(str(IJ.d2s(t, 3)), ImagePlus('', snap).getProcessor())
			snap.flush()
			t += real_interval

		ImagePlus("Desktop recording", stack).show()
	except Exception, e:
		print "Some error ocurred:"
		print e
		for snap in snaps: snap.flush()

thread.start_new_thread(run, ("Do it",))

########NEW FILE########
__FILENAME__ = Record_Window
# Albert Cardona 20090418.
# Released under the General Public License v2.0
#
# Take snapshots of a user-specified window over time,
# and then make an image stack of of them all.
# 
# In the dialog, 0 frames mean infinite recording, to be interrupted by ESC
# pressed on the ImageJ toolbar or other frames with the same listener.
# 
# If not saving to file, then you are limited to RAM.
#
# When done, a stack or a virtual stack opens.

import thread
import time
import sys

from java.awt import Robot, Rectangle, Frame
from java.awt.image import BufferedImage
from javax.swing import SwingUtilities
from java.io import File, FilenameFilter
from java.util.concurrent import Executors
from java.util import Arrays

class PrintAll(Runnable):
	def __init__(self, frame, g):
		self.frame = frame
		self.g = g
	def run(self):
		self.frame.printAll(self.g)

def snapshot(frame, box):
	bi = BufferedImage(box.width, box.height, BufferedImage.TYPE_INT_RGB)
	g = bi.createGraphics()
	g.translate(-box.x, -box.y)
	#all black! # frame.paintAll(g)
	#only swing components! # frame.paint(g)
	#only swing components! # frame.update(g)
	#together, also only swing and with errors
	##frame.update(g)
	##frame.paint(g)
	# locks the entire graphics machinery # frame.printAll(g)
	# Finally, the right one:
	SwingUtilities.invokeAndWait(PrintAll(frame, g))
	return bi

class Saver(Runnable):
	def __init__(self, i, dir, bounds, borders, img, insets):
		self.i = i
		self.dir = dir
		self.bounds = bounds
		self.borders = borders
		self.img = img
		self.insets = insets
	def run(self):
		System.out.println("run")
		# zero-pad up to 10 digits
		bi = None
		try:
			title = str(self.i)
			while len(title) < 10:
				title = '0' + title
			bi = BufferedImage(self.bounds.width, self.bounds.height, BufferedImage.TYPE_INT_RGB)
			g = bi.createGraphics()
			g.drawImage(self.borders, 0, 0, None)
			g.drawImage(self.img, self.insets.left, self.insets.top, None)
			FileSaver(ImagePlus(title, ColorProcessor(bi))).saveAsTiff(self.dir + title + '.tif')
		except Exception, e:
			print e
			e.printStackTrace()
		if bi is not None: bi.flush()
		self.img.flush()

class TifFilter(FilenameFilter):
	def accept(self, dir, name):
		return name.endswith('.tif')

def run(title):
	gd = GenericDialog('Record Window')
	gd.addMessage("Maximum number of frames to record.\nZero means infinite, interrupt with ESC key.")
	gd.addNumericField('Max. frames:', 50, 0)
	gd.addNumericField('Milisecond interval:', 300, 0)
	gd.addSlider('Start in (seconds):', 0, 20, 5)
	frames = []
	titles = []
	for f in Frame.getFrames():
		if f.isEnabled() and f.isVisible():
			frames.append(f)
			titles.append(f.getTitle())
	gd.addChoice('Window:', titles, titles[0])
	gd.addCheckbox("To file", False)
	gd.showDialog()
	if gd.wasCanceled():
		return
	n_frames = int(gd.getNextNumber())
	interval = gd.getNextNumber() / 1000.0 # in seconds
	frame = frames[gd.getNextChoiceIndex()]
	delay = int(gd.getNextNumber())
	tofile = gd.getNextBoolean()

	dir = None
	if tofile:
		dc = DirectoryChooser("Directory to store image frames")
		dir = dc.getDirectory()
		if dir is None:
			return # dialog canceled

	snaps = []
	borders = None
	executors = Executors.newFixedThreadPool(1)
	try:
		while delay > 0:
			IJ.showStatus('Starting in ' + str(delay) + 's.')
			time.sleep(1) # one second
			delay -= 1

		IJ.showStatus('Capturing frame borders...')
		bounds = frame.getBounds()
		robot = Robot()
		frame.toFront()
		time.sleep(0.5) # half a second
		borders = robot.createScreenCapture(bounds)

		IJ.showStatus("Recording " + frame.getTitle())

		# Set box to the inside borders of the frame
		insets = frame.getInsets()
		box = bounds.clone()
		box.x = insets.left
		box.y = insets.top
		box.width -= insets.left + insets.right
		box.height -= insets.top + insets.bottom

		start = System.currentTimeMillis() / 1000.0 # in seconds
		last = start
		intervals = []
		real_interval = 0
		i = 1
		fus = None
		if tofile:
			fus = []

		# 0 n_frames means continuous acquisition
		while 0 == n_frames or (len(snaps) < n_frames and last - start < n_frames * interval):
			now = System.currentTimeMillis() / 1000.0   # in seconds
			real_interval = now - last
			if real_interval >= interval:
				last = now
				img = snapshot(frame, box)
				if tofile:
					fus.append(executors.submit(Saver(i, dir, bounds, borders, img, insets))) # will flush img
					i += 1
				else:
					snaps.append(img)
				intervals.append(real_interval)
			else:
				time.sleep(interval / 5)
			# interrupt capturing:
			if IJ.escapePressed():
				IJ.showStatus("Recording user-interrupted")
				break

		# debug:
		#print "insets:", insets
		#print "bounds:", bounds
		#print "box:", box
		#print "snap dimensions:", snaps[0].getWidth(), snaps[0].getHeight()

		# Create stack
		stack = None;
		if tofile:
			for fu in snaps: fu.get() # wait on all
			stack = VirtualStack(bounds.width, bounds.height, None, dir)
			files = File(dir).list(TifFilter())
			Arrays.sort(files)
			for f in files:
				stack.addSlice(f)
		else:
			stack = ImageStack(bounds.width, bounds.height, None)
			t = 0
			for snap,real_interval in zip(snaps,intervals):
				bi = BufferedImage(bounds.width, bounds.height, BufferedImage.TYPE_INT_RGB)
				g = bi.createGraphics()
				g.drawImage(borders, 0, 0, None)
				g.drawImage(snap, insets.left, insets.top, None)
				stack.addSlice(str(IJ.d2s(t, 3)), ImagePlus('', bi).getProcessor())
				t += real_interval
				snap.flush()
				bi.flush()

		borders.flush()

		ImagePlus(frame.getTitle() + " recording", stack).show()
		IJ.showStatus('Done recording ' + frame.getTitle())
	except Exception, e:
		print "Some error ocurred:"
		print e.printStackTrace()
		IJ.showStatus('')
		if borders is not None: borders.flush()
		for snap in snaps: snap.flush()
	
	executors.shutdown()

thread.start_new_thread(run, ("Do it",))


########NEW FILE########
__FILENAME__ = 3d
#!/bin/sh
''''exec "$(dirname "$0")"/../ImageJ --jython "$0" "$@" # (call again with fiji)'''

from ij import IJ, ImageJ

import lib

lib.startIJ()
lib.test(lambda: IJ.run("Fiji Logo 3D"))
lib.waitForWindow("ImageJ 3D Viewer")
lib.quitIJ()

########NEW FILE########
__FILENAME__ = class_versions
#!/bin/sh
''''exec "$(dirname "$0")"/../ImageJ --jython "$0" "$@" # (call again with fiji)'''


from fiji import CheckClassVersions

from java.lang import System

ij_dir = System.getProperty('ij.dir') + '/'

dirs = ['plugins/', 'jars/', 'misc/', 'precompiled/']
dirs = [ij_dir + dir for dir in dirs]

CheckClassVersions().main(dirs)

########NEW FILE########
__FILENAME__ = crlf-in-javas
#!/bin/sh
''''exec "$(dirname "$0")"/../ImageJ --jython "$0" "$@" # (call again with fiji)'''


from java.io import BufferedReader, InputStreamReader

from java.lang import Runtime, System

import os, sys

def check_text(lines_array):
	for line in lines_array:
		if line.endswith("\r"):
			return False
	return True

def check_file(path):
	f = open(path, 'r')
	if not check_text(f.readlines()):
		f.close()
		print 'CR/LF detected in', path
		return
	f.close()

def check_directory(dir):
	for item in os.listdir(dir):
		path = dir + '/' + item
		if item.endswith('.java'):
                        check_file(path)
                elif os.path.isdir(path):
                        check_directory(path)

def execute(cmd):
	runtime = Runtime.getRuntime()
	p = runtime.exec(cmd)
	p.outputStream.close()
	result = ""
	reader = BufferedReader(InputStreamReader(p.inputStream))
	errorReader = BufferedReader(InputStreamReader(p.errorStream))
	while True:
		if p.errorStream.available() > 0:
			print errorReader.readLine()
		line=reader.readLine()
		if line == None:
			break
		result+=line + "\n"
	while True:
		line = errorReader.readLine()
		if line == None:
			break
		print line
	p.waitFor()
	if p.exitValue() != 0:
		print result
		raise RuntimeError, 'execution failure'
	return result

def check_in_HEAD(path):
	if not check_text(execute('git show HEAD:' + path).split("\n")):
		print 'CR/LF detected in', path

def check_HEAD():
	for line in execute('git ls-tree -r HEAD').split("\n"):
		if line == '':
			continue
		path = line.split("\t")[1]
		if path.endswith('.java'):
			check_in_HEAD(path)

ij_dir = System.getProperty('ij.dir') + '/src-plugins'

if sys.argv[0] == 'worktree':
	check_directory(ij_dir)
else:
	check_HEAD()

########NEW FILE########
__FILENAME__ = extra_file_types
#!/bin/sh
''''exec "$(dirname "$0")"/../ImageJ --jython "$0" "$@" # (call again with fiji)'''

# Test whether HandleExtraFileTypes.java tryPlugIn(<classname>) calls
# will succeed, by testing if the class is in the classpath or in the plugins folder.

from ij import IJ, ImageJ, Prefs
from java.lang import Class, ClassNotFoundException, System, NoClassDefFoundError

# Launch ImageJ
ImageJ()
print "Testing HandleExtraFileTypes.java:"

# Try both system and IJ class loaders
def checkClassName(name):
  try:
    cl = Class.forName(name)
    return 1
  except ClassNotFoundException:
    try:
      cl = IJ.getClassLoader().loadClass(name)
      print "found :", cl
      return 1
    except NoClassDefFoundError:
      return 0
    except ClassNotFoundException:
      return 0

path = System.getProperty('ij.dir') + '/' + "src-plugins/IO_/"
print "path: ", path
f = open(path + "HandleExtraFileTypes.java")

error = 0

try:
  count = 0
  for line in f.readlines():
    count += 1
    #if not 'tryPlugIn' in line: continue
    itp = line.find('tryPlugIn')
    if -1 == itp: continue
    istart = line.find('"', itp + 8)
    if -1 == istart: continue
    istart += 1
    iend = line.find('"', istart)
    if -1 == iend:
      print 'Unclosed colon at line ', str(count), ':', line.strip()
      continue
    name = line[istart:iend]
    if not checkClassName(name):
      print 'Class not found: ', name, 'at line', str(count), ':', line.strip()
      error = 1
except error:
  print error
  print "Some error ocurred while parsing HandleExtraFileTypes.java"
  error = 1

f.close()

if not error:
  print 'ok - All classes in tryPlugIn(<classname>) in HandleExtraFileTypes exist'

System.exit(0)

########NEW FILE########
__FILENAME__ = lib
# This is a small library of function which should make testing Fiji/ImageJ
# much easier.

from jarray import zeros
from threading import Lock
from sys import exit, stderr
from os.path import realpath

from fiji import Main
from ij import IJ, ImageJ
from java.awt import Button, Container, Dialog, Frame, Toolkit
from java.awt.event import ActionEvent, MouseEvent
from java.io import File
from java.lang import Runtime, System, Thread

currentWindow = None
def startIJ():
	Main.premain()
	global currentWindow
	currentWindow = ImageJ()
	currentWindow.exitWhenQuitting(True)
	Main.postmain()

def catchIJErrors(function):
	try:
		IJ.redirectErrorMessages()
		return function()
	except:
		logWindow = WindowManager.getFrame("Log")
		if not logWindow is None:
			error_message = logWindow.getTextPanel().getText()
			logWindow.close()
			return error_message

def test(function):
	result = catchIJErrors(function)
	if not result == None:
		print 'Failed:', function
		exit(1)

def waitForWindow(title):
	global currentWindow
	currentWindow = Main.waitForWindow(title)
	return currentWindow

def getMenuEntry(menuBar, path):
	if menuBar == None:
		global currentWindow
		menuBar = currentWindow.getMenuBar()
	if isinstance(path, str):
		path = path.split('>')
	try:
		menu = None
		for i in range(0, menuBar.getMenuCount()):
			if path[0] == menuBar.getMenu(i).getLabel():
				menu = menuBar.getMenu(i)
				break
		for j in range(1, len(path)):
			entry = None
			for i in range(0, menu.getItemCount()):
				if path[j] == menu.getItem(i).getLabel():
					entry = menu.getItem(i)
					break
			menu = entry
		return menu
	except:
		return None

def dispatchActionEvent(component):
	event = ActionEvent(component, ActionEvent.ACTION_PERFORMED, \
		component.getLabel(), MouseEvent.BUTTON1)
	component.dispatchEvent(event)

def clickMenuItem(path):
	menuEntry = getMenuEntry(None, path)
	dispatchActionEvent(menuEntry)

def getButton(container, label):
	if container == None:
		global currentWindow
		container = currentWindow
	components = container.getComponents()
	for i in range(0, len(components)):
		if isinstance(components[i], Container):
			result = getButton(components[i], label)
			if result != None:
				return result
		elif isinstance(components[i], Button) and \
				components[i].getLabel() == label:
			return components[i]

def clickButton(label):
	button = getButton(None, label)
	dispatchActionEvent(button)

def quitIJ():
	global currentWindow
	IJ.getInstance().quit()
	currentWindow = None

class OutputThread(Thread):
	def __init__(self, input, output):
		self.buffer = zeros(65536, 'b')
		self.input = input
		self.output = output

	def run(self):
		while True:
			count = self.input.read(self.buffer)
			if count < 0:
				return
			self.output.write(self.buffer, 0, count)

def launchProgramNoWait(args, workingDir = None):
	if workingDir != None and not isinstance(workingDir, File):
		workingDir = File(workingDir)
	process = Runtime.getRuntime().exec(args, None, workingDir)
	OutputThread(process.getInputStream(), System.out).start()
	OutputThread(process.getErrorStream(), System.err).start()
	return process

def launchProgram(args, workingDir = None):
	process = launchProgramNoWait(args, workingDir)
	return process.waitFor()

def launchFiji(args, workingDir = None):
	args.insert(0, realpath(System.getProperty('ij.executable')))
	try:
		launchProgram(args, workingDir)
	except:
		return -1

########NEW FILE########
__FILENAME__ = menus
#!/bin/sh
''''exec "$(dirname "$0")"/../ImageJ --jython "$0" "$@" # (call again with fiji)'''

# Test that ImageJ(A) can add to any menu, and that the result is
# appropriately separated by a separator, and sorted alphabetically.

from ij import IJ, ImageJ, Menus, Prefs, WindowManager

from java.awt import Menu, MenuBar
from java.lang import System
from java.io import FileOutputStream
from java.util.zip import ZipOutputStream, ZipEntry

import os

# make a temporary directory, and put two fake .jar files in it

# Warning: Jython does not support removedirs() yet
def removedirs(dir):
	os.system('rm -rf ' + dir)

temporary_folder = 'tests/plugins'
removedirs(temporary_folder)
os.makedirs(temporary_folder)

def fake_plugin_jar(name, plugins_config):
	output = FileOutputStream(name)
	zip = ZipOutputStream(output)
	entry = ZipEntry('plugins.config')
	zip.putNextEntry(entry)
	zip.write(plugins_config)
	zip.closeEntry()
	zip.close()

def fake_plugin_class(name):
	slash = name.rfind('/')
	if slash > 0 and not os.path.isdir(name[:slash]):
		os.makedirs(name[:slash])
	f = open(name + '.class', 'w')
	f.write('Invalid class')
	f.close()

def update_menus():
	try:
		IJ.redirectErrorMessages()
		IJ.run('Update Menus')
	except:
		error_message = 'Error updating menus'
		logWindow = WindowManager.getFrame("Log")
		if not logWindow is None:
			error_message = error_message + ': ' \
				+ logWindow.getTextPanel().getText()
			logWindow.close()
		print error_message
		global error
		error += 1

fake_plugin_jar(temporary_folder + '/test_.jar',
	'Image>Color>Hello, "Cello", Cello')
fake_plugin_jar(temporary_folder + '/test_2.jar',
	'Image>Color>Hello, "Bello", Bello' + "\n" +
	'Image>Color>Hello, "Allo", Bello' + "\n" +
	'Plugins>bla>blub>, "Eldo", Rado' + "\n" +
	'Plugins>bla>blub>, "Bubble", Rado' + "\n" +
	'Plugins, "Cello", xyz' + "\n" +
	'Plugins, "Abracadabra", abc')

# reset the plugins folder to the temporary directory

System.setProperty('plugins.dir', temporary_folder);

# Launch ImageJ

IJ.redirectErrorMessages()
ij = ImageJ()
error = 0

# Must show Duplicate command error

logWindow = WindowManager.getFrame("Log")
if logWindow is None:
	print 'No error adding duplicate entries'
	error += 1
else:
	logText = logWindow.getTextPanel().getText()
	if not 'Duplicate command' in logText:
		print 'Error adding duplicate entries, but the wrong one'
		error += 1
	logWindow.close()

# debug functions

def printMenu(menu, indent):
	n = menu.getItemCount()
	for i in range(0, n):
		item = menu.getItem(i)
		print indent, item.getLabel()
		if isinstance(item, Menu):
			printMenu(item, indent + '    ')

def printAllMenus():
	mbar = Menus.getMenuBar()
	n = mbar.getMenuCount()
	for i in range(0, n):
		menu = mbar.getMenu(i)
		print menu.getLabel()
		printMenu(menu, '    ')
	print 'Help'
	printMenu(mbar.getHelpMenu(), '    ')

# make sure that something was inserted into Image>Color

def getMenuEntry(path):
	if isinstance(path, str):
		path = path.split('>')
	try:
		menu = None
		mbar = Menus.getMenuBar()
		for i in range(0, mbar.getMenuCount()):
			if path[0] == mbar.getMenu(i).getLabel():
				menu = mbar.getMenu(i)
				break
		for j in range(1, len(path)):
			entry = None
			for i in range(0, menu.getItemCount()):
				if path[j] == menu.getItem(i).getLabel():
					entry = menu.getItem(i)
					break
			menu = entry
		return menu
	except:
		return None

if getMenuEntry('Image>Color>Hello>Bello') is None:
	print 'Bello was not inserted at all'
	error += 1

# make sure that added submenus are sorted

def isSorted(path, onlyAfterSeparator):
	menu = getMenuEntry(path)
	if menu is None:
		return False
	for i in range(0, menu.getItemCount() - 1):
		if onlyAfterSeparator:
			if menu.getItem(i).getLabel() == '-':
				onlyAfterSeparator = False
			continue
		if menu.getItem(i).getLabel() > menu.getItem(i + 1).getLabel():
			return False
	return True

if isSorted('Image>Color>Hello', False):
	print 'Image>Color>Hello was sorted'
	error += 1

if not isSorted('Plugins', True):
	print 'Plugins was not sorted'
	error += 1

if not isSorted('Plugins>bla>blub', True):
	print 'Plugins>bla>blub was not sorted'
	error += 1

os.remove(temporary_folder + '/test_2.jar')
fake_plugin_jar(temporary_folder + '/test_3.jar',
	'Image>Color>Hello, "Zuerich", Zuerich')

update_menus()

if not getMenuEntry('Image>Color>Hello>Bello') is None:
	print 'Update Menus kept Bello'
	error += 1

if getMenuEntry('Image>Color>Hello>Zuerich') is None:
	print 'Update Menus did not insert Zuerich'
	error += 1

# Test isolated classes

fake_plugin_class(temporary_folder + '/Some_Isolated_Class')
fake_plugin_class(temporary_folder + '/Another/Isolated_Class')
Prefs.moveToMisc = True

update_menus()

if getMenuEntry('Plugins>Some Isolated Class') is None:
	print 'Isolated class not put into toplevel'
	error += 1

if not getMenuEntry('Plugins>Another>Isolated Class') is None:
	print 'Isolated class in subdirectory put into toplevel'
	error += 1

if getMenuEntry('Plugins>Miscellaneous>Isolated Class') is None:
	print 'Isolated class in subdirectory not put into misc menu'
	error += 1

# Test that 'Quit' is always last item in the File menu

fake_plugin_jar(temporary_folder + '/test_4.jar',
	'File, "Something", Wuerzburg')

update_menus()

if getMenuEntry('File>Something') is None:
	print 'File>Something is missing'
	error += 1

file = getMenuEntry('File')
if file is None:
	print 'Huh? File menu is missing!'
	error += 1
elif file.getItem(file.getItemCount() - 1).getLabel() != 'Quit':
	print 'Last item in File menu is not Quit!'
	error += 1

ij.exitWhenQuitting(True)
ij.quit()

########NEW FILE########
__FILENAME__ = plugin_jars
#!/bin/sh
''''exec "$(dirname "$0")"/../ImageJ --jython "$0" "$@" # (call again with fiji)'''

# Test whether any menu items contain pointers to non-existent classes which
# likely indicate a missconfiguration of a plugins.config file in a .jar plugin.

from ij import IJ, ImageJ, Menus

from java.lang import Class, ClassNotFoundException, NoClassDefFoundError

import sys

# Launch ImageJ
ImageJ()

if len(sys.argv) > 1 and sys.argv[1] == '-v':
	for key in Menus.getCommands():
		command = Menus.getCommands().get(key)
		print key, '->', command
	sys.exit()

ok = 1

def doesClassExist(name):
	try:
		IJ.getClassLoader().loadClass(name)
		return True
	except ClassNotFoundException:
		return False
	except NoClassDefFoundError:
		return False

# Inspect each menu command
for it in Menus.getCommands().entrySet().iterator():
	name = it.value
	paren = name.find('(')
	if -1 != paren:
		name = name[:paren]

	if not doesClassExist(name):
		# Try without the first package name, since it may be fake
		# for plugins in subfolders of the plugins directory:
		dot = name.find('.')
		if -1 == dot or not doesClassExist(name[dot+1:]):
			print 'ERROR: Class not found for menu command:', \
				it.key, '=>', it.value, \
				'in:', Menus.getJarFileForMenuEntry(it.key)
			ok = 0

if ok:
	print "ok - Menu commands all correct."
	sys.exit(0)

sys.exit(1)

########NEW FILE########
__FILENAME__ = record
#!/bin/sh
''''exec "$(dirname "$0")"/../ImageJ --jython "$0" "$@" # (call again with fiji)'''

import lib
from java.awt import AWTEvent, Button, Dialog, Frame, Menu, MenuBar, MenuItem
from java.awt import Toolkit, Window
from java.awt.event import AWTEventListener
from java.awt.event import ActionEvent, ContainerEvent, ComponentEvent
from java.awt.event import FocusEvent
from java.awt.event import HierarchyEvent, InputMethodEvent, MouseEvent
from java.awt.event import PaintEvent, WindowEvent

verbose = False

lib.startIJ()

def record(function, argument):
	print 'lib.' + function + "('" + argument + "')"

def getMenuPath(menuItem):
	result = ''
	while not isinstance(menuItem, MenuBar):
		if result != '':
			result = '>' + result
		result = menuItem.getLabel() + result
		menuItem = menuItem.getParent()
	if isinstance(menuItem.getParent(), Frame):
		record('waitForWindow', menuItem.getParent().getTitle())
	record('clickMenuItem', result)

def getButton(button):
	label = button.getLabel()
	while button != None:
		if isinstance(button, Frame) or isinstance(button, Dialog):
			record('waitForWindow', button.getTitle())
			break
		button = button.getParent()
	record('clickButton', label)

class Listener(AWTEventListener):
	def eventDispatched(self, event):
		if isinstance(event, ContainerEvent) or \
				isinstance(event, HierarchyEvent) or \
				isinstance(event, InputMethodEvent) or \
				isinstance(event, MouseEvent) or \
				isinstance(event, PaintEvent):
			return
		if isinstance(event, ActionEvent):
			if isinstance(event.getSource(), MenuItem):
				getMenuPath(event.getSource())
			elif isinstance(event.getSource(), Button):
				getButton(event.getSource())
			else:
				print 'Unknown action event:', event
		elif (event.getID() == FocusEvent.FOCUS_GAINED and \
				    isinstance(event, Window)) or \
				event.getID() == WindowEvent.WINDOW_OPENED:
			record('waitForWindow', event.getSource().getTitle())
		else:
			global verbose
			if verbose:
				print 'event', event, 'from source', \
					event.getSource()

listener = Listener()
Toolkit.getDefaultToolkit().addAWTEventListener(listener, -1)

print 'import lib'
print ''
print 'lib.startIJ()'

########NEW FILE########
__FILENAME__ = vib
#!/bin/sh
''''exec "$(dirname "$0")"/../ImageJ --jython "$0" "$@" # (call again with fiji)'''

from java.io import File

from java.lang import System

import lib, sys, os, errno, urllib
from os.path import realpath

ij_dir = System.getProperty('ij.dir')
images_dir = os.path.join(ij_dir, 'tests', 'sample-data')

# Ensure that the sample-data directory exists:
try:
	os.mkdir(images_dir)
except OSError, e:
	if e.errno != errno.EEXIST:
		raise

# Download any required test images that are missing:
for filename in (
		'CantonF41c-reduced.tif.points.xml',
		'CantonF41c-reduced.tif',
		'tidied-mhl-62yxUAS-lacZ0-reduced.tif.points.R',
		'tidied-mhl-62yxUAS-lacZ0-reduced.tif',
		'tidied-mhl-62yxUAS-lacZ0-reduced.tif',
		'71yAAeastmost.labels.points',
		'71yAAeastmost.labels',
		'c005BA.labels',
		'181y-12bit-aaarrg-dark-detail-reduced.tif',
		'181y-12bit-aaarrg-mid-detail-reduced.tif',
		'181y-12bit-aaarrg-bright-reduced.tif',
		'tidied-mhl-62yxUAS-lacZ0-reduced.tif.points.R',
		'c061AG-small-section-z-max.tif',
		'c061AG-small-section.tif'):
	destination = os.path.join(images_dir, filename)
	url = 'http://fiji.sc/test-data/' + urllib.quote(filename)
	if not os.path.exists(destination):
		print 'Downloading', filename
		urllib.urlretrieve(url, destination)

if realpath(os.getcwd()) != realpath(ij_dir):
    print >> sys.stderr, "The tests must be run from", realpath(ij_dir)
    sys.exit(1)

from org.junit.runner import JUnitCore

JUnitCore.main(['math3d.TestEigenvalueDecompositions', \
               'distance.TestMutualInformation', \
               'distance.TestEuclidean', \
               'distance.TestCorrelation', \
               'landmarks.TestLoading', \
               'util.TestPenalty', \
               'vib.TestFastMatrix', \
               'tracing.Test2DTracing', \
               'tracing.Test3DTracing'])

########NEW FILE########
