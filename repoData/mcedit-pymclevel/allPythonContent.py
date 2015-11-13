__FILENAME__ = biome_types
biome_types = {
    -1: '(Uncalculated)',
    0: 'Ocean',
    1: 'Plains',
    2: 'Desert',
    3: 'Extreme Hills',
    4: 'Forest',
    5: 'Taiga',
    6: 'Swamppland',
    7: 'River',
    8: 'Hell (Nether)',
    9: 'Sky (End)',
    10: 'Frozen Ocean',
    11: 'Frozen River',
    12: 'Ice Plains',
    13: 'Ice Mountains',
    14: 'Mushroom Island',
    15: 'Mushroom Island Shore',
    16: 'Beach',
    17: 'Desert Hills',
    18: 'Forest Hills',
    19: 'Taiga Hills',
    20: 'Extreme Hills Edge',
    21: 'Jungle',
    22: 'Jungle Hills',
    23: 'Jungle Edge',
    24: 'Deep Ocean',
    25: 'Stone Beach',
    26: 'Cold Beach',
    27: 'Birch Forest',
    28: 'Birch Forest Hills',
    29: 'Roofed Forest',
    30: 'Cold Taiga',
    31: 'Cold Taiga Hills',
    32: 'Mega Taiga',
    33: 'Mega Taiga Hills',
    34: 'Extreme Hills+',
    35: 'Savanna',
    36: 'Savanna Plateau',
    37: 'Messa',
    38: 'Messa Plateau F',
    39: 'Messa Plateau',
    129: 'Sunflower Plains',
    130: 'Desert M',
    131: 'Extreme Hills M',
    132: 'Flower Forest',
    133: 'Taiga M',
    134: 'Swampland M',
    140: 'Ice Plains Spikes',
    141: 'Ice Mountains Spikes',
    149: 'Jungle M',
    151: 'JungleEdge M',
    155: 'Birch Forest M',
    156: 'Birch Forest Hills M',
    157: 'Roofed Forest M',
    158: 'Cold Taiga M',
    160: 'Mega Spruce Taiga',
    161: 'Mega Spruce Taiga 2',
    162: 'Extreme Hills+ M',
    163: 'Savanna M',
    164: 'Savanna Plateau M',
    165: 'Mesa (Bryce)',
    166: 'Mesa Plateau F M',
    167: 'Mesa Plateau M'
}

########NEW FILE########
__FILENAME__ = blockrotation
import materials
from materials import alphaMaterials
from numpy import arange, zeros


def genericVerticalFlip(cls):
    rotation = arange(16, dtype='uint8')
    if hasattr(cls, "Up") and hasattr(cls, "Down"):
        rotation[cls.Up] = cls.Down
        rotation[cls.Down] = cls.Up

    if hasattr(cls, "TopNorth") and hasattr(cls, "TopWest") and hasattr(cls, "TopSouth") and hasattr(cls, "TopEast"):
        rotation[cls.North] = cls.TopNorth
        rotation[cls.West] = cls.TopWest
        rotation[cls.South] = cls.TopSouth
        rotation[cls.East] = cls.TopEast
        rotation[cls.TopNorth] = cls.North
        rotation[cls.TopWest] = cls.West
        rotation[cls.TopSouth] = cls.South
        rotation[cls.TopEast] = cls.East

    return rotation


def genericRotation(cls):
    rotation = arange(16, dtype='uint8')
    rotation[cls.North] = cls.West
    rotation[cls.West] = cls.South
    rotation[cls.South] = cls.East
    rotation[cls.East] = cls.North
    if hasattr(cls, "TopNorth") and hasattr(cls, "TopWest") and hasattr(cls, "TopSouth") and hasattr(cls, "TopEast"):
        rotation[cls.TopNorth] = cls.TopWest
        rotation[cls.TopWest] = cls.TopSouth
        rotation[cls.TopSouth] = cls.TopEast
        rotation[cls.TopEast] = cls.TopNorth

    return rotation


def genericEastWestFlip(cls):
    rotation = arange(16, dtype='uint8')
    rotation[cls.West] = cls.East
    rotation[cls.East] = cls.West
    if hasattr(cls, "TopWest") and hasattr(cls, "TopEast"):
        rotation[cls.TopWest] = cls.TopEast
        rotation[cls.TopEast] = cls.TopWest

    return rotation


def genericNorthSouthFlip(cls):
    rotation = arange(16, dtype='uint8')
    rotation[cls.South] = cls.North
    rotation[cls.North] = cls.South
    if hasattr(cls, "TopNorth") and hasattr(cls, "TopSouth"):
        rotation[cls.TopSouth] = cls.TopNorth
        rotation[cls.TopNorth] = cls.TopSouth

    return rotation

rotationClasses = []

def genericFlipRotation(cls):
    cls.rotateLeft = genericRotation(cls)

    cls.flipVertical = genericVerticalFlip(cls)
    cls.flipEastWest = genericEastWestFlip(cls)
    cls.flipNorthSouth = genericNorthSouthFlip(cls)
    rotationClasses.append(cls)
    return cls


class Torch:
    blocktypes = [
        alphaMaterials.Torch.ID,
        alphaMaterials.RedstoneTorchOn.ID,
        alphaMaterials.RedstoneTorchOff.ID,
    ]

    South = 1
    North = 2
    West = 3
    East = 4

genericFlipRotation(Torch)


class Ladder:
    blocktypes = [alphaMaterials.Ladder.ID]

    East = 2
    West = 3
    North = 4
    South = 5
genericFlipRotation(Ladder)


class Stair:
    blocktypes = [b.ID for b in alphaMaterials.AllStairs]

    South = 0
    North = 1
    West = 2
    East = 3
    TopSouth = 4
    TopNorth = 5
    TopWest = 6
    TopEast = 7
genericFlipRotation(Stair)


class HalfSlab:
    blocktypes = [alphaMaterials.StoneSlab.ID]

    StoneSlab = 0
    SandstoneSlab = 1
    WoodenSlab = 2
    CobblestoneSlab = 3
    BrickSlab = 4
    StoneBrickSlab = 5
    TopStoneSlab = 8
    TopSandstoneSlab = 9
    TopWoodenSlab = 10
    TopCobblestoneSlab = 11
    TopBrickSlab = 12
    TopStoneBrickSlab = 13

HalfSlab.flipVertical =  arange(16, dtype='uint8')
HalfSlab.flipVertical[HalfSlab.StoneSlab] = HalfSlab.TopStoneSlab
HalfSlab.flipVertical[HalfSlab.SandstoneSlab] = HalfSlab.TopSandstoneSlab
HalfSlab.flipVertical[HalfSlab.WoodenSlab] = HalfSlab.TopWoodenSlab
HalfSlab.flipVertical[HalfSlab.CobblestoneSlab] = HalfSlab.TopCobblestoneSlab
HalfSlab.flipVertical[HalfSlab.BrickSlab] = HalfSlab.TopBrickSlab
HalfSlab.flipVertical[HalfSlab.StoneBrickSlab] = HalfSlab.TopStoneBrickSlab
HalfSlab.flipVertical[HalfSlab.TopStoneSlab] = HalfSlab.StoneSlab
HalfSlab.flipVertical[HalfSlab.TopSandstoneSlab] = HalfSlab.SandstoneSlab
HalfSlab.flipVertical[HalfSlab.TopWoodenSlab] = HalfSlab.WoodenSlab
HalfSlab.flipVertical[HalfSlab.TopCobblestoneSlab] = HalfSlab.CobblestoneSlab
HalfSlab.flipVertical[HalfSlab.TopBrickSlab] = HalfSlab.BrickSlab
HalfSlab.flipVertical[HalfSlab.TopStoneBrickSlab] = HalfSlab.StoneBrickSlab
rotationClasses.append(HalfSlab)


class WallSign:
    blocktypes = [alphaMaterials.WallSign.ID]

    East = 2
    West = 3
    North = 4
    South = 5
genericFlipRotation(WallSign)


class FurnaceDispenserChest:
    blocktypes = [
        alphaMaterials.Furnace.ID,
        alphaMaterials.LitFurnace.ID,
        alphaMaterials.Dispenser.ID,
        alphaMaterials.Chest.ID,
    ]
    East = 2
    West = 3
    North = 4
    South = 5
genericFlipRotation(FurnaceDispenserChest)


class Pumpkin:
    blocktypes = [
        alphaMaterials.Pumpkin.ID,
        alphaMaterials.JackOLantern.ID,
    ]

    East = 0
    South = 1
    West = 2
    North = 3
genericFlipRotation(Pumpkin)


class Rail:
    blocktypes = [alphaMaterials.Rail.ID]

    EastWest = 0
    NorthSouth = 1
    South = 2
    North = 3
    East = 4
    West = 5

    Northeast = 6
    Southeast = 7
    Southwest = 8
    Northwest = 9


def generic8wayRotation(cls):

    cls.rotateLeft = genericRotation(cls)
    cls.rotateLeft[cls.Northeast] = cls.Northwest
    cls.rotateLeft[cls.Southeast] = cls.Northeast
    cls.rotateLeft[cls.Southwest] = cls.Southeast
    cls.rotateLeft[cls.Northwest] = cls.Southwest

    cls.flipEastWest = genericEastWestFlip(cls)
    cls.flipEastWest[cls.Northeast] = cls.Northwest
    cls.flipEastWest[cls.Northwest] = cls.Northeast
    cls.flipEastWest[cls.Southwest] = cls.Southeast
    cls.flipEastWest[cls.Southeast] = cls.Southwest

    cls.flipNorthSouth = genericNorthSouthFlip(cls)
    cls.flipNorthSouth[cls.Northeast] = cls.Southeast
    cls.flipNorthSouth[cls.Southeast] = cls.Northeast
    cls.flipNorthSouth[cls.Southwest] = cls.Northwest
    cls.flipNorthSouth[cls.Northwest] = cls.Southwest
    rotationClasses.append(cls)

generic8wayRotation(Rail)
Rail.rotateLeft[Rail.NorthSouth] = Rail.EastWest
Rail.rotateLeft[Rail.EastWest] = Rail.NorthSouth


def applyBit(apply):
    def _applyBit(class_or_array):
        if hasattr(class_or_array, "rotateLeft"):
            for a in (class_or_array.flipEastWest,
                      class_or_array.flipNorthSouth,
                      class_or_array.rotateLeft):
                apply(a)
        else:
            array = class_or_array
            apply(array)

    return _applyBit


@applyBit
def applyBit8(array):
    array[8:16] = array[0:8] | 0x8


@applyBit
def applyBit4(array):
    array[4:8] = array[0:4] | 0x4
    array[12:16] = array[8:12] | 0x4


@applyBit
def applyBits48(array):
    array[4:8] = array[0:4] | 0x4
    array[8:16] = array[0:8] | 0x8

applyThrownBit = applyBit8


class PoweredDetectorRail(Rail):
    blocktypes = [alphaMaterials.PoweredRail.ID, alphaMaterials.DetectorRail.ID]
PoweredDetectorRail.rotateLeft = genericRotation(PoweredDetectorRail)

PoweredDetectorRail.rotateLeft[PoweredDetectorRail.NorthSouth] = PoweredDetectorRail.EastWest
PoweredDetectorRail.rotateLeft[PoweredDetectorRail.EastWest] = PoweredDetectorRail.NorthSouth

PoweredDetectorRail.flipEastWest = genericEastWestFlip(PoweredDetectorRail)
PoweredDetectorRail.flipNorthSouth = genericNorthSouthFlip(PoweredDetectorRail)
applyThrownBit(PoweredDetectorRail)
rotationClasses.append(PoweredDetectorRail)


class Lever:
    blocktypes = [alphaMaterials.Lever.ID]
    ThrownBit = 0x8
    South = 1
    North = 2
    West = 3
    East = 4
    EastWest = 5
    NorthSouth = 6
Lever.rotateLeft = genericRotation(Lever)
Lever.rotateLeft[Lever.NorthSouth] = Lever.EastWest
Lever.rotateLeft[Lever.EastWest] = Lever.NorthSouth
Lever.flipEastWest = genericEastWestFlip(Lever)
Lever.flipNorthSouth = genericNorthSouthFlip(Lever)
applyThrownBit(Lever)
rotationClasses.append(Lever)


class Button:
    blocktypes = [alphaMaterials.Button.ID, alphaMaterials.WoodenButton.ID]
    PressedBit = 0x8
    South = 1
    North = 2
    West = 3
    East = 4
Button.rotateLeft = genericRotation(Button)
Button.flipEastWest = genericEastWestFlip(Button)
Button.flipNorthSouth = genericNorthSouthFlip(Button)
applyThrownBit(Button)
rotationClasses.append(Button)


class SignPost:
    blocktypes = [alphaMaterials.Sign.ID]
    #west is 0, increasing clockwise

    rotateLeft = arange(16, dtype='uint8')
    rotateLeft -= 4
    rotateLeft &= 0xf

    flipEastWest = arange(16, dtype='uint8')
    flipNorthSouth = arange(16, dtype='uint8')
    pass

rotationClasses.append(SignPost)


class Bed:
    blocktypes = [alphaMaterials.Bed.ID]
    West = 0
    North = 1
    East = 2
    South = 3

genericFlipRotation(Bed)
applyBit8(Bed)
applyBit4(Bed)


class Door:
    blocktypes = [
        alphaMaterials.IronDoor.ID,
        alphaMaterials.WoodenDoor.ID,
    ]
    TopHalfBit = 0x8
    SwungCCWBit = 0x4

    Northeast = 0
    Southeast = 1
    Southwest = 2
    Northwest = 3

    rotateLeft = arange(16, dtype='uint8')

Door.rotateLeft[Door.Northeast] = Door.Northwest
Door.rotateLeft[Door.Southeast] = Door.Northeast
Door.rotateLeft[Door.Southwest] = Door.Southeast
Door.rotateLeft[Door.Northwest] = Door.Southwest

applyBit4(Door.rotateLeft)

#when flipping horizontally, swing the doors so they at least look the same

Door.flipEastWest = arange(16, dtype='uint8')
Door.flipEastWest[Door.Northeast] = Door.Northwest
Door.flipEastWest[Door.Northwest] = Door.Northeast
Door.flipEastWest[Door.Southwest] = Door.Southeast
Door.flipEastWest[Door.Southeast] = Door.Southwest
Door.flipEastWest[4:8] = Door.flipEastWest[0:4]
Door.flipEastWest[0:4] = Door.flipEastWest[4:8] | 0x4
Door.flipEastWest[8:16] = Door.flipEastWest[0:8] | 0x8

Door.flipNorthSouth = arange(16, dtype='uint8')
Door.flipNorthSouth[Door.Northeast] = Door.Southeast
Door.flipNorthSouth[Door.Northwest] = Door.Southwest
Door.flipNorthSouth[Door.Southwest] = Door.Northwest
Door.flipNorthSouth[Door.Southeast] = Door.Northeast
Door.flipNorthSouth[4:8] = Door.flipNorthSouth[0:4]
Door.flipNorthSouth[0:4] = Door.flipNorthSouth[4:8] | 0x4
Door.flipNorthSouth[8:16] = Door.flipNorthSouth[0:8] | 0x8

rotationClasses.append(Door)


class RedstoneRepeater:
    blocktypes = [
        alphaMaterials.RedstoneRepeaterOff.ID,
        alphaMaterials.RedstoneRepeaterOn.ID,

    ]

    East = 0
    South = 1
    West = 2
    North = 3

genericFlipRotation(RedstoneRepeater)

#high bits of the repeater indicate repeater delay, and should be preserved
applyBits48(RedstoneRepeater)


class Trapdoor:
    blocktypes = [alphaMaterials.Trapdoor.ID]

    West = 0
    East = 1
    South = 2
    North = 3

genericFlipRotation(Trapdoor)
applyOpenedBit = applyBit4
applyOpenedBit(Trapdoor)


class PistonBody:
    blocktypes = [alphaMaterials.StickyPiston.ID, alphaMaterials.Piston.ID]

    Down = 0
    Up = 1
    East = 2
    West = 3
    North = 4
    South = 5

genericFlipRotation(PistonBody)
applyPistonBit = applyBit8
applyPistonBit(PistonBody)


class PistonHead(PistonBody):
    blocktypes = [alphaMaterials.PistonHead.ID]

rotationClasses.append(PistonHead)


#Mushroom types:
#Value     Description     Textures
#0     Fleshy piece     Pores on all sides
#1     Corner piece     Cap texture on top, directions 1 (cloud direction) and 2 (sunrise)
#2     Side piece     Cap texture on top and direction 2 (sunrise)
#3     Corner piece     Cap texture on top, directions 2 (sunrise) and 3 (cloud origin)
#4     Side piece     Cap texture on top and direction 1 (cloud direction)
#5     Top piece     Cap texture on top
#6     Side piece     Cap texture on top and direction 3 (cloud origin)
#7     Corner piece     Cap texture on top, directions 0 (sunset) and 1 (cloud direction)
#8     Side piece     Cap texture on top and direction 0 (sunset)
#9     Corner piece     Cap texture on top, directions 3 (cloud origin) and 0 (sunset)
#10     Stem piece     Stem texture on all four sides, pores on top and bottom


class HugeMushroom:
    blocktypes = [alphaMaterials.HugeRedMushroom.ID, alphaMaterials.HugeBrownMushroom.ID]
    Northeast = 1
    East = 2
    Southeast = 3
    South = 6
    Southwest = 9
    West = 8
    Northwest = 7
    North = 4

generic8wayRotation(HugeMushroom)


class Vines:
    blocktypes = [alphaMaterials.Vines.ID]

    WestBit = 1
    NorthBit = 2
    EastBit = 4
    SouthBit = 8

    rotateLeft = arange(16, dtype='uint8')
    flipEastWest = arange(16, dtype='uint8')
    flipNorthSouth = arange(16, dtype='uint8')

#Hmm... Since each bit is a direction, we can rotate by shifting!
Vines.rotateLeft = 0xf & ((Vines.rotateLeft >> 1) | (Vines.rotateLeft << 3))
# Wherever each bit is set, clear it and set the opposite bit
EastWestBits = (Vines.EastBit | Vines.WestBit)
Vines.flipEastWest[(Vines.flipEastWest & EastWestBits) > 0] ^= EastWestBits

NorthSouthBits = (Vines.NorthBit | Vines.SouthBit)
Vines.flipNorthSouth[(Vines.flipNorthSouth & NorthSouthBits) > 0] ^= NorthSouthBits

rotationClasses.append(Vines)



class Anvil:
    blocktypes = [alphaMaterials.Anvil.ID]

    NorthSouth = 0
    WestEast = 1

    rotateLeft = arange(16, dtype='uint8')
    flipEastWest = arange(16, dtype='uint8')
    flipNorthSouth = arange(16, dtype='uint8')

    rotateLeft[NorthSouth] = WestEast
    rotateLeft[WestEast] = NorthSouth

rotationClasses.append(Anvil)

@genericFlipRotation
class FenceGate:
    blocktypes = [alphaMaterials.FenceGate.ID]

    South = 0
    West = 1
    North = 2
    East = 3

@genericFlipRotation
class EnderPortal:
    blocktypes = [alphaMaterials.EnderPortal.ID]

    South = 0
    West = 1
    North = 2
    East = 3

@genericFlipRotation
class CocoaPlant:
    blocktypes = [alphaMaterials.CocoaPlant.ID]

    North = 0
    East = 1
    South = 2
    West = 3

applyBits48(CocoaPlant) # growth state

@genericFlipRotation
class TripwireHook:
    blocktypes = [alphaMaterials.TripwireHook.ID]

    South = 0
    West = 1
    North = 2
    East = 3

applyBits48(TripwireHook) # activation/ready state

@genericFlipRotation
class MobHead:
    blocktypes = [alphaMaterials.MobHead.ID]

    North = 2
    South = 3
    East = 4
    West = 5

@genericFlipRotation
class Hopper:
    blocktypes = [alphaMaterials.Hopper.ID]

    South = 2
    North = 3
    East = 4
    West = 5

@genericFlipRotation
class RedstoneComparator:
    blocktypes = [alphaMaterials.RedstoneComparatorInactive.ID, alphaMaterials.RedstoneComparatorActive.ID]

    South = 0
    West = 1
    North = 2
    East = 3

applyBits48(RedstoneComparator)

def masterRotationTable(attrname):
    # compute a materials.id_limitx16 table mapping each possible blocktype/data combination to
    # the resulting data when the block is rotated
    table = zeros((materials.id_limit, 16), dtype='uint8')
    table[:] = arange(16, dtype='uint8')
    for cls in rotationClasses:
        if hasattr(cls, attrname):
            blocktable = getattr(cls, attrname)
            for blocktype in cls.blocktypes:
                table[blocktype] = blocktable

    return table


def rotationTypeTable():
    table = {}
    for cls in rotationClasses:
        for b in cls.blocktypes:
            table[b] = cls

    return table


class BlockRotation:
    rotateLeft = masterRotationTable("rotateLeft")
    flipEastWest = masterRotationTable("flipEastWest")
    flipNorthSouth = masterRotationTable("flipNorthSouth")
    flipVertical = masterRotationTable("flipVertical")
    typeTable = rotationTypeTable()


def SameRotationType(blocktype1, blocktype2):
    #use different default values for typeTable.get() to make it return false when neither blocktype is present
    return BlockRotation.typeTable.get(blocktype1.ID) == BlockRotation.typeTable.get(blocktype2.ID, BlockRotation)


def FlipVertical(blocks, data):
    data[:] = BlockRotation.flipVertical[blocks, data]


def FlipNorthSouth(blocks, data):
    data[:] = BlockRotation.flipNorthSouth[blocks, data]


def FlipEastWest(blocks, data):
    data[:] = BlockRotation.flipEastWest[blocks, data]


def RotateLeft(blocks, data):
    data[:] = BlockRotation.rotateLeft[blocks, data]

########NEW FILE########
__FILENAME__ = block_copy
from datetime import datetime
import logging
log = logging.getLogger(__name__)

import numpy
from box import BoundingBox, Vector
from mclevelbase import exhaust
import materials
from entity import Entity, TileEntity


def convertBlocks(destLevel, sourceLevel, blocks, blockData):
    return materials.convertBlocks(destLevel.materials, sourceLevel.materials, blocks, blockData)

def sourceMaskFunc(blocksToCopy):
    if blocksToCopy is not None:
        typemask = numpy.zeros(materials.id_limit, dtype='bool')
        typemask[blocksToCopy] = 1

        def maskedSourceMask(sourceBlocks):
            return typemask[sourceBlocks]

        return maskedSourceMask

    def unmaskedSourceMask(_sourceBlocks):
        return slice(None, None)

    return unmaskedSourceMask


def adjustCopyParameters(destLevel, sourceLevel, sourceBox, destinationPoint):
    # if the destination box is outside the level, it and the source corners are moved inward to fit.
    (dx, dy, dz) = map(int, destinationPoint)

    log.debug(u"Asked to copy {} blocks \n\tfrom {} in {}\n\tto {} in {}" .format(
              sourceBox.volume, sourceBox, sourceLevel, destinationPoint, destLevel))
    if destLevel.Width == 0:
        return sourceBox, destinationPoint

    destBox = BoundingBox(destinationPoint, sourceBox.size)
    actualDestBox = destBox.intersect(destLevel.bounds)

    actualSourceBox = BoundingBox(sourceBox.origin + actualDestBox.origin - destBox.origin, destBox.size)
    actualDestPoint = actualDestBox.origin

    return actualSourceBox, actualDestPoint



def copyBlocksFromIter(destLevel, sourceLevel, sourceBox, destinationPoint, blocksToCopy=None, entities=True, create=False, biomes=False):
    """ copy blocks between two infinite levels by looping through the
    destination's chunks. make a sub-box of the source level for each chunk
    and copy block and entities in the sub box to the dest chunk."""

    (lx, ly, lz) = sourceBox.size

    sourceBox, destinationPoint = adjustCopyParameters(destLevel, sourceLevel, sourceBox, destinationPoint)
    # needs work xxx
    log.info(u"Copying {0} blocks from {1} to {2}" .format(ly * lz * lx, sourceBox, destinationPoint))
    startTime = datetime.now()

    destBox = BoundingBox(destinationPoint, sourceBox.size)
    chunkCount = destBox.chunkCount
    i = 0
    e = 0
    t = 0

    sourceMask = sourceMaskFunc(blocksToCopy)

    copyOffset = [d - s for s, d in zip(sourceBox.origin, destinationPoint)]

    # Visit each chunk in the destination area.
    #   Get the region of the source area corresponding to that chunk
    #   Visit each chunk of the region of the source area
    #     Get the slices of the destination chunk
    #     Get the slices of the source chunk
    #     Copy blocks and data

    for destCpos in destBox.chunkPositions:
        cx, cz = destCpos

        destChunkBox = BoundingBox((cx << 4, 0, cz << 4), (16, destLevel.Height, 16)).intersect(destBox)
        destChunkBoxInSourceLevel = BoundingBox([d - o for o, d in zip(copyOffset, destChunkBox.origin)], destChunkBox.size)

        if not destLevel.containsChunk(*destCpos):
            if create and any(sourceLevel.containsChunk(*c) for c in destChunkBoxInSourceLevel.chunkPositions):
                # Only create chunks in the destination level if the source level has chunks covering them.
                destLevel.createChunk(*destCpos)
            else:
                continue

        destChunk = destLevel.getChunk(*destCpos)


        i += 1
        yield (i, chunkCount)
        if i % 100 == 0:
            log.info("Chunk {0}...".format(i))

        for srcCpos in destChunkBoxInSourceLevel.chunkPositions:
            if not sourceLevel.containsChunk(*srcCpos):
                continue

            sourceChunk = sourceLevel.getChunk(*srcCpos)

            sourceChunkBox, sourceSlices = sourceChunk.getChunkSlicesForBox(destChunkBoxInSourceLevel)
            if sourceChunkBox.volume == 0:
                continue

            sourceChunkBoxInDestLevel = BoundingBox([d + o for o, d in zip(copyOffset, sourceChunkBox.origin)], sourceChunkBox.size)

            _, destSlices = destChunk.getChunkSlicesForBox(sourceChunkBoxInDestLevel)

            sourceBlocks = sourceChunk.Blocks[sourceSlices]
            sourceData = sourceChunk.Data[sourceSlices]

            mask = sourceMask(sourceBlocks)
            convertedSourceBlocks, convertedSourceData = convertBlocks(destLevel, sourceLevel, sourceBlocks, sourceData)

            destChunk.Blocks[destSlices][mask] = convertedSourceBlocks[mask]
            if convertedSourceData is not None:
                destChunk.Data[destSlices][mask] = convertedSourceData[mask]

            if entities:
                ents = sourceChunk.getEntitiesInBox(destChunkBoxInSourceLevel)
                e += len(ents)
                for entityTag in ents:
                    eTag = Entity.copyWithOffset(entityTag, copyOffset)
                    destLevel.addEntity(eTag)

            tileEntities = sourceChunk.getTileEntitiesInBox(destChunkBoxInSourceLevel)
            t += len(tileEntities)
            for tileEntityTag in tileEntities:
                eTag = TileEntity.copyWithOffset(tileEntityTag, copyOffset)
                destLevel.addTileEntity(eTag)

            if biomes and hasattr(destChunk, 'Biomes') and hasattr(sourceChunk, 'Biomes'):
                destChunk.Biomes[destSlices[:2]] = sourceChunk.Biomes[sourceSlices[:2]]

        destChunk.chunkChanged()

    log.info("Duration: {0}".format(datetime.now() - startTime))
    log.info("Copied {0} entities and {1} tile entities".format(e, t))

def copyBlocksFrom(destLevel, sourceLevel, sourceBox, destinationPoint, blocksToCopy=None, entities=True, create=False, biomes=False):
    return exhaust(copyBlocksFromIter(destLevel, sourceLevel, sourceBox, destinationPoint, blocksToCopy, entities, create, biomes))






########NEW FILE########
__FILENAME__ = block_fill
import logging
import materials

log = logging.getLogger(__name__)

import numpy

from mclevelbase import exhaust
import blockrotation
from entity import TileEntity

def blockReplaceTable(blocksToReplace):
    blocktable = numpy.zeros((materials.id_limit, 16), dtype='bool')
    for b in blocksToReplace:
        if b.hasVariants:
            blocktable[b.ID, b.blockData] = True
        else:
            blocktable[b.ID] = True

    return blocktable

def fillBlocks(level, box, blockInfo, blocksToReplace=()):
    return exhaust(level.fillBlocksIter(box, blockInfo, blocksToReplace))

def fillBlocksIter(level, box, blockInfo, blocksToReplace=()):
    if box is None:
        chunkIterator = level.getAllChunkSlices()
        box = level.bounds
    else:
        chunkIterator = level.getChunkSlices(box)

    # shouldRetainData = (not blockInfo.hasVariants and not any([b.hasVariants for b in blocksToReplace]))
    # if shouldRetainData:
    #    log.info( "Preserving data bytes" )
    shouldRetainData = False  # xxx old behavior overwrote blockdata with 0 when e.g. replacing water with lava

    log.info("Replacing {0} with {1}".format(blocksToReplace, blockInfo))

    changesLighting = True
    blocktable = None
    if len(blocksToReplace):
        blocktable = blockReplaceTable(blocksToReplace)
        shouldRetainData = all([blockrotation.SameRotationType(blockInfo, b) for b in blocksToReplace])

        newAbsorption = level.materials.lightAbsorption[blockInfo.ID]
        oldAbsorptions = [level.materials.lightAbsorption[b.ID] for b in blocksToReplace]
        changesLighting = False
        for a in oldAbsorptions:
            if a != newAbsorption:
                changesLighting = True

        newEmission = level.materials.lightEmission[blockInfo.ID]
        oldEmissions = [level.materials.lightEmission[b.ID] for b in blocksToReplace]
        for a in oldEmissions:
            if a != newEmission:
                changesLighting = True

    i = 0
    skipped = 0
    replaced = 0

    for (chunk, slices, point) in chunkIterator:
        i += 1
        if i % 100 == 0:
            log.info(u"Chunk {0}...".format(i))
        yield i, box.chunkCount

        blocks = chunk.Blocks[slices]
        data = chunk.Data[slices]
        mask = slice(None)

        needsLighting = changesLighting

        if blocktable is not None:
            mask = blocktable[blocks, data]

            blockCount = mask.sum()
            replaced += blockCount

            # don't waste time relighting and copying if the mask is empty
            if blockCount:
                blocks[:][mask] = blockInfo.ID
                if not shouldRetainData:
                    data[mask] = blockInfo.blockData
            else:
                skipped += 1
                needsLighting = False

            def include(tileEntity):
                p = TileEntity.pos(tileEntity)
                x, y, z = map(lambda a, b, c: (a - b) - c, p, point, box.origin)
                return not ((p in box) and mask[x, z, y])

            chunk.TileEntities[:] = filter(include, chunk.TileEntities)

        else:
            blocks[:] = blockInfo.ID
            if not shouldRetainData:
                data[:] = blockInfo.blockData
            chunk.removeTileEntitiesInBox(box)

        chunk.chunkChanged(needsLighting)

    if len(blocksToReplace):
        log.info(u"Replace: Skipped {0} chunks, replaced {1} blocks".format(skipped, replaced))

########NEW FILE########
__FILENAME__ = box
from collections import namedtuple
import itertools
import math

_Vector = namedtuple("_Vector", ("x", "y", "z"))

class Vector(_Vector):

    __slots__ = ()

    def __add__(self, other):
        return Vector(self[0] + other[0], self[1] + other[1], self[2] + other[2])

    def __sub__(self, other):
        return Vector(self[0] - other[0], self[1] - other[1], self[2] - other[2])

    def __mul__(self, other):
        if isinstance(other, (int, float)):
            return Vector(self[0] * other, self[1] * other, self[2] * other)

        return Vector(self[0] * other[0], self[1] * other[1], self[2] * other[2])

    def __truediv__(self, other):
        if isinstance(other, (int, float)):
            return Vector(self[0] / other, self[1] / other, self[2] / other)

        return Vector(self[0] / other[0], self[1] / other[1], self[2] / other[2])

    __div__ = __truediv__

    def length(self):
        return math.sqrt(self[0] * self[0] + self[1] * self[1] + self[2] * self[2])

    def normalize(self):
        l = self.length()
        if l == 0: return self
        return self / l

    def intfloor(self):
        return Vector(*[int(math.floor(p)) for p in self])

class BoundingBox (object):
    type = int

    def __init__(self, origin=(0, 0, 0), size=(0, 0, 0)):
        if isinstance(origin, BoundingBox):
            self._origin = origin._origin
            self._size = origin._size
        else:
            self._origin, self._size = Vector(*(self.type(a) for a in origin)), Vector(*(self.type(a) for a in size))

    def __repr__(self):
        return "BoundingBox({0}, {1})".format(self.origin, self.size)

    @property
    def origin(self):
        "The smallest position in the box"
        return self._origin

    @property
    def size(self):
        "The size of the box"
        return self._size

    @property
    def width(self):
        "The dimension along the X axis"
        return self._size.x

    @property
    def height(self):
        "The dimension along the Y axis"
        return self._size.y

    @property
    def length(self):
        "The dimension along the Z axis"
        return self._size.z

    @property
    def minx(self):
        return self.origin.x

    @property
    def miny(self):
        return self.origin.y

    @property
    def minz(self):
        return self.origin.z

    @property
    def maxx(self):
        return self.origin.x + self.size.x

    @property
    def maxy(self):
        return self.origin.y + self.size.y

    @property
    def maxz(self):
        return self.origin.z + self.size.z

    @property
    def maximum(self):
        "The largest point of the box; origin plus size."
        return self._origin + self._size

    @property
    def volume(self):
        "The volume of the box in blocks"
        return self.size.x * self.size.y * self.size.z

    @property
    def positions(self):
        """iterate through all of the positions within this selection box"""
        return itertools.product(
            xrange(self.minx, self.maxx),
            xrange(self.miny, self.maxy),
            xrange(self.minz, self.maxz)
        )

    def intersect(self, box):
        """
        Return a box containing the area self and box have in common. Box will have zero volume
         if there is no common area.
        """
        if (self.minx > box.maxx or self.maxx < box.minx or
            self.miny > box.maxy or self.maxy < box.miny or
            self.minz > box.maxz or self.maxz < box.minz):
            #Zero size intersection.
            return BoundingBox()

        origin = Vector(
            max(self.minx, box.minx),
            max(self.miny, box.miny),
            max(self.minz, box.minz),
        )
        maximum = Vector(
            min(self.maxx, box.maxx),
            min(self.maxy, box.maxy),
            min(self.maxz, box.maxz),
        )

        #print "Intersect of {0} and {1}: {2}".format(self, box, newbox)
        return BoundingBox(origin, maximum - origin)

    def union(self, box):
        """
        Return a box large enough to contain both self and box.
        """
        origin = Vector(
            min(self.minx, box.minx),
            min(self.miny, box.miny),
            min(self.minz, box.minz),
        )
        maximum = Vector(
            max(self.maxx, box.maxx),
            max(self.maxy, box.maxy),
            max(self.maxz, box.maxz),
        )
        return BoundingBox(origin, maximum - origin)

    def expand(self, dx, dy=None, dz=None):
        """
        Return a new box with boundaries expanded by dx, dy, dz.
        If only dx is passed, expands by dx in all dimensions.
        """
        if dz is None:
            dz = dx
        if dy is None:
            dy = dx

        origin = self.origin - (dx, dy, dz)
        size = self.size + (dx * 2, dy * 2, dz * 2)

        return BoundingBox(origin, size)

    def __contains__(self, pos):
        x, y, z = pos
        if x < self.minx or x >= self.maxx:
            return False
        if y < self.miny or y >= self.maxy:
            return False
        if z < self.minz or z >= self.maxz:
            return False

        return True

    def __cmp__(self, b):
        return cmp((self.origin, self.size), (b.origin, b.size))


    # --- Chunk positions ---

    @property
    def mincx(self):
        "The smallest chunk position contained in this box"
        return self.origin.x >> 4

    @property
    def mincz(self):
        "The smallest chunk position contained in this box"
        return self.origin.z >> 4

    @property
    def maxcx(self):
        "The largest chunk position contained in this box"
        return ((self.origin.x + self.size.x - 1) >> 4) + 1

    @property
    def maxcz(self):
        "The largest chunk position contained in this box"
        return ((self.origin.z + self.size.z - 1) >> 4) + 1

    def chunkBox(self, level):
        """Returns this box extended to the chunk boundaries of the given level"""
        box = self
        return BoundingBox((box.mincx << 4, 0, box.mincz << 4),
                           (box.maxcx - box.mincx << 4, level.Height, box.maxcz - box.mincz << 4))

    @property
    def chunkPositions(self):
        #iterate through all of the chunk positions within this selection box
        return itertools.product(xrange(self.mincx, self.maxcx), xrange(self.mincz, self.maxcz))

    @property
    def chunkCount(self):
        return (self.maxcx - self.mincx) * (self.maxcz - self.mincz)

    @property
    def isChunkAligned(self):
        return (self.origin.x & 0xf == 0) and (self.origin.z & 0xf == 0)

class FloatBox (BoundingBox):
    type = float

########NEW FILE########
__FILENAME__ = cachefunc
# From http://code.activestate.com/recipes/498245/
import collections
import functools
from itertools import ifilterfalse
from heapq import nsmallest
from operator import itemgetter


class Counter(dict):
    'Mapping where default values are zero'

    def __missing__(self, key):
        return 0


def lru_cache(maxsize=100):
    '''Least-recently-used cache decorator.

    Arguments to the cached function must be hashable.
    Cache performance statistics stored in f.hits and f.misses.
    Clear the cache with f.clear().
    http://en.wikipedia.org/wiki/Cache_algorithms#Least_Recently_Used

    '''
    maxqueue = maxsize * 10

    def decorating_function(user_function,
            len=len, iter=iter, tuple=tuple, sorted=sorted, KeyError=KeyError):
        cache = {}                   # mapping of args to results
        queue = collections.deque()  # order that keys have been used
        refcount = Counter()         # times each key is in the queue
        sentinel = object()          # marker for looping around the queue
        kwd_mark = object()          # separate positional and keyword args

        # lookup optimizations (ugly but fast)
        queue_append, queue_popleft = queue.append, queue.popleft
        queue_appendleft, queue_pop = queue.appendleft, queue.pop

        @functools.wraps(user_function)
        def wrapper(*args, **kwds):
            # cache key records both positional and keyword args
            key = args
            if kwds:
                key += (kwd_mark,) + tuple(sorted(kwds.items()))

            # record recent use of this key
            queue_append(key)
            refcount[key] += 1

            # get cache entry or compute if not found
            try:
                result = cache[key]
                wrapper.hits += 1
            except KeyError:
                result = user_function(*args, **kwds)
                cache[key] = result
                wrapper.misses += 1

                # purge least recently used cache entry
                if len(cache) > maxsize:
                    key = queue_popleft()
                    refcount[key] -= 1
                    while refcount[key]:
                        key = queue_popleft()
                        refcount[key] -= 1
                    del cache[key], refcount[key]

            # periodically compact the queue by eliminating duplicate keys
            # while preserving order of most recent access
            if len(queue) > maxqueue:
                refcount.clear()
                queue_appendleft(sentinel)
                for key in ifilterfalse(refcount.__contains__,
                                        iter(queue_pop, sentinel)):
                    queue_appendleft(key)
                    refcount[key] = 1

            return result

        def clear():
            cache.clear()
            queue.clear()
            refcount.clear()
            wrapper.hits = wrapper.misses = 0

        wrapper.hits = wrapper.misses = 0
        wrapper.clear = clear
        return wrapper
    return decorating_function


def lfu_cache(maxsize=100):
    '''Least-frequenty-used cache decorator.

    Arguments to the cached function must be hashable.
    Cache performance statistics stored in f.hits and f.misses.
    Clear the cache with f.clear().
    http://en.wikipedia.org/wiki/Least_Frequently_Used

    '''

    def decorating_function(user_function):
        cache = {}                      # mapping of args to results
        use_count = Counter()           # times each key has been accessed
        kwd_mark = object()             # separate positional and keyword args

        @functools.wraps(user_function)
        def wrapper(*args, **kwds):
            key = args
            if kwds:
                key += (kwd_mark,) + tuple(sorted(kwds.items()))
            use_count[key] += 1

            # get cache entry or compute if not found
            try:
                result = cache[key]
                wrapper.hits += 1
            except KeyError:
                result = user_function(*args, **kwds)
                cache[key] = result
                wrapper.misses += 1

                # purge least frequently used cache entry
                if len(cache) > maxsize:
                    for key, _ in nsmallest(maxsize // 10,
                                            use_count.iteritems(),
                                            key=itemgetter(1)):
                        del cache[key], use_count[key]

            return result

        def clear():
            cache.clear()
            use_count.clear()
            wrapper.hits = wrapper.misses = 0

        wrapper.hits = wrapper.misses = 0
        wrapper.clear = clear
        return wrapper
    return decorating_function

if __name__ == '__main__':

    @lru_cache(maxsize=20)
    def f_lru(x, y):
        return 3 * x + y

    domain = range(5)
    from random import choice
    for i in range(1000):
        r = f_lru(choice(domain), choice(domain))

    print(f_lru.hits, f_lru.misses)

    @lfu_cache(maxsize=20)
    def f_lfu(x, y):
        return 3 * x + y

    domain = range(5)
    from random import choice
    for i in range(1000):
        r = f_lfu(choice(domain), choice(domain))

    print(f_lfu.hits, f_lfu.misses)

########NEW FILE########
__FILENAME__ = entity
'''
Created on Jul 23, 2011

@author: Rio
'''
from math import isnan

import nbt
from copy import deepcopy

__all__ = ["Entity", "TileEntity"]

class TileEntity(object):
    baseStructures = {
        "Furnace": (
            ("BurnTime", nbt.TAG_Short),
            ("CookTime", nbt.TAG_Short),
            ("Items", nbt.TAG_List),
        ),
        "Sign": (
            ("Items", nbt.TAG_List),
        ),
        "MobSpawner": (
            ("Items", nbt.TAG_List),
        ),
        "Chest": (
            ("Items", nbt.TAG_List),
        ),
        "Music": (
            ("note", nbt.TAG_Byte),
        ),
        "Trap": (
            ("Items", nbt.TAG_List),
        ),
        "RecordPlayer": (
            ("Record", nbt.TAG_Int),
        ),
        "Piston": (
            ("blockId", nbt.TAG_Int),
            ("blockData", nbt.TAG_Int),
            ("facing", nbt.TAG_Int),
            ("progress", nbt.TAG_Float),
            ("extending", nbt.TAG_Byte),
        ),
        "Cauldron": (
            ("Items", nbt.TAG_List),
            ("BrewTime", nbt.TAG_Int),
        ),
    }

    knownIDs = baseStructures.keys()
    maxItems = {
        "Furnace": 3,
        "Chest": 27,
        "Trap": 9,
        "Cauldron": 4,
    }
    slotNames = {
        "Furnace": {
            0: "Raw",
            1: "Fuel",
            2: "Product"
        },
        "Cauldron": {
            0: "Potion",
            1: "Potion",
            2: "Potion",
            3: "Reagent",
        }
    }

    @classmethod
    def Create(cls, tileEntityID, **kw):
        tileEntityTag = nbt.TAG_Compound()
        tileEntityTag["id"] = nbt.TAG_String(tileEntityID)
        base = cls.baseStructures.get(tileEntityID, None)
        if base:
            for (name, tag) in base:
                tileEntityTag[name] = tag()

        cls.setpos(tileEntityTag, (0, 0, 0))
        return tileEntityTag

    @classmethod
    def pos(cls, tag):
        return [tag[a].value for a in 'xyz']

    @classmethod
    def setpos(cls, tag, pos):
        for a, p in zip('xyz', pos):
            tag[a] = nbt.TAG_Int(p)

    @classmethod
    def copyWithOffset(cls, tileEntity, copyOffset):
        eTag = deepcopy(tileEntity)
        eTag['x'] = nbt.TAG_Int(tileEntity['x'].value + copyOffset[0])
        eTag['y'] = nbt.TAG_Int(tileEntity['y'].value + copyOffset[1])
        eTag['z'] = nbt.TAG_Int(tileEntity['z'].value + copyOffset[2])
        if eTag['id'].value == "Control":
            command = eTag['Command'].value

            # Adjust teleport command coordinates.
            # /tp <playername> <x> <y> <z>
            if command.startswith('/tp'):
                words = command.split(' ')
                if len(words) > 4:
                    x, y, z = words[2:5]

                    # Only adjust non-relative teleport coordinates.
                    # These coordinates can be either ints or floats. If ints, Minecraft adds
                    # 0.5 to the coordinate to center the player in the block.
                    # We need to preserve the int/float status or else the coordinates will shift.
                    # Note that copyOffset is always ints.

                    def num(x):
                        try:
                            return int(x)
                        except ValueError:
                            return float(x)

                    if x[0] != "~":
                        x = str(num(x) + copyOffset[0])
                    if y[0] != "~":
                        y = str(num(y) + copyOffset[1])
                    if z[0] != "~":
                        z = str(num(z) + copyOffset[2])

                    words[2:5] = x, y, z
                    eTag['Command'].value = ' '.join(words)

        return eTag


class Entity(object):
    monsters = ["Creeper",
                "Skeleton",
                "Spider",
                "CaveSpider",
                "Giant",
                "Zombie",
                "Slime",
                "PigZombie",
                "Ghast",
                "Pig",
                "Sheep",
                "Cow",
                "Chicken",
                "Squid",
                "Wolf",
                "Monster",
                "Enderman",
                "Silverfish",
                "Blaze",
                "Villager",
                "LavaSlime",
                "WitherBoss",
                ]
    projectiles = ["Arrow",
                   "Snowball",
                   "Egg",
                   "Fireball",
                   "SmallFireball",
                   "ThrownEnderpearl",
                   ]

    items = ["Item",
             "XPOrb",
             "Painting",
             "EnderCrystal",
             "ItemFrame",
             "WitherSkull",
             ]
    vehicles = ["Minecart", "Boat"]
    tiles = ["PrimedTnt", "FallingSand"]

    @classmethod
    def Create(cls, entityID, **kw):
        entityTag = nbt.TAG_Compound()
        entityTag["id"] = nbt.TAG_String(entityID)
        Entity.setpos(entityTag, (0, 0, 0))
        return entityTag

    @classmethod
    def pos(cls, tag):
        if "Pos" not in tag:
            raise InvalidEntity(tag)
        values = [a.value for a in tag["Pos"]]

        if isnan(values[0]) and 'xTile' in tag :
            values[0] = tag['xTile'].value
        if isnan(values[1]) and 'yTile' in tag:
            values[1] = tag['yTile'].value
        if isnan(values[2]) and 'zTile' in tag:
            values[2] = tag['zTile'].value

        return values

    @classmethod
    def setpos(cls, tag, pos):
        tag["Pos"] = nbt.TAG_List([nbt.TAG_Double(p) for p in pos])

    @classmethod
    def copyWithOffset(cls, entity, copyOffset):
        eTag = deepcopy(entity)

        positionTags = map(lambda p, co: nbt.TAG_Double(p.value + co), eTag["Pos"], copyOffset)
        eTag["Pos"] = nbt.TAG_List(positionTags)

        if eTag["id"].value in ("Painting", "ItemFrame"):
            eTag["TileX"].value += copyOffset[0]
            eTag["TileY"].value += copyOffset[1]
            eTag["TileZ"].value += copyOffset[2]

        return eTag


class InvalidEntity(ValueError):
    pass


class InvalidTileEntity(ValueError):
    pass

########NEW FILE########
__FILENAME__ = faces

FaceXIncreasing = 0
FaceXDecreasing = 1
FaceYIncreasing = 2
FaceYDecreasing = 3
FaceZIncreasing = 4
FaceZDecreasing = 5
MaxDirections = 6

faceDirections = (
                            (FaceXIncreasing, (1, 0, 0)),
                            (FaceXDecreasing, (-1, 0, 0)),
                            (FaceYIncreasing, (0, 1, 0)),
                            (FaceYDecreasing, (0, -1, 0)),
                            (FaceZIncreasing, (0, 0, 1)),
                            (FaceZDecreasing, (0, 0, -1))
                            )

########NEW FILE########
__FILENAME__ = gprof2dot
#!/usr/bin/env python
#
# Copyright 2008-2009 Jose Fonseca
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

"""Generate a dot graph from the output of several profilers."""

__author__ = "Jose Fonseca"

__version__ = "1.0"

import sys
import math
import os.path
import re
import textwrap
import optparse
import xml.parsers.expat


def times(x):
    return u"%u\xd7" % (x,)


def percentage(p):
    return "%.02f%%" % (p * 100.0,)


def add(a, b):
    return a + b


def equal(a, b):
    if a == b:
        return a
    else:
        return None


def fail(a, b):
    assert False

tol = 2 ** -23


def ratio(numerator, denominator):
    try:
        ratio = float(numerator) / float(denominator)
    except ZeroDivisionError:
        # 0 / 0 is undefined, but 1.0 yields more useful results
        return 1.0
    if ratio < 0.0:
        if ratio < -tol:
            sys.stderr.write('warning: negative ratio (%s/%s)\n' % (numerator, denominator))
        return 0.0
    if ratio > 1.0:
        if ratio > 1.0 + tol:
            sys.stderr.write('warning: ratio greater than one (%s/%s)\n' % (numerator, denominator))
        return 1.0
    return ratio


class UndefinedEvent(Exception):
    """Raised when attempting to get an event which is undefined."""

    def __init__(self, event):
        Exception.__init__(self)
        self.event = event

    def __str__(self):
        return 'unspecified event %s' % self.event.name


class Event(object):
    """Describe a kind of event, and its basic operations."""

    def __init__(self, name, null, aggregator, formatter=str):
        self.name = name
        self._null = null
        self._aggregator = aggregator
        self._formatter = formatter

    def __eq__(self, other):
        return self is other

    def __hash__(self):
        return id(self)

    def null(self):
        return self._null

    def aggregate(self, val1, val2):
        """Aggregate two event values."""
        assert val1 is not None
        assert val2 is not None
        return self._aggregator(val1, val2)

    def format(self, val):
        """Format an event value."""
        assert val is not None
        return self._formatter(val)

CALLS = Event("Calls", 0, add, times)
SAMPLES = Event("Samples", 0, add)
SAMPLES2 = Event("Samples", 0, add)

TIME = Event("Time", 0.0, add, lambda x: '(' + str(x) + ')')
TIME_RATIO = Event("Time ratio", 0.0, add, lambda x: '(' + percentage(x) + ')')
TOTAL_TIME = Event("Total time", 0.0, fail)
TOTAL_TIME_RATIO = Event("Total time ratio", 0.0, fail, percentage)


class Object(object):
    """Base class for all objects in profile which can store events."""

    def __init__(self, events=None):
        if events is None:
            self.events = {}
        else:
            self.events = events

    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        return self is other

    def __contains__(self, event):
        return event in self.events

    def __getitem__(self, event):
        try:
            return self.events[event]
        except KeyError:
            raise UndefinedEvent(event)

    def __setitem__(self, event, value):
        if value is None:
            if event in self.events:
                del self.events[event]
        else:
            self.events[event] = value


class Call(Object):
    """A call between functions.

    There should be at most one call object for every pair of functions.
    """

    def __init__(self, callee_id):
        Object.__init__(self)
        self.callee_id = callee_id
        self.ratio = None
        self.weight = None


class Function(Object):
    """A function."""

    def __init__(self, id, name):
        Object.__init__(self)
        self.id = id
        self.name = name
        self.module = None
        self.process = None
        self.calls = {}
        self.called = None
        self.weight = None
        self.cycle = None

    def add_call(self, call):
        if call.callee_id in self.calls:
            sys.stderr.write('warning: overwriting call from function %s to %s\n' % (str(self.id), str(call.callee_id)))
        self.calls[call.callee_id] = call

    # TODO: write utility functions

    def __repr__(self):
        return self.name


class Cycle(Object):
    """A cycle made from recursive function calls."""

    def __init__(self):
        Object.__init__(self)
        # XXX: Do cycles need an id?
        self.functions = set()

    def add_function(self, function):
        assert function not in self.functions
        self.functions.add(function)
        # XXX: Aggregate events?
        if function.cycle is not None:
            for other in function.cycle.functions:
                if function not in self.functions:
                    self.add_function(other)
        function.cycle = self


class Profile(Object):
    """The whole profile."""

    def __init__(self):
        Object.__init__(self)
        self.functions = {}
        self.cycles = []

    def add_function(self, function):
        if function.id in self.functions:
            sys.stderr.write('warning: overwriting function %s (id %s)\n' % (function.name, str(function.id)))
        self.functions[function.id] = function

    def add_cycle(self, cycle):
        self.cycles.append(cycle)

    def validate(self):
        """Validate the edges."""

        for function in self.functions.itervalues():
            for callee_id in function.calls.keys():
                assert function.calls[callee_id].callee_id == callee_id
                if callee_id not in self.functions:
                    sys.stderr.write('warning: call to undefined function %s from function %s\n' % (str(callee_id), function.name))
                    del function.calls[callee_id]

    def find_cycles(self):
        """Find cycles using Tarjan's strongly connected components algorithm."""

        # Apply the Tarjan's algorithm successively until all functions are visited
        visited = set()
        for function in self.functions.itervalues():
            if function not in visited:
                self._tarjan(function, 0, [], {}, {}, visited)
        cycles = []
        for function in self.functions.itervalues():
            if function.cycle is not None and function.cycle not in cycles:
                cycles.append(function.cycle)
        self.cycles = cycles
        if 0:
            for cycle in cycles:
                sys.stderr.write("Cycle:\n")
                for member in cycle.functions:
                    sys.stderr.write("\tFunction %s\n" % member.name)

    def _tarjan(self, function, order, stack, orders, lowlinks, visited):
        """Tarjan's strongly connected components algorithm.

        See also:
        - http://en.wikipedia.org/wiki/Tarjan's_strongly_connected_components_algorithm
        """

        visited.add(function)
        orders[function] = order
        lowlinks[function] = order
        order += 1
        pos = len(stack)
        stack.append(function)
        for call in function.calls.itervalues():
            callee = self.functions[call.callee_id]
            # TODO: use a set to optimize lookup
            if callee not in orders:
                order = self._tarjan(callee, order, stack, orders, lowlinks, visited)
                lowlinks[function] = min(lowlinks[function], lowlinks[callee])
            elif callee in stack:
                lowlinks[function] = min(lowlinks[function], orders[callee])
        if lowlinks[function] == orders[function]:
            # Strongly connected component found
            members = stack[pos:]
            del stack[pos:]
            if len(members) > 1:
                cycle = Cycle()
                for member in members:
                    cycle.add_function(member)
        return order

    def call_ratios(self, event):
        # Aggregate for incoming calls
        cycle_totals = {}
        for cycle in self.cycles:
            cycle_totals[cycle] = 0.0
        function_totals = {}
        for function in self.functions.itervalues():
            function_totals[function] = 0.0
        for function in self.functions.itervalues():
            for call in function.calls.itervalues():
                if call.callee_id != function.id:
                    callee = self.functions[call.callee_id]
                    function_totals[callee] += call[event]
                    if callee.cycle is not None and callee.cycle is not function.cycle:
                        cycle_totals[callee.cycle] += call[event]

        # Compute the ratios
        for function in self.functions.itervalues():
            for call in function.calls.itervalues():
                assert call.ratio is None
                if call.callee_id != function.id:
                    callee = self.functions[call.callee_id]
                    if callee.cycle is not None and callee.cycle is not function.cycle:
                        total = cycle_totals[callee.cycle]
                    else:
                        total = function_totals[callee]
                    call.ratio = ratio(call[event], total)

    def integrate(self, outevent, inevent):
        """Propagate function time ratio allong the function calls.

        Must be called after finding the cycles.

        See also:
        - http://citeseer.ist.psu.edu/graham82gprof.html
        """

        # Sanity checking
        assert outevent not in self
        for function in self.functions.itervalues():
            assert outevent not in function
            assert inevent in function
            for call in function.calls.itervalues():
                assert outevent not in call
                if call.callee_id != function.id:
                    assert call.ratio is not None

        # Aggregate the input for each cycle
        for cycle in self.cycles:
            total = inevent.null()
            for function in self.functions.itervalues():
                total = inevent.aggregate(total, function[inevent])
            self[inevent] = total

        # Integrate along the edges
        total = inevent.null()
        for function in self.functions.itervalues():
            total = inevent.aggregate(total, function[inevent])
            self._integrate_function(function, outevent, inevent)
        self[outevent] = total

    def _integrate_function(self, function, outevent, inevent):
        if function.cycle is not None:
            return self._integrate_cycle(function.cycle, outevent, inevent)
        else:
            if outevent not in function:
                total = function[inevent]
                for call in function.calls.itervalues():
                    if call.callee_id != function.id:
                        total += self._integrate_call(call, outevent, inevent)
                function[outevent] = total
            return function[outevent]

    def _integrate_call(self, call, outevent, inevent):
        assert outevent not in call
        assert call.ratio is not None
        callee = self.functions[call.callee_id]
        subtotal = call.ratio * self._integrate_function(callee, outevent, inevent)
        call[outevent] = subtotal
        return subtotal

    def _integrate_cycle(self, cycle, outevent, inevent):
        if outevent not in cycle:

            # Compute the outevent for the whole cycle
            total = inevent.null()
            for member in cycle.functions:
                subtotal = member[inevent]
                for call in member.calls.itervalues():
                    callee = self.functions[call.callee_id]
                    if callee.cycle is not cycle:
                        subtotal += self._integrate_call(call, outevent, inevent)
                total += subtotal
            cycle[outevent] = total

            # Compute the time propagated to callers of this cycle
            callees = {}
            for function in self.functions.itervalues():
                if function.cycle is not cycle:
                    for call in function.calls.itervalues():
                        callee = self.functions[call.callee_id]
                        if callee.cycle is cycle:
                            try:
                                callees[callee] += call.ratio
                            except KeyError:
                                callees[callee] = call.ratio

            for member in cycle.functions:
                member[outevent] = outevent.null()

            for callee, call_ratio in callees.iteritems():
                ranks = {}
                call_ratios = {}
                partials = {}
                self._rank_cycle_function(cycle, callee, 0, ranks)
                self._call_ratios_cycle(cycle, callee, ranks, call_ratios, set())
                partial = self._integrate_cycle_function(cycle, callee, call_ratio, partials, ranks, call_ratios, outevent, inevent)
                assert partial == max(partials.values())
                assert not total or abs(1.0 - partial / (call_ratio * total)) <= 0.001

        return cycle[outevent]

    def _rank_cycle_function(self, cycle, function, rank, ranks):
        if function not in ranks or ranks[function] > rank:
            ranks[function] = rank
            for call in function.calls.itervalues():
                if call.callee_id != function.id:
                    callee = self.functions[call.callee_id]
                    if callee.cycle is cycle:
                        self._rank_cycle_function(cycle, callee, rank + 1, ranks)

    def _call_ratios_cycle(self, cycle, function, ranks, call_ratios, visited):
        if function not in visited:
            visited.add(function)
            for call in function.calls.itervalues():
                if call.callee_id != function.id:
                    callee = self.functions[call.callee_id]
                    if callee.cycle is cycle:
                        if ranks[callee] > ranks[function]:
                            call_ratios[callee] = call_ratios.get(callee, 0.0) + call.ratio
                            self._call_ratios_cycle(cycle, callee, ranks, call_ratios, visited)

    def _integrate_cycle_function(self, cycle, function, partial_ratio, partials, ranks, call_ratios, outevent, inevent):
        if function not in partials:
            partial = partial_ratio * function[inevent]
            for call in function.calls.itervalues():
                if call.callee_id != function.id:
                    callee = self.functions[call.callee_id]
                    if callee.cycle is not cycle:
                        assert outevent in call
                        partial += partial_ratio * call[outevent]
                    else:
                        if ranks[callee] > ranks[function]:
                            callee_partial = self._integrate_cycle_function(cycle, callee, partial_ratio, partials, ranks, call_ratios, outevent, inevent)
                            call_ratio = ratio(call.ratio, call_ratios[callee])
                            call_partial = call_ratio * callee_partial
                            try:
                                call[outevent] += call_partial
                            except UndefinedEvent:
                                call[outevent] = call_partial
                            partial += call_partial
            partials[function] = partial
            try:
                function[outevent] += partial
            except UndefinedEvent:
                function[outevent] = partial
        return partials[function]

    def aggregate(self, event):
        """Aggregate an event for the whole profile."""

        total = event.null()
        for function in self.functions.itervalues():
            try:
                total = event.aggregate(total, function[event])
            except UndefinedEvent:
                return
        self[event] = total

    def ratio(self, outevent, inevent):
        assert outevent not in self
        assert inevent in self
        for function in self.functions.itervalues():
            assert outevent not in function
            assert inevent in function
            function[outevent] = ratio(function[inevent], self[inevent])
            for call in function.calls.itervalues():
                assert outevent not in call
                if inevent in call:
                    call[outevent] = ratio(call[inevent], self[inevent])
        self[outevent] = 1.0

    def prune(self, node_thres, edge_thres):
        """Prune the profile"""

        # compute the prune ratios
        for function in self.functions.itervalues():
            try:
                function.weight = function[TOTAL_TIME_RATIO]
            except UndefinedEvent:
                pass

            for call in function.calls.itervalues():
                callee = self.functions[call.callee_id]

                if TOTAL_TIME_RATIO in call:
                    # handle exact cases first
                    call.weight = call[TOTAL_TIME_RATIO]
                else:
                    try:
                        # make a safe estimate
                        call.weight = min(function[TOTAL_TIME_RATIO], callee[TOTAL_TIME_RATIO])
                    except UndefinedEvent:
                        pass

        # prune the nodes
        for function_id in self.functions.keys():
            function = self.functions[function_id]
            if function.weight is not None:
                if function.weight < node_thres:
                    del self.functions[function_id]

        # prune the egdes
        for function in self.functions.itervalues():
            for callee_id in function.calls.keys():
                call = function.calls[callee_id]
                if callee_id not in self.functions or call.weight is not None and call.weight < edge_thres:
                    del function.calls[callee_id]

    def dump(self):
        for function in self.functions.itervalues():
            sys.stderr.write('Function %s:\n' % (function.name,))
            self._dump_events(function.events)
            for call in function.calls.itervalues():
                callee = self.functions[call.callee_id]
                sys.stderr.write('  Call %s:\n' % (callee.name,))
                self._dump_events(call.events)
        for cycle in self.cycles:
            sys.stderr.write('Cycle:\n')
            self._dump_events(cycle.events)
            for function in cycle.functions:
                sys.stderr.write('  Function %s\n' % (function.name,))

    def _dump_events(self, events):
        for event, value in events.iteritems():
            sys.stderr.write('    %s: %s\n' % (event.name, event.format(value)))


class Struct:
    """Masquerade a dictionary with a structure-like behavior."""

    def __init__(self, attrs=None):
        if attrs is None:
            attrs = {}
        self.__dict__['_attrs'] = attrs

    def __getattr__(self, name):
        try:
            return self._attrs[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        self._attrs[name] = value

    def __str__(self):
        return str(self._attrs)

    def __repr__(self):
        return repr(self._attrs)


class ParseError(Exception):
    """Raised when parsing to signal mismatches."""

    def __init__(self, msg, line):
        self.msg = msg
        # TODO: store more source line information
        self.line = line

    def __str__(self):
        return '%s: %r' % (self.msg, self.line)


class Parser:
    """Parser interface."""

    def __init__(self):
        pass

    def parse(self):
        raise NotImplementedError


class LineParser(Parser):
    """Base class for parsers that read line-based formats."""

    def __init__(self, file):
        Parser.__init__(self)
        self._file = file
        self.__line = None
        self.__eof = False

    def readline(self):
        line = self._file.readline()
        if not line:
            self.__line = ''
            self.__eof = True
        self.__line = line.rstrip('\r\n')

    def lookahead(self):
        assert self.__line is not None
        return self.__line

    def consume(self):
        assert self.__line is not None
        line = self.__line
        self.readline()
        return line

    def eof(self):
        assert self.__line is not None
        return self.__eof

XML_ELEMENT_START, XML_ELEMENT_END, XML_CHARACTER_DATA, XML_EOF = range(4)


class XmlToken:

    def __init__(self, type, name_or_data, attrs=None, line=None, column=None):
        assert type in (XML_ELEMENT_START, XML_ELEMENT_END, XML_CHARACTER_DATA, XML_EOF)
        self.type = type
        self.name_or_data = name_or_data
        self.attrs = attrs
        self.line = line
        self.column = column

    def __str__(self):
        if self.type == XML_ELEMENT_START:
            return '<' + self.name_or_data + ' ...>'
        if self.type == XML_ELEMENT_END:
            return '</' + self.name_or_data + '>'
        if self.type == XML_CHARACTER_DATA:
            return self.name_or_data
        if self.type == XML_EOF:
            return 'end of file'
        assert 0


class XmlTokenizer:
    """Expat based XML tokenizer."""

    def __init__(self, fp, skip_ws=True):
        self.fp = fp
        self.tokens = []
        self.index = 0
        self.final = False
        self.skip_ws = skip_ws

        self.character_pos = 0, 0
        self.character_data = ''

        self.parser = xml.parsers.expat.ParserCreate()
        self.parser.StartElementHandler = self.handle_element_start
        self.parser.EndElementHandler = self.handle_element_end
        self.parser.CharacterDataHandler = self.handle_character_data

    def handle_element_start(self, name, attributes):
        self.finish_character_data()
        line, column = self.pos()
        token = XmlToken(XML_ELEMENT_START, name, attributes, line, column)
        self.tokens.append(token)

    def handle_element_end(self, name):
        self.finish_character_data()
        line, column = self.pos()
        token = XmlToken(XML_ELEMENT_END, name, None, line, column)
        self.tokens.append(token)

    def handle_character_data(self, data):
        if not self.character_data:
            self.character_pos = self.pos()
        self.character_data += data

    def finish_character_data(self):
        if self.character_data:
            if not self.skip_ws or not self.character_data.isspace():
                line, column = self.character_pos
                token = XmlToken(XML_CHARACTER_DATA, self.character_data, None, line, column)
                self.tokens.append(token)
            self.character_data = ''

    def next(self):
        size = 16 * 1024
        while self.index >= len(self.tokens) and not self.final:
            self.tokens = []
            self.index = 0
            data = self.fp.read(size)
            self.final = len(data) < size
            try:
                self.parser.Parse(data, self.final)
            except xml.parsers.expat.ExpatError, e:
                #if e.code == xml.parsers.expat.errors.XML_ERROR_NO_ELEMENTS:
                if e.code == 3:
                    pass
                else:
                    raise e
        if self.index >= len(self.tokens):
            line, column = self.pos()
            token = XmlToken(XML_EOF, None, None, line, column)
        else:
            token = self.tokens[self.index]
            self.index += 1
        return token

    def pos(self):
        return self.parser.CurrentLineNumber, self.parser.CurrentColumnNumber


class XmlTokenMismatch(Exception):

    def __init__(self, expected, found):
        self.expected = expected
        self.found = found

    def __str__(self):
        return '%u:%u: %s expected, %s found' % (self.found.line, self.found.column, str(self.expected), str(self.found))


class XmlParser(Parser):
    """Base XML document parser."""

    def __init__(self, fp):
        Parser.__init__(self)
        self.tokenizer = XmlTokenizer(fp)
        self.consume()

    def consume(self):
        self.token = self.tokenizer.next()

    def match_element_start(self, name):
        return self.token.type == XML_ELEMENT_START and self.token.name_or_data == name

    def match_element_end(self, name):
        return self.token.type == XML_ELEMENT_END and self.token.name_or_data == name

    def element_start(self, name):
        while self.token.type == XML_CHARACTER_DATA:
            self.consume()
        if self.token.type != XML_ELEMENT_START:
            raise XmlTokenMismatch(XmlToken(XML_ELEMENT_START, name), self.token)
        if self.token.name_or_data != name:
            raise XmlTokenMismatch(XmlToken(XML_ELEMENT_START, name), self.token)
        attrs = self.token.attrs
        self.consume()
        return attrs

    def element_end(self, name):
        while self.token.type == XML_CHARACTER_DATA:
            self.consume()
        if self.token.type != XML_ELEMENT_END:
            raise XmlTokenMismatch(XmlToken(XML_ELEMENT_END, name), self.token)
        if self.token.name_or_data != name:
            raise XmlTokenMismatch(XmlToken(XML_ELEMENT_END, name), self.token)
        self.consume()

    def character_data(self, strip=True):
        data = ''
        while self.token.type == XML_CHARACTER_DATA:
            data += self.token.name_or_data
            self.consume()
        if strip:
            data = data.strip()
        return data


class GprofParser(Parser):
    """Parser for GNU gprof output.

    See also:
    - Chapter "Interpreting gprof's Output" from the GNU gprof manual
      http://sourceware.org/binutils/docs-2.18/gprof/Call-Graph.html#Call-Graph
    - File "cg_print.c" from the GNU gprof source code
      http://sourceware.org/cgi-bin/cvsweb.cgi/~checkout~/src/gprof/cg_print.c?rev=1.12&cvsroot=src
    """

    def __init__(self, fp):
        Parser.__init__(self)
        self.fp = fp
        self.functions = {}
        self.cycles = {}

    def readline(self):
        line = self.fp.readline()
        if not line:
            sys.stderr.write('error: unexpected end of file\n')
            sys.exit(1)
        line = line.rstrip('\r\n')
        return line

    _int_re = re.compile(r'^\d+$')
    _float_re = re.compile(r'^\d+\.\d+$')

    def translate(self, mo):
        """Extract a structure from a match object, while translating the types in the process."""
        attrs = {}
        groupdict = mo.groupdict()
        for name, value in groupdict.iteritems():
            if value is None:
                value = None
            elif self._int_re.match(value):
                value = int(value)
            elif self._float_re.match(value):
                value = float(value)
            attrs[name] = value
        return Struct(attrs)

    _cg_header_re = re.compile(
        # original gprof header
        r'^\s+called/total\s+parents\s*$|' +
        r'^index\s+%time\s+self\s+descendents\s+called\+self\s+name\s+index\s*$|' +
        r'^\s+called/total\s+children\s*$|' +
        # GNU gprof header
        r'^index\s+%\s+time\s+self\s+children\s+called\s+name\s*$'
    )

    _cg_ignore_re = re.compile(
        # spontaneous
        r'^\s+<spontaneous>\s*$|'
        # internal calls (such as "mcount")
        r'^.*\((\d+)\)$'
    )

    _cg_primary_re = re.compile(
        r'^\[(?P<index>\d+)\]?' +
        r'\s+(?P<percentage_time>\d+\.\d+)' +
        r'\s+(?P<self>\d+\.\d+)' +
        r'\s+(?P<descendants>\d+\.\d+)' +
        r'\s+(?:(?P<called>\d+)(?:\+(?P<called_self>\d+))?)?' +
        r'\s+(?P<name>\S.*?)' +
        r'(?:\s+<cycle\s(?P<cycle>\d+)>)?' +
        r'\s\[(\d+)\]$'
    )

    _cg_parent_re = re.compile(
        r'^\s+(?P<self>\d+\.\d+)?' +
        r'\s+(?P<descendants>\d+\.\d+)?' +
        r'\s+(?P<called>\d+)(?:/(?P<called_total>\d+))?' +
        r'\s+(?P<name>\S.*?)' +
        r'(?:\s+<cycle\s(?P<cycle>\d+)>)?' +
        r'\s\[(?P<index>\d+)\]$'
    )

    _cg_child_re = _cg_parent_re

    _cg_cycle_header_re = re.compile(
        r'^\[(?P<index>\d+)\]?' +
        r'\s+(?P<percentage_time>\d+\.\d+)' +
        r'\s+(?P<self>\d+\.\d+)' +
        r'\s+(?P<descendants>\d+\.\d+)' +
        r'\s+(?:(?P<called>\d+)(?:\+(?P<called_self>\d+))?)?' +
        r'\s+<cycle\s(?P<cycle>\d+)\sas\sa\swhole>' +
        r'\s\[(\d+)\]$'
    )

    _cg_cycle_member_re = re.compile(
        r'^\s+(?P<self>\d+\.\d+)?' +
        r'\s+(?P<descendants>\d+\.\d+)?' +
        r'\s+(?P<called>\d+)(?:\+(?P<called_self>\d+))?' +
        r'\s+(?P<name>\S.*?)' +
        r'(?:\s+<cycle\s(?P<cycle>\d+)>)?' +
        r'\s\[(?P<index>\d+)\]$'
    )

    _cg_sep_re = re.compile(r'^--+$')

    def parse_function_entry(self, lines):
        parents = []
        children = []

        while True:
            if not lines:
                sys.stderr.write('warning: unexpected end of entry\n')
            line = lines.pop(0)
            if line.startswith('['):
                break

            # read function parent line
            mo = self._cg_parent_re.match(line)
            if not mo:
                if self._cg_ignore_re.match(line):
                    continue
                sys.stderr.write('warning: unrecognized call graph entry: %r\n' % line)
            else:
                parent = self.translate(mo)
                parents.append(parent)

        # read primary line
        mo = self._cg_primary_re.match(line)
        if not mo:
            sys.stderr.write('warning: unrecognized call graph entry: %r\n' % line)
            return
        else:
            function = self.translate(mo)

        while lines:
            line = lines.pop(0)

            # read function subroutine line
            mo = self._cg_child_re.match(line)
            if not mo:
                if self._cg_ignore_re.match(line):
                    continue
                sys.stderr.write('warning: unrecognized call graph entry: %r\n' % line)
            else:
                child = self.translate(mo)
                children.append(child)

        function.parents = parents
        function.children = children

        self.functions[function.index] = function

    def parse_cycle_entry(self, lines):

        # read cycle header line
        line = lines[0]
        mo = self._cg_cycle_header_re.match(line)
        if not mo:
            sys.stderr.write('warning: unrecognized call graph entry: %r\n' % line)
            return
        cycle = self.translate(mo)

        # read cycle member lines
        cycle.functions = []
        for line in lines[1:]:
            mo = self._cg_cycle_member_re.match(line)
            if not mo:
                sys.stderr.write('warning: unrecognized call graph entry: %r\n' % line)
                continue
            call = self.translate(mo)
            cycle.functions.append(call)

        self.cycles[cycle.cycle] = cycle

    def parse_cg_entry(self, lines):
        if lines[0].startswith("["):
            self.parse_cycle_entry(lines)
        else:
            self.parse_function_entry(lines)

    def parse_cg(self):
        """Parse the call graph."""

        # skip call graph header
        while not self._cg_header_re.match(self.readline()):
            pass
        line = self.readline()
        while self._cg_header_re.match(line):
            line = self.readline()

        # process call graph entries
        entry_lines = []
        while line != '\014':  # form feed
            if line and not line.isspace():
                if self._cg_sep_re.match(line):
                    self.parse_cg_entry(entry_lines)
                    entry_lines = []
                else:
                    entry_lines.append(line)
            line = self.readline()

    def parse(self):
        self.parse_cg()
        self.fp.close()

        profile = Profile()
        profile[TIME] = 0.0

        cycles = {}
        for index in self.cycles.iterkeys():
            cycles[index] = Cycle()

        for entry in self.functions.itervalues():
            # populate the function
            function = Function(entry.index, entry.name)
            function[TIME] = entry.self
            if entry.called is not None:
                function.called = entry.called
            if entry.called_self is not None:
                call = Call(entry.index)
                call[CALLS] = entry.called_self
                function.called += entry.called_self

            # populate the function calls
            for child in entry.children:
                call = Call(child.index)

                assert child.called is not None
                call[CALLS] = child.called

                if child.index not in self.functions:
                    # NOTE: functions that were never called but were discovered by gprof's
                    # static call graph analysis dont have a call graph entry so we need
                    # to add them here
                    missing = Function(child.index, child.name)
                    function[TIME] = 0.0
                    function.called = 0
                    profile.add_function(missing)

                function.add_call(call)

            profile.add_function(function)

            if entry.cycle is not None:
                try:
                    cycle = cycles[entry.cycle]
                except KeyError:
                    sys.stderr.write('warning: <cycle %u as a whole> entry missing\n' % entry.cycle)
                    cycle = Cycle()
                    cycles[entry.cycle] = cycle
                cycle.add_function(function)

            profile[TIME] = profile[TIME] + function[TIME]

        for cycle in cycles.itervalues():
            profile.add_cycle(cycle)

        # Compute derived events
        profile.validate()
        profile.ratio(TIME_RATIO, TIME)
        profile.call_ratios(CALLS)
        profile.integrate(TOTAL_TIME, TIME)
        profile.ratio(TOTAL_TIME_RATIO, TOTAL_TIME)

        return profile


class CallgrindParser(LineParser):
    """Parser for valgrind's callgrind tool.

    See also:
    - http://valgrind.org/docs/manual/cl-format.html
    """

    _call_re = re.compile('^calls=\s*(\d+)\s+((\d+|\+\d+|-\d+|\*)\s+)+$')

    def __init__(self, infile):
        LineParser.__init__(self, infile)

        # Textual positions
        self.position_ids = {}
        self.positions = {}

        # Numeric positions
        self.num_positions = 1
        self.cost_positions = ['line']
        self.last_positions = [0]

        # Events
        self.num_events = 0
        self.cost_events = []

        self.profile = Profile()
        self.profile[SAMPLES] = 0

    def parse(self):
        # read lookahead
        self.readline()

        self.parse_key('version')
        self.parse_key('creator')
        self.parse_part()

        # compute derived data
        self.profile.validate()
        self.profile.find_cycles()
        self.profile.ratio(TIME_RATIO, SAMPLES)
        self.profile.call_ratios(CALLS)
        self.profile.integrate(TOTAL_TIME_RATIO, TIME_RATIO)

        return self.profile

    def parse_part(self):
        while self.parse_header_line():
            pass
        while self.parse_body_line():
            pass
        return True

    def parse_header_line(self):
        return \
            self.parse_empty() or \
            self.parse_comment() or \
            self.parse_part_detail() or \
            self.parse_description() or \
            self.parse_event_specification() or \
            self.parse_cost_line_def() or \
            self.parse_cost_summary()

    _detail_keys = set(('cmd', 'pid', 'thread', 'part'))

    def parse_part_detail(self):
        return self.parse_keys(self._detail_keys)

    def parse_description(self):
        return self.parse_key('desc') is not None

    def parse_event_specification(self):
        event = self.parse_key('event')
        if event is None:
            return False
        return True

    def parse_cost_line_def(self):
        pair = self.parse_keys(('events', 'positions'))
        if pair is None:
            return False
        key, value = pair
        items = value.split()
        if key == 'events':
            self.num_events = len(items)
            self.cost_events = items
        if key == 'positions':
            self.num_positions = len(items)
            self.cost_positions = items
            self.last_positions = [0] * self.num_positions
        return True

    def parse_cost_summary(self):
        pair = self.parse_keys(('summary', 'totals'))
        if pair is None:
            return False
        return True

    def parse_body_line(self):
        return \
            self.parse_empty() or \
            self.parse_comment() or \
            self.parse_cost_line() or \
            self.parse_position_spec() or \
            self.parse_association_spec()

    _cost_re = re.compile(r'^(\d+|\+\d+|-\d+|\*)( \d+)+$')

    def parse_cost_line(self, calls=None):
        line = self.lookahead()
        mo = self._cost_re.match(line)
        if not mo:
            return False

        function = self.get_function()

        values = line.split(' ')
        assert len(values) == self.num_positions + self.num_events

        positions = values[0: self.num_positions]
        events = values[self.num_positions:]

        for i in range(self.num_positions):
            position = positions[i]
            if position == '*':
                position = self.last_positions[i]
            elif position[0] in '-+':
                position = self.last_positions[i] + int(position)
            else:
                position = int(position)
            self.last_positions[i] = position

        events = map(float, events)

        if calls is None:
            function[SAMPLES] += events[0]
            self.profile[SAMPLES] += events[0]
        else:
            callee = self.get_callee()
            callee.called += calls

            try:
                call = function.calls[callee.id]
            except KeyError:
                call = Call(callee.id)
                call[CALLS] = calls
                call[SAMPLES] = events[0]
                function.add_call(call)
            else:
                call[CALLS] += calls
                call[SAMPLES] += events[0]

        self.consume()
        return True

    def parse_association_spec(self):
        line = self.lookahead()
        if not line.startswith('calls='):
            return False

        _, values = line.split('=', 1)
        values = values.strip().split()
        calls = int(values[0])
        self.consume()

        self.parse_cost_line(calls)

        return True

    _position_re = re.compile('^(?P<position>c?(?:ob|fl|fi|fe|fn))=\s*(?:\((?P<id>\d+)\))?(?:\s*(?P<name>.+))?')

    _position_table_map = {
        'ob': 'ob',
        'fl': 'fl',
        'fi': 'fl',
        'fe': 'fl',
        'fn': 'fn',
        'cob': 'ob',
        'cfl': 'fl',
        'cfi': 'fl',
        'cfe': 'fl',
        'cfn': 'fn',
    }

    _position_map = {
        'ob': 'ob',
        'fl': 'fl',
        'fi': 'fl',
        'fe': 'fl',
        'fn': 'fn',
        'cob': 'cob',
        'cfl': 'cfl',
        'cfi': 'cfl',
        'cfe': 'cfl',
        'cfn': 'cfn',
    }

    def parse_position_spec(self):
        line = self.lookahead()
        mo = self._position_re.match(line)
        if not mo:
            return False

        position, id, name = mo.groups()
        if id:
            table = self._position_table_map[position]
            if name:
                self.position_ids[(table, id)] = name
            else:
                name = self.position_ids.get((table, id), '')
        self.positions[self._position_map[position]] = name
        self.consume()
        return True

    def parse_empty(self):
        line = self.lookahead()
        if line.strip():
            return False
        self.consume()
        return True

    def parse_comment(self):
        line = self.lookahead()
        if not line.startswith('#'):
            return False
        self.consume()
        return True

    _key_re = re.compile(r'^(\w+):')

    def parse_key(self, key):
        pair = self.parse_keys((key,))
        if not pair:
            return None
        key, value = pair
        return value

    def parse_keys(self, keys):
        line = self.lookahead()
        mo = self._key_re.match(line)
        if not mo:
            return None
        key, value = line.split(':', 1)
        if key not in keys:
            return None
        value = value.strip()
        self.consume()
        return key, value

    def make_function(self, module, filename, name):
        # FIXME: module and filename are not being tracked reliably
        #id = '|'.join((module, filename, name))
        id = name
        try:
            function = self.profile.functions[id]
        except KeyError:
            function = Function(id, name)
            function[SAMPLES] = 0
            function.called = 0
            self.profile.add_function(function)
        return function

    def get_function(self):
        module = self.positions.get('ob', '')
        filename = self.positions.get('fl', '')
        function = self.positions.get('fn', '')
        return self.make_function(module, filename, function)

    def get_callee(self):
        module = self.positions.get('cob', '')
        filename = self.positions.get('cfi', '')
        function = self.positions.get('cfn', '')
        return self.make_function(module, filename, function)


class OprofileParser(LineParser):
    """Parser for oprofile callgraph output.

    See also:
    - http://oprofile.sourceforge.net/doc/opreport.html#opreport-callgraph
    """

    _fields_re = {
        'samples': r'(\d+)',
        '%': r'(\S+)',
        'linenr info': r'(?P<source>\(no location information\)|\S+:\d+)',
        'image name': r'(?P<image>\S+(?:\s\(tgid:[^)]*\))?)',
        'app name': r'(?P<application>\S+)',
        'symbol name': r'(?P<symbol>\(no symbols\)|.+?)',
    }

    def __init__(self, infile):
        LineParser.__init__(self, infile)
        self.entries = {}
        self.entry_re = None

    def add_entry(self, callers, function, callees):
        try:
            entry = self.entries[function.id]
        except KeyError:
            self.entries[function.id] = (callers, function, callees)
        else:
            callers_total, function_total, callees_total = entry
            self.update_subentries_dict(callers_total, callers)
            function_total.samples += function.samples
            self.update_subentries_dict(callees_total, callees)

    def update_subentries_dict(self, totals, partials):
        for partial in partials.itervalues():
            try:
                total = totals[partial.id]
            except KeyError:
                totals[partial.id] = partial
            else:
                total.samples += partial.samples

    def parse(self):
        # read lookahead
        self.readline()

        self.parse_header()
        while self.lookahead():
            self.parse_entry()

        profile = Profile()

        # populate the profile
        profile[SAMPLES] = 0
        for _callers, _function, _callees in self.entries.itervalues():
            function = Function(_function.id, _function.name)
            function[SAMPLES] = _function.samples
            profile.add_function(function)
            profile[SAMPLES] += _function.samples

            if _function.application:
                function.process = os.path.basename(_function.application)
            if _function.image:
                function.module = os.path.basename(_function.image)

            total_callee_samples = 0
            for _callee in _callees.itervalues():
                total_callee_samples += _callee.samples

            for _callee in _callees.itervalues():
                if not _callee.self:
                    call = Call(_callee.id)
                    call[SAMPLES2] = _callee.samples
                    function.add_call(call)

        # compute derived data
        profile.validate()
        profile.find_cycles()
        profile.ratio(TIME_RATIO, SAMPLES)
        profile.call_ratios(SAMPLES2)
        profile.integrate(TOTAL_TIME_RATIO, TIME_RATIO)

        return profile

    def parse_header(self):
        while not self.match_header():
            self.consume()
        line = self.lookahead()
        fields = re.split(r'\s\s+', line)
        entry_re = r'^\s*' + r'\s+'.join([self._fields_re[field] for field in fields]) + r'(?P<self>\s+\[self\])?$'
        self.entry_re = re.compile(entry_re)
        self.skip_separator()

    def parse_entry(self):
        callers = self.parse_subentries()
        if self.match_primary():
            function = self.parse_subentry()
            if function is not None:
                callees = self.parse_subentries()
                self.add_entry(callers, function, callees)
        self.skip_separator()

    def parse_subentries(self):
        subentries = {}
        while self.match_secondary():
            subentry = self.parse_subentry()
            subentries[subentry.id] = subentry
        return subentries

    def parse_subentry(self):
        entry = Struct()
        line = self.consume()
        mo = self.entry_re.match(line)
        if not mo:
            raise ParseError('failed to parse', line)
        fields = mo.groupdict()
        entry.samples = int(mo.group(1))
        if 'source' in fields and fields['source'] != '(no location information)':
            source = fields['source']
            filename, lineno = source.split(':')
            entry.filename = filename
            entry.lineno = int(lineno)
        else:
            source = ''
            entry.filename = None
            entry.lineno = None
        entry.image = fields.get('image', '')
        entry.application = fields.get('application', '')
        if 'symbol' in fields and fields['symbol'] != '(no symbols)':
            entry.symbol = fields['symbol']
        else:
            entry.symbol = ''
        if entry.symbol.startswith('"') and entry.symbol.endswith('"'):
            entry.symbol = entry.symbol[1:-1]
        entry.id = ':'.join((entry.application, entry.image, source, entry.symbol))
        entry.self = fields.get('self', None) != None
        if entry.self:
            entry.id += ':self'
        if entry.symbol:
            entry.name = entry.symbol
        else:
            entry.name = entry.image
        return entry

    def skip_separator(self):
        while not self.match_separator():
            self.consume()
        self.consume()

    def match_header(self):
        line = self.lookahead()
        return line.startswith('samples')

    def match_separator(self):
        line = self.lookahead()
        return line == '-' * len(line)

    def match_primary(self):
        line = self.lookahead()
        return not line[:1].isspace()

    def match_secondary(self):
        line = self.lookahead()
        return line[:1].isspace()


class SysprofParser(XmlParser):

    def __init__(self, stream):
        XmlParser.__init__(self, stream)

    def parse(self):
        objects = {}
        nodes = {}

        self.element_start('profile')
        while self.token.type == XML_ELEMENT_START:
            if self.token.name_or_data == 'objects':
                assert not objects
                objects = self.parse_items('objects')
            elif self.token.name_or_data == 'nodes':
                assert not nodes
                nodes = self.parse_items('nodes')
            else:
                self.parse_value(self.token.name_or_data)
        self.element_end('profile')

        return self.build_profile(objects, nodes)

    def parse_items(self, name):
        assert name[-1] == 's'
        items = {}
        self.element_start(name)
        while self.token.type == XML_ELEMENT_START:
            id, values = self.parse_item(name[:-1])
            assert id not in items
            items[id] = values
        self.element_end(name)
        return items

    def parse_item(self, name):
        attrs = self.element_start(name)
        id = int(attrs['id'])
        values = self.parse_values()
        self.element_end(name)
        return id, values

    def parse_values(self):
        values = {}
        while self.token.type == XML_ELEMENT_START:
            name = self.token.name_or_data
            value = self.parse_value(name)
            assert name not in values
            values[name] = value
        return values

    def parse_value(self, tag):
        self.element_start(tag)
        value = self.character_data()
        self.element_end(tag)
        if value.isdigit():
            return int(value)
        if value.startswith('"') and value.endswith('"'):
            return value[1:-1]
        return value

    def build_profile(self, objects, nodes):
        profile = Profile()

        profile[SAMPLES] = 0
        for id, object in objects.iteritems():
            # Ignore fake objects (process names, modules, "Everything", "kernel", etc.)
            if object['self'] == 0:
                continue

            function = Function(id, object['name'])
            function[SAMPLES] = object['self']
            profile.add_function(function)
            profile[SAMPLES] += function[SAMPLES]

        for id, node in nodes.iteritems():
            # Ignore fake calls
            if node['self'] == 0:
                continue

            # Find a non-ignored parent
            parent_id = node['parent']
            while parent_id != 0:
                parent = nodes[parent_id]
                caller_id = parent['object']
                if objects[caller_id]['self'] != 0:
                    break
                parent_id = parent['parent']
            if parent_id == 0:
                continue

            callee_id = node['object']

            assert objects[caller_id]['self']
            assert objects[callee_id]['self']

            function = profile.functions[caller_id]

            samples = node['self']
            try:
                call = function.calls[callee_id]
            except KeyError:
                call = Call(callee_id)
                call[SAMPLES2] = samples
                function.add_call(call)
            else:
                call[SAMPLES2] += samples

        # Compute derived events
        profile.validate()
        profile.find_cycles()
        profile.ratio(TIME_RATIO, SAMPLES)
        profile.call_ratios(SAMPLES2)
        profile.integrate(TOTAL_TIME_RATIO, TIME_RATIO)

        return profile


class SharkParser(LineParser):
    """Parser for MacOSX Shark output.

    Author: tom@dbservice.com
    """

    def __init__(self, infile):
        LineParser.__init__(self, infile)
        self.stack = []
        self.entries = {}

    def add_entry(self, function):
        try:
            entry = self.entries[function.id]
        except KeyError:
            self.entries[function.id] = (function, {})
        else:
            function_total, callees_total = entry
            function_total.samples += function.samples

    def add_callee(self, function, callee):
        func, callees = self.entries[function.id]
        try:
            entry = callees[callee.id]
        except KeyError:
            callees[callee.id] = callee
        else:
            entry.samples += callee.samples

    def parse(self):
        self.readline()
        self.readline()
        self.readline()
        self.readline()

        match = re.compile(r'(?P<prefix>[|+ ]*)(?P<samples>\d+), (?P<symbol>[^,]+), (?P<image>.*)')

        while self.lookahead():
            line = self.consume()
            mo = match.match(line)
            if not mo:
                raise ParseError('failed to parse', line)

            fields = mo.groupdict()
            prefix = len(fields.get('prefix', 0)) / 2 - 1

            symbol = str(fields.get('symbol', 0))
            image = str(fields.get('image', 0))

            entry = Struct()
            entry.id = ':'.join([symbol, image])
            entry.samples = int(fields.get('samples', 0))

            entry.name = symbol
            entry.image = image

            # adjust the callstack
            if prefix < len(self.stack):
                del self.stack[prefix:]

            if prefix == len(self.stack):
                self.stack.append(entry)

            # if the callstack has had an entry, it's this functions caller
            if prefix > 0:
                self.add_callee(self.stack[prefix - 1], entry)

            self.add_entry(entry)

        profile = Profile()
        profile[SAMPLES] = 0
        for _function, _callees in self.entries.itervalues():
            function = Function(_function.id, _function.name)
            function[SAMPLES] = _function.samples
            profile.add_function(function)
            profile[SAMPLES] += _function.samples

            if _function.image:
                function.module = os.path.basename(_function.image)

            for _callee in _callees.itervalues():
                call = Call(_callee.id)
                call[SAMPLES] = _callee.samples
                function.add_call(call)

        # compute derived data
        profile.validate()
        profile.find_cycles()
        profile.ratio(TIME_RATIO, SAMPLES)
        profile.call_ratios(SAMPLES)
        profile.integrate(TOTAL_TIME_RATIO, TIME_RATIO)

        return profile


class XPerfParser(Parser):
    """Parser for CSVs generted by XPerf, from Microsoft Windows Performance Tools.
    """

    def __init__(self, stream):
        Parser.__init__(self)
        self.stream = stream
        self.profile = Profile()
        self.profile[SAMPLES] = 0
        self.column = {}

    def parse(self):
        import csv
        reader = csv.reader(
            self.stream,
            delimiter=',',
            quotechar=None,
            escapechar=None,
            doublequote=False,
            skipinitialspace=True,
            lineterminator='\r\n',
            quoting=csv.QUOTE_NONE)
        it = iter(reader)
        row = reader.next()
        self.parse_header(row)
        for row in it:
            self.parse_row(row)

        # compute derived data
        self.profile.validate()
        self.profile.find_cycles()
        self.profile.ratio(TIME_RATIO, SAMPLES)
        self.profile.call_ratios(SAMPLES2)
        self.profile.integrate(TOTAL_TIME_RATIO, TIME_RATIO)

        return self.profile

    def parse_header(self, row):
        for column in range(len(row)):
            name = row[column]
            assert name not in self.column
            self.column[name] = column

    def parse_row(self, row):
        fields = {}
        for name, column in self.column.iteritems():
            value = row[column]
            for factory in int, float:
                try:
                    value = factory(value)
                except ValueError:
                    pass
                else:
                    break
            fields[name] = value

        process = fields['Process Name']
        symbol = fields['Module'] + '!' + fields['Function']
        weight = fields['Weight']
        count = fields['Count']

        function = self.get_function(process, symbol)
        function[SAMPLES] += weight * count
        self.profile[SAMPLES] += weight * count

        stack = fields['Stack']
        if stack != '?':
            stack = stack.split('/')
            assert stack[0] == '[Root]'
            if stack[-1] != symbol:
                # XXX: some cases the sampled function does not appear in the stack
                stack.append(symbol)
            caller = None
            for symbol in stack[1:]:
                callee = self.get_function(process, symbol)
                if caller is not None:
                    try:
                        call = caller.calls[callee.id]
                    except KeyError:
                        call = Call(callee.id)
                        call[SAMPLES2] = count
                        caller.add_call(call)
                    else:
                        call[SAMPLES2] += count
                caller = callee

    def get_function(self, process, symbol):
        function_id = process + '!' + symbol

        try:
            function = self.profile.functions[function_id]
        except KeyError:
            module, name = symbol.split('!', 1)
            function = Function(function_id, name)
            function.process = process
            function.module = module
            function[SAMPLES] = 0
            self.profile.add_function(function)

        return function


class SleepyParser(Parser):
    """Parser for GNU gprof output.

    See also:
    - http://www.codersnotes.com/sleepy/
    - http://sleepygraph.sourceforge.net/
    """

    def __init__(self, filename):
        Parser.__init__(self)

        from zipfile import ZipFile

        self.database = ZipFile(filename)

        self.symbols = {}
        self.calls = {}

        self.profile = Profile()

    _symbol_re = re.compile(
        r'^(?P<id>\w+)' +
        r'\s+"(?P<module>[^"]*)"' +
        r'\s+"(?P<procname>[^"]*)"' +
        r'\s+"(?P<sourcefile>[^"]*)"' +
        r'\s+(?P<sourceline>\d+)$'
    )

    def parse_symbols(self):
        lines = self.database.read('symbols.txt').splitlines()
        for line in lines:
            mo = self._symbol_re.match(line)
            if mo:
                symbol_id, module, procname, sourcefile, sourceline = mo.groups()

                function_id = ':'.join([module, procname])

                try:
                    function = self.profile.functions[function_id]
                except KeyError:
                    function = Function(function_id, procname)
                    function.module = module
                    function[SAMPLES] = 0
                    self.profile.add_function(function)

                self.symbols[symbol_id] = function

    def parse_callstacks(self):
        lines = self.database.read("callstacks.txt").splitlines()
        for line in lines:
            fields = line.split()
            samples = int(fields[0])
            callstack = fields[1:]

            callstack = [self.symbols[symbol_id] for symbol_id in callstack]

            callee = callstack[0]

            callee[SAMPLES] += samples
            self.profile[SAMPLES] += samples

            for caller in callstack[1:]:
                try:
                    call = caller.calls[callee.id]
                except KeyError:
                    call = Call(callee.id)
                    call[SAMPLES2] = samples
                    caller.add_call(call)
                else:
                    call[SAMPLES2] += samples

                callee = caller

    def parse(self):
        profile = self.profile
        profile[SAMPLES] = 0

        self.parse_symbols()
        self.parse_callstacks()

        # Compute derived events
        profile.validate()
        profile.find_cycles()
        profile.ratio(TIME_RATIO, SAMPLES)
        profile.call_ratios(SAMPLES2)
        profile.integrate(TOTAL_TIME_RATIO, TIME_RATIO)

        return profile


class AQtimeTable:

    def __init__(self, name, fields):
        self.name = name

        self.fields = fields
        self.field_column = {}
        for column in range(len(fields)):
            self.field_column[fields[column]] = column
        self.rows = []

    def __len__(self):
        return len(self.rows)

    def __iter__(self):
        for values, children in self.rows:
            fields = {}
            for name, value in zip(self.fields, values):
                fields[name] = value
            children = dict([(child.name, child) for child in children])
            yield fields, children
        raise StopIteration

    def add_row(self, values, children=()):
        self.rows.append((values, children))


class AQtimeParser(XmlParser):

    def __init__(self, stream):
        XmlParser.__init__(self, stream)
        self.tables = {}

    def parse(self):
        self.element_start('AQtime_Results')
        self.parse_headers()
        results = self.parse_results()
        self.element_end('AQtime_Results')
        return self.build_profile(results)

    def parse_headers(self):
        self.element_start('HEADERS')
        while self.token.type == XML_ELEMENT_START:
            self.parse_table_header()
        self.element_end('HEADERS')

    def parse_table_header(self):
        attrs = self.element_start('TABLE_HEADER')
        name = attrs['NAME']
        id = int(attrs['ID'])
        field_types = []
        field_names = []
        while self.token.type == XML_ELEMENT_START:
            field_type, field_name = self.parse_table_field()
            field_types.append(field_type)
            field_names.append(field_name)
        self.element_end('TABLE_HEADER')
        self.tables[id] = name, field_types, field_names

    def parse_table_field(self):
        attrs = self.element_start('TABLE_FIELD')
        type = attrs['TYPE']
        name = self.character_data()
        self.element_end('TABLE_FIELD')
        return type, name

    def parse_results(self):
        self.element_start('RESULTS')
        table = self.parse_data()
        self.element_end('RESULTS')
        return table

    def parse_data(self):
        attrs = self.element_start('DATA')
        table_id = int(attrs['TABLE_ID'])
        table_name, field_types, field_names = self.tables[table_id]
        table = AQtimeTable(table_name, field_names)
        while self.token.type == XML_ELEMENT_START:
            row, children = self.parse_row(field_types)
            table.add_row(row, children)
        self.element_end('DATA')
        return table

    def parse_row(self, field_types):
        row = [None] * len(field_types)
        children = []
        self.element_start('ROW')
        while self.token.type == XML_ELEMENT_START:
            if self.token.name_or_data == 'FIELD':
                field_id, field_value = self.parse_field(field_types)
                row[field_id] = field_value
            elif self.token.name_or_data == 'CHILDREN':
                children = self.parse_children()
            else:
                raise XmlTokenMismatch("<FIELD ...> or <CHILDREN ...>", self.token)
        self.element_end('ROW')
        return row, children

    def parse_field(self, field_types):
        attrs = self.element_start('FIELD')
        id = int(attrs['ID'])
        type = field_types[id]
        value = self.character_data()
        if type == 'Integer':
            value = int(value)
        elif type == 'Float':
            value = float(value)
        elif type == 'Address':
            value = int(value)
        elif type == 'String':
            pass
        else:
            assert False
        self.element_end('FIELD')
        return id, value

    def parse_children(self):
        children = []
        self.element_start('CHILDREN')
        while self.token.type == XML_ELEMENT_START:
            table = self.parse_data()
            assert table.name not in children
            children.append(table)
        self.element_end('CHILDREN')
        return children

    def build_profile(self, results):
        assert results.name == 'Routines'
        profile = Profile()
        profile[TIME] = 0.0
        for fields, tables in results:
            function = self.build_function(fields)
            children = tables['Children']
            for fields, _ in children:
                call = self.build_call(fields)
                function.add_call(call)
            profile.add_function(function)
            profile[TIME] = profile[TIME] + function[TIME]
        profile[TOTAL_TIME] = profile[TIME]
        profile.ratio(TOTAL_TIME_RATIO, TOTAL_TIME)
        return profile

    def build_function(self, fields):
        function = Function(self.build_id(fields), self.build_name(fields))
        function[TIME] = fields['Time']
        function[TOTAL_TIME] = fields['Time with Children']
        #function[TIME_RATIO] = fields['% Time'] / 100.0
        #function[TOTAL_TIME_RATIO] = fields['% with Children'] / 100.0
        return function

    def build_call(self, fields):
        call = Call(self.build_id(fields))
        call[TIME] = fields['Time']
        call[TOTAL_TIME] = fields['Time with Children']
        #call[TIME_RATIO] = fields['% Time'] / 100.0
        #call[TOTAL_TIME_RATIO] = fields['% with Children'] / 100.0
        return call

    def build_id(self, fields):
        return ':'.join([fields['Module Name'], fields['Unit Name'], fields['Routine Name']])

    def build_name(self, fields):
        # TODO: use more fields
        return fields['Routine Name']


class PstatsParser:
    """Parser python profiling statistics saved with te pstats module."""

    def __init__(self, *filename):
        import pstats
        try:
            self.stats = pstats.Stats(*filename)
        except ValueError, e:
            sys.stderr.write("ERROR: {0}".format(e))
            import hotshot.stats
            self.stats = hotshot.stats.load(filename[0])
        self.profile = Profile()
        self.function_ids = {}

    def get_function_name(self, (filename, line, name)):
        module = os.path.splitext(filename)[0]
        module = os.path.basename(module)
        return "%s:%d:%s" % (module, line, name)

    def get_function(self, key):
        try:
            id = self.function_ids[key]
        except KeyError:
            id = len(self.function_ids)
            name = self.get_function_name(key)
            function = Function(id, name)
            self.profile.functions[id] = function
            self.function_ids[key] = id
        else:
            function = self.profile.functions[id]
        return function

    def parse(self):
        self.profile[TIME] = 0.0
        self.profile[TOTAL_TIME] = self.stats.total_tt
        for fn, (cc, nc, tt, ct, callers) in self.stats.stats.iteritems():
            callee = self.get_function(fn)
            callee.called = nc
            callee[TOTAL_TIME] = ct
            callee[TIME] = tt
            self.profile[TIME] += tt
            self.profile[TOTAL_TIME] = max(self.profile[TOTAL_TIME], ct)
            for fn, value in callers.iteritems():
                caller = self.get_function(fn)
                call = Call(callee.id)
                if isinstance(value, tuple):
                    for i in xrange(0, len(value), 4):
                        nc, cc, tt, ct = value[i:i + 4]
                        if CALLS in call:
                            call[CALLS] += cc
                        else:
                            call[CALLS] = cc

                        if TOTAL_TIME in call:
                            call[TOTAL_TIME] += ct
                        else:
                            call[TOTAL_TIME] = ct

                else:
                    call[CALLS] = value
                    call[TOTAL_TIME] = ratio(value, nc) * ct

                caller.add_call(call)
        #self.stats.print_stats()
        #self.stats.print_callees()

        # Compute derived events
        self.profile.validate()
        self.profile.ratio(TIME_RATIO, TIME)
        self.profile.ratio(TOTAL_TIME_RATIO, TOTAL_TIME)

        return self.profile


class Theme:

    def __init__(self,
            bgcolor=(0.0, 0.0, 1.0),
            mincolor=(0.0, 0.0, 0.0),
            maxcolor=(0.0, 0.0, 1.0),
            fontname="Arial",
            minfontsize=10.0,
            maxfontsize=10.0,
            minpenwidth=0.5,
            maxpenwidth=4.0,
            gamma=2.2,
            skew=1.0):
        self.bgcolor = bgcolor
        self.mincolor = mincolor
        self.maxcolor = maxcolor
        self.fontname = fontname
        self.minfontsize = minfontsize
        self.maxfontsize = maxfontsize
        self.minpenwidth = minpenwidth
        self.maxpenwidth = maxpenwidth
        self.gamma = gamma
        self.skew = skew

    def graph_bgcolor(self):
        return self.hsl_to_rgb(*self.bgcolor)

    def graph_fontname(self):
        return self.fontname

    def graph_fontsize(self):
        return self.minfontsize

    def node_bgcolor(self, weight):
        return self.color(weight)

    def node_fgcolor(self, weight):
        return self.graph_bgcolor()

    def node_fontsize(self, weight):
        return self.fontsize(weight)

    def edge_color(self, weight):
        return self.color(weight)

    def edge_fontsize(self, weight):
        return self.fontsize(weight)

    def edge_penwidth(self, weight):
        return max(weight * self.maxpenwidth, self.minpenwidth)

    def edge_arrowsize(self, weight):
        return 0.5 * math.sqrt(self.edge_penwidth(weight))

    def fontsize(self, weight):
        return max(weight ** 2 * self.maxfontsize, self.minfontsize)

    def color(self, weight):
        weight = min(max(weight, 0.0), 1.0)

        hmin, smin, lmin = self.mincolor
        hmax, smax, lmax = self.maxcolor

        if self.skew < 0:
            raise ValueError("Skew must be greater than 0")
        elif self.skew == 1.0:
            h = hmin + weight * (hmax - hmin)
            s = smin + weight * (smax - smin)
            l = lmin + weight * (lmax - lmin)
        else:
            base = self.skew
            h = hmin + ((hmax - hmin) * (-1.0 + (base ** weight)) / (base - 1.0))
            s = smin + ((smax - smin) * (-1.0 + (base ** weight)) / (base - 1.0))
            l = lmin + ((lmax - lmin) * (-1.0 + (base ** weight)) / (base - 1.0))

        return self.hsl_to_rgb(h, s, l)

    def hsl_to_rgb(self, h, s, l):
        """Convert a color from HSL color-model to RGB.

        See also:
        - http://www.w3.org/TR/css3-color/#hsl-color
        """

        h = h % 1.0
        s = min(max(s, 0.0), 1.0)
        l = min(max(l, 0.0), 1.0)

        if l <= 0.5:
            m2 = l * (s + 1.0)
        else:
            m2 = l + s - l * s
        m1 = l * 2.0 - m2
        r = self._hue_to_rgb(m1, m2, h + 1.0 / 3.0)
        g = self._hue_to_rgb(m1, m2, h)
        b = self._hue_to_rgb(m1, m2, h - 1.0 / 3.0)

        # Apply gamma correction
        r **= self.gamma
        g **= self.gamma
        b **= self.gamma

        return r, g, b

    def _hue_to_rgb(self, m1, m2, h):
        if h < 0.0:
            h += 1.0
        elif h > 1.0:
            h -= 1.0
        if h * 6 < 1.0:
            return m1 + (m2 - m1) * h * 6.0
        elif h * 2 < 1.0:
            return m2
        elif h * 3 < 2.0:
            return m1 + (m2 - m1) * (2.0 / 3.0 - h) * 6.0
        else:
            return m1

TEMPERATURE_COLORMAP = Theme(
    mincolor=(2.0 / 3.0, 0.80, 0.25),  # dark blue
    maxcolor=(0.0, 1.0, 0.5),  # satured red
    gamma=1.0
)

PINK_COLORMAP = Theme(
    mincolor=(0.0, 1.0, 0.90),  # pink
    maxcolor=(0.0, 1.0, 0.5),  # satured red
)

GRAY_COLORMAP = Theme(
    mincolor=(0.0, 0.0, 0.85),  # light gray
    maxcolor=(0.0, 0.0, 0.0),  # black
)

BW_COLORMAP = Theme(
    minfontsize=8.0,
    maxfontsize=24.0,
    mincolor=(0.0, 0.0, 0.0),  # black
    maxcolor=(0.0, 0.0, 0.0),  # black
    minpenwidth=0.1,
    maxpenwidth=8.0,
)


class DotWriter:
    """Writer for the DOT language.

    See also:
    - "The DOT Language" specification
      http://www.graphviz.org/doc/info/lang.html
    """

    def __init__(self, fp):
        self.fp = fp

    def graph(self, profile, theme):
        self.begin_graph()

        fontname = theme.graph_fontname()

        self.attr('graph', fontname=fontname, ranksep=0.25, nodesep=0.125)
        self.attr('node', fontname=fontname, shape="box", style="filled", fontcolor="white", width=0, height=0)
        self.attr('edge', fontname=fontname)

        for function in profile.functions.itervalues():
            labels = []
            if function.process is not None:
                labels.append(function.process)
            if function.module is not None:
                labels.append(function.module)
            labels.append(function.name)
            for event in TOTAL_TIME_RATIO, TIME_RATIO:
                if event in function.events:
                    label = event.format(function[event])
                    labels.append(label)
            if function.called is not None:
                labels.append(u"%u\xd7" % (function.called,))

            if function.weight is not None:
                weight = function.weight
            else:
                weight = 0.0

            label = '\n'.join(labels)
            self.node(function.id,
                label=label,
                color=self.color(theme.node_bgcolor(weight)),
                fontcolor=self.color(theme.node_fgcolor(weight)),
                fontsize="%.2f" % theme.node_fontsize(weight),
            )

            for call in function.calls.itervalues():
                callee = profile.functions[call.callee_id]

                labels = []
                for event in TOTAL_TIME_RATIO, CALLS:
                    if event in call.events:
                        label = event.format(call[event])
                        labels.append(label)

                if call.weight is not None:
                    weight = call.weight
                elif callee.weight is not None:
                    weight = callee.weight
                else:
                    weight = 0.0

                label = '\n'.join(labels)

                self.edge(function.id, call.callee_id,
                    label=label,
                    color=self.color(theme.edge_color(weight)),
                    fontcolor=self.color(theme.edge_color(weight)),
                    fontsize="%.2f" % theme.edge_fontsize(weight),
                    penwidth="%.2f" % theme.edge_penwidth(weight),
                    labeldistance="%.2f" % theme.edge_penwidth(weight),
                    arrowsize="%.2f" % theme.edge_arrowsize(weight),
                )

        self.end_graph()

    def begin_graph(self):
        self.write('digraph {\n')

    def end_graph(self):
        self.write('}\n')

    def attr(self, what, **attrs):
        self.write("\t")
        self.write(what)
        self.attr_list(attrs)
        self.write(";\n")

    def node(self, node, **attrs):
        self.write("\t")
        self.id(node)
        self.attr_list(attrs)
        self.write(";\n")

    def edge(self, src, dst, **attrs):
        self.write("\t")
        self.id(src)
        self.write(" -> ")
        self.id(dst)
        self.attr_list(attrs)
        self.write(";\n")

    def attr_list(self, attrs):
        if not attrs:
            return
        self.write(' [')
        first = True
        for name, value in attrs.iteritems():
            if first:
                first = False
            else:
                self.write(", ")
            self.id(name)
            self.write('=')
            self.id(value)
        self.write(']')

    def id(self, id):
        if isinstance(id, (int, float)):
            s = str(id)
        elif isinstance(id, basestring):
            if id.isalnum() and not id.startswith('0x'):
                s = id
            else:
                s = self.escape(id)
        else:
            raise TypeError
        self.write(s)

    def color(self, (r, g, b)):

        def float2int(f):
            if f <= 0.0:
                return 0
            if f >= 1.0:
                return 255
            return int(255.0 * f + 0.5)

        return "#" + "".join(["%02x" % float2int(c) for c in (r, g, b)])

    def escape(self, s):
        s = s.encode('utf-8')
        s = s.replace('\\', r'\\')
        s = s.replace('\n', r'\n')
        s = s.replace('\t', r'\t')
        s = s.replace('"', r'\"')
        return '"' + s + '"'

    def write(self, s):
        self.fp.write(s)


class Main:
    """Main program."""

    themes = {
            "color": TEMPERATURE_COLORMAP,
            "pink": PINK_COLORMAP,
            "gray": GRAY_COLORMAP,
            "bw": BW_COLORMAP,
    }

    def main(self):
        """Main program."""

        parser = optparse.OptionParser(
            usage="\n\t%prog [options] [file] ...",
            version="%%prog %s" % __version__)
        parser.add_option(
            '-o', '--output', metavar='FILE',
            type="string", dest="output",
            help="output filename [stdout]")
        parser.add_option(
            '-n', '--node-thres', metavar='PERCENTAGE',
            type="float", dest="node_thres", default=0.5,
            help="eliminate nodes below this threshold [default: %default]")
        parser.add_option(
            '-e', '--edge-thres', metavar='PERCENTAGE',
            type="float", dest="edge_thres", default=0.1,
            help="eliminate edges below this threshold [default: %default]")
        parser.add_option(
            '-f', '--format',
            type="choice", choices=('prof', 'callgrind', 'oprofile', 'sysprof', 'pstats', 'shark', 'sleepy', 'aqtime', 'xperf'),
            dest="format", default="prof",
            help="profile format: prof, callgrind, oprofile, sysprof, shark, sleepy, aqtime, pstats, or xperf [default: %default]")
        parser.add_option(
            '-c', '--colormap',
            type="choice", choices=('color', 'pink', 'gray', 'bw'),
            dest="theme", default="color",
            help="color map: color, pink, gray, or bw [default: %default]")
        parser.add_option(
            '-s', '--strip',
            action="store_true",
            dest="strip", default=False,
            help="strip function parameters, template parameters, and const modifiers from demangled C++ function names")
        parser.add_option(
            '-w', '--wrap',
            action="store_true",
            dest="wrap", default=False,
            help="wrap function names")
        # add a new option to control skew of the colorization curve
        parser.add_option(
            '--skew',
            type="float", dest="theme_skew", default=1.0,
            help="skew the colorization curve.  Values < 1.0 give more variety to lower percentages.  Value > 1.0 give less variety to lower percentages")
        (self.options, self.args) = parser.parse_args(sys.argv[1:])

        if len(self.args) > 1 and self.options.format != 'pstats':
            parser.error('incorrect number of arguments')

        try:
            self.theme = self.themes[self.options.theme]
        except KeyError:
            parser.error('invalid colormap \'%s\'' % self.options.theme)

        # set skew on the theme now that it has been picked.
        if self.options.theme_skew:
            self.theme.skew = self.options.theme_skew

        if self.options.format == 'prof':
            if not self.args:
                fp = sys.stdin
            else:
                fp = open(self.args[0], 'rt')
            parser = GprofParser(fp)
        elif self.options.format == 'callgrind':
            if not self.args:
                fp = sys.stdin
            else:
                fp = open(self.args[0], 'rt')
            parser = CallgrindParser(fp)
        elif self.options.format == 'oprofile':
            if not self.args:
                fp = sys.stdin
            else:
                fp = open(self.args[0], 'rt')
            parser = OprofileParser(fp)
        elif self.options.format == 'sysprof':
            if not self.args:
                fp = sys.stdin
            else:
                fp = open(self.args[0], 'rt')
            parser = SysprofParser(fp)
        elif self.options.format == 'pstats':
            if not self.args:
                parser.error('at least a file must be specified for pstats input')
            parser = PstatsParser(*self.args)
        elif self.options.format == 'xperf':
            if not self.args:
                fp = sys.stdin
            else:
                fp = open(self.args[0], 'rt')
            parser = XPerfParser(fp)
        elif self.options.format == 'shark':
            if not self.args:
                fp = sys.stdin
            else:
                fp = open(self.args[0], 'rt')
            parser = SharkParser(fp)
        elif self.options.format == 'sleepy':
            if len(self.args) != 1:
                parser.error('exactly one file must be specified for sleepy input')
            parser = SleepyParser(self.args[0])
        elif self.options.format == 'aqtime':
            if not self.args:
                fp = sys.stdin
            else:
                fp = open(self.args[0], 'rt')
            parser = AQtimeParser(fp)
        else:
            parser.error('invalid format \'%s\'' % self.options.format)

        self.profile = parser.parse()

        if self.options.output is None:
            self.output = sys.stdout
        else:
            self.output = open(self.options.output, 'wt')

        self.write_graph()

    _parenthesis_re = re.compile(r'\([^()]*\)')
    _angles_re = re.compile(r'<[^<>]*>')
    _const_re = re.compile(r'\s+const$')

    def strip_function_name(self, name):
        """Remove extraneous information from C++ demangled function names."""

        # Strip function parameters from name by recursively removing paired parenthesis
        while True:
            name, n = self._parenthesis_re.subn('', name)
            if not n:
                break

        # Strip const qualifier
        name = self._const_re.sub('', name)

        # Strip template parameters from name by recursively removing paired angles
        while True:
            name, n = self._angles_re.subn('', name)
            if not n:
                break

        return name

    def wrap_function_name(self, name):
        """Split the function name on multiple lines."""

        if len(name) > 32:
            ratio = 2.0 / 3.0
            height = max(int(len(name) / (1.0 - ratio) + 0.5), 1)
            width = max(len(name) / height, 32)
            # TODO: break lines in symbols
            name = textwrap.fill(name, width, break_long_words=False)

        # Take away spaces
        name = name.replace(", ", ",")
        name = name.replace("> >", ">>")
        name = name.replace("> >", ">>")  # catch consecutive

        return name

    def compress_function_name(self, name):
        """Compress function name according to the user preferences."""

        if self.options.strip:
            name = self.strip_function_name(name)

        if self.options.wrap:
            name = self.wrap_function_name(name)

        # TODO: merge functions with same resulting name

        return name

    def write_graph(self):
        dot = DotWriter(self.output)
        profile = self.profile
        profile.prune(self.options.node_thres / 100.0, self.options.edge_thres / 100.0)

        for function in profile.functions.itervalues():
            function.name = self.compress_function_name(function.name)

        dot.graph(profile, self.theme)

if __name__ == '__main__':
    Main().main()

########NEW FILE########
__FILENAME__ = indev
"""
Created on Jul 22, 2011

@author: Rio

Indev levels:

TAG_Compound "MinecraftLevel"
{
   TAG_Compound "Environment"
   {
      TAG_Short "SurroundingGroundHeight"// Height of surrounding ground (in blocks)
      TAG_Byte "SurroundingGroundType"   // Block ID of surrounding ground
      TAG_Short "SurroundingWaterHeight" // Height of surrounding water (in blocks)
      TAG_Byte "SurroundingWaterType"    // Block ID of surrounding water
      TAG_Short "CloudHeight"            // Height of the cloud layer (in blocks)
      TAG_Int "CloudColor"               // Hexadecimal value for the color of the clouds
      TAG_Int "SkyColor"                 // Hexadecimal value for the color of the sky
      TAG_Int "FogColor"                 // Hexadecimal value for the color of the fog
      TAG_Byte "SkyBrightness"           // The brightness of the sky, from 0 to 100
   }

   TAG_List "Entities"
   {
      TAG_Compound
      {
         // One of these per entity on the map.
         // These can change a lot, and are undocumented.
         // Feel free to play around with them, though.
         // The most interesting one might be the one with ID "LocalPlayer", which contains the player inventory
      }
   }

   TAG_Compound "Map"
   {
      // To access a specific block from either byte array, use the following algorithm:
      // Index = x + (y * Depth + z) * Width

      TAG_Short "Width"                  // Width of the level (along X)
      TAG_Short "Height"                 // Height of the level (along Y)
      TAG_Short "Length"                 // Length of the level (along Z)
      TAG_Byte_Array "Blocks"             // An array of Length*Height*Width bytes specifying the block types
      TAG_Byte_Array "Data"              // An array of Length*Height*Width bytes with data for each blocks

      TAG_List "Spawn"                   // Default spawn position
      {
         TAG_Short x  // These values are multiplied by 32 before being saved
         TAG_Short y  // That means that the actual values are x/32.0, y/32.0, z/32.0
         TAG_Short z
      }
   }

   TAG_Compound "About"
   {
      TAG_String "Name"                  // Level name
      TAG_String "Author"                // Name of the player who made the level
      TAG_Long "CreatedOn"               // Timestamp when the level was first created
   }
}
"""

from entity import TileEntity
from level import MCLevel
from logging import getLogger
from materials import indevMaterials
from numpy import array, swapaxes
import nbt
import os

log = getLogger(__name__)

MinecraftLevel = "MinecraftLevel"

Environment = "Environment"
SurroundingGroundHeight = "SurroundingGroundHeight"
SurroundingGroundType = "SurroundingGroundType"
SurroundingWaterHeight = "SurroundingWaterHeight"
SurroundingWaterType = "SurroundingWaterType"
CloudHeight = "CloudHeight"
CloudColor = "CloudColor"
SkyColor = "SkyColor"
FogColor = "FogColor"
SkyBrightness = "SkyBrightness"

About = "About"
Name = "Name"
Author = "Author"
CreatedOn = "CreatedOn"
Spawn = "Spawn"

__all__ = ["MCIndevLevel"]

from level import EntityLevel


class MCIndevLevel(EntityLevel):
    """ IMPORTANT: self.Blocks and self.Data are indexed with [x,z,y] via axis
    swapping to be consistent with infinite levels."""

    materials = indevMaterials

    def setPlayerSpawnPosition(self, pos, player=None):
        assert len(pos) == 3
        self.Spawn = array(pos)

    def playerSpawnPosition(self, player=None):
        return self.Spawn

    def setPlayerPosition(self, pos, player="Ignored"):
        self.LocalPlayer["Pos"] = nbt.TAG_List([nbt.TAG_Float(p) for p in pos])

    def getPlayerPosition(self, player="Ignored"):
        return array(map(lambda x: x.value, self.LocalPlayer["Pos"]))

    def setPlayerOrientation(self, yp, player="Ignored"):
        self.LocalPlayer["Rotation"] = nbt.TAG_List([nbt.TAG_Float(p) for p in yp])

    def getPlayerOrientation(self, player="Ignored"):
        """ returns (yaw, pitch) """
        return array(map(lambda x: x.value, self.LocalPlayer["Rotation"]))

    def setBlockDataAt(self, x, y, z, newdata):
        if x < 0 or y < 0 or z < 0:
            return 0
        if x >= self.Width or y >= self.Height or z >= self.Length:
            return 0
        self.Data[x, z, y] = (newdata & 0xf)

    def blockDataAt(self, x, y, z):
        if x < 0 or y < 0 or z < 0:
            return 0
        if x >= self.Width or y >= self.Height or z >= self.Length:
            return 0
        return self.Data[x, z, y]

    def blockLightAt(self, x, y, z):
        if x < 0 or y < 0 or z < 0:
            return 0
        if x >= self.Width or y >= self.Height or z >= self.Length:
            return 0
        return self.BlockLight[x, z, y]

    def __repr__(self):
        return u"MCIndevLevel({0}): {1}W {2}L {3}H".format(self.filename, self.Width, self.Length, self.Height)

    @classmethod
    def _isTagLevel(cls, root_tag):
        return "MinecraftLevel" == root_tag.name

    def __init__(self, root_tag=None, filename=""):
        self.Width = 0
        self.Height = 0
        self.Length = 0
        self.Blocks = array([], "uint8")
        self.Data = array([], "uint8")
        self.Spawn = (0, 0, 0)
        self.filename = filename

        if root_tag:

            self.root_tag = root_tag
            mapTag = root_tag["Map"]
            self.Width = mapTag["Width"].value
            self.Length = mapTag["Length"].value
            self.Height = mapTag["Height"].value

            mapTag["Blocks"].value.shape = (self.Height, self.Length, self.Width)

            self.Blocks = swapaxes(mapTag["Blocks"].value, 0, 2)

            mapTag["Data"].value.shape = (self.Height, self.Length, self.Width)

            self.Data = swapaxes(mapTag["Data"].value, 0, 2)

            self.BlockLight = self.Data & 0xf

            self.Data >>= 4

            self.Spawn = [mapTag[Spawn][i].value for i in range(3)]

            if "Entities" not in root_tag:
                root_tag["Entities"] = nbt.TAG_List()
            self.Entities = root_tag["Entities"]

            # xxx fixup Motion and Pos to match infdev format
            def numbersToDoubles(ent):
                for attr in "Motion", "Pos":
                    if attr in ent:
                        ent[attr] = nbt.TAG_List([nbt.TAG_Double(t.value) for t in ent[attr]])
            for ent in self.Entities:
                numbersToDoubles(ent)

            if "TileEntities" not in root_tag:
                root_tag["TileEntities"] = nbt.TAG_List()
            self.TileEntities = root_tag["TileEntities"]
            # xxx fixup TileEntities positions to match infdev format
            for te in self.TileEntities:
                pos = te["Pos"].value

                (x, y, z) = self.decodePos(pos)

                TileEntity.setpos(te, (x, y, z))


            localPlayerList = [tag for tag in root_tag["Entities"] if tag['id'].value == 'LocalPlayer']
            if len(localPlayerList) == 0:  # omen doesn't make a player entity
                playerTag = nbt.TAG_Compound()
                playerTag['id'] = nbt.TAG_String('LocalPlayer')
                playerTag['Pos'] = nbt.TAG_List([nbt.TAG_Float(0.), nbt.TAG_Float(64.), nbt.TAG_Float(0.)])
                playerTag['Rotation'] = nbt.TAG_List([nbt.TAG_Float(0.), nbt.TAG_Float(45.)])
                self.LocalPlayer = playerTag

            else:
                self.LocalPlayer = localPlayerList[0]

        else:
            log.info(u"Creating new Indev levels is not yet implemented.!")
            raise ValueError("Can't do that yet")
#            self.SurroundingGroundHeight = root_tag[Environment][SurroundingGroundHeight].value
#            self.SurroundingGroundType = root_tag[Environment][SurroundingGroundType].value
#            self.SurroundingWaterHeight = root_tag[Environment][SurroundingGroundHeight].value
#            self.SurroundingWaterType = root_tag[Environment][SurroundingWaterType].value
#            self.CloudHeight = root_tag[Environment][CloudHeight].value
#            self.CloudColor = root_tag[Environment][CloudColor].value
#            self.SkyColor = root_tag[Environment][SkyColor].value
#            self.FogColor = root_tag[Environment][FogColor].value
#            self.SkyBrightness = root_tag[Environment][SkyBrightness].value
#            self.TimeOfDay = root_tag[Environment]["TimeOfDay"].value
#
#
#            self.Name = self.root_tag[About][Name].value
#            self.Author = self.root_tag[About][Author].value
#            self.CreatedOn = self.root_tag[About][CreatedOn].value

    def rotateLeft(self):
        MCLevel.rotateLeft(self)

        self.Data = swapaxes(self.Data, 1, 0)[:, ::-1, :]  # x=y; y=-x

        torchRotation = array([0, 4, 3, 1, 2, 5,
                               6, 7,

                               8, 9, 10, 11, 12, 13, 14, 15])

        torchIndexes = (self.Blocks == self.materials.Torch.ID)
        log.info(u"Rotating torches: {0}".format(len(torchIndexes.nonzero()[0])))
        self.Data[torchIndexes] = torchRotation[self.Data[torchIndexes]]

    def decodePos(self, v):
        b = 10
        m = (1 << b) - 1
        return v & m, (v >> b) & m, (v >> (2 * b))

    def encodePos(self, x, y, z):
        b = 10
        return x + (y << b) + (z << (2 * b))

    def saveToFile(self, filename=None):
        if filename is None:
            filename = self.filename
        if filename is None:
            log.warn(u"Attempted to save an unnamed file in place")
            return  # you fool!

        self.Data <<= 4
        self.Data |= (self.BlockLight & 0xf)

        self.Blocks = swapaxes(self.Blocks, 0, 2)
        self.Data = swapaxes(self.Data, 0, 2)

        mapTag = nbt.TAG_Compound()
        mapTag["Width"] = nbt.TAG_Short(self.Width)
        mapTag["Height"] = nbt.TAG_Short(self.Height)
        mapTag["Length"] = nbt.TAG_Short(self.Length)
        mapTag["Blocks"] = nbt.TAG_Byte_Array(self.Blocks)
        mapTag["Data"] = nbt.TAG_Byte_Array(self.Data)

        self.Blocks = swapaxes(self.Blocks, 0, 2)
        self.Data = swapaxes(self.Data, 0, 2)

        mapTag[Spawn] = nbt.TAG_List([nbt.TAG_Short(i) for i in self.Spawn])

        self.root_tag["Map"] = mapTag

        self.Entities.append(self.LocalPlayer)
        # fix up Entities imported from Alpha worlds
        def numbersToFloats(ent):
            for attr in "Motion", "Pos":
                if attr in ent:
                    ent[attr] = nbt.TAG_List([nbt.TAG_Double(t.value) for t in ent[attr]])
        for ent in self.Entities:
            numbersToFloats(ent)

        # fix up TileEntities imported from Alpha worlds.
        for ent in self.TileEntities:
            if "Pos" not in ent and all(c in ent for c in 'xyz'):
                ent["Pos"] = nbt.TAG_Int(self.encodePos(ent['x'].value, ent['y'].value, ent['z'].value))
        # output_file = gzip.open(self.filename, "wb", compresslevel=1)
        try:
            os.rename(filename, filename + ".old")
        except Exception:
            pass

        try:
            self.root_tag.save(filename)
        except:
            os.rename(filename + ".old", filename)

        try:
            os.remove(filename + ".old")
        except Exception:
            pass

        self.Entities.remove(self.LocalPlayer)

        self.BlockLight = self.Data & 0xf

        self.Data >>= 4

########NEW FILE########
__FILENAME__ = infiniteworld
'''
Created on Jul 22, 2011

@author: Rio
'''

import copy
from datetime import datetime
import itertools
from logging import getLogger
from math import floor
import os
import re
import random
import shutil
import struct
import time
import traceback
import weakref
import zlib
import sys

import blockrotation
from box import BoundingBox
from entity import Entity, TileEntity
from faces import FaceXDecreasing, FaceXIncreasing, FaceZDecreasing, FaceZIncreasing
from level import LightedChunk, EntityLevel, computeChunkHeightMap, MCLevel, ChunkBase
from materials import alphaMaterials
from mclevelbase import ChunkMalformed, ChunkNotPresent, exhaust, PlayerNotFound
import nbt
from numpy import array, clip, maximum, zeros
from regionfile import MCRegionFile

log = getLogger(__name__)


DIM_NETHER = -1
DIM_END = 1

__all__ = ["ZeroChunk", "AnvilChunk", "ChunkedLevelMixin", "MCInfdevOldLevel", "MCAlphaDimension", "ZipSchematic"]
_zeros = {}

class SessionLockLost(IOError):
    pass



def ZeroChunk(height=512):
    z = _zeros.get(height)
    if z is None:
        z = _zeros[height] = _ZeroChunk(height)
    return z


class _ZeroChunk(ChunkBase):
    " a placebo for neighboring-chunk routines "

    def __init__(self, height=512):
        zeroChunk = zeros((16, 16, height), 'uint8')
        whiteLight = zeroChunk + 15
        self.Blocks = zeroChunk
        self.BlockLight = whiteLight
        self.SkyLight = whiteLight
        self.Data = zeroChunk


def unpackNibbleArray(dataArray):
    s = dataArray.shape
    unpackedData = zeros((s[0], s[1], s[2] * 2), dtype='uint8')

    unpackedData[:, :, ::2] = dataArray
    unpackedData[:, :, ::2] &= 0xf
    unpackedData[:, :, 1::2] = dataArray
    unpackedData[:, :, 1::2] >>= 4
    return unpackedData


def packNibbleArray(unpackedData):
    packedData = array(unpackedData.reshape(16, 16, unpackedData.shape[2] / 2, 2))
    packedData[..., 1] <<= 4
    packedData[..., 1] |= packedData[..., 0]
    return array(packedData[:, :, :, 1])

def sanitizeBlocks(chunk):
    # change grass to dirt where needed so Minecraft doesn't flip out and die
    grass = chunk.Blocks == chunk.materials.Grass.ID
    grass |= chunk.Blocks == chunk.materials.Dirt.ID
    badgrass = grass[:, :, 1:] & grass[:, :, :-1]

    chunk.Blocks[:, :, :-1][badgrass] = chunk.materials.Dirt.ID

    # remove any thin snow layers immediately above other thin snow layers.
    # minecraft doesn't flip out, but it's almost never intended
    if hasattr(chunk.materials, "SnowLayer"):
        snowlayer = chunk.Blocks == chunk.materials.SnowLayer.ID
        badsnow = snowlayer[:, :, 1:] & snowlayer[:, :, :-1]

        chunk.Blocks[:, :, 1:][badsnow] = chunk.materials.Air.ID


class AnvilChunkData(object):
    """ This is the chunk data backing an AnvilChunk. Chunk data is retained by the MCInfdevOldLevel until its
    AnvilChunk is no longer used, then it is either cached in memory, discarded, or written to disk according to
    resource limits.

    AnvilChunks are stored in a WeakValueDictionary so we can find out when they are no longer used by clients. The
    AnvilChunkData for an unused chunk may safely be discarded or written out to disk. The client should probably
     not keep references to a whole lot of chunks or else it will run out of memory.
    """
    def __init__(self, world, chunkPosition, root_tag = None, create = False):
        self.chunkPosition = chunkPosition
        self.world = world
        self.root_tag = root_tag
        self.dirty = False

        self.Blocks = zeros((16, 16, world.Height), 'uint16')
        self.Data = zeros((16, 16, world.Height), 'uint8')
        self.BlockLight = zeros((16, 16, world.Height), 'uint8')
        self.SkyLight = zeros((16, 16, world.Height), 'uint8')
        self.SkyLight[:] = 15

        if create:
            self._create()
        else:
            self._load(root_tag)

        levelTag = self.root_tag["Level"]
        if "Biomes" not in levelTag:
            levelTag["Biomes"] = nbt.TAG_Byte_Array(zeros((16, 16), 'uint8'))
            levelTag["Biomes"].value[:] = -1

    def _create(self):
        (cx, cz) = self.chunkPosition
        chunkTag = nbt.TAG_Compound()
        chunkTag.name = ""

        levelTag = nbt.TAG_Compound()
        chunkTag["Level"] = levelTag

        levelTag["HeightMap"] = nbt.TAG_Int_Array(zeros((16, 16), 'uint32').newbyteorder())
        levelTag["TerrainPopulated"] = nbt.TAG_Byte(1)
        levelTag["xPos"] = nbt.TAG_Int(cx)
        levelTag["zPos"] = nbt.TAG_Int(cz)

        levelTag["LastUpdate"] = nbt.TAG_Long(0)

        levelTag["Entities"] = nbt.TAG_List()
        levelTag["TileEntities"] = nbt.TAG_List()

        self.root_tag = chunkTag

        self.dirty = True

    def _load(self, root_tag):
        self.root_tag = root_tag

        for sec in self.root_tag["Level"].pop("Sections", []):
            y = sec["Y"].value * 16

            for name in "Blocks", "Data", "SkyLight", "BlockLight":
                arr = getattr(self, name)
                secarray = sec[name].value
                if name == "Blocks":
                    secarray.shape = (16, 16, 16)
                else:
                    secarray.shape = (16, 16, 8)
                    secarray = unpackNibbleArray(secarray)

                arr[..., y:y + 16] = secarray.swapaxes(0, 2)

            tag = sec.get("Add")
            if tag is not None:
                tag.value.shape = (16, 16, 8)
                add = unpackNibbleArray(tag.value)
                self.Blocks[...,y:y + 16] |= (array(add, 'uint16') << 8).swapaxes(0, 2)

    def savedTagData(self):
        """ does not recalculate any data or light """

        log.debug(u"Saving chunk: {0}".format(self))
        sanitizeBlocks(self)

        sections = nbt.TAG_List()
        for y in range(0, self.world.Height, 16):
            section = nbt.TAG_Compound()

            Blocks = self.Blocks[..., y:y + 16].swapaxes(0, 2)
            Data = self.Data[..., y:y + 16].swapaxes(0, 2)
            BlockLight = self.BlockLight[..., y:y + 16].swapaxes(0, 2)
            SkyLight = self.SkyLight[..., y:y + 16].swapaxes(0, 2)

            if (not Blocks.any() and
                not BlockLight.any() and
                (SkyLight == 15).all()):
                continue

            Data = packNibbleArray(Data)
            BlockLight = packNibbleArray(BlockLight)
            SkyLight = packNibbleArray(SkyLight)

            add = Blocks >> 8
            if add.any():
                section["Add"] = nbt.TAG_Byte_Array(packNibbleArray(add).astype('uint8'))

            section['Blocks'] = nbt.TAG_Byte_Array(array(Blocks, 'uint8'))
            section['Data'] = nbt.TAG_Byte_Array(array(Data))
            section['BlockLight'] = nbt.TAG_Byte_Array(array(BlockLight))
            section['SkyLight'] = nbt.TAG_Byte_Array(array(SkyLight))

            section["Y"] = nbt.TAG_Byte(y / 16)
            sections.append(section)

        self.root_tag["Level"]["Sections"] = sections
        data = self.root_tag.save(compressed=False)
        del self.root_tag["Level"]["Sections"]

        log.debug(u"Saved chunk {0}".format(self))
        return data

    @property
    def materials(self):
        return self.world.materials


class AnvilChunk(LightedChunk):
    """ This is a 16x16xH chunk in an (infinite) world.
    The properties Blocks, Data, SkyLight, BlockLight, and Heightmap
    are ndarrays containing the respective blocks in the chunk file.
    Each array is indexed [x,z,y].  The Data, Skylight, and BlockLight
    arrays are automatically unpacked from nibble arrays into byte arrays
    for better handling.
    """

    def __init__(self, chunkData):
        self.world = chunkData.world
        self.chunkPosition = chunkData.chunkPosition
        self.chunkData = chunkData


    def savedTagData(self):
        return self.chunkData.savedTagData()


    def __str__(self):
        return u"AnvilChunk, coords:{0}, world: {1}, D:{2}, L:{3}".format(self.chunkPosition, self.world.displayName, self.dirty, self.needsLighting)

    @property
    def needsLighting(self):
        return self.chunkPosition in self.world.chunksNeedingLighting

    @needsLighting.setter
    def needsLighting(self, value):
        if value:
            self.world.chunksNeedingLighting.add(self.chunkPosition)
        else:
            self.world.chunksNeedingLighting.discard(self.chunkPosition)

    def generateHeightMap(self):
        if self.world.dimNo == DIM_NETHER:
            self.HeightMap[:] = 0
        else:
            computeChunkHeightMap(self.materials, self.Blocks, self.HeightMap)

    def addEntity(self, entityTag):

        def doubleize(name):
            # This is needed for compatibility with Indev levels. Those levels use TAG_Float for entity motion and pos
            if name in entityTag:
                m = entityTag[name]
                entityTag[name] = nbt.TAG_List([nbt.TAG_Double(i.value) for i in m])

        doubleize("Motion")
        doubleize("Position")

        self.dirty = True
        return super(AnvilChunk, self).addEntity(entityTag)

    def removeEntitiesInBox(self, box):
        self.dirty = True
        return super(AnvilChunk, self).removeEntitiesInBox(box)

    def removeTileEntitiesInBox(self, box):
        self.dirty = True
        return super(AnvilChunk, self).removeTileEntitiesInBox(box)

    # --- AnvilChunkData accessors ---

    @property
    def root_tag(self):
        return self.chunkData.root_tag

    @property
    def dirty(self):
        return self.chunkData.dirty

    @dirty.setter
    def dirty(self, val):
        self.chunkData.dirty = val

    # --- Chunk attributes ---

    @property
    def materials(self):
        return self.world.materials

    @property
    def Blocks(self):
        return self.chunkData.Blocks

    @property
    def Data(self):
        return self.chunkData.Data

    @property
    def SkyLight(self):
        return self.chunkData.SkyLight

    @property
    def BlockLight(self):
        return self.chunkData.BlockLight

    @property
    def Biomes(self):
        return self.root_tag["Level"]["Biomes"].value.reshape((16, 16))

    @property
    def HeightMap(self):
        return self.root_tag["Level"]["HeightMap"].value.reshape((16, 16))

    @property
    def Entities(self):
        return self.root_tag["Level"]["Entities"]

    @property
    def TileEntities(self):
        return self.root_tag["Level"]["TileEntities"]

    @property
    def TerrainPopulated(self):
        return self.root_tag["Level"]["TerrainPopulated"].value

    @TerrainPopulated.setter
    def TerrainPopulated(self, val):
        """True or False. If False, the game will populate the chunk with
        ores and vegetation on next load"""
        self.root_tag["Level"]["TerrainPopulated"].value = val
        self.dirty = True


base36alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"


def decbase36(s):
    return int(s, 36)


def base36(n):
    global base36alphabet

    n = int(n)
    if 0 == n:
        return '0'
    neg = ""
    if n < 0:
        neg = "-"
        n = -n

    work = []

    while n:
        n, digit = divmod(n, 36)
        work.append(base36alphabet[digit])

    return neg + ''.join(reversed(work))


def deflate(data):
    # zobj = zlib.compressobj(6,zlib.DEFLATED,-zlib.MAX_WBITS,zlib.DEF_MEM_LEVEL,0)
    # zdata = zobj.compress(data)
    # zdata += zobj.flush()
    # return zdata
    return zlib.compress(data)


def inflate(data):
    return zlib.decompress(data)


class ChunkedLevelMixin(MCLevel):
    def blockLightAt(self, x, y, z):
        if y < 0 or y >= self.Height:
            return 0
        zc = z >> 4
        xc = x >> 4

        xInChunk = x & 0xf
        zInChunk = z & 0xf
        ch = self.getChunk(xc, zc)

        return ch.BlockLight[xInChunk, zInChunk, y]

    def setBlockLightAt(self, x, y, z, newLight):
        if y < 0 or y >= self.Height:
            return 0
        zc = z >> 4
        xc = x >> 4

        xInChunk = x & 0xf
        zInChunk = z & 0xf

        ch = self.getChunk(xc, zc)
        ch.BlockLight[xInChunk, zInChunk, y] = newLight
        ch.chunkChanged(False)

    def blockDataAt(self, x, y, z):
        if y < 0 or y >= self.Height:
            return 0
        zc = z >> 4
        xc = x >> 4

        xInChunk = x & 0xf
        zInChunk = z & 0xf

        try:
            ch = self.getChunk(xc, zc)
        except ChunkNotPresent:
            return 0

        return ch.Data[xInChunk, zInChunk, y]

    def setBlockDataAt(self, x, y, z, newdata):
        if y < 0 or y >= self.Height:
            return 0
        zc = z >> 4
        xc = x >> 4

        xInChunk = x & 0xf
        zInChunk = z & 0xf

        try:
            ch = self.getChunk(xc, zc)
        except ChunkNotPresent:
            return 0

        ch.Data[xInChunk, zInChunk, y] = newdata
        ch.dirty = True
        ch.needsLighting = True

    def blockAt(self, x, y, z):
        """returns 0 for blocks outside the loadable chunks.  automatically loads chunks."""
        if y < 0 or y >= self.Height:
            return 0

        zc = z >> 4
        xc = x >> 4
        xInChunk = x & 0xf
        zInChunk = z & 0xf

        try:
            ch = self.getChunk(xc, zc)
        except ChunkNotPresent:
            return 0

        return ch.Blocks[xInChunk, zInChunk, y]

    def setBlockAt(self, x, y, z, blockID):
        """returns 0 for blocks outside the loadable chunks.  automatically loads chunks."""
        if y < 0 or y >= self.Height:
            return 0

        zc = z >> 4
        xc = x >> 4
        xInChunk = x & 0xf
        zInChunk = z & 0xf

        try:
            ch = self.getChunk(xc, zc)
        except ChunkNotPresent:
            return 0

        ch.Blocks[xInChunk, zInChunk, y] = blockID
        ch.dirty = True
        ch.needsLighting = True

    def skylightAt(self, x, y, z):

        if y < 0 or y >= self.Height:
            return 0
        zc = z >> 4
        xc = x >> 4

        xInChunk = x & 0xf
        zInChunk = z & 0xf

        ch = self.getChunk(xc, zc)

        return ch.SkyLight[xInChunk, zInChunk, y]

    def setSkylightAt(self, x, y, z, lightValue):
        if y < 0 or y >= self.Height:
            return 0
        zc = z >> 4
        xc = x >> 4

        xInChunk = x & 0xf
        zInChunk = z & 0xf

        ch = self.getChunk(xc, zc)
        skyLight = ch.SkyLight

        oldValue = skyLight[xInChunk, zInChunk, y]

        ch.chunkChanged(False)
        if oldValue < lightValue:
            skyLight[xInChunk, zInChunk, y] = lightValue
        return oldValue < lightValue

    createChunk = NotImplemented



    def generateLights(self, dirtyChunkPositions=None):
        return exhaust(self.generateLightsIter(dirtyChunkPositions))

    def generateLightsIter(self, dirtyChunkPositions=None):
        """ dirtyChunks may be an iterable yielding (xPos,zPos) tuples
        if none, generate lights for all chunks that need lighting
        """

        startTime = datetime.now()

        if dirtyChunkPositions is None:
            dirtyChunkPositions = self.chunksNeedingLighting
        else:
            dirtyChunkPositions = (c for c in dirtyChunkPositions if self.containsChunk(*c))

        dirtyChunkPositions = sorted(dirtyChunkPositions)

        maxLightingChunks = getattr(self, 'loadedChunkLimit', 400)

        log.info(u"Asked to light {0} chunks".format(len(dirtyChunkPositions)))
        chunkLists = [dirtyChunkPositions]

        def reverseChunkPosition((cx, cz)):
            return cz, cx

        def splitChunkLists(chunkLists):
            newChunkLists = []
            for l in chunkLists:

                # list is already sorted on x position, so this splits into left and right

                smallX = l[:len(l) / 2]
                bigX = l[len(l) / 2:]

                # sort halves on z position
                smallX = sorted(smallX, key=reverseChunkPosition)
                bigX = sorted(bigX, key=reverseChunkPosition)

                # add quarters to list

                newChunkLists.append(smallX[:len(smallX) / 2])
                newChunkLists.append(smallX[len(smallX) / 2:])

                newChunkLists.append(bigX[:len(bigX) / 2])
                newChunkLists.append(bigX[len(bigX) / 2:])

            return newChunkLists

        while len(chunkLists[0]) > maxLightingChunks:
            chunkLists = splitChunkLists(chunkLists)

        if len(chunkLists) > 1:
            log.info(u"Using {0} batches to conserve memory.".format(len(chunkLists)))
        # batchSize = min(len(a) for a in chunkLists)
        estimatedTotals = [len(a) * 32 for a in chunkLists]
        workDone = 0

        for i, dc in enumerate(chunkLists):
            log.info(u"Batch {0}/{1}".format(i, len(chunkLists)))

            dc = sorted(dc)
            workTotal = sum(estimatedTotals)
            t = 0
            for c, t, p in self._generateLightsIter(dc):

                yield c + workDone, t + workTotal - estimatedTotals[i], p

            estimatedTotals[i] = t
            workDone += t

        timeDelta = datetime.now() - startTime

        if len(dirtyChunkPositions):
            log.info(u"Completed in {0}, {1} per chunk".format(timeDelta, dirtyChunkPositions and timeDelta / len(dirtyChunkPositions) or 0))

        return

    def _generateLightsIter(self, dirtyChunkPositions):
        la = array(self.materials.lightAbsorption)
        clip(la, 1, 15, la)

        dirtyChunks = set(self.getChunk(*cPos) for cPos in dirtyChunkPositions)

        workDone = 0
        workTotal = len(dirtyChunks) * 29

        progressInfo = (u"Lighting {0} chunks".format(len(dirtyChunks)))
        log.info(progressInfo)

        for i, chunk in enumerate(dirtyChunks):

            chunk.chunkChanged()
            yield i, workTotal, progressInfo
            assert chunk.dirty and chunk.needsLighting

        workDone += len(dirtyChunks)
        workTotal = len(dirtyChunks)

        for ch in list(dirtyChunks):
            # relight all blocks in neighboring chunks in case their light source disappeared.
            cx, cz = ch.chunkPosition
            for dx, dz in itertools.product((-1, 0, 1), (-1, 0, 1)):
                try:
                    ch = self.getChunk(cx + dx, cz + dz)
                except (ChunkNotPresent, ChunkMalformed):
                    continue
                dirtyChunks.add(ch)
                ch.dirty = True

        dirtyChunks = sorted(dirtyChunks, key=lambda x: x.chunkPosition)
        workTotal += len(dirtyChunks) * 28

        for i, chunk in enumerate(dirtyChunks):
            chunk.BlockLight[:] = self.materials.lightEmission[chunk.Blocks]
            chunk.dirty = True

        zeroChunk = ZeroChunk(self.Height)
        zeroChunk.BlockLight[:] = 0
        zeroChunk.SkyLight[:] = 0

        startingDirtyChunks = dirtyChunks

        oldLeftEdge = zeros((1, 16, self.Height), 'uint8')
        oldBottomEdge = zeros((16, 1, self.Height), 'uint8')
        oldChunk = zeros((16, 16, self.Height), 'uint8')
        if self.dimNo in (-1, 1):
            lights = ("BlockLight",)
        else:
            lights = ("BlockLight", "SkyLight")
        log.info(u"Dispersing light...")

        def clipLight(light):
            # light arrays are all uint8 by default, so when results go negative
            # they become large instead.  reinterpret as signed int using view()
            # and then clip to range
            light.view('int8').clip(0, 15, light)

        for j, light in enumerate(lights):
            zerochunkLight = getattr(zeroChunk, light)
            newDirtyChunks = list(startingDirtyChunks)

            work = 0

            for i in range(14):
                if len(newDirtyChunks) == 0:
                    workTotal -= len(startingDirtyChunks) * (14 - i)
                    break

                progressInfo = u"{0} Pass {1}: {2} chunks".format(light, i, len(newDirtyChunks))
                log.info(progressInfo)

#                propagate light!
#                for each of the six cardinal directions, figure a new light value for
#                adjoining blocks by reducing this chunk's light by light absorption and fall off.
#                compare this new light value against the old light value and update with the maximum.
#
#                we calculate all chunks one step before moving to the next step, to ensure all gaps at chunk edges are filled.
#                we do an extra cycle because lights sent across edges may lag by one cycle.
#
#                xxx this can be optimized by finding the highest and lowest blocks
#                that changed after one pass, and only calculating changes for that
#                vertical slice on the next pass. newDirtyChunks would have to be a
#                list of (cPos, miny, maxy) tuples or a cPos : (miny, maxy) dict

                newDirtyChunks = set(newDirtyChunks)
                newDirtyChunks.discard(zeroChunk)

                dirtyChunks = sorted(newDirtyChunks, key=lambda x: x.chunkPosition)

                newDirtyChunks = list()

                for chunk in dirtyChunks:
                    (cx, cz) = chunk.chunkPosition
                    neighboringChunks = {}

                    for dir, dx, dz in ((FaceXDecreasing, -1, 0),
                                        (FaceXIncreasing, 1, 0),
                                        (FaceZDecreasing, 0, -1),
                                        (FaceZIncreasing, 0, 1)):
                        try:
                            neighboringChunks[dir] = self.getChunk(cx + dx, cz + dz)
                        except (ChunkNotPresent, ChunkMalformed):
                            neighboringChunks[dir] = zeroChunk
                        neighboringChunks[dir].dirty = True

                    chunkLa = la[chunk.Blocks]
                    chunkLight = getattr(chunk, light)
                    oldChunk[:] = chunkLight[:]

                    ### Spread light toward -X

                    nc = neighboringChunks[FaceXDecreasing]
                    ncLight = getattr(nc, light)
                    oldLeftEdge[:] = ncLight[15:16, :, 0:self.Height]  # save the old left edge

                    # left edge
                    newlight = (chunkLight[0:1, :, :self.Height] - la[nc.Blocks[15:16, :, 0:self.Height]])
                    clipLight(newlight)

                    maximum(ncLight[15:16, :, 0:self.Height], newlight, ncLight[15:16, :, 0:self.Height])

                    # chunk body
                    newlight = (chunkLight[1:16, :, 0:self.Height] - chunkLa[0:15, :, 0:self.Height])
                    clipLight(newlight)

                    maximum(chunkLight[0:15, :, 0:self.Height], newlight, chunkLight[0:15, :, 0:self.Height])

                    # right edge
                    nc = neighboringChunks[FaceXIncreasing]
                    ncLight = getattr(nc, light)

                    newlight = ncLight[0:1, :, :self.Height] - chunkLa[15:16, :, 0:self.Height]
                    clipLight(newlight)

                    maximum(chunkLight[15:16, :, 0:self.Height], newlight, chunkLight[15:16, :, 0:self.Height])

                    ### Spread light toward +X

                    # right edge
                    nc = neighboringChunks[FaceXIncreasing]
                    ncLight = getattr(nc, light)

                    newlight = (chunkLight[15:16, :, 0:self.Height] - la[nc.Blocks[0:1, :, 0:self.Height]])
                    clipLight(newlight)

                    maximum(ncLight[0:1, :, 0:self.Height], newlight, ncLight[0:1, :, 0:self.Height])

                    # chunk body
                    newlight = (chunkLight[0:15, :, 0:self.Height] - chunkLa[1:16, :, 0:self.Height])
                    clipLight(newlight)

                    maximum(chunkLight[1:16, :, 0:self.Height], newlight, chunkLight[1:16, :, 0:self.Height])

                    # left edge
                    nc = neighboringChunks[FaceXDecreasing]
                    ncLight = getattr(nc, light)

                    newlight = ncLight[15:16, :, :self.Height] - chunkLa[0:1, :, 0:self.Height]
                    clipLight(newlight)

                    maximum(chunkLight[0:1, :, 0:self.Height], newlight, chunkLight[0:1, :, 0:self.Height])

                    zerochunkLight[:] = 0  # zero the zero chunk after each direction
                    # so the lights it absorbed don't affect the next pass

                    # check if the left edge changed and dirty or compress the chunk appropriately
                    if (oldLeftEdge != ncLight[15:16, :, :self.Height]).any():
                        # chunk is dirty
                        newDirtyChunks.append(nc)

                    ### Spread light toward -Z

                    # bottom edge
                    nc = neighboringChunks[FaceZDecreasing]
                    ncLight = getattr(nc, light)
                    oldBottomEdge[:] = ncLight[:, 15:16, :self.Height]  # save the old bottom edge

                    newlight = (chunkLight[:, 0:1, :self.Height] - la[nc.Blocks[:, 15:16, :self.Height]])
                    clipLight(newlight)

                    maximum(ncLight[:, 15:16, :self.Height], newlight, ncLight[:, 15:16, :self.Height])

                    # chunk body
                    newlight = (chunkLight[:, 1:16, :self.Height] - chunkLa[:, 0:15, :self.Height])
                    clipLight(newlight)

                    maximum(chunkLight[:, 0:15, :self.Height], newlight, chunkLight[:, 0:15, :self.Height])

                    # top edge
                    nc = neighboringChunks[FaceZIncreasing]
                    ncLight = getattr(nc, light)

                    newlight = ncLight[:, 0:1, :self.Height] - chunkLa[:, 15:16, 0:self.Height]
                    clipLight(newlight)

                    maximum(chunkLight[:, 15:16, 0:self.Height], newlight, chunkLight[:, 15:16, 0:self.Height])

                    ### Spread light toward +Z

                    # top edge
                    nc = neighboringChunks[FaceZIncreasing]

                    ncLight = getattr(nc, light)

                    newlight = (chunkLight[:, 15:16, :self.Height] - la[nc.Blocks[:, 0:1, :self.Height]])
                    clipLight(newlight)

                    maximum(ncLight[:, 0:1, :self.Height], newlight, ncLight[:, 0:1, :self.Height])

                    # chunk body
                    newlight = (chunkLight[:, 0:15, :self.Height] - chunkLa[:, 1:16, :self.Height])
                    clipLight(newlight)

                    maximum(chunkLight[:, 1:16, :self.Height], newlight, chunkLight[:, 1:16, :self.Height])

                    # bottom edge
                    nc = neighboringChunks[FaceZDecreasing]
                    ncLight = getattr(nc, light)

                    newlight = ncLight[:, 15:16, :self.Height] - chunkLa[:, 0:1, 0:self.Height]
                    clipLight(newlight)

                    maximum(chunkLight[:, 0:1, 0:self.Height], newlight, chunkLight[:, 0:1, 0:self.Height])

                    zerochunkLight[:] = 0

                    if (oldBottomEdge != ncLight[:, 15:16, :self.Height]).any():
                        newDirtyChunks.append(nc)

                    newlight = (chunkLight[:, :, 0:self.Height - 1] - chunkLa[:, :, 1:self.Height])
                    clipLight(newlight)
                    maximum(chunkLight[:, :, 1:self.Height], newlight, chunkLight[:, :, 1:self.Height])

                    newlight = (chunkLight[:, :, 1:self.Height] - chunkLa[:, :, 0:self.Height - 1])
                    clipLight(newlight)
                    maximum(chunkLight[:, :, 0:self.Height - 1], newlight, chunkLight[:, :, 0:self.Height - 1])

                    if (oldChunk != chunkLight).any():
                        newDirtyChunks.append(chunk)

                    work += 1
                    yield workDone + work, workTotal, progressInfo

                workDone += work
                workTotal -= len(startingDirtyChunks)
                workTotal += work

                work = 0

        for ch in startingDirtyChunks:
            ch.needsLighting = False


def TagProperty(tagName, tagType, default_or_func=None):
    def getter(self):
        if tagName not in self.root_tag["Data"]:
            if hasattr(default_or_func, "__call__"):
                default = default_or_func(self)
            else:
                default = default_or_func

            self.root_tag["Data"][tagName] = tagType(default)
        return self.root_tag["Data"][tagName].value

    def setter(self, val):
        self.root_tag["Data"][tagName] = tagType(value=val)

    return property(getter, setter)

class AnvilWorldFolder(object):
    def __init__(self, filename):
        if not os.path.exists(filename):
            os.mkdir(filename)

        elif not os.path.isdir(filename):
            raise IOError, "AnvilWorldFolder: Not a folder: %s" % filename

        self.filename = filename
        self.regionFiles = {}

    # --- File paths ---

    def getFilePath(self, path):
        path = path.replace("/", os.path.sep)
        return os.path.join(self.filename, path)

    def getFolderPath(self, path):
        path = self.getFilePath(path)
        if not os.path.exists(path):
            os.makedirs(path)

        return path

    # --- Region files ---

    def getRegionFilename(self, rx, rz):
        return os.path.join(self.getFolderPath("region"), "r.%s.%s.%s" % (rx, rz, "mca"))

    def getRegionFile(self, rx, rz):
        regionFile = self.regionFiles.get((rx, rz))
        if regionFile:
            return regionFile
        regionFile = MCRegionFile(self.getRegionFilename(rx, rz), (rx, rz))
        self.regionFiles[rx, rz] = regionFile
        return regionFile

    def getRegionForChunk(self, cx, cz):
        rx = cx >> 5
        rz = cz >> 5
        return self.getRegionFile(rx, rz)

    def closeRegions(self):
        for rf in self.regionFiles.values():
            rf.close()

        self.regionFiles = {}

    # --- Chunks and chunk listing ---

    def tryLoadRegionFile(self, filepath):
        filename = os.path.basename(filepath)
        bits = filename.split('.')
        if len(bits) < 4 or bits[0] != 'r' or bits[3] != "mca":
            return None

        try:
            rx, rz = map(int, bits[1:3])
        except ValueError:
            return None

        return MCRegionFile(filepath, (rx, rz))

    def findRegionFiles(self):
        regionDir = self.getFolderPath("region")

        regionFiles = os.listdir(regionDir)
        for filename in regionFiles:
            yield os.path.join(regionDir, filename)

    def listChunks(self):
        chunks = set()

        for filepath in self.findRegionFiles():
            regionFile = self.tryLoadRegionFile(filepath)
            if regionFile is None:
                continue

            if regionFile.offsets.any():
                rx, rz = regionFile.regionCoords
                self.regionFiles[rx, rz] = regionFile

                for index, offset in enumerate(regionFile.offsets):
                    if offset:
                        cx = index & 0x1f
                        cz = index >> 5

                        cx += rx << 5
                        cz += rz << 5

                        chunks.add((cx, cz))
            else:
                log.info(u"Removing empty region file {0}".format(filepath))
                regionFile.close()
                os.unlink(regionFile.path)

        return chunks

    def containsChunk(self, cx, cz):
        rx = cx >> 5
        rz = cz >> 5
        if not os.path.exists(self.getRegionFilename(rx, rz)):
            return False

        return self.getRegionForChunk(cx, cz).containsChunk(cx, cz)

    def deleteChunk(self, cx, cz):
        r = cx >> 5, cz >> 5
        rf = self.getRegionFile(*r)
        if rf:
            rf.setOffset(cx & 0x1f, cz & 0x1f, 0)
            if (rf.offsets == 0).all():
                rf.close()
                os.unlink(rf.path)
                del self.regionFiles[r]

    def readChunk(self, cx, cz):
        if not self.containsChunk(cx, cz):
            raise ChunkNotPresent((cx, cz))

        return self.getRegionForChunk(cx, cz).readChunk(cx, cz)

    def saveChunk(self, cx, cz, data):
        regionFile = self.getRegionForChunk(cx, cz)
        regionFile.saveChunk(cx, cz, data)

    def copyChunkFrom(self, worldFolder, cx, cz):
        fromRF = worldFolder.getRegionForChunk(cx, cz)
        rf = self.getRegionForChunk(cx, cz)
        rf.copyChunkFrom(fromRF, cx, cz)

class MCInfdevOldLevel(ChunkedLevelMixin, EntityLevel):

    def __init__(self, filename=None, create=False, random_seed=None, last_played=None, readonly=False):
        """
        Load an Alpha level from the given filename. It can point to either
        a level.dat or a folder containing one. If create is True, it will
        also create the world using the random_seed and last_played arguments.
        If they are none, a random 64-bit seed will be selected for RandomSeed
        and long(time.time() * 1000) will be used for LastPlayed.

        If you try to create an existing world, its level.dat will be replaced.
        """

        self.Length = 0
        self.Width = 0
        self.Height = 256

        self.playerTagCache = {}
        self.players = []
        assert not (create and readonly)

        if os.path.basename(filename) in ("level.dat", "level.dat_old"):
            filename = os.path.dirname(filename)

        if not os.path.exists(filename):
            if not create:
                raise IOError('File not found')

            os.mkdir(filename)

        if not os.path.isdir(filename):
            raise IOError('File is not a Minecraft Alpha world')


        self.worldFolder = AnvilWorldFolder(filename)
        self.filename = self.worldFolder.getFilePath("level.dat")
        self.readonly = readonly
        if not readonly:
            self.acquireSessionLock()

            workFolderPath = self.worldFolder.getFolderPath("##MCEDIT.TEMP##")
            if os.path.exists(workFolderPath):
                # xxxxxxx Opening a world a second time deletes the first world's work folder and crashes when the first
                # world tries to read a modified chunk from the work folder. This mainly happens when importing a world
                # into itself after modifying it.
                shutil.rmtree(workFolderPath, True)

            self.unsavedWorkFolder = AnvilWorldFolder(workFolderPath)

        # maps (cx, cz) pairs to AnvilChunk
        self._loadedChunks = weakref.WeakValueDictionary()

        # maps (cx, cz) pairs to AnvilChunkData
        self._loadedChunkData = {}

        self.chunksNeedingLighting = set()
        self._allChunks = None
        self.dimensions = {}

        self.loadLevelDat(create, random_seed, last_played)

        assert self.version == self.VERSION_ANVIL, "Pre-Anvil world formats are not supported (for now)"


        self.playersFolder = self.worldFolder.getFolderPath("players")
        self.players = [x[:-4] for x in os.listdir(self.playersFolder) if x.endswith(".dat")]
        if "Player" in self.root_tag["Data"]:
            self.players.append("Player")

        self.preloadDimensions()

    # --- Load, save, create ---

    def _create(self, filename, random_seed, last_played):

        # create a new level
        root_tag = nbt.TAG_Compound()
        root_tag["Data"] = nbt.TAG_Compound()
        root_tag["Data"]["SpawnX"] = nbt.TAG_Int(0)
        root_tag["Data"]["SpawnY"] = nbt.TAG_Int(2)
        root_tag["Data"]["SpawnZ"] = nbt.TAG_Int(0)

        if last_played is None:
            last_played = long(time.time() * 1000)
        if random_seed is None:
            random_seed = long(random.random() * 0xffffffffffffffffL) - 0x8000000000000000L

        self.root_tag = root_tag
        root_tag["Data"]['version'] = nbt.TAG_Int(self.VERSION_ANVIL)

        self.LastPlayed = long(last_played)
        self.RandomSeed = long(random_seed)
        self.SizeOnDisk = 0
        self.Time = 1
        self.LevelName = os.path.basename(self.worldFolder.filename)

        ### if singleplayer:

        self.createPlayer("Player")

    def acquireSessionLock(self):
        lockfile = self.worldFolder.getFilePath("session.lock")
        self.initTime = int(time.time() * 1000)
        with file(lockfile, "wb") as f:
            f.write(struct.pack(">q", self.initTime))
            f.flush()
            os.fsync(f.fileno())

    def checkSessionLock(self):
        if self.readonly:
            raise SessionLockLost, "World is opened read only."

        lockfile = self.worldFolder.getFilePath("session.lock")
        try:
            (lock, ) = struct.unpack(">q", file(lockfile, "rb").read())
        except struct.error:
            lock = -1
        if lock != self.initTime:
            raise SessionLockLost, "Session lock lost. This world is being accessed from another location."

    def loadLevelDat(self, create=False, random_seed=None, last_played=None):

        if create:
            self._create(self.filename, random_seed, last_played)
            self.saveInPlace()
        else:
            try:
                self.root_tag = nbt.load(self.filename)
            except Exception, e:
                filename_old = self.worldFolder.getFilePath("level.dat_old")
                log.info("Error loading level.dat, trying level.dat_old ({0})".format(e))
                try:
                    self.root_tag = nbt.load(filename_old)
                    log.info("level.dat restored from backup.")
                    self.saveInPlace()
                except Exception, e:
                    traceback.print_exc()
                    print repr(e)
                    log.info("Error loading level.dat_old. Initializing with defaults.")
                    self._create(self.filename, random_seed, last_played)

    def saveInPlace(self):
        if self.readonly:
            raise IOError, "World is opened read only."

        self.checkSessionLock()

        for level in self.dimensions.itervalues():
            level.saveInPlace(True)

        dirtyChunkCount = 0
        for chunk in self._loadedChunkData.itervalues():
            cx, cz = chunk.chunkPosition
            if chunk.dirty:
                data = chunk.savedTagData()
                dirtyChunkCount += 1
                self.worldFolder.saveChunk(cx, cz, data)
                chunk.dirty = False

        for cx, cz in self.unsavedWorkFolder.listChunks():
            if (cx, cz) not in self._loadedChunkData:
                data = self.unsavedWorkFolder.readChunk(cx, cz)
                self.worldFolder.saveChunk(cx, cz, data)
                dirtyChunkCount += 1


        self.unsavedWorkFolder.closeRegions()
        shutil.rmtree(self.unsavedWorkFolder.filename, True)
        if not os.path.exists(self.unsavedWorkFolder.filename):
            os.mkdir(self.unsavedWorkFolder.filename)

        for path, tag in self.playerTagCache.iteritems():
            tag.save(path)

        self.playerTagCache.clear()

        self.root_tag.save(self.filename)
        log.info(u"Saved {0} chunks (dim {1})".format(dirtyChunkCount, self.dimNo))

    def unload(self):
        """
        Unload all chunks and close all open filehandles.
        """
        self.worldFolder.closeRegions()
        if not self.readonly:
            self.unsavedWorkFolder.closeRegions()

        self._allChunks = None
        self._loadedChunks.clear()
        self._loadedChunkData.clear()

    def close(self):
        """
        Unload all chunks and close all open filehandles. Discard any unsaved data.
        """
        self.unload()
        try:
            self.checkSessionLock()
            shutil.rmtree(self.unsavedWorkFolder.filename, True)
        except SessionLockLost:
            pass

    # --- Resource limits ---

    loadedChunkLimit = 400

    # --- Constants ---

    GAMETYPE_SURVIVAL = 0
    GAMETYPE_CREATIVE = 1

    VERSION_MCR = 19132
    VERSION_ANVIL = 19133

    # --- Instance variables  ---

    materials = alphaMaterials
    isInfinite = True
    parentWorld = None
    dimNo = 0
    Height = 256
    _bounds = None

    # --- NBT Tag variables ---

    SizeOnDisk = TagProperty('SizeOnDisk', nbt.TAG_Long, 0)
    RandomSeed = TagProperty('RandomSeed', nbt.TAG_Long, 0)
    Time = TagProperty('Time', nbt.TAG_Long, 0)  # Age of the world in ticks. 20 ticks per second; 24000 ticks per day.
    LastPlayed = TagProperty('LastPlayed', nbt.TAG_Long, lambda self: long(time.time() * 1000))

    LevelName = TagProperty('LevelName', nbt.TAG_String, lambda self: self.displayName)

    MapFeatures = TagProperty('MapFeatures', nbt.TAG_Byte, 1)

    GameType = TagProperty('GameType', nbt.TAG_Int, 0)  # 0 for survival, 1 for creative

    version = TagProperty('version', nbt.TAG_Int, VERSION_ANVIL)

    # --- World info ---

    def __str__(self):
        return "MCInfdevOldLevel(\"%s\")" % os.path.basename(self.worldFolder.filename)

    @property
    def displayName(self):
        # shortname = os.path.basename(self.filename)
        # if shortname == "level.dat":
        shortname = os.path.basename(os.path.dirname(self.filename))

        return shortname

    @property
    def bounds(self):
        if self._bounds is None:
            self._bounds = self.getWorldBounds()
        return self._bounds

    def getWorldBounds(self):
        if self.chunkCount == 0:
            return BoundingBox((0, 0, 0), (0, 0, 0))

        allChunks = array(list(self.allChunks))
        mincx = (allChunks[:, 0]).min()
        maxcx = (allChunks[:, 0]).max()
        mincz = (allChunks[:, 1]).min()
        maxcz = (allChunks[:, 1]).max()

        origin = (mincx << 4, 0, mincz << 4)
        size = ((maxcx - mincx + 1) << 4, self.Height, (maxcz - mincz + 1) << 4)

        return BoundingBox(origin, size)

    @property
    def size(self):
        return self.bounds.size

    # --- Format detection ---

    @classmethod
    def _isLevel(cls, filename):

        if os.path.exists(os.path.join(filename, "chunks.dat")):
            return False  # exclude Pocket Edition folders

        if not os.path.isdir(filename):
            f = os.path.basename(filename)
            if f not in ("level.dat", "level.dat_old"):
                return False
            filename = os.path.dirname(filename)

        files = os.listdir(filename)
        if "level.dat" in files or "level.dat_old" in files:
            return True

        return False

    # --- Dimensions ---

    def preloadDimensions(self):
        worldDirs = os.listdir(self.worldFolder.filename)

        for dirname in worldDirs:
            if dirname.startswith("DIM"):
                try:
                    dimNo = int(dirname[3:])
                    log.info("Found dimension {0}".format(dirname))
                    dim = MCAlphaDimension(self, dimNo)
                    self.dimensions[dimNo] = dim
                except Exception, e:
                    log.error(u"Error loading dimension {0}: {1}".format(dirname, e))

    def getDimension(self, dimNo):
        if self.dimNo != 0:
            return self.parentWorld.getDimension(dimNo)

        if dimNo in self.dimensions:
            return self.dimensions[dimNo]
        dim = MCAlphaDimension(self, dimNo, create=True)
        self.dimensions[dimNo] = dim
        return dim

    # --- Region I/O ---

    def preloadChunkPositions(self):
        log.info(u"Scanning for regions...")
        self._allChunks = self.worldFolder.listChunks()
        if not self.readonly:
            self._allChunks.update(self.unsavedWorkFolder.listChunks())
        self._allChunks.update(self._loadedChunkData.iterkeys())

    def getRegionForChunk(self, cx, cz):
        return self.worldFolder.getRegionFile(cx, cz)

    # --- Chunk I/O ---

    def dirhash(self, n):
        return self.dirhashes[n % 64]

    def _dirhash(self):
        n = self
        n = n % 64
        s = u""
        if n >= 36:
            s += u"1"
            n -= 36
        s += u"0123456789abcdefghijklmnopqrstuvwxyz"[n]

        return s

    dirhashes = [_dirhash(n) for n in range(64)]

    def _oldChunkFilename(self, cx, cz):
        return self.worldFolder.getFilePath("%s/%s/c.%s.%s.dat" % (self.dirhash(cx), self.dirhash(cz), base36(cx), base36(cz)))

    def extractChunksInBox(self, box, parentFolder):
        for cx, cz in box.chunkPositions:
            if self.containsChunk(cx, cz):
                self.extractChunk(cx, cz, parentFolder)

    def extractChunk(self, cx, cz, parentFolder):
        if not os.path.exists(parentFolder):
            os.mkdir(parentFolder)

        chunkFilename = self._oldChunkFilename(cx, cz)
        outputFile = os.path.join(parentFolder, os.path.basename(chunkFilename))

        chunk = self.getChunk(cx, cz)

        chunk.root_tag.save(outputFile)

    @property
    def chunkCount(self):
        """Returns the number of chunks in the level. May initiate a costly
        chunk scan."""
        if self._allChunks is None:
            self.preloadChunkPositions()
        return len(self._allChunks)

    @property
    def allChunks(self):
        """Iterates over (xPos, zPos) tuples, one for each chunk in the level.
        May initiate a costly chunk scan."""
        if self._allChunks is None:
            self.preloadChunkPositions()
        return self._allChunks.__iter__()

    def copyChunkFrom(self, world, cx, cz):
        """
        Copy a chunk from world into the same chunk position in self.
        """
        assert isinstance(world, MCInfdevOldLevel)
        if self.readonly:
            raise IOError, "World is opened read only."
        self.checkSessionLock()

        destChunk = self._loadedChunks.get((cx, cz))
        sourceChunk = world._loadedChunks.get((cx, cz))

        if sourceChunk:
            if destChunk:
                log.debug("Both chunks loaded. Using block copy.")
                # Both chunks loaded. Use block copy.
                self.copyBlocksFrom(world, destChunk.bounds, destChunk.bounds.origin)
                return
            else:
                log.debug("Source chunk loaded. Saving into work folder.")

                # Only source chunk loaded. Discard destination chunk and save source chunk in its place.
                self._loadedChunkData.pop((cx, cz), None)
                self.unsavedWorkFolder.saveChunk(cx, cz, sourceChunk.savedTagData())
                return
        else:
            if destChunk:
                log.debug("Destination chunk loaded. Using block copy.")
                # Only destination chunk loaded. Use block copy.
                self.copyBlocksFrom(world, destChunk.bounds, destChunk.bounds.origin)
            else:
                log.debug("No chunk loaded. Using world folder.copyChunkFrom")
                # Neither chunk loaded. Copy via world folders.
                self._loadedChunkData.pop((cx, cz), None)

                # If the source chunk is dirty, write it to the work folder.
                chunkData = world._loadedChunkData.pop((cx, cz), None)
                if chunkData and chunkData.dirty:
                    data = chunkData.savedTagData()
                    world.unsavedWorkFolder.saveChunk(cx, cz, data)

                if world.unsavedWorkFolder.containsChunk(cx, cz):
                    sourceFolder = world.unsavedWorkFolder
                else:
                    sourceFolder = world.worldFolder

                self.unsavedWorkFolder.copyChunkFrom(sourceFolder, cx, cz)

    def _getChunkBytes(self, cx, cz):
        if not self.readonly and self.unsavedWorkFolder.containsChunk(cx, cz):
            return self.unsavedWorkFolder.readChunk(cx, cz)
        else:
            return self.worldFolder.readChunk(cx, cz)

    def _getChunkData(self, cx, cz):
        chunkData = self._loadedChunkData.get((cx, cz))
        if chunkData is not None: return chunkData

        try:
            data = self._getChunkBytes(cx, cz)
            root_tag = nbt.load(buf=data)
            chunkData = AnvilChunkData(self, (cx, cz), root_tag)
        except (MemoryError, ChunkNotPresent):
            raise
        except Exception, e:
            raise ChunkMalformed, "Chunk {0} had an error: {1!r}".format((cx, cz), e), sys.exc_info()[2]

        if not self.readonly and self.unsavedWorkFolder.containsChunk(cx, cz):
            chunkData.dirty = True

        self._storeLoadedChunkData(chunkData)

        return chunkData

    def _storeLoadedChunkData(self, chunkData):
        if len(self._loadedChunkData) > self.loadedChunkLimit:
            # Try to find a chunk to unload. The chunk must not be in _loadedChunks, which contains only chunks that
            # are in use by another object. If the chunk is dirty, save it to the temporary folder.
            if not self.readonly:
                self.checkSessionLock()
            for (ocx, ocz), oldChunkData in self._loadedChunkData.items():
                if (ocx, ocz) not in self._loadedChunks:
                    if oldChunkData.dirty and not self.readonly:
                        data = oldChunkData.savedTagData()
                        self.unsavedWorkFolder.saveChunk(ocx, ocz, data)

                    del self._loadedChunkData[ocx, ocz]
                    break

        self._loadedChunkData[chunkData.chunkPosition] = chunkData

    def getChunk(self, cx, cz):
        """ read the chunk from disk, load it, and return it."""

        chunk = self._loadedChunks.get((cx, cz))
        if chunk is not None:
            return chunk

        chunkData = self._getChunkData(cx, cz)
        chunk = AnvilChunk(chunkData)

        self._loadedChunks[cx, cz] = chunk
        return chunk

    def markDirtyChunk(self, cx, cz):
        self.getChunk(cx, cz).chunkChanged()

    def markDirtyBox(self, box):
        for cx, cz in box.chunkPositions:
            self.markDirtyChunk(cx, cz)

    def listDirtyChunks(self):
        for cPos, chunkData in self._loadedChunkData.iteritems():
            if chunkData.dirty:
                yield cPos

    # --- HeightMaps ---

    def heightMapAt(self, x, z):
        zc = z >> 4
        xc = x >> 4
        xInChunk = x & 0xf
        zInChunk = z & 0xf

        ch = self.getChunk(xc, zc)

        heightMap = ch.HeightMap

        return heightMap[zInChunk, xInChunk]  # HeightMap indices are backwards

    # --- Entities and TileEntities ---

    def addEntity(self, entityTag):
        assert isinstance(entityTag, nbt.TAG_Compound)
        x, y, z = map(lambda x: int(floor(x)), Entity.pos(entityTag))

        try:
            chunk = self.getChunk(x >> 4, z >> 4)
        except (ChunkNotPresent, ChunkMalformed):
            return None
            # raise Error, can't find a chunk?
        chunk.addEntity(entityTag)
        chunk.dirty = True

    def tileEntityAt(self, x, y, z):
        chunk = self.getChunk(x >> 4, z >> 4)
        return chunk.tileEntityAt(x, y, z)

    def addTileEntity(self, tileEntityTag):
        assert isinstance(tileEntityTag, nbt.TAG_Compound)
        if not 'x' in tileEntityTag:
            return
        x, y, z = TileEntity.pos(tileEntityTag)

        try:
            chunk = self.getChunk(x >> 4, z >> 4)
        except (ChunkNotPresent, ChunkMalformed):
            return
            # raise Error, can't find a chunk?
        chunk.addTileEntity(tileEntityTag)
        chunk.dirty = True

    def getEntitiesInBox(self, box):
        entities = []
        for chunk, slices, point in self.getChunkSlices(box):
            entities += chunk.getEntitiesInBox(box)

        return entities

    def removeEntitiesInBox(self, box):
        count = 0
        for chunk, slices, point in self.getChunkSlices(box):
            count += chunk.removeEntitiesInBox(box)

        log.info("Removed {0} entities".format(count))
        return count

    def removeTileEntitiesInBox(self, box):
        count = 0
        for chunk, slices, point in self.getChunkSlices(box):
            count += chunk.removeTileEntitiesInBox(box)

        log.info("Removed {0} tile entities".format(count))
        return count

    # --- Chunk manipulation ---

    def containsChunk(self, cx, cz):
        if self._allChunks is not None:
            return (cx, cz) in self._allChunks
        if (cx, cz) in self._loadedChunkData:
            return True

        return self.worldFolder.containsChunk(cx, cz)

    def containsPoint(self, x, y, z):
        if y < 0 or y > 127:
            return False
        return self.containsChunk(x >> 4, z >> 4)

    def createChunk(self, cx, cz):
        if self.containsChunk(cx, cz):
            raise ValueError("{0}:Chunk {1} already present!".format(self, (cx, cz)))
        if self._allChunks is not None:
            self._allChunks.add((cx, cz))

        self._storeLoadedChunkData(AnvilChunkData(self, (cx, cz), create=True))
        self._bounds = None

    def createChunks(self, chunks):

        i = 0
        ret = []
        for cx, cz in chunks:
            i += 1
            if not self.containsChunk(cx, cz):
                ret.append((cx, cz))
                self.createChunk(cx, cz)
            assert self.containsChunk(cx, cz), "Just created {0} but it didn't take".format((cx, cz))
            if i % 100 == 0:
                log.info(u"Chunk {0}...".format(i))

        log.info("Created {0} chunks.".format(len(ret)))

        return ret

    def createChunksInBox(self, box):
        log.info(u"Creating {0} chunks in {1}".format((box.maxcx - box.mincx) * (box.maxcz - box.mincz), ((box.mincx, box.mincz), (box.maxcx, box.maxcz))))
        return self.createChunks(box.chunkPositions)

    def deleteChunk(self, cx, cz):
        self.worldFolder.deleteChunk(cx, cz)
        if self._allChunks is not None:
            self._allChunks.discard((cx, cz))

        self._bounds = None


    def deleteChunksInBox(self, box):
        log.info(u"Deleting {0} chunks in {1}".format((box.maxcx - box.mincx) * (box.maxcz - box.mincz), ((box.mincx, box.mincz), (box.maxcx, box.maxcz))))
        i = 0
        ret = []
        for cx, cz in itertools.product(xrange(box.mincx, box.maxcx), xrange(box.mincz, box.maxcz)):
            i += 1
            if self.containsChunk(cx, cz):
                self.deleteChunk(cx, cz)
                ret.append((cx, cz))

            assert not self.containsChunk(cx, cz), "Just deleted {0} but it didn't take".format((cx, cz))

            if i % 100 == 0:
                log.info(u"Chunk {0}...".format(i))

        return ret

    # --- Player and spawn manipulation ---

    def playerSpawnPosition(self, player=None):
        """
        xxx if player is None then it gets the default spawn position for the world
        if player hasn't used a bed then it gets the default spawn position
        """
        dataTag = self.root_tag["Data"]
        if player is None:
            playerSpawnTag = dataTag
        else:
            playerSpawnTag = self.getPlayerTag(player)

        return [playerSpawnTag.get(i, dataTag[i]).value for i in ("SpawnX", "SpawnY", "SpawnZ")]

    def setPlayerSpawnPosition(self, pos, player=None):
        """ xxx if player is None then it sets the default spawn position for the world """
        if player is None:
            playerSpawnTag = self.root_tag["Data"]
        else:
            playerSpawnTag = self.getPlayerTag(player)
        for name, val in zip(("SpawnX", "SpawnY", "SpawnZ"), pos):
            playerSpawnTag[name] = nbt.TAG_Int(val)

    def getPlayerPath(self, player):
        assert player != "Player"
        return os.path.join(self.playersFolder, "%s.dat" % player)

    def getPlayerTag(self, player="Player"):
        if player == "Player":
            if player in self.root_tag["Data"]:
                # single-player world
                return self.root_tag["Data"]["Player"]
            raise PlayerNotFound(player)
        else:
            playerFilePath = self.getPlayerPath(player)
            if os.path.exists(playerFilePath):
                # multiplayer world, found this player
                playerTag = self.playerTagCache.get(playerFilePath)
                if playerTag is None:
                    playerTag = nbt.load(playerFilePath)
                    self.playerTagCache[playerFilePath] = playerTag
                return playerTag
            else:
                raise PlayerNotFound(player)

    def getPlayerDimension(self, player="Player"):
        playerTag = self.getPlayerTag(player)
        if "Dimension" not in playerTag:
            return 0
        return playerTag["Dimension"].value

    def setPlayerDimension(self, d, player="Player"):
        playerTag = self.getPlayerTag(player)
        if "Dimension" not in playerTag:
            playerTag["Dimension"] = nbt.TAG_Int(0)
        playerTag["Dimension"].value = d

    def setPlayerPosition(self, (x, y, z), player="Player"):
        posList = nbt.TAG_List([nbt.TAG_Double(p) for p in (x, y-1.8, z)])
        playerTag = self.getPlayerTag(player)

        playerTag["Pos"] = posList

    def getPlayerPosition(self, player="Player"):
        playerTag = self.getPlayerTag(player)
        posList = playerTag["Pos"]

        x, y, z = map(lambda x: x.value, posList)
        return x, y + 1.8, z

    def setPlayerOrientation(self, yp, player="Player"):
        self.getPlayerTag(player)["Rotation"] = nbt.TAG_List([nbt.TAG_Float(p) for p in yp])

    def getPlayerOrientation(self, player="Player"):
        """ returns (yaw, pitch) """
        yp = map(lambda x: x.value, self.getPlayerTag(player)["Rotation"])
        y, p = yp
        if p == 0:
            p = 0.000000001
        if p == 180.0:
            p -= 0.000000001
        yp = y, p
        return array(yp)

    def setPlayerAbilities(self, gametype, player="Player"):
        playerTag = self.getPlayerTag(player)

        # Check for the Abilities tag.  It will be missing in worlds from before
        # Beta 1.9 Prerelease 5.
        if not 'abilities' in playerTag:
            playerTag['abilities'] = nbt.TAG_Compound()

        # Assumes creative (1) is the only mode with these abilities set,
        # which is true for now.  Future game modes may not hold this to be
        # true, however.
        if gametype == 1:
            playerTag['abilities']['instabuild'] = nbt.TAG_Byte(1)
            playerTag['abilities']['mayfly'] = nbt.TAG_Byte(1)
            playerTag['abilities']['invulnerable'] = nbt.TAG_Byte(1)
        else:
            playerTag['abilities']['flying'] = nbt.TAG_Byte(0)
            playerTag['abilities']['instabuild'] = nbt.TAG_Byte(0)
            playerTag['abilities']['mayfly'] = nbt.TAG_Byte(0)
            playerTag['abilities']['invulnerable'] = nbt.TAG_Byte(0)

    def setPlayerGameType(self, gametype, player="Player"):
        playerTag = self.getPlayerTag(player)
        # This annoyingly works differently between single- and multi-player.
        if player == "Player":
            self.GameType = gametype
            self.setPlayerAbilities(gametype, player)
        else:
            playerTag['playerGameType'] = nbt.TAG_Int(gametype)
            self.setPlayerAbilities(gametype, player)

    def getPlayerGameType(self, player="Player"):
        if player == "Player":
            return self.GameType
        else:
            playerTag = self.getPlayerTag(player)
            return playerTag["playerGameType"].value

    def createPlayer(self, playerName):
        if playerName == "Player":
            playerTag = self.root_tag["Data"].setdefault(playerName, nbt.TAG_Compound())
        else:
            playerTag = nbt.TAG_Compound()

        playerTag['Air'] = nbt.TAG_Short(300)
        playerTag['AttackTime'] = nbt.TAG_Short(0)
        playerTag['DeathTime'] = nbt.TAG_Short(0)
        playerTag['Fire'] = nbt.TAG_Short(-20)
        playerTag['Health'] = nbt.TAG_Short(20)
        playerTag['HurtTime'] = nbt.TAG_Short(0)
        playerTag['Score'] = nbt.TAG_Int(0)
        playerTag['FallDistance'] = nbt.TAG_Float(0)
        playerTag['OnGround'] = nbt.TAG_Byte(0)

        playerTag["Inventory"] = nbt.TAG_List()

        playerTag['Motion'] = nbt.TAG_List([nbt.TAG_Double(0) for i in range(3)])
        playerTag['Pos'] = nbt.TAG_List([nbt.TAG_Double([0.5, 2.8, 0.5][i]) for i in range(3)])
        playerTag['Rotation'] = nbt.TAG_List([nbt.TAG_Float(0), nbt.TAG_Float(0)])

        if playerName != "Player":
            if self.readonly:
                raise IOError, "World is opened read only."
            self.checkSessionLock()
            playerTag.save(self.getPlayerPath(playerName))


class MCAlphaDimension (MCInfdevOldLevel):
    def __init__(self, parentWorld, dimNo, create=False):
        filename = parentWorld.worldFolder.getFolderPath("DIM" + str(int(dimNo)))

        self.parentWorld = parentWorld
        MCInfdevOldLevel.__init__(self, filename, create)
        self.dimNo = dimNo
        self.filename = parentWorld.filename
        self.players = self.parentWorld.players
        self.playersFolder = self.parentWorld.playersFolder
        self.playerTagCache = self.parentWorld.playerTagCache

    @property
    def root_tag(self):
        return self.parentWorld.root_tag

    def __str__(self):
        return u"MCAlphaDimension({0}, {1})".format(self.parentWorld, self.dimNo)

    def loadLevelDat(self, create=False, random_seed=None, last_played=None):
        pass

    def preloadDimensions(self):
        pass

    def _create(self, *args, **kw):
        pass

    def acquireSessionLock(self):
        pass

    def checkSessionLock(self):
        self.parentWorld.checkSessionLock()

    dimensionNames = {-1: "Nether", 1: "The End"}

    @property
    def displayName(self):
        return u"{0} ({1})".format(self.parentWorld.displayName,
                                   self.dimensionNames.get(self.dimNo, "Dimension %d" % self.dimNo))

    def saveInPlace(self, saveSelf=False):
        """saving the dimension will save the parent world, which will save any
         other dimensions that need saving.  the intent is that all of them can
         stay loaded at once for fast switching """

        if saveSelf:
            MCInfdevOldLevel.saveInPlace(self)
        else:
            self.parentWorld.saveInPlace()


########NEW FILE########
__FILENAME__ = items
from logging import getLogger
logger = getLogger(__name__)

items_txt = """
:mc-version Minecraft 1.6.2

# Minecraft 1.5 onwards does not use stitched texture files, so FILE and CORDS
# are deprecated. To keep format consistent, dummy values like none.png 0,0 were
# used for new items.

# Also note MCEdit uses this file for items only (editing chest contents etc),
# not for rendering blocks, so FILE and CORDS are ignored.

#            Blocks
# ID  NAME                   FILE         CORDS   DAMAGE
   1  Stone                  terrain.png  1,0
   2  Grass                  terrain.png  3,0
   3  Dirt                   terrain.png  2,0
   4  Cobblestone            terrain.png  0,1
   5  Oak_Wooden_Planks      terrain.png  4,0    0
   5  Spruce_Wooden_Planks   terrain.png  6,12   1
   5  Birch_Wooden_Planks    terrain.png  6,13   2
   5  Jungle_Wooden_Planks   terrain.png  7,12   3
   6  Oak_Sapling            terrain.png  15,0   0
   6  Spruce_Sapling         terrain.png  15,3   1
   6  Birch_Sapling          terrain.png  15,4   2
   6  Jungle_Sapling         terrain.png  14,1   3
   7  Bedrock                terrain.png  1,1
   8  Water                  terrain.png  15,13
   9  Still_Water            terrain.png  15,13
  10  Lava                   terrain.png  15,15
  11  Still_Lava             terrain.png  15,15
  12  Sand                   terrain.png  2,1
  13  Gravel                 terrain.png  3,1
  14  Gold_Ore               terrain.png  0,2
  15  Iron_Ore               terrain.png  1,2
  16  Coal_Ore               terrain.png  2,2
  17  Oak_Wood               terrain.png  4,1    0
  17  Dark_Wood              terrain.png  4,7    1
  17  Birch_Wood             terrain.png  5,7    2
  17  Jungle_Wood            terrain.png  9,9    3
  18  Oak_Leaves             special.png  15,0   0
  18  Dark_Leaves            special.png  14,1   1
  18  Birch_Leaves           special.png  14,2   2
  18  Jungle_Leaves          special.png  14,3   3
  19  Sponge                 terrain.png  0,3
  20  Glass                  terrain.png  1,3
  21  Lapis_Lazuli_Ore       terrain.png  0,10
  22  Lapis_Lazuli_Block     terrain.png  0,9
  23  Dispenser              terrain.png  14,2
  24  Sandstone              terrain.png  0,12   0
  24  Chiseled_Sandstone     terrain.png  5,14   1
  24  Smooth_Sandstone       terrain.png  6,14   2
  25  Note_Block             terrain.png  10,4
  26  Bed_Block              terrain.png  6,8
  27  Powered_Rail           terrain.png  3,10
  28  Detector_Rail          terrain.png  3,12
  29  Sticky_Piston          terrain.png  10,6
  30  Cobweb                 terrain.png  11,0
  31  Dead_Bush              terrain.png  7,3    0
  31  Tall_Grass             special.png  15,0   1
  31  Fern                   special.png  15,1   2
  32  Dead_Bush              terrain.png  7,3
  33  Piston                 terrain.png  11,6
  34  Piston_(head)          terrain.png  11,6
  35  Wool                   terrain.png  0,4    0
  35  Orange_Wool            terrain.png  2,13   1
  35  Magenta_Wool           terrain.png  2,12   2
  35  Light_Blue_Wool        terrain.png  2,11   3
  35  Yellow_Wool            terrain.png  2,10   4
  35  Lime_Wool              terrain.png  2,9    5
  35  Pink_Wool              terrain.png  2,8    6
  35  Gray_Wool              terrain.png  2,7    7
  35  Light_Gray_Wool        terrain.png  1,14   8
  35  Cyan_Wool              terrain.png  1,13   9
  35  Purple_Wool            terrain.png  1,12   10
  35  Blue_Wool              terrain.png  1,11   11
  35  Brown_Wool             terrain.png  1,10   12
  35  Green_Wool             terrain.png  1,9    13
  35  Red_Wool               terrain.png  1,8    14
  35  Black_Wool             terrain.png  1,7    15
  37  Flower                 terrain.png  13,0
  38  Rose                   terrain.png  12,0
  39  Brown_Mushroom         terrain.png  13,1
  40  Red_Mushroom           terrain.png  12,1
  41  Block_of_Gold          terrain.png  7,1
  42  Block_of_Iron          terrain.png  6,1
  43  Double_Stone_Slab      terrain.png  5,0    0
  43  Double_Sandstone_Slab  terrain.png  0,12   1
  43  Double_Wooden_Slab     terrain.png  4,0    2
  43  Double_Stone_Slab      terrain.png  0,1    3
  43  Double_Brick_Slab         none.png  0,0    4
  43  Double_Stone_Brick_Slab   none.png  0,0    5
  43  Double_Nether_Brick_Slab  none.png  0,0    6
  43  Quartz_Slab               none.png  0,0    7
  43  Smooth_Stone_Slab         none.png  0,0    8
  43  Smooth_Sandstone_Slab     none.png  0,0    9
  43  Tile_Quartz_Slab          none.png  0,0    15
  44  Stone_Slab             special.png  2,2    0
  44  Sandstone_Slab         special.png  8,0    1
  44  Wooden_Slab            special.png  3,0    2
  44  Stone_Slab             special.png  1,0    3
  44  Brick_Slab             special.png  0,0    4
  44  Stone_Brick_Slab       special.png  2,0    5
  44  Nether_Brick_Slab         none.png  0,0    6
  43  Quartz_Slab               none.png  0,0    7
  45  Bricks                 terrain.png  7,0
  46  TNT                    terrain.png  8,0
  47  Bookshelf              terrain.png  3,2
  48  Moss_Stone             terrain.png  4,2
  49  Obsidian               terrain.png  5,2
  50  Torch                  terrain.png  0,5
  51  Fire                   special.png  0,5
  52  Monster_Spawner        terrain.png  1,4
  53  Oak_Wood_Stair         special.png  3,1
  54  Chest                  special.png  0,6
  55  Redstone_Dust          terrain.png  4,5
  56  Diamond_Ore            terrain.png  2,3
  57  Block_of_Diamond       terrain.png  8,1
  58  Workbench              terrain.png  12,3   (x1)
  59  Crops                  terrain.png  15,5
  60  Farmland               terrain.png  7,5
  61  Furnace                terrain.png  12,2
  62  Lit_Furnace            terrain.png  13,3
  63  Sign_Block             terrain.png  0,0
  64  Wooden_Door_Block      terrain.png  1,6
  65  Ladder                 terrain.png  3,5
  66  Rail                   terrain.png  0,8
  67  Stone_Stairs           special.png  1,1
  68  Wall_Sign              terrain.png  4,0
  69  Lever                  terrain.png  0,6
  70  Stone_Pressure_Plate   special.png  2,4
  71  Iron_Door_Block        terrain.png  2,6
  72  Wooden_Pressure_Plate  special.png  3,4
  73  Redstone_Ore           terrain.png  3,3
  74  Glowing_Redstone_Ore   terrain.png  3,3
  75  Redstone_Torch_(off)   terrain.png  3,7
  76  Redstone_Torch         terrain.png  3,6
  77  Stone_Button           special.png  2,3
  78  Snow_Layer             special.png  1,4
  79  Ice                    terrain.png  3,4
  80  Snow                   terrain.png  2,4
  81  Cactus                 terrain.png  6,4
  82  Clay                   terrain.png  8,4
  83  Sugar_cane             terrain.png  9,4
  84  Jukebox                terrain.png  10,4
  85  Fence                  special.png  3,2
  86  Pumpkin                terrain.png  7,7
  87  Netherrack             terrain.png  7,6
  88  Soul_Sand              terrain.png  8,6
  89  Glowstone              terrain.png  9,6
  90  Portal                 special.png  1,5
  91  Jack-o'-lantern        terrain.png  8,7
  92  Cake                   special.png  0,4
  93  Repeater_Block_(off)   terrain.png  3,8
  94  Repeater_Block         terrain.png  3,9
  95  Locked_Chest           special.png  0,2
  96  Trapdoor               terrain.png  4,5
  97  Silverfish_Block       terrain.png  1,0
  98  Stone_Brick            terrain.png  6,3    0
  98  Mossy_Stone_Brick      terrain.png  4,6    1
  98  Cracked_Stone_Brick    terrain.png  5,6    2
  98  Chiseled_Stone_Brick   terrain.png  5,13   3
  99  Brown_Mushroom_Block   terrain.png  13,7
 100  Red_Mushroom_Block     terrain.png  14,7
 101  Iron_Bars              terrain.png  5,5
 102  Glass_Pane             special.png  1,3
 103  Melon                  terrain.png  8,8
 104  Pumpkin_Stem           special.png  15,4
 105  Melon_Stem             special.png  15,4
 106  Vines                  special.png  15,2
 107  Fence_Gate             special.png  4,3
 108  Brick_Stairs           special.png  0,1
 109  Stone_Brick_Stairs     special.png  2,1
 110  Mycelium               terrain.png  13,4
 111  Lily_Pad               special.png  15,3
 112  Nether_Brick           terrain.png  0,14
 113  Nether_Brick_Fence     special.png  7,2
 114  Nether_Brick_Stairs    special.png  7,1
 115  Nether_Wart            terrain.png  2,14
 116  Enchantment_Table      terrain.png  6,11   (x1)
 117  Brewing_Stand          terrain.png  13,9
 118  Cauldron               terrain.png  10,9
 119  End_Portal             special.png  2,5
 120  End_Portal_Frame       terrain.png  15,9
 121  End_Stone              terrain.png  15,10
 122  Dragon_Egg             special.png  0,7
 123  Redstone_Lamp          terrain.png  3,13
 124  Redstone_Lamp_(on)     terrain.png  4,13
 125  Oak_Wooden_D._Slab     terrain.png  4,0    0
 125  Spruce_Wooden_D._Slab  terrain.png  6,12   1
 125  Birch_Wooden_D._Slab   terrain.png  6,13   2
 125  Jungle_Wooden_D._Slab  terrain.png  7,12   3
 126  Oak_Wooden_Slab        special.png  3,0    0
 126  Spruce_Wooden_Slab     special.png  4,0    1
 126  Birch_Wooden_Slab      special.png  5,0    2
 126  Jungle_Wooden_Slab     special.png  6,0    3
 127  Cocoa_Plant            special.png  15,5
 128  Sandstone_Stairs       special.png  8,1
 129  Emerald_Ore            terrain.png  11,10
 130  Ender_Chest            special.png  1,6
 131  Tripwire_Hook          terrain.png  12,10
 132  Tripwire               terrain.png  5,11
 133  Block_of_Emerald       terrain.png  9,1
 134  Spruce_Wood_Stairs     special.png  4,1
 135  Birch_Wood_Stairs      special.png  5,1
 136  Jungle_Wood_Stairs     special.png  6,1
 137  Command_Block          terrain.png  8,11
 138  Beacon                 special.png  2,6
 139  Cobblestone_Wall       special.png  1,2    0
 139  Moss_Stone_Wall        special.png  0,2    1
 140  Flower_Pot             terrain.png  9,11
 141  Carrots                terrain.png  11,12
 142  Potatoes               terrain.png  12,12
 143  Wooden_Button          special.png  3,3
 144  Head                     items.png  0,14
 145  Anvil                  special.png  3,6    0
 145  Slightly_Damaged_Anvil special.png  4,6    1
 145  Very_Damaged_Anvil     special.png  5,6    2
 146  Trapped_Chest                    none.png  0,0
 147  Weighted_Pressure_Plate_(Light)  none.png  0,0
 148  Weighted_Pressure_Plate_(Heavy)  none.png  0,0
 149  Redstone_Comparator_(inactive)   none.png  0,0
 150  Redstone_Comparator_(active)     none.png  0,0
 151  Daylight_Sensor                  none.png  0,0
 152  Block_of_Redstone                none.png  0,0
 153  Nether_Quartz_Ore                none.png  0,0
 154  Hopper                           none.png  0,0
 155  Block_of_Quartz                  none.png  0,0    0
 155  Chiseled_Quartz_Block            none.png  0,0    1
 155  Pillar_Quartz_Block              none.png  0,0    2
 156  Quartz_Stairs                    none.png  0,0
 157  Activator_Rail                   none.png  0,0
 158  Dropper                          none.png  0,0
 159  Stained_Clay                     none.png  0,0
 170  Hay_Block                        none.png  0,0
 171  Carpet                           none.png  0,0
 172  Hardened_Clay                    none.png  0,0
 173  Block_of_Coal                    none.png  0,0

#            Items
# ID  NAME                   FILE       CORDS  DAMAGE
 256  Iron_Shovel            items.png  2,5    +250
 257  Iron_Pickaxe           items.png  2,6    +250
 258  Iron_Axe               items.png  2,7    +250
 259  Flint_and_Steel        items.png  5,0    +64
 260  Apple                  items.png  10,0
 261  Bow                    items.png  5,1    +384
 262  Arrow                  items.png  5,2
 263  Coal                   items.png  7,0    0
 263  Charcoal               items.png  7,0    1
 264  Diamond                items.png  7,3
 265  Iron_Ingot             items.png  7,1
 266  Gold_Ingot             items.png  7,2
 267  Iron_Sword             items.png  2,4    +250
 268  Wooden_Sword           items.png  0,4    +59
 269  Wooden_Shovel          items.png  0,5    +59
 270  Wooden_Pickaxe         items.png  0,6    +59
 271  Wooden_Axe             items.png  0,7    +59
 272  Stone_Sword            items.png  1,4    +131
 273  Stone_Shovel           items.png  1,5    +131
 274  Stone_Pickaxe          items.png  1,6    +131
 275  Stone_Axe              items.png  1,7    +131
 276  Diamond_Sword          items.png  3,4    +1561
 277  Diamond_Shovel         items.png  3,5    +1561
 278  Diamond_Pickaxe        items.png  3,6    +1561
 279  Diamond_Axe            items.png  3,7    +1561
 280  Stick                  items.png  5,3
 281  Bowl                   items.png  7,4
 282  Mushroom_Stew          items.png  8,4    x1
 283  Golden_Sword           items.png  4,4    +32
 284  Golden_Shovel          items.png  4,5    +32
 285  Golden_Pickaxe         items.png  4,6    +32
 286  Golden_Axe             items.png  4,7    +32
 287  String                 items.png  8,0
 288  Feather                items.png  8,1
 289  Gunpowder              items.png  8,2
 290  Wooden_Hoe             items.png  0,8    +59
 291  Stone_Hoe              items.png  1,8    +131
 292  Iron_Hoe               items.png  2,8    +250
 293  Diamond_Hoe            items.png  3,8    +1561
 294  Golden_Hoe             items.png  4,8    +32
 295  Seeds                  items.png  9,0
 296  Wheat                  items.png  9,1
 297  Bread                  items.png  9,2
 298  Leather_Cap            items.png  0,0    +34
 299  Leather_Tunic          items.png  0,1    +48
 300  Leather_Pants          items.png  0,2    +46
 301  Leather_Boots          items.png  0,3    +40
 302  Chainmail_Helmet       items.png  1,0    +68
 303  Chainmail_Chestplate   items.png  1,1    +96
 304  Chainmail_Leggings     items.png  1,2    +92
 305  Chainmail_Boots        items.png  1,3    +80
 306  Iron_Helmet            items.png  2,0    +136
 307  Iron_Chestplate        items.png  2,1    +192
 308  Iron_Leggings          items.png  2,2    +184
 309  Iron_Boots             items.png  2,3    +160
 310  Diamond_Helmet         items.png  3,0    +272
 311  Diamond_Chestplate     items.png  3,1    +384
 312  Diamond_Leggings       items.png  3,2    +368
 313  Diamond_Boots          items.png  3,3    +320
 314  Golden_Helmet          items.png  4,0    +68
 315  Golden_Chestplate      items.png  4,1    +96
 316  Golden_Leggings        items.png  4,2    +92
 317  Golden_Boots           items.png  4,3    +80
 318  Flint                  items.png  6,0
 319  Raw_Porkchop           items.png  7,5
 320  Cooked_Porkchop        items.png  8,5
 321  Painting               items.png  10,1
 322  Golden_Apple           items.png  11,0
 322  Ench._Golden_Apple   special.png  0,3    1
 323  Sign                   items.png  10,2   x16
 324  Wooden_Door            items.png  11,2   x1
 325  Bucket                 items.png  10,4   x16
 326  Water_Bucket           items.png  11,4   x1
 327  Lava_Bucket            items.png  12,4   x1
 328  Minecart               items.png  7,8    x1
 329  Saddle                 items.png  8,6    x1
 330  Iron_Door              items.png  12,2   x1
 331  Redstone               items.png  8,3
 332  Snowball               items.png  14,0   x16
 333  Boat                   items.png  8,8    x1
 334  Leather                items.png  7,6
 335  Milk                   items.png  13,4   x1
 336  Brick                  items.png  6,1
 337  Clay                   items.png  9,3
 338  Sugar_Canes            items.png  11,1
 339  Paper                  items.png  10,3
 340  Book                   items.png  11,3
 341  Slimeball              items.png  14,1
 342  Minecart_with_Chest    items.png  7,9    x1
 343  Minecart_with_Furnace  items.png  7,10   x1
 344  Egg                    items.png  12,0
 345  Compass                items.png  6,3    (x1)
 346  Fishing_Rod            items.png  5,4    +64
 347  Clock                  items.png  6,4    (x1)
 348  Glowstone_Dust         items.png  9,4
 349  Raw_Fish               items.png  9,5
 350  Cooked_Fish            items.png  10,5
 351  Ink_Sack               items.png  14,4   0
 351  Rose_Red               items.png  14,5   1
 351  Cactus_Green           items.png  14,6   2
 351  Cocoa_Beans            items.png  14,7   3
 351  Lapis_Lazuli           items.png  14,8   4
 351  Purple_Dye             items.png  14,9   5
 351  Cyan_Dye               items.png  14,10  6
 351  Light_Gray_Dye         items.png  14,11  7
 351  Gray_Dye               items.png  15,4   8
 351  Pink_Dye               items.png  15,5   9
 351  Lime_Dye               items.png  15,6   10
 351  Dandelion_Yellow       items.png  15,7   11
 351  Light_Blue_Dye         items.png  15,8   12
 351  Magenta_Dye            items.png  15,9   13
 351  Orange_Dye             items.png  15,10  14
 351  Bone_Meal              items.png  15,11  15
 352  Bone                   items.png  12,1
 353  Sugar                  items.png  13,0
 354  Cake                   items.png  13,1   x1
 355  Bed                    items.png  13,2   x1
 356  Redstone_Repeater      items.png  6,5
 357  Cookie                 items.png  12,5
 358  Map                    items.png  12,3   x1
 359  Shears                 items.png  13,5   +238
 360  Melon                  items.png  13,6
 361  Pumpkin_Seeds          items.png  13,3
 362  Melon_Seeds            items.png  14,3
 363  Raw_Beef               items.png  9,6
 364  Steak                  items.png  10,6
 365  Raw_Chicken            items.png  9,7
 366  Cooked_Chicken         items.png  10,7
 367  Rotten_Flesh           items.png  11,5
 368  Ender_Pearl            items.png  11,6
 369  Blaze_Rod              items.png  12,6
 370  Ghast_Tear             items.png  11,7
 371  Gold_Nugget            items.png  12,7
 372  Nether_Wart            items.png  13,7
 373  Potion               special.png  0,14
 374  Glass_Bottle           items.png  12,8
 375  Spider_Eye             items.png  11,8
 376  Fermented_Spider_Eye   items.png  10,8
 377  Blaze_Powder           items.png  13,9
 378  Magma_Cream            items.png  13,10
 379  Brewing_Stand          items.png  12,10  (x1)
 380  Cauldron               items.png  12,9   (x1)
 381  Eye_of_Ender           items.png  11,9
 382  Glistering_Melon       items.png  9,8
 383  Spawn_Egg              items.png  9,9
 384  Bottle_o'_Enchanting   items.png  11,10
 385  Fire_Charge            items.png  14,2
 386  Book_and_Quill         items.png  11,11  x1
 387  Written_Book           items.png  12,11  x1
 388  Emerald                items.png  10,11
 389  Item_Frame             items.png  14,12
 390  Flower_Pot             items.png  13,11
 391  Carrot                 items.png  8,7
 392  Potato                 items.png  7,7
 393  Baked_Potato           items.png  6,7
 394  Poisonous_Potato       items.png  6,8
 395  Empty_Map              items.png  13,12  x1
 396  Golden_Carrot          items.png  6,9
 397  Skeleton_Head          items.png  0,14   0
 397  Wither_Skeleton_Head   items.png  1,14   1
 397  Zombie_Head            items.png  2,14   2
 397  Human_Head             items.png  3,14   3
 397  Creeper_Head           items.png  4,14   4
 398  Carrot_on_a_Stick      items.png  6,6    +25
 399  Nether_Star            items.png  9,11
 400  Pumpkin_Pie            items.png  8,9
 401  Firework_Rocket        items.png  9,12
 402  Firework_Star          items.png  10,12
 403  Enchanted_Book         items.png  15,12
 404  Redstone_Comparator     none.png  0,0
 405  Nether_Brick            none.png  0,0
 406  Nether_Quartz           none.png  0,0
 407  Minecart_with_TNT       none.png  0,0
 408  Minecart_with_Hopper    none.png  0,0
 417  Iron_Horse_Armor        none.png  0,0
 418  Gold_Horse_Armor        none.png  0,0
 419  Diamond_Horse_Armor     none.png  0,0
 420  Lead                    none.png  0,0
 421  Name_Tag                none.png  0,0
2256  C418_-_13              items.png  0,15   x1
2257  C418_-_cat             items.png  1,15   x1
2258  C418_-_blocks          items.png  2,15   x1
2259  C418_-_chirp           items.png  3,15   x1
2260  C418_-_far             items.png  4,15   x1
2261  C418_-_mall            items.png  5,15   x1
2262  C418_-_mellohi         items.png  6,15   x1
2263  C418_-_stal            items.png  7,15   x1
2264  C418_-_strad           items.png  8,15   x1
2265  C418_-_ward            items.png  9,15   x1
2266  C418_-_11              items.png  10,15  x1
2267  C418_-_wait          special.png  0,8    x1

#           Potions
# ID  NAME                    FILE         CORDS  DAMAGE
 373  Water_Bottle            special.png  0,14   0
 373  Awkward_Potion          special.png  1,14   16
 373  Thick_Potion            special.png  1,14   32
 373  Mundane_Potion          special.png  1,14   64
 373  Mundane_Potion          special.png  1,14   8192
 373  Regeneration_(0:45)     special.png  2,14   8193
 373  Regeneration_(2:00)     special.png  2,14   8257
 373  Regeneration_II_(0:22)  special.png  2,14   8225
 373  Swiftness_(3:00)        special.png  3,14   8194
 373  Swiftness_(8:00)        special.png  3,14   8258
 373  Swiftness_II_(1:30)     special.png  3,14   8226
 373  Fire_Resistance_(3:00)  special.png  4,14   8195
 373  Fire_Resistance_(3:00)  special.png  4,14   8227
 373  Fire_Resistance_(8:00)  special.png  4,14   8259
 373  Healing                 special.png  6,14   8197
 373  Healing                 special.png  6,14   8261
 373  Healing_II              special.png  6,14   8229
 373  Strength_(3:00)         special.png  8,14   8201
 373  Strength_(8:00)         special.png  8,14   8265
 373  Strength_II_(1:30)      special.png  8,14   8233
 373  Poison_(0:45)           special.png  5,14   8196
 373  Poison_(2:00)           special.png  5,14   8260
 373  Poison_II_(0:22)        special.png  5,14   8228
 373  Weakness_(1:30)         special.png  7,14   8200
 373  Weakness_(1:30)         special.png  7,14   8332
 373  Weakness_(4:00)         special.png  7,14   8264
 373  Slowness_(1:30)         special.png  9,14   8202
 373  Slowness_(1:30)         special.png  9,14   8234
 373  Slowness_(4:00)         special.png  9,14   8266
 373  Harming                 special.png  10,14  8204
 373  Harming                 special.png  10,14  8268
 373  Harming_II              special.png  10,14  8236
 373  Night_Vision_(3:00)     special.png  11,14  8198
 373  Night_Vision_(8:00)     special.png  11,14  8262
 373  Invisibility_(3:00)     special.png  12,14  8206
 373  Invisibility_(8:00)     special.png  12,14  8270
# Unbrewable:
 373  Regeneration_II_(1:00)  special.png  2,14   8289
 373  Swiftness_II_(4:00)     special.png  3,14   8290
 373  Strength_II_(4:00)      special.png  8,14   8297
 373  Poison_II_(1:00)        special.png  5,14   8292

#           Splash Potions
# ID  NAME                    FILE         CORDS  DAMAGE
 373  Splash_Mundane          special.png  1,13   16384
 373  Regeneration_(0:33)     special.png  2,13   16385
 373  Regeneration_(1:30)     special.png  2,13   16499
 373  Regeneration_II_(0:16)  special.png  2,13   16417
 373  Swiftness_(2:15)        special.png  3,13   16386
 373  Swiftness_(6:00)        special.png  3,13   16450
 373  Swiftness_II_(1:07)     special.png  3,13   16418
 373  Fire_Resistance_(2:15)  special.png  4,13   16387
 373  Fire_Resistance_(2:15)  special.png  4,13   16419
 373  Fire_Resistance_(6:00)  special.png  4,13   16451
 373  Healing                 special.png  6,13   16389
 373  Healing                 special.png  6,13   16453
 373  Healing_II              special.png  6,13   16421
 373  Strength_(2:15)         special.png  8,13   16393
 373  Strength_(6:00)         special.png  8,13   16457
 373  Strength_II_(1:07)      special.png  8,13   16425
 373  Poison_(0:33)           special.png  5,13   16388
 373  Poison_(1:30)           special.png  5,13   16452
 373  Poison_II_(0:16)        special.png  5,13   16420
 373  Weakness_(1:07)         special.png  7,13   16392
 373  Weakness_(1:07)         special.png  7,13   16424
 373  Weakness_(3:00)         special.png  7,13   16456
 373  Slowness_(1:07)         special.png  9,13   16394
 373  Slowness_(1:07)         special.png  9,13   16426
 373  Slowness_(3:00)         special.png  9,13   16458
 373  Harming                 special.png  10,13  16396
 373  Harming                 special.png  10,13  16460
 373  Harming_II              special.png  10,13  16428
 373  Night_Vision_(3:00)     special.png  11,13  16390
 373  Night_Vision_(8:00)     special.png  11,13  16454
 373  Invisibility_(3:00)     special.png  12,13  16398
 373  Invisibility_(8:00)     special.png  12,13  16462
# Unbrewable:
 373  Regeneration_II_(0:45)  special.png  2,13   16481
 373  Swiftness_II_(3:00)     special.png  3,13   16482
 373  Strength_II_(3:00)      special.png  8,13   16489
 373  Poison_II_(0:45)        special.png  5,13   16484

#           Spawn Eggs
# ID  NAME                   FILE         CORDS  DAMAGE
 383  Spawn_Creeper          special.png  0,9    50
 383  Spawn_Skeleton         special.png  1,9    51
 383  Spawn_Spider           special.png  2,9    52
 383  Spawn_Zombie           special.png  3,9    54
 383  Spawn_Slime            special.png  4,9    55
 383  Spawn_Ghast            special.png  0,10   56
 383  Spawn_Zombie_Pigmen    special.png  1,10   57
 383  Spawn_Enderman         special.png  2,10   58
 383  Spawn_Cave_Spider      special.png  3,10   59
 383  Spawn_Silverfish       special.png  4,10   60
 383  Spawn_Blaze            special.png  0,11   61
 383  Spawn_Magma_Cube       special.png  1,11   62
 383  Spawn_Bat              special.png  5,9    65
 383  Spawn_Witch            special.png  5,10   66
 383  Spawn_Pig              special.png  2,11   90
 383  Spawn_Sheep            special.png  3,11   91
 383  Spawn_Cow              special.png  4,11   92
 383  Spawn_Chicken          special.png  0,12   93
 383  Spawn_Squid            special.png  1,12   94
 383  Spawn_Wolf             special.png  2,12   95
 383  Spawn_Mooshroom        special.png  3,12   96
 383  Spawn_Villager         special.png  4,12   120

#           Groups
# NAME      ICON  ITEMS
# Column 1
~ Natural    2     2,3,12,24,128,44~1,13,82,79,80,78
~ Stone      1     1,4,48,67,44~3,139,140,98,109,44~5,44~0,45,108,44~4,101
~ Wood       5     17,5,53,134,135,136,126,47,85,107,20,102,30
~ NetherEnd  87    87,88,89,348,112,114,113,372,121,122
~ Ores       56    16,15,14,56,129,73,21,49,42,41,57,133,22,263~0,265,266,264,388
~ Special    54    46,52,58,54,130,61,23,25,84,116,379,380,138,146~0,321,389,323,324,330,355,65,96,390,397
~ Plants1    81    31~1,31~2,106,111,18,81,86,91,103,110
~ Plants2    6     295,361,362,6,296,338,37,38,39,40,32
~ Transport  328   66,27,28,328,342,343,333,329,398
~ Logic      331   331,76,356,69,70,72,131,77,144,33,29,123,137
~ Wool       35    35~0,35~8,35~7,35~15,35~14,35~12,35~1,35~4,35~5,35~13,35~11,35~3,35~9,35~10,35~2,35~6
~ Dye        351   351~15,351~7,351~8,351~0,351~1,351~3,351~14,351~11,351~10,351~2,351~4,351~12,351~6,351~5,351~13,351~9
# Column 2
~ TierWood   299   298,299,300,301,269,270,271,290,268
~ TierStone  303   302,303,304,305,273,274,275,291,272
~ TierIron   307   306,307,308,309,256,257,258,292,267
~ TierDiam   311   310,311,312,313,277,278,279,293,276
~ TierGold   315   314,315,316,317,284,285,286,294,283
~ Tools      261   50,261,262,259,346,359,345,347,395,358,325,326,327,335,384,385,386,387
~ Food       297   260,322,282,297,360,319,320,363,364,365,366,349,350,354,357,391,396,392,393,394,400
~ Items      318   280,281,318,337,336,353,339,340,332,376,377,382,381
~ Drops      341   344,288,334,287,352,289,367,375,341,368,369,370,371,378,399
~ Music      2257  2256,2257,2258,2259,2260,2261,2262,2263,2264,2265,2266,2267
~ Potion     373   373~0,373~16,373~32,373~8192,373~8193,373~8257,373~8225,373~8289,373~8194,373~8258,373~8226,373~8290,373~8195,373~8259,373~8197,373~8229,373~8201,373~8265,373~8233,373~8297,373~8196,373~8260,373~8228,373~8292,373~8200,373~8264,373~8202,373~8266,373~8204,373~8236,373~8198,373~8262,373~8206,373~8270,373~16384,373~16385,373~16499,373~16417,373~16481,373~16386,373~16450,373~16418,373~16482,373~16387,373~16451,373~16389,373~16421,373~16393,373~16457,373~16425,373~16489,373~16388,373~16452,373~16420,373~16484,373~16392,373~16456,373~16394,373~16458,373~16396,373~16428,373~16390,373~16454,373~16398,373~16462
~ Eggs       383   383~50,383~51,383~52,383~54,383~55,383~56,383~57,383~58,383~59,383~60,383~61,383~62,383~65,383~66,383~90,383~91,383~92,383~93,383~94,383~95,383~96,383~120

#            Enchantments
# EID  NAME                   MAX  ITEMS
+   0  Protection             4    298,299,300,301,302,303,304,305,306,307,308,309,310,311,312,313,314,315,316,317
+   1  Fire_Protection        4    298,299,300,301,302,303,304,305,306,307,308,309,310,311,312,313,314,315,316,317
+   2  Feather_Falling        4    301,305,309,313,317
+   3  Blast_Protection       4    298,299,300,301,302,303,304,305,306,307,308,309,310,311,312,313,314,315,316,317
+   4  Projectile_Protection  4    298,299,300,301,302,303,304,305,306,307,308,309,310,311,312,313,314,315,316,317
+   5  Respiration            3    298,302,306,310,314
+   6  Aqua_Affinity          1    298,302,306,310,314
+  16  Sharpness              5    268,272,267,276,283
+  17  Smite                  5    268,272,267,276,283
+  18  Bane_of_Arthropods     5    268,272,267,276,283
+  19  Knockback              2    268,272,267,276,283
+  20  Fire_Aspect            2    268,272,267,276,283
+  21  Looting                3    268,272,267,276,283
+  32  Efficiency             5    269,270,271,273,274,275,256,257,258,277,278,279,284,285,286
+  33  Silk_Touch             1    269,270,271,273,274,275,256,257,258,277,278,279,284,285,286
+  34  Unbreaking             3    269,270,271,273,274,275,256,257,258,277,278,279,284,285,286
+  35  Fortune                3    269,270,271,273,274,275,256,257,258,277,278,279,284,285,286
+  48  Power                  5    261
+  49  Punch                  2    261
+  50  Flame                  1    261
+  51  Infinity               1    261
"""


class ItemType (object):
    def __init__(self, id, name, imagefile=None, imagecoords=None, maxdamage=0, damagevalue=0, stacksize=64):
        self.id = id
        self.name = name
        self.imagefile = imagefile
        self.imagecoords = imagecoords
        self.maxdamage = maxdamage
        self.damagevalue = damagevalue
        self.stacksize = stacksize

    def __repr__(self):
        return "ItemType({0}, '{1}')".format(self.id, self.name)

    def __str__(self):
        return "ItemType {0}: {1}".format(self.id, self.name)


class Items (object):
    items_txt = items_txt

    def __init__(self, filename=None):
        if filename is None:
            items_txt = self.items_txt
        else:
            try:
                with file(filename) as f:
                    items_txt = f.read()
            except Exception, e:
                logger.info("Error reading '%s': %s", filename, e)
                logger.info("Using internal data.")
                items_txt = self.items_txt

        self.itemtypes = {}
        self.itemgroups = []

        for line in items_txt.split("\n"):
            try:
                line = line.strip()
                if len(line) == 0:
                    continue
                if line[0] == "#":  # comment
                    continue
                if line[0] == "+":  # enchantment
                    continue
                if line[0] == "~":  # category
                    fields = line.split()
                    name, icon, items = fields[1:4]
                    items = items.split(",")
                    self.itemgroups.append((name, icon, items))
                    continue

                stacksize = 64
                damagevalue = None
                maxdamage = 0

                fields = line.split()
                if len(fields) >= 4:
                    maxdamage = None
                    id, name, imagefile, imagecoords = fields[0:4]
                    if len(fields) > 4:
                        info = fields[4]
                        if info[0] == '(':
                            info = info[1:-1]
                        if info[0] == 'x':
                            stacksize = int(info[1:])
                        elif info[0] == '+':
                            maxdamage = int(info[1:])
                        else:
                            damagevalue = int(info)
                    id = int(id)
                    name = name.replace("_", " ")
                    imagecoords = imagecoords.split(",")

                    self.itemtypes[(id, damagevalue)] = ItemType(id, name, imagefile, imagecoords, maxdamage, damagevalue, stacksize)
            except Exception, e:
                print "Error reading line:", e
                print "Line: ", line
                print

        self.names = dict((item.name, item.id) for item in self.itemtypes.itervalues())

    def findItem(self, id=0, damage=None):
        item = self.itemtypes.get((id, damage))
        if item:
            return item

        item = self.itemtypes.get((id, None))
        if item:
            return item

        item = self.itemtypes.get((id, 0))
        if item:
            return item

        return ItemType(id, "Unknown Item {0}:{1}".format(id, damage), damagevalue=damage)
        #raise ItemNotFound, "Item {0}:{1} not found".format(id, damage)


class ItemNotFound(KeyError):
    pass

items = Items()

########NEW FILE########
__FILENAME__ = javalevel
'''
Created on Jul 22, 2011

@author: Rio
'''

__all__ = ["MCJavaLevel"]

from cStringIO import StringIO
import gzip
from level import MCLevel
from logging import getLogger
from numpy import fromstring
import os
import re

log = getLogger(__name__)

class MCJavaLevel(MCLevel):
    def setBlockDataAt(self, *args):
        pass

    def blockDataAt(self, *args):
        return 0

    @property
    def Height(self):
        return self.Blocks.shape[2]

    @property
    def Length(self):
        return self.Blocks.shape[1]

    @property
    def Width(self):
        return self.Blocks.shape[0]

    def guessSize(self, data):
        Width = 64
        Length = 64
        Height = 64
        if data.shape[0] <= (32 * 32 * 64) * 2:
            log.warn(u"Can't guess the size of a {0} byte level".format(data.shape[0]))
            raise IOError("MCJavaLevel attempted for smaller than 64 blocks cubed")
        if data.shape[0] > (64 * 64 * 64) * 2:
            Width = 128
            Length = 128
            Height = 64
        if data.shape[0] > (128 * 128 * 64) * 2:
            Width = 256
            Length = 256
            Height = 64
        if data.shape[0] > (256 * 256 * 64) * 2:  # could also be 256*256*256
            Width = 512
            Length = 512
            Height = 64
        if data.shape[0] > 512 * 512 * 64 * 2:  # just to load shadowmarch castle
            Width = 512
            Length = 512
            Height = 256
        return Width, Length, Height

    @classmethod
    def _isDataLevel(cls, data):
        return (data[0] == 0x27 and
                data[1] == 0x1B and
                data[2] == 0xb7 and
                data[3] == 0x88)

    def __init__(self, filename, data):
        self.filename = filename
        if isinstance(data, basestring):
            data = fromstring(data, dtype='uint8')
        self.filedata = data

        # try to take x,z,y from the filename
        r = re.findall("\d+", os.path.basename(filename))
        if r and len(r) >= 3:
            (w, l, h) = map(int, r[-3:])
            if w * l * h > data.shape[0]:
                log.info("Not enough blocks for size " + str((w, l, h)))
                w, l, h = self.guessSize(data)
        else:
            w, l, h = self.guessSize(data)

        log.info(u"MCJavaLevel created for potential level of size " + str((w, l, h)))

        blockCount = h * l * w
        if blockCount > data.shape[0]:
            raise ValueError("Level file does not contain enough blocks! (size {s}) Try putting the size into the filename, e.g. server_level_{w}_{l}_{h}.dat".format(w=w, l=l, h=h, s=data.shape))

        blockOffset = data.shape[0] - blockCount
        blocks = data[blockOffset:blockOffset + blockCount]

        maxBlockType = 64  # maximum allowed in classic
        while max(blocks[-4096:]) > maxBlockType:
            # guess the block array by starting at the end of the file
            # and sliding the blockCount-sized window back until it
            # looks like every block has a valid blockNumber
            blockOffset -= 1
            blocks = data[blockOffset:blockOffset + blockCount]

            if blockOffset <= -data.shape[0]:
                raise IOError("Can't find a valid array of blocks <= #%d" % maxBlockType)

        self.Blocks = blocks
        self.blockOffset = blockOffset
        blocks.shape = (w, l, h)
        blocks.strides = (1, w, w * l)

    def saveInPlace(self):

        s = StringIO()
        g = gzip.GzipFile(fileobj=s, mode='wb')


        g.write(self.filedata.tostring())
        g.flush()
        g.close()

        try:
            os.rename(self.filename, self.filename + ".old")
        except Exception, e:
            pass

        try:
            with open(self.filename, 'wb') as f:
                f.write(s.getvalue())
        except Exception, e:
            log.info(u"Error while saving java level in place: {0}".format(e))
            try:
                os.remove(self.filename)
            except:
                pass
            os.rename(self.filename + ".old", self.filename)

        try:
            os.remove(self.filename + ".old")
        except Exception, e:
            pass


class MCSharpLevel(MCLevel):
    """ int magic = convert(data.readShort())
        logger.trace("Magic number: {}", magic)
        if (magic != 1874)
            throw new IOException("Only version 1 MCSharp levels supported (magic number was "+magic+")")

        int width = convert(data.readShort())
        int height = convert(data.readShort())
        int depth = convert(data.readShort())
        logger.trace("Width: {}", width)
        logger.trace("Depth: {}", depth)
        logger.trace("Height: {}", height)

        int spawnX = convert(data.readShort())
        int spawnY = convert(data.readShort())
        int spawnZ = convert(data.readShort())

        int spawnRotation = data.readUnsignedByte()
        int spawnPitch = data.readUnsignedByte()

        int visitRanks = data.readUnsignedByte()
        int buildRanks = data.readUnsignedByte()

        byte[][][] blocks = new byte[width][height][depth]
        int i = 0
        BlockManager manager = BlockManager.getBlockManager()
        for(int z = 0;z<depth;z++) {
            for(int y = 0;y<height;y++) {
                byte[] row = new byte[height]
                data.readFully(row)
                for(int x = 0;x<width;x++) {
                    blocks[x][y][z] = translateBlock(row[x])
                }
            }
        }

        lvl.setBlocks(blocks, new byte[width][height][depth], width, height, depth)
        lvl.setSpawnPosition(new Position(spawnX, spawnY, spawnZ))
        lvl.setSpawnRotation(new Rotation(spawnRotation, spawnPitch))
        lvl.setEnvironment(new Environment())

        return lvl
    }"""

########NEW FILE########
__FILENAME__ = level
'''
Created on Jul 22, 2011

@author: Rio
'''

import blockrotation
from box import BoundingBox
from collections import defaultdict
from entity import Entity, TileEntity
import itertools
from logging import getLogger
import materials
from math import floor
from mclevelbase import ChunkMalformed, ChunkNotPresent, exhaust
import nbt
from numpy import argmax, swapaxes, zeros, zeros_like
import os.path

log = getLogger(__name__)

def computeChunkHeightMap(materials, blocks, HeightMap=None):
    """Computes the HeightMap array for a chunk, which stores the lowest
    y-coordinate of each column where the sunlight is still at full strength.
    The HeightMap array is indexed z,x contrary to the blocks array which is x,z,y.

    If HeightMap is passed, fills it with the result and returns it. Otherwise, returns a
    new array.
    """

    lightAbsorption = materials.lightAbsorption[blocks]
    heights = extractHeights(lightAbsorption)
    heights = heights.swapaxes(0, 1)
    if HeightMap is None:
        return heights.astype('uint8')
    else:
        HeightMap[:] = heights
        return HeightMap


def extractHeights(array):
    """ Given an array of bytes shaped (x, z, y), return the coordinates of the highest
    non-zero value in each y-column into heightMap
    """

    # The fastest way I've found to do this is to make a boolean array with >0,
    # then turn it upside down with ::-1 and use argmax to get the _first_ nonzero
    # from each column.

    w, h = array.shape[:2]
    heightMap = zeros((w, h), 'int16')

    heights = argmax((array > 0)[..., ::-1], 2)
    heights = array.shape[2] - heights

    # if the entire column is air, argmax finds the first air block and the result is a top height column
    # top height columns won't ever have air in the top block so we can find air columns by checking for both
    heights[(array[..., -1] == 0) & (heights == array.shape[2])] = 0

    heightMap[:] = heights

    return heightMap


def getSlices(box, height):
    """ call this method to iterate through a large slice of the world by
        visiting each chunk and indexing its data with a subslice.

    this returns an iterator, which yields 3-tuples containing:
    +  a pair of chunk coordinates (cx, cz),
    +  a x,z,y triplet of slices that can be used to index the AnvilChunk's data arrays,
    +  a x,y,z triplet representing the relative location of this subslice within the requested world slice.

    Note the different order of the coordinates between the 'slices' triplet
    and the 'offset' triplet. x,z,y ordering is used only
    to index arrays, since it reflects the order of the blocks in memory.
    In all other places, including an entity's 'Pos', the order is x,y,z.
    """

    # when yielding slices of chunks on the edge of the box, adjust the
    # slices by an offset
    minxoff, minzoff = box.minx - (box.mincx << 4), box.minz - (box.mincz << 4)
    maxxoff, maxzoff = box.maxx - (box.maxcx << 4) + 16, box.maxz - (box.maxcz << 4) + 16

    newMinY = 0
    if box.miny < 0:
        newMinY = -box.miny
    miny = max(0, box.miny)
    maxy = min(height, box.maxy)

    for cx in range(box.mincx, box.maxcx):
        localMinX = 0
        localMaxX = 16
        if cx == box.mincx:
            localMinX = minxoff

        if cx == box.maxcx - 1:
            localMaxX = maxxoff
        newMinX = localMinX + (cx << 4) - box.minx

        for cz in range(box.mincz, box.maxcz):
            localMinZ = 0
            localMaxZ = 16
            if cz == box.mincz:
                localMinZ = minzoff
            if cz == box.maxcz - 1:
                localMaxZ = maxzoff
            newMinZ = localMinZ + (cz << 4) - box.minz
            slices, point = (
                (slice(localMinX, localMaxX), slice(localMinZ, localMaxZ), slice(miny, maxy)),
                (newMinX, newMinY, newMinZ)
            )

            yield (cx, cz), slices, point


class MCLevel(object):
    """ MCLevel is an abstract class providing many routines to the different level types,
    including a common copyEntitiesFrom built on class-specific routines, and
    a dummy getChunk/allChunks for the finite levels.

    MCLevel subclasses must have Width, Length, and Height attributes.  The first two are always zero for infinite levels.
    Subclasses must also have Blocks, and optionally Data and BlockLight.
    """

    ### common to Creative, Survival and Indev. these routines assume
    ### self has Width, Height, Length, and Blocks

    materials = materials.classicMaterials
    isInfinite = False

    root_tag = None

    Height = None
    Length = None
    Width = None

    players = ["Player"]
    dimNo = 0
    parentWorld = None
    world = None

    @classmethod
    def isLevel(cls, filename):
        """Tries to find out whether the given filename can be loaded
        by this class.  Returns True or False.

        Subclasses should implement _isLevel, _isDataLevel, or _isTagLevel.
        """
        if hasattr(cls, "_isLevel"):
            return cls._isLevel(filename)

        with file(filename) as f:
            data = f.read()

        if hasattr(cls, "_isDataLevel"):
            return cls._isDataLevel(data)

        if hasattr(cls, "_isTagLevel"):
            try:
                root_tag = nbt.load(filename, data)
            except:
                return False

            return cls._isTagLevel(root_tag)

        return False

    def getWorldBounds(self):
        return BoundingBox((0, 0, 0), self.size)

    @property
    def displayName(self):
        return os.path.basename(self.filename)

    @property
    def size(self):
        "Returns the level's dimensions as a tuple (X,Y,Z)"
        return self.Width, self.Height, self.Length

    @property
    def bounds(self):
        return BoundingBox((0, 0, 0), self.size)

    def close(self):
        pass

    # --- Entity Methods ---
    def addEntity(self, entityTag):
        pass

    def addEntities(self, entities):
        pass

    def tileEntityAt(self, x, y, z):
        return None

    def addTileEntity(self, entityTag):
        pass

    def getEntitiesInBox(self, box):
        return []

    def getTileEntitiesInBox(self, box):
        return []

    def removeEntitiesInBox(self, box):
        pass

    def removeTileEntitiesInBox(self, box):
        pass

    @property
    def chunkCount(self):
        return (self.Width + 15 >> 4) * (self.Length + 15 >> 4)

    @property
    def allChunks(self):
        """Returns a synthetic list of chunk positions (xPos, zPos), to fake
        being a chunked level format."""
        return itertools.product(xrange(0, self.Width + 15 >> 4), xrange(0, self.Length + 15 >> 4))

    def getChunks(self, chunks=None):
        """ pass a list of chunk coordinate tuples to get an iterator yielding
        AnvilChunks. pass nothing for an iterator of every chunk in the level.
        the chunks are automatically loaded."""
        if chunks is None:
            chunks = self.allChunks
        return (self.getChunk(cx, cz) for (cx, cz) in chunks if self.containsChunk(cx, cz))

    def _getFakeChunkEntities(self, cx, cz):
        """Returns Entities, TileEntities"""
        return nbt.TAG_List(), nbt.TAG_List()

    def getChunk(self, cx, cz):
        """Synthesize a FakeChunk object representing the chunk at the given
        position. Subclasses override fakeBlocksForChunk and fakeDataForChunk
        to fill in the chunk arrays"""

        f = FakeChunk()
        f.world = self
        f.chunkPosition = (cx, cz)

        f.Blocks = self.fakeBlocksForChunk(cx, cz)

        f.Data = self.fakeDataForChunk(cx, cz)

        whiteLight = zeros_like(f.Blocks)
        whiteLight[:] = 15

        f.BlockLight = whiteLight
        f.SkyLight = whiteLight

        f.Entities, f.TileEntities = self._getFakeChunkEntities(cx, cz)

        f.root_tag = nbt.TAG_Compound()

        return f

    def getAllChunkSlices(self):
        slices = (slice(None), slice(None), slice(None),)
        box = self.bounds
        x, y, z = box.origin

        for cpos in self.allChunks:
            xPos, zPos = cpos
            try:
                chunk = self.getChunk(xPos, zPos)
            except (ChunkMalformed, ChunkNotPresent):
                continue

            yield (chunk, slices, (xPos * 16 - x, 0, zPos * 16 - z))

    def _getSlices(self, box):
        if box == self.bounds:
            log.info("All chunks selected! Selecting %s chunks instead of %s", self.chunkCount, box.chunkCount)
            y = box.miny
            slices = slice(0, 16), slice(0, 16), slice(0, box.maxy)

            def getAllSlices():
                for cPos in self.allChunks:
                    x, z = cPos
                    x *= 16
                    z *= 16
                    x -= box.minx
                    z -= box.minz
                    yield cPos, slices, (x, y, z)
            return getAllSlices()
        else:
            return getSlices(box, self.Height)

    def getChunkSlices(self, box):
        return ((self.getChunk(*cPos), slices, point)
                for cPos, slices, point in self._getSlices(box)
                if self.containsChunk(*cPos))

    def containsPoint(self, x, y, z):
        return (x, y, z) in self.bounds

    def containsChunk(self, cx, cz):
        bounds = self.bounds
        return ((bounds.mincx <= cx < bounds.maxcx) and
                (bounds.mincz <= cz < bounds.maxcz))

    def fakeBlocksForChunk(self, cx, cz):
        # return a 16x16xH block array for rendering.  Alpha levels can
        # just return the chunk data.  other levels need to reorder the
        # indices and return a slice of the blocks.

        cxOff = cx << 4
        czOff = cz << 4
        b = self.Blocks[cxOff:cxOff + 16, czOff:czOff + 16, 0:self.Height, ]
        # (w, l, h) = b.shape
        # if w<16 or l<16:
        #    b = resize(b, (16,16,h) )
        return b

    def fakeDataForChunk(self, cx, cz):
        # Data is emulated for flexibility
        cxOff = cx << 4
        czOff = cz << 4

        if hasattr(self, "Data"):
            return self.Data[cxOff:cxOff + 16, czOff:czOff + 16, 0:self.Height, ]

        else:
            return zeros(shape=(16, 16, self.Height), dtype='uint8')

    # --- Block accessors ---
    def skylightAt(self, *args):
        return 15

    def setSkylightAt(self, *args):
        pass

    def setBlockDataAt(self, x, y, z, newdata):
        pass

    def blockDataAt(self, x, y, z):
        return 0

    def blockLightAt(self, x, y, z):
        return 15

    def blockAt(self, x, y, z):
        if (x, y, z) not in self.bounds:
            return 0
        return self.Blocks[x, z, y]

    def setBlockAt(self, x, y, z, blockID):
        if (x, y, z) not in self.bounds:
            return 0
        self.Blocks[x, z, y] = blockID

    # --- Fill and Replace ---

    from block_fill import fillBlocks, fillBlocksIter

    # --- Transformations ---
    def rotateLeft(self):
        self.Blocks = swapaxes(self.Blocks, 1, 0)[:, ::-1, :]  # x=z; z=-x
        pass

    def roll(self):
        self.Blocks = swapaxes(self.Blocks, 2, 0)[:, :, ::-1]  # x=y; y=-x
        pass

    def flipVertical(self):
        self.Blocks = self.Blocks[:, :, ::-1]  # y=-y
        pass

    def flipNorthSouth(self):
        self.Blocks = self.Blocks[::-1, :, :]  # x=-x
        pass

    def flipEastWest(self):
        self.Blocks = self.Blocks[:, ::-1, :]  # z=-z
        pass

    # --- Copying ---

    from block_copy import copyBlocksFrom, copyBlocksFromIter


    def saveInPlace(self):
        self.saveToFile(self.filename)

    # --- Player Methods ---
    def setPlayerPosition(self, pos, player="Player"):
        pass

    def getPlayerPosition(self, player="Player"):
        return 8, self.Height * 0.75, 8

    def getPlayerDimension(self, player="Player"):
        return 0

    def setPlayerDimension(self, d, player="Player"):
        return

    def setPlayerSpawnPosition(self, pos, player=None):
        pass

    def playerSpawnPosition(self, player=None):
        return self.getPlayerPosition()

    def setPlayerOrientation(self, yp, player="Player"):
        pass

    def getPlayerOrientation(self, player="Player"):
        return -45., 0.

    # --- Dummy Lighting Methods ---
    def generateLights(self, dirtyChunks=None):
        pass

    def generateLightsIter(self, dirtyChunks=None):
        yield 0


class EntityLevel(MCLevel):
    """Abstract subclass of MCLevel that adds default entity behavior"""

    def getEntitiesInBox(self, box):
        """Returns a list of references to entities in this chunk, whose positions are within box"""
        return [ent for ent in self.Entities if Entity.pos(ent) in box]

    def getTileEntitiesInBox(self, box):
        """Returns a list of references to tile entities in this chunk, whose positions are within box"""
        return [ent for ent in self.TileEntities if TileEntity.pos(ent) in box]

    def removeEntitiesInBox(self, box):

        newEnts = []
        for ent in self.Entities:
            if Entity.pos(ent) in box:
                continue
            newEnts.append(ent)

        entsRemoved = len(self.Entities) - len(newEnts)
        log.debug("Removed {0} entities".format(entsRemoved))

        self.Entities.value[:] = newEnts

        return entsRemoved

    def removeTileEntitiesInBox(self, box):

        if not hasattr(self, "TileEntities"):
            return
        newEnts = []
        for ent in self.TileEntities:
            if TileEntity.pos(ent) in box:
                continue
            newEnts.append(ent)

        entsRemoved = len(self.TileEntities) - len(newEnts)
        log.debug("Removed {0} tile entities".format(entsRemoved))

        self.TileEntities.value[:] = newEnts

        return entsRemoved

    def addEntities(self, entities):
        for e in entities:
            self.addEntity(e)

    def addEntity(self, entityTag):
        assert isinstance(entityTag, nbt.TAG_Compound)
        self.Entities.append(entityTag)
        self._fakeEntities = None

    def tileEntityAt(self, x, y, z):
        entities = []
        for entityTag in self.TileEntities:
            if TileEntity.pos(entityTag) == [x, y, z]:
                entities.append(entityTag)

        if len(entities) > 1:
            log.info("Multiple tile entities found: {0}".format(entities))
        if len(entities) == 0:
            return None

        return entities[0]

    def addTileEntity(self, tileEntityTag):
        assert isinstance(tileEntityTag, nbt.TAG_Compound)

        def differentPosition(a):

            return not ((tileEntityTag is a) or TileEntity.pos(a) == TileEntity.pos(tileEntityTag))

        self.TileEntities.value[:] = filter(differentPosition, self.TileEntities)

        self.TileEntities.append(tileEntityTag)
        self._fakeEntities = None

    _fakeEntities = None

    def _getFakeChunkEntities(self, cx, cz):
        """distribute entities into sublists based on fake chunk position
        _fakeEntities keys are (cx, cz) and values are (Entities, TileEntities)"""
        if self._fakeEntities is None:
            self._fakeEntities = defaultdict(lambda: (nbt.TAG_List(), nbt.TAG_List()))
            for i, e in enumerate((self.Entities, self.TileEntities)):
                for ent in e:
                    x, y, z = [Entity, TileEntity][i].pos(ent)
                    ecx, ecz = map(lambda x: (int(floor(x)) >> 4), (x, z))

                    self._fakeEntities[ecx, ecz][i].append(ent)

        return self._fakeEntities[cx, cz]


class ChunkBase(EntityLevel):
    dirty = False
    needsLighting = False

    chunkPosition = NotImplemented
    Blocks = Data = SkyLight = BlockLight = HeightMap = NotImplemented  # override these!

    Width = Length = 16

    @property
    def Height(self):
        return self.world.Height

    @property
    def bounds(self):
        cx, cz = self.chunkPosition
        return BoundingBox((cx << 4, 0, cz << 4), self.size)


    def chunkChanged(self, needsLighting=True):
        self.dirty = True
        self.needsLighting = needsLighting or self.needsLighting

    @property
    def materials(self):
        return self.world.materials


    def getChunkSlicesForBox(self, box):
        """
         Given a BoundingBox enclosing part of the world, return a smaller box enclosing the part of this chunk
         intersecting the given box, and a tuple of slices that can be used to select the corresponding parts
         of this chunk's block and data arrays.
        """
        bounds = self.bounds
        localBox = box.intersect(bounds)

        slices = (
            slice(localBox.minx - bounds.minx, localBox.maxx - bounds.minx),
            slice(localBox.minz - bounds.minz, localBox.maxz - bounds.minz),
            slice(localBox.miny - bounds.miny, localBox.maxy - bounds.miny),
        )
        return localBox, slices


class FakeChunk(ChunkBase):
    @property
    def HeightMap(self):
        if hasattr(self, "_heightMap"):
            return self._heightMap

        self._heightMap = computeChunkHeightMap(self.materials, self.Blocks)
        return self._heightMap


class LightedChunk(ChunkBase):
    def generateHeightMap(self):
        computeChunkHeightMap(self.materials, self.Blocks, self.HeightMap)

    def chunkChanged(self, calcLighting=True):
        """ You are required to call this function after you are done modifying
        the chunk. Pass False for calcLighting if you know your changes will
        not change any lights."""

        self.dirty = True
        self.needsLighting = calcLighting or self.needsLighting
        self.generateHeightMap()
        if calcLighting:
            self.genFastLights()

    def genFastLights(self):
        self.SkyLight[:] = 0
        if self.world.dimNo in (-1, 1):
            return  # no light in nether or the end

        blocks = self.Blocks
        la = self.world.materials.lightAbsorption
        skylight = self.SkyLight
        heightmap = self.HeightMap

        for x, z in itertools.product(xrange(16), xrange(16)):

            skylight[x, z, heightmap[z, x]:] = 15
            lv = 15
            for y in reversed(range(heightmap[z, x])):
                lv -= (la[blocks[x, z, y]] or 1)

                if lv <= 0:
                    break
                skylight[x, z, y] = lv

########NEW FILE########
__FILENAME__ = materials
from logging import getLogger
from numpy import zeros, rollaxis, indices
import traceback
from os.path import join
from collections import defaultdict
from pprint import pformat

import os

NOTEX = (0x1F0, 0x1F0)

import yaml

log = getLogger(__name__)


class Block(object):
    """
    Value object representing an (id, data) pair.
    Provides elements of its parent material's block arrays.
    Blocks will have (name, ID, blockData, aka, color, brightness, opacity, blockTextures)
    """

    def __str__(self):
        return "<Block {name} ({id}:{data}) hasVariants:{ha}>".format(
            name=self.name, id=self.ID, data=self.blockData, ha=self.hasVariants)

    def __repr__(self):
        return str(self)

    def __cmp__(self, other):
        if not isinstance(other, Block):
            return -1
        key = lambda a: a and (a.ID, a.blockData)
        return cmp(key(self), key(other))

    hasVariants = False  # True if blockData defines additional blocktypes

    def __init__(self, materials, blockID, blockData=0):
        self.materials = materials
        self.ID = blockID
        self.blockData = blockData

    def __getattr__(self, attr):
        if attr in self.__dict__:
            return self.__dict__[attr]
        if attr == "name":
            r = self.materials.names[self.ID]
        else:
            r = getattr(self.materials, attr)[self.ID]
        if attr in ("name", "aka", "color", "type"):
            r = r[self.blockData]
        return r

id_limit = 4096
class MCMaterials(object):
    defaultColor = (0xc9, 0x77, 0xf0, 0xff)
    defaultBrightness = 0
    defaultOpacity = 15
    defaultTexture = NOTEX
    defaultTex = [t // 16 for t in defaultTexture]

    def __init__(self, defaultName="Unused Block"):
        object.__init__(self)
        self.yamlDatas = []

        self.defaultName = defaultName


        self.blockTextures = zeros((id_limit, 16, 6, 2), dtype='uint16')
        self.blockTextures[:] = self.defaultTexture
        self.names = [[defaultName] * 16 for i in range(id_limit)]
        self.aka = [[""] * 16 for i in range(id_limit)]
            #Sets terrain.png array size
        self.type = [["NORMAL"] * 16] * id_limit
        self.blocksByType = defaultdict(list)
        self.allBlocks = []
        self.blocksByID = {}

        self.lightEmission = zeros(id_limit, dtype='uint8')
        self.lightEmission[:] = self.defaultBrightness
        self.lightAbsorption = zeros(id_limit, dtype='uint8')
        self.lightAbsorption[:] = self.defaultOpacity
        self.flatColors = zeros((id_limit, 16, 4), dtype='uint8')
        self.flatColors[:] = self.defaultColor

        self.idStr = [""] * id_limit

        self.color = self.flatColors
        self.brightness = self.lightEmission
        self.opacity = self.lightAbsorption

        self.Air = self.addBlock(0,
            name="Air",
            texture=(0x80, 0xB0),
            opacity=0,
        )

    def __repr__(self):
        return "<MCMaterials ({0})>".format(self.name)

    @property
    def AllStairs(self):
        return [b for b in self.allBlocks if b.name.endswith("Stairs")]

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __len__(self):
        return len(self.allBlocks)

    def __iter__(self):
        return iter(self.allBlocks)

    def __getitem__(self, key):
        """ Let's be magic. If we get a string, return the first block whose
            name matches exactly. If we get a (id, data) pair or an id, return
            that block. for example:

                level.materials[0]  # returns Air
                level.materials["Air"]  # also returns Air
                level.materials["Powered Rail"]  # returns Powered Rail
                level.materials["Lapis Lazuli Block"]  # in Classic

           """
        if isinstance(key, basestring):
            for b in self.allBlocks:
                if b.name == key:
                    return b
            raise KeyError("No blocks named: " + key)
        if isinstance(key, (tuple, list)):
            id, blockData = key
            return self.blockWithID(id, blockData)
        return self.blockWithID(key)

    def blocksMatching(self, name):
        name = name.lower()
        return [v for v in self.allBlocks if name in v.name.lower() or name in v.aka.lower()]

    def blockWithID(self, id, data=0):
        if (id, data) in self.blocksByID:
            return self.blocksByID[id, data]
        else:
            bl = Block(self, id, blockData=data)
            bl.hasVariants = True
            return bl

    def addYamlBlocksFromFile(self, filename):
        try:
            import pkg_resources

            f = pkg_resources.resource_stream(__name__, filename)
        except (ImportError, IOError), e:
            print "Cannot get resource_stream for ", filename, e
            root = os.environ.get("PYMCLEVEL_YAML_ROOT", "pymclevel")  # fall back to cwd as last resort
            path = join(root, filename)

            log.exception("Failed to read %s using pkg_resources. Trying %s instead." % (filename, path))

            f = file(path)
        try:
            log.info(u"Loading block info from %s", f)
            blockyaml = yaml.load(f)
            self.addYamlBlocks(blockyaml)

        except Exception, e:
            log.error(u"Exception while loading block info from %s: %s", f, e)
            raise

    def addYamlBlocks(self, blockyaml):
        self.yamlDatas.append(blockyaml)
        for block in blockyaml['blocks']:
            try:
                self.addYamlBlock(block)
            except Exception, e:
                log.error(u"Exception while parsing block: %s", e)
                log.error(u"Block definition: \n%s", pformat(block))
                raise

    def addYamlBlock(self, kw):
        blockID = kw['id']

        # xxx unused_yaml_properties variable unused; needed for
        #     documentation purpose of some sort?  -zothar
        #unused_yaml_properties = \
        #['explored',
        # # 'id',
        # # 'idStr',
        # # 'mapcolor',
        # # 'name',
        # # 'tex',
        # ### 'tex_data',
        # # 'tex_direction',
        # ### 'tex_direction_data',
        # 'tex_extra',
        # # 'type'
        # ]

        for val, data in kw.get('data', {0: {}}).items():
            datakw = dict(kw)
            datakw.update(data)
            idStr = datakw.get('idStr', "")
            tex = [t * 16 for t in datakw.get('tex', self.defaultTex)]
            texture = [tex] * 6
            texDirs = {
                "FORWARD": 5,
                "BACKWARD": 4,
                "LEFT": 1,
                "RIGHT": 0,
                "TOP": 2,
                "BOTTOM": 3,
            }
            for dirname, dirtex in datakw.get('tex_direction', {}).items():
                if dirname == "SIDES":
                    for dirname in ("LEFT", "RIGHT"):
                        texture[texDirs[dirname]] = [t * 16 for t in dirtex]
                if dirname in texDirs:
                    texture[texDirs[dirname]] = [t * 16 for t in dirtex]
            datakw['texture'] = texture
            # print datakw
            block = self.addBlock(blockID, val, **datakw)
            block.yaml = datakw
            self.idStr[blockID] = idStr

        tex_direction_data = kw.get('tex_direction_data')
        if tex_direction_data:
            texture = datakw['texture']
            # X+0, X-1, Y+, Y-, Z+b, Z-f
            texDirMap = {
                "NORTH": 0,
                "EAST": 1,
                "SOUTH": 2,
                "WEST": 3,
            }

            def rot90cw():
                rot = (5, 0, 2, 3, 4, 1)
                texture[:] = [texture[r] for r in rot]

            for data, dir in tex_direction_data.items():
                for _i in range(texDirMap.get(dir, 0)):
                    rot90cw()
                self.blockTextures[blockID][data] = texture

    def addBlock(self, blockID, blockData=0, **kw):
        name = kw.pop('name', self.names[blockID][blockData])

        self.lightEmission[blockID] = kw.pop('brightness', self.defaultBrightness)
        self.lightAbsorption[blockID] = kw.pop('opacity', self.defaultOpacity)
        self.aka[blockID][blockData] = kw.pop('aka', "")
        type = kw.pop('type', 'NORMAL')

        color = kw.pop('mapcolor', self.flatColors[blockID, blockData])
        self.flatColors[blockID, (blockData or slice(None))] = (tuple(color) + (255,))[:4]

        texture = kw.pop('texture', None)

        if texture:
            self.blockTextures[blockID, (blockData or slice(None))] = texture

        if blockData is 0:
            self.names[blockID] = [name] * 16
            self.type[blockID] = [type] * 16
        else:
            self.names[blockID][blockData] = name
            self.type[blockID][blockData] = type

        block = Block(self, blockID, blockData)

        self.allBlocks.append(block)
        self.blocksByType[type].append(block)

        if (blockID, 0) in self.blocksByID:
            self.blocksByID[blockID, 0].hasVariants = True
            block.hasVariants = True

        self.blocksByID[blockID, blockData] = block

        return block

alphaMaterials = MCMaterials(defaultName="Future Block!")
alphaMaterials.name = "Alpha"
alphaMaterials.addYamlBlocksFromFile("minecraft.yaml")

# --- Special treatment for some blocks ---

HugeMushroomTypes = {
   "Northwest": 1,
   "North": 2,
   "Northeast": 3,
   "East": 6,
   "Southeast": 9,
   "South": 8,
   "Southwest": 7,
   "West": 4,
   "Stem": 10,
   "Top": 5,
}
from faces import FaceXDecreasing, FaceXIncreasing, FaceYIncreasing, FaceZDecreasing, FaceZIncreasing

Red = (0xD0, 0x70)
Brown = (0xE0, 0x70)
Pore = (0xE0, 0x80)
Stem = (0xD0, 0x80)


def defineShroomFaces(Shroom, id, name):
    for way, data in sorted(HugeMushroomTypes.items(), key=lambda a: a[1]):
        loway = way.lower()
        if way is "Stem":
            tex = [Stem, Stem, Pore, Pore, Stem, Stem]
        elif way is "Pore":
            tex = Pore
        else:
            tex = [Pore] * 6
            tex[FaceYIncreasing] = Shroom
            if "north" in loway:
                tex[FaceZDecreasing] = Shroom
            if "south" in loway:
                tex[FaceZIncreasing] = Shroom
            if "west" in loway:
                tex[FaceXDecreasing] = Shroom
            if "east" in loway:
                tex[FaceXIncreasing] = Shroom

        alphaMaterials.addBlock(id, blockData=data,
            name="Huge " + name + " Mushroom (" + way + ")",
            texture=tex,
            )

defineShroomFaces(Brown, 99, "Brown")
defineShroomFaces(Red, 100, "Red")

classicMaterials = MCMaterials(defaultName="Not present in Classic")
classicMaterials.name = "Classic"
classicMaterials.addYamlBlocksFromFile("classic.yaml")

indevMaterials = MCMaterials(defaultName="Not present in Indev")
indevMaterials.name = "Indev"
indevMaterials.addYamlBlocksFromFile("indev.yaml")

pocketMaterials = MCMaterials()
pocketMaterials.name = "Pocket"
pocketMaterials.addYamlBlocksFromFile("pocket.yaml")

# --- Static block defs ---

alphaMaterials.Stone = alphaMaterials[1, 0]
alphaMaterials.Grass = alphaMaterials[2, 0]
alphaMaterials.Dirt = alphaMaterials[3, 0]
alphaMaterials.Cobblestone = alphaMaterials[4, 0]
alphaMaterials.WoodPlanks = alphaMaterials[5, 0]
alphaMaterials.Sapling = alphaMaterials[6, 0]
alphaMaterials.SpruceSapling = alphaMaterials[6, 1]
alphaMaterials.BirchSapling = alphaMaterials[6, 2]
alphaMaterials.Bedrock = alphaMaterials[7, 0]
alphaMaterials.WaterActive = alphaMaterials[8, 0]
alphaMaterials.Water = alphaMaterials[9, 0]
alphaMaterials.LavaActive = alphaMaterials[10, 0]
alphaMaterials.Lava = alphaMaterials[11, 0]
alphaMaterials.Sand = alphaMaterials[12, 0]
alphaMaterials.Gravel = alphaMaterials[13, 0]
alphaMaterials.GoldOre = alphaMaterials[14, 0]
alphaMaterials.IronOre = alphaMaterials[15, 0]
alphaMaterials.CoalOre = alphaMaterials[16, 0]
alphaMaterials.Wood = alphaMaterials[17, 0]
alphaMaterials.Ironwood = alphaMaterials[17, 1]
alphaMaterials.BirchWood = alphaMaterials[17, 2]
alphaMaterials.Leaves = alphaMaterials[18, 0]
alphaMaterials.PineLeaves = alphaMaterials[18, 1]
alphaMaterials.BirchLeaves = alphaMaterials[18, 2]
alphaMaterials.JungleLeaves = alphaMaterials[18, 3]
alphaMaterials.LeavesPermanent = alphaMaterials[18, 4]
alphaMaterials.PineLeavesPermanent = alphaMaterials[18, 5]
alphaMaterials.BirchLeavesPermanent = alphaMaterials[18, 6]
alphaMaterials.JungleLeavesPermanent = alphaMaterials[18, 7]
alphaMaterials.LeavesDecaying = alphaMaterials[18, 8]
alphaMaterials.PineLeavesDecaying = alphaMaterials[18, 9]
alphaMaterials.BirchLeavesDecaying = alphaMaterials[18, 10]
alphaMaterials.JungleLeavesDecaying = alphaMaterials[18, 11]
alphaMaterials.Sponge = alphaMaterials[19, 0]
alphaMaterials.Glass = alphaMaterials[20, 0]

alphaMaterials.LapisLazuliOre = alphaMaterials[21, 0]
alphaMaterials.LapisLazuliBlock = alphaMaterials[22, 0]
alphaMaterials.Dispenser = alphaMaterials[23, 0]
alphaMaterials.Sandstone = alphaMaterials[24, 0]
alphaMaterials.NoteBlock = alphaMaterials[25, 0]
alphaMaterials.Bed = alphaMaterials[26, 0]
alphaMaterials.PoweredRail = alphaMaterials[27, 0]
alphaMaterials.DetectorRail = alphaMaterials[28, 0]
alphaMaterials.StickyPiston = alphaMaterials[29, 0]
alphaMaterials.Web = alphaMaterials[30, 0]
alphaMaterials.UnusedShrub = alphaMaterials[31, 0]
alphaMaterials.TallGrass = alphaMaterials[31, 1]
alphaMaterials.Shrub = alphaMaterials[31, 2]
alphaMaterials.DesertShrub2 = alphaMaterials[32, 0]
alphaMaterials.Piston = alphaMaterials[33, 0]
alphaMaterials.PistonHead = alphaMaterials[34, 0]
alphaMaterials.WhiteWool = alphaMaterials[35, 0]
alphaMaterials.OrangeWool = alphaMaterials[35, 1]
alphaMaterials.MagentaWool = alphaMaterials[35, 2]
alphaMaterials.LightBlueWool = alphaMaterials[35, 3]
alphaMaterials.YellowWool = alphaMaterials[35, 4]
alphaMaterials.LightGreenWool = alphaMaterials[35, 5]
alphaMaterials.PinkWool = alphaMaterials[35, 6]
alphaMaterials.GrayWool = alphaMaterials[35, 7]
alphaMaterials.LightGrayWool = alphaMaterials[35, 8]
alphaMaterials.CyanWool = alphaMaterials[35, 9]
alphaMaterials.PurpleWool = alphaMaterials[35, 10]
alphaMaterials.BlueWool = alphaMaterials[35, 11]
alphaMaterials.BrownWool = alphaMaterials[35, 12]
alphaMaterials.DarkGreenWool = alphaMaterials[35, 13]
alphaMaterials.RedWool = alphaMaterials[35, 14]
alphaMaterials.BlackWool = alphaMaterials[35, 15]
alphaMaterials.Block36 = alphaMaterials[36, 0]
alphaMaterials.Flower = alphaMaterials[37, 0]
alphaMaterials.Rose = alphaMaterials[38, 0]
alphaMaterials.BrownMushroom = alphaMaterials[39, 0]
alphaMaterials.RedMushroom = alphaMaterials[40, 0]
alphaMaterials.BlockofGold = alphaMaterials[41, 0]
alphaMaterials.BlockofIron = alphaMaterials[42, 0]
alphaMaterials.DoubleStoneSlab = alphaMaterials[43, 0]
alphaMaterials.DoubleSandstoneSlab = alphaMaterials[43, 1]
alphaMaterials.DoubleWoodenSlab = alphaMaterials[43, 2]
alphaMaterials.DoubleCobblestoneSlab = alphaMaterials[43, 3]
alphaMaterials.DoubleBrickSlab = alphaMaterials[43, 4]
alphaMaterials.DoubleStoneBrickSlab = alphaMaterials[43, 5]
alphaMaterials.StoneSlab = alphaMaterials[44, 0]
alphaMaterials.SandstoneSlab = alphaMaterials[44, 1]
alphaMaterials.WoodenSlab = alphaMaterials[44, 2]
alphaMaterials.CobblestoneSlab = alphaMaterials[44, 3]
alphaMaterials.BrickSlab = alphaMaterials[44, 4]
alphaMaterials.StoneBrickSlab = alphaMaterials[44, 5]
alphaMaterials.Brick = alphaMaterials[45, 0]
alphaMaterials.TNT = alphaMaterials[46, 0]
alphaMaterials.Bookshelf = alphaMaterials[47, 0]
alphaMaterials.MossStone = alphaMaterials[48, 0]
alphaMaterials.Obsidian = alphaMaterials[49, 0]

alphaMaterials.Torch = alphaMaterials[50, 0]
alphaMaterials.Fire = alphaMaterials[51, 0]
alphaMaterials.MonsterSpawner = alphaMaterials[52, 0]
alphaMaterials.WoodenStairs = alphaMaterials[53, 0]
alphaMaterials.Chest = alphaMaterials[54, 0]
alphaMaterials.RedstoneWire = alphaMaterials[55, 0]
alphaMaterials.DiamondOre = alphaMaterials[56, 0]
alphaMaterials.BlockofDiamond = alphaMaterials[57, 0]
alphaMaterials.CraftingTable = alphaMaterials[58, 0]
alphaMaterials.Crops = alphaMaterials[59, 0]
alphaMaterials.Farmland = alphaMaterials[60, 0]
alphaMaterials.Furnace = alphaMaterials[61, 0]
alphaMaterials.LitFurnace = alphaMaterials[62, 0]
alphaMaterials.Sign = alphaMaterials[63, 0]
alphaMaterials.WoodenDoor = alphaMaterials[64, 0]
alphaMaterials.Ladder = alphaMaterials[65, 0]
alphaMaterials.Rail = alphaMaterials[66, 0]
alphaMaterials.StoneStairs = alphaMaterials[67, 0]
alphaMaterials.WallSign = alphaMaterials[68, 0]
alphaMaterials.Lever = alphaMaterials[69, 0]
alphaMaterials.StoneFloorPlate = alphaMaterials[70, 0]
alphaMaterials.IronDoor = alphaMaterials[71, 0]
alphaMaterials.WoodFloorPlate = alphaMaterials[72, 0]
alphaMaterials.RedstoneOre = alphaMaterials[73, 0]
alphaMaterials.RedstoneOreGlowing = alphaMaterials[74, 0]
alphaMaterials.RedstoneTorchOff = alphaMaterials[75, 0]
alphaMaterials.RedstoneTorchOn = alphaMaterials[76, 0]
alphaMaterials.Button = alphaMaterials[77, 0]
alphaMaterials.SnowLayer = alphaMaterials[78, 0]
alphaMaterials.Ice = alphaMaterials[79, 0]
alphaMaterials.Snow = alphaMaterials[80, 0]

alphaMaterials.Cactus = alphaMaterials[81, 0]
alphaMaterials.Clay = alphaMaterials[82, 0]
alphaMaterials.SugarCane = alphaMaterials[83, 0]
alphaMaterials.Jukebox = alphaMaterials[84, 0]
alphaMaterials.Fence = alphaMaterials[85, 0]
alphaMaterials.Pumpkin = alphaMaterials[86, 0]
alphaMaterials.Netherrack = alphaMaterials[87, 0]
alphaMaterials.SoulSand = alphaMaterials[88, 0]
alphaMaterials.Glowstone = alphaMaterials[89, 0]
alphaMaterials.NetherPortal = alphaMaterials[90, 0]
alphaMaterials.JackOLantern = alphaMaterials[91, 0]
alphaMaterials.Cake = alphaMaterials[92, 0]
alphaMaterials.RedstoneRepeaterOff = alphaMaterials[93, 0]
alphaMaterials.RedstoneRepeaterOn = alphaMaterials[94, 0]
alphaMaterials.AprilFoolsChest = alphaMaterials[95, 0]
alphaMaterials.Trapdoor = alphaMaterials[96, 0]

alphaMaterials.HiddenSilverfishStone = alphaMaterials[97, 0]
alphaMaterials.HiddenSilverfishCobblestone = alphaMaterials[97, 1]
alphaMaterials.HiddenSilverfishStoneBrick = alphaMaterials[97, 2]
alphaMaterials.StoneBricks = alphaMaterials[98, 0]
alphaMaterials.MossyStoneBricks = alphaMaterials[98, 1]
alphaMaterials.CrackedStoneBricks = alphaMaterials[98, 2]
alphaMaterials.HugeBrownMushroom = alphaMaterials[99, 0]
alphaMaterials.HugeRedMushroom = alphaMaterials[100, 0]
alphaMaterials.IronBars = alphaMaterials[101, 0]
alphaMaterials.GlassPane = alphaMaterials[102, 0]
alphaMaterials.Watermelon = alphaMaterials[103, 0]
alphaMaterials.PumpkinStem = alphaMaterials[104, 0]
alphaMaterials.MelonStem = alphaMaterials[105, 0]
alphaMaterials.Vines = alphaMaterials[106, 0]
alphaMaterials.FenceGate = alphaMaterials[107, 0]
alphaMaterials.BrickStairs = alphaMaterials[108, 0]
alphaMaterials.StoneBrickStairs = alphaMaterials[109, 0]
alphaMaterials.Mycelium = alphaMaterials[110, 0]
alphaMaterials.Lilypad = alphaMaterials[111, 0]
alphaMaterials.NetherBrick = alphaMaterials[112, 0]
alphaMaterials.NetherBrickFence = alphaMaterials[113, 0]
alphaMaterials.NetherBrickStairs = alphaMaterials[114, 0]
alphaMaterials.NetherWart = alphaMaterials[115, 0]

alphaMaterials.EnchantmentTable = alphaMaterials[116,0]
alphaMaterials.BrewingStand = alphaMaterials[117,0]
alphaMaterials.Cauldron = alphaMaterials[118,0]
alphaMaterials.EnderPortal = alphaMaterials[119,0]
alphaMaterials.PortalFrame = alphaMaterials[120,0]
alphaMaterials.EndStone = alphaMaterials[121,0]
alphaMaterials.DragonEgg = alphaMaterials[122,0]
alphaMaterials.RedstoneLampoff = alphaMaterials[123,0]
alphaMaterials.RedstoneLampon = alphaMaterials[124,0]
alphaMaterials.OakWoodDoubleSlab = alphaMaterials[125,0]
alphaMaterials.SpruceWoodDoubleSlab = alphaMaterials[125,1]
alphaMaterials.BirchWoodDoubleSlab = alphaMaterials[125,2]
alphaMaterials.JungleWoodDoubleSlab = alphaMaterials[125,3]
alphaMaterials.OakWoodSlab = alphaMaterials[126,0]
alphaMaterials.SpruceWoodSlab = alphaMaterials[126,1]
alphaMaterials.BirchWoodSlab = alphaMaterials[126,2]
alphaMaterials.JungleWoodSlab = alphaMaterials[126,3]
alphaMaterials.CocoaPlant = alphaMaterials[127,0]
alphaMaterials.SandstoneStairs = alphaMaterials[128,0]
alphaMaterials.EmeraldOre = alphaMaterials[129,0]
alphaMaterials.EnderChest = alphaMaterials[130,0]
alphaMaterials.TripwireHook = alphaMaterials[131,0]
alphaMaterials.Tripwire = alphaMaterials[132,0]
alphaMaterials.BlockofEmerald = alphaMaterials[133,0]
alphaMaterials.SpruceWoodStairs = alphaMaterials[134,0]
alphaMaterials.BirchWoodStairs = alphaMaterials[135,0]
alphaMaterials.JungleWoodStairs = alphaMaterials[136,0]
alphaMaterials.CommandBlock = alphaMaterials[137,0]
alphaMaterials.BeaconBlock = alphaMaterials[138,0]
alphaMaterials.CobblestoneWall = alphaMaterials[139,0]
alphaMaterials.MossyCobblestoneWall = alphaMaterials[139,1]
alphaMaterials.FlowerPot = alphaMaterials[140,0]
alphaMaterials.Carrots = alphaMaterials[141,0]
alphaMaterials.Potatoes = alphaMaterials[142,0]
alphaMaterials.WoodenButton = alphaMaterials[143,0]
alphaMaterials.MobHead = alphaMaterials[144,0]
alphaMaterials.Anvil = alphaMaterials[145,0]
alphaMaterials.TrappedChest = alphaMaterials[146,0]
alphaMaterials.WeightedPressurePlateLight = alphaMaterials[147,0]
alphaMaterials.WeightedPressurePlateHeavy = alphaMaterials[148,0]
alphaMaterials.RedstoneComparatorInactive = alphaMaterials[149,0]
alphaMaterials.RedstoneComparatorActive = alphaMaterials[150,0]
alphaMaterials.DaylightSensor = alphaMaterials[151,0]
alphaMaterials.BlockofRedstone = alphaMaterials[152,0]
alphaMaterials.NetherQuartzOre = alphaMaterials[153,0]
alphaMaterials.Hopper = alphaMaterials[154,0]
alphaMaterials.BlockofQuartz = alphaMaterials[155,0]
alphaMaterials.QuartzStairs = alphaMaterials[156,0]
alphaMaterials.ActivatorRail = alphaMaterials[157,0]
alphaMaterials.Dropper = alphaMaterials[158,0]


# --- Classic static block defs ---
classicMaterials.Stone = classicMaterials[1]
classicMaterials.Grass = classicMaterials[2]
classicMaterials.Dirt = classicMaterials[3]
classicMaterials.Cobblestone = classicMaterials[4]
classicMaterials.WoodPlanks = classicMaterials[5]
classicMaterials.Sapling = classicMaterials[6]
classicMaterials.Bedrock = classicMaterials[7]
classicMaterials.WaterActive = classicMaterials[8]
classicMaterials.Water = classicMaterials[9]
classicMaterials.LavaActive = classicMaterials[10]
classicMaterials.Lava = classicMaterials[11]
classicMaterials.Sand = classicMaterials[12]
classicMaterials.Gravel = classicMaterials[13]
classicMaterials.GoldOre = classicMaterials[14]
classicMaterials.IronOre = classicMaterials[15]
classicMaterials.CoalOre = classicMaterials[16]
classicMaterials.Wood = classicMaterials[17]
classicMaterials.Leaves = classicMaterials[18]
classicMaterials.Sponge = classicMaterials[19]
classicMaterials.Glass = classicMaterials[20]

classicMaterials.RedWool = classicMaterials[21]
classicMaterials.OrangeWool = classicMaterials[22]
classicMaterials.YellowWool = classicMaterials[23]
classicMaterials.LimeWool = classicMaterials[24]
classicMaterials.GreenWool = classicMaterials[25]
classicMaterials.AquaWool = classicMaterials[26]
classicMaterials.CyanWool = classicMaterials[27]
classicMaterials.BlueWool = classicMaterials[28]
classicMaterials.PurpleWool = classicMaterials[29]
classicMaterials.IndigoWool = classicMaterials[30]
classicMaterials.VioletWool = classicMaterials[31]
classicMaterials.MagentaWool = classicMaterials[32]
classicMaterials.PinkWool = classicMaterials[33]
classicMaterials.BlackWool = classicMaterials[34]
classicMaterials.GrayWool = classicMaterials[35]
classicMaterials.WhiteWool = classicMaterials[36]

classicMaterials.Flower = classicMaterials[37]
classicMaterials.Rose = classicMaterials[38]
classicMaterials.BrownMushroom = classicMaterials[39]
classicMaterials.RedMushroom = classicMaterials[40]
classicMaterials.BlockofGold = classicMaterials[41]
classicMaterials.BlockofIron = classicMaterials[42]
classicMaterials.DoubleStoneSlab = classicMaterials[43]
classicMaterials.StoneSlab = classicMaterials[44]
classicMaterials.Brick = classicMaterials[45]
classicMaterials.TNT = classicMaterials[46]
classicMaterials.Bookshelf = classicMaterials[47]
classicMaterials.MossStone = classicMaterials[48]
classicMaterials.Obsidian = classicMaterials[49]

# --- Indev static block defs ---
indevMaterials.Stone = indevMaterials[1]
indevMaterials.Grass = indevMaterials[2]
indevMaterials.Dirt = indevMaterials[3]
indevMaterials.Cobblestone = indevMaterials[4]
indevMaterials.WoodPlanks = indevMaterials[5]
indevMaterials.Sapling = indevMaterials[6]
indevMaterials.Bedrock = indevMaterials[7]
indevMaterials.WaterActive = indevMaterials[8]
indevMaterials.Water = indevMaterials[9]
indevMaterials.LavaActive = indevMaterials[10]
indevMaterials.Lava = indevMaterials[11]
indevMaterials.Sand = indevMaterials[12]
indevMaterials.Gravel = indevMaterials[13]
indevMaterials.GoldOre = indevMaterials[14]
indevMaterials.IronOre = indevMaterials[15]
indevMaterials.CoalOre = indevMaterials[16]
indevMaterials.Wood = indevMaterials[17]
indevMaterials.Leaves = indevMaterials[18]
indevMaterials.Sponge = indevMaterials[19]
indevMaterials.Glass = indevMaterials[20]

indevMaterials.RedWool = indevMaterials[21]
indevMaterials.OrangeWool = indevMaterials[22]
indevMaterials.YellowWool = indevMaterials[23]
indevMaterials.LimeWool = indevMaterials[24]
indevMaterials.GreenWool = indevMaterials[25]
indevMaterials.AquaWool = indevMaterials[26]
indevMaterials.CyanWool = indevMaterials[27]
indevMaterials.BlueWool = indevMaterials[28]
indevMaterials.PurpleWool = indevMaterials[29]
indevMaterials.IndigoWool = indevMaterials[30]
indevMaterials.VioletWool = indevMaterials[31]
indevMaterials.MagentaWool = indevMaterials[32]
indevMaterials.PinkWool = indevMaterials[33]
indevMaterials.BlackWool = indevMaterials[34]
indevMaterials.GrayWool = indevMaterials[35]
indevMaterials.WhiteWool = indevMaterials[36]

indevMaterials.Flower = indevMaterials[37]
indevMaterials.Rose = indevMaterials[38]
indevMaterials.BrownMushroom = indevMaterials[39]
indevMaterials.RedMushroom = indevMaterials[40]
indevMaterials.BlockofGold = indevMaterials[41]
indevMaterials.BlockofIron = indevMaterials[42]
indevMaterials.DoubleStoneSlab = indevMaterials[43]
indevMaterials.StoneSlab = indevMaterials[44]
indevMaterials.Brick = indevMaterials[45]
indevMaterials.TNT = indevMaterials[46]
indevMaterials.Bookshelf = indevMaterials[47]
indevMaterials.MossStone = indevMaterials[48]
indevMaterials.Obsidian = indevMaterials[49]

indevMaterials.Torch = indevMaterials[50, 0]
indevMaterials.Fire = indevMaterials[51, 0]
indevMaterials.InfiniteWater = indevMaterials[52, 0]
indevMaterials.InfiniteLava = indevMaterials[53, 0]
indevMaterials.Chest = indevMaterials[54, 0]
indevMaterials.Cog = indevMaterials[55, 0]
indevMaterials.DiamondOre = indevMaterials[56, 0]
indevMaterials.BlockofDiamond = indevMaterials[57, 0]
indevMaterials.CraftingTable = indevMaterials[58, 0]
indevMaterials.Crops = indevMaterials[59, 0]
indevMaterials.Farmland = indevMaterials[60, 0]
indevMaterials.Furnace = indevMaterials[61, 0]
indevMaterials.LitFurnace = indevMaterials[62, 0]

# --- Pocket static block defs ---

pocketMaterials.Air = pocketMaterials[0, 0]
pocketMaterials.Stone = pocketMaterials[1, 0]
pocketMaterials.Grass = pocketMaterials[2, 0]
pocketMaterials.Dirt = pocketMaterials[3, 0]
pocketMaterials.Cobblestone = pocketMaterials[4, 0]
pocketMaterials.WoodPlanks = pocketMaterials[5, 0]
pocketMaterials.Sapling = pocketMaterials[6, 0]
pocketMaterials.SpruceSapling = pocketMaterials[6, 1]
pocketMaterials.BirchSapling = pocketMaterials[6, 2]
pocketMaterials.Bedrock = pocketMaterials[7, 0]
pocketMaterials.Wateractive = pocketMaterials[8, 0]
pocketMaterials.Water = pocketMaterials[9, 0]
pocketMaterials.Lavaactive = pocketMaterials[10, 0]
pocketMaterials.Lava = pocketMaterials[11, 0]
pocketMaterials.Sand = pocketMaterials[12, 0]
pocketMaterials.Gravel = pocketMaterials[13, 0]
pocketMaterials.GoldOre = pocketMaterials[14, 0]
pocketMaterials.IronOre = pocketMaterials[15, 0]
pocketMaterials.CoalOre = pocketMaterials[16, 0]
pocketMaterials.Wood = pocketMaterials[17, 0]
pocketMaterials.PineWood = pocketMaterials[17, 1]
pocketMaterials.BirchWood = pocketMaterials[17, 2]
pocketMaterials.Leaves = pocketMaterials[18, 0]
pocketMaterials.Glass = pocketMaterials[20, 0]

pocketMaterials.LapisLazuliOre = pocketMaterials[21, 0]
pocketMaterials.LapisLazuliBlock = pocketMaterials[22, 0]
pocketMaterials.Sandstone = pocketMaterials[24, 0]
pocketMaterials.Bed = pocketMaterials[26, 0]
pocketMaterials.Web = pocketMaterials[30, 0]
pocketMaterials.UnusedShrub = pocketMaterials[31, 0]
pocketMaterials.TallGrass = pocketMaterials[31, 1]
pocketMaterials.Shrub = pocketMaterials[31, 2]
pocketMaterials.WhiteWool = pocketMaterials[35, 0]
pocketMaterials.OrangeWool = pocketMaterials[35, 1]
pocketMaterials.MagentaWool = pocketMaterials[35, 2]
pocketMaterials.LightBlueWool = pocketMaterials[35, 3]
pocketMaterials.YellowWool = pocketMaterials[35, 4]
pocketMaterials.LightGreenWool = pocketMaterials[35, 5]
pocketMaterials.PinkWool = pocketMaterials[35, 6]
pocketMaterials.GrayWool = pocketMaterials[35, 7]
pocketMaterials.LightGrayWool = pocketMaterials[35, 8]
pocketMaterials.CyanWool = pocketMaterials[35, 9]
pocketMaterials.PurpleWool = pocketMaterials[35, 10]
pocketMaterials.BlueWool = pocketMaterials[35, 11]
pocketMaterials.BrownWool = pocketMaterials[35, 12]
pocketMaterials.DarkGreenWool = pocketMaterials[35, 13]
pocketMaterials.RedWool = pocketMaterials[35, 14]
pocketMaterials.BlackWool = pocketMaterials[35, 15]
pocketMaterials.Flower = pocketMaterials[37, 0]
pocketMaterials.Rose = pocketMaterials[38, 0]
pocketMaterials.BrownMushroom = pocketMaterials[39, 0]
pocketMaterials.RedMushroom = pocketMaterials[40, 0]
pocketMaterials.BlockofGold = pocketMaterials[41, 0]
pocketMaterials.BlockofIron = pocketMaterials[42, 0]
pocketMaterials.DoubleStoneSlab = pocketMaterials[43, 0]
pocketMaterials.DoubleSandstoneSlab = pocketMaterials[43, 1]
pocketMaterials.DoubleWoodenSlab = pocketMaterials[43, 2]
pocketMaterials.DoubleCobblestoneSlab = pocketMaterials[43, 3]
pocketMaterials.DoubleBrickSlab = pocketMaterials[43, 4]
pocketMaterials.StoneSlab = pocketMaterials[44, 0]
pocketMaterials.SandstoneSlab = pocketMaterials[44, 1]
pocketMaterials.WoodenSlab = pocketMaterials[44, 2]
pocketMaterials.CobblestoneSlab = pocketMaterials[44, 3]
pocketMaterials.BrickSlab = pocketMaterials[44, 4]
pocketMaterials.Brick = pocketMaterials[45, 0]
pocketMaterials.TNT = pocketMaterials[46, 0]
pocketMaterials.Bookshelf = pocketMaterials[47, 0]
pocketMaterials.MossStone = pocketMaterials[48, 0]
pocketMaterials.Obsidian = pocketMaterials[49, 0]

pocketMaterials.Torch = pocketMaterials[50, 0]
pocketMaterials.Fire = pocketMaterials[51, 0]
pocketMaterials.WoodenStairs = pocketMaterials[53, 0]
pocketMaterials.Chest = pocketMaterials[54, 0]
pocketMaterials.DiamondOre = pocketMaterials[56, 0]
pocketMaterials.BlockofDiamond = pocketMaterials[57, 0]
pocketMaterials.CraftingTable = pocketMaterials[58, 0]
pocketMaterials.Crops = pocketMaterials[59, 0]
pocketMaterials.Farmland = pocketMaterials[60, 0]
pocketMaterials.Furnace = pocketMaterials[61, 0]
pocketMaterials.LitFurnace = pocketMaterials[62, 0]
pocketMaterials.WoodenDoor = pocketMaterials[64, 0]
pocketMaterials.Ladder = pocketMaterials[65, 0]
pocketMaterials.StoneStairs = pocketMaterials[67, 0]
pocketMaterials.IronDoor = pocketMaterials[71, 0]
pocketMaterials.RedstoneOre = pocketMaterials[73, 0]
pocketMaterials.RedstoneOreGlowing = pocketMaterials[74, 0]
pocketMaterials.SnowLayer = pocketMaterials[78, 0]
pocketMaterials.Ice = pocketMaterials[79, 0]

pocketMaterials.Snow = pocketMaterials[80, 0]
pocketMaterials.Cactus = pocketMaterials[81, 0]
pocketMaterials.Clay = pocketMaterials[82, 0]
pocketMaterials.SugarCane = pocketMaterials[83, 0]
pocketMaterials.Fence = pocketMaterials[85, 0]
pocketMaterials.Glowstone = pocketMaterials[89, 0]
pocketMaterials.InvisibleBedrock = pocketMaterials[95, 0]
pocketMaterials.Trapdoor = pocketMaterials[96, 0]

pocketMaterials.StoneBricks = pocketMaterials[98, 0]
pocketMaterials.GlassPane = pocketMaterials[102, 0]
pocketMaterials.Watermelon = pocketMaterials[103, 0]
pocketMaterials.MelonStem = pocketMaterials[105, 0]
pocketMaterials.FenceGate = pocketMaterials[107, 0]
pocketMaterials.BrickStairs = pocketMaterials[108, 0]

pocketMaterials.GlowingObsidian = pocketMaterials[246, 0]
pocketMaterials.NetherReactor = pocketMaterials[247, 0]
pocketMaterials.NetherReactorUsed = pocketMaterials[247, 1]

def printStaticDefs(name):
    # printStaticDefs('alphaMaterials')
    mats = eval(name)
    for b in sorted(mats.allBlocks):
        print "{name}.{0} = {name}[{1},{2}]".format(
            b.name.replace(" ", "").replace("(","").replace(")",""),
            b.ID, b.blockData,
            name=name,
        )

_indices = rollaxis(indices((id_limit, 16)), 0, 3)


def _filterTable(filters, unavailable, default=(0, 0)):
    # a filter table is a id_limit table of (ID, data) pairs.
    table = zeros((id_limit, 16, 2), dtype='uint8')
    table[:] = _indices
    for u in unavailable:
        try:
            if u[1] == 0:
                u = u[0]
        except TypeError:
            pass
        table[u] = default
    for f, t in filters:
        try:
            if f[1] == 0:
                f = f[0]
        except TypeError:
            pass
        table[f] = t
    return table

nullConversion = lambda b, d: (b, d)


def filterConversion(table):
    def convert(blocks, data):
        if data is None:
            data = 0
        t = table[blocks, data]
        return t[..., 0], t[..., 1]

    return convert


def guessFilterTable(matsFrom, matsTo):
    """ Returns a pair (filters, unavailable)
    filters is a list of (from, to) pairs;  from and to are (ID, data) pairs
    unavailable is a list of (ID, data) pairs in matsFrom not found in matsTo.

    Searches the 'name' and 'aka' fields to find matches.
    """
    filters = []
    unavailable = []
    toByName = dict(((b.name, b) for b in sorted(matsTo.allBlocks, reverse=True)))
    for fromBlock in matsFrom.allBlocks:
        block = toByName.get(fromBlock.name)
        if block is None:
            for b in matsTo.allBlocks:
                if b.name.startswith(fromBlock.name):
                    block = b
                    break
        if block is None:
            for b in matsTo.allBlocks:
                if fromBlock.name in b.name:
                    block = b
                    break
        if block is None:
            for b in matsTo.allBlocks:
                if fromBlock.name in b.aka:
                    block = b
                    break
        if block is None:
            if "Indigo Wool" == fromBlock.name:
                block = toByName.get("Purple Wool")
            elif "Violet Wool" == fromBlock.name:
                block = toByName.get("Purple Wool")

        if block:
            if block != fromBlock:
                filters.append(((fromBlock.ID, fromBlock.blockData), (block.ID, block.blockData)))
        else:
            unavailable.append((fromBlock.ID, fromBlock.blockData))

    return filters, unavailable

allMaterials = (alphaMaterials, classicMaterials, pocketMaterials, indevMaterials)

_conversionFuncs = {}


def conversionFunc(destMats, sourceMats):
    if destMats is sourceMats:
        return nullConversion
    func = _conversionFuncs.get((destMats, sourceMats))
    if func:
        return func

    filters, unavailable = guessFilterTable(sourceMats, destMats)
    log.debug("")
    log.debug("%s %s %s", sourceMats.name, "=>", destMats.name)
    for a, b in [(sourceMats.blockWithID(*a), destMats.blockWithID(*b)) for a, b in filters]:
        log.debug("{0:20}: \"{1}\"".format('"' + a.name + '"', b.name))

    log.debug("")
    log.debug("Missing blocks: %s", [sourceMats.blockWithID(*a).name for a in unavailable])

    table = _filterTable(filters, unavailable, (35, 0))
    func = filterConversion(table)
    _conversionFuncs[(destMats, sourceMats)] = func
    return func


def convertBlocks(destMats, sourceMats, blocks, blockData):
    if sourceMats == destMats:
        return blocks, blockData

    return conversionFunc(destMats, sourceMats)(blocks, blockData)

namedMaterials = dict((i.name, i) for i in allMaterials)

__all__ = "indevMaterials, pocketMaterials, alphaMaterials, classicMaterials, namedMaterials, MCMaterials".split(", ")

########NEW FILE########
__FILENAME__ = mce
#!/usr/bin/env python
import mclevelbase
import mclevel
import materials
import infiniteworld
import sys
import os
from box import BoundingBox, Vector
import numpy
from numpy import zeros, bincount
import logging
import itertools
import traceback
import shlex
import operator
import codecs

from math import floor
try:
    import readline  # if available, used by raw_input()
except:
    pass


class UsageError(RuntimeError):
    pass


class BlockMatchError(RuntimeError):
    pass


class PlayerNotFound(RuntimeError):
    pass


class mce(object):
    """
    Block commands:
       {commandPrefix}clone <sourceBox> <destPoint> [noair] [nowater]
       {commandPrefix}fill <blockType> [ <box> ]
       {commandPrefix}replace <blockType> [with] <newBlockType> [ <box> ]

       {commandPrefix}export <filename> <sourceBox>
       {commandPrefix}import <filename> <destPoint> [noair] [nowater]

       {commandPrefix}createChest <point> <item> [ <count> ]
       {commandPrefix}analyze

    Player commands:
       {commandPrefix}player [ <player> [ <point> ] ]
       {commandPrefix}spawn [ <point> ]

    Entity commands:
       {commandPrefix}removeEntities [ <EntityID> ]
       {commandPrefix}dumpSigns [ <filename> ]
       {commandPrefix}dumpChests [ <filename> ]

    Chunk commands:
       {commandPrefix}createChunks <box>
       {commandPrefix}deleteChunks <box>
       {commandPrefix}prune <box>
       {commandPrefix}relight [ <box> ]

    World commands:
       {commandPrefix}create <filename>
       {commandPrefix}dimension [ <dim> ]
       {commandPrefix}degrief
       {commandPrefix}time [ <time> ]
       {commandPrefix}worldsize
       {commandPrefix}heightmap <filename>
       {commandPrefix}randomseed [ <seed> ]
       {commandPrefix}gametype [ <player> [ <gametype> ] ]

    Editor commands:
       {commandPrefix}save
       {commandPrefix}reload
       {commandPrefix}load <filename> | <world number>
       {commandPrefix}execute <filename>
       {commandPrefix}quit

    Informational:
       {commandPrefix}blocks [ <block name> | <block ID> ]
       {commandPrefix}help [ <command> ]

    **IMPORTANT**
       {commandPrefix}box

       Type 'box' to learn how to specify points and areas.

    """
    random_seed = os.getenv('MCE_RANDOM_SEED', None)
    last_played = os.getenv("MCE_LAST_PLAYED", None)

    def commandUsage(self, command):
        " returns usage info for the named command - just give the docstring for the handler func "
        func = getattr(self, "_" + command)
        return func.__doc__

    commands = [
        "clone",
        "fill",
        "replace",

        "export",
        "execute",
        "import",

        "createchest",

        "player",
        "spawn",

        "removeentities",
        "dumpsigns",
        "dumpchests",

        "createchunks",
        "deletechunks",
        "prune",
        "relight",

        "create",
        "degrief",
        "time",
        "worldsize",
        "heightmap",
        "randomseed",
        "gametype",

        "save",
        "load",
        "reload",
        "dimension",
        "repair",

        "quit",
        "exit",

        "help",
        "blocks",
        "analyze",
        "region",

        "debug",
        "log",
        "box",
    ]
    debug = False
    needsSave = False

    def readInt(self, command):
        try:
            val = int(command.pop(0))
        except ValueError:
            raise UsageError("Cannot understand numeric input")
        return val

    def prettySplit(self, command):
        cmdstring = " ".join(command)

        lex = shlex.shlex(cmdstring)
        lex.whitespace_split = True
        lex.whitespace += "(),"

        command[:] = list(lex)

    def readBox(self, command):
        self.prettySplit(command)

        sourcePoint = self.readIntPoint(command)
        if command[0].lower() == "to":
            command.pop(0)
            sourcePoint2 = self.readIntPoint(command)
            sourceSize = sourcePoint2 - sourcePoint
        else:
            sourceSize = self.readIntPoint(command, isPoint=False)
        if len([p for p in sourceSize if p <= 0]):
            raise UsageError("Box size cannot be zero or negative")
        box = BoundingBox(sourcePoint, sourceSize)
        return box

    def readIntPoint(self, command, isPoint=True):
        point = self.readPoint(command, isPoint)
        point = map(int, map(floor, point))
        return Vector(*point)

    def readPoint(self, command, isPoint=True):
        self.prettySplit(command)
        try:
            word = command.pop(0)
            if isPoint and (word in self.level.players):
                x, y, z = self.level.getPlayerPosition(word)
                if len(command) and command[0].lower() == "delta":
                    command.pop(0)
                    try:
                        x += int(command.pop(0))
                        y += int(command.pop(0))
                        z += int(command.pop(0))

                    except ValueError:
                        raise UsageError("Error decoding point input (expected a number).")
                return x, y, z

        except IndexError:
            raise UsageError("Error decoding point input (expected more values).")

        try:
            try:
                x = float(word)
            except ValueError:
                if isPoint:
                    raise PlayerNotFound(word)
                raise
            y = float(command.pop(0))
            z = float(command.pop(0))
        except ValueError:
            raise UsageError("Error decoding point input (expected a number).")
        except IndexError:
            raise UsageError("Error decoding point input (expected more values).")

        return x, y, z

    def readBlockInfo(self, command):
        keyword = command.pop(0)

        matches = self.level.materials.blocksMatching(keyword)
        blockInfo = None

        if len(matches):
            if len(matches) == 1:
                blockInfo = matches[0]

            # eat up more words that possibly specify a block.  stop eating when 0 matching blocks.
            while len(command):
                newMatches = self.level.materials.blocksMatching(keyword + " " + command[0])

                if len(newMatches) == 1:
                    blockInfo = newMatches[0]
                if len(newMatches) > 0:
                    matches = newMatches
                    keyword = keyword + " " + command.pop(0)
                else:
                    break

        else:
            try:
                data = 0
                if ":" in keyword:
                    blockID, data = map(int, keyword.split(":"))
                else:
                    blockID = int(keyword)
                blockInfo = self.level.materials.blockWithID(blockID, data)

            except ValueError:
                blockInfo = None

        if blockInfo is None:
                print "Ambiguous block specifier: ", keyword
                if len(matches):
                    print "Matches: "
                    for m in matches:
                        if m == self.level.materials.defaultName:
                            continue
                        print "{0:3}:{1:<2} : {2}".format(m.ID, m.blockData, m.name)
                else:
                    print "No blocks matched."
                raise BlockMatchError

        return blockInfo

    def readBlocksToCopy(self, command):
        blocksToCopy = range(materials.id_limit)
        while len(command):
            word = command.pop()
            if word == "noair":
                blocksToCopy.remove(0)
            if word == "nowater":
                blocksToCopy.remove(8)
                blocksToCopy.remove(9)

        return blocksToCopy

    def _box(self, command):
        """
        Boxes:

    Many commands require a <box> as arguments. A box can be specified with
    a point and a size:
        (12, 5, 15), (5, 5, 5)

    or with two points, making sure to put the keyword "to" between them:
        (12, 5, 15) to (17, 10, 20)

    The commas and parentheses are not important.
    You may add them for improved readability.


        Points:

    Points and sizes are triplets of numbers ordered X Y Z.
    X is position north-south, increasing southward.
    Y is position up-down, increasing upward.
    Z is position east-west, increasing westward.


        Players:

    A player's name can be used as a point - it will use the
    position of the player's head. Use the keyword 'delta' after
    the name to specify a point near the player.

    Example:
       codewarrior delta 0 5 0

    This refers to a point 5 blocks above codewarrior's head.

    """
        raise UsageError

    def _debug(self, command):
        self.debug = not self.debug
        print "Debug", ("disabled", "enabled")[self.debug]

    def _log(self, command):
        """
    log [ <number> ]

    Get or set the log threshold. 0 logs everything; 50 only logs major errors.
    """
        if len(command):
            try:
                logging.getLogger().level = int(command[0])
            except ValueError:
                raise UsageError("Cannot understand numeric input.")
        else:
            print "Log level: {0}".format(logging.getLogger().level)

    def _clone(self, command):
        """
    clone <sourceBox> <destPoint> [noair] [nowater]

    Clone blocks in a cuboid starting at sourcePoint and extending for
    sourceSize blocks in each direction. Blocks and entities in the area
    are cloned at destPoint.
    """
        if len(command) == 0:
            self.printUsage("clone")
            return

        box = self.readBox(command)

        destPoint = self.readPoint(command)

        destPoint = map(int, map(floor, destPoint))
        blocksToCopy = self.readBlocksToCopy(command)

        tempSchematic = self.level.extractSchematic(box)
        self.level.copyBlocksFrom(tempSchematic, BoundingBox((0, 0, 0), box.origin), destPoint, blocksToCopy)

        self.needsSave = True
        print "Cloned 0 blocks."

    def _fill(self, command):
        """
    fill <blockType> [ <box> ]

    Fill blocks with blockType in a cuboid starting at point and
    extending for size blocks in each direction. Without a
    destination, fills the whole world. blockType and may be a
    number from 0-255 or a name listed by the 'blocks' command.
    """
        if len(command) == 0:
            self.printUsage("fill")
            return

        blockInfo = self.readBlockInfo(command)

        if len(command):
            box = self.readBox(command)
        else:
            box = None

        print "Filling with {0}".format(blockInfo.name)

        self.level.fillBlocks(box, blockInfo)

        self.needsSave = True
        print "Filled {0} blocks.".format("all" if box is None else box.volume)

    def _replace(self, command):
        """
    replace <blockType> [with] <newBlockType> [ <box> ]

    Replace all blockType blocks with newBlockType in a cuboid
    starting at point and extending for size blocks in
    each direction. Without a destination, replaces blocks over
    the whole world. blockType and newBlockType may be numbers
    from 0-255 or names listed by the 'blocks' command.
    """
        if len(command) == 0:
            self.printUsage("replace")
            return

        blockInfo = self.readBlockInfo(command)

        if command[0].lower() == "with":
            command.pop(0)
        newBlockInfo = self.readBlockInfo(command)

        if len(command):
            box = self.readBox(command)
        else:
            box = None

        print "Replacing {0} with {1}".format(blockInfo.name, newBlockInfo.name)

        self.level.fillBlocks(box, newBlockInfo, blocksToReplace=[blockInfo])

        self.needsSave = True
        print "Done."

    def _createchest(self, command):
        """
    createChest <point> <item> [ <count> ]

    Create a chest filled with the specified item.
    Stacks are 64 if count is not given.
    """
        point = map(lambda x: int(floor(float(x))), self.readPoint(command))
        itemID = self.readInt(command)
        count = 64
        if len(command):
            count = self.readInt(command)

        chest = mclevel.MCSchematic.chestWithItemID(itemID, count)
        self.level.copyBlocksFrom(chest, chest.bounds, point)
        self.needsSave = True

    def _analyze(self, command):
        """
        analyze

        Counts all of the block types in every chunk of the world.
        """
        blockCounts = zeros((65536,), 'uint64')
        sizeOnDisk = 0

        print "Analyzing {0} chunks...".format(self.level.chunkCount)
        # for input to bincount, create an array of uint16s by
        # shifting the data left and adding the blocks

        for i, cPos in enumerate(self.level.allChunks, 1):
            ch = self.level.getChunk(*cPos)
            btypes = numpy.array(ch.Data.ravel(), dtype='uint16')
            btypes <<= 12
            btypes += ch.Blocks.ravel()
            counts = bincount(btypes)

            blockCounts[:counts.shape[0]] += counts
            if i % 100 == 0:
                logging.info("Chunk {0}...".format(i))

        for blockID in range(materials.id_limit):
            block = self.level.materials.blockWithID(blockID, 0)
            if block.hasVariants:
                for data in range(16):
                    i = (data << 12) + blockID
                    if blockCounts[i]:
                        idstring = "({id}:{data})".format(id=blockID, data=data)

                        print "{idstring:9} {name:30}: {count:<10}".format(
                            idstring=idstring, name=self.level.materials.blockWithID(blockID, data).name, count=blockCounts[i])

            else:
                count = int(sum(blockCounts[(d << 12) + blockID] for d in range(16)))
                if count:
                    idstring = "({id})".format(id=blockID)
                    print "{idstring:9} {name:30}: {count:<10}".format(
                          idstring=idstring, name=self.level.materials.blockWithID(blockID, 0).name, count=count)

        self.needsSave = True

    def _export(self, command):
        """
    export <filename> <sourceBox>

    Exports blocks in the specified region to a file in schematic format.
    This file can be imported with mce or MCEdit.
    """
        if len(command) == 0:
            self.printUsage("export")
            return

        filename = command.pop(0)
        box = self.readBox(command)

        tempSchematic = self.level.extractSchematic(box)

        tempSchematic.saveToFile(filename)

        print "Exported {0} blocks.".format(tempSchematic.bounds.volume)

    def _import(self, command):
        """
    import <filename> <destPoint> [noair] [nowater]

    Imports a level or schematic into this world, beginning at destPoint.
    Supported formats include
    - Alpha single or multiplayer world folder containing level.dat,
    - Zipfile containing Alpha world folder,
    - Classic single-player .mine,
    - Classic multiplayer server_level.dat,
    - Indev .mclevel
    - Schematic from RedstoneSim, MCEdit, mce
    - .inv from INVEdit (appears as a chest)
    """
        if len(command) == 0:
            self.printUsage("import")
            return

        filename = command.pop(0)
        destPoint = self.readPoint(command)
        blocksToCopy = self.readBlocksToCopy(command)

        importLevel = mclevel.fromFile(filename)

        self.level.copyBlocksFrom(importLevel, importLevel.bounds, destPoint, blocksToCopy, create=True)

        self.needsSave = True
        print "Imported {0} blocks.".format(importLevel.bounds.volume)

    def _player(self, command):
        """
    player [ <player> [ <point> ] ]

    Move the named player to the specified point.
    Without a point, prints the named player's position.
    Without a player, prints all players and positions.

    In a single-player world, the player is named Player.
    """
        if len(command) == 0:
            print "Players: "
            for player in self.level.players:
                print "    {0}: {1}".format(player, self.level.getPlayerPosition(player))
            return

        player = command.pop(0)
        if len(command) == 0:
            print "Player {0}: {1}".format(player, self.level.getPlayerPosition(player))
            return

        point = self.readPoint(command)
        self.level.setPlayerPosition(point, player)

        self.needsSave = True
        print "Moved player {0} to {1}".format(player, point)

    def _spawn(self, command):
        """
    spawn [ <point> ]

    Move the world's spawn point.
    Without a point, prints the world's spawn point.
    """
        if len(command):
            point = self.readPoint(command)
            point = map(int, map(floor, point))

            self.level.setPlayerSpawnPosition(point)

            self.needsSave = True
            print "Moved spawn point to ", point
        else:
            print "Spawn point: ", self.level.playerSpawnPosition()

    def _dumpsigns(self, command):
        """
    dumpSigns [ <filename> ]

    Saves the text and location of every sign in the world to a text file.
    With no filename, saves signs to <worldname>.signs

    Output is newline-delimited. 5 lines per sign. Coordinates are
    on the first line, followed by four lines of sign text. For example:

        [229, 118, -15]
        "To boldly go
        where no man
        has gone
        before."

    Coordinates are ordered the same as point inputs:
        [North/South, Down/Up, East/West]

    """
        if len(command):
            filename = command[0]
        else:
            filename = self.level.displayName + ".signs"

        # We happen to encode the output file in UTF-8 too, although
        # we could use another UTF encoding.  The '-sig' encoding puts
        # a signature at the start of the output file that tools such
        # as Microsoft Windows Notepad and Emacs understand to mean
        # the file has UTF-8 encoding.
        outFile = codecs.open(filename, "w", encoding='utf-8-sig')

        print "Dumping signs..."
        signCount = 0

        for i, cPos in enumerate(self.level.allChunks):
            try:
                chunk = self.level.getChunk(*cPos)
            except mclevelbase.ChunkMalformed:
                continue

            for tileEntity in chunk.TileEntities:
                if tileEntity["id"].value == "Sign":
                    signCount += 1

                    outFile.write(str(map(lambda x: tileEntity[x].value, "xyz")) + "\n")
                    for i in range(4):
                        signText = tileEntity["Text{0}".format(i + 1)].value
                        outFile.write(signText + u"\n")

            if i % 100 == 0:
                print "Chunk {0}...".format(i)


        print "Dumped {0} signs to {1}".format(signCount, filename)

        outFile.close()

    def _region(self, command):
        """
    region [rx rz]

    List region files in this world.
    """
        level = self.level
        assert(isinstance(level, mclevel.MCInfdevOldLevel))
        assert level.version

        def getFreeSectors(rf):
            runs = []
            start = None
            count = 0
            for i, free in enumerate(rf.freeSectors):
                if free:
                    if start is None:
                        start = i
                        count = 1
                    else:
                        count += 1
                else:
                    if start is None:
                        pass
                    else:
                        runs.append((start, count))
                        start = None
                        count = 0

            return runs

        def printFreeSectors(runs):

            for i, (start, count) in enumerate(runs):
                if i % 4 == 3:
                    print ""
                print "{start:>6}+{count:<4}".format(**locals()),

            print ""

        if len(command):
            if len(command) > 1:
                rx, rz = map(int, command[:2])
                print "Calling allChunks to preload region files: %d chunks" % len(level.allChunks)
                rf = level.regionFiles.get((rx, rz))
                if rf is None:
                    print "Region {rx},{rz} not found.".format(**locals())
                    return

                print "Region {rx:6}, {rz:6}: {used}/{sectors} sectors".format(used=rf.usedSectors, sectors=rf.sectorCount)
                print "Offset Table:"
                for cx in range(32):
                    for cz in range(32):
                        if cz % 4 == 0:
                            print ""
                            print "{0:3}, {1:3}: ".format(cx, cz),
                        off = rf.getOffset(cx, cz)
                        sector, length = off >> 8, off & 0xff
                        print "{sector:>6}+{length:<2} ".format(**locals()),
                    print ""

                runs = getFreeSectors(rf)
                if len(runs):
                    print "Free sectors:",

                    printFreeSectors(runs)

            else:
                if command[0] == "free":
                    print "Calling allChunks to preload region files: %d chunks" % len(level.allChunks)
                    for (rx, rz), rf in level.regionFiles.iteritems():

                        runs = getFreeSectors(rf)
                        if len(runs):
                            print "R {0:3}, {1:3}:".format(rx, rz),
                            printFreeSectors(runs)

        else:
            print "Calling allChunks to preload region files: %d chunks" % len(level.allChunks)
            coords = (r for r in level.regionFiles)
            for i, (rx, rz) in enumerate(coords):
                print "({rx:6}, {rz:6}): {count}, ".format(count=level.regionFiles[rx, rz].chunkCount),
                if i % 5 == 4:
                    print ""

    def _repair(self, command):
        """
    repair

    Attempt to repair inconsistent region files.
    MAKE A BACKUP. WILL DELETE YOUR DATA.

    Scans for and repairs errors in region files:
        Deletes chunks whose sectors overlap with another chunk
        Rearranges chunks that are in the wrong slot in the offset table
        Deletes completely unreadable chunks

    Only usable with region-format saves.
    """
        if self.level.version:
            self.level.preloadRegions()
            for rf in self.level.regionFiles.itervalues():
                rf.repair()

    def _dumpchests(self, command):
        """
    dumpChests [ <filename> ]

    Saves the content and location of every chest in the world to a text file.
    With no filename, saves signs to <worldname>.chests

    Output is delimited by brackets and newlines. A set of coordinates in
    brackets begins a chest, followed by a line for each inventory slot.
    For example:

        [222, 51, 22]
        2 String
        3 String
        3 Iron bar

    Coordinates are ordered the same as point inputs:
        [North/South, Down/Up, East/West]

    """
        from items import items
        if len(command):
            filename = command[0]
        else:
            filename = self.level.displayName + ".chests"

        outFile = file(filename, "w")

        print "Dumping chests..."
        chestCount = 0

        for i, cPos in enumerate(self.level.allChunks):
            try:
                chunk = self.level.getChunk(*cPos)
            except mclevelbase.ChunkMalformed:
                continue

            for tileEntity in chunk.TileEntities:
                if tileEntity["id"].value == "Chest":
                    chestCount += 1

                    outFile.write(str(map(lambda x: tileEntity[x].value, "xyz")) + "\n")
                    itemsTag = tileEntity["Items"]
                    if len(itemsTag):
                        for itemTag in itemsTag:
                            try:
                                id = itemTag["id"].value
                                damage = itemTag["Damage"].value
                                item = items.findItem(id, damage)
                                itemname = item.name
                            except KeyError:
                                itemname = "Unknown Item {0}".format(itemTag)
                            except Exception, e:
                                itemname = repr(e)
                            outFile.write("{0} {1}\n".format(itemTag["Count"].value, itemname))
                    else:
                        outFile.write("Empty Chest\n")

            if i % 100 == 0:
                print "Chunk {0}...".format(i)


        print "Dumped {0} chests to {1}".format(chestCount, filename)

        outFile.close()

    def _removeentities(self, command):
        """
    removeEntities [ [except] [ <EntityID> [ <EntityID> ... ] ] ]

    Remove all entities matching one or more entity IDs.
    With the except keyword, removes all entities not
    matching one or more entity IDs.

    Without any IDs, removes all entities in the world,
    except for Paintings.

    Known Mob Entity IDs:
        Mob Monster Creeper Skeleton Spider Giant
        Zombie Slime Pig Sheep Cow Chicken

    Known Item Entity IDs: Item Arrow Snowball Painting

    Known Vehicle Entity IDs: Minecart Boat

    Known Dynamic Tile Entity IDs: PrimedTnt FallingSand
    """
        ENT_MATCHTYPE_ANY = 0
        ENT_MATCHTYPE_EXCEPT = 1
        ENT_MATCHTYPE_NONPAINTING = 2

        def match(entityID, matchType, matchWords):
            if ENT_MATCHTYPE_ANY == matchType:
                return entityID.lower() in matchWords
            elif ENT_MATCHTYPE_EXCEPT == matchType:
                return not (entityID.lower() in matchWords)
            else:
                # ENT_MATCHTYPE_EXCEPT == matchType
                return entityID != "Painting"

        removedEntities = {}
        match_words = []

        if len(command):
            if command[0].lower() == "except":
                command.pop(0)
                print "Removing all entities except ", command
                match_type = ENT_MATCHTYPE_EXCEPT
            else:
                print "Removing {0}...".format(", ".join(command))
                match_type = ENT_MATCHTYPE_ANY

            match_words = map(lambda x: x.lower(), command)

        else:
            print "Removing all entities except Painting..."
            match_type = ENT_MATCHTYPE_NONPAINTING

        for cx, cz in self.level.allChunks:
            chunk = self.level.getChunk(cx, cz)
            entitiesRemoved = 0

            for entity in list(chunk.Entities):
                entityID = entity["id"].value

                if match(entityID, match_type, match_words):
                    removedEntities[entityID] = removedEntities.get(entityID, 0) + 1

                    chunk.Entities.remove(entity)
                    entitiesRemoved += 1

            if entitiesRemoved:
                chunk.chunkChanged(False)


        if len(removedEntities) == 0:
            print "No entities to remove."
        else:
            print "Removed entities:"
            for entityID in sorted(removedEntities.keys()):
                print "  {0}: {1:6}".format(entityID, removedEntities[entityID])

        self.needsSave = True

    def _createchunks(self, command):
        """
    createChunks <box>

    Creates any chunks not present in the specified region.
    New chunks are filled with only air. New chunks are written
    to disk immediately.
    """
        if len(command) == 0:
            self.printUsage("createchunks")
            return

        box = self.readBox(command)

        chunksCreated = self.level.createChunksInBox(box)

        print "Created {0} chunks." .format(len(chunksCreated))

        self.needsSave = True

    def _deletechunks(self, command):
        """
    deleteChunks <box>

    Removes all chunks contained in the specified region.
    Chunks are deleted from disk immediately.
    """
        if len(command) == 0:
            self.printUsage("deletechunks")
            return

        box = self.readBox(command)

        deletedChunks = self.level.deleteChunksInBox(box)

        print "Deleted {0} chunks." .format(len(deletedChunks))

    def _prune(self, command):
        """
    prune <box>

    Removes all chunks not contained in the specified region. Useful for enforcing a finite map size.
    Chunks are deleted from disk immediately.
    """
        if len(command) == 0:
            self.printUsage("prune")
            return

        box = self.readBox(command)

        i = 0
        for cx, cz in list(self.level.allChunks):
            if cx < box.mincx or cx >= box.maxcx or cz < box.mincz or cz >= box.maxcz:
                self.level.deleteChunk(cx, cz)
                i += 1

        print "Pruned {0} chunks." .format(i)

    def _relight(self, command):
        """
    relight [ <box> ]

    Recalculates lights in the region specified. If omitted,
    recalculates the entire world.
    """
        if len(command):
            box = self.readBox(command)
            chunks = itertools.product(range(box.mincx, box.maxcx), range(box.mincz, box.maxcz))

        else:
            chunks = self.level.allChunks

        self.level.generateLights(chunks)

        print "Relit 0 chunks."
        self.needsSave = True

    def _create(self, command):
        """
    create [ <filename> ]

    Create and load a new Minecraft Alpha world. This world will have no
    chunks and a random terrain seed. If run from the shell, filename is not
    needed because you already specified a filename earlier in the command.
    For example:

        mce.py MyWorld create

    """
        if len(command) < 1:
            raise UsageError("Expected a filename")

        filename = command[0]
        if not os.path.exists(filename):
            os.mkdir(filename)

        if not os.path.isdir(filename):
            raise IOError("{0} already exists".format(filename))

        if mclevel.MCInfdevOldLevel.isLevel(filename):
            raise IOError("{0} is already a Minecraft Alpha world".format(filename))

        level = mclevel.MCInfdevOldLevel(filename, create=True)

        self.level = level

    def _degrief(self, command):
        """
    degrief [ <height> ]

    Reverse a few forms of griefing by removing
    Adminium, Obsidian, Fire, and Lava wherever
    they occur above the specified height.
    Without a height, uses height level 32.

    Removes natural surface lava.

    Also see removeEntities
    """
        box = self.level.bounds
        box = BoundingBox(box.origin + (0, 32, 0), box.size - (0, 32, 0))
        if len(command):
            try:
                box.miny = int(command[0])
            except ValueError:
                pass

        print "Removing grief matter and surface lava above height {0}...".format(box.miny)

        self.level.fillBlocks(box,
                              self.level.materials.Air,
                              blocksToReplace=[self.level.materials.Bedrock,
                                self.level.materials.Obsidian,
                                self.level.materials.Fire,
                                self.level.materials.LavaActive,
                                self.level.materials.Lava,
                                ]
                              )
        self.needsSave = True

    def _time(self, command):
        """
    time [time of day]

    Set or display the time of day. Acceptable values are "morning", "noon",
    "evening", "midnight", or a time of day such as 8:02, 12:30 PM, or 16:45.
    """
        ticks = self.level.Time
        timeOfDay = ticks % 24000
        ageInTicks = ticks - timeOfDay
        if len(command) == 0:

            days = ageInTicks / 24000
            hours = timeOfDay / 1000
            clockHours = (hours + 6) % 24

            ampm = ("AM", "PM")[clockHours > 11]

            minutes = (timeOfDay % 1000) / 60

            print "It is {0}:{1:02} {2} on Day {3}".format(clockHours % 12 or 12, minutes, ampm, days)
        else:
            times = {"morning": 6, "noon": 12, "evening": 18, "midnight": 24}
            word = command[0]
            minutes = 0

            if word in times:
                hours = times[word]
            else:
                try:
                    if ":" in word:
                        h, m = word.split(":")
                        hours = int(h)
                        minutes = int(m)
                    else:
                        hours = int(word)
                except Exception, e:
                    raise UsageError(("Cannot interpret time, ", e))

                if len(command) > 1:
                    if command[1].lower() == "pm":
                        hours += 12

            ticks = ageInTicks + hours * 1000 + minutes * 1000 / 60 - 6000
            if ticks < 0:
                ticks += 18000

            ampm = ("AM", "PM")[hours > 11 and hours < 24]
            print "Changed time to {0}:{1:02} {2}".format(hours % 12 or 12, minutes, ampm)
            self.level.Time = ticks
            self.needsSave = True

    def _randomseed(self, command):
        """
    randomseed [ <seed> ]

    Set or display the world's random seed, a 64-bit integer that uniquely
    defines the world's terrain.
    """
        if len(command):
            try:
                seed = long(command[0])
            except ValueError:
                raise UsageError("Expected a long integer.")

            self.level.RandomSeed = seed
            self.needsSave = True
        else:
            print "Random Seed: ", self.level.RandomSeed

    def _gametype(self, command):
        """
    gametype [ <player> [ <gametype> ] ]

    Set or display the player's game type, an integer that identifies whether
    their game is survival (0) or creative (1).  On single-player worlds, the
    player is just 'Player'.
    """
        if len(command) == 0:
            print "Players: "
            for player in self.level.players:
                print "    {0}: {1}".format(player, self.level.getPlayerGameType(player))
            return

        player = command.pop(0)
        if len(command) == 0:
            print "Player {0}: {1}".format(player, self.level.getPlayerGameType(player))
            return

        try:
            gametype = int(command[0])
        except ValueError:
            raise UsageError("Expected an integer.")

        self.level.setPlayerGameType(gametype, player)
        self.needsSave = True

    def _worldsize(self, command):
        """
    worldsize

    Computes and prints the dimensions of the world.  For infinite worlds,
    also prints the most negative corner.
    """
        bounds = self.level.bounds
        if isinstance(self.level, mclevel.MCInfdevOldLevel):
            print "\nWorld size: \n  {0[0]:7} north to south\n  {0[2]:7} east to west\n".format(bounds.size)
            print "Smallest and largest points: ({0[0]},{0[2]}), ({1[0]},{1[2]})".format(bounds.origin, bounds.maximum)

        else:
            print "\nWorld size: \n  {0[0]:7} wide\n  {0[1]:7} tall\n  {0[2]:7} long\n".format(bounds.size)

    def _heightmap(self, command):
        """
    heightmap <filename>

    Takes a png and imports it as the terrain starting at chunk 0,0.
    Data is internally converted to greyscale and scaled to the maximum height.
    The game will fill the terrain with trees and mineral deposits the next
    time you play the level.

    Please please please try out a small test image before using a big source.
    Using the levels tool to get a good heightmap is an art, not a science.
    A smaller map lets you experiment and get it right before having to blow
    all night generating the really big map.

    Requires the PIL library.
    """
        if len(command) == 0:
            self.printUsage("heightmap")
            return

        if not sys.stdin.isatty() or raw_input(
     "This will destroy a large portion of the map and may take a long time.  Did you really want to do this?"
     ).lower() in ("yes", "y", "1", "true"):

            from PIL import Image
            import datetime

            filename = command.pop(0)

            imgobj = Image.open(filename)

            greyimg = imgobj.convert("L")  # luminance
            del imgobj

            width, height = greyimg.size

            water_level = 64

            xchunks = (height + 15) / 16
            zchunks = (width + 15) / 16

            start = datetime.datetime.now()
            for cx in range(xchunks):
                for cz in range(zchunks):
                    try:
                        self.level.createChunk(cx, cz)
                    except:
                        pass
                    c = self.level.getChunk(cx, cz)

                    imgarray = numpy.asarray(greyimg.crop((cz * 16, cx * 16, cz * 16 + 16, cx * 16 + 16)))
                    imgarray = imgarray / 2  # scale to 0-127

                    for x in range(16):
                        for z in range(16):
                            if z + (cz * 16) < width - 1 and x + (cx * 16) < height - 1:
                                # world dimension X goes north-south
                                # first array axis goes up-down

                                h = imgarray[x, z]

                                c.Blocks[x, z, h + 1:] = 0  # air
                                c.Blocks[x, z, h:h + 1] = 2  # grass
                                c.Blocks[x, z, h - 4:h] = 3  # dirt
                                c.Blocks[x, z, :h - 4] = 1  # rock

                                if h < water_level:
                                    c.Blocks[x, z, h + 1:water_level] = 9  # water
                                if h < water_level + 2:
                                    c.Blocks[x, z, h - 2:h + 1] = 12  # sand if it's near water level

                                c.Blocks[x, z, 0] = 7  # bedrock

                    c.chunkChanged()
                    c.TerrainPopulated = False
                    # the quick lighting from chunkChanged has already lit this simple terrain completely
                    c.needsLighting = False

                logging.info("%s Just did chunk %d,%d" % (datetime.datetime.now().strftime("[%H:%M:%S]"), cx, cz))

            logging.info("Done with mapping!")
            self.needsSave = True
            stop = datetime.datetime.now()
            logging.info("Took %s." % str(stop - start))

            spawnz = width / 2
            spawnx = height / 2
            spawny = greyimg.getpixel((spawnx, spawnz))
            logging.info("You probably want to change your spawn point. I suggest {0}".format((spawnx, spawny, spawnz)))

    def _execute(self, command):
        """
    execute <filename>
    Execute all commands in a file and save.
    """
        if len(command) == 0:
            print "You must give the file with commands to execute"
        else:
            commandFile = open(command[0], "r")
            commandsFromFile = commandFile.readlines()
            for commandFromFile in commandsFromFile:
                print commandFromFile
                self.processCommand(commandFromFile)
            self._save("")

    def _quit(self, command):
        """
    quit [ yes | no ]

    Quits the program.
    Without 'yes' or 'no', prompts to save before quitting.

    In batch mode, an end of file automatically saves the level.
    """
        if len(command) == 0 or not (command[0].lower() in ("yes", "no")):
            if raw_input("Save before exit? ").lower() in ("yes", "y", "1", "true"):
                self._save(command)
                raise SystemExit
        if len(command) and command[0].lower == "yes":
            self._save(command)

        raise SystemExit

    def _exit(self, command):
        self._quit(command)

    def _save(self, command):
        if self.needsSave:
            self.level.generateLights()
            self.level.saveInPlace()
            self.needsSave = False

    def _load(self, command):
        """
    load [ <filename> | <world number> ]

    Loads another world, discarding all changes to this world.
    """
        if len(command) == 0:
            self.printUsage("load")
        self.loadWorld(command[0])

    def _reload(self, command):
        self.level = mclevel.fromFile(self.level.filename)

    def _dimension(self, command):
        """
    dimension [ <dim> ]

    Load another dimension, a sub-world of this level. Without options, lists
    all of the dimensions found in this world. <dim> can be a number or one of
    these keywords:
        nether, hell, slip: DIM-1
        earth, overworld, parent: parent world
        end: DIM1
    """

        if len(command):
            if command[0].lower() in ("earth", "overworld", "parent"):
                if self.level.parentWorld:
                    self.level = self.level.parentWorld
                    return
                else:
                    print "You are already on earth."
                    return

            elif command[0].lower() in ("hell", "nether", "slip"):
                dimNo = -1
            elif command[0].lower() == "end":
                dimNo = 1
            else:
                dimNo = self.readInt(command)

            if dimNo in self.level.dimensions:
                self.level = self.level.dimensions[dimNo]
                return

        if self.level.parentWorld:
            print u"Parent world: {0} ('dimension parent' to return)".format(self.level.parentWorld.displayName)

        if len(self.level.dimensions):
            print u"Dimensions in {0}:".format(self.level.displayName)
            for k in self.level.dimensions:
                print "{0}: {1}".format(k, infiniteworld.MCAlphaDimension.dimensionNames.get(k, "Unknown"))

    def _help(self, command):
        if len(command):
            self.printUsage(command[0])
        else:
            self.printUsage()

    def _blocks(self, command):
        """
    blocks [ <block name> | <block ID> ]

    Prints block IDs matching the name, or the name matching the ID.
    With nothing, prints a list of all blocks.
    """

        searchName = None
        if len(command):
            searchName = " ".join(command)
            try:
                searchNumber = int(searchName)
            except ValueError:
                searchNumber = None
                matches = self.level.materials.blocksMatching(searchName)
            else:
                matches = [b for b in self.level.materials.allBlocks if b.ID == searchNumber]
#                print "{0:3}: {1}".format(searchNumber, self.level.materials.names[searchNumber])
 #               return

        else:
            matches = self.level.materials.allBlocks

        print "{id:9} : {name} {aka}".format(id="(ID:data)", name="Block name", aka="[Other names]")
        for b in sorted(matches):
            idstring = "({ID}:{data})".format(ID=b.ID, data=b.blockData)
            aka = b.aka and " [{aka}]".format(aka=b.aka) or ""

            print "{idstring:9} : {name} {aka}".format(idstring=idstring, name=b.name, aka=aka)

    def printUsage(self, command=""):
        if command.lower() in self.commands:
            print "Usage: ", self.commandUsage(command.lower())
        else:
            print self.__doc__.format(commandPrefix=("", "mce.py <world> ")[not self.batchMode])

    def printUsageAndQuit(self):
        self.printUsage()
        raise SystemExit

    def loadWorld(self, world):

        worldpath = os.path.expanduser(world)
        if os.path.exists(worldpath):
            self.level = mclevel.fromFile(worldpath)
        else:
            self.level = mclevel.loadWorld(world)

    level = None

    batchMode = False

    def run(self):
        logging.basicConfig(format=u'%(levelname)s:%(message)s')
        logging.getLogger().level = logging.INFO

        sys.argv.pop(0)

        if len(sys.argv):
            world = sys.argv.pop(0)

            if world.lower() in ("-h", "--help"):
                self.printUsageAndQuit()

            if len(sys.argv) and sys.argv[0].lower() == "create":
                # accept the syntax, "mce world3 create"
                self._create([world])
                print "Created world {0}".format(world)

                sys.exit(0)
            else:
                self.loadWorld(world)
        else:
            self.batchMode = True
            self.printUsage()

            while True:
                try:
                    world = raw_input("Please enter world name or path to world folder: ")
                    self.loadWorld(world)
                except EOFError, e:
                    print "End of input."
                    raise SystemExit
                except Exception, e:
                    print "Cannot open {0}: {1}".format(world, e)
                else:
                    break

        if len(sys.argv):
            # process one command from command line
            try:
                self.processCommand(" ".join(sys.argv))
            except UsageError:
                self.printUsageAndQuit()
            self._save([])

        else:
            # process many commands on standard input, maybe interactively
            command = [""]
            self.batchMode = True
            while True:
                try:
                    command = raw_input(u"{0}> ".format(self.level.displayName))
                    print
                    self.processCommand(command)

                except EOFError, e:
                    print "End of file. Saving automatically."
                    self._save([])
                    raise SystemExit
                except Exception, e:
                    if self.debug:
                        traceback.print_exc()
                    print 'Exception during command: {0!r}'.format(e)
                    print "Use 'debug' to enable tracebacks."

                    # self.printUsage()

    def processCommand(self, command):
        command = command.strip()

        if len(command) == 0:
            return

        if command[0] == "#":
            return

        commandWords = command.split()

        keyword = commandWords.pop(0).lower()
        if not keyword in self.commands:
            matches = filter(lambda x: x.startswith(keyword), self.commands)
            if len(matches) == 1:
                keyword = matches[0]
            elif len(matches):
                print "Ambiguous command. Matches: "
                for k in matches:
                    print "  ", k
                return
            else:
                raise UsageError("Command {0} not recognized.".format(keyword))

        func = getattr(self, "_" + keyword)

        try:
            func(commandWords)
        except PlayerNotFound, e:
            print "Cannot find player {0}".format(e.args[0])
            self._player([])

        except UsageError, e:
            print e
            if self.debug:
                traceback.print_exc()
            self.printUsage(keyword)


def main(argv):
    profile = os.getenv("MCE_PROFILE", None)
    editor = mce()
    if profile:
        print "Profiling enabled"
        import cProfile
        cProfile.runctx('editor.run()', locals(), globals(), profile)
    else:
        editor.run()

    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = mclevel
# -*- coding: utf-8 -*-
"""
MCLevel interfaces

Sample usage:

import mclevel

# Call mclevel.fromFile to identify and open any of these four file formats:
#
# Classic levels - gzipped serialized java objects.  Returns an instance of MCJavalevel
# Indev levels - gzipped NBT data in a single file.  Returns an MCIndevLevel
# Schematics - gzipped NBT data in a single file.  Returns an MCSchematic.
#   MCSchematics have the special method rotateLeft which will reorient torches, stairs, and other tiles appropriately.
# Alpha levels - world folder structure containing level.dat and chunk folders.  Single or Multiplayer.
#   Can accept a path to the world folder or a path to the level.dat.  Returns an MCInfdevOldLevel

# Load a Classic level.
level = mclevel.fromFile("server_level.dat");

# fromFile identified the file type and returned a MCJavaLevel.  MCJavaLevel doesn't actually know any java. It guessed the
# location of the Blocks array by starting at the end of the file and moving backwards until it only finds valid blocks.
# It also doesn't know the dimensions of the level.  This is why you have to tell them to MCEdit via the filename.
# This works here too:  If the file were 512 wide, 512 long, and 128 high, I'd have to name it "server_level_512_512_128.dat"
#
# This is one area for improvement.

# Classic and Indev levels have all of their blocks in one place.
blocks = level.Blocks

# Sand to glass.
blocks[blocks == level.materials.Sand.ID] = level.materials.Glass.ID

# Save the file with another name.  This only works for non-Alpha levels.
level.saveToFile("server_level_glassy.dat");

# Load an Alpha world
# Loading an Alpha world immediately scans the folder for chunk files.  This takes longer for large worlds.
ourworld = mclevel.fromFile("C:\\Minecraft\\OurWorld");

# Convenience method to load a numbered world from the saves folder.
world1 = mclevel.loadWorldNumber(1);

# Find out which chunks are present. Doing this will scan the chunk folders the
# first time it is used. If you already know where you want to be, skip to
# world1.getChunk(xPos, zPos)

chunkPositions = list(world1.allChunks)

# allChunks returns an iterator that yields a (xPos, zPos) tuple for each chunk
xPos, zPos = chunkPositions[0];

# retrieve an AnvilChunk object. this object will load and decompress
# the chunk as needed, and remember whether it needs to be saved or relighted

chunk = world1.getChunk(xPos, zPos)

### Access the data arrays of the chunk like so:
# Take note that the array is indexed x, z, y.  The last index corresponds to
# height or altitude.

blockType = chunk.Blocks[0,0,64]
chunk.Blocks[0,0,64] = 1

# Access the chunk's Entities and TileEntities as arrays of TAG_Compound as
# they appear in the save format.

# Entities usually have Pos, Health, and id
# TileEntities usually have tileX, tileY, tileZ, and id
# For more information, google "Chunk File Format"

for entity in chunk.Entities:
    if entity["id"].value == "Spider":
        entity["Health"].value = 50


# Accessing one byte at a time from the Blocks array is very slow in Python.
# To get around this, we have methods to access multiple bytes at once.
# The first technique is slicing. You can use slicing to restrict your access
# to certain depth levels, or to extract a column or a larger section from the
# array. Standard python slice notation is used.

# Set the top half of the array to 0. The : says to use the entire array along
# that dimension. The syntax []= indicates we are overwriting part of the array
chunk.Blocks[:,:,64:] = 0

# Using [] without =  creates a 'view' on part of the array.  This is not a
# copy, it is a reference to a portion of the original array.
midBlocks = chunk.Blocks[:,:,32:64]

# Here's a gotcha:  You can't just write 'midBlocks = 0' since it will replace
# the 'midBlocks' reference itself instead of accessing the array. Instead, do
# this to access and overwrite the array using []= syntax.
midBlocks[:] = 0


# The second is masking.  Using a comparison operator ( <, >, ==, etc )
# against the Blocks array will return a 'mask' that we can use to specify
# positions in the array.

# Create the mask from the result of the equality test.
fireBlocks = ( chunk.Blocks==world.materials.Fire.ID )

# Access Blocks using the mask to set elements. The syntax is the same as
# using []= with slices
chunk.Blocks[fireBlocks] = world.materials.Leaves.ID

# You can also combine mask arrays using logical operations (&, |, ^) and use
# the mask to access any other array of the same shape.
# Here we turn all trees into birch trees.

# Extract a mask from the Blocks array to find the locations of tree trunks.
# Or | it with another mask to find the locations of leaves.
# Use the combined mask to access the Data array and set those locations to birch

# Note that the Data, BlockLight, and SkyLight arrays have been
# unpacked from 4-bit arrays to numpy uint8 arrays. This makes them much easier
# to work with.

treeBlocks = ( chunk.Blocks == world.materials.Wood.ID )
treeBlocks |= ( chunk.Blocks == world.materials.Leaves.ID )
chunk.Data[treeBlocks] = 2 # birch


# The chunk doesn't know you've changed any of that data.  Call chunkChanged()
# to let it know. This will mark the chunk for lighting calculation,
# recompression, and writing to disk. It will also immediately recalculate the
# chunk's HeightMap and fill the SkyLight only with light falling straight down.
# These are relatively fast and were added here to aid MCEdit.

chunk.chunkChanged();

# To recalculate all of the dirty lights in the world, call generateLights
world.generateLights();


# Move the player and his spawn
world.setPlayerPosition( (0, 67, 0) ) # add 3 to make sure his head isn't in the ground.
world.setPlayerSpawnPosition( (0, 64, 0) )


# Save the level.dat and any chunks that have been marked for writing to disk
# This also compresses any chunks marked for recompression.
world.saveInPlace();


# Advanced use:
# The getChunkSlices method returns an iterator that returns slices of chunks within the specified range.
# the slices are returned as tuples of (chunk, slices, point)

# chunk:  The AnvilChunk object we're interested in.
# slices:  A 3-tuple of slice objects that can be used to index chunk's data arrays
# point:  A 3-tuple of floats representing the relative position of this subslice within the larger slice.
#
# Take caution:
# the point tuple is ordered (x,y,z) in accordance with the tuples used to initialize a bounding box
# however, the slices tuple is ordered (x,z,y) for easy indexing into the arrays.

# Here is an old version of MCInfdevOldLevel.fillBlocks in its entirety:

def fillBlocks(self, box, blockType, blockData = 0):
    chunkIterator = self.getChunkSlices(box)

    for (chunk, slices, point) in chunkIterator:
        chunk.Blocks[slices] = blockType
        chunk.Data[slices] = blockData
        chunk.chunkChanged();


Copyright 2010 David Rio Vierra
"""

from indev import MCIndevLevel
from infiniteworld import MCInfdevOldLevel
from javalevel import MCJavaLevel
from logging import getLogger
from mclevelbase import saveFileDir
import nbt
from numpy import fromstring
import os
from pocket import PocketWorld
from schematic import INVEditChest, MCSchematic, ZipSchematic
import sys
import traceback

log = getLogger(__name__)

class LoadingError(RuntimeError):
    pass


def fromFile(filename, loadInfinite=True, readonly=False):
    ''' The preferred method for loading Minecraft levels of any type.
    pass False to loadInfinite if you'd rather not load infdev levels.
    '''
    log.info(u"Identifying " + filename)

    if not filename:
        raise IOError("File not found: " + filename)
    if not os.path.exists(filename):
        raise IOError("File not found: " + filename)

    if ZipSchematic._isLevel(filename):
        log.info("Zipfile found, attempting zipped infinite level")
        lev = ZipSchematic(filename)
        log.info("Detected zipped Infdev level")
        return lev

    if PocketWorld._isLevel(filename):
        return PocketWorld(filename)

    if MCInfdevOldLevel._isLevel(filename):
        log.info(u"Detected Infdev level.dat")
        if loadInfinite:
            return MCInfdevOldLevel(filename=filename, readonly=readonly)
        else:
            raise ValueError("Asked to load {0} which is an infinite level, loadInfinite was False".format(os.path.basename(filename)))

    if os.path.isdir(filename):
        raise ValueError("Folder {0} was not identified as a Minecraft level.".format(os.path.basename(filename)))

    f = file(filename, 'rb')
    rawdata = f.read()
    f.close()
    if len(rawdata) < 4:
        raise ValueError("{0} is too small! ({1}) ".format(filename, len(rawdata)))

    data = fromstring(rawdata, dtype='uint8')
    if not data.any():
        raise ValueError("{0} contains only zeroes. This file is damaged beyond repair.")

    if MCJavaLevel._isDataLevel(data):
        log.info(u"Detected Java-style level")
        lev = MCJavaLevel(filename, data)
        lev.compressed = False
        return lev

    #ungzdata = None
    compressed = True
    unzippedData = None
    try:
        unzippedData = nbt.gunzip(rawdata)
    except Exception, e:
        log.info(u"Exception during Gzip operation, assuming {0} uncompressed: {1!r}".format(filename, e))
        if unzippedData is None:
            compressed = False
            unzippedData = rawdata

    #data =
    data = unzippedData
    if MCJavaLevel._isDataLevel(data):
        log.info(u"Detected compressed Java-style level")
        lev = MCJavaLevel(filename, data)
        lev.compressed = compressed
        return lev

    try:
        root_tag = nbt.load(buf=data)

    except Exception, e:
        log.info(u"Error during NBT load: {0!r}".format(e))
        log.info(traceback.format_exc())
        log.info(u"Fallback: Detected compressed flat block array, yzx ordered ")
        try:
            lev = MCJavaLevel(filename, data)
            lev.compressed = compressed
            return lev
        except Exception, e2:
            raise LoadingError(("Multiple errors encountered", e, e2), sys.exc_info()[2])

    else:
        if MCIndevLevel._isTagLevel(root_tag):
            log.info(u"Detected Indev .mclevel")
            return MCIndevLevel(root_tag, filename)
        if MCSchematic._isTagLevel(root_tag):
            log.info(u"Detected Schematic.")
            return MCSchematic(root_tag=root_tag, filename=filename)

        if INVEditChest._isTagLevel(root_tag):
            log.info(u"Detected INVEdit inventory file")
            return INVEditChest(root_tag=root_tag, filename=filename)

    raise IOError("Cannot detect file type.")


def loadWorld(name):
    filename = os.path.join(saveFileDir, name)
    return fromFile(filename)


def loadWorldNumber(i):
    #deprecated
    filename = u"{0}{1}{2}{3}{1}".format(saveFileDir, os.sep, u"World", i)
    return fromFile(filename)

########NEW FILE########
__FILENAME__ = mclevelbase
'''
Created on Jul 22, 2011

@author: Rio
'''

from contextlib import contextmanager
from logging import getLogger
import sys
import os

log = getLogger(__name__)

@contextmanager
def notclosing(f):
    yield f


class PlayerNotFound(Exception):
    pass


class ChunkNotPresent(Exception):
    pass


class RegionMalformed(Exception):
    pass


class ChunkMalformed(ChunkNotPresent):
    pass


def exhaust(_iter):
    """Functions named ending in "Iter" return an iterable object that does
    long-running work and yields progress information on each call. exhaust()
    is used to implement the non-Iter equivalents"""
    i = None
    for i in _iter:
        pass
    return i



def win32_appdata():
    # try to use win32 api to get the AppData folder since python doesn't populate os.environ with unicode strings.

    try:
        import win32com.client
        objShell = win32com.client.Dispatch("WScript.Shell")
        return objShell.SpecialFolders("AppData")
    except Exception, e:
        print "Error while getting AppData folder using WScript.Shell.SpecialFolders: {0!r}".format(e)
        try:
            from win32com.shell import shell, shellcon
            return shell.SHGetPathFromIDListEx(
                shell.SHGetSpecialFolderLocation(0, shellcon.CSIDL_APPDATA)
            )
        except Exception, e:
            print "Error while getting AppData folder using SHGetSpecialFolderLocation: {0!r}".format(e)

            return os.environ['APPDATA'].decode(sys.getfilesystemencoding())

if sys.platform == "win32":
    appDataDir = win32_appdata()
    minecraftDir = os.path.join(appDataDir, u".minecraft")
    appSupportDir = os.path.join(appDataDir, u"pymclevel")

elif sys.platform == "darwin":
    appDataDir = os.path.expanduser(u"~/Library/Application Support")
    minecraftDir = os.path.join(appDataDir, u"minecraft")
    appSupportDir = os.path.expanduser(u"~/Library/Application Support/pymclevel/")

else:
    appDataDir = os.path.expanduser(u"~")
    minecraftDir = os.path.expanduser(u"~/.minecraft")
    appSupportDir = os.path.expanduser(u"~/.pymclevel")

saveFileDir = os.path.join(minecraftDir, u"saves")



########NEW FILE########
__FILENAME__ = minecraft_server
import atexit
import itertools
import logging
import os
from os.path import dirname, join, basename
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib

import infiniteworld
from mclevelbase import appSupportDir, exhaust, ChunkNotPresent

log = logging.getLogger(__name__)

__author__ = 'Rio'

# Thank you, Stackoverflow
# http://stackoverflow.com/questions/377017/test-if-executable-exists-in-python
def which(program):
    def is_exe(f):
        return os.path.exists(f) and os.access(f, os.X_OK)

    fpath, _fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        if sys.platform == "win32":
            if "SYSTEMROOT" in os.environ:
                root = os.environ["SYSTEMROOT"]
                exe_file = os.path.join(root, program)
                if is_exe(exe_file):
                    return exe_file
        if "PATH" in os.environ:
            for path in os.environ["PATH"].split(os.pathsep):
                exe_file = os.path.join(path, program)
                if is_exe(exe_file):
                    return exe_file

    return None


convert = lambda text: int(text) if text.isdigit() else text
alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]


def sort_nicely(l):
    """ Sort the given list in the way that humans expect.
    """
    l.sort(key=alphanum_key)


class ServerJarStorage(object):
    defaultCacheDir = os.path.join(appSupportDir, u"ServerJarStorage")

    def __init__(self, cacheDir=None):
        if cacheDir is None:
            cacheDir = self.defaultCacheDir

        self.cacheDir = cacheDir

        if not os.path.exists(self.cacheDir):
            os.makedirs(self.cacheDir)
        readme = os.path.join(self.cacheDir, "README.TXT")
        if not os.path.exists(readme):
            with file(readme, "w") as f:
                f.write("""
About this folder:

This folder is used by MCEdit and pymclevel to store different versions of the
Minecraft Server to use for terrain generation. It should have one or more
subfolders, one for each version of the server. Each subfolder must hold at
least one file named minecraft_server.jar, and the subfolder's name should
have the server's version plus the names of any installed mods.

There may already be a subfolder here (for example, "Beta 1.7.3") if you have
used the Chunk Create feature in MCEdit to create chunks using the server.

Version numbers can be automatically detected. If you place one or more
minecraft_server.jar files in this folder, they will be placed automatically
into well-named subfolders the next time you run MCEdit. If a file's name
begins with "minecraft_server" and ends with ".jar", it will be detected in
this way.
""")

        self.reloadVersions()

    def reloadVersions(self):
        cacheDirList = os.listdir(self.cacheDir)
        self.versions = list(reversed(sorted([v for v in cacheDirList if os.path.exists(self.jarfileForVersion(v))], key=alphanum_key)))

        if MCServerChunkGenerator.javaExe:
            for f in cacheDirList:
                p = os.path.join(self.cacheDir, f)
                if f.startswith("minecraft_server") and f.endswith(".jar") and os.path.isfile(p):
                    print "Unclassified minecraft_server.jar found in cache dir. Discovering version number..."
                    self.cacheNewVersion(p)
                    os.remove(p)

        print "Minecraft_Server.jar storage initialized."
        print u"Each server is stored in a subdirectory of {0} named with the server's version number".format(self.cacheDir)

        print "Cached servers: ", self.versions

    def downloadCurrentServer(self):
        print "Downloading the latest Minecraft Server..."
        try:
            (filename, headers) = urllib.urlretrieve("http://www.minecraft.net/download/minecraft_server.jar")
        except Exception, e:
            print "Error downloading server: {0!r}".format(e)
            return

        self.cacheNewVersion(filename, allowDuplicate=False)

    def cacheNewVersion(self, filename, allowDuplicate=True):
        """ Finds the version number from the server jar at filename and copies
        it into the proper subfolder of the server jar cache folder"""

        version = MCServerChunkGenerator._serverVersionFromJarFile(filename)
        print "Found version ", version
        versionDir = os.path.join(self.cacheDir, version)

        i = 1
        newVersionDir = versionDir
        while os.path.exists(newVersionDir):
            if not allowDuplicate:
                return

            newVersionDir = versionDir + " (" + str(i) + ")"
            i += 1

        os.mkdir(newVersionDir)

        shutil.copy2(filename, os.path.join(newVersionDir, "minecraft_server.jar"))

        if version not in self.versions:
            self.versions.append(version)

    def jarfileForVersion(self, v):
        return os.path.join(self.cacheDir, v, "minecraft_server.jar").encode(sys.getfilesystemencoding())

    def checksumForVersion(self, v):
        jf = self.jarfileForVersion(v)
        with file(jf, "rb") as f:
            import hashlib
            return hashlib.md5(f.read()).hexdigest()

    broken_versions = ["Beta 1.9 Prerelease {0}".format(i) for i in (1, 2, 3)]

    @property
    def latestVersion(self):
        if len(self.versions) == 0:
            return None
        return max((v for v in self.versions if v not in self.broken_versions), key=alphanum_key)

    def getJarfile(self, version=None):
        if len(self.versions) == 0:
            print "No servers found in cache."
            self.downloadCurrentServer()

        version = version or self.latestVersion
        if version not in self.versions:
            return None
        return self.jarfileForVersion(version)


class JavaNotFound(RuntimeError):
    pass


class VersionNotFound(RuntimeError):
    pass


def readProperties(filename):
    if not os.path.exists(filename):
        return {}

    with file(filename) as f:
        properties = dict((line.split("=", 2) for line in (l.strip() for l in f) if not line.startswith("#")))

    return properties


def saveProperties(filename, properties):
    with file(filename, "w") as f:
        for k, v in properties.iteritems():
            f.write("{0}={1}\n".format(k, v))


def findJava():
    if sys.platform == "win32":
        javaExe = which("java.exe")
        if javaExe is None:
            KEY_NAME = "HKLM\SOFTWARE\JavaSoft\Java Runtime Environment"
            try:
                p = subprocess.Popen(["REG", "QUERY", KEY_NAME, "/v", "CurrentVersion"], stdout=subprocess.PIPE, universal_newlines=True)
                o, e = p.communicate()
                lines = o.split("\n")
                for l in lines:
                    l = l.strip()
                    if l.startswith("CurrentVersion"):
                        words = l.split(None, 2)
                        version = words[-1]
                        p = subprocess.Popen(["REG", "QUERY", KEY_NAME + "\\" + version, "/v", "JavaHome"], stdout=subprocess.PIPE, universal_newlines=True)
                        o, e = p.communicate()
                        lines = o.split("\n")
                        for l in lines:
                            l = l.strip()
                            if l.startswith("JavaHome"):
                                w = l.split(None, 2)
                                javaHome = w[-1]
                                javaExe = os.path.join(javaHome, "bin", "java.exe")
                                print "RegQuery: java.exe found at ", javaExe
                                break

            except Exception, e:
                print "Error while locating java.exe using the Registry: ", repr(e)
    else:
        javaExe = which("java")

    return javaExe


class MCServerChunkGenerator(object):
    """Generates chunks using minecraft_server.jar. Uses a ServerJarStorage to
    store different versions of minecraft_server.jar in an application support
    folder.

        from pymclevel import *

    Example usage:

        gen = MCServerChunkGenerator()  # with no arguments, use the newest
                                        # server version in the cache, or download
                                        # the newest one automatically
        level = loadWorldNamed("MyWorld")

        gen.generateChunkInLevel(level, 12, 24)


    Using an older version:

        gen = MCServerChunkGenerator("Beta 1.6.5")

    """
    defaultJarStorage = None

    javaExe = findJava()
    jarStorage = None
    tempWorldCache = {}

    def __init__(self, version=None, jarfile=None, jarStorage=None):

        self.jarStorage = jarStorage or self.getDefaultJarStorage()

        if self.javaExe is None:
            raise JavaNotFound("Could not find java. Please check that java is installed correctly. (Could not find java in your PATH environment variable.)")
        if jarfile is None:
            jarfile = self.jarStorage.getJarfile(version)
        if jarfile is None:
            raise VersionNotFound("Could not find minecraft_server.jar for version {0}. Please make sure that a minecraft_server.jar is placed under {1} in a subfolder named after the server's version number.".format(version or "(latest)", self.jarStorage.cacheDir))
        self.serverJarFile = jarfile
        self.serverVersion = version or self._serverVersion()

    @classmethod
    def getDefaultJarStorage(cls):
        if cls.defaultJarStorage is None:
            cls.defaultJarStorage = ServerJarStorage()
        return cls.defaultJarStorage

    @classmethod
    def clearWorldCache(cls):
        cls.tempWorldCache = {}

        for tempDir in os.listdir(cls.worldCacheDir):
            t = os.path.join(cls.worldCacheDir, tempDir)
            if os.path.isdir(t):
                shutil.rmtree(t)

    def createReadme(self):
        readme = os.path.join(self.worldCacheDir, "README.TXT")

        if not os.path.exists(readme):
            with file(readme, "w") as f:
                f.write("""
    About this folder:

    This folder is used by MCEdit and pymclevel to cache levels during terrain
    generation. Feel free to delete it for any reason.
    """)

    worldCacheDir = os.path.join(tempfile.gettempdir(), "pymclevel_MCServerChunkGenerator")

    def tempWorldForLevel(self, level):

        # tempDir = tempfile.mkdtemp("mclevel_servergen")
        tempDir = os.path.join(self.worldCacheDir, self.jarStorage.checksumForVersion(self.serverVersion), str(level.RandomSeed))
        propsFile = os.path.join(tempDir, "server.properties")
        properties = readProperties(propsFile)

        tempWorld = self.tempWorldCache.get((self.serverVersion, level.RandomSeed))

        if tempWorld is None:
            if not os.path.exists(tempDir):
                os.makedirs(tempDir)
                self.createReadme()

            worldName = "world"
            worldName = properties.setdefault("level-name", worldName)

            tempWorldDir = os.path.join(tempDir, worldName)
            tempWorld = infiniteworld.MCInfdevOldLevel(tempWorldDir, create=True, random_seed=level.RandomSeed)
            tempWorld.close()

            tempWorldRO = infiniteworld.MCInfdevOldLevel(tempWorldDir, readonly=True)

            self.tempWorldCache[self.serverVersion, level.RandomSeed] = tempWorldRO

        if level.dimNo == 0:
            properties["allow-nether"] = "false"
        else:
            tempWorld = tempWorld.getDimension(level.dimNo)

            properties["allow-nether"] = "true"

        properties["server-port"] = int(32767 + random.random() * 32700)
        saveProperties(propsFile, properties)

        return tempWorld, tempDir

    def generateAtPosition(self, tempWorld, tempDir, cx, cz):
        return exhaust(self.generateAtPositionIter(tempWorld, tempDir, cx, cz))

    def generateAtPositionIter(self, tempWorld, tempDir, cx, cz, simulate=False):
        tempWorldRW = infiniteworld.MCInfdevOldLevel(tempWorld.filename)
        tempWorldRW.setPlayerSpawnPosition((cx * 16, 64, cz * 16))
        tempWorldRW.saveInPlace()
        tempWorldRW.close()
        del tempWorldRW

        tempWorld.unload()

        startTime = time.time()
        proc = self.runServer(tempDir)
        while proc.poll() is None:
            line = proc.stdout.readline().strip()
            log.info(line)
            yield line

#            Forge and FML change stderr output, causing MCServerChunkGenerator to wait endlessly.
#
#            Vanilla:
#              2012-11-13 11:29:19 [INFO] Done (9.962s)!
#
#            Forge/FML:
#              2012-11-13 11:47:13 [INFO] [Minecraft] Done (8.020s)!

            if "INFO" in line and "Done" in line:
                if simulate:
                    duration = time.time() - startTime

                    simSeconds = max(8, int(duration) + 1)

                    for i in range(simSeconds):
                        # process tile ticks
                        yield "%2d/%2d: Simulating the world for a little bit..." % (i, simSeconds)
                        time.sleep(1)

                proc.stdin.write("stop\n")
                proc.wait()
                break
            if "FAILED TO BIND" in line:
                proc.kill()
                proc.wait()
                raise RuntimeError("Server failed to bind to port!")

        stdout, _ = proc.communicate()

        if "Could not reserve enough space" in stdout and not MCServerChunkGenerator.lowMemory:
            MCServerChunkGenerator.lowMemory = True
            for i in self.generateAtPositionIter(tempWorld, tempDir, cx, cz):
                yield i

        (tempWorld.parentWorld or tempWorld).loadLevelDat()  # reload version number

    def copyChunkAtPosition(self, tempWorld, level, cx, cz):
        if level.containsChunk(cx, cz):
            return
        try:
            tempChunkBytes = tempWorld._getChunkBytes(cx, cz)
        except ChunkNotPresent, e:
            raise ChunkNotPresent, "While generating a world in {0} using server {1} ({2!r})".format(tempWorld, self.serverJarFile, e), sys.exc_info()[2]

        level.worldFolder.saveChunk(cx, cz, tempChunkBytes)
        level._allChunks = None

    def generateChunkInLevel(self, level, cx, cz):
        assert isinstance(level, infiniteworld.MCInfdevOldLevel)

        tempWorld, tempDir = self.tempWorldForLevel(level)
        self.generateAtPosition(tempWorld, tempDir, cx, cz)
        self.copyChunkAtPosition(tempWorld, level, cx, cz)

    minRadius = 5
    maxRadius = 20

    def createLevel(self, level, box, simulate=False, **kw):
        return exhaust(self.createLevelIter(level, box, simulate, **kw))

    def createLevelIter(self, level, box, simulate=False, **kw):
        if isinstance(level, basestring):
            filename = level
            level = infiniteworld.MCInfdevOldLevel(filename, create=True, **kw)

        assert isinstance(level, infiniteworld.MCInfdevOldLevel)
        minRadius = self.minRadius

        genPositions = list(itertools.product(
                       xrange(box.mincx, box.maxcx, minRadius * 2),
                       xrange(box.mincz, box.maxcz, minRadius * 2)))

        for i, (cx, cz) in enumerate(genPositions):
            log.info("Generating at %s" % ((cx, cz),))
            parentDir = dirname(os.path.abspath(level.worldFolder.filename))
            propsFile = join(parentDir, "server.properties")
            props = readProperties(join(dirname(self.serverJarFile), "server.properties"))
            props["level-name"] = basename(level.worldFolder.filename)
            props["server-port"] = int(32767 + random.random() * 32700)
            saveProperties(propsFile, props)

            for p in self.generateAtPositionIter(level, parentDir, cx, cz, simulate):
                yield i, len(genPositions), p

        level.close()

    def generateChunksInLevel(self, level, chunks):
        return exhaust(self.generateChunksInLevelIter(level, chunks))

    def generateChunksInLevelIter(self, level, chunks, simulate=False):
        tempWorld, tempDir = self.tempWorldForLevel(level)

        startLength = len(chunks)
        minRadius = self.minRadius
        maxRadius = self.maxRadius
        chunks = set(chunks)

        while len(chunks):
            length = len(chunks)
            centercx, centercz = chunks.pop()
            chunks.add((centercx, centercz))
            # assume the generator always generates at least an 11x11 chunk square.
            centercx += minRadius
            centercz += minRadius

            # boxedChunks = [cPos for cPos in chunks if inBox(cPos)]

            print "Generating {0} chunks out of {1} starting from {2}".format("XXX", len(chunks), (centercx, centercz))
            yield startLength - len(chunks), startLength

            # chunks = [c for c in chunks if not inBox(c)]

            for p in self.generateAtPositionIter(tempWorld, tempDir, centercx, centercz, simulate):
                yield startLength - len(chunks), startLength, p

            i = 0
            for cx, cz in itertools.product(
                            xrange(centercx - maxRadius, centercx + maxRadius),
                            xrange(centercz - maxRadius, centercz + maxRadius)):
                if level.containsChunk(cx, cz):
                    chunks.discard((cx, cz))
                elif ((cx, cz) in chunks
                    and all(tempWorld.containsChunk(ncx, ncz) for ncx, ncz in itertools.product(xrange(cx-1, cx+2), xrange(cz-1, cz+2)))
                    ):
                    self.copyChunkAtPosition(tempWorld, level, cx, cz)
                    i += 1
                    chunks.discard((cx, cz))
                    yield startLength - len(chunks), startLength

            if length == len(chunks):
                print "No chunks were generated. Aborting."
                break

        level.saveInPlace()

    def runServer(self, startingDir):
        if isinstance(startingDir, unicode):
            startingDir = startingDir.encode(sys.getfilesystemencoding())

        return self._runServer(startingDir, self.serverJarFile)

    lowMemory = False

    @classmethod
    def _runServer(cls, startingDir, jarfile):
        log.info("Starting server %s in %s", jarfile, startingDir)
        if cls.lowMemory:
            memflags = []
        else:
            memflags = ["-Xmx1024M", "-Xms1024M", ]

        proc = subprocess.Popen([cls.javaExe, "-Djava.awt.headless=true"] + memflags + ["-jar", jarfile],
            executable=cls.javaExe,
            cwd=startingDir,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            )

        atexit.register(proc.terminate)
        return proc

    def _serverVersion(self):
        return self._serverVersionFromJarFile(self.serverJarFile)

    @classmethod
    def _serverVersionFromJarFile(cls, jarfile):
        tempdir = tempfile.mkdtemp("mclevel_servergen")
        proc = cls._runServer(tempdir, jarfile)

        version = "Unknown"
        # out, err = proc.communicate()
        # for line in err.split("\n"):

        while proc.poll() is None:
            line = proc.stdout.readline()
            if "Preparing start region" in line:
                break
            if "Starting minecraft server version" in line:
                version = line.split("Starting minecraft server version")[1].strip()
                break

        if proc.returncode is None:
            try:
                proc.kill()
            except WindowsError:
                pass  # access denied, process already terminated

        proc.wait()
        shutil.rmtree(tempdir)
        if ";)" in version:
            version = version.replace(";)", "")  # Damnit, Jeb!
        # Versions like "0.2.1" are alphas, and versions like "1.0.0" without "Beta" are releases
        if version[0] == "0":
            version = "Alpha " + version
        try:
            if int(version[0]) > 0:
                version = "Release " + version
        except ValueError:
            pass

        return version

########NEW FILE########
__FILENAME__ = nbt

# vim:set sw=2 sts=2 ts=2:

"""
Named Binary Tag library. Serializes and deserializes TAG_* objects
to and from binary data. Load a Minecraft level by calling nbt.load().
Create your own TAG_* objects and set their values.
Save a TAG_* object to a file or StringIO object.

Read the test functions at the end of the file to get started.

This library requires Numpy.    Get it here:
http://new.scipy.org/download.html

Official NBT documentation is here:
http://www.minecraft.net/docs/NBT.txt


Copyright 2010 David Rio Vierra
"""
import collections
import gzip
import itertools
import logging
import struct
import zlib
from cStringIO import StringIO

import numpy
from numpy import array, zeros, fromstring


log = logging.getLogger(__name__)


class NBTFormatError(RuntimeError):
    pass


TAG_BYTE = 1
TAG_SHORT = 2
TAG_INT = 3
TAG_LONG = 4
TAG_FLOAT = 5
TAG_DOUBLE = 6
TAG_BYTE_ARRAY = 7
TAG_STRING = 8
TAG_LIST = 9
TAG_COMPOUND = 10
TAG_INT_ARRAY = 11
TAG_SHORT_ARRAY = 12


class TAG_Value(object):
    """Simple values. Subclasses override fmt to change the type and size.
    Subclasses may set data_type instead of overriding setValue for automatic data type coercion"""
    __slots__ = ('_name', '_value')

    def __init__(self, value=0, name=""):
        self.value = value
        self.name = name

    fmt = struct.Struct("b")
    tagID = NotImplemented
    data_type = NotImplemented

    _name = None
    _value = None

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, newVal):
        """Change the TAG's value. Data types are checked and coerced if needed."""
        self._value = self.data_type(newVal)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, newVal):
        """Change the TAG's name. Coerced to a unicode."""
        self._name = unicode(newVal)

    @classmethod
    def load_from(cls, ctx):
        data = ctx.data[ctx.offset:]
        (value,) = cls.fmt.unpack_from(data)
        self = cls(value=value)
        ctx.offset += self.fmt.size
        return self

    def __repr__(self):
        return "<%s name=\"%s\" value=%r>" % (str(self.__class__.__name__), self.name, self.value)

    def write_tag(self, buf):
        buf.write(chr(self.tagID))

    def write_name(self, buf):
        if self.name is not None:
            write_string(self.name, buf)

    def write_value(self, buf):
        buf.write(self.fmt.pack(self.value))


class TAG_Byte(TAG_Value):
    __slots__ = ('_name', '_value')
    tagID = TAG_BYTE
    fmt = struct.Struct(">b")
    data_type = int


class TAG_Short(TAG_Value):
    __slots__ = ('_name', '_value')
    tagID = TAG_SHORT
    fmt = struct.Struct(">h")
    data_type = int


class TAG_Int(TAG_Value):
    __slots__ = ('_name', '_value')
    tagID = TAG_INT
    fmt = struct.Struct(">i")
    data_type = int


class TAG_Long(TAG_Value):
    __slots__ = ('_name', '_value')
    tagID = TAG_LONG
    fmt = struct.Struct(">q")
    data_type = long


class TAG_Float(TAG_Value):
    __slots__ = ('_name', '_value')
    tagID = TAG_FLOAT
    fmt = struct.Struct(">f")
    data_type = float


class TAG_Double(TAG_Value):
    __slots__ = ('_name', '_value')
    tagID = TAG_DOUBLE
    fmt = struct.Struct(">d")
    data_type = float


class TAG_Byte_Array(TAG_Value):
    """Like a string, but for binary data. Four length bytes instead of
    two. Value is a numpy array, and you can change its elements"""

    tagID = TAG_BYTE_ARRAY

    def __init__(self, value=None, name=""):
        if value is None:
            value = zeros(0, self.dtype)
        self.name = name
        self.value = value

    def __repr__(self):
        return "<%s name=%s length=%d>" % (self.__class__, self.name, len(self.value))

    __slots__ = ('_name', '_value')

    def data_type(self, value):
        return array(value, self.dtype)

    dtype = numpy.dtype('uint8')

    @classmethod
    def load_from(cls, ctx):
        data = ctx.data[ctx.offset:]
        (string_len,) = TAG_Int.fmt.unpack_from(data)
        value = fromstring(data[4:string_len * cls.dtype.itemsize + 4], cls.dtype)
        self = cls(value)
        ctx.offset += string_len * cls.dtype.itemsize + 4
        return self

    def write_value(self, buf):
        value_str = self.value.tostring()
        buf.write(struct.pack(">I%ds" % (len(value_str),), self.value.size, value_str))


class TAG_Int_Array(TAG_Byte_Array):
    """An array of big-endian 32-bit integers"""
    tagID = TAG_INT_ARRAY
    __slots__ = ('_name', '_value')
    dtype = numpy.dtype('>u4')



class TAG_Short_Array(TAG_Int_Array):
    """An array of big-endian 16-bit integers. Not official, but used by some mods."""
    tagID = TAG_SHORT_ARRAY
    __slots__ = ('_name', '_value')
    dtype = numpy.dtype('>u2')


class TAG_String(TAG_Value):
    """String in UTF-8
    The value parameter must be a 'unicode' or a UTF-8 encoded 'str'
    """

    tagID = TAG_STRING

    def __init__(self, value="", name=""):
        if name:
            self.name = name
        self.value = value

    _decodeCache = {}

    __slots__ = ('_name', '_value')

    def data_type(self, value):
        if isinstance(value, unicode):
            return value
        else:
            decoded = self._decodeCache.get(value)
            if decoded is None:
                decoded = value.decode('utf-8')
                self._decodeCache[value] = decoded

            return decoded


    @classmethod
    def load_from(cls, ctx):
        value = load_string(ctx)
        return cls(value)

    def write_value(self, buf):
        write_string(self._value, buf)

string_len_fmt = struct.Struct(">H")


def load_string(ctx):
    data = ctx.data[ctx.offset:]
    (string_len,) = string_len_fmt.unpack_from(data)

    value = data[2:string_len + 2].tostring()
    ctx.offset += string_len + 2
    return value


def write_string(string, buf):
    encoded = string.encode('utf-8')
    buf.write(struct.pack(">h%ds" % (len(encoded),), len(encoded), encoded))

#noinspection PyMissingConstructor


class TAG_Compound(TAG_Value, collections.MutableMapping):
    """A heterogenous list of named tags. Names must be unique within
    the TAG_Compound. Add tags to the compound using the subscript
    operator [].    This will automatically name the tags."""

    tagID = TAG_COMPOUND

    ALLOW_DUPLICATE_KEYS = False

    __slots__ = ('_name', '_value')

    def __init__(self, value=None, name=""):
        self.value = value or []
        self.name = name

    def __repr__(self):
        return "<%s name='%s' keys=%r>" % (str(self.__class__.__name__), self.name, self.keys())

    def data_type(self, val):
        for i in val:
            self.check_value(i)
        return list(val)

    def check_value(self, val):
        if not isinstance(val, TAG_Value):
            raise TypeError("Invalid type for TAG_Compound element: %s" % val.__class__.__name__)
        if not val.name:
            raise ValueError("Tag needs a name to be inserted into TAG_Compound: %s" % val)

    @classmethod
    def load_from(cls, ctx):
        self = cls()
        while ctx.offset < len(ctx.data):
            tag_type = ctx.data[ctx.offset]
            ctx.offset += 1

            if tag_type == 0:
                break

            tag_name = load_string(ctx)
            tag = tag_classes[tag_type].load_from(ctx)
            tag.name = tag_name

            self._value.append(tag)

        return self

    def save(self, filename_or_buf=None, compressed=True):
        """
        Save the TAG_Compound element to a file. Since this element is the root tag, it can be named.

        Pass a filename to save the data to a file. Pass a file-like object (with a read() method)
        to write the data to that object. Pass nothing to return the data as a string.
        """
        if self.name is None:
            self.name = ""

        buf = StringIO()
        self.write_tag(buf)
        self.write_name(buf)
        self.write_value(buf)
        data = buf.getvalue()

        if compressed:
            gzio = StringIO()
            gz = gzip.GzipFile(fileobj=gzio, mode='wb')
            gz.write(data)
            gz.close()
            data = gzio.getvalue()

        if filename_or_buf is None:
            return data

        if isinstance(filename_or_buf, basestring):
            f = file(filename_or_buf, "wb")
            f.write(data)
        else:
            filename_or_buf.write(data)

    def write_value(self, buf):
        for tag in self.value:
            tag.write_tag(buf)
            tag.write_name(buf)
            tag.write_value(buf)

        buf.write("\x00")

    # --- collection functions ---

    def __getitem__(self, key):
        # hits=filter(lambda x: x.name==key, self.value)
        # if(len(hits)): return hits[0]
        for tag in self.value:
            if tag.name == key:
                return tag
        raise KeyError("Key {0} not found".format(key))

    def __iter__(self):
        return itertools.imap(lambda x: x.name, self.value)

    def __contains__(self, key):
        return key in map(lambda x: x.name, self.value)

    def __len__(self):
        return self.value.__len__()

    def __setitem__(self, key, item):
        """Automatically wraps lists and tuples in a TAG_List, and wraps strings
        and unicodes in a TAG_String."""
        if isinstance(item, (list, tuple)):
            item = TAG_List(item)
        elif isinstance(item, basestring):
            item = TAG_String(item)

        item.name = key
        self.check_value(item)

        # remove any items already named "key".
        if not self.ALLOW_DUPLICATE_KEYS:
            self._value = filter(lambda x: x.name != key, self._value)

        self._value.append(item)

    def __delitem__(self, key):
        self.value.__delitem__(self.value.index(self[key]))

    def add(self, value):
        if value.name is None:
            raise ValueError("Tag %r must have a name." % value)

        self[value.name] = value

    def get_all(self, key):
        return [v for v in self._value if v.name == key]

class TAG_List(TAG_Value, collections.MutableSequence):
    """A homogenous list of unnamed data of a single TAG_* type.
    Once created, the type can only be changed by emptying the list
    and adding an element of the new type. If created with no arguments,
    returns a list of TAG_Compound

    Empty lists in the wild have been seen with type TAG_Byte"""

    tagID = 9

    def __init__(self, value=None, name="", list_type=TAG_BYTE):
        # can be created from a list of tags in value, with an optional
        # name, or created from raw tag data, or created with list_type
        # taken from a TAG class or instance

        self.name = name
        self.list_type = list_type
        self.value = value or []

    __slots__ = ('_name', '_value')


    def __repr__(self):
        return "<%s name='%s' list_type=%r length=%d>" % (self.__class__.__name__, self.name,
                                                          tag_classes[self.list_type],
                                                          len(self))

    def data_type(self, val):
        if val:
            self.list_type = val[0].tagID
        assert all([x.tagID == self.list_type for x in val])
        return list(val)



    @classmethod
    def load_from(cls, ctx):
        self = cls()
        self.list_type = ctx.data[ctx.offset]
        ctx.offset += 1

        (list_length,) = TAG_Int.fmt.unpack_from(ctx.data, ctx.offset)
        ctx.offset += TAG_Int.fmt.size

        for i in range(list_length):
            tag = tag_classes[self.list_type].load_from(ctx)
            self.append(tag)

        return self


    def write_value(self, buf):
       buf.write(chr(self.list_type))
       buf.write(TAG_Int.fmt.pack(len(self.value)))
       for i in self.value:
           i.write_value(buf)

    def check_tag(self, value):
        if value.tagID != self.list_type:
            raise TypeError("Invalid type %s for TAG_List(%s)" % (value.__class__, tag_classes[self.list_type]))

    # --- collection methods ---

    def __iter__(self):
        return iter(self.value)

    def __contains__(self, tag):
        return tag in self.value

    def __getitem__(self, index):
        return self.value[index]

    def __len__(self):
        return len(self.value)

    def __setitem__(self, index, value):
        if isinstance(index, slice):
            for tag in value:
                self.check_tag(tag)
        else:
            self.check_tag(value)

        self.value[index] = value

    def __delitem__(self, index):
        del self.value[index]

    def insert(self, index, value):
        if len(self) == 0:
            self.list_type = value.tagID
        else:
            self.check_tag(value)

        value.name = ""
        self.value.insert(index, value)


tag_classes = { c.tagID: c for c in (TAG_Byte, TAG_Short, TAG_Int, TAG_Long, TAG_Float, TAG_Double, TAG_String,
    TAG_Byte_Array, TAG_List, TAG_Compound, TAG_Int_Array, TAG_Short_Array) }



def gunzip(data):
    return gzip.GzipFile(fileobj=StringIO(data)).read()


def try_gunzip(data):
    try:
        data = gunzip(data)
    except IOError, zlib.error:
        pass
    return data


def load(filename="", buf=None):
    """
    Unserialize data from an NBT file and return the root TAG_Compound object. If filename is passed,
    reads from the file, otherwise uses data from buf. Buf can be a buffer object with a read() method or a string
    containing NBT data.
    """
    if filename:
        buf = file(filename, "rb")

    if hasattr(buf, "read"):
        buf = buf.read()

    return _load_buffer(try_gunzip(buf))

class load_ctx(object):
    pass

def _load_buffer(buf):
    if isinstance(buf, str):
        buf = fromstring(buf, 'uint8')
    data = buf

    if not len(data):
        raise NBTFormatError("Asked to load root tag of zero length")

    tag_type = data[0]
    if tag_type != 10:
        magic = data[:4]
        raise NBTFormatError('Not an NBT file with a root TAG_Compound '
                             '(file starts with "%s" (0x%08x)' % (magic.tostring(), magic.view(dtype='uint32')))

    ctx = load_ctx()
    ctx.offset = 1
    ctx.data = data

    tag_name = load_string(ctx)
    tag = TAG_Compound.load_from(ctx)
    tag.name = tag_name

    return tag


__all__ = [a.__name__ for a in tag_classes.itervalues()] + ["load", "gunzip"]

import nbt_util

TAG_Value.__str__ = nbt_util.nested_string

try:
    #noinspection PyUnresolvedReferences
    from _nbt import (load, TAG_Byte, TAG_Short, TAG_Int, TAG_Long, TAG_Float, TAG_Double, TAG_String,
    TAG_Byte_Array, TAG_List, TAG_Compound, TAG_Int_Array, TAG_Short_Array, NBTFormatError)
except ImportError:
    pass


########NEW FILE########
__FILENAME__ = nbt_util
import nbt

def nested_string(tag, indent_string="  ", indent=0):
    result = ""

    if tag.tagID == nbt.TAG_COMPOUND:
        result += 'TAG_Compound({\n'
        indent += 1
        for key, value in tag.iteritems():
            result += indent_string * indent + '"%s": %s,\n' % (key, nested_string(value, indent_string, indent))
        indent -= 1
        result += indent_string * indent + '})'

    elif tag.tagID == nbt.TAG_LIST:
        result += 'TAG_List([\n'
        indent += 1
        for index, value in enumerate(tag):
            result += indent_string * indent + nested_string(value, indent_string, indent) + ",\n"
        indent -= 1
        result += indent_string * indent + '])'

    else:
        result += "%s(%r)" % (tag.__class__.__name__, tag.value)

    return result



########NEW FILE########
__FILENAME__ = pocket
from level import FakeChunk
import logging
from materials import pocketMaterials
from mclevelbase import ChunkNotPresent, notclosing
from nbt import TAG_List
from numpy import array, fromstring, zeros
import os
import struct

# values are usually little-endian, unlike Minecraft PC

logger = logging.getLogger(__name__)


class PocketChunksFile(object):
    holdFileOpen = False  # if False, reopens and recloses the file on each access
    SECTOR_BYTES = 4096
    CHUNK_HEADER_SIZE = 4

    @property
    def file(self):
        openfile = lambda: file(self.path, "rb+")
        if PocketChunksFile.holdFileOpen:
            if self._file is None:
                self._file = openfile()
            return notclosing(self._file)
        else:
            return openfile()

    def close(self):
        if PocketChunksFile.holdFileOpen:
            self._file.close()
            self._file = None

    def __init__(self, path):
        self.path = path
        self._file = None
        if not os.path.exists(path):
            file(path, "w").close()

        with self.file as f:

            filesize = os.path.getsize(path)
            if filesize & 0xfff:
                filesize = (filesize | 0xfff) + 1
                f.truncate(filesize)

            if filesize == 0:
                filesize = self.SECTOR_BYTES
                f.truncate(filesize)

            f.seek(0)
            offsetsData = f.read(self.SECTOR_BYTES)

            self.freeSectors = [True] * (filesize / self.SECTOR_BYTES)
            self.freeSectors[0] = False

            self.offsets = fromstring(offsetsData, dtype='<u4')

        needsRepair = False

        for index, offset in enumerate(self.offsets):
            sector = offset >> 8
            count = offset & 0xff

            for i in xrange(sector, sector + count):
                if i >= len(self.freeSectors):
                    # raise RegionMalformed("Region file offset table points to sector {0} (past the end of the file)".format(i))
                    print  "Region file offset table points to sector {0} (past the end of the file)".format(i)
                    needsRepair = True
                    break
                if self.freeSectors[i] is False:
                    logger.debug("Double-allocated sector number %s (offset %s @ %s)", i, offset, index)
                    needsRepair = True
                self.freeSectors[i] = False

        if needsRepair:
            self.repair()

        logger.info("Found region file {file} with {used}/{total} sectors used and {chunks} chunks present".format(
             file=os.path.basename(path), used=self.usedSectors, total=self.sectorCount, chunks=self.chunkCount))

    @property
    def usedSectors(self):
        return len(self.freeSectors) - sum(self.freeSectors)

    @property
    def sectorCount(self):
        return len(self.freeSectors)

    @property
    def chunkCount(self):
        return sum(self.offsets > 0)

    def repair(self):
        pass
#        lostAndFound = {}
#        _freeSectors = [True] * len(self.freeSectors)
#        _freeSectors[0] = _freeSectors[1] = False
#        deleted = 0
#        recovered = 0
#        logger.info("Beginning repairs on {file} ({chunks} chunks)".format(file=os.path.basename(self.path), chunks=sum(self.offsets > 0)))
#        rx, rz = self.regionCoords
#        for index, offset in enumerate(self.offsets):
#            if offset:
#                cx = index & 0x1f
#                cz = index >> 5
#                cx += rx << 5
#                cz += rz << 5
#                sectorStart = offset >> 8
#                sectorCount = offset & 0xff
#                try:
#
#                    if sectorStart + sectorCount > len(self.freeSectors):
#                        raise RegionMalformed("Offset {start}:{end} ({offset}) at index {index} pointed outside of the file".format()
#                            start=sectorStart, end=sectorStart + sectorCount, index=index, offset=offset)
#
#                    compressedData = self._readChunk(cx, cz)
#                    if compressedData is None:
#                        raise RegionMalformed("Failed to read chunk data for {0}".format((cx, cz)))
#
#                    format, data = self.decompressSectors(compressedData)
#                    chunkTag = nbt.load(buf=data)
#                    lev = chunkTag["Level"]
#                    xPos = lev["xPos"].value
#                    zPos = lev["zPos"].value
#                    overlaps = False
#
#                    for i in xrange(sectorStart, sectorStart + sectorCount):
#                        if _freeSectors[i] is False:
#                            overlaps = True
#                        _freeSectors[i] = False
#
#
#                    if xPos != cx or zPos != cz or overlaps:
#                        lostAndFound[xPos, zPos] = (format, compressedData)
#
#                        if (xPos, zPos) != (cx, cz):
#                            raise RegionMalformed("Chunk {found} was found in the slot reserved for {expected}".format(found=(xPos, zPos), expected=(cx, cz)))
#                        else:
#                            raise RegionMalformed("Chunk {found} (in slot {expected}) has overlapping sectors with another chunk!".format(found=(xPos, zPos), expected=(cx, cz)))
#
#
#
#                except Exception, e:
#                    logger.info("Unexpected chunk data at sector {sector} ({exc})".format(sector=sectorStart, exc=e))
#                    self.setOffset(cx, cz, 0)
#                    deleted += 1
#
#        for cPos, (format, foundData) in lostAndFound.iteritems():
#            cx, cz = cPos
#            if self.getOffset(cx, cz) == 0:
#                logger.info("Found chunk {found} and its slot is empty, recovering it".format(found=cPos))
#                self._saveChunk(cx, cz, foundData[5:], format)
#                recovered += 1
#
#        logger.info("Repair complete. Removed {0} chunks, recovered {1} chunks, net {2}".format(deleted, recovered, recovered - deleted))
#


    def _readChunk(self, cx, cz):
        cx &= 0x1f
        cz &= 0x1f
        offset = self.getOffset(cx, cz)
        if offset == 0:
            return None

        sectorStart = offset >> 8
        numSectors = offset & 0xff
        if numSectors == 0:
            return None

        if sectorStart + numSectors > len(self.freeSectors):
            return None

        with self.file as f:
            f.seek(sectorStart * self.SECTOR_BYTES)
            data = f.read(numSectors * self.SECTOR_BYTES)
        assert(len(data) > 0)
        logger.debug("REGION LOAD %s,%s sector %s", cx, cz, sectorStart)
        return data

    def loadChunk(self, cx, cz, world):
        data = self._readChunk(cx, cz)
        if data is None:
            raise ChunkNotPresent((cx, cz, self))

        chunk = PocketChunk(cx, cz, data[4:], world)
        return chunk

    def saveChunk(self, chunk):
        cx, cz = chunk.chunkPosition

        cx &= 0x1f
        cz &= 0x1f
        offset = self.getOffset(cx, cz)
        sectorNumber = offset >> 8
        sectorsAllocated = offset & 0xff

        data = chunk._savedData()

        sectorsNeeded = (len(data) + self.CHUNK_HEADER_SIZE) / self.SECTOR_BYTES + 1
        if sectorsNeeded >= 256:
            return

        if sectorNumber != 0 and sectorsAllocated >= sectorsNeeded:
            logger.debug("REGION SAVE {0},{1} rewriting {2}b".format(cx, cz, len(data)))
            self.writeSector(sectorNumber, data, format)
        else:
            # we need to allocate new sectors

            # mark the sectors previously used for this chunk as free
            for i in xrange(sectorNumber, sectorNumber + sectorsAllocated):
                self.freeSectors[i] = True

            runLength = 0
            try:
                runStart = self.freeSectors.index(True)

                for i in range(runStart, len(self.freeSectors)):
                    if runLength:
                        if self.freeSectors[i]:
                            runLength += 1
                        else:
                            runLength = 0
                    elif self.freeSectors[i]:
                        runStart = i
                        runLength = 1

                    if runLength >= sectorsNeeded:
                        break
            except ValueError:
                pass

            # we found a free space large enough
            if runLength >= sectorsNeeded:
                logger.debug("REGION SAVE {0},{1}, reusing {2}b".format(cx, cz, len(data)))
                sectorNumber = runStart
                self.setOffset(cx, cz, sectorNumber << 8 | sectorsNeeded)
                self.writeSector(sectorNumber, data, format)
                self.freeSectors[sectorNumber:sectorNumber + sectorsNeeded] = [False] * sectorsNeeded

            else:
                # no free space large enough found -- we need to grow the
                # file

                logger.debug("REGION SAVE {0},{1}, growing by {2}b".format(cx, cz, len(data)))

                with self.file as f:
                    f.seek(0, 2)
                    filesize = f.tell()

                    sectorNumber = len(self.freeSectors)

                    assert sectorNumber * self.SECTOR_BYTES == filesize

                    filesize += sectorsNeeded * self.SECTOR_BYTES
                    f.truncate(filesize)

                self.freeSectors += [False] * sectorsNeeded

                self.setOffset(cx, cz, sectorNumber << 8 | sectorsNeeded)
                self.writeSector(sectorNumber, data, format)

    def writeSector(self, sectorNumber, data, format):
        with self.file as f:
            logger.debug("REGION: Writing sector {0}".format(sectorNumber))

            f.seek(sectorNumber * self.SECTOR_BYTES)
            f.write(struct.pack("<I", len(data) + self.CHUNK_HEADER_SIZE))  # // chunk length
            f.write(data)  # // chunk data
            # f.flush()

    def containsChunk(self, cx, cz):
        return self.getOffset(cx, cz) != 0

    def getOffset(self, cx, cz):
        cx &= 0x1f
        cz &= 0x1f
        return self.offsets[cx + cz * 32]

    def setOffset(self, cx, cz, offset):
        cx &= 0x1f
        cz &= 0x1f
        self.offsets[cx + cz * 32] = offset
        with self.file as f:
            f.seek(0)
            f.write(self.offsets.tostring())

    def chunkCoords(self):
        indexes = (i for (i, offset) in enumerate(self.offsets) if offset)
        coords = ((i % 32, i // 32) for i in indexes)
        return coords

from infiniteworld import ChunkedLevelMixin
from level import MCLevel, LightedChunk


class PocketWorld(ChunkedLevelMixin, MCLevel):
    Height = 128
    Length = 512
    Width = 512

    isInfinite = True  # Wrong. isInfinite actually means 'isChunked' and should be changed
    materials = pocketMaterials

    @property
    def allChunks(self):
        return list(self.chunkFile.chunkCoords())

    def __init__(self, filename):
        if not os.path.isdir(filename):
            filename = os.path.dirname(filename)
        self.filename = filename
        self.dimensions = {}

        self.chunkFile = PocketChunksFile(os.path.join(filename, "chunks.dat"))
        self._loadedChunks = {}

    def getChunk(self, cx, cz):
        for p in cx, cz:
            if not 0 <= p <= 31:
                raise ChunkNotPresent((cx, cz, self))

        c = self._loadedChunks.get((cx, cz))
        if c is None:
            c = self.chunkFile.loadChunk(cx, cz, self)
            self._loadedChunks[cx, cz] = c
        return c

    @classmethod
    def _isLevel(cls, filename):
        clp = ("chunks.dat", "level.dat")

        if not os.path.isdir(filename):
            f = os.path.basename(filename)
            if f not in clp:
                return False
            filename = os.path.dirname(filename)

        return all([os.path.exists(os.path.join(filename, f)) for f in clp])

    def saveInPlace(self):
        for chunk in self._loadedChunks.itervalues():
            if chunk.dirty:
                self.chunkFile.saveChunk(chunk)
                chunk.dirty = False

    def containsChunk(self, cx, cz):
        if cx > 31 or cz > 31 or cx < 0 or cz < 0:
            return False
        return self.chunkFile.getOffset(cx, cz) != 0

    @property
    def chunksNeedingLighting(self):
        for chunk in self._loadedChunks.itervalues():
            if chunk.needsLighting:
                yield chunk.chunkPosition

class PocketChunk(LightedChunk):
    HeightMap = FakeChunk.HeightMap

    Entities = TileEntities = property(lambda self: TAG_List())

    dirty = False
    filename = "chunks.dat"

    def __init__(self, cx, cz, data, world):
        self.chunkPosition = (cx, cz)
        self.world = world
        data = fromstring(data, dtype='uint8')

        self.Blocks, data = data[:32768], data[32768:]
        self.Data, data = data[:16384], data[16384:]
        self.SkyLight, data = data[:16384], data[16384:]
        self.BlockLight, data = data[:16384], data[16384:]
        self.DirtyColumns = data[:256]

        self.unpackChunkData()
        self.shapeChunkData()


    def unpackChunkData(self):
        for key in ('SkyLight', 'BlockLight', 'Data'):
            dataArray = getattr(self, key)
            dataArray.shape = (16, 16, 64)
            s = dataArray.shape
            # assert s[2] == self.world.Height / 2
            # unpackedData = insert(dataArray[...,newaxis], 0, 0, 3)

            unpackedData = zeros((s[0], s[1], s[2] * 2), dtype='uint8')

            unpackedData[:, :, ::2] = dataArray
            unpackedData[:, :, ::2] &= 0xf
            unpackedData[:, :, 1::2] = dataArray
            unpackedData[:, :, 1::2] >>= 4
            setattr(self, key, unpackedData)

    def shapeChunkData(self):
        chunkSize = 16
        self.Blocks.shape = (chunkSize, chunkSize, self.world.Height)
        self.SkyLight.shape = (chunkSize, chunkSize, self.world.Height)
        self.BlockLight.shape = (chunkSize, chunkSize, self.world.Height)
        self.Data.shape = (chunkSize, chunkSize, self.world.Height)
        self.DirtyColumns.shape = chunkSize, chunkSize

    def _savedData(self):
        def packData(dataArray):
            assert dataArray.shape[2] == self.world.Height

            data = array(dataArray).reshape(16, 16, self.world.Height / 2, 2)
            data[..., 1] <<= 4
            data[..., 1] |= data[..., 0]
            return array(data[:, :, :, 1])

        if self.dirty:
            # elements of DirtyColumns are bitfields. Each bit corresponds to a
            # 16-block segment of the column. We set all of the bits because
            # we only track modifications at the chunk level.
            self.DirtyColumns[:] = 255

        return "".join([self.Blocks.tostring(),
                       packData(self.Data).tostring(),
                       packData(self.SkyLight).tostring(),
                       packData(self.BlockLight).tostring(),
                       self.DirtyColumns.tostring(),
                       ])

########NEW FILE########
__FILENAME__ = regionfile
import logging
import os
import struct
import zlib

from numpy import fromstring
import time
from mclevelbase import notclosing, RegionMalformed, ChunkNotPresent
import nbt

log = logging.getLogger(__name__)

__author__ = 'Rio'

def deflate(data):
    return zlib.compress(data, 2)

def inflate(data):
    return zlib.decompress(data)


class MCRegionFile(object):
    holdFileOpen = False  # if False, reopens and recloses the file on each access

    @property
    def file(self):
        openfile = lambda: file(self.path, "rb+")
        if MCRegionFile.holdFileOpen:
            if self._file is None:
                self._file = openfile()
            return notclosing(self._file)
        else:
            return openfile()

    def close(self):
        if MCRegionFile.holdFileOpen:
            self._file.close()
            self._file = None

    def __del__(self):
        self.close()

    def __init__(self, path, regionCoords):
        self.path = path
        self.regionCoords = regionCoords
        self._file = None
        if not os.path.exists(path):
            file(path, "w").close()

        with self.file as f:

            filesize = os.path.getsize(path)
            if filesize & 0xfff:
                filesize = (filesize | 0xfff) + 1
                f.truncate(filesize)

            if filesize == 0:
                filesize = self.SECTOR_BYTES * 2
                f.truncate(filesize)

            f.seek(0)
            offsetsData = f.read(self.SECTOR_BYTES)
            modTimesData = f.read(self.SECTOR_BYTES)

            self.freeSectors = [True] * (filesize / self.SECTOR_BYTES)
            self.freeSectors[0:2] = False, False

            self.offsets = fromstring(offsetsData, dtype='>u4')
            self.modTimes = fromstring(modTimesData, dtype='>u4')

        needsRepair = False

        for offset in self.offsets:
            sector = offset >> 8
            count = offset & 0xff

            for i in xrange(sector, sector + count):
                if i >= len(self.freeSectors):
                    # raise RegionMalformed("Region file offset table points to sector {0} (past the end of the file)".format(i))
                    print  "Region file offset table points to sector {0} (past the end of the file)".format(i)
                    needsRepair = True
                    break
                if self.freeSectors[i] is False:
                    needsRepair = True
                self.freeSectors[i] = False

        if needsRepair:
            self.repair()

        log.info("Found region file {file} with {used}/{total} sectors used and {chunks} chunks present".format(
             file=os.path.basename(path), used=self.usedSectors, total=self.sectorCount, chunks=self.chunkCount))

    def __repr__(self):
        return "%s(\"%s\")" % (self.__class__.__name__, self.path)
    @property
    def usedSectors(self):
        return len(self.freeSectors) - sum(self.freeSectors)

    @property
    def sectorCount(self):
        return len(self.freeSectors)

    @property
    def chunkCount(self):
        return sum(self.offsets > 0)

    def repair(self):
        lostAndFound = {}
        _freeSectors = [True] * len(self.freeSectors)
        _freeSectors[0] = _freeSectors[1] = False
        deleted = 0
        recovered = 0
        log.info("Beginning repairs on {file} ({chunks} chunks)".format(file=os.path.basename(self.path), chunks=sum(self.offsets > 0)))
        rx, rz = self.regionCoords
        for index, offset in enumerate(self.offsets):
            if offset:
                cx = index & 0x1f
                cz = index >> 5
                cx += rx << 5
                cz += rz << 5
                sectorStart = offset >> 8
                sectorCount = offset & 0xff
                try:

                    if sectorStart + sectorCount > len(self.freeSectors):
                        raise RegionMalformed("Offset {start}:{end} ({offset}) at index {index} pointed outside of the file".format(
                            start=sectorStart, end=sectorStart + sectorCount, index=index, offset=offset))

                    data = self.readChunk(cx, cz)
                    if data is None:
                        raise RegionMalformed("Failed to read chunk data for {0}".format((cx, cz)))

                    chunkTag = nbt.load(buf=data)
                    lev = chunkTag["Level"]
                    xPos = lev["xPos"].value
                    zPos = lev["zPos"].value
                    overlaps = False

                    for i in xrange(sectorStart, sectorStart + sectorCount):
                        if _freeSectors[i] is False:
                            overlaps = True
                        _freeSectors[i] = False

                    if xPos != cx or zPos != cz or overlaps:
                        lostAndFound[xPos, zPos] = data

                        if (xPos, zPos) != (cx, cz):
                            raise RegionMalformed("Chunk {found} was found in the slot reserved for {expected}".format(found=(xPos, zPos), expected=(cx, cz)))
                        else:
                            raise RegionMalformed("Chunk {found} (in slot {expected}) has overlapping sectors with another chunk!".format(found=(xPos, zPos), expected=(cx, cz)))

                except Exception, e:
                    log.info("Unexpected chunk data at sector {sector} ({exc})".format(sector=sectorStart, exc=e))
                    self.setOffset(cx, cz, 0)
                    deleted += 1

        for cPos, foundData in lostAndFound.iteritems():
            cx, cz = cPos
            if self.getOffset(cx, cz) == 0:
                log.info("Found chunk {found} and its slot is empty, recovering it".format(found=cPos))
                self.saveChunk(cx, cz, foundData)
                recovered += 1

        log.info("Repair complete. Removed {0} chunks, recovered {1} chunks, net {2}".format(deleted, recovered, recovered - deleted))


    def _readChunk(self, cx, cz):
        cx &= 0x1f
        cz &= 0x1f
        offset = self.getOffset(cx, cz)
        if offset == 0:
            raise ChunkNotPresent((cx, cz))

        sectorStart = offset >> 8
        numSectors = offset & 0xff
        if numSectors == 0:
            raise ChunkNotPresent((cx, cz))

        if sectorStart + numSectors > len(self.freeSectors):
            raise ChunkNotPresent((cx, cz))

        with self.file as f:
            f.seek(sectorStart * self.SECTOR_BYTES)
            data = f.read(numSectors * self.SECTOR_BYTES)
        if len(data) < 5:
            raise RegionMalformed, "Chunk data is only %d bytes long (expected 5)" % len(data)

        # log.debug("REGION LOAD {0},{1} sector {2}".format(cx, cz, sectorStart))

        length = struct.unpack_from(">I", data)[0]
        format = struct.unpack_from("B", data, 4)[0]
        data = data[5:length + 5]
        return data, format

    def readChunk(self, cx, cz):
        data, format = self._readChunk(cx, cz)
        if format == self.VERSION_GZIP:
            return nbt.gunzip(data)
        if format == self.VERSION_DEFLATE:
            return inflate(data)

        raise IOError("Unknown compress format: {0}".format(format))

    def copyChunkFrom(self, regionFile, cx, cz):
        """
        Silently fails if regionFile does not contain the requested chunk.
        """
        try:
            data, format = regionFile._readChunk(cx, cz)
            self._saveChunk(cx, cz, data, format)
        except ChunkNotPresent:
            pass

    def saveChunk(self, cx, cz, uncompressedData):
        data = deflate(uncompressedData)
        try:
            self._saveChunk(cx, cz, data, self.VERSION_DEFLATE)
        except ChunkTooBig as e:
            raise ChunkTooBig(e.message + " (%d uncompressed)" % len(uncompressedData))

    def _saveChunk(self, cx, cz, data, format):
        cx &= 0x1f
        cz &= 0x1f
        offset = self.getOffset(cx, cz)

        sectorNumber = offset >> 8
        sectorsAllocated = offset & 0xff
        sectorsNeeded = (len(data) + self.CHUNK_HEADER_SIZE) / self.SECTOR_BYTES + 1

        if sectorsNeeded >= 256:
            raise ChunkTooBig("Chunk too big! %d bytes exceeds 1MB" % len(data))

        if sectorNumber != 0 and sectorsAllocated >= sectorsNeeded:
            log.debug("REGION SAVE {0},{1} rewriting {2}b".format(cx, cz, len(data)))
            self.writeSector(sectorNumber, data, format)
        else:
            # we need to allocate new sectors

            # mark the sectors previously used for this chunk as free
            for i in xrange(sectorNumber, sectorNumber + sectorsAllocated):
                self.freeSectors[i] = True

            runLength = 0
            runStart = 0
            try:
                runStart = self.freeSectors.index(True)

                for i in range(runStart, len(self.freeSectors)):
                    if runLength:
                        if self.freeSectors[i]:
                            runLength += 1
                        else:
                            runLength = 0
                    elif self.freeSectors[i]:
                        runStart = i
                        runLength = 1

                    if runLength >= sectorsNeeded:
                        break
            except ValueError:
                pass

            # we found a free space large enough
            if runLength >= sectorsNeeded:
                log.debug("REGION SAVE {0},{1}, reusing {2}b".format(cx, cz, len(data)))
                sectorNumber = runStart
                self.setOffset(cx, cz, sectorNumber << 8 | sectorsNeeded)
                self.writeSector(sectorNumber, data, format)
                self.freeSectors[sectorNumber:sectorNumber + sectorsNeeded] = [False] * sectorsNeeded

            else:
                # no free space large enough found -- we need to grow the
                # file

                log.debug("REGION SAVE {0},{1}, growing by {2}b".format(cx, cz, len(data)))

                with self.file as f:
                    f.seek(0, 2)
                    filesize = f.tell()

                    sectorNumber = len(self.freeSectors)

                    assert sectorNumber * self.SECTOR_BYTES == filesize

                    filesize += sectorsNeeded * self.SECTOR_BYTES
                    f.truncate(filesize)

                self.freeSectors += [False] * sectorsNeeded

                self.setOffset(cx, cz, sectorNumber << 8 | sectorsNeeded)
                self.writeSector(sectorNumber, data, format)

        self.setTimestamp(cx, cz)

    def writeSector(self, sectorNumber, data, format):
        with self.file as f:
            log.debug("REGION: Writing sector {0}".format(sectorNumber))

            f.seek(sectorNumber * self.SECTOR_BYTES)
            f.write(struct.pack(">I", len(data) + 1))  # // chunk length
            f.write(struct.pack("B", format))  # // chunk version number
            f.write(data)  # // chunk data
            # f.flush()

    def containsChunk(self, cx, cz):
        return self.getOffset(cx, cz) != 0

    def getOffset(self, cx, cz):
        cx &= 0x1f
        cz &= 0x1f
        return self.offsets[cx + cz * 32]

    def setOffset(self, cx, cz, offset):
        cx &= 0x1f
        cz &= 0x1f
        self.offsets[cx + cz * 32] = offset
        with self.file as f:
            f.seek(0)
            f.write(self.offsets.tostring())

    def getTimestamp(self, cx, cz):
        cx &= 0x1f
        cz &= 0x1f
        return self.modTimes[cx + cz * 32]

    def setTimestamp(self, cx, cz, timestamp = None):
        if timestamp is None:
            timestamp = time.time()

        cx &= 0x1f
        cz &= 0x1f
        self.modTimes[cx + cz * 32] = timestamp
        with self.file as f:
            f.seek(self.SECTOR_BYTES)
            f.write(self.modTimes.tostring())

    SECTOR_BYTES = 4096
    SECTOR_INTS = SECTOR_BYTES / 4
    CHUNK_HEADER_SIZE = 5
    VERSION_GZIP = 1
    VERSION_DEFLATE = 2

    compressMode = VERSION_DEFLATE


class ChunkTooBig(ValueError):
    pass

########NEW FILE########
__FILENAME__ = run_regression_test
#!/usr/bin/env python

import tempfile
import sys
import subprocess
import shutil
import os
import hashlib
import contextlib
import gzip
import fnmatch
import tarfile
import zipfile


def generate_file_list(directory):
    for dirpath, dirnames, filenames in os.walk(directory):
        for filename in filenames:
            yield os.path.join(dirpath, filename)


def sha1_file(name, checksum=None):
    CHUNKSIZE = 1024
    if checksum is None:
        checksum = hashlib.sha1()
    if fnmatch.fnmatch(name, "*.dat"):
        opener = gzip.open
    else:
        opener = open

    with contextlib.closing(opener(name, 'rb')) as data:
        chunk = data.read(CHUNKSIZE)
        while len(chunk) == CHUNKSIZE:
            checksum.update(chunk)
            chunk = data.read(CHUNKSIZE)
        else:
            checksum.update(chunk)
    return checksum


def calculate_result(directory):
    checksum = hashlib.sha1()
    for filename in sorted(generate_file_list(directory)):
        if filename.endswith("session.lock"):
            continue
        sha1_file(filename, checksum)
    return checksum.hexdigest()


@contextlib.contextmanager
def temporary_directory(prefix='regr'):
    name = tempfile.mkdtemp(prefix)
    try:
        yield name
    finally:
        shutil.rmtree(name)


@contextlib.contextmanager
def directory_clone(src):
    with temporary_directory('regr') as name:
        subdir = os.path.join(name, "subdir")
        shutil.copytree(src, subdir)
        yield subdir


def launch_subprocess(directory, arguments, env=None):
    #my python breaks with an empty environ, i think it wants PATH
    #if sys.platform == "win32":
    if env is None:
        env = {}

    newenv = {}
    newenv.update(os.environ)
    newenv.update(env)

    proc = subprocess.Popen((["python.exe"] if sys.platform == "win32" else []) + [
            "./mce.py",
            directory] + arguments, stdin=subprocess.PIPE, stdout=subprocess.PIPE, env=newenv)

    return proc


class RegressionError(Exception):
    pass


def do_test(test_data, result_check, arguments=()):
    """Run a regression test on the given world.

    result_check - sha1 of the recursive tree generated
    arguments - arguments to give to mce.py on execution
    """
    result_check = result_check.lower()

    env = {
            'MCE_RANDOM_SEED': '42',
            'MCE_LAST_PLAYED': '42',
    }

    if 'MCE_PROFILE' in os.environ:
        env['MCE_PROFILE'] = os.environ['MCE_PROFILE']

    with directory_clone(test_data) as directory:
        proc = launch_subprocess(directory, arguments, env)
        proc.stdin.close()
        proc.wait()

        if proc.returncode:
            raise RegressionError("Program execution failed!")

        checksum = calculate_result(directory).lower()
        if checksum != result_check.lower():
            raise RegressionError("Checksum mismatch: {0!r} != {1!r}".format(checksum, result_check))
    print "[OK] (sha1sum of result is {0!r}, as expected)".format(result_check)


def do_test_match_output(test_data, result_check, arguments=()):
    result_check = result_check.lower()

    env = {
            'MCE_RANDOM_SEED': '42',
            'MCE_LAST_PLAYED': '42'
    }

    with directory_clone(test_data) as directory:
        proc = launch_subprocess(directory, arguments, env)
        proc.stdin.close()
        output = proc.stdout.read()
        proc.wait()

        if proc.returncode:
            raise RegressionError("Program execution failed!")

        print "Output\n{0}".format(output)

        checksum = hashlib.sha1()
        checksum.update(output)
        checksum = checksum.hexdigest()

        if checksum != result_check.lower():
            raise RegressionError("Checksum mismatch: {0!r} != {1!r}".format(checksum, result_check))

    print "[OK] (sha1sum of result is {0!r}, as expected)".format(result_check)


alpha_tests = [
    (do_test, 'baseline', '2bf250ec4e5dd8bfd73b3ccd0a5ff749569763cf', []),
    (do_test, 'degrief', '2b7eecd5e660f20415413707b4576b1234debfcb', ['degrief']),
    (do_test_match_output, 'analyze', '9cb4aec2ed7a895c3a5d20d6e29e26459e00bd53', ['analyze']),
    (do_test, 'relight', 'f3b3445b0abca1fe2b183bc48b24fb734dfca781', ['relight']),
    (do_test, 'replace', '4e816038f9851817b0d75df948d058143708d2ec', ['replace', 'Water (active)', 'with', 'Lava (active)']),
    (do_test, 'fill', '94566d069edece4ff0cc52ef2d8f877fbe9720ab', ['fill', 'Water (active)']),
    (do_test, 'heightmap', '71c20e7d7e335cb64b3eb0e9f6f4c9abaa09b070', ['heightmap', 'regression_test/mars.png']),
]

import optparse

parser = optparse.OptionParser()
parser.add_option("--profile", help="Perform profiling on regression tests", action="store_true")


def main(argv):
    options, args = parser.parse_args(argv)

    if len(args) <= 1:
        do_these_regressions = ['*']
    else:
        do_these_regressions = args[1:]

    with directory_clone("testfiles/AnvilWorld") as directory:
        test_data = directory
        passes = []
        fails = []

        for func, name, sha, args in alpha_tests:
            print "Starting regression {0} ({1})".format(name, args)

            if any(fnmatch.fnmatch(name, x) for x in do_these_regressions):
                if options.profile:
                    print >> sys.stderr, "Starting to profile to %s.profile" % name
                    os.environ['MCE_PROFILE'] = '%s.profile' % name
                try:
                    func(test_data, sha, args)
                except RegressionError, e:
                    fails.append("Regression {0} failed: {1}".format(name, e))
                    print fails[-1]
                else:
                    passes.append("Regression {0!r} complete.".format(name))
                    print passes[-1]

        print "{0} tests passed.".format(len(passes))
        for line in fails:
            print line


if __name__ == '__main__':
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = schematic
'''
Created on Jul 22, 2011

@author: Rio
'''
import atexit
from contextlib import closing
import os
import shutil
import zipfile
from logging import getLogger

import blockrotation
from box import BoundingBox
import infiniteworld
from level import MCLevel, EntityLevel
from materials import alphaMaterials, MCMaterials, namedMaterials
from mclevelbase import exhaust
import nbt
from numpy import array, swapaxes, uint8, zeros, resize

log = getLogger(__name__)

__all__ = ['MCSchematic', 'INVEditChest']


class MCSchematic (EntityLevel):
    materials = alphaMaterials

    def __init__(self, shape=None, root_tag=None, filename=None, mats='Alpha'):
        """ shape is (x,y,z) for a new level's shape.  if none, takes
        root_tag as a TAG_Compound for an existing schematic file.  if
        none, tries to read the tag from filename.  if none, results
        are undefined. materials can be a MCMaterials instance, or one of
        "Classic", "Alpha", "Pocket" to indicate allowable blocks. The default
        is Alpha.

        block coordinate order in the file is y,z,x to use the same code as classic/indev levels.
        in hindsight, this was a completely arbitrary decision.

        the Entities and TileEntities are nbt.TAG_List objects containing TAG_Compounds.
        this makes it easy to copy entities without knowing about their insides.

        rotateLeft swaps the axes of the different arrays.  because of this, the Width, Height, and Length
        reflect the current dimensions of the schematic rather than the ones specified in the NBT structure.
        I'm not sure what happens when I try to re-save a rotated schematic.
        """

        if filename:
            self.filename = filename
            if None is root_tag and os.path.exists(filename):
                root_tag = nbt.load(filename)
        else:
            self.filename = None

        if mats in namedMaterials:
            self.materials = namedMaterials[mats]
        else:
            assert(isinstance(mats, MCMaterials))
            self.materials = mats

        if root_tag:
            self.root_tag = root_tag
            if "Materials" in root_tag:
                self.materials = namedMaterials[self.Materials]
            else:
                root_tag["Materials"] = nbt.TAG_String(self.materials.name)

            w = self.root_tag["Width"].value
            l = self.root_tag["Length"].value
            h = self.root_tag["Height"].value

            self._Blocks = self.root_tag["Blocks"].value.astype('uint16').reshape(h, l, w) # _Blocks is y, z, x
            del self.root_tag["Blocks"]
            if "AddBlocks" in self.root_tag:
                # Use WorldEdit's "AddBlocks" array to load and store the 4 high bits of a block ID.
                # Unlike Minecraft's NibbleArrays, this array stores the first block's bits in the
                # 4 high bits of the first byte.

                size = (h * l * w)

                # If odd, add one to the size to make sure the adjacent slices line up.
                add = zeros(size + (size & 1), 'uint16')

                # Fill the even bytes with data
                add[::2] = self.root_tag["AddBlocks"].value

                # Copy the low 4 bits to the odd bytes
                add[1::2] = add[::2] & 0xf

                # Shift the even bytes down
                add[::2] >>= 4

                # Shift every byte up before merging it with Blocks
                add <<= 8
                self._Blocks |= add[:size].reshape(h, l, w)
                del self.root_tag["AddBlocks"]

            self.root_tag["Data"].value = self.root_tag["Data"].value.reshape(h, l, w)

            if "Biomes" in self.root_tag:
                self.root_tag["Biomes"].value.shape = (l, w)

        else:
            assert shape is not None
            root_tag = nbt.TAG_Compound(name="Schematic")
            root_tag["Height"] = nbt.TAG_Short(shape[1])
            root_tag["Length"] = nbt.TAG_Short(shape[2])
            root_tag["Width"] = nbt.TAG_Short(shape[0])

            root_tag["Entities"] = nbt.TAG_List()
            root_tag["TileEntities"] = nbt.TAG_List()
            root_tag["Materials"] = nbt.TAG_String(self.materials.name)

            self._Blocks = zeros((shape[1], shape[2], shape[0]), 'uint16')
            root_tag["Data"] = nbt.TAG_Byte_Array(zeros((shape[1], shape[2], shape[0]), uint8))

            root_tag["Biomes"] = nbt.TAG_Byte_Array(zeros((shape[2], shape[0]), uint8))

            self.root_tag = root_tag

        self.root_tag["Data"].value &= 0xF  # discard high bits


    def saveToFile(self, filename=None):
        """ save to file named filename, or use self.filename.  XXX NOT THREAD SAFE AT ALL. """
        if filename is None:
            filename = self.filename
        if filename is None:
            raise IOError, u"Attempted to save an unnamed schematic in place"

        self.Materials = self.materials.name

        self.root_tag["Blocks"] = nbt.TAG_Byte_Array(self._Blocks.astype('uint8'))

        add = self._Blocks >> 8
        if add.any():
            # WorldEdit AddBlocks compatibility.
            # The first 4-bit value is stored in the high bits of the first byte.

            # Increase odd size by one to align slices.
            packed_add = zeros(add.size + (add.size & 1), 'uint8')
            packed_add[:add.size] = add.ravel()

            # Shift even bytes to the left
            packed_add[::2] <<= 4

            # Merge odd bytes into even bytes
            packed_add[::2] |= packed_add[1::2]

            # Save only the even bytes, now that they contain the odd bytes in their lower bits.
            packed_add = packed_add[0::2]
            self.root_tag["AddBlocks"] = nbt.TAG_Byte_Array(packed_add)

        with open(filename, 'wb') as chunkfh:
            self.root_tag.save(chunkfh)

        del self.root_tag["Blocks"]
        self.root_tag.pop("AddBlocks", None)


    def __str__(self):
        return u"MCSchematic(shape={0}, materials={2}, filename=\"{1}\")".format(self.size, self.filename or u"", self.Materials)

    # these refer to the blocks array instead of the file's height because rotation swaps the axes
    # this will have an impact later on when editing schematics instead of just importing/exporting
    @property
    def Length(self):
        return self.Blocks.shape[1]

    @property
    def Width(self):
        return self.Blocks.shape[0]

    @property
    def Height(self):
        return self.Blocks.shape[2]

    @property
    def Blocks(self):
        return swapaxes(self._Blocks, 0, 2)

    @property
    def Data(self):
        return swapaxes(self.root_tag["Data"].value, 0, 2)

    @property
    def Entities(self):
        return self.root_tag["Entities"]

    @property
    def TileEntities(self):
        return self.root_tag["TileEntities"]

    @property
    def Materials(self):
        return self.root_tag["Materials"].value

    @Materials.setter
    def Materials(self, val):
        if "Materials" not in self.root_tag:
            self.root_tag["Materials"] = nbt.TAG_String()
        self.root_tag["Materials"].value = val

    @property
    def Biomes(self):
        return swapaxes(self.root_tag["Biomes"].value, 0, 1)

    @classmethod
    def _isTagLevel(cls, root_tag):
        return "Schematic" == root_tag.name

    def _update_shape(self):
        root_tag = self.root_tag
        shape = self.Blocks.shape
        root_tag["Height"] = nbt.TAG_Short(shape[2])
        root_tag["Length"] = nbt.TAG_Short(shape[1])
        root_tag["Width"] = nbt.TAG_Short(shape[0])


    def rotateLeft(self):
        self._fakeEntities = None
        self._Blocks = swapaxes(self._Blocks, 1, 2)[:, ::-1, :]  # x=z; z=-x
        if "Biomes" in self.root_tag:
            self.root_tag["Biomes"].value = swapaxes(self.root_tag["Biomes"].value, 0, 1)[::-1, :]

        self.root_tag["Data"].value   = swapaxes(self.root_tag["Data"].value, 1, 2)[:, ::-1, :]  # x=z; z=-x
        self._update_shape()

        blockrotation.RotateLeft(self.Blocks, self.Data)

        log.info(u"Relocating entities...")
        for entity in self.Entities:
            for p in "Pos", "Motion":
                if p == "Pos":
                    zBase = self.Length
                else:
                    zBase = 0.0
                newX = entity[p][2].value
                newZ = zBase - entity[p][0].value

                entity[p][0].value = newX
                entity[p][2].value = newZ
            entity["Rotation"][0].value -= 90.0
            if entity["id"].value in ("Painting", "ItemFrame"):
                x, z = entity["TileX"].value, entity["TileZ"].value
                newx = z
                newz = self.Length - x - 1

                entity["TileX"].value, entity["TileZ"].value = newx, newz
                entity["Dir"].value = (entity["Dir"].value + 1) % 4

        for tileEntity in self.TileEntities:
            if not 'x' in tileEntity:
                continue

            newX = tileEntity["z"].value
            newZ = self.Length - tileEntity["x"].value - 1

            tileEntity["x"].value = newX
            tileEntity["z"].value = newZ

    def roll(self):
        " xxx rotate stuff - destroys biomes"
        self.root_tag.pop('Biomes', None)
        self._fakeEntities = None

        self._Blocks = swapaxes(self._Blocks, 2, 0)[:, :, ::-1]  # x=y; y=-x
        self.root_tag["Data"].value = swapaxes(self.root_tag["Data"].value, 2, 0)[:, :, ::-1]
        self._update_shape()

    def flipVertical(self):
        " xxx delete stuff "
        self._fakeEntities = None

        blockrotation.FlipVertical(self.Blocks, self.Data)
        self._Blocks = self._Blocks[::-1, :, :]  # y=-y
        self.root_tag["Data"].value = self.root_tag["Data"].value[::-1, :, :]

    def flipNorthSouth(self):
        if "Biomes" in self.root_tag:
            self.root_tag["Biomes"].value = self.root_tag["Biomes"].value[::-1, :]

        self._fakeEntities = None

        blockrotation.FlipNorthSouth(self.Blocks, self.Data)
        self._Blocks = self._Blocks[:, :, ::-1]  # x=-x
        self.root_tag["Data"].value = self.root_tag["Data"].value[:, :, ::-1]

        northSouthPaintingMap = [0, 3, 2, 1]

        log.info(u"N/S Flip: Relocating entities...")
        for entity in self.Entities:

            entity["Pos"][0].value = self.Width - entity["Pos"][0].value
            entity["Motion"][0].value = -entity["Motion"][0].value

            entity["Rotation"][0].value -= 180.0

            if entity["id"].value in ("Painting", "ItemFrame"):
                entity["TileX"].value = self.Width - entity["TileX"].value
                entity["Dir"].value = northSouthPaintingMap[entity["Dir"].value]

        for tileEntity in self.TileEntities:
            if not 'x' in tileEntity:
                continue

            tileEntity["x"].value = self.Width - tileEntity["x"].value - 1

    def flipEastWest(self):
        if "Biomes" in self.root_tag:
            self.root_tag["Biomes"].value = self.root_tag["Biomes"].value[:, ::-1]

        self._fakeEntities = None

        blockrotation.FlipEastWest(self.Blocks, self.Data)
        self._Blocks = self._Blocks[:, ::-1, :]  # z=-z
        self.root_tag["Data"].value = self.root_tag["Data"].value[:, ::-1, :]

        eastWestPaintingMap = [2, 1, 0, 3]

        log.info(u"E/W Flip: Relocating entities...")
        for entity in self.Entities:

            entity["Pos"][2].value = self.Length - entity["Pos"][2].value
            entity["Motion"][2].value = -entity["Motion"][2].value

            entity["Rotation"][0].value -= 180.0

            if entity["id"].value in ("Painting", "ItemFrame"):
                entity["TileZ"].value = self.Length - entity["TileZ"].value
                entity["Dir"].value = eastWestPaintingMap[entity["Dir"].value]

        for tileEntity in self.TileEntities:
            tileEntity["z"].value = self.Length - tileEntity["z"].value - 1


    def setBlockDataAt(self, x, y, z, newdata):
        if x < 0 or y < 0 or z < 0:
            return 0
        if x >= self.Width or y >= self.Height or z >= self.Length:
            return 0
        self.Data[x, z, y] = (newdata & 0xf)

    def blockDataAt(self, x, y, z):
        if x < 0 or y < 0 or z < 0:
            return 0
        if x >= self.Width or y >= self.Height or z >= self.Length:
            return 0
        return self.Data[x, z, y]

    @classmethod
    def chestWithItemID(cls, itemID, count=64, damage=0):
        """ Creates a chest with a stack of 'itemID' in each slot.
        Optionally specify the count of items in each stack. Pass a negative
        value for damage to create unnaturally sturdy tools. """
        root_tag = nbt.TAG_Compound()
        invTag = nbt.TAG_List()
        root_tag["Inventory"] = invTag
        for slot in range(9, 36):
            itemTag = nbt.TAG_Compound()
            itemTag["Slot"] = nbt.TAG_Byte(slot)
            itemTag["Count"] = nbt.TAG_Byte(count)
            itemTag["id"] = nbt.TAG_Short(itemID)
            itemTag["Damage"] = nbt.TAG_Short(damage)
            invTag.append(itemTag)

        chest = INVEditChest(root_tag, "")

        return chest


    def getChunk(self, cx, cz):
        chunk = super(MCSchematic, self).getChunk(cx, cz)
        if "Biomes" in self.root_tag:
            x = cx << 4
            z = cz << 4
            chunk.Biomes = self.Biomes[x:x + 16, z:z + 16]
        return chunk


class INVEditChest(MCSchematic):
    Width = 1
    Height = 1
    Length = 1
    Blocks = array([[[alphaMaterials.Chest.ID]]], 'uint8')
    Data = array([[[0]]], 'uint8')
    Entities = nbt.TAG_List()
    Materials = alphaMaterials

    @classmethod
    def _isTagLevel(cls, root_tag):
        return "Inventory" in root_tag

    def __init__(self, root_tag, filename):

        if filename:
            self.filename = filename
            if None is root_tag:
                try:
                    root_tag = nbt.load(filename)
                except IOError, e:
                    log.info(u"Failed to load file {0}".format(e))
                    raise
        else:
            assert root_tag, "Must have either root_tag or filename"
            self.filename = None

        for item in list(root_tag["Inventory"]):
            slot = item["Slot"].value
            if slot < 9 or slot >= 36:
                root_tag["Inventory"].remove(item)
            else:
                item["Slot"].value -= 9  # adjust for different chest slot indexes

        self.root_tag = root_tag

    @property
    def TileEntities(self):
        chestTag = nbt.TAG_Compound()
        chestTag["id"] = nbt.TAG_String("Chest")
        chestTag["Items"] = nbt.TAG_List(self.root_tag["Inventory"])
        chestTag["x"] = nbt.TAG_Int(0)
        chestTag["y"] = nbt.TAG_Int(0)
        chestTag["z"] = nbt.TAG_Int(0)

        return nbt.TAG_List([chestTag], name="TileEntities")


class ZipSchematic (infiniteworld.MCInfdevOldLevel):
    def __init__(self, filename, create=False):
        self.zipfilename = filename

        tempdir = tempfile.mktemp("schematic")
        if create is False:
            zf = zipfile.ZipFile(filename)
            zf.extractall(tempdir)
            zf.close()

        super(ZipSchematic, self).__init__(tempdir, create)
        atexit.register(shutil.rmtree, self.worldFolder.filename, True)


        try:
            schematicDat = nbt.load(self.worldFolder.getFilePath("schematic.dat"))

            self.Width = schematicDat['Width'].value
            self.Height = schematicDat['Height'].value
            self.Length = schematicDat['Length'].value

            if "Materials" in schematicDat:
                self.materials = namedMaterials[schematicDat["Materials"].value]

        except Exception, e:
            print "Exception reading schematic.dat, skipping: {0!r}".format(e)
            self.Width = 0
            self.Length = 0

    def __del__(self):
        shutil.rmtree(self.worldFolder.filename, True)

    def saveInPlace(self):
        self.saveToFile(self.zipfilename)

    def saveToFile(self, filename):
        super(ZipSchematic, self).saveInPlace()
        schematicDat = nbt.TAG_Compound()
        schematicDat.name = "Mega Schematic"

        schematicDat["Width"] = nbt.TAG_Int(self.size[0])
        schematicDat["Height"] = nbt.TAG_Int(self.size[1])
        schematicDat["Length"] = nbt.TAG_Int(self.size[2])
        schematicDat["Materials"] = nbt.TAG_String(self.materials.name)

        schematicDat.save(self.worldFolder.getFilePath("schematic.dat"))

        basedir = self.worldFolder.filename
        assert os.path.isdir(basedir)
        with closing(zipfile.ZipFile(filename, "w", zipfile.ZIP_STORED)) as z:
            for root, dirs, files in os.walk(basedir):
                # NOTE: ignore empty directories
                for fn in files:
                    absfn = os.path.join(root, fn)
                    zfn = absfn[len(basedir) + len(os.sep):]  # XXX: relative path
                    z.write(absfn, zfn)

    def getWorldBounds(self):
        return BoundingBox((0, 0, 0), (self.Width, self.Height, self.Length))

    @classmethod
    def _isLevel(cls, filename):
        return zipfile.is_zipfile(filename)




def adjustExtractionParameters(self, box):
    x, y, z = box.origin
    w, h, l = box.size
    destX = destY = destZ = 0

    if y < 0:
        destY -= y
        h += y
        y = 0

    if y >= self.Height:
        return

    if y + h >= self.Height:
        h -= y + h - self.Height
        y = self.Height - h

    if h <= 0:
        return

    if self.Width:
        if x < 0:
            w += x
            destX -= x
            x = 0
        if x >= self.Width:
            return

        if x + w >= self.Width:
            w = self.Width - x

        if w <= 0:
            return

        if z < 0:
            l += z
            destZ -= z
            z = 0

        if z >= self.Length:
            return

        if z + l >= self.Length:
            l = self.Length - z

        if l <= 0:
            return

    box = BoundingBox((x, y, z), (w, h, l))

    return box, (destX, destY, destZ)


def extractSchematicFrom(sourceLevel, box, entities=True):
    return exhaust(extractSchematicFromIter(sourceLevel, box, entities))


def extractSchematicFromIter(sourceLevel, box, entities=True):
    p = sourceLevel.adjustExtractionParameters(box)
    if p is None:
        yield None
        return
    newbox, destPoint = p

    tempSchematic = MCSchematic(shape=box.size, mats=sourceLevel.materials)
    for i in tempSchematic.copyBlocksFromIter(sourceLevel, newbox, destPoint, entities=entities, biomes=True):
        yield i

    yield tempSchematic

MCLevel.extractSchematic = extractSchematicFrom
MCLevel.extractSchematicIter = extractSchematicFromIter
MCLevel.adjustExtractionParameters = adjustExtractionParameters

import tempfile


def extractZipSchematicFrom(sourceLevel, box, zipfilename=None, entities=True):
    return exhaust(extractZipSchematicFromIter(sourceLevel, box, zipfilename, entities))


def extractZipSchematicFromIter(sourceLevel, box, zipfilename=None, entities=True):
    # converts classic blocks to alpha
    # probably should only apply to alpha levels

    if zipfilename is None:
        zipfilename = tempfile.mktemp("zipschematic.zip")
    atexit.register(shutil.rmtree, zipfilename, True)

    p = sourceLevel.adjustExtractionParameters(box)
    if p is None:
        return
    sourceBox, destPoint = p

    destPoint = (0, 0, 0)

    tempSchematic = ZipSchematic(zipfilename, create=True)
    tempSchematic.materials = sourceLevel.materials

    for i in tempSchematic.copyBlocksFromIter(sourceLevel, sourceBox, destPoint, entities=entities, create=True, biomes=True):
        yield i

    tempSchematic.Width, tempSchematic.Height, tempSchematic.Length = sourceBox.size
    tempSchematic.saveInPlace()  # lights not needed for this format - crashes minecraft though
    yield tempSchematic

MCLevel.extractZipSchematic = extractZipSchematicFrom
MCLevel.extractZipSchematicIter = extractZipSchematicFromIter


def extractAnySchematic(level, box):
    return exhaust(level.extractAnySchematicIter(box))


def extractAnySchematicIter(level, box):
    if box.chunkCount < infiniteworld.MCInfdevOldLevel.loadedChunkLimit:
        for i in level.extractSchematicIter(box):
            yield i
    else:
        for i in level.extractZipSchematicIter(box):
            yield i

MCLevel.extractAnySchematic = extractAnySchematic
MCLevel.extractAnySchematicIter = extractAnySchematicIter


########NEW FILE########
__FILENAME__ = anvil_test
import itertools
import os
import shutil
import unittest
import numpy

from pymclevel import mclevel
from pymclevel.infiniteworld import MCInfdevOldLevel
from pymclevel import nbt
from pymclevel.schematic import MCSchematic
from pymclevel.box import BoundingBox
from pymclevel import block_copy
from templevel import mktemp, TempLevel

__author__ = 'Rio'

class TestAnvilLevelCreate(unittest.TestCase):
    def testCreate(self):
        temppath = mktemp("AnvilCreate")
        self.anvilLevel = MCInfdevOldLevel(filename=temppath, create=True)
        self.anvilLevel.close()
        shutil.rmtree(temppath)


class TestAnvilLevel(unittest.TestCase):
    def setUp(self):
        self.indevLevel = TempLevel("hell.mclevel")
        self.anvilLevel = TempLevel("AnvilWorld")

    def testUnsetProperties(self):
        level = self.anvilLevel.level
        del level.root_tag['Data']['LastPlayed']
        import time
        assert 0 != level.LastPlayed
        level.LastPlayed = time.time() * 1000 - 1000000

    def testGetEntities(self):
        level = self.anvilLevel.level
        print len(level.getEntitiesInBox(level.bounds))

    def testCreateChunks(self):
        level = self.anvilLevel.level

        for ch in list(level.allChunks):
            level.deleteChunk(*ch)
        level.createChunksInBox(BoundingBox((0, 0, 0), (32, 0, 32)))

    def testCopyChunks(self):
        level = self.anvilLevel.level
        temppath = mktemp("AnvilCreate")
        newLevel = MCInfdevOldLevel(filename=temppath, create=True)
        for cx, cz in level.allChunks:
            newLevel.copyChunkFrom(level, cx, cz)

        newLevel.close()
        shutil.rmtree(temppath)

    def testCopyConvertBlocks(self):
        indevlevel = self.indevLevel.level
        level = self.anvilLevel.level
        x, y, z = level.bounds.origin
        x += level.bounds.size[0]/2 & ~15
        z += level.bounds.size[2]/2 & ~15
        x -= indevlevel.Width / 2
        z -= indevlevel.Height / 2

        middle = (x, y, z)

        oldEntityCount = len(level.getEntitiesInBox(BoundingBox(middle, indevlevel.bounds.size)))
        level.copyBlocksFrom(indevlevel, indevlevel.bounds, middle)

        convertedSourceBlocks, convertedSourceData = block_copy.convertBlocks(indevlevel, level, indevlevel.Blocks[0:16, 0:16, 0:indevlevel.Height], indevlevel.Data[0:16, 0:16, 0:indevlevel.Height])

        assert ((level.getChunk(x >> 4, z >> 4).Blocks[0:16, 0:16, 0:indevlevel.Height]
                == convertedSourceBlocks).all())

        assert (oldEntityCount + len(indevlevel.getEntitiesInBox(indevlevel.bounds))
                == len(level.getEntitiesInBox(BoundingBox(middle, indevlevel.bounds.size))))

    def testImportSchematic(self):
        level = self.anvilLevel.level
        cx, cz = level.allChunks.next()

        schem = mclevel.fromFile("schematics/CreativeInABox.schematic")
        box = BoundingBox((cx * 16, 64, cz * 16), schem.bounds.size)
        level.copyBlocksFrom(schem, schem.bounds, (0, 64, 0))
        schem = MCSchematic(shape=schem.bounds.size)
        schem.copyBlocksFrom(level, box, (0, 0, 0))
        convertedSourceBlocks, convertedSourceData = block_copy.convertBlocks(schem, level, schem.Blocks, schem.Data)
        assert (level.getChunk(cx, cz).Blocks[0:1, 0:3, 64:65] == convertedSourceBlocks).all()

    def testRecreateChunks(self):
        level = self.anvilLevel.level

        for x, z in itertools.product(xrange(-1, 3), xrange(-1, 2)):
            level.deleteChunk(x, z)
            assert not level.containsChunk(x, z)
            level.createChunk(x, z)

    def testFill(self):
        level = self.anvilLevel.level
        cx, cz = level.allChunks.next()
        box = BoundingBox((cx * 16, 0, cz * 16), (32, level.Height, 32))
        level.fillBlocks(box, level.materials.WoodPlanks)
        level.fillBlocks(box, level.materials.WoodPlanks, [level.materials.Stone])
        level.saveInPlace()
        c = level.getChunk(cx, cz)

        assert (c.Blocks == 5).all()

    def testReplace(self):
        level = self.anvilLevel.level

        level.fillBlocks(BoundingBox((-11, 0, -7), (38, level.Height, 25)), level.materials.WoodPlanks, [level.materials.Dirt, level.materials.Grass])

    def testSaveRelight(self):
        indevlevel = self.indevLevel.level
        level = self.anvilLevel.level

        cx, cz = -3, -1

        level.deleteChunk(cx, cz)

        level.createChunk(cx, cz)
        level.copyBlocksFrom(indevlevel, BoundingBox((0, 0, 0), (32, 64, 32,)), level.bounds.origin)

        level.generateLights()
        level.saveInPlace()

    def testRecompress(self):
        level = self.anvilLevel.level
        cx, cz = level.allChunks.next()

        ch = level.getChunk(cx, cz)
        ch.dirty = True
        ch.Blocks[:] = 6
        ch.Data[:] = 13
        d = {}
        keys = 'Blocks Data SkyLight BlockLight'.split()
        for key in keys:
            d[key] = numpy.array(getattr(ch, key))

        for i in range(5):
            level.saveInPlace()
            ch = level.getChunk(cx, cz)
            ch.dirty = True
            assert (ch.Data == 13).all()
            for key in keys:
                assert (d[key] == getattr(ch, key)).all()

    def testPlayerSpawn(self):
        level = self.anvilLevel.level

        level.setPlayerSpawnPosition((0, 64, 0), "Player")
        level.getPlayerPosition()
        assert len(level.players) != 0

    def testBigEndianIntHeightMap(self):
        """ Test modifying, saving, and loading the new TAG_Int_Array heightmap
        added with the Anvil format.
        """
        chunk = nbt.load("testfiles/AnvilChunk.dat")

        hm = chunk["Level"]["HeightMap"]
        hm.value[2] = 500
        oldhm = numpy.array(hm.value)

        filename = mktemp("ChangedChunk")
        chunk.save(filename)
        changedChunk = nbt.load(filename)
        os.unlink(filename)

        eq = (changedChunk["Level"]["HeightMap"].value == oldhm)
        assert eq.all()

########NEW FILE########
__FILENAME__ = entity_test
from pymclevel import fromFile
from templevel import TempLevel

__author__ = 'Rio'

def test_command_block():
    level = TempLevel("AnvilWorld").level

    cmdblock = fromFile("testfiles/Commandblock.schematic")

    point = level.bounds.origin + [p/2 for p in level.bounds.size]
    level.copyBlocksFrom(cmdblock, cmdblock.bounds, point)

    te = level.tileEntityAt(*point)
    command = te['Command'].value
    words = command.split(' ')
    x, y, z = words[2:5]
    assert x == str(point[0])
    assert y == str(point[1] + 10)
    assert z == str(point[2])

########NEW FILE########
__FILENAME__ = extended_id_test
from pymclevel import BoundingBox
from pymclevel.schematic import MCSchematic
from pymclevel import MCInfdevOldLevel
from templevel import TempLevel

__author__ = 'Rio'

def test_schematic_extended_ids():
    s = MCSchematic(shape=(1, 1, 5))
    s.Blocks[0,0,0] = 2048
    temp = TempLevel("schematic", createFunc=s.saveToFile)
    s = temp.level
    assert s.Blocks[0,0,0] == 2048

def alpha_test_level():
    temp = TempLevel("alpha", createFunc=lambda f: MCInfdevOldLevel(f, create=True))
    level = temp.level
    level.createChunk(0, 0)

    for x in range(0, 10):
        level.setBlockAt(x, 2, 5, 2048)

    level.saveInPlace()
    level.close()

    level = MCInfdevOldLevel(filename=level.filename)
    return level

def testExport():
    level = alpha_test_level()

    for size in [(16, 16, 16),
                 (15, 16, 16),
                 (15, 16, 15),
                 (15, 15, 15),
                 ]:
        schem = level.extractSchematic(BoundingBox((0, 0, 0), size))
        schem = TempLevel("schem", createFunc=lambda f: schem.saveToFile(f)).level
        assert (schem.Blocks > 255).any()

def testAlphaIDs():
    level = alpha_test_level()
    assert level.blockAt(0,2,5) == 2048


########NEW FILE########
__FILENAME__ = indev_test
import unittest
from templevel import TempLevel

from pymclevel.box import BoundingBox
from pymclevel.entity import Entity, TileEntity


__author__ = 'Rio'

class TestIndevLevel(unittest.TestCase):
    def setUp(self):
        self.srclevel = TempLevel("hell.mclevel")
        self.indevlevel = TempLevel("hueg.mclevel")

    def testEntities(self):
        level = self.indevlevel.level
        entityTag = Entity.Create("Zombie")
        tileEntityTag = TileEntity.Create("Painting")
        level.addEntity(entityTag)
        level.addTileEntity(tileEntityTag)
        schem = level.extractSchematic(level.bounds)
        level.copyBlocksFrom(schem, schem.bounds, (0, 0, 0))

        # raise Failure

    def testCopy(self):
        indevlevel = self.indevlevel.level
        srclevel = self.srclevel.level
        indevlevel.copyBlocksFrom(srclevel, BoundingBox((0, 0, 0), (64, 64, 64,)), (0, 0, 0))
        assert((indevlevel.Blocks[0:64, 0:64, 0:64] == srclevel.Blocks[0:64, 0:64, 0:64]).all())

    def testFill(self):
        indevlevel = self.indevlevel.level
        indevlevel.fillBlocks(BoundingBox((0, 0, 0), (64, 64, 64,)), indevlevel.materials.Sand, [indevlevel.materials.Stone, indevlevel.materials.Dirt])
        indevlevel.saveInPlace()

########NEW FILE########
__FILENAME__ = java_test
import unittest
import numpy
from templevel import TempLevel
from pymclevel.box import BoundingBox

__author__ = 'Rio'

class TestJavaLevel(unittest.TestCase):
    def setUp(self):
        self.creativelevel = TempLevel("Dojo_64_64_128.dat")
        self.indevlevel = TempLevel("hell.mclevel")

    def testCopy(self):
        indevlevel = self.indevlevel.level
        creativelevel = self.creativelevel.level

        creativelevel.copyBlocksFrom(indevlevel, BoundingBox((0, 0, 0), (64, 64, 64,)), (0, 0, 0))
        assert(numpy.array((indevlevel.Blocks[0:64, 0:64, 0:64]) == (creativelevel.Blocks[0:64, 0:64, 0:64])).all())

        creativelevel.saveInPlace()
        # xxx old survival levels

########NEW FILE########
__FILENAME__ = mcr_test
import anvil_test
from templevel import TempLevel

__author__ = 'Rio'

class TestMCR(anvil_test.TestAnvilLevel):
    def setUp(self):
        self.indevLevel = TempLevel("hell.mclevel")
        self.anvilLevel = TempLevel("PyTestWorld")


########NEW FILE########
__FILENAME__ = nbt_test
from cStringIO import StringIO
import os
from os.path import join
import time
import unittest
import numpy
from pymclevel import nbt
from templevel import TempLevel

__author__ = 'Rio'

class TestNBT():

    def testLoad(self):
        "Load an indev level."
        level = nbt.load("testfiles/hell.mclevel")

        # The root tag must have a name, and so must any tag within a TAG_Compound
        print level.name

        # Use the [] operator to look up subtags of a TAG_Compound.
        print level["Environment"]["SurroundingGroundHeight"].value

        # Numeric, string, and bytearray types have a value that can be accessed and changed.
        print level["Map"]["Blocks"].value

        return level

    def testLoadUncompressed(self):
        root_tag = nbt.load("testfiles/uncompressed.nbt")

    def testLoadNBTExplorer(self):
        root_tag = nbt.load("testfiles/modified_by_nbtexplorer.dat")

    def testCreate(self):
        "Create an indev level."

        # The root of an NBT file is always a TAG_Compound.
        level = nbt.TAG_Compound(name="MinecraftLevel")

        # Subtags of a TAG_Compound are automatically named when you use the [] operator.
        level["About"] = nbt.TAG_Compound()
        level["About"]["Author"] = nbt.TAG_String("codewarrior")
        level["About"]["CreatedOn"] = nbt.TAG_Long(time.time())

        level["Environment"] = nbt.TAG_Compound()
        level["Environment"]["SkyBrightness"] = nbt.TAG_Byte(16)
        level["Environment"]["SurroundingWaterHeight"] = nbt.TAG_Short(32)
        level["Environment"]["FogColor"] = nbt.TAG_Int(0xcccccc)

        entity = nbt.TAG_Compound()
        entity["id"] = nbt.TAG_String("Creeper")
        entity["Pos"] = nbt.TAG_List([nbt.TAG_Float(d) for d in (32.5, 64.0, 33.3)])

        level["Entities"] = nbt.TAG_List([entity])

        # You can also create and name a tag before adding it to the compound.
        spawn = nbt.TAG_List((nbt.TAG_Short(100), nbt.TAG_Short(45), nbt.TAG_Short(55)))
        spawn.name = "Spawn"

        mapTag = nbt.TAG_Compound()
        mapTag.add(spawn)
        mapTag.name = "Map"
        level.add(mapTag)

        mapTag2 = nbt.TAG_Compound([spawn])
        mapTag2.name = "Map"

        # I think it looks more familiar with [] syntax.

        l, w, h = 128, 128, 128
        mapTag["Height"] = nbt.TAG_Short(h)  # y dimension
        mapTag["Length"] = nbt.TAG_Short(l)  # z dimension
        mapTag["Width"] = nbt.TAG_Short(w)  # x dimension

        # Byte arrays are stored as numpy.uint8 arrays.

        mapTag["Blocks"] = nbt.TAG_Byte_Array()
        mapTag["Blocks"].value = numpy.zeros(l * w * h, dtype=numpy.uint8)  # create lots of air!

        # The blocks array is indexed (y,z,x) for indev levels, so reshape the blocks
        mapTag["Blocks"].value.shape = (h, l, w)

        # Replace the bottom layer of the indev level with wood
        mapTag["Blocks"].value[0, :, :] = 5

        # This is a great way to learn the power of numpy array slicing and indexing.

        mapTag["Data"] = nbt.TAG_Byte_Array()
        mapTag["Data"].value = numpy.zeros(l * w * h, dtype=numpy.uint8)

        # Save a few more tag types for completeness

        level["ShortArray"] = nbt.TAG_Short_Array(numpy.zeros((16, 16), dtype='uint16'))
        level["IntArray"] = nbt.TAG_Int_Array(numpy.zeros((16, 16), dtype='uint32'))
        level["Float"] = nbt.TAG_Float(0.3)

        return level

    def testToStrings(self):
        level = self.testCreate()
        repr(level)
        repr(level["Map"]["Blocks"])
        repr(level["Entities"])

        str(level)

    def testModify(self):
        level = self.testCreate()

        # Most of the value types work as expected. Here, we replace the entire tag with a TAG_String
        level["About"]["Author"] = nbt.TAG_String("YARRR~!")

        # Because the tag type usually doesn't change,
        # we can replace the string tag's value instead of replacing the entire tag.
        level["About"]["Author"].value = "Stew Pickles"

        # Remove members of a TAG_Compound using del, similar to a python dict.
        del(level["About"])

        # Replace all of the wood blocks with gold using a boolean index array
        blocks = level["Map"]["Blocks"].value
        blocks[blocks == 5] = 41

        level["Entities"][0] = nbt.TAG_Compound([nbt.TAG_String("Creeper", "id"),
                                                 nbt.TAG_List([nbt.TAG_Double(d) for d in (1, 1, 1)], "Pos")])

    def testMultipleCompound(self):
        """ According to rumor, some TAG_Compounds store several tags with the same name. Once I find a chunk file
        with such a compound, I need to test TAG_Compound.get_all()"""

        pass

    def testSave(self):

        level = self.testCreate()
        level["Environment"]["SurroundingWaterHeight"].value += 6

        # Save the entire TAG structure to a different file.
        TempLevel("atlantis.mclevel", createFunc=level.save) #xxx don't use templevel here


    def testList(self):
        tag = nbt.TAG_List()
        tag.append(nbt.TAG_Int(258))
        del tag[0]

    def testErrors(self):
        """
        attempt to name elements of a TAG_List
        named list elements are not allowed by the NBT spec,
        so we must discard any names when writing a list.
        """

        level = self.testCreate()
        level["Map"]["Spawn"][0].name = "Torg Potter"
        data = level.save()
        newlevel = nbt.load(buf=data)

        n = newlevel["Map"]["Spawn"][0].name
        if n:
            print "Named list element failed: %s" % n

        # attempt to delete non-existent TAG_Compound elements
        # this generates a KeyError like a python dict does.
        level = self.testCreate()
        try:
            del level["DEADBEEF"]
        except KeyError:
            pass
        else:
            assert False

    def testSpeed(self):
        d = join("testfiles", "TileTicks_chunks")
        files = [join(d, f) for f in os.listdir(d)]
        startTime = time.time()
        for f in files[:40]:
            n = nbt.load(f)
        duration = time.time() - startTime

        assert duration < 1.0 # Will fail when not using _nbt.pyx


########NEW FILE########
__FILENAME__ = pocket_test
import unittest
import numpy
from templevel import TempLevel

__author__ = 'Rio'

class TestPocket(unittest.TestCase):
    def setUp(self):
        # self.alphaLevel = TempLevel("Dojo_64_64_128.dat")
        self.level = TempLevel("PocketWorld")
        self.alphalevel = TempLevel("AnvilWorld")

    def testPocket(self):
        level = self.level.level
#        alphalevel = self.alphalevel.level
        print "Chunk count", len(level.allChunks)
        chunk = level.getChunk(1, 5)
        a = numpy.array(chunk.SkyLight)
        chunk.dirty = True
        chunk.needsLighting = True
        level.generateLights()
        level.saveInPlace()
        assert (a == chunk.SkyLight).all()

#        level.copyBlocksFrom(alphalevel, BoundingBox((0, 0, 0), (64, 64, 64,)), (0, 0, 0))
        # assert((level.Blocks[0:64, 0:64, 0:64] == alphalevel.Blocks[0:64, 0:64, 0:64]).all())

########NEW FILE########
__FILENAME__ = schematic_test
import itertools
import os
import unittest
from pymclevel import mclevel
from templevel import TempLevel, mktemp
from pymclevel.schematic import MCSchematic
from pymclevel.box import BoundingBox

__author__ = 'Rio'

class TestSchematics(unittest.TestCase):
    def setUp(self):
        # self.alphaLevel = TempLevel("Dojo_64_64_128.dat")
        self.indevLevel = TempLevel("hell.mclevel")
        self.anvilLevel = TempLevel("AnvilWorld")

    def testCreate(self):
        # log.info("Schematic from indev")

        size = (64, 64, 64)
        temp = mktemp("testcreate.schematic")
        schematic = MCSchematic(shape=size, filename=temp, mats='Classic')
        level = self.indevLevel.level

        schematic.copyBlocksFrom(level, BoundingBox((0, 0, 0), (64, 64, 64,)), (0, 0, 0))
        assert((schematic.Blocks[0:64, 0:64, 0:64] == level.Blocks[0:64, 0:64, 0:64]).all())

        schematic.copyBlocksFrom(level, BoundingBox((0, 0, 0), (64, 64, 64,)), (-32, -32, -32))
        assert((schematic.Blocks[0:32, 0:32, 0:32] == level.Blocks[32:64, 32:64, 32:64]).all())

        schematic.saveInPlace()

        schem = mclevel.fromFile("schematics/CreativeInABox.schematic")
        tempSchematic = MCSchematic(shape=(1, 1, 3))
        tempSchematic.copyBlocksFrom(schem, BoundingBox((0, 0, 0), (1, 1, 3)), (0, 0, 0))

        level = self.anvilLevel.level
        for cx, cz in itertools.product(xrange(0, 4), xrange(0, 4)):
            try:
                level.createChunk(cx, cz)
            except ValueError:
                pass
        schematic.copyBlocksFrom(level, BoundingBox((0, 0, 0), (64, 64, 64,)), (0, 0, 0))
        schematic.close()
        os.remove(temp)

    def testRotate(self):
        level = self.anvilLevel.level
        schematic = level.extractSchematic(BoundingBox((0, 0, 0), (21, 11, 8)))
        schematic.rotateLeft()

        level.copyBlocksFrom(schematic, schematic.bounds, level.bounds.origin, biomes=True, create=True)

        schematic.flipEastWest()
        level.copyBlocksFrom(schematic, schematic.bounds, level.bounds.origin, biomes=True, create=True)

        schematic.flipVertical()
        level.copyBlocksFrom(schematic, schematic.bounds, level.bounds.origin, biomes=True, create=True)

    def testZipSchematic(self):
        level = self.anvilLevel.level

        x, y, z = level.bounds.origin
        x += level.bounds.size[0]/2 & ~15
        z += level.bounds.size[2]/2 & ~15

        box = BoundingBox((x, y, z), (64, 64, 64,))
        zs = level.extractZipSchematic(box)
        assert(box.chunkCount == zs.chunkCount)
        zs.close()
        os.remove(zs.filename)

    def testINVEditChests(self):
        invFile = mclevel.fromFile("schematics/Chests/TinkerersBox.inv")
        assert invFile.Blocks.any()
        assert not invFile.Data.any()
        assert len(invFile.Entities) == 0
        assert len(invFile.TileEntities) == 1
        # raise SystemExit

########NEW FILE########
__FILENAME__ = server_test
import unittest
from pymclevel.minecraft_server import MCServerChunkGenerator
from templevel import TempLevel
from pymclevel.box import BoundingBox

__author__ = 'Rio'

class TestServerGen(unittest.TestCase):
    def setUp(self):
        # self.alphaLevel = TempLevel("Dojo_64_64_128.dat")
        self.alphalevel = TempLevel("AnvilWorld")

    def testCreate(self):
        gen = MCServerChunkGenerator()
        print "Version: ", gen.serverVersion

        def _testCreate(filename):
            gen.createLevel(filename, BoundingBox((-128, 0, -128), (128, 128, 128)))

        TempLevel("ServerCreate", createFunc=_testCreate)

    def testServerGen(self):
        gen = MCServerChunkGenerator()
        print "Version: ", gen.serverVersion

        level = self.alphalevel.level

        gen.generateChunkInLevel(level, 50, 50)
        gen.generateChunksInLevel(level, [(120, 50), (121, 50), (122, 50), (123, 50), (244, 244), (244, 245), (244, 246)])
        c = level.getChunk(50, 50)
        assert c.Blocks.any()

########NEW FILE########
__FILENAME__ = session_lock_test
from pymclevel.infiniteworld import SessionLockLost, MCInfdevOldLevel
from templevel import TempLevel
import unittest

class SessionLockTest(unittest.TestCase):
    def test_session_lock(self):
        temp = TempLevel("AnvilWorld")
        level = temp.level
        level2 = MCInfdevOldLevel(level.filename)
        def touch():
            level.saveInPlace()
        self.assertRaises(SessionLockLost, touch)


########NEW FILE########
__FILENAME__ = templevel
import atexit
import os
from os.path import join
import shutil
import tempfile
from pymclevel import mclevel

__author__ = 'Rio'

tempdir = os.path.join(tempfile.gettempdir(), "pymclevel_test")
if not os.path.exists(tempdir):
    os.mkdir(tempdir)

def mktemp(suffix):
    td = tempfile.mkdtemp(suffix, dir=tempdir)
    os.rmdir(td)
    return td


class TempLevel(object):
    def __init__(self, filename, createFunc=None):
        if not os.path.exists(filename):
            filename = join("testfiles", filename)
        tmpname = mktemp(os.path.basename(filename))
        if os.path.exists(filename):
            if os.path.isdir(filename):
                shutil.copytree(filename, tmpname)
            else:
                shutil.copy(filename, tmpname)
        elif createFunc:
            createFunc(tmpname)
        else:
            raise IOError, "File %s not found." % filename

        self.tmpname = tmpname
        self.level = mclevel.fromFile(tmpname)
        atexit.register(self.removeTemp)

    def __del__(self):
        if hasattr(self, 'level'):
            self.level.close()
            del self.level

        self.removeTemp()

    def removeTemp(self):

        if hasattr(self, 'tmpname'):
            filename = self.tmpname

            if os.path.isdir(filename):
                shutil.rmtree(filename)
            else:
                os.unlink(filename)

########NEW FILE########
__FILENAME__ = test_primordial
from templevel import TempLevel

def testPrimordialDesert():
    templevel = TempLevel("PrimordialDesert")
    level = templevel.level
    for chunk in level.allChunks:
        level.getChunk(*chunk)

########NEW FILE########
__FILENAME__ = time_nbt
from StringIO import StringIO

__author__ = 'Rio'

import pymclevel.nbt as nbt

from timeit import timeit

path = "testfiles/TileTicks.nbt"
test_data = file(path, "rb").read()

def load_file():
    global test_file
    test_file = nbt.load(buf=test_data)

def save_file():
    global resaved_test_file
    s = StringIO()
    resaved_test_file = test_file.save(compressed=False)
    #resaved_test_file = test_file.save(buf=s)
    #resaved_test_file = s.getvalue()

print "File: ", path
print "Load: %0.1f ms" % (timeit(load_file, number=1)*1000)
print "Save: %0.1f ms" % (timeit(save_file, number=1)*1000)
print "Length: ", len(resaved_test_file)

assert test_data == resaved_test_file
__author__ = 'Rio'

########NEW FILE########
__FILENAME__ = time_relight
from pymclevel.infiniteworld import MCInfdevOldLevel
from pymclevel import mclevel
from timeit import timeit

import templevel

#import logging
#logging.basicConfig(level=logging.INFO)

def natural_relight():
    world = mclevel.fromFile("testfiles/AnvilWorld")
    t = timeit(lambda: world.generateLights(world.allChunks), number=1)
    print "Relight natural terrain: %d chunks in %.02f seconds (%.02fms per chunk)" % (world.chunkCount, t, t / world.chunkCount * 1000)


def manmade_relight():
    t = templevel.TempLevel("TimeRelight", createFunc=lambda f:MCInfdevOldLevel(f, create=True))

    world = t.level
    station = mclevel.fromFile("testfiles/station.schematic")

    times = 2

    for x in range(times):
        for z in range(times):
            world.copyBlocksFrom(station, station.bounds, (x * station.Width, 63, z * station.Length), create=True)

    t = timeit(lambda: world.generateLights(world.allChunks), number=1)
    print "Relight manmade building: %d chunks in %.02f seconds (%.02fms per chunk)" % (world.chunkCount, t, t / world.chunkCount * 1000)

if __name__ == '__main__':
    natural_relight()
    manmade_relight()




########NEW FILE########
