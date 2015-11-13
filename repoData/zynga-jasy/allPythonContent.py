__FILENAME__ = ImageInfo
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

import struct, hashlib

import jasy.core.Console as Console

"""
Contains image format detection classes. Once the format is detect it supports image size detection, too.
"""

class ImgFile(object):
    """Abstract base class for all image types"""

    def __init__(self, filename):
        try:
            self.fp = open(filename, "rb")
        except IOError as err:
            Console.error("Could not open file: %s" % filename)
            raise err

    def verify(self):
        raise NotImplementedError("%s: %s" % (self.__class__, "verify()"))

    def type(self):
        raise NotImplementedError("%s: %s" % (self.__class__, "type()"))

    def size(self):
        raise NotImplementedError("%s: %s" % (self.__class__, "size()"))

    def close(self):
        self.fp.close()

    def getChecksum(self):

        self.fp.seek(0)
        m = hashlib.md5()
        m.update(self.fp.read())

        return m.hexdigest()

    def __del__(self):
        self.close()


# http://www.w3.org/Graphics/GIF/spec-gif89a.txt
class GifFile(ImgFile):
    """Class for parsing GIF files"""

    def verify(self):
        self.fp.seek(0)
        header = self.fp.read(6)
        signature = struct.unpack("3s3s", header[:6])
        isGif = signature[0] == b"GIF" and signature[1] in [b"87a", b"89a"]
        return isGif

    def type(self):
        return "gif"

    def size(self):
        self.fp.seek(0)
        header = self.fp.read(6+6)
        (width, height) = struct.unpack("<HH", header[6:10])
        return width, height


# http://www.libmng.com/pub/png/spec/1.2/png-1.2-pdg.html#Structure
class PngFile(ImgFile):
    """Class for parsing PNG files"""
    
    def type(self):
        return "png"

    def verify(self):
        self.fp.seek(0)
        header = self.fp.read(8)
        signature = struct.pack("8B", 137, 80, 78, 71, 13, 10, 26, 10)
        isPng = header[:8] == signature
        return isPng

    def size(self):
        self.fp.seek(0)
        header = self.fp.read(8+4+4+13+4)
        ihdr = struct.unpack("!I4s", header[8:16])
        data = struct.unpack("!II5B", header[16:29])
        (width, height, bitDepth, colorType, compressionMethod, filterMethod, interleaceMethod) = data
        return (width, height)


# http://www.obrador.com/essentialjpeg/HeaderInfo.htm
class JpegFile(ImgFile):
    def verify(self):
        self.fp.seek(0)
        signature = struct.unpack("!H", self.fp.read(2))
        isJpeg = signature[0] == 0xFFD8
        return isJpeg

    def type(self):
        return "jpeg"

    def size(self):
        self.fp.seek(0)

        self.fp.read(2)

        b = self.fp.read(1)
        try:
            while (b and ord(b) != 0xDA):
                while (ord(b) != 0xFF): b = self.fp.read(1)
                while (ord(b) == 0xFF): b = self.fp.read(1)
                if (ord(b) >= 0xC0 and ord(b) <= 0xC3):
                    self.fp.read(3)
                    h, w = struct.unpack(">HH", self.fp.read(4))
                    break
                else:
                    self.fp.read(int(struct.unpack(">H", self.fp.read(2))[0])-2)
                b = self.fp.read(1)
            width = int(w)
            height = int(h)
            
            return (width, height)
        except struct.error:
            pass
        except ValueError:
            pass
            

class ImgInfo(object):
    def __init__(self, filename):
        self.__filename = filename

    classes = [PngFile, GifFile, JpegFile]

    def getSize(self):
        """
        Returns the image sizes of png, gif and jpeg files as
        (width, height) tuple
        """
        
        filename = self.__filename
        classes = self.classes

        for cls in classes:
            img = cls(filename)
            if img.verify():
                size = img.size()
                if size is not None:
                    img.close()
                    return size
            img.close()

        return None
    
    def getInfo(self):
        ''' Returns (width, height, "type") of the image'''
        filename = self.__filename
        classes = self.classes
        
        for cls in classes:
            img = cls(filename)
            if img.verify():
                return (img.size()[0], img.size()[1], img.type())

        return None

    def getChecksum(self):

        img = ImgFile(self.__filename)
        checksum = img.getChecksum()
        img.close()

        return checksum


########NEW FILE########
__FILENAME__ = Manager
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

import re, json, os, fnmatch

import jasy.core.File
import jasy.item.Asset

from jasy import UserError
import jasy.core.Console as Console

__all__ = ["AssetManager"]


class AssetManager:
    """
    Manages assets aka images, styles and other files required for a web application.
    
    Supports filtering assets based on a given class list (with optional permutation) to
    only include and copy assets which are needed by the current implementation. This is 
    especially useful when only parts of dependend projects are actually used.
    
    Merges assets with the same name from different projects. But normally each project
    creates it's own sandbox namespace so this has not often any effect at all.
    
    Supports images and automatically detect their size and image format. Both informations
    are added to the exported data later on.
    """
    
    def __init__(self, session):

        Console.info("Initializing assets...")
        Console.indent()

        # Store session reference (one asset manager per session)
        self.__session = session

        # Stores manager contextual asset information (like relative paths)
        self.__data = {}
        
        # Registry for profiles aka asset groups
        self.__profiles = []
        
        # Loop though all projects and merge assets
        assets = self.__assets = {}
        for project in self.__session.getProjects():
            assets.update(project.getAssets())
        
        self.__processSprites()
        self.__processAnimations()
        
        Console.outdent()
        Console.info("Activated %s assets", len(assets))


    def __processSprites(self):
        """Processes jasysprite.json files to merge sprite data into asset registry"""
        
        assets = self.__assets
        configs = [fileId for fileId in assets if assets[fileId].isImageSpriteConfig()]
        
        if configs:
            Console.info("Processing %s image sprite configs...", len(configs))
        
        sprites = []
        Console.indent()
        for fileId in configs:
            Console.debug("Processing %s...", fileId)
            
            asset = assets[fileId]
            spriteBase = os.path.dirname(fileId)
                
            try:
                spriteConfig = asset.getParsedObject();
            except ValueError as err:
                raise UserError("Could not parse jasysprite.json at %s: %s" % (fileId, err))
                
            Console.indent()
            for spriteImage in spriteConfig:
                spriteImageId = "%s/%s" % (spriteBase, spriteImage)
                
                singleRelPaths = spriteConfig[spriteImage]
                Console.debug("Image %s combines %s images", spriteImageId, len(singleRelPaths))

                for singleRelPath in singleRelPaths:
                    singleId = "%s/%s" % (spriteBase, singleRelPath)
                    singleData = singleRelPaths[singleRelPath]

                    if singleId in assets:
                        singleAsset = assets[singleId]
                    else:
                        Console.info("Creating new asset: %s", singleId)
                        singleAsset = jasy.item.Asset.AssetItem(None)
                        assets[singleId] = singleAsset
                        
                    if not spriteImageId in sprites:
                        spriteImageIndex = len(sprites) 
                        sprites.append(spriteImageId)
                    else:
                        spriteImageIndex = sprites.index(spriteImageId)
                        
                    singleAsset.addImageSpriteData(spriteImageIndex, singleData["left"], singleData["top"])
                    
                    if "width" in singleData and "height" in singleData:
                        singleAsset.addImageDimensionData(singleData["width"], singleData["height"])
                    
                    # Verify that sprite sheet is up-to-date
                    if "checksum" in singleData:
                        fileChecksum = singleAsset.getChecksum()
                        storedChecksum = singleData["checksum"]
                        
                        Console.debug("Checksum Compare: %s <=> %s", fileChecksum[0:6], storedChecksum[0:6])
                        
                        if storedChecksum != fileChecksum:
                            raise UserError("Sprite Sheet is not up-to-date. Checksum of %s differs.", singleId)
        
            Console.outdent()
            Console.debug("Deleting sprite config from assets: %s", fileId)
            del assets[fileId]
            
        Console.outdent()
        self.__sprites = sprites
        
        
        
    def __processAnimations(self):
        """Processes jasyanimation.json files to merge animation data into asset registry"""
        
        assets = self.__assets
        configs = [fileId for fileId in assets if assets[fileId].isImageAnimationConfig()]
        
        if configs:
            Console.info("Processing %s image animation configs...", len(configs))
        
        Console.indent()
        for fileId in configs:
            Console.debug("Processing %s...", fileId)
        
            asset = assets[fileId]
            base = os.path.dirname(fileId)
                
            try:
                config = json.loads(asset.getText())
            except ValueError as err:
                raise UserError("Could not parse jasyanimation.json at %s: %s" % (fileId, err))
            
            for relPath in config:
                imageId = "%s/%s" % (base, relPath)
                data = config[relPath]
                
                if not imageId in assets:
                    raise UserError("Unknown asset %s in %s" % (imageId, fileId))
                
                animationAsset = assets[imageId]
                
                if "rows" in data or "columns" in data:
                    rows = Util.getKey(data, "rows", 1)
                    columns = Util.getKey(data, "columns", 1)
                    frames = Util.getKey(data, "frames")
                    
                    animationAsset.addImageAnimationData(columns, rows, frames)
                    
                    if frames is None:
                        frames = rows * columns
                    
                elif "layout" in data:
                    layout = data["layout"]
                    animationAsset.addImageAnimationData(None, None, layout=layout)
                    frames = len(layout)
                    
                else:
                    raise UserError("Invalid image frame data for: %s" % imageId)

                Console.debug("  - Animation %s has %s frames", imageId, frames)

            Console.debug("  - Deleting animation config from assets: %s", fileId)
            del assets[fileId]
            
        Console.outdent()
        
    
    
    def addProfile(self, name, root=None, config=None, items=None):
        """
        Adds a new profile to the manager. This is basically the plain
        version of addSourceProfile/addBuildProfile which gives complete
        manual control of where to load the assets from. This is useful
        for e.g. supporting a complete custom loading scheme aka complex
        CDN based setup.
        """
        
        profiles = self.__profiles
        for entry in profiles:
            if entry["name"] == name:
                raise UserError("Asset profile %s was already defined!" % name)
        
        profile = {
            "name" : name
        }
        
        if root:
            if not root.endswith("/"):
                root += "/"
                
            profile["root"] = root
        
        if config is not None:
            profile.update(config)

        unique = len(profiles)
        profiles.append(profile)
        
        if items:
            for fileId in items:
                items[fileId]["p"] = unique
            
            self.__addRuntimeData(items)
        
        return unique
    
    
    def addSourceProfile(self, urlPrefix="", override=False):
        """
        Adds a profile to include assets as being available in source tasks.
        
        This basically means that assets from all projects are referenced via
        relative URLs to the main project.

        Note 1: This automatically updates all currently known assets to
        reference the source profile.

        Note 2: This method only adds profile data to any assets when either
        there is no profile registered yet or override is set to True.
        """

        # First create a new profile with optional (CDN-) URL prefix
        profileId = self.addProfile("source", urlPrefix)

        # Then export all relative paths to main project and add this to the runtime data
        main = self.__session.getMain()
        assets = self.__assets
        data = self.__data

        for fileId in assets:
            if not fileId in data:
                data[fileId] = {}
                
            if override or not "p" in data[fileId]:
                data[fileId]["p"] = profileId
                data[fileId]["u"] = main.toRelativeUrl(assets[fileId].getPath())

        return self



    def addBuildProfile(self, urlPrefix="asset", override=False):
        """
        Adds a profile to include assets as being available in build tasks.
        
        This basically means that assets from all projects are copied to
        a local directory inside the build folder.

        Note 1: This automatically updates all currently known assets to
        reference the build profile.

        Note 2: This method only adds profile data to any assets when either
        there is no profile registered yet or override is set to True.
        """
        
        # First create a new profile with optional (CDN-) URL prefix
        profileId = self.addProfile("build", urlPrefix)

        # Then export all relative paths to main project and add this to the runtime data
        main = self.__session.getMain()
        assets = self.__assets
        data = self.__data

        for fileId in assets:
            if not fileId in data:
                data[fileId] = {}
                
            if override or not "p" in data[fileId]:
                data[fileId]["p"] = profileId

        return self

    
    def __addRuntimeData(self, runtime):
        assets = self.__assets
        data = self.__data
        
        for fileId in runtime:
            if not fileId in assets:
                Console.debug("Unknown asset: %s" % fileId)
                continue
        
            if not fileId in data:
                data[fileId] = {}
                
            data[fileId].update(runtime[fileId])

        return self
    
    
    def __structurize(self, data):
        """
        This method structurizes the incoming data into a cascaded structure representing the
        file system location (aka file IDs) as a tree. It further extracts the extensions and
        merges files with the same name (but different extensions) into the same entry. This is
        especially useful for alternative formats like audio files, videos and fonts. It only
        respects the data of the first entry! So it is not a good idea to have different files
        with different content stored with the same name e.g. content.css and content.png.
        """
        
        root = {}
        
        # Easier to debug and understand when sorted
        for fileId in sorted(data):
            current = root
            splits = fileId.split("/")
            
            # Extract the last item aka the filename itself
            basename = splits.pop()
            
            # Find the current node to store info on
            for split in splits:
                if not split in current:
                    current[split] = {}
                elif type(current[split]) != dict:
                    raise UserError("Invalid asset structure. Folder names must not be identical to any filename without extension: \"%s\" in %s" % (split, fileId))
                    
                current = current[split]
            
            # Create entry
            Console.debug("Adding %s..." % fileId)
            current[basename] = data[fileId]
        
        return root
    
    
    
    def __compileFilterExpr(self, classes):
        """Returns the regular expression object to use for filtering"""
        
        # Merge asset hints from all classes and remove duplicates
        hints = set()
        for classObj in classes:
            hints.update(classObj.getMetaData(self.__session.getCurrentPermutation()).assets)
        
        # Compile filter expressions
        matcher = "^%s$" % "|".join(["(?:%s)" % fnmatch.translate(hint) for hint in hints])
        Console.debug("Compiled asset matcher: %s" % matcher)
        
        return re.compile(matcher)
        
        
        
    def deploy(self, classes, assetFolder=None):
        """
        Deploys all asset files to the destination asset folder. This merges
        assets from different projects into one destination folder.
        """

        # Sometimes it's called with explicit None - we want to fill the default
        # in that case as well.
        if assetFolder is None:
            assetFolder = "$prefix/asset"

        assets = self.__assets
        projects = self.__session.getProjects()

        copyAssetFolder = self.__session.expandFileName(assetFolder)
        filterExpr = self.__compileFilterExpr(classes)
        
        Console.info("Deploying assets...")
        
        counter = 0
        length = len(assets)
        
        for fileId in assets:
            if not filterExpr.match(fileId):
                length -= 1
                continue

            srcFile = assets[fileId].getPath()
            dstFile = os.path.join(copyAssetFolder, fileId.replace("/", os.sep))
            
            if jasy.core.File.syncfile(srcFile, dstFile):
                counter += 1
        
        Console.info("Updated %s/%s files" % (counter, length))
        


    def export(self, classes=None):
        """
        Exports asset data for usage at the client side. Utilizes JavaScript
        class jasy.Asset to inject data into the client at runtime.
        """
        
        # Processing assets
        assets = self.__assets
        data = self.__data
        
        result = {}
        filterExpr = self.__compileFilterExpr(classes) if classes else None
        for fileId in assets:
            if filterExpr and not filterExpr.match(fileId):
                continue
            
            entry = {}
            
            asset = assets[fileId]
            entry["t"] = asset.getType(short=True)

            assetData = asset.exportData()
            if assetData:
                entry["d"] = assetData
            
            if fileId in data:
                entry.update(data[fileId])
                
            result[fileId] = entry
        
        # Ignore empty result
        if not result:
            return None

        Console.info("Exported %s assets", len(result))

        return json.dumps({
            "assets" : self.__structurize(result),
            "profiles" : self.__profiles,
            "sprites" : self.__sprites
        }, indent=2)
        


########NEW FILE########
__FILENAME__ = Block
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

class Block():

    def __init__(self, w, h, image, rotated=False):
        self.w = w
        self.h = h
        self.fit = None
        self.image = image
        self.duplicates = []
        self.area = w * h
        self.rotated = rotated

    def toJSON(self):
        if self.fit:
            return {
                "left": self.fit.x,
                "top": self.fit.y,
                "width": self.image.width,
                "height": self.image.height,
                "rotation": -90 if self.rotated else 0
            }

        else:
            return  {
                "left": 0,
                "top": 0,
                "width": self.w,
                "height": self.h,
                "rotation": 0
            }


########NEW FILE########
__FILENAME__ = BlockNode
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

class BlockNode():
    
    def __init__(self, parent, x, y, w, h):

        parent.nodes.append(self)
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.down = None
        self.right = None
        self.used = False


########NEW FILE########
__FILENAME__ = BlockPacker
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

from jasy.asset.sprite.BlockNode import BlockNode

class BlockPacker():
    
    def __init__(self, w = 0, h = 0):

        self.nodes = []
        self.autogrow = False
        if w > 0 and h > 0:
            self.root = BlockNode(self, 0, 0, w, h)

        else:
            self.autogrow = True
            self.root = None

    def getUnused(self):
        return [b for b in self.nodes if not b.used]
        
    def fit(self, blocks):

        length = len(blocks)
        w = blocks[0].w if length > 0 else 0
        h = blocks[0].h if length > 0 else 0

        if self.autogrow:
            self.root = BlockNode(self, 0, 0, w, h)

        for block in blocks:
            
            node = self.findNode(self.root, block.w, block.h)
            if node:
                block.fit = self.splitNode(node, block.w, block.h)

            elif self.autogrow:
                block.fit = self.growNode(block.w, block.h)
        
    def findNode(self, root, w, h):

        if (root.used):
            return self.findNode(root.right, w, h) or self.findNode(root.down, w, h)

        elif w <= root.w and h <= root.h:
            return root

        else:
            return None

    def splitNode(self, node, w, h):
        node.used = True
        node.down = BlockNode(self, node.x, node.y + h, node.w, node.h - h)
        node.right = BlockNode(self, node.x + w, node.y, node.w - w, h)
        return node


    def growNode(self, w, h):
        
        canGrowDown  = w <= self.root.w
        canGrowRight = h <= self.root.h

        shouldGrowRight = canGrowRight and self.root.h >= self.root.w + w
        shouldGrowDown  = canGrowDown  and self.root.w >= self.root.h + h

        if shouldGrowRight:
            return self.growRight(w, h)

        elif shouldGrowDown:
            return self.growDown(w, h)

        elif canGrowRight:
            return self.growRight(w, h)

        elif canGrowDown:
            return self.growDown(w, h)

        else:
            return None
    

    def growRight(self, w, h):
        root = Node(self, 0, 0, self.root.w + w, self.root.h)
        root.used = True
        root.down = self.root
        root.right = BlockNode(self, self.root.w, 0, w, self.root.h)
        
        self.root = root

        node = self.findNode(self.root, w, h)

        if node:
            return self.splitNode(node, w, h)

        else:
            return None


    def growDown(self, w, h):
        root = BlockNode(self, 0, 0, self.root.w, self.root.h + h)
        root.used = True
        root.down = BlockNode(self, 0, self.root.h, self.root.w, h)
        root.right = self.root
        
        self.root = root

        node = self.findNode(self.root, w, h)

        if node:
            return self.splitNode(node, w, h)

        else:
            return None


########NEW FILE########
__FILENAME__ = File
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

class SpriteFile():

    def __init__(self, width, height, relPath, fullPath, checksum):

        self.width = width
        self.height = height
        self.relPath = relPath
        self.src = fullPath
        self.checksum = checksum
        self.block = None

    def __repr__(self):
        return '<SpriteFile %s > %s %dx%dpx>' % (self.relPath, self.src, self.width, self.height)

########NEW FILE########
__FILENAME__ = Sheet
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

from jasy import UserError
import jasy.core.Console as Console

# Make PIL (native module) optional
try:
    import Image, ImageDraw
except ImportError as err:
    Image = None

class SpriteSheet():

    def __init__(self, packer, blocks):

        self.packer = packer
        self.width = packer.root.w
        self.height = packer.root.h
        self.blocks = blocks

        self.area = self.width * self.height
        self.usedArea = sum([s.w * s.h for s in blocks])
        self.used = (100 / self.area) * self.usedArea


    def __len__(self):
        return len(self.blocks)


    def export(self, projectId=''):
        
        data = {}

        for block in self.blocks:

            info = block.toJSON()
            
            data[block.image.relPath] = info

            for d in block.duplicates:
                data[d.relPath] = info

        return data


    def write(self, filename, debug=False):

        if Image is None:
            raise UserError("Missing Python PIL which is required to create sprite sheets!")

        img = Image.new('RGBA', (self.width, self.height))
        draw = ImageDraw.Draw(img)

        #draw.rectangle((0, 0, self.width, self.height), fill=(255, 255, 0, 255))

        # Load images and pack them in
        for block in self.blocks:
            res = Image.open(block.image.src)

            x, y = block.fit.x, block.fit.y
            if block.rotated:
                Console.debug('%s is rotated' % block.image.src)
                res = res.rotate(90)

            img.paste(res, (x, y))
            del res

            if debug:
                x, y, w, h = block.fit.x, block.fit.y, block.w, block.h
                draw.rectangle((x, y , x + w , y + h), outline=(0, 0, 255, 255) if block.rotated else (255, 0, 0, 255))

        if debug:
            for i, block in enumerate(self.packer.getUnused()):
                x, y, w, h = block.x, block.y, block.w, block.h
                draw.rectangle((x, y , x + w , y + h), fill=(255, 255, 0, 255))

        img.save(filename)


########NEW FILE########
__FILENAME__ = SpritePacker
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

from jasy.asset.ImageInfo import ImgInfo
from jasy.asset.sprite.Block import Block
from jasy.asset.sprite.BlockPacker import BlockPacker
from jasy.asset.sprite.File import SpriteFile
from jasy.asset.sprite.Sheet import SpriteSheet
from jasy.core.Config import writeConfig

import jasy.core.Console as Console

import os, json, itertools, math


class PackerScore():

    def __init__(self, sheets, external):
        
        self.sheets = sheets
        self.external = external

        # TODO choose quadratic over non??
        self.sizes = ['%dx%dpx' % (s.width, s.height) for s in sheets]
        self.indexSize = sum([s.width / 128 + s.height / 128 for s in sheets])

        # the total area used
        self.area = int(sum([s.area for s in sheets]) * 0.0001)
        self.exArea = sum([s.area for s in external]) * 0.0001
        self.usedArea = int(sum([s.usedArea for s in sheets]) * 0.0001)
        self.count = len(sheets) 

        # we only factor in left out images
        # if their size is less than 50% of the total spritesheet size we have right now
        # everything else is included as it would blow up the sheet way too much
        self.excount = len([i for i in external if i.w * i.h * 0.0001 < self.area * 0.5]) + 1

        # Calculate in efficiency
        self.efficency = (100 / self.area) * self.usedArea
        self.value = self.efficency / (self.area * (self.excount * self.excount)) / (self.count ** self.count)

    def data(self):
        return (self.sheets, self.external)

    def __lt__(self, other):

        # Merge index sizes! if less images

        # Only go with bigger index size (n^2 more space taken) if we're score at least
        # 10% better
        if self.value > other.value * 1.1:
            return True

        # Otherwise sort against the index size
        elif self.value >= other.value:

            if self.indexSize < other.indexSize:
                return True

            elif self.indexSize == other.indexSize and self.sheets[0].width > other.sheets[0].width:
                return True

            else:
                return False

        else:
            if other.area == 1 and self.area > 1:
                return True

            return False

    def __gt__(self, other):
        return not self < other

    def __repr__(self):
        return '<PackerScore %d sheets #%d (%s) Area: %d Used: %d (%2.f%%) External: %d Count: %d Value: %2.5f>' % (self.count, self.indexSize, ', '.join(self.sizes), self.area, self.usedArea, self.efficency, self.excount - 1, self.count ** self.count, self.value)



class SpritePacker():
    """Packs single images into sprite images automatically"""


    def __init__(self, base, types = ('png'), width=1024, height=1024):

        self.base = base
        self.files = []
        self.types = types
        self.dataFormat = 'yaml';
    
    def clear(self):
        """
        Removes all generated sprite files found in the base directory
        """

        Console.info("Cleaning sprite files...")
        Console.indent()
        
        for dirPath, dirNames, fileNames in os.walk(self.base):
            for fileName in fileNames:
                if fileName.startswith("jasysprite"):
                    filePath = os.path.join(dirPath, fileName)
                    Console.debug("Removing file: %s", filePath)
                    os.remove(filePath)
        
        Console.outdent()

    def addDir(self, directory, recursive=False):
        """Adds all images within a directory to the sprite packer."""
        
        path = os.path.join(self.base, directory)
        if not os.path.exists(path):
            return

        if recursive:
            dirs = os.walk(path)

        else:
            dirs = [(os.path.join(self.base, directory), os.listdir(path), [])]

        # Iteratre over all directories
        for dirPath, dirNames, fileNames in dirs:

            Console.debug('Scanning directory for images: %s' % dirPath)

            # go through all dirs
            for dirName in dirNames:

                # Filter dotted directories like .git, .bzr, .hg, .svn, etc.
                if dirName.startswith("."):
                    dirNames.remove(dirName)
                    
            relDirPath = os.path.relpath(dirPath, path)

            # Add all the files within the dir
            for fileName in fileNames:
                
                if fileName[0] == "." or fileName.split('.')[-1] not in self.types or fileName.startswith('jasysprite'):
                    continue
                    
                relPath = os.path.normpath(os.path.join(relDirPath, fileName)).replace(os.sep, "/")
                fullPath = os.path.join(dirPath, fileName)
                
                self.addFile(relPath, fullPath)


    def addFile(self, relPath, fullPath):
        """Adds the specific file to the sprite packer."""

        fileType = relPath.split('.')[-1]
        if fileType not in self.types:
            raise Exception('Unsupported image format: %s' % fileType)
        
        # Load image and grab required information
        img = ImgInfo(fullPath)
        w, h = img.getSize()
        checksum = img.getChecksum()
        del img

        # TODO crop transparent "borders"
        # TODO allow for rotation

        self.files.append(SpriteFile(w, h, relPath, fullPath, checksum))

        Console.debug('- Found image "%s" (%dx%dpx)' % (relPath, w, h))


    def packBest(self, autorotate=False):
        """Pack blocks into a sprite sheet by trying multiple settings."""

        sheets, extraBlocks = [], []
        score = 0

        best = {
            'score': 0,
            'area': 10000000000000000000,
            'count': 10000000000000,
            'eff': 0
        }
        
        # Sort Functions
        def sortHeight(block):
            return (block.w, block.h, block.image.checksum)

        def sortWidth(block):
            return (block.h, block.w, block.image.checksum)

        def sortArea(block):
            return (block.w * block.h, block.w, block.h, block.image.checksum)

        sorts = [sortHeight, sortWidth, sortArea]
        rotationDiff = [(0, 0), (1.4, 0), (0, 1.4), (1.4, 1.4)] # rotate by 90 degrees if either b / a > value

        # Determine minimum size for spritesheet generation
        # by averaging the widths and heights of all images
        # while taking the ones in the sorted middile higher into account
        # then the ones at the outer edges of the spectirum


        l = len(self.files)
        mw = [(l - abs(i - l / 2)) / l * v for i, v in enumerate(sorted([i.width for i in self.files]))]
        mh = [(l - abs(i - l / 2)) / l * v for i, v in enumerate(sorted([i.height for i in self.files]))]

        minWidth = max(128, math.pow(2, math.ceil(math.log(sum(mw) / l, 2))))
        minHeight = max(128, math.pow(2, math.ceil(math.log(sum(mh) / l, 2))))

        #baseArea = sum([(l - abs(i - l / 2)) / l * v for i, v in enumerate(sorted([i.width * i.height for i in self.files]))])


        # try to skip senseless generation of way to small sprites
        baseArea = sum([minWidth * minHeight for i in self.files])
        while baseArea / (minWidth * minHeight) >= 20: # bascially an estimate of the number of sheets needed
            minWidth *= 2
            minHeight *= 2

        Console.debug('- Minimal size is %dx%dpx' % (minWidth, minHeight))

        sizes = list(itertools.product([w for w in [128, 256, 512, 1024, 2048] if w >= minWidth],
                                       [h for h in [128, 256, 512, 1024, 2048] if h >= minHeight]))

        if autorotate:
            methods = list(itertools.product(sorts, sizes, rotationDiff))

        else:
            methods = list(itertools.product(sorts, sizes, [(0, 0)]))

        Console.debug('Packing sprite sheet variants...')
        Console.indent()

        scores = []
        for sort, size, rotation in methods:

            # pack with current settings
            sh, ex, _ = self.pack(size[0], size[1], sort, silent=True, rotate=rotation)

            if len(sh):
                score = PackerScore(sh, ex)

                # Determine score, highest wins
                scores.append(score)

            else:
                Console.debug('No sprite sheets generated, no image fit into the sheet')

        Console.outdent()
        scores.sort()

        Console.debug('Generated the following sheets:')
        for i in scores:
            Console.debug('- ' + str(i))

        sheets, external = scores[0].data()
        
        if external:
            for block in external:
                Console.info('Ignored file %s (%dx%dpx)' % (block.image.relPath, block.w, block.h))
        
        return sheets, len(scores)


    def pack(self, width=1024, height=1024, sort=None, silent=False, rotate=(0, 0)):
        """Packs all sprites within the pack into sheets of the given size."""
        
        Console.debug('Packing %d images...' % len(self.files))

        allBlocks = []
        duplicateCount = 0
        checkBlocks = {}

        for f in self.files:
            f.block = None

            if not f.checksum in checkBlocks:
                
                # check for rotation
                ow = f.width
                oh = f.height

                rot = False

                if rotate[0] != 0:
                    if ow / oh > rotate[0]:
                        rot = True

                elif rotate[1] != 0:
                    if oh / ow > rotate[1]:
                        rot = True
                
                w, h = (oh, ow) if rot else (ow, oh)

                checkBlocks[f.checksum] = f.block = Block(w, h, f, rot)
                allBlocks.append(f.block)

            else:
                src = checkBlocks[f.checksum]
                Console.debug('  - Detected duplicate of "%s" (using "%s" as reference)' % (f.relPath, src.image.relPath))

                src.duplicates.append(f)
                duplicateCount += 1

            f.block = checkBlocks[f.checksum]

        Console.debug('Found %d unique blocks (mapping %d duplicates)' % (len(allBlocks), duplicateCount))

        # Sort Functions
        def sortHeight(img):
            return (img.w, img.h)

        def sortWidth(img):
            return (img.w, img.h)

        def sortArea(img):
            return (img.w * img.h, img.w, img.h)


        # Filter out blocks which are too big
        blocks = []
        extraBlocks = []
        for b in allBlocks:

            if b.w > width or b.h > height:
                extraBlocks.append(b)

            else:
                blocks.append(b)

        sheets = []

        fitted = 0
        while len(blocks):

            Console.debug('Sorting %d blocks...' % len(blocks))
            Console.indent()

            sortedSprites = sorted(blocks, key=sort if sort is not None else sortHeight)
            sortedSprites.reverse()

            # Pack stuff
            packer = BlockPacker(width, height)
            packer.fit(sortedSprites)
            
            # Filter fit vs non-fit blocks
            blocks = [s for s in sortedSprites if not s.fit]
            fitBlocks = [s for s in sortedSprites if s.fit]

            fitted += len(fitBlocks)

            # Create a new sprite sheet with the given blocks
            if len(fitBlocks) > 1:
                sheet = SpriteSheet(packer, fitBlocks)
                sheets.append(sheet)

                Console.debug('Created new sprite sheet (%dx%dpx, %d%% used)' % (sheet.width, sheet.height, sheet.used))

            else:
                Console.debug('Only one image fit into sheet, ignoring.')
                extraBlocks.append(fitBlocks[0])
                
            Console.outdent()

        Console.debug('Packed %d images into %d sheets. %d images were found to be too big and did not fit.' % (fitted, len(sheets), len(extraBlocks)))

        return (sheets, extraBlocks, 0)

    # extension can be set to 'yaml' or 'json'
    def setDataFormat(self, format='yaml'):
        """Sets format (json or yaml) for metadata output"""
        self.dataFormat = format;


    def generate(self, path='', autorotate=False, debug=False):
        """Generate sheets/variants"""
        
        Console.info('Generating sprite sheet variants...')
        Console.indent()
        
        sheets, count = self.packBest(autorotate)

        # Write PNG files
        data = {}
        for pos, sheet in enumerate(sheets):

            Console.info('Writing image (%dx%dpx) with %d images' % (sheet.width, sheet.height, len(sheet)))
            name = 'jasysprite_%d.png' % pos

            # Export
            sheet.write(os.path.join(self.base, path, name), debug)
            data[name] = sheet.export()
            
        Console.outdent()

        # Generate JSON/YAML
        Console.info('Exporting data...')
        script = os.path.join(self.base, path, 'jasysprite.%s' % self.dataFormat)
        writeConfig(data, script)



    def packDir(self, path='', recursive=True, autorotate=False, debug=False):
        """Pack images inside a dir into sprite sheets"""

        Console.info('Packing sprites in: %s' % os.path.join(self.base, path))
        Console.indent()
        
        self.files = []
        self.addDir(path, recursive=recursive)
        Console.info('Found %d images' % len(self.files))

        if len(self.files) > 0:
            self.generate(path, autorotate, debug)
            
        Console.outdent()



########NEW FILE########
__FILENAME__ = Cache
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

import shelve, time, os, os.path, sys, pickle, dbm, uuid, hashlib, atexit

import jasy
import jasy.core.Util
import jasy.core.Console as Console

hostId = uuid.getnode()

class Cache:
    """ 
    A cache class based on shelve feature of Python. Supports transient in-memory 
    storage, too. Uses memory storage for caching requests to DB as well for 
    improved performance. Uses keys for identification of entries like a normal
    hash table / dictionary.
    """
    
    __shelve = None
    
    def __init__(self, path, filename="jasycache", hashkeys=False):
        self.__transient = {}
        self.__file = os.path.join(path, filename)
        self.__hashkeys = hashkeys

        self.open()

        # Be sure to correctly write down and close cache file on exit
        atexit.register(self.close)
        
        
    def open(self):
        """Opens a cache file in the given path"""
        
        try:
            self.__shelve = shelve.open(self.__file, flag="c")
            
            storedVersion = jasy.core.Util.getKey(self.__shelve, "jasy-version")
            storedHost = jasy.core.Util.getKey(self.__shelve, "jasy-host")
            
            if storedVersion == jasy.__version__ and storedHost == hostId:
                return
                    
            if storedVersion is not None or storedHost is not None:
                Console.debug("Jasy version or host has been changed. Recreating cache...")
            
            self.clear()

            self.__shelve["jasy-version"] = jasy.__version__
            self.__shelve["jasy-host"] = hostId
            
        except dbm.error as dbmerror:
            errno = None
            try:
                errno = dbmerror.errno
            except:
                pass
                
            if errno is 35:
                raise IOError("Cache file is locked by another process!")
                
            elif "type could not be determined" in str(dbmerror):
                Console.error("Could not detect cache file format: %s" % self.__file)
                Console.warn("Recreating cache database...")
                self.clear()
                
            elif "module is not available" in str(dbmerror):
                Console.error("Unsupported cache file format: %s" % self.__file)
                Console.warn("Recreating cache database...")
                self.clear()
                
            else:
                raise dbmerror
    
    
    def clear(self):
        """
        Clears the cache file through re-creation of the file
        """
        
        if self.__shelve != None:
            Console.debug("Closing cache file %s..." % self.__file)
            
            self.__shelve.close()
            self.__shelve = None

        Console.debug("Clearing cache file %s..." % self.__file)
        
        self.__shelve = shelve.open(self.__file, flag="n")

        self.__shelve["jasy-version"] = jasy.__version__
        self.__shelve["jasy-host"] = hostId
        
        
    def read(self, key, timestamp=None, inMemory=True):
        """ 
        Reads the given value from cache.
        Optionally support to check wether the value was stored after the given 
        time to be valid (useful for comparing with file modification times).
        """
        
        if self.__hashkeys:
            key = hashlib.sha1(key.encode("ascii")).hexdigest()

        if key in self.__transient:
            return self.__transient[key]
        
        timeKey = key + "-timestamp"
        if key in self.__shelve and timeKey in self.__shelve:
            if not timestamp or timestamp <= self.__shelve[timeKey]:
                value = self.__shelve[key]
                
                # Useful to debug serialized size. Often a performance
                # issue when data gets to big.
                # rePacked = pickle.dumps(value)
                # print("LEN: %s = %s" % (key, len(rePacked)))
                
                # Copy over value to in-memory cache
                if inMemory:
                    self.__transient[key] = value

                return value
                
        return None
        
    
    def store(self, key, value, timestamp=None, transient=False, inMemory=True):
        """
        Stores the given value.
        Default timestamp goes to the current time. Can be modified
        to the time of an other files modification date etc.
        Transient enables in-memory cache for the given value
        """
        
        if self.__hashkeys:
            key = hashlib.sha1(key.encode("ascii")).hexdigest()
        
        if inMemory:
            self.__transient[key] = value

        if transient:
            return
        
        if not timestamp:
            timestamp = time.time()
        
        try:
            self.__shelve[key+"-timestamp"] = timestamp
            self.__shelve[key] = value
        except pickle.PicklingError as err:
            Console.error("Failed to store enty: %s" % key)

        
    def sync(self):
        """ Syncs the internal storage database """
        
        if self.__shelve is not None:
            self.__shelve.sync() 
      
      
    def close(self):
        """ Closes the internal storage database """
        
        if self.__shelve is not None:
            self.__shelve.close()  
            self.__shelve = None

      

########NEW FILE########
__FILENAME__ = Config
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

import sys, os, yaml, json

import jasy.core.Console as Console
import jasy.core.File as File

from jasy import UserError
from jasy.core.Util import getKey


__all__ = [ "Config", "findConfig", "loadConfig", "writeConfig" ]


def findConfig(fileName):
    """
    Returns the name of a config file based on the given base file name (without extension).
    Returns either a filename which endswith .json, .yaml or None
    """

    fileExt = os.path.splitext(fileName)[1]

    # Auto discovery
    if not fileExt:
        for tryExt in (".json", ".yaml"):
            if os.path.exists(fileName + tryExt):
                return fileName + tryExt

        return None  

    if os.path.exists(fileName) and fileExt in (".json", ".yaml"):
        return fileName  
    else:
        return None


def loadConfig(fileName, encoding="utf-8"):
    """
    Loads the given configuration file (filename without extension) and 
    returns the parsed object structure 
    """

    configName = findConfig(fileName)
    if configName is None:
        raise UserError("Unsupported config file: %s" % fileName)

    fileHandle = open(configName, mode="r", encoding=encoding)    

    fileExt = os.path.splitext(configName)[1]
    if fileExt == ".json":
        result = json.load(fileHandle)

    elif fileExt == ".yaml":
        result = yaml.load(fileHandle)

    fileHandle.close()
    return result


def writeConfig(data, fileName, indent=2, encoding="utf-8"):
    """
    Writes the given data structure to the given file name. Based on the given extension
    a different file format is choosen. Currently use either .yaml or .json.
    """

    fileHandle = open(fileName, mode="w", encoding=encoding)

    fileExt = os.path.splitext(fileName)[1]
    if fileExt == ".json":
        json.dump(data, fileHandle, indent=indent, ensure_ascii=False)
        fileHandle.close()

    elif fileExt == ".yaml":
        yaml.dump(data, fileHandle, default_flow_style=False, indent=indent, allow_unicode=True)
        fileHandle.close()

    else:
        fileHandle.close()
        raise UserError("Unsupported config type: %s" % fileExt)


def matchesType(value, expected):
    """
    Returns boolean for whether the given value matches the given type.
    Supports all basic JSON supported value types:
    primitive, integer/int, float, number/num, string/str, boolean/bool, dict/map, array/list, ...
    """

    result = type(value)
    expected = expected.lower()

    if result is int:
        return expected in ("integer", "number", "int", "num", "primitive")
    elif result is float:
        return expected in ("float", "number", "num", "primitive")
    elif result is str:
        return expected in ("string", "str", "primitive")
    elif result is bool:
        return expected in ("boolean", "bool", "primitive")
    elif result is dict:
        return expected in ("dict", "map")
    elif result is list:
        return expected in ("array", "list")

    return False


class Config:
    """
    Wrapper around JSON/YAML with easy to use import tools for using question files,
    command line arguments, etc.
    """

    def __init__(self, data=None):
        """
        Initialized configuration object with destination file name.
        """

        self.__data = data or {}


    def debug(self):
        """
        Prints data to the console
        """

        print(self.__data)


    def export(self):
        """
        Returns a flat data structure of the internal data
        """

        result = {}

        def recurse(data, prefix):
            for key in data:
                value = data[key]
                if type(value) is dict:
                    if prefix:
                        recurse(value, prefix + key + ".")
                    else:
                        recurse(value, key + ".")
                else:
                    result[prefix + key] = value

        recurse(self.__data, "")

        return result


    def injectValues(self, parse=True, **argv):
        """
        Injects a list of arguments into the configuration file, typically used for injecting command line arguments
        """

        for key in argv:
            self.set(key, argv[key], parse=parse)


    def loadValues(self, fileName, optional=False, encoding="utf-8"):
        """
        Imports the values of the given config file
        Returns True when the file was found and processed.

        Note: Supports dotted names to store into sub trees
        Note: This method overrides keys when they are already defined!
        """

        configFile = findConfig(fileName)
        if configFile is None:
            if optional:
                return False
            else:
                raise UserError("Could not find configuration file (values): %s" % configFile)

        data = loadConfig(configFile, encoding=encoding)
        for key in data:
            self.set(key, data[key])

        return True


    def readQuestions(self, fileName, force=False, autoDelete=True, optional=False, encoding="utf-8"):
        """
        Reads the given configuration file with questions and deletes the file afterwards (by default).
        Returns True when the file was found and processed.
        """

        configFile = findConfig(fileName)
        if configFile is None:
            if optional:
                return False
            else:
                raise UserError("Could not find configuration file (questions): %s" % configFile)

        data = loadConfig(configFile, encoding=encoding)
        for entry in data:
            question = entry["question"]
            name = entry["name"]

            accept = getKey(entry, "accept", None)
            required = getKey(entry, "required", True)
            default = getKey(entry, "default", None)
            force = getKey(entry, "force", False)

            self.ask(question, name, accept=accept, required=required, default=default, force=force)

        if autoDelete:
            File.rm(configFile)

        return True


    def executeScript(self, fileName, autoDelete=True, optional=False, encoding="utf-8"):
        """
        Executes the given script for configuration proposes and deletes the file afterwards (by default).
        Returns True when the file was found and processed.
        """

        if not os.path.exists(fileName):
            if optional:
                return False
            else:
                raise UserError("Could not find configuration script: %s" % configFile)

        env = {
            "config" : self,
            "file" : File
        }

        code = open(fileName, "r", encoding=encoding).read()
        exec(compile(code, os.path.abspath(fileName), "exec"), globals(), env)

        if autoDelete:
            File.rm("jasycreate.py")

        return True


    def has(self, name):
        """
        Returns whether there is a value for the given field name.
        """

        if not "." in name:
            return name in self.__data

        splits = name.split(".")
        current = self.__data

        for split in splits:
            if split in current:
                current = current[split]
            else:
                return False

        return True


    def get(self, name, default=None):
        """
        Returns the value of the given field or None when field is not set 
        """

        if not "." in name:
            return getKey(self.__data, name, default)

        splits = name.split(".")
        current = self.__data

        for split in splits[:-1]:
            if split in current:
                current = current[split]
            else:
                return None

        return getKey(current, splits[-1], default)        


    def ask(self, question, name, accept=None, required=True, default=None, force=False, parse=True):
        """
        Asks the user for value for the given configuration field:

        :param question: Question to ask the user
        :type question: string
        :param name: Name of field to store value in
        :type name: string
        :param accept: Any of the supported types to validate for (see matchesType)
        :type accept: string
        :param required: Whether the field is required
        :type required: boolean
        :param default: Default value whenever user has given no value
        """

        while True:
            msg = "- %s?" % question
            if accept is not None:
                msg += Console.colorize(" [%s]" % accept, "grey")

            if default is None:
                msg += Console.colorize(" (%s)" % name, "magenta")
            else:
                msg += Console.colorize(" (%s=%s)" % (name, default), "magenta")

            msg += ": "

            sys.stdout.write(msg)

            # Do not ask user for solved items
            if not force and self.has(name):
                print("%s %s" % (self.get(name), Console.colorize("(pre-filled)", "cyan")))
                return

            # Read user input, but ignore any leading/trailing white space
            value = input().strip()

            # Fallback to default if no value is given and field is not required
            if not required and value == "":
                value = default

            # Don't accept empty values
            if value == "":
                continue

            # Try setting the current value
            if self.set(name, value, accept=accept, parse=parse):
                break


    def set(self, name, value, accept=None, parse=False):
        """
        Saves the given value under the given field
        """

        # Don't accept None value
        if value is None:
            return False

        # Parse value for easy type checks
        if parse:
            try:
                parsedValue = eval(value)
            except:
                pass
            else:
                value = parsedValue

                # Convert tuples/sets into JSON compatible array
                if type(value) in (tuple, set):
                    value = list(value)

        # Check for given type
        if accept is not None and not matchesType(value, accept):
            print(Console.colorize("  - Invalid value: %s" % str(value), "red"))
            return False

        if "." in name:
            splits = name.split(".")
            current = self.__data
            for split in splits[:-1]:
                if not split in current:
                    current[split] = {}

                current = current[split]

            current[splits[-1]] = value

        else:
            self.__data[name] = value

        return True


    def write(self, fileName, indent=2, encoding="utf-8"):
        """
        Uses config writer to write the configuration file to the application
        """

        writeConfig(self.__data, fileName, indent=indent, encoding=encoding)

########NEW FILE########
__FILENAME__ = Console
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

"""
Centralized logging for complete Jasy environment.
"""

import logging, sys

__all__ = ["colorize", "header", "error", "warn", "info", "debug", "indent", "outdent"]



# ---------------------------------------------
# Colorized Output
# ---------------------------------------------

__colors = {
    'bold'      : ['\033[1m',  '\033[22m'],
    'italic'    : ['\033[3m',  '\033[23m'],
    'underline' : ['\033[4m',  '\033[24m'],
    'inverse'   : ['\033[7m',  '\033[27m'],

    'white'     : ['\033[37m', '\033[39m'],
    'grey'      : ['\033[90m', '\033[39m'],
    'black'     : ['\033[30m', '\033[39m'],

    'blue'      : ['\033[34m', '\033[39m'],
    'cyan'      : ['\033[36m', '\033[39m'],
    'green'     : ['\033[32m', '\033[39m'],
    'magenta'   : ['\033[35m', '\033[39m'],
    'red'       : ['\033[31m', '\033[39m'],
    'yellow'    : ['\033[33m', '\033[39m']
}

def colorize(text, color="red"):
    """Uses to colorize the given text for output on Unix terminals"""

    # Not supported on console on Windows native
    # Note: Cygwin has a different platform value
    if sys.platform == "win32":
        return text
        
    entry = __colors[color]
    return "%s%s%s" % (entry[0], text, entry[1])



# ---------------------------------------------
# Logging API
# ---------------------------------------------

__level = 0

def __format(text):
    global __level
    
    if __level == 0 or text == "":
        return text
    elif __level == 1:
        return "- %s" % text
    else:
        return "%s- %s" % ("  " * (__level-1), text)

def indent():
    """
    Increments global indenting level. Prepends spaces to the next
    logging messages until outdent() is called.

    Should be called whenever leaving a structural logging section.
    """

    global __level
    __level += 1

def outdent(all=False):
    """
    Decrements global indenting level. 
    Should be called whenever leaving a structural logging section.
    """

    global __level
    
    if all:
        __level = 0
    else:
        __level -= 1
    
def error(text, *argv):
    """Outputs an error message (visible by default)"""

    logging.warn(__format(colorize(colorize(text, "red"), "bold")), *argv)

def warn(text, *argv):
    """Outputs an warning (visible by default)"""

    logging.warn(__format(colorize(text, "red")), *argv)

def info(text, *argv):
    """Outputs an info message (visible by default, disable via --quiet option)"""

    logging.info(__format(text), *argv)

def debug(text, *argv):
    """Output a debug message (hidden by default, enable via --verbose option)"""

    logging.debug(__format(text), *argv)

def header(title):
    """Outputs the given title with prominent formatting"""

    global __level
    __level = 0
    
    logging.info("")
    logging.info(colorize(colorize(">>> %s" % title.upper(), "blue"), "bold"))
    logging.info(colorize("-------------------------------------------------------------------------------", "blue"))

########NEW FILE########
__FILENAME__ = Create
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

import re, os, os.path, shutil, tempfile

import jasy

from jasy.core.Project import getProjectFromPath
from jasy.core.Util import getKey
from jasy.core.Config import Config
from jasy import UserError

import jasy.core.Console as Console
import jasy.vcs.Repository as Repository


def getFirstSubFolder(start):

    for root, dirs, files in os.walk(start):
        for directory in dirs:
            if not directory.startswith("."):
                return directory

    return None



fieldPattern = re.compile(r"\$\${([_a-z][_a-z0-9\.]*)}", re.IGNORECASE | re.VERBOSE)

def massFilePatcher(path, data):
    
    # Convert method with access to local data
    def convertPlaceholder(mo):
        field = mo.group(1)
        value = data.get(field)

        # Verify that None means missing
        if value is None and not data.has(field):
            raise ValueError('No value for placeholder "%s"' % field)
    
        # Requires value being a string
        return str(value)
        
    # Patching files recursively
    Console.info("Patching files...")
    Console.indent()
    for dirPath, dirNames, fileNames in os.walk(path):
        relpath = os.path.relpath(dirPath, path)

        # Filter dotted directories like .git, .bzr, .hg, .svn, etc.
        for dirname in dirNames:
            if dirname.startswith("."):
                dirNames.remove(dirname)
        
        for fileName in fileNames:
            filePath = os.path.join(dirPath, fileName)
            fileRel = os.path.normpath(os.path.join(relpath, fileName))
            
            Console.debug("Processing: %s..." % fileRel)

            fileHandle = open(filePath, "r", encoding="utf-8", errors="surrogateescape")
            fileContent = []
            
            # Parse file line by line to detect binary files early and omit
            # fully loading them into memory
            try:
                isBinary = False

                for line in fileHandle:
                    if '\0' in line:
                        isBinary = True
                        break 
                    else:
                        fileContent.append(line)
        
                if isBinary:
                    Console.debug("Ignoring binary file: %s", fileRel)
                    continue

            except UnicodeDecodeError as ex:
                Console.warn("Can't process file: %s: %s", fileRel, ex)
                continue

            fileContent = "".join(fileContent)

            # Update content with available data
            try:
                resultContent = fieldPattern.sub(convertPlaceholder, fileContent)
            except ValueError as ex:
                Console.warn("Unable to process file %s: %s!", fileRel, ex)
                continue

            # Only write file if there where any changes applied
            if resultContent != fileContent:
                Console.info("Updating: %s...", Console.colorize(fileRel, "bold"))
                
                fileHandle = open(filePath, "w", encoding="utf-8", errors="surrogateescape")
                fileHandle.write(resultContent)
                fileHandle.close()
                
    Console.outdent()



validProjectName = re.compile(r"^[a-z][a-z0-9]*$")

def create(name="myproject", origin=None, originVersion=None, skeleton=None, destination=None, session=None, **argv):
    """
    Creates a new project from a defined skeleton or an existing project's root directory (only if there is a jasycreate.yaml/.json).

    :param name: The name of the new created project
    :type name: string
    :param origin: Path or git url to the base project
    :type origin: string
    :param originVersion: Version of the base project from wich will be created.
    :type originVersion: string
    :param skeleton: Name of a defined skeleton. None for creating from root
    :type skeleton: string
    :param destination: Destination path for the new created project
    :type destination: string
    :param session: An optional session to use as origin project
    :type session: object
    """

    if not validProjectName.match(name):
        raise UserError("Invalid project name: %s (Use lowercase characters and numbers only for broadest compabibility)" % name)


    #
    # Initial Checks
    #

    # Figuring out destination folder
    if destination is None:
        destination = name

    destinationPath = os.path.abspath(os.path.expanduser(destination))
    if os.path.exists(destinationPath):
        raise UserError("Cannot create project %s in %s. File or folder exists!" % (name, destinationPath))

    # Origin can be either:
    # 1) None, which means a skeleton from the current main project
    # 2) An repository URL
    # 3) A project name known inside the current session
    # 4) Relative or absolute folder path

    originPath = None;
    originName = None;

    if origin is None:
        originProject = session and session.getMain()

        if originProject is None:
            raise UserError("Auto discovery failed! No Jasy projects registered!")

        originPath = originProject.getPath()
        originName = originProject.getName()
        originRevision = None

    elif Repository.isUrl(origin):
        Console.info("Using remote skeleton")

        tempDirectory = tempfile.TemporaryDirectory()
        originPath = os.path.join(tempDirectory.name, "clone")
        originUrl = origin

        Console.indent()
        originRevision = Repository.update(originUrl, originVersion, originPath)
        Console.outdent()

        if originRevision is None:
            raise UserError("Could not clone origin repository!")

        Console.debug("Cloned revision: %s" % originRevision)
        if os.path.isfile(os.path.join(originPath, "jasycreate.yaml")) or os.path.isfile(os.path.join(originPath, "jasycreate.json")) or os.path.isfile(os.path.join(originPath, "jasycreate.py")):
            originProject = None
        else:
            originProject = getProjectFromPath(originPath)
            originName = originProject.getName()

    else:
        originProject = session and session.getProjectByName(origin)
        originVersion = None
        originRevision = None

        if originProject is not None:
            originPath = originProject.getPath()
            originName = origin

        elif os.path.isdir(origin):
            originPath = origin
            if os.path.isfile(os.path.join(originPath, "jasycreate.yaml")) or os.path.isfile(os.path.join(originPath, "jasycreate.json")) or os.path.isfile(os.path.join(originPath, "jasycreate.py")):
                originProject = None
            else:
                originProject = getProjectFromPath(originPath)
                originName = originProject.getName()

        else:
            raise UserError("Invalid value for origin: %s" % origin)


    # Figure out the skeleton root folder
    if originProject is not None:
        skeletonDir = os.path.join(originPath, originProject.getConfigValue("skeletonDir", "skeleton"))
    else:
        skeletonDir = originPath
    if not os.path.isdir(skeletonDir):
        raise UserError('The project %s offers no skeletons!' % originName)

    # For convenience: Use first skeleton in skeleton folder if no other selection was applied
    if skeleton is None:
        if originProject is not None:
            skeleton = getFirstSubFolder(skeletonDir)
        else:
            skeleton = skeletonDir

    # Finally we have the skeleton path (the root folder to copy for our app)
    skeletonPath = os.path.join(skeletonDir, skeleton)
    if not os.path.isdir(skeletonPath):
        raise UserError('Skeleton %s does not exist in project "%s"' % (skeleton, originName))


    #
    # Actual Work
    #

    # Prechecks done
    if originName:
        Console.info('Creating %s from %s %s...', Console.colorize(name, "bold"), Console.colorize(skeleton + " @", "bold"), Console.colorize(originName, "magenta"))
    else:
        Console.info('Creating %s from %s...', Console.colorize(name, "bold"), Console.colorize(skeleton, "bold"))
    Console.debug('Skeleton: %s', Console.colorize(skeletonPath, "grey"))
    Console.debug('Destination: %s', Console.colorize(destinationPath, "grey"))

    # Copying files to destination
    Console.info("Copying files...")
    shutil.copytree(skeletonPath, destinationPath)
    Console.debug("Files were copied successfully.")

    # Close origin project
    if originProject:
        originProject.close()

    # Change to directory before continuing
    os.chdir(destinationPath)

    # Create configuration file from question configs and custom scripts
    Console.info("Starting configuration...")
    config = Config()

    config.set("name", name)
    config.set("jasy.version", jasy.__version__)
    if originName:
        config.set("origin.name", originName)
    config.set("origin.version", originVersion)
    config.set("origin.revision", originRevision)
    config.set("origin.skeleton", os.path.basename(skeletonPath))

    config.injectValues(**argv)
    if originProject is not None:
        config.readQuestions("jasycreate", optional=True)
        config.executeScript("jasycreate.py", optional=True)

    # Do actual replacement of placeholders
    massFilePatcher(destinationPath, config)
    Console.debug("Files were patched successfully.")

    # Done
    Console.info('Your application %s was created successfully!', Console.colorize(name, "bold"))


########NEW FILE########
__FILENAME__ = Daemon
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

import time, os

import jasy.core.Console as Console

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

except ImportError as err:
    Observer = None
    FileSystemEventHandler = None


if FileSystemEventHandler:

    class JasyEventHandler(FileSystemEventHandler):
        """
        Summarizes callbacks for filesystem change events.
        """

        def on_moved(self, event):
            super(JasyEventHandler, self).on_moved(event)

            what = 'directory' if event.is_directory else 'file'
            Console.info("Moved %s: from %s to %s", what, event.src_path, event.dest_path)

        def on_created(self, event):
            super(JasyEventHandler, self).on_created(event)

            what = 'directory' if event.is_directory else 'file'
            Console.info("Created %s: %s", what, event.src_path)

        def on_deleted(self, event):
            super(JasyEventHandler, self).on_deleted(event)

            what = 'directory' if event.is_directory else 'file'
            Console.info("Deleted %s: %s", what, event.src_path)

        def on_modified(self, event):
            super(JasyEventHandler, self).on_modified(event)

            what = 'directory' if event.is_directory else 'file'
            Console.info("Modified %s: %s", what, event.src_path)


def watch(path, callback):
    """
    Start observing changes in filesystem. See JasyEventHandler for the event callbacks.

    :param path: Path wich will be observed
    :type name: string
    """
    
    if Observer is None:
        Console.error("You need to install Watchdog for supporting file system watchers")

    # Initialize file system observer
    observer = Observer()
    observer.schedule(JasyEventHandler(), ".", recursive=True)
    observer.start()

    Console.info("Started file system watcher for %s... [PID=%s]", path, os.getpid())
    Console.info("Use 'ulimit -n 1024' to increase number of possible open files")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    Console.info("Stopped file system watcher for %s...", path)
    observer.join()


########NEW FILE########
__FILENAME__ = Doctor
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

import jasy.core.Console as Console
from distutils.version import LooseVersion

try:
    import pip
except ImportError:
    Console.error("pip is required to run JASY!")
    sys.exit(1)


needs = [
    {
        "packageName": "Pygments",
        "minVersion": "1.5",
        "installPath": "'pip install Pygments'",
        "updatePath": "'pip install --upgrade pygments'"
    },
    {
        "packageName": "polib",
        "minVersion": "1.0.1",
        "installPath": "'pip install polib'",
        "updatePath": "'pip install --upgrade polib'"
    },
    {
        "packageName": "requests",
        "minVersion": "0.14",
        "installPath": "'pip install requests'",
        "updatePath": "'pip install --upgrade requests'"
    },
    {
        "packageName": "CherryPy",
        "minVersion": "3.2",
        "installPath": "'pip install CherryPy'",
        "updatePath": "'pip install --upgrade CherryPy'"
    },
    {
        "packageName": "PyYAML",
        "minVersion": "3.1",
        "installPath": "'pip install PyYAML'",
        "updatePath": "'pip install --upgrade PyYAML'"
    }
]

optionals = [
    {
        "packageName": "misaka",
        "minVersion": "1.0",
        "installPath": "'pip install misaka'",
        "updatePath": ""
    },
    {
        "packageName": "sphinx",
        "minVersion": "1.1",
        "installPath": "'pip install sphinx'",
        "updatePath": ""
    },
    {
        "packageName": "watchdog",
        "minVersion": "0.0",
        "installPath": "'pip install git+https://github.com/wpbasti/watchdog'",
        "updatePath": ""
    },
    {
        "packageName": "pil",
        "minVersion": "1.0",
        "installPath": "'pip install git+https://github.com/zynga/pil-py3k'",
        "updatePath": ""
    }
]


def doCompleteDoctor():
    """Checks for uninstalled or too old versions of requirements and gives a complete output"""

    Console.header("Doctor")

    dists = [dist for dist in pip.get_installed_distributions()]
    keys = [dist.key for dist in pip.get_installed_distributions()]

    versions = {}
    for dist in dists:
        versions[dist.key] = dist.version

    def checkSingleInstallation(keys, versions, packageName, minVersion, installPath, updatePath):
        Console.info('%s:' % packageName)
        Console.indent()
        if packageName.lower() in keys:
            Console.info(Console.colorize('Found installation', "green"))
            if LooseVersion(minVersion) > LooseVersion("0.0"):
                if LooseVersion(versions[packageName.lower()]) >= LooseVersion(minVersion):
                    Console.info(Console.colorize('Version is OK (needed: %s installed: %s)' % (minVersion, versions[packageName.lower()]), "green"))
                else:
                    Console.info(Console.colorize(Console.colorize('- Version is NOT OK (needed: %s installed: %s)' % (minVersion, versions[packageName.lower()]) , "red"), "bold"))
                    Console.info('Update to the newest version of %s using %s' % (packageName, updatePath))
        else:
            Console.info(Console.colorize(Console.colorize('Did NOT find installation', "red"), "bold"))
            Console.info('Install the newest version of %s using %s' % (packageName, installPath))
        Console.outdent()


    # Required packages
    Console.info(Console.colorize("Required Packages:", "bold"))
    Console.indent()
    for entry in needs:
        checkSingleInstallation(keys, versions, entry["packageName"], entry["minVersion"], entry["installPath"], entry["updatePath"])
    Console.outdent()

    # Optional packages
    Console.info("")
    Console.info(Console.colorize("Optional Packages:", "bold"))
    Console.indent()
    for entry in optionals:
        checkSingleInstallation(keys, versions, entry["packageName"], entry["minVersion"], entry["installPath"], entry["updatePath"])
    Console.outdent()


def doInitializationDoctor():
    """Checks for uninstalled or too old versions only of needed requirements and gives error output"""

    dists = [dist for dist in pip.get_installed_distributions()]
    keys = [dist.key for dist in pip.get_installed_distributions()]

    versions = {}
    for dist in dists:
        versions[dist.key] = dist.version

    def checkSingleInstallation(keys, versions, packageName, minVersion, installPath, updatePath):
        if packageName.lower() in keys:
            if LooseVersion(minVersion) > LooseVersion("0.0"):
                if LooseVersion(versions[packageName.lower()]) < LooseVersion(minVersion):
                    Console.info(Console.colorize(Console.colorize('Jasy requirement error: "%s"' % packageName, "red"), "bold"))
                    Console.indent()
                    Console.info(Console.colorize(Console.colorize('Version is NOT OK (needed: %s installed: %s)' % (minVersion, versions[packageName.lower()]) , "red"), "bold"))
                    Console.info('Update to the newest version of %s using %s' % (packageName, updatePath))
                    Console.outdent()
                    return False
        else:
            Console.info(Console.colorize(Console.colorize('Jasy requirement error: "%s"' % packageName, "red"), "bold"))
            Console.indent()
            Console.info(Console.colorize(Console.colorize('Did NOT find installation', "red"), "bold"))
            Console.info('Install the newest version of %s using %s' % (packageName, installPath))
            Console.outdent()
            return False

        return True

    allOk = True

    for entry in needs:
        if not checkSingleInstallation(keys, versions, entry["packageName"], entry["minVersion"], entry["installPath"], entry["updatePath"]):
            allOk = False

    return allOk




########NEW FILE########
__FILENAME__ = File
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

"""
A module consisting of some often used file system actions in easy to use unix tradition.
"""

import shutil, os, hashlib
from jasy import UserError

def cp(src, dst):
    """Copies a file"""

    # First test for existance of destination directory
    mkdir(os.path.dirname(dst))

    return shutil.copy2(src, dst)

def cpdir(src, dst):
    """Copies a directory"""
    return shutil.copytree(src, dst)

def exists(name):
    """Returns whether the given file or folder exists"""
    return os.path.exists(name)

def mkdir(name):
    """Creates directory (works recursively)"""

    if os.path.isdir(name):
        return
    elif os.path.exists(name):
        raise UserError("Error creating directory %s - File exists!" % name)

    return os.makedirs(name)

def mv(src, dst):
    """Moves files or directories"""
    return shutil.move(src, dst)

def rm(name):
    """Removes the given file"""
    return os.remove(name)

def rmdir(name):
    """Removes a directory (works recursively)"""
    return shutil.rmtree(name)

def write(dst, content):
    """Writes the content to the destination file name"""
    
    # First test for existance of destination directory
    mkdir(os.path.dirname(dst))
    
    # Open file handle and write
    handle = open(dst, mode="w", encoding="utf-8")
    handle.write(content)
    handle.close()

def syncfile(src, dst):
    """Same as cp() but only do copying when source file is newer than target file"""
    
    if not os.path.isfile(src):
        raise Exception("No such file: %s" % src)
    
    try:
        dst_mtime = os.path.getmtime(dst)
        src_mtime = os.path.getmtime(src)
        
        # Only accecpt equal modification time as equal as copyFile()
        # syncs over the mtime from the source.
        if src_mtime == dst_mtime:
            return False
        
    except OSError:
        # destination file does not exist, so mtime check fails
        pass
        
    return cp(src, dst)

def sha1(fileOrPath, block_size=2**20):
    """Returns a SHA 1 checksum (as hex digest) of the given file (handle)"""

    if type(fileOrPath) is str:
        fileOrPath = open(fileOrPath, "rb")

    sha1res = hashlib.sha1()
    while True:
        data = fileOrPath.read(block_size)
        if not data:
            break
        sha1res.update(data)

    return sha1res.hexdigest()


########NEW FILE########
__FILENAME__ = FileManager
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

import os, shutil, json
import jasy.core.Console as Console


class FileManager:
    """
    Summarizes utility methods for operations in filesystem.
    """

    def __init__(self, session):

        self.__session = session


    def removeDir(self, dirname):
        """Removes the given directory"""
        
        dirname = self.__session.expandFileName(dirname)
        if os.path.exists(dirname):
            Console.info("Deleting folder %s" % dirname)
            shutil.rmtree(dirname)


    def removeFile(self, filename):
        """Removes the given file"""
        
        filename = self.__session.expandFileName(filename)
        if os.path.exists(filename):
            Console.info("Deleting file %s" % filename)
            os.remove(filename)


    def makeDir(self, dirname):
        """Creates missing hierarchy levels for given directory"""
        
        if dirname == "":
            return
            
        dirname = self.__session.expandFileName(dirname)
        if not os.path.exists(dirname):
            os.makedirs(dirname)


    def copyDir(self, src, dst):
        """
        Copies a directory to a destination directory. 
        Merges the existing directory structure with the folder to copy.
        """
        
        dst = self.__session.expandFileName(dst)
        srcLength = len(src)
        counter = 0
        
        for rootFolder, dirs, files in os.walk(src):
            
            # figure out where we're going
            destFolder = dst + rootFolder[srcLength:]

            # loop through all files in the directory
            for fileName in files:

                # compute current (old) & new file locations
                srcFile = os.path.join(rootFolder, fileName)
                dstFile = os.path.join(destFolder, fileName)
                
                if self.updateFile(srcFile, dstFile):
                    counter += 1
        
        return counter


    def copyFile(self, src, dst):
        """Copy src file to dst file. Both should be filenames, not directories."""
        
        if not os.path.isfile(src):
            raise Exception("No such file: %s" % src)

        dst = self.__session.expandFileName(dst)

        # First test for existance of destination directory
        self.makeDir(os.path.dirname(dst))
        
        # Finally copy file to directory
        try:
            shutil.copy2(src, dst)
        except IOError as ex:
            Console.error("Could not write file %s: %s" % (dst, ex))
            
        return True


    def updateFile(self, src, dst):
        """Same as copyFile() but only do copying when source file is newer than target file"""
        
        if not os.path.isfile(src):
            raise Exception("No such file: %s" % src)
        
        dst = self.__session.expandFileName(dst)
        
        try:
            dst_mtime = os.path.getmtime(dst)
            src_mtime = os.path.getmtime(src)
            
            # Only accecpt equal modification time as equal as copyFile()
            # syncs over the mtime from the source.
            if src_mtime == dst_mtime:
                return False
            
        except OSError:
            # destination file does not exist, so mtime check fails
            pass
            
        return self.copyFile(src, dst)


    def writeFile(self, dst, content):
        """Writes the content to the destination file name"""
        
        dst = self.__session.expandFileName(dst)
        
        # First test for existance of destination directory
        self.makeDir(os.path.dirname(dst))
        
        # Open file handle and write
        handle = open(dst, mode="w", encoding="utf-8")
        handle.write(content)
        handle.close()


########NEW FILE########
__FILENAME__ = Inspect
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

import types, inspect, textwrap, re
import jasy.core.Console as Console


def highlightArgs(value, inClassOrObject=False):

    argsspec = inspect.getfullargspec(value)     

    if inClassOrObject:
        del argsspec.args[0]

    argmsg = "(%s" % ", ".join(argsspec.args)

    if argsspec.varkw is not None:
        if argsspec.args:
            argmsg += ", "

        argmsg += "..."

    argmsg += ")"

    return Console.colorize(argmsg, "cyan")    


def extractDoc(value, limit=80, indent=2):

    doc = value.__doc__

    if not doc:
        return None

    doc = doc.strip("\n\t ")

    if ". " in doc:
        doc = doc[:doc.index(". ")]

    lines = doc.split("\n")
    relevant = []
    for line in lines:
        # Stop at special lines (lists, sphinx hints)
        if line.strip().startswith(("-", "*", "#", ":")):
            break

        relevant.append(line)

    # Cleanup spaces
    doc = re.sub(" +", " ", " ".join(relevant)).strip()

    if doc:
        prefix = "\n" + (" " * indent)
        return ":" + prefix + prefix.join(textwrap.wrap(doc, limit))
    else:
        return None


def extractType(value):
    if inspect.isclass(value):
        return "Class"
    elif inspect.ismodule(value):
        return "Module"
    elif type(value) in (types.FunctionType, types.LambdaType):
        return "Function"
    elif isinstance(value, object):
        return "Object"

    return None


def generateApi(api):
    """Returns a stringified output for the given API set"""

    import jasy.env.Task as Task

    result = []

    for key in sorted(api):

        if key.startswith("__"):
            continue

        value = api[key]

        if type(value) is Task.Task:
            continue

        msg = Console.colorize(key, "bold")

        if inspect.isfunction(value):
            msg += Console.colorize(highlightArgs(value), "bold")
        elif inspect.isclass(value):
            msg += Console.colorize(highlightArgs(value.__init__, True), "bold")

        humanType = extractType(value)
        if humanType:
            msg += Console.colorize(" [%s]" % extractType(value), "magenta")

        msg += extractDoc(value) or ""

        result.append(msg)

        if inspect.isclass(value) or inspect.ismodule(value) or isinstance(value, object):

            if inspect.isclass(value):
                sprefix = ""
            elif inspect.ismodule(value) or isinstance(value, object):
                sprefix = "%s." % key

            smembers = dict(inspect.getmembers(value))

            for skey in sorted(smembers):
                if not "__" in skey:
                    svalue = smembers[skey]
                    if inspect.ismethod(svalue) or inspect.isfunction(svalue):
                        msg = "  - %s%s" % (sprefix, Console.colorize(skey, "bold"))
                        msg += highlightArgs(svalue, humanType in ("Class", "Object"))
                        msg += extractDoc(svalue, indent=6) or ""
                        result.append(msg)

        result.append("")

    return "\n".join(result)    


########NEW FILE########
__FILENAME__ = Locale
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

import os, json, re, xml.etree.ElementTree

import jasy.core.Console as Console
from jasy import datadir, __version__

import jasy.core.File

__all__ = ["LocaleParser"]


# Here we load our CLDR data from
CLDR_DIR = os.path.join(datadir, "cldr")

# Regular expression used for parsing CLDR plural rules
REGEXP_REL = re.compile(r"(\band\b|\bor\b)")
REGEXP_IS = re.compile(r"^(.*?) is (not )?([0-9]+)")
REGEXP_IN = re.compile(r"^(.*?) (not )?(within|in) ([0-9]+)\.\.([0-9]+)")

# Class template as used to generate JS files
CLASS_TEMPLATE = "// Automatically generated by Jasy %s\ncore.Module(\"%s\", %s);"


def camelCaseToUpper(input):
    if input.upper() == input:
        return input
    
    result = []
    for char in input:
        conv = char.upper()
        if char == conv and len(result) > 0:
            result.append("_")
            
        result.append(conv)
        
    return "".join(result)
    

def pluralToJavaScript(expr):
    """
    Translates the CLDR plural rules from 
    http://cldr.unicode.org/index/cldr-spec/plural-rules
    into JavaScript expressions
    """
    
    res = ""
    for relation in REGEXP_REL.split(expr.lower()):
        if relation == "and":
            res += "&&"
        elif relation == "or":
            res += "||"
        else:
            match = REGEXP_IS.match(relation)
            if match:
                expr = match.group(1).strip()
                if " " in expr:
                    expr = "(%s)" % re.compile(r"\s+mod\s+").sub("%", expr)

                res += expr
                
                if match.group(2) != None:
                    res += "!="
                else:
                    res += "=="
                    
                res += match.group(3)
                continue

            match = REGEXP_IN.match(relation)
            if match:
                expr = match.group(1).strip()
                if " " in expr:
                    expr = "(%s)" % re.compile(r"\s+mod\s+").sub("%", expr)
                
                if match.group(2) != None:
                    res += "!"
                
                res += "("
                if match.group(3) == "in":
                    # Fast integer check via: http://jsperf.com/simple-integer-check
                    res += "~~" + expr + "==" + expr + "&&"
                
                res += expr + ">=" + match.group(4) + "&&" + expr + "<=" + match.group(5) 
                res += ")"
                continue
                
            raise Exception("Unsupported relation: %s" % relation)

    return res
    
    
class LocaleParser():
    """Parses CLDR locales into JavaScript files"""

    def __init__(self, locale):
        Console.info("Parsing CLDR files for %s..." % locale)
        Console.indent()

        splits = locale.split("_")

        # Store for internal usage
        self.__locale = locale
        self.__language = splits[0]
        self.__territory = splits[1] if len(splits) > 1 else None

        # This will hold all data extracted data
        self.__data = {}

        # Add info section
        self.__data["info"] = {
            "LOCALE" : self.__locale,
            "LANGUAGE" : self.__language,
            "TERRITORY" : self.__territory
        }

        # Add keys (fallback to C-default locale)
        path = "%s.xml" % os.path.join(CLDR_DIR, "keys", self.__language)
        try:
            Console.info("Processing %s..." % os.path.relpath(path, CLDR_DIR))
            tree = xml.etree.ElementTree.parse(path)
        except IOError:
            path = "%s.xml" % os.path.join(CLDR_DIR, "keys", "C")
            Console.info("Processing %s..." % os.path.relpath(path, CLDR_DIR))
            tree = xml.etree.ElementTree.parse(path)
            
        self.__data["key"] = {
            "Short" : { key.get("type"): key.text for key in tree.findall("./keys/short/key") },
            "Full" : { key.get("type"): key.text for key in tree.findall("./keys/full/key") }
        }
        
        # Add main CLDR data: Fallback chain for locales
        main = os.path.join(CLDR_DIR, "main")
        files = []
        while True:
            files.append("%s.xml" % os.path.join(main, locale))
            
            if "_" in locale:
                locale = locale[:locale.rindex("_")]
            else:
                break

        # Extend data with root data
        files.append(os.path.join(main, "root.xml"))

        # Finally import all these files in order
        for path in reversed(files):
            Console.info("Processing %s..." % os.path.relpath(path, CLDR_DIR))
            tree = xml.etree.ElementTree.parse(path)

            self.__addDisplayNames(tree)
            self.__addDelimiters(tree)
            self.__addCalendars(tree)
            self.__addNumbers(tree)  
                
        # Add supplemental CLDR data
        self.__addSupplementals(self.__territory)

        Console.outdent()


    def export(self, path):
        Console.info("Writing result...")
        Console.info("Target directory: %s", path)
        Console.indent()
        
        jasy.core.File.write(os.path.join(path, "jasyproject.yaml"), 'name: locale\npackage: ""\n')
        count = self.__exportRecurser(self.__data, "locale", path)

        Console.info("Created %s classes", count)
        Console.outdent()


    def __exportRecurser(self, data, prefix, project):
        counter = 0

        for key in data:
            # Ignore invalid values
            if key is None:
                continue

            value = data[key]
            
            firstIsDict = False
            for childKey in value:
                if type(value[childKey]) == dict:
                    firstIsDict = True
                    break
            
            if firstIsDict:
                name = "%s.%s" % (prefix, key)
                counter += self.__exportRecurser(value, name, project)
            else:
                name = "%s.%s%s" % (prefix, key[0].upper(), key[1:])
                result = CLASS_TEMPLATE % (__version__, name, json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False))
                filename = "%s.js" % name.replace(".", os.path.sep)
                
                jasy.core.File.write(os.path.join(project, "src", filename), result)
                counter += 1

        return counter


    def __getStore(self, parent, name):
        """ Manages data fields """
        
        if not name in parent:
            store = {}
            parent[name] = store
        else:
            store = parent[name]

        return store
        
        
    def __addSupplementals(self, territory):
        """ Converts data from supplemental folder """
        
        supplemental = os.path.join(CLDR_DIR, "supplemental")

        # Plurals
        path = os.path.join(supplemental, "plurals.xml")
        Console.info("Processing %s..." % os.path.relpath(path, CLDR_DIR))
        tree = xml.etree.ElementTree.parse(path)
        self.__data["Plural"] = {}
        for item in tree.findall("plurals/pluralRules"):
            attr = item.get("locales")
            if attr != None:
                if self.__language in attr.split(" "):
                    for rule in item.findall("pluralRule"):
                        jsPlural = pluralToJavaScript(rule.text)
                        self.__data["Plural"][rule.get("count").upper()] = jsPlural
        
        # Telephone Codes
        path = os.path.join(supplemental, "telephoneCodeData.xml")
        Console.info("Processing %s..." % os.path.relpath(path, CLDR_DIR))
        tree = xml.etree.ElementTree.parse(path)
        for item in tree.findall("telephoneCodeData/codesByTerritory"):
            territoryId = item.get("territory")
            if territoryId == territory:
                for rule in item.findall("telephoneCountryCode"):
                    self.__data["PhoneCode"] = {"CODE":int(rule.get("code"))}
                    # Respect first only
                    break
        
        # Postal Codes
        path = os.path.join(supplemental, "postalCodeData.xml")
        Console.info("Processing %s..." % os.path.relpath(path, CLDR_DIR))
        tree = xml.etree.ElementTree.parse(path)
        for item in tree.findall("postalCodeData/postCodeRegex"):
            territoryId = item.get("territoryId")
            if territory == territoryId:
                self.__data["PostalCode"] = {"CODE":item.text}
                break
        
        # Supplemental Data
        path = os.path.join(supplemental, "supplementalData.xml")
        Console.info("Processing %s..." % os.path.relpath(path, CLDR_DIR))
        tree = xml.etree.ElementTree.parse(path)
        
        # :: Calendar Preference
        ordering = None
        for item in tree.findall("calendarPreferenceData/calendarPreference"):
            if item.get("territories") == "001" and ordering == None:
                ordering = item.get("ordering")
            elif territory in item.get("territories").split(" "):
                ordering = item.get("ordering")
                break
        
        self.__data["CalendarPref"] = { "ORDERING" : ordering.split(" ") }
        
        # :: Week Data
        self.__data["Week"] = {}
        weekData = tree.find("weekData")
        for key in ["firstDay", "weekendStart", "weekendEnd"]:
            day = None
            for item in weekData.findall(key):
                if item.get("territories") == "001" and day == None:
                    day = item.get("day")
                elif territory in item.get("territories").split(" "):
                    day = item.get("day")
                    break
            
            self.__data["Week"][camelCaseToUpper(key)] = day

        # :: Measurement System
        self.__data["Measurement"] = {}
        measurementData = tree.find("measurementData")
        for key in ["measurementSystem", "paperSize"]:
            mtype = None
            for item in measurementData.findall(key):
                if item.get("territories") == "001" and mtype == None:
                    mtype = item.get("type")
                elif territory in item.get("territories").split(" "):
                    mtype = item.get("type")
                    break

            self.__data["Measurement"][camelCaseToUpper(key)] = mtype

        
        
    def __addDisplayNames(self, tree):
        """ Adds CLDR display names section """
        
        display = self.__getStore(self.__data, "display")
        
        for key in ["languages", "scripts", "territories", "variants", "keys", "types", "measurementSystemNames"]:
            # make it a little bit shorter, there is not really any conflict potential
            if key == "measurementSystemNames":
                store = self.__getStore(display, "Measure")
            elif key == "territories":
                store = self.__getStore(display, "Territory")
            else:
                # remove last character "s" to force singular
                store = self.__getStore(display, key[:-1])
                
            for element in tree.findall("./localeDisplayNames/%s/*" % key):
                if not element.get("draft"):
                    field = element.get("type")
                    if not field in store:
                        store[camelCaseToUpper(field)] = element.text
                    
                    
    def __addDelimiters(self, tree):
        """ Adds CLDR delimiters """
        
        delimiters = self.__getStore(self.__data, "delimiter")
        
        for element in tree.findall("./delimiters/*"):
            if not element.get("draft"):
                field = element.tag
                if not field in delimiters:
                    delimiters[camelCaseToUpper(field)] = element.text
        
        
    def __addCalendars(self, tree, key="dates/calendars"):
        """ Loops through all CLDR calendars and adds them """
        
        calendars = self.__getStore(self.__data, "calendar")
            
        for element in tree.findall("./%s/*" % key):
            if not element.get("draft"):
                self.__addCalendar(calendars, element)


    def __addCalendar(self, store, element):
        """ Adds data from a CLDR calendar section """
        
        calendar = self.__getStore(store, element.get("type"))

        # Months Widths
        if element.find("months/monthContext/monthWidth") is not None:
            months = self.__getStore(calendar, "month")
            for child in element.findall("months/monthContext/monthWidth"):
                if not child.get("draft"):
                    format = child.get("type")
                    if not format in months:
                        months[format] = {}
                
                    for month in child.findall("month"):
                        if not month.get("draft"):
                            name = month.get("type").upper()
                            if not name in months[format]:
                                months[format][name] = month.text


        # Day Widths
        if element.find("days/dayContext/dayWidth") is not None:
            days = self.__getStore(calendar, "day")
            for child in element.findall("days/dayContext/dayWidth"):
                if not child.get("draft"):
                    format = child.get("type")
                    if not format in days:
                        days[format] = {}

                    for day in child.findall("day"):
                        if not day.get("draft"):
                            name = day.get("type").upper()
                            if not name in days[format]:
                                days[format][name] = day.text


        # Quarter Widths
        if element.find("quarters/quarterContext/quarterWidth") is not None:
            quarters = self.__getStore(calendar, "quarter")
            for child in element.findall("quarters/quarterContext/quarterWidth"):
                if not child.get("draft"):
                    format = child.get("type")
                    if not format in quarters:
                        quarters[format] = {}

                    for quarter in child.findall("quarter"):
                        if not quarter.get("draft"):
                            name = quarter.get("type").upper()
                            if not name in quarters[format]:
                                quarters[format][name] = quarter.text
        
        
        # Date Formats
        if element.find("dateFormats/dateFormatLength") is not None:
            dateFormats = self.__getStore(calendar, "date")
            for child in element.findall("dateFormats/dateFormatLength"):
                if not child.get("draft"):
                    format = child.get("type").upper()
                    text = child.find("dateFormat/pattern").text
                    if not format in dateFormats:
                        dateFormats[format] = text


        # Time Formats
        if element.find("timeFormats/timeFormatLength") is not None:
            timeFormats = self.__getStore(calendar, "time")
            for child in element.findall("timeFormats/timeFormatLength"):
                if not child.get("draft"):
                    format = child.get("type").upper()
                    text = child.find("timeFormat/pattern").text
                    if not format in timeFormats:
                        timeFormats[format] = text
                        
                        
        # DateTime Formats
        if element.find("dateTimeFormats/availableFormats") is not None:
            datetime = self.__getStore(calendar, "datetime")
            for child in element.findall("dateTimeFormats/availableFormats/dateFormatItem"):
                if not child.get("draft"):
                    # no uppercase here, because of intentianal camelcase
                    format = child.get("id")
                    text = child.text
                    if not format in datetime:
                        datetime[format] = text
        
        
        # Fields
        if element.find("fields/field") is not None:
            fields = self.__getStore(calendar, "field")
            for child in element.findall("fields/field"):
                if not child.get("draft"):
                    format = child.get("type").upper()
                    for nameChild in child.findall("displayName"):
                        if not nameChild.get("draft"):
                            text = nameChild.text
                            if not format in fields:
                                fields[format] = text
                            break
                        
                        
        # Relative
        if element.find("fields/field") is not None:
            relatives = self.__getStore(calendar, "relative")
            for child in element.findall("fields/field"):
                if not child.get("draft"):
                    format = child.get("type")
                    if child.findall("relative"):
                        relativeField = self.__getStore(relatives, format)
                        for relChild in child.findall("relative"):
                            if not relChild.get("draft"):
                                pos = relChild.get("type")
                                text = relChild.text
                                if not pos in relativeField:
                                    relativeField[pos] = text
                        
                        
    def __addNumbers(self, tree):
        store = self.__getStore(self.__data, "number")
                        
        # Symbols
        symbols = self.__getStore(store, "symbol")
        for element in tree.findall("numbers/symbols/*"):
            if not element.get("draft"):
                field = camelCaseToUpper(element.tag)
                if not field in store:
                    symbols[field] = element.text

        # Formats
        if not "format" in store:
            store["format"] = {}
                    
        for format in ["decimal", "scientific", "percent", "currency"]:
            if not format in store["format"]:
                for element in tree.findall("numbers//%sFormat/pattern" % format):
                    store["format"][camelCaseToUpper(format)] = element.text
            
        # Currencies
        currencies = self.__getStore(store, "currencyName")
        currenciesSymbols = self.__getStore(store, "currencySymbol")

        for child in tree.findall("numbers/currencies/currency"):
            if not child.get("draft"):
                short = child.get("type")
                for nameChild in child.findall("displayName"):
                    if not nameChild.get("draft"):
                        text = nameChild.text
                        if not format in currencies:
                            currencies[short] = text
                        break

                for symbolChild in child.findall("symbol"):
                    currenciesSymbols[short] = symbolChild.text

                
########NEW FILE########
__FILENAME__ = Options
#
# Jasy - Web Tooling Framework
# Copyright 2012 Zynga Inc.
#

import sys
import jasy.core.Console as Console

class Options:
    """
    More flexible alternative to the standard python option parser module
    which solves the requirements to have arbirary tasks and custom parameters for each task.
    """
    
    __slots__ = ["__tasks", "__options", "__defaults", "__types", "__shortcuts", "__help"]
    
    def __init__(self):

        self.__tasks = []
        self.__options = {}
        
        self.__help = {}
        self.__defaults = {}
        self.__types = {}
        self.__shortcuts = {}


    def parse(self, args):
        
        current = {
            "task" : None, 
            "params": {}
        }

        inTaskMode = False

        index = 0
        length = len(args)
        
        while index < length:

            name = args[index]
            if name.startswith("--"):
                name = name[2:]
            
                if "=" in name:
                    pos = name.find("=")
                    value = name[pos+1:]
                    name = name[0:pos]
                    
                    if not inTaskMode and self.__types[name] is bool:
                        raise Exception("Invalid argument: %s. Boolean flag!" % name)
                    
                elif (not name in self.__types or not self.__types[name] is bool) and (index+1) < length and not args[index+1].startswith("-"):
                    index += 1
                    value = args[index]

                elif inTaskMode:
                    raise Exception("Invalid argument: %s. In task mode every arguments needs to have a value!" % name)
                    
                else:
                    value = True
                    
                current["params"][name] = value
            
            elif name.startswith("-"):
                if inTaskMode:
                    raise Exception("Invalid argument: %s. Flags are not supported for tasks!" % name)
                
                name = name[1:]
                for partname in name:
                    current["params"][partname] = True
            
            else:
                if current:
                    self.__tasks.append(current)

                current = {}
                current["task"] = name
                current["params"] = {}
                
                inTaskMode = True
                
            index += 1

        if current:
            self.__tasks.append(current)
        
        if self.__tasks and self.__tasks[0]["task"] is None:
            self.__options = self.__tasks.pop(0)["params"]
            
        for name in list(self.__options):
            if name in self.__shortcuts:
                self.__options[self.__shortcuts[name]] = self.__options[name]
                del self.__options[name]
            elif len(name) == 1:
                raise Exception("Invalid argument: %s" % name)
            
            
    def printOptions(self, indent=16):

        for name in sorted(self.__defaults):
            col = len(name)
            msg = "  --%s" % name
            
            for shortcut in self.__shortcuts:
                if self.__shortcuts[shortcut] == name:
                    col += len(" [-%s]" % shortcut)
                    msg += Console.colorize(" [-%s]" % shortcut, "grey")
                    
            if name in self.__help:
                msg += ": "
                diff = indent - col
                if diff > 0:
                    msg += " " * diff
                    
                msg += Console.colorize(self.__help[name], "magenta")
            
            print(msg)
        

    def add(self, name, accept=bool, value=None, short=None, help=""):
        
        self.__defaults[name] = value

        if accept is not None:
            self.__types[name] = accept
        if short is not None:
            self.__shortcuts[short] = name
        if help:
            self.__help[name] = help

    def __str__(self):
        return str(self.__tasks)
        
    def __getattr__(self, name):
        if name in self.__options:
            return self.__options[name]
        elif name in self.__defaults:
            return self.__defaults[name]
        else:
            raise Exception("Unknown option: %s!" % name)
    
    def getTasks(self):
        return self.__tasks


        
########NEW FILE########
__FILENAME__ = OutputManager
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

import os

import jasy.core.Console as Console

from jasy.core.Permutation import getPermutation
from jasy.item.Class import ClassError
from jasy.js.Resolver import Resolver
from jasy.js.Sorter import Sorter
from jasy.js.parse.Parser import parse
from jasy.js.output.Compressor import Compressor
from jasy import UserError

from jasy.js.output.Optimization import Optimization
from jasy.js.output.Formatting import Formatting

from jasy.core.FileManager import FileManager

compressor = Compressor()
packCache = {}


def packCode(code):
    """Packs the given code by passing it to the compression engine"""
    
    if code in packCache:
       return packCache[code]
    
    packed = compressor.compress(parse(code))
    packCache[code] = packed
    
    return packed



class OutputManager:

    def __init__(self, session, assetManager=None, compressionLevel=1, formattingLevel=0):

        Console.info("Initializing OutputManager...")
        Console.indent()
        Console.info("Formatting Level: %s", formattingLevel)
        Console.info("Compression Level: %s", compressionLevel)

        self.__session = session

        self.__assetManager = assetManager
        self.__fileManager = FileManager(session)

        self.__scriptOptimization = Optimization()
        
        self.__compressGeneratedCode = False

        self.__kernelClasses = []

        if compressionLevel > 0:
            self.__scriptOptimization.enable("variables")
            self.__scriptOptimization.enable("declarations")
            
            self.__compressGeneratedCode = True

        if compressionLevel > 1:
            self.__scriptOptimization.enable("blocks")
            self.__scriptOptimization.enable("privates")

        self.__scriptFormatting = Formatting()

        if formattingLevel > 0:
            self.__scriptFormatting.enable("semicolon")
            self.__scriptFormatting.enable("comma")

        Console.outdent()


    def deployAssets(self, classes, assetFolder=None):
        """
        Deploys assets for the given classes and all their dependencies

        :param classes: List of classes to deploy assets for
        :type classes: list
        :param assetFolder: Destination folder of assets (defaults to $prefix/asset)
        :type assetFolder: string
        """

        Console.info("Deploying assets...")
        Console.indent()

        resolver = Resolver(self.__session)

        for className in classes:
            resolver.addClassName(className)

        self.__assetManager.deploy(resolver.getIncludedClasses(), assetFolder=assetFolder)

        Console.outdent()


    def storeKernel(self, fileName, classes=None, debug=False):
        """
        Writes a so-called kernel script to the given location. This script contains
        data about possible permutations based on current session values. It optionally
        might include asset data (useful when boot phase requires some assets) and 
        localization data (if only one locale is built).
        
        Optimization of the script is auto-enabled when no other information is given.
        
        This method returns the classes which are included by the script so you can 
        exclude it from the real other generated output files.
        """
        
        Console.info("Storing kernel...")
        Console.indent()
        
        # Use a new permutation based on debug settings and statically configured fields
        self.__session.setStaticPermutation(debug=debug)

        # Build resolver
        # We need the permutation here because the field configuration might rely on detection classes
        resolver = Resolver(self.__session)

        detectionClasses = self.__session.getFieldDetectionClasses()
        for className in detectionClasses:
            resolver.addClassName(className)

        # Jasy client side classes to hold data
        resolver.addClassName("jasy.Env")
        resolver.addClassName("jasy.Asset")
        resolver.addClassName("jasy.Translate")

        # Allow kernel level mass loading of scripts (required for source, useful for build)
        resolver.addClassName("core.io.Script")
        resolver.addClassName("core.io.Queue")

        if classes:
            for className in classes:
                resolver.addClassName(className)

        # Generate boot code 
        bootCode = "jasy.Env.setFields(%s);" % self.__session.exportFields()

        if self.__compressGeneratedCode:
            bootCode = packCode(bootCode)

        # Sort resulting class list
        sortedClasses = resolver.getSortedClasses()
        self.storeCompressed(sortedClasses, fileName, bootCode)
        
        # Remember classes for filtering in storeLoader/storeCompressed
        self.__kernelClasses = set(sortedClasses)

        # Reset static permutation
        self.__session.resetCurrentPermutation()

        Console.outdent()


    def storeCompressed(self, classes, fileName, bootCode=None):
        """
        Combines the compressed result of the stored class list
        
        :param classes: List of sorted classes to compress
        :type classes: list
        :param fileName: Filename to write result to
        :type fileName: string
        :param bootCode: Code to execute once all the classes are loaded
        :type bootCode: string
        """

        if self.__kernelClasses:
            filtered = [ classObj for classObj in classes if not classObj in self.__kernelClasses ]
        else:
            filtered = classes

        Console.info("Compressing %s classes...", len(filtered))
        Console.indent()
        result = []

        if self.__assetManager:
            assetData = self.__assetManager.export(filtered)
            if assetData:
                assetCode = "jasy.Asset.addData(%s);" % assetData
                if self.__compressGeneratedCode:
                    result.append(packCode(assetCode))
                else:
                    result.append(assetCode)

        permutation = self.__session.getCurrentPermutation()

        try:
            for classObj in filtered:
                result.append(classObj.getCompressed(permutation, 
                    self.__session.getCurrentTranslationBundle(), self.__scriptOptimization, self.__scriptFormatting))
                
        except ClassError as error:
            raise UserError("Error during class compression! %s" % error)

        Console.outdent()

        if bootCode:
            bootCode = "(function(){%s})();" % bootCode

            if self.__compressGeneratedCode:
                result.append(packCode(bootCode))
            else:
                result.append(bootCode)

        if self.__compressGeneratedCode:
            compressedCode = "".join(result)
        else:
            compressedCode = "\n\n".join(result)

        self.__fileManager.writeFile(fileName, compressedCode)


    def storeLoader(self, classes, fileName, bootCode="", urlPrefix=""):
        """
        Generates a source loader which is basically a file which loads the original JavaScript files.
        This is super useful during development of a project as it supports pretty fast workflows
        where most often a simple reload in the browser is enough to get the newest sources.
        
        :param classes: List of sorted classes to compress
        :type classes: list
        :param fileName: Filename to write result to
        :type fileName: string
        :param bootCode: Code to execute once all classes have been loaded
        :type bootCode: string
        :param urlPrefix: Prepends the given URL prefix to all class URLs to load
        :type urlPrefix: string
        """
        
        if self.__kernelClasses:
            filtered = [ classObj for classObj in classes if not classObj in self.__kernelClasses ]
        else:
            filtered = classes

        Console.info("Generating loader for %s classes...", len(classes))
        Console.indent()
        
        main = self.__session.getMain()
        files = []
        for classObj in filtered:
            path = classObj.getPath()

            # Support for multi path classes 
            # (typically in projects with custom layout/structure e.g. 3rd party)
            if type(path) is list:
                for singleFileName in path:
                    files.append(main.toRelativeUrl(singleFileName, urlPrefix))
            
            else:
                files.append(main.toRelativeUrl(path, urlPrefix))
        
        result = []
        Console.outdent()
        
        if self.__assetManager:
            assetData = self.__assetManager.export(filtered)
            if assetData:
                assetCode = "jasy.Asset.addData(%s);" % assetData
                if self.__compressGeneratedCode:
                    result.append(packCode(assetCode))
                else:
                    result.append(assetCode)

        translationBundle = self.__session.getCurrentTranslationBundle()
        if translationBundle:
            translationData = translationBundle.export(filtered)
            if translationData:
                translationCode = 'jasy.Translate.addData(%s);' % translationData
                if self.__compressGeneratedCode:
                    result.append(packCode(translationCode))        
                else:
                    result.append(translationCode)

        if self.__compressGeneratedCode:
            loaderList = '"%s"' % '","'.join(files)
        else:
            loaderList = '"%s"' % '",\n"'.join(files)

        wrappedBootCode = "function(){ %s }" % bootCode if bootCode else "null"
        loaderCode = 'core.io.Queue.load([%s], %s, null, true);' % (loaderList, wrappedBootCode)

        if self.__compressGeneratedCode:
            result.append(packCode(loaderCode))
        else:
            result.append(loaderCode)

        if self.__compressGeneratedCode:
            loaderCode = "".join(result)
        else:
            loaderCode = "\n\n".join(result)

        self.__fileManager.writeFile(fileName, loaderCode)


########NEW FILE########
__FILENAME__ = Permutation
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

import hashlib


__all__ = ["Permutation", "getPermutation"]


"""Central cache for all permutations"""
registry = {}

def getPermutation(combination):
    """
    Small wrapper to omit double creation of identical permutations in filter() method 
    As these instances don't have any reference to session etc. they are actually cacheable globally.
    """
    
    key = str(combination)
    if key in registry:
        return registry[key]
        
    registry[key] = Permutation(combination)
    return registry[key]


class Permutation:
    """Object to store a single kind of permutation"""
    
    def __init__(self, combination):
        
        self.__combination = combination
        self.__key = self.__buildKey(combination)
        self.__checksum = hashlib.sha1(self.__key.encode("ascii")).hexdigest()
        
        
    def __buildKey(self, combination):
        """Computes the permutations' key based on the given combination"""
        
        result = []
        for key in sorted(combination):
            value = combination[key]
            
            # Basic translation like in JavaScript frontend
            # We don't have a special threadment for strings, numbers, etc.
            if value == True:
                value = "true"
            elif value == False:
                value = "false"
            elif value == None:
                value = "null"
            
            result.append("%s:%s" % (key, value))

        return ";".join(result)
        
        
    def has(self, key):
        """Whether the permutation holds a value for the given key"""
        return key in self.__combination
        
        
    def get(self, key):
        """Returns the value of the given key in the permutation"""
        
        if key in self.__combination:
            return self.__combination[key]
            
        return None
        
        
    def getKey(self):
        """Returns the computed key from this permutation"""
        return self.__key
        
        
    def getChecksum(self):
        """Returns the computed (SHA1) checksum based on the key of this permutation"""
        return self.__checksum
        
        
    def filter(self, available):
        """Returns a variant of that permutation which only holds values for the available keys."""
        
        filtered = {}
        for key in self.__combination:
            if key in available:
                filtered[key] = self.__combination[key]
        
        if not filtered:
            return None
            
        return getPermutation(filtered)


    # Map Python built-ins
    __repr__ = getKey
    __str__ = getKey


########NEW FILE########
__FILENAME__ = Project
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

import os, re

import jasy.core.Cache
import jasy.core.Config as Config
import jasy.core.File as File
import jasy.core.Console as Console
import jasy.core.Util as Util

import jasy.vcs.Repository as Repository

import jasy.item.Abstract
import jasy.item.Doc
import jasy.item.Translation
import jasy.item.Class
import jasy.item.Asset

from jasy import UserError


__all__ = ["Project", "getProjectFromPath", "getProjectDependencies"]


classExtensions = (".js")
# Gettext .po files + ICU formats (http://userguide.icu-project.org/locale/localizing) (all formats but without .java support)
translationExtensions = (".po", ".xlf", ".properties", ".txt")
docFiles = ("package.md", "readme.md")
repositoryFolder = re.compile(r"^([a-zA-Z0-9\.\ _-]+)-([a-f0-9]{40})$")


projects = {}


def getProjectFromPath(path, config=None, version=None):
    global projects
    
    if not path in projects:
        projects[path] = Project(path, config, version)

    return projects[path]


def getProjectDependencies(project, checkoutDirectory="external", updateRepositories=True):
    """ Returns a sorted list of projects depending on the given project (including the given one) """

    def __resolve(project):

        name = project.getName()

        # List of required projects
        Console.info("Getting requirements of %s...", Console.colorize(name, "bold"))
        Console.indent()
        requires = project.getRequires(checkoutDirectory, updateRepositories)
        Console.outdent()

        if not requires:
            return

        Console.debug("Processing %s requirements...", len(requires))
        Console.indent()

        # Adding all project in reverse order.
        # Adding all local ones first before going down to their requirements
        for requiredProject in reversed(requires):
            requiredName = requiredProject.getName()
            if not requiredName in names:
                Console.debug("Adding: %s %s (via %s)", requiredName, requiredProject.version, project.getName())
                names[requiredName] = True
                result.append(requiredProject)
            else:
                Console.debug("Blocking: %s %s (via %s)", requiredName, requiredProject.version, project.getName())

        # Process all requirements of added projects
        for requiredProject in requires:
            if requiredProject.hasRequires():
                __resolve(requiredProject)

        Console.outdent()

    result = [project]
    names = {
        project.getName() : True
    }

    __resolve(project)

    return result



def getProjectNameFromPath(path):
    name = os.path.basename(path)

    # Remove folder SHA1 postfix when cloned via git etc.
    clone = repositoryFolder.match(name)
    if clone is not None:
        name = clone.group(1)

    # Slashes are often used as a separator to optional data
    if "-" in name:
        name = name[:name.rindex("-")]

    return name


class Project():
    
    kind = "none"
    scanned = False


    def __init__(self, path, config=None, version=None):
        """
        Constructor call of the project. 

        - First param is the path of the project relative to the current working directory.
        - Config can be read from jasyproject.json or using constructor parameter @config
        - Parent is used for structural debug messages (dependency trees)
        """
        
        if not os.path.isdir(path):
            raise UserError("Invalid project path: %s" % path)
        
        # Only store and work with full path
        self.__path = os.path.abspath(os.path.expanduser(path))
        
        # Store given params
        self.version = version
        
        # Intialize item registries
        self.classes = {}
        self.assets = {}        
        self.docs = {}
        self.translations = {}

        # Load project configuration
        self.__config = Config.Config(config)
        self.__config.loadValues(os.path.join(self.__path, "jasyproject"), optional=True)

        # Initialize cache
        try:
            File.mkdir(os.path.join(self.__path, ".jasy"))
            self.__cache = jasy.core.Cache.Cache(self.__path, filename=".jasy/cache")
        except IOError as err:
            raise UserError("Could not initialize project. Cache file in %s could not be initialized! %s" % (self.__path, err))
        
        # Detect version changes
        if version is None:
            self.__modified = True
        else:
            cachedVersion = self.__cache.read("project[version]")
            self.__modified = cachedVersion != version
            self.__cache.store("project[version]", version)

        # Read name from manifest or use the basename of the project's path
        self.__name = self.__config.get("name", getProjectNameFromPath(self.__path))
            
        # Read requires
        self.__requires = self.__config.get("requires", {})
        
        # Defined whenever no package is defined and classes/assets are not stored in the toplevel structure.
        self.__package = self.__config.get("package", self.__name if self.__config.has("name") else None)

        # Read fields (for injecting data into the project and build permutations)
        self.__fields = self.__config.get("fields", {})

        # Read setup for running command pre-scan
        self.__setup = self.__config.get("setup")



    #
    # Project Scan/Init
    #

    def scan(self):

        if self.scanned:
            return

        updatemsg = "[updated]" if self.__modified else "[cached]"
        Console.info("Scanning project %s %s...", self.__name, Console.colorize(updatemsg, "grey"))
        Console.indent()

        # Support for pre-initialize projects...
        setup = self.__setup
        if setup and self.__modified:
            Console.info("Running setup...")
            Console.indent()

            for cmd in setup:
                Console.info("Executing %s...", cmd)

                result = None
                try:
                    result = None
                    result = Util.executeCommand(cmd, "Failed to execute setup command %s" % cmd, path=self.__path)
                except Exception as ex:
                    if result:
                        Console.error(result)

                    raise UserError("Could not scan project %s: %s" % (self.__name, ex))

            Console.outdent()
        
        # Processing custom content section. Only supports classes and assets.
        if self.__config.has("content"):
            self.kind = "manual"
            self.__addContent(self.__config.get("content"))

        # Application projects
        elif self.__hasDir("source"):
            self.kind = "application"

            if self.__hasDir("source/class"):
                self.__addDir("source/class", "classes")
            if self.__hasDir("source/asset"):
                self.__addDir("source/asset", "assets")
            if self.__hasDir("source/translation"):
                self.__addDir("source/translation", "translations")
                
        # Compat - please change to class/style/asset instead
        elif self.__hasDir("src"):
            self.kind = "resource"
            self.__addDir("src", "classes")

        # Resource projects
        else:
            self.kind = "resource"

            if self.__hasDir("class"):
                self.__addDir("class", "classes")
            if self.__hasDir("asset"):
                self.__addDir("asset", "assets")
            if self.__hasDir("translation"):
                self.__addDir("translation", "translations")

        # Generate summary
        summary = []
        for section in ["classes", "assets", "translations"]:
            content = getattr(self, section, None)
            if content:
                summary.append("%s %s" % (len(content), section))

        # Print out
        if summary:
            Console.info("Done %s: %s" % (Console.colorize("[%s]" % self.kind, "grey"), Console.colorize(", ".join(summary), "green")))
        else:
            Console.error("Project is empty!")

        self.scanned = True

        Console.outdent()




    #
    # FILE SYSTEM INDEXER
    #
    
    def __hasDir(self, directory):
        full = os.path.join(self.__path, directory)
        if os.path.exists(full):
            if not os.path.isdir(full):
                raise UserError("Expecting %s to be a directory: %s" % full)
            
            return True
        
        return False
        
        
    def __addContent(self, content):
        Console.debug("Adding manual content")
        
        Console.indent()
        for fileId in content:
            fileContent = content[fileId]
            if len(fileContent) == 0:
                raise UserError("Empty content!")
                
            # If the user defines a file extension for JS public idenfiers 
            # (which is not required) we filter them out
            if fileId.endswith(".js"):
                raise UserError("JavaScript files should define the exported name, not a file name: %s" % fileId)

            fileExtension = os.path.splitext(fileContent[0])[1]
            
            # Support for joining text content
            if len(fileContent) == 1:
                filePath = os.path.join(self.__path, fileContent[0])
            else:
                filePath = [os.path.join(self.__path, filePart) for filePart in fileContent]
            
            # Structure files
            if fileExtension in classExtensions:
                construct = jasy.item.Class.ClassItem
                dist = self.classes
            elif fileExtension in translationExtensions:
                construct = jasy.item.Translation.TranslationItem
                dist = self.translations
            else:
                construct = jasy.item.Asset.AssetItem
                dist = self.assets
                
            # Check for duplication
            if fileId in dist:
                raise UserError("Item ID was registered before: %s" % fileId)
            
            # Create instance
            item = construct(self, fileId).attach(filePath)
            Console.debug("Registering %s %s" % (item.kind, fileId))
            dist[fileId] = item
            
        Console.outdent()
        
        
    def __addDir(self, directory, distname):
        
        Console.debug("Scanning directory: %s" % directory)
        Console.indent()
        
        path = os.path.join(self.__path, directory)
        if not os.path.exists(path):
            return
            
        for dirPath, dirNames, fileNames in os.walk(path):
            for dirName in dirNames:
                # Filter dotted directories like .git, .bzr, .hg, .svn, etc.
                if dirName.startswith("."):
                    dirNames.remove(dirName)

                # Filter sub projects
                if os.path.exists(os.path.join(dirPath, dirName, "jasyproject.json")):
                    dirNames.remove(dirName)
                    
            relDirPath = os.path.relpath(dirPath, path)

            for fileName in fileNames:
                
                if fileName[0] == ".":
                    continue
                    
                relPath = os.path.normpath(os.path.join(relDirPath, fileName)).replace(os.sep, "/")
                fullPath = os.path.join(dirPath, fileName)
                
                self.addFile(relPath, fullPath, distname)
        
        Console.outdent()


    def addFile(self, relPath, fullPath, distname, override=False):
        
        fileName = os.path.basename(relPath)
        fileExtension = os.path.splitext(fileName)[1]

        # Prepand package
        if self.__package:
            fileId = "%s/" % self.__package
        else:
            fileId = ""

        # Structure files  
        if fileExtension in classExtensions and distname == "classes":
            fileId += os.path.splitext(relPath)[0]
            construct = jasy.item.Class.ClassItem
            dist = self.classes
        elif fileExtension in translationExtensions and distname == "translations":
            fileId += os.path.splitext(relPath)[0]
            construct = jasy.item.Translation.TranslationItem
            dist = self.translations
        elif fileName in docFiles:
            fileId += os.path.dirname(relPath)
            fileId = fileId.strip("/") # edge case when top level directory
            construct = jasy.item.Doc.DocItem
            dist = self.docs
        else:
            fileId += relPath
            construct = jasy.item.Asset.AssetItem
            dist = self.assets

        # Only assets keep unix style paths identifiers
        if construct != jasy.item.Asset.AssetItem:
            fileId = fileId.replace("/", ".")

        # Check for duplication
        if fileId in dist and not override:
            raise UserError("Item ID was registered before: %s" % fileId)

        # Create instance
        item = construct(self, fileId).attach(fullPath)
        Console.debug("Registering %s %s" % (item.kind, fileId))
        dist[fileId] = item
        
        
    

    #
    # ESSENTIALS
    #

    def hasRequires(self):
        return len(self.__requires) > 0

    
    def getRequires(self, checkoutDirectory="external", updateRepositories=True):
        """
        Return the project requirements as project instances
        """

        global projects
        
        result = []
        
        for entry in self.__requires:
            
            if type(entry) is dict:
                source = entry["source"]
                config = Util.getKey(entry, "config")
                version = Util.getKey(entry, "version")
                kind = Util.getKey(entry, "kind")
            else:
                source = entry
                config = None
                version = None
                kind = None

            # Versions are expected being string type
            if version is not None:
                version = str(version)

            revision = None
            
            if Repository.isUrl(source):
                kind = kind or Repository.getType(source)
                path = os.path.abspath(os.path.join(checkoutDirectory, Repository.getTargetFolder(source, version)))
                
                # Only clone and update when the folder is unique in this session
                # This reduces git/hg/svn calls which are typically quite expensive
                if not path in projects:
                    revision = Repository.update(source, version, path, updateRepositories)
                    if revision is None:
                        raise UserError("Could not update repository %s" % source)
            
            else:
                kind = "local"
                if not source.startswith(("/", "~")):
                    path = os.path.join(self.__path, source)
                else:
                    path = os.path.abspath(os.path.expanduser(source))
            
            if path in projects:
                project = projects[path]
                
            else:
                fullversion = []
                
                # Produce user readable version when non is defined
                if version is None and revision is not None:
                    version = "master"
                
                if version is not None:
                    if "/" in version:
                        fullversion.append(version[version.rindex("/")+1:])
                    else:
                        fullversion.append(version)
                    
                if revision is not None:
                    # Shorten typical long revisions as used by e.g. Git
                    if type(revision) is str and len(revision) > 20:
                        fullversion.append(revision[:10])
                    else:
                        fullversion.append(revision)
                        
                if fullversion:
                    fullversion = "-".join(fullversion)
                else:
                    fullversion = None

                project = Project(path, config, fullversion)
                projects[path] = project
            
            result.append(project)
        
        return result


    def getFields(self):
        """ Return the project defined fields which may be configured by the build script """
        return self.__fields

    def getClassByName(self, className):
        """ Finds a class by its name."""

        try:
            return self.getClasses()[className]
        except KeyError:
            return None

    def getName(self):
        return self.__name
    
    def getPath(self):
        return self.__path
    
    def getPackage(self):
        return self.__package

    def getConfigValue(self, key, default=None):
        return self.__config.get(key, default)
        
    def toRelativeUrl(self, path, prefix="", subpath="source"):
        root = os.path.join(self.__path, subpath)
        relpath = os.path.relpath(path, root)

        if prefix:
            if not prefix[-1] == os.sep:
                prefix += os.sep
                
            relpath = os.path.normpath(prefix + relpath)
            
        return relpath.replace(os.sep, "/")



    #
    # CACHE API
    #
    
    def getCache(self):
        """Returns the cache instance"""
        
        return self.__cache
    
    def clean(self):
        """Clears the cache of the project"""
        
        Console.info("Clearing cache of %s..." % self.__name)
        self.__cache.clear()
        
    def close(self):
        """Closes the project which deletes the internal caches"""
        
        if self.__cache:
            self.__cache.close()
            self.__cache = None
        
        self.classes = None
        self.assets = None
        self.docs = None
        self.translations = None
        
    def pause(self):
        """Pauses the project so that other processes could modify/access it"""
        
        self.__cache.close()
        
    def resume(self):
        """Resumes the paused project"""
        
        self.__cache.open()



    #
    # LIST ACCESSORS
    #
    
    def getDocs(self):
        """Returns all package docs"""

        if not self.scanned:
            self.scan()

        return self.docs

    def getClasses(self):
        """ Returns all project JavaScript classes. Requires all files to have a "js" extension. """

        if not self.scanned:
            self.scan()

        return self.classes

    def getAssets(self):
        """ Returns all project asssets (images, stylesheets, static data, etc.). """

        if not self.scanned:
            self.scan()

        return self.assets

    def getTranslations(self):
        """ Returns all translation objects """

        if not self.scanned:
            self.scan()

        return self.translations

        
########NEW FILE########
__FILENAME__ = Session
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

import itertools, time, atexit, json, os

import jasy.core.Locale
import jasy.core.Config
import jasy.core.Project
import jasy.core.Permutation

import jasy.asset.Manager
import jasy.item.Translation

from jasy import UserError
import jasy.core.Console as Console


class Session():
    """
    Manages all projects, fields, permutations, translations etc. Mainly like
    the main managment infrastructure. 
    """

    __currentPermutation = None
    __currentTranslationBundle = None
    __currentPrefix = None
    
    __timestamp = None
    __projects = None
    __fields = None
    __translationBundles = None
    __updateRepositories = True
    __scriptEnvironment = None


    #
    # Core
    #

    def __init__(self):

        atexit.register(self.close)

        self.__timestamp = time.time()

        self.__projects = []
        self.__fields = {}
        self.__translationBundles = {}
        

    def init(self, autoInitialize=True, updateRepositories=True, scriptEnvironment=None):
        """
        Initialize the actual session with projects

        :param autoInitialize: Whether the projects should be automatically added when the current folder contains a valid Jasy project.
        :param updateRepositories: Whether to update repositories of all project dependencies.
        :param scriptEnvironment: API object as being used for loadLibrary to add Python features offered by projects.
        """

        self.__scriptEnvironment = scriptEnvironment
        self.__updateRepositories = updateRepositories

        if autoInitialize and jasy.core.Config.findConfig("jasyproject"):

            try:
                self.addProject(jasy.core.Project.getProjectFromPath("."))

            except UserError as err:
                Console.outdent(True)
                Console.error(err)
                raise UserError("Critical: Could not initialize session!")

            Console.info("Active projects (%s):", len(self.__projects))
            Console.indent()

            for project in self.__projects:
                if project.version:
                    Console.info("%s @ %s", Console.colorize(project.getName(), "bold"), Console.colorize(project.version, "magenta"))
                else:
                    Console.info(Console.colorize(project.getName(), "bold"))

            Console.outdent()        

    
    def clean(self):
        """Clears all caches of all registered projects"""

        if not self.__projects:
            return

        Console.info("Cleaning session...")
        Console.indent()

        for project in self.__projects:
            project.clean()

        Console.outdent()


    def close(self):
        """Closes the session and stores cache to the harddrive."""

        if not self.__projects:
            return

        Console.debug("Closing session...")
        Console.indent()

        for project in self.__projects:
            project.close()
        
        self.__projects = None

        Console.outdent()
    
    
    def pause(self):
        """
        Pauses the session. This release cache files etc. and makes 
        it possible to call other jasy processes on the same projects.
        """
        
        Console.info("Pausing session...")

        for project in self.__projects:
            project.pause()


    def resume(self):
        """Resumes the session after it has been paused."""

        Console.info("Resuming session...")

        for project in self.__projects:
            project.resume()
            
    
    def getClassByName(self, className):
        """
        Queries all currently registered projects for the given class and returns the class item.
        Returns None when no matching class item was found.

        :param className: Any valid classname from any of the projects.
        :type className: str
        """

        for project in self.__projects:
            classes = project.getClasses()
            if className in classes:
                return classes[className]

        return None


    
    
    
    #
    # Project Managment
    #
        
    def addProject(self, project):
        """
        Adds the given project to the list of known projects. Projects should be added in order of
        their priority. This adds the field configuration of each project to the session fields.
        Fields must not conflict between different projects (same name).
        
        :param project: Instance of Project to append to the list
        :type project: object
        """
        
        result = jasy.core.Project.getProjectDependencies(project, "external", self.__updateRepositories)
        for project in result:
            
            # Append to session list
            self.__projects.append(project)

            # Import library methods
            libraryPath = os.path.join(project.getPath(), "jasylibrary.py")
            if os.path.exists(libraryPath):
                self.loadLibrary(project.getName(), libraryPath, doc="Library of project %s" % project.getName())

            # Import project defined fields which might be configured using "activateField()"
            fields = project.getFields()
            for name in fields:
                entry = fields[name]

                if name in self.__fields:
                    raise UserError("Field '%s' was already defined!" % (name))

                if "check" in entry:
                    check = entry["check"]
                    if check in ["Boolean", "String", "Number"] or type(check) == list:
                        pass
                    else:
                        raise UserError("Unsupported check: '%s' for field '%s'" % (check, name))
                    
                self.__fields[name] = entry



    def loadLibrary(self, objectName, fileName, encoding="utf-8", doc=None):
        """
        Creates a new object inside the user API (jasyscript.py) with the given name 
        containing all @share'd functions and fields loaded from the given file.
        """

        if objectName in self.__scriptEnvironment:
            raise UserError("Could not import library %s as the object name %s is already used." % (fileName, objectName))

        # Create internal class object for storing shared methods
        class Shared(object): pass
        exportedModule = Shared()
        exportedModule.__doc__ = doc or "Imported from %s" % os.path.relpath(fileName, os.getcwd())
        counter = 0

        # Method for being used as a decorator to share methods to the outside
        def share(func):
            nonlocal counter
            setattr(exportedModule, func.__name__, func)
            counter += 1

            return func

        # Execute given file. Using clean new global environment
        # but add additional decorator for allowing to define shared methods
        # and the session object (self).
        code = open(fileName, "r", encoding=encoding).read()
        exec(compile(code, os.path.abspath(fileName), "exec"), {"share" : share, "session" : self})

        # Export destination name as global    
        Console.debug("Importing %s shared methods under %s...", counter, objectName)
        self.__scriptEnvironment[objectName] = exportedModule

        return counter
        
        
    def getProjects(self):
        """
        Returns all currently registered projects. 
        Injects locale project when current permutation has configured a locale.
        """

        project = self.getCurrentLocaleProject()
        if project:
            return self.__projects + [project]

        return self.__projects
        
        
    def getProjectByName(self, name):
        """Returns a project by its name"""
        
        for project in self.__projects:
            if project.getName() == name:
                return project
                
        return None
        
        
    def getRelativePath(self, project):
        """Returns the relative path of any project to the main project"""
        
        mainPath = self.__projects[0].getPath()
        projectPath = project.getPath()
        
        return os.path.relpath(projectPath, mainPath)
        
        
    def getMain(self):
        """
        Returns the main project which is the first project added to the
        session and the one with the highest priority.
        """

        if self.__projects:
            return self.__projects[0]
        else:
            return None



    #
    # Support for fields
    # Fields allow to inject data from the build into the running application
    #
    
    def setLocales(self, locales, default=None):
        """
        Store locales as a special built-in field with optional default value
        """

        self.__fields["locale"] = {
            "values" : locales,
            "default" : default or locales[0],
            "detect" : "core.detect.Locale"
        }


    def setDefaultLocale(self, locale):
        """
        Sets the default locale
        """

        if not "locale" in self.__fields:
            raise UserError("Define locales first!")

        self.__fields["locale"]["default"] = locale


    def setField(self, name, value):
        """
        Statically configure the value of the given field.
        
        This field is just injected into Permutation data and used for permutations, but as
        it only holds a single value all alternatives paths are removed/ignored.
        """
        
        if not name in self.__fields:
            raise Exception("Unsupported field (not defined by any project): %s" % name)

        entry = self.__fields[name]
        
        # Replace current value with single value
        entry["values"] = [value]
        
        # Additonally set the default
        entry["default"] = value

        # Delete detection if configured by the project
        if "detect" in entry:
            del entry["detect"]


    def permutateField(self, name, values=None, detect=None, default=None):
        """
        Adds the given key/value pair to the session for permutation usage.
        
        It supports an optional test. A test is required as soon as there is
        more than one value available. The detection method and values are typically 
        already defined by the project declaring the key/value pair.
        """
        
        if not name in self.__fields:
            raise Exception("Unsupported field (not defined by any project): %s" % name)

        entry = self.__fields[name]
            
        if values:
            if type(values) != list:
                values = [values]

            entry["values"] = values

            # Verifying values from build script with value definition in project manifests
            if "check" in entry:
                check = entry["check"]
                for value in values:
                    if check == "Boolean":
                        if type(value) == bool:
                            continue
                    elif check == "String":
                        if type(value) == str:
                            continue
                    elif check == "Number":
                        if type(value) in (int, float):
                            continue
                    else:
                        if value in check:
                            continue

                    raise Exception("Unsupported value %s for %s" % (value, name))
                    
            if default is not None:
                entry["default"] = default
                    
        elif "check" in entry and entry["check"] == "Boolean":
            entry["values"] = [True, False]
            
        elif "check" in entry and type(entry["check"]) == list:
            entry["values"] = entry["check"]
            
        elif "default" in entry:
            entry["values"] = [entry["default"]]
            
        else:
            raise Exception("Could not permutate field: %s! Requires value list for non-boolean fields which have no defaults." % name)

        # Store class which is responsible for detection (overrides data from project)
        if detect:
            if not self.getClass(detect):
                raise Exception("Could not permutate field: %s! Unknown detect class %s." % detect)
                
            entry["detect"] = detect
        
        
    def getFieldDetectionClasses(self):
        """
        Returns all JavaScript classes relevant by current field setups to detect all 
        relevant values for the given fields.
        """

        result = set()

        fields = self.__fields
        for name in fields:
            value = fields[name]
            if "detect" in value:
                result.add(value["detect"])

        return result


    def exportFields(self):
        """
        Converts data from values to a compact data structure for being used to 
        compute a checksum in JavaScript.

        Export structures:
        1. [ name, 1, test, [value1, ...] ]
        2. [ name, 2, value ]
        3. [ name, 3, test, default? ]
        """

        export = []
        for key in sorted(self.__fields):
            source = self.__fields[key]
            
            content = []
            content.append("'%s'" % key)
            
            # We have available values to permutate for
            if "values" in source:
                values = source["values"]
                if "detect" in source and len(values) > 1:
                    # EXPORT STRUCT 1
                    content.append("1")
                    content.append(source["detect"])

                    if "default" in source:
                        # Make sure that default value is first in
                        values = values[:]
                        values.remove(source["default"])
                        values.insert(0, source["default"])
                    
                    content.append(json.dumps(values))
            
                else:
                    # EXPORT STRUCT 2
                    content.append("2")

                    if "default" in source:
                        content.append(json.dumps(source["default"]))
                    else:
                        content.append(json.dumps(values[0]))

            # Has no relevance for permutation, just insert the test
            else:
                if "detect" in source:
                    # EXPORT STRUCT 3
                    content.append("3")

                    # Add detection class
                    content.append(source["detect"])
                    
                    # Add default value if available
                    if "default" in source:
                        content.append(json.dumps(source["default"]))
                
                elif "default" in source:
                    # EXPORT STRUCT 2
                    content.append("2")
                    content.append(json.dumps(source["default"]))

                else:
                    # Has no detection and no permutation. Ignore it completely
                    continue
                
            export.append("[%s]" % ", ".join(content))
            
        if export:
            return "[%s]" % ", ".join(export)

        return None
    
    
    
    
    #
    # Translation Support
    #
    
    def getAvailableTranslations(self):
        """ 
        Returns a set of all available translations 
        
        This is the sum of all projects so even if only one 
        project supports "fr_FR" then it will be included here.
        """
        
        supported = set()
        for project in self.__projects:
            supported.update(project.getTranslations().keys())
            
        return supported
    
    
    def __generateTranslationBundle(self):
        """ 
        Returns a translation object for the given language containing 
        all relevant translation files for the current project set. 
        """

        language = self.getCurrentPermutation().get("locale")
        if language is None:
            return None

        if language in self.__translationBundles:
            return self.__translationBundles[language]

        Console.info("Creating translation bundle: %s", language)
        Console.indent()

        # Initialize new Translation object with no project assigned
        # This object is used to merge all seperate translation instances later on.
        combined = jasy.item.Translation.TranslationItem(None, id=language)
        relevantLanguages = self.__expandLanguage(language)

        # Loop structure is build to prefer finer language matching over project priority
        for currentLanguage in reversed(relevantLanguages):
            for project in self.__projects:
                for translation in project.getTranslations().values():
                    if translation.getLanguage() == currentLanguage:
                        Console.debug("Adding %s entries from %s @ %s...", len(translation.getTable()), currentLanguage, project.getName())
                        combined += translation

        Console.debug("Combined number of translations: %s", len(combined.getTable()))
        Console.outdent()

        self.__translationBundles[language] = combined
        return combined


    def __expandLanguage(self, language):
        """Expands the given language into a list of languages being used in priority order (highest first)"""

        # Priority Chain: 
        # de_DE => de => C (default language) => code

        all = [language]
        if "_" in language:
            all.append(language[:language.index("_")])
        all.append("C")

        return all



    #
    # State Handling / Looping
    #

    def __generatePermutations(self):
        """
        Combines all values to a set of permutations.
        These define all possible combinations of the configured settings
        """

        fields = self.__fields
        values = { key:fields[key]["values"] for key in fields if "values" in fields[key] }

        # Thanks to eumiro via http://stackoverflow.com/questions/3873654/combinations-from-dictionary-with-list-values-using-python
        names = sorted(values)
        combinations = [dict(zip(names, prod)) for prod in itertools.product(*(values[name] for name in names))]
        permutations = [jasy.core.Permutation.getPermutation(combi) for combi in combinations]

        return permutations


    def permutate(self):
        """ Generator method for permutations for improving output capabilities """
        
        Console.info("Processing permutations...")
        Console.indent()
        
        permutations = self.__generatePermutations()
        length = len(permutations)
        
        for pos, current in enumerate(permutations):
            Console.info("Permutation %s/%s:" % (pos+1, length))
            Console.indent()

            self.__currentPermutation = current
            self.__currentTranslationBundle = self.__generateTranslationBundle()
            
            yield current
            Console.outdent()

        Console.outdent()

        self.__currentPermutation = None
        self.__currentTranslationBundle = None


    def getCurrentPermutation(self):
        """Returns current permutation object (useful during looping through permutations via permutate())."""

        return self.__currentPermutation


    def resetCurrentPermutation(self):
        """Resets the current permutation object."""

        self.__currentPermutation = None


    def setStaticPermutation(self, **argv):
        """
        Sets current permutation to a static permutation which contains all values hardly wired to 
        static values using setField() or given via additional named parameters.
        """

        combi = {}

        for name in self.__fields:
            entry = self.__fields[name]
            if not "detect" in entry:
                combi[name] = entry["default"]

        for name in argv:
            combi[name] = argv[name]

        if not combi:
            self.__currentPermutation = None
            return None

        permutation = jasy.core.Permutation.getPermutation(combi)
        self.__currentPermutation = permutation

        return permutation


    def getCurrentTranslationBundle(self):
        """Returns the current translation bundle (useful during looping through permutations via permutate())."""
        
        return self.__currentTranslationBundle


    def getCurrentLocale(self):
        """Returns the current locale as defined in current permutation"""

        permutation = self.getCurrentPermutation()
        if permutation:
            locale = permutation.get("locale")
            if locale:
                return locale

        return None


    def getCurrentLocaleProject(self, update=False):
        """
        Returns a locale project for the currently configured locale. 
        Returns None if locale is not set to a valid value.
        """

        locale = self.getCurrentLocale()
        if not locale:
            return None

        path = os.path.abspath(os.path.join(".jasy", "locale", locale))
        if not os.path.exists(path) or update:
            jasy.core.Locale.LocaleParser(locale).export(path)

        return jasy.core.Project.getProjectFromPath(path)


    def setCurrentPrefix(self, path):
        """Interface for Task class to configure the current prefix to use"""

        if path is None:
            self.__currentPrefix = None
            Console.debug("Resetting prefix to working directory")
        else:
            self.__currentPrefix = os.path.normpath(os.path.abspath(os.path.expanduser(path)))
            Console.debug("Setting prefix to: %s" % self.__currentPrefix)
        

    def getCurrentPrefix(self):
        """
        Returns the current prefix which should be used to generate/copy new files 
        in the current task. This somewhat sandboxes each task automatically to mostly
        only create files in a task specific folder.
        """

        return self.__currentPrefix


    def expandFileName(self, fileName):
        """
        Replaces placeholders inside the given filename and returns the result. 
        The placeholders are based on the current state of the session.

        These are the currently supported placeholders:

        - $prefix: Current prefix of task
        - $permutation: SHA1 checksum of current permutation
        - $locale: Name of current locale e.g. de_DE
        """

        if self.__currentPrefix:
            fileName = fileName.replace("$prefix", self.__currentPrefix)

        if self.__currentPermutation:
            fileName = fileName.replace("$permutation", self.__currentPermutation.getChecksum())

            locale = self.__currentPermutation.get("locale")
            if locale:
                fileName = fileName.replace("$locale", locale)

        return fileName



########NEW FILE########
__FILENAME__ = Text
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

import re


#
# MARKDOWN TO HTML
#

try:
    import misaka

    misakaExt = misaka.EXT_AUTOLINK | misaka.EXT_NO_INTRA_EMPHASIS | misaka.EXT_FENCED_CODE
    misakaRender = misaka.HTML_SKIP_STYLE | misaka.HTML_SMARTYPANTS
    supportsMarkdown = True

except:
    supportsMarkdown = False

def markdownToHtml(markdownStr):
    """
    Converts Markdown to HTML. Supports GitHub's fenced code blocks, 
    auto linking and typographic features by SmartyPants.
    """

    return misaka.html(markdownStr, misakaExt, misakaRender)


#
# HIGHLIGHT CODE BLOCKS
#

try:
    from pygments import highlight
    from pygments.formatters import HtmlFormatter
    from pygments.lexers import get_lexer_by_name

    # By http://misaka.61924.nl/#toc_3
    codeblock = re.compile(r'<pre(?: lang="([a-z0-9]+)")?><code(?: class="([a-z0-9]+).*?")?>(.*?)</code></pre>', re.IGNORECASE | re.DOTALL)

    supportsHighlighting = True

except ImportError:

    supportsHighlighting = False

def highlightCodeBlocks(html, tabsize=2, defaultlang="javascript"):
    """
    Patches 'code' elements in HTML to apply HTML based syntax highlighting. Automatically
    chooses the matching language detected via a CSS class of the 'code' element.
    """

    def unescape(html):
        html = html.replace('&lt;', '<')
        html = html.replace('&gt;', '>')
        html = html.replace('&amp;', '&')
        html = html.replace('&quot;', '"')
        return html.replace('&#39;', "'")

    def replace(match):
        language, classname, code = match.groups()
        if language is None:
            language = classname if classname else defaultlang
    
        lexer = get_lexer_by_name(language, tabsize=tabsize)
        formatter = HtmlFormatter(linenos="table")
    
        code = unescape(code)

        # for some reason pygments escapes our code once again so we need to reverse it twice
        return unescape(highlight(code, lexer, formatter))
    
    return codeblock.sub(replace, html)

########NEW FILE########
__FILENAME__ = Types
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

class CaseInsensitiveDict(dict):
    """
    A case-insensitive dict subclass.
    Each key is changed on entry to str(key).title().
    """
    
    def __getitem__(self, key):
        return dict.__getitem__(self, str(key).title())
    
    def __setitem__(self, key, value):
        dict.__setitem__(self, str(key).title(), value)
    
    def __delitem__(self, key):
        dict.__delitem__(self, str(key).title())
    
    def __contains__(self, key):
        return dict.__contains__(self, str(key).title())
    
    def get(self, key, default=None):
        return dict.get(self, str(key).title(), default)
    
    if hasattr({}, 'has_key'):
        def has_key(self, key):
            return dict.has_key(self, str(key).title())
    
    def update(self, E):
        for k in E.keys():
            self[str(k).title()] = E[k]
    
    def fromkeys(cls, seq, value=None):
        newdict = cls()
        for k in seq:
            newdict[str(k).title()] = value
        return newdict
    fromkeys = classmethod(fromkeys)
    
    def setdefault(self, key, x=None):
        key = str(key).title()
        try:
            return self[key]
        except KeyError:
            self[key] = x
            return x
    
    def pop(self, key, default):
        return dict.pop(self, str(key).title(), default)
########NEW FILE########
__FILENAME__ = Util
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

import re, os, hashlib, tempfile, subprocess, sys, shlex

import jasy.core.Console as Console


def executeCommand(args, failmsg=None, path=None):
    """
    Executes the given process and outputs failmsg when errors happen.
    Returns the combined shell output (stdout and strerr combined).

    :param args: 
    :type args: str or list
    :param failmsg: Message for exception when command fails
    :type failmsg: str
    :param path: Directory path where the command should be executed
    :type path: str
    :raise Exception: Raises an exception whenever the shell command fails in execution
    """

    if type(args) == str:
        args = shlex.split(args)

    prevpath = os.getcwd()

    # Execute in custom directory
    if path:
        path = os.path.abspath(os.path.expanduser(path))
        os.chdir(path)

    Console.debug("Executing command: %s", " ".join(args))
    Console.indent()
    
    # Using shell on Windows to resolve binaries like "git"
    output = tempfile.TemporaryFile(mode="w+t")
    returnValue = subprocess.call(args, stdout=output, stderr=output, shell=sys.platform == "win32")
        
    output.seek(0)
    result = output.read().strip("\n\r")
    output.close()

    # Change back to previous path
    os.chdir(prevpath)

    if returnValue != 0:
        raise Exception("Error during executing shell command: %s (%s)" % (failmsg, result))
    
    for line in result.splitlines():
        Console.debug(line)
    
    Console.outdent()
    
    return result


def getKey(data, key, default=None):
    """
    Returns the key from the data if available or the given default

    :param data: Data structure to inspect
    :type data: dict
    :param key: Key to lookup in dictionary
    :type key: str
    :param default: Default value to return when key is not set
    :type default: any
    """

    if key in data:
        return data[key]
    else:
        return default


__REGEXP_DASHES = re.compile(r"\-+([\S]+)?")
__REGEXP_HYPHENATE = re.compile(r"([A-Z])")

def __camelizeHelper(match):
    result = match.group(1)
    return result[0].upper() + result[1:].lower()

def __hyphenateHelper(match):
    return "-%s" % match.group(1).lower()
    
def camelize(str):
    """
    Returns a camelized version of the incoming string: foo-bar-baz => fooBarBaz

    :param str: Input string
    """
    return __REGEXP_DASHES.sub(__camelizeHelper, str)

def hyphenate(str):
    """Returns a hyphenated version of the incoming string: fooBarBaz => foo-bar-baz

    :param str: Input string
    """

    return __REGEXP_HYPHENATE.sub(__hyphenateHelper, str)    


########NEW FILE########
__FILENAME__ = Context
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

"""Global environment which is used by jasyscript.py files"""

# Session
from jasy.env.State import session

# Modules
import jasy.core.Console as Console
import jasy.env.Task as Task
import jasy.vcs.Repository as Repository

# Classes
from jasy.core.OutputManager import OutputManager
from jasy.core.FileManager import FileManager
from jasy.asset.Manager import AssetManager
from jasy.asset.SpritePacker import SpritePacker
from jasy.js.Resolver import Resolver
from jasy.js.api.Writer import ApiWriter
from jasy.http.Server import Server

# Commands (be careful with these, prefer modules and classes)
from jasy.env.Task import task

# Create config object
import jasy.core.Config as Config
config = Config.Config()
config.__doc__ = "Auto initialized config object based on project's jasyscript.yaml/json"
config.loadValues("jasyscript", optional=True)


@task
def about():
    """Print outs the Jasy about page"""

    import jasy

    jasy.info()

    from jasy.env.Task import getCommand

    Console.info("Command: %s", getCommand())
    Console.info("Version: %s", jasy.__version__)


@task
def help():
    """Shows this help screen"""

    import jasy

    jasy.info()

    print(Console.colorize(Console.colorize("Usage", "underline"), "bold"))
    print("  $ jasy [<options...>] <task1> [<args...>] [<task2> [<args...>]]")

    print()
    print(Console.colorize(Console.colorize("Global Options", "underline"), "bold"))
    Task.getOptions().printOptions()

    print()
    print(Console.colorize(Console.colorize("Available Tasks", "underline"), "bold"))
    Task.printTasks()

    print()


@task
def doctor():
    """Checks Jasy environment and prints offers support for installing missing packages"""

    # This is a placeholder task to show up in the jasy task list
    # The handling itself is directly implemented in "bin/jasy"
    pass


@task
def create(name="myproject", origin=None, originVersion=None, skeleton=None, destination=None, **argv):
    """Creates a new project based on a local or remote skeleton"""

    import jasy.core.Create as Create
    return Create.create(name, origin, originVersion, skeleton, destination, session, **argv)


@task
def showapi():
    """Shows the official API available in jasyscript.py"""

    from jasy.core.Inspect import generateApi
    Console.info(generateApi(__api__))



########NEW FILE########
__FILENAME__ = State
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

"""This module is used to pass a single session instance around to different modules"""

import jasy.core.Session as Session

__all__ = ["session"]

session = Session.Session()
session.__doc__ = """Auto initialized session object based on jasy.core.Session"""


########NEW FILE########
__FILENAME__ = Task
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

"""
Tasks are basically functions with some managment code allow them to run in jasyscript.py
"""

import types, os, sys, inspect, subprocess

import jasy.core.Console as Console

from jasy.env.State import session
import jasy.core.Util as Util
from jasy import UserError

__all__ = ["task", "executeTask", "runTask", "printTasks", "setCommand", "setOptions", "getOptions"]

class Task:

    __slots__ = ["func", "name", "curry", "availableArgs", "hasFlexArgs", "__doc__", "__name__"]

    
    def __init__(self, func, **curry):
        """Creates a task bound to the given function and currying in static parameters"""

        self.func = func
        self.name = func.__name__

        self.__name__ = "Task: %s" % func.__name__

        # Circular reference to connect both, function and task
        func.task = self

        # The are curried in arguments which are being merged with 
        # dynamic command line arguments on each execution
        self.curry = curry

        # Extract doc from function and attach it to the task
        self.__doc__ = inspect.getdoc(func)

        # Analyse arguments for help screen
        result = inspect.getfullargspec(func)        
        self.availableArgs = result.args
        self.hasFlexArgs = result.varkw is not None

        # Register task globally
        addTask(self)
        

    def __call__(self, **kwargs):
        
        merged = {}
        merged.update(self.curry)
        merged.update(kwargs)


        #
        # SUPPORT SOME DEFAULT FEATURES CONTROLLED BY TASK PARAMETERS
        #
        
        # Allow overriding of prefix via task or cmdline parameter.
        # By default use name of the task (no prefix for cleanup tasks)
        if "prefix" in merged:
            session.setCurrentPrefix(merged["prefix"])
            del merged["prefix"]
        elif "clean" in self.name:
            session.setCurrentPrefix(None)
        else:
            session.setCurrentPrefix(self.name)
        

        #
        # EXECUTE ATTACHED FUNCTION
        #

        Console.header(self.__name__)

        # Execute internal function
        return self.func(**merged)


    def __repr__(self):
        return "Task: " + self.__name__




def task(*args, **kwargs):
    """ Specifies that this function is a task. """
    
    if len(args) == 1:

        func = args[0]

        if isinstance(func, Task):
            return func

        elif isinstance(func, types.FunctionType):
            return Task(func)

        # Compat to old Jasy 0.7.x task declaration
        elif type(func) is str:
            return task(**kwargs)

        else:
            raise UserError("Invalid task")
    
    else:

        def wrapper(func):
            return Task(func, **kwargs)
            
        return wrapper



# Local task managment
__taskRegistry = {}

def addTask(task):
    """Registers the given task with its name"""
    
    if task.name in __taskRegistry:
        Console.debug("Overriding task: %s" % task.name)
    else:
        Console.debug("Registering task: %s" % task.name)
        
    __taskRegistry[task.name] = task

def executeTask(taskname, **kwargs):
    """Executes the given task by name with any optional named arguments"""

    if taskname in __taskRegistry:
        try:
            camelCaseArgs = { Util.camelize(key) : kwargs[key] for key in kwargs }
            __taskRegistry[taskname](**camelCaseArgs)
        except UserError as err:
            raise
        except:
            Console.error("Unexpected error! Could not finish task %s successfully!" % taskname)
            raise
    else:
        raise UserError("No such task: %s" % taskname)

def printTasks(indent=16):
    """Prints out a list of all avaible tasks and their descriptions"""
    
    for name in sorted(__taskRegistry):
        obj = __taskRegistry[name]

        formattedName = name
        if obj.__doc__:
            space = (indent - len(name)) * " "
            print("    %s: %s%s" % (formattedName, space, Console.colorize(obj.__doc__, "magenta")))
        else:
            print("    %s" % formattedName)

        if obj.availableArgs or obj.hasFlexArgs:
            text = ""
            if obj.availableArgs:
                text += Util.hyphenate("--%s <var>" % " <var> --".join(obj.availableArgs))

            if obj.hasFlexArgs:
                if text:
                    text += " ..."
                else:
                    text += "--<name> <var>"

            print("      %s" % (Console.colorize(text, "grey")))


# Jasy reference for executing remote tasks
__command = None
__options = None

def setCommand(cmd):
    """Sets the jasy command which should be used to execute tasks with runTask()"""

    global __command
    __command = cmd

def getCommand():
    """Returns the "jasy" command which is currently executed."""

    global __command
    return __command

def setOptions(options):
    """Sets currently configured command line options. Mainly used for printing help screens."""

    global __options
    __options = options

def getOptions():
    """Returns the options as passed to the jasy command. Useful for printing all command line arguments."""

    global __options
    return __options

def runTask(project, task, **kwargs):
    """
    Executes the given task of the given projects. 
    
    This happens inside a new sandboxed session during which the 
    current session is paused/resumed automatically.
    """

    remote = session.getProjectByName(project)
    if remote is not None:
        remotePath = remote.getPath()
        remoteName = remote.getName()
    elif os.path.isdir(project):
        remotePath = project
        remoteName = os.path.basename(project)
    else:
        raise UserError("Unknown project or invalid path: %s" % project)

    Console.info("Running %s of project %s...", Console.colorize(task, "bold"), Console.colorize(remoteName, "bold"))

    # Pauses this session to allow sub process fully accessing the same projects
    session.pause()

    # Build parameter list from optional arguments
    params = ["--%s=%s" % (key, kwargs[key]) for key in kwargs]
    if not "prefix" in kwargs:
        params.append("--prefix=%s" % session.getCurrentPrefix())

    # Full list of args to pass to subprocess
    args = [__command, task] + params

    # Change into sub folder and execute jasy task
    oldPath = os.getcwd()
    os.chdir(remotePath)
    returnValue = subprocess.call(args, shell=sys.platform == "win32")
    os.chdir(oldPath)

    # Resumes this session after sub process was finished
    session.resume()

    # Error handling
    if returnValue != 0:
        raise UserError("Executing of sub task %s from project %s failed" % (task, project))




########NEW FILE########
__FILENAME__ = Request
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

import shutil, json, base64, os, re, random, sys, mimetypes, http.client, urllib.parse, hashlib
import jasy.core.Console as Console

__all__ = ["requestUrl", "uploadData"]


#
# Generic HTTP support
#

def requestUrl(url, content_type="text/plain", headers=None, method="GET", port=None, body="", user=None, password=None):
    """Generic HTTP request wrapper with support for basic authentification and automatic parsing of response content"""
    
    Console.info("Opening %s request to %s..." % (method, url))

    parsed = urllib.parse.urlparse(url)
    
    if parsed.scheme== "http":
        request = http.client.HTTPConnection(parsed.netloc)
    elif parsed.scheme== "https":
        request = http.client.HTTPSConnection(parsed.netloc)
    else:
        raise Exception("Unsupported url: %s" % url)
    
    if parsed.query:
        request.putrequest(method, parsed.path + "?" + parsed.query)
    else:
        request.putrequest(method, parsed.path)
    
    request.putheader("Content-Type", content_type)
    request.putheader("Content-Length", str(len(body)))

    if user is not None and password is not None:
        auth = "Basic %s" % base64.b64encode(("%s:%s" % (user, password)).encode("utf-8")).decode("utf-8")
        request.putheader("Authorization", auth)
        
    request.endheaders()
    
    if body:
        Console.info("Sending data (%s bytes)..." % len(body))
    else:
        Console.info("Sending request...")

    Console.indent()

    request.send(body)

    response = request.getresponse()
    
    res_code = int(response.getcode())
    res_headers = dict(response.getheaders())
    res_content = response.read()
    res_success = False
    
    if res_code >= 200 and res_code <= 300:
        Console.debug("HTTP Success!")
        res_success = True
    else:
        Console.error("HTTP Failure Code: %s!", res_code)
        
    if "Content-Type" in res_headers:
        res_type = res_headers["Content-Type"]
        
        if ";" in res_type:
            res_type = res_type.split(";")[0]
            
        if res_type in ("application/json", "text/html", "text/plain"):
            res_content = res_content.decode("utf-8")

        if res_type == "application/json":
            res_content = json.loads(res_content)
            
            if "error" in res_content:
                Console.error("Error %s: %s", res_content["error"], res_content["reason"])
            elif "reason" in res_content:
                Console.info("Success: %s" % res_content["reason"])
                
    Console.outdent()
    
    return res_success, res_headers, res_content




#
# Multipart Support
#

def uploadData(url, fields, files, user=None, password=None, method="POST"):
    """Easy wrapper for uploading content via HTTP multi part"""
    
    content_type, body = encode_multipart_formdata(fields, files)
    return requestUrl(url, body=body, content_type=content_type, method=method, user=user, password=password)


def choose_boundary():
    """Return a string usable as a multipart boundary."""
    
    # Follow IE and Firefox
    nonce = "".join([str(random.randint(0, sys.maxsize-1)) for i in (0,1,2)])
    return "-"*27 + nonce


def get_content_type(filename):
    """Figures out the content type of the given file"""
    
    return mimetypes.guess_type(filename)[0] or "application/octet-stream"


def encode_multipart_formdata(fields, files):
    """Encodes given fields and files to a multipart ready HTTP body"""

    # Choose random boundary
    boundary = choose_boundary()

    # Build HTTP content type with generated boundary
    content_type = "multipart/form-data; boundary=%s" % boundary
    
    # Join all fields and files into one collection of lines
    lines = []

    for (key, value) in fields:
        lines.append("--" + boundary)
        lines.append('Content-Disposition: form-data; name="' + key + '"')
        lines.append("")
        lines.append(value)

    for (key, filename, value) in files:
        lines.append("--" + boundary)
        lines.append('Content-Disposition: form-data; name="' + key + '"; filename="' + filename + '"')
        lines.append('Content-Type: ' + get_content_type(filename))
        lines.append("")
        lines.append(value)
        
    lines.append("--" + boundary + "--")
    lines.append("")
    
    # Encode and join all lines as ascii
    bytelines = [line if isinstance(line, bytes) else line.encode("ascii") for line in lines]
    body = "\r\n".encode("ascii").join(bytelines)
    
    return content_type, body


########NEW FILE########
__FILENAME__ = Server
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

import os, logging, base64, json, requests, cherrypy, locale
from collections import namedtuple

import jasy.core.Cache as Cache
import jasy.core.Console as Console

from jasy.core.Types import CaseInsensitiveDict
from jasy.core.Util import getKey
from jasy import __version__ as jasyVersion

Result = namedtuple('Result', ['headers', 'content', 'status_code'])

# Disable logging HTTP request being created
logging.getLogger("requests").setLevel(logging.WARNING)


#
# UTILITIES
#

def enableCrossDomain():
    # See also: https://developer.mozilla.org/En/HTTP_Access_Control
    
    # Allow requests from all locations
    cherrypy.response.headers["Access-Control-Allow-Origin"] = "*"
   
    # Allow all methods supported by urlfetch
    cherrypy.response.headers["Access-Control-Allow-Methods"] = "GET, POST, HEAD, PUT, DELETE"
    
    # Allow cache-control and our custom headers
    cherrypy.response.headers["Access-Control-Allow-Headers"] = "Cache-Control, X-Proxy-Authorization, X-Requested-With"    
    
    # Cache allowence for cross domain for 7 days
    cherrypy.response.headers["Access-Control-Max-Age"] = "604800"


def findIndex(path):
    all = ["index.html", "index.php"]
    for candidate in all:
        rel = os.path.join(path, candidate)
        if os.path.exists(rel):
            return candidate
            
    return None

def noBodyProcess():
    cherrypy.request.process_request_body = False

cherrypy.tools.noBodyProcess = cherrypy.Tool('before_request_body', noBodyProcess)


#
# ROUTERS
#

class Proxy(object):
    
    def __init__(self, id, config):
        self.id = id
        self.config = config
        self.host = getKey(config, "host")
        self.auth = getKey(config, "auth")
        
        self.enableDebug = getKey(config, "debug", False)
        self.enableMirror = getKey(config, "mirror", False)
        self.enableOffline = getKey(config, "offline", False)

        if self.enableMirror:
            self.mirror = Cache.Cache(os.getcwd(), ".jasy/mirror-%s" % self.id, hashkeys=True)

        Console.info('Proxy "%s" => "%s" [debug:%s|mirror:%s|offline:%s]', self.id, self.host, self.enableDebug, self.enableMirror, self.enableOffline)
        
        
    # These headers will be blocked between header copies
    __blockHeaders = CaseInsensitiveDict.fromkeys([
        "content-encoding", 
        "content-length", 
        "connection", 
        "keep-alive", 
        "proxy-authenticate", 
        "proxy-authorization", 
        "transfer-encoding", 
        "remote-addr", 
        "host"
    ])
    
    
    @cherrypy.expose
    @cherrypy.tools.noBodyProcess()
    def default(self, *args, **query):
        """
        This method returns the content of existing files on the file system.
        Query string might be used for cache busting and are otherwise ignored.
        """
        
        url = self.config["host"] + "/".join(args)
        result = None
        body = None
        
        # Try using offline mirror if feasible
        if self.enableMirror and cherrypy.request.method == "GET":
            mirrorId = "%s[%s]" % (url, json.dumps(query, separators=(',',':'), sort_keys=True))
            result = self.mirror.read(mirrorId)
            if result is not None and self.enableDebug:
                Console.info("Mirrored: %s" % url)
            
        if cherrypy.request.method in ("POST", "PUT"):
            body = cherrypy.request.body.fp.read()
         
        # Check if we're in forced offline mode
        if self.enableOffline and result is None:
            Console.info("Offline: %s" % url)
            raise cherrypy.NotFound(url)
        
        # Load URL from remote server
        if result is None:

            # Prepare headers
            headers = CaseInsensitiveDict()
            for name in cherrypy.request.headers:
                if not name in self.__blockHeaders:
                    headers[name] = cherrypy.request.headers[name]
            
            # Load URL from remote host
            try:
                if self.enableDebug:
                    Console.info("Requesting: %s", url)
                    
                # Apply headers for basic HTTP authentification
                if "X-Proxy-Authorization" in headers:
                    headers["Authorization"] = headers["X-Proxy-Authorization"]
                    del headers["X-Proxy-Authorization"]                
                    
                # Add headers for different authentification approaches
                if self.auth:
                    
                    # Basic Auth
                    if self.auth["method"] == "basic":
                        headers["Authorization"] = b"Basic " + base64.b64encode(("%s:%s" % (self.auth["user"], self.auth["password"])).encode("ascii"))
                    
                # We disable verifícation of SSL certificates to be more tolerant on test servers
                result = requests.request(cherrypy.request.method, url, params=query, headers=headers, data=body, verify=False)
                
            except Exception as err:
                if self.enableDebug:
                    Console.info("Request failed: %s", err)
                    
                raise cherrypy.HTTPError(403)

            # Storing result into mirror
            if self.enableMirror and cherrypy.request.method == "GET" and result.status_code == 200:

                # Wrap result into mirrorable entry
                resultCopy = Result(result.headers, result.content, result.status_code)
                self.mirror.store(mirrorId, resultCopy)
        

        # Copy response headers to our reponse
        for name in result.headers:
            if not name.lower() in self.__blockHeaders:
                cherrypy.response.headers[name] = result.headers[name]

        # Set the proxyed reply status to the response status
        cherrypy.response.status = result.status_code

        # Append special header to all responses
        cherrypy.response.headers["X-Jasy-Version"] = jasyVersion
        
        # Enable cross domain access to this server
        enableCrossDomain()

        return result.content
        
        
class Static(object):
    
    def __init__(self, id, config, mimeTypes=None):
        self.id = id
        self.config = config
        self.mimeTypes = mimeTypes
        self.root = getKey(config, "root", ".")
        self.enableDebug = getKey(config, "debug", False)

        Console.info('Static "%s" => "%s" [debug:%s]', self.id, self.root, self.enableDebug)
        
    @cherrypy.expose
    def default(self, *args, **query):
        """
        This method returns the content of existing files on the file system.
        Query string might be used for cache busting and are otherwise ignored.
        """
        
        # Append special header to all responses
        cherrypy.response.headers["X-Jasy-Version"] = jasyVersion
        
        # Enable cross domain access to this server
        enableCrossDomain()
        
        # When it's a file name in the local folder... load it
        if args:
            path = os.path.join(*args)
        else:
            path = "index.html"
        
        path = os.path.join(self.root, path)
        
        # Check for existance first
        if os.path.isfile(path):
            if self.enableDebug:
                Console.info("Serving file: %s", path)

            # Default content type to autodetection by Python mimetype API            
            contentType = None

            # Support overriding by extensions
            extension = os.path.splitext(path)[1]
            if extension:
                extension = extension.lower()[1:]
                if extension in self.mimeTypes:
                    contentType = self.mimeTypes[extension] + "; charset=" + locale.getpreferredencoding()

            return cherrypy.lib.static.serve_file(os.path.abspath(path), content_type=contentType)
            
        # Otherwise return a classic 404
        else:
            if self.enableDebug:
                Console.warn("File at location %s not found at %s!", path, os.path.abspath(path))
            
            raise cherrypy.NotFound(path)
        
# 
# ADDITIONAL MIME TYPES
# 

additionalContentTypes = {
    "js": "application/javascript",
    "jsonp": "application/javascript",
    "json": "application/json",
    "oga": "audio/ogg",
    "ogg": "audio/ogg",
    "m4a": "audio/mp4",
    "f4a": "audio/mp4",
    "f4b": "audio/mp4",
    "ogv": "video/ogg",
    "mp4": "video/mp4",
    "m4v": "video/mp4",
    "f4v": "video/mp4",
    "f4p": "video/mp4",
    "webm": "video/webm",
    "flv": "video/x-flv",
    "svg": "image/svg+xml",
    "svgz": "image/svg+xml",
    "eot": "application/vnd.ms-fontobject",
    "ttf": "application/x-font-ttf",
    "ttc": "application/x-font-ttf",
    "otf": "font/opentype",
    "woff": "application/x-font-woff",
    "ico": "image/x-icon",
    "webp": "image/webp",
    "appcache": "text/cache-manifest",
    "manifest": "text/cache-manifest",
    "htc": "text/x-component",
    "rss": "application/xml",
    "atom": "application/xml",
    "xml": "application/xml",
    "rdf": "application/xml",
    "crx": "application/x-chrome-extension",
    "oex": "application/x-opera-extension",
    "xpi": "application/x-xpinstall",
    "safariextz": "application/octet-stream",
    "webapp": "application/x-web-app-manifest+json",
    "vcf": "text/x-vcard",
    "swf": "application/x-shockwave-flash",
    "vtt": "text/vtt"
}



#
# START
#

class Server:
    """Starts the built-in HTTP server inside the project's root directory"""

    def __init__(self, port=8080, host="127.0.0.1", mimeTypes=None):

        Console.info("Initializing server...")
        Console.indent()

        # Shared configuration (global/app)
        self.__config = {
            "global" : {
                "environment" : "production",
                "log.screen" : False,
                "server.socket_port": port,
                "server.socket_host": host,
                "engine.autoreload_on" : False
            },
            
            "/" : {
                "log.screen" : False
            }
        }

        self.__port = port

        # Build dict of content types to override native mimetype detection
        combinedTypes = {}
        combinedTypes.update(additionalContentTypes)
        if mimeTypes:    
            combinedTypes.update(mimeTypes)

        # Update global config
        cherrypy.config.update(self.__config)

        # Somehow this screen disabling does not work
        # This hack to disable all access/error logging works
        def empty(*param, **args): pass
        def inspect(*param, **args): 
            if args["severity"] > 20:
                Console.error("Critical error occoured:")
                Console.error(param[0])
        
        cherrypy.log.access = empty
        cherrypy.log.error = inspect
        cherrypy.log.screen = False

        # Basic routing
        self.__root = Static("/", {}, mimeTypes=combinedTypes)

        Console.outdent()


    def setRoutes(self, routes):
        """
        Adds the given routes to the server configuration. Routes can be used
        to add special top level entries to the different features of the integrated
        webserver either mirroring a remote server or delivering a local directory.

        The parameters is a dict where every key is the name of the route
        and the value is the configuration of that route.
        """

        Console.info("Adding routes...")
        Console.indent()        

        for key in routes:
            entry = routes[key]
            if "host" in entry:
                node = Proxy(key, entry)
            else:
                node = Static(key, entry, mimeTypes=self.__root.mimeTypes)
            
            setattr(self.__root, key, node)

        Console.outdent()


    def start(self):
        """
        Starts the web server and blocks execution. 

        Note: This stops further execution of the current task or method.
        """

        app = cherrypy.tree.mount(self.__root, "", self.__config)
        cherrypy.process.plugins.PIDFile(cherrypy.engine, ".jasy/server-%s" % self.__port).subscribe()
        
        cherrypy.engine.start()
        Console.info("Started HTTP server at port %s... [PID=%s]", self.__port, os.getpid())
        Console.indent()
        cherrypy.engine.block()

        Console.outdent()
        Console.info("Stopped HTTP server at port %s.", self.__port)  


########NEW FILE########
__FILENAME__ = Abstract
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

import os

from jasy import UserError
import jasy.core.File as File

class AbstractItem:
    
    id = None
    project = None
    kind = "item"

    __path = None
    __cache = None
    mtime = None
    
    def __init__(self, project, id=None):
        self.id = id
        self.project = project

    def attach(self, path):
        self.__path = path
        
        entry = None

        try:
            if type(path) is list:
                mtime = 0
                for entry in path:
                    entryTime = os.stat(entry).st_mtime
                    if entryTime > mtime:
                        mtime = entryTime
                    
                self.mtime = mtime
        
            else:
                entry = path
                self.mtime = os.stat(entry).st_mtime
            
        except OSError as oserr:
            raise UserError("Invalid item path: %s" % entry)
        
        return self
        
    def getId(self):
        """Returns a unique identify of the class. Typically as it is stored inside the project."""
        return self.id

    def setId(self, id):
        self.id = id
        return self

    def getProject(self):
        """Returns the project which the class belongs to"""
        return self.project

    def getPath(self):
        """Returns the exact position of the class file in the file system."""
        return self.__path

    def getModificationTime(self):
        """Returns last modification time of the class"""
        return self.mtime

    def getText(self, encoding="utf-8"):
        """Reads the file (as UTF-8) and returns the text"""
        
        if self.__path is None:
            return None
        
        if type(self.__path) == list:
            return "".join([open(filename, mode="r", encoding=encoding).read() for filename in self.__path])
        else:
            return open(self.__path, mode="r", encoding=encoding).read()
    
    def getChecksum(self, mode="rb"):
        """Returns the SHA1 checksum of the item"""
        
        return File.sha1(open(self.getPath(), mode))
    

    # Map Python built-ins
    __repr__ = getId
    __str__ = getId


########NEW FILE########
__FILENAME__ = Asset
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

import os.path

import jasy.asset.ImageInfo
import jasy.item.Abstract

from jasy.core.Util import getKey
from jasy.core.Config import loadConfig
import jasy.core.Console as Console

extensions = {
    ".png" : "image",
    ".jpeg" : "image",
    ".jpg" : "image",
    ".gif" : "image",
    
    ".mp3" : "audio",
    ".ogg" : "audio",
    ".m4a" : "audio",
    ".aac" : "audio",
    ".wav" : "audio",
    
    ".avi" : "video",
    ".mpeg" : "video",
    ".mpg" : "video",
    ".m4v" : "video",
    ".mkv" : "video",
    
    ".eot" : "font",
    ".woff" : "font",
    ".ttf" : "font",
    ".otf" : "font",
    ".pfa" : "font",
    ".pfb" : "font",
    ".afm" : "font",
    
    ".json" : "text",
    ".svg" : "text",
    ".txt" : "text",
    ".csv" : "text",
    ".html" : "text",
    ".js" : "text",
    ".css" : "text",
    ".htc" : "text",
    ".xml" : "text",
    ".tmpl" : "text",
    
    ".fla" : "binary",
    ".swf" : "binary",
    ".psd" : "binary",
    ".pdf" : "binary"
}


class AssetItem(jasy.item.Abstract.AbstractItem):
    
    kind = "asset"

    __imageSpriteData = []
    __imageAnimationData = []
    __imageDimensionData = []

    def __init__(self, project, id=None):
        # Call Item's init method first
        super().__init__(project, id)

        self.extension = os.path.splitext(self.id.lower())[1]
        self.type = getKey(extensions, self.extension, "other")
        self.shortType = self.type[0]
        

    def isImageSpriteConfig(self):
        return self.isText() and (os.path.basename(self.id) == "jasysprite.yaml" or os.path.basename(self.id) == "jasysprite.json")

    def isImageAnimationConfig(self):
        return self.isText() and (os.path.basename(self.id) == "jasyanimation.yaml" or os.path.basename(self.id) == "jasyanimation.json")

    def isText(self):
        return self.type == "text"

    def isImage(self):
        return self.type == "image"
    
    def isAudio(self):
        return self.type == "audio"

    def isVideo(self):
        return self.type == "video"
        
        
    def getType(self, short=False):
        if short:
            return self.shortType
        else:
            return self.type

    def getParsedObject(self):
        return loadConfig(self.getPath())

    
    def addImageSpriteData(self, id, left, top):
        Console.debug("Registering sprite location for %s: %s@%sx%s", self.id, id, left, top)
        self.__imageSpriteData = [id, left, top]
        
    
    def addImageAnimationData(self, columns, rows, frames=None, layout=None):
        if layout is not None:
            self.__imageAnimationData = layout
        elif frames is not None:
            self.__imageAnimationData = [columns, rows, frames]
        else:
            self.__imageAnimationData = [columns, rows]
    
    
    def addImageDimensionData(self, width, height):
        Console.debug("Adding dimension data for %s: %sx%s", self.id, width, height)
        self.__imageDimensionData = [width, height]
    
    
    def exportData(self):
        
        if self.isImage():
            if self.__imageDimensionData:
                image = self.__imageDimensionData[:]
            else:
                info = jasy.asset.ImageInfo.ImgInfo(self.getPath()).getInfo()
                if info is None:
                    raise Exception("Invalid image: %s" % fileId)

                image = [info[0], info[1]]

            if self.__imageSpriteData:
                image.append(self.__imageSpriteData)
            elif self.__imageAnimationData:
                # divider between sprite data and animation data
                image.append(0)
                
            if self.__imageAnimationData:
                image.append(self.__imageAnimationData)
                
            return image
            
        # TODO: audio length, video codec, etc.?
        
        return None



########NEW FILE########
__FILENAME__ = Class
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

import os, copy, zlib, fnmatch, re

import jasy.js.parse.Parser as Parser
import jasy.js.parse.ScopeScanner as ScopeScanner
import jasy.js.clean.DeadCode
import jasy.js.clean.Unused
import jasy.js.clean.Permutate
import jasy.js.optimize.Translation
import jasy.js.output.Optimization
import jasy.js.api.Data
import jasy.core.Permutation
import jasy.item.Abstract

from jasy.js.MetaData import MetaData
from jasy.js.output.Compressor import Compressor

from jasy import UserError
from jasy.js.util import *
import jasy.core.Console as Console 

try:
    from pygments import highlight
    from pygments.lexers import JavascriptLexer
    from pygments.formatters import HtmlFormatter
except:
    highlight = None


aliases = {}

defaultOptimization = jasy.js.output.Optimization.Optimization("declarations", "blocks", "variables")
defaultPermutation = jasy.core.Permutation.getPermutation({"debug" : False})


def collectFields(node, keys=None):
    
    if keys is None:
        keys = set()
    
    # Always the first parameter
    # Supported calls: jasy.Env.isSet(key, expected?), jasy.Env.getValue(key), jasy.Env.select(key, map)
    calls = ("jasy.Env.isSet", "jasy.Env.getValue", "jasy.Env.select")
    if node.type == "dot" and node.parent.type == "call" and assembleDot(node) in calls:
        keys.add(node.parent[1][0].value)

    # Process children
    for child in reversed(node):
        if child != None:
            collectFields(child, keys)
            
    return keys


class ClassError(Exception):
    def __init__(self, inst, msg):
        self.__msg = msg
        self.__inst = inst
        
    def __str__(self):
        return "Error processing class %s: %s" % (self.__inst, self.__msg)


class ClassItem(jasy.item.Abstract.AbstractItem):
    
    kind = "class"
    
    def __getTree(self, context=None):
        
        field = "tree[%s]" % self.id
        tree = self.project.getCache().read(field, self.mtime)
        if not tree:
            Console.info("Processing class %s %s...", Console.colorize(self.id, "bold"), Console.colorize("[%s]" % context, "cyan"))
            
            Console.indent()
            tree = Parser.parse(self.getText(), self.id)
            ScopeScanner.scan(tree)
            Console.outdent()
            
            self.project.getCache().store(field, tree, self.mtime, True)
        
        return tree
    
    
    def __getOptimizedTree(self, permutation=None, context=None):
        """Returns an optimized tree with permutations applied"""

        field = "opt-tree[%s]-%s" % (self.id, permutation)
        tree = self.project.getCache().read(field, self.mtime)
        if not tree:
            tree = copy.deepcopy(self.__getTree("%s:plain" % context))

            # Logging
            msg = "Processing class %s" % Console.colorize(self.id, "bold")
            if permutation:
                msg += Console.colorize(" (%s)" % permutation, "grey")
            if context:
                msg += Console.colorize(" [%s]" % context, "cyan")
                
            Console.info("%s..." % msg)
            Console.indent()

            # Apply permutation
            if permutation:
                Console.debug("Patching tree with permutation: %s", permutation)
                Console.indent()
                jasy.js.clean.Permutate.patch(tree, permutation)
                Console.outdent()

            # Cleanups
            jasy.js.clean.DeadCode.cleanup(tree)
            ScopeScanner.scan(tree)
            jasy.js.clean.Unused.cleanup(tree)
        
            self.project.getCache().store(field, tree, self.mtime, True)
            Console.outdent()

        return tree


    def getDependencies(self, permutation=None, classes=None, warnings=True):
        """ 
        Returns a set of dependencies seen through the given list of known 
        classes (ignoring all unknown items in original set). This method
        makes use of the meta data (see core/MetaData.py) and the variable data 
        (see parse/ScopeData.py).
        """

        permutation = self.filterPermutation(permutation)

        meta = self.getMetaData(permutation)
        scope = self.getScopeData(permutation)
        
        result = set()
        
        # Manually defined names/classes
        for name in meta.requires:
            if name != self.id and name in classes and classes[name].kind == "class":
                result.add(classes[name])
            elif "*" in name:
                reobj = re.compile(fnmatch.translate(name))
                for className in classes:
                    if className != self.id:
                        if reobj.match(className):
                            result.add(classes[className])
            elif warnings:
                Console.warn("- Missing class (required): %s in %s", name, self.id)

        # Globally modified names (mostly relevant when working without namespaces)
        for name in scope.shared:
            if name != self.id and name in classes and classes[name].kind == "class":
                result.add(classes[name])
        
        # Add classes from detected package access
        for package in scope.packages:
            if package in aliases:
                className = aliases[package]
                if className in classes:
                    result.add(classes[className])
                    continue
            
            orig = package
            while True:
                if package == self.id:
                    break
            
                elif package in classes and classes[package].kind == "class":
                    aliases[orig] = package
                    result.add(classes[package])
                    break
            
                else:
                    pos = package.rfind(".")
                    if pos == -1:
                        break
                    
                    package = package[0:pos]
                    
        # Manually excluded names/classes
        for name in meta.optionals:
            if name != self.id and name in classes and classes[name].kind == "class":
                result.remove(classes[name])
            elif warnings:
                Console.warn("- Missing class (optional): %s in %s", name, self.id)

        return result
        
        
    def getScopeData(self, permutation=None):
        """
        Returns the top level scope object which contains information about the
        global variable and package usage/influence.
        """
        
        permutation = self.filterPermutation(permutation)
        
        field = "scope[%s]-%s" % (self.id, permutation)
        scope = self.project.getCache().read(field, self.mtime)
        if scope is None:
            scope = self.__getOptimizedTree(permutation, "scope").scope
            self.project.getCache().store(field, scope, self.mtime)

        return scope
        
        
    def getApi(self, highlight=True):
        field = "api[%s]-%s" % (self.id, highlight)
        apidata = self.project.getCache().read(field, self.mtime, inMemory=False)
        if apidata is None:
            apidata = jasy.js.api.Data.ApiData(self.id, highlight)
            
            tree = self.__getTree(context="api")
            Console.indent()
            apidata.scanTree(tree)
            Console.outdent()
            
            metaData = self.getMetaData()
            apidata.addAssets(metaData.assets)
            for require in metaData.requires:
                apidata.addUses(require)
            for optional in metaData.optionals:
                apidata.removeUses(optional)
                
            apidata.addSize(self.getSize())
            apidata.addFields(self.getFields())
            
            self.project.getCache().store(field, apidata, self.mtime, inMemory=False)

        return apidata


    def getHighlightedCode(self):
        field = "highlighted[%s]" % self.id
        source = self.project.getCache().read(field, self.mtime)
        if source is None:
            if highlight is None:
                raise UserError("Could not highlight JavaScript code! Please install Pygments.")
            
            lexer = JavascriptLexer(tabsize=2)
            formatter = HtmlFormatter(full=True, style="autumn", linenos="table", lineanchors="line")
            source = highlight(self.getText(), lexer, formatter)
            
            self.project.getCache().store(field, source, self.mtime)

        return source


    def getMetaData(self, permutation=None):
        permutation = self.filterPermutation(permutation)

        field = "meta[%s]-%s" % (self.id, permutation)
        meta = self.project.getCache().read(field, self.mtime)
        if meta is None:
            meta = MetaData(self.__getOptimizedTree(permutation, "meta"))
            self.project.getCache().store(field, meta, self.mtime)
            
        return meta
        
        
    def getFields(self):
        field = "fields[%s]" % (self.id)
        fields = self.project.getCache().read(field, self.mtime)
        if fields is None:
            fields = collectFields(self.__getTree(context="fields"))
            self.project.getCache().store(field, fields, self.mtime)
        
        return fields


    def getTranslations(self):
        field = "translations[%s]" % (self.id)
        result = self.project.getCache().read(field, self.mtime)
        if result is None:
            result = jasy.js.optimize.Translation.collectTranslations(self.__getTree(context="i18n"))
            self.project.getCache().store(field, result, self.mtime)

        return result
        
        
    def filterPermutation(self, permutation):
        if permutation:
            fields = self.getFields()
            if fields:
                return permutation.filter(fields)

        return None
        
        
    def getCompressed(self, permutation=None, translation=None, optimization=None, formatting=None, context="compressed"):
        permutation = self.filterPermutation(permutation)

        # Disable translation for caching / patching when not actually used
        if translation and not self.getTranslations():
            translation = None
        
        field = "compressed[%s]-%s-%s-%s-%s" % (self.id, permutation, translation, optimization, formatting)
        compressed = self.project.getCache().read(field, self.mtime)
        if compressed == None:
            tree = self.__getOptimizedTree(permutation, context)
            
            if translation or optimization:
                tree = copy.deepcopy(tree)
            
                if translation:
                    jasy.js.optimize.Translation.optimize(tree, translation)

                if optimization:
                    try:
                        optimization.apply(tree)
                    except jasy.js.output.Optimization.Error as error:
                        raise ClassError(self, "Could not compress class! %s" % error)
                
            compressed = Compressor(formatting).compress(tree)
            self.project.getCache().store(field, compressed, self.mtime)
            
        return compressed
            
            
    def getSize(self):
        field = "size[%s]" % self.id
        size = self.project.getCache().read(field, self.mtime)
        
        if size is None:
            compressed = self.getCompressed(context="size")
            optimized = self.getCompressed(permutation=defaultPermutation, optimization=defaultOptimization, context="size")
            zipped = zlib.compress(optimized.encode("utf-8"))
            
            size = {
                "compressed" : len(compressed),
                "optimized" : len(optimized),
                "zipped" : len(zipped)
            }
            
            self.project.getCache().store(field, size, self.mtime)
            
        return size
        
        

########NEW FILE########
__FILENAME__ = Doc
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

import jasy.js.api.Data as Data
import jasy.core.Text as Text
import jasy.item.Abstract as Abstract

from jasy import UserError

class DocItem(Abstract.AbstractItem):
    
    kind = "doc"
    
    def getApi(self):
        field = "api[%s]" % self.id
        apidata = self.project.getCache().read(field, self.getModificationTime())
        
        if not Text.supportsMarkdown:
            raise UserError("Missing Markdown feature to convert package docs into HTML.")
        
        if apidata is None:
            apidata = Data.ApiData(self.id)
            apidata.main["type"] = "Package"
            apidata.main["doc"] = Text.highlightCodeBlocks(Text.markdownToHtml(self.getText()))
            
            self.project.getCache().store(field, apidata, self.getModificationTime())

        return apidata
        
########NEW FILE########
__FILENAME__ = Translation
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

import polib, json

import jasy.item.Abstract
import jasy.core.Console as Console


def getFormat(path):
    """
    Returns the file format of the translation. One of: gettext, xlf, properties and txt
    """

    if path:
        if path.endswith(".po"):
            return "gettext"
        elif path.endswith(".xlf"):
            return "xlf"
        elif path.endswith(".properties"):
            return "property"
        elif path.endswith(".txt"):
            return "txt"

    return None


def generateId(basic, plural=None, context=None):
    """
    Returns a unique message ID based on info typically stored in the code: id, plural, context
    """

    result = basic

    if context is not None:
        result += "[C:%s]" % context
    elif plural:
        result += "[N:%s]" % plural

    return result


class TranslationItem(jasy.item.Abstract.AbstractItem):
    """
    Internal instances mapping a translation file in different formats
    with a conventient API.
    """

    def __add__(self, other):
        self.table.update(other.getTable())
        return self


    def __init__(self, project, id=None, table=None):
        # Call Item's init method first
        super().__init__(project, id)

        # Extract language from file ID
        # Thinking of that all files are named like de.po, de.txt, de.properties, etc.
        lang = self.id
        if "." in lang:
            lang = lang[lang.rfind(".")+1:]

        self.language = lang

        # Initialize translation table
        self.table = table or {}


    def attach(self, path):
        # Call Item's attach method first
        super().attach(path)

        Console.debug("Loading translation file: %s", path)
        Console.indent()

        # Flat data strucuture where the keys are unique
        table = {}
        path = self.getPath()
        format = self.getFormat()

        # Decide infrastructure/parser to use based on file name
        if format is "gettext":
            po = polib.pofile(path)
            Console.debug("Translated messages: %s=%s%%", self.language, po.percent_translated())

            for entry in po.translated_entries():
                entryId = generateId(entry.msgid, entry.msgid_plural, entry.msgctxt)
                if not entryId in table:
                    if entry.msgstr != "":
                        table[entryId] = entry.msgstr
                    elif entry.msgstr_plural:
                        # This field contains all different plural cases (type=dict)
                        table[entryId] = entry.msgstr_plural

        elif format is "xlf":
            raise UserError("Parsing ICU/XLF files is currently not supported!")

        elif format is "properties":
            raise UserError("Parsing ICU/Property files is currently not supported!")

        elif format is "txt":
            raise UserError("Parsing ICU/text files is currently not supported!")
                        
        Console.debug("Translation of %s entries ready" % len(table))        
        Console.outdent()
        
        self.table = table

        return self

    def export(self, classes):
        """Exports the translation table as JSON based on the given set of classes"""

        # Based on the given class list figure out which translations are actually used
        relevantTranslations = set()
        for classObj in classes:
            classTranslations = classObj.getTranslations()
            if classTranslations:
                relevantTranslations.update(classTranslations)

        # Produce new table which is filtered by relevant translations
        table = self.table
        result = { translationId: table[translationId] for translationId in relevantTranslations if translationId in table }

        return json.dumps(result or None)

    def getTable(self):
        """Returns the translation table"""
        return self.table

    def getLanguage(self):
        """Returns the language of the translation file"""
        return self.language        

    def getFormat(self):
        """Returns the format of the localization file"""
        return getFormat(self.getPath())

########NEW FILE########
__FILENAME__ = Comment
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

import re

import jasy.core.Text as Text
import jasy.core.Console as Console

from jasy import UserError
from jasy.js.util import *


__all__ = ["CommentException", "Comment"]


# Used to measure the doc indent size (with leading stars in front of content)
docIndentReg = re.compile(r"^(\s*\*\s*)(\S*)")

# Used to split type lists as supported by throw, return and params
listSplit = re.compile("\s*\|\s*")

# Used to remove markup sequences after doc processing of comment text
stripMarkup = re.compile(r"<.*?>")



# Matches return blocks in comments
returnMatcher = re.compile(r"^\s*\{([a-zA-Z0-9_ \.\|\[\]]+)\}")

# Matches type definitions in comments
typeMatcher = re.compile(r"^\s*\{=([a-zA-Z0-9_ \.]+)\}")

# Matches tags
tagMatcher = re.compile(r"#([a-zA-Z][a-zA-Z0-9]+)(\((\S+)\))?(\s|$)")

# Matches param declarations in own dialect
paramMatcher = re.compile(r"@([a-zA-Z0-9_][a-zA-Z0-9_\.]*[a-zA-Z0-9_]|[a-zA-Z0-9_]+)(\s*\{([a-zA-Z0-9_ \.\|\[\]]+?)(\s*\.{3}\s*)?((\s*\?\s*(\S+))|(\s*\?\s*))?\})?")

# Matches links in own dialect
linkMatcher = re.compile(r"(\{((static|member|property|event)\:)?([a-zA-Z0-9_\.]+)?(\#([a-zA-Z0-9_]+))?\})")

# matches backticks and has a built-in failsafe for backticks which do not terminate on the same line
tickMatcher = re.compile(r"(`[^\n`]*?`)")


class CommentException(Exception):
    """
    Thrown when errors during comment processing are detected.
    """

    def __init__(self, message, lineNo=0):
        Exception.__init__(self, "Comment error: %s (line: %s)" % (message, lineNo+1))




class Comment():
    """
    Comment class is attached to parsed nodes and used to store all comment related information.
    
    The class supports a new Markdown and TomDoc inspired dialect to make developers life easier and work less repeative.
    """
    
    # Relation to code
    context = None
    
    # Dictionary of tags
    tags = None
    
    # Dictionary of params
    params = None

    # List of return types
    returns = None
    
    # Static type
    type = None
    
    # Collected text of the comment (without the extracted doc relevant data)
    text = None
    
    # Text with extracted / parsed data
    __processedText = None

    # Text of the comment converted to HTML including highlighting (only for doc comment)
    __highlightedText = None

    # Text / Code Blocks in the comment
    __blocks = None

    
    def __init__(self, text, context=None, lineNo=0, indent="", fileId=None):

        # Store context (relation to code)
        self.context = context
        
        # Store fileId
        self.fileId = fileId
        
        # Figure out the type of the comment based on the starting characters

        # Inline comments
        if text.startswith("//"):
            # "// hello" => "   hello"
            text = "  " + text[2:]
            self.variant = "single"
            
        # Doc comments
        elif text.startswith("/**"):
            # "/** hello */" => "    hello "
            text = "   " + text[3:-2]
            self.variant = "doc"

        # Protected comments which should not be removed (e.g these are used for license blocks)
        elif text.startswith("/*!"):
            # "/*! hello */" => "    hello "
            text = "   " + text[3:-2]
            self.variant = "protected"
            
        # A normal multiline comment
        elif text.startswith("/*"):
            # "/* hello */" => "   hello "
            text = "  " + text[2:-2]
            self.variant = "multi"
            
        else:
            raise CommentException("Invalid comment text: %s" % text, lineNo)

        # Multi line comments need to have their indentation removed
        if "\n" in text:
            text = self.__outdent(text, indent, lineNo)

        # For single line comments strip the surrounding whitespace
        else:
            # " hello " => "hello"
            text = text.strip()

        # The text of the comment before any processing took place
        self.text = text


        # Perform annotation parsing, markdown conversion and code highlighting on doc blocks
        if self.variant == "doc":

            # Separate text and code blocks
            self.__blocks = self.__splitBlocks(text)

            # Re-combine everything and apply processing and formatting
            plainText = '' # text without annotations but with markdown
            for b in self.__blocks:

                if b["type"] == "comment":

                    processed = self.__processDoc(b["text"], lineNo)
                    b["processed"] = processed

                    if "<" in processed:
                        plainText += stripMarkup.sub("", processed)

                    else:
                        plainText += processed

                else:
                    plainText += "\n\n" + b["text"] + "\n\n"

            # The without any annotations 
            self.text = plainText.strip()


    def __splitBlocks(self, text):
        """
        Splits up text and code blocks in comments.
        
        This will try to use Misaka for Markdown parsing if available and will 
        fallback to a simpler implementation in order to allow processing of
        doc parameters and links without Misaka being installed.
        """

        if not Text.supportsMarkdown:
            return self.__splitSimple(text)
        
        marked = Text.markdownToHtml(text)

        def unescape(html):
            html = html.replace('&lt;', '<')
            html = html.replace('&gt;', '>')
            html = html.replace('&amp;', '&')
            html = html.replace('&quot;', '"')
            return html.replace('&#39;', "'")

        parts = []

        lineNo = 0
        lines = text.split("\n")
        markedLines = marked.split("\n")

        i = 0
        while i < len(markedLines):

            l = markedLines[i]

            # the original text of the line
            parsed = unescape(stripMarkup.sub("", l))

            # start of a code block, grab all text before it and move it into a block
            if l.startswith('<pre><code>'):

                # everything since the last code block and before this one must be text
                comment = []
                for s in range(lineNo, len(lines)):

                    source = lines[s]
                    if source.strip() == parsed.strip():
                        lineNo = s
                        break

                    comment.append(source)

                parts.append({
                    "type": "comment",
                    "text": "\n".join(comment)
                })

                # Find the end of the code block
                e = i
                while i < len(markedLines):
                    l = markedLines[i]
                    i += 1

                    if l.startswith('</code></pre>'):
                        break

                lineCount = (i - e) - 1

                # add the code block
                parts.append({
                    "type": "code",
                    "text": "\n".join(lines[lineNo:lineNo + lineCount])
                })

                lineNo += lineCount

            else:
                i += 1
            
        # append the rest of the comment as text
        parts.append({
            "type": "comment",
            "text": "\n".join(lines[lineNo:])
        })

        return parts


    def __splitSimple(self, text):
        """Splits comment text and code blocks by manually parsing a subset of markdown"""
        
        inCode = False
        oldIndent = 0
        parts = []
        wasEmpty = False
        wasList = False
        
        lineNo = 0
        lines = text.split("\n")

        for s, l in enumerate(lines):

            # ignore empty lines
            if not l.strip() == "":

                # get indentation value and change
                indent = len(l) - len(l.lstrip())
                change = indent - oldIndent

                # detect code blocks
                if change >= 4 and wasEmpty:
                    if not wasList:
                        oldIndent = indent
                        inCode = True
                    
                        parts.append({
                            "type": "comment",
                            "text": "\n".join(lines[lineNo:s])
                        })

                        lineNo = s

                # detect outdents
                elif change < 0:
                    inCode = False

                    parts.append({
                        "type": "code",
                        "text": "\n".join(lines[lineNo:s - 1])
                    })

                    lineNo = s

                # only keep track of old previous indentation outside of comments
                if not inCode:
                    oldIndent = indent

                # remember whether this marked a list or not
                wasList = l.strip().startswith('-') or l.strip().startswith('*')
                wasEmpty = False

            else:
                wasEmpty = True

        parts.append({
            "type": "code" if inCode else "comment",
            "text": "\n".join(lines[lineNo:])
        })
        
        return parts


    def getHtml(self, highlight=True):
        """
        Returns the comment text converted to HTML

        :param highlight: Whether to highlight the code
        :type highlight: bool
        """

        if not Text.supportsMarkdown:
            raise UserError("Markdown is not supported by the system. Documentation comments could converted to HTML.")

        if highlight:

            if self.__highlightedText is None:

                highlightedText = ""

                for block in self.__blocks:

                    if block["type"] == "comment":
                        highlightedText += Text.highlightCodeBlocks(Text.markdownToHtml(block["processed"]))
                    else:
                        highlightedText += "\n%s" % Text.highlightCodeBlocks(Text.markdownToHtml(block["text"]))

                self.__highlightedText = highlightedText

            return self.__highlightedText

        else:
            
            if self.__processedText is None:
            
                processedText = ""

                for block in self.__blocks:

                    if block["type"] == "comment":
                        processedText += Text.markdownToHtml(block["processed"]) 
                    else:
                        processedText += "\n%s\n\n" % block["text"]

                self.__processedText = processedText.strip()

            return self.__processedText
    
    
    def hasContent(self):
        return self.variant == "doc" and len(self.text)
    

    def getTags(self):
        return self.tags
        

    def hasTag(self, name):
        if not self.tags:
            return False

        return name in self.tags


    def __outdent(self, text, indent, startLineNo):
        """
        Outdent multi line comment text and filtering empty lines
        """
        
        lines = []

        # First, split up the comments lines and remove the leading indentation
        for lineNo, line in enumerate((indent+text).split("\n")):

            if line.startswith(indent):
                lines.append(line[len(indent):].rstrip())

            elif line.strip() == "":
                lines.append("")

            else:
                # Only warn for doc comments, otherwise it might just be code commented out 
                # which is sometimes formatted pretty crazy when commented out
                if self.variant == "doc":
                    Console.warn("Could not outdent doc comment at line %s in %s", startLineNo+lineNo, self.fileId)
                    
                return text

        # Find first line with real content, then grab the one after it to get the 
        # characters which need 
        outdentString = ""
        for lineNo, line in enumerate(lines):

            if line != "" and line.strip() != "":
                matchedDocIndent = docIndentReg.match(line)
                
                if not matchedDocIndent:
                    # As soon as we find a non doc indent like line we stop
                    break
                    
                elif matchedDocIndent.group(2) != "":
                    # otherwise we look for content behind the indent to get the 
                    # correct real indent (with spaces)
                    outdentString = matchedDocIndent.group(1)
                    break
                
            lineNo += 1

        # Process outdenting to all lines (remove the outdentString from the start of the lines)
        if outdentString != "":

            lineNo = 0
            outdentStringLen = len(outdentString)

            for lineNo, line in enumerate(lines):
                if len(line) <= outdentStringLen:
                    lines[lineNo] = ""

                else:
                    if not line.startswith(outdentString):
                        
                        # Only warn for doc comments, otherwise it might just be code commented out 
                        # which is sometimes formatted pretty crazy when commented out
                        if self.variant == "doc":
                            Console.warn("Invalid indentation in doc comment at line %s in %s", startLineNo+lineNo, self.fileId)
                        
                    else:
                        lines[lineNo] = line[outdentStringLen:]

        # Merge final lines and remove leading and trailing new lines
        return "\n".join(lines).strip("\n")
            
            
    def __processDoc(self, text, startLineNo):

        text = self.__extractStaticType(text)
        text = self.__extractReturns(text)
        text = self.__extractTags(text)
        
        # Collapse new empty lines at start/end
        text = text.strip("\n\t ")

        parsed = ''

        # Now parse only the text outside of backticks
        last = 0
        def split(match):

            # Grab the text before the back tick and process any parameters in it
            nonlocal parsed
            nonlocal last

            start, end = match.span() 
            before = text[last:start]
            parsed += self.__processParams(before) + match.group(1)
            last = end

        tickMatcher.sub(split, text)

        # add the rest of the text
        parsed += self.__processParams(text[last:])

        text = self.__processLinks(parsed)

        return text
            

    def __splitTypeList(self, decl):
        
        if decl is None:
            return decl
        
        splitted = listSplit.split(decl.strip())

        result = []
        for entry in splitted:

            # Figure out if it is marked as array
            isArray = False
            if entry.endswith("[]"):
                isArray = True
                entry = entry[:-2]
            
            store = { 
                "name" : entry 
            }
            
            if isArray:
                store["array"] = True
                
            if entry in builtinTypes:
                store["builtin"] = True
                
            if entry in pseudoTypes:
                store["pseudo"] = True
            
            result.append(store)
            
        return result



    def __extractReturns(self, text):
        """
        Extracts leading return defintion (when type is function)
        """

        def collectReturn(match):
            self.returns = self.__splitTypeList(match.group(1))
            return ""
            
        return returnMatcher.sub(collectReturn, text)
        
        
        
    def __extractStaticType(self, text):
        """
        Extracts leading type defintion (when value is a static type)
        """

        def collectType(match):
            self.type = match.group(1).strip()
            return ""

        return typeMatcher.sub(collectType, text)
        
        
        
    def __extractTags(self, text):
        """
        Extract all tags inside the give doc comment. These are replaced from 
        the text and collected inside the "tags" key as a dict.
        """
        
        def collectTags(match):
             if not self.tags:
                 self.tags = {}

             name = match.group(1)
             param = match.group(3)

             if name in self.tags:
                 self.tags[name].add(param)
             elif param:
                 self.tags[name] = set([param])
             else:
                 self.tags[name] = True

             return ""

        return tagMatcher.sub(collectTags, text)
                
        
    def __processParams(self, text):
        
        def collectParams(match):

            paramName = match.group(1)
            paramTypes = match.group(3)
            paramDynamic = match.group(4) is not None
            paramOptional = match.group(5) is not None
            paramDefault = match.group(7)
            
            if paramTypes:
                paramTypes = self.__splitTypeList(paramTypes)
            
            if self.params is None:
                self.params = {}

            params = self.params
            fullName = match.group(1).strip()
            names = fullName.split('.')

            for i, mapName in enumerate(names):

                # Ensure we have the map object in the params
                if not mapName in params:
                    params[mapName] = {}

                # Add new entries and overwrite if a type is defined in this entry
                if not mapName in params or paramTypes is not None:
                
                    # Make sure to not overwrite something like @options {Object} with the type of @options.x {Number}
                    if i == len(names) - 1:

                        paramEntry = params[mapName] = {}

                        if paramTypes is not None:
                            paramEntry["type"] = paramTypes
                        
                        if paramDynamic:
                            paramEntry["dynamic"] = paramDynamic
                            
                        if paramOptional:
                            paramEntry["optional"] = paramOptional
                            
                        if paramDefault is not None:
                            paramEntry["default"] = paramDefault

                    else:
                        paramEntry = params[mapName]


                else:
                    paramEntry = params[mapName]

                # create fields for new map level
                if i + 1 < len(names):
                    if not "fields" in paramEntry:
                        paramEntry["fields"] = {}

                    params = paramEntry["fields"]

            return '<code class="param">%s</code>' % fullName
            
        return paramMatcher.sub(collectParams, text)
        
        
    def __processLinks(self, text):
        
        def formatTypes(match):
            
            parsedSection = match.group(3)
            parsedFile = match.group(4)
            parsedItem = match.group(6)
            
            # Do not match {}
            if parsedSection is None and parsedFile is None and parsedItem is None:
                return match.group(1)

            # Minor corrections
            if parsedSection and not parsedItem:
                parsedSection = ""
            
            attr = ""
            link = ""
            label = ""
            
            if parsedSection:
                link += '%s:' % parsedSection
            
            if parsedFile:
                link += parsedFile
                label += parsedFile
                
            if parsedItem:
                link += "~%s" % parsedItem
                if label == "":
                    label = parsedItem
                else:
                    label += "#%s" % parsedItem
                
            # add link to attributes list
            attr += ' href="#%s"' % link
            
            # build final HTML
            return '<a%s><code>%s</code></a>' % (attr, label)

        return linkMatcher.sub(formatTypes, text)
        

########NEW FILE########
__FILENAME__ = Data
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

import jasy.js.api.Text as Text

from jasy.js.util import *
import jasy.core.Console as Console
from jasy import UserError


__all__ = ["ApiData"]


class ApiData():
    """
    Container for all relevant API data. 
    Automatically generated, filled and cached by jasy.item.Class.getApiDocs().
    """


    __slots__ = [
        "main", "construct", "statics", "properties", "events", "members", 
        
        "id", 
        "package", "basename", 
        "errors", "size", "assets", "permutations", 
        "content", "isEmpty",
        
        "uses", "usedBy", 
        "includes", "includedBy", 
        "implements", "implementedBy",
        
        "highlight"
    ]
    
    
    def __init__(self, id, highlight=True):
        
        self.id = id
        self.highlight = highlight
        
        splits = id.split(".")
        self.basename = splits.pop()
        self.package = ".".join(splits)
        self.isEmpty = False
        
        self.uses = set()
        self.main = {
            "type" : "Unsupported",
            "name" : id,
            "line" : 1
        }
        
        
    def addSize(self, size):
        """ 
        Adds the statistics on different size aspects 
        """
        
        self.size = size
        
    def addAssets(self, assets):
        """ 
        Adds the info about used assets
        """
        
        self.assets = assets
        
    def addUses(self, uses):
        self.uses.add(uses)

    def removeUses(self, uses):
        self.uses.remove(uses)
        
    def addFields(self, permutations):
        self.permutations = permutations


    def scanTree(self, tree):
        self.uses.update(tree.scope.shared)

        for package in tree.scope.packages:
            splits = package.split(".")
            current = splits[0]
            for split in splits[1:]:
                current = "%s.%s" % (current, split)
                self.uses.add(current)
        
        try:
            if not self.__processTree(tree):
                self.main["errornous"] = True
                
        except UserError as UserError:
            raise UserError
                
        except Exception as error:
            self.main["errors"] = ({
                "line": 1,
                "message": "%s" % error
            })
            self.main["errornous"] = True
            self.warn("Error during processing file: %s" % error, 1)
    
    
    def __processTree(self, tree):
            
        success = False
        
        callNode = findCall(tree, ("core.Module", "core.Interface", "core.Class", "core.Main.declareNamespace"))
        if callNode:
            callName = getCallName(callNode)

            #
            # core.Module
            #
            if callName == "core.Module":
                self.setMain(callName, callNode.parent, self.id)
            
                staticsMap = getParameterFromCall(callNode, 1)
                if staticsMap:
                    success = True
                    self.statics = {}
                    for staticsEntry in staticsMap:
                        self.addEntry(staticsEntry[0].value, staticsEntry[1], staticsEntry, self.statics)
                        
                else:
                    self.warn("Invalid core.Module()", callNode.line)


            #
            # core.Interface
            #
            elif callName == "core.Interface":
                self.setMain(callName, callNode.parent, self.id)
        
                configMap = getParameterFromCall(callNode, 1)
                if configMap:
                    success = True
                    
                    for propertyInit in configMap:
                
                        sectionName = propertyInit[0].value
                        sectionValue = propertyInit[1]
                
                        if sectionName == "properties":
                            self.properties = {}
                            for propertyEntry in sectionValue:
                                self.addProperty(propertyEntry[0].value, propertyEntry[1], propertyEntry, self.properties)
                
                        elif sectionName == "events":
                            self.events = {}
                            for eventEntry in sectionValue:
                                self.addEvent(eventEntry[0].value, eventEntry[1], eventEntry, self.events)

                        elif sectionName == "members":
                            self.members = {}
                            for memberEntry in sectionValue:
                                self.addEntry(memberEntry[0].value, memberEntry[1], memberEntry, self.members)
                        
                        else:
                            self.warn('Invalid core.Interface section "%s"' % sectionName, propertyInit.line) 

                else:
                    self.warn("Invalid core.Interface()", callNode.line)


            #
            # core.Class
            #
            elif callName == "core.Class":
                self.setMain(callName, callNode.parent, self.id)
            
                configMap = getParameterFromCall(callNode, 1)
                if configMap:
                    success = True
                    
                    for propertyInit in configMap:
                    
                        sectionName = propertyInit[0].value
                        sectionValue = propertyInit[1]
                    
                        if sectionName == "construct":
                            self.addConstructor(sectionValue, propertyInit)

                        elif sectionName == "properties":
                            self.properties = {}
                            for propertyEntry in sectionValue:
                                self.addProperty(propertyEntry[0].value, propertyEntry[1], propertyEntry, self.properties)
                    
                        elif sectionName == "events":
                            self.events = {}
                            for eventEntry in sectionValue:
                                self.addEvent(eventEntry[0].value, eventEntry[1], eventEntry, self.events)

                        elif sectionName == "members":
                            self.members = {}
                            for memberEntry in sectionValue:
                                self.addEntry(memberEntry[0].value, memberEntry[1], memberEntry, self.members)
                            
                        elif sectionName == "include":
                            self.includes = [valueToString(entry) for entry in sectionValue]

                        elif sectionName == "implement":
                            self.implements = [valueToString(entry) for entry in sectionValue]

                        else:
                            self.warn('Invalid core.Class section "%s"' % sectionName, propertyInit.line)
                            
                else:
                    self.warn("Invalid core.Class()", callNode.line)


            #
            # core.Main.declareNamespace
            #
            elif callName == "core.Main.declareNamespace":
                target = getParameterFromCall(callNode, 0)
                assigned = getParameterFromCall(callNode, 1)
                
                if target:
                    success = True
                    
                    if assigned and assigned.type == "function":
                        # Use callNode call for constructor, find first doc comment for main documentation
                        self.setMain("core.Main", findCommentNode(tree), target.value)
                        self.addConstructor(assigned, callNode.parent)

                    else:
                        self.setMain("core.Main", callNode.parent, target.value)

                        if assigned and assigned.type == "object_init":
                            self.statics = {}
                            for staticsEntry in assigned:
                                self.addEntry(staticsEntry[0].value, staticsEntry[1], staticsEntry, self.statics)
        
        #
        # Handle plain JS namespace -> object assignments
        #
        else:

            def assignMatcher(node):

                if node.type == "assign" and node[0].type == "dot":
                    if node[1].type == "object_init":
                        doc = getDocComment(node.parent)
                        if not doc is None:
                            return True
                    elif node[1].type == "function":
                        doc = getDocComment(node.parent)
                        if not doc is None:
                            return True
                    
                return False

            result = query(tree, assignMatcher)

            if not result is None:
                name = assembleDot(result[0])
                self.setMain("Native", result.parent, name)
                success = True


                if result[1].type == "object_init":

                    # Ingore empty objects and do not produce namespaces for them
                    #
                    # e.g. some.namespace.foo = {};
                    if len(result[1]) == 0:
                        success = False
                        self.isEmpty = True

                    self.statics = {}
                    for prop in result[1]:
                        self.addEntry(prop[0].value, prop[1], prop, self.statics)
                
                elif result[1].type == "function":
                    self.addConstructor(result[1], result.parent)
                    
                    def memberMatcher(node):
                        if node is not result and node.type == "assign" and node[0].type == "dot":
                            assignName = assembleDot(node[0])
                            if assignName is not None and assignName != name and assignName.startswith(name) and len(assignName) > len(name):
                                localName = assignName[len(name):]
                                if localName.startswith("."):
                                    localName = localName[1:]

                                    # Support for MyClass.prototype.memberFoo = function() {}
                                    if "." in localName:
                                        splittedLocalName = localName.split(".")
                                        if len(splittedLocalName) == 2 and splittedLocalName[0] == "prototype":
                                            if not hasattr(self, "members"):
                                                self.members = {}
                                                
                                            self.addEntry(splittedLocalName[1], node[1], node.parent, self.members)                             
                                        
                                    # Support for MyClass.staticFoo = function() {}
                                    elif localName != "prototype":
                                        if not hasattr(self, "statics"):
                                            self.statics = {}                                        
                                    
                                        self.addEntry(localName, node[1], node.parent, self.statics)
                                    
                                    else:
                                        if not hasattr(self, "members"):
                                            self.members = {}
                                        
                                        # Support for MyClass.prototype = {};
                                        if node[1].type == "object_init":
                                            membersMap = node[1]
                                            for membersEntry in membersMap:
                                                self.addEntry(membersEntry[0].value, membersEntry[1], membersEntry, self.members)                                            
                                        
                                        # Support for MyClass.prototype = new BaseClass;
                                        elif node[1].type == "new" or node[1].type == "new_with_args":
                                            self.includes = [valueToString(node[1][0])]
                    
                    queryAll(tree, memberMatcher)
        
        
        
        #
        # core.Main.addStatics
        #
        addStatics = findCall(tree, "core.Main.addStatics")
        if addStatics:
            target = getParameterFromCall(addStatics, 0)
            staticsMap = getParameterFromCall(addStatics, 1)
            
            if target and staticsMap and target.type == "string" and staticsMap.type == "object_init":
            
                if self.main["type"] == "Unsupported":
                    self.setMain("core.Main", addStatics.parent, target.value)
            
                success = True
                if not hasattr(self, "statics"):
                    self.statics = {}
                    
                for staticsEntry in staticsMap:
                    self.addEntry(staticsEntry[0].value, staticsEntry[1], staticsEntry, self.statics)
                        
            else:
                self.warn("Invalid core.Main.addStatics()")
        
        
        #
        # core.Main.addMembers
        #
        addMembers = findCall(tree, "core.Main.addMembers")
        if addMembers:
            target = getParameterFromCall(addMembers, 0)
            membersMap = getParameterFromCall(addMembers, 1)

            if target and membersMap and target.type == "string" and membersMap.type == "object_init":
                
                if self.main["type"] == "Unsupported":
                    self.setMain("core.Main", addMembers.parent, target.value)

                success = True
                if not hasattr(self, "members"):
                    self.members = {}

                for membersEntry in membersMap:
                    self.addEntry(membersEntry[0].value, membersEntry[1], membersEntry, self.members)                    
                        
            else:
                self.warn("Invalid core.Main.addMembers()")


        return success
        


    def export(self):
        
        ret = {}
        for name in self.__slots__:
            if hasattr(self, name):
                ret[name] = getattr(self, name)
                
        return ret


    def warn(self, message, line):
        Console.warn("%s at line %s in %s" % (message, line, self.id))


    def setMain(self, mainType, mainNode, exportName):
        
        callComment = getDocComment(mainNode)

        entry = self.main = {
            "type" : mainType,
            "name" : exportName,
            "line" : mainNode.line
        }
        
        if callComment:
            
            if callComment.text:
                html = callComment.getHtml(self.highlight)
                entry["doc"] = html
                entry["summary"] = Text.extractSummary(html)
        
            if hasattr(callComment, "tags"):
                entry["tags"] = callComment.tags
        
        if callComment is None or not callComment.text:
            entry["errornous"] = True
            self.warn('Missing comment on "%s" namespace' % exportName, mainNode.line)


    def addProperty(self, name, valueNode, commentNode, collection):
        
        entry = collection[name] = {
            "line": (commentNode or valueNode).line
        }
        comment = getDocComment(commentNode)
        
        if comment is None or not comment.text:
            entry["errornous"] = True
            self.warn('Missing or empty comment on property "%s"' % name, valueNode.line)

        else:
            html = comment.getHtml(self.highlight)
            entry["doc"] = html
            entry["summary"] = Text.extractSummary(html)
            
        if comment and comment.tags:
            entry["tags"] = comment.tags
        
        # Copy over value
        ptype = getKeyValue(valueNode, "type")
        if ptype and ptype.type == "string":
            entry["type"] = ptype.value
            
        pfire = getKeyValue(valueNode, "fire")
        if pfire and pfire.type == "string":
            entry["fire"] = pfire.value

        # Produce nice output for init value
        pinit = getKeyValue(valueNode, "init")
        if pinit:
            entry["init"] = valueToString(pinit)
        
        # Handle nullable, default value is true when an init value is there. Otherwise false.
        pnullable = getKeyValue(valueNode, "nullable")
        if pnullable:
            entry["nullable"] = pnullable.type == "true"
        elif pinit is not None and pinit.type != "null":
            entry["nullable"] = False
        else:
            entry["nullable"] = True

        # Just store whether an apply routine was defined
        papply = getKeyValue(valueNode, "apply")
        if papply and papply.type == "function":
            entry["apply"] = True
        
        # Multi Properties
        pthemeable = getKeyValue(valueNode, "themeable")
        if pthemeable and pthemeable.type == "true":
            entry["themeable"] = True
        
        pinheritable = getKeyValue(valueNode, "inheritable")
        if pinheritable and pinheritable.type == "true":
            entry["inheritable"] = True
        
        pgroup = getKeyValue(valueNode, "group")
        if pgroup and len(pgroup) > 0:
            entry["group"] = [child.value for child in pgroup]
            
            pshorthand = getKeyValue(valueNode, "shorthand")
            if pshorthand and pshorthand.type == "true":
                entry["shorthand"] = True
        

    def addConstructor(self, valueNode, commentNode=None):
        entry = self.construct = {
            "line" : (commentNode or valueNode).line
        }
        
        if commentNode is None:
            commentNode = valueNode
            
        # Root doc comment is optional for constructors
        comment = getDocComment(commentNode)
        if comment and comment.hasContent():
            html = comment.getHtml(self.highlight)
            entry["doc"] = html
            entry["summary"] = Text.extractSummary(html)

        if comment and comment.tags:
            entry["tags"] = comment.tags
        
        entry["init"] = self.main["name"]
        
        funcParams = getParamNamesFromFunction(valueNode)
        if funcParams:
            entry["params"] = {}
            for paramPos, paramName in enumerate(funcParams):
                entry["params"][paramName] = {
                    "position" : paramPos
                }
            
            # Use comment for enrich existing data
            comment = getDocComment(commentNode)
            if comment:
                if not comment.params:
                    self.warn("Documentation for parameters of constructor are missing", valueNode.line)
                    for paramName in funcParams:
                        entry["params"][paramName]["errornous"] = True

                else:
                    for paramName in funcParams:
                        if paramName in comment.params:
                            entry["params"][paramName].update(comment.params[paramName])
                        else:
                            entry["params"][paramName]["errornous"] = True
                            self.warn("Missing documentation for parameter %s in constructor" % paramName, valueNode.line)
                            
            else:
                entry["errornous"] = True


    def addEvent(self, name, valueNode, commentNode, collection):
        entry = collection[name] = {
            "line" : (commentNode or valueNode).line
        }
        
        if valueNode.type == "dot":
            entry["type"] = assembleDot(valueNode)
        elif valueNode.type == "identifier":
            entry["type"] = valueNode.value
            
            # Try to resolve identifier with local variable assignment
            assignments, values = findAssignments(valueNode.value, valueNode)
            if assignments:
                
                # We prefer the same comment node as before as in these 
                # szenarios a reference might be used for different event types
                if not findCommentNode(commentNode):
                    commentNode = assignments[0]

                self.addEvent(name, values[0], commentNode, collection)
                return
        
        comment = getDocComment(commentNode)
        if comment:
            
            if comment.tags:
                entry["tags"] = comment.tags
            
            # Prefer type but fall back to returns (if the developer has made an error here)
            if comment.type:
                entry["type"] = comment.type
            elif comment.returns:
                entry["type"] = comment.returns[0]

            if comment.hasContent():
                html = comment.getHtml(self.highlight)
                entry["doc"] = html
                entry["summary"] = Text.extractSummary(html)
            else:
                self.warn("Comment contains invalid HTML", commentNode.line)
                entry["errornous"] = True
                
        else:
            self.warn("Invalid doc comment", commentNode.line)
            entry["errornous"] = True            
            


    def addEntry(self, name, valueNode, commentNode, collection):
        
        #
        # Use already existing type or get type from node info
        #
        if name in collection:
            entry = collection[name]
        else:
            entry = collection[name] = {
                "type" : nodeTypeToDocType[valueNode.type]
            }
        
        
        #
        # Store generic data like line number and visibility
        #
        entry["line"] = valueNode.line
        entry["visibility"] = getVisibility(name)
        
        if name.upper() == name:
            entry["constant"] = True
        
        
        # 
        # Complex structured types are processed in two steps
        #
        if entry["type"] == "Call" or entry["type"] == "Hook":
            
            commentNode = findCommentNode(commentNode)
            if commentNode:

                comment = getDocComment(commentNode)
                if comment:

                    # Static type definition
                    if comment.type:
                        entry["type"] = comment.type
                        self.addEntry(name, valueNode, commentNode, collection)
                        return
                
                    else:
                    
                        # Maybe type function: We need to ignore returns etc. which are often
                        # the parent of the comment.
                        funcValueNode = findFunction(commentNode)
                        if funcValueNode:
                        
                            # Switch to function type for re-analysis
                            entry["type"] = "Function"
                            self.addEntry(name, funcValueNode, commentNode, collection)
                            return
                            
            if entry["type"] == "Call":
                
                callFunction = None
                
                if valueNode[0].type == "function":
                    callFunction = valueNode[0]
                
                elif valueNode[0].type == "identifier":
                    assignNodes, assignValues = findAssignments(valueNode[0].value, valueNode[0])
                    if assignNodes:
                        callFunction = assignValues[0]
                
                if callFunction:
                    # We try to analyze what the first return node returns
                    returnNode = findReturn(callFunction)
                    if returnNode and len(returnNode) > 0:
                        returnValue = returnNode[0]
                        entry["type"] = nodeTypeToDocType[returnValue.type]
                        self.addEntry(name, returnValue, returnValue, collection)
                    
            elif entry["type"] == "Hook":

                thenEntry = valueNode[1]
                thenType = nodeTypeToDocType[thenEntry.type]
                if not thenType in ("void", "null"):
                    entry["type"] = thenType
                    self.addEntry(name, thenEntry, thenEntry, collection)

                # Try second item for better data then null/void
                else:
                    elseEntry = valueNode[2]
                    elseType = nodeTypeToDocType[elseEntry.type]
                    entry["type"] = elseType
                    self.addEntry(name, elseEntry, elseEntry, collection)
                
            return
            
            
        #
        # Try to resolve identifiers
        #
        if entry["type"] == "Identifier":
            
            assignTypeNode, assignCommentNode = resolveIdentifierNode(valueNode)
            if assignTypeNode is not None:
                entry["type"] = nodeTypeToDocType[assignTypeNode.type]
                
                # Prefer comment from assignment, not from value if available
                self.addEntry(name, assignTypeNode, assignCommentNode, collection)
                return


        #
        # Processes special types:
        #
        # - Plus: Whether a string or number is created
        # - Object: Figures out the class instance which is created
        #
        if entry["type"] == "Plus":
            entry["type"] = detectPlusType(valueNode)
        
        elif entry["type"] == "Object":
            entry["type"] = detectObjectType(valueNode)
        
        
        #
        # Add human readable value
        #
        valueNodeHumanValue = valueToString(valueNode)
        if valueNodeHumanValue != entry["type"] and not valueNodeHumanValue in ("Other", "Call"):
            entry["value"] = valueNodeHumanValue
        
        
        #
        # Read data from comment and add documentation
        #
        comment = getDocComment(commentNode)
        if comment:
            
            if comment.tags:
                entry["tags"] = comment.tags
            
            if comment.type:
                entry["type"] = comment.type
                
            if comment.hasContent():
                html = comment.getHtml(self.highlight)
                entry["doc"] = html
                entry["summary"] = Text.extractSummary(html)
            else:
                entry["errornous"] = True
                
            if comment.tags:
                entry["tags"] = comment.tags
                
        else:
            entry["errornous"] = True
        
        
        #
        # Add additional data for function types (params, returns)
        #
        if entry["type"] == "Function":
            
            # Add basic param data
            funcParams = getParamNamesFromFunction(valueNode)
            if funcParams:
                entry["params"] = {}
                for paramPos, paramName in enumerate(funcParams):
                    entry["params"][paramName] = {
                        "position" : paramPos
                    }
            
            # Detect return type automatically
            returnNode = findReturn(valueNode)
            if returnNode and len(returnNode) > 0:
                autoReturnType = nodeTypeToDocType[returnNode[0].type]
                if autoReturnType == "Plus":
                    autoReturnType = detectPlusType(returnNode[0])
                elif autoReturnType in ("Call", "Object"):
                    autoReturnType = "var"
            
                autoReturnEntry = { 
                    "name" : autoReturnType,
                    "auto" : True
                }
                
                if autoReturnType in builtinTypes:
                    autoReturnEntry["builtin"] = True
                    
                if autoReturnType in pseudoTypes:
                    autoReturnEntry["pseudo"] = True

                entry["returns"] = [autoReturnEntry]

            # Use comment for enrich existing data
            if comment:
                if comment.returns:
                    entry["returns"] = comment.returns

                if funcParams:
                    if not comment.params:
                        for paramName in funcParams:
                            entry["params"][paramName]["errornous"] = True
                            
                    else:
                        for paramName in funcParams:
                            if paramName in comment.params:
                                entry["params"][paramName].update(comment.params[paramName])
                            else:
                                entry["params"][paramName]["errornous"] = True


########NEW FILE########
__FILENAME__ = Text
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

import re
import jasy.core.Console as Console

__all__ = ["extractSummary"]

# Used to filter first paragraph from HTML
paragraphExtract = re.compile(r"^(.*?)(\. |\? |\! |$)")
newlineMatcher = re.compile(r"\n")

# Used to remove markup sequences after doc processing of comment text
stripMarkup = re.compile(r"<.*?>")

def extractSummary(text):
    try:
        text = stripMarkup.sub("", newlineMatcher.sub(" ", text))
        matched = paragraphExtract.match(text)
    except TypeError:
        matched = None
        
    if matched:
        summary = matched.group(1)
        if summary is not None:
            if not summary.endswith((".", "!", "?")):
                summary = summary.strip() + "."
            return summary
            
    else:
        Console.warn("Unable to extract summary for: %s", text)
    
    return None
    

########NEW FILE########
__FILENAME__ = Writer
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

import copy, re, os, json

import jasy.js.api.Data as Data
import jasy.js.api.Text as Text
import jasy.core.File as File

from jasy.js.util import *
import jasy.core.Console as Console
from jasy import UserError


__all__ = ["ApiWriter"]

itemMap = {
    "members": "member",
    "statics": "static",
    "properties": "property",
    "events": "event"
}

linkMap = {
    "member": "members",
    "static": "statics",
    "property": "properties",
    "event": "events"
}

# Used to process HTML links
linkExtract = re.compile(r" href=(\"|')([a-zA-Z0-9#\:\.\~]+)(\"|')", re.M)
internalLinkParse = re.compile(r"^((static|member|property|event)\:)?([a-zA-Z0-9_\.]+)?(\~([a-zA-Z0-9_]+))?$")

def convertFunction(item):
    item["isFunction"] = True
    if "params" in item:
        params = item["params"]
        paramsNew = []
        sortedParams = list(sorted(params, key=lambda paramName: params[paramName]["position"]))
        for paramName in sortedParams:
            param = params[paramName]
            param["name"] = paramName
            paramsNew.append(param)
            
        item["params"] = paramsNew
        
        
def convertTags(item):
    if "tags" in item:
        tags = item["tags"]
        tagsNew = []
        if tags:
            for tagName in sorted(tags):
                tag = { "name" : tagName }
                if tags[tagName] is not True:
                    tag["value"] = "+".join(tags[tagName])
                tagsNew.append(tag)
            
        item["tags"] = tagsNew


def safeUpdate(dest, origin):
    """ Like update() but only never overwrites"""
    
    for key in origin:
        if not key in dest:
            dest[key] = origin[dest]


def isErrornous(data):
    if "errornous" in data:
        return True
        
    if "params" in data:
        for paramName in data["params"]:
            param = data["params"][paramName]
            if "errornous" in param:
                return True
                
    return False


def mergeMixin(className, mixinName, classApi, mixinApi):
    Console.info("Merging %s into %s", mixinName, className)

    sectionLink = ["member", "property", "event"]
    
    for pos, section in enumerate(("members", "properties", "events")):
        mixinItems = getattr(mixinApi, section, None)
        if mixinItems:
            classItems = getattr(classApi, section, None)
            if not classItems:
                classItems = {}
                setattr(classApi, section, classItems)
            
            for name in mixinItems:

                # Overridden Check
                if name in classItems:
                
                    # If it was included, just store another origin
                    if "origin" in classItems[name]:
                        classItems[name]["origin"].append({
                            "name": mixinName,
                            "link": "%s:%s~%s" % (sectionLink[pos], mixinName, name)
                        })
                
                    # Otherwise add it to the overridden list
                    else:
                        if not "overridden" in classItems[name]:
                            classItems[name]["overridden"] = []

                        classItems[name]["overridden"].append({
                            "name": mixinName,
                            "link": "%s:%s~%s" % (sectionLink[pos], mixinName, name)
                        })

                # Remember where classes are included from
                else:
                    classItems[name] = {}
                    classItems[name].update(mixinItems[name])
                    if not "origin" in classItems[name]:
                        classItems[name]["origin"] = []

                    classItems[name]["origin"].append({
                        "name": mixinName,
                        "link": "%s:%s~%s" % (sectionLink[pos], mixinName, name)
                    })



def connectInterface(className, interfaceName, classApi, interfaceApi):
    Console.debug("- Connecting %s with %s", className, interfaceName)
    
    #
    # Properties
    #
    interfaceProperties = getattr(interfaceApi, "properties", None)
    if interfaceProperties:
        classProperties = getattr(classApi, "properties", {})
        for name in interfaceProperties:
            if not name in classProperties:
                Console.warn("Class %s is missing implementation for property %s of interface %s!", className, name, interfaceName)

            else:
                # Add reference to interface
                if not "interface" in classProperties[name]:
                    classProperties[name]["defined"] = []

                classProperties[name]["defined"].append({
                    "name": interfaceName,
                    "link": "property:%s~%s" % (interfaceName, name)
                })
                
                # Copy over documentation
                if not "doc" in classProperties[name] and "doc" in interfaceProperties[name]:
                    classProperties[name]["doc"] = interfaceProperties[name]["doc"]

                if not "summary" in classProperties[name] and "summary" in interfaceProperties[name]:
                    classProperties[name]["summary"] = interfaceProperties[name]["summary"]
                    
                if "errornous" in classProperties[name] and not "errornous" in interfaceProperties[name]:
                    del classProperties[name]["errornous"]
                    
                # Update tags with data from interface
                if "tags" in interfaceProperties[name]:
                    if not "tags" in classProperties[name]:
                        classProperties[name]["tags"] = {}

                    safeUpdate(classProperties[name]["tags"], interfaceProperties[name]["tags"])                    
    
    #
    # Events
    #
    interfaceEvents = getattr(interfaceApi, "events", None)
    if interfaceEvents:
        classEvents = getattr(classApi, "events", {})
        for name in interfaceEvents:
            if not name in classEvents:
                Console.warn("Class %s is missing implementation for event %s of interface %s!", className, name, interfaceName)
            else:
                # Add reference to interface
                if not "interface" in classEvents[name]:
                    classEvents[name]["defined"] = []

                classEvents[name]["defined"].append({
                    "name": interfaceName,
                    "link": "event:%s~%s" % (interfaceName, name)
                })
                
                # Copy user event type and documentation from interface
                if not "doc" in classEvents[name] and "doc" in interfaceEvents[name]:
                    classEvents[name]["doc"] = interfaceEvents[name]["doc"]

                if not "summary" in classEvents[name] and "summary" in interfaceEvents[name]:
                    classEvents[name]["summary"] = interfaceEvents[name]["summary"]

                if not "type" in classEvents[name] and "type" in interfaceEvents[name]:
                    classEvents[name]["type"] = interfaceEvents[name]["type"]

                if "errornous" in classEvents[name] and not "errornous" in interfaceEvents[name]:
                    del classEvents[name]["errornous"]
                    
                # Update tags with data from interface
                if "tags" in interfaceEvents[name]:
                    if not "tags" in classEntry:
                        classEvents[name]["tags"] = {}

                    safeUpdate(classEvents[name]["tags"], interfaceEvents[name]["tags"])                    

    #
    # Members
    #
    interfaceMembers = getattr(interfaceApi, "members", None)
    if interfaceMembers:
        classMembers = getattr(classApi, "members", {})
        for name in interfaceMembers:
            if not name in classMembers:
                Console.warn("Class %s is missing implementation for member %s of interface %s!", className, name, interfaceName)
    
            else:
                interfaceEntry = interfaceMembers[name]
                classEntry = classMembers[name]
                
                # Add reference to interface
                if not "interface" in classEntry:
                    classEntry["defined"] = []
                    
                classEntry["defined"].append({
                    "name": interfaceName,
                    "link": "member:%s~%s" % (interfaceName, name)
                })
                
                # Copy over doc from interface
                if not "doc" in classEntry and "doc" in interfaceEntry:
                    classEntry["doc"] = interfaceEntry["doc"]

                if not "summary" in classEntry and "summary" in interfaceEntry:
                    classEntry["summary"] = interfaceEntry["summary"]

                if "errornous" in classEntry and not "errornous" in interfaceEntry:
                    del classEntry["errornous"]

                # Priorize return value from interface (it's part of the interface feature set to enforce this)
                if "returns" in interfaceEntry:
                    classEntry["returns"] = interfaceEntry["returns"]

                # Update tags with data from interface
                if "tags" in interfaceEntry:
                    if not "tags" in classEntry:
                        classEntry["tags"] = {}
                    
                    safeUpdate(classEntry["tags"], interfaceEntry["tags"])

                # Copy over params from interface
                if "params" in interfaceEntry:
                    # Fix completely missing parameters
                    if not "params" in classEntry:
                        classEntry["params"] = {}
                        
                    for paramName in interfaceEntry["params"]:
                        # Prefer data from interface
                        if not paramName in classEntry["params"]:
                            classEntry["params"][paramName] = {}
                            
                        classEntry["params"][paramName].update(interfaceEntry["params"][paramName])
                        
                        # Clear errournous documentation flags
                        if "errornous" in classEntry["params"][paramName] and not "errornous" in interfaceEntry["params"][paramName]:
                            del classEntry["params"][paramName]["errornous"]


class ApiWriter():
    """
    Processes JavaScript classes into data for API documentation. Exports plain data which can be used
    by a wide varity of tools for further processing or for displaying documentation. A good
    example of how to use the data generated by `write` is the ApiBrowser: https://github.com/zynga/apibrowser
    """

    def __init__(self, session):

        self.__session = session

    
    def __isIncluded(self, className, classFilter):
        
        if not classFilter:
            return True
            
        if type(classFilter) is tuple:
            if className.startswith(classFilter):
                return True
            
        elif not classFilter(className):
            return True
            
        return False
    

    def write(self, distFolder, classFilter=None, callback="apiload", showInternals=False, showPrivates=False, printErrors=True, highlightCode=True):
        """
        Writes API data generated from JavaScript into distFolder

        :param distFolder: Where to store the API data
        :param classFilter: Tuple of classes or method to use for filtering
        :param callback: Name of callback to use for loading or None if pure JSON should be used
        :param showInternals: Include internal methods inside API data
        :param showPrivates: Include private methods inside API data
        :param printErrors: Whether errors should be printed to the console
        :param highlightCode: Whether to enable code highlighting using Pygments 

        :type distFolder: str
        :type classFilter: tuple or function
        :type callback: function
        :type showInternals: bool
        :type showPrivates: bool
        :type printErrors: bool
        :type highlightCode: bool
        """
        
        #
        # Collecting
        #
        
        Console.info("Collecting API Data...")
        Console.indent()
        
        apiData = {}
        highlightedCode = {}
        
        for project in self.__session.getProjects():
            classes = project.getClasses()
            Console.info("Loading API of project %s: %s...", Console.colorize(project.getName(), "bold"), Console.colorize("%s classes" % len(classes), "cyan"))
            Console.indent()
            for className in classes:
                if self.__isIncluded(className, classFilter):

                    data = classes[className].getApi(highlightCode)

                    if not data.isEmpty:
                        apiData[className] = data
                        highlightedCode[className] = classes[className].getHighlightedCode()
                
                    else:
                        Console.info("Skipping %s, class is empty." % className)

            Console.outdent()
        
        Console.outdent()

        
        #
        # Processing
        #
        
        Console.info("Processing API Data...")
        Console.indent()
        
        data, index, search = self.__process(apiData, classFilter=classFilter, internals=showInternals, privates=showPrivates, printErrors=printErrors, highlightCode=highlightCode)
        
        Console.outdent()
        
        
        
        #
        # Writing
        #

        Console.info("Storing API data...")
        Console.indent()

        writeCounter = 0
        extension = "js" if callback else "json"
        compress = True


        class JsonEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, set):
                    return list(obj)
                    
                return json.JSONEncoder.default(self, obj)


        def encode(content, name):

            if compress:
                jsonContent = json.dumps(content, sort_keys=True, cls=JsonEncoder, separators=(',',':'))
            else:
                jsonContent = json.dumps(content, sort_keys=True, cls=JsonEncoder, indent=2)

            if callback:
                return "%s(%s,'%s');" % (callback, jsonContent, name)
            else:
                return jsonContent


        Console.info("Saving class data (%s files)...", len(data))
        Console.indent()

        for className in data:
            try:
                classData = data[className]
                if type(classData) is dict:
                    classExport = classData
                else:
                    classExport = classData.export()

                File.write(self.__session.expandFileName(os.path.join(distFolder, "%s.%s" % (className, extension))), encode(classExport, className))
            except TypeError as writeError:
                Console.error("Could not write API data of: %s: %s", className, writeError)
                continue

        Console.outdent()

        if highlightCode:
            Console.info("Saving highlighted code (%s files)...", len(highlightedCode))
            Console.indent()

            for className in highlightedCode:
                try:
                    File.write(self.__session.expandFileName(os.path.join(distFolder, "%s.html" % className)), highlightedCode[className])
                except TypeError as writeError:
                    Console.error("Could not write highlighted code of: %s: %s", className, writeError)
                    continue

            Console.outdent()

        Console.info("Writing index...")

        Console.indent()
        File.write(self.__session.expandFileName(os.path.join(distFolder, "meta-index.%s" % extension)), encode(index, "meta-index"))
        File.write(self.__session.expandFileName(os.path.join(distFolder, "meta-search.%s" % extension)), encode(search, "meta-search"))
        Console.outdent()
        
        Console.outdent()



    def __process(self, apiData, classFilter=None, internals=False, privates=False, printErrors=True, highlightCode=True):
        
        knownClasses = set(list(apiData))


        #
        # Attaching Links to Source Code (Lines)
        # Building Documentation Summaries
        #

        
        Console.info("Adding Source Links...")

        for className in apiData:
            classApi = apiData[className]

            constructData = getattr(classApi, "construct", None)
            if constructData is not None:
                if "line" in constructData:
                    constructData["sourceLink"] = "source:%s~%s" % (className, constructData["line"])

            for section in ("properties", "events", "statics", "members"):
                sectionData = getattr(classApi, section, None)

                if sectionData is not None:
                    for name in sectionData:
                        if "line" in sectionData[name]:
                            sectionData[name]["sourceLink"] = "source:%s~%s" % (className, sectionData[name]["line"])



        #
        # Including Mixins / IncludedBy
        #

        Console.info("Resolving Mixins...")
        Console.indent()

        # Just used temporary to keep track of which classes are merged
        mergedClasses = set()

        def getApi(className):
            classApi = apiData[className]

            if className in mergedClasses:
                return classApi

            classIncludes = getattr(classApi, "includes", None)
            if classIncludes:
                for mixinName in classIncludes:
                    if not mixinName in apiData:
                        Console.error("Invalid mixin %s in class %s", className, mixinName)
                        continue
                        
                    mixinApi = apiData[mixinName]
                    if not hasattr(mixinApi, "includedBy"):
                        mixinApi.includedBy = set()

                    mixinApi.includedBy.add(className)
                    mergeMixin(className, mixinName, classApi, getApi(mixinName))

            mergedClasses.add(className)

            return classApi

        for className in apiData:
            apiData[className] = getApi(className)

        Console.outdent()



        #
        # Checking links
        #
        
        Console.info("Checking Links...")
        
        additionalTypes = ("Call", "Identifier", "Map", "Integer", "Node", "Element")
        
        def checkInternalLink(link, className):
            match = internalLinkParse.match(link)
            if not match:
                return 'Invalid link "#%s"' % link
                
            if match.group(3) is not None:
                className = match.group(3)
                
            if not className in knownClasses and not className in apiData:
                return 'Invalid class in link "#%s"' % link
                
            # Accept all section/item values for named classes,
            # as it might be pretty complicated to verify this here.
            if not className in apiData:
                return True
                
            classApi = apiData[className]
            sectionName = match.group(2)
            itemName = match.group(5)
            
            if itemName is None:
                return True
                
            if sectionName is not None:
                if not sectionName in linkMap:
                    return 'Invalid section in link "#%s"' % link
                    
                section = getattr(classApi, linkMap[sectionName], None)
                if section is None:
                    return 'Invalid section in link "#%s"' % link
                else:
                    if itemName in section:
                        return True
                        
                    return 'Invalid item in link "#%s"' % link
            
            for sectionName in ("statics", "members", "properties", "events"):
                section = getattr(classApi, sectionName, None)
                if section and itemName in section:
                    return True
                
            return 'Invalid item link "#%s"' % link


        def checkLinksInItem(item):
            
            # Process types
            if "type" in item:
                
                if item["type"] == "Function":

                    # Check param types
                    if "params" in item:
                        for paramName in item["params"]:
                            paramEntry = item["params"][paramName]
                            if "type" in paramEntry:
                                for paramTypeEntry in paramEntry["type"]:
                                    if not paramTypeEntry["name"] in knownClasses and not paramTypeEntry["name"] in additionalTypes and not ("builtin" in paramTypeEntry or "pseudo" in paramTypeEntry):
                                        item["errornous"] = True
                                        Console.error('Invalid param type "%s" in %s' % (paramTypeEntry["name"], className))

                                    if not "pseudo" in paramTypeEntry and paramTypeEntry["name"] in knownClasses:
                                        paramTypeEntry["linkable"] = True
                
                
                    # Check return types
                    if "returns" in item:
                        for returnTypeEntry in item["returns"]:
                            if not returnTypeEntry["name"] in knownClasses and not returnTypeEntry["name"] in additionalTypes and not ("builtin" in returnTypeEntry or "pseudo" in returnTypeEntry):
                                item["errornous"] = True
                                Console.error('Invalid return type "%s" in %s' % (returnTypeEntry["name"], className))
                            
                            if not "pseudo" in returnTypeEntry and returnTypeEntry["name"] in knownClasses:
                                returnTypeEntry["linkable"] = True
                            
                elif not item["type"] in builtinTypes and not item["type"] in pseudoTypes and not item["type"] in additionalTypes:
                    item["errornous"] = True
                    Console.error('Invalid type "%s" in %s' % (item["type"], className))
            
            
            # Process doc
            if "doc" in item:
                
                def processInternalLink(match):
                    linkUrl = match.group(2)

                    if linkUrl.startswith("#"):
                        linkCheck = checkInternalLink(linkUrl[1:], className)
                        if linkCheck is not True:
                            item["errornous"] = True

                            if sectionName:
                                Console.error("%s in %s:%s~%s" % (linkCheck, sectionName, className, name))
                            else:
                                Console.error("%s in %s" % (linkCheck, className))
            
                linkExtract.sub(processInternalLink, item["doc"])


        Console.indent()

        # Process APIs
        for className in apiData:
            classApi = apiData[className]
            
            sectionName = None
            constructData = getattr(classApi, "construct", None)
            if constructData is not None:
                checkLinksInItem(constructData)

            for sectionName in ("properties", "events", "statics", "members"):
                section = getattr(classApi, sectionName, None)

                if section is not None:
                    for name in section:
                         checkLinksInItem(section[name])

        Console.outdent()



        #
        # Filter Internals/Privates
        #
        
        Console.info("Filtering Items...")
        
        def isVisible(entry):
            if "visibility" in entry:
                visibility = entry["visibility"]
                if visibility == "private" and not privates:
                    return False
                if visibility == "internal" and not internals:
                    return False

            return True

        def filterInternalsPrivates(classApi, field):
            data = getattr(classApi, field, None)
            if data:
                for name in list(data):
                    if not isVisible(data[name]):
                        del data[name]

        for className in apiData:
            filterInternalsPrivates(apiData[className], "statics")
            filterInternalsPrivates(apiData[className], "members")



        #
        # Connection Interfaces / ImplementedBy
        #
        
        Console.info("Connecting Interfaces...")
        Console.indent()
        
        for className in apiData:
            classApi = getApi(className)
            
            if not hasattr(classApi, "main"):
                continue
                
            classType = classApi.main["type"]
            if classType == "core.Class":
                
                classImplements = getattr(classApi, "implements", None)
                if classImplements:
                    
                    for interfaceName in classImplements:
                        interfaceApi = apiData[interfaceName]
                        implementedBy = getattr(interfaceApi, "implementedBy", None)
                        if not implementedBy:
                            implementedBy = interfaceApi.implementedBy = []
                            
                        implementedBy.append(className)
                        connectInterface(className, interfaceName, classApi, interfaceApi)
        
        Console.outdent()
        
        
        #
        # Merging Named Classes
        #
        
        Console.info("Merging Named Classes...")
        Console.indent()
        
        for className in list(apiData):
            classApi = apiData[className]
            destName = classApi.main["name"]
            
            if destName is not None and destName != className:

                Console.debug("Extending class %s with %s", destName, className)

                if destName in apiData:
                    destApi = apiData[destName]
                    destApi.main["from"].append(className)
                
                else:
                    destApi = apiData[destName] = Data.ApiData(destName, highlight=highlightCode)
                    destApi.main = {
                        "type" : "Extend",
                        "name" : destName,
                        "from" : [className]
                    }
                    
                # If there is a "main" tag found in the class use its API description
                if "tags" in classApi.main and classApi.main["tags"] is not None and "main" in classApi.main["tags"]:
                    if "doc" in classApi.main:
                        destApi.main["doc"] = classApi.main["doc"]
                
                classApi.main["extension"] = True
                    
                # Read existing data
                construct = getattr(classApi, "construct", None)
                statics = getattr(classApi, "statics", None)
                members = getattr(classApi, "members", None)

                if construct is not None:
                    if hasattr(destApi, "construct"):
                        Console.warn("Overriding constructor in extension %s by %s", destName, className)
                        
                    destApi.construct = copy.copy(construct)

                if statics is not None:
                    if not hasattr(destApi, "statics"):
                        destApi.statics = {}

                    for staticName in statics:
                        destApi.statics[staticName] = copy.copy(statics[staticName])
                        destApi.statics[staticName]["from"] = className
                        destApi.statics[staticName]["fromLink"] = "static:%s~%s" % (className, staticName)

                if members is not None:
                    if not hasattr(destApi, "members"):
                        destApi.members = {}
                        
                    for memberName in members:
                        destApi.members[memberName] = copy.copy(members[memberName])
                        destApi.members[memberName]["from"] = className
                        destApi.members[memberName]["fromLink"] = "member:%s~%s" % (className, memberName)

        Console.outdent()
        

        #
        # Connecting Uses / UsedBy
        #

        Console.info("Collecting Use Patterns...")

        # This matches all uses with the known classes and only keeps them if matched
        allClasses = set(list(apiData))
        for className in apiData:
            uses = apiData[className].uses

            # Rebuild use list
            cleanUses = set()
            for use in uses:
                if use != className and use in allClasses:
                    cleanUses.add(use)

                    useEntry = apiData[use]
                    if not hasattr(useEntry, "usedBy"):
                        useEntry.usedBy = set()

                    useEntry.usedBy.add(className)

            apiData[className].uses = cleanUses

        
        
        #
        # Collecting errors
        #
        
        Console.info("Collecting Errors...")
        Console.indent()
        
        for className in sorted(apiData):
            classApi = apiData[className]
            errors = []

            if isErrornous(classApi.main):
                errors.append({
                    "kind": "Main",
                    "name": None,
                    "line": 1
                })
            
            if hasattr(classApi, "construct"):
                if isErrornous(classApi.construct):
                    errors.append({
                        "kind": "Constructor",
                        "name": None,
                        "line": classApi.construct["line"]
                    })
            
            for section in ("statics", "members", "properties", "events"):
                items = getattr(classApi, section, {})
                for itemName in items:
                    item = items[itemName]
                    if isErrornous(item):
                        errors.append({
                            "kind": itemMap[section],
                            "name": itemName,
                            "line": item["line"]
                        })
                        
            if errors:
                if printErrors:
                    Console.warn("Found errors in %s", className)
                    
                errorsSorted = sorted(errors, key=lambda entry: entry["line"])
                
                if printErrors:
                    Console.indent()
                    for entry in errorsSorted:
                        if entry["name"]:
                            Console.warn("%s: %s (line %s)", entry["kind"], entry["name"], entry["line"])
                        else:
                            Console.warn("%s (line %s)", entry["kind"], entry["line"])
                
                    Console.outdent()
                    
                classApi.errors = errorsSorted
                
        Console.outdent()
        
        
        
        #
        # Building Search Index
        #

        Console.info("Building Search Index...")
        search = {}

        def addSearch(classApi, field):
            data = getattr(classApi, field, None)
            if data:
                for name in data:
                    if not name in search:
                        search[name] = set()

                    search[name].add(className)

        for className in apiData:

            classApi = apiData[className]

            addSearch(classApi, "statics")
            addSearch(classApi, "members")
            addSearch(classApi, "properties")
            addSearch(classApi, "events")
        
        
        
        #
        # Post Process (dict to sorted list)
        #
        
        Console.info("Post Processing Data...")
        
        for className in sorted(apiData):
            classApi = apiData[className]
            
            convertTags(classApi.main)
            
            construct = getattr(classApi, "construct", None)
            if construct:
                convertFunction(construct)
                convertTags(construct)

            for section in ("statics", "members", "properties", "events"):
                items = getattr(classApi, section, None)
                if items:
                    sortedList = []
                    for itemName in sorted(items):
                        item = items[itemName]
                        item["name"] = itemName
                        
                        if "type" in item and item["type"] == "Function":
                            convertFunction(item)
                                
                        convertTags(item)
                        sortedList.append(item)

                    setattr(classApi, section, sortedList)
        
        
        
        #
        # Collecting Package Docs
        #

        Console.info("Collecting Package Docs...")
        Console.indent()
        
        # Inject existing package docs into api data
        for project in self.__session.getProjects():
            docs = project.getDocs()
            
            for packageName in docs:
                if self.__isIncluded(packageName, classFilter):
                    Console.debug("Creating package documentation %s", packageName)
                    apiData[packageName] = docs[packageName].getApi()
        
        
        # Fill missing package docs
        for className in sorted(apiData):
            splits = className.split(".")
            packageName = splits[0]
            for split in splits[1:]:
                if not packageName in apiData:
                    Console.warn("Missing package documentation %s", packageName)
                    apiData[packageName] = Data.ApiData(packageName, highlight=highlightCode)
                    apiData[packageName].main = {
                        "type" : "Package",
                        "name" : packageName
                    }
                        
                packageName = "%s.%s" % (packageName, split)


        # Now register all classes in their parent namespace/package
        for className in sorted(apiData):
            splits = className.split(".")
            packageName = ".".join(splits[:-1])
            if packageName:
                package = apiData[packageName]
                # debug("- Registering class %s in parent %s", className, packageName)
                
                entry = {
                    "name" : splits[-1],
                    "link" : className,
                }
                
                classMain = apiData[className].main
                if "doc" in classMain and classMain["doc"]:
                    summary = Text.extractSummary(classMain["doc"])
                    if summary:
                        entry["summary"] = summary
                        
                if "type" in classMain and classMain["type"]:
                    entry["type"] = classMain["type"]
                
                if not hasattr(package, "content"):
                    package.content = [entry]
                else:
                    package.content.append(entry)
                    
        Console.outdent()



        #
        # Writing API Index
        #
        
        Console.debug("Building Index...")
        index = {}
        
        for className in sorted(apiData):
            
            classApi = apiData[className]
            mainInfo = classApi.main
            
            # Create structure for className
            current = index
            for split in className.split("."):
                if not split in current:
                    current[split] = {}
            
                current = current[split]
            
            # Store current type
            current["$type"] = mainInfo["type"]
            
            # Keep information if
            if hasattr(classApi, "content"):
                current["$content"] = True
        
        
        
        #
        # Return
        #
        
        return apiData, index, search
        
        
        

########NEW FILE########
__FILENAME__ = DeadCode
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

"""
This module is used to detect dead code branches and remove them. 
This is escecially useful after injecting values from the outside
which might lead to simple truish equations which can be easily
resolved. 

This module is directly used by Class after Permutations have been
applied (code branches) but can be used more widely, too.

This acts somewhat like the optimizers you find under "optimizer",
but is dependency relevant (Permutations might remove whole blocks 
of alternative code branches). It makes no sense to optimize this
just before compilation. It must be done pretty early during the
processing of classes.

The module currently support the following statements:

* if
* hook (?:)
* switch

and can detect good code based on:

* true
* false
* equal: ==
* strict equal: ===
* not equal: !=
* strict not equal: !==
* not: !
* and: &&
* or: ||

It supports the types "string" and "number" during comparisions. It
uses a simple equality operator in Python which behaves like strict
equal in JavaScript. This also means that number 42 is not equal to
string "42" during the dead code analysis.

It can figure out combined expressions as well like:

* 4 == 4 && !false

"""

__all__ = ["cleanup"]

import jasy.core.Console as Console

def cleanup(node):
    """
    Reprocesses JavaScript to remove dead paths 
    """
    
    Console.debug("Removing dead code branches...")

    Console.indent()
    result = __cleanup(node)
    Console.outdent()

    return result


def __cleanup(node):
    """
    Reprocesses JavaScript to remove dead paths 
    """
    
    optimized = False
    
    # Process from inside to outside
    for child in reversed(node):
        # None children are allowed sometimes e.g. during array_init like [1,2,,,7,8]
        if child != None:
            if __cleanup(child):
                optimized = True
        
    # Optimize if cases
    if node.type == "if":
        check = __checkCondition(node.condition)
        if check is not None:
            optimized = True
            Console.debug("Optimizing if/else at line %s", node.line)
            
            if check is True:
                node.parent.replace(node, node.thenPart)
                
            elif check is False:
                if hasattr(node, "elsePart"):
                    node.parent.replace(node, node.elsePart)
                else:
                    node.parent.remove(node)
    
    # Optimize hook statement
    if node.type == "hook":
        check = __checkCondition(node[0])
        if check is not None:
            Console.debug("Optimizing hook at line %s", node.line)
            optimized = True
        
            if check is True:
                node.parent.replace(node, node[1])
            elif check is False:
                node.parent.replace(node, node[2])
                
    # Optimize switch statement
    if node.type == "switch" and node.discriminant.type in ("string", "number"):
        discriminant = node.discriminant.value
        fallback = None
        matcher = None
        allowed = ["default", "case"]
        
        for child in node:
            # Require that every case block ends with a break (no fall-throughs)
            if child.type == "case":
                block = child[len(child)-1]
                if len(block) == 0 or block[len(block)-1].type != "break":
                    Console.warn("Could not optimize switch statement (at line %s) because of fallthrough break statement.", node.line)
                    return False

            if child.type == "default":
                fallback = child.statements

            elif child.type == "case" and child.label.value == discriminant:
                matcher = child.statements
                
                # Remove break statement
                matcher.pop()
            
        if matcher or fallback:
            if not matcher:
                matcher = fallback
                
            node.parent.replace(node, matcher)
            Console.debug("Optimizing switch at line %s", node.line)
            optimized = True
    
    return optimized



#
# Implementation
#

def __checkCondition(node):
    """
    Checks a comparison for equality. Returns None when
    both, truely and falsy could not be deteted.
    """
    
    if node.type == "false":
        return False
    elif node.type == "true":
        return True
        
    elif node.type == "eq" or node.type == "strict_eq":
        return __compareNodes(node[0], node[1])
    elif node.type == "ne" or node.type == "strict_ne":
        return __invertResult(__compareNodes(node[0], node[1]))
        
    elif node.type == "not":
        return __invertResult(__checkCondition(node[0]))
        
    elif node.type == "and":
        first = __checkCondition(node[0])
        if first != None and not first:
            return False

        second = __checkCondition(node[1])
        if second != None and not second:
            return False
            
        if first and second:
            return True

    elif node.type == "or":
        first = __checkCondition(node[0])
        second = __checkCondition(node[1])
        if first != None and second != None:
            return first or second

    return None


def __invertResult(result):
    """
    Used to support the NOT operator.
    """
    
    if type(result) == bool:
        return not result
        
    return result


def __compareNodes(a, b):
    """
    This method compares two nodes from the tree regarding equality.
    It supports boolean, string and number type compares
    """
    
    if a.type == b.type:
        if a.type in ("string", "number"):
            return a.value == b.value
        elif a.type == "true":
            return True
        elif b.type == "false":
            return False    
            
    elif a.type in ("true", "false") and b.type in ("true", "false"):
        return False

    return None
    
########NEW FILE########
__FILENAME__ = Permutate
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

import jasy.js.parse.Parser as Parser
import jasy.core.Console as Console

from jasy.js.util import *


__all__ = ["patch"]


def __translateToJS(code):
    """ Returns the code equivalent of the stored value for the given key """
    
    if code is None:
        pass
    elif code is True:
        code = "true"
    elif code is False:
        code = "false"
    elif type(code) is str and code.startswith("{") and code.endswith("}"):
        pass
    elif type(code) is str and code.startswith("[") and code.endswith("]"):
        pass
    else:
        code = "\"%s\"" % code
        
    return code
    

def patch(node, permutation):
    """ Replaces all occourences with incoming values """

    modified = False
    
    if node.type == "dot" and node.parent.type == "call":
        assembled = assembleDot(node)
        
        # jasy.Env.getValue(key)
        if assembled == "jasy.Env.getValue" and node.parent.type == "call":
            callNode = node.parent
            params = callNode[1]
            name = params[0].value

            Console.debug("Found jasy.Env.getValue(%s) in line %s", name, node.line)

            replacement = __translateToJS(permutation.get(name))
            if replacement:
                replacementNode = Parser.parseExpression(replacement)
                callNode.parent.replace(callNode, replacementNode)
                modified = True

                Console.debug("Replaced with %s", replacement)
         
        
        # jasy.Env.isSet(key, expected)
        # also supports boolean like: jasy.Env.isSet(key)
        elif assembled == "jasy.Env.isSet" and node.parent.type == "call":

            callNode = node.parent
            params = callNode[1]
            name = params[0].value

            Console.debug("Found jasy.Env.isSet(%s) in line %s", name, node.line)

            replacement = __translateToJS(permutation.get(name))

            if replacement != None:
                # Auto-fill second parameter with boolean "true"
                expected = params[1] if len(params) > 1 else Parser.parseExpression("true")

                if expected.type in ("string", "number", "true", "false"):
                    parsedReplacement = Parser.parseExpression(replacement)
                    expectedValue = getattr(expected, "value", None)
                    
                    if expectedValue is not None:
                        if getattr(parsedReplacement, "value", None) is not None:
                            replacementResult = parsedReplacement.value in str(expected.value).split("|")
                        else:
                            replacementResult = parsedReplacement.type in str(expected.value).split("|")
                    else:
                        replacementResult = parsedReplacement.type == expected.type

                    # Do actual replacement
                    replacementNode = Parser.parseExpression("true" if replacementResult else "false")
                    callNode.parent.replace(callNode, replacementNode)
                    modified = True

                    Console.debug("Replaced with %s", "true" if replacementResult else "false")

        
        # jasy.Env.select(key, map)
        elif assembled == "jasy.Env.select" and node.parent.type == "call":
            Console.debug("Found jasy.Env.select() in line %s", node.line)

            callNode = node.parent
            params = callNode[1]
            replacement = __translateToJS(permutation.get(params[0].value))
            if replacement:
                parsedReplacement = Parser.parseExpression(replacement)
                if parsedReplacement.type != "string":
                    raise Exception("jasy.Env.select requires that the given replacement is of type string.")

                # Directly try to find matching identifier in second param (map)
                objectInit = params[1]
                if objectInit.type == "object_init":
                    fallbackNode = None
                    for propertyInit in objectInit:
                        if propertyInit[0].value == "default":
                            fallbackNode = propertyInit[1]

                        elif parsedReplacement.value in str(propertyInit[0].value).split("|"):
                            callNode.parent.replace(callNode, propertyInit[1])
                            modified = True
                            break

                    if not modified and fallbackNode is not None:
                        callNode.parent.replace(callNode, fallbackNode)
                        modified = True

                        Console.debug("Updated with %s", replacement)


    # Process children
    for child in reversed(node):
        if child != None:
            if patch(child, permutation):
                modified = True

    return modified
########NEW FILE########
__FILENAME__ = Unused
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

import jasy.js.parse.Node as Node
import jasy.js.parse.ScopeScanner as ScopeScanner

import jasy.core.Console as Console

__all__ = ["cleanup", "Error"]


#
# Public API
#

class Error(Exception):
    def __init__(self, name, line):
        self.__name = name
        self.__line = line
    
    def __str__(self):
        return "Unallowed private field access to %s at line %s!" % (self.__name, self.__line)



def cleanup(node):
    """
    """
    
    if not hasattr(node, "variables"):
        ScopeScanner.scan(node)

    # Re cleanup until nothing to remove is found
    x = 0
    cleaned = False
    
    Console.debug("Removing unused variables...")
    while True:
        x = x + 1
        #debug("Removing unused variables [Iteration: %s]...", x)
        Console.indent()

        if __cleanup(node):
            ScopeScanner.scan(node)
            cleaned = True
            Console.outdent()
        else:
            Console.outdent()
            break
        
    return cleaned



#
# Implementation
#

def __cleanup(node):
    """ The scanner part which looks for scopes with unused variables/params """
    
    cleaned = False
    
    for child in list(node):
        if child != None and __cleanup(child):
            cleaned = True

    if node.type == "script" and node.scope.unused and hasattr(node, "parent"):
        if __recurser(node, node.scope.unused):
            cleaned = True

    return cleaned
            
            
            
def __recurser(node, unused):
    """ 
    The cleanup part which always processes one scope and cleans up params and
    variable definitions which are unused
    """
    
    retval = False
    
    # Process children
    if node.type != "function":
        for child in node:
            # None children are allowed sometimes e.g. during array_init like [1,2,,,7,8]
            if child != None:
                if __recurser(child, unused):
                    retval = True
                    

    if node.type == "script" and hasattr(node, "parent"):
        # Remove unused parameters
        params = getattr(node.parent, "params", None)
        if params:
            # Start from back, as we can only remove params as long
            # as there is not a required one after the current one
            for identifier in reversed(params):
                if identifier.value in unused:
                    Console.debug("Removing unused parameter '%s' in line %s", identifier.value, identifier.line)
                    params.remove(identifier)
                    retval = True
                else:
                    break

        # Remove function names which are unused
        if node.parent.functionForm == "expressed_form":
            funcName = getattr(node.parent, "name", None)
            if funcName != None and funcName in unused:
                Console.debug("Removing unused function name at line %s" % node.line)
                del node.parent.name
                retval = True
                    
                    
    elif node.type == "function":
        # Remove full unused functions (when not in top-level scope)
        if node.functionForm == "declared_form" and getattr(node, "parent", None) and node.parent.type != "call":
            funcName = getattr(node, "name", None)
            if funcName != None and funcName in unused:
                Console.debug("Removing unused function declaration %s at line %s" % (funcName, node.line))
                node.parent.remove(node)
                retval = True
            
    
    elif node.type == "var":
        for decl in reversed(node):
            if getattr(decl, "name", None) in unused:
                if hasattr(decl, "initializer"):
                    init = decl.initializer
                    if init.type in ("null", "this", "true", "false", "identifier", "number", "string", "regexp"):
                        Console.debug("Removing unused primitive variable %s at line %s" % (decl.name, decl.line))
                        node.remove(decl)
                        retval = True
                        
                    elif init.type == "function" and (not hasattr(init, "name") or init.name in unused):
                        Console.debug("Removing unused function variable %s at line %s" % (decl.name, decl.line))
                        node.remove(decl)
                        retval = True
                    
                    # If we have only one child, we replace the whole var statement with just the init block
                    elif len(node) == 1:
                        semicolon = Node.Node(init.tokenizer, "semicolon")
                        semicolon.append(init, "expression")

                        # Protect non-expressions with parens
                        if init.type in ("array_init", "object_init"):
                            init.parenthesized = True
                        elif init.type == "call" and init[0].type == "function":
                            init[0].parenthesized = True
                        
                        node.parent.replace(node, semicolon)
                        retval = True

                    # If we are the last declaration, move it out of node and append after var block
                    elif node[-1] == decl or node[0] == decl:
                        isFirst = node[0] == decl
                        
                        node.remove(decl)
                        nodePos = node.parent.index(node)
                        semicolon = Node.Node(init.tokenizer, "semicolon")
                        semicolon.append(init, "expression")

                        # Protect non-expressions with parens
                        if init.type in ("array_init", "object_init"):
                            init.parenthesized = True
                        elif init.type == "call" and init[0].type == "function":
                            init[0].parenthesized = True

                        if isFirst:
                            node.parent.insert(nodePos, semicolon)
                        else:
                            node.parent.insert(nodePos + 1, semicolon)
                            
                        retval = True
                        
                    else:
                        Console.debug("Could not automatically remove unused variable %s at line %s without possible side-effects" % (decl.name, decl.line))
                    
                else:
                    node.remove(decl)
                    retval = True
                    
        if len(node) == 0:
            Console.debug("Removing empty 'var' block at line %s" % node.line)
            node.parent.remove(node)

    return retval

    
########NEW FILE########
__FILENAME__ = MetaData
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

class MetaData:
    """ 
    Data structure to hold all meta information. 
    
    A instance of this class is typically created by processing all 
    meta data relevant tags of all doc comments in the given node structure.

    Hint: Must be a clean data class without links to other 
    systems for optiomal cachability using Pickle
    """
    
    __slots__ = ["name", "requires", "optionals", "breaks", "assets"]
    
    def __init__(self, tree):
        self.name = None
        
        self.requires = set()
        self.optionals = set()
        self.breaks = set()
        self.assets = set()
        
        self.__inspect(tree)
        
        
    def __inspect(self, node):
        """ The internal inspection routine """
    
        # Parse comments
        comments = getattr(node, "comments", None)
        if comments:
            for comment in comments:
                commentTags = comment.getTags()
                if commentTags:

                    if "name" in commentTags:
                        self.name = list(commentTags["name"])[0]
                    if "require" in commentTags:
                        self.requires.update(commentTags["require"])
                    if "load" in commentTags:
                        # load is a special combination shorthand for requires + breaks
                        # This means load it but don't require it being loaded first
                        self.requires.update(commentTags["load"])
                        self.breaks.update(commentTags["load"])
                    if "optional" in commentTags:
                        self.optionals.update(commentTags["optional"])
                    if "break" in commentTags:
                        self.breaks.update(commentTags["break"])
                    if "asset" in commentTags:
                        self.assets.update(commentTags["asset"])

        # Process children
        for child in node:
            if child is not None:
                self.__inspect(child)

########NEW FILE########
__FILENAME__ = BlockReducer
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

import jasy.js.parse.Node as Node
import jasy.js.output.Compressor as Compressor

import jasy.js.parse.Lang

import jasy.core.Console as Console


__all__ = ["optimize", "Error"]


class Error(Exception):
    def __init__(self, line):
        self.__line = line


def optimize(node):
    Console.debug("Reducing block complexity...")
    Console.indent()
    result = __optimize(node, Compressor.Compressor())
    Console.outdent()
    return result
    

def __optimize(node, compressor):
    # Process from inside to outside
    # on a copy of the node to prevent it from forgetting children when structure is modified
    for child in list(node):
        # None children are allowed sometimes e.g. during array_init like [1,2,,,7,8]
        if child != None:
            __optimize(child, compressor)
    
    
    # Cleans up empty semicolon statements (or pseudo-empty)
    if node.type == "semicolon" and node.parent.type in ("block", "script"):
        expr = getattr(node, "expression", None)
        if not expr or expr.type in ("null", "this", "true", "false", "identifier", "number", "string", "regexp"):
            # Keep scrict mode hints
            if expr and expr.type is "string" and expr.value == "use strict":
                pass
            else:
                if expr is not None:
                    Console.debug("Remove empty statement at line %s of type: %s", expr.line, expr.type)
                node.parent.remove(node)
                return


    # Remove unneeded parens
    if getattr(node, "parenthesized", False):
        cleanParens(node)
    
    
    # Pre-compute numeric expressions where it makes sense
    if node.type in ("plus", "minus", "mul", "div", "mod") and node[0].type == "number" and node[1].type == "number":
        firstNumber = node[0]
        secondNumber = node[1]
        operator = node.type

        # Only do for real numeric values and not for protected strings (float differences between Python and JS)
        if type(firstNumber.value) == str or type(secondNumber.value) == str:
            pass
        elif operator == "plus":
            Console.debug("Precompute numeric %s operation at line: %s", operator, node.line)
            firstNumber.value += secondNumber.value
            node.parent.replace(node, firstNumber)
        elif operator == "minus":
            Console.debug("Precompute numeric %s operation at line: %s", operator, node.line)
            firstNumber.value -= secondNumber.value
            node.parent.replace(node, firstNumber)
        else:
            if operator == "mul":
                result = firstNumber.value * secondNumber.value
            elif operator == "div" and secondNumber.value is not 0:
                result = firstNumber.value / secondNumber.value
            elif operator == "mod":
                result = firstNumber.value % secondNumber.value
            else:
                result = None
            
            if result is not None and len(str(result)) < len(compressor.compress(node)):
                Console.debug("Precompute numeric %s operation at line: %s", operator, node.line)
                firstNumber.value = result
                node.parent.replace(node, firstNumber)


    # Pre-combine strings (even supports mixed string + number concats)
    elif node.type == "plus" and node[0].type in ("number", "string") and node[1].type in ("number", "string"):
        Console.debug("Joining strings at line: %s", node.line)
        node[0].value = "%s%s" % (node[0].value, node[1].value)
        node[0].type = "string"

        node.parent.replace(node, node[0])

    # Pre-combine last with last (special case e.g.: somevar + "hello" + "world")
    elif node.type == "plus" and node[0].type == "plus" and node[0][1].type in ("number", "string") and node[1].type in ("number", "string"):
        node[1].value = "%s%s" % (node[0][1].value, node[1].value)
        node[1].type = "string"

        node.replace(node[0], node[0][0])


    # Unwrap blocks
    if node.type == "block":
        if node.parent.type in ("try", "catch", "finally"):
            pass
        elif len(node) == 0:
            Console.debug("Replace empty block with semicolon at line: %s", node.line)
            repl = Node.Node(node.tokenizer, "semicolon")
            node.parent.replace(node, repl)
            node = repl
        elif len(node) == 1:
            if node.parent.type == "if" and node.rel == "thenPart" and hasattr(node.parent, "elsePart") and containsIf(node):
                # if with else where the thenBlock contains another if
                pass
            elif node.parent.type == "if" and node.rel == "thenPart" and containsIfElse(node):
                # if without else where the thenBlock contains a if-else
                pass
            elif node.parent.type in ("case", "default"):
                # virtual blocks inside case/default statements
                pass
            else:
                # debug("Removing block for single statement at line %s", node.line)
                node.parent.replace(node, node[0])
                node = node[0]
        else:
            node = combineToCommaExpression(node)
        
        
    # Remove "empty" semicolons which are inside a block/script parent
    if node.type == "semicolon":
        if not hasattr(node, "expression"):
            if node.parent.type in ("block", "script"):
                Console.debug("Remove empty semicolon expression at line: %s", node.line)
                node.parent.remove(node)
            elif node.parent.type == "if":
                rel = getattr(node, "rel", None)
                if rel == "elsePart":
                    Console.debug("Remove empty else part at line: %s", node.line)
                    node.parent.remove(node)
            
            
    # Process all if-statements
    if node.type == "if":
        condition = node.condition
        thenPart = node.thenPart
        elsePart = getattr(node, "elsePart", None)
        
        # Optimize for empty thenPart if elsePart is available
        if thenPart.type == "semicolon" and not hasattr(thenPart, "expression") and elsePart:
            if condition.type == "not":
                node.replace(condition, condition[0])
                condition = condition[0]
            else:
                repl = Node.Node(None, "not")
                node.replace(condition, repl)
                repl.append(condition)
                fixParens(condition)
                condition = repl
            
            node.replace(thenPart, elsePart)
            thenPart = elsePart
            elsePart = None
        
        # Optimize using hook operator
        if elsePart and thenPart.type == "return" and elsePart.type == "return" and hasattr(thenPart, "value") and hasattr(elsePart, "value"):
            # Combine return statement
            replacement = createReturn(createHook(condition, thenPart.value, elsePart.value))
            node.parent.replace(node, replacement)
            return

        # Check whether if-part ends with a return statement. Then
        # We do not need a else statement here and just can wrap the whole content
        # of the else block inside the parent
        if elsePart and endsWithReturnOrThrow(thenPart):
            reworkElse(node, elsePart)
            elsePart = None

        # Optimize using "AND" or "OR" operators
        # Combine multiple semicolon statements into one semicolon statement using an "comma" expression
        thenPart = combineToCommaExpression(thenPart)
        elsePart = combineToCommaExpression(elsePart)
        
        # Optimize remaining if or if-else constructs
        if elsePart:
            mergeParts(node, thenPart, elsePart, condition, compressor)
        elif thenPart.type == "semicolon":
            compactIf(node, thenPart, condition)


def reworkElse(node, elsePart):
    """ 
    If an if ends with a return/throw we are able to inline the content 
    of the else to the same parent as the if resides into. This method
    deals with all the nasty details of this operation.
    """
    
    target = node.parent
    targetIndex = target.index(node)+1

    # A workaround for compact if-else blocks
    # We are a elsePart of the if where we want to move our
    # content to. This cannot work. So we need to wrap ourself
    # into a block and move the else statements to this newly
    # established block
    if not target.type in ("block", "script"):
        newBlock = Node.Node(None, "block")
        
        # Replace node with newly created block and put ourself into it
        node.parent.replace(node, newBlock)
        newBlock.append(node)
        
        # Update the target and the index
        target = newBlock
        targetIndex = 1
        
    if not target.type in ("block", "script"):
        # print("No possible target found/created")
        return elsePart
        
    if elsePart.type == "block":
        for child in reversed(elsePart):
            target.insert(targetIndex, child)

        # Remove else block from if statement
        node.remove(elsePart)
            
    else:
        target.insert(targetIndex, elsePart)
        
    return  



def endsWithReturnOrThrow(node):
    """ 
    Used by the automatic elsePart removal logic to find out whether
    the given node ends with a return or throw which is bascially the allowance
    to remove the else keyword as this is not required to keep the logic intact.
    """
    
    if node.type in ("return", "throw"):
        return True
        
    elif node.type == "block":
        length = len(node)
        return length > 0 and node[length-1].type in ("return", "throw")
        
    return False
    
    
    
def mergeParts(node, thenPart, elsePart, condition, compressor):
    """
    Merges if statement with a elsePart using a hook. Supports two different ways of doing
    this: using a hook expression outside, or using a hook expression inside an assignment.
    
    Example:
    if(test) first(); else second()   => test ? first() : second();
    if(foo) x=1; else x=2             => x = foo ? 1 : 2;
    """
    
    if thenPart.type == "semicolon" and elsePart.type == "semicolon":
        # Combine two assignments or expressions
        thenExpression = getattr(thenPart, "expression", None)
        elseExpression = getattr(elsePart, "expression", None)
        if thenExpression and elseExpression:
            replacement = combineAssignments(condition, thenExpression, elseExpression, compressor) or combineExpressions(condition, thenExpression, elseExpression)
            if replacement:
                node.parent.replace(node, replacement)    


def cleanParens(node):
    """
    Automatically tries to remove superfluous parens which are sometimes added for more clearance
    and readability but which are not required for parsing and just produce overhead.
    """
    parent = node.parent

    if node.type == "function":
        # Ignore for direct execution functions. This is required
        # for parsing e.g. (function(){})(); which does not work
        # without parens around the function instance other than
        # priorities might suggest. It only works this way when being
        # part of assignment/declaration.
        if parent.type == "call" and parent.parent.type in ("declaration", "assign"):
            node.parenthesized = False
            
        # Need to make sure to not modify in cases where we use a "dot" operator e.g.
        # var x = (function(){ return 1; }).hide();
            
    elif node.type == "assign" and parent.type == "hook":
        node.parenthesized = node.rel == "condition"
                
    elif getattr(node, "rel", None) == "condition":
        # inside a condition e.g. while(condition) or for(;condition;) we do not need
        # parens aroudn an expression
        node.parenthesized = False
    
    elif node.type in jasy.js.parse.Lang.expressions and parent.type == "return":
        # Returns never need parens around the expression
        node.parenthesized = False
        
    elif node.type in jasy.js.parse.Lang.expressions and parent.type == "list" and parent.parent.type == "call":
        # Parameters don't need to be wrapped in parans
        node.parenthesized = False
        
    elif node.type in ("new", "string", "number", "boolean") and parent.type == "dot":
        # Constructs like (new foo.bar.Object).doSomething()
        # "new" is defined with higher priority than "dot" but in
        # this case it does not work without parens. Interestingly
        # the same works without issues when having "new_with_args" 
        # instead like: new foo.bar.Object("param").doSomething()
        pass
        
    elif node.type == "unary_plus" or node.type == "unary_minus":
        # Prevent unary operators from getting joined with parent
        # x+(+x) => x++x => FAIL
        pass
        
    elif node.type in jasy.js.parse.Lang.expressions and parent.type in jasy.js.parse.Lang.expressions:
        prio = jasy.js.parse.Lang.expressionOrder[node.type]
        parentPrio = jasy.js.parse.Lang.expressionOrder[node.parent.type]
        
        # Only higher priorities are optimized. Others are just to complex e.g.
        # "hello" + (3+4) + "world" is not allowed to be translated to 
        # "hello" + 3+4 + "world"
        if prio > parentPrio:
            node.parenthesized = False
        elif prio == parentPrio:
            if node.type == "hook":
                node.parenthesized = False


def fixParens(node):
    """ 
    Automatically wraps the given node into parens when it was moved into
    another block and is not parsed there in the same way as it was the case previously.
    The method needs to be called *after* the node has been moved to the target node.
    """
    parent = node.parent
    
    if parent.type in jasy.js.parse.Lang.expressions:
        prio = jasy.js.parse.Lang.expressionOrder[node.type]
        parentPrio = jasy.js.parse.Lang.expressionOrder[node.parent.type]
        
        needsParens = prio < parentPrio
        if needsParens:
            # debug("Adding parens around %s node at line: %s", node.type, node.line)
            node.parenthesized = needsParens


def combineToCommaExpression(node):
    """
    This method tries to combine a block with multiple statements into
    one semicolon statement with a comma expression containing all expressions
    from the previous block. This only works when the block exclusively consists
    of expressions as this do not work with other statements. Still this conversion
    reduces the size impact of many blocks and leads to the removal of a lot of 
    curly braces in the result code.
    
    Example: {x++;y+=3} => x++,x+=3
    """
    
    if node == None or node.type != "block":
        return node
        
    counter = 0
    for child in node:
        if child is None:
            pass
            
        elif child.type != "semicolon":
            return node
          
        else:
            counter = counter + 1
            
    if counter == 1:
        return node
    
    comma = Node.Node(node.tokenizer, "comma")
    
    for child in list(node):
        if child is None:
            pass

        # Ignore empty semicolons
        if hasattr(child, "expression"):
            comma.append(child.expression)
            
    semicolon = Node.Node(node.tokenizer, "semicolon")
    semicolon.append(comma, "expression")
    
    parent = node.parent
    parent.replace(node, semicolon)
    
    return semicolon


def compactIf(node, thenPart, condition):
    """
    Reduces the size of a if statement (without elsePart) using boolean operators
    instead of the typical keywords e.g. 
    "if(something)make()" is translated to "something&&make()"
    which is two characters shorter. This however only works when the
    thenPart is only based on expressions and does not contain other 
    statements.
    """
    
    thenExpression = getattr(thenPart, "expression", None)
    if not thenExpression:
        # Empty semicolon statement => translate if into semicolon statement
        node.remove(condition)
        node.remove(node.thenPart)
        node.append(condition, "expression")
        node.type = "semicolon"

    else:
        # Has expression => Translate IF using a AND or OR operator
        if condition.type == "not":
            replacement = Node.Node(thenPart.tokenizer, "or")
            condition = condition[0]
        else:
            replacement = Node.Node(thenPart.tokenizer, "and")

        replacement.append(condition)
        replacement.append(thenExpression)

        thenPart.append(replacement, "expression")

        fixParens(thenExpression)
        fixParens(condition)
        
        node.parent.replace(node, thenPart)


def containsIfElse(node):
    """ Checks whether the given node contains another if-else-statement """
    
    if node.type == "if" and hasattr(node, "elsePart"):
        return True

    for child in node:
        if child is None:
            pass
        
        # Blocks reset this if-else problem so we ignore them 
        # (and their content) for our scan.
        elif child.type == "block":
            pass
            
        # Script blocks reset as well (protected by other function)
        elif child.type == "script":
            pass
        
        elif containsIfElse(child):
            return True

    return False
    
    
def containsIf(node):
    """ Checks whether the given node contains another if-statement """
    
    if node.type == "if":
        return True

    for child in node:
        if child is None:
            pass
        
        # Blocks reset this if-else problem so we ignore them 
        # (and their content) for our scan.
        if child.type == "block":
            pass

        # Script blocks reset as well (protected by other function)
        elif child.type == "script":
            pass

        elif containsIf(child):
            return True

    return False    


def combineAssignments(condition, thenExpression, elseExpression, compressor):
    """ 
    Combines then and else expression to one assignment when they both assign 
    to the same target node and using the same operator. 
    """
    
    if thenExpression.type == "assign" and elseExpression.type == "assign":
        operator = getattr(thenExpression, "assignOp", None)
        if operator == getattr(elseExpression, "assignOp", None):
            if compressor.compress(thenExpression[0]) == compressor.compress(elseExpression[0]):
                hook = createHook(condition, thenExpression[1], elseExpression[1])
                fixParens(condition)
                fixParens(hook.thenPart)
                fixParens(hook.elsePart)
                thenExpression.append(hook)
                return thenExpression.parent


def combineExpressions(condition, thenExpression, elseExpression):
    """ Combines then and else expression using a hook statement. """
    
    hook = createHook(condition, thenExpression, elseExpression)
    semicolon = Node.Node(condition.tokenizer, "semicolon")
    semicolon.append(hook, "expression")
    
    fixParens(condition)
    fixParens(thenExpression)
    fixParens(elseExpression)
    
    return semicolon


def createReturn(value):
    """ Creates a return statement with the given value """
    
    ret = Node.Node(value.tokenizer, "return")
    ret.append(value, "value")
    return ret


def createHook(condition, thenPart, elsePart):
    """ Creates a hook expression with the given then/else parts """
    
    hook = Node.Node(condition.tokenizer, "hook")
    hook.append(condition, "condition")
    hook.append(thenPart, "thenPart")
    hook.append(elsePart, "elsePart")
    return hook
    

########NEW FILE########
__FILENAME__ = ClosureWrapper
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

# Via
# https://developer.mozilla.org/en/JavaScript/Reference/Global_Objects
GLOBALS = [
    "Boolean",
    "Number",
    "String",
    "Array",
    "Object",
    "Function",
    "RegExp",
    "Date",

    "Error",
    "EvalError",
    "RangeError",
    "ReferenceError",
    "SyntaxError",
    "TypeError",
    "URIError",

    "decodeURI",
    "decodeURIComponent",
    "encodeURI",
    "encodeURIComponent",

    "eval",
    "isFinite",
    "isNaN",
    "parseFloat",
    "parseInt",

    "Infinity",
    "Math",
    "NaN",
    "undefined"
]


def optimize(node):
    # TODO
    pass
########NEW FILE########
__FILENAME__ = CombineDeclarations
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

import jasy.js.parse.Node as Node
import jasy.core.Console as Console

__all__ = ["optimize", "Error"]



#
# Public API
#

class Error(Exception):
    def __init__(self, line):
        self.__line = line
        
        
def optimize(node):
    Console.debug("Combining declarations...")
    Console.indent()
    result = __optimize(node)
    Console.outdent()
    return result
    

def __optimize(node):
    
    # stabilize list during processing modifyable stuff
    copy = node
    if node.type in ("script", "block"):
        copy = list(node)
    
    for child in copy:
        # None children are allowed sometimes e.g. during array_init like [1,2,,,7,8]
        if child != None:
            __optimize(child)
        
    if node.type in ("script", "block"):
        __combineSiblings(node)
        
    if node.type == "script":
        __combineVarStatements(node)




#
# Merge direct variable siblings
#

def __combineSiblings(node):
    """Backwards processing and insertion into previous sibling if both are declarations""" 
    length = len(node)
    pos = length-1
    while pos > 0:
        child = node[pos]
        prevChild = node[pos-1]

        # Special FOR loop optimization, emulate faked VAR
        if child.type == "for" and prevChild.type == "var":
            setup = getattr(child, "setup", None)
            if setup and setup.type == "var":
                Console.debug("Removing for-loop setup section at line %s" % setup.line)
                child.remove(setup)
                child = setup    

        # Combine declarations of VAR statements
        if child.type == "var" and prevChild.type == "var":
            # debug("Combining var statement at line %s" % child.line)
            
            # Fix loop through casting node to list()
            for variable in list(child):
                prevChild.append(variable)
                
            if child in node:
                node.remove(child)
            
        pos -= 1




#
# Merge var statements, convert in-place to assignments in other locations (quite complex)
#

def __combineVarStatements(node):
    """Top level method called to optimize a script node"""
    
    if len(node.scope.declared) == 0:
        return
    
    firstVar = __findFirstVarStatement(node)
    
    # Special case, when a node has variables, but no valid "var" block to hold them
    # This happens in cases where there is a for-loop which contains a "var", but
    # there are no other variable declarations anywhere. In this case we are not able
    # to optimize the code further and just exit at this point
    
    # Only size-saving when there are multiple for-in loops, but no other var statement or first
    # "free" var declaration is after for-loops.
    if not firstVar:
        firstVar = Node.Node(None, "var")
        node.insert(0, firstVar)
    
    __patchVarStatements(node, firstVar)
    __cleanFirst(firstVar)
    
    # Remove unused "var"
    if len(firstVar) == 0:
        firstVar.parent.remove(firstVar)

    else:
        # When there is a classical for loop immediately after our 
        # first var statement, then we try to move the var declaration
        # into there as a setup expression
    
        firstVarParent = firstVar.parent
        firstVarPos = firstVarParent.index(firstVar)
        if len(firstVarParent) > firstVarPos+1:
            possibleForStatement = firstVarParent[firstVarPos+1]
            if possibleForStatement.type == "for" and not hasattr(possibleForStatement, "setup"):
                possibleForStatement.append(firstVar, "setup")

        
def __findFirstVarStatement(node):
    """Returns the first var statement of the given node. Ignores inner functions."""
    
    if node.type == "var":
        # Ignore variable blocks which are used as an iterator in for-in loops
        # In this case we return False, so that a new collector "var" is being created
        if getattr(node, "rel", None) == "iterator":
            return False
        else:
            return node
        
    for child in node:
        if child.type == "function":
            continue
        
        result = __findFirstVarStatement(child)
        if result:
            return result
        elif result is False:
            return False
    
    return None
        

def __cleanFirst(first):
    """ 
    Should remove double declared variables which have no initializer e.g.
    var s=3,s,s,t,s; => var s=3,t;
    """
    
    # Add all with initializer first
    known = set()
    for child in first:
        if hasattr(child, "initializer"):
            varName = getattr(child, "name", None)
            if varName != None:
                known.add(varName)
            else:
                # JS 1.7 Destructing Expression
                for varIdentifier in child.names:
                    known.add(varIdentifier.value)
    
    # Then add all remaining ones which are not added before
    # This implementation omits duplicates even if the assignments
    # are listed later in the original node.
    for child in list(first):
        # JS 1.7 Destructing Expression always have a initializer
        if not hasattr(child, "initializer"):
            if child.name in known:
                first.remove(child)
            else:
                known.add(child.name)


def __createSimpleAssignment(identifier, valueNode):
    assignNode = Node.Node(None, "assign")
    identNode = Node.Node(None, "identifier")
    identNode.value = identifier
    assignNode.append(identNode)
    assignNode.append(valueNode)

    return assignNode
    
    
def __createMultiAssignment(names, valueNode):
    assignNode = Node.Node(None, "assign")
    assignNode.append(names)
    assignNode.append(valueNode)

    return assignNode    


def __createDeclaration(name):
    declNode = Node.Node(None, "declaration")
    declNode.name = name
    declNode.readOnly = False
    return declNode


def __createIdentifier(value):
    identifier = Node.Node(None, "identifier")
    identifier.value = value
    return identifier    


def __patchVarStatements(node, firstVarStatement):
    """Patches all variable statements in the given node (works recursively) and replace them with assignments."""
    if node is firstVarStatement:
        return
        
    elif node.type == "function":
        # Don't process inner functions/scopes
        return
        
    elif node.type == "var":
        __rebuildAsAssignment(node, firstVarStatement)
        
    else:
        # Recursion into children
        # Create a cast to list() to keep loop stable during modification
        for child in list(node):
            __patchVarStatements(child, firstVarStatement)
            
            
def __rebuildAsAssignment(node, firstVarStatement):
    """Rebuilds the items of a var statement into a assignment list and moves declarations to the given var statement"""
    assignment = Node.Node(node.tokenizer, "semicolon")
    assignmentList = Node.Node(node.tokenizer, "comma")
    assignment.append(assignmentList, "expression")

    # Casting to list() creates a copy during the process (keeps loop stable)
    for child in list(node):
        if hasattr(child, "name"):
            # Cleanup initializer and move to assignment
            if hasattr(child, "initializer"):
                assign = __createSimpleAssignment(child.name, child.initializer)
                assignmentList.append(assign)
                
            firstVarStatement.append(child)
        
        else:
            # JS 1.7 Destructing Expression
            for identifier in child.names:
                firstVarStatement.append(__createDeclaration(identifier.value))

            if hasattr(child, "initializer"):
                assign = __createMultiAssignment(child.names, child.initializer)
                assignmentList.append(assign)
                
            node.remove(child)
                        
    # Patch parent node to contain assignment instead of declaration
    if len(assignmentList) > 0:
        node.parent.replace(node, assignment)
    
    # Special process for "for-in" loops
    # It is OK to be second because of assignments are not allowed at
    # all in for-in loops and so the first if basically does nothing
    # for these kind of statements.
    elif getattr(node, "rel", None) == "iterator":
        if hasattr(child, "name"):
            node.parent.replace(node, __createIdentifier(child.name))
        else:
            # JS 1.7 Destructing Expressions
            node.parent.replace(node, child.names)
    
    # Edge case. Not yet found if this happen realistically
    else:
        if hasattr(node, "rel"):
            Console.warn("Remove related node (%s) from parent: %s" % (node.rel, node))
            
        node.parent.remove(node)
        
    # Minor post-cleanup. Remove useless comma statement when only one expression is the result
    if len(assignmentList) == 1:
        assignment.replace(assignmentList, assignmentList[0])

########NEW FILE########
__FILENAME__ = CryptPrivates
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

import zlib, string, re
import jasy.core.Console as Console

__all__ = ["optimize", "Error"]



#
# Public API
#


class Error(Exception):
    def __init__(self, name, line):
        self.__name = name
        self.__line = line
    
    def __str__(self):
        return "Unallowed private field access to %s at line %s!" % (self.__name, self.__line)



def optimize(node, contextId=""):
    
    Console.debug("Crypting private fields...")
    Console.indent()
    
    coll = __search(node)

    repl = {}
    for name in coll:
        repl[name] = "__%s" % __encode("%s.%s" % (contextId, name[2:]))
        Console.debug("Replacing private field %s with %s (context: %s)", name, repl[name], contextId)
    
    Console.debug("Found %s private fields" % len(repl))
    modified, reduction = __replace(node, repl)
    
    Console.debug("Reduced size by %s bytes" % reduction)
    Console.outdent()
    
    return modified
    


#
# Internal API
#

__matcher = re.compile("__[a-zA-Z0-9]+")


def __search(node, coll=None):
    
    if coll is None:
        coll = set()
    
    if node.type == "assign" and node[0].type == "dot":
        # Only last dot child is relevant
        if node[0][1].type == "identifier":
            name = node[0][1].value
            if type(name) is str and __matcher.match(name):
                coll.add(name)
        
    elif node.type == "property_init":
        name = node[0].value
        if type(name) is str and __matcher.match(name):
            coll.add(name)

    for child in node:
        # None children are allowed sometimes e.g. during array_init like [1,2,,,7,8]
        if child != None:
            __search(child, coll)
            
    return coll



def __replace(node, repl):
    modified = False
    reduction = 0
    
    if node.type == "identifier" and getattr(node, "parent", None):
        # Only rename items which are part of a dot operator
        if node.parent.type in ("dot", "property_init") and type(node.value) is str and __matcher.match(node.value):
            if node.value in repl:
                reduction = reduction + len(node.value) - len(repl[node.value])
                node.value = repl[node.value]
                modified = True
            elif node.value.endswith("__"):
                # Ignore __defineGetter__, __defineSetter__, __proto__
                pass
            else:
                raise Error(node.value, node.line)
        
    for child in node:
        # None children are allowed sometimes e.g. during array_init like [1,2,,,7,8]
        if child != None:
            subModified, subReduction = __replace(child, repl)
            modified = modified or subModified
            reduction = reduction + subReduction
            
    return modified, reduction
    
    
    
def __encode(value, alphabet=string.ascii_letters+string.digits):
    
    num = zlib.adler32(value.encode("utf-8"))
    
    if num == 0:
        return alphabet[0]
    
    arr = []
    base = len(alphabet)
    
    while num:
        rem = num % base
        num = num // base
        arr.append(alphabet[rem])
    
    arr.reverse()
    
    return "".join(arr)
    
########NEW FILE########
__FILENAME__ = LocalVariables
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

import string
import jasy.js.tokenize.Lang

__all__ = ["optimize", "Error"]



#
# Public API
#


class Error(Exception):
    def __init__(self, name, line):
        self.__name = name
        self.__line = line
    
    def __str__(self):
        return "Unallowed private field access to %s at line %s!" % (self.__name, self.__line)


def optimize(node):
    """
    Node to optimize with the global variables to ignore as names
    """
    
    blocked = set(node.scope.shared.keys())
    blocked.update(node.scope.modified)
    
    __patch(node, blocked)



#
# Implementation
#

def __baseEncode(num, alphabet=string.ascii_letters):
    if (num == 0):
        return alphabet[0]
    arr = []
    base = len(alphabet)
    while num:
        rem = num % base
        num = num // base
        arr.append(alphabet[rem])
    arr.reverse()
    return "".join(arr)


def __patch(node, blocked=None, enable=False, translate=None):
    # Start with first level scopes (global scope should not be affected)
    if node.type == "script" and hasattr(node, "parent"):
        enable = True
    
    
    #
    # GENERATE TRANSLATION TABLE
    #
    if enable:
        scope = getattr(node, "scope", None)
        
        if scope:
            declared = scope.declared
            params = scope.params
            
            if declared or params:
                usedRepl = set()
        
                if not translate:
                    translate = {}
                else:
                    # copy only the interesting ones from the shared set
                    newTranslate = {}
            
                    for name in scope.shared:
                        if name in translate:
                            newTranslate[name] = translate[name]
                            usedRepl.add(translate[name])
                    translate = newTranslate
            
                # Merge in usage data into declaration map to have
                # the possibilities to sort translation priority to
                # the usage number. Pretty cool.
        
                names = set()
                if params:
                    names.update(params)
                if declared:
                    names.update(declared)
                
                # We have to sort the set() before to support both Python 3.2 and 
                # Python 3.3 with identical results.
                namesSorted = list(reversed(sorted(sorted(names), key=lambda x: scope.accessed[x] if x in scope.accessed else 0)))

                # Extend translation map by new replacements for locally 
                # declared variables. Automatically ignores keywords. Only
                # blocks usage of replacements where the original variable from
                # outer scope is used. This way variable names may be re-used more
                # often than in the original code.
                pos = 0
                for name in namesSorted:
                    while True:
                        repl = __baseEncode(pos)
                        pos += 1
                        if not repl in usedRepl and not repl in jasy.js.tokenize.Lang.keywords and not repl in blocked:
                            break
                
                    # print("Translate: %s => %s" % (name, repl))
                    translate[name] = repl


    #
    # APPLY TRANSLATION
    #
    if translate:
        # Update param names in outer function block
        if node.type == "script" and hasattr(node, "parent"):
            function = node.parent
            if function.type == "function" and hasattr(function, "params"):
                for identifier in function.params:
                    if identifier.value in translate:
                        identifier.value = translate[identifier.value]
            
        # Update names of exception objects
        elif node.type == "exception" and node.value in translate:
            node.value = translate[node.value]

        # Update function name
        elif node.type == "function" and hasattr(node, "name") and node.name in translate:
            node.name = translate[node.name]
    
        # Update identifiers
        elif node.type == "identifier":
            # Ignore param blocks from inner functions
            if node.parent.type == "list" and getattr(node.parent, "rel", None) == "params":
                pass
                
            # Ignore keyword in property initialization names
            elif node.parent.type == "property_init" and node.parent[0] == node:
                pass
            
            # Update all identifiers which are 
            # a) not part of a dot operator
            # b) first in a dot operator
            elif node.parent.type != "dot" or node.parent.index(node) == 0:
                if node.value in translate:
                    node.value = translate[node.value]
                
        # Update declarations (as part of a var statement)
        elif node.type == "declaration":
            varName = getattr(node, "name", None)
            if varName != None:
                if varName in translate:
                    node.name = varName = translate[varName]
            else:
                # JS 1.7 Destructing Expression
                for identifier in node.names:
                    if identifier.value in translate:
                        identifier.value = translate[identifier.value]


    #
    # PROCESS CHILDREN
    #
    for child in node:
        # None children are allowed sometimes e.g. during array_init like [1,2,,,7,8]
        if child != None:
            __patch(child, blocked, enable, translate)



########NEW FILE########
__FILENAME__ = Translation
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

import re, copy, polib

import jasy.js.parse.Node as Node
import jasy.item.Translation as Translation

from jasy import UserError
import jasy.core.Console as Console


#
# Public API
#

__all__ = ["hasText", "optimize", "collectTranslations"]

translationFunctions = ("tr", "trc", "trn", "marktr")


def hasText(node):
    if node.type == "call":
        funcName = None
        
        if node[0].type == "identifier":
            funcName = node[0].value
        elif node[0].type == "dot" and node[0][1].type == "identifier":
            funcName = node[0][1].value
        
        if funcName in translationFunctions:
            return True
            
    # Process children
    for child in node:
        if child != None:
            ret = hasText(child)
            if ret:
                return True
    
    return False


def parseParams(params, funcName):

    basic = None
    plural = None
    context = None

    if funcName == "tr" or funcName == "trn" or funcName == "marktr":
        basic = params[0].value
    elif funcName == "trc":
        context = params[0].value
        basic = params[1].value
    
    if funcName == "trn":
        plural = params[1].value

    return basic, plural, context



def __collectionRecurser(node, collection):
    if node.type == "call":
        funcName = None
        
        if node[0].type == "identifier":
            funcName = node[0].value
        elif node[0].type == "dot" and node[0][1].type == "identifier":
            funcName = node[0][1].value
        
        if funcName in translationFunctions:
            translationId = Translation.generateId(*parseParams(node[1], funcName))
            if translationId:
                if translationId in collection:
                    collection[translationId].append(node.line)
                else:
                    collection[translationId] = [node.line]

    # Process children
    for child in node:
        if child != None:
            __collectionRecurser(child, collection)

    return collection


def collectTranslations(node):
    return __collectionRecurser(node, dict())



def optimize(node, translation):
  return __recurser(node, translation.getTable())
  


#
# Patch :: Implementation
#


__replacer = re.compile("(%[0-9])")


def __splitTemplate(value, valueParams):
    """ 
    Split string into plus-expression(s) 

    - patchParam: string node containing the placeholders
    - valueParams: list of params to inject
    """

    # Convert list with nodes into Python dict
    # [a, b, c] => {0:a, 1:b, 2:c}
    mapper = { pos: value for pos, value in enumerate(valueParams) }
    
    result = []
    splits = __replacer.split(value)
    if len(splits) == 1:
        return None
    
    pair = Node.Node(None, "plus")

    for entry in splits:
        if entry == "":
            continue
            
        if len(pair) == 2:
            newPair = Node.Node(None, "plus")
            newPair.append(pair)
            pair = newPair

        if __replacer.match(entry):
            pos = int(entry[1]) - 1
            
            # Items might be added multiple times. Copy to protect original.
            try:
                repl = mapper[pos]
            except KeyError:
                raise UserError("Invalid positional value: %s in %s" % (entry, value))
            
            copied = copy.deepcopy(mapper[pos])
            if copied.type not in ("identifier", "call"):
                copied.parenthesized = True
            pair.append(copied)
            
        else:
            child = Node.Node(None, "string")
            child.value = entry
            pair.append(child)
            
    return pair


def __recurser(node, table):

    counter = 0

    # Process children
    for child in list(node):
        if child is not None:
            counter += __recurser(child, table)
                    
    # Process all method calls
    if node.type == "call":
        funcName = None
        funcNameNode = None
        
        # Uses global translation method (not typical)
        if node[0].type == "identifier":
            funcNameNode = node[0]

        # Uses namespaced translation method.
        # Typically core.locale.Translation.tr() or Translation.tr()
        elif node[0].type == "dot" and node[0][1].type == "identifier":
            funcNameNode = node[0][1]

        # Gettext methods only at the moment
        funcName = funcNameNode and funcNameNode.value
        if funcName in translationFunctions:
            Console.debug("Found translation method %s in %s", funcName, node.line)
            Console.indent()

            params = node[1]
            
            # Remove marktr() calls
            if funcName == "marktr":
                node.parent.remove(node)

            # Verify param types
            elif params[0].type is not "string":
                # maybe something marktr() relevant being used, in this case we need to keep the call and inline the data
                pass
                
            # Error handling
            elif (funcName == "trn" or funcName == "trc") and params[1].type != "string":
                Console.warn("Expecting translation string to be type string: %s at line %s" % (params[1].type, params[1].line))

            # Signature tr(msg, arg1, ...)
            elif funcName == "tr":
                key = params[0].value
                if key in table:
                    params[0].value = table[key]
                
                counter += 1

                if len(params) == 1:
                    node.parent.replace(node, params[0])
                else:
                    replacement = __splitTemplate(params[0].value, params[1:])
                    if replacement:
                        node.parent.replace(node, replacement)

                    
            # Signature trc(context, msg, arg1, ...)
            elif funcName == "trc":
                key = "%s[C:%s]" % (params[1].value, params[0].value)
                if key in table:
                    params[1].value = table[key]

                counter += 1

                if len(params) == 2:
                    node.parent.replace(node, params[1])
                else:
                    replacement = __splitTemplate(params[1].value, params[2:])
                    if replacement:
                        node.parent.replace(node, replacement)


            # Signature trn(msgSingular, msgPlural, int, arg1, ...)
            elif funcName == "trn":
                key = "%s[N:%s]" % (params[0].value, params[1].value)
                if not key in table:
                    Console.outdent()
                    return counter

                counter += 1

                # Use optimized trnc() method instead of trn()
                funcNameNode.value = "trnc"
                
                # Remove first two string parameters
                params.remove(params[0])
                params.remove(params[0])

                # Inject new object into params
                container = Node.Node(None, "object_init")
                params.insert(0, container)

                # Create new construction with all properties generated from the translation table
                for plural in table[key]:
                    pluralEntry = Node.Node(None, "property_init")
                    pluralEntryIdentifier = Node.Node(None, "identifier")
                    pluralEntryIdentifier.value = plural
                    pluralEntryValue = Node.Node(None, "string")
                    pluralEntryValue.value = table[key][plural]
                    pluralEntry.append(pluralEntryIdentifier)
                    pluralEntry.append(pluralEntryValue)
                    container.append(pluralEntry)

                # Replace strings with plus operations to omit complex client side string operation
                if len(params) > 2:
                    for pluralEntry in container:
                        replacement = __splitTemplate(pluralEntry[1].value, params[2:])
                        if replacement:
                            pluralEntry.replace(pluralEntry[1], replacement)

                    # When all variables have been patched in all string with placeholder
                    # we are able to remove the whole list of placeholder values afterwards
                    while len(params) > 2:
                        params.pop()

            Console.outdent()

    return counter

########NEW FILE########
__FILENAME__ = Compressor
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

import re, sys, json

from jasy.js.tokenize.Lang import keywords
from jasy.js.parse.Lang import expressions, futureReserved

all = [ "Compressor" ]

high_unicode = re.compile(r"\\u[2-9A-Fa-f][0-9A-Fa-f]{3}")
ascii_encoder = json.JSONEncoder(ensure_ascii=True)
unicode_encoder = json.JSONEncoder(ensure_ascii=False)

#
# Class
#

class Compressor:
    __semicolonSymbol = ";"
    __commaSymbol = ","
    

    def __init__(self, format=None):
        if format:
            if format.has("semicolon"):
                self.__semicolonSymbol = ";\n"
            
            if format.has("comma"):
                self.__commaSymbol = ",\n"
            
        self.__forcedSemicolon = False



    #
    # Main
    #

    def compress(self, node):
        type = node.type
        result = None
    
        if type in self.__simple:
            result = type
        elif type in self.__prefixes:
            if getattr(node, "postfix", False):
                result = self.compress(node[0]) + self.__prefixes[node.type]
            else:
                result = self.__prefixes[node.type] + self.compress(node[0])
        
        elif type in self.__dividers:
            first = self.compress(node[0])
            second = self.compress(node[1])
            divider = self.__dividers[node.type]
            
            # Fast path
            if node.type not in ("plus", "minus"):
                result = "%s%s%s" % (first, divider, second)
                
            # Special code for dealing with situations like x + ++y and y-- - x
            else:
                result = first
                if first.endswith(divider):
                    result += " "
            
                result += divider
            
                if second.startswith(divider):
                    result += " "
                
                result += second

        else:
            try:
                result = getattr(self, "type_%s" % type)(node)
            except KeyError:
                print("Compressor does not support type '%s' from line %s in file %s" % (type, node.line, node.getFileName()))
                sys.exit(1)
            
        if getattr(node, "parenthesized", None):
            return "(%s)" % result
        else:
            return result
    
    
    
    #
    # Helpers
    #
    
    def __statements(self, node):
        result = []
        for child in node:
            result.append(self.compress(child))

        return "".join(result)
    
    def __handleForcedSemicolon(self, node):
        if node.type == "semicolon" and not hasattr(node, "expression"):
            self.__forcedSemicolon = True

    def __addSemicolon(self, result):
        if not result.endswith(self.__semicolonSymbol):
            if self.__forcedSemicolon:
                self.__forcedSemicolon = False
        
            return result + self.__semicolonSymbol

        else:
            return result

    def __removeSemicolon(self, result):
        if self.__forcedSemicolon:
            self.__forcedSemicolon = False
            return result
    
        if result.endswith(self.__semicolonSymbol):
            return result[:-len(self.__semicolonSymbol)]
        else:
            return result


    #
    # Data
    #
    
    __simple_property = re.compile(r"^[a-zA-Z_$][a-zA-Z0-9_$]*$")
    __number_property = re.compile(r"^[0-9]+$")

    __simple = ["true", "false", "null", "this", "debugger"]

    __dividers = {
        "plus"        : '+',
        "minus"       : '-',
        "mul"         : '*',
        "div"         : '/',
        "mod"         : '%',
        "dot"         : '.',
        "or"          : "||",
        "and"         : "&&",
        "strict_eq"   : '===',
        "eq"          : '==',
        "strict_ne"   : '!==',
        "ne"          : '!=',
        "lsh"         : '<<',
        "le"          : '<=',
        "lt"          : '<',
        "ursh"        : '>>>',
        "rsh"         : '>>',
        "ge"          : '>=',
        "gt"          : '>',
        "bitwise_or"  : '|',
        "bitwise_xor" : '^',
        "bitwise_and" : '&'
    }

    __prefixes = {    
        "increment"   : "++",
        "decrement"   : "--",
        "bitwise_not" : '~',
        "not"         : "!",
        "unary_plus"  : "+",
        "unary_minus" : "-",
        "delete"      : "delete ",
        "new"         : "new ",
        "typeof"      : "typeof ",
        "void"        : "void "
    }



    #
    # Script Scope
    #

    def type_script(self, node):
        return self.__statements(node)



    #
    # Expressions
    #
    
    def type_comma(self, node):
        return self.__commaSymbol.join(map(self.compress, node))

    def type_object_init(self, node):
        return "{%s}" % self.__commaSymbol.join(map(self.compress, node))

    def type_property_init(self, node):
        key = self.compress(node[0])
        value = self.compress(node[1])

        if type(key) in (int, float):
            pass

        elif self.__number_property.match(key):
            pass

        # Protect keywords and special characters
        elif key in keywords or key in futureReserved or not self.__simple_property.match(key):
            key = self.type_string(node[0])

        return "%s:%s" % (key, value)
        
    def type_array_init(self, node):
        def helper(child):
            return self.compress(child) if child != None else ""
    
        return "[%s]" % ",".join(map(helper, node))

    def type_array_comp(self, node):
        return "[%s %s]" % (self.compress(node.expression), self.compress(node.tail))    

    def type_string(self, node):
        # Omit writing real high unicode character which are not supported well by browsers
        ascii = ascii_encoder.encode(node.value)

        if high_unicode.search(ascii):
            return ascii
        else:
            return unicode_encoder.encode(node.value)

    def type_number(self, node):
        value = node.value

        # Special handling for protected float/exponential
        if type(value) == str:
            # Convert zero-prefix
            if value.startswith("0.") and len(value) > 2:
                value = value[1:]
                
            # Convert zero postfix
            elif value.endswith(".0"):
                value = value[:-2]

        elif int(value) == value and node.parent.type != "dot":
            value = int(value)

        return "%s" % value

    def type_regexp(self, node):
        return node.value

    def type_identifier(self, node):
        return node.value

    def type_list(self, node):
        return ",".join(map(self.compress, node))

    def type_index(self, node):
        return "%s[%s]" % (self.compress(node[0]), self.compress(node[1]))

    def type_declaration(self, node):
        names = getattr(node, "names", None)
        if names:
            result = self.compress(names)
        else:
            result = node.name    

        initializer = getattr(node, "initializer", None)
        if initializer:
            result += "=%s" % self.compress(node.initializer)

        return result

    def type_assign(self, node):
        assignOp = getattr(node, "assignOp", None)
        operator = "=" if not assignOp else self.__dividers[assignOp] + "="
    
        return self.compress(node[0]) + operator + self.compress(node[1])

    def type_call(self, node):
        return "%s(%s)" % (self.compress(node[0]), self.compress(node[1]))

    def type_new_with_args(self, node):
        result = "new %s" % self.compress(node[0])
        
        # Compress new Object(); => new Object;
        if len(node[1]) > 0:
            result += "(%s)" % self.compress(node[1])
        else:
            parent = getattr(node, "parent", None)
            if parent and parent.type is "dot":
                result += "()"
            
        return result

    def type_exception(self, node):
        return node.value
    
    def type_generator(self, node):
        """ Generator Expression """
        result = self.compress(getattr(node, "expression"))
        tail = getattr(node, "tail", None)
        if tail:
            result += " %s" % self.compress(tail)

        return result

    def type_comp_tail(self, node):
        """  Comprehensions Tails """
        result = self.compress(getattr(node, "for"))
        guard = getattr(node, "guard", None)
        if guard:
            result += "if(%s)" % self.compress(guard)

        return result    
    
    def type_in(self, node):
        first = self.compress(node[0])
        second = self.compress(node[1])
    
        if first.endswith("'") or first.endswith('"'):
            pattern = "%sin %s"
        else:
            pattern = "%s in %s"
    
        return pattern % (first, second)
    
    def type_instanceof(self, node):
        first = self.compress(node[0])
        second = self.compress(node[1])

        return "%s instanceof %s" % (first, second)    
    
    

    #
    # Statements :: Core
    #

    def type_block(self, node):
        return "{%s}" % self.__removeSemicolon(self.__statements(node))
    
    def type_let_block(self, node):
        begin = "let(%s)" % ",".join(map(self.compress, node.variables))
        if hasattr(node, "block"):
            end = self.compress(node.block)
        elif hasattr(node, "expression"):
            end = self.compress(node.expression)    
    
        return begin + end

    def type_const(self, node):
        return self.__addSemicolon("const %s" % self.type_list(node))

    def type_var(self, node):
        return self.__addSemicolon("var %s" % self.type_list(node))

    def type_let(self, node):
        return self.__addSemicolon("let %s" % self.type_list(node))

    def type_semicolon(self, node):
        expression = getattr(node, "expression", None)
        return self.__addSemicolon(self.compress(expression) if expression else "")

    def type_label(self, node):
        return self.__addSemicolon("%s:%s" % (node.label, self.compress(node.statement)))

    def type_break(self, node):
        return self.__addSemicolon("break" if not hasattr(node, "label") else "break %s" % node.label)

    def type_continue(self, node):
        return self.__addSemicolon("continue" if not hasattr(node, "label") else "continue %s" % node.label)


    #
    # Statements :: Functions
    #

    def type_function(self, node):
        if node.type == "setter":
            result = "set"
        elif node.type == "getter":
            result = "get"
        else:
            result = "function"
        
        name = getattr(node, "name", None)
        if name:
            result += " %s" % name
    
        params = getattr(node, "params", None)
        result += "(%s)" % self.compress(params) if params else "()"
    
        # keep expression closure format (may be micro-optimized for other code, too)
        if getattr(node, "expressionClosure", False):
            result += self.compress(node.body)
        else:
            result += "{%s}" % self.__removeSemicolon(self.compress(node.body))
        
        return result

    def type_getter(self, node):
        return self.type_function(node)
    
    def type_setter(self, node):
        return self.type_function(node)
    
    def type_return(self, node):
        result = "return"
        if hasattr(node, "value"):
            valueCode = self.compress(node.value)

            # Micro optimization: Don't need a space when a block/map/array/group/strings are returned
            if not valueCode.startswith(("(","[","{","'",'"',"!","-","/")): 
                result += " "

            result += valueCode

        return self.__addSemicolon(result)



    #
    # Statements :: Exception Handling
    #            
    
    def type_throw(self, node):
        return self.__addSemicolon("throw %s" % self.compress(node.exception))

    def type_try(self, node):
        result = "try%s" % self.compress(node.tryBlock)
    
        for catch in node:
            if catch.type == "catch":
                if hasattr(catch, "guard"):
                    result += "catch(%s if %s)%s" % (self.compress(catch.exception), self.compress(catch.guard), self.compress(catch.block))
                else:
                    result += "catch(%s)%s" % (self.compress(catch.exception), self.compress(catch.block))

        if hasattr(node, "finallyBlock"):
            result += "finally%s" % self.compress(node.finallyBlock)

        return result



    #
    # Statements :: Loops
    #    
    
    def type_while(self, node):
        result = "while(%s)%s" % (self.compress(node.condition), self.compress(node.body))
        self.__handleForcedSemicolon(node.body)
        return result


    def type_do(self, node):
        # block unwrapping don't help to reduce size on this loop type
        # but if it happens (don't like to modify a global function to fix a local issue), we
        # need to fix the body and re-add braces around the statement
        body = self.compress(node.body)
        if not body.startswith("{"):
            body = "{%s}" % body
        
        return self.__addSemicolon("do%swhile(%s)" % (body, self.compress(node.condition)))


    def type_for_in(self, node):
        # Optional variable declarations
        varDecl = getattr(node, "varDecl", None)

        # Body is optional - at least in comprehensions tails
        body = getattr(node, "body", None)
        if body:
            body = self.compress(body)
        else:
            body = ""
        
        result = "for"
        if node.isEach:
            result += " each"
    
        result += "(%s in %s)%s" % (self.__removeSemicolon(self.compress(node.iterator)), self.compress(node.object), body)
    
        if body:
            self.__handleForcedSemicolon(node.body)
        
        return result
    
    
    def type_for(self, node):
        setup = getattr(node, "setup", None)
        condition = getattr(node, "condition", None)
        update = getattr(node, "update", None)

        result = "for("
        result += self.__addSemicolon(self.compress(setup) if setup else "")
        result += self.__addSemicolon(self.compress(condition) if condition else "")
        result += self.compress(update) if update else ""
        result += ")%s" % self.compress(node.body)

        self.__handleForcedSemicolon(node.body)
        return result
    
       
       
    #       
    # Statements :: Conditionals
    #

    def type_hook(self, node):
        """aka ternary operator"""
        condition = node.condition
        thenPart = node.thenPart
        elsePart = node.elsePart
    
        if condition.type == "not":
            [thenPart,elsePart] = [elsePart,thenPart]
            condition = condition[0]
    
        return "%s?%s:%s" % (self.compress(condition), self.compress(thenPart), self.compress(elsePart))
    
    
    def type_if(self, node):
        result = "if(%s)%s" % (self.compress(node.condition), self.compress(node.thenPart))

        elsePart = getattr(node, "elsePart", None)
        if elsePart:
            result += "else"

            elseCode = self.compress(elsePart)
        
            # Micro optimization: Don't need a space when the child is a block
            # At this time the brace could not be part of a map declaration (would be a syntax error)
            if not elseCode.startswith(("{", "(", ";")):
                result += " "        
            
            result += elseCode
        
            self.__handleForcedSemicolon(elsePart)
        
        return result


    def type_switch(self, node):
        result = "switch(%s){" % self.compress(node.discriminant)
        for case in node:
            if case.type == "case":
                labelCode = self.compress(case.label)
                if labelCode.startswith('"'):
                    result += "case%s:" % labelCode
                else:
                    result += "case %s:" % labelCode
            elif case.type == "default":
                result += "default:"
            else:
                continue
        
            for statement in case.statements:
                temp = self.compress(statement)
                if len(temp) > 0:
                    result += self.__addSemicolon(temp)
        
        return "%s}" % self.__removeSemicolon(result)
        
########NEW FILE########
__FILENAME__ = Formatting
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

__all__ = ["Formatting"]


class Formatting:
    """
    Configures an formatting object which can be used to compress classes afterwards.
    The optimization set is frozen after initialization which also generates the unique
    key based on the given formatting options.
    """
    
    __key = None

    
    def __init__(self, *args):
        self.__formatting = set()
        
        for identifier in args:
            self.__formatting.add(identifier)
            
        self.__key = "+".join(sorted(self.__formatting))
        
        
    def has(self, key):
        """
        Whether the given formatting is enabled.
        """

        return key in self.__formatting
    
    
    def enable(self, flag):
        self.__formatting.add(flag)
        self.__key = None


    def disable(self, flag):
        self.__formatting.remove(flag)
        self.__key = None        
        
        
    def getKey(self):
        """
        Returns a unique key to identify this formatting set
        """

        if self.__key is None:
            self.__key = "+".join(sorted(self.__formatting))
        
        return self.__key


    # Map Python built-ins
    __repr__ = getKey
    __str__ = getKey



########NEW FILE########
__FILENAME__ = Optimization
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

import jasy.js.optimize.CryptPrivates as CryptPrivates
import jasy.js.optimize.BlockReducer as BlockReducer
import jasy.js.optimize.LocalVariables as LocalVariables
import jasy.js.optimize.CombineDeclarations as CombineDeclarations
import jasy.js.optimize.ClosureWrapper as ClosureWrapper


__all__ = ["Error", "Optimization"]


class Error(Exception):
    """
    Error object which is raised whenever an optimization could not be applied correctly.
    """
    
    def __init__(self, msg):
        self.__msg = msg
    
    def __str__(self):
        return "Error during optimization! %s" % (self.__msg)



class Optimization:
    """
    Configures an optimization object which can be used to compress classes afterwards.
    The optimization set is frozen after initialization which also generates the unique
    key based on the given optimizations.
    """
    
    __key = None
    
    def __init__(self, *args):
        self.__optimizations = set()
        
        for flag in args:
            self.__optimizations.add(flag)


    def has(self, flag):
        """
        Whether the given optimization is enabled.
        """
        
        return flag in self.__optimizations


    def enable(self, flag):
        self.__optimizations.add(flag)
        self.__key = None
        
        
    def disable(self, flag):
        self.__optimizations.remove(flag)
        self.__key = None
        

    def apply(self, tree):
        """
        Applies the configured optimizations to the given node tree. Modifies the tree in-place
        to be sure to have a deep copy if you need the original one. It raises an error instance
        whenever any optimization could not be applied to the given tree.
        """
        
        enabled = self.__optimizations
        
        if "wrap" in enabled:
            try:
                ClosureWrapper.optimize(tree)
            except CryptPrivates.Error as err:
                raise Error(err)
            
        if "declarations" in enabled:
            try:
                CombineDeclarations.optimize(tree)
            except CombineDeclarations.Error as err:
                raise Error(err)

        if "blocks" in enabled:
            try:
                BlockReducer.optimize(tree)
            except BlockReducer.Error as err:
                raise Error(err)

        if "variables" in enabled:
            try:
                LocalVariables.optimize(tree)
            except LocalVariables.Error as err:
                raise Error(err)

        if "privates" in enabled:
            try:
                CryptPrivates.optimize(tree, tree.fileId)
            except CryptPrivates.Error as err:
                raise Error(err)
                
                
    def getKey(self):
        """
        Returns a unique key to identify this optimization set
        """
        
        if self.__key is None:
            self.__key = "+".join(sorted(self.__optimizations))
        
        return self.__key
        
        
    # Map Python built-ins
    __repr__ = getKey
    __str__ = getKey        
########NEW FILE########
__FILENAME__ = Lang
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

futureReserved = set([
    "abstract",
    "boolean",
    "byte",
    "char",
    "class",
    "const",
    "debugger",
    "double",
    "enum",
    "export",
    "extends",
    "final",
    "float",
    "goto",
    "implements",
    "import",
    "int",
    "interface",
    "long",
    "native",
    "package",
    "private",
    "protected",
    "public",
    "short",
    "static",
    "super",
    "synchronized",
    "throws",
    "transient",
    "volatile" 
])


statements = [
    # With semicolon at end
    "semicolon",
    "return",
    "throw",
    "label",
    "break",
    "continue",
    "var",
    "const",
    "debugger",

    # Only semicolon when no-block braces are created
    "block",
    "let_block",
    "while",
    "do",
    "for",
    "for_in",
    "if",
    "switch",
    "hook",
    "with",

    # no semicolons
    # function, setter and getter as statement_form or declared_form
    "function", 
    "setter",
    "getter",
    "try",
    "label"
]


# All allowed expression types of JavaScript 1.7
# They may be separated by "comma" which is quite of special 
# and not allowed everywhere e.g. in conditional statements
expressions = [
    # Primary Expression - Part 1 (expressed form)
    "function",

    # Primary Expression - Part 2
    "object_init",
    "array_init",
    "array_comp",
    
    # Primary Expression - Part 3
    "let",

    # Primary Expression - Part 4
    "null", 
    "this", 
    "true", 
    "false", 
    "identifier", 
    "number", 
    "string", 
    "regexp",

    # Member Expression - Part 1
    "new_with_args",
    "new",

    # Member Expression - Part 2
    "dot",
    "call",
    "index",

    # Unary Expression
    "unary_plus",
    "unary_minus",
    "delete",
    "void",
    "typeof",
    "not",
    "bitwise_not",
    "increment",
    "decrement",

    # Multiply Expression
    "mul",
    "div",
    "mod",

    # Add Expression
    "plus",
    "minus",
    
    # Shift Expression
    "lsh",
    "rsh",
    "ursh",
    
    # Relational Expression
    "lt",
    "le",
    "ge",
    "gt",
    "in",
    "instanceof",
    
    # Equality Expression
    "eq",
    "ne",
    "strict_eq",
    "strict_ne",
    
    # BitwiseAnd Expression
    "bitwise_and",
    
    # BitwiseXor Expression
    "bitwise_xor",
    
    # BitwiseOr Expression
    "bitwise_or",
    
    # And Expression
    "and",
    
    # Or Expression
    "or",
    
    # Conditional Expression
    "hook",
    
    # Assign Expression
    "assign",
    
    # Expression
    "comma"
]




def __createOrder():
    expressions = [
        ["comma"],
        ["assign"],
        ["hook"],
        ["or"],
        ["and"],
        ["bitwise_or"],
        ["bitwise_xor",],
        ["bitwise_and"],
        ["eq","ne","strict_eq","strict_ne"],
        ["lt","le","ge","gt","in","instanceof"],
        ["lsh","rsh","ursh"],
        ["plus","minus"],
        ["mul","div","mod"],
        ["unary_plus","unary_minus","delete","void","typeof","not","bitwise_not","increment","decrement"],
        ["dot","call","index"],
        ["new_with_args","new"],
        ["null","this","true","false","identifier","number","string","regexp"],
        ["let"],
        ["object_init","array_init","array_comp"],
        ["function"]
    ]
    
    result = {}
    for priority, itemList in enumerate(expressions):
        for item in itemList:
            result[item] = priority
            
    return result
    
expressionOrder = __createOrder()


########NEW FILE########
__FILENAME__ = Node
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

#
# License: MPL 1.1/GPL 2.0/LGPL 2.1
# Authors: 
#   - Brendan Eich <brendan@mozilla.org> (Original JavaScript) (2004)
#   - Sebastian Werner <info@sebastian-werner.net> (Refactoring Python) (2010)
#

import json, copy

class Node(list):
    
    __slots__ = [
        # core data
        "line", "type", "tokenizer", "start", "end", "rel", "parent", 
        
        # dynamic added data by other modules
        "comments", "scope", 
        
        # node type specific
        "value", "expression", "body", "functionForm", "parenthesized", "fileId", "params", 
        "name", "readOnly", "initializer", "condition", "isLoop", "isEach", "object", "assignOp",
        "iterator", "thenPart", "exception", "elsePart", "setup", "postfix", "update", "tryBlock",
        "block", "defaultIndex", "discriminant", "label", "statements", "finallyBlock", 
        "statement", "variables", "names", "guard", "for", "tail", "expressionClosure"
    ]
    
    
    def __init__(self, tokenizer=None, type=None, args=[]):
        list.__init__(self)
        
        self.start = 0
        self.end = 0
        self.line = None
        
        if tokenizer:
            token = getattr(tokenizer, "token", None)
            if token:
                # We may define a custom type but use the same positioning as another token
                # e.g. transform curlys in block nodes, etc.
                self.type = type if type else getattr(token, "type", None)
                self.line = token.line
                
                # Start & end are file positions for error handling.
                self.start = token.start
                self.end = token.end
            
            else:
                self.type = type
                self.line = tokenizer.line
                self.start = None
                self.end = None

            self.tokenizer = tokenizer
            
        elif type:
            self.type = type

        for arg in args:
            self.append(arg)
            
            
    def getUnrelatedChildren(self):
        """Collects all unrelated children"""
        
        collection = []
        for child in self:
            if not hasattr(child, "rel"):
                collection.append(child)
            
        return collection
        

    def getChildrenLength(self, filter=True):
        """Number of (per default unrelated) children"""
        
        count = 0
        for child in self:
            if not filter or not hasattr(child, "rel"):
                count += 1
        return count
            
    
    def remove(self, kid):
        """Removes the given kid"""
        
        if not kid in self:
            raise Exception("Given node is no child!")
        
        if hasattr(kid, "rel"):
            delattr(self, kid.rel)
            del kid.rel
            del kid.parent
            
        list.remove(self, kid)
        
        
    def insert(self, index, kid):
        """Inserts the given kid at the given index"""
        
        if index is None:
            return self.append(kid)
            
        if hasattr(kid, "parent"):
            kid.parent.remove(kid)
            
        kid.parent = self

        return list.insert(self, index, kid)
            

    def append(self, kid, rel=None):
        """Appends the given kid with an optional relation hint"""
        
        # kid can be null e.g. [1, , 2].
        if kid:
            if hasattr(kid, "parent"):
                kid.parent.remove(kid)
            
            # Debug
            if not isinstance(kid, Node):
                raise Exception("Invalid kid: %s" % kid)
            
            if hasattr(kid, "tokenizer"):
                if hasattr(kid, "start"):
                    if not hasattr(self, "start") or self.start == None or kid.start < self.start:
                        self.start = kid.start

                if hasattr(kid, "end"):
                    if not hasattr(self, "end") or self.end == None or self.end < kid.end:
                        self.end = kid.end
                
            kid.parent = self
            
            # alias for function
            if rel != None:
                setattr(self, rel, kid)
                setattr(kid, "rel", rel)

        # Block None kids when they should be related
        if not kid and rel:
            return
            
        return list.append(self, kid)

    
    def replace(self, kid, repl):
        """Replaces the given kid with a replacement kid"""
        
        if repl in self:
            self.remove(repl)
        
        self[self.index(kid)] = repl
        
        if hasattr(kid, "rel"):
            repl.rel = kid.rel
            setattr(self, kid.rel, repl)
            
            # cleanup old kid
            delattr(kid, "rel")
            
            
        elif hasattr(repl, "rel"):
            # delete old relation on new child
            delattr(repl, "rel")

        delattr(kid, "parent")
        repl.parent = self
        
        return kid
        

    def toXml(self, format=True, indent=0, tab="  "):
        """Converts the node to XML"""

        lead = tab * indent if format else ""
        innerLead = tab * (indent+1) if format else ""
        lineBreak = "\n" if format else ""

        relatedChildren = []
        attrsCollection = []
        
        for name in self.__slots__:
            # "type" is used as node name - no need to repeat it as an attribute
            # "parent" is a relation to the parent node - for serialization we ignore these at the moment
            # "rel" is used internally to keep the relation to the parent - used by nodes which need to keep track of specific children
            # "start" and "end" are for debugging only
            if hasattr(self, name) and name not in ("type", "parent", "comments", "rel", "start", "end") and name[0] != "_":
                value = getattr(self, name)
                if isinstance(value, Node):
                    if hasattr(value, "rel"):
                        relatedChildren.append(value)

                elif type(value) in (bool, int, float, str, list, set, dict):
                    if type(value) == bool:
                        value = "true" if value else "false" 
                    elif type(value) in (int, float):
                        value = str(value)
                    elif type(value) in (list, set, dict):
                        if type(value) == dict:
                            value = value.keys()
                        if len(value) == 0:
                            continue
                        try:
                            value = ",".join(value)
                        except TypeError:
                            raise Exception("Invalid attribute list child at: %s" % name)
                            
                    attrsCollection.append('%s=%s' % (name, json.dumps(value)))

        attrs = (" " + " ".join(attrsCollection)) if len(attrsCollection) > 0 else ""
        
        comments = getattr(self, "comments", None)
        scope = getattr(self, "scope", None)
        
        if len(self) == 0 and len(relatedChildren) == 0 and (not comments or len(comments) == 0) and not scope:
            result = "%s<%s%s/>%s" % (lead, self.type, attrs, lineBreak)

        else:
            result = "%s<%s%s>%s" % (lead, self.type, attrs, lineBreak)
            
            if comments:
                for comment in comments:
                    result += '%s<comment context="%s" variant="%s">%s</comment>%s' % (innerLead, comment.context, comment.variant, comment.text, lineBreak)
                    
            if scope:
                for statKey in scope:
                    statValue = scope[statKey]
                    if statValue != None and len(statValue) > 0:
                        if type(statValue) is set:
                            statValue = ",".join(statValue)
                        elif type(statValue) is dict:
                            statValue = ",".join(statValue.keys())
                        
                        result += '%s<stat name="%s">%s</stat>%s' % (innerLead, statKey, statValue, lineBreak)

            for child in self:
                if not child:
                    result += "%s<none/>%s" % (innerLead, lineBreak)
                elif not hasattr(child, "rel"):
                    result += child.toXml(format, indent+1)
                elif not child in relatedChildren:
                    raise Exception("Oops, irritated by non related: %s in %s - child says it is related as %s" % (child.type, self.type, child.rel))

            for child in relatedChildren:
                result += "%s<%s>%s" % (innerLead, child.rel, lineBreak)
                result += child.toXml(format, indent+2)
                result += "%s</%s>%s" % (innerLead, child.rel, lineBreak)

            result += "%s</%s>%s" % (lead, self.type, lineBreak)

        return result
        
        
    def __deepcopy__(self, memo):
        """Used by deepcopy function to clone Node instances"""
        
        # Create copy
        if hasattr(self, "tokenizer"):
            result = Node(tokenizer=self.tokenizer)
        else:
            result = Node(type=self.type)
        
        # Copy children
        for child in self:
            if child is None:
                list.append(result, None)
            else:
                # Using simple list appends for better performance
                childCopy = copy.deepcopy(child, memo)
                childCopy.parent = result
                list.append(result, childCopy)
        
        # Sync attributes
        # Note: "parent" attribute is handled by append() already
        for name in self.__slots__:
            if hasattr(self, name) and not name in ("parent", "tokenizer"):
                value = getattr(self, name)
                if value is None:
                    pass
                elif type(value) in (bool, int, float, str):
                    setattr(result, name, value)
                elif type(value) in (list, set, dict, Node):
                    setattr(result, name, copy.deepcopy(value, memo))
                # Scope can be assigned (will be re-created when needed for the copied node)
                elif name == "scope":
                    result.scope = self.scope

        return result
        
        
    def getSource(self):
        """Returns the source code of the node"""

        if not self.tokenizer:
            raise Exception("Could not find source for node '%s'" % node.type)
            
        if getattr(self, "start", None) is not None:
            if getattr(self, "end", None) is not None:
                return self.tokenizer.source[self.start:self.end]
            return self.tokenizer.source[self.start:]
    
        if getattr(self, "end", None) is not None:
            return self.tokenizer.source[:self.end]
    
        return self.tokenizer.source[:]


    # Map Python built-ins
    __repr__ = toXml
    __str__ = toXml
    
    
    def __eq__(self, other):
        return self is other

    def __bool__(self): 
        return True

########NEW FILE########
__FILENAME__ = Parser
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

#
# License: MPL 1.1/GPL 2.0/LGPL 2.1
# Authors: 
#   - Brendan Eich <brendan@mozilla.org> (Original JavaScript) (2004-2010)
#   - Sebastian Werner <info@sebastian-werner.net> (Python Port) (2010-2012)
#

import jasy.js.tokenize.Tokenizer
import jasy.js.parse.VanillaBuilder
import jasy.js.tokenize.Lang

__all__ = [ "parse", "parseExpression" ]

def parseExpression(source, fileId=None, line=1, builder=None):
    if builder == None:
        builder = jasy.js.parse.VanillaBuilder.VanillaBuilder()
    
    # Convert source into expression statement to be friendly to the Tokenizer
    if not source.endswith(";"):
        source = source + ";"
    
    tokenizer = jasy.js.tokenize.Tokenizer.Tokenizer(source, fileId, line)
    staticContext = StaticContext(False, builder)
    
    return Expression(tokenizer, staticContext)



def parse(source, fileId=None, line=1, builder=None):
    if builder == None:
        builder = jasy.js.parse.VanillaBuilder.VanillaBuilder()
    
    tokenizer = jasy.js.tokenize.Tokenizer.Tokenizer(source, fileId, line)
    staticContext = StaticContext(False, builder)
    node = Script(tokenizer, staticContext)
    
    # store fileId on top-level node
    node.fileId = tokenizer.fileId
    
    # add missing comments e.g. empty file with only a comment etc.
    # if there is something non-attached by an inner node it is attached to
    # the top level node, which is not correct, but might be better than
    # just ignoring the comment after all.
    if len(node) > 0:
        builder.COMMENTS_add(node[-1], None, tokenizer.getComments())
    else:
        builder.COMMENTS_add(node, None, tokenizer.getComments())
    
    if not tokenizer.done():
        raise SyntaxError("Unexpected end of file", tokenizer)

    return node



class SyntaxError(Exception):
    def __init__(self, message, tokenizer):
        Exception.__init__(self, "Syntax error: %s\n%s:%s" % (message, tokenizer.fileId, tokenizer.line))


# Used as a status container during tree-building for every def body and the global body
class StaticContext(object):
    # inFunction is used to check if a return stm appears in a valid context.
    def __init__(self, inFunction, builder):
        # Whether this is inside a function, mostly True, only for top-level scope it's False
        self.inFunction = inFunction
        
        self.hasEmptyReturn = False
        self.hasReturnWithValue = False
        self.isGenerator = False
        self.blockId = 0
        self.builder = builder
        self.statementStack = []
        
        # Sets to store variable uses
        # self.functions = set()
        # self.variables = set()
        
        # Status
        # self.needsHoisting = False
        self.bracketLevel = 0
        self.curlyLevel = 0
        self.parenLevel = 0
        self.hookLevel = 0
        
        # Configure strict ecmascript 3 mode
        self.ecma3OnlyMode = False
        
        # Status flag during parsing
        self.inForLoopInit = False


def Script(tokenizer, staticContext):
    """Parses the toplevel and def bodies."""
    node = Statements(tokenizer, staticContext)
    
    # change type from "block" to "script" for script root
    node.type = "script"
    
    # copy over data from compiler context
    # node.functions = staticContext.functions
    # node.variables = staticContext.variables

    return node
    

def nest(tokenizer, staticContext, node, func, end=None):
    """Statement stack and nested statement handler."""
    staticContext.statementStack.append(node)
    node = func(tokenizer, staticContext)
    staticContext.statementStack.pop()
    end and tokenizer.mustMatch(end)
    
    return node


def Statements(tokenizer, staticContext):
    """Parses a list of Statements."""

    builder = staticContext.builder
    node = builder.BLOCK_build(tokenizer, staticContext.blockId)
    staticContext.blockId += 1

    builder.BLOCK_hoistLets(node)
    staticContext.statementStack.append(node)

    prevNode = None
    while not tokenizer.done() and tokenizer.peek(True) != "right_curly":
        comments = tokenizer.getComments()
        childNode = Statement(tokenizer, staticContext)
        builder.COMMENTS_add(childNode, prevNode, comments)
        builder.BLOCK_addStatement(node, childNode)
        prevNode = childNode

    staticContext.statementStack.pop()
    builder.BLOCK_finish(node)

    # if getattr(node, "needsHoisting", False):
    #     # TODO
    #     raise Exception("Needs hoisting went true!!!")
    #     builder.setHoists(node.id, node.variables)
    #     # Propagate up to the function.
    #     staticContext.needsHoisting = True

    return node


def Block(tokenizer, staticContext):
    tokenizer.mustMatch("left_curly")
    node = Statements(tokenizer, staticContext)
    tokenizer.mustMatch("right_curly")
    
    return node


def Statement(tokenizer, staticContext):
    """Parses a Statement."""

    tokenType = tokenizer.get(True)
    builder = staticContext.builder

    # Cases for statements ending in a right curly return early, avoiding the
    # common semicolon insertion magic after this switch.
    
    if tokenType == "function":
        # "declared_form" extends functions of staticContext, "statement_form" doesn'tokenizer.
        if len(staticContext.statementStack) > 1:
            kind = "statement_form"
        else:
            kind = "declared_form"
        
        return FunctionDefinition(tokenizer, staticContext, True, kind)
        
        
    elif tokenType == "left_curly":
        node = Statements(tokenizer, staticContext)
        tokenizer.mustMatch("right_curly")
        
        return node
        
        
    elif tokenType == "if":
        node = builder.IF_build(tokenizer)
        builder.IF_setCondition(node, ParenExpression(tokenizer, staticContext))
        staticContext.statementStack.append(node)
        builder.IF_setThenPart(node, Statement(tokenizer, staticContext))

        if tokenizer.match("else"):
            comments = tokenizer.getComments()
            elsePart = Statement(tokenizer, staticContext)
            builder.COMMENTS_add(elsePart, node, comments)
            builder.IF_setElsePart(node, elsePart)

        staticContext.statementStack.pop()
        builder.IF_finish(node)
        
        return node
        
        
    elif tokenType == "switch":
        # This allows CASEs after a "default", which is in the standard.
        node = builder.SWITCH_build(tokenizer)
        builder.SWITCH_setDiscriminant(node, ParenExpression(tokenizer, staticContext))
        staticContext.statementStack.append(node)

        tokenizer.mustMatch("left_curly")
        tokenType = tokenizer.get()
        
        while tokenType != "right_curly":
            if tokenType == "default":
                if node.defaultIndex >= 0:
                    raise SyntaxError("More than one switch default", tokenizer)
                    
                childNode = builder.DEFAULT_build(tokenizer)
                builder.SWITCH_setDefaultIndex(node, len(node)-1)
                tokenizer.mustMatch("colon")
                builder.DEFAULT_initializeStatements(childNode, tokenizer)
                
                while True:
                    tokenType=tokenizer.peek(True)
                    if tokenType == "case" or tokenType == "default" or tokenType == "right_curly":
                        break
                    builder.DEFAULT_addStatement(childNode, Statement(tokenizer, staticContext))
                
                builder.DEFAULT_finish(childNode)

            elif tokenType == "case":
                childNode = builder.CASE_build(tokenizer)
                builder.CASE_setLabel(childNode, Expression(tokenizer, staticContext))
                tokenizer.mustMatch("colon")
                builder.CASE_initializeStatements(childNode, tokenizer)

                while True:
                    tokenType=tokenizer.peek(True)
                    if tokenType == "case" or tokenType == "default" or tokenType == "right_curly":
                        break
                    builder.CASE_addStatement(childNode, Statement(tokenizer, staticContext))
                
                builder.CASE_finish(childNode)

            else:
                raise SyntaxError("Invalid switch case", tokenizer)

            builder.SWITCH_addCase(node, childNode)
            tokenType = tokenizer.get()

        staticContext.statementStack.pop()
        builder.SWITCH_finish(node)

        return node
        

    elif tokenType == "for":
        node = builder.FOR_build(tokenizer)
        forBlock = None
        
        if tokenizer.match("identifier") and tokenizer.token.value == "each":
            builder.FOR_rebuildForEach(node)
            
        tokenizer.mustMatch("left_paren")
        tokenType = tokenizer.peek()
        childNode = None
        
        if tokenType != "semicolon":
            staticContext.inForLoopInit = True
            
            if tokenType == "var" or tokenType == "const":
                tokenizer.get()
                childNode = Variables(tokenizer, staticContext)
            
            elif tokenType == "let":
                tokenizer.get()

                if tokenizer.peek() == "left_paren":
                    childNode = LetBlock(tokenizer, staticContext, False)
                    
                else:
                    # Let in for head, we need to add an implicit block
                    # around the rest of the for.
                    forBlock = builder.BLOCK_build(tokenizer, staticContext.blockId)
                    staticContext.blockId += 1
                    staticContext.statementStack.append(forBlock)
                    childNode = Variables(tokenizer, staticContext, forBlock)
                
            else:
                childNode = Expression(tokenizer, staticContext)
            
            staticContext.inForLoopInit = False

        if childNode and tokenizer.match("in"):
            builder.FOR_rebuildForIn(node)
            builder.FOR_setObject(node, Expression(tokenizer, staticContext), forBlock)
            
            if childNode.type == "var" or childNode.type == "let":
                if len(childNode) != 1:
                    raise SyntaxError("Invalid for..in left-hand side", tokenizer)

                builder.FOR_setIterator(node, childNode, forBlock)
                
            else:
                builder.FOR_setIterator(node, childNode, forBlock)

        else:
            builder.FOR_setSetup(node, childNode)
            tokenizer.mustMatch("semicolon")
            
            if node.isEach:
                raise SyntaxError("Invalid for each..in loop", tokenizer)
                
            if tokenizer.peek() == "semicolon":
                builder.FOR_setCondition(node, None)
            else:
                builder.FOR_setCondition(node, Expression(tokenizer, staticContext))
            
            tokenizer.mustMatch("semicolon")
            
            if tokenizer.peek() == "right_paren":
                builder.FOR_setUpdate(node, None)
            else:    
                builder.FOR_setUpdate(node, Expression(tokenizer, staticContext))
        
        tokenizer.mustMatch("right_paren")
        builder.FOR_setBody(node, nest(tokenizer, staticContext, node, Statement))
        
        if forBlock:
            builder.BLOCK_finish(forBlock)
            staticContext.statementStack.pop()
    
        builder.FOR_finish(node)
        return node
        
        
    elif tokenType == "while":
        node = builder.WHILE_build(tokenizer)
        
        builder.WHILE_setCondition(node, ParenExpression(tokenizer, staticContext))
        builder.WHILE_setBody(node, nest(tokenizer, staticContext, node, Statement))
        builder.WHILE_finish(node)
        
        return node                                    
        
        
    elif tokenType == "do":
        node = builder.DO_build(tokenizer)
        
        builder.DO_setBody(node, nest(tokenizer, staticContext, node, Statement, "while"))
        builder.DO_setCondition(node, ParenExpression(tokenizer, staticContext))
        builder.DO_finish(node)
        
        if not staticContext.ecma3OnlyMode:
            # <script language="JavaScript"> (without version hints) may need
            # automatic semicolon insertion without a newline after do-while.
            # See http://bugzilla.mozilla.org/show_bug.cgi?id=238945.
            tokenizer.match("semicolon")
            return node

        # NO RETURN
      
      
    elif tokenType == "break" or tokenType == "continue":
        if tokenType == "break":
            node = builder.BREAK_build(tokenizer) 
        else:
            node = builder.CONTINUE_build(tokenizer)

        if tokenizer.peekOnSameLine() == "identifier":
            tokenizer.get()
            
            if tokenType == "break":
                builder.BREAK_setLabel(node, tokenizer.token.value)
            else:
                builder.CONTINUE_setLabel(node, tokenizer.token.value)

        statementStack = staticContext.statementStack
        i = len(statementStack)
        label = node.label if hasattr(node, "label") else None

        if label:
            while True:
                i -= 1
                if i < 0:
                    raise SyntaxError("Label not found", tokenizer)
                if getattr(statementStack[i], "label", None) == label:
                    break

            # 
            # Both break and continue to label need to be handled specially
            # within a labeled loop, so that they target that loop. If not in
            # a loop, then break targets its labeled statement. Labels can be
            # nested so we skip all labels immediately enclosing the nearest
            # non-label statement.
            # 
            while i < len(statementStack) - 1 and statementStack[i+1].type == "label":
                i += 1
                
            if i < len(statementStack) - 1 and getattr(statementStack[i+1], "isLoop", False):
                i += 1
            elif tokenType == "continue":
                raise SyntaxError("Invalid continue", tokenizer)
                
        else:
            while True:
                i -= 1
                if i < 0:
                    if tokenType == "break":
                        raise SyntaxError("Invalid break", tokenizer)
                    else:
                        raise SyntaxError("Invalid continue", tokenizer)

                if getattr(statementStack[i], "isLoop", False) or (tokenType == "break" and statementStack[i].type == "switch"):
                    break
        
        if tokenType == "break":
            builder.BREAK_finish(node)
        else:
            builder.CONTINUE_finish(node)
        
        # NO RETURN


    elif tokenType == "try":
        node = builder.TRY_build(tokenizer)
        builder.TRY_setTryBlock(node, Block(tokenizer, staticContext))
        
        while tokenizer.match("catch"):
            childNode = builder.CATCH_build(tokenizer)
            tokenizer.mustMatch("left_paren")
            nextTokenType = tokenizer.get()
            
            if nextTokenType == "left_bracket" or nextTokenType == "left_curly":
                # Destructured catch identifiers.
                tokenizer.unget()
                exception = DestructuringExpression(tokenizer, staticContext, True)
            
            elif nextTokenType == "identifier":
                exception = builder.CATCH_wrapException(tokenizer)
            
            else:
                raise SyntaxError("Missing identifier in catch", tokenizer)
                
            builder.CATCH_setException(childNode, exception)
            
            if tokenizer.match("if"):
                if staticContext.ecma3OnlyMode:
                    raise SyntaxError("Illegal catch guard", tokenizer)
                    
                if node.getChildrenLength() > 0 and not node.getUnrelatedChildren()[0].guard:
                    raise SyntaxError("Guarded catch after unguarded", tokenizer)
                    
                builder.CATCH_setGuard(childNode, Expression(tokenizer, staticContext))
                
            else:
                builder.CATCH_setGuard(childNode, None)
            
            tokenizer.mustMatch("right_paren")
            
            builder.CATCH_setBlock(childNode, Block(tokenizer, staticContext))
            builder.CATCH_finish(childNode)
            
            builder.TRY_addCatch(node, childNode)
        
        builder.TRY_finishCatches(node)
        
        if tokenizer.match("finally"):
            builder.TRY_setFinallyBlock(node, Block(tokenizer, staticContext))
            
        if node.getChildrenLength() == 0 and not hasattr(node, "finallyBlock"):
            raise SyntaxError("Invalid try statement", tokenizer)
            
        builder.TRY_finish(node)
        return node
        

    elif tokenType == "catch" or tokenType == "finally":
        raise SyntaxError(tokens[tokenType] + " without preceding try", tokenizer)


    elif tokenType == "throw":
        node = builder.THROW_build(tokenizer)
        
        builder.THROW_setException(node, Expression(tokenizer, staticContext))
        builder.THROW_finish(node)
        
        # NO RETURN


    elif tokenType == "return":
        node = returnOrYield(tokenizer, staticContext)
        
        # NO RETURN


    elif tokenType == "with":
        node = builder.WITH_build(tokenizer)

        builder.WITH_setObject(node, ParenExpression(tokenizer, staticContext))
        builder.WITH_setBody(node, nest(tokenizer, staticContext, node, Statement))
        builder.WITH_finish(node)

        return node


    elif tokenType == "var" or tokenType == "const":
        node = Variables(tokenizer, staticContext)
        
        # NO RETURN
        

    elif tokenType == "let":
        if tokenizer.peek() == "left_paren":
            node = LetBlock(tokenizer, staticContext, True)
        else:
            node = Variables(tokenizer, staticContext)
        
        # NO RETURN
        

    elif tokenType == "debugger":
        node = builder.DEBUGGER_build(tokenizer)
        
        # NO RETURN
        

    elif tokenType == "newline" or tokenType == "semicolon":
        node = builder.SEMICOLON_build(tokenizer)

        builder.SEMICOLON_setExpression(node, None)
        builder.SEMICOLON_finish(tokenizer)
        
        return node


    else:
        if tokenType == "identifier":
            tokenType = tokenizer.peek()

            # Labeled statement.
            if tokenType == "colon":
                label = tokenizer.token.value
                statementStack = staticContext.statementStack
               
                i = len(statementStack)-1
                while i >= 0:
                    if getattr(statementStack[i], "label", None) == label:
                        raise SyntaxError("Duplicate label", tokenizer)
                    
                    i -= 1
               
                tokenizer.get()
                node = builder.LABEL_build(tokenizer)
                
                builder.LABEL_setLabel(node, label)
                builder.LABEL_setStatement(node, nest(tokenizer, staticContext, node, Statement))
                builder.LABEL_finish(node)
                
                return node

        # Expression statement.
        # We unget the current token to parse the expression as a whole.
        node = builder.SEMICOLON_build(tokenizer)
        tokenizer.unget()
        builder.SEMICOLON_setExpression(node, Expression(tokenizer, staticContext))
        node.end = node.expression.end
        builder.SEMICOLON_finish(node)
        
        # NO RETURN
        

    MagicalSemicolon(tokenizer)
    return node



def MagicalSemicolon(tokenizer):
    if tokenizer.line == tokenizer.token.line:
        tokenType = tokenizer.peekOnSameLine()
    
        if tokenType != "end" and tokenType != "newline" and tokenType != "semicolon" and tokenType != "right_curly":
            raise SyntaxError("Missing ; before statement", tokenizer)
    
    tokenizer.match("semicolon")

    

def returnOrYield(tokenizer, staticContext):
    builder = staticContext.builder
    tokenType = tokenizer.token.type

    if tokenType == "return":
        if not staticContext.inFunction:
            raise SyntaxError("Return not in function", tokenizer)
            
        node = builder.RETURN_build(tokenizer)
        
    else:
        if not staticContext.inFunction:
            raise SyntaxError("Yield not in function", tokenizer)
            
        staticContext.isGenerator = True
        node = builder.YIELD_build(tokenizer)

    nextTokenType = tokenizer.peek(True)
    if nextTokenType != "end" and nextTokenType != "newline" and nextTokenType != "semicolon" and nextTokenType != "right_curly" and (tokenType != "yield" or (nextTokenType != tokenType and nextTokenType != "right_bracket" and nextTokenType != "right_paren" and nextTokenType != "colon" and nextTokenType != "comma")):
        if tokenType == "return":
            builder.RETURN_setValue(node, Expression(tokenizer, staticContext))
            staticContext.hasReturnWithValue = True
        else:
            builder.YIELD_setValue(node, AssignExpression(tokenizer, staticContext))
        
    elif tokenType == "return":
        staticContext.hasEmptyReturn = True

    # Disallow return v; in generator.
    if staticContext.hasReturnWithValue and staticContext.isGenerator:
        raise SyntaxError("Generator returns a value", tokenizer)

    if tokenType == "return":
        builder.RETURN_finish(node)
    else:
        builder.YIELD_finish(node)

    return node



def FunctionDefinition(tokenizer, staticContext, requireName, functionForm):
    builder = staticContext.builder
    functionNode = builder.FUNCTION_build(tokenizer)
    
    if tokenizer.match("identifier"):
        builder.FUNCTION_setName(functionNode, tokenizer.token.value)
    elif requireName:
        raise SyntaxError("Missing def identifier", tokenizer)

    tokenizer.mustMatch("left_paren")
    
    if not tokenizer.match("right_paren"):
        builder.FUNCTION_initParams(functionNode, tokenizer)
        prevParamNode = None
        while True:
            tokenType = tokenizer.get()
            if tokenType == "left_bracket" or tokenType == "left_curly":
                # Destructured formal parameters.
                tokenizer.unget()
                paramNode = DestructuringExpression(tokenizer, staticContext)
                
            elif tokenType == "identifier":
                paramNode = builder.FUNCTION_wrapParam(tokenizer)
                
            else:
                raise SyntaxError("Missing formal parameter", tokenizer)
                
            builder.FUNCTION_addParam(functionNode, tokenizer, paramNode)
            builder.COMMENTS_add(paramNode, prevParamNode, tokenizer.getComments())
        
            if not tokenizer.match("comma"):
                break
                
            prevParamNode = paramNode
        
        tokenizer.mustMatch("right_paren")

    # Do we have an expression closure or a normal body?
    tokenType = tokenizer.get()
    if tokenType != "left_curly":
        builder.FUNCTION_setExpressionClosure(functionNode, True)
        tokenizer.unget()

    childContext = StaticContext(True, builder)
    rp = tokenizer.save()
    
    if staticContext.inFunction:
        # Inner functions don't reset block numbering, only functions at
        # the top level of the program do.
        childContext.blockId = staticContext.blockId

    if tokenType != "left_curly":
        builder.FUNCTION_setBody(functionNode, AssignExpression(tokenizer, staticContext))
        if staticContext.isGenerator:
            raise SyntaxError("Generator returns a value", tokenizer)
            
    else:
        builder.FUNCTION_hoistVars(childContext.blockId)
        builder.FUNCTION_setBody(functionNode, Script(tokenizer, childContext))

    # 
    # Hoisting makes parse-time binding analysis tricky. A taxonomy of hoists:
    # 
    # 1. vars hoist to the top of their function:
    # 
    #    var x = 'global';
    #    function f() {
    #      x = 'f';
    #      if (false)
    #        var x;
    #    }
    #    f();
    #    print(x); // "global"
    # 
    # 2. lets hoist to the top of their block:
    # 
    #    function f() { // id: 0
    #      var x = 'f';
    #      {
    #        {
    #          print(x); // "undefined"
    #        }
    #        let x;
    #      }
    #    }
    #    f();
    # 
    # 3. inner functions at function top-level hoist to the beginning
    #    of the function.
    # 
    # If the builder used is doing parse-time analyses, hoisting may
    # invalidate earlier conclusions it makes about variable scope.
    # 
    # The builder can opt to set the needsHoisting flag in a
    # CompilerContext (in the case of var and function hoisting) or in a
    # node of type BLOCK (in the case of let hoisting). This signals for
    # the parser to reparse sections of code.
    # 
    # To avoid exponential blowup, if a function at the program top-level
    # has any hoists in its child blocks or inner functions, we reparse
    # the entire toplevel function. Each toplevel function is parsed at
    # most twice.
    # 
    # The list of declarations can be tied to block ids to aid talking
    # about declarations of blocks that have not yet been fully parsed.
    # 
    # Blocks are already uniquely numbered; see the comment in
    # Statements.
    # 
    
    #
    # wpbasti: 
    # Don't have the feeling that I need this functionality because the
    # tree is often modified before the variables and names inside are 
    # of any interest. So better doing this in a post-scan.
    #
    
    #
    # if childContext.needsHoisting:
    #     # Order is important here! Builders expect functions to come after variables!
    #     builder.setHoists(functionNode.body.id, childContext.variables.concat(childContext.functions))
    # 
    #     if staticContext.inFunction:
    #         # If an inner function needs hoisting, we need to propagate
    #         # this flag up to the parent function.
    #         staticContext.needsHoisting = True
    #     
    #     else:
    #         # Only re-parse functions at the top level of the program.
    #         childContext = StaticContext(True, builder)
    #         tokenizer.rewind(rp)
    #         
    #         # Set a flag in case the builder wants to have different behavior
    #         # on the second pass.
    #         builder.secondPass = True
    #         builder.FUNCTION_hoistVars(functionNode.body.id, True)
    #         builder.FUNCTION_setBody(functionNode, Script(tokenizer, childContext))
    #         builder.secondPass = False

    if tokenType == "left_curly":
        tokenizer.mustMatch("right_curly")

    functionNode.end = tokenizer.token.end
    functionNode.functionForm = functionForm
    
    builder.COMMENTS_add(functionNode.body, functionNode.body, tokenizer.getComments())
    builder.FUNCTION_finish(functionNode, staticContext)
    
    return functionNode



def Variables(tokenizer, staticContext, letBlock=None):
    """Parses a comma-separated list of var declarations (and maybe initializations)."""
    
    builder = staticContext.builder
    if tokenizer.token.type == "var":
        build = builder.VAR_build
        addDecl = builder.VAR_addDecl
        finish = builder.VAR_finish
        childContext = staticContext
            
    elif tokenizer.token.type == "const":
        build = builder.CONST_build
        addDecl = builder.CONST_addDecl
        finish = builder.CONST_finish
        childContext = staticContext
        
    elif tokenizer.token.type == "let" or tokenizer.token.type == "left_paren":
        build = builder.LET_build
        addDecl = builder.LET_addDecl
        finish = builder.LET_finish
        
        if not letBlock:
            statementStack = staticContext.statementStack
            i = len(statementStack) - 1
            
            # a BLOCK *must* be found.
            while statementStack[i].type != "block":
                i -= 1

            # Lets at the def toplevel are just vars, at least in SpiderMonkey.
            if i == 0:
                build = builder.VAR_build
                addDecl = builder.VAR_addDecl
                finish = builder.VAR_finish
                childContext = staticContext

            else:
                childContext = statementStack[i]
            
        else:
            childContext = letBlock

    node = build(tokenizer)
    
    while True:
        tokenType = tokenizer.get()

        # Done in Python port!
        # FIXME Should have a special DECLARATION node instead of overloading
        # IDENTIFIER to mean both identifier declarations and destructured
        # declarations.
        childNode = builder.DECL_build(tokenizer)
        
        if tokenType == "left_bracket" or tokenType == "left_curly":
            # Pass in childContext if we need to add each pattern matched into
            # its variables, else pass in staticContext.
            # Need to unget to parse the full destructured expression.
            tokenizer.unget()
            builder.DECL_setNames(childNode, DestructuringExpression(tokenizer, staticContext, True, childContext))
            
            if staticContext.inForLoopInit and tokenizer.peek() == "in":
                addDecl(node, childNode, childContext)
                if tokenizer.match("comma"): 
                    continue
                else: 
                    break            

            tokenizer.mustMatch("assign")
            if tokenizer.token.assignOp:
                raise SyntaxError("Invalid variable initialization", tokenizer)

            # Parse the init as a normal assignment.
            builder.DECL_setInitializer(childNode, AssignExpression(tokenizer, staticContext))
            builder.DECL_finish(childNode)
            addDecl(node, childNode, childContext)
            
            # Copy over names for variable list
            # for nameNode in childNode.names:
            #    childContext.variables.add(nameNode.value)
                
            if tokenizer.match("comma"): 
                continue
            else: 
                break            

        if tokenType != "identifier":
            raise SyntaxError("Missing variable name", tokenizer)

        builder.DECL_setName(childNode, tokenizer.token.value)
        builder.DECL_setReadOnly(childNode, node.type == "const")
        addDecl(node, childNode, childContext)

        if tokenizer.match("assign"):
            if tokenizer.token.assignOp:
                raise SyntaxError("Invalid variable initialization", tokenizer)

            initializerNode = AssignExpression(tokenizer, staticContext)
            builder.DECL_setInitializer(childNode, initializerNode)

        builder.DECL_finish(childNode)
        
        # If we directly use the node in "let" constructs
        # if not hasattr(childContext, "variables"):
        #    childContext.variables = set()
        
        # childContext.variables.add(childNode.name)
        
        if not tokenizer.match("comma"):
            break
        
    finish(node)
    return node



def LetBlock(tokenizer, staticContext, isStatement):
    """Does not handle let inside of for loop init."""
    builder = staticContext.builder

    # tokenizer.token.type must be "let"
    node = builder.LETBLOCK_build(tokenizer)
    tokenizer.mustMatch("left_paren")
    builder.LETBLOCK_setVariables(node, Variables(tokenizer, staticContext, node))
    tokenizer.mustMatch("right_paren")

    if isStatement and tokenizer.peek() != "left_curly":
        # If this is really an expression in let statement guise, then we
        # need to wrap the "let_block" node in a "semicolon" node so that we pop
        # the return value of the expression.
        childNode = builder.SEMICOLON_build(tokenizer)
        builder.SEMICOLON_setExpression(childNode, node)
        builder.SEMICOLON_finish(childNode)
        isStatement = False

    if isStatement:
        childNode = Block(tokenizer, staticContext)
        builder.LETBLOCK_setBlock(node, childNode)
        
    else:
        childNode = AssignExpression(tokenizer, staticContext)
        builder.LETBLOCK_setExpression(node, childNode)

    builder.LETBLOCK_finish(node)
    return node


def checkDestructuring(tokenizer, staticContext, node, simpleNamesOnly=None, data=None):
    if node.type == "array_comp":
        raise SyntaxError("Invalid array comprehension left-hand side", tokenizer)
        
    if node.type != "array_init" and node.type != "object_init":
        return

    builder = staticContext.builder

    for child in node:
        if child == None:
            continue
        
        if child.type == "property_init":
            lhs = child[0]
            rhs = child[1]
        else:
            lhs = None
            rhs = None
            
    
        if rhs and (rhs.type == "array_init" or rhs.type == "object_init"):
            checkDestructuring(tokenizer, staticContext, rhs, simpleNamesOnly, data)
            
        if lhs and simpleNamesOnly:
            # In declarations, lhs must be simple names
            if lhs.type != "identifier":
                raise SyntaxError("Missing name in pattern", tokenizer)
                
            elif data:
                childNode = builder.DECL_build(tokenizer)
                builder.DECL_setName(childNode, lhs.value)

                # Don't need to set initializer because it's just for
                # hoisting anyways.
                builder.DECL_finish(childNode)

                # Each pattern needs to be added to variables.
                # data.variables.add(childNode.name)
                

# JavaScript 1.7
def DestructuringExpression(tokenizer, staticContext, simpleNamesOnly=None, data=None):
    node = PrimaryExpression(tokenizer, staticContext)
    checkDestructuring(tokenizer, staticContext, node, simpleNamesOnly, data)

    return node


# JavsScript 1.7
def GeneratorExpression(tokenizer, staticContext, expression):
    builder = staticContext.builder
    node = builder.GENERATOR_build(tokenizer)

    builder.GENERATOR_setExpression(node, expression)
    builder.GENERATOR_setTail(node, comprehensionTail(tokenizer, staticContext))
    builder.GENERATOR_finish(node)
    
    return node


# JavaScript 1.7 Comprehensions Tails (Generators / Arrays)
def comprehensionTail(tokenizer, staticContext):
    builder = staticContext.builder
    
    # tokenizer.token.type must be "for"
    body = builder.COMPTAIL_build(tokenizer)
    
    while True:
        node = builder.FOR_build(tokenizer)
        
        # Comprehension tails are always for..in loops.
        builder.FOR_rebuildForIn(node)
        if tokenizer.match("identifier"):
            # But sometimes they're for each..in.
            if tokenizer.token.value == "each":
                builder.FOR_rebuildForEach(node)
            else:
                tokenizer.unget()

        tokenizer.mustMatch("left_paren")
        
        tokenType = tokenizer.get()
        if tokenType == "left_bracket" or tokenType == "left_curly":
            tokenizer.unget()
            # Destructured left side of for in comprehension tails.
            builder.FOR_setIterator(node, DestructuringExpression(tokenizer, staticContext))

        elif tokenType == "identifier":
            # Removed variable/declaration substructure in Python port.
            # Variable declarations are not allowed here. So why process them in such a way?
            
            # declaration = builder.DECL_build(tokenizer)
            # builder.DECL_setName(declaration, tokenizer.token.value)
            # builder.DECL_finish(declaration)
            # childNode = builder.VAR_build(tokenizer)
            # builder.VAR_addDecl(childNode, declaration)
            # builder.VAR_finish(childNode)
            # builder.FOR_setIterator(node, declaration)

            # Don't add to variables since the semantics of comprehensions is
            # such that the variables are in their own def when desugared.
            
            identifier = builder.PRIMARY_build(tokenizer, "identifier")
            builder.FOR_setIterator(node, identifier)

        else:
            raise SyntaxError("Missing identifier", tokenizer)
        
        tokenizer.mustMatch("in")
        builder.FOR_setObject(node, Expression(tokenizer, staticContext))
        tokenizer.mustMatch("right_paren")
        builder.COMPTAIL_addFor(body, node)
        
        if not tokenizer.match("for"):
            break

    # Optional guard.
    if tokenizer.match("if"):
        builder.COMPTAIL_setGuard(body, ParenExpression(tokenizer, staticContext))

    builder.COMPTAIL_finish(body)

    return body


def ParenExpression(tokenizer, staticContext):
    tokenizer.mustMatch("left_paren")

    # Always accept the 'in' operator in a parenthesized expression,
    # where it's unambiguous, even if we might be parsing the init of a
    # for statement.
    oldLoopInit = staticContext.inForLoopInit
    staticContext.inForLoopInit = False
    node = Expression(tokenizer, staticContext)
    staticContext.inForLoopInit = oldLoopInit

    err = "expression must be parenthesized"
    if tokenizer.match("for"):
        if node.type == "yield" and not node.parenthesized:
            raise SyntaxError("Yield " + err, tokenizer)
            
        if node.type == "comma" and not node.parenthesized:
            raise SyntaxError("Generator " + err, tokenizer)
            
        node = GeneratorExpression(tokenizer, staticContext, node)

    tokenizer.mustMatch("right_paren")

    return node


def Expression(tokenizer, staticContext):
    """Top-down expression parser matched against SpiderMonkey."""
    builder = staticContext.builder
    node = AssignExpression(tokenizer, staticContext)

    if tokenizer.match("comma"):
        childNode = builder.COMMA_build(tokenizer)
        builder.COMMA_addOperand(childNode, node)
        node = childNode
        while True:
            childNode = node[len(node)-1]
            if childNode.type == "yield" and not childNode.parenthesized:
                raise SyntaxError("Yield expression must be parenthesized", tokenizer)
            builder.COMMA_addOperand(node, AssignExpression(tokenizer, staticContext))
            
            if not tokenizer.match("comma"):
                break
                
        builder.COMMA_finish(node)

    return node


def AssignExpression(tokenizer, staticContext):
    builder = staticContext.builder

    # Have to treat yield like an operand because it could be the leftmost
    # operand of the expression.
    if tokenizer.match("yield", True):
        return returnOrYield(tokenizer, staticContext)

    comments = tokenizer.getComments()
    node = builder.ASSIGN_build(tokenizer)
    lhs = ConditionalExpression(tokenizer, staticContext)
    builder.COMMENTS_add(lhs, None, comments)

    if not tokenizer.match("assign"):
        builder.ASSIGN_finish(node)
        return lhs

    if lhs.type == "object_init" or lhs.type == "array_init":
        checkDestructuring(tokenizer, staticContext, lhs)
    elif lhs.type == "identifier" or lhs.type == "dot" or lhs.type == "index" or lhs.type == "call":
        pass
    else:
        raise SyntaxError("Bad left-hand side of assignment", tokenizer)
        
    builder.ASSIGN_setAssignOp(node, tokenizer.token.assignOp)
    builder.ASSIGN_addOperand(node, lhs)
    builder.ASSIGN_addOperand(node, AssignExpression(tokenizer, staticContext))
    builder.ASSIGN_finish(node)

    return node


def ConditionalExpression(tokenizer, staticContext):
    builder = staticContext.builder
    node = OrExpression(tokenizer, staticContext)

    if tokenizer.match("hook"):
        childNode = node
        node = builder.HOOK_build(tokenizer)
        builder.HOOK_setCondition(node, childNode)

        # Always accept the 'in' operator in the middle clause of a ternary,
        # where it's unambiguous, even if we might be parsing the init of a
        # for statement.
        oldLoopInit = staticContext.inForLoopInit
        staticContext.inForLoopInit = False
        builder.HOOK_setThenPart(node, AssignExpression(tokenizer, staticContext))
        staticContext.inForLoopInit = oldLoopInit
        
        if not tokenizer.match("colon"):
            raise SyntaxError("Missing : after ?", tokenizer)
            
        builder.HOOK_setElsePart(node, AssignExpression(tokenizer, staticContext))
        builder.HOOK_finish(node)

    return node
    

def OrExpression(tokenizer, staticContext):
    builder = staticContext.builder
    node = AndExpression(tokenizer, staticContext)
    
    while tokenizer.match("or"):
        childNode = builder.OR_build(tokenizer)
        builder.OR_addOperand(childNode, node)
        builder.OR_addOperand(childNode, AndExpression(tokenizer, staticContext))
        builder.OR_finish(childNode)
        node = childNode

    return node


def AndExpression(tokenizer, staticContext):
    builder = staticContext.builder
    node = BitwiseOrExpression(tokenizer, staticContext)

    while tokenizer.match("and"):
        childNode = builder.AND_build(tokenizer)
        builder.AND_addOperand(childNode, node)
        builder.AND_addOperand(childNode, BitwiseOrExpression(tokenizer, staticContext))
        builder.AND_finish(childNode)
        node = childNode

    return node


def BitwiseOrExpression(tokenizer, staticContext):
    builder = staticContext.builder
    node = BitwiseXorExpression(tokenizer, staticContext)
    
    while tokenizer.match("bitwise_or"):
        childNode = builder.BITWISEOR_build(tokenizer)
        builder.BITWISEOR_addOperand(childNode, node)
        builder.BITWISEOR_addOperand(childNode, BitwiseXorExpression(tokenizer, staticContext))
        builder.BITWISEOR_finish(childNode)
        node = childNode

    return node


def BitwiseXorExpression(tokenizer, staticContext):
    builder = staticContext.builder
    node = BitwiseAndExpression(tokenizer, staticContext)
    
    while tokenizer.match("bitwise_xor"):
        childNode = builder.BITWISEXOR_build(tokenizer)
        builder.BITWISEXOR_addOperand(childNode, node)
        builder.BITWISEXOR_addOperand(childNode, BitwiseAndExpression(tokenizer, staticContext))
        builder.BITWISEXOR_finish(childNode)
        node = childNode

    return node


def BitwiseAndExpression(tokenizer, staticContext):
    builder = staticContext.builder
    node = EqualityExpression(tokenizer, staticContext)

    while tokenizer.match("bitwise_and"):
        childNode = builder.BITWISEAND_build(tokenizer)
        builder.BITWISEAND_addOperand(childNode, node)
        builder.BITWISEAND_addOperand(childNode, EqualityExpression(tokenizer, staticContext))
        builder.BITWISEAND_finish(childNode)
        node = childNode

    return node


def EqualityExpression(tokenizer, staticContext):
    builder = staticContext.builder
    node = RelationalExpression(tokenizer, staticContext)
    
    while tokenizer.match("eq") or tokenizer.match("ne") or tokenizer.match("strict_eq") or tokenizer.match("strict_ne"):
        childNode = builder.EQUALITY_build(tokenizer)
        builder.EQUALITY_addOperand(childNode, node)
        builder.EQUALITY_addOperand(childNode, RelationalExpression(tokenizer, staticContext))
        builder.EQUALITY_finish(childNode)
        node = childNode

    return node


def RelationalExpression(tokenizer, staticContext):
    builder = staticContext.builder
    oldLoopInit = staticContext.inForLoopInit

    # Uses of the in operator in shiftExprs are always unambiguous,
    # so unset the flag that prohibits recognizing it.
    staticContext.inForLoopInit = False
    node = ShiftExpression(tokenizer, staticContext)

    while tokenizer.match("lt") or tokenizer.match("le") or tokenizer.match("ge") or tokenizer.match("gt") or (oldLoopInit == False and tokenizer.match("in")) or tokenizer.match("instanceof"):
        childNode = builder.RELATIONAL_build(tokenizer)
        builder.RELATIONAL_addOperand(childNode, node)
        builder.RELATIONAL_addOperand(childNode, ShiftExpression(tokenizer, staticContext))
        builder.RELATIONAL_finish(childNode)
        node = childNode
    
    staticContext.inForLoopInit = oldLoopInit

    return node


def ShiftExpression(tokenizer, staticContext):
    builder = staticContext.builder
    node = AddExpression(tokenizer, staticContext)
    
    while tokenizer.match("lsh") or tokenizer.match("rsh") or tokenizer.match("ursh"):
        childNode = builder.SHIFT_build(tokenizer)
        builder.SHIFT_addOperand(childNode, node)
        builder.SHIFT_addOperand(childNode, AddExpression(tokenizer, staticContext))
        builder.SHIFT_finish(childNode)
        node = childNode

    return node


def AddExpression(tokenizer, staticContext):
    builder = staticContext.builder
    node = MultiplyExpression(tokenizer, staticContext)
    
    while tokenizer.match("plus") or tokenizer.match("minus"):
        childNode = builder.ADD_build(tokenizer)
        builder.ADD_addOperand(childNode, node)
        builder.ADD_addOperand(childNode, MultiplyExpression(tokenizer, staticContext))
        builder.ADD_finish(childNode)
        node = childNode

    return node


def MultiplyExpression(tokenizer, staticContext):
    builder = staticContext.builder
    node = UnaryExpression(tokenizer, staticContext)
    
    while tokenizer.match("mul") or tokenizer.match("div") or tokenizer.match("mod"):
        childNode = builder.MULTIPLY_build(tokenizer)
        builder.MULTIPLY_addOperand(childNode, node)
        builder.MULTIPLY_addOperand(childNode, UnaryExpression(tokenizer, staticContext))
        builder.MULTIPLY_finish(childNode)
        node = childNode

    return node


def UnaryExpression(tokenizer, staticContext):
    builder = staticContext.builder
    tokenType = tokenizer.get(True)

    if tokenType in ["delete", "void", "typeof", "not", "bitwise_not", "plus", "minus"]:
        node = builder.UNARY_build(tokenizer)
        builder.UNARY_addOperand(node, UnaryExpression(tokenizer, staticContext))
    
    elif tokenType == "increment" or tokenType == "decrement":
        # Prefix increment/decrement.
        node = builder.UNARY_build(tokenizer)
        builder.UNARY_addOperand(node, MemberExpression(tokenizer, staticContext, True))

    else:
        tokenizer.unget()
        node = MemberExpression(tokenizer, staticContext, True)

        # Don't look across a newline boundary for a postfix {in,de}crement.
        if tokenizer.tokens[(tokenizer.tokenIndex + tokenizer.lookahead - 1) & 3].line == tokenizer.line:
            if tokenizer.match("increment") or tokenizer.match("decrement"):
                childNode = builder.UNARY_build(tokenizer)
                builder.UNARY_setPostfix(childNode)
                builder.UNARY_finish(node)
                builder.UNARY_addOperand(childNode, node)
                node = childNode

    builder.UNARY_finish(node)
    return node


def MemberExpression(tokenizer, staticContext, allowCallSyntax):
    builder = staticContext.builder

    if tokenizer.match("new"):
        node = builder.MEMBER_build(tokenizer)
        builder.MEMBER_addOperand(node, MemberExpression(tokenizer, staticContext, False))
        
        if tokenizer.match("left_paren"):
            builder.MEMBER_rebuildNewWithArgs(node)
            builder.MEMBER_addOperand(node, ArgumentList(tokenizer, staticContext))
        
        builder.MEMBER_finish(node)
    
    else:
        node = PrimaryExpression(tokenizer, staticContext)

    while True:
        tokenType = tokenizer.get()
        if tokenType == "end":
            break
        
        if tokenType == "dot":
            childNode = builder.MEMBER_build(tokenizer)
            builder.MEMBER_addOperand(childNode, node)
            tokenizer.mustMatch("identifier")
            builder.MEMBER_addOperand(childNode, builder.MEMBER_build(tokenizer))

        elif tokenType == "left_bracket":
            childNode = builder.MEMBER_build(tokenizer, "index")
            builder.MEMBER_addOperand(childNode, node)
            builder.MEMBER_addOperand(childNode, Expression(tokenizer, staticContext))
            tokenizer.mustMatch("right_bracket")

        elif tokenType == "left_paren" and allowCallSyntax:
            childNode = builder.MEMBER_build(tokenizer, "call")
            builder.MEMBER_addOperand(childNode, node)
            builder.MEMBER_addOperand(childNode, ArgumentList(tokenizer, staticContext))

        else:
            tokenizer.unget()
            return node

        builder.MEMBER_finish(childNode)
        node = childNode

    return node


def ArgumentList(tokenizer, staticContext):
    builder = staticContext.builder
    node = builder.LIST_build(tokenizer)
    
    if tokenizer.match("right_paren", True):
        return node
    
    while True:    
        childNode = AssignExpression(tokenizer, staticContext)
        if childNode.type == "yield" and not childNode.parenthesized and tokenizer.peek() == "comma":
            raise SyntaxError("Yield expression must be parenthesized", tokenizer)
            
        if tokenizer.match("for"):
            childNode = GeneratorExpression(tokenizer, staticContext, childNode)
            if len(node) > 1 or tokenizer.peek(True) == "comma":
                raise SyntaxError("Generator expression must be parenthesized", tokenizer)
        
        builder.LIST_addOperand(node, childNode)
        if not tokenizer.match("comma"):
            break

    tokenizer.mustMatch("right_paren")
    builder.LIST_finish(node)

    return node


def PrimaryExpression(tokenizer, staticContext):
    builder = staticContext.builder
    tokenType = tokenizer.get(True)

    if tokenType == "function":
        node = FunctionDefinition(tokenizer, staticContext, False, "expressed_form")

    elif tokenType == "left_bracket":
        node = builder.ARRAYINIT_build(tokenizer)
        while True:
            tokenType = tokenizer.peek(True)
            if tokenType == "right_bracket":
                break
        
            if tokenType == "comma":
                tokenizer.get()
                builder.ARRAYINIT_addElement(node, None)
                continue

            builder.ARRAYINIT_addElement(node, AssignExpression(tokenizer, staticContext))

            if tokenType != "comma" and not tokenizer.match("comma"):
                break

        # If we matched exactly one element and got a "for", we have an
        # array comprehension.
        if len(node) == 1 and tokenizer.match("for"):
            childNode = builder.ARRAYCOMP_build(tokenizer)
            builder.ARRAYCOMP_setExpression(childNode, node[0])
            builder.ARRAYCOMP_setTail(childNode, comprehensionTail(tokenizer, staticContext))
            node = childNode
        
        builder.COMMENTS_add(node, node, tokenizer.getComments())
        tokenizer.mustMatch("right_bracket")
        builder.PRIMARY_finish(node)

    elif tokenType == "left_curly":
        node = builder.OBJECTINIT_build(tokenizer)

        if not tokenizer.match("right_curly"):
            while True:
                tokenType = tokenizer.get()
                tokenValue = getattr(tokenizer.token, "value", None)
                comments = tokenizer.getComments()
                
                if tokenValue in ("get", "set") and tokenizer.peek() == "identifier":
                    if staticContext.ecma3OnlyMode:
                        raise SyntaxError("Illegal property accessor", tokenizer)
                        
                    fd = FunctionDefinition(tokenizer, staticContext, True, "expressed_form")
                    builder.OBJECTINIT_addProperty(node, fd)
                    
                else:
                    if tokenType == "identifier" or tokenType == "number" or tokenType == "string":
                        id = builder.PRIMARY_build(tokenizer, "identifier")
                        builder.PRIMARY_finish(id)
                        
                    elif tokenType == "right_curly":
                        if staticContext.ecma3OnlyMode:
                            raise SyntaxError("Illegal trailing ,", tokenizer)
                            
                        tokenizer.unget()
                        break
                            
                    else:
                        if tokenValue in jasy.js.tokenize.Lang.keywords:
                            id = builder.PRIMARY_build(tokenizer, "identifier")
                            builder.PRIMARY_finish(id)
                        else:
                            print("Value is '%s'" % tokenValue)
                            raise SyntaxError("Invalid property name", tokenizer)
                    
                    if tokenizer.match("colon"):
                        childNode = builder.PROPERTYINIT_build(tokenizer)
                        builder.COMMENTS_add(childNode, node, comments)
                        builder.PROPERTYINIT_addOperand(childNode, id)
                        builder.PROPERTYINIT_addOperand(childNode, AssignExpression(tokenizer, staticContext))
                        builder.PROPERTYINIT_finish(childNode)
                        builder.OBJECTINIT_addProperty(node, childNode)
                        
                    else:
                        # Support, e.g., |var {staticContext, y} = o| as destructuring shorthand
                        # for |var {staticContext: staticContext, y: y} = o|, per proposed JS2/ES4 for JS1.8.
                        if tokenizer.peek() != "comma" and tokenizer.peek() != "right_curly":
                            raise SyntaxError("Missing : after property", tokenizer)
                        builder.OBJECTINIT_addProperty(node, id)
                    
                if not tokenizer.match("comma"):
                    break

            builder.COMMENTS_add(node, node, tokenizer.getComments())
            tokenizer.mustMatch("right_curly")

        builder.OBJECTINIT_finish(node)

    elif tokenType == "left_paren":
        # ParenExpression does its own matching on parentheses, so we need to unget.
        tokenizer.unget()
        node = ParenExpression(tokenizer, staticContext)
        node.parenthesized = True

    elif tokenType == "let":
        node = LetBlock(tokenizer, staticContext, False)

    elif tokenType in ["null", "this", "true", "false", "identifier", "number", "string", "regexp"]:
        node = builder.PRIMARY_build(tokenizer, tokenType)
        builder.PRIMARY_finish(node)

    else:
        raise SyntaxError("Missing operand. Found type: %s" % tokenType, tokenizer)

    return node

########NEW FILE########
__FILENAME__ = ScopeData
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

__all__ = ["ScopeData"]

class ScopeData():
    """
    Used by core/Variables.py to store the resulting statistics data efficiently. Contains information about:
    
    * Declared Variables (declared)
    * Modified Variables (modified)
    * Shared
    * Unused Variables (unused)
    """

    __slots__ = ["name", "params", "declared", "accessed", "modified", "shared", "unused", "packages"]

    def __init__(self):
        self.name = None
        self.params = set()
        self.declared = set()
        self.accessed = {}
        self.modified = set()
        self.shared = {}
        self.unused = set()
        self.packages = {}

    def __iter__(self):
        for field in self.__slots__:
            yield field

    def __getitem__(self, key):
        if key == "name":
            return self.name
        elif key == "params":
            return self.params
        elif key == "declared":
            return self.declared
        elif key == "accessed":
            return self.accessed
        elif key == "modified":
            return self.modified
        elif key == "shared":
            return self.shared
        elif key == "unused":
            return self.unused
        elif key == "packages":
            return self.packages

        raise KeyError("Unknown key: %s" % key)

    def export(self):
        """Exports all data as a Python dict instance"""

        return {
            "name": self.name,
            "params": self.params,
            "declared": self.declared,
            "accessed": self.accessed,
            "modified": self.modified,
            "shared": self.shared,
            "unused": self.unused,
            "packages": self.packages
        }

    def increment(self, name, by=1):
        """ Small helper so simplify adding variables to "accessed" dict """
        
        if not name in self.accessed:
            self.accessed[name] = by
        else:
            self.accessed[name] += by
            
########NEW FILE########
__FILENAME__ = ScopeScanner
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

import jasy.js.parse.ScopeData


__all__ = ["scan"]


#
# Public API
#

def scan(tree):
    """
    Scans the given tree and attaches variable data instances (core/ScopeData.py) to every scope (aka function).
    This data is being stored independently from the real tree so that if you modifiy the tree the
    data is not automatically updated. This means that every time you modify the tree heavily,
    it might make sense to re-execute this method to bring it in sync to the current tree structure.
    """
    
    return __scanScope(tree)



#
# Implementation
#

def __scanNode(node, data):
    """
    Scans nodes recursively and collects all variables which are declared and accessed.
    """
    
    if node.type == "function":
        if node.functionForm == "declared_form":
            data.declared.add(node.name)
            data.modified.add(node.name)
    
    elif node.type == "declaration":
        varName = getattr(node, "name", None)
        if varName != None:
            data.declared.add(varName)
            
            if hasattr(node, "initializer"):
                data.modified.add(varName)
            
            # If the variable is used as a iterator, we need to add it to the use counter as well
            if getattr(node.parent, "rel", None) == "iterator":
                data.increment(varName)
            
        else:
            # JS 1.7 Destructing Expression
            varNames = node.names
            for identifier in node.names:
                data.declared.add(identifier.value)
                data.modified.add(identifier.value)
                
            # If the variable is used as a iterator, we need to add it to the use counter as well
            if getattr(node.parent, "rel", None) == "iterator":
                for identifier in node.names:
                    data.increment(identifier.value)
            
    elif node.type == "identifier":
        # Ignore parameter names (of inner functions, these are handled by __scanScope)
        if node.parent.type == "list" and getattr(node.parent, "rel", None) == "params":
            pass
        
        # Ignore property initialization names
        elif node.parent.type == "property_init" and node.parent[0] == node:
            pass
            
        # Ignore non first identifiers in dot-chains
        elif node.parent.type != "dot" or node.parent.index(node) == 0:
            if node.value != "arguments":
                data.increment(node.value)
            
                if node.parent.type in ("increment", "decrement"):
                    data.modified.add(node.value)
                
                elif node.parent.type == "assign" and node.parent[0] == node:
                    data.modified.add(node.value)

                # Support for package-like object access
                if node.parent.type == "dot":
                    package = __combinePackage(node)
                    if package in data.packages:
                        data.packages[package] += 1
                    else:
                        data.packages[package] = 1
                
    # Treat exception variables in catch blocks like declared
    elif node.type == "block" and node.parent.type == "catch":
        data.declared.add(node.parent.exception.value)                
    
    if node.type == "script":
        innerVariables = __scanScope(node)
        for name in innerVariables.shared:
            data.increment(name, innerVariables.shared[name])
            
            if name in innerVariables.modified:
                data.modified.add(name)
        
        for package in innerVariables.packages:
            if package in data.packages:
                data.packages[package] += innerVariables.packages[package]
            else:
                data.packages[package] = innerVariables.packages[package]
                
    else:
        for child in node:
            # None children are allowed sometimes e.g. during array_init like [1,2,,,7,8]
            if child != None:
                __scanNode(child, data)



def __combinePackage(node):
    """
    Combines a package variable (e.g. foo.bar.baz) into one string
    """

    result = [node.value]
    parent = node.parent
    while parent.type == "dot":
        result.append(parent[1].value)
        parent = parent.parent

    return ".".join(result)
    
    
    
def __scanScope(node):
    """ 
    Scans a scope and collects statistics on variable declaration and usage 
    """
    
    # Initialize statistics object for this scope
    data = jasy.js.parse.ScopeData.ScopeData()
    node.scope = data
    
    # Add params to declaration list
    __addParams(node, data)

    # Collect all data from all children (excluding sub-scopes)
    for child in node:
        __scanNode(child, data)
        
    # Remove all objects which are based on locally declared variables
    for name in list(data.packages):
        top = name[0:name.index(".")]
        if top in data.declared or top in data.params:
            del data.packages[name]
    
    # Look for accessed varibles which have not been defined
    # Might be a part of a closure or just a mistake
    for name in data.accessed:
        if name not in data.declared and name not in data.params and name != "arguments":
            data.shared[name] = data.accessed[name]
            
    # Look for variables which have been defined, but not accessed.
    if data.name and not data.name in data.accessed:
        data.unused.add(data.name)
    for name in data.params:
        if not name in data.accessed:
            data.unused.add(name)
    for name in data.declared:
        if not name in data.accessed:
            data.unused.add(name)
    
    return data
    
    
    
def __addParams(node, data):
    """
    Adds all param names from outer function to the definition list
    """

    rel = getattr(node, "rel", None)
    if rel == "body" and node.parent.type == "function":
        # In expressed_form the function name belongs to the function body, not to the parent scope
        if node.parent.functionForm == "expressed_form":
            data.name = getattr(node.parent, "name", None)
        
        paramList = getattr(node.parent, "params", None)
        if paramList:
            for paramIdentifier in paramList:
                data.params.add(paramIdentifier.value)


########NEW FILE########
__FILENAME__ = VanillaBuilder
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

#
# License: MPL 1.1/GPL 2.0/LGPL 2.1
# Authors: 
#   - Brendan Eich <brendan@mozilla.org> (Original JavaScript) (2004-2010)
#   - Sebastian Werner <info@sebastian-werner.net> (Python Port) (2010)
#

import jasy.js.parse.Node

class VanillaBuilder:
    """The vanilla AST builder."""
    
    def COMMENTS_add(self, currNode, prevNode, comments):
        if not comments:
            return
            
        currComments = []
        prevComments = []
        for comment in comments:
            # post comments - for previous node
            if comment.context == "inline":
                prevComments.append(comment)
                
            # all other comment styles are attached to the current one
            else:
                currComments.append(comment)
        
        # Merge with previously added ones
        if hasattr(currNode, "comments"):
            currNode.comments.extend(currComments)
        else:
            currNode.comments = currComments
        
        if prevNode:
            if hasattr(prevNode, "comments"):
                prevNode.comments.extend(prevComments)
            else:
                prevNode.comments = prevComments
        else:
            # Don't loose the comment in tree (if not previous node is there, attach it to this node)
            currNode.comments.extend(prevComments)
    
    def IF_build(self, tokenizer):
        return jasy.js.parse.Node.Node(tokenizer, "if")

    def IF_setCondition(self, node, expression):
        node.append(expression, "condition")

    def IF_setThenPart(self, node, statement):
        node.append(statement, "thenPart")

    def IF_setElsePart(self, node, statement):
        node.append(statement, "elsePart")

    def IF_finish(self, node):
        pass

    def SWITCH_build(self, tokenizer):
        node = jasy.js.parse.Node.Node(tokenizer, "switch")
        node.defaultIndex = -1
        return node

    def SWITCH_setDiscriminant(self, node, expression):
        node.append(expression, "discriminant")

    def SWITCH_setDefaultIndex(self, node, index):
        node.defaultIndex = index

    def SWITCH_addCase(self, node, childNode):
        node.append(childNode)

    def SWITCH_finish(self, node):
        pass

    def CASE_build(self, tokenizer):
        return jasy.js.parse.Node.Node(tokenizer, "case")

    def CASE_setLabel(self, node, expression):
        node.append(expression, "label")

    def CASE_initializeStatements(self, node, tokenizer):
        node.append(jasy.js.parse.Node.Node(tokenizer, "block"), "statements")

    def CASE_addStatement(self, node, statement):
        node.statements.append(statement)

    def CASE_finish(self, node):
        pass

    def DEFAULT_build(self, tokenizer):
        return jasy.js.parse.Node.Node(tokenizer, "default")

    def DEFAULT_initializeStatements(self, node, tokenizer):
        node.append(jasy.js.parse.Node.Node(tokenizer, "block"), "statements")

    def DEFAULT_addStatement(self, node, statement):
        node.statements.append(statement)

    def DEFAULT_finish(self, node):
        pass

    def FOR_build(self, tokenizer):
        node = jasy.js.parse.Node.Node(tokenizer, "for")
        node.isLoop = True
        node.isEach = False
        return node

    def FOR_rebuildForEach(self, node):
        node.isEach = True

    # NB: This function is called after rebuildForEach, if that'statement called at all.
    def FOR_rebuildForIn(self, node):
        node.type = "for_in"

    def FOR_setCondition(self, node, expression):
        node.append(expression, "condition")

    def FOR_setSetup(self, node, expression):
        node.append(expression, "setup")

    def FOR_setUpdate(self, node, expression):
        node.append(expression, "update")

    def FOR_setObject(self, node, expression, forBlock=None):
        # wpbasti: not sure what forBlock stands for but it is used in the parser
        # JS tolerates the optinal unused parameter, but not so Python.
        node.append(expression, "object")

    def FOR_setIterator(self, node, expression, forBlock=None):
        # wpbasti: not sure what forBlock stands for but it is used in the parser
        # JS tolerates the optinal unused parameter, but not so Python.
        node.append(expression, "iterator")

    def FOR_setBody(self, node, statement):
        node.append(statement, "body")

    def FOR_finish(self, node):
        pass

    def WHILE_build(self, tokenizer):
        node = jasy.js.parse.Node.Node(tokenizer, "while")
        node.isLoop = True
        return node

    def WHILE_setCondition(self, node, expression):
        node.append(expression, "condition")

    def WHILE_setBody(self, node, statement):
        node.append(statement, "body")

    def WHILE_finish(self, node):
        pass

    def DO_build(self, tokenizer):
        node = jasy.js.parse.Node.Node(tokenizer, "do")
        node.isLoop = True
        return node

    def DO_setCondition(self, node, expression):
        node.append(expression, "condition")

    def DO_setBody(self, node, statement):
        node.append(statement, "body")

    def DO_finish(self, node):
        pass

    def BREAK_build(self, tokenizer):
        return jasy.js.parse.Node.Node(tokenizer, "break")

    def BREAK_setLabel(self, node, label):
        node.label = label

    def BREAK_setTarget(self, node, target):
        # Hint, no append() - relation, but not a child
        node.target = target

    def BREAK_finish(self, node):
        pass

    def CONTINUE_build(self, tokenizer):
        return jasy.js.parse.Node.Node(tokenizer, "continue")

    def CONTINUE_setLabel(self, node, label):
        node.label = label

    def CONTINUE_setTarget(self, node, target):
        # Hint, no append() - relation, but not a child
        node.target = target

    def CONTINUE_finish(self, node):
        pass

    def TRY_build(self, tokenizer):
        node = jasy.js.parse.Node.Node(tokenizer, "try")
        return node

    def TRY_setTryBlock(self, node, statement):
        node.append(statement, "tryBlock")

    def TRY_addCatch(self, node, childNode):
        node.append(childNode)

    def TRY_finishCatches(self, node):
        pass

    def TRY_setFinallyBlock(self, node, statement):
        node.append(statement, "finallyBlock")

    def TRY_finish(self, node):
        pass

    def CATCH_build(self, tokenizer):
        node = jasy.js.parse.Node.Node(tokenizer, "catch")
        return node
        
    def CATCH_wrapException(self, tokenizer):
        node = jasy.js.parse.Node.Node(tokenizer, "exception")
        node.value = tokenizer.token.value
        return node

    def CATCH_setException(self, node, exception):
        node.append(exception, "exception")

    def CATCH_setGuard(self, node, expression):
        node.append(expression, "guard")

    def CATCH_setBlock(self, node, statement):
        node.append(statement, "block")

    def CATCH_finish(self, node):
        pass

    def THROW_build(self, tokenizer):
        return jasy.js.parse.Node.Node(tokenizer, "throw")

    def THROW_setException(self, node, expression):
        node.append(expression, "exception")

    def THROW_finish(self, node):
        pass

    def RETURN_build(self, tokenizer):
        return jasy.js.parse.Node.Node(tokenizer, "return")

    def RETURN_setValue(self, node, expression):
        node.append(expression, "value")

    def RETURN_finish(self, node):
        pass

    def YIELD_build(self, tokenizer):
        return jasy.js.parse.Node.Node(tokenizer, "yield")

    def YIELD_setValue(self, node, expression):
        node.append(expression, "value")

    def YIELD_finish(self, node):
        pass

    def GENERATOR_build(self, tokenizer):
        return jasy.js.parse.Node.Node(tokenizer, "generator")

    def GENERATOR_setExpression(self, node, expression):
        node.append(expression, "expression")

    def GENERATOR_setTail(self, node, childNode):
        node.append(childNode, "tail")

    def GENERATOR_finish(self, node):
        pass

    def WITH_build(self, tokenizer):
        return jasy.js.parse.Node.Node(tokenizer, "with")

    def WITH_setObject(self, node, expression):
        node.append(expression, "object")

    def WITH_setBody(self, node, statement):
        node.append(statement, "body")

    def WITH_finish(self, node):
        pass

    def DEBUGGER_build(self, tokenizer):
        return jasy.js.parse.Node.Node(tokenizer, "debugger")

    def SEMICOLON_build(self, tokenizer):
        return jasy.js.parse.Node.Node(tokenizer, "semicolon")

    def SEMICOLON_setExpression(self, node, expression):
        node.append(expression, "expression")

    def SEMICOLON_finish(self, node):
        pass

    def LABEL_build(self, tokenizer):
        return jasy.js.parse.Node.Node(tokenizer, "label")

    def LABEL_setLabel(self, node, label):
        node.label = label

    def LABEL_setStatement(self, node, statement):
        node.append(statement, "statement")

    def LABEL_finish(self, node):
        pass

    def FUNCTION_build(self, tokenizer):
        node = jasy.js.parse.Node.Node(tokenizer)
        if node.type != "function":
            if tokenizer.token.value == "get":
                node.type = "getter"
            else:
                node.type = "setter"
                
        return node

    def FUNCTION_setName(self, node, identifier):
        node.name = identifier

    def FUNCTION_initParams(self, node, tokenizer):
        node.append(jasy.js.parse.Node.Node(tokenizer, "list"), "params")
        
    def FUNCTION_wrapParam(self, tokenizer):
        param = jasy.js.parse.Node.Node(tokenizer)
        param.value = tokenizer.token.value
        return param
        
    def FUNCTION_addParam(self, node, tokenizer, expression):
        node.params.append(expression)
        
    def FUNCTION_setExpressionClosure(self, node, expressionClosure):
        node.expressionClosure = expressionClosure

    def FUNCTION_setBody(self, node, statement):
        # copy over function parameters to function body
        params = getattr(node, "params", None)
        #if params:
        #    statement.params = [param.value for param in params]
            
        node.append(statement, "body")

    def FUNCTION_hoistVars(self, x):
        pass

    def FUNCTION_finish(self, node, x):
        pass

    def VAR_build(self, tokenizer):
        return jasy.js.parse.Node.Node(tokenizer, "var")

    def VAR_addDecl(self, node, childNode, childContext=None):
        node.append(childNode)

    def VAR_finish(self, node):
        pass

    def CONST_build(self, tokenizer):
        return jasy.js.parse.Node.Node(tokenizer, "const")

    def CONST_addDecl(self, node, childNode, childContext=None):
        node.append(childNode)

    def CONST_finish(self, node):
        pass

    def LET_build(self, tokenizer):
        return jasy.js.parse.Node.Node(tokenizer, "let")

    def LET_addDecl(self, node, childNode, childContext=None):
        node.append(childNode)

    def LET_finish(self, node):
        pass

    def DECL_build(self, tokenizer):
        return jasy.js.parse.Node.Node(tokenizer, "declaration")

    def DECL_setNames(self, node, expression):
        node.append(expression, "names")

    def DECL_setName(self, node, identifier):
        node.name = identifier

    def DECL_setInitializer(self, node, expression):
        node.append(expression, "initializer")

    def DECL_setReadOnly(self, node, readOnly):
        node.readOnly = readOnly

    def DECL_finish(self, node):
        pass

    def LETBLOCK_build(self, tokenizer):
        node = jasy.js.parse.Node.Node(tokenizer, "let_block")
        return node

    def LETBLOCK_setVariables(self, node, childNode):
        node.append(childNode, "variables")

    def LETBLOCK_setExpression(self, node, expression):
        node.append(expression, "expression")

    def LETBLOCK_setBlock(self, node, statement):
        node.append(statement, "block")

    def LETBLOCK_finish(self, node):
        pass

    def BLOCK_build(self, tokenizer, id):
        node = jasy.js.parse.Node.Node(tokenizer, "block")
        # node.id = id
        return node

    def BLOCK_hoistLets(self, node):
        pass

    def BLOCK_addStatement(self, node, childNode):
        node.append(childNode)

    def BLOCK_finish(self, node):
        pass

    def EXPRESSION_build(self, tokenizer, tokenType):
        return jasy.js.parse.Node.Node(tokenizer, tokenType)

    def EXPRESSION_addOperand(self, node, childNode):
        node.append(childNode)

    def EXPRESSION_finish(self, node):
        pass

    def ASSIGN_build(self, tokenizer):
        return jasy.js.parse.Node.Node(tokenizer, "assign")

    def ASSIGN_addOperand(self, node, childNode):
        node.append(childNode)

    def ASSIGN_setAssignOp(self, node, operator):
        node.assignOp = operator

    def ASSIGN_finish(self, node):
        pass

    def HOOK_build(self, tokenizer):
        return jasy.js.parse.Node.Node(tokenizer, "hook")

    def HOOK_setCondition(self, node, expression):
        node.append(expression, "condition")

    def HOOK_setThenPart(self, node, childNode):
        node.append(childNode, "thenPart")

    def HOOK_setElsePart(self, node, childNode):
        node.append(childNode, "elsePart")

    def HOOK_finish(self, node):
        pass

    def OR_build(self, tokenizer):
        return jasy.js.parse.Node.Node(tokenizer, "or")

    def OR_addOperand(self, node, childNode):
        node.append(childNode)

    def OR_finish(self, node):
        pass

    def AND_build(self, tokenizer):
        return jasy.js.parse.Node.Node(tokenizer, "and")

    def AND_addOperand(self, node, childNode):
        node.append(childNode)

    def AND_finish(self, node):
        pass

    def BITWISEOR_build(self, tokenizer):
        return jasy.js.parse.Node.Node(tokenizer, "bitwise_or")

    def BITWISEOR_addOperand(self, node, childNode):
        node.append(childNode)

    def BITWISEOR_finish(self, node):
        pass

    def BITWISEXOR_build(self, tokenizer):
        return jasy.js.parse.Node.Node(tokenizer, "bitwise_xor")

    def BITWISEXOR_addOperand(self, node, childNode):
        node.append(childNode)

    def BITWISEXOR_finish(self, node):
        pass

    def BITWISEAND_build(self, tokenizer):
        return jasy.js.parse.Node.Node(tokenizer, "bitwise_and")

    def BITWISEAND_addOperand(self, node, childNode):
        node.append(childNode)

    def BITWISEAND_finish(self, node):
        pass

    def EQUALITY_build(self, tokenizer):
        # NB: tokenizer.token.type must be "eq", "ne", "strict_eq", or "strict_ne".
        return jasy.js.parse.Node.Node(tokenizer)

    def EQUALITY_addOperand(self, node, childNode):
        node.append(childNode)

    def EQUALITY_finish(self, node):
        pass

    def RELATIONAL_build(self, tokenizer):
        # NB: tokenizer.token.type must be "lt", "le", "ge", or "gt".
        return jasy.js.parse.Node.Node(tokenizer)

    def RELATIONAL_addOperand(self, node, childNode):
        node.append(childNode)

    def RELATIONAL_finish(self, node):
        pass

    def SHIFT_build(self, tokenizer):
        # NB: tokenizer.token.type must be "lsh", "rsh", or "ursh".
        return jasy.js.parse.Node.Node(tokenizer)

    def SHIFT_addOperand(self, node, childNode):
        node.append(childNode)

    def SHIFT_finish(self, node):
        pass

    def ADD_build(self, tokenizer):
        # NB: tokenizer.token.type must be "plus" or "minus".
        return jasy.js.parse.Node.Node(tokenizer)

    def ADD_addOperand(self, node, childNode):
        node.append(childNode)

    def ADD_finish(self, node):
        pass

    def MULTIPLY_build(self, tokenizer):
        # NB: tokenizer.token.type must be "mul", "div", or "mod".
        return jasy.js.parse.Node.Node(tokenizer)

    def MULTIPLY_addOperand(self, node, childNode):
        node.append(childNode)

    def MULTIPLY_finish(self, node):
        pass

    def UNARY_build(self, tokenizer):
        # NB: tokenizer.token.type must be "delete", "void", "typeof", "not", "bitwise_not",
        # "unary_plus", "unary_minus", "increment", or "decrement".
        if tokenizer.token.type == "plus":
            tokenizer.token.type = "unary_plus"
        elif tokenizer.token.type == "minus":
            tokenizer.token.type = "unary_minus"
            
        return jasy.js.parse.Node.Node(tokenizer)

    def UNARY_addOperand(self, node, childNode):
        node.append(childNode)

    def UNARY_setPostfix(self, node):
        node.postfix = True

    def UNARY_finish(self, node):
        pass

    def MEMBER_build(self, tokenizer, tokenType=None):
        node = jasy.js.parse.Node.Node(tokenizer, tokenType)
        if node.type == "identifier":
            node.value = tokenizer.token.value
        return node

    def MEMBER_rebuildNewWithArgs(self, node):
        node.type = "new_with_args"

    def MEMBER_addOperand(self, node, childNode):
        node.append(childNode)

    def MEMBER_finish(self, node):
        pass

    def PRIMARY_build(self, tokenizer, tokenType):
        # NB: tokenizer.token.type must be "null", "this", "true", "false", "identifier", "number", "string", or "regexp".
        node = jasy.js.parse.Node.Node(tokenizer, tokenType)
        if tokenType in ("identifier", "string", "regexp", "number"):
            node.value = tokenizer.token.value
            
        return node

    def PRIMARY_finish(self, node):
        pass

    def ARRAYINIT_build(self, tokenizer):
        return jasy.js.parse.Node.Node(tokenizer, "array_init")

    def ARRAYINIT_addElement(self, node, childNode):
        node.append(childNode)

    def ARRAYINIT_finish(self, node):
        pass

    def ARRAYCOMP_build(self, tokenizer):
        return jasy.js.parse.Node.Node(tokenizer, "array_comp")
    
    def ARRAYCOMP_setExpression(self, node, expression):
        node.append(expression, "expression")
    
    def ARRAYCOMP_setTail(self, node, childNode):
        node.append(childNode, "tail")
    
    def ARRAYCOMP_finish(self, node):
        pass

    def COMPTAIL_build(self, tokenizer):
        return jasy.js.parse.Node.Node(tokenizer, "comp_tail")

    def COMPTAIL_setGuard(self, node, expression):
        node.append(expression, "guard")

    def COMPTAIL_addFor(self, node, childNode):
        node.append(childNode, "for")

    def COMPTAIL_finish(self, node):
        pass

    def OBJECTINIT_build(self, tokenizer):
        return jasy.js.parse.Node.Node(tokenizer, "object_init")

    def OBJECTINIT_addProperty(self, node, childNode):
        node.append(childNode)

    def OBJECTINIT_finish(self, node):
        pass

    def PROPERTYINIT_build(self, tokenizer):
        return jasy.js.parse.Node.Node(tokenizer, "property_init")

    def PROPERTYINIT_addOperand(self, node, childNode):
        node.append(childNode)

    def PROPERTYINIT_finish(self, node):
        pass

    def COMMA_build(self, tokenizer):
        return jasy.js.parse.Node.Node(tokenizer, "comma")

    def COMMA_addOperand(self, node, childNode):
        node.append(childNode)

    def COMMA_finish(self, node):
        pass

    def LIST_build(self, tokenizer):
        return jasy.js.parse.Node.Node(tokenizer, "list")

    def LIST_addOperand(self, node, childNode):
        node.append(childNode)

    def LIST_finish(self, node):
        pass

    def setHoists(self, id, vds):
        pass
        
########NEW FILE########
__FILENAME__ = Resolver
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

import jasy.js.Sorter as Sorter
import jasy.core.Console as Console

__all__ = ["Resolver"]

class Resolver():
    """Resolves dependencies between JavaScript files"""

    def __init__(self, session):
        
        # Keep session reference
        self.__session = session

        # Keep permutation reference
        self.__permutation = session.getCurrentPermutation()

        # Required classes by the user
        self.__required = []

        # Hard excluded classes (used for filtering previously included classes etc.)
        self.__excluded = []
        
        # Included classes after dependency calculation
        self.__included = []

        # Collecting all available classes
        self.__classes = {}
        for project in session.getProjects():
            self.__classes.update(project.getClasses())
        
        
    def addClassName(self, className):
        """ Adds a class to the initial dependencies """
        
        if not className in self.__classes:
            raise Exception("Unknown Class: %s" % className)
            
        Console.debug("Adding class: %s", className)
        self.__required.append(self.__classes[className])
        
        del self.__included[:]
        
        return self
            
            
    def removeClassName(self, className):
        """ Removes a class name from dependencies """
        
        for classObj in self.__required:
            if classObj.getId() == className:
                self.__required.remove(classObj)
                if self.__included:
                    self.__included = []
                return True
                
        return False


    def excludeClasses(self, classObjects):
        """ Excludes the given class objects (just a hard-exclude which is applied after calculating the current dependencies) """
        
        self.__excluded.extend(classObjects)
        
        # Invalidate included list
        self.__included = None
        
        return self
        

    def getRequiredClasses(self):
        """ Returns the user added classes - the so-called required classes. """
        
        return self.__required


    def getIncludedClasses(self):
        """ Returns a final set of classes after resolving dependencies """

        if self.__included:
            return self.__included
        
        Console.info("Detecting class dependencies...")
        Console.indent()
        
        collection = set()
        for classObj in self.__required:
            self.__resolveDependencies(classObj, collection)
            
        # Filter excluded classes
        for classObj in self.__excluded:
            if classObj in collection:
                collection.remove(classObj)
        
        self.__included = collection

        Console.outdent()
        Console.debug("Including %s classes", len(collection))
        
        return self.__included
        
        
    def getSortedClasses(self):
        """ Returns a list of sorted classes """

        return Sorter.Sorter(self, self.__session).getSortedClasses()


    def __resolveDependencies(self, classObj, collection):
        """ Internal resolver engine which works recursively through all dependencies """
        
        collection.add(classObj)
        dependencies = classObj.getDependencies(self.__permutation, classes=self.__classes)
        
        for depObj in dependencies:
            if not depObj in collection:
                self.__resolveDependencies(depObj, collection)
                    
########NEW FILE########
__FILENAME__ = Sorter
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

import time
import jasy.core.Console as Console

__all__ = ["Sorter"]


class CircularDependency(Exception):
    pass
    

class Sorter:
    def __init__(self, resolver, session):
        # Keep classes/permutation reference
        # Classes is set(classObj, ...)
        self.__resolver = resolver
        self.__permutation = session.getCurrentPermutation()
        
        classes = self.__resolver.getIncludedClasses()

        # Build class name dict
        self.__names = dict([(classObj.getId(), classObj) for classObj in classes])
        
        # Initialize fields
        self.__loadDeps = {}
        self.__circularDeps = {}
        self.__sortedClasses = []


    def getSortedClasses(self):
        """ Returns the sorted class list (caches result) """

        if not self.__sortedClasses:
            Console.debug("Sorting classes...")
            Console.indent()
            
            classNames = self.__names
            for className in classNames:
                self.__getLoadDeps(classNames[className])

            result = []
            requiredClasses = self.__resolver.getRequiredClasses()
            for classObj in requiredClasses:
                if not classObj in result:
                    Console.debug("Start adding with: %s", classObj)
                    self.__addSorted(classObj, result)

            Console.outdent()
            self.__sortedClasses = result

        return self.__sortedClasses


    def __addSorted(self, classObj, result, postponed=False):
        """ Adds a single class and its dependencies to the sorted result list """

        loadDeps = self.__getLoadDeps(classObj)
        
        for depObj in loadDeps:
            if not depObj in result:
                self.__addSorted(depObj, result)

        if classObj in result:
            return
            
        # debug("Adding class: %s", classObj)
        result.append(classObj)

        # Insert circular dependencies as soon as possible
        if classObj in self.__circularDeps:
            circularDeps = self.__circularDeps[classObj]
            for depObj in circularDeps:
                if not depObj in result:
                    self.__addSorted(depObj, result, True)



    def __getLoadDeps(self, classObj):
        """ Returns load time dependencies of given class """

        if not classObj in self.__loadDeps:
            self.__getLoadDepsRecurser(classObj, [])

        return self.__loadDeps[classObj]



    def __getLoadDepsRecurser(self, classObj, stack):
        """ 
        This is the main routine which tries to control over a system
        of unsorted classes. It directly tries to fullfil every dependency
        a class have, but has some kind of exception based loop protection
        to prevent circular dependencies from breaking the build.
        
        It respects break information given by file specific meta data, but
        also adds custom hints where it found recursions. This lead to a valid 
        sort, but might lead to problems between exeactly the two affected classes.
        Without doing an exact execution it's not possible to whether found out
        which of two each-other referencing classes needs to be loaded first.
        This is basically only interesting in cases where one class needs another
        during the definition phase which is not the case that often.
        """
        
        if classObj in stack:
            stack.append(classObj)
            msg = " >> ".join([x.getId() for x in stack[stack.index(classObj):]])
            raise CircularDependency("Circular Dependency: %s" % msg)
    
        stack.append(classObj)

        classDeps = classObj.getDependencies(self.__permutation, classes=self.__names, warnings=False)
        classMeta = classObj.getMetaData(self.__permutation)
        
        result = set()
        circular = set()
        
        # Respect manually defined breaks
        # Breaks are dependencies which are down-priorized to break
        # circular dependencies between classes.
        for breakName in classMeta.breaks:
            if breakName in self.__names:
                circular.add(self.__names[breakName])

        # Now process the deps of the given class
        loadDeps = self.__loadDeps
        for depObj in classDeps:
            if depObj is classObj:
                continue
            
            depName = depObj.getId()
            
            if depName in classMeta.breaks:
                Console.debug("Manual Break: %s => %s" % (classObj, depObj))
                pass
            
            elif depObj in loadDeps:
                result.update(loadDeps[depObj])
                result.add(depObj)
        
            else:
                current = self.__getLoadDepsRecurser(depObj, stack[:])
        
                result.update(current)
                result.add(depObj)
        
        # Sort dependencies by number of other dependencies
        # For performance reasions we access the __loadDeps 
        # dict directly as this data is already stored
        result = sorted(result, key=lambda depObj: len(self.__loadDeps[depObj]))
        
        loadDeps[classObj] = result
        
        if circular:
            self.__circularDeps[classObj] = circular
        
        return result

########NEW FILE########
__FILENAME__ = Lang
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

"""JavaScript 1.7 keywords"""
keywords = set([
    "break",
    "case", "catch", "const", "continue",
    "debugger", "default", "delete", "do",
    "else",
    "false", "finally", "for", "function",
    "if", "in", "instanceof",
    "let",
    "new", "null",
    "return",
    "switch",
    "this", "throw", "true", "try", "typeof",
    "var", "void",
    "yield",
    "while", "with"
])

########NEW FILE########
__FILENAME__ = Tokenizer
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

#
# License: MPL 1.1/GPL 2.0/LGPL 2.1
# Authors: 
#   - Brendan Eich <brendan@mozilla.org> (Original JavaScript) (2004-2010)
#   - Sebastian Werner <info@sebastian-werner.net> (Python Port) (2010)
#

import re, copy

import jasy.js.tokenize.Lang as Lang
import jasy.js.api.Comment as Comment
import jasy.core.Console as Console

__all__ = [ "Tokenizer" ]


# Operator and punctuator mapping from token to tree node type name.
# NB: because the lexer doesn't backtrack, all token prefixes must themselves
# be valid tokens (e.g. !== is acceptable because its prefixes are the valid
# tokens != and !).
operatorNames = {
    '<'   : 'lt', 
    '>'   : 'gt', 
    '<='  : 'le', 
    '>='  : 'ge', 
    '!='  : 'ne', 
    '!'   : 'not', 
    '=='  : 'eq', 
    '===' : 'strict_eq', 
    '!==' : 'strict_ne', 

    '>>'  : 'rsh', 
    '<<'  : 'lsh',
    '>>>' : 'ursh', 
     
    '+'   : 'plus', 
    '*'   : 'mul', 
    '-'   : 'minus', 
    '/'   : 'div', 
    '%'   : 'mod', 

    ','   : 'comma', 
    ';'   : 'semicolon', 
    ':'   : 'colon', 
    '='   : 'assign', 
    '?'   : 'hook', 

    '&&'  : 'and', 
    '||'  : 'or', 

    '++'  : 'increment', 
    '--'  : 'decrement', 

    ')'   : 'right_paren', 
    '('   : 'left_paren', 
    '['   : 'left_bracket', 
    ']'   : 'right_bracket', 
    '{'   : 'left_curly', 
    '}'   : 'right_curly', 

    '&'   : 'bitwise_and', 
    '^'   : 'bitwise_xor', 
    '|'   : 'bitwise_or', 
    '~'   : 'bitwise_not'
}


# Assignment operators
assignOperators = ["|", "^", "&", "<<", ">>", ">>>", "+", "-", "*", "/", "%"]




#
# Classes
#

class Token: 
    __slots__ = ["type", "start", "line", "assignOp", "end", "value"]


class ParseError(Exception):
    def __init__(self, message, fileId, line):
        Exception.__init__(self, "Syntax error: %s\n%s:%s" % (message, fileId, line))


class Tokenizer(object):
    def __init__(self, source, fileId="", line=1):
        # source: JavaScript source
        # fileId: Filename (for debugging proposes)
        # line: Line number (for debugging proposes)
        self.cursor = 0
        self.source = str(source)
        self.tokens = {}
        self.tokenIndex = 0
        self.lookahead = 0
        self.scanNewlines = False
        self.fileId = fileId
        self.line = line
        self.comments = []

    input_ = property(lambda self: self.source[self.cursor:])
    token = property(lambda self: self.tokens.get(self.tokenIndex))


    def done(self):
        # We need to set scanOperand to true here because the first thing
        # might be a regexp.
        return self.peek(True) == "end"
        

    def match(self, tokenType, scanOperand=False):
        return self.get(scanOperand) == tokenType or self.unget()


    def mustMatch(self, tokenType):
        if not self.match(tokenType):
            raise ParseError("Missing " + tokenType, self.fileId, self.line)
            
        return self.token


    def peek(self, scanOperand=False):
        if self.lookahead:
            next = self.tokens.get((self.tokenIndex + self.lookahead) & 3)
            if self.scanNewlines and (getattr(next, "line", None) != getattr(self, "line", None)):
                tokenType = "newline"
            else:
                tokenType = getattr(next, "type", None)
        else:
            tokenType = self.get(scanOperand)
            self.unget()
            
        return tokenType


    def peekOnSameLine(self, scanOperand=False):
        self.scanNewlines = True
        tokenType = self.peek(scanOperand)
        self.scanNewlines = False
        return tokenType
        

    def getComments(self):
        if self.comments:
            comments = self.comments
            self.comments = []
            return comments
            
        return None


    def skip(self):
        """Eats comments and whitespace."""
        input = self.source
        startLine = self.line

        # Whether this is the first called as happen on start parsing a file (eat leading comments/white space)
        startOfFile = self.cursor is 0
        
        indent = ""
        
        while (True):
            if len(input) > self.cursor:
                ch = input[self.cursor]
            else:
                return
                
            self.cursor += 1
            
            if len(input) > self.cursor:
                next = input[self.cursor]
            else:
                next = None

            if ch == "\n" and not self.scanNewlines:
                self.line += 1
                indent = ""
                
            elif ch == "/" and next == "*":
                self.cursor += 1
                text = "/*"
                inline = startLine == self.line and startLine > 1
                commentStartLine = self.line
                if startLine == self.line and not startOfFile:
                    mode = "inline"
                elif (self.line-1) > startLine:
                    # distance before this comment means it is a comment block for a whole section (multiple lines of code)
                    mode = "section"
                else:
                    # comment for maybe multiple following lines of code, but not that important (no visual white space divider)
                    mode = "block"
                    
                while (True):
                    try:
                        ch = input[self.cursor]
                        self.cursor += 1
                    except IndexError:
                        raise ParseError("Unterminated comment", self.fileId, self.line)
                        
                    if ch == "*":
                        next = input[self.cursor]
                        if next == "/":
                            text += "*/"
                            self.cursor += 1
                            break
                            
                    elif ch == "\n":
                        self.line += 1
                        
                    text += ch
                    
                
                # Filter escaping on slash-star combinations in comment text
                text = text.replace("*\/", "*/")
                
                try:
                    self.comments.append(Comment.Comment(text, mode, commentStartLine, indent, self.fileId))
                except Comment.CommentException as commentError:
                    Console.error("Ignoring comment in %s: %s", self.fileId, commentError)
                    
                    
            elif ch == "/" and next == "/":
                self.cursor += 1
                text = "//"
                if startLine == self.line and not startOfFile:
                    mode = "inline"
                elif (self.line-1) > startLine:
                    # distance before this comment means it is a comment block for a whole section (multiple lines of code)
                    mode = "section"
                else:
                    # comment for maybe multiple following lines of code, but not that important (no visual white space divider)
                    mode = "block"
                    
                while (True):
                    try:
                        ch = input[self.cursor]
                        self.cursor += 1
                    except IndexError:
                        # end of file etc.
                        break

                    if ch == "\n":
                        self.line += 1
                        break
                    
                    text += ch
                    
                try:
                    self.comments.append(Comment.Comment(text, mode, self.line-1, "", self.fileId))
                except Comment.CommentException:
                    Console.error("Ignoring comment in %s: %s", self.fileId, commentError)

            # check for whitespace, also for special cases like 0xA0
            elif ch in "\xA0 \t":
                indent += ch

            else:
                self.cursor -= 1
                return


    # Lexes the exponential part of a number, if present. Returns True if an
    # exponential part was found.
    def lexExponent(self):
        input = self.source
        next = input[self.cursor]
        if next == "e" or next == "E":
            self.cursor += 1
            ch = input[self.cursor]
            self.cursor += 1
            if ch == "+" or ch == "-":
                ch = input[self.cursor]
                self.cursor += 1

            if ch < "0" or ch > "9":
                raise ParseError("Missing exponent", self.fileId, self.line)

            while(True):
                ch = input[self.cursor]
                self.cursor += 1
                if not (ch >= "0" and ch <= "9"):
                    break
                
            self.cursor -= 1
            return True

        return False


    def lexZeroNumber(self, ch):
        token = self.token
        input = self.source
        token.type = "number"

        ch = input[self.cursor]
        self.cursor += 1
        if ch == ".":
            while(True):
                ch = input[self.cursor]
                self.cursor += 1
                if not (ch >= "0" and ch <= "9"):
                    break
                
            self.cursor -= 1
            self.lexExponent()
            token.value = input[token.start:self.cursor]
            
        elif ch == "x" or ch == "X":
            while(True):
                ch = input[self.cursor]
                self.cursor += 1
                if not ((ch >= "0" and ch <= "9") or (ch >= "a" and ch <= "f") or (ch >= "A" and ch <= "F")):
                    break
                    
            self.cursor -= 1
            token.value = input[token.start:self.cursor]

        elif ch >= "0" and ch <= "7":
            while(True):
                ch = input[self.cursor]
                self.cursor += 1
                if not (ch >= "0" and ch <= "7"):
                    break
                    
            self.cursor -= 1
            token.value = input[token.start:self.cursor]

        else:
            self.cursor -= 1
            self.lexExponent()     # 0E1, &c.
            token.value = 0
    

    def lexNumber(self, ch):
        token = self.token
        input = self.source
        token.type = "number"

        floating = False
        while(True):
            ch = input[self.cursor]
            self.cursor += 1
            
            if ch == "." and not floating:
                floating = True
                ch = input[self.cursor]
                self.cursor += 1
                
            if not (ch >= "0" and ch <= "9"):
                break

        self.cursor -= 1

        exponent = self.lexExponent()
        segment = input[token.start:self.cursor]
        
        # Protect float or exponent numbers
        if floating or exponent:
            token.value = segment
        else:
            token.value = int(segment)


    def lexDot(self, ch):
        token = self.token
        input = self.source
        next = input[self.cursor]
        
        if next >= "0" and next <= "9":
            while (True):
                ch = input[self.cursor]
                self.cursor += 1
                if not (ch >= "0" and ch <= "9"):
                    break

            self.cursor -= 1
            self.lexExponent()

            token.type = "number"
            token.value = input[token.start:self.cursor]

        else:
            token.type = "dot"


    def lexString(self, ch):
        token = self.token
        input = self.source
        token.type = "string"

        hasEscapes = False
        delim = ch
        ch = input[self.cursor]
        self.cursor += 1
        while ch != delim:
            if ch == "\\":
                hasEscapes = True
                self.cursor += 1

            ch = input[self.cursor]
            self.cursor += 1

        if hasEscapes:
            token.value = eval(input[token.start:self.cursor])
        else:
            token.value = input[token.start+1:self.cursor-1]


    def lexRegExp(self, ch):
        token = self.token
        input = self.source
        token.type = "regexp"

        while (True):
            try:
                ch = input[self.cursor]
                self.cursor += 1
            except IndexError:
                raise ParseError("Unterminated regex", self.fileId, self.line)

            if ch == "\\":
                self.cursor += 1
                
            elif ch == "[":
                while (True):
                    if ch == "\\":
                        self.cursor += 1

                    try:
                        ch = input[self.cursor]
                        self.cursor += 1
                    except IndexError:
                        raise ParseError("Unterminated character class", self.fileId, self.line)
                    
                    if ch == "]":
                        break
                    
            if ch == "/":
                break

        while(True):
            ch = input[self.cursor]
            self.cursor += 1
            if not (ch >= "a" and ch <= "z"):
                break

        self.cursor -= 1
        token.value = input[token.start:self.cursor]
    

    def lexOp(self, ch):
        token = self.token
        input = self.source

        op = ch
        while(True):
            try:
                next = input[self.cursor]
            except IndexError:
                break
                
            if (op + next) in operatorNames:
                self.cursor += 1
                op += next
            else:
                break
        
        try:
            next = input[self.cursor]
        except IndexError:
            next = None

        if next == "=" and op in assignOperators:
            self.cursor += 1
            token.type = "assign"
            token.assignOp = operatorNames[op]
            op += "="
            
        else:
            token.type = operatorNames[op]
            token.assignOp = None


    # FIXME: Unicode escape sequences
    # FIXME: Unicode identifiers
    def lexIdent(self, ch):
        token = self.token
        input = self.source

        try:
            while True:
                ch = input[self.cursor]
                self.cursor += 1
            
                if not ((ch >= "a" and ch <= "z") or (ch >= "A" and ch <= "Z") or (ch >= "0" and ch <= "9") or ch == "$" or ch == "_"):
                    break
                    
        except IndexError:
            self.cursor += 1
            pass
        
        # Put the non-word character back.
        self.cursor -= 1

        identifier = input[token.start:self.cursor]
        if identifier in Lang.keywords:
            token.type = identifier
        else:
            token.type = "identifier"
            token.value = identifier


    def get(self, scanOperand=False):
        """ 
        It consumes input *only* if there is no lookahead.
        Dispatches to the appropriate lexing function depending on the input.
        """
        while self.lookahead:
            self.lookahead -= 1
            self.tokenIndex = (self.tokenIndex + 1) & 3
            token = self.tokens[self.tokenIndex]
            if token.type != "newline" or self.scanNewlines:
                return token.type

        self.skip()

        self.tokenIndex = (self.tokenIndex + 1) & 3
        self.tokens[self.tokenIndex] = token = Token()

        token.start = self.cursor
        token.line = self.line

        input = self.source
        if self.cursor == len(input):
            token.end = token.start
            token.type = "end"
            return token.type

        ch = input[self.cursor]
        self.cursor += 1
        
        if (ch >= "a" and ch <= "z") or (ch >= "A" and ch <= "Z") or ch == "$" or ch == "_":
            self.lexIdent(ch)
        
        elif scanOperand and ch == "/":
            self.lexRegExp(ch)
        
        elif ch == ".":
            self.lexDot(ch)

        elif self.scanNewlines and ch == "\n":
            token.type = "newline"
            self.line += 1

        elif ch in operatorNames:
            self.lexOp(ch)
        
        elif ch >= "1" and ch <= "9":
            self.lexNumber(ch)
        
        elif ch == "0":
            self.lexZeroNumber(ch)
        
        elif ch == '"' or ch == "'":
            self.lexString(ch)
        
        else:
            raise ParseError("Illegal token: %s (Code: %s)" % (ch, ord(ch)), self.fileId, self.line)

        token.end = self.cursor
        return token.type
        

    def unget(self):
        """ Match depends on unget returning undefined."""
        self.lookahead += 1
        
        if self.lookahead == 4: 
            raise ParseError("PANIC: too much lookahead!", self.fileId, self.line)
        
        self.tokenIndex = (self.tokenIndex - 1) & 3
        
    
    def save(self):
        return {
            "cursor" : self.cursor,
            "tokenIndex": self.tokenIndex,
            "tokens": copy.copy(self.tokens),
            "lookahead": self.lookahead,
            "scanNewlines": self.scanNewlines,
            "line": self.line
        }

    
    def rewind(self, point):
        self.cursor = point["cursor"]
        self.tokenIndex = point["tokenIndex"]
        self.tokens = copy.copy(point["tokens"])
        self.lookahead = point["lookahead"]
        self.scanNewline = point["scanNewline"]
        self.line = point["line"]

########NEW FILE########
__FILENAME__ = assettype
#!/usr/bin/env python3

import sys, os, unittest, logging, pkg_resources, tempfile

# Extend PYTHONPATH with local 'lib' folder
jasyroot = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]), os.pardir, os.pardir, os.pardir))
sys.path.insert(0, jasyroot)

import jasy.asset.ImageInfo as ImageInfo



class Tests(unittest.TestCase):


    def createGIF(self, path):
        filePath = os.path.join(path, "giffile.gif")
        handle = open(filePath, mode="wb")
        #x: 16; y: 16
        handle.write(b'GIF89a\x10\x00\x10\x00\xe6l\x00\x00\x00\xb5\xff\xff\xff\x01\x00\x00\x02\x05\x00\x00\x00 \x03\x00\x00\x01\x01\x00\x00\x00\'\xca\xc9\xcf\x00\x00I\x04\x00\x00\x00\x00"\x00\x00\x1c\n\x0c\x1b\r\x08\x0c\x00\x00\t\x05\x00\'\x00\x00G\x00\x00:\x00\x00)\x01\x00\x02\x00\x00S\xf7\xfc\xff\xcf\xcf\xd9\x00\x02\x00\x00\x00>\xf4\xf5\xff\x04\x07\x00\x00\x00V\x00\x00\x1e\xbf\xc6\xb4\xb3\xb0\xc3\x00\x02\x12\x01\x00C\xfc\xfc\xff\x00\x00Y\xfb\xfe\xff\xf0\xf3\xff\x03\x02<\x04\t&\xd5\xd4\xd2\xfb\xff\xf6\x17\x14\r\xfe\xff\xff\xc5\xc7\xbc\xc7\xc9\xb3\xd0\xcd\xe8\x02\x03;\xbd\xbc\xc4\xba\xbc\xaf\xcc\xcf\xbe\xfe\xfa\xff\xc3\xc4\xbf\xfc\xf9\xff\xfc\xfe\xf9\xf4\xf7\xff\xd1\xd1\xdb\xf6\xf4\xff\xdb\xdc\xd6\xb7\xb4\xbf\x00\x00\x19\x0c\x06"\xc9\xc3\xf3\xca\xc9\xdb\x00\x05\'\x01\x00,\xcc\xcd\xc8\x00\x00c\x02\x00F\x00\x005\x04\x04\x06\xbb\xbd\xb2\x05\x00\\\x0b\x07\x04\xfc\xff\xff\x00\x00L\x00\x01\x00\xf0\xf2\xff\xda\xe2\xd3\xfb\xff\xfa\x00\x00\\\x07\x01\'\xdb\xde\xcd\x03\x01\x00\x00\x00,\x00\x02\x18\x01\x03\x02\x00\x00\x04\xb5\xb3\xc8\xda\xe0\xd4\x00\x00#\xb5\xb8\xb1\x07\x02<\xfc\xff\xf8\xfc\xfe\xff\x0e\x08P\x00\x00\x00\x00\x00+\x03\x00\x07\xbe\xbe\xbc\x00\x00Q\x04\x06\x00\xfc\xfa\xff\x00\x00\x13\x04\x002\x01\x00\x0e\xfa\xfa\xff\xc8\xc8\xc0\xf2\xf7\xd7\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00!\xf9\x04\x01\x00\x00l\x00,\x00\x00\x00\x00\x10\x00\x10\x00\x00\x07\xb3\x80l\x82l\x03\x85W\r\r\x0fL\x1b\x18\x83\x83e-G\x17X?8c:F\x8e\x82\x024+j^7J6[V`*\x8eg.\x1a\x16O)N]Y\x1eRSb=\x07E\x19D!/\x07\x0b\'\x1d\x04Z<\x14T\x00\xc6\xc7\xc8\xc8Q&\x00\x01\xce\xcd\xc6\x01\xd1\xceA\x0c\xd0\xd2\xcf\xd8\xc7\x04 \xcd\xd9\xde\xd7\x01\x04U\xd0\xd1\xe6\xd2\xcda@\xe5\xe5\xe8\xce\x01\x13\\\xc9\xf3\xc7\x0c\x10h\x12KPC#d\t\x11\t\x90T\xe0\xf0%\x8d\xa3\x05>j\x88(A\xa2\x89\x99\x1c3>\x14p\xe4`\x07\x02\x162b\x08A\x00\x03\xc5\x1a\x05\x8e\x14$)P\xc0\x80\x01\x01(\x05\x18`\x13\x08\x00;')
        handle.close()
        return filePath

    def createPNG(self, path):
        filePath = os.path.join(path, "pngfile.png")
        handle = open(filePath, mode="wb")
        #x: 16; y: 16
        handle.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x03\x00\x00\x00(-\x0fS\x00\x00\x00\x07tIME\x07\xd4\x07\x02\n&,\xa1\xc3\x8a\x13\x00\x00\x00\tpHYs\x00\x00\x0b\x12\x00\x00\x0b\x12\x01\xd2\xdd~\xfc\x00\x00\x00\x04gAMA\x00\x00\xb1\x8f\x0b\xfca\x05\x00\x00\x01\x98PLTE\xfb\xfb\xfb\x94\x94\xad\xc6\xc6\xd5\xf0\xf0\xf4\xe8\xe8\xee\xe6\xe6\xed\xe4\xe4\xeb\xe0\xe0\xe9\xdf\xdf\xe8\xdc\xdc\xe5\xda\xda\xe4\xd7\xd7\xe2\xf3\xf3\xf6\xe7\xe7\xee\xe5\xe5\xec\xe1\xe1\xe9\xdb\xdb\xe5mnnvc`\x94\x8a\x89\xa6\xa8\xa9\xb5\xb5\xb4\xa4\xa3\xa4\x8e\x8e\x8f\x80\x80\x80rrr__aXZq\x96\x95\x95\xb4pc\xd3\xbb\xb2\xdb\xe0\xe1\xd7\xd7\xd7\xc6\xc6\xc5\xb3\xb2\xb2\xa8\xa8\xa8\x95\x95\x95\x86\x86\x86OQf\xb4\xb6\xb4\xec\x8f\x7f\xe9\xab\xa3\xf3\xfc\xfe\xdf\xdf\xdf\xce\xce\xcd\xc7\xc7\xc7\xb6\xb4\xb5\xa1\x9f\xa0\x94\x94\x94]_u\xd9\xd9\xe3\xd6\xd6\xe1\xb7\xc1\xc3\xe0\x9a\x90\xcega\xf3\xef\xef\xc1\xd2\xdf\x8a\x9a\xad\xc1\xbd\xbc\x92\x9a\x98y~~\x8c\x89\x8b_`u\xba\xb6\xb3\xe6t\\\xbe72\xe5\xd4\xd5\x8d\xce\xe4Kx\xa3\x9b\x9f\xa3w\xa7r@}Mu{z_`v\xd4\xd4\xe0\xd2\xd2\xde\xbb\x85}\xed[:\xc56*\xca\x97\x9cn\xcd\xeb4\x85\xb8x\x7f\x97|\xbcg8\xa16Mp]__v\xd1\xd1\xdd\xce\xce\xdb\xc1}s\xf3\x91n\xdcN;\x9e@Lb\xc3\xe3=\x98\xc6DZ\x8a\xa0\xc5\x9ab\xbb[8yNTUj\xcb\xcb\xd9\xc8\xc8\xd6\xafZY\xf7\xca\xb7\xf4\x8cp\xafCG\x98\xd5\xea\\\xba\xde>q\x9d\xbf\xd5\xc3\x9f\xd7\x96@\\nORv\xd0\xd0\xdc\xc4\xc4\xd3\xc2\xc2\xd1\xccb`\xc2@;\xbc\x88\x93\x8c\xc4\xdbQ\xb4\xda\xa8\xca\xd9\xd3\xe3\xca\x91\xc5\x8e\xa6\xb1\xb0\xcd\xcd\xda\xbf\xbf\xd0\xfb\xfb\xfc\xf8\xf8\xfa\xf5\xf5\xf8\xee\xee\xf2\xed\xed\xf2\xc9\xc9\xd7\xf4\xf4\xf7\xea\xea\xf0\xde\xde\xe7\xe6\xf1\xac\xf6\x00\x00\x00\x01tRNS\x00@\xe6\xd8f\x00\x00\x00\xd1IDATx\xdac````\x82\x02F\x06(`\xaaohmjkg\x87\x8b\x00\x05\x1a\x99\x9b\xf9\xd9\x99Z\x18\x91\x04\x9a\xd8\xd8\x19\x81\x00\xc8-)-+\xaf\xa8\xac\xaa\xae\xe1\x10\xa8\xad\x03\n\xa4\xa5gdfe\xe7\xe4\xe6\xe5\x17\x14\x16\x15\x03\x05"\xa3\xa2cb\xe3\xe2\x13\x12\x93\x92SRA\xc6\xfa\xf8\xfa\xf9\x07\x04\x06\x05\x87\x84\x86y\x87G\x00\x05\xec\x1d\x1c\x9d\x9c]\\\xdd\xdc=<\x8d\xbd\xbc\x81\x02&\xa6f\xe6\x16\x96V\xd66\xb6v\\\xdc\xc6@\x01u\rM-m\x1d]=}\x03C\x01#\x90\x80\x8c\xac\x9c\xbc\x82\xa2\x92\xb2\x8a\xaa\x1a\'\x177P@PHXDTL\\BRJ\x1a"\x00r)\x0f\x0b/\x1f\x1b?\x87\x00\\\x80\x99\x85\x85\x95\x8d\x9d\x03\xae\x82\x11\t0\x00\x00\xcc\x16(\x9e^\xe8\x01\xfd\x00\x00\x00\x00IEND\xaeB`\x82')
        handle.close()
        return filePath

    def createJPG(self, path):
        filePath = os.path.join(path, "jpgfile.jpg")
        handle = open(filePath, mode="wb")
        #x: 32; y: 32
        handle.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x02\x00\x00d\x00d\x00\x00\xff\xec\x00\x11Ducky\x00\x01\x00\x04\x00\x00\x00<\x00\x00\xff\xee\x00\x0eAdobe\x00d\xc0\x00\x00\x00\x01\xff\xdb\x00\x84\x00\x06\x04\x04\x04\x05\x04\x06\x05\x05\x06\t\x06\x05\x06\t\x0b\x08\x06\x06\x08\x0b\x0c\n\n\x0b\n\n\x0c\x10\x0c\x0c\x0c\x0c\x0c\x0c\x10\x0c\x0e\x0f\x10\x0f\x0e\x0c\x13\x13\x14\x14\x13\x13\x1c\x1b\x1b\x1b\x1c\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x01\x07\x07\x07\r\x0c\r\x18\x10\x10\x18\x1a\x15\x11\x15\x1a\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\xff\xc0\x00\x11\x08\x00 \x00 \x03\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x80\x00\x00\x03\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x05\x06\x07\x04\x02\x08\x01\x00\x02\x03\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x04\x00\x03\x06\x01\x05\x10\x00\x02\x02\x01\x03\x03\x04\x03\x01\x01\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x11\x00!\x05\x12\x13\x061Q"\x07A2\x14qB\x11\x00\x01\x02\x04\x04\x04\x05\x05\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x02\x11!\x03\x041AQ\x12"B\x05\x06\xf0a\xa12\x13q\x81\x91\xb1\xc1\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00?\x00\xaaV\xfb[\xc8n\xf26\xe8S\xa9L\xcbQ\x1aI\x1aN\xf0R\x16E\x8b\xfe:\xf1\xf2pIl*\x8c\x96 \ry\xc2\xed\xc4\x90\x00\x92\xd9\xd4\xed\xca\x14\xe9\xb5\xefs\xe0\xe3\tm\xd0\x9c\xe1\xa6S&@E.V\xf2o\'\xb74\x0b^\xc8\x92Y\xd29%\x8cOm\x9a\x1e\xfdG\xbb\x12\xb2\xac$\xbb<Q6\x04]{\xed\xa8/\x1ep\r\xf5\xd2> \x8e\xa7nZ\xb0\x12\xe7T\x00\x129\'\xb5\xe1\x86\x13\x90\x0e#\xdd\xb6SA(}\xb5\xcfI\xe55xt\x92Pd\xb1,rJ&\x9b\x04A\x1c\x92\x92\x11\xd5\x1b\xe5\xda\xc6\x19A\xdfq\xa2\xb7\xbcuG\xed *z\xcfn\xd1\xb4\xb6\x15\x9a\xe7\x12H\x91\xdb\x9f\xd3\xf8a\xe6\xbd\x0b^\xd4\xf1X\x14\xeen\xed\x9e\xc4\xe0`H\x07\xe0\xfb0\xd3\xeb\x1e\xa4\xf6~\x85\xf2\t&\xbf$~SV8\xef\xf5,\xc8x\xb7rc2\xac\xc1z\x8d\xdf\xc3\xc6\xa7 \x0fM l\x1b9\x99\xadk{\xb6\xa8\r\x1b\x1b\xc1\x84\xce\x85\xbf\xa2Px\xbe\xae\xf3[\xd4\xe1C\xe55b\x8c\xc0"\x02>%\x15\x9a3Y\xab(\x91\x96\xc2\xb4\x85`\x91\x91K\x92W;cDlA\xe6>\x9aA\x03{\xa5\xc0\x93\xf16$\xc7\xdc\xfcw\x07\xcb\x8a\\@\x13\x0csX</\xe99\xe8y\x9b\xde\xb1\xcd\xa5\xb1\xc1\xcaU\xebGT\xc4d\xfe\x8a\x8c\xa0\x96\xfe\x89::{\xde\xc78\xd4\xb6\xb6k\x1e`p]\xeb]r\xad\xcd\xbbC\xda\x00|\xe5\x1c\x89\x1ft\xf6\xfcP\xe2\xec\t\xa8f\xbbDD\x98_\xd4\xf4o\x86\x19\xc1\xd3\xf0YEQo\xd4\xff\x00\x9a\x15\x12r\xf20q\xbc46d\x1drv#\xec@?y$*\x02\xa2\x8fvb\x06\xb8\xf7m\x11W\xdb\xd05^\x1a0\xcc\xe85Bj\xd7\xe4\xeb\x9a\xf6*IR>Q\xe4\x92;\xad4\xc0\xa5\x89\\\xb4\xd2\xc5\xd1\x18f\xea\x8b\xa5\xba7\xca\xa89\x18\xce\xa9k\x1c&1\xcdz5.h:-qq\xa7\xcb\x016\xc0@c\xaf0\xcdgn[\x90\xb4\xd2\xa5\xca\xd1G\x98\xe5)5y;\xb1\x16BQ\x94>\x06\xe1\x81\xf5\xc1\xdb\xd3V\xb1\xce\xc0\x84\x9d\xc5*!\xbb\xa9\xb8\xbay\x88\x15OoC\xa2I\xa9\x9bs^%^\xe4\x13[\x96\xeb_\xa9\x14p\xb4\x06\x95\xd7\x8a9#^\x92T\xa4\x05I\xdc\xee\x18\x8fm\x0e\xc1\x18\xa6\x05\xd3\x85?\x8cH\x1f\xca\x9c\xdb\xafg\xfa\x9ax/JC\xda\x96\xf1H\xaa\xf2\x95\xb1-\x90\xe2\xc2\x0e\xdc\x1b\x99\x15\xc2wve\x00\xe0|\x8e\x8e)u\xcf\x8f\xc1\xcc\xa71U&\xb9rx:\xe4\xcc\x0b\r\xe5I\'\x98\xb1i\\K\x08@$/\x92\x99\n\xac:\x81\xdd\xb5\xd8\xa8\xbf\xff\xd9')
        handle.close()
        return filePath


    def test_img_file_classes(self):
        tempdir = tempfile.TemporaryDirectory().name
        os.makedirs(tempdir)
        gifpath = self.createGIF(tempdir)
        pngpath = self.createPNG(tempdir)
        jpgpath = self.createJPG(tempdir)

        gif = ImageInfo.GifFile(gifpath)
        png = ImageInfo.PngFile(pngpath)
        jpg = ImageInfo.JpegFile(jpgpath)

        self.assertTrue(gif.verify())
        self.assertEqual(gif.type(), 'gif')
        self.assertEqual(gif.size(), (16, 16))

        self.assertTrue(png.verify())
        self.assertEqual(png.type(), 'png')
        self.assertEqual(png.size(), (16, 16))

        self.assertTrue(jpg.verify())
        self.assertEqual(jpg.type(), 'jpeg')
        self.assertEqual(jpg.size(), (32, 32))


    def test_type_correction(self):
        tempdir = tempfile.TemporaryDirectory().name
        os.makedirs(tempdir)
        gifpath = self.createGIF(tempdir)
        pngpath = self.createPNG(tempdir)
        jpgpath = self.createJPG(tempdir)

        jpg = ImageInfo.GifFile(gifpath)
        gif = ImageInfo.PngFile(pngpath)
        png = ImageInfo.JpegFile(jpgpath)

        self.assertTrue(gif.verify())
        self.assertEqual(gif.type(), 'png')
        self.assertEqual(gif.size(), (16, 16))

        self.assertTrue(png.verify())
        self.assertEqual(png.type(), 'jpeg')
        self.assertEqual(png.size(), (32, 32))

        self.assertTrue(jpg.verify())
        self.assertEqual(jpg.type(), 'gif')
        self.assertEqual(jpg.size(), (16, 16))


    def test_img_info_class(self):
        tempdir = tempfile.TemporaryDirectory().name
        os.makedirs(tempdir)
        gifpath = self.createGIF(tempdir)
        pngpath = self.createPNG(tempdir)
        jpgpath = self.createJPG(tempdir)

        gifInfo = ImageInfo.ImgInfo(gifpath)
        pngInfo = ImageInfo.ImgInfo(pngpath)
        jpgInfo = ImageInfo.ImgInfo(jpgpath)

        self.assertEqual(gifInfo.getSize(), (16, 16))
        self.assertEqual(pngInfo.getSize(), (16, 16))
        self.assertEqual(jpgInfo.getSize(), (32, 32))

        self.assertEqual(gifInfo.getInfo(), (16, 16, 'gif'))
        self.assertEqual(pngInfo.getInfo(), (16, 16, 'png'))
        self.assertEqual(jpgInfo.getInfo(), (32, 32, 'jpeg'))




if __name__ == '__main__':
    logging.getLogger().setLevel(logging.ERROR)
    suite = unittest.TestLoader().loadTestsFromTestCase(Tests)
    unittest.TextTestRunner(verbosity=2).run(suite)

########NEW FILE########
__FILENAME__ = cache
#!/usr/bin/env python3

import sys, os, unittest, logging, tempfile

# Extend PYTHONPATH with local 'lib' folder
jasyroot = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]), os.pardir, os.pardir, os.pardir))
sys.path.insert(0, jasyroot)

import jasy.core.Cache as Cache

class Tests(unittest.TestCase):

    def test_store_and_read(self):

        tempDirectory = tempfile.TemporaryDirectory().name
        os.makedirs(tempDirectory)
        cache = Cache.Cache(tempDirectory)
        cache.store("test", 1337)
        self.assertEqual(cache.read("test"), 1337)

    def test_overwriting(self):

        tempDirectory = tempfile.TemporaryDirectory().name
        os.makedirs(tempDirectory)
        cache = Cache.Cache(tempDirectory)
        cache.store("test", 1337)
        self.assertEqual(cache.read("test"), 1337)
        cache.store("test", "yeah")
        self.assertEqual(cache.read("test"), "yeah")

    def test_close_and_reopen(self):

        tempDirectory = tempfile.TemporaryDirectory().name
        os.makedirs(tempDirectory)
        cache = Cache.Cache(tempDirectory)
        cache.store("test", 1337)
        self.assertEqual(cache.read("test"), 1337)
        cache.close()
        cache2 = Cache.Cache(tempDirectory)
        self.assertEqual(cache2.read("test"), 1337)   

    def test_clear(self):     

        tempDirectory = tempfile.TemporaryDirectory().name
        os.makedirs(tempDirectory)
        cache = Cache.Cache(tempDirectory)
        cache.store("test", 1337)
        self.assertEqual(cache.read("test"), 1337)
        cache.close()
        cache2 = Cache.Cache(tempDirectory)
        cache2.clear()      
        cache2.close()
        cache3 = Cache.Cache(tempDirectory)
        self.assertEqual(cache3.read("test"), None)   

    def test_store_iMfalse_and_read_iMtrue(self):

        tempDirectory = tempfile.TemporaryDirectory().name
        os.makedirs(tempDirectory)
        cache = Cache.Cache(tempDirectory)
        cache.store("test", 1337, inMemory=False)
        self.assertEqual(cache.read("test"), 1337)

    def test_store_iMfalse_and_read_iMfalse(self):

        tempDirectory = tempfile.TemporaryDirectory().name
        os.makedirs(tempDirectory)
        cache = Cache.Cache(tempDirectory)
        cache.store("test", 1337, inMemory=False)
        self.assertEqual(cache.read("test", inMemory=False), 1337)

    def test_store_iMtrue_and_read_iMfalse(self):

        tempDirectory = tempfile.TemporaryDirectory().name
        os.makedirs(tempDirectory)
        cache = Cache.Cache(tempDirectory)
        cache.store("test", 1337)
        self.assertEqual(cache.read("test", inMemory=False), 1337)

    def test_store_read_transient(self):

        tempDirectory = tempfile.TemporaryDirectory().name
        os.makedirs(tempDirectory)
        cache = Cache.Cache(tempDirectory)
        cache.store("test", 1337, transient=True, inMemory=False)
        self.assertEqual(cache.read("test", inMemory=False), None)


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.ERROR)
    suite = unittest.TestLoader().loadTestsFromTestCase(Tests)
    unittest.TextTestRunner(verbosity=2).run(suite)


########NEW FILE########
__FILENAME__ = config
#!/usr/bin/env python3

import sys, os, unittest, logging, tempfile

# Extend PYTHONPATH with local 'lib' folder
if __name__ == "__main__":
    jasyroot = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]), os.pardir, os.pardir, os.pardir))
    sys.path.insert(0, jasyroot)
    print("Running from %s..." % jasyroot)

import jasy.core.Config as Config

class Tests(unittest.TestCase):

    def test_write_json(self):

        tempDirectory = tempfile.TemporaryDirectory().name
        os.makedirs(tempDirectory)

        Config.writeConfig([{"one": 1,"two": 2},{"three": 3,"four": 4}], os.path.join(tempDirectory, "test.json"))
        
        self.assertEqual(Config.findConfig(os.path.join(tempDirectory, "test.json")), os.path.join(tempDirectory, "test.json"))        
       
       
    def test_write_and_read_json(self):

        tempDirectory = tempfile.TemporaryDirectory().name
        os.makedirs(tempDirectory)

        Config.writeConfig([{"one": 10-9,"two": 5-3},{"three": 1+1+1,"four": 2*2}], os.path.join(tempDirectory, "test.json"))
        data = Config.loadConfig(os.path.join(tempDirectory, "test.json"))

        self.assertEqual(data, [{'two': 2, 'one': 1}, {'four': 4, 'three': 3}])        
       

    def test_write_yaml(self):

        tempDirectory = tempfile.TemporaryDirectory().name
        os.makedirs(tempDirectory)

        Config.writeConfig([{"one": 1,"two": 2},{"three": 3,"four": 4}], os.path.join(tempDirectory, "test.yaml"))
        
        self.assertEqual(Config.findConfig(os.path.join(tempDirectory, "test.yaml")), os.path.join(tempDirectory, "test.yaml"))        
    

    def test_write_and_read_json(self):

        tempDirectory = tempfile.TemporaryDirectory().name
        os.makedirs(tempDirectory)

        Config.writeConfig([{"one": 10-9,"two": 5-3},{"three": 1+1+1,"four": 2*2}], os.path.join(tempDirectory, "test.yaml"))
        data = Config.loadConfig(os.path.join(tempDirectory, "test.yaml"))

        self.assertEqual(data, [{'two': 2, 'one': 1}, {'four': 4, 'three': 3}]) 


    def test_matching_types(self):

        self.assertTrue(Config.matchesType(42, "int"))
        self.assertTrue(Config.matchesType(11.0, "float"))
        self.assertTrue(Config.matchesType(11.1, "float"))
        self.assertTrue(Config.matchesType("hello", "string"))
        self.assertTrue(Config.matchesType(False, "bool"))
        self.assertTrue(Config.matchesType([{"one": 10-9,"two": 5-3},{"three": 1+1+1,"four": 2*2}], "list"))
        self.assertTrue(Config.matchesType({"one": 10-9,"two": 5-3}, "dict"))
    

    def test_config_object_hasdata(self):

        config = Config.Config({'two': 2, 'one': 1, 'ten': 10})
        self.assertTrue(config.has('two'))


    def test_config_object_getdata(self):

        config = Config.Config({'two': 2, 'one': 1, 'ten': 10})
        self.assertEqual(config.get('ten'), 10)


    def test_config_object_setdata(self):

        config = Config.Config({'two': 2, 'one': 1, 'ten': 10})
        config.set('ten', 15)
        self.assertEqual(config.get('ten'), 15)


    def test_config_object_getdata_withdot(self):

        config = Config.Config({'foo': {'yeah': 42}, 'one': 1})
        self.assertEqual(config.get('foo.yeah'), 42)


    def test_config_object_setdata_withdot(self):

        config = Config.Config({'foo': {'yeah': 42}, 'one': 1})
        config.set('foo.yeah', 1337)
        self.assertEqual(config.get('foo')['yeah'], 1337)


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.ERROR)
    suite = unittest.TestLoader().loadTestsFromTestCase(Tests)
    unittest.TextTestRunner(verbosity=2).run(suite)


########NEW FILE########
__FILENAME__ = giturl
#!/usr/bin/env python3

import sys, os, unittest, logging

# Extend PYTHONPATH with local 'lib' folder
jasyroot = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]), os.pardir, os.pardir, os.pardir))
sys.path.insert(0, jasyroot)

import jasy.vcs.Repository as Repository


class Tests(unittest.TestCase):

    def test_git_urls(self):
        
        self.assertEqual(Repository.isUrl("foo"), False)
        self.assertEqual(Repository.isUrl("../bar"), False)
        self.assertEqual(Repository.isUrl("https://faz.net?x=1"), False)
        self.assertEqual(Repository.isUrl("git@github.com:zynga/apibrowser.git"), True)
        self.assertEqual(Repository.isUrl("https://github.com/zynga/core"), False)
        self.assertEqual(Repository.isUrl("git+https://github.com/zynga/core"), True)
        self.assertEqual(Repository.isUrl("https://github.com/zynga/core.git"), True)
        self.assertEqual(Repository.isUrl("git+https://github.com/zynga/core.git"), True)
        self.assertEqual(Repository.isUrl("https://wpbasti@github.com/zynga/apibrowser.git"), True)
        self.assertEqual(Repository.isUrl("git://github.com/zynga/core.git"), True)
        self.assertEqual(Repository.isUrl("git://gitorious.org/qt/qtdeclarative.git"), True)
        self.assertEqual(Repository.isUrl("git+git://gitorious.org/qt/qtdeclarative.git"), True)
        self.assertEqual(Repository.isUrl("https://git.gitorious.org/qt/qtdeclarative.git"), True)
    


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.ERROR)
    suite = unittest.TestLoader().loadTestsFromTestCase(Tests)
    unittest.TextTestRunner(verbosity=2).run(suite)

########NEW FILE########
__FILENAME__ = api
#!/usr/bin/env python3

import sys, os, unittest, logging

# Extend PYTHONPATH with local 'lib' folder
if __name__ == "__main__":
    jasyroot = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]), os.pardir, os.pardir, os.pardir, os.pardir))
    sys.path.insert(0, jasyroot)
    print("Running from %s..." % jasyroot)

import jasy.js.parse.Parser as Parser
import jasy.js.parse.ScopeScanner as ScopeScanner
import jasy.js.api.Data as Data


class Tests(unittest.TestCase):

    def process(self, code):
        node = Parser.parse(code)
        ScopeScanner.scan(node)
        data = Data.ApiData("test")
        data.scanTree(node)
        
        return data
        
    
    def test_unsupported(self):
        
        data = self.process("""
        
        x;
        
        """)
        
        self.assertIsInstance(data, Data.ApiData)
        self.assertEqual(data.main["type"], "Unsupported")
        self.assertEqual(data.main["line"], 1)
        
    
    def test_uses(self):
        
        data = self.process("""

        core.Class("foo.Bar", {
        
            main: function() {
                
                document.body.appendChild(new Image());
            
            }
        
        });

        """)

        self.assertIsInstance(data, Data.ApiData)
        
        self.assertIn("Image", data.uses)
        self.assertIn("document", data.uses)
        self.assertIn("document.body.appendChild", data.uses)
        self.assertIn("core", data.uses)
        self.assertIn("core.Class", data.uses)
        
        
    def test_core_module(self):

        data = self.process("""

        core.Module("foo.Bar", {});

        """)

        self.assertIsInstance(data, Data.ApiData)
        self.assertEqual(data.main["type"], "core.Module")
        
        
        
    def test_params(self):

        data = self.process("""

        core.Module("foo.Bar", {
        
          /** Returns sum of @first {Integer} and @second {Integer} and multiplies with @varargs {Integer...} */
          method: function(first, second, varargs) {
            
          }
        
        });

        """)

        self.assertIsInstance(data, Data.ApiData)
        self.assertEqual(data.main["type"], "core.Module")
        self.assertEqual(data.statics["method"]["params"]["first"]["type"][0]["name"], "Integer")
        self.assertEqual(data.statics["method"]["params"]["second"]["type"][0]["name"], "Integer")
        self.assertEqual(data.statics["method"]["params"]["varargs"]["type"][0]["name"], "Integer")
        self.assertEqual(data.statics["method"]["params"]["first"]["position"], 0)
        self.assertEqual(data.statics["method"]["params"]["second"]["position"], 1)
        self.assertEqual(data.statics["method"]["params"]["varargs"]["position"], 2)
        self.assertNotIn("optional", data.statics["method"]["params"]["varargs"])
        self.assertTrue(data.statics["method"]["params"]["varargs"]["dynamic"])
        
        
        
    def test_params_optional(self):

        data = self.process("""

        core.Module("foo.Bar", {

          /** Returns sum of @first {Integer} and @second {Integer} and multiplies with @varargs {Integer...?} */
          method: function(first, second, varargs) {

          }

        });

        """)

        self.assertIsInstance(data, Data.ApiData)
        self.assertEqual(data.main["type"], "core.Module")
        self.assertEqual(data.statics["method"]["params"]["first"]["type"][0]["name"], "Integer")
        self.assertEqual(data.statics["method"]["params"]["second"]["type"][0]["name"], "Integer")
        self.assertEqual(data.statics["method"]["params"]["varargs"]["type"][0]["name"], "Integer")
        self.assertTrue(data.statics["method"]["params"]["varargs"]["optional"])
        self.assertTrue(data.statics["method"]["params"]["varargs"]["dynamic"])
        
        
        
    def test_core_class(self):

        data = self.process("""

        core.Class("foo.Bar", {});

        """)

        self.assertIsInstance(data, Data.ApiData)
        self.assertEqual(data.main["type"], "core.Class")
        
        
        
    def test_construct(self):

        data = self.process("""

        core.Class("foo.Bar", {
        
            /**
             * Creates an instance of foo.Bar using the @config {Map} data given 
             */
            construct: function(config) {
            
            }
        
        });

        """)

        self.assertIsInstance(data, Data.ApiData)
        self.assertIsInstance(data.construct, dict)
        self.assertIsInstance(data.construct["params"], dict)
        self.assertIsInstance(data.construct["params"]["config"], dict)
        self.assertEqual(data.construct["params"]["config"]["type"][0]["name"], "Map")
        
        
        
    def test_properties(self):

        data = self.process("""

        core.Class("foo.Bar", {

            properties: {
            
                width: {
                    type: "Number",
                    init: 100,
                    fire: "changeWidth",
                    apply: function() {
                        this.scheduleForRendering("size");
                    }
                },

                height: {
                    type: "Number",
                    init: 200,
                    fire: "changeHeight",
                    apply: function() {
                        this.scheduleForRendering("size");
                    }
                },
                
                enabled: {
                    type: "Boolean",
                    init: true,
                    nullable: false
                },
                
                color: {
                    type: "Color",
                    nullable: true,
                    apply: function(value) {
                        this.__domElement.style.color = value;
                    }
                }
            
            }

        });

        """)

        self.assertIsInstance(data, Data.ApiData)
        self.assertIsInstance(data.properties, dict)
        self.assertIsInstance(data.properties["width"], dict)
        self.assertIsInstance(data.properties["height"], dict)
        self.assertIsInstance(data.properties["enabled"], dict)
        self.assertEqual(data.properties["width"]["init"], "100")
        self.assertEqual(data.properties["height"]["init"], "200")
        self.assertEqual(data.properties["enabled"]["init"], "true")
        self.assertNotIn("init", data.properties["color"])
        self.assertEqual(data.properties["width"]["fire"], "changeWidth")
        self.assertEqual(data.properties["height"]["fire"], "changeHeight")
        self.assertEqual(data.properties["width"]["nullable"], False)
        self.assertEqual(data.properties["height"]["nullable"], False)
        self.assertEqual(data.properties["enabled"]["nullable"], False)
        self.assertEqual(data.properties["color"]["nullable"], True)
        self.assertEqual(data.properties["width"]["apply"], True)
        self.assertEqual(data.properties["height"]["apply"], True)
        self.assertEqual(data.properties["color"]["apply"], True)
        
        
    def test_properties_nullable(self):

        data = self.process("""

        core.Class("foo.Bar", {

            properties: {

                nullable: {
                    nullable: true
                },
                
                not: {
                    nullable: false
                },
                
                init: {
                    init: 3
                },
                
                nullInit: {
                    init: null
                },
                
                nothing: {
                    
                }

            }

        });

        """) 
        
        self.assertEqual(data.properties["nullable"]["nullable"], True)
        self.assertEqual(data.properties["not"]["nullable"], False)
        self.assertEqual(data.properties["init"]["nullable"], False)
        self.assertEqual(data.properties["nullInit"]["nullable"], True)
        self.assertEqual(data.properties["nothing"]["nullable"], True)
        
        
        
    def test_properties_groups(self):

        data = self.process("""

        core.Class("foo.Bar", {

            properties: {

                size: {
                    group: ["width", "height"]
                },

                padding: {
                    group: ["paddingTop", "paddingRight", "paddingBottom", "paddingLeft"],
                    shorthand: true
                }
                
            }

        });

        """) 

        self.assertEqual(data.properties["size"]["group"], ["width", "height"])
        self.assertNotIn("shorthand", data.properties["size"])
        self.assertEqual(data.properties["padding"]["group"], ["paddingTop", "paddingRight", "paddingBottom", "paddingLeft"])
        self.assertTrue(data.properties["padding"]["shorthand"])
        
        

    def test_properties_init(self):

        data = self.process("""

        core.Class("foo.Bar", {

            properties: {

                str: {
                    init: "hello"
                },
                
                bool: {
                    init: true
                },
                
                num: {
                    init: 3.14
                },
                
                reg: {
                    init: /[a-z]/
                },
                
                date: {
                    init: new Date
                },
                
                timestamp: {
                    init: +new Date
                },
                
                arr: {
                    init: [1,2,3]
                },
                
                map: {
                    init: {}
                },
                
                nully: {
                    init: null
                },
                
                add: {
                    init: 3+4
                },
                
                ref: {
                    init: my.custom.Formatter
                }

            }

        });

        """) 

        self.assertEqual(data.properties["str"]["init"], '"hello"')
        self.assertEqual(data.properties["bool"]["init"], "true")
        self.assertEqual(data.properties["num"]["init"], "3.14")
        self.assertEqual(data.properties["reg"]["init"], "/[a-z]/")
        self.assertEqual(data.properties["date"]["init"], "Date")
        self.assertEqual(data.properties["timestamp"]["init"], "Number")
        self.assertEqual(data.properties["arr"]["init"], "Array")
        self.assertEqual(data.properties["map"]["init"], "Map")
        self.assertEqual(data.properties["nully"]["init"], "null")
        self.assertEqual(data.properties["add"]["init"], "Number")
        self.assertEqual(data.properties["ref"]["init"], "my.custom.Formatter")
        
        
        
    def test_properties_multi(self):

        data = self.process("""

        core.Class("foo.Bar", {

            properties: {

                color: {
                    inheritable: true,
                    themeable: true
                },

                spacing: {
                    themeable: true
                },

                cursor: {
                    inheritable: true
                }

            }

        });

        """) 

        self.assertEqual(data.properties["color"]["inheritable"], True)
        self.assertEqual(data.properties["color"]["themeable"], True)
        self.assertNotIn("inheritable", data.properties["spacing"])
        self.assertEqual(data.properties["spacing"]["themeable"], True)
        self.assertEqual(data.properties["cursor"]["inheritable"], True)
        self.assertNotIn("themeable", data.properties["cursor"])
        
        
        
    def test_include(self):

        data = self.process("""

        core.Class("foo.Bar", {
          include: [foo.MEvents, foo.MColor]

        });

        """) 

        self.assertEqual(data.includes, ["foo.MEvents", "foo.MColor"])
        
        
    def test_implement(self):

        data = self.process("""

        core.Class("foo.Bar", {
          implement: [foo.ILayoutObject, foo.IThemeable]

        });

        """) 

        self.assertEqual(data.implements, ["foo.ILayoutObject", "foo.IThemeable"])        
        
        
        
    def test_primitives(self):
        
        data = self.process("""
        
        core.Class("foo.Bar", 
        {
          members: {
            pi: 3.14,
            str: "hello world",
            bool: true
          }
        });
        
        """)
        
        self.assertIsInstance(data.members, dict)
        self.assertIn("pi", data.members)
        self.assertIn("str", data.members)
        self.assertIn("bool", data.members)
        self.assertEqual(data.members["pi"]["type"], "Number")
        self.assertEqual(data.members["str"]["type"], "String")
        self.assertEqual(data.members["bool"]["type"], "Boolean")
        
        
    def test_values(self):

        data = self.process("""

        core.Class("foo.Bar", 
        {
          members: {
            str: "hello",
            bool: true,
            num: 3.14,
            reg: /[a-z]/,
            date: new Date,
            timestamp: +new Date,
            arr: [1,2,3],
            map: {},
            nully: null,
            add: 3+4,
            ref: my.custom.Formatter,
            func: function() {}
          }
        });

        """)

        self.assertIsInstance(data.members, dict)
        self.assertEqual(data.members["str"]["value"], '"hello"')
        self.assertEqual(data.members["bool"]["value"], "true")
        self.assertEqual(data.members["num"]["value"], "3.14")
        self.assertEqual(data.members["reg"]["value"], "/[a-z]/")
        
        # Type has enough information in these cases
        self.assertNotIn("value", data.members["date"])
        self.assertNotIn("value", data.members["timestamp"])
        self.assertNotIn("value", data.members["arr"])
        self.assertNotIn("value", data.members["map"])
        self.assertNotIn("value", data.members["nully"])
        self.assertNotIn("value", data.members["add"])
        self.assertNotIn("value", data.members["ref"])
        self.assertNotIn("value", data.members["func"])
        
        
        
    def test_kinds(self):

        data = self.process("""

        core.Class("foo.Bar", 
        {
          members: {
            PI: 3.14,
            LONGER_CONST: "def",
            functionName: function() {},
            variable: "hello",
          }
        });

        """)

        self.assertIsInstance(data.members, dict)
        self.assertTrue(data.members["PI"]["constant"])
        self.assertTrue(data.members["LONGER_CONST"]["constant"])
        self.assertNotIn("constant", data.members["functionName"])
        self.assertNotIn("constant", data.members["variable"])
    
    
    def test_lines(self):

        data = self.process("""

        /**
         * Class comment
         */
        core.Class("foo.Bar", {

            members: {

                method1: function() {

                }

            }

        });
        """)

        self.assertIsInstance(data, Data.ApiData)

        self.assertEqual(data.main["line"], 6)
        self.assertEqual(data.members["method1"]["line"], 10)


    def test_visibility(self):

        data = self.process("""

        core.Class("foo.Bar", {

            members: {

                publicFunction: function() {

                },

                _internalFunction: function() {

                },

                __privateFunction: function() {

                }

            }

        });

        """)

        self.assertIsInstance(data, Data.ApiData)

        self.assertEqual(data.members["publicFunction"]["visibility"], "public")
        self.assertEqual(data.members["_internalFunction"]["visibility"], "internal")
        self.assertEqual(data.members["__privateFunction"]["visibility"], "private")        
        
        
    def test_custom_type(self):

        data = self.process("""

        core.Class("foo.Bar", 
        {
          members: {
            /** {=Color} */
            background: "#fff",
          }
        });

        """)

        self.assertIsInstance(data.members, dict)
        self.assertIn("background", data.members)
        self.assertEqual(data.members["background"]["type"], "Color")
        
        
    def test_function(self):
        
        data = self.process("""

        core.Class("foo.Bar", 
        {
          members: {
            /**
             * {Number} Computes the sum of @a {Number} and @b {Number}
             */
            func: function(a, b) {
                return a+b;
            }
          }
        });

        """)

        self.assertIsInstance(data.members, dict)
        self.assertIn("func", data.members)
        self.assertEqual(data.members["func"]["type"], "Function")
        self.assertIsInstance(data.members["func"]["params"], dict)
        self.assertIsInstance(data.members["func"]["params"]["a"], dict)
        self.assertIsInstance(data.members["func"]["params"]["b"], dict)
        self.assertEqual(data.members["func"]["params"]["a"]["type"][0]["name"], "Number")
        self.assertEqual(data.members["func"]["params"]["b"]["type"][0]["name"], "Number")
        self.assertEqual(data.members["func"]["params"]["a"]["type"][0]["builtin"], True)
        self.assertEqual(data.members["func"]["params"]["b"]["type"][0]["builtin"], True)
        self.assertEqual(data.members["func"]["returns"][0]["name"], "Number")
        
        
    def test_function_return_number(self):

        data = self.process("""

        core.Class("foo.Bar", 
        {
          members: {
            answer: function() {
                return 42;
            }
          }
        });

        """)

        self.assertIsInstance(data.members, dict)
        self.assertIn("answer", data.members)
        self.assertEqual(data.members["answer"]["type"], "Function")
        self.assertEqual(data.members["answer"]["returns"][0]["name"], "Number")
        
    
    def test_function_return_string(self):

        data = self.process("""

        core.Class("foo.Bar", 
        {
          members: {
            answer: function() {
                return "hello";
            }
          }
        });

        """)

        self.assertIsInstance(data.members, dict)
        self.assertIn("answer", data.members)
        self.assertEqual(data.members["answer"]["type"], "Function")
        self.assertEqual(data.members["answer"]["returns"][0]["name"], "String")
        
        
    def test_function_return_plus_string(self):

        data = self.process("""

        core.Class("foo.Bar", 
        {
          members: {
            answer: function() {
                return "hello" + "world";
            }
          }
        });

        """)

        self.assertIsInstance(data.members, dict)
        self.assertIn("answer", data.members)
        self.assertEqual(data.members["answer"]["type"], "Function")
        self.assertEqual(data.members["answer"]["returns"][0]["name"], "String")
        
        
    def test_function_return_plus_x(self):

        data = self.process("""

        core.Class("foo.Bar", 
        {
          members: {
            answer: function(x) {
                return x + x;
            }
          }
        });

        """)

        self.assertIsInstance(data.members, dict)
        self.assertIn("answer", data.members)
        self.assertEqual(data.members["answer"]["type"], "Function")
        self.assertEqual(data.members["answer"]["returns"][0]["name"], "var")        
        
        
    def test_function_return_dotted(self):

        data = self.process("""

        core.Class("foo.Bar", 
        {
          members: {
            answer: function() {
                return window.innerWidth;
            }
          }
        });

        """)

        self.assertIsInstance(data.members, dict)
        self.assertIn("answer", data.members)
        self.assertEqual(data.members["answer"]["type"], "Function")
        self.assertEqual(data.members["answer"]["returns"][0]["name"], "var")
        
        
    def test_literal(self):
        
        data = self.process("""
        
        core.Class("foo.Bar", 
        {
          members: {
            map: {foo:1,bar:2},
            array: [1,2,3],
            reg: /[a-z]/g
          }
        });
        
        """)
        
        self.assertIsInstance(data.members, dict)
        self.assertEqual(data.members["map"]["type"], "Map")
        self.assertEqual(data.members["array"]["type"], "Array")
        self.assertEqual(data.members["reg"]["type"], "RegExp")
        
        
    def test_number(self):
        
        data = self.process("""

        core.Class("foo.Bar", 
        {
          members: {
            bitwise: 1 ^ 2,
            shif: 4 >> 3,
            mod: 15 / 4,
            unary: -3,
            increment: i++
          }
        });

        """)        
        
        self.assertIsInstance(data.members, dict)
        self.assertEqual(data.members["bitwise"]["type"], "Number")
        self.assertEqual(data.members["shif"]["type"], "Number")
        self.assertEqual(data.members["mod"]["type"], "Number")
        self.assertEqual(data.members["unary"]["type"], "Number")
        self.assertEqual(data.members["increment"]["type"], "Number")
        
        
    def test_boolean(self):

        data = self.process("""

        core.Class("foo.Bar", 
        {
          members: {
            trueish: 2 == 2,
            falsy: 4 != 4,
            and: window.location && window.document,
            or: document.createElement || document.createDocumentFragment,
            not: !!document.createElement,
            bigger: 3 > 5,
            is: foo instanceof bar
          }
        });

        """)        
        
        self.assertIsInstance(data.members, dict)
        self.assertEqual(data.members["trueish"]["type"], "Boolean")
        self.assertEqual(data.members["falsy"]["type"], "Boolean")
        self.assertEqual(data.members["and"]["type"], "Boolean")
        self.assertEqual(data.members["or"]["type"], "Boolean")
        self.assertEqual(data.members["not"]["type"], "Boolean")
        self.assertEqual(data.members["bigger"]["type"], "Boolean")
        self.assertEqual(data.members["is"]["type"], "Boolean")
        
        
    def test_specials(self):

        data = self.process("""

        core.Class("foo.Bar", 
        {
          members: {
            plus: 3 + 4,
            plusstr: 3 + "world",
            plusstr2: 3 + "world" + 4,
            now: +new Date,
            custom: new Global,
            formatter: new foo.DateFormatter,
            date: new Date,
            number: new Number(3),
            voi: void 3,
            nul: null,
            type: typeof 3,
            del: delete obj.x,
            id: someidentifier
          }
        });

        """)        

        self.assertIsInstance(data.members, dict)
        self.assertEqual(data.members["plus"]["type"], "Number")
        self.assertEqual(data.members["plusstr"]["type"], "String")
        self.assertEqual(data.members["plusstr2"]["type"], "String")
        self.assertEqual(data.members["now"]["type"], "Number")
        self.assertEqual(data.members["custom"]["type"], "Object")
        self.assertEqual(data.members["formatter"]["type"], "foo.DateFormatter"),
        self.assertEqual(data.members["date"]["type"], "Date"),
        self.assertEqual(data.members["number"]["type"], "Number")
        self.assertEqual(data.members["voi"]["type"], "undefined")
        self.assertEqual(data.members["nul"]["type"], "null")
        self.assertEqual(data.members["type"]["type"], "String")
        self.assertEqual(data.members["del"]["type"], "Boolean")
        self.assertEqual(data.members["id"]["type"], "Identifier")
        
        
    def test_dynamic(self):
        
        data = self.process("""

        core.Class("foo.Bar", 
        {
          members: {

            func: (function() {
     
              /**
               * Returns the sum of @a {Integer} and @b {Integer}
               */
              return function(a, b) {
                return a+b;
              };
    
            })(),
            
            string: (function() {

              /** {=String} Private data */
              return "private";

            })(),
        
            map: (function() {
            
              /** {=Map} A map with `x` and `y`. */
              return {
                foo: 1, 
                bar: 2
              };
            
            })(),

            hook: isSomething() ? 
              /** A function for doing things with @a {voodoo.Hoo} */
              function(a) {} : 
              function(a) {}
        
          }
          
        });

        """)
        
        self.assertIsInstance(data.members, dict)
        
        self.assertEqual(data.members["func"]["type"], "Function")
        self.assertIsInstance(data.members["func"]["params"], dict)
        self.assertEqual(data.members["func"]["params"]["a"]["type"][0]["name"], "Integer")
        self.assertEqual(data.members["func"]["params"]["b"]["type"][0]["name"], "Integer")
        
        self.assertEqual(data.members["string"]["type"], "String")
        self.assertEqual(data.members["map"]["type"], "Map")
        
        self.assertEqual(data.members["hook"]["type"], "Function")
        self.assertIsInstance(data.members["hook"]["params"], dict)
        self.assertEqual(data.members["hook"]["params"]["a"]["type"][0]["name"], "voodoo.Hoo")
        
        
    def test_dynamic_cascaded(self):
        
        data = self.process("""

        core.Class("foo.Bar", {
        
          members: {

            func: (function() {

              var ret = function(c) {
              
                /**
                 * Returns the sum of @a {Integer} and @b {Integer}
                 */
                return function(a, b) {
                  return a+b+c;
                };
              
              }
              
              return ret(3);
    
            })()

          }
          
        });

        """)
        
        self.assertIsInstance(data.members, dict)
        
        self.assertEqual(data.members["func"]["type"], "Function")
        self.assertIsInstance(data.members["func"]["params"], dict)
        self.assertEqual(data.members["func"]["params"]["a"]["type"][0]["name"], "Integer")
        self.assertEqual(data.members["func"]["params"]["b"]["type"][0]["name"], "Integer")
        
        
    def test_dynamic_auto(self):

        data = self.process("""

        core.Class("foo.Bar", 
        {
          members: {

            func: (function() {

              return function(a, b) {
                return a+b;
              };

            })(),

            string: (function() {

              return "private";

            })(),

            map: (function() {

              return {
                foo: 1, 
                bar: 2
              };

            })(),

            hook: isSomething() ? function(a) {} : function(a) {},
            
            hookNull: isEmpty() ? null : function(a) {},
            
            hookMissingType: doTest() ? /** Width to apply */ 14 : 16,
            
            hookCascade: first ? second ? 1 : 2 : 3,

            hookCascadeDeep: first ? second ? 1 : 2 : third ? 3 : 4

          }

        });

        """)

        self.assertIsInstance(data.members, dict)

        self.assertEqual(data.members["func"]["type"], "Function")
        self.assertIsInstance(data.members["func"]["params"], dict)
        self.assertIsInstance(data.members["func"]["params"]["a"], dict)
        self.assertIsInstance(data.members["func"]["params"]["b"], dict)

        self.assertEqual(data.members["string"]["type"], "String")
        self.assertEqual(data.members["map"]["type"], "Map")

        self.assertEqual(data.members["hook"]["type"], "Function")
        self.assertIsInstance(data.members["hook"]["params"], dict)
        self.assertIsInstance(data.members["hook"]["params"]["a"], dict)        

        self.assertEqual(data.members["hookNull"]["type"], "Function")
        self.assertIsInstance(data.members["hookNull"]["params"], dict)
        self.assertIsInstance(data.members["hookNull"]["params"]["a"], dict)        

        self.assertEqual(data.members["hookMissingType"]["type"], "Number")
        self.assertEqual(data.members["hookMissingType"]["doc"], "<p>Width to apply</p>\n")

        self.assertEqual(data.members["hookCascade"]["type"], "Number")
        self.assertEqual(data.members["hookCascadeDeep"]["type"], "Number")
        
        
    def test_closure(self):

        data = self.process("""

        /** Returns the sum of @a {Integer} and @b {Integer} */
        var method = function(a, b) {
          return a+b;
        };

        core.Class("foo.Bar", {

          members: {

            func: method

          }

        });

        """)

        self.assertIsInstance(data.members, dict)

        self.assertEqual(data.members["func"]["type"], "Function")
        self.assertIsInstance(data.members["func"]["params"], dict)
        self.assertEqual(data.members["func"]["params"]["a"]["type"][0]["name"], "Integer")
        self.assertEqual(data.members["func"]["params"]["b"]["type"][0]["name"], "Integer")


    def test_closure_namedfunc(self):

        data = self.process("""

        /** Returns the sum of @a {Integer} and @b {Integer} */
        function method(a, b) {
          return a+b;
        };

        core.Class("foo.Bar", {

          members: {

            func: method

          }

        });

        """)

        self.assertIsInstance(data.members, dict)

        self.assertEqual(data.members["func"]["type"], "Function")
        self.assertIsInstance(data.members["func"]["params"], dict)
        self.assertEqual(data.members["func"]["params"]["a"]["type"][0]["name"], "Integer")
        self.assertEqual(data.members["func"]["params"]["b"]["type"][0]["name"], "Integer")
        
        
    def test_closure_static(self):

        data = self.process("""

        var pi = 3.14;

        core.Class("foo.Bar", {

          members: {

            stat: pi

          }

        });

        """)

        self.assertIsInstance(data.members, dict)

        self.assertEqual(data.members["stat"]["type"], "Number")
        
        
    def test_closure_static_sum(self):

        data = self.process("""

        var sum = "hello" + 1.23;

        core.Class("foo.Bar", {

          members: {

            stat: sum

          }

        });

        """)

        self.assertIsInstance(data.members, dict)

        self.assertEqual(data.members["stat"]["type"], "String")            
        
        
    def test_closure_static_later(self):

        data = self.process("""

        var pi;
        
        pi = 3.14;

        core.Class("foo.Bar", {

          members: {

            stat: pi

          }

        });

        """)

        self.assertIsInstance(data.members, dict)

        self.assertEqual(data.members["stat"]["type"], "Number")
        
        
    def test_closure_static_hoisting(self):

        data = self.process("""

        pi = 3.14;

        core.Class("foo.Bar", {

          members: {

            stat: pi

          }

        });

        var pi;


        """)

        self.assertIsInstance(data.members, dict)

        self.assertEqual(data.members["stat"]["type"], "Number")                
        
        
    def test_closure_static_doc(self):

        data = self.process("""

        /** {=Color} Bright */
        var white = "#fff";

        core.Class("foo.Bar", {

          members: {

            stat: white

          }

        });

        """)

        self.assertIsInstance(data.members, dict)

        self.assertEqual(data.members["stat"]["type"], "Color")            
        
        
    def test_closure_if_else(self):

        data = self.process("""

        if (browser.isCool()) {
          /** Returns the sum of @a {Integer} and @b {Integer} */
          var method = function(a, b) {
            return Math.sum(a, b);
          };
        } else {
          var method = function(a, b) {
            return a+b;
          };
        }

        core.Class("foo.Bar", {

          members: {

            func: method

          }

        });

        """)

        self.assertIsInstance(data.members, dict)

        self.assertEqual(data.members["func"]["type"], "Function")
        self.assertIsInstance(data.members["func"]["params"], dict)
        self.assertEqual(data.members["func"]["params"]["a"]["type"][0]["name"], "Integer")
        self.assertEqual(data.members["func"]["params"]["b"]["type"][0]["name"], "Integer")
        
        
    def test_closure_hook(self):

        data = self.process("""
        
        /**
         * Requests the given @url {String} from the server
         */
        var corsRequest = function(url) {
          
        };
        
        var xhrRequest = function(url) {
        
        };

        var hook = browser.isCool() ? corsRequest : xhrRequest;

        core.Class("foo.Bar", {

          members: {

            func: hook

          }

        });

        """)

        self.assertIsInstance(data.members, dict)

        self.assertEqual(data.members["func"]["type"], "Function")
        self.assertIsInstance(data.members["func"]["params"], dict)
        self.assertEqual(data.members["func"]["params"]["url"]["type"][0]["name"], "String")
        
        
    def test_closure_call(self):

        data = self.process("""

        var variant = function() {
        
          /**
           * Requests the given @url {String} from the server
           */
          var corsRequest = function(url) {
          };

          var xhrRequest = function(url) {
          };            
            
          return browser.isCool() ? corsRequest : xhrRequest;
        
        };

        core.Class("foo.Bar", {

          members: {

            func: variant()

          }

        });

        """)

        self.assertIsInstance(data.members, dict)

        self.assertEqual(data.members["func"]["type"], "Function")
        self.assertIsInstance(data.members["func"]["params"], dict)
        self.assertEqual(data.members["func"]["params"]["url"]["type"][0]["name"], "String")
        
    
    def test_closure_call_alter(self):

        data = self.process("""

        var variant = (function() {

          /**
           * Requests the given @url {String} from the server
           */
          var corsRequest = function(url) {
          };

          var xhrRequest = function(url) {
          };            

          return browser.isCool() ? corsRequest : xhrRequest;

        })();

        core.Class("foo.Bar", {

          members: {

            func: variant

          }

        });

        """)

        self.assertIsInstance(data.members, dict)

        self.assertEqual(data.members["func"]["type"], "Function")
        self.assertIsInstance(data.members["func"]["params"], dict)
        self.assertEqual(data.members["func"]["params"]["url"]["type"][0]["name"], "String")


    def test_reference(self):

        data = self.process("""

        core.Class("foo.Bar", {

          members: {

            func: foo.bar.baz.Boo,
            inst: new foo.bar.baz.Boo

          }

        });

        """)

        self.assertIsInstance(data.members, dict)

        self.assertEqual(data.members["func"]["type"], "foo.bar.baz.Boo")
        self.assertEqual(data.members["inst"]["type"], "foo.bar.baz.Boo")
        
        
        
    def test_events(self):

        data = self.process("""

        core.Class("foo.Bar", {

          events: {

            click: core.event.type.Mouse,
            keypress: core.event.type.Key

          }

        });

        """)

        self.assertIsInstance(data.events, dict)

        self.assertEqual(data.events["click"]["type"], "core.event.type.Mouse")
        self.assertEqual(data.events["keypress"]["type"], "core.event.type.Key")
        
    
    def test_events_reference(self):

        data = self.process("""

        var mouseEvent = core.event.type.Mouse;
        var keyEvent = core.event.type.Key;

        core.Class("foo.Bar", {

          events: {

            click: mouseEvent,
            keypress: keyEvent

          }

        });

        """)

        self.assertIsInstance(data.events, dict)

        self.assertEqual(data.events["click"]["type"], "core.event.type.Mouse")
        self.assertEqual(data.events["keypress"]["type"], "core.event.type.Key")        
        
        

    def test_events_doc(self):

        data = self.process("""
        
        var mouseEvent = core.event.type.Mouse;
        var keyEvent = core.event.type.Key;

        core.Class("foo.Bar", {

          events: {

            /** {=MouseEvent} Fired when the user clicks */
            click: mouseEvent,

            /** {=KeyEvent} Fired when the user presses a key */
            keypress: keyEvent

          }

        });

        """)

        self.assertIsInstance(data.events, dict)

        self.assertEqual(data.events["click"]["type"], "MouseEvent")
        self.assertEqual(data.events["keypress"]["type"], "KeyEvent")
        self.assertEqual(data.events["click"]["doc"], "<p>Fired when the user clicks</p>\n")
        self.assertEqual(data.events["keypress"]["doc"], "<p>Fired when the user presses a key</p>\n")
        
        
    def test_summary(self):

        data = self.process("""
        
        /** First sentence. Second sentence. */
        core.Class("foo.Bar", {

        });

        """)

        self.assertEqual(data.main["doc"], '<p>First sentence. Second sentence.</p>\n')
        self.assertEqual(data.main["summary"], 'First sentence.')
        
        
        
    def test_summary_nodot(self):

        data = self.process("""

        /** First sentence */
        core.Class("foo.Bar", {

        });

        """)

        self.assertEqual(data.main["doc"], '<p>First sentence</p>\n')
        self.assertEqual(data.main["summary"], 'First sentence.')        
        
        
        
    def test_tags(self):

        data = self.process("""

        var mouseEvent = core.event.type.Mouse;
        var keyEvent = core.event.type.Key;

        core.Class("foo.Bar", {

          members: {
          
            /** #final #public */
            setWidth: function(width) {

              // do stuff
            
              this._applyWidth(width);

            },
            
            _applyWidth: function() {
            
            }
          }

        });

        """)

        self.assertIn("final", data.members["setWidth"]["tags"])
        self.assertIn("public", data.members["setWidth"]["tags"])
        
        
        
    def test_interface(self):

        data = self.process("""

        var mouseEvent = core.event.type.Mouse;
        var keyEvent = core.event.type.Key;

        core.Interface("foo.LayoutObject", {

          events: {
          
            changeWidth: foo.PropertyEvent,
            changeHeight: foo.PropertyEvent

          },
          
          properties: {
          
            enabled: {
              type: "Boolean"
            }
          
          },

          members: {
          
            setWidth: function(width) {
              
            },
            
            getWidth: function() {
            
            },
            
            setHeight: function(height) {
            
            },
            
            getHeight: function() {
            
            }

          }

        });

        """)
        
        self.assertEqual(data.main["type"], "core.Interface")

        self.assertIn("getWidth", data.members)
        self.assertIn("getHeight", data.members)
        self.assertIn("setWidth", data.members)
        self.assertIn("setHeight", data.members)

        self.assertIn("width", data.members["setWidth"]["params"])
        self.assertIn("height", data.members["setHeight"]["params"])
    
        self.assertIn("changeWidth", data.events)
        self.assertIn("changeHeight", data.events)
        
        self.assertEqual(data.events["changeWidth"]["type"], "foo.PropertyEvent")
        self.assertEqual(data.events["changeHeight"]["type"], "foo.PropertyEvent")
    
        self.assertIn("enabled", data.properties)
        self.assertEqual(data.properties["enabled"]["type"], "Boolean")
    


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.ERROR)
    suite = unittest.TestLoader().loadTestsFromTestCase(Tests)
    unittest.TextTestRunner(verbosity=2).run(suite)        

    
########NEW FILE########
__FILENAME__ = blockreduce
#!/usr/bin/env python3

import sys, os, unittest, logging

# Extend PYTHONPATH with local 'lib' folder
if __name__ == "__main__":
    jasyroot = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]), os.pardir, os.pardir, os.pardir, os.pardir))
    sys.path.insert(0, jasyroot)
    print("Running from %s..." % jasyroot)

import jasy.js.parse.Parser as Parser
import jasy.js.parse.ScopeScanner as ScopeScanner
import jasy.js.output.Compressor as Compressor
import jasy.js.optimize.BlockReducer as BlockReducer



class Tests(unittest.TestCase):

    def process(self, code):
        node = Parser.parse(code)
        BlockReducer.optimize(node)
        return Compressor.Compressor().compress(node)

    def test_combine_mixed(self):
        self.assertEqual(self.process('var str = 4 + 3 + "x"'), 'var str="7x";')

    def test_combine_number(self):
        self.assertEqual(self.process('var adds = 4 * (5+6);'), 'var adds=44;')

    def test_combine_number_omit(self):
        self.assertEqual(self.process('var third = 1/3;'), 'var third=1/3;')

    def test_combine_string(self):
        self.assertEqual(self.process('var result = "first second third " + "fourth fivs sixs";'), 'var result="first second third fourth fivs sixs";')

    def test_combine_mixed_empty(self):
        self.assertEqual(self.process('4 + 3 + "x"'), '')

    def test_combine_inner_out(self):
        self.assertEqual(self.process('var s=x+"foo"+"bar"'), 'var s=x+"foobar";')

    def test_elseinline_return(self):
        self.assertEqual(self.process(
            '''
            function x()
            {
              if (something)
              {
                x++;
                while(warm) {}
                return x;
              }
              else
              {
                y++;
              }
            }
            '''),
            'function x(){if(something){x++;while(warm);return x}y++}'
        ) 
               

    def test_elseinline_throw(self):
        self.assertEqual(self.process(
            '''
            function x()
            {
              if (something)
              {
                x++;
                while(warm) {}
                throw new Error("Wrong data!");
              }
              else
              {
                y++;
              }
            }
            '''),
            'function x(){if(something){x++;while(warm);throw new Error("Wrong data!")}y++}'
        )
        
    
    def test_elseinline_elseif(self):
        self.assertEqual(self.process(
            '''
            function x()
            {
              if(something)
              {
                while(a);
                return 0;
              }
              else if(xxx)
              {
                while(b);
                return 1;
              }
              else
              {
                while(c);
                return 2;
              }
            }            
            '''),
            'function x(){if(something){while(a);return 0}if(xxx){while(b);return 1}while(c);return 2}'
        )
        
        
    def test_elseinline_elseif_nolast(self):
        self.assertEqual(self.process(
            '''
            function x()
            {
              if(something)
              {
                while(a);
                return 0;
              }
              else if(xxx)
              {
                while(b);
                return 1;
              }
              else
              {
                i++;
              }
            }            
            '''),
            'function x(){if(something){while(a);return 0}if(xxx){while(b);return 1}i++}'
        ) 
        
        
    def test_elseinline_cascaded(self):
        self.assertEqual(self.process(
            '''
            function x()
            {
              if(something)
              {
                while(x);
                return 0;
              }
              else if(xxx)
              {
                if(test2())
                {
                  while(x);
                  return 1;
                }
                else if(test3())
                {
                  while(x);
                  return 2;
                }
                else
                {
                  while(x);
                  return 3;
                }
              }
              else
              {
                while(x);
                return 4;
              }
            }
            '''),
            'function x(){if(something){while(x);return 0}if(xxx){if(test2()){while(x);return 1}if(test3()){while(x);return 2}while(x);return 3}while(x);return 4}'
        )        

     

    def test_if_deep_if(self):
        self.assertEqual(self.process(
            '''
            if(something)
            {
              for(g in h)
              {
                x++;
                if(otherthing){
                  y++;
                  while(bar);
                }
              }
            }
            '''),
            'if(something)for(g in h){x++;if(otherthing){y++;while(bar);}}'
        )        

    def test_loop_brackets(self):
        self.assertEqual(self.process(
            '''
            while(true)
            {
              retVal = !!callback(elems[i],i);

              if (inv!==retVal) {
                ret.push(elems[i])
              }
            }
            '''),
            'while(true)retVal=!!callback(elems[i],i),inv!==retVal&&ret.push(elems[i]);'
        )

    def test_switch_return(self):
        self.assertEqual(self.process(
            '''
            function wrapper(code)
            {
              switch(code)
              {
                case null:
                case 0:
                  return true;

                case -1:
                  return false;
              }
            }
            '''),
            'function wrapper(code){switch(code){case null:case 0:return true;case -1:return false}}'
        )        

    def test_if_else_cascaded(self):
        self.assertEqual(self.process(
            '''
            if(something)
            {
              if (condition)
              {
                somethingCase1a();
                somethingCase1b();
              }
              else
              {
                somethingCase2a();
                somethingCase2b();
              }
            }
            else
            {
              otherStuffA();
              otherStuffB();
            }
            '''),
            'something?condition?(somethingCase1a(),somethingCase1b()):(somethingCase2a(),somethingCase2b()):(otherStuffA(),otherStuffB());'
        )
        
    def test_if_else_expression(self):
        self.assertEqual(self.process(
            '''
            if(foo)
            {
              x++;
            }
            else
            {
              x--;
            }
            '''),
            'foo?x++:x--;'
        )        

    def test_if_else_both_empty(self):
        self.assertEqual(self.process(
            '''
            function wrapper()
            {
              if(something)
              {}
              else
              {}
            }
            '''),
            'function wrapper(){something}'
        )

    def test_if_else_empty(self):
        self.assertEqual(self.process(
            '''
            function wrapper()
            {
              if(something)
              {
                while(x);
              }
              else
              {}
            }
            '''),
            'function wrapper(){if(something)while(x);}'
        )        

    def test_if_else_while_if(self):
        self.assertEqual(self.process(
            '''
            if(first)
            {
              while(second) 
              {
                if(x)
                {
                  x++;
                }
              }
            }
            else
            {
              y++;
            }
            '''),
            'if(first)while(second)x&&x++;else y++;'
        )        

    def test_if_empty_else(self):
        self.assertEqual(self.process(
            '''
            function wrapper()
            {
              if(something)
              {
              }
              else
              {
                while(x); 
              }
            }
            '''),
            'function wrapper(){if(!something)while(x);}'
        )      
        
    def test_if_empty_else_two(self):
        self.assertEqual(self.process(
            '''
            function wrapper()
            {
              if(something && otherthing)
              {
              }
              else
              {
                while(x); 
              }
            }
            '''),
            'function wrapper(){if(!(something&&otherthing))while(x);}'
        )          

    def test_ifoptimize_assign_late(self):
        self.assertEqual(self.process(
            '''
            if(something) {
              x++;
              x=4;
            }
            '''),
            'something&&(x++,x=4);'
        )

    def test_ifoptimize_assign(self):
        self.assertEqual(self.process(
            '''
            if (something) {
              x = 4;
            }
            '''),
            'something&&(x=4);'
        )        

    def test_ifoptimize_crazy(self):
        self.assertEqual(self.process(
            'if (X && !this.isRich()) { {}; }'),
            'X&&!this.isRich();'
        )

    def test_ifoptimize_empty(self):
        self.assertEqual(self.process(
            'if(something){}'),
            'something;'
        )        

    def test_mergeassign_assign(self):
        self.assertEqual(self.process(
            '''
            if(foo)
            {
              x = 5;
            }
            else
            {
              x = 7;
            }
            '''),
            'x=foo?5:7;'
        )

    def test_mergeassign_assign_plus(self):
        self.assertEqual(self.process(
            '''
            if(something) {
              x += 3;
            } else {
              x += 4;
            }
            '''),
            'x+=something?3:4;'
        )        

    def test_mergeassign_object(self):
        self.assertEqual(self.process(
            '''
            if(something) {
              obj.foo.bar = "hello";
            } else {
              obj.foo.bar = "world";
            }
            '''),
            'obj.foo.bar=something?"hello":"world";'
        )
    
    def test_mergereturn(self):
        self.assertEqual(self.process(
            '''
            function ret()
            {
              if(something) {
                return "hello";
              } else {
                return "world";
              }
            }
            '''),
            'function ret(){return something?"hello":"world"}'
        )

    def test_parens_arithm(self):
        self.assertEqual(self.process(
            'x=(4*5)+4;'),
            'x=24;'
        )        

    def test_parens_assign(self):
        self.assertEqual(self.process(
            'doc = (context ? context.ownerDocument || context : document);'),
            'doc=context?context.ownerDocument||context:document;'
        )

    def test_parens_condition(self):
        self.assertEqual(self.process(
            '''
            while ( (fn = readyList[ i++ ]) ) {
              fn.call( document, jQuery );
            }
            '''),
            'while(fn=readyList[i++])fn.call(document,jQuery);'
        )        

    def test_parens_directexec(self):
        self.assertEqual(self.process(
            '(function(){ x++; })();'),
            '(function(){x++})();'
        )

    def test_parens_new(self):
        self.assertEqual(self.process(
            'var x = (new some.special.Item).setText("Hello World");'),
            'var x=(new some.special.Item).setText("Hello World");'
        )        

    def test_parens_new_args(self):
        self.assertEqual(self.process(
            'var x = new some.special.Item("param").setText("Hello World");'),
            'var x=new some.special.Item("param").setText("Hello World");'
        )        

    def test_parens_return(self):
        self.assertEqual(self.process(
            '''
            function x() {
              return (somemethod() && othermethod() != null);
            }
            '''),
            'function x(){return somemethod()&&othermethod()!=null}'
        )
        
    def test_parens_numberoper(self):
        self.assertEqual(self.process('''(23).pad(2);'''), '(23).pad(2);')
        
    def test_single_command_if_block(self):
        self.assertEqual(self.process(
            '''
            if (!abc) {
              abc = {
                setup: function() {
                  if (cde) {
                    x();
                  } else {
                    return false;
                  }
                }
              };
            }
            '''),
            'abc||(abc={setup:function(){if(cde)x();else return false}});'
        )

    def test_strict(self):
        self.assertEqual(self.process(
            '''
            function foo() {

              "use strict";

              doSomething();

            }

            foo();
            '''),
            'function foo(){"use strict";doSomething()}foo();'
        )

    def test_return_in_elseif(self):
        self.assertEqual(self.process(
            '''
            var a = function() {
                if (yyy) {
                    return;
                } else if (zzz) {
                    return;
                } else {
                    return;
                }
            };
            '''),
            'var a=function(){if(yyy)return;if(zzz)return;return};'
        )



if __name__ == '__main__':
    logging.getLogger().setLevel(logging.ERROR)
    suite = unittest.TestLoader().loadTestsFromTestCase(Tests)
    unittest.TextTestRunner(verbosity=2).run(suite)    


########NEW FILE########
__FILENAME__ = combinedecl
#!/usr/bin/env python3

import sys, os, unittest, logging

# Extend PYTHONPATH with local 'lib' folder
if __name__ == "__main__":
    jasyroot = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]), os.pardir, os.pardir, os.pardir, os.pardir))
    sys.path.insert(0, jasyroot)
    print("Running from %s..." % jasyroot)

import jasy.js.parse.Parser as Parser
import jasy.js.parse.ScopeScanner as ScopeScanner
import jasy.js.output.Compressor as Compressor
import jasy.js.optimize.CombineDeclarations as CombineDeclarations


class Tests(unittest.TestCase):

    def process(self, code):
        node = Parser.parse(code)
        ScopeScanner.scan(node)
        CombineDeclarations.optimize(node)
        return Compressor.Compressor().compress(node)


    def test_combine_basic(self):
        self.assertEqual(self.process(
            '''
            var foo=3;
            var bar=4;
            foo++;
            var baz=foo+bar;
            '''),
            'var foo=3,bar=4,baz;foo++;baz=foo+bar;'
        )        

    def test_combine_closure_innerfirst(self):
        self.assertEqual(self.process(
            '''
            function inner() 
            {
              var innerVarA = 5;
              var innerVarB = 10;
              doSomething();
              var innerVarC = 15;
            }
            var after;
            var afterInit = 6;
            '''),
            'function inner(){var innerVarA=5,innerVarB=10,innerVarC;doSomething();innerVarC=15}var after,afterInit=6;'
        )

    def test_combine_closure(self):
        self.assertEqual(self.process(
            '''
            var before = 4;
            function inner() 
            {
              var innerVarA = 5;
              var innerVarB = 10;
              doSomething();
              var innerVarC = 15;
            }
            var after;
            var afterInit = 6;
            '''),
            'var before=4,after,afterInit;function inner(){var innerVarA=5,innerVarB=10,innerVarC;doSomething();innerVarC=15}afterInit=6;'
        )

    def test_combine_complex(self):
        self.assertEqual(self.process(
            '''
            var foo=3;
            var bar=4;
            foo++;
            {
              var baz=foo+bar;
              var next;
            }
            '''),
            'var foo=3,bar=4,baz,next;foo++;{baz=foo+bar}'
        )        

    def test_combine_destruct_assign(self):
        self.assertEqual(self.process(
            '''
            function wrapper()
            {
              var desFirst=3;
              while(x);
              var [desFirst, desSecond] = destruct();
            }
            '''),
            'function wrapper(){var desFirst=3,desSecond;while(x);[desFirst,desSecond]=destruct()}'
        )

    def test_combine_destruct(self):
        self.assertEqual(self.process(
            '''
            function wrapper()
            {
              var desFirst=3, desSecond;
              var [desFirst, desSecond] = destruct();
            }
            '''),
            'function wrapper(){var desFirst=3,[desFirst,desSecond]=destruct()}'
        )        

    def test_combine_doubles(self):
        self.assertEqual(self.process(
            '''
            var foo=3;
            var foo=4;
            '''),
            'var foo=3,foo=4;'
        )

    def test_combine_doubles_break(self):
        self.assertEqual(self.process(
            '''
            var foo = 3;
            var bar = 2;
            x();
            var foo = 4;
            '''),
            'var foo=3,bar=2;x();foo=4;'
        )        

    def test_combine_doubles_for(self):
        self.assertEqual(self.process(
            '''
            for(var key in obj) {}
            for(var key in obj2) {}
            for(var key2 in obj) {}
            '''),
            'var key,key2;for(key in obj){}for(key in obj2){}for(key2 in obj){}'
        )
        
    def test_combine_doubles_oneassign(self):
        self.assertEqual(self.process(
            '''
            var foo=3;
            var foo;
            '''),
            'var foo=3;'
        )
        

if __name__ == '__main__':
    logging.getLogger().setLevel(logging.ERROR)
    suite = unittest.TestLoader().loadTestsFromTestCase(Tests)
    unittest.TextTestRunner(verbosity=2).run(suite)


########NEW FILE########
__FILENAME__ = comments
#!/usr/bin/env python3

import sys, os, unittest, logging

# Extend PYTHONPATH with local 'lib' folder
if __name__ == "__main__":
    jasyroot = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]), os.pardir, os.pardir, os.pardir, os.pardir))
    sys.path.insert(0, jasyroot)
    print("Running from %s..." % jasyroot)

import jasy.js.parse.Parser as Parser


        
class Tests(unittest.TestCase):

    def process(self, code):
        node = Parser.parse(code)
        return node
        
        

    #
    # SINGLE COMMENTS
    #        
    
    def test_single(self):
        
        parsed = self.process('''
        
        // Single Comment
        singleCommentCmd();
        
        ''')
        
        self.assertEqual(parsed[0].type, "semicolon")
        self.assertEqual(isinstance(parsed[0].comments, list), True)
        self.assertEqual(len(parsed[0].comments), 1)
        
        self.assertEqual(parsed[0].comments[0].variant, "single")
        self.assertEqual(parsed[0].comments[0].text, "Single Comment")
        

    def test_single_unbound(self):

        parsed = self.process('''
        // Single Comment
        ''')

        self.assertEqual(parsed.type, "script")
        self.assertEqual(isinstance(parsed.comments, list), True)
        self.assertEqual(len(parsed.comments), 1)

        self.assertEqual(parsed.comments[0].variant, "single")
        self.assertEqual(parsed.comments[0].text, "Single Comment")        


    def test_single_unbound_nobreak(self):

        parsed = self.process('''// Single Comment''')

        self.assertEqual(parsed.type, "script")
        self.assertEqual(isinstance(parsed.comments, list), True)
        self.assertEqual(len(parsed.comments), 1)

        self.assertEqual(parsed.comments[0].variant, "single")
        self.assertEqual(parsed.comments[0].text, "Single Comment")        

        
    def test_single_two(self):

        parsed = self.process('''

        // Single1 Comment
        // Single2 Comment
        singleCommentCmd();

        ''')

        self.assertEqual(parsed[0].type, "semicolon")
        self.assertEqual(isinstance(parsed[0].comments, list), True)
        self.assertEqual(len(parsed[0].comments), 2)

        self.assertEqual(parsed[0].comments[0].variant, "single")
        self.assertEqual(parsed[0].comments[0].text, "Single1 Comment")

        self.assertEqual(parsed[0].comments[1].variant, "single")
        self.assertEqual(parsed[0].comments[1].text, "Single2 Comment")
        
        
        
    #
    # SINGLE COMMENTS :: CONTEXT
    #
        
    def test_single_context_inline(self):

        parsed = self.process('''singleCommentCmd(); // Single Inline Comment''')

        self.assertEqual(parsed[0].type, "semicolon")
        self.assertEqual(isinstance(parsed[0].comments, list), True)
        self.assertEqual(len(parsed[0].comments), 1)

        self.assertEqual(parsed[0].comments[0].variant, "single")
        self.assertEqual(parsed[0].comments[0].context, "inline")
        
        
    def test_single_context_block_before(self):

        parsed = self.process('''
        singleCommentCmd(); 
        // Single Block Comment
        ''')

        self.assertEqual(parsed[0].type, "semicolon")
        self.assertEqual(isinstance(parsed[0].comments, list), True)
        self.assertEqual(len(parsed[0].comments), 1)

        self.assertEqual(parsed[0].comments[0].variant, "single")
        self.assertEqual(parsed[0].comments[0].context, "block")   
        
        
    def test_single_context_block_after(self):

        parsed = self.process('''
        // Single Block Comment
        singleCommentCmd(); 
        ''')

        self.assertEqual(parsed[0].type, "semicolon")
        self.assertEqual(isinstance(parsed[0].comments, list), True)
        self.assertEqual(len(parsed[0].comments), 1)

        self.assertEqual(parsed[0].comments[0].variant, "single")
        self.assertEqual(parsed[0].comments[0].context, "block")
        
        
    def test_single_context_section(self):

        parsed = self.process('''
        
        // Single Section Comment
        singleCommentCmd(); 
        ''')

        self.assertEqual(parsed[0].type, "semicolon")
        self.assertEqual(isinstance(parsed[0].comments, list), True)
        self.assertEqual(len(parsed[0].comments), 1)

        self.assertEqual(parsed[0].comments[0].variant, "single")
        self.assertEqual(parsed[0].comments[0].context, "section")
        
        
        
    #
    # MULTI COMMENTS
    #
        
    def test_multi(self):

        parsed = self.process('''

        /* Multi Comment */
        multiCommentCmd();

        ''')

        self.assertEqual(parsed[0].type, "semicolon")
        self.assertEqual(isinstance(parsed[0].comments, list), True)
        self.assertEqual(len(parsed[0].comments), 1)

        self.assertEqual(parsed[0].comments[0].variant, "multi")
        self.assertEqual(parsed[0].comments[0].text, "Multi Comment")        
        
        
    def test_multi_unbound(self):

        parsed = self.process('''
        /* Multi Comment */
        ''')

        self.assertEqual(parsed.type, "script")
        self.assertEqual(isinstance(parsed.comments, list), True)
        self.assertEqual(len(parsed.comments), 1)

        self.assertEqual(parsed.comments[0].variant, "multi")
        self.assertEqual(parsed.comments[0].text, "Multi Comment")        
        
        
    def test_multi_unbound_nobreak(self):

        parsed = self.process('''/* Multi Comment */''')

        self.assertEqual(parsed.type, "script")
        self.assertEqual(isinstance(parsed.comments, list), True)
        self.assertEqual(len(parsed.comments), 1)

        self.assertEqual(parsed.comments[0].variant, "multi")
        self.assertEqual(parsed.comments[0].text, "Multi Comment")        
        
        
    def test_multi_two(self):

        parsed = self.process('''

        /* Multi Comment1 */
        /* Multi Comment2 */
        multiCommentCmd();

        ''')

        self.assertEqual(parsed[0].type, "semicolon")
        self.assertEqual(isinstance(parsed[0].comments, list), True)
        self.assertEqual(len(parsed[0].comments), 2)

        self.assertEqual(parsed[0].comments[0].variant, "multi")
        self.assertEqual(parsed[0].comments[0].text, "Multi Comment1")
        
        self.assertEqual(parsed[0].comments[1].variant, "multi")
        self.assertEqual(parsed[0].comments[1].text, "Multi Comment2")
        
        
    def test_multi_multiline(self):

        parsed = self.process('''

        /* Multi
           Comment
           Test */
        multiCommentCmd();

        ''')

        self.assertEqual(parsed[0].type, "semicolon")
        self.assertEqual(isinstance(parsed[0].comments, list), True)
        self.assertEqual(len(parsed[0].comments), 1)

        self.assertEqual(parsed[0].comments[0].variant, "multi")
        self.assertEqual(parsed[0].comments[0].text, "   Multi\n   Comment\n   Test")
        
        
    def test_multi_multiline_otherbreaks(self):

        parsed = self.process('''

        /*
          Multi
          Comment
          Test 
        */
        multiCommentCmd();

        ''')

        self.assertEqual(parsed[0].type, "semicolon")
        self.assertEqual(isinstance(parsed[0].comments, list), True)
        self.assertEqual(len(parsed[0].comments), 1)

        self.assertEqual(parsed[0].comments[0].variant, "multi")
        self.assertEqual(parsed[0].comments[0].text, "  Multi\n  Comment\n  Test")
    
    
    
    #
    # MULTI COMMENTS :: CONTEXT
    #
            
    def test_multi_context_inline(self):

        parsed = self.process('''multiCommentCmd(); /* Multi Inline Comment */''')

        self.assertEqual(parsed[0].type, "semicolon")
        self.assertEqual(isinstance(parsed[0].comments, list), True)
        self.assertEqual(len(parsed[0].comments), 1)

        self.assertEqual(parsed[0].comments[0].variant, "multi")
        self.assertEqual(parsed[0].comments[0].context, "inline")
        
        
    def test_multi_context_inline_multiline(self):

        parsed = self.process('''
        multiCommentCmd(); /* 
          Multi Inline Comment 
        */''')

        self.assertEqual(parsed[0].type, "semicolon")
        self.assertEqual(isinstance(parsed[0].comments, list), True)
        self.assertEqual(len(parsed[0].comments), 1)

        self.assertEqual(parsed[0].comments[0].variant, "multi")
        self.assertEqual(parsed[0].comments[0].context, "inline")        


    def test_multi_context_block_before(self):

        parsed = self.process('''
        multiCommentCmd(); 
        /* Multi Block Comment */
        ''')

        self.assertEqual(parsed[0].type, "semicolon")
        self.assertEqual(isinstance(parsed[0].comments, list), True)
        self.assertEqual(len(parsed[0].comments), 1)

        self.assertEqual(parsed[0].comments[0].variant, "multi")
        self.assertEqual(parsed[0].comments[0].context, "block")   


    def test_multi_context_block_after(self):

        parsed = self.process('''
        /* Multi Block Comment */
        multiCommentCmd(); 
        ''')

        self.assertEqual(parsed[0].type, "semicolon")
        self.assertEqual(isinstance(parsed[0].comments, list), True)
        self.assertEqual(len(parsed[0].comments), 1)

        self.assertEqual(parsed[0].comments[0].variant, "multi")
        self.assertEqual(parsed[0].comments[0].context, "block")


    def test_multi_context_section(self):

        parsed = self.process('''

        /* Multi Section Comment */
        multiCommentCmd(); 
        ''')

        self.assertEqual(parsed[0].type, "semicolon")
        self.assertEqual(isinstance(parsed[0].comments, list), True)
        self.assertEqual(len(parsed[0].comments), 1)

        self.assertEqual(parsed[0].comments[0].variant, "multi")
        self.assertEqual(parsed[0].comments[0].context, "section")    
    
    


    #
    # PROTECTED COMMENTS
    #

    def test_protected(self):

        parsed = self.process('''

        /*! Protected Comment */
        protectedCommentCmd();

        ''')

        self.assertEqual(parsed[0].type, "semicolon")
        self.assertEqual(isinstance(parsed[0].comments, list), True)
        self.assertEqual(len(parsed[0].comments), 1)

        self.assertEqual(parsed[0].comments[0].variant, "protected")
        self.assertEqual(parsed[0].comments[0].text, "Protected Comment")    


    def test_protected_newline(self):

        parsed = self.process('''

        /*! 
        Protected Comment 
        */
        protectedCommentCmd();

        ''')

        self.assertEqual(parsed[0].type, "semicolon")
        self.assertEqual(isinstance(parsed[0].comments, list), True)
        self.assertEqual(len(parsed[0].comments), 1)

        self.assertEqual(parsed[0].comments[0].variant, "protected")
        self.assertEqual(parsed[0].comments[0].text, "Protected Comment")
            

    def test_protected_jquery(self):

        parsed = self.process('''

        /*!
         * jQuery JavaScript Library v@VERSION
         * http://jquery.com/
         *
         * Copyright 2011, John Resig
         * Dual licensed under the MIT or GPL Version 2 licenses.
         * http://jquery.org/license
         *
         * Includes Sizzle.js
         * http://sizzlejs.com/
         * Copyright 2011, The Dojo Foundation
         * Released under the MIT, BSD, and GPL Licenses.
         *
         * Date: @DATE
         */

        ''')

        self.assertEqual(parsed.type, "script")
        self.assertEqual(isinstance(parsed.comments, list), True)
        self.assertEqual(len(parsed.comments), 1)

        self.assertEqual(parsed.comments[0].variant, "protected")
        self.assertEqual(parsed.comments[0].text, "jQuery JavaScript Library v@VERSION\nhttp://jquery.com/\n\nCopyright 2011, John Resig\nDual licensed under the MIT or GPL Version 2 licenses.\nhttp://jquery.org/license\n\nIncludes Sizzle.js\nhttp://sizzlejs.com/\nCopyright 2011, The Dojo Foundation\nReleased under the MIT, BSD, and GPL Licenses.\n\nDate: @DATE")



    #
    # ATTACHMENT
    #
    
    def test_missing_node(self):

        parsed = self.process('''

        /** Root Doc */
        core.Class("xxx", {
          members : {
            foo : function() {
              /** TODO */
            }
          }
          /** END */
        })

        ''')

        self.assertEqual(parsed.type, "script")
        
        self.assertEqual(isinstance(parsed[0].comments, list), True)
        self.assertEqual(len(parsed[0].comments), 1)
        self.assertEqual(parsed[0].comments[0].variant, "doc")
        self.assertEqual(parsed[0].comments[0].text, "Root Doc")


    


    #
    # DOC COMMENTS
    #
    
    def test_doc(self):

        parsed = self.process('''

        /** Doc Comment */
        docCommentCmd();

        ''')

        self.assertEqual(parsed[0].type, "semicolon")
        self.assertEqual(isinstance(parsed[0].comments, list), True)
        self.assertEqual(len(parsed[0].comments), 1)

        self.assertEqual(parsed[0].comments[0].variant, "doc")
        self.assertEqual(parsed[0].comments[0].getHtml(), "<p>Doc Comment</p>\n")
        self.assertEqual(parsed[0].comments[0].text, "Doc Comment")
        
        
    def test_doc_unbound(self):

        parsed = self.process('''
        /** Doc Comment */
        ''')

        self.assertEqual(parsed.type, "script")
        self.assertEqual(isinstance(parsed.comments, list), True)
        self.assertEqual(len(parsed.comments), 1)

        self.assertEqual(parsed.comments[0].variant, "doc")
        self.assertEqual(parsed.comments[0].getHtml(), "<p>Doc Comment</p>\n")
        self.assertEqual(parsed.comments[0].text, "Doc Comment")
        
        
    def test_doc_unbound_nobreak(self):

        parsed = self.process('''/** Doc Comment */''')

        self.assertEqual(parsed.type, "script")
        self.assertEqual(isinstance(parsed.comments, list), True)
        self.assertEqual(len(parsed.comments), 1)

        self.assertEqual(parsed.comments[0].variant, "doc")
        self.assertEqual(parsed.comments[0].getHtml(), "<p>Doc Comment</p>\n")
        self.assertEqual(parsed.comments[0].text, "Doc Comment")


    def test_doc_multiline(self):

        parsed = self.process('''

        /**
         * Doc Comment
         */
        docCommentCmd();

        ''')

        self.assertEqual(parsed[0].type, "semicolon")
        self.assertEqual(isinstance(parsed[0].comments, list), True)
        self.assertEqual(len(parsed[0].comments), 1)

        self.assertEqual(parsed[0].comments[0].variant, "doc")
        self.assertEqual(parsed[0].comments[0].getHtml(), "<p>Doc Comment</p>\n")
        self.assertEqual(parsed[0].comments[0].text, "Doc Comment")
        

    def test_doc_multiline_three(self):

        parsed = self.process('''

        /**
         * Doc Comment Line 1
         * Doc Comment Line 2
         * Doc Comment Line 3
         */
        docCommentCmd();

        ''')

        self.assertEqual(parsed[0].type, "semicolon")
        self.assertEqual(isinstance(parsed[0].comments, list), True)
        self.assertEqual(len(parsed[0].comments), 1)

        self.assertEqual(parsed[0].comments[0].variant, "doc")
        self.assertEqual(parsed[0].comments[0].getHtml(), "<p>Doc Comment Line 1\nDoc Comment Line 2\nDoc Comment Line 3</p>\n")
        self.assertEqual(parsed[0].comments[0].text, "Doc Comment Line 1\nDoc Comment Line 2\nDoc Comment Line 3")
        
        
        
    def test_doc_multiline_clean(self):

        parsed = self.process('''

        /**
        Doc Comment
        */
        docCommentCmd();

        ''')

        self.assertEqual(parsed[0].type, "semicolon")
        self.assertEqual(isinstance(parsed[0].comments, list), True)
        self.assertEqual(len(parsed[0].comments), 1)

        self.assertEqual(parsed[0].comments[0].variant, "doc")
        self.assertEqual(parsed[0].comments[0].getHtml(), "<p>Doc Comment</p>\n")
        self.assertEqual(parsed[0].comments[0].text, "Doc Comment")


    def test_doc_multiline_clean_three(self):

        parsed = self.process('''

        /**
        Doc Comment Line 1
        Doc Comment Line 2
        Doc Comment Line 3
        */
        docCommentCmd();

        ''')

        self.assertEqual(parsed[0].type, "semicolon")
        self.assertEqual(isinstance(parsed[0].comments, list), True)
        self.assertEqual(len(parsed[0].comments), 1)

        self.assertEqual(parsed[0].comments[0].variant, "doc")
        self.assertEqual(parsed[0].comments[0].getHtml(), "<p>Doc Comment Line 1\nDoc Comment Line 2\nDoc Comment Line 3</p>\n")
        self.assertEqual(parsed[0].comments[0].text, "Doc Comment Line 1\nDoc Comment Line 2\nDoc Comment Line 3")


    #
    # DOC COMMENTS :: RETURN
    #

    def test_doc_return(self):

        parsed = self.process('''

        /**
         * {Number} Returns the sum of x and y.
         */

        ''')

        self.assertEqual(parsed.type, "script")
        self.assertEqual(isinstance(parsed.comments, list), True)
        self.assertEqual(len(parsed.comments), 1)

        comment = parsed.comments[0]

        self.assertEqual(comment.variant, "doc")
        self.assertEqual(comment.getHtml(), "<p>Returns the sum of x and y.</p>\n")
        self.assertEqual(comment.text, "Returns the sum of x and y.")
        self.assertEqual(comment.returns[0]["name"], "Number")
        
        
    def test_doc_return_twotypes(self):

        parsed = self.process('''

        /**
         * {Number | String} Returns the sum of x and y.
         */

        ''')

        self.assertEqual(parsed.type, "script")
        self.assertEqual(isinstance(parsed.comments, list), True)
        self.assertEqual(len(parsed.comments), 1)

        comment = parsed.comments[0]

        self.assertEqual(comment.variant, "doc")
        self.assertEqual(comment.getHtml(), "<p>Returns the sum of x and y.</p>\n")
        self.assertEqual(comment.text, "Returns the sum of x and y.")
        self.assertEqual(comment.returns[0]["name"], "Number")
        self.assertEqual(comment.returns[1]["name"], "String")
    
    
    
    #
    # DOC COMMENTS :: TAGS
    #

    def test_doc_tags(self):
        
        parsed = self.process('''
        
        /**
         * Hello World
         *
         * #deprecated #public #use(future) #use(current)
         */
        
        ''')
        
        self.assertEqual(parsed.type, "script")
        self.assertEqual(isinstance(parsed.comments, list), True)
        self.assertEqual(len(parsed.comments), 1)

        comment = parsed.comments[0]

        self.assertEqual(comment.variant, "doc")
        self.assertEqual(comment.getHtml(), "<p>Hello World</p>\n")
        self.assertEqual(comment.text, "Hello World")
        
        self.assertEqual(comment.tags["deprecated"], True)
        self.assertEqual(comment.tags["public"], True)
        self.assertEqual(type(comment.tags["use"]), set)
        self.assertEqual("future" in comment.tags["use"], True)
        self.assertEqual("current" in comment.tags["use"], True)
        self.assertEqual("xxx" in comment.tags["use"], False)
        
    
    
    def test_doc_tags_clean(self):

        parsed = self.process('''

        /**
         * #deprecated #public #use(future) #use(current)
         */

        ''')

        self.assertEqual(parsed.type, "script")
        self.assertEqual(isinstance(parsed.comments, list), True)
        self.assertEqual(len(parsed.comments), 1)

        comment = parsed.comments[0]

        self.assertEqual(comment.variant, "doc")
        self.assertEqual(comment.text, "")
    
        self.assertEqual(comment.tags["deprecated"], True)
        self.assertEqual(comment.tags["public"], True)
        self.assertEqual(type(comment.tags["use"]), set)
        self.assertEqual("future" in comment.tags["use"], True)
        self.assertEqual("current" in comment.tags["use"], True)
        self.assertEqual("xxx" in comment.tags["use"], False)

    
    
    #
    # DOC COMMENTS :: LINKS
    #

    def test_doc_links(self):

        parsed = self.process('''
        
        /**
         * Link to cool {z.core.Style} class. Looks at this method {core.io.Asset#toUri} to translate local
         * asset IDs to something usable in the browser.
         */

        ''')
        
        self.assertEqual(parsed.type, "script")
        self.assertEqual(isinstance(parsed.comments, list), True)
        self.assertEqual(len(parsed.comments), 1)

        comment = parsed.comments[0]
        
        self.assertEqual(comment.getHtml(), '<p>Link to cool <a href="#z.core.Style"><code>z.core.Style</code></a> class. Looks at this method <a href="#core.io.Asset~toUri"><code>core.io.Asset#toUri</code></a> to translate local\nasset IDs to something usable in the browser.</p>\n')
        self.assertEqual(comment.text, 'Link to cool z.core.Style class. Looks at this method core.io.Asset#toUri to translate local\nasset IDs to something usable in the browser.')
    
    
    def test_doc_links_primitive(self):

        parsed = self.process('''

        /**
         * You can either use {String} or {Map} types as primitive data types.
         */

        ''')

        self.assertEqual(parsed.type, "script")
        self.assertEqual(isinstance(parsed.comments, list), True)
        self.assertEqual(len(parsed.comments), 1)

        comment = parsed.comments[0]

        self.assertEqual(comment.getHtml(), '<p>You can either use <a href="#String"><code>String</code></a> or <a href="#Map"><code>Map</code></a> types as primitive data types.</p>\n')
        self.assertEqual(comment.text, 'You can either use String or Map types as primitive data types.')    


    def test_doc_links_type(self):

        parsed = self.process('''

        /**
         * Just execute the {member:#update} method to fire the event {event:#update}.
         */

        ''')

        self.assertEqual(parsed.type, "script")
        self.assertEqual(isinstance(parsed.comments, list), True)
        self.assertEqual(len(parsed.comments), 1)

        comment = parsed.comments[0]

        self.assertEqual(comment.getHtml(), '<p>Just execute the <a href="#member:~update"><code>update</code></a> method to fire the event <a href="#event:~update"><code>update</code></a>.</p>\n')
        self.assertEqual(comment.text, 'Just execute the update method to fire the event update.')


    def test_doc_links_object_alike(self):

        parsed = self.process('''
        
        /**
         * {event:foo} an foo event that looks like a json structure.
         */

        ''')
        
        self.assertEqual(parsed.type, "script")
        self.assertEqual(isinstance(parsed.comments, list), True)
        self.assertEqual(len(parsed.comments), 1)

        comment = parsed.comments[0]
        
        self.assertEqual(comment.getHtml(), '<p><a href="#foo"><code>foo</code></a> an foo event that looks like a json structure.</p>\n')
        self.assertEqual(comment.text, 'foo an foo event that looks like a json structure.')


    #
    # DOC COMMENTS :: Code Blocks
    #
    def test_doc_links_in_code_block(self):

        parsed = self.process('''
        
        /**
         * Foo event example code:
         * 
         *     var e = {event:foo};
         *     var e = {};
         */

        ''')
        
        self.assertEqual(parsed.type, "script")
        self.assertEqual(isinstance(parsed.comments, list), True)
        self.assertEqual(len(parsed.comments), 1)

        comment = parsed.comments[0]

        self.assertEqual(comment.getHtml(), '<p>Foo event example code:</p>\n\n<table class="highlighttable"><tr><td class="linenos"><div class="linenodiv"><pre>1\n2</pre></div></td><td class="code"><div class="highlight"><pre><span class="kd">var</span> <span class="nx">e</span> <span class="o">=</span> <span class="p">{</span><span class="nx">event</span><span class="o">:</span><span class="nx">foo</span><span class="p">};</span>\n<span class="kd">var</span> <span class="nx">e</span> <span class="o">=</span> <span class="p">{};</span>\n</pre></div>\n</td></tr></table>\n')
        self.assertEqual(comment.text, 'Foo event example code:\n\n    var e = {event:foo};\n    var e = {};')
    

    def test_doc_params_in_code_block(self):

        parsed = self.process('''
        
        /**
         * Email example code:
         * 
         *     var foo = 'hello@bla.org';
         *     var test = "foo@blub.net";
         */

        ''')
        
        self.assertEqual(parsed.type, "script")
        self.assertEqual(isinstance(parsed.comments, list), True)
        self.assertEqual(len(parsed.comments), 1)

        comment = parsed.comments[0]

        self.assertEqual(comment.getHtml(), '<p>Email example code:</p>\n\n<table class="highlighttable"><tr><td class="linenos"><div class="linenodiv"><pre>1\n2</pre></div></td><td class="code"><div class="highlight"><pre><span class="kd">var</span> <span class="nx">foo</span> <span class="o">=</span> <span class="s1">\'hello@bla.org\'</span><span class="p">;</span>\n<span class="kd">var</span> <span class="nx">test</span> <span class="o">=</span> <span class="s2">"foo@blub.net"</span><span class="p">;</span>\n</pre></div>\n</td></tr></table>\n')
        self.assertEqual(comment.text, 'Email example code:\n\n    var foo = \'hello@bla.org\';\n    var test = "foo@blub.net";')


    def test_multi_code_blocks(self):

        parsed = self.process('''
        
        /**
         * Some code example:
         * 
         *     // A code block with empty lines in it
         *
         *     if (true) {
         *  
         *     } else {
         *      
         *     }
         *
         *  Another code block:
         *  
         *      console.log('Hello World');
         */

        ''')
        
        self.assertEqual(parsed.type, "script")
        self.assertEqual(isinstance(parsed.comments, list), True)
        self.assertEqual(len(parsed.comments), 1)
        comment = parsed.comments[0]

        self.assertEqual(comment.getHtml(), '<p>Some code example:</p>\n\n<table class="highlighttable"><tr><td class="linenos"><div class="linenodiv"><pre>1\n2\n3\n4\n5\n6\n7</pre></div></td><td class="code"><div class="highlight"><pre><span class="c1">// A code block with empty lines in it</span>\n\n<span class="k">if</span> <span class="p">(</span><span class="kc">true</span><span class="p">)</span> <span class="p">{</span>\n\n<span class="p">}</span> <span class="k">else</span> <span class="p">{</span>\n\n<span class="p">}</span>\n</pre></div>\n</td></tr></table>\n<p>Another code block:</p>\n\n<table class="highlighttable"><tr><td class="linenos"><div class="linenodiv"><pre>1</pre></div></td><td class="code"><div class="highlight"><pre> <span class="nx">console</span><span class="p">.</span><span class="nx">log</span><span class="p">(</span><span class="s1">\'Hello World\'</span><span class="p">);</span>\n</pre></div>\n</td></tr></table>\n')
        self.assertEqual(comment.text, 'Some code example:\n\n    // A code block with empty lines in it\n\n    if (true) {\n\n    } else {\n\n    }\n\nAnother code block:\n\n     console.log(\'Hello World\');')


    def test_code_blocks_in_list(self):

        self.maxDiff = None
        parsed = self.process('''
        
        /**
         * Some code:
         *
         *     var e = 1;
         *
         * A list of things below:
         *
         *  - __listItem__
         *
         *     This is text and not code.
         *
         *          // Some code
         *          console.log("This actually is code in the list")
         *
         *  - __anotherListItem__
         *
         *      More text.
         *      
         *          console.log("More code")
         *
         */

        ''')
        
        self.assertEqual(parsed.type, "script")
        self.assertEqual(isinstance(parsed.comments, list), True)
        self.assertEqual(len(parsed.comments), 1)
        comment = parsed.comments[0]

        #print('\\n'.join(comment.getHtml().split('\n')))
        #print('\\n'.join(comment.text.split('\n')))

        self.assertEqual(comment.getHtml(), '<p>Some code:</p>\n\n<table class="highlighttable"><tr><td class="linenos"><div class="linenodiv"><pre>1</pre></div></td><td class="code"><div class="highlight"><pre><span class="kd">var</span> <span class="nx">e</span> <span class="o">=</span> <span class="mi">1</span><span class="p">;</span>\n</pre></div>\n</td></tr></table>\n<p>A list of things below:</p>\n\n<ul>\n<li><p><strong>listItem</strong></p>\n\n<p>This is text and not code.</p></li>\n</ul>\n\n<table class="highlighttable"><tr><td class="linenos"><div class="linenodiv"><pre>1\n2</pre></div></td><td class="code"><div class="highlight"><pre>     <span class="c1">// Some code</span>\n     <span class="nx">console</span><span class="p">.</span><span class="nx">log</span><span class="p">(</span><span class="s2">"This actually is code in the list"</span><span class="p">)</span>\n</pre></div>\n</td></tr></table>\n<ul>\n<li><p><strong>anotherListItem</strong></p>\n\n<p>More text.</p></li>\n</ul>\n\n<table class="highlighttable"><tr><td class="linenos"><div class="linenodiv"><pre>1</pre></div></td><td class="code"><div class="highlight"><pre>     <span class="nx">console</span><span class="p">.</span><span class="nx">log</span><span class="p">(</span><span class="s2">"More code"</span><span class="p">)</span>\n</pre></div>\n</td></tr></table>\n')
        self.assertEqual(comment.text, 'Some code:\n\n    var e = 1;\n\nA list of things below:\n\n - __listItem__\n\n    This is text and not code.\n\n         // Some code\n         console.log("This actually is code in the list")\n\n- __anotherListItem__\n\n     More text.\n\n         console.log("More code")')


    #
    # DOC COMMENTS :: PARAMS
    #
    
    def test_doc_params(self):

        parsed = self.process('''
        
        /**
         * {Boolean} Returns whether @x {Number} is bigger than @y {Number}. The optional @cache {Boolean?false} controls whether caching should be enabled.
         * Also see @extra {String | Array ?} which is normally pretty useless
         */

        ''')
        
        self.assertEqual(parsed.type, "script")
        self.assertEqual(isinstance(parsed.comments, list), True)
        self.assertEqual(len(parsed.comments), 1)

        comment = parsed.comments[0]
    
        self.assertEqual(comment.variant, "doc")
        self.assertEqual(comment.getHtml(), '<p>Returns whether <code class="param">x</code> is bigger than <code class="param">y</code>. The optional <code class="param">cache</code> controls whether caching should be enabled.\nAlso see <code class="param">extra</code> which is normally pretty useless</p>\n')
        self.assertEqual(comment.text, 'Returns whether x is bigger than y. The optional cache controls whether caching should be enabled.\nAlso see extra which is normally pretty useless')
        
        self.assertEqual(type(comment.params), dict)

        self.assertEqual(type(comment.params["x"]), dict)
        self.assertEqual(type(comment.params["y"]), dict)
        self.assertEqual(type(comment.params["cache"]), dict)
        self.assertEqual(type(comment.params["extra"]), dict)

        self.assertEqual(comment.params["x"]["type"][0]["name"], "Number")
        self.assertEqual(comment.params["y"]["type"][0]["name"], "Number")
        self.assertEqual(comment.params["cache"]["type"][0]["name"], "Boolean")
        self.assertEqual(comment.params["extra"]["type"][0]["name"], "String")
        self.assertEqual(comment.params["extra"]["type"][1]["name"], "Array")
        self.assertEqual(comment.params["cache"]["type"][0]["builtin"], True)
        self.assertEqual(comment.params["extra"]["type"][0]["builtin"], True)
        self.assertEqual(comment.params["extra"]["type"][1]["builtin"], True)

        self.assertNotIn("optional", comment.params["x"])
        self.assertNotIn("optional", comment.params["y"])
        self.assertIn("optional", comment.params["cache"])
        self.assertIn("optional", comment.params["extra"])

        self.assertNotIn("default", comment.params["x"])
        self.assertNotIn("default", comment.params["y"])
        self.assertEqual(comment.params["cache"]["default"], "false")
        self.assertNotIn("default", comment.params["extra"])
        
        
        
    def test_doc_params_dynamic(self):

        parsed = self.process('''

        /**
         * {Number} Returns the sum of all given @number {Number...} parameters.
         */

        ''')

        self.assertEqual(parsed.type, "script")
        self.assertEqual(isinstance(parsed.comments, list), True)
        self.assertEqual(len(parsed.comments), 1)

        comment = parsed.comments[0]

        self.assertEqual(comment.variant, "doc")

        self.assertEqual(type(comment.params), dict)
        self.assertEqual(type(comment.params["number"]), dict)
        self.assertEqual(comment.params["number"]["type"][0]["name"], "Number")
        self.assertNotIn("optional", comment.params["number"])
        self.assertTrue(comment.params["number"]["dynamic"])
        self.assertNotIn("default", comment.params["number"])
        
        
        
    def test_doc_params_dynamic_default(self):

        parsed = self.process('''

        /**
         * {Number} Returns the sum of all given @number {Number...?0} parameters.
         */

        ''')

        self.assertEqual(parsed.type, "script")
        self.assertEqual(isinstance(parsed.comments, list), True)
        self.assertEqual(len(parsed.comments), 1)

        comment = parsed.comments[0]

        self.assertEqual(comment.variant, "doc")

        self.assertEqual(type(comment.params), dict)
        self.assertEqual(type(comment.params["number"]), dict)
        self.assertEqual(comment.params["number"]["type"][0]["name"], "Number")
        self.assertEqual(comment.params["number"]["type"][0]["builtin"], True)
        self.assertTrue(comment.params["number"]["optional"])
        self.assertTrue(comment.params["number"]["dynamic"])
        self.assertEqual(comment.params["number"]["default"], "0")
        
        
        
    def test_doc_params_dynamic_multi(self):

        parsed = self.process('''

        /**
         * {Number} Returns the sum of all given @number {Number|Integer...} parameters.
         */

        ''')

        self.assertEqual(parsed.type, "script")
        self.assertEqual(isinstance(parsed.comments, list), True)
        self.assertEqual(len(parsed.comments), 1)

        comment = parsed.comments[0]

        self.assertEqual(comment.variant, "doc")

        self.assertEqual(type(comment.params), dict)
        self.assertEqual(type(comment.params["number"]), dict)
        self.assertEqual(comment.params["number"]["type"][0]["name"], "Number")
        self.assertEqual(comment.params["number"]["type"][1]["name"], "Integer")
        self.assertNotIn("optional", comment.params["number"])
        self.assertTrue(comment.params["number"]["dynamic"])
        self.assertNotIn("default", comment.params["number"])
        
        
        
    def test_doc_params_dynamic_multi_spacey(self):

        parsed = self.process('''

        /**
         * {Number} Returns the sum of all given @number {Number | Integer ... } parameters.
         */

        ''')

        self.assertEqual(parsed.type, "script")
        self.assertEqual(isinstance(parsed.comments, list), True)
        self.assertEqual(len(parsed.comments), 1)

        comment = parsed.comments[0]

        self.assertEqual(comment.variant, "doc")

        self.assertEqual(type(comment.params), dict)
        self.assertEqual(type(comment.params["number"]), dict)
        self.assertEqual(comment.params["number"]["type"][0]["name"], "Number")
        self.assertEqual(comment.params["number"]["type"][1]["name"], "Integer")
        self.assertNotIn("optional", comment.params["number"])
        self.assertTrue(comment.params["number"]["dynamic"])
        self.assertNotIn("default", comment.params["number"])       
        
        
        
    def test_doc_params_namespaced(self):

        parsed = self.process('''

        /**
         * {Boolean} Returns whether @x {core.Number} is bigger than @y {core.Number}. The optional @cache {core.Boolean?false} controls whether caching should be enabled.
         * Also see @extra {core.String | core.Array ?} which is normally pretty useless
         */

        ''')

        self.assertEqual(parsed.type, "script")
        self.assertEqual(isinstance(parsed.comments, list), True)
        self.assertEqual(len(parsed.comments), 1)

        comment = parsed.comments[0]

        self.assertEqual(comment.variant, "doc")
        self.assertEqual(comment.getHtml(), '<p>Returns whether <code class="param">x</code> is bigger than <code class="param">y</code>. The optional <code class="param">cache</code> controls whether caching should be enabled.\nAlso see <code class="param">extra</code> which is normally pretty useless</p>\n')
        self.assertEqual(comment.text, 'Returns whether x is bigger than y. The optional cache controls whether caching should be enabled.\nAlso see extra which is normally pretty useless')

        self.assertEqual(type(comment.params), dict)

        self.assertEqual(type(comment.params["x"]), dict)
        self.assertEqual(type(comment.params["y"]), dict)
        self.assertEqual(type(comment.params["cache"]), dict)
        self.assertEqual(type(comment.params["extra"]), dict)

        self.assertEqual(comment.params["x"]["type"][0]["name"], "core.Number")
        self.assertEqual(comment.params["y"]["type"][0]["name"], "core.Number")
        self.assertEqual(comment.params["cache"]["type"][0]["name"], "core.Boolean")
        self.assertEqual(comment.params["extra"]["type"][0]["name"], "core.String")
        self.assertEqual(comment.params["extra"]["type"][1]["name"], "core.Array")

        self.assertNotIn("optional", comment.params["x"])
        self.assertNotIn("optional", comment.params["y"])
        self.assertEqual(comment.params["cache"]["optional"], True)
        self.assertEqual(comment.params["extra"]["optional"], True)

        self.assertNotIn("default", comment.params["x"])
        self.assertNotIn("default", comment.params["y"])
        self.assertEqual(comment.params["cache"]["default"], "false")
        self.assertNotIn("default", comment.params["extra"])        
        
        
    def test_doc_params_lazytypes(self):

        parsed = self.process('''

        /**
         * {Boolean} Returns whether @x is bigger than @y.
         *
         * Parameters:
         *
         * - @x {Number}
         * - @y {Number}
         * - @cache {Boolean?false}
         * - @extra {String | Array ?}
         */

        ''')

        self.assertEqual(parsed.type, "script")
        self.assertEqual(isinstance(parsed.comments, list), True)
        self.assertEqual(len(parsed.comments), 1)

        comment = parsed.comments[0]

        self.assertEqual(comment.variant, "doc")
        self.assertEqual(comment.getHtml(), '<p>Returns whether <code class="param">x</code> is bigger than <code class="param">y</code>.</p>\n\n<p>Parameters:</p>\n\n<ul>\n<li><code class="param">x</code></li>\n<li><code class="param">y</code></li>\n<li><code class="param">cache</code></li>\n<li><code class="param">extra</code></li>\n</ul>\n')
        
        self.assertEqual(comment.text, 'Returns whether x is bigger than y.\n\nParameters:\n\n- x\n- y\n- cache\n- extra')
        
        self.assertEqual(type(comment.params), dict)

        self.assertEqual(type(comment.params["x"]), dict)
        self.assertEqual(type(comment.params["y"]), dict)
        self.assertEqual(type(comment.params["cache"]), dict)
        self.assertEqual(type(comment.params["extra"]), dict)

        self.assertEqual(comment.params["x"]["type"][0]["name"], "Number")
        self.assertEqual(comment.params["y"]["type"][0]["name"], "Number")
        self.assertEqual(comment.params["cache"]["type"][0]["name"], "Boolean")
        self.assertEqual(comment.params["extra"]["type"][0]["name"], "String")
        self.assertEqual(comment.params["extra"]["type"][1]["name"], "Array")

        self.assertNotIn("optional", comment.params["x"])
        self.assertNotIn("optional", comment.params["y"])
        self.assertEqual(comment.params["cache"]["optional"], True)
        self.assertEqual(comment.params["extra"]["optional"], True)

        self.assertNotIn("default", comment.params["x"])
        self.assertNotIn("default", comment.params["y"])
        self.assertEqual(comment.params["cache"]["default"], "false")
        self.assertNotIn("default", comment.params["extra"])
        
        
        
    def test_doc_params_firstloose(self):

        parsed = self.process('''

        /**
         * {Boolean} Returns whether @x {String ? 13} is bigger than @y.
         *
         * Parameters:
         *
         * - @x {Number}
         * - @y {Number}
         */

        ''')

        self.assertEqual(parsed.type, "script")
        self.assertEqual(isinstance(parsed.comments, list), True)
        self.assertEqual(len(parsed.comments), 1)

        comment = parsed.comments[0]

        self.assertEqual(comment.variant, "doc")
        self.assertEqual(comment.getHtml(), '''<p>Returns whether <code class="param">x</code> is bigger than <code class="param">y</code>.</p>\n\n<p>Parameters:</p>\n\n<ul>\n<li><code class="param">x</code></li>\n<li><code class="param">y</code></li>\n</ul>\n''')

        self.assertEqual(type(comment.params), dict)

        self.assertEqual(type(comment.params["x"]), dict)
        self.assertEqual(type(comment.params["y"]), dict)

        self.assertEqual(comment.params["x"]["type"][0]["name"], "Number")
        self.assertEqual(comment.params["y"]["type"][0]["name"], "Number")

        self.assertNotIn("optional", comment.params["x"])
        self.assertNotIn("optional", comment.params["y"])

        self.assertNotIn("default", comment.params["x"])
        self.assertNotIn("default", comment.params["y"])
        
        
    def test_doc_params_firstwin(self):

        parsed = self.process('''

        /**
         * {Boolean} Returns whether @x {Number ? 13} is bigger than @y.
         *
         * Parameters:
         *
         * - @x
         * - @y {Number}
         */

        ''')

        self.assertEqual(parsed.type, "script")
        self.assertEqual(isinstance(parsed.comments, list), True)
        self.assertEqual(len(parsed.comments), 1)

        comment = parsed.comments[0]

        self.assertEqual(comment.variant, "doc")
        self.assertEqual(comment.getHtml(), '<p>Returns whether <code class="param">x</code> is bigger than <code class="param">y</code>.</p>\n\n<p>Parameters:</p>\n\n<ul>\n<li><code class="param">x</code></li>\n<li><code class="param">y</code></li>\n</ul>\n')

        self.assertEqual(type(comment.params), dict)

        self.assertEqual(type(comment.params["x"]), dict)
        self.assertEqual(type(comment.params["y"]), dict)

        self.assertEqual(comment.params["x"]["type"][0]["name"], "Number")
        self.assertEqual(comment.params["y"]["type"][0]["name"], "Number")

        self.assertTrue(comment.params["x"]["optional"])
        self.assertNotIn("optional", comment.params["y"])

        self.assertEqual(comment.params["x"]["default"], "13")
        self.assertNotIn("default", comment.params["y"])
        
    
    def test_doc_params_maps(self):

        parsed = self.process('''

        /**
         * Additional arguments can be passed in via @options {Object?}:
         *
         * - @options.x {String}
         * - @options.y {Number}
         */

        ''')

        self.assertEqual(parsed.type, "script")
        self.assertEqual(isinstance(parsed.comments, list), True)
        self.assertEqual(len(parsed.comments), 1)

        comment = parsed.comments[0]

        self.assertEqual(comment.variant, "doc")
        self.assertEqual(comment.getHtml(), '<p>Additional arguments can be passed in via <code class="param">options</code>:</p>\n\n<ul>\n<li><code class="param">options.x</code></li>\n<li><code class="param">options.y</code></li>\n</ul>\n')

        self.assertEqual(type(comment.params), dict)

        self.assertEqual(type(comment.params["options"]), dict)

        self.assertEqual(type(comment.params["options"]["fields"]), dict)
        self.assertEqual(comment.params["options"]["type"][0]["name"], "Object")

        self.assertEqual(type(comment.params["options"]["fields"]["x"]), dict)
        self.assertEqual(type(comment.params["options"]["fields"]["y"]), dict)

        self.assertEqual(comment.params["options"]["fields"]["x"]["type"][0]["name"], "String")
        self.assertEqual(comment.params["options"]["fields"]["y"]["type"][0]["name"], "Number")


    def test_doc_params_maps_multi_levels(self):

        parsed = self.process('''

        /**
         * Additional arguments can be passed in via @options {Object?}:
         *
         * - @options {Object}
         *
         *   - @options.x {String}
         *   - @options.y {Number}
         *
         *   - @options.foo {Object}
         *
         *     - @options.foo.x {String}
         *     - @options.foo.y {Number}
         *
         */

        ''')

        self.assertEqual(parsed.type, "script")
        self.assertEqual(isinstance(parsed.comments, list), True)
        self.assertEqual(len(parsed.comments), 1)

        comment = parsed.comments[0]

        self.assertEqual(comment.variant, "doc")

        self.assertEqual(comment.getHtml(), '<p>Additional arguments can be passed in via <code class="param">options</code>:</p>\n\n<ul>\n<li><p><code class="param">options</code></p>\n\n<ul>\n<li><code class="param">options.x</code></li>\n<li><code class="param">options.y</code></li>\n<li><code class="param">options.foo</code></li>\n<li><code class="param">options.foo.x</code></li>\n<li><code class="param">options.foo.y</code></li>\n</ul></li>\n</ul>\n')

        self.assertEqual(type(comment.params), dict)

        self.assertEqual(type(comment.params["options"]), dict)

        self.assertEqual(type(comment.params["options"]["fields"]), dict)
        self.assertEqual(comment.params["options"]["type"][0]["name"], "Object")

        self.assertEqual(type(comment.params["options"]["fields"]["x"]), dict)
        self.assertEqual(type(comment.params["options"]["fields"]["y"]), dict)

        self.assertEqual(comment.params["options"]["fields"]["x"]["type"][0]["name"], "String")
        self.assertEqual(comment.params["options"]["fields"]["y"]["type"][0]["name"], "Number")

        self.assertEqual(type(comment.params["options"]["fields"]["foo"]), dict)
        self.assertEqual(comment.params["options"]["fields"]["foo"]["type"][0]["name"], "Object")

        self.assertEqual(type(comment.params["options"]["fields"]["foo"]["fields"]["x"]), dict)
        self.assertEqual(type(comment.params["options"]["fields"]["foo"]["fields"]["y"]), dict)

        self.assertEqual(comment.params["options"]["fields"]["foo"]["fields"]["x"]["type"][0]["name"], "String")
        self.assertEqual(comment.params["options"]["fields"]["foo"]["fields"]["y"]["type"][0]["name"], "Number")

    
    #
    # DOC COMMENTS :: MARKDOWN
    #
    
    def test_doc_markdown_formatting(self):

        parsed = self.process('''

        /**
         * This is some **important** text about *Jasy*.
         */
        docCommentCmd();

        ''')

        self.assertEqual(parsed[0].type, "semicolon")
        self.assertEqual(isinstance(parsed[0].comments, list), True)
        self.assertEqual(len(parsed[0].comments), 1)

        self.assertEqual(parsed[0].comments[0].variant, "doc")
        self.assertEqual(parsed[0].comments[0].getHtml(), "<p>This is some <strong>important</strong> text about <em>Jasy</em>.</p>\n")    
    
    def test_doc_markdown_quote(self):

        parsed = self.process('''

        /**
         * Items:
         * 
         * - Data
         *
         *     > This is a block quote
         */
        docCommentCmd();
         
         ''')

        self.assertEqual(parsed[0].type, "semicolon")
        self.assertEqual(isinstance(parsed[0].comments, list), True)
        self.assertEqual(len(parsed[0].comments), 1)

        self.assertEqual(parsed[0].comments[0].variant, "doc")
        self.assertEqual(parsed[0].comments[0].getHtml(), "<p>Items:</p>\n\n<ul>\n<li><p>Data</p>\n\n<blockquote>\n<p>This is a block quote</p>\n</blockquote></li>\n</ul>\n")

    
    def test_doc_markdown_smartypants(self):

        parsed = self.process('''

        /**
         * Text formatting with 'quotes' is pretty nice, too...
         *
         * It possible to use "different styles" here -- to improve clarity.
         *
         * Still it keeps code like `this.foo()` intact.
         *
         * It's also capable of detecting these things: "Joe's Restaurant".
         */
        docCommentCmd();

        ''')

        self.assertEqual(parsed[0].type, "semicolon")
        self.assertEqual(isinstance(parsed[0].comments, list), True)
        self.assertEqual(len(parsed[0].comments), 1)

        self.assertEqual(parsed[0].comments[0].variant, "doc")
        self.assertEqual(parsed[0].comments[0].getHtml(), "<p>Text formatting with &#39;quotes&#39; is pretty nice, too&hellip;</p>\n\n<p>It possible to use &ldquo;different styles&rdquo; here &ndash; to improve clarity.</p>\n\n<p>Still it keeps code like <code>this.foo()</code> intact.</p>\n\n<p>It&#39;s also capable of detecting these things: &ldquo;Joe&#39;s Restaurant&rdquo;.</p>\n")
    
    def test_doc_markdown_formatting_code(self):

        parsed = self.process('''

        /**
         * This is some example code:
         *     
         *     var name = 'jasy';
         */
        docCommentCmd();

        ''')

        self.assertEqual(parsed[0].type, "semicolon")
        self.assertEqual(isinstance(parsed[0].comments, list), True)
        self.assertEqual(len(parsed[0].comments), 1)

        self.assertEqual(parsed[0].comments[0].variant, "doc")
        self.assertEqual(parsed[0].comments[0].getHtml(), '<p>This is some example code:</p>\n\n<table class="highlighttable"><tr><td class="linenos"><div class="linenodiv"><pre>1</pre></div></td><td class="code"><div class="highlight"><pre><span class="kd">var</span> <span class="nx">name</span> <span class="o">=</span> <span class="s1">\'jasy\'</span><span class="p">;</span>\n</pre></div>\n</td></tr></table>\n')
    

    #
    # DOC COMMENTS :: CODE
    #

    def test_doc_markdown_code(self):

        parsed = self.process('''

        /**
         * Some code example:
         *
         *     if (this.isEnabled()) {
         *       self.callCommand("reload", true);
         *     }
         */
        docCommentCmd();

        ''')
        
        self.assertEqual(parsed[0].type, "semicolon")
        self.assertEqual(isinstance(parsed[0].comments, list), True)
        self.assertEqual(len(parsed[0].comments), 1)

        self.assertEqual(parsed[0].comments[0].variant, "doc")
        self.assertEqual(parsed[0].comments[0].getHtml(), '<p>Some code example:</p>\n\n<table class="highlighttable"><tr><td class="linenos"><div class="linenodiv"><pre>1\n2\n3</pre></div></td><td class="code"><div class="highlight"><pre><span class="k">if</span> <span class="p">(</span><span class="k">this</span><span class="p">.</span><span class="nx">isEnabled</span><span class="p">())</span> <span class="p">{</span>\n  <span class="nx">self</span><span class="p">.</span><span class="nx">callCommand</span><span class="p">(</span><span class="s2">"reload"</span><span class="p">,</span> <span class="kc">true</span><span class="p">);</span>\n<span class="p">}</span>\n</pre></div>\n</td></tr></table>\n')
        


        
    def test_doc_markdown_code_single_blockquote(self):

        parsed = self.process('''

        /**
         * Some code example:
         *
         *     self.callCommand("reload", true);
         */
        docCommentCmd();

        ''')

        self.assertEqual(parsed[0].type, "semicolon")
        self.assertEqual(isinstance(parsed[0].comments, list), True)
        self.assertEqual(len(parsed[0].comments), 1)

        self.assertEqual(parsed[0].comments[0].variant, "doc")
        self.assertEqual(parsed[0].comments[0].getHtml(), '<p>Some code example:</p>\n\n<table class="highlighttable"><tr><td class="linenos"><div class="linenodiv"><pre>1</pre></div></td><td class="code"><div class="highlight"><pre><span class="nx">self</span><span class="p">.</span><span class="nx">callCommand</span><span class="p">(</span><span class="s2">"reload"</span><span class="p">,</span> <span class="kc">true</span><span class="p">);</span>\n</pre></div>\n</td></tr></table>\n')    
        
        
    def test_doc_markdown_code_single_inline(self):

        parsed = self.process('''

        /**
         * Some code example: `self.callCommand("reload", true);`
         */
        docCommentCmd();

        ''')

        self.assertEqual(parsed[0].type, "semicolon")
        self.assertEqual(isinstance(parsed[0].comments, list), True)
        self.assertEqual(len(parsed[0].comments), 1)

        self.assertEqual(parsed[0].comments[0].variant, "doc")
        self.assertEqual(parsed[0].comments[0].getHtml(), '<p>Some code example: <code>self.callCommand(&quot;reload&quot;, true);</code></p>\n')            


    def test_doc_markdown_code_html(self):

        parsed = self.process('''

        /**
         * ## HTML example:
         *
         * ```html
         * <title>My Title</title>
         * <link rel="stylesheet" type="text/css" src="style.css"/>
         * <script type="text/javascript">alert("Loaded");</script>
         * ```
         */
        docCommentCmd();

        ''')

        self.assertEqual(parsed[0].type, "semicolon")
        self.assertEqual(isinstance(parsed[0].comments, list), True)
        self.assertEqual(len(parsed[0].comments), 1)

        self.assertEqual(parsed[0].comments[0].variant, "doc")
        self.assertEqual(parsed[0].comments[0].getHtml(), '<h2>HTML example:</h2>\n\n<table class="highlighttable"><tr><td class="linenos"><div class="linenodiv"><pre>1\n2\n3</pre></div></td><td class="code"><div class="highlight"><pre><span class="nt"><title></span>My Title<span class="nt"></title></span>\n<span class="nt"><link</span> <span class="na">rel=</span><span class="s">"stylesheet"</span> <span class="na">type=</span><span class="s">"text/css"</span> <span class="na">src=</span><span class="s">"style.css"</span><span class="nt">/></span>\n<span class="nt"><script </span><span class="na">type=</span><span class="s">"text/javascript"</span><span class="nt">></span><span class="nx">alert</span><span class="p">(</span><span class="s2">"Loaded"</span><span class="p">);</span><span class="nt"></script></span>\n</pre></div>\n</td></tr></table>\n')




if __name__ == '__main__':
    logging.getLogger().setLevel(logging.ERROR)
    suite = unittest.TestLoader().loadTestsFromTestCase(Tests)
    unittest.TextTestRunner(verbosity=2).run(suite)      
    

########NEW FILE########
__FILENAME__ = compressor
#!/usr/bin/env python3

import sys, os, unittest, logging

# Extend PYTHONPATH with local 'lib' folder
if __name__ == "__main__":
    jasyroot = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]), os.pardir, os.pardir, os.pardir, os.pardir))
    sys.path.insert(0, jasyroot)
    print("Running from %s..." % jasyroot)

import jasy.js.parse.Parser as Parser
import jasy.js.output.Compressor as Compressor


class Tests(unittest.TestCase):

    def process(self, code):
        return Compressor.Compressor().compress(Parser.parse(code))
        
    def test_and(self):
        self.assertEqual(self.process('x && y'), 'x&&y;')

    def test_arithm(self):
        self.assertEqual(self.process('i++; j-- + 3;'), 'i++;j--+3;')

    def test_arithm_increment(self):
        self.assertEqual(self.process('x++ + y; x + ++y; x++ + ++y'), 'x++ +y;x+ ++y;x++ + ++y;')

    def test_arithm_decrement(self):
        self.assertEqual(self.process('x-- - y; x - --y; x-- - --y'), 'x-- -y;x- --y;x-- - --y;')

    def test_array_number(self):
        self.assertEqual(self.process('var data1 = [ 1, 2, 3 ];'), 'var data1=[1,2,3];')

    def test_array_string(self):
        self.assertEqual(self.process('var data2 = [ "hello" ];'), 'var data2=["hello"];')

    def test_array_sparse(self):
        self.assertEqual(self.process('var data3 = [ 1, , , 4, , 6 ];'), 'var data3=[1,,,4,,6];')
        
    def test_array_comprehension(self):
        self.assertEqual(self.process('exec([i for (i in obj) if (i > 3)]);'), 'exec([i for(i in obj)if(i>3)]);')

    def test_bitwise_and(self):
        self.assertEqual(self.process('z = x & y;'), 'z=x&y;')

    def test_block_separate(self):
        self.assertEqual(self.process('{ x = 1; y = 2; }'), '{x=1;y=2}')

    def test_block_empty(self):
        self.assertEqual(self.process('if (true) {}'), 'if(true){}')

    def test_call_singlearg(self):
        self.assertEqual(self.process('hello("hello world");'), 'hello("hello world");')

    def test_call_multiargs(self):
        self.assertEqual(self.process('multi(1, 2, 3);'), 'multi(1,2,3);')

    def test_call_destruct(self):
        self.assertEqual(self.process('[a, b] = f();'), '[a,b]=f();')

    def test_const(self):
        self.assertEqual(self.process('const foo = 3;'), 'const foo=3;')

    def test_const_multi(self):
        self.assertEqual(self.process('const foo = 3, bar = 4;'), 'const foo=3,bar=4;')

    def test_continue(self):
        self.assertEqual(self.process('while(x) { continue; }'), 'while(x){continue}')

    def test_continue_label(self):
        self.assertEqual(self.process('dist: while(y) { continue dist; }'), 'dist:while(y){continue dist};')

    def test_declaration(self):
        self.assertEqual(self.process('var a, b=5, c;'), 'var a,b=5,c;')

    def test_declaration_destruct(self):
        self.assertEqual(self.process('var [d, e] = destruct(), x;'), 'var [d,e]=destruct(),x;')

    def test_delete(self):
        self.assertEqual(self.process('delete obj.key;'), 'delete obj.key;')

    def test_destruct_assign(self):
        self.assertEqual(self.process('[first, second] = [second, first];'), '[first,second]=[second,first];')

    def test_destruct_for(self):
        self.assertEqual(self.process('for (var [name, value] in Iterator(obj)) {}'), 'for(var [name,value] in Iterator(obj)){}')

    def test_destruct_for_let(self):
        self.assertEqual(self.process('for (let [name, value] in Iterator(obj)) {}'), 'for(let [name,value] in Iterator(obj)){}')

    def test_do_while(self):
        self.assertEqual(self.process('do{ something; } while(true);'), 'do{something}while(true);')

    def test_dot(self):
        self.assertEqual(self.process('parent.child.weight;'), 'parent.child.weight;')

    def test_expression_closure(self):
        self.assertEqual(self.process('node.onclick = function(x) x * x'), 'node.onclick=function(x)x*x;')

    def test_for_multiinit(self):
        self.assertEqual(self.process('for(x = 0, l = foo.length; x < l; x++) {}'), 'for(x=0,l=foo.length;x<l;x++){}')

    def test_for_simple(self):
        self.assertEqual(self.process('for (var i=0; i<100; i++) {}'), 'for(var i=0;i<100;i++){}')

    def test_for_each(self):
        self.assertEqual(self.process('for each (var item in obj) { sum += item; }'), 'for each(var item in obj){sum+=item}')

    def test_for_in(self):
        self.assertEqual(self.process('for (var key in map) { }'), 'for(var key in map){}')

    def test_function_expressed(self):
        self.assertEqual(self.process('x = function() { i++ };'), 'x=function(){i++};')

    def test_function_declared(self):
        self.assertEqual(self.process('function y() { i++ }'), 'function y(){i++}')

    def test_generator_expression(self):
        self.assertEqual(self.process('handleResults(i for (i in obj));'), 'handleResults(i for(i in obj));')
        
    def test_generator_expression_guard(self):
        self.assertEqual(self.process('handleResults(i for (i in obj) if (i > 3));'), 'handleResults(i for(i in obj)if(i>3));')

    def test_getter(self):
        self.assertEqual(self.process('var obj={get name() { return myName; }};'), 'var obj={get name(){return myName}};')

    def test_setter(self):
        self.assertEqual(self.process('var obj={set name(value) { myName = value; }};'), 'var obj={set name(value){myName=value}};')

    def test_hook_assign(self):
        self.assertEqual(self.process('x = test1 ? case1 = 1 : case2 = 2;'), 'x=test1?case1=1:case2=2;')

    def test_hook_left_child(self):
        self.assertEqual(self.process('test1 ? test2 ? res1 : res2 : res3;'), 'test1?test2?res1:res2:res3;')

    def test_hook_right_child(self):
        self.assertEqual(self.process('test1 ? res1 : test2 ? res2 : res3;'), 'test1?res1:test2?res2:res3;')

    def test_hook_simple(self):
        self.assertEqual(self.process('test1 ? res1 : res2;'), 'test1?res1:res2;')

    def test_hook_two_children(self):
        self.assertEqual(self.process('test1 ? test2 ? res1 : res2 : test3 ? res3 : res4;'), 'test1?test2?res1:res2:test3?res3:res4;')

    def test_if_else_noblocks(self):
        self.assertEqual(self.process('if (foo) hello(); else quit();'), 'if(foo)hello();else quit();')
        
    def test_if_else(self):
        self.assertEqual(self.process('if (bar) { hello(); } else { quit(); }'), 'if(bar){hello()}else{quit()}')

    def test_if_else_if_noblocks(self):
        self.assertEqual(self.process('if (foo) hello(); else if (x) quit();'), 'if(foo)hello();else if(x)quit();')

    def test_if_else_if(self):
        self.assertEqual(self.process('if (bar) { hello(); } else if (x) { quit(); }'), 'if(bar){hello()}else if(x){quit()}')

    def test_if_empty(self):
        self.assertEqual(self.process('if(foo && bar) {}'), 'if(foo&&bar){}')

    def test_if_not_else(self):
        self.assertEqual(self.process('if (!bar) { first; } else { second; }'), 'if(!bar){first}else{second}')

    def test_if_not(self):
        self.assertEqual(self.process('if (!bar) { first; }'), 'if(!bar){first}')

    def test_if_noblock(self):
        self.assertEqual(self.process('if (foo) hello();'), 'if(foo)hello();')

    def test_if(self):
        self.assertEqual(self.process('if (bar) { hello(); }'), 'if(bar){hello()}')

    def test_in(self):
        self.assertEqual(self.process('"foo" in obj;'), '"foo"in obj;')

    def test_increment_prefix(self):
        self.assertEqual(self.process('++i;'), '++i;')

    def test_increment_postfix(self):
        self.assertEqual(self.process('i++;'), 'i++;')

    def test_index(self):
        self.assertEqual(self.process('list[12];'), 'list[12];')

    def test_let_definition(self):
        self.assertEqual(self.process('if (x > y) { let gamma = 12.7 + y; }'), 'if(x>y){let gamma=12.7+y}')
        
    def test_let_expression(self):
        self.assertEqual(self.process('write(let(x = x + 10, y = 12) x + y + "<br>");'), 'write(let(x=x+10,y=12)x+y+"<br>");')

    def test_let_statement(self):
        self.assertEqual(self.process('let (x = x+10, y = 12) { print(x+y); }'), 'let(x=x+10,y=12){print(x+y)}')

    def test_new(self):
        self.assertEqual(self.process('var obj = new Object;'), 'var obj=new Object;')

    def test_new_args(self):
        self.assertEqual(self.process('var arr = new Array(1,2,3);'), 'var arr=new Array(1,2,3);')

    def test_new_args_empty(self):
        self.assertEqual(self.process('var obj = new Object();'), 'var obj=new Object;')
        
    def test_new_args_empty_dot_call(self):
        self.assertEqual(self.process('var x = new Date().doSomething();'), 'var x=new Date().doSomething();')

    def test_new_args_empty_dot_call_paren(self):
        self.assertEqual(self.process('var x = (new Date).doSomething();'), 'var x=(new Date).doSomething();')

    def test_new_dot_call(self):
        self.assertEqual(self.process('var x = new Date(true).doSomething();'), 'var x=new Date(true).doSomething();')

    def test_number_float(self):
        self.assertEqual(self.process('4.3;'), '4.3;')

    def test_number_float_short(self):
        self.assertEqual(self.process('.3;'), '.3;')

    def test_number_float_zero_prefix(self):
        self.assertEqual(self.process('0.5;'), '.5;')

    def test_number_hex(self):
        self.assertEqual(self.process('0xF0;'), '0xF0;')

    def test_number_int(self):
        self.assertEqual(self.process('3 + 6.0;'), '3+6;')
            
    def test_number_max(self):
        self.assertEqual(self.process('1.7976931348623157e+308;'), '1.7976931348623157e+308;')

    def test_number_min(self):
        self.assertEqual(self.process('5e-324;'), '5e-324;')            

    def test_tofixed(self):
        self.assertEqual(self.process('0..toFixed();'), '0..toFixed();')

    def test_object_init(self):
        self.assertEqual(self.process('var x = { vanilla : "vanilla", "default" : "enclosed" };'), 'var x={vanilla:"vanilla","default":"enclosed"};')

    def test_object_init_trail(self):
        self.assertEqual(self.process('var x = { vanilla : "vanilla", };'), 'var x={vanilla:"vanilla"};')

    def test_or(self):
        self.assertEqual(self.process('x || y'), 'x||y;')

    def test_regexp(self):
        self.assertEqual(self.process('var x = /[a-z]/g.exec(foo);'), 'var x=/[a-z]/g.exec(foo);')

    def test_regexp_in_array(self):
        self.assertEqual(self.process('var x = [/[a-z]/];'), 'var x=[/[a-z]/];')

    def test_return(self):
        self.assertEqual(self.process('function y() { return 1; }'), 'function y(){return 1}')

    def test_return_empty(self):
        self.assertEqual(self.process('function x() { return; }'), 'function x(){return}')

    def test_return_array(self):
        self.assertEqual(self.process('function z() { return [ 1, 2, 3 ]; }'), 'function z(){return[1,2,3]}')

    def test_strict(self):
        self.assertEqual(self.process('function test() { "use strict"; var x = 4+5; }'), 'function test(){"use strict";var x=4+5}')

    def test_string_escape(self):
        self.assertEqual(self.process(r'var x="abc\ndef";'), r'var x="abc\ndef";')

    def test_string(self):
        self.assertEqual(self.process(r'var x = "hello" + "world";'), r'var x="hello"+"world";')

    def test_string_quotes(self):
        self.assertEqual(self.process(r'var x = "hello" + " \"world\"";'), r'var x="hello"+" \"world\"";')

    def test_switch(self):
        self.assertEqual(self.process('switch(x) { case 1: case 2: r = 2; case 3: r = 3; break; default: r = null; }'), 'switch(x){case 1:case 2:r=2;case 3:r=3;break;default:r=null}')

    def test_throw(self):
        self.assertEqual(self.process('throw new Error("Ooops");'), 'throw new Error("Ooops");')            

    def test_trycatch_guard(self):
        self.assertEqual(self.process('try{ x=1; } catch (ex1 if ex1 instanceof MyError) { alert(ex1); } catch (ex2) { alert(ex2); }'), 'try{x=1}catch(ex1 if ex1 instanceof MyError){alert(ex1)}catch(ex2){alert(ex2)}')

    def test_trycatch(self):
        self.assertEqual(self.process('try{ x=1; } catch (ex) { alert(ex); }'), 'try{x=1}catch(ex){alert(ex)}')

    def test_unary(self):
        self.assertEqual(self.process('var x = -1 * +3;'), 'var x=-1*+3;')

    def test_unicode(self):
        # Should be allowed in UTF-8 documents
        self.assertEqual(self.process(r'var x = "\u00A9 Netscape Communications";'), r'var x="© Netscape Communications";')

        # Low Unicode escapes are encoded as Unicode text
        ret = self.process(r'"[\t\n\u000b\f\r \u00a0]"')
        self.assertEqual(ret, r'"[\t\n\u000b\f\r  ]";')
        
        # High Unicode escapes are encoded as ASCII with escape sequences
        ret = self.process(r'"[\t\n\u000b\f\r \u00a0\u1680\u180e\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u202f\u205f\u3000\u2028\u2029\ufeff]"')
        self.assertEqual(ret, r'"[\t\n\u000b\f\r \u00a0\u1680\u180e\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u202f\u205f\u3000\u2028\u2029\ufeff]";')

        ret = self.process(r'var x="\u2028", y="\u2029"')
        self.assertEqual(ret, r'var x="\u2028",y="\u2029";')

        ret = self.process(r'var x={"\u2028":"u2028","\u2029":"u2029"}')
        self.assertEqual(ret, r'var x={"\u2028":"u2028","\u2029":"u2029"};')

    def test_while_comma_condition(self):
        self.assertEqual(self.process('while (x=1, x<3){ x++; }'), 'while(x=1,x<3){x++}')            

    def test_while(self):
        self.assertEqual(self.process('while (true) { x++; }'), 'while(true){x++}')
                     
        

if __name__ == '__main__':
    logging.getLogger().setLevel(logging.ERROR)
    suite = unittest.TestLoader().loadTestsFromTestCase(Tests)
    unittest.TextTestRunner(verbosity=2).run(suite)


########NEW FILE########
__FILENAME__ = deadcode
#!/usr/bin/env python3

import sys, os, unittest, logging

# Extend PYTHONPATH with local 'lib' folder
if __name__ == "__main__":
    jasyroot = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]), os.pardir, os.pardir, os.pardir, os.pardir))
    sys.path.insert(0, jasyroot)
    print("Running from %s..." % jasyroot)

import jasy.js.parse.Parser as Parser
import jasy.js.parse.ScopeScanner as ScopeScanner
import jasy.js.output.Compressor as Compressor
import jasy.js.clean.Unused as Unused
import jasy.js.clean.DeadCode as DeadCode


class Tests(unittest.TestCase):

    def process(self, code):
        node = Parser.parse(code)
        DeadCode.cleanup(node)
        return Compressor.Compressor().compress(node)

    def test_if_trueish(self):
        self.assertEqual(self.process('if (true) x++;'), 'x++;')
        
    def test_if_falsy(self):
        self.assertEqual(self.process('if (false) x++;'), '')

    def test_if_equal_true(self):
        self.assertEqual(self.process('if (2==2) x++;'), 'x++;')
        
    def test_if_equal_false(self):
        self.assertEqual(self.process('if (2==3) x++;'), '')

    def test_if_identical_true(self):
        self.assertEqual(self.process('if (2===2) x++;'), 'x++;')

    def test_if_identical_false(self):
        self.assertEqual(self.process('if (2===3) x++;'), '')
        
    def test_if_not_trueish(self):
        self.assertEqual(self.process('if (!true) x++;'), '')
        
    def test_if_not_falsy(self):
        self.assertEqual(self.process('if (!false) x++;'), 'x++;')
        
    def test_if_trueish_and_trueish(self):
        self.assertEqual(self.process('if (true && true) x++;'), 'x++;')

    def test_if_falsy_and_falsy(self):
        self.assertEqual(self.process('if (false && false) x++;'), '')
        
    def test_if_trueish_and_falsy(self):
        self.assertEqual(self.process('if (true && false) x++;'), '')

    def test_if_falsy_and_trueish(self):
        self.assertEqual(self.process('if (false && true) x++;'), '')
        
    def test_if_unknown_and_falsy(self):
        self.assertEqual(self.process('if (x && false) x++;'), '')

    def test_if_unknown_and_trueish(self):
        self.assertEqual(self.process('if (x && true) x++;'), 'if(x&&true)x++;')
        
    def test_if_falsy_and_unknown(self):
        self.assertEqual(self.process('if (false && x) x++;'), '')

    def test_if_trueish_and_unknown(self):
        self.assertEqual(self.process('if (true && x) x++;'), 'if(true&&x)x++;')

    def test_if_trueish_or_trueish(self):
        self.assertEqual(self.process('if (true || true) x++;'), 'x++;')

    def test_if_falsy_or_falsy(self):
        self.assertEqual(self.process('if (false || false) x++;'), '')

    def test_if_trueish_or_falsy(self):
        self.assertEqual(self.process('if (true || false) x++;'), 'x++;')

    def test_if_falsy_or_trueish(self):
        self.assertEqual(self.process('if (false || true) x++;'), 'x++;')

    def test_if_unknown_or_falsy(self):
        self.assertEqual(self.process('if (x || false) x++;'), 'if(x||false)x++;')

    def test_if_unknown_or_trueish(self):
        self.assertEqual(self.process('if (x || true) x++;'), 'if(x||true)x++;')

    def test_if_falsy_or_unknown(self):
        self.assertEqual(self.process('if (false || x) x++;'), 'if(false||x)x++;')

    def test_if_trueish_or_unknown(self):
        self.assertEqual(self.process('if (true || x) x++;'), 'if(true||x)x++;')


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.ERROR)
    suite = unittest.TestLoader().loadTestsFromTestCase(Tests)
    unittest.TextTestRunner(verbosity=2).run(suite)    

########NEW FILE########
__FILENAME__ = inject
#!/usr/bin/env python3

import sys, os, unittest, logging

# Extend PYTHONPATH with local 'lib' folder
if __name__ == "__main__":
    jasyroot = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]), os.pardir, os.pardir, os.pardir, os.pardir))
    sys.path.insert(0, jasyroot)
    print("Running from %s..." % jasyroot)

import jasy.core.Permutation as Permutation

import jasy.js.parse.Parser as Parser
import jasy.js.parse.ScopeScanner as ScopeScanner
import jasy.js.output.Compressor as Compressor
import jasy.js.clean.Permutate as Permutate


class Tests(unittest.TestCase):

    def process(self, code, contextId=""):
        node = Parser.parse(code)
        permutation = Permutation.Permutation({
            'debug': False,
            'legacy': True,
            'engine': 'webkit',
            'version': 3,
            'fullversion': 3.11
        })
        Permutate.patch(node, permutation)
        return Compressor.Compressor().compress(node)    
    
    
    def test_get(self):
        self.assertEqual(self.process(
            'var engine = jasy.Env.getValue("engine");'),
            'var engine="webkit";'
        )

    def test_if_isset(self):
        self.assertEqual(self.process(
            '''
            if (jasy.Env.isSet("debug", true)) {
                var x = 1;
            }
            '''),
            'if(false){var x=1}'
        )        

    def test_isset_bool_false(self):
        self.assertEqual(self.process(
            'var debug = jasy.Env.isSet("debug", true);'),
            'var debug=false;'
        )             
        
    def test_isset_bool_shorthand_false(self):
        self.assertEqual(self.process(
            'var debug = jasy.Env.isSet("debug");'),
            'var debug=false;'
        )
        
    def test_isset_bool_true(self):
        self.assertEqual(self.process(
            'var legacy = jasy.Env.isSet("legacy", true);'),
            'var legacy=true;'
        )
        
    def test_isset_bool_shorthand_true(self):
        self.assertEqual(self.process(
            'var legacy = jasy.Env.isSet("legacy");'),
            'var legacy=true;'
        )             

    def test_isset_typediff(self):
        self.assertEqual(self.process(
            'var legacy = jasy.Env.isSet("legacy", "foo");'),
            'var legacy=false;'
        )

    def test_isset_lookup(self):
        self.assertEqual(self.process(
            'var legacy = jasy.Env.isSet("legacy", x);'),
            'var legacy=jasy.Env.isSet("legacy",x);'
        )        
        
    def test_isset_int_true(self):
        self.assertEqual(self.process(
            'var recent = jasy.Env.isSet("version", 3);'),
            'var recent=true;'
        )             

    def test_isset_int_false(self):
        self.assertEqual(self.process(
            'var recent = jasy.Env.isSet("version", 5);'),
            'var recent=false;'
        )

    def test_isset_float_true(self):
        self.assertEqual(self.process(
            'var buggy = jasy.Env.isSet("fullversion", 3.11);'),
            'var buggy=true;'
        )

    def test_isset_float_false(self):
        self.assertEqual(self.process(
            'var buggy = jasy.Env.isSet("fullversion", 3.2);'),
            'var buggy=false;'
        )           
        
    def test_isset_str_single(self):
        self.assertEqual(self.process(
            'var modern = jasy.Env.isSet("engine", "webkit");'),
            'var modern=true;'
        )
        
    def test_isset_str_multi(self):
        self.assertEqual(self.process(
            'var modern = jasy.Env.isSet("engine", "gecko|webkit");'),
            'var modern=true;'
        )
        
    def test_isset_str_multilong(self):
        self.assertEqual(self.process(
            'var modern = jasy.Env.isSet("engine", "gecko|webkitbrowser");'),
            'var modern=false;'
        )            

    def test_select(self):
        self.assertEqual(self.process(
            '''
            var prefix = jasy.Env.select("engine", {
              webkit: "Webkit",
              gecko: "Moz",
              trident: "ms"
            });
            '''),
            'var prefix="Webkit";'
        )

    def test_select_notfound(self):
        self.assertEqual(self.process(
            '''
            var prefix = jasy.Env.select("engine", {
              gecko: "Moz",
              trident: "ms"
            });            
            '''),
            'var prefix=jasy.Env.select("engine",{gecko:"Moz",trident:"ms"});'
        )        
        
    def test_select_default(self):
        self.assertEqual(self.process(
            '''
            var prefix = jasy.Env.select("engine", {
              gecko: "Moz",
              trident: "ms",
              "default": ""
            });            
            '''),
            'var prefix="";'
        )

    def test_select_multi(self):
        self.assertEqual(self.process(
            '''
            var prefix = jasy.Env.select("engine", {
              "webkit|khtml": "Webkit",
              trident: "ms",
            });            
            '''),
            'var prefix="Webkit";'
        )             


    
if __name__ == '__main__':
    logging.getLogger().setLevel(logging.ERROR)
    suite = unittest.TestLoader().loadTestsFromTestCase(Tests)
    unittest.TextTestRunner(verbosity=2).run(suite)
    

########NEW FILE########
__FILENAME__ = localvariables
#!/usr/bin/env python3

import sys, os, unittest, logging

# Extend PYTHONPATH with local 'lib' folder
if __name__ == "__main__":
    jasyroot = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]), os.pardir, os.pardir, os.pardir, os.pardir))
    sys.path.insert(0, jasyroot)
    print("Running from %s..." % jasyroot)

import jasy.js.parse.Parser as Parser
import jasy.js.parse.ScopeScanner as ScopeScanner
import jasy.js.output.Compressor as Compressor
import jasy.js.optimize.LocalVariables as LocalVariables



class Tests(unittest.TestCase):

    def process(self, code):
        node = Parser.parse(code)
        ScopeScanner.scan(node)
        LocalVariables.optimize(node)
        return Compressor.Compressor().compress(node)

    def test_basic(self):
        self.assertEqual(self.process(
            'function test(para1, para2) { var result = para1 + para2; return result; }'), 
            'function test(c,b){var a=c+b;return a}'
        )

    def test_args(self):
        self.assertEqual(self.process(
            '''
            function wrapper(obj, foo, hello) { 
              obj[foo]().hello; 
            }
            '''), 
            'function wrapper(a,b,c){a[b]().hello}'
        )

    def test_accessor_names(self):
        self.assertEqual(self.process(
          '''
          function outer(alpha, beta, gamma) 
          { 
            function inner() {} 
            var result = alpha * beta + gamma; 
            var doNot = result.alpha.beta.gamma; 
            return result * outer(alpha, beta, gamma); 
          }
          '''), 
          'function outer(d,c,b){function e(){}var a=d*c+b;var f=a.alpha.beta.gamma;return a*outer(d,c,b)}'
        )
        
    def test_bind(self):
        self.assertEqual(self.process(
            '''
            function bind(func, self, varargs) 
            { 
              return this.create(func, { 
                self : self, 
                args : null 
              }); 
            };
            '''),
            'function bind(b,a,c){return this.create(b,{self:a,args:null})};'
        )

    def test_closure(self):
        self.assertEqual(self.process(
            '''
            (function(global)
            {
              var foo;
              var bar = function()
              {
                var baz = foo;

              }
            })(this);
            '''),
            '(function(b){var a;var c=function(){var b=a}})(this);'
        )

    def test_conflict_generatedname(self):
        self.assertEqual(self.process(
            '''
            function wrapper()
            {
              var first=4;
              var a=5;
            }
            '''),
            'function wrapper(){var a=4;var b=5}'
        )

    def test_conflict_param_var(self):
        self.assertEqual(self.process(
            '''
            function x(config){
              var config = 3;
            }
            '''),
            'function x(a){var a=3}'
        )

    def test_conflict_same_name(self):
        self.assertEqual(self.process(
            '''
            function wrapper()
            {
              var first=4;
              var first=5;
            }
            '''),
            'function wrapper(){var a=4;var a=5}'
        )

    def test_declaration(self):
        self.assertEqual(self.process(
            '''
            function wrapper()
            {
              var first, second=5, third;
              var [desFirst, desSecond]=destruct(), after;
            }
            '''),
            'function wrapper(){var e,d=5,c;var [b,a]=destruct(),f}'
        )

    def test_exception_catchvar(self):
        self.assertEqual(self.process(
            '''
            function wrapper()
            {
              var x = 1, y = x+2;
              try
              {
                something();
              }
              catch(ex)
              {
                var inCatch = 3;
                alert(ex);
              }
            }
            '''),
            'function wrapper(){var a=1,c=a+2;try{something()}catch(b){var d=3;alert(b)}}'
        )

    def test_exception(self):
        self.assertEqual(self.process(
            '''
            function wrapper(param1)
            {
              var b = "hello";

              try{
                access.an.object[param1];

              } 
              catch(except)
              {
                alert(except + param1)
              }
            }            
            '''),
            'function wrapper(a){var c="hello";try{access.an.object[a]}catch(b){alert(b+a)}}'
        )

    def test_function(self):
        self.assertEqual(self.process(
            '''
            (function(global)
            {
              var x = doScrollCheck();
              function doScrollCheck() {
                doScrollCheck();
              }
            })(window);
            '''),
            '(function(c){var b=a();function a(){a()}})(window);'
        )

    def test_inline_access(self):
        self.assertEqual(self.process(
            '''
            function wrapper()
            {
              var d, a=d;
            }
            '''),
            'function wrapper(){var a,b=a}'
        )

    def test_let_definition(self):
        self.assertEqual(self.process(
            '''
            function wrapper()
            {
              if (x > y) {  
                let gamma = 12.7 + y;  
                i = gamma * x;  
              } 
            }
            '''),
            'function wrapper(){if(x>y){let a=12.7+y;i=a*x}}'
        )

    def test_let_expression(self):
        self.assertEqual(self.process(
            r'''
            function wrapper()
            {
              var x = 5;  
              var y = 0;  
              document.write(let(x = x + 10, y = 12) x + y + "<br>\n");  
              document.write(x+y + "<br>\n");  
            }            
            '''),
            r'function wrapper(){var a=5;var b=0;document.write(let(a=a+10,b=12)a+b+"<br>\n");document.write(a+b+"<br>\n")}'
        )

    def test_let_statement(self):
        self.assertEqual(self.process(
            r'''
            function wrapper()
            {
              var x = 5;
              var y = 0;

              let (x = x+10, y = 12, z=3) {
                print(x+y+z + "\n");
              }

              print((x + y) + "\n");
            }
            '''),
            r'function wrapper(){var a=5;var b=0;let(a=a+10,b=12,c=3){print(a+b+c+"\n")}print((a+b)+"\n")}'
        )
        
    def test_reuse_different(self):
        self.assertEqual(self.process(
            '''
            function run()
            {
              var first = function() {
                var inFirst = 1;
              };

              var second = function() {
                var inSecond = 2;
              };

            }
            '''),
            'function run(){var b=function(){var a=1};var a=function(){var a=2}}'
        )

    def test_reuse_names(self):
        self.assertEqual(self.process(
            '''
            function run()
            {
              var first = function() {
                var a = 1;
              };

              var second = function() {
                var a = 2;
              };

            }
            '''),
            'function run(){var b=function(){var a=1};var a=function(){var a=2}}'
        )



if __name__ == '__main__':
    logging.getLogger().setLevel(logging.ERROR)
    suite = unittest.TestLoader().loadTestsFromTestCase(Tests)
    unittest.TextTestRunner(verbosity=2).run(suite)

########NEW FILE########
__FILENAME__ = meta
#!/usr/bin/env python3

import sys, os, unittest, logging

# Extend PYTHONPATH with local 'lib' folder
if __name__ == "__main__":
    jasyroot = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]), os.pardir, os.pardir, os.pardir, os.pardir))
    sys.path.insert(0, jasyroot)
    print("Running from %s..." % jasyroot)

import jasy.js.parse.Parser as Parser
from jasy.js.MetaData import MetaData

        
class Tests(unittest.TestCase):

    def process(self, code):
        tree = Parser.parse(code)
        meta = MetaData(tree)
        return meta
        
        
    def test_other(self):
    
        meta = self.process('''
    
        /**
         * Hello World
         *
         * #deprecated #public #use(future) #use(current)
         */
    
        ''')
    
        self.assertIsInstance(meta, MetaData)
        self.assertEqual(meta.name, None)
        self.assertIsInstance(meta.requires, set)
        self.assertIsInstance(meta.optionals, set)
        self.assertIsInstance(meta.breaks, set)
        self.assertIsInstance(meta.assets, set)
        self.assertEqual(len(meta.requires), 0)
        self.assertEqual(len(meta.optionals), 0)
        self.assertEqual(len(meta.breaks), 0)
        self.assertEqual(len(meta.assets), 0)
        
        
    def test_name(self):

        meta = self.process('''

        /**
         * Hello World
         *
         * #name(my.main.Class)
         */

        ''')

        self.assertIsInstance(meta, MetaData)
        self.assertEqual(meta.name, "my.main.Class")
        self.assertIsInstance(meta.requires, set)
        self.assertIsInstance(meta.optionals, set)
        self.assertIsInstance(meta.breaks, set)
        self.assertIsInstance(meta.assets, set)
        self.assertEqual(len(meta.requires), 0)
        self.assertEqual(len(meta.optionals), 0)
        self.assertEqual(len(meta.breaks), 0)
        self.assertEqual(len(meta.assets), 0)
        
        
    def test_classes(self):

        meta = self.process('''

        /**
         * Hello World
         *
         * #require(my.other.Class)
         * #optional(no.dep.to.Class)
         * #break(depedency.to.Class)
         */

        ''')

        self.assertIsInstance(meta, MetaData)
        self.assertEqual(meta.name, None)
        self.assertIsInstance(meta.requires, set)
        self.assertIsInstance(meta.optionals, set)
        self.assertIsInstance(meta.breaks, set)
        self.assertIsInstance(meta.assets, set)
        self.assertEqual(len(meta.requires), 1)
        self.assertEqual(len(meta.optionals), 1)
        self.assertEqual(len(meta.breaks), 1)
        self.assertEqual(len(meta.assets), 0)
        self.assertEqual(meta.requires, set(["my.other.Class"]))
        self.assertEqual(meta.breaks, set(["depedency.to.Class"]))
        self.assertEqual(meta.optionals, set(["no.dep.to.Class"]))


    def test_assets(self):

        meta = self.process('''

        /**
         * Hello World
         *
         * #asset(projectx/*)
         * #asset(projectx/some/local/url.png)
         * #asset(icons/*post/home.png)
         */

        ''')

        self.assertIsInstance(meta, MetaData)
        self.assertEqual(meta.name, None)
        self.assertIsInstance(meta.requires, set)
        self.assertIsInstance(meta.optionals, set)
        self.assertIsInstance(meta.breaks, set)
        self.assertIsInstance(meta.assets, set)
        self.assertEqual(len(meta.requires), 0)
        self.assertEqual(len(meta.optionals), 0)
        self.assertEqual(len(meta.breaks), 0)
        self.assertEqual(len(meta.assets), 3)
        self.assertEqual(meta.assets, set(["projectx/*", "projectx/some/local/url.png", "icons/*post/home.png"]))
        
        
        
    def test_asset_escape(self):

        meta = self.process('''

        /**
         * Hello World
         *
         * #asset(icons/*\/home.png)
         */

        ''')

        self.assertIsInstance(meta, MetaData)
        
        # Test unescaping
        self.assertEqual(meta.assets, set(["icons/*/home.png"]))
        
        
    
    def test_structured(self):

        meta = self.process('''

        (function(global) {
        
          global.my.Class = function() {
          
            /**
             * #asset(projectx/some/local/url.png)
             */
            var uri = core.io.Asset.toUri("projectx/some/local/url.png");
            
          };
        
        })(this);

        ''')

        self.assertIsInstance(meta, MetaData)
        self.assertEqual(meta.assets, set(["projectx/some/local/url.png"]))        



if __name__ == '__main__':
    logging.getLogger().setLevel(logging.ERROR)
    suite = unittest.TestLoader().loadTestsFromTestCase(Tests)
    unittest.TextTestRunner(verbosity=2).run(suite)
########NEW FILE########
__FILENAME__ = privates
#!/usr/bin/env python3

import sys, os, unittest, logging

# Extend PYTHONPATH with local 'lib' folder
if __name__ == "__main__":
    jasyroot = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]), os.pardir, os.pardir, os.pardir, os.pardir))
    sys.path.insert(0, jasyroot)
    print("Running from %s..." % jasyroot)

import jasy.js.parse.Parser as Parser
import jasy.js.output.Compressor as Compressor
import jasy.js.optimize.CryptPrivates as CryptPrivates



class Tests(unittest.TestCase):

    def process(self, code, contextId=""):
        node = Parser.parse(code)
        CryptPrivates.optimize(node, contextId)
        return Compressor.Compressor().compress(node)        

    def test_assign(self):
        self.assertEqual(self.process(
            '''
            this.__field1 = 123;
            ''', 1),
            'this.__mJ02j=123;'
        )
        
    def test_assign_long(self):
        self.assertEqual(self.process(
            '''
            this.__titleBarBackgroundColor = "red";
            ''', 1),
            'this.__clbJJO="red";'
        )        
            
    def test_global_obj_file1(self):
        self.assertEqual(self.process(
            '''
            var obj = {
              __x : 123,
              __y : 456
            };
            alert(obj.__x + ":" + obj.__y);
            ''', 1),
            'var obj={__bLHVk:123,__bLYYn:456};alert(obj.__bLHVk+":"+obj.__bLYYn);'
        )        

    def test_global_obj_file2(self):
        self.assertEqual(self.process(
            '''
            var obj = {
              __x : 123,
              __y : 456
            };
            alert(obj.__x + ":" + obj.__y);
            ''', 2),
            'var obj={__bMw4r:123,__bMN7u:456};alert(obj.__bMw4r+":"+obj.__bMN7u);'
        )
        
    def test_remote(self):
        self.assertRaises(CryptPrivates.Error, self.process, 
            '''
            alert(RemoteObj.__x);
            ''')

    def test_localvar(self):
        self.assertEqual(self.process(
            '''
            var __x = 4;
            alert(__x);
            '''),
            'var __x=4;alert(__x);'
        )
    
    def test_localvar_undeclared(self):
        self.assertEqual(self.process(
            '''
            alert(__y);
            '''),
            'alert(__y);'
        )        

    def test_local_deep(self):
        self.assertEqual(self.process(
            '''
            var obj = {
              __field : {
                __sub : true
              }
            };
            
            alert(obj.__field.__sub);
            '''),
            'var obj={__ihERj:{__dZ1y9:true}};alert(obj.__ihERj.__dZ1y9);'
        )

    def test_access_same_named_external(self):
        """ 
        Is is somehow an unsupported edge case which is not supported correctly yet.
        Normally one would expect that the access to __field on RemoteObj would raise an error.
        At least it breaks this wrong access because this field is renamed based on file name as well.
        """
        self.assertEqual(self.process(
            '''
            var obj = {
              __field : true
            };
            alert(RemoteObj.__field);
            '''),
            'var obj={__ihERj:true};alert(RemoteObj.__ihERj);'
        )        

    def test_mixin(self):
        self.assertEqual(self.process(
            '''
            var source = {
              __field1 : 123,
              __field2 : 456
            };
            
            var target = {
              __field1 : 789
            };
            
            for (var key in source) {
              target[key] = source[key];
            }
            '''),
            'var source={__kZWNQ:123,__k0dQT:456};var target={__kZWNQ:789};for(var key in source){target[key]=source[key]}'
        )   




if __name__ == '__main__':
    logging.getLogger().setLevel(logging.ERROR)
    suite = unittest.TestLoader().loadTestsFromTestCase(Tests)
    unittest.TextTestRunner(verbosity=2).run(suite)



########NEW FILE########
__FILENAME__ = translation
#!/usr/bin/env python3

import sys, os, unittest, logging

# Extend PYTHONPATH with local 'lib' folder
if __name__ == "__main__":
    jasyroot = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]), os.pardir, os.pardir, os.pardir, os.pardir))
    sys.path.insert(0, jasyroot)
    print("Running from %s..." % jasyroot)

import jasy.js.parse.Parser as Parser
import jasy.js.parse.ScopeScanner as ScopeScanner
import jasy.js.output.Compressor as Compressor
import jasy.js.optimize.Translation as TranslationOptimizer
import jasy.item.Translation as Translation


class Tests(unittest.TestCase):

    def process(self, code):
        node = Parser.parse(code)

        translation = Translation.TranslationItem(None, id="de_DE", table={
            
            "Hello World": "Hallo Welt",
            "Short": "Kurz",
            "Thank you for the flowers": "Danke für die Blumen",
            
            "Hello %1!": "Hallo: %1!",
            "Hello %1! %1!": "Hallo: %1! %1!",
            
            "Chat[C:Chat (noum)]": "Unterhaltung",
            "Chat %1[C:Chat (noum) %1]": "Unterhaltung %1",
            
            "You have got a new mail[N:You have got new mails]": {0:"Du hast eine neue E-Mail", 1:"Du hast neue E-Mails"},
            "You have got a new mail[N:You have got %1 new mails]": {0:"Du hast eine neue E-Mail", 1:"Du hast %1 neue E-Mail erhalten"}
            
        })
        
        TranslationOptimizer.optimize(node, translation)
        
        return Compressor.Compressor().compress(node)        


    def test_basic(self):
        self.assertEqual(self.process(
            '''
            function wrapper()
            {
                alert(this.tr("Hello World"));
                alert(tr("Short"));
                alert(core.Locale.tr("Thank you for the flowers"));
            }
            '''),
            'function wrapper(){alert("Hallo Welt");alert("Kurz");alert("Danke für die Blumen")}'
        )


    def test_vars1(self):
        self.assertEqual(self.process(
            '''
            function wrapper() {
                alert(tr("Hello %1!", "Peter"))
            }
            '''),
            'function wrapper(){alert("Hallo: "+("Peter")+"!")}'
        )        

    def test_vars2(self):
        self.assertEqual(self.process(
            '''
            function wrapper() {
                alert(tr("Hello %1! %1!", "Peter"))
            }
            '''),
            'function wrapper(){alert("Hallo: "+("Peter")+"! "+("Peter")+"!")}'
        )        

    def test_vars3(self):
        self.assertEqual(self.process(
            '''
            function wrapper() {
                alert(tr("Hello %1!", this.getGreetingName()))
            }
            '''),
            'function wrapper(){alert("Hallo: "+this.getGreetingName()+"!")}'
        )
            
    def test_vars4(self):
        self.assertEqual(self.process(
            '''
            function wrapper() {
                alert(tr("Hello %1! %1!", this.getGreetingName()))
            }
            '''),
            'function wrapper(){alert("Hallo: "+this.getGreetingName()+"! "+this.getGreetingName()+"!")}'
        )        
 
    def test_trc1(self):
        self.assertEqual(self.process(
            '''
            function wrapper() {
                alert(trc("Chat (noum)", "Chat"));
            }
            '''),
            'function wrapper(){alert("Unterhaltung")}'
        )
        
    def test_trc2(self):
        self.assertEqual(self.process(
            '''
            function wrapper() {
                alert(trc("Chat (noum) %1", "Chat %1", "Online"));
            }
            '''),
            'function wrapper(){alert("Unterhaltung "+("Online"))}'
        )
        
    def test_trc3(self):
        self.assertEqual(self.process(
            '''
            function wrapper() {
                alert(trc("Chat (noum) %1", "Chat %1", this.getChatStatus()));
            }
            '''),
            'function wrapper(){alert("Unterhaltung "+this.getChatStatus())}'
        )
        
        
    def test_trn1(self):
        self.assertEqual(self.process(
            '''
            function wrapper() {
                alert(trn("You have got a new mail", "You have got new mails", newMails));
            }
            '''),
            'function wrapper(){alert(trnc({0:"Du hast eine neue E-Mail",1:"Du hast neue E-Mails"},newMails))}'
        )

    def test_trn2(self):
        self.assertEqual(self.process(
            '''
            function wrapper()
            {
                alert(trn("You have got a new mail", "You have got %1 new mails", newMails, newMails));
            }
            '''),
            'function wrapper(){alert(trnc({0:"Du hast eine neue E-Mail",1:"Du hast "+newMails+" neue E-Mail erhalten"},newMails))}'
        )


    def test_marktr(self):
        self.assertEqual(self.process(
            '''
            function wrapper()
            {
                // Register strings in translation file (will be compiled out)
                // According to doc, marktr() does mark for tranlsation, but always returns the original text.
                marktr("Dog");
                marktr("Cat");
                marktr("Bird");

                // After marking the text these can be used for translation
                var objs = ["Dog","Cat","Bird"];
                for (var i=0, l=objs.length; i<l; i++) {
                    alert(tr(objs[i]));
                }
            }
            '''),
            'function wrapper(){;;;var objs=["Dog","Cat","Bird"];for(var i=0,l=objs.length;i<l;i++){alert(tr(objs[i]))}}'
        )




if __name__ == '__main__':
    logging.getLogger().setLevel(logging.ERROR)
    suite = unittest.TestLoader().loadTestsFromTestCase(Tests)
    unittest.TextTestRunner(verbosity=2).run(suite)



########NEW FILE########
__FILENAME__ = unused
#!/usr/bin/env python3

import sys, os, unittest, logging

# Extend PYTHONPATH with local 'lib' folder
if __name__ == "__main__":
    jasyroot = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]), os.pardir, os.pardir, os.pardir, os.pardir))
    sys.path.insert(0, jasyroot)
    print("Running from %s..." % jasyroot)

import jasy.js.parse.Parser as Parser
import jasy.js.parse.ScopeScanner as ScopeScanner
import jasy.js.output.Compressor as Compressor
import jasy.js.clean.Unused as Unused


        
class Tests(unittest.TestCase):

    def process(self, code):
        node = Parser.parse(code)
        Unused.cleanup(node)
        return Compressor.Compressor().compress(node)

    def test_var_single(self):
        """ y is unused. Removed whole var block. """
        self.assertEqual(self.process(
            '''
            function wrapper() {
              var x = 4;
              var y = 5;
              func(x);
            }
            '''),
            'function wrapper(){var x=4;func(x)}'
        )        

    def test_var_multi_last(self):
        """ y is unused. Removes list entry. """
        self.assertEqual(self.process(
            '''
            function wrapper() {
              var x = 4, y = 5;
              func(x);
            }
            '''),
            'function wrapper(){var x=4;func(x)}'
        )        

    def test_var_multi_first(self):
        """ y is unused. Removes list entry."""
        self.assertEqual(self.process(
            '''
            function wrapper() {
              var y = 5, x = 4;
              func(x);
            }
            '''),
            'function wrapper(){var x=4;func(x)}'
        )        

    def test_var_dep_closure(self):
        """ Removes y first and in a second run removes x as well. """
        self.assertEqual(self.process(
            '''
            function wrapper() {
              var x = 4;
              var y = function() {
                return x;
              };
            }
            '''),
            'function wrapper(){}'
        )
        

    def test_var_ief(self):
        """  """
        self.assertEqual(self.process(
            '''
            function wrapper() {
              var exec = (function() {
                return 4+5;
              })();
            }
            '''),
            'function wrapper(){(function(){return 4+5})()}'
        )        
        
    def test_var_ief_middle(self):
        """  """
        self.assertEqual(self.process(
            '''
            function wrapper() {
              var a, exec = (function() {
                return 4+5;
              })(), b;
            }
            '''),
            'function wrapper(){(function(){return 4+5})()}'
        )
        
    def test_var_ief_end(self):
        """  """
        self.assertEqual(self.process(
            '''
            function wrapper() {
              var a, exec = (function() {
                return 4+5;
              })();
            }
            '''),
            'function wrapper(){(function(){return 4+5})()}'
        )        
        
        

    def test_var_ief_noparens(self):
        """  """
        self.assertEqual(self.process(
            '''
            function wrapper() {
              var exec = function() {
                return 4+5;
              }();
            }
            '''),
            'function wrapper(){(function(){return 4+5})()}'
        )        

    def test_var_ief_noparens_middle(self):
        """  """
        self.assertEqual(self.process(
            '''
            function wrapper() {
              var a, exec = function() {
                return 4+5;
              }(), b;
            }
            '''),
            'function wrapper(){(function(){return 4+5})()}'
        )

    def test_var_ief_noparens_end(self):
        """  """
        self.assertEqual(self.process(
            '''
            function wrapper() {
              var a, exec = function() {
                return 4+5;
              }();
            }
            '''),
            'function wrapper(){(function(){return 4+5})()}'
        )        
        
        
        
    def test_object(self):
        """ Non expressions must be protected with parens. """
        
        self.assertEqual(self.process(
        '''
        function abc() {
           var obj = {
               x:1
           };
        };
        '''
        ), 
        'function abc(){({x:1})};')
        
    def test_object_multi(self):
        """ Non expressions must be protected with parens. """

        self.assertEqual(self.process(
        '''
        function abc() {
           var obj1 = {
               x:1
           }, obj2 = {
               x:2
           };
        };
        '''
        ), 
        'function abc(){({x:1});({x:2})};')        

    def test_object_multi_others(self):
        """ Non expressions must be protected with parens. """

        self.assertEqual(self.process(
        '''
        function abc() {
           var obj1 = {
               x:1
           }, str = "hello", obj2 = {
               x:2
           }, nr = 3.14;
           return str;
        };
        '''
        ), 
        'function abc(){({x:1});var str="hello";({x:2});return str};')

    def test_var_dep_blocks(self):
        """ y contains operation so could not be removed and x is still in use. """
        self.assertEqual(self.process(
            '''
            function wrapper() {
              var x = 4;
              var y = x + 5;
            }
            '''),
            'function wrapper(){var x=4;x+5}'
        )

    def test_params_first(self):
        """ x is unused but could not be removed. """
        self.assertEqual(self.process(
            '''
            function a(x, y) {
              return y + 1;
            }
            '''),
            'function a(x,y){return y+1}'
        )        

    def test_params_middle(self):
        """ y is unused but could not be removed. """
        self.assertEqual(self.process(
            '''
            function a(x, y, z) {
              return x + z;
            }
            '''),
            'function a(x,y,z){return x+z}'
        )
        
    def test_params_last(self):
        """ y is unused and can be removed """
        self.assertEqual(self.process(
            '''
            function a(x, y) {
              return x + 1;
            }
            '''),
            'function a(x){return x+1}'
        )        

    def test_func_named_called(self):
        self.assertEqual(self.process(
            '''
            function wrapper() {
              function x() {}
              x();
            }
            '''),
            'function wrapper(){function x(){}x()}'
        )        

    def test_func_named_unused(self):
        self.assertEqual(self.process(
            '''
            function wrapper() {
              function x() {}
            }
            '''),
            'function wrapper(){}'
        )
        
    def test_func_called(self):
        self.assertEqual(self.process(
            '''
            function wrapper() {
              var x = function() {}
              x();
            }
            '''),
            'function wrapper(){var x=function(){};x()}'
        )        

    def test_func_unused(self):
        self.assertEqual(self.process(
            '''
            function wrapper() {
              var x = function() {}
            }
            '''),
            'function wrapper(){}'
        )

    def test_func_named_direct_called(self):
        self.assertEqual(self.process(
            '''
            function wrapper() {
              (function x() { 
                return 3; 
              })();
            }
            '''),
            'function wrapper(){(function(){return 3})()}'
        )        

    def test_var_vs_named(self):
        self.assertEqual(self.process(
            '''
            function wrapper() {
              var x = function y() {};
              x();
            }            
            '''),
            'function wrapper(){var x=function(){};x()}'
        ) 
        
    def test_var_vs_named_inner(self):
        self.assertEqual(self.process(
            '''
            function wrapper() {
              var x = function y() {
                setTimeout(y, 100);
              };
              x();
            }            
            '''),
            'function wrapper(){var x=function y(){setTimeout(y,100)};x()}'
        )        
        
    def test_named_vs_var(self):
        self.assertEqual(self.process(
            '''
            function wrapper() {
              var x = function y() {};

              // This might be an error: y is not defined in this context.
              // At least not here in this code.
              y();
            }
            '''),
            'function wrapper(){y()}'
        )               

    def test_var_same_inner_outer(self):
        self.assertEqual(self.process(
            '''
            var x = 1;
            function wrapper() {
              var x = 2;
            }
            '''),
            'var x=1;function wrapper(){}'
        )

    def test_named_func_same_inner_outer(self):
        self.assertEqual(self.process(
            '''
            function x() {};
            function wrapper() {
              function x() {};
            }            
            '''),
            'function x(){};function wrapper(){}'
        )        

    def test_global_var(self):
        self.assertEqual(self.process(
            '''
            var x = 4;
            '''),
            'var x=4;'
        )        
        
    def test_global_func(self):
        self.assertEqual(self.process(
            '''
            function x() {};
            '''),
            'function x(){};'
        )        
        
    def test_func_expressed_form_named_inner(self):
        self.assertEqual(self.process(
            '''
            function wrapper() {
              // y is only known inside the y-method
              var x = function y() {
                y();
              };
              x();
            }
            '''),
            'function wrapper(){var x=function y(){y()};x()}'
        )        

    def test_func_expressed_form_named(self):
        self.assertEqual(self.process(
            '''
            function wrapper() {
              // y is only known inside the y-method
              var x = function y() {
                // but not used
                z();
              };
              x();
            }
            '''),
            'function wrapper(){var x=function(){z()};x()}'
        )        
    
    def test_outdent_multi_var(self):
        self.assertEqual(self.process(
            '''
            var a = function d(b) {
              var c = d(), x = 3, y = x, z = y;
            };            
            '''),
            'var a=function d(){d()};'
        )        

    def test_outdent_multi_var(self):
        self.assertEqual(self.process(
            '''
            var a = function d(b) {
              var c = d(), g = 3, x = b(), y = x, z = y;
            };            
            '''),
            'var a=function d(b){d();b()};'
        )        

    def test_outdent(self):
        self.assertEqual(self.process(
            '''
            var a = function d(b) {
              var c = d();
            };
            '''),
            'var a=function d(){d()};'
        )
        
        



if __name__ == '__main__':
    logging.getLogger().setLevel(logging.ERROR)
    suite = unittest.TestLoader().loadTestsFromTestCase(Tests)
    unittest.TextTestRunner(verbosity=2).run(suite)


########NEW FILE########
__FILENAME__ = options
#!/usr/bin/env python3

import sys, os, unittest, logging

# Extend PYTHONPATH with local 'lib' folder
if __name__ == "__main__":
    jasyroot = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]), os.pardir, os.pardir, os.pardir))
    sys.path.insert(0, jasyroot)
    print("Running from %s..." % jasyroot)

import jasy.core.Options as Options


class Tests(unittest.TestCase):

    def test_add(self):

        options = Options.Options()
        options.add("file", accept=str, value="jasyscript.py", help="Use the given jasy script")
        self.assertEqual(options.__getattr__("file"), 'jasyscript.py')


    def test_parse(self):

        options = Options.Options()
        options.parse(['--file', 'bla'])
        self.assertEqual(options.__getattr__("file"), "bla")


    def test_add_and_parse(self):

        options = Options.Options()
        options.add("file", accept=str, value="jasyscript.py", help="Use the given jasy script")
        options.parse(['--file', 'foo'])
        self.assertEqual(options.__getattr__("file"), "foo") 


    def test_getTasks(self):

        options = Options.Options()
        options.parse(['source', '--file', 'foo'])
        self.assertEqual(options.getTasks()[0]['task'], 'source') 


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.ERROR)
    suite = unittest.TestLoader().loadTestsFromTestCase(Tests)
    unittest.TextTestRunner(verbosity=2).run(suite)


########NEW FILE########
__FILENAME__ = project
#!/usr/bin/env python3

import sys, os, unittest, logging, tempfile

# Extend PYTHONPATH with local 'lib' folder
jasyroot = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]), os.pardir, os.pardir, os.pardir))
sys.path.insert(0, jasyroot)

import jasy.core.Project as Project


class Tests(unittest.TestCase):

    def writeFile(self, path, fileName, content):
        handle = open(os.path.join(path, fileName), mode="w", encoding="utf-8")
        handle.write(content)
        handle.close()

    def readFile(self, path, fileName):
        return open(os.path.join(path, fileName), mode="r", encoding="utf-8").read()

    def createjpyaml(self, path):
        self.writeFile(path, "jasyproject.yaml", """name: myproject
""")

    def createjpyaml_withContent(self, path):
        self.writeFile(path, "jasyproject.yaml", """name: myproject

content: {myproject.Main: [man/Main.js, man/Add.js], myproject/main.css: [man/main.css]}
""")

    def createCaseOne(self):
        #manual

        path = os.path.join(tempfile.TemporaryDirectory().name, "myproject")
        os.makedirs(path)

        def createFolders():
            os.makedirs(os.path.join(path, "man"))

        def createSampleClasses():
            self.writeFile(os.path.join(path, "man"), "index.html", """<html></html>""")
            self.writeFile(os.path.join(path, "man"), "Main.js", ";")
            self.writeFile(os.path.join(path, "man"), "Add.js", ";")

        def createSampleAssets():
            self.writeFile(os.path.join(path, "man"), "main.css", """html{}""")


        createFolders()
        self.createjpyaml_withContent(path)
        createSampleClasses()
        createSampleAssets()

        return Project.getProjectFromPath(path)


    def createCaseTwo(self):
        #application

        path = os.path.join(tempfile.TemporaryDirectory().name, "myproject")
        os.makedirs(path)

        def createFolders():
            os.makedirs(os.path.join(path, "source"))
            os.makedirs(os.path.join(os.path.join(path, "source"), "class"))
            os.makedirs(os.path.join(os.path.join(path, "source"), "asset"))
            os.makedirs(os.path.join(os.path.join(path, "source"), "translation"))

        def createSampleClasses():
            self.writeFile(os.path.join(path, "source"), "index.html", """<html></html>""")
            self.writeFile(os.path.join(os.path.join(path, "source"), "class"), "Main.js", ";")

        def createSampleAssets():
            self.writeFile(os.path.join(os.path.join(path, "source"), "asset"), "main.css", """html{}""")

        def createSampleTranslations():
            self.writeFile(os.path.join(os.path.join(path, "source"), "translation"), "de.po", " ")

        createFolders()
        self.createjpyaml(path)
        createSampleClasses()
        createSampleAssets()
        createSampleTranslations()

        return Project.getProjectFromPath(path)


    def createCaseThree(self):
        #src

        path = os.path.join(tempfile.TemporaryDirectory().name, "myproject")
        os.makedirs(path)

        def createFolders():
            os.makedirs(os.path.join(path, "src"))

        def createSampleClasses():
            self.writeFile(os.path.join(path, "src"), "index.html", """<html></html>""")
            self.writeFile(os.path.join(path, "src"), "Main.js", ";")

        def createSampleAssets():
            self.writeFile(os.path.join(path, "src"), "main.css", """html{}""")

        createFolders()
        self.createjpyaml(path)
        createSampleClasses()
        createSampleAssets()

        return Project.getProjectFromPath(path)


    def createCaseFour(self):
        #resource

        path = os.path.join(tempfile.TemporaryDirectory().name, "myproject")
        os.makedirs(path)

        def createFolders():
            os.makedirs(os.path.join(path, "class"))
            os.makedirs(os.path.join(path, "asset"))
            os.makedirs(os.path.join(path, "translation"))

        def createSampleClasses():
            self.writeFile(os.path.join(path, "class"), "index.html", """<html></html>""")
            self.writeFile(os.path.join(path, "class"), "Main.js", ";")

        def createSampleAssets():
            self.writeFile(os.path.join(path, "asset"), "main.css", """html{}""")

        def createSampleTranslations():
            self.writeFile(os.path.join(path, "translation"), "de.po", " ")

        createFolders()
        self.createjpyaml(path)
        createSampleClasses()
        createSampleAssets()
        createSampleTranslations()

        return Project.getProjectFromPath(path)


    def getProjects(self):
        return [self.createCaseOne(),self.createCaseTwo(),self.createCaseThree(),self.createCaseFour()]

    def test_get_project(self):
        for project in self.getProjects():
            self.assertEqual(project.getName(), "myproject")

    def test_get_name_from_path(self):
        for project in self.getProjects():
            self.assertEqual(Project.getProjectNameFromPath(project.getPath()), "myproject")

    def test_scan(self):
        for project in self.getProjects():
            project.scan()
            self.assertEqual(project.scanned, True)

    def test_has_requires(self):
        for project in self.getProjects():
            self.assertEqual(project.hasRequires(), False)

    def test_fields(self):
        for project in self.getProjects():
            self.assertEqual(project.getFields(), {})

    def test_get_class_by_name(self):
        for project in self.getProjects():
            self.assertEqual(project.getClassByName("myproject.Main"), project.getClasses()["myproject.Main"])
            self.assertEqual(type(project.getClassByName("myproject.Main")).__name__, "ClassItem")

    def test_assets(self):
        for project in self.getProjects():
            self.assertEqual(type(project.getAssets()["myproject/main.css"]).__name__, "AssetItem")

    def test_translations(self):
        for project in [self.createCaseTwo(), self.createCaseFour()]:
            self.assertEqual(type(project.getTranslations()["myproject.de"]).__name__, "TranslationItem")     

    def test_manual_class_fusion(self):
        self.assertEqual(self.createCaseOne().getClassByName("myproject.Main").getText(), ";;")

if __name__ == '__main__':
    logging.getLogger().setLevel(logging.ERROR)
    suite = unittest.TestLoader().loadTestsFromTestCase(Tests)
    unittest.TextTestRunner(verbosity=2).run(suite)

########NEW FILE########
__FILENAME__ = requirements
#!/usr/bin/env python3

import sys, os, unittest, logging, tempfile

# Extend PYTHONPATH with local 'lib' folder
jasyroot = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]), os.pardir, os.pardir, os.pardir))
sys.path.insert(0, jasyroot)

import jasy.core.Project as Project
import jasy.core.Session as Session


class Tests(unittest.TestCase):

    def writeFile(self, path, fileName, content):
        handle = open(os.path.join(path, fileName), mode="w", encoding="utf-8")
        handle.write(content)
        handle.close()

    def readFile(self, path, fileName):
        return open(os.path.join(path, fileName), mode="r", encoding="utf-8").read()

    def createjpyaml(self, path, requirements):
        content = """name: myproject  
requires:"""
        for r in requirements:
            content += r
        self.writeFile(path, "jasyproject.yaml",  content)
        #print(content)

    def createRequirement(self, name, subrequirements=None, manPath=None):
        if manPath is not None:
            reqpath = os.path.join(manPath, name)
        else:
            reqpath = os.path.join(tempfile.TemporaryDirectory().name, name)
        try:
            os.makedirs(os.path.join(reqpath, "class"))
        except OSError as e:
            pass

        self.writeFile(os.path.join(reqpath, "class"), "Base.js", ";")
        ruquirement = ("""
- source: %s
  config:
    name: %s""" % (reqpath, name))


        if subrequirements is not None:
            ruquirement += """
    requires:"""
            for s in subrequirements:
                ruquirement += s;

        return ruquirement

    def createSubRequirement(self, name, manPath=None):
        if manPath is not None:
            reqpath = os.path.join(manPath, name)
        else:
            reqpath = os.path.join(tempfile.TemporaryDirectory().name, name)
        try:
            os.makedirs(os.path.join(reqpath, "class"))
        except OSError as e:
            pass

        self.writeFile(os.path.join(reqpath, "class"), "Base.js", ";")
        return("""
    - source: %s
      config:
      name: %s""" % (reqpath, name))


    def createProject(self, requirements):

        path = os.path.join(tempfile.TemporaryDirectory().name, "myproject")
        os.makedirs(path)

        def createFolders():
            os.makedirs(os.path.join(path, "source"))
            os.makedirs(os.path.join(os.path.join(path, "source"), "class"))
            os.makedirs(os.path.join(os.path.join(path, "source"), "asset"))
            os.makedirs(os.path.join(os.path.join(path, "source"), "translation"))

        def createSampleClasses():
            self.writeFile(os.path.join(path, "source"), "index.html", """<html></html>""")
            self.writeFile(os.path.join(os.path.join(path, "source"), "class"), "Main.js", ";")

        def createSampleAssets():
            self.writeFile(os.path.join(os.path.join(path, "source"), "asset"), "main.css", """html{}""")

        def createSampleTranslations():
            self.writeFile(os.path.join(os.path.join(path, "source"), "translation"), "de.po", " ")


        createFolders()
        self.createjpyaml(path, requirements)
        createSampleClasses()
        createSampleAssets()
        createSampleTranslations()

        os.chdir(path)

        return Project.getProjectFromPath(path)


    def test_has_requires(self):
        project = self.createProject([self.createRequirement("engine"), self.createRequirement("engine2")])
        project.scan()
        self.assertEqual(project.hasRequires(), True)

    def test_requires(self):
        project = self.createProject([self.createRequirement("engine"), self.createRequirement("engine2")])
        project.scan()
        requires = project.getRequires()
        self.assertEqual(requires[0].getName(), "engine")
        self.assertEqual(requires[1].getName(), "engine2")

    def test_classes(self):
        project = self.createProject([self.createRequirement("framework")])
        project.scan()
        requires = project.getRequires()
        self.assertEqual(requires[0].getClassByName('framework.Base').getText(), ";")

    def test_subrequirement(self):
        project = self.createProject([self.createRequirement("engine", [self.createSubRequirement("framework")])])
        project.scan()
        requires = project.getRequires()
        self.assertEqual(requires[0].getName(), "engine")
        subrequires = requires[0].getRequires()
        self.assertEqual(subrequires[0].getName(), "framework")

    
    def test_subrequirement_classes(self):
        session = Session.Session()
        session.addProject(self.createProject([self.createRequirement("engine", [self.createSubRequirement("framework")])]))

        self.assertEqual(len(session.getProjects()), 3)


    """
    # TODO catch if this ends in an endless loop
    def test_crossed_requirements(self):

        enginePath = tempfile.TemporaryDirectory().name
        frameworkPath = tempfile.TemporaryDirectory().name

        requirement1 = self.createRequirement("engine", [self.createSubRequirement("framework", manPath=frameworkPath)], manPath=enginePath)
        requirement2 = self.createRequirement("framework", [self.createSubRequirement("engine", manPath=enginePath)], manPath=frameworkPath)

        session = Session.Session()
        session.addProject(self.createProject([requirement1, requirement2]))

        self.assertEqual(len(session.getProjects()), 3)
    """

    def test_same_subrequirements(self):

        frameworkPath = tempfile.TemporaryDirectory().name

        requirement1 = self.createRequirement("engine", [self.createSubRequirement("framework", manPath=frameworkPath)])
        requirement2 = self.createRequirement("engine2", [self.createSubRequirement("framework", manPath=frameworkPath)])

        session = Session.Session()
        session.addProject(self.createProject([requirement1, requirement2]))

        self.assertEqual(len(session.getProjects()), 4)


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.ERROR)
    suite = unittest.TestLoader().loadTestsFromTestCase(Tests)
    unittest.TextTestRunner(verbosity=2).run(suite)

########NEW FILE########
__FILENAME__ = session
#!/usr/bin/env python3

import sys, os, unittest, logging, pkg_resources, tempfile

# Extend PYTHONPATH with local 'lib' folder
jasyroot = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]), os.pardir, os.pardir, os.pardir))
sys.path.insert(0, jasyroot)

import jasy.core.Project as Project
import jasy.core.Session as Session

globProject = None


class Tests(unittest.TestCase):

    def writeFile(self, path, fileName, content):
        handle = open(os.path.join(path, fileName), mode="w", encoding="utf-8")
        handle.write(content)
        handle.close()

    def readFile(self, path, fileName):
        return open(os.path.join(path, fileName), mode="r", encoding="utf-8").read()

    def createjpyaml(self, path, requirements):
        content = """name: myproject
fields:
  debug: {check: "Boolean", default: False, values: [True, False]}
  engine: {check: ["webkit", "gecko", "trident", "presto"], default: "trident", values: ["webkit", "gecko", "trident", "presto"]}
requires:"""
        for r in requirements:
            content += r
        self.writeFile(path, "jasyproject.yaml",  content)
        #print(content)

    def createRequirement(self, name, manPath=None):
        if manPath is not None:
            reqpath = os.path.join(manPath, name)
        else:
            reqpath = os.path.join(tempfile.TemporaryDirectory().name, name)
        try:
            os.makedirs(os.path.join(reqpath, "class"))
        except OSError as e:
            pass

        self.writeFile(os.path.join(reqpath, "class"), "Base.js", ";")
        ruquirement = ("""
- source: %s
  config:
    name: %s""" % (reqpath, name))

        return ruquirement

    def createProject(self, requirements, onlyFileCreation=False):

        global globProject
        globProject = tempfile.TemporaryDirectory()

        path = os.path.join(globProject.name, "myproject")
        os.makedirs(path)

        def createFolders():
            os.makedirs(os.path.join(path, "source"))
            os.makedirs(os.path.join(os.path.join(path, "source"), "class"))
            os.makedirs(os.path.join(os.path.join(path, "source"), "asset"))
            os.makedirs(os.path.join(os.path.join(path, "source"), "translation"))

        def createSampleClasses():
            self.writeFile(os.path.join(path, "source"), "index.html", """<html></html>""")
            self.writeFile(os.path.join(os.path.join(path, "source"), "class"), "Main.js", ";")

        def createSampleAssets():
            self.writeFile(os.path.join(os.path.join(path, "source"), "asset"), "main.css", """html{}""")

        def createSampleTranslations():
            self.writeFile(os.path.join(os.path.join(path, "source"), "translation"), "de.po", " ")

        createFolders()
        self.createjpyaml(path, requirements)
        createSampleClasses()
        createSampleAssets()
        createSampleTranslations()

        os.chdir(path)

        if onlyFileCreation:
            return path

        return Project.getProjectFromPath(path)

    def test_init(self):

        self.createProject([], onlyFileCreation=True)

        session = Session.Session()
        session.init()
        self.assertTrue(session.getProjectByName("myproject") is not None)


    def test_pause_resume(self):

        session = Session.Session()
        session.addProject(self.createProject([]))

        try:
            session.pause()
            session.resume()

            self.assertTrue(True)
        except:
            self.assertTrue(False)

    def test_other_process(self):

        project = self.createProject([])

        try:
            session = Session.Session()
            session.addProject(project)
            session2 = Session.Session()
            session2.addProject(project)
            session2.pause()
            session.resume()

            self.assertTrue(True)
        except:
            self.assertTrue(False)

        try:
            session = Session.Session()
            session.addProject(project)
            session2 = Session.Session()
            session2.addProject(project)
            session2.resume()

            self.assertTrue(False)
        except:
            self.assertTrue(True)

        try:
            session = Session.Session()
            session.addProject(project)
            session2 = Session.Session()
            session2.addProject(project)
            session2.close()
            session2.clean()

            self.assertTrue(False)
        except:
            self.assertTrue(True)

        try:
            session = Session.Session()
            session.addProject(project)
            session2 = Session.Session()
            session2.addProject(project)
            session2.close()
            session.clean()

            self.assertTrue(False)
        except:
            self.assertTrue(True)


    def test_load_library(self):
        path = os.path.join(globProject.name, "mylib")
        os.makedirs(path)
        self.writeFile(path, "MyScript.py", """
@share
def double(number):
    return number*2

@share
def pow(number):
    return number*number

def add(number):
    return number+1
""")
        session = Session.Session()
        env = {}
        session.init(scriptEnvironment=env)

        session.loadLibrary("MyScript", os.path.join(path, "MyScript.py"))

        self.assertEqual(env["MyScript"].double(5), 10)
        self.assertEqual(env["MyScript"].pow(4), 16)

        try:
            env["MyScript"].add(8)

            self.assertTrue(False)
        except:
            self.assertTrue(True)


    def test_field(self):
        session = Session.Session()
        session.addProject(self.createProject([]))

        self.assertEqual(session.exportFields(),'[[\'debug\', 2, false], [\'engine\', 2, "trident"]]')

    
    def test_set_field(self):
        session = Session.Session()
        session.addProject(self.createProject([]))

        session.setField("debug", True)
        self.assertEqual(session.exportFields(),'[[\'debug\', 2, true], [\'engine\', 2, "trident"]]')

    
    def test_set_permutation(self):
        session = Session.Session()
        session.addProject(self.createProject([]))

        session.permutateField("debug", values=[False, True], detect=None, default=True)
        session.permutateField("engine", values=["webkit", "gecko", "trident", "presto"], detect=None, default="gecko")

        self.assertEqual(session.exportFields(),'[[\'debug\', 2, true], [\'engine\', 2, "gecko"]]')  

        session.permutateField("engine", values=["webkit"], detect=None, default="webkit")

        self.assertEqual(session.exportFields(),'[[\'debug\', 2, true], [\'engine\', 2, "webkit"]]')  

    
    def test_permutate(self):
        session = Session.Session()
        session.addProject(self.createProject([]))

        counter = 0
        for p in session.permutate():
            counter += 1
        self.assertEqual(counter, 8)

        session.permutateField("engine", values=["webkit", "gecko", "trident"])
        counter = 0
        for p in session.permutate():
            counter += 1
        self.assertEqual(counter, 6)

        session.setField("debug", True)
        counter = 0
        for p in session.permutate():
            counter += 1
        self.assertEqual(counter, 3)


    def test_locale(self):
        session = Session.Session()
        session.addProject(self.createProject([]))

        session.setLocales(["de", "en_", "fr"])

        counter = 0
        for p in session.permutate():
            counter += 1
        self.assertEqual(counter, 24)


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.ERROR)
    suite = unittest.TestLoader().loadTestsFromTestCase(Tests)
    unittest.TextTestRunner(verbosity=2).run(suite)

########NEW FILE########
__FILENAME__ = text
#!/usr/bin/env python3

import sys, os, unittest, logging

# Extend PYTHONPATH with local 'lib' folder
jasyroot = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]), os.pardir, os.pardir, os.pardir))
sys.path.insert(0, jasyroot)

import jasy.core.Text as Text


class Tests(unittest.TestCase):

    def test_markdown(self):
        
        self.assertEqual(Text.markdownToHtml("*emphased*"), "<p><em>emphased</em></p>\n")
        self.assertEqual(Text.markdownToHtml("**bold**"), "<p><strong>bold</strong></p>\n")

        self.assertEqual(Text.markdownToHtml("# Header 1"), "<h1>Header 1</h1>\n")
        self.assertEqual(Text.markdownToHtml("## Header 2"), "<h2>Header 2</h2>\n")
        self.assertEqual(Text.markdownToHtml("### Header 3"), "<h3>Header 3</h3>\n")
        self.assertEqual(Text.markdownToHtml("#### Header 4"), "<h4>Header 4</h4>\n")
        self.assertEqual(Text.markdownToHtml("##### Header 5"), "<h5>Header 5</h5>\n")
        self.assertEqual(Text.markdownToHtml("###### Header 6"), "<h6>Header 6</h6>\n")

        self.assertEqual(Text.markdownToHtml("""
Paragraph 1

Paragraph 2
        """), "<p>Paragraph 1</p>\n\n<p>Paragraph 2</p>\n")

        self.assertEqual(Text.markdownToHtml("""
- Item 1
- Item 2
- Item 3
        """), "<ul>\n<li>Item 1</li>\n<li>Item 2</li>\n<li>Item 3</li>\n</ul>\n")        

        self.assertEqual(Text.markdownToHtml("""
1. Item 1
2. Item 2
3. Item 3
        """), "<ol>\n<li>Item 1</li>\n<li>Item 2</li>\n<li>Item 3</li>\n</ol>\n")


        self.assertEqual(Text.highlightCodeBlocks(Text.markdownToHtml("""
```js
alert("hello");
```
        """)), 
'''<table class="highlighttable"><tr><td class="linenos"><div class="linenodiv"><pre>1</pre></div></td><td class="code"><div class="highlight"><pre><span class="nx">alert</span><span class="p">(</span><span class="s2">"hello"</span><span class="p">);</span>
</pre></div>
</td></tr></table>
''')


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.ERROR)
    suite = unittest.TestLoader().loadTestsFromTestCase(Tests)
    unittest.TextTestRunner(verbosity=2).run(suite)

########NEW FILE########
__FILENAME__ = Git
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

import os.path, re, urllib.parse, shutil

from jasy.core.Util import executeCommand
import jasy.core.Console as Console


__versionNumber = re.compile(r"^v?([0-9\.]+)(-?(a|b|rc|alpha|beta)([0-9]+)?)?\+?$")

__gitAccountUrl = re.compile("([a-zA-Z0-9-_]+)@([a-zA-Z0-9-_\.]+):([a-zA-Z0-9/_-]+\.git)")
__gitHash = re.compile(r"^[a-f0-9]{40}$")
__gitSchemes = ('git', 'git+http', 'git+https', 'git+ssh', 'git+git', 'git+file')


def update(url, version, path, update=True, submodules=True):
    """Clones the given repository URL (optionally with overriding/update features)"""

    # Prepend git+ so that user knows that we identified the URL as git repository
    if not url.startswith("git+"):
        url = "git+%s" % url

    old = os.getcwd()

    if os.path.exists(path) and os.path.exists(os.path.join(path, ".git")):
        
        if not os.path.exists(os.path.join(path, ".git", "HEAD")):
            Console.error("Invalid git clone. Cleaning up...")
            shutil.rmtree(path)

        else:
            os.chdir(path)
            revision = executeCommand(["git", "rev-parse", "HEAD"], "Could not detect current revision")
            
            if update and (version == "master" or "refs/heads/" in version):
                if update:
                    Console.info("Updating %s", Console.colorize("%s @ " % url, "bold") + Console.colorize(version, "magenta"))
                    Console.indent()
                    
                    try:
                        executeCommand(["git", "fetch", "-q", "--depth", "1", "origin", version], "Could not fetch updated revision!")
                        executeCommand(["git", "reset", "-q", "--hard", "FETCH_HEAD"], "Could not update checkout!")
                        newRevision = executeCommand(["git", "rev-parse", "HEAD"], "Could not detect current revision")
                        
                        if revision != newRevision:
                            Console.info("Updated from %s to %s", revision[:10], newRevision[:10])
                            revision = newRevision

                            if submodules and os.path.exists(".gitmodules"):
                                Console.info("Updating sub modules (this might take some time)...")
                                executeCommand("git submodule update --recursive", "Could not initialize sub modules")

                    except Exception:
                        Console.error("Error during git transaction! Could not update clone.")
                        Console.error("Please verify that the host is reachable or disable automatic branch updates.")
                        Console.outdent()

                        os.chdir(old)
                        return
                        
                    except KeyboardInterrupt:
                        print()
                        Console.error("Git transaction was aborted by user!")
                        Console.outdent()
                        
                        os.chdir(old)
                        return                            

                    Console.outdent()
                    
                else:
                    Console.debug("Updates disabled")
                
            else:
                Console.debug("Using existing clone")

            os.chdir(old)
            return revision

    Console.info("Cloning %s", Console.colorize("%s @ " % url, "bold") + Console.colorize(version, "magenta"))
    Console.indent()

    os.makedirs(path)
    os.chdir(path)
    
    try:
        # cut of "git+" prefix
        remoteurl = url[4:]

        executeCommand(["git", "init", "."], "Could not initialize GIT repository!")
        executeCommand(["git", "remote", "add", "origin", remoteurl], "Could not register remote repository!")
        executeCommand(["git", "fetch", "-q", "--depth", "1", "origin", version], "Could not fetch revision!")
        executeCommand(["git", "reset", "-q", "--hard", "FETCH_HEAD"], "Could not update checkout!")
        revision = executeCommand(["git", "rev-parse", "HEAD"], "Could not detect current revision")

        if submodules and os.path.exists(".gitmodules"):
            Console.info("Updating sub modules (this might take some time)...")
            executeCommand("git submodule update --init --recursive", "Could not initialize sub modules")
        
    except Exception:
        Console.error("Error during git transaction! Intitial clone required for continuing!")
        Console.error("Please verify that the host is reachable.")

        Console.error("Cleaning up...")
        os.chdir(old)
        shutil.rmtree(path)

        Console.outdent()
        return
        
    except KeyboardInterrupt:
        print()
        Console.error("Git transaction was aborted by user!")
        
        Console.error("Cleaning up...")
        os.chdir(old)
        shutil.rmtree(path)

        Console.outdent()
        return
    
    os.chdir(old)
    Console.outdent()

    return revision



def getBranch(path=None):
    """Returns the name of the git branch"""

    return executeCommand("git rev-parse --abbrev-ref HEAD", "Could not figure out git branch. Is there a valid Git repository?", path=path)



def isUrl(url):
    """Figures out whether the given string is a valid Git repository URL"""

    parsed = urllib.parse.urlparse(url)

    if not parsed.params and not parsed.query and not parsed.fragment:

        if parsed.scheme in __gitSchemes:
            return True
        elif parsed.scheme == "https" and parsed.path.endswith(".git"):
            return True
        elif not parsed.scheme and parsed.path == url and __gitAccountUrl.match(url) != None:
            return True
        
    return False
    
    
    
def expandVersion(version=None):
    if version is None:
        version = "master"
    
    version = str(version)

    if version.startswith("refs/"):
        pass
    elif re.compile(r"^[a-f0-9]{40}$").match(version):
        # See also: http://git.661346.n2.nabble.com/Fetch-by-SHA-missing-td5604552.html
        raise Exception("Can't fetch non tags/branches: %s@%s!" % (url, version))
    elif __versionNumber.match(version) is not None:
        version = "refs/tags/" + version
    else:
        version = "refs/heads/" + version
        
    return version


def cleanRepository():
    """Cleans git repository from untracked files."""
    return executeCommand(["git", "clean", "-d", "-f"], "Could not clean GIT repository!")

def distcleanRepository():
    """Cleans git repository from untracked files. Ignores the files listed in ".gitignore"."""
    return executeCommand(["git", "clean", "-d", "-f", "-x"], "Could not distclean GIT repository!")


########NEW FILE########
__FILENAME__ = Repository
#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

import hashlib, os

import jasy.core.Console as Console
import jasy.core.Util as Util
import jasy.vcs.Git as Git


def isUrl(url):
    """
    Figures out whether the given string is a valid Git repository URL

    :param url: URL to the repository
    :type url: string
    """
    return Git.isUrl(url)


def getType(url):
    """
    Returns repository type of the given URL

    :param url: URL to the repository
    :type url: string
    """
    if Git.isUrl(url):
        return "git"
    else:
        return None


def getTargetFolder(url, version=None):
    """
    Returns the target folder name based on the URL and version using SHA1 checksums

    :param url: URL to the repository
    :type url: string
    :param version: Version to use
    :type url: string
    """
    
    if Git.isUrl(url):

        version = Git.expandVersion(version)

        folder = url[url.rindex("/")+1:]
        if folder.endswith(".git"):
            folder = folder[:-4]

        identifier = "%s@%s" % (url, version)
        version = version[version.rindex("/")+1:]

    hash = hashlib.sha1(identifier.encode("utf-8")).hexdigest()
    return "%s-%s-%s" % (folder, version, hash)


def update(url, version=None, path=None, update=True):
    """
    Clones the given repository URL (optionally with overriding/update features)

    :param url: URL to the repository
    :type url: string
    :param version: Version to clone
    :type url: string
    :param version: Destination path
    :type url: string
    :param version: Eneable/disable update functionality
    :type url: string
    """

    revision = None

    if Git.isUrl(url):
        version = Git.expandVersion(version)
        revision = Git.update(url, version, path, update)

    return revision


def clean(path=None):
    """
    Cleans repository from untracked files.

    :param url: Path to the local repository
    :type url: string
    """

    old = os.getcwd()

    Console.info("Cleaning repository (clean)...")
    Console.indent()

    if path:
        os.chdir(path)

    if os.path.exists(".git"):
        Git.cleanRepository()

    os.chdir(old)
    Console.outdent()


def distclean(path=None):
    """
    Cleans repository from untracked and ignored files. This method
    is pretty agressive in a way that it deletes all non repository managed
    files e.g. external folder, uncommitted changes, unstaged files, etc.

    :param url: Path to the local repository
    :type url: string
    """

    old = os.getcwd()

    Console.info("Cleaning repository (distclean)...")
    Console.indent()

    if path:
        os.chdir(path)

    if os.path.exists(".git"):
        Git.distcleanRepository()

    os.chdir(old)
    Console.outdent()


########NEW FILE########
__FILENAME__ = upload_docs
# -*- coding: utf-8 -*-
"""upload_docs

Implements a Distutils 'upload_docs' subcommand (upload documentation to
PyPI's packages.python.org).
"""

import os
import socket
import zipfile
import http.client
import base64
import urllib.parse
import tempfile
import sys, io
from base64 import standard_b64encode

from distutils import log
from distutils.errors import DistutilsOptionError

try:
    from distutils.command.upload import upload
except ImportError:
    from setuptools.command.upload import upload

_IS_PYTHON3 = sys.version > '3'

try:
    bytes
except NameError:
    bytes = str


class upload_docs(upload):

    description = 'Upload documentation to PyPI'

    user_options = [
        ('repository=', 'r',
         "url of repository [default: %s]" % upload.DEFAULT_REPOSITORY),
        ('show-response', None,
         'display full response text from server'),
        ('upload-dir=', None, 'directory to upload'),
        ]
    boolean_options = upload.boolean_options

    def initialize_options(self):
        upload.initialize_options(self)
        self.upload_dir = None

    def finalize_options(self):
        upload.finalize_options(self)
        if self.upload_dir is None:
            build = self.get_finalized_command('build')
            self.upload_dir = os.path.join(build.build_base, 'docs')
            self.mkpath(self.upload_dir)
        self.ensure_dirname('upload_dir')
        self.announce('Using upload directory %s' % self.upload_dir)

    def create_zipfile(self):
        name = self.distribution.metadata.get_name()
        tmp_dir = tempfile.mkdtemp()
        tmp_file = os.path.join(tmp_dir, "%s.zip" % name)
        zip_file = zipfile.ZipFile(tmp_file, "w")
        for root, dirs, files in os.walk(self.upload_dir):
            if root == self.upload_dir and not files:
                raise DistutilsOptionError(
                    "no files found in upload directory '%s'"
                    % self.upload_dir)
            for name in files:
                full = os.path.join(root, name)
                relative = root[len(self.upload_dir):].lstrip(os.path.sep)
                dest = os.path.join(relative, name)
                zip_file.write(full, dest)
        zip_file.close()
        return tmp_file

    def run(self):
        zip_file = self.create_zipfile()
        self.upload_file(zip_file)

    def upload_file(self, filename):
        content = open(filename, 'rb').read()
        meta = self.distribution.metadata
        data = {
            ':action': 'doc_upload',
            'name': meta.get_name(),
            'content': (os.path.basename(filename), content),
        }

        # set up the authentication
        user_pass = (self.username + ":" + self.password).encode('ascii')
        # The exact encoding of the authentication string is debated.
        # Anyway PyPI only accepts ascii for both username or password.
        auth = "Basic " + standard_b64encode(user_pass).decode('ascii')

        # Build up the MIME payload for the POST data
        boundary = '--------------GHSKFJDLGDS7543FJKLFHRE75642756743254'
        sep_boundary = b'\n--' + boundary.encode('ascii')
        end_boundary = sep_boundary + b'--'
        body = io.BytesIO()
        for key, value in data.items():
            title = '\nContent-Disposition: form-data; name="%s"' % key
            # handle multiple entries for the same name
            if type(value) != type([]):
                value = [value]
            for value in value:
                if type(value) is tuple:
                    title += '; filename="%s"' % value[0]
                    value = value[1]
                else:
                    value = str(value).encode('utf-8')
                body.write(sep_boundary)
                body.write(title.encode('utf-8'))
                body.write(b"\n\n")
                body.write(value)
                if value and value[-1:] == b'\r':
                    body.write(b'\n')  # write an extra newline (lurve Macs)
        body.write(end_boundary)
        body.write(b"\n")
        body = body.getvalue()

        self.announce("Submitting documentation to %s" % (self.repository),
                      log.INFO)

        # build the Request
        # We can't use urllib2 since we need to send the Basic
        # auth right with the first request
        schema, netloc, url, params, query, fragments = \
            urllib.parse.urlparse(self.repository)
        assert not params and not query and not fragments
        if schema == 'http':
            conn = http.client.HTTPConnection(netloc)
        elif schema == 'https':
            conn = http.client.HTTPSConnection(netloc)
        else:
            raise AssertionError("unsupported schema "+schema)

        data = ''
        loglevel = log.INFO
        try:
            conn.connect()
            conn.putrequest("POST", url)
            conn.putheader('Content-type',
                           'multipart/form-data; boundary=%s'%boundary)
            conn.putheader('Content-length', str(len(body)))
            conn.putheader('Authorization', auth)
            conn.endheaders()
            conn.send(body)
        except socket.error as e:
            self.announce(str(e), log.ERROR)
            return

        r = conn.getresponse()
        if r.status == 200:
            self.announce('Server response (%s): %s' % (r.status, r.reason),
                          log.INFO)
        elif r.status == 301:
            location = r.getheader('Location')
            if location is None:
                location = 'http://packages.python.org/%s/' % meta.get_name()
            self.announce('Upload successful. Visit %s' % location,
                          log.INFO)
        else:
            self.announce('Upload failed (%s): %s' % (r.status, r.reason),
                          log.ERROR)
        if self.show_response:
            print('-'*75, r.read(), '-'*75)

########NEW FILE########
