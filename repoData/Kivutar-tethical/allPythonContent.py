__FILENAME__ = AT
from Config import *

# Displays the Active Time flag on a sprite
class AT(object):

    def __init__(self):
        self.atcontainer = render.attachNewNode("atcontainer")
        self.atcontainer.setPos(0,0,3.5)
        self.atcontainer.setBillboardPointEye()
        at = loader.loadModel(GAME+'/models/gui/AT')
        at.setTransparency(True)
        at.reparentTo(self.atcontainer)
        at.setPos(.75,0,0)
        at.setScale(2.0*256.0/240.0)

    def showOnSprite(self, sprite):
        self.atcontainer.reparentTo(sprite.node)

    def hide(self):
        self.atcontainer.detachNode()
########NEW FILE########
__FILENAME__ = BarNodeDrawer
from Config import *
from pandac.PandaModules import *
from direct.interval.IntervalGlobal import *
import GUI
import os
import os.path
from operator import itemgetter, attrgetter

#THEME
class Bar:
    # Force following textures to not be power-of-2 scaled (up or down); setting is probably global.
    texture = Texture()
    texture.setTexturesPower2(ATSNone)
    def __init__(self, bar='bar-3', parent=None):
        self.textureList = []
        self.bar = bar
        self.path = GAME+'/textures/gui/'+THEME+'/'+self.bar+'/'
        self.container = NodePath("container")
        if parent != None:
            self.container.reparentTo(parent)
        dirList=os.listdir(self.path)
        for fname in dirList:
            fileWithoutExtension = os.path.splitext(fname)[0]
            if str(fileWithoutExtension) == 'frame' or (int(fileWithoutExtension) >= 0 and int(fileWithoutExtension) <= 100):
                texture = loader.loadTexture(self.path+fname)
                texture.setMagfilter(Texture.FTNearest)
                texture.setMinfilter(Texture.FTNearest)
                texture.setAnisotropicDegree(0)
                texture.setWrapU(Texture.WMClamp)
                texture.setWrapV(Texture.WMClamp)
                self.textureList.append((str(fileWithoutExtension), texture))
                if str(fileWithoutExtension) == 'frame':
                    self.width = texture.getOrigFileXSize()
                    self.height = texture.getOrigFileYSize()
                    # Create background card from frame.
                    cm = CardMaker('bar-frame-'+bar+'-backgrmoranoound')
                    cm.setFrame(0, self.width, 0, self.height)
                    card = self.container.attachNewNode(cm.generate())
                    card.setTexture(texture)
                    card.setScale(GUI.v)
                    card.setTransparency(True)
                    self.frameCard = card
                    # Create foreground card from frame dimensions.
                    cm = CardMaker('bar-frame-'+bar+'-foreground')
                    cm.setFrame(0, self.width, 0, self.height)
                    card = self.container.attachNewNode(cm.generate())
                    card.setScale(GUI.v)
                    card.setTexture(texture)
                    card.setTransparency(True)
                    self.barCard = card
            # Sort list for future comparison to value numbers.
            self.textureList = sorted(self.textureList, cmp=self.orderByNumber)
            pass

    def orderByNumber(self, x, y):
        if str(x[0]) == 'frame':
            return 1
        if str(y[0]) == 'frame':
            return -1
        return int(x[0]) - int(y[0])
        pass

    def updateTo(self, value):
        index = 0
        for i in range(0, len(self.textureList),1):
            if str(self.textureList[i][0]) != 'frame':
                if int(self.textureList[i][0]) > value:
                    self.barCard.setTexture(self.textureList[index][1])
                    return
                elif int(self.textureList[i][0]) == value:
                    index = i
                    self.barCard.setTexture(self.textureList[index][1])
                    return
                index = i
                pass
        pass

    def getFrameSize(self):
        return (0, GUI.v*self.width, 0, GUI.v*self.height)
        pass

########NEW FILE########
__FILENAME__ = BattleGraphics
from Config import *
from panda3d.core import *
from panda3d.physics import BaseParticleEmitter,BaseParticleRenderer
from panda3d.physics import PointParticleFactory,SpriteParticleRenderer
from panda3d.physics import LinearNoiseForce,DiscEmitter
from direct.particles.Particles import Particles
from direct.particles.ParticleEffect import ParticleEffect
from direct.particles.ForceGroup import ForceGroup
import Sprite

class BattleGraphics(object):

    def __init__(self, mp, game = None):
		self.mp = mp
		# Honor a custom GAME value (ex: 'fft','lijj') if one is being provided; used by the testing environment.
		if not game is None:
			global GAME
			GAME = game
		pass

    # Converts logic coordinates to panda3d coordinates
    def logic2terrain(self, tile):
        (x, y, z) = tile
        return Point3(
            (x+self.mp['offset'][0]+0.5) * 3.7,
            (y+self.mp['offset'][1]+0.5) * 3.7,
            (z+self.mp['offset'][2]+0.0) * 3.7/4.0*6.0/7.0,
        )

    # Load the terrain model, scale it and attach it to render
    def displayTerrain(self):
        self.terrain = loader.loadModel(GAME+'/models/maps/'+self.mp['model'])
        self.terrain.reparentTo( render )
        self.terrain.setScale( *self.mp['scale'] )

    # Loop over the lights defined in a map, and light the scene
    def lightScene(self):
        for i, light in enumerate(self.mp['lights']):
            if light.has_key('direction'):
                directionalLight = DirectionalLight( "directionalLight_"+str(i) )
                directionalLight.setDirection( Vec3( *light['direction'] ) )
                directionalLight.setColor( Vec4( *light['color'] ) )
                render.setLight( render.attachNewNode( directionalLight ) )
            elif light.has_key('position'):
                plight = PointLight('plighti_'+str(i))
                plight.setColor( Vec4( *light['color'] ) )
                plight.setAttenuation(Point3( *light['attenuation'] ))
                plnp = render.attachNewNode(plight)
                plnp.setPos( self.logic2terrain( light['position'] ) )
                render.setLight( plnp )
            else:
                ambientLight = AmbientLight( "ambientLight"+str(i) )
                ambientLight.setColor( Vec4( *light['color'] ) )
                render.setLight( render.attachNewNode( ambientLight ) )

    # Add special effects to the scene
    def addEffects(self):
        if self.mp.has_key('effects'):
            base.enableParticles()
            for effect in self.mp['effects']:
                p = ParticleEffect()
                p.loadConfig(GAME+'/particles/'+effect['file']+'.ptf') 
                p.start(render)
                p.setPos(self.logic2terrain( effect['position'] ))
########NEW FILE########
__FILENAME__ = CameraHandler
from Config import *
from direct.directbase import DirectStart
from direct.showbase import DirectObject
from panda3d.core import OrthographicLens
from pandac.PandaModules import *
from direct.interval.IntervalGlobal import LerpPosInterval, LerpScaleInterval, LerpHprInterval, Sequence

class CameraHandler(DirectObject.DirectObject):

    def __init__(self):

        base.disableMouse()

        lens = OrthographicLens()
        lens.setFilmSize(34.2007, 25.6505)
        lens.setNear(-10)
        lens.setFar(100)
        base.cam.node().setLens(lens)

        self.container = render.attachNewNode('camContainer')
        base.camera.reparentTo( self.container )
        base.camera.setPos( -40, 0, 23 )
        base.camera.lookAt(0, 0, 3)
        self.container.setHpr(45, 0, 0)

        self.zoomed = True
        self.r      = False
        
        # Load sounds
        self.toggle_r_snd = base.loader.loadSfx(GAME+'/sounds/camera_toggle_r.ogg')
        self.rotate_snd   = base.loader.loadSfx(GAME+'/sounds/camera_rotate.ogg')

        self.acceptAll()
        self.windowEvent(base.win)

    def acceptAll(self):
        self.accept(L1_BTN, lambda: self.rotate( 90) )
        self.accept(R1_BTN, lambda: self.rotate(-90) )
        self.accept(L2_BTN,         self.toggleZoom  )
        self.accept(R2_BTN,         self.toggleR     )
        self.accept('window-event', self.windowEvent )

    def ignore(self):
        self.ignoreAll()
        self.accept('window-event', self.windowEvent )

    def toggleZoom(self):
        if round(self.container.getScale()[0]*10) in (10, 14):
            self.toggle_r_snd.play()
            if self.zoomed:
                i = LerpScaleInterval(self.container, 0.25, 1.4, 1.0)
            else:
                i = LerpScaleInterval(self.container, 0.25, 1.0, 1.4)
            s = Sequence(i)
            s.start()
            self.zoomed = not self.zoomed

    def toggleR(self):
        (h, p, r) = self.container.getHpr()
        if r in (0.0, 15.0):
            self.toggle_r_snd.play()
            if self.r:
                i = LerpHprInterval(self.container, 0.25, (h, p, r-15), (h, p, r))
            else:
                i = LerpHprInterval(self.container, 0.25, (h, p, r+15), (h, p, r))
            s = Sequence(i)
            s.start()
            self.r = not self.r

    def rotate(self, delta):
        (h, p, r) = self.container.getHpr()
        if (h-45)%90 == 0.0:
            self.rotate_snd.play()
            i = LerpHprInterval(self.container, 0.5, (h+delta, p, r), (h, p, r))
            s = Sequence(i)
            s.start()

    def move(self, dest):
        orig = self.container.getPos()
        i = LerpPosInterval(self.container, 0.5, dest, startPos=orig)
        s = Sequence(i)
        s.start()

    def windowEvent(self, window):
        ratio = float(window.getXSize()) / float(window.getYSize())
        base.cam.node().getLens().setAspectRatio( ratio )

    def destroy(self):
        self.ignoreAll()
        self.container.removeNode()

########NEW FILE########
__FILENAME__ = Config
import sys
from panda3d.core import loadPrcFile
from pandac.PandaModules import ConfigVariableString
loadPrcFile("../config.prc")
GAME = ConfigVariableString('game', 'fft').getValue()
loadPrcFile(GAME+"/config.prc")

IP = ConfigVariableString('ip', '127.0.0.1').getValue()
PORT =  int(ConfigVariableString('port', '3001').getValue())

CROSS_BTN    = ConfigVariableString('cross-btn',    '0').getValue()
CIRCLE_BTN   = ConfigVariableString('circle-btn',   '3').getValue()
TRIANGLE_BTN = ConfigVariableString('triangle-btn', '2').getValue()
SQUARE_BTN   = ConfigVariableString('square-btn',   '1').getValue()
L1_BTN       = ConfigVariableString('l1-btn',       '4').getValue()
L2_BTN       = ConfigVariableString('l2-btn',       '7').getValue()
R1_BTN       = ConfigVariableString('r1-btn',       '6').getValue()
R2_BTN       = ConfigVariableString('r2-btn',       '9').getValue()
START_BTN    = ConfigVariableString('start-btn',    '8').getValue()
SELECT_BTN   = ConfigVariableString('select-btn',   '5').getValue()

SPRITE_SCALE = float( ConfigVariableString('sprite-scale', '2').getValue() )

THEME = ConfigVariableString('theme', 'default').getValue()
########NEW FILE########
__FILENAME__ = ATTACKABLES_LIST
import json

def execute(client, iterator):
    charid = iterator.getString()
    attackables = json.loads(iterator.getString())

    client.setupAttackableTileChooser(charid, attackables)
########NEW FILE########
__FILENAME__ = ATTACK_PASSIVE
from direct.interval.IntervalGlobal import Sequence, Func, Wait
import SequenceBuilder
import json

def execute(client, iterator):
    charid = iterator.getString()
    targetid = iterator.getString()
    damages = iterator.getUint8()
    attackables = json.loads(iterator.getString())

    print damages
    target = client.party['chars'][targetid]
    target['hp'] = target['hp'] - damages
    if target['hp'] < 0:
        target['hp'] = 0

    client.inputs.ignoreAll()
    seq = Sequence()
    seq.append( Func(client.matrix.setupAttackableZone, charid, attackables) )
    seq.append( Wait(0.5) )
    seq.append( Func(client.updateCursorPos, client.matrix.getCharacterCoords(targetid)) )
    seq.append( Func(client.camhandler.move, client.battleGraphics.logic2terrain(client.matrix.getCharacterCoords(targetid))) )
    seq.append( Wait(0.5) )
    seq.append( SequenceBuilder.characterAttackSequence(client, charid, targetid) )
    seq.append( Func(client.camhandler.move, client.battleGraphics.logic2terrain(client.matrix.getCharacterCoords(charid))) )
    seq.start()
########NEW FILE########
__FILENAME__ = ATTACK_SUCCESS
from direct.interval.IntervalGlobal import Sequence, Func
import SequenceBuilder

def execute(client, iterator):
    charid = iterator.getString()
    targetid = iterator.getString()
    damages = iterator.getUint8()

    print damages
    target = client.party['chars'][targetid]
    target['hp'] = target['hp'] - damages
    if target['hp'] < 0:
        target['hp'] = 0

    seq = Sequence()
    seq.append( SequenceBuilder.characterAttackSequence(client, charid, targetid) )
    seq.append( Func(client.send.UPDATE_PARTY) )
    seq.start()
########NEW FILE########
__FILENAME__ = BATTLE_COMPLETE
from Config import GAME
import GUI

def execute(client, iterator):
    if client.charbars:
        client.charbars.hide()
    if client.charcard:
        client.charcard.hide()
    if client.actionpreview:
        client.actionpreview.hide()
    for i,charid in enumerate(client.matrix.sprites):
        if client.matrix.sprites[charid].animation == 'walk':
            client.updateSpriteAnimation(charid, 'stand')
    client.music.stop()
    client.music = base.loader.loadSfx(GAME+'/music/13.ogg')
    client.music.play()
    GUI.BrownOverlay(GUI.Congratulations, client.end)
########NEW FILE########
__FILENAME__ = GAME_OVER
from Config import GAME
import GUI

def execute(client, iterator):
    if client.charbars:
        client.charbars.hide()
    if client.charcard:
        client.charcard.hide()
    for i,charid in enumerate(client.matrix.sprites):
        if client.matrix.sprites[charid].animation == 'walk':
            client.updateSpriteAnimation(charid, 'stand')
    client.music.stop()
    client.music = base.loader.loadSfx(GAME+'/music/33.ogg')
    client.music.play()
    GUI.GameOver(client.end)
########NEW FILE########
__FILENAME__ = LOGIN_FAIL
# Login failed, print an error message
def execute(client, iterator):
    print iterator.getString()
########NEW FILE########
__FILENAME__ = LOGIN_SUCCESS
# Successfully logged into the server, display the party list
def execute(client, iterator):
    client.loginwindow.commandanddestroy(client.send.GET_PARTIES)
########NEW FILE########
__FILENAME__ = MAP_LIST
import json, GUI

# Receive map list, display the map chooser
def execute(client, iterator):
    maps = json.loads(iterator.getString())
    client.mapchooserwindow = GUI.MapChooser(maps, client.background.frame, client.send.CREATE_PARTY, client.send.GET_PARTIES)

########NEW FILE########
__FILENAME__ = MOVED
def execute(client, iterator):
    charid = iterator.getString()
    x2 = iterator.getUint8()
    y2 = iterator.getUint8()
    z2 = iterator.getUint8()

    (x1, y1, z1) = client.matrix.getCharacterCoords(charid)
    del client.party['map']['tiles'][x1][y1][z1]['char']
    client.party['map']['tiles'][x2][y2][z2]['char'] = charid
    client.send.UPDATE_PARTY()
########NEW FILE########
__FILENAME__ = MOVED_PASSIVE
from direct.interval.IntervalGlobal import Sequence, Func, Wait
import json
import SequenceBuilder

def execute(client, iterator):
    charid = iterator.getString()
    walkables = json.loads(iterator.getString())
    path = json.loads(iterator.getString())

    client.inputs.ignoreAll()
    (x1, y1, z1) = path[0]
    (x2, y2, z2) = path[-1]
    del client.party['map']['tiles'][x1][y1][z1]['char']
    client.party['map']['tiles'][x2][y2][z2]['char'] = charid
    seq = Sequence()
    seq.append( Func(client.matrix.setupPassiveWalkableZone, walkables) )
    seq.append( Wait(0.5) )
    seq.append( Func(client.updateCursorPos, (x2, y2, z2)) )
    seq.append( Wait(0.5) )
    seq.append( Func(client.at.hide) )
    seq.append( Func(client.updateSpriteAnimation, charid, 'run') )
    seq.append( Func(client.camhandler.move, client.battleGraphics.logic2terrain((x2, y2, z2))) )
    seq.append( SequenceBuilder.characterMoveSequence(client, charid, path) )
    seq.append( Wait(0.5) )
    seq.append( Func(client.updateSpriteAnimation, charid) )
    seq.append( Func(client.matrix.clearZone) )
    seq.append( Func(client.at.showOnSprite, client.matrix.sprites[charid]) )
    seq.start()
########NEW FILE########
__FILENAME__ = PARTY_CREATED
import json

# Your party has been created server side. Put the party data in the client instance
def execute(client, iterator):
    party = json.loads(iterator.getString32())
    client.party = party
########NEW FILE########
__FILENAME__ = PARTY_JOINED
import json

# You joined a party
def execute(client, iterator):
    party = json.loads(iterator.getString32())
    client.party = party
########NEW FILE########
__FILENAME__ = PARTY_JOIN_FAIL
import json, GUI

# The client failed at joining a party, display a new party list window
def execute(client, iterator):
    print iterator.getString()
    parties = json.loads(iterator.getString32())
    client.partylistwindow = GUI.PartyListWindow(client.send.JOIN_PARTY, client.send.GET_MAPS)
    client.partylistwindow.refresh(parties)
########NEW FILE########
__FILENAME__ = PARTY_LIST
import json, GUI

# Party list data received, display the party list GUI
def execute(client, iterator):
    parties = json.loads(iterator.getString32())
    client.partylistwindow = GUI.PartyListWindow(client.send.JOIN_PARTY, client.send.GET_MAPS)
    client.partylistwindow.refresh(parties)
########NEW FILE########
__FILENAME__ = PARTY_UPDATED
import json, GUI

def execute(client, iterator):
    client.party['yourturn'] = iterator.getBool()
    client.party['chars'] = json.loads(iterator.getString32())

    client.matrix.clearZone()
    if client.charbars:
        client.charbars.hide()
    if client.charcard:
        client.charcard.hide()
    if client.actionpreview:
        client.actionpreview.hide()
    client.subphase = False

    for x,xs in enumerate(client.party['map']['tiles']):
        for y,ys in enumerate(xs):
            for z,zs in enumerate(ys):
                if not client.party['map']['tiles'][x][y][z] is None:
                    if client.party['map']['tiles'][x][y][z].has_key('char') and client.party['map']['tiles'][x][y][z]['char'] != 0:
                        charid = client.party['map']['tiles'][x][y][z]['char']
                        char = client.party['chars'][charid]

                        if char['active']:
                            client.camhandler.move(client.battleGraphics.logic2terrain((x, y, z)))
                            client.at.showOnSprite(client.matrix.sprites[charid])

                            client.updateCursorPos((x,y,z))

                            client.charcard = GUI.CharCard(char)

                            if client.party['yourturn']:
                                if char['canmove'] or char['canact']:
                                    client.showMenu(charid)
                                else:
                                    client.onWaitClicked(charid)
                            else:
                                client.camhandler.ignoreAll()
########NEW FILE########
__FILENAME__ = PASSIVE_WALKABLES_LIST
import json

def execute(client, iterator):
    charid = iterator.getString()
    walkables = json.loads(iterator.getString())
    if walkables:
        client.clicked_snd.play()
        client.matrix.setupPassiveWalkableZone(walkables)
        client.subphase = 'passivewalkables'
    else:
        #TODO: show message "no walkable tile"
        print "no walkable tile"
        client.send.UPDATE_PARTY()
########NEW FILE########
__FILENAME__ = PATH
from direct.interval.IntervalGlobal import Sequence, Func
import json
import SequenceBuilder

def execute(client, iterator):
    charid = iterator.getString()
    orig = json.loads(iterator.getString())
    origdir = iterator.getUint8()
    dest = json.loads(iterator.getString())
    path = json.loads(iterator.getString())

    seq = Sequence()
    seq.append( Func(client.at.hide) )
    seq.append( Func(client.updateSpriteAnimation, charid, 'run') )
    seq.append( Func(client.matrix.clearZone) )
    seq.append( SequenceBuilder.characterMoveSequence(client, charid, path) )
    seq.append( Func(client.updateSpriteAnimation, charid) )
    seq.append( Func(client.moveCheck, charid, orig, origdir, dest) )
    seq.start()
########NEW FILE########
__FILENAME__ = START_BATTLE
from direct.gui.DirectGui import DirectFrame
from direct.interval.IntervalGlobal import Sequence, LerpColorInterval, Func
import json

# The teams are ready for the battle, stop the lobby BGM and initiate the battle
def execute(client, iterator):
    client.party = json.loads(iterator.getString32())
    client.transitionframe = DirectFrame( frameSize = ( -2, 2, -2, 2 ) )
    client.transitionframe.setTransparency(True)
    seq = Sequence()
    seq.append(LerpColorInterval(client.transitionframe, 2, (0,0,0,1), startColor=(0,0,0,0)))
    seq.append(Func(client.background.frame.destroy))
    seq.append(Func(client.music.stop))
    seq.append(Func(client.battle_init))
    seq.start()
########NEW FILE########
__FILENAME__ = START_FORMATION
from Config import GAME
import json, GUI

def execute(client, iterator):
    tilesets = json.loads(iterator.getString32())
    characters = json.loads(iterator.getString32())
    client.music.stop()
    client.music = base.loader.loadSfx(GAME+'/music/11.ogg')
    client.music.play()
    GUI.Formation(client.background.frame, tilesets, characters, client.send.FORMATION_READY)
########NEW FILE########
__FILENAME__ = UPDATE_PARTY_LIST
import json

# Party list has been updated, refresh the party list window
def execute(client, iterator):
    parties = json.loads(iterator.getString32())
    client.partylistwindow.refresh(parties)
########NEW FILE########
__FILENAME__ = WAIT_PASSIVE
from direct.interval.IntervalGlobal import Sequence, Func, Wait

def execute(client, iterator):
    charid = iterator.getString()
    direction = iterator.getUint8()
    
    client.inputs.ignoreAll()
    seq = Sequence()
    seq.append( Func(client.at.hide) )
    seq.append( Wait(0.5) )
    seq.append( Func(client.matrix.sprites[charid].setRealDir, direction) )
    seq.append( Wait(0.5) )
    seq.append( Func(client.inputs.ignoreAll) )
    seq.append( Func(client.send.UPDATE_PARTY) )
    seq.start()
########NEW FILE########
__FILENAME__ = WAIT_SUCCESS
def execute(client, iterator):
    client.send.UPDATE_PARTY()
########NEW FILE########
__FILENAME__ = WALKABLES_LIST
from Config import *
import json, GUI

def execute(client, iterator):
    charid = iterator.getString()
    walkables = json.loads(iterator.getString())
    if walkables:
        client.inputs.ignoreAll()
        GUI.Help(
            0, 25, 142, 60,
            'shadowed', 'Check',
            'Specify the point to move with\nthe cursor. Press the %c button\nto select.' % CIRCLE_BTN.upper(),
            lambda: client.setupWalkableTileChooser(charid, walkables),
            client.send.UPDATE_PARTY,
        )
    else:
        #TODO: show message "no walkable tile"
        print "no walkable tile"
        client.send.UPDATE_PARTY()
########NEW FILE########
__FILENAME__ = Cursor
from Config import *
from panda3d.core import TransparencyAttrib, Texture, CardMaker

class Cursor(object):

    def __init__(self, battleGraphics, matrixContainer):
        self.battleGraphics = battleGraphics
        self.matrixContainer = matrixContainer

        self.curtex = loader.loadTexture(GAME+'/textures/cursor.png')
        self.curtex.setMagfilter(Texture.FTNearest)
        self.curtex.setMinfilter(Texture.FTNearest)

        self.x = False
        self.y = False
        self.z = False

        self.cursor = loader.loadModel(GAME+'/models/slopes/flat')
        self.cursor.reparentTo( self.matrixContainer )
        self.cursor.setScale(3.7)
        self.cursor.setTransparency(TransparencyAttrib.MAlpha)
        self.cursor.setColor( 1, 1, 1, 1 )
        self.cursor.setTexture(self.curtex)

        pointertex = loader.loadTexture(GAME+'/textures/pointer.png')
        pointertex.setMagfilter(Texture.FTNearest)
        pointertex.setMinfilter(Texture.FTNearest)
        cm = CardMaker('card')
        cm.setFrame(-2, 2, -2, 2) 
        self.pointer = render.attachNewNode(cm.generate())
        self.pointer.setTexture(pointertex)
        self.pointer.setTransparency(True)
        self.pointer.setBillboardPointEye()
        self.pointer.reparentTo(render)
        self.pointer.setScale(256.0/240.0)

    def move(self, x, y, z, tile):
        self.cursor.detachNode()
        self.cursor = loader.loadModel(GAME+"/models/slopes/"+tile['slope'])
        self.cursor.reparentTo( self.matrixContainer )
        self.cursor.setScale(3.7, 3.7, 6.0/7.0*3.7*tile['scale'])
        self.cursor.setTransparency(TransparencyAttrib.MAlpha)
        self.cursor.setTexture(self.curtex)
        self.cursor.setPos(self.battleGraphics.logic2terrain((x, y, z+tile['depth']+0.1)))
        self.pointer.setPos(self.battleGraphics.logic2terrain((x, y, z+tile['depth']+12)))

        if tile['walkable']:
            self.cursor.setColor( 1, 1, 1, .75 )
        else:
            self.cursor.setColor( 1, 0, 0, .75 )

        self.x = x
        self.y = y
        self.z = z
########NEW FILE########
__FILENAME__ = DirectionChooser
from Config import *
from pandac.PandaModules import *
from direct.showbase.DirectObject import DirectObject
from panda3d.core import CollisionTraverser, CollisionNode, CollisionHandlerQueue, CollisionRay, BitMask32, CardMaker, NodePath, Texture, TextureStage
from direct.task.Task import Task

class DirectionChooser(DirectObject):
    
    def __init__(self, charid, sprite, camhandler, callback, cancelcallback):
    
        self.charid = charid
        self.sprite = sprite
        self.camhandler = camhandler
        self.callback = callback
        self.cancelcallback = cancelcallback
        self.initdir  = self.sprite.realdir
        self.hidir = None

        # Textures
        self.readytex = loader.loadTexture(GAME+'/textures/gui/direction.png')
        self.readytex.setMagfilter(Texture.FTNearest)
        self.readytex.setMinfilter(Texture.FTNearest)
        self.hovertex = loader.loadTexture(GAME+'/textures/gui/direction_hover.png')
        self.hovertex.setMagfilter(Texture.FTNearest)
        self.hovertex.setMinfilter(Texture.FTNearest)

        # Sounds
        self.hover_snd   = base.loader.loadSfx(GAME+'/sounds/hover.ogg')
        self.clicked_snd = base.loader.loadSfx(GAME+'/sounds/clicked.ogg')
        self.cancel_snd  = base.loader.loadSfx(GAME+'/sounds/cancel.ogg')

        # Buttons list
        self.directionbuttons = []

        # Buttons container
        self.directionRoot = sprite.node.attachNewNode( "directionRoot" )

        directionsdata = [
            { 'direction': '1', 'pos': ( 1.45, 0.0, 5) },
            { 'direction': '2', 'pos': ( 0.0, 1.45, 5) },
            { 'direction': '3', 'pos': (-1.45, 0.0, 5) },
            { 'direction': '4', 'pos': ( 0.0,-1.45, 5) }
        ]
        for directiondata in directionsdata:
            cm = CardMaker('card')
            cm.setFrame(-.5, .5, -.5, .5) 
            card = render.attachNewNode(cm.generate())
            card.setTexture(self.readytex)
            card.setTransparency(True)
            card.setBillboardPointEye()
            card.reparentTo(self.directionRoot)
            card.setPos(directiondata['pos'])
            card.setScale(256.0/240.0)

            self.directionbuttons.append(card)

            if int(directiondata['direction']) == int(self.initdir):
                self.hidir = directiondata['direction']
                card.setTexture(self.hovertex)

        self.accept(CIRCLE_BTN, self.onCircleClicked)
        self.accept(CROSS_BTN,  self.onCrossClicked)
        self.accept("arrow_up", lambda: self.onArrowClicked('up'))
        self.accept("arrow_down", lambda: self.onArrowClicked('down'))
        self.accept("arrow_left", lambda: self.onArrowClicked('left'))
        self.accept("arrow_right", lambda: self.onArrowClicked('right'))

    def onCircleClicked(self):
        self.directionRoot.removeNode()
        self.ignoreAll()
        self.clicked_snd.play()
        self.callback(self.charid, self.hidir)

    def onCrossClicked(self):
        self.directionRoot.removeNode()
        self.ignoreAll()
        self.cancel_snd.play()
        self.sprite.setRealDir(self.initdir)
        self.cancelcallback()

    def onArrowClicked(self, direction):

        self.hover_snd.play()

        for directionbutton in self.directionbuttons:
            directionbutton.setTexture(self.readytex)

        h = self.camhandler.container.getH()
        while h > 180:
            h -= 360
        while h < -180:
            h += 360

        if direction == 'up':
            if h >=    0 and h <  90:
                self.directionbuttons[0].setTexture(self.hovertex)
                self.hidir = '1'
            if h >=  -90 and h <   0:
                self.directionbuttons[3].setTexture(self.hovertex)
                self.hidir = '4'
            if h >= -180 and h < -90:
                self.directionbuttons[2].setTexture(self.hovertex)
                self.hidir = '3'
            if h >=   90 and h < 180:
                self.directionbuttons[1].setTexture(self.hovertex)
                self.hidir = '2'
        elif direction == 'down':
            if h >=    0 and h <  90:
                self.directionbuttons[2].setTexture(self.hovertex)
                self.hidir = '3'
            if h >=  -90 and h <   0:
                self.directionbuttons[1].setTexture(self.hovertex)
                self.hidir = '2'
            if h >= -180 and h < -90:
                self.directionbuttons[0].setTexture(self.hovertex)
                self.hidir = '1'
            if h >=   90 and h < 180:
                self.directionbuttons[3].setTexture(self.hovertex)
                self.hidir = '4'
        elif direction == 'left':
            if h >=    0 and h <  90:
                self.directionbuttons[1].setTexture(self.hovertex)
                self.hidir = '2'
            if h >=  -90 and h <   0:
                self.directionbuttons[0].setTexture(self.hovertex)
                self.hidir = '1'
            if h >= -180 and h < -90:
                self.directionbuttons[3].setTexture(self.hovertex)
                self.hidir = '4'
            if h >=   90 and h < 180:
                self.directionbuttons[2].setTexture(self.hovertex)
                self.hidir = '3'
        elif direction == 'right':
            if h >=    0 and h <  90:
                self.directionbuttons[3].setTexture(self.hovertex)
                self.hidir = '4'
            if h >=  -90 and h <   0:
                self.directionbuttons[2].setTexture(self.hovertex)
                self.hidir = '3'
            if h >= -180 and h < -90:
                self.directionbuttons[1].setTexture(self.hovertex)
                self.hidir = '2'
            if h >=   90 and h < 180:
                self.directionbuttons[0].setTexture(self.hovertex)
                self.hidir = '1'

        self.sprite.setRealDir(self.hidir)
########NEW FILE########
__FILENAME__ = Effect
from Config import *
from pandac.PandaModules import PandaNode,NodePath,Camera,TextNode,GeomTristrips,Geom,GeomVertexFormat,GeomVertexData,GeomVertexWriter,GeomNode,TransformState,OrthographicLens,TextureStage,TexGenAttrib,PNMImage,Texture,ColorBlendAttrib,CardMaker,TransparencyAttrib
from direct.interval.IntervalGlobal import *
import xml.etree.cElementTree as etree
import math

def transparencyKey(filename):
    image = PNMImage(GAME+'/textures/effects/'+filename)
    image.addAlpha()
    backgroundColor = None
    for y in range(image.getYSize()):
        for x in range(image.getXSize()):
            if backgroundColor == None:
                backgroundColor = Color(image.getRedVal(x, y), image.getGreenVal(x, y), image.getGreenVal(x, y), 0)
            if image.getRedVal(x, y) == backgroundColor.R and \
                image.getGreenVal(x, y) == backgroundColor.G and \
                image.getGreenVal(x, y) == backgroundColor.B:
                # Transparent
                image.setAlpha(x, y, 0.0)
            else:
                # Opaque
                image.setAlpha(x, y, 1.0) 
    return image

class Point:
    X = 0
    Y = 0
    Z = 0
    def __init__(self, x, y, z):
        self.X = x
        self.Y = y
        self.Z = z

class Line:
    Start = Point(0,0,0)
    End = Point(0,0,0)
    distanceLeadingUpToLine = 0
    distance = 0
    def __init__(self, start, end, distanceLeadingUpToLine):
        self.Start = start
        self.End = end
        self.distanceLeadingUpToLine = distanceLeadingUpToLine
        self.distance = ((self.End.X-self.Start.X)**2 + (self.End.Y-self.Start.Y)**2)**(1/2)
    def Distance(self, distanceOnLine):
        angleOfLineInRadians = atan2(self.End.Y - self.Start.Y, self.End.X - self.Start.X)
        return Point(self.Start.X + (distanceOnLine * cos(angleOfLineInRadians)), self.Start.Y + (distanceOnLine * sin(angleOfLineInRadians)))

class Tween:
    lineSegments = []
    colorList = []
    frameLength = 0
    advancementFunction = "linear"
    def __init__(self, frameLength, advancementFunction, points, colors):
        if points != None and points != []:
            if len(points) > 1:
                runningDistanceTotal = 0
                for i in range(1, len(points), 1):
                    line = Line(points[i - 1], points[i], runningDistanceTotal);
                    self.lineSegments.append(line)
                    runningDistanceTotal = runningDistanceTotal + line.distance
                    pass
                pass
            pass
        self.colorList = colors
        self.frameLength = frameLength
        self.advancementFunction = advancementFunction

    def hasColorComponent(self):
        if len(self.colorList) > 0:
            return True
        return False

    def colorFromFrame(self, frame):
        if frame < 1:
            return Color(1,1,1,1)
        elif frame == 1 or len(self.colorList) == 1:
            return self.colorList[0]
        elif frame >= self.frameLength:
            return self.colorList[len(colorList)-1]
        else:
            zeroToOneIndex = float(frame) / float(self.frameLength)
            startIndex = 0
            endIndex = 0
            zeroToOneStartIndex = 0
            zeroToOneEndIndex = 1.0
            for i in range(0, len(self.colorList)-1, 1):
                thisZeroToOneIndex = float(i+1) / float(len(self.colorList))
                if thisZeroToOneIndex == zeroToOneIndex:
                    startIndex = i
                    endIndex = i
                    zeroToOneStartIndex = zeroToOneIndex
                    zeroToOneEndIndex = zeroToOneIndex
                elif thisZeroToOneIndex >= zeroToOneIndex:
                    endIndex = i;
                    zeroToOneEndIndex = thisZeroToOneIndex
                    break # Exit after finding suitable data
                else:
                    startIndex = i
                    zeroToOneStartIndex = thisZeroToOneIndex
            if len(self.colorList) > 0 and float(zeroToOneEndIndex - zeroToOneStartIndex) > 0:
                transitionPercent = float(zeroToOneIndex - zeroToOneStartIndex) / float(zeroToOneEndIndex - zeroToOneStartIndex)
                return Color((1-transitionPercent) * self.colorList[startIndex].R + transitionPercent * self.colorList[endIndex].R, (1-transitionPercent) * self.colorList[startIndex].G + transitionPercent * self.colorList[endIndex].G, (1-transitionPercent) * self.colorList[startIndex].B + transitionPercent * self.colorList[endIndex].B, (1-transitionPercent) * self.colorList[startIndex].A + transitionPercent * self.colorList[endIndex].A)
            else:
                return Color(1,1,1,1)
    def lengthOfLineSegments(self):
        if len(self.lineSegments) > 0:
            return self.lineSegments[len(self.lineSegments)-1].distanceLeadingUpToLine + self.lineSegments[len(self.lineSegments)-1].distance;
        else:
            return 0
    def XYFromFrame(self, frame):
        if frame < 1:
            return Point(0, 0, 0)
        else:
            fullLength = self.lengthOfLineSegments()
            distance = float(frame-1)*fullLength/float(self.frameLength)
            if frame <= self.frameLength:
                lineThatContainsPoint = None
                for i in range(0, len(self.lineSegments)-1, 1):
                    if self.lineSegments[i].distanceLeadingUpToLine <= distance and (self.lineSegments[i].distanceLeadingUpToLine + self.lineSegments[i].distance) >= distance:
                        lineThatContainsPoints = self.lineSegments[i]
                        break
                if lineThatContainsPoint != None:
                    return lineThatContainsPoint.Distance(distance - lineThatContainsPoint.distanceLeadingUpToLine)
                else:
                    return Point(0,0,0)
            else:
                if len(self.lineSegments)>0:
                    return self.lineSegments[len(self.lineSegments)-1].End
                else:
                    return Point(0,0,0)

class Bound:
    X = 0
    Y = 0
    Width = 0
    Height = 0
    def __init__(self, x, y, width, height):
        self.X = x
        self.Y = y
        self.Width = width
        self.Height = height

class Color:
    R = 0
    G = 0
    B = 0
    A = 1
    def __init__(self, R, G, B, A):
        self.R = R
        self.G = G
        self.B = B
        self.A = A
    def printAsString(self):
        print str(self.R)+", "+str(self.G)+", "+str(self.B)+", "+str(self.A)
class Frame:
    bound = Bound(0, 0, 0, 0)
    s = 0
    t = 0
    S = 1
    T = 1
    blendMode = "overwrite"
    scaleX = 1
    scaleY = 1
    color = Color(1,1,1,1)
    rotationZ = 0
    def __init__(self, bound, s, t, S, T, blendMode, scaleX, scaleY, color, rotationZ):
        self.bound = bound
        self.s = s
        self.t = t
        self.S = S
        self.T = T
        self.blendMode = blendMode
        self.scaleX = scaleX
        self.scaleY = scaleY
        if color != None:
            self.color = color
        else: # TODO: Find logic error in color from frame.
            self.color = Color(1,1,1,1)
        self.rotationZ = rotationZ
    def printAsString(self):
        print "["+str(self)+"]::"
        print "   Bound: ["+str(self.bound.X)+", "+str(self.bound.Y)+"; "+str(self.bound.Width)+"x"+str(self.bound.Height)+"],"
        print "   (s, t; S, T): ["+str(self.s)+", "+str(self.t)+"; "+str(self.S)+", "+str(self.T)+"]," 
        print "   Blend: '"+self.blendMode+"'," 
        print "   Scale(x, y): ["+str(self.scaleX)+", "+str(self.scaleY)+"]," 
        print "   Color(R, G, B, A): ["+str(self.color.R)+", "+str(self.color.G)+", "+str(self.color.B)+", "+str(self.color.A)+"]," 
        print "   Rotation-Z: "+str(self.rotationZ)

class Effect:
    baseWidth = 0
    baseHeight = 0
    effectWidth = 1
    effectHeight = 1
    effectTargetMS = 143
    noSampling = False
    tex = None
    loadedFormat = None
    # Animation variables
    internalFrameIndex = 1
    startIndex = 1
    endIndex = 1
    loopEffect = False
    # XML variables
    tree = None
    frames = None
    colors = None
    tweens = None
    compositeFrames = None
    # Nodes
    consumedNodesList = None
    # Accessible object (nodePath)
    effectCameraNodePath = None
    effectCardNodePath = None
    # Constant value; Unit comparison for card size; basis is from cure, which is [140x110]
    cardDimensionBasis = [-5.0, 5.0, 0.0, 10.0, 140.0, 110.0]
    pixelScaleX = cardDimensionBasis[4]/(cardDimensionBasis[1]-cardDimensionBasis[0])
    pixelScaleZ = cardDimensionBasis[5]/(cardDimensionBasis[3]-cardDimensionBasis[2])
    effectIsCentered = True
    effectAdjustment = [0, 0, 0]
    def __init__(self, effectFileName, parent=None, loop=False, effectIsCentered=True, effectAdjustment=[0, 0, 0]):
        self.effectAdjustment = effectAdjustment
        self.loopEffect = loop
        self.effectIsCentered = effectIsCentered
        self.loadedFormat = None
        if effectFileName != None:
            effectFileNameSplit = effectFileName.split('.')
            self.loadedFormat = effectFileNameSplit[len(effectFileNameSplit)-2] # Get value at penultimate index
            if self.loadedFormat == effectFileNameSplit[0]:
                self.loadedFormat = None # Get rid of bad format name.
            pass
            
        # Load texture; supply alpha channel if it doesn't exist.
        p = transparencyKey(effectFileName)
        self.tex = Texture()
        self.tex.setup2dTexture(p.getXSize(), p.getYSize(), Texture.TUnsignedByte, Texture.FRgba)
        self.tex.load(p)
        if self.loadedFormat != None:
            try:
                self.tree = etree.parse("./"+GAME+"/effects/"+self.loadedFormat+"/sprite.xml")
            except IOError:
                self.loadedFormat = None
            pass
        if self.loadedFormat != None: 
            root = self.tree.getroot()
            self.frames = root.find('.//frames')
            self.colors = root.find('.//colors')
            self.tweens = root.find('.//motion-tweens')
            self.compositeFrames = root.find('.//composite-frames')
            self.baseWidth = 0 if root.attrib.get("base-width") == None else float(root.attrib.get("base-width"))
            self.baseHeight = 0 if root.attrib.get("base-height") == None else float(root.attrib.get("base-height"))
            self.effectWidth = 1 if root.attrib.get("frame-width") == None else float(root.attrib.get("frame-width"))
            self.effectHeight = 1 if root.attrib.get("frame-height") == None else float(root.attrib.get("frame-height"))
            self.effectTargetMS = 143 if root.attrib.get("target-ms") == None else float(root.attrib.get("target-ms"))
            self.startIndex = 1 if root.attrib.get("target-start") == None else int(root.attrib.get("target-start"))
            self.endIndex = 1 if root.attrib.get("target-end") == None else int(root.attrib.get("target-end"))
            self.noSampling = False if root.attrib.get("no-sampling") == None else bool(root.attrib.get("no-sampling"))
            if self.noSampling==True:
                self.tex.setMagfilter(Texture.FTNearest)
                self.tex.setMinfilter(Texture.FTNearest)
            cm = CardMaker('card-'+effectFileName)
            cardDeltaX = self.effectWidth / self.pixelScaleX
            cardDeltaZ = self.effectHeight / self.pixelScaleZ
            if self.effectIsCentered == True:
                cm.setFrame(0, 0, 0, 0)
                deltaX = (cardDeltaX/2.0) - (-cardDeltaX/2.0)
                deltaY = 0
                deltaZ = (cardDeltaZ/2.0) - (-cardDeltaZ/2.0)
                #occluder = OccluderNode('effect-parent-occluder', Point3((-cardDeltaX/2.0), 0, (-cardDeltaZ/2.0)), Point3((-cardDeltaX/2.0), 0, (cardDeltaZ/2.0)), Point3((cardDeltaX/2.0), 0, (cardDeltaZ/2.0)), Point3((cardDeltaX/2.0), 0, (-cardDeltaZ/2.0)))
            else:
                cm.setFrame(0, 0, 0, 0)
                deltaX = (cardDeltaX/2.0) - (-cardDeltaX/2.0)
                deltaY = 0
                deltaZ = cardDeltaZ - 0
                #occluder = OccluderNode('effect-parent-occluder', Point3((-cardDeltaX/2.0), 0, 0), Point3((-cardDeltaX/2.0), 0, cardDeltaZ), Point3((cardDeltaX/2.0), 0, cardDeltaZ), Point3((cardDeltaX/2.0), 0, 0))
            self.effectCardNodePath = render.attachNewNode(cm.generate())            
            self.effectCardNodePath.setBillboardPointEye()
            self.effectCardNodePath.reparentTo(parent)
            #occluder_nodepath = self.effectCardNodePath.attachNewNode(occluder)
            #self.effectCardNodePath.setOccluder(occluder_nodepath)
            emptyNode = NodePath('effect-parent-translator')
            emptyNode.reparentTo(self.effectCardNodePath)
            if effectIsCentered == True:
                emptyNode.setPos(-deltaX/2.0+self.effectAdjustment[0], 0+self.effectAdjustment[1], deltaZ/2.0+self.effectAdjustment[2])
            else:
                emptyNode.setPos(-deltaX/2.0+self.effectAdjustment[0], 0+self.effectAdjustment[1], deltaZ+self.effectAdjustment[2])
            #emptyNode.place()
            emptyNode.setSx(float(deltaX)/self.effectWidth)
            emptyNode.setSz(float(deltaZ)/self.effectHeight)
            self.effectCameraNodePath = emptyNode                        
            if parent != None:
                self.effectCardNodePath.reparentTo(parent)
            else:
                self.effectCardNodePath.reparentTo(render)
            #self.effectCardNodePath.place()
            self.effectCardNodePath.setBin("fixed", 40)
            self.effectCardNodePath.setDepthTest(False)
            self.effectCardNodePath.setDepthWrite(False)
        pass
    def getSequence(self):
        sequence = Sequence()
        for x in range(self.startIndex, self.endIndex, 1):
            sequence.append(Func(self.pandaRender))
            sequence.append(Func(self.advanceFrame))
            sequence.append(Wait(self.effectTargetMS * 0.001))
        sequence.append(Func(self.clearNodesForDrawing))
        sequence.append(Func(self.advanceFrame))
        sequence.append(Wait(self.effectTargetMS * 0.001))
        return sequence
        pass
    def hasEffectFinished(self):
        if self.internalFrameIndex > self.endIndex and self.loopEffect == False:
            return True
        else:
            return False
        pass
    def advanceFrame(self):
        if self.internalFrameIndex < self.endIndex:
            self.internalFrameIndex += 1
        elif self.internalFrameIndex == self.endIndex and self.loopEffect == True:
            self.internalFrameIndex = self.startIndex
        else:
            self.internalFrameIndex = self.endIndex + 1
            self.clearNodesForDrawing()
        pass
    def clearNodesForDrawing(self):
        if False:
            self.effectCameraNodePath.analyze()
        if self.consumedNodesList != None and self.consumedNodesList != []:
            for consumedNode in self.consumedNodesList:
                consumedNode.removeNode()
        self.consumedNodesList = []
        pass
    def pandaRender(self):
        frameList = []
        for node in self.compositeFrames.getiterator('composite-frame'):
            if node.tag == "composite-frame" and node.attrib.get("id") == str(self.internalFrameIndex):
                for frameCallNode in node:
                    for frameNode in self.frames.getiterator('frame'):
                        if frameNode.tag == "frame" and frameNode.attrib.get("id") == frameCallNode.attrib.get("id"):
                            offsetX = 0 if frameCallNode.attrib.get("offset-x") == None else float(frameCallNode.attrib.get("offset-x"))
                            offsetY = 0 if frameCallNode.attrib.get("offset-y") == None else float(frameCallNode.attrib.get("offset-y"))
                            tweenId = frameCallNode.attrib.get("tween")
                            frameInTween = 0 if frameCallNode.attrib.get("frame-in-tween") == None else int(frameCallNode.attrib.get("frame-in-tween"))
                            addWidth = 0 if frameNode.attrib.get("w") == None else float(frameNode.attrib.get("w"))
                            addHeight = 0 if frameNode.attrib.get("h") == None else float(frameNode.attrib.get("h"))
                            sInPixels = 0 if frameNode.attrib.get("s") == None else float(frameNode.attrib.get("s"))
                            tInPixels = 0 if frameNode.attrib.get("t") == None else float(frameNode.attrib.get("t"))
                            swInPixels = sInPixels + addWidth
                            thInPixels = tInPixels + addHeight
                            s = (sInPixels / self.baseWidth)
                            t = 1 - (tInPixels / self.baseHeight) # Complemented to deal with loading image upside down.
                            S = (swInPixels / self.baseWidth)
                            T = 1 - (thInPixels / self.baseHeight) # Complemented to deal with loading image upside down.
                            blend = "overwrite" if frameCallNode.attrib.get("blend") == None else frameCallNode.attrib.get("blend")
                            scaleX = 1 if frameCallNode.attrib.get("scale-x") == None else float(frameCallNode.attrib.get("scale-x"))
                            scaleY = 1 if frameCallNode.attrib.get("scale-y") == None else float(frameCallNode.attrib.get("scale-y"))
                            color = Color(1,1,1,1)
                            tweenHasColor = False
                            frameCallHasColor = False
                            frameCallColorName = frameCallNode.attrib.get("color-name")
                            if frameCallColorName != None:
                                # Get color at frame call as first resort.
                                frameCallHasColor = True
                                for colorNode in self.colors.getiterator('color'):
                                    if colorNode.tag == 'color' and colorNode.attrib.get("name") == frameCallColorName:
                                        R = 1 if colorNode.attrib.get("r") == None else float(colorNode.attrib.get("r"))
                                        G = 1 if colorNode.attrib.get("g") == None else float(colorNode.attrib.get("g"))
                                        B = 1 if colorNode.attrib.get("b") == None else float(colorNode.attrib.get("b"))
                                        A = 1 if colorNode.attrib.get("a") == None else float(colorNode.attrib.get("a"))
                                        color = Color(R, G, B, A)
                                        break # leave for loop when we find the correct color
                                pass

                            if tweenId != None and tweenId != "0":
                                # Get color at tween frame as second resort.
                                thisTween = None
                                frameLength = 1
                                advancementFunction = "linear"
                                foundTween = False
                                pointList = []
                                colorList = []
                                for tweenNode in self.tweens.getiterator('motion-tween'):
                                    if tweenNode.tag == "motion-tween" and tweenNode.attrib.get("id") == tweenId:
                                        foundTween = True
                                        frameLength = 1 if tweenNode.attrib.get("length-in-frames") == None else tweenNode.attrib.get("length-in-frames")
                                        advancementFunction = "linear" if tweenNode.attrib.get("advancement-function") == None else tweenNode.attrib.get("advancement-function")
                                        for pointOrColorNode in tweenNode.getiterator():
                                            if pointOrColorNode.tag == "point":
                                                pX = 0 if pointOrColorNode.attrib.get("x") == None else float(pointOrColorNode.attrib.get("x"))
                                                pY = 0 if pointOrColorNode.attrib.get("y") == None else float(pointOrColorNode.attrib.get("y"))
                                                pointList.append(Point(pX, pY, 0))
                                            elif pointOrColorNode.tag == "color-state":
                                                colorName = "white" if pointOrColorNode.attrib.get("name") == None else pointOrColorNode.attrib.get("name")
                                                for colorNode in self.colors.getiterator('color'):
                                                    if colorNode.tag == 'color' and colorNode.attrib.get("name") == colorName:
                                                        R = 1 if colorNode.attrib.get("r") == None else float(colorNode.attrib.get("r"))
                                                        G = 1 if colorNode.attrib.get("g") == None else float(colorNode.attrib.get("g"))
                                                        B = 1 if colorNode.attrib.get("b") == None else float(colorNode.attrib.get("b"))
                                                        A = 1 if colorNode.attrib.get("a") == None else float(colorNode.attrib.get("a"))
                                                        colorList.append(Color(R, G, B, A))
                                                        break # leave for loop when we find the correct color reference
                                            pass # Run through all child nodes of selected tween
                                        break # Exit after finding correct tween
                                pass
                                if foundTween:
                                    thisTween = Tween(frameLength, advancementFunction, pointList, colorList)
                                    offset = thisTween.XYFromFrame(frameInTween);
                                    offsetFromTweenX = int(offset.X);
                                    offsetFromTweenY = int(offset.Y);
                                    offsetX += int(offset.X);
                                    offsetY += int(offset.Y);
                                    if thisTween.hasColorComponent():
                                        tweenHasColor = True;
                                        if frameCallHasColor == False:
                                            color = thisTween.colorFromFrame(frameInTween);
                                    pass
                            if frameNode.attrib.get("color-name") != None and frameCallHasColor == False and tweenHasColor == False:
                                # Get color at frame definition as last resort.
                                for colorNode in colors.getiterator('color'):
                                    if colorNode.tag == 'color' and colorNode.attrib.get("name") == frameNode.attrib.get("color-name"):
                                        R = 1 if colorNode.attrib.get("r") == None else float(colorNode.attrib.get("r"))
                                        G = 1 if colorNode.attrib.get("g") == None else float(colorNode.attrib.get("g"))
                                        B = 1 if colorNode.attrib.get("b") == None else float(colorNode.attrib.get("b"))
                                        A = 1 if colorNode.attrib.get("a") == None else float(colorNode.attrib.get("a"))
                                        color = Color(R, G, B, A)
                                        break # leave for loop when we find the correct color
                                pass
                            rotationZ = 0 if frameCallNode.attrib.get("rotation-z") == None else float(frameCallNode.attrib.get("rotation-z"))
                            frameList.append(Frame(Bound(offsetX, offsetY, addWidth, addHeight), s, t, S, T, blend, scaleX, scaleY, color, rotationZ))
                    pass 
                break # Leave once we've found the appropriate frame

        # Prepare tracking list of consumed nodes.
        self.clearNodesForDrawing()
        # Make an identifier to tack onto primitive names in Panda3d's scene graph.
        frameIndexForName = 1
                
        # Loop through loaded frames that make up composite frame.
        for loadedFrame in frameList:              
            # For debugging purposes, print the object.
            if False:
                loadedFrame.printAsString()
            
            # Set up place to store primitive 3d object; note: requires vertex data made by GeomVertexData
            squareMadeByTriangleStrips = GeomTristrips(Geom.UHDynamic)
              
            # Set up place to hold 3d data and for the following coordinates:
            #   square's points (V3: x, y, z), 
            #   the colors at each point of the square (c4: r, g, b, a), and
            #   for the UV texture coordinates at each point of the square     (t2: S, T).
            vertexData = GeomVertexData('square-'+str(frameIndexForName), GeomVertexFormat.getV3c4t2(), Geom.UHDynamic)
            vertex = GeomVertexWriter(vertexData, 'vertex')
            color = GeomVertexWriter(vertexData, 'color')
            texcoord = GeomVertexWriter(vertexData, 'texcoord') 
              
            # Add the square's data
            # Upper-Left corner of square
            vertex.addData3f(-loadedFrame.bound.Width / 2.0, 0, -loadedFrame.bound.Height / 2.0)
            color.addData4f(loadedFrame.color.R,loadedFrame.color.G,loadedFrame.color.B,loadedFrame.color.A)
            texcoord.addData2f(loadedFrame.s, loadedFrame.T)

            # Upper-Right corner of square
            vertex.addData3f(loadedFrame.bound.Width / 2.0, 0, -loadedFrame.bound.Height / 2.0)
            color.addData4f(loadedFrame.color.R,loadedFrame.color.G,loadedFrame.color.B,loadedFrame.color.A)
            texcoord.addData2f(loadedFrame.S, loadedFrame.T)
            
            # Lower-Left corner of square
            vertex.addData3f(-loadedFrame.bound.Width / 2.0, 0, loadedFrame.bound.Height / 2.0)
            color.addData4f(loadedFrame.color.R,loadedFrame.color.G,loadedFrame.color.B,loadedFrame.color.A)
            texcoord.addData2f(loadedFrame.s, loadedFrame.t)
            
            # Lower-Right corner of square
            vertex.addData3f(loadedFrame.bound.Width / 2.0, 0, loadedFrame.bound.Height / 2.0)
            color.addData4f(loadedFrame.color.R,loadedFrame.color.G,loadedFrame.color.B,loadedFrame.color.A)
            texcoord.addData2f(loadedFrame.S, loadedFrame.t)

            # Pass data to primitive
            squareMadeByTriangleStrips.addNextVertices(4)
            squareMadeByTriangleStrips.closePrimitive()
            square = Geom(vertexData)
            square.addPrimitive(squareMadeByTriangleStrips)
            # Pass primtive to drawing node
            drawPrimitiveNode=GeomNode('square-'+str(frameIndexForName))    
            drawPrimitiveNode.addGeom(square)
            # Pass node to scene (effect camera)
            nodePath = self.effectCameraNodePath.attachNewNode(drawPrimitiveNode)
            # Linear dodge:
            if loadedFrame.blendMode == "darken":
                nodePath.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.MAdd, ColorBlendAttrib.OOneMinusFbufferColor, ColorBlendAttrib.OOneMinusIncomingColor))
                pass
            elif loadedFrame.blendMode == "multiply":
                nodePath.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.MAdd, ColorBlendAttrib.OFbufferColor, ColorBlendAttrib.OZero))
                pass
            elif loadedFrame.blendMode == "color-burn":
                nodePath.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.MAdd, ColorBlendAttrib.OZero, ColorBlendAttrib.OOneMinusIncomingColor))
                pass
            elif loadedFrame.blendMode == "linear-burn":
                nodePath.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.MAdd, ColorBlendAttrib.OZero, ColorBlendAttrib.OIncomingColor))
                pass
            elif loadedFrame.blendMode == "lighten":
                nodePath.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.MMax, ColorBlendAttrib.OIncomingColor, ColorBlendAttrib.OFbufferColor))
                pass
            elif loadedFrame.blendMode == "color-dodge":
                nodePath.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.MAdd, ColorBlendAttrib.OOne, ColorBlendAttrib.OOne))
                pass
            elif loadedFrame.blendMode == "linear-dodge":
                nodePath.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.MAdd, ColorBlendAttrib.OOne, ColorBlendAttrib.OOneMinusIncomingColor))
                pass
            else: # Overwrite:
                nodePath.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.MAdd, ColorBlendAttrib.OIncomingAlpha, ColorBlendAttrib.OOneMinusIncomingAlpha))
                pass
            nodePath.setDepthTest(False)
            # Apply texture
            nodePath.setTexture(self.tex)
            # Apply translation, then rotation, then scaling to node.
            nodePath.setPos((loadedFrame.bound.X + loadedFrame.bound.Width / 2.0, 1, -loadedFrame.bound.Y - loadedFrame.bound.Height / 2.0))
            nodePath.setR(loadedFrame.rotationZ)
            nodePath.setScale(loadedFrame.scaleX, 1, loadedFrame.scaleY)
            nodePath.setTwoSided(True)
            self.consumedNodesList.append(nodePath)
            frameIndexForName = frameIndexForName + 1
        # Loop continues on through each frame called in the composite frame.
        pass

########NEW FILE########
__FILENAME__ = GUI
from Config import *
import direct.directbase.DirectStart
from direct.showbase import DirectObject
from direct.gui.OnscreenText import OnscreenText 
from direct.gui.DirectGui import *
from direct.task import Task
from direct.actor import Actor
from direct.interval.IntervalGlobal import *
from pandac.PandaModules import *
import Sprite
import functools
from WindowNodeDrawer import WindowNodeDrawer
from BarNodeDrawer import Bar

u = 1.0/128.0
v = 1.0/120.0
hover_snd = base.loader.loadSfx(GAME+"/sounds/hover.ogg")
clicked_snd = base.loader.loadSfx(GAME+"/sounds/clicked.ogg")
cancel_snd = base.loader.loadSfx(GAME+"/sounds/cancel.ogg")
regularscale = 2*16.0/240.0
scale = 2*12.0/240.0
regularfont = loader.loadFont(GAME+'/fonts/fft')
font3 = loader.loadFont(GAME+'/fonts/fft3')
font4 = loader.loadFont(GAME+'/fonts/fft4')
coordsfont = loader.loadFont(GAME+'/fonts/fftcoords')
whitefont = loader.loadFont(GAME+'/fonts/fftwhite')
smwhitefont = loader.loadFont(GAME+'/fonts/fftwhite-small-caps')

class Coords(DirectObject.DirectObject):

    def __init__(self, tile):

        self.coordstn = TextNode('tn')
        self.coordstn.setFont(coordsfont)
        self.coordstn.setAlign(self.coordstn.ARight)
        self.coordstn.setTextColor(1,1,1,1)
        self.tnp = aspect2d.attachNewNode(self.coordstn)
        self.tnp.setScale(scale)
        self.tnp.setPos(v*112, 0, v*66)

        self.update(tile)

    def update(self, tile):
        self.coordstn.setText(str(tile['z']/2).replace('.0','').replace('.5','a')+'h')

    def destroy(self):
        self.tnp.removeNode()

class Background(DirectObject.DirectObject):

    def __init__(self, command):
        
        tex = loader.loadTexture(GAME+'/textures/gui/loadingbackground.png')
        tex.setMagfilter(Texture.FTNearest)
        tex.setMinfilter(Texture.FTNearest)

        base.setBackgroundColor(.03125, .03125, .03125)

        self.frame = DirectFrame( color = (1, 1, 1, 1), frameTexture = tex, frameSize = ( -v*128, v*128, -v*128, v*128 ), scale = 10 )
        self.frame.setTransparency(True)

        seq = Sequence()
        i = LerpScaleInterval(self.frame, 0.1, 1, startScale=10 )
        seq.append(i)
        seq.append( Wait(0.5) )
        seq.append( Func(command) )
        seq.start()

class Blueprint(DirectObject.DirectObject):

    def __init__(self, image):

        tex = loader.loadTexture(GAME+'/textures/blueprints/'+image+'.png')
        tex.setMagfilter(Texture.FTNearest)
        tex.setMinfilter(Texture.FTNearest)

        base.setBackgroundColor(0,0,1)

        self.frame = DirectFrame(
            color = (1, 1, 1, 1),
            frameTexture = tex,
            frameSize = ( -v*128.0, v*128.0, -v*128.0, v*128.0 ),
            scale = 1,
            sortOrder= -2,
        )
        self.frame.setTransparency(True)

class LoginWindow(DirectObject.DirectObject):

    def __init__(self, command):
        
        self.frame = DirectFrame(
            frameColor = (1, 1, 1, .25),
            frameSize = ( -v*56, v*56, -v*22, v*22 ),
            pos = (v*10, 0, -v*0),
            geom = WindowNodeDrawer(112, 44, 'shadowed', 'Login'),
            scale = 0.1,
        )
        self.frame.setTransparency(True)

        self.loginLabel = DirectLabel(
            text = 'Username:',
            color = (0,0,0,0),
            scale = regularscale,
            text_font = regularfont,
            text_fg = (1,1,1,1),
            text_align = TextNode.ALeft,
            parent = self.frame,
        )
        self.loginLabel.setPos(-v*50, 0, v*4)

        self.loginEntry = DirectEntry(
            color = (0,0,0,0),
            scale = regularscale,
            numLines = 1,
            focus = 1,
            text_font = regularfont,
            text_fg = (1,1,1,1),
            parent = self.frame
        )
        self.loginEntry.setPos(-v*6, 0, v*4)

        self.passwordLabel = DirectLabel(
            text = 'Password:',
            color = (0,0,0,0),
            scale = regularscale,
            text_font = regularfont,
            text_fg = (1,1,1,1),
            text_align = TextNode.ALeft,
            parent = self.frame,
        )
        self.passwordLabel.setPos(-v*50, 0, -v*12)

        self.passwordEntry = DirectEntry(
            color = (0,0,0,0),
            scale = regularscale,
            numLines = 1,
            text_font = regularfont,
            text_fg = (1,1,1,1),
            obscured = True,
            parent = self.frame,
        )
        self.passwordEntry.setPos(-v*6, 0, -v*12)

        connectButton = DirectButton(
            scale = regularscale,
            text  = ("Connect", "Connect", "Connect", "disabled"),
            command = command,
            color = (.62, .6, .5, 1),
            text_font = regularfont,
            text_fg = (1,1,1,1),
            rolloverSound = hover_snd,
            clickSound = clicked_snd,
            pressEffect = 0,
            pad = (.15,.15),
            parent = self.frame
        )
        connectButton.setPos(v*37, 0, -v*40)

        seq = Sequence()
        i = LerpScaleInterval(self.frame, 0.1, 1, startScale=0.1 )
        seq.append(i)
        seq.start()

    def commandanddestroy(self, command):
        seq = Sequence()
        i = LerpScaleInterval(self.frame, 0.1, 0.1, startScale=1 )
        seq.append(i)
        seq.append( Func(self.frame.destroy) )
        seq.append( Wait(0.5) )
        seq.append( Func(command) )
        seq.start()

class PartyListWindow(DirectObject.DirectObject):

    def __init__(self, command, createpartycommand):

        self.command = command
        self.createpartycommand = createpartycommand

        tex = loader.loadTexture(GAME+'/textures/gui/parties_window.png')
        tex.setMagfilter(Texture.FTNearest)
        tex.setMinfilter(Texture.FTNearest)
    
        self.frame = DirectFrame( frameTexture = tex, color = (1, 1, 1, 1), frameSize = ( -v*128.0, v*128.0, -v*128.0, v*128.0 ), scale=0.1 )
        self.frame.setTransparency(True)
        
        cptexture = loader.loadTexture(GAME+'/textures/gui/create_party.png')
        cptexture.setMagfilter(Texture.FTNearest)
        cptexture.setMinfilter(Texture.FTNearest)

        self.cpframe = DirectFrame(
            frameTexture = cptexture,
            frameColor = (1, 1, 1, 1),
            frameSize = ( -v*32.0, v*32.0, -v*8.0, v*8.0 ),
            pos = (0, 0, -.8),
            scale = 1.0,
        )
        self.cpframe.setTransparency(True)
        
        Sequence(
            Parallel(
                LerpScaleInterval(self.frame, 0.1, 1, startScale=0.1 ),
                LerpPosInterval(self.cpframe, 0.25, (0, 0, -.8), (0, 0, -1.0)),
            ),
            Func( self.acceptAll ),
        ).start()

    def acceptAll(self):
        self.accept(TRIANGLE_BTN, self.onTriangleClicked)

    def onTriangleClicked(self):
        clicked_snd.play()
        self.commandAndDestroy(self.createpartycommand)

    def commandAndDestroy(self,command):
        Sequence(
            Parallel(
                LerpScaleInterval(self.frame, 0.1, 0.1, startScale=1),
                LerpPosInterval(self.cpframe, 0.25, (0, 0, -1.0), (0, 0, -0.8)),
            ),
            Func(self.ignoreAll),
            Func(self.cpframe.destroy),
            Func(self.frame.destroy),
            Func(command),
        ).start()

    def refresh(self, parties):

        for child in self.frame.getChildren():
            child.removeNode()

        buttons = {}
        commands = {}
        for i,key in enumerate(parties):
            nameLabel = DirectLabel(
                color = (0,0,0,0),
                text = parties[key]['name'],
                scale = regularscale,
                text_font = regularfont,
                text_fg = (1,1,1,1),
                text_align = TextNode.ALeft,
                parent = self.frame
            )
            nameLabel.setPos(-v*93, 0, v*49 - i*v*16)

            creatorLabel = DirectLabel(
                color = (0,0,0,0),
                text = parties[key]['creator'],
                scale = regularscale,
                text_font = regularfont,
                text_fg = (1,1,1,1),
                text_align = TextNode.ALeft,
                parent = self.frame
            )
            creatorLabel.setPos(-v*30, 0, v*49 - i*v*16)

            mapLabel = DirectLabel(
                color = (0,0,0,0),
                text = parties[key]['map']['name'],
                scale = regularscale,
                text_font = regularfont,
                text_fg = (1,1,1,1),
                text_align = TextNode.ALeft,
                parent = self.frame
            )
            mapLabel.setPos(v*20, 0, v*49 - i*v*16)
            
            commands[key] = functools.partial(self.command, key)
            commands[key].__name__ = str(key)
            buttons[key] = DirectButton(
                text  = (str(len(parties[key]['players']))+'/'+str(len(parties[key]['map']['tilesets'])), "Join", "Join", "Full"),
                command = self.commandAndDestroy,
                extraArgs = [ commands[key] ],
                scale = regularscale,
                text_font = regularfont,
                text_fg = (1,1,1,1),
                text_align = TextNode.ALeft,
                rolloverSound = hover_snd,
                clickSound = clicked_snd,
                pressEffect = 0,
                parent = self.frame
            )
            buttons[key].setPos(v*80, 0, v*49 - i*v*16)

            if len(parties[key]['players']) >= len(parties[key]['map']['tilesets']):
                buttons[key]['state'] = DGG.DISABLED

class MoveCheck(DirectObject.DirectObject):

    def __init__(self, command, cancelcommand):

        self.offset = -10
        self.height = 16
        self.index = 0
        self.cancelcommand = cancelcommand

        self.buttons = [
            { 'text': 'Yes',   'enabled': True, 'pos': (v*45.5,0,v*(self.offset-self.height*0)), 'command': command       },
            { 'text': 'No',    'enabled': True, 'pos': (v*45.5,0,v*(self.offset-self.height*1)), 'command': cancelcommand },
        ]

        tex = loader.loadTexture(GAME+'/textures/gui/move_check.png')
        tex.setMagfilter(Texture.FTNearest)
        tex.setMinfilter(Texture.FTNearest)

        handtexture = loader.loadTexture(GAME+'/textures/gui/hand.png')
        handtexture.setMagfilter(Texture.FTNearest)
        handtexture.setMinfilter(Texture.FTNearest)

        self.frame = DirectFrame(
            frameTexture = tex,
            frameColor = (1, 1, 1, 1),
            frameSize = ( -v*128.0, v*128.0, -v*64.0, v*64.0 ),
            pos = (0, 0, 0),
            scale = 0.1,
        )
        self.frame.setTransparency(True)

        self.hand = DirectFrame(
            frameTexture = handtexture,
            frameColor = (1, 1, 1, 1),
            frameSize = ( -v*8, v*8, -v*8, v*8 ),
            pos = self.buttons[0]['pos'],
            parent = self.frame
        )

        messageLabel = DirectLabel(
            color = (0,0,0,0),
            text = 'Are you sure you want to move here?',
            scale = regularscale,
            text_font = regularfont,
            text_fg = (1,1,1,1),
            text_align = TextNode.ALeft,
            parent = self.frame,
            pos = (-v*75, 0, v*19)
        )

        for i,button in enumerate(self.buttons):
            label = DirectLabel(
                color = (0,0,0,0),
                text = button['text'],
                scale = regularscale,
                text_font = regularfont,
                text_fg = (1,1,1,1),
                text_align = TextNode.ALeft,
                parent = self.frame,
                pos = (v*57, 0, v*(self.offset-3-self.height*i))
            )
            if not button['enabled']:
                label['text_fg'] = (.375,.34375,.28125,1)

        seq = Sequence()
        seq.append(LerpScaleInterval(self.frame, 0.1, 1, startScale=0.1))
        seq.append(Func(self.acceptAll))
        seq.start()

    def acceptAll(self):
        self.accept(CROSS_BTN,  self.onCrossClicked)
        self.accept(CIRCLE_BTN, self.onCircleClicked)
        self.accept("arrow_down",        lambda: self.updateIndex( 1))
        self.accept("arrow_down-repeat", lambda: self.updateIndex( 1))
        self.accept("arrow_up",          lambda: self.updateIndex(-1))
        self.accept("arrow_up-repeat",   lambda: self.updateIndex(-1))

    def updateIndex(self, direction):
        hover_snd.play()
        next = self.index + direction
        if next == len(self.buttons):
            next = 0
        if next == -1:
            next = len(self.buttons)-1
        self.hand.setPos(self.buttons[next]['pos'])
        self.index = next

    def onCircleClicked(self):
        if self.buttons[self.index]['enabled']:
            clicked_snd.play()
            self.commandAndDestroy(self.buttons[self.index]['command'])

    def onCrossClicked(self):
        cancel_snd.play()
        self.commandAndDestroy(self.cancelcommand)

    def commandAndDestroy(self,command):
        seq = Sequence()
        seq.append(LerpScaleInterval(self.frame, 0.1, 0.1, startScale=1))
        seq.append(Func(self.ignoreAll))
        seq.append(Func(self.frame.destroy))
        seq.append(Func(command))
        seq.start()

class AttackCheck(DirectObject.DirectObject):

    def __init__(self, command, cancelcommand):

        self.offset = -18
        self.height = 16
        self.index = 0
        self.cancelcommand = cancelcommand

        self.buttons = [
            { 'text': 'Execute', 'enabled': True, 'pos': (-v*8.5,0,v*(self.offset-self.height*0)), 'command': command       },
            { 'text': 'Quit',    'enabled': True, 'pos': (-v*8.5,0,v*(self.offset-self.height*1)), 'command': cancelcommand },
        ]

        tex = loader.loadTexture(GAME+'/textures/gui/attack_check.png')
        tex.setMagfilter(Texture.FTNearest)
        tex.setMinfilter(Texture.FTNearest)

        handtexture = loader.loadTexture(GAME+'/textures/gui/hand.png')
        handtexture.setMagfilter(Texture.FTNearest)
        handtexture.setMinfilter(Texture.FTNearest)

        self.frame = DirectFrame(
            frameTexture = tex,
            frameColor = (1, 1, 1, 1),
            frameSize = ( -v*64.0, v*64.0, -v*64.0, v*64.0 ),
            pos = (-v*1.0, 0, v*10.0),
            scale = 0.1,
        )
        self.frame.setTransparency(True)

        self.hand = DirectFrame(
            frameTexture = handtexture,
            frameColor = (1, 1, 1, 1),
            frameSize = ( -v*8, v*8, -v*8, v*8 ),
            pos = self.buttons[0]['pos'],
            parent = self.frame
        )

        messageLabel = DirectLabel(
            color = (0,0,0,0),
            text = 'Executing action.\nOK?',
            scale = regularscale,
            text_font = regularfont,
            text_fg = (1,1,1,1),
            text_align = TextNode.ALeft,
            parent = self.frame,
            pos = (-v*33, 0, v*27)
        )

        for i,button in enumerate(self.buttons):
            label = DirectLabel(
                color = (0,0,0,0),
                text = button['text'],
                scale = regularscale,
                text_font = regularfont,
                text_fg = (1,1,1,1),
                text_align = TextNode.ALeft,
                parent = self.frame,
                pos = (v*3, 0, v*(self.offset-3-self.height*i))
            )
            if not button['enabled']:
                label['text_fg'] = (.375,.34375,.28125,1)

        seq = Sequence()
        seq.append(LerpScaleInterval(self.frame, 0.1, 1, startScale=0.1))
        seq.append(Func(self.acceptAll))
        seq.start()

    def acceptAll(self):
        self.accept(CROSS_BTN,  self.onCrossClicked)
        self.accept(CIRCLE_BTN, self.onCircleClicked)
        self.accept("arrow_down",        lambda: self.updateIndex( 1))
        self.accept("arrow_down-repeat", lambda: self.updateIndex( 1))
        self.accept("arrow_up",          lambda: self.updateIndex(-1))
        self.accept("arrow_up-repeat",   lambda: self.updateIndex(-1))

    def updateIndex(self, direction):
        hover_snd.play()
        next = self.index + direction
        if next == len(self.buttons):
            next = 0
        if next == -1:
            next = len(self.buttons)-1
        self.hand.setPos(self.buttons[next]['pos'])
        self.index = next

    def onCircleClicked(self):
        if self.buttons[self.index]['enabled']:
            clicked_snd.play()
            self.commandAndDestroy(self.buttons[self.index]['command'])

    def onCrossClicked(self):
        cancel_snd.play()
        self.commandAndDestroy(self.cancelcommand)

    def commandAndDestroy(self,command):
        seq = Sequence()
        seq.append(LerpScaleInterval(self.frame, 0.1, 0.1, startScale=1))
        seq.append(Func(self.ignoreAll))
        seq.append(Func(self.frame.destroy))
        seq.append(Func(command))
        seq.start()

# Display an help message, the player can confirm or cancel
class Help(DirectObject.DirectObject):

    def __init__(self, x, y, w, h, style, title, message, command, cancelcommand):

        self.command = command
        self.cancelcommand = cancelcommand

        self.frame = DirectFrame(
            frameColor = (1, 1, 1, 0),
            frameSize = ( -v*w/2.0, v*w/2.0, -v*h/2.0, v*h/2.0 ),
            pos = (v*x, 0, v*y),
            geom = WindowNodeDrawer(w, h, style, title),
            scale=0.1,
        )
        self.frame.setTransparency(True)

        messageLabel = DirectLabel(
            color = (0,0,0,0),
            text = message,
            scale = regularscale,
            text_font = regularfont,
            text_fg = (1,1,1,1),
            text_align = TextNode.ALeft,
            parent = self.frame,
            pos = (-v*(w/2-6), 0, v*(h/2-17))
        )
        
        seq = Sequence()
        seq.append(LerpScaleInterval(self.frame, 0.1, 1, startScale=0.1))
        seq.append(Func(self.acceptAll))
        seq.start()

    def acceptAll(self):
        self.accept(CROSS_BTN,  self.onCrossClicked)
        self.accept(CIRCLE_BTN, self.onCircleClicked )

    def onCircleClicked(self):
        clicked_snd.play()
        self.commandAndDestroy(self.command)

    def onCrossClicked(self):
        cancel_snd.play()
        self.commandAndDestroy(self.cancelcommand)

    def commandAndDestroy(self, command):
        clicked_snd.play()
        seq = Sequence()
        seq.append(LerpScaleInterval(self.frame, 0.1, 0.1, startScale=1))
        seq.append(Func(self.ignoreAll))
        seq.append(Func(self.frame.destroy))
        seq.append(Func(command))
        seq.start()

class CharBarsLeft:

    def __init__(self, char):

        self.fbgframe = DirectFrame(
            frameColor=(1, 1, 1, 0),
            geom = WindowNodeDrawer(37, 53, 'flat'),
            pos = (-2, 0, -v*82)
        )
        self.fbgframe.setTransparency(True)

        facetex = loader.loadTexture(GAME+'/textures/sprites/'+char['sprite']+'_face.png')
        facetex.setMagfilter(Texture.FTNearest)
        facetex.setMinfilter(Texture.FTNearest)
        
        self.face = DirectFrame(
            frameTexture = facetex, 
            frameColor=(1, 1, 1, 1),
            frameSize = ( 0, v*32, 0, v*64 ),
            parent = self.fbgframe,
        )
        self.face.setPos(-v*17, 0, -v*31)
        
        self.frame = DirectFrame(
            frameColor=(1, 1, 1, 0),
            frameSize = ( -v*64.0, v*64.0, -v*32.0, v*32.0 ),
            parent = self.fbgframe
        )
        self.frame.setPos(v*46, 0, -v*9)
        self.frame.setTransparency(True)

        bar = Bar(bar='bar-1')
        bar.updateTo(int(float(char['hp'])/float(char['hpmax'])*100))
        self.hpbar = DirectFrame(
            frameColor=(1, 1, 1, 1),
            frameSize=(0, 0, 0, 0), 
            parent = self.fbgframe,
            geom = bar.container,
            pos = (v*24, 0, -v*2),
        )
        self.hpbar.setTransparency(True)

        bar = Bar(bar='bar-2')
        bar.updateTo(int(float(char['mp'])/float(char['mpmax'])*100))
        self.mpbar = DirectFrame(
            frameColor=(1, 1, 1, 1),
            frameSize=(0, 0, 0, 0), 
            parent = self.fbgframe,
            geom = bar.container,
            pos = (v*24, 0, -v*13),
        )
        self.mpbar.setTransparency(True)

        bar = Bar(bar='bar-3')
        bar.updateTo(int(char['ct']))
        self.ctbar = DirectFrame(
            frameColor=(1, 1, 1, 1),
            frameSize=(0, 0, 0, 0), 
            parent = self.fbgframe,
            geom = bar.container,
            pos = (v*24, 0, -v*24)
        )
        self.ctbar.setTransparency(True)

        infos = [
            { 'x':  12, 'z':  23, 'text':  '%02d' % char['lv']   , 'font':   whitefont },
            { 'x':  43, 'z':  23, 'text':  '%02d' % char['exp']  , 'font':   whitefont },
            { 'x':  15, 'z':   9, 'text':  '%03d' % char['hp']   , 'font':   whitefont },
            { 'x':  28, 'z':   5, 'text': '/%03d' % char['hpmax'], 'font':   whitefont },
            { 'x':  15, 'z':  -2, 'text':  '%03d' % char['mp']   , 'font':   whitefont },
            { 'x':  28, 'z':  -6, 'text': '/%03d' % char['mpmax'], 'font':   whitefont },
            { 'x':  15, 'z': -13, 'text':  '%03d' % char['ct']   , 'font':   whitefont },
            { 'x':  28, 'z': -17, 'text':  '/100'                , 'font':   whitefont },
            { 'x': -33, 'z':   8, 'text':    'Hp'                , 'font': smwhitefont },
            { 'x': -33, 'z':  -3, 'text':    'Mp'                , 'font': smwhitefont },
            { 'x': -33, 'z': -13, 'text':    'Ct'                , 'font': smwhitefont },
            { 'x':   0, 'z':  23, 'text':   'Lv.'                , 'font': smwhitefont },
            { 'x':  27, 'z':  23, 'text':  'Exp.'                , 'font': smwhitefont },
        ]
        
        for info in infos:
            label = DirectLabel(
                text = info['text'],
                color = (1, 1, 1, 0),
                scale = scale,
                text_font = info['font'],
                text_fg = (1, 1, 1, 1),
                text_align = TextNode.ALeft,
                parent = self.frame,
            )
            label.setPos(v*info['x'], 0, v*info['z'])

        i1 = LerpPosInterval(self.fbgframe, 0.2, (-u*104,0,-u*82), (-2,0,-u*82))
        s = Sequence(i1)
        s.start()

    def hide(self):
        if self.fbgframe:
            i1 = LerpPosInterval(self.fbgframe, 0.2, (-2,0,-u*82), (-u*104,0,-u*82))
            i2 = Func( self.fbgframe.destroy )
            s = Sequence(i1,i2)
            s.start()

class CharBarsRight:

    def __init__(self, char):

        self.fbgframe = DirectFrame(
            frameColor=(1, 1, 1, 0),
            geom = WindowNodeDrawer(37, 53, 'flat'),
            pos = (2, 0, -v*82)
        )
        self.fbgframe.setTransparency(True)
        
        facetex = loader.loadTexture(GAME+'/textures/sprites/'+char['sprite']+'_face.png')
        facetex.setMagfilter(Texture.FTNearest)
        facetex.setMinfilter(Texture.FTNearest)
        
        self.face = DirectFrame(
            frameTexture = facetex, 
            frameColor=(1, 1, 1, 1),
            frameSize = ( 0, v*32, 0, v*64 ),
            parent = self.fbgframe,
        )
        self.face.setPos(-v*(59-42), 0, -v*31)
        
        self.frame = DirectFrame(
            frameColor=(1, 1, 1, 0),
            frameSize = ( -v*64.0, v*64.0, -v*32.0, v*32.0 ),
            parent = self.fbgframe,
            pos = (-v*64, 0, v*7)
        )
        self.frame.setTransparency(True)

        bar = Bar(bar='bar-1')
        bar.updateTo(int(float(char['hp'])/float(char['hpmax'])*100))
        self.hpbar = DirectFrame(
            frameColor=(1, 1, 1, 1),
            frameSize=(0, 0, 0, 0),
            parent = self.fbgframe,
            geom = bar.container,
            pos = (-v*87, 0, v*14),
        )
        self.hpbar.setTransparency(True)
        
        bar = Bar(bar='bar-2')
        bar.updateTo(int(float(char['mp'])/float(char['mpmax'])*100))
        self.mpbar = DirectFrame(
            frameColor=(1, 1, 1, 1),
            frameSize=(0, 0, 0, 0),
            parent = self.fbgframe,
            geom = bar.container,
            pos = (-v*87, 0, v*3),
        )
        self.mpbar.setTransparency(True)
        
        bar = Bar(bar='bar-3')
        bar.updateTo(int(char['ct']))
        self.ctbar = DirectFrame(
            frameColor=(1, 1, 1, 1),
            frameSize=(0, 0, 0, 0),
            parent = self.fbgframe,
            geom = bar.container,
            pos = (-v*87, 0, -v*8),
        )
        self.ctbar.setTransparency(True)

        infos = [
            { 'x':   15, 'z': -31, 'text':  '%02d' % char['lv']   , 'font':   whitefont },
            { 'x':   48, 'z': -31, 'text':  '%02d' % char['exp']  , 'font':   whitefont },
            { 'x':   14, 'z':   7, 'text':  '%03d' % char['hp']   , 'font':   whitefont },
            { 'x':   28, 'z':   3, 'text': '/%03d' % char['hpmax'], 'font':   whitefont },
            { 'x':   14, 'z':  -4, 'text':  '%03d' % char['mp']   , 'font':   whitefont },
            { 'x':   28, 'z':  -8, 'text': '/%03d' % char['mpmax'], 'font':   whitefont },
            { 'x':   14, 'z': -15, 'text':  '%03d' % char['ct']   , 'font':   whitefont },
            { 'x':   28, 'z': -19, 'text':  '/100'                , 'font':   whitefont },            
            { 'x':  -33, 'z':   8, 'text':    'Hp'                , 'font': smwhitefont },
            { 'x':  -33, 'z':  -3, 'text':    'Mp'                , 'font': smwhitefont },
            { 'x':  -33, 'z': -13, 'text':    'Ct'                , 'font': smwhitefont },
            { 'x':    3, 'z': -31, 'text':   'Lv.'                , 'font': smwhitefont },
            { 'x':   31, 'z': -31, 'text':  'Exp.'                , 'font': smwhitefont },
        ]
        
        for info in infos:
            label = DirectLabel(
                text = info['text'],
                color = (1, 1, 1, 0),
                scale = scale,
                text_font = info['font'],
                text_fg = (1,1,1,1),
                text_align = TextNode.ALeft,
                parent = self.frame,
                sortOrder = 100
            )
            label.setPos(v*info['x'], -1, v*info['z'])

        i1 = LerpPosInterval(self.fbgframe, 0.2, (u*107,0,-u*82), (2,0,-u*82))
        s = Sequence(i1)
        s.start()

    def hide(self):
        if self.fbgframe:
            i1 = LerpPosInterval(self.fbgframe, 0.2, (2,0,-u*82), (u*107,0,-u*82))
            i2 = Func( self.fbgframe.destroy )
            s = Sequence(i1,i2)
            s.start()

class CharCard:

    def __init__(self, char):
        blacktex = loader.loadTexture(GAME+'/textures/gui/black.png')
        blacktex.setMagfilter(Texture.FTNearest)
        blacktex.setMinfilter(Texture.FTNearest)

        self.blackframe = DirectFrame(
                frameTexture = blacktex, 
                frameColor=(1, 1, 1, 1),
                frameSize = ( -2, 2, -v*64.0, v*64.0 ),
                sortOrder = -1,
        )
        self.blackframe.setTransparency(True)
        self.blackframe.setPos(0, 0, u*-82)

        tex = loader.loadTexture(GAME+'/textures/gui/char_card.png')
        tex.setMagfilter(Texture.FTNearest)
        tex.setMinfilter(Texture.FTNearest)

        self.frame = DirectFrame(
            frameTexture = tex, 
            frameColor=(1, 1, 1, 1),
            frameSize = ( -v*64.0, v*64.0, -v*32.0, v*32.0 ),
        )
        self.frame.setTransparency(True)
        self.frame.setPos(2, 0, -u*85)

        self.name = DirectLabel(
            text = char['name'],
            color = (0,0,0,0),
            scale = regularscale,
            text_font = regularfont,
            text_fg = (1,1,1,1),
            text_align = TextNode.ALeft,
            parent = self.frame
        )
        self.name.setPos(-v*33, 0, v*12)

        self.name = DirectLabel(
            text = char['job'],
            color = (0,0,0,0),
            scale = regularscale,
            text_font = regularfont,
            text_fg = (1,1,1,1),
            text_align = TextNode.ALeft,
            parent = self.frame
        )
        self.name.setPos(-v*33, 0, -v*4)

        teamcolors = ['blue','red','green']
        ledtex = loader.loadTexture(GAME+'/textures/gui/led_'+teamcolors[int(char['team'])]+'.png')
        ledtex.setMagfilter(Texture.FTNearest)
        ledtex.setMinfilter(Texture.FTNearest)

        self.led = DirectFrame(
            frameTexture = ledtex, 
            frameColor=(1, 1, 1, 1),
            frameSize = ( -.0625, .0625, -.0625, .0625 ),
            parent = self.frame
        )
        self.led.setTransparency(True)
        self.led.setPos(-v*49, 0, v*18)

        signs = ['aries','scorpio']
        signtex = loader.loadTexture(GAME+'/textures/gui/'+signs[int(char['sign'])]+'.png')
        signtex.setMagfilter(Texture.FTNearest)
        signtex.setMinfilter(Texture.FTNearest)

        self.sign = DirectFrame(
            frameTexture = signtex, 
            frameColor=(1, 1, 1, 1),
            frameSize = ( -.125, .125, -.125, .125 ),
            parent = self.frame
        )
        self.sign.setTransparency(True)
        self.sign.setPos(-v*42, 0, -v*12)

        brlabel = DirectLabel(
            text = str(char['br']),
            color = (1, 1, 1, 0),
            scale = scale,
            text_font = font4,
            text_fg = (1,1,1,1),
            text_align = TextNode.ARight,
            parent = self.frame
        )
        brlabel.setPos(v*6, 0, -v*22)

        falabel = DirectLabel(
            text = str(char['fa']),
            color = (1, 1, 1, 0),
            scale = scale,
            text_font = font4,
            text_fg = (1,1,1,1),
            text_align = TextNode.ARight,
            parent = self.frame
        )
        falabel.setPos(v*45, 0, -v*22)

        i1 = LerpScaleInterval(self.blackframe, 0.1, (1,1,1), (1,1,0))
        i2 = LerpColorInterval(self.blackframe, 0.1, (1,1,1,1), (1,1,1,0))
        i3 = LerpPosInterval(  self.frame,      0.2, (u*67,0,-u*82), (2,0,-u*82))
        p1 = Parallel(i1,i2,i3)
        s = Sequence(p1)
        s.start()

    def hide(self):
        if self.frame:
            i1 = LerpScaleInterval(self.blackframe, 0.1, (1,1,0), (1,1,1))
            i2 = LerpColorInterval(self.blackframe, 0.1, (1,1,1,0), (1,1,1,1))
            i3 = LerpPosInterval(  self.frame,      0.2, (2,0,-u*82), (u*67,0,-u*82))
            p1 = Parallel(i1,i2,i3)
            i4 = Func( self.blackframe.destroy )
            i5 = Func( self.frame.destroy )
            s = Sequence(p1,i4,i5)
            s.start()

class ActionPreview(DirectObject.DirectObject):

    def __init__(self, char1, char2, damages, chance, command, cancelcommand):
        self.command = command
        self.cancelcommand = cancelcommand
    
        blacktex = loader.loadTexture(GAME+'/textures/gui/black.png')
        blacktex.setMagfilter(Texture.FTNearest)
        blacktex.setMinfilter(Texture.FTNearest)

        self.blackframe = DirectFrame(
            frameTexture = blacktex, 
            frameColor=(1, 1, 1, 1),
            frameSize = ( -2, 2, -v*64.0, v*64.0 ),
            sortOrder = -1,
        )
        self.blackframe.setTransparency(True)
        self.blackframe.setPos(0, 0, u*-82)

        self.fbgframe1 = DirectFrame(
            frameColor=(1, 1, 1, 0),
            geom = WindowNodeDrawer(37, 53, 'flat'),
            pos = (-2, 0, -v*82)
        )
        self.fbgframe1.setTransparency(True)
        
        facetex1 = loader.loadTexture(GAME+'/textures/sprites/'+char1['sprite']+'_face.png')
        facetex1.setMagfilter(Texture.FTNearest)
        facetex1.setMinfilter(Texture.FTNearest)
        
        self.face1 = DirectFrame(
            frameTexture = facetex1, 
            frameColor=(1, 1, 1, 1),
            frameSize = ( 0, v*32, 0, v*64 ),
            parent = self.fbgframe1,
        )
        self.face1.setPos(-v*(59-42), 0, -v*31)
        
        self.frame1 = DirectFrame(
            frameColor=(1, 1, 1, 0),
            frameSize = ( -v*64.0, v*64.0, -v*32.0, v*32.0 ),
            parent = self.fbgframe1
        )
        self.frame1.setPos(v*46, 0, -v*9)
        self.frame1.setTransparency(True)

        atex = loader.loadTexture(GAME+'/textures/gui/action_preview_arrow.png')
        atex.setMagfilter(Texture.FTNearest)
        atex.setMinfilter(Texture.FTNearest)
        
        self.arrow = DirectFrame(
            frameTexture = atex, 
            frameColor=(1, 1, 1, 1),
            frameSize = ( -v*8.0, v*8.0, -v*16.0, v*16.0 ),
            parent = self.fbgframe1
        )
        self.arrow.setPos(v*101.0, 0, v*1.0)
        self.arrow.setTransparency(True)

        bar = Bar(bar='bar-1')
        bar.updateTo(int(float(char1['hp'])/float(char1['hpmax'])*100))
        self.hpbar = DirectFrame(
            frameColor=(1, 1, 1, 1),
            frameSize=(0, 0, 0, 0), 
            parent = self.fbgframe1,
            geom = bar.container,
            pos = (v*24, 0, -v*2),
        )
        self.hpbar.setTransparency(True)

        bar = Bar(bar='bar-2')
        bar.updateTo(int(float(char1['mp'])/float(char1['mpmax'])*100))
        self.mpbar = DirectFrame(
            frameColor=(1, 1, 1, 1),
            frameSize=(0, 0, 0, 0), 
            parent = self.fbgframe1,
            geom = bar.container,
            pos = (v*24, 0, -v*13),
        )
        self.mpbar.setTransparency(True)

        bar = Bar(bar='bar-3')
        bar.updateTo(int(char1['ct']))
        self.ctbar = DirectFrame(
            frameColor=(1, 1, 1, 1),
            frameSize=(0, 0, 0, 0), 
            parent = self.fbgframe1,
            geom = bar.container,
            pos = (v*24, 0, -v*24),
        )
        self.ctbar.setTransparency(True)

        infos = [
            { 'x':  16, 'z':  23, 'text':  '%02d' % chance        , 'font':   whitefont },
            { 'x':  15, 'z':   9, 'text':  '%03d' % char1['hp']   , 'font':   whitefont },
            { 'x':  28, 'z':   5, 'text': '/%03d' % char1['hpmax'], 'font':   whitefont },
            { 'x':  15, 'z':  -2, 'text':  '%03d' % char1['mp']   , 'font':   whitefont },
            { 'x':  28, 'z':  -6, 'text': '/%03d' % char1['mpmax'], 'font':   whitefont },
            { 'x':  15, 'z': -13, 'text':  '%03d' % char1['ct']   , 'font':   whitefont },
            { 'x':  28, 'z': -17, 'text':  '/100'                 , 'font':   whitefont },
            { 'x': -33, 'z':   8, 'text':    'Hp'                 , 'font': smwhitefont },
            { 'x': -33, 'z':  -3, 'text':    'Mp'                 , 'font': smwhitefont },
            { 'x': -33, 'z': -13, 'text':    'Ct'                 , 'font': smwhitefont },
        ]
        
        for info in infos:
            label = DirectLabel(
                text = info['text'],
                color = (1, 1, 1, 0),
                scale = scale,
                text_font = info['font'],
                text_fg = (1, 1, 1, 1),
                text_align = TextNode.ALeft,
                parent = self.frame1,
            )
            label.setPos(v*info['x'], 0, v*info['z'])

        self.fbgframe2 = DirectFrame(
            frameColor=(1, 1, 1, 0),
            frameSize = ( -v*32.0, v*32.0, -v*32.0, v*32.0 ),
            geom = WindowNodeDrawer(37, 53, 'flat'),
            pos = (2, 0, -v*82)
        )
        self.fbgframe2.setTransparency(True)

        facetex2 = loader.loadTexture(GAME+'/textures/sprites/'+char2['sprite']+'_face.png')
        facetex2.setMagfilter(Texture.FTNearest)
        facetex2.setMinfilter(Texture.FTNearest)
        
        self.face2 = DirectFrame(
            frameTexture = facetex2, 
            frameColor=(1, 1, 1, 1),
            frameSize = ( 0, v*32, 0, v*64 ),
            parent = self.fbgframe2,
        )
        self.face2.setPos(-v*(59-42), 0, -v*31)
        
        self.frame2 = DirectFrame(
            frameColor=(1, 1, 1, 0),
            frameSize = ( -v*64.0, v*64.0, -v*32.0, v*32.0 ),
            parent = self.fbgframe2
        )
        self.frame2.setPos(-v*64, 0, v*7)
        self.frame2.setTransparency(True)

        bar = Bar(bar='bar-1')
        bar.updateTo(int(float(char2['hp'])/float(char2['hpmax'])*100))
        self.hpbar = DirectFrame(
            frameColor=(1, 1, 1, 1),
            frameSize=(0, 0, 0, 0),
            parent = self.fbgframe2,
            geom = bar.container,
            pos = (-v*87, 0, v*14),
        )
        self.hpbar.setTransparency(True)
        
        bar = Bar(bar='bar-2')
        bar.updateTo(int(float(char2['mp'])/float(char2['mpmax'])*100))
        self.mpbar = DirectFrame(
            frameColor=(1, 1, 1, 1),
            frameSize=(0, 0, 0, 0),
            parent = self.fbgframe2,
            geom = bar.container,
            pos = (-v*87, 0, v*3),
        )
        self.mpbar.setTransparency(True)
        
        bar = Bar(bar='bar-3')
        bar.updateTo(int(char2['ct']))
        self.ctbar = DirectFrame(
            frameColor=(1, 1, 1, 1),
            frameSize=(0,0,0,0),
            parent = self.fbgframe2,
            geom = bar.container,
            pos = (-v*87, 0, -v*8),
        )
        self.ctbar.setTransparency(True)

        infos = [
            { 'x':   14, 'z':   7, 'text':  '%03d' % char2['hp']   , 'font':   whitefont },
            { 'x':   28, 'z':   3, 'text': '/%03d' % char2['hpmax'], 'font':   whitefont },
            { 'x':   14, 'z':  -4, 'text':  '%03d' % char2['mp']   , 'font':   whitefont },
            { 'x':   28, 'z':  -8, 'text': '/%03d' % char2['mpmax'], 'font':   whitefont },
            { 'x':   14, 'z': -15, 'text':  '%03d' % char2['ct']   , 'font':   whitefont },
            { 'x':   28, 'z': -19, 'text':  '/100'                 , 'font':   whitefont },            
            { 'x':  -33, 'z':   8, 'text':    'Hp'                 , 'font': smwhitefont },
            { 'x':  -33, 'z':  -3, 'text':    'Mp'                 , 'font': smwhitefont },
            { 'x':  -33, 'z': -13, 'text':    'Ct'                 , 'font': smwhitefont },
        ]
        
        for info in infos:
            label = DirectLabel(
                text = info['text'],
                color = (1, 1, 1, 0),
                scale = scale,
                text_font = info['font'],
                text_fg = (1, 1, 1, 1),
                text_align = TextNode.ALeft,
                parent = self.frame2,
            )
            label.setPos(v*info['x'], 0, v*info['z'])

        s = Sequence(
            Parallel(
                LerpScaleInterval(self.blackframe, 0.1, (1,1,1), (1,1,0)),
                LerpColorInterval(self.blackframe, 0.1, (1,1,1,1), (1,1,1,0)),
                LerpPosInterval(   self.fbgframe1, 0.2, (-u*111,0,-u*82), (-2,0,-u*82)),
                LerpPosInterval(   self.fbgframe2, 0.2, ( u*109,0,-u*82), ( 2,0,-u*82)),
            ),
            Func( self.acceptAll ),
        ).start()

    def hide(self):
        if self.fbgframe1:
            s = Sequence(
                Parallel(
                    LerpScaleInterval(self.blackframe, 0.1, (1,1,0), (1,1,1)),
                    LerpColorInterval(self.blackframe, 0.1, (1,1,1,0), (1,1,1,1)),
                    LerpPosInterval(   self.fbgframe1, 0.2, (-2,0,-u*82), (u*111,0,-u*82)),
                    LerpPosInterval(   self.fbgframe2, 0.2, ( 2,0,-u*82), (u*109,0,-u*82)),
                ),
                Func( self.blackframe.destroy ),
                Func( self.fbgframe1.destroy ),
                Func( self.fbgframe2.destroy ),
            ).start()

    def acceptAll(self):
        self.accept(CROSS_BTN,  self.onCrossClicked)
        self.accept(CIRCLE_BTN, self.onCircleClicked)

    def onCircleClicked(self):
        clicked_snd.play()
        self.command()
        self.ignoreAll()

    def onCrossClicked(self):
        cancel_snd.play()
        self.hide()
        self.ignoreAll()
        self.cancelcommand()

class BrownOverlay(DirectObject.DirectObject):

    def __init__(self, textcallback, callback):
        
        self.callback = callback
        self.r = 20
        self.frames = [ [ None for y in range(self.r) ] for x in range(self.r) ]
        
        for x in range(self.r):
            for y in range(self.r):
                frame = DirectFrame(
                    color = (0,0,0,0),
                    frameSize = ( -1.0/self.r, 1.0/self.r, -1.0/self.r, 1.0/self.r ),
                    pos = (
                        (((float(x)/float(self.r))-.5)*2.0)+1.0/self.r,
                        0,
                        ((-(float(y)/float(self.r))+.5)*2.0)-1.0/self.r,
                    ),
                    parent = render2d,
                )
                frame.setTransparency(True)
                self.frames[x][y] = frame

                s = Sequence(
                    Wait(float(x+y)/40.0),
                    Parallel(
                        LerpHprInterval(frame, .125, (0,0,0), (0,0,90)),
                        LerpColorInterval(frame, .125, (.3,.22,.05,.5), (.3,.22,.04,0)),
                        LerpScaleInterval(frame, .25, 1, .01),
                    ),
                )
                if x == self.r-1 and y == self.r-1:
                    s.append(Func(lambda: textcallback(self.hide)))
                s.start()

    def hide(self):
        
        for x in range(self.r):
            for y in range(self.r):
                frame = self.frames[x][y]
                
                s = Sequence(
                    Wait(float(x+y)/40.0),
                    Parallel(
                        LerpHprInterval(frame, .125, (0,0,90), (0,0,0)),
                        LerpColorInterval(frame, .125, (.3,.22,.05,0), (.3,.22,.04,.5)),
                        LerpScaleInterval(frame, .25, .01, 1),
                    ),
                    Func(frame.destroy),
                )
                if x == self.r-1 and y == self.r-1:
                    s.append(Wait(1))
                    s.append(Func(self.callback))
                s.start()

class ConditionsForWinning(DirectObject.DirectObject):

    def __init__(self, callback):
        
        cfwtex = loader.loadTexture(GAME+'/textures/gui/conditions_for_winning.png')
        cfwtex.setMagfilter(Texture.FTNearest)
        cfwtex.setMinfilter(Texture.FTNearest)
        cfw = DirectFrame(
            color = (1,1,1,0),
            frameTexture = cfwtex,
            frameSize = ( -v*128.0, v*128.0, -v*16.0, v*16.0 ),
            pos = (v*20, 0, v*90),
        )
        cfw.setTransparency(True)

        daetex = loader.loadTexture(GAME+'/textures/gui/defeat_all_enemies.png')
        daetex.setMagfilter(Texture.FTNearest)
        daetex.setMinfilter(Texture.FTNearest)
        dae = DirectFrame(
            color = (1,1,1,0),
            frameTexture = daetex,
            frameSize = ( -v*128.0, v*128.0, -v*16.0, v*16.0 ),
            pos = (v*49, 0, v*60),
        )
        dae.setTransparency(True)

        readytex = loader.loadTexture(GAME+'/textures/gui/ready.png')
        readytex.setMagfilter(Texture.FTNearest)
        readytex.setMinfilter(Texture.FTNearest)
        ready = DirectFrame(
            color = (1,1,1,0),
            frameTexture = readytex,
            frameSize = ( -v*128.0, v*128.0, -v*16.0, v*16.0 ),
        )
        ready.setTransparency(True)

        s = Sequence(
            Wait(1),
            LerpColorInterval(cfw, .5, (1,1,1,1), (1,1,1,0)),
            Wait(.5),
            LerpColorInterval(dae, .5, (1,1,1,1), (1,1,1,0)),
            Wait(2),
            Parallel(
                LerpColorInterval(cfw, .5, (1,1,1,0), (1,1,1,1)),
                LerpColorInterval(dae, .5, (1,1,1,0), (1,1,1,1)),
            ),
            Func(cfw.destroy),
            Func(dae.destroy),
            LerpColorInterval(ready, 1, (1,1,1,1), (1,1,1,0)),
            Wait(2),
            LerpColorInterval(ready, 1, (1,1,1,0), (1,1,1,1)),
            Func(ready.destroy),
            Func(callback),
        ).start()

class Congratulations(DirectObject.DirectObject):

    def __init__(self, callback):
        
        ggtex = loader.loadTexture(GAME+'/textures/gui/congratulations.png')
        ggtex.setMagfilter(Texture.FTNearest)
        ggtex.setMinfilter(Texture.FTNearest)
        gg = DirectFrame(
            color = (1,1,1,0),
            frameTexture = ggtex,
            frameSize = ( -v*128.0, v*128.0, -v*16.0, v*16.0 ),
            pos = (v*0, 0, v*30),
        )
        gg.setTransparency(True)

        bctex = loader.loadTexture(GAME+'/textures/gui/battle_complete.png')
        bctex.setMagfilter(Texture.FTNearest)
        bctex.setMinfilter(Texture.FTNearest)
        bc = DirectFrame(
            color = (1,1,1,0),
            frameTexture = bctex,
            frameSize = ( -v*64.0, v*64.0, -v*16.0, v*16.0 ),
            pos = (v*0, 0, -v*30),
        )
        bc.setTransparency(True)

        s = Sequence(
            Wait(1),
            LerpColorInterval(gg, .5, (1,1,1,1), (1,1,1,0)),
            Wait(.5),
            LerpColorInterval(bc, .5, (1,1,1,1), (1,1,1,0)),
            Wait(2),
            Parallel(
                LerpColorInterval(gg, .5, (1,1,1,0), (1,1,1,1)),
                LerpColorInterval(bc, .5, (1,1,1,0), (1,1,1,1)),
            ),
            Func(gg.destroy),
            Func(bc.destroy),
            Func(callback),
        ).start()

class GameOver(DirectObject.DirectObject):

    def __init__(self, callback):
        
        gotex = loader.loadTexture(GAME+'/textures/gui/game_over.png')
        gotex.setMagfilter(Texture.FTNearest)
        gotex.setMinfilter(Texture.FTNearest)
        go = DirectFrame(
            color = (1,1,1,0),
            frameTexture = gotex,
            frameSize = ( -2, 2, -2, 2 ),
        )
        go.setTransparency(True)

        s = Sequence(
            LerpColorInterval(go, 3, (1,1,1,1), (1,1,1,0)),
            Wait(2),
            LerpColorInterval(go, 3, (0,0,0,1), (1,1,1,1)),
            Func(go.destroy),
            Func(callback),
        ).start()

class MapChooser(DirectObject.DirectObject):

    def __init__(self, maplist, parent, command, cancelcommand):
        self.parent = parent
        self.command = command
        self.cancelcommand = cancelcommand
        self.current = 0
        self.maplist = maplist

        loadingtexture = loader.loadTexture(GAME+'/textures/gui/now_loading.png')
        loadingtexture.setMagfilter(Texture.FTNearest)
        loadingtexture.setMinfilter(Texture.FTNearest)

        self.loadingframe = DirectFrame(
            frameTexture = loadingtexture,
            frameColor = (1, 1, 1, 1),
            frameSize = ( -.25, .25, -.0625, .0625 ),
            pos = (.9, 0, -.8),
            scale = 1.0,
        )
        self.loadingframe.setTransparency(True)

        for mapinfo in self.maplist:
            terrain = loader.loadModel(GAME+'/models/maps/'+mapinfo['model'])
            terrain.setTransparency(TransparencyAttrib.MAlpha)
            terrain.setScale( *[ x/25.0 for x in mapinfo['scale'] ] )
            terrain.setDepthWrite(True)
            terrain.setDepthTest(True)
            bbcenter = terrain.getBounds().getCenter()
            hprcontainer = NodePath("hprcontainer")
            recentrer = NodePath("recentrer")
            hprcontainer.setHpr(0,33,0)
            terrain.reparentTo(recentrer)
            terrain.setPos(-bbcenter[0], -bbcenter[1], -bbcenter[2]/2.0)
            recentrer.reparentTo(hprcontainer)
            mapinfo['recentrer'] = recentrer
            mapinfo['terrain'] = hprcontainer

        self.loadingframe.destroy()

        l1texture = loader.loadTexture(GAME+'/textures/gui/L1.png')
        l1texture.setMagfilter(Texture.FTNearest)
        l1texture.setMinfilter(Texture.FTNearest)

        self.l1frame = DirectFrame(
            frameTexture = l1texture,
            frameColor = (1, 1, 1, 1),
            frameSize = ( -.125, .125, -.0625, .0625 ),
            pos = (-.9, 0, .8),
            scale = 1.0,
        )
        self.l1frame.setTransparency(True)

        r1texture = loader.loadTexture(GAME+'/textures/gui/R1.png')
        r1texture.setMagfilter(Texture.FTNearest)
        r1texture.setMinfilter(Texture.FTNearest)

        self.r1frame = DirectFrame(
            frameTexture = r1texture,
            frameColor = (1, 1, 1, 1),
            frameSize = ( -.125, .125, -.0625, .0625 ),
            pos = (.9, 0, .8),
            scale = 1.0,
        )
        self.r1frame.setTransparency(True)

        starttexture = loader.loadTexture(GAME+'/textures/gui/start_end.png')
        starttexture.setMagfilter(Texture.FTNearest)
        starttexture.setMinfilter(Texture.FTNearest)

        self.startframe = DirectFrame(
            frameTexture = starttexture,
            frameColor = (1, 1, 1, 1),
            frameSize = ( -.25, .25, -.0625, .0625 ),
            pos = (0, 0, -.8),
            scale = 1.0,
        )
        self.startframe.setTransparency(True)
        
        seq = Sequence(
            Parallel(
                LerpPosInterval(self.l1frame, 0.25, (-.9, 0, .8), (-.9, 0, 1.0)),
                LerpPosInterval(self.r1frame, 0.25, ( .9, 0, .8), ( .9, 0, 1.0)),
                LerpPosInterval(self.startframe, 0.25, (0, 0, -.8), (0, 0, -1.0)),
                Func( self.maplist[self.current]['terrain'].reparentTo, self.parent ),
                LerpColorInterval(self.maplist[self.current]['terrain'], 0.25, (1,1,1,1), (1,1,1,0)),
            ),
            Func( taskMgr.add, self.mapRotationTask, 'mapRotationTask' ),
            Func( self.acceptAll ),
        ).start()

    def acceptAll(self):
        self.accept(CROSS_BTN,        self.onCrossClicked)
        self.accept(START_BTN,        self.onStartClicked)
        self.accept(L1_BTN,           self.onL1Clicked)
        self.accept(R1_BTN,           self.onR1Clicked)
        self.accept(L1_BTN+"-repeat", self.onL1Clicked)
        self.accept(L1_BTN+"-repeat", self.onR1Clicked)

    def onCrossClicked(self):
        cancel_snd.play()
        self.commandAndDestroy(self.cancelcommand)

    def onStartClicked(self):
        clicked_snd.play()
        self.commandAndDestroy( lambda: self.command( self.maplist[self.current]['name'] ) )

    def commandAndDestroy(self, command):
        self.ignoreAll()

        seq = Sequence(
            Func( taskMgr.remove, 'mapRotationTask' ),
            Wait( 0.5 ),
            Parallel(
                LerpPosInterval(self.l1frame, 0.25, (-.9, 0, 1.0), (-.9, 0, .8)),
                LerpPosInterval(self.r1frame, 0.25, ( .9, 0, 1.0), ( .9, 0, .8)),
                LerpPosInterval(self.startframe, 0.25, (0, 0, -1.0), (0, 0, -.8)),
                LerpColorInterval(self.maplist[self.current]['terrain'], 0.25, (1,1,1,0), (1,1,1,1)),
            ),
            Func( self.l1frame.destroy ),
            Func( self.r1frame.destroy ),
            Func( self.startframe.destroy ),
            Func( command ),
            Func( self.unloadTerrains ),
        ).start()

    def unloadTerrains(self):
        for mapinfo in self.maplist:
            mapinfo['terrain'].removeNode()
            loader.unloadModel(GAME+'/models/maps/'+mapinfo['model'])
        del self.maplist

    def onR1Clicked(self):

        self.previous = self.current
        self.current = self.current - 1
        if self.current < 0:
            self.current = len(self.maplist) - 1

        seq = Sequence(
            Func( self.ignoreAll ),
            Func( self.maplist[self.current]['terrain'].reparentTo, self.parent ),
            Parallel(
                #LerpScaleInterval(self.maplist[self.previous]['terrain'], 0.25, 0.1, startScale=1.0 ),
                LerpColorInterval(self.maplist[self.previous]['terrain'], 0.25, (1,1,1,0), (1,1,1,1)),
                LerpPosInterval(  self.maplist[self.previous]['terrain'], 0.25, (-25,25,0), (0,0,0)),
                #LerpHprInterval(  self.maplist[self.previous]['terrain'], 0.25, (90,0,0), (0,0,0)),
                #LerpScaleInterval(self.maplist[self.current]['terrain'],  0.25, 1.0, startScale=0.1 ),
                LerpColorInterval(self.maplist[self.current]['terrain'],  0.25, (1,1,1,1), (1,1,1,0)),
                LerpPosInterval(  self.maplist[self.current]['terrain'],  0.25, (0,0,0), (25,-25,0)),
                #LerpHprInterval(  self.maplist[self.current]['terrain'], 0.25, (180,0,0), (90,0,0)),
            ),
            Func( self.maplist[self.previous]['terrain'].detachNode ),
            Func( self.acceptAll ),
            Func( hover_snd.play ),
        ).start()

    def onL1Clicked(self):

        self.previous = self.current
        self.current = self.current + 1
        if self.current > len(self.maplist) - 1:
            self.current = 0

        seq = Sequence(
            Func( self.ignoreAll ),
            Func( self.maplist[self.current]['terrain'].reparentTo, self.parent ),
            Parallel(
                #LerpScaleInterval(self.maplist[self.previous]['terrain'], 0.25, 0.1, startScale=1.0 ),
                LerpColorInterval(self.maplist[self.previous]['terrain'], 0.25, (1,1,1,0), (1,1,1,1)),
                LerpPosInterval(  self.maplist[self.previous]['terrain'], 0.25, (25,-25,0), (0,0,0)),
                #LerpHprInterval(  self.maplist[self.previous]['terrain'], 0.25, (90,0,0), (0,0,0)),
                #LerpScaleInterval(self.maplist[self.current]['terrain'],  0.25, 1.0, startScale=0.1 ),
                LerpColorInterval(self.maplist[self.current]['terrain'],  0.25, (1,1,1,1), (1,1,1,0)),
                LerpPosInterval(  self.maplist[self.current]['terrain'],  0.25, (0,0,0), (-25,25,0)),
                #LerpHprInterval(  self.maplist[self.current]['terrain'], 0.25, (180,0,0), (90,0,0)),
            ),
            Func( self.maplist[self.previous]['terrain'].detachNode ),
            Func( self.acceptAll ),
            Func( hover_snd.play ),
        ).start()

    def mapRotationTask(self, task):
        h = task.time * 30
        self.maplist[self.current]['recentrer'].setHpr(h,0,0)
        return Task.cont

class Formation(DirectObject.DirectObject):

    def __init__(self, parent, tileset, chars, command):
    
        self.tileset = tileset
        self.chars = chars
        self.current = 0
        self.char = self.chars[self.current]
        self.direction = self.tileset['direction']
        self.capacity = self.tileset['capacity']
        self.remaining = self.capacity
        self.command = command
        self.sprites = [ [ None for y in range(5) ] for x in range(5) ]

        tex0 = loader.loadTexture(GAME+'/textures/gui/frm0.png')
        tex0.setMagfilter(Texture.FTNearest)
        tex0.setMinfilter(Texture.FTNearest)

        tex1 = loader.loadTexture(GAME+'/textures/gui/frm1.png')
        tex1.setMagfilter(Texture.FTNearest)
        tex1.setMinfilter(Texture.FTNearest)

        self.hprcontainer = parent.attachNewNode('hprcontainer')
        self.hprcontainer.setHpr(0,30,0)
        self.hprcontainer.setScale(0.235)
        self.hprcontainer.setPos(0,0,-.415)
        self.hprcontainer.setDepthWrite(True)
        self.hprcontainer.setDepthTest(True)

        self.root = NodePath("root")
        self.root.setHpr(-45,0,0)
        self.root.reparentTo(self.hprcontainer)

        self.tiles = [ [ {} for y in range(5) ] for x in range(5) ]
        for y,l in enumerate(self.tileset['maping']):
            y = 4-y
            for x,t in enumerate(l):
                self.tiles[x][y]['coords'] = t
                self.tiles[x][y]['char'] = None
                self.tiles[x][y]['model'] = loader.loadModel(GAME+"/models/slopes/flat")
                self.tiles[x][y]['model'].setTexture(tex0)
                self.tiles[x][y]['model'].setColor(1,1,1,1)
                self.tiles[x][y]['model'].setTransparency(TransparencyAttrib.MAlpha)
                self.tiles[x][y]['model'].reparentTo(self.root)
                self.tiles[x][y]['model'].setPos((x-2, y-2, 0))

                if t:
                    self.tiles[x][y]['model'].setTexture(tex1)
                    self.tiles[x][y]['model'].setPos((x-2, y-2, .33))
                else:
                    self.tiles[x][y]['model'].setTexture(tex0)                

        l1texture = loader.loadTexture(GAME+'/textures/gui/L1.png')
        l1texture.setMagfilter(Texture.FTNearest)
        l1texture.setMinfilter(Texture.FTNearest)

        self.l1frame = DirectFrame(
            frameTexture = l1texture,
            frameColor = (1, 1, 1, 0),
            frameSize = ( -v*16, v*16, -v*8, v*8 ),
            pos = (-v*104, 0, v*100),
            scale = 1.0,
        )
        self.l1frame.setTransparency(True)

        r1texture = loader.loadTexture(GAME+'/textures/gui/R1.png')
        r1texture.setMagfilter(Texture.FTNearest)
        r1texture.setMinfilter(Texture.FTNearest)

        self.r1frame = DirectFrame(
            frameTexture = r1texture,
            frameColor = (1, 1, 1, 0),
            frameSize = ( -v*16, v*16, -v*8, v*8 ),
            pos = (v*109, 0, v*100),
            scale = 1.0,
        )
        self.r1frame.setTransparency(True)

        searchtexture = loader.loadTexture(GAME+'/textures/gui/search_btn.png')
        searchtexture.setMagfilter(Texture.FTNearest)
        searchtexture.setMinfilter(Texture.FTNearest)

        self.searchframe = DirectFrame(
            frameTexture = searchtexture,
            frameColor = (1, 1, 1, 0),
            frameSize = ( -v*32, v*32, -v*8, v*8 ),
            pos = (-v*58, 0, -v*100),
            scale = 1.0,
        )
        self.searchframe.setTransparency(True)

        statustexture = loader.loadTexture(GAME+'/textures/gui/status_btn.png')
        statustexture.setMagfilter(Texture.FTNearest)
        statustexture.setMinfilter(Texture.FTNearest)

        self.statusframe = DirectFrame(
            frameTexture = statustexture,
            frameColor = (1, 1, 1, 0),
            frameSize = ( -v*32, v*32, -v*8, v*8 ),
            pos = (-v*0, 0, -v*100),
            scale = 1.0,
        )
        self.statusframe.setTransparency(True)

        starttexture = loader.loadTexture(GAME+'/textures/gui/start_end.png')
        starttexture.setMagfilter(Texture.FTNearest)
        starttexture.setMinfilter(Texture.FTNearest)

        self.startframe = DirectFrame(
            frameTexture = starttexture,
            frameColor = (1, 1, 1, 0),
            frameSize = ( -v*32, v*32, -v*8, v*8 ),
            pos = (v*61, 0, -v*100),
            scale = 1.0,
        )
        self.startframe.setTransparency(True)

        squadtexture0 = loader.loadTexture(GAME+'/textures/gui/squad_lbl0.png')
        squadtexture0.setMagfilter(Texture.FTNearest)
        squadtexture0.setMinfilter(Texture.FTNearest)

        self.squadframe = DirectFrame(
            frameTexture = squadtexture0,
            frameColor = (1, 1, 1, 0),
            frameSize = ( -v*32, v*32, -v*8, v*8 ),
            pos = (-v*96, 0, v*23),
            scale = 1.0,
        )
        self.squadframe.setTransparency(True)

        capacitytexture = loader.loadTexture(GAME+'/textures/gui/capacity_lbl.png')
        capacitytexture.setMagfilter(Texture.FTNearest)
        capacitytexture.setMinfilter(Texture.FTNearest)

        self.capacityframe = DirectFrame(
            frameTexture = capacitytexture,
            frameColor = (1, 1, 1, 0),
            frameSize = ( -v*32, v*32, -v*8, v*8 ),
            pos = (-v*96, 0, v*7),
            scale = 1.0,
        )
        self.capacityframe.setTransparency(True)

        remainingtexture = loader.loadTexture(GAME+'/textures/gui/remaining_lbl.png')
        remainingtexture.setMagfilter(Texture.FTNearest)
        remainingtexture.setMinfilter(Texture.FTNearest)

        self.remainingframe = DirectFrame(
            frameTexture = remainingtexture,
            frameColor = (1, 1, 1, 0),
            frameSize = ( -v*32, v*32, -v*8, v*8 ),
            pos = (-v*94, 0, -v*9),
            scale = 1.0,
        )
        self.remainingframe.setTransparency(True)

        # Cursor stuff
        self.curtex = loader.loadTexture(GAME+'/textures/cursor.png')
        self.curtex.setMagfilter(Texture.FTNearest)
        self.curtex.setMinfilter(Texture.FTNearest)
        self.cux = 2
        self.cuy = 2
        self.cursor = loader.loadModel(GAME+'/models/slopes/flat')
        self.cursor.reparentTo(self.root)
        self.cursor.setPos(0, 0, .33+0.025)
        self.cursor.setTransparency(TransparencyAttrib.MAlpha)
        self.cursor.setColor(1, 1, 1, 1)
        self.cursor.setTexture(self.curtex)

        self.fbgframe = DirectFrame(
            frameColor=(1, 1, 1, 0),
            geom = WindowNodeDrawer(37, 53, 'flat'),
            pos = (-v*97, 0, v*61)
        )
        self.fbgframe.setTransparency(True)

        facetex = loader.loadTexture(GAME+'/textures/sprites/'+self.char['sprite']+'_face.png')
        facetex.setMagfilter(Texture.FTNearest)
        facetex.setMinfilter(Texture.FTNearest)

        self.face = DirectFrame(
            frameTexture = facetex, 
            frameColor=(1, 1, 1, 0),
            frameSize = ( 0, v*32, 0, v*64 ),
            parent = self.fbgframe,
        )
        self.face.setPos(-v*(59-42), 0, -v*31)

        self.barsframe = DirectFrame(
            frameColor=(1, 1, 1, 0),
            frameSize = ( -v*64.0, v*64.0, -v*32.0, v*32.0 ),
            parent = self.fbgframe
        )
        self.barsframe.setPos(v*46, 0, -v*9)
        self.barsframe.setTransparency(True)

        bar = Bar(bar='bar-1')
        bar.updateTo(int(float(self.char['hp'])/float(self.char['hpmax'])*100))
        self.hpbar = DirectFrame(
            frameColor=(1, 1, 1, 1),
            frameSize=(0, 0, 0, 0), 
            parent = self.fbgframe,
            geom = bar.container,
            pos = (v*24, 0, -v*2),
        )
        self.hpbar.setTransparency(True)

        bar = Bar(bar='bar-2')
        bar.updateTo(int(float(self.char['mp'])/float(self.char['mpmax'])*100))
        self.mpbar = DirectFrame(
            frameColor=(1, 1, 1, 1),
            frameSize=(0, 0, 0, 0), 
            parent = self.fbgframe,
            geom = bar.container,
            pos = (v*24, 0, -v*13),
        )
        self.mpbar.setTransparency(True)

        bar = Bar(bar='bar-3')
        bar.updateTo(100)
        self.ctbar = DirectFrame(
            frameColor=(1, 1, 1, 1),
            frameSize=(0, 0, 0, 0), 
            parent = self.fbgframe,
            geom = bar.container,
            pos = (.20, 0, -.20)
        )
        self.ctbar.setTransparency(True)

        infos = [
            { 'x':  12, 'z':  23, 'text':  '%02d' % self.char['lv']   , 'font':   whitefont },
            { 'x':  43, 'z':  23, 'text':  '%02d' % self.char['exp']  , 'font':   whitefont },
            { 'x':  15, 'z':   9, 'text':  '%03d' % self.char['hp']   , 'font':   whitefont },
            { 'x':  28, 'z':   5, 'text': '/%03d' % self.char['hpmax'], 'font':   whitefont },
            { 'x':  15, 'z':  -2, 'text':  '%03d' % self.char['mp']   , 'font':   whitefont },
            { 'x':  28, 'z':  -6, 'text': '/%03d' % self.char['mpmax'], 'font':   whitefont },
            { 'x':  15, 'z': -13, 'text':   '---'                     , 'font':   whitefont },
            { 'x':  28, 'z': -17, 'text':  '/---'                     , 'font':   whitefont },
            { 'x': -33, 'z':   8, 'text':    'Hp'                     , 'font': smwhitefont },
            { 'x': -33, 'z':  -3, 'text':    'Mp'                     , 'font': smwhitefont },
            { 'x': -33, 'z': -13, 'text':    'Ct'                     , 'font': smwhitefont },
            { 'x':   0, 'z':  23, 'text':   'Lv.'                     , 'font': smwhitefont },
            { 'x':  27, 'z':  23, 'text':  'Exp.'                     , 'font': smwhitefont },
        ]

        self.labels = [ None for i in infos ]
        for i,info in enumerate(infos):
            self.labels[i] = DirectLabel(
                text = info['text'],
                color = (1, 1, 1, 0),
                scale = scale,
                text_font = info['font'],
                text_fg = (1, 1, 1, 1),
                text_align = TextNode.ALeft,
                parent = self.barsframe
            )
            self.labels[i].setPos(v*info['x'], 0, v*info['z'])

        cardtex = loader.loadTexture(GAME+'/textures/gui/char_card.png')
        cardtex.setMagfilter(Texture.FTNearest)
        cardtex.setMinfilter(Texture.FTNearest)

        self.cardframe = DirectFrame(
            frameTexture = cardtex, 
            frameColor=(1, 1, 1, 1),
            frameSize = ( -v*64.0, v*64.0, -v*32.0, v*32.0 ),
        )
        self.cardframe.setTransparency(True)
        self.cardframe.setPos(v*63, 0, u*65)

        self.name = DirectLabel(
            text = self.char['name'],
            color = (0,0,0,0),
            scale = regularscale,
            text_font = regularfont,
            text_fg = (1,1,1,1),
            text_align = TextNode.ALeft,
            parent = self.cardframe
        )
        self.name.setPos(-v*33, 0, v*12)

        self.job = DirectLabel(
            text = self.char['job'],
            color = (0,0,0,0),
            scale = regularscale,
            text_font = regularfont,
            text_fg = (1,1,1,1),
            text_align = TextNode.ALeft,
            parent = self.cardframe
        )
        self.job.setPos(-v*33, 0, -v*4)

        teamcolors = ['blue','red','green']
        ledtex = loader.loadTexture(GAME+'/textures/gui/led_'+teamcolors[int(self.char['team'])]+'.png')
        ledtex.setMagfilter(Texture.FTNearest)
        ledtex.setMinfilter(Texture.FTNearest)

        self.led = DirectFrame(
            frameTexture = ledtex, 
            frameColor=(1, 1, 1, 1),
            frameSize = ( -.0625, .0625, -.0625, .0625 ),
            parent = self.cardframe
        )
        self.led.setTransparency(True)
        self.led.setPos(-v*49, 0, v*18)

        signs = ['aries','scorpio']
        signtex = loader.loadTexture(GAME+'/textures/gui/'+signs[int(self.char['sign'])]+'.png')
        signtex.setMagfilter(Texture.FTNearest)
        signtex.setMinfilter(Texture.FTNearest)

        self.sign = DirectFrame(
            frameTexture = signtex, 
            frameColor=(1, 1, 1, 1),
            frameSize = ( -.125, .125, -.125, .125 ),
            parent = self.cardframe
        )
        self.sign.setTransparency(True)
        self.sign.setPos(-v*42, 0, -v*12)

        self.brlabel = DirectLabel(
            text = str(self.char['br']),
            color = (1, 1, 1, 0),
            scale = scale,
            text_font = font4,
            text_fg = (1,1,1,1),
            text_align = TextNode.ARight,
            parent = self.cardframe
        )
        self.brlabel.setPos(v*6, 0, -v*22)

        self.falabel = DirectLabel(
            text = str(self.char['fa']),
            color = (1, 1, 1, 0),
            scale = scale,
            text_font = font4,
            text_fg = (1,1,1,1),
            text_align = TextNode.ARight,
            parent = self.cardframe
        )
        self.falabel.setPos(v*45, 0, -v*22)
        
        for char in self.chars:
            char['placed'] = False

        seq = Sequence(
            Parallel(
                LerpPosInterval(  self.hprcontainer,   .5, (0,0,-.415), (0,0,-2)),
                LerpPosInterval(  self.cardframe,      .5, (v*63,0,u*65), (v*63,0,2)),
                LerpPosInterval(  self.fbgframe,       .5, (-v*97,0,v*61), (-v*97,0,2)),
            ),
            Parallel(
                LerpColorInterval(self.l1frame,        .5, (1,1,1,1), (1,1,1,0)),
                LerpColorInterval(self.r1frame,        .5, (1,1,1,1), (1,1,1,0)),
                LerpColorInterval(self.squadframe,     .5, (1,1,1,1), (1,1,1,0)),
                LerpColorInterval(self.capacityframe,  .5, (1,1,1,1), (1,1,1,0)),
                LerpColorInterval(self.remainingframe, .5, (1,1,1,1), (1,1,1,0)),
                LerpColorInterval(self.searchframe,    .5, (.75,.75,.75,1), (1,1,1,0)),
                LerpColorInterval(self.statusframe,    .5, (.75,.75,.75,1), (1,1,1,0)),
                LerpColorInterval(self.startframe,     .5, (.75,.75,.75,1), (1,1,1,0)),
            ),
            Func( self.updateButtons ),
            Func( self.acceptAll ),
            Func( self.updateChar ),
        ).start()

    def acceptAll(self):
        self.accept("arrow_up", lambda: self.onArrowClicked('up'))
        self.accept("arrow_down", lambda: self.onArrowClicked('down'))
        self.accept("arrow_left", lambda: self.onArrowClicked('left'))
        self.accept("arrow_right", lambda: self.onArrowClicked('right'))
        self.accept("arrow_up-repeat", lambda: self.onArrowClicked('up'))
        self.accept("arrow_down-repeat", lambda: self.onArrowClicked('down'))
        self.accept("arrow_left-repeat", lambda: self.onArrowClicked('left'))
        self.accept("arrow_right-repeat", lambda: self.onArrowClicked('right'))
        self.accept(L1_BTN,           lambda: self.updateChar(-1))
        self.accept(R1_BTN,           lambda: self.updateChar(+1))
        self.accept(L1_BTN+"-repeat", lambda: self.updateChar(-1))
        self.accept(R1_BTN+"-repeat", lambda: self.updateChar(+1))
        self.accept(CIRCLE_BTN, self.onCircleClicked)
        self.accept(TRIANGLE_BTN, self.onTriangleClicked)
        self.accept(START_BTN, self.onStartClicked)

    def updateChar(self, delta=0, current=None):
        if current != None:
            self.current = current
        else:
            self.current = self.current + delta
            if self.current == len(self.chars):
                self.current = 0
            elif self.current == -1:
                self.current = len(self.chars)-1
        self.char = self.chars[self.current]

        self.labels[0]['text'] =  '%02d' % self.char['lv']
        self.labels[1]['text'] =  '%02d' % self.char['exp']
        self.labels[2]['text'] =  '%03d' % self.char['hpmax']
        self.labels[3]['text'] = '/%03d' % self.char['hpmax']
        self.labels[4]['text'] =  '%03d' % self.char['mpmax']
        self.labels[5]['text'] = '/%03d' % self.char['mpmax']

        self.name['text'] = self.char['name']
        self.job['text']  = self.char['job']
        self.brlabel['text']= str(self.char['br'])
        self.falabel['text']= str(self.char['fa'])

        facetex = loader.loadTexture(GAME+'/textures/sprites/'+self.char['sprite']+'_face.png')
        facetex.setMagfilter(Texture.FTNearest)
        facetex.setMinfilter(Texture.FTNearest)
        self.face['frameTexture'] = facetex

        signs = ['aries','scorpio']
        signtex = loader.loadTexture(GAME+'/textures/gui/'+signs[int(self.char['sign'])]+'.png')
        signtex.setMagfilter(Texture.FTNearest)
        signtex.setMinfilter(Texture.FTNearest)
        self.sign['frameTexture'] = signtex

        if self.char['placed']:
            color = [.7,.7,.9,1]
        else:
            color = [1, 1, 1, 1]

        self.cardframe['frameColor'] = color
        self.led['frameColor'] = color
        self.sign['frameColor'] = color
        self.name['text_fg'] = color
        self.job['text_fg'] = color
        self.brlabel['text_fg'] = color
        self.falabel['text_fg'] = color
        self.face['frameColor'] = color
        #self.barsframe['frameColor'] = color
        #self.fbgframe['frameColor'] = color
        for label in self.labels:
            label['text_fg'] = color

    def onArrowClicked(self, direction):
        if direction == 'up':
            if self.cuy < 4:
                self.cuy = self.cuy+1
        elif direction == 'down':
            if self.cuy > 0:
                self.cuy = self.cuy-1
        elif direction == 'left':
            if self.cux > 0:
                self.cux = self.cux-1
        elif direction == 'right':
            if self.cux < 4:
                self.cux = self.cux+1

        y = .33 if self.tiles[self.cux][self.cuy]['coords'] else 0
        self.cursor.setPos(self.cux-2, self.cuy-2, y+0.025)
        
        self.updateButtons()

    def onCircleClicked(self):

        if self.tiles[self.cux][self.cuy]['coords']:
        
            if not self.char['placed']:
            
                if self.tiles[self.cux][self.cuy]['char']:
                
                    print 'Switch verticaly'
                    self.sprites[self.cux][self.cuy].node.removeNode()
                    self.sprites[self.cux][self.cuy] = Sprite.Sprite(GAME+'/textures/sprites/'+self.char['sprite']+'.png', 1)
                    self.sprites[self.cux][self.cuy].animation = 'stand'
                    self.sprites[self.cux][self.cuy].node.setPos(self.cux-2, self.cuy-2, .33+0.025)
                    self.sprites[self.cux][self.cuy].node.setScale(.3)
                    self.sprites[self.cux][self.cuy].node.reparentTo(self.root)
                    self.char['placed'] = True
                    self.tiles[self.cux][self.cuy]['char']['placed'] = False
                    self.tiles[self.cux][self.cuy]['char'] = self.char

                else:
                
                    print 'Place'
            
                    if self.remaining > 0:
                    
                        print 'Placed successfully'
                        self.sprites[self.cux][self.cuy] = Sprite.Sprite(GAME+'/textures/sprites/'+self.char['sprite']+'.png', 1)
                        self.sprites[self.cux][self.cuy].animation = 'stand'
                        self.sprites[self.cux][self.cuy].node.setPos(self.cux-2, self.cuy-2, .33+0.025)
                        self.sprites[self.cux][self.cuy].node.setScale(.3)
                        self.sprites[self.cux][self.cuy].node.reparentTo(self.root)
                        self.char['placed'] = True
                        self.tiles[self.cux][self.cuy]['char'] = self.char
                        self.remaining = self.remaining - 1
        
            else:
            
                if self.tiles[self.cux][self.cuy]['char']:

                    if self.tiles[self.cux][self.cuy]['char'] == self.char:
                
                        print 'Remove'
                        self.sprites[self.cux][self.cuy].node.removeNode()
                        self.char['placed'] = False
                        self.tiles[self.cux][self.cuy]['char']['placed'] = False
                        self.tiles[self.cux][self.cuy]['char'] = None
                        self.remaining = self.remaining + 1
                    
                    else:

                        print 'Switch horizontaly'
                        ox = oy = oc = None
                        
                        # remove the char at destination
                        self.sprites[self.cux][self.cuy].node.removeNode()
                        self.char['placed'] = False
                        self.tiles[self.cux][self.cuy]['char']['placed'] = False
                        oc = self.tiles[self.cux][self.cuy]['char']
                        self.tiles[self.cux][self.cuy]['char'] = None

                        # remove the char at origin
                        for x,l in enumerate(self.tiles):
                            for y,t in enumerate(l):
                                if t['char'] == self.char:
                                    ox = x
                                    oy = y
                                    self.sprites[x][y].node.removeNode()
                                    self.char['placed'] = False
                                    self.tiles[x][y]['char']['placed'] = False
                                    self.tiles[x][y]['char'] = None

                        # place the char at destination
                        self.sprites[self.cux][self.cuy] = Sprite.Sprite(GAME+'/textures/sprites/'+self.char['sprite']+'.png', 1)
                        self.sprites[self.cux][self.cuy].animation = 'stand'
                        self.sprites[self.cux][self.cuy].node.setPos(self.cux-2, self.cuy-2, .33+0.025)
                        self.sprites[self.cux][self.cuy].node.setScale(.3)
                        self.sprites[self.cux][self.cuy].node.reparentTo(self.root)
                        self.char['placed'] = True
                        self.tiles[self.cux][self.cuy]['char'] = self.char
                        
                        # place the char at origin
                        self.sprites[ox][oy] = Sprite.Sprite(GAME+'/textures/sprites/'+oc['sprite']+'.png', 1)
                        self.sprites[ox][oy].animation = 'stand'
                        self.sprites[ox][oy].node.setPos(ox-2, oy-2, .33+0.025)
                        self.sprites[ox][oy].node.setScale(.3)
                        self.sprites[ox][oy].node.reparentTo(self.root)
                        oc['placed'] = True
                        self.tiles[ox][oy]['char'] = oc

                else:

                    print 'Move'

                    for x,l in enumerate(self.tiles):
                        for y,t in enumerate(l):
                            if t['char'] == self.char:
                                self.sprites[x][y].node.removeNode()
                                self.char['placed'] = False
                                self.tiles[x][y]['char']['placed'] = False
                                self.tiles[x][y]['char'] = None

                    self.sprites[self.cux][self.cuy] = Sprite.Sprite(GAME+'/textures/sprites/'+self.char['sprite']+'.png', 1)
                    self.sprites[self.cux][self.cuy].animation = 'stand'
                    self.sprites[self.cux][self.cuy].node.setPos(self.cux-2, self.cuy-2, .33+0.025)
                    self.sprites[self.cux][self.cuy].node.setScale(.3)
                    self.sprites[self.cux][self.cuy].node.reparentTo(self.root)
                    self.char['placed'] = True
                    self.tiles[self.cux][self.cuy]['char'] = self.char

            self.updateChar()
            self.updateButtons()

    def onTriangleClicked(self):
        for i,char in enumerate(self.chars):
            if char == self.tiles[self.cux][self.cuy]['char']:
                self.updateChar(delta=None, current=i)

    def onStartClicked(self):
        if self.remaining < self.capacity:
            seq = Sequence(
                Func( self.ignoreAll ),
                Parallel(
                    LerpColorInterval(self.l1frame,        .5, (1,1,1,0), (1,1,1,1)),
                    LerpColorInterval(self.r1frame,        .5, (1,1,1,0), (1,1,1,1)),
                    LerpColorInterval(self.squadframe,     .5, (1,1,1,0), (1,1,1,1)),
                    LerpColorInterval(self.capacityframe,  .5, (1,1,1,0), (1,1,1,1)),
                    LerpColorInterval(self.remainingframe, .5, (1,1,1,0), (1,1,1,1)),
                    LerpColorInterval(self.searchframe,    .5, (1,1,1,0), (.75,.75,.75,1)),
                    LerpColorInterval(self.statusframe,    .5, (1,1,1,0), (.75,.75,.75,1)),
                    LerpColorInterval(self.startframe,     .5, (1,1,1,0), (.75,.75,.75,1)),
                ),
                Parallel(
                    LerpPosInterval(  self.hprcontainer,   .5, (0,0,-2), (0,0,-.415)),
                    LerpPosInterval(  self.cardframe,      .5, (v*63,0,2), (v*63,0,u*65)),
                    LerpPosInterval(  self.fbgframe,       .5, (-v*97,0,2), (-v*97,0,v*61)),
                ),
                Func( self.l1frame.removeNode ),
                Func( self.r1frame.removeNode ),
                Func( self.fbgframe.removeNode ),
                Func( self.cardframe.removeNode ),
                Func( self.squadframe.removeNode ),
                Func( self.capacityframe.removeNode ),
                Func( self.remainingframe.removeNode ),
                Func( self.searchframe.removeNode ),
                Func( self.statusframe.removeNode ),
                Func( self.startframe.removeNode ),
                Func( self.hprcontainer.removeNode ),
            ).start()

            formation = []
            for x,l in enumerate(self.tiles):
                for y,t in enumerate(l):
                    if t['char']:
                        formation.append({'charid': t['char']['id'], 'coords': t['coords'], 'direction': self.direction})
            self.command(formation)

    def updateButtons(self):

        if self.remaining < self.capacity:
            self.startframe.setColor((1,1,1,1))
        else:
            self.startframe.setColor((.75,.75,.75,1))
        if self.tiles[self.cux][self.cuy]['char']:
            self.statusframe.setColor((.75,.75,.75,1)) # TODO
            self.searchframe.setColor((1,1,1,1))
        else:
            self.statusframe.setColor((.75,.75,.75,1))
            self.searchframe.setColor((.75,.75,.75,1))

class ScrollableList(DirectObject.DirectObject):

    def __init__(self, style, x, y, w, h, flushToTop, columns, rows, maxrows, cancelcallback, title=None):

        self.style = style

        # positioning
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.flushToTop = flushToTop

        self.offset = 0
        self.rowheight = 16
        self.index = 0
        self.internalIndex = 0
        self.columns = columns
        self.rows = rows
        self.maxrows = maxrows
        self.cancelcallback = cancelcallback
        self.container = None
        self.maxoffset = len(self.rows) - self.maxrows

        menutexture = loader.loadTexture(GAME+'/textures/gui/menu2.png')
        menutexture.setMagfilter(Texture.FTNearest)
        menutexture.setMinfilter(Texture.FTNearest)

        handtexture = loader.loadTexture(GAME+'/textures/gui/hand.png')
        handtexture.setMagfilter(Texture.FTNearest)
        handtexture.setMinfilter(Texture.FTNearest)

        rulertexture = loader.loadTexture(GAME+'/textures/gui/ruler.png')
        rulertexture.setMagfilter(Texture.FTNearest)
        rulertexture.setMinfilter(Texture.FTNearest)

        self.frame = DirectFrame(
            frameColor = (1, 1, 1, 0),
            frameSize = ( -v*self.w/2.0, v*self.w/2.0, -v*self.h/2.0, v*self.h/2.0 ),
            pos = (v*self.x, 0, -v*self.y),
            geom = WindowNodeDrawer(self.w, self.h, self.style, title),
        )
        self.frame.setTransparency(True)

        self.hand = DirectFrame(
            frameTexture = handtexture,
            frameColor = (1, 1, 1, 1),
            frameSize = ( -v*8, v*8, -v*8, v*8 ),
            pos = (-v*(self.w/2+3.5), 0, v*(self.h/2-self.flushToTop+3)),
            parent = self.frame
        )

        self.ruler = DirectFrame(
            frameTexture = rulertexture,
            frameColor = (1, 1, 1, 1),
            frameSize = ( -v*4, v*4, -v*4, v*4 ),
            pos = (v*(self.w/2.0-1), 0, v*(self.h/2.0-self.flushToTop)),
            parent = self.frame
        )
        if len(rows) <= self.maxrows:
            self.ruler['frameColor'] = (1,1,1,0)

        seq = Sequence()
        seq.append(Func(self.printContent, self.offset))
        seq.append(LerpScaleInterval(self.frame, 0.1, 1, startScale=0.1))
        seq.append(Func(self.acceptAll))
        seq.start()

    def printContent(self, offset=0):

        if self.container:
            self.container.removeNode()           
        self.container = DirectFrame(parent=self.frame)

        for cid,column in enumerate(self.columns):
            for y,i in enumerate(range(offset, self.maxrows+offset)):
                rid = i
                row = self.rows[rid]
                label = DirectLabel(
                    parent = self.container,
                    color = (0,0,0,0),
                    text_fg = (1,1,1,1),
                    text = row['cells'][cid],
                    scale = regularscale,
                    text_font = column['font'],
                    text_align = column['align'],
                    pos = (v*column['x'], 0, v*(self.h/2.0-self.flushToTop-self.rowheight*y))
                )
                if not row['enabled']:
                    label['text_fg'] = (1,1,1,.5)

    def acceptAll(self):
        self.accept(CROSS_BTN,  self.onCrossClicked)
        self.accept(CIRCLE_BTN, self.onCircleClicked)
        self.accept("arrow_down",        lambda: self.updateIndex( 1))
        self.accept("arrow_down-repeat", lambda: self.updateIndex( 1))
        self.accept("arrow_up",          lambda: self.updateIndex(-1))
        self.accept("arrow_up-repeat",   lambda: self.updateIndex(-1))

    def updateIndex(self, direction):
        hover_snd.play()
        next = self.index + direction
        # Array navigation.
        internalNext = (self.internalIndex + direction)
        if internalNext < len(self.rows) and internalNext > -1:
            self.internalIndex = internalNext
            # Move relative to ruler's existing position; 0 = no change.
            self.ruler.setPos(self.ruler, 0, 0, -v*direction*(self.rowheight*self.maxrows/len(self.rows)))
        # Printed list navigation.
        if next == self.maxrows:
            next = self.maxrows-1
            if self.offset < self.maxoffset:
                self.offset = self.offset + 1
                self.printContent(self.offset)
        if next == -1:
            next = 0
            if self.offset > 0:
                self.offset = self.offset - 1
                self.printContent(self.offset)
        self.hand.setPos(-v*(self.w/2+3.5), 0, v*(self.h/2-self.flushToTop-self.rowheight*next+3))        
        self.index = next

    def onCircleClicked(self):
        # self.index is in range(0, viewable row count); it is not true where len(rows) > maxrows
        if self.rows[self.internalIndex]['enabled']:
            clicked_snd.play()
            self.commandAndDestroy(self.rows[self.internalIndex]['callback'])

    def onCrossClicked(self):
        cancel_snd.play()
        self.commandAndDestroy(self.cancelcallback)

    def commandAndDestroy(self, callback):
        seq = Sequence()
        seq.append(LerpScaleInterval(self.frame, 0.1, 0.1, startScale=1))
        seq.append(Func(self.ignoreAll))
        seq.append(Func(self.frame.destroy))
        seq.append(Func(callback))
        seq.start()
########NEW FILE########
__FILENAME__ = KeyboardTileTraverser
from Config import *
from direct.showbase.DirectObject import DirectObject
import math
from operator import itemgetter
import GUI

class KeyboardTileTraverser(DirectObject):

    def __init__(self, client):
        DirectObject.__init__(self)
        self.client = client

    def acceptAll(self):
        self.accept(CIRCLE_BTN,                   self.onCircleClicked        )
        self.accept(CROSS_BTN,                    self.onCrossClicked         )
        self.accept("arrow_up",           lambda: self.onArrowClicked('up'   ))
        self.accept("arrow_down",         lambda: self.onArrowClicked('down' ))
        self.accept("arrow_left",         lambda: self.onArrowClicked('left' ))
        self.accept("arrow_right",        lambda: self.onArrowClicked('right'))
        self.accept("arrow_up-repeat",    lambda: self.onArrowClicked('up'   ))
        self.accept("arrow_down-repeat",  lambda: self.onArrowClicked('down' ))
        self.accept("arrow_left-repeat",  lambda: self.onArrowClicked('left' ))
        self.accept("arrow_right-repeat", lambda: self.onArrowClicked('right'))

    def onArrowClicked(self, direction):
        x = self.client.cursor.x
        y = self.client.cursor.y

        h = self.client.camhandler.container.getH()
        while h > 180:
            h -= 360
        while h < -180:
            h += 360

        if direction == 'up':
            if h >=    0 and h <  90:
                self.findTileAndUpdateCursorPos((x+1, y  ))
            if h >=  -90 and h <   0:
                self.findTileAndUpdateCursorPos((x  , y-1))
            if h >= -180 and h < -90:
                self.findTileAndUpdateCursorPos((x-1, y  ))
            if h >=   90 and h < 180:
                self.findTileAndUpdateCursorPos((x  , y+1))
        elif direction == 'down':
            if h >=    0 and h <  90:
                self.findTileAndUpdateCursorPos((x-1, y  ))
            if h >=  -90 and h <   0:
                self.findTileAndUpdateCursorPos((x  , y+1))
            if h >= -180 and h < -90:
                self.findTileAndUpdateCursorPos((x+1, y  ))
            if h >=   90 and h < 180:
                self.findTileAndUpdateCursorPos((x  , y-1))
        elif direction == 'left':
            if h >=    0 and h <  90:
                self.findTileAndUpdateCursorPos((x  , y+1))
            if h >=  -90 and h <   0:
                self.findTileAndUpdateCursorPos((x+1, y  ))
            if h >= -180 and h < -90:
                self.findTileAndUpdateCursorPos((x  , y-1))
            if h >=   90 and h < 180:
                self.findTileAndUpdateCursorPos((x-1, y  ))
        elif direction == 'right':
            if h >=    0 and h <  90:
                self.findTileAndUpdateCursorPos((x  , y-1))
            if h >=  -90 and h <   0:
                self.findTileAndUpdateCursorPos((x-1, y  ))
            if h >= -180 and h < -90:
                self.findTileAndUpdateCursorPos((x  , y+1))
            if h >=   90 and h < 180:
                self.findTileAndUpdateCursorPos((x+1, y  ))

    # You clicked on a tile, this can mean different things, so this is a dispatcher
    def onCircleClicked(self):
        if self.client.cursor.x is not False and self.client.party['yourturn']:

            x = self.client.cursor.x
            y = self.client.cursor.y
            z = self.client.cursor.z

            if self.client.charcard:
                self.client.charcard.hide()

            # we clicked an active walkable tile, let's move the character
            if self.client.party['map']['tiles'][x][y][z].has_key('walkablezone'):
                charid = self.client.party['map']['tiles'][x][y][z]['walkablezone']
                self.client.clicked_snd.play()
                dest = (x, y, z)
                self.client.send.GET_PATH(charid, dest)
                return

            # we clicked on a character
            if self.client.party['map']['tiles'][x][y][z].has_key('char'):
                charid = self.client.party['map']['tiles'][x][y][z]['char']
                self.client.clicked_snd.play()

                # we clicked on a target, let's attack it!
                if self.client.party['map']['tiles'][x][y][z].has_key('attackablezone'):
                    attackable = self.client.party['map']['tiles'][x][y][z]['attackablezone']
                    self.ignoreAll()
                    if self.client.charbars:
                        self.client.charbars.hide()
                    self.client.actionpreview = GUI.ActionPreview(
                        self.client.party['chars'][attackable],
                        self.client.party['chars'][charid],
                        16,
                        99,
                        lambda: GUI.AttackCheck(
                            lambda: self.client.send.ATTACK(attackable, charid),
                            self.client.send.UPDATE_PARTY
                        ),
                        self.client.send.UPDATE_PARTY
                    )

                # we clicked on the currently active character, let's display the menu
                elif self.client.party['chars'][charid]['active'] and self.client.party['yourturn']:
                    self.client.send.UPDATE_PARTY()
            else:
                self.client.clicked_snd.play()
                self.client.send.UPDATE_PARTY()
    
    def onCrossClicked(self):
        if self.client.cursor.x is not False and self.client.party['yourturn']:

            x = self.client.cursor.x
            y = self.client.cursor.y
            z = self.client.cursor.z

            if self.client.subphase == 'free':
                # if we clicked on a character
                if self.client.party['map']['tiles'][x][y][z].has_key('char'):
                    charid = self.client.party['map']['tiles'][x][y][z]['char']
                    self.client.send.GET_PASSIVE_WALKABLES(charid)

            elif self.client.subphase == 'passivewalkables':
                self.client.matrix.clearZone()
                self.client.cancel_snd.play()
                self.client.subphase = 'free'

            elif self.client.subphase == 'move':
                self.client.matrix.clearZone()
                self.client.cancel_snd.play()
                self.client.subphase = None
                self.client.send.UPDATE_PARTY()

            elif self.client.subphase == 'attack':
                self.client.matrix.clearZone()
                self.client.cancel_snd.play()
                self.client.subphase = None
                self.client.send.UPDATE_PARTY()

    # Returns the closest tile for the given x and y
    def findTileAndUpdateCursorPos(self, pos):
        fux, fuy = pos

        # list the possibles tiles, on official maps, this list should not excess 2 items
        possibles = []
        for x,xs in enumerate(self.client.party['map']['tiles']):
            for y,ys in enumerate(xs):
                for z,zs in enumerate(ys):
                    if not self.client.party['map']['tiles'][x][y][z] is None:
                        if fux == x and fuy == y:
                            d = math.fabs(z-self.client.cursor.z) # for each possible, compute the Z delta with the current tile
                            possibles.append((x, y, z, d))

        if len(possibles):
            # sort the possibles on Z delta, and get the closer tile
            selected = sorted(possibles, key=itemgetter(3))[0][0:3]

            self.client.hover_snd.play()
            self.client.updateCursorPos(selected)
########NEW FILE########
__FILENAME__ = Direction
from pandac.PandaModules import *
from direct.showbase import DirectObject
from panda3d.core import CollisionTraverser, CollisionNode, CollisionHandlerQueue, CollisionRay, BitMask32, CardMaker, NodePath, Texture, TextureStage
from direct.task.Task import Task

GAME = 'lijj'

class Chooser(DirectObject.DirectObject):
    
    def __init__(self, charid, sprite, camhandler, callback, cancelcallback):
    
        self.charid = charid
        self.sprite = sprite
        self.camhandler = camhandler
        self.callback = callback
        self.cancelcallback = cancelcallback
        self.initdir  = self.sprite.realdir
        self.hidir = None

        # Textures
        self.tex = [ 0 for i in range(4) ]
        for i in range(4):
            self.tex[i] = loader.loadTexture(GAME+'/textures/gui/direction'+str(i)+'.png')
            self.tex[i].setMagfilter(Texture.FTNearest)
            self.tex[i].setMinfilter(Texture.FTNearest)

        # Sounds
        self.hover_snd   = base.loader.loadSfx(GAME+"/sounds/hover.ogg")
        self.clicked_snd = base.loader.loadSfx(GAME+"/sounds/clicked.ogg")
        self.cancel_snd  = base.loader.loadSfx(GAME+"/sounds/cancel.ogg")

        # Buttons container
        self.directionRoot = sprite.node.attachNewNode( "directionRoot" )

        cm = CardMaker('card')
        cm.setFrame(-2, 2, -2, 2) 
        self.card = render.attachNewNode(cm.generate())
        self.card.setTexture(self.tex[self.initdir-1])
        self.card.setTransparency(True)
        self.card.setBillboardPointEye()
        self.card.reparentTo(self.directionRoot)
        self.card.setPos(0,0,6)
        self.card.setScale(256.0/240.0)

        self.accept("b", self.onCircleClicked)
        self.accept("space", self.onCrossClicked)
        self.accept("arrow_up", lambda: self.onArrowClicked('up'))
        self.accept("arrow_down", lambda: self.onArrowClicked('down'))
        self.accept("arrow_left", lambda: self.onArrowClicked('left'))
        self.accept("arrow_right", lambda: self.onArrowClicked('right'))

    def onCircleClicked(self):
        self.directionRoot.removeNode()
        self.ignoreAll()
        self.clicked_snd.play()
        self.callback(self.charid, self.hidir)

    def onCrossClicked(self):
        self.directionRoot.removeNode()
        self.ignoreAll()
        self.cancel_snd.play()
        self.sprite.setRealDir(self.initdir)
        self.cancelcallback()

    def onArrowClicked(self, direction):

        self.hover_snd.play()

        h = self.camhandler.container.getH()
        while h > 180:
            h -= 360
        while h < -180:
            h += 360

        if direction == 'up':
            if h >=    0 and h <  90:
                self.hidir = '1'
                self.card.setTexture(self.tex[0])
            if h >=  -90 and h <   0:
                self.hidir = '4'
                self.card.setTexture(self.tex[3])
            if h >= -180 and h < -90:
                self.hidir = '3'
                self.card.setTexture(self.tex[2])
            if h >=   90 and h < 180:
                self.hidir = '2'
                self.card.setTexture(self.tex[1])
        elif direction == 'down':
            if h >=    0 and h <  90:
                self.hidir = '3'
                self.card.setTexture(self.tex[2])
            if h >=  -90 and h <   0:
                self.hidir = '2'
                self.card.setTexture(self.tex[1])
            if h >= -180 and h < -90:
                self.hidir = '1'
                self.card.setTexture(self.tex[0])
            if h >=   90 and h < 180:
                self.hidir = '4'
                self.card.setTexture(self.tex[3])
        elif direction == 'left':
            if h >=    0 and h <  90:
                self.hidir = '2'
                self.card.setTexture(self.tex[1])
            if h >=  -90 and h <   0:
                self.hidir = '1'
                self.card.setTexture(self.tex[0])
            if h >= -180 and h < -90:
                self.hidir = '4'
                self.card.setTexture(self.tex[3])
            if h >=   90 and h < 180:
                self.hidir = '3'
                self.card.setTexture(self.tex[2])
        elif direction == 'right':
            if h >=    0 and h <  90:
                self.hidir = '4'
                self.card.setTexture(self.tex[3])
            if h >=  -90 and h <   0:
                self.hidir = '3'
                self.card.setTexture(self.tex[2])
            if h >= -180 and h < -90:
                self.hidir = '2'
                self.card.setTexture(self.tex[1])
            if h >=   90 and h < 180:
                self.hidir = '1'
                self.card.setTexture(self.tex[0])

        self.sprite.setRealDir(self.hidir)


########NEW FILE########
__FILENAME__ = animate_water
from panda3d.core import *
from direct.interval.IntervalGlobal import *
import sys, getopt, inspect, os, subprocess

# Prepare variables.
tethicalTestApplication = ''
game = ''
gameName = ''
basePath = ''
testName = 'map-event-test'
thisWholeFilename = os.path.abspath(__file__)
thisFilename = os.path.basename(os.path.abspath(__file__))
targetMapNameWithoutExtension = os.path.basename(os.path.dirname(os.path.abspath(__file__)))
targetMapName = os.path.basename(os.path.dirname(os.path.abspath(__file__))) + ".json"
targetMapFullPath = ''
# Prepare path components of event Python file.
path = os.path.abspath(__file__)
folders=[]
while 1:
	path,folder=os.path.split(path)
	if folder!="":
		folders.append(folder)
	else:
		if path!="":
			folders.append(path)
		break
folders.reverse()
# Get Tethical application and maps path.
if 'client' in folders:
	i = folders.index('client')
	if len(folders) > i+1:
		basePath = os.path.join(*folders[:i])
		tethicalTestApplication = os.path.join(*folders[:i+1] + ['Tests.py'])
		game = os.path.join(*folders[:i+2])
		gameName = folders[i+1]
		targetMapFullPath = os.path.join(*folders[:i+2] + ['models', 'maps', targetMapName])
		pass
	pass

# Prepare error class.
class UsageError(Exception):
	def __init__(self, msg):
		self.msg = msg
#
def main(argv=None):
	"""
This is a Tethical client-side map event script. When called from the command-line, the event will load itself into Tethical's map test application. Otherwise, calling the map event from a map description file will result in the event's programming running right before the map is displayed for the user (i.e. at the very beginning of a battle).
	"""
	# Make sure not to throw an exception when dealing with arguments.
	try:
		argv
	except NameError:
		argv = None
	# Pick the appropriate arguments, if not set already.
	if argv is None:
		argv = sys.argv
	try:
		try:
			opts, args = getopt.getopt(argv[1:], "h", ["help"])
		except getopt.error, msg:
			raise UsageError(msg)
		# Create a list with only the options.
		onlyOptions = [a[0] for a in opts]
		# Find supplied options.
		if ('-h' in onlyOptions) or ('--help' in onlyOptions):
			raise UsageError ("Usage: python " + os.path.basename(os.path.abspath(__file__)) + "\n\n" + main.__doc__)
		elif len(argv[1:]) != 0:
			raise UsageError ("Usage: python " + os.path.basename(os.path.abspath(__file__)) + "\n" + "For help, use --help")
		pass
		# Finally, run the test application.
		if tethicalTestApplication is not '' and thisFilename is not '' and targetMapFullPath is not '':
			print "Running: python " + tethicalTestApplication + " " + testName + " " + basePath + " " + gameName + " " + targetMapName + " " + thisWholeFilename
			subprocess.call(["python", tethicalTestApplication, testName, basePath, gameName, targetMapName, thisWholeFilename])
		else:
			raise UsageError ("Cannot execute test. This client-side map event is not in a location conducive to being run.")
	except UsageError, err:
		print >>sys.stderr, err.msg
		return 2
# Run the test event, or run the event code, depending on context.
if __name__ == "__main__":
	sys.exit(main())
else:
	failedToLoadAtLeastOneTexture = False
	# Generate a PNMImage.
	def setupTexture(path):
		global failedToLoadAtLeastOneTexture
		# Set up blank image as a texture.
		texturePNMImage = PNMImage ()
		# Have Panda3d get the appropriate filename.
		file = Filename.fromOsSpecific(path)
		# Make sure the file actually exists first.
		try:
			texture = loader.loadTexture(file) # Use Panda3d's loader to load a pandac.PandaModules.Texture into a variable.
			texture.store(texturePNMImage) # Signal Panda3d to store the contents of what it just loaded into our blank image.
		except:
			failedToLoadAtLeastOneTexture = True
		# Return just the image (not the pandac.PandaModules.Texture).
		return texturePNMImage
	# Prepare to store a record of PNMImage objects.
	textures = []
	# Join each image frame's PNMImage to the record, resulting in: [PNMImage-1, ..., PNMImage-n]
	textures = textures + [setupTexture(os.path.join( gameName, 'textures', 'map', targetMapNameWithoutExtension+'-2.png'))]
	textures = textures + [setupTexture(os.path.join( gameName, 'textures', 'map', targetMapNameWithoutExtension+'-3.png'))]
	textures = textures + [setupTexture(os.path.join( gameName, 'textures', 'map', targetMapNameWithoutExtension+'-4.png'))]
	textures = textures + [setupTexture(os.path.join( gameName, 'textures', 'map', targetMapNameWithoutExtension+'-5.png'))]
	textures = textures + [setupTexture(os.path.join( gameName, 'textures', 'map', targetMapNameWithoutExtension+'-6.png'))]
	textures = textures + [setupTexture(os.path.join( gameName, 'textures', 'map', targetMapNameWithoutExtension+'-7.png'))]
	textures = textures + [setupTexture(os.path.join( gameName, 'textures', 'map', targetMapNameWithoutExtension+'-8.png'))]
	textures = textures + [setupTexture(os.path.join( gameName, 'textures', 'map', targetMapNameWithoutExtension+'-9.png'))]
	textures = textures + [setupTexture(os.path.join( gameName, 'textures', 'map', targetMapNameWithoutExtension+'-1.png'))]
	# Prepare to get the NodePath of the loaded map object (attached to the render object).
	targetMapName = os.path.basename(os.path.dirname(os.path.abspath(__file__))) + ".egg"
	# Get the NodePath.
	mapObject = render.find("**/"+targetMapName+"/Cube")
	# If the NodePath was found, add the sequence of texture switches to the scene in order to animate water.
	if not mapObject.isEmpty() and not failedToLoadAtLeastOneTexture:
		# Prepare the Sequence object.
		seq = Sequence()
		# Go through the range of textures in the record.
		for i in range(len(textures)):
			# Prepare the delay between texture switches.
			delay = 0.14
			# Prepare a function to switch the texture of the passed in NodePath.
			def f(x, c):
				tex = x.findTexture('*')
				tex.load(textures[c])
				pass
			# Push the function to the animation sequence.
			seq.append(Func(f, mapObject, i))
			# Push the wait time to the animation sequence.
			seq.append(Wait(delay))
		# Loop indefinitely.
		seq.loop()
		pass
	else:
		print "Event failed to find map: " + targetMapName
########NEW FILE########
__FILENAME__ = main
from Config import *
import direct.directbase.DirectStart
from panda3d.core import *
from direct.gui.DirectGui import *
from direct.task.Task import Task
from direct.distributed.PyDatagramIterator import *
from direct.interval.IntervalGlobal import *
import GUI
from CameraHandler import *
from DirectionChooser import *
from BattleGraphics import *
from Sky import *
from Matrix import *
from Cursor import *
from AT import *
from Send import *
from Controllers import *
from KeyboardTileTraverser import *
import SequenceBuilder

class Client(object):

    def __init__(self):
        self.music = base.loader.loadSfx(GAME+'/music/24.ogg')
        self.music.setLoop(True)
        self.music.play()
        self.background = GUI.Background(self.loginScreen)

    # Display the login window
    def loginScreen(self):
        self.loginwindow = GUI.LoginWindow(self.authenticate)

    def processData(self, datagram):
        iterator = PyDatagramIterator(datagram)
        source = datagram.getConnection()
        callback = iterator.getString()
        getattr(globals()[callback], 'execute')(self, iterator)

    # This task process data sent by the server, if any
    def tskReaderPolling(self, taskdata):
        if self.cReader.dataAvailable():
            datagram=NetDatagram()
            if self.cReader.getData(datagram):
                self.processData(datagram)
        return Task.cont

    # Setup connection and send the LOGIN datagram with credentials
    def authenticate(self):
        login = self.loginwindow.loginEntry.get()
        password = self.loginwindow.passwordEntry.get()

        self.cManager  = QueuedConnectionManager()
        self.cListener = QueuedConnectionListener(self.cManager, 0)
        self.cReader   = QueuedConnectionReader(self.cManager, 0)
        self.cReader.setTcpHeaderSize(4)

        self.myConnection = self.cManager.openTCPClientConnection(IP, PORT, 5000)
        if self.myConnection:
            self.cReader.addConnection(self.myConnection)
            self.send = Send(self.cManager, self.myConnection)
            print 'Client listening on', IP, ':', PORT
            taskMgr.add(self.tskReaderPolling, "Poll the connection reader")

            self.send.LOGIN_MESSAGE(login, password)

        else:
            print 'Can\'t connect to server on', IP, ':', PORT

    # The battle begins
    def battle_init(self):
        self.subphase = None

        # Instanciate the camera handler
        self.camhandler = CameraHandler()

        # Instanciate the keyboard tile traverser
        self.inputs = KeyboardTileTraverser(self)

        # Instanciate the battle graphics
        self.battleGraphics = BattleGraphics(self.party['map'])
        
        # Light the scene
        self.battleGraphics.lightScene()
        
        # Display the terrain
        self.battleGraphics.displayTerrain()
        
        # Play the background music
        self.music = base.loader.loadSfx(GAME+'/music/'+self.party['map']['music']+'.ogg')
        self.music.setLoop(True)
        self.music.play()
        
        # Load sounds
        self.hover_snd   = base.loader.loadSfx(GAME+"/sounds/hover.ogg")
        self.clicked_snd = base.loader.loadSfx(GAME+"/sounds/clicked.ogg")
        self.cancel_snd  = base.loader.loadSfx(GAME+"/sounds/cancel.ogg")
        self.attack_snd  = base.loader.loadSfx(GAME+"/sounds/attack.ogg")
        self.die_snd     = base.loader.loadSfx(GAME+"/sounds/die.ogg")
        
        # Place highlightable tiles on the map
        self.matrix = Matrix(self.battleGraphics, self.party['map'])
        self.matrix.placeChars(self.party['chars'])
        
        # Instanciate and hide the AT flag
        self.at = AT()
        self.at.hide()
        
        self.charbars = None
        self.charcard = None
        self.actionpreview = None

        # Generate the sky and attach it to the camera
        self.sky = Sky(self.party['map'])

        # Tasks
        taskMgr.add(self.characterDirectionTask , 'characterDirectionTask')

        # Cursor stuff
        self.cursor = Cursor(self.battleGraphics, self.matrix.container)

        # Add the special effects
        self.battleGraphics.addEffects()

        # Battle intro animation
        SequenceBuilder.battleIntroduction(self).start()

    def updateAllSpritesAnimations(self, animation):
        for i,charid in enumerate(self.matrix.sprites):
            Sequence(
                Wait(float(i)/6.0),
                Func(self.updateSpriteAnimation, charid, animation),
            ).start()

    def end(self):
        taskMgr.remove('characterDirectionTask')
        for child in render.getChildren():
            child.removeNode()
        self.camhandler.destroy()
        self.coords.destroy()
        self.sky.remove()
        self.background = GUI.Background(self.send.GET_PARTIES)

    def showMenu(self, charid):
        self.inputs.ignoreAll()
        self.camhandler.ignoreAll()

        canmove = self.party['chars'][charid]['canmove']
        canact  = self.party['chars'][charid]['canact']

        columns = [ { 'x': -25, 'font': GUI.regularfont, 'align': TextNode.ALeft   }, ]

        rows = [
            { 'cells': ['Move'        ], 'enabled': canmove, 'callback': lambda: self.send.GET_WALKABLES  (charid) },
            { 'cells': ['Act'         ], 'enabled': canact , 'callback': lambda: self.onAttackClicked(charid) },
            { 'cells': ['Wait'        ], 'enabled': True   , 'callback': lambda: self.onWaitClicked  (charid) },
            { 'cells': ['Status'      ], 'enabled': False  , 'callback': lambda: self.onWaitClicked  (charid) },
            { 'cells': ['Auto-Battle' ], 'enabled': False  , 'callback': lambda: self.onWaitClicked  (charid) },
        ]

        GUI.ScrollableList(
            'shadowed', 73, -8, 62.0, 91.0, 16, 
            columns, rows, 5, 
            lambda: self.onCancelClicked(charid), 
            'Menu'
        )

    def moveCheck(self, charid, orig, origdir, dest):
        self.inputs.ignoreAll()
        self.camhandler.ignoreAll()
        GUI.MoveCheck(
            lambda: self.send.MOVE_TO(charid, dest),
            lambda: self.cancelMove(charid, orig, origdir)
        )

    def cancelMove(self, charid, orig, origdir):
        self.matrix.sprites[charid].node.setPos(self.battleGraphics.logic2terrain(orig))
        self.matrix.sprites[charid].setRealDir(origdir)
        self.send.UPDATE_PARTY()

    # Makes a character look at another one
    def characterLookAt(self, charid, targetid):
        (x1, y1, z1) = self.matrix.getCharacterCoords(charid)
        (x2, y2, z2) = self.matrix.getCharacterCoords(targetid)
        if x1 > x2:
            self.matrix.sprites[charid].setRealDir(3)
        if x1 < x2:
            self.matrix.sprites[charid].setRealDir(1)
        if y1 > y2:
            self.matrix.sprites[charid].setRealDir(4)
        if y1 < y2:
            self.matrix.sprites[charid].setRealDir(2)

    # Update the status (animation) of a sprite after something happened
    def updateSpriteAnimation(self, charid, animation=False):
        if animation:
            self.matrix.sprites[charid].animation = animation
        else:
            stats = self.party['chars'][charid]
            if stats['hp'] >= (stats['hpmax']/2):
                self.matrix.sprites[charid].animation = 'walk'
            if stats['hp'] < (stats['hpmax']/2):
                self.matrix.sprites[charid].animation = 'weak'
            if stats['hp'] <= 0:
                self.matrix.sprites[charid].animation = 'dead'
                self.die_snd.play()
        h = self.camhandler.container.getH()
        self.matrix.sprites[charid].updateDisplayDir( h, True )

    def updateCursorPos(self, pos):

        self.camhandler.move(self.battleGraphics.logic2terrain(pos))

        (x, y, z) = pos
        tile = self.party['map']['tiles'][x][y][z]

        self.cursor.move(x, y, z, tile)

        if self.charbars:
            self.charbars.hide()

        if self.party['map']['tiles'][x][y][z].has_key('char'):
            charid = self.party['map']['tiles'][x][y][z]['char']
            char = self.party['chars'][charid]
            if self.subphase == 'attack':
                self.charbars = GUI.CharBarsRight(char)
            else:
                self.charbars = GUI.CharBarsLeft(char)

        try:
            self.coords.update(tile)
        except:
            self.coords = GUI.Coords(tile)

### Events

    # Battle func
    def setupWalkableTileChooser(self, charid, walkables):
        self.inputs.acceptAll()
        self.camhandler.acceptAll()
        self.subphase = 'move'
        self.matrix.setupWalkableZone(charid, walkables)
        if self.charcard:
            self.charcard.hide()

    # Battle func
    def setupAttackableTileChooser(self, charid, attackables):
        self.inputs.acceptAll()
        self.camhandler.acceptAll()
        self.subphase = 'attack'
        self.matrix.setupAttackableZone(charid, attackables)
        if self.charcard:
            self.charcard.hide()

    # Battle func
    def setupDirectionChooser(self, charid):
        self.inputs.ignoreAll()
        self.camhandler.acceptAll()
        self.at.hide()
        DirectionChooser(charid, self.matrix.sprites[charid], self.camhandler, self.send.WAIT, self.send.UPDATE_PARTY)

    # Attack button clicked
    def onAttackClicked(self, charid):
        self.inputs.ignoreAll()
        self.camhandler.ignoreAll()
        GUI.Help(
            0, 25, 155, 44,
            'shadowed', 'Check',
            'Specify the target with the cursor.\nPress the %c button to select.' % CIRCLE_BTN.upper(),
            lambda: self.send.GET_ATTACKABLES(charid),
            self.send.UPDATE_PARTY,
        )

    # Wait menu item chosen
    def onWaitClicked(self, charid):
        self.inputs.ignoreAll()
        self.camhandler.ignoreAll()
        GUI.Help(
            0, 25, 135, 60,
            'shadowed', 'Check',
            'Specify the direction with\nthe Directional buttons.\nPress the %c button to select.' % CIRCLE_BTN.upper(),
            lambda: self.setupDirectionChooser(charid),
            self.send.UPDATE_PARTY,
        )

    # Cancel menu item chosen
    def onCancelClicked(self, charid):
        self.inputs.acceptAll()
        self.camhandler.acceptAll()
        if self.charcard:
            self.charcard.hide()

### Tasks

    # Updates the displayed direction of a character according to the camera angle
    def characterDirectionTask(self, task):
        h = self.camhandler.container.getH()
        for charid in self.matrix.sprites:
            self.matrix.sprites[charid].updateDisplayDir( h );
        return Task.cont

Client()
run()

########NEW FILE########
__FILENAME__ = Matrix
from Config import *
from panda3d.core import TransparencyAttrib, Texture
import Sprite

class Matrix(object):

    def __init__(self, battleGraphics, mp):
        self.battleGraphics = battleGraphics
        self.mp = mp
        self.container = render.attachNewNode( "matrixContainer" )

        self.tiles = [ [ [ None for z in range(self.mp['z']) ] for y in range(self.mp['y']) ] for x in range(self.mp['x']) ]

        for x,xs in enumerate(self.mp['tiles']):
            for y,ys in enumerate(xs):
                for z,zs in enumerate(ys):
                    if not self.mp['tiles'][x][y][z] is None:
                        slope = self.mp['tiles'][x][y][z]['slope']
                        scale = self.mp['tiles'][x][y][z]['scale']
                        depth = self.mp['tiles'][x][y][z]['depth']

                        self.tiles[x][y][z] = loader.loadModel(GAME+"/models/slopes/"+slope)
                        self.tiles[x][y][z].reparentTo( self.container )
                        self.tiles[x][y][z].setPos(self.battleGraphics.logic2terrain( (x, y, z+depth+0.05) ))
                        self.tiles[x][y][z].setScale(3.7, 3.7, 6.0/7.0*3.7*scale)
                        self.tiles[x][y][z].setTransparency(TransparencyAttrib.MAlpha)
                        self.tiles[x][y][z].setColor( 0, 0, 0, 0 )

        self.wtex = loader.loadTexture(GAME+'/textures/walkable.png')
        self.wtex.setMagfilter(Texture.FTNearest)
        self.wtex.setMinfilter(Texture.FTNearest)
        
        self.atex = loader.loadTexture(GAME+'/textures/attackable.png')
        self.atex.setMagfilter(Texture.FTNearest)
        self.atex.setMinfilter(Texture.FTNearest)

    def placeChars(self, chars):
        self.chars = chars
        self.sprites = {}

        for x,xs in enumerate(self.mp['tiles']):
            for y,ys in enumerate(xs):
                for z,zs in enumerate(ys):
                    if not self.mp['tiles'][x][y][z] is None:
                        slope = self.mp['tiles'][x][y][z]['slope']
                        scale = self.mp['tiles'][x][y][z]['scale']
                        depth = self.mp['tiles'][x][y][z]['depth']

                        if self.mp['tiles'][x][y][z].has_key('char'):
                            charid = self.mp['tiles'][x][y][z]['char']
                            char = self.chars[charid]
                            sprite = Sprite.Sprite(GAME+'/textures/sprites/'+char['sprite']+'.png', int(char['direction']))
                            sprite.animation = 'stand'
                            sprite.node.setPos(self.battleGraphics.logic2terrain((x,y,z)))
                            sprite.node.reparentTo( render )
                            self.sprites[charid] = sprite

    # Draw blue tile zone
    def setupPassiveWalkableZone(self, walkables):
        for x,y,z in walkables:
            self.tiles[x][y][z].setColor(1, 1, 1, 1)
            self.tiles[x][y][z].setTexture(self.wtex)

    # Tag a zone as walkable or active-walkable
    def setupWalkableZone(self, charid, walkables):
        for x,y,z in walkables:
            self.tiles[x][y][z].setColor(1, 1, 1, 1)
            self.tiles[x][y][z].setTexture(self.wtex)
            self.mp['tiles'][x][y][z]['walkablezone'] = charid

    # Draw and tag the red tile zone
    def setupAttackableZone(self, charid, attackables):
        for x,y,z in attackables:
            self.tiles[x][y][z].setColor(1, 1, 1, 1)
            self.tiles[x][y][z].setTexture(self.atex)
            self.mp['tiles'][x][y][z]['attackablezone'] = charid

    # Clear any tile zone
    def clearZone(self):
        for x,xs in enumerate(self.mp['tiles']):
            for y,ys in enumerate(xs):
                for z,zs in enumerate(ys):
                    if not self.mp['tiles'][x][y][z] is None:
                        self.tiles[x][y][z].setColor(0, 0, 0, 0)
                        if self.mp['tiles'][x][y][z].has_key('walkablezone'):
                            del self.mp['tiles'][x][y][z]['walkablezone']
                        if self.mp['tiles'][x][y][z].has_key('attackablezone'):
                            del self.mp['tiles'][x][y][z]['attackablezone']

    # Returns the logic coordinates of a character
    def getCharacterCoords(self, charid):
        for x,xs in enumerate(self.mp['tiles']):
            for y,ys in enumerate(xs):
                for z,zs in enumerate(ys):
                    if not self.mp['tiles'][x][y][z] is None:
                        if self.mp['tiles'][x][y][z].has_key('char') and self.mp['tiles'][x][y][z]['char'] != 0:
                            if charid == self.mp['tiles'][x][y][z]['char']:
                                return (x, y, z)

########NEW FILE########
__FILENAME__ = Send
from direct.distributed.PyDatagram import PyDatagram, ConnectionWriter
import json

# Datagrams to be sent to the server
class Send(object):

    def __init__(self, cManager, myConnection):
        self.cWriter = ConnectionWriter(cManager, 0)
        self.cWriter.setTcpHeaderSize(4)
        self.myConnection = myConnection

    # Get the path from the server, and makes the character walk on it
    def GET_PATH(self, charid, dest):
        (x, y, z) = dest
        myPyDatagram = PyDatagram()
        myPyDatagram.addString('GET_PATH')
        myPyDatagram.addString(charid)
        myPyDatagram.addUint8(x)
        myPyDatagram.addUint8(y)
        myPyDatagram.addUint8(z)
        self.cWriter.send(myPyDatagram, self.myConnection)

    # Send the MOVE_TO packet and update the map tags with new char coords
    def MOVE_TO(self, charid, dest):
        (x2, y2, z2) = dest
        myPyDatagram = PyDatagram()
        myPyDatagram.addString('MOVE_TO')
        myPyDatagram.addString(charid)
        myPyDatagram.addUint8(x2)
        myPyDatagram.addUint8(y2)
        myPyDatagram.addUint8(z2)
        self.cWriter.send(myPyDatagram, self.myConnection)

    # Send the ATTACK packet, get the returned damages and display the attack animation
    def ATTACK(self, charid, targetid):
        myPyDatagram = PyDatagram()
        myPyDatagram.addString('ATTACK')
        myPyDatagram.addString(charid)
        myPyDatagram.addString(targetid)
        self.cWriter.send(myPyDatagram, self.myConnection)

    # The team is formed, send the formation data to the server
    def FORMATION_READY(self, formation):
        myPyDatagram = PyDatagram()
        myPyDatagram.addString('FORMATION_READY')
        myPyDatagram.addString(json.dumps(formation))
        self.cWriter.send(myPyDatagram, self.myConnection)

    def GET_PARTIES(self):
        myPyDatagram = PyDatagram()
        myPyDatagram.addString('GET_PARTIES')
        self.cWriter.send(myPyDatagram, self.myConnection)

    def GET_MAPS(self):
        myPyDatagram = PyDatagram()
        myPyDatagram.addString('GET_MAPS')
        self.cWriter.send(myPyDatagram, self.myConnection)

    # Send the party details to the server in order to instanciate a party
    def CREATE_PARTY(self, mapname):
        import time
        partyname = str(int(time.time()))
        myPyDatagram = PyDatagram()
        myPyDatagram.addString('CREATE_PARTY')
        myPyDatagram.addString(partyname)
        myPyDatagram.addString(mapname)
        self.cWriter.send(myPyDatagram, self.myConnection)

    # Join a party
    def JOIN_PARTY(self, name):
        myPyDatagram = PyDatagram()
        myPyDatagram.addString('JOIN_PARTY')
        myPyDatagram.addString(name)
        self.cWriter.send(myPyDatagram, self.myConnection)

    # Try to log into the server
    def LOGIN_MESSAGE(self, login, password):
        myPyDatagram = PyDatagram()
        myPyDatagram.addString('LOGIN_MESSAGE')
        myPyDatagram.addString(login)
        myPyDatagram.addString(password)
        self.cWriter.send(myPyDatagram, self.myConnection)

    # The battle main dispatcher, see it as a "next turn"
    def UPDATE_PARTY(self):
        myPyDatagram = PyDatagram()
        myPyDatagram.addString('UPDATE_PARTY')
        self.cWriter.send(myPyDatagram, self.myConnection)

    def GET_PASSIVE_WALKABLES(self, charid):
        myPyDatagram = PyDatagram()
        myPyDatagram.addString('GET_PASSIVE_WALKABLES')
        myPyDatagram.addString(charid)
        self.cWriter.send(myPyDatagram, self.myConnection)

    # Move button clicked
    def GET_WALKABLES(self, charid):
        myPyDatagram = PyDatagram()
        myPyDatagram.addString('GET_WALKABLES')
        myPyDatagram.addString(charid)
        self.cWriter.send(myPyDatagram, self.myConnection)

    def GET_ATTACKABLES(self, charid):
        myPyDatagram = PyDatagram()
        myPyDatagram.addString('GET_ATTACKABLES')
        myPyDatagram.addString(charid)
        self.cWriter.send(myPyDatagram, self.myConnection)

    # The direction has been chosen, send the WAIT datagram
    def WAIT(self, charid, direction):
        myPyDatagram = PyDatagram()
        myPyDatagram.addString('WAIT')
        myPyDatagram.addString(charid)
        myPyDatagram.addUint8(direction)
        self.cWriter.send(myPyDatagram, self.myConnection)
########NEW FILE########
__FILENAME__ = SequenceBuilder
from direct.interval.IntervalGlobal import *
import GUI

def battleIntroduction(client):
    seq = Sequence()
    i1 = LerpColorInterval(client.transitionframe, 5, (0,0,0,0), startColor=(0,0,0,1))
    cx, cy, cz = client.battleGraphics.terrain.getBounds().getCenter()
    i2 = LerpPosInterval(client.camhandler.container, 5, (cx,cy,cz), startPos=(cx,cy,cz+50))
    ch, cp, cr = client.camhandler.container.getHpr()
    i3 = LerpHprInterval(client.camhandler.container, 5, (ch+90, cp, cr), (ch-180, cp, cr))
    p1 = Parallel(i1,i2,i3)
    seq.append(p1)
    seq.append(Func(client.transitionframe.destroy))
    seq.append(Wait(1))
    seq.append(Func(client.updateAllSpritesAnimations, 'walk'))
    seq.append(Func(lambda: GUI.BrownOverlay(GUI.ConditionsForWinning, client.send.UPDATE_PARTY)))
    return seq

# Returns the sequence of a character punching another
def characterAttackSequence(client, charid, targetid):
    seq = Sequence()
    seq.append( Func(client.at.hide) )
    seq.append( Func(client.characterLookAt,       charid, targetid) )
    seq.append( Func(client.updateSpriteAnimation, charid, 'attack') )
    seq.append( Wait(0.5) )
    seq.append( Func(client.updateSpriteAnimation, targetid, 'hit') )
    seq.append( Func(client.attack_snd.play) )
    seq.append( Wait(0.5) )
    seq.append( Func(client.updateSpriteAnimation, charid) )
    seq.append( Wait(0.5) )
    seq.append( Func(client.updateSpriteAnimation, targetid) )
    seq.append( Wait(0.5) )
    seq.append( Func(client.matrix.clearZone) )
    return seq

# Returns a sequence showing the character moving through a path
def characterMoveSequence(client, charid, path):
    sprite = client.matrix.sprites[charid]
    seq = Sequence()
    origin = False
    for destination in path:
        if origin:

            (x1, y1, z1) = origin
            (x2, y2, z2) = destination

            # first, face the right direction
            if x2 > x1:
                d = 1
            elif x2 < x1:
                d = 3
            elif y2 > y1:
                d = 2
            elif y2 < y1:
                d = 4
            seq.append( Func(sprite.setRealDir, d) )

            # then, add the move animation from one tile to the next
            if z2 - z1 >= 4:
                middle = (
                    origin[0] + (destination[0] - origin[0]) / 2.0,
                    origin[1] + (destination[1] - origin[1]) / 2.0,
                    destination[2] + 0.5
                )
                seq.append(
                    Sequence(
                        Func(client.updateSpriteAnimation, charid, 'smalljump'),
                        LerpPosInterval(
                            sprite.node, 
                            0.125,
                            client.battleGraphics.logic2terrain(middle), 
                            startPos=client.battleGraphics.logic2terrain(origin)
                        ),
                        LerpPosInterval(
                            sprite.node, 
                            0.125,
                            client.battleGraphics.logic2terrain(destination), 
                            startPos=client.battleGraphics.logic2terrain(middle)
                        ),
                        Func(client.updateSpriteAnimation, charid, 'run'),
                    )
                )
            elif z1 - z2 >= 4:
                middle = (
                    origin[0] + (destination[0] - origin[0]) / 2.0,
                    origin[1] + (destination[1] - origin[1]) / 2.0,
                    origin[2] + 0.5
                )
                seq.append(
                    Sequence(
                        Func(client.updateSpriteAnimation, charid, 'smalljump'),
                        LerpPosInterval(
                            sprite.node, 
                            0.125,
                            client.battleGraphics.logic2terrain(middle), 
                            startPos=client.battleGraphics.logic2terrain(origin)
                        ),
                        LerpPosInterval(
                            sprite.node, 
                            0.125,
                            client.battleGraphics.logic2terrain(destination), 
                            startPos=client.battleGraphics.logic2terrain(middle)
                        ),
                        Func(client.updateSpriteAnimation, charid, 'run'),
                    )
                )
            else:
                seq.append(
                    LerpPosInterval(
                        sprite.node, 
                        0.25,
                        client.battleGraphics.logic2terrain(destination), 
                        startPos=client.battleGraphics.logic2terrain(origin)
                    )
                )
        origin = destination
    return seq
########NEW FILE########
__FILENAME__ = Sky
from panda3d.core import GeomVertexFormat, Geom, GeomVertexData, GeomVertexWriter, GeomTristrips, VBase4, GeomNode, NodePath

# Draw the gradient background representing the sky during a battle
class Sky(object):

    def __init__(self, mp):
        vdata = GeomVertexData('name_me', GeomVertexFormat.getV3c4(), Geom.UHStatic)
        vertex = GeomVertexWriter(vdata, 'vertex')
        color = GeomVertexWriter(vdata, 'color')
        primitive = GeomTristrips(Geom.UHStatic)
        film_size = base.cam.node().getLens().getFilmSize()
        x = film_size.getX() / 2.0
        z = x * 256.0/240.0
        vertex.addData3f( x, 90,  z)
        vertex.addData3f(-x, 90,  z)
        vertex.addData3f( x, 90, -z)
        vertex.addData3f(-x, 90, -z)
        color.addData4f(VBase4(*mp['backgroundcolor1']))
        color.addData4f(VBase4(*mp['backgroundcolor1']))
        color.addData4f(VBase4(*mp['backgroundcolor2']))
        color.addData4f(VBase4(*mp['backgroundcolor2']))
        primitive.addNextVertices(4)
        primitive.closePrimitive()
        geom = Geom(vdata)
        geom.addPrimitive(primitive)
        self.node = GeomNode('sky')
        self.node.addGeom(geom)
        base.camera.attachNewNode(self.node)

    def remove(self):
        NodePath(self.node).removeNode()
########NEW FILE########
__FILENAME__ = Sprite
from Config import *
from panda3d.core import NodePath, TransparencyAttrib
from pandac.PandaModules import Texture, TextureStage
import Sprite2d

class Sprite:

    def __init__(self, sheet, realdir=1):
    
        self.realdir    = realdir
        self.camdir     = 1
        self.displaydir = 1
        self.animation  = 'walk'
    
        self.sprite2d = Sprite2d.Sprite2d(sheet, cols=14, rows=4, scale=SPRITE_SCALE*0.7*256.0/240.0, anchorX='Center')

        # the main container
        self.node = NodePath("dummy1")
        
        # shadow
        self.shadow = loader.loadModel(GAME+'/models/slopes/flat')
        self.shadow.setZ(0.075)
        self.shadow.setScale(3.7)
        self.shadow.setTransparency(TransparencyAttrib.MAlpha)
        self.shadowtexture = loader.loadTexture(GAME+'/textures/shadow.png')
        self.shadowtexture.setMagfilter(Texture.FTNearest)
        self.shadowtexture.setMinfilter(Texture.FTNearest)
        self.shadowtexture.setWrapU(Texture.WMRepeat)
        self.shadowtexture.setWrapV(Texture.WMClamp)
        self.shadow.setTexture( self.shadowtexture )
        self.shadow.reparentTo( self.node )

        # the billboard container
        self.node2 = NodePath("dummy2")
        self.node2.setBillboardPointEye()
        self.node2.reparentTo( self.node )
        self.sprite2d.node.reparentTo( self.node2 )
        self.sprite2d.node.setPos( 0, -1.5, -1.5 )

        # animations
        self.sprite2d.createAnim('stand1', ( 0, 0), fps=10)
        self.sprite2d.createAnim('stand2', (14,14), fps=10)
        self.sprite2d.createAnim('stand3', (28,28), fps=10)
        self.sprite2d.createAnim('stand4', (42,42), fps=10)

        self.sprite2d.createAnim('smalljump1', ( 1, 1), fps=10)
        self.sprite2d.createAnim('smalljump2', (15,15), fps=10)
        self.sprite2d.createAnim('smalljump3', (29,29), fps=10)
        self.sprite2d.createAnim('smalljump4', (43,43), fps=10)

        self.sprite2d.createAnim('walk1', ( 1, 2, 3, 4, 5, 4, 3, 2), fps=10)
        self.sprite2d.createAnim('walk2', (15,16,17,18,19,18,17,16), fps=10)
        self.sprite2d.createAnim('walk3', (29,30,31,32,33,32,31,30), fps=10)
        self.sprite2d.createAnim('walk4', (43,44,45,46,47,46,45,44), fps=10)

        self.sprite2d.createAnim('run1', ( 1, 2, 3, 4, 5, 4, 3, 2), fps=15)
        self.sprite2d.createAnim('run2', (15,16,17,18,19,18,17,16), fps=15)
        self.sprite2d.createAnim('run3', (29,30,31,32,33,32,31,30), fps=15)
        self.sprite2d.createAnim('run4', (43,44,45,46,47,46,45,44), fps=15)
        
        self.sprite2d.createAnim('hit1', ( 6, 6), fps=10)
        self.sprite2d.createAnim('hit2', (20,20), fps=10)
        self.sprite2d.createAnim('hit3', (34,34), fps=10)
        self.sprite2d.createAnim('hit4', (48,48), fps=10)
        
        self.sprite2d.createAnim('weak1', ( 7, 7), fps=10)
        self.sprite2d.createAnim('weak2', (21,21), fps=10)
        self.sprite2d.createAnim('weak3', (35,35), fps=10)
        self.sprite2d.createAnim('weak4', (49,49), fps=10)
        
        self.sprite2d.createAnim('dead1', ( 8, 8), fps=10)
        self.sprite2d.createAnim('dead2', (22,22), fps=10)
        self.sprite2d.createAnim('dead3', (36,36), fps=10)
        self.sprite2d.createAnim('dead4', (50,50), fps=10)
        
        self.sprite2d.createAnim('attack1', ( 9,10, 9,13,11,12,11,13), fps=8)
        self.sprite2d.createAnim('attack2', (23,24,23,27,25,26,25,27), fps=8)
        self.sprite2d.createAnim('attack3', (37,38,37,41,39,40,39,41), fps=8)
        self.sprite2d.createAnim('attack4', (51,52,51,55,53,54,53,55), fps=8)

    def setRealDir(self, direction):
        self.realdir = int(direction)

    def updateDisplayDir(self, h, force=False):
        h = self.normalizeH(h)
        if h >=    0 and h <  90:
            self.camdir = 2
        if h >=  -90 and h <   0:
            self.camdir = 3
        if h >= -180 and h < -90:
            self.camdir = 4
        if h >=   90 and h < 180:
            self.camdir = 1
        
        tmpdir = self.realdir + self.camdir
        if tmpdir > 4:
            tmpdir -= 4
        if tmpdir != self.displaydir or force:
            self.sprite2d.playAnim( self.animation+str(tmpdir), loop=True)
            self.displaydir = tmpdir

    def normalizeH(self, h):
        while h > 180:
            h -= 360
        while h < -180:
            h += 360
        return h


########NEW FILE########
__FILENAME__ = Sprite2d
from pandac.PandaModules import NodePath, PNMImageHeader, PNMImage, Filename, CardMaker, TextureStage, Texture, TransparencyAttrib
from math import log, modf

class Sprite2d:

    class Cell:
        def __init__(self, col, row):
            self.col = col
            self.row = row
       
        def __str__(self):
            return "Cell - Col %d, Row %d" % (self.col, self.row)
       
    class Animation:
        def __init__(self, cells, fps):
            self.cells = cells
            self.fps = fps
            self.playhead = 0

    ALIGN_CENTER = "Center"
    ALIGN_LEFT = "Left"
    ALIGN_RIGHT = "Right"
    ALIGN_BOTTOM = "Bottom"
    ALIGN_TOP = "Top"
   
    TRANS_ALPHA = TransparencyAttrib.MAlpha
    TRANS_DUAL = TransparencyAttrib.MDual
    # One pixel is divided by this much. If you load a 100x50 image with PIXEL_SCALE of 10.0
    # you get a card that is 1 unit wide, 0.5 units high
    PIXEL_SCALE = 10.0

    def __init__(self, image_path, name=None,\
                  rows=1, cols=1, scale=1.0,\
                  twoSided=True, alpha=TRANS_ALPHA,\
                  repeatX=1, repeatY=1,\
                  anchorX=ALIGN_LEFT, anchorY=ALIGN_BOTTOM):
        """
        Create a card textured with an image. The card is sized so that the ratio between the
        card and image is the same.
        """
       
        scale *= self.PIXEL_SCALE
       
        self.animations = {}
       
        self.scale = scale
        self.repeatX = repeatX
        self.repeatY = repeatY
        self.flip = {'x':False,'y':False}
        self.rows = rows
        self.cols = cols
       
        self.currentFrame = 0
        self.currentAnim = None
        self.loopAnim = False
        self.frameInterrupt = True
       
        # Create the NodePath
        if name:
            self.node = NodePath("Sprite2d:%s" % name)
        else:
            self.node = NodePath("Sprite2d:%s" % image_path)
       
        # Set the attribute for transparency/twosided
        self.node.node().setAttrib(TransparencyAttrib.make(alpha))
        if twoSided:
            self.node.setTwoSided(True)
       
        # Make a filepath
        self.imgFile = Filename(image_path)
        if self.imgFile.empty():
            raise IOError, "File not found"
       
        # Instead of loading it outright, check with the PNMImageHeader if we can open
        # the file.
        imgHead = PNMImageHeader()
        if not imgHead.readHeader(self.imgFile):
            raise IOError, "PNMImageHeader could not read file. Try using absolute filepaths"
       
        # Load the image with a PNMImage
        image = PNMImage()
        image.read(self.imgFile)
       
        self.sizeX = image.getXSize()
        self.sizeY = image.getYSize()
       
        self.frames = []
        for rowIdx in xrange(self.rows):
            for colIdx in xrange(self.cols):
                self.frames.append(Sprite2d.Cell(colIdx, rowIdx))
       
        # We need to find the power of two size for the another PNMImage
        # so that the texture thats loaded on the geometry won't have artifacts
        textureSizeX = self.nextsize(self.sizeX)
        textureSizeY = self.nextsize(self.sizeY)
       
        # The actual size of the texture in memory
        self.realSizeX = textureSizeX
        self.realSizeY = textureSizeY
       
        self.paddedImg = PNMImage(textureSizeX, textureSizeY)
        if image.hasAlpha():
            self.paddedImg.alphaFill(0)
        # Copy the source image to the image we're actually using
        self.paddedImg.blendSubImage(image, 0, 0)
        # We're done with source image, clear it
        image.clear()
       
        # The pixel sizes for each cell
        self.colSize = self.sizeX/self.cols
        self.rowSize = self.sizeY/self.rows
       
        # How much padding the texture has
        self.paddingX = textureSizeX - self.sizeX
        self.paddingY = textureSizeY - self.sizeY
       
        # Set UV padding
        self.uPad = float(self.paddingX)/textureSizeX
        self.vPad = float(self.paddingY)/textureSizeY
       
        # The UV dimensions for each cell
        self.uSize = (1.0 - self.uPad) / self.cols
        self.vSize = (1.0 - self.vPad) / self.rows
       
        card = CardMaker("Sprite2d-Geom")

        # The positions to create the card at
        if anchorX == self.ALIGN_LEFT:
            posLeft = 0
            posRight = (self.colSize/scale)*repeatX
        elif anchorX == self.ALIGN_CENTER:
            posLeft = -(self.colSize/2.0/scale)*repeatX
            posRight = (self.colSize/2.0/scale)*repeatX
        elif anchorX == self.ALIGN_RIGHT:
            posLeft = -(self.colSize/scale)*repeatX
            posRight = 0
       
        if anchorY == self.ALIGN_BOTTOM:
            posTop = 0
            posBottom = (self.rowSize/scale)*repeatY
        elif anchorY == self.ALIGN_CENTER:
            posTop = -(self.rowSize/2.0/scale)*repeatY
            posBottom = (self.rowSize/2.0/scale)*repeatY
        elif anchorY == self.ALIGN_TOP:
            posTop = -(self.rowSize/scale)*repeatY
            posBottom = 0
       
        card.setFrame(posLeft, posRight, posTop, posBottom)
        card.setHasUvs(True)
        self.card = self.node.attachNewNode(card.generate())
       
        # Since the texture is padded, we need to set up offsets and scales to make
        # the texture fit the whole card
        self.offsetX = (float(self.colSize)/textureSizeX)
        self.offsetY = (float(self.rowSize)/textureSizeY)
       
        self.node.setTexScale(TextureStage.getDefault(), self.offsetX * repeatX, self.offsetY * repeatY)
        self.node.setTexOffset(TextureStage.getDefault(), 0, 1-self.offsetY)
       
        self.texture = Texture()
       
        self.texture.setXSize(textureSizeX)
        self.texture.setYSize(textureSizeY)
        self.texture.setZSize(1)
       
        # Load the padded PNMImage to the texture
        self.texture.load(self.paddedImg)

        self.texture.setMagfilter(Texture.FTNearest)
        self.texture.setMinfilter(Texture.FTNearest)
       
        #Set up texture clamps according to repeats
        if repeatX > 1:
            self.texture.setWrapU(Texture.WMRepeat)
        else:
            self.texture.setWrapU(Texture.WMClamp)
        if repeatY > 1:
            self.texture.setWrapV(Texture.WMRepeat)
        else:
            self.texture.setWrapV(Texture.WMClamp)
       
        self.node.setTexture(self.texture)
    
    def nextsize(self, num):
        """ Finds the next power of two size for the given integer. """
        p2x=max(1,log(num,2))
        notP2X=modf(p2x)[0]>0
        return 2**int(notP2X+p2x)
   
    def setFrame(self, frame=0):
        """ Sets the current sprite to the given frame """
        self.frameInterrupt = True # A flag to tell the animation task to shut it up ur face
        self.currentFrame = frame
        self.flipTexture()
   
    def playAnim(self, animName, loop=False):
        """ Sets the sprite to animate the given named animation. Booleon to loop animation"""
        if hasattr(self, "task"):
            #if not self.task.isRemoved():
            taskMgr.remove(self.task)
        self.frameInterrupt = False # Clear any previous interrupt flags
        self.loopAnim = loop
        self.currentAnim = self.animations[animName]
        self.currentAnim.playhead = 0
        self.task = taskMgr.doMethodLater(1.0/self.currentAnim.fps,self.animPlayer, "Animate sprite")
   
    def createAnim(self, animName, frames, fps=12):
        """ Create a named animation. Takes the animation name and a tuple of frame numbers """
        self.animations[animName] = Sprite2d.Animation(frames, fps)
        return self.animations[animName]
   
    def flipX(self, val=None):
        """ Flip the sprite on X. If no value given, it will invert the current flipping."""
        if val:
            self.flip['x'] = val
        else:
            if self.flip['x']:
                self.flip['x'] = False
            else:
                self.flip['x'] = True
        self.flipTexture()
        return self.flip['x']
       
    def flipY(self, val=None):
        """ See flipX """
        if val:
            self.flip['y'] = val
        else:
            if self.flip['y']:
                self.flip['y'] = False
            else:
                self.flip['y'] = True
        self.flipTexture()
        return self.flip['y']

    def flipTexture(self):
        """ Sets the texture coordinates of the texture to the current frame"""
        sU = self.offsetX * self.repeatX
        sV = self.offsetY * self.repeatY
        oU = 0 + self.frames[self.currentFrame].col * self.uSize
        oV = 1 - self.frames[self.currentFrame].row * self.vSize - self.offsetY
        if self.flip['x']:
            sU *= -1
            oU = self.uSize + self.frames[self.currentFrame].col * self.uSize
        if self.flip['y']:
            sV *= -1
            oV = 1 - self.frames[self.currentFrame].row * self.vSize
        self.node.setTexScale(TextureStage.getDefault(), sU, sV)
        self.node.setTexOffset(TextureStage.getDefault(), oU, oV)
   
    def clear(self):
        """ Free up the texture memory being used """
        self.texture.clear()
        self.paddedImg.clear()
        self.node.removeNode()
   
    def animPlayer(self, task):
        if self.frameInterrupt:
            return task.done
        #print "Playing",self.currentAnim.cells[self.currentAnim.playhead]
        self.currentFrame = self.currentAnim.cells[self.currentAnim.playhead]
        self.flipTexture()
        if self.currentAnim.playhead+1 < len(self.currentAnim.cells):
            self.currentAnim.playhead += 1
            return task.again
        if self.loopAnim:
            self.currentAnim.playhead = 0
            return task.again

########NEW FILE########
__FILENAME__ = Tests
from direct.showbase.DirectObject import DirectObject
import direct.directbase.DirectStart
import json, sys, getopt, inspect, os, imp
# Tethical's Drawing-Related Features
from BattleGraphics import *
from Matrix import *
from Cursor import *
import SequenceBuilder
# Tethical's Key Handling Feature
import CameraHandler

class UsageError(Exception):
	def __init__(self, msg):
		self.msg = msg

#
try:
    argv
except NameError:
    argv = None
#
if argv is None:
	argv = sys.argv
try:
	try:
		opts, args = getopt.getopt(argv[1:], "h", ["help"])
	except getopt.error, msg:
		raise UsageError(msg)
except UsageError, err:
	print >>sys.stderr, err.msg
# Running: 
#
#	python C:\Tethical\master\client\Tests.py 
#		map-event-test 
#		C:\Tethical\master 
#		lijj 
#		custom006.json 
#		C:\Tethical\master\client\lijj\events\custom006\animate_water.py
if len(argv[1:]) > 0:
	# Required argument matching.
	command = argv[1]	
	BASEPATH = argv[2] # 'C:\Tethical\master'
	GAME = argv[3] # 'lijj', 'fft'
	# Global game directories available.
	SERVERGAME = os.path.join(BASEPATH, 'server', GAME)	
	# Map Event Test (map-event-test) launches a map and manually runs a script.
	if command == 'map-event-test':
		# Event argument usage.
		MAP = argv[4] # 'custom006.json'
		EVENT = argv[5] # 'C:\Tethical\master\client\lijj\events\custom006\animate_water.py'
		# Get directory of map description files (JSON).
		MAPS = os.path.join(SERVERGAME, 'maps', MAP)
		# Get map description file (JSON); ..\server\Map.py:9
		f = open(MAPS, 'r')
		mapJSON = json.loads(f.read())
		f.close()
		# Parse map description file in place of the JSON response the server sends; ..\server\Map.py:13
		tiles = [ [ [ None for z in range(mapJSON['z']) ] for y in range(mapJSON['y']) ] for x in range(mapJSON['x']) ]
		for t in mapJSON['tiles']:
			tiles[int(t['x'])][int(t['y'])][int(t['z'])] = t
		# Add extra information back to the map description file in memory; ..\server\Map.py:17
		mapJSON['tiles'] = tiles
		battleGraphics = None
		try:
			# Instanciate the battle graphics
			battleGraphics = BattleGraphics(mapJSON, GAME)			
			# Display the terrain (map model is actually loaded here).
			battleGraphics.displayTerrain()			
		except IOError:
			# Map couldn't be found.
			battleGraphics = None
			pass
		# If the map was loaded successfully, finish setting everything up and run the event.
		if not battleGraphics is None:
			# Light the scene
			battleGraphics.lightScene()
			# Bind camera controls to keys.
			camhandler = CameraHandler.CameraHandler()
			camhandler.accept('escape', lambda: sys.exit());
			# Play the background music
			music = base.loader.loadSfx(GAME+'/music/'+mapJSON['music']+'.ogg')
			music.setLoop(True)
			music.play()
			# Place highlightable tiles on the map
			matrix = Matrix(battleGraphics, mapJSON)
			# Cursor stuff
			cursor = Cursor(battleGraphics, matrix.container)
			# Add the special effects
			battleGraphics.addEffects()
			try:
				# Load event.
				imp.load_source('event', EVENT)
				#
				print ""
				print ""
				print "Controls: "
				print ""
				print "  G:	Rotate Map Left"
				print "  F:	Rotate Map Right"
				print "  H:	Ascend/Descend"
				print "  D:	Zoom In/Zoom Out"
				print "  ESC:	End Test"
			except:
				print 'Event could not be found at '+str(EVENT)
		pass
	pass
#
run()
########NEW FILE########
__FILENAME__ = test_bars
from Config import *
import direct.directbase.DirectStart
from direct.gui.OnscreenText import OnscreenText 
from direct.gui.DirectGui import *
from pandac.PandaModules import *
from direct.interval.IntervalGlobal import *
import GUI
import os
import os.path
from operator import itemgetter, attrgetter

# GUI.Blueprint('menu1')

# char = {
#     'sprite': '4A_F_1',
#     'lv': 15,
#     'exp': 20,
#     'hp': 205,
#     'hpmax': 245,
#     'mp': 30,
#     'mpmax': 30,
#     'ct': 20
# }
# GUI.CharBarsLeft(char)

# GUI.Blueprint('charbarsright')

# char = {
#     'sprite': '4A_F_0',
#     'lv': 15,
#     'exp': 0,
#     'hp': 225,
#     'hpmax': 225,
#     'mp': 32,
#     'mpmax': 36,
#     'ct': 50
# }
# GUI.CharBarsRight(char)

# GUI.Blueprint('formation0')

# def foo():
# 	pass

# chars = [
# {
# 	'name': 'Kivu',
# 	'job': 'Kivu',
# 	'team': 1,
# 	'sign': 1,
#     'sprite': '4A_F_0',
#     'lv': 15,
#     'exp': 0,
#     'hp': 225,
#     'hpmax': 225,
#     'mp': 32,
#     'mpmax': 36,
#     'ct': 50,
#     'br': 12,
#     'fa': 13,
# },
# {
# 	'name': 'Kivy',
# 	'job': 'Kivy',
# 	'team': 1,
# 	'sign': 1,
#     'sprite': '4A_F_0',
#     'lv': 15,
#     'exp': 0,
#     'hp': 225,
#     'hpmax': 225,
#     'mp': 32,
#     'mpmax': 36,
#     'ct': 50,
#     'br': 12,
#     'fa': 13,
# },
# ]

# tileset = {
#     "capacity": 4,
#     "direction": 2,
#     "maping": [
#         [ None   , None   , None   , None   , None    ],
#         [ None   , None   , None   , None   , None    ],
#         [ None   , [3,0,4], [4,0,4], [5,0,4], [6,0,4] ],
#         [ None   , None   , None   , None   , None    ],
#         [ None   , None   , None   , None   , None    ]
#     ]
# }

# GUI.Formation(render, tileset, chars, foo)

GUI.Blueprint('actionpreview')

char1 = {
	'name': 'Kivu',
	'job': 'Kivu',
	'team': 1,
	'sign': 1,
    'sprite': '4A_F_0',
    'lv': 15,
    'exp': 0,
    'hp': 225,
    'hpmax': 225,
    'mp': 32,
    'mpmax': 36,
    'ct': 50,
    'br': 12,
    'fa': 13,
}

char2 = {
	'name': 'Kivy',
	'job': 'Kivy',
	'team': 1,
	'sign': 1,
    'sprite': '4A_F_0',
    'lv': 15,
    'exp': 0,
    'hp': 225,
    'hpmax': 225,
    'mp': 32,
    'mpmax': 36,
    'ct': 50,
    'br': 12,
    'fa': 13,
}

def foo():
	pass

GUI.ActionPreview(char1, char2, 25, 96, foo, foo)

run()

########NEW FILE########
__FILENAME__ = test_effects
from Config import *
import direct.directbase.DirectStart
from direct.gui.OnscreenText import OnscreenText
from pandac.PandaModules import PandaNode,NodePath,Camera,TextNode,GeomTristrips,Geom,GeomVertexFormat,GeomVertexData,GeomVertexWriter,GeomNode,TransformState,OrthographicLens,TextureStage,TexGenAttrib,PNMImage,Texture,ColorBlendAttrib
from panda3d.core import *
from direct.gui.DirectGui import *
from direct.interval.IntervalGlobal import *
from direct.task import Task
import Effect
import Sprite
from CameraHandler import CameraHandler

camhandler = CameraHandler()

terrain = render.attachNewNode('terrain')

tile1 = loader.loadModel(GAME+"/models/slopes/flat" )
tile1.setScale(3.0)
tile1.reparentTo(terrain)
tile1.setColor(0, 0, 1, 1)
tile1.setPos(9, 0, 0)
sprite1 = Sprite.Sprite(GAME+'/textures/sprites/4C_F_1.png', 3)
sprite1.node.reparentTo(terrain)
sprite1.node.setPos(9, 0, 0)

tile2 = loader.loadModel(GAME+"/models/slopes/flat" )
tile2.setScale(3.0)
tile2.reparentTo(terrain)
tile2.setColor(0, 0, 1, 1)
tile2.setPos(-9, 0, 0)
sprite2 = Sprite.Sprite(GAME+'/textures/sprites/4C_F_1.png', 1)
sprite2.node.reparentTo(terrain)
sprite2.node.setPos(-9, 0, 0)

def rotationTask(task):
    h = task.time * 30
    camhandler.container.setHpr(h,0,0)
    return Task.cont

def characterDirectionTask(task):
    h = camhandler.container.getH()
    sprite1.updateDisplayDir(h)
    sprite2.updateDisplayDir(h)
    return Task.cont

def updateSpriteAnimation(sprite, animation):
    sprite.animation = animation
    h = camhandler.container.getH()
    sprite.updateDisplayDir( h, True )

taskMgr.add(rotationTask, 'rotationTask')
taskMgr.add(characterDirectionTask, 'characterDirectionTask')

Sequence(
    Func(updateSpriteAnimation, sprite1, 'attack'),
    Func(updateSpriteAnimation, sprite2, 'hit'),
    #Effect.Effect('cure.fft-E001.bmp', sprite2.node, True).getSequence(),
    Effect.Effect('ice.fft-E024.bmp', sprite2.node, True, False, [0,0,-2]).getSequence(),
    #Effect.Effect('bizen-boat.fft-E135.bmp', sprite2.node, True).getSequence(),
    #Effect.Effect('death.fft-E030-color.bmp', sprite2.node, True).getSequence(),
    #Effect.Effect('dark-blade.fft-E172.bmp', sprite2.node, True, True, [0,0,3]).getSequence(),
    #Effect.Effect('dark-blade.fft-E172-color.bmp', sprite2.node, True, True, [0,0,3]).getSequence(),
    Func(updateSpriteAnimation, sprite2, 'attack'),
    Func(updateSpriteAnimation, sprite1, 'hit'),
    Effect.Effect('cure.fft-E001.bmp', sprite1.node, True).getSequence()
    #Effect.Effect('night-sword.fft-E173.bmp', sprite1.node, True, False, [0,0,-2]).getSequence()
    #Effect.Effect('cure-it-with-fire.fft-E001.png', sprite1.node, True).getSequence()
    #Effect.Effect('ice.fft-E024.bmp', sprite1.node, True, False, [0,0,-2]).getSequence()
).loop()

run()
########NEW FILE########
__FILENAME__ = test_menu
from Config import *
import direct.directbase.DirectStart
from direct.gui.OnscreenText import OnscreenText 
from direct.gui.DirectGui import *
from pandac.PandaModules import *
import GUI

def exemplecallback(text):
    print "You clicked the row #"+str(text)

def cancelcallback():
    print "Bye"

GUI.Blueprint('menu0')

columns = [
    { 'name': "abilityName", 'label': "Ability", 'x': -93, 'font': GUI.regularfont, 'align': TextNode.ALeft   },
    { 'name': "mpCost",      'label': "MP",      'x':   4, 'font': GUI.regularfont, 'align': TextNode.ALeft   },
    { 'name': "speed",       'label': "Speed",   'x':  35, 'font': GUI.regularfont, 'align': TextNode.ALeft   },
    { 'name': "jpCost",      'label': "JP",      'x':  78, 'font': GUI.regularfont, 'align': TextNode.ACenter },
]

rows = [
    { 'cells': ['Aim',      '00', '50', 'Learned', ], 'enabled': True , 'callback': exemplecallback, },
    { 'cells': ['Blackout', '00', '25', 'Learned', ], 'enabled': True , 'callback': exemplecallback, },
    { 'cells': ['Wait',     '00', '25', 'Learned', ], 'enabled': True , 'callback': exemplecallback, },
    { 'cells': ['Status',   '00', '25', 'Learned', ], 'enabled': False, 'callback': exemplecallback, },
    { 'cells': ['Blackout', '00', '00', 'Learned', ], 'enabled': True , 'callback': exemplecallback, },
    { 'cells': ['Test1',    '00', '34', 'Learned', ], 'enabled': True , 'callback': exemplecallback, },
    { 'cells': ['Test2',    '00', '17', 'Learned', ], 'enabled': False, 'callback': exemplecallback, },
    { 'cells': ['Test3',    '00', '15', 'Learned', ], 'enabled': False, 'callback': exemplecallback, },
    { 'cells': ['Test4',    '00', '25', 'Learned', ], 'enabled': False, 'callback': exemplecallback, },
    { 'cells': ['Test5',    '00', '00', 'Learned', ], 'enabled': True , 'callback': exemplecallback, },
    { 'cells': ['Test6',    '00', '30', 'Learned', ], 'enabled': True , 'callback': exemplecallback, },
    { 'cells': ['Aim',      '00', '50', 'Learned', ], 'enabled': True , 'callback': exemplecallback, },
    { 'cells': ['Blackout', '00', '25', 'Learned', ], 'enabled': True , 'callback': exemplecallback, },
    { 'cells': ['Wait',     '00', '25', 'Learned', ], 'enabled': True , 'callback': exemplecallback, },
    { 'cells': ['Status',   '00', '25', 'Learned', ], 'enabled': False, 'callback': exemplecallback, },
]

GUI.ScrollableList('list', 3.0, 31.0, 206.0, 148.0, 23, columns, rows, 8, cancelcallback)

# GUI.Blueprint('menu1')

# columns = [
#     { 'name': "menu", 'label': "Menu", 'x': -25, 'font': GUI.regularfont, 'align': TextNode.ALeft   },
# ]

# rows = [
#     { 'cells': ['Status',      ], 'enabled': True , 'callback': exemplecallback, },
#     { 'cells': ['Auto-Battle', ], 'enabled': True , 'callback': exemplecallback, },
# ]

# GUI.ScrollableList('shadowed', 73, -32, 62.0, 43.0, 16, columns, rows, 2, cancelcallback, 'Menu')

# GUI.Blueprint('menu2')

# columns = [
#     { 'name': "menu", 'label': "Menu", 'x': -44, 'font': GUI.regularfont, 'align': TextNode.ALeft   },
# ]

# rows = [
#     { 'cells': ['Sleep Blade',   ], 'enabled': True , 'callback': exemplecallback, },
#     { 'cells': ['Coral Sword',   ], 'enabled': True , 'callback': exemplecallback, },
#     { 'cells': ['Mythril Sword', ], 'enabled': True , 'callback': exemplecallback, },
#     { 'cells': ['Iron Sword',    ], 'enabled': True , 'callback': exemplecallback, },
#     { 'cells': ['Auto-Battle',   ], 'enabled': True , 'callback': exemplecallback, },
#     { 'cells': ['Sleep Blade',   ], 'enabled': True , 'callback': exemplecallback, },
#     { 'cells': ['Coral Sword',   ], 'enabled': True , 'callback': exemplecallback, },
#     { 'cells': ['Mythril Sword', ], 'enabled': True , 'callback': exemplecallback, },
#     { 'cells': ['Iron Sword',    ], 'enabled': True , 'callback': exemplecallback, },
#     { 'cells': ['Auto-Battle',   ], 'enabled': True , 'callback': exemplecallback, },
#     { 'cells': ['Sleep Blade',   ], 'enabled': True , 'callback': exemplecallback, },
#     { 'cells': ['Coral Sword',   ], 'enabled': True , 'callback': exemplecallback, },
#     { 'cells': ['Mythril Sword', ], 'enabled': True , 'callback': exemplecallback, },
#     { 'cells': ['Iron Sword',    ], 'enabled': True , 'callback': exemplecallback, },
#     { 'cells': ['Auto-Battle',   ], 'enabled': True , 'callback': exemplecallback, },
# ]

# GUI.ScrollableList('list', -31, 35, 170.0, 148.0, 23, columns, rows, 8, cancelcallback)

run()

########NEW FILE########
__FILENAME__ = WindowNodeDrawer
import direct.directbase.DirectStart
from direct.gui.DirectGui import *
from pandac.PandaModules import *
from Config import *

v = 1.0/120.0
scale = 2*12.0/240.0
whitefont = loader.loadFont(GAME+'/fonts/fftwhite')

def WindowNodeDrawer(w, h, style, title=None):

    # 0 1 2
    # 3 4 5
    # 6 7 8
    w = float(w)
    h = float(h)

    container = NodePath('foo')

    frames = (
        ( -v*(w/2   ), -v*(w/2-16),  v*(h/2-16),  v*(h/2   ) ),
        ( -v*(w/2-16),  v*(w/2-16),  v*(h/2-16),  v*(h/2   ) ),
        (  v*(w/2-16),  v*(w/2   ),  v*(h/2-16),  v*(h/2   ) ),
        ( -v*(w/2   ), -v*(w/2-16),  v*(h/2-16), -v*(h/2-16) ),
        ( -v*(w/2- 2),  v*(w/2- 2), -v*(h/2- 2),  v*(h/2- 2) ), # 4
        (  v*(w/2-16),  v*(w/2   ),  v*(h/2-16), -v*(h/2-16) ),
        ( -v*(w/2   ), -v*(w/2-16), -v*(h/2   ), -v*(h/2-16) ),
        ( -v*(w/2-16),  v*(w/2-16), -v*(h/2   ), -v*(h/2-16) ),
        (  v*(w/2-16),  v*(w/2   ), -v*(h/2   ), -v*(h/2-16) ),
    )

    for i in (4,0,1,2,3,5,6,7,8):

        path = GAME+'/textures/gui/'+THEME+'/'+style+'/'+str(i)+'.png'

        tex = loader.loadTexture(path)
        tex.setMagfilter(Texture.FTNearest)
        tex.setMinfilter(Texture.FTNearest)
        tex.setWrapU(Texture.WMRepeat)
        tex.setWrapV(Texture.WMRepeat)

        cm = CardMaker('card')
        cm.setFrame(frames[i])
        if i == 4:
            cm.setUvRange((0,0), (w/tex.getOrigFileXSize(), h/tex.getOrigFileYSize()))

        card = container.attachNewNode(cm.generate())
        card.setTexture(tex)
        if w%2:
            card.setX(-v*.5)
        if h%2:
            card.setZ( v*.5)

    if title:

        titleLabel = DirectLabel(
            color = (0,0,0,0),
            text = title,
            scale = scale,
            text_font = whitefont,
            text_fg = (1,1,1,1),
            text_align = TextNode.ALeft,
            parent = container,
            pos = (-v*(w/2-2), 0, v*(h/2-6))
        )

    return container
########NEW FILE########
__FILENAME__ = Attack
import math
import Character

def GetAttackables ( party, charid ):

    x1, y1, z1 = Character.Coords( party, charid )
    
    attackables = []
    for x2, y2 in ( (x1-1, y1), (x1+1, y1), (x1, y1-1), (x1, y1+1) ):

        try:
            t2 = party['map']['tiles'][x2][y2]
            if t2 and x2 >= 0 and y2 >= 0:
                for z2,t3 in enumerate(t2):
                    if t3 and t3['walkable'] and t3['selectable'] and math.fabs(z2-z1) <= 4:
                        attackables.append( (x2, y2, z2) )
        except:
            pass

    return attackables

def IsAttackable( party, charid1, charid2 ):
    
    return Character.Coords( party, charid2 ) in GetAttackables( party, charid1 )


########NEW FILE########
__FILENAME__ = Character
from panda3d.core import loadPrcFile
loadPrcFile("config.prc")
from pandac.PandaModules import *
import json, random, os

GAME = ConfigVariableString('game', 'fft').getValue()

jobs = {}
jobids = map( lambda m: m.split('.')[0], os.listdir(GAME+'/jobs'))
for jobid in jobids:
    f = open(GAME+'/jobs/'+jobid+'.json', 'r')
    jobs[jobid] = json.loads(f.read())
    f.close()

def Coords( party, charid ):
    
    for x in range( party['map']['x'] ):
        for y in range( party['map']['y'] ):
            for z in range( party['map']['z'] ):
                
                tile = party['map']['tiles'][x][y][z]
                
                if tile and tile.has_key('char') and int(tile['char']) == int(charid):
                    return (x, y, z)

def Random( charid, teamid=0, direction=0 ):
    jobid = jobids[random.randint(0, len(jobids)-1)]
    job = jobs[jobid]
    gender = ('F','M')[random.randint(0, 1)]
    sprite = str(jobid)+'_'+str(gender)+'_'+str(teamid)

    if gender == 'F':
        rhp = random.randint(458752, 491519)
        rmp = random.randint(245760, 262143)
        rsp = 98304
        rpa = 65536
        rma = 81920
    elif gender == 'M':
        rhp = random.randint(491520, 524287)
        rmp = random.randint(229376, 245759)
        rsp = 98304
        rpa = 81920
        rma = 65536

    hp = rhp * job['hpm'] / 1638400
    mp = rmp * job['mpm'] / 1638400
    sp = rsp * job['spm'] / 1638400
    pa = rpa * job['pam'] / 1638400
    ma = rma * job['mam'] / 1638400

    lv = random.randint(10, 15)
    for l in range(1, lv+1):
        hp = hp + ( hp / (job['hpc'] + l) )
        mp = mp + ( mp / (job['mpc'] + l) )
        sp = sp + ( sp / (job['spc'] + l) )
        pa = pa + ( pa / (job['pac'] + l) )
        ma = ma + ( ma / (job['mac'] + l) )

    return {  'id': charid
           , 'name': GetRandomName(gender)
           , 'job': job['name']
           , 'sign': 1
           , 'br': random.randint(45, 74)
           , 'fa': random.randint(45, 74)
           , 'hp': hp
           , 'hpmax': hp
           , 'mp': mp
           , 'mpmax': mp
           , 'speed': sp
           , 'pa': pa
           , 'ma': ma
           , 'ct': random.randint(0, 100)
           , 'lv': lv
           , 'exp': random.randint(0, 99)
           , 'team': teamid
           , 'move': job['move']
           , 'jump': job['jump']*2
           , 'direction': direction
           , 'sprite': sprite
           , 'gender': gender
           , 'active': 0
           }

def GetRandomName( gender ):
    f = open(GAME+'/'+gender+'_names.txt', 'r')
    names = f.readlines()
    f.close()
    
    i = random.randint(0, len(names)-1)
    
    return names[i]


########NEW FILE########
__FILENAME__ = ATTACK
import Attack

# A unit is attacking another
def execute(server, iterator, source):
    charid1 = iterator.getString()
    charid2 = iterator.getString()
    party = server.parties[server.sessions[source]['party']]
    char1 = party['chars'][charid1]
    char2 = party['chars'][charid2]
    
    damages = char1['pa'] * char1['br'] / 100 * char1['pa']
    
    char2['hp'] = char2['hp'] - damages*4
    if char2['hp'] < 0:
        char2['hp'] = 0
    
    char1['canact'] = False
    
    server.send.ATTACK_SUCCESS(charid1, charid2, damages, source)
    
    attackables = Attack.GetAttackables( party, charid1 )
    
    for playerid,playerlogin in enumerate(party['players']):
        if playerid != server.sessions[source]['player']:
            server.send.ATTACK_PASSIVE(charid1, charid2, damages, attackables, server.players[playerlogin])
########NEW FILE########
__FILENAME__ = CREATE_PARTY
import Map

# A player tries to create a party.
def execute(server, iterator, source):
    name = iterator.getString()
    mapname = iterator.getString()
    
    party = {
        'name': name,
        'mapname': mapname,
        'map' : Map.load(mapname),
        'chars': {},
        'log': {},
        'creator': server.sessions[source]['login'],
        'players': [],
        'formations': [],
    }
    party['players'].append(server.sessions[source]['login'])

    server.parties[name] = party
    server.sessions[source]['party'] = name
    server.sessions[source]['player'] = len(party['players'])-1
    
    server.updateAllPartyLists()
    
    print server.sessions[source]['login'], "created the party", name, "using the map", mapname
    server.send.PARTY_CREATED(party, source)
########NEW FILE########
__FILENAME__ = FORMATION_READY
import json

# A team is complete. See if all teams are complete, and if so, start the battle
def execute(server, iterator, source):
    formation = json.loads(iterator.getString())

    party = server.parties[server.sessions[source]['party']]
    party['formations'].append(formation)

    if len(party['formations']) == len(party['map']['tilesets']):

        for team,formation in enumerate(party['formations']):
            for line in formation:
                x, y, z = line['coords']
                charid = line['charid']
                party['map']['tiles'][x][y][z]['char'] = str(charid)
                char = filter(lambda x: x['id'] == charid, server.chars)[0]
                char['team'] = team
                char['direction'] = line['direction']
                party['chars'][str(charid)] = char

        for playerlogin in party['players']:
            server.send.START_BATTLE(party, server.players[playerlogin])
########NEW FILE########
__FILENAME__ = GET_ATTACKABLES
import Attack

# Return the list of tiles that a unit can attack
def execute(server, iterator, source):
    charid = iterator.getString()
    
    party = server.parties[server.sessions[source]['party']]
    
    attackables = Attack.GetAttackables( party, charid )

    server.send.ATTACKABLES_LIST(charid, attackables, source)
########NEW FILE########
__FILENAME__ = GET_MAPS
from panda3d.core import loadPrcFile
loadPrcFile("config.prc")
from pandac.PandaModules import ConfigVariableString
import os
import Map
GAME = ConfigVariableString('game', 'fft').getValue()

# Return map list to a client
def execute(server, iterator, source):
    server.playersinlobby.remove(source)

    mapnames = map( lambda m: m.split('.')[0], os.listdir(GAME+'/maps'))

    maps = []
    for mapname in mapnames:
        mp = Map.load(mapname)
        del mp['tiles']
        maps.append(mp)

    server.send.MAP_LIST(maps, source)
########NEW FILE########
__FILENAME__ = GET_PARTIES
from copy import deepcopy

# Return party list to a client
def execute(server, iterator, source):
    server.playersinlobby.append(source)

    parties = deepcopy(server.parties)
    for party in parties.values():
        del party['map']['tiles']

    server.send.PARTY_LIST(parties, source)
########NEW FILE########
__FILENAME__ = GET_PASSIVE_WALKBALES
import Move

# Returns a list of tiles to display the walkable zone of an enemy while in passive mode
def execute(server, iterator, source):
    charid = iterator.getString()
    party = server.parties[server.sessions[source]['party']]
    walkables = Move.GetWalkables( party, charid )
    
    server.send.PASSIVE_WALKABLES_LIST(charid, walkables, source)
########NEW FILE########
__FILENAME__ = GET_PATH
import Move, Character

# Returns the path that a chatacter will take to move from one tile to another on the map
def execute(server, iterator, source):
    charid = iterator.getString()
    x2 = iterator.getUint8()
    y2 = iterator.getUint8()
    z2 = iterator.getUint8()

    party = server.parties[server.sessions[source]['party']]

    orig = Character.Coords( party, charid )
    x1 = orig[0]
    y1 = orig[1]
    z1 = orig[2]

    path = Move.GetPath( party, charid, x1, y1, z1, x2, y2, z2 )

    server.send.PATH(charid, orig, party['chars'][charid]['direction'], (x2,y2,z2), path, source)
########NEW FILE########
__FILENAME__ = GET_WALKABLES
import Move

# Return the list of walkable tile for a character to a client
def execute(server, iterator, source):
    charid = iterator.getString()
    party = server.parties[server.sessions[source]['party']]
    walkables = Move.GetWalkables( party, charid )

    server.send.WALKABLES_LIST(charid, walkables, source)
########NEW FILE########
__FILENAME__ = JOIN_PARTY
# A client is trying to join a party
def execute(server, iterator, source):
    name = iterator.getString()
    party = server.parties[name]
    
    if len(party['players']) >= len(party['map']['tilesets']):
        parties = deepcopy(server.parties)
        for party in parties.values():
            del party['map']['tiles']
        server.send.PARTY_JOIN_FAIL(name, parties, source)
    else:
        party['players'].append(server.sessions[source]['login'])
        server.sessions[source]['party'] = name
        server.sessions[source]['player'] = len(party['players'])-1
        server.playersinlobby.remove(source)

        print server.sessions[source]['login'], "joined the party", name
        server.send.PARTY_JOINED(party, source)

        if len(party['players']) == len(party['map']['tilesets']):
            for tilesetid,player in enumerate(party['players']):
                server.send.START_FORMATION(party['map']['tilesets'][tilesetid], server.sessions[server.players[player]]['characters'], server.players[player])

        server.updateAllPartyLists()
########NEW FILE########
__FILENAME__ = LOGIN_MESSAGE
import Character

# A client is trying to log into the server. Let's check its credentials and sent it back a reply
def execute(server, iterator, source):
    login = iterator.getString()
    password = iterator.getString()

    # since the server code is not connected to the database yet,
    # we authenticate the client if login == password
    if login != password:
        server.send.LOGIN_FAIL('Wrong credentials.', source)
    elif server.sessions.has_key(source):
        server.send.LOGIN_FAIL('Already logged in.', source)
    elif login in server.players.keys():
        server.send.LOGIN_FAIL('Username already in use.', source)
    else:
        server.players[login] = source
        server.sessions[source] = {}
        server.sessions[source]['login'] = login
        print login, 'logged in.'
        # since the server code is not connected to the database yet,
        # we generate a random team for each player
        server.sessions[source]['characters'] = []
        for i in range(10):
            server.charid = server.charid + 1
            char = Character.Random(server.charid)
            server.sessions[source]['characters'].append(char)
            server.chars.append(char)
        server.send.LOGIN_SUCCESS(source)
########NEW FILE########
__FILENAME__ = MOVE_TO
import Move, Character

# A player wants to move one of its units
def execute(server, iterator, source):
    charid = iterator.getString()
    x2 = iterator.getUint8()
    y2 = iterator.getUint8()
    z2 = iterator.getUint8()
    
    party = server.parties[server.sessions[source]['party']]
    
    orig = Character.Coords( party, charid )
    x1 = orig[0]
    y1 = orig[1]
    z1 = orig[2]

    path = Move.GetPath( party, charid, x1, y1, z1, x2, y2, z2 )
    walkables = Move.GetWalkables( party, charid )

    del party['map']['tiles'][x1][y1][z1]['char']
    party['map']['tiles'][x2][y2][z2]['char'] = charid

    party['chars'][charid]['direction'] = Move.GetNewDirection( x1, y1, x2, y2 )
    party['chars'][charid]['canmove'] = False
    
    server.send.MOVED(charid, x2, y2, z2, source)
    
    for playerid,playerlogin in enumerate(party['players']):
        if playerid != server.sessions[source]['player']:
            server.send.MOVED_PASSIVE(charid, walkables, path, server.players[playerlogin])
########NEW FILE########
__FILENAME__ = UPDATE_PARTY
# The most important controller
def execute(server, iterator, source):
    party = server.parties[server.sessions[source]['party']]
    chars = party['chars']
    
    aliveteams = {}
    for charid in chars.keys():
        if chars[charid]['hp'] > 0:
            if aliveteams.has_key(chars[charid]['team']):
                aliveteams[chars[charid]['team']] = aliveteams[chars[charid]['team']] + 1
            else:
                aliveteams[chars[charid]['team']] = 1
    if len(aliveteams) < 2:
        for client in party['players']:
            if source == server.players[client]:
                server.send.BATTLE_COMPLETE(server.players[client])
            else:
                server.send.GAME_OVER(server.players[client])
        del server.parties[server.sessions[source]['party']]
        server.updateAllPartyLists()
        return

    for charid in chars.keys():
        party['yourturn'] = int(chars[charid]['team']) == int(server.sessions[source]['player'])
        if chars[charid]['active']:
            server.send.PARTY_UPDATED(party['yourturn'], chars, source)
            return
    
    while True:
        for charid in chars.keys():
            char = chars[charid]
            char['ct'] = char['ct'] + char['speed']
            if char['ct'] >= 100:
                if char['hp'] > 0:
                    char['active'] = True
                    char['canmove'] = True
                    char['canact'] = True
                    party['yourturn'] = int(chars[charid]['team']) == int(server.sessions[source]['player'])
                    server.send.PARTY_UPDATED(party['yourturn'], chars, source)
                    return
                else:
                    char['ct'] = 0

########NEW FILE########
__FILENAME__ = WAIT
# End of the turn of a unit
def execute(server, iterator, source):
    charid = iterator.getString()
    direction = iterator.getUint8()
    
    party = server.parties[server.sessions[source]['party']]
    char = party['chars'][charid]

    if char['canmove'] and char['canact']:
        char['ct'] = char['ct'] - 60
    elif char['canmove'] or char['canact']:
        char['ct'] = char['ct'] - 80
    else:
        char['ct'] = char['ct'] - 100

    char['direction'] = direction

    char['active'] = False
    char['canmove'] = False
    char['canact'] = False

    server.send.WAIT_SUCCESS(source)

    for playerid,playerlogin in enumerate(party['players']):
        if playerid != server.sessions[source]['player']:
            server.send.WAIT_PASSIVE(charid, direction, server.players[playerlogin])
########NEW FILE########
__FILENAME__ = main
from panda3d.core import loadPrcFile
loadPrcFile("config.prc")
import direct.directbase.DirectStart
from direct.task.Task import Task
from direct.distributed.PyDatagramIterator import *
import sys
from copy import deepcopy
from Send import Send
from Controllers import *

class Server:

    def __init__(self):

        self.activeConnections = [] # lists all connections
        self.players = {} # keys are the players logins, values are the players datagram connections
        self.parties = {} # keys are the parties names, values are dicts representing parties data
        self.sessions = {} # keys are the datagram connections, values are dicts storing the characters of the player and its party
        self.playersinlobby = [] # lists players in the party screen
        self.charid = 0 # used for random team generation
        self.chars = [] # lists of dicts representing characters data

        self.cManager  = QueuedConnectionManager()
        self.cListener = QueuedConnectionListener(self.cManager, 0)
        self.cReader   = QueuedConnectionReader(self.cManager, 0)
        self.cReader.setTcpHeaderSize(4)
        self.send = Send(self.cManager)

        port = 3001
        if len(sys.argv) > 1:
            port = sys.argv[1]

        self.tcpSocket = self.cManager.openTCPServerRendezvous(port, 10)
        self.cListener.addConnection(self.tcpSocket)
        print "Server listening on port", port

        taskMgr.add(self.tskListenerPolling, "Poll the connection listener", -39)
        taskMgr.add(self.tskReaderPolling, "Poll the connection reader", -40)

    def processData(self, datagram):
        iterator = PyDatagramIterator(datagram)
        source = datagram.getConnection()
        callback = iterator.getString()
        getattr(globals()[callback], 'execute')(self, iterator, source)

    def updateAllPartyLists(self):
        parties = deepcopy(self.parties)
        for party in parties.values():
            del party['map']['tiles']

        for player in self.playersinlobby:
            self.send.UPDATE_PARTY_LIST(parties, player)

    def tskListenerPolling(self, taskdata):
        if self.cListener.newConnectionAvailable():

            rendezvous = PointerToConnection()
            netAddress = NetAddress()
            newConnection = PointerToConnection()
     
            if self.cListener.getNewConnection(rendezvous, netAddress, newConnection):
                newConnection = newConnection.p()
                self.activeConnections.append(newConnection)
                self.cReader.addConnection(newConnection)
                print 'A new client is connected', newConnection
        return Task.cont

    def tskReaderPolling(self, taskdata):
        if self.cReader.dataAvailable():
            datagram=NetDatagram()
            if self.cReader.getData(datagram):
                self.processData(datagram)
        return Task.cont

Server()
run()
########NEW FILE########
__FILENAME__ = Map
from panda3d.core import loadPrcFile
loadPrcFile("config.prc")
from pandac.PandaModules import *
import json

GAME = ConfigVariableString('game', 'fft').getValue()

def load(name):
    f = open(GAME+'/maps/'+name+'.json', 'r')
    m = json.loads(f.read())
    f.close()

    tiles = [ [ [ None for z in range(m['z']) ] for y in range(m['y']) ] for x in range(m['x']) ]
    for t in m['tiles']:
        tiles[int(t['x'])][int(t['y'])][int(t['z'])] = t

    m['tiles'] = tiles

    return m

########NEW FILE########
__FILENAME__ = Move
import math
import Character

def getadjacentwalkables( party, charid, tiles ):

    walkables = []

    for x1, y1, z1 in tiles:
        for x2, y2 in ( (x1-1, y1), (x1+1, y1), (x1, y1-1), (x1, y1+1) ):
            try:
                t2 = party['map']['tiles'][x2][y2]
                if t2 and x2 >= 0 and y2 >= 0:
                    for z2,t3 in enumerate(t2):
                        if t3 \
                        and (not t3.has_key('char') or party['chars'][t3['char']]['team'] ==  party['chars'][charid]['team'] or party['chars'][t3['char']]['hp'] == 0 ) \
                        and t3['walkable'] and t3['selectable'] \
                        and math.fabs(z2-z1) <= party['chars'][charid]['jump']:
                            walkables.append( (x2, y2, z2) )
            except:
                pass

    return walkables

def GetWalkables( party, charid ):

    # get the current tile
    tile = Character.Coords( party, charid )
    # recursively add walkables tiles to the list
    walkables = [ tile ]
    for i in range(1, party['chars'][charid]['move']+1):
        walkables.extend( getadjacentwalkables( party, charid, walkables ) )

    # remove current tile from the list
    filtered_walkables = []
    for walkable in walkables:
        if not walkable == tile:
            filtered_walkables.append( walkable )
    walkables = filtered_walkables

    # remove tiles containing characters from the list
    filtered_walkables = []
    for walkable in walkables:
        x, y, z = walkable
        if not party['map']['tiles'][x][y][z].has_key('char'):
            filtered_walkables.append( walkable )
    walkables = filtered_walkables

    return walkables

def IsWalkable( party, charid, x, y, z ):

    return (x, y, z) in GetWalkables( party, charid )

def GetNewDirection( x1, y1, x2, y2 ):

    dx = x2 - x1
    dy = y2 - y1

    if math.fabs(dy) > math.fabs(dx):
        return 1 if dy > 0 else 0
    else:
        return 2 if dx > 0 else 3

def GetPath ( party, charid, x1, y1, z1, x2, y2, z2 ):

    tree = { '-'.join(map(str,(x1,y1,z1))) : {} }
    buildtree( party, charid, tree, party['chars'][charid]['move']-1, '-'.join(map(str,(x2,y2,z2))) )

    paths = []
    findpathes( tree, [], paths )

    pathtoreturn = []
    for tile in paths[0]:
        pathtoreturn.append( tuple(map(int,tile.split('-'))) )

    return pathtoreturn

def buildtree ( party, charid, tree, moves, dest ):

    for k1 in tree.keys():

        for adj in getadjacentwalkables( party, charid, [ tuple(map(int,k1.split('-'))) ] ):
            k2 = '-'.join( map( str, adj ) )

            if k2 == dest:
                tree[k1][k2] = 'X'
                return
            else:
                tree[k1][k2] = {}

        if moves > 0:
            buildtree( party, charid, tree[k1], moves-1, dest )

def findpathes ( tree, p, paths ):

    for k in tree.keys():
        if tree[k] == 'X':
            paths.append( p + [k] )
        else:
            findpathes( tree[k], p + [k], paths )


########NEW FILE########
__FILENAME__ = Send
from direct.distributed.PyDatagram import PyDatagram, ConnectionWriter
import json

# Datagrams to be sent to the clients
class Send(object):

    def __init__(self, cManager):
        self.cWriter = ConnectionWriter(cManager, 0)
        self.cWriter.setTcpHeaderSize(4)

    def LOGIN_FAIL(self, errormsg, player):
        myPyDatagram = PyDatagram()
        myPyDatagram.addString('LOGIN_FAIL')
        myPyDatagram.addString(errormsg)
        self.cWriter.send(myPyDatagram, player)

    def LOGIN_SUCCESS(self, player):
        myPyDatagram = PyDatagram()
        myPyDatagram.addString('LOGIN_SUCCESS')
        self.cWriter.send(myPyDatagram, player)

    def PARTY_CREATED(self, party, player):
        myPyDatagram = PyDatagram()
        myPyDatagram.addString('PARTY_CREATED')
        myPyDatagram.addString32(json.dumps(party))
        self.cWriter.send(myPyDatagram, player)

    def MAP_LIST(self, maps, player):
        myPyDatagram = PyDatagram()
        myPyDatagram.addString('MAP_LIST')
        myPyDatagram.addString(json.dumps(maps))
        self.cWriter.send(myPyDatagram, player)

    def PARTY_LIST(self, parties, player):
        myPyDatagram = PyDatagram()
        myPyDatagram.addString('PARTY_LIST')
        myPyDatagram.addString32(json.dumps(parties))
        self.cWriter.send(myPyDatagram, player)

    def PARTY_JOIN_FAIL(self, name, parties, player):
        myPyDatagram = PyDatagram()
        myPyDatagram.addString('PARTY_JOIN_FAIL')
        myPyDatagram.addString('Party '+name+' is full.')
        myPyDatagram.addString32(json.dumps(parties))
        self.cWriter.send(myPyDatagram, player)

    def PARTY_JOINED(self, party, player):
        myPyDatagram = PyDatagram()
        myPyDatagram.addString('PARTY_JOINED')
        myPyDatagram.addString32(json.dumps(party))
        self.cWriter.send(myPyDatagram, player)

    def START_FORMATION(self, tileset, team, player):
        myPyDatagram = PyDatagram()
        myPyDatagram.addString('START_FORMATION')
        myPyDatagram.addString32(json.dumps(tileset))
        myPyDatagram.addString32(json.dumps(team))
        self.cWriter.send(myPyDatagram, player)

    def BATTLE_COMPLETE(self, player):
        myPyDatagram = PyDatagram()
        myPyDatagram.addString('BATTLE_COMPLETE')
        self.cWriter.send(myPyDatagram, player)

    def GAME_OVER(self, player):
        myPyDatagram = PyDatagram()
        myPyDatagram.addString('GAME_OVER')
        self.cWriter.send(myPyDatagram, player)

    def PARTY_UPDATED(self, yourturn, chars, player):
        myPyDatagram = PyDatagram()
        myPyDatagram.addString('PARTY_UPDATED')
        myPyDatagram.addBool(yourturn)
        myPyDatagram.addString32(json.dumps(chars))
        self.cWriter.send(myPyDatagram, player)

    def WALKABLES_LIST(self, charid, walkables, player):
        myPyDatagram = PyDatagram()
        myPyDatagram.addString('WALKABLES_LIST')
        myPyDatagram.addString(charid)
        myPyDatagram.addString(json.dumps(walkables))
        self.cWriter.send(myPyDatagram, player)

    def PASSIVE_WALKABLES_LIST(self, charid, walkables, player):
        myPyDatagram = PyDatagram()
        myPyDatagram.addString('PASSIVE_WALKABLES_LIST')
        myPyDatagram.addString(charid)
        myPyDatagram.addString(json.dumps(walkables))
        self.cWriter.send(myPyDatagram, player)

    def PATH(self, charid, orig, direction, dest, path, player):
        myPyDatagram = PyDatagram()
        myPyDatagram.addString('PATH')
        myPyDatagram.addString(charid)
        myPyDatagram.addString(json.dumps(orig))
        myPyDatagram.addUint8(direction)
        myPyDatagram.addString(json.dumps(dest))
        myPyDatagram.addString(json.dumps(path))
        self.cWriter.send(myPyDatagram, player)

    def MOVED(self, charid, x, y, z, player):
        myPyDatagram = PyDatagram()
        myPyDatagram.addString('MOVED')
        myPyDatagram.addString(charid)
        myPyDatagram.addUint8(x)
        myPyDatagram.addUint8(y)
        myPyDatagram.addUint8(z)
        self.cWriter.send(myPyDatagram, player)

    def MOVED_PASSIVE(self, charid, walkables, path, player):
        myPyDatagram = PyDatagram()
        myPyDatagram.addString('MOVED_PASSIVE')
        myPyDatagram.addString(charid)
        myPyDatagram.addString(json.dumps(walkables))
        myPyDatagram.addString(json.dumps(path))
        self.cWriter.send(myPyDatagram, player)

    def WAIT_PASSIVE(self, charid, direction, player):
        myPyDatagram = PyDatagram()
        myPyDatagram.addString('WAIT_PASSIVE')
        myPyDatagram.addString(charid)
        myPyDatagram.addUint8(direction)
        self.cWriter.send(myPyDatagram, player)

    def ATTACKABLES_LIST(self, charid, attackables, player):
        myPyDatagram = PyDatagram()
        myPyDatagram.addString('ATTACKABLES_LIST')
        myPyDatagram.addString(charid)
        myPyDatagram.addString(json.dumps(attackables))
        self.cWriter.send(myPyDatagram, player)

    def ATTACK_SUCCESS(self, charid1, charid2, damages, player):
        myPyDatagram = PyDatagram()
        myPyDatagram.addString('ATTACK_SUCCESS')
        myPyDatagram.addString(charid1)
        myPyDatagram.addString(charid2)
        myPyDatagram.addUint8(damages)
        self.cWriter.send(myPyDatagram, player)

    def ATTACK_PASSIVE(self, charid1, charid2, damages, attackables, player):
        myPyDatagram = PyDatagram()
        myPyDatagram.addString('ATTACK_PASSIVE')
        myPyDatagram.addString(charid1)
        myPyDatagram.addString(charid2)
        myPyDatagram.addUint8(damages)
        myPyDatagram.addString(json.dumps(attackables))
        self.cWriter.send(myPyDatagram, player)

    def START_BATTLE(self, party, player):
        myPyDatagram = PyDatagram()
        myPyDatagram.addString('START_BATTLE')
        myPyDatagram.addString32(json.dumps(party))
        self.cWriter.send(myPyDatagram, player)

    def UPDATE_PARTY_LIST(self, parties, player):
        myPyDatagram = PyDatagram()
        myPyDatagram.addString('UPDATE_PARTY_LIST')
        myPyDatagram.addString32(json.dumps(parties))
        self.cWriter.send(myPyDatagram, player)

    def WAIT_SUCCESS(self, player):
        myPyDatagram = PyDatagram()
        myPyDatagram.addString('WAIT_SUCCESS')
        self.cWriter.send(myPyDatagram, player)
########NEW FILE########
